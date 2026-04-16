# Execution Feedback

## Execution Run 2026-02-25 (run-24428afa)

### Wave 0

#### 3.1e-00: ALIGNED
**Criteria state:** 12/12 criteria MET
**Key finding:** All 10 required artifacts present with correct content. Temporal integrity confirmed (decision lock precedes baseline). Per-function baseline: 15 TP / 116 FP across 7 contracts. Property diagnostic confirmed YAML-only fix path for Plan 01. Minor deviations (JSON structure wrapping, field name mapping) classified as reasonable.
**Corrections applied:** N/A
**Correction success:** N/A
**Research gates:** 0 evaluated

### Wave 1

#### 3.1e-01: ALIGNED (after correction, attempt 1)
**Criteria state:** 12/12 criteria MET
**Key finding:** Access-tierb-001 pattern fixed (added `is_deposit_like eq true` to `none:` block). Precision delta: +0.27pp (Outcome B: weak signal). 3 FPs removed, 15 TPs preserved, 0 regressions. Negative control passed. Deep analysis revealed 83.6% of FPs (97/116) fire with zero any-conditions — the narrow scope was deliberate (proving the loop works, not maximizing delta).
**Corrections applied:** Added `fingerprint_method` field to baseline-before.json meta section. Changed `compute_seconds` from null to 15.0 in cost-summary.json with `compute_seconds_basis: "estimated_from_after_run"`.
**Correction success:** yes
**Per-attempt criteria:** Initial: 10/12 (compute_seconds null, fingerprint_method missing) → Attempt 1: 12/12
**Research gates:** 0 evaluated

#### 3.1e-02: ALIGNED (after correction, attempt 1)
**Criteria state:** 12/12 criteria MET
**Key finding:** Three-instrument LLM measurement (ordering, scale calibration, divergence). Hypothesis scoring (H1/H2/H3). Hallucination check completed. Verdict: GO (synthetic_preliminary). All 7 heuristic dimensions showed NONE validity — boundary ties from extreme score clustering. Self-evaluation concern documented.
**Corrections applied:** Added Forward Action 7 to llm-recommendation.md documenting self-evaluation internal validity concern. Added `line_number_note` field to hallucination-check.json explaining zero LINE_NUMBER checks. Documented model change (claude-sonnet-4-20250514 vs specified claude-sonnet-4-6).
**Correction success:** yes
**Per-attempt criteria:** Initial: 10/12 (in-session eval deviation, LINE_NUMBER unexplained) → Attempt 1: 12/12
**Research gates:** 0 evaluated

#### 3.1e-03: ALIGNED
**Criteria state:** 12/12 criteria MET
**Key finding:** FP taxonomy: 5 descriptive clusters (trivial_structural_match 83.6%, reentrancy_overfiring, multi_pattern_pileup, standard_function_overfiring, implicit_access_control_gap). Action map: per-cluster fix classification. 5 adversarial gaming archetypes. Validity matrix: all 7 dimensions NONE validity. Gameability assessment complete.
**Corrections applied:** N/A
**Correction success:** N/A
**Research gates:** 0 evaluated

### Wave 2

#### 3.1e-04: ALIGNED
**Criteria state:** 12/12 criteria MET
**Key finding:** 35 schema fields extracted across 3 tracks (A: 17 detection, B: 7 evaluation constrained, C: 11 taxonomy). All fields trace to observed artifacts. 3 contradiction pairs resolved from data. 7 Unobserved Phenomena accepted (5→3.1c, 2→3.1f), 2 rejected. Entry protocol: partial_data. Smoke test: 35/35 PASS. No Pydantic code created (anti-v5.0 pattern honored).
**Corrections applied:** N/A
**Correction success:** N/A
**Research gates:** 0 evaluated
