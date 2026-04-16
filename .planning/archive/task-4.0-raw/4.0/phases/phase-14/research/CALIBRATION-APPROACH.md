# Calibration Approach Decision Document

**Created:** 2026-01-08
**Status:** COMPLETE
**Research Task:** R14.1

---

## Executive Summary

After analyzing the BSKG codebase, we found substantial existing calibration infrastructure in `src/true_vkg/learning/bounds.py` that uses Wilson score intervals and Bayesian updating. The `benchmarks/confidence_bounds.json` already contains per-pattern calibration data for 30+ patterns with sample sizes ranging from 0 to 34. Phase 14 should **extend** this infrastructure rather than rebuild from scratch.

---

## Method Selection

### Decision: Bayesian + Wilson Score (Already Implemented)

**Selected Method:** Bayesian confidence with Wilson score intervals (hybrid approach)

**Rationale:**
- Already implemented in `learning/bounds.py`
- Wilson score handles small samples well (many patterns have n < 20)
- Bayesian updating with prior_strength=2.0 provides stability
- Absolute bounds (0.15 min, 0.98 max) prevent runaway confidence

**Code Reference:**
```python
# src/true_vkg/learning/bounds.py:66
def bayesian_confidence(
    true_positives: int,
    false_positives: int,
    prior_strength: float = 2.0,
    prior_probability: float = 0.5,
) -> float:
```

**Minimum Data Requirement:** 5 samples (patterns with < 5 fall back to defaults)

---

## Calibration Scope Decision

### Decision: Hierarchical (Per-Pattern with Global Fallback)

**Selected Scope:** Per-pattern calibration with global fallback

**Current Implementation:**
- `BoundsManager.get(pattern_id)` returns pattern-specific bounds
- `ConfidenceBounds.default(pattern_id)` provides fallback

**Evidence from `confidence_bounds.json`:**
| Pattern Type | Sample Sizes | Observed Precision Range |
|-------------|--------------|-------------------------|
| dos-* | 25-34 | 0.91-1.0 |
| oracle-* | 6-14 | 0.0-1.0 (high variance) |
| token-* | 9-26 | 0.5-1.0 |
| auth-* | 0-20 | 0.7-1.0 |
| vm-* | 12-16 | 0.73-1.0 |

**Minimum Samples for Per-Pattern:** 5 (current threshold)
**Fallback Strategy:** Use default bounds (0.30, 0.95) with initial=0.7

---

## Data Requirements

### Current State:
- **Total patterns tracked:** 32+ in confidence_bounds.json
- **Patterns with sufficient data (n >= 10):** 24
- **Patterns needing more data:** 8 (oracle-001, mev-001, mev-002, auth-005, etc.)

### Recommended Actions:
1. No need for new ground truth collection - existing benchmark data is sufficient
2. Focus on calibration visualization and validation
3. Add Platt/Isotonic calibrators as optional enhancement for patterns with n >= 30

### Acceptable Data Sources:
1. DVDeFi benchmark results (primary)
2. SmartBugs benchmark results (secondary)
3. Pattern test fixtures (for TP/FP counting)

---

## Context Factor Strategy

### Decision: Manual Tuning with Data Validation

**Approach:** Start with manual multipliers, validate against observed precision

**Initial Weights (from Phase 14 TRACKER):**
```yaml
context_factors:
  reentrancy_guard_multiplier: 0.3    # Strong guard
  trusted_call_multiplier: 0.5        # Moderate mitigation
  access_control_multiplier: 0.7      # Partial mitigation
```

**Adjustment Caps:**
- Minimum multiplier: 0.1 (never fully dismiss)
- Maximum multiplier: 1.0 (never amplify)

**Validation Required:**
- Track context factor applications
- Measure post-adjustment precision
- Tune multipliers based on outcomes

---

## Implementation Recommendations

### Phase 14 Task Adjustments:

1. **Task 14.1 (Ground Truth)** → SKIP or MINIMAL
   - Existing `benchmarks/` data is sufficient
   - Focus on loading and organizing existing data

2. **Task 14.2 (Calibration Model)** → EXTEND
   - Add isotonic/Platt calibrators as optional layer
   - Keep existing Bayesian as default

3. **Task 14.3 (Per-Pattern)** → ALREADY DONE
   - `BoundsManager` handles per-pattern bounds
   - Add visualization and reporting

4. **Task 14.4 (Context Factors)** → NEW
   - Implement context multiplier system
   - Add to finding confidence calculation

5. **Task 14.5 (Calibration Plot)** → NEW
   - Create reliability diagrams
   - Plot predicted vs actual precision

6. **Task 14.6 (Explanation)** → NEW
   - Add confidence explanations to findings
   - Show contributing factors

7. **Task 14.7 (Validation)** → NEW
   - Measure Brier score
   - Compare before/after calibration

---

## Architecture Decision

### Create `src/true_vkg/calibration/` Module

New module should:
1. Import from `learning/bounds.py` (don't duplicate)
2. Add higher-level calibration API
3. Add visualization tools
4. Add validation metrics

**Module Structure:**
```
src/true_vkg/calibration/
├── __init__.py           # Public API
├── calibrator.py         # Isotonic/Platt wrappers (optional)
├── context.py            # Context factor multipliers
├── visualization.py      # Reliability diagrams
├── explanation.py        # Confidence explanations
└── validation.py         # Brier score, ECE metrics
```

---

## References

1. **Existing Implementation:** `src/true_vkg/learning/bounds.py`
2. **Current Data:** `benchmarks/confidence_bounds.json`
3. **sklearn Calibration:** https://scikit-learn.org/stable/modules/calibration.html
4. **Wilson Score:** Used for confidence intervals with small samples

---

## Validation Criteria Met

- [x] All 4 research questions answered
- [x] Method selection justified with existing code
- [x] Scope decision matches existing implementation
- [x] Data requirements assessed from current benchmarks
- [x] Implementation plan is concrete with file paths
