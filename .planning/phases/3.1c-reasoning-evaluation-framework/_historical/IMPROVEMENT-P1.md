# Improvement Pass 1

**Pass:** 1
**Date:** 2026-02-18
**Prior passes read:** none
**Status:** complete

## Improvements

### P1-IMP-01: Resolve the Execution Model Split-Brain (Showstopper)
**What:** CONTEXT.md states "ALL evaluation runs through Claude Code subagents (Task tool with prompt). NEVER direct Anthropic API calls." But the evaluation pipeline (EvaluationRunner, GraphValueScorer, ReasoningEvaluator) is Python code that runs via `uv run pytest`. Python code cannot call the Task tool — that's a Claude Code tool available only during interactive/subagent sessions.
**Why:** This is a fundamental architecture contradiction. The dual-Opus meta-evaluation (3.1c-07) requires spawning Task tool subagents, but the EvaluationRunner is a Python class. A planner would produce a plan where 3.1c-07 literally cannot execute as described. Three possible resolutions exist:
  - (A) EvaluationRunner shells out to `claude --print` for LLM evaluation — headless, no Task tool, no skills
  - (B) The entire evaluation pipeline runs inside a Claude Code session (not pytest) — tests become prompts, not Python
  - (C) Direct Anthropic API calls from Python for evaluation only — violates the locked decision but is pragmatic
  CONTEXT.md must pick one and document the boundary clearly: "deterministic stages run in Python, LLM evaluation stages use [mechanism X]."
**How:** Add an "Execution Boundary" section to CONTEXT.md that explicitly defines: (1) which pipeline stages run in Python (pytest), (2) which stages require LLM calls, (3) the mechanism for LLM calls (recommend Option A: `ClaudeCodeRunner` wrapping `claude --print` for evaluation prompts). Update the locked decision to say "Workflow runs use Claude Code subagents; evaluation scoring uses `claude --print` via ClaudeCodeRunner."
**Impacts:** 3.1c-07 (Evaluator) design fundamentally changes. 3.1c-08 (Runner) must handle the Python↔Claude boundary. All downstream plans affected.
**Research needed:** yes — Verify that `claude --print --output-format json` can receive a transcript + rubric and return structured JSON scores. Test with a 10-line prompt. 15-minute spike.
**Confidence:** HIGH
**Status:** implemented
**Research summary:** GAP-01 RESOLVED. `claude -p --output-format text --json-schema SCHEMA` works reliably with guaranteed schema compliance via constrained decoding. Use `--tools "" --no-session-persistence --max-turns 1` for evaluation calls. Existing ModelGrader validates the subprocess pattern. Cannot nest claude -p from within Claude Code sessions.

### P1-IMP-02: Promote Debrief Validation to P0 Gate
**What:** CONTEXT.md lists "Quick debrief viability pilot" as P2 priority (prestep 5). The debrief strategy is marked "Research Complete" with HIGH confidence, but Layer 1 (the PRIMARY layer) is a stub returning `success=False` and has never been tested with a real agent.
**Why:** If SendMessage-to-idle-agent doesn't work, the entire debrief strategy collapses to Layer 4 (keyword-matching transcript fallback, confidence=0.0). This would degrade 3.1c-05, 3.1c-07, and all investigation/orchestration evaluations in 3.1c-09/10/11. A 30-minute validation now prevents weeks of building on a broken assumption. The PHILOSOPHY.md Rule F ("Honest Research") explicitly requires evidence before claiming success.
**How:** Move prestep 5 from P2 to P0. Add hard gate: "3.1c-05 planning MUST NOT begin until debrief viability is validated with a real SendMessage-to-idle-agent test. Result documented in `.vrs/debug/phase-3.1c/debrief-viability.md`." If it fails, CONTEXT.md must update debrief strategy to make Layer 4 (transcript analysis) the primary approach.
**Impacts:** 3.1c-05 (Debrief) blocked until validation. Wave 3 potentially delayed by 30 minutes. Minimal cost, massive risk reduction.
**Research needed:** yes — Run the actual SendMessage-to-idle-agent test: spawn an agent team, let one agent go idle, send it a message, verify it wakes and responds. 30 minutes max.
**Confidence:** HIGH
**Status:** implemented
**Research summary:** GAP-02 RESOLVED. SendMessage to idle agents is officially supported ("wakes them up and they process normally"). Bug #24246 affects idle notification timing but not message delivery. Use TaskCompleted hook as debrief trigger, not idle notifications. Guard against session resumption (teammates not restored).

### P1-IMP-03: Add Real-Transcript Checkpoint Between Wave 2 and Wave 3
**What:** CONTEXT.md acknowledges "All 280 tests use synthetic data" and says to capture transcripts "during early 3.1c execution" but provides no hard gate. Wave 2 (3.1c-02 Hooks + 3.1c-03 Parser) can complete and Wave 3 can begin without any real transcript validation.
**Why:** If real Claude Code JSONL transcripts have different record structures, compaction artifacts, or content block types than synthetic data, TranscriptParser will break silently. Building the GraphValueScorer (3.1c-04) and Debrief Protocol (3.1c-05) on top of an untested parser creates cascading failures. RESEARCH.md Open Question 3 flags this explicitly.
**How:** Add to execution waves: "CHECKPOINT after Wave 2: TranscriptParser validated on >= 3 real Claude Code session transcripts. Validation documented in `.vrs/debug/phase-3.1c/real-transcript-validation.md`. Wave 3 MUST NOT begin until checkpoint passes." Real transcripts are captured as a byproduct of 3.1c-02 hook development (hooks fire during Claude Code sessions).
**Impacts:** Adds a gate between Wave 2 and Wave 3. Could delay Wave 3 by 1-2 hours if parser fixes are needed. Prevents much larger delays from discovering parser issues at Wave 4+.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-04: Split 3.1c-06 (Contracts) Into Two Sub-Plans
**What:** CONTEXT.md assigns all 51 evaluation contracts to a single plan (3.1c-06). 10 exist, 41 must be authored. The RESEARCH.md identifies this as significant manual work requiring reading 5,135 lines of agent/skill spec prose.
**Why:** 41 contracts at ~30-60 minutes each = 20-40 hours of authoring in ONE plan. This violates GSD's plan-size guidelines and creates a planning bottleneck in Wave 1. The mitigation "template-based generation for support tier" needs its own plan because: (a) templates must be validated against real evaluation runs, (b) generated contracts need human review for semantic correctness (a `health-check` contract auto-generated from investigation template would be nonsensical), (c) Core contracts define the quality standard that templates must match.
**How:** Split into: 3.1c-06a (Core + Important contracts, ~15, hand-authored from agent/skill specs, Wave 1) and 3.1c-06b (Standard contracts, ~36, template-generated with human review, can run after 3.1c-06a defines the quality standard). Update execution waves accordingly. 3.1c-06a stays in Wave 1; 3.1c-06b can run in Wave 2 or 3 since only Core contracts are needed for Wave 4 (Evaluator).
**Impacts:** Unblocks Wave 1 parallelism (3.1c-01 + 3.1c-06a are both manageable size). Gives template-generated contracts time to be validated. Changes wave dependencies slightly.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-05: Acknowledge Wave 1 Coupling Between Models and Contracts
**What:** CONTEXT.md states Wave 1 (3.1c-01 Models + 3.1c-06 Contracts) has "zero dependencies." But evaluation contracts define `reasoning_dimensions` that must map to fields in 3.1c-01's Pydantic models.
**Why:** If 3.1c-01 finalizes model schemas (e.g., `DimensionScore` with a fixed enum of dimension names) before 3.1c-06 discovers what contracts actually need, you get schema-contract mismatches. The models and contracts co-define the evaluation vocabulary.
**How:** Change Wave 1 description from "zero dependencies" to "soft coupling — models define the type vocabulary, contracts define the instances. 3.1c-01 MUST define dimension names as open strings (not closed enums) to allow contracts to introduce new dimensions without model changes."
**Impacts:** 3.1c-01 model design (use open strings or extensible enums for dimensions). Minor coordination overhead in Wave 1.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-06: Defer Cascade DAG Scoring to v2
**What:** PHILOSOPHY.md Pillar 1 describes cascade-aware evaluation scoring with a DAG of 7 reasoning moves, hard/soft blocking modes, root cause vs cascade victim classification, inspired by PRISM-Physics (Stanford/ICLR 2026). CONTEXT.md treats this as part of 3.1c-07.
**Why:** This is cutting-edge ML evaluation research being treated as a feature in one plan. You have ZERO real transcripts. You're designing a scoring DAG for data you haven't seen. The cascade modes (hard/soft/attribution) triple the complexity for uncertain benefit. What you actually need for v1: Score 3 things: (1) Did it query the graph? (2) Did it use the results? (3) Did it reach correct conclusions? The simpler alternative — score dimensions independently, correlate post-hoc — delivers 80% of the value with 20% of the complexity. PHILOSOPHY.md North Star #13 is unachievable in 3.1c because no labeled failure transcripts exist yet.
**How:** Move cascade DAG scoring from 3.1c-07 to "Deferred Ideas" in CONTEXT.md. Replace 7 reasoning move types with 3 practical dimensions for v1: `graph_query_quality`, `evidence_utilization`, `conclusion_grounding`. Keep the 7-move taxonomy as v2 roadmap. Update PHILOSOPHY.md North Star #13 to achievable v1 version.
**Impacts:** 3.1c-07 complexity dramatically reduced. PHILOSOPHY.md requires update.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-07: Add Cost Model for Evaluation Pipeline
**What:** Neither CONTEXT.md nor RESEARCH.md discuss the operational cost of running the evaluation pipeline. 51 workflows x dual-Opus evaluation x multiple scenarios = potentially hundreds of Opus calls per full regression suite.
**Why:** Without a cost model, the planner can't make sensible decisions about: (a) how often to run full suites vs targeted tests, (b) whether dual-Opus is justified for Standard tier (26 workflows), (c) the tier-weighted evaluation depth strategy. At current Opus pricing, a full suite could cost $50-300+. The PHILOSOPHY.md says "no cost constraints" but this should be acknowledged as a design choice, not silently assumed.
**How:** Add a "Cost Model" section to CONTEXT.md with: (a) estimated tokens per evaluation call, (b) estimated cost per full regression suite, (c) recommended run frequency by tier, (d) cost optimization strategies (shallow evaluation catches ~60% of regressions at near-zero LLM cost).
**Impacts:** May influence 3.1c-08 (Runner) to implement cost-aware scheduling. May affect dual-Opus decision for Standard tier.
**Research needed:** yes — Estimate average transcript size (tokens), rubric prompt size, and scoring output size. Multiply by workflow count x evaluators. Use current Anthropic pricing. 30-minute estimation exercise.
**Confidence:** MEDIUM
**Status:** implemented
**Research summary:** GAP-03 RESOLVED. Cost fears overblown. Tiered model + single evaluator: $1.87/suite. All-Opus dual evaluator: $8/suite. With caching+batch: $0.83/suite. Weekly regression: $7.48/mo. Real cost is workflow runs, not evaluation. Opus for ~8 critical, Sonnet for ~12 standard, deterministic for ~31 mechanical.

### P1-IMP-08: Resolve Observation vs Transcript Dual-Source Confusion
**What:** RESEARCH.md Open Question 4 identifies that two independent data sources exist: (a) observation hooks writing to `.vrs/observations/` (real-time, during session), and (b) TranscriptParser reading from session JSONL (post-hoc). CONTEXT.md doesn't specify which is primary for each pipeline stage.
**Why:** Two truth sources with different failure modes create ambiguity. The GraphValueScorer needs BSKG query data — should it read from ObservationParser or TranscriptParser? If hooks fail silently, ObservationParser sees fewer events.
**How:** Add a "Data Source Hierarchy" section to CONTEXT.md: "Primary: ObservationParser (hooks) for GVS, capability checks, and real-time evaluation. Secondary: TranscriptParser for debrief fallback (Layer 4), post-hoc analysis, and `cited_in_conclusion` computation."
**Impacts:** 3.1c-04 (GVS) and 3.1c-08 (Runner) data source selection clarified.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-09: Clarify the Improvement Loop Actor (Human vs Automated)
**What:** CONTEXT.md and PHILOSOPHY.md describe the improvement loop with "parallel prompt exploration" but Rule E says "The improvement loop proposes; the human disposes." The mechanism for WHO reads failure narratives, generates variants, and triggers re-tests is never specified.
**Why:** Without a clear actor model, 3.1c-12 can't be planned. The PHILOSOPHY.md's "parallel prompt exploration" implies automation, but Rule E implies human control. These are different architectures.
**How:** Add to CONTEXT.md under 3.1c-12: "The improvement loop is HYBRID: System generates failure narratives + prompt variant suggestions. Human reviews and approves variants for testing. System executes approved variants in parallel. Human selects winning variant. Trigger: on-demand via `/vrs-improve` skill, NOT automatic."
**Impacts:** 3.1c-12 plan scope and exit criteria.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-10: Remove Composition Testing from 3.1c Scope
**What:** PHILOSOPHY.md Rule M defines 8 composition variants. CONTEXT.md GAP-5 says "Move to Phase 4.1" but PHILOSOPHY.md still lists it as a binding Rule.
**Why:** CONTEXT.md and PHILOSOPHY.md contradict. Planners reading PHILOSOPHY.md will try to implement composition testing in 3.1c, conflicting with the CONTEXT.md deferral.
**How:** Mark Rule M as "DEFERRED TO 4.1" in PHILOSOPHY.md. Ensure no North Star condition requires composition testing.
**Impacts:** PHILOSOPHY.md update. Reduces 3.1c-11 scope.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-11: Add Per-Plan Exit Criteria to CONTEXT.md
**What:** CONTEXT.md lists execution waves but no concrete, testable exit criteria per plan. When is 3.1c-07 "done"?
**Why:** Without exit criteria, planners can't define plan boundaries and GSD verification gates can't pass.
**How:** Add a "Plan Exit Criteria" section to CONTEXT.md with testable gates per plan. Example for 3.1c-07: "EXIT: (a) ReasoningEvaluator.evaluate() returns per-dimension 0-100 scores. (b) 3 test transcripts evaluated end-to-end. (c) Heuristic fallback preserved for simulated mode."
**Impacts:** Every plan gets clearer scope.
**Research needed:** no
**Confidence:** MEDIUM
**Status:** implemented

### P1-IMP-12: Address Hook Cold-Start Overhead
**What:** All observation hooks start a new Python process per invocation. 100-300 tool calls × ~100-200ms = 10-60 seconds of accumulated overhead per session.
**Why:** The decision should be explicit, not discovered during implementation.
**How:** Add to CONTEXT.md under 3.1c-02: "Hook performance constraint: Keep imports minimal — only `json`, `sys`, `pathlib`, and observation_writer. Target < 50ms per invocation. Measure and document."
**Impacts:** 3.1c-02 hook implementation guidelines. Minor.
**Research needed:** no
**Confidence:** MEDIUM
**Status:** implemented

### P1-IMP-13: Reduce PHILOSOPHY.md North Star from 15 to ~8 Achievable Conditions
**What:** PHILOSOPHY.md lists 15 North Star conditions. Several require artifacts/data that cannot exist within 3.1c: #10 (coverage radar >60%), #13 (cascade scoring calibrated), #14 (adversarial audit), #15 (contract versioning evolution).
**Why:** Unachievable conditions either block Phase 3.2 forever or get quietly ignored. Move unachievable conditions to "Phase 4.1+ Extensions."
**How:** Keep conditions 1-9, 11-12. Move 10, 13, 14, 15 to future scope with achievable v1 replacements.
**Impacts:** PHILOSOPHY.md North Star. Unblocks Phase 3.2 gate.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-14: Simulated Tests Provide Zero Real Signal — Define the Transition Plan
**What:** All existing evaluation tests (`test_skill_evaluation.py`, `test_agent_evaluation.py`, `test_orchestrator_evaluation.py`) use `SimulatedSkillOutput` with hand-crafted tool sequences and fake BSKG queries. Example from `test_skill_evaluation.py:53-63`: a "good investigation" is `tool_sequence=["Bash","Bash","Read","Bash","Read","Write"]` with 4 fake queries. This tests the evaluator's plumbing, NOT whether real agents reason well.
**Why:** These tests are evaluator unit tests, not workflow tests. The danger: 3.1c-09/10/11 are called "Skill Evaluation," "Agent Evaluation," "Orchestrator Evaluation" — implying they evaluate real workflows. But they evaluate synthetic stubs. There is NO plan describing when simulated tests transition to real workflow execution.
**How:** Add to CONTEXT.md: "3.1c-09/10/11 have TWO phases: Phase A (simulated): Validates evaluation pipeline produces correct scores given known inputs (evaluator unit tests). Phase B (real execution): Spawns actual agents against corpus contracts, evaluates with full pipeline. Phase B is the actual test. Transition trigger: 3.1c-08 can execute a real workflow end-to-end with `run_mode=HEADLESS`."
**Impacts:** 3.1c-09/10/11 scope and exit criteria. Makes explicit what's really being tested.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-15: The 7-Move Reasoning Extraction Has No Prototype — Risk of Pure Theory
**What:** PHILOSOPHY.md describes extracting 7 reasoning move types from agent transcripts. The existing `reasoning_evaluator.py` has a `REASONING_PROMPT_TEMPLATE` (line 40-55) that asks an LLM to score dimensions but NO code for extracting discrete reasoning moves. LLM transcripts are messy — agents don't label their reasoning moves.
**Why:** Extracting moves requires either (a) the LLM evaluator inferring them from context (makes the evaluator prompt extremely complex) or (b) heuristic detection from tool call patterns (fragile). Neither has been prototyped. This is the core differentiator of 3.1c-07 and it's 100% theoretical. Connected to P1-IMP-06: if cascade scoring is deferred and 7 moves reduced to 3 dimensions, this becomes much simpler.
**How:** Add to presteps: "P0.5: Reasoning Dimension Extraction Prototype — Before 3.1c-07 planning, create a 50-line prototype that takes ONE real transcript and attempts to score the 3 core dimensions (graph_query_quality, evidence_utilization, conclusion_grounding). Test both LLM-based and heuristic approaches. Document which produces usable results."
**Impacts:** Adds a prestep that de-risks 3.1c-07. May fundamentally change evaluator design.
**Research needed:** yes — Run the prototype. 1-2 hours. Critical path for 3.1c-07 viability.
**Confidence:** HIGH
**Status:** implemented
**Research summary:** GAP-04 RESOLVED. LLM-as-judge for multi-dimension rubric scoring is proven (G-Eval, RAGAS, LLM-Rubric). Use 5-level anchored rubric per dimension with CoT before score. Single call with --json-schema. Map levels 1-5 to scores {10,30,50,70,90}. Calibrate with 5 golden transcripts. ~$0.01-0.03 per eval, ~3-6s latency with Sonnet.

### P1-IMP-16: GVS Calibration Has a Chicken-and-Egg Problem
**What:** PHILOSOPHY.md says GVS needs "30+ labeled transcripts" for calibration. But labeled transcripts require running the evaluation pipeline, which needs a calibrated GVS.
**Why:** Bootstrapping problem. The current GVS has heuristic scoring with `_DEFAULT_CITATION_RATE = 0.3` — it can run uncalibrated. But North Star #3 is unachievable without a labeling process.
**How:** Define phased GVS calibration: Phase 1 (3.1c-04): Ship with heuristic scoring. Phase 2 (3.1c-09/10): During real runs, capture transcripts + GVS scores, human labels sample. Phase 3 (3.1c-12): Use labeled sample (target 30+) to calibrate thresholds. Adjust North Star #3 to v1 version.
**Impacts:** 3.1c-04 scope reduced. North Star #3 adjusted.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-17: "Agents Don't Know They're Being Tested" Is a Fiction — Acknowledge Controlled Environment
**What:** PHILOSOPHY.md says "spawn real agents that don't know they're being tested." Agents analyze contracts from `examples/testing/corpus/` — synthetic 50-200 line Solidity with pre-planted vulnerabilities.
**Why:** This is a controlled test environment, not "real" analysis. An agent might reason perfectly on a 50-line synthetic contract and fail on a 5000-line real protocol. Test signal is bounded by corpus quality (18 seed projects, 153 findings). The language is misleading.
**How:** Replace "don't know they're being tested" with "agents run with production prompts and tools, targeting corpus contracts that provide ground truth for evaluation." Add: "3.1c evaluates reasoning quality in a controlled corpus environment. Phase 3.2 is where agents face real contracts."
**Impacts:** Framing change only. Prevents false confidence.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-18: Dual-Opus Meta-Evaluation May Produce Agreement-by-Shared-Bias, Not Validity
**What:** PHILOSOPHY.md Rule J requires two independent Opus evaluators. CONTEXT.md marks this as core of 3.1c-07.
**Why:** Two instances of the SAME model with the SAME biases will agree — high inter-rater agreement does not mean the evaluation is correct. Inter-rater agreement measures consistency, not validity. If Opus systematically overweights verbose reasoning, both evaluators share that bias. True validation requires anchor transcripts with human-assigned scores.
**How:** Add to CONTEXT.md: "Inter-rater agreement measures CONSISTENCY, not VALIDITY. For v1, use a SINGLE well-prompted Opus evaluator (see P1-IMP-21 for rationale). Add 10-20 anchor transcripts with human-assigned scores as the ground truth for evaluator validity in 3.1c-12."
**Impacts:** 3.1c-07 design (single evaluator for v1). 3.1c-12 scope (create anchor set).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-19: The Inter-Rater Agreement Threshold (15pt) Is Arbitrary and Uncalibrated
**What:** 15-point disagreement threshold appears in multiple places: tier promotion, evaluator self-improvement, meta-evaluation. No calibration data exists.
**Why:** On first execution, natural variance between two evaluator calls is unknown. If natural variance is ~20 points, EVERY evaluation is flagged "unreliable." The threshold should be derived from data, not assumed. Connected to P1-IMP-21: if dual-Opus is deferred, this threshold becomes moot for v1.
**How:** If dual-Opus is kept: change all 15-point references to "calibrated during 3.1c-07 development, initially 15 points." If single evaluator adopted (P1-IMP-21): remove all inter-rater threshold references from v1 scope.
**Impacts:** 3.1c-07 exit criteria. PHILOSOPHY.md updates.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-20: Half the "51 Workflows" Are Dev/Mechanical Tools — LLM Reasoning Evaluation Adds No Value
**What:** PHILOSOPHY.md Pillar 2 says "No workflow excluded from reasoning evaluation." The MANIFEST includes `vrs-health-check`, `vrs-bead-list`, `vrs-bead-update`, `vrs-taxonomy-migrate`, `vrs-benchmark-runner` — mechanical CRUD operations.
**Why:** Evaluating "reasoning quality" for a health-check skill (runs `alphaswarm tools status`) is meaningless — there's no reasoning to evaluate. Running Opus evaluation on `bead-list` wastes ~$5-10 per cycle for zero signal. The "no exclusions" rule conflates "all workflows tested" (correct) with "all workflows need LLM-powered reasoning evaluation" (incorrect).
**How:** Define evaluation depth by workflow nature: (a) INVESTIGATION (~10-12 workflows): Full reasoning evaluation. (b) SYNTHESIS/COORDINATION (~5-8): Coherence scoring, evidence flow. (c) MECHANICAL (~25-30): Capability checks ONLY — deterministic assertions, NO LLM evaluation. "All workflows tested" ≠ "all workflows get same evaluation depth."
**Impacts:** Dramatically reduces workflows needing LLM evaluation (51 → ~15-20). Reduces cost. Simplifies contracts.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-21: Phase is a Research Program Masquerading as Engineering — Collapse 12 Plans to ~5
**What:** 3.1c proposes 12 plans, ~110 new files, ~10,500 LOC, 15 North Star conditions. The core question is: "Are our skills and agents producing correct security findings with proper reasoning?" This can be answered with far less machinery.
**Why:** The phase designs an elaborate evaluation machine before having any real data to evaluate. 7 of 12 plans have "STUB DONE" status — meaning skeletons exist but no real functionality. The stubs create false confidence that work is 50% done when the hard part (real evaluation with real data) is 0% done. Most of the complexity (cascade DAG, 51 individual contracts, 12 intelligence sub-modules, meta-evaluation, adaptive tiers, counterfactual replay, composition testing) provides value only AFTER you have 100+ real evaluation runs showing where the simple approach falls short.
**How:** Consider collapsing to 5 practical plans:
  - 3.1c-A: Capture 10 real transcripts, validate parser, calibrate GVS (~500 LOC)
  - 3.1c-B: Author ~10 category-level + ~5 custom evaluation contracts (~1,000 LOC YAML)
  - 3.1c-C: Single Opus reasoning evaluator with structured rubric (~800 LOC)
  - 3.1c-D: Evaluation runner + baseline + regression detection (~600 LOC extending existing)
  - 3.1c-E: Run 10 core workflows, establish baseline, prove the improvement loop works (~400 LOC)
  Total: ~3,300 LOC instead of ~10,500. 5 plans instead of 12. Same practical value. The intelligence layer, cascade scoring, meta-evaluation, 51 individual contracts, adaptive tiers, and counterfactual replay become v2 scope, activated when real data shows the simple approach is insufficient.
**Impacts:** Fundamental restructuring of 3.1c. All 12 plan descriptions change. PHILOSOPHY.md scope shrinks. Phase becomes achievable in weeks instead of months. Biggest risk: user may disagree with scope reduction.
**Research needed:** no — this is a scoping decision, not a technical question.
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-22: 12 Intelligence Sub-Module Stubs Are Premature Abstraction
**What:** CONTEXT.md describes 12 intelligence sub-modules as v2 scope but structurally planned: scenario_synthesizer, tier_manager, reasoning_decomposer, coverage_radar, contract_healer, insight_propagator, evaluator_improver, composition_tester, fingerprinter, adversarial_auditor, counterfactual_replayer, feedback_ingester.
**Why:** Even as stubs, 12 files × interface design × activation strategy documentation = significant overhead that provides zero value until you have 20+ real runs per workflow. Creating stubs now is premature abstraction — the interfaces will likely change once real data reveals what intelligence is actually needed. The stubs constrain future design without providing current value.
**How:** Remove intelligence sub-module stubs from 3.1c scope entirely. Add a single `INTELLIGENCE-ROADMAP.md` document listing the 12 modules with trigger conditions for when each should be implemented. No code, no interfaces, no stubs. Code them when the trigger condition is met (e.g., "Implement tier_manager after 50+ evaluation runs show static tiers are insufficient").
**Impacts:** Reduces 3.1c file count by ~12-15 files. Removes premature interface design. Simplifies 3.1c-12.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-23: Anti-Fabrication Checks Guard Against a Problem That Won't Exist with Real Data
**What:** PHILOSOPHY.md Rule D defines 6 static triggers and adversarial diversity analysis for detecting fabricated results. CONTEXT.md lists these as active requirements.
**Why:** The anti-fabrication rules were created because all prior tests used synthetic data that could trivially produce perfect scores. Once you have a real capture pipeline with real Claude Code sessions, fabrication isn't the risk — the risk is the evaluator being wrong, not the data being fake. The 6 triggers (100% pass rate, identical outputs, all scores at 100, no variance, duration <5s, transcript <500 chars) are reasonable sanity checks but don't need the adversarial diversity analysis layer (cosine similarity of reasoning chains across runs) for v1.
**How:** Keep the 6 static triggers as lightweight sanity checks in the evaluation runner. Remove adversarial diversity analysis from v1 scope — add it when the improvement loop has run enough iterations that gaming becomes a realistic concern. Update Rule D to: "Level 1 — Static triggers: active for all runs. Level 2 — Adversarial diversity analysis: v2 scope, activated after 50+ improvement loop iterations."
**Impacts:** Reduces 3.1c-12 complexity. Removes a feature that solves a problem that doesn't exist yet.
**Research needed:** no
**Confidence:** MEDIUM
**Status:** implemented

### P1-IMP-24: Category-Level Contracts Cover 80% of Value — 51 Individual Contracts Is Busywork
**What:** CONTEXT.md requires 51 per-workflow evaluation contracts. 10 exist, 41 must be authored. Most of the 30 skills and 21 agents share behavioral patterns by category.
**Why:** `/vrs-bead-create`, `/vrs-bead-update`, `/vrs-bead-list` all follow the same pattern: parse input, call a tool, write output. Testing them as 3 separate evaluation targets with 3 individual contracts is busywork. The existing 4 templates (investigation, tool, orchestration, support) already define category-level contracts. You could cover 80% of evaluation value with ~8-10 category-level contracts plus 5-6 custom ones for core workflows. The remaining 20% (per-workflow nuances) can be added incrementally as evaluation data reveals which workflows need custom contracts. Supports P1-IMP-20's workflow grouping.
**How:** Replace "51 per-workflow contracts" with: "~10 Core contracts (hand-authored, per-workflow for investigation agents + core skills) + 4 category-level template contracts (investigation, tool, orchestration, support) that cover the remaining ~41 workflows. Per-workflow contracts for non-core workflows are created ON DEMAND when category-level evaluation proves insufficient for a specific workflow."
**Impacts:** 3.1c-06 scope dramatically reduced (10 custom + 4 templates instead of 51 files). Simplifies maintenance. Aligns with P1-IMP-04 split.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-25: Single Opus Evaluator Is Sufficient for v1 — Defer Dual-Opus to v2
**What:** CONTEXT.md and PHILOSOPHY.md require TWO independent Opus evaluators per transcript with inter-rater agreement. This doubles evaluation cost and complexity.
**Why:** A single well-prompted Opus evaluator with a structured rubric gives you ~95% of the value of dual-Opus. The dual-Opus approach catches evaluator prompt bugs (if the rubric is ambiguous, evaluators diverge) — but you can catch those same bugs more cheaply with anchor transcripts (P1-IMP-18). The execution model split-brain (P1-IMP-01) makes dual-Opus even harder to implement. Cost: 2x Opus calls × 15-20 workflows needing LLM eval × 3 runs = ~90-120 Opus calls just for baseline. Single evaluator: 45-60 calls. For a v1 that's establishing baselines and proving the concept works, single evaluator is the pragmatic choice.
**How:** Change CONTEXT.md locked decision: "v1 uses a single Opus evaluator per transcript. Dual-Opus meta-evaluation is v2 scope, activated when: (a) 50+ evaluation runs exist, (b) anchor transcripts show single-evaluator accuracy > 80%, (c) specific dimension reliability concerns emerge from the failure mode catalog." Remove all inter-rater agreement references from v1 plans. Keep the meta-evaluation architecture in PHILOSOPHY.md as the v2 target.
**Impacts:** 3.1c-07 complexity halved. Cost halved. P1-IMP-01 execution boundary simplified. P1-IMP-19 threshold becomes moot for v1. PHILOSOPHY.md Rule J becomes "Rule J (v2): Meta-Evaluation Validates the Evaluator."
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P1-IMP-26: Update Model Strategy — Sonnet 4.6 Default, Opus 4.6 When Needed, Haiku for Efficiency
**What:** CONTEXT.md and PHILOSOPHY.md reference model tiers (opus/sonnet/haiku) for agents but don't specify the evaluation model strategy. The dual-Opus design assumes Opus everywhere for evaluation.
**Why:** With the model landscape evolving: Sonnet 4.6 handles most non-critical evaluation tasks well. Opus 4.6 (not 4.5) should be reserved for tasks requiring deep reasoning judgment. Haiku can handle mechanical/low-level evaluation tasks (capability checks, output format validation, tool sequence verification) at much lower cost. This aligns with the investigation/synthesis/mechanical workflow classification from P1-IMP-20. Testing Haiku's quality on granular tasks enables creating small, efficient evaluation workflows without sacrificing quality.
**How:** Add "Model Strategy for Evaluation" section to CONTEXT.md: "Default evaluator model: Sonnet 4.6 (reasoning evaluation, failure narrative generation). Critical evaluator model: Opus 4.6 (Core tier deep evaluation, anchor transcript validation, complex orchestrator coherence). Efficiency model: Haiku (capability checks, format validation, mechanical workflow evaluation). Model selection is per-contract: `evaluation_config.evaluator_model` field, defaulting to sonnet. Quality gate: Before deploying Haiku for any evaluation task, validate it produces equivalent results to Sonnet on 5+ test cases. If quality drops >10% on any dimension, escalate to Sonnet."
**Impacts:** Evaluation cost reduction. 3.1c-06 contracts need `evaluator_model` field. 3.1c-07 evaluator needs model parameter. 3.1c-08 runner must route to correct model.
**Research needed:** yes — Run 5 evaluation prompts through Haiku, Sonnet, and Opus on same transcript. Compare score distributions. 30-minute test. Determines which tasks Haiku handles adequately.
**Confidence:** MEDIUM
**Status:** implemented
**Research summary:** GAP-05 RESOLVED. 7 papers confirm: Opus for critical reasoning eval (~8 workflows), Sonnet for standard reasoning + narratives (~12 workflows), deterministic code for capability checks (~31 workflows). Haiku NOT suitable for any LLM evaluation task — mechanical tasks need code, not LLM. Run one-time calibration (~$2) to validate Sonnet-Opus boundary.

### P1-IMP-27: Temporal Reasoning Trajectory Is a Research Criterion, Not a Shipping Criterion
**What:** PHILOSOPHY.md North Star #9 requires "Temporal reasoning analysis distinguishes hypothesis-first from retrofit reasoning." CONTEXT.md Pillar 1 describes analyzing WHEN agents form hypotheses relative to queries.
**Why:** "Hypothesis-first vs retrofit" is a fascinating research question but not a practical shipping criterion. What matters for the product is: did the agent find the vulnerability with good evidence? Whether it formed the hypothesis before or after the first query is academic. The temporal analysis requires timestamp-level analysis of reasoning patterns, which is complex to implement and validate. The TranscriptParser has timestamps but no temporal analysis code exists.
**How:** Move temporal reasoning analysis from v1 North Star to v2 scope. Replace North Star #9 with: "Evaluation produces per-dimension scores that correlate with finding quality (validated against ground truth correct/incorrect findings)." Keep timestamp recording in transcripts for future temporal analysis.
**Impacts:** PHILOSOPHY.md North Star #9. Reduces 3.1c-03 and 3.1c-07 complexity.
**Research needed:** no
**Confidence:** MEDIUM
**Status:** implemented
```
