# Improvement Pass 7

**Date:** 2026-02-25
**Phase:** 3.1e
**Status:** complete

## Pipeline Status

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 0 | 0 | — |
| Research | 0 | 0 | — |
| Merge-ready | 10 | 0 | — |
| ADV/SYN/CSC (open) | 8 | 0 | — |

**Pipeline:** [discuss] ✓ → [improve] ✓ → [pre-impl] — → [research] — → [implement] ! → [plan] ✓ → [execute] —
**Next:** /msd:implement-improvements 3.1e

## Convergence — Pass 7
Structural: 18  |  Cosmetic: 0  |  Ratio: 0% cosmetic
Threshold: 90% (novelty: genuinely_new_territory)
Signal: ACTIVE (0% < 90% threshold)
Value filter: Novel: 18  |  Maintenance: 0
Maintenance ratio: 0% (no self-justifying loop)

## Improvements

## Adversarial Lenses

| Lens | Brief | Items | Attack Vector |
|------|-------|-------|---------------|
| Measurement Artifact Self-Description | All Session 0/Plan 01 items share a root pattern: artifacts that exist but don't encode their own provenance constraints (scope, import-validity, structure, limit parameter). The fix set may be redundant if they share a single root cause. | P7-IMP-06, P7-IMP-07, P7-IMP-08, P7-IMP-09 | Does removing the --dry-run or _run_params from any one of these items produce the same safety gap, making the others cosmetic? Or are they genuinely independent failure modes requiring independent fixes? |
| Protocol Self-Consistency | Both Plan 02 items expose a gap between the protocol's stated guarantees and its structural implementation: P7-IMP-04 claims 'pre-registration' while placing the field in a post-observation gate; P7-IMP-05 claims 'invocation incompatible' is terminal while leaving the plan undefended after 20 minutes. | P7-IMP-04, P7-IMP-05 | Is GATE A recording of flip_resolution sufficient for P7-IMP-04, or does executor behavior under time pressure in Session B mean GATE A recording is itself unenforceable — making the fix address the wrong layer? |
| Adversarial Assessment Validity Scope | All Plan 03/04 items share a root pattern: the plan makes downstream claims (go verdict, gameability matrix, quality gate) that depend on measurements whose scope is narrower than implied. P7-IMP-01 may prove 'LLM detects wrong conclusions' instead of 'LLM distinguishes vocabulary from reasoning'; P7-IMP-02's go verdict licenses normal-transcript use from adversarial-only data; P7-IMP-03's quality gate applies clean-calibrated rubric to adversarial transcripts. | P7-IMP-01, P7-IMP-02, P7-IMP-03 | Is P7-IMP-02's verdict_scope annotation sufficient to prevent 3.1c from misusing the go verdict, or does each dimension need explicit stop conditions? Could P7-IMP-03 be rejected on grounds that a rubric discrimination failure is already detectable by the existing INCONCLUSIVE path? |
| Plan 05 Protocol Completeness | All four Plan 05 items expose states that are acknowledged to exist but have undefined executor actions: Ambiguous Track B (10), blocked_recovery done-criteria (11), specificity forwarding (12), addressed_count='pending' update authority (13). All are edge cases of upstream degradation. | P7-IMP-10, P7-IMP-11, P7-IMP-12, P7-IMP-13 | Are these four independent gaps, or are they all manifestations of a single design decision that Plan 05 assumes clean upstream outputs — making a single 'degradation handling protocol' the correct fix rather than four individual patches? If a unified protocol exists, which individual items become redundant? |

## Improvements

### P7-IMP-01: LLM-Flatterer Has No Falsifiable Specification
**Target:** CONTEXT (Plan 03/04, Phase 1 section)
**What:** LLM-Flatterer lacks falsifiable specification: no target vulnerability, no measurable definition of "correct vocabulary," no validation that the wrong conclusion requires graph knowledge to refute. Without this, the archetype tests Axis B (factual error detection) rather than Axis A (reasoning process failure detection), invalidating the Livshits conclusion.
**Why:** If the wrong conclusion is refutable from contract syntax alone (without BSKG traversal), LLM detection does not demonstrate graph-reasoning awareness. The archetype must force the evaluator to use graph knowledge to identify the failure — otherwise adversarial_validity measurement conflates two distinct LLM capabilities.
**How:**
1. Add three-field pre-specification block to archetype-count.json for LLM-Flatterer: `target_vulnerability` (specific vuln, e.g., flash-loan reentrancy on SideEntranceLenderPool), `correct_facts_used` (3-5 BSKG node IDs citing properties the transcript accurately invokes), `wrong_conclusion_type` (must contradict a BSKG-derived fact that is NOT recoverable from Solidity syntax inspection alone — e.g., concludes "balance updated before call" when graph shows WRITES_USER_BALANCE comes after TRANSFERS_VALUE_OUT).
2. Add graph-necessity test: for each candidate wrong conclusion, run alphaswarm query to confirm (a) the contradicted property is present in the graph and (b) the property is NOT inferrable from the function signature or NatSpec. If inferrable from syntax: reject and regenerate wrong conclusion.
3. Plausibility spot-check exemption remains, but add a single mandatory check: a human crafting executor confirms the wrong conclusion passes surface reading (sounds plausible from code), and a graph query is the only reliable refutation path.
4. Record these fields in archetype-count.json before Phase 1 quality gate runs — LLM-Flatterer exit criterion becomes "present AND graph-necessity test passed."
**Impacts:** Plan 03 confidence MEDIUM -> unchanged in level, but execution reliability improves. Phase 1 exit artifact validation becomes meaningful. Gameability matrix Livshits conclusion becomes falsifiable.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — specification-before-test is standard practice, but specifying adversarial transcript pre-conditions for LLM-as-judge evaluation has no established template.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the LLM-Flatterer specification gap exists in the original CONTEXT regardless of prior passes. No prior pass addressed what "correct graph vocabulary, wrong conclusion" means operationally.

### P7-IMP-02: Three-State Validity Decision Produces go/no-go from Adversarial-Only Sample
**Target:** CONTEXT (Plan 03/04, Phase 2 section)
**What:** The go verdict from Phase 2 gameability matrix licenses LLM evaluation in 3.1c, but adversarial_validity only measures LLM's ability to detect gaming on adversarial transcripts — normal transcript correlation is neither tested nor labeled as untested. A rubric that detects all 6 archetypes (go verdict) could be random noise on normal audit transcripts. The scope mismatch is unrecorded and the license is over-broad.
**Why:** 3.1c will consume the go/no-go verdict as an enablement signal. If verdict_scope is metadata only, 3.1c has no structural reason to restrict use to adversarial contexts. The Livshits conclusion ("LLM-as-judge provides meaningful defense") must be scoped or it becomes a categorical claim from a sample of adversarial transcripts only.
**How:**
1. Add `verdict_scope: adversarial_only` to validity-matrix.json go/conditional/no-go verdict block.
2. Add `3.1c_entry_constraint` field with explicit value: `"LLM evaluation enabled for: gaming detection only. Normal transcript scoring requires separate normal_validity measurement before use in 3.1c reasoning quality pipeline."` This is not a JSON label — it is an explicit stop condition that 3.1c's plan governance must reference.
3. Add scope-explicit sentence to Livshits conclusion template: "LLM-as-judge [provides/does not provide] meaningful defense against [N] gaming archetypes on adversarial transcripts. Transfer to normal transcript evaluation is not established by this measurement and requires Plan 03/04 Phase 2 normal_validity track."
4. Add a cross-reference in Plan 05 (3.1c entry): if validity-matrix.json verdict_scope == adversarial_only AND normal_validity == deferred, LLM scoring of normal transcripts requires a blocking RESEARCH item before enablement. This makes the constraint structural rather than advisory.
**Impacts:** Plan 03 Phase 2 exit artifact gains one field. Plan 05 Track B annotation 'validity-unassessed' continues to apply correctly. 3.1c conditional entry protocol gains a scope constraint.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1 — scope-labeling of validity measurements is standard in psychometrics but has no established template in LLM evaluator assessment.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — this gap is visible in the original CONTEXT. Prior passes added the three-state decision structure but did not address that adversarial_validity and normal_validity serve different downstream decisions. The go criterion's scope restriction is absent from the original design.

### P7-IMP-03: Phase 1 Quality Gate Rubric Mismatch — Adversarial Transcripts Scored on Clean-Calibrated Bands
**Target:** CONTEXT (Plan 03/04, Phase 1 section)
**What:** Phase 1 quality gate uses Plan 02 rubric (calibrated on GOOD/MEDIOCRE/BAD reasoning spread >= 30 pts) to score adversarial transcripts. Count-inflation archetype — many BSKG queries returning empty results — may score LLM >= 70 because rubric rewards evidence quantity without penalizing vacuity. Quality gate interprets this as "undetected gaming" and triggers hand-craft harder. If harder transcripts also score >= 70, retry fires and Phase 1 exits with an unrecorded rubric discrimination failure. Phase 2 then receives a gameability matrix built on a rubric that demonstrably cannot detect count-inflation.
**Why:** Rubric calibration failure produces false confidence in LLM robustness at the Phase 2 level. Unlike a transcript difficulty failure (which hand-crafting addresses), a rubric failure is not fixed by harder transcripts — the same rubric is applied. Without recording this distinction, Phase 2 conclusions are invalid for count-inflation archetypes and no downstream system knows it.
**How:**
1. Before quality gate, add archetype-level rubric-fit check: score all archetypes; if score range (max - min) < 20 pts across archetypes, flag `rubric_discrimination_suspected: true` (low variance may also reflect genuine difficulty — do not hard-fail on variance alone).
2. For count-inflation specifically: if LLM scores >= 70, extract evidence_invocations from transcript. If >= 50% of invocations have empty results (vacuity ratio), force a second evaluation pass with an explicit vacuity-aware prompt addendum: "Note: evidence items with empty query results do not constitute positive evidence." Record pre- and post-addendum scores separately.
3. If post-addendum score drops below 70: record `count_inflation_detected: true` for this archetype — quality gate resets to "undetected" = false.
4. If post-addendum score remains >= 70: record `rubric_discrimination_failure: count_inflation` and route to rubric degradation path rather than hand-craft harder. Document explicitly: "This is a rubric calibration failure, not a transcript difficulty failure."
5. Confirm in Phase 1 spec that rubric_discrimination_failure routes to INCONCLUSIVE rather than firing the retry cycle, preventing a retry that would produce the same calibration failure on harder transcripts. Track B annotation in validity-matrix.json must include `rubric_discrimination_failure` field when set.
**Impacts:** Plan 03 Phase 1 exit artifact gains one field. Quality gate retry limit (max 1 hand-crafting cycle) is preserved but conditioned: retry only if rubric_discrimination_failure is false. Plan 02 rubric degradation branch applies to Phase 1 quality gate failures caused by discrimination failure, not just Plan 02 divergence.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — rubric calibration failure modes in LLM-as-judge are partially documented (Zheng et al. 2023 MT-Bench), but the specific interaction between adversarial transcript structure and calibration anchor design is novel.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — this structural mismatch between rubric calibration domain (clean transcripts) and quality gate application domain (adversarial transcripts) is visible in the original CONTEXT. No prior pass addressed it. The quality gate was added in pass 5 to resolve the parallelism paradox; the calibration mismatch is a consequence of that design that no pass has examined.

### P7-IMP-04: flip_resolution Default Must Be Pre-Committed in GATE A, Not GATE C
**Target:** CONTEXT
**What:** `flip_resolution` is placed in GATE C which fires "after MEDIOCRE-BAD flip, before scoring" — post-observation. Pre-registration is only valid when committed before the outcome is observable. The current protocol contradicts itself: it claims pre-registration but defers `flip_resolution.default` until after the triggering event. Additionally, moving the field to GATE A without requiring a rationale allows rubber-stamp completion that defeats pre-commitment just as thoroughly as the timing problem does.
**Why:** EXPECTED.md criteria "pre-registration complete before scoring" cannot be satisfied under the GATE C placement. GATE A without a required rationale field degrades to a formality check rather than a genuine pre-commitment. Both failure modes corrupt the non-determinism protocol's validity guarantee.
**How:**
1. Move `flip_resolution: {default: "proximity_artifact", override_requires_written_justification: true, rationale: "<executor-written, min 1 sentence>"}` to GATE A (element-preregistration.json).
2. Redefine GATE C as apply-or-override only. GATE C never establishes the default; it only records whether the override path was taken and, if so, attaches the written justification.
3. Add GATE A completion check to Session B entry precondition: `flip_resolution.default` present AND `flip_resolution.rationale` non-empty AND GATE A timestamp precedes first Session B clock start. Executor must not advance to Session B if this check fails.
4. EXPECTED.md validation: "element-preregistration.json GATE A contains flip_resolution.default, flip_resolution.rationale (non-empty), AND both timestamps precede first llm-scores.jsonl entry."
5. Add one-line note to the non-determinism protocol section: "Default is chosen at GATE A based on prior domain knowledge, not on observed flips. Observed flips trigger GATE C apply-or-override, never GATE A authoring."
**Impacts:** Plan 02 GATE A content definition affected. EXPECTED.md criterion for pre-registration completeness affected.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — pre-registration before data collection is standard experimental protocol. The specific GATE assignment is adaptation.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — this contradiction exists in the original protocol design regardless of prior passes. Passes 4-6 added the GATE structure and the flip_resolution field, but none identified that GATE C fires post-observation, making the "pre-registration" claim false.

### P7-IMP-05: Type D Persistent Failure Has No Defined Terminal Action
**Target:** CONTEXT
**What:** The LLM call method section describes Type D failure as "valid JSON but wrong schema (score out of range, empty evidence, null fields) — retry with explicit schema reminder. Max 20 minutes in-session debugging." If the retry also fails, the protocol says "mark 'invocation incompatible,' log raw response." But the plan has no defined forward path after this marking. The executor has spent up to 20 minutes, `claude -p` is mechanically non-functional for schema compliance, and Plan 02 has no stated action. The three instruments require an LLM call — without it, no go/no-go is possible, Plans 03/04 cannot gate, and Plan 05 receives no LLM recommendation matrix.
**Why:** This is a blocking execution failure, not confusion. If Type D failures persist, the executor has no defined choice between: (a) abort Plan 02 entirely, (b) reduce to Instrument 1 only using manual rubric application without LLM, (c) treat both dimensions as LLM_unreliable and proceed to Plan 05 with that verdict, or (d) escalate. Without a defined terminal action, the executor will either stall or make an undocumented decision that invalidates downstream plan gating. The 20-minute budget implies the problem was anticipated — but the consequence was not.
**How:** 
1. In the "LLM call method" section of Plan 02's CONTEXT entry, add a terminal action after "mark 'invocation incompatible'": "Terminal action: both primary dimensions are classified as LLM_unreliable (not LLM_adds_signal, not LLM_equivalent). Record `lm_invocation_failed: true` in element-preregistration.json. Proceed to Plan 05 with recommendation: 'LLM evaluation mechanically non-functional — defer all Track B decisions to 3.1c pilot with infrastructure fix prerequisite.' Do NOT attempt manual rubric application as a substitute — this would conflate human judgment with LLM scoring validity."
2. Add a smoke-test precondition that must pass before Session B begins: invoke `claude -p` with a trivial schema-compliance prompt (the existing "smoke test" mention) and confirm JSON output matches expected schema. Record `smoke_test_passed: true/false` in element-preregistration.json GATE A. If smoke test fails, cancel Session B before investing 90-140 minutes, and execute the terminal action immediately. This converts a mid-session failure into a pre-session abort.
**Impacts:** Plan 02 session structure affected (smoke test gates Session B entry). Plan 05 must handle LLM_unreliable on both dimensions as a valid input state.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — graceful degradation paths for external service failures are standard. The specific framing (LLM_unreliable as terminal verdict rather than retry) is adapted to this context.
**Prerequisite:** no
**Status:** reframed → see P7-ADV-201
**Origin:** NOVEL — the 20-minute debugging window was added in prior passes, but the terminal action gap exists regardless. No prior pass defined what happens after "mark invocation incompatible." The smoke test as a Session B gate is new.

### P7-IMP-06: cost-summary.json schema cannot distinguish measurement scope from timing position
**Target:** CONTEXT (Session 0 / Plan 01 cost instrumentation section)
**What:** The cost-summary.json schema is specified as `{level: "before"|"after", compute_seconds, wall_clock_seconds, contracts_processed, cost_per_FP_removed, LOC_per_FP_removed}` with "exactly 2 records." Simultaneously, the plan describes three cost instrumentation levels: full 7-contract pipeline, targeted 2-3 contract run, and lens-report-only on pre-built graphs. The `level` enum encodes timing position (before/after the fix), not measurement scope. An executor running a targeted 2-3 contract run for baseline ("before") will produce `cost_per_FP_removed` computed on a subset stored in a record structurally identical to a full-pipeline record. The ratio is then meaningless: Plan 01's stated goal is "effort-to-improvement ratio" but the schema cannot represent the scope over which the ratio was computed. When Plan 05 consumes this artifact, it will have no way to flag that the two records used different measurement scopes.
**Why:** This is not a schema style issue. The specific failure: executor runs targeted 2-contract run for "before" (allowed by overflow rule), then runs full 7-contract for "after", both stored as `level: "before"` / `level: "after"`. The cost_per_FP_removed comparison is now apples-to-oranges. The plan's own falsification criteria for Outcome C (`if fix requires >200 LOC: STOP`) reads LOC_per_FP_removed from this schema — if the denominator FPs_removed is from different scopes, the STOP decision can be wrong. Adding a `scope` field (`full_7|targeted_3|lens_only`) makes the schema self-describing and allows Plan 05 to flag cross-scope comparisons.
**How:** 
1. In the Plan 01 cost instrumentation section, add a `scope` field to the cost-summary.json schema with enum `"full_7" | "targeted_3" | "lens_only"`. The schema becomes: `{level: "before"|"after", scope: "full_7"|"targeted_3"|"lens_only", compute_seconds, wall_clock_seconds, contracts_processed, cost_per_FP_removed, LOC_per_FP_removed}`. Specify: if the before-run used targeted scope due to overflow, set `scope: "targeted_3"` and add a `scope_note` field with free text. Cost comparison in Outcome C is only valid when both records share the same `scope` value — if they differ, emit warning "cross-scope comparison: ratio unreliable."
2. Add one sentence to the Outcome C falsification criterion: "If cost-summary.json records differ in `scope`, do not apply the >200 LOC STOP rule — escalate to human for scope-adjusted judgment."
**Impacts:** Plan 01 confidence stays HIGH but Outcome C evaluation becomes guarded; Plan 05 schema synthesis gains a reliable provenance field
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — tagging experimental records with scope/condition is standard in A/B test instrumentation
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the `level` enum ambiguity vs three cost levels exists in the original CONTEXT specification independent of any prior improvement pass

### P7-IMP-07: session-0-baseline-script.py has no smoke-test gate before the 35-minute clock starts
**Target:** CONTEXT (Session 0 pre-flight checklist)
**What:** session-0-baseline-script.py has no smoke-test gate before the 35-minute clock that exercises the PatternEngine call path.
**Why:** A dry-run limited to imports + schema print does not catch runtime call-path failures in PatternEngine.run(). An import that succeeds but a broken engine call signature still surfaces 5-10 min into task (a1), hitting the 35-minute overflow threshold with zero baseline output. Plan 01's entry criterion cannot be met.
**How:**
1. Add --dry-run flag to script template spec.
2. --dry-run behavior: (a) verify all imports succeed, (b) construct a minimal synthetic function node dict matching the BSKG schema, (c) call PatternEngine.run([synthetic_node], limit=1) and assert non-exception return, (d) print resulting schema shape to stdout, (e) exit 0.
3. Add to Session 0 pre-flight checklist as BLOCKING step before session clock: `python session-0-baseline-script.py --dry-run`.
4. If exit non-zero, pre-flight fails — do not start session clock. No graph builds are performed; total execution < 30 seconds.
**Impacts:** Plan 00 pre-flight checklist gains one blocking item; session-0-baseline-script.py template spec gains --dry-run requirement
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — smoke-test / dry-run before long-running batch scripts is universal practice
**Prerequisite:** no — this is about adding a flag to the pre-generated template, which is generated before session starts
**Status:** implemented
**Origin:** NOVEL — the gap exists in the original CONTEXT pre-flight checklist independent of prior passes; no prior pass addressed import validation before session clock

### P7-IMP-08: `finding['explain']` structure is unverified on the live codebase before first extraction
**Target:** CONTEXT (Session 0 task a1 description)
**What:** Task (a1) specifies: "Extract `fired_conditions` from `finding['explain']` (structure: `{all: [...], any: [...], none: [...], edges: [...]}`)". This is the first time the pipeline is run live in phase 3.1e. The structure description comes from design documentation, not from a codebase verification step. If `PatternEngine().run()` on the current codebase returns findings where `explain` has a different key structure (e.g., renamed keys, nested differently, or `explain` is `None` for some finding types), the extraction loop will either raise `KeyError` silently swallowed in a try/except or produce malformed JSON where `fired_conditions` fields are empty dicts. The baseline-before.json will pass schema validation (fields present) but contain no usable data. Task (a2)'s annotation step then annotates empty dicts, producing null results. Plan 01's Outcome B (YAML exclusion effectiveness) depends on `fired_conditions` to understand WHY FPs fire — empty dicts make root-cause analysis impossible.
**Why:** This fails silently. The specific failure sequence: `finding['explain']` returns `{'conditions': {'all': [...], ...}}` (one extra nesting level introduced in a refactor) instead of `{'all': [...], ...}`. The extraction code `finding['explain']['all']` raises `KeyError`. If the script wraps extraction in try/except (likely, to handle findings without explain), `fired_conditions` defaults to `{all: [], any: [], none: [], edges: []}`. All 65 FPs are recorded with empty fired_conditions. Baseline-before.json is syntactically valid. The executor does not notice. Plan 01 Outcome B runs, YAML fix is applied, delta is measured in raw counts but root-cause is unknown — the fix is blind. Plan 03/04 Phase 0 taxonomy (which consumes baseline-before.json) produces a taxonomy of empty-condition FPs, which cannot distinguish root causes.
**How:** 
1. Add to the Session 0 pre-flight checklist (after the "manually review one of the 3+ clustered evaluator code paths" item): "Structure probe (3 min): Run `PatternEngine().run(graph, patterns[:3], limit=5, explain=True)` on one pre-built graph. Print `findings[0]['explain']` raw. Confirm top-level keys are exactly `{all, any, none, edges}`. If structure differs: document actual structure, update extraction code in session-0-baseline-script.py before starting task (a1) clock. BLOCKING."
2. Add to task (a1) instructions, immediately before the fired_conditions extraction line: "Extraction guard: after extracting `raw_explain = finding.get('explain', {})`, assert `set(raw_explain.keys()) <= {'all', 'any', 'none', 'edges'}`. If assertion fails on any finding: log the actual keys, set `fired_conditions` to `{'_extraction_error': 'unexpected_keys', '_actual_keys': list(raw_explain.keys())}`. Do NOT silently default to empty lists — an extraction error must be distinguishable from a legitimate zero-condition finding."
**Impacts:** Plan 00 task (a1) gains a structural guard; Plan 01 Outcome B root-cause analysis is protected; Plan 03/04 Phase 0 taxonomy receives valid input
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — structure probes before batch extraction are common; the security-specific explain structure being novel makes the probe non-trivial to specify generically
**Prerequisite:** no
**Status:** reframed → see P7-ADV-101
**Origin:** NOVEL — no prior pass addressed live-pipeline structure verification for finding['explain']; the gap exists in the original CONTEXT task (a1) specification

### P7-IMP-09: Plan 01 Outcome A limit=200 enforcement has no mechanism in comparison-script.py spec
**Target:** CONTEXT (Plan 01 Outcome A falsification criteria)
**What:** Plan 01 states: "Outcome A reproducibility comparison must use `limit=200` in both runs." The comparison-script.py artifact is specified in the plan summary as producing the before/after comparison. However, the comparison-script.py specification does not include any mechanism to verify that the two baseline JSON files it compares were both produced with `limit=200`. The graph-fingerprints.json from Session 0 records `node_count` and `edge_count` but not the `limit` parameter used in pattern engine runs. An executor running Plan 01 who forgets to set limit=200 (e.g., uses the PatternEngine default of 50 or 100) produces a "before" with 200-limit findings and an "after" with default-limit findings. The fingerprints will match (graph construction is the same), so Outcome A passes. But the finding counts differ due to limit, not due to the YAML fix. Outcome B's delta is then wrong — the fix appears to remove more FPs than it actually did, or introduces apparent TP regressions that are actually limit artifacts.
**Why:** This is not a documentation clarity issue. The specific failure: Session 0 runs with limit=200 (explicitly specified). Plan 01 executor runs `PatternEngine().run(graph, patterns)` without specifying limit — defaults to 50. Before-run finds 65 FPs (limit=200 from session 0). After-run finds 31 FPs with default limit=50 (many legitimate findings simply not reached). Delta appears to be 34 FPs removed. True delta from YAML fix might be 8 FPs. Outcome B "passes" (FPs removed, no TP loss in the 50-finding window). The effort-to-improvement ratio is off by 4x. Plan 05 builds schemas on this ratio.
**How:** 
1. Add a `limit_param` field to the baseline JSON schema (both baseline-before.json and baseline-after.json): `{contract, pattern_id, ..., _run_params: {limit: int, lens: str}}`. The `_run_params` block is written once per contract-run (not per finding). comparison-script.py must check `_run_params.limit` in both files and ASSERT they are equal before computing delta. If limits differ: exit non-zero with message "ABORT: limit mismatch — before={X} after={Y}. Rerun after-baseline with limit={X}."
2. Add to Plan 01's pre-run checklist (before executing the YAML fix run): "Confirm limit parameter: grep session-0 baseline-before.json for `_run_params.limit`. Use this exact value for Plan 01 after-run. Default is NOT acceptable."
**Impacts:** Plan 01 Outcome A/B measurement integrity protected; Plan 05 schema synthesis receives reliable delta data; baseline JSON schema gains one `_run_params` block per contract-run
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — recording run parameters in output artifacts is standard reproducibility practice; the specific limit-parameter confusion is domain-specific
**Prerequisite:** no — this change is to the script template and comparison-script.py spec, both pre-generated before execution
**Status:** implemented
**Origin:** NOVEL — no prior pass addressed limit parameter provenance in the comparison pipeline; the gap exists in the original Outcome A specification

### P7-IMP-10: Ambiguous Verdict Creates Unresolvable Track B Activation Conflict
**Target:** CONTEXT
**What:** The Track B activation condition states "if Plan 02 produces LLM_adds_signal on >=
1 dimension" — where LLM_adds_signal is only CONFIRMED when all three criteria are met
(pairwise ordering correct, explanation cites dimension-specific signal, LLM_unreliable NOT
triggered). The go/no-go decision table has Ambiguous verdicts (score 1.0-1.5) whose defined
forward action is "3.1c with constraint: LLM evaluation gated behind real-transcript pilot."
This forward action implicitly requires a constrained Track B: 3.1c needs evaluation schemas
to design the pilot. But LLM_adds_signal = false for Ambiguous (explanation criterion fails),
so Track B is not activated, so no evaluation schemas are written, so 3.1c cannot perform the
forward action. The two rules are contradictory: Ambiguous forward action requires Track B
output, but the activation gate prohibits it.
**Why:** The current rules produce two incompatible outputs for the same input. Either the
activation gate must be widened to include Ambiguous (with a 'constrained' flag), or the
forward action for Ambiguous must be explicitly mapped to evaluation_observations.md content
that tells 3.1c "pilot needed before committing to LLM evaluation." Without this, the executor
must improvise — and improvised schema decisions are exactly what the "Experiment Before
Infrastructure" principle prohibits.
**How:** 
1. In the Plan 05 "Track B (graduated activation)" section, add a third activation state
   between "activated" and "absent": `Track B: constrained`. Trigger: Plan 02 produces >= 1
   Ambiguous verdict AND 0 Confirmed verdicts. Output: write
   `evaluation_observations_constrained.md` with content: (a) which dimensions were Ambiguous,
   (b) what the pilot transcript requirements are (drawn from the Ambiguous forward action), (c)
   which schema fields would be written if the pilot confirms signal. Set
   `phase_entry_mode: partial_data` with `track_b_state: constrained`. This produces something
   3.1c can act on.
2. In the 3.1c conditional entry protocol section, add a row for
   `track_b_state: constrained`: forward action is "run 1-transcript pilot before full Track B
   schema instantiation." This closes the loop — 3.1c knows exactly what to do with a
   constrained Track B.
**Impacts:** Plan 04 (the schema extraction plan as numbered in the plans section) — adds a
third output artifact and a third phase_entry_mode sub-state. Plan 02 (Area 2) — Ambiguous
verdict handling gains a defined downstream consumer.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — Three-state activation (on/off/conditional) is used in feature flags and
circuit breakers, but mapping it to schema activation in an empirical protocol is novel enough
to require design rather than copy.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — The Ambiguous verdict exists in the context, the Track B activation gate
exists in the context, but the contradiction between them is not acknowledged anywhere and
would cause execution failure independent of any prior improvement pass.

### P7-IMP-11: Blocked Recovery State Has No Applicable Success/Failure Criteria
**Target:** CONTEXT
**What:** Blocked recovery state (compound failure: Track A + Track B both unavailable) has no applicable success/failure criteria, and the existing pre-registration criteria are vacuously satisfied or inapplicable — losing their falsifiability property.
**Why:** Executor paralysis: cannot satisfy criteria that assume upstream data exists. More critically, vacuous satisfaction of criteria means no evidence that the pre-registration is being enforced. The Unobserved Phenomena list, which requires evidence anchors, also has no exemption for blocked state — leaving it either empty (no anchors) or unpopulated (executor skips it entirely).
**How:**
1. Add two blocked_recovery sub-states to the sprint-block.md spec: (a) `blocked_partial` — at least one upstream artifact exists with parseable data; (b) `blocked_zero` — no upstream artifacts with parseable data.
2. For `blocked_partial`: Unobserved Phenomena entries are best-effort using available data, tagged `evidence_partial: true`. Contradiction pairs marked irresolvable with available evidence noted.
3. For `blocked_zero`: Unobserved Phenomena section contains exactly one entry: "no evidence anchors available — all phenomena unobserved." Contradiction pairs marked irresolvable with reason `no_upstream_data`.
4. sprint-block.md minimum content spec: missing artifacts table (artifact name, expected path, actual status), sub-state declaration, recovery sequence (which upstream plan must re-run first), phase_entry_mode: blocked_recovery.
5. Add sprint-block.md to artifact manifest with this spec.
6. Pre-registration success criteria: add branch — "if phase_entry_mode=blocked_recovery, sprint-block.md present with all five minimum-content fields" replaces criteria (a)-(d).
**Impacts:** Plan 04 task list — blocked_recovery branch gains explicit done-criteria, removing executor discretion in failure state.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — Graceful degradation with explicit exit criteria is standard in protocol design. Applying it to a blocked schema-extraction state requires adaptation but the pattern is well-understood.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — The blocked_recovery state was introduced in Pass 6, but the missing done-criteria for that state is a gap in the original pre-registration design that would cause execution failure regardless of prior passes. A first-time reader of the CONTEXT would not see done-criteria for the blocked state within one read-through (it requires cross-referencing pre-registration success criteria against the compound failure protocol and noticing the inapplicability — non-trivial).

### P7-IMP-12: 'specificity unvalidated' Annotation Has No 3.1c Forwarding Protocol
**Target:** CONTEXT
**What:** The Plan 03/04 Phase 2 may produce validity-matrix.json with dimensions annotated
'specificity unvalidated'. Plan 05 passes these into Track B schemas with the annotation
preserved. The compound degradation rules cover corpus-failure forwarding and rubric-failure
forwarding, but there is no defined 3.1c forwarding protocol for specificity-failure. 3.1c
receives Track B schemas annotated 'specificity unvalidated' with no instruction on what that
annotation means for experiment design.
**Why:** The compound degradation rules are the forwarding protocol system. Specificity-failure
is a third type of validity degradation that the system handles partially (it annotates but does
not route). The routing gap means the annotation exists only for human reviewers, not as a
machine-actionable constraint. For a phase explicitly designed as input to 3.1c experiment
design, this gap is execution-relevant: 3.1c's plan authors will read the schemas, see the
annotation, and have no protocol to follow.
**How:** 
1. In the compound degradation rules section (or the 3.1c conditional entry protocol section),
   add a specificity-failure forwarding rule: "If >= 1 dimension in validity-matrix.json carries
   'specificity unvalidated': (a) those dimensions in Track B schemas get an additional
   annotation `use_constraint: pilot_required_before_production_use`; (b) Plan 05 Unobserved
   Phenomena list must include at least one entry per unvalidated dimension with
   `measurement_difficulty: requires-infrastructure` and `target_phase: 3.1c`; (c) the
   field-provenance.md row for those dimensions gets `validity_status: specificity_unvalidated`
   instead of a clean provenance." This converts a silent annotation into a binding constraint
   that 3.1c can mechanically follow.
2. In the 3.1c conditional entry protocol, add a row: "If track_b contains dimensions with
   `use_constraint: pilot_required_before_production_use`: route those dimensions to a
   specificity-pilot sub-experiment before full evaluation infrastructure build. Document in
   phase_entry_mode as an additional constraint flag, not a separate mode." This tells 3.1c
   exactly what to do without introducing a fourth entry mode.
**Impacts:** Plan 04 — field-provenance.md minimum content gains a `validity_status` field for
specificity-degraded dimensions. Plan 03/04 (Area 3) — annotation now has a defined consumer.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1 — Propagating validity annotations with binding forwarding rules is analogous
to data lineage systems in data engineering, but the specific application to LLM evaluation
schema design has no direct prior art.
**Prerequisite:** no
**Status:** reframed → see P7-ADV-401
**Origin:** NOVEL — The 'specificity unvalidated' annotation exists in the context. The absence
of a forwarding protocol is not introduced by any prior improvement pass — it was a gap in the
original compound degradation design that Pass 6 did not close. A reader who traces the
annotation from validity-matrix.json through Plan 05 schemas to 3.1c consumption finds the
dead end without prior pass context.

### P7-IMP-13: Contradiction Pair 2 Has No Protocol for addressed_count = 'pending' at Execution Time
**Target:** CONTEXT
**What:** Contradiction pair 2 (Plan 01 YAML-fix-sufficient vs Plan 03/04 Phase 0
builder-fix-required) requires joining baseline-before.json by
`pattern_id in action_map['pattern_ids']`. The CONTEXT states "action_map.json
addressed_count field may be updated post-Plan-01 without re-running Phase 0 — this is
expected." But it provides no protocol for what Plan 05 does if addressed_count still reads
'pending' when Plan 05 begins its 15-20 minute contradiction pair 2 check.
**Why:** The 15-20 minute allocation was sized for the comparison, not for a prerequisite data
update step. If the update takes 5-10 minutes (read Plan 01 output, identify matching
pattern_ids, write updated addressed_count values), the total time exceeds the allocation by
33-67%. More importantly, the executor has no authority to modify action_map.json without a
defined protocol — it's a Plan 03/04 output artifact, and modifying it from Plan 05 is
cross-plan mutation with no documented precedent.
**How:** 
1. In the Plan 05 upstream integration contract section, add a precondition check for
   action_map.json: "Before contradiction pair 2 analysis: verify action_map['addressed_count']
   != 'pending' for all clusters. If any cluster has addressed_count = 'pending': execute
   action_map update step — read baseline-after.json, for each cluster's pattern_ids list count
   how many pattern_ids appear in baseline-after.json with is_tp = true (address confirmed), set
   addressed_count to that value, note the update in field-provenance.md as
   'post-hoc update from Plan 01 data.' Time budget: add 10 minutes to the 15-20 minute
   allocation when this step is required." This gives the executor authority and a procedure.
2. In the pre-registration success criteria, add: "Contradiction pair 2: if
   action_map update step was required, document it as (e) 'data state: updated at Plan 05
   execution.' This does not count as irresolvable — it counts as resolved with provenance."
   This prevents the executor from incorrectly classifying a solvable-but-stale data state
   as an irresolvable contradiction.
**Impacts:** Plan 04 time estimate — the 0.5 session estimate should note "up to +10 min if
action_map update step required." field-provenance.md minimum content gains a `data_state`
field (fresh | updated_at_plan05).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Cross-artifact update steps with provenance tracking are standard in data
pipeline design. The adaptation needed here is minimal.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — The 'pending' addressed_count state is documented in the CONTEXT as
expected, but no protocol for handling it at Plan 05 execution time exists anywhere in the
context. This would cause a time-budget violation and pre-registration failure independent of
any prior improvement pass.


---

### P7-ADV-101: `finding['explain']` — Pre-flight Structure Probe and In-script Extraction Guard (Replaces P7-IMP-08)
**Target:** CONTEXT (Session 0 task a1 description and pre-flight checklist)
**What:** `finding['explain']` structure validation is unverified before Session 0 task a1 clock starts, and extraction failures are indistinguishable from zero-condition findings at runtime.
**Why:** Two failure modes: (1) pre-session structure mismatch discovered mid-a1, halting task; (2) in-session exceptions silently produce empty dicts that poison Plan 01 Outcome B root-cause trace. Both must be caught before Session B entry.
**How:**
1. **Pre-flight (before Session 0 task a1 begins):** Add shell script `./scripts/validate-pattern-structure.sh contracts/TestContract.sol` — calls `alphaswarm build-kg --limit 1 contracts/TestContract.sol`, pipes first finding to `./scripts/assert-explain-keys.py` which verifies `finding['explain']` contains exactly keys `{all, any, none, edges}`. Exit code 1 if mismatch; prints found keys. Reference this in task a1 precondition.
2. **In-script (Session 0 task a1 execution):** Modify finding extraction in `src/alphaswarm_sol/detection/parser.py::extract_finding()` — wrap explain dict access in try/except. On KeyError or structural mismatch: set `_extraction_error: true`, copy unparsed explain to `_explain_raw` (dict as-is), leave explain keys as empty dicts. Log line with finding ID and error detail.
3. **Session 0 completion gate:** Reject baseline.json if any FP record has `_extraction_error: true`. Print summary: "N extraction errors detected; see baseline.json _extraction_error field for details."
**Impacts:** Session 0 task a1; Plan 01 Outcome B root-cause analysis protected; Plan 03/04 Phase 0 taxonomy receives valid input.
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented
**Origin:** ADV-CREATE (reframe of P7-IMP-08 — Lens: Measurement Artifact Self-Description)

### P7-ADV-201: Type D Persistent Failure — invocation_failed Status and Smoke Test Gate (Replaces P7-IMP-05)
**Target:** CONTEXT
**What:** Type D failure (valid JSON, wrong schema) has a 20-minute debugging window but no defined terminal action. The proposed fix of classifying both dimensions as LLM_unreliable conflates mechanical invocation failure (dimension never tested) with evaluative unreliability (dimension tested, LLM produced inconsistent results). These are distinct failure classes. Injecting invocation failure into the LLM_unreliable path corrupts the recommendation matrix's semantics and may incorrectly trigger Plan 05's evaluative-inconsistency recovery tracks.
**Why:** Blocking execution failure after 90-140 min of Session B investment with no defined exit causes executor stall or undocumented decisions. But the exit path must preserve the distinction between "LLM evaluation mechanically non-functional" and "LLM evaluation functionally unreliable" — Plan 05's routing logic depends on this distinction being clean.
**How:**
1. Introduce `invocation_status: "failed" | "ok"` field in GATE A (not GATE C). Type D persistent failure sets this to `"failed"`.
2. Terminal action after 20-minute window exhausted: set `invocation_status: "failed"`, set `lm_invocation_failed: true`, leave both dimension scores as `null` (not LLM_unreliable). Log raw response.
3. In element-preregistration.json, add a separate routing rule: if `lm_invocation_failed: true`, proceed to Plan 05 with recommendation "LLM evaluation mechanically non-functional — invocation incompatible, not evaluatively unreliable." Do NOT set LLM_unreliable for either dimension.
4. Smoke test as Session B gate: before Session B clock starts, run a single schema-compliance invocation against a fixed reference input. If it fails schema validation, abort to the terminal action immediately (converts mid-session Type D discovery to pre-session abort, preserving session investment guarantee).
5. Document the distinction in the recommendation matrix: LLM_unreliable = tested + inconsistent; invocation_failed = not tested + mechanical breakdown. These produce different Plan 05 routing.
**Impacts:** Plan 02 session structure affected (smoke test gates Session B entry). Plan 05 must handle lm_invocation_failed as a valid input state distinct from LLM_unreliable.
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented
**Origin:** ADV-CREATE (reframe of P7-IMP-05 — Lens: Protocol Self-Consistency)

### P7-ADV-401: 'specificity unvalidated' Forwarding Rule in Plan 05 Degradation Rules (Replaces P7-IMP-12)
**Target:** CONTEXT (Plan 05 compound degradation rules section)
**What:** Plan 05's compound degradation rules have no forwarding protocol for dimensions annotated 'specificity_unvalidated'. The annotation exists but has no defined output route.
**Why:** Without a routing protocol, 3.1c plan authors and executors will improvise inconsistent handling. Unvalidated dimensions must be explicitly forwarded as pilot-phase constraints, not silently carried forward.
**How:**
1. **Plan 05 CONTEXT (degradation rules section):** Add new subsection "Specificity Validation Forwarding." Define: if a dimension's `validity_status == 'specificity_unvalidated'`, the dimension receives output annotation `use_constraint: pilot_required_before_production_use`. Cite which prior Plan (03/04) discovered this unvalidated dimension.
2. **Plan 05 CONTEXT (Unobserved Phenomena section):** Add mandatory entry block for each dimension marked specificity_unvalidated in sprint output. Entry must state: why specificity could not be validated during 3.1e, what additional data would be needed to validate in 3.1c, what happens if dimension is used without pilot phase.
3. **Create file `.vrs/experiments/plan-05/field-provenance.md`:** Add table with columns: field_name | source_plan | validity_status (ready | specificity_unvalidated | reference_only) | pilot_required (yes/no) | notes. For each field from Plans 01-04, populate source_plan and validity_status. Set pilot_required=yes where validity_status=specificity_unvalidated.
4. **Update 3.1c conditional entry protocol:** Add section "Pilot-Phase Constraints" — states that fields marked pilot_required=yes in field-provenance.md must be treated as experimental and re-validated in 3.1c before shipping in 3.2.
**Impacts:** field-provenance.md (new file); Plan 05 CONTEXT (two additions); 3.1c entry protocol (new section).
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented
**Origin:** ADV-CREATE (reframe of P7-IMP-12 — Lens: Plan 05 Protocol Completeness)

---

## Convergence Assessment

**Novel improvements:** 3
**Filtered observations (not proposed):**
- DERIVATIVE: 0
- DEDUCIBLE: 0
**Cosmetic (of novel):** 0
**Self-justification ratio:** 0%

All three items address logic gaps or execution failure scenarios visible in the original CONTEXT that no prior pass addressed. Pass 6 introduced the quality gate retry limit and three-state validity decision without examining (a) what "LLM-Flatterer present" means as a falsifiable criterion, (b) whether adversarial_validity supports the scope of the 3.1c go verdict, or (c) whether the Plan 02 rubric's calibration domain is appropriate for scoring adversarial transcripts in the quality gate. These are genuinely novel structural issues, not derivative of prior pass artifacts.


## Convergence Assessment

**Novel improvements:** 2
**Filtered observations (not proposed):**
- DEDUCIBLE: 2 — Calibration criteria Goodhart risk (absolute score thresholds as calibration gates could incentivize spread-over-ordering; discoverable from "Rubric freeze protocol" section by anyone reading Plan 02 carefully); Held-out anchor contamination enforcement (behavioral discipline gap without structural enforcement, discoverable from "anti-circularity tradeoff" paragraph)
**Cosmetic (of novel):** 0
**Self-justification ratio:** 2 deducible / 4 total candidates = 50%

Both proposed items meet the execution failure bar: IMP-01 causes an unfalsifiable EXPECTED.md criterion (the pre-registration claim cannot be satisfied as designed); IMP-02 causes session stall or undocumented decision on a blocking path.

The two filtered items are real design weaknesses but would be discovered by any executor reading the plan before Session B begins — they do not require a pass-7 reviewer to surface.


## Convergence Assessment

**Novel improvements:** 4
**Filtered observations (not proposed):**
- DERIVATIVE: 0
- DEDUCIBLE: 0

**Cosmetic (of novel):** 0
**Structural (of novel):** 4

**Self-justification ratio:** 0% — all four items address execution failure risks present in the original CONTEXT specification, independent of any prior pass content.

**Assessment:** Pass 7 finds four genuine execution-failure risks that survived 6 prior passes. All four are in the execution boundary layer — the gap between specified behavior and actual runtime behavior. Prior passes addressed schema precision, measurement methodology, and protocol design. This pass addresses the four places where a correct-looking specification fails at execution time due to unverified runtime structure, missing scope tags, no import gate, and no parameter provenance. The phase is approaching genuine convergence — these are the last mechanical failure points in the measurement foundation. No restructuring required.


## Convergence Assessment

**Novel improvements:** 4
**Filtered observations (not proposed):**
- DERIVATIVE: 0
- DEDUCIBLE: 0
**Cosmetic (of novel):** 0
**Self-justification ratio:** 0%

All four items address execution failure scenarios (not confusion) that exist in the original
CONTEXT design independent of prior pass content. No derivative or deducible items were found
in this area after applying the Pass 3+ hard filter.

The four items cluster around a single structural pattern: the CONTEXT defines complex
multi-state protocols (Track B activation, compound failure, validity degradation, contradiction
checking) but each protocol has one edge case with no defined executor path. Passes 1-6
progressively refined the happy path for each protocol without closing the edge-case branches.
This is consistent with the "execution-protocol precision" convergence character noted in the
Pass 6 summary — the remaining gaps are specifically in the edge branches, not the main path.

---

## Post-Review Synthesis
**Items created:** P7-SYN-01, P7-SYN-02, P7-CSC-01, P7-CSC-02, P7-CSC-03
**Key insight:** Two systemic gaps emerge across all reviewed items: (1) pre-observation specification is consistently deferred or absent across Plans 01-04, creating a pattern where data collection begins before success criteria are fully locked; (2) terminal/edge states (Ambiguous, blocked_recovery, pending) share a structural deficiency — no complete handling protocol — which means the sprint's exit conditions are under-specified in exactly the states most likely to occur.

---

### P7-SYN-01: Pre-Observation Commitment Gap Across Plans 01-04
**Target:** CONTEXT
**What:** Four items across Plans 01-04 independently flagged post-hoc rationalization risk: decisions about outcome interpretation should be pre-committed, not derived after observation. Sprint pre-registers outcomes (EXPECTED.md) but each plan makes internal decision rules ad-hoc. Sprint-level decision-lock protocol is missing.
**Why:** Without unified pre-commitment, each plan independently risks retrofitting evaluation rules to observed data. This is especially critical for compound failure scenarios in Plan 05, where multiple plan outputs must be synthesized under consistent decision governance.
**How:**
1. **Create `.planning/phases/3.1e-evaluation-zero-empirical-sprint/DECISION-LOCK.md`:** Top-level document with sections for each Plan (01, 02, 03/04, 05). Each section lists: (a) outcome variables observed, (b) decision rules in JSON format (if outcome X and condition Y, then decision Z), (c) no-modification clause stating when rules are locked (before Session A execution).
2. **Pre-flight for each Plan:** Add "Pre-Commitment" section referencing DECISION-LOCK.md. Reproduce applicable decision rules as 1:1 copy. Executor must sign off (comment in plan) that rules were read pre-execution.
3. **Create `.planning/phases/3.1e-evaluation-zero-empirical-sprint/pre-commitment.json`:** Schema: `{ "plan_01": {rules...}, "plan_02": {rules...}, "plan_03_04": {rules...}, "plan_05": {rules...}, "locked_at": "ISO timestamp", "locked_by": "executor name" }`. Read by Plan 05 entry logic; modification after lock timestamp triggers REJECT.
4. **Plan 05 entry gate (new step 0):** Load pre-commitment.json, verify locked_at < current_time. If modification detected, halt with error "Decision rules modified after lock; aborting synthesis."
**Impacts:** PLAN-01, PLAN-02, PLAN-03/04, PLAN-05; creates new files DECISION-LOCK.md, pre-commitment.json.
**Components:** P7-IMP-01, P7-IMP-02, P7-IMP-03, P7-IMP-04
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
**Origin:** genuine

---

### P7-SYN-02: Terminal State Protocol Incompleteness Across Plan 05 Exit Conditions
**Target:** CONTEXT
**What:** Three items targeting Plan 05 and terminal states (P7-IMP-10, P7-IMP-11, P7-IMP-13) each independently found that an edge/terminal state has no complete handling protocol. IMP-10: Ambiguous verdict has contradictory forward actions. IMP-11: blocked_recovery has no success/failure criteria for the zero-data case. IMP-13: addressed_count='pending' has no protocol. These three states are not isolated — they can co-occur. The interaction between these states is unspecified.
**Why:** Individual fixes address each state in isolation but don't specify priority ordering when multiple terminal states apply simultaneously. Plan 05 synthesis logic needs a state precedence table so the sprint-block.md and field-provenance.md can be generated unambiguously when compound failure occurs.
**How:** 1. Add a state-precedence table to Plan 05 with three entries: if blocked_recovery active, it takes precedence over Ambiguous and pending sub-states. 2. Define the interaction: if blocked_partial AND addressed_count='pending', treat as blocked_zero for provenance purposes. 3. Add a state-conflict detection step at Plan 05 entry: enumerate active terminal states from Plans 01-04, resolve via precedence table, then execute exactly one output protocol.
**Impacts:** PLAN-05
**Components:** P7-IMP-10, P7-IMP-11, P7-IMP-13
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
**Origin:** genuine

---

### P7-CSC-01: GATE A Completion Check Becomes Unenforceable Without Rationale Adequacy Criteria
**Target:** CONTEXT
**What:** P7-IMP-04 moves flip_resolution to GATE A but creates an unverifiable gate — the "rationale adequacy" check has no measurable criteria, producing false assurance of validation.
**Why:** An unenforceable gate is worse than no gate; it masks validation gaps while appearing to enforce them. Executors will skip verification thinking it is already validated.
**How:**
1. **In P7-IMP-04 CONTEXT update (GATE A rationale_adequacy section):** Add validation rubric with two measurable criteria: (a) **Length check:** rationale must be >= 20 words (enforced by `len(flip_rationale.split()) >= 20` at gate evaluation); (b) **Falsifiability check:** rationale must contain at least one of: "if X then Y", "evidence suggests", "contradicts", "confirms", "signal: [metric]", "requires [condition]". Regex pattern: `r'(if|evidence|contradicts|confirms|signal:|requires)'` with count >= 1.
2. **Implementer reference:** In P7-IMP-04 How steps, add explicit gate validation call: `_validate_rationale(finding['flip_rationale'])` must return (length_pass: bool, falsifiable_pass: bool, error_msg: str).
3. **Gate rejection behavior:** If either criterion fails, set verdict=REJECT with reason "rationale_inadequate: length={found} words (min 20), falsifiable={found_count} signals (min 1)."
**Trigger:** P7-IMP-04
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

---

### P7-CSC-02: blocked_recovery Activation Ambiguous Under Track B Constrained Sub-State
**Target:** CONTEXT
**What:** P7-IMP-10's Track B "constrained" sub-state creates ambiguity for blocked_recovery activation. A constrained Track B is neither failed nor active, leaving blocked_recovery conditions undefined.
**Why:** Without clear state definitions, Plan 05 cannot reliably trigger blocked_recovery, leading to either premature compound failure or missed blocked state — both corrupt 3.1c entry decision.
**How:**
1. **Update P7-IMP-10 Track B state definitions:** Add three states to replace ambiguity: (a) **Track B failed:** produced output but all confidence/validity scores below thresholds; (b) **Track B pending:** not yet executed or in progress; (c) **Track B constrained:** produced output with mixed validity (some dimensions valid, others unvalidated). "Constrained is NOT a failure state; it means partial output usable."
2. **Define blocked_recovery activation (in Plan 05 CONTEXT):** Add decision table:
   - If Track A failed AND Track B failed → blocked_recovery: true
   - If Track A failed AND Track B pending → deferred (wait for Track B)
   - If Track A failed AND Track B constrained → partial_recovery: true
3. **Add partial_recovery compound state:** Plan 05 output variant "partial recovery" includes: (a) Track A findings with full confidence scores; (b) Track B findings marked `confidence_qualifier: 'constrained'` per dimension; (c) field-provenance entries for constrained dimensions; (d) note on revalidation in 3.1c.
**Trigger:** P7-IMP-10 and Plan 05 state machine definition.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

---

### P7-CSC-03: Plan 05 Has No Output Variant for RESEARCH-Blocked 3.1c Entry
**Target:** CONTEXT
**What:** P7-IMP-02 introduces a research-blocking rule for LLM scoring dimensions with verdict_scope=adversarial_only. This creates a Plan 05 outcome state (sprint succeeded but 3.1c entry gated on external RESEARCH) for which no output variant is currently defined.
**Why:** Plan 05 will either silently omit the blocking condition or incorrectly trigger sprint-block.md (full sprint failure), neither of which is accurate. A deferred-but-incomplete state requires its own output path.
**How:**
1. **Create `.vrs/experiments/plan-05/3.1c_deferred.md`:** New output variant. Schema: (a) header "3.1e Sprint Completed with Research Deferral"; (b) summary table: plan | dimension | verdict_scope | blocking_research_topic | unresolved_condition; (c) detailed section per dimension with recommendation; (d) 3.1c entry gate rule: "Do not proceed to 3.1c until RESEARCH item is DONE."
2. **Plan 05 decision rule (DECISION-LOCK.md entry):** "If any dimension has verdict_scope='adversarial_only' AND normal_validity=='deferred', Plan 05 produces 3.1c_deferred.md instead of sprint-successful.md."
3. **Update Exit Artifact Manifest in Plan 05 CONTEXT:** Add conditional row: "If (verdict_scope=adversarial_only AND normal_validity=deferred) then include 3.1c_deferred.md; status=conditional." Evaluated at Plan 05 entry before artifact routing.
4. **Activation specificity:** This rule applies only to dimensions from Plan 02 (LLM-scored findings) where P7-IMP-02 research-blocking rule fired.
**Trigger:** P7-IMP-02 and Plan 05 artifact routing.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 0
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

Recommendation: these four items are the last structural gaps in Plan 05. After merging,
the plan's executor paths should be fully specified for all observable input states.

