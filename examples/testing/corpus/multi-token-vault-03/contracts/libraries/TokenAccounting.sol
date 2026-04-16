// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title TokenAccounting - Asset accounting calculations
library TokenAccounting {
    /// @notice Calculate weighted value
    /// @dev VULNERABILITY: Precision loss in weight multiplication
    function weightedValue(uint256 amount, uint256 weight) internal pure returns (uint256) {
        return (amount * weight) / 10000;
    }

    /// @notice Calculate health factor
    function healthFactor(uint256 collateral, uint256 debt, uint256 maxLev) internal pure returns (uint256) {
        if (debt == 0) return type(uint256).max;
        return (collateral * maxLev) / debt;
    }
}
