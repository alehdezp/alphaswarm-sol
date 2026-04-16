# Phase 2: Property Gap Quick Wins

## Goal

Recover real detection capability by eliminating high-impact orphan-property gaps and triaging broken patterns.

## Status

Completed in roadmap, with major reality corrections captured by Phase 2.1.

## Philosophy Alignment (Reality Check)

Phase 2 created real value, but the honest picture requires Phase 2.1 evidence:

- Pattern rescue claims needed validation and were partially corrected later.
- Triaging and orphan baselines required follow-through and ratcheting.
- Behavior-first detection value exists, but coverage is still incomplete.

## Critical Gaps Still Relevant

1. Quarantined patterns still depend on missing properties.
2. Orphan properties remain and reduce effective recall.
3. CI catches existence mismatches better than semantic correctness.
4. Validation evidence is strong for sampled patterns, not complete for the whole active set.

## Key Files

- `src/alphaswarm_sol/kg/builder/functions.py`
- `src/alphaswarm_sol/queries/patterns.py`
- `tests/test_pattern_property_coverage.py`
- `vulndocs/.quarantine/`
- `vulndocs/.archive/`

## Plans (If Re-run Today, Test-First)

### 2-01: Build Failing Detection Tests for Priority Gaps

- Add TP and TN tests for top-impact rescued and quarantined pattern families.
- Use real vulnerable and safe contracts before implementing new properties.

### 2-02: Add Property Correctness Tests

- Add tests for high-risk semantic properties, not just property presence.
- Include negative assertions to prevent over-broad property emission.

### 2-03: Implement Missing Properties by ROI

- Prioritize properties that unlock the largest number of quarantined patterns.
- Keep a property -> patterns-unblocked ledger.

### 2-04: Re-run Detection and Ratchet Baselines

- Lower orphan baseline only when tests pass.
- Reject any change that increases totally-broken active patterns.

### 2-05: Runtime Safety and Transparency

- Ensure loader warnings for orphan-dependent patterns are explicit.
- Keep quarantine metadata up to date with remediation status.

## Interactive Validation Method (Agent Teams + JJ Workspace)

- Use isolated `jj` workspaces per property batch.
- Use attacker-defender-verifier team loops on sampled contracts for each batch.
- Keep debate artifacts linked to the exact property changes tested.

## Non-Vanity Metrics

- True-positive and true-negative rates on real contract sets.
- Orphan property count and trend.
- Quarantined pattern restoration rate tied to passing tests.
- Count of active totally-broken patterns (target: zero).

## Recommended Subagents

- `vrs-test-builder`
- `vrs-attacker`
- `vrs-defender`
- `vrs-verifier`
- `vrs-secure-reviewer`

## Exit Gate

Property additions produce measurable detection gains on real contracts, orphan counts trend downward, and restored patterns have evidence-backed passing tests.

## Research Inputs

- `.planning/phases/2.1-critical-review-property-gap/PLAN.md`
- `.planning/phases/2.1-critical-review-property-gap/context.md`
- `.planning/new-milestone/reports/w2-property-gap-plan.md`
- `docs/PHILOSOPHY.md`

## 2026-02-09 Reordering Audit Context

### Global Sequence

Execution order after Phase 2.1 is now fixed:
`3.1 -> 3.2 -> 4 -> 6 -> 7 -> 5 -> 8`

### Iteration Notes (1 -> 3)

1. Iteration 1: confirmed Phase 2 delivered value but left silent-failure risk if orphan controls weaken.
2. Iteration 2: required explicit carry-forward to preserve property integrity and quarantine hygiene.
3. Iteration 3: enforced that benchmark/test phases cannot proceed if orphan baselines regress.

### This Phase's Role

Phase 2 provides recall-critical property coverage foundations. Later phases depend on these being stable and auditable.

### Mandatory Carry-Forward Gates

- Property coverage ratchet cannot regress.
- No active totally-broken patterns.
- Property correctness tests (not only presence tests) remain active.
- Pattern engine orphan warnings remain visible and test-backed.

### Debug/Artifact Contract

- Property regressions must write `.vrs/debug/phase-2/repro.json`.
- Include property IDs, affected pattern IDs, and failing contract fixtures.

### Assigned Research Subagent

- `vrs-pattern-verifier` for property-to-pattern dependency integrity

### Research Sources Used

- `.planning/phases/2.1-critical-review-property-gap/PLAN.md`
- `docs/PHILOSOPHY.md`
- https://conf.researchr.org/details/icse-2025/llm4code-2025-papers/22/SC-Bench-A-Large-Scale-Dataset-for-Smart-Contract-Auditing
