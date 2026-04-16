# Hook Callback Reentrancy

## Vulnerability Pattern

**Core Issue:** Uniswap V4 hooks can reenter via unlockCallback during pool operations, bypassing standard reentrancy guards.

**Vulnerable Pattern:**
```solidity
// Standard reentrancy guard doesn't protect callback path
contract VulnerableIntegration {
    bool locked;

    function doSwap() external {
        require(!locked, "Reentrancy");
        locked = true;

        poolManager.unlock(data);  // Hook executes here
        // State update after hook callback completes

        locked = false;
    }

    function unlockCallback(bytes calldata) external returns (bytes memory) {
        // Malicious hook can call back into unlockCallback
        // Reentrancy guard bypassed via different entry point
    }
}
```

**Why Vulnerable:**
- Hook's beforeSwap/afterSwap execute during pool.unlock()
- Malicious hook calls back into victim's unlockCallback
- Standard reentrancy mutex doesn't protect callback path
- State inconsistent during callback execution

**Safe Pattern:**
```solidity
contract SafeIntegration {
    bool locked;
    bool inCallback;

    function doSwap() external {
        require(!locked, "Reentrancy");
        locked = true;
        poolManager.unlock(data);
        locked = false;
    }

    function unlockCallback(bytes calldata) external returns (bytes memory) {
        require(!inCallback, "Callback reentrancy");
        inCallback = true;
        // Safe operations
        inCallback = false;
    }
}
```

## Detection Signals

**Tier A (Deterministic):**
- `implements_unlock_callback: true`
- `has_callback_reentrancy_guard: false`
- `interacts_with_hooks: true`

**Behavioral Signature:**
```
UNLOCK -> HOOK_EXECUTES -> CALLBACK_REENTRY -> STATE_MANIPULATION
```

## Fix

1. Add separate reentrancy guard for callback path
2. Complete all state updates before unlock call
3. Use nonReentrant on both entry and callback functions
4. Validate callback caller is expected PoolManager

**Real-world:** Bunni V2 (2024)
