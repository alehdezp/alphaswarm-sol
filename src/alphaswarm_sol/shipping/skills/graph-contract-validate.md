---
name: vrs-graph-contract-validate
description: |
  Contract validation skill for VRS Graph Interface v2 compliance. Validates that all LLM-facing outputs conform to the schema and evidence requirements.

  Invoke when:
  - Validating query results before consumption
  - Checking pattern outputs for evidence compliance
  - Auditing omission metadata completeness
  - Debugging contract violations

slash_command: vrs:graph-contract-validate
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
---

# VRS Graph Contract Validate Skill

You are the **VRS Graph Contract Validate** skill, responsible for ensuring all Graph Interface v2 outputs comply with the contract schema and evidence requirements.

## How to Invoke

```bash
/vrs-graph-contract-validate <output-file>
/vrs-graph-contract-validate results.json --strict
/vrs-graph-contract-validate --check-evidence
```

---

## Purpose

Phase 5.9 establishes the Graph Interface Contract v2 as the canonical LLM-facing output schema. This skill validates outputs against that contract, ensuring:

1. **Schema compliance** - Output matches v2 JSON Schema
2. **Evidence enforcement** - All matched clauses have evidence refs
3. **Omission completeness** - Cut sets and coverage scores are present
4. **Build hash consistency** - Evidence refs use correct build hash
5. **Clause matrix alignment** - matched/failed/unknown lists match matrix

---

## Contract Enforcement Rules

### Rule 1: Evidence or Evidence-Missing

Every matched clause MUST have either:
- `evidence_refs` with at least one reference, OR
- Entry in `evidence_missing` with reason code

```yaml
# VALID - has evidence
clause_matrix:
  - clause: "visibility_public"
    status: matched
    evidence_refs:
      - { file: "Token.sol", line: 42, node_id: "N-001", snippet_id: "EVD-abc123", build_hash: "abc123def456" }

# VALID - has evidence_missing entry
clause_matrix:
  - clause: "taint_user_input"
    status: matched
    evidence_refs: []
    omission_refs: ["taint_dataflow_unavailable"]
```

### Rule 2: Unknown Implies Omission

Every unknown clause MUST have omission reason:

```yaml
clause_matrix:
  - clause: "guard_dominance"
    status: unknown
    evidence_refs: []
    omission_refs: ["dominance_unknown"]
```

### Rule 3: Build Hash Consistency

All evidence refs must use the same `build_hash` as the top-level output:

```yaml
interface_version: "2.0.0"
build_hash: "abc123def456"
findings:
  - evidence_refs:
      - { build_hash: "abc123def456" }  # MUST match
```

### Rule 4: Coverage Score Required

All subgraph outputs must include `coverage_score`:

```yaml
omissions:
  coverage_score: 0.85
  cut_set: []
  excluded_edges: []
  slice_mode: standard
```

### Rule 5: Clause List Completeness

All clauses in `matched_clauses`, `failed_clauses`, `unknown_clauses` must appear in `clause_matrix`:

```yaml
matched_clauses: ["visibility_public", "has_external_call"]
failed_clauses: ["has_reentrancy_guard"]
unknown_clauses: ["guard_dominance"]
clause_matrix:
  - { clause: "visibility_public", status: matched }
  - { clause: "has_external_call", status: matched }
  - { clause: "has_reentrancy_guard", status: failed }
  - { clause: "guard_dominance", status: unknown }
```

---

## Validation Process

### Step 1: Load Output

```bash
# Load output file
alphaswarm query validate results.json
```

### Step 2: Schema Validation

Check against `schemas/graph_interface_v2.json`:

```python
from alphaswarm_sol.llm.interface_contract import validate_output

is_valid, errors = validate_output(output, strict=True)
```

### Step 3: Semantic Validation

Beyond schema, check semantic rules:
- Evidence linkage
- Omission reasons
- Build hash consistency
- Coverage bounds (0.0-1.0)

### Step 4: Report Violations

```markdown
## Contract Violations

### Evidence Missing (Rule 1)
- Finding[0].clause_matrix[2]: matched clause "taint_user_input" has no evidence

### Unknown Without Omission (Rule 2)
- Finding[1].clause_matrix[0]: unknown clause "guard_dominance" has no omission reason

### Build Hash Mismatch (Rule 3)
- Finding[0].evidence_refs[0]: build_hash "xyz789" != expected "abc123def456"
```

---

## Unknowns Budget Gating

The contract enforces unknowns budget to prevent low-confidence findings:

| Budget | Limit | Effect |
|--------|-------|--------|
| max_ratio | 0.3 | Max 30% of clauses can be unknown |
| max_absolute | 2 | Max 2 unknown clauses per finding |
| critical_clauses | configurable | These clauses cannot be unknown |

When budget exceeded:
```yaml
insufficient_evidence: true
```

---

## Evidence Missing Reason Codes

| Code | Meaning |
|------|---------|
| `taint_dataflow_unavailable` | Taint analysis not available |
| `dominance_unknown` | Dominance cannot be proven |
| `interprocedural_truncated` | Cross-function analysis truncated |
| `external_return_untracked` | External return values not tracked |
| `aliasing_unknown` | Storage aliasing uncertain |
| `sanitizer_uncertain` | Sanitizer effect uncertain |
| `legacy_no_evidence` | Legacy v1 output without evidence |

---

## Omission Reason Codes

| Code | Meaning |
|------|---------|
| `modifier_not_traversed` | Modifier body not analyzed |
| `inherited_not_traversed` | Inherited function not analyzed |
| `external_target_unknown` | External call target unknown |
| `budget_exceeded` | Token budget exceeded |
| `depth_limit_reached` | Analysis depth limit reached |
| `library_excluded` | Library code excluded |

---

## V1 to V2 Migration

Legacy v1 outputs can be transformed via compatibility shim:

```python
from alphaswarm_sol.llm.interface_contract import transform_v1_to_v2

v2_output = transform_v1_to_v2(v1_output)
```

The shim:
- Adds default omission metadata
- Generates evidence IDs for legacy refs
- Emits deprecation warnings

---

## Integration Points

This skill integrates with:

| Component | Integration |
|-----------|-------------|
| `PatternEngine` | Validates pattern outputs |
| `QueryExecutor` | Validates query results |
| `Orchestration` | Validates routing context |
| `Agents` | Validates agent inputs |

---

## When to Invoke

Invoke this skill when:
- **Before consumption**: Validate results before agent reasoning
- **After generation**: Validate outputs before serialization
- **Debug failures**: Diagnose why outputs fail contract
- **Audit compliance**: Check historical outputs

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-ordering-proof` | Dominance-based ordering verification |
| `/vrs-taint-extend` | Taint source/sink analysis |
| `/vrs-audit` | Full audit workflow |

---

## Write Boundaries

This skill is restricted to writing in:
- `.claude/vrs/` - VRS working directory
- `.beads/` - Bead storage directory

All other directories are read-only.

---

## Notes

- Contract validation is a fail-fast gate - no partial compliance
- Evidence is required, not optional
- Missing signals must be marked unknown, not safe
- Build hash ensures reproducibility
- Unknowns budget prevents low-confidence verdicts
- This skill CAN be invoked by orchestrators (disable-model-invocation: false)
