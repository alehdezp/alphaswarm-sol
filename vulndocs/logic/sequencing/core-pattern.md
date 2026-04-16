# L2 Transaction Sequencing Issues

## Vulnerability Pattern

**Core Issue:** L2 retryable transactions can execute out of order, breaking state dependencies between operations.

**Vulnerable Pattern:**
```solidity
// L1 to L2 messaging via retryable tickets
function retry(bytes calldata data) external {
    // No nonce check - executes in any order
    // No ordering enforcement
    processMessage(data);  // State assumptions may be violated
}
```

**Why Vulnerable:**
- Retryable tickets can be redeemed in any order
- Transaction A depends on state from transaction B
- If A executes before B, state assumptions violated
- Double-spend or DoS possible

**Safe Pattern:**
```solidity
uint256 public nextExpectedNonce;

function retry(uint256 nonce, bytes calldata data) external {
    require(nonce == nextExpectedNonce, "Out of order");
    nextExpectedNonce++;
    processMessage(data);
}
```

## Detection Signals

**Tier A (Deterministic):**
- `uses_retryable_transactions: true`
- `validates_execution_order: false`
- `has_state_dependencies: true`

**Behavioral Signature:**
```
SUBMIT_TX(A) -> SUBMIT_TX(B) -> RETRY(B) -> RETRY(A) -> STATE_INCONSISTENT
```

## Fix

1. Add nonce validation for sequential execution
2. Check state preconditions before retry execution
3. Make retry operations idempotent where possible
4. Use receipt-based confirmation for dependencies

**Real-world:** Arbitrum Outages (2023-12, 2023-06)
