# Phase 0: BUILDER-REFACTOR.md - Brutal Critique

**Reviewer:** Automated Technical Review
**Date:** 2026-01-07
**Verdict:** MAJOR REWRITE REQUIRED

---

## Critical Issues Found

### 1. WRONG LINE COUNT - SEVERELY UNDERESTIMATED

**Claim:** "Transform builder.py from a monolithic 2000+ line file"

**Reality:** builder.py is **6120 lines** - 3x larger than stated. This is not a minor oversight - it fundamentally changes the scope and effort estimation.

**Impact:**
- All hour estimates are wrong
- Task decomposition is incomplete
- Risk assessment is underestimated

---

### 2. `_add_functions` METHOD SIZE HIDDEN

**Claim:** "`_add_functions` is very large"

**Reality:** `_add_functions` alone is **1382 lines** (lines 511-1892). This is a method that should be 10-15 separate modules. The document doesn't specify this, making the BR.3 task (8h estimate) absurdly optimistic.

**Impact:**
- BR.3 "Split Detectors into Modules" should be 40h+, not 8h
- There should be at least 10-12 detector modules, not 7

---

### 3. TASKS NOT SELF-CONTAINED

Each task (BR.1-BR.6) says "Graph fingerprint identical" but:
- Doesn't specify WHERE to find the golden fingerprint
- Doesn't specify HOW to generate comparison
- Doesn't specify WHICH test files to run
- Doesn't provide example commands

**An LLM picking up BR.2 cannot complete it** because:
- Where is the baseline fingerprint?
- How do I compare?
- What test command proves success?

---

### 4. MISSING PREREQUISITE CONTEXT

Tasks reference:
- "DVDeFi corpus" - Not explained how to access
- "Golden Graph Snapshot Tests" - Don't exist in file system
- "Determinism Tests" - Not linked to actual test files
- "Performance Regression Tracking" - No CI config provided

---

### 5. CONTINGENCY PATH IS FICTION

**Claim:** "Create builder_v2.py as parallel implementation"

**Reality:** This is effectively rewriting 6120 lines. The "feature flag" approach requires both implementations to be maintained. This is not a contingency - it's a multi-month project.

---

### 6. HOUR ESTIMATES ARE FANTASY

| Task | Estimated | Realistic (based on 6120 lines) |
|------|-----------|--------------------------------|
| BR.1 Extract Context Dataclasses | 4h | 8-12h |
| BR.2 Centralize Token Lists | 3h | 6-8h |
| BR.3 Split Detectors | 8h | 40-60h |
| BR.4 Table-Driven Pipeline | 4h | 8-12h |
| BR.5 Performance Optimizations | 4h | 12-16h |
| BR.6 Protocol Types | 3h | 6-10h |
| **Total** | **26h** | **80-118h** |

---

### 7. SAFETY TESTS DON'T EXIST

The document says "MUST pass after each task" but:
- `tests/test_golden_snapshots.py` exists - good
- `tests/test_rename_resistance.py` exists - good
- BUT these were created in Phase 1, not Phase 0
- No CI pipeline for determinism validation exists

---

### 8. NO DEPENDENCY ON PHASE 1

Phase 0 is supposed to be a prerequisite workstream, but Phase 1 was completed first. The document doesn't acknowledge this ordering, creating confusion about what exists.

---

## Recommendations

### SPLIT INTO MULTIPLE FILES

This document should be 7 files:
1. `BR.0-CONTEXT.md` - Overview, architecture, validation approach
2. `BR.1-EXTRACT-CONTEXTS.md` - Self-contained task
3. `BR.2-CENTRALIZE-TOKENS.md` - Self-contained task
4. `BR.3-SPLIT-DETECTORS.md` - Self-contained task (with sub-tasks)
5. `BR.4-TABLE-DRIVEN-PIPELINE.md` - Self-contained task
6. `BR.5-PERFORMANCE.md` - Self-contained task
7. `BR.6-PROTOCOL-TYPES.md` - Self-contained task

### EACH TASK FILE MUST INCLUDE

1. **Exact file locations** - Not just "builder.py" but line ranges
2. **Prerequisite tasks** - What must be complete first
3. **Test commands** - Exact commands to verify success
4. **Golden baseline** - Where to find reference output
5. **Rollback procedure** - How to undo if broken
6. **Time estimate** - Realistic, not optimistic

---

## Files to Create

1. Split BUILDER-REFACTOR.md into 7 individual task files
2. Create test baseline scripts
3. Add CI workflow for determinism
4. Create performance benchmark script

---

*Critique complete. See improved files in same directory.*
