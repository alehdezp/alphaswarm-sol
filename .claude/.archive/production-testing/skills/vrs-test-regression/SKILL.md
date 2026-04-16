---
name: vrs-test-regression
description: Run regression test suite to verify no regressions after changes
---

# /vrs-test-regression — Regression Test Suite

## Purpose

Run the full regression test suite or a selected subset to ensure that changes haven't broken existing functionality. This is the gate that every phase exit must pass through.

## Usage

```
/vrs-test-regression                          # Full regression suite
/vrs-test-regression --tag smoke              # Smoke tests only (fast)
/vrs-test-regression --tag pattern            # All pattern tests
/vrs-test-regression --category e2e-pipeline  # All E2E tests
/vrs-test-regression --since <phase-id>       # Only new scenarios since phase
/vrs-test-regression --failed-only            # Re-run only previously failed tests
```

## Process

### Step 1: Load Test Suite

Read `.vrs/testing/scenarios/registry.yaml` and filter based on arguments.

Display test plan:
```
## Regression Suite Plan

Scenarios to run: 15
Categories: pattern-detection (8), orchestration (3), e2e-pipeline (2), agent-reasoning (2)
Estimated time: ~45 minutes

Proceed? [Y/n]
```

### Step 2: Execute Scenarios

Run scenarios using `/vrs-test-run` for each. Where possible, run scenarios in parallel using separate jj workspaces:

```
Parallel execution plan:
  Workspace 1: ct-access-control-001, ct-reentrancy-001, ct-oracle-001
  Workspace 2: orchestration-spawn-001, orchestration-pickup-001
  Workspace 3: e2e-dvdefi-unstoppable
  Sequential: agent-reasoning-graph-first-001 (depends on graph building)
```

### Step 3: Collect Results

Aggregate results from all scenarios:

```
## Regression Results

Run ID: reg-2026-02-09-001
Duration: 38 minutes
Scenarios: 15 total

### Results
PASS: 12
FAIL: 2
PARTIAL: 1

### Failures
1. bt-reentrancy-001 — FAIL
   Observer: "Agent did not detect cross-function reentrancy. It built the graph
   but only checked single-function patterns. The BT pattern for cross-function
   analysis was not triggered."
   Regression: YES (passed in previous run)

2. e2e-dvdefi-unstoppable — FAIL
   Observer: "Pipeline crashed during pattern matching stage. Error in
   PatternEngine.run_all_patterns — likely introduced by recent changes."
   Regression: YES (passed in previous run)

### Partial
3. orchestration-spawn-001 — PARTIAL
   Observer: "Subagents were spawned correctly but one timed out before
   completing its task. May be a resource issue rather than a code bug."

### All Results
[Full table with scenario ID, verdict, duration, observer summary]
```

### Step 4: Update Registry

Update the registry with latest run results:
```yaml
scenarios:
  - id: ct-access-control-001
    last_run: 2026-02-09
    last_result: pass
    run_count: 5
    consecutive_passes: 5
```

### Step 5: Gate Decision

For phase exit gates, provide a clear go/no-go:

```
## Phase Exit Gate: Regression

RESULT: BLOCKED (2 failures)

Must fix before proceeding:
1. bt-reentrancy-001 — Cross-function reentrancy detection broken
2. e2e-dvdefi-unstoppable — Pipeline crash in pattern matching

Recommendation: Fix the PatternEngine regression first (likely root cause of both).
```

## Integration with GSD Phases

This skill is automatically invoked (or should be invoked) at:
- **Phase planning**: Identify which scenarios to add
- **Phase execution**: Run relevant scenarios during implementation
- **Phase exit**: Full regression suite must pass

## Report Format

Results are saved to `.vrs/testing/results/regression-<run-id>/`:
- `summary.json` — Machine-readable aggregate results
- `report.md` — Human-readable full report
- `per-scenario/` — Individual scenario results
