# Graph Usage Metrics (Validation Contract)

**Purpose:** Prove the knowledge graph materially improves reasoning quality and is used before conclusions.

## When To Load

- Graph-first validation, Tier B/C evaluation, or any ablation testing.

## Required Metrics (Evidence Pack)

Record these fields under `report.json.graph_usage`:

- `query_count` (int) — total graph/VQL queries executed
- `unique_nodes` (int) — unique graph nodes referenced in query results
- `unique_edges` (int) — unique edges traversed or referenced
- `query_time_ms` (int) — total time spent running queries
- `graph_build_ms` (int) — KG build duration (if applicable)
- `evidence_nodes_cited` (int) — node IDs referenced in findings
- `vql_min_set_present` (bool) — minimum VQL set executed
- `cross_contract_queries` (int) — count of VQL-XCON queries

Example snippet:

```json
{
  "graph_usage": {
    "query_count": 12,
    "unique_nodes": 87,
    "unique_edges": 214,
    "query_time_ms": 1840,
    "graph_build_ms": 9812,
    "evidence_nodes_cited": 14,
    "vql_min_set_present": true,
    "cross_contract_queries": 2
  }
}
```

## Ablation Protocol (Required)

Run paired scenarios on the same target:

1. **Graph Enabled** — normal KG build + VQL usage.
2. **Graph Disabled** — block KG build and VQL usage (must emit `[GRAPH_BUILD_FAIL]` or explicit bypass marker).

Compare:
- findings count and severity
- evidence quality (node IDs, code references)
- reasoning depth (cross-function reasoning)
- time-to-first-finding

Ablation runs **must** include external ground truth for accuracy comparisons.

## Interpretation Guidance

- If graph usage metrics are zero or minimal, the run is invalid.
- If ablation shows no measurable delta, revisit graph schema, query templates, or orchestration logic.

## Related Docs

- `.planning/testing/vql/VQL-LIBRARY.md`
- `.planning/testing/scenarios/SCENARIO-MANIFEST.yaml`
- `.planning/testing/rules/canonical/RULES-ESSENTIAL.md`
