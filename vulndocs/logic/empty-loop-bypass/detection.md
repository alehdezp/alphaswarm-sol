# Empty Loop Bypass - Detection

## Detection Signals

**Tier A:**
1. `has_loop_over_array = true` - Function loops over array parameter
2. `no_array_length_check = true` - Missing `require(arr.length > 0)`
3. `validation_in_loop_body = true` - Security check inside loop

**Signature:** `L:array{no_check}->V:validate{in_loop}`

## Vulnerable Pattern

```solidity
// VULNERABLE: Empty array bypasses all signature checks
function batchWithdraw(bytes[] memory signatures) external {
    for (uint i = 0; i < signatures.length; i++) {
        require(verifySignature(signatures[i]));
    }
    // If signatures.length == 0, loop never executes
    _withdrawAll();  // UNAUTHORIZED
}
```

## Safe Pattern

```solidity
// SAFE: Require non-empty
function batchWithdraw(bytes[] memory signatures) external {
    require(signatures.length > 0, "Empty array");  // FIX
    for (uint i = 0; i < signatures.length; i++) {
        require(verifySignature(signatures[i]));
    }
    _withdrawAll();
}
```

## Detection

Search for loops with validation inside but no length check before loop.
