// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title PositionMath - Financial calculations for credit positions
library PositionMath {
    /// @notice Compute accrued interest
    /// @dev VULNERABILITY: Precision loss in interest calculation
    function computeAccrual(
        uint256 principal,
        uint256 rateBps,
        uint256 elapsed
    ) internal pure returns (uint256) {
        // Integer division truncates - small principals lose precision
        return (principal * rateBps * elapsed) / (10000 * 86400);
    }

    /// @notice Calculate liquidation threshold
    function liquidationAmount(
        uint256 collateral,
        uint256 price,
        uint256 liability
    ) internal pure returns (uint256) {
        uint256 collateralValue = (collateral * price) / 1e18;
        if (collateralValue >= liability) return 0;
        return liability - collateralValue;
    }
}
