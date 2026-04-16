# Phase 1.1 Plan: Critical Review — P0 Fixes Foundation

**Phase:** 1.1
**Goal:** Skeptically verify P0 fixes work end-to-end with meaningful tests
**Status:** PLANNED
**Context:** context.md

---

## Plan 1.1-01: Verify PatternEngine API End-to-End

**Objective:** Prove `run_all_patterns()` and `run_pattern()` produce real findings, not just exist.

**Tasks:**
1. Build a graph on a DVDeFi challenge contract (e.g., Unstoppable)
2. Run `PatternEngine(pattern_dir=vulndocs/).run_all_patterns(graph)`
3. Document: How many patterns loaded? How many findings? Which patterns matched?
4. Run `run_pattern(graph, "specific-pattern-id")` on a known-vulnerable function
5. If zero findings: diagnose why (property mismatch? graph shape? pattern conditions?)

**Verification:**
- [ ] `run_all_patterns()` completes without error on real graph
- [ ] At least 1 pattern produces a finding with code location
- [ ] `run_pattern()` returns findings for a pattern known to match the contract

**If it fails:** Document exactly where it breaks. This determines Phase 3 scope.

---

## Plan 1.1-02: Verify Orchestrate Resume State Advancement

**Objective:** Prove a pool actually transitions INTAKE → CONTEXT → BEADS via resume.

**Tasks:**
1. Create a test pool with `orchestrate start` on a simple contract
2. Verify pool starts in INTAKE state
3. Verify BUILD_GRAPH handler sets `graph_built = True` in metadata
4. Verify router returns WAIT (not BUILD_GRAPH again) after metadata is set
5. Write an integration test that exercises the full state transition

**Verification:**
- [ ] Router returns `RouteAction.WAIT` when `graph_built = True`
- [ ] Router returns `RouteAction.WAIT` when `context_loaded = True`
- [ ] No infinite loop: resume advances the pool, does not repeat the same action
- [ ] Integration test written and passing

**If it fails:** Document the exact metadata/router state where loop occurs.

---

## Plan 1.1-03: Verify VulnDocs Validation on All Real Entries

**Objective:** Prove all vulndocs entries validate, not just the schema unit tests.

**Tasks:**
1. Run `uv run alphaswarm vulndocs validate vulndocs/` — capture full output
2. Count successes vs failures
3. For any failures: classify as schema bug vs data bug
4. Cross-check: how many validated entries are actually referenced by working patterns?

**Verification:**
- [ ] Command completes without errors
- [ ] >= 70 entries validate successfully (claimed: 74)
- [ ] Any failures documented with root cause

---

## Plan 1.1-04: Write Missing Integration Tests

**Objective:** Fill the critical test gaps for FIX-01 and FIX-02.

**Tasks:**
1. Write `test_pattern_engine_run_all_patterns_real()`:
   - Builds graph on test contract
   - Runs `PatternEngine(pattern_dir=vulndocs/).run_all_patterns(graph)`
   - Asserts: completes without error, returns list of findings
   - Tests both `run_all_patterns()` and `run_pattern()` with specific pattern ID

2. Write `test_router_advances_after_handler_completion()`:
   - Creates pool in INTAKE
   - Sets `graph_built = True` in metadata
   - Routes pool → asserts WAIT action (not BUILD_GRAPH)
   - Repeats for context_loaded, patterns_detected, beads_created

3. Write `test_vulndocs_all_entries_validate()`:
   - Iterates all `index.yaml` files in vulndocs/
   - Validates each with VulnDocIndex schema
   - Asserts no ValidationError raised

**Verification:**
- [ ] All 3 tests pass with `uv run pytest tests/test_phase_1_1_integration.py -v`
- [ ] Tests use real data (vulndocs/, real contracts), not mocks

---

## Plan 1.1-05: Critical Assessment Document

**Objective:** Honest written assessment of which P0 fixes add real value.

**Tasks:**
1. For each FIX: classify as PIPELINE-CRITICAL, QUALITY, or COSMETIC
2. Document which fixes actually unblock the E2E pipeline
3. Document which fixes have regression-proof tests vs none
4. Rate overall Phase 1 effectiveness: did it unblock the next phase?
5. List any new issues discovered during review

**Output:** `.planning/phases/1.1-critical-review-p0-fixes/ASSESSMENT.md`

**Assessment criteria:**
- Pipeline Critical = without this fix, E2E audit cannot complete
- Quality = improves reliability but not blocking
- Cosmetic = nice-to-have, no pipeline impact

---

## Execution Order

```
1.1-01 (verify patterns) ──┐
1.1-02 (verify resume)  ───┤──► 1.1-04 (write tests) ──► 1.1-05 (assessment)
1.1-03 (verify vulndocs) ──┘
```

Plans 01, 02, 03 can run in parallel. Plan 04 depends on their results. Plan 05 is final synthesis.

---

## Exit Gate

Phase 1.1 is COMPLETE when:
1. PatternEngine integration test passes on real data
2. Router state advancement integration test passes
3. VulnDocs CLI validation passes on all entries
4. All 3 integration tests committed and green
5. Critical assessment document written with honest pipeline impact analysis
