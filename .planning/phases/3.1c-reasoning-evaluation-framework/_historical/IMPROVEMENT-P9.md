# Improvement Pass 9

**Pass:** 9
**Date:** 2026-02-19
**Prior passes read:** 1-8 (via IMPROVEMENT-DIGEST.md — all terminal)
**Areas analyzed:** 3 (Architectural Foundations, Evaluation Pipeline Plans 01-08, Test Execution & Improvement Loop)
**Agents:** 3 improvement + 4 adversarial + 1 synthesis
**Focus:** Alignment audit against VISION.md and PHILOSOPHY.md — workflow flexibility, interactive framework philosophy, Claude Code orchestration centrality
**Status:** complete

<!-- File-level status: in-progress | complete -->

## Pipeline Status

<!-- Auto-populated by workflows. Shows pending actions across ALL passes for this phase. -->

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 0 | 0 | — |
| Research | 0 | 0 | — |
| Gaps | 0 | 0 | — |
| Merge-ready | 0 | 20 | — |

**Pipeline:** [discuss] — → [improve] ✓ → [adversarial] ✓ → [synthesis] ✓ → [implement] ✓
**Next recommended:** `/msd:plan-phase` or another `/msd:improve-phase 3.1c` pass

**Verdict summary:** 9 enhanced, 3 confirmed, 4 reframed, 1 rejected, 6 created (adversarial), 2 created (synthesis)
**Net actionable:** 20 (9 enhanced + 3 confirmed + 6 adversarial created + 2 synthesis created)

## Improvements

### P9-IMP-01: PHILOSOPHY.md Pillar 2 Contradicts CONTEXT.md on Evaluation Scope
**Target:** CONTEXT
**What:** PHILOSOPHY.md contains two real contradictions with CONTEXT.md that will mislead planners:

1. **Category/tier mismatch:** Pillar 2 names Investigation / Synthesis/Coordination / Mechanical. CONTEXT.md uses Investigation / Tool Integration / Orchestration / Support plus Core / Important / Standard. The "Mechanical" label does not appear in CONTEXT.md at all — planners cannot resolve which taxonomy wins without reading both documents completely.

2. **LLM evaluation exclusion:** Pillar 2 explicitly says Mechanical gets "capability checks ONLY (deterministic assertions, NO LLM evaluation)." CONTEXT.md says "ALL get reasoning evaluation, no exclusions." These are binary opposites. The "CONTEXT.md wins" escape clause is present in PHILOSOPHY.md but is not a substitute for alignment — it forces every planner to mentally reconcile two contradictory paragraphs.

3. **Contract count:** PHILOSOPHY.md Pillar 2 says "~14 evaluation contracts (10 Core hand-authored + 4 category templates)." CONTEXT.md says "51 per-workflow evaluation contracts." These describe structurally different architectures.

4. **North Star item 1:** PHILOSOPHY.md North Star #1 says "Standard with capability checks." CONTEXT.md Tier table says Standard gets "Lite: capability + focused reasoning evaluator + deterministic checks."

**Why:** PHILOSOPHY.md is labeled "v1 binding constraints." A planner who reads PHILOSOPHY.md first — the natural entry point — will build a Mechanical tier with zero LLM calls, then discover CONTEXT.md says otherwise. The contradiction is not a nuance; it is a load-bearing architectural decision (do ~26 workflows run Opus evaluation or not?). After 8 improvement passes, PHILOSOPHY.md still describes an architecture that was abandoned.
**How:**
1. In PHILOSOPHY.md Pillar 2, replace the Investigation/Synthesis/Mechanical paragraph with the four categories from CONTEXT.md (Investigation, Tool Integration, Orchestration, Support). Replace the tier descriptions with Core/Important/Standard and their evaluation depths as defined in CONTEXT.md. Remove all references to "Mechanical" and "NO LLM evaluation." One paragraph, no ambiguity.
2. In PHILOSOPHY.md Pillar 2, change "~14 evaluation contracts (10 Core hand-authored + 4 category templates)" to "51 per-workflow evaluation contracts. Core (~10) fully tailored. Important (~15) stub + 1 workflow-specific check. Standard (~26) template-derived stubs (full authoring deferred until after first real run)." This matches the Implementation Decision exactly.
3. In PHILOSOPHY.md North Star item 1, change "Standard with capability checks" to "Standard with lite evaluation (capability + focused reasoning evaluator + deterministic checks)." This aligns with the CONTEXT.md tier table.
4. Do NOT rewrite the "CONTEXT.md wins" escape clause — it is correct for future drift. But add one sentence after it: "This document is synchronized with CONTEXT.md as of 2026-02-19. If they diverge again, CONTEXT.md is authoritative."
5. Preserve the Pillar 2 `v1 implementation` note about "Cascade-aware DAG scoring is v2 scope" — it is correct and aligns with VISION.md.
**Impacts:** All plans — PHILOSOPHY.md is labeled "v1 binding constraints"
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Standard document reconciliation
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Philosophy-CONTEXT Reconciliation) — rewritten to target 4 specific contradictions with concrete edits

### P9-IMP-02: Category Rigidity Trap — Smart Selection Matrix Is Category-Driven Despite Per-Workflow Contract Claim
**Target:** CONTEXT
**What (reframed):** The improvement mis-identifies where the rigidity actually lives. The Smart Selection Matrix in CONTEXT.md is already designated as "reference, not runtime dispatch" — CONTEXT.md line 162-169 explicitly states that "Pre-session setup step (NOT the runner) reads contract's `hooks` field." The real rigidity is in Plan 07's 4 prompt templates (CONTEXT.md plan 07: "4 prompt templates by category"), which ARE runtime dispatch and DO hard-code category as the template selector. Additionally, the category enum in the schema (`"enum": ["skill", "agent", "orchestrator"]`) is a coarser taxonomy than the 4 CONTEXT.md categories — 3 schema values map to 4 runtime categories with no declared mapping.
**Why (reframed):** The proposed fix attacks the Smart Selection Matrix when that is already documented as reference-only. The actual runtime dispatch rigidity is in Plan 07's evaluator — a narrower and more fixable target. The schema/taxonomy mismatch (3 vs 4 categories) is a second-order bug the original misses entirely.
**How (reframed):** In Plan 07: replace category-based template selection with dimension-driven selection. `ReasoningEvaluator` reads `reasoning_dimensions` from the loaded contract and selects prompt template sections based on which canonical move types those dimensions map to. The 4 templates become 4 prompt section fragments, composable per contract. The schema `category` field remains as authoring metadata. Requires: (1) a dimension-to-move-type mapping table (~15 LOC), (2) template sections that can be concatenated, (3) contract authoring guide update. ~50 LOC change to Plan 07.
**Impacts:** Plan 07 (evaluator dispatch model)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — Dimension-driven evaluation
**Prerequisite:** no
**Status:** reframed
**Adversarial verdict:** REFRAME (Category Rigidity) — redirected to Plan 07 evaluator dispatch, not matrix. See P9-ADV-2-01 for replacement.

### P9-IMP-03: Architecture Diagram Shows Python-Centric Pipeline, Omits Claude Code Orchestration Layer
**Target:** CONTEXT
**What:** The architecture diagram (lines ~1268-1318) shows a linear Python pipeline with Claude Code appearing only as the hook source at the top. The actual execution model has two distinct orchestration layers: (1) the CC skill `/vrs-test-suite` as the live-mode test orchestrator (spawns Agent Teams, triggers debrief via SendMessage, writes JSONL + exit reports), and (2) the Python evaluation pipeline as the scoring orchestrator (reads those artifacts). The diagram communicates an incorrect mental model where Python is the primary orchestrator in all modes.
**Why:** The Plans 09-11 Architectural Restructuring decision explicitly states that the primary artifact is a CC skill, NOT pytest files. A planner building from the current diagram will under-scope Plans 09-11. Additionally, "simulated mode" replaces Layer 1 with synthetic data — this branching is completely invisible in the current diagram.
**How:**
1. Replace the single ASCII diagram with a dual-layer diagram. Layer 1 (CC, top half): `/vrs-test-suite skill` -> spawns Agent Teams -> hooks fire (JSONL) -> debrief via SendMessage -> writes exit report to `.vrs/evaluations/`. Layer 2 (Python, bottom half): evaluation_runner reads exit report + JSONL -> ObservationParser -> GVS + ReasoningEvaluator -> EvaluationResult -> BaselineManager. Connect layers with a vertical arrow labeled "artifacts (JSONL, exit report)" at the boundary.
2. Add a "simulated mode bypass" callout on Layer 1: "In simulated mode, Layer 1 replaced by synthetic fixture data."
3. Add note: "The CC skill is the test orchestrator in interactive/headless mode. The Python pipeline is the scoring orchestrator. These are separate concerns with a file-artifact boundary between them."
**Impacts:** Plans 09-11 (execution model), Plan 08 (runner scope)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Dual-layer architecture diagrams
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Pipeline Completeness) — added simulated mode bypass callout and artifact boundary label

### P9-IMP-04: Evaluation Contract `hooks` Field Is the Per-Workflow Flexibility Mechanism but Semantics Are Underdefined
**Target:** CONTEXT
**What:** The `hooks` field in evaluation contracts has no definition in the schema (`evaluation_contract.schema.json`), no explicit population in any template, and no enum of valid hook names. The field is referenced in architectural decisions but is a phantom in the actual schema. A mis-named hook in a contract silently installs nothing, producing zero observations with no error — the runner reads the same field passively for "expected observation types," so a wrong hook name means the runner also expects the wrong types, and the mismatch goes undetected.
**Why:** The `hooks` field is the coordination point between pre-session setup (Plan 02) and the runner (Plan 08). Validation must happen in pre-session setup, not the runner — hooks must be installed BEFORE the session starts. If the runner validates, it is too late.
**How:**
1. Add `hooks` property to `evaluation_contract.schema.json` as `type: array, items: {type: string, enum: [PreToolUse, PostToolUse, SubagentStart, SubagentStop, Stop, SessionStart, TeammateIdle, TaskCompleted]}`. Add to `required` in the Schema Hardening atomic commit (Plan 06).
2. Add `hooks` to all 4 category templates with correct defaults: investigation gets `[PreToolUse, PostToolUse, SubagentStart, SubagentStop, Stop]`; tool gets `[PreToolUse, PostToolUse]`; orchestration gets `[PreToolUse, PostToolUse, SubagentStart, SubagentStop, TeammateIdle, TaskCompleted]`; support gets `[Stop]`.
3. Plan 02 pre-session setup validates that every hook name in the contract's `hooks` field has a corresponding `.py` file in `tests/workflow_harness/hooks/` before installing. ~10 LOC guard. If missing, FAIL FAST.
**Impacts:** Plans 02, 06, 08, 09-11. Schema Hardening atomic commit scope expands — all 14 existing files (10 contracts + 4 templates) must be updated simultaneously.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Schema definition for configuration fields
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Category Rigidity) — moved validation to Plan 02 pre-session (not runner), added template defaults, flagged Schema Hardening scope expansion

### P9-IMP-05: VISION.md North Star Items Lack v1/v2 Markers
**Target:** CONTEXT
**Why rejected:** VISION.md's opening block already contains: "This document is NOT binding for 3.1c v1." The non-binding status applies to the entire document, not individual items. Adding per-item (v2) markers implies items WITHOUT a marker are v1 requirements — but the header says nothing in VISION.md is v1 binding. The marker scheme is more confusing than the blanket disclaimer. Additionally, the improvement misidentifies which items need marking: CONTEXT.md Plan 03 explicitly includes temporal reasoning trajectory (v1 scope), so marking item #9 as (v2) would contradict CONTEXT.md. If there is a genuine risk, it belongs in PHILOSOPHY.md's "Deferred to v2" section which already lists specific deferred items.
**Status:** rejected
**Adversarial verdict:** REJECT (Philosophy-CONTEXT Reconciliation)

### P9-IMP-06: DC-2 Import Separation Has No Enforcement Mechanism
**Target:** CONTEXT
**What:** DC-2 specifies that `ReasoningAssessment`, `EvaluationResult`, and `ScoreCard` must not import from `alphaswarm_sol.kg` or `alphaswarm_sol.vulndocs`. No enforcement exists. The constraint must cover three boundary surfaces, not just `models.py`: the evaluation intelligence stubs, the observation parser, and the graph scorer.
**Why:** The proposed grep check is correct but too narrow at one file. The `coverage_radar.py` decision explicitly says "MUST NOT import from `vulndocs`" but this is not wired to any verifiable exit criterion. Each boundary is a separate violation surface.
**How:**
1. In DC-2, add: "Enforcement — three boundaries to check at Plan 01 exit:
   - `grep -r 'from alphaswarm_sol.kg\|from alphaswarm_sol.vulndocs' src/alphaswarm_sol/testing/evaluation/models.py` — zero matches.
   - `grep -r 'from alphaswarm_sol.kg\|from alphaswarm_sol.vulndocs' src/alphaswarm_sol/testing/evaluation/intelligence/` — zero matches.
   - `grep -r 'from alphaswarm_sol.vulndocs' tests/workflow_harness/graders/graph_value_scorer.py` — zero matches."
2. In Plan 01 exit criteria, add hard criterion: "DC-2 import boundaries verified — all three grep checks return zero matches."
3. In Plan 12 Part 5 (`coverage_radar.py`), add comment: "DC-2 verified at Plan 01 exit."
**Impacts:** Plan 01 (exit criteria), DC-2 documentation
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Import boundary enforcement
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Pipeline Completeness) — expanded grep to 3 boundary surfaces

### P9-IMP-07: Plan 04 GVS Has No Explicit Skip Path for Non-Graph Workflows
**Target:** CONTEXT
**What:** Plan 04 builds a scorer with AlphaSwarm-specific dimensions. When `evaluation_config.run_gvs: false`, the scorer behavior is undefined. A non-graph workflow would score 0 (actively penalized), not N/A.
**Why:** DC-2 promises pluggability but Plan 04 never mentions the skip path. The guard must be in TWO places: (1) `ReasoningEvaluator.__init__()` (auto-registration guard), AND (2) `GraphValueScorer.score()` itself should return a `PluginScore` with `applicable=False` when called on non-graph output rather than a 0-score that gets averaged in. The `applicable: bool` field on `DimensionScore` (IMP-25) needs a parallel field on `PluginScore` for this to work end-to-end.
**How:**
1. In Plan 04 deliverables, add: "When `run_gvs: false` in contract, scorer returns `GraphValueScore` with all dimensions `applicable=False`. No transcript parsing attempted. ~5 LOC guard."
2. In DC-2, clarify: "GraphValueScorer is the first EvaluationPlugin instance. Non-graph scorers register as separate plugins."
3. In Plan 01 scope, add `applicable: bool = True` to `PluginScore` alongside `DimensionScore` to prevent `_compute_overall()` from including 0-score GVS results in weighted average for non-graph workflows.
**Impacts:** Plan 04 gains ~5 LOC. Plan 01 gains `PluginScore.applicable`. DC-2 documentation clarified.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Plugin skip pattern
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** CONFIRM (Category Rigidity) — flagged `PluginScore.applicable` gap as second-order fix needed in Plan 01

### P9-IMP-08: Contract Count "51" Is Unachievable Given "Standard Tier Deferred" Policy
**Target:** CONTEXT
**What:** Plan 06 exit criterion says "51 contracts" but Tiered Contract Authoring Policy says Standard (~26) are "Defer authoring until after at least 1 real run." These contradict. The Phase exit criterion at line ~1454 already has clarified language ("Standard have correct workflow_id + schema-valid structure") — it implicitly accepts stubs. But the Plan 06 exit criterion says only "51 contracts" with no stub qualifier.
**Why:** A planner implementing Plan 06 reads the Plan exit criterion first, sees "51 contracts," reads the deliverables, sees "Standard deferred," and faces a contradiction.
**How:**
1. In Plan 06 exit criteria, change to: "51 contract files exist; Core (~10) fully tailored; Important (~15) have template + 1 workflow-specific check; Standard (~26) are template-derived stubs marked `status: stub`."
2. In Tiered Contract Authoring Policy, clarify: "Standard: Create template-derived stubs during Plan 06. Full authoring deferred until after at least 1 real run."
**Impacts:** Plan 06 exit criteria become achievable. Plan 07 evaluator needs defined behavior when loading a stub contract — should skip Standard contracts with `status: stub` in pre-real-run phases.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Tiered rollout
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** CONFIRM (Philosophy-CONTEXT Reconciliation) — stub interpretation explicit, consistent with Phase exit criterion

### P9-IMP-09: Evaluator Debate Cost Underestimated — No Total Wall-Clock Estimate for Core Suite
**Target:** CONTEXT
**What:** CONTEXT.md has a critical internal contradiction. The Evaluator Debate Protocol says "IMP-03 wall-clock estimates must account for this" — but IMP-03 resolves to "Intelligence Module Integration Constraints," which does not contain wall-clock estimates. The cross-reference is broken. Plan 08 deliverable 6 gives only bare cadence labels with no minute figures. Additionally, the opt-in mechanism needs a concrete field name, not just the concept.
**Why:** The broken IMP-03 cross-reference is the most dangerous failure mode — planners will follow it and find nothing. Without a concrete flag name for debate opt-in, two implementers could choose different surface areas, breaking CC skill and Python runner interoperability.
**How:**
1. In Plan 08 deliverable 6, replace bare cadence labels with: "Fast regression (Core, debate disabled): ~60-90 min. Core-with-debate: ~3-4 hours. Full suite (all 51, debate disabled): ~8-12 hours. Recommended: fast daily, debate-enabled 2x/week (not daily)." State derivation so estimates can be updated.
2. In Evaluator Debate Protocol, add the specific opt-in surface: "`debate_enabled` controlled by (a) `evaluation_config.debate_enabled: bool` in evaluation contract (per-workflow) and (b) `--debate` CLI flag (suite-wide override). Contract field wins when both present. Default: `false`."
3. Fix the broken cross-reference: replace "IMP-03 wall-clock estimates must account for this" with "Plan 08 deliverable 6 wall-clock estimates must account for this."
**Impacts:** Plan 08 cadence guidance. Debate Protocol gains opt-in semantics. See P9-ADV-3-01 for baseline key impact.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4 — CI cadence tiers
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Operational Feasibility) — fixed broken IMP-03 cross-reference, named concrete `debate_enabled` field

### P9-IMP-10: Plan 01 Lists Adapters with Logic Among Pure Data Models
**Target:** CONTEXT
**What:** Plan 01 deliverable 7 lists `GroundTruthAdapter.normalize()` (~30 LOC) and `AgentFindingNormalizer` (~20 LOC) as data models. These contain transformation logic, not just type definitions.
**Why:** Implementing adapters in Plan 01 without Plan 03's validation context risks building against wrong assumptions. Plan 03 already validates the adapter. The dependency arrow is Plan 01 -> Plan 03, and Plan 03 validates what it also should implement.
**How:**
1. In Plan 01 deliverable 7, split: Plan 01 defines `GroundTruthEntry` and `NormalizedFinding` as Pydantic types. Plan 03 implements `GroundTruthAdapter` class with `normalize()` using those types.
2. Same for `AgentFindingNormalizer` — type signature in Plan 01, implementation in Plan 03/09.
**Impacts:** Plan 01 stays focused on types. Plan 03 gains ~50 LOC.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4 — Separating type definitions from logic
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** CONFIRM (Pipeline Completeness) — dependency chain validated, Plan 03 exit criterion already covers GroundTruthAdapter validation

### P9-IMP-11: Reasoning Move Taxonomy Is Investigation-Locked Despite Flexibility Mandate
**Target:** CONTEXT
**What (reframed):** The improvement correctly identifies that tool integration workflows receive only 2 of 7 reasoning moves. But the proposed solution (`custom_moves` extension) is the wrong abstraction. The existing 7-move enum already contains all needed moves — the problem is that only 2 are mapped as applicable to tool workflows based on category-driven defaults. The assumption that tool workflows don't hypothesize or self-critique is wrong: a tool coordinator deciding WHICH tool to run is performing HYPOTHESIS_FORMATION. Conflicting Slither and Aderyn findings require CONTRADICTION_HANDLING.
**Why (reframed):** Adding `custom_moves` increases schema complexity and creates a validation split (canonical moves use enum validation; custom moves use registry validation) for a problem that doesn't require new vocabulary. The fix is to make per-workflow applicability the contract author's responsibility via the existing `reasoning_dimensions` field. The "Orchestration: Subset TBD" (IMP-16) is the same structural problem — an unresolved applicability assignment, not a missing vocabulary problem.
**How (reframed):** Remove the `custom_moves` proposal. Instead, update the Dimension Registry decision: for each of the 7 canonical moves, document DEFAULT applicability per category. The contract's `reasoning_dimensions` field supports per-workflow override. Add schema support for an `applicable_moves` field on each dimension entry. No new move types needed. ~0 schema changes, ~30 LOC in Plan 07, 1 CONTEXT.md decision update.
**Impacts:** Plan 07 (applicability logic)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — Core + per-contract override pattern
**Prerequisite:** no
**Status:** reframed
**Adversarial verdict:** REFRAME (Category Rigidity) — eliminated custom_moves in favor of per-contract applicability overrides. See P9-ADV-2-02 for replacement.

### P9-IMP-12: Plan 12 Delivers Batch Baseline, Not VISION.md's Living System — Gap Should Be Acknowledged
**Target:** CONTEXT
**What (reframed):** The real problem is not missing documentation — it is that Plan 12 is a manually-triggered improvement loop that is never described as such. The kill.signal / SIGINT / progress.json mechanisms constitute an implicit re-evaluation workflow with no defined trigger. A USAGE.md document tells a human what to type but does not close the gap between "batch tool" and "living system."
**Why (reframed):** The trigger ambiguity means Plan 12 Part 3 metaprompting loop has no defined entry point — a human might run it after a hunch rather than after a detected regression. Making the manual trigger protocol binding prevents Plan 12 from being delivered as a one-shot calibration tool never run again.
**How (reframed):**
1. Acknowledge the batch nature in Plan 12 summary: "v1 is a manually-triggered improvement loop, not an automated re-evaluation system."
2. In Deferred Ideas, promote trigger description to specific: "v2 trigger: git post-commit hook on `.claude/skills/` + `.claude/agents/` paths writes `pending_reeval.yaml`; Plan 12 Part 1 reads this at startup and re-runs only affected workflows."
3. The USAGE.md addition is still useful but is a consequence of acknowledging batch nature, not the solution.
4. Exit Gate 17 addition: "completed cycle must produce documented MANUAL re-evaluation procedure."
**Impacts:** Plan 12 (scope clarification), Exit Gate 17
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Ops runbook documentation
**Prerequisite:** no
**Status:** reframed
**Adversarial verdict:** REFRAME (Pipeline Completeness) — problem is operational (no trigger), not documentary. See P9-ADV-4-01 for replacement.

### P9-IMP-13: Exit Gates 18-19 (Detection Accuracy) Have No Failure Protocol
**Target:** CONTEXT
**What:** Exit gates 18-19 require Tier A recall >= 60% and Tier B recall >= 40% with no failure protocol. The failure protocol must distinguish three distinct failure modes: (1) corpus quality failure — patterns have no BSKG representation (infrastructure miss), (2) pattern granularity failure — 2-3 patterns account for most misses (VulnDocs issue), (3) agent capability failure — misses distributed across patterns (prompt issue). Plan 12 Part 3 convergence detection will burn N=5 cycles on prompt changes even if the root cause is infrastructure-level.
**Why:** Without failure mode distinction, hitting an accuracy wall causes unbounded time sink. Running N=5 improvement cycles against infrastructure misses wastes ~25 hours (5 cycles * 5 variants * ~1 hour each).
**How:**
1. After exit gate 19, add "Detection Accuracy Failure Protocol" with three branches:
   - **Branch A (infrastructure miss):** If IMP-17's diagnostic flags >= 5 patterns as infrastructure misses, HALT prompt improvement for those patterns. File issues against Plan 04 or VulnDocs. Exclude from gate computation and recompute.
   - **Branch B (pattern concentration):** If >= 50% of missed detections cluster on <= 3 patterns after 3 improvement cycles, flag for VulnDocs improvement. Do not lower gate. Resume after fix.
   - **Branch C (distributed agent failure):** If misses distributed across >= 10 patterns and Tier A recall < 50% after 3 cycles, lower gate to `measured_recall + 10%` (minimum floor: Tier A 45%, Tier B 30%) with mandatory drift log entry.
2. In Plan 12 Part 0, add: "Run infrastructure diagnostic before first improvement cycle. Output: per-pattern classification. Exclude infrastructure misses from gate computation."
3. In Exit Gate 18, add parenthetical: "Excluding patterns classified as infrastructure misses per Detection Accuracy Failure Protocol."
**Impacts:** Plan 12 gains failure handling. Coupled with P9-IMP-17 — must implement together.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Threshold adjustment protocols
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Pipeline Completeness) — 3-branch failure protocol with distinct escalation paths

### P9-IMP-14: Plans 09-11 Missing Wall-Clock Budget and Per-Workflow Abort Criteria
**Target:** CONTEXT
**What:** This improvement conflates two distinct problems: (a) missing wall-clock estimates for planners (documentation gap), (b) timeout enforcement in CC skills (architectural constraint). CC skills cannot interrupt in-progress Tasks — a skill can check elapsed time between tool calls but cannot interrupt an in-progress subagent. The kill-file mechanism (`.vrs/evaluations/kill.signal`) is a Python runner mechanism, not CC skill mechanism.
**Why:** Without enforcement specificity, implementers will either skip timeout entirely or build a mechanism that silently does nothing when the subagent is already running. The unaddressed failure mode: CC skill spawns a Task, subagent runs 45+ minutes, Python runner's SIGINT kills itself, but the CC skill session continues unaffected, accumulating unbounded cost.
**How:**
1. In Shared Execution Note (Plans 09-11), add budget estimates: "Core sub-wave (~10 workflows, no debate): ~7.5 hours (45 min/workflow). Core with debate: ~10-12.5 hours. Important: ~11 hours. Standard: ~10 hours. Total staged execution: 3-4 days across sub-waves."
2. In Plan 08 deliverable 11, split timeout into two paths:
   - Python runner path (existing): SIGINT handler calls `os.kill(_current_session_pid)` then writes progress.
   - CC skill path (new): between workflow iterations, check `elapsed > per_workflow_budget` (default 2700s = 45 min). If exceeded, write `status: interrupted` to exit report, proceed to next. This is a "check before start" pattern, not "interrupt in-progress."
3. In Plan 08 deliverable 11, clarify: "The CC skill cannot interrupt a running subagent Task mid-execution. The timeout is enforced by refusing to start the next workflow when cumulative budget is exceeded. In-progress subagents run to completion regardless."
4. Add cost monitoring note: "Recommend running sub-waves in separate CC sessions to bound per-session cost and enable resumption."
**Impacts:** Plan 08 (enforcement), Plans 09-11 (expectations)
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3 — Timeout in CC skills is novel territory
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Operational Feasibility) — distinguished "check before start" (feasible) from "interrupt mid-execution" (not feasible)

### P9-IMP-15: Intelligence Module LOC Estimates Are Unrealistically Low
**Target:** CONTEXT
**What (reframed):** The LOC estimates are not the problem. Three separate authoritative sources give different numbers for the same modules:
- IMP-03 (line 293): "Revised LOC: ~350 (200 module + 150 guards)"
- Plan 12 Part 5 (line 1184): "tier_manager ~50, contract_healer ~30-50, coverage_radar ~150-200" (sum: 230-300)
- Intelligence Layer table (lines 1249-1252): matches Plan 12 Part 5

The gap (50-120 LOC) is labeled "guards" in IMP-03 but guards are not itemized or assigned to any module. A planner will produce contradictory scope estimates from the same document.
**Why (reframed):** Updating numbers with different estimates moves the problem — in two passes someone will challenge the new numbers. The real defect is internal inconsistency: three locations, three different totals. Fixing consistency is actionable and verifiable. Revising specific numbers is a guess.
**How (reframed):** See P9-ADV-3-02 — consolidate sources before revising numbers.
**Impacts:** Plan 12 scope estimate.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Status:** reframed
**Adversarial verdict:** REFRAME (Operational Feasibility) — 3-source inconsistency is the real problem, not magnitude. See P9-ADV-3-02 for replacement.

### P9-IMP-16: Orchestration Move Applicability Still "TBD" After 8 Passes
**Target:** CONTEXT
**What:** CONTEXT.md Plan 07 summary states "Orchestration: Subset TBD per prompt template" — Plan 07 cannot be implemented without knowing which moves apply. The proposed set: EVIDENCE_INTEGRATION, CONCLUSION_SYNTHESIS, SELF_CRITIQUE, CONTRADICTION_HANDLING (DEFAULT_ON, not conditional).
**Why:** CONTRADICTION_HANDLING must be DEFAULT_ON for orchestration, not conditional on "when agents disagree." If scored only when agents disagree, the dimension becomes non-comparable across runs — some evaluations include it, others don't. For baseline regression (Plan 12), dimensions must be consistently scored or excluded.
**How:**
1. Update CONTEXT.md Plan 07 summary: replace "Orchestration: Subset TBD" with "Orchestration: EVIDENCE_INTEGRATION + CONCLUSION_SYNTHESIS + SELF_CRITIQUE + CONTRADICTION_HANDLING." All DEFAULT_ON.
2. Update `template-orchestration.yaml` `reasoning_dimensions` to list these 4 move-type names alongside existing domain dimensions.
3. In Plan 07 evaluator: HYPOTHESIS_FORMATION and QUERY_FORMULATION receive `applicable: False` automatically for orchestration. Do not require contract authors to set these.
**Impacts:** Plan 07 (orchestration template now specifiable), Plan 11 (alignment). Note: updating template triggers Schema Hardening scope expansion — must batch with P9-IMP-04.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — Mapping reasoning skills to orchestration
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Category Rigidity) — CONTRADICTION_HANDLING DEFAULT_ON, Schema Hardening batch requirement

### P9-IMP-17: Deferred Pattern Diagnostic Is Actually Critical for Exit Gates 18-19
**Target:** CONTEXT
**What:** For each VulnDocs pattern where recall < 30% across all 4 Core investigation agents after Part 0 calibration, run a 2-step infrastructure diagnostic: (a) `alphaswarm query "pattern:{pattern_id}"` on corpus contracts — if 0 results where ground truth expects detection, flag as BSKG infrastructure miss; (b) `alphaswarm vulndocs list --pattern {pattern_id}` — if no entry or `status: draft`, flag as VulnDocs miss. The diagnostic must produce a machine-readable exclude list that Part 3 reads before selecting improvement targets.
**Why:** Without the machine-readable output, the diagnostic produces a report a human might not read before starting 3-5 improvement cycles. The exclude list makes exclusion structural, not procedural — consistent with existing `pending_tier_changes.yaml` pattern.
**How:**
1. In Plan 12 Part 0, add: "Infrastructure diagnostic (~30 LOC): Output `.vrs/evaluations/infrastructure_misses.yaml` with per-pattern classification: `{pattern_id, miss_type: bskg_gap|vulndocs_gap|addressable, evidence}`."
2. In Plan 12 Part 2: "Read `infrastructure_misses.yaml` at startup. Skip `bskg_gap` and `vulndocs_gap` patterns in improvement target selection."
3. In Plan 12 Part 3: "Metaprompting targets exclude infrastructure-miss patterns. No Experiment Ledger entries for infrastructure misses."
4. Update Deferred Ideas: "Full feedback loop deferred (IMP-21). Infrastructure diagnostic classification is Plan 12 Part 0 scope."
5. In Plan 12 Part 0 description: add "Deliverables: (a) calibration anchor (existing), (b) infrastructure diagnostic — produces `infrastructure_misses.yaml`."
**Impacts:** Plan 12 Part 0 gains ~30 LOC. Coupled with P9-IMP-13 — must implement together. Plan 12 Part 0 must complete before Part 2 (sequential ordering constraint).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — Root cause triage before optimization
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Pipeline Completeness) — added machine-readable `infrastructure_misses.yaml` output, coupled with IMP-13

---

## Created Items (Adversarial Review)

### P9-ADV-1-01: PHILOSOPHY.md "Deferred to v2" List Does Not Include All Items from CONTEXT.md Two-Tier Decision
**Target:** CONTEXT (PHILOSOPHY.md)
**What:** PHILOSOPHY.md "Deferred to v2" says Rule K (self-healing = contract_healer) and Rule L (coverage radar) are "deferred to v2." But CONTEXT.md implements real v1 versions of both: `contract_healer.py` (~30-50 LOC real v1), `coverage_radar.py` (~150-200 LOC real v1). These are "v1 REAL" in the Intelligence Module table. PHILOSOPHY.md is more conservative than CONTEXT.md.
**Why:** Same contradiction pattern as P9-IMP-01 but in the opposite direction. Fixing Pillar 2 without fixing the Deferred section leaves a second contradiction in the binding document.
**How:**
1. Change Rule K from "self-healing contracts" to "full self-healing contracts with automated proposals queue — v1 has real contract_healer with statistical detection, propose-only, no auto-apply."
2. Change Rule L from "live coverage radar" to "live coverage radar with scenario synthesis integration — v1 has real coverage_radar with 4-axis cross-referencing, reporting-only (no synthesis)."
3. Keep Rules M, N, O as fully deferred — no v1 implementation in CONTEXT.md.
**Source:** Adversarial review (Philosophy-CONTEXT Reconciliation)
**Cross-references:** P9-IMP-01
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

### P9-ADV-2-01: Dimension-to-Move-Type Mapping Layer Missing
**Target:** CONTEXT (Plan 07 scope addition)
**What:** Plan 07 must add a dimension-to-move-type mapping table before implementing dimension-driven template dispatch. The 7 canonical move types and the domain dimensions in `dimension_registry.yaml` (~6-8 entries) are separate vocabularies. Without a declared mapping, every dimension that doesn't match a move-type name falls through to heuristic scoring — the `_heuristic_dimension_score()` already shows 12 keyword branches, exponentially unmaintainable.
**Why:** Neither IMP-02 nor IMP-11 names this mapping as a concrete artifact. IMP-02 proposes "dimension-driven template registry" without specifying what it maps FROM. The gap is the bridge between the two vocabularies.
**How:** Add to Plan 07 scope: define `DIMENSION_TO_MOVE_TYPES: dict[str, list[str]]` in `reasoning_evaluator.py`. Example: `{"graph_utilization": ["QUERY_FORMULATION", "RESULT_INTERPRETATION"], "evidence_quality": ["EVIDENCE_INTEGRATION", "CONCLUSION_SYNTHESIS"]}`. Evaluator uses this map to select prompt template sections. Unmapped dimensions fall back to heuristic with logged warning. ~20 LOC, zero schema changes.
**Source:** Adversarial review (Category Rigidity)
**Cross-references:** P9-IMP-02, P9-IMP-11
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

### P9-ADV-2-02: Per-Move Default Applicability Table Missing from CONTEXT.md
**Target:** CONTEXT
**What:** CONTEXT.md locks 7 canonical move types as schema enum but does not specify which moves are applicable by default for each workflow category. Plan 07 is left with "Orchestration: Subset TBD" and Tool=2 moves only.
**Why:** Score comparability is a hard requirement for the regression baseline (Plan 12). Without a declared applicability table, individual contract authors make inconsistent decisions, producing incomparable scores. This resolves both IMP-11 (move extensibility) and IMP-16 (orchestration TBD) as a single decision.
**How:** Add a "Move Type Default Applicability" Implementation Decision with a 4-row x 7-column table (Investigation, Tool, Orchestration, Support x 7 move types). Mark each cell DEFAULT_ON, DEFAULT_OFF, or CONTEXT_DEPENDENT (with condition). Plan 07 reads this table. Individual contracts override via explicit dimension entries with `applicable: false`. ~1 CONTEXT.md table, ~20 LOC in Plan 07.
**Source:** Adversarial review (Category Rigidity)
**Cross-references:** P9-IMP-11, P9-IMP-16
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

### P9-ADV-3-01: Debate-Enabled Flag Must Be a Baseline Key Dimension
**Target:** CONTEXT
**What:** Plan 12 baseline is keyed by `(workflow_id, run_mode)`. If `debate_enabled` is added (per P9-IMP-09), runs with debate produce systematically different scores. If both configurations write to the same baseline key, regression detection will fire false positives whenever the debate flag changes.
**Why:** The Mode Capability Matrix already established that different evaluation configurations are incomparable baselines. Debate is a third comparability dimension.
**How:**
1. Add `debate_enabled: bool` as third baseline key dimension: `(workflow_id, run_mode, debate_enabled)`.
2. Update `BaselineKey` model (Plan 01): add `debate_enabled: bool = False`.
3. In Plan 12 Part 1: establish baseline for each combination. Minimum: all Core with `(interactive, False)` and `(interactive, True)`.
4. In Mode Capability Matrix: "Debate-enabled runs produce distinct baseline entries. Do not mix."
**Source:** Adversarial review (Operational Feasibility)
**Cross-references:** P9-IMP-09
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

### P9-ADV-3-02: Intelligence Module LOC — Establish One Authoritative Breakdown
**Target:** CONTEXT
**What:** Three locations give different total LOC figures: IMP-03 says ~350 (200 + 150 guards), Plan 12 Part 5 sums to ~230-300, Intelligence Layer table matches Part 5. The "guards" component (50-120 LOC gap) is not defined or assigned to any module.
**Why:** IMP-03 is in "Implementation Decisions (Locked)" — it has precedence. But planners reading Plan 12 may not realize this. Consolidating sources before revising numbers makes the revision a single-location update.
**How:**
1. Make IMP-03 the single authoritative source. Plan 12 Part 5 and Intelligence Layer table reference it: "See IMP-03 for LOC breakdown."
2. In IMP-03, itemize the "guards" component — specify which module(s) and what "guard" means (input validation? thresholds? YAML I/O?).
3. Add Plan 12 exit criterion: "intelligence/ directory total LOC within 20% of IMP-03 estimate — document discrepancy if exceeded."
**Source:** Adversarial review (Operational Feasibility)
**Cross-references:** P9-IMP-15
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

### P9-ADV-4-01: Living System Gap — v1 Manual Trigger Protocol Decision
**Target:** CONTEXT
**What:** Add an Implementation Decision named "v1 Manual Trigger Protocol" making the batch nature of Plan 12 explicit with exact manual steps for re-evaluation. Replaces vague USAGE.md proposal with a binding protocol.
**Why:** The distinction between "has a USAGE.md" and "has a binding operational protocol in Implementation Decisions" matters because planners use Implementation Decisions as constraints. A trigger protocol prevents Plan 12 from being delivered as a one-shot calibration tool.
**How:** Add Implementation Decision: "Plan 12 is a manually-triggered improvement loop, NOT an automated re-evaluation system. Re-evaluation trigger: (1) human runs `alphaswarm evaluation summary --format json` to identify affected workflows, (2) human runs `/vrs-test-suite --tier core --workflow affected_id` in a new CC session, (3) human inspects exit report delta against `BaselineManager` rolling window. Automated trigger (v2): file watcher or git post-commit hook on `.claude/skills/` + `.claude/agents/` paths. Do NOT design Plan 12 as if re-evaluation triggers automatically."
**Source:** Adversarial review (Pipeline Completeness)
**Cross-references:** P9-IMP-12
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

---

## Cross-Group Conflicts (Adversarial Review)

1. **P9-IMP-04 + P9-IMP-16 + P9-ADV-2-02:** All touch Schema Hardening atomic commit (Plan 06). If IMP-04 adds `hooks` to required, IMP-16 adds move-type dimensions to templates, and ADV-2-02 adds applicability structure — all must land in same commit or intermediate states break schema validator.

2. **P9-IMP-13 + P9-IMP-17:** Tightly coupled — failure protocol's Branch A requires the diagnostic's exclude list. Must implement together.

3. **P9-IMP-09 + P9-ADV-3-01:** Debate flag without baseline key update produces polluted regression signals immediately. Must implement together.

4. **P9-IMP-02 (reframed) + P9-ADV-2-01:** ADV-2-01 (mapping layer) is a prerequisite for the dimension-driven dispatch concept from IMP-02.

## Second-Order Risks (Adversarial Review)

1. **PluginScore.applicable gap** (from IMP-07): `_compute_overall()` will include 0-score GVS results in weighted average for non-graph workflows unless `PluginScore` gains `applicable: bool`. Plan 01 scope must be updated.

2. **Schema Hardening scope creep:** Current scope targets 10+4 files. IMP-04 + IMP-16 + ADV-2-02 all expand the retrofit list. Must batch or intermediate states break validator.

3. **Debate baseline pollution:** If IMP-09 lands without ADV-3-01, Plan 12 regression detection is polluted from first run with different debate setting.

4. **CC skill timeout misimplementation:** IMP-14 must clearly specify "check before start" not "interrupt mid-execution" — CC skills cannot interrupt running Tasks.

5. **Broken IMP-03 cross-reference:** CONTEXT.md's Debate Protocol references "IMP-03 wall-clock estimates" which is a dead pointer. Systemic risk of other dead IMP-XX references.

---

## Synthesis Items

### P9-SYN-01: Schema Hardening Needs a Field Manifest — Multiple Items Independently Discover Phantom Schema Fields
**Target:** CONTEXT
**What:** Four items across three review groups independently discover that CONTEXT.md Implementation Decisions reference evaluation contract fields that do not exist in the schema: P9-IMP-04 (hooks field), P9-IMP-08 (status field for stubs), P9-IMP-09 (debate_enabled field), P9-ADV-2-02 (applicable_moves structure). Each item proposes adding its field to the schema. The Schema Hardening atomic commit was originally scoped to 3 fixes (evaluation_config required, inner required, additionalProperties) across 14 files. These 4 items expand the commit scope by 4 additional fields with no tracking mechanism to ensure all are included.
**Why:** Addressing each field addition individually risks partial implementation: if 3 of 4 fields land in the atomic commit and the 4th is missed, the contract files validated against the new schema will fail on the next pass when the 4th field is added. More critically, without a manifest the Schema Hardening commit has no definition of "complete" — it keeps growing as improvement passes discover more phantom fields. A single manifest makes the scope explicit, auditable, and closeable.
**How:**
1. Add a "Schema Hardening Field Manifest" subsection to the existing Schema Hardening Implementation Decision in CONTEXT.md. List every field that must be added in the atomic commit: `evaluation_config` (existing), `evaluation_config.run_gvs` (existing), `evaluation_config.run_reasoning` (existing), `evaluation_config.debrief` (existing), `evaluation_config.depth` (existing), `evaluation_config.debate_enabled` (P9-IMP-09), `hooks` (P9-IMP-04), `status` with enum `[active, stub]` (P9-IMP-08), `reasoning_dimensions` applicability entries (P9-ADV-2-02), `coverage_axes` (Plan 06 deliverable 5). Mark each with source item ID.
2. Add Plan 06 exit criterion: "All fields in Schema Hardening Field Manifest are present in schema, all 14 files (10 contracts + 4 templates) validate against updated schema, no field from manifest is missing."
3. Add a note: "Future improvement passes that discover new phantom fields must add them to this manifest, not propose standalone schema changes."
**Impacts:** Plan 06 (exit criteria, scope definition), Plan 01 (any new model fields implied by schema changes)
**Components:** P9-IMP-04, P9-IMP-08, P9-IMP-09, P9-ADV-2-02
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)

### P9-CSC-01: Infrastructure Miss Exclusion Can Collapse Gate Denominator
**Target:** CONTEXT
**What:** P9-IMP-13 (enhanced) adds a Detection Accuracy Failure Protocol where Branch A excludes infrastructure-miss patterns from exit gate 18-19 computation. If the infrastructure diagnostic (P9-IMP-17) classifies a large fraction of the 77 ground truth patterns as infrastructure misses (BSKG gaps or VulnDocs gaps), the gate denominator shrinks. With 77 patterns total, if 50+ are excluded, the gate computes recall over fewer than 27 patterns. In the extreme case (e.g., 70 excluded), recall is computed over 7 patterns where getting 5 right yields 71% — trivially passing the 60% gate while the system detects almost nothing.
**Why:** The failure protocol correctly identifies that infrastructure misses should not block prompt improvement. But it creates a new failure mode: the gate becomes meaningless when the denominator is too small. The current 10 uncatalogued patterns (Prestep P6) already reduce the effective pool. Adding infrastructure exclusions compounds this. No existing item addresses a minimum denominator.
**How:**
1. In the Detection Accuracy Failure Protocol (after Branch A), add: "Denominator floor: if infrastructure exclusions reduce the addressable pattern count below 20 for Tier A or 15 for Tier B, the gate CANNOT be satisfied by exclusion alone. Instead, the gate is SUSPENDED with a mandatory action item to resolve infrastructure gaps before re-attempting. Log to drift-log.jsonl with reason `gate_suspended_low_denominator`."
2. In Exit Gate 18 parenthetical, extend: "Excluding patterns classified as infrastructure misses per Detection Accuracy Failure Protocol, subject to minimum denominator floor (20 Tier A, 15 Tier B)."
**Impacts:** Plan 12 (failure protocol), Exit Gates 18-19
**Trigger:** P9-IMP-13
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

---

## Post-Review Synthesis
**Items created:** P9-SYN-01, P9-CSC-01
**Key insight:** The Schema Hardening atomic commit is accumulating undeclared fields from multiple independent improvement items with no manifest to track completeness -- adding a field checklist prevents partial implementation. Additionally, the infrastructure-miss exclusion mechanism in the detection accuracy failure protocol needs a denominator floor to prevent the gate from becoming trivially passable when many patterns are classified as infrastructure gaps.
