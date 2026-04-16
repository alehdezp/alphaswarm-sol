# Insufficient Pool Key Validation

## Vulnerability Pattern

**Core Issue:** Hook functions accept arbitrary pool keys without validation. Attacker creates malicious pool with fake currencies to drain hook.

**Vulnerable Pattern:**
```solidity
function beforeSwap(PoolKey calldata key, ...) external {
    // Accepts ANY pool key - attacker controlled
    currency0 = key.currency0;  // Could be malicious token
    currency1 = key.currency1;  // Recursive LP token
    // Proceeds to transfer/manipulate funds
}
```

**Why Vulnerable:**
- Hook callable from any pool referencing it
- No validation of currency addresses in pool key
- Attacker deploys malicious pool with hook address
- Hook interacts with attacker-controlled tokens

**Safe Pattern:**
```solidity
mapping(PoolId => bool) public validPools;

function beforeSwap(PoolKey calldata key, ...) external {
    PoolId poolId = key.toId();
    require(validPools[poolId], "Invalid pool");
    // Safe - only whitelisted pools accepted
}
```

## Detection Signals

**Tier A (Deterministic):**
- `accepts_pool_key: true`
- `validates_pool_id: false`
- `checks_currency_addresses: false`

**Behavioral Signature:**
```
ACCEPTS_POOL_KEY -> !VALIDATES_POOL_ID -> USES_CURRENCY -> VULNERABLE
```

## Fix

1. Whitelist specific pool IDs in mapping
2. Validate currency0/currency1 against expected addresses
3. Verify hook address in key matches contract
4. Initialize valid pools in constructor/setup

**Real-world:** Doppler Protocol (2024)
