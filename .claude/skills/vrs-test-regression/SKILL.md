---
name: vrs-test-regression
description: |
  Run full regression suite across all use case scenarios. Compares current
  scores against baseline, flags any drops > 5 points, and reports overall
  health of the evaluation system.

  Invoke when user wants to:
  - Check for regressions: "regression check", "did anything break?"
  - Pre-commit validation: "run all tests before committing"
  - Full suite: "run full scenario suite", "/vrs-test-regression"

slash_command: vrs-test-regression
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(pytest*)
  - Bash(uv run*)
  - Bash(python*)
---

# VRS Test Regression — Full Regression Suite

You are the **VRS Test Regression** skill. You run ALL use case scenarios and compare results against baseline to detect regressions.

## How to Invoke

```bash
/vrs-test-regression
/vrs-test-regression --tier core      # core scenarios only
/vrs-test-regression --verbose        # detailed output per scenario
```

## Workflow

### 1. Run all scenarios

```bash
# Full regression suite
uv run pytest tests/scenarios/ -v --tb=short 2>&1

# Core tier only (fastest)
uv run pytest tests/scenarios/ -k "core" -v --tb=short

# Also run the workflow harness tests
uv run pytest tests/workflow_harness/ -x -q --tb=short
```

### 2. Compare against baseline

The BaselineManager at `tests/workflow_harness/lib/regression_baseline.py` tracks historical scores. Check if any scenario dropped > 5 points from its rolling average.

**Note:** BaselineManager requires explicit wiring by the caller — it is not auto-enabled. The `EvaluationRunner` accepts an optional `baseline_manager` parameter that must be constructed and passed in.

### 3. Report results

```
=== REGRESSION REPORT ===

Total: 32 scenarios
  Passed: 28
  Failed: 3
  Skipped: 1

Regressions detected: 1
  UC-AUDIT-005: score 48 (baseline avg: 72) → REGRESSION (-24 points)
    Lowest dimension: oracle_detection (score: 20)
    Cause: Oracle pattern conditions changed in commit abc123

No regressions: 27 scenarios stable or improved

Workflow harness: 298 tests passed
```

### 4. If regressions found

1. Identify the exact dimension that dropped
2. Check git log for recent changes that could have caused it
3. Suggest specific fix or rollback
4. Recommend running `/vrs-test-scenario <ID>` for detailed diagnosis

## Regression Thresholds

- **> 5 point drop**: Flag as REGRESSION
- **> 15 point drop**: Flag as CRITICAL REGRESSION
- **Score drops to 0**: Flag as BROKEN
- **New scenario fails on first run**: Not a regression, just a new baseline

## Key Principle

Regressions are detected automatically. No manual "did I break anything?" needed. Every change is measured against history.
