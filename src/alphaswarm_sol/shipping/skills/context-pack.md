---
name: vrs-context-pack
description: |
  Build a deterministic Pattern Context Pack (PCP) for a pattern and scope.
  The PCP is cacheable and used for batch discovery.

slash_command: vrs:context-pack
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
---

# VRS Context Pack Skill

You are the **VRS Context Pack** skill. Generate deterministic PCP context from VulnDocs + graph slices.

## When to Run

### Trigger Conditions (RUN)

| Condition | Action |
|-----------|--------|
| No cached PCP for pattern | RUN - build fresh PCP |
| Graph hash changed since last PCP | RUN - rebuild PCP (cache invalidated) |
| Pattern version updated | RUN - rebuild PCP for new pattern def |
| Batch scan starting | RUN - ensure PCPs ready before batch |
| Protocol context newly available | RUN - rebuild to include protocol context |

### Defer Conditions (DO NOT RUN)

| Condition | Action |
|-----------|--------|
| Cached PCP exists + hash matches | DEFER - reuse cached PCP |
| Pattern not in VulnDocs | DEFER - no VulnDoc to source from |
| Graph not built | DEFER - build graph first |
| Budget insufficient for PCP build | DEFER - notify user |

### Reuse vs Rebuild Decision Matrix

| Cached PCP | Graph Hash | Pattern Version | Action |
|------------|------------|-----------------|--------|
| Yes | Match | Match | **REUSE** cached PCP |
| Yes | Mismatch | Any | **REBUILD** (graph changed) |
| Yes | Match | Mismatch | **REBUILD** (pattern updated) |
| No | Any | Any | **BUILD** new PCP |

## Protocol Context Gating

Protocol context inclusion follows these rules:

| Protocol Context State | Action |
|------------------------|--------|
| **Available + < 500 tokens** | INCLUDE in PCP (cheap enrichment) |
| **Available + 500-2000 tokens** | INCLUDE if budget allows; record cost |
| **Available + > 2000 tokens** | SUMMARIZE to 1500 tokens; include summary |
| **Missing** | Build PCP without; flag as "no_protocol_context" |

**Protocol context fields to include:**
- Roles and permissions (always)
- Economic assumptions (if available)
- Invariants (always)
- Off-chain inputs (if relevant to pattern)

## Unknown Handling & Escalation

PCP generation must handle missing data gracefully:

| Missing Data | Action |
|--------------|--------|
| VulnDoc missing fields | Use defaults; flag in PCP metadata |
| Pattern has no counter-signals | Emit warning; PCP still valid |
| Semantic operations unknown | Mark `unknowns: [ops]` in PCP |
| Witness extraction fails | Mark `witness_status: incomplete` |

**PCP completeness levels:**

| Level | Definition |
|-------|------------|
| `complete` | All required fields, witnesses, counter-signals present |
| `partial` | Required fields present; optional fields missing |
| `minimal` | Only pattern ID and basic ops; insufficient for deep verify |

**Escalation:** If PCP generation yields `minimal`, emit warning and suggest manual VulnDoc enrichment.

## Guardrails

- No RAG or semantic search.
- PCP must include pseudocode, scenarios, op signatures, invariants, and counter-signals.
- Enforce token budget targets.

## Output Format

Return valid JSON only:

```json
{
  "context_pack": {
    "pattern_id": "reentrancy-classic",
    "pack_id": "pcp:reentrancy-classic",
    "path": ".vrs/context/patterns/reentrancy-classic.yaml",
    "token_estimate": 950,
    "budget_target": 1200
  }
}
```
