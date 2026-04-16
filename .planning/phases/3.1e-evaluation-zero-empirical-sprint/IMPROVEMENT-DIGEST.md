# Improvement Digest

**Last updated:** 2026-02-25
**Passes completed:** 8 (7 pre-plan + 1 post-plan)
**Total proposed:** 257 (234 pre-plan + 23 post-plan)
**Total merged:** 233 (211 pre-plan + 22 post-plan)
**Total rejected:** 3 (P4-IMP-29, P4-IMP-34, P6-IMP-02)
**Total reframed:** 28 (27 pre-plan + 1 post-plan: P1-IMP-10)
**Active items:** 0

## Active Items

None. All items resolved across 8 passes (7 pre-plan + 1 post-plan).

## Rejection Log

### P1-IMP-08: "Binary answer" framing suppresses fix cost spectrum [REFRAMED, Pass 1]
**Proposed:** Plan 01 should produce fix cost spectrum as a deliverable
**Reframed because:** Fix cost requires examining multiple FP root causes across 65-FP corpus — Plan 04's territory, not Plan 01
**Reframed into:** P1-ADV-101

### P1-IMP-09: REASONING_PROMPT_TEMPLATE is dead code [REFRAMED, Pass 1]
**Proposed:** Plan 02 requires new invocation architecture
**Reframed because:** Template is not just "not called" but "not defined well enough to call" — rubric must be defined first
**Reframed into:** P1-ADV-201

### P1-IMP-15: JudgeBench hard-case on UnstoppableVault [REFRAMED, Pass 1]
**Proposed:** If LLM evaluator scores confident-wrong transcript highly, it's unreliable
**Reframed because:** Evaluator measures reasoning PROCESS quality (Axis A), not conclusion correctness (Axis B). The test would generate a false no-go.
**Reframed into:** P1-ADV-401

### P1-IMP-18: Transcript generation needs explicit 30-minute time-box [REFRAMED, Pass 1]
**Proposed:** Hard time-box with synthetic fallback
**Reframed because:** "Proceed with synthetic anchors" replicates fabrication anti-pattern. Synthetic go validates API, not evaluation quality.
**Reframed into:** P1-ADV-202

### P1-IMP-26: Plan 03's ~100 LOC estimate is a distraction [REFRAMED, Pass 1]
**Proposed:** Replace LOC estimate with decision document
**Reframed because:** Removing LOC estimates without replacing effort signals removes self-constraint at expansion moment
**Reframed into:** P1-ADV-501

### P2-IMP-05: has_access_gate already in none: block but not working [REFRAMED, Pass 2]
**Proposed:** Research whether builder bug or pattern engine bug
**Reframed because:** This is a precondition failure, not a research question. Session 0 must verify properties before any YAML fix.
**Reframed into:** P2-ADV-1-01

### P2-IMP-17: "Goodhart risk" is a category error [REFRAMED, Pass 2]
**Proposed:** Quantify Goodhart risk
**Reframed because:** Heuristic is a disposable proxy — nobody optimizes toward it. The risk is low validity, not Goodhart. Measuring gameability of a proxy nobody is gaming produces trivially predictable results.
**Reframed into:** P2-ADV-2-01

### P2-IMP-19: Plan 04's taxonomy classifies detection system behavior [REFRAMED, Pass 2]
**Proposed:** Group FPs by improvement action
**Reframed because:** Single-pass action framing biases toward fix-obvious clusters. Discovery must be undirected first.
**Reframed into:** P2-ADV-4-01

### P3-IMP-02: Per-function FP masking by _unique_patterns() deduplication [REFRAMED, Pass 3]
**Proposed:** Plan 01 must operate at per-function granularity due to _unique_patterns() masking intra-contract co-fires
**Reframed because:** Original framing underestimates depth — SideEntranceLenderPool near-certainly has TWO firings (flashLoan=TP, withdraw=FP). _unique_patterns() dedup masks the FP. Structural defect named explicitly.
**Reframed into:** P3-ADV-1-01

### P3-IMP-08: {observed} field for Plan 02 needs semantic validity constraints [REFRAMED, Pass 3]
**Proposed:** Plan 02 needs extraction algorithm for {observed} field
**Reframed because:** Plan 02 anchors are hand-written — nothing to compress. The real gap is semantic validity (reasoning-quality discrimination), not extraction. Extraction belongs to Plan 03/04 Phase 2.
**Reframed into:** P3-ADV-3-01

### P3-IMP-18: Plan 03/04 needs phase-gating via exit artifacts [REFRAMED, Pass 3]
**Proposed:** Time budgets for Plan 03/04's three-phase structure
**Reframed because:** Time budgets within coupled plan are silently skippable. Artifact gates solve the problem time budgets only approximate. Three-experiment structure becomes manageable with independent exit artifacts.
**Reframed into:** P3-ADV-4-01

### P4-IMP-06: Session 0 counting policy ambiguity across Plans 01/02/03/04 [REFRAMED, Pass 4]
**Proposed:** Session 0 must produce counting-policy.md document
**Reframed because:** counting-policy.md is a deliverable best generated BEFORE Session 0, not during it — avoids consuming session time on document creation
**Reframed into:** P4-ADV-1-01

### P4-IMP-08: Plan 01 Outcome C "more than ~200 LOC" is not a measurement [REFRAMED, Pass 4]
**Proposed:** Replace 200 LOC threshold with scope guard
**Reframed because:** 200 LOC is a scope boundary marker for the sprint, not a measurement target — removing it without replacement removes scope discipline
**Reframed into:** P4-ADV-2-01

### P4-IMP-11: Plan 02 conflates instrument precision with experiment design [REFRAMED, Pass 4]
**Proposed:** Separate rubric quality from scoring stability
**Reframed because:** Three-instrument measurement model (rubric fidelity, scorer stability, anchor discrimination) resolves the IMP-11 vs IMP-13 conflict
**Reframed into:** P4-ADV-3-01

### P4-IMP-15: Plan 02 non-determinism protocol doesn't match multi-run design [REFRAMED, Pass 4]
**Proposed:** Add variance measurement to non-determinism handling
**Reframed because:** Non-determinism protocol must match the three-instrument model — variance is per-instrument, not global
**Reframed into:** P4-ADV-3-02

### P4-IMP-16: Plan 03/04 compound degradation rule conflates corpus and rubric failures [REFRAMED, Pass 4]
**Proposed:** Split compound degradation into separate failure modes
**Reframed because:** The original split was correct but the rule boundaries needed corpus-failure vs rubric-failure separation
**Reframed into:** P4-ADV-4-01

### P4-IMP-18: Plan 03/04 Phase 1 Haiku plausibility has no quality check [REFRAMED, Pass 4]
**Proposed:** Add quality validation for Haiku plausibility results
**Reframed because:** Spot-check is sufficient — full quality validation is premature for a plausibility gate
**Reframed into:** P4-ADV-4-02

### P4-IMP-23: Plan 05 minimum-necessary contract lacks field provenance [REFRAMED, Pass 4]
**Proposed:** Add field provenance tracking to contract
**Reframed because:** Minimum-necessary contract with field-provenance is the correct frame — traces each contract element to the source requirement
**Reframed into:** P4-ADV-5-01

### P4-IMP-26: Session 0 behavioral-property probe needs systematic approach [REFRAMED, Pass 4]
**Proposed:** Add systematic property verification to Session 0
**Reframed because:** Source inspection is sufficient — behavioral probe via code reading, not runtime testing
**Reframed into:** P4-ADV-6-01

### P4-IMP-37: Plan 02 recommendation matrix has no falsification condition [REFRAMED, Pass 4]
**Proposed:** Add falsification conditions to recommendation matrix
**Reframed because:** Hallucination and variance checks are the falsification mechanism — recommendation matrix is falsified when instruments produce inconsistent recommendations
**Reframed into:** P4-ADV-7-01

### P5-IMP-05: Plan 01 Outcome A tests detection reproducibility but not graph construction reproducibility [REFRAMED, Pass 5]
**Proposed:** Add graph construction reproducibility test to Plan 01 Outcome A
**Reframed because:** Graph fingerprint infrastructure already exists in `kg/fingerprint.py` — the improvement proposed building what already exists. Replaced with concrete fingerprint persistence instruction.
**Reframed into:** P5-ADV-R-02

### P6-IMP-03: Session 0 branch table is prose IF blocks instead of structured decision table [REFRAMED, Pass 6]
**Proposed:** Replace prose IF/IF/IF with structured 3-row table
**Reframed because:** Formatting was correct but needed "Diagnostic Branch Table" heading for scannability
**Reframed into:** P6-ADV-1-01

### P6-IMP-04: Plan 01 cost-summary.json has no defined level enum [REFRAMED, Pass 6]
**Proposed:** Define level values and schema constraints
**Reframed because:** Diagnosis targeted wrong problem — three-level cost measurement was correct; real issue was ambiguous `level` enum and record multiplicity
**Reframed into:** P6-ADV-R-01

### P6-IMP-14: No protocol for real transcript search [REFRAMED, Pass 6]
**Proposed:** Add search depth, format qualification, and time budget for transcript search
**Reframed because:** Scope was too broad; narrowed to specific search protocol with qualification definition
**Reframed into:** P6-ADV-2-01

### P7-IMP-05: Type D Persistent Failure Has No Defined Terminal Action [REFRAMED, Pass 7]
**Proposed:** Add terminal action for Type D LLM invocation failure (schema/API error not recoverable by retry)
**Reframed because:** Original framing confused LLM_unreliable (evaluative) with lm_invocation_failed (mechanical). Terminal action must use correct status code and route through smoke test gate.
**Reframed into:** P7-ADV-201

### P7-IMP-08: `finding['explain']` structure is unverified before extraction loop [REFRAMED, Pass 7]
**Proposed:** Add structural validation of finding['explain'] key before extraction
**Reframed because:** Validation scope was too narrow — must validate full pattern structure, not just explain key. Implemented as BLOCKING pre-flight with validate-pattern-structure.sh + assert-explain-keys.py.
**Reframed into:** P7-ADV-101

### P7-IMP-12: 'specificity unvalidated' annotation has no 3.1c forwarding protocol [REFRAMED, Pass 7]
**Proposed:** Add protocol to forward specificity-unvalidated patterns to 3.1c
**Reframed because:** Forwarding requires field-provenance validity_status annotation + pilot_required flag, not just a protocol sentence. Structural forwarding rule needed at degradation rules level.
**Reframed into:** P7-ADV-401

### P4-IMP-29: Plan 05 "first real execution" framing is marketing [REJECTED, Pass 4]
**Proposed:** Remove "first real execution" language from Plan 05
**Rejected because:** Language serves as scope anchor — removing it without replacement risks scope expansion

### P4-IMP-34: Session 0 golden-path walkthrough duplicates existing pre-task [REJECTED, Pass 4]
**Proposed:** Add golden-path walkthrough as Session 0 pre-task
**Rejected because:** Duplicates P4-IMP-20's systematic verification — same verification from different angle

### P6-IMP-02: Session 0 graph_fingerprint instruction has naming hazard [REJECTED, Pass 6]
**Proposed:** Rename graph_fingerprint() → fingerprint_graph() for consistency
**Rejected because:** API name is `graph_fingerprint()` in the codebase; renaming would create a different naming hazard. Warning note added instead.

### P1-IMP-10 (post-plan): Plan 02/03 parallelism creates rubric version conflict [REFRAMED, Post-Plan Pass 1]
**Proposed:** Add sequencing constraint between Plan 02 rubric revisions and Plan 03 Phase 1
**Reframed because:** Scope reduction was the wrong fix — needs sequencing via rubric-freeze gate
**Reframed into:** P1-ADV-31

## Convergence State

Post-plan Pass 1: 0% cosmetic (0/23). Signal: ACTIVE — all structural. Character: plan-level execution gaps (CORPUS validation, runtime limit invariant, handoff schemas, negative control operationalization, fingerprint method, categorical IC, artifact-existence gates, JSON schema convention).
Pass 7: 0% cosmetic (0/18 counted items). Signal: ACTIVE — all 18 structural. Character: execution-boundary precision (dry-run pre-flights, extraction guards, GATE A pre-commitment, smoke test session gates, Track B constrained sub-state, compound state precedence table, sprint-level DECISION-LOCK).
Pass 6: 4.2% cosmetic (1/24 counted items). Signal: ACTIVE — 23 structural + 1 cosmetic. Character: execution-protocol precision (schema enums, temporal gates, unified decision tables, compound failure protocols).
Pass 5: 9.1% cosmetic (3/33 counted items). Signal: ACTIVE — 30 structural + 3 cosmetic. Character: interaction-level bugs across independently-refined components.
Pass 4: 8.2% cosmetic (4/49 counted items). Signal: ACTIVE — 43 structural + 2 creative-structural + 4 cosmetic.
Pass 3: 0% cosmetic (0/20 counted items). Signal: ACTIVE — all structural improvements targeting cross-plan data flow.
Pass 2: 3.8% cosmetic (1/26 counted items). Signal: ACTIVE — substantial structural findings.
Pass 1: Not computed (first pass).
Note: All passes < 6 had convergence gate INFORMATIONAL (pass 1-2) / ADVISORY (pass 3-5). Pass 6 gate was ACTIVE (4.2% well below 90% threshold).

## Provenance Manifest

### Pass 1 Items
| Item ID | Verdict | Lens | Key Insight |
|---------|---------|------|-------------|
| P1-IMP-01 | implemented | Plan 01 Coherence | access-tierb-001 operates as Tier A-only — MVL proves Tier A sub-cycle only |
| P1-IMP-02 | implemented | Plan 01 Coherence | MVL proves metric sensitivity, not loop automation — different claims |
| P1-IMP-03 | implemented | Plan 01 Coherence | ReentrancyWithGuard has 12 FPs from 12 patterns — needs contract swap |
| P1-IMP-06 | implemented | Plan 01 Coherence | Zero tolerance on TP regression with only 2 TPs |
| P1-IMP-10 | implemented | LLM Evaluation Architecture | Anchors must be grounded in domain correctness, not heuristic alignment |
| P1-IMP-11 | implemented | LLM Evaluation Architecture | Spearman rho for rank ordering, not just score spread |
| P1-IMP-20 | implemented | Adversarial Methodology | GVS citation_rate is trivially exploitable via regex keyword stuffing |
| P1-IMP-28 | implemented | Adversarial Methodology | Observation layer is third gameable layer — obs_bskg_query.py:25 exploit |
| P1-SYN-01 | implemented | Cross-Cutting | Systemic missing ground truth across all comparison plans |
| P1-SYN-02 | implemented | Cross-Cutting | Three gameable layers share one root cause — content never validated |
| P1-SYN-03 | implemented | Cross-Cutting | Serial prerequisite chain breaks intended parallel sprint — Session 0 pattern |

**Conflicts resolved:** None (Pass 1, no prior pass)
**Synthesis patterns:** SYN-01 (components: ADV-102, ADV-201, ADV-202, IMP-12, IMP-10); SYN-02 (components: IMP-20, IMP-28, ADV-302); SYN-03 (components: IMP-27, ADV-102, ADV-201, ADV-202, IMP-17, ADV-301)

### Pass 2 Items
| Item ID | Verdict | Lens | Key Insight |
|---------|---------|------|-------------|
| P2-IMP-01 | implemented | Measurement Foundation | Baseline document internally contradictory — Session 0 re-run required |
| P2-IMP-03 | implemented | Experiment Design | Plan 01 binary answer unfalsifiable — reframed to three-outcome measurement |
| P2-IMP-09 | implemented | Framework Validity | 7-move decomposition doesn't exist — Plan 02 tests ad-hoc dimensions |
| P2-IMP-10 | implemented | Framework Validity | Go/no-go should be per-dimension matrix, not single binary |
| P2-IMP-11 | implemented | Experiment Design | claude -p correct for stateless scoring — Agent Teams is confounding variable |
| P2-IMP-18 | implemented | Scope Discipline | Plans 03+04 merge — same corpus, same technique, saves ~1 session |
| P2-ADV-1-01 | implemented | Measurement Foundation | Builder diagnostic protocol — verify BSKG properties before YAML fix |
| P2-ADV-2-01 | implemented | Framework Validity | Validity coefficient replaces Goodhart framing — actionable for 3.1c |
| P2-ADV-3-01 | implemented | Scope Discipline | Session 0 ceiling: 3 bounded tasks, explicitly excludes scope migration |
| P2-SYN-01 | implemented | Cross-Cutting | Pre-registration principle for all experiments |
| P2-SYN-02 | implemented | Cross-Cutting | Plan 02 wiring: rubric -> observed -> anchors (sequential dependency chain) |

**Conflicts resolved:** None (no cross-pass conflicts detected — passes are additive)
**Synthesis patterns:** SYN-01 (components: IMP-03, IMP-10, IMP-20, IMP-23, IMP-24); SYN-02 (components: IMP-13, IMP-14, ADV-2-02)

### Pass 3 Items
| Item ID | Verdict | Lens | Key Insight |
|---------|---------|------|-------------|
| P3-IMP-07 | implemented | LLM Decision Protocol | Spearman rho on n=3 only produces {-1, -0.5, 0.5, 1} — thresholds 0.6/0.8 unreachable |
| P3-IMP-12 | implemented | LLM Decision Protocol | Hypothesis (b) pre-falsified (BAD=16); replaced with reasoning_depth saturation test |
| P3-IMP-14 | implemented | Cross-Plan Integration | Taxonomy-archetype decoupling — Phase 0 (detector failures) ≠ Phase 1 (evaluator attacks) |
| P3-IMP-09 | implemented | LLM Decision Protocol | Rubric freeze needs calibration round with spread thresholds (GOOD-BAD >= 30) |
| P3-IMP-10 | implemented | LLM Decision Protocol | Default-30 dimensions make success criterion unfalsifiable — primary tier only |
| P3-ADV-1-01 | implemented | Measurement Validity | _unique_patterns() masks intra-contract TP+FP co-fires — per-function counting required |
| P3-ADV-2-01 | implemented | LLM Decision Protocol | Calibration transcript provenance contradiction blocks evidence base |
| P3-ADV-3-01 | implemented | Experimental Realism | {observed} must ensure reasoning-quality discrimination, not structural discrimination |
| P3-ADV-4-01 | implemented | Cross-Plan Integration | Phase-gating via exit artifacts replaces time budgets for Plan 03/04 |
| P3-SYN-01 | implemented | Cross-Cutting | Session 0 scope absorption — 7 improvements collectively exceed 1-session ceiling |

**Conflicts resolved:** None (passes are additive — P3 stress-tests cross-plan connections built by P1-P2)
**Synthesis patterns:** SYN-01 (components: IMP-01, IMP-02, IMP-03, IMP-05, IMP-06, ADV-1-01, ADV-2-01); SYN-02 (components: IMP-07, IMP-10, IMP-12, IMP-15); CSC-01 (trigger: IMP-14, cascade: taxonomy collapse fallback)

### Pass 4 Items
| Item ID | Verdict | Lens | Key Insight |
|---------|---------|------|-------------|
| P4-IMP-01 | implemented | Session 0 Integrity | Cache-independence is non-problem for one-shot baseline recording |
| P4-IMP-02 | implemented | Session 0 Integrity | Transcript provenance verifiable now — 5 min freed from session budget |
| P4-IMP-04 | implemented | Session 0 Integrity | Baseline deviation threshold: >30% FPs or >5 access-tierb-001 triggers review |
| P4-IMP-05 | implemented | Session 0 Integrity | Split task (a) into (a1) raw capture MUST + (a2) FP annotation SHOULD |
| P4-IMP-07 | implemented | Plan 01 Rigor | "Metric sensitivity" → "metric responsiveness" — honest scoping for 3.1f |
| P4-IMP-09 | implemented | Plan 01 Rigor | UnstoppableVault 13 FPs as observation target — most informative signal |
| P4-IMP-10 | implemented | Plan 01 Rigor | SelfiePool prediction chain — branch table for Session 0 diagnostic results |
| P4-IMP-12 | implemented | Plan 02 Statistics | Hypothesis (b) score prediction: formula gives 90 not 70 at 3 unique tools |
| P4-IMP-13 | implemented | Plan 02 Statistics | Held-out anchor breaks calibration circularity |
| P4-IMP-14 | implemented | Plan 02 Statistics | evidence_quality harder test — same query count, different interpretation quality |
| P4-IMP-17 | implemented | Plan 03/04 Thresholds | Phase 2 gate: rubric calibration quality floor (GOOD-BAD >= 30) |
| P4-IMP-19 | implemented | Plan 03/04 Thresholds | Specificity check — re-score GOOD anchor to detect over-rejection |
| P4-IMP-20 | implemented | Plan 03/04 Thresholds | Critical path parallelism: 4-4.75 sessions vs 5.5-6.25 serial |
| P4-IMP-21 | implemented | Plan 03/04 Thresholds | Stale 4/N threshold removed; ceil(N/2) authoritative post-merge |
| P4-IMP-22 | implemented | Plan 05 Quality | Unobserved Phenomena quality gate: evidence-anchor + testable question required |
| P4-IMP-24 | implemented | Plan 05 Quality | Partial upstream fallback: Plan 03/04 Phase 0 minimum, not full completion |
| P4-IMP-25 | implemented | Plan 05 Quality | Plan 02 dependency made explicit — three-part preconditions |
| P4-IMP-27 | implemented | Strategic Alignment | Multi-agent debate acknowledged as highest-risk assumption, deferred Phase 4 |
| P4-IMP-28 | implemented | Strategic Alignment | Budget recount: 8-12 elapsed, 5-6 work; "sprint" = methodology not speed |
| P4-IMP-30 | implemented | Strategic Alignment | Integration smoke test: detection→evaluation format gap characterization |
| P4-IMP-31 | implemented | Strategic Alignment | Measurement methodology decision: per-function (3.1e) vs per-vulnerability (EVMbench) |
| P4-IMP-32 | implemented | Strategic Alignment | Deferred list restructured: Killed / Conditional / Future |
| P4-IMP-33 | implemented | Strategic Alignment | Multi-agent info flow out of scope — Assumption 8 added |
| P4-IMP-35 | implemented | Cross-Plan Novel | 7-contract corpus limitation — Assumption 6: all results in-sample |
| P4-IMP-36 | implemented | Cross-Plan Novel | Cost measurement structured as named deliverable (cost-summary.json) |
| P4-IMP-38 | implemented | Cross-Plan Novel | Graph quality assumption + graph-property-error as Phase 0 action category |
| P4-IMP-39 | implemented | Cross-Plan Novel | Loop economics formula: cost_per_FP_removed, LOC_per_FP_removed |
| P4-ADV-1-01 | implemented | Session 0 Integrity | Pre-generate counting-policy.md from Decisions text |
| P4-ADV-2-01 | implemented | Plan 01 Rigor | Outcome C reframe: measurement result, not scope failure |
| P4-ADV-2-02 | implemented | Plan 01 Rigor | Mixed Outcome B pre-registration for partial FP reduction |
| P4-ADV-3-01 | implemented | Plan 02 Statistics | Three-instrument model: ordering + calibration + evidence |
| P4-ADV-3-02 | implemented | Plan 02 Statistics | Non-determinism protocol: pairwise variance, element pre-registration |
| P4-ADV-4-01 | implemented | Plan 03/04 Thresholds | Compound degradation split: corpus vs rubric independent branches |
| P4-ADV-4-02 | implemented | Plan 03/04 Thresholds | Haiku plausibility spot-check replaces heuristic floor gate |
| P4-ADV-5-01 | implemented | Plan 05 Quality | Minimum-necessary contract with field-provenance annotation |
| P4-ADV-6-01 | implemented | Strategic Alignment | Builder source inspection replaces rename-and-detect smoke test |
| P4-ADV-7-01 | implemented | Cross-Plan Novel | Plan 02 falsification: hallucination check + variance check |
| P4-ADV-8-01 | implemented | Plan 02 Statistics | Eligible dimension pool pre-registered from evaluator source |
| P4-SYN-01 | implemented | Cross-Cutting | Pre-registration checklist — phase-wide structural fix |
| P4-SYN-02 | implemented | Cross-Cutting | Plan 02 synthetic-only scope declaration — honest claims |
| P4-SYN-03 | implemented | Cross-Cutting | Exit artifact provenance manifest — authorship + schema |
| P4-CSC-01 | implemented | Cross-Cutting | Held-out anchor structural differentiation constraint |
| P4-CSC-02 | implemented | Cross-Cutting | INCONCLUSIVE entries accepted in Unobserved Phenomena |
| P4-CSC-03 | implemented | Cross-Cutting | N-dependent verdict context preserved in validity-matrix.json |

**Conflicts resolved:** IMP-11 vs IMP-13 (resolved by ADV-3-01 three-instrument model); IMP-15 vs IMP-11 (resolved by ADV-3-02); IMP-34 duplicates IMP-20 (IMP-34 rejected); IMP-27 absorbed Novel IMP-04 content
**Synthesis patterns:** SYN-01 (components: IMP-09, IMP-33, IMP-38, ADV-2-02 — pre-registration completeness); SYN-02 (components: IMP-13, ADV-3-01, IMP-35 — Plan 02 researcher-constructed inputs); SYN-03 (components: IMP-20, IMP-33, ADV-5-01 — exit artifact provenance); CSC-01 (trigger: IMP-12, cascade: held-out anchor design constraint); CSC-02 (trigger: IMP-22, cascade: INCONCLUSIVE gaps excluded from taxonomy); CSC-03 (trigger: IMP-21, cascade: N-dependent verdicts without N context)

### Pass 5 Items
| Item ID | Verdict | Lens | Key Insight |
|---------|---------|------|-------------|
| P5-IMP-01 | implemented | Plan 01 Coherence | fired_conditions field doesn't exist in pipeline output — schema mismatch |
| P5-IMP-09 | implemented | Plan 02 Coherence (go/no-go) | Divergence hypotheses (a) and (b) are the same — collapsed to H1, added H3 for BAD-MEDIOCRE |
| P5-IMP-10 | implemented | Plan 02 Coherence (go/no-go) | LLM call count makes 1-1.25 sessions infeasible — revised to 2-2.5 with scope reduction rule |
| P5-IMP-11 | implemented | Plan 02 Coherence (go/no-go) | n=2 pairwise flips are expected at GOOD-MEDIOCRE boundary — tiered kill switch |
| P5-IMP-17 | implemented | Assumption Stress Test | Validity coefficient has construct validity problem — heuristic and LLM measure different constructs |
| P5-IMP-22 | implemented | Cross-Plan Integration | Phase 1 quality gate paradox — LLM scoring requires Plan 02 rubric but runs in parallel |
| P5-ADV-R-01 | implemented | Assumption Stress Test | Plan 05 schema fields must be layer-qualified when constructs differ between heuristic/LLM |
| P5-ADV-R-03 | implemented | Structural Gap Probe | Budget ceiling breached when IMP-10 + IMP-22 compound — scope lever required |
| P5-ADV-R-07 | implemented | Structural Gap Probe | Go/no-go state table absent — CONFIRMED/DISCONFIRMED/EXCLUDED/BORDERLINE with fractional scoring |
| P5-CSC-01 | implemented | Post-Review Synthesis | H3 requires BAD anchor with graph queries (not structural absence) — design constraints added |

**Conflicts resolved:** None (single-pass, no cross-pass conflicts)
**Synthesis patterns:** SYN-01 (components: IMP-18, IMP-20, IMP-21 — Plan 05 upstream integration contract); CSC-01 (trigger: IMP-09 H3, cascade: BAD anchor design constraints)

### Pass 6 Items
| Item ID | Verdict | Lens | Key Insight |
|---------|---------|------|-------------|
| P6-IMP-01 | implemented | Executable Specification Fidelity | graph_fingerprint() naming hazard — fingerprint_graph vs graph_fingerprint confusion risk |
| P6-IMP-05 | implemented | Executable Specification Fidelity | is_tp join instruction wrong — CORPUS is list[GroundTruth] not dict; 2-min pre-flight type check |
| P6-IMP-06 | implemented | LLM Evaluation Protocol Robustness | Dual-parity split: unique_tool_count REQUIRED, bskg_query_count PREFERRED ±1; temporal discriminability gate |
| P6-IMP-07 | implemented | LLM Evaluation Protocol Robustness | Default flip_resolution missing for MEDIOCRE-BAD flips |
| P6-IMP-08 | implemented | LLM Evaluation Protocol Robustness | {observed} minimum schema needs 4 labeled sections |
| P6-IMP-09 | implemented | LLM Evaluation Protocol Robustness | Held-out anchor should be MEDIOCRE-tier on different contract, not BAD |
| P6-IMP-10 | implemented | LLM Evaluation Protocol Robustness | AMBIGUOUS band (1.0-1.5) needs forward action: 3.1c gated pilot |
| P6-IMP-11 | implemented | LLM Evaluation Protocol Robustness | Anti-contamination extended to prose paraphrase with contamination_check_passed field |
| P6-IMP-12 | implemented | LLM Evaluation Protocol Robustness | Schema validation added to retry protocol (Type D failure) |
| P6-IMP-13 | implemented | LLM Evaluation Protocol Robustness | H3 weight = 0.5; consolidated go/no-go decision table |
| P6-IMP-15 | implemented | Evaluator Assessment & Downstream Integration | Phase 0 scope-reduction gate when archetype_count <= 2 |
| P6-IMP-16 | implemented | Evaluator Assessment & Downstream Integration | Quality gate retry limit: max 1 hand-crafting cycle |
| P6-IMP-17 | implemented | Evaluator Assessment & Downstream Integration | Three-state validity decision: adversarial/normal/circular_excluded |
| P6-IMP-18 | implemented | Evaluator Assessment & Downstream Integration | Join key pattern_ids: list per cluster in action_map.json |
| P6-IMP-19 | implemented | Evaluator Assessment & Downstream Integration | 3.1c conditional entry protocol: data_rich/partial_data/blocked_recovery |
| P6-IMP-20 | implemented | Evaluator Assessment & Downstream Integration | Split cluster (3) into (3a) non-BSKG Bash + (3b) false event injection |
| P6-IMP-21 | implemented | Evaluator Assessment & Downstream Integration | Transformation sketch requirement (min 2 steps, bridge_complexity field) |
| P6-ADV-1-01 | implemented | ADV Validation | Diagnostic branch table reformatted from prose IF to structured 3-row table |
| P6-ADV-2-01 | implemented | ADV Validation | Pre-flight real-transcript search with synthetic detector heuristic |
| P6-ADV-R-01 | implemented | Interrupted Review Recovery | cost-summary.json level enum: "before"|"after", 2 records per experiment |
| P6-SYN-01 | implemented | ADV Validation | element-preregistration.json unified schema with GATE A/B/C temporal ordering |
| P6-SYN-02 | implemented | ADV Validation | Consolidated go/no-go decision table with 7 rows (H3=0.5 weight) |
| P6-CSC-01 | implemented | ADV Validation | IMP-15 scope reduction pre-authorizes Track C degradation when archetype_count < 3 |

**Conflicts resolved:** None (single-pass, no cross-pass conflicts)
**Synthesis patterns:** SYN-01 (components: IMP-06, IMP-07, IMP-08, IMP-11, ADV-2-01 — element-preregistration.json unified schema); SYN-02 (components: IMP-10, IMP-13 — go/no-go consolidated table); CSC-01 (trigger: IMP-15, cascade: Track C degradation pre-authorization)

### Pass 7 Items
| Item ID | Verdict | Lens | Key Insight |
|---------|---------|------|-------------|
| P7-IMP-01 | implemented | LLM Evaluation Integrity | LLM-Flatterer three-field pre-spec + graph-necessity test before Phase 1 adversarial generation |
| P7-IMP-02 | implemented | Upstream Integration | verdict_scope: adversarial_only + 3.1c_entry_constraint + scope-explicit Livshits conclusion in Phase 2 |
| P7-IMP-03 | implemented | LLM Evaluation Integrity | Rubric-discrimination check + vacuity-aware pass with INCONCLUSIVE routing in Phase 1 quality gate |
| P7-IMP-04 | implemented | GATE A Pre-commitment | flip_resolution moved to GATE A with rationale adequacy rubric (>=20 words + falsifiability regex) |
| P7-IMP-06 | implemented | Upstream Integration | cost-summary.json scope field: "full_7"|"targeted_3"|"lens_only" + cross-scope warning |
| P7-IMP-07 | implemented | Pre-flight Protocol | --dry-run BLOCKING pre-flight step before any session execution |
| P7-IMP-09 | implemented | Upstream Integration | _run_params: {limit, lens} added to session 0 baseline-before.json schema; comparison-script pre-run assertion |
| P7-IMP-10 | implemented | Upstream Integration | Track B constrained sub-state (active/constrained/absent) with state definitions + blocked_recovery decision table |
| P7-IMP-11 | implemented | Compound State | blocked_partial/blocked_zero sub-states + sprint-block.md 5-field minimum spec |
| P7-IMP-13 | implemented | Compound State | addressed_count='pending' protocol + state precedence table + DECISION-LOCK |
| P7-ADV-101 | implemented | Pre-flight Protocol | BLOCKING structure probe + extraction guard (_extraction_error field) before pattern extraction loop |
| P7-ADV-201 | implemented | GATE A Pre-commitment | invocation_status field separating mechanical failure from evaluative unreliability; smoke test as Session B gate |
| P7-ADV-401 | implemented | Upstream Integration | Specificity validation forwarding rule + field-provenance validity_status + pilot_required columns |
| P7-SYN-01 | implemented | Compound State | Pre-Sprint Decision Lock: DECISION-LOCK.md + pre-commitment.json for all plan decision rules before sprint start |
| P7-SYN-02 | implemented | Compound State | State precedence table: blocked_recovery > Ambiguous > pending; contradiction pair 2 precondition with +10 min budget |
| P7-CSC-01 | implemented | GATE A Pre-commitment | GATE A now authoritative for flip_resolution; GATE C redefined as apply-or-override only |
| P7-CSC-02 | implemented | Upstream Integration | constrained sub-state triggers evaluation_observations_constrained.md output variant for Plan 05 |
| P7-CSC-03 | implemented | Compound State | blocked_recovery routes to 3.1c_deferred.md output variant; Plan 05 artifact manifest updated |

**Conflicts resolved:** None (single-pass, no cross-pass conflicts)
**Synthesis patterns:** SYN-01 (components: IMP-11, IMP-13, CSC-03 — sprint-level DECISION-LOCK and state precedence); SYN-02 (components: IMP-10, CSC-02, IMP-13 — compound state handling); CSC-01 (trigger: IMP-04, cascade: GATE C role contraction); CSC-02 (trigger: IMP-10, cascade: constrained sub-state output variant); CSC-03 (trigger: IMP-13, cascade: deferred routing for blocked_recovery)

### Post-Plan Pass 1 Items (plan-level execution gaps)
| Item ID | Verdict | Lens | Key Insight |
|---------|---------|------|-------------|
| P1-IMP-01 | enhanced | Baseline Measurement Validity | Shallow isinstance misses element-level CORPUS type confusion |
| P1-IMP-02 | enhanced | Baseline Measurement Validity | Grep-based source check fragile; runtime assertion + meta field |
| P1-IMP-03 | confirmed | Baseline Measurement Validity | Explicit handoff schema between Plan 00 and Plan 01 |
| P1-IMP-04 | researched | Schema Synthesis | "Three levels" = three pipeline scopes (full_7, targeted_3, lens_only) |
| P1-IMP-05 | enhanced | Baseline Measurement Validity | Negative control expected_tp=0 with BLOCKING halt |
| P1-IMP-06 | researched | Baseline Measurement Validity | Use graph_fingerprint OO, not legacy fingerprint_graph |
| P1-IMP-07 | enhanced | Baseline Measurement Validity | counting-policy.md needs derivation, not just a choice |
| P1-IMP-08 | enhanced | LLM Evaluation Protocol Rigor | Categorical STRONG/WEAK/NONE replaces continuous IC at N=7 |
| P1-IMP-09 | enhanced | LLM Evaluation Protocol Rigor | Anchor feasibility with per-dimension + composite separation |
| P1-IMP-11 | confirmed | LLM Evaluation Protocol Rigor | RIGHT_ANSWER_WRONG_REASON as explicit NO-GO pattern |
| P1-IMP-12 | enhanced | LLM Evaluation Protocol Rigor | Five entity classes operationalize hallucination detection |
| P1-IMP-13 | confirmed | LLM Evaluation Protocol Rigor | Max 2 retries with scope reduction trigger |
| P1-IMP-14 | enhanced | LLM Evaluation Protocol Rigor | Spearman correlation selects least-correlated dimensions |
| P1-IMP-15 | enhanced | Schema Synthesis | Track A load-bearing vs supplementary artifacts |
| P1-IMP-16 | confirmed | Schema Synthesis | pending_human vs unavailable for Track B |
| P1-IMP-17 | enhanced | Schema Synthesis | Self-defining smoke test from field-provenance |
| P1-IMP-18 | confirmed | Schema Synthesis | Companion .json for machine consumption |
| P1-IMP-19 | enhanced | Schema Synthesis | Artifact-existence gates replace time budgets |
| P1-IMP-20 | confirmed | Schema Synthesis | REJECT example calibrates Unobserved Phenomena |
| P1-ADV-31 | confirmed | ADV Validation | Rubric-freeze gate for Plan 02→03 sequencing |
| P1-SYN-01 | enhanced | ADV Validation | Unified JSON schema convention across plans |
| P1-CSC-01 | enhanced | ADV Validation | Negative control halt recovery triage path |

**Conflicts resolved:** None (post-plan pass, no cross-pass conflicts)
**Synthesis patterns:** SYN-01 (components: IMP-01, IMP-03, IMP-17, IMP-18 — JSON schema convention); CSC-01 (trigger: IMP-05, depends: IMP-07, IMP-01 — halt recovery)

## Merged Summary

| Pass | Context | Plans | Research | Key Themes |
|------|---------|-------|----------|------------|
| 1 | 37 | 0 | 0 | Tier A scope clarity, metric sensitivity vs loop automation, Session 0 pattern, three gameable layers, serial prerequisite chain |
| 2 | 33 | 0 | 0 | Baseline contradictions, Plan 03+04 merge, validity coefficient, pre-registration, 7-move decoupling, budget recount to 5-6 sessions |
| 3 | 24 | 0 | 0 | Cross-plan data flow: n=3 Spearman impossibility, _unique_patterns() FP masking, taxonomy-archetype decoupling, phase exit artifacts, Session 0 scope absorption, rubric calibration protocol |
| 4 | 44 | 0 | 0 | Three-instrument model, metric responsiveness (not sensitivity), artifact manifest, pre-registration checklist, held-out anchor design, compound degradation split, Haiku plausibility, field-provenance, cost formulas, deferred triage |
| 5 | 32 | 0 | 0 | Interaction-level bugs: hypothesis dedup (H1/H2/H3), session estimate revision (2-2.5), tiered kill switch, budget scope lever, go/no-go state table, BAD anchor constraints, Plan 05 upstream integration contract, schema layer-qualification, anti-circularity tradeoff documentation |
| 6 | 23 | 0 | 0 | Execution-protocol precision: schema enums (level, flip_resolution), temporal gates (GATE A/B/C), unified decision table (7 rows, H3=0.5), compound failure protocols, scope-reduction cascade, 3.1c conditional entry, transformation sketches |
| 7 | 18 | 0 | 0 | Execution-boundary precision: dry-run + structure probe BLOCKING pre-flights, extraction guard, GATE A pre-commitment (flip_resolution + rationale rubric), smoke test Session B gate, invocation_status field, Track B constrained sub-state, blocked_partial/blocked_zero, compound state precedence table, sprint-level DECISION-LOCK |
| Post-plan 1 | 1 | 21 | 0 | Baseline measurement validity (CORPUS validation, runtime limits, handoff schema, counting-policy derivation), LLM evaluation protocol rigor (categorical IC, anchor feasibility, RIGHT_ANSWER_WRONG_REASON, hallucination classes, Spearman dimension selection, retry bounds, rubric-freeze gate), schema synthesis (artifact tiering, pending_human state, self-defining smoke test, JSON companions, artifact-existence gates, REJECT example), inter-plan JSON schema convention |
