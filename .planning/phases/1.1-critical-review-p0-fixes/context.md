# Phase 1.1: Critical Review — P0 Fixes Foundation

## Goal

Skeptically verify every Phase 1 P0 fix actually works end-to-end, adds real value to the pipeline, and has meaningful test coverage. Identify and close gaps before building on this foundation.

## Phase 1 Research Findings

### FIX-01: PatternEngine API

**Implementation:** COMPLETE — `pattern_dir`, `run_all_patterns()`, `run_pattern()` all exist in `src/alphaswarm_sol/queries/patterns.py:504-597`. Handler at `orchestration/handlers.py:388-390` uses the new API.

**Test Coverage:** WEAK
- `tests/test_patterns.py` (73 lines) tests basic matching only
- NO tests for `run_all_patterns()` or `run_pattern()` methods
- NO tests for `pattern_dir` parameter
- Handler integration untested

**Critical Questions:**
- Does `run_all_patterns()` produce real findings when pointed at `vulndocs/` with a real graph?
- What happens when `pattern_dir` points to an empty or invalid directory?
- Are error paths handled (malformed patterns, missing properties)?

### FIX-02: Orchestrate Resume Infinite Loop

**Implementation:** COMPLETE — Router checks metadata (`graph_built`, `context_loaded`, `patterns_detected`, `beads_created`) before re-routing. All handlers set their completion flags.

**Code locations:**
- Router logic: `orchestration/router.py:178-211`
- Metadata flags: `handlers.py:252,311,393,474`

**Test Coverage:** WEAK
- `tests/test_cli_orchestrate.py:333-370` tests edge cases (not found, complete, failed)
- NO test for the actual fix: "resume after BUILD_GRAPH succeeds → pool advances"
- NO test for router returning WAIT when metadata says phase is complete

**Critical Questions:**
- Can we actually demonstrate a pool transitioning INTAKE → CONTEXT → BEADS?
- Does the metadata persist correctly across process restarts (resume scenario)?
- What happens if handler succeeds but metadata write fails?

### FIX-03: Skill Frontmatter

**Implementation:** COMPLETE — All 20 skill files use `name:` field correctly.
**Test Coverage:** N/A — mechanical fix, verified by grep.
**Assessment:** Low-risk, cosmetic but necessary. No further review needed.

### FIX-04: VulnDocs Validation

**Implementation:** COMPLETE — Schema updated in `src/alphaswarm_sol/vulndocs/schema.py:841-975`.
**Test Coverage:** GOOD — `tests/test_vulndocs_schema.py` (732 lines) covers schema logic thoroughly.
**Gap:** No E2E test that validates ALL real `index.yaml` files in `vulndocs/` directory.

**Critical Questions:**
- Does `uv run alphaswarm vulndocs validate vulndocs/` pass without errors?
- How many of the "74 validated entries" are actually usable by pattern matching?

### FIX-05: --scope Flag Documentation

**Implementation:** COMPLETE — CLAUDE.md updated with correct CLI syntax.
**Assessment:** Documentation-only fix. No further review needed.

### FIX-06: Google Deprecated Warning

**Implementation:** COMPLETE — Lazy import in `llm/providers/google.py:17-23`.
**Assessment:** QoL fix. No further review needed.

## Severity Assessment

| Fix | Pipeline Impact | Test Gap | Review Priority |
|-----|----------------|----------|-----------------|
| FIX-01 | HIGH — patterns are core detection | CRITICAL — no integration test | P0 |
| FIX-02 | HIGH — resume is core workflow | CRITICAL — no integration test | P0 |
| FIX-04 | MEDIUM — validation enables patterns | MODERATE — no E2E test | P1 |
| FIX-03 | LOW — cosmetic | None needed | Skip |
| FIX-05 | LOW — docs only | None needed | Skip |
| FIX-06 | LOW — QoL | None needed | Skip |

## Key Files

- `src/alphaswarm_sol/queries/patterns.py` — PatternEngine
- `src/alphaswarm_sol/orchestration/router.py` — Router state machine
- `src/alphaswarm_sol/orchestration/handlers.py` — Pipeline handlers
- `src/alphaswarm_sol/vulndocs/schema.py` — VulnDocs schema
- `tests/test_patterns.py` — Pattern tests (weak)
- `tests/test_cli_orchestrate.py` — Orchestrate tests (weak)
- `tests/vulndocs/test_schema.py` — Schema tests (good)

## Success Criteria

1. PatternEngine `run_all_patterns()` produces >= 1 finding on a real DVDeFi contract
2. Router returns WAIT (not re-route) after handler sets completion metadata
3. `alphaswarm vulndocs validate vulndocs/` passes on all entries
4. Integration tests written and passing for FIX-01 and FIX-02
5. Honest assessment document: which fixes matter vs which are cosmetic

## 2026-02-09 Reordering Audit Context

### Global Sequence

Execution order after Phase 2.1 is now fixed:
`3.1 -> 3.2 -> 4 -> 6 -> 7 -> 5 -> 8`

### Iteration Notes (1 -> 3)

1. Iteration 1: phase review outputs were strong but lacked hard carry-forward language.
2. Iteration 2: added explicit requirement that Phase 1.1 integration tests remain permanent upstream gates.
3. Iteration 3: confirmed no downstream phase can bypass these integration proofs.

### This Phase's Role

Phase 1.1 is the foundation lock between P0 implementation and all later capability work.

### Mandatory Carry-Forward Gates

- PatternEngine E2E integration on real graphs.
- Router advancement integration proving WAIT/advance semantics.
- Full VulnDocs corpus validation on real entries.
- Marker and evidence-first behavior for these flows must remain enforceable in later phases.

### Debug/Artifact Contract

- Failing carry-forward gate writes `.vrs/debug/phase-1.1/repro.json`.
- Include test target, sample artifact path, and expected/actual behavior.

### Assigned Research Subagent

- `vrs-verifier` for carry-forward gate compliance audits

### Research Sources Used

- `.planning/phases/1.1-critical-review-p0-fixes/PLAN.md`
- `docs/PHILOSOPHY.md`
- https://proceedings.mlr.press/v235/du24e.html
