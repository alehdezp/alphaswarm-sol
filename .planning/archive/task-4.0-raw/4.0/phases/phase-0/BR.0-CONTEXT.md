# Builder Refactor: Context & Overview

**Status:** TODO
**Priority:** MUST (Production Readiness Blocker)
**Estimated Total Hours:** 80-120h (6120 lines to refactor)
**Constraint:** builder.py is protected - all changes must be behavior-preserving

---

## What This Workstream Achieves

Transform `src/true_vkg/kg/builder.py` (6120 lines) into a modular, maintainable architecture:

```
BEFORE (monolithic):
builder.py (6120 lines)
├── VKGBuilder class
├── _add_contract (253 lines)
├── _add_functions (1382 lines)  <-- THE MONSTER
├── 50+ helper methods
└── Inline token lists everywhere

AFTER (modular):
builder_v2.py (orchestrator)
├── contexts.py (dataclasses)
├── constants.py (token lists)
├── protocols.py (type hints)
├── pipeline.py (execution order)
└── detectors/
    ├── access_control.py
    ├── reentrancy.py
    ├── oracle.py
    ├── token.py
    ├── math.py
    ├── proxy.py
    ├── mev.py
    ├── callback.py
    ├── loop.py
    ├── crypto.py
    └── external_call.py
```

---

## File Locations You Need

| File | Path | Lines | Purpose |
|------|------|-------|---------|
| builder.py | `src/true_vkg/kg/builder.py` | 6120 | Main target |
| schema.py | `src/true_vkg/kg/schema.py` | ~400 | Node/Edge types |
| operations.py | `src/true_vkg/kg/operations.py` | ~600 | Semantic operations |
| heuristics.py | `src/true_vkg/kg/heuristics.py` | ~200 | Classification helpers |
| constants (new) | `src/true_vkg/kg/constants.py` | TBD | Token lists, patterns |
| contexts (new) | `src/true_vkg/kg/contexts.py` | TBD | Dataclasses |
| protocols (new) | `src/true_vkg/kg/protocols.py` | TBD | Type protocols |
| pipeline (new) | `src/true_vkg/kg/pipeline.py` | TBD | Execution order |
| detectors/ (new) | `src/true_vkg/kg/detectors/` | TBD | Signal modules |

---

## Method Size Map (builder.py)

| Method | Lines | Start | End | Complexity |
|--------|-------|-------|-----|------------|
| `_add_functions` | 1382 | 511 | 1892 | EXTREME |
| `_add_contract` | 253 | 147 | 400 | HIGH |
| `_annotate_cross_function_signals` | 93 | 1892 | 1985 | MEDIUM |
| `_classify_state_write_targets` | 10 | 2002 | 2012 | LOW |
| Other helpers | ~2400 | 1985 | 6120 | MIXED |

---

## Validation Strategy

### Golden Baseline (CRITICAL)

Before ANY change, generate golden baseline:

```bash
# Generate baseline graph
uv run alphaswarm build-kg tests/contracts/BasicVault.sol --out /tmp/golden-baseline

# Save fingerprint
uv run python -c "
from true_vkg.kg.fingerprint import compute_fingerprint
import json
graph = json.load(open('/tmp/golden-baseline/graph.json'))
print(compute_fingerprint(graph))
" > /tmp/golden-fingerprint.txt

# Run ALL existing tests
uv run pytest tests/ -v --tb=short > /tmp/baseline-tests.txt 2>&1
echo "Tests passed: $(grep -c 'PASSED' /tmp/baseline-tests.txt)"
echo "Tests failed: $(grep -c 'FAILED' /tmp/baseline-tests.txt)"
```

### After EVERY Change

```bash
# Rebuild same contract
uv run alphaswarm build-kg tests/contracts/BasicVault.sol --out /tmp/after-change

# Compare fingerprint (MUST be identical)
NEW_FP=$(uv run python -c "
from true_vkg.kg.fingerprint import compute_fingerprint
import json
graph = json.load(open('/tmp/after-change/graph.json'))
print(compute_fingerprint(graph))
")
OLD_FP=$(cat /tmp/golden-fingerprint.txt)
if [ "$NEW_FP" != "$OLD_FP" ]; then
    echo "FINGERPRINT CHANGED - ROLLBACK REQUIRED"
    exit 1
fi

# Run all tests
uv run pytest tests/ -v --tb=short
```

---

## Task Dependencies

```
BR.0 (this doc) - Context only, no code changes
    │
    ├── BR.1 (Extract Contexts) - No dependencies
    │
    ├── BR.2 (Centralize Tokens) - No dependencies
    │
    ├── BR.6 (Protocol Types) - No dependencies
    │
    └── BR.3 (Split Detectors) - Depends on BR.1, BR.2, BR.6
            │
            ├── BR.4 (Table-Driven Pipeline) - Depends on BR.3
            │
            └── BR.5 (Performance) - Depends on BR.3, BR.4
```

**Parallelizable:** BR.1, BR.2, BR.6 can run in parallel
**Sequential:** BR.3 must wait, then BR.4, then BR.5

---

## Risk Mitigation

### If Fingerprint Changes

1. **STOP immediately** - Do not continue refactoring
2. Check `git diff src/true_vkg/kg/builder.py`
3. Identify which change caused drift
4. Rollback: `git checkout HEAD -- src/true_vkg/kg/builder.py`
5. Document the failure in task file

### If Tests Fail

1. Check if failure is pre-existing or new
2. If new: rollback and investigate
3. If pre-existing: continue but document

### If Performance Regresses

1. Acceptable regression: < 5%
2. Warning regression: 5-10%
3. Blocking regression: > 10%

---

## Test Files That MUST Pass

These tests are the safety net:

| Test File | Purpose | Command |
|-----------|---------|---------|
| `tests/test_fingerprint.py` | Graph determinism | `pytest tests/test_fingerprint.py -v` |
| `tests/test_rename_resistance.py` | Name independence | `pytest tests/test_rename_resistance.py -v` |
| `tests/test_golden_snapshots.py` | Baseline comparison | `pytest tests/test_golden_snapshots.py -v` |
| `tests/test_builder.py` | Builder unit tests | `pytest tests/test_builder.py -v` |
| All lens tests | Pattern detection | `pytest tests/test_*_lens.py -v` |

**Run all at once:**
```bash
uv run pytest tests/test_fingerprint.py tests/test_rename_resistance.py tests/test_golden_snapshots.py tests/test_builder.py tests/test_*_lens.py -v --tb=short
```

---

## Success Criteria (Phase 0 Complete)

- [ ] All BR.1-BR.6 tasks complete
- [ ] Graph fingerprint identical to pre-refactor baseline
- [ ] All 1315+ base tests pass (0 regressions)
- [ ] Each detector module has dedicated tests
- [ ] No `Any` types for Slither objects
- [ ] 20% minimum speedup measured
- [ ] CI pipeline validates determinism

---

## References

- `task/4.0/protocols/BUILDER-PROTOCOL.md` - Change safety procedures
- `task/4.0/protocols/PROPERTY-SCHEMA-CONTRACT.md` - Property semantics
- `task/4.0/phases/phase-1/TRACKER.md` - Already complete foundation work
- `tests/test_fingerprint.py` - Fingerprinting tests (exist)
- `tests/test_rename_resistance.py` - Rename tests (exist)

---

*Context Document | Version 1.0 | 2026-01-07*
