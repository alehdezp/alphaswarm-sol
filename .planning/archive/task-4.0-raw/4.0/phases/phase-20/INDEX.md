# Phase 20: Final Testing Phase (VKG 4.0)

**Status:** TODO
**Priority:** CRITICAL - Final real-world usability gate
**Last Updated:** 2026-01-08
**Owner:** BSKG Team

---

## Mission

Prove BSKG works in **real-world auditing conditions** with **agentic orchestration**. This phase is a brutal, exhaustive validation of usability, correctness, and reliability. The output is not code changes; it is a **testing dossier** documenting **what works, what fails, and why**, with a prioritized improvement backlog.

This is the final reality check. If BSKG fails here, it is not ready for real audits.

---

## Global Rules (Non-Negotiable)

- **No code changes.** This phase is validation only.
- Every run must capture **inputs, commands, outputs, and rationale**.
- All failures require **root-cause analysis** (not just symptoms).
- Claude Code agents must log **tool choices** and **decision paths**.
- Any ambiguity or missing capability must be documented.

---

## Entry Gate (Must Be True)

- Phases 1-19 complete or explicitly waived by owner.
- VulnDocs crawled, stored locally, and retrievable.
- CLI tooling stable (build, query, report).
- Agentic workflows enabled (Claude Code + skills).

---

## Exit Gate (Must Be True)

- All subphases executed end-to-end.
- Real-world corpus evaluated and documented.
- Agentic orchestration validated with repeatable results.
- Limitations report completed with root-cause analysis.
- Improvement backlog created with priority, risk, and effort estimates.

---

## Phase Map (Subphases)

| Subphase | File | Purpose |
|---------|------|---------|
| 20.A | `PHASE-20A-READINESS.md` | Environment, instrumentation, runbook |
| 20.B | `PHASE-20B-CORPUS.md` | Corpus + ground truth labeling |
| 20.C | `PHASE-20C-AGENTIC-ORCHESTRATION.md` | Claude Code orchestration trials |
| 20.D | `PHASE-20D-END-TO-END.md` | Full pipeline validation per vuln |
| 20.E | `PHASE-20E-ADVERSARIAL.md` | Obfuscation, hostile inputs, edge cases |
| 20.F | `PHASE-20F-PERFORMANCE.md` | Scale, latency, throughput, stability |
| 20.G | `PHASE-20G-LIMITATIONS.md` | Limitations + improvement backlog |
| 20.H | `PHASE-20H-HUMAN-SHADOW.md` | Human vs agent shadow audits |
| 20.I | `PHASE-20I-OPERATIONAL-UX.md` | CLI/UX friction and failure modes |
| 20.J | `PHASE-20J-VULNDOCS-AUDIT.md` | VulnDocs field completeness audit |
| 20.K | `PHASE-20K-TEST-MATRIX.md` | Behavior-first test matrix |
| 20.Z | `PHASE-20Z-READINESS-DOSSIER.md` | Final dossier assembly outline |

---

## PHILOSOPHY Alignment Checklist (docs/PHILOSOPHY.md)

Phase 20 must explicitly validate the core philosophy pillars:

- **Behavior-first detection**: D/E enforce behavioral signatures and name-agnostic checks.
- **Semantic operations + signatures**: D/E require op sequences in evidence.
- **Two-tier patterns**: D validates Tier A and Tier B behavior separately.
- **Multi-agent verification**: C/H require attacker/defender/verifier roles and cross-checks.
- **Beads-based orchestration**: C/H ensure evidence packets and bead tracking are used.
- **Tool orchestration**: C/I validate multi-tool coordination and error recovery.
- **VulnDocs knowledge system**: J audits minimal-context retrieval and field completeness.

If any pillar is not validated, Phase 20 is incomplete.

---

## Pillar Coverage Matrix

| Pillar | Primary Subphases | Primary Artifacts |
|--------|-------------------|-------------------|
| Behavior-first detection | 20.D, 20.E, 20.H | END_TO_END_RESULTS, ADVERSARIAL_RESULTS, HUMAN_SHADOW |
| Semantic operations + signatures | 20.B, 20.D, 20.E, 20.J | GROUND_TRUTH, END_TO_END_RESULTS, ADVERSARIAL_RESULTS, VULNDOCS_AUDIT |
| Two-tier pattern system | 20.D | END_TO_END_RESULTS |
| Multi-agent verification | 20.C, 20.H | AGENT_SCORECARDS, HUMAN_SHADOW |
| Beads-based orchestration | 20.C, 20.D | AGENT_SCORECARDS, END_TO_END_RESULTS, BEAD_LOG |
| Tool orchestration | 20.C, 20.I | ORCHESTRATION_TRACE, UX_FAILURES |
| VulnDocs knowledge system | 20.J | VULNDOCS_AUDIT |

All pillars must have at least one **PASS** entry in `PILLAR_COVERAGE.md`.

---

## Master Task Registry

| ID | Task | Depends On | Status | Output |
|----|------|------------|--------|--------|
| 20.1 | Readiness + instrumentation | Phase 18 | TODO | Runbook + environment manifest |
| 20.2 | Corpus + ground truth | 20.1 | TODO | Corpus manifest + labeling protocol |
| 20.3 | Agentic orchestration trials | 20.2 | TODO | Agent scorecards + failure analysis |
| 20.4 | End-to-end validation | 20.3 | TODO | Precision/recall report |
| 20.5 | Adversarial + stress suite | 20.4 | TODO | Robustness report |
| 20.6 | Performance + scalability | 20.4 | TODO | Benchmark report |
| 20.7 | Limitations + backlog | 20.4-20.6 | TODO | Final dossier |
| 20.8 | Human shadow audits | 20.4 | TODO | Human vs agent delta report |
| 20.9 | Operational UX + recovery | 20.3 | TODO | UX failure log |
| 20.10 | VulnDocs audit | 20.2 | TODO | Field completeness report |
| 20.11 | Test matrix coverage | 20.2 | TODO | Behavior-first matrix complete |
| 20.12 | Dossier assembly | 20.7 | TODO | Readiness dossier written |

---

## Required Artifacts

- `task/4.0/phases/phase-20/artifacts/ENVIRONMENT.md`
- `task/4.0/phases/phase-20/artifacts/RUNBOOK.md`
- `task/4.0/phases/phase-20/artifacts/CORPUS_MANIFEST.md`
- `task/4.0/phases/phase-20/artifacts/GROUND_TRUTH.md`
- `task/4.0/phases/phase-20/artifacts/AGENT_SCORECARDS.md`
- `task/4.0/phases/phase-20/artifacts/END_TO_END_RESULTS.md`
- `task/4.0/phases/phase-20/artifacts/ADVERSARIAL_RESULTS.md`
- `task/4.0/phases/phase-20/artifacts/PERFORMANCE_RESULTS.md`
- `task/4.0/phases/phase-20/artifacts/LIMITATIONS.md`
- `task/4.0/phases/phase-20/artifacts/IMPROVEMENT_BACKLOG.md`
- `task/4.0/phases/phase-20/artifacts/HUMAN_SHADOW.md`
- `task/4.0/phases/phase-20/artifacts/UX_FAILURES.md`
- `task/4.0/phases/phase-20/artifacts/VULNDOCS_AUDIT.md`
- `task/4.0/phases/phase-20/artifacts/ORCHESTRATION_TRACE.md`
- `task/4.0/phases/phase-20/artifacts/BEAD_LOG.md`
- `task/4.0/phases/phase-20/artifacts/PILLAR_COVERAGE.md`
- `task/4.0/phases/phase-20/artifacts/READINESS_DOSSIER.md`

---

## Templates

- `task/4.0/phases/phase-20/SUBAGENT_SECURITY_ASSESSMENT_TEMPLATE.md`
- `task/4.0/phases/phase-20/REALTIME_LOGIC_AUTH_TEST_PACK.md`

---

## Severity Definitions

- **Blocker:** System cannot be used for real-world audits.
- **Critical:** High false positives/negatives or incorrect conclusions.
- **Major:** Significant usability or coverage limitations.
- **Minor:** Quality or clarity issues that degrade UX.

---

## Final Deliverable

A single **VKG Real-World Readiness Dossier** assembled from the artifacts above, summarizing:
- What works reliably
- What fails and why
- Gaps in tool coverage
- Exact improvements required
