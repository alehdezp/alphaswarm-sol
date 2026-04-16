# Detection: Forced Ether Reception via Selfdestruct

## Overview
Contracts can be forced to receive ether via `selfdestruct()` without triggering fallback or receive functions, breaking balance-dependent invariants.

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| has_strict_equality_check | true | YES |
| checks_balance | true | YES |
| uses_balance_in_logic | true | YES |

## Semantic Operations

**Vulnerable Pattern:**
- `READS_BALANCE` with strict equality check
- `COMPARES_BALANCE` with internal accounting variable
- No assumption that balance can increase externally

**Safe Pattern:**
- Use >= instead of == for balance checks
- Maintain internal accounting separate from balance
- Handle unexpected balance increases gracefully

## Behavioral Signatures

- `R:balance->CMP:==->REVERT` - Strict equality causes revert
- `assert(balance == accounting)` - Broken invariant

## Detection Checklist

1. Contract uses strict equality (==) with address(this).balance
2. Contract logic depends on balance matching internal state
3. No handling for unexpected balance increases
4. Critical function blocked if balance != expected

## False Positive Indicators

- Balance check uses >= or <= instead of ==
- Contract explicitly handles forced ether
- Balance used only for informational purposes
- Logic continues even if balance check fails
