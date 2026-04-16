# BSKG 4.0 Phases - Structure & Coordination

**Last Updated:** 2026-01-07
**Template Version:** 2.0

---

## Overview

VKG 4.0 is organized into 19 phases plus a future/creative upgrades bucket. Each phase has a dedicated tracker file (`TRACKER.md`) that follows the standard `PHASE_TEMPLATE.md` format.

**Key Documents:**
| Document | Location | Purpose |
|----------|----------|---------|
| MASTER.md | `task/4.0/MASTER.md` | High-level roadmap, decision gates |
| TODO.md | `task/4.0/TODO.md` | Daily tracking, current focus |
| PHASE_TEMPLATE.md | `phases/PHASE_TEMPLATE.md` | Standard format for all trackers |
| INDEX.md | `phases/INDEX.md` | Cross-phase task index |
| README.md | `phases/README.md` | This file - structure overview |

---

## Phase Dependency Graph

```
                              PHASE 0: BUILDER REFACTOR (Foundation)
                                            │
                                            ▼
                              PHASE 1: FIX DETECTION ✅ COMPLETE
                                            │
                                            ▼
                              PHASE 2: BENCHMARK INFRASTRUCTURE (IN PROGRESS)
                                            │
                                            ▼
                              PHASE 3: BASIC CLI & TASK SYSTEM (BLOCKED)
                                            │
                                            ▼
                              PHASE 4: TEST SCAFFOLDING
                                            │
                                            ▼
                              PHASE 5: REAL-WORLD VALIDATION
                                            │
            ┌───────────────────────────────┼───────────────────────────────┐
            │                               │                               │
            ▼                               ▼                               ▼
    PHASE 6: BEADS              PHASE 7: CONSERVATIVE         PHASE 8: METRICS
    (Rich Context)                 LEARNING                 & OBSERVABILITY
            │                               │                               │
            └───────────────────────────────┼───────────────────────────────┘
                                            │
                                            ▼
                              PHASE 9: CONTEXT OPTIMIZATION (PPR)
                                            │
                                            ▼
                              PHASE 10: GRACEFUL DEGRADATION
                                            │
            ┌───────────────────────────────┼───────────────────────────────┐
            │                               │                               │
            ▼                               ▼                               ▼
   PHASE 11: LLM            PHASE 12: AGENT SDK         PHASE 13: GRIMOIRES
   INTEGRATION (TIER B)         MICRO-AGENTS               & SKILLS
            │                               │                               │
            └───────────────────────────────┼───────────────────────────────┘
                                            │
                                            ▼
                              PHASE 14: CONFIDENCE CALIBRATION
                                            │
                                            ▼
                              PHASE 15: NOVEL SOLUTIONS INTEGRATION
                                            │
                                            ▼
                              PHASE 16: RELEASE & DISTRIBUTION
                                            │
                                            ▼
                              PHASE 17: VULNDOCS KNOWLEDGE SYSTEM
                                            │
                                            ▼
                              PHASE 18: VULNDOCS MINING + RETRIEVAL
                                            │
                                            ▼
                              PHASE 19: REAL-WORLD AGENTIC VALIDATION
```

---

## Phase Summary Table

| Phase | Name | Priority | Status | Est. Hours | Depends On | Unblocks |
|-------|------|----------|--------|------------|------------|----------|
| **0** | Builder Refactor | CRITICAL | TODO | ~90-120h | - | 1 |
| **1** | Fix Detection | CRITICAL | COMPLETE (84.6%) | - | 0 | 2 |
| **2** | Benchmark Infrastructure | CRITICAL | IN PROGRESS (8/12 tasks) | ~40h | 1 | 3 |
| **3** | Basic CLI & Task System | HIGH | BLOCKED (by Phase 2) | ~50h | 2 | 4 |
| **4** | Test Scaffolding | HIGH | COMPLETE | ~35h | 3 | 5 |
| **5** | Real-World Validation | HIGH | IN PROGRESS | ~40h | 4 | 6,7,8 |
| **6** | Beads System | MEDIUM | COMPLETE | ~45h | 5 | 9 |
| **7** | Conservative Learning | MEDIUM | COMPLETE | ~30h | 5 | 9 |
| **8** | Metrics & Observability | MEDIUM | COMPLETE (core) - optional tasks pending | ~35h | 5 | 9 |
| **9** | Context Optimization (PPR) | MEDIUM | COMPLETE (core) - fixtures pending | ~40h | 6,7,8 | 10 |
| **10** | Graceful Degradation | MEDIUM | COMPLETE (core) - optional tasks pending | ~30h | 9 | 11,12,13 |
| **11** | LLM Integration (Tier B) | MEDIUM | IN PROGRESS | ~55h | 10 | 14 |
| **12** | Agent SDK Micro-Agents | LOW | IN PROGRESS (deferred MUST tasks pending) | ~45h | 10 | 14 |
| **13** | Grimoires & Skills | MEDIUM | COMPLETE | ~35h | 10 | 14 |
| **14** | Confidence Calibration | MEDIUM | COMPLETE | ~43h | 11,12,13 | 15 |
| **15** | Novel Solutions Integration | LOW | COMPLETE | ~36h | 14 | 16 |
| **16** | Release & Distribution | MEDIUM | TODO (unblocked) | ~41h | 15 | - |
| **17** | VulnDocs Knowledge System | HIGH | TODO | ~80h | 11 | 18 |
| **18** | VulnDocs Mining + Retrieval | CRITICAL | COMPLETE (core) - optional task pending | ~98h | 17 | 19 |
| **19** | Real-World Agentic Validation | CRITICAL | TODO | ~120h | 18 | - |

**Total Estimated:** ~900h (200+ tasks across 19 phases)

---

## Decision Gates

Three major decision gates serve as GO/NO-GO checkpoints:

### Gate 1: After Phase 5 (Real-World Validation)

| Criteria | Threshold | Action if Failed |
|----------|-----------|------------------|
| Real-world precision | >= 70% | STOP. Fix detection before proceeding. |
| False positive rate | < 30% | STOP. Add discriminators to patterns. |
| Auditor verdict | "Has potential" or better | STOP. Get feedback, understand why. |
| Builder.py failure rate | < 20% on 100 real contracts | STOP. Fix builder.py bugs. |

### Gate 2: After Phase 8 (Metrics & Observability)

| Criteria | Threshold | Action if Failed |
|----------|-----------|------------------|
| User testing | >= 3 users have tried BSKG | Pivot. Focus on distribution. |
| CLI usability | "Intuitive" rating | Iterate CLI before LLM integration. |
| Task persistence | Works across sessions | Fix Beads before LLM depends on it. |

### Gate 3: After Phase 11 (LLM Integration)

| Criteria | Threshold | Action if Failed |
|----------|-----------|------------------|
| Tier B precision improvement | >= 10% over Tier A alone | Cut scope. Tier B becomes optional. |
| Cost per audit | < $2.00 | Optimize prompts or reduce LLM usage. |
| Multi-agent value | Debate reduces FP by 15% | Simplify to single-agent verification. |

---

## Phase Groupings

### FOUNDATION (Phases 0-5)
**Goal:** Get detection working and validated on real-world code.

| Phase | Goal | Key Deliverable |
|-------|------|-----------------|
| 0 | Builder refactor | Clean, testable builder.py |
| 1 | Fix detection | 84.6% DVDeFi detection |
| 2 | Benchmark infrastructure | Automated benchmark CI |
| 3 | CLI & task system | Working CLI for LLM agents |
| 4 | Test scaffolding | Compilable test generation |
| 5 | Real-world validation | Auditor feedback, 6+ projects |

**Exit:** Phase 5 complete with >= 70% real-world precision

### ENHANCEMENT (Phases 6-10)
**Goal:** Add context, learning, and robustness features.

| Phase | Goal | Key Deliverable |
|-------|------|-----------------|
| 6 | Beads system | Rich context for findings |
| 7 | Conservative learning | Self-improving patterns |
| 8 | Metrics & observability | Usage and performance tracking |
| 9 | Context optimization | Token-efficient LLM output |
| 10 | Graceful degradation | Offline mode, fallbacks |

**Exit:** Phase 10 complete with observable, resilient system

### INTELLIGENCE (Phases 11-15)
**Goal:** Add LLM reasoning and multi-agent capabilities.

| Phase | Goal | Key Deliverable |
|-------|------|-----------------|
| 11 | LLM integration | Tier B verification |
| 12 | Agent SDK | Micro-agents for specialized tasks |
| 13 | Grimoires & skills | Vulnerability playbooks |
| 14 | Confidence calibration | Meaningful confidence scores |
| 15 | Novel solutions | Evaluated research features |

**Exit:** Phase 15 complete with calibrated, intelligent system

### RELEASE (Phase 16)
**Goal:** Package and distribute BSKG 4.0.

| Phase | Goal | Key Deliverable |
|-------|------|-----------------|
| 16 | Release & distribution | PyPI, Docker, GitHub release |

**Exit:** Fresh install works on clean system in < 10 minutes

---

## Cross-Phase Dependencies

### Critical Dependencies (Must Be Resolved)

| Upstream | Downstream | Artifact | Risk if Missing |
|----------|------------|----------|-----------------|
| Phase 2 | Phase 3, 4, 5 | Benchmark infrastructure | Can't measure improvement |
| Phase 5 | Phase 6-16 | Real-world validation baseline | Building on unvalidated foundation |
| Phase 6 | Phase 9 | Beads context format | Context optimization has nothing to optimize |
| Phase 11 | Phase 14 | LLM findings | No findings to calibrate |

### Parallel Opportunities

These can be worked on in parallel if resources available:

- **Phases 6, 7, 8:** Independent after Phase 5
- **Phases 11, 12, 13:** Independent after Phase 10
- **Phase 16 prep:** Documentation can start during Phase 14

### Known Dependency Issues

1. **Phase 0 alignment pending:** Phase 0 now has a tracker, but alignment tasks are still TODO and must complete before Phase 1 dependencies.

2. **Tight coupling 11-14:** Phases 11, 12, 13 all need to complete before 14 starts. Consider if some Phase 14 work (ground truth collection) can start earlier.

3. **No explicit test dependencies:** Many phases require tests from earlier phases but don't explicitly list which test fixtures they need.

---

## How to Pick Tasks

### Daily Workflow

1. **Check current phase:** Look at `TODO.md` for current phase
2. **Find unblocked tasks:** In phase tracker, find tasks with all dependencies DONE
3. **Check INDEX.md:** Verify task isn't already in progress
4. **Update status:** Mark task as IN PROGRESS in tracker
5. **Work:** Implement with validation at each step
6. **Complete:** Update tracker and INDEX.md when done

### Task Selection Priority

1. **MUST tasks in current phase** - Required for phase completion
2. **Blocking tasks for other phases** - Unblock downstream work
3. **SHOULD tasks with highest impact** - Improve quality
4. **COULD tasks if time permits** - Nice-to-have

### When Stuck

1. **Check research requirements:** Is there unfinished research?
2. **Check dependencies:** Is something actually blocking you?
3. **Check alternative approaches:** What else was considered?
4. **Escalate:** Document the blocker and move to next task

---

## File Structure

```
task/4.0/
├── MASTER.md                    # High-level roadmap
├── TODO.md                      # Daily tracking
├── protocols/                   # Cross-cutting protocols
│   ├── BUILDER-PROTOCOL.md      # How to modify builder.py
│   ├── CONTINGENCY-PATHS.md     # Fallback strategies
│   ├── PROPERTY-SCHEMA-CONTRACT.md  # Property validation
│   └── TEST-SANDBOX.md          # Test isolation
│
└── phases/
    ├── README.md                # This file
    ├── INDEX.md                 # Cross-phase task index
    ├── PHASE_TEMPLATE.md        # Standard format
    │
    ├── phase-0/
    │   ├── TRACKER.md           # Builder refactor + alignment foundation
    │   └── BUILDER-REFACTOR.md  # Foundation work (legacy docs)
    │
    ├── phase-1/
    │   └── TRACKER.md           # Fix Detection
    │
    ├── phase-2/
    │   └── TRACKER.md           # Benchmark Infrastructure
    │
    ├── phase-3/
    │   └── TRACKER.md           # Basic CLI & Task System
    │
    ... (phases 4-16)
    │
    └── future/
        └── CREATIVE-UPGRADES.md # Ideas for post-4.0
```

---

## Quality Standards

### Every Phase Must Have

1. **Clear entry gate:** What must be true to start
2. **Clear exit gate:** What must be true to complete
3. **Task registry:** All tasks with IDs, estimates, dependencies
4. **Test requirements:** What tests this phase adds
5. **Cross-phase dependencies:** What it needs and what depends on it
6. **Reflection protocol:** Brutal self-critique after each task

### Every Task Must Have

1. **Unique ID:** `[Phase].[TaskNumber]` (e.g., `2.4`)
2. **Estimated hours:** Realistic estimate
3. **Dependencies:** What must complete first
4. **Exit criteria:** Testable completion criteria
5. **Test requirements:** What tests validate it

### Every Completion Must Have

1. **Updated tracker:** Status changed to COMPLETE
2. **Updated INDEX.md:** Cross-phase index updated
3. **Passing tests:** All relevant tests pass
4. **No regressions:** Benchmark doesn't degrade

---

## Architectural Issues Identified

### STRUCTURAL ISSUES

1. **Phase 0 alignment pending:** Alignment tasks are defined but not executed; downstream phases depend on packet mapping and bucket defaults.

2. **Missing Section 0 (Cross-Phase Dependencies):** Most existing trackers don't have the new Section 0 that captures cross-phase dependencies. Trackers should be updated to v2.0 template.

3. **Unclear status sync:** No automated way to ensure INDEX.md stays in sync with individual tracker files.

4. **No versioning on trackers:** Hard to know if a tracker is up-to-date with template changes.

### DEPENDENCY ISSUES

1. **Phases 6,7,8 can be parallel:** Dependency graph shows sequential, but all three depend only on Phase 5 and are independent of each other.

2. **Phase 14 bottleneck:** Phase 14 waits for 11, 12, AND 13 to complete. Consider if parts of 14 (ground truth collection) can start earlier with Phase 5 data.

3. **No explicit artifact contracts:** Phases don't explicitly define what artifacts they produce for downstream phases.

### CONTENT ISSUES

1. **Duplicate task definitions:** Some tasks appear in MASTER.md priority gates AND individual trackers with slightly different descriptions.

2. **Inconsistent task numbering:** Some phases use R[N].X for research, others don't.

3. **Missing test fixture dependencies:** Phases don't specify which fixtures from earlier phases they need.

### RECOMMENDATIONS

1. **Complete Phase 0 alignment tasks:** Execute P0.P.1-P0.P.5 and review tasks in `phase-0/TRACKER.md`.

2. **Update all trackers to v2.0:** Add Section 0 (Cross-Phase Dependencies) to all existing trackers.

3. **Define artifact contracts:** Each phase should explicitly list artifacts it produces for downstream phases.

4. **Create INDEX.md:** Centralized task index (created alongside this README).

5. **Add template version to all trackers:** Footer should show which template version was used.

---

## Contributing

### Adding a New Phase

1. Create directory: `phases/phase-N/`
2. Copy `PHASE_TEMPLATE.md` to `phase-N/TRACKER.md`
3. Fill in all sections (none should remain as placeholders)
4. Update this README with new phase
5. Update INDEX.md with new phase tasks
6. Update MASTER.md phase summary

### Updating a Phase Tracker

1. Make changes in `phase-N/TRACKER.md`
2. Update version history at bottom
3. Update INDEX.md if task status changed
4. If structural changes, consider updating PHASE_TEMPLATE.md

### Proposing Template Changes

1. Document rationale for change
2. Update PHASE_TEMPLATE.md
3. Increment template version
4. Document migration path for existing trackers
5. Update this README

---

*Phases README | Version 1.0 | 2026-01-07*
