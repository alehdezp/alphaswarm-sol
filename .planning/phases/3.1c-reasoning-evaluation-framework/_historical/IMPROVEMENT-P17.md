# Improvement Pass 17

<!--
  Improvement File Template
  =========================
  Full documentation: @references/improvement-file-guide.md
  Classification formulas: @references/pipeline-classification.md

  When adding new statuses, update references/pipeline-classification.md (single source).
-->

**Pass:** 17
**Date:** 2026-02-25
**Prior passes read:** 1-16 (via IMPROVEMENT-DIGEST.md)
**Status:** complete

<!-- File-level status: complete (all 14 items terminal: 10 implemented, 2 reframed, 1 not-needed CSC-03 absorbed into CONTEXT Plan 07 summary) -->

## Pipeline Status

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 0 | 0 | — |
| Research | 0 | 0 | — |
| Gaps | 0 | 13 | — |
| Merge-ready | 14 | 0 | — |

**Pipeline:** [discuss] done → [improve] done → [pre-impl] — → [research] — → [implement] pending
**Next recommended:** /msd:implement-improvements 3.1c

## Adversarial Lenses

| Lens | Brief | Items | Attack Vector |
|------|-------|-------|---------------|
| Heuristic Invalidation Cascade | Both items downstream of 3.1e NONE validity finding. Tension: "NONE for ranking" vs "no utility at all" | P17-IMP-01, P17-IMP-06 | Does "NONE validity for rank-preservation" actually mean "no value for any purpose" — or overclaiming invalidation scope? |
| Execution Model Constraint Discovery | Both items from claude -p nested session restriction. IMP-02 captures mechanical restriction; IMP-04 elevates self-evaluation consequence | P17-IMP-02, P17-IMP-04 | 3.1e GO verdict (2.5/2.5) achieved WITH self-evaluation — does this weaken rather than strengthen the case for IMP-04? |
| 3.1e Data Integration | Three items absorbing 3.1e artifacts into 3.1c. Tension: data is preliminary (synthetic_preliminary, INCONCLUSIVE) | P17-IMP-03, P17-IMP-05, P17-IMP-07 | Should 3.1c lock in 3.1e's 35 fields as canonical when Track B is only synthetic_preliminary? |

## Improvements

### P17-IMP-01: Heuristic Scoring Path Must Be Demoted to Structural Proxy Only
**Target:** CONTEXT
**What:** CONTEXT.md "heuristic + LLM dual scoring path" language overstates heuristic contribution as independent evaluation. 3.1e Plan 03 establishes NONE validity for ranking signal across all 7 heuristic dimensions. The dual-path framing must be corrected before Plan 07 implementation begins, but the scope of invalidation must be accurately bounded.
**Why:** Uncorrected dual-path framing will cause Plan 07 to build heuristic scoring infrastructure aimed at producing evaluation outputs — which 3.1e proves cannot be valid. However, overclaiming "no utility for any purpose" risks stripping legitimate structural health-check uses (anti-fabrication triggers, zero-query guards), which are not ranking operations and were not tested by 3.1e Plan 03.
**How:**
1. Add a locked decision addendum to CONTEXT.md under the Reasoning Evaluation section: "3.1e-03 Finding: Heuristic dimensions have ZERO validity as ranking signal vs LLM evaluation. Heuristics are demoted to structural proxy role only — pipeline health checks, anti-fabrication guards, and fast-fail gates. They MUST NOT contribute to evaluation scores."
2. In the research baseline "dual scoring path" description, rewrite to "LLM primary path with structural heuristic guards — heuristics do not score, they gate."
3. In Plan 07 gate language, replace any reference to heuristic scoring contributing to evaluation output with "heuristics trigger structural alerts only; score computation is LLM-only."
4. Add a one-line comment in each affected section citing "3.1e-03 empirical basis" so future reviewers can trace the decision.
**Impacts:** Plan 07 (Reasoning Evaluator) — changes the fallback path in the permission gates; Plan 01 (Data Structures) — DimensionScore fields that aggregate heuristic+LLM should be separated cleanly.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Heuristic Invalidation Cascade):** Invalidation scope bounded to ranking signal. Heuristic structural guard uses (anti-fabrication, zero-query detection) explicitly preserved — 3.1e did not test these non-ranking use cases.

### P17-IMP-02: claude -p Nested Session Restriction Must Be Captured as a Hard Constraint
**Target:** CONTEXT
**What:** CONTEXT.md Plan 07 summary (lines 2222-2308) specifies "_llm_evaluate_dimension() via claude -p" as the implementation mechanism. The Execution Architecture section (lines 2848-2946) does not mention the nested session restriction. 3.1e Plan 02 discovered that claude -p cannot be called from within a Claude Code subagent session (nested session restriction).
**Why:** Plan 07 tasks will attempt to implement claude -p invocation and hit this restriction immediately. This is not a minor implementation detail — it changes the fundamental mechanism. Without capturing this as a constraint, implementors will design the wrong interface, write the wrong code, and discover the problem at execution time.
**How:**
1. In CONTEXT.md Architecture section (lines 2848-2946), add to Constraints or Assumptions: "claude -p CANNOT be invoked from within subagent sessions (nested session restriction, confirmed 3.1e Plan 02). LLM evaluation must either: (a) be invoked from the top-level CC orchestrator session, or (b) use Python subprocess calling claude CLI from outside the agent context, or (c) use direct Anthropic API calls from Python. The implementation path (b) or (c) must be validated before Plan 07 task implementation begins."
2. In Plan 07 summary (lines 2222-2308), replace "_llm_evaluate_dimension() via claude -p" with "_llm_evaluate_dimension() via [subprocess/API TBD — claude -p nested restriction applies, see Architecture Constraints]" and add a Validation Phase 0 gate: "Confirm LLM invocation mechanism (subprocess vs API) with a real call before implementing remaining tasks."
**Impacts:** Plan 07 (Reasoning Evaluator) — changes invocation mechanism design; Plan 02 (transcript collection) — affects how evaluation is triggered post-collection.
**Research needed:** no — the restriction is confirmed empirically; the implementation path requires a one-step feasibility check.
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Execution Model Constraint Discovery):** Confirmed — empirically validated by 3.1e, directly causes wrong-interface failure in Plan 07. No duplication with other items.

### P17-IMP-03: Plan 01 Schema Must Reference 3.1e Fields With Tier-Aware Stability
**Target:** CONTEXT
**What:** Plan 01 defines ~30+ types pre-experiment. 3.1e Plan 04 produced 35 fields across three stability tiers: Track A (17 fields, deterministic/stable), Track B (7 fields, synthetic_preliminary — validity INCONCLUSIVE, subject to revision), Track C (11 fields, heuristic-derived). Current Plan 01 schema definition references neither this empirical set nor the layer-qualified naming convention (heuristic_ prefix vs llm_ prefix).
**Why:** Without tier-aware reference, implementors treat all 35 fields as equally stable. Track B fields may shift when real transcripts replace synthetic ones; freezing them now embeds a bias source. Layer-qualified naming is load-bearing: heuristic_ fields drive structural proxies (P17-IMP-01 scope), llm_ fields drive evaluator inputs — conflating them breaks the two-tier evaluation architecture.
**How:**
1. In Plan 01 CONTEXT.md schema section, add a "Field Stability Tiers" subsection referencing 3.1e Plan 04 output: Track A fields are stable and MUST be implemented as specified; Track B fields are PROVISIONAL and tagged `[pending-real-transcript-validation]`; Track C fields are heuristic-derived and tagged `[structural-proxy]`.
2. Enforce layer-qualified naming convention as a hard constraint for all 35 fields (heuristic_ prefix for Track C + structural proxies, llm_ prefix for evaluator-facing fields).
3. Add a note: Track B field stability gates on real transcript GO confirmation (see P17-IMP-07 deferred item 1) — implementations depending on Track B fields must not be marked DONE until that gate clears.
4. Do NOT lock Track B field shapes as canonical until 3.1e validity re-scoring is complete.
**Impacts:** Plan 01 (Data Structures) — constrains implementation with stability tiers rather than hard lock.
**Research needed:** no — 3.1e Plan 04 is the source of truth.
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (3.1e Data Integration):** Original item conflated "reference" with "lock as canonical." Reframed to three-tier stability model: Track A stable, Track B provisional, Track C structural-proxy. Layer-qualified naming still enforced as hard convention.
**Reframed into:** P17-ADV-3-01

### P17-IMP-04: Evaluator Independence Assumption Must Be Documented as Architectural Caveat
**Target:** CONTEXT
**What:** CONTEXT.md's dual-Opus framing embeds an independence assumption (two evaluators, separate sessions) that the in-session workaround technically violates. 3.1e operated under this constraint and was declared GO — but the assumption is undocumented, making future readers unable to assess when the workaround is safe.
**Why:** Architectural assumptions that are silently violated create hidden validity risk. The violation is not proven to cause bias (3.1e found no evidence of inflation), but the assumption must be documented so future phases can recognize when the violation becomes material — for example, when evaluator and executor share the same conversation thread on a single contract with strong recency effects.
**How:**
1. In CONTEXT.md architecture section, add a callout: "Evaluator Independence Caveat — In-session evaluation (required when claude -p is unavailable) violates the strict session-isolation assumption of dual-Opus design. 3.1e empirically validated this workaround under three-instrument cross-check. Flag for re-evaluation if: (a) single-evaluator mode is used without cross-check, or (b) evaluator and executor operate on the same contract in the same thread."
2. In Plan 07 Phase 0, add a documentation step (not a blocking gate): record which evaluation mode is active (isolated vs in-session) and attach to the run artifact.
3. Do NOT add gate 0c as a blocking prerequisite — route to a monitoring annotation instead.
4. In Gate 6 validity precondition, add: "If in-session evaluation was used, confirm three-instrument cross-check was applied; if not, flag result as provisional."
**Impacts:** Plan 07 (Reasoning Evaluator) — adds documentation step; Exit Gates — Gate 6 gets provisional flag for unverified independence.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Execution Model Constraint Discovery):** Original claimed HIGH-confidence that "scores will be inflated" — but 3.1e achieved GO at 2.5/2.5 under self-evaluation conditions with no evidence of inflation. Reframed from blocking gate to documented caveat + monitoring annotation. The independence assumption is real and should be documented; the causal claim of bias is not empirically supported.
**Reframed into:** P17-ADV-2-01

### P17-IMP-05: FP Taxonomy Corpus Dominance Bias Must Constrain Exit Gate 7
**Target:** CONTEXT
**What:** Exit Gate 7 requires "calibrated with 30+ transcripts" but contains no corpus composition requirement. 3.1e empirical finding: trivial_structural_match dominates at dominance_ratio=0.836 across the synthetic corpus. A calibration run meeting the 30-transcript count on a similarly skewed corpus will produce a scorer optimized for the dominant class and systematically under-calibrated for the other 4 FP clusters.
**Why:** Gate 7 as written is a count gate, not a validity gate. A biased scorer can pass it trivially. The downstream consequence is that Dual-Opus evaluator calibration will embed the corpus skew as a baseline, causing the 15-point disagreement threshold to be tuned against a non-representative distribution. This is a structural validity defect, not a calibration tuning issue.
**How:**
1. Add to Gate 7 a "Corpus Composition Audit" sub-requirement: before calibration run begins, compute per-cluster transcript counts across the 5 FP taxonomy clusters from 3.1e.
2. Set a hard stratification floor: no single cluster may represent > 60% of the calibration corpus (vs observed 83.6%). If floor is violated, calibration is blocked until corpus is augmented.
3. Set a minimum per-cluster floor of 3 transcripts for non-dominant clusters.
4. Document dominance_ratio (dominant_cluster_count / total_count) as a named gate metric in Gate 7 criteria.
5. Cross-reference P17-IMP-07 deferred item 2 (validity re-scoring): if re-scoring changes cluster distribution, Gate 7 corpus audit must re-run.
6. Note: stratification is mitigation for corpus skew, not a fix for underlying validity uncertainty — Track B fields driving cluster assignments remain provisional until real transcripts confirm them.
**Impacts:** Exit Gates (Gate 7) — adds stratification requirement with concrete thresholds.
**Research needed:** no
**Confidence:** HIGH (upgraded from MEDIUM — dominance_ratio is a quantified finding, not a hypothesis)
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (3.1e Data Integration):** Enhanced with concrete thresholds (>60% cap, 3 minimum per non-dominant cluster) and dependency link to IMP-07 item 2. Stratification is mitigation, not cure.

### P17-IMP-06: Plan 07 Fallback Gate Language Is Wrong — Heuristic-Only Is Not a Valid Fallback
**Target:** CONTEXT
**What:** Plan 07 fallback gate specifies "reduce to heuristic-only" when dual-evaluator reliability fails. 3.1e Plan 03 establishes heuristics have NONE validity as ranking signal, making this fallback produce zero-signal scores that superficially resemble valid evaluation outputs.
**Why:** A zero-signal score with normal formatting is epistemically worse than an explicit unavailability flag: downstream consumers (regression detectors, exit gates) will treat it as real signal. The false confidence problem is not theoretical — any consumer that thresholds on the score will make decisions on noise. The correct fallback hierarchy must degrade gracefully: dual-evaluator (normal) -> single-evaluator with uncertainty flag (degraded) -> evaluation_unavailable sentinel (failed).
**How:**
1. Locate the fallback specification in Plan 07 Deliverable 9c (Lightweight Permission Gates).
2. Replace the "reduce to heuristic-only" clause with a three-tier fallback chain: (a) primary: dual-evaluator consensus; (b) degraded: single-evaluator LLM with `uncertainty_flag=True` and score confidence tagged LOW; (c) failed: emit `evaluation_status: unavailable` sentinel — no score field, block any downstream gate that requires a score.
3. Add explicit prohibition: "heuristic-only is NOT a valid fallback tier. Heuristics may accompany any tier as structural guards but MUST NOT substitute for evaluation score."
4. Update any exit gate in Plan 07 that references the fallback to handle the `evaluation_unavailable` sentinel explicitly (treat as "cannot confirm pass" rather than "fail" to avoid penalizing infrastructure failures).
5. Cite "3.1e-03 empirical basis: NONE validity for ranking signal" in the updated section.
**Impacts:** Plan 07 (Reasoning Evaluator) — changes fallback from heuristic scoring to degraded-LLM + unavailable sentinel.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Heuristic Invalidation Cascade):** Enhanced with three-tier fallback chain (dual -> single+uncertainty -> unavailable sentinel). Original only covered two tiers. Exit gate handling of sentinel prevents infrastructure failures from generating false regression signals.

### P17-IMP-07: 5 Deferred 3.1e Items Need Explicit Capture as 3.1c Entry Constraints
**Target:** CONTEXT
**What:** 5 items explicitly deferred from 3.1e to 3.1c have no corresponding assignments in CONTEXT.md: (1) real transcript GO confirmation — gates Track B field stability; (2) validity re-scoring — re-runs scoring once real transcripts replace synthetic corpus; (3) bridge transformer (~150 LOC, non-trivial code artifact); (4) self-evaluation check — architectural constraint; (5) construct disambiguation — affects Plan 01 schema.
**Why:** Item 3 (bridge transformer) is a code deliverable that must appear in a specific plan's task list, not a design note. Item 1 gates Items 2 and 3 — executing 2 or 3 before 1 is confirmed wastes implementation effort on provisional field shapes. Item 5 (construct disambiguation) directly affects Plan 01 schema and must be resolved before implementors finalize type definitions.
**How:**
1. Add a "3.1e Deferred Items" section to CONTEXT.md with ordered dependency chain: Item 1 (real transcript GO confirmation) -> Item 2 (validity re-scoring) -> Item 3 (bridge transformer). Item 4 (self-evaluation check) is parallel. Item 5 (construct disambiguation) must precede Plan 01 schema finalization.
2. Assign each item to a specific plan: Item 1 -> Plan 02 as GATE task; Item 2 -> Plan 02 as dependent task after Item 1; Item 3 -> Plan 05 or 06 as required deliverable; Item 4 -> Plan 01 or Plan 09; Item 5 -> Plan 01 as schema pre-condition.
3. Mark Items 1 and 3 as Track B prerequisites: "Track B field implementations MUST NOT be finalized until Item 1 GO confirmation is received."
4. Add NO-GO handling: if Item 1 returns NO-GO, Track B fields revert to PROVISIONAL status and plans depending on them must be re-scoped.
5. Verify proposed plan assignments do not conflict with existing task scope before committing.
**Impacts:** Plan 01, Plan 02, Plan 05/06 — adds required scope with explicit dependency ordering.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (3.1e Data Integration):** Enhanced with concrete plan mappings, dependency ordering (1->2->3, 4 parallel, 5 before Plan 01), and NO-GO handling note. Original proposed direction without content.

### P17-ADV-2-01: Evaluator Independence Caveat With Monitoring (Reframe of P17-IMP-04)
**Target:** CONTEXT
**What:** Document the evaluator independence assumption gap as an architectural caveat with monitoring annotation. In-session evaluation technically violates the dual-Opus independence assumption, but 3.1e found no evidence of bias under three-instrument cross-check. The caveat ensures future phases can recognize when the violation becomes material without blocking current implementation.
**Why:** The independence assumption is architecturally real but the causal claim of bias is not empirically supported. 3.1e achieved GO (2.5/2.5) under self-evaluation conditions. A blocking gate based on theoretical concern would delay implementation without empirical justification. A documented caveat with monitoring lets the framework detect if bias emerges from real data.
**How:**
1. Architecture section: "Evaluator Independence Caveat — In-session evaluation violates session-isolation assumption. 3.1e validated this under three-instrument cross-check. Re-evaluate if: (a) single-evaluator without cross-check, or (b) evaluator and executor share same thread on same contract."
2. Plan 07: documentation step (not blocking gate) — record evaluation mode (isolated vs in-session) per run.
3. Gate 6: "If in-session evaluation used, confirm three-instrument cross-check applied; if not, flag result as provisional."
**Impacts:** Plan 07 — documentation step; Gate 6 — provisional flag for unverified independence.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Origin:** Reframe of P17-IMP-04 by Execution Model Constraint Discovery lens. Separates documented caveat (confirmed) from blocking gate (not supported by evidence).

### P17-ADV-3-01: Plan 01 Schema Field Stability Tiers (Reframe of P17-IMP-03)
**Target:** CONTEXT
**What:** Reference 3.1e's 35 schema fields in Plan 01 using a three-tier stability model rather than treating all as equally canonical. Track A (17 fields): stable, implement as specified. Track B (7 fields): PROVISIONAL, tagged `[pending-real-transcript-validation]`. Track C (11 fields): heuristic-derived, tagged `[structural-proxy]`. Layer-qualified naming (heuristic_ vs llm_ prefix) enforced as hard convention across all tiers.
**Why:** Track B is synthetic_preliminary with INCONCLUSIVE validity. Locking these 7 fields as canonical now creates premature freeze risk — they may change when real transcripts are available. The stability tier model prevents divergence without premature canonicalization while still enforcing the load-bearing naming convention.
**How:**
1. Add "Field Stability Tiers" subsection to Plan 01 CONTEXT.md referencing 3.1e Plan 04.
2. Track A: stable, MUST implement as specified. Track B: PROVISIONAL, tagged. Track C: structural-proxy, tagged.
3. Layer-qualified naming as hard constraint for all tiers.
4. Track B stability gates on P17-IMP-07 deferred item 1 (real transcript GO confirmation).
5. Do NOT lock Track B field shapes until validity re-scoring complete.
**Impacts:** Plan 01 — schema with stability awareness.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Origin:** Reframe of P17-IMP-03 by 3.1e Data Integration lens. Separates "reference the fields" (confirmed) from "lock as canonical" (premature for Track B).

### P17-SYN-01: Framework Lacks Explicit Validity Model Separating Proxy Signals from Validity Claims
**Target:** CONTEXT
**What:** P17-IMP-01 (heuristic demotion) and P17-ADV-3-01 (schema stability tiers) independently converged on the same finding: the framework contains signals documented as evaluation scores that are actually structural proxies with no validity claim. No explicit validity model declares what each signal claims to measure, what evidence confirms it, and how consumers should interpret it.
**Why:** Without a shared validity vocabulary, each plan independently decides signal interpretation — leading to inconsistency, silent score misuse in exit gates, and difficulty extending the framework. Two independent review groups converging on this from different angles (scoring vs schema) indicates the gap is load-bearing.
**How:**
1. Add "Signal Validity Vocabulary" to Implementation Decisions (Locked): three classes — VALIDITY_CLAIM (asserts measurable quality, must cite evidence), STRUCTURAL_PROXY (pipeline routing/guard, not ranking), PROVISIONAL (under validation, cannot gate decisions).
2. Annotate each Plan 01 scored field against these classes, using Track A/B/C as starting classification.
3. Add validity class annotation to exit gate threshold references.
**Impacts:** Plan 01 (schema), Plan 07 (evaluator output), exit gate criteria.
**Components:** P17-IMP-01, P17-ADV-3-01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)

### P17-CSC-01: Exit Gate Criteria Reference Heuristic Thresholds Now Demoted to Proxy-Only
**Target:** CONTEXT
**What:** After P17-IMP-01 demotion, exit gate thresholds using heuristic scores as pass/fail become invalid — silently passing on meaningless ranking signal.
**Why:** An exit gate passing on a demoted signal gives false confidence that quality was measured.
**How:** Audit exit gate for heuristic-derived thresholds; replace with non-heuristic equivalents or mark as STRUCTURAL_PROXY_GUARD.
**Impacts:** Exit gate, Plan 01
**Trigger:** P17-IMP-01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Source:** Post-review synthesis (cascade)

### P17-CSC-02: Gate 7 Stratification Degrades Silently Without Corpus Maintenance Contract
**Target:** CONTEXT
**What:** P17-IMP-05's stratification constraint (>60% cap) only holds at initial construction. No corpus maintenance guidance exists — future additions will violate it silently.
**Why:** Constraint enforced at construction but not addition creates degrading corpus. Phases 3.1f and 3.2 will break it first.
**How:** Add "Corpus Maintenance Contract" to Infrastructure Available: check stratification invariant before any corpus addition.
**Impacts:** Plan 07 (Gate 7), phases 3.1f and 3.2
**Trigger:** P17-IMP-05
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Source:** Post-review synthesis (cascade)

### P17-CSC-03: Fallback Tier Provenance Unrecorded — Exit Gate Cannot Distinguish Quality Levels
**Target:** PLAN-07
**What:** P17-IMP-06's three-tier fallback produces outputs from different quality levels but tier provenance is not recorded. Exit gate cannot distinguish dual-evaluator from sentinel-padded results.
**Why:** Without tier logging, the fallback becomes quality-masking rather than transparency mechanism.
**How:** Add `evaluator_tier_used` field (DUAL/SINGLE_WITH_UNCERTAINTY/UNAVAILABLE_SENTINEL); exit gate distribution check (flag if UNAVAILABLE_SENTINEL >10% or DUAL <70%).
**Impacts:** Plan 07, exit gate
**Trigger:** P17-IMP-06
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** open
**Source:** Post-review synthesis (cascade)

### P17-CSC-04: IMP-07 Dependency Chain Not Reflected in Execution Waves Section
**Target:** CONTEXT
**What:** P17-IMP-07's dependency chain (items 1->2->3, item 5 before Plan 01) conflicts with the Execution Waves section which doesn't account for these items.
**Why:** Two authoritative scheduling sources diverge — item 5 may not be scheduled before Plan 01.
**How:** Update Execution Waves to incorporate deferred items at correct wave positions; add reconciliation note.
**Impacts:** All 12 plans (ordering), Plan 01 specifically (item 5 dependency)
**Trigger:** P17-IMP-07
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 0
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Source:** Post-review synthesis (cascade)

## Convergence

Pass 17: 0% cosmetic (0/14)
Structural: 14 | Cosmetic: 0
Threshold: 80% (novelty: default)
Signal: ACTIVE

All 14 items are structural, driven by 3.1e empirical data. This is a cross-phase alignment pass — cosmetic items are out of scope by design.
