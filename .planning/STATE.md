---
gsd_state_version: 1.0
milestone: v5.0
milestone_name: milestone
current_phase: 3.1c.3 — Evaluation Intelligence Bootstrap
status: executing
stopped_at: "Phase 3.1c.3: improvement pass 1 complete. 37 items (17 confirmed, 11 enhanced, 1 reframed, 1 created, 3 SYN, 4 CSC). 7 prerequisites, 2 research items. Convergence: 0% cosmetic — ACTIVE. Next: /msd:resolve-blockers 3.1c.3"
last_updated: "2026-04-17T00:00:00.000Z"
progress:
  total_phases: 22
  completed_phases: 4
  total_plans: 48
  completed_plans: 42
---

# State: AlphaSwarm.sol Milestone 6.0

**Last Updated:** 2026-04-17
**Current Phase:** 3.1c.3 — Evaluation Intelligence Bootstrap
**Profile:** quality

---

## Executive Summary

AlphaSwarm.sol is transitioning from theoretical infrastructure (v5.0) to proven functionality (v6.0). The BSKG builder works, ~290 patterns are active, P0 bugs are fixed, and the property gap is resolved. The next critical milestone is proving ONE complete audit works end-to-end.

**Status:** 65/111 plans complete (59%) — Phases 1, 1.1, 2, 2.1, 3.1, 3.1.1, 3.1b, 3.1c.1, 3.1c.2, 3.1d, 3.1e DONE. Phase 3.1c IN PROGRESS (Plans 01-09 complete, 3 remaining). Phase 3.1c.3 (12 plans) NEXT, then 3.1f (3).
**Philosophy:** Nothing ships until proven. Prove everything. Ship only what works.
**Cost Model:** $0 — All testing via Claude Code CLI subscription

**Note:** v5.0 phases (1-9) are archived in `.planning/phases/v5.0-archive/`. v6.0 renumbers phases 10-17 → 1-8 for clarity.

---

## Global Planning Policy

- Every feature must be proven on real contracts before claiming it exists
- No mock-only testing — detection tests use real Solidity contracts
- No aspirational documentation — only document what works
- Agent Teams for orchestration
- Graph-first enforcement via hooks

---

## Phase Status

| Execution Order | Phase | Name | Status | Plans |
|-----------------|-------|------|--------|-------|
| done | 1 | Emergency Triage (P0 Fixes) | ✅ COMPLETE | DONE |
| done | 1.1 | Critical Review: P0 Fixes | ✅ COMPLETE (B) | 5/5 |
| done | 2 | Property Gap Quick Wins | ✅ COMPLETE | DONE |
| done | 2.1 | Critical Review: Property Gap | ✅ COMPLETE (B+) | 5/5 |
| done | 3.1 | Testing Audit & Cleanup | ✅ COMPLETE | 7/7 |
| done | 3.1.1 | Pattern Loading Architecture Fix | ✅ COMPLETE | 4/4 |
| done | 3.1b | Workflow Testing Harness & Test Corpus | ✅ COMPLETE | 8/9 |
| now | **3.1c** | **Reasoning-Based Evaluation Framework** | **⏳ IN PROGRESS** | 9/12 (Plans 01-09 complete) |
| done | 3.1c.1 | CLI & Graph Isolation Hardening | ✅ COMPLETE | 6/6 |
| now | **3.1c.2** | **Agent Evaluation Harness Hardening** | **⏳ IN PROGRESS** | 2/5 (Plans 01,03 complete) |
| done | 3.1d | Detection-Evaluation Feedback Bridge | ✅ COMPLETE | 8/8 |
| done | 3.1e | Evaluation Zero — Empirical Sprint | ✅ COMPLETE | 5/5 |
| next | 3.1f | Proven Loop Closure | ⏳ PLANNED | 0/3 |
| next | **3.2** | **First Working Audit** | **⏳ PLANNED** | 0/5 |
| next | 4 | Agent Teams Debate | ⏳ PLANNED | 0/6 |
| next | 4.1 | Workflow Test Expansion | ⏳ PLANNED | 0/4 |
| next | 6 | Test Framework Overhaul | ⏳ PLANNED | 0/5 |
| next | 7 | Documentation Honesty + Hooks | ⏳ PLANNED | 0/5 |
| next | 5 | Benchmark Reality | ⏳ PLANNED | 0/6 |
| next | 8 | Ship What Works | ⏳ PLANNED | 0/5 |

**Phase 3.1b → 3.1c readiness:** Phase 3.1b delivers infrastructure only (9 plans), preserving existing harness (3,745 LOC) as foundation. Phase 3.1c IS the testing framework (12 plans) — tests all skills, agents, orchestrator WITH evaluation. API contracts: TranscriptParser extensions (timestamp, duration_ms, BSKGQuery, TeamObservation, 3 new methods), OutputCollector (collect + summary), EvaluationGuidance (per-scenario reasoning questions), hook registration (N hooks), `.vrs/observations/` paths, scenario DSL `evaluation:`/`evaluation_guidance:` blocks, SendMessage content capture via TeamManager, debrief research findings, sandbox `.claude/` copying, Jujutsu workspace isolation (create/forget/rollback, multiple workspaces per scenario), corpus generation system (guidelines catalog + Opus-powered subagent + 15-20 committed seed projects with 5-10 vulns each). 3.1c API contract design review (plan 3.1b-08) front-loaded as Wave 0 to prevent backtracking.

**Phase 3.1c docs unified (2026-02-12):** All 27 improvement concepts from Passes 1-3 merged into PHILOSOPHY.md and context.md as native design. IMPROVEMENTS.md deleted. Evaluation Intelligence Layer (10 sub-modules) fully documented. Sequential execution constraint established.

**Phase 3.1c docs extended (2026-02-12):** 8 additional research-backed improvements integrated as native design. Intelligence layer expanded to 12 sub-modules (+adversarial_auditor, +counterfactual_replayer). New Rules N-O, North Star conditions 13-15, 22 anti-patterns. Research completed on: cascade-aware scoring (PRISM-Physics/ICLR 2026), Goodhart's Law mitigation (EST framework), trajectory replay (DoVer/ICLR 2026). Research artifacts at `.planning/research/`. Scope updated: ~35 model types, ~110 files, ~10500 LOC, 23 exit gates. Docs ready for `/gsd:plan-phase 3.1c`.

**Phase 3.1c readiness backlog hardened (2026-02-12):** Replaced `.planning/phases/3.1c-reasoning-evaluation-framework/PENDING-IMPROVEMENTS.md` with an execution-grade 3.1b->3.1c bridge backlog: validated baseline, explicit Definition of Ready, P0/P1/P2 workstreams, creative R&D tracks, dependency waves, and required tracking artifacts (`gates/`, `hitl/`, drift log). This converts pending work from a short checklist into a plan-ready implementation contract.

**Phase 3.1c prestep plan added (2026-02-12):** Created `.planning/phases/3.1c-reasoning-evaluation-framework/3.1c-00-PRESTEPS-PLAN.md` as a hard-gated prestep-only plan. It blocks all 3.1c execution plans until readiness artifacts and no-go checks pass, and sets scripted session policy to 3.1b CLI path (`ClaudeCodeRunner` / `claude --print`) instead of clauty dependency.

**Phase 3.1c evidence hardening pass (2026-02-12):** Updated 3.1c prestep planning to be explicitly non-theoretical: added approach-validation requirements, philosophy-alignment artifacts, pilot+kill-criterion rules for research-backed upgrades, and a stricter prestep boundary that defers runtime implementation to `3.1c-01..12`.

**Phase 3.1c interactive-alignment pass (2026-02-12):** Strengthened planning alignment with phase philosophy and product reality: interactive Claude Code Agent Teams are now explicit primary realism path, scripted CLI runs are secondary reproducibility path, and prestep artifacts now require an attacker/defender/verifier pilot contract plus evidence schema for teammate message/debrief validation.

**Phase 3.1c intent-lock pass (2026-02-13):** Hardened prestep docs to protect the novel phase intent before implementation: added intent-lock contracts for adaptive intelligence (tier/depth dynamics), self-debug loops (failure narrative + intervention/replay protocol), composition stress/keystone analysis, and explicit doc-drift authority mapping. Clarified that 3.1b remains aligned with 3.1c and is the required substrate; drift handling applies to peripheral stale docs only.

**Totals (honest, updated after Phase 2.1 triage):**
- Production Code: ~260,000 LOC across 475 Python files
- Working Patterns: 466 active (39 archived, 57 quarantined, down from 562 total)
- Orphan Properties: 147 (down from 223 pre-triage)
- Tests: 245 files, 11,282 tests (most mock-heavy, overhaul in Phase 6)
- VulnDocs: 466 active patterns, 18 categories, 106 index entries (89 valid, 17 failing)

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-08)

**Core value:** Prove every capability on real contracts before claiming it
**Current focus:** Phase 3.1c — Reasoning-Based Evaluation Framework (PARTIAL — needs real LLM evaluation implementation)

**Execution sequence:** `3.1 -> 3.1b -> 3.1c (partial) -> 3.1d ✅ -> **3.1e** -> 3.1c (resumes) -> **3.1f** -> 3.2 -> 4 -> 4.1 -> 6 -> 7 -> 5 -> 8`

---

## Current Position

### Phase 3.1: Testing Audit & Cleanup

**Status:** ✅ COMPLETE (2026-02-11) — Clean foundations achieved, 3.1b and 3.2 unblocked
**Goal:** Remove dead testing infrastructure, eliminate legacy dependencies, enforce testing rules, and prepare the infrastructure foundation for Phase 3.1c's evaluation framework.

**Plans (7):**
1. Delete dead testing code (~3-6K LOC across 48 files, 8 directories; verify via import graph first)
2. Remove legacy testing infrastructure (files, skills, agents, configs)
3. Shipping manifest + infrastructure audit for 3.1c (MANIFEST.yaml, evaluator audit, harness audit, sample contracts)
4. Update testing rules for Agent Teams (rewrite RULES-ESSENTIAL.md, VALIDATION-RULES.md, stable rule IDs for 3.1c-06)
5. Evaluation contract foundation + assertion integration (schema, 3 samples, workflow_harness extensions)
6. Clean up test files for removed infrastructure
7. Verify clean state (7 checks: grep, pytest, build-kg, dead code, manifest, eval contracts, assertion integration)

**Skills reorganization (2026-02-09):**
- Promoted `vrs-tool-mythril` and `vrs-tool-coordinator` to shipping (30 shipped skills total)
- Deleted 20 non-functional legacy test skills from `.claude/skills-testing/`
- Created 4 replacement test skills: `vrs-test-workflow`, `vrs-test-e2e`, `vrs-test-component`, `vrs-test-enforce`
- Fixed frontmatter in all 13 VRS dev skills (model_tier normalization: opus-4.5→opus, sonnet-4→sonnet, etc.)

**Terminology cleanup (2026-02-09):**
- Replaced remaining legacy execution terminology repository-wide with Agent Teams + `claude-code-controller` terminology
- Verification gate: repository-wide legacy-token sweep returns zero matches

**Exit gate:** Zero legacy infrastructure refs in production. Dead code removed. Shipping manifest exists. Evaluation contract schema defined with 3 samples. Rules rewritten with stable IDs. Evaluators audited for 3.1c.

**Context:** `.planning/phases/3.1-testing-audit-cleanup/context.md`

**Documentation alignment sweep (2026-02-10):**
- Migrated canonical docs to Claude Code workflow-first execution model with Claude Code as orchestrator and CLI as subordinate tool surface.
- Added `docs/claude-code-architecture.md` as canonical architecture/API/workflow reference and `docs/migrations/claude-code-workflow-migration.md` as migration/changelog for integrators.
- Removed stale repository-wide terminology (`skills/shipped`, `/vrs-resume`, `pattern-tester`, `50+ properties`) across docs, scripts, tests, fixtures, and VulnDocs metadata comments.

**Phase 3 integrity review pass (2026-02-10):**
- Completed full context review of 3.1, 3.1b, and 3.2 with strict gate/human-checkpoint alignment.
- Added cross-phase planning governance for `/gsd-plan-phase`:
  - `.planning/testing/PLAN-PHASE-GOVERNANCE.md`
  - `.planning/testing/schemas/phase_plan_contract.schema.json`
  - templates for derived checks, HITL runbooks, drift RCA, and phase entry/exit checklists
- Added machine dashboard generator: `scripts/planning/render_phase_plan_dashboard.py`
- Added missing strict-governance sections in `.planning/phases/3.2-first-working-audit/context.md`:
  - Phase-wide machine gate + HITL + drift-log contract
  - Repeatable HITL scenarios for plans 3.2-01..3.2-05
- Added missing rigor in `.planning/phases/3.1b-workflow-testing-harness/context.md`:
  - `3.1b-03`: explicit drift-detection controls
  - `3.1b-04`: explicit testing strategy + drift-detection controls
- Reality check vs plan (implementation gap snapshot):
  - `examples/testing/` exists but currently has 11 project dirs (target is 100 in plan 3.1b-01)
  - `tests/workflow_harness/` exists and passes foundational tests, but currently has 12 Python files (missing planned TypeScript/controller/DSL artifacts)
  - planned 3.2 enforcement tests/artifacts are still missing (`test_pipeline_connectivity.py`, `test_mvp_unstoppable.py`, replay/provenance/exploit tests, `.vrs/debug/phase-3.x/gates/*.json`)
  - smoke/controller placeholder tests are skip-only (`tests/e2e/test_agent_teams_harness_smoke.py`, `tests/test_claude_code_controller_wrapper.py`)
- Verification evidence from this pass:
  - `uv run pytest tests/workflow_harness -q` -> 91 passed
  - `uv run pytest tests/e2e/test_workflow_infrastructure.py -q` -> 33 passed
  - `uv run pytest tests/test_phase_1_1_integration.py -q` -> 25 passed (41 warnings: unknown `slow` mark + builder_legacy deprecation)
  - `uv run pytest tests/e2e/test_agent_teams_harness_smoke.py -q` -> no tests ran
  - `uv run pytest tests/test_claude_code_controller_wrapper.py -q` -> no tests ran

## Phase Governance Checklists (Entry/Exit)

Template source:
- `.planning/testing/templates/PHASE-GATE-CHECKLIST-TEMPLATE.md`

### Phase 3.1 Entry Checklist

- [x] Phase context exists and is marked planning draft/active correctly.
- [x] Strict validation + HITL + drift artifact contract is defined.
- [ ] `/gsd-plan-phase` derived checks generated for all `3.1-xx` plans.
- [ ] Research notes generated for all unresolved unknowns.
- [ ] HITL runbooks generated for all `HITL-3.1-xx` scenarios.
- [ ] Baseline plan-vs-reality dashboard generated.

### Phase 3.1 Exit Checklist

- [ ] `gates/<plan-id>.json` exists for all `3.1-xx` plans.
- [ ] `hitl/<plan-id>.md` exists for all `3.1-xx` plans.
- [ ] Drift log includes all deviations with severity + RCA when required.
- [ ] Required gate tests are not skip/xfail/placeholders.
- [ ] Plan-vs-reality dashboard regenerated and reviewed.
- [ ] Phase completion evidence recorded before moving to `3.1b`.

### Phase 3.1b Entry Checklist

- [x] Phase context has strict validation + HITL + drift contracts.
- [ ] `/gsd-plan-phase` derived checks generated for all `3.1b-xx` plans.
- [ ] Skill/agent inventory baselines captured at planning time.
- [ ] HITL runbooks generated for all `HITL-3.1b-xx` scenarios.
- [ ] Baseline plan-vs-reality dashboard generated.

### Phase 3.1c Entry Checklist

- [x] Phase context exists and is marked planning draft correctly.
- [x] Strict validation + HITL + drift artifact contract is defined.
- [ ] `/gsd-plan-phase` derived checks generated for all `3.1c-xx` plans.
- [ ] Workflow inventory and category assignments captured at planning time.
- [ ] HITL runbooks generated for all `HITL-3.1c-xx` scenarios.
- [ ] Baseline plan-vs-reality dashboard generated.

### Phase 3.2 Entry Checklist

- [x] Phase context has strict validation + HITL + drift contracts.
- [ ] `/gsd-plan-phase` derived checks generated for all `3.2-xx` plans.
- [ ] Replay/negative-control preconditions measured and documented.
- [ ] HITL runbooks generated for all `HITL-3.2-xx` scenarios.
- [ ] Baseline plan-vs-reality dashboard generated.

---

## Recently Completed

### Documentation: README Case Study Refresh ✅

**Status:** COMPLETE (2026-04-17) — Rewrote `README.md` as a professional case-study overview that foregrounds the novel behavioral-security ideas while preserving the project honesty policy.

**Updated:**
- Reframed the project as an evidence-grounded AI security auditing case study, not a finished commercial auditor.
- Added an explicit honest-status table for implemented, partial, planned, and unknown capabilities.
- Highlighted the 2026-relevant ideas: behavioral signatures, evidence-first agents, adversarial verification, and reasoning-quality evaluation.
- Simplified the architecture and repository guide so non-specialist readers can understand the direction before diving into technical docs.

**No phase status changed.**

### Phase 3.1b: Workflow Testing Harness & Test Corpus ✅

**Completed:** 2026-02-12

**Delivered:**
- 280 passing tests across workflow harness (0 regressions)
- 6 API contract specifications (1,305 lines) with dependency matrix mapping all 12 3.1c plans
- TranscriptParser extended: BSKGQuery extraction, timing fields, graph citation tracking
- OutputCollector: TeamObservation, AgentObservation, CollectedOutput, EvaluationGuidance models
- Hook infrastructure: HookConfig typed API, N hooks per event, .vrs/observations/ convention
- WorkspaceManager: Jujutsu workspace isolation (create, forget, list, rollback, snapshot)
- Scenario DSL: evaluation, evaluation_guidance, graders, trials, post_run_hooks fields
- TeamManager: full lifecycle, SendMessage capture, sandbox support
- CodeGrader + ModelGrader: 4 grading methods + CLI-based LLM grading
- 18 adversarial corpus projects (77 unique patterns, 153 findings, 3 FP controls)
- Full pipeline proven: scenario → parse → collect → grade (23 E2E smoke tests)

**Verification:** `.planning/phases/3.1b-workflow-testing-harness/3.1b-VERIFICATION.md` — 12/12 PASS

### Phase 2.1: Critical Review — Property Gap Reality ✅ (B+)

**Completed:** 2026-02-09

**Delivered:**
- 9/10 rescued patterns produce true positives on real contracts (90% TP rate)
- 275 emitted properties verified — 222 (80.7%) consumed by patterns, only 26 truly dead
- CI gate strengthened: totally-broken detection, ratchet mechanism, orphan baseline 223 → 147
- Actual pattern triage executed: 96 patterns moved (39 archived, 57 quarantined), 466 active remain
- Corrected Phase 2 false claims (169 deleted/141 quarantined was never executed)

**Assessment:** `.planning/phases/2.1-critical-review-property-gap/ASSESSMENT.md`

### Phase 1.1: Critical Review — P0 Fixes Foundation ✅ (B)

**Completed:** 2026-02-08

**Delivered:**
- PatternEngine API verified end-to-end (loads 562 patterns, produces findings on real contracts)
- Router state advancement verified (pool advances INTAKE → CONTEXT → BEADS)
- VulnDocs validation: 89/106 pass, 17 fail (16% failure rate documented, deferred)
- Integration tests written for FIX-01 and FIX-02 (506 lines, 25 tests)
- Critical assessment: FIX-01/02 pipeline-critical, FIX-03/05/06 cosmetic

**Assessment:** `.planning/phases/1.1-critical-review-p0-fixes/ASSESSMENT.md`

### Phase 2: Property Gap Quick Wins ✅

**Completed:** 2026-02-08

**Delivered:**
- 35/37 properties emitted (rescued patterns from orphan status)
- Property validation CI gate active
- ~~Pattern triage: 169 deleted, 141 quarantined~~ **CORRECTED:** Triage was documented but never executed. Actual triage done in Phase 2.1-04

### Phase 1: Emergency Triage ✅

**Completed:** 2026-02-08

**Delivered:**
- PatternEngine API fixed (pattern_dir, run_all_patterns, run_pattern)
- orchestrate resume infinite loop fixed
- 19 skill frontmatters fixed (skill: → name:)
- VulnDocs validation fixed for 74 entries
- --scope flag and google.generativeai deprecation fixed

---

## Key Metrics (Honest)

| Metric | Claimed (v5.0) | Reality (post-2.1 triage) |
|--------|----------------|---------------------------|
| Patterns | 556+ | 466 active (39 archived, 57 quarantined) |
| Rescued patterns | — | 9/10 true positive rate on real contracts |
| Orphan properties | — | 147 (down from 223) |
| VulnDocs entries | 74 validated | 106 total (89 valid, 17 failing) |
| DVDeFi Detection | 84.6% | YAML annotation, needs re-validation |
| Agents | 24 | 3-4 functional |
| Skills | 47 | Fixed (was 19 broken frontmatter) |
| E2E Pipeline | Working | Breaks at Stage 4 |
| Multi-agent debate | Core feature | Never executed |
| Benchmarks | Multiple | Zero ever run |

---

## Accumulated Context

### Roadmap Evolution
- Phase 3.1 inserted after Phase 2.1: Testing Audit & Cleanup (URGENT)
- Original Phase 3 renumbered to Phase 3.2: First Working Audit
- Reason: Testing framework has dead code, legacy infrastructure removal needed before Agent Teams (Phase 4), rule enforcement gap
- Phases 1.1 and 2.1 were independent reviews — no technical dependency between them
- Phase 2 had false documentation claims (triage never executed) — corrected in Phase 2.1
- Reordering audit (3 iterations) changed active execution path from `3.1 -> 3.2 -> 4 -> 5 -> 8` to `3.1 -> 3.2 -> 4 -> 6 -> 7 -> 5 -> 8`
- Reason for `7 before 5`: benchmark publication is now blocked until hook/schema enforcement is fail-closed, preventing vanity metrics.
- Phase 4.1 originally inserted after Phase 4: Scripted Workflow Testing Harness
- Reordering audit (iteration 4): 3 parallel research agents analyzed phase ordering, agent/skill testing needs, and tool capabilities
- Finding: Phase 4.1 plans 01-04 (controller install, harness, DSL, health-check test) have ZERO dependency on Phases 3.2 or 4
- Primary tools: Agent Teams (native) + Companion (v0.19.1, The-Vibe-Company) — Web UI + REST API (port 3456) + WebSocket (NDJSON) for secondary automation of regression testing.
- Action: Extracted harness core into new **Phase 3.1b** (8 plans, expanded from original 4) placed immediately after Phase 3.1
- Phase 3.1b expanded scope: 10 curated scenarios + dynamic generation guidelines, all 30 skill tests, all 21 agent tests, orchestrator flow, regression baseline
- Action: Phase 4.1 focused on deep validation (hook enforcement, full coverage, self-improving loops)
- Phase 3.1 corrected: dead code estimate ~3-6K LOC (not 16K), import graph analysis now mandatory first step
- Phase 3.2 corrected: re-verify break points, align markers with lowercase metadata keys, use existing replay.py (633 LOC)
- Principle: Testing frameworks must come before the features they test. "It does not matter how good the tool is if the agents do not know how to use it."
- Updated critical path: `3.1 -> 3.1b -> 3.1c -> 3.2 -> 4 -> 4.1 -> 6 -> 7 -> 5 -> 8`
- Phase 3.1c inserted between 3.1b and 3.2: Reasoning-Based Evaluation Framework
- Reason: 3.1b builds harness infrastructure (transcript parser, assertions, hooks), 3.1c adds intelligent evaluation ON TOP of that harness
- Key innovation: Smart dynamic selection per workflow + safe prompt sandboxing + regression detection + agent debrief approach (research required)
- Total 10 plans, ~43 new files, ~4500 LOC. Zero dependency on 3.2 or 4. Total plans increased from 61 to 71
- 2026-02-11: 3.1b ↔ 3.1c alignment audit completed. Added 7 explicit API contracts to 3.1b exit gate (TranscriptParser, hooks, DSL, observations, sandbox, debrief events, regression schema). Updated 3.1c with specific 3.1b dependency matrix per plan.
- 2026-02-11: Philosophy-first testing framework redesign. Phase 3.1b restructured from 8 plans to 7 (infrastructure-only). Phase 3.1c restructured from 10 plans to 12 (absorbs skill/agent/orchestrator tests + regression baseline from 3.1b). Key insight: 3.1c IS the testing framework, not an add-on to 3.1b. Skill/agent/orchestrator tests moved to 3.1c where they are evaluated with full pipeline (capability + reasoning + debrief + GVS), not just mechanical liveness. Total plans: 71 → 72.
- 2026-02-20: Phase 3.1e inserted after Phase 3.1d: Evaluation Zero — Empirical Sprint. Adversarial review (4 rounds, 12 agents) found original VRS-MSD integration plan proposed ~1,185 LOC of schemas BEFORE running a single real evaluation (v5.0 anti-pattern). 3.1e runs 5 experiments first (~430 LOC), then 3.1c builds against proven interfaces. Phase 3.1f (Proven Loop Closure, ~400 LOC) planned after 3.1c resumes. Total new plans: 96 (was 91).
- Updated execution sequence: `3.1d ✅ → 3.1e → 3.1c (resumes) → 3.1f → 3.2 → 4 → 4.1 → 6 → 7 → 5 → 8`

---

## Blockers

None currently.

---

## Next Actions

1. ~~Execute Phase 3.1~~ (Testing Audit & Cleanup) — COMPLETE (2026-02-11)
2. ~~Execute Phase 3.1b~~ (Workflow Testing Harness Core) — COMPLETE (2026-02-12)
3. **Execute Phase 3.1c** (Reasoning-Based Evaluation Framework) — PARTIAL: skeletons exist (~3.6K LOC), core missing: dual-Opus evaluator, 41/51 contracts, debrief Layer 1, improvement loop, intelligence stubs
4. ~~Execute Phase 3.1d~~ (Detection-Evaluation Feedback Bridge) — COMPLETE (2026-02-20)
5. ~~Execute Phase 3.1e~~ (Evaluation Zero — Empirical Sprint) — COMPLETE (5/5 plans). Plan 04: 35 schema fields extracted from data, 3.1c entry protocol = partial_data, 7 deferred items routed (5 to 3.1c, 2 to 3.1f). Human-approved.
6. Execute Phase 3.2 (First Working Audit)
7. Execute Phase 4 (Agent Teams Debate)
8. Execute Phase 4.1 (Workflow Test Expansion)
9. Execute Phase 6 (Test Framework Overhaul)
10. Execute Phase 7 (Documentation Honesty + Hooks)
11. Execute Phase 5 (Benchmark Reality)
10. Execute Phase 8 (Ship What Works)

---

## Session Continuity

**Last session:** 2026-03-02T18:26:05.926Z
**Stopped at:** Phase 3.1c.3: improvement pass 1 complete. 37 items (17 confirmed, 11 enhanced, 1 reframed, 1 created, 3 SYN, 4 CSC). 7 prerequisites, 2 research items. Convergence: 0% cosmetic — ACTIVE. Next: /msd:resolve-blockers 3.1c.3

**Key decisions in 3.1c.2-02:**
- TranscriptParser.get_bskg_queries() as single source of truth for forensic CLI detection (D-2 honored)
- Error detection heuristic: short results (<50 chars) check all error indicators; longer results check only first line
- Lazy imports in _check_cli_attempt_state to avoid circular import issues
- Last text event always reclassified as "conclusion" in reasoning timeline
- _resolve_transcript_paths scans JSONL event files for agent_stop events to auto-map transcripts

**Key decisions in 3.1c.2-03:**
- Dual output format: subdirectory stats.json + flat {cal-id}-graph-stats.json for validator compatibility
- Corrected function names from plan assumptions to match actual .sol sources (3 of 4 contracts had wrong names)
- Added .vrs/ground-truth/ to .gitignore exceptions for version-controlled ground truth

**Key decisions in 3.1c.2-04:**
- Integrity check unconditional when obs_dir exists (no opt-out flag) per D-5
- Stage 9 persists Stage 6 debrief object (no re-invocation of run_debrief)
- DEGRADED escalation threshold at 3+ warnings (prevents dead zone)
- Enrichment as _enrichment.json sidecar file (not embedded in observation schema)
- failure_mode classification covers FM-1 through FM-4 + FM-OTHER on all 20 violation sites
- Hand-authored expected_findings.json enables outcome-based evaluation (finding accuracy, not just CLI usage)

**Key decisions in 3.1c.2-01:**
- Separated allowed_file_reads (path substring match for Read/Grep) from allowed_bash_commands (prefix match for Bash) to close Gap 2.7 bypass
- _GUARD_PROFILE=strict + DELEGATE_GUARD_CONFIG env vars gate eval config loading with fail-fast on invalid path
- D-AUDIT coverage at ~40% -- 6 plans confirmed for phase 3.1c.2
- Forensic logging via DELEGATE_GUARD_LOG env var for blocked/allowed call audit trail

**Key decisions in 3.1c-09:**
- Thin pytest wrappers read progress.json (not invoke evaluation pipeline) -- 15 tests across 7 classes
- JSONL contamination check split into CLI + .sol Read assertions for full PROHIBITED coverage
- Joint gate (09a+10a) blocks Important sub-wave until Plan 10 Core completes

**3.1e Pass 4 progress (what's DONE):**
- All 7 adversarial reviewer temp files read and processed
- IMPROVEMENT-P4.md header updated: status=complete, agent count=14, pipeline status updated
- Adversarial Lenses section added with verdict summary table and cross-group conflicts
- ALL 39 item statuses changed: 11 confirmed, 16 enhanced, 9 reframed, 2 rejected, 1 open (IMP-03 unreviewed)
- IMP-03 correctly left as `open` (not assigned to any adversarial lens)

**3.1e Pass 4 remaining work (what's NOT DONE):**
1. **ENHANCE content rewrites** (16 items): IMP-02,05,07,10,13,14,21,22,25,28,30,32,35,36,38,39 — each needs What/Why/How replaced with reviewer's rewritten version from the .tmp-review-*.md files
2. **CREATE item insertions** (10 items): P4-ADV-1-01 through P4-ADV-7-01 — one per REFRAME item + 1 holistic gap. Content is in the .tmp-review-*.md files. IDs use format P4-ADV-{lens_index}-{NN}
3. **Temp file cleanup**: `rm .tmp-review-*.md` (7 files in phase dir)
4. **Post-review synthesis**: spawn msd-synthesis-agent
5. **IMPROVEMENT-DIGEST.md update**: Add Pass 4 data (38 items, 2 rejected, 10 ADV created)
6. **STATE.md update**: Final session continuity
7. **Commit**: IMPROVEMENT-P4.md + IMPROVEMENT-DIGEST.md
8. **Auto-chain**: `/msd:resolve-blockers 3.1e --auto`

**Lens→CREATE ID mapping:**
- Lens 1 (Session 0): P4-ADV-1-01 (counting-policy pre-generation, replaces IMP-06)
- Lens 2 (Plan 01): P4-ADV-2-01 (200 LOC as measurement, replaces IMP-08), P4-ADV-2-02 (mixed Outcome B, holistic gap)
- Lens 3 (Plan 02): P4-ADV-3-01 (three-instrument model, replaces IMP-11), P4-ADV-3-02 (non-determinism protocol, replaces IMP-15)
- Lens 4 (Plan 03/04): P4-ADV-4-01 (compound degradation split, replaces IMP-16), P4-ADV-4-02 (Haiku plausibility, replaces IMP-18)
- Lens 5 (Plan 05): P4-ADV-5-01 (minimum-necessary contract, replaces IMP-23)
- Lens 6 (Strategic): P4-ADV-6-01 (behavioral-property probe, replaces IMP-26)
- Lens 7 (Cross-Plan): P4-ADV-7-01 (falsification condition, replaces IMP-37)

**Resume approach:** Read .tmp-review-*.md files (still present), extract reviewer content for ENHANCE rewrites and CREATE items, apply to IMPROVEMENT-P4.md, then continue from step 3 above

**3.1c actual state (honest):**
- Models: 465 LOC, partial (~01 partial)
- Hooks: 9 scripts, 414 LOC (~02 done)
- Observation parser: 211 LOC, basic (~03 partial)
- Graph value scorer: 188 LOC, heuristic only (~04 partial)
- Debrief protocol: 400 LOC, Layer 1 still stub (~05 NOT done)
- Evaluation contracts: 10/51 YAML (~06 NOT done — 41 missing)
- Reasoning evaluator: 659 LOC, ZERO LLM calls (~07 NOT done)
- Evaluation runner: 309 LOC, no LLM integration (~08 partial)
- Skill/agent/orchestrator tests: 27 test functions, skeletal (~09/10/11 NOT done)
- Improvement loop: 251 LOC regression only, no metaprompting/failure catalog/intelligence stubs (~12 NOT done)
- Total: ~3,640 LOC src + 4,490 LOC tests vs planned ~10,500 LOC + ~110 files

**3.1d COMPLETE (2026-02-20):**
- 33 use case scenarios across 8 categories + pytest plugin
- 8 eval stubs fixed (heuristic replacements, not LLM)
- Detection baseline: Precision=13.3%, Recall=83.3%, F1=23.0%
- Guard recognition fix: 12→2 FPs on ReentrancyWithGuard
- Evaluator discrimination: 63.5pt spread (good=79.5, mediocre=53, bad=16)
- 413 evaluation+scenario tests passing, 0 failures
- 3 workflow docs delivered (evaluate, scenarios, improvement)
- 4 test mismatches from 3.1c prestep changes fixed
- Known caveat: calibration uses heuristic-scored synthetic transcripts, not real agent transcripts

**Next:** Plan and execute 3.1c Plans A-E. Presteps P-1 (quarantine) and P-2 (multi-agent ground truth) are DONE. LLM evaluation (Plan B) is the core missing piece.

**3.1b→3.1c alignment audit (2026-02-13):**
- 8 code-level mismatches documented (3 blocking: InboxMessage.sender rename, collect() signature drift, ModelGrader summary-only limitation)
- 4 missing integrations (debrief protocol in TeamManager is biggest gap — 3.1c-05 scope)
- ~6,700 LOC of undocumented infrastructure across 24 files (AgentSpawner, OutputParser, Assertions, TeamManager, CodeGrader, ModelGrader, 10 testing support modules) — 3.1c context only references 35% of built infrastructure
- Corpus quality: 62.7% generic reasoning chains need rewriting (96/153 findings), zero multi-agent ground truth
- All 280+ tests use synthetic data — zero real Claude Code transcripts tested
- Companion bridge: research complete, implementation deferred (not blocking any 3.1c plan)
- API contract docs fixed: InboxMessage.sender field, AgentObservation.transcript optionality, OutputCollector.collect() actual signature
- Pre-work items: rewrite 96 chains (P0), add multi-agent templates (P1), capture real transcripts (P1), run static analysis on safe variants (P2)
- EventStream: fully functional (160 LOC), no changes needed
- Verdict: Fix 3 blocking issues + update 3.1c context with full inventory, then plan with confidence

**3.1b-02 deliverables for downstream plans:**
- BSKGQuery dataclass with command classification (build-kg, query, pattern-query, vulndocs) and citation tracking
- ToolCall extended with timestamp, duration_ms, content_block (all optional, backward-compatible)
- 5 new TranscriptParser methods: get_bskg_queries(), graph_citation_rate(), get_raw_messages(), get_message_at(), get_messages_between()
- OutputCollector with collect() and summary() methods
- TeamObservation with get_agent_by_type(), cross_agent_evidence_flow(), debate_turns()
- AgentObservation, InboxMessage, EvidenceFlowEdge, DebateTurn, CollectedOutput, EvaluationGuidance dataclasses
- 144 harness tests passing (up from 96 at Phase 3.1 exit)

**3.1b-04 deliverables for downstream plans:**
- TeamManager class with full lifecycle: create_team, spawn_teammate, send_message, broadcast, shutdown_all, delete_team
- Full message content capture (sender, recipient, content, timestamp, message_type) for 3.1c debrief
- TeamObservation assembly via get_team_observation() from captured messages
- Sandbox .claude/ support: setup_sandbox(skills_dir, agents_dir) + teardown_sandbox()
- Context manager ensures no orphan teams (shutdown_all + delete_team on __exit__)
- WorkspaceManager extended: create_workspace, forget_workspace (idempotent), rollback, list_workspaces, snapshot_operation
- All Jujutsu methods check jj availability, use subprocess with 30s timeout
- 193 harness tests passing (up from 144 at 3.1b-02 exit)

**3.1b-06a deliverables for downstream plans:**
- Pattern catalog: 461 patterns from vulndocs as generation-ready specs (examples/testing/guidelines/pattern-catalog.yaml)
- Adversarial taxonomy: 3 categories (A: Name Obfuscation, B: Protocol Complexity, C: Honeypot Inversions) with 6 techniques each
- Combination rules: 15 compatible + 8 interference pattern pairs, 8 protocol theme affinities
- 8-step generation pipeline specification with quality checklists
- Opus-powered corpus-generator.md subagent (.claude/agents/corpus-generator.md)
- Orchestration wrapper generate_project.py with CLI interface for programmatic invocation
- Ground truth format with expected_reasoning_chain for 3.1c-09/10/11

**3.1b-08 deliverables for downstream plans:**
- `api-contracts/` directory with 6 specification documents covering all 3.1c-facing APIs
- Dependency matrix maps all 12 3.1c plans to specific 3.1b API contracts (41 references)
- 25 xfail test stubs verifying import compatibility (become real tests when implemented)
- Parse/execute boundary: 3.1b parses and stores, 3.1c executes and interprets
- Backward compat rules: ToolCall new fields have defaults, _records stays accessible
- Scoring scale: 0-100 integer canonical

**3.1b-05 deliverables for downstream plans:**
- ScenarioConfig extended with evaluation, evaluation_guidance, graders, steps, post_run_hooks, trials (all optional, backward compatible)
- EvaluationConfig, EvaluationGuidanceConfig, GraderConfig, StepExpect, ScenarioStep Pydantic models
- JSON Schema (schema.json) validates full scenario YAML format
- ScenarioLoader validates against schema (warns, never blocks)
- CodeGrader: string_match, regex, schema, tool_usage grading methods + routing
- ModelGrader: claude CLI subprocess AI judge with JSON response parsing
- GradeResult dataclass: passed, score (0.0-1.0), reason, grader_type
- TestScenario extended with new fields for round-trip preservation
- 234 harness tests passing (up from 193 at 3.1b-04 exit)

**Phase 3.1.1 deliverables for downstream phases:**
- `get_patterns()` is the single canonical pattern loader (466 patterns from vulndocs/)
- `tests/pattern_loader.py` provides `load_all_patterns()` with `@lru_cache` for all tests
- `src/alphaswarm_sol/queries/errors.py` has `PatternLoadError` hierarchy (3 classes)
- Bad paths raise `PatternDirectoryNotFoundError` (never silent `[]`)
- `PatternStore.load()` emits `DeprecationWarning` — use `get_patterns()` instead
- Test baseline: 10,440 passed, 46 skipped, 330 xfailed, 0 failures
- Triage report: `.vrs/debug/phase-3.1.1/failure-triage.md` (per-file categories)
- 210 PATTERN_GAP xfails → Phase 3.1c evaluation targets
- 104 STALE_CODE xfails → Phase 6 test audit cleanup
- VulnDocs schema format (schema.py:873 list vs dict) would unblock 24 tests with single fix

**Key decisions in 3.1.1:**
1. executor.py modification APPROVED — 2-line semantic change to use get_patterns()
2. Used xfail markers (not skip/delete) for all 317 failures to preserve visibility
3. Categorized 210 as PATTERN_GAP, 104 as STALE_CODE, 3 as OTHER — zero unexplained
4. PatternEngine._load_patterns() kept lenient (logs warning, returns []) to not break CLI usage

**Key decisions in 3.1-07:**
1. Jujutsu references (12) in workspace.py classified as active infrastructure (consistent with 3.1-02 gate), not legacy
2. 892 pre-existing test failures documented as stable baseline (891 in 3.1-01, +1 flaky variance)
3. SimpleToken.sol replaced with AccessGateIfReturn.sol for pipeline check (SimpleToken.sol does not exist)
4. Phase 3.1 marked COMPLETE -- all 7 objectives achieved

**Key decisions in 3.1-06:**
1. Zero test files needed deletion -- all 5 candidates already removed in 3.1-01
2. test_workflow_infrastructure.py confirmed LIVE via import analysis (WorkflowEvaluator, EvalStatus, etc. from living modules)

**Key decisions in 3.1-04:**
1. 15 rule categories with UPPERCASE-HYPHENATED IDs (shared namespace between both files)
2. Every category maps to one enforcement mechanism (hook, controller, grader, CI, architecture)
3. 5-step Mandatory Testing Pattern: TeamCreate, Task, TaskCreate/TaskUpdate, SendMessage, controller verify
4. DURATION-BOUNDS separated from TRANSCRIPT-AUTH (different enforcement mechanisms)

Previous session overhaul — updated all 6 planning files per investigation findings from 4 parallel research agents:
- Phase 3.1 context: corrected dead code estimate, added import graph analysis, corrected pattern-tester claim, updated rules for Agent Teams + controller
- Phase 3.1b context: FULL REWRITE — controller architecture, 10 curated scenarios + guidelines, 8 plans, all 30 skills + 21 agents, regression baseline
- Phase 3.2 context: added architecture context, corrected marker format (lowercase), noted existing replay.py, added re-verification requirement
- Phase 4.1 context: FULL REWRITE — removed SDK references, Claude Code as orchestrator, hook enforcement, self-improving loops, quality gates
- ROADMAP.md: updated 3.1b description and plan count (4→8), updated 4.1 description, added iteration 5, updated total (57→61)
- STATE.md: updated plan counts, accumulated context with controller architecture decision

**Key decisions in prior session:**
1. Companion (v0.19.1) for secondary automation — REST API (port 3456) + WebSocket (NDJSON) for regression testing. Replaced earlier `claude-code-controller` assumption.
2. Phase 3.1 dead code estimate corrected from ~16K to ~3-6K LOC — import graph analysis now mandatory
3. Phase 3.1b: existing harness (3,745 LOC) is foundation, not replaced. Interactive testing philosophy: Claude Code IS evaluator brain.
4. Phase 3.2 leverages existing replay.py (633 LOC), aligns with lowercase marker format, re-verifies break points
5. All phase contexts now include: anti-fabrication rules, regression protocol, Claude Code as orchestrator architecture

**Update 2026-02-10 (hard delivery gate integration):**
1. Added HDG-01..HDG-12 contracts across phase contexts with explicit phase ownership and strict validation requirements.
2. Added exploit-or-it-didn't-happen, patch-and-retest, provenance lock, shadow verifier, consensus skepticism, uncertainty protocol, permission abuse drills, chaos recovery, blind holdout, economic realism, and release kill-switch gates.
3. Aligned execution-order references to include `3.1b` and `4.1` where older chain variants remained.
4. Updated `REQUIREMENTS.md` dependency chain and execution traceability to match the active critical path.

**Update 2026-02-11 (Phase 3.1c planning):**
1. Created Phase 3.1c: Reasoning-Based Evaluation Framework — inserted between 3.1b and 3.2 in critical path.
2. Phase 3.1c adds intelligent reasoning-based evaluation on top of 3.1b harness: hook-based observability, LLM-powered reasoning evaluator, graph value scoring, agent debrief approach (research TBD), per-workflow evaluation contracts, improvement loop with regression detection, safe prompt sandboxing.
3. 10 plans, ~43 new files, ~4500 LOC. Zero dependency on 3.2 or 4.
4. Updated ROADMAP.md (total plans 61->71, progress 28%, critical path, dependency tree, iteration 6) and STATE.md accordingly.
5. Updated execution sequence to `3.1 -> 3.1b -> 3.1c -> 3.2 -> 4 -> 4.1 -> 6 -> 7 -> 5 -> 8`.

**Update 2026-02-11 (3.1b ↔ 3.1c alignment audit):**
1. Added 7 explicit API contracts to 3.1b exit gate: TranscriptParser extensibility (`get_tool_calls`, `ToolCall` dataclass), hook registration (N hooks via `install_hooks()`), `.vrs/observations/` directory convention, scenario DSL `evaluation:` block, controller event capture (`agent_transcript_path`, `SendMessage` content), sandbox `.claude/` copying, regression baseline schema.
2. Added hard dependency declaration in 3.1c ROADMAP section.
3. Updated dependency tree with explicit API contract labels on 3.1b → 3.1c edge.
4. Updated CONTEXT-OVERVIEW.md with handoff contract table.
5. Updated Next Actions: 3.1b must deliver 3.1c infrastructure readiness as part of exit gate.

**Update 2026-02-11 (misconception correction pass — 6 themes):**
1. Test corpus: 100 hardcoded projects → 10 curated scenarios + Tier A/B/C dynamic generation guidelines. Guidelines are the real deliverable. 466 pattern coverage via dynamic generation, not upfront corpus.
2. Hooks: always-on → selective per evaluation contract. Each test only enables hooks it honestly needs. Context-efficient, performance-optimized.
3. Blocking debrief: decided design → OPEN RESEARCH QUESTION. Need `/gsd:research-phase 3.1c` to investigate hook capabilities and orchestrator-level alternatives before planning.
4. Evaluation scores: 0-100 product quality metrics → internal regression signals only. Evaluation answers "what broke and where?" not "what score?" Never reported as product quality. No overpromising metrics.
5. Evaluation execution: direct Sonnet API → Claude Code subagents only (Task tool). All testing via subscription, never API billing.
6. Test generation: pre-authored per pattern → dynamic from guidelines. Guidelines define per tier what a good scenario looks like, what reasoning chain to expect, what evidence should appear.
Additional: sub-orchestrator as team teammate is a research question (not confirmed).

**Update 2026-02-11 (3.1 → 3.1c alignment correction):**
1. Reshaped Phase 3.1 plans 03, 04, 05 so every deliverable feeds forward into 3.1b → 3.1c chain.
2. Plan 3.1-03: replaced pattern-tester rewrite with Shipping Manifest + Infrastructure Audit (MANIFEST.yaml for 3.1c-09/10, evaluator audit for 3.1c integration, harness audit for 3.1b, sample capability contracts for 3.1c-06). Pattern-tester rewrite moves to 3.1c-09 where its evaluation pipeline lives.
3. Plan 3.1-04: added stable machine-readable rule IDs (e.g., EXEC-INTEGRITY, TRANSCRIPT-AUTH) so 3.1c-06 evaluation contracts can reference them as `rule_refs[]`.
4. Plan 3.1-05: replaced standalone enforcement (pytest plugin, transcript validator, report schema) with Evaluation Contract Foundation + Assertion Integration. Builds schema + 3 samples for 3.1c-06, extends existing `tests/workflow_harness/lib/assertions.py` instead of creating parallel enforcement stack.
5. Plan 3.1-07: expanded from 5 checks to 7 (added manifest verification and evaluation contract validation).
6. Success criteria, key files, preconditions, HITL scenarios, carry-forward gates all updated to match.
7. Rationale: without these changes, 3.1 produced deliverables nobody downstream consumed (pattern-tester output format unspecified, enforcement stack duplicated by 3.1c-06, transcript validator for wrong data format). Now every 3.1 output has an explicit consumer in 3.1b or 3.1c.

**Update 2026-02-11 (3.1-05 evaluation contract foundation):**
1. Defined evaluation contract JSON Schema (Draft 7) at `.vrs/testing/schemas/evaluation_contract.schema.json` with required fields: workflow_id, category, rule_refs[], capability_checks[], grader_type.
2. Created 3 sample evaluation contracts: skill-vrs-audit (3 checks), agent-vrs-attacker (4 checks), orchestrator-debate (4 checks). All rule_refs reference stable IDs from 3.1-04.
3. Extended `tests/workflow_harness/lib/assertions.py` with assert_matches_contract (Category 8) and assert_reasoning_dimensions_covered (Category 9). 9 categories total.
4. 37 tests in `tests/test_evaluation_contracts.py` covering schema, invalid rejection (7 cases), assertion pass/fail, non-regression.
5. Updated .gitignore to allow tracking of .vrs/testing/schemas/, .vrs/testing/contracts/, and .vrs/debug/ directories.

**Update 2026-02-11 (3.1b context rewrite + 3.1c alignment):**
1. Full rewrite of Phase 3.1b context.md — removed all `claude-code-controller` npm references, TypeScript files, and "all existing harness code is superseded" false claim.
2. Replaced with interactive testing philosophy: Claude Code IS the evaluator brain, Agent Teams IS the primary testing mechanism.
3. Companion (v0.19.1, The-Vibe-Company) identified as secondary automation tool — Web UI + REST API (port 3456) + WebSocket (NDJSON). Python bridge uses `requests` + `websocket-client`, not httpx.
4. Existing harness (3,745 LOC, 91+ passing tests) preserved as foundation — ClaudeCodeRunner, AgentSpawner, OutputParser, ScenarioLoader, TranscriptParser, WorkspaceManager, assertions.py all kept/extended.
5. New concepts added: OutputCollector (unified artifact collection), EvaluationGuidance (per-scenario reasoning questions for evaluator), Hook Philosophy (selective, not always-on), TeamManager (Agent Teams lifecycle).
6. Plan structure revised: 01=Companion bridge, 02=Parser+Collector, 03=Hooks (3 iterations), 04=Teams+Debrief research, 05=DSL+Guidance, 06=Corpus, 07=Interactive smoke.
7. Updated 3.1c context: added "Claude Code Has Final Word" to Critical Design Decisions, updated debrief section to reference 3.1b-04 research, replaced controller event stream references with Companion + existing harness, added OutputCollector and EvaluationGuidance as new API contracts.
8. Updated ROADMAP.md: removed `claude-code-controller` from 3.1b description, notes, dependency tree, research references.
9. Updated STATE.md with accumulated context for this session's research findings.

**Update 2026-02-11 (Research Spike 02 — Debrief Research COMPLETE):**
1. Research Spike 02 resolved all 5 research questions for agent debrief mechanism with HIGH confidence.
2. Four-layer debrief strategy verified: SendMessage to idle agent (primary), hook gates via TeammateIdle/TaskCompleted exit 2 (safety net), LLM quality gate (optional), transcript analysis (fallback).
3. CRITICAL BUG #20221 discovered: `type: "prompt"` SubagentStop hooks are BROKEN — send feedback but do NOT prevent termination. Must use `type: "command"` hooks only.
4. New hook events discovered: TeammateIdle and TaskCompleted (Agent Teams-specific) — preferred blocking points for debrief over SubagentStop.
5. `stop_hook_active` flag verified as safety mechanism preventing infinite blocking loops.
6. Updated 3.1b context.md: 3.1b-03 (hooks) with new events, timeout fix 5s→30s, 3 hook types; 3.1b-04 (debrief) status changed from EXPLORATORY to RESEARCH COMPLETE.
7. Updated 3.1c context.md: debrief section changed from "RESEARCH REQUIRED" to "RESEARCH COMPLETE"; 3.1c-05 plan updated with concrete four-layer implementation; hook registration section updated with verified exit code 2 behavior; added TeammateIdle/TaskCompleted hooks to 3.1c hook list.
8. Findings document: `.vrs/debug/phase-3.1b/research/hook-verification-findings.md`.

**Update 2026-02-12 (3.1b-03 hook infrastructure verification):**
1. Hook infrastructure verified 3.1c-ready -- no gaps found, no code changes needed.
2. install_hooks() accepts arbitrary extra_hooks list for any event type (extensible, not hardcoded).
3. _ensure_hook() deduplicates by command string -- idempotent registration confirmed.
4. .vrs/observations/ directory created during workspace setup (3.1c JSONL convention).
5. 96 harness tests passing (up from 91 at Phase 3.1 exit).
6. Hook exit code 2 blocking is Claude Code feature -- tested by 3.1c gate hooks, not log_session.

**3.1c presteps completed (2026-02-19):**
- Prestep P-1 (Quarantine Heuristic Scores): DONE
  - `DimensionScore.scoring_method: Literal["heuristic", "llm"]` field added to models.py
  - `ScoreCard.capability_gating_failed: bool` field added
  - `ScoreCard.has_heuristic_scores` property added
  - `BaselineManager` guards: rejects heuristic-scored Core results, capability-gate failures, unreliable first runs from baselines
  - `TIER_THRESHOLDS` and `CORE_WORKFLOW_PREFIXES` constants in regression_baseline.py
  - 298 tests pass, 0 regressions
- Prestep P-2 (Multi-Agent Ground Truth Format): DONE
  - `debate_expectations` schema added to corpus ground-truth.yaml files
  - 3 entries in defi-lending-protocol-01 (balance-update-after-transfer, oracle-stale-price, auth-002)
  - 2 entries in flash-loan-vault-04 (balance-update-after-transfer via encoding indirection, vault-share-inflation)
  - Schema: 4 outcome types, defender position taxonomy, anti-rubber-stamp checks, quality signals
- CONTEXT.md updated: Plan A exit criteria tightened (>= 3 transcripts, DC-3 fix, P-1 guard active)

**Research resolved (2026-02-23):**
- P14-ADV-4-02: `--temperature` flag UNAVAILABLE in Claude Code v2.1.50. Document as non-controllable.
- P14-ADV-2-02: `claude -p --output-format json` DOES return `cost_usd` and `usage` fields. Cost tracking per call IS possible. Prior claim incorrect.
- P15-IMP-17: Parallel `claude -p` IS safe (stateless one-shot). File locking needed for BaselineManager only.
- P15-ADV-4-01: Context exhaustion is coordinator-only problem. Each `claude -p` gets own 200K window.

**Resume file:** .planning/phases/3.1c.3-evaluation-intelligence-bootstrap/IMPROVEMENT-P1.md

---
*State updated: 2026-02-19T10:00Z*
