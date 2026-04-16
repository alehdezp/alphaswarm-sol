# Pattern Advanced Guide

**Advanced pattern features: Tier A+B matching, edge requirements, and PCP v2.**

**Prerequisites:** [Pattern Basics](patterns-basics.md)

---

## Pattern Development Skills And Agents

**Canonical registries:**
- Skills: `src/alphaswarm_sol/skills/registry.yaml`
- Agents: `src/alphaswarm_sol/agents/catalog.yaml`

**Pattern development skills:**
- `vrs-discover`, `vrs-research`, `vrs-ingest-url`, `vrs-add-vulnerability`
- `pattern-forge`, `vrs-refine`, `vrs-test-pattern`, `pattern-verify`

**Pattern development agents:**
- `vrs-pattern-architect` → `.claude/agents/vrs-pattern-architect.md`
- `vrs-test-conductor` → `src/alphaswarm_sol/shipping/agents/vrs-test-conductor.md`

---

## Using the Pattern Architect Agent

The `vrs-pattern-architect` agent automates pattern design:

```
User Request → vrs-pattern-architect
    ├── Research vulnerability (CVEs, exploits, audits)
    ├── Read builder.py for available properties
    ├── Check existing patterns for conventions
    ├── Design: core signal + discriminators + exclusions
    ├── Create pattern YAML
    └── Invoke workflow test harness for quality scoring
```

### Pattern Quality Lifecycle

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   DRAFT     │───►│   READY     │───►│  EXCELLENT  │
│  <70% prec  │    │  ≥70% prec  │    │  ≥90% prec  │
│  <50% rec   │    │  ≥50% rec   │    │  ≥85% rec   │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## Edge Requirements

Match based on graph relationships:

```yaml
edges:
  # Function writes to privileged state variable
  - type: WRITES_STATE
    direction: out
    target_type: StateVariable
    target_match:
      property: security_tags
      op: contains_any
      value: [owner, role, admin]

  # Function receives tainted input
  - type: FUNCTION_INPUT_TAINTS_STATE
    direction: out
```

---

## Path Requirements

Match based on multi-hop graph traversal:

```yaml
paths:
  # Reachable from public entry point
  - from_type: Function
    from_property: visibility
    from_value: public
    edge_types: [CALLS_INTERNAL]
    max_depth: 5
```

---

## Tier A + B Matching

Tier A (deterministic) and Tier B (LLM-enhanced) work together:

| Mode | Description | Use Case |
|------|-------------|----------|
| `tier_a_only` | Only Tier A conditions | Standard deterministic |
| `tier_a_required` | Tier A must match, Tier B confirms | Business logic |
| `tier_b_enhances` | Tier A filters, Tier B detects | Semantic inconsistency |

### Example

```yaml
match:
  tier_a:
    all:
      - property: visibility
        op: in
        value: [public, external]
      - has_operation: TRANSFERS_VALUE_OUT
      - sequence_order:
          before: TRANSFERS_VALUE_OUT
          after: WRITES_USER_BALANCE
    none:
      - property: has_reentrancy_guard
        value: true

  tier_b:
    any:
      - has_risk_tag: reentrancy

aggregation:
  mode: tier_a_required
```

### Tier B Pattern Types

| Pattern Type | Risk Tags |
|--------------|-----------|
| Business Logic | `intent_deviation`, `business_logic_mismatch` |
| Invariant Violation | `invariant_violation`, `unbacked_shares` |
| Semantic Inconsistency | `naming_behavior_mismatch` |
| Trust Assumption | `implicit_trust_boundary` |

---

## Operation Matching

```yaml
# Single operation
- has_operation: TRANSFERS_VALUE_OUT

# All required
- has_all_operations:
    - TRANSFERS_VALUE_OUT
    - WRITES_USER_BALANCE

# Sequence ordering (CEI violation)
- sequence_order:
    before: TRANSFERS_VALUE_OUT
    after: WRITES_USER_BALANCE
```

---

## Severity Guidelines

| Severity | Criteria | Examples |
|----------|----------|----------|
| **critical** | Direct fund loss, no conditions | Unprotected withdrawAll |
| **high** | Fund loss with conditions | CEI violation without guard |
| **medium** | Partial impact or difficult | Missing slippage check |
| **low** | Edge case or minor | Deprecated function use |
| **info** | Best practice | Missing events |

---

## Quality Checklist

### Accuracy
- [ ] Core condition is SEMANTIC, not syntactic
- [ ] At least one `none` condition excludes safe patterns
- [ ] No reliance on naming conventions

### Completeness
- [ ] Description explains "why" not just "what"
- [ ] Attack scenarios documented
- [ ] Fix recommendations provided

### Implementation-Agnostic
- [ ] Would survive code renaming
- [ ] Works with different modifier patterns
- [ ] Works with inheritance variations

---

## Pattern Migration (v1 → v2)

### Before (Name-dependent)

```yaml
# BAD: Relies on naming
match:
  all:
    - property: label
      op: regex
      value: ".*[Ww]ithdraw.*"
```

### After (Operation-based)

```yaml
# GOOD: Uses semantic operations
match:
  tier_a:
    all:
      - has_operation: TRANSFERS_VALUE_OUT
      - has_operation: WRITES_USER_BALANCE
```

---

## Pattern Context Pack (PCP) v2

PCPs provide deterministic, evidence-first context for agentic pattern discovery.

**Location:** `vulndocs/{category}/{subcategory}/patterns/{pattern-id}.pcp.yaml`

### Design Principles

| Principle | Description |
|-----------|-------------|
| **Deterministic** | No RAG, no semantic search |
| **Evidence-First** | Every claim references evidence IDs |
| **Unknown != Safe** | Missing signals = unknown |
| **Graph-First** | Semantic operations, not names |

### Required Fields

```yaml
id: pcp-<pattern-id>
version: "2.0"
pattern_id: "<pattern-id>"
name: "<Pattern Name>"
summary: "<Brief description>"

determinism:
  no_rag: true
  no_name_heuristics: true

op_signatures:
  required_ops:
    - "OPERATION_1"
```

### Evidence Gating

For high/critical patterns:

```yaml
witness:
  minimal_required:
    - "EVD-12345678"
  negative_required:
    - "EVD-87654321"

anti_signals:
  - id: "guard.reentrancy"
    guard_type: "reentrancy_guard"
    bypass_notes:
      - "Guard only applies to one entry point"
```

### PCP Lint Rules

| Rule | Severity | Description |
|------|----------|-------------|
| PCP001 | ERROR | Missing required_ops |
| PCP010 | ERROR | no_rag must be true |
| PCP020 | WARN | High/critical missing witnesses |

### Running PCP Validation

```bash
uv run alphaswarm vulndocs validate vulndocs/ --pcp
uv run alphaswarm vulndocs validate vulndocs/ --pcp --strict
```

**Template:** `vulndocs/.meta/templates/pattern_context_pack_v2.yaml`

---

## Related Documentation

- [Pattern Basics](patterns-basics.md) - Pattern fundamentals
- [Pattern Testing Guide](testing.md) - Test and rate patterns
- [Operations Reference](../reference/operations.md) - 20 semantic operations

---

*Version 3.0 | February 2026*
