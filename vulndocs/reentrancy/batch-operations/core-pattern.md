# Batch Operation Reentrancy

## Vulnerability Pattern

**Core Issue:** Single operation is safe, but looped/batched execution amplifies reentrancy through repeated callbacks.

**Vulnerable Pattern:**
```solidity
function claimAll(uint256[] calldata ids) external {
    for (uint i = 0; i < ids.length; i++) {
        uint256 reward = rewards[ids[i]][msg.sender];
        (bool success,) = msg.sender.call{value: reward}("");  // Callback per iteration
        rewards[ids[i]][msg.sender] = 0;  // State update per iteration
    }
}
// Attacker: callback re-enters with remaining loop iterations pending
```

**Why Vulnerable:**
- Each loop iteration: external call before state update
- Callback can manipulate state for remaining iterations
- Amplification: N iterations = N reentry opportunities

**Safe Pattern:**
```solidity
function claimAll(uint256[] calldata ids) external nonReentrant {
    uint256 total;
    for (uint i = 0; i < ids.length; i++) {
        total += rewards[ids[i]][msg.sender];
        rewards[ids[i]][msg.sender] = 0;  // Clear ALL state first
    }
    (bool success,) = msg.sender.call{value: total}("");  // Single transfer
}
```

## Detection Signals

**Tier A (Deterministic):**
- `external_calls_in_loop: true`
- `has_reentrancy_guard: false`
- `state_write_after_external_call: true`

**Behavioral Signature:**
```
LOOP_START -> R:bal -> X:untrusted -> W:bal -> LOOP_CONTINUE
```

## Fix

1. Aggregate values in loop, single external call after loop
2. Clear all state before any external interaction
3. `nonReentrant` guard on batch functions

**Real-world:** Penpie ($27M, 2024)
