# Performance Scenario Reference

**Purpose:** Provide a concrete scenario list for the HENTI performance suite.

## Scenario List

- `perf-001` — baseline single run (concurrency 1)
- `perf-002` — moderate load (concurrency 4, queue depth 8)
- `perf-003` — stress load (concurrency 8, queue depth 16)
- `perf-004` — latency stress (tool latency injected)

## Required Evidence

- Evidence pack per run
- Aggregate metrics report from `.planning/testing/perf/PERF-PLAN.md`

## Related Docs

- `.planning/testing/perf/PERF-PLAN.md`
- `.planning/testing/workflows/workflow-orchestration.md`
