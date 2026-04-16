# Detection: Weak or Bypassable Modifier

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| has_access_gate | true | NO |
| writes_privileged_state | true | YES |
| visibility | public, external | YES |
| empty_modifier | true | YES |
| modifier_logic_weak | true | YES |

## Semantic Operations

**Vulnerable Pattern:**
- Weak `CHECKS_PERMISSION` followed by `MODIFIES_OWNER`
- Empty modifier before `MODIFIES_CRITICAL_STATE`
- Bypassable check before `MODIFIES_ROLES`

**Safe Pattern:**
- Strong `CHECKS_PERMISSION` with proper comparison
- Multiple redundant checks for critical operations

## Behavioral Signatures

- `G:empty->W:critical` - Empty guard before critical write
- `G:weak->W:owner` - Weak guard before owner modification
- `G:bypassable->W:role` - Bypassable guard before role change

## Detection Checklist

1. Function has a modifier applied
2. Modifier body is empty or contains no require/revert
3. Modifier uses incorrect comparison operator
4. Modifier checks wrong state variable
5. Modifier can be bypassed via state manipulation
6. Modifier logic has logical errors

## False Positive Indicators

- Modifier is intentionally permissive (documented)
- Additional inline checks compensate for weak modifier
- Access control delegated to external verified contract
- Protected by timelock or governance vote
- Modifier combines with other security mechanisms
