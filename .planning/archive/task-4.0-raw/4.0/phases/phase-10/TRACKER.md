# Phase 10: Graceful Degradation & Robustness

**Status:** COMPLETE (core) - optional tasks pending
**Priority:** MEDIUM - Production reliability
**Last Updated:** 2026-01-08
**Author:** BSKG Team

---

## Quick Reference

| Field | Value |
|-------|-------|
| Entry Gate | Phase 9 complete (PPR works) |
| Exit Gate | Core works with zero external tools, stress test passes 5/5 scenarios |
| Philosophy Pillars | Knowledge Graph, Agentic Automation, Self-Improvement |
| Estimated Hours | 37h |
| Task Count | 8 implementation + 2 research tasks |
| Test Count Target | 50+ tests |

---

## Task Files

All tasks have been split into independent, self-contained files in `tasks/`:

### Research Tasks

| ID | Task File | Est. | Priority | Status |
|----|-----------|------|----------|--------|
| R10.1 | [R10.1-failure-mode-analysis.md](tasks/R10.1-failure-mode-analysis.md) | 2h | MUST | DONE |
| R10.2 | [R10.2-recovery-patterns.md](tasks/R10.2-recovery-patterns.md) | 2h | MUST | DONE |

### Implementation Tasks

| ID | Task File | Est. | Priority | Depends On | Status | Tests |
|----|-----------|------|----------|------------|--------|-------|
| 10.1 | [10.1-dependency-hierarchy.md](tasks/10.1-dependency-hierarchy.md) | 3h | MUST | R10.1 | DONE | 56 |
| 10.2 | [10.2-tool-status-command.md](tasks/10.2-tool-status-command.md) | 4h | MUST | 10.1 | DONE | 31 |
| 10.3 | [10.3-isolated-tool-execution.md](tasks/10.3-isolated-tool-execution.md) | 6h | MUST | 10.2 | DONE | 57 |
| 10.4 | [10.4-state-versioning.md](tasks/10.4-state-versioning.md) | 6h | MUST | - | DONE | 50 |
| 10.5 | [10.5-error-recovery-commands.md](tasks/10.5-error-recovery-commands.md) | 4h | MUST | 10.4 | DONE | 40 |
| 10.6 | [10.6-partial-results-handling.md](tasks/10.6-partial-results-handling.md) | 4h | MUST | 10.3 | DONE | 44 |
| 10.7 | [10.7-offline-mode.md](tasks/10.7-offline-mode.md) | 4h | SHOULD | 10.1 | TODO | - |
| 10.8 | [10.8-stress-test.md](tasks/10.8-stress-test.md) | 6h | MUST | All | DONE | 17 |

### Dependency Graph

```
R10.1 (Failure Analysis)
   |
   +---> R10.2 (Recovery Patterns)
   |        |
   +---> 10.1 (Dependency Hierarchy)
            |
            +---> 10.2 (Tool Status)
            |        |
            |        +---> 10.3 (Isolated Execution)
            |                  |
            |                  +---> 10.6 (Partial Results)
            |
            +---> 10.7 (Offline Mode)

10.4 (State Versioning) [can run in parallel]
   |
   +---> 10.5 (Error Recovery)

                    All tasks
                        |
                        v
                10.8 (Stress Test)
```

---

## Key Outcomes

### Tier System

| Tier | Components | Failure Impact |
|------|------------|----------------|
| TIER 0 (Core) | Python, Slither, Pattern Engine | BSKG cannot run |
| TIER 1 (Enhancement) | Aderyn, Medusa, LLM | Reduced capability |
| TIER 2 (Optional) | MCP, Monitoring | No impact |

### New CLI Commands

```bash
# Check system state
vkg tools status
vkg doctor

# Repair issues
vkg repair
vkg validate

# Reset (last resort)
vkg reset --confirm
```

---

## Exit Criteria

Phase 10 is COMPLETE when:

- [x] Core works with zero external tools (Tier 0 only)
- [x] Tool failures are isolated (no BSKG crashes)
- [x] State versioning tracks graph changes
- [x] Recovery commands work
- [x] Stress test passes 5/5 scenarios:
  1. Kill Slither mid-run ✓
  2. Remove .vkg directory ✓
  3. Corrupt graph.json ✓
  4. Timeout external tools ✓
  5. Disk full during write ✓

---

## Files Created by This Phase

| File | Purpose |
|------|---------|
| `src/true_vkg/core/tiers.py` | Tier definitions |
| `src/true_vkg/core/availability.py` | Availability checker |
| `src/true_vkg/tools/runner.py` | Isolated tool runner |
| `src/true_vkg/tools/timeout.py` | Timeout handling |
| `src/true_vkg/state/versioning.py` | Version tracking |
| `src/true_vkg/state/staleness.py` | Staleness detection |
| `src/true_vkg/cli/tools.py` | Tools subcommand |
| `src/true_vkg/cli/doctor.py` | Doctor command |
| `src/true_vkg/cli/repair.py` | Repair command |
| `src/true_vkg/core/network.py` | Network detection |
| `src/true_vkg/analysis/results.py` | Result aggregation |
| `src/true_vkg/analysis/partial.py` | Partial result handling |
| `tests/stress/chaos.py` | Chaos injection |
| `tests/stress/test_failure_scenarios.py` | Stress tests |

---

## How to Pick Up a Task

Each task file in `tasks/` is self-contained with:
1. **Objective** - What to accomplish
2. **Context** - What already exists, what files to read
3. **Files to Create/Modify** - Exact code to write
4. **Test Requirements** - Tests to create
5. **Validation Criteria** - Checklist for completion
6. **Exit Gate** - When task is DONE

Start with R10.1 (Failure Mode Analysis) as it blocks other tasks.

---

*Phase 10 Tracker | Version 3.0 | 2026-01-07*
*Reorganized with independent task files*

---

## Alignment Addendum (Workstream P)

### Workstream P: Alignment Tasks

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P10.P.1 | Define missing-tool bucket override rules | `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-10/TRACKER.md` | P14.P.1 | Override table | Phase 3 CLI outputs bucket changes | Tier A determinism preserved | New tool outage mode |
| P10.P.2 | Add missing tool fields + rationale in evidence packets | `docs/PHILOSOPHY.md`, `src/true_vkg/` | P3.P.1 | Schema notes for `missing_tools` | Phase 20 audit checks missing tools | Evidence packet versioned | Missing tool detected |

### Review Tasks (Required + Phase-Specific)

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P10.R.1 | Phase necessity review (keep/cut/modify) | `task/4.0/MASTER.md`, `docs/PHILOSOPHY.md` | - | Decision log in tracker | Decision referenced in alignment sweep | None | Phase outputs no longer needed |
| P10.R.2 | Task necessity review for P10.P.* | `task/4.0/phases/phase-10/TRACKER.md`, `task/codex/vkg_4_0_alignment_super_task.md` | P10.P.1-P10.P.2 | Task justification log | Each task has keep/merge decision | Avoid overlap with Phase 11 | Redundant task discovered |
| P10.R.3 | Conflict review with downstream phases | `task/4.0/MASTER.md` | P10.P.1-P10.P.2 | Conflict notes in tracker | Conflicts resolved or escalated | Tier A/Tier B separation | Conflict discovered |
| P10.R.4 | Ensure degraded mode does not conflict with Phase 11 LLM usage | `task/4.0/phases/phase-11/TRACKER.md` | P10.P.1 | Compatibility note | LLM safety gates remain intact | No Tier B leak | Conflict detected |

### Dynamic Task Spawning (Alignment)

**Trigger:** New tool integration added.
**Spawn:** Add degraded-mode handling task.
**Example spawned task:** P10.P.3 Add bucket overrides for a new tool outage mode.
