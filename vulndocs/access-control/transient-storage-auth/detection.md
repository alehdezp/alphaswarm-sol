# Detection: Transient Storage Authentication Bypass

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| uses_transient_storage | true | YES |
| checks_permission | true | YES |
| visibility | public, external | YES |
| state_write_before_check | true | YES |

## Semantic Operations

**Vulnerable Sequence:**
- `WRITES_TRANSIENT_STORAGE -> READS_TRANSIENT_STORAGE -> CHECKS_PERMISSION`
- `CALLS_EXTERNAL(callback) -> OVERWRITES_TRANSIENT_SLOT -> BYPASSES_AUTH`

**Safe Sequence:**
- `READS_STORAGE -> CHECKS_PERMISSION -> MODIFIES_STATE`
- `VALIDATES_SIGNATURE -> CHECKS_PERMISSION -> EXECUTES`

## Behavioral Signatures

- `W:tstore->R:tload->CHECK:auth` - Transient storage used for auth
- `X:callback->W:tstore(0x1)->R:tload(0x1)->VALIDATES` - Attacker overwrites auth slot

## Detection Checklist

1. Function uses `tload`/`tstore` opcodes (EIP-1153)
2. Transient storage slot read for authentication
3. External call or callback occurs before/during auth check
4. Attacker can control transient storage value
5. No state variable or signature-based fallback auth
6. Vulnerable in same-transaction attack scenarios

## Code Pattern (Vulnerable)

```solidity
// VULNERABLE: Transient storage auth in callback
function uniswapV3SwapCallback(
    int256 amount0Delta,
    int256 amount1Delta,
    bytes calldata data
) external {
    // Read pool address from transient storage (slot 0x1)
    address pool;
    assembly {
        pool := tload(0x1)  // VULNERABLE: Can be overwritten by attacker
    }

    // Authentication check
    require(msg.sender == pool, "Unauthorized");

    // Execute swap logic...
}
```

## Attack Vector

1. Attacker triggers callback function
2. Before auth check executes, attacker writes to transient slot
3. Auth check reads attacker-controlled value from transient storage
4. Check passes with malicious value
5. Unauthorized operation executes

## False Positive Indicators

- Transient storage used for gas optimization, not authentication
- State variables (`address public trustedPool`) used for auth
- Signature verification (`ecrecover`) used instead
- Immutable addresses checked
- Reentrancy guard prevents slot manipulation during execution
