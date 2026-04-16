// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/IVaultCore.sol";
import "../interfaces/IPriceFeed.sol";
import "../libraries/ShareMath.sol";

/// @title SimpleVault - Basic yield-bearing vault
/// @notice Accepts ETH deposits and issues shares proportional to deposited value
contract SimpleVault is IVaultCore {
    using ShareMath for uint256;

    mapping(address => uint256) public shares;
    uint256 public totalShares;
    uint256 private _totalDeposited;
    address public manager;
    IPriceFeed public priceFeed;
    bool private _initialized;

    modifier onlyManager() {
        require(msg.sender == manager, "Not manager");
        _;
    }

    constructor(address _priceFeed) {
        manager = msg.sender;
        priceFeed = IPriceFeed(_priceFeed);
    }

    /// @notice Deposit ETH and receive vault shares
    function deposit(uint256 amount) external payable override {
        require(msg.value == amount && amount > 0, "Invalid deposit");

        uint256 sharesToMint;
        if (totalShares == 0) {
            sharesToMint = amount;
        } else {
            sharesToMint = amount.calculateShares(totalShares, _totalDeposited);
        }

        shares[msg.sender] += sharesToMint;
        totalShares += sharesToMint;
        _totalDeposited += amount;

        emit Deposited(msg.sender, amount, sharesToMint);
    }

    /// @notice Redeem shares for ETH
    /// @dev VULNERABILITY: State update after external call (reentrancy)
    function redeem(uint256 shareAmount) external override {
        require(shares[msg.sender] >= shareAmount, "Insufficient shares");

        uint256 payout = shareAmount.calculateAssets(totalShares, _totalDeposited);

        // External call before state update
        (bool success, ) = msg.sender.call{value: payout}("");
        require(success, "Transfer failed");

        shares[msg.sender] -= shareAmount;
        totalShares -= shareAmount;
        _totalDeposited -= payout;

        emit Redeemed(msg.sender, shareAmount, payout);
    }

    /// @notice Get current share price
    function getSharePrice() external view override returns (uint256) {
        if (totalShares == 0) return 1e18;
        return (_totalDeposited * 1e18) / totalShares;
    }

    /// @notice Total assets under management
    function totalAssets() external view override returns (uint256) {
        return _totalDeposited;
    }

    /// @notice Emergency withdrawal by manager
    /// @dev VULNERABILITY: No access control on setManager
    function setManager(address newManager) external {
        manager = newManager;
    }

    /// @notice Update price feed
    function updatePriceFeed(address newFeed) external onlyManager {
        priceFeed = IPriceFeed(newFeed);
    }

    /// @notice Check if price is fresh
    /// @dev VULNERABILITY: No staleness check on oracle price
    function checkPrice() external view returns (uint256) {
        (uint256 price, ) = priceFeed.latestPrice();
        return price;
    }

    receive() external payable {}
}
