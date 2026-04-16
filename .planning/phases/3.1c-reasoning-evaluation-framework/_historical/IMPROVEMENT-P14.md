# Improvement Pass 14

**Pass:** 14
**Date:** 2026-02-20
**Prior passes read:** 13 (via IMPROVEMENT-DIGEST.md: 288 merged, 0 active, fully converged)
**Areas:** Data Foundation (Plans 01-03), Scoring & Evaluation Design (Plans 04-07), Test Execution & Operations (Plans 08-11), Improvement Loop & Intelligence (Plan 12)
**Agent count:** 4 improvement agents, 4 adversarial reviewers, 1 synthesis (pending)
**Cross-pollination:** 3.1e (Evaluation Zero — Empirical Sprint) experiment-first philosophy
**Status:** complete

<!-- File-level status: in-progress | complete -->

## Pipeline Status

<!-- Auto-populated by workflows. Shows pending actions across ALL passes for this phase. -->

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 0 | 0 | — |
| Research | 0 | 2 | — (resolved 2026-02-23, see P15 Research Resolution) |
| Gaps | 0 | 0 | — |
| Merge-ready | 0 | 21 | — |

**Pipeline:** [discuss] done → [improve] done → [pre-impl] — → [research] done → [implement] done → [plan] — → [execute] —
**Merged:** 2026-02-23 — 21 items merged into 3.1c-CONTEXT.md (combined with P15's 38 = 59 total)

## Adversarial Lenses

| Lens | Brief | Items | Attack Vector |
|------|-------|-------|---------------|
| Experiment-First Overreach | 3.1e's "experiment before infrastructure" is directionally correct but can be weaponized to hollow out 3.1c's foundational type system and locked architectural decisions. The attack: use experiment-first philosophy to defer load-bearing infrastructure (types, debate protocol) that downstream plans depend on at compile time. | P14-IMP-01, P14-IMP-03, P14-IMP-07, P14-IMP-08, P14-IMP-13, P14-IMP-14, P14-IMP-20 | Does "defer until observed" distinguish execution decisions (testable) from compilation dependencies (load-bearing)? |
| Cost & Calibration Grounding | Cost estimates and calibration thresholds are stated without empirical basis. The attack: scare numbers ($100-270) and unenforceable ceilings ($10) obscure the actual cost architecture (per-dimension filtering, applicable gates) and prevent HITL reviewers from making calibrated decisions. | P14-IMP-02, P14-IMP-10, P14-IMP-21, P14-IMP-22, P14-IMP-25 | Are cost/threshold numbers grounded in the actual architecture, or do they bypass filtering mechanisms to manufacture urgency? |
| Detection Baseline Alignment | The 13.3% detection precision figure creates a gravitational pull toward outcome-based evaluation. The attack: items reference the precision number to justify changes that inadvertently conflate process evaluation with detection outcome, undermining the Grader Taxonomy separation. | P14-IMP-09, P14-IMP-12, P14-IMP-16, P14-IMP-23, P14-IMP-24 | Does each item's fix maintain the process/outcome separation, or does it smuggle detection accuracy back into process evaluation? |
| Technical Debt vs Premature Refactoring | Items proposing cleanup or consolidation may be premature refactoring disguised as debt reduction. The attack: collapse structurally meaningful boundaries (Wave 2/3, plan decomposition) in exchange for fewer labels, losing the empirical gates those boundaries encode. | P14-IMP-04, P14-IMP-05, P14-IMP-06, P14-IMP-11, P14-IMP-15, P14-IMP-17, P14-IMP-18, P14-IMP-19 | Does the proposed consolidation/cleanup eliminate a structurally meaningful boundary, or does it genuinely reduce complexity? |

## Improvements

### P14-IMP-01: Split Plan 01 Into "First-Run" vs "Post-Observation" Type Tiers
**Target:** CONTEXT
**What:** Plan 01 deliverables (lines 1563-1639) define 30+ Pydantic types as a single Wave 1 deliverable. Many types presuppose evaluation patterns never observed: `TemporalAnalysis`, `MetaEvaluationResult`, `ImprovementAttempt`, `CalibrationConfig`, `EvaluatorDisagreement` (with `B_score_pre_exposure`), `ImprovementHint`. These encode assumptions about what the evaluation loop will look like before a single real evaluation has completed.
**Why:** 3.1e's core philosophy is "experiment before infrastructure." The model count grew from ~15 to 30+ through 13 passes of speculative refinement with zero real transcripts and zero real evaluation runs. Types genuinely needed for first run (~18) already exist or are straightforward. The remaining ~12 types are needed only after first evaluation produces data. Splitting reduces Plan 01 scope by ~40% and gets to first real run faster. Prior rejection P1-IMP-02 proposed pruning entirely — this keeps types as stubs instead.
**How:**
1. Split Plan 01 deliverables into Group A (first-run types, Wave 1) and Group B (post-observation types, Wave 4) with explicit lists
2. Group B types created as stubs with `# TODO: validate fields after first calibration run` markers
3. Update Plan 01 exit criterion: "Group A types fully specified. Group B types have stub definitions."
4. Update Cross-Plan Dependencies: Plans 02-08 depend on Group A only. Plans 07 (debate), 12 depend on Group B.
**Impacts:** Plan 01 scope reduced ~40%. Plan 07 gains Group B dependency. Plan 12 unaffected.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Experiment-First Overreach):** The "30+ types grown through 13 passes of speculative refinement" observation is directionally correct but the proposed fix breaks the dependency graph. The Cross-Plan Dependencies table lists `01 | all | Data models consumed everywhere`. If `DebriefResponse`, `BaselineKey`, `CalibrationConfig`, and `ExperimentLedgerEntry` are deferred to Wave 4, Plan 05 has no type to declare its return, Plan 07's `_llm_evaluate_dimension()` has no `DimensionScore` to produce, and Plan 12's `CalibrationConfig.from_disk()` startup guard has nothing to assert against. The 3.1e experiment-first philosophy targets *execution* decisions, not *type declaration* decisions. Types are load-bearing infrastructure, not speculative features. REFRAME: see P14-ADV-1-01.

### P14-IMP-02: calibration_epoch Needs 'failed' State for Calibration Failure
**Target:** CONTEXT
**What:** `ExperimentLedgerEntry.calibration_epoch: Literal['provisional', 'calibrated']` (line 1569) and the Calibration Anchor Protocol (lines 353-365) assume calibration will succeed. With 13.3% detection precision, agents produce mostly false positives — Spearman rho > 0.6 may be unachievable, making `calibration_epoch` permanently stuck at `'provisional'`.
**Why:** The 13.3% precision means most agents find everything including junk. Computing Spearman rho requires rank ordering that may be too noisy. The design doesn't account for this failure mode — `ImprovementHint` entries would never enter the automated queue, and the entire improvement loop remains human-only (which might be fine, but should be explicit).
**How:**
1. Add failure mode to Calibration Anchor Protocol: if rho < 0.6 after initial anchor, diagnosis path with binary classification fallback (Mann-Whitney U test)
2. Change `calibration_epoch` type to `Literal['provisional', 'calibrated', 'failed']`
**Impacts:** Plan 12 Part 0 gains fallback path. Plan 01 model gains one enum value.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 12 (calibration run)
**Classification:** structural
**Status:** reframed
**Adversarial note (Cost & Calibration Grounding):** The framing conflates two distinct failure modes. `calibration_epoch` controls the hint routing state machine — `'failed'` would be a permanent terminal state blocking all downstream processing. The real problem is the re-entry path: after diagnosing a rho failure and fixing underlying issues, how does the system reset? Adding `'failed'` to `calibration_epoch` Literal is architecturally wrong — the failure status belongs on `CalibrationConfig` (the artifact), not on `calibration_epoch` (the routing enum). REFRAME: see P14-ADV-2-01.

### P14-IMP-03: Plan 02 Should Capture Real Transcripts FIRST, Not as Deliverable 7 of 10
**Target:** CONTEXT
**What:** Plan 02 deliverable 1 specifies `TranscriptParser.to_observation_summary() (~60 LOC)` but real transcript capture is deliverable 7. All extraction logic is built on assumptions about transcript structure that have never been validated. 3.1e independently flags this concern: zero real transcripts exist.
**Why:** This is the exact anti-pattern 3.1e identified: designing extraction logic before observing source data. Field name bugs were already found in the hook pipeline (P13-IMP-01: `tool_output` vs `tool_response`). The same class of bugs is likely in transcript assumptions but undetectable without real data.
**How:**
1. Reorder Plan 02: real transcript capture becomes deliverable 1 (currently 7)
2. Add sequencing note: "Capture first, validate TranscriptParser, then implement extraction"
3. Elevate transcript exit criterion to FIRST checked: "3+ real transcripts exist and TranscriptParser parses them. If parsing fails, HALT."
**Impacts:** Plan 02 internal task ordering changes. No cross-plan dependency changes.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (Experiment-First Overreach):** This withstands scrutiny and is the one item that unambiguously applies 3.1e's philosophy correctly. Plan 02 has 9 deliverables before it captures real transcripts, meaning every prior deliverable is built on unvalidated assumptions. P0 is listed as deliverable 7 of 10 inside Plan 02's own execution order — the plan itself would build 6 deliverables before reaching its own hard prerequisite. The reordering should be "P0 deliverable (real transcript capture) is Plan 02 Stage 0, not Stage 7."

### P14-IMP-04: Plan 03 (~120 LOC Adapter) Should Be Absorbed Into Plan 02
**Target:** CONTEXT
**What:** Plan 03 (lines 1717-1749) was reduced to "thin adapter over TranscriptParser (~40 LOC)" by P13-IMP-12. Total across 9 micro-deliverables: ~120 LOC. It depends entirely on Plan 02's TranscriptParser work and cannot be tested independently.
**Why:** A plan with ~120 LOC across 9 micro-deliverables is over-decomposed. The adapter's design cannot be finalized until Plan 02's `to_observation_summary()` is complete, making Plan 03 a dependent continuation, not an independent plan. Merging eliminates one inter-plan dependency edge.
**How:**
1. Merge Plan 03 deliverables into Plan 02 as "Part B: Observation Adapter"
2. Update Cross-Plan Dependencies: remove Plan 03 rows, redirect to Plan 02
3. Keep plan number but mark as "absorbed into Plan 02" to avoid renumbering cascade
**Impacts:** Plan 03 eliminated. Plans 04, 07, 08 redirect dependency to Plan 02. Plan 02 scope increases from ~300 to ~420 LOC.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Technical Debt vs Premature Refactoring):** The merger proposal is premature refactoring. It would eliminate a structurally meaningful boundary (live-environment work vs. pure-code work) in exchange for fewer plan labels. The Wave 2/3 distinction encodes the empirical gate that Plan 02's real transcripts must exist before Plan 03 can validate on them (P0 hard gate). The real issue — the 02→03 stall risk — is a scheduling concern, not a decomposition problem. REFRAME: see P14-ADV-4-01.

### P14-IMP-05: Annotate Plan 01 Model Fields as [core] vs [defensive]
**Target:** CONTEXT
**What:** Three fields added through improvement passes encode behavioral assumptions: `DebriefResponse.compacted`, `DimensionScore.applicable`, `EvaluatorDisagreement.B_score_pre_exposure`. These are individually reasonable but downstream plans build branching logic around them.
**Why:** Documentation clarity: distinguish fields carrying evaluation data from fields handling edge cases that may never occur. Prevents Plan 08 from blocking on untested code paths.
**How:**
1. Annotate fields in Plan 01 deliverables: `[core]` for data fields, `[defensive]` for edge-case handling
2. Plan 08 exit criterion gains: "Defensive fields have unit tests but are NOT required for first successful evaluation run."
**Impacts:** Plan 01 documentation. Plan 08 exit criterion nuance.
**Research needed:** no
**Confidence:** LOW
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** cosmetic
**Status:** rejected
**Adversarial note (Technical Debt vs Premature Refactoring):** This is process overhead on a design document that planners consume to write PLAN.md task breakdowns. Adding [core]/[defensive] annotations to ~30+ model fields would double signal-to-noise, create a maintenance surface (every future field must be classified), and deliver no machine-readable enforcement. The stated Why is already addressed structurally: `run_mode=simulated` distinguishes untested paths, and exit gates are tied to `run_mode=interactive` or `run_mode=headless`. LOW confidence on a cosmetic change to an already-converged model list is the correct signal to reject.

### P14-IMP-06: EvaluatorConstants.current() Has Circular Import Problem
**Target:** CONTEXT
**What:** The CONTEXT (P11-SYN-02 section, lines 667-678) specifies that `EvaluatorConstants` is defined in `models.py` and that `EVALUATOR_MODEL` / `EVALUATOR_EFFORT` constants in `reasoning_evaluator.py` are replaced by `EvaluatorConstants.current()`. This creates a concrete circular import: `reasoning_evaluator.py` imports from `models.py` (already present — line 23-31 of the existing file), and if `EvaluatorConstants.current()` needs to compute `prompt_template_hash` of `REASONING_PROMPT_TEMPLATE`, it must import from `reasoning_evaluator.py`. The CONTEXT must close this loop explicitly by specifying that `EvaluatorConstants.current()` takes `prompt_template_hash: str` as a parameter, NOT by importing from `reasoning_evaluator.py`. The hash is computed at call site in Plan 07 and passed in. The factory method signature becomes `EvaluatorConstants.current(prompt_template_hash: str) -> EvaluatorConstants`.
**Why:** A circular import between `models.py` (Wave 1, Plan 01) and `reasoning_evaluator.py` (Wave 4, Plan 07) would silently break the import chain at runtime. Python resolves some circular imports, but a frozen dataclass calling a class method that requires importing from its consumer is not one of them. This is a v1-blocking architectural defect, not an edge case.
**How:**
1. In the EvaluatorConstants Single Source of Truth section, add: "`EvaluatorConstants.current(prompt_template_hash: str) -> EvaluatorConstants` — caller computes SHA256 of `REASONING_PROMPT_TEMPLATE` and passes it in. Do NOT import from `reasoning_evaluator.py` in `models.py`."
2. In Plan 07 deliverable (EvaluatorLLM call path section), add: "At startup, Plan 07 calls `EvaluatorConstants.current(prompt_template_hash=hashlib.sha256(REASONING_PROMPT_TEMPLATE.encode()).hexdigest())` and stores the result. All evaluator-configuration-bearing models receive fields from this instance."
3. Add to Plan 01 exit criteria: "EvaluatorConstants.current() takes prompt_template_hash as parameter; zero imports from `reasoning_evaluator.py` in `models.py` (grep check)."
**Impacts:** Plan 01, Plan 07, Plan 12 (CalibrationConfig uses EvaluatorConstants)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Technical Debt vs Premature Refactoring):** The original item correctly identifies a real circular import problem. The enhancement adds the precise fix (parameter-passing rather than import) and the specific exit criterion grep check. Second-order: Plan 07 must document that `EvaluatorConstants` instances are per-session, not module-level singletons — if `REASONING_PROMPT_TEMPLATE` is modified during improvement loop experiments, the hash will be stale.

### P14-IMP-07: Plan 07 Needs "First Real LLM Call" Gate Before Debate Protocol
**Target:** CONTEXT
**What:** Add a single-evaluator validation milestone inside Plan 07 before building the blind-then-debate protocol: (1) implement `_llm_evaluate_dimension()` with a single Opus call, (2) run it on 3 real transcripts from Plan 02's P0 deliverable, (3) confirm `DimensionScore` round-trips through `--json-schema` without parse errors AND that scores are not uniformly 50 or 100 before proceeding to the full debate architecture. Gate criterion: single-evaluator produces non-degenerate score distribution (std dev > 10 across 3 transcripts) on at least 2 dimensions. If criterion fails, diagnose prompt template before investing in debate infrastructure.
**Why:** `REASONING_PROMPT_TEMPLATE` at `reasoning_evaluator.py:40-55` has zero invocations. The debate protocol adds ~5-15 min/workflow and requires `EvaluatorDisagreement`, `B_score_pre_exposure`, separate session orchestration, and tie-breaking logic (~80 LOC). If the underlying prompt template produces degenerate outputs (all 50s, all 100s, or unparseable JSON), the debate protocol compounds a broken foundation rather than improving it. The single-evaluator gate is a ~30 min empirical check that validates the LLM call path before 80+ LOC of debate infrastructure is written.
**How:**
1. Plan 07 deliverable 1 (`_llm_evaluate_dimension()` ~30 LOC) is the minimum viable evaluator. Add an explicit sub-exit criterion: "single-evaluator call on 3 real transcripts from P0 produces valid `DimensionScore` objects with std dev > 10 on at least 2 dimensions."
2. Mark deliverable 2 (debate protocol) as explicitly gated on sub-exit criterion 1 passing. Add to CONTEXT.md Plan 07 deliverables: "Debate protocol implementation is conditional: proceed only after single-evaluator validation milestone confirms non-degenerate outputs."
3. Define "degenerate" concretely: all scores within ±5pt of 50, or parse errors on >1 of 3 transcripts, or evaluation_complete=False on all calls.
**Impacts:** Plan 07 scope potentially halved. Plan 08 debate wall-clock may be unnecessary. Plan 12 calibration may simplify.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 02 (real transcripts)
**Classification:** structural
**Status:** enhanced
**Adversarial note (Experiment-First Overreach):** The gate is about validating the `claude -p --json-schema` call path, not questioning the debate architecture itself (which is a Locked Implementation Decision). The rewrite frames it as a call-path validation gate within Plan 07's own sequence. Monitor for drift during plan execution: if framed incorrectly as "debate is optional pending validation," it could be used to defer the debate architecture entirely.

### P14-IMP-08: GVS 66-Combo Grid Search Needs Minimum Sample Size
**Target:** CONTEXT
**What:** GVS Weight Calibration specifies 66 three-weight combos. Plan 02 targets 3+ transcripts. Running 66 combos on 3 data points is overfitting by definition.
**Why:** Calibration without sufficient data is meaningless. The procedure needs a minimum sample size gate.
**How:**
1. Add minimum: "10 scored transcripts spanning 3+ categories. If <10 available, use DEFAULT_WEIGHTS and defer calibration to post-Plan 09."
2. Separate Plan 04 exit criteria: "GVS scoring works" (Wave 3-5, no calibration) vs "GVS weights calibrated" (Wave 6, data-dependent)
**Impacts:** Plan 04 Wave 6 deferred until sufficient data. Plan 12 baseline uses default weights initially.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** Plan 02 (transcripts), Plan 09 (scored runs)
**Classification:** structural
**Status:** confirmed
**Adversarial note (Experiment-First Overreach):** This withstands scrutiny. The 66-combo grid search on 3 transcripts is genuinely degenerate. The item should be expressed as: add a hard minimum-sample guard: "If labeled transcript count < 10, skip grid search and log `status: deferred_insufficient_data` in `gvs_calibration.yaml`." Confirm this guard applies to Wave 6 calibration only (not the Wave 3 provisional calibration, which is on 3+ transcripts and not a grid search).

### P14-IMP-09: Evaluation Contract Rubrics Must Evaluate Process, Not Detection Outcome
**Target:** CONTEXT
**What:** The `ground_truth_rubric` specification (Implementation Decision "ground_truth_rubric Specification") uses "all findings covered = 80+" which conflates detection outcome with reasoning process. Since detection accuracy is tracked separately via `GroundTruthComparison`, the rubric scoring bands must score reasoning process coverage, not finding discovery. The Grader Taxonomy section already separates these concerns but does not explicitly bind `ground_truth_rubric` to the process-grader column.
**Why:** With 13.3% detection precision, "findings covered" scores reward outcome luck rather than process quality. More critically, the ambiguity will cause Plan 06 Core contract authors to write outcome-oriented rubrics by default (the linguistic gravity of "expected findings" pulls that way). This makes rubric scores correlated with detection accuracy rather than reasoning quality — partially defeating the point of the 7-move decomposition.
**How:**
1. In the `ground_truth_rubric Specification` section, replace the scoring bands with: "Rubric text MUST describe reasoning process expectations only (examples: 'Agent should query BSKG for external-call patterns before forming an initial hypothesis', 'Agent should explicitly evaluate whether state-write ordering is protected'). Rubric MUST NOT encode detection outcomes ('Agent should find reentrancy'). Score mapping: rubric present + reasoning coverage spans all specified process steps = 80+, partial coverage = 40-79, none covered = 0-39."
2. Add a negative example to the Specification: "NON-CONFORMING: 'Agent finds the reentrancy in withdraw().' CONFORMING: 'Agent queries BSKG for value-movement patterns before invoking hypothesis formation.'"
3. In the Grader Taxonomy section, add one sentence: "`ground_truth_rubric` is a transcript grader (process column). Its scoring bands measure reasoning move coverage, not detection outcomes."
4. Plan 06 exit criterion: "All Core-tier `ground_truth_rubric` texts pass rubric conformance check — zero detection-outcome phrases ('find', 'detect', 'identify the vulnerability') in rubric text."
**Impacts:** Plan 06 Core contract authoring, Plan 07 rubric injection semantics. Plan 12 improvement loop (rubric-coverage score should not correlate with detection accuracy).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Detection Baseline Alignment):** The original How ("MUST describe reasoning process expectations, NOT detection outcomes") is correct but needs a negative example and a verifiable exit criterion. Without a concrete counter-example and a grep-style check, Plan 06 authors will inadvertently use phrases like "Agent identifies the vulnerability" which sound like process language but encode outcome expectations.

### P14-IMP-10: No Cost Constraint on Dual-Opus Evaluation Per Run
**Target:** CONTEXT
**What:** Evaluator Debate Protocol and LLM Call Path specify dual-Opus evaluation with `--effort high`. No cost per evaluation or budget ceiling documented. Each `claude -p` call with Opus on a 15-30 min transcript could cost $2-5 per dimension. With 27 dimensions and dual evaluators, a single Core evaluation could cost $100-270.
**Why:** 3.1e P1-IMP-07 flags this: "dual-Opus evaluation is expensive." Without a cost model, the framework risks being unusable. A $200 evaluation of a $5 agent run is economically absurd.
**How:**
1. Add locked decision: "Cost Budget: Each evaluation run MUST cost < $10 in LLM API calls. Plan 07 must estimate per-dimension cost."
2. Add token budget: "REASONING_PROMPT_TEMPLATE input < 6k tokens, output < 1k tokens. Truncate transcript per dimension."
3. Plan 07 exit criteria: "Cost estimate documented per evaluation configuration."
**Impacts:** Plan 07 dimension count may be constrained. Plan 08/12 budgets become calculable.
**Research needed:** no — RESOLVED 2026-02-23: `claude -p --output-format json` returns `cost_usd` field. Per-dimension cost ~$0.03-0.04 at Opus 4.6. Per Core workflow scoring ~$0.60-0.80. Cost ceiling enforceable via `cost_usd` accumulation.
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Cost & Calibration Grounding):** The $100-270 figure is a worst-case scare number that does not reflect the actual architecture. CONTEXT already specifies per-dimension filtering (depth controls, Mode Capability Matrix, DimensionScore.applicable=False, DIMENSION_TO_MOVE_TYPES mapping, Standard tier headless with no LLM cost). Per-dimension scoring cost is actually ~$0.03-0.038/dimension call at Opus 4.6 pricing, making ~$0.60-0.76 per Core workflow scoring step — far below $100-270. The $10 ceiling is inoperable: `claude -p` calls do not return cost metadata. REFRAME: see P14-ADV-2-02.

### P14-IMP-11: REASONING_PROMPT_TEMPLATE Needs Structured Output and Temperature 0
**Target:** CONTEXT
**What:** The existing `REASONING_PROMPT_TEMPLATE` in `reasoning_evaluator.py` (lines 40-55) instructs the LLM to `Respond as JSON: {"score": N, "evidence": [...], "explanation": "..."}` as freeform prose instruction. The CONTEXT's Evaluator LLM Call Path (IMP-13 Reframe section, lines 367-388) specifies `claude -p --output-format json --json-schema <DimensionScore.schema>`. These conflict: `--json-schema` enforces schema-constrained generation that ignores the freeform JSON instruction in the prompt body. Additionally, the CONTEXT specifies `--effort high` (P11-IMP-06) as the primary non-determinism guard; Temperature 0 is not currently mentioned anywhere despite being the standard control for evaluator reproducibility.
**Why:** Two concrete failure modes: (1) if `--json-schema` is present, the template's `Respond as JSON: {...}` line is noise at best, contradicting at worst — some prompting guides recommend removing explicit JSON instructions when using constrained generation. (2) Without temperature specification, evaluator reproducibility relies solely on `--effort high`, which controls reasoning effort, not sampling stochasticity.
**How:**
1. Rewrite the template instruction section: replace `Respond as JSON: {"score": N, ...}` with field descriptions matching `DimensionScore` schema fields — the schema constraint handles format, the prompt handles semantics.
2. Add a research note in the Evaluator LLM Call Path section: "Verify `claude -p --temperature 0` flag availability in v2.1.47. If available: add `EVALUATOR_TEMPERATURE = 0` constant adjacent to `EVALUATOR_MODEL` and `EVALUATOR_EFFORT`. If unavailable: document as known non-determinism source in CalibrationConfig."
3. Add to Plan 07 exit criteria: "Template does not contain redundant JSON format instruction when `--json-schema` is active; temperature flag verified."
**Impacts:** Plan 07, Plan 12 (CalibrationConfig baseline key may need `temperature` field)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Technical Debt vs Premature Refactoring):** The original item combines two issues (template-schema conflict, temperature) without specifying whether temperature 0 is achievable. The enhancement separates the confirmed fix (template cleanup) from the research item (temperature flag — see P14-ADV-4-02), preventing Plan 07 from being blocked on an unverified platform capability. Second-order: removing `Respond as JSON` means Plan 07 must verify that `DimensionScore.schema` constrains output correctly — if the schema is underspecified, the template instruction was a safety net.

### P14-IMP-12: No Documented Fallback If LLM-as-Judge Fails
**Target:** CONTEXT
**What:** The Calibration Anchor Protocol specifies "HALT if rho < 0.6" with no recovery path. This leaves Plans 01-06's data pipeline investment stranded. A documented fallback is needed that preserves the infrastructure while changing the evaluation strategy.
**Why:** The "HALT" instruction is not actionable. With 13.3% detection precision, rho < 0.6 may reflect evaluator failure OR may reflect the noisy FP environment making rank ordering difficult — these require different responses. Additionally, the naive fallback of using "detection accuracy as primary regression signal" would amplify the FP problem rather than address it: optimizing for the system that produces 65 FPs across 7 contracts makes it worse.
**How:**
1. Add locked decision "LLM-as-Judge No-Go Fallback Protocol" with three diagnostic-first steps: (a) Diagnose rho failure cause — run 3 additional anchor transcripts with extreme-quality variance (known-perfect vs deliberately-broken reasoning). If rho rises above 0.6 with wider variance, the original 18-contract corpus was insufficient; expand corpus. (b) If rho remains < 0.6 after expansion, evaluate whether GVS alone (graph-first compliance + citation rate) produces score spread >= 20pt on the same extreme-variance fixtures. If yes, fall back to GVS-only scoring with heuristic evaluator as supplemental signal only. (c) If GVS also lacks spread: the problem is infrastructure (no observable reasoning signal), not evaluator design. Plans 07-12 are blocked; restart from Plan 02 with real transcript diagnosis.
2. Explicitly exclude detection accuracy from fallback scoring options, citing Grader Taxonomy separation. Detection accuracy remains a KILL criterion for changes but never becomes the primary improvement signal.
3. Change Calibration Anchor HALT text to: "HALT and invoke No-Go Fallback Protocol (see LLM-as-Judge No-Go Fallback)."
**Impacts:** Plan 12 Part 0 gains structured fallback. No plan scope changes unless LLM evaluation fails.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 1
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Detection Baseline Alignment):** The original fallback option (c) — "detection accuracy as primary regression signal" — would create a direct conflict with P14-IMP-09 and the Grader Taxonomy separation. At 13.3% precision, using detection accuracy to drive improvement means optimizing for finding more false positives. The rewrite removes this option and replaces it with a diagnostic-first approach that distinguishes corpus insufficiency from structural evaluator failure.

### P14-IMP-13: Debrief Protocol Layers 2-4 Over-Designed for v1
**Target:** CONTEXT
**What:** Debrief Strategy (lines 82-113) specifies four layers. Layer 1 (SendMessage) requires interactive mode, applicable to ~25/51 workflows. Layer 2 has LOW confidence. Layers 3-4 are optional/fallback. Plan 05 builds infrastructure for all 4 layers.
**Why:** For v1, only Layer 1 is reliable and only for interactive workflows. Standard-tier (26 workflows) run headless with no debrief. Building 4 layers when only 1 works is premature.
**How:**
1. Narrow Plan 05 v1 scope: "Layer 1 (SendMessage) only. Layers 2-4 documented as degradation paths but not implemented until Layer 1 validated on 5+ real interactive sessions."
2. Add Plan 05 exit criteria: "Layer 1 validated on 1+ real interactive session before Layer 2 begins."
**Impacts:** Plan 05 scope reduction. Plan 07 debrief scoring simplified.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 02 (real transcripts)
**Classification:** structural
**Status:** rejected
**Adversarial note (Experiment-First Overreach):** This was explicitly rejected in Pass 2 as P2-IMP-16 ("Remove Layers 2 and 3 from debrief cascade. Rejected because: Layer 3 transcript analysis serves a different purpose than the evaluator. Even low-confidence debrief data provides unique signal."). Pass 13 further refined layer weights into `debrief_layer_weight` (P13-ADV-4-02), giving headless contracts `weight: 0.0` — effectively silencing Layers 2-4 for headless workflows. The `debrief_layer_weight` mechanism already implements the item's intent without deleting the cascade. Rehashing a rejected item using 3.1e authority without engaging the rejection rationale is not valid.

### P14-IMP-14: Plans 08-11 Need "Quality Validation Gate" Before 51-Workflow Scope
**Target:** CONTEXT
**What:** Add a concrete scoring quality validation fixture (a "known-good vs known-bad transcript pair") as a Plan 08 pre-execution gate. Specifically: (1) Create a paired fixture set — one transcript where the agent demonstrably queries BSKG first, uses node IDs in reasoning, and finds the known vulnerability ("good"), and one where the agent reads Solidity directly, uses no graph queries, and misses the vulnerability ("bad"). (2) Run the full pipeline (GVS + reasoning evaluator + debrief) on both fixtures. (3) Assert that good_score > bad_score on at least 3 of the 4 GVS dimensions AND at least 2 reasoning dimensions. (4) If assertion fails: block Wave 6 execution and diagnose scoring pipeline. This is distinct from Gate 0 (which validates execution plumbing) and from Calibration Anchor (which validates rank-ordering against ground truth).
**Why:** CONTEXT's Gate 0 ("validates mechanics, not scoring quality") is correctly identified as insufficient. The Calibration Anchor Protocol in Plan 12 Part 0 validates rank-ordering against external ground truth — but it fires AFTER Wave 6 (Plans 09-11) have run. A scoring quality gate BEFORE Wave 6 costs ~30 minutes and prevents wasting 8-26 hours of Wave 6 execution on inverted baselines.
**How:**
1. In Plan 08 deliverables, add: "Scoring Quality Gate fixture: paired known-good and known-bad transcripts at `tests/workflow_harness/fixtures/scoring_quality_gate/`. Good transcript: agent performs >= 2 BSKG queries before reading any .sol file, uses node IDs in conclusion, TP detection confirmed in ground_truth.yaml. Bad transcript: agent reads .sol directly, no BSKG queries, misses the vulnerability."
2. Add Plan 08 exit criterion: "EvaluationRunner produces higher effective_score() for good fixture than bad fixture on GVS (>= 3 dimensions) AND reasoning assessment (>= 2 dimensions). Failure blocks Plan 09 execution."
3. Note in CONTEXT.md Cross-Plan Dependencies: `08 | 09-11 | Scoring Quality Gate fixture must pass | YES`. This is a sequencing constraint only.
**Impacts:** Plan 08 gains deliverable. Plans 09-11 gain harder prerequisite. +30 min if passes, saves 8-26 hours if broken.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 07 (evaluator must exist)
**Classification:** structural
**Status:** enhanced
**Adversarial note (Experiment-First Overreach):** The original item correctly identifies the gap but the How was too vague ("good-vs-bad fixture, 30 min"). "Good vs bad" is ambiguous without specifying what makes a transcript "known good." The rewrite operationalizes the fixture specification. This does NOT conflict with the Calibration Anchor Protocol — they validate different things: quality gate tests pipeline directionality (good > bad); anchor tests absolute rank-ordering against external ground truth.

### P14-IMP-15: Plan 08 Deliverable Numbering Has Duplicates
**Target:** CONTEXT
**What:** Plan 08 has two items numbered "13" (lines ~1999 and ~1983). Plan 09 has two items numbered "2" (lines ~2019 and ~2020). Cross-references break with ambiguous numbers.
**Why:** Implementers referencing "Plan 08 deliverable 13" get the wrong item.
**How:** Renumber Plan 08 deliverables sequentially 1-17. Renumber Plan 09 deliverables 1-11.
**Impacts:** No plan structure changes. Cross-reference verification needed.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** cosmetic
**Status:** confirmed
**Adversarial note (Technical Debt vs Premature Refactoring):** Confirmed as a genuine bug. Plan 08 has three items numbered "13" and Plan 04 has deliverable ordering issues. These are real numbering errors — duplicate numbers cause ambiguous task references. The fix is mechanical and changes no specification content.

### P14-IMP-16: Capability Check Thresholds Undefined at 13.3% Detection Precision
**Target:** CONTEXT
**What:** Plans 09-11's capability contract checks have undefined pass thresholds for structural execution quality. With 13.3% precision, outcome-based thresholds (e.g., `expected_findings_count`) trivially pass — agents always find many things (mostly FPs). Process-based thresholds (e.g., `bskg_queried: true`, `debrief_received: true`, `tool_calls_completed: N`) do not reference detection outcomes but still need calibration to avoid trivial pass or systematic fail.
**Why:** A capability check that trivially passes provides no gate. A check calibrated to detection outcome is measuring luck. The two-stage architecture is sound; the threshold definitions are not. Without explicit guidance, Plan 06 contract authors will default to outcome-based thresholds, producing contracts that always pass and give false confidence before reasoning evaluation.
**How:**
1. Add to Implementation Decision "Tiered Contract Authoring Policy": "Capability check fields in Core/Important contracts MUST use structural execution criteria only: `bskg_queries_executed: true`, `tool_sequence_complete: true`, `session_completed: true`, `debrief_collected: true` (for interactive). PROHIBITED capability fields: `findings_count >= N`, `vulnerabilities_found >= N`. These are outcome fields, not capability fields."
2. Plan 06 exit criterion: "Zero Core/Important capability contracts contain outcome-based capability thresholds (grep: `findings_count`, `vulnerabilities_found` as required capability criteria)."
3. Gate 0 report must include capability pass rate. If 100% trivially pass (no gate value) OR 0% pass (over-tight thresholds), HALT and recalibrate before sub-wave (a). Add this to Wave 6 Execution Plan.
4. Add a note under Detection Accuracy Testing: "Detection accuracy is a SEPARATE outcome metric tracked post-capability-gate, never used as the capability gate criterion itself."
**Impacts:** Plan 06 contract authoring needs explicit prohibited-field list. Plans 09-11 gates become structurally calibrated. Plan 08 Gate 0 report gains pass-rate health check.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** Plan 06 (contracts)
**Classification:** structural
**Status:** enhanced
**Adversarial note (Detection Baseline Alignment):** The original How says "reference detection baseline (13.3% precision, 83.3% recall)" but gives no concrete translation. The real problem is that outcome-based thresholds will always trivially pass at 13.3% precision because FPs inflate the count. The rewrite explicitly prohibits outcome-based capability fields and defines structural execution criteria as the only valid capability gate.

### P14-IMP-17: Plan 08 Bug Fix References Stale Line Number
**Target:** CONTEXT
**What:** Plan 08 deliverable 16: "evaluation_runner.py:263 calls update_baseline() unconditionally". The actual code may have shifted (file is 314 lines, baseline call may be at 265).
**Why:** Stale line references cause implementers to modify wrong code.
**How:** Change to "evaluation_runner.py `_baseline_manager.update_baseline()` call in `run()` method" — reference pattern, not line number.
**Impacts:** Plan 08 only. Implementer clarity.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** cosmetic
**Status:** confirmed
**Adversarial note (Technical Debt vs Premature Refactoring):** Confirmed. Line numbers in a 510-LOC file that will be modified by Plans 01-07 before Plan 08 runs are guaranteed to be stale. The fix to a method-pattern reference is unambiguous and durable.

### P14-IMP-18: Wave 6 Needs Intra-Stage Circuit Breaker
**Target:** CONTEXT
**What:** Add a circuit breaker rule to the Wave 6 Execution Schedule: if 3 consecutive workflows within a stage produce `status='failed'` with the same `failure_reasons` entry (identical root cause), HALT the stage and write a structured halt report. The halt report includes the shared failure reason, count of affected workflows, and recommended action. Resume requires human acknowledgement.
**Why:** The existing intra-stage failure policy says "write EvaluationResult(status='failed') and continue." This is correct for isolated failures but not for systematic root causes. If hook installation is systematically broken, or if a contract schema error affects all workflows in a category, the current policy consumes the entire stage budget before surfacing a fixable root cause. Wave 6 Stage 2 alone is 4-8 hours. A 10 LOC guard prevents a multi-hour blind run.
**How:**
1. In the "Intra-stage failure policy" paragraph, add: "Circuit breaker: if 3 consecutive workflows produce `status='failed'` with identical `failure_reasons[0]`, HALT stage execution. Write `.vrs/evaluations/stage_halt_{stage}_{timestamp}.json` with `{stage, halt_reason, affected_workflow_ids, consecutive_count, recommended_action}`. Human must acknowledge (delete halt file) before stage can resume. ~10 LOC in the CC skill between-workflow loop."
2. Add `recommended_action` lookup table for known halt reasons: `hook_installation_failed → "Re-run Plan 02 hook installation"; contract_schema_invalid → "Run validate_scenarios.py"; delegate_mode_violation → "Inspect SKILL.md delegation rules"`.
3. Add to Plan 09 exit criteria: "Circuit breaker triggers on fixture with 3 consecutive identical failures."
**Impacts:** Plans 09-11 (all share Wave 6 execution policy)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Technical Debt vs Premature Refactoring):** Genuinely needed — this is not premature infrastructure. It closes a real gap in the failure policy. The enhancement specifies the halt file schema and lookup table. Second-order: the 3-consecutive threshold may be too sensitive for Standard tier (26 headless workflows with higher baseline failure rates). The circuit breaker should be tier-aware: 3 for Core/Important, 5 for Standard.

### P14-IMP-19: Plans 09-11 "~15% Pre-Addressed" Claim Is Misleading
**Target:** CONTEXT
**What:** Plans 09-11 list `src/alphaswarm_sol/shipping/skills/test-suite/` as primary location. This directory doesn't exist. "~15% pre-addressed" refers to scenario framework, not the CC skill that orchestrates Wave 6.
**Why:** The CC skill is the novel, high-risk component. 0% exists for it.
**How:** Change "~15% pre-addressed" to "~15% pre-addressed (scenario framework + contracts). Primary CC skill test-suite/ does not exist (0% on orchestration component)."
**Impacts:** Plans 09-11 risk assessment visibility.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** cosmetic
**Status:** confirmed
**Adversarial note (Technical Debt vs Premature Refactoring):** Confirmed. The scenario framework (32 YAML files, working JSON Schema validation, scenario plugin) is test infrastructure — it does NOT pre-address the CC skill `/vrs-test-suite` which is the primary artifact. "~15% pre-addressed" is ambiguous and misleads planners.

### P14-IMP-20: Plan 12 Needs Explicit Dependency on 3.1e MVL Go/No-Go
**Target:** CONTEXT
**What:** Plan 12's 6-part improvement loop assumes detect-improve-re-detect works. 3.1e Plan 01 (MVL) tests exactly this with a single pattern fix. If MVL shows zero improvement, Plan 12 Parts 2-3 are premature. No dependency exists in Cross-Plan Dependencies table.
**Why:** The Spearman rho gate tests evaluator-detection correlation, NOT improvement viability. These are different questions. Plan 12 is a ~2 week effort — an explicit MVL gate is cheaper than discovering the assumption is wrong mid-execution.
**How:**
1. Add to Cross-Plan Dependencies: `| 3.1e-01 (MVL) | 12 Part 2 | MVL precision delta proves improvement cycle viability | YES |`
2. Plan 12 Part 2 pre-condition: "3.1e MVL must show precision delta > 0 on at least one contract"
3. Add Implementation Decision: "3.1e MVL Gate: Plan 12 Part 2 cannot begin until 3.1e demonstrates measurable improvement"
**Impacts:** Plan 12 gains hard sequencing constraint on 3.1e.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 01 from 3.1e (MVL)
**Classification:** structural
**Status:** reframed
**Adversarial note (Experiment-First Overreach):** The dependency proposal is structurally invalid for three reasons: (1) 3.1e's MVL measures a different thing than Plan 12 Part 2 needs — they share no contractual surface, (2) Plan 12 already has internal go/no-go gates (Spearman rho, addressable count) more tightly coupled to Part 2's risk, (3) adding a cross-phase dependency to 3.1e would create a dependency graph loop (3.1e is downstream of 3.1c). The real gap is to strengthen Plan 12's own go/no-go criteria. REFRAME: see P14-ADV-1-02.

### P14-IMP-21: Convergence Detection Thresholds Are Theoretical, Not Empirically Grounded
**Target:** CONTEXT
**What:** The convergence detection thresholds in Plan 12 Part 3 ("improvement is <2 points per cycle for the last 2 cycles" triggers CONVERGED states) are pre-empirical constants that will produce systematic mislabeling when actual inter-run variance is measured in Plan 12 Part 1. CONTEXT specifies that Part 1 runs Core tier 5x for variance measurement, but Part 3 convergence detection does not reference these variance measurements. The 2pt threshold is too small relative to likely evaluator variance (two independent Opus runs with debate routinely differ by 5-10pt within the defined disagreement window). Add to Plan 12 Part 3: "Before emitting any CONVERGED_* declaration, read Core-tier variance data from Part 1. If per-dimension standard deviation > 3pt, raise convergence threshold to max(2pt, 1.5 × sd). Write as `convergence_config.yaml` at Part 2 start."
**Why:** A 2pt threshold against an 8pt standard deviation produces ~40% false positive CONVERGED_HIGH declarations. False convergence declarations in CONVERGED_PLATEAU cause premature addition to `pending_redesign_candidates.yaml`. False CONVERGED_LOW triggers FailureReport with `recommendation: redesign_needed` for adequately-performing workflows.
**How:**
1. Add to Plan 12 Part 3 specification: "Convergence threshold = max(2pt, 1.5 × per_dimension_sd_from_part1). If Part 1 variance data is absent, use 5pt conservative default instead of 2pt."
2. Add `convergence_config.yaml` artifact to Plan 12 Part 2 setup: `{computed_at, source_run_count, per_dimension_thresholds: dict[str, float]}`. Write before improvement cycles begin. Plan 12 exit criterion: "convergence_config.yaml exists and references actual Part 1 data."
3. Add validation: if any per-dimension threshold > 15pt, flag WARNING "high evaluator variance — convergence detection unreliable on this dimension."
**Impacts:** Part 1 gains small deliverable. Part 3 gains startup dependency.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none (internal to Plan 12)
**Classification:** structural
**Status:** enhanced
**Adversarial note (Cost & Calibration Grounding):** Directionally correct. The original How was vague ("replace fixed thresholds with provisional values"). The rewrite makes it actionable: compute threshold from Part 1 data, write to named artifact, reference from Part 3. Second-order risk: Plan 12 Part 1 data is in BaselineManager's rolling window — Part 3 needs a concrete extraction path, not a vague "from Part 1 variance data." Part 1 must write a variance summary file.

### P14-IMP-22: API Cost Estimates Missing for Wave 6 and Plan 12 Part 1
**Target:** CONTEXT
**What:** The Shared Execution Note (lines 2117-2153) provides wall-clock estimates but zero cost estimates. Plan 12 Part 1 runs "All 51 tests 1x; Core 5x for variance" with dual-Opus evaluation. No cost appears anywhere.
**Why:** Cost visibility is a prerequisite for informed go/no-go. 3.1e explicitly considers costs ($0.07-0.20/run). Without estimates, HITL reviewers at sub-wave boundaries cannot make rational decisions. Estimated range: Wave 6 scoring alone ~$5-15, CC session execution ~$50-200+. Plan 12 Part 1: $200 (cached transcripts) to $1,200 (fresh runs).
**How:**
1. Add "API Cost Estimates [ESTIMATE: update after first Core run]" subsection to Shared Execution Note
2. Add to Plan 12 Part 1: "Cost estimate: ~101 dual-Opus evaluations. Scoring cost ~$200. Agent execution if required ~$1,010. Total range: $200-$1,200. Human approval required."
3. Stage 3 HITL gate: "Reviewer receives cost-per-workflow actuals. If cost exceeds estimate by >2x, reviewer may reduce scope."
**Impacts:** Plans 09-11 and Plan 12 gain cost transparency.
**Research needed:** no — RESOLVED 2026-02-23: `cost_usd` available per `claude -p` call via JSON output. ccusage data confirms typical Opus 4.6 session costs. See P14-ADV-2-02 for consolidated cost model.
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Cost & Calibration Grounding):** The estimates are simultaneously too wide ($50-200+ is a 4x range with open upper bound) and conflate agent execution cost with evaluator scoring cost. The $200-$1200 Plan 12 range has 6x spread — not cost visibility but a disclaimer. Static dollar numbers in planning documents will mislead future readers as pricing changes. Both IMP-10 and IMP-22 address the same gap from different angles. REFRAME: see P14-ADV-2-02.

### P14-IMP-23: Failure Reporter Categories Should Come From 3.1e Taxonomy
**Target:** CONTEXT
**What:** Plan 12 Part 4 Failure Reporter uses hand-designed failure categories with no specified values. These categories will be used before any failure observations exist, meaning they are speculative. 3.1e Plan 04 will produce empirically-derived taxonomy after real runs — but may complete after Plan 12 Part 4 begins, creating a timing dependency.
**Why:** Hand-designed categories risk misclassifying FP-inflated poor scores as reasoning failures (e.g., a "poor reasoning" category may capture what is actually "agent is responding to 87% FPs by hedging"). The fix must specify both the fallback (provisional categories) AND the transition path when 3.1e taxonomy arrives.
**How:**
1. Plan 12 Part 4: "Use taxonomy from 3.1e Plan 04 (`failure_taxonomy.yaml`) if available at Part 4 start. If unavailable: use provisional categories `[bskg_compliance_failure, tool_sequence_failure, debrief_absent, scoring_infrastructure_failure, reasoning_quality_failure]`. Flag reports with `taxonomy: provisional`."
2. Add provisional category `precision_environment_noise` to handle cases where score variance exceeds evaluator variance (may reflect FP-inflated inputs, not reasoning regression).
3. Add transition step in Part 4: "If `failure_taxonomy.yaml` arrives during Part 4, re-classify accumulated failures and note reclassification in ledger."
4. Add soft dependency to Cross-Plan Dependencies table: `| 3.1e-04 (taxonomy) | 12 Part 4 | Empirical failure categories | SOFT |`
**Impacts:** Plan 12 Part 4 gains specified provisional categories. 3.1e soft dependency becomes concrete.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 1
**Prerequisite:** no
**Depends on plans:** Plan 04 from 3.1e (soft)
**Classification:** structural
**Status:** enhanced
**Adversarial note (Detection Baseline Alignment):** The original item correctly identifies the anti-pattern but leaves "provisional categories" unspecified. The rewrite specifies the provisional categories, adds `precision_environment_noise` as a FP-specific category the original hand-design would miss, and defines the transition protocol when empirical taxonomy arrives.

### P14-IMP-24: Part 0 Should Check Goodhart Risk, Not Just Evaluator Correlation
**Target:** CONTEXT
**What:** Plan 12 Part 0 computes Spearman rho (evaluator-detection correlation) but does not check evaluator gameability. A gameable evaluator can achieve rho > 0.6 on current corpus while still being vulnerable to systematic gaming when improvement cycles optimize against it. FS-01 already documents this failure mode. 3.1e-03's Goodhart screen is the designated mitigation, but its integration into Part 0 needs defined semantics.
**Why:** In the 13.3% precision environment, gaming is easier: because agents already produce high FP rates, an evaluator that rewards citation density can be gamed by prompt changes that increase specificity without improving discrimination. Rho measures correlation on current data; Goodhart risk measures evaluator sensitivity to optimization pressure. Both are needed before committing to iterative improvement.
**How:**
1. Add to Part 0: "Goodhart screen: if 3.1e-03 result file `goodhart_risk.yaml` exists, load it. Parse `risk_level` field. Decision tree: (a) `risk_level: low` — proceed. (b) `risk_level: medium` — proceed with WARNING logged to calibration report; add 'Goodhart surveillance' to Part 1 deliverables (track per-dimension score variance across 5 Core runs). (c) `risk_level: high` — do NOT proceed to Part 2 without human approval. Present risk report and require explicit human sign-off. If unavailable: `goodhart_screen: deferred`; proceed with WARNING."
2. Note in Part 0: "3.1e-03 must define `risk_level` in terms of evaluator sensitivity to citation density, specificity, and structural complexity signals — the three most easily-gamed dimensions in the 13.3% precision environment."
3. Add soft dependency to Cross-Plan Dependencies: `| 3.1e-03 (Goodhart) | 12 Part 0 | Evaluator gameability check | SOFT |`
4. Do NOT make `risk_level: high` a hard HALT. Make it a human-approval gate. Automated HALT on an undefined artifact from 3.1e creates a false sense of protection.
**Impacts:** Plan 12 Part 0 gains tiered Goodhart screen. Part 1 gains surveillance deliverable for medium risk.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** Plan 03 from 3.1e (soft)
**Classification:** structural
**Status:** enhanced
**Adversarial note (Detection Baseline Alignment):** The original "HALT Part 2 regardless of rho" for `risk_level: high` is too aggressive given that `goodhart_risk.yaml` semantics are undefined. In the 13.3% precision environment, false-triggering a HALT on an undefined risk signal blocks the improvement effort specifically needed to address the precision problem. The rewrite preserves intent while requiring human judgment for high-risk and downgrading medium risk to surveillance.

### P14-IMP-25: Spearman rho [0.3, 0.6) Is an Undefined State
**Target:** CONTEXT
**What:** The Calibration Anchor Protocol specifies rho > 0.6 as the pass threshold and rho < 0.3 as the halt condition. The interval [0.3, 0.6) has no documented response, creating a decision vacuum when the system produces a marginal result. With 72 data points (4 agents x 18 contracts), a measured rho of 0.45 has a 95% bootstrap CI approximately [0.25, 0.62] — the true value is consistent with both "near-pass" and "near-fail". Add to "Calibration Anchor Protocol" locked decision: "If measured rho is in [0.3, 0.6): (a) compute 1000-sample bootstrap CI using scipy.stats.bootstrap on the 72 rank pairs. If CI lower bound > 0.5: PROCEED with `calibration_epoch: 'provisional'` and schedule re-validation after 5 improvement cycles. If CI lower bound <= 0.5: HALT, diagnose same as rho < 0.3. Write rho_ci to CalibrationConfig as `spearman_rho_ci: tuple[float, float]`."
**Why:** The [0.3, 0.6) gap is not academic. At 13.3% precision, early calibration runs are likely to land in this range. Without documented response, the human reviewer applies either halt (too conservative) or pass (too permissive). Bootstrap CI is the standard statistical tool — it requires only a scipy.stats import and ~15 LOC.
**How:**
1. Add `spearman_rho_ci: tuple[float, float] | None = None` to `CalibrationConfig` model in Plan 01. Always populated when rho is computed.
2. Add to Plan 12 Part 0: three-branch decision after rho computation: rho >= 0.6 → PASS; rho in [0.3, 0.6) → compute bootstrap CI, branch as specified; rho < 0.3 → HALT. ~15 LOC.
3. Add to locked "Calibration Anchor Protocol" decision: the three-branch decision tree with specific CI threshold (lower bound > 0.5 = proceed provisional). Binding on all future Plan 12 implementations.
4. Plan 12 Part 0 exit report: always include rho + CI in `calibration_config.yaml` regardless of branch.
**Impacts:** Plan 12 Part 0 gains ~15 LOC for bootstrap CI. CalibrationConfig model gains field.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Cost & Calibration Grounding):** Strongest item in the group. The [0.3, 0.6) gap is genuine, 72-point sample size correctly identified as producing wide CI, and bootstrap CI is standard and well-scoped. The original How was underspecified ("add bootstrap CI for marginal cases"). Rewrite provides complete decision tree, names the threshold (0.5), identifies exact CalibrationConfig field, and scopes implementation. Second-order: scipy.stats.bootstrap requires scipy >= 1.7 — verify against project requirements.

---

## Adversarial CREATE Items

### P14-ADV-1-01: Plan 01 Types — Annotate Provisional Fields, Don't Defer Types
**Target:** CONTEXT
**What:** Add a `# PROVISIONAL: calibrate in Plan 12 Part 0` annotation convention for types whose field inventories are empirically unverifiable before real runs. Apply to specific contested fields in `ExperimentLedgerEntry` (`calibration_epoch`), `ToolUseData`/`ToolResultData` (IMP-28 marked "Optional in Wave 1"), and `CalibrationConfig` (`n_transcripts`, `spearman_rho`). Do NOT defer type declaration — defer only field-level constants and optional field defaults.
**Why:** Deferring type declarations (as P14-IMP-01 proposed) breaks the dependency graph. But pretending all 30+ types are fully specified is also wrong — `ToolUseData`'s `tool_use_id` field correctness depends on P0's `tool_use_id` confirmed non-null test. The annotation convention allows the pipeline to compile while marking fields whose values are empirically constrained.
**How:**
1. Identify fields in Plan 01 deliverables marked "blocked on Plan 02" or "Optional in Wave 1": `ToolUseData.tool_use_id`, `ToolResultData.output_preview`, `CalibrationConfig.spearman_rho` (pre-calibration value), `ExperimentLedgerEntry.calibration_epoch` default.
2. Add `# PROVISIONAL: validate in Plan 02 P0 — field may be None before tool_use_id confirmed` inline annotations to these fields in `models.py`.
3. Add Plan 01 exit criterion: "All PROVISIONAL fields have corresponding Plan 02 or Plan 12 exit criteria that will remove the annotation."
**Impacts:** Plan 01, Plan 02
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** open
**Source:** Adversarial review (Experiment-First Overreach)
**Cross-references:** replaces: P14-IMP-01; see also P14-IMP-03
**Adversarial note (Experiment-First Overreach):** Solves the real problem behind P14-IMP-01 (over-specified types) without breaking the compilation dependency chain.

### P14-ADV-1-02: Plan 12 Part 2 Go/No-Go — Strengthen Addressable Count Threshold
**Target:** CONTEXT
**What:** Strengthen Plan 12 Part 2's early-exit guard: replace the arbitrary `addressable_count < 5` halt threshold with a proportional criterion: "If addressable patterns represent < 30% of total low-scoring patterns, HALT Part 2 with `part2_blocked.yaml`." Add rationale: when infrastructure gaps (BSKG/VulnDocs) dominate low scores, the improvement loop generates hints for patterns it cannot fix.
**Why:** The current threshold of 5 is not grounded in any analysis. If there are 50 low-scoring patterns and 4 are addressable, the improvement loop runs (5 > threshold) but 92% of its targets are infrastructure-blocked — producing meaningless ExperimentLedgerEntry records that contaminate convergence detection.
**How:**
1. In CONTEXT.md Plan 12 Part 2 section, replace "If `addressable_count < 5`, HALT" with "If `addressable_count < max(5, 0.30 * total_low_scoring)`, HALT."
2. Add to `part2_blocked.yaml` schema: `addressable_ratio: float` field alongside existing counts.
3. Add rationale comment: "30% threshold: below this, infrastructure gaps dominate and improvement loop has insufficient signal-to-noise ratio."
**Impacts:** Plan 12
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 1
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** open
**Source:** Adversarial review (Experiment-First Overreach)
**Cross-references:** replaces: P14-IMP-20; see also Calibration Anchor Protocol
**Adversarial note (Experiment-First Overreach):** Addresses the real gap behind P14-IMP-20 (improvement loop viability) without importing an invalid cross-phase dependency from 3.1e.

### P14-ADV-2-01: CalibrationConfig Re-Entry Path After rho Failure
**Target:** CONTEXT
**What:** Specify the re-entry mutation path when a calibration failure is diagnosed and fixed. Currently: HALT is the only documented response to rho < 0.6, with no specification for how the system state resets to allow a new calibration attempt after underlying issues are addressed.
**Why:** A permanent HALT is operationally correct for an automated loop, but the manual trigger protocol requires a human to restart Plan 12 after fixing infrastructure misses. Without a defined re-entry path, `calibration_epoch: 'provisional'` on existing ExperimentLedgerEntry records is ambiguous. CalibrationConfig.from_disk() will load the failed calibration config, causing the startup guard to block the new run unless explicitly reset.
**How:**
1. Add to "Calibration Anchor Re-Validation" locked decision: "On rho < 0.6 HALT, write `calibration_config.yaml` with field `status: 'failed'` (separate from `calibration_epoch`). Plan 12 startup guard: if status == 'failed', require explicit `--reset-calibration` flag or human deletion of the file before re-run."
2. Add to Plan 12 Part 0: "After infrastructure_misses.yaml review and remediation, delete or overwrite `calibration_config.yaml` before re-running anchor. New run writes fresh config. Existing ExperimentLedgerEntry records with `calibration_epoch: 'provisional'` from prior runs are reclassified via `reclassify_provisional()` against new thresholds."
3. Add `status: Literal['pending', 'passed', 'failed']` to `CalibrationConfig` model (NOT to `calibration_epoch`) — this is a config artifact field, not an ExperimentLedgerEntry routing field.
**Impacts:** Plan 01 (CalibrationConfig model), Plan 12 Part 0, Part 0.5
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** open
**Source:** Adversarial review (Cost & Calibration Grounding)
**Cross-references:** replaces: P14-IMP-02; also related to P11-ADV-3-01, P11-IMP-15
**Adversarial note (Cost & Calibration Grounding):** IMP-02's proposed `'failed'` state on `calibration_epoch` is architecturally wrong — `calibration_epoch` routes ExperimentLedgerEntry records through hint queues, not calibration run status. The real gap is CalibrationConfig reset semantics after a HALT event.

### P14-ADV-2-02: Documented Per-Run Cost Model for HITL Go/No-Go Decisions
**Target:** CONTEXT
**What:** Add a concrete per-run cost derivation to the Plan Summaries or Wave 6 Execution Schedule so HITL reviewers understand the cost commitment before approving each wave. Currently there are wall-clock estimates but no token/cost estimates.
**Why:** The evaluation architecture has THREE distinct cost drivers: (1) Core-tier interactive run (execution: Opus-powered agents in real sessions — dominant cost), (2) per-workflow scoring (dual-Opus `claude -p --effort high` for applicable dimensions only — NOT 27 per run), (3) calibration anchor (one-time: 4 agents x 18 corpus contracts). Without separating these, HITL reviewers cannot make calibrated go/no-go decisions. The corrected per-workflow scoring estimate: ~$0.60-0.76 per Core workflow (10 applicable dimensions x 2 evaluators x ~$0.03-0.038/dimension), far below the $100-270 scare figure.
**How:**
1. Add "Per-Run Cost Model" subsection to Wave 6 Execution Schedule: derive Core-tier scoring cost from applicable dimensions (8-12 of 27 after mode + applicability filtering) x 2 evaluators x ~$0.03-0.038/dimension. Note that dominant cost is agent execution, not evaluator scoring.
2. Add "Calibration Anchor Cost Estimate" to Plan 12 Part 0: 4 agents x 18 corpus contracts = 72 sessions. Flag as requiring explicit HITL approval.
3. Add note: "Per-run cost ceiling enforcement via `claude -p` IS possible — `claude -p --output-format json` returns `cost_usd` and `usage` fields. Cost management via architecture (applicable dimensions filter) + per-call cost accumulation + HITL approval gates."
**Impacts:** Plan 12 Part 0, Plans 09-11 Wave 6 Schedule
**Research needed:** no — RESOLVED 2026-02-23: `claude -p --output-format json` DOES return `{result, model, usage, cost_usd}`. Cost tracking per call is possible. Prior claim that cost metadata is unavailable was INCORRECT.
**Confidence:** MEDIUM
**Prior art:** 1
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** open
**Source:** Adversarial review (Cost & Calibration Grounding)
**Cross-references:** replaces: P14-IMP-10, P14-IMP-22
**Adversarial note (Cost & Calibration Grounding):** The original items propose an unenforceable programmatic ceiling (IMP-10) and wide static ranges (IMP-22). The real gap is a written cost derivation separating execution from scoring cost, enabling HITL reviewers to make calibrated decisions.

### P14-ADV-3-01: FP Rate Visibility in EvaluationResult
**Target:** CONTEXT
**What:** `EvaluationResult` and the evaluation summary currently have no field for per-run FP rate or precision estimate. An agent scored 75 on reasoning and producing 12 FPs vs. an agent scored 75 on reasoning and producing 1 FP are currently indistinguishable.
**Why:** Without FP rate in `EvaluationResult`, the improvement loop cannot distinguish reasoning improvements that also improve precision from reasoning improvements that inflate scores while worsening precision. FS-01 specifically describes this failure. The External Detection Validation catches this at experiment level — but only if the evaluator explicitly tracks per-run detection data. Currently `detection_validation` fields are on `ExperimentLedgerEntry`, not `EvaluationResult`.
**How:**
1. Add `detection_summary: DetectionSummary | None = None` to `EvaluationResult` model (Plan 01). `DetectionSummary` fields: `tp_count: int | None`, `fp_count: int | None`, `fn_count: int | None`, `precision: float | None`, `corpus_contract: str | None`. All nullable — only populated for corpus-contract runs with ground truth.
2. Plan 03/Plan 08: after `GroundTruthComparison` runs, populate `DetectionSummary` on the `EvaluationResult`.
3. Plan 12 Part 1 rho computation: use `EvaluationResult.detection_summary.precision` instead of separate lookup. Single source of truth.
4. `alphaswarm evaluation summary` CLI: display `fp_count` alongside reasoning scores when `detection_summary` is present.
**Impacts:** Plan 01 model gains `DetectionSummary`. Plan 03/08 populate it. Plan 12 reads it.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 03 (GroundTruthComparison wiring)
**Classification:** structural
**Status:** open
**Source:** Adversarial review (Detection Baseline Alignment)
**Cross-references:** P14-IMP-09, P14-IMP-12, P14-IMP-16
**Adversarial note (Detection Baseline Alignment):** The Grader Taxonomy correctly separates transcript graders from outcome graders. But without FP rate on `EvaluationResult`, the separation becomes opaque at the artifact level. Linking `DetectionSummary` to `EvaluationResult` (for corpus runs) closes this visibility gap without conflating grader types.

### P14-ADV-4-01: Clarify Plan 03 Skeleton Parallelism Opportunity
**Target:** CONTEXT
**What:** Add an explicit note in Cross-Plan Dependencies table and Plan 03 summary clarifying that Plan 03's ~40 LOC adapter skeleton can be authored during Plan 02 execution, but `tool_use_id` wiring and real transcript validation are gated behind Plan 02's HARD EXIT CRITERION. The current CONTEXT says only "Depends on: Plan 01 (models), Plan 02 (tool_use_id)" without specifying which Plan 03 deliverables are hard-blocked vs. parallelizable.
**Why:** The REFRAME of P14-IMP-04 identified that the underlying scheduling concern (02→03 stall risk) is real even though merger is wrong. Without parallelism guidance, implementers will wait for Plan 02's full exit before touching Plan 03. Making the skeleton-authoring window explicit saves 1-3 implementation days.
**How:**
1. In Cross-Plan Dependencies table, add footnote to `02 → 03 (tool_use_id)` YES row: "Hard-blocked: deliverables 2 (LIFO replacement), 4 (real transcript test), 9 (session_id filter). Parallelizable: deliverable 1 skeleton, class stubs, return type signature."
2. In Plan 03 summary, add sentence: "Wave 2 parallelism: adapter skeleton may be authored during Plan 02 execution. Deliverables gated on Plan 02 hard exit: LIFO replacement, real transcript validation, session_id filter."
**Impacts:** Plan 02, Plan 03
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** open
**Source:** Adversarial review (Technical Debt vs Premature Refactoring)
**Cross-references:** replaces: P14-IMP-04
**Adversarial note (Technical Debt vs Premature Refactoring):** The merger in P14-IMP-04 is wrong, but the scheduling risk is real. This CREATE addresses the concern without collapsing a structurally meaningful boundary.

### P14-ADV-4-02: Temperature Flag Verification Research Item for Plan 07
**Target:** RESEARCH
**What:** Verify whether `claude -p --temperature 0` (or equivalent `CLAUDE_DEFAULT_TEMPERATURE`) is available in the current CC version (v2.1.47). If available: add `EVALUATOR_TEMPERATURE = 0` constant to Plan 07 and `temperature` field to `BaselineKey`. If unavailable: document as known non-determinism source in CalibrationConfig.
**Why:** The CONTEXT specifies `--effort high` as evaluator reproducibility control, but effort controls reasoning depth, not sampling stochasticity. The debate protocol requires both evaluators to produce scores without anchoring effects — undetermined sampling temperature introduces noise that cannot be controlled or tracked in CalibrationConfig.
**How:**
1. Add to RESEARCH.md: "Verify `claude -p --temperature 0` or `CLAUDE_DEFAULT_TEMPERATURE=0` in v2.1.47. Test: run `claude -p "Return exactly: 42" --temperature 0` ten times, confirm identical outputs."
2. Based on result: update Plan 07 deliverables with `temperature: null` documentation. EVALUATOR_TEMPERATURE constant NOT created.
**Impacts:** Plan 07, Plan 12 (BaselineKey — no temperature field needed)
**Research needed:** no — RESOLVED 2026-02-23: Claude Code v2.1.50 has NO `--temperature` flag. Not in `--help`. No `CLAUDE_DEFAULT_TEMPERATURE` env var. Temperature is platform-controlled, not user-controllable. Document as known non-determinism source in CalibrationConfig. `--effort high` remains sole reproducibility control.
**Confidence:** HIGH
**Prior art:** 0
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** open
**Source:** Adversarial review (Technical Debt vs Premature Refactoring)
**Cross-references:** enhances P14-IMP-11
**Adversarial note (Technical Debt vs Premature Refactoring):** The evaluator debate protocol's validity depends on both evaluators running under identical conditions. Temperature is the most basic reproducibility control after effort. Unverified temperature state is a silent baseline corruption risk.

---

## Synthesis Items

### P14-SYN-01: Process/Outcome Boundary Enforcement Across All Touchpoints
**Target:** CONTEXT
**What:** Four items across three adversarial review groups independently tighten the same boundary -- the Grader Taxonomy separation between process evaluation (transcript graders) and outcome evaluation (detection graders) -- but at different enforcement points. P14-IMP-09 fixes rubric text, P14-IMP-16 fixes capability thresholds, P14-IMP-12 fixes the fallback protocol, and P14-ADV-3-01 adds FP visibility to EvaluationResult. No item proposes a unified validation that checks all touchpoints together. Without cross-cutting enforcement, each fix can be correctly implemented in isolation while a new outcome-metric leak appears at an uncovered touchpoint (e.g., Plan 12 Part 3 convergence detection using detection accuracy as a convergence signal, or a future improvement pass adding an outcome-derived dimension to `dimension_registry.yaml`).
**Why:** Addressing these as a unified concern is better than individual fixes because the boundary is enforced by convention (prose rules in CONTEXT.md), not by a machine-readable check. Each individual item adds its own grep-style check, but no single check covers the full boundary. A unified validation step at Plan 06 (contracts) and Plan 12 (improvement loop) entry points catches violations that slip between individual checks.
**How:**
1. Add Implementation Decision "Process/Outcome Boundary Enforcement": "The Grader Taxonomy separation is enforced at four touchpoints: (a) rubric text (P14-IMP-09 grep check), (b) capability contract fields (P14-IMP-16 prohibited fields), (c) fallback scoring protocol (P14-IMP-12 explicit exclusion), (d) EvaluationResult visibility (P14-ADV-3-01 DetectionSummary). Any new scoring dimension, contract field, or improvement loop criterion that references detection outcomes (findings_count, precision, recall, tp_count, fp_count) as a process-evaluation input MUST be flagged as an outcome metric and routed through the External Detection Validation path, not the reasoning evaluation path."
2. Plan 06 exit criterion addition: "Process/Outcome boundary audit: grep all 51 contracts for fields referencing detection outcomes used as capability gates or reasoning dimensions. Zero violations."
3. Plan 12 Part 2 startup check: "Verify no ExperimentLedgerEntry uses detection_accuracy as kill_criterion for a reasoning dimension improvement. Detection accuracy kill criteria are valid ONLY for External Detection Validation experiments."
**Impacts:** Plan 06, Plan 12
**Components:** P14-IMP-09, P14-IMP-12, P14-IMP-16, P14-ADV-3-01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (ADV Validation):** The synthesis consolidates four related items but frames them as enforcing one boundary when they enforce three distinct enforcement surfaces (rubric semantics, capability contract field restrictions, fallback metric exclusion) plus one transparency surface (FP visibility). The unified concern is "prevent detection outcomes from driving process evaluation decisions across four architectural surfaces" — each surface has its own validation check, coordinated but separate.
**Source:** Post-review synthesis (cross-cutting)

### P14-CSC-01: Scoring Quality Gate Fixtures Require Controlled Agent Runs, Not Fabrication
**Target:** CONTEXT
**What:** P14-IMP-14 (enhanced) specifies a "known-good vs known-bad transcript pair" as Plan 08 fixtures. The good transcript requires "agent performs >= 2 BSKG queries before reading any .sol file, uses node IDs in conclusion." The bad transcript requires "agent reads .sol directly, no BSKG queries." Creating these fixtures requires either (a) running real agents with deliberately constrained prompts to produce controlled behavior, or (b) fabricating transcripts -- which violates the "All Tests Use Synthetic Data" KCI lesson (fabricated data was already deleted in quality audit). The fixture creation method is unspecified, creating a gap where implementers default to fabrication.
**Why:** If fixtures are fabricated, the Scoring Quality Gate validates the pipeline against the implementer's assumptions about transcript structure -- the exact anti-pattern that P14-IMP-03 (confirmed) fixes for Plan 02. If fixtures are from controlled agent runs, they are real transcripts and satisfy both IMP-14 and the P0 data quality principle. But controlled runs require agent prompt variants that produce predictable good/bad behavior, which is itself an untested assumption at Plan 08 time.
**How:**
1. Add to P14-IMP-14's Plan 08 fixture specification: "Fixtures MUST be real agent transcripts, not fabricated JSONL. Source: run vrs-attacker on a simple corpus contract (e.g., reentrancy) twice: once with standard prompt (expected good), once with prompt modified to skip BSKG queries (expected bad). If both runs produce similar transcripts (agent ignores prompt constraint), the scoring quality gate is inconclusive -- log WARNING and proceed to Wave 6 with Gate 0 only."
2. Add to Plan 08 exit criterion: "Scoring Quality Gate fixtures sourced from real agent runs. Fixture provenance documented in `tests/workflow_harness/fixtures/scoring_quality_gate/README.md`."
**Impacts:** Plan 08
**Trigger:** P14-IMP-14
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 02 (real transcripts as baseline for fixture creation method)
**Classification:** structural
**Status:** enhanced
**Adversarial note (ADV Validation):** The How has two ambiguities: (1) "simple corpus contract" is undefined — should specify Plan 08 creates this fixture, not sourced from Plan 02. (2) The dependency on Plan 02 conflates sourcing existing transcripts vs. creating new ones via controlled agent runs. The bad fixture requires a deliberately-broken prompt run (Plan 08 activity), not a Plan 02 artifact. Drop the undefined "KCI lesson" reference; state clearly that fixtures must be real agent transcripts, not hand-written mocks.
**Source:** Post-review synthesis (cascade)

## Post-Review Synthesis
**Items created:** P14-SYN-01, P14-CSC-01
**Key insight:** The process/outcome boundary (Grader Taxonomy) is the most critical invariant in the 13.3% precision environment, yet it is enforced by convention across four independent touchpoints with no unified validation -- a unified enforcement decision prevents future leaks at uncovered touchpoints. The Scoring Quality Gate (IMP-14) opens a fixture provenance gap where fabrication would repeat the exact anti-pattern the phase has already paid to fix.