# Detection: Cross-Function Reentrancy

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| state_write_after_external_call | true | YES |
| has_reentrancy_guard | false | YES |
| shared_state_variables | >1 function | YES |
| visibility | public, external | YES |

## Operation Sequences

**Vulnerable:**
- `F1: R:bal -> X:out | F2: R:bal -> W:state` (Function 1 calls out, Function 2 reads stale)
- `F1: R:state -> X:call | F2: M:state` (Different function modifies during reentrancy)

**Safe:**
- Global nonReentrant modifier on all state-modifying functions
- State isolation between functions

## Detection Strategy

1. Identify functions with external calls
2. Identify state variables read/written by those functions
3. Find OTHER functions that access the same state variables
4. Check if reentrancy guard covers ALL related functions
5. Flag if guard is missing from any function in the group

## Multi-Function Analysis Required

Cross-function reentrancy requires analyzing the contract holistically:

```
Function A: reads balance -> external call -> writes balance
Function B: reads balance -> performs action based on balance

Attacker: Call A -> during A's external call, re-enter via B
```

## False Positive Indicators

- Global reentrancy lock covering all external functions
- State variables are contract-specific (no user balances)
- All related functions are internal/private
