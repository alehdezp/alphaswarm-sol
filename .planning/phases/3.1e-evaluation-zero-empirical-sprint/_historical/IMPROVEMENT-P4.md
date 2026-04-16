# Improvement Pass 4 — Phase 3.1e: Evaluation Zero Empirical Sprint

**Pass:** 4
**Date:** 2026-02-23
**Prior passes read:** 1, 2, 3 (via IMPROVEMENT-DIGEST.md + archived passes)
**Areas analyzed:** 7 (Session 0 & Measurement Foundation, Plan 01 Detection Metric Sensitivity, Plan 02 LLM Evaluation Architecture, Plan 03/04 Evaluator Assessment, Plan 05 Schema Extraction, AlphaSwarm Strategic Alignment, Novel Approaches & Cross-Plan Gaps)
**Agent count:** 7 improvement agents + 7 adversarial reviewers
**Status:** complete

## Pipeline Status

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 0 | 0 | — |
| Research | 0 | 0 | — |
| Gaps | 0 | 2 (done) | — |
| ADV unvalidated | 1 | 6 | P4-ADV-8-01 (new, needs validation) |
| Merge-ready | 38 | 0 | — |
| Rejected | — | 2 | — |
| Reframed | — | 10 | — |

**Pipeline:** `[discuss] ✓ → [improve] ✓ → [resolve] ~ → [implement] — → [plan] —`

**Deduplication log:**
- Dedup: kept P4-IMP-27 (Strategic IMP-01, multi-agent debate), dropped Novel IMP-04 (same topic, less comprehensive). Merged Novel IMP-04's Plan 02 connection into P4-IMP-27 How steps.
- Dedup: kept P4-IMP-37 (Novel IMP-07, synthetic-vs-real Phase A/B), dropped Plan 02 IMP-06 (same topic — IMP-06 said remove hedge, IMP-37 adds Phase A/B structure which is more actionable).

**Verdict summary:** 11 confirmed, 16 enhanced, 9 reframed, 2 rejected, 10 created (ADV items)
**Net actionable:** 39 original - 2 rejected - 9 reframed + 10 created = 38 actionable items
**Unreviewed:** 1 (P4-IMP-03 — not assigned to any adversarial lens)

## Adversarial Lenses

| # | Lens | Items | CONFIRM | ENHANCE | REFRAME | REJECT | CREATE |
|---|------|-------|---------|---------|---------|--------|--------|
| 1 | Session 0 Integrity | 01,02,04,05,06 | 2 | 2 | 1 | 0 | 1 |
| 2 | Plan 01 Experimental Rigor | 07,08,09,10 | 1 | 2 | 1 | 0 | 2 |
| 3 | Plan 02 Statistical Design | 11,12,13,14,15 | 1 | 2 | 2 | 0 | 2 |
| 4 | Plan 03/04 Threshold Coherence | 16,17,18,19,20,21 | 3 | 1 | 2 | 0 | 2 |
| 5 | Plan 05 Dependency & Quality | 22,23,24,25 | 1 | 2 | 1 | 0 | 1 |
| 6 | Strategic Alignment | 26,27,28,29,30,31,32,33 | 3 | 3 | 1 | 1 | 1 |
| 7 | Cross-Plan Novel Gaps | 34,35,36,37,38,39 | 0 | 4 | 1 | 1 | 1 |
| | **Total** | **38** | **11** | **16** | **9** | **2** | **10** |

**Cross-group conflicts resolved:**
- IMP-11 vs IMP-13 (incompatible go/no-go): resolved by P4-ADV-3-01 (three-instrument model)
- IMP-15 vs IMP-11 (variance on wrong instrument): resolved by P4-ADV-3-02
- IMP-34 duplicates IMP-20: IMP-34 rejected
- IMP-36 + IMP-39 tightly coupled: must implement together

## Improvements

### P4-IMP-01: Session 0 task (a) cache-independence requirement is solving a non-problem for baseline recording
**Target:** CONTEXT
**What:** Session 0 task (a) specifies "build graphs explicitly outside pytest cache lifecycle (not via pytest `_graph_cache`)." The `_graph_cache` at `tests/evaluation/test_detection_baseline.py:267` is a module-level Python dict -- it exists only within a single Python process. Running the baseline recording as a standalone script already runs outside pytest. The cache confound was legitimate for Plan 01 Outcome A (two runs in same pytest session), but Session 0 task (a) is a one-shot baseline recording, not a reproducibility test.
**Why:** The instruction adds implementation confusion without solving a real problem. Session 0 task (a) records a baseline -- it runs once. The cache concern applies to Plan 01 Outcome A, which is already addressed there.
**How:**
1. In Session 0 task (a), replace "build graphs explicitly outside pytest cache lifecycle" with "Run as standalone script (not via pytest). Build graphs via `VKGBuilder.build()` and run `build_lens_report()` directly."
2. Move cache-independence requirement to Plan 01 Outcome A only.
**Impacts:** Session 0 task (a) clarity. No impact on Plan 01.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** cosmetic
**Status:** implemented
**Adversarial note (Session 0 Integrity):** Withstands the "adding decision points" test — this REMOVES a pseudo-requirement rather than adding one. The replacement instruction is shorter, more concrete, and directly actionable. No hidden assumption about how the graph cache works is introduced. Executor time saved: ~30 seconds of confusion per re-read.

### P4-IMP-02: Transcript provenance pre-task is verifiable right now -- directory is empty (no .gitkeep)
**Target:** CONTEXT
**What:** Session 0 pre-task allocates 5 minutes to check `.vrs/observations/calibration/` for non-`.gitkeep` content. The directory is completely empty — no `.gitkeep`, no files. Assumption 3 states the directory "contains only `.gitkeep`" which is false in detail; git does not track empty directories. The provenance question (fabricated-and-deleted vs never-committed) resolves to "never committed" — verifiable by a single git log call that can be run now, not during Session 0.
**Why:** Spending 5 session minutes confirming something already confirmed before the session is waste against a 95-minute budget. The pre-task's value was resolving an ambiguity about whether transcripts ever existed. That ambiguity is already resolved by filesystem inspection.
**How:**
1. Update Assumption 3 to: "`.vrs/observations/calibration/` is an empty directory with no `.gitkeep`. Git does not track it. `git log --all -- .vrs/observations/calibration/` returns empty — directory was never committed. Transcripts never existed in version control."
2. Remove the pre-task as a time-boxed task. Replace with a VERIFICATION NOTE in Session 0 header: "Confirm: `ls .vrs/observations/calibration/` is empty. If any file appears, escalate — this assumption is violated. Expected: empty. Time: 10 seconds."
3. Reduce from 5 min to 0 min (pre-confirmed). Reallocate freed 5 min as buffer for task (a) overflow.
**Impacts:** Session 0 time budget gains 5 minutes. Assumption 3 becomes more precise.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Session 0 Integrity):** The original proposal reduced from 5 to 2 minutes. The correct answer is 0 minutes — the pre-task degenerates to a single-line verification that belongs in session pre-flight, not as a named task. A 2-minute task with `git log` still implies the executor must decide what to do with the output. Pre-confirming the assumption text now eliminates the decision entirely. The freed 5 minutes are more valuable applied to task (a) overflow.

### P4-IMP-03: Session 0 task (b) rubric covers only 2 dimensions -- Plan 02 needs fallback if one fails calibration
**Target:** CONTEXT
**What:** Session 0 task (b) writes rubric v1.0 for `reasoning_depth` and `evidence_quality`. Plan 02's go/no-go requires "LLM_adds_signal on >= 2 dimensions WITH REAL HEURISTIC HANDLERS." If only 2 rubrics exist and one fails calibration, Plan 02 has no fallback dimensions to test.
**Why:** Plan 02's success criterion requires >= 2 primary-tier dimensions. If Session 0 writes rubrics for exactly 2 and one fails calibration (max 3 revisions), Plan 02 is stuck with 1 dimension and cannot achieve its success criterion.
**How:**
1. In Session 0 task (b): add note "These 2 rubrics are the minimum. Plan 02 may write additional primary-tier dimension rubrics as its first action if calibration fails on one."
2. In Plan 02 preconditions: change from "rubric written" to "at least 2 rubrics written; Plan 02 may extend to additional primary-tier dimensions if needed."
3. Alternatively (preferred if time allows): write rubrics for top 3-4 primary-tier dimensions during Session 0 task (b), adjusting time from 20 to 30 min.
**Impacts:** Plan 02 viability. Session 0 time budget (if alternative chosen).
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Interrupted Review Recovery):** The item's framing targets the wrong lever. It treats "calibration failure on one dimension" as the failure mode and proposes adding a third rubric as mitigation. But the go/no-go criterion says >= 2 dimensions WITH REAL HEURISTIC HANDLERS — rubric existence and heuristic handler existence are independent gates. Option 3 (write 3-4 rubrics in Session 0) compounds Plan 02 calibration work without verifying handler eligibility. The correct fix is pre-registering a fallback dimension list with heuristic handler status verified from `reasoning_evaluator.py` source, not adding Session 0 scope. See replacement: P4-ADV-8-01.

### P4-IMP-04: Session 0 has no explicit failure mode for baseline deviation from 3.1d-05 numbers
**Target:** CONTEXT
**What:** Session 0 task (a) re-runs the pipeline because baseline has contradictions. But there is no handling for when the fresh baseline reveals DRAMATICALLY different numbers (e.g., 30 FPs instead of 65, or 4 TPs instead of 10-11). The entire phase's plan structure is built on the 3.1d-05 numbers.
**Why:** If the actual numbers deviate significantly, Plans 01 through 05 are designed against wrong data. If access-tierb-001 contributes fewer than 10 FPs, Plan 01's "measurable FP reduction" may be trivial; if total FPs are much lower than 65, Plan 03/04's taxonomy has a smaller corpus.
**How:**
1. Add to Session 0 task (a) output requirements: "Compare fresh baseline against 3.1d-05 numbers. If total FPs differ by > 30% OR access-tierb-001 FP count differs by > 5: flag 'baseline deviation' and document which plan assumptions are affected."
2. Add to Session 0 entry criteria: "If baseline deviation flagged: review Plan 01 primary test contracts and Plan 03/04 corpus size assumptions before proceeding."
**Impacts:** Plan 01 scope, Plan 03/04 corpus assumptions. Low effort addition.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Session 0 Integrity):** Withstands the cognitive-load test. This adds ONE decision point at the END of task (a), not during it. The threshold is pre-specified so the executor does not need to judge what counts as "dramatic." The human-approval gate is already a design constraint; this improvement just names the trigger condition.

### P4-IMP-05: The 95-minute budget has no slack for structured JSON output format requirement
**Target:** CONTEXT
**What:** Task (a) at 45 minutes must build 7 graphs (~10 min), run lens reports (~5 min), save raw JSON (~5 min), then for each of 65 FPs record tier_a match conditions AND none-block expected suppressions. The diagnostic annotation is ~25 seconds per FP × 65 FPs = ~27 min — leaving the budget exhausted before the overflow rule triggers at 60 min.
**Why:** The real problem is not just that the 95-minute budget is tight. It is that task (a) conflates TWO fundamentally different activities: (1) raw data collection (objective, fast, machine-assisted) and (2) per-FP diagnostic annotation (judgment-intensive, slow, human-dependent). Mixing them creates a task that cannot be interrupted cleanly because partial annotation has no defined "done" state.
**How:**
1. Split into two clearly separate tasks with distinct completion criteria:
   - **(a1) Raw baseline capture** (25-30 min, MUST): Run fresh pipeline. Save all firings as `baseline-before.json` with `{contract, pattern_id, function_name, is_tp, fired_conditions}`. Completion criterion: file exists with content. No annotation required.
   - **(a2) FP diagnostic annotation** (20 min, SHOULD — overflow to Plan 01 if needed): For each FP in baseline-before.json, add `tier_a_matched` and `none_block_expected_but_missed` fields. Completion criterion: at least UnstoppableVault and SideEntranceLenderPool annotated (the Plan 01 primary contracts). Partial completion is a valid exit state.
2. Update overflow rule: "If (a1) completes but (a2) does not: proceed to task (b). (a2) is Plan 01 first action."
3. Note: (a2) partial annotation on Plan 01 primary contracts is SUFFICIENT for Plan 01 entry criteria — full annotation of all 65 FPs is informative but not blocking.
**Impacts:** Session 0 time management. Plan 01 entry criteria unchanged.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Session 0 Integrity):** The original proposal splits into (a1) 30 min MUST and (a2) 15-20 min MAY. The rewrite sharpens the split by: (a) giving (a1) a concrete completion criterion rather than a time box, (b) specifying that partial (a2) on Plan 01 primary contracts is sufficient for Plan 01 entry, and (c) reducing the MUST time to 25-30 min to account for the 5-minute buffer gained from P4-IMP-02. The "overflow to Plan 01 first action" mechanism already exists — the improvement correctly formalizes it.

### P4-IMP-06: Session 0 counting-policy.md is mentioned in Decisions but absent from task list
**Target:** CONTEXT
**What:** The Finding Counting Policy decision states "Record in `.vrs/experiments/counting-policy.md` during Session 0." But Session 0's task table has no entry for creating this file. This is an orphaned deliverable.
**Why:** Without this, the executor may miss it entirely, and Plan 01 operates without documented counting methodology.
**How:**
1. In Session 0 task (a) output column, add: "`baseline-before.json` + `counting-policy.md` documenting per-function vs per-pattern methodology used."
2. Alternatively, absorb counting-policy.md into the baseline JSON itself as a metadata section.
**Impacts:** Session 0 task (a) completeness. Plan 01 counting clarity.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** cosmetic
**Status:** reframed
**Adversarial note (Session 0 Integrity):** The "orphaned deliverable" framing assumes the executor must produce the policy during Session 0 under time pressure. But the policy content already exists verbatim in the Decisions section. The correct intervention is to pre-generate counting-policy.md from the existing Decisions text before Session 0 runs, or absorb it into baseline JSON metadata. Framing this as a Session 0 task artifact creation problem when it is actually a pre-session artifact creation problem leads to the wrong fix. See P4-ADV-1-01 for replacement.

### P4-IMP-07: "Metric sensitivity" claim is under-scoped -- Plan 01 proves editability, not sensitivity
**Target:** CONTEXT
**What:** The Plan 01 Decisions section contains two conflicting framings. "Plan 01 Validates Metric Sensitivity" is a section heading. The body text correctly says "Plan 01 proves detection metrics are sensitive enough to distinguish good patterns from bad" — this is narrower and accurate. The damage is in the decision section heading because that heading will be read by 3.1f as a proven claim. The CONTEXT already contains the correct qualifier in the SICA note ("Plan 01 tests human-edited YAML — metric sensitivity is a necessary precondition for automated loop closure in 3.1f, not proof of automation"). So the qualifier exists but is buried in pre_research, not adjacent to the decision heading.
**Why:** The existing text has the correct qualifier in pre_research (SICA note) but not adjacent to the decision it qualifies. 3.1f will read the Decisions section, not pre_research. The mismatch between decision heading ("validates") and pre_research text ("precondition, not proof") creates an inheritance risk.
**How:**
1. In `<decisions>`, change the heading "Plan 01 Validates Metric Sensitivity, Not Loop Automation" to "Plan 01 Establishes Metric Responsiveness as Precondition — Not Sensitivity Validation."
2. Change the body of that decision: replace "Plan 01 proves detection metrics are sensitive enough to distinguish good patterns from bad" with "Plan 01 proves detection metrics are RESPONSIVE to a single-pattern fix on a known-over-firing pattern. Full sensitivity validation — that metrics distinguish degrees of improvement proportionally — requires the multi-pattern corpus in 3.1f."
3. In Plan 01 intent line: change "Prove detection metric sensitivity" to "Establish detection metric responsiveness — a necessary precondition for 3.1f, not a proof of full sensitivity."
4. No changes to pre_research (qualifier already correct there).
**Impacts:** Plan 01 scope unchanged. 3.1f inherits more honest foundation.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** creative-structural
**Status:** implemented
**Adversarial note (Plan 01 Experimental Rigor):** The original How targets intent + assumption 1, but the highest-risk location is the Decisions section heading because it is what downstream plans inherit as a named decision. The existing SICA qualifier in pre_research shows the author already knew the distinction — the fix is co-location, not invention of a new qualifier. This rewrite is stronger because it fixes the inheritance vector directly.

### P4-IMP-08: The 200 LOC scope limit is a constraint on informativeness, not just scope
**Target:** CONTEXT
**What:** Falsification criterion C says "Outcome C fails if fix requires >200 LOC (scope mis-set)." But a builder fix exceeding 200 LOC that reduces FPs across MANY patterns is not a scope error -- it is evidence the most effective intervention is at a different layer.
**Why:** The 200 LOC limit exists to prevent scope creep, which is reasonable. But the falsification criterion conflates "fix too big for this plan" with "scope mis-set." A builder fix exceeding 200 LOC that dramatically improves detection is the most informative outcome.
**How:**
1. Change "Outcome C fails if fix requires >200 LOC (scope mis-set)" to "Outcome C: if fix requires >200 LOC, STOP and escalate. This is a scope decision: either (a) accept larger fix if informativeness justifies it (human approval), or (b) cap at YAML-only fix and record builder-level fix as Plan 03/04 finding."
2. In Session 0 entry criteria, remove "LOC ~100-200" and say "scope and LOC assessed at human gate."
**Impacts:** Plan 01 retains discipline but stops treating most informative outcome as failure.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Plan 01 Experimental Rigor):** The improvement's proposed human-approval gate opens the exact scope creep vector the 200 LOC limit was designed to close. A >200 LOC builder fix is infrastructure, not an experiment. The reframe (P4-ADV-2-01) preserves the 200 LOC boundary as inviolable but reframes what crossing it MEANS — a measurement result, not a scope failure or an approval trigger.

### P4-IMP-09: UnstoppableVault's 13 access-tierb-001 FPs are the real informativeness test
**Target:** CONTEXT
**What:** UnstoppableVault has 13 access-tierb-001 FPs on standard ERC4626 functions including read-only functions. Plan 01's primary contracts are SideEntranceLenderPool (1 FP) and NaiveReceiverPool (3 FPs). But UnstoppableVault is where access-tierb-001 does the most damage. If those 13 FPs survive despite the existing view/pure exclusion, the pattern has a deeper bug than YAML can fix.
**Why:** The fix's effect on UnstoppableVault's 13 FPs is MORE informative than on SideEntrance's 1 FP. Either the view/pure exclusion already handles those (Session 0 baseline will show fewer FPs), or they survive (builder bug signal).
**How:**
1. Add UnstoppableVault as an OBSERVATION target in Plan 01 primary test contracts: "UnstoppableVault: 13 access-tierb-001 FPs expected at baseline. After fix, document how many survive and why."
2. Add to Session 0 task (a): "For UnstoppableVault access-tierb-001 FPs, note which functions have state_mutability=view/pure in the graph but still fire."
**Impacts:** Plan 01 scope unchanged (already in 7-contract suite). Adds explicit observation target.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 01 Experimental Rigor):** UnstoppableVault's 13 FPs provide a larger signal than SideEntrance's 1 FP for distinguishing YAML-fixable from builder-fixable. The improvement explicitly limits scope by designating UnstoppableVault as OBSERVATION target (not primary). Adding state_mutability diagnostic to Session 0 task (c) is ~5 minutes of additional work within the existing 25-minute budget. P4-IMP-10 (SelfiePool prediction chain) is complementary — both add explicit observation targets with pre-registered interpretations.

### P4-IMP-10: SelfiePool prediction chain connects Session 0 diagnostic to Plan 01 scope
**Target:** CONTEXT
**What:** The improvement is correct but the proposed How is incomplete in a way that creates a dangerous ambiguity. The plan currently says Plan 01's "primary test contracts: SideEntranceLenderPool (1 FP on withdraw) + NaiveReceiverPool (3 FPs)." If Session 0 reveals `has_access_gate=false` for modifier-based access, Plan 01 scope DOES NOT simply "narrow" — it branches into a fundamentally different type of fix. The current entry criteria text is disconnected from the SelfiePool-specific finding.
**Why:** Without an explicit branch table, the executor faces a Session 0 result of `has_access_gate=false` for onlyGovernance and must infer what "scope narrows" means for Outcomes A, B, C. This is a decision point that should not be left to inference.
**How:**
1. In Plan 01, add an explicit branch table immediately after "Primary test contracts":
   ```
   Session 0 diagnostic branch:
   - IF has_access_gate=true for emergencyExit (onlyGovernance recognized):
     YAML-only fix is viable. Proceed as planned. All 3 outcomes testable.
   - IF has_access_gate=false for emergencyExit (modifier not recognized):
     Outcome B scope narrows: YAML exclusion cannot fix modifier-recognition FPs.
     YAML fix addresses ONLY view/pure functions (NaiveReceiver.maxFlashLoan, etc.).
     Modifier-recognition FPs routed to Plan 03/04 action_map as {builder-fixable: modifier-recognition}.
     Outcome B still testable on reduced FP set. Outcome C threshold unchanged.
   ```
2. In Session 0 entry criteria for Plan 01: replace "may change to builder fix + regression test" with "see Plan 01 branch table — modifier-recognition FPs are NOT in scope for YAML-only fix."
3. The prediction chain should appear in Plan 01 itself (not only Session 0 entry criteria) because Plan 01 is the document executed, not the entry criteria.
**Impacts:** Plan 01 scope self-adjusting based on Session 0 data. No additional work.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 01 Experimental Rigor):** The original How adds "prediction and branch point" to Session 0 entry criteria, but the executor reads Plan 01 during execution, not entry criteria. The branch table must live in Plan 01. The improvement's insight is correct — the prediction chain is valuable precisely because it pre-registers what the executor should DO with each diagnostic result, not just what it MEANS.

### P4-IMP-11: Pairwise comparison is fundamentally superior to absolute scoring at n=3
**Target:** CONTEXT
**What:** Plan 02's decision protocol uses Spearman rho on absolute scores from 3 anchors. With n=3, Spearman produces only {-1.0, -0.5, 0.5, 1.0}. But the deeper problem is that absolute LLM scoring on a 0-100 scale with 3 data points conflates rubric interpretation variance and actual reasoning quality discrimination. Pairwise comparison eliminates scale calibration noise entirely and produces 3 binary judgments with transitivity as a built-in consistency check.
**Why:** Pairwise comparison is the standard approach in LLM-as-judge literature (Chatbot Arena, JudgeBench, MT-Bench) for exactly this reason. With 3 pairs from 3 anchors, you get: (1) complete ordering (or cycle detection), (2) transitivity violation as free reliability signal, (3) cleaner signal for divergence hypotheses.
**How:**
1. Add pairwise comparison as PRIMARY decision instrument. For each pair, call `claude -p` with both transcripts side by side asking "which demonstrates better reasoning on {dimension}?" Record winner + confidence.
2. Retain absolute scoring as SECONDARY (informative, for rubric calibration data feeding 3.1c), but remove from go/no-go decision path. Decision becomes: (a) all 3 pairwise consistent = confirmed, (b) 2/3 consistent = partial, (c) cycle = LLM_unreliable on that dimension.
3. Reframe divergence hypotheses as pairwise.
4. Update rubric freeze calibration criteria to "all 3 pairwise judgments match intended ordering with high confidence."
**Impacts:** Plan 02 go/no-go mechanism changes. Plan 03/04 Phase 2 should adopt pairwise for small N.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Plan 02 Statistical Design):** Pairwise-as-primary creates a fatal interaction with IMP-13. IMP-13 argues evidence-based success; IMP-11 argues ordering-based success. If both merged, Plan 02 has two incompatible go/no-go mechanisms. Converting hypotheses to pairwise binary judgments destroys the score-delta information that IMP-14 depends on. The transitivity "free reliability signal" only fires on a cycle (A>B, B>C, C>A) — unlikely with honest anchors. Replaced by P4-ADV-3-01 (three-instrument model that assigns each instrument to a specific question).

### P4-IMP-12: Divergence hypothesis (b) references wrong score predictions from formula
**Target:** CONTEXT
**What:** Hypothesis (b) states "both 70, per 3.1d calibration." Looking at `reasoning_evaluator.py:384-388`, reasoning_depth scores `min(100, 30 + unique_tools * 20)`. So: 0 tools = 30, 1 = 50, 2 = 70, 3 = 90, 4+ = 100. The "both 70" claim means exactly 2 unique tools each. But anchor spec requires "at least 3 tool calls" -- if 3 different tools, score = 90, not 70.
**Why:** The hypothesis says "both score 70" but anchors score 90 because they have 3 unique tool types. The "saturation" the hypothesis tests does not actually occur at the predicted score.
**How:**
1. Replace "both 70, per 3.1d calibration" with actual formula-derived prediction. State tool count as explicit anchor design parameter.
2. Design GOOD and MEDIOCRE anchors to have SAME number of unique tools (to trigger heuristic parity) but differ in reasoning chain quality.
3. Add pre-check: after writing anchors but before LLM scoring, run through heuristic and verify predicted parity holds.
**Impacts:** Plan 02 hypothesis (b) becomes testable. No other plans affected.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 02 Statistical Design):** The formula error is real and verifiable: `min(100, 30 + unique_tools * 20)` at 3 unique tools = 90, not 70. IMP-14 constrains MEDIOCRE to have same query count as GOOD. IMP-12 constrains same unique tool count. These two anchor design constraints must be coordinated — MEDIOCRE must simultaneously match GOOD on (a) unique tool count and (b) bskg_query count, while differing only in reasoning chain quality. This tightens anchor design significantly but does not make it infeasible. The pre-check step is the correct safeguard.

### P4-IMP-13: Rubric freeze protocol creates circular dependency with go/no-go decision
**Target:** CONTEXT
**What:** The rubric freeze protocol calibrates on the same 3 anchors used for the official go/no-go evaluation. This is correctly identified as overfitting, but shifting success to "qualitatively different evidence" does not resolve the circularity — it relocates it. If the rubric was tuned on these 3 anchors, the rubric is still tuned to these 3 anchors regardless of whether success is measured by score ordering or explanation quality. The real fix is temporal: separate calibration from evaluation by adding a held-out anchor BEFORE calibration begins.
**Why:** A rubric tuned over 3 revisions to produce the right ordering on 3 anchors will also produce the right LLM explanation content on those same 3 anchors — the LLM reads the rubric and the transcripts together. The circularity is in the calibration-target set, not in the success metric definition.
**How:**
1. Add a 4th "held-out" anchor (zero-graph: agent produces a finding with no graph queries, no node IDs, correct conclusion by luck). Written BEFORE rubric drafting. Not shown during calibration rounds.
2. Calibration round uses only 3 anchors (GOOD, MEDIOCRE, BAD). Rubric revised freely against these 3.
3. After freeze: score the held-out anchor. If held-out scores low (as expected for zero-graph), rubric generalizes. If held-out scores high, rubric overfit to surface features of the 3 calibration anchors.
4. Held-out result is an independent validity signal, not the go/no-go gate itself.
5. Cost: ~2 additional LLM calls. Session budget unchanged.
**Impacts:** Plan 02 success criterion gains independent validation. Plan 05 benefits from richer evidence data.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 02 Statistical Design):** The original proposed fix (evidence-based success criterion) changes what success means without breaking the circular dependency. The held-out anchor placed BEFORE calibration is the standard psychometric approach. This also interacts with P4-ADV-3-01: the held-out anchor should be scored with all three instruments (pairwise against each calibration anchor, absolute score, explanation content check).

### P4-IMP-14: evidence_quality hypothesis (c) is trivially confirmable -- bar too low
**Target:** CONTEXT
**What:** Hypothesis (c) is trivially confirmable as stated. The harder test (same query count, different interpretation quality) is correct and necessary. However it creates an anchor design conflict: MEDIOCRE must now simultaneously satisfy (from IMP-12) identical unique_tool_count to GOOD AND (from this item) identical bskg_query_count to GOOD while differing only in reasoning chain quality. This makes MEDIOCRE a very precisely engineered anchor with strawman risk.
**Why:** The interesting question is whether the LLM discriminates between queries that FOUND relevant results vs queries returning irrelevant results. That is the actual gap in the heuristic. But the combined constraints from IMP-12 + IMP-14 create a tightly engineered MEDIOCRE that may be harder to write than GOOD.
**How:**
1. Replace hypothesis (c) with harder test: "GOOD and MEDIOCRE have identical bskg_query_count. Heuristic scores identically. LLM scores GOOD higher due to interpretation quality."
2. Add anti-strawman check: before running LLM scoring, have a human read MEDIOCRE's reasoning chain and confirm it is "plausibly mediocre" — could come from a real agent that made real queries but drew shallow conclusions. Record judgment.
3. Retain original hypothesis (c) as sanity check but label it "sanity check, not counted in go/no-go."
4. Coordinate anchor design constraints explicitly: "MEDIOCRE anchor design constraints: (a) unique_tool_count = GOOD_unique_tool_count, (b) bskg_query_count = GOOD_bskg_query_count, (c) reasoning chain reads as plausibly real but shallow, (d) result interpretation lacks causal specificity."
**Impacts:** Plan 02 anchor design more constrained. Makes hypothesis (c) actually discriminating.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 02 Statistical Design):** The combined IMP-12 + IMP-14 anchor constraints create a tightly engineered MEDIOCRE that may actually be harder to write than GOOD. This is a craft problem, not a logic problem — but it deserves explicit acknowledgment. If MEDIOCRE cannot be written to satisfy all constraints plausibly, the fallback is to relax (b) and accept that hypotheses (b) and (c) cannot be tested simultaneously in the same anchor.

### P4-IMP-15: Plan 02 has no protocol for LLM scoring non-determinism across runs
**Target:** CONTEXT
**What:** Plan 02 scores all 3 anchors with the frozen rubric but only once. If the LLM gives reasoning_depth=75 on one call and 52 on a second call for the same anchor, the decision protocol is unreliable. The existing dual-Opus evaluator design acknowledges this problem but Plan 02 does not use it.
**Why:** LLM scoring variance is the most well-documented failure mode in LLM-as-judge literature. With n=3 anchors and only 1 scoring call per (dimension, anchor) pair, Plan 02 cannot distinguish signal from noise.
**How:**
1. Add minimum 2 scoring runs per (dimension, anchor) pair for go/no-go dimensions. If two runs differ by > 15 points, flag "high variance" and run tie-breaker or exclude.
2. Add explicit step after official scoring: "compare runs, report per-dimension variance."
3. Cost note: doubles LLM calls from ~6 to ~12. At `claude -p` rates, trivial cost.
**Impacts:** Plan 02 session estimate may increase slightly. Plan 03/04 Phase 2 should adopt same protocol.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Plan 02 Statistical Design):** IMP-15's duplicate-absolute-scoring protocol applies variance detection to the wrong instrument. Once the three-instrument model from P4-ADV-3-01 is adopted, absolute scoring is demoted to secondary/calibration-only. Doubling the secondary instrument's calls is wasteful while leaving the primary instrument (pairwise) with zero variance protocol. Replaced by P4-ADV-3-02 which redirects variance detection to pairwise ordering and explanation content.

### P4-IMP-16: Phase 0 taxonomy "degenerate corpus" threshold is too permissive
**Target:** CONTEXT
**What:** Taxonomy collapse triggers at "< 2 categories." But with 18+ of 65 FPs from access-tierb-001, even 3 categories could be structurally degenerate if the dominant cluster contains 80% of samples. The threshold measures category COUNT but not category BALANCE.
**Why:** A taxonomy with 3 categories where one has 55 FPs and two have 5 each provides almost no actionable differentiation.
**How:**
1. Add balance criterion: "If largest category > 75% of FPs: finding = 'dominated corpus.' Phase 1 proceeds unchanged. Phase 0 output annotated with dominance ratio."
2. Update Phase 0 exit artifact: ">= 1 category with scope tag AND dominance ratio recorded."
3. Update compound degradation rule: "Phase 0 < 3 categories OR largest category > 75%."
**Impacts:** Plan 05 gains dominance ratio input. Plan 03/04 Phase 2 compound degradation tightens.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Plan 03/04 Threshold Coherence):** The 75% dominance threshold is a predetermined fire — access-tierb-001 alone accounts for 27.7% of 65 FPs, UnstoppableVault's 13 FPs from ERC4626 functions are structurally identical. The threshold will ALWAYS trigger on this corpus, making it a rubber stamp. More importantly, Phase 0 taxonomy is decoupled from Phase 1 archetype generation, so a "dominated corpus" finding has ZERO effect on Phase 1 scope. The real problem is the compound degradation rule conflating two independent failure modes. See P4-ADV-4-01 for replacement.

### P4-IMP-17: Phase 2 inherits Plan 02 rubric quality uncertainty without a quality floor
**Target:** CONTEXT
**What:** Phase 2 gates on Plan 02 rubric freeze (SHA256 match) but only checks IDENTITY, not QUALITY. Plan 02's rubric freeze protocol allows fallback: "if not achieved in 3 revisions, use best version, record 'rubric calibration incomplete'." Phase 2 would then score with a rubric that failed its own calibration.
**Why:** The compound degradation rule catches Plan 02 divergence hypothesis failure but does NOT catch rubric calibration failure. A rubric that passed 2/3 hypotheses but failed calibration could still gate Phase 2 in.
**How:**
1. Add to Phase 2 gate: "Gate: confirm rubric SHA256 matches AND rubric calibration succeeded (GOOD-BAD spread >= 30). If calibration incomplete: Phase 2 proceeds but results annotated 'rubric-uncalibrated.'"
2. Update Phase 2 exit artifact to include rubric calibration status.
**Impacts:** Plan 03/04 Phase 2 confidence assessment. Plan 05 receives calibration status.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** Plan 02 (rubric freeze outcome)
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 03/04 Threshold Coherence):** SHA256 identity check confirms WHICH rubric was used; it does not confirm the rubric achieved calibration. The fallback allows a rubric that failed calibration in 3 revisions to proceed ("use best version, record 'rubric calibration incomplete'"). Phase 2 would then score with a rubric that already demonstrated it cannot discriminate. The annotation approach correctly preserves experimental data while flagging reliability. Plan 05's Unobserved Phenomena should receive "rubric-uncalibrated" as an item if triggered.

### P4-IMP-18: Haiku as adversarial transcript generator may be capability-insufficient
**Target:** CONTEXT
**What:** Phase 1 uses Haiku to generate gaming transcripts. Quality gate catches transcripts that fool BOTH heuristic and LLM, but does not catch when Haiku cannot generate PLAUSIBLE gaming transcripts at all.
**Why:** Haiku is asked to: read evaluator source code, identify exploitable paths, generate realistic transcripts. This is multi-step reasoning that may exceed Haiku's capabilities. No gate for Haiku succeeding TOO POORLY.
**How:**
1. Add minimum competence gate: "If zero Haiku transcripts score heuristic >= 50: Haiku generation inadequate. Escalate to Sonnet for generation. Record model tier."
2. Add model tier to Phase 1 exit artifact.
**Impacts:** Plan 03/04 Phase 1 gains floor gate. Session estimate adds ~15 min if escalation needed.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Plan 03/04 Threshold Coherence):** The heuristic >= 50 threshold tests whether Haiku can game the heuristic, not whether it can produce plausible content. A transcript scoring heuristic 30 could be an excellent "obviously bad reasoning" example that tests the LLM's lower-bound detection. The existing quality gate handles the upper bound; the lower bound should be a plausibility spot-check, not a score threshold. See P4-ADV-4-02 for replacement.

### P4-IMP-19: Gameability matrix measures LLM-catches-gaming but not LLM-false-flags-legitimate
**Target:** CONTEXT
**What:** The gameability matrix measures "can LLM catch gaming?" but does not test "does LLM also score LEGITIMATE high-quality transcripts as high?" Without this, a trigger-happy evaluator that rejects everything would pass.
**Why:** A matrix testing only detection without testing acceptance is structurally incomplete. Plan 02's GOOD anchor could serve as the legitimate-acceptance baseline.
**How:**
1. Add to Phase 2: "Re-score Plan 02 GOOD anchor with Phase 2 rubric. If GOOD anchor scores LLM < 60: evaluator is over-rejecting. Matrix conclusions annotated 'specificity unvalidated.'"
2. Requires no additional transcripts -- one additional LLM call.
**Impacts:** Plan 03/04 Phase 2 gains specificity check. Plan 05 receives specificity status.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** Plan 02 (GOOD anchor must exist)
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 03/04 Threshold Coherence):** Sensitivity-without-specificity gap is real and the fix is cheap: one LLM call against Plan 02 GOOD anchor. One concern: the GOOD anchor is an idealized "gold standard" — if real transcripts score < 60 while GOOD scores >= 60, the specificity check is falsely reassuring. IMP-19's How should note: "GOOD anchor provides best-case specificity lower bound. Real transcript specificity requires Phase B of Plan 02."

### P4-IMP-20: Session estimate does not surface parallelism opportunity
**Target:** CONTEXT
**What:** Budget Recount says "5-6 core sessions" serially. But Phase 0+1 of Plan 03/04 can run parallel with Plan 02. The critical path is: Session 0 -> Plan 01 -> [Plan 02 || Plan 03/04 Phases 0+1] -> Plan 03/04 Phase 2 -> Plan 05. This could be 4-4.5 sessions on critical path.
**Why:** The plan is MORE parallelizable than the budget suggests. Making this explicit helps scheduling.
**How:**
1. Add to Budget Recount: "Critical path: Session 0 (1) -> Plan 01 (1) -> Plan 02 + Plan 03/04 Phases 0+1 in parallel (1) -> Plan 03/04 Phase 2 (0.5-1) -> Plan 05 (0.5) = 4-4.5 core sessions on critical path."
2. Make Phase 0/1 preconditions explicit: "Phase 0 requires only baseline data. Phase 1 requires evaluator source code. Phase 2 requires Plan 02 rubric freeze."
**Impacts:** Budget Recount clarity, Plan 03/04 scheduling.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** cosmetic
**Status:** implemented
**Adversarial note (Plan 03/04 Threshold Coherence):** The parallelism claim is accurate. The improvement is correctly classified cosmetic — no plan scope, gate, or artifact changes. Making parallelism explicit creates scheduling guidance for the human, not an execution instruction. The How should note "parallelism is available but each parallel stream may require separate session slots if Agent Teams are involved."

### P4-IMP-21: Pre-registered interpretation thresholds contradict gameability matrix criterion
**Target:** CONTEXT
**What:** Two threshold systems in Plan 03/04 produce contradictory go/no-go verdicts for the same N. Line 281 states ">= 4/N caught with mechanism explanation: go. 2-3/N: conditional. <= 1/N: no-go." Line 256 states "LLM-score < 70 AND identifies gaming mechanism on >= ceil(N/2) of N mandatory archetypes." For N=6: line 256 sets go threshold at ceil(6/2)=3, but line 281 calls 3/N "conditional." The contradiction exists for all N where ceil(N/2) < 4.
**Why:** This is not just a documentation inconsistency — it is an ambiguity at the exact moment an executor must make a binary go/no-go call. The gameability matrix go criterion (line 256) was explicitly designed for the ceil(N/2) formulation after the Plans 03/04 merge; line 281 is a stale remnant of pre-merge Plan 04 threshold language.
**How:**
1. Locate line 281 in CONTEXT.md ("Pre-registered interpretation thresholds: >= 4/N caught...").
2. Replace line 281 entirely with: "Pre-registered interpretation thresholds: see gameability matrix go criterion above (line 256). Go = ceil(N/2) with mechanism explanation. Conditional = ceil(N/2)-1. No-go = <= 1. N is pre-registered in archetype-count.json (Phase 1 exit artifact)."
3. Add a note documenting the provenance: "Note: the >= 4/N threshold (removed) was from pre-merge Plan 04 language. The ceil(N/2) criterion is authoritative post-merge."
4. Verify that for the expected N range (3-8 archetypes), the ceil(N/2) thresholds are not too lenient: N=3 → go at 2, N=4 → go at 2, N=8 → go at 4.
**Impacts:** Plan 03/04 Phase 2 interpretation clarity.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 03/04 Threshold Coherence):** The original How is a one-liner that does not capture the full repair. The remnant threshold exists because Plans 03 and 04 were merged but pre-merge Plan 04 language was not removed. Simply removing line 281 fixes the contradiction but does not make provenance traceable. The enhanced How adds provenance documentation and a sanity check on ceil(N/2) values across the expected N range.

### P4-IMP-22: Unobserved Phenomena list is the phase's most consequential deliverable but has no quality criteria
**Target:** CONTEXT
**What:** Plan 05's Unobserved Phenomena list is the primary scope-defining artifact for 3.1c, but the current pre-registration says nothing about its quality. The existing structure `(phenomenon, why, difficulty, target-phase)` permits shallow entries that cite no evidence and ask no testable question — producing a bad map for 3.1c before it starts.
**Why:** The risk is not that the list is empty — it is that the list looks complete while being unfalsifiable. An entry like "multi-pattern interaction: matters because patterns interact: moderate: 3.1c" survives the current format without naming a single artifact or testable question. 3.1c then inherits scope items with no evidence trail. The list is the one Plan 05 deliverable that outlives the phase; shallow entries compound forward.
**How:**
1. In Plan 05 description, after the existing per-item structure `(a) phenomenon, (b) why, (c) difficulty, (d) target phase`, add required fields: `(e) concrete experimental question — a falsifiable "does X cause Y?" or "can we measure Z?", not a topic label; (f) evidence anchor — at least one artifact from Plans 01, 02, or 03/04 (filename + finding) that revealed this gap. Acceptable: "Plan 03/04 Phase 0 action_map.json: cluster 'modifier-based-access-control' has no YAML-fixable action — reveals gap in has_access_gate recognition." Unacceptable: "modifier patterns may matter."`.
2. Add the anti-pattern example verbatim: "REJECT: 'cross-contract interaction: matters because patterns interact: moderate: 3.1c' — no evidence cited, no testable question. This entry cannot guide 3.1c experiment design."
3. Keep the existing `> 5 items tagged 3.1c → Scope overflow → top 3 by difficulty as high-priority` rule unchanged.
**Impacts:** Plan 05 execution quality; downstream 3.1c scope definition.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 05 Dependency & Quality):** The original How is directionally correct but underspecified. "Concrete experimental question" and "cite at least one artifact" are the right constraints but need operational definitions — otherwise an implementer writes "Q: does it matter? Artifact: baseline-before.json" and satisfies the letter. The rewrite adds the specific format pattern and explicit reject example as a prescriptive gate criterion.

### P4-IMP-23: The 80% observed-data-fields threshold is measuring the wrong thing
**Target:** CONTEXT
**What:** "Success: schemas capture >= 80% of observed data fields." This measures coverage of WHAT WAS OBSERVED, but the question is whether schemas are SUFFICIENT for 3.1c. 80% of observed fields could miss the 20% that matters most.
**Why:** A schema capturing Plan 01 firing data and Plan 02 scores at 80% but unable to link "this FP was in the transcript that got score X" fails the actual purpose.
**How:**
1. Replace threshold with: "schemas capture observed data AND demonstrate composability: at least one query joining detection data (Plan 01) with evaluation data (Plan 02 or 03/04) is expressible. Example: 'for each FP function, what was the heuristic validity score on the dimension most relevant to that FP type?'"
2. Keep failure criterion unchanged ("schemas require fields no experiment produced").
**Impacts:** Plan 05 success criteria become harder but more meaningful.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plans 01, 02, 03/04
**Classification:** structural
**Status:** reframed
**Adversarial note (Plan 05 Dependency & Quality):** IMP-23's composability test is stronger than 80% coverage, but has a new failure mode: it is binary and implementation-specific. "At least one query joining detection and evaluation data is expressible" passes if the example query happens to work, even if the schema omits five other critical joins. The deeper problem: Plan 05 is a SYNTHESIS plan, not a PROOF plan. The right success criterion is not coverage or composability but MINIMUM NECESSARY: field-provenance annotation. See P4-ADV-5-01 for replacement.

### P4-IMP-24: Plan 05 has no fallback for partial upstream completion
**Target:** CONTEXT
**What:** Plan 05 preconditions: "Plans 01 and merged 03/04 complete." But Plan 03/04 is MEDIUM confidence with compound degradation rule that can produce INCONCLUSIVE. Plan 05 treats preconditions as binary.
**Why:** If Plan 03/04 Phase 2 is INCONCLUSIVE, Plan 05 still has Track A data (Plan 01 is HIGH confidence) and Phase 0 taxonomy data. Waiting blocks synthesis on the lowest-confidence plan.
**How:**
1. Change preconditions to: "Plan 01 complete. Plan 03/04: Phase 0 exit artifact exists (minimum). Full completion provides richer input but is not blocking."
2. Add: "If Phase 2 INCONCLUSIVE, Unobserved Phenomena includes 'heuristic validity: requires-infrastructure, target: 3.1c'."
**Impacts:** Plan 05 can start earlier; reduces critical path dependency.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** Plan 03/04 (partial outputs)
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 05 Dependency & Quality):** The fallback is sound. Track A is independent of Plan 03/04's Phase 2 outcome. The proposed "Phase 0 exit artifact exists (minimum)" is the right floor because Phase 0 is no-Plan-02-dependency and high-confidence. Partial upstream just means Track B activates at tier 1, not tier 2+. The fallback does not introduce new risk; it correctly documents existing partial-output handling.

### P4-IMP-25: Plan 02 dependency for Plan 05 is implicit but critical
**Target:** CONTEXT
**What:** Plan 05 preconditions list "Plans 01 and merged 03/04 complete" but Track B graduated activation explicitly depends on Plan 02's per-dimension recommendation matrix. Combined with IMP-24's change (Plan 03/04 Phase 0 minimum, not full completion), the preconditions now need three items: Plan 01, Plan 02, and Plan 03/04 Phase 0.
**Why:** The omission is not just a documentation gap — it creates a scheduling trap. With IMP-24 accepted, Plan 05 can start after Plan 01 + Plan 03/04 Phase 0. But Track B requires Plan 02's dimension matrix. If an implementer starts Plan 05 with Plans 01 and Phase 0 complete but Plan 02 still running, Track B either silently fails or blocks mid-execution.
**How:**
1. Replace preconditions with three-part statement: "Plan 01 complete (required — provides detection schema data for Track A). Plan 02 core complete (required — provides per-dimension matrix for Track B graduated activation gate). Plan 03/04 Phase 0 exit artifacts exist (minimum for taxonomy input; Phase 2 full completion enriches but does not gate)."
2. In Track B description, make the gate explicit inline: "Track B activation gate: Plan 02 per-dimension matrix must show LLM_adds_signal on >= 1 dimension. If Plan 02 is incomplete at Plan 05 start, Track B is deferred — write evaluation_observations.md as fallback."
3. Note on execution order with IMP-24 combined: "Minimum entry state for Plan 05: Plans 01 and 02 complete, Plan 03/04 Phase 0 artifacts exist."
**Impacts:** Scheduling accuracy; prevents premature Plan 05 execution.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** Plan 02 (Track B gate)
**Classification:** structural
**Status:** implemented
**Adversarial note (Plan 05 Dependency & Quality):** The original How is correct in substance but does not account for the IMP-24 change in the same pass. After IMP-24, preconditions change from binary to partial-ok. Adding Plan 02 to THAT formulation requires a three-part rewrite, not just appending. If Plan 02 has a delayed Phase B (per IMP-37 REFRAME), Plan 05 should not wait for Phase B — only Plan 02 CORE (synthetic anchor phase) is the gate.

### P4-IMP-26: No experiment tests AlphaSwarm's core behavioral signature thesis
**Target:** CONTEXT
**What:** None of the 5 experiments test the foundational claim: "Names lie. Behavior does not." Plan 01 tests FP reduction via YAML exclusion. It does NOT test whether behavioral signatures survive function renaming -- the exact scenario CLAUDE.md uses to justify the entire approach.
**Why:** If behavioral signatures DO break under renaming (e.g., because graph construction relies on name-based heuristics), then 466 patterns are built on sand. A single experiment -- rename `withdraw` to `processPayment` in SideEntranceLenderPool, rebuild graph, re-run detection -- would either validate or reveal a catastrophic blind spot. This costs ~15 minutes.
**How:**
1. Add Session 0 stretch task: "Name-independence smoke test: Copy SideEntranceLenderPool.sol, rename `withdraw` to `processPayment` and `flashLoan` to `executeBorrow`. Build graph. Run detection. Compare pattern firings. If ANY pattern stops firing, record 'name-dependent pattern: {pattern_id}' -- critical finding for 3.1c." Estimated 15 min.
2. In domain deliverables, add: "Name-independence smoke test result on 1 contract (stretch)."
**Impacts:** Session 0 stretch scope changes. If result is negative, cascades to ALL plans.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Strategic Alignment):** The 15-minute estimate is wrong — renaming requires copying contract, renaming ALL call sites, rebuilding graph (~10 min), running detection, comparing. More realistically 25-35 minutes. But the deeper problem: the test proves the WRONG thing. A pattern that stops firing after renaming could indicate name-based heuristic in builder, in pattern YAML, or a test artifact. The actionable question is whether the builder has name-dependent property assignment — and Session 0 task (c) already probes graph properties directly. See P4-ADV-6-01 for replacement.

### P4-IMP-27: No experiment tests multi-agent orchestration value -- the core product differentiator
**Target:** CONTEXT
**What:** The plans define 5 experiments testing single-agent, single-capability questions. None test whether the attacker/defender/verifier debate protocol adds value over single-agent analysis. CLAUDE.md positions multi-agent debate as the core product differentiator, yet 3.1e validates components that could exist in a single-agent tool. This is explicitly deferred to Phase 4 and acknowledged in the phase boundary.
**Why:** If multi-agent debate adds no value over single-agent analysis, the orchestration layer (6,400 LOC) is waste. 3.1e is the "contact with reality" phase, yet avoids the most important reality question. The deferral may be correct since detection and evaluation must work BEFORE debate can be tested. Plan 02's per-dimension recommendation matrix defines what "value" means for debate evaluation.
**How:**
1. Add to deferred section: "Multi-agent debate value experiment -- single-agent vs multi-agent verdict comparison on same finding. Deferred to Phase 4, but ACKNOWLEDGED as higher strategic risk than any 3.1e experiment. Plan 02's per-dimension matrix defines which dimensions to measure. Design: take one finding, run single-agent evaluation, then debate. Compare scores using Plan 02's measurement instruments. If LLM_adds_signal from Plan 02, LLM scoring is the instrument; if not, use heuristic as rough proxy. Target: 3.1c."
2. In phase boundary "What this phase does NOT deliver," add: "Validation that multi-agent debate adds value over single-agent analysis (Phase 4 -- but this is the single highest-risk assumption in the project)."
**Impacts:** No plan changes. Strategic documentation of a known gap. Informs Phase 4 priority.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 02 (per-dimension matrix informs debate measurement)
**Classification:** structural
**Status:** implemented
**Adversarial note (Strategic Alignment):** Correctly identifies the gap AND correctly explains why deferral is justified: single-agent capabilities must work before debate can be tested. The How is appropriately minimal — documentation only, no scope change. The phrase "single highest-risk assumption in the project" is accurate — STATE.md confirms "Multi-agent debate: Core feature | Never executed." One note: the deferred item should say "Target: Phase 4" not "Target: 3.1c" since debate testing belongs in Phase 4.

### P4-IMP-28: "5-6 session sprint" framing creates false urgency that conflicts with serial dependency reality
**Target:** CONTEXT
**What:** The Budget Recount currently says "5-6 core sessions" in the Decisions section. The 5-6 figure counts session-equivalents of work assuming zero gate failures, zero scope changes from Session 0, zero review latency. Session 0 property diagnostic alone has explicit branch points that could add 1-2 sessions.
**Why:** The Budget Recount decision already contains the right content ("The 'empirical sprint' label is retained for brevity but the time commitment is a research phase") but buries it after the 5-6 number, which is what readers will anchor on.
**How:**
1. In the Budget Recount decision, restructure to lead with the elapsed estimate: "Elapsed estimate: 8-12 sessions accounting for human review gates, potential Session 0 scope adjustments, and gate failures. Work-session estimate (zero failures, no scope changes): 5-6 sessions."
2. Add clarifying sentence: "'Sprint' refers to experimental methodology — small, bounded, falsifiable experiments — not execution speed."
3. No other changes needed. The 5-6 figure itself is defensible as a work estimate; the problem is ordering and framing.
**Impacts:** No plan changes. Expectation management only.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** creative-structural
**Status:** implemented
**Adversarial note (Strategic Alignment):** The original How says "add elapsed estimate" and "clarify sprint" without specifying WHERE in the document these changes land. The Budget Recount decision in `<decisions>` is the canonical location. The rewrite should anchor the improvement to the Session 0 overflow rule (which already acknowledges overflow risk) so the two signals are consistent.

### P4-IMP-29: Deferred "Finding deduplication" may be more impactful than Plan 03/04's evaluator validity
**Target:** CONTEXT
**What:** Deferred list includes "Finding deduplication -- estimated 3x noise reduction." Meanwhile Plan 03/04 spends 1.5-2 sessions measuring evaluator validity on a heuristic the context describes as "disposable." The 3x noise reduction would directly improve the 13.3% precision figure.
**Why:** Plan 03/04 Phase 0 (taxonomy) directly enables deduplication -- the taxonomy clusters ARE the deduplication classes. Phase 0 output should explicitly tag clusters as deduplication groups.
**How:**
1. Add to Plan 03/04 Phase 0 scope note: "Phase 0 taxonomy output should explicitly tag clusters as potential deduplication groups."
2. Add to deferred "Finding deduplication": "Depends on Phase 0 taxonomy output. Consider as immediate follow-up to Phase 0 before Phase 1 adversarial work."
**Impacts:** Suggests Phase 0 is higher priority than Phases 1-2 (already the design but not stated rationale).
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** Plan 03/04 Phase 0
**Classification:** structural
**Status:** rejected
**Adversarial note (Strategic Alignment):** The improvement conflates deduplication as MEASUREMENT improvement with deduplication as PRODUCT improvement. Taxonomy clusters group FPs by root cause; deduplication groups findings by vulnerability class across functions — these are NOT the same. Additionally, "Plan 03/04 spends 1.5-2 sessions on a heuristic the context describes as disposable" misreads the design: Phase 2 measures whether the LLM evaluator is trustworthy, which is foundational for 3.1c. The deferred item already tracks deduplication. No change needed.

### P4-IMP-30: Phase proves components work but avoids testing the integration path to 3.2
**Target:** CONTEXT
**What:** The phase validates 5 isolated components. None answer: "Can detection output feed into evaluation input?" Plan 01 produces per-function-firing JSON; Plan 02 expects transcript content in `{observed}` field. These are fundamentally different data shapes — one is a detection result, the other is an agent reasoning trace.
**Why:** The formats almost certainly DO NOT compose directly, meaning the "integration smoke test" will likely immediately fail and produce the most valuable finding of Plan 05: explicit documentation of the data shape gap between detection and evaluation.
**How:**
1. Add to Plan 05 deliverables: "Integration smoke test: attempt to feed Plan 01 per-function detection output for one contract as `{observed}` content in Plan 02 rubric. Document: (a) whether raw detection JSON is interpretable by the LLM as evidence, or (b) what transformation is needed. This is expected to reveal a format gap. The FINDING is the valuable output."
2. Change framing from "verify data flows without format conversion" to "characterize the transformation required." The actual outcome is diagnostic.
3. Add to Unobserved Phenomena routing: "Detection-to-evaluation format gap: document as 'integration gap: architectural, target: 3.1c' if non-trivial transformation required."
4. Confirm fits within 0.5-session budget — one LLM call plus analysis.
**Impacts:** Plan 05 scope slightly expands but within existing budget.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** Plan 01, Plan 02
**Classification:** structural
**Status:** implemented
**Adversarial note (Strategic Alignment):** The original How says "verify data flows without format conversion" — wrong expectation. Detection JSON and evaluation transcript content are different abstractions entirely. The smoke test will reveal a format mismatch, which is the correct and expected outcome. Framing it as "verify it works" sets up a false success criterion. The rewrite frames it as a diagnostic, which better serves Plan 05's purpose.

### P4-IMP-31: EVMbench orientation decision is buried -- should be explicit strategic choice
**Target:** CONTEXT
**What:** EVMbench appears in pre_research, deferred items, and Plan 05 as optional reference. The strategic question is: should detection metrics be COMPARABLE to EVMbench methodology? EVMbench uses binary per-vulnerability; AlphaSwarm uses per-function-firing. If 3.1e uses per-function-firing and Phase 5 switches to per-vulnerability, all baselines become non-comparable.
**Why:** The measurement methodology choice should be made BEFORE experiments, not deferred.
**How:**
1. Elevate EVMbench decision: "Measurement methodology: 3.1e uses per-function-firing for delta measurement (maximum sensitivity). EVMbench uses per-vulnerability for benchmark comparison. These serve different purposes. Plan 05 must document the mapping. Phase 5 must NOT invalidate 3.1e baselines -- it must ADD per-vulnerability alongside, not replace."
2. Add to Plan 05: "Document mapping between per-function-firing counts (3.1e) and per-vulnerability counts (EVMbench)."
**Impacts:** Plan 05 adds one analysis step. Clarifies Phase 5 relationship.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** Plan 01, Plan 03/04 Phase 0
**Classification:** structural
**Status:** implemented
**Adversarial note (Strategic Alignment):** The improvement correctly identifies a real methodological risk: if 3.1e standardizes on per-function-firing and Phase 5 switches to per-vulnerability, all baselines become non-comparable. The key claim is accurate: methodology choice should be made BEFORE experiments. One concern: "Phase 5 must NOT invalidate 3.1e baselines" slightly overreaches — soften to "Phase 5 should document why, if it departs from per-function-firing baseline."

### P4-IMP-32: Deferred list conflates "not yet" with "probably never" -- needs triage
**Target:** CONTEXT
**What:** Restructure the `<deferred>` section's flat 21-item list into three labeled sub-sections: (1) Killed — ideas explicitly rejected, not to be resurrected without new evidence; (2) Conditional — depends on 3.1e experimental results; (3) Future work — planned for a specific downstream phase, with phase label.
**Why:** The current flat list mixes "600 LOC of Pydantic models pre-experiments" (explicitly killed, the v5.0 anti-pattern this entire phase exists to counter) with "Multi-pattern corpus taxonomy" (legitimate future work needing infrastructure) and "Automated Goodhart mitigation" (conditional on Plan 03 results). Downstream phases reading this list cannot distinguish what to revive from what to ignore.
**How:**
1. Restructure `<deferred>` into three sub-sections with the following initial classification:
   - **Killed (do not resurrect without new evidence):** "600 LOC of Pydantic models pre-experiments" | "7 pre-defined failure categories (replaced by LLM-discovered taxonomy)" | "GapLogProtocol interface (zero entries; write JSONL directly)" | "DetectionGroundTruth protocol (markdown table; parse when needed)" | "14 YAML contract updates for gap_triggers (updating contracts for features that haven't run)"
   - **Conditional (depends on 3.1e results):** "Automated Goodhart mitigation (build only if Plan 03 proves validity low AND automatable)" | "Cross-model validation / GPT-4o evaluator (only if self-similarity bias confirmed in Plan 03 stretch)" | "GVS result_length filter (test in Plan 03 stretch; otherwise design in 3.1c)" | "Finding deduplication (depends on Phase 0 taxonomy — estimated 3x noise reduction)"
   - **Future work (phase-tagged):** All items with explicit target phases (3.1c, 3.1f, Phase 4, Phase 5)
2. Each item in Killed should include a one-line reason. Killed sub-section should note "if new evidence contradicts this, treat as Conditional" as standing policy.
**Impacts:** No plan changes. Improves downstream planning efficiency.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Strategic Alignment):** The original How correctly identifies the three sub-sections but does not provide initial classification of the 21 items — leaving the executor to re-do the triage. The rewrite makes classification explicit so implementation is a direct copy-edit rather than another analysis pass. The "Killed" classification deserves special validation by the executor, since only the context author knows which items were explicitly rejected vs tentatively deferred.

### P4-IMP-33: Agent-to-agent information flow is untested and unmentioned as risk
**Target:** CONTEXT
**What:** The 9-stage audit pipeline has Stage 7 (Verification: Attacker -> Defender -> Verifier debate) where each agent receives the prior agent's output. If the attacker produces a finding format the defender cannot parse, debate fails. The context notes "multi-agent debate has never been executed" but does not reflect this in 3.1e's risk model.
**Why:** Plan 02's LLM evaluation tests scoring a SINGLE agent's transcript. Multi-agent debate may produce fundamentally different transcript structures (interleaved, multi-perspective). Plan 02's rubric may not transfer.
**How:**
1. Add assumption: "Multi-agent information flow is out of scope -- All 3.1e experiments evaluate single-agent capabilities. Multi-agent debate is deferred to Phase 4. Rubrics and schemas from 3.1e may require adaptation for multi-agent transcripts."
2. Add to Plan 02: "Note: multi-agent transcripts may have fundamentally different structure. Rubric transferability to multi-agent is an open question for 3.1c."
**Impacts:** Plan 02 gains documented limitation. No scope change.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Strategic Alignment):** Correctly identifies a scoping gap. Adding an explicit assumption about multi-agent info flow being out of 3.1e scope costs nothing and prevents 3.1c from inheriting a false assumption that Plan 02 rubrics generalize to multi-agent transcripts. STATE.md confirms "Multi-agent debate: Never executed" — this is an untested assumption for the entire evaluation infrastructure. Confirmed as necessary documentation.

### P4-IMP-34: Sequential dependency chain is suboptimal -- Plan 03/04 Phase 0 can run before Plan 01
**Target:** CONTEXT
**What:** Plan 03/04 Phase 0 states "runs immediately, no Plan 01/02 dependency" and requires "only baseline data." But the implicit ordering is Session 0 -> Plan 01 -> Plan 03/04. Phase 0 could run DURING Session 0 or parallel with Plan 01, saving 0.5 sessions.
**Why:** Phase 0 is a pure taxonomy exercise on existing FP data. Its output (descriptive_clusters.json + action_map.json) could inform Plan 01's fix strategy -- knowing which FPs are YAML-fixable vs builder-fixable BEFORE attempting the fix.
**How:**
1. Make parallelism explicit in Plan 03/04: "Phase 0 MAY run in parallel with Plan 01 (requires only 3.1d baseline data). descriptive_clusters.json informs Plan 01 fix targeting OPTIONALLY."
2. Add decision: "Phase 0 Parallel Execution: reduces critical path by ~0.5 sessions."
3. Note in Session 0 entry criteria for Plan 01: "Plan 03/04 Phase 0 taxonomy is OPTIONAL pre-input."
**Impacts:** Plan 01 better-targeted fix. Plan 03/04 Phase 0 executes earlier. Budget unchanged.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** rejected
**Adversarial note (Cross-Plan Novel Gaps):** P4-IMP-20 (other group) already captures this exact parallelism with near-identical How steps. The only marginal addition ("Phase 0 output informs Plan 01 fix targeting") is weak: taxonomy discovers YAML-fixable vs builder-fixable AFTER clustering 65 FPs, but Plan 01 already knows its fix target from Session 0 task (c). Implementing IMP-34 on top of IMP-20 produces a duplicate decision entry.

### P4-IMP-35: 7-contract corpus limitation never acknowledged as statistical constraint
**Target:** CONTEXT
**What:** All quantitative claims (precision 13.3%, recall 83.3%, FP counts, validity coefficients) are from N=7 contracts with N=65 FPs. The domain boundary does not acknowledge this as a statistical limitation. The word "overfitting" does not apply here — overfitting requires a model that learns. What actually happens is narrower: metric improvement is measured on the same contracts that produced the baseline FPs, so Plan 01's precision delta measures "this exclusion works on these contracts," not "this exclusion works in general."
**Why:** That distinction is worth stating — it frames what 3.1e results actually prove for downstream consumers.
**How:**
1. Add to domain "What this phase does NOT deliver": one sentence — "Generalizability claims beyond the 7-contract corpus. All precision, recall, and validity metrics are in-sample."
2. Add Assumption 6: "All 3.1e results are in-sample on 7 DamnVulnerableDefi contracts. Scope tags in Plan 03/04 output flag candidate generalizability; they do not prove it. Out-of-sample validation is a 3.1f concern."
3. Do NOT add a Plan 05 Unobserved Phenomena routing instruction — Plan 05 already states "Mandatory Unobserved Phenomena list" with routing rules. Pre-populating defeats empirical discovery.
**Impacts:** Frames 3.1e results correctly for downstream consumers.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Cross-Plan Novel Gaps):** The original How step 3 (route corpus limitation to Plan 05 as infrastructure item) assumes the experimenter will forget to include it in the Unobserved Phenomena list. But IMP-22 already adds quality criteria requiring each item to name an artifact that revealed the gap. Pre-populating the list from CONTEXT defeats the purpose of empirical discovery. Steps 1 and 2 are sufficient; step 3 is paternalistic toward Plan 05.

### P4-IMP-36: Cost measurement is mentioned but never structured as a deliverable
**Target:** CONTEXT
**What:** Promote cost capture from incidental mention in Plan 01 text to a named exit artifact with a concrete schema. Plan 02 calibration chain logging already includes `cost_tokens` per scoring call — no new output file needed for Plan 02, only an aggregation note.
**Why:** Cost data is critical input to 3.1f (loop economics) and 3.1c (heuristic-only vs LLM tiers). Without structured capture NOW, future phases must re-run experiments just to measure cost.
**How:**
1. Add to Plan 01 named deliverables: `.vrs/experiments/plan-01/cost-summary.json` with fields `{level: "full_pipeline"|"targeted"|"lens_only", token_count, wall_clock_seconds, contracts_processed, cost_per_FP_removed}`. This is the only new file needed.
2. Add to domain deliverables: "Per-experiment cost data (token counts and wall-clock time) as first empirical input to 3.1f loop economics."
3. For Plan 02: add one sentence to calibration chain logging — "Aggregated cost per dimension per anchor is derivable from llm-scores.jsonl — no separate cost-summary.json needed."
4. Do NOT add Plan 05 guidance — cost data from named artifacts is already in scope of Plan 05's Track A.
**Impacts:** Plan 01 gains small additional output artifact. 3.1f benefits directly.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Cross-Plan Novel Gaps):** The original How creates three new artifacts and adds a guidance constraint. Steps 2-4 of the original are redundant given existing structure. One clean artifact (Plan 01 cost-summary.json) captures the essential gap. IMP-39 is tightly coupled — IMP-39 defines the formula that cost-summary.json must support. These must be implemented together.

### P4-IMP-37: Plan 02 synthetic anchors evaluate rubric self-consistency, not evaluation quality
**Target:** CONTEXT
**What:** Plan 02's real gap is not "synthetic vs real" but "no falsification path for the recommendation matrix." The matrix is derived from anchors designed by the rubric writer, scored with a rubric they calibrated. Under these conditions, LLM_adds_signal on >= 2 dimensions is structurally guaranteed given a functional LLM API. The matrix cannot be wrong given these conditions — it is a tautology.
**Why:** The Phase A/Phase B structure is the right intuition but the wrong fix. "Add Plan 01 transcript capture as precondition" creates a hard dependency on a capability Plan 01 was never designed to deliver. Plan 01 captures per-function firing JSON, not agent reasoning transcripts. The actionable fix is adding falsification conditions to the matrix itself.
**How:** See P4-ADV-7-01 for the replacement approach (falsification conditions independent of anchor ordering).
**Impacts:** Plan 02 confidence MEDIUM. No scope change to Plan 01.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** Plan 02
**Classification:** structural
**Status:** reframed
**Adversarial note (Cross-Plan Novel Gaps):** Requiring Plan 01 to capture agent evaluation transcripts silently expands its scope and creates a new failure mode: if Plan 01 does not produce a transcript, Plan 02's matrix is permanently downgraded to "preliminary indication." The framing of "synthetic = self-consistency = bad" misreads what Plan 02 is for: it is specifically designed to test rubric calibration capability. The real problem is that the matrix has no falsification condition. See P4-ADV-7-01.

### P4-IMP-38: Graph quality is the unacknowledged single point of failure
**Target:** CONTEXT
**What:** Add one explicit assumption covering the 200+ property coverage gap and add "graph-property-error" as a fourth action category to Plan 03/04 Phase 0 action mapping. Do NOT frame as "single point of failure" — if graph errors exist in untested properties, experiments still measure the correct behavior of the TESTED properties. The coverage gap is a gap in diagnostic capability, not in experiment validity.
**Why:** Plan 03/04's taxonomy might discover FP clusters caused by OTHER graph properties being wrong. Adding "graph-property-error" as an action category in Phase 0 gives a bucket for this case. The category can only be selected when a cluster is NOT explainable by pattern logic AND the analyst suspects graph construction.
**How:**
1. Add Assumption (after existing 5): "Graph construction correctness is verified only for 4 properties tested in Session 0 (has_access_gate, state_mutability, is_constructor, has_external_calls). The remaining ~196 properties per function are assumed correct. If Plan 03/04 Phase 0 discovers FP clusters with no YAML-fixable or builder-fixable explanation, graph-property-error is a candidate diagnosis."
2. In Plan 03/04 Phase 0 action mapping, add "graph-property-error" as fourth category. Selection criterion: "FP cluster has no pattern-logic explanation — properties used by the pattern are computing unexpected values."
3. Add to deferred: "Systematic BSKG graph quality audit — representative sample of 200+ properties/function. Target: 3.1c or Phase 5. Priority: schedule only if Phase 0 finds >= 1 graph-property-error cluster."
**Impacts:** Plan 03/04 Phase 0 gains one additional action category (trivial). Assumption section gains explicit coverage gap.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Cross-Plan Novel Gaps):** Without a concrete selection criterion, the "graph-property-error" category would be a dead branch — analysts will default to "architectural" before concluding graph error. The How addresses this by giving the criterion: "properties used by the pattern are computing unexpected values." With that criterion, it has a narrow but valid use case as a diagnostic label.

### P4-IMP-39: Missing explicit connection between Plan 01 cost data and 3.1f viability gate
**Target:** CONTEXT
**What:** Add one decision entry naming the two cost formulas Plan 01 must compute, and add two computed metrics to Plan 01's named deliverables. The formula `cost_per_FP_removed` is derivable from data Plan 01 already collects.
**Why:** Defining the threshold now is premature. But defining WHAT the threshold applies to is not. `cost_per_FP_removed = total_pipeline_cost / FPs_removed` requires only total pipeline cost (already captured) and FP delta (Plan 01's primary output). The formula is data-independent in structure.
**How:**
1. Add decision "Loop Economics Formula": "Plan 01 computes `cost_per_FP_removed = total_pipeline_cost / FPs_removed` and `LOC_per_FP_removed = LOC_changed / FPs_removed`. These are Plan 01's contribution to 3.1f loop economics. No threshold set in 3.1e — threshold is a 3.1f decision."
2. Add to Plan 01 deliverables: "(c) cost_per_FP_removed (tokens and wall-clock), (d) LOC_per_FP_removed." Remove `cost_per_TP_verified` — Plan 01 does not run verification; TP preservation is a regression check, not a verification cost measurement.
3. This improvement is tightly coupled with IMP-36 (cost-summary.json). IMP-36 defines the artifact; IMP-39 defines what computed metrics that artifact must contain. Implement together.
**Impacts:** Plan 01 gains two computed metrics (data already collected). 3.1f planning has explicit formula.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Cross-Plan Novel Gaps):** The `cost_per_TP_verified` formula in the original is a category error. Detection cost (Plan 01) and verification cost (Stage 7 of the 9-stage pipeline) are different operations with different token profiles. Including it in Plan 01 deliverables would either require running the agent debate loop (out of scope) or produce a misleading figure. Removing it is correct.

## Adversarial CREATE Items

### P4-ADV-1-01: counting-policy.md should be pre-generated from existing Decisions text, not produced under Session 0 time pressure
**Target:** CONTEXT
**What:** The Finding Counting Policy decision in CONTEXT Decisions section already contains the complete methodology text. Change to: generate `counting-policy.md` as a PRE-SESSION artifact by extracting the existing Decisions text verbatim. Add to Session 0 pre-flight: "Verify `.vrs/experiments/counting-policy.md` exists (pre-generated). If missing, create from Decisions section before starting task (a)."
**Why:** Session 0 task (a) is already time-pressured (per P4-IMP-05). Requiring a prose document mid-task creates an interruption during data collection. The content already exists — extraction is a 2-minute copy, not a 20-minute authoring task.
**How:**
1. Change the Finding Counting Policy decision to: "Pre-generate `counting-policy.md` before Session 0. Content: extract this decision verbatim. Path: `.vrs/experiments/counting-policy.md`."
2. Add to Session 0 pre-flight checklist: "[ ] `.vrs/experiments/counting-policy.md` exists."
3. Remove from task (a) output column.
**Impacts:** Session 0 task (a) time pressure reduced. Plan 01 counting clarity unchanged.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** cosmetic
**Status:** implemented
**Source:** Adversarial review (Session 0 Integrity)
**Cross-references:** P4-IMP-06, P4-IMP-05
**Adversarial note (Session 0 Integrity):** P4-IMP-06 correctly identifies the orphan but proposes fixing it by adding to an already overloaded task (a). The right fix is to pre-generate before the session. The counting-policy content exists; the file just needs to be written.

### P4-ADV-2-01: Outcome C reframe — 200 LOC is a scope boundary marker, not a quality judgment
**Target:** CONTEXT
**What:** Falsification criterion C for Outcome C should read: "If fix requires >200 LOC: STOP. Record finding: 'YAML-only fix insufficient for access-tierb-001; builder-layer intervention required, estimated N LOC.' Route to Plan 03/04 action_map as {builder-fixable}. This is the MOST INFORMATIVE Outcome C — it defines the boundary between YAML-addressable and builder-addressable FPs. Do NOT execute the builder fix within Plan 01. Outcome C is a measurement outcome, not a failure." Remove "scope mis-set" language entirely. Add to domain deliverables: "If Outcome C: LOC estimate and builder-fix characterization."
**Why:** The current "scope mis-set" framing treats the most informative outcome (builder fix needed) as a failure. The correct framing: Outcome C is a successful measurement — it answers "is YAML sufficient?" with "no, and here is why." The 200 LOC limit protects against scope creep into 3.1c territory, not against informativeness.
**How:**
1. In Plan 01 Falsification criteria: replace "Outcome C fails if fix requires >200 LOC (scope mis-set)" with the text above.
2. In Plan 01 "What it delivers": add "(c) If builder fix required: LOC estimate + characterization as Plan 03/04 action_map input."
3. Remove the Session 0 entry criteria text "LOC ~100-200, confidence drops to MEDIUM" — this anticipates an outcome that should be discovered, not pre-prejudiced.
**Impacts:** Plan 01 scope unchanged. Outcome C becomes a measurement, not a failure.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Source:** Adversarial review (Plan 01 Experimental Rigor)
**Cross-references:** P4-IMP-08
**Adversarial note (Plan 01 Experimental Rigor):** IMP-08's proposed human-approval gate is a weaker version of the right fix. The strong version preserves the 200 LOC boundary as inviolable but reframes what crossing it MEANS — a measurement result, not a scope failure.

### P4-ADV-2-02: Mixed Outcome B pre-registration for partial FP reduction across root causes
**Target:** CONTEXT
**What:** Plan 01 has no pre-registered interpretation for a MIXED Outcome B result (partial FP reduction across different root causes). The current falsification criteria treat Outcome B as binary. But if the YAML fix removes view/pure FPs but leaves modifier-recognition FPs untouched, the interpretation is ambiguous without pre-registration.
**Why:** Mixed results are the EXPECTED outcome given that access-tierb-001 fires on at least two distinct root causes. Pre-registering the mixed-result interpretation prevents post-hoc rationalization and aligns with the Pre-Registration Principle already established in Decisions.
**How:**
1. Add to Plan 01 "Falsification criteria" section: "Mixed Outcome B (partial): if YAML fix removes subset S1 of FPs but leaves subset S2 untouched, pre-registered interpretation: Outcome B = CONFIRMED for S1 root cause, FINDING = S2 requires different intervention. Report: (a) FPs removed by root cause, (b) FPs remaining by root cause, (c) route S2 root causes to Plan 03/04 action_map."
2. Add to domain deliverables: "If Mixed Outcome B: per-root-cause FP reduction table."
**Impacts:** Plan 01 gains pre-registered interpretation for most likely outcome.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Source:** Adversarial review (Plan 01 Experimental Rigor)
**Cross-references:** P4-IMP-09, P4-IMP-10
**Adversarial note (Plan 01 Experimental Rigor):** IMP-09 adds UnstoppableVault as observation target and IMP-10 adds the modifier-recognition branch. Their interaction reveals that the executor will almost certainly encounter a mixed result. Neither pre-registers how to interpret it. This closes that gap.

### P4-ADV-3-01: Three-instrument measurement model for Plan 02
**Target:** CONTEXT
**What:** Plan 02 needs a three-instrument measurement model, not a primary/secondary ordering. Instrument 1 (ordering): pairwise comparison — for each of 3 pairs, `claude -p` asks "which demonstrates better {dimension} reasoning?" Records winner + confidence. Instrument 2 (scale calibration): absolute scores — retained ONLY to feed 3.1c rubric calibration data, NOT for go/no-go. Instrument 3 (divergence evidence): LLM explanation text — does the LLM name something the heuristic formula cannot compute? Go/no-go: pairwise ordering consistent with intended ranking on >= 2 dimensions (Instrument 1) AND LLM explanation contains at least one dimension-specific insight not derivable from tool/query count (Instrument 3).
**Why:** IMP-11 and IMP-13 pull Plan 02 in opposite directions (score-ordering vs evidence-content). Separating instruments by question resolves the conflict, preserves pairwise ordering information, and makes go/no-go both rigorous and achievable.
**How:**
1. In Plan 02 "Decision protocol (n=3-correct)" section: replace single-instrument Spearman rho with three-instrument model.
2. Reframe divergence hypotheses as pairwise ordering predictions, not score predictions.
3. Add LLM explanation content check: "for each go/no-go dimension, record whether LLM explanation names a specific reasoning element the heuristic cannot detect."
4. Retain absolute scoring in calibration chain log only.
**Impacts:** Plan 02 go/no-go mechanism changes. Session estimate may grow to 1.25 sessions.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Source:** Adversarial review (Plan 02 Statistical Design)
**Cross-references:** P4-IMP-11, P4-IMP-13
**Adversarial note (Plan 02 Statistical Design):** IMP-11 and IMP-13 interact: pairwise scores and evidence-based success are not the same test. The three-instrument model is the synthesis that makes both items actionable without contradiction.

### P4-ADV-3-02: Non-determinism protocol matching three-instrument model
**Target:** CONTEXT
**What:** Add a non-determinism protocol that matches the three-instrument model from P4-ADV-3-01. Instrument 1 (pairwise): run each of 3 pairwise comparisons twice. If winner flips, flag "LLM_unreliable on {pair}." Instrument 3 (explanation content): pre-register before any scoring a minimal element list per dimension. Check element presence across calls. Instrument 2 (absolute score): run once for calibration data; variance not measured (not decision-relevant). Cost: 6 additional pairwise calls + pre-registration step (~10 min).
**Why:** IMP-15's duplicate-absolute-scoring protocol applies variance detection to the wrong instrument. Non-determinism at the primary decision instrument (pairwise ordering) is what can invalidate go/no-go.
**How:**
1. In Plan 02 "LLM call failure handling" section, add variance protocol: "For each pairwise comparison (3 pairs per dimension), call twice. Record both winners. If flip: mark dimension as LLM_unreliable, exclude from go/no-go count."
2. Add pre-registration step before scoring: "For each go/no-go dimension, write minimal element list (2-3 specific reasoning signals). Record to `.vrs/experiments/plan-02/element-preregistration.json` before first scoring call."
3. Absolute score: single call retained for calibration chain log.
**Impacts:** Plan 02 gains variance protocol at the correct instrument. Cost: ~6 additional calls.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Source:** Adversarial review (Plan 02 Statistical Design)
**Cross-references:** P4-IMP-15, P4-IMP-11, P4-ADV-3-01
**Adversarial note (Plan 02 Statistical Design):** IMP-15 identifies the right problem (non-determinism) but the fix assumes absolute scoring remains primary. Once the three-instrument model is adopted, the variance protocol must be re-targeted to pairwise ordering.

### P4-ADV-4-01: Compound degradation rule conflates two independent failure modes
**Target:** CONTEXT
**What:** The compound degradation rule merges corpus diversity failure with rubric calibration failure. These are independent: corpus-dominated failure routes to corpus expansion (3.1f target), rubric failure routes to rubric redesign (3.1c target). Split into two independent branches with separate remediation paths.
**Why:** When Phase 2 produces INCONCLUSIVE from corpus dominance, the executor cannot tell whether 3.1c needs to fix the rubric or 3.1f needs to expand the corpus. Two different downstream consumers need to know which failure mode fired.
**How:**
1. Split compound degradation rule into two independent branches: (a) "Corpus degradation: if Phase 0 produces < 3 categories OR largest category > 75% — finding = 'corpus-limited.' Routes to Plan 05 Unobserved Phenomena as {corpus_expansion: requires-infrastructure, target: 3.1f}. Phase 1 and Phase 2 proceed UNCHANGED — corpus-limited is an annotation, not a gate." (b) "Rubric degradation: if Plan 02 divergence hypotheses 0/3 or 1/3 — finding = 'rubric-insufficient.' Routes to 3.1c. Phase 2 proceeds but results annotated 'rubric-insufficient.'" (c) "Both degrade: Phase 2 produces INCONCLUSIVE. Annotation records WHICH modes degraded."
2. Phase 0 exit artifact: add `dominance_ratio` field as OBSERVATION (not a gate).
**Impacts:** Phase 2 proceeds in more cases (corpus-dominated alone no longer triggers INCONCLUSIVE). Remediation paths become explicit.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Source:** Adversarial review (Plan 03/04 Threshold Coherence)
**Cross-references:** P4-IMP-16, P4-IMP-17
**Adversarial note (Plan 03/04 Threshold Coherence):** IMP-16 and IMP-17 together add conditions to the compound degradation rule without examining whether the rule's conflation is itself the problem. Corpus domination is a permanent structural property; rubric failure is a fixable quality deficiency. These need separate remediation paths.

### P4-ADV-4-02: Phase 1 Haiku generation needs a plausibility check, not a heuristic floor gate
**Target:** CONTEXT
**What:** Phase 1's Haiku quality gate operates at the upper bound (heuristic >= 70: too easy, hand-craft harder). No gate checks whether Haiku produced transcripts plausible enough to be valid adversarial test cases. The correct check is structural plausibility, not heuristic score.
**Why:** A heuristic floor gate (>= 50) conflates "Haiku gamed the heuristic" with "Haiku produced usable content." A score of 30 could mean either realistic bad-reasoning transcripts (useful for LLM lower-bound testing) or incoherent noise (useless). The score cannot distinguish them; human spot-check can.
**How:**
1. Add to Phase 1, after Haiku generation: "Plausibility spot-check: sample 2 transcripts. Each must contain: (a) at least 2 tool calls in Claude Code format, (b) reference to a contract name from the 7-contract baseline, (c) at least one alphaswarm command or BSKG query (even if fabricated). If either fails: escalate to Sonnet for that archetype. Record model tier in archetype-count.json."
2. Remove the heuristic >= 50 floor gate from IMP-18's proposed How.
3. The existing upper-bound gate (heuristic >= 70 AND LLM >= 70: hand-craft harder) is unchanged.
**Impacts:** Phase 1 gains plausibility gate. ~1 minute per transcript check.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Source:** Adversarial review (Plan 03/04 Threshold Coherence)
**Cross-references:** P4-IMP-18
**Adversarial note (Plan 03/04 Threshold Coherence):** IMP-18 adds a gate that tests the wrong property. The capability concern is content plausibility, not heuristic score. Haiku generating a heuristic-30 transcript is expected — it might be the best "obviously bad" example.

### P4-ADV-5-01: Plan 05 success criterion needs a minimum-necessary contract replacing both the 80% threshold and composability test
**Target:** CONTEXT
**What:** Replace Plan 05's pre-registration success criterion with: "(a) no schema field exists without an observed data justification (existing failure criterion, unchanged); (b) a field-provenance annotation exists for every schema field, mapping it to the experiment artifact that produced the data; (c) schemas are annotated 'incomplete' for phenomena where data exists but structure is ambiguous." Delete the 80% coverage threshold. Do not add the composability join test as a gate.
**Why:** The 80% threshold measures completeness of coverage — the wrong question. The composability test fixes the direction but introduces binary pass/fail on implementation-specific join logic. The minimum-necessary contract asks the right question: "Is every schema field grounded in observations?" Field-provenance annotation also feeds 3.1c directly.
**How:**
1. In Plan 05 pre-registration block, replace "Success: schemas capture >= 80% of observed data fields" with the three-part criterion above.
2. Add output artifact: `.vrs/experiments/plan-05/field-provenance.md` — markdown table with columns: schema_name, field_name, source_experiment, source_artifact, observed_data_example.
3. Keep failure criterion unchanged: "Failure: schemas require fields no experiment produced data for."
**Impacts:** Plan 05 success criteria become harder but more meaningful.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plans 01, 02, 03/04
**Classification:** structural
**Status:** implemented
**Source:** Adversarial review (Plan 05 Dependency & Quality)
**Cross-references:** P4-IMP-23, P4-IMP-30
**Adversarial note (Plan 05 Dependency & Quality):** IMP-23 correctly diagnoses the 80% threshold as wrong but the composability replacement is also wrong — it transforms Plan 05 from "extract schemas" into "prove schemas compose." The field-provenance contract is the right abstraction: lightweight enough for 0.5 sessions, anti-anti-pattern, and produces an artifact 3.1c can use.

### P4-ADV-6-01: Session 0 behavioral-property probe should replace rename-and-detect smoke test
**Target:** CONTEXT
**What:** Replace the proposed "rename withdraw → processPayment, rebuild, run detection" stretch task with a focused graph-builder behavioral-property probe: search `kg/builder/` source for any string containing common function name patterns used to ASSIGN properties. If found, flag 'name-dependent property assignment: {file:line}' — architectural finding for 3.1c. Additionally, query the graph for one function known to fire access-tierb-001 and confirm behavioral property assignment path via source inspection.
**Why:** The rename+detect approach conflates graph builder name-dependence (architectural flaw) with pattern YAML name-dependence (YAML flaw). The behavioral-property probe isolates the architectural question in 5-10 minutes vs 25-35 minutes. If the builder uses name heuristics anywhere, it will appear as a property-assignment failure.
**How:**
1. Add to Session 0 task (c): "Name-dependence check: search `kg/builder/` source for any string containing common function name patterns ('withdraw', 'transfer', 'swap', etc.) used to ASSIGN properties. If found, flag 'name-dependent property assignment: {file:line}' — architectural finding for 3.1c."
2. Add as 5-minute secondary diagnostic in task (c): "Query the graph for one function known to fire access-tierb-001 — confirm behavioral property assignment path via source inspection, not pattern execution."
3. Retire the Session 0 rename+detect stretch task from P4-IMP-26.
**Impacts:** Session 0 task (c) gains 5-10 minutes of diagnostic work. No scope expansion.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Source:** Adversarial review (Strategic Alignment)
**Cross-references:** P4-IMP-26
**Adversarial note (Strategic Alignment):** The behavioral signature thesis is the project's central architectural claim. Testing it via a name-swap smoke test risks false positive (pattern still fires because YAML exclusions don't reference names) or false negative (pattern stops for unrelated reasons). A source-level audit of the builder's property assignment logic gives a definitive answer in less time.

### P4-ADV-7-01: Plan 02 recommendation matrix has no falsification condition independent of anchor design
**Target:** CONTEXT
**What:** Plan 02 produces a per-dimension recommendation matrix ({LLM_adds_signal | LLM_equivalent | LLM_unreliable}). The matrix is derived from rubric-writer-designed anchors scored with a rubric calibrated to order those anchors. Under these conditions, LLM_adds_signal is structurally guaranteed. Add falsification conditions: "LLM_unreliable on dimension D if LLM evidence field cites transcript features that DO NOT EXIST in the anchor (hallucination), OR if two independent scoring calls produce scores differing by > 20 points (variance failure)."
**Why:** Without a falsification condition, the matrix is a measurement of rubric-tuning success, not LLM evaluation capability. A matrix that can only say "LLM_adds_signal" provides no useful information for 3.1c.
**How:**
1. Add to Plan 02 rubric freeze protocol: "After official scoring, run hallucination check: for each LLM evidence string, verify it corresponds to a real element of the scored anchor."
2. Add variance check: compare runs; if > 20 points divergence on any dimension, that dimension is LLM_unreliable regardless of ordering result.
3. Add to Plan 02 pre-registration: "LLM_unreliable is confirmed (not inferred) when hallucination or variance failure is detected. LLM_adds_signal requires BOTH correct ordering AND absence of hallucination AND variance < 20 points."
4. Update domain deliverable: "Per-dimension LLM evaluation recommendation matrix with per-dimension falsification status."
**Impacts:** Plan 02 gains falsification conditions. No scope expansion.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** Plan 02
**Classification:** structural
**Status:** implemented
**Source:** Adversarial review (Cross-Plan Novel Gaps)
**Cross-references:** P4-IMP-37, P4-IMP-13, P4-IMP-15
**Adversarial note (Cross-Plan Novel Gaps):** IMP-37 identified self-consistency, IMP-13 identified circularity, IMP-15 identified non-determinism. These three items together reveal a systemic gap: Plan 02 has no positive-control falsification path. This item provides that condition through hallucination detection and variance checks — independent of anchor ordering.

## Post-Review Synthesis Items

### P4-SYN-01: Pre-registration completeness is a phase-wide structural gap, not a per-plan defect
**Target:** CONTEXT
**What:** Every plan in the phase has at least one decision gate that is either (a) contradictory with another plan's gate, (b) missing an interpretation rule for the most likely outcome, or (c) lacking a falsification condition. P4-IMP-04 found no handling for baseline deviation. P4-IMP-21 found contradictory threshold systems in Plan 03/04. P4-ADV-2-02 found no pre-registered mixed-Outcome-B interpretation. P4-ADV-7-01 found the Plan 02 matrix has no falsification condition. Each reviewer fixed their plan's instance in isolation. The cross-cutting pattern: the Pre-Registration Principle declared in CONTEXT Decisions ("Every experiment must specify, BEFORE execution: (a) success, (b) failure, (c) ambiguous-middle") is not applied uniformly — it is applied to named outcomes but not to the most likely outcome (mixed/partial results) or to measurement instruments (the matrix).
**Why:** Fixing pre-registration gaps one-at-a-time means each future pass will continue finding the same category of defect in different plans. A phase-level pre-registration checklist applied before Session 0 would catch remaining gaps structurally, rather than requiring another adversarial pass per plan.
**How:**
1. Add to CONTEXT `<decisions>` a "Pre-Registration Checklist" decision: "Before Session 0 executes, each plan must pass: (a) every named outcome has success/failure/ambiguous-middle interpretation; (b) every measurement instrument has at least one falsification condition that is not circular with the instrument's design; (c) the most likely PARTIAL outcome (mixed result across root causes) has a pre-registered interpretation; (d) every go/no-go threshold is consistent with all other plans' thresholds for the same metric."
2. Apply checklist to Plans 01-05 as a final pre-session review step. Flag any gap found during that review as a blocking item.
3. Do NOT apply this retroactively to items already addressed by P4-IMP-04, P4-IMP-21, P4-ADV-2-02, P4-ADV-7-01 — those are already resolved. Checklist is forward-facing for any plans added or modified before Session 0.
**Impacts:** All plans (pre-registration completeness gate)
**Components:** P4-IMP-04, P4-IMP-21, P4-ADV-2-02, P4-ADV-7-01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
**Adversarial note (ADV Validation):** Withstood scrutiny on concreteness (How is specific, bounded, sequential), prerequisite correctness (CONTEXT → no code required), and integration (non-retroactive, respects prior fixes). Item enables systematic gap prevention in future phases.

### P4-SYN-02: Plan 02's entire validation chain uses only researcher-constructed inputs — no external grounding at any layer
**Target:** CONTEXT
**What:** P4-IMP-13 (calibration circular), P4-IMP-14 (trivially confirmable hypothesis), P4-IMP-37 (matrix tautological under synthetic conditions), and P4-ADV-7-01 (hallucination check addresses output integrity, not ground-truth) each fix one layer of Plan 02's validation chain in isolation. Viewing them together reveals a deeper pattern: ALL layers — rubric design, anchor design, calibration, go/no-go, and falsification — use researcher-constructed synthetic inputs. Even with all individual fixes applied, the result is evidence that the LLM can correctly order researcher-designed synthetic transcripts. This says nothing about whether the LLM provides reliable signal on real agent transcripts, which may be structurally different from synthetic anchors in ways the researcher did not anticipate. The held-out anchor (P4-IMP-13) is an improvement but is still researcher-designed.
**Why:** The individual fixes are necessary but insufficient. The phase needs at least one externally grounded validation signal — a real agent output that was NOT designed by the rubric author — to break the closed loop. Even a single real transcript from a prior audit run (if one exists anywhere in the codebase) would serve as an uncontrolled validity check. If no real transcripts exist, Plan 02 should explicitly declare its results as "rubric calibration capability evidence" rather than "LLM evaluation capability evidence" — a narrower and honest claim that 3.1c can build on without overextending.
**How:**
1. Search `.vrs/` and `tests/` for any existing agent transcript files (non-synthetic) before Plan 02 begins. If found: add one as an uncontrolled post-freeze scoring call. Do not adjust rubric based on its score — record the score as "out-of-distribution validity check."
2. If no real transcripts exist: add to Plan 02 pre-registration a scope declaration: "Plan 02 results scope: rubric calibration capability on researcher-designed synthetic transcripts. Generalizability to real agent transcripts is an open question addressed in Plan 02 Phase B (real transcript scoring, requires at least 1 real transcript from any prior run)."
3. Add to domain deliverables: "Plan 02 scope declaration (synthetic-only or includes out-of-distribution check)."
4. Add to Plan 05 Unobserved Phenomena routing: "If Plan 02 is synthetic-only: 'real-transcript validity: requires-infrastructure, target: 3.1c' as a mandatory item."
**Impacts:** Plan 02, Plan 05 Unobserved Phenomena, domain deliverables
**Components:** P4-IMP-13, P4-IMP-14, P4-IMP-37, P4-ADV-7-01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Session 0 (transcript provenance verification output)
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
**Adversarial note (ADV Validation):** Item identifies a real closed-loop risk with high confidence. Enhanced to add depends_on_plans: Session 0 (transcript provenance output). The search task is bounded and deterministic; conditional logic in How is appropriate for data-driven decision branching.

### P4-SYN-03: Exit artifact provenance is undefined phase-wide — a recurring anti-pattern requiring a single structural fix
**Target:** CONTEXT
**What:** P4-IMP-06 found counting-policy.md is orphaned (content exists but no one creates the file). P4-ADV-1-01 proposed pre-generating it from existing text. P4-IMP-22 found the Unobserved Phenomena list has no quality criteria. P4-ADV-5-01 proposed a field-provenance artifact for Plan 05. P4-IMP-25 found Plan 02's dependency in Plan 05 preconditions was implicit. Each item addresses one artifact's authorship problem in isolation. The phase-wide pattern: exit artifacts are named as outputs but not specified for (a) who generates them, (b) whether content can be pre-generated from existing CONTEXT text vs must be produced during the session, and (c) minimum content schema. This is the same class of problem in every plan — repeated discovery of "orphaned deliverables."
**Why:** Addressing artifact provenance plan-by-plan ensures each future pass will find the same gap in newly added artifacts. A single phase-level pre-flight manifest — listing every named exit artifact with authorship and minimum content structure — solves this structurally. The pattern also explains why Session 0 is chronically time-pressured: artifacts that could be pre-generated from existing CONTEXT text are instead being authored under session time constraints.
**How:**
1. Add to CONTEXT a `<artifact_manifest>` section listing all named exit artifacts across all plans and Session 0 with: (a) artifact path, (b) authorship: pre-generated | session-produced | post-session, (c) minimum content schema (field list or file format), (d) source: CONTEXT-derivable | experiment-data | human-judgment.
2. For all CONTEXT-derivable artifacts (counting-policy.md, any artifact whose content already exists verbatim in CONTEXT decisions): mark as pre-generated and add to a session pre-flight checklist.
3. For session-produced artifacts: verify they are in the correct plan's task table, not orphaned in the Decisions section.
4. This is a one-time audit. Future artifact additions should specify authorship inline when first introduced.
**Impacts:** Session 0, Plans 01-05 (artifact clarity); prevents recurring orphaned-deliverable finding in future passes
**Components:** P4-IMP-06, P4-ADV-1-01, P4-IMP-22, P4-ADV-5-01, P4-IMP-25
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
**Adversarial note (ADV Validation):** Item passes all validation gates. Artifact provenance tracking addresses a real recurring pattern across P1-P4. The manifest design is future-proof (supports "future artifact additions specify authorship inline"). Scope is appropriately limited to one-time audit plus forward guidance.

### P4-CSC-01: P4-IMP-12 triggers held-out anchor design constraint conflict with generalization test
**Target:** CONTEXT
**What:** P4-IMP-12 requires GOOD and MEDIOCRE anchors to have identical unique tool counts (to produce the same heuristic score and thus trigger the discriminability test). P4-IMP-13 requires a held-out anchor written before calibration to test rubric generalization. The cascade: if the rubric is calibrated exclusively on anchors with unique_tool_count = N, the held-out anchor should have a DIFFERENT unique tool count to test that the rubric does not merely recognize the structural signature of the calibration anchors. But neither item specifies the held-out anchor's tool count constraint. If the held-out anchor is designed with the same unique tool count as the calibration anchors, it does not test generalization — it tests whether the rubric correctly scores a structurally identical anchor it was not directly trained on, which is a much weaker validity signal.
**Why:** Without specifying that the held-out anchor must differ structurally from calibration anchors on at least one heuristic dimension, the held-out anchor becomes a near-duplicate of the BAD calibration anchor (zero-graph, no node IDs) and provides no information about whether the rubric generalizes to structurally novel transcripts. The generalization test becomes trivial: "does a zero-graph anchor score low?" is answered by the rubric design, not by rubric quality.
**How:**
1. In Plan 02, add held-out anchor design constraint table: "Held-out anchor must differ from all calibration anchors (GOOD, MEDIOCRE, BAD) on at least ONE of: (a) unique_tool_count (calibration=3, held-out in {1,2}), OR (b) bskg_query_count (if calibration=0, held-out >= 1). This ensures the rubric must evaluate CONTENT, not just tool-count pattern."
2. Add to anchor design constraints table: "(e) held-out anchor structural constraint: differs from calibration anchors on at least one specified heuristic dimension per step 1."
3. After post-freeze held-out scoring, record: "held-out unique_tool_count = N, calibration anchors unique_tool_count = M. Structural difference confirmed: yes/no."
**Impacts:** Plan 02 held-out anchor design
**Trigger:** P4-IMP-12
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)
**Adversarial note (ADV Validation):** Cascade rationale is sound — P4-IMP-12 fixes calibration anchor structure, CSC-01 correctly identifies this constrains held-out design. Enhanced to specify allowed differentiation axes (unique_tool_count, bskg_query_count) with parameter ranges rather than vague "any heuristic dimension."

### P4-CSC-02: P4-IMP-22 creates an evidence-anchor requirement that excludes INCONCLUSIVE-experiment gaps from the Unobserved Phenomena list
**Target:** CONTEXT
**What:** P4-IMP-22 adds a mandatory evidence-anchor field to each Unobserved Phenomena list entry: "at least one artifact from Plans 01, 02, or 03/04 (filename + finding) that revealed this gap." This is the right quality gate for gaps that were OBSERVED. But the most important gaps are often those where an experiment produced no signal — the experiment ran, produced INCONCLUSIVE results, and the phenomenon was NOT captured in any artifact. The rubric calibration failure scenario (P4-IMP-17: rubric fails calibration in 3 revisions), the corpus dominance scenario (P4-ADV-4-01: Phase 0 produces degenerate taxonomy), and the LLM hallucination scenario (P4-ADV-7-01: LLM cites non-existent evidence) all produce gaps that are real but may leave no artifact to cite. Under the enhanced quality criteria, these gaps CANNOT be included in the Unobserved Phenomena list — exactly the opposite of what the quality gate is meant to achieve.
**Why:** The evidence-anchor requirement would silently exclude the most important class of negative findings: things that were tried and failed to produce signal. Plan 05 would then pass its quality gate (all entries have artifact evidence) while omitting the failures that matter most for 3.1c design.
**How:**
1. In Plan 05, add a second list entry type alongside the standard evidence-anchored type: "Negative signal entries: for phenomena where an experiment ran but produced INCONCLUSIVE or absent signal, the evidence anchor field is: 'INCONCLUSIVE: {experiment}, {artifact}, {why no signal}.' Example: 'INCONCLUSIVE: Plan 02 rubric calibration, rubric-v1.0.txt, failed calibration in 3 revisions — GOOD-BAD spread never exceeded 25 points.' This counts as a valid evidence anchor."
2. Add to Plan 05 anti-pattern examples: "REJECT: entry with no evidence anchor AND no INCONCLUSIVE note. ACCEPT: entry with INCONCLUSIVE evidence noting which experiment and why no signal."
3. Keep the original rejection criterion unchanged: entries with neither evidence-anchor nor INCONCLUSIVE note are still rejected.
**Impacts:** Plan 05, Unobserved Phenomena list quality criteria
**Trigger:** P4-IMP-22
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)
**Adversarial note (ADV Validation):** Item correctly identifies and fixes a cascade risk from P4-IMP-22. The two-category entry model (evidence-anchored vs INCONCLUSIVE-noted) is simple and preserves both positive and negative findings. Quality gate logic is clear and implementable.

### P4-CSC-03: P4-IMP-21 produces N-dependent verdicts that Plan 05 and 3.1c inherit without N context
**Target:** CONTEXT
**What:** P4-IMP-21 resolves the contradictory threshold systems by making ceil(N/2) the authoritative gameability go-criterion, with N pre-registered in archetype-count.json. The cascade: once archetype-count.json is the source of N, validity-matrix.json reports a verdict ("go" or "no-go") that was produced at a specific N. Plan 05's field-provenance schema (P4-ADV-5-01) maps schema fields to source artifacts but does not capture the N at which a verdict was generated. 3.1c will inherit "gameability matrix: go" from validity-matrix.json without knowing whether that verdict was produced at N=3 (go threshold = 2) or N=8 (go threshold = 4). A "go" at N=3 requires only 2 archetypes caught — a much weaker claim than "go" at N=8. This N-context is erased at the artifact boundary.
**Why:** If 3.1c designs its evaluation infrastructure assuming a gameability verdict produced at N=3 carries the same weight as one at N=8, it may invest in the wrong confidence level for the LLM evaluator's gaming-detection capability. The verdict is the same word; the evidential content is very different.
**How:**
1. Add to validity-matrix.json schema: required field `archetype_n` recording the N value from archetype-count.json at time of Phase 2 execution.
2. Add to validity-matrix.json schema: required field `go_threshold_used` recording ceil(N/2) applied.
3. Add to domain deliverables annotation: "Gameability matrix verdict is N-dependent. 3.1c must read archetype_n from validity-matrix.json before interpreting verdict strength."
4. In Plan 05 field-provenance.md template: add column `verdict_conditions` — for verdict-type fields, record the N and threshold under which the verdict was produced.
**Impacts:** Plan 03/04 Phase 2 exit artifact, Plan 05 field-provenance schema, 3.1c scope
**Trigger:** P4-IMP-21
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** Plan 03/04 (validity matrix schema + execution)
**Status:** implemented
**Source:** Post-review synthesis (cascade)
**Adversarial note (ADV Validation):** Item addresses a real risk: N-dependent verdicts lose their N-context when passed to downstream phases. Enhanced to add depends_on_plans: Plan 03/04 (validity matrix generation). The How field is mechanical and clear — schema extension with metadata capture.

### P4-ADV-8-01: Pre-registered fallback dimension eligibility list for Plan 02 go/no-go
**Target:** CONTEXT
**What:** Plan 02's go/no-go requires "LLM_adds_signal on >= 2 primary-tier dimensions WITH REAL HEURISTIC HANDLERS." The phrase "primary-tier dimensions WITH REAL HEURISTIC HANDLERS" must be resolved to a concrete enumerated list before Session 0, with each dimension's heuristic handler existence verified against `reasoning_evaluator.py` source. Without this enumeration, calibration failure on one dimension leaves the executor facing an undefined question: "can I substitute another dimension, and if so, which ones are eligible?"
**Why:** The current CONTEXT lists 4 dimensions that silently score default-30 (`exploit_path_construction`, `arbitration_quality`, `evidence_weighing`, `investigation_depth`) — these are ineligible regardless of rubric quality. P4-IMP-03 would add a third rubric to Session 0 without verifying whether that third dimension even has a heuristic handler. The fallback mechanism only works if fallback dimensions are confirmed eligible before the session where they might be needed.
**How:**
1. Before Session 0: enumerate all primary-tier dimensions in `ReasoningEvaluator` with heuristic handlers (non-default-30). Record in CONTEXT as "eligible fallback dimensions." Minimum confirmed: `reasoning_depth` (formula at line 384-388), `evidence_quality` (needs handler confirmed). List any additional dimensions with confirmed handlers. This can be done now by reading `reasoning_evaluator.py` — no plan execution required.
2. In Plan 02 go/no-go pre-registration: add "Eligible dimension pool: [list from step 1]. Primary dimensions for Session 0 rubric: `reasoning_depth` and `evidence_quality`. Fallback order if one fails calibration: [next eligible dimension from pool]. If fallback pool is empty (only 2 eligible dimensions exist): go/no-go criterion degrades to 1-dimension minimum — record as scope constraint, not failure."
3. Remove Session 0 task (b) time expansion (Option 3 from P4-IMP-03). Do NOT write rubrics for unconfirmed dimensions during Session 0 — do not commit time to dimensions whose heuristic handlers are unverified.
4. In Session 0 task (b) note: "Rubrics written here: `reasoning_depth` v1.0 and `evidence_quality` v1.0. Fallback dimension if needed: [from step 2 enumeration]."
**Impacts:** Plan 02 go/no-go pre-registration. Session 0 task (b) scope. CONTEXT assumptions section.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Replaces:** P4-IMP-03
**Adversarial note (Interrupted Review Recovery):** P4-IMP-03 adds a buffer by writing more rubrics in Session 0. This replacement fixes the underdetermination at the source: the eligible dimension pool is knowable right now from static code inspection. Once the pool is enumerated and recorded in CONTEXT, the fallback ordering is pre-registered and the executor never faces an improvisation decision. Cross-group interaction: P4-ADV-3-01's three-instrument model assumes "primary tier" is a pre-fixed set — this item grounds that assumption.

## Post-Review Synthesis
**Items created:** P4-SYN-01, P4-SYN-02, P4-SYN-03, P4-CSC-01, P4-CSC-02, P4-CSC-03
**Key insight:** Plan 02's validation chain is fully researcher-constructed with no external grounding at any layer (SYN-02), and this self-referential design is compounded by a phase-wide pre-registration gap (SYN-01) where the most likely partial outcomes — mixed FP results, INCONCLUSIVE experiments, and N-small verdicts — lack interpretation rules that downstream phases can safely inherit.
