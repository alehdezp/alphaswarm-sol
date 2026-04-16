// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MEVDeadlineTimestamp
 * @notice Demonstrates vulnerable pattern where deadline is set to block.timestamp
 *
 * Using block.timestamp as deadline allows validators/sequencers
 * to hold transactions indefinitely and execute them at worst possible price.
 *
 * CWE Mapping: CWE-20 (Improper Input Validation)
 * Related: SCWE-037 (Insufficient Protection Against Front-Running)
 *
 * Attack Vector:
 * 1. User submits swap with deadline = block.timestamp
 * 2. Sequencer/validator holds transaction in mempool
 * 3. Price moves unfavorably to user
 * 4. Sequencer includes transaction later when block.timestamp still matches
 * 5. User receives much worse execution than expected
 */
contract MEVDeadlineTimestamp {
    function swapWithCurrentTimestamp(uint256 amountIn, uint256 amountOutMin) external view returns (uint256) {
        // VULNERABLE: Using block.timestamp as deadline provides no time protection
        require(block.timestamp <= block.timestamp, "expired");
        uint256 amountOut = amountIn;
        require(amountOut >= amountOutMin, "slippage");
        return amountOut;
    }

    function swapWithNoDeadline(uint256 amountIn, uint256 amountOutMin) external view returns (uint256) {
        // VULNERABLE: No deadline check at all
        uint256 amountOut = amountIn;
        require(amountOut >= amountOutMin, "slippage");
        return amountOut;
    }
}
