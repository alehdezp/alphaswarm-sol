# Fixes: Stale Price Data

## Recommended Fixes

### 1. Complete Chainlink Validation

**Effectiveness:** High
**Complexity:** Low

Always validate all return values from `latestRoundData()`.

```solidity
uint256 public constant MAX_STALENESS = 3600; // 1 hour

function getValidatedPrice() public view returns (uint256) {
    (
        uint80 roundId,
        int256 price,
        ,
        uint256 updatedAt,
        uint80 answeredInRound
    ) = priceFeed.latestRoundData();

    require(price > 0, "Invalid price");
    require(updatedAt > 0, "Round not complete");
    require(answeredInRound >= roundId, "Stale round");
    require(block.timestamp - updatedAt < MAX_STALENESS, "Stale price");

    return uint256(price);
}
```

### 2. Asset-Specific Heartbeats

**Effectiveness:** High
**Complexity:** Medium

Different assets have different update frequencies.

```solidity
// Chainlink heartbeats vary by asset:
// ETH/USD: 1 hour
// BTC/USD: 1 hour
// USDC/USD: 24 hours (stablecoins update less frequently)

mapping(address => uint256) public maxStaleness;

function setMaxStaleness(address feed, uint256 staleness) external onlyOwner {
    require(staleness >= 60 && staleness <= 86400, "Invalid staleness");
    maxStaleness[feed] = staleness;
}

function getPrice(address feed) public view returns (uint256) {
    uint256 staleness = maxStaleness[feed];
    require(staleness > 0, "Feed not configured");

    (, int256 price, , uint256 updatedAt, ) =
        AggregatorV3Interface(feed).latestRoundData();

    require(block.timestamp - updatedAt < staleness, "Stale");
    return uint256(price);
}
```

### 3. Fallback Oracle System

**Effectiveness:** High
**Complexity:** High

Use multiple oracle sources with automatic failover.

```solidity
address[] public oracleSources;
uint256 public constant MIN_VALID_SOURCES = 2;

function getMedianPrice() public view returns (uint256) {
    uint256[] memory prices = new uint256[](oracleSources.length);
    uint256 validCount = 0;

    for (uint256 i = 0; i < oracleSources.length; i++) {
        (uint256 price, bool isValid) = _getValidatedPrice(oracleSources[i]);
        if (isValid) {
            prices[validCount++] = price;
        }
    }

    require(validCount >= MIN_VALID_SOURCES, "Insufficient valid oracles");
    return _median(prices, validCount);
}
```

### 4. Circuit Breaker on Stale Data

**Effectiveness:** Medium
**Complexity:** Low

Pause critical operations when oracle data is stale.

```solidity
bool public circuitBreakerActive;

modifier whenOracleHealthy() {
    require(!circuitBreakerActive, "Circuit breaker active");
    _;
}

function checkOracleHealth() external {
    (, , , uint256 updatedAt, ) = priceFeed.latestRoundData();

    if (block.timestamp - updatedAt > MAX_STALENESS) {
        circuitBreakerActive = true;
        emit CircuitBreakerTriggered(updatedAt);
    }
}
```

## Best Practices

1. **Check all return values** - Don't ignore roundId, updatedAt, answeredInRound
2. **Asset-appropriate thresholds** - Stablecoins can tolerate longer staleness
3. **Multiple oracle sources** - Fallback when primary is stale
4. **Monitor oracle health** - Off-chain monitoring with alerts
5. **Graceful degradation** - Pause risky operations vs using bad data

## Testing Recommendations

1. Mock stale oracle responses in tests
2. Test circuit breaker activation
3. Verify fallback oracle switching
4. Test edge cases around staleness threshold
5. Simulate high gas / network congestion scenarios
