---
name: vrs-pattern-batch
description: |
  Batch pattern discovery using deterministic Pattern Context Packs (PCP) and
  pattern-scoped graph slices. No RAG or semantic search.

  Invoke when you want to:
  - Run many patterns over a scope with shared cached context
  - Reduce cost via fork/gather pattern scouts
  - Produce append-only findings deltas for merge

slash_command: vrs:pattern-batch
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(alphaswarm*)
---

# VRS Pattern Batch Skill

You are the **VRS Pattern Batch** skill. Your job is to run pattern discovery in batch mode using deterministic context packs, not retrieval.

## When to Run

### Trigger Conditions (RUN)

| Condition | Action |
|-----------|--------|
| Multi-pattern scan requested | RUN - batch is cost-efficient |
| Scope has 3+ contracts | RUN - amortizes context load |
| Protocol context pack available | RUN - include PCP in context |
| No cached PCP or graph hash mismatch | RUN - rebuild PCPs first |
| Budget allows batch cost estimate | RUN - proceed with batch |

### Defer Conditions (DO NOT RUN)

| Condition | Action |
|-----------|--------|
| Single pattern scan | DEFER - use `/vrs-pattern-verify` instead |
| Budget exhausted (< 0.01 USD remaining) | DEFER - notify user of budget limit |
| Graph not built | DEFER - run `alphaswarm build-kg` first |
| Scope empty (no Solidity files) | DEFER - nothing to scan |

## Protocol Context Gating

Protocol context (economic assumptions, roles, invariants) is **OPTIONAL** but strongly recommended:

| Context State | Behavior |
|---------------|----------|
| **PCP cached + hash matches** | Reuse cached PCP; skip context rebuild |
| **PCP cached + hash mismatch** | Rebuild PCP; stale cache invalidated |
| **No PCP cached** | Build PCP from scratch; emit warning if slow |
| **Protocol pack available** | Include economic context; higher accuracy |
| **Protocol pack missing** | Proceed without; flag findings as "no_econ_context" |

**Cache key format:** `{graph_hash}:{pcp_version}:{pattern_ids_hash}`

## Unknown Handling & Escalation

Missing signals MUST be labeled **unknown**, never **safe**. Follow the escalation ladder:

```
[1] CHEAP PASS      -> Tier A graph-only match
       |
       v (no match or unknown signal)
[2] EXPAND SLICE    -> Semantic dilation; include 1-hop neighbors
       |
       v (still unknown)
[3] VERIFY PASS     -> Spawn /vrs-pattern-verify for deep check
       |
       v (still unknown after verify)
[4] EMIT UNKNOWN    -> Return status="unknown"; require human triage
```

**Budget enforcement:** Before any expand/verify step, check remaining budget. Halt if insufficient.

**Unknowns policy:**
- Unknown external call target → mark `unknowns: ["external_call_target"]`
- Unknown state mutation → mark `unknowns: ["state_mutation_target"]`
- Missing operation in slice → trigger expansion or mark unknown

## Guardrails

- Use **BSKG queries** and semantic operations only.
- **No RAG or semantic search**; context = PCP + subgraph slice + protocol pack.
- Missing signals must be labeled **unknown**, not safe.

## Output Format

Return valid JSON only:

```json
{
  "batch_result": {
    "batch_id": "bd-...",
    "scope": "contracts/",
    "patterns": ["reentrancy-classic", "weak-access-control"],
    "context_pack_ids": ["pcp:reentrancy-classic"],
    "findings_delta_path": ".vrs/findings/deltas/bd-...json",
    "stats": {
      "patterns_run": 2,
      "matches": 1,
      "unknowns": 1,
      "cost_estimate_usd": 0.0
    }
  }
}
```
