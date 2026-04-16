# Cross-Function Reentrancy

## Vulnerability Pattern

**Core Issue:** Reentrancy callback exploits shared state across multiple functions, bypassing per-function guards.

**Vulnerable Pattern:**
```solidity
function withdraw() external nonReentrant {
    uint256 bal = balances[msg.sender];
    (bool success,) = msg.sender.call{value: bal}("");
    balances[msg.sender] = 0;
}

function transfer(address to, uint256 amt) external {  // NO guard
    require(balances[msg.sender] >= amt);
    balances[msg.sender] -= amt;
    balances[to] += amt;
}
// Attacker: withdraw() -> callback -> transfer() with stale balance
```

**Why Vulnerable:**
- Only withdraw() has reentrancy guard
- Callback can call transfer() which shares balances mapping
- Guard on one function doesn't protect shared state access

**Safe Pattern:**
```solidity
function withdraw() external nonReentrant { ... }
function transfer(address to, uint256 amt) external nonReentrant { ... }
// All functions accessing shared state MUST have guard
```

## Detection Signals

**Tier A (Deterministic):**
- `has_reentrancy_guard: partial` (some functions unguarded)
- `shares_state_with_guarded_function: true`
- `visibility: [public, external]`

**Behavioral Signature:**
```
F1:R:bal -> F1:X:out -> [callback] -> F2:R:bal -> F2:W:bal
```

## Fix

1. Apply `nonReentrant` to ALL functions accessing shared state
2. CEI pattern in every function, not just entry points
3. Global lock for related functions (same modifier instance)

**Real-world:** GMX V1 (2023), Lendf.me (2020)
