# Patterns: Sequencer Uptime

## Vulnerable Pattern

```solidity
// VULNERABLE: No sequencer uptime check on L2
contract VulnerableLending {
    AggregatorV3Interface public priceFeed;

    function liquidate(address user) external {
        // Directly reads price without checking sequencer status
        (, int256 price, , , ) = priceFeed.latestRoundData();

        uint256 collateralValue = userCollateral[user] * uint256(price) / 1e8;

        // May use stale price from before sequencer went down
        if (collateralValue < userDebt[user]) {
            _liquidate(user);
        }
    }
}
```

## Safe Pattern (Sequencer Check)

```solidity
// Safe: Checks sequencer uptime before using oracle
contract SafeLending {
    AggregatorV3Interface public priceFeed;
    AggregatorV3Interface public sequencerUptimeFeed;
    uint256 public constant GRACE_PERIOD = 3600; // 1 hour

    function getPrice() public view returns (uint256) {
        // Check sequencer uptime first
        (, int256 answer, uint256 startedAt, , ) =
            sequencerUptimeFeed.latestRoundData();

        // answer == 0: Sequencer is up
        // answer == 1: Sequencer is down
        bool isSequencerUp = answer == 0;
        require(isSequencerUp, "Sequencer is down");

        // Enforce grace period after sequencer comes back up
        uint256 timeSinceUp = block.timestamp - startedAt;
        require(timeSinceUp > GRACE_PERIOD, "Grace period not elapsed");

        // Now safe to read price
        (
            uint80 roundId,
            int256 price,
            ,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = priceFeed.latestRoundData();

        require(price > 0, "Invalid price");
        require(answeredInRound >= roundId, "Stale round");
        require(block.timestamp - updatedAt < 3600, "Stale price");

        return uint256(price);
    }

    function liquidate(address user) external {
        uint256 price = getPrice();  // Safe with sequencer check
        // ... liquidation logic
    }
}
```

## Safe Pattern (With Fallback)

```solidity
contract RobustLending {
    AggregatorV3Interface public priceFeed;
    AggregatorV3Interface public sequencerUptimeFeed;
    uint256 public lastValidPrice;
    uint256 public lastPriceTimestamp;
    uint256 public constant MAX_PRICE_AGE = 86400; // 24 hours

    function getPrice() public view returns (uint256) {
        // Try to get live price with sequencer check
        (bool success, uint256 livePrice) = _tryGetLivePrice();

        if (success) {
            return livePrice;
        }

        // Fallback to cached price if sequencer is down
        require(lastValidPrice > 0, "No fallback price");
        require(
            block.timestamp - lastPriceTimestamp < MAX_PRICE_AGE,
            "Fallback price too old"
        );

        return lastValidPrice;
    }

    function _tryGetLivePrice() internal view returns (bool, uint256) {
        // Check sequencer status
        (, int256 answer, uint256 startedAt, , ) =
            sequencerUptimeFeed.latestRoundData();

        if (answer != 0) return (false, 0);  // Sequencer down
        if (block.timestamp - startedAt < 3600) return (false, 0);  // Grace period

        // Get price with validation
        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();

        if (price <= 0) return (false, 0);
        if (block.timestamp - updatedAt > 3600) return (false, 0);

        return (true, uint256(price));
    }
}
```

## Variations

### Network-Aware Deployment

```solidity
// Detect L2 and require sequencer check
bool public immutable isL2;
AggregatorV3Interface public sequencerFeed;

constructor(address _sequencerFeed) {
    // Set based on deployment network
    isL2 = _sequencerFeed != address(0);
    if (isL2) {
        sequencerFeed = AggregatorV3Interface(_sequencerFeed);
    }
}

function requireSequencerUp() internal view {
    if (!isL2) return;  // Skip on L1

    (, int256 answer, uint256 startedAt, , ) = sequencerFeed.latestRoundData();
    require(answer == 0, "Sequencer down");
    require(block.timestamp - startedAt > 3600, "Grace period");
}
```
