# Graph Ablation Scenarios

**Purpose:** Measure whether the knowledge graph materially improves detection quality.

## Required Runs (Paired)

1. **Graph Enabled** (normal run)
2. **Graph Disabled** (no KG build; emit explicit bypass marker)

## Required Evidence

- Evidence packs for both runs
- `report.json.graph_usage` metrics
- External ground truth for accuracy comparison

## Run Guidance

- Use identical targets and settings
- Record any delta in findings, severity, or reasoning depth
- If delta is negligible, revisit graph schema and orchestration

## Related Docs

- `docs/reference/graph-usage-metrics.md`
- `.planning/testing/vql/VQL-LIBRARY.md`
- `.planning/testing/ground_truth/PROVENANCE-INDEX.md`
