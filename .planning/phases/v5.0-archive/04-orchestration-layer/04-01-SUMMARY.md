---
phase: 04-orchestration-layer
plan: 01
subsystem: orchestration
tags: [schemas, pool, verdict, storage]
dependency-graph:
  requires: []
  provides: [Pool, PoolStatus, Verdict, VerdictConfidence, Scope, EvidencePacket, PoolManager, PoolStorage]
  affects: [04-02, 04-03, 04-04, 04-05, 04-06, 04-07]
tech-stack:
  added: []
  patterns: [dataclass-serialization, yaml-storage, enum-lifecycle]
key-files:
  created:
    - src/true_vkg/orchestration/schemas.py
    - src/true_vkg/orchestration/pool.py
    - tests/test_orchestration_schemas.py
  modified:
    - src/true_vkg/orchestration/__init__.py
decisions:
  - Pool lifecycle with 7 active phases plus FAILED/PAUSED states
  - VerdictConfidence requires human review for all levels per PHILOSOPHY.md
  - YAML serialization for human readability
  - CONFIRMED verdict requires evidence (validation in __post_init__)
  - Pause/resume tracks previous status for correct phase resumption
metrics:
  duration: ~45 minutes
  completed: 2026-01-20
---

# Phase 4 Plan 01: Canonical Artifact Schemas Summary

**One-liner:** Pool, Verdict, Scope, EvidencePacket dataclasses with YAML serialization and lifecycle management for orchestration layer.

## What Was Done

### Task 1: Define canonical artifact schemas
Created `src/true_vkg/orchestration/schemas.py` (999 LOC) with:
- **PoolStatus**: Enum with 9 states (intake, context, beads, execute, verify, integrate, complete, failed, paused)
- **VerdictConfidence**: Enum with 4 levels (confirmed, likely, uncertain, rejected)
- **Scope**: Audit scope definition (files, contracts, focus_areas, exclude_patterns)
- **EvidenceItem**: Single piece of evidence with type, value, location, confidence, source
- **EvidencePacket**: Collection of evidence items with aggregation helpers
- **DebateClaim**: Structured claim from attacker/defender with evidence anchoring
- **DebateRecord**: Full debate transcript (claim round, rebuttals, verifier synthesis)
- **Verdict**: Final determination with confidence, evidence, debate record, and human_flag
- **Pool**: Batch container for audit waves (renamed from "convoy" per 04-CONTEXT.md)

All schemas support:
- `to_dict()` / `from_dict()` for JSON serialization
- `to_yaml()` / `from_yaml()` for human-readable persistence
- Validation in `__post_init__` (confidence ranges, required evidence)

### Task 2: Implement Pool storage and management
Created `src/true_vkg/orchestration/pool.py` (507 LOC) with:
- **PoolStorage**: File-based YAML storage at `.vrs/pools/`
  - `save_pool()`, `get_pool()`, `list_pools()`
  - `list_pools_by_status()`, `list_active_pools()`
  - `delete_pool()`, `clear()`, `count()`, `exists()`
  - `get_summary()` for aggregate statistics
- **PoolManager**: High-level operations
  - `create_pool()` from Scope with auto-ID generation
  - `add_bead()`, `add_beads()`, `remove_bead()`
  - `record_verdict()` for finding verdicts
  - `advance_phase()`, `set_status()` for lifecycle
  - `fail_pool()`, `pause_pool()`, `resume_pool()`
  - `get_pending_beads()`, `get_pools_by_status()`
  - `update_pool()` with custom update function

### Task 3: Add schema validation tests
Created `tests/test_orchestration_schemas.py` (1270 LOC) with 79 tests:
- **TestPoolStatus** (5 tests): Enum values, transitions, terminal/active checks
- **TestVerdictConfidence** (4 tests): Enum values, positive checks, human review
- **TestScope** (6 tests): Creation, dict roundtrip, YAML roundtrip, file matching
- **TestEvidenceItem** (3 tests): Creation, confidence validation, roundtrip
- **TestEvidencePacket** (8 tests): Creation, add_item, get_by_type/source, aggregations
- **TestDebateClaim** (2 tests): Creation, roundtrip
- **TestDebateRecord** (5 tests): Creation, add_rebuttal, complete, YAML roundtrip
- **TestVerdict** (7 tests): Creation, human_flag enforcement, evidence requirement, summary
- **TestPool** (12 tests): Creation, beads, verdicts, lifecycle, pause/resume, counts
- **TestPoolStorage** (9 tests): Save/load, list, filter, delete, summary
- **TestPoolManager** (15 tests): Create, beads, verdicts, phases, pause/resume
- **TestYAMLSerialization** (4 tests): Human-readable format, complex roundtrip

## Verification Results

All truths from plan verified:
1. Pool can be created with unique ID and bead list
2. Pool tracks status through phases (intake -> context -> beads -> execute -> verify -> integrate -> complete)
3. Verdict schema captures attacker/defender claims with evidence via DebateRecord
4. Schemas serialize to YAML for human readability

All artifacts created:
- `src/true_vkg/orchestration/schemas.py` with all required exports
- `src/true_vkg/orchestration/pool.py` with PoolManager, PoolStorage
- `tests/test_orchestration_schemas.py` with 1270 LOC (exceeds 100 minimum)

Key link verified:
- pool.py imports Pool, PoolStatus from schemas.py

## Commits

| Hash | Type | Description |
|------|------|-------------|
| a97cdd1 | feat | Canonical artifact schemas for orchestration layer |
| fecb4d0 | feat | Pool storage and management implementation |
| 3f0f6f2 | test | Comprehensive schema validation tests (79 tests) |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Ready for 04-02 (Bead-Pool Integration):**
- Pool schemas provide the foundation for bead batching
- PoolManager supports adding beads and recording verdicts
- Storage layer ready for pool persistence

**Dependencies Satisfied:**
- Pool can track bead_ids list
- Verdict can store EvidencePacket with debate transcript
- All orchestration schemas importable from `true_vkg.orchestration`

## Statistics

| Metric | Value |
|--------|-------|
| Files created | 3 |
| Lines of code | 2,776 |
| Tests | 79 |
| Test pass rate | 100% |
| Schemas defined | 9 (enums + dataclasses) |

---
*Completed: 2026-01-20*
