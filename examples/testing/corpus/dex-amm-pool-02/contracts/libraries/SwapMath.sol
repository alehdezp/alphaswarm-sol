// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title SwapMath - AMM mathematical operations
library SwapMath {
    /// @notice Calculate output for constant-product swap
    /// @dev VULNERABILITY: Precision loss with small amounts
    function constantProductOut(
        uint256 amountIn,
        uint256 reserveIn,
        uint256 reserveOut
    ) internal pure returns (uint256) {
        uint256 numerator = amountIn * reserveOut;
        uint256 denominator = reserveIn + amountIn;
        return numerator / denominator;
    }

    /// @notice Geometric mean for initial LP calculation
    function geometricMean(uint256 a, uint256 b) internal pure returns (uint256) {
        return sqrt(a * b);
    }

    function sqrt(uint256 x) internal pure returns (uint256) {
        if (x == 0) return 0;
        uint256 z = (x + 1) / 2;
        uint256 y = x;
        while (z < y) {
            y = z;
            z = (x / z + z) / 2;
        }
        return y;
    }
}
