# Detection: Classic Reentrancy

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| state_write_after_external_call | true | YES |
| has_reentrancy_guard | false | YES |
| visibility | public, external | YES |
| uses_low_level_call | true | NO |

## Operation Sequences

**Vulnerable:**
- `R:bal -> X:out -> W:bal`
- `R:bal -> X:call{value} -> W:bal`

**Safe (CEI Pattern):**
- `R:bal -> W:bal -> X:out`
- `R:bal -> W:bal -> X:call{value}`

## Behavioral Signatures

- `R:bal.*X:out.*W:bal` - Read balance, external call, write balance
- `R:bal.*X:call.*W:bal` - Read balance, low-level call, write balance

## Detection Checklist

1. Function is public/external
2. Function reads user balance or allowance
3. Function makes external call (ETH transfer or contract call)
4. Function writes to balance/state AFTER external call
5. No reentrancy guard modifier present
6. No manual lock variable checked

## False Positive Indicators

- nonReentrant modifier present
- All state writes complete before external call (CEI compliant)
- External call is to trusted contract (hardcoded address)
- Function is marked as internal or private
- Lock variable checked and set before external call
- Balance zeroed before external call in same transaction
