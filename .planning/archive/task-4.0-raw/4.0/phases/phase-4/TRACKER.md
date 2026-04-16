# Phase 4: Test Scaffolding

**Status:** ✅ COMPLETE (11/11 tasks)
**Priority:** HIGH
**Last Updated:** 2026-01-08
**Estimated Hours:** 47h
**Actual Tests:** 258 tests passing

---

## Quick Summary

Generate test scaffolds that help verify vulnerabilities with tiered confidence levels.

**CRITICAL CORRECTIONS FROM ORIGINAL:**
1. **Target 30-40% compile rate**, not 60% (see reflection section in original)
2. **Module named `testing/`**, not `scaffolding/` (avoid confusion with existing `kg/scaffold.py`)
3. **Three Finding classes exist** - extend `enterprise/reports.py`

## Tasks (Split into Independent Files)

| Task | File | Est. | Status |
|------|------|------|--------|
| R4.1 | [research/R4.1-project-structure-detection.md](research/R4.1-project-structure-detection.md) | 4h | ✅ DONE |
| 4.1 | [tasks/4.1-tier-system-design.md](tasks/4.1-tier-system-design.md) | 3h | ✅ DONE (28 tests) |
| 4.2 | [tasks/4.2-project-detection.md](tasks/4.2-project-detection.md) | 4h | ✅ DONE (32 tests) |
| 4.3 | [tasks/4.3-remapping-resolution.md](tasks/4.3-remapping-resolution.md) | 6h | ✅ DONE (39 tests) |
| 4.4 | Pragma Compatibility (in TRACKER) | 3h | ✅ DONE (47 tests) |
| 4.5 | [tasks/4.5-tier1-generator.md](tasks/4.5-tier1-generator.md) | 4h | ✅ DONE (36 tests) |
| 4.6 | [tasks/4.6-tier2-generator.md](tasks/4.6-tier2-generator.md) | 8h | ✅ DONE (combined with 4.5) |
| 4.7-4.8 | Quality Tracking & Fallback (in TRACKER) | 7h | ✅ DONE (28 tests) |
| 4.9 | [tasks/4.9-finding-schema-extension.md](tasks/4.9-finding-schema-extension.md) | 2h | ✅ DONE (25 tests) |
| 4.10-4.11 | Test Summary & Loop Closure (in TRACKER) | 8h | ✅ DONE (23 tests) |

## Task Dependency Graph

```
R4.1 (Research)
  │
  ├── 4.1 (Tier Design) ──── 4.5 (Tier 1 Gen)
  │                               │
  ├── 4.2 (Detection) ──── 4.3 (Remapping) ──── 4.4 (Pragma)
  │                               │
  │                               └── 4.6 (Tier 2 Gen) ──── 4.7 (Quality)
  │                                                              │
  │                                                              └── 4.8 (Fallback)
  │
  └── 4.9 (Finding Schema) ──── 4.10 (Summary) ──── 4.11 (Loop)
```

## Critical Context

### Existing Code References

| What | Location | Note |
|------|----------|------|
| Semantic Scaffold (DIFFERENT!) | `src/true_vkg/kg/scaffold.py` | For LLM context, NOT tests |
| Finding class (CANONICAL) | `src/true_vkg/enterprise/reports.py` | Extend this one |
| Finding class (swarm) | `src/true_vkg/swarm/shared_memory.py` | Don't touch |
| Finding class (collab) | `src/true_vkg/collab/findings.py` | Don't touch |
| CLI | `src/true_vkg/cli.py` | Add `scaffold` command |
| Builder | `src/true_vkg/kg/builder.py` | Read-only reference |

### New Module Structure

```
src/true_vkg/testing/
├── __init__.py
├── tiers.py          # Task 4.1
├── detection.py      # Task 4.2
├── remappings.py     # Task 4.3
├── pragma.py         # Task 4.4
├── generator.py      # Tasks 4.5, 4.6
├── quality.py        # Task 4.7
└── verification.py   # Tasks 4.10, 4.11
```

## Remaining Tasks (Not Split)

### Task 4.4: Pragma Compatibility Check

**Est:** 3h

```python
# src/true_vkg/testing/pragma.py

def check_pragma_compatibility(
    test_pragma: str,
    contract_pragma: str
) -> CompatibilityResult:
    """Check if test pragma is compatible with contract."""
    # Parse version constraints
    # Return compatible/incompatible/unknown
```

### Tasks 4.7-4.8: Quality Tracking & Fallback

**Est:** 7h total

See original TRACKER sections 3.4.7 and 3.4.8 for details.

### Tasks 4.10-4.11: Test Summary & Loop Closure

**Est:** 8h total

See original TRACKER sections 3.4.10 and 3.4.11 for details.

## Success Metrics (REALISTIC)

| Metric | Target | Minimum |
|--------|--------|---------|
| Tier 1 Generation | 100% | 100% |
| Tier 2 Compile Rate | **30-40%** | 25% |
| Verification Loop | 5 findings | 3 findings |

## Exit Criteria

- [x] All task files completed ✅
- [x] `src/true_vkg/testing/` module exists ✅
- [x] Tier 1 always generates ✅ (100% confidence, MUST NEVER FAIL)
- [x] Tier 2 achieves 30%+ compile rate target ✅ (25% minimum threshold)
- [x] Finding schema extended ✅ (Verdict, TestResult, evidence fields)
- [x] CLI commands added ✅ (`scaffold generate/batch/info`)
- [x] All tests pass ✅ (258 tests)

## Module Structure (Final)

```
src/true_vkg/testing/
├── __init__.py       # 36 exports
├── tiers.py          # Task 4.1: TestTier enum, TierDefinition
├── detection.py      # Task 4.2: ProjectType, detect_project_structure
├── remappings.py     # Task 4.3: ImportResolver, extract functions
├── pragma.py         # Task 4.4: SemVer, VersionRange, compatibility
├── generator.py      # Tasks 4.5-4.6: TestScaffold, Tier 1/2 generators
├── quality.py        # Tasks 4.7-4.8: QualityTracker, fallback
└── verification.py   # Tasks 4.10-4.11: VerificationLoop, summaries
```

## CLI Commands (Added)

```bash
# Generate scaffold for a single finding
uv run alphaswarm scaffold generate VKG-001 --tier 2

# Generate scaffolds for all findings in a graph
uv run alphaswarm scaffold batch --graph .true_vkg/graphs/graph.json

# Show tier information
uv run alphaswarm scaffold info
```

## Test Summary

| Test File | Count | Description |
|-----------|-------|-------------|
| test_testing_tiers.py | 28 | Tier definitions, validation |
| test_testing_detection.py | 32 | Project detection (Foundry/Hardhat/Brownie) |
| test_testing_remappings.py | 39 | Import resolution, common patterns |
| test_testing_pragma.py | 47 | SemVer parsing, compatibility |
| test_testing_generator.py | 36 | Tier 1/2 scaffold generation |
| test_testing_quality.py | 28 | Quality tracking, fallback |
| test_testing_verification.py | 23 | Verification loop, summaries |
| test_finding_schema.py | 25 | Finding verdict/test fields |
| **Total** | **258** | |

---

*Phase 4 Tracker | Updated 2026-01-08 | COMPLETE*

---

## Alignment Addendum (Workstream P)

### Workstream P: Alignment Tasks

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P4.P.1 | Map scaffold test outcomes to bead verdict + bucket | `docs/PHILOSOPHY.md`, `src/true_vkg/testing/` | P6.P.1 | Mapping spec in tracker | Failure modes documented | Keep Tier A/Tier B separate | New scaffold result type |
| P4.P.2 | Add evidence packet test fields + tool metadata | `docs/PHILOSOPHY.md`, `src/true_vkg/testing/` | P3.P.1 | Schema update notes | Referenced in Phase 3 schema | Evidence packet schema versioned | New test tool |
| P4.P.3 | Define compile failure taxonomy + bucket overrides | `docs/PHILOSOPHY.md`, `src/true_vkg/testing/pragma.py` | - | Taxonomy list | Used by Phase 10 degraded mode | Degradation only for Tier A buckets | New failure mode |

### Review Tasks (Required + Phase-Specific)

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P4.R.1 | Phase necessity review (keep/cut/modify) | `task/4.0/MASTER.md`, `docs/PHILOSOPHY.md` | - | Decision log in tracker | Decision referenced in alignment sweep | None | Phase outputs no longer needed |
| P4.R.2 | Task necessity review for P4.P.* | `task/4.0/phases/phase-4/TRACKER.md`, `task/codex/vkg_4_0_alignment_super_task.md` | P4.P.1-P4.P.3 | Task justification log | Each task has keep/merge decision | Avoid overlap with Phase 6 | Redundant task discovered |
| P4.R.3 | Conflict review with downstream phases | `task/4.0/MASTER.md` | P4.P.1-P4.P.3 | Conflict notes in tracker | Conflicts resolved or escalated | Tier A/Tier B separation | Conflict discovered |
| P4.R.4 | Verify mapping does not conflict with Phase 6 bead lifecycle | `task/4.0/phases/phase-6/TRACKER.md` | P4.P.1 | Compatibility note | Bead lifecycle unchanged | Bead schema mismatch | Conflict detected |

### Dynamic Task Spawning (Alignment)

**Trigger:** New testing tool added.
**Spawn:** Add tool-specific scaffold mapping task.
**Example spawned task:** P4.P.4 Add evidence packet field mapping for a new scaffold tool.
