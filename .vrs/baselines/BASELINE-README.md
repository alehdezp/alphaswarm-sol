# GA Regression Baseline

## Overview

This directory contains the regression baseline captured for GA validation.
Future releases should compare against this baseline to detect performance regressions.

## Baseline File

- **File:** `ga-baseline.json`
- **Captured:** See `created_at` field in JSON
- **Commit:** See `git.commit` field in JSON

## Metrics Captured

| Metric | Value | Target |
|--------|-------|--------|
| Precision | See JSON | >= 70% |
| Recall | See JSON | >= 60% |
| F1 Score | See JSON | >= 65% |

## Regression Thresholds

- Precision: max 5% drop allowed
- Recall: max 5% drop allowed
- F1 Score: max 5% drop allowed

## Running Regression Tests

```bash
# After running new tests
uv run python scripts/regression_test.py \
  --baseline .vrs/baselines/ga-baseline.json \
  --current .vrs/ga-metrics/aggregated-metrics.json
```

## Updating Baseline

Only update baseline for major releases after thorough validation:

```bash
./scripts/run_baseline_capture.sh
```

## Baseline Contents

The baseline JSON contains:

```json
{
  "baseline_type": "ga-release",
  "created_at": "2026-01-30T...",
  "git": {
    "commit": "abc123...",
    "branch": "feature/07.3-...",
    "commit_date": "2026-01-30 ...",
    "dirty": false
  },
  "version": {
    "alphaswarm_version": "0.5.0"
  },
  "metrics": {
    "precision": 0.75,
    "recall": 0.65,
    "f1_score": 0.70,
    "true_positives": 45,
    "false_positives": 15,
    "false_negatives": 24,
    "tests_count": 5,
    "total_duration_ms": 125000
  },
  "by_vulnerability_type": {
    "reentrancy": {"precision": 0.80, "recall": 0.75, ...},
    "access-control": {"precision": 0.70, "recall": 0.60, ...}
  },
  "regression_thresholds": {
    "precision_max_drop": 0.05,
    "recall_max_drop": 0.05,
    "f1_max_drop": 0.05
  }
}
```

## Flexible Workflow Baselines

The baseline can also capture metrics from flexible workflow configurations:

- **Solo mode:** Single-agent detection metrics
- **Swarm mode:** Multi-agent verification metrics
- **Skip stages:** Reduced pipeline metrics
- **Tier A only:** Pattern-matching-only metrics

## Notes

- Baseline captures REAL metrics from actual tests
- Git commit is recorded for traceability
- Regression thresholds are configurable per metric
- Future releases should never drop more than 5% from baseline
- Update baseline only for major releases after thorough validation
