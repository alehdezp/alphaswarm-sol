# Precision Loss Accounting

## Vulnerability Pattern

**Core Issue:** Integer division rounding exploited through micro-operations that individually round to zero but extract value in aggregate.

**Vulnerable Pattern:**
```solidity
function withdraw(uint256 shares) external {
    uint256 assets = shares * totalAssets / totalShares;  // Rounds down
    // shares=1, totalAssets=99, totalShares=100 -> assets=0
    // But user burns 1 share, receiving nothing
    totalShares -= shares;
    // Attacker: deposit tiny, inflate share price, others lose to rounding
}

function deposit(uint256 amount) external {
    uint256 shares = amount * totalShares / totalAssets;  // Rounds down
    // No minimum prevents shares = 0 with value deposited
}
```

**Why Vulnerable:**
- No minimum operation threshold
- Division rounds to zero for small amounts
- Repeated micro-ops accumulate rounding error
- Value extracted through precision drift

**Safe Pattern:**
```solidity
uint256 constant MIN_SHARES = 1e3;  // Minimum share unit

function withdraw(uint256 shares) external {
    require(shares >= MIN_SHARES, "Below minimum");
    uint256 assets = shares.mulDivUp(totalAssets, totalShares);  // Round UP against user
    // ...
}

function deposit(uint256 amount) external {
    uint256 shares = amount.mulDivDown(totalShares, totalAssets);
    require(shares >= MIN_SHARES, "Shares too small");
    // ...
}
```

## Detection Signals

**Tier A (Deterministic):**
- `precision_loss_possible: true`
- `allows_micro_operations: true`
- `has_minimum_threshold: false`

**Behavioral Signature:**
```
R:bal -> SCALE_DOWN(->0) -> W:bal(no_change) -> X:out(actual)
```

## Fix

1. Enforce minimum operation thresholds
2. Round against user (up on withdraw, down on deposit)
3. Use virtual shares offset (ERC4626 inflation attack mitigation)
4. Track dust accumulation

**Real-world:** Sherlock AI Detection (2025)
