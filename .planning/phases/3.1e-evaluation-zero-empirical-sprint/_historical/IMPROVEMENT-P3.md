# Improvement Pass 3

<!--
  Pass 3 focuses on interaction-level issues between plans — how data flows
  across Session 0 → Plan 01 → Plan 02 → Plan 03/04 → Plan 05 pipeline.
  Passes 1-2 established structural integrity of individual plans (70 merged).
  This pass stress-tests the connections between plans.
-->

**Pass:** 3
**Date:** 2026-02-22
**Prior passes read:** 1, 2 (via IMPROVEMENT-DIGEST.md)
**Areas analyzed:** 3 (Measurement Foundation, LLM Evaluation Architecture, Assessment & Synthesis)
**Agents:** 3 improvement + 4 adversarial + pending synthesis
**Status:** complete

<!-- File-level status: in-progress | complete -->

## Pipeline Status

<!-- Auto-populated by workflows. Shows pending actions across ALL passes for this phase. -->

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 0 | 0 | — |
| Research | 0 | 1 | P3-IMP-12 resolved by adversarial review |
| Gaps | 0 | 0 | — |
| Merge-ready | 19 | 0 | 10 enhanced + 5 confirmed + 4 ADV items (all merge-ready after synthesis) |

**Pipeline:** [improve] ✓ → [adversarial] ✓ → [synthesis] pending → [implement] →
**Next recommended:** synthesis (this pass), then /msd:implement-improvements 3.1e

## Adversarial Lenses

| Lens | Brief | Items | Attack Vector |
|------|-------|-------|---------------|
| Measurement Validity | Session 0 was designed as a 1-session prerequisite gate, but these improvements suggest it needs more instrumentation than its time budget allows. | IMP-01, IMP-02, IMP-03, IMP-04, IMP-05 | If Session 0 passes all tasks but the counting/classification foundation is wrong, does Plan 01 measure anything real? |
| LLM Decision Protocol | Passes 1-2 added pre-registration as a principle without verifying the specific pre-registrations are valid — thresholds are impossible, unfalsifiable, or pre-falsified. | IMP-07, IMP-09, IMP-10, IMP-12 | Do these improvements genuinely fix broken decision criteria, or substitute one set of arbitrary thresholds for another? |
| Experimental Realism | Plan 02 grants Claude's Discretion over implementation, yet these improvements prescribe operational specifics for a creative experiment. | IMP-06, IMP-08, IMP-11, IMP-13 | Are these protecting against genuine execution risks, or pre-scripting a creative experiment past the point of useful flexibility? |
| Cross-Plan Integration | Plans 03/04 and 05 handle upstream uncertainty through decoupling, parameterization, and compound failure handling. | IMP-14, IMP-15, IMP-16, IMP-17, IMP-18, IMP-19, IMP-20 | Do improvements make a fundamentally over-coupled plan more robust, or should the response be to split Plan 03/04? |

## Improvements

### P3-IMP-01: Session 0 diagnostic tests functions where has_access_gate already computes correctly
**Target:** CONTEXT
**What:** Session 0 task (c) queries `has_access_gate` on three functions where the property already computes correctly. The diagnostic will pass, giving false confidence. The REAL risk — non-keyword modifiers — is untested. If no corpus function uses non-keyword access control, the entry criterion for Plan 01 ("If property diagnostic reveals has_access_gate not computed correctly") becomes an untestable gate.
**Why:** False confidence from a passing diagnostic is worse than no diagnostic. Plan 01 proceeds assuming the property is validated when it isn't. The entry criterion cannot trigger on a failure case that the diagnostic cannot exercise.
**How:**
1. Identify whether any function in the 7-contract corpus uses access control via: (a) custom modifiers without "only/auth/role/admin/owner/guardian/governor", (b) inline require(msg.sender == ...) without a modifier, or (c) meta-transaction forwarder patterns (NaiveReceiverPool._msgSender). If found, add to task (c).
2. If no such function exists in the corpus, task (c) must document "known coverage gap: keyword-list-based has_access_gate is unvalidated for non-keyword modifier patterns."
3. Mark entry criterion as: "If diagnostic reveals builder bug OR reveals gap in diagnostic coverage itself: Plan 01 scope assessment required."
**Impacts:** Session 0 task (c) interpretation. Plan 01 scope change criteria refinement.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 -- standard test case selection review
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (Measurement Validity): Factually correct but stops halfway. The deeper problem is that Plan 01's scope-change entry criterion becomes an untestable gate if no corpus function exercises the failure path. How rewritten to actively search corpus for non-keyword patterns and update entry criterion accordingly.

### P3-IMP-02: Per-function FP masking by _unique_patterns() deduplication
**Target:** CONTEXT
**What:** `_unique_patterns()` in `test_detection_baseline.py` deduplicates by pattern name per contract. When access-tierb-001 fires on both `flashLoan()` (TP — external call to unverified caller) AND `withdraw()` (FP — safe self-withdrawal) in SideEntranceLenderPool, the harness counts it once as TP. The FP is invisible. Plan 01 must operate at per-function granularity.
**Why:** Plan 01's Outcome B ("measurable FP reduction") cannot be verified with `_unique_patterns()` for intra-contract co-fires. The experiment would report "0 FPs removed" even after a correct fix.
**How:**
1. In Plan 01 "Primary test contracts": "Before fixing, verify which FUNCTIONS access-tierb-001 fires on in SideEntranceLenderPool."
2. In Session 0 task (a): "Record not just FP/TP counts but WHICH FUNCTIONS each pattern fires on."
**Impacts:** Plan 01 fix strategy and delta measurement.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
Adversarial note (Measurement Validity): Original framing "may be TP, not FP" underestimates depth. SideEntranceLenderPool near-certainly has TWO firings: flashLoan (TP) and withdraw (FP). _unique_patterns() dedup masks the FP. Reframed to name the structural defect. See P3-ADV-1-01 for fuller treatment.

### P3-IMP-03: Detection re-run mechanism is unresolved despite Session 0 depending on it
**Target:** CONTEXT
**What:** The `<research_needs>` unchecked item about detection re-run mechanism is unresolved. `test_detection_baseline.py` provides the pipeline via `build_lens_report()`. But pytest module-level `_graph_cache` means a second run reuses the same Python object, making reproducibility testing trivially true by cache hit.
**Why:** Session 0 task (a) needs a cache-independent baseline recording. The mechanism exists but cache lifecycle must be controlled.
**How:**
1. Mark research_needs resolved: "Resolved: `build_lens_report(graph, DEFAULT_LENSES, limit=200)` in `test_detection_baseline.py`."
2. Session 0 task (a): "Build graphs explicitly outside pytest cache lifecycle. Save to `.vrs/experiments/plan-01/baseline-before.json` directly."
3. Cross-reference P3-IMP-04: cache confound and reproducibility are the same root cause.
**Impacts:** Session 0 task (a) time estimate. Removes ambiguity.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 -- mechanism already exists
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (Measurement Validity): Mechanism exists but "use the existing test infrastructure" has a cache confound. The How rewritten to require building graphs outside pytest cache lifecycle. Research need resolved for mechanism location.

### P3-IMP-04: Plan 01 Outcome A (reproducibility) is either trivially true or measures the wrong thing
**Target:** CONTEXT
**What:** "Run identical detection twice, check count stability" is trivially true on cached graphs or non-deterministic from Slither. No informative middle ground.
**Why:** Should specify detection pipeline reproducibility on pre-built graphs, not end-to-end.
**How:**
1. Specify: "Run `build_lens_report()` twice on the SAME pre-built graph. Tests detection pipeline reproducibility, NOT graph building."
2. Add: "Confirm same graph object produces identical JSON. If output differs on same object, that is a detection engine bug — stop and diagnose."
3. If count instability: diagnose whether from (a) pattern matching (stop), (b) graph difference (builder bug), or (c) classification logic.
**Impacts:** Plan 01 Outcome A falsification criteria become more precise.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (Measurement Validity): Solid. Added note that networkx graph node ordering must be confirmed deterministic between calls, or detection engine bug is lurking.

### P3-IMP-05: Finding counting policy has per-function vs per-pattern discrepancy with tier_a diagnostic
**Target:** CONTEXT
**What:** `_unique_patterns()` counts per-pattern-per-contract. CONTEXT counts per-function. Delta measurement changes 3x. Additionally: NaiveReceiverPool's `maxFlashLoan()` is `external view` — should be excluded by `state_mutability: [view, pure]` none-block. If it fires, the root cause is property evaluation bug (builder fix), not missing YAML exclusion.
**Why:** Effort ratio is the entire point. Counting ambiguity invalidates the experiment. Per-function firing diagnostics distinguish YAML-fixable from builder-fixable FPs.
**How:**
1. Resolve in Finding Counting Policy: "For Plan 01, count per-function-firing. Use raw finding count, not `_unique_patterns()`."
2. Session 0 task (a): "Record BOTH per-pattern and per-function counts."
3. For each FP function, record which tier_a conditions matched AND which none conditions were expected to suppress but didn't. Distinguishes: (a) missing exclusion (YAML fix) vs (b) non-computing exclusion (builder fix).
**Impacts:** Plan 01 effort ratio. All FP counts in CONTEXT.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (Measurement Validity): Correct identification. Enhancement adds: maxFlashLoan (view function) firing despite none-block signals property evaluation bug. Session 0 must capture tier_a match reasons and none-block evaluation to distinguish YAML-fixable from builder-fixable.

### P3-IMP-06: Session 0 rubric output must be LLM-consumable for REASONING_PROMPT_TEMPLATE
**Target:** CONTEXT
**What:** Session 0 task (b) rubric must be LLM-consumable as-is when injected into `{expected}` field. The template at `reasoning_evaluator.py:40` expects scoring guide text, not prose documentation.
**Why:** A rubric shaped for human readers degrades LLM scoring performance. This is not formatting preference — it changes scores. The rubric IS the calibration instrument.
**How:**
1. Add format requirement: "One paragraph per scoring band (90+, 50-70, below 30), stating what agent MUST demonstrate for that band. No headers, no rationale sections."
2. Add concrete negative example: "NOT acceptable: 'reasoning_depth measures how thoroughly the agent considers root causes.' ACCEPTABLE: 'A score of 90+ requires: agent traces specific state change sequence, names graph node IDs, identifies at least one implicit code assumption the vulnerability exploits.'"
3. "LLM-injectable text first. Human documentation layer optional and appended separately."
**Impacts:** Plan 02 wiring step (1). Low effort addition.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (Experimental Realism): Original "structured as template-injectable text" is too vague. Rewrite adds concrete positive example and self-verification test. Claude's Discretion covers {observed}, not {expected} — rubric format does not over-prescribe.

### P3-IMP-07: Spearman rho on n=3 cannot produce the claimed decision thresholds
**Target:** CONTEXT
**What:** With n=3, Spearman rho ∈ {-1.0, -0.5, 0.5, 1.0}. Thresholds 0.6 and 0.8 are unreachable. "Ambiguous zone" is empty. rho=-0.5 covers two structurally different orderings with different diagnostic implications.
**Why:** Decision framework is mathematically impossible. Imported from multi-transcript designs (n>=10) without n=3 adjustment. Creates two primary decision instruments (hypothesis count AND rho) with unspecified conflict resolution.
**How:**
1. Replace with n=3-correct values: rho=1.0 → no inversions (confirmed). rho=0.5 → one adjacent inversion (identify which pair: GOOD/MEDIOCRE or MEDIOCRE/BAD — different diagnoses). rho=-0.5 → two-position inversion (investigate direction). rho=-1.0 → full reversal (failed).
2. Define conflict resolution: "Primary = divergence hypothesis count (2/3 = go). Secondary = rho. If primary says go AND rho <= -0.5, record 'anomalous — ordering contradicts hypothesis results; investigate before 3.1c.'"
3. Remove "Spearman rho >= 0.8 = go, 0.6-0.8 = ambiguous, < 0.6 = no-go" from Plan 02.
**Impacts:** Plan 02 decision protocol becomes executable.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (LLM Decision Protocol): Math confirmed correct (verified by formula on all 6 permutations). Weakness: proposed fix creates two-decision-instrument conflict. Enhanced How adds inversion-direction diagnosis and explicit conflict resolution rule.

### P3-IMP-08: {observed} field for Plan 02 needs semantic validity constraints, not extraction algorithm
**Target:** CONTEXT
**What:** Plan 02 uses hand-written anchor transcripts, not 50-100K production transcripts. There is nothing to compress. The real gap: `{observed}` spec must require semantically discriminative content (reasoning chain quality), not structurally obvious differences. The executor controls both anchor content AND extraction — may write anchors where GOOD/BAD discrimination is trivially structural.
**Why:** If `{observed}` for BAD anchor only shows "no BSKG queries," even a heuristic scores it correctly. LLM evaluator adds signal only when `{observed}` contains content requiring semantic interpretation. Deterministic extraction algorithm is for Plan 03/04, not Plan 02.
**How:**
1. In wiring step (2): "`{observed}` must include content requiring semantic interpretation. Minimum per anchor: stated hypothesis, BSKG query results (not just commands), evidence-to-conclusion reasoning chain. Discriminative signal must be in REASONING CHAIN, not structural presence/absence of tool calls."
2. Anti-validity check: "Before freezing anchors, verify: can three anchors be rank-ordered by reading only `{observed}` excerpts?"
3. Reserve extraction algorithm for Plan 03/04 Phase 2.
**Impacts:** Plan 02 anchor design time. Plan 03/04 inherits extraction for production transcripts.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
Adversarial note (Experimental Realism): Original diagnosed "no extraction strategy" as if compressing production transcripts. Plan 02 anchors are hand-written — nothing to compress. Reframed from extraction problem to semantic validity problem. See P3-ADV-3-01.

### P3-IMP-09: Rubric freeze protocol needs calibration round with measurable spread thresholds
**Target:** CONTEXT
**What:** One GOOD-anchor test call before freeze conflates calibration with measurement. "Face-valid ordering" is subjective. Need quantitative calibration criteria. Per-dimension data from 3.1d shows `reasoning_depth` scored GOOD=70 and MEDIOCRE=70 (identical — heuristic saturates).
**Why:** Risk of locking in bad rubric. "Face-valid" is vulnerable to anchoring bias. Right balance: iterate during calibration (quantitative thresholds), freeze during measurement.
**How:**
1. Replace freeze protocol: "Step 0a: write draft. Step 0b: calibration round — score all 3 anchors, revise freely. Calibration succeeds when: (a) GOOD > MEDIOCRE > BAD AND (b) GOOD-BAD spread >= 30 points AND (c) GOOD-MEDIOCRE gap >= 10 points. Max 3 revisions. Step 0c: freeze when calibration succeeds, record SHA256. Step 0d: re-score all 3 with frozen rubric — official scores."
2. Fallback: "If not achieved in 3 revisions, use best version, record 'rubric calibration incomplete.'"
3. "Calibration anchors are Plan 02's own transcripts. Do NOT reuse 3.1d calibration transcripts."
4. "Each revision must target a specific failure mode from prior round. Undirected rewrites don't count."
**Impacts:** Plan 02 — reduces wasted-session risk. Plan 03/04 Phase 2 benefits.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (LLM Decision Protocol): Correct direction. "Face-valid" replaced with measurable spread thresholds. Second-order risk: calibration round requires all 3 anchors first, creating serial dependency with anchor design (session-blocking task).

### P3-IMP-10: Default-30 dimensions make pre-registered success criterion unfalsifiable
**Target:** CONTEXT
**What:** 4 default-30 dimensions automatically count as "LLM_adds_signal." Pre-registration success (>= 2) is guaranteed before experiment runs.
**Why:** Pre-registration unfalsifiable. Success guaranteed.
**How:**
1. Amend: "Success: LLM_adds_signal on >= 2 dimensions WITH REAL HEURISTIC HANDLERS (primary tier only)."
2. Rename secondary tier from "adds signal" to "fills gap" — informative but not counted in go/no-go.
**Impacts:** Tightens success criterion.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (LLM Decision Protocol): Clean unfalsifiability trap. Fix minimal and correct. Secondary risk: verify >= 2 primary-tier dimensions exist in total before finalizing threshold.

### P3-IMP-11: Anchor transcripts need structural realism requirements
**Target:** CONTEXT
**What:** No spec for what makes synthetic anchors realistic vs strawman. BAD anchor must differ in reasoning quality, not structural completeness.
**Why:** Real bad agents still follow tool-call patterns. Structurally sparse BAD anchor makes scoring trivial — can't distinguish "LLM detected reasoning failure" from "LLM noticed no tool calls."
**How:**
1. "Each anchor MUST include: (a) at least 3 tool calls in realistic Claude Code format, (b) reference to real contract from baseline, (c) at least one BSKG query with plausible syntax."
2. "BAD differs in REASONING QUALITY, not structural completeness."
3. Anti-circularity: "If all 3 within 20 points, record 'anchor discrimination failure.'"
**Impacts:** Plan 02 — increases anchor creation time but increases result informativeness.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (Experimental Realism): Structural realism requirements do not over-prescribe anchor design. They close the pathological easy-grading failure mode without touching creative content. Anti-circularity check is a pre-registered stopping rule. Does not conflict with Claude's Discretion.

### P3-IMP-12: Divergence hypothesis (b) is pre-falsified — replace with reasoning_depth saturation test
**Target:** CONTEXT
**What:** Hypothesis (b) "heuristic scores BAD above 20" is pre-falsified: BAD=16 (confirmed overall composite from 3.1d calibration-results.md). Additionally, `reasoning_depth` scores GOOD=70 and MEDIOCRE=70 (identical due to unique_tools proxy saturation at 3 tools). This is a confirmed, dimension-specific heuristic failure.
**Why:** Pre-falsified hypothesis wastes 1 of 3 slots. 2/3 rule with dead slot requires both remaining to confirm. Creates false-precision appearance.
**How:**
1. Replace hypothesis (b) with: "Heuristic scores GOOD and MEDIOCRE identically on `reasoning_depth` (both 70, per 3.1d calibration — unique_tools proxy saturates at 3). LLM should score them > 20 points apart because GOOD has causal chain tracing through BSKG node IDs while MEDIOCRE makes shallow queries without result interpretation."
2. Resolve transcript provenance contradiction (see P3-ADV-2-01) before relying on calibration data.
3. Pre-register replacement as part of same block, not post-hoc adjustment.
**Impacts:** Plan 02 — makes hypothesis set genuinely testable.
**Research needed:** no (answered by adversarial review — LLM Decision Protocol)
Research resolved by: adversarial review (calibration-results.md confirms overall composite, BAD=16, reasoning_depth GOOD=MEDIOCRE=70)
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (LLM Decision Protocol): Research resolved from calibration-results.md. Original replacement targeted evidence_quality without verifying heuristic handler — redirected to reasoning_depth saturation which has direct per-dimension evidence. Note: ensure hypothesis (b) replacement targets a different dimension than hypothesis (a) to maximize coverage.

### P3-IMP-13: No failure mode specified for the claude -p call itself
**Target:** CONTEXT
**What:** First real LLM call. No JSON validation, retry policy, or smoke test. `REASONING_PROMPT_TEMPLATE` closes with fragile JSON instruction pattern.
**Why:** API-level failures most likely session blocker. Three common failure modes: markdown-wrapped JSON, safety refusals, schema mismatch.
**How:**
1. Smoke test: "Invoke `claude -p --output-format json` with trivial prompt. Must complete within 5 minutes. If fails: session pivots to debugging invocation only."
2. Validation: "JSON with integer `score` in [0,100], list `evidence` >= 1 string, string `explanation`. 3 lines of Python."
3. Retry: "If fails: retry with suffix 'Your entire response must be valid JSON only. No markdown fences or preamble.' If second fails: mark 'invocation incompatible,' log raw response. Max 20 minutes in-session debugging."
**Impacts:** Plan 02 — reduces session-waste risk.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (Experimental Realism): Correct direction, too vague originally. Rewrite adds exact validation schema, verbatim retry suffix, and hard 20-minute cap. 15-minute smoke test corrected to 5 minutes.

### P3-IMP-14: Taxonomy-to-archetype pipeline conflates detection failures with evaluator attack surfaces
**Target:** CONTEXT
**What:** Phase 0 taxonomy categories (what detector gets wrong) ≠ Phase 1 adversarial archetypes (how evaluator can be gamed). Orthogonal classification axes. Current spec couples transcript count to taxonomy count, producing false alarms (taxonomy collapse constrains adversarial scope) and false reassurance (rich taxonomy expands scope without finding new code paths).
**Why:** Taxonomy useful for Plan 05/3.1f but wrong input for adversarial design. Decoupling eliminates taxonomy collapse as threat to Phase 2 validity.
**How:**
1. Phase 1: "Transcript count data-driven from evaluator code path enumeration. Min 3 exploitable paths, max 8. LLM-Flatterer mandatory."
2. Add framing: "Phase 0 = what detector gets wrong. Phase 1 = how evaluator can be gamed. Taxonomy categories annotate transcript domain scenarios, not archetype count."
3. Remove taxonomy-count-to-archetype-count mapping from Phase 1.
4. In `<decisions>`: "Taxonomy and adversarial archetypes are separate classification systems."
**Impacts:** Decouples taxonomy from adversarial generation. Taxonomy collapse no longer threatens Phase 2.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (Cross-Plan Integration): Correct direction but original How omitted removing the mapping and recording separation in decisions. Both needed to prevent coupling from silently reappearing during execution.

### P3-IMP-15: No pre-registered interpretation for simultaneous taxonomy collapse AND ambiguous Plan 02
**Target:** CONTEXT
**What:** Individual fallbacks exist for single failures. Compound failure (both taxonomy collapse AND Plan 02 ambiguous) is unaddressed but realistic given corpus structure and n=3.
**Why:** With both inputs degraded, Phase 2 result is "experiment underpowered," not "LLM works/doesn't." Must be pre-registered per pre-registration principle.
**How:**
1. Add compound degradation rule: "If Phase 0 < 3 categories AND Plan 02 divergence hypotheses 0/3 or 1/3: Phase 2 = INCONCLUSIVE. Finding: 'Evaluation validity cannot be assessed. 3.1c must address corpus diversity and rubric calibration.'"
2. "Compound degradation is a research finding constraining 3.1c scope, not a failure."
3. Distinguish: "Single-side degradation → individual fallbacks. Both sides → INCONCLUSIVE."
**Impacts:** Plan 03/04 Phase 2 interpretation. Prevents over-interpreting weak data.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** Plan 02 (rubric quality)
**Classification:** structural
**Status:** implemented
Adversarial note (Cross-Plan Integration): Original underspecified single-side vs compound boundary. Rewrite adds explicit rule: single-side degradation triggers individual fallbacks; both simultaneously = INCONCLUSIVE.

### P3-IMP-16: Plan 05 Track B is binary but Plan 02 produces a gradient
**Target:** CONTEXT
**What:** Track B: "conditional on Plan 02 go." But Plan 02 is per-dimension matrix, not binary. Track B should scale with signal count.
**Why:** Binary go/stub discards intermediate info. 3.1c needs partial observations.
**How:**
1. "Track B activates if Plan 02 produces LLM_adds_signal on >= 1 dimension. Scope scales: 1 = minimal schema; 2+ = full."
2. "If 0 dimensions: write `evaluation_observations.md` documenting what was attempted, which dimensions tested, why LLM scoring failed, what 3.1c needs to change."
**Impacts:** Plan 05 deliverables. Makes Track B a gradient.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** Plan 02 (per-dimension matrix)
**Classification:** structural
**Status:** implemented
Adversarial note (Cross-Plan Integration): Withstands scrutiny. Graduated Track B correctly calibrated against Plan 02's per-dimension output. Activation threshold >= 1 is well-calibrated (lower than Plan 02's amended >= 2 primary-tier threshold because Track B is schema extraction, not validity judgment).

### P3-IMP-17: Gameability matrix "3 of 6" hardcodes variable denominator — needs Phase 1 exit artifact
**Target:** CONTEXT
**What:** "3 of 6 mandatory archetypes" — 6 is ungrounded. Actual count depends on Phase 0/1 outcomes. N must be locked as Phase 1 exit artifact before Phase 2 begins.
**Why:** Without artifact, threshold can be computed post-hoc, violating pre-registration principle.
**How:**
1. Change to "ceil(N/2) of N mandatory archetypes."
2. "Record N in `.vrs/experiments/plan-03/archetype-count.json` before Phase 2. Pre-registered at Phase 1 close."
3. Add Phase 1 exit criterion: "Phase 1 not complete until archetype-count.json exists."
**Impacts:** Plan 03/04 Phase 2 go criterion. Pre-registration consistency.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (Cross-Plan Integration): Correct fix. Missing timing constraint: N must be locked before Phase 2 via mandatory exit artifact. Prevents retroactive threshold adjustment.

### P3-IMP-18: Plan 03/04 needs phase-gating via exit artifacts, not time budgets
**Target:** CONTEXT
**What:** The problem is not lack of time budgets but that three genuinely independent experiments are sequenced as single monolithic plan without independent checkpoints. Phase 0 (taxonomy) is valuable regardless of Phase 2. Phase 2 has external dependency on Plan 02 rubric, not Phase 1 completion. Time budgets are silently skippable; artifact gates are not.
**Why:** Clock-based discipline within coupled plan still results in Phase 2 being skipped if earlier phases overrun. Artifact gates solve the problem time budgets only approximate. Session 0's entry criteria already uses this pattern successfully.
**How:** See P3-ADV-4-01 for the artifact-gating replacement.
**Impacts:** Plan 03/04 execution structure.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
Adversarial note (Cross-Plan Integration): Time budgets are symptom treatment. The merge was correct (same corpus, technique, customer) but didn't carry over Session 0's artifact-gate pattern. Three-experiment structure becomes manageable once each phase has independent exit artifact. Reframed to P3-ADV-4-01.

### P3-IMP-19: Unobserved Phenomena list needs routing structure and consumer
**Target:** CONTEXT
**What:** Mandatory list with ambiguity threshold but no downstream consumer, no item structure, no routing. An unrouted list in a phase whose anti-pattern is shelf-ware will become shelf-ware.
**Why:** Two functions must be separated: (a) scope-bounding for 3.1c, (b) infrastructure prioritization for 3.1f. Conflating both in unstructured list makes routing impossible.
**How:**
1. Per-item structure: "(a) phenomenon, (b) why it matters, (c) measurement difficulty: trivial | moderate | requires-infrastructure, (d) target phase: 3.1c | 3.1f | Phase 5."
2. Routing rule: "3.1c items → 3.1c experiment design input. 3.1f items → loop design input. Phase 5 → appended to `<deferred>`. Routing at Plan 05 close."
3. "> 5 items tagged 3.1c: 'Scope overflow' — mark top 3 by difficulty as high-priority."
4. Add to 3.1c anchor: "Must review Plan 05 Unobserved Phenomena as required input."
**Impacts:** Plan 05 deliverable quality. Converts list from observations to routing instructions.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (Cross-Plan Integration): Misclassified as cosmetic by improvement agent — elevated to structural. An unrouted mandatory list is shelf-ware risk. Per-item `target_phase` field is the key addition.

### P3-IMP-20: Phase 1 Haiku adversarial generation may produce trivially detectable gaming
**Target:** CONTEXT
**What:** Weaker model generates attacks, stronger evaluates. Biases toward "defense works." Most dangerous transcripts need convincing fakes that Haiku may not produce.
**Why:** Adversarial evaluation tests HARD cases. Asymmetry provides lower bound, not definitive assessment.
**How:**
1. Add rationale: "Haiku provides LOWER BOUND on evaluator robustness."
2. Quality gate: "If >= 2 Haiku transcripts score heuristic >= 70 AND LLM >= 70 (undetected): STOP — hand-craft 2 harder transcripts."
3. "Hand-crafted supplements are additive — archetype-count.json updated and Phase 1 exit re-confirmed."
**Impacts:** Plan 03/04 Phase 1 methodology, Phase 2 interpretation.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Adversarial note (Cross-Plan Integration): Withstands scrutiny. Quality gate correctly bounded (requires both evaluators to fail simultaneously). Supplement transcripts must not invalidate Phase 1 exit artifact.

## Adversarial CREATE Items

### P3-ADV-1-01: Per-function FP masking is a structural defect in the measurement harness
**Target:** CONTEXT
**What:** `_unique_patterns()` deduplicates by pattern name per contract. When a pattern fires on both TP and FP functions in the same contract, the harness counts only TP. This is the exact SideEntranceLenderPool situation (access-tierb-001 on flashLoan=TP, withdraw=FP). Plan 01's "zero FPs removed" falsification criterion cannot be checked with per-pattern counting for intra-contract co-fires.
**Why:** If Plan 01 fixes the pattern to not fire on withdraw, the harness reports "0 FPs removed, 1 TP preserved" — appearing as Outcome B failure — even after a correct fix. False negative on the experiment's primary outcome.
**How:**
1. Session 0 task (a): per-function firings as structured JSON: `{contract, pattern_id, function_name, classification_reason}`.
2. Finding Counting Policy: "per-pattern-per-contract masks intra-contract co-fires; per-function required for Plan 01 delta."
3. Note: `_unique_patterns()` adequate for regression detection, insufficient for delta measurement.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Source: Adversarial review (Measurement Validity). Cross-references: P3-IMP-02, P3-IMP-05.
Adversarial note (Measurement Validity): P3-IMP-02 and P3-IMP-05 each partially identify this but neither names it as structural defect. Together they reveal the harness cannot represent Plan 01's most likely improvement form.

### P3-ADV-2-01: Calibration transcript existence contradiction blocks evidence provenance
**Target:** CONTEXT
**What:** CONTEXT line 59: "Transcripts were fabricated and deleted." But `calibration-results.md` line 119: "6 calibration transcripts stored in `.vrs/observations/calibration/`." Both cannot be true. All divergence hypothesis pre-falsification claims and pre-research evidence citing the 63.5-point spread depend on this data.
**Why:** Three effects: (1) P3-IMP-12's evidence base is uncertain. (2) P3-IMP-09's "do NOT reuse 3.1d transcripts" guidance may be wrong. (3) Plan 02's anchor design may be partially complete if transcripts exist.
**How:**
1. Session 0 zero task: "Check `.vrs/observations/calibration/` for non-`.gitkeep` content. If transcripts exist, record filenames, verify provenance. Document in `transcript-provenance.md`."
2. Amend Assumption 3 with: "VERIFY at Session 0 start — assumption may be stale."
3. If exist: update CONTEXT. If deleted: label calibration-results.md as historical data only.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Source: Adversarial review (LLM Decision Protocol). Cross-references: P3-IMP-12, P3-IMP-09.
Adversarial note (LLM Decision Protocol): Not cosmetic contradiction. Calibration-results.md is real experimental data used as pre-research evidence. If underlying transcripts deleted, evidence cannot be audited. Pre-registration principle requires stable evidentiary base.

### P3-ADV-3-01: {observed} field must ensure reasoning-quality discrimination, not structural discrimination
**Target:** CONTEXT
**What:** For hand-written anchors, the executor controls both content AND extraction. Without spec for semantic discriminability, anchors may differentiate on structural presence (tool calls) rather than reasoning quality (causal chains). This makes Plan 02 test the wrong thing.
**Why:** LLM evaluator adds signal only when `{observed}` requires semantic interpretation. If BAD anchor has "no BSKG queries" in `{observed}`, even heuristic scores correctly — no LLM signal demonstrated.
**How:**
1. Wiring step (2): "Minimum per anchor: stated hypothesis, BSKG query results (not just commands), evidence-to-conclusion reasoning chain. Discriminative signal in REASONING CHAIN, not tool-call presence."
2. Anti-validity check: "Before freezing anchors, verify: can three be rank-ordered by reading only `{observed}`? If human cannot rank, rewrite."
3. Reserve extraction algorithm for Plan 03/04 Phase 2.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Source: Adversarial review (Experimental Realism). Cross-references: P3-IMP-08, P3-IMP-11.
Adversarial note (Experimental Realism): IMP-11 (structural floors) + IMP-08 (extraction) together reveal gap: you can satisfy both and still write anchors where BAD is obviously bad for structural reasons. The gap requires semantic validity constraint.

### P3-ADV-4-01: Phase-gating via exit artifacts instead of time budgets for Plan 03/04
**Target:** CONTEXT
**What:** Replace time budgets with phase-gating on exit artifacts: Phase 0 = `descriptive_clusters.json` + `action_map.json`; Phase 1 = `archetype-count.json` + transcript files; Phase 2 = `validity-matrix.json` (or INCONCLUSIVE log). Session estimates become phase-artifact targets.
**Why:** Time budgets within coupled plan are silently skippable. Artifact gates are outcome-based and cannot be bypassed. Consistent with Session 0 entry criteria pattern already proven.
**How:**
1. Add "Phase Exit Artifacts" table to Plan 03/04.
2. Session targets: "Phase 0: target < 0.5 sessions; scope gate if > 0.75. Phase 1: < 0.5 sessions. Phase 2: 0.5-1 session; cannot be skipped if Phase 0+1 artifacts exist."
3. Scope gate: "If Phase 0 not complete within 0.75 sessions, document partial taxonomy as-is, proceed to Phase 1."
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
Source: Adversarial review (Cross-Plan Integration). Cross-references: P3-IMP-17, P3-IMP-15, P3-IMP-18.
Adversarial note (Cross-Plan Integration): Three-experiment structure manageable once each has independent exit artifact with minimum-content requirement. Clock-based discipline replaced with outcome-based gates.

## Synthesis Items

### P3-SYN-01: Session 0 scope absorption — 6+ additions exceed 1-session ceiling
**Target:** CONTEXT
**What:** Session 0 has a hard ceiling of "1 session, 3 bounded tasks" (CONTEXT line 178). But improvements from this pass collectively add to Session 0: (a) corpus search for non-keyword access control patterns (IMP-01), (b) per-function structured JSON recording with tier_a match reasons (IMP-02, IMP-05, ADV-1-01), (c) cache-independent graph building outside pytest (IMP-03), (d) transcript provenance verification (ADV-2-01), (e) LLM-consumable rubric format requirement (IMP-06). These are not individually large, but together they transform Session 0 from "3 bounded tasks" into "3 tasks + 5 instrumentation requirements" without updating the time budget or task decomposition.
**Why:** Addressing each addition individually leaves the aggregate unexamined. If Session 0 overruns, Plan 01 is delayed and the entire pipeline shifts. The 1-session ceiling was a deliberate scope decision (CONTEXT decisions section: "Additional setup requires a plan slot"). Either the ceiling holds and some additions must be absorbed into existing tasks without expanding them, or the ceiling must be explicitly revised with acknowledgment of downstream schedule impact.
**How:**
1. Classify each Session 0 addition as either "absorbed into existing task (a/b/c)" or "new sub-task requiring its own time." Per-function JSON (IMP-02, IMP-05, ADV-1-01) absorbs into task (a) as output format change. Corpus search (IMP-01) absorbs into task (c) as expanded scope. Cache-independent building (IMP-03) absorbs into task (a) as methodology change. Transcript provenance (ADV-2-01) is a new 5-minute pre-task.
2. Update Session 0 time estimates: task (a) from 30 min to 45 min (structured JSON + cache-independent), task (c) from 15 min to 25 min (corpus search addition). Total: ~95 min vs original ~65 min. Still within 1-session ceiling if session = 2 hours, but margin is thin.
3. Add Session 0 overflow rule: "If task (a) exceeds 60 min, record partial baseline and proceed. Complete in Plan 01 first action."
**Impacts:** Session 0, Plan 01 entry criteria
**Components:** P3-IMP-01, P3-IMP-02, P3-IMP-03, P3-IMP-05, P3-IMP-06, P3-ADV-1-01, P3-ADV-2-01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
Adversarial note (ADV Validation): Correctly aggregates 7 improvements into single scope constraint. How field actionable. All flags correct. Overflow contingency is sensible pre-registered fallback.

### P3-SYN-02: Small-N statistical threshold fragility recurs across Plans 02 and 03/04
**Target:** CONTEXT
**What:** IMP-07 fixes Plan 02's Spearman rho thresholds for n=3 (mathematically impossible values). But Plan 03/04 Phase 2 uses the same "validity >= 0.6" threshold (CONTEXT line 245) on what will be a small N of transcripts per dimension (3-8 archetypes). The same class of error — importing thresholds from large-N designs without small-N adjustment — appears in both plans independently. IMP-10 (default-30 unfalsifiability) and IMP-12 (pre-falsified hypothesis) are symptoms of the same root cause: pre-registration criteria were adopted as a principle without validating that specific thresholds are achievable given the sample sizes.
**Why:** Fixing Plan 02 thresholds without fixing Plan 03/04 thresholds creates an inconsistency: one plan uses n-aware decision rules while the other uses the same broken large-N thresholds. The "LLM Decision Protocol" adversarial lens identified this pattern but no single item or ADV addresses the Plan 03/04 propagation. A unified fix ensures all statistical decision criteria are sample-size-aware.
**How:**
1. In Plan 03/04 Phase 2, replace "validity >= 0.6 on >= 2 dimensions" with N-aware rule: "For N < 10 transcripts per dimension, use rank-ordering with inversion count (same framework as Plan 02 IMP-07). For N >= 10, Spearman rho with standard thresholds."
2. Add to decisions: "All correlation-based decision thresholds must specify the expected N and use N-appropriate statistical criteria. Thresholds from literature (typically N > 30) are not valid at N < 10."
3. Audit CONTEXT lines 373 and 390 for other correlation threshold claims referencing "validity < 0.6" — annotate each with N-dependency note specifying expected sample size.
**Impacts:** Plan 03/04 Phase 2 decision protocol, deferred items referencing validity thresholds
**Components:** P3-IMP-07, P3-IMP-10, P3-IMP-12, P3-IMP-15
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
Adversarial note (ADV Validation): Core insight sound. How Steps 2-3 enhanced: Step 2 targets exact CONTEXT sections; Step 3 enumerates validity-threshold audit scope (lines 373, 390) rather than leaving unbound.

### P3-CSC-01: Plan 03/04 taxonomy collapse fallback still references coupled archetype count
**Target:** CONTEXT
**What:** If P3-IMP-14 (enhanced) is implemented — decoupling taxonomy categories from adversarial archetype count — the existing taxonomy collapse fallback (CONTEXT line 256: "If < 3 categories, Phase 1 reverts to 5 pre-specified archetypes") becomes inconsistent. After decoupling, taxonomy collapse should not trigger Phase 1 revert because Phase 1 archetype count is driven by evaluator code-path enumeration, not taxonomy. The fallback conflates a Phase 0 outcome with a Phase 1 input that IMP-14 explicitly separated.
**Why:** Implementing IMP-14 without updating the fallback creates a contradictory spec: the main text says "archetypes are independent of taxonomy" but the fallback says "taxonomy collapse changes archetype count." Executor will face conflicting instructions.
**How:**
1. Update taxonomy collapse fallback: "If < 3 categories: record 'degenerate corpus' as Phase 0 finding. Phase 1 proceeds with evaluator code-path-enumerated archetypes (unaffected by taxonomy count). Phase 0 finding routes to Plan 05 Unobserved Phenomena as 'corpus diversity: requires-infrastructure, target: 3.1f.'"
2. Remove "Phase 1 reverts to 5 pre-specified archetypes" — this is the old coupled logic.
**Impacts:** Plan 03/04 Phase 0 fallback, Phase 1 entry
**Trigger:** P3-IMP-14
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)
Adversarial note (ADV Validation): Correctly identifies cascade from IMP-14 decoupling. How specifies line 256 replacement. Trigger field properly expresses sequencing constraint without over-marking as prerequisite.

## Post-Review Synthesis
**Items created:** P3-SYN-01, P3-SYN-02, P3-CSC-01
**Key insight:** Session 0 has become a silent bottleneck — seven improvements add instrumentation requirements without revising the 1-session ceiling. Separately, small-N statistical threshold fragility is systemic across Plans 02 and 03/04, not a single-plan issue, and fixing one without the other creates an internal inconsistency in the pre-registration framework.
