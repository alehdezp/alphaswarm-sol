---
name: vrs-evidence-audit
description: |
  Evidence audit skill for VRS deterministic evidence references. Validates evidence IDs, build hash consistency, and source resolution.

  Invoke when:
  - Validating evidence references in findings
  - Checking build hash consistency
  - Resolving evidence to source code
  - Auditing evidence completeness

slash_command: vrs:evidence-audit
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
---

# VRS Evidence Audit Skill

You are the **VRS Evidence Audit** skill, responsible for validating that all evidence references are deterministic, resolvable, and tied to correct build hashes.

## How to Invoke

```bash
/vrs-evidence-audit <findings-file>
/vrs-evidence-audit VRS-001 --resolve
/vrs-evidence-audit --check-hash abc123def456
/vrs-evidence-audit --completeness
```

---

## Purpose

Phase 5.9 establishes deterministic evidence as a core requirement:

1. **Evidence IDs** - Unique, reproducible identifiers for code locations
2. **Build hash binding** - All evidence tied to specific graph build
3. **Resolution** - Evidence IDs resolve to source code spans
4. **Completeness** - All matched clauses have evidence or explicit missing reason

---

## Evidence Reference Structure

```yaml
evidence_refs:
  - id: "EVD-001"
    file: "Token.sol"
    line: 42
    column: 8
    end_line: 42
    end_column: 56
    node_id: "N-ext-call-1"
    snippet_id: "SNP-abc123"
    build_hash: "abc123def456"
    span:
      start: 1842
      end: 1890
```

### Required Fields

| Field | Purpose | Validation |
|-------|---------|------------|
| `id` | Unique evidence ID | Must be unique within finding |
| `file` | Source file path | Must exist in build |
| `line` | Line number | Must be valid (1-indexed) |
| `node_id` | Graph node reference | Must exist in KG |
| `build_hash` | Build this evidence belongs to | Must match top-level |

### Optional Fields

| Field | Purpose |
|-------|---------|
| `column` | Column offset |
| `end_line` | End line (for multi-line) |
| `end_column` | End column |
| `snippet_id` | Pre-computed snippet ID |
| `span` | Byte offsets in source |

---

## Evidence ID Generation

Evidence IDs are deterministic based on:

```
EVD-{hash(file + line + column + node_id + build_hash)[:8]}
```

Same input always produces same ID, enabling:
- Cross-session evidence matching
- Deduplication of repeated evidence
- Reproducible findings

### Build Hash Generation

Build hash is computed from:

```
build_hash = hash(
  sorted(source_files) +
  slither_version +
  kg_builder_version +
  timestamp_day  # Day-level granularity
)[:12]
```

Build hash ensures:
- Evidence tied to specific analysis
- Stale evidence detected when source changes
- Reproducibility within same day

---

## Validation Rules

### Rule 1: Build Hash Consistency

All evidence refs must use the same build_hash as top-level:

```yaml
# VALID
interface_version: "2.0.0"
build_hash: "abc123def456"
findings:
  - evidence_refs:
      - { id: "EVD-001", build_hash: "abc123def456" }  # Matches
      - { id: "EVD-002", build_hash: "abc123def456" }  # Matches

# INVALID
findings:
  - evidence_refs:
      - { id: "EVD-001", build_hash: "xyz789000000" }  # MISMATCH!
```

### Rule 2: Node ID Resolution

Evidence node_id must exist in the knowledge graph:

```yaml
# Check node exists
evidence_refs:
  - node_id: "N-ext-call-1"  # Must exist in KG nodes
```

### Rule 3: Source Resolution

Evidence file/line must resolve to actual source:

```yaml
# Check source resolves
evidence_refs:
  - file: "Token.sol"
    line: 42  # Must be valid line in Token.sol
```

### Rule 4: ID Uniqueness

Evidence IDs must be unique within a finding:

```yaml
# INVALID - duplicate IDs
evidence_refs:
  - id: "EVD-001"
  - id: "EVD-001"  # DUPLICATE!
```

---

## Resolution Workflow

### Step 1: Load Evidence

```bash
/vrs-evidence-audit findings.json --resolve
```

### Step 2: Resolve to Source

For each evidence ref:

```python
def resolve_evidence(ref):
    # 1. Check file exists
    if not exists(ref.file):
        return ResolveError("file_not_found")

    # 2. Check line valid
    lines = read_lines(ref.file)
    if ref.line > len(lines):
        return ResolveError("line_out_of_range")

    # 3. Extract snippet
    snippet = lines[ref.line - 1]
    if ref.column and ref.end_column:
        snippet = snippet[ref.column:ref.end_column]

    # 4. Verify node_id
    if not kg.has_node(ref.node_id):
        return ResolveError("node_not_found")

    return ResolveResult(snippet=snippet, verified=True)
```

### Step 3: Report Results

```markdown
## Resolution Results

### Resolved
| Evidence ID | File | Line | Snippet |
|-------------|------|------|---------|
| EVD-001 | Token.sol | 42 | `msg.sender.call{value: amount}("")` |
| EVD-002 | Token.sol | 45 | `balances[msg.sender] -= amount` |

### Resolution Failures
| Evidence ID | Error | Reason |
|-------------|-------|--------|
| EVD-003 | file_not_found | `OldToken.sol` no longer exists |
| EVD-004 | node_not_found | `N-deleted-1` not in current KG |
```

---

## Completeness Audit

Verify all matched clauses have evidence:

```bash
/vrs-evidence-audit --completeness findings.json
```

### Completeness Rules

| Clause Status | Evidence Requirement |
|---------------|---------------------|
| `matched` | Must have `evidence_refs` OR `evidence_missing` |
| `failed` | May have `evidence_refs` (showing why failed) |
| `unknown` | Must have `omission_refs` |

### Completeness Report

```markdown
## Completeness Audit

### Summary
- Total clauses: 24
- With evidence: 18
- With evidence_missing: 4
- Missing evidence: 2 (INCOMPLETE)

### Missing Evidence
| Finding | Clause | Status |
|---------|--------|--------|
| F-001 | taint_user_input | matched (NO EVIDENCE) |
| F-002 | guard_dominates | matched (NO EVIDENCE) |

### Evidence Missing Reasons
| Finding | Clause | Reason |
|---------|--------|--------|
| F-001 | external_return_tainted | taint_dataflow_unavailable |
| F-003 | guard_dominance | dominance_unknown |
```

---

## Stale Evidence Detection

Detect evidence that no longer matches source:

```bash
/vrs-evidence-audit --check-stale
```

Evidence becomes stale when:
- Source file modified after build
- Line content changed
- Node removed from KG

```markdown
## Stale Evidence

### Stale References
| Evidence ID | Issue | Current | Expected |
|-------------|-------|---------|----------|
| EVD-001 | line_changed | `// TODO: fix` | `msg.sender.call...` |
| EVD-002 | file_modified | (modified 2 hours ago) | (build from yesterday) |

### Recommendation
Rebuild knowledge graph to get fresh evidence references.
```

---

## Build Hash Verification

Verify evidence against specific build:

```bash
/vrs-evidence-audit --check-hash abc123def456
```

Output:
```markdown
## Build Hash Verification

### Build: abc123def456
- Created: 2026-01-27T12:00:00Z
- Sources: 12 files
- Slither: 0.10.0
- KG Builder: 2.0.0

### Evidence Status
| Status | Count |
|--------|-------|
| Valid | 45 |
| Mismatched hash | 3 |
| Unresolvable | 2 |

### Mismatched Hashes
| Evidence ID | Has Hash | Expected |
|-------------|----------|----------|
| EVD-old-1 | xyz789... | abc123... |
```

---

## Integration with Contract v2

Evidence audit is part of v2 contract compliance:

```yaml
interface_version: "2.0.0"
build_hash: "abc123def456"
evidence_integrity:
  total_refs: 24
  resolved: 24
  stale: 0
  completeness: 1.0  # All clauses have evidence
findings:
  - evidence_refs:
      - id: "EVD-001"
        build_hash: "abc123def456"  # Must match
        resolution_verified: true    # Must be true for v2
```

---

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| `EV-001` | Build hash mismatch | Check evidence source |
| `EV-002` | Node not found | Rebuild KG |
| `EV-003` | File not found | Source may have moved |
| `EV-004` | Line out of range | Source may have changed |
| `EV-005` | Duplicate evidence ID | Fix ID generation |
| `EV-006` | Missing evidence | Add evidence or evidence_missing |
| `EV-007` | Stale evidence | Rebuild with current source |

---

## When to Invoke

Invoke this skill when:
- **Finding validation**: Verify evidence before reporting
- **Build verification**: Check evidence matches build
- **Completeness check**: Audit evidence coverage
- **Stale detection**: Find outdated evidence
- **Debug resolution**: Trace evidence to source

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-graph-contract-validate` | Schema/evidence validation |
| `/vrs-slice-unify` | Unified context slicing |
| `/vrs-taxonomy-migrate` | Operation naming validation |

---

## Write Boundaries

This skill is restricted to writing in:
- `.claude/vrs/` - VRS working directory
- `.beads/` - Bead storage directory

All other directories are read-only.

---

## Notes

- Evidence IDs are deterministic and reproducible
- Build hash ties evidence to specific analysis run
- All matched clauses require evidence or evidence_missing
- Stale evidence indicates source has changed
- Resolution failures indicate KG rebuild needed
- Completeness is required for v2 contract compliance
- This skill CAN be invoked by orchestrators (disable-model-invocation: false)
