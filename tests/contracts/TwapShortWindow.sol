// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TwapShortWindow
 * @notice VULNERABLE: TWAP window too short (multi-block manipulation possible)
 *
 *  * - Uses TWAP but window is too short (30 seconds = ~2.5 blocks)
 * - Post-merge PoS allows validators to know future block proposers
 * - Multi-block manipulation possible with 2-3 coordinated blocks
 *
 * Related CWEs:
 * - CWE-20: Improper Input Validation
 * - SCWE-028: Price Oracle Manipulation
 *
 * Research:
 * - Uniswap blog: "TWAP Oracles in Proof of Stake" (Oct 2022)
 * - Euler Finance: TWAP manipulation cost analysis
 * - Chaos Labs: TWAP market risk assessment
 *
 * Recommendation:
 * - Use minimum 10-minute TWAP window (50 blocks)
 * - For high-value operations, use 30+ minute windows
 * - Consider Chainlink Price Feeds for primary oracle
 */

interface IUniswapV3Pool {
    function observe(uint32[] calldata secondsAgos) external view returns (
        int56[] memory tickCumulatives,
        uint160[] memory secondsPerLiquidityCumulativeX128s
    );
}

contract TwapShortWindow {
    IUniswapV3Pool public pool;

    // VULNERABLE: 30 seconds is too short post-merge
    uint32 public constant SHORT_WINDOW = 30;

    // Better but still risky for low-liquidity pairs
    uint32 public constant MEDIUM_WINDOW = 300; // 5 minutes

    constructor(IUniswapV3Pool pool_) {
        pool = pool_;
    }

    // VULNERABLE: Short window enables multi-block manipulation
    function getTwapShortWindow() external view returns (int24) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = SHORT_WINDOW;
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = pool.observe(secondsAgos);

        int56 tickCumulativesDelta = tickCumulatives[1] - tickCumulatives[0];
        int24 tick = int24(tickCumulativesDelta / int56(uint56(SHORT_WINDOW)));

        return tick;
    }

    // Still risky for manipulation
    function getTwapMediumWindow() external view returns (int24) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = MEDIUM_WINDOW;
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = pool.observe(secondsAgos);

        int56 tickCumulativesDelta = tickCumulatives[1] - tickCumulatives[0];
        int24 tick = int24(tickCumulativesDelta / int56(uint56(MEDIUM_WINDOW)));

        return tick;
    }
}
