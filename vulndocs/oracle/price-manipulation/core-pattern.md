# Flash Loan Oracle Manipulation

## Vulnerability Pattern

**Core Issue:** Flash loan enables spot price manipulation to exploit oracle that reads from manipulated source.

**Vulnerable Pattern:**
```solidity
function getPrice() public view returns (uint256) {
    (uint112 reserve0, uint112 reserve1,) = pair.getReserves();
    return reserve1 * 1e18 / reserve0;  // Spot price from AMM reserves
}

function liquidate(address user) external {
    uint256 price = getPrice();  // Reads manipulated spot price
    uint256 collateralValue = userCollateral[user] * price / 1e18;
    require(collateralValue < debt[user], "Not liquidatable");
    // Attacker: flash loan -> manipulate reserves -> liquidate at wrong price
}
```

**Why Vulnerable:**
- Oracle reads spot price from single block
- Flash loan can move price within transaction
- No time-weighted averaging or bounds checking

**Safe Pattern:**
```solidity
function getPrice() public view returns (uint256) {
    (,int256 answer,,uint256 updatedAt,) = chainlinkFeed.latestRoundData();
    require(updatedAt > block.timestamp - MAX_STALENESS, "Stale price");
    require(answer > 0, "Invalid price");
    return uint256(answer);
}
// Or use TWAP with sufficient window (30min+)
```

## Detection Signals

**Tier A (Deterministic):**
- `reads_spot_price: true`
- `uses_single_block_data: true`
- `has_price_bounds: false`
- `uses_twap: false`

**Behavioral Signature:**
```
FLASH_LOAN -> MANIPULATES_RESERVES -> READS_ORACLE(spot) -> X:out(profit)
```

## Fix

1. Use Chainlink or other decentralized oracle
2. TWAP with 30min+ window for DEX prices
3. Price deviation bounds (max 10% move per block)
4. Multiple oracle sources with median

**Real-world:** Harvest ($34M, 2020), Warp Finance ($7.7M, 2020)
