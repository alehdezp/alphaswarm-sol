# Improvement Pass 4

**Pass:** 4
**Date:** 2026-02-19
**Prior passes read:** P1, P2, P3
**Status:** complete (all items implemented or rejected)

## Approach

Passes 1-2 fixed surface contradictions. Pass 3 found code-reality gaps and anti-signal scoring. This pass looks at deeper structural problems: the gap between PHILOSOPHY.md and CONTEXT.md, hidden coupling between components that will break during integration, and specific scenarios where the v1 plan as written will produce misleading results.

I read the full source code for all pipeline components (evaluation_runner.py, reasoning_evaluator.py, graph_value_scorer.py, observation_parser.py, debrief_protocol.py, regression_baseline.py, contract_loader.py, models.py) and both PHILOSOPHY.md and CONTEXT.md.

## Improvements

### P4-IMP-01: PHILOSOPHY.md and CONTEXT.md Are Dangerously Divergent
**What:** PHILOSOPHY.md (lines 78-85) commits to "51 per-workflow contracts" and "No workflow is excluded from reasoning evaluation. The old 'Mechanical' tier (capability-only, no LLM evaluation) is eliminated." CONTEXT.md (lines 139-142) says "Mechanical (~25-30): Capability checks ONLY -- deterministic assertions, NO LLM evaluation." PHILOSOPHY.md Rule C (line 241) says "51 per-workflow evaluation contracts." CONTEXT.md (line 143) says "~10 Core contracts (hand-authored) + 4 category-level template contracts." PHILOSOPHY.md North Star (line 414) has 15 conditions including cascade-aware scoring, contrastive calibration, coverage radar > 60%, adversarial evaluation audit. CONTEXT.md defers all of these to v2.
**Why:** Two documents claiming authority over the same phase, with contradictory commitments, means every plan author must choose which to follow. CONTEXT.md was scoped down deliberately through P1+P2 improvements. PHILOSOPHY.md was NOT updated. It still makes commitments (51 contracts, no mechanical tier, dual-Opus meta-evaluation) that CONTEXT.md explicitly defers or rejects. The line in CONTEXT.md "See PHILOSOPHY.md in this directory for v1 binding constraints" (line 15) is actively misleading -- PHILOSOPHY.md contains a mixture of v1 binding constraints AND v2+ aspirational scope, with no clear demarcation.
**How:** Split PHILOSOPHY.md into two files: (1) `PHILOSOPHY.md` -- one page of binding v1 constraints (the 5 pillars, stripped of v2 features). Remove all references to: 51 per-workflow contracts, dual-Opus meta-evaluation, contrastive calibration, cascade-aware scoring, coverage radar as live dashboard, composition stress testing, difficulty scaling, evaluator rotation, counterfactual replay, cross-workflow learning, reasoning fingerprinting. (2) `VISION.md` -- the aspirational full vision, explicitly labeled "v2+ aspirational scope, NOT binding for 3.1c." Update CONTEXT.md line 15 to reference the stripped PHILOSOPHY.md only.
**Impacts:** All plans -- removes ambiguity about what PHILOSOPHY.md commits the implementation to. CONTEXT.md line 684 already mentions "Full PHILOSOPHY.md aspirational vision (v1 philosophy is 1 page of binding constraints; aspirational scope lives in VISION.md)" in Deferred Ideas, confirming this was intended but never executed.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P4-IMP-02: EvaluationRunner Does Not Call check_regression -- Baseline Is Write-Only
**What:** CONTEXT.md (line 646) says "Tier-weighted regression detection operational with per-category thresholds." Plan D exit criteria (line 477) say "Tier-weighted regression detection operational." But `evaluation_runner.py:262-267` only calls `self._baseline_manager.update_baseline()` -- it never calls `check_regression()`. The runner writes to baselines but never reads from them. `check_regression()` exists in `regression_baseline.py:161-206` but has zero callers. `check_batch()` also has zero callers.
**Why:** Regression detection is the entire purpose of Plan D. The runner currently produces baselines that nobody checks. The Plan D exit criteria can be "satisfied" by establishing baselines (update_baseline works) without ever demonstrating regression detection (check_regression is never called). This is the same class of loophole P3-IMP-07 identified for Plan B -- the exit criteria technically pass without the core capability working.
**How:** Add to Plan D scope: "EvaluationRunner.run() must call `check_regression()` after `update_baseline()` and include the `RegressionReport` in `EvaluationResult.metadata['regression']`. Add `regression_report: RegressionReport | None` field to EvaluationResult (or serialize to metadata dict). Plan D exit criteria must require: 'Runner produces regression reports that correctly flag a >threshold score drop as regression' -- demonstrated with a concrete test where a deliberately degraded workflow triggers regression."
**Impacts:** Plan D exit criteria (must demonstrate regression detection, not just baseline storage). Models.py may need a new field.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P4-IMP-03: PipelineHealth Metric Is Fundamentally Broken
**What:** `PipelineHealth` (models.py:242-266) calculates `health_pct = (parsed_records - errors) / expected_records`. `expected_records` is set to `len(PIPELINE_STAGES) = 5` at runner initialization (evaluation_runner.py:160). `parsed_records` counts completed stages (0-5). `errors` counts exceptions (0+). This means health_pct can only be {0.0, 0.2, 0.4, 0.6, 0.8, 1.0} minus error adjustments. With 1 error and 5 stages complete: health = (5-1)/5 = 0.8 = reliable. With 0 errors and 3 stages complete: health = 3/5 = 0.6 = reliable (barely). A run that crashes after Stage 3 (evaluation never completes) is marked "reliable" at 60%.
**Why:** The reliability threshold of 0.6 (line 266) means a run where the EVALUATOR ITSELF FAILS (stages 4+5 never complete) is still considered reliable for baseline. `BaselineManager.update_baseline()` (regression_baseline.py:128) gates on `result.is_reliable`. A run with no evaluation score -- where the ScoreCard is the zero-score fallback from the `FileNotFoundError` handler -- passes the reliability check if 3 of 5 pipeline stages completed. This directly contradicts P3-IMP-05's concern about capability gating: health_pct declares crashed runs "reliable."
**How:** Fix PipelineHealth to distinguish "pipeline completed" from "pipeline health." Add `completed: bool` property that requires `"run_evaluator" in stages_completed`. `is_reliable` should require BOTH `completed` AND `health_pct >= 0.6`. Update Known Code Issues to document this. This is a Plan A fix -- the pipeline health model is foundational and must be correct before any evaluation run produces baselines.
**Impacts:** Plan A (models fix), Plan D (baseline gating depends on correct reliability). Prevents the scenario P3-IMP-05 describes (crashed runs seeding baselines) at the root cause.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P4-IMP-04: JSONFileStore.list_results Is O(n) Full Scan With No Index
**What:** `evaluation_runner.py:66-78` -- `list_results()` reads and deserializes EVERY JSON file in the results directory, then filters by workflow_id. `get_latest()` calls `list_results(limit=1)` but the limit applies AFTER filtering, so it still reads all files until it finds a match.
**Why:** After Plan D establishes baselines with 3+ runs per 10 Core workflows, the results directory contains 30+ files. After Plan E exercises 51 workflows, 150+ files. Each `get_latest()` call reads and parses all of them. This is not a performance problem yet, but it becomes one when `check_batch()` calls `check_regression()` per result, each of which calls `get_baseline()` (file read). The real problem: `list_results()` sorts by filename (alphabetical UUID), NOT by timestamp. It returns the lexicographically-latest UUID, not the most recent result. `get_latest()` returns the wrong result.
**How:** Fix `get_latest()` to sort by `completed_at` field instead of filename. This is a correctness bug, not just performance. Add to Plan A scope (2-line fix in `get_latest()`: read all, sort by `result.completed_at`, return first). Performance optimization (filename-based index) is Plan E scope.
**Impacts:** Plan A (correctness fix for get_latest), Plan D (regression detection compares against wrong baseline without this fix).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P4-IMP-05: Debrief Cascade Produces Different Types for Same Semantic Role
**What:** The debrief cascade (debrief_protocol.py:278-295) returns `DebriefResponse` for every layer. But the answer quality varies enormously: Layer 1 (SendMessage) returns direct agent prose. Layer 3 (transcript analysis) returns `_find_relevant_lines()` output which is raw transcript lines joined by " | " (line 399). Layer 4 (skip) returns `"[No debrief data available]"` x5. The `_score_debrief_dimension()` method in reasoning_evaluator.py:336-357 scores these identically: `base_score = confidence * 100`, then checks `not a.startswith("[No")` for answer quality.
**Why:** A transcript-analysis debrief with confidence 0.3 that returns 3 real lines produces `base_score=30`, answer_ratio might be 3/5=0.6, giving `adjusted = 30*0.5 + 60*0.5 = 45`. A skip debrief with confidence 0.0 produces `base_score=0`, answer_ratio=0/5=0.0, giving `adjusted = 0`. So the scoring CAN differentiate. But the transcript-analysis answers are not actually answers -- they are keyword-matched lines from the transcript. "strategy" -> lines containing "strategy", "approach", "plan", "first". An agent transcript saying "First, I'll read the contract" matches the "strategy" question because "first" is a keyword. The debrief scorer gives credit for this non-answer.
**How:** Add to Known Code Issues: "Transcript-analysis debrief (Layer 3) keyword matching produces non-answers that pass the debrief scorer. The `_find_relevant_lines()` function matches generic words ('first', 'plan', 'found') that appear in any transcript. Until Plan B replaces this with LLM-based transcript summarization, Layer 3 debrief scores are noise. Plan B exit criteria for debrief: 'Layer 1 (SendMessage) works on at least 1 real agent' -- do NOT gate on Layer 3 quality."
**Impacts:** Plan B (debrief quality expectations). Documents why Layer 3 is confidence 0.3, not a design choice but a quality signal.
**Research needed:** no
**Confidence:** MEDIUM
**Status:** implemented

### P4-IMP-06: Contract Loader resolve_contract_id Silently Falls Through to Raw ID
**What:** `contract_loader.py:40-54` -- `resolve_contract_id()` returns `_WORKFLOW_TO_CONTRACT.get(workflow_id, workflow_id)` -- if workflow_id is not in the mapping, it passes through unchanged. Then `load_contract()` looks for `{workflow_id}.yaml`. If someone passes "vrs-tool-aderyn" (a shipped skill), it's not in `_WORKFLOW_TO_CONTRACT`, so it looks for `vrs-tool-aderyn.yaml`. The file is actually named `skill-vrs-tool-aderyn.yaml` (if it existed, which per P3-IMP-04 it doesn't). The fallthrough turns a missing mapping into a missing file, and the error message says "No contract found for 'vrs-tool-aderyn'" -- not "workflow ID not in mapping."
**Why:** P3-IMP-04 identified 3 missing Core tool contracts. When those are added (Plan B), the mapping also needs entries. But the fallthrough behavior means ANY new workflow silently gets a FileNotFoundError with a confusing message instead of a clear "unknown workflow ID" error. This will bite Plan E when template contracts are generated for all 51 workflows -- every unmapped ID fails silently.
**How:** Add a `strict` mode to `resolve_contract_id()`: when `strict=True`, raise `ValueError(f"Unknown workflow ID: {workflow_id}. Known IDs: {list(_WORKFLOW_TO_CONTRACT.keys())}")` instead of falling through. The runner should use strict mode. Direct `load_contract()` calls can use non-strict for backward compatibility. Alternatively: eliminate the mapping entirely and use naming convention only (prefix detection: starts with "skill-", "agent-", "orchestrator-"). Add to Plan B scope.
**Impacts:** Plan B (mapping completeness), Plan E (template generation needs to populate mapping).
**Research needed:** no
**Confidence:** MEDIUM
**Status:** implemented

### P4-IMP-07: Plan A and Plan B Have No Shared Definition of "Real Transcript"
**What:** Plan A exit criteria (line 441): "TranscriptParser processes >= 1 real Claude Code transcript without errors." Prestep P0.5 (line 412): "Score 3 core dimensions on 3 real transcripts." Plan B exit criteria (line 454): "Evaluator distinguishes good from bad transcript (differential > 20 points on anchor transcripts)." Three different uses of "transcript" -- none defined. TranscriptParser processes JSONL session transcripts. ObservationParser processes JSONL from hooks. The ReasoningEvaluator receives `CollectedOutput` which may or may not have a `transcript: TranscriptParser` field. In headless mode (Plan C), `CollectedOutput.transcript` is None -- only observations exist.
**Why:** Plan B's exit criteria ("distinguishes good from bad transcript") requires TWO transcripts with known quality labels. But what is being distinguished? The `CollectedOutput` (which includes tool_sequence, bskg_queries, response_text) or the raw JSONL transcript? The evaluator scores dimensions from `_heuristic_dimension_score()` which reads `tool_sequence` and `bskg_queries` from CollectedOutput. In headless mode, these come from observations, not transcripts. So "anchor transcripts" actually means "anchor CollectedOutputs with observations." The terminology confusion will cause Plan B to produce anchor data in the wrong format.
**How:** Add to Implementation Decisions: "Terminology: A 'transcript' in evaluation context means a `CollectedOutput` instance populated from either (a) TranscriptParser + ObservationParser in interactive mode, or (b) ObservationParser alone in headless mode. 'Anchor transcripts' are `CollectedOutput` instances with human-assigned quality labels (good/bad) and dimension scores. They are NOT raw JSONL files. Plan B must produce anchor CollectedOutputs, not anchor JSONL files."
**Impacts:** Plan B (anchor transcript format clarification). Prevents Plan B from producing JSONL files that the evaluator cannot consume.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

### P4-IMP-08: The Observation-to-CollectedOutput Bridge Does Not Exist
**What:** CONTEXT.md Data Source Hierarchy (lines 159-162) says "Primary: ObservationParser (hooks) for GVS, capability checks, and real-time evaluation." The EvaluationRunner (evaluation_runner.py:178-185) parses observations into `obs_summary` and passes it to the evaluator via `obs_summary=obs_summary`. But `ReasoningEvaluator.evaluate()` stores `obs_summary` in `plugin_context` (line 150) and passes it to plugins. The dimension scoring in `_heuristic_dimension_score()` and `_evaluate_capabilities()` reads from `collected_output.tool_sequence` and `collected_output.bskg_queries` -- NOT from obs_summary. In headless mode, the `CollectedOutput` is constructed from... what? There is no code that populates `CollectedOutput.tool_sequence` from `ObservationSummary.tool_events` or `CollectedOutput.bskg_queries` from `ObservationSummary.bskg_observations`.
**Why:** This is the fundamental integration gap. The observation pipeline (hooks -> JSONL -> ObservationParser -> ObservationSummary) and the evaluation pipeline (CollectedOutput -> ReasoningEvaluator -> ScoreCard) are two parallel tracks that never merge. GVS receives CollectedOutput and ignores obs_summary. The heuristic evaluator reads from CollectedOutput fields that are empty in headless mode. Plan C's exit criteria ("Evaluation runner processes a real workflow end-to-end") will fail at the bridge: observations exist but the evaluator cannot read them because CollectedOutput is not populated from observations.
**How:** Add to Plan A scope: "Build `CollectedOutput.from_observations(obs_summary: ObservationSummary)` class method that populates `tool_sequence` from `obs_summary.tool_events`, `bskg_queries` from `obs_summary.bskg_observations`, etc. The runner must call this bridge when constructing CollectedOutput in headless mode. This is ~30-50 LOC and is the critical integration point between 3.1b's observation infrastructure and 3.1c's evaluation pipeline." Add to Plan A exit criteria: "CollectedOutput constructed from ObservationSummary produces valid GVS and capability check scores."
**Impacts:** Plan A (critical -- without this bridge, headless evaluation is impossible), Plan C (depends on this bridge for headless workflow testing).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

**Implementation note (2026-02-19):** Content merged into CONTEXT.md: Plan A exit criteria (line 523), Known Code Issues "Data Source Hierarchy Is Aspirational" (line 427-428). Status was incorrectly left as `open` during prior merge pass.

### P4-IMP-09: Anti-Fabrication Checks Have No Implementation Location
**What:** CONTEXT.md Plan D exit criteria (line 480): "Anti-fabrication static triggers pass (6 checks: 100% pass rate, identical outputs, all 100s, zero variance, duration <5s, transcript <500 chars)." Exit Gate item 11 (line 651): "Anti-fabrication: Level 1 static triggers active for all runs." But no code exists for these checks. The 6 triggers are described in PHILOSOPHY.md Rule D (lines 254-260) but never referenced in any implementation plan, any module, or any test.
**Why:** This is a Plan D exit criteria that has no implementation path. Unlike P3-IMP-16 (variant execution mechanism, which at least has WorkspaceManager as a foundation), anti-fabrication has zero code surface. It needs: a function that accepts an EvaluationResult and returns a list of triggered flags, integration into the runner or baseline manager, and threshold values. Without defining WHERE these checks live and WHEN they run, Plan D will either skip them or implement them ad-hoc.
**How:** Add to Plan D scope: "Anti-fabrication module (~100 LOC): `check_fabrication_signals(result: EvaluationResult, historical: list[EvaluationResult] | None = None) -> list[FabricationFlag]`. 6 static checks on individual results. Returns list of triggered flags. Called by `EvaluationRunner.run()` after scoring. Results stored in `result.metadata['fabrication_flags']`. If any flag triggers, `result.metadata['fabrication_warning'] = True`. Location: `tests/workflow_harness/lib/fabrication_detector.py`."
**Impacts:** Plan D scope (adds ~100 LOC for fabrication detection).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented

---

## Convergence Assessment

**Structural improvements:** 6 (P4-IMP-01, P4-IMP-02, P4-IMP-03, P4-IMP-04, P4-IMP-08, P4-IMP-09)
**Cosmetic improvements:** 3 (P4-IMP-05, P4-IMP-06, P4-IMP-07)
**Ratio:** 33% cosmetic

> Structural issues remain. P4-IMP-08 (observation-to-CollectedOutput bridge) is the most critical finding: it reveals that the two halves of the pipeline (observation hooks and evaluation scoring) have no integration point. P4-IMP-03 (broken PipelineHealth) undermines all baseline reliability gating. P4-IMP-01 (PHILOSOPHY.md divergence) creates ongoing confusion about scope commitments. Another improvement pass is recommended only if P3 items are merged first; otherwise, pass 5 will repeat P3's open items.

---

## NEW GAPS (Discovered by Adversarial Review of P3+P4)

These gaps were found by 4 parallel adversarial agents that verified P3+P4 improvement claims against actual source code. They represent issues that 4 prior improvement passes missed because they required cross-component integration analysis.

### New Gap 1: `capability_gating_failed` Flag Never Set by Evaluator
**Source:** Adversarial review of P3-IMP-05
**Priority:** CRITICAL
**What:** P-1 prestep added `capability_gating_failed: bool` to `ScoreCard` and `BaselineManager` guards. But the evaluator (`ReasoningEvaluator.evaluate()`) never sets this flag to `True`. The entire gate detection path is dead code — the field exists, the guard checks it, but nothing triggers it.
**Impact:** Plan B must wire capability gate detection into the evaluator. Without it, crashed runs pass through the baseline guard unchecked.

### New Gap 2: `_bridge_input()` Silently Returns None on Exception
**Source:** Adversarial review of P4-IMP-08
**Priority:** HIGH
**What:** `evaluation_runner.py` `_bridge_input()` catches all exceptions and returns `None`. The caller proceeds with `None` CollectedOutput, producing zero-score results with no error trace. This is the exact "silent failure" pattern P3-IMP-03 describes.
**Impact:** Plan A must add logging to `_bridge_input()` exception handler.

### New Gap 3: Dead LLM Evaluation Templates
**Source:** Adversarial review of P3-IMP-07
**Priority:** HIGH
**What:** `reasoning_evaluator.py` contains `REASONING_PROMPT_TEMPLATE` (15-line placeholder) and `STRUCTURED_EVAL_SCHEMA` that are never invoked. The heuristic path is the only active scorer. These templates are Plan B's starting point but are currently dead code with no tests.
**Impact:** Plan B must verify these templates produce valid output before building on them.

### New Gap 4: Debrief Dimension Scores Missing `scoring_method` Tag
**Source:** Adversarial review of P3-IMP-06 + P4-IMP-05
**Priority:** HIGH
**What:** Debrief dimension scores from `_score_debrief_dimension()` do not carry the `scoring_method: "heuristic"` tag added by P-1 prestep. The P-1 quarantine only tags reasoning dimensions, not debrief dimensions. This means debrief heuristic scores bypass the baseline quarantine.
**Impact:** Plan B must extend `scoring_method` tagging to debrief dimensions.

### New Gap 5: Contract Schema Too Permissive
**Source:** Adversarial review of P3-IMP-04 + P4-IMP-06
**Priority:** MEDIUM
**What:** The evaluation contract YAML schema allows arbitrary dimension names with no validation against known dimension types. A typo in a contract dimension name (`evidenve_quality` instead of `evidence_quality`) silently falls through to the hardcoded-30 `else` branch in the heuristic scorer.
**Impact:** Plan B contract authoring needs schema validation against known dimension names.

### New Gap 6: Contract Loader Auto-Discovery Claim vs Reality
**Source:** Adversarial review of P3-IMP-04
**Priority:** MEDIUM
**What:** CONTEXT.md claims "Contract loader: Auto-discovers contracts by directory scan." The actual code uses a hardcoded `_WORKFLOW_TO_CONTRACT` dict with 7 entries. Auto-discovery does not exist.
**Impact:** Either implement auto-discovery (Plan E) or correct the CONTEXT.md claim.

### New Gap 7: Data Source Hierarchy Is Aspirational
**Source:** Adversarial review of P4-IMP-08
**Priority:** MEDIUM
**What:** CONTEXT.md Data Source Hierarchy lists Primary (ObservationParser), Secondary (TranscriptParser), Tertiary (debrief). But the evaluator reads from `CollectedOutput` fields that are only populated by TranscriptParser. The hierarchy describes desired state, not current state.
**Impact:** Plan A must implement the bridge (P4-IMP-08) to make the hierarchy real.
