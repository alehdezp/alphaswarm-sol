// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title RewardCalc - Time-weighted reward calculations
library RewardCalc {
    /// @notice Calculate pending reward for a staked amount
    /// @dev VULNERABILITY: Precision loss in division
    function pendingReward(
        uint256 stakedAmount,
        uint256 startTime,
        uint256 rate
    ) internal view returns (uint256) {
        uint256 elapsed = block.timestamp - startTime;
        return (stakedAmount * rate * elapsed) / 1e18;
    }
}
