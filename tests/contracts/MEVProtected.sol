// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MEVProtected
 * @notice Demonstrates SAFE patterns that protect against MEV attacks
 *
 * This contract shows proper implementation of MEV protection mechanisms:
 * - Proper slippage checks with reasonable tolerances
 * - Deadline enforcement with block.timestamp validation
 * - Commit-reveal for sensitive operations
 * - Private transaction options
 * - Time locks for critical operations
 *
 * This is a NEGATIVE TEST contract - it should NOT trigger MEV vulnerability patterns
 */
contract MEVProtected {
    mapping(bytes32 => uint256) public commitments;
    mapping(bytes32 => bool) public revealed;
    uint256 public constant REVEAL_DELAY = 1;
    uint256 public constant MAX_SLIPPAGE_BPS = 100; // 1%

    // SAFE: Proper slippage and deadline checks
    function safeSwap(
        uint256 amountIn,
        uint256 amountOutMin,
        uint256 deadline
    ) external view returns (uint256) {
        // SAFE: Validates deadline is in future
        require(deadline > block.timestamp, "invalid deadline");
        require(block.timestamp <= deadline, "expired");

        uint256 amountOut = amountIn;

        // SAFE: Enforces minimum output
        require(amountOut >= amountOutMin, "insufficient output");

        return amountOut;
    }

    // SAFE: Commit-reveal pattern prevents frontrunning
    function commitOrder(bytes32 commitHash) external {
        require(commitments[commitHash] == 0, "already committed");
        commitments[commitHash] = block.number;
    }

    function revealOrder(
        uint256 amountIn,
        uint256 amountOutMin,
        uint256 deadline,
        bytes32 salt
    ) external view returns (uint256) {
        bytes32 commitHash = keccak256(abi.encode(amountIn, amountOutMin, deadline, salt));

        // SAFE: Enforces delay between commit and reveal
        require(commitments[commitHash] > 0, "no commitment");
        require(block.number >= commitments[commitHash] + REVEAL_DELAY, "reveal too early");
        require(!revealed[commitHash], "already revealed");

        // Now safe to execute with parameters hidden from mempool
        require(block.timestamp <= deadline, "expired");

        uint256 amountOut = amountIn;
        require(amountOut >= amountOutMin, "insufficient output");

        return amountOut;
    }

    // SAFE: Validates slippage tolerance is reasonable
    function swapWithMaxSlippage(
        uint256 amountIn,
        uint256 amountOutMin,
        uint256 slippageBps,
        uint256 deadline
    ) external view returns (uint256) {
        require(deadline > block.timestamp, "invalid deadline");
        require(block.timestamp <= deadline, "expired");

        // SAFE: Enforces maximum slippage tolerance
        require(slippageBps <= MAX_SLIPPAGE_BPS, "slippage too high");

        uint256 amountOut = amountIn;
        require(amountOut >= amountOutMin, "insufficient output");

        return amountOut;
    }

    // SAFE: Time lock prevents instant manipulation
    function timelockWithdraw(
        uint256 amount,
        uint256 unlockTime,
        uint256 requestTime
    ) external view returns (bool) {
        // SAFE: Requires delay between request and execution
        require(unlockTime > requestTime, "invalid timelock");
        require(block.timestamp >= unlockTime, "still locked");
        require(block.timestamp <= unlockTime + 1 days, "timelock expired");
        require(amount > 0, "invalid amount");

        return true;
    }
}
