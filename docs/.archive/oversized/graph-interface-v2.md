# Graph Interface Contract v2

**Normative specification for all LLM-facing graph outputs.**

Version: 2.0.0
Status: Normative
Updated: 2026-01-27

---

## Overview

The Graph Interface Contract v2 defines the canonical schema for all LLM-facing outputs in AlphaSwarm.sol. This contract is treated as an **ABI** with:

- **Semver versioning**: Breaking changes increment major version
- **Compatibility shims**: v1 outputs can be transformed to v2 format
- **Fail-fast validation**: Schema violations fail at serialization time
- **Deterministic evidence**: All references tied to build hash

### Scope

This contract applies to:
- CLI query outputs (`alphaswarm query`)
- Pattern engine results
- Orchestration routing contexts
- Agent inputs and evidence packets
- Subgraph extractions

---

## ABI Versioning Rules

### Semver Compatibility

| Version Change | When Applied |
|----------------|--------------|
| **Major (X.0.0)** | Breaking schema changes, removed fields, semantic changes |
| **Minor (X.Y.0)** | Additive fields, new optional features |
| **Patch (X.Y.Z)** | Bug fixes, clarifications, no schema changes |

### Compatibility Guarantees

1. **Major version changes** require migration via compatibility shim
2. **Minor version changes** are forward-compatible (old consumers work)
3. **Patch version changes** have no consumer impact

### Compatibility Shim Contract

When upgrading from v1 to v2, the shim must:
- Map all v1 fields to v2 equivalents
- Apply default values for new required fields
- Emit deprecation warnings for legacy fields
- Preserve semantic meaning of all outputs

---

## Core Schema

### Root Structure

```yaml
interface_version: "2.0.0"           # REQUIRED: Semver version string
build_hash: "<sha256-12>"            # REQUIRED: 12-char graph build hash
timestamp: "<ISO8601>"               # REQUIRED: Generation timestamp

query:                               # REQUIRED: Query metadata
  kind: pattern|logic|flow|edges|fetch
  id: "<string>"
  source: "<raw-query-string>"

summary:                             # REQUIRED: Result summary
  nodes: <int>
  edges: <int>
  findings: <int>
  coverage_score: <float>            # 0.0-1.0
  omissions_present: <bool>
  unknowns_count: <int>

findings: [ <Finding> ]              # REQUIRED: Array of findings (may be empty)

omissions:                           # REQUIRED: Global omission ledger
  coverage_score: <float>
  cut_set: [ <CutSetEntry> ]
  excluded_edges: [ "<EdgeType>" ]
  omitted_nodes: [ "<NodeID>" ]
  slice_mode: standard|debug

debug:                               # OPTIONAL: Debug information
  execution_ms: <int>
  cache_hit: <bool>
  warnings: [ "<string>" ]
```

### Finding Schema

```yaml
id: "<finding-id>"                   # REQUIRED: Unique finding identifier
pattern_id: "<pattern-id>"           # REQUIRED: Pattern that matched
severity: critical|high|medium|low   # REQUIRED: Severity level
confidence: <float>                  # REQUIRED: 0.0-1.0

matched_clauses: [ "<clause>" ]      # REQUIRED: Clauses that matched
failed_clauses: [ "<clause>" ]       # REQUIRED: Clauses that failed
unknown_clauses: [ "<clause>" ]      # REQUIRED: Clauses with unknown status

clause_matrix:                       # REQUIRED: Truth table for all clauses
  - clause: "<clause-id>"
    status: matched|failed|unknown
    evidence_refs: [ <EvidenceRef> ]
    omission_refs: [ "<reason>" ]

evidence_refs: [ <EvidenceRef> ]     # REQUIRED: At least one, or evidence_missing

evidence_missing:                    # REQUIRED if evidence_refs empty
  - reason: "<reason-code>"
    clause: "<clause-id>"
    details: "<explanation>"

omissions:                           # REQUIRED: Finding-specific omissions
  cut_set: [ <CutSetEntry> ]
  excluded_edges: [ "<EdgeType>" ]
  coverage_score: <float>
```

### Evidence Reference Schema

```yaml
file: "<filename.sol>"               # REQUIRED: Source file
line: <int>                          # REQUIRED: Line number (1-indexed)
column: <int>                        # OPTIONAL: Column number (1-indexed)
node_id: "<node-id>"                 # REQUIRED: Graph node identifier
snippet_id: "<EVD-xxx>"              # REQUIRED: Deterministic evidence ID
snippet: "<code-text>"               # OPTIONAL: Code snippet (max 200 chars)
build_hash: "<sha256-12>"            # REQUIRED: Tied to graph build
```

### Omission Ledger Schema

```yaml
coverage_score: <float>              # REQUIRED: 0.0-1.0 coverage ratio
cut_set:                             # REQUIRED: Traversal blockers
  - blocker: "<node-or-edge-id>"
    reason: "<reason-code>"
    impact: "<description>"
excluded_edges: [ "<EdgeType>" ]     # REQUIRED: Omitted edge types
omitted_nodes: [ "<NodeID>" ]        # OPTIONAL: Dropped nodes
slice_mode: standard|debug           # REQUIRED: Current slicing mode
```

---

## Clause Matrix Rules

### Status Definitions

| Status | Meaning | Requirements |
|--------|---------|--------------|
| `matched` | Clause condition satisfied | Must have evidence_refs OR evidence_missing with reason |
| `failed` | Clause condition not satisfied | Must have evidence_refs OR reason in omission_refs |
| `unknown` | Cannot determine status | Must have omission_refs explaining why |

### Invariants

1. **Completeness**: Every clause must appear in exactly one of matched/failed/unknown
2. **Evidence linkage**: Matched clauses MUST have evidence_refs or evidence_missing
3. **Omission linkage**: Unknown clauses MUST have omission_refs
4. **Matrix alignment**: clause_matrix MUST match matched/failed/unknown lists
5. **No orphans**: Every evidence_ref must correspond to a clause

### Clause ID Format

```
<pattern-id>:<clause-type>:<index>

Examples:
- reentrancy-classic:all:0
- reentrancy-classic:none:1
- oracle-stale:any:2
```

---

## Evidence Reference Determinism

### Evidence ID Generation

Evidence IDs are deterministic and reproducible:

```python
def generate_evidence_id(build_hash: str, node_id: str, line: int, column: int = 0) -> str:
    """Generate deterministic evidence ID.

    Format: EVD-<hash-8>
    Where hash = SHA256(build_hash + node_id + line + column)[:8]
    """
    content = f"{build_hash}:{node_id}:{line}:{column}"
    hash_val = hashlib.sha256(content.encode()).hexdigest()[:8]
    return f"EVD-{hash_val}"
```

### Build Hash Binding

- All evidence_refs MUST include the `build_hash` they were generated from
- Evidence refs are only valid for the matching build_hash
- Stale evidence (different build_hash) must be regenerated

---

## Coverage Score Formula

### Definition

```
coverage_score = captured_weight / relevant_weight

Where:
- captured_weight = sum(weight(n) for n in captured_nodes)
- relevant_weight = sum(weight(n) for n in relevant_nodes)
- relevant_nodes = PPR_selected UNION query_matched UNION dependency_closed
```

### Node Weights

| Node Type | Base Weight | Modifiers |
|-----------|-------------|-----------|
| Function | 1.0 | +0.5 if external/public, +0.3 if payable |
| StateVariable | 0.5 | +0.5 if privileged |
| Contract | 0.3 | - |
| Edge | 0.2 | +0.3 if high-risk type |

### Thresholds

| Coverage | Interpretation | Action |
|----------|----------------|--------|
| >= 0.90 | Excellent | High confidence |
| >= 0.70 | Good | Acceptable |
| >= 0.50 | Partial | Review omissions |
| < 0.50 | Insufficient | Expand context |

---

## Unknowns Budget Gating

### Definition

Unknowns budget limits how many `unknown` clauses are acceptable before a finding is marked as "insufficient evidence".

```yaml
unknowns_budget:
  max_ratio: 0.3                     # Max unknown/total ratio
  max_absolute: 2                    # Max absolute unknown count
  critical_clauses: [ "<clause>" ]   # Clauses that cannot be unknown
```

### Gating Logic

```python
def check_unknowns_budget(finding: Finding, budget: UnknownsBudget) -> bool:
    """Check if finding meets unknowns budget.

    Returns True if acceptable, False if insufficient evidence.
    """
    total_clauses = len(finding.matched_clauses) + len(finding.failed_clauses) + len(finding.unknown_clauses)
    unknown_ratio = len(finding.unknown_clauses) / total_clauses if total_clauses > 0 else 0

    # Check ratio limit
    if unknown_ratio > budget.max_ratio:
        return False

    # Check absolute limit
    if len(finding.unknown_clauses) > budget.max_absolute:
        return False

    # Check critical clauses
    for clause in budget.critical_clauses:
        if clause in finding.unknown_clauses:
            return False

    return True
```

### Failure Semantics

When unknowns budget is exceeded:
1. Finding is marked with `insufficient_evidence: true`
2. Finding is demoted from detection results
3. Warning emitted with specific budget violation

---

## Debug Slice Mode

### Activation

Debug slice mode bypasses normal pruning for diagnostic purposes:

```bash
# CLI activation
alphaswarm query "..." --debug-slice

# Programmatic activation
result = pattern_engine.match(pattern, graph, slice_mode="debug")
```

### Behavior Differences

| Aspect | Standard Mode | Debug Mode |
|--------|--------------|------------|
| Pruning | Applied per budget | Bypassed |
| Omissions | Partial | Complete |
| Performance | Optimized | May be slow |
| Token usage | Budget-limited | Unlimited |

### Debug Output Extensions

```yaml
debug:
  slice_mode: debug
  pruning_bypassed: true
  full_omissions:
    nodes_considered: <int>
    nodes_captured: <int>
    edges_considered: <int>
    edges_captured: <int>
  traversal_trace: [ <TraversalStep> ]
```

---

## Validation Rules

### Required Field Validation

All REQUIRED fields must be present. Missing required fields cause immediate validation failure.

### Type Validation

- `interface_version`: Valid semver string (X.Y.Z)
- `build_hash`: Exactly 12 hex characters
- `coverage_score`: Float in range [0.0, 1.0]
- `severity`: One of critical|high|medium|low
- `status`: One of matched|failed|unknown

### Semantic Validation

1. **Clause list consistency**: Union of matched + failed + unknown must be complete
2. **Evidence linkage**: Every matched clause must have evidence
3. **Omission linkage**: Every unknown clause must have omission reason
4. **Build hash consistency**: All evidence_refs must share same build_hash
5. **Coverage bounds**: coverage_score must be in [0.0, 1.0]

### Validation Failure Behavior

Schema validation failures are **fatal** at serialization time:

```python
def serialize_finding(finding: Finding) -> str:
    """Serialize finding to v2 format.

    Raises:
        GraphInterfaceContractViolation: If validation fails
    """
    errors = validate_finding(finding)
    if errors:
        raise GraphInterfaceContractViolation(
            f"Finding {finding.id} violates Graph Interface Contract v2: {errors}"
        )
    return json.dumps(finding.to_dict())
```

---

## Reason Codes

### Evidence Missing Reasons

| Code | Meaning |
|------|---------|
| `taint_dataflow_unavailable` | Taint analysis not available for this path |
| `dominance_unknown` | Cannot determine dominance relationship |
| `interprocedural_truncated` | Call chain exceeded analysis depth |
| `external_return_untracked` | External call return not tracked |
| `aliasing_unknown` | Storage aliasing prevents tracking |
| `sanitizer_uncertain` | Cannot determine if sanitized |

### Omission Reasons

| Code | Meaning |
|------|---------|
| `modifier_not_traversed` | Modifier code not included in slice |
| `inherited_not_traversed` | Inherited function not included |
| `external_target_unknown` | External call target unresolved |
| `budget_exceeded` | Token/node budget caused pruning |
| `depth_limit_reached` | Call depth limit reached |
| `library_excluded` | Library code excluded from slice |

---

## Examples

### Complete Finding Example

```yaml
interface_version: "2.0.0"
build_hash: "a1b2c3d4e5f6"
timestamp: "2026-01-27T18:30:00Z"

query:
  kind: pattern
  id: "reentrancy-classic"
  source: "pattern:reentrancy-classic"

summary:
  nodes: 42
  edges: 87
  findings: 1
  coverage_score: 0.85
  omissions_present: true
  unknowns_count: 0

findings:
  - id: "FND-a1b2c3d4"
    pattern_id: "reentrancy-classic"
    severity: critical
    confidence: 0.92

    matched_clauses:
      - "reentrancy-classic:all:0"  # visibility in [public, external]
      - "reentrancy-classic:all:1"  # has TRANSFERS_VALUE_OUT
      - "reentrancy-classic:all:2"  # has WRITES_USER_BALANCE
      - "reentrancy-classic:all:3"  # TRANSFERS before WRITES

    failed_clauses: []

    unknown_clauses: []

    clause_matrix:
      - clause: "reentrancy-classic:all:0"
        status: matched
        evidence_refs:
          - file: "Token.sol"
            line: 42
            node_id: "N-withdraw-001"
            snippet_id: "EVD-f3a2b1c0"
            snippet: "function withdraw() external {"
            build_hash: "a1b2c3d4e5f6"
        omission_refs: []

      - clause: "reentrancy-classic:all:1"
        status: matched
        evidence_refs:
          - file: "Token.sol"
            line: 45
            node_id: "N-withdraw-001"
            snippet_id: "EVD-d4e5f6a7"
            snippet: "msg.sender.call{value: amount}(\"\");"
            build_hash: "a1b2c3d4e5f6"
        omission_refs: []

      - clause: "reentrancy-classic:all:2"
        status: matched
        evidence_refs:
          - file: "Token.sol"
            line: 46
            node_id: "N-withdraw-001"
            snippet_id: "EVD-b8c9d0e1"
            snippet: "balances[msg.sender] = 0;"
            build_hash: "a1b2c3d4e5f6"
        omission_refs: []

      - clause: "reentrancy-classic:all:3"
        status: matched
        evidence_refs:
          - file: "Token.sol"
            line: 45
            node_id: "N-withdraw-001"
            snippet_id: "EVD-d4e5f6a7"
            build_hash: "a1b2c3d4e5f6"
          - file: "Token.sol"
            line: 46
            node_id: "N-withdraw-001"
            snippet_id: "EVD-b8c9d0e1"
            build_hash: "a1b2c3d4e5f6"
        omission_refs: []

    evidence_refs:
      - file: "Token.sol"
        line: 42
        node_id: "N-withdraw-001"
        snippet_id: "EVD-f3a2b1c0"
        build_hash: "a1b2c3d4e5f6"
      - file: "Token.sol"
        line: 45
        node_id: "N-withdraw-001"
        snippet_id: "EVD-d4e5f6a7"
        build_hash: "a1b2c3d4e5f6"
      - file: "Token.sol"
        line: 46
        node_id: "N-withdraw-001"
        snippet_id: "EVD-b8c9d0e1"
        build_hash: "a1b2c3d4e5f6"

    omissions:
      cut_set: []
      excluded_edges: []
      coverage_score: 0.92

omissions:
  coverage_score: 0.85
  cut_set:
    - blocker: "M-inherited-ownable"
      reason: "inherited_not_traversed"
      impact: "Ownable modifier code not included"
  excluded_edges:
    - "CONTAINS_EVENT"
  omitted_nodes: []
  slice_mode: standard
```

### Finding with Unknown Clauses

```yaml
findings:
  - id: "FND-x1y2z3w4"
    pattern_id: "oracle-stale"
    severity: high
    confidence: 0.65

    matched_clauses:
      - "oracle-stale:all:0"  # calls oracle

    failed_clauses: []

    unknown_clauses:
      - "oracle-stale:all:1"  # missing staleness check

    clause_matrix:
      - clause: "oracle-stale:all:0"
        status: matched
        evidence_refs:
          - file: "PriceOracle.sol"
            line: 28
            node_id: "N-getPrice-001"
            snippet_id: "EVD-aa11bb22"
            build_hash: "a1b2c3d4e5f6"
        omission_refs: []

      - clause: "oracle-stale:all:1"
        status: unknown
        evidence_refs: []
        omission_refs:
          - "external_return_untracked"

    evidence_refs:
      - file: "PriceOracle.sol"
        line: 28
        node_id: "N-getPrice-001"
        snippet_id: "EVD-aa11bb22"
        build_hash: "a1b2c3d4e5f6"

    evidence_missing:
      - reason: "external_return_untracked"
        clause: "oracle-stale:all:1"
        details: "Chainlink return tuple not fully tracked"

    omissions:
      cut_set:
        - blocker: "E-latestRoundData-return"
          reason: "external_return_untracked"
          impact: "Cannot verify staleness check on oracle return"
      excluded_edges: []
      coverage_score: 0.72
```

---

## Migration Guide (v1 to v2)

### Breaking Changes

1. `evidence_refs` now REQUIRED (was optional)
2. `omissions` now REQUIRED at both root and finding level
3. `clause_matrix` now REQUIRED (new field)
4. `build_hash` now REQUIRED on all evidence refs
5. `interface_version` format changed from int to semver string

### Compatibility Shim

The v1-to-v2 shim applies these transformations:

| v1 Field | v2 Transformation |
|----------|-------------------|
| `version: 1` | `interface_version: "2.0.0"` |
| (missing evidence) | `evidence_missing: [{reason: "legacy_no_evidence"}]` |
| (missing omissions) | `omissions: {coverage_score: 1.0, cut_set: [], ...}` |
| (missing clause_matrix) | Generated from matched/failed/unknown lists |
| (missing build_hash) | Inferred from graph metadata or marked "legacy" |

---

## JSON Schema Reference

The normative JSON Schema is located at:
```
schemas/graph_interface_v2.json
```

All implementations MUST validate against this schema before serialization.

---

*Graph Interface Contract v2 - AlphaSwarm.sol*
*Version: 2.0.0*
*Last Updated: 2026-01-27*
