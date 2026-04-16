# Patterns: TWAP Manipulation

## Vulnerable Pattern (Short Window)

```solidity
// VULNERABLE: 10-minute TWAP is too short
contract VulnerableTWAP {
    IUniswapV3Pool public pool;
    uint32 public constant TWAP_PERIOD = 600; // 10 minutes - TOO SHORT!

    function getPrice() public view returns (uint256) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = TWAP_PERIOD;
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = pool.observe(secondsAgos);
        int56 tickDelta = tickCumulatives[1] - tickCumulatives[0];
        int24 avgTick = int24(tickDelta / int56(uint56(TWAP_PERIOD)));

        // Short window can be manipulated with sustained trading
        return OracleLibrary.getQuoteAtTick(avgTick, 1e18, token0, token1);
    }
}
```

## Vulnerable Pattern (Low Liquidity Pool)

```solidity
// VULNERABLE: Uses low-liquidity pool for TWAP
contract LowLiquidityTWAP {
    // Pool with only $500k TVL
    IUniswapV3Pool public thinPool;

    function getPrice() public view returns (uint256) {
        // Even with long TWAP window, low liquidity makes manipulation cheap
        return _getTwapPrice(thinPool, 3600);
    }
}
```

## Safe Pattern (Long Window + Validation)

```solidity
contract SafeTWAP {
    IUniswapV3Pool public pool;
    AggregatorV3Interface public chainlinkFeed;
    uint32 public constant TWAP_PERIOD = 3600; // 1 hour
    uint256 public constant MAX_DEVIATION = 500; // 5%

    function getPrice() public view returns (uint256) {
        uint256 twapPrice = _getTwapPrice();
        uint256 chainlinkPrice = _getChainlinkPrice();

        // Cross-validate TWAP against Chainlink
        uint256 deviation = _calculateDeviation(twapPrice, chainlinkPrice);
        require(deviation <= MAX_DEVIATION, "Price deviation too high");

        // Use average of both sources
        return (twapPrice + chainlinkPrice) / 2;
    }

    function _getTwapPrice() internal view returns (uint256) {
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = TWAP_PERIOD;
        secondsAgos[1] = 0;

        (int56[] memory tickCumulatives, ) = pool.observe(secondsAgos);
        int56 tickDelta = tickCumulatives[1] - tickCumulatives[0];
        int24 avgTick = int24(tickDelta / int56(uint56(TWAP_PERIOD)));

        return OracleLibrary.getQuoteAtTick(avgTick, 1e18, token0, token1);
    }

    function _getChainlinkPrice() internal view returns (uint256) {
        (, int256 price, , uint256 updatedAt, ) = chainlinkFeed.latestRoundData();
        require(price > 0 && block.timestamp - updatedAt < 3600, "Invalid");
        return uint256(price);
    }

    function _calculateDeviation(uint256 a, uint256 b) internal pure returns (uint256) {
        if (a > b) {
            return (a - b) * 10000 / b;
        }
        return (b - a) * 10000 / a;
    }
}
```

## Safe Pattern (Multi-Pool TWAP)

```solidity
contract MultiPoolTWAP {
    IUniswapV3Pool[] public pools;
    uint32 public constant TWAP_PERIOD = 1800; // 30 minutes

    function getMedianPrice() public view returns (uint256) {
        uint256[] memory prices = new uint256[](pools.length);

        for (uint256 i = 0; i < pools.length; i++) {
            prices[i] = _getTwapPrice(pools[i]);
        }

        // Use median to resist single-pool manipulation
        return _median(prices);
    }

    function _median(uint256[] memory arr) internal pure returns (uint256) {
        // Sort and return middle value
        _sort(arr);
        uint256 mid = arr.length / 2;
        if (arr.length % 2 == 0) {
            return (arr[mid - 1] + arr[mid]) / 2;
        }
        return arr[mid];
    }
}
```

## Variations

### Dynamic Window Based on Volatility

```solidity
// Increase TWAP window during high volatility
function getDynamicTwapPeriod() public view returns (uint32) {
    uint256 recentVolatility = _calculateRecentVolatility();

    if (recentVolatility > HIGH_VOLATILITY_THRESHOLD) {
        return 7200; // 2 hours during high vol
    } else if (recentVolatility > MEDIUM_VOLATILITY_THRESHOLD) {
        return 3600; // 1 hour during medium vol
    }
    return 1800; // 30 minutes during low vol
}
```
