# Requirements: AlphaSwarm.sol Milestone 6.0

**Defined:** 2026-02-08
**Updated:** 2026-02-09
**Core Value:** Prove every capability works on real contracts before claiming it exists

## v6.0 Requirements Summary

| Category | Requirements | Status | Phase | Execution Order |
|----------|-------------|--------|-------|-----------------|
| FIX | P0 Bug Fixes | ✅ 6/6 | 1 | done |
| PROP | Property Gap Resolution | ✅ 4/4 | 2 | done |
| E2E | End-to-End Pipeline | ⏳ 0/5 | 3 | after 3.1 |
| EVAL | Reasoning-Based Evaluation | ⏳ 7/12 | 3.1c | after 3.1b |
| AGENT | Agent Teams Debate | ⏳ 0/6 | 4 | after E2E |
| TEST | Test Framework | ⏳ 0/5 | 6 | after AGENT |
| DOCS | Documentation + Hooks | ⏳ 0/5 | 7 | after TEST |
| BENCH | Benchmark Reality | ⏳ 0/6 | 5 | after DOCS |
| SHIP | Ship What Works | ⏳ 0/5 | 8 | final |

**Total:** 17/54 requirements complete (31%)

---

## Cross-Phase Planning Governance Requirements

These requirements apply to every active phase plan and are enforced during `/gsd-plan-phase`:

- [ ] GOV-01: Every plan has derived checks generated from evidence (no static outcome hardcoding).
- [ ] GOV-02: Every plan has explicit preconditions resolved or risk-accepted with evidence.
- [ ] GOV-03: Every plan has a runnable HITL runbook (commands, expected signals, failure signatures, time budget).
- [ ] GOV-04: Every `major`/`critical` drift event has RCA with standardized cause codes.
- [ ] GOV-05: Required gate tests are not skip/xfail/placeholders.
- [ ] GOV-06: Plan-vs-reality dashboard is regenerated before any phase completion update.
- [ ] GOV-07: Phase entry and exit checklists are completed and recorded in `STATE.md`.

Governance references:
- `.planning/testing/PLAN-PHASE-GOVERNANCE.md`
- `.planning/testing/schemas/phase_plan_contract.schema.json`
- `.planning/testing/templates/PHASE-GATE-CHECKLIST-TEMPLATE.md`

---

## Completed Categories

### P0 Bug Fixes (FIX) — ✅ COMPLETE
*Phase 1 | Done*

- [x] FIX-01: PatternEngine API has `pattern_dir`, `run_all_patterns`, `run_pattern` methods
- [x] FIX-02: `orchestrate resume` advances state (no infinite loop)
- [x] FIX-03: All skills have correct frontmatter (`name:` not `skill:`)
- [x] FIX-04: VulnDocs validation passes for all entries
- [x] FIX-05: `--scope` flag works on `orchestrate start`
- [x] FIX-06: No deprecated google.generativeai warnings

### Property Gap Resolution (PROP) — ✅ COMPLETE
*Phase 2 | Done*

- [x] PROP-01: 37 computed-but-not-emitted properties now emitted
- [x] PROP-02: Top-10 trivial orphan properties implemented
- [x] PROP-03: Property validation CI gate active
- [x] PROP-04: Dead patterns triaged (169 deleted, 141 quarantined, ~290 working)

---

## Active Categories

### End-to-End Pipeline (E2E)
*Phase 3*

- [ ] E2E-01: All 12 integration break points fixed and tested
- [ ] E2E-02: Handler API mismatches resolved (DetectPatterns, CreateBeads, SpawnAttackers)
- [ ] E2E-03: MVP pipeline runs on DVDeFi Challenge #1 with finding produced
- [ ] E2E-04: Full pipeline transcript captured showing all 9 stages and required orchestration markers
- [ ] E2E-05: Deterministic replay + negative-control gate passes (same input reproduces evidence; safe contract has no high-confidence false positives)

**Exit criteria:** One DVDeFi challenge produces a finding with code location and graph evidence, required markers are present, deterministic replay passes, and safe negative control passes.

### Reasoning-Based Evaluation (EVAL)
*Phase 3.1c*

- [x] EVAL-01: Hook-based observability writes observation JSONL when enabled by evaluation contract (selective per test, not always-on)
- [x] EVAL-02: Interactive agent debrief via SendMessage captures reasoning from teammates before shutdown
- [x] EVAL-03: LLM Reasoning Evaluator produces ReasoningAssessment with scored dimensions per run
- [x] EVAL-04: Graph Value Score computed mechanically from observation logs for investigation workflows
- [ ] EVAL-05: 24 per-workflow evaluation contracts define what "good" looks like with smart selection
- [x] EVAL-06: Safe sandboxing: prompt experiments use test project copies, never modify production prompts
- [ ] EVAL-07: Regression detection compares before/after scores; hard regression (> 0.2 drop) triggers revert
- [ ] EVAL-08: Improvement loop generates suggestions, safely tests them, reports to human
- [x] EVAL-09: Metaprompting feedback: live hook nudges during runs + offline improvement aggregation
- [x] EVAL-10: Blocking debrief enforcement: SubagentStop hook blocks until debrief responses found
- [ ] EVAL-11: All 30 shipped skills tested with capability contracts (HDG-10) AND reasoning evaluation via full pipeline
- [ ] EVAL-12: All 21 shipped agents tested with behavioral contracts AND reasoning evaluation via full pipeline

**Exit criteria:** All 24 shipped workflows have evaluation contracts. Hook observability is selective per evaluation contract. Reasoning evaluator identifies what broke and where (internal regression signals, not product quality metrics) on investigation and orchestration workflows. All 30 skills and 21 agents pass capability + reasoning evaluation. Improvement loop demonstrates at least one successful prompt improvement with regression detection.

### Agent Teams Debate (AGENT)
*Phase 4*

- [ ] AGENT-01: Agent Teams enabled in settings
- [ ] AGENT-02: `/vrs-team-verify` skill creates team with attacker/defender/verifier
- [ ] AGENT-03: Agent `.md` files have correct tool permissions (`Bash(uv run alphaswarm*)`)
- [ ] AGENT-04: Hooks enforce graph-first reasoning and evidence completeness
- [ ] AGENT-05: 3 debates completed on known-vulnerable contracts with real LLM responses
- [ ] AGENT-06: Debate-path workflow/agent/skill coverage matrix is complete with live test transcripts

**Exit criteria:** 3 real debates with evidence-anchored verdicts. Agents proven to use graph. Every workflow/agent/skill in the debate path has live-test evidence.

### Benchmark Reality (BENCH)
*Phase 5*

- [ ] BENCH-01: Negative-control safe-set gate and deterministic scorer gate pass before benchmark scaling
- [ ] BENCH-02: DVDeFi ground truth entries replaced (no more TODO placeholders)
- [ ] BENCH-03: DVDeFi full run + SmartBugs subset evaluated with explicit exclusions and compile tracking
- [ ] BENCH-04: Head-to-head comparison vs Slither published with identical scorer
- [ ] BENCH-05: BSKG ablation study (with graph vs without graph on identical corpus/tool/scorer setup)
- [ ] BENCH-06: Results published in `benchmarks/RESULTS.md` with artifact-only scoring and repeatability (`pass^k`) reporting

**Exit criteria:** Reproducible artifact-derived metrics. False-positive metrics and repeatability are reported. Ablation study answers "does the graph help?"

### Test Framework (TEST)
*Phase 6*

- [ ] TEST-01: 20 detection regression tests (contract → finding) passing
- [ ] TEST-02: 5 E2E pipeline integration tests passing
- [ ] TEST-03: Existing test audit complete (50 file sample classified) + workflow/agent/skill live-coverage map complete
- [ ] TEST-04: Top 20 mock-heavy test offenders rewritten
- [ ] TEST-05: Graph cache operational for test speed and reproducible failure artifact output (`.vrs/debug/phase-6/repro.json`)

**Exit criteria:** Detection regression tests pass. Workflow/agent/skill live coverage is complete. Mock ratio below 40%.

### Documentation + Hooks (DOCS)
*Phase 7*

- [ ] DOCS-01: Hook test harness and fail-closed policy tests implemented
- [ ] DOCS-02: docs/ updated — working vs planned features clearly separated with artifact links
- [ ] DOCS-03: 5 hook configurations implemented and active (graph-first/evidence-first hard fail)
- [ ] DOCS-04: Aspirational YAML configs removed, JSON consolidated, marker chain checks enforced
- [ ] DOCS-05: Skill/docs honesty audit complete (no unsupported claims)

**Exit criteria:** No unsupported claims in any documentation. Hooks and evidence schema gates are active and benchmark-blocking.

### Ship What Works (SHIP)
*Phase 8*

- [ ] SHIP-01: All functional skills installed and invocable
- [ ] SHIP-02: Legacy `vkg-*` skills cleaned up to `vrs-*`
- [ ] SHIP-03: Demo recorded: `/vrs-audit` on DVDeFi with output
- [ ] SHIP-04: README reflects real capabilities and limitations
- [ ] SHIP-05: GA readiness dossier with gate-by-gate evidence IDs (G0-G7 + marker coverage) complete

**Exit criteria:** New user runs `/vrs-audit contracts/` and gets a real vulnerability report.

## Execution Dependency Gates

Execution order for active work is fixed:
`3.1 -> 3.1b -> 3.1c -> 3.2 -> 4 -> 4.1 -> 6 -> 7 -> 5 -> 8`

Hard dependencies:
- `3.1b` depends on 3.1 cleanup/enforcement baseline.
- `3.1c` depends on 3.1b harness infrastructure (transcript parser, assertions, hooks).
- `3.2` depends on 3.1 marker/proof-token enforcement gate + 3.1b harness baseline + 3.1c evaluation contracts.
- `4` depends on 3.2 deterministic replay + negative-control gate.
- `4.1` depends on 4 debate-path workflow integration.
- `6` depends on 4.1 expanded workflow validation coverage.
- `7` depends on 6 live harness coverage.
- `5` depends on 6 harness and 7 hook/schema enforcement.
- `8` depends on all prior gates and published artifact-backed results.

---

## Out of Scope (v6.1+)

| Feature | Reason |
|---------|--------|
| Pool batching | Fix E2E first, then batch |
| Autonomous work-pulling | Prove basic orchestration first |
| Multi-SDK parallel execution | Single provider sufficient for proving value |
| Cross-project label persistence | Scoped analysis safer |
| Self-improving iteration loop | Prove debate works first |
| Continuous validation pipeline | Manual validation first, automate later |

---

## Traceability

| Phase | Requirements | Status |
|-------|-------------|--------|
| 1 | FIX-01 to FIX-06 | ✅ |
| 2 | PROP-01 to PROP-04 | ✅ |
| 3 | E2E-01 to E2E-05 | ⏳ |
| 3.1c | EVAL-01 to EVAL-12 | ⏳ |
| 4 | AGENT-01 to AGENT-06 | ⏳ |
| 5 | BENCH-01 to BENCH-06 | ⏳ |
| 6 | TEST-01 to TEST-05 | ⏳ |
| 7 | DOCS-01 to DOCS-05 | ⏳ |
| 8 | SHIP-01 to SHIP-05 | ⏳ |

### Execution Traceability (Quality-First Ordering)

| Execution Step | Phase | Requirement Group |
|----------------|-------|-------------------|
| 1 | 3.1 | E2E prerequisites (enforcement baseline) |
| 2 | 3.1b | Workflow harness + corpus prerequisites |
| 2.5 | 3.1c | EVAL-01 to EVAL-12 (includes skill/agent/orchestrator capability + reasoning tests) |
| 3 | 3.2 | E2E-01 to E2E-05 |
| 4 | 4 | AGENT-01 to AGENT-06 |
| 5 | 4.1 | Deep workflow test expansion |
| 6 | 6 | TEST-01 to TEST-05 |
| 7 | 7 | DOCS-01 to DOCS-05 |
| 8 | 5 | BENCH-01 to BENCH-06 |
| 9 | 8 | SHIP-01 to SHIP-05 |

---
*Requirements defined: 2026-02-08*
*Source: MILESTONE-6.0-ROADMAP.md success criteria + v5.0 closure analysis*
