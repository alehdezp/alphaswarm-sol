# Patterns: Stale Price Data

## Vulnerable Pattern

```solidity
// VULNERABLE: No staleness checks on Chainlink data
function getPrice() public view returns (uint256) {
    (, int256 price, , , ) = priceFeed.latestRoundData();
    return uint256(price);  // Could be hours or days old!
}

function liquidate(address user) external {
    uint256 price = getPrice();  // May use stale price
    uint256 collateralValue = userCollateral[user] * price / 1e18;

    if (collateralValue < userDebt[user] * liquidationThreshold / 10000) {
        // Unfair liquidation with outdated price
        _liquidate(user);
    }
}
```

## Safe Pattern (Full Validation)

```solidity
uint256 public constant MAX_STALENESS = 3600; // 1 hour

function getPrice() public view returns (uint256) {
    (
        uint80 roundId,
        int256 price,
        ,
        uint256 updatedAt,
        uint80 answeredInRound
    ) = priceFeed.latestRoundData();

    // Validate price is positive
    require(price > 0, "Invalid price");

    // Validate round is complete
    require(updatedAt > 0, "Round not complete");
    require(answeredInRound >= roundId, "Stale round");

    // Validate freshness
    require(block.timestamp - updatedAt < MAX_STALENESS, "Price too old");

    return uint256(price);
}
```

## Safe Pattern (With Fallback)

```solidity
AggregatorV3Interface public primaryFeed;
AggregatorV3Interface public fallbackFeed;
uint256 public constant MAX_STALENESS = 3600;

function getPrice() public view returns (uint256) {
    (uint256 price, bool isValid) = _tryGetPrice(primaryFeed);

    if (!isValid) {
        (price, isValid) = _tryGetPrice(fallbackFeed);
        require(isValid, "All oracles stale");
    }

    return price;
}

function _tryGetPrice(AggregatorV3Interface feed)
    internal view returns (uint256, bool)
{
    try feed.latestRoundData() returns (
        uint80 roundId,
        int256 price,
        uint256,
        uint256 updatedAt,
        uint80 answeredInRound
    ) {
        if (price <= 0) return (0, false);
        if (answeredInRound < roundId) return (0, false);
        if (block.timestamp - updatedAt >= MAX_STALENESS) return (0, false);
        return (uint256(price), true);
    } catch {
        return (0, false);
    }
}
```

## Variations

### Heartbeat-Aware Staleness

```solidity
// Different assets have different heartbeats
mapping(address => uint256) public assetHeartbeat;

function getAssetPrice(address asset) public view returns (uint256) {
    AggregatorV3Interface feed = assetFeeds[asset];
    (, int256 price, , uint256 updatedAt, ) = feed.latestRoundData();

    uint256 heartbeat = assetHeartbeat[asset];
    require(heartbeat > 0, "Asset not configured");
    require(block.timestamp - updatedAt < heartbeat * 2, "Stale price");

    return uint256(price);
}
```
