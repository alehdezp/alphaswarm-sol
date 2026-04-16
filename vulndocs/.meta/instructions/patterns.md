# How to Write Patterns

Patterns are YAML files that live in `vulndocs/{category}/{subcategory}/patterns/` and define detection logic for specific vulnerability variants.

## Purpose

Patterns provide:
1. Precise detection logic (graph-based matching)
2. Tiered detection (A: strict, B: LLM-verified, C: label-dependent)
3. Test coverage tracking
4. Bidirectional link to vulnerability folder

## Pattern ID Naming Convention

Format: `{category-abbrev}-{number}-{variant}`

Examples:
- `vm-001-classic` (Value Movement lens, pattern 1, classic variant)
- `oracle-001-twap` (Oracle category, pattern 1, TWAP variant)
- `ac-002-missing` (Access Control, pattern 2, missing checks)

## Required Fields

### Core Identification
```yaml
id: pattern-id
name: "Human-Readable Pattern Name"
severity: critical  # critical, high, medium, low
scope: Function  # Function, Contract, Transaction
```

### Lens Classification
```yaml
lens:
  - LensName1  # E.g., ValueMovement, ExternalInfluence
  - LensName2
```

Available lenses: ValueMovement, ExternalInfluence, AccessControl, StateConsistency, Oracle, Logic, GasOptimization

### VulnDoc Link (CRITICAL)
```yaml
vulndoc: category/subcategory  # Links back to vulnerability folder
```

This field enables bidirectional linking between patterns and vulnerability documentation.

## Match Logic

### Tier A: Strict, Graph-Only
High-confidence detection using only graph properties:

```yaml
match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - has_all_operations:
          - OPERATION_1
          - OPERATION_2
      - sequence_order:
          before: OPERATION_1
          after: OPERATION_2
    none:
      - property: has_protection
        op: eq
        value: true
```

**Operators:** `eq`, `ne`, `in`, `not_in`, `gt`, `lt`, `gte`, `lte`, `contains`

### Tier B: LLM-Verified (Optional)
Exploratory detection requiring LLM reasoning:

```yaml
  tier_b:
    prompt: |
      Analyze if this function exhibits [specific behavior].
      Look for [pattern details].
      Consider edge cases: [list].
```

Use when:
- Pattern too complex for pure graph matching
- Requires semantic understanding beyond graph properties
- Exploratory detection (lower confidence)

### Tier C: Label-Dependent (Optional, Phase 5+)
Detection using semantic labels:

```yaml
  tier_c:
    - has_label: state_mutation.balance_update
    - missing_label: access_control.reentrancy_guard
    - has_any_label:
        - value_flow.external_transfer
        - value_flow.native_transfer
```

Use when:
- Detection depends on semantic labeling
- Requires LLM-generated context (labels)
- Phase 5+ feature

## Optional Fields

### Description
```yaml
description: |
  Clear description of what this pattern detects.
  Why is it a vulnerability?
  What are the consequences?
```

### Confidence
```yaml
confidence: high  # high, medium, low
```

### Test Coverage
```yaml
test_coverage:
  precision: 0.95  # Populated during testing
  recall: 0.90
  status: excellent  # draft, ready, excellent
```

**Status guidelines:**
- `draft`: precision < 70% OR recall < 50%
- `ready`: precision >= 70% AND recall >= 50%
- `excellent`: precision >= 90% AND recall >= 85%

### Tags
```yaml
tags:
  - reentrancy
  - value-transfer
  - cei-violation
```

## Good Example (Complete)

```yaml
# vulndocs/reentrancy/classic/patterns/vm-001-classic.yaml

id: vm-001-classic
name: "Classic Reentrancy (CEI Violation)"
severity: critical
scope: Function
lens:
  - ValueMovement
  - ExternalInfluence

vulndoc: reentrancy/classic

match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - has_all_operations:
          - TRANSFERS_VALUE_OUT
          - WRITES_USER_BALANCE
      - sequence_order:
          before: TRANSFERS_VALUE_OUT
          after: WRITES_USER_BALANCE
    none:
      - property: has_reentrancy_guard
        op: eq
        value: true

  tier_c:
    - has_label: state_mutation.balance_update
    - missing_label: access_control.reentrancy_guard

description: |
  Detects classic reentrancy vulnerability where state is written after
  an external call that transfers value. This violates the Checks-Effects-
  Interactions (CEI) pattern and creates a reentrancy window.

confidence: high

test_coverage:
  precision: 1.0
  recall: 1.0
  status: excellent

tags:
  - reentrancy
  - cei-violation
  - value-transfer
```

## Bad Example (What NOT to do)

```yaml
id: bad-pattern
name: "Reentrancy"

match:
  tier_a:
    all:
      - property: function_name
        op: contains
        value: "withdraw"
```

Problems:
- Uses function name (not semantic)
- Missing required fields (vulndoc, severity, scope, lens)
- No description
- Too vague

## Common Mistakes

### Mistake 1: Missing vulndoc Field
Every pattern MUST have `vulndoc: category/subcategory` to link back to its vulnerability folder.

### Mistake 2: Name-Based Detection
Bad: `function_name: contains: "withdraw"`
Good: `has_all_operations: [TRANSFERS_VALUE_OUT]`

### Mistake 3: Too Broad
Patterns should be specific. If a pattern matches 50% of contracts, it's too broad.

### Mistake 4: No Test Coverage
Patterns without test coverage tracking cannot be validated. Always include the `test_coverage` field.

## Tier Selection Guide

| Detection Type | Tier | When to Use |
|----------------|------|-------------|
| Graph properties only | A | High confidence, deterministic |
| Semantic reasoning needed | B | Complex patterns, exploratory |
| Requires semantic labels | C | Phase 5+ feature, label-dependent |

Most patterns should start with Tier A. Add Tier B/C only if Tier A is insufficient.

## Aggregation Modes

When using multiple tiers:

```yaml
match:
  aggregation_mode: tier_a_required  # Options: tier_a_only, tier_a_required, tier_abc_all, voting
  tier_a: [...]
  tier_c: [...]
```

**Modes:**
- `tier_a_only`: Only Tier A (default if only tier_a present)
- `tier_a_required`: Tier A must match, Tier B/C adds confidence
- `tier_abc_all`: ALL tiers must match (intersection)
- `voting`: Majority vote across tiers

## Template Reference

See `.meta/templates/pattern.yaml` for the full pattern template with all fields.

## Validation

Your pattern should:
- [ ] Have unique ID following naming convention
- [ ] Include required fields (id, name, severity, scope, lens, vulndoc)
- [ ] Use semantic operations in Tier A (not names)
- [ ] Have descriptive name and description
- [ ] Link back to vulnerability folder via vulndoc field
- [ ] Include test_coverage field (even if unpopulated initially)

## Testing Patterns

Test your pattern:
```bash
uv run alphaswarm query "pattern:vm-001-classic" contracts/
```

Measure precision/recall:
```bash
uv run pytest tests/test_*_lens.py -v -k vm-001
```

---

*Patterns are embedded in vulnerability folders for co-location and discoverability.*
