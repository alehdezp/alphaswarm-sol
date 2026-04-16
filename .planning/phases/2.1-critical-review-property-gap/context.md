# Phase 2.1: Critical Review — Property Gap Reality

## Goal

Skeptically verify that Phase 2 property gap work actually improved detection capability, not just inflated pattern counts. Close the critical gaps that were skipped.

## Phase 2 Research Findings

### PROP-01: Computed-But-Not-Emitted Properties

**Plan target:** 37 properties emitted, rescuing 51 patterns.
**Actual:** 35/37 added (95%).

**Missing properties:**
- `cross_function_reentrancy_surface` — defined in dataclass (line 297) but NOT in props dict
- `cross_function_reentrancy_read` — defined in dataclass (line 298) but NOT in props dict

**Implementation location:** `src/alphaswarm_sol/kg/builder/functions.py:1289-1361`
**Result:** 237 → 332 fully working patterns (40% improvement)

### PROP-02: Derived/Composite Properties

**Plan target:** 15+ derived properties, target 340 working patterns.
**Actual:** 11/11 derived properties added (100%).

**Implementation location:** `functions.py:1348-1360`
- Contract bridges: `is_upgradeable`, `has_timelock`, `has_multisig`, `has_governance`, etc.
- MEV risk composites: `risk_missing_slippage_parameter`, `risk_missing_deadline_parameter`, etc.

### PROP-03: Property Validation CI Gate

**Plan target:** Decreasing baseline, active enforcement.
**Actual:** Gate exists but baseline is FLAT at 223 orphans.

**Test file:** `tests/test_pattern_property_coverage.py` (378 lines)
- `ORPHAN_BASELINE = 223` — never decreased despite adding properties
- Gate prevents regression (orphans can't increase) but doesn't enforce improvement
- Coverage report is informational only (no assertions)

**Actual metrics (2026-02-08):**
- Properties referenced by patterns: 465
- Properties emitted by builder: 346
- Covered: 242 (52%)
- Orphaned: 223

### PROP-04: Dead Patterns Triaged — COMPLETE MISS

**Plan target:** Delete 47 patterns, quarantine 141, ~290 working.
**Actual:** ZERO patterns deleted, ZERO quarantined. 0% complete.

**Current state:**
- 332 fully working patterns (59%)
- 134 partially broken patterns (24%)
- 96 totally broken patterns (17%) — ALL properties are orphans
- **Total: 562 patterns still in active directories**

**Why this matters (silent false negatives):**
When a totally broken pattern is evaluated:
1. Pattern engine loads it
2. Evaluates conditions against function nodes
3. Orphan properties evaluate to `None != expected_value` → no match
4. Returns 0 findings WITH NO ERROR OR WARNING
5. User thinks pattern ran but found nothing — actually it never worked

This is a **correctness bug**, not just cleanup. An auditor trusting AlphaSwarm could miss vulnerabilities because broken patterns report "no findings" instead of "I can't check this."

## Honest Assessment

| Requirement | Planned | Actual | Gap |
|-------------|---------|--------|-----|
| PROP-01 | 37 properties | 35/37 (95%) | 2 missing cross-function reentrancy |
| PROP-02 | 15+ derived | 11/11 (100%) | Done |
| PROP-03 | Decreasing baseline | Flat at 223 | Gate is speed bump, not blocker |
| PROP-04 | 169 delete + 141 quarantine | 0 triaged | **COMPLETE MISS** |

**What v6.0 claimed:** "~290 working patterns (down from 556, 385 pruned)"
**Reality:** 332 working + 96 broken still active. Nothing was pruned — the count just changed in documentation.

## Critical Issues

### Issue 1: 96 Silent False Negatives (P0)
96 patterns silently return no findings. Must quarantine or delete them.

### Issue 2: No Pattern Load Validation Warning (P0)
No log or error when a pattern depends on unavailable properties.

### Issue 3: Flat Baseline (P1)
CI gate baseline never decreased despite implementing properties. Should track improvement.

### Issue 4: 2 Missing Properties (P1)
`cross_function_reentrancy_surface` and `cross_function_reentrancy_read` exist in dataclass but never emitted.

## Key Files

- `src/alphaswarm_sol/kg/builder/functions.py` — Property emission (lines 1289-1361)
- `src/alphaswarm_sol/queries/patterns.py` — Pattern engine (no orphan validation)
- `tests/test_pattern_property_coverage.py` — CI gate (weak baseline)
- `vulndocs/` — All 562 patterns (96 should be quarantined)

## Success Criteria

1. 96 totally broken patterns quarantined or deleted with documented justification
2. Pattern engine warns when loading patterns with orphan properties
3. CI gate baseline updated to reflect actual improvement (223 → lower)
4. 2 missing cross-function reentrancy properties emitted
5. 10 "rescued" patterns proven to detect real vulnerabilities on DVDeFi contracts
6. Honest pattern count in documentation matches verified reality

## Hard Dependencies and Gates (Phase Sequencing)

Phase 2.1 must enforce the following gates before Phase 3 can start. These are non-negotiable and must be backed by test output, inventory reports, or documented evidence.

### Gate A: Property Integrity

Conditions:
1. Every property declared in the dataclass is emitted in the builder property map.
2. Two missing properties (`cross_function_reentrancy_surface`, `cross_function_reentrancy_read`) are emitted and verified on at least one real contract.
3. The property coverage test fails on any newly introduced orphan property reference.

Evidence required:
1. Updated property map diff and a passing coverage test.
2. One real-contract graph run showing the two properties set (not always `None`/`False`).

### Gate B: Orphan Warnings and Broken-Pattern Safety

Conditions:
1. Pattern engine logs a warning when a pattern references an orphan property.
2. No active pattern in `vulndocs/` has all properties orphaned.
3. Orphan baseline is reduced below 223 and locked as the new baseline.

Evidence required:
1. Log or test output demonstrating orphan warnings.
2. Validation output showing zero totally-broken patterns in active directories.
3. Updated baseline value and a passing test run.

### Gate C: Documentation Honesty

Conditions:
1. Published counts (active patterns, quarantined, deleted) match validation output.
2. Any claim of "working patterns" includes the definition and the validation method.
3. No documentation asserts pruning or triage that did not actually occur.

Evidence required:
1. Validation report or inventory snapshot committed with the doc update.
2. Doc changes that include explicit counts and reference the validation source.

## 2026-02-09 Reordering Audit Context

### Global Sequence

Execution order after this completed phase is now fixed:
`3.1 -> 3.2 -> 4 -> 6 -> 7 -> 5 -> 8`

### Iteration Notes (1 -> 3)

1. Iteration 1: phase successfully exposed reality gaps but did not explicitly bind downstream sequencing.
2. Iteration 2: added explicit phase-sequencing hard gates (property integrity, orphan safety, documentation honesty).
3. Iteration 3: strict review kept these as mandatory upstream blockers for all later phases.

### This Phase's Role

Phase 2.1 is the honesty checkpoint that prevents silent false negatives from propagating into E2E, debate, and benchmark claims.

### Mandatory Carry-Forward Gates

- Gate A Property Integrity
- Gate B Orphan Warnings and Broken-Pattern Safety
- Gate C Documentation Honesty

### Debug/Artifact Contract

- Any Gate A/B/C regression writes `.vrs/debug/phase-2.1/repro.json`.
- Repro includes property list, pattern IDs, coverage output, and validation output paths.

### Assigned Research Subagent

- `vrs-regression-hunter` for ongoing property-integrity drift detection

### Research Sources Used

- `.planning/phases/2.1-critical-review-property-gap/PLAN.md`
- `docs/PHILOSOPHY.md`
- https://arxiv.org/abs/2601.06112
