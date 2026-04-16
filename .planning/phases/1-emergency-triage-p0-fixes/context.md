# Phase 1: Emergency Triage (P0 Fixes)

## Goal

Unblock the product by fixing pipeline-stopping bugs, with test evidence that each fix is durable.

## Status

Completed in roadmap, but this context captures the missing rigor discovered later in Phase 1.1 and current milestone audits.

## Philosophy Alignment (Reality Check)

Phase 1 shipped critical fixes, but not all proof standards from `docs/PHILOSOPHY.md` were in place at the time:

- Fixes landed before complete integration-gate coverage.
- Orchestration markers and proof-token requirements were not enforced.
- Some claims were corrected later by Phase 1.1 and Phase 2.1.

## Critical Gaps Still Relevant

1. VulnDocs validation is still not 100% (current state documents failing entries).
2. `--scope` and frontmatter regressions need explicit, permanent regression coverage tied to release gates.
3. P0 completion did not include marker/proof-token compliance tests.
4. Evidence-first execution was improved later, not by Phase 1 itself.

## Key Files

- `src/alphaswarm_sol/queries/patterns.py`
- `src/alphaswarm_sol/orchestration/router.py`
- `src/alphaswarm_sol/orchestration/handlers.py`
- `src/alphaswarm_sol/cli/orchestrate.py`
- `tests/test_phase_1_1_integration.py`
- `tests/test_skills_package.py`

## Plans (If Re-run Today, Test-First)

### 1-01: Write Failing Regression Tests First

- Add failing integration tests for PatternEngine API compatibility.
- Add failing router-resume tests proving no repeated phase loop.
- Add failing VulnDocs full-corpus validation test.

### 1-02: Add CLI and Skill Contract Tests

- Add failing test for `orchestrate start --scope` behavior and scope composition.
- Add failing frontmatter gate test: reject `skill:` and require `name:` for shipped skills.
- Add failing deprecation-warning test for provider imports.

### 1-03: Implement the P0 Fixes

- Patch code only after failing tests exist.
- Keep each fix atomic and mapped to a gate.

### 1-04: Add Marker and Proof-Token Checks

- Add tests that assert required transcript markers for the fixed flows.
- Add minimal proof-token artifact check in `.vrs/` outputs.

### 1-05: Evidence Audit

- Produce a concise evidence report for each fix: failing test -> patch -> passing test.

## Interactive Validation Method (Agent Teams + JJ Workspace)

- Run each P0 replay in a dedicated `jj` workspace.
- Use a small team pattern for verification:
  - `attacker` tries to break the fix.
  - `defender` checks guards and edge cases.
  - `verifier` confirms evidence sufficiency.
- Require transcripts and command logs for all replay runs.

## Non-Vanity Metrics

- P0 regression pass rate on real integration tests.
- VulnDocs pass count and fail count (absolute numbers, not percentages only).
- Router advancement correctness (no repeated action loops for same state).
- Number of required orchestration markers emitted by P0 validation runs.

## Recommended Subagents

- `vrs-test-builder`
- `vrs-secure-reviewer`
- `vrs-attacker`
- `vrs-defender`
- `vrs-verifier`

## Exit Gate

All P0 fixes are backed by durable regression tests, marker/proof checks, and honest counts that match `.planning/STATE.md`.

## Research Inputs

- `.planning/phases/1.1-critical-review-p0-fixes/PLAN.md`
- `.planning/phases/1.1-critical-review-p0-fixes/context.md`
- `.planning/new-milestone/reports/w2-p0-fixes-plan.md`
- `docs/PHILOSOPHY.md`

## 2026-02-09 Reordering Audit Context

### Global Sequence

Execution order after Phase 2.1 is now fixed:
`3.1 -> 3.2 -> 4 -> 6 -> 7 -> 5 -> 8`

### Iteration Notes (1 -> 3)

1. Iteration 1: identified missing hard regression carry-forward from P0 fixes.
2. Iteration 2: required marker/proof-token enforcement to be moved into early gates.
3. Iteration 3: final sequence accepted only after fail-closed enforcement and deterministic replay gates were added downstream.

### This Phase's Role

Phase 1 remains the non-negotiable regression foundation. Later phases inherit these guarantees and cannot weaken them.

### Mandatory Carry-Forward Gates

- PatternEngine API compatibility tests must remain green.
- Router resume advancement and no-loop behavior must remain green.
- Full VulnDocs validation must remain a blocker, not informational.
- Skill frontmatter and `--scope` behavior checks remain release-protecting regressions.

### Debug/Artifact Contract

- Any regression in inherited Phase 1 gates must write `.vrs/debug/phase-1/repro.json`.
- Repro artifact must include command, environment hash, and failing test IDs.

### Assigned Research Subagent

- `vrs-secure-reviewer` for regression gate audits

### Research Sources Used

- `docs/PHILOSOPHY.md`
- https://docs.jj-vcs.dev/latest/working-copy/
