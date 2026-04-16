// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../libraries/TokenAccounting.sol";

/// @title MultiAssetVault (SAFE VARIANT)
contract MultiAssetVault_safe {
    using TokenAccounting for uint256;

    struct AssetConfig { uint256 weight; uint256 deposited; uint256 borrowed; bool active; }

    mapping(uint256 => AssetConfig) public assets;
    mapping(address => mapping(uint256 => uint256)) public userBalances;
    mapping(address => uint256) public userDebt;
    uint256 public assetCount;
    address public curator;
    uint256 public maxLeverage;
    bool private _locked;
    uint256 public constant MAX_ASSETS = 50;

    modifier nonReentrant() { require(!_locked); _locked = true; _; _locked = false; }
    modifier onlyCurator() { require(msg.sender == curator, "Not curator"); _; }

    event AssetDeposited(address indexed user, uint256 assetId, uint256 amount);
    event AssetBorrowed(address indexed user, uint256 assetId, uint256 amount);

    constructor() { curator = msg.sender; maxLeverage = 300; }

    function registerAsset(uint256 weight) external onlyCurator returns (uint256) {
        require(assetCount < MAX_ASSETS, "Max assets");
        uint256 id = assetCount++;
        assets[id] = AssetConfig(weight, 0, 0, true);
        return id;
    }

    function depositAsset(uint256 assetId, uint256 amount) external payable {
        require(assets[assetId].active, "Asset inactive");
        require(msg.value == amount, "Value mismatch");
        userBalances[msg.sender][assetId] += amount;
        assets[assetId].deposited += amount;
    }

    function borrowAsset(uint256 assetId, uint256 amount) external nonReentrant {
        require(assets[assetId].active, "Asset inactive");
        uint256 totalCollateral = _totalUserCollateral(msg.sender);
        uint256 newDebt = userDebt[msg.sender] + amount;
        require(totalCollateral.healthFactor(newDebt, maxLeverage) >= 100, "Undercollateralized"); // FIXED
        userDebt[msg.sender] = newDebt;
        assets[assetId].borrowed += amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Borrow failed");
    }

    function withdrawAsset(uint256 assetId, uint256 amount) external nonReentrant {
        require(userBalances[msg.sender][assetId] >= amount, "Insufficient");
        require(userDebt[msg.sender] == 0, "Repay debt first"); // FIXED
        userBalances[msg.sender][assetId] -= amount;
        assets[assetId].deposited -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Withdraw failed");
    }

    function setAssetWeight(uint256 assetId, uint256 newWeight) external onlyCurator { assets[assetId].weight = newWeight; } // FIXED
    function transferCurator(address newCurator) external onlyCurator { require(newCurator != address(0)); curator = newCurator; } // FIXED

    function _totalUserCollateral(address user) internal view returns (uint256) {
        uint256 total;
        for (uint256 i = 0; i < assetCount; i++) { total += userBalances[user][i]; }
        return total;
    }

    receive() external payable {}
}
