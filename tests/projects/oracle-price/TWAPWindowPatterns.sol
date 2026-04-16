// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title TWAPWindowPatterns
 * @notice Test contract for oracle-005: TWAP Oracle Missing Time Window Parameter
 * @dev Contains vulnerable (no window parameter) and safe (with window parameter) TWAP patterns
 */

// Mock Uniswap V3 Pool interface for TWAP
interface IUniswapV3Pool {
    function observe(uint32[] calldata secondsAgos)
        external
        view
        returns (
            int56[] memory tickCumulatives,
            uint160[] memory secondsPerLiquidityCumulativeX128s
        );
}

// Mock Uniswap V2 Pair interface for TWAP
interface IUniswapV2Pair {
    function price0CumulativeLast() external view returns (uint256);
    function price1CumulativeLast() external view returns (uint256);
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
}

contract TWAPWindowPatterns {
    IUniswapV3Pool public uniswapV3Pool;
    IUniswapV2Pair public uniswapV2Pair;

    uint256 public storedPrice;
    mapping(address => uint256) public userCollateral;

    // =============================================================================
    // TRUE POSITIVES - TWAP reads WITHOUT window parameter (VULNERABLE)
    // =============================================================================

    /**
     * @dev TP1: Hardcoded 30-minute window (classic vulnerability)
     * Pattern: oracle-005 should FLAG this
     */
    function getTWAPPriceHardcoded() public returns (uint256) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = 1800; // HARDCODED 30 minutes
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        int56 tickCumulativeDelta = tickCumulatives[1] - tickCumulatives[0];
        int24 avgTick = int24(tickCumulativeDelta / 1800);

        storedPrice = _getQuoteAtTick(avgTick);
        return storedPrice;
    }

    /**
     * @dev TP2: Short hardcoded window (10 minutes - CRITICAL vulnerability)
     * Pattern: oracle-005 should FLAG this
     */
    function getTWAPShortWindow() external returns (uint256) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = 600; // HARDCODED 10 minutes - too short!
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        int56 tickCumulativeDelta = tickCumulatives[1] - tickCumulatives[0];

        storedPrice = uint256(int256(tickCumulativeDelta));
        return storedPrice;
    }

    /**
     * @dev TP3: Uniswap V2 TWAP with hardcoded window
     * Pattern: oracle-005 should FLAG this
     */
    function getUniswapV2TWAP() public returns (uint256) {
        uint256 price0Cumulative = uniswapV2Pair.price0CumulativeLast();
        (, , uint32 blockTimestamp) = uniswapV2Pair.getReserves();

        // HARDCODED window calculation
        uint32 timeElapsed = blockTimestamp - 1800; // HARDCODED 30 minutes
        uint256 twapPrice = price0Cumulative / timeElapsed;

        storedPrice = twapPrice;
        return twapPrice;
    }

    /**
     * @dev TP4: Critical operation (liquidation) using hardcoded TWAP
     * Pattern: oracle-005 should FLAG this (high severity context)
     */
    function liquidateWithHardcodedTWAP(address user) external returns (bool) {
        // Get TWAP with HARDCODED window
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = 1200; // HARDCODED 20 minutes
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        int56 tickCumulativeDelta = tickCumulatives[1] - tickCumulatives[0];
        int24 avgTick = int24(tickCumulativeDelta / 1200);
        uint256 price = _getQuoteAtTick(avgTick);

        // Use price for liquidation decision
        if (userCollateral[user] < price * 150 / 100) {
            userCollateral[user] = 0;
            return true;
        }
        return false;
    }

    /**
     * @dev TP5: Borrow operation with hardcoded TWAP window
     * Pattern: oracle-005 should FLAG this
     */
    function borrowAgainstCollateral(uint256 amount) external returns (bool) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = 900; // HARDCODED 15 minutes
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        uint256 collateralValue = uint256(int256(tickCumulatives[1] - tickCumulatives[0]));

        if (collateralValue > amount * 2) {
            storedPrice = collateralValue;
            return true;
        }
        return false;
    }

    /**
     * @dev TP6: Swap using hardcoded TWAP (MEV-sensitive)
     * Pattern: oracle-005 should FLAG this
     */
    function swapAtTWAPPrice(uint256 amountIn) external returns (uint256) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = 1800; // HARDCODED
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        int56 delta = tickCumulatives[1] - tickCumulatives[0];

        uint256 twapPrice = uint256(int256(delta));
        uint256 amountOut = amountIn * twapPrice / 1e18;

        return amountOut;
    }

    /**
     * @dev TP7: consult() pattern (Uniswap V2 style) with hardcoded window
     * Pattern: oracle-005 should FLAG this
     */
    function consultTWAP(address token, uint256 amountIn) public returns (uint256) {
        uint256 price0Cumulative = uniswapV2Pair.price0CumulativeLast();

        // HARDCODED window
        uint256 timeElapsed = 1800; // 30 minutes hardcoded
        uint256 price = price0Cumulative / timeElapsed;

        storedPrice = price * amountIn;
        return storedPrice;
    }

    /**
     * @dev TP8: Variation - different naming but still hardcoded
     * Pattern: oracle-005 should FLAG this
     */
    function getPriceFromTWAPOracle() external returns (uint256) {
        uint32[] memory periods = new uint32[](2);
        periods[0] = 2400; // HARDCODED 40 minutes
        periods[1] = 0;

        (int56[] memory ticks, ) = uniswapV3Pool.observe(periods);
        storedPrice = uint256(int256(ticks[1] - ticks[0]));
        return storedPrice;
    }

    // =============================================================================
    // TRUE NEGATIVES - TWAP reads WITH window parameter (SAFE)
    // =============================================================================

    /**
     * @dev TN1: Configurable window parameter (SAFE)
     * Pattern: oracle-005 should NOT flag this
     */
    function getTWAPPriceConfigurable(uint32 twapWindow) public view returns (uint256) {
        require(twapWindow >= 600, "Window too short");

        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = twapWindow; // CONFIGURABLE!
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        int56 tickCumulativeDelta = tickCumulatives[1] - tickCumulatives[0];
        int24 avgTick = int24(tickCumulativeDelta / int56(uint56(twapWindow)));

        return _getQuoteAtTick(avgTick);
    }

    /**
     * @dev TN2: secondsAgo parameter name variant (SAFE)
     * Pattern: oracle-005 should NOT flag this
     */
    function getTWAPWithSecondsAgo(uint32 secondsAgo) external view returns (uint256) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = secondsAgo;
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        return uint256(int256(tickCumulatives[1] - tickCumulatives[0]));
    }

    /**
     * @dev TN3: period parameter name variant (SAFE)
     * Pattern: oracle-005 should NOT flag this
     */
    function getTWAPWithPeriod(uint32 period) public view returns (uint256) {
        require(period >= 1800, "Period minimum 30 min");

        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = period;
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        int56 delta = tickCumulatives[1] - tickCumulatives[0];

        return uint256(int256(delta / int56(uint56(period))));
    }

    /**
     * @dev TN4: twapWindow parameter name (SAFE)
     * Pattern: oracle-005 should NOT flag this
     */
    function getTWAPWithWindowParam(uint32 twapWindow) external view returns (uint256) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = twapWindow;
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        return uint256(int256(tickCumulatives[1] - tickCumulatives[0]));
    }

    /**
     * @dev TN5: interval parameter name variant (SAFE)
     * Pattern: oracle-005 should NOT flag this
     */
    function consultWithInterval(uint32 interval) public view returns (uint256) {
        require(interval > 0, "Invalid interval");

        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = interval;
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        return _getQuoteAtTick(int24(tickCumulatives[1] - tickCumulatives[0]));
    }

    /**
     * @dev TN6: Liquidation with configurable TWAP (SAFE)
     * Pattern: oracle-005 should NOT flag this
     */
    function liquidateWithConfigurableTWAP(address user, uint32 window) external returns (bool) {
        require(window >= 1800, "Window too short for liquidation");

        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = window;
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        int56 tickCumulativeDelta = tickCumulatives[1] - tickCumulatives[0];
        int24 avgTick = int24(tickCumulativeDelta / int56(uint56(window)));
        uint256 price = _getQuoteAtTick(avgTick);

        if (userCollateral[user] < price * 150 / 100) {
            userCollateral[user] = 0;
            return true;
        }
        return false;
    }

    // =============================================================================
    // EDGE CASES
    // =============================================================================

    /**
     * @dev EDGE1: Internal helper with hardcoded window
     * Expected: Should FLAG (internal but state-changing via storage write)
     * Pattern: oracle-005 should FLAG this (internal but not pure/view)
     */
    function _getTWAPInternal() internal returns (uint256) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = 1800; // HARDCODED
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        storedPrice = uint256(int256(tickCumulatives[1] - tickCumulatives[0]));
        return storedPrice;
    }

    /**
     * @dev EDGE2: View function with hardcoded TWAP
     * Expected: Should NOT flag (view functions excluded by pattern)
     * Pattern: oracle-005 should NOT flag (is_view = true)
     */
    function viewTWAPHardcoded() external view returns (uint256) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = 1800; // HARDCODED but view-only
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        return uint256(int256(tickCumulatives[1] - tickCumulatives[0]));
    }

    /**
     * @dev EDGE3: Pure function (should not flag - no oracle read possible)
     * Pattern: oracle-005 should NOT flag (is_pure = true)
     */
    function calculateTWAPDelta(int56 tick1, int56 tick0, uint32 window) external pure returns (uint256) {
        int56 delta = tick1 - tick0;
        return uint256(int256(delta / int56(uint56(window))));
    }

    /**
     * @dev EDGE4: Multi-window TWAP (has window parameters)
     * Pattern: oracle-005 should NOT flag this (has window parameters)
     */
    function getMultiWindowTWAP(uint32 shortWindow, uint32 longWindow) external view returns (uint256, uint256) {
        uint32[] memory secondsAgos = new uint32[](2);

        // Short window TWAP
        secondsAgos[0] = shortWindow;
        secondsAgos[1] = 0;
        (int56[] memory shortTicks, ) = uniswapV3Pool.observe(secondsAgos);

        // Long window TWAP
        secondsAgos[0] = longWindow;
        (int56[] memory longTicks, ) = uniswapV3Pool.observe(secondsAgos);

        return (
            uint256(int256(shortTicks[1] - shortTicks[0])),
            uint256(int256(longTicks[1] - longTicks[0]))
        );
    }

    /**
     * @dev EDGE5: No TWAP read at all (should not flag - no reads_twap)
     * Pattern: oracle-005 should NOT flag (no TWAP operation)
     */
    function updateStoredPriceManual(uint256 price) external {
        storedPrice = price;
    }

    /**
     * @dev EDGE6: TWAP read but with window from storage (configurable via governance)
     * Pattern: oracle-005 should NOT flag IF builder detects parameter-like storage
     * Note: This is a limitation test - storage-based windows may or may not be detected
     */
    uint32 public governanceWindow = 1800;

    function getTWAPFromStorageWindow() external returns (uint256) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = governanceWindow; // From storage (governance-controlled)
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        storedPrice = uint256(int256(tickCumulatives[1] - tickCumulatives[0]));
        return storedPrice;
    }

    // =============================================================================
    // VARIATIONS - Different function names, contexts
    // =============================================================================

    /**
     * @dev VAR1: Different naming - getPrice instead of getTWAP
     * Pattern: oracle-005 should FLAG this (hardcoded window)
     */
    function getPrice() external returns (uint256) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = 1800; // HARDCODED
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        storedPrice = uint256(int256(tickCumulatives[1] - tickCumulatives[0]));
        return storedPrice;
    }

    /**
     * @dev VAR2: Different context - collateral valuation
     * Pattern: oracle-005 should FLAG this (hardcoded window)
     */
    function getCollateralValue(address user) external returns (uint256) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = 2400; // HARDCODED 40 minutes
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        uint256 price = uint256(int256(tickCumulatives[1] - tickCumulatives[0]));

        return userCollateral[user] * price / 1e18;
    }

    /**
     * @dev VAR3: Configurable with different parameter name
     * Pattern: oracle-005 should NOT flag (has window parameter)
     */
    function getPriceWithDuration(uint32 duration) external view returns (uint256) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = duration;
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = uniswapV3Pool.observe(secondsAgos);
        return uint256(int256(tickCumulatives[1] - tickCumulatives[0]));
    }

    /**
     * @dev VAR4: Public function calling hardcoded internal (VULNERABLE)
     * Pattern: oracle-005 should FLAG _getTWAPInternal()
     */
    function executeWithInternalTWAP() external returns (uint256) {
        return _getTWAPInternal();
    }

    // =============================================================================
    // HELPER FUNCTIONS
    // =============================================================================

    function _getQuoteAtTick(int24 tick) internal pure returns (uint256) {
        // Simplified price calculation from tick
        if (tick < 0) {
            return 1e18 / uint256(uint24(-tick));
        }
        return uint256(uint24(tick)) * 1e18;
    }
}
