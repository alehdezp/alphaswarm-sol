# Fixes: Sequencer Uptime

## Recommended Fixes

### 1. Sequencer Uptime Feed Check

**Effectiveness:** High
**Complexity:** Low

Always check sequencer status before reading price oracles on L2.

```solidity
// Arbitrum Sequencer Uptime Feed
address constant SEQUENCER_FEED = 0xFdB631F5EE196F0ed6FAa767959853A9F217697D;

// Optimism Sequencer Uptime Feed
// address constant SEQUENCER_FEED = 0x371EAD81c9102C9BF4874A9075FFFf170F2Ee389;

AggregatorV3Interface public sequencerUptimeFeed =
    AggregatorV3Interface(SEQUENCER_FEED);

function checkSequencerUp() internal view {
    (, int256 answer, uint256 startedAt, , ) =
        sequencerUptimeFeed.latestRoundData();

    // answer: 0 = up, 1 = down
    require(answer == 0, "Sequencer is down");

    // Enforce grace period
    require(
        block.timestamp - startedAt > GRACE_PERIOD_TIME,
        "Grace period not over"
    );
}
```

### 2. Grace Period Enforcement

**Effectiveness:** High
**Complexity:** Low

Prevent oracle usage immediately after sequencer recovery.

```solidity
uint256 public constant GRACE_PERIOD_TIME = 3600; // 1 hour

function getPrice() public view returns (uint256) {
    // Check sequencer status
    (, int256 answer, uint256 startedAt, , ) =
        sequencerUptimeFeed.latestRoundData();

    bool isSequencerUp = answer == 0;
    if (!isSequencerUp) {
        revert SequencerDown();
    }

    // Make sure grace period has passed
    uint256 timeSinceUp = block.timestamp - startedAt;
    if (timeSinceUp < GRACE_PERIOD_TIME) {
        revert GracePeriodNotOver();
    }

    // Safe to read oracle
    return _getOraclePrice();
}
```

### 3. Network-Aware Oracle Wrapper

**Effectiveness:** High
**Complexity:** Medium

Create a reusable oracle wrapper that handles L2-specific checks.

```solidity
contract L2SafeOracle {
    AggregatorV3Interface public priceFeed;
    AggregatorV3Interface public sequencerFeed;
    uint256 public gracePeriod;
    uint256 public maxStaleness;

    constructor(
        address _priceFeed,
        address _sequencerFeed,
        uint256 _gracePeriod,
        uint256 _maxStaleness
    ) {
        priceFeed = AggregatorV3Interface(_priceFeed);
        sequencerFeed = AggregatorV3Interface(_sequencerFeed);
        gracePeriod = _gracePeriod;
        maxStaleness = _maxStaleness;
    }

    function getPrice() external view returns (uint256) {
        _checkSequencer();
        return _getValidatedPrice();
    }

    function _checkSequencer() internal view {
        (, int256 answer, uint256 startedAt, , ) =
            sequencerFeed.latestRoundData();

        require(answer == 0, "Sequencer down");
        require(block.timestamp - startedAt > gracePeriod, "Grace period");
    }

    function _getValidatedPrice() internal view returns (uint256) {
        (
            uint80 roundId,
            int256 price,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        require(price > 0, "Invalid price");
        require(answeredInRound >= roundId, "Stale round");
        require(block.timestamp - updatedAt < maxStaleness, "Stale price");

        return uint256(price);
    }
}
```

## Best Practices

1. **Always check sequencer on L2** - Every L2 deployment needs this
2. **Use appropriate grace periods** - 1 hour is standard, adjust based on oracle
3. **Handle downtime gracefully** - Pause liquidations vs using stale data
4. **Test for both networks** - L1 and L2 behavior may differ
5. **Monitor sequencer health** - Off-chain alerts for downtime events

## Testing Recommendations

1. Mock sequencer down state in tests
2. Test grace period edge cases
3. Verify behavior during/after simulated downtime
4. Test fallback mechanisms
5. Simulate L1-submitted transactions during downtime
