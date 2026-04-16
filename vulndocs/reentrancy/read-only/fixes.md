# Fixes: Read-Only Reentrancy

## Recommended Fixes

### 1. Use Manipulation-Resistant Oracles

**Effectiveness:** High
**Complexity:** Medium

Use TWAP oracles or Chainlink instead of spot prices from pools.

### 2. Check Reentrancy Flags

**Effectiveness:** High
**Complexity:** Low

Some protocols expose reentrancy status that can be checked.

```solidity
// For Curve pools
require(!curvePool.is_killed(), "Pool in callback");
```

### 3. Time-Weighted Calculations

**Effectiveness:** High
**Complexity:** Medium

Use time-weighted average prices to resist manipulation.
