# Classic Reentrancy

## Vulnerability Pattern

**Core Issue:** External call executes before state update, allowing callback to re-enter function with stale state.

**Vulnerable Pattern:**
```solidity
function withdraw() external {
    uint256 bal = balances[msg.sender];
    (bool success,) = msg.sender.call{value: bal}("");  // External call FIRST
    require(success);
    balances[msg.sender] = 0;  // State update AFTER - TOO LATE
}
```

**Why Vulnerable:**
- Attacker receives callback during external call
- Callback re-enters withdraw() with unchanged balance
- State update bypassed on each reentry

**Safe Pattern:**
```solidity
function withdraw() external nonReentrant {
    uint256 bal = balances[msg.sender];
    balances[msg.sender] = 0;  // State update FIRST
    (bool success,) = msg.sender.call{value: bal}("");  // External call LAST
    require(success);
}
```

## Detection Signals

**Tier A (Deterministic):**
- `state_write_after_external_call: true`
- `has_reentrancy_guard: false`
- `visibility: [public, external]`
- `has_all_operations: [TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE]`

**Behavioral Signature:**
```
R:bal -> X:out -> W:bal  (vulnerable)
R:bal -> W:bal -> X:out  (safe - CEI)
```

## Fix

1. Apply CEI pattern: state changes BEFORE external calls
2. Add `ReentrancyGuard.nonReentrant` modifier
3. For ERC777/ERC1155: account for token callbacks

**Real-world:** DAO (2016), Lendf.me (2020), Cream (2021), Fei (2022)
