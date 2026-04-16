# Builder.py Refactor Workstream

**Status:** TODO
**Priority:** MUST (Production Readiness Blocker)
**Estimated Total Hours:** 80-120h (revised from original 26h)
**Constraint:** builder.py is protected - all changes must be behavior-preserving

---

## CRITICAL: Original Document Was Revised

The original version of this document had significant issues:

1. **Wrong line count**: Stated "2000+ lines" but builder.py is **6120 lines**
2. **Underestimated complexity**: `_add_functions` alone is **1382 lines**
3. **Unrealistic hour estimates**: Original 26h total, revised to 80-120h
4. **Tasks not self-contained**: Lacked specific file locations and commands

See `CRITIQUE.md` for full analysis of issues.

---

## Task Structure (REVISED)

This workstream has been split into individual task files:

| Task | File | Est. Hours | Dependencies |
|------|------|------------|--------------|
| Overview | `BR.0-CONTEXT.md` | - | None (read first) |
| Extract Contexts | `BR.1-EXTRACT-CONTEXTS.md` | 8-12h | None |
| Centralize Tokens | `BR.2-CENTRALIZE-TOKENS.md` | 6-8h | None |
| Protocol Types | `BR.6-PROTOCOL-TYPES.md` | 6-10h | None |
| Split Detectors | `BR.3-SPLIT-DETECTORS.md` | 40-60h | BR.1, BR.2, BR.6 |
| Table-Driven Pipeline | `BR.4-TABLE-DRIVEN-PIPELINE.md` | 8-12h | BR.3 |
| Performance | `BR.5-PERFORMANCE.md` | 12-16h | BR.3, BR.4 |

**Total: 80-118h** (realistic estimate)

---

## Execution Order

```
WEEK 1 (Parallel):
├── BR.1 Extract Contexts (8-12h)
├── BR.2 Centralize Tokens (6-8h)
└── BR.6 Protocol Types (6-10h)

WEEK 2-4 (Sequential):
└── BR.3 Split Detectors (40-60h)
    ├── BR.3.1 Base interface
    ├── BR.3.2 access_control.py
    ├── BR.3.3 reentrancy.py
    ├── BR.3.4 oracle.py
    ├── BR.3.5 token.py
    ├── BR.3.6 loop.py
    └── BR.3.7 remaining detectors

WEEK 5:
├── BR.4 Table-Driven Pipeline (8-12h)
└── BR.5 Performance (12-16h)
```

---

## Quick Reference: Key Files

| File | Path | Lines |
|------|------|-------|
| Main target | `src/true_vkg/kg/builder.py` | 6120 |
| The monster method | `builder.py:_add_functions` | 1382 (lines 511-1892) |
| Schema types | `src/true_vkg/kg/schema.py` | ~400 |
| Operations | `src/true_vkg/kg/operations.py` | ~600 |
| Fingerprinting | `src/true_vkg/kg/fingerprint.py` | ~200 |

---

## Validation (All Tasks)

Every task must pass these checks:

```bash
# 1. Graph fingerprint identical
uv run alphaswarm build-kg tests/contracts/BasicVault.sol --out /tmp/after
diff <(jq -S . /tmp/golden-baseline/graph.json) <(jq -S . /tmp/after/graph.json)

# 2. All tests pass
uv run pytest tests/ -v --tb=short

# 3. Key safety tests
uv run pytest tests/test_fingerprint.py tests/test_rename_resistance.py -v
```

---

## Success Criteria (Phase 0 Complete)

- [ ] All 6 tasks (BR.1-BR.6) complete
- [ ] Graph fingerprint identical to pre-refactor baseline
- [ ] All 1315+ base tests pass (0 regressions)
- [ ] Each detector module has dedicated tests
- [ ] No `Any` types for Slither objects
- [ ] 20% minimum speedup measured
- [ ] CI validates determinism

---

## Files in This Directory

```
phase-0/
├── BUILDER-REFACTOR.md      # This file (overview)
├── CRITIQUE.md              # Issues with original document
├── BR.0-CONTEXT.md          # Context and overview
├── BR.1-EXTRACT-CONTEXTS.md # Task: Extract dataclasses
├── BR.2-CENTRALIZE-TOKENS.md# Task: Centralize token lists
├── BR.3-SPLIT-DETECTORS.md  # Task: Split into modules (LARGEST)
├── BR.4-TABLE-DRIVEN-PIPELINE.md # Task: Execution pipeline
├── BR.5-PERFORMANCE.md      # Task: Performance optimization
└── BR.6-PROTOCOL-TYPES.md   # Task: Type protocols
```

---

## Contingency Path

If builder.py changes prove too risky:

1. Create `builder_v2.py` as parallel implementation
2. Feature flag: `VKG_BUILDER_V2=1`
3. Run both builders, compare output fingerprints
4. Once validated across all tests, deprecate original

**Note:** This is NOT a quick fix. builder_v2.py would require rewriting 6120 lines. Only use if incremental refactoring fails.

---

*Builder Refactor Master Document | Version 2.0 | 2026-01-07*
*Revised after brutal critique of v1.0*
