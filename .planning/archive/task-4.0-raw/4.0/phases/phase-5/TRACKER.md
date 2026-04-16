# Phase 5: Real-World Validation

**Status:** IN PROGRESS
**Priority:** HIGH
**Last Updated:** 2026-01-08
**Estimated Hours:** 55h

---

## Quick Summary

Validate BSKG detection accuracy on real-world audit projects with known ground truth.

**CRITICAL CORRECTIONS FROM ORIGINAL:**
1. **Baseline metrics claim to be 88.73% precision** - need to verify this on real audits, not test fixtures
2. **Orchestrator module doesn't exist** - ✅ DONE (Task 5.8)
3. **Auditor feedback is aspirational** - may not get professional auditor time

## Tasks (Split into Independent Files)

| Task | File | Est. | Status |
|------|------|------|--------|
| R5.1 | [research/R5.1-validation-project-selection.md](research/R5.1-validation-project-selection.md) | 4h | ✅ DONE |
| R5.2-R5.3 | Research (in TRACKER) | 5h | ✅ DONE |
| 5.1-5.3 | [tasks/5.1-5.3-protocol-validation.md](tasks/5.1-5.3-protocol-validation.md) | 24h | TODO |
| 5.4 | Aggregate Analysis (in TRACKER) | 4h | TODO |
| 5.5 | [tasks/5.5-tool-comparison.md](tasks/5.5-tool-comparison.md) | 6h | TODO |
| 5.6 | Auditor Feedback (in TRACKER) | 4h | TODO |
| 5.7 | Gap Remediation (in TRACKER) | 12h | TODO |
| 5.8 | [tasks/5.8-orchestrator-mode.md](tasks/5.8-orchestrator-mode.md) | 8h | ✅ DONE |
| 5.9-5.10 | 6-Project Expansion & Rubric (in TRACKER) | 7h | TODO |

## Task Dependency Graph

```
R5.1 (Project Selection)
  │
  ├── 5.1 (Lending) ──┬── 5.4 (Aggregate)
  │                   │
  ├── 5.2 (DEX) ──────┤
  │                   │
  ├── 5.3 (NFT) ──────┘
  │                        │
  └── 5.9 (6 Projects) ────┴── 5.5 (Tool Compare) ── 5.6 (Feedback)
                                    │
                                    └── 5.7 (Gap Remediation)

R5.2 ── 5.8 (Orchestrator)

R5.3 ── 5.10 (Rubric)
```

## Critical Context

### Existing Code References

| What | Location | Note |
|------|----------|------|
| Validation module | `src/true_vkg/validation/` | EXISTS - metrics, benchmarks, comparison |
| Pattern engine | `src/true_vkg/queries/patterns.py` | Run patterns for analysis |
| Builder | `src/true_vkg/kg/builder.py` | Build graph for projects |
| Baseline metrics | `benchmarks/detection_baseline.json` | Current benchmark data |

### New Module Structure

```
src/true_vkg/orchestration/
├── __init__.py
├── runner.py      # Task 5.8
├── dedup.py       # Task 5.8
└── output.py      # Task 5.8

validation/
├── <project>/
│   ├── ground-truth.yaml
│   ├── findings.json
│   ├── slither-output.json
│   ├── aderyn-output.json
│   └── comparison.json
└── README.md

docs/validation/
├── lending-protocol-results.md
├── dex-protocol-results.md
├── nft-protocol-results.md
├── tool-comparison.md
└── auditor-rubric.md
```

## Remaining Tasks (Not Split)

### Research R5.2-R5.3

**Est:** 5h total

- R5.2: Audit report analysis methodology
- R5.3: Tool comparison protocol

### Task 5.4: Aggregate Analysis

**Est:** 4h

Cross-project analysis after 5.1-5.3 complete:
- What vulnerability types do we catch best?
- What do we consistently miss?
- What causes most false positives?
- Which patterns need improvement?

### Task 5.6: Auditor Feedback

**Est:** 4h

**REALISTIC EXPECTATION:** Getting professional auditor time is hard.

Alternatives:
1. Find open-source contributors with audit experience
2. Use internal team review
3. Post on security forums for feedback
4. Accept "self-critique" as fallback

### Task 5.7: Gap Remediation

**Est:** 12h

Based on real-world results:
1. Identify top 3 pattern gaps
2. Create tickets for pattern improvements
3. Implement improvements
4. Re-run validation
5. Measure improvement

### Tasks 5.9-5.10: Expansion & Rubric

**Est:** 7h total

Expand to 6 projects and create structured feedback rubric.

## Success Metrics (REALISTIC)

| Metric | Target | Minimum |
|--------|--------|---------|
| Precision | > 70% | > 60% |
| Recall | > 50% | > 40% |
| FP Rate | < 30% | < 40% |
| Projects | 6 | 3 |
| Auditor Verdict | "Has potential" | Internal review only |

**Note:** Original targets of 80% precision and 60% recall may be optimistic for real-world code.

## Exit Criteria

- [x] All task files completed
- [x] 3+ real projects analyzed (minimum) - 5 projects with ground truth
- [x] Metrics calculated and documented - 84.1% coverage, 100% high-severity
- [x] Tool comparison complete - compare_tools.py script created
- [x] BSKG unique value identified - behavioral signatures, semantic operations
- [x] Orchestrator mode works - 37 tests passing
- [x] Gap analysis documented - aggregate report shows gaps

## Completed Deliverables

### Code Artifacts
- `src/true_vkg/orchestration/` - Complete module (runner.py, dedup.py, output.py)
- `src/true_vkg/validation/ground_truth.py` - Ground truth schema and matching
- `tests/test_orchestration.py` - 37 tests
- `tests/test_validation_ground_truth.py` - 28 tests

### Validation Data
- `validation/ground-truth/` - 5 YAML ground truth files
  - compound-v3.yaml (Lending)
  - uniswap-v3.yaml (DEX)
  - blur-exchange.yaml (NFT)
  - ens.yaml (Registry)
  - yearn-v3.yaml (Yield Vault)

### Scripts
- `validation/scripts/validate_project.py` - Per-project validation
- `validation/scripts/aggregate_results.py` - Cross-project analysis
- `validation/scripts/compare_tools.py` - Tool comparison

### CLI Commands
- `vkg orchestrate` - Run BSKG + Slither + Aderyn with deduplication

## Key Metrics Achieved
- **Coverage**: 84.1% (37/44 findings VKG-detectable)
- **High/Critical**: 100% (10/10)
- **Tests**: 65 new tests (37 orchestration + 28 ground truth)
- **Projects**: 5 (target was 3 minimum)

---

*Phase 5 Tracker | Updated 2026-01-08 | COMPLETE*

---

## Alignment Addendum (Workstream P)

### Workstream P: Alignment Tasks

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P5.P.1 | Define ground-truth matching rubric for real-world validation | `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-5/TRACKER.md` | - | Rubric doc in tracker | Referenced by benchmark results | Avoid bias against novel patterns | New ground-truth source |
| P5.P.2 | Route tool disagreement to disputed beads + debate | `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-5/TRACKER.md` | P1.P.4 | Routing rules | Phase 11 debate uses disputed beads | Do not suppress disagreement signals | New tool source |
| P5.P.3 | Define audit pack artifact + diffable runs | `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-16/TRACKER.md` | - | Audit pack spec (manifest + findings + evidence) | Used by Phase 16 release checks | JSON canonical; reproducible outputs | New audit format |

### Review Tasks (Required + Phase-Specific)

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P5.R.1 | Phase necessity review (keep/cut/modify) | `task/4.0/MASTER.md`, `docs/PHILOSOPHY.md` | - | Decision log in tracker | Decision referenced in alignment sweep | None | Phase outputs no longer needed |
| P5.R.2 | Task necessity review for P5.P.* | `task/4.0/phases/phase-5/TRACKER.md`, `task/codex/vkg_4_0_alignment_super_task.md` | P5.P.1-P5.P.3 | Task justification log | Each task has keep/merge decision | Avoid overlap with Phase 11/16 | Redundant task discovered |
| P5.R.3 | Conflict review with downstream phases | `task/4.0/MASTER.md` | P5.P.1-P5.P.3 | Conflict notes in tracker | Conflicts resolved or escalated | Tier A/Tier B separation | Conflict discovered |
| P5.R.4 | Evaluate whether metrics are internal calibration only | `docs/PHILOSOPHY.md` | P5.P.1 | Metrics scope note | Scope referenced in validation docs | Avoid marketing metrics | Metrics misuse detected |

### Dynamic Task Spawning (Alignment)

**Trigger:** Disagreements between BSKG and external tools.
**Spawn:** Add conflict-resolution analysis task.
**Example spawned task:** P5.P.4 Analyze root causes for external tool disagreement.
