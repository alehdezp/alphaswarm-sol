// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ILiquidityPool {
    function exchange(address fromAsset, address toAsset, uint256 qty, address recipient) external returns (uint256);
}

/**
 * @title SwapRenamed
 * @notice DEX interaction with non-standard naming.
 *         Tests detection of MEV vulnerabilities without "swap", "slippage", "deadline" names.
 *
 * Renamed: swap -> exchange, minAmountOut -> minimumReturn, deadline -> expiry
 */
contract SwapRenamed {
    ILiquidityPool public liquidityPool;  // Renamed from "router" or "dex"

    constructor(address _pool) {
        liquidityPool = ILiquidityPool(_pool);
    }

    // VULNERABLE: No minimum return (slippage) protection
    function exchangeAssetsUnsafe(
        address fromAsset,
        address toAsset,
        uint256 qty
    ) external returns (uint256) {
        return liquidityPool.exchange(fromAsset, toAsset, qty, msg.sender);
    }

    // VULNERABLE: No expiry (deadline) check
    function exchangeWithMinimum(
        address fromAsset,
        address toAsset,
        uint256 qty,
        uint256 minimumReturn  // Renamed from "minAmountOut"
    ) external returns (uint256) {
        uint256 received = liquidityPool.exchange(fromAsset, toAsset, qty, msg.sender);
        require(received >= minimumReturn, "insufficient return");
        return received;
    }

    // SAFE: Has both minimum return AND expiry
    function exchangeSafe(
        address fromAsset,
        address toAsset,
        uint256 qty,
        uint256 minimumReturn,
        uint256 expiry  // Renamed from "deadline"
    ) external returns (uint256) {
        require(block.timestamp <= expiry, "expired");
        uint256 received = liquidityPool.exchange(fromAsset, toAsset, qty, msg.sender);
        require(received >= minimumReturn, "insufficient return");
        return received;
    }
}
