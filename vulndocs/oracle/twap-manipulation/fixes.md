# Fixes: TWAP Manipulation

## Recommended Fixes

### 1. Use Longer TWAP Windows

**Effectiveness:** High
**Complexity:** Low

Minimum 30-minute window, prefer 1+ hour for critical operations.

```solidity
// Minimum recommended: 30 minutes
// Better: 1 hour
// Best for high-value: 2+ hours
uint32 public constant TWAP_PERIOD = 3600; // 1 hour

function getTwapPrice() public view returns (uint256) {
    require(TWAP_PERIOD >= 1800, "TWAP too short");

    uint32[] memory secondsAgos = new uint32[](2);
    secondsAgos[0] = TWAP_PERIOD;
    secondsAgos[1] = 0;

    (int56[] memory tickCumulatives, ) = pool.observe(secondsAgos);
    int56 tickDelta = tickCumulatives[1] - tickCumulatives[0];
    int24 avgTick = int24(tickDelta / int56(uint56(TWAP_PERIOD)));

    return OracleLibrary.getQuoteAtTick(avgTick, 1e18, token0, token1);
}
```

### 2. Cross-Validate with Multiple Sources

**Effectiveness:** High
**Complexity:** Medium

Require TWAP and Chainlink to agree within tolerance.

```solidity
uint256 public constant MAX_DEVIATION_BPS = 500; // 5%

function getValidatedPrice() public view returns (uint256) {
    uint256 twapPrice = _getTwapPrice();
    uint256 chainlinkPrice = _getChainlinkPrice();

    uint256 deviation;
    if (twapPrice > chainlinkPrice) {
        deviation = (twapPrice - chainlinkPrice) * 10000 / chainlinkPrice;
    } else {
        deviation = (chainlinkPrice - twapPrice) * 10000 / twapPrice;
    }

    require(deviation <= MAX_DEVIATION_BPS, "Price sources diverge");

    // Return Chainlink as primary (more manipulation-resistant)
    return chainlinkPrice;
}
```

### 3. Require Minimum Pool Liquidity

**Effectiveness:** Medium
**Complexity:** Medium

Only trust TWAP from sufficiently liquid pools.

```solidity
uint256 public constant MIN_POOL_LIQUIDITY = 10_000_000e18; // $10M

function validatePoolLiquidity(address pool) public view returns (bool) {
    (uint160 sqrtPriceX96, , , , , , ) = IUniswapV3Pool(pool).slot0();
    uint128 liquidity = IUniswapV3Pool(pool).liquidity();

    // Convert to USD value (simplified)
    uint256 liquidityUSD = _calculateLiquidityUSD(sqrtPriceX96, liquidity);

    return liquidityUSD >= MIN_POOL_LIQUIDITY;
}

modifier onlyLiquidPool(address pool) {
    require(validatePoolLiquidity(pool), "Pool liquidity too low");
    _;
}
```

### 4. Implement Price Bounds

**Effectiveness:** Medium
**Complexity:** Low

Reject prices that deviate too much from historical average.

```solidity
uint256 public lastValidPrice;
uint256 public constant MAX_PRICE_CHANGE_BPS = 2000; // 20%

function getPriceWithBounds() public returns (uint256) {
    uint256 newPrice = _getTwapPrice();

    if (lastValidPrice > 0) {
        uint256 change;
        if (newPrice > lastValidPrice) {
            change = (newPrice - lastValidPrice) * 10000 / lastValidPrice;
        } else {
            change = (lastValidPrice - newPrice) * 10000 / lastValidPrice;
        }

        require(change <= MAX_PRICE_CHANGE_BPS, "Price change too large");
    }

    lastValidPrice = newPrice;
    return newPrice;
}
```

### 5. Economic Security Analysis

**Effectiveness:** High
**Complexity:** High

Ensure manipulation cost exceeds potential profit.

```solidity
// Off-chain analysis framework
// Manipulation Cost = Capital * Time * Fee Rate + Arbitrage Loss
// Attack Profit = Protocol Exposure * Price Deviation

// Protocol should ensure:
// Manipulation Cost > Attack Profit * Safety Factor (2-3x)
```

## Best Practices

1. **Minimum 30-minute TWAP** - Longer for higher-value operations
2. **Cross-validate sources** - TWAP + Chainlink agreement
3. **Check pool liquidity** - Only trust deep pools
4. **Bound price changes** - Reject extreme deviations
5. **Economic analysis** - Ensure attack is unprofitable
6. **Monitor anomalies** - Alert on unusual price movements

## Testing Recommendations

1. Simulate multi-block price manipulation
2. Test with varying pool liquidity levels
3. Verify cross-validation rejects divergent prices
4. Test price bounds with historical volatility
5. Calculate theoretical attack profitability
6. Test with real mainnet fork data
