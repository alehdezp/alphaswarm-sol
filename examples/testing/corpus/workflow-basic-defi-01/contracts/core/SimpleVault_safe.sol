// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/IVaultCore.sol";
import "../interfaces/IPriceFeed.sol";
import "../libraries/ShareMath.sol";

/// @title SimpleVault - Basic yield-bearing vault (SAFE VARIANT)
contract SimpleVault_safe is IVaultCore {
    using ShareMath for uint256;

    mapping(address => uint256) public shares;
    uint256 public totalShares;
    uint256 private _totalDeposited;
    address public manager;
    IPriceFeed public priceFeed;
    bool private _locked;

    modifier nonReentrant() {
        require(!_locked, "Reentrancy");
        _locked = true;
        _;
        _locked = false;
    }

    modifier onlyManager() {
        require(msg.sender == manager, "Not manager");
        _;
    }

    constructor(address _priceFeed) {
        manager = msg.sender;
        priceFeed = IPriceFeed(_priceFeed);
    }

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

    /// @notice Redeem shares for ETH (FIXED: CEI pattern + nonReentrant)
    function redeem(uint256 shareAmount) external override nonReentrant {
        require(shares[msg.sender] >= shareAmount, "Insufficient shares");
        uint256 payout = shareAmount.calculateAssets(totalShares, _totalDeposited);

        // State update BEFORE external call
        shares[msg.sender] -= shareAmount;
        totalShares -= shareAmount;
        _totalDeposited -= payout;

        (bool success, ) = msg.sender.call{value: payout}("");
        require(success, "Transfer failed");
        emit Redeemed(msg.sender, shareAmount, payout);
    }

    function getSharePrice() external view override returns (uint256) {
        if (totalShares == 0) return 1e18;
        return (_totalDeposited * 1e18) / totalShares;
    }

    function totalAssets() external view override returns (uint256) {
        return _totalDeposited;
    }

    /// @notice FIXED: Access control added
    function setManager(address newManager) external onlyManager {
        require(newManager != address(0), "Zero address");
        manager = newManager;
    }

    function updatePriceFeed(address newFeed) external onlyManager {
        priceFeed = IPriceFeed(newFeed);
    }

    /// @notice FIXED: Staleness check added
    function checkPrice() external view returns (uint256) {
        (uint256 price, uint256 ts) = priceFeed.latestPrice();
        require(block.timestamp - ts < 3600, "Stale price");
        return price;
    }

    receive() external payable {}
}
