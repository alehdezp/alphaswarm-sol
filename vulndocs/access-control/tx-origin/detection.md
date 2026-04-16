# Detection: tx.origin Authentication

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| uses_tx_origin | true | YES |
| has_access_gate | true | NO |
| writes_privileged_state | true | YES |
| visibility | public, external | YES |

## Semantic Operations

**Vulnerable Pattern:**
- `require(tx.origin == owner)` followed by `MODIFIES_CRITICAL_STATE`
- `require(tx.origin == owner)` followed by `TRANSFERS_VALUE_OUT`

**Safe Pattern:**
- `require(msg.sender == owner)` followed by any privileged operation
- `CHECKS_PERMISSION` using `msg.sender`

## Behavioral Signatures

- `G:tx.origin->W:critical` - tx.origin guard before critical write
- `G:tx.origin->X:call{value}` - tx.origin guard before value transfer
- `tx.origin==owner->W:owner` - tx.origin ownership check

## Detection Checklist

1. Function uses tx.origin in a require/if statement
2. tx.origin is compared against owner/admin/authorized address
3. Function performs privileged operation after check
4. Function is public or external
5. No additional msg.sender check present

## False Positive Indicators

- tx.origin used only in events/logging (not for access control)
- Both tx.origin and msg.sender checked (defense in depth)
- tx.origin used for gas refund recipient (not authorization)
- Function is internal or private (cannot be called externally)
- Contract explicitly designed for EOA-only interaction
