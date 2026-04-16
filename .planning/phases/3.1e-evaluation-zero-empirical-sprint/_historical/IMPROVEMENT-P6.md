# Improvement Pass 6

<!--
  Improvement File Template
  =========================
  Full documentation: @references/improvement-file-guide.md
  Classification formulas: @references/pipeline-classification.md

  When adding new statuses, update references/pipeline-classification.md (single source).
-->

**Pass:** 6
**Date:** 2026-02-24
**Prior passes read:** 1-5 (via IMPROVEMENT-DIGEST.md)
**Status:** complete

<!-- File-level status: in-progress | complete -->

**Areas analyzed:** Measurement Foundation (Plan 01 + Session 0), LLM Evaluation Capability (Plan 02), Evaluator Assessment & Schema Extraction (Plans 03/04 + Plan 05)
**Agent count:** 3 improvement + 3 adversarial + 1 synthesis (pending)

## Pipeline Status

<!-- Auto-populated by workflows. Shows pending actions across ALL passes for this phase. -->

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 0 | 0 | — |
| Research | 0 | 0 | — |
| Gaps | 0 | 2 (done/) | — |
| Merge-ready | 21 | 0 | — |

**Pipeline:** [discuss] ✓ → [improve] ✓ → [pre-impl] — → [research] — → [implement] ~ → [plan] — → [execute] —
**Next recommended:** /msd:implement-improvements 3.1e

## Adversarial Lenses

| Lens | Brief | Items | Attack Vector |
|------|-------|-------|---------------|
| Executable Specification Fidelity | Session 0 instructions reference Python APIs and data structures refined through 5 passes. Remaining specification errors compound at execution time when the 25-30 min time-box leaves no debugging room. | P6-IMP-01, P6-IMP-02, P6-IMP-03, P6-IMP-05 | Can an executor follow Session 0 instructions without consulting source code? |
| LLM Evaluation Protocol Robustness | Plan 02's three-hypothesis design with n=2 pairwise comparison creates multiple points where statistical artifacts could masquerade as LLM capability evidence. | P6-IMP-06, P6-IMP-07, P6-IMP-08, P6-IMP-09, P6-IMP-10, P6-IMP-11, P6-IMP-12, P6-IMP-13, P6-IMP-14 | Does the scoring protocol distinguish genuine LLM discrimination from statistical artifacts at n=2? |
| Evaluator Assessment & Downstream Integration | Plans 03/04 and 05 depend on upstream artifacts whose schemas and join keys have been iteratively refined. Remaining format incompatibility becomes a silent integration failure. | P6-IMP-15, P6-IMP-16, P6-IMP-17, P6-IMP-18, P6-IMP-19, P6-IMP-20, P6-IMP-21 | Will Plan 05 integration succeed given accumulated schema changes from 5 prior passes? |

**Note:** P6-IMP-04 was not assigned to any adversarial lens — remains unreviewed (status: open).

## Improvements

### P6-IMP-01: `graph_fingerprint()` returns a string; CONTEXT.md schema requires `node_count` and `edge_count` — naming hazard between OO and legacy interfaces
**Target:** CONTEXT
**What:** Session 0 task (a1) instructs: "call `graph_fingerprint(graph)` and persist with schema `{contract, fingerprint, node_count, edge_count}`." But `graph_fingerprint(graph: KGType) -> str` returns a 64-char hex string, not a dict. `node_count` and `edge_count` must be retrieved separately via `len(graph.nodes)` and `len(graph.edges)`. Additionally, `fingerprint.py` exports both `graph_fingerprint` (OO, str return) and `fingerprint_graph` (legacy, dict-based) — the naming similarity is a debugging hazard.
**Why:** 5 min of debugging inside a 25-30 min time-boxed session can cascade into overflow. Naming hazard between `graph_fingerprint` and `fingerprint_graph` not flagged in prior passes.
**How:**
1. Replace instruction with: "call `graph_fingerprint(graph)` — returns hex string. Build schema entry manually: `{contract, fingerprint: graph_fingerprint(graph), node_count: len(graph.nodes), edge_count: len(graph.edges)}`."
2. Add explicit warning: "`fingerprint_graph` (legacy, dict-based) exists alongside `graph_fingerprint` (OO, str return) — use the OO variant."
3. Do NOT reference `verify_determinism()` — it takes the legacy dict interface and is irrelevant to Session 0.
**Impacts:** Session 0 task (a1) time budget; Assumption 7 accuracy
**Research needed:** no — confirmed by reading `kg/fingerprint.py:157-212`
**Confidence:** HIGH
**Prior art:** 5 — direct source inspection; factual correction
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** ENHANCE (Lens: Executable Specification Fidelity) — naming hazard not flagged in original

### P6-IMP-02: `build_lens_report()` strips `node_id`; schema uses `function_name` but output has `node_label`
**Target:** CONTEXT
**What:** Session 0 task (a1) schema specifies `function_name` but `PatternEngine.run()` outputs `node_label`. The fields are equivalent but the name mismatch wastes 3-5 min.
**Why:** Schema field name should match actual output keys to avoid confusion.
**How:**
1. In Session 0 task (a1) schema, change `function_name` to `node_label`.
2. Update Artifact Manifest for `baseline-before.json` and `baseline-after.json` to use `node_label`.
**Impacts:** Session 0 task (a1); Plan 01 Artifact Manifest
**Research needed:** no — confirmed by reading `queries/report.py:29-52` and `queries/patterns.py:706-718`
**Confidence:** HIGH
**Prior art:** 5 — direct source inspection
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** rejected
**Verdict:** REJECT (Lens: Executable Specification Fidelity) — `function_name` → `node_label` is normal field mapping between schema and implementation; renaming is a 1-line fix during execution, not a debugging hazard worth an improvement item

### P6-IMP-03: Session 0 branch table has no handler for branch (c) — the structurally expected outcome
**Target:** CONTEXT
**What:** `is_access_gate()` in `helpers.py:104-115` uses keyword matching on modifier names. This correctly detects `onlyOwner` but misses `require(msg.sender == owner)` inline guards. On DamnVulnerableDefi, the diagnostic will likely return MIXED results — branch (c).
**Why:** Branch (c) is the structurally expected outcome. The executor would improvise mid-session without a pre-registered response.
**How:**
1. Add concrete Branch (c) handler.
2. In Assumption 7, note the keyword-match limitations.
**Impacts:** Session 0 task (b); Plan 01 branch table
**Research needed:** no — confirmed by reading `helpers.py:104-115`
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Verdict:** REFRAME (Lens: Executable Specification Fidelity) — Branch table content exists but is formatted as prose IF/IF/IF blocks. The issue is formatting, not missing content. Replaced by P6-ADV-1-01.

### P6-IMP-04: Three-level cost measurement adds unbudgeted overhead for data only 3.1f needs
**Target:** CONTEXT
**What:** Plan 01 requires `cost-summary.json` with three levels (full pipeline, targeted 2-3 contract, lens-only). This requires either running the pipeline three times or writing ~50 LOC of timing instrumentation — neither budgeted. The core deliverable (`cost_per_FP_removed`) needs only one measurement: wall_clock for baseline-before vs baseline-after.
**Why:** Three-level breakdown is forward-looking infrastructure for 3.1f, not needed for 3.1e's effort/FP ratio claim.
**How:**
1. Reduce to single-level: "Record `wall_clock_seconds` and `compute_seconds` for full 7-contract before and after runs."
2. Replace three-level schema with two records: `{run: "before"|"after", wall_clock_seconds, compute_seconds, contracts_processed: 7}`.
3. Defer three-level cost breakdown to 3.1f.
**Impacts:** Plan 01 cost instrumentation; Artifact Manifest cost-summary.json
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — before/after timing is standard
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Verdict:** REFRAME (Lens: Interrupted Review Recovery) — diagnosis rests on misread of artifact manifest; `level` field is a label, not a three-level breakdown; proposed fix drops `LOC_per_FP_removed` which feeds 3.1f. Real problem is ambiguous `level` enum. Replaced by P6-ADV-R-01.

### P6-IMP-05: `is_tp` join instruction cites `(contract_label, node_label)` but CORPUS has no such structure — silent data integrity failure
**Target:** CONTEXT
**What:** Session 0 task (a1) says: "join against CORPUS dict using `(contract_label, node_label)` as key." But CORPUS is a `list[GroundTruth]` indexed by iteration, not a dict. TP classification uses `pattern_id in gt.expected_patterns`. The cited join key doesn't exist — executor would silently produce wrong TP/FP counts without any error.
**Why:** Silent data integrity failure is worse than a crash. Wrong baseline numbers propagate to all downstream plans without detection. A 2-minute pre-flight type inspection of CORPUS prevents 10 min of reconstruction.
**How:**
1. Replace join instruction with: "Build `corpus_by_contract = {gt.target_contract_label: set(gt.expected_patterns) for gt in CORPUS}`. For each finding, `is_tp = finding['pattern_id'] in corpus_by_contract.get(contract_label, set())`."
2. Add 2-min pre-flight: "Before scoring, `print(type(CORPUS), type(CORPUS[0]))` — must be `list, GroundTruth`. If dict: you're using a cached transform."
3. Note: `node_label` is for human readability, not part of TP join key.
**Impacts:** Session 0 task (a1) time budget; Plan 01 baseline join correctness
**Research needed:** no — confirmed by reading `test_detection_baseline.py:55-219`
**Confidence:** HIGH
**Prior art:** 5 — direct source inspection
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** ENHANCE (Lens: Executable Specification Fidelity) — reframed as silent data integrity failure, added 2-min pre-flight type inspection

### P6-IMP-06: Dual heuristic parity on both dimensions simultaneously may be unachievable — needs temporal constraint
**Target:** CONTEXT
**What:** MEDIOCRE anchor must satisfy `unique_tool_count = GOOD` (H1 parity) AND `bskg_query_count = GOOD` (H2 parity) simultaneously. A transcript with 3 real BSKG queries and shallow reasoning is either not plausibly mediocre, or requires semantically empty queries — making H2 confirmation trivial.
**Why:** The dual-parity constraint creates a design conflict. Additionally, discriminability must be checked BEFORE rubric freeze — if MEDIOCRE BSKG queries have no genuine semantic content, H2 confirmation is trivially achieved.
**How:**
1. Split dual-parity into priority: `unique_tool_count` parity REQUIRED for H1; `bskg_query_count` parity PREFERRED with ±1 relaxation if discriminability fails.
2. Add temporal constraint: discriminability check BEFORE rubric freeze. Record in element-preregistration.json with `h2_parity_relaxed: true|false` field.
3. Add pre-condition: verify MEDIOCRE BSKG queries have genuine semantic content (not template/empty queries).
**Impacts:** Plan 02 confidence stays MEDIUM. H2 confirmation evidence quality improves.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — concurrent validity in psychometrics; multi-attribute parity at small N is novel
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** ENHANCE (Lens: LLM Evaluation Protocol Robustness) — added temporal gate before rubric freeze

### P6-IMP-07: n=2 non-determinism protocol is under-powered for MEDIOCRE-BAD pair — needs default choice
**Target:** CONTEXT
**What:** At n=2 for an "expected moderate" pair, a flip cannot distinguish LLM variance from anchor proximity. The plan's MEDIOCRE-BAD trigger is still n=2.
**Why:** If MEDIOCRE-BAD flips at n=2 and triggers a marginal downgrade, the go/no-go scoring may unfairly penalize cases where MEDIOCRE was correctly designed as close to BAD. A pre-registered DEFAULT is needed, not just the option to choose.
**How:**
1. Add pre-registered DEFAULT interpretation for MEDIOCRE-BAD flips: executor must record their choice in `flip_resolution` field BEFORE scoring. Required, not optional.
2. Default: classify as anchor-proximity artifact (conservative choice) unless executor provides written justification for upgrade to n=3.
3. Add `flip_resolution: {default: "proximity_artifact" | override: "upgrade_n3", justification: str}` to element-preregistration.json.
**Impacts:** Reduces risk of a single flip corrupting go/no-go verdict.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — LLM pairwise stability at small n (MT-Bench)
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** ENHANCE (Lens: LLM Evaluation Protocol Robustness) — requires default choice, not just pre-registration

### P6-IMP-08: `{observed}` has no schema enforcement — format variation is an invisible confound
**Target:** CONTEXT
**What:** `REASONING_PROMPT_TEMPLATE` injects `{observed}` as a free-form string. Calibration anchors use researcher-crafted formatting; real/adversarial transcripts will differ. Rubric calibrated on one format and scoring on another creates a confound.
**Why:** Plan 03/04 Phase 2 scores adversarial transcripts through the frozen rubric. If formatting differs from calibration anchors, rubric may perform inconsistently due to format, not evaluator quality.
**How:**
1. Define minimum `{observed}` schema: 3-5 labeled sections (e.g., `[HYPOTHESIS]`, `[GRAPH_QUERIES]`, `[EVIDENCE_CHAIN]`, `[CONCLUSION]`). Record in element-preregistration.json.
2. Extend feasibility check (step 2.5) to test both researcher-formatted and raw Claude Code tool_call format.
**Impacts:** Plan 02 adds ~15 min to step 2. Plan 03/04 Phase 1 Haiku transcripts must follow `{observed}` schema.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — structured prompt inputs for LLM evaluation are standard
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** CONFIRM (Lens: LLM Evaluation Protocol Robustness)

### P6-IMP-09: Held-out anchor independence is weaker than claimed — use MEDIOCRE-tier on different contract
**Target:** CONTEXT
**What:** Zero-graph held-out is structurally identical to BAD calibration anchor. A rubric that scores BAD low trivially scores held-out low — this is redundancy, not generalization evidence.
**Why:** The rubric freeze protocol uses held-out as generalization check. If held-out = BAD variant, passing provides zero additional confidence.
**How:**
1. Change held-out design from "zero-graph" to "MEDIOCRE-tier transcript on a DIFFERENT CONTRACT than calibration anchors." This tests both score-level generalization and contract generalization.
2. Do NOT use the Axis A/B framework for held-out — that framework is for calibration anchors. Held-out tests rubric portability.
3. Add check: "held-out must NOT be scoreable by BAD-tier heuristics alone."
**Impacts:** Held-out design adds ~10-15 min. Generalization claim validity improves.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — held-out test set design is standard; rubric portability testing is novel
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** ENHANCE (Lens: LLM Evaluation Protocol Robustness) — same-contract held-out better than Axis A/B; MEDIOCRE on different contract provides actual generalization evidence

### P6-IMP-10: Go/no-go AMBIGUOUS outcome (1.0-1.5) has no registered forward action
**Target:** CONTEXT
**What:** The plan acknowledges "Ambiguous: 1.0-1.5" but provides no action. This is the most likely result for a first-ever LLM evaluation call.
**Why:** Without a forward path, the AMBIGUOUS outcome creates a decision vacuum at the 3.1c handoff.
**How:**
1. Add explicit AMBIGUOUS action: "Proceed to 3.1c with constraint 'LLM evaluation gated behind real-transcript pilot before full integration.'"
2. Add `llm-recommendation.md` as a required Plan 02 output artifact (verdict, hypothesis scores, forward actions).
**Impacts:** Plan 05 Track B activation gate becomes clearer. 3.1c entry conditions sharpened.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — decision tree design with ambiguous-outcome branches
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** CONFIRM (Lens: LLM Evaluation Protocol Robustness)

### P6-IMP-11: Step 2.5 feasibility check tests format legibility, not content validity — prose paraphrase retains contamination
**Target:** CONTEXT
**What:** The check asks "can a human understand a detection firing record?" but structured JSON from the detection pipeline is scoreable by keyword counting. If `{observed}` contains raw `fired_conditions` JSON, the LLM can confirm H3 by pattern-matching, not reasoning. Additionally, prose paraphrase of detection JSON retains the same contamination — the LLM identifies patterns by matching rephrased detection output.
**Why:** This would make Instrument 3 (divergence evidence) trivially confirmable. Contamination is not just JSON format — it's semantic content.
**How:**
1. Extend step 2.5 to test whether `{observed}` content can be scored by counting or paraphrase matching alone.
2. Anti-contamination rule: `{observed}` must NOT contain raw `fired_conditions` JSON OR prose paraphrase of detection results as primary content. Detection results may be referenced only as supporting context.
3. Add `contamination_check_passed: true|false` field to element-preregistration.json.
**Impacts:** Anchor design becomes harder but more valid. Plan 05 smoke test may conclude raw detection JSON is NOT directly injectable.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — contamination in evaluation design (NLP)
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** ENHANCE (Lens: LLM Evaluation Protocol Robustness) — prose paraphrase retains contamination; added contamination_check_passed field

### P6-IMP-12: `claude -p` retry protocol covers invocation failures but not schema violations
**Target:** CONTEXT
**What:** The retry handles non-JSON output but not valid JSON with wrong schema (score out of range, empty evidence, null fields). With 12 scoring calls, manual schema checking is error-prone.
**Why:** Schema violations discovered mid-scoring consume the 20-minute debugging budget.
**How:**
1. Add pre-scoring validation: 10-line `validate_llm_response()` function as smoke-test prerequisite.
2. Add Type D failure category for schema mismatch with retry instruction.
**Impacts:** Calibration chain log gains `validation_passed` field.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — JSON schema validation is standard
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** CONFIRM (Lens: LLM Evaluation Protocol Robustness)

### P6-IMP-13: H3 tests a different construct than H1/H2 — weight should be 0.5, coordinate with AMBIGUOUS resolution
**Target:** CONTEXT
**What:** H1 and H2 test discrimination where heuristic has parity (the core claim). H3 tests whether LLM correctly identifies BAD as bad — a difference the heuristic ALREADY detects. H1+H3=2.0=go without ever demonstrating LLM adds signal where heuristic fails. H2 is the critical hypothesis — it's the only one that tests whether LLM adds value BEYOND heuristic.
**Why:** Equal weighting produces a false-positive go signal if H1+H3 confirmed without H2. Must coordinate with IMP-10's AMBIGUOUS resolution.
**How:**
1. Reclassify H3 weight to 0.5 (coherence check): necessary but not sufficient.
2. Change go interpretation: "H1 + H2 CONFIRMED = go (2.0). H1 + H3 WITHOUT H2 = ambiguous (1.5). H3-only = no-go."
3. Coordinate with IMP-10: AMBIGUOUS (1.0-1.5) forward action applies when H1+H3 without H2.
**Impacts:** Go threshold effectively becomes "H2 required for unambiguous go" — stricter but more valid.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — construct validity distinctions in evaluation design
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** ENHANCE (Lens: LLM Evaluation Protocol Robustness) — H3 weight = 0.5; coordinate with IMP-10's AMBIGUOUS resolution

### P6-IMP-14: No protocol for real transcript search — scope classification may be incorrect
**Target:** CONTEXT
**What:** The plan says "search `.vrs/` or `tests/` for real transcripts" but gives no search depth, format qualification, or time budget.
**Why:** Two-tier go/no-go depends on whether "synthetic-only" or "includes real transcript" scope applies.
**How:**
1. Add 5-minute pre-flight search protocol.
2. Record search results in element-preregistration.json.
**Impacts:** element-preregistration.json gains search-results field.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Verdict:** REFRAME (Lens: LLM Evaluation Protocol Robustness) — scope was too broad; narrowed to specific search protocol with qualification definition. Replaced by P6-ADV-2-01.

### P6-IMP-15: Phase 0 taxonomy will collapse to single cluster — needs scope-reduction gate
**Target:** CONTEXT
**What:** 38% of FPs from one pattern means dominance_ratio almost certainly exceeds the plan's own 0.75 corpus-limited threshold. The "two-pass undirected discovery" will rediscover what pattern IDs already tell us.
**Why:** If corpus-limited is the expected outcome, Phase 0 is confirming known information. If archetype_count <= 2, the elaborate Phase 2 adversarial evaluation is oversized for the data.
**How:**
1. Add pre-registration: "Most likely outcome: corpus-limited (dominance_ratio > 0.75). If this occurs, Phase 0 completes in < 15 min."
2. Add scope-reduction gate: "If Phase 0 produces archetype_count <= 2, reduce Phase 2 scope: 2 adversarial transcripts instead of 3-4, 1 Haiku plausibility check instead of 2."
3. Update expected outcome from "2-4 categories" to "1-2 categories (corpus-limited likely)."
**Impacts:** Phase 0 session estimate drops from 0.5 to 0.1-0.15 sessions. Phase 2 becomes proportional to data.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — corpus homogeneity as taxonomy threat
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** ENHANCE (Lens: Evaluator Assessment & Downstream Integration) — added scope-reduction gate for Phase 2 proportionality

### P6-IMP-16: Phase 1 quality gate has unresolvable temporal paradox — exit artifact depends on Plan 02 completion
**Target:** CONTEXT
**What:** Phase 1 transcript generation runs parallel with Plan 02, but archetype-count.json cannot be finalized until Plan 02 freeze + quality gate evaluation + optional re-crafting. No iteration limit on re-crafting.
**Why:** The 30-minute buffer may become 1+ hour, compressing Phase 2.
**How:**
1. Add quality gate retry limit: maximum 1 hand-crafting cycle. If second round also fails, record finding and proceed.
2. Clarify naming: "archetype-draft.json" during parallel execution, promoted to "archetype-count.json" after quality gate.
3. Update Budget Recount: Phase 1 quality gate retry adds 0.5-1 session if fired.
**Impacts:** Plan 03/04 session estimate should be 1.5-2.5 sessions.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — quality gate retry loops with cycle limits
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** CONFIRM (Lens: Evaluator Assessment & Downstream Integration)

### P6-IMP-17: Validity coefficient on adversarial transcripts measures adversarial divergence, not normal-operation validity — don't use anchors as non-adversarial sample
**Target:** CONTEXT
**What:** Phase 2 measures heuristic vs LLM rank correlation on transcripts designed to exploit heuristic weaknesses. A low validity coefficient is the expected outcome by construction. 3.1c reading "Spearman rho = -0.3" may incorrectly discard the heuristic for normal operation. The Plan 02 anchors should NOT be used as a non-adversarial validity sample — they are researcher-crafted, not representative.
**Why:** Conflates "Is the heuristic valid in normal operation?" with "Can the heuristic be gamed?" Using calibration anchors as the non-adversarial sample introduces circularity (rubric was tuned on those anchors).
**How:**
1. Add `validity_sample_type: adversarial_only` field to validity-matrix.json. Note in construct_alignment_note: "normal-operation validity is unassessed, deferred to 3.1c."
2. Do NOT use Plan 02 anchors as non-adversarial sample. Record as three-state validity decision: `{adversarial_validity: measured, normal_validity: deferred, anchor_validity: circular_excluded}`.
3. Update "Heuristic Validity, Not Goodhart" decision: validity on adversarial vs representative corpus are separate measurements.
**Impacts:** Plan 05 Track B validity_coefficient field requires `validity_sample_type` annotation.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — construct validity distinctions; anchors-as-sample circularity is novel
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** ENHANCE (Lens: Evaluator Assessment & Downstream Integration) — anchors aren't population samples; three-state validity decision

### P6-IMP-18: Plan 05 contradiction pair (2) requires a join key that neither artifact specifies
**Target:** CONTEXT
**What:** Contradiction pair (2) — "YAML-fix-sufficient vs builder-fix-required for same FP cluster" — requires joining `baseline-before/after.json` (keyed by pattern_id + node_label) against `action_map.json` (keyed by cluster_id). The join key (pattern_ids per cluster) is not in action_map.json's minimum content schema.
**Why:** Without the join key, the contradiction is structurally irresolvable.
**How:**
1. Replace uniform "10-15 min" with per-pair allocations: Pair (1) 5 min, Pair (2) 15-20 min, Pair (3) 5 min.
2. Add to Plan 03/04 Phase 0 action_map.json minimum content: `pattern_ids: list` per cluster.
3. Add join specification to Upstream Integration Contract.
**Impacts:** Plan 03/04 Phase 0 action_map.json schema extended. Plan 05 session estimate increases to 0.5-0.75 sessions.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — join key specification is standard data engineering
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** CONFIRM (Lens: Evaluator Assessment & Downstream Integration)

### P6-IMP-19: Plan 05 compound failure (Track A + Track B both unavailable) is undefined — needs 3.1c conditional entry protocol
**Target:** CONTEXT
**What:** Individual track fallbacks exist but simultaneous failure leaves Plan 05 with no valid output specification. Additionally, 3.1c entry conditions are undefined — there are 3 possible entry scenarios that need explicit protocols.
**Why:** Compound failure is plausible — both Plans have documented failure modes. Without a specified response AND clear 3.1c entry conditions, the sprint-to-schema handoff fails.
**How:**
1. Add compound failure output: `sprint-block.md` documenting which plans failed, what data exists, what 3.1c must address.
2. Add 3.1c conditional entry protocol with 3 named scenarios:
   - **Full success:** All plans complete → 3.1c receives full data package, `phase_entry_mode: data_rich`
   - **Partial success:** Some plans complete → 3.1c receives partial data + sprint-block.md, `phase_entry_mode: partial_data`
   - **Compound failure:** Track A + B both fail → 3.1c receives sprint-block.md only, `phase_entry_mode: blocked_recovery`
3. Add `phase_entry_mode` field to Plan 05 output specification.
**Impacts:** Plan 05 pre-registration updated. 3.1c entry conditions specified.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — graceful degradation specifications
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** ENHANCE (Lens: Evaluator Assessment & Downstream Integration) — added 3.1c conditional entry protocol with 3 named scenarios

### P6-IMP-20: GVS `graph_first` tests "Bash before Read," not "BSKG before Read" — independent attack surface
**Target:** CONTEXT
**What:** `graph_value_scorer.py:170-193` returns `graph_first=True` if ANY Bash call (including `ls` or `pwd`) appears before the first Read call. This is independent from the obs_bskg_query.py exploit.
**Why:** An adversarial transcript could score high GVS with one early `ls` call and no BSKG. This is an independent exploit from false bskg_query event injection.
**How:**
1. Separate cluster (3) into: (3a) early non-BSKG Bash call, no actual queries; (3b) obs_bskg_query.py false event injection.
2. Add `exploit_layers: list[str]` per archetype in archetype-count.json.
3. Update Evaluation Layer Content Validation Policy to note both mechanisms.
**Impacts:** Phase 1 transcript count may increase by 1. archetype-count.json schema extended.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — code reading confirmed at `graph_value_scorer.py:170-193`
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** CONFIRM (Lens: Evaluator Assessment & Downstream Integration)

### P6-IMP-21: Plan 05 integration smoke test produces "gap found, defer" without specifying what 3.1c needs — requires transformation sketch
**Target:** CONTEXT
**What:** If the smoke test finds a detection-to-evaluation format incompatibility, it routes to Unobserved Phenomena as "integration gap: architectural." But it doesn't describe what transformation the LLM evaluator would need. 3.1c inherits a gap label without the specification to design a solution.
**Why:** "Gap found, defer" is insufficient when the smoke test has the data to characterize the gap. A minimum transformation sketch (at least 2 concrete steps) is needed.
**How:**
1. Require Unobserved Phenomena entry to include: concrete field-mapping question, which fields have no rubric mapping, AND a minimum 2-step transformation sketch.
2. Add `detection_evaluation_bridge` row to field-provenance.md in the gap case with `bridge_complexity: {steps: int, estimated_loc: int}` field.
3. Even in "transformation needed" case, record specific fields from baseline-before.json that have no rubric mapping plus the first 2 transformation steps.
**Impacts:** Plan 05 field-provenance.md minimum content extended. Plan 05 session estimate +0.1 sessions.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3 — data pipeline interface specification; detection-to-evaluation bridge is novel
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Verdict:** ENHANCE (Lens: Evaluator Assessment & Downstream Integration) — requires transformation sketch (min 2 steps), bridge_complexity field

### P6-ADV-1-01: Diagnostic Branch Table formatting — replace prose IF blocks with structured table
**Target:** CONTEXT
**What:** Session 0 branch table exists in CONTEXT.md but is formatted as prose IF/IF/IF blocks that are easy to miss during execution. The content is correct but the format is not executor-friendly.
**Why:** A structured 3-row table with clear columns is scannable in 5 seconds; prose IF blocks require re-reading to find the relevant branch.
**How:**
1. Add "Diagnostic Branch Table" heading to Session 0 section.
2. Replace prose IF blocks with 3-row table: columns `{Diagnostic outcome | has_access_gate result | Plan 01 action}`.
3. Content unchanged — this is a formatting fix, not a content addition.
**Impacts:** Session 0 executor experience. No content change.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — table formatting for decision trees
**Prerequisite:** no
**Depends on plans:** none
**Classification:** cosmetic
**Status:** implemented
**Origin:** REFRAME of P6-IMP-03 (Lens: Executable Specification Fidelity)
**Verdict:** CONFIRM (Lens: ADV Validation) — concrete How, all required fields, no conflicts

### P6-ADV-2-01: 5-minute pre-flight real-transcript search with qualification definition
**Target:** CONTEXT
**What:** Plan 02's two-tier go/no-go depends on whether real transcripts exist. The search needs specific paths, file patterns, and a qualification definition for "real transcript."
**Why:** Misclassification of scope (synthetic-only vs includes real) corrupts the 3.1c investment decision. A 5-minute bounded search with clear qualification prevents this.
**How:**
1. Add pre-flight search protocol: search paths `.vrs/experiments/`, `.vrs/sessions/`, `tests/workflow_harness/outputs/`. File pattern: `*.json` or `*.jsonl` containing tool_call events.
2. Qualification definition: "real transcript" = contains >= 3 tool_call events AND passes synthetic detector:
   - Real: events have non-deterministic fields (claude_id, session_id) or timestamp spread > 2 min
   - Synthetic: event sequence is identical across files OR uses hardcoded session_id="test-*" prefix
   - Record detector output in search-results field with boolean `is_real` per file found
3. Record search results (found/not-found, paths, qualification verdict) in element-preregistration.json field `transcript_search: {paths_searched: list, files_found: int, is_real_detected: bool}` before Plan 02 execution begins.
**Impacts:** element-preregistration.json gains `transcript_search` field. Scope classification becomes auditable.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — artifact inventory
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Origin:** REFRAME of P6-IMP-14 (Lens: LLM Evaluation Protocol Robustness)
**Verdict:** ENHANCE (Lens: ADV Validation) — synthetic-vs-real detection heuristic under-specified; added detector criteria

### P6-SYN-01: element-preregistration.json accumulates fields from 5 independent items without a unified schema
**Target:** CONTEXT
**What:** Five items across Lens 2 and Lens 3 each add fields to `element-preregistration.json` independently: P6-IMP-06 adds `h2_parity_relaxed`, P6-IMP-07 adds `flip_resolution`, P6-IMP-11 adds `contamination_check_passed`, P6-ADV-2-01 adds `transcript_search`, and P6-IMP-08 adds `{observed}` schema reference. Each item specifies its field in isolation. There is no consolidated schema showing what element-preregistration.json actually contains after all improvements are merged, nor any ordering constraint on when fields must be populated during Plan 02 execution.
**Why:** Implementing these individually risks: (a) field name collisions or nesting inconsistencies discovered at execution time, (b) no single reference for the executor to verify completeness before scoring begins, (c) temporal ordering ambiguity -- some fields must be set before calibration (P6-IMP-06 discriminability check), others before scoring (P6-IMP-07 flip resolution), others before execution starts (P6-ADV-2-01 transcript search). Addressing as a unified schema is more efficient than patching 5 independent field additions.
**How:**
1. In CONTEXT.md Plan 02 Produced artifact manifest entry for `element-preregistration.json`, expand minimum content to enumerate ALL fields: `h2_parity_relaxed` (bool), `flip_resolution` (object: `{default: "proximity_artifact"|"upgrade_n3", override_justification: str}`), `contamination_check_passed` (bool), `transcript_search` (object: `{paths_searched: list, files_found: int, is_real_detected: bool}`), `observed_schema` (list of section labels).
2. Add temporal ordering with explicit Plan 02 execution checkpoints:
   - **GATE A (step 1):** `transcript_search`, `observed_schema` — must be populated before feasibility test
   - **GATE B (step 2.5):** `h2_parity_relaxed`, `contamination_check_passed` — must be populated after discriminability check, before calibration
   - **GATE C (step 3):** `flip_resolution` — must be populated after any MEDIOCRE-BAD flip detected, before scoring
3. Add completeness check as explicit task (2 min): "Before scoring begins (gate C), verify all element-preregistration.json fields are populated. Per-field missing → blocker with clear diagnostic."
**Impacts:** Plan 02 artifact manifest, Plan 02 execution protocol
**Components:** P6-IMP-06, P6-IMP-07, P6-IMP-08, P6-IMP-11, P6-ADV-2-01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
**Verdict:** ENHANCE (Lens: ADV Validation) — temporal gates mapped to Plan 02 execution checkpoints

### P6-SYN-02: Unified go/no-go decision table required -- P6-IMP-13 reweighting and P6-IMP-10 AMBIGUOUS action are interdependent but specified separately
**Target:** CONTEXT
**What:** P6-IMP-13 changes H3 weight to 0.5 and redefines which hypothesis combinations map to go/ambiguous/no-go. P6-IMP-10 adds a forward action for the AMBIGUOUS band (1.0-1.5). Both items modify the same decision logic but are specified in different improvement items with only a textual "coordinate with IMP-10" note. When implemented separately, the go/no-go section of CONTEXT.md will require two non-overlapping edits to the same decision table that must be mutually consistent.
**Why:** Implementing P6-IMP-13 without simultaneously implementing P6-IMP-10 creates an inconsistent decision table: the AMBIGUOUS band would be redefined (H1+H3 without H2) but still have no forward action. Implementing P6-IMP-10 first creates an AMBIGUOUS action that references the old weighting. The merger must specify a single consolidated decision table to avoid contradictory edits.
**How:**
1. When implementing P6-IMP-10 and P6-IMP-13, produce a single consolidated "Go/No-Go Decision Table" with columns: `{Hypothesis combination | Score | Verdict | Forward action}`. Rows: H1+H2+H3 (2.5, go, full Track B), H1+H2 (2.0, go, full Track B), H1+H3 (1.5, ambiguous, 3.1c gated pilot), H2+H3 (1.5, ambiguous, 3.1c gated pilot), H1-only (1.0, ambiguous, 3.1c gated pilot), H3-only (0.5, no-go, evaluation_observations.md), None (0, no-go, evaluation_observations.md).
2. Add this table to Plan 02 description in CONTEXT.md, replacing the current prose "Go >= 2.0, Ambiguous 1.0-1.5, No-go < 1.0" with the explicit combination table.
3. Cross-reference `llm-recommendation.md` (from P6-IMP-10) to include the specific row from this table as the verdict source.
**Impacts:** Plan 02 go/no-go protocol, Plan 05 Track B activation gate
**Components:** P6-IMP-10, P6-IMP-13
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
**Verdict:** CONFIRM (Lens: ADV Validation) — explicit decision table with 7 rows, consolidates IMP-10 and IMP-13 correctly

### P6-CSC-01: P6-IMP-15 scope reduction may breach Plan 05 Track C minimum of 3 gaming archetypes
**Target:** CONTEXT
**What:** P6-IMP-15 adds a scope-reduction gate: "If Phase 0 produces archetype_count <= 2, reduce Phase 2 scope." But Plan 05's Upstream Integration Contract Track C specifies minimum "at least 3 gaming archetypes" for archetype-count.json. If Phase 1 produces fewer archetypes due to scope reduction, Track C minimum is not met, triggering Track C degradation and routing to Unobserved Phenomena. This degradation path is technically handled ("If < 2 categories present: flag as 'corpus-limited'"), but the archetype minimum of 3 is not addressed by the category threshold of 2. archetype_count and category_count are separate measurements (P6-IMP-15 conflates them in the scope-reduction gate).
**Why:** The scope-reduction gate in P6-IMP-15 reduces Phase 2 adversarial transcript count (2 instead of 3-4), which directly constrains Phase 1 archetype generation scope. If the executor follows the reduced scope and produces only 2 archetypes, Plan 05 Track C silently degrades. The executor needs to know this is an expected consequence, not a failure.
**How:**
1. In P6-IMP-15's scope-reduction gate, add explicit note: "If scope reduction produces archetype_count < 3, Plan 05 Track C will degrade to 'corpus-limited' -- this is expected and not a failure. Record in archetype-count.json: `scope_reduced: true, original_minimum: 3, actual: N`."
2. Update Plan 05 Upstream Integration Contract Track C to add: "If archetype_count < 3 AND `scope_reduced: true` in archetype-count.json, Track C degradation is pre-authorized by Phase 0 scope-reduction gate -- skip Unobserved Phenomena routing for this specific case."
**Impacts:** Plan 03/04, Plan 05
**Trigger:** P6-IMP-15
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)
**Verdict:** CONFIRM (Lens: ADV Validation) — concrete cascade prevention with pre-authorized degradation path

### P6-ADV-R-01: cost-summary.json `level` field has no defined enum or record multiplicity
**Target:** CONTEXT
**What:** The `level` field in the Plan 01 cost-summary.json artifact manifest has no defined enum and no record-multiplicity specification. An executor cannot determine whether cost-summary.json contains one record or multiple records at different granularity levels, or what `level` values are valid.
**Why:** Ambiguous schema fields in a time-boxed session (Plan 01 is single-session) cause the same debugging overhead as incorrect schemas. The `level` field must have a defined value space before Plan 01 executes. `LOC_per_FP_removed` is a required 3.1f input and must not be removed.
**How:**
1. In the Plan 01 Produced artifact manifest entry for cost-summary.json, expand `level` to specify valid values and record multiplicity: `level: "before"|"after"` (2 records per experiment run).
2. Add parenthetical to artifact manifest row: "(2 records: before and after runs)".
3. Retain all existing fields including `LOC_per_FP_removed` — it feeds the Loop Economics Formula (3.1f cost ceiling definition).
**Impacts:** Plan 01 artifact manifest — 1-line schema annotation
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — schema field disambiguation
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Origin:** REFRAME of P6-IMP-04 (Lens: Interrupted Review Recovery)

## Post-Review Synthesis
**Items created:** P6-SYN-01, P6-SYN-02, P6-CSC-01
**Key insight:** element-preregistration.json has become a load-bearing artifact accumulating fields from 5 independent items without a unified schema or temporal ordering, creating execution-time discovery risk. Additionally, the go/no-go decision logic is split across two items (P6-IMP-10 and P6-IMP-13) that must be implemented as a single consolidated table to avoid contradictory intermediate states.
