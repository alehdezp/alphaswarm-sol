# Detection: Yala Bridge LayerZero Exploit

## Overview

The Yala Bridge vulnerability can be detected through analysis of cross-chain message handling code. The key detection signals involve the presence of external calls to LayerZero infrastructure combined with insufficient input validation and weak nonce tracking.

## Graph Signals

| Property | Expected | Critical? | Confidence | Description |
|----------|----------|-----------|------------|-------------|
| `calls_external` | true | YES | 0.95 | Makes calls to LayerZero endpoint or relay contracts |
| `calls_untrusted` | true | YES | 0.90 | Calls to external contracts without proper trust verification |
| `reads_external_value` | true | YES | 0.92 | Reads values from LayerZero messages or cross-chain data |
| `validates_input` | false | YES | 0.88 | **CRITICAL**: Missing or insufficient payload validation |
| `has_access_gate` | false | YES | 0.85 | No access control on critical minting/burning operations |
| `writes_privileged_state` | true | YES | 0.93 | Writes to token balances, supply, or bridge state |
| `uses_weak_nonce` | true | YES | 0.82 | Weak nonce tracking or missing replay protection |
| `visibility` | public/external | YES | 0.90 | Bridge receive functions are externally callable |

## Semantic Operation Sequences

### VULNERABLE Pattern
```
READS_EXTERNAL_VALUE
  → CALLS_EXTERNAL
    → WRITES_PRIVILEGED_STATE
```

This sequence indicates:
1. Function reads data from external source (LayerZero message)
2. Function makes external call (to bridge or relay)
3. Function modifies critical state (mints tokens, transfers assets)
4. **NO validation occurs between operations**

### SAFE Pattern
```
VALIDATES_INPUT
  → CHECKS_PERMISSION
    → READS_EXTERNAL_VALUE
      → VALIDATES_INPUT
        → MODIFIES_CRITICAL_STATE
```

This sequence shows:
1. Input parameters validated first
2. Access control checked
3. External data read
4. Payload content validated
5. Only then modify state

### Alternative SAFE Pattern
```
CHECKS_PERMISSION
  → READS_EXTERNAL_VALUE
    → VALIDATES_INPUT
      → TRANSFERS_VALUE_OUT
```

## Behavioral Signatures

Look for these operation patterns in code:

### Vulnerable Signatures
| Signature | Meaning | Risk |
|-----------|---------|------|
| `R:ext->X:bridge->W:bal` | Read external, call bridge, write balance | CRITICAL |
| `R:msg->W:supply` | Read message, write supply (no validation) | CRITICAL |
| `X:lz->W:bal` | Call LayerZero, write balance | HIGH |
| `R:nonce->X:unk->W:crit` | Read weak nonce, call untrusted, write critical | CRITICAL |

### Safe Signatures
| Signature | Meaning |
|-----------|---------|
| `V:sig->V:nonce->X:lz->W:bal` | Validate signature, validate nonce, call LayerZero, write balance |
| `V:src->V:msg->C:perm->W:bal` | Verify source, validate message, check permission, write balance |

## Detection Checklist

For any cross-chain bridge function, verify:

- [ ] **Signature Verification**: Is there ECDSA/BLS signature verification on messages?
  - Look for `ecrecover()`, `_hashTypedDataV4()`, or signature library calls
  - If missing: VULNERABLE

- [ ] **Nonce Tracking**: Is there nonce validation to prevent replays?
  - Look for `lastNonce[chainId]` or similar mappings
  - Check if nonce is compared before processing
  - If missing or not checked: VULNERABLE

- [ ] **Source Chain Validation**: Are messages from trusted chains only?
  - Look for chain ID checks
  - Check for whitelist of authorized endpoints
  - If missing: VULNERABLE

- [ ] **Payload Validation**: Is message payload structure validated?
  - Check for bounds validation on amounts
  - Check for address validation (non-zero, etc.)
  - Look for type checking and format validation
  - If insufficient: VULNERABLE

- [ ] **Access Control**: Who can call critical functions?
  - Look for modifiers like `onlyLzReceiver` or similar
  - Check that only LayerZero endpoint can call
  - If anyone can call: VULNERABLE

- [ ] **State Mutation Ordering**: When is state modified relative to calls?
  - Should be: VALIDATE → AUTHORIZE → CALL → VERIFY RESULT → WRITE STATE
  - If: READ → CALL → WRITE without validation in between: VULNERABLE

## False Positive Indicators

The following patterns indicate this is likely NOT a vulnerability:

1. **Proper Signature Verification**
   - Uses ECDSA with proper recovery
   - Uses BLS signatures
   - Multiple signature requirements
   - Signature expiration checking

2. **Nonce Protection**
   - Persistent nonce mapping per chain
   - Nonce strictly increases
   - Strict equality check: `require(_nonce == lastNonce[_src] + 1)`

3. **Source Validation**
   - Chain ID whitelist enforced
   - Remote address verification
   - Trusted endpoint registration

4. **Strict Input Validation**
   - Amount bounds checking (min/max)
   - Address validation (not zero address)
   - Data format validation (fixed-size structs)
   - Revert on any invalid input

5. **Access Control**
   - `onlyLzReceiver` or equivalent modifier
   - Endpoint address verified before processing
   - Multi-sig guards on state changes

6. **Safe Ordering**
   - All validation completes before external calls
   - External calls complete before state writes
   - Results of external calls verified

## Common Vulnerable Patterns to Look For

### Pattern 1: Direct Message Processing
```solidity
// VULNERABLE: No validation
function lzReceive(uint16 _srcChainId, bytes calldata _srcAddress, uint64 _nonce, bytes calldata _payload) external {
    (uint256 amount, address to) = abi.decode(_payload, (uint256, address));
    balances[to] += amount;  // VULNERABLE: No validation
}
```

### Pattern 2: Weak Nonce Tracking
```solidity
// VULNERABLE: Nonce not checked properly
uint256 nonce = 0;
function lzReceive(uint16 _srcChainId, bytes calldata _srcAddress, uint64 _nonce, bytes calldata _payload) external {
    nonce++;  // VULNERABLE: Only increment, never verify sequence
    (uint256 amount, address to) = abi.decode(_payload, (uint256, address));
    balances[to] += amount;
}
```

### Pattern 3: Missing Source Validation
```solidity
// VULNERABLE: Any chain can send
function lzReceive(uint16 _srcChainId, bytes calldata _srcAddress, uint64 _nonce, bytes calldata _payload) external {
    // VULNERABLE: _srcChainId and _srcAddress not validated
    (uint256 amount, address to) = abi.decode(_payload, (uint256, address));
    require(amount > 0, "Invalid amount");
    balances[to] += amount;
}
```

## Detection Implementation

When analyzing code, look for:

1. **Call Graph Analysis**: `lzReceive()` or similar cross-chain receive functions
2. **Data Flow Analysis**: External value → State modification without validation
3. **Access Control Analysis**: Missing permission checks on critical operations
4. **Nonce Analysis**: Search for nonce-related variables and their usage
5. **Signature Analysis**: Search for signature verification calls

### BSKG Query Example

```sql
FIND functions WHERE
  has_operation(CALLS_EXTERNAL) AND
  has_operation(READS_EXTERNAL_VALUE) AND
  NOT has_operation(VALIDATES_INPUT) AND
  has_operation(WRITES_PRIVILEGED_STATE) AND
  operation_sequence_before(READS_EXTERNAL_VALUE, WRITES_PRIVILEGED_STATE) AND
  NOT has_guard(nonReentrant)
```

## Severity Factors

Increase severity if:
- Unlimited amount can be transferred
- Any address can be the recipient
- Multiple chains can trigger the same function
- No rollback mechanism exists
- Assets are immediately moved to attacker-controlled addresses

Decrease severity (but still keep high/critical) if:
- Limited amount per transaction
- Whitelist of trusted recipients
- Rate limiting applied
- Multi-sig approval required
- Proper staging (escrow) of assets
