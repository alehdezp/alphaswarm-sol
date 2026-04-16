// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MEVSandwichVulnerable
 * @notice Demonstrates patterns vulnerable to sandwich attacks
 *
 * Large swaps without slippage protection or with excessive
 * slippage tolerance can be sandwiched by MEV bots.
 *
 * Sandwich Attack Flow:
 * 1. MEV bot monitors mempool for large swaps
 * 2. Bot submits frontrun transaction (buy) with higher gas to execute first
 * 3. Victim's swap executes at inflated price
 * 4. Bot submits backrun transaction (sell) to capture profit
 * 5. Victim suffers price impact + sandwich loss (often 51%+ of MEV volume in 2025)
 *
 * Real-world impact: $289.76M in sandwich attacks in 2025 (51.56% of MEV volume)
 */
contract MEVSandwichVulnerable {
    // VULNERABLE: Zero slippage tolerance - catastrophic for large trades
    function swapWithZeroSlippage(uint256 amountIn) external pure returns (uint256) {
        uint256 amountOut = amountIn;
        // No slippage check means ANY price is acceptable
        return amountOut;
    }

    // VULNERABLE: Excessive slippage (50%) opens sandwich opportunity
    function swapWithExcessiveSlippage(uint256 amountIn, uint256 amountOutMin) external pure returns (uint256) {
        uint256 amountOut = amountIn;
        // Even with amountOutMin, if tolerance is too high (e.g., 50%), sandwich is profitable
        require(amountOut >= amountOutMin, "slippage");
        return amountOut;
    }

    // VULNERABLE: No deadline + no slippage = maximum exposure
    function swapNoProtection(uint256 amountIn) external pure returns (uint256) {
        return amountIn;
    }
}
