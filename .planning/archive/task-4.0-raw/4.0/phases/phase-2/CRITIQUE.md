# Phase 2 Brutal Critique & Improvements

**Date:** 2026-01-07
**Reviewer:** Brutal Technical Reviewer

---

## Summary

Phase 2 TRACKER.md was generally well-structured but had critical gaps in the TODO tasks that would cause implementation failure. The main issues were:

1. **Lack of self-containment**: TODO tasks referenced code locations but didn't provide enough context
2. **Missing step-by-step instructions**: Tasks had objectives but no implementation roadmap
3. **Unclear failure modes**: No guidance on what to do when things go wrong
4. **Missing prerequisite verification**: No way to verify readiness before starting

---

## Issues Found

### Issue 1: Task 2.7 (SmartBugs) Missing Critical Details

**Problem:**
- No instructions for downloading SmartBugs dataset
- No Solidity version handling (SmartBugs has 0.4.x contracts)
- No pattern mapping from SmartBugs categories to BSKG patterns
- No curated file selection criteria

**Impact:** Implementer would spend 2-4h researching before starting

**Fix:** Created `/task/4.0/phases/phase-2/tasks/2.7-smartbugs-dataset.md` with:
- Step-by-step download instructions
- Solidity version handling strategy
- Pattern mapping table
- Curation criteria
- Failure mode handling

---

### Issue 2: Task 2.8 (Safe Set) Too Vague

**Problem:**
- "Curate 50+ known-safe contracts" has no selection criteria
- No FP rate calculation implementation
- No guidance on what to do if FP rate exceeds threshold
- No contract source locations

**Impact:** Implementer might select wrong contracts, undermining entire FP measurement

**Fix:** Created `/task/4.0/phases/phase-2/tasks/2.8-safe-set-fp.md` with:
- Explicit selection criteria (deployed > 1 year, audited, no exploits)
- Tiered contract sources (OpenZeppelin, Uniswap, AAVE)
- FP rate calculation code
- Threshold remediation steps

---

### Issue 3: Task 2.10 (Completeness Report) Too Large

**Problem:**
- 8h task with no breakdown
- Touches multiple modules (builder, CLI, schema)
- No schema definition
- No test cases

**Impact:** Task would take 12-16h due to scope creep

**Fix:** Created `/task/4.0/phases/phase-2/tasks/2.10-completeness-report.md` with:
- 4 subtasks (2.10a-2.10d)
- Full JSON schema
- CompletenessReport class implementation
- CLI integration code
- Test cases

---

### Issue 4: Code Location References Insufficient

**Problem:**
- TRACKER references `src/true_vkg/benchmark/runner.py` but doesn't explain what to modify
- No context on how existing code works

**Fix:** Each task file now includes:
- Relevant code locations table with PURPOSE and WHY YOU NEED IT
- Code snippets showing integration points
- Prerequisites verification commands

---

### Issue 5: No Validation Criteria

**Problem:**
- Tasks have "Validation" column but entries are vague
- "69+ vulns integrated" doesn't tell you HOW to verify

**Fix:** Each task file now includes:
- Validation criteria table with specific commands
- Pass/Fail checkboxes
- Common failure modes and solutions

---

## Files Created

| File | Purpose | Size |
|------|---------|------|
| `tasks/2.7-smartbugs-dataset.md` | SmartBugs integration details | 6.5KB |
| `tasks/2.8-safe-set-fp.md` | Safe set FP measurement | 7.2KB |
| `tasks/2.10-completeness-report.md` | Completeness report with subtasks | 8.1KB |
| `CRITIQUE.md` | This document | - |

---

## Files Modified

| File | Change |
|------|--------|
| `TRACKER.md` | Added links to detailed task files |

---

## Remaining Concerns

### Task 2.5 (Metrics Dashboard)
- Still marked TODO with no detailed task
- Lower priority (SHOULD), so acceptable to defer
- Recommendation: Create detailed task when prioritized

### CI Integration (2.4)
- Marked complete but no `.github/workflows/benchmark.yml` visible in git status
- May need verification that CI is actually active

### Real-World Tier
- TIER_STRATEGY.md mentions Tier 4 (Real-World) but no tasks exist for it
- Acceptable: Phase 2 focuses on Tier 1-3, Real-World is Phase 5

---

## Recommendations

1. **Before starting any TODO task**: Read the detailed task file first
2. **Run prerequisites check**: Each task file has verification commands
3. **Track time**: Compare actual vs estimated to calibrate future phases
4. **Document failures**: Add to "Iteration Log" in TRACKER.md

---

*Critique completed: 2026-01-07*
