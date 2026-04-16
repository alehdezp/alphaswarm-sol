# Pattern Context Pack (PCP) v2 Specification

**Version:** 2.0
**Status:** Normative Reference
**Last Updated:** 2026-01-27

---

## Overview

Pattern Context Pack (PCP) v2 is a deterministic, evidence-first context schema for agentic pattern discovery. PCP v2 is cacheable, schema-validated, and graph-first.

**Key Invariants:**
- **Deterministic** serialization and hashing
- **No name heuristics** - behavior over names
- **No RAG** - no retrieval-augmented generation
- **Evidence-first** - explicit and stable canonical IDs
- **Unknown != Safe** - missing signals marked "unknown", never inferred as safe

## Schema Model

PCP v2 is implemented as `PatternContextPackV2` in `src/alphaswarm_sol/vulndocs/schema.py`.

JSON Schema available at: `schemas/pattern_context_pack_v2.json`

---

## Canonical YAML Template

```yaml
pattern_context_pack:
  # === IDENTITY (Required) ===
  id: "pcp-<pattern_id>"           # Unique PCP identifier
  version: "2.0"                   # Schema version (must be 2.x)
  pattern_id: "vm-001"             # Associated pattern ID
  name: "Classic Reentrancy"       # Human-readable name
  summary: "State write after external call enables re-entry before balance update."
  scope: "Function"                # Function | Contract | Transaction

  # === DETERMINISM CONSTRAINTS ===
  determinism:
    no_rag: true                   # No retrieval-augmented generation
    no_name_heuristics: true       # No function/variable name heuristics
    serialization_order:           # Canonical ordering for hashing
      - pcp
      - slice
      - protocol
      - evidence
    hash_seed: "graph_hash + pcp_version + pattern_id"

  # === TOKEN BUDGET ===
  budget:
    pcp_max_tokens: 800            # Max tokens for PCP itself
    context_max_tokens: 2200       # Max for full context
    cheap_pass_tokens: 1200        # Budget for cheap/fast pass
    verify_pass_tokens: 1800       # Budget for verification pass
    deep_pass_tokens: 2400         # Budget for deep analysis

  # === EVIDENCE WEIGHTS ===
  evidence_weights:
    required: []                   # Evidence refs that MUST exist
    strong: []                     # Strongly supporting evidence
    weak: []                       # Weakly supporting evidence
    optional: []                   # Nice-to-have evidence

  # === WITNESS REQUIREMENTS ===
  witness:
    minimal_required: []           # Minimal evidence set for plausible match
    negative_required: []          # Evidence that must NOT exist

  # === EXPLOIT MODELING ===
  preconditions:
    - id: "pre-001"
      description: "Caller is user-controlled"
      evidence_refs: []

  exploit_steps:
    - id: "step-001"
      description: "External call occurs before balance update"
      required_ops:
        - "TRANSFERS_VALUE_OUT"
        - "WRITES_USER_BALANCE"
      evidence_refs: []

  impact_invariants:
    - id: "impact-001"
      description: "User balance can be drained"
      evidence_refs: []

  # === OPERATION SIGNATURES (Required) ===
  op_signatures:
    required_ops:                  # MUST have at least one
      - "TRANSFERS_VALUE_OUT"
      - "WRITES_USER_BALANCE"
    ordering_variants:             # Valid orderings
      - id: "seq-001"
        description: "CEI violated"
        sequence:
          - "READS_USER_BALANCE"
          - "TRANSFERS_VALUE_OUT"
          - "WRITES_USER_BALANCE"
    forbidden_ops: []              # Ops that must NOT exist

  # === ANTI-SIGNALS (Guards/Mitigations) ===
  anti_signals:
    - id: "guard.reentrancy"
      guard_type: "reentrancy_guard"      # See guard types below
      severity: "critical"                # How strongly this negates
      expected_context: "nonReentrant modifier present"
      evidence_refs: []
      bypass_notes:
        - "Guard only applies to one entry point"
        - "Cross-contract reentrancy may bypass"

  # === COUNTERFACTUALS (Tier-B What-If) ===
  counterfactuals:
    - id: "cf-001"
      if_removed: "guard.reentrancy"      # Anti-signal ID to remove
      becomes_true: true                  # Pattern would hold if removed
      notes: "Pattern would hold if guard is removed"

  # === GUARD TAXONOMY ===
  guard_taxonomy:
    - id: "g-001"
      type: "reentrancy_guard"
      description: "Global reentrancy lock"
      expected_ops:
        - "CHECKS_REENTRANCY_GUARD"
      bypass_notes:
        - "May not protect cross-contract calls"

  # === ORDERING VARIANTS (Convenience Duplicate) ===
  ordering_variants:
    - id: "ov-001"
      description: "CEI violated"
      sequence:
        - "READS_USER_BALANCE"
        - "TRANSFERS_VALUE_OUT"
        - "WRITES_USER_BALANCE"

  # === RISK ENVELOPE ===
  risk_envelope:
    asset_type: "native"           # native | token | governance | mixed | unknown
    trust_boundary: "user->contract"  # See trust boundaries below
    value_movement: "out"          # in | out | internal | bidirectional | unknown
    severity_floor: "high"         # Minimum severity

  # === COMPOSITION HINTS ===
  composition_hints:
    co_occurs_with:                # Patterns that frequently co-occur
      - "vm-003"
      - "auth-004"
    combine_with:                  # Patterns to combine for compound detection
      - "access-gate-missing"

  # === ECONOMIC PLACEHOLDERS (Phase 5.11) ===
  economic_placeholders:
    value_flows: []                # Populated in Phase 5.11
    incentive_hooks: []            # Populated in Phase 5.11
    role_assumptions: []           # Populated in Phase 5.11
    offchain_dependencies: []      # Populated in Phase 5.11
    risk_pre_score: "medium"       # critical | high | medium | low | unknown

  # === EVIDENCE REQUIREMENTS ===
  evidence_requirements:
    node_types:                    # Required node types
      - "Function"
      - "Call"
    edge_types:                    # Required edge types
      - "CALLS"
      - "WRITES_STATE"
    path_constraints: []           # Path constraint expressions

  # === UNKNOWNS POLICY (Critical) ===
  unknowns_policy:
    missing_required: "unknown"    # unknown | fail | warn
    missing_optional: "unknown"
    missing_anti_signal: "unknown"
```

---

## Field Reference

### Identity Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `id` | Yes | string | Unique PCP identifier, format: `pcp-<pattern_id>` |
| `version` | Yes | string | Must be `2.0` or `2.x` |
| `pattern_id` | Yes | string | Associated pattern ID |
| `name` | Yes | string | Human-readable pattern name |
| `summary` | Yes | string | Brief pattern summary |
| `scope` | No | enum | `Function` (default), `Contract`, or `Transaction` |

### Determinism Constraints

| Field | Default | Description |
|-------|---------|-------------|
| `no_rag` | `true` | No retrieval-augmented generation allowed |
| `no_name_heuristics` | `true` | No function/variable name heuristics |
| `serialization_order` | `[pcp, slice, protocol, evidence]` | Canonical ordering |
| `hash_seed` | `graph_hash + pcp_version + pattern_id` | Cache key formula |

### Token Budget

| Field | Default | Range | Description |
|-------|---------|-------|-------------|
| `pcp_max_tokens` | 800 | 100-2000 | Max tokens for PCP itself |
| `context_max_tokens` | 2200 | 500-6000 | Max for full context |
| `cheap_pass_tokens` | 1200 | 500-3000 | Budget for cheap pass |
| `verify_pass_tokens` | 1800 | 1000-4000 | Budget for verify pass |
| `deep_pass_tokens` | 2400 | 1500-6000 | Budget for deep pass |

**Constraint:** `cheap_pass < verify_pass < deep_pass`

### Evidence Weights

Categorizes evidence refs by importance for multi-pass detection.

| Category | Description |
|----------|-------------|
| `required` | Evidence refs that MUST exist for a match |
| `strong` | Evidence refs that strongly support a match |
| `weak` | Evidence refs that weakly support a match |
| `optional` | Evidence refs that are nice-to-have |

### Witness Requirements

| Field | Description |
|-------|-------------|
| `minimal_required` | Minimal evidence set that must exist for a plausible match |
| `negative_required` | Evidence that must NOT exist for a match to hold |

### Operation Signatures

| Field | Required | Description |
|-------|----------|-------------|
| `required_ops` | Yes (min 1) | Semantic operations required for this pattern |
| `ordering_variants` | No | Valid operation orderings (multiple allowed) |
| `forbidden_ops` | No | Semantic operations that must NOT be present |

### Anti-Signals

Anti-signals indicate that a pattern does NOT apply due to some guard/mitigation.

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique anti-signal identifier |
| `guard_type` | Yes | Guard type classification (see below) |
| `severity` | No | How severely this negates the pattern |
| `expected_context` | No | Expected context when present |
| `evidence_refs` | No | Evidence references |
| `bypass_notes` | No | How this guard might be bypassed |

**Guard Types:**
- `reentrancy_guard` - Reentrancy lock (nonReentrant)
- `access_control` - Access control check (onlyOwner, etc.)
- `pausable` - Pause mechanism
- `timelock` - Time-based lock
- `oracle_check` - Oracle validation
- `slippage_check` - Slippage protection
- `balance_check` - Balance validation
- `custom` - Custom guard type

### Risk Envelope

| Field | Values | Description |
|-------|--------|-------------|
| `asset_type` | `native`, `token`, `governance`, `mixed`, `unknown` | Type of asset at risk |
| `trust_boundary` | See below | Trust boundary being crossed |
| `value_movement` | `in`, `out`, `internal`, `bidirectional`, `unknown` | Direction of value |
| `severity_floor` | `critical`, `high`, `medium`, `low` | Minimum severity |

**Trust Boundaries:**
- `user->contract` - User to contract
- `contract->contract` - Contract to contract
- `external->internal` - External to internal
- `admin->user` - Admin to user
- `unknown` - Unknown trust boundary

### Economic Placeholders

Reserved for Phase 5.11 economic context integration.

| Field | Description |
|-------|-------------|
| `value_flows` | Value flow descriptors |
| `incentive_hooks` | Incentive mechanism hooks |
| `role_assumptions` | Role/actor assumptions |
| `offchain_dependencies` | Off-chain dependency flags |
| `risk_pre_score` | Pre-computed risk score (`critical`, `high`, `medium`, `low`, `unknown`) |

### Unknowns Policy

**Critical:** Never infer safety from missing context. Missing = unknown.

| Field | Values | Description |
|-------|--------|-------------|
| `missing_required` | `unknown`, `fail`, `warn` | How to treat missing required evidence |
| `missing_optional` | `unknown`, `fail`, `warn` | How to treat missing optional evidence |
| `missing_anti_signal` | `unknown`, `fail`, `warn` | How to treat missing anti-signals |

---

## Validation Rules

### Required Fields

1. `id` - Must start with `pcp-`
2. `pattern_id` - Non-empty string
3. `name` - Non-empty string
4. `summary` - Non-empty string
5. `op_signatures.required_ops` - Must have at least one operation

### Version Constraint

- `version` must match pattern `^2\.\d+$` (e.g., "2.0", "2.1")

### Budget Ordering

- `cheap_pass_tokens < verify_pass_tokens < deep_pass_tokens`

### Soft Recommendations

- High/critical severity patterns SHOULD have at least one anti-signal OR negative witness
- Tier B/C claims SHOULD have non-empty `witness.minimal_required`

---

## Defaults

All optional sections default to empty lists or structures with safe defaults:

```yaml
determinism:
  no_rag: true
  no_name_heuristics: true
  serialization_order: [pcp, slice, protocol, evidence]
  hash_seed: "graph_hash + pcp_version + pattern_id"

budget:
  pcp_max_tokens: 800
  context_max_tokens: 2200
  cheap_pass_tokens: 1200
  verify_pass_tokens: 1800
  deep_pass_tokens: 2400

evidence_weights:
  required: []
  strong: []
  weak: []
  optional: []

witness:
  minimal_required: []
  negative_required: []

unknowns_policy:
  missing_required: "unknown"
  missing_optional: "unknown"
  missing_anti_signal: "unknown"
```

---

## Migration Rules (v1 to v2)

The migration shim `migrate_pcp_v1_to_v2()` handles automatic conversion:

### Identity Migration

| v1 Field | v2 Field | Transformation |
|----------|----------|----------------|
| `id` | `id` | Prefix with `pcp-` if missing |
| `id` | `pattern_id` | Extract pattern ID |
| `name` | `name` | Preserve |
| `description` | `summary` | Use as summary |
| `scope` | `scope` | Preserve (default: Function) |

### Operation Migration

| v1 Field | v2 Field | Transformation |
|----------|----------|----------------|
| `required_ops` | `op_signatures.required_ops` | Direct mapping |
| `semantic_operations` | `op_signatures.required_ops` | Fallback source |
| `operation_sequence` | `op_signatures.ordering_variants[0].sequence` | Wrap in variant |
| `forbidden_ops` | `op_signatures.forbidden_ops` | Direct mapping |

### Guard Migration

| v1 Field | v2 Field | Transformation |
|----------|----------|----------------|
| `guards` (string) | `anti_signals` | Convert to anti-signal with `custom` type |
| `guards` (object) | `anti_signals` | Map fields directly |

### Evidence Migration

| v1 Field | v2 Field | Transformation |
|----------|----------|----------------|
| `minimal_witness` | `witness.minimal_required` | Direct mapping |
| `negative_witness` | `witness.negative_required` | Direct mapping |
| `evidence_refs` | Preserve in respective sections | Keep canonical IDs |

### New Fields (Defaults Applied)

All new v2 fields receive explicit defaults:

```yaml
determinism:
  no_rag: true
  no_name_heuristics: true

unknowns_policy:
  missing_required: "unknown"
  missing_optional: "unknown"
  missing_anti_signal: "unknown"

economic_placeholders:
  value_flows: []
  incentive_hooks: []
  role_assumptions: []
  offchain_dependencies: []
  risk_pre_score: "unknown"
```

---

## Usage Examples

### Python: Create PCP v2

```python
from alphaswarm_sol.vulndocs.schema import PatternContextPackV2, PCPOpSignatures

pcp = PatternContextPackV2(
    id="pcp-reentrancy-001",
    pattern_id="reentrancy-001",
    name="Classic Reentrancy",
    summary="State write after external call enables re-entry",
    op_signatures=PCPOpSignatures(
        required_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"]
    )
)
```

### Python: Load with v1 Migration

```python
from pathlib import Path
from alphaswarm_sol.vulndocs.schema import load_pcp_v2

# Automatically migrates v1 data to v2
pcp = load_pcp_v2(Path("patterns/reentrancy.yaml"))
print(f"Loaded: {pcp.id}, version={pcp.version}")
```

### Python: Export JSON Schema

```python
from pathlib import Path
from alphaswarm_sol.vulndocs.schema import export_pcp_v2_json_schema

export_pcp_v2_json_schema(Path("schemas/pattern_context_pack_v2.json"))
```

### Python: Compute Cache Key

```python
graph_hash = "abc123def456"
cache_key = pcp.compute_cache_key(graph_hash)
print(f"Cache key: {cache_key}")  # e.g., "7f3a8b2c1d4e5f6g"
```

---

## Related Documents

- [Pattern Authoring Guide](../guides/patterns.md)
- [Semantic Operations Reference](operations.md)
- [VKG Properties Reference](properties.md)
- [VulnDocs Framework Guide](../guides/vulndocs.md)

---

## Changelog

### v2.0 (2026-01-27)

- Initial v2 specification
- Added anti-signals with guard taxonomy
- Added witness requirements (minimal + negative)
- Added evidence weights for prioritized analysis
- Added ordering variants for multiple valid sequences
- Added risk envelope for semantic risk framing
- Added economic placeholders for Phase 5.11
- Added explicit unknowns policy
- Implemented v1 to v2 migration shim
- JSON Schema export support
