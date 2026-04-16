# Improvement Pass 1

**Date:** 2026-02-25
**Phase:** 3.1e
**Status:** complete

## Pipeline Status

| Stage | Count | Items |
|-------|-------|-------|
| Implemented | 22 | P1-IMP-01, 02, 03, 04, 05, 06, 07, 08, 09, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, P1-ADV-31, P1-SYN-01, P1-CSC-01 |
| Reframed | 1 | P1-IMP-10 → P1-ADV-31 |
| **Total** | **23** | |

**Pipeline:** [discuss] ✓ → [improve] ✓ → [research] ✓ → [implement] ✓ → [plan] ✓ → [execute] —

## Adversarial Lenses

| Lens | Brief | Items | Attack Vector |
|------|-------|-------|---------------|
| Baseline Measurement Validity | Tests whether Session 0 and Plan 01 measurement foundations are trustworthy. Fragile CORPUS type handling, silent truncation, undefined handoff schemas, and unresolved counting contradictions can corrupt all downstream experiment data. | P1-IMP-01, P1-IMP-02, P1-IMP-03, P1-IMP-05, P1-IMP-06, P1-IMP-07 | What if the baseline script passes all pre-flight checks but silently produces wrong counts due to element-level type confusion or parameter override at runtime? |
| LLM Evaluation Protocol Rigor | Challenges whether the LLM-as-judge measurement model (three instruments, anchor calibration, validity coefficients) can produce meaningful results at N=7. Degenerate statistics, correlated dimensions, and undefined hallucination checks threaten measurement validity. | P1-IMP-08, P1-IMP-09, P1-IMP-10, P1-IMP-11, P1-IMP-12, P1-IMP-13, P1-IMP-14 | What if the normalized inversion count at N=7 cannot distinguish signal from noise, making the entire validity measurement theater? |
| Schema Synthesis & Downstream Handoff | Examines whether Plan 05's synthesis and 3.1c entry protocol will work given partial upstream data, undefined schemas, and the gap between human-readable and machine-parseable artifacts. | P1-IMP-04, P1-IMP-15, P1-IMP-16, P1-IMP-17, P1-IMP-18, P1-IMP-19, P1-IMP-20 | What if Plan 05 enters constrained mode unnecessarily because it cannot distinguish "Track B pending human review" from "Track B failed"? |

## Improvements

### P1-IMP-01: Pre-flight must validate CORPUS element structure, not just container type
**Target:** PLAN-00
**What:** Pre-flight checklist must validate CORPUS is `list[GroundTruth]` with required fields, not merely a list — the type confusion can survive a shallow isinstance check and still produce silent count corruption downstream.
**Why:** Research explicitly flags this confusion as the single highest-risk blocker. A malformed CORPUS that passes a top-level type check will silently produce wrong TP/FP counts that corrupt every downstream experiment baseline.
**How:**
1. In the pre-flight section of the baseline script, add a dedicated `validate_corpus()` function that: (a) asserts `isinstance(CORPUS, list)` and `len(CORPUS) > 0`; (b) for each element asserts `isinstance(el, GroundTruth)`; (c) asserts required fields `contract_name`, `expected_tp`, `expected_fp` are present and non-null.
2. Call `validate_corpus()` as the FIRST step of the script — before any graph build or query.
3. Make failure BLOCKING: raise `SystemExit(1)` with a message that prints the offending element index and its actual type.
4. In the dry-run smoke test, include one intentionally malformed element (a plain dict) and assert the script exits with code 1 and prints the diagnostic — proving the guard is exercised, not just present.
5. Add a checklist item in Plan 00's preflight section: "CORPUS type+field validation passes on 7-contract corpus."
**Impacts:** Plan 00 confidence unchanged (HIGH), but prevents silent corruption propagating to Plan 01 and all downstream plans.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Standard defensive assertion
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Research flagged this risk; no plan addresses it
**Classification:** structural
**Adversarial verdict:** ENHANCE (Baseline Measurement Validity) — shallow isinstance misses element-level type confusion; must validate element structure and required fields

### P1-IMP-02: limit=200 must be a runtime-observable invariant, not a source-text grep
**Target:** PLAN-00
**What:** The baseline script must enforce `limit >= 200` as a runtime-observable invariant, not a source-text grep, and must record the actual limit value used in `baseline-before.json` under a specified field path.
**Why:** Default limit=50 silently truncates results — 75 candidates becomes 50 with no warning. If the limit is set correctly in code but overridden by a config file or kwargs at runtime, a grep check gives false confidence. The baseline JSON must record the actual runtime value so Plan 01 comparisons can verify parity.
**How:**
1. In the baseline script's `run_query()` wrapper, add a runtime assertion immediately after constructing the query object: `assert query.limit >= 200, f"BLOCKING: limit={query.limit} will truncate results"`.
2. Log the actual limit used to a `meta.query_params.limit` field in `baseline-before.json` — exact path: `$.meta.query_params.limit`.
3. In Plan 00 done criteria, add: "baseline-before.json contains `$.meta.query_params.limit >= 200`."
4. In the pre-flight checklist, replace the grep step with: "Run `python baseline_script.py --dry-run --limit 49` and confirm it exits with code 1 and prints the BLOCKING message."
5. Remove any grep-based check — source text is not a substitute for runtime assertion.
**Impacts:** Plan 00 and Plan 01 — prevents invalid delta measurements
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Standard parameter validation
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Research identified risk, plans do not address it
**Classification:** structural
**Adversarial verdict:** ENHANCE (Baseline Measurement Validity) — grep-based source check is fragile; must use runtime assertion and record actual limit in baseline JSON

### P1-IMP-03: Session 0 to Plan 01 handoff schema must be explicit
**Target:** PLAN-00
**What:** Plan 00 produces baseline-before.json. Plan 01 consumes it for delta computation. The area brief asks "whether the Session 0 -> Plan 01 handoff (baseline-before.json schema) is complete for Plan 01's delta computation." From the plan summaries: Plan 01 needs per-function-firing counts, contract-level breakdowns, and graph fingerprints. Plan 00's done criteria mention "raw baseline capture" but do not specify the JSON schema that Plan 01 requires.
**Why:** Without an explicit schema contract, Plan 00 might produce a baseline that Plan 01's comparison script cannot consume. This is a classic interface gap between sequential plans. The comparison script in Plan 01 would need to be written against whatever Plan 00 happens to produce, rather than against a specified contract.
**How:**
1. In Plan 00, Task 2 (baseline capture), add to done criteria: "baseline-before.json matches schema: `{meta: {timestamp, limit, graph_fingerprint, corpus_size}, per_contract: {[name]: {findings: [...], tp_count, fp_count, total}}, totals: {tp, fp, total, contracts_tested}}`"
2. In Plan 01, frontmatter must_haves, add: "comparison script validates baseline-before.json and baseline-after.json share identical schema before computing deltas"
**Impacts:** Plan 00 -> Plan 01 interface. Without this, Plan 01 Task 1 could fail at comparison time.
**Research needed:** no
**Confidence:** MEDIUM — the exact schema fields depend on what the PatternEngine actually returns, which I cannot verify without reading the code. But the principle of defining the handoff contract is clearly correct.
**Prior art:** 4 — Standard interface contract pattern
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Interface gap between two plans
**Classification:** structural
**Adversarial verdict:** CONFIRM (Baseline Measurement Validity) — correctly scoped, concrete, and bounded

### P1-IMP-04: Cost instrumentation scope is vague — "three levels" undefined for 3.1f loop economics
**Target:** PLAN-01
**What:** CONTEXT says Plan 01 delivers "Cost instrumentation at three levels" and the area brief asks about "gaps that would invalidate 3.1f loop economics calculations." Plan 01's summary mentions "cost summary" as Task 3 output. But what are the three levels? Time? Token count? API calls? Wall-clock per stage? The cost-summary.json is consumed by Plan 05 (per other_areas). If the cost data is incomplete or uses wrong units, 3.1f economics are built on sand.
**Why:** "Cost" in LLM contexts is ambiguous: wall-clock time, token consumption (input vs output), API call count, dollars. For 3.1f loop economics, you likely need all of these at per-pattern-fix granularity. If Plan 01 only records wall-clock time, the economics model is missing the dominant cost driver (tokens/dollars).
**How:**
1. In Plan 01, Task 3 (cost summary), specify the three levels explicitly in done criteria: e.g., "(1) wall-clock seconds per stage, (2) total LOC changed, (3) human-effort-minutes if applicable" — or whatever the actual intended levels are.
2. In Plan 01, Task 3, add to done criteria: "cost-summary.json includes `{fix_cost: {loc_changed, time_seconds, files_modified}, measurement_cost: {pipeline_runs, time_seconds}, total_effort_minutes}`"
**Impacts:** Plan 01 -> Plan 05 -> 3.1f. Vague cost data propagates as vague economics.
**Research needed:** no (resolved — GAP-03: "three levels" = three pipeline scopes: full_7, targeted_3, lens_only. Cost schema already fully specified in Plan 01. 3.1f defers to 3.1e data.)
**Confidence:** HIGH (upgraded from MEDIUM — research resolved all ambiguity)
**Prior art:** 3 — Cost tracking is standard, but what to measure for "loop economics" is project-specific
**Prerequisite:** no
**Status:** implemented
**Research summary:** "Three levels" means three pipeline scopes, not abstraction layers. cost-summary.json schema is already specified. Do NOT reuse CostLedger/CostTracker (product infrastructure). Use time.perf_counter() + LLM API response tokens.
**Origin:** NOVEL — Gap exists in original context
**Classification:** structural
**Adversarial verdict:** RESEARCH (Schema Synthesis & Downstream Handoff) — cannot define schema without knowing 3.1f's consumer contract

### P1-IMP-05: Negative control must pre-register expected_tp=0 and classify any TP as false positive
**Target:** PLAN-01
**What:** The negative control contract (ReentrancyWithGuard) must have a pre-registered expectation that separately specifies `expected_tp=0` and records any observed findings as confirmed false positives — not merely a total count assertion.
**Why:** A control that only asserts count parity does not distinguish between "no findings" and "same number of false positives." If the first run produces 2 FPs and the second run produces 2 different FPs, count parity passes while the FP character of findings has silently changed — invalidating the control's diagnostic value.
**How:**
1. In `baseline-before.json`, add a `negative_controls` array with one entry for ReentrancyWithGuard: `{ "contract": "ReentrancyWithGuard", "expected_tp": 0, "expected_fp_max": N }` where N is determined empirically in Session 0 and recorded.
2. In the Plan 01 comparison script, add a BLOCKING assertion: if any finding on ReentrancyWithGuard is classified as TP, halt with "NEGATIVE CONTROL VIOLATION: unexpected TP on guarded contract."
3. Non-zero FP count on the negative control is recorded and flagged as a known-FP, not silently accepted.
4. Add to Plan 01 done criteria: "Negative control TP count = 0; any deviation triggers BLOCKING halt before proceeding to metric comparison."
5. In Plan 00's Session 0 instructions, add a step: "Run pattern engine on ReentrancyWithGuard, record all findings as baseline FP candidates, commit to negative_controls entry."
**Impacts:** Plan 01 Outcome B falsification ("any TP lost") — without this, TP loss on the negative control could go undetected if it is not part of the primary test contracts.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Standard experimental control practice
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — CONTEXT mentions negative control but plans do not operationalize it
**Classification:** structural
**Adversarial verdict:** ENHANCE (Baseline Measurement Validity) — must distinguish expected_tp=0 from total count; any TP on negative control is a confirmed false positive

### P1-IMP-06: Graph fingerprint method undefined — legacy anti-pattern flagged but no replacement specified
**Target:** PLAN-01
**What:** Plan 01 includes "fingerprint verification" and "CORPUS drift check." These verify that the graph has not changed between baseline and re-run. But what IS a graph fingerprint? A hash of the entire graph? A count of nodes/edges? If it is a hash, any non-determinism in the builder (timestamp, dict ordering) produces false "drift" signals. If it is too coarse (just node count), real drift goes undetected.
**Why:** Research flags "using legacy fingerprint_graph" as an anti-pattern. This suggests there is an old fingerprint function that should not be used. Plan 01 needs to specify which fingerprint method to use and what equality means. A false drift detection halts the experiment unnecessarily; a missed drift corrupts the delta measurement.
**How:**
1. In Plan 01, Task 1, add to action steps: "Use content-based fingerprint (sorted node properties hash), NOT legacy fingerprint_graph. Record fingerprint method in baseline JSON."
2. In Plan 01, Task 1, add to done criteria: "Graph fingerprint comparison uses deterministic hashing (sorted keys, no timestamps). Fingerprint method is recorded in both baseline-before.json and baseline-after.json."
**Impacts:** Plan 01 Outcome A (pipeline reproducibility) depends entirely on this.
**Research needed:** no (resolved — GAP-04: Use `graph_fingerprint` from `alphaswarm_sol.kg.fingerprint`, NOT legacy `fingerprint_graph`. Returns 64-char SHA256 hex string, operates on KnowledgeGraph objects, hashes all stable properties.)
**Confidence:** HIGH (upgraded from MEDIUM — research found both functions with clear current/legacy separation)
**Prior art:** 5 — Function exists and is well-documented in codebase
**Prerequisite:** no
**Status:** implemented
**Research summary:** `graph_fingerprint(graph)` → 64-char hex, KnowledgeGraph input, all stable properties, rich edges, sorted keys. `fingerprint_graph(graph_data)` → legacy dict-based, 20 hardcoded keys, no rich edges. Use the OO variant. Drift check = simple string equality.
**Origin:** NOVEL — Research flags the anti-pattern; plans do not specify the alternative
**Classification:** structural
**Adversarial verdict:** RESEARCH (Baseline Measurement Validity) — cannot specify replacement without knowing current codebase state

### P1-IMP-07: Branch table must reference a counting-policy.md with derivation, not just a choice
**Target:** PLAN-00
**What:** The branch table in Plan 00 must reference a `counting-policy.md` that contains a derivation — not just a choice — of which baseline (11 TP/44 candidates vs 10 TP/75 candidates) is ground truth, with criteria that distinguish "under-reporting" from "correct low count" operationalized as numeric thresholds.
**Why:** Research surfaces two contradictory baselines. A branch table that says "if count < X → under-reporting" is only meaningful if X is derived from a resolved ground truth. Delegating to a policy document that merely picks a number restates the problem; the policy must show why one baseline is more trustworthy (e.g., which run used limit >= 200, which had correct CORPUS type) so the branch criteria are traceable.
**How:**
1. Before finalizing Plan 00's branch table, create `counting-policy.md` in the experiment directory. It must include: (a) the two contradictory baseline runs with their configuration parameters (limit, CORPUS type, date); (b) a decision rule identifying which is authoritative and why (e.g., "Run B used limit=200 and validated CORPUS type — Run A is discarded"); (c) the numeric threshold for "expected TP" on the 7-contract corpus derived from the authoritative baseline.
2. Update Plan 00 branch table to: `if observed_tp < (authoritative_tp - tolerance)` rather than an absolute threshold — where `authoritative_tp` is imported from counting-policy.md.
3. Add to Plan 00 done criteria: "counting-policy.md exists with derivation section; branch table references it by path."
4. Mark counting-policy.md as a BLOCKING prerequisite: Plan 01 execution cannot begin until it is committed.
5. If the research question (actual ground truth TP counts) cannot be answered in Session 0, record that as an explicit blocker in STATE.md rather than proceeding with an unresolved branch table.
**Impacts:** Plan 00 -> Plan 01 branch selection. Wrong branch = wrong Plan 01 strategy.
**Research needed:** no (answered by adversarial review — Baseline Measurement Validity)
**Confidence:** HIGH
**Prior art:** 3 — Branch tables are standard, but ground truth establishment for this specific corpus is novel
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Research identified the contradiction; plans do not resolve it before branching
**Classification:** structural
**Adversarial verdict:** ENHANCE (Baseline Measurement Validity) — counting-policy.md must contain derivation showing why one baseline is authoritative, not just a choice

### P1-IMP-08: Normalized Inversion Count must use categorical scheme at N=7
**Target:** PLAN-03
**What:** With N=7 transcripts, the normalized inversion count produces only 22 distinct values (max inversions = C(7,2) = 21). A single rank swap changes the score by ~0.048, making any fixed threshold arbitrary and brittle at this sample size.
**Why:** A threshold-based go/no-go verdict derived from a near-continuous score with 22 bins at N=7 will produce false precision. The measurement cannot meaningfully distinguish "close to threshold" from "clearly above" — the instrument is reporting noise as signal.
**How:**
1. Replace normalized IC with a three-tier categorical scheme evaluated against the heuristic ground-truth ranking:
   - STRONG: top-2 AND bottom-2 rank positions preserved (strict — no ties resolved in favor of pass)
   - WEAK: top-1 AND bottom-1 rank positions preserved, but interior order not fully preserved
   - NONE: neither top-1 nor bottom-1 preserved
2. Tie-breaking rule: if two transcripts share the same heuristic score, assign both the higher rank (pessimistic). A tie at the boundary of top-2 or bottom-2 counts as NOT preserved.
3. Map categories to gate outcomes: STRONG → PASS, WEAK → CONDITIONAL (requires H3 corroboration), NONE → FAIL.
4. Record the raw inversion count alongside the category label in calibration-results.json for future reanalysis when N grows.
5. Document that NONE subsumes both "random ordering" and "systematic inversion" — flag which subcase occurred (fraction of inversions > 0.5 indicates systematic reversal, a stronger failure signal).
**Impacts:** Plan 03/04 confidence stays MEDIUM but execution risk drops. Plan 05 input format changes.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — rank-order statistics at small N is studied but rarely applied to LLM-as-judge settings
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — visible from research anti-pattern warning + corpus size constraint
**Classification:** structural
**Adversarial verdict:** ENHANCE (LLM Evaluation Protocol Rigor) — added tie-breaking rule, NONE subcases, and gate outcome mapping

### P1-IMP-09: Anchor feasibility must define separation criteria per-dimension with composite threshold
**Target:** PLAN-02
**What:** The anchor set for Plan 02 Task 2 has no pre-flight satisfiability check. Multiple simultaneous constraints (unique_tool_count parity, bskg_query_count magnitude, saturation avoidance) may be mutually incompatible given the 7-transcript corpus — a condition that will not be detected until after LLM sessions have consumed budget.
**Why:** If anchor heuristic scores are not well-separated, the LLM ranking signal cannot be attributed to reasoning quality versus noise. Running calibration with degenerate anchors produces a result that looks like data but is actually undefined.
**How:**
1. Before Task 2, run the heuristic scorer on candidate anchor transcripts and emit a feasibility report.
2. Define minimum separation: for each of the two primary selected dimensions (per IMP-14 correlation-based selection), GOOD anchor must score strictly higher than BAD anchor. For the composite score (unweighted average across all 7 dimensions), GOOD > BAD by at least 0.20 on [0,1] scale.
3. Required pass conditions: both primary dimensions separate AND composite score separates. Partial separation (one of two primary dimensions fails) → CONDITIONAL — record which dimension failed and proceed with a note.
4. Saturation check: if any dimension scores 1.0 for both GOOD and BAD, flag that dimension as uninformative and exclude it from composite.
5. If no anchor pair satisfies minimum separation: halt Task 2, emit anchor-feasibility-FAIL.json with per-dimension scores, escalate to human before proceeding. Do not substitute different transcripts without recording the substitution.
6. Output: anchor-feasibility.json with per-dimension scores for each anchor, separation deltas, and pass/fail verdict.
**Impacts:** Plan 02 Task 1 gets longer but Task 2 failure risk drops significantly.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — standard calibration validation practice
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the constraints are listed but no satisfiability check exists
**Classification:** structural
**Adversarial verdict:** ENHANCE (LLM Evaluation Protocol Rigor) — must define 2x separation in terms of per-dimension and composite thresholds; specify what happens when dimensions saturate

### P1-IMP-10: Plan 02/03 parallelism creates rubric version conflict — needs sequencing constraint
**Target:** PLAN-03
**What:** Plan 03/04 Phase 1 (adversarial generation) is specified as "parallel with Plan 02." Plan 02 includes a "rubric freeze protocol: Max 3 revisions, SHA256 recorded." If Phase 1 generates adversarial transcripts while Plan 02 is still revising the rubric, the adversarial transcripts may be designed to game a rubric version that gets superseded.
**Why:** The LLM-Flatterer adversarial type is explicitly designed to fool LLM scoring, not heuristic scoring. If it only targets heuristics, it loses its defining purpose. The correct fix is sequencing, not scope reduction.
**How:** See P1-ADV-31 (REFRAME replacement).
**Impacts:** Plan 02 Task 3, Plan 03 Phase 1, execution sequencing
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2 — adversarial evaluation methodology is young; rubric versioning in LLM-as-judge is novel
**Prerequisite:** no
**Status:** reframed
**Origin:** NOVEL — the parallelism is explicitly specified but the rubric version interaction is not addressed
**Classification:** structural
**Adversarial verdict:** REFRAME (LLM Evaluation Protocol Rigor) — scope reduction is wrong fix; needs sequencing constraint (see P1-ADV-31)

### P1-IMP-11: Three-Instrument Model must name RIGHT_ANSWER_WRONG_REASON as explicit NO-GO
**Target:** PLAN-02
**What:** H1 pass (ordering correct) combined with H3 fail (explanation cites irrelevant features) is a critical diagnostic pattern — it means the LLM is a noise-driven oracle that happens to correlate with the ground truth at this corpus size. Without naming this case explicitly in the decision table, the three-instrument model will categorize it as "ambiguous" rather than "NO-GO with explanation pathology."
**Why:** Without naming this case explicitly in the decision table, the three-instrument model will categorize it as "ambiguous" rather than "NO-GO with explanation pathology," obscuring the failure mode.
**How:**
1. In Plan 02's Go/No-Go Decision Table, add an explicit case: "H1=pass, H3=fail: RIGHT_ANSWER_WRONG_REASON. Score=1.0. Verdict: NO-GO. Action: examine LLM explanations for spurious features, consider rubric revision (counts against 3-revision limit)."
2. In Plan 02 Task 2 verification steps, add: "After computing H1/H2/H3, explicitly check for RIGHT_ANSWER_WRONG_REASON pattern before declaring go/no-go."
3. Ensure the decision table entry also records which H3 criteria failed, for downstream diagnosis.
**Impacts:** Plan 02 go/no-go becomes more explicit. No structural change.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3 — "right for wrong reasons" is well-studied in ML evaluation but novel in this specific protocol
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the three-instrument design implies this case but does not name or handle it
**Classification:** structural
**Adversarial verdict:** CONFIRM (LLM Evaluation Protocol Rigor) — correctly identified, Score=1.0 → NO-GO is the right mapping

### P1-IMP-12: Hallucination check must define five entity classes with authoritative sources
**Target:** PLAN-02
**What:** The hallucination gate in Plan 02 uses "no hallucination" as a binary pass/fail criterion with no operational definition. In a security audit context, "hallucination" can mean fabricated function names, invented tool output values, nonexistent graph node IDs, or incorrect line number citations — each with different severity and detection method.
**Why:** Without an operational definition, the hallucination check is a subjective human judgment that cannot be automated, reproduced, or made part of a deterministic gate. Two evaluators applying the same criterion will reach different verdicts on the same explanation text.
**How:**
1. Define five entity classes with their authoritative sources:
   - FUNCTION_NAME → must appear in the transcript's contract source section
   - VARIABLE_NAME → must appear in the transcript's contract source section
   - LINE_NUMBER → must be within the contract's line range
   - TOOL_OUTPUT_VALUE → must match a value in the transcript's tool output section
   - GRAPH_NODE_ID → must match a node ID in the bskg query results section of the transcript
2. Extraction step: parse LLM explanation text, extract all tokens matching each entity class pattern (function calls, line number references, node ID format).
3. Cross-reference step: for each extracted entity, look up in the authoritative source. Not found → hallucinated.
4. Gate: 0 hallucinated entities = PASS. Any hallucinated entity = FAIL with list of offending entities.
5. Output schema for hallucination-check.json:
   ```json
   {
     "verdict": "PASS|FAIL",
     "entity_counts": {"FUNCTION_NAME": N, "LINE_NUMBER": N, ...},
     "hallucinated": [{"entity": "...", "class": "...", "context": "..."}]
   }
   ```
6. For entity classes where automated extraction is ambiguous (e.g., variable names with short tokens), fall back to human review and record in hallucination-check.json with source="HUMAN".
**Impacts:** Plan 02 Task 2 gets a concrete verification artifact.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — hallucination detection in LLM outputs is well-studied; application to LLM-as-judge explanations is less so
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the criterion exists but lacks operational definition
**Classification:** structural
**Adversarial verdict:** ENHANCE (LLM Evaluation Protocol Rigor) — must enumerate domain-specific entity classes; generic NER misses fabricated node IDs and tool output values

### P1-IMP-13: Quality gate retry must have max 2 retries with scope reduction trigger
**Target:** PLAN-03
**What:** Plan 03/04 Phase 1 includes a "quality gate with retry" for adversarial transcript generation. The plan does not specify: (a) maximum retry count, (b) what changes between retries, (c) what happens when retries are exhausted. Without termination bounds, this becomes an unbounded loop that can consume the session budget.
**Why:** Plan 03/04 has a session estimate of 1.5-2 sessions. If adversarial generation retries consume even 0.5 sessions, the remaining phases become infeasible.
**How:**
1. In Plan 03/04 Phase 1, add: "Quality gate retry: max 2 retries per adversarial transcript type. Between retries, modify the adversarial strategy (not just regenerate). If 2 retries exhausted for a transcript type, mark that type as FAILED and proceed with remaining types."
2. Add a scope-reduction rule: "If > 50% of adversarial transcript types fail quality gate after retries, trigger scope-reduction gate: drop Phase 3 (EST invariance) and reduce Phase 2 to validity measurement on successful types only."
3. In Plan 03/04 done criteria, add: "adversarial-generation-log.json records per-type attempt count, retry reasons, and final status (PASS/FAILED)."
**Impacts:** Plan 03/04 session budget becomes predictable. Phase 3 becomes conditional.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — retry with backoff/termination is standard practice
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the quality gate exists but termination is unspecified
**Classification:** structural
**Adversarial verdict:** CONFIRM (LLM Evaluation Protocol Rigor) — concrete, well-bounded, and appropriate. Scope reduction should specify what "reduce" means (e.g., drop weakest type, reduce N from 3 to 2).

### P1-IMP-14: Dimension selection must use Spearman correlation on pilot data, not name-based ordering
**Target:** PLAN-02
**What:** All 7 heuristic dimensions in Plan 02 are count-based proxies derived from the same transcript. Falling back from the default dimension to another count-based proxy does not increase measurement independence — it substitutes one correlated proxy for another, providing the appearance of a fallback without adding information.
**Why:** If the two selected primary dimensions are correlated (r > 0.6), the composite score is effectively measuring one construct with added noise. A fallback to a third correlated dimension compounds this — the three-instrument model's H3 component loses its diagnostic independence from H1.
**How:**
1. Before Plan 02 Task 1, compute Spearman rank correlation (not Pearson — counts are bounded and non-normal) for all C(7,2)=21 dimension pairs using the pilot transcript scores.
2. Select the two dimensions with the lowest pairwise Spearman correlation as the primary pair.
3. If the minimum pairwise correlation exceeds 0.6: flag "no low-correlation pair available in current dimension set." In this case, proceed with the two lowest-correlated pair but mark H3 as DEGRADED in all outputs — its independence is not established.
4. Fallback ordering: rank all remaining dimensions by their maximum correlation to either primary. Select fallback with lowest maximum correlation.
5. Record the correlation matrix in dimension-selection.json alongside the selected primary and fallback dimensions, for traceability.
6. This selection must be performed once before Task 2 and treated as fixed for the remainder of Plan 02 — do not recompute mid-run.
**Impacts:** Plan 02 Task 1 gets a data-driven dimension selection step. May change which dimensions are tested.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3 — decorrelation in feature selection is standard; application to LLM-judge dimension selection is novel
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — research identifies count-based proxy pattern but plan does not address correlation
**Classification:** structural
**Adversarial verdict:** ENHANCE (LLM Evaluation Protocol Rigor) — must specify Spearman (not Pearson), pilot corpus as data source, and handling when all pairs exceed r=0.6

### P1-IMP-15: Track A activation must distinguish load-bearing from supplementary artifacts
**Target:** PLAN-04
**What:** Track A activation criteria must distinguish load-bearing artifacts from supplementary ones. Binary available/unavailable silently degrades Plan 05 when partial Plan 01 output exists.
**Why:** If Plan 01 produced execution logs but not semantic-operation-counts.json, the current binary flag sends Plan 05 to Track B even though the most critical data is present. This causes 3.1c to receive a constrained-mode data package unnecessarily.
**How:**
1. In Plan 04 Task that evaluates upstream artifact state, add a tiered artifact manifest for Plan 01 with two tiers:
   - **Load-bearing** (Track A requires ALL): execution transcript, operation-sequence records, timing data
   - **Supplementary** (Track A degrades gracefully without): per-stage cost breakdown, retry logs
2. Add a third Track A state: `partial` — load-bearing present, supplementary missing. Document how downstream synthesis degrades (e.g., provenance entries marked `confidence: degraded`).
3. Add a fourth row to the compound state table: `Track A partial + Track B available → constrained synthesis with degraded provenance`.
4. The artifact manifest should be a short inline checklist in the plan task, not a separate file — keep it reviewable without context-switching.
**Impacts:** Plan 05 Task 1 action steps, Task 2 phase_entry_mode determination
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4 — Standard state machine design, minor adaptation needed
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — This gap exists in the original plan design regardless of any prior passes
**Classification:** structural
**Adversarial verdict:** ENHANCE (Schema Synthesis & Downstream Handoff) — must name which artifacts are load-bearing vs supplementary; add `partial` state

### P1-IMP-16: Track B must distinguish pending_human from unavailable
**Target:** PLAN-04
**What:** The distinction between "Track B unavailable" (Plan 02 failed) and "Track B pending human review" (Plan 02 succeeded but human hasn't signed off) produces different correct behaviors. "Unavailable" means skip Track B schemas. "Pending" means pause and request human input.
**Why:** Conflating them loses information and may cause Plan 05 to incorrectly enter constrained mode when a 2-minute human action would unlock data_rich mode.
**How:**
1. In Task 1 step 0 (Upstream Integration Contract check), add an explicit check: if llm-recommendation.md exists but plan-02-verdict-final.json does not, emit a human-action-required prompt and PAUSE (do not proceed to Track B classification). Quote the current contract check and add this intermediate state.
2. In the compound failure matrix, add a row: "Track B = pending_human" that maps to a 5-minute wait-and-prompt protocol before falling back to constrained mode.
**Impacts:** Plan 05 Task 1, potentially delays Plan 05 start
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Standard workflow gate pattern
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — The handoff gap exists in the original plan design
**Classification:** structural
**Adversarial verdict:** CONFIRM (Schema Synthesis & Downstream Handoff) — concrete gap with clear attack vector; PAUSE mechanism is appropriate for human decision gates

### P1-IMP-17: Smoke test pass criterion must be self-defining from field-provenance output
**Target:** PLAN-04
**What:** Integration smoke test pass criterion must be self-defining relative to the fields actually emitted by Plan 05, not against an independently maintained baseline list.
**Why:** A static baseline list diverges from actual output as the schema evolves. Tying the pass criterion to field-provenance output ensures coverage is always complete relative to what was produced, not what was anticipated.
**How:**
1. After field-provenance.md (or .json if IMP-18 is accepted) is written, the smoke test step reads the field list from that artifact.
2. For each field, the test asserts: source plan identified, confidence level present, at least one value example present.
3. smoke-test-results.json structure: `{ "fields_covered": [...], "fields_missing": [...], "pass": bool }` — `pass` is `true` iff `fields_missing` is empty.
4. If IMP-18 is also accepted, smoke-test-results.json references field-provenance.json directly, eliminating the need for a separate field list.
5. Add this as an explicit verify step in Plan 04: "smoke-test-results.json exists AND `pass: true` before emitting phase-entry signal to 3.1c."
**Impacts:** Plan 05 Task 1 done criteria observability
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Standard test coverage reporting
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Observability gap in original plan
**Classification:** structural
**Adversarial verdict:** ENHANCE (Schema Synthesis & Downstream Handoff) — pass criterion must reference field-provenance output, not a static baseline list

### P1-IMP-18: field-provenance needs companion .json for 3.1c machine consumption
**Target:** PLAN-04
**What:** The plan specifies field-provenance.md (markdown table, NOT Pydantic) as the primary output. The 3.1c conditional entry protocol then needs to consume phase_entry_mode from this. But 3.1c is a code-heavy phase building evaluation infrastructure — it will need to parse structured data, not markdown tables.
**Why:** Markdown tables are human-readable but machine-hostile. If 3.1c needs to programmatically determine which schema fields are available and which are deferred, parsing a markdown table is error-prone.
**How:**
1. Keep field-provenance.md as the human-readable artifact, but add a companion field-provenance.json (same data, JSON format) as a secondary output in Task 1's done criteria.
2. In Task 2's 3.1c entry protocol step, specify that phase_entry_mode is written to a simple JSON file (e.g., phase-entry.json with fields: mode, available_tracks, deferred_items) that 3.1c can load without parsing markdown.
**Impacts:** Plan 05 Task 1 and Task 2 done criteria, 3.1c plan consuming these outputs
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4 — Dual-format output is standard practice
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — The consumption problem exists regardless of prior passes
**Classification:** structural
**Adversarial verdict:** CONFIRM (Schema Synthesis & Downstream Handoff) — correct pattern; .json is authoritative source, .md generated from it or maintained alongside

### P1-IMP-19: Contradiction analysis must gate on artifact existence, not time budgets
**Target:** PLAN-04
**What:** Contradiction analysis for pair (1) must gate on artifact existence before attempting analysis, not on a wall-clock time budget.
**Why:** A time cap is unenforceable in a plan task. If both upstream artifacts for pair (1) are absent, any analysis is fabrication. A pre-analysis artifact gate prevents wasted effort and prevents hallucinated contradiction resolutions from polluting field-provenance.
**How:**
1. At the start of the contradiction analysis task, add an artifact-existence check for each pair:
   - Pair (1): requires Plan 01 execution log AND Plan 02 verdict-final.json
   - Pair (2): requires Plan 03 output AND Plan 04 output
   - Pair (3): requires Plan 01 AND Plan 03 outputs
2. If a pair's required artifacts are absent, mark it `status: skipped, reason: upstream_missing` in a contradictions-summary.json and move to the next pair. Do not attempt analysis.
3. If artifacts exist but contradict without resolution path, mark `status: unresolvable, escalate: human` — this surfaces in phase-entry.json as a flag for 3.1c.
4. Remove the equal-time-allocation assumption entirely; analysis depth is now determined by artifact completeness, not time budget.
**Impacts:** Plan 05 Task 1 time allocation, potentially affects session estimate
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3 — Triage-gated analysis is known but the specific contradiction pairs are novel
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Time allocation issue in original plan design
**Classification:** structural
**Adversarial verdict:** ENHANCE (Schema Synthesis & Downstream Handoff) — time caps are unenforceable in LLM workflows; artifact-existence gates are deterministic

### P1-IMP-20: Unobserved Phenomena entries need a concrete REJECT example and reject criterion
**Target:** PLAN-04
**What:** The plan specifies per-item structure with fields (a)-(f) for unobserved phenomena, and CONTEXT mentions REJECT/ACCEPT patterns. But the plan does not include a concrete example of what a REJECT looks like.
**Why:** Without a REJECT example, the executor has no calibration for the quality bar. An uncalibrated list will either be too permissive (including unmeasurable items that waste future planning time) or too conservative. Calibration without a REJECT example is a known failure mode for LLM-driven quality gates — the model anchors to the ACCEPT structure and produces low-quality entries that technically satisfy the format.
**How:**
1. In Task 2's Unobserved Phenomena step, add one concrete REJECT example inline: e.g., "REJECT: 'Agent creativity' — (c) measurement difficulty: impossible with current infrastructure, (e) no falsifiable question possible, (f) no evidence anchor exists. Rejected because no target phase can resolve measurement difficulty."
2. Add an explicit reject criterion: if field (c) is "impossible" AND field (e) cannot be stated, the item is rejected with a one-line reason.
**Impacts:** Plan 05 Task 2 action quality
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4 — Pre-registration with reject criteria is established practice
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Quality calibration gap in original plan
**Classification:** structural
**Adversarial verdict:** CONFIRM (Schema Synthesis & Downstream Handoff) — directly relevant to downstream 3.1c quality; prevents noise propagation

### P1-ADV-31: Rubric-freeze gate between Plan 02 Task 3 and Plan 03 Phase 1
**Target:** PLAN-03
**What:** Insert a rubric-freeze gate between Plan 02 Task 3 (rubric revision) and Plan 03 Phase 1 (adversarial transcript generation). Adversarial transcript generation must not begin until the rubric version is locked.
**Why:** Adversarial transcripts (especially LLM-Flatterer) are constructed to exploit specific rubric criteria. If the rubric is revised after generation, those transcripts no longer test the current instrument — they test a superseded one. The parallel execution window in the current plan creates a silent validity gap.
**How:**
1. In Plan 03 Phase 1 preconditions, add: "REQUIRES rubric-version.lock file created by Plan 02 Task 3 final step."
2. Plan 02 Task 3 final step emits rubric-version.lock containing: rubric file hash, date, version tag.
3. Plan 03 Phase 1 reads rubric-version.lock on entry; if absent, halt with error "Rubric not frozen — complete Plan 02 Task 3 first."
4. LLM-Flatterer generation step explicitly loads the locked rubric version and generates against its criteria.
5. If rubric is later revised (post-lock), all adversarial transcripts generated against the prior lock are marked stale and must be regenerated before validity measurement.
6. Document in plan header: "Plan 03 Phase 1 is sequentially dependent on Plan 02 Task 3 completion. Do not parallelize."
**Impacts:** Plan 02 Task 3, Plan 03 Phase 1, execution sequencing
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented
**Origin:** ADVERSARIAL — Created by LLM Evaluation Protocol Rigor lens as REFRAME of P1-IMP-10
**Classification:** structural
**Adversarial verdict:** CONFIRM (ADV Validation) — passes all 4 gates; concrete sequencing constraint

## Post-Review Synthesis

### P1-SYN-01: Unified JSON Schema Convention for Inter-Plan Data Contracts
**Target:** CONTEXT
**What:** P1-IMP-03 (baseline-before.json schema), P1-IMP-18 (field-provenance .json for 3.1c), P1-IMP-17 (smoke test derived from field-provenance), and P1-IMP-01 (corpus element structure validation) all independently introduce JSON-based data contracts at plan boundaries. There is no shared convention for how these schemas are defined, versioned, or validated.
**Why:** Without a unified convention, the four independently-created JSON contracts will use inconsistent key naming, nesting, and validation approaches. Plan 04 smoke tests (IMP-17) need to consume Plan 00 output (IMP-03) and Plan 04 field-provenance (IMP-18), but nothing ensures these are structurally compatible. A single schema convention prevents N-squared integration bugs across plans.
**How:** 1. Define a shared schema convention in CONTEXT.md Session 0 prerequisites: required top-level keys ($.meta with version, plan_id, timestamp; $.data with plan-specific payload), naming convention (snake_case), and a JSON Schema draft-07 template. 2. Add a validate_schema(path, expected_plan_id) utility to the Session 0 preflight (alongside validate_corpus from IMP-01) that checks any inter-plan JSON artifact against the convention before downstream consumption. 3. Update IMP-03, IMP-17, and IMP-18 descriptions to reference this convention as a constraint.
**Impacts:** PLAN-00, PLAN-04, downstream 3.1c ingestion
**Components:** P1-IMP-01, P1-IMP-03, P1-IMP-17, P1-IMP-18
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** PLAN-00, PLAN-04
**Depends on items:** P1-IMP-01, P1-IMP-03, P1-IMP-17, P1-IMP-18
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
**Origin:** genuine
**Classification:** structural
**Adversarial verdict:** ENHANCE (ADV Validation) — added missing depends_on_plans and depends_on_items metadata

### P1-CSC-01: Negative Control Halt Requires Defined Recovery Path to Plan 00
**Target:** PLAN-01
**What:** P1-IMP-05 adds a BLOCKING halt when a true positive appears in the negative control (safe contract). If triggered, Plan 01 stops entirely, but there is no defined path to diagnose whether the fault lies in the counting policy (Plan 00, IMP-07), the corpus element classification (Plan 00, IMP-01), or the detection logic itself.
**Why:** The BLOCKING halt is correct — a TP on a negative control invalidates the entire metric delta measurement. But the sprint has a fixed time budget. If the halt fires and the operator must manually trace the root cause across Plan 00 artifacts, the sprint stalls. A pre-defined triage checklist turns the halt into a 15-minute diagnosis rather than a multi-hour investigation.
**How:** 1. Add a "Negative Control Halt Recovery" subsection to Plan 01 that specifies a three-step triage: (a) re-run counting policy rules from IMP-07 against the flagged finding to check for counting error, (b) verify corpus element classification from IMP-01 confirms the contract is genuinely safe, (c) if both pass, escalate as a true detection false-positive requiring pattern fix before retry. 2. Each triage step must produce a one-line verdict logged to the session artifact so the retry has causal context.
**Impacts:** PLAN-01, PLAN-00
**Trigger:** P1-IMP-05
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** no
**Depends on items:** P1-IMP-05, P1-IMP-07, P1-IMP-01
**Status:** implemented
**Source:** Post-review synthesis (cascade)
**Classification:** structural
**Adversarial verdict:** ENHANCE (ADV Validation) — added missing depends_on_items metadata

## Convergence

Pass 1: 0% cosmetic (0/23)
Structural: 23 | Cosmetic: 0
Threshold: 90% (novelty: genuinely_new_territory)
Signal: ACTIVE
