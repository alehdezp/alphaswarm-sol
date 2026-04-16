# Phase 14: Confidence Calibration

**Status:** ✅ COMPLETE
**Priority:** MEDIUM - Meaningful confidence scores
**Last Updated:** 2026-01-08
**Author:** BSKG Team

---

## Quick Reference

| Field | Value |
|-------|-------|
| Entry Gate | Phase 13 complete + benchmark ground truth available |
| Exit Gate | Calibration model trained, validated, per-pattern calibration working |
| Philosophy Pillars | Knowledge Graph, Self-Improvement |
| Threat Model Categories | False Positives, Trust in Findings |
| Estimated Hours | 43h |
| Actual Hours | ~20h |
| Task Count | 7 tasks + 1 research |
| Test Count | 62 tests ✅ |

---

## IMPLEMENTATION NOTES

### Implementation Summary (2026-01-08)

Phase 14 was implemented by leveraging existing infrastructure in `learning/bounds.py` which already had Wilson score intervals and Bayesian confidence updating. The calibration module was built as a new `src/true_vkg/calibration/` package with 6 submodules:

1. **dataset.py** (Task 14.1) - Ground truth dataset management with `CalibrationDataset`, `LabeledFinding`, and `Label` types. Loads from existing `benchmarks/confidence_bounds.json`.

2. **calibrator.py** (Tasks 14.2 & 14.3) - `PatternCalibrator` with Bayesian (default), Isotonic, and Platt scaling methods. Per-pattern calibration with global fallback.

3. **context.py** (Task 14.4) - `ContextFactors` for guard-based confidence adjustment with 20+ predefined multipliers (e.g., `has_reentrancy_guard: 0.2`).

4. **visualization.py** (Task 14.5) - `CalibrationPlotter` for reliability diagrams and ECE visualization.

5. **explanation.py** (Task 14.6) - `ConfidenceExplainer` for human-readable confidence explanations with markdown/text/JSON output.

6. **validation.py** (Task 14.7) - `CalibrationValidator` with Brier score, ECE, MCE metrics and comparison tools.

### Key Design Decisions

1. **Reused existing infrastructure**: Imported from `learning/bounds.py` rather than reimplementing Wilson score intervals.

2. **Hierarchical calibration**: Per-pattern when n >= 5 samples, global fallback otherwise.

3. **Method selection**:
   - Isotonic: n >= 30 (non-parametric, flexible)
   - Platt: n >= 20 (logistic, stable)
   - Bayesian: default (prior-weighted, works with sparse data)

4. **Context factors**: Multiplicative by default with min_multiplier=0.1 floor to never fully dismiss.

### Files Created

```
src/true_vkg/calibration/
├── __init__.py          # Public API exports
├── calibrator.py        # Tasks 14.2 & 14.3
├── context.py           # Task 14.4
├── dataset.py           # Task 14.1
├── explanation.py       # Task 14.6
├── validation.py        # Task 14.7
└── visualization.py     # Task 14.5

tests/test_calibration.py  # 62 tests
```

---

## Task Registry - COMPLETE

| ID | Task | Est. | Actual | Status |
|----|------|------|--------|--------|
| R14.1 | Calibration Techniques Research | 4h | 2h | ✅ COMPLETE |
| 14.1 | Ground Truth Collection | 6h | 3h | ✅ COMPLETE |
| 14.2 | Calibration Model | 8h | 4h | ✅ COMPLETE |
| 14.3 | Per-Pattern Calibration | 6h | 3h | ✅ COMPLETE |
| 14.4 | Context Factor Integration | 6h | 3h | ✅ COMPLETE |
| 14.5 | Calibration Plot | 3h | 2h | ✅ COMPLETE |
| 14.6 | Confidence Explanation | 4h | 2h | ✅ COMPLETE |
| 14.7 | Calibration Validation | 6h | 3h | ✅ COMPLETE |

**Total: 43h estimated → ~22h actual (49% efficiency gain)**

---

## Test Results

```
tests/test_calibration.py - 62 tests PASSED

Test Categories:
- TestLabel: 2 tests
- TestLabeledFinding: 3 tests
- TestCalibrationDataset: 7 tests
- TestPatternCalibrator: 7 tests
- TestContextFactors: 9 tests
- TestCalibrationPlotter: 7 tests
- TestConfidenceExplainer: 10 tests
- TestCalibrationValidator: 14 tests
- TestIntegration: 3 tests
```

---

## Public API

```python
from true_vkg.calibration import (
    # Dataset (14.1)
    CalibrationDataset,
    LabeledFinding,
    Label,
    load_benchmark_data,

    # Calibrator (14.2 & 14.3)
    PatternCalibrator,
    CalibratorConfig,
    CalibrationMethod,
    calibrate_finding,

    # Context (14.4)
    ContextFactors,
    ContextConfig,
    apply_context_factors,
    GUARD_MULTIPLIERS,

    # Visualization (14.5)
    CalibrationPlotter,
    plot_reliability_diagram,
    plot_confidence_histogram,
    plot_before_after,

    # Explanation (14.6)
    ConfidenceExplainer,
    ConfidenceExplanation,
    explain_confidence,
    format_explanation,

    # Validation (14.7)
    CalibrationValidator,
    CalibrationMetrics,
    brier_score,
    expected_calibration_error,
    validate_calibration,
)
```

---

## Usage Examples

### Basic Calibration

```python
from true_vkg.calibration import PatternCalibrator, calibrate_finding

# Load from existing bounds
calibrator = PatternCalibrator.from_bounds_file("benchmarks/confidence_bounds.json")

# Calibrate a finding
result = calibrator.calibrate("vm-001-classic", 0.8)
print(f"Calibrated: {result.calibrated_confidence}")  # ~0.75
```

### With Context Factors

```python
from true_vkg.calibration import ContextFactors, apply_context_factors

# Apply guard-based adjustment
result = apply_context_factors(
    confidence=0.85,
    present_factors={"has_reentrancy_guard", "has_access_gate"},
    pattern_id="vm-001"
)
# Significantly reduced due to guards
print(f"Adjusted: {result.adjusted_confidence}")
```

### Generate Explanation

```python
from true_vkg.calibration import explain_confidence, format_explanation

explanation = explain_confidence(
    confidence=0.75,
    pattern_id="vm-001",
    positive_evidence=["External call before state update"],
    negative_evidence=["Has reentrancy guard"],
)

print(format_explanation(explanation, "markdown"))
```

### Validation

```python
from true_vkg.calibration import CalibrationValidator, validate_calibration

metrics = validate_calibration(
    predictions=[0.8, 0.6, 0.7, 0.9],
    actuals=[1, 0, 1, 1],
)

print(f"ECE: {metrics.expected_calibration_error}")
print(f"Well calibrated: {metrics.is_well_calibrated()}")
```

---

## Completion Checklist

- [x] All tasks completed (7/7)
- [x] All tests passing (62/62)
- [x] Documentation updated
- [x] No regressions introduced
- [x] Phase 15 unblocked

**Exit Gate:** ✅ PASSED - Calibration module complete with comprehensive tests.

---

*Phase 14 Tracker | Version 3.0 (Complete) | 2026-01-08*

---

## Alignment Addendum (Workstream P)

### Workstream P: Alignment Tasks

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P14.P.1 | Define score-to-bucket mapping rules + overrides | `docs/PHILOSOPHY.md`, `src/true_vkg/calibration/` | P10.P.1 | Mapping table | Used by Phase 3 output + Phase 20 audit | Buckets are primary output | New bucket threshold |
| P14.P.2 | Require evidence packets as calibration inputs | `docs/PHILOSOPHY.md`, `src/true_vkg/calibration/` | P2.P.4 | Input contract notes | Phase 2 exports referenced | Evidence packets immutable | Missing packet signals |

### Review Tasks (Required + Phase-Specific)

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P14.R.1 | Phase necessity review (keep/cut/modify) | `task/4.0/MASTER.md`, `docs/PHILOSOPHY.md` | - | Decision log in tracker | Decision referenced in alignment sweep | None | Phase outputs no longer needed |
| P14.R.2 | Task necessity review for P14.P.* | `task/4.0/phases/phase-14/TRACKER.md`, `task/codex/vkg_4_0_alignment_super_task.md` | P14.P.1-P14.P.2 | Task justification log | Each task has keep/merge decision | Avoid overlap with Phase 7 | Redundant task discovered |
| P14.R.3 | Conflict review with downstream phases | `task/4.0/MASTER.md` | P14.P.1-P14.P.2 | Conflict notes in tracker | Conflicts resolved or escalated | Tier A/Tier B separation | Conflict discovered |
| P14.R.4 | Check conflicts with Phase 7 learning policies | `task/4.0/phases/phase-7/TRACKER.md` | P14.P.1 | Policy compatibility note | Learning gates preserved | Learning conflict | Conflict detected |

### Dynamic Task Spawning (Alignment)

**Trigger:** Calibration drift detected.
**Spawn:** Add recalibration task.
**Example spawned task:** P14.P.3 Recalibrate buckets after drift detection.
