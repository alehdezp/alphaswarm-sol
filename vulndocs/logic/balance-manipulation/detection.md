# Detection: Balance Manipulation

## Overview
Detect vulnerabilities arising from incorrect assumptions about contract balance behavior.

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| has_strict_equality_check | true | YES |
| checks_balance | true | YES |
| uses_balance_in_logic | true | YES |
| reads_balance_in_payable | true | MEDIUM |

## Semantic Operations

**Vulnerable Patterns:**
- `READS_BALANCE` with strict equality (==)
- `READS_BALANCE` during payable function execution
- `COMPARES_BALANCE` with internal accounting without inequality
- `USES_BALANCE` in state machine transitions

**Safe Patterns:**
- Internal accounting separate from balance
- Inequality checks (>=, <=) instead of equality
- Balance used only for informational purposes

## Detection Checklist

1. Contract reads address(this).balance
2. Balance used in conditional logic or assertions
3. Strict equality check with balance
4. No handling for unexpected balance changes
5. Balance read during msg.value transaction
