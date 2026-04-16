# Hook Permission Mismatch

## Vulnerability Pattern

**Core Issue:** Hook address lower bits encode required permissions. Mismatch between encoded permissions and implemented functions causes silent failures.

**Vulnerable Pattern:**
```solidity
// Hook implements afterSwap() but AFTER_SWAP_FLAG not encoded in address
contract VulnerableHook {
    function afterSwap(PoolKey calldata, ...) external returns (bytes4, int128) {
        // This NEVER executes - permission not encoded in address
        // Protocol fee logic silently skipped
    }
}
```

**Why Vulnerable:**
- Hook address encodes permissions via CREATE2 salt
- PoolManager checks address bits before calling hook
- Missing permission flag = hook function never called
- No revert, silent failure causes logic bypass

**Safe Pattern:**
```solidity
contract SafeHook is BaseHook {
    constructor(IPoolManager _manager) BaseHook(_manager) {
        Hooks.validateHookPermissions(this, Hooks.Permissions({
            afterSwap: true,
            afterSwapReturnsDelta: true
        }));
    }
}
```

## Detection Signals

**Tier A (Deterministic):**
- `implements_hook_function: true`
- `inherits_base_hook: false`
- `validates_permissions_in_constructor: false`

**Behavioral Signature:**
```
IMPLEMENTS_HOOK_FUNCTION -> !VALIDATES_PERMISSIONS -> SKIP_EXECUTION
```

## Fix

1. Inherit from Uniswap BaseHook implementation
2. Call Hooks.validateHookPermissions() in constructor
3. Verify deployed address lower bits match expected permissions
4. Test all hook functions execute as expected

**Real-world:** Doppler Protocol (2024), Cork Protocol (2024)
