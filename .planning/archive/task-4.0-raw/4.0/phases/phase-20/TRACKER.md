# Phase 20: Final Testing Phase

**Status:** TODO (Final gate after Phases 1-19) **Priority:** CRITICAL **Last Updated:**
2026-01-08 **Author:** BSKG Team

---

## Quick Reference

| Field | Value |
|-------|-------|
| Entry Gate | Phases 1-19 complete + VulnDocs populated |
| Exit Gate | Real-world dossier completed + limitations documented |
| Philosophy Pillars | Agentic Automation, Self-Improvement |
| Estimated Hours | 152h |
| Task Count | 12 |
| Test Count Target | 500+ real-world cases |

---

## PHILOSOPHY Alignment (docs/PHILOSOPHY.md)

Phase 20 must validate every pillar:

- Behavior-first detection and name-agnostic checks
- Semantic operations and behavioral signatures in evidence
- Tier A vs Tier B pattern separation
- Multi-agent verification and testing roles
- Beads-based task orchestration with evidence packets
- Tool orchestration and recovery behavior
- VulnDocs minimal-context retrieval for audits

---

## Canonical Plan

The full Phase 20 plan lives in `task/4.0/phases/phase-20/INDEX.md` with subphases:
- `task/4.0/phases/phase-20/PHASE-20A-READINESS.md`
- `task/4.0/phases/phase-20/PHASE-20B-CORPUS.md`
- `task/4.0/phases/phase-20/PHASE-20C-AGENTIC-ORCHESTRATION.md`
- `task/4.0/phases/phase-20/PHASE-20D-END-TO-END.md`
- `task/4.0/phases/phase-20/PHASE-20E-ADVERSARIAL.md`
- `task/4.0/phases/phase-20/PHASE-20F-PERFORMANCE.md`
- `task/4.0/phases/phase-20/PHASE-20G-LIMITATIONS.md`
- `task/4.0/phases/phase-20/PHASE-20H-HUMAN-SHADOW.md`
- `task/4.0/phases/phase-20/PHASE-20I-OPERATIONAL-UX.md`
- `task/4.0/phases/phase-20/PHASE-20J-VULNDOCS-AUDIT.md`



### IMPORTANT: Before starting with the implementation each phase, you must review each phase 1 by 1 one ensuring that they makes sense, critically improve them before starting. do not blindly trust that the are well implemented

---

## Task Registry

| ID | Task | Est. | Priority | Depends | Status | Description |
|----|------|------|----------|---------|--------|-------------|
| 20.1 | Readiness + instrumentation | 16h | MUST | Phase 18 | TODO | Runbook, environment manifest |
| 20.2 | Corpus + ground truth | 24h | MUST | 20.1 | TODO | Real-world dataset + labels |
| 20.3 | Agentic orchestration trials | 16h | MUST | 20.2 | TODO | Claude Code scorecards |
| 20.4 | End-to-end validation | 20h | MUST | 20.3 | TODO | Precision/recall report |
| 20.5 | Adversarial + stress | 16h | MUST | 20.4 | TODO | Robustness report |
| 20.6 | Performance + scalability | 12h | MUST | 20.4 | TODO | Benchmarks |
| 20.7 | Limitations + backlog | 16h | MUST | 20.4-20.6 | TODO | Final dossier |
| 20.8 | Human shadow audits | 10h | SHOULD | 20.4 | TODO | Human vs agent delta report |
| 20.9 | Operational UX + recovery | 6h | SHOULD | 20.3 | TODO | UX failure log |
| 20.10 | VulnDocs audit | 4h | SHOULD | 20.2 | TODO | Field completeness report |
| 20.11 | Test matrix coverage | 6h | MUST | 20.2 | TODO | Behavior-first matrix complete |
| 20.12 | Dossier assembly | 8h | MUST | 20.7 | TODO | Readiness dossier written |

---

## Exit Criteria

- [ ] All 12 tasks complete
- [ ] Dossier artifacts produced
- [ ] Limitations documented with root causes
- [ ] Improvement backlog prioritized
- [ ] Pillar coverage recorded in `task/4.0/phases/phase-20/artifacts/PILLAR_COVERAGE.md`

---

## Alignment Addendum (Workstream P)

### Workstream P: Alignment Tasks

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P20.P.1 | Run evidence packet completeness audit across corpus | `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-20/TRACKER.md` | P8.P.2 | Audit report spec | Gate 4 criteria | Evidence packet versioned | Completeness below threshold |
| P20.P.2 | Stress test debate protocol on high-impact disputes | `docs/PHILOSOPHY.md`, `task/4.0/phases/phase-11/TRACKER.md` | P11.P.1 | Debate reports | Unresolved disputes logged | Dispute handling required | Unresolved critical debate |

### Review Tasks (Required + Phase-Specific)

| ID | Objective | Start here | Dependencies | Deliverables | Validation | Conflicts | Spawn Triggers |
|----|-----------|------------|--------------|--------------|------------|-----------|----------------|
| P20.R.1 | Phase necessity review (keep/cut/modify) | `task/4.0/MASTER.md`, `docs/PHILOSOPHY.md` | - | Decision log in tracker | Decision referenced in alignment sweep | None | Phase outputs no longer needed |
| P20.R.2 | Task necessity review for P20.P.* | `task/4.0/phases/phase-20/TRACKER.md`, `task/codex/vkg_4_0_alignment_super_task.md` | P20.P.1-P20.P.2 | Task justification log | Each task has keep/merge decision | Avoid overlap with Phase 16 | Redundant task discovered |
| P20.R.3 | Conflict review with downstream phases | `task/4.0/MASTER.md` | P20.P.1-P20.P.2 | Conflict notes in tracker | Conflicts resolved or escalated | Tier A/Tier B separation | Conflict discovered |
| P20.R.4 | Verify VulnDocs track complete before GA | `task/4.0/phases/phase-17/TRACKER.md` | P17.P.1-P18.P.2 | Completion note | Gate 4 references VulnDocs completion | No GA without VulnDocs | VulnDocs incomplete |

### Dynamic Task Spawning (Alignment)

**Trigger:** Evidence packet completeness < threshold.
**Spawn:** Add remediation tasks in Phase 0/1/3.
**Example spawned task:** P20.P.3 Add remediation tasks for missing evidence packet fields.
