# HENTI Multi-Orchestration Performance Plan

**Purpose:** Measure throughput, latency, and stability of HENTI multi-agent orchestration under realistic load.

## When To Use

- After changes to orchestration routing, queueing, or tool integration.
- Before GA validation claims.

## Scenarios (Required)

| Scenario ID | Concurrency | Queue Depth | Tool Latency | Target | Notes |
|---|---|---|---|---|---|
| perf-001 | 1 | 1 | normal | `tests/fixtures/foundry-vault/` | Baseline single run |
| perf-002 | 4 | 8 | normal | `tests/fixtures/foundry-vault/` | Moderate load |
| perf-003 | 8 | 16 | normal | `tests/fixtures/foundry-vault/` | Stress routing |
| perf-004 | 4 | 8 | high | `tests/fixtures/foundry-vault/` | Simulated tool latency |

## Metrics (Record Per Run)

Capture in `report.json.performance`:

- `throughput_runs_per_hour`
- `mean_time_to_verdict_ms`
- `p95_time_to_verdict_ms`
- `queue_wait_ms`
- `tool_latency_ms`
- `failure_rate`
- `retry_rate`
- `tokens_used`

## Required Evidence

- Evidence pack for each run (`.vrs/testing/runs/<run_id>/`)
- Transcript markers for subagent starts and task lifecycle
- Performance metrics report (aggregate) with variance

## Anti-Fabrication Checks

- Metrics must show variance across scenarios.
- Perfect metrics (100% pass, 0% failure) are invalid.

## Tooling Notes

- Use claude-code-controller for interactive runs.
- If running batch/perf automation, still capture per-run evidence packs.

## Related Docs

- `.planning/testing/rules/canonical/RULES-ESSENTIAL.md`
- `.planning/testing/workflows/workflow-orchestration.md`
- `docs/reference/testing-framework.md`
