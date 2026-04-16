# Rounding Direction Vulnerability Detection

## Semantic Operations

```yaml
operations:
  - PERFORMS_DIVISION
  - PERFORMS_MULTIPLICATION
  - READS_USER_BALANCE
  - READS_POOL_STATE
  - TRANSFERS_VALUE_OUT
```

## Behavioral Signature

```
R:supply->DIV:down->R:bal->MUL:amount->W:out
```

## Detection Properties

```yaml
properties:
  uses_division: true
  rounding_direction: down  # or missing explicit rounding
  affects_value_transfer: true
  in_critical_accounting: true
  precision_sensitive: true
```

## Preconditions

- Division operation in value calculation pathway
- Rounding direction inconsistent with security model
- User can manipulate denominator via donations
- Dust amounts can exploit rounding errors
- No minimum threshold checks

## Detection Signals (Tier A - Deterministic)

### Pattern: Vulnerable Rounding

```yaml
all:
  - property: uses_division
    value: true
  - property: rounds_down_user_benefit
    value: false  # should round down for user withdrawals
  - has_operation: READS_POOL_STATE
  - has_operation: TRANSFERS_VALUE_OUT
none:
  - property: has_minimum_threshold
    value: true
  - property: explicit_rounding_up
    value: true
```

### Critical Functions

Functions that:
- Calculate share-to-asset conversions
- Compute pool token amounts
- Determine withdrawal quantities
- Scale token amounts across decimals

## LLM Reasoning Signals (Tier B)

Questions for LLM analysis:

1. "Does the rounding direction favor the protocol or the user in withdrawals?"
2. "Can a user manipulate the denominator before division via donations?"
3. "Are there minimum deposit/withdrawal thresholds?"
4. "Is rounding direction explicitly specified or implicit via division?"
5. "Can dust-level donations cause significant rounding errors?"

## Safe Properties

```yaml
safe_properties:
  has_minimum_threshold: true
  rounds_up_protocol_favor: true  # for user withdrawals
  uses_safe_math_library: true
  prevents_dust_donations: true
```
