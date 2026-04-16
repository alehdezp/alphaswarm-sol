// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../libraries/TokenAccounting.sol";

/// @title MultiAssetVault - Multi-token vault with dynamic rebalancing
contract MultiAssetVault {
    using TokenAccounting for uint256;

    struct AssetConfig {
        uint256 weight;
        uint256 deposited;
        uint256 borrowed;
        bool active;
    }

    mapping(uint256 => AssetConfig) public assets; // assetId => config
    mapping(address => mapping(uint256 => uint256)) public userBalances;
    mapping(address => uint256) public userDebt;
    uint256 public assetCount;
    address public curator;
    uint256 public maxLeverage; // e.g. 300 = 3x

    event AssetDeposited(address indexed user, uint256 assetId, uint256 amount);
    event AssetBorrowed(address indexed user, uint256 assetId, uint256 amount);
    event Rebalanced(uint256 totalValue);

    constructor() {
        curator = msg.sender;
        maxLeverage = 300;
    }

    /// @notice Register a new asset type
    function registerAsset(uint256 weight) external returns (uint256) {
        require(msg.sender == curator, "Not curator");
        uint256 id = assetCount++;
        assets[id] = AssetConfig(weight, 0, 0, true);
        return id;
    }

    /// @notice Deposit asset into vault
    function depositAsset(uint256 assetId, uint256 amount) external payable {
        require(assets[assetId].active, "Asset inactive");
        require(msg.value == amount, "Value mismatch");
        userBalances[msg.sender][assetId] += amount;
        assets[assetId].deposited += amount;
        emit AssetDeposited(msg.sender, assetId, amount);
    }

    /// @notice Borrow against deposited collateral
    /// @dev VULNERABILITY: No collateral ratio check (logic flaw)
    function borrowAsset(uint256 assetId, uint256 amount) external {
        require(assets[assetId].active, "Asset inactive");
        // Missing: collateral adequacy check
        userDebt[msg.sender] += amount;
        assets[assetId].borrowed += amount;

        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Borrow failed");

        emit AssetBorrowed(msg.sender, assetId, amount);
    }

    /// @notice Withdraw deposited assets
    /// @dev VULNERABILITY: Reentrancy + no debt check
    function withdrawAsset(uint256 assetId, uint256 amount) external {
        require(userBalances[msg.sender][assetId] >= amount, "Insufficient");
        // Missing: check that user debt is repaid before withdrawal

        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Withdraw failed");

        userBalances[msg.sender][assetId] -= amount;
        assets[assetId].deposited -= amount;
    }

    /// @notice Rebalance vault weights
    /// @dev VULNERABILITY: Unbounded loop over assets
    function rebalance() external {
        require(msg.sender == curator, "Not curator");
        uint256 totalValue;
        for (uint256 i = 0; i < assetCount; i++) {
            if (assets[i].active) {
                totalValue += assets[i].deposited * assets[i].weight;
            }
        }
        emit Rebalanced(totalValue);
    }

    /// @notice Update asset weight
    /// @dev VULNERABILITY: Missing access control
    function setAssetWeight(uint256 assetId, uint256 newWeight) external {
        assets[assetId].weight = newWeight;
    }

    /// @notice Liquidate undercollateralized position
    /// @dev VULNERABILITY: Anyone can liquidate, no health check
    function liquidatePosition(address user, uint256 assetId) external {
        uint256 balance = userBalances[user][assetId];
        uint256 debt = userDebt[user];
        // Missing: actual health factor check
        require(debt > 0, "No debt");

        userBalances[user][assetId] = 0;
        userDebt[user] = 0;
        assets[assetId].deposited -= balance;

        (bool ok, ) = msg.sender.call{value: balance}("");
        require(ok, "Liquidation failed");
    }

    /// @notice Transfer curator role
    /// @dev VULNERABILITY: Missing access control
    function transferCurator(address newCurator) external {
        curator = newCurator;
    }

    receive() external payable {}
}
