# Phase 2.1 Plan: Critical Review — Property Gap Reality

**Phase:** 2.1
**Goal:** Verify property gap work improved real detection, fix the skipped pattern triage
**Status:** PLANNED
**Context:** context.md

---

## Plan 2.1-01: Verify "Rescued" Patterns Detect Real Vulnerabilities

**Objective:** Prove that patterns rescued by PROP-01/02 actually find bugs, not just parse.

**Tasks:**
1. Identify 10 patterns that were "rescued" (broken before PROP-01, working after)
2. For each: find a DVDeFi or test contract where the vulnerability exists
3. Build graph on that contract, run the specific pattern
4. Document: did it produce a finding? Was the finding correct? False positive?
5. Score: X/10 patterns produce true positive findings

**Verification:**
- [ ] 10 rescued patterns identified with before/after status
- [ ] Each pattern tested against a real contract with known vulnerability
- [ ] >= 5/10 produce correct findings (true positives)
- [ ] Any false positives or false negatives documented

**If < 5/10 work:** The "rescued" claim is inflated. Document why patterns fail even with correct properties.

---

## Plan 2.1-02: Verify Emitted Properties Are Actually Used

**Objective:** Prove the 37 emitted properties connect to working patterns, not emitted into void.

**Tasks:**
1. For each of the 35 emitted properties: count how many patterns reference it
2. Identify any properties emitted by PROP-01 that zero patterns reference (waste)
3. Check the 2 missing properties (`cross_function_reentrancy_surface`, `cross_function_reentrancy_read`): implement and emit them
4. Verify property values are correct on a real contract (not just emitted as False/None)

**Verification:**
- [ ] All 35 properties mapped to pattern count (X patterns reference property Y)
- [ ] Any zero-reference properties flagged as dead code
- [ ] 2 missing properties implemented and emitted
- [ ] Property values verified correct on >= 1 real contract

---

## Plan 2.1-03: Audit Property Validation Gate

**Objective:** Determine if the CI gate catches real problems or just counts.

**Tasks:**
1. Read `tests/test_pattern_property_coverage.py` completely
2. Introduce a deliberate regression: add an orphan property reference to a pattern
3. Run the test — does it catch the regression? What error message?
4. Lower the baseline from 223 to the actual current orphan count
5. Add assertion: fail if any pattern has ALL properties orphaned (catch totally-broken patterns)

**Verification:**
- [ ] Gate catches deliberate orphan introduction (regression test works)
- [ ] Baseline updated to reflect current reality
- [ ] New assertion catches totally-broken patterns (96 should now fail or warn)

---

## Plan 2.1-04: Execute Pattern Triage (The Missing PROP-04)

**Objective:** Do what Phase 2 skipped: quarantine broken patterns, delete dead ones.

**Tasks:**
1. Identify all 96 totally-broken patterns (all properties are orphans)
2. For each: determine if it's DELETE (unrealistic/aspirational) or QUARANTINE (valid but waiting for properties)
3. Delete patterns classified as unrealistic (move to `vulndocs/.deleted/` with reason)
4. Quarantine patterns waiting for properties (move to `vulndocs/.quarantine/` with required properties list)
5. Add pattern engine validation: log warning when loading patterns with orphan properties
6. Update pattern count documentation to match verified reality

**Verification:**
- [ ] 96 broken patterns classified (delete vs quarantine) with documented rationale
- [ ] Deleted patterns moved to `vulndocs/.deleted/` with reason files
- [ ] Quarantined patterns moved to `vulndocs/.quarantine/` with metadata
- [ ] Pattern engine logs warning for orphan-dependent patterns
- [ ] `uv run alphaswarm vulndocs validate vulndocs/` passes (no broken patterns in active dirs)
- [ ] Documentation updated: honest count of active patterns

---

## Plan 2.1-05: Critical Assessment — Did Property Gap Work Improve Quality?

**Objective:** Honest written assessment of Phase 2 impact on detection capability.

**Tasks:**
1. Before/after comparison:
   - Before PROP-01/02: 237 fully working patterns
   - After PROP-01/02: 332 fully working patterns
   - After PROP-04 triage: X active patterns (all verified working)
2. Detection capability change: did any of the rescued patterns find bugs that were previously missed?
3. Test quality assessment: do the property coverage tests prove behavior or count beans?
4. False positive assessment: did adding properties increase false positive rate?
5. Grade Phase 2: A/B/C/D/F with justification

**Output:** `.planning/phases/2.1-critical-review-property-gap/ASSESSMENT.md`

**Grading criteria:**
- A: All 4 PROPs delivered, patterns proven to find real bugs
- B: 3/4 PROPs delivered, detection capability improved
- C: Properties added but unproven, triage incomplete
- D: Properties added but no evidence they help detection
- F: Net negative (added complexity without value)

---

## Execution Order

```
2.1-01 (verify rescued patterns) ──┐
2.1-02 (verify properties used)  ──┤──► 2.1-04 (pattern triage) ──► 2.1-05 (assessment)
2.1-03 (audit CI gate)           ──┘
```

Plans 01, 02, 03 can run in parallel. Plan 04 depends on their findings. Plan 05 is final synthesis.

---

## Exit Gate

Phase 2.1 is COMPLETE when:
1. >= 5/10 rescued patterns produce true positive findings on real contracts
2. 96 broken patterns quarantined or deleted with documented rationale
3. CI gate baseline updated and catches totally-broken patterns
4. 2 missing properties implemented
5. Pattern engine warns on orphan-dependent patterns
6. Honest assessment document with letter grade
7. Active pattern count matches documentation (no inflated claims)

---

## Hard Dependencies and Gates (Phase Sequencing)

Phase 2.1 is a hard prerequisite for Phase 3. The following gates must pass before any Phase 3 work begins. If any gate fails, Phase 2.1 remains open.

### Gate A: Property Integrity (Builder ↔ Patterns)

Requirements:
1. All properties declared in the builder dataclass are emitted in the property map.
2. `cross_function_reentrancy_surface` and `cross_function_reentrancy_read` are emitted and validated on a real contract.
3. Property coverage tests fail on any newly introduced orphan property reference.

Proof:
1. Passing `tests/test_pattern_property_coverage.py` output showing new baseline.
2. Evidence of non-trivial values for the two missing properties on a real contract graph run.

### Gate B: Orphan Warnings and Broken-Pattern Safety

Requirements:
1. Pattern engine logs a warning when loading patterns with orphan properties.
2. No active pattern has all properties orphaned.
3. Orphan baseline reduced below 223 and locked as the new baseline.

Proof:
1. Log output or unit test demonstrating warning behavior.
2. Validation output showing zero totally-broken patterns in active directories.

### Gate C: Documentation Honesty

Requirements:
1. Active, quarantined, and deleted pattern counts match validation output.
2. Any "working pattern" claim includes the definition and validation method.
3. No doc asserts pruning/triage without a matching inventory or move history.

Proof:
1. Doc updates include explicit counts and reference the validation output committed in the same phase.
