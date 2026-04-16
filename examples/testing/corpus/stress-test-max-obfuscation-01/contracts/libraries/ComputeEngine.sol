// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ComputeEngine - Mathematical computations for adaptive pools
library ComputeEngine {
    /// @notice Aggregate base and bonus amounts
    function aggregate(uint256 base, uint256 bonus) internal pure returns (uint256) {
        return base + bonus;
    }

    /// @notice Compute growth based on rate
    /// @dev VULNERABILITY: Precision loss in growth calculation
    function computeGrowth(uint256 principal, uint256 rate) internal pure returns (uint256) {
        return (principal * rate) / 1e18;
    }

    /// @notice Weighted distribution
    function distribute(uint256 total, uint256 weight, uint256 totalWeight) internal pure returns (uint256) {
        if (totalWeight == 0) return 0;
        return (total * weight) / totalWeight;
    }
}
