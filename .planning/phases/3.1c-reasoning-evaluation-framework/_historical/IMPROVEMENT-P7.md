# Improvement Pass 7

**Pass:** 7
**Date:** 2026-02-19
**Prior passes read:** 1-5 (via IMPROVEMENT-DIGEST.md), 6 (active file)
**Areas:** Self-Improving Interactive Framework Architecture, Pattern Testing & Static Analysis Integration, Evaluation Pipeline & Execution Infrastructure
**Agents spawned:** 3 improvement + 3 adversarial
**Status:** complete

<!-- File-level status: in-progress | complete -->

## Pre-Implementation Summary (2026-02-19)

**Commit:** cc1a4bb7

4 prerequisites found (items with `Status: prerequisite`):

| ID | Scope | Outcome | Detail |
|----|-------|---------|--------|
| P7-IMP-13 | MEDIUM | Not pre-implementable | Finding-merger input schema needs architectural decision (JSON format, dedup algorithm, severity reconciliation). Route as Known Code Issue. |
| P7-IMP-20 | SMALL | **Pre-implemented** | Aderyn v0.6.8 installed (pre-built binary). Verified parseable JSON on corpus contract (5 results → 7 VKG findings). Adapter mapping stale (v0.6.8 detector names differ). Mythril: pip crashes (pkg_resources), Docker not running. Aderyn unblocked, Mythril deferred. |
| P7-IMP-23 | MEDIUM | Not pre-implementable | Blocked by unimplemented P6-IMP-10 (fcntl.flock) + architectural PoC needed for polling+SendMessage interleaving. Two compounding blockers. |
| P7-IMP-26 | MEDIUM | Not pre-implementable | contract_healer.py does not exist (Plan 12 scope). Circular dependency: Plan 06 gate → Plan 12 code → Plan 06 contracts. Route to Plan 08 per adversarial note. |

### Pre-Implementation Pass 2 (2026-02-19)

3 remaining prerequisite items re-assessed after research resolution:

| ID | Scope | Outcome | Detail |
|----|-------|---------|--------|
| P7-IMP-13 | SMALL | **Resolved → route as Known Code Issue** | Research answered the architectural question: extend `SemanticDeduplicator`, not the merger agent. `deduplicate_findings()` already accepts `List[Dict]` with the exact key mapping needed. Remaining work: define which `InvestigationResult` fields map to VKGFinding dict keys (file/line extraction from `evidence[]` or `step_results`). ~20 LOC mapping function. Status contradictions fixed (prereq field said `no`, status said `prerequisite`). Demoted to Known Code Issue — no blocker for scenario authoring. |
| P7-IMP-23 | MEDIUM | **Resolved → defer to v2** | Research resolved NEGATIVE: hooks cannot read their own session's JSONL mid-session. Each hook is a stateless subprocess; `threading.Lock` provides zero cross-process protection; CC cannot poll and SendMessage simultaneously. Alternative A (signal-file with PreToolUse hook on orchestrator) is viable but requires reframe + P6-IMP-10 landing. Batch-only architecture accepted for v1. Item reframed to `deferred`. |
| P7-IMP-26 | MEDIUM | **Resolved → route to Plan 08** | contract_healer.py does not exist (Plan 12 scope). Circular dependency confirmed: Plan 06 exit criterion would require Plan 12 component. Adversarial note's resolution accepted: extract basic anomaly detection (ceiling/floor/zero-variance) into Plan 08 as post-run analysis after 5th Core run. Plan 06 exit criterion is wrong target; Plan 08 exit criterion is correct. Item reframed with Plan 08 routing. |

**New findings discovered during pre-implementation pass 2:**
1. **P7-IMP-13 status contradiction:** `Status: prerequisite` but `Prerequisite: no` (after research resolution). The contradiction exists because research resolved the architectural question but the pre-implement note was never updated. Fixed: status changed to `researched`, prereq field removed.
2. **`deduplicate_findings()` dict acceptance is complete:** Lines 690-714 in `dedup.py` already handle `List[Dict[str, Any]]` input with fallback defaults for all VKGFinding fields. The "agent finding to dict" mapping is NOT a SemanticDeduplicator change — it is a thin adapter function that extracts file/line/function/category from `InvestigationResult.evidence` and `step_results` into the dict format that `deduplicate_findings()` already consumes.
3. **P7-IMP-23 alternatives clarified:** Alternative A (signal-file architecture) is architecturally sound but requires: (a) new hook type on orchestrator session (PreToolUse), (b) signal-file writer in target session hooks, (c) P6-IMP-10 for cross-process write safety. This is ~80 LOC across 3 files — genuinely v2 scope.

**Action items for next pass or implementation:**
- Update `AderynAdapter.DETECTOR_TO_PATTERN` for v0.6.8 detector names
- Fix `_parse_src` to handle offset-based `src` format (or verify Aderyn's `--output` flag produces file-prefixed src)
- Add mythril to `tool_registry.py` VERSION_PATTERNS for consistent display
- Mythril runtime: either add `setuptools` to mythril's uv tool venv, or document Docker as required
- P7-IMP-13: Add Known Code Issue "Agent finding → VKGFinding dict mapping undefined" to CONTEXT.md (owner: Plan 09-10 merge scenarios)
- P7-IMP-26: Add Plan 08 task "Post-run anomaly detection after 5th Core run" to CONTEXT.md plan summary

## Improvements

---

## Group A: Self-Improving Interactive Framework Architecture

### P7-IMP-01: The Improvement Loop Is Wave 7 But Should Be the Architectural Spine — Define Data Contracts in Wave 1 AND Split Plan 12 for Early Consumption
**Target:** CONTEXT
**What:** CONTEXT.md places Plan 12 (Improvement Loop + Regression Baseline) at Wave 7 — the last thing built after all 51 tests pass. The user directive states self-improvement is the "CORE IDENTITY, not an add-on." Two complementary fixes are needed:

(A) **Data contracts forward:** Plan 12's data models (`ImprovementAttempt`, `ImprovementHint`, `EvaluationProgress`, `ExperimentLedgerEntry`, `BaselineKey`) should be defined in Plan 01 Wave 1, not invented in Plan 12 Wave 7. When Plan 12 is built last, Plans 01-11 make design choices (field names, file formats, storage locations) without knowing what Plan 12 needs. This creates "big bang integration" risk.

(B) **Split Plan 12 for early consumption:** Split into Plan 12a (Wave 5.5 — minimal improvement hint consumer, ~40 LOC, writes prioritized hypothesis queue to `.vrs/evaluations/improvement_queue.jsonl`) and Plan 12b (Wave 7 — full improvement loop with experiment ledger, Jujutsu sandbox, regression baseline, metaprompting, intelligence modules). Plans 09-11 test orchestrator gains a step: after each Core-tier workflow, check improvement queue; if >3 hints with score <30, pause and surface to human reviewer.

**Why:** The architecture says improvement is the last thing assembled. The user's vision says it is the identity. Moving data contracts to Wave 1 resolves the data format tension. Splitting Plan 12 resolves the timing tension: Wave 6 runs 51 workflows producing improvement hints with no consumer until Wave 7. The first run is wasted as "baseline capture" rather than "diagnose and fix." Combined: the framework is designed for self-improvement from day 1 and starts consuming improvement signals during testing, not after.
**How:** (1) Add to Plan 01 scope: `ImprovementAttempt`, `EvaluationProgress`, `ExperimentLedgerEntry`, `ImprovementHint` (with `calibration_status` from P6-IMP-17), `BaselineKey` (`workflow_id` + `run_mode` from P6-IMP-06). (2) Add to Implementation Decisions: "Plan 12 data contracts are defined in Plan 01 (Wave 1). Plan 12 implements the logic that produces and consumes them." (3) Split Plan 12 into 12a (Wave 5.5, hint consumer ~40 LOC) and 12b (Wave 7, full loop). (4) Plans 09-11 gain mid-suite improvement queue check.
**Impacts:** Plan 01 (scope +6 models), Plan 08 (consumes EvaluationProgress), Plan 12 (split into 12a/12b), Wave ordering (12a at Wave 5.5), Plans 09-11 (improvement queue check)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — "contract-first" development applied to an LLM self-improvement loop
**Prerequisite:** no
**Status:** implemented

**Original framing:** "The Improvement Loop Is Wave 7 But Should Be the Architectural Spine — Define Data Contracts in Wave 1 AND Split Plan 12 for Early Consumption"

**Adversarial note (Self-Improvement Architecture Coherence):** The data-contracts-forward proposal (Part A) is correct and well-targeted. `ImprovementAttempt`, `EvaluationProgress`, and `ImprovementHint` are already listed in the CONTEXT.md Plan 01 summary (`v1 core types (~26)`) — this is verified by reading the Plan 01 summary section. So Part A is partially already addressed. The REFRAME targets Part B: splitting Plan 12 into 12a at Wave 5.5 assumes that Plans 07 and 08 produce `ImprovementHint` objects worth consuming before Wave 6 even runs. But `ImprovementHint` generation requires `calibration_status`, which requires the Calibration Anchor Protocol (Plan 12 Part 0), which ITSELF requires 51 tests to have run on corpus contracts. The sequencing contradiction is: Plan 12a at Wave 5.5 would consume hints that are `uncalibrated` (the evaluator hasn't been validated against ground truth yet), routing them to human review. This is correct behavior per the Improvement Hints Protocol — uncalibrated hints go to `uncalibrated_hints.jsonl` for human review only. So 12a is safe to build early. The real framing problem: the item describes Plan 12a as "minimal improvement hint consumer" but the consumer already exists implicitly — Plan 07 writes `improvement_hints` to `EvaluationResult`, which Plan 08 persists. What's missing is the QUEUE and the THRESHOLD CHECK, not a new consumer plan. The correct reframe: rename Part B as "Add improvement queue threshold check to Plans 09-11 (no new plan needed — 12a is 30 LOC of queue logic in Plan 08's progress.json write path, not a separate plan)." This avoids plan count inflation.

**Reframed What:** (A) Confirm that `ImprovementAttempt`, `EvaluationProgress`, and `ImprovementHint` belong in Plan 01 — verify the Plan 01 summary already lists them, and add `ExperimentLedgerEntry` and `BaselineKey` if missing. (B) Instead of a new Plan 12a, add a threshold-check step to Plan 08's progress writer: after each Core-tier workflow, if `improvement_hints` contains >3 entries with `score < 30`, append a `HIGH_PRIORITY` flag to `progress.json`. Plans 09-11 skill reads this flag and surfaces to human reviewer. No new plan, ~30 LOC in Plan 08. The "self-improvement from day 1" identity is preserved without plan count inflation.

---

### P7-IMP-02: PHILOSOPHY.md v1 Pillar 1 Contradicts CONTEXT.md on Reasoning Decomposition Scope
**Target:** CONTEXT
**What:** PHILOSOPHY.md Pillar 1 states: "v1 implementation: 3 practical dimensions... Cascade-aware DAG scoring and 7-move taxonomy are v2 scope." But CONTEXT.md Plan 07 specifies dual-Opus with 4 prompt templates, per-category move type applicability, and the 7-move taxonomy fully scoped. CONTEXT.md wins per the header rule, but a developer reading only PHILOSOPHY.md will build the wrong evaluator.
**Why:** Plan 07 implementers will read PHILOSOPHY.md (binding constraints) and build a simpler evaluator than CONTEXT.md specifies.
**How:** (1) Update PHILOSOPHY.md Pillar 1 v1 to match CONTEXT.md: "v1 implementation: 7 reasoning move types scored via dual-Opus evaluator with per-category applicability." (2) Remove "7-move taxonomy are v2 scope" from Deferred to v2. (3) Update North Star item 7 to reference dual-Opus and external ground truth.
**Impacts:** PHILOSOPHY.md (alignment fix), no plan changes
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Self-Improvement Architecture Coherence):** The divergence is verified by reading both files. PHILOSOPHY.md Pillar 1 explicitly states "3 practical dimensions" and defers the 7-move taxonomy to v2. CONTEXT.md Plan 07 explicitly specifies 7 move types, dual-Opus, and 4 templates. PHILOSOPHY.md also states "Binding Rules: Deferred to v2: Rule J (dual-Opus meta-evaluation)" — which directly contradicts CONTEXT.md's locked Evaluator Debate Protocol. The contradiction survives the header rule because PHILOSOPHY.md is labeled "v1 Binding Constraints" and a developer may treat it as the authoritative v1 document despite the header. The fix is necessary and the scope (PHILOSOPHY.md only, no code changes) is correct. Second-order effect: updating PHILOSOPHY.md to match CONTEXT.md means PHILOSOPHY.md's "Deferred to v2" list will shrink substantially — verify the trimmed list doesn't accidentally remove real v2 items (Rule K through O should remain deferred).

---

### P7-IMP-03: P6-IMP-15 Intelligence Modules Need Integration Constraints — They Interact With the Live Pipeline
**Target:** CONTEXT
**What:** P6-IMP-15 promotes coverage_radar, contract_healer, tier_manager to v1 at ~200 LOC. But they interact with Plans 01, 06, 08, 12 simultaneously: tier_manager writes tier changes affecting hook installation (Plan 02) and evaluation depth (Plan 07); contract_healer modifies contracts (Plan 06 artifacts) mid-baseline; coverage_radar needs severity data from VulnDocs.
**Why:** Promoting modules without pipeline interaction guards creates bugs: tier changes mid-run, contract mutations during baseline collection. P6-IMP-15 is correct directionally but needs integration constraints.
**How:** (1) tier_manager: changes take effect NEXT suite run via `pending_tier_changes.yaml` queue. (2) contract_healer: `propose()` returns proposals, no `apply()` method — never auto-applies. (3) coverage_radar v1: reporting only, no scenario synthesis. (4) Add constraints to Implementation Decisions. (5) Revise LOC to ~350 (200 module + 150 guards).
**Impacts:** Plan 12 Part 5 (integration constraints, revised LOC), Implementation Decisions (+3 constraints)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Self-Improvement Architecture Coherence):** The integration constraint for `contract_healer` (propose-only, no apply) is correct and already partially implied by CONTEXT.md's description of contract_healer as "detects from BaselineManager's 20-score windows." However, the item misses a fourth interaction: coverage_radar's "requires `coverage_axes` field from Plan 06" dependency is already noted in CONTEXT.md, but the claim that coverage_radar "needs severity data from VulnDocs" violates DC-2 (no imports from `kg` or `vulndocs`). Coverage_radar should derive severity from the evaluation contract's `coverage_axes` field (which can include a severity annotation), NOT from VulnDocs directly. The How should add: "(4b) coverage_radar MUST NOT import from `vulndocs` — severity labels must come from evaluation contract `coverage_axes` field." This is a DC-2 compliance issue introduced by P6-IMP-15 and not caught until now. The LOC estimate revision from 200 to 350 is plausible. Second-order: the `pending_tier_changes.yaml` queue for tier_manager creates a new file artifact that Plan 08's runner must be aware of — add to Plan 08 summary: "skip workflows in `pending_tier_changes.yaml` for the current run."

---

### P7-IMP-04: Plans 09-11 as CC Skills (P6-ADV-02) Creates Testability Inversion — Who Tests the Test Skill?
**Target:** CONTEXT
**What:** P6-ADV-02 restructures Plans 09-11 as CC skill `/vrs-test-suite` with thin pytest wrappers. Correct resolution. But creates testability inversion: the test framework is a CC skill that must itself be tested. Pytest wrappers validate report FORMAT, not orchestration BEHAVIOR.
**Why:** Concrete failure: skill skips debrief for Important-tier workflows. Report omits debrief scores. Pytest wrapper accepts `debrief: null` as "no debrief configured" — bug is invisible because format is valid even when behavior is wrong.
**How:** (1) Accept P6-ADV-02. (2) Add Implementation Decision: dual validation — automated pytest wrappers validate schema + score thresholds; HITL scenarios 09-11 validate orchestration behavior by human observation. Both required for Wave 6 gate. (3) Add `--dry-run` mode to skill: orchestrates 1 Core workflow with full debrief, writes diagnostic report of each pipeline stage (~50 LOC).
**Impacts:** Plans 09-11 (+dry-run mode), HITL scenarios (clarified scope), Implementation Decisions
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** yes — P6-ADV-02 must be accepted first
**Status:** implemented

**Adversarial note (Self-Improvement Architecture Coherence):** The testability inversion is real. HITL scenarios 09-11 already exist in CONTEXT.md (the HITL table shows Plans 09, 10, 11 with specific pass conditions), so the dual validation concept is partially present. What is genuinely new: (a) making HITL 09-11 explicitly required for Wave 6 gate passage (not optional), and (b) the `--dry-run` mode for the skill itself. The `--dry-run` mode is well-scoped at ~50 LOC and directly addresses the class of bug described. Second-order effect: `--dry-run` produces a diagnostic report — this report format should be defined in Plan 01 or the Plan 09-11 skill spec, not left unspecified. The improvement item should add "diagnostic report schema to Plan 01" to the Impacts list. Cross-group check: P7-IMP-22 (Group C) also targets Plan summaries. No conflict — they target different layers (skill behavior vs plan documentation).

---

### P7-IMP-05: Jujutsu Workspace Isolation Is Referenced 5 Times But Has Zero Operational Specification
**Target:** CONTEXT
**What:** CONTEXT.md and PHILOSOPHY.md reference Jujutsu workspace isolation as preferred sandboxing but never specify: how workspaces interact with `.claude/` paths, whether hooks in parent are visible in child, how results map back to variants, or what happens on workspace forget mid-evaluation. WorkspaceManager exists (416 LOC) but its jj methods are unvalidated against real CC hook installation.
**Why:** Plan 12 Part 2 says "3-5 variants branched in Jujutsu, evaluated sequentially." If Jujutsu workspaces share `.claude/` paths with parent, the improvement sandbox modifies production — violating the ABSOLUTE RULE.
**How:** (1) New Prestep P5: "Jujutsu Workspace Isolation Pilot" — create workspace, install modified hooks, run single workflow, verify `.claude/` independence, hook isolation, workspace-local `.vrs/`, clean forget. 30 minutes. (2) Add to Plan 12: "WorkspaceManager.create_variant() must validate `.claude/` independence before proceeding. Fallback: `.claude.sandbox/` copy." (3) Failure protocol: if Jujutsu isolation fails, use `.claude.sandbox/` exclusively.
**Impacts:** Presteps (+P5), Plan 12 (workspace validation prerequisite)
**Research needed:** no — RESOLVED empirically by adversarial reviewer (2026-02-19). `jj workspace add` creates physically independent `.claude/` directories. Isolation confirmed. See adversarial note below for full evidence.
**Status:** implemented

**Adversarial note (Self-Improvement Architecture Coherence):** The research question has been answered empirically during this review session. `jj workspace add /tmp/jj-isolation-test` was executed against the project repository. Results: (1) The workspace creates a physically independent directory at the destination path with its own file copies — `ls /tmp/jj-isolation-test/.claude/` shows `agents`, `skills`, `subagents`, `settings.json` as independent files. (2) A file written to `/tmp/jj-isolation-test/.claude/` does NOT appear in the main worktree `.claude/` — isolation is confirmed. (3) The workspace showed "1 update skipped due to conflicting changes in the working copy" (due to the current git-tracked `.claude/` modifications in the main worktree), which means the workspace reflects the COMMITTED state, not the dirty working tree state. This has an important consequence: if Plan 12 improvement loop modifies `.claude/` in the workspace as a prompt variant, and those changes are committed in the workspace's jj change, they stay isolated. The ABSOLUTE RULE is not violated by `jj workspace add`.

The remaining concern is NOT isolation (confirmed safe) but operational gaps: (a) hooks must be re-installed in the workspace `.claude/settings.json` since the workspace reflects committed hook state, not the current working tree's hook setup; (b) `.vrs/observations/` must be created in the workspace before running a session there. These operational gaps belong in Prestep P5. The item is enhanced: remove `research_needed: yes` (question answered), refine Prestep P5 to focus on the operational setup steps rather than isolation verification, and document the committed-state behavior so Plan 12 implementers know to re-run `WorkspaceManager.install_hooks()` in each workspace.

**research_needed:** no — answered empirically: `jj workspace add` creates filesystem-independent `.claude/` directories. Isolation confirmed. Remaining operational gaps are setup steps, not isolation failures.

---

### P7-IMP-06: Improvement Loop Only Consumes Own Scores — No External Feedback Protocol
**Target:** CONTEXT
**What:** Plan 12 Part 3 implements metaprompting from failure narratives. But the loop never checks prompt changes against external detection outcomes from `corpus/ground_truth.yaml` (153 findings). This creates a closed self-referential loop: optimizing for evaluator satisfaction, not detection capability. P6-ADV-03 addresses evaluator calibration; this addresses the feedback loop itself.
**Why:** A self-improving system consuming only its own scores converges on evaluator-pleasing behavior, not detection-improving behavior. External ground truth exists and is unwired.
**How:** (1) Add to Plan 12 Part 3: "Before accepting any prompt change, run on 3 corpus contracts with known vulnerabilities. If detection rate drops, REJECT regardless of evaluation score improvement." (~30 LOC). (2) Add `detection_validation: {tp_count, fp_count, corpus_contracts}` to `ExperimentLedgerEntry`. (3) Add to Experiment Ledger Protocol: "Kill criteria MUST include at least one external detection outcome."
**Impacts:** Plan 01 (model field), Plan 12 Part 3 (external kill criterion), Experiment Ledger Protocol
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Self-Improvement Architecture Coherence):** This item partially overlaps with P6-ADV-03 (Calibration Anchor Protocol) but targets the improvement LOOP rather than the initial calibration. The distinction is real: ADV-03 gates exit gate 6 (calibration before accepting hints), this item gates each individual experiment ledger entry (validation before accepting each prompt change). The overlap is tolerable because the mechanisms are different. However, there is a circular dependency the item does not acknowledge: to run "3 corpus contracts with known vulnerabilities" as a kill criterion, the improvement loop must run investigation agents on corpus contracts during Plan 12. But Plan 12 is Wave 7, and the first corpus runs in Wave 6 (Plans 09-11) are the test suite runs. Running additional corpus evaluations inside each experiment ledger entry effectively doubles the Plan 12 runtime per variant: each of 3-5 variants now requires (a) the prompt variant run + (b) 3 corpus validation runs. At ~25 minutes per Investigation run, 3 corpus runs = 75 additional minutes per variant. A 5-variant cycle becomes 5 * (25 + 75) = 500 minutes (8+ hours). The item must acknowledge this cost and add a mitigation: "use `run_mode=headless` for corpus validation runs in the experiment ledger (no debrief, no debate — just detection outcome check). This reduces corpus validation from ~75 min to ~15 min per variant." The How should be updated to include run_mode specification for corpus validation.

---

### P7-IMP-07: Concrete Failure Scenario — Improvement Loop Optimizes Wrong Direction Without External Anchor
**Target:** CONTEXT
**What:** Day 1: attacker scores 55 on CONCLUSION_SYNTHESIS. Day 2: improvement adds "always cite specific function names and line numbers." Day 3: scores 72 — more specific. Day 4: agent over-cites on SAFE contract, constructs convincing FALSE vulnerability. Evaluator scores 68. No regression detected (68 > 55). Agent is WORSE at distinguishing real from false but scores higher. Detection baseline already shows Precision=13.3% — agents already produce many FPs. Rewarding specificity without truth checking amplifies this.
**Why:** Validates P6-ADV-03 and P7-IMP-06 as critical, not aspirational.
**How:** Add as "Documented Failure Scenario" in CONTEXT.md after Known Code Issues. Reference P6-ADV-03 and P7-IMP-06 as mitigations. Design rationale that prevents future removal of external anchors.
**Impacts:** CONTEXT.md documentation (no code impact)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — Goodhart's Law in RLHF is documented (Skalse et al. 2022)
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Self-Improvement Architecture Coherence):** The failure scenario is internally consistent and correctly validates two other items (P6-ADV-03, P7-IMP-06) as structurally necessary rather than aspirational. The Goodhart's Law framing is accurate. The scenario is strengthened by real data: Precision=13.3% from the detection baseline means the attacker already generates ~6.5 false positives per true positive. Rewarding specificity without truth-checking would systematically amplify this. One gap: the scenario assumes Day 4's evaluation uses the SAME evaluator on a SAFE contract. The evaluator debate protocol (IMP-14) would expose disagreement on a convincingly false finding — Evaluator B, seeing A's raw scores without A's reasoning, may score the false finding lower. This means IMP-14 provides partial protection against this failure scenario. This should be noted in the design rationale to accurately represent the defense-in-depth. The "Documented Failure Scenario" section should reference IMP-14 alongside P6-ADV-03 and P7-IMP-06 as a third mitigation layer.

---

### P7-IMP-08: The "Report-Generating" Vision Has No Report Schema, Consumer, or Aggregation
**Target:** CONTEXT
**What:** User directive: "reports on WHY things fail, suggest improvements, identify redesign needs." Plan 12 Part 4 says "structured reports when auto-fix fails" but specifies no schema, consumer, or delivery. Individual `FailureNarrative` entries exist per dimension but no aggregation into a readable report. After 51 workflows, no mechanism produces a single document answering "what failed, why, and what to do."

Two complementary needs: (A) Per-workflow failure escalation: `FailureReport` with `recommendation: Literal["continue_improving", "escalate_to_human", "redesign_needed"]` — "redesign_needed" set when root cause is architectural. (B) Suite-level aggregation: executive summary, systemic patterns (dimensions failing across >3 workflows grouped by root cause), per-tier breakdown, prioritized action items from improvement_hints frequency analysis.

**Why:** Individual failure narratives are useful for the improvement loop but not for human comprehension. The user asked for reports that "trigger new GSD phases when fundamental redesign is needed."
**How:** (1) Add `FailureReport` model to Plan 01: `workflow_id, dimension, iterations_attempted, best_score_achieved, target_score, root_cause_hypothesis, failed_interventions: list[ExperimentLedgerEntry], recommendation, redesign_rationale`. (2) Expand Plan 12 Part 4: aggregated report to `.vrs/evaluations/failure_report_{timestamp}.md` with executive summary, systemic patterns, per-tier breakdown, action items. (3) CLI: `alphaswarm evaluation failures [--severity redesign_needed]` and `alphaswarm evaluation report`.
**Impacts:** Plan 01 (FailureReport model), Plan 12 Part 4 (report generation + aggregation), CLI (P6-IMP-18 gains subcommands)
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Self-Improvement Architecture Coherence):** The gap is real: Plan 12 Part 4 says "structured reports when auto-fix fails" but has no schema. The `FailureReport` model is correctly targeted to Plan 01. However, the item's `failed_interventions: list[ExperimentLedgerEntry]` field creates a circular type dependency if `ExperimentLedgerEntry` references `FailureReport` for "what failed." Ensure no circular import: `FailureReport` references `ExperimentLedgerEntry` unidirectionally (ledger entries are prior attempts, report is the diagnosis). Also: `recommendation: Literal["redesign_needed"]` is meant to trigger new GSD phases. The item does not specify how this recommendation reaches the human. The CLI subcommand `alphaswarm evaluation failures --severity redesign_needed` is the delivery mechanism — but Plan 12 Part 4 should also produce a human-readable `.md` file that can be read directly without CLI. The How already specifies `.vrs/evaluations/failure_report_{timestamp}.md` — this is sufficient. The MEDIUM confidence rating is appropriate because "redesign_needed" classification requires LLM judgment about what constitutes "architectural root cause" vs "prompt-fixable root cause." Add this ambiguity to the item: "redesign_needed classification heuristic: N>=3 failed interventions across N>=2 distinct dimensions, where root_cause_hypothesis references a non-prompt artifact (graph builder, pattern schema, or hook behavior)."

---

### P7-IMP-09: Mode Coverage Fraction — Headless Passes All "Applicable" Dimensions But Covers 65% of Quality Surface
**Target:** CONTEXT
**What:** P6-IMP-06 adds Mode Capability Matrix. P6-IMP-03 proposes headless for Standard tier. Neither quantifies the quality surface coverage per mode. A headless result that passes all applicable dimensions gives false confidence — unmeasured dimensions (debrief, team coordination, cross-agent coherence) are where real quality signal lives.
**Why:** Without mode_coverage, evaluation reports cannot communicate "this workflow was evaluated at 65% coverage" vs "100% coverage." Exit gates need minimum coverage to prevent headless-only satisfaction.
**How:** (1) Add `mode_coverage: dict[str, float]` to evaluation contracts: `{"interactive": 1.0, "headless": 0.65, "simulated": 0.2}`. (2) Add `coverage_fraction: float` to EvaluationResult. (3) BaselineManager: never compare different coverage_fraction values in same regression window. (4) Exit gates 3-5: minimum coverage_fraction 0.8 required.
**Impacts:** Plan 06 (contracts), Plan 01 (EvaluationResult field), Plan 08 (runner computation), Plan 12 (baseline guards), Exit gates
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** yes — P6-IMP-06 must be accepted first
**Status:** reject

**Adversarial note (Self-Improvement Architecture Coherence):** The item is REJECTED on two grounds. First, the coverage_fraction numbers (interactive=1.0, headless=0.65, simulated=0.2) are static constants authored without empirical basis. The Mode Capability Matrix already defines WHICH dimensions are applicable per mode — the fraction is trivially computable from the matrix as `applicable_dimensions / total_dimensions`. Hardcoding 0.65 without derivation from the matrix creates a maintenance hazard: if a new dimension is added, 0.65 becomes wrong. The correct implementation is: `coverage_fraction = len([d for d in dimensions if d.applicable]) / len(dimensions)` — this is already implied by P7-IMP-25's `applicable: bool` on `DimensionScore`. No separate `mode_coverage` contract field is needed. Second, "minimum coverage_fraction 0.8 required for exit gates 3-5" would BLOCK Standard tier testing in headless mode. The existing CONTEXT.md explicitly allows Standard tier with lite evaluation (capability + focused reasoning only). Adding a 0.8 coverage floor for exit gates 3-5 contradicts this design decision. The actual defense against headless-only satisfaction is the Mode Capability Matrix's annotation `run_mode == 'interactive'` required for Core tier (already in CONTEXT.md). The item creates redundant infrastructure for a problem already addressed.

---

### P7-IMP-10: Phase Exit Should Require One Demonstrated Improvement Cycle, Not Just Infrastructure
**Target:** CONTEXT
**What:** Exit gates 9-11 verify improvement INFRASTRUCTURE (loop never modifies production, regression detection operational, baseline established). They do not verify the LOOP works end-to-end. A Phase 3.1c that ships "improvement infrastructure exists" but "improvement loop has never successfully improved anything" is incomplete.
**Why:** "Self-improving" implies demonstrated self-improvement, not just plumbing.
**How:** Add exit gate 17: "At least one completed improvement cycle on a Core-tier workflow: (a) low-scoring dimension identified, (b) hypothesis with experiment ledger card, (c) prompt variant sandboxed in Jujutsu, (d) re-evaluation shows improvement > 5 points, (e) no regression > 10 points on Core, (f) external detection validation passes. Alternatively: one cycle completed with documented failure + root cause FailureReport."
**Impacts:** Exit gates (+gate 17), Plan 12 (no scope change, just verification criterion)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Self-Improvement Architecture Coherence):** The gate is necessary and the "alternatively: documented failure + FailureReport" escape clause is the right engineering choice — it prevents the exit gate from being blocked by fundamental limitations of the framework (e.g., if no dimension improves >5 points in v1, the framework should still ship with a documented root cause). However, exit gate 17's condition (f) "external detection validation passes" creates a hard dependency on P7-IMP-06 being implemented. If P7-IMP-06 is not merged, gate 17 cannot be evaluated. The Prerequisite field should be updated to: "yes — P7-IMP-06 (external feedback protocol) must be accepted; if rejected, remove condition (f) from gate 17." Also: condition (c) "prompt variant sandboxed in Jujutsu" — the Jujutsu isolation is now confirmed safe (per P7-IMP-05 analysis). But the alternative exit path ("documented failure + FailureReport") should NOT require Jujutsu sandboxing — a documented failure cycle can use `.claude.sandbox/` fallback. Clarify: "condition (c) requires EITHER Jujutsu workspace OR `.claude.sandbox/` fallback — both satisfy the sandboxing requirement." Second-order: exit gate 17 is the only gate that requires actually RUNNING the improvement loop (not just building it). This means Phase 3.1c cannot close without at least one real improvement cycle run, which may take several additional hours beyond the 51-workflow baseline. Phase timeline estimates should reflect this.

---

## Group B: Pattern Testing & Static Analysis Integration

### P7-IMP-11: CONTEXT.md Has Zero Mention of Testing Vulnerability Detection Accuracy
**Target:** CONTEXT
**What:** The 12-plan architecture tests whether agents RUN correctly and REASON well, but never tests whether they actually FIND VULNERABILITIES. No plan runs investigation agents on corpus contracts and measures TP/FP/miss rates. The detection baseline exists (Precision=13.3%, Recall=83.3%), 18 corpus projects have ground truth with 153 findings, `OutputParser.calculate_accuracy()` exists — but the connection is blocked by a schema mismatch: `OutputParser._is_match()` calls `ground_truth.get("location", "")`, but ground truth YAML entries use `function`, `contract`, and `line_range` fields, not a `location` field. The "all unwired" claim is understated — the wiring will silently produce wrong results if the adapter layer is missing.
**Why:** This is the single largest gap between the user's goal ("Test ALL B-tier and C-tier patterns") and the CONTEXT.md design. The framework evaluates HOW agents think, not WHETHER they find what they should find. Critically, simply reusing `OutputParser.calculate_accuracy()` is not sufficient — a ground truth adapter must first normalize `{contract, function, line_range}` into the `{pattern, location}` format the parser expects. Without this adapter, every ground truth entry matches as "location unknown" and precision/recall computation is silently wrong.
**How:** (1) Add "Detection Accuracy Testing" to Implementation Decisions. (2) Before wiring `calculate_accuracy()`, add `GroundTruthAdapter.normalize(entry) -> dict` that maps `{contract, function, line_range}` to `{pattern: entry.pattern_id, location: f"{entry.contract}.{entry.function}:{entry.line_range}"}`. (3) Define dimension: compare agent findings against adapted ground truth (TP/FP/miss). (4) Wire into Plans 09-10: run `GroundTruthComparison` after evaluation. (5) Exit gate: "Recall >= 60% for Tier A patterns on Core investigation agents." (6) Plan 12: track detection accuracy as regression signal. (7) Add `GroundTruthAdapter` to Plan 01 scope.
**Impacts:** Plans 09-10 (ground truth comparison), Plan 01 (GroundTruthComparison + GroundTruthAdapter), Plan 12 (detection regression), Exit gates
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Detection Accuracy & Pattern Testing Viability):** The original framing says `OutputParser.calculate_accuracy()` is "unwired." That is correct but incomplete. The actual problem is a schema mismatch: corpus ground truth uses `{contract, function, line_range}` but `_is_match()` reads `ground_truth.get("location", "")` which returns empty string on every corpus entry. Naively wiring the existing function produces silently wrong metrics — every agent finding would be a false positive because nothing matches. The How section must include an explicit adapter step. Rewrite strengthens the How to make the adapter a first-class deliverable rather than an assumed detail.

---

### P7-IMP-12: B-tier and C-tier Patterns Are Completely Untested — No Plan Addresses Them
**Target:** CONTEXT
**What:** Pattern catalog: 461 patterns (353 A, 95 B, 13 C). CONTEXT.md says B/C tests are "dynamically generated" but no plan generates them. The claim that ground truth "lacks tier annotation" and "B/C coverage is unknown" is incorrect — a direct join of ground truth `pattern_id` values against `pattern-catalog.yaml` reveals: 28 unique patterns are Tier A, 30 are Tier B, 9 are Tier C, and 10 patterns appear in ground truth but are absent from the catalog entirely. The corpus already has significant B/C coverage. The problem is not absence of B/C patterns — it is (a) 10 patterns with no catalog entry, meaning their tier is unclassified and their detection queries are undefined, and (b) the evaluation framework has no per-tier accuracy tracking regardless of coverage.
**Why:** B-tier requires cross-function dataflow analysis. C-tier requires protocol context and economic reasoning. These distinguish this framework from Slither. If they don't work, the core value proposition is unproven. The 10 uncatalogued patterns represent a real gap — they exist in ground truth but have no VulnDoc and no BSKG detection query, so even if an agent finds them, there is no "correct" detection path to verify against.
**How:** (1) Run the join now as Prestep P6 (5 minutes, not a research spike): document tier distribution (28A/30B/9C/10-uncatalogued) and list the 10 uncatalogued patterns. (2) For the 10 uncatalogued patterns, decide: add them to catalog with tier assignment, or remove them from ground truth as "unverifiable." (3) Add tier annotation to existing ground truth via join output. (4) Build per-tier accuracy tracking into `GroundTruthComparison` without waiting for new corpus generation. (5) Exit gate: "Tier B recall >= 40% on already-existing corpus patterns." (6) Generating 5-10 new B-tier projects: demote to Deferred — the existing 30 B-tier ground truth entries are sufficient to establish the baseline before generating more.
**Impacts:** Presteps (P6 is 5-minute join, not corpus generation), Plans 09-10 (per-tier accuracy), Plan 12 (per-tier regression), Exit gates, P6-IMP-15 coverage_radar
**Research needed:** no — join result: 28A/30B/9C/10-uncatalogued
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Detection Accuracy & Pattern Testing Viability):** The original framing marks this as "research needed — answerable by join." The join has been performed. Result: the corpus already has 30 B-tier and 9 C-tier patterns in ground truth. The problem is not sparse B/C coverage; it is the 10 patterns absent from the catalog (making their detection unverifiable) and the absence of per-tier tracking in the evaluation framework. Rewrite replaces the "generate new corpus" first step with "fix the 10 uncatalogued patterns" and moves bulk generation to Deferred. The "B/C coverage is unknown" claim was resolvable immediately and should not have been marked as research.

---

### P7-IMP-13: Static Analysis Tool Integration Has No Finding Merge Testing
**Target:** CONTEXT
**What:** User stated: "The workflow that merges findings from static analysis tools may not work." No scenario tests the MERGE step: Slither JSON + BSKG pattern matches + agent findings → unified set. `vrs-finding-merger` and `vrs-finding-synthesizer` agents exist but have no evaluation contract, scenario, or test. UC-TOOL-001 tests "run Slither and parse" but stops there.
**Why:** If merge is broken, users see duplicates, contradictions, or lost findings. The value depends on deduplication (same reentrancy found by Slither AND agent = 1 report).
**How:** (1) New scenarios: UC-TOOL-004 "Full pipeline: Slither + agent + merge" and UC-TOOL-005 "Deduplication: same vuln from tool and agent." (2) Evaluation contracts for finding-merger and finding-synthesizer at Important tier. (3) Add Known Code Issue: "Finding merge pipeline untested E2E." (4) Merge-quality dimension: deduplication rate, evidence preservation, severity reconciliation.
**Impacts:** Plans 09-10 (merge pipeline test), Plan 06 (2 contracts), Scenarios (+2-3)
**Research needed:** no — RESOLVED by codebase archaeology (2026-02-19).

**Research answer:** Extend `SemanticDeduplicator` to accept both formats. Do NOT make the merger agent the dedup layer.

**Evidence:**
1. **`SemanticDeduplicator`** lives in `orchestration/dedup.py` (1101 LOC, not `tools/`). It already has: (a) two-stage dedup (location clustering + semantic similarity via sentence-transformers), (b) category normalization with 12 alias groups, (c) cross-tool confidence boosting, (d) `deduplicate_findings()` convenience function that already accepts `List[Dict[str, Any]]` and converts dicts to `VKGFinding` internally (lines 690-714). This dict-acceptance path means agent findings CAN be fed in today if formatted as dicts with keys: `source`, `rule_id`, `title`, `description`, `severity`, `category`, `file`, `line`, `function`, `confidence`, `vkg_pattern`.
2. **`merge_batch_deltas()`** (lines 864-970) is a SEPARATE v2 merge pipeline operating on `DeltaEntry`/`MergeBatch` from `orchestration/schemas.py`. It handles deterministic ordering, conflict detection (evidence mismatch, confidence conflict, payload divergence), and idempotent replay. This is the append-only delta pipeline — conceptually different from dedup.
3. **`vrs-finding-merger`** agent (32 LOC) is a thin CC agent spec with no input schema, no dedup algorithm, and no reference to either `SemanticDeduplicator` or `merge_batch_deltas`. It says "merge append-only findings deltas" and "idempotent merges by deterministic IDs" — which aligns with `merge_batch_deltas()` semantics, not `SemanticDeduplicator`.
4. **`vrs-finding-synthesizer`** agent (122 LOC) is well-specified with input format (`findings`, `evidence_registry`, `pcps`, `protocol_context`), clustering strategy, confidence boundary rules, and conflict resolution. This is the LLM-powered synthesis layer that operates AFTER dedup.

**Architectural recommendation:**
- **Layer 1 — Deterministic dedup:** Extend `SemanticDeduplicator.deduplicate()` to accept `List[VKGFinding | Dict[str, Any]]` (already half-done via `deduplicate_findings()`). Agent findings become dicts with `source="agent-attacker"`. ~30 LOC to formalize.
- **Layer 2 — Delta merge:** `merge_batch_deltas()` handles append-only delta tracking and conflict quarantine. Agent beads produce `DeltaEntry` objects. This is orthogonal to dedup — it tracks WHAT CHANGED, not WHAT'S DUPLICATE.
- **Layer 3 — LLM synthesis:** `vrs-finding-synthesizer` clusters, resolves conflicts, computes confidence bounds. Called after Layer 1+2.
- **Finding-merger agent:** Should be retired or rewritten as a thin orchestrator that calls Layer 1 → Layer 2 → Layer 3 in sequence. Current spec is too vague to implement.

**Remaining prerequisite:** Define the agent finding → dict mapping (which fields from bead/verdict map to `VKGFinding` fields like `file`, `line`, `category`). This is a ~20-line schema definition, not an architectural decision.
**Confidence:** HIGH
**Prior art:** 3
**Status:** implemented
**Pre-implement note (pass 2 — resolved):** The architectural question is answered: extend `SemanticDeduplicator` via `deduplicate_findings()` which already accepts `List[Dict]` (lines 690-714 in `orchestration/dedup.py`). The remaining work is a thin mapping function: `InvestigationResult` → dict with keys {source, rule_id, title, description, severity, category, file, line, function, confidence, vkg_pattern}. Key design decision: `file` and `line` must be extracted from `InvestigationResult.evidence` list (which contains code locations) or from `step_results[].evidence` — NOT from top-level fields (which don't have file/line). This is ~20 LOC and belongs in Plan 09-10 merge scenario implementation, not as a standalone prerequisite. Route as Known Code Issue.

**Adversarial note (Detection Accuracy & Pattern Testing Viability):** The research question is answered by reading `vrs-finding-merger.md` (32 LOC, no input format specified beyond "findings deltas") and `alphaswarm tools status` output (Aderyn not installed, Mythril absent entirely). The merge test proposed requires: (a) Slither produces findings in JSON format that `vrs-finding-merger` can consume — this interface is UNSPECIFIED in the agent's spec; (b) a "full pipeline with tool integration" scenario requires Aderyn or Mythril to be installed — neither is. Before writing scenarios, the merger agent spec must be extended to define: what JSON schema it accepts as input, what deduplication algorithm it uses (hash? location? pattern?), and how it reconciles severity conflicts. Without this, any scenario written is testing aspirational behavior, not actual behavior. Mark as PREREQUISITE: "Define finding-merger input schema before authoring merge test scenarios."

---

### P7-IMP-14: Graph Knowledge Verification Is Superficial — No Test Checks Whether Agents REASON FROM Graph Results
**Target:** CONTEXT
**What:** GVS checks 4 dimensions including citation rate (regex matching node IDs in conclusions). This tests whether agents MENTION graph results, not whether they REASON FROM them. Failure: agent queries BSKG, gets 47 nodes, cites `node:func_withdraw` in conclusion, but actual vulnerability is in `func_deposit` (also in results). GVS gives high citation rate. Reasoning evaluator and GVS are disconnected — nobody checks "did the conclusion follow from the graph results?"
**Why:** User asked: "Verify agents actually USE graph knowledge (not just query it)."
**How:** (1) Add "Graph-Reasoning Coherence" cross-scorer dimension: cross-reference cited node IDs against ground truth function/contract names. (2) Plan 04: `_check_citation_relevance()` ~50 LOC. (3) Only computable for corpus contracts with ground truth. (4) Investigation contracts gain `graph_reasoning_coherence: true`.
**Impacts:** Plan 04 (+50 LOC), Plan 06 (investigation contracts), Plan 02 (must capture result node IDs — already required)
**Research needed:** no — RESOLVED by GAP-11. BSKG returns full Node objects with label=function_name, properties.file, properties.line_start/line_end. Cross-referencing is feasible via label matching.
**Research summary:** Node IDs are one-way hashes (not reversible), but query results return full Node objects with all mapping data. BSKGQuery in transcript_parser.py needs ~20 LOC to parse JSON and extract structured node labels. Match on label field, not hash-based node IDs.
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** yes — Plan 02 must capture BSKG result node IDs
**Status:** implemented

---

### P7-IMP-15: 18 Corpus Projects Are Insufficient for B/C Testing — Need Targeted Generation
**Target:** CONTEXT
**What:** The corpus already contains 30 B-tier and 9 C-tier patterns in existing ground truth (verified by join against pattern-catalog.yaml). The original claim that "no evidence corpus covers B-tier or C-tier patterns" is incorrect. The actual insufficiency is different: (a) the stress-test projects (protocol-maze-02, max-obfuscation-01) already contain multi-contract B-tier scenarios, but they were never run through the evaluation pipeline; (b) 10 ground truth patterns are absent from the catalog, making their B/C classification unknown; (c) no corpus project tests C-tier economic interactions (flash loan + oracle manipulation across 5+ contracts) — the existing C-tier patterns are mostly signature-replay and governance variants, not multi-protocol economic attacks.
**Why:** Realistic B-tier testing requires contracts where vulnerabilities span multiple functions with non-obvious dataflow. C-tier requires multi-contract economic scenarios (flash loan → oracle manipulation → lending pool). The existing corpus partially covers B-tier but under-represents true C-tier economic complexity.
**How:** (1) First: run the existing 18 projects through the evaluation pipeline and measure actual B/C detection rates before generating new projects — this is the ground truth on what's missing. (2) If existing B-tier recall < 40%: investigate whether the gap is corpus quality (contracts too simple) or detection capability (BSKG missing cross-function edges). Only generate new contracts if corpus quality is the bottleneck. (3) If C-tier economic scenarios are genuinely absent after inventory: generate 2-3 targeted C-tier projects (not 3+5 as proposed). (4) Demote Prestep P7 from "corpus generation" to "corpus gap analysis" — run the pipeline, measure the gap, then decide whether to generate.
**Impacts:** Presteps (P7 is gap analysis first, generation conditionally), Plans 09-10 (+8 corpus projects only if gap analysis warrants), corpus directory
**Research needed:** partially answered — Cannot run full pipeline now (evaluation framework not yet built), but existing data provides strong bounds. See research answer below.

**Research answer:** The B/C detection rate against the existing corpus cannot be measured yet because the evaluation pipeline (Plans 01-08) does not exist. However, existing evidence constrains the answer:

**Evidence from existing baselines:**
1. **Detection baseline (3.1d-05, 2026-02-18):** Precision=25%, Recall=57.1% on 7 contracts using Tier A lens-report patterns only. All detected findings are Tier A (reentrancy, access control, external call patterns). Zero B-tier or C-tier patterns were tested because the lens-report only runs A-tier deterministic patterns.
2. **Pattern catalog:** 353 A-tier, 95 B-tier, 13 C-tier patterns exist. B-tier patterns require cross-function analysis (BSKG graph traversal). C-tier patterns require multi-contract economic reasoning.
3. **Corpus:** Only `ground_truth_markers.yaml` exists in `corpus/` (vulnerability markers stripped from test contracts). The "18 corpus projects" referenced in the improvement item do not exist as a separate corpus directory — the corpus IS the `tests/contracts/*.sol` files (30+ contracts). The ground truth manifest references SmartBugs (143 contracts, 207 findings) as external source, but no local SmartBugs corpus is materialized.
4. **No agent-based detection has been run.** The detection baseline was Tier A pattern matching via lens-report, not agent investigation. B-tier detection requires agents running BSKG queries to find cross-function dataflow — this has never been measured.

**Conclusion:** The question "What is actual B/C detection rate?" is premature. The answer is: **B-tier detection rate is unknown (never measured), C-tier detection rate is unknown (never measured).** The existing 25% precision / 57% recall baseline is A-tier only. Running B/C detection requires: (a) build-kg on corpus contracts, (b) agent sessions with BSKG queries, (c) comparison against ground truth. This is exactly what Plans 09-11 will do.

**Revised recommendation:** Demote Prestep P7 from "corpus gap analysis" to "verify ground truth has B/C tier annotations" — a 30-minute inventory task. Actual B/C detection measurement happens in Wave 6 (Plans 09-11), not before.
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Detection Accuracy & Pattern Testing Viability):** The original framing assumes corpus sparseness before measuring. The join reveals 30 B-tier and 9 C-tier patterns already exist in ground truth. Generating 8 new projects before knowing whether existing detection is broken wastes effort — if agents can't find the 30 B-tier patterns already in corpus, adding more B-tier contracts does not help. The root cause is unknown (agent capability vs corpus quality). Rewrite inverts the sequence: measure first, generate only if gap analysis confirms corpus is the bottleneck. Also corrects the factual error about B/C coverage.

---

### P7-IMP-16: Pattern Grouping Strategy Is Unaddressed — Per-Pattern Agent Spawning Will Not Scale
**Target:** CONTEXT
**What:** User asked: "group patterns/nodes/sub-agents instead of spawning a sub-agent for each pattern?" CONTEXT.md has zero mention of pattern grouping. 461 patterns (95 B-tier requiring cross-function analysis). Does one agent handle all patterns or should per-group specialists exist?
**Why:** This is a product architecture question that the testing framework should help answer via A/B experiments.
**How:** (1) Add to Deferred Ideas (post-baseline): "Pattern grouping experiments: compare (a) single-agent-all-patterns, (b) per-category-group agents, (c) per-semantic-operation agents. Use experiment ledger to track which produces highest B/C detection accuracy." (2) Note in Plan 12: "improvement loop should explore pattern grouping as hypothesis when B/C accuracy below target." (3) Do NOT build into Plans 09-11 — this is an experiment.
**Impacts:** Deferred Ideas (+pattern grouping), Plan 12 (note about grouping experiments)
**Research needed:** no — RESOLVED by GAP-12 (pass 2). Two unreconciled execution models exist: (1) bead-dispatch via vrs-orch-spawn with structured AgentContext, (2) self-directed via graph-first-template where agent runs own queries. /vrs-audit Phase 4 is too vague — CC must improvise agent spawning, making pattern context non-deterministic across runs.
**Research summary:** The /vrs-audit skill says "spawn verification agents" without specifying what context to pass. vrs-attacker.md expects structured AgentContext (pattern_hints, subgraph, focal_nodes, bead_id) but no skill provides instructions for assembling it. The evaluation framework actually tests the self-directed model where agents discover vulnerabilities via own graph queries. Top fix: add concrete Task tool spawning template to vrs-audit.md Phase 4.
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** yes — P7-IMP-11 (detection accuracy) must exist first
**Status:** implemented

---

### P7-IMP-17: Scenario Realism Has No Definition — "Realistic" Is Unspecified
**Target:** CONTEXT
**What:** User: "comprehensive fake scenarios that are as realistic and compelling as possible." No definition of "realistic" in CONTEXT.md. Existing scenarios use pedagogical contracts (50-line ReentrancyClassic.sol). Real DeFi is 500-5000 LOC with libraries, inheritance, external integrations.
**Why:** If framework only works on pedagogical contracts, it fails on real audits.
**How:** Add Implementation Decision: "Scenario Realism Tiers. Level 1 (unit): single contract, <100 LOC. Level 2 (component): 2-3 contracts, 200-500 LOC, inheritance, 2-3 vulns. Level 3 (integration): 5+ contracts, 500-2000 LOC, library imports, economic interactions, B-tier included. Core-tier tests use Level 2+. Detection accuracy tests include ≥3 Level 3."
**Impacts:** CONTEXT.md (new Implementation Decision), Scenario YAMLs (realism tags), Plans 09-10
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

---

### P7-IMP-18: No Scenario Tests the Full Audit Pipeline — Tool + Agent + Merge + Report
**Target:** CONTEXT
**What:** 32 scenario YAMLs exist. Audit scenarios test `/vrs-audit`. Tool scenarios test individual tools. No scenario tests the full E2E: build KG → run tools → spawn agents → merge findings → produce deduplicated report. The merge step and deduplication are never verified in any scenario.
**Why:** The full pipeline is what users run. Testing components in isolation is necessary but not sufficient.
**How:** (1) New scenarios: UC-AUDIT-009 "Full pipeline with tool integration" and UC-AUDIT-010 "Pipeline deduplication." Core-tier. (2) `must_happen` criteria spanning full pipeline: "BSKG built before investigation," "Slither findings referenced in agent evidence," "Final report has no duplicate findings." (3) Plans 09-11: ≥1 Core orchestrator test exercises full pipeline.
**Impacts:** Scenarios (+2), Plans 09-11
**Research needed:** no — RESOLVED by GAP-13 (pass 2). Prompt-level omission confirmed. `alphaswarm tools analyze --beads` already creates investigation beads from tool findings. Adding ~20 lines to audit.md (Phase 2.5: TOOLS) bridges the gap with zero Python code changes.
**Research summary:** `allowed-tools: Bash(alphaswarm*)` permits tool calls. `alphaswarm tools analyze --beads` runs full tool pipeline AND creates beads identical to VKG-detected beads. Agent pipeline is source-agnostic — investigates all beads regardless of origin. Fix: add Phase 2.5 TOOLS step (~15 lines) + Phase 7 supplement for LOW/MEDIUM findings + Related Skills update. UC-AUDIT-009/010 go from "blocked: feature missing" to "blocked: prompt patch needed (~1 hour)."
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

---

### P7-IMP-19: Expected Reasoning Chains in Ground Truth Are Not Wired to Evaluation
**Target:** CONTEXT
**What:** Ground truth includes `expected_reasoning_chain` with 3-4 step sequences. The 7-move reasoning evaluator scores generically. These are disconnected. The evaluator cannot distinguish "found vulnerability through wrong reasoning" (lucky guess) from "followed the correct analytical path."
**Why:** Expected reasoning chains are the most valuable signal in corpus. They define not just WHAT to find but HOW. If unused, the improvement loop cannot distinguish coincidental success from genuine understanding.
**How:** (1) Plan 07: add chain coverage dimension — fraction of expected steps in agent's trace. (2) Add `reasoning_chain_coverage: float` to `GroundTruthComparison`. (3) Semantic matching (LLM judges correspondence). (4) Contracts gain `ground_truth_ref` field. (5) N/A for scenarios without ground truth.
**Impacts:** Plan 01 (model field), Plan 07 (chain coverage dimension), Plan 06 (ground_truth_ref)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented

**Original framing:** "Expected Reasoning Chains in Ground Truth Are Not Wired to Evaluation — add chain coverage dimension to Plan 07, semantic matching via LLM."

**Adversarial note (Detection Accuracy & Pattern Testing Viability):** The framing is wrong in a subtle but important way. The existing reasoning chains (e.g., "Identify external call at line 59 → Notice state update after call → Conclude reentrancy") describe WHAT a human auditor would observe in the code, not what a BSKG-querying agent would do. An agent using graph-first reasoning would instead: (1) query BSKG for TRANSFERS_VALUE_OUT followed by WRITES_USER_BALANCE, (2) find 2 matching functions, (3) inspect them. The ground truth chains document code-reading reasoning, not graph-first reasoning. Wiring them to the 7-move evaluator is incorrect: the evaluator would penalize QUERY_FORMULATION because the agent's query ("TRANSFERS_VALUE_OUT sequence") doesn't textually match "Identify external call via msg.sender.call{value: payout}." The correct abstraction is not "chain coverage" but "outcome coverage": did the agent reach the SAME CONCLUSION as the expected chain, regardless of path? The reasoning chain's value is as a RUBRIC for the Opus evaluator, not as a structural match target. The How should say: "Embed expected_reasoning_chain as rubric text in Plan 07 evaluator prompts — evaluator judges whether agent's reasoning covers the same logical territory, not whether it follows identical steps. Do NOT attempt structural step-matching. Do NOT add chain_coverage as a float metric — LLM judges 'adequate coverage' as a binary per finding."

---

### P7-IMP-20: Aderyn and Mythril Have Zero Test Scenarios or Evaluation Contracts
**Target:** CONTEXT
**What:** 3 tool scenarios exist: UC-TOOL-001 (Slither), 002 (coordinator), 003 (failure). No Aderyn or Mythril scenarios. No evaluation contracts for either. User explicitly asked to test all tool integrations.
**Why:** If Aderyn or Mythril integration is broken, nobody knows until a user runs /vrs-audit.
**How:** (1) UC-TOOL-004 "Aderyn basic" and UC-TOOL-005 "Mythril basic." (2) Evaluation contracts at Important tier. (3) Plans 09-10: ≥1 scenario per tool. (4) Prestep P2 already tests "Slither + Aderyn on safe variants" — add Mythril.
**Impacts:** Scenarios (+2), Plan 06 (2 contracts), Plans 09-10, Prestep P2
**Research needed:** no — RESOLVED by pre-implementation. See below.
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented
**prerequisite:** yes
**Pre-implement note:** Aderyn v0.6.8 installed (pre-built binary, aarch64-apple-darwin → `~/.cargo/bin/aderyn`). `cargo install` failed (svm-rs requires Rust 1.89, we have 1.88; also svm-rs-builds has duplicate constant bug). Pre-built binary from GitHub releases worked. Verified: (1) `aderyn . --output report.json` produces parseable JSON on CrossFunctionReentrancy.sol (ran 88 detectors, 5 raw issues, 7 VKG findings via adapter). (2) `AderynAdapter.parse_json()` and `to_vkg_findings()` work on real output. (3) `alphaswarm tools status` now shows "aderyn 0.6.8 ✓ Ready". **Issues found:** (a) Adapter detector-to-pattern mapping is stale — v0.6.8 uses `reentrancy-state-change` but adapter maps `state-change-after-external-call`. All VKG pattern lookups return `None`. (b) `_parse_src` assumes `file:line:col` but v0.6.8 produces `offset:col` (e.g., "558:48"). First part parsed as filepath. (c) Aderyn v0.6.8 output has `high_issues` and `low_issues` but observed contract produced no `medium_issues` or `nc_issues` keys — verify if format changed. **Mythril investigation:** (a) `mythril_adapter.py` exists (415 LOC, fully implemented with SWC mapping). (b) `core/availability.py` registers mythril (exe: `myth`, optional tier). (c) `tool_registry.py` VERSION_PATTERNS does NOT include mythril — this is why `tools status` doesn't show it (display bug, not missing integration). (d) `uv tool install mythril` installs but crashes on `import pkg_resources` (Python 3.11 removed setuptools by default). (e) Docker available but daemon not running (OrbStack). **Conclusion:** Aderyn is functional — UC-TOOL-004 can be authored now. Mythril has full integration code but no working runtime — defer UC-TOOL-005 until either Docker setup or `setuptools` is added to mythril's venv. File Known Code Issue for both adapter mapping drift and mythril display bug.

**Adversarial note (Detection Accuracy & Pattern Testing Viability):** `alphaswarm tools status` output (verified 2026-02-19) shows: Aderyn = "Not installed," Mythril = completely absent from the status table (not even listed as a known tool). Writing test scenarios and evaluation contracts for tools that are not installed and whose integration code may not exist is authoring aspirational contracts, not real tests. The evaluation contract schema says contracts must be based on "genuine behavioral understanding" (Core contracts) or have real run validation (Important contracts). Neither is possible for uninstalled tools. This is a PREREQUISITE, not an improvement: (a) Install Aderyn (`cargo install aderyn`) and verify it produces parseable output on one corpus contract. (b) Investigate whether Mythril is in scope at all — it does not appear in tools status, suggesting the integration code does not exist. (c) Only after installation validation should scenarios and contracts be authored. The original "research needed" tag is correct but the conclusion should be PREREQUISITE not OPEN.

---

### P7-IMP-21: Pattern Improvement Feedback Loop Is Missing — Improvement Loop Targets Prompts but Not Patterns
**Target:** CONTEXT
**What:** User: "test pattern engines... do we need to redesign the entire pattern logic?" Plan 12 has improvement loop for PROMPTS (metaprompting for skills/agents). No improvement loop for PATTERNS. When evaluation reveals attacker misses B-tier vulnerability, the framework produces failure narratives about agent reasoning but not about the PATTERN. Was the pattern's semantic operation wrong? Was the BSKG query insufficiently specific? Was the graph builder missing required edges?
**Why:** User's question "do we need to redesign the entire pattern logic?" can only be answered with pattern-level feedback. If attacker consistently misses cross-function reentrancy, the fix may be in the pattern's detection query or BSKG builder's cross-function edge handling, not the agent prompt.
**How:** (1) Add to Deferred Ideas (post-baseline): "Pattern Improvement Feedback: When detection accuracy reveals consistent misses for specific patterns, generate pattern-level hypotheses: (a) semantic operation definition correct? (b) BSKG builder creates needed edges? (c) detection query too narrow/broad?" (2) Plan 12 Part 4 failure reporter: include pattern-level failure modes.
**Impacts:** Deferred Ideas (+pattern feedback), Plan 12 Part 4
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 1
**Prerequisite:** yes — P7-IMP-11 and P7-IMP-12 must exist first
**Status:** implemented

---

## Group C: Evaluation Pipeline & Execution Infrastructure

### P7-IMP-22: Plan Summaries Lack Implementer-Ready Detail — Task Breakdowns and Acceptance Criteria Missing
**Target:** CONTEXT
**What:** Expand Plans 01-08 summaries in CONTEXT.md to include task lists with ordering, per-task acceptance criteria (objectively verifiable), input/output contracts between plans at task level, and LOC estimates per task. This targets CONTEXT.md only — not separate PLAN files.
**Why:** Each plan implementation session begins with 15-30 minutes of archaeology. Plan summaries serve as an index, not as implementation guides.
**How:** For Plans 01-08, expand summaries to include: (1) Task list with ordering. (2) Per-task acceptance criteria (objectively verifiable). (3) Input/output contracts between plans at task level. (4) LOC estimate per task. This is NOT writing PLANs — it's making CONTEXT.md self-sufficient for implementation.
**Impacts:** All Plans 01-08 summaries (no structural change to plan count or waves)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

**Original framing:** "CONTEXT.md Plan Summaries provide 3-8 lines per plan. None includes task breakdowns... User directive: 'CONTEXT.md has too little context on each plan and its tasks.'"

**Adversarial note (Pipeline Execution Feasibility):** The problem diagnosis is correct (too little context), but the proposed solution — expanding 8 plan summaries inside CONTEXT.md — worsens the readability problem it claims to solve. CONTEXT.md currently has 12 plan summaries averaging ~200-300 words each after 6 passes of additions. Plans 01-12 in the current CONTEXT.md are already 2,200+ words of the 1,170-line document. Adding task lists + per-task acceptance criteria + input/output contracts + LOC estimates per task across all 8 plans would double or triple that section — easily adding 1,500-3,000 words to an already dense document. The lens_brief explicitly flags "31 improvements to a CONTEXT.md that already has 96 merged items is dangerously close to making CONTEXT.md unreadable." This improvement would be the single largest contributor to that problem.

The RIGHT abstraction is to create per-plan implementation notes in a companion file (e.g., `PLAN-NOTES.md` or individual `PLAN-{NN}.md` stubs) that are loaded on demand. CONTEXT.md should remain the architectural decision record — not the implementation guide. The correct REFRAME is: "Add a companion `IMPLEMENTATION-GUIDE.md` or per-plan stub files under `.planning/phases/3.1c-reasoning-evaluation-framework/plans/` that contain the task breakdowns and acceptance criteria. CONTEXT.md gains only a pointer: 'See plans/ directory for implementation guides.'" This resolves the archaeology problem without bloating CONTEXT.md. The What field above has been corrected to reflect this narrowed scope — if merged as-is the improvement must be understood as targeting CONTEXT.md plan summaries only, not creating new files, but the reviewer recommends the companion-file approach as a separate decision.

---

### P7-IMP-23: Pipeline Architecture Is Batch-Only — No Real-Time Feedback During Interactive Sessions
**Target:** CONTEXT
**What:** Architecture shows strictly sequential: HOOKS → Parser → Scorer → Evaluator → Runner. Runner starts AFTER session completes. Zero feedback during a 20-60 minute interactive Agent Teams session. Agent cannot course-correct based on evaluation signals.
**Why:** Post-hoc-only evaluation means 1-2 hour feedback loops for Core tier. Lightweight in-session signals ("graph-first compliance: FAIL") would enable early abort or corrective SendMessage.
**How:** (1) Add "In-Session Evaluation Signals" to Architecture. Passive signals: hooks compute derived observations in real-time (graph_first_status). Active signals: test orchestrator reads passive signals after N tool calls and decides whether to continue/abort/correct. (2) Plan 02: +1 derived field in obs_tool_use.py — `graph_first_status` (~10 LOC). (3) Plans 09-11 skill: optional mid-session checkpoint after 10th tool call.
**Impacts:** Architecture (new subsection), Plan 02 (+10 LOC), Plans 09-11 (+20 LOC)
**Research needed:** no — RESOLVED by codebase analysis (2026-02-19).

**Research answer:** No — hooks cannot reliably read their own session's JSONL mid-session in the current architecture. The adversarial note's analysis is correct on all three points.

**Evidence:**
1. **`observation_writer.py` uses `threading.Lock()`** (line 22: `_write_lock = threading.Lock()`), not `fcntl.flock()`. No `fcntl` import exists anywhere in `tests/workflow_harness/`. `threading.Lock` only protects threads within the SAME process. Each hook is a separate subprocess spawned by CC — the lock provides zero cross-process protection.
2. **Each hook is a stateless subprocess.** `obs_tool_use.py` reads JSON from stdin, calls `write_observation()`, and exits. It has no access to prior hook outputs. A "mid-session checkpoint after 10th tool call" would require a READER process that: (a) knows the session_id, (b) polls the JSONL file, (c) counts events, (d) decides to abort/continue. This reader cannot be a hook — hooks are fire-and-forget, triggered by CC events, not by polling.
3. **The CC execution model blocks polling+action interleaving.** The test orchestrator is a top-level CC session. If it enters a polling loop (reading JSONL repeatedly), it cannot simultaneously call SendMessage to correct the target session. CC processes one tool call at a time — no concurrent tool execution within a single session.
4. **`fcntl.flock()` is advisory-only** — even with it, a reader seeing a partial JSON line (write interrupted mid-flush) would get `json.JSONDecodeError`. The fix would need atomic line writes (already approximately true since `json.dumps() + "\n"` is typically under 4KB, within POSIX atomic write guarantees for regular files) PLUS explicit flock on both reader and writer.

**Architectural verdict:** The "in-session evaluation signals" concept requires a fundamentally different model than hook-reads-JSONL. Two viable alternatives exist:
- **Alternative A (file-based signal):** Hook writes a separate signal file (e.g., `.vrs/observations/{session_id}.signal`) as a simple counter/status file. Orchestrator checks this file BETWEEN tool calls (not during), using a `PreToolUse` hook on the ORCHESTRATOR session that reads the TARGET session's signal file. No polling loop needed — CC's own hook system provides the trigger.
- **Alternative B (deferred to post-session):** Accept batch-only architecture for v1. Real-time feedback is a v2 feature requiring either a sidecar process or CC's native notification system (if one is added).

**Prerequisite status unchanged:** P6-IMP-10 (fcntl.flock) is still needed for correctness of multi-process writes, but even with it, the polling+SendMessage model described in P7-IMP-23 is architecturally infeasible. If this item is pursued, it must be reframed around Alternative A.

**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** yes — P6-IMP-10 (fcntl.flock) must land first, AND the item must be reframed around signal-file architecture (Alternative A above)
**Status:** deferred
**Pre-implement note (pass 2 — resolved NEGATIVE, deferred to v2):** Research confirms the original model (hooks read JSONL mid-session) is architecturally broken on three independent grounds: (1) `threading.Lock` provides zero cross-process protection, (2) each hook is a stateless subprocess with no access to prior outputs, (3) CC cannot poll and SendMessage simultaneously. Alternative A (signal-file with PreToolUse hook on orchestrator) is viable but requires P6-IMP-10 + reframe + ~80 LOC across 3 files. Accepted: batch-only architecture for v1. Real-time feedback deferred to v2. The item's original "in-session evaluation signals" concept is sound but the implementation path requires CC features (concurrent tool calls or sidecar process support) that don't exist.

**Adversarial note (Pipeline Execution Feasibility):** Two compounding blockers make this improvement unfeasible in its current form.

**Blocker 1 — fcntl.flock is not yet implemented.** P6-IMP-10 requires replacing `threading.Lock()` with `fcntl.flock()` in `observation_writer.py`. Inspection of the actual file (line 77: `with _write_lock:`) confirms `threading.Lock` is still in use. No `fcntl` import exists anywhere in the `tests/workflow_harness/` directory. The improvement correctly identifies this dependency, but marks it as a prerequisite note rather than flagging that the prerequisite does not yet exist.

**Blocker 2 — The read-your-own-JSONL model is architecturally broken even with flock.** Each hook script is a separate subprocess spawned by CC for each tool call. It writes to `.vrs/observations/{session_id}.jsonl`. A "mid-session checkpoint" after the 10th tool call means: the test orchestrator (a CC top-level session, per the Execution Model) reads the JSONL while the target CC session is still running. `fcntl.flock()` is advisory — it prevents concurrent writes but does not prevent a reader from reading a partially-written file. Worse: the test orchestrator is itself a separate process from the target CC session. The orchestrator reading the JSONL mid-session to decide "abort/continue/correct" requires a polling loop that: (a) knows the session_id of the target session (which is written at startup by obs_session_start.py — fine), (b) can reliably distinguish "10th tool call not yet reached" from "session stalled", and (c) can act on the decision via SendMessage. Point (c) is the fatal issue: **Agent Teams cannot be spawned from subagents** (CONTEXT.md Execution Constraint). The test orchestrator IS a top-level session, but if it enters a polling loop reading a JSONL file, it is blocked from calling SendMessage until the poll completes. The whole proposal requires the orchestrator to be doing two things simultaneously — which CC cannot do.

This is not an enhancement problem; it is a wrong-model problem. The framing "hooks compute derived observations in real-time" presupposes hooks have access to prior hook outputs, which they do not — each hook subprocess is stateless. Mark as PREREQUISITE: P6-IMP-10 (fcntl.flock) must land AND a proof-of-concept of the polling + SendMessage interleaving must succeed in a real CC session before this improvement can be specified correctly.

---

### P7-IMP-24: EvaluationPlugin Protocol Still Missing context Kwarg — 6 Passes Documented, Never Gated
**Target:** CONTEXT
**What:** Known Code Issue documented since Pass 5. `models.py:136` still declares `score(self, collected_output: Any)` without `context`. Meanwhile `reasoning_evaluator.py:201` calls with `context=context`. Fix is 1 line but has never been marked as exit criterion.
**Why:** Runtime-checkable Protocol won't catch signature mismatch (PEP 544). Plugins without context will fail silently.
**How:** (1) Add Plan 01 exit criterion: "`EvaluationPlugin.score()` includes `context: dict[str, Any] | None = None`." (2) Move from Known Code Issue to Plan 01 Task 1.
**Impacts:** Plan 01 (hard exit criterion), models.py (1-line fix)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Pipeline Execution Feasibility):** The improvement correctly identifies a real bug but the "Why" understates the actual failure mode. Confirmed by reading `models.py:136` — the Protocol declares `score(self, collected_output: Any) -> PluginScore` with no `context` parameter. Reading `reasoning_evaluator.py:201` confirms `plugin.score(collected_output, context=context)` is called with `context` as a keyword argument. Under Python's `@runtime_checkable` Protocol, `isinstance()` checks only verify that the method EXISTS — not its signature. So a plugin implementing `score(self, output)` passes `isinstance(plugin, EvaluationPlugin)` but raises `TypeError: score() got an unexpected keyword argument 'context'` at runtime, silently swallowed if the runner has a broad `except Exception` catch (which the runner at line 202-210 does via `except FileNotFoundError` only — other exceptions propagate). This is a silent DATA CORRUPTION bug, not just a type error: when plugins fail with TypeError, the runner produces a zero-score `ScoreCard` attributed to `FileNotFoundError`, making it appear as "contract not found" rather than "plugin signature mismatch."

The How should add: (3) Add a unit test that instantiates a compliant plugin and one missing `context`, verifies `isinstance` passes for both, then verifies the compliant one succeeds and the non-compliant one raises `TypeError` when called with `context={}`. This documents the PEP 544 trap for future contributors. The fix must happen in Wave 1 (same commit as Plan 01) before any downstream consumer writes a plugin.

---

### P7-IMP-25: Mode Capability Matrix Is Dead Letter — Runner Has No Mode-Aware Filtering
**Target:** CONTEXT
**What:** P6-IMP-06 merged as "Mode Capability Matrix" in Implementation Decisions. But `evaluation_runner.py` has no mode-aware filtering. `DimensionScore` has no `applicable: bool`. `ScoreCard.overall_score` is a plain `int` with no mode-dependent computation.
**Why:** Without implementation path in Plan 08 summary, headless and interactive scores are computed identically. The locked decision is a dead letter.
**How:** (1) Plan 01: `DimensionScore` gains `applicable: bool = True`. (2) Plan 08 task: "Apply Mode Capability Matrix — set `applicable=False` for unavailable dimensions." (3) `ScoreCard.effective_score()` method excludes non-applicable dimensions. (4) Plan 12 baseline uses `effective_score()`.
**Impacts:** Plan 01 (field), Plan 08 (filtering task), ScoreCard (method), Plan 12 (baseline)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Pipeline Execution Feasibility):** Confirmed by reading `evaluation_runner.py` (no mode filtering), `models.py` (`DimensionScore` has no `applicable` field, `ScoreCard.overall_score` is a plain `int`). The improvement is correct, the fix is well-specified, and the plan-level routing is accurate. Second-order effect worth noting: `ScoreCard.effective_score()` must replace `ScoreCard.overall_score` in ALL Plan 12 baseline comparisons, not just be added as an alternative method. If both properties coexist, implementers will use `overall_score` by habit. The CONTEXT.md update should explicitly state: "Plan 12 MUST use `effective_score()` exclusively for baseline keying. `overall_score` is deprecated for baseline use."

---

### P7-IMP-26: Contract Healer Should Activate During Wave 6 Core Sub-Wave, Not Wave 7
**Target:** CONTEXT
**What:** P6-IMP-15 promoted contract_healer to v1 but still in Plan 12 Part 5 (Wave 7). Between Wave 1 (contract authoring) and Wave 7, contracts are static. Core workflows run 5x during Wave 6 — contract_healer needs only 5 runs to detect ceiling/floor/zero-variance anomalies.
**Why:** User wants "self-healing" contracts. Static contracts for 6 waves is the opposite. The healer should activate DURING Wave 6 Core sub-wave.
**How:** (1) Move basic contract_healer activation to Plan 06 exit criterion: after Core contracts tested 5x, run healer, fix anomalies before Important tier. (2) Core sub-wave gate includes: "contract_healer reports zero anomalies." (3) Keep full healing (propagation, versioning) in Plan 12b.
**Impacts:** Plan 06 (exit criterion), Wave 6(a) gate, Plan 12 (reduced scope)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** yes — BaselineManager must have 5 Core runs AND contract_healer basic anomaly detection must be scoped to Plan 08
**Status:** implemented
**Pre-implement note (pass 2 — resolved, reframed to Plan 08):** The circular dependency (Plan 06 gate → Plan 12 code → Plan 06 contracts) is confirmed and unresolvable in the current wave ordering. Adversarial note's resolution accepted: (1) Extract basic anomaly detection (ceiling/floor/zero-variance checks) from Plan 12 Part 5 into Plan 08 (the Runner, Wave 5). Plan 08 already receives all run results and can detect anomalies after the 5th Core run. (2) The Plan 06 exit criterion is the wrong target — change to Plan 08 exit criterion: "After 5 Core-tier runs, anomaly detection reports zero ceiling/floor/zero-variance issues." (3) Full healing (propagation, versioning, contract rewriting) stays in Plan 12b. This eliminates the circular dependency: Plan 08 (Wave 5) runs anomaly detection using only `EvaluationResult` data it already has, no dependency on Plan 12.

**Adversarial note (Pipeline Execution Feasibility):** The improvement has two independent prerequisites that are not both acknowledged.

**Prerequisite 1 (acknowledged):** BaselineManager must have 5 Core runs. This is correct and documented.

**Prerequisite 2 (unacknowledged — more critical):** `contract_healer.py` does not exist yet. The improvement says "move basic contract_healer activation to Plan 06 exit criterion" but contract_healer is currently a stub placeholder in the intelligence module plan (Plan 12 Part 5). It has zero LOC implemented. Moving an activation condition for a module that doesn't exist yet creates a gate that is permanently unpassable until Plan 12 is partially implemented — which violates the wave ordering (Plan 12 is Wave 7, Plan 06 is Wave 1). The improvement creates a circular dependency: Plan 06 exit criterion requires contract_healer, which is Plan 12 scope, which depends on Plan 06's contracts.

The correct resolution is: (a) contract_healer stub must be extracted from Plan 12 into Plan 01 scope (~5 LOC interface definition only), (b) basic anomaly detection logic (ceiling/floor/zero-variance) promoted to Plan 08 scope (Wave 5, the Runner) as a post-run analysis step, NOT Plan 06 (Wave 1, the Contracts). Plan 08 already receives all run results and can run the healer after the 5th Core run. The Plan 06 exit criterion change is wrong — it should be a Plan 08 exit criterion. Mark as PREREQUISITE: contract_healer must be scoped to Plan 08 (not Plan 12) before this improvement is implementable.

---

### P7-IMP-27: Debate Timeout Silently Produces Single-Rater Scores That Enter Baseline
**Target:** CONTEXT
**What:** P6-IMP-14 (debate) and P6-IMP-20 (timeout) interact: Core transcript → Evaluator A (5 min) → Blind B (4 min) → 3 dimensions disagree → debate (6 min) → total 15 min but budget is 900s. Debate times out. B's blind scores recorded but debate resolution lost. `EvaluatorDisagreement` has `resolved_score` but no `debate_completed` field. Runner records `evaluation_complete: true`. Unresolved disputes use lower score (tie-breaking). Baseline absorbs artificially low scores.
**Why:** Undebated disagreement ≠ genuinely contested disagreement. Baseline needs to distinguish them.
**How:** (1) Add `debate_completed: bool = True` to `EvaluatorDisagreement`. (2) If any disagreement has `debate_completed: False`, set `evaluation_complete: False`. (3) BaselineManager filters these out. (4) HITL 07: verify timeout produces correct flags.
**Impacts:** Plan 01 (field), Plan 08 (partial detection), Plan 12 (filtering), HITL 07
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Pipeline Execution Feasibility):** The bug description is accurate: `EvaluatorDisagreement` lacks `debate_completed`, and `evaluation_runner.py` line 237-249 builds `EvaluationResult` without any partial-evaluation detection logic. The fix is well-scoped and low-risk. Second-order effect: BaselineManager's filter for `evaluation_complete: False` means that in practice, if the debate timeout fires on every Core run (because debates reliably exceed the 900s budget for transcripts with >3 contested dimensions), the baseline will NEVER have valid entries. The improvement should add: "(5) If >50% of Core baseline entries are `evaluation_complete: False`, surface a warning: 'Debate timeout is systematic — increase budget or reduce debate trigger threshold.' This prevents a silent baseline starvation."

---

### P7-IMP-28: ObservationRecord.data Is Untyped — tool_use_id Has No Schema Guarantee
**Target:** CONTEXT
**What:** P6-IMP-09 makes `tool_use_id` a hard Plan 02 exit criterion. But `ObservationRecord` has `data: dict[str, Any]` catch-all. Parser must extract from `data["tool_use_id"]` with no guarantee. If a hook writes `data["id"]` or `data["toolUseId"]`, pairing silently fails.
**Why:** The schema is the contract between hooks (Plan 02) and parser (Plan 03). Untyped `data` produces the same class of bug as current LIFO.
**How:** (1) Add submodels to Plan 01: `ToolUseData(tool_name, tool_use_id, tool_input)`, `ToolResultData(tool_use_id, output_preview)`. (2) `ObservationRecord` validator: if event_type in (tool_use, tool_result), data must contain tool_use_id. (3) Plan 02 hooks produce typed data. Plan 03 parser consumes typed fields.
**Impacts:** Plan 01 (typed data submodels), Plan 02 (hooks), Plan 03 (parser)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Pipeline Execution Feasibility):** The improvement is correct. Confirmed by reading `models.py:64` — `data: dict[str, Any]` with no discriminated union. Confirmed by reading `obs_tool_use.py` — it writes `tool_input_keys` and `tool_input_preview` but zero `tool_use_id`. Confirmed by reading `obs_tool_result.py` — writes `tool_name` and `result_preview` but zero `tool_use_id`. These hooks have never captured `tool_use_id`. The LIFO pairing at `observation_parser.py:161-163` is the only pairing mechanism, and it is structurally broken for parallel tool calls.

However, the How has a design problem: adding a Pydantic validator to `ObservationRecord` that rejects records missing `tool_use_id` on `tool_use`/`tool_result` events will BREAK all existing tests. The 298 tests use synthetic data that does not include `tool_use_id` in hook-format records. The fix should be staged: (a) add `ToolUseData` and `ToolResultData` as optional submodels in Plan 01; (b) Plan 02 hooks produce typed data with `tool_use_id`; (c) Plan 03 parser uses typed submodels when present, falls back to LIFO only when absent (with a warning, not a crash); (d) after Plan 02 delivers real `tool_use_id` capture, add the hard validator as a Wave 2 gate. Making it immediately hard-required breaks backward compatibility with all existing synthetic test data before Plan 02 is implemented.

---

### P7-IMP-29: EvaluationResult Missing 4+ Fields Required by Merged P6 Improvements
**Target:** CONTEXT
**What:** Plan 01 summary says "~22 v1 core types" but doesn't enumerate fields added by P6 decisions. Missing from Plan 01 scope: `improvement_hints: list[ImprovementHint]` (P6-IMP-17), `evaluation_complete: bool` (P6-IMP-20), `evaluator_disagreements: list[EvaluatorDisagreement]` (P6-IMP-14), `calibration_anchor_result` (P6-ADV-03).
**Why:** Gap between "merged improvement decision" and "Plan 01 task list" means implementers miss fields.
**How:** Add explicit enumeration to Plan 01 summary: "Fields to add to EvaluationResult: improvement_hints, evaluation_complete, evaluator_disagreements, calibration_anchor_result. Fields to add to DimensionScore: applicable. New models: ImprovementHint, EvaluatorDisagreement, EvaluationProgress."
**Impacts:** Plan 01 summary (expanded enumeration)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Pipeline Execution Feasibility):** Confirmed by reading `models.py`. Current `EvaluationResult` (line 295-341) has none of the four fields listed. `DimensionScore` (line 165-193) has no `applicable` field. The `ImprovementHint`, `EvaluatorDisagreement`, and `EvaluationProgress` models do not exist in `models.py`. The enumeration fix is purely additive to a CONTEXT.md summary — zero risk of breaking existing code. The improvement is correct and necessary to prevent implementers from reading the Plan 01 summary and believing the 22 existing types are complete. Cross-group note: P7-IMP-25 also adds `applicable: bool` to `DimensionScore` — these two improvements must be merged into a single Plan 01 task to avoid duplication.

---

### P7-IMP-30: Kill Action and Agent Grouping for Testing Is Unaddressed
**Target:** CONTEXT
**What:** User: "test grouping and kill actions for agents/workflows." No mechanism to: (a) abort a specific workflow evaluation while others continue, (b) kill a tier group, (c) abort suite preserving partial results. No documented way to run only a specific group (e.g., "only investigation agents" or "only Core tier").
**Why:** 6+ hour run without kill capabilities means any mid-run problem requires killing the entire process and losing results.
**How:** (1) Plan 08: `--tier core` and `--category investigation` filters. SIGINT handler writes progress, marks current as `interrupted`, exits cleanly. (2) Plans 09-11 skill: scope parameters `tier`, `category`, `workflow_ids`. (3) Add `status: Literal["completed", "interrupted", "failed", "skipped"]` to EvaluationProgress per-workflow entries.
**Impacts:** Plan 08 (filters, SIGINT handler), Plans 09-11 (scope params), Plan 01 (status field)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented

**Adversarial note (Pipeline Execution Feasibility):** The improvement is correct in identifying the missing kill capability, and the Python-side SIGINT handler in Plan 08 (the EvaluationRunner) is straightforward to implement. However, the "kill a running CC session" scenario is not addressed. The What says "abort a specific workflow evaluation while others continue" — but each CC session (skill run, agent run) is a subprocess started by `claude --print` or similar. Killing it requires `subprocess.Popen.terminate()` or `os.kill(pid, SIGINT)` on the CC process, not just a Python SIGINT handler on the runner. The How needs: "(4) Plan 08 `EvaluationRunner` maintains a `_current_session_pid: int | None` field. SIGINT handler calls `os.kill(self._current_session_pid, signal.SIGTERM)` before writing progress and exiting. Without this, SIGINT on the runner leaves the CC subprocess running as an orphan, consuming tokens with no consumer for its output."

For Plans 09-11 (the CC skill `/vrs-test-suite`): SIGINT to the outer Python process that invoked `claude -p skill:vrs-test-suite` will not propagate to the CC session. The CC session continues running. The scope parameters `--tier core` and `--category investigation` are correct for PRE-RUN filtering but do not address MID-RUN kill. The improvement should add a kill_file mechanism: runner writes `.vrs/evaluations/kill.signal` when SIGINT received; the CC skill polls for this file between workflows and exits cleanly if found.

---

### P7-IMP-31: Graph Knowledge "Bubbling" Across Agent Boundaries Has No Evaluation
**Target:** CONTEXT
**What:** GVS scores individual agent graph usage. No test verifies whether graph query results from attacker are accessible to verifier. `EvidenceFlowEdge` exists in output_collector.py but has no evaluation consumer. If attacker finds vulnerability via BSKG but verifier cannot access those results, multi-agent architecture fails silently.
**Why:** User: "verify agents use graph knowledge and that it's bubbled correctly." GVS scores agents individually but nobody checks cross-agent knowledge flow.
**How:** (1) Add "Knowledge Bubbling" as Plan 11 evaluation dimension. (2) Test: count evidence nodes cited by both attacker and verifier. If attacker cited X and verifier's assessment ignores X, `evidence_flow_score` is penalized. (3) Wire `EvidenceFlowEdge` into orchestration contracts. (4) HITL 11: "verify evidence flow edges exist between attacker findings and verifier assessment."
**Impacts:** Plan 11 (new dimension), Plan 06 (orchestration contracts), HITL 11
**Research needed:** yes — How does CC handle knowledge transfer between subagents? Does verifier receive attacker's output or summary?
**Status:** implemented

**Original framing:** "GVS scores individual agent graph usage. No test verifies whether graph query results from attacker are accessible to verifier."

**Adversarial note (Pipeline Execution Feasibility):** The "knowledge bubbling" framing assumes that BSKG query results are shared between agents as graph data. This is the wrong model of how CC Agent Teams work. In CC Agent Teams, agents communicate via SendMessage (text) and task outputs (text). There is no shared graph memory or structured object passing. The attacker's BSKG query results are visible only in the attacker's own context window. The verifier receives what the orchestrator explicitly sends via SendMessage — which is typically a text summary of findings, not the raw node IDs or graph traversal results.

This means "graph knowledge bubbling" is actually "text-to-text knowledge transfer fidelity" — a fundamentally different problem. The right evaluation question is not "did the verifier receive attacker's graph node IDs?" but "did the orchestrator's SendMessage preserve enough evidence specificity for the verifier to reach a valid verdict?" The node-ID citation comparison proposed in the How will produce zero matches by design — not because of a bug, but because the verifier never receives node IDs.

The correct framing for the CONTEXT.md addition is: "Evidence Fidelity Across Handoffs" — measure whether the structured evidence in attacker findings (function names, vulnerability class, severity) survives the text serialization through SendMessage into the verifier's assessment. This is evaluable with existing `EvidenceFlowEdge` if it captures semantic content rather than node IDs. The research question should be: "What structured evidence format does the orchestrator use in SendMessage to verifier? Does it include function names that can be compared to attacker's raw BSKG results?"


---

## New Items from Adversarial Review

---

### P7-ADV-01: The "Self-Improving" Identity Has No Activation Criteria — The Loop Can Run Forever Without Declaring Convergence or Failure
**Target:** CONTEXT
**Source:** Adversarial review (Self-Improvement Architecture Coherence)
**What:** Plan 12 specifies improvement loop mechanics (3-5 variants per dimension, experiment ledger, metaprompting) but has no termination criteria other than "human decides." The loop can produce 20 improvement cycles on QUERY_FORMULATION, each showing marginal gains (52 → 55 → 57 → 59), with no mechanism to declare "this dimension has converged" or "this dimension requires architectural redesign, not prompt tweaking." The only stopping rule is exit gate 17 (one demonstrated cycle) plus the implicit "human has final word." Without convergence criteria, the improvement loop is an infinite maintenance burden, not a self-improving system.

**Why:** A self-improving system that never declares convergence or failure is not self-improving — it is self-running. The distinction matters for Phase 3.2 readiness: if Phase 3.1c improvement loop never terminates, Phase 3.2 (First Working Audit) cannot begin. The user's vision explicitly includes "redesign needed" as an output — but the loop has no mechanism to produce that output automatically based on cycle count or score trajectory.

**How:** Add to Plan 12 Part 3: "Convergence detection — after N improvement cycles on a single dimension (N=5 for Core, N=3 for Important), if improvement is <2 points per cycle for the last 2 cycles, declare convergence mode: (a) CONVERGED_HIGH if score > 70 — dimension is performing adequately; (b) CONVERGED_PLATEAU if 40 < score <= 70 — plateau detected, add to `pending_redesign_candidates.yaml` for human review; (c) CONVERGED_LOW if score <= 40 after N cycles — declare architectural failure, generate FailureReport with `recommendation: redesign_needed`, halt further attempts on this dimension." This is ~40 LOC of scoring trajectory analysis and is a prerequisite for the improvement loop being genuinely self-determining rather than human-supervised-indefinitely.

**Impacts:** Plan 12 Part 3 (convergence detection ~40 LOC), Plan 01 (`pending_redesign_candidates.yaml` entry model), Exit gate 17 (add: "improvement loop declares convergence or failure on at least one dimension")
**research_needed:** no
**Confidence:** HIGH
**Status:** implemented

**Adversarial note (Self-Improvement Architecture Coherence):** The gap is not addressed by any existing item. P7-IMP-10 adds a gate requiring one demonstrated cycle, but does not address what happens after multiple cycles with no progress. P7-IMP-08 adds a FailureReport but does not specify when the report is triggered automatically vs manually. The convergence detection fills the gap between "one cycle demonstrated" (gate 17) and "the framework actually terminates gracefully." Without it, Phase 3.1c technically closes at gate 17 but leaves a permanently running improvement loop with no declared exit state.

---

---


---

### P7-ADV-02: GroundTruthAdapter Is a Missing Component Blocking P7-IMP-11, P7-IMP-12, and P7-IMP-19
**Target:** CONTEXT
**What:** `OutputParser._is_match()` expects ground truth entries with a `location` field (string). All 15 ground truth YAML files use `contract`, `function`, and `line_range` fields instead. `ground_truth.get("location", "")` returns empty string on every corpus entry. The practical consequence: any attempt to run detection accuracy testing via `calculate_accuracy()` against corpus ground truth produces 0% recall and 0% precision regardless of agent quality — every agent finding is a false positive, and every ground truth entry is a false negative. This is not a wiring gap; it is a schema mismatch that renders the entire `OutputParser.calculate_accuracy()` call path unusable on corpus data as-is. Additionally, ground truth entries have `pattern_id` (e.g., `balance-update-after-transfer`) while agents report findings in whatever format their prompts specify — there is no enforced schema on agent output `pattern` field values.
**Why:** P7-IMP-11 says "reuse `OutputParser.calculate_accuracy()`" as if it is ready to wire. P7-IMP-12 adds per-tier accuracy tracking. P7-IMP-19 adds reasoning chain coverage. All three depend on ground truth matching working correctly. None of them work without a normalization layer. This gap will not be discovered until the pipeline runs against corpus data and produces nonsensical 0% metrics that look plausible because the code runs without errors.
**How:** (1) Add `GroundTruthAdapter` to Plan 01 scope (new model, ~30 LOC): `normalize(entry: dict) -> dict` maps `{pattern_id, contract, function, line_range}` to `{pattern: entry["pattern_id"], location: f"{entry['contract']}.{entry['function']}:{entry['line_range']}"}`. (2) Add `AgentFindingNormalizer` to Plan 01 scope (~20 LOC): validates agent output has `pattern` field and normalizes synonyms. (3) `GroundTruthComparison` uses adapted form, not raw YAML. (4) Add to Known Code Issues: "`OutputParser._is_match()` expects `location` field absent from corpus ground truth YAMLs." (5) Add Plan 03 task: validate adapter produces correct matches on 3 known ground truth entries before wiring into evaluation pipeline.
**Impacts:** Plan 01 (2 new models), Plan 03 (adapter validation task), Known Code Issues, Plans 09-10 (use adapter), P7-IMP-11 How (adapter is Step 2), P7-IMP-12 How (adapter prerequisite)
**Research needed:** no
**Confidence:** HIGH — verified by reading `output_parser.py:279-314` and all 15 ground truth YAML files
**Prerequisite:** no
**Status:** implemented

**Source:** Adversarial review (Detection Accuracy & Pattern Testing Viability)
**Adversarial note (Detection Accuracy & Pattern Testing Viability):** This gap is invisible in code review because `calculate_accuracy()` runs without errors — it just silently returns wrong results. The schema mismatch was discovered by cross-referencing actual ground truth YAML field names against `_is_match()`'s expected field names. Any implementation of P7-IMP-11 that does not include this adapter will pass unit tests (which use hand-crafted `{"pattern": ..., "location": ...}` dicts) and fail silently on real corpus data.

---

### P7-ADV-03: The 10 Uncatalogued Ground Truth Patterns Are a Correctness Risk, Not a Coverage Gap
**Target:** CONTEXT
**What:** Cross-referencing the 77 unique `pattern_id` values in corpus ground truth against `pattern-catalog.yaml` reveals 10 patterns that appear in ground truth but have no catalog entry: `delegatecall-to-untrusted`, `dos-unbounded-loop`, `flash-loan-price-manipulation`, `frontrunning-vulnerability`, `missing-access-control`, `oracle-stale-price`, `precision-loss-rounding`, `signature-replay`, `state-machine-violation`, `vault-share-inflation`. These are not obscure patterns — `dos-unbounded-loop`, `oracle-stale-price`, and `precision-loss-rounding` appear frequently in corpus findings. Because they have no catalog entry, they have no tier assignment, no VulnDoc path, no semantic operations, and no BSKG detection query. When detection accuracy testing runs, if an agent correctly identifies a `dos-unbounded-loop` vulnerability, it will be measured against a ground truth entry with no catalog metadata — the per-tier accuracy tracking (P7-IMP-12) will exclude it from B/C counting since tier is unknown, and the pattern-level feedback loop (P7-IMP-21) cannot generate pattern hypotheses for it.
**Why:** These 10 patterns represent common, high-value vulnerability types. Excluding them from per-tier measurement while counting them in total recall creates misleading accuracy metrics. Worse, if agents consistently find these patterns but they are labeled "uncatalogued," the detection system appears to have gaps that don't exist.
**How:** (1) Add to Known Code Issues: "10 ground truth patterns have no catalog entry — tier unknown, VulnDoc missing." (2) As part of Prestep P6 (P7-IMP-12): for each of the 10 patterns, decide: (a) add to catalog with tier/vulndoc_path, or (b) annotate ground truth entries as `tier: "uncatalogued"` so accuracy tracking can flag them explicitly rather than silently mismatch. (3) `GroundTruthComparison` must handle `tier: null` entries without crashing — count them separately as "uncatalogued" in per-tier breakdown. (4) Do NOT silently exclude uncatalogued patterns from recall computation — they count toward total recall even if they don't count toward per-tier recall.
**Impacts:** Known Code Issues (new entry), Prestep P6 (5 decisions, not just join), Plan 01 (GroundTruthComparison handles null tier), Plans 09-10 (per-tier accuracy reports "uncatalogued: N")
**Research needed:** no
**Confidence:** HIGH — verified by join
**Prerequisite:** no
**Status:** implemented

**Source:** Adversarial review (Detection Accuracy & Pattern Testing Viability)
**Adversarial note (Detection Accuracy & Pattern Testing Viability):** The 10 uncatalogued patterns include `dos-unbounded-loop` and `oracle-stale-price` — two of the most commonly reported vulnerability types in DeFi audits. These are not edge cases. Their absence from the catalog suggests the catalog and the corpus evolved independently. This is a data integrity issue that will corrupt per-tier accuracy metrics if not handled explicitly before evaluation runs.

---

### P7-ADV-RG-01: BSKGQuery JSON Extraction Must Handle TOON Format and Truncation
**Target:** CONTEXT
**Source:** Adversarial review of GAP-11 research (Agent Pipeline Evidence Quality lens)
**What:** GAP-11 recommends BSKGQuery parse `result_snippet` as JSON to extract node labels. Three edge cases invalidate the naive approach: (1) `build-kg` defaults to `--format toon`, not JSON — only `query` command outputs JSON. Extraction must guard on query_type. (2) `BSKG_RESULT_TRUNCATE_LEN = 2000` truncates large JSON results mid-structure, causing `JSONDecodeError`. Must wrap in try/except. (3) Contract name is absent from `_serialize_node()` output — requires `CONTAINS_FUNCTION` edge traversal or file path derivation.
**Why:** Without these guards, the ground_truth_coherence dimension silently returns 0.0 on TOON outputs and crashes on truncated JSON. This is a silent correctness failure that would degrade evaluation quality without error messages.
**How:** (1) Plan 02: BSKGQuery extraction must guard `query_type in {"query", "pattern-query"}` before JSON parsing. (2) Wrap `json.loads()` in try/except, return empty lists on parse failure. (3) Ground truth schema matches on `function` + `file` (not `function` + `contract`). LOC estimate: ~30 (up from ~20).
**Impacts:** Plan 02 (+10 LOC over GAP-11 estimate), Plan 06 (ground truth schema change: file instead of contract)
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

---

### P7-ADV-RG-02: Plan 12 Must Use CC LLM Agent Path Exclusively — Python AttackerAgent Is Prompt-Insensitive
**Target:** CONTEXT
**Source:** Adversarial review of GAP-12 research (Agent Pipeline Evidence Quality lens)
**What:** GAP-12 recommended "use Python agent path for fast iteration in Plan 12 improvement loop." This is wrong. The Python `AttackerAgent` class runs deterministic strategy selection — it is prompt-insensitive. Running improvement experiments (metaprompting) against it produces null improvement signals. The evaluation framework targets the CC LLM agent (vrs-attacker.md prompt) exclusively. Plan 12's Calibration Anchor Protocol (Part 0) and improvement experiments (Part 2) must both use CC agent spawning via Task tool.
**Why:** If Plan 12 improvement loop runs against the wrong execution path, it will report "no improvement possible" (because prompts don't affect the Python path), leading to false convergence detection and premature termination.
**How:** (1) Add explicit note to Plan 12 in CONTEXT.md: "All improvement experiments and calibration runs MUST use the CC LLM agent path (Task tool spawning vrs-attacker.md), NOT the Python AttackerAgent class." (2) Plan 12 Part 0 specification: agents are spawned via `Task(subagent_type="BSKG Attacker")`, not via `AttackerAgent.analyze()`.
**Impacts:** Plan 12 (Part 0 and Part 2 clarification), CONTEXT.md (decision record)
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

---

## Adversarial Review: Self-Improvement Architecture Coherence
**Items reviewed:** 10 (P7-IMP-01 through P7-IMP-10)
**Verdicts:**
- REFRAME: 1 (P7-IMP-01 — Plan 12a is not a new plan, it is 30 LOC in Plan 08)
- CONFIRM: 2 (P7-IMP-02, P7-IMP-07)
- ENHANCE: 5 (P7-IMP-03, P7-IMP-05, P7-IMP-06, P7-IMP-08, P7-IMP-10)
- REJECT: 1 (P7-IMP-09 — coverage_fraction is computable from existing DimensionScore.applicable, hardcoded constants contradict Mode Capability Matrix, exit gate floor contradicts Standard tier lite evaluation policy)
- CONFIRMED: 1 (P7-IMP-04)
- CREATE: 1 (P7-ADV-01 — convergence/termination criteria for improvement loop)

**Cross-group conflicts:**
- P7-IMP-01 (Group A) vs P7-IMP-25 (Group C): Both target `DimensionScore` fields. P7-IMP-01 (reframed) adds `ExperimentLedgerEntry` to Plan 01; P7-IMP-25 adds `applicable: bool` to `DimensionScore`. No conflict — different fields.
- P7-IMP-09 (Group A, REJECTED) vs P7-IMP-25 (Group C): P7-IMP-09 proposes a `coverage_fraction` field on `EvaluationResult`; P7-IMP-25 proposes `applicable: bool` on `DimensionScore`. If P7-IMP-09 were accepted, the `coverage_fraction` would be computable from `DimensionScore.applicable` introduced by P7-IMP-25. Rejection of P7-IMP-09 removes the redundancy.
- P7-IMP-06 (Group A) vs P7-IMP-10 (Group A): P7-IMP-10 exit gate 17 condition (f) requires "external detection validation passes" — this is a hard dependency on P7-IMP-06 being accepted. If P7-IMP-06 is rejected, condition (f) must be dropped from gate 17. Both items enhanced to note this dependency.
- P7-IMP-03 (Group A) vs P7-IMP-26 (Group C): Both address `contract_healer`. P7-IMP-03 adds integration constraints (propose-only, no auto-apply); P7-IMP-26 moves activation to Wave 6(a). These are complementary, not conflicting. The propose-only constraint from P7-IMP-03 applies to the early activation proposed by P7-IMP-26.
- P7-ADV-01 (created) vs P7-IMP-08: Both relate to FailureReport generation. P7-IMP-08 defines the schema; P7-ADV-01 defines the automatic trigger. Complementary — P7-ADV-01 depends on P7-IMP-08's FailureReport model existing.

**Second-order risks:**
1. P7-IMP-01 (reframed): Moving `ExperimentLedgerEntry` and `ImprovementAttempt` to Plan 01 increases Plan 01's model count from ~26 to ~30+. The Plan 01 summary already says "~22 v1 core types" and P7-IMP-29 notes it's already diverged. The combined effect of P7-IMP-01 + P7-IMP-29 + P7-IMP-08 (FailureReport) + P7-IMP-27 (EvaluatorDisagreement field) is Plan 01 growing to ~35 models. This may push Plan 01 LOC estimate beyond its current ~60% pre-addressed state into territory requiring a full authoring session.
2. P7-IMP-06 (enhanced): The corpus validation runs required for each experiment ledger entry add significant runtime cost. The headless run_mode mitigation reduces this but adds a new constraint that corpus validation must function correctly in headless mode — which itself requires Plan 02 (hooks) and Plan 08 (runner) to be stable.
3. P7-IMP-05 (enhanced — Jujutsu confirmed safe): The jj workspace shows committed state, not the dirty working tree. If the main worktree has modified (uncommitted) hooks during Plan 12 improvement loop execution, the workspace will NOT have those modifications. Plan 12 must either commit hooks before creating variants or explicitly copy modified hooks into the workspace. This is an operational prerequisite not yet documented.
4. P7-ADV-01 (created): Adding convergence detection to Plan 12 increases Plan 12 Part 3's LOC by ~40 and adds a new file artifact (`pending_redesign_candidates.yaml`). This artifact must be included in the Plan 12 deliverable list and should be git-ignored or stored under `.vrs/` to avoid polluting the repo.

## Adversarial Review: Detection Accuracy & Pattern Testing Viability
**Items reviewed:** 11 (P7-IMP-11 through P7-IMP-21)
**Verdicts:**
- ENHANCE: 3 (P7-IMP-11, P7-IMP-12, P7-IMP-15)
- CONFIRM: 0
- RESEARCH: 0
- REJECT: 0
- CREATE: 2 (P7-ADV-02, P7-ADV-03)
- PREREQUISITE: 2 (P7-IMP-13, P7-IMP-20)
- REFRAME: 1 (P7-IMP-19)
- OPEN (unchanged): 3 (P7-IMP-14, P7-IMP-16, P7-IMP-17, P7-IMP-18, P7-IMP-21)

**Cross-group conflicts:**
- P7-IMP-11 (Group B) proposes adding `GroundTruthComparison` to Plan 01. P7-IMP-29 (Group C) lists missing fields for `EvaluationResult` and `DimensionScore`. These are additive and do not conflict, but Plan 01 is accumulating scope from 6+ different improvements across both groups. The Plan 01 summary in CONTEXT.md needs consolidation to prevent implementers from missing fields added by different passes.
- P7-IMP-13 (finding merge testing) and P7-IMP-18 (full audit pipeline scenario) both require Slither → agent → merge to work end-to-end. P7-IMP-18 proposes Core-tier scenarios requiring this, while P7-IMP-13 is marked Important-tier. If P7-IMP-13 is a PREREQUISITE (merger input format must be defined), then P7-IMP-18 Core-tier scenarios are also blocked — they cannot be Core if the underlying merge mechanism is unspecified.
- P7-IMP-15 (corpus generation) conflicts with the data from P7-IMP-12 (corpus already has 30 B-tier patterns). P7-IMP-15's Prestep P7 should be demoted from "generate new corpus" to "gap analysis first" per the rewrite, otherwise both improvements will add corpus projects independently.

**Second-order risks:**
1. **Silent zero-metrics risk (P7-ADV-02):** If `GroundTruthAdapter` is not built before detection accuracy testing starts, the evaluation pipeline will produce 0% precision and 0% recall silently. This will appear as a catastrophic agent quality finding, trigger the improvement loop, and generate metaprompts attempting to fix agents that are actually working correctly. The improvement loop would then optimize agents toward producing output matching `OutputParser`'s expected format, not toward finding vulnerabilities.
2. **Catalog divergence amplification (P7-ADV-03):** The 10 uncatalogued patterns are already in ground truth for 15 corpus projects. If per-tier accuracy tracking is built without handling null tiers, the B/C recall numbers will be systematically understated (uncatalogued patterns silently excluded from denominator). This will generate false improvement signals for B/C tier coverage and trigger unnecessary corpus generation.
3. **Aderyn/Mythril prerequisite cascade (P7-IMP-20, P7-IMP-13):** P7-IMP-18 proposes full pipeline Core scenarios. These require tool integration. Tool integration requires Aderyn and Mythril to be installed. **UPDATE (pre-implement 2026-02-19):** Aderyn v0.6.8 now installed and verified. Mythril still unavailable (pkg_resources crash + Docker not running). Aderyn-only scenarios are unblocked. Full pipeline scenarios requiring Mythril remain blocked. Adapter detector mapping needs update before Aderyn cross-tool correlation works (pattern lookups return None).
4. **Reasoning chain reframe (P7-IMP-19):** If the existing reasoning chains are embedded as rubric text in evaluator prompts (as reframed), the Plan 07 evaluator prompt templates become corpus-specific — different contracts need different rubric text. This creates a per-corpus-contract prompt template requirement. Plan 06 (evaluation contracts) must include a `ground_truth_rubric` field that Plan 07 reads at evaluation time, not baked into static prompt templates.

## Adversarial Review: Pipeline Execution Feasibility

**Items reviewed:** 10 (P7-IMP-22 through P7-IMP-31)

**Verdicts:**
- CONFIRM: 2 (P7-IMP-25, P7-IMP-29)
- ENHANCE: 3 (P7-IMP-24, P7-IMP-28, P7-IMP-30)
- REFRAME: 2 (P7-IMP-22, P7-IMP-31)
- PREREQUISITE: 3 (P7-IMP-23, P7-IMP-26, P7-IMP-27 received CONFIRM but with enhancement)

Note: P7-IMP-27 was assigned CONFIRM (not PREREQUISITE) because its prerequisites (P6-IMP-14 debate protocol, P6-IMP-20 timeout) are already merged decisions — this improvement fixes an interaction between already-accepted items, which is within scope. The enhancement adds a secondary warning for systematic timeout starvation.

**Cross-group conflicts detected:**

1. **IMP-22 vs IMP-29**: IMP-22 proposes expanding Plan 01 summaries in CONTEXT.md; IMP-29 also proposes expanding Plan 01 summary with specific field enumerations. These target the same Plan 01 summary section. If both are implemented naively, the same section is written twice by different agents. Merge required: IMP-29's specific field enumeration should be the substance of IMP-22's Plan 01 expansion task.

2. **IMP-25 vs IMP-29**: Both add `applicable: bool` to `DimensionScore` (IMP-25 names it explicitly; IMP-29 lists it as "Fields to add to DimensionScore"). Duplicate. Must be a single Plan 01 task.

3. **IMP-23 vs IMP-30**: IMP-23 proposes mid-session checkpoints (orchestrator polls JSONL during session); IMP-30 proposes SIGINT handlers and kill_file polling. Both require the orchestrator to poll filesystem artifacts while a CC session is running. These interact: if both are implemented, the orchestrator has two polling loops (evaluation signals + kill signals). They should be unified into a single orchestrator polling loop with multiple concerns.

4. **IMP-26 (contract_healer at Wave 6) vs Group A IMP-03 (integration constraints)**: IMP-03 adds constraints that `contract_healer.propose()` returns proposals with no `apply()`. IMP-26 moves healer activation to Wave 6 Plan 06 exit criterion. These are compatible IF IMP-26 is corrected to target Plan 08 (not Plan 06) for the healer activation — but the exact constraint from IMP-03 ("no apply() method") must be preserved when the healer activates earlier.

**Second-order risks:**

1. **CONTEXT.md bloat is the biggest systemic risk**: IMP-22 (plan summaries), IMP-29 (field enumerations), IMP-27 (new field + HITL note), IMP-25 (new field + method), IMP-28 (new submodels), IMP-30 (new status field + SIGINT spec) — all add text to CONTEXT.md's Plan sections. Taken together these 6 improvements targeting Plan 01, Plan 08, and Plans 09-11 could add 800-1,500 words to a document already at ~9,000 words. The REFRAME verdict on IMP-22 addresses the worst case, but implementers should be directed to use additive Plan Notes rather than expanding every plan summary in place.

2. **Plan 01 is the critical path bottleneck**: Six of ten improvements in this group (IMP-24, IMP-25, IMP-27, IMP-28, IMP-29, IMP-30) require changes to Plan 01 data models. Plan 01 is Wave 1 — it blocks all other plans. Adding 6 improvements' worth of model changes to Plan 01 increases its LOC and implementation risk. These must be consolidated into a single Plan 01 implementation pass, not discovered incrementally.

3. **IMP-23's prerequisite (fcntl.flock) is unimplemented**: If P6-IMP-10 is not scheduled for Plan 02, IMP-23 remains permanently blocked. Verify P6-IMP-10 is in the Plan 02 task list before treating IMP-23 as actionable.

4. **IMP-26's Plan 06 routing error creates a wave violation**: If merged as written (Plan 06 exit criterion), it creates a Plan 06 dependency on Plan 12 intelligence module code. This would require either partially implementing Plan 12 before Wave 6 completes, or the gate being permanently unpassable. The PREREQUISITE verdict addresses this, but the fix (route to Plan 08 instead of Plan 06) must be explicit in the merge decision.
