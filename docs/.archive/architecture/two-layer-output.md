# Two-Layer Output Architecture

**Status:** Specification
**Version:** 1.0.0
**Source:** CRITIQUE-REMEDIATION.md WS1.1
**Affects:** Phase 3, 9, 11

---

## Overview

VKG uses a two-layer output architecture to optimize for both token efficiency (LLM consumption) and evidence completeness (verification).

```
┌─────────────────────────────────────────────────────────────────┐
│                    TWO-LAYER OUTPUT                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: LLM Report JSON           Layer 2: Evidence JSONL     │
│  ┌─────────────────────────┐       ┌─────────────────────────┐ │
│  │ Minimal token footprint │       │ Detailed evidence by ID │ │
│  │ ~500-2000 tokens        │       │ Referenced on demand    │ │
│  │ Always generated        │       │ Streamable              │ │
│  └─────────────────────────┘       └─────────────────────────┘ │
│           │                                   │                  │
│           │    evidence_refs: ["EVD-001"]     │                  │
│           └───────────────────────────────────┘                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: LLM Report JSON

Minimal, token-efficient report for LLM consumption. Contains finding summaries with references to Layer 2 evidence.

### Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "VKGReport",
  "version": "1.0.0",
  "type": "object",
  "required": ["schema_version", "vkg_version", "graph_fingerprint", "analysis_completeness", "findings"],
  "properties": {
    "schema_version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$",
      "description": "Report schema version (semver)"
    },
    "vkg_version": {
      "type": "string",
      "description": "VKG tool version that generated this report"
    },
    "graph_fingerprint": {
      "type": "string",
      "description": "Deterministic hash of the knowledge graph for reproducibility"
    },
    "generated_at": {
      "type": "string",
      "format": "date-time"
    },
    "analysis_completeness": {
      "$ref": "#/definitions/AnalysisCompleteness"
    },
    "findings": {
      "type": "array",
      "items": { "$ref": "#/definitions/Finding" }
    },
    "pattern_pack_version": {
      "type": "string",
      "description": "Version of pattern pack used"
    }
  },
  "definitions": {
    "AnalysisCompleteness": {
      "type": "object",
      "required": ["status", "coverage_pct"],
      "properties": {
        "status": { "enum": ["complete", "partial", "failed"] },
        "coverage_pct": { "type": "number", "minimum": 0, "maximum": 100 },
        "contracts_analyzed": { "type": "integer" },
        "contracts_skipped": { "type": "integer" },
        "skipped_contracts": {
          "type": "array",
          "items": { "type": "string" }
        },
        "unsupported_features": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "Finding": {
      "type": "object",
      "required": ["id", "pattern_id", "tier", "severity", "location", "evidence_refs"],
      "properties": {
        "id": {
          "type": "string",
          "pattern": "^VKG-[0-9]+$"
        },
        "pattern_id": { "type": "string" },
        "tier": { "enum": ["tier_a", "tier_b"] },
        "severity": { "enum": ["critical", "high", "medium", "low", "info"] },
        "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
        "location": {
          "type": "object",
          "required": ["file", "line"],
          "properties": {
            "file": { "type": "string" },
            "line": { "type": "integer" },
            "column": { "type": "integer" },
            "function": { "type": "string" }
          }
        },
        "behavioral_signature": {
          "type": "string",
          "description": "Operation sequence signature (e.g., R:bal->X:out->W:bal)"
        },
        "evidence_refs": {
          "type": "array",
          "items": { "type": "string", "pattern": "^EVD-[0-9]+$" },
          "description": "References to Layer 2 evidence records"
        },
        "verdict": {
          "enum": ["pending", "confirmed", "false_positive", "inconclusive"],
          "default": "pending"
        }
      }
    }
  }
}
```

### Example Layer 1 Output

```json
{
  "schema_version": "1.0.0",
  "vkg_version": "4.0.0",
  "graph_fingerprint": "abc123def456",
  "generated_at": "2026-01-07T10:00:00Z",
  "analysis_completeness": {
    "status": "partial",
    "coverage_pct": 85,
    "contracts_analyzed": 15,
    "contracts_skipped": 2,
    "skipped_contracts": ["YulHelper.sol", "ProxyAdmin.sol"],
    "unsupported_features": ["inline_assembly"]
  },
  "findings": [
    {
      "id": "VKG-001",
      "pattern_id": "reentrancy-classic",
      "tier": "tier_a",
      "severity": "critical",
      "confidence": 0.92,
      "location": {
        "file": "Vault.sol",
        "line": 45,
        "column": 9,
        "function": "withdraw"
      },
      "behavioral_signature": "R:bal->X:out->W:bal",
      "evidence_refs": ["EVD-001", "EVD-002", "EVD-003"],
      "verdict": "pending"
    }
  ],
  "pattern_pack_version": "1.0.0"
}
```

---

## Layer 2: Evidence JSONL

Detailed evidence records in newline-delimited JSON (NDJSON) format. Each record is referenced by ID from Layer 1 findings.

### Format

One JSON object per line, no trailing commas, no array wrapper.

### Evidence Types

| Type | Purpose | Fields |
|------|---------|--------|
| `code` | Source code snippet | file, lines, snippet |
| `property` | Detected property | name, value, node_id |
| `call_graph` | Function call edge | from, to, edge_type, risk |
| `operation` | Semantic operation | operation, node_id, sequence_position |
| `guard` | Protection mechanism | guard_type, location, effective |
| `path` | Execution path | steps, risk_score |

### Schema Per Type

```json
// Type: code
{"id": "EVD-001", "type": "code", "file": "Vault.sol", "lines": [45, 52], "snippet": "function withdraw(uint amount) external {\n    require(balances[msg.sender] >= amount);\n    payable(msg.sender).transfer(amount);\n    balances[msg.sender] -= amount;\n}"}

// Type: property
{"id": "EVD-002", "type": "property", "name": "state_write_after_external_call", "value": true, "node_id": "Vault.withdraw"}

// Type: call_graph
{"id": "EVD-003", "type": "call_graph", "from": "withdraw", "to": "transfer", "edge_type": "external_call", "risk": "high"}

// Type: operation
{"id": "EVD-004", "type": "operation", "operation": "TRANSFERS_VALUE_OUT", "node_id": "Vault.withdraw", "sequence_position": 2}

// Type: guard
{"id": "EVD-005", "type": "guard", "guard_type": "reentrancy_guard", "location": "Vault.sol:10", "effective": false}

// Type: path
{"id": "EVD-006", "type": "path", "steps": ["deposit", "withdraw", "receive", "withdraw"], "risk_score": 0.95}
```

### Example Layer 2 Output (evidence.jsonl)

```jsonl
{"id": "EVD-001", "type": "code", "file": "Vault.sol", "lines": [45, 52], "snippet": "function withdraw(uint amount) external {...}"}
{"id": "EVD-002", "type": "property", "name": "state_write_after_external_call", "value": true, "node_id": "Vault.withdraw"}
{"id": "EVD-003", "type": "call_graph", "from": "withdraw", "to": "transfer", "edge_type": "external_call", "risk": "high"}
```

---

## Why Two Layers?

### 1. Token Efficiency
- LLM sees ~500-2000 token Layer 1 report
- Fetches specific evidence only when investigating a finding
- Reduces context usage by 60-80% vs monolithic reports

### 2. Deduplication
- Evidence shared across multiple findings by reference
- Same code snippet referenced by reentrancy AND access control findings
- Avoids token waste from repeated snippets

### 3. Streaming
- Layer 2 JSONL can be processed incrementally
- Supports large codebases without memory issues
- Enables parallel evidence fetch

### 4. Determinism
- Layer 1 JSON uses canonical formatting (sorted keys)
- Same input = same output (reproducible)
- Graph fingerprint enables cache validation

### 5. Separation of Concerns
- Layer 1: "What was found" (for decision making)
- Layer 2: "Why it was found" (for verification)

---

## CLI Commands

```bash
# Layer 1 only (LLM consumption)
vkg report --format json > report.json

# Both layers (full output)
vkg report --format json+evidence

# Evidence only (streaming mode)
vkg report --format jsonl > evidence.jsonl

# Fetch specific evidence by ID
vkg evidence EVD-001 EVD-002

# Validate report schema
vkg validate-output report.json

# Export with both layers for CI
vkg report --format json+evidence --output-dir ./reports/
# Creates: reports/report.json + reports/evidence.jsonl
```

---

## Phase Mapping

| Phase | Task | Integration |
|-------|------|-------------|
| **Phase 3** | 3.9 Output Schema Versioning | Implement Layer 1 schema |
| **Phase 3** | 3.14 Evidence-First Output | Implement Layer 2 + evidence_refs |
| **Phase 9** | Context Optimization | Optimize Layer 1 for token budget |
| **Phase 11** | LLM Integration | LLM consumes Layer 1, fetches Layer 2 on demand |

---

## Validation

### Schema Validation

```bash
# Validate Layer 1
jsonschema validate report.json --schema schemas/vkg-report.schema.json

# Validate Layer 2 (each line)
jq -c '.' evidence.jsonl | while read line; do
  echo "$line" | jsonschema validate --schema schemas/vkg-evidence.schema.json
done
```

### CI Integration

```yaml
# .github/workflows/ci.yml
- name: Validate BSKG Output
  run: |
    vkg report --format json > report.json
    vkg validate-output report.json
    # Exit code 0 = valid, 1 = invalid
```

### Evidence Reference Integrity

```python
# All evidence_refs in Layer 1 must exist in Layer 2
def validate_evidence_refs(report_json, evidence_jsonl):
    refs_needed = set()
    for finding in report_json["findings"]:
        refs_needed.update(finding["evidence_refs"])

    evidence_ids = set()
    for line in evidence_jsonl:
        evidence_ids.add(json.loads(line)["id"])

    missing = refs_needed - evidence_ids
    if missing:
        raise ValidationError(f"Missing evidence: {missing}")
```

---

## Acceptance Criteria

- [ ] Layer 1 JSON schema defined in `schemas/vkg-report.schema.json`
- [ ] Layer 2 evidence types documented
- [ ] CLI commands implemented: `--format json`, `--format json+evidence`, `--format jsonl`
- [ ] Validation command: `vkg validate-output`
- [ ] CI check validates schema on every test run
- [ ] 100% of findings have non-empty `evidence_refs`
- [ ] Evidence reference integrity validated

---

*Two-Layer Output Architecture | Version 1.0.0 | 2026-01-07*
