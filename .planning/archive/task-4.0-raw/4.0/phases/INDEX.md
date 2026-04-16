# BSKG 4.0 - Cross-Phase Task Index

**Last Updated:** 2026-01-09
**Total Tasks:** 190+ (15 new alignment tasks from philosophy gap analysis)
**Total Est. Hours:** ~1010h

---

## Status Legend

| Symbol | Status | Description |
|--------|--------|-------------|
| `[ ]` | TODO | Not started |
| `[~]` | IN PROGRESS | Currently being worked on |
| `[x]` | COMPLETE | Finished and validated |
| `[-]` | BLOCKED | Waiting on dependencies |
| `[!]` | NEEDS ATTENTION | Has issues or blockers |

---

## Quick Stats

| Phase | Total Tasks | TODO | In Progress | Complete | Blocked |
|-------|-------------|------|-------------|----------|---------|
| 0 | 17 | 6 | 0 | 11 | 0 |
| 1 | ~23 | 0 | 0 | 23 | 0 |
| 2 | 12 | 0 | 0 | 12 | 0 |
| 3 | 17 | 0 | 0 | 17 | 0 |
| 4 | 12 | 0 | 0 | 12 | 0 |
| 5 | 11 | 0 | 0 | 11 | 0 |
| 6 | 16 | 0 | 0 | 16 | 0 |
| 7 | 8 | 0 | 0 | 8 | 0 |
| 8 | 11 | 2 | 0 | 9 | 0 |
| 9 | 9 | 1 | 0 | 8 | 0 |
| 10 | 9 | 2 | 0 | 7 | 0 |
| 11 | 16 | 0 | 0 | 13 | 3 SKIP |
| 12 | 12 | 0 | 0 | 8 | 4 DEFER |
| 13 | 9 | 0 | 0 | 9 | 0 |
| 14 | 8 | 0 | 0 | 8 | 0 |
| 15 | 7 | 0 | 0 | 7 | 0 |
| 16 | 11 | 11 | 0 | 0 | 0 |
| 17 | 16 | 16 | 0 | 0 | 0 |
| 18 | 12 | 1 | 0 | 11 | 0 |
| 19 | 14 | 14 | 0 | 0 | 0 |
| 20 | 12 | 12 | 0 | 0 | 0 |

---

## Phase 0: Builder Refactor + Alignment Foundation [IN PROGRESS]

**Status:** IN PROGRESS (11/17 tasks complete - all alignment tasks done, builder refactor pending)
**Tracker:** `phases/phase-0/TRACKER.md`

| ID | Task | Est. | Status | Notes |
|----|------|------|--------|-------|
| 0.BR.1 | Extract contexts | 8-12h | [ ] | BR.1-EXTRACT-CONTEXTS.md |
| 0.BR.2 | Centralize tokens | 6-8h | [ ] | BR.2-CENTRALIZE-TOKENS.md |
| 0.BR.3 | Split detectors | 40-60h | [ ] | BR.3-SPLIT-DETECTORS.md |
| 0.BR.4 | Table-driven pipeline | 8-12h | [ ] | BR.4-TABLE-DRIVEN-PIPELINE.md |
| 0.BR.5 | Performance pass | 12-16h | [ ] | BR.5-PERFORMANCE.md |
| 0.BR.6 | Protocol types | 6-10h | [ ] | BR.6-PROTOCOL-TYPES.md |
| P0.P.1 | Evidence packet mapping (post-graph) | 2h | [x] | P0.P.1-EVIDENCE-PACKET-MAPPING.md |
| P0.P.2 | Bucket defaults for Tier A | 2h | [x] | P0.P.2-BUCKET-DEFAULTS.md |
| P0.P.3 | Graph-quality debate trigger | 2h | [x] | P0.P.3-GRAPH-QUALITY-ROUTING.md |
| P0.P.4 | VulnDocs category mapping | 2h | [x] | P0.P.4-VULNDOCS-MAPPING.md |
| P0.P.5 | Evidence packet completeness tests | 2h | [x] | P0.P.5-PACKET-COMPLETENESS-TESTS.md |
| P0.P.6 | Deduplication rule validation tests | 2h | [x] | P0.P.6-DEDUPLICATION-TESTS.md |
| P0.P.7 | Tool disagreement routing rules | 2h | [x] | P0.P.7-TOOL-DISAGREEMENT-ROUTING.md |
| P0.P.8 | Evidence packet fallback rules | 3h | [x] | P0.P.8-FALLBACK-RULES.md |
| R0.1 | Phase necessity review | 1h | [x] | R0-REVIEW-DECISIONS.md |
| R0.2 | Task necessity review | 2h | [x] | R0-REVIEW-DECISIONS.md |
| R0.3 | Conflict review | 1h | [x] | R0-REVIEW-DECISIONS.md |

---

## Phase 1: Fix Detection [COMPLETE]

**Status:** COMPLETE (84.6% detection rate)
**Tracker:** `phases/phase-1/TRACKER.md`

| ID | Task | Est. | Status | Notes |
|----|------|------|--------|-------|
| R1.1 | DVDeFi analysis research | 4h | [x] | Completed |
| 1.A.1 | Test sandbox setup | 6h | [x] | TEST-SANDBOX.md created |
| 1.A.2 | Builder change protocol | 4h | [x] | BUILDER-PROTOCOL.md created |
| 1.A.3 | Rollback mechanism | 2h | [x] | Git-based rollback |
| 1.A.4 | Property schema contract | 4h | [x] | PROPERTY-SCHEMA-CONTRACT.md |
| 1.B.1 | Rename resistance harness | 6h | [x] | test_rename_resistance.py |
| 1.B.2 | Graph fingerprint v1 | 4h | [x] | fingerprint.py |
| 1.B.3 | CI fingerprint check | 2h | [x] | GitHub Actions |
| 1.C.1 | Builder audit | 8h | [x] | Completed |
| 1.C.2 | Strict equality fix | 3h | [x] | dos-strict-equality detection |
| 1.C.3 | Call target tracking | 4h | [x] | Fixed in builder.py |
| 1.C.4 | Build manifest | 2h | [x] | build_manifest.json |
| 1.D.1 | Callback detection | 6h | [x] | callback-controlled-recipient |
| 1.D.2 | Flash loan patterns | 6h | [x] | flash-loan-reward-attack |
| 1.D.3 | DEX oracle patterns | 6h | [x] | dex-oracle-manipulation |
| 1.D.4 | Governance patterns | 4h | [x] | governance-flash-loan |
| 1.D.5 | msg.value patterns | 4h | [x] | msg-value-loop-reuse |
| 1.E.1 | Pattern testing | 8h | [x] | All patterns tested |
| 1.E.2 | DVDeFi validation | 4h | [x] | 11/13 (84.6%) |
| 1.E.3 | Regression tests | 4h | [x] | Added to CI |
| 1.F.1 | Phase 1 documentation | 2h | [x] | Complete |
| 1.F.2 | Lessons learned | 1h | [x] | Documented |

---

## Phase 2: Benchmark Infrastructure [CURRENT]

**Status:** IN PROGRESS (9/12 done)
**Tracker:** `phases/phase-2/TRACKER.md`

| ID | Task | Est. | Status | Notes |
|----|------|------|--------|-------|
| R2.1 | Benchmark approaches research | 2h | [x] | RESEARCH_NOTES.md |
| 2.1 | Define expected results | 4h | [x] | 13 DVDeFi YAMLs |
| 2.2 | Implement benchmark runner | 8h | [x] | src/true_vkg/benchmark/ |
| 2.3 | Baseline comparison | 4h | [x] | compare_results() |
| 2.4 | CI integration | 4h | [x] | benchmark.yml |
| 2.5 | Metrics dashboard | 4h | [ ] | SHOULD priority |
| 2.6 | Self-validation test | 4h | [x] | 9 tests passing |
| 2.7 | SmartBugs curated dataset | 8h | [ ] | MUST priority |
| 2.8 | Safe set for FP measurement | 6h | [ ] | MUST priority |
| 2.9 | Labeling protocol | 2h | [x] | LABELING.md |
| 2.10 | Analysis completeness report | 4h | [ ] | MUST priority |
| 2.11 | Multi-tier strategy | 2h | [x] | TIER_STRATEGY.md |
| 2.12 | Framework detection | 4h | [x] | framework.py, 12 tests |

---

## Phase 3: Basic CLI & Task System [COMPLETE]

**Status:** COMPLETE (17/17 tasks, 451 tests)
**Tracker:** `phases/phase-3/TRACKER.md`

| ID | Task | Est. | Status | Notes |
|----|------|------|--------|-------|
| R3.1 | Research LLM patterns | 3h | [x] | Best practices doc |
| R3.2 | Research OpenCode SDK | 2h | [x] | R3.2-OPENCODE-SDK-RESEARCH.md |
| R3.3 | Research Codex Noninteractive | 2h | [x] | R3.3-CODEX-NONINTERACTIVE-RESEARCH.md |
| 3.1 | AGENTS.md Generation | 4h | [x] | LLM discovery enabled |
| 3.1b | OpenCode Config Generation | 3h | [x] | 39 tests, `vkg init --opencode` |
| 3.2 | Findings Data Model | 4h | [x] | 51 tests |
| 3.3 | Findings CLI Commands | 6h | [x] | 28 tests |
| 3.4 | Priority Queue Logic | 3h | [x] | Included in 3.2/3.3 |
| 3.5 | Session Handoff | 4h | [x] | `vkg findings status` command |
| 3.6 | SARIF Report Output | 4h | [x] | SARIF 2.1.0 export |
| 3.7 | Error Message Quality | 3h | [x] | 21 tests, errors.py module |
| 3.8 | LLM Integration Test | 4h | [x] | 7 tests, < 15 tool calls |
| 3.8b | OpenCode Integration Test | 3h | [x] | 66 tests |
| 3.8c | Codex Noninteractive Test | 3h | [x] | 63 tests |
| 3.9-3.16 | Output Stability Tasks | 27h | [x] | Schema versioning, tier labels, locations, etc. |
| 3.17 | BSKG Output Schema for Codex | 3h | [x] | 58 tests, schemas/vkg-codex-output.json |

---

## Phase 4: Test Scaffolding [BLOCKED]

**Status:** BLOCKED (by Phase 3)
**Tracker:** `phases/phase-4/TRACKER.md`

| ID | Task | Est. | Status | Depends On |
|----|------|------|--------|------------|
| R4.1 | Test generation research | 2h | [-] | Phase 3 |
| 4.1 | Scaffold data model | 4h | [-] | R4.1 |
| 4.2 | Template engine | 6h | [-] | 4.1 |
| 4.3 | Foundry integration | 6h | [-] | 4.2 |
| 4.4 | Hardhat integration | 4h | [-] | 4.2 |
| 4.5 | scaffold command | 4h | [-] | 4.2 |
| 4.6 | Compile validation | 4h | [-] | 4.5 |
| 4.7 | Mock contract generation | 4h | [-] | 4.2 |
| 4.8 | Attack simulation stubs | 4h | [-] | 4.2 |
| 4.9 | Verification loop v1 | 6h | [-] | 4.6 |
| 4.10 | Verification loop v2 | 6h | [-] | 4.9 |
| 4.11 | Verification closure | 4h | [-] | 4.10 |
| 4.12 | Scaffold risk tags | 3h | [-] | 4.5 |

---

## Phase 5: Real-World Validation [BLOCKED]

**Status:** BLOCKED (by Phase 4)
**Tracker:** `phases/phase-5/TRACKER.md`

| ID | Task | Est. | Status | Depends On |
|----|------|------|--------|------------|
| R5.1 | Real-world corpus research | 4h | [-] | Phase 4 |
| 5.1 | Project selection (6+) | 4h | [-] | R5.1 |
| 5.2 | Ground truth labeling | 8h | [-] | 5.1 |
| 5.3 | Precision measurement | 6h | [-] | 5.2 |
| 5.4 | False positive analysis | 6h | [-] | 5.3 |
| 5.5 | Pattern refinement | 8h | [-] | 5.4 |
| 5.6 | Auditor feedback | 4h | [-] | 5.3 |
| 5.7 | Comparison baseline | 4h | [-] | 5.3 |
| 5.8 | Orchestrator mode (Slither/Aderyn) | 6h | [-] | 5.7 |
| 5.9 | 6-project validation report | 4h | [-] | 5.6 |
| 5.10 | Audit pack/diff commands | 4h | [-] | 5.8 |

---

## Phase 6: Beads System [BLOCKED]

**Status:** BLOCKED (by Phase 5)
**Tracker:** `phases/phase-6/TRACKER.md`

| ID | Task | Est. | Status | Depends On |
|----|------|------|--------|------------|
| R6.1 | Context richness research | 2h | [-] | Phase 5 |
| 6.1 | Bead data model | 6h | [-] | R6.1 |
| 6.2 | Bead persistence | 6h | [-] | 6.1 |
| 6.3 | Finding-Bead linking | 4h | [-] | 6.2 |
| 6.4 | Investigation context | 6h | [-] | 6.2 |
| 6.5 | Session management | 4h | [-] | 6.2 |
| 6.6 | bead command | 4h | [-] | 6.3 |
| 6.7 | Context export | 4h | [-] | 6.3 |
| 6.8 | LLM context formatting | 6h | [-] | 6.4 |
| 6.9 | Bead summarization | 4h | [-] | 6.4 |
| 6.10 | Cross-session persistence | 4h | [-] | 6.5 |
| P6.P.3 | Convoy data model | 3h | [-] | Philosophy gap - convoy |
| P6.P.4 | Convoy lifecycle manager | 4h | [-] | P6.P.3 |
| P6.P.5 | Convoy CLI commands | 2h | [-] | P6.P.4 |
| P6.P.6 | Hook data model | 3h | [-] | Philosophy gap - hooks |
| P6.P.7 | Hook priority ordering | 2h | [-] | P6.P.6 |
| P6.P.8 | Hook routing rules | 2h | [-] | P6.P.6, P6.P.7 |

---

## Phase 7: Conservative Learning [BLOCKED]

**Status:** BLOCKED (by Phase 5)
**Tracker:** `phases/phase-7/TRACKER.md`

| ID | Task | Est. | Status | Depends On |
|----|------|------|--------|------------|
| R7.1 | Learning approaches research | 4h | [-] | Phase 5 |
| 7.1 | Feedback data model | 4h | [-] | R7.1 |
| 7.2 | Confidence adjustment | 6h | [-] | 7.1 |
| 7.3 | Pattern weight updates | 6h | [-] | 7.2 |
| 7.4 | Rollback mechanism | 4h | [-] | 7.2 |
| 7.5 | A/B testing framework | 6h | [-] | 7.3 |
| 7.6 | Degradation detection | 4h | [-] | 7.3 |
| 7.7 | Learn toggle (off by default) | 2h | [-] | 7.4 |
| 7.8 | Learning metrics | 4h | [-] | 7.5 |

---

## Phase 8: Metrics & Observability [BLOCKED]

**Status:** BLOCKED (by Phase 5)
**Tracker:** `phases/phase-8/TRACKER.md`

| ID | Task | Est. | Status | Depends On |
|----|------|------|--------|------------|
| R8.1 | Observability research | 2h | [-] | Phase 5 |
| 8.1 | Metrics collection framework | 6h | [-] | R8.1 |
| 8.2 | Usage metrics | 4h | [-] | 8.1 |
| 8.3 | Performance metrics | 4h | [-] | 8.1 |
| 8.4 | Detection metrics | 4h | [-] | 8.1 |
| 8.5 | Metrics export (Prometheus) | 4h | [-] | 8.1 |
| 8.6 | Metrics dashboard | 6h | [-] | 8.5 |
| 8.7 | Alert thresholds | 4h | [-] | 8.4 |
| 8.8 | Performance budgets | 4h | [-] | 8.3 |
| 8.9 | Performance baselines | 4h | [-] | 8.8 |
| 8.10 | Budget enforcement | 4h | [-] | 8.9 |

---

## Phase 9: Context Optimization (PPR) [BLOCKED]

**Status:** BLOCKED (by Phases 6, 7, 8)
**Tracker:** `phases/phase-9/TRACKER.md`

| ID | Task | Est. | Status | Depends On |
|----|------|------|--------|------------|
| R9.1 | PPR research | 4h | [-] | Phases 6,7,8 |
| 9.1 | Context compressor | 8h | [-] | R9.1 |
| 9.2 | Token budgeting | 4h | [-] | 9.1 |
| 9.3 | Priority ranking | 4h | [-] | 9.1 |
| 9.4 | Relevance scoring | 6h | [-] | 9.1 |
| 9.5 | Context caching | 4h | [-] | 9.1 |
| 9.6 | Multi-model support | 6h | [-] | 9.2 |
| 9.7 | Context metrics | 4h | [-] | 9.1 |
| 9.8 | TOON format for LLM output | 4h | [-] | 9.1 |

---

## Phase 10: Graceful Degradation [BLOCKED]

**Status:** BLOCKED (by Phase 9)
**Tracker:** `phases/phase-10/TRACKER.md`

| ID | Task | Est. | Status | Depends On |
|----|------|------|--------|------------|
| R10.1 | Degradation strategies research | 2h | [-] | Phase 9 |
| 10.1 | Offline mode detection | 4h | [-] | R10.1 |
| 10.2 | Fallback hierarchy | 6h | [-] | 10.1 |
| 10.3 | Local-only mode | 6h | [-] | 10.1 |
| 10.4 | Cached model responses | 4h | [-] | 10.2 |
| 10.5 | Tier degradation | 4h | [-] | 10.2 |
| 10.6 | User notification | 2h | [-] | 10.2 |
| 10.7 | Recovery detection | 4h | [-] | 10.1 |
| 10.8 | Degradation metrics | 4h | [-] | 10.5 |

---

## Phase 11: LLM Integration (Tier B) [BLOCKED]

**Status:** BLOCKED (by Phase 10)
**Tracker:** `phases/phase-11/TRACKER.md`

| ID | Task | Est. | Status | Depends On |
|----|------|------|--------|------------|
| R11.1 | LLM integration research | 4h | [-] | Phase 10 |
| 11.1 | LLM provider abstraction | 6h | [-] | R11.1 |
| 11.2 | Tier B pipeline | 8h | [-] | 11.1 |
| 11.3 | Finding verification | 6h | [-] | 11.2 |
| 11.4 | False positive filtering | 6h | [-] | 11.3 |
| 11.5 | Context enrichment | 4h | [-] | 11.2 |
| 11.6 | Confidence adjustment | 4h | [-] | 11.3 |
| 11.7 | LLM safety guardrails | 4h | [-] | 11.1 |
| 11.8 | Prompt contract + schema | 6h | [-] | 11.2 |
| 11.9 | Cost tracking | 4h | [-] | 11.1 |
| 11.10 | Rate limiting | 3h | [-] | 11.1 |
| 11.11 | Tier B metrics | 4h | [-] | 11.4 |
| 11.12 | Multi-tier model support | 6h | [-] | 11.1 |

---

## Phase 12: Agent SDK Micro-Agents [BLOCKED]

**Status:** BLOCKED (by Phase 10)
**Tracker:** `phases/phase-12/TRACKER.md`

| ID | Task | Est. | Status | Depends On |
|----|------|------|--------|------------|
| R12.1 | Agent SDK research | 4h | [-] | Phase 10 |
| 12.1 | Agent base class | 6h | [-] | R12.1 |
| 12.2 | Explorer agent | 6h | [-] | 12.1 |
| 12.3 | Pattern agent | 6h | [-] | 12.1 |
| 12.4 | Constraint agent | 6h | [-] | 12.1 |
| 12.5 | Risk agent | 6h | [-] | 12.1 |
| 12.6 | Agent orchestration | 6h | [-] | 12.2,12.3,12.4,12.5 |
| 12.7 | Consensus mechanism | 6h | [-] | 12.6 |
| 12.8 | Subagent orchestration manager | 6h | [-] | 12.6 |
| 12.9 | Agent metrics | 4h | [-] | 12.7 |
| P12.P.3 | Propulsion behavior implementation | 3h | [-] | Philosophy gap - propulsion |
| P12.P.4 | Escalation trigger specification | 2h | [-] | P11.P.1 |
| P12.P.5 | Triage Analyst role definition | 2h | [-] | P12.P.1 |
| P12.P.6 | Evidence Curator role definition | 2h | [-] | P12.P.1 |
| P12.P.7 | Defender role enhancement | 2h | [-] | P12.P.1 |

---

## Phase 13: Grimoires & Skills [BLOCKED]

**Status:** BLOCKED (by Phase 10)
**Tracker:** `phases/phase-13/TRACKER.md`

| ID | Task | Est. | Status | Depends On |
|----|------|------|--------|------------|
| R13.1 | Grimoire design research | 4h | [-] | Phase 10 |
| 13.1 | Grimoire data model | 4h | [-] | R13.1 |
| 13.2 | Reentrancy grimoire | 6h | [-] | 13.1 |
| 13.3 | Access control grimoire | 6h | [-] | 13.1 |
| 13.4 | Oracle manipulation grimoire | 6h | [-] | 13.1 |
| 13.5 | MEV grimoire | 6h | [-] | 13.1 |
| 13.6 | Skill definitions | 4h | [-] | 13.1 |
| 13.7 | AGENTS.md generation | 2h | [-] | 13.6 |
| 13.8 | Grimoire versioning | 4h | [-] | 13.1 |
| 13.9 | Custom grimoire support | 4h | [-] | 13.1 |

---

## Phase 14: Confidence Calibration [BLOCKED]

**Status:** BLOCKED (by Phases 11, 12, 13)
**Tracker:** `phases/phase-14/TRACKER.md`

| ID | Task | Est. | Status | Depends On |
|----|------|------|--------|------------|
| R14.1 | Calibration techniques research | 4h | [-] | Phases 11,12,13 |
| 14.1 | Ground truth collection | 6h | [-] | R14.1 |
| 14.2 | Calibration model | 8h | [-] | 14.1 |
| 14.3 | Per-pattern calibration | 6h | [-] | 14.2 |
| 14.4 | Context factor integration | 6h | [-] | 14.2 |
| 14.5 | Calibration plot | 3h | [-] | 14.2,14.4 |
| 14.6 | Confidence explanation | 4h | [-] | 14.5 |
| 14.7 | Calibration validation | 6h | [-] | 14.3,14.6 |

---

## Phase 15: Novel Solutions Integration [BLOCKED]

**Status:** BLOCKED (by Phase 14)
**Tracker:** `phases/phase-15/TRACKER.md`

| ID | Task | Est. | Status | Depends On |
|----|------|------|--------|------------|
| 15.1 | Evaluation framework | 4h | [-] | Phase 14 |
| 15.2 | Evaluate: Self-Evolving Patterns | 6h | [-] | 15.1 |
| 15.3 | Evaluate: Adversarial Test Gen | 6h | [-] | 15.1 |
| 15.4 | Evaluate: Semantic Similarity | 6h | [-] | 15.1 |
| 15.5 | Evaluate: Formal Invariants | 6h | [-] | 15.1 |
| 15.6 | Integration decision | 4h | [-] | 15.2-15.5 |
| 15.7 | Integration of selected | Varies | [-] | 15.6 |

---

## Phase 16: Release & Distribution [BLOCKED]

**Status:** BLOCKED (by Phase 15)
**Tracker:** `phases/phase-16/TRACKER.md`

| ID | Task | Est. | Status | Depends On |
|----|------|------|--------|------------|
| 16.1 | Documentation complete | 12h | [-] | Phase 15 |
| 16.2 | Getting started guide | 4h | [-] | 16.1 |
| 16.3 | API finalization | 6h | [-] | - |
| 16.4 | PyPI package | 4h | [-] | 16.3 |
| 16.5 | Docker image | 4h | [-] | 16.4 |
| 16.6 | GitHub release | 2h | [-] | 16.4,16.5 |
| 16.7 | GitHub marketplace | 4h | [-] | 16.6 |
| 16.8 | Pre-release checklist | 4h | [-] | 16.4,16.5,16.6 |
| 16.9 | Fresh install test | 2h | [-] | 16.8 |
| 16.10 | Pattern pack versioning | 4h | [-] | - |
| 16.11 | CODEOWNERS definition | 1h | [-] | - |

---

## Phase 17: VulnDocs Knowledge System [TODO]

**Status:** TODO
**Tracker:** `phases/phase-17/TRACKER.md`

---

## Phase 18: VulnDocs Knowledge Mining & Retrieval [IN PROGRESS]

**Status:** IN PROGRESS
**Tracker:** `phases/phase-18/TRACKER.md`

---

## Phase 19: Semantic Labeling for Complex Logic Detection [TODO]

**Status:** TODO
**Tracker:** `phases/phase-19/TRACKER.md`
**Master Plan:** `task/4.0/phases/phase-19/INDEX.md`

---

## Phase 20: Final Testing Phase [TODO]

**Status:** TODO (Final gate after Phases 1-19)
**Tracker:** `phases/phase-20/TRACKER.md`
**Master Plan:** `task/4.0/phases/phase-20/INDEX.md`

---

## Cross-Phase Artifacts

### Artifacts Produced by Each Phase

| Phase | Key Artifacts | Used By |
|-------|--------------|---------|
| 1 | Detection baseline (84.6%), new patterns | 2, 5, 14 |
| 2 | Benchmark infrastructure, DVDeFi YAMLs | 3, 4, 5 |
| 3 | CLI commands, SARIF output | 4, 5, 6 |
| 4 | Test scaffolding, verification loop | 5, 11 |
| 5 | Real-world validation baseline | 6, 7, 8 |
| 6 | Beads context system | 9, 11 |
| 7 | Learning infrastructure | 9, 14 |
| 8 | Metrics framework | 9, 11, 14 |
| 9 | Context optimization (PPR), TOON | 10, 11 |
| 10 | Graceful degradation | 11, 12, 13 |
| 11 | Tier B verification, LLM findings | 14 |
| 12 | Micro-agents | 14 |
| 13 | Grimoires, skills | 14 |
| 14 | Calibrated confidence | 15, 16 |
| 15 | Integrated novel solutions | 16 |
| 16 | Release artifacts | - |
| 17 | VulnDocs knowledge hierarchy | 18, 20 |
| 18 | VulnDocs mining + retrieval | 20 |
| 19 | Semantic labeling overlays + label-aware patterns | 20 |
| 20 | Final testing readiness dossier | - |

---

## Blocking Relationships

### Critical Path

The longest dependency chain (critical path):

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 9 → Phase 10 → Phase 11 → Phase 14 → Phase 15 → Phase 16
```

**Total Critical Path Length:** 12 phases

### Parallelization Opportunities

| After Phase | Can Run in Parallel |
|-------------|---------------------|
| Phase 5 | Phases 6, 7, 8 |
| Phase 10 | Phases 11, 12, 13 |

---

## Change Log

| Date | Author | Changes |
|------|--------|---------|
| 2026-01-07 | BSKG Team | Initial INDEX.md creation |
| 2026-01-08 | BSKG Team | Added Phases 17-19 and Phase 19 master plan reference |
| 2026-01-08 | BSKG Team | Added 15 philosophy gap alignment tasks (P0.P.6-P0.P.8, P6.P.3-P6.P.8, P12.P.3-P12.P.7) |
| 2026-01-09 | BSKG Team | Added Phase 20 planning and tracking references |
| 2026-01-09 | BSKG Team | Renumbered Phase 20 to Phase 19; Phase 19 renamed to Final Testing Phase (Phase 20) |

---

*INDEX.md | Version 1.0 | 2026-01-07*
*Based on PHASE_TEMPLATE.md v2.0*
