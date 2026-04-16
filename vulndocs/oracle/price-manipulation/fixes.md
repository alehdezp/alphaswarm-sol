# Fixes: Price Manipulation

## Recommended Fixes

### 1. Use TWAP Oracles

**Effectiveness:** High
**Complexity:** Medium

Time-weighted average prices resist single-block manipulation.

```solidity
// Uniswap V3 TWAP implementation
function getTwapPrice(uint32 twapInterval) public view returns (uint256) {
    require(twapInterval >= 1800, "TWAP window too short");

    uint32[] memory secondsAgos = new uint32[](2);
    secondsAgos[0] = twapInterval;
    secondsAgos[1] = 0;

    (int56[] memory tickCumulatives, ) = pool.observe(secondsAgos);
    int56 tickDelta = tickCumulatives[1] - tickCumulatives[0];
    int24 avgTick = int24(tickDelta / int56(uint56(twapInterval)));

    return OracleLibrary.getQuoteAtTick(avgTick, 1e18, token0, token1);
}
```

### 2. Use Decentralized Oracles

**Effectiveness:** High
**Complexity:** Low

Chainlink and similar oracles aggregate from multiple off-chain sources.

```solidity
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

AggregatorV3Interface internal priceFeed;

function getChainlinkPrice() public view returns (uint256) {
    (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
    require(price > 0, "Invalid price");
    require(block.timestamp - updatedAt < 3600, "Stale price");
    return uint256(price);
}
```

### 3. Price Sanity Bounds

**Effectiveness:** Medium
**Complexity:** Low

Limit how much price can change between updates.

```solidity
uint256 public lastPrice;
uint256 public constant MAX_PRICE_CHANGE = 1000; // 10%

function updatePrice(uint256 newPrice) internal {
    if (lastPrice > 0) {
        uint256 change = newPrice > lastPrice
            ? (newPrice - lastPrice) * 10000 / lastPrice
            : (lastPrice - newPrice) * 10000 / lastPrice;
        require(change <= MAX_PRICE_CHANGE, "Price change too large");
    }
    lastPrice = newPrice;
}
```

### 4. Flash Loan Detection

**Effectiveness:** Medium
**Complexity:** Medium

Detect and block same-block price manipulation.

```solidity
mapping(address => uint256) public lastActionBlock;

modifier noFlashLoan() {
    require(lastActionBlock[msg.sender] < block.number, "Flash loan detected");
    lastActionBlock[msg.sender] = block.number;
    _;
}
```

## Best Practices

1. **Never use spot prices** - Always use TWAP with >= 30 minute window
2. **Multiple price sources** - Aggregate from 2+ independent oracles
3. **Price deviation checks** - Reject outlier prices vs historical average
4. **Delay-based protection** - Require price to be stable across multiple blocks
5. **Circuit breakers** - Pause protocol if price moves > 20% in short time

## Testing Recommendations

1. Write flash loan attack simulation tests
2. Test with extreme pool imbalances
3. Verify TWAP window is sufficient
4. Test price sanity bounds with edge cases
5. Simulate multi-block sustained manipulation
