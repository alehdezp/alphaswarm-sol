# Phase 3.1d: Detection-Evaluation Feedback Bridge

**Status:** COMPLETE (2026-02-20)
**Goal:** Connect detection quality to evaluation measurement. Create a reusable testing framework with use case scenarios that serve as regression tests and improvement targets.

## What This Phase Delivers

1. **Use case scenario framework** — 32+ YAML scenarios defining expected behavior for all Tier 1 workflows
2. **Calibrated evaluator** — Fix 3.1c stubs, run on real data, verify score discrimination
3. **Detection quality baseline** — Precision/recall/F1 against ground truth
4. **Testing skills** — Reusable skills so future phases can test without building test infrastructure
5. **First improvement iteration** — Prove the detect → evaluate → improve loop works

## Plans (8)

| Plan | Name | Effort | Wave | Dependencies |
|------|------|--------|------|-------------|
| 3.1d-01 | Scenario Framework + Pytest Plugin | M | 1 | None |
| 3.1d-02 | Fix Critical 3.1c Evaluation Stubs | S | 1 | None |
| 3.1d-03 | Capture First Real Transcripts | S | 2 | 02 |
| 3.1d-04 | Calibrate Evaluator on Real Output | M | 3 | 03 |
| 3.1d-05 | Detection Quality Baseline | M | 3 | 03 |
| 3.1d-06 | Author Remaining 22 Scenarios | M | 4 | 01, 04 |
| 3.1d-07 | Testing Skills + Subagent | M | 5 | 01, 04 |
| 3.1d-08 | First Improvement Iteration + Doc Update | M | 6 | 05, 06, 07 |

## Execution Waves

```
Wave 1: [01] Scenario Framework  +  [02] Fix Stubs     (independent)
Wave 2: [03] Real Transcripts                           (depends on 02)
Wave 3: [04] Calibrate Evaluator +  [05] Detection Baseline  (depend on 03)
Wave 4: [06] Remaining Scenarios                        (depends on 01, informed by 04)
Wave 5: [07] Testing Skills                             (depends on 01, 04)
Wave 6: [08] First Improvement + Doc Update             (depends on 05, 06, 07)
```

## Key Design Decisions

- Scenarios live in `.planning/testing/scenarios/use-cases/` (test specification, not docs)
- Pytest plugin auto-discovers YAML scenarios, no code changes needed to add scenarios
- BaselineManager tracks scores across sessions for regression detection
- Testing skills are self-contained — callable from any future GSD phase
- All evaluation stubs replaced with heuristic-based scoring (no hardcoded 50s)

## Exit Gate

- 32+ scenarios pass schema validation
- All 274+ existing tests still pass
- Evaluator score spread > 20 points between good and bad
- Detection baseline published
- Testing skills produce structured feedback
- `docs/workflows/` updated with honest capability status
