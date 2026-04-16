# Proof Token Matrix

**Status:** CANONICAL
**Created:** 2026-02-04
**Purpose:** Define required proof tokens per validation stage (IMP-A3)

---

## Overview

Proof tokens are structured evidence markers that prove a specific stage completed successfully. Evidence packs MUST contain the required proof tokens for their test type.

## Token Types

| Token Type | Format | Purpose |
|------------|--------|---------|
| `stage.health_check` | `{tool: str, version: str, status: pass}` | Tool availability verified |
| `stage.graph_build` | `{nodes: int, edges: int, hash: str}` | Graph constructed |
| `stage.graph_integrity` | `{orphans: int, cycles: int, valid: bool}` | Graph structure valid |
| `stage.context_pack` | `{protocol: str, ctl: str, fields: list}` | Context loaded |
| `stage.pattern_match` | `{patterns: int, matches: int}` | Patterns executed |
| `stage.agent_spawn` | `{type: str, task_id: str, completed: bool}` | Agent ran |
| `stage.debate` | `{rounds: int, verdict: str, confidence: float}` | Debate completed |
| `stage.report` | `{findings: int, path: str, format: str}` | Report generated |

---

## Proof Token Matrix by Test Type

### CLI Install Validation
```yaml
cli_install:
  required:
    - stage.health_check
  optional: []
  na:
    - stage.graph_build
    - stage.graph_integrity
    - stage.context_pack
    - stage.pattern_match
    - stage.agent_spawn
    - stage.debate
    - stage.report
```

### Graph Build Validation
```yaml
graph_build:
  required:
    - stage.health_check
    - stage.graph_build
    - stage.graph_integrity
  optional: []
  na:
    - stage.context_pack
    - stage.pattern_match
    - stage.agent_spawn
    - stage.debate
    - stage.report
```

### Pattern Detection Validation
```yaml
pattern_detection:
  required:
    - stage.health_check
    - stage.graph_build
    - stage.pattern_match
  optional:
    - stage.graph_integrity
  na:
    - stage.context_pack
    - stage.agent_spawn
    - stage.debate
    - stage.report
```

### Single Agent Validation
```yaml
single_agent:
  required:
    - stage.health_check
    - stage.graph_build
    - stage.agent_spawn
  optional:
    - stage.graph_integrity
    - stage.pattern_match
  na:
    - stage.debate
```

### Multi-Agent Debate Validation
```yaml
multi_agent_debate:
  required:
    - stage.health_check
    - stage.graph_build
    - stage.graph_integrity
    - stage.agent_spawn  # x3 (attacker, defender, verifier)
    - stage.debate
  optional:
    - stage.context_pack
    - stage.pattern_match
  na: []
```

### Audit Entrypoint (E2E)
```yaml
audit_entrypoint:
  required:
    - stage.health_check
    - stage.graph_build
    - stage.graph_integrity
    - stage.context_pack
    - stage.pattern_match
    - stage.agent_spawn
    - stage.debate
    - stage.report
  optional: []
  na: []
```

### E2E Full Validation
```yaml
e2e_validation:
  required:
    - ALL tokens (none N/A)
  optional: []
  na: []
```

---

## Token Schemas

### stage.health_check
```json
{
  "type": "stage.health_check",
  "tool": "alphaswarm",
  "version": "5.0.0",
  "status": "pass",
  "timestamp": "2026-02-04T15:30:00Z",
  "checks": {
    "cli": true,
    "slither": true,
    "python": true
  }
}
```

### stage.graph_build
```json
{
  "type": "stage.graph_build",
  "nodes": 142,
  "edges": 387,
  "hash": "a3f8c2b1e9d4",
  "duration_ms": 2340,
  "target": "contracts/Vault.sol",
  "timestamp": "2026-02-04T15:30:05Z"
}
```

### stage.graph_integrity
```json
{
  "type": "stage.graph_integrity",
  "orphans": 0,
  "cycles": 0,
  "disconnected_components": 1,
  "valid": true,
  "timestamp": "2026-02-04T15:30:06Z"
}
```

### stage.context_pack
```json
{
  "type": "stage.context_pack",
  "protocol": "Aave",
  "ctl": "high",
  "fields_present": ["protocol_type", "trust_boundaries", "asset_types", "upgradeability", "economic_model"],
  "fields_missing": [],
  "source": "official_docs",
  "timestamp": "2026-02-04T15:30:10Z"
}
```

### stage.pattern_match
```json
{
  "type": "stage.pattern_match",
  "patterns_evaluated": 556,
  "matches_raw": 12,
  "matches_deduplicated": 8,
  "tier_a": 5,
  "tier_b": 2,
  "tier_c": 1,
  "timestamp": "2026-02-04T15:30:30Z"
}
```

### stage.agent_spawn
```json
{
  "type": "stage.agent_spawn",
  "agent_type": "vrs-attacker",
  "task_id": "task-001",
  "bead_id": "bead-reentrancy-001",
  "started_at": "2026-02-04T15:30:35Z",
  "completed_at": "2026-02-04T15:31:15Z",
  "duration_ms": 40000,
  "evidence_nodes": 5,
  "completed": true
}
```

### stage.debate
```json
{
  "type": "stage.debate",
  "bead_id": "bead-reentrancy-001",
  "rounds": 1,
  "attacker_claims": 3,
  "defender_claims": 2,
  "verdict": "high",
  "confidence": 0.85,
  "cross_references": 4,
  "timestamp": "2026-02-04T15:32:00Z"
}
```

### stage.report
```json
{
  "type": "stage.report",
  "findings": 3,
  "critical": 1,
  "high": 1,
  "medium": 1,
  "low": 0,
  "informational": 0,
  "path": ".vrs/reports/audit-2026-02-04.json",
  "format": "json",
  "timestamp": "2026-02-04T15:32:30Z"
}
```

---

## Validation Rules

### Required Token Presence
```python
def validate_proof_tokens(evidence_pack: dict, test_type: str) -> tuple[bool, list[str]]:
    """Validate evidence pack has required proof tokens."""
    matrix = PROOF_TOKEN_MATRIX[test_type]
    missing = []

    for required_token in matrix['required']:
        if required_token not in evidence_pack.get('proofs', {}):
            missing.append(required_token)

    return len(missing) == 0, missing
```

### Token Integrity
```python
def validate_token_integrity(token: dict) -> bool:
    """Validate token has required fields and valid values."""
    schema = TOKEN_SCHEMAS[token['type']]
    for field, field_type in schema['required_fields'].items():
        if field not in token:
            return False
        if not isinstance(token[field], field_type):
            return False
    return True
```

### Cross-Token Consistency
```python
def validate_cross_consistency(tokens: list[dict]) -> bool:
    """Validate tokens are consistent with each other."""
    # Graph hash must match across tokens
    graph_hashes = {t.get('graph_hash') for t in tokens if 'graph_hash' in t}
    if len(graph_hashes) > 1:
        return False  # Inconsistent graph hashes

    # Timestamps must be in order
    timestamps = [t['timestamp'] for t in tokens if 'timestamp' in t]
    if timestamps != sorted(timestamps):
        return False  # Out of order

    return True
```

---

## Evidence Pack Structure

Evidence packs must include proof tokens in standardized location:

```
.vrs/testing/runs/{run_id}/
├── manifest.json           # Run metadata
├── transcript.txt          # Raw output
├── report.json             # Results
├── environment.json        # Context
├── proofs/                 # Proof tokens
│   ├── health_check.json
│   ├── graph_build.json
│   ├── graph_integrity.json
│   ├── context_pack.json
│   ├── pattern_match.json
│   ├── agent_spawn_attacker.json
│   ├── agent_spawn_defender.json
│   ├── agent_spawn_verifier.json
│   ├── debate.json
│   └── report.json
└── ground_truth.json       # External reference (optional)
```

---

## Attestation Requirements

### Token Source
Each token must indicate its source:
- `"source": "cli_output"` - Extracted from CLI output
- `"source": "transcript_parse"` - Parsed from transcript
- `"source": "tool_api"` - From tool API response
- `"source": "file_system"` - From file existence/content

### Verification Method
Each token must specify how to verify:
- `"verify_method": "file_exists"` - Check file at path
- `"verify_method": "hash_match"` - Compare hash values
- `"verify_method": "count_check"` - Verify numeric counts
- `"verify_method": "regex_match"` - Match pattern in transcript

---

## Anti-Fabrication

### Fabrication Indicators
- All counts are round numbers (100, 200, etc.)
- All confidences are exactly 1.0
- Timestamps have identical seconds
- Hash appears nowhere in source files

### Validation Script
```bash
# Validate proof token authenticity
python3 scripts/validate_proof_tokens.py .vrs/testing/runs/{run_id}/
```

---

**Last Updated:** 2026-02-04
