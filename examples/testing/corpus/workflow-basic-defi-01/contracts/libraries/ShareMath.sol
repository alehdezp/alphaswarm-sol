// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ShareMath - Library for vault share calculations
library ShareMath {
    /// @notice Calculate shares for a given deposit amount
    /// @dev VULNERABILITY: Precision loss - integer division without rounding protection
    function calculateShares(
        uint256 amount,
        uint256 totalShares,
        uint256 totalAssets
    ) internal pure returns (uint256) {
        return (amount * totalShares) / totalAssets;
    }

    /// @notice Calculate asset value for a given share amount
    function calculateAssets(
        uint256 shareAmount,
        uint256 totalShares,
        uint256 totalAssets
    ) internal pure returns (uint256) {
        return (shareAmount * totalAssets) / totalShares;
    }
}
