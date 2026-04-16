// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TwapSecureWindow
 * @notice Secure TWAP implementation with proper window size
 *
 * Security Features:
 * - Uses 30-minute TWAP window (manipulation resistant)
 * - Validates pool observations are available
 * - Configurable window for different risk levels
 *
 * Related CWEs:
 * - Mitigation for CWE-20: Improper Input Validation
 * - Mitigation for SCWE-028: Price Oracle Manipulation
 */

interface IUniswapV3Pool {
    function observe(uint32[] calldata secondsAgos) external view returns (
        int56[] memory tickCumulatives,
        uint160[] memory secondsPerLiquidityCumulativeX128s
    );
}

contract TwapSecureWindow {
    IUniswapV3Pool public pool;

    // Secure: 30-minute window makes manipulation very expensive
    uint32 public constant SECURE_WINDOW = 1800; // 30 minutes

    constructor(IUniswapV3Pool pool_) {
        pool = pool_;
    }

    function getTwapSecureWindow() external view returns (int24) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = SECURE_WINDOW;
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = pool.observe(secondsAgos);

        int56 tickCumulativesDelta = tickCumulatives[1] - tickCumulatives[0];
        int24 tick = int24(tickCumulativesDelta / int56(uint56(SECURE_WINDOW)));

        return tick;
    }

    function getTwapCustomWindow(uint32 window) external view returns (int24) {
        require(window >= 600, "Window too short"); // Minimum 10 minutes

        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = window;
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = pool.observe(secondsAgos);

        int56 tickCumulativesDelta = tickCumulatives[1] - tickCumulatives[0];
        int24 tick = int24(tickCumulativesDelta / int56(uint56(window)));

        return tick;
    }
}
