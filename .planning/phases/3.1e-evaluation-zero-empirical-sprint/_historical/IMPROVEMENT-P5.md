# Improvement Pass 5 — Phase 3.1e Evaluation Zero: Empirical Sprint

<!--
  pass:           5
  date:           2026-02-23
  prior_passes:   1, 2, 3, 4
  areas:          Measurement Foundation (Session 0 + Plan 01) |
                  LLM Evaluation Design (Plan 02) |
                  Downstream Experiments & Integration (Plans 03/04 + 05)
  agent_count:    3
  status:         in-progress
-->

**Pass:** 5
**Date:** 2026-02-23
**Prior passes:** 1, 2, 3, 4
**Areas covered:**
- Measurement Foundation (Session 0 + Plan 01)
- LLM Evaluation Design (Plan 02)
- Downstream Experiments & Integration (Plans 03/04 + 05)
**Agent count:** 3 (all present)
**Status:** complete

---

## Pipeline Status

| Stage | Symbol | Basis |
|-------|--------|-------|
| [discuss] | ✓ | CONTEXT.md exists, status = improved |
| [improve] | ✓ | imp_unreviewed = 0; confirmed = 9, enhanced = 23, reframed = 1, open = 0 |
| [pre-impl] | — | No prerequisite items |
| [research] | — | No research-needed items; gaps_active = 0 |
| [implement] | ~ | mergeable = 32; adv_unvalidated = 0 |
| [plan] | ✓ | Plans 01-05 defined in CONTEXT.md |
| [execute] | — | Plans not yet executed |

**Pipeline string:** `[discuss] ✓ [improve] ✓ [pre-impl] — [research] — [implement] ~ [plan] ✓ [execute] —`

**Stage counts (P5 items, post-synthesis):**
| Bucket | Count |
|--------|-------|
| prereqs_pending | 0 |
| prereqs_built | 0 |
| research_pending | 0 |
| research_done | 0 |
| gaps_active | 0 |
| gaps_disputed | 0 |
| imp_unreviewed | 0 |
| confirmed | 9 |
| enhanced | 23 |
| reframed | 1 |
| adv_unvalidated | 0 |
| mergeable | 32 |
| implemented | 0 |

---

## Adversarial Lenses

| Lens | Brief | Items | Attack Vector |
|------|-------|-------|---------------|
| Plan 01 Coherence | Five corrections to Session 0 pipeline assumptions — budget impact of collective overhead | P5-IMP-01, 02, 05, 06, 07 | If all five applied, does Session 0 still fit 25-30 min budget? |
| Plan 02 Coherence (go/no-go) | Go/no-go criterion unreachable as written — hypothesis duplication, kill switch, saturation | P5-IMP-09, 10, 11, 14 | After fixes, can Plan 02 still produce a genuine no-go? |
| Plan 02 Coherence (Calibration) | Calibration protocol redundancy, underspecification, orphaned requirements | P5-IMP-12, 13, 15 | Have simplifications hollowed out anti-circularity protection? |
| Cross-Plan Integration | Hidden data dependencies between plans assumed independent | P5-IMP-18, 19, 21, 22 | Does corrected critical path fit the 3.1e session budget? |
| Assumption Stress Test | Measurement constructs conflated across plans under shared labels | P5-IMP-03, 17, 20 | If reasoning_depth means different things in different layers, what does Plan 05 schema field mean? |
| Structural Gap Probe | Gates/constraints with undefined failure responses | P5-IMP-04, 16, 23 | Without fixes, does executor silently proceed, make local judgment, or halt? |
| Confidence Calibration | Structural item rated MEDIUM while cosmetic rated HIGH — confidence asymmetry | P5-IMP-05, 08 | Is MEDIUM confidence on IMP-05 genuine uncertainty or research gap? |

---

## Improvements

### P5-IMP-01: Session 0 task (a1) `fired_conditions` field does not exist in the pipeline output
**Target:** CONTEXT
**What:** Task (a1) specifies `{contract, pattern_id, function_name, is_tp, fired_conditions}` per finding. `fired_conditions` does not exist in `PatternEngine.run()` default output (lines 706-718). `build_lens_report()` never passes `explain=True`. `is_tp` requires a cross-reference join against the `CORPUS` ground truth from `test_detection_baseline.py` — this join is a scripting step, not a pipeline output. Without explicit guidance, the executor faces two failure modes: (a) spending time discovering missing fields, or (b) implementing the join incorrectly.
**Why:** The task description creates a false impression that the pipeline produces structured per-condition match data. Correcting it saves at most the field-discovery time. But if the correction adds a ground-truth join requirement without estimating that join's implementation cost, the time saving is illusory — the complexity moves, it does not disappear.
**How:**
1. In Session 0 task (a1), change the pipeline call to: "call `PatternEngine().run(graph, patterns, lens=DEFAULT_LENSES, limit=200, explain=True)` directly."
2. Add: "Extract `fired_conditions` from `finding['explain']` (structure: `{all: [...], any: [...], none: [...], edges: [...]}`)."
3. Add: "Compute `is_tp` by joining against the `CORPUS` dict in `test_detection_baseline.py`: for each finding, check if `(contract_label, node_label)` appears as a TP entry. Pre-write this join function before the session clock starts — include it in the pre-generated script template. This is a prerequisite script step, not in-session scripting."
4. Update the JSON schema to `{contract, pattern_id, function_name, node_id, is_tp, fired_conditions: {all, any, none, edges}}`.
5. Note explicitly: "baseline-before.json and baseline-after.json must use this identical schema (constraint from IMP-08)."
6. Add to Session 0 task (a1) time budget: "If joining against CORPUS during the session, add 10 min for join implementation. Recommended: pre-write join script in pre-flight."
**Impacts:** Session 0 task (a1) time budget; Plan 01 baseline-before.json structure
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — reading the source code; this is a factual correction
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 01 Coherence):** The improvement is correct in substance but under-specifies the implementation complexity of the `is_tp` join. By proposing a solution without estimating its cost, it gives the appearance of saving budget while displacing the complexity. The fix must either (a) pre-generate the join script as a pre-flight artifact, or (b) acknowledge that task (a1) expands to 35-40 min rather than 25-30 min when the full schema is required.

---

### P5-IMP-02: Session 0 task (a1) `build_lens_report()` has a `limit=50` default that silently truncates findings
**Target:** CONTEXT
**What:** Task (a1) says "run `build_lens_report()` directly" but the context also references `build_lens_report(graph, DEFAULT_LENSES, limit=200)` from `test_detection_baseline.py`. The function's default is `limit=50` (`report.py:16`). More critically, the limit is passed through to `PatternEngine.run()` which returns early at `len(findings) >= limit` (`patterns.py:719-720`). If the Session 0 standalone script calls `build_lens_report()` without `limit=200`, it will get a truncated finding set. The baseline will appear to have fewer FPs than the 3.1d-05 run, triggering a false "baseline deviation" flag. Worse: the limit applies GLOBALLY across all patterns and all contracts in a single graph build, not per-contract. If running 7 contracts through separate graph builds, each gets its own limit budget. If running all through one build (which the standalone script might do for efficiency), the 200 limit could still truncate.
**Why:** This is a concrete failure scenario: executor builds a standalone script, uses default limit, gets 50 findings, compares to 3.1d-05's 75+, flags >30% deviation, and wastes time diagnosing a non-issue. The context should make the limit requirement explicit and warn about the global-across-patterns behavior.
**How:**
1. In Session 0 task (a1), after "Build graphs via `VKGBuilder.build()`", add: "IMPORTANT: call pipeline with `limit=200` (matching 3.1d-05 test). The default `limit=50` silently truncates. Build and query each contract graph separately (7 builds, 7 queries) to avoid cross-contract limit exhaustion."
2. In Plan 01 Outcome A (reproducibility), note that "identical JSON" comparison must use the same limit value in both runs.
**Impacts:** Session 0 task (a1) correctness; Plan 01 Outcome A validity
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — direct code reading
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 01 Coherence):** This improvement is precise, verifiable, and low-overhead. It does not expand session budget — it prevents a specific failure mode. The 7-contract loop structure it implies is consistent with IMP-01's changes and should be noted as a joint constraint: "7 separate graph builds, each with PatternEngine().run(explain=True, limit=200)."

---

### P5-IMP-03: Plan 01 cost instrumentation `token_count` field is undefined for a non-LLM detection pipeline
**Target:** CONTEXT
**What:** cost-summary.json specifies `token_count` for Plan 01's LLM-free detection pipeline. The field has no meaningful value (always 0) and makes the Loop Economics formula unit-ambiguous — `cost_per_FP_removed` across plans will mix wall-clock and token units with no exchange rate.
**Why:** The Loop Economics formula is the primary input to 3.1f loop-closure decisions. If 3.1f receives a `cost_per_FP_removed` that silently blends incommensurable units, it cannot set a meaningful cost ceiling. The field ambiguity is not just cosmetic — it propagates to the 3.1f design as a hidden assumption that all plans share a common cost unit.
**How:**
1. In cost-summary.json field spec, replace `token_count` with `compute_seconds` (pipeline wall-clock excluding human time). Retain `wall_clock_seconds` for total elapsed.
2. Add a note to the Loop Economics Formula decision: "Plan 01 cost = compute_seconds (LLM-free). Plans 02, 03/04 cost = token_count + compute_seconds. For 3.1f cost-ceiling decisions, establish a token-to-second exchange rate based on Plan 02 observed data (tokens / compute_seconds on first LLM call). This rate converts Plan 02+ costs to a single unit for comparison with Plan 01."
3. In Plan 05 field-provenance, require a `cost_unit` annotation per schema field that references cost data, recording which unit system applies (compute_seconds | tokens | mixed). Flag `cost_per_FP_removed` at Plan 05 close if the rate has not been established.
**Impacts:** Plan 01 cost-summary.json schema; Loop Economics Formula decision; Plan 05 field-provenance
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — standard cost modeling practice
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Assumption Stress Test):** The improvement correctly identifies the unit ambiguity, but the proposed fix introduces its own assumption that the `cost_per_FP_removed` formula is purely additive across plan types. The Loop Economics formula will be computed across Plans 01-03/04, mixing compute-seconds (Plan 01) with token-cost (Plans 02, 03/04). When 3.1f consumes these numbers, it will encounter incommensurable cost units in the same formula unless an exchange rate is established. The rewrite adds this exchange-rate step and a cost_unit annotation in Plan 05 field-provenance.

---

### P5-IMP-04: Session 0 pre-flight checklist item 2 has no actionable failure mode
**Target:** CONTEXT
**What:** Pre-flight checklist item 2 proposes a gate on "fewer than 2 eligible dimensions," but this gate is impossible to trigger given actual source code: `_heuristic_dimension_score` contains 7 distinct non-default-30 handlers. The real structural gap is the absence of a TESTABILITY gate: all 7 handlers are count-based proxies (query count, tool count, sequence length). A pool of 7 is not useful if all 7 share the same root exploit mechanism.
**Why:** The pre-flight checklist was added (P4-ADV-8-01) specifically to catch precondition failures before the session clock starts. If the dimension pool is critically small (0-1 dimensions), Session 0 task (b) is blocked (can't write rubrics for 2 dimensions). The checklist must define the failure response.
**How:**
1. In pre-flight checklist item 2, add a two-part gate. Part A (count gate, as proposed): "if fewer than 2 eligible dimensions found: block Session 0 task (b). Escalate to 3.1c." Part B (testability gate, new): "For each eligible dimension, record the heuristic formula. If ALL eligible dimensions compute solely from count-based inputs: flag 'structural proxy homogeneity' — document as a Plan 02 design constraint. The executor must choose anchor designs where heuristic formula inputs are equalized across GOOD and MEDIOCRE, making the count-based limitation a feature of the test design, not a failure."
2. Add to the Eligible Dimension Pool decision: "The 7 non-default-30 dimensions found in `_heuristic_dimension_score` as of 3.1e are all count-based proxies. `reasoning_depth = min(100, 30 + unique_tools * 20)`. `evidence_quality = min(100, 40 + len(bskg_queries) * 15)`. Confirming this during pre-flight prevents wasted session time discovering it mid-execution."
3. Remove the escalation-to-3.1c clause for the `< 2 count` case only. Keep escalation as a last resort if the testability gate produces an unsolvable constraint.
**Impacts:** Session 0 entry gate; Plan 02 preconditions
**Research needed:** no
**Confidence:** MEDIUM — it is plausible that exactly 2 dimensions exist (reasoning_depth and evidence_quality are likely the only non-default-30 handlers), making this a realistic edge case
**Prior art:** 4 — standard pre-flight gate pattern
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Structural Gap Probe):** The original item identifies a real gap (no failure response) but proposes a gate condition that cannot fire given existing code (7 non-default-30 handlers exist, not 0-1). The actual structural risk is "dimension pool appears large yet all share the same exploit mechanism, making testability misleading." Without the testability gate, the pre-flight passes with 7 "eligible" dimensions, and only during Plan 02 execution does anyone discover that divergence test design depends on something the pre-flight should have confirmed: that heuristic formula inputs can be equalized between GOOD and MEDIOCRE.

---

### P5-IMP-05: Plan 01 Outcome A tests detection reproducibility but not graph construction reproducibility
**Target:** CONTEXT
**What:** Plan 01 Outcome A says "run `build_lens_report()` twice on the SAME pre-built graph, tests detection pipeline reproducibility (NOT graph building)." This explicitly excludes graph construction from reproducibility testing. But Session 0 task (a1) says "Build graphs via `VKGBuilder.build()`" — a fresh build. Plan 01 then also builds graphs. If `VKGBuilder.build()` is non-deterministic (e.g., property computation depends on Slither analysis order, or dictionary iteration order in Python 3.7+ is insertion-ordered but Slither's AST traversal order could vary), the SAME source code could produce DIFFERENT graphs across runs, and thus different findings, and Plan 01 would misattribute this to a "detection engine bug" when it is actually a graph construction bug.
**Why:** The context explicitly says "NOT graph building" for Outcome A, but this creates a blind spot. If Session 0 baseline and Plan 01 baseline use fresh graph builds and get different findings, the diagnostic pathway says "detection engine bug" when the real cause is graph non-determinism. The diagnostic should include graph-level comparison as a first step.
**How:**
1. In Plan 01 Outcome A, after "if output differs on same object, that is a detection engine bug — stop and diagnose", add: "If graph object IS the same (Python `id()` check), this is a pure detection bug. If different graph objects from the same source produce different findings, FIRST compare the graph objects (node count, edge count, property values on the firing function). If graphs differ, this is a graph construction reproducibility issue — route to Assumption 7 and flag for systematic BSKG audit."
2. In Session 0 task (a1), add: "After building each graph, record `{contract, node_count, edge_count}` as a graph fingerprint. Plan 01 uses this to verify graph construction determinism."
**Impacts:** Plan 01 Outcome A diagnostic accuracy; Assumption 7 scope
**Research needed:** no
**Confidence:** MEDIUM — Python dict ordering is deterministic since 3.7, and Slither's AST is likely deterministic, but property computation involves set operations that may not be order-stable
**Prior art:** 3 — standard reproducibility testing, but graph construction determinism is domain-specific
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Confidence Calibration):** REFRAME: replaced by P5-ADV-R-02 (graph fingerprint infrastructure already exists). The improvement's MEDIUM confidence is partially justified but aimed at the wrong target. `graph_fingerprint()` and `verify_determinism()` are already implemented and already called by `VKGBuilder.build()`. Proposing "add graph fingerprinting" as a Session 0 task suggests the author did not know the machinery exists — a research gap, not a design gap.

---

### P5-IMP-06: Plan 01 branch table has a gap for the case where Session 0 property diagnostic is partially correct
**Target:** CONTEXT
**What:** The Session 0 diagnostic branch table has two cases: (1) `has_access_gate=true` for emergencyExit — YAML fix viable; (2) `has_access_gate=false` for emergencyExit — Outcome B scope narrows. But Session 0 tests THREE functions (SelfiePool.emergencyExit, SideEntrance.withdraw, ReentrancyWithGuard.withdraw). What happens when `has_access_gate` is correct for some functions but not others? For example: emergencyExit=true (modifier recognized), but SideEntrance.withdraw=true when it should be false (withdraw has no access control in SideEntranceLenderPool — it is the vulnerable function). This would mean the builder OVER-reports access control, which would SUPPRESS FPs incorrectly (false negative risk on the FP-removal fix).
**Why:** The branch table assumes the diagnostic produces a clean binary signal. In practice, property correctness may vary by access-control mechanism (modifier vs require vs meta-transaction). A partially-correct property could cause Plan 01's YAML fix to suppress TPs, violating the zero-tolerance TP regression rule.
**How:**
1. In Plan 01 Session 0 diagnostic branch, add a third branch: "IF mixed correctness (has_access_gate correct for some functions, incorrect for others): the property is not reliable as an exclusion criterion. YAML fix must NOT use has_access_gate in the none: block as the primary exclusion mechanism for access-tierb-001. Redirect: use state_mutability=view/pure as the exclusion criterion for view/pure functions (NaiveReceiver.maxFlashLoan). For modifier-based FPs (where has_access_gate over-reports), route to Plan 03/04 as {builder-fixable: modifier-recognition}. Document: 'has_access_gate over-reporting confirmed; YAML-only fix for this class is not safe.'"
2. In Session 0 task (c), add: "For each of the 3 tested functions, record EXPECTED has_access_gate value: SelfiePool.emergencyExit (EXPECTED: true — onlyGovernance), SideEntrance.withdraw (EXPECTED: false — no access control), ReentrancyWithGuard.withdraw (EXPECTED: true — nonReentrant is not access control but note separately). If SideEntrance.withdraw has ACTUAL=true, flag as OVER-REPORTING. This is more dangerous than under-reporting for TP preservation."
3. Note: this third branch does NOT add to task (c) time but DOES change Plan 01 execution path if triggered.
**Impacts:** Plan 01 TP preservation guarantee; Session 0 diagnostic branch completeness
**Research needed:** no
**Confidence:** HIGH — partial correctness is the most likely real-world outcome
**Prior art:** 3 — standard diagnostic branching, but the specific property semantics are domain-specific
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 01 Coherence):** The original How contains a conceptual error: YAML pattern conditions cannot be restricted to specific functions. The corrected framing acknowledges that mixed correctness redirects the fix strategy (state_mutability instead of has_access_gate) rather than narrowing its application scope. This distinction matters for Plan 01 Outcome B feasibility.

---

### P5-IMP-07: Session 0 task (a2) annotation fields are undefined for non-access-tierb-001 FPs
**Target:** CONTEXT
**What:** Task (a2) says "For each FP in baseline-before.json, add `tier_a_matched` and `none_block_expected_but_missed` fields." These fields are meaningful for access-tierb-001 FPs (where we know which tier_a conditions fire and which none-block conditions should have blocked). But the baseline has 65 FPs across 12+ distinct patterns (ReentrancyWithGuard alone has 12 FPs from 12 different patterns). What do `tier_a_matched` and `none_block_expected_but_missed` mean for a reentrancy-basic FP on ReentrancyWithGuard? The fields are pattern-specific to access-tierb-001.
**Why:** If the executor annotates all 65 FPs with these fields, most annotations will be meaningless (e.g., `tier_a_matched: ["has_external_calls"]` for a reentrancy pattern where that IS the correct behavior, not a diagnostic finding). This wastes time and produces noise. The completion criterion already limits to Plan 01 primary contracts, but the task description says "for each FP" without restriction.
**How:**
1. In Session 0 task (a2), change "For each FP in baseline-before.json" to "For each access-tierb-001 FP in baseline-before.json." Non-access-tierb-001 FPs get a simplified annotation: `{pattern_id, function_name, contract}` only — no condition-level diagnostic.
2. Add: "Full FP diagnostic annotation across all patterns is Plan 03/04 Phase 0 territory, not Session 0."
**Impacts:** Session 0 task (a2) time budget; clarity of purpose
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — scoping annotation to the relevant subset
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 01 Coherence):** This improvement is correct, well-bounded, and its net effect is to recover approximately 10-14 minutes from task (a2) that can absorb the IMP-01 complexity overhead. The five-improvement set is roughly budget-neutral on Session 0 aggregate minutes only if the `is_tp` join script is pre-generated as a pre-flight artifact rather than implemented during the session.

---

### P5-IMP-08: Plan 01 "baseline-after.json" is not in the artifact manifest with minimum content spec
**Target:** CONTEXT
**What:** The artifact manifest lists `baseline-after.json` with minimum content "Per-function firings after YAML fix" but does not specify the JSON schema. Meanwhile, `baseline-before.json` has a detailed schema specified in task (a1): `{contract, pattern_id, function_name, is_tp, fired_conditions}`. The after-file must be structurally identical to the before-file for the comparison script to work, but this constraint is not stated.
**Why:** If the before and after files have different schemas (e.g., after-file omits `fired_conditions` because the executor considers it unnecessary post-fix), the comparison script breaks or produces misleading deltas. Schema consistency between paired before/after artifacts should be explicit.
**How:**
1. In the artifact manifest Plan 01 section, update `baseline-after.json` minimum content to: "Same schema as baseline-before.json (after IMP-01 correction): `{contract, pattern_id, function_name, node_id, is_tp, fired_conditions: {all: [...], any: [...], none: [...]}}`. Per-function firings after YAML fix. Must include all fields to enable element-wise delta computation."
2. In Plan 01 description, add: "Use the same recording script for both baseline-before.json and baseline-after.json. Delta computation: for each `(contract, pattern_id, function_name)` triple, compare `is_tp` field to identify TP-preserved / FP-removed / FP-remained / regression-introduced counts."
3. Add to artifact manifest Plan 01 section a new row: `comparison-script.py | .vrs/experiments/plan-01/comparison-script.py | Claude's discretion | Minimum: reads before and after JSON, outputs delta table with columns (contract, pattern_id, function_name, before_is_tp, after_is_tp, change: fp_removed|tp_preserved|regression|unchanged).`
**Impacts:** Plan 01 comparison script; Plan 05 field-provenance
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — standard paired-measurement practice
**Prerequisite:** no
**Depends on plans:** none
**Classification:** cosmetic
**Status:** implemented
**Adversarial note (Confidence Calibration):** HIGH confidence for a cosmetic fix is correctly calibrated — this is factual documentation correction with no design uncertainty. The enhancement adds the comparison script specification to prevent last-minute improvisation. Merge order dependency: IMP-01 must be applied before or simultaneously with IMP-08's manifest update to avoid a stale schema reference.

---

### P5-IMP-09: Divergence hypotheses (a) and (b) are the same hypothesis with different wording
**Target:** CONTEXT
**What:** Divergence hypotheses (a) and (b) are structurally duplicate — both assert "LLM correctly identifies GOOD > MEDIOCRE on reasoning_depth by recognizing causal chain quality, despite heuristic parity from equal unique_tool_count." With only 1 countable hypothesis and a 2/3 threshold, the go/no-go is structurally unreachable.
**Why:** The 2/3 threshold was set by prior passes to require multi-dimensional confirmation, specifically to prevent a single-dimension artifact from gating the entire investment decision. Without the fix, the threshold looks rigorous but is actually binary — exactly the binary framing that P2-IMP-10 rejected.
**How:**
1. Merge (a)+(b) into: "H1 (reasoning_depth, pair: GOOD vs MEDIOCRE): LLM identifies GOOD > MEDIOCRE on reasoning_depth despite heuristic parity (same unique_tool_count). Confirmed by: pairwise ordering GOOD wins AND LLM explanation cites causal chain quality, not tool count."
2. Promote a new H2: "H2 (evidence_quality, pair: GOOD vs MEDIOCRE): LLM identifies GOOD > MEDIOCRE on evidence_quality despite heuristic parity (same bskg_query_count). Confirmed by: pairwise ordering GOOD wins AND LLM explanation cites interpretation depth or result specificity, not query quantity."
3. Add H3: "H3 (either dimension, pair: BAD vs MEDIOCRE): LLM explanation for MEDIOCRE > BAD cites ABSENCE of evidence chain in BAD, not merely absence of graph queries. Tests whether LLM can discriminate semantic quality difference in the low-quality range."
4. Keep original (c) as sanity check only ("LLM does not score purely by citation count"), explicitly labeled: "sanity check — NOT counted in 2/3."
5. Update the go/no-go line to name hypotheses explicitly: "Confirmation: H1 AND H2 AND H3 independently pre-registered. 2/3 confirmed = go. 0/3 = no-go. 1/3 = ambiguous."
**Impacts:** Plan 02 go/no-go criterion becomes achievable. Without this fix, the 2/3 threshold is structurally unreachable (only 1 countable hypothesis + 1 sanity check).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — pre-registration methodology is established; applying it to LLM-as-judge divergence is novel
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 02 Coherence (go/no-go)):** The existing three-instrument model assumed three independently confirmable hypotheses. The CONTEXT currently delivers one. Second-order risk: if H1 and H2 both test GOOD-MEDIOCRE parity, they could co-fail for the same reason. H3 on a different pair provides genuine independence.

---

### P5-IMP-10: LLM call count makes 1-1.25 sessions infeasible without scope reduction
**Target:** CONTEXT
**What:** The minimum LLM call count for Plan 02 core is 28 calls (optimistic). The realistic call count is 40-46. At 30-90 seconds per call, pure wait time is 14-69 minutes. The session estimate of "Core = 1-1.25 sessions" does not account for anchor writing (~30 min), rubric drafting (~20 min), hallucination check (~12-15 min), pre-registration writing (~20 min), and calibration chain logging. If IMP-11 (majority-vote n=3) is also applied, the call count increases to 34-52.
**Why:** An infeasible estimate creates selection pressure against the most important steps. The most likely casualties are the hallucination check and pre-registration writing — precisely the steps that prevent confounded results.
**How:**
1. Revise Plan 02 "Session estimate" to: "Core = 2-2.5 sessions. Session A (anchor + rubric): ~70-85 min. Session B (calibration + scoring): ~90-140 min. Budget assumes 1-2 calibration rounds. 3 rounds = session overflow; accept best-version rubric at round 3."
2. Adjust Budget Recount decision: "Plan 02 core: 2-2.5 sessions (revised from 1-1.25). Critical path: Session 0 (1) → Plan 01 (1) → Plan 02 + Plan 03/04 Phases 0+1 in parallel (2-2.5) → Plan 03/04 Phase 2 (0.5-1) → Plan 05 (0.5) = 5-6 core sessions on critical path."
3. Add explicit scope reduction rule: "If Session B reaches 90 minutes with calibration incomplete: freeze at current rubric version, annotate 'calibration-incomplete,' proceed to scoring. Record round number where session was cut."
**Impacts:** Budget Recount decision (critical path: 4-4.75 -> 4.75-6 sessions). Plan 03/04 Phase 2 start date shifts if Plan 02 runs longer.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — session estimation from task decomposition is standard
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 02 Coherence (go/no-go)):** The original How offered two options: revise estimate OR reduce rounds. These are not equivalent. A scope reduction rule (pre-registered, not improvised) achieves both: honest time accounting AND a defined fallback. Cross-references: P5-IMP-11 (if majority-vote adopted, add 6 calls), P5-IMP-12 (if Step 0d removed, subtract 6 calls).

---

### P5-IMP-11: LLM_unreliable has asymmetric trigger sensitivity — n=2 pairwise flips are expected, not diagnostic
**Target:** CONTEXT
**What:** The non-determinism protocol marks a dimension LLM_unreliable if a pairwise winner flips across n=2 calls. The GOOD-MEDIOCRE pair is explicitly designed to be close. LLM-as-judge research documents 20-40% flip rates on close pairs. For a 3-pair test per dimension with n=2 per pair, the probability of at least one flip is ~0.66 under a 30% flip rate assumption. The kill switch, as designed, is not a reliability test — it is a difficulty test that most evaluators will fail on the GOOD-MEDIOCRE pair.
**Why:** The three-instrument model was built specifically to survive single-instrument noise. The LLM_unreliable kill switch short-circuits the entire model based on n=2 pairwise variance — a single-point-of-failure that the three-instrument design was supposed to prevent.
**How:**
1. Add pair-tier classification: "(a) GOOD-BAD: expected easy distinction. (b) MEDIOCRE-BAD: expected moderate distinction. (c) GOOD-MEDIOCRE: expected hard distinction — designed to be close."
2. Replace single flip criterion with tiered rule: "LLM_unreliable trigger: GOOD-BAD flip = strong evidence — mark LLM_unreliable. MEDIOCRE-BAD flip = moderate — record as 'marginal' but do not yet mark unreliable. GOOD-MEDIOCRE flip = 'close pair variance' — informative for 3.1c rubric tightening, NOT grounds for LLM_unreliable. LLM_unreliable requires: GOOD-BAD flip OR MEDIOCRE-BAD flip on both n=2 runs."
3. If budget allows, upgrade GOOD-BAD and MEDIOCRE-BAD to majority-vote n=3. Keep GOOD-MEDIOCRE at n=2.
4. In element-preregistration.json, add: "For each dimension, record which pair tiers produced flips."
**Impacts:** Plan 02 go/no-go becomes reachable. Without this fix, LLM_unreliable will likely fire on most dimensions, producing a systematic no-go bias.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — LLM-as-judge variance is well-documented (JudgeBench, LMSYS Arena), but applying majority-vote to security rubric scoring is novel
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 02 Coherence (go/no-go)):** The kill switch is correctly calibrated for EASY pairs (GOOD-BAD should be stable) but catastrophically miscalibrated for the HARD pair (GOOD-MEDIOCRE was designed to be hard). The tiered approach resolves this without weakening the kill switch where it matters. Cross-references: P5-IMP-09, P5-IMP-10, P4-ADV-3-01, P4-ADV-3-02.

---

### P5-IMP-12: Rubric freeze calibration and official scoring are redundant — calibration IS the measurement
**Target:** CONTEXT
**What:** The rubric freeze protocol has: Step 0b (calibrate — score all 3, revise up to 3 times), Step 0c (freeze), Step 0d (re-score all 3 with frozen rubric — "official scores"). Re-scoring the same 3 anchors with the same rubric is expected to produce similar results (assuming LLM consistency, which is separately tested by the non-determinism protocol). Step 0d adds 6 LLM calls (3 anchors x 2 dimensions) that provide almost no new information beyond what calibration already showed.
**Why:** Step 0d exists to prevent the rubric from being tuned to produce desired scores (anti-circularity). But the held-out anchor (Step 0d also scores the held-out) already serves this purpose — the held-out was never seen during calibration. The calibration anchors were seen, so re-scoring them is not an independence test. The real anti-circularity protection is the held-out, not Step 0d's re-score of calibration anchors.
**How:** Remove "remove Step 0d re-scoring of calibration anchors" as the primary action. Replace with: "In the rubric freeze protocol, clarify that Step 0c (freeze, record SHA256) must occur IMMEDIATELY after the successful calibration round with zero edits to rubric text. The final calibration-round scores ARE the official scores under the frozen rubric. Step 0d absolute re-scores of calibration anchors are then redundant and may be removed. If any cleanup edits occur post-calibration, Step 0d re-score is required to establish official scores under the final rubric text. Add to Step 0c: 'No edits permitted after SHA256 recording. Post-freeze corrections create v1.1 and require full re-calibration.'"
**Impacts:** Plan 02 session estimate reduced. Calibration chain logging still captures all scores (calibration rounds + held-out).
**Research needed:** no
**Confidence:** MEDIUM — there is a valid argument that re-scoring tests rubric stability (same rubric, same anchor, different LLM run = same score?), but this is already tested by the non-determinism protocol on pairwise comparisons.
**Prior art:** 4 — calibration vs. validation split is standard psychometrics
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 02 Coherence (Calibration)):** The item misidentifies Step 0d's purpose for calibration anchors. Step 0d's re-score serves a distinct function from the non-determinism protocol. The How (use final calibration-round scores as official) is valid ONLY IF the rubric is frozen atomically — no edits between the successful calibration call and SHA256 recording. The How must add this constraint explicitly or the measurement gap remains. Cross-references: IMP-10 (complementary — saves calls IMP-10 budgets for), IMP-11 (together they reduce total anti-circularity protection — see P5-ADV-R-05).

---

### P5-IMP-13: Hallucination check is underspecified — "verify it corresponds to a real element" requires a methodology
**Target:** CONTEXT
**What:** "After official scoring: Run hallucination check: for each LLM evidence string, verify it corresponds to a real element of the scored anchor. If evidence cites transcript features that DO NOT EXIST: dimension is LLM_unreliable." The anchors are hand-written synthetic transcripts. "Verify it corresponds" requires comparing LLM evidence strings against anchor content. With 3 anchors x 2 dimensions x (pairwise explanations + absolute explanations), this is 12+ evidence lists to manually cross-reference. There is no definition of what counts as a "real element" vs. a paraphrase, inference, or interpretation.
**Why:** Without a methodology, this check will either be perfunctory (skim and approve) or paralyzing (debate every paraphrase). Either outcome undermines the check's purpose. More critically: if the LLM says "the agent traced the CEI pattern through node 0x42" and the anchor contains "queried BSKG for node 0x42 re: CEI violation," is that hallucination or accurate citation? The boundary matters because it determines LLM_unreliable classification.
**How:**
1. In the "After official scoring" paragraph, add a concrete hallucination taxonomy: "(a) Fabricated feature: LLM cites a tool call, query, or finding that does not appear anywhere in the anchor transcript. (b) Fabricated detail: LLM cites a correct feature but invents a specific detail (e.g., names a node ID not present). (c) Interpretive paraphrase: LLM describes a feature using different words but the referent exists. Classification: (a) = hallucination (triggers LLM_unreliable). (b) = hallucination. (c) = not hallucination."
2. Add a practical constraint: "For each dimension, sample the 3 strongest evidence claims from the LLM. Cross-reference against anchor content. If >= 1 is type (a) or (b): dimension is LLM_unreliable. Record all checked claims in the calibration chain log."
3. This scopes the check to ~12 evidence claims total (3 per dimension x 2 dimensions x 2 for pairwise/absolute) rather than exhaustive review of all evidence strings.
**Impacts:** Plan 02 hallucination check becomes executable within session time.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — hallucination detection in LLM-as-judge is actively researched but no standard taxonomy exists for this specific use case
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 02 Coherence (Calibration)):** This item withstands scrutiny. The three-category taxonomy correctly separates fabrication (both types) from legitimate paraphrase, and the sampling bound makes the check feasible within the session. One gap not addressed but not a reason to ENHANCE: the taxonomy does not cover "severity inflation" — LLM cites a real feature but inflates its significance. For this phase's scope (is the LLM citing things that exist?) the taxonomy is adequate. The severity inflation question belongs to 3.1c.

---

### P5-IMP-14: evidence_quality heuristic formula creates a different divergence structure than reasoning_depth
**Target:** CONTEXT
**What:** The MEDIOCRE anchor design constraints specify: "(a) unique_tool_count = GOOD_unique_tool_count (to produce heuristic parity on reasoning_depth), (b) bskg_query_count = GOOD_bskg_query_count." The reasoning_depth formula is `min(100, 30 + unique_tools * 20)` — controlled by unique_tool_count. The evidence_quality formula is `min(100, 40 + len(bskg_queries) * 15)` — controlled by bskg_query_count. Both are equalized between GOOD and MEDIOCRE. But the formulas saturate at different points: reasoning_depth hits 100 at unique_tools=4 (min(100, 30+80)=100); evidence_quality hits 100 at bskg_queries=4 (min(100, 40+60)=100). If anchors use >= 4 of either, BOTH hit 100, and there is zero room for heuristic variation — the test is trivially confirmed because the heuristic literally cannot score them differently regardless of content.
**Why:** The anchor design must ensure tool/query counts stay below saturation. This is not stated anywhere. An implementer who writes GOOD with 5 tool calls and 5 BSKG queries will produce heuristic scores of (100, 100) for both GOOD and MEDIOCRE, trivially confirming the divergence hypotheses without any LLM discrimination being tested.
**How:**
1. In the "Wiring order" paragraph, step (3) anchor design, add: "Anchor unique_tool_count MUST be <= 3 AND bskg_query_count MUST be <= 3, to keep heuristic scores below formula saturation (100). At 3 unique tools: reasoning_depth = 90; at 3 BSKG queries: evidence_quality = 85. This leaves room for the heuristic to differentiate if anchor content changes, ensuring the divergence test is non-trivial."
2. In the divergence hypotheses paragraph, add after hypothesis (b): "Validity prerequisite: heuristic scores for GOOD and MEDIOCRE must be BELOW 100 on the tested dimension. If both are 100 (formula saturation), the hypothesis is trivially confirmed and does not count toward go/no-go."
**Impacts:** Prevents false confirmation of divergence hypotheses. Makes anchor design constraints complete.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — ceiling effects in measurement instruments are well-known
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 02 Coherence (go/no-go)):** This item withstands lens scrutiny. The saturation guard (counts <= 3) is necessary and sufficient to prevent trivial confirmation. Under the holistic analysis, IMP-14 is the item that prevents a particular class of false-go: saturation-enabled trivial confirmation. One addition would strengthen IMP-14: specify that the validity prerequisite check happens at anchor-design time (before LLM scoring), not at scoring time, to avoid wasting calls on a saturated anchor. However, this is a sequencing detail that does not change structural correctness — CONFIRM is appropriate.

---

### P5-IMP-15: The "two-variant test on evidence_quality" for rubric style recommendation is never defined
**Target:** CONTEXT
**What:** Plan 02 deliverables include: "Rubric style recommendation (generic vs security-chain) based on two-variant test on evidence_quality." This two-variant test is mentioned in the deliverables line but never appears in the wiring order, the rubric freeze protocol, the divergence hypotheses, or anywhere else in Plan 02's detailed specification. There is no description of what the two variants ARE, when they are administered, or how results inform the recommendation.
**Why:** Either this is a deliverable that was specified early and never wired into the detailed protocol (an orphaned requirement), or it was absorbed into another mechanism without updating the deliverables line. Either way, an unspecified deliverable in a plan with MEDIUM confidence is a scope risk — someone will either try to improvise it during execution (adding unbudgeted time) or silently drop it.
**How:**
- Option 2 (recommended fallback): Remove the "based on two-variant test on evidence_quality" clause from the deliverables line. Replace with "based on calibration round observations — which rubric vocabulary produced the required GOOD>MED>BAD ordering."
- Option 3 (recommended primary): Defer the two-variant test to Plan 03/04 Phase 2 as an additional column in the validity matrix. Phase 2 already runs LLM scoring with the Plan 02 rubric — adding a generic-rubric variant as a parallel column costs ~3 calls and provides the controlled comparison without adding to Plan 02's already overloaded session budget.
**Impacts:** Plan 02 session estimate (if option 1) or Plan 02 deliverables line (if option 2). Either way, removes an unimplemented commitment.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — variant testing in rubric design is standard educational measurement
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 02 Coherence (Calibration)):** The How presents only two options when a third (delegate to Plan 03/04 Phase 2) is materially better. Option 2 ("based on calibration round observations") is epistemically weak — a single rubric calibrated through revision will converge on whatever vocabulary the author initially used. The research question "does security-chain vocabulary outperform generic vocabulary for rubric discrimination?" is valuable for 3.1c rubric design and should not be dropped silently. Option 3 should be the recommended option; Option 2 is the fallback if Plan 03/04 is already overloaded.

---

### P5-IMP-16: Plan 03/04 Phase 1 code-path enumeration will discover far more than 8 exploitable paths
**Target:** CONTEXT
**What:** The "max 8" cap is the right direction, but "max 8 mechanism clusters" miscalibrates expected output. Reading `_heuristic_dimension_score`, `_evaluate_capabilities`, and `GraphValueScorer` directly: there are approximately 5-6 distinct exploit mechanisms — (1) count-inflation on len(bskg_queries) or len(tool_seq); (2) unique-tool-count saturation (set()); (3) early-position presence check (Bash in tool_seq[:3]); (4) binary presence checks (has_queries and has_response); (5) regex citation detection (GVS path); (6) keyword matching in response_text. "Max 8 mechanism clusters" provides no guidance for scope-constrained execution without a priority ordering.
**Why:** Without a selection criterion, the executor will either (a) hit the cap early and miss the most interesting exploits, or (b) spend time deciding which 8 to keep. The cap should be tied to exploitability severity, not an arbitrary number. More importantly, many of these code paths share the same fundamental exploit mechanism (count-based scoring) — the real number of distinct gaming strategies is likely 4-6, not 20. The enumeration should cluster code paths by exploit mechanism, then generate one transcript per mechanism cluster.
**How:**
1. In Plan 03/04 Phase 1, replace "Min 3 exploitable paths, max 8" with: "Enumerate heuristic scoring code paths. Cluster by exploit mechanism. Expected clusters from current code: (1) count-inflation, (2) unique-tool saturation, (3) position-based presence, (4) binary-presence, (5) regex citation detection (GVS), (6) keyword matching. Generate one adversarial transcript per cluster. Minimum: 3 clusters. Maximum: 6 (current code) + LLM-Flatterer (hand-crafted, not mechanism-derived)."
2. Add priority ordering for scope-constrained execution: "(1) count-inflation (most impactful — covers evidence_quality and reasoning_depth simultaneously), (2) regex citation detection (known exploit in GVS), (3) position-based presence, (4) unique-tool saturation, (5) binary-presence, (6) keyword matching. LLM-Flatterer is mandatory regardless of time pressure."
3. Update `archetype-count.json` schema: add `mechanism_cluster` (which of the 5-6 types), `coverage_complete` (boolean), and `skipped_clusters` (list).
4. Add: "Heuristic-gaming archetypes are mechanism-cluster-derived. LLM-evaluator-gaming archetypes (e.g., LLM-Flatterer) are hand-crafted and tracked separately under `llm_gaming_archetypes`."
**Impacts:** Plan 03/04 Phase 1 session estimate unchanged (clustering is a <10 min analysis step). archetype-count.json records mechanism clusters, not raw code paths.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — exploit categorization by mechanism is standard in security testing
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Structural Gap Probe):** The original improvement solves the right problem with the right framing. The rewrite grounds the mechanism count in actual source code (5-6, not "up to 8"), adds priority ordering for scope-constrained execution, and separates heuristic-gaming from LLM-evaluator-gaming archetypes. Second-order effect on Phase 2: N is now 6-7, so go_threshold_used = ceil(6/2) = 3 or ceil(7/2) = 4 — stricter than the go_threshold for N=3. The reframe tightens the go criterion appropriately.

---

### P5-IMP-17: Plan 03/04 Phase 2 validity coefficient has a construct validity problem — heuristic and LLM measure different constructs
**Target:** CONTEXT
**What:** Phase 2 computes Spearman rho between heuristic and LLM scores per dimension, labeling the result "heuristic validity." The heuristic `reasoning_depth` formula (`min(100, 30 + unique_tools * 20)`) measures tool diversity; the LLM rubric measures causal chain quality. These are different constructs under the same dimension name. The resulting Spearman rho is not a validity coefficient — it is a construct-divergence measurement. The conflation propagates to Plan 05: any schema field named `reasoning_depth` will silently inherit construct ambiguity into 3.1c design.
**Why:** 3.1c will consume Plan 05 schemas as design input. If `reasoning_depth` in the schema can mean tool-diversity OR causal-chain-quality depending on which layer generated the score, the 3.1c evaluator design will be built on a silently ambiguous foundation.
**How:**
1. In Phase 2, after the validity coefficient definition, add: "Interpretation framework for construct-mismatched proxies: (a) rank-correlation high AND false-negative rate at threshold acceptable — heuristic is a valid pre-filter; (b) rank-correlation near zero — heuristic rank-ordering is random; (c) rank-correlation negative — heuristic is actively counter-productive. Cases (b) and (c) warrant discarding. Case (a) warrants keeping with explicit notation that it pre-filters on tool-diversity AS A PROXY for causal chain quality, not on causal chain quality directly."
2. In validity-matrix.json required fields, add `construct_alignment_note` per dimension: what the heuristic formula actually measures vs what the LLM rubric asks.
3. In Plan 05 Unobserved Phenomena routing, add: "If any dimension has `construct_alignment_note` showing heuristic and LLM measure different constructs, add a 3.1c-targeted phenomenon: 'construct disambiguation: schema field {dimension} must declare which construct it captures per evaluation layer.' Tag this phenomenon `measurement_difficulty: trivial, target: 3.1c`."
**Impacts:** Plan 03/04 Phase 2 decision framework becomes more nuanced. Plan 05 Unobserved Phenomena may gain a "construct alignment" item if the mismatch is severe.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — construct validity is well-understood in psychometrics but applying it to automated code evaluator vs LLM judge comparison is novel
**Prerequisite:** no
**Depends on plans:** Plan 02 (rubric freeze provides the LLM construct definition)
**Classification:** structural
**Status:** implemented
**Adversarial note (Assumption Stress Test):** The improvement is correct that the constructs diverge, but it understates a second-order consequence. The lens brief explicitly names: if 'reasoning_depth' means tool diversity in heuristic and causal chain quality in LLM, what does Plan 05's schema field actually mean? The improvement's How addresses interpretation but not the downstream schema consequence. IMP-17 must be implemented together with P5-ADV-R-01 (schema naming) to close the loop — IMP-17 fixes the measurement record without fixing the downstream artifact.

---

### P5-IMP-18: Plan 05 integration smoke test is positioned too late to influence Plan 02 {observed} design
**Target:** CONTEXT
**What:** Plan 05's integration smoke test ("feed Plan 01 per-function detection output as {observed} content in Plan 02 rubric") runs AFTER Plan 02 completes. But the {observed} field design is frozen during Plan 02 Step 2 of the wiring order. If the smoke test reveals that detection JSON is uninterpretable by the LLM, that finding cannot retroactively fix Plan 02's {observed} spec. The smoke test discovers a problem that can no longer be acted on within 3.1e.
**Why:** The smoke test's stated purpose is to "reveal a format gap." But the gap it reveals is between Plan 01 output format and Plan 02 {observed} format — and both are already frozen by the time Plan 05 runs. Moving a lightweight version of this test earlier (during Plan 02 {observed} design) would let the format gap influence the design rather than just documenting it.
**How:**
1. In Plan 02 wiring order, after "Define `{observed}` spec — must contain content requiring semantic interpretation," add: "Feasibility check: take the SideEntranceLenderPool access-tierb-001 FP from baseline-before.json. Attempt to include one detection firing record as supplementary evidence in the `{observed}` field. Can a human reading only `{observed}` excerpts understand what the detection result means? If no: document the minimum transformation needed. This takes <= 5 minutes and sets format direction for Plan 05."
2. In Plan 05, update the smoke test description: "Extends the Plan 02 feasibility check from step 2: systematic coverage of all Plan 01 output fields, one contract from each Phase 0 taxonomy cluster. The Plan 02 check established format direction; Plan 05 confirms it holds across the full output space."
3. In Plan 05 pre-registration, add to success criteria: "(d) If smoke test conflicts with step-2 feasibility check conclusion, document the contradiction explicitly — this is a scope item for 3.1c, not a Plan 05 failure."
**Impacts:** Plan 02 session estimate increases by ~5 minutes. Plan 05 smoke test shifts from "pure discovery" to "validation of a known direction." Reduces risk of Plan 05 finding a format gap that requires Plan 02 redesign.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — early integration testing is standard practice
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Cross-Plan Integration):** The original item is correct but the How stops short of making the step-2 feasibility check mandatory vs optional. The rewrite adds: (a) a concrete description of what the check does, (b) a time bound (5 minutes), (c) an explicit requirement that Plan 05 characterize whether its findings agree or disagree with the step-2 direction. Without (c), Plan 05 could produce a smoke test result that silently contradicts the step-2 check.

---

### P5-IMP-19: Plan 03/04 Phase 0 taxonomy operates on 65 FPs but Plan 01 will change the FP count
**Target:** CONTEXT
**What:** Phase 0 says "Two-pass LLM taxonomy on 65 FPs." Phase 0 "runs immediately, no Plan 01/02 dependency." But Plan 01 is designed to remove FPs via the access-tierb-001 fix. If Phase 0 runs before Plan 01, it taxonomizes FPs that Plan 01 will then remove. If Phase 0 runs after Plan 01, the 65-FP number is stale. The context says Phase 0 requires "only baseline data" but does not specify which baseline — before-fix or after-fix.
**Why:** This matters because the taxonomy's purpose includes fix-cost classification (Phase 0 Pass 2 action mapping: YAML-fixable, builder-fixable, etc.). If Phase 0 runs on pre-fix data, some FPs classified as "YAML-fixable" will have already been fixed by Plan 01. The action_map becomes partially obsolete before Phase 1 even starts. If Phase 0 runs on post-fix data, the FP count may be significantly smaller (Plan 01 targets 18+ access-tierb-001 FPs), reducing taxonomy diversity.
**How:**
1. In Phase 0 description, first paragraph: add "Phase 0 operates on baseline-before.json (pre-fix data, from Session 0 task a1). The 65 FP count is the pre-fix baseline. Fixing FPs during Plan 01 does not invalidate the taxonomy — it enriches the action_map with confirmation data."
2. In Phase 0 exit artifact minimum content, update action_map.json schema: "Per-cluster: action_category, scope_tag, and `addressed_count` (integer if Plan 01 complete at Phase 0 close, else string 'pending-plan-01'). Field may be updated post-Plan-01 without re-running Phase 0."
3. In the artifact manifest, annotate action_map.json: "Phase 0 produced. addressed_count field may be updated after Plan 01 completes — this is expected, not a re-run of Phase 0."
**Impacts:** Plan 05 Unobserved Phenomena list will be more accurate because it can distinguish "addressed FP categories" from "remaining FP categories."
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — standard before/after experimental design
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Cross-Plan Integration):** The original item is correct on the core problem (pre-fix vs post-fix baseline ambiguity) but misses the parallelism timing issue that makes `addressed_count` inherently deferred. The rewrite adds the parallel-execution case where Phase 0 exits before Plan 01 completes, making the field schema need to support a "pending" state. Without this, the artifact schema is technically incorrect for the parallel execution path that Budget Recount explicitly allows.

---

### P5-IMP-20: Plan 05 Unobserved Phenomena routing has no mechanism for cross-area conflict detection
**Target:** CONTEXT
**What:** Plan 05 has no mechanism to detect when upstream plans produce findings with contradictory implications for the same downstream design decision. Without this, Plan 05 functions as a collection point, not a synthesis point, and 3.1c receives incoherent design input.
**Why:** Three structurally predictable contradiction pairs exist: (1) Plan 02 LLM_adds_signal vs Plan 03/04 validity coefficient; (2) Plan 01 YAML-fix-sufficient vs Plan 03/04 Phase 0 builder-fix-required for the same FP cluster; (3) Plan 02 rubric-calibration-succeeded vs Plan 03/04 Phase 2 rubric-uncalibrated annotation.
**How:**
1. In Plan 05, add a "Pre-specified contradiction pairs" section listing the three pairs above with their source plans and the design decision they affect. Check each pair explicitly before routing phenomena. Estimate: 10-15 minute structured check.
2. For each contradiction found, document: (a) Finding A (source: plan, artifact, quote), (b) Finding B (source: plan, artifact, quote), (c) Whether the contradiction is resolvable from data, (d) If irresolvable: "Arbitration required by 3.1c: [specific decision question]."
3. In Plan 05 pre-registration success criteria, add: "(d) each pre-specified contradiction pair has been explicitly checked and either resolved or documented as an arbitration question for 3.1c with data on both sides."
**Impacts:** Plan 05 session estimate may increase by 10-15 minutes for contradiction analysis. 3.1c receives cleaner input.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3 — systematic review methodology includes contradiction detection
**Prerequisite:** no
**Depends on plans:** Plan 01 (detection data), Plan 02 (LLM evaluation data), Plan 03/04 (taxonomy + validity data)
**Classification:** structural
**Status:** implemented
**Adversarial note (Assumption Stress Test):** The improvement identifies the symptom correctly but the How is underspecified. "Scan all phenomena for pairs with contradictory implications" relies on the executor to recognize semantic relationships between findings from different plans using different measurement instruments. Without pre-specified contradiction PAIRS TO WATCH FOR, the check degrades to an informal scan. The three pre-specified pairs should be enumerated in the CONTEXT Decisions section, not buried in the Plan 05 description.

---

### P5-IMP-21: Degradation rules create a path where Plan 05 receives INCONCLUSIVE from Phase 2 but must still produce schemas
**Target:** CONTEXT
**What:** The compound degradation rule says "Both degrade: Phase 2 produces INCONCLUSIVE." Plan 05 Track A says "always available: detection schemas from Plans 01 + 03/04 data." But if Phase 2 is INCONCLUSIVE, Plan 05 still needs to decide what to do with the partial Phase 0 and Phase 1 artifacts. The taxonomy (Phase 0) and archetypes (Phase 1) exist but lack validity assessment. The current "Plans 01 + 03/04 data" reference conflates detection-relevant and evaluation-relevant artifacts: only Phase 0 action_map directly feeds schema design; Phases 1-2 feed evaluation assessment.
**Why:** The current design implies Plan 05 Track A uses Plan 03/04 data for detection schemas, but the only Plan 03/04 artifact relevant to detection schemas is Phase 0's action_map (fix-cost classification). Phases 1-2 are about evaluator validity, which feeds Track B. The "Plans 01 + 03/04 data" reference conflates detection-relevant and evaluation-relevant artifacts.
**How:**
1. In Plan 05 Track A, clarify: "detection schemas from Plan 01 (per-function firings, cost data) + Plan 03/04 Phase 0 (taxonomy categories, action_map fix-cost classification)."
2. In Plan 05 Track B, clarify: "evaluation schemas from Plan 02 (per-dimension matrix) + Plan 03/04 Phases 1-2 (validity coefficient, gameability matrix). If Phase 2 INCONCLUSIVE: Track B evaluation schemas annotated 'validity-unassessed.'"
3. This is a clarification of existing intent, not a scope change, but prevents the executor from being confused about which upstream artifacts feed which track.
**Impacts:** No session estimate change. Reduces ambiguity during Plan 05 execution.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — standard data lineage documentation
**Prerequisite:** no
**Depends on plans:** none
**Classification:** cosmetic
**Status:** implemented
**Adversarial note (Cross-Plan Integration):** Item withstands scrutiny. The INCONCLUSIVE degradation path is already handled: Plan 05 preconditions say "If Phase 2 INCONCLUSIVE, Unobserved Phenomena includes 'heuristic validity: requires-infrastructure, target: 3.1c'." The Track A/B clarification prevents a secondary confusion where an executor, seeing INCONCLUSIVE from Phase 2, misreads Track A as also requiring Phases 1-2 data. The cosmetic classification is correct.

---

### P5-IMP-22: Plan 03/04 Phase 1 quality gate creates a paradox — LLM scoring gaming transcripts requires Plan 02 rubric, but Phase 1 runs in parallel with Plan 02
**Target:** CONTEXT
**What:** Phase 1 quality gate requires LLM scoring of gaming transcripts using the Plan 02 frozen rubric. But Phase 1 runs in parallel with Plan 02, meaning the rubric is not frozen when Phase 1 generates transcripts. The resolution is to split Phase 1 into two stages: (a) transcript generation (genuinely parallel with Plan 02) and (b) quality gate evaluation (sequential after Plan 02 rubric freeze).
**Why:** The current text implies Phase 1 is complete before Plan 02 finishes, allowing Phase 2 to start immediately after Plan 02 freeze. But if the quality gate fires, hand-crafting 2 harder transcripts adds time to Phase 1 AFTER Plan 02 freeze — extending the critical path. The current critical path estimate (4-4.75 sessions) does not account for this potential extension.
**How:**
1. In Phase 1 description, split the quality gate: "Transcript generation: runs in parallel with Plan 02. Quality gate evaluation: runs after Plan 02 rubric freeze, using frozen rubric for LLM scoring. If gate fires: hand-craft 2 harder transcripts (additional time: ~30 min). archetype-count.json is not finalized until quality gate evaluation completes."
2. In the Budget Recount decision, add: "Phase 1 transcript generation is parallel with Plan 02. Phase 1 quality gate evaluation is sequential AFTER Plan 02 freeze. If gate fires, add ~30 min buffer before Phase 2 can start. Critical path: Plan 02 freeze → Phase 1 gate evaluation (0-30 min) → Phase 2."
3. In the Phase Exit Artifacts table, annotate Phase 1 archetype-count.json: "Finalized after quality gate evaluation (requires Plan 02 rubric freeze). Transcript files exist earlier — only count and model-tier fields are gated."
4. Do NOT remove "AND LLM >= 70" from the quality gate.
**Impacts:** Critical path may extend slightly. Budget Recount should note this partial dependency. Plan 03/04 session estimate unchanged (transcript generation is the bulk of the work).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — dependency analysis is standard project management
**Prerequisite:** no
**Depends on plans:** Plan 02 (rubric freeze)
**Classification:** structural
**Status:** implemented
**Adversarial note (Cross-Plan Integration):** The original item correctly identifies the dependency but understates the downstream consequence: if the quality gate fires, the critical path is not zero — it is 30 minutes of hand-crafting. Cross-group interaction: IMP-10 (Plan 02 session estimate: 1-1.25 → 2-2.5 sessions) and IMP-22 compound — see P5-ADV-R-03.

---

### P5-IMP-23: Plan 05 field-provenance for verdict fields assumes verdict_conditions are stable, but N is experiment-dependent
**Target:** CONTEXT
**What:** Plan 05 pre-registration says "For verdict-type fields, field-provenance includes `verdict_conditions` — the N and threshold under which the verdict was produced." The N in Plan 03/04 Phase 2 comes from archetype-count.json (Phase 1 exit artifact). The threshold is ceil(N/2). But N is not known until Phase 1 completes. If Plan 05 starts schema extraction before Phase 1 is fully complete (allowed by preconditions: "Plan 03/04 Phase 0 exit artifacts exist (minimum)"), the verdict_conditions cannot be recorded because N is unknown.
**Why:** This is not a blocking issue but a documentation gap. The current preconditions allow Plan 05 to start with only Phase 0 artifacts, but verdict_conditions require Phase 1+ data. The field-provenance will have gaps that are not explicitly called out as expected gaps.
**How:**
1. In Plan 05 pre-registration, add: "Verdict-type fields whose verdict_conditions depend on Plan 03/04 Phase 1+ artifacts: annotate as 'verdict_conditions: pending-phase-{N}' if those artifacts do not yet exist at Plan 05 execution time. Update field-provenance.md when artifacts become available. If Plan 05 closes before Phase 2: these fields remain annotated 'pending' — this is an expected state, not a failure."
**Impacts:** No session estimate change. Prevents false "failure" classification when Plan 05 runs on partial upstream data.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4 — incremental documentation is standard
**Prerequisite:** no
**Depends on plans:** Plan 03/04 Phase 1 (archetype-count.json)
**Classification:** cosmetic
**Status:** implemented
**Adversarial note (Structural Gap Probe):** This improvement withstands scrutiny under the structural gap lens. The failure mode is correctly diagnosed. One second-order effect: the annotation pattern should be extended to Plan 05 pre-registration success criterion (b) — "a field-provenance annotation exists for every schema field" — because without the pending-state exception, criterion (b) would fail by definition when Plan 05 runs before Phase 2 completes. The improvement implicitly handles this, but criterion (b) should explicitly say "pending-phase-N annotations count as fulfilling this criterion."

---

### P5-ADV-R-01: Plan 05 schema field naming must declare construct per evaluation layer
**Target:** CONTEXT
**What:** When Plan 05 extracts Pydantic schemas, it will name fields after evaluation dimensions (e.g., `reasoning_depth`, `evidence_quality`, `cost_per_FP_removed`). Dimension names are overloaded: `reasoning_depth` means tool diversity at the heuristic layer and causal chain quality at the LLM layer. In IMP-03, `cost_per_FP_removed` mixes compute-seconds and tokens without a declared unit. No schema field naming constraint prevents these conflations from being encoded into 3.1c infrastructure as permanent assumptions.
**Why:** 3.1c is where the production evaluation infrastructure gets built. If it receives Plan 05 schemas with ambiguous field names (same name, different construct per layer), it will either (a) build unified fields that silently conflate measurements, or (b) discover the ambiguity mid-implementation and have to redesign. Option (b) requires re-running Plan 05 analysis, which is not in scope.
**How:**
1. In Plan 05 pre-registration, add a schema naming constraint: "For any dimension that appears in both heuristic and LLM scoring, the schema field name must be layer-qualified: `heuristic_reasoning_depth` and `llm_reasoning_depth` — not a shared `reasoning_depth`. Exception: if validity-matrix.json case (a) is confirmed for a dimension, a unified field MAY be used with a `construct_note` annotation."
2. In Plan 05 field-provenance, add a column `layer_qualified` (yes/no) for each field. If `no`, a `unification_justification` is required citing the validity-matrix.json finding.
3. In the CONTEXT Decisions section, add: "Plan 05 Schema Naming: Dimension names shared between heuristic and LLM layers are presumptively distinct constructs. Layer-qualified names are the default. Unification requires explicit validity evidence."
**Impacts:** Plan 05, 3.1c, Plans 03/04 (validity-matrix.json must support the unification decision)
**Research needed:** no
**Confidence:** HIGH
**Classification:** structural
**Status:** implemented
**Adversarial note (ADV Validation):** The improvement withstands scrutiny. It correctly identifies construct ambiguity as an infrastructure risk (not cosmetic), specifies three discrete changes, and leaves the unification decision to evidence (validity-matrix.json case a). The item is mergeable.
**Cross-references:** IMP-17, IMP-03, IMP-20 — closes the loop these three leave open at the schema boundary. IMP-17 must be implemented together with P5-ADV-R-01.

---

### P5-ADV-R-02: Session 0 baseline capture must persist and compare graph fingerprints from existing machinery
**Target:** CONTEXT
**What:** Session 0 task (a1) does not instruct persisting the graph fingerprint that `VKGBuilder.build()` already computes and logs. Without persisted fingerprints, any cross-build finding difference during Plan 01 is undiagnosable. The fingerprint infrastructure (`graph_fingerprint()`, `compare_fingerprints()`, `verify_determinism()`) is fully implemented in `kg/fingerprint.py` and already imported in `core.py`. The Session 0 script only needs to call `graph_fingerprint(graph)` on the returned object and write the result to a sidecar file.
**Why:** Plan 01 Outcome A says "if output differs on same object, that is a detection engine bug." But if Session 0 builds fresh graphs and Plan 01 builds fresh graphs, there are no "same object" runs. Without fingerprint comparison, Outcome A cannot distinguish (a) detection non-determinism from (b) graph construction non-determinism.
**How:**
1. In Session 0 task (a1), after "Build graphs via `VKGBuilder.build()`", add: "For each contract graph, call `graph_fingerprint(graph)` from `alphaswarm_sol.kg.fingerprint` and persist to `.vrs/experiments/session-0/graph-fingerprints.json` with schema `{contract: str, fingerprint: str, node_count: int, edge_count: int}`. This uses existing machinery — no new code required."
2. In Plan 01 Outcome A, add: "First diagnostic step: compare graph fingerprints from Session 0 build vs Plan 01 build using `compare_fingerprints()`. If `identical=False`: graph construction non-determinism detected — do NOT classify as detection engine bug. Route to Assumption 7 and BSKG audit. If `identical=True`: Outcome A divergence is definitively a detection engine issue."
3. In Assumption 7, add: "Partial coverage note: `graph_fingerprint()` hashes final stored property values. If `set()` intermediate computations in `operations.py` (lines 287, 988, 1129) produce different iteration orders across runs but hash to the same final values, the fingerprint will NOT detect this. To test: rebuild the same contract twice in the same Python session and compare fingerprints. `verify_determinism()` in `kg/fingerprint.py` automates this."
**Impacts:** Session 0 task (a1), Plan 01 Outcome A diagnostic path, Assumption 7
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no — `kg/fingerprint.py` with all required functions is already implemented and imported
**Classification:** structural
**Status:** implemented
**Adversarial note (ADV Validation):** Research-free and mergeable. The item's strength is catching that IMP-05 over-proposed a solution when the machinery was already built. Classification as structural is correct — this is a measurement methodology gap, not cosmetic.
**Cross-references:** replaces P5-IMP-05; addresses Assumption 7 coverage gap

---

### P5-ADV-R-03: Budget ceiling requires explicit Plan 02 scope lever — IMP-10 and IMP-22 compound on critical path
**Target:** CONTEXT
**What:** The 5.5-6.25 work-session budget is at risk when IMP-10 (Plan 02 session estimate correction: 1-1.25 → 2-2.5 sessions) and IMP-22 (Phase 1 quality gate deferred to after Plan 02 rubric freeze, adding 0-30 min conditional) are both applied. Worst case: Plan 02 takes 2.5 sessions AND Phase 1 quality gate fires → 6.5 work sessions, exceeding the 6.25 ceiling. No current scope lever is identified to absorb this overrun.
**Why:** The Budget Recount names the work-session ceiling (5.5-6.25) but does not identify what to cut if Plan 02 extends. Plan 02's internal protocol has grown substantially across 4 passes (three-instrument model, pairwise calls, calibration rounds, held-out anchor, non-determinism protocol). The ceiling will be breached in the "careful execution" case, not the "failure" case.
**How:**
1. Add: "Baseline expectation: Plan 02 core = 2-2.5 sessions includes 1-2 successful calibration rounds. Threshold: if Session B (calibration + scoring phase) exceeds 90 minutes with calibration still incomplete, cut to best-version rubric at current round. Proceed to scoring with 'calibration-incomplete' annotation."
2. Add: "Fallback scope lever for critical-path pressure: if Plan 02 runs over AND Plan 03/04 Phase 2 must start on schedule, the option sequence is: (a) complete calibration with best version [preferred], (b) reduce Plan 03/04 Phase 2 to Phase 1 only (skip gameability matrix — critical-path compression), (c) defer Plan 03/04 Phase 2 one week [does NOT block Plan 05 or 3.1c entry]. Pre-register which option applies if time pressure materializes."
3. Update Impacts to include: "Plan 03/04 Phase 2 start date; Plan 05 entry gate (if Phase 2 deferred)"
**Impacts:** Budget Recount decision; Plan 02 session estimate; Plan 02 rubric freeze protocol; Plan 03/04 Phase 2 start date; Plan 05 entry gate (if Phase 2 deferred)
**Research needed:** no
**Confidence:** HIGH
**Classification:** structural
**Status:** implemented
**Adversarial note (ADV Validation):** The improvement identifies a real budget risk (highest confidence), but the original How was insufficiently concrete for `/msd:plan-phase` to turn into tasks. Two specific issues: (1) "primary reduction target is calibration rounds" lacked a baseline round count and threshold; (2) "budget overrun trigger and procedure" was unspecified. The rewrite provides explicit 90-minute threshold, option sequence for scope levers, and a pre-registration requirement for which option applies under time pressure.
**Cross-references:** IMP-10, IMP-22

---

### P5-ADV-R-04: `is_tp` join script must be pre-generated as a pre-flight artifact
**Target:** CONTEXT
**What:** The five structural corrections to Session 0 (IMP-01 through IMP-07) collectively depend on a ground-truth join script being available during task (a1). IMP-01 requires computing `is_tp` by joining each finding against the CORPUS ground truth from `test_detection_baseline.py`. If this join script is written during the session, task (a1) expands by 10+ minutes and the 100-min core budget is breached. If pre-generated, the budget holds. This dependency is not documented anywhere in the current pre-flight checklist (3 items).
**Why:** Session 0 time budget arithmetic breaks if the `is_tp` join is in-session work. An executor following the CONTEXT as written would write the join script during task (a1), eating into the 25-30 min window.
**How:**
1. Specify the script template location and minimum content: ".planning/phases/3.1e-evaluation-zero-empirical-sprint/session-0-baseline-script.py — template script containing: (a) imports + setup, (b) CORPUS dict load from test_detection_baseline.py, (c) join function definition: `is_tp(contract_label, node_label, corpus_dict) -> bool`, (d) example invocation on SideEntranceLenderPool. Minimum: 80 LOC template."
2. Add to pre-flight checklist: "[ ] Verify session-0-baseline-script.py exists. If not, pre-generate from template before session clock starts. Time: 15 min to customize for current codebase if template needs refresh."
3. Note: "This script becomes the foundation for both Session 0 task (a1) and Plan 01 comparison-script.py (IMP-08). Reuse the same join logic in both."
**Impacts:** Session 0 task (a1) budget; Session 0 pre-flight checklist; Artifact manifest
**Research needed:** no
**Confidence:** HIGH
**Classification:** structural
**Status:** implemented
**Adversarial note (ADV Validation):** The improvement is directionally correct (the join IS a prerequisite work artifact) and identifies real budget risk (IMP-01 displaces 10+ min of complexity). However, the original How lacked specification of the artifact itself — template location, minimum content, and reuse guidance for IMP-08's comparison script. The rewrite adds these specifics.
**Cross-references:** derived from IMP-01, IMP-02, IMP-05, IMP-06, IMP-07 holistic analysis

---

### P5-ADV-R-05: Simplification interactions create net reduction in anti-circularity protection without documentation
**Target:** CONTEXT
**What:** IMP-12 (remove Step 0d calibration re-score), IMP-11 (weaken non-determinism kill switch from n=2 flip to majority-vote), and IMP-13 (tighten hallucination taxonomy) are implemented as independent improvements. Together they change the anti-circularity structure of the rubric validation protocol without any single item documenting that their combined effect reduces the total number of checks that could catch a miscalibrated rubric.
**Why:** The three improvements are individually reasonable but their combined effect is an increase in the protocol's brittleness to rubric overfit: no post-freeze re-score catches anchor-overfit (IMP-12 removed it), the variance kill switch fires less often (IMP-11 raises threshold), hallucination check covers only 3 claims per dimension (IMP-13). The held-out anchor becomes the sole structural anti-circularity guard. If the held-out anchor is not sufficiently different from calibration anchors in reasoning quality, rubric overfit will not be caught.
**How:**
1. Add to "Rubric freeze protocol" section: "Anti-circularity tradeoff note: Original Step 0d re-scored calibration anchors to test rubric stability under frozen text. IMP-12 removes Step 0d re-score, relying on the held-out anchor (Step 0d also score held-out) for independence testing. This assumes: (a) held-out anchor was never touched during calibration, (b) held-out differs from calibration anchors on at least one formula-input (unique_tool_count OR bskg_query_count), (c) if held-out scores low as expected, the rubric generalizes. This three-part check is the compensating mechanism. If any part fails, the rubric was tuned to calibration anchors and may not generalize."
2. Add item (e) to "Pre-Registration Checklist" decision: "(e) Held-out anchor coverage: does the held-out anchor differ from GOOD on at least one heuristic-formula-input dimension? If both GOOD and held-out have unique_tool_count=3 AND bskg_query_count=3, the held-out is not independent — held-out cannot serve as generalization test. Pre-verify this before calibration begins."
**Impacts:** CONTEXT (Rubric freeze protocol section + Pre-Registration Checklist decision)
**Research needed:** no
**Confidence:** MEDIUM
**Classification:** structural
**Status:** implemented
**Adversarial note (ADV Validation):** The item correctly identifies a second-order effect (simplifications interact) that requires documentation, but the original How was too vague to implement — it did not specify what anti-circularity protection was lost or what now compensates for it. Confidence corrected from HIGH to MEDIUM (requires understanding the interaction between three separate items). The rewrite articulates the three-part compensating mechanism and adds a concrete held-out independence check.
**Cross-references:** IMP-12 (atomic-freeze constraint), IMP-11 (majority-vote kill switch), IMP-13 (hallucination scope). Second-order consequence: if rubric overfit is not caught in Plan 02, the validity-matrix.json results may overstate LLM_adds_signal confidence, inflating the go/no-go outcome for Plan 03/04 Phase 2 — the most consequential downstream risk.

---

### P5-ADV-R-06: MEDIOCRE anchor has no machine-checkable discriminability floor before LLM scoring
**Target:** CONTEXT
**What:** The MEDIOCRE anti-strawman check says "before LLM scoring, confirm MEDIOCRE is 'plausibly mediocre' — record judgment." This is a human judgment with no operationalized criterion. If the anchor writer makes MEDIOCRE too close to GOOD (to avoid strawman), they risk creating an anchor that even a competent LLM cannot distinguish from GOOD on content alone. This would cause H1 and H2 to fail simultaneously — a false no-go produced by over-correcting the strawman concern.
**Why:** All three fixes (IMP-09, 11, 14) address the go/no-go threshold structure. None address the anchor design process that determines whether the threshold is reachable given the actual anchors produced. A false no-go from an over-corrected MEDIOCRE anchor would be indistinguishable from a genuine no-go.
**How:**
1. Clarify the gate targets LLM discrimination, not heuristic parity: "Discriminability check (Step 2.5, inserted before anchor freezing): the rubric must rank GOOD > MEDIOCRE > BAD on LLM scoring, not merely heuristic scoring. Before freeze, confirm: (a) can a human reading {observed} excerpts alone rank the 3 anchors correctly? (b) do the pairwise hypotheses predict GOOD > MEDIOCRE ranking? If either fails, revise MEDIOCRE. Anti-circularity guard: do NOT adjust anchors based on preliminary heuristic scores. Use human judgment + hypothesis structure only."
2. Fallback rule: "If MEDIOCRE discriminability cannot be achieved after 2 revision rounds, escalate: MEDIOCRE may be intrinsically hard to write at the required specificity. Options: (a) widen GOOD-MEDIOCRE gap via concrete protocol-knowledge depth difference, (b) substitute a different secondary dimension (pull from eligible fallback pool), (c) proceed with ambiguous MEDIOCRE and record as 'low-confidence dimension' in element-preregistration.json. Option (c) may still yield data but reduces go/no-go confidence."
3. Add to element-preregistration.json: "discriminability_assessment: human_judgment (yes|no|unclear) + justification (why MEDIOCRE is or is not clearly worse than GOOD on the dimension's conceptual definition)."
**Impacts:** Plan 02 wiring order step (3); element-preregistration.json minimum content spec
**Research needed:** no
**Confidence:** HIGH
**Classification:** structural
**Status:** implemented
**Adversarial note (ADV Validation):** The item identifies a real risk (over-corrected MEDIOCRE could become indistinguishable from GOOD, producing a false no-go), but the original How conflated heuristic and LLM discriminability without specifying which matters for the gate. The rewrite clarifies the gate targets LLM discrimination, provides a concrete two-revision fallback with three options, and adds a structured discriminability_assessment field to element-preregistration.json.
**Cross-references:** P5-IMP-09, P5-IMP-11, P4-ADV-3-01. NOTE: this gap is only visible from the holistic scan. Individually IMP-09, 11, and 14 each fix a real problem; together they shift the remaining failure mode to anchor design.

---

### P5-ADV-R-07: Go/no-go state table is absent — execution will improvise threshold application
**Target:** CONTEXT
**What:** The go/no-go criterion is stated as prose: "2/3 divergence hypotheses confirmed via pairwise ordering = go. 0/3 = no-go. 1/3 = ambiguous." But the confirmation rules for each hypothesis depend on: (a) pairwise ordering outcome, (b) LLM explanation content check, AND (c) LLM_unreliable not triggered on that dimension. These three conditions interact. A hypothesis can fail instrument (a) but pass (b) — does it count? These interaction rules are not specified. During execution, the implementer will make judgment calls that are not pre-registered, introducing experimenter degrees of freedom in the go/no-go decision.
**Why:** Pre-registration principle (P2-SYN-01) requires specifying what constitutes success, failure, and the ambiguous-middle interpretation rule. The go/no-go has a prose statement but no decision table covering all combination outcomes. This is the most concrete way experimenter degrees of freedom can enter Plan 02 and invalidate its pre-registration claim.
**How:**
1. Add to Plan 02 a minimal go/no-go state table:
   "For each hypothesis H (1, 2, or 3):
   - CONFIRMED: pairwise ordering correct AND explanation content cites dimension-specific signal AND LLM_unreliable NOT triggered.
   - DISCONFIRMED: pairwise ordering incorrect (wrong winner on majority of n=2 or n=3 calls).
   - EXCLUDED: LLM_unreliable triggered on this dimension (counts as 0, not as disconfirmed — different downstream routes).
   - BORDERLINE: pairwise ordering correct but explanation content does not clearly cite non-heuristic signal. Count as 0.5 in go/no-go.
   Go/no-go total: CONFIRMED = 1.0, BORDERLINE = 0.5, DISCONFIRMED and EXCLUDED = 0. Go threshold: >= 2.0. Ambiguous: 1.0-1.5. No-go: <= 0.5."
2. Add to element-preregistration.json schema: per-hypothesis confirmation criterion (what specific LLM evidence strings would constitute 'cites dimension-specific signal').
3. This state table is the answer to "what does 2/3 mean operationally?" — without it, the threshold is a number without a procedure.
**Impacts:** Plan 02 pre-registration (element-preregistration.json); go/no-go decision at Plan 02 close
**Research needed:** no
**Confidence:** HIGH
**Classification:** structural
**Status:** implemented
**Adversarial note (ADV Validation):** The improvement withstands scrutiny. Pre-registration without explicit go/no-go state definitions is incomplete. The four-state framework (CONFIRMED/DISCONFIRMED/EXCLUDED/BORDERLINE) is appropriate for a complex multi-hypothesis evaluation. Mergeable as-is.
**Cross-references:** P5-IMP-09 (defines the 3 hypotheses), P5-IMP-11 (defines LLM_unreliable trigger), P2-SYN-01, P4-ADV-3-02. NOTE: the BORDERLINE state is necessary because the explanation content check (Instrument 3) is qualitative — some LLM explanations will be partially responsive, and a binary confirm/disconfirm forces an arbitrary cut.

---

### P5-ADV-R-08: Pre-flight checklist has no silent-failure detection for executor miscounting mechanism clusters
**Target:** CONTEXT
**What:** The gap revealed by reviewing IMP-04 and IMP-16 together: both items address pre-flight or Phase 1 gates, but neither addresses the case where the executor silently miscounts without the session stalling or failing visibly. IMP-04 installs a gate on dimension count. IMP-16 installs a gate on mechanism cluster count. Neither installs a gate on enumeration CONTENT. If the executor selects wrong dimensions for Session 0 task (b), all downstream divergence hypotheses test the wrong signal. If mechanism clusters are under-counted, Phase 2 goes-no-go on an incomplete adversarial corpus.
**Why:** Silent enumeration errors are the worst failure mode for a pre-registration-first methodology. Both failures are undetectable until Plan 05 synthesis, where field-provenance.md would reveal the discrepancy — but by then, re-running Phase 1 would require a new session slot.
**How:**
1. Specify "spot-check item 2a" in pre-flight checklist: "Before Phase 1 execution, manually review one of the 3+ clustered code paths. Open the cluster mechanism's source file (e.g., graph_value_scorer.py:92-95 for regex citation detection). Confirm: (a) the code path exists and matches the mechanism description, (b) the function is reachable from the evaluator's main call path, (c) no recent refactoring has orphaned the code path. Time: 5 min. This prevents 'enumeration-on-stale-code' trap."
2. Add to archetype-count.json schema: `enumerated_code_paths: [{ mechanism_cluster: str, code_location: str, source_file_sha256: str }]` — records which file version was enumerated, enabling quick re-check if code changes.
3. Add to Phase 0 exit artifact (descriptive_clusters.json): `source_baseline: { bskg_builder_commit: str, evaluator_commit: str, timestamp: str }` — records the codebase state when baseline FPs were classified, enabling Phase 0 categories to be revisited if code shifts.
**Impacts:** Pre-flight checklist (item 2a), Phase 1 exit gate (archetype-count.json schema), Phase 0 exit artifact (descriptive_clusters.json schema)
**Research needed:** no
**Confidence:** HIGH
**Classification:** structural
**Status:** implemented
**Adversarial note (ADV Validation):** The improvement identifies a real risk (silent enumeration errors are the worst failure mode for pre-registration methodology), and the three proposed additions are directionally correct. However, the original How was too abstract to implement — "spot-check item 2a" was undefined, and archetype-count.json/descriptive_clusters.json schema additions lacked concrete field specifications. The rewrite provides specific source file references, file version tracking via SHA256, and commit-based provenance.
**Cross-references:** IMP-04, IMP-16 — addresses a shared gap both items left open (enumeration content validation vs enumeration count validation)

---

### P5-SYN-01: Plan 05 assumes upstream outputs are format-compatible, but three independent items found three independent incompatibilities
**Target:** CONTEXT
**What:** Three items from different review groups independently discovered that Plan 05 cannot fulfill its synthesis role because upstream plan outputs are incompatible in ways that Plan 05's current design does not detect or resolve: (1) IMP-18 found the integration smoke test runs too late to influence Plan 02's {observed} format; (2) IMP-20 found no mechanism for detecting contradictory findings across plans; (3) IMP-21 found that Plan 05 Track A/B conflates detection-relevant and evaluation-relevant artifacts from Plan 03/04. Each item proposes a local fix, but the underlying pattern is that Plan 05 was designed as a sequential aggregator receiving compatible inputs from parallel experiments, when in practice those experiments produce outputs in different formats, with different construct definitions (IMP-17/ADV-R-01), under different degradation conditions (compound degradation rule), and with no integration interface specification between them.
**Why:** Addressing IMP-18, IMP-20, and IMP-21 individually produces three local patches. Addressing them as a unified concern produces a single Plan 05 "integration contract" that specifies: (a) what format each upstream artifact must be in for Plan 05 to consume it, (b) what degradation states Plan 05 can handle vs what requires escalation, and (c) what contradictions are structurally predictable. Without this, each new improvement to Plan 05 adds another ad-hoc check rather than building on a coherent integration model.
**How:**
1. Name the three incompatibilities explicitly: (a) IMP-18 — Plan 05 smoke test: format gap between Plan 01 per-function detection output and Plan 02 rubric {observed} field; (b) IMP-20 — Plan 05 conflict detection: cost-unit ambiguity (compute_seconds vs tokens) across tracks; (c) IMP-21 — Plan 05 degradation rules: INCONCLUSIVE handling when multiple tracks are inactive.
2. Add to CONTEXT "Plan 05" section: "Upstream Integration Contract (new subsection): Every input artifact from Plans 01, 02, 03/04 must satisfy minimum format requirements before Plan 05 consumes it. Track A (always available): Plan 01 baseline-before.json and baseline-after.json (schema defined in IMP-01). Minimum: per-function findings with is_tp field. Degradation: if missing, Plan 05 cannot compute cost_per_FP_removed — note as Track A degraded, continue with Track B. Track B (graduated activation): Plan 02 per-dimension matrix output (validity-matrix.json). Minimum: dimension, validity_coefficient, LLM_adds_signal flag. If not present, write evaluation_observations.md documenting what was attempted. Track C (optional): Plan 03/04 Phase 0+1 outputs (descriptive_clusters.json, archetype-count.json). Minimum: at least one taxonomy category with ≥1 FP, at least 3 gaming archetypes. If < 2 categories present: flag as 'corpus-limited' and route to Plan 05 Unobserved Phenomena (not a blocker, but a finding)."
3. For each track, specify: "If degraded, what is the Plan 05 fallback?" (e.g., "if Track B unavailable, Unobserved Phenomena item: 'LLM evaluation reliability: requires-infrastructure, target: 3.1c'").
**Impacts:** Plan 05 (adds integration contract section), CONTEXT Decisions (adds new decision)
**Components:** P5-IMP-18, P5-IMP-20, P5-IMP-21
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (ADV Validation):** The item correctly identifies a pattern (three independent items found the same systemic problem: Plan 05 was designed as a sequential aggregator for compatible inputs, but experiments produce incompatible outputs). The original How was too vague — "add Upstream Integration Contract section" without naming the three incompatibilities or specifying track-level degradation handling. The rewrite names the three incompatibilities explicitly and provides minimum field requirements with concrete fallback paths per track.
**Source:** Post-review synthesis (cross-cutting)

---

### P5-CSC-01: IMP-09's H3 hypothesis requires BAD anchor design constraints that do not exist
**Target:** CONTEXT
**What:** IMP-09 (enhanced) introduces H3: "LLM explanation for MEDIOCRE > BAD cites ABSENCE of evidence chain in BAD, not merely absence of graph queries." The current BAD anchor specification is "no graph queries, hallucinated finding." But H3 explicitly requires the LLM to discriminate BAD from MEDIOCRE on something deeper than structural absence of graph queries. If BAD is defined primarily by "no graph queries," then the most obvious LLM explanation for MEDIOCRE > BAD will be "MEDIOCRE has graph queries and BAD does not" — exactly the structural feature H3 is trying to exclude. H3 needs BAD to have some graph queries (or at least tool calls that look like real investigation) but with a fundamentally broken evidence chain, so the LLM must evaluate reasoning quality rather than structural presence/absence.
**Why:** Without BAD anchor design constraints parallel to MEDIOCRE's, H3 is likely to produce a trivially confirmed result (LLM cites structural absence) or a false disconfirmation (LLM cannot find a non-structural difference because the anchor was not designed to have one). Either outcome corrupts the go/no-go count. The current CONTEXT has detailed MEDIOCRE design constraints (4 specific requirements) but only a one-line BAD description.
**How:**
1. Specify BAD anchor design constraints (parallel to MEDIOCRE's, from IMP-13): "(a) unique_tool_count <= 3 (to prevent formula saturation). (b) bskg_query_count = 0 (explicit: no graph queries, which is the structural difference from GOOD/MEDIOCRE). (c) conclusion IS correct (agent identifies a real vulnerability, just got there by luck/hallucination, not reasoning). (d) NO reasoning chain — agent jumps directly from finding to conclusion without explaining causal steps. Anti-strawman: is this plausibly bad? Yes — a real agent might jump-to-conclusion when evidence is weak."
2. Add H3 validity prerequisite: "Before LLM scoring BAD, confirm: the BAD anchor contains at least one CORRECT element (function name, pattern class, or vulnerability consequence) that the agent reached without graph context. This prevents BAD from being nonsensical (which would make MEDIOCRE > BAD trivially true). Example: 'Function X has access control bypass through Y' is a correct structure, even if the causal chain is missing. Example anti-strawman check: 'Does the BAD anchor demonstrate a reasoning failure I could see from a real agent under time pressure?' If answer is no, rewrite."
3. Update BAD description: "BAD: agent produces a finding with plausible conclusion but zero graph-based reasoning. The finding is correct by luck. The reasoning process lacks evidence interpretation. Structural markers: zero bskg_query_count, no node IDs cited, no causal chain. Semantic markers: (LLM scores this part) conclusion is correct despite hollow reasoning."
**Impacts:** Plan 02 anchor design (BAD anchor specification); H3 testability
**Trigger:** P5-IMP-09
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (ADV Validation):** The item correctly identifies that H3 (testing whether LLM discriminates BAD from MEDIOCRE on reasoning quality) is vulnerable to a structural failure mode: if BAD is defined only by "absence of graph queries," LLM will trivially cite this structural feature. The original How was directionally correct but lacked specificity — it did not enumerate BAD design constraints with the same detail as MEDIOCRE's. The rewrite provides four concrete BAD constraints, an anti-strawman check, and a validity prerequisite tying bskg_query_count to H3 testability.
**Source:** Post-review synthesis (cascade)

---

## Convergence Assessment (P5 aggregate)

| Area | Structural | Cosmetic | Creative-structural | Ratio |
|------|-----------|---------|---------------------|-------|
| Measurement Foundation (Session 0 + Plan 01) | 7 + 2 ADV | 1 | 0 | 10.0% cosmetic |
| LLM Evaluation Design (Plan 02) | 7 + 4 ADV | 0 | 0 | 0% cosmetic |
| Downstream Experiments & Integration (Plans 03/04 + 05) | 6 + 2 ADV | 2 | 0 | 20.0% cosmetic |
| **Total** | **28** | **3** | **0** | **9.7% cosmetic** |

**Original items:** 20 structural + 3 cosmetic = 13.0% cosmetic
**ADV items added:** 8 (all structural)
**New total:** 28 structural + 3 cosmetic = 9.7% cosmetic

**Convergence ratio:** 9.7% (threshold: 80% for advisory at pass 5 — ADVISORY, does not block)
**Gate behavior:** Pass 5 is ADVISORY — structural issues remain; passing adversarial review is warranted.

---

## Post-Review Synthesis
**Items created:** P5-SYN-01, P5-CSC-01
**Key insight:** Plan 05's role as a synthesis point is undermined by three independent format/compatibility gaps (IMP-18, IMP-20, IMP-21) that share a common cause: no upstream integration contract. Separately, IMP-09's new H3 hypothesis creates a cascade gap in BAD anchor design -- the current one-line BAD specification ("no graph queries, hallucinated finding") makes H3 either trivially confirmed or meaningless, because the hypothesis explicitly requires discrimination beyond structural presence/absence of queries.
