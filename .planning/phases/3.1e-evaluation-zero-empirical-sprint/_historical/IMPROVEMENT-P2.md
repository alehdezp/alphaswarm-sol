# Improvement Pass 2 — Phase 3.1e: Evaluation Zero

**Pass:** 2
**Date:** 2026-02-20
**Prior passes read:** 1
**Areas analyzed:** 3 (Detection Loop & Metrics, LLM Evaluation Architecture, Adversarial Resilience & Taxonomy)
**Agent count:** 3 improvement agents + 4 adversarial reviewers + synthesis pending
**Status:** complete

---

## Pipeline Status

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 0 | 1 | P1-IMP-28 prerequisite removed |
| Research | 3 | 0 | P1-IMP-01, P1-IMP-04, P2-IMP-05 |
| Gaps | 1 | 0 | P1-ADV-102 |
| Merge-ready | 8 | 0 | 8 P1 confirmed items |

**Pipeline:** `REVIEWED(24 IMP + 8 ADV-CREATE + 36 prior) → research(3) → gaps(1) → merge(8 P1 confirmed)`
**Next:** Synthesis review, then merge confirmed items from both passes

---

## Adversarial Lenses

| Lens | Brief | Items | Attack Vector |
|------|-------|-------|---------------|
| Measurement Foundation | Every Plan 01/02 measurement dimension has at least one broken prerequisite. The baseline document disagrees with itself, properties may not compute correctly, and counting conventions propagate ambiguously. Do these measurement fixes collectively transform Session 0 from a quick setup into a multi-session calibration exercise? | IMP-01, 02, 05, 06, 14, 15 | Does fixing measurement prerequisites one-by-one disguise a structural session cost that should be made explicit? |
| Framework Validity | Plan 02 tests LLM scoring against ad-hoc contract dimensions while the 7-move framework it is supposed to validate does not exist in the codebase. The go/no-go gate collapses a multi-dimensional signal into a binary that cannot distinguish rubric quality from framework validity. | IMP-09, 10, 12, 13, 17, 24 | Can Plan 02's go/no-go signal license 3.1c's 7-move investment when the experiment tests a structurally different decomposition? |
| Scope Discipline | Pass 1 correctly diagnosed scope inflation in plans but relocated scope to Session 0 rather than eliminating it. Pass 2 adds more items to Session 0. After all improvements, is this still a sprint? | IMP-07, 08, 16, 18, 21, 23 | Does solving scope inflation by migrating scope to Session 0 just rename the inflation rather than reducing it? |
| Experiment Design | Three experiments have structural design flaws: Plan 01 is unfalsifiable, Plan 04's taxonomy framing biases toward fix-obvious categories, and adversarial transcript counts are arbitrary. Are the proposed fixes genuinely experimental improvements or do they add design complexity without improving signal? | IMP-03, 04, 11, 19, 20, 22 | Do the experiment design improvements strengthen falsifiability or just add more specification to experiments that may not need it? |

---

## Improvements

### P2-IMP-01: Detection baseline document has internally contradictory metrics — Executive Summary vs Aggregate Table disagree on precision
**Target:** CONTEXT
**What:** detection-baseline.md contains two incompatible precision values: Executive Summary says "Precision: 25.0% (11 TP / 44 classified findings)" while the Aggregate Metrics table says "Precision: 13.3% (10 / 75)." Critically: the Executive Summary's denominator is 44, not present anywhere in the table's per-contract totals (which sum to 75). The 11 TP figure in the Executive Summary does not match the table's TOTAL row of 10 TP. This is not merely a methodology disagreement — the numerators differ too. The TP count (10 vs 11) suggests the Executive Summary was written at a different time or with different counting rules than the table.
**Why:** A before/after measurement where the "before" value cannot be independently reproduced from its source document fails the reproducibility criterion even before Plan 01 runs. The discrepancy is not just "which methodology" but "where did the 11th TP come from and why is the denominator 44 not 75."
**How:**
1. Add to `<research_needs>`: "Audit detection-baseline.md for the source of Executive Summary's 11 TP / 44 denominator. The table shows 10 TP / 75 total. These cannot be reconciled as a counting-method difference — they differ in TP count. Determine which is correct and mark the other as erroneous."
2. In Plan 01 deliverables, add "Session 0 task: re-run baseline on all 7 contracts to produce a fresh ground truth count before any fix. Do not inherit the existing document's precision as the 'before' value — re-derive it."
3. In Assumption 1, replace the 13.3% figure with "TBD (Session 0 re-run)" to make the dependency explicit.
4. Footnote: retain the explanation that a 25%/13.3% split COULD reflect deduplication methodology, but note the TP count discrepancy means this is not the only explanation.
**Impacts:** Plan 01 measurement validity, P1-ADV-102 (needs methodology lock, not just re-run)
**Research needed:** no — document reconciliation task
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Measurement Foundation):** The original How treats this as a "methodology lock" task (choose one of two valid methods). The deeper problem is that a document with different numerators in two sections cannot be resolved by methodology choice alone. The re-run is not optional — it's the only way to establish a clean baseline.

---

### P2-IMP-02: Fixing access-tierb-001 may regress TPs on OTHER contracts — cross-contract impact not analyzed
**Target:** CONTEXT
**What:** Detection baseline shows access-tierb-001 producing TPs on 4+ contracts (SideEntrance, NaiveReceiver, TrusterLender, SelfiePool). A `none:` block fix adding view/pure exclusions could exclude TPs on TrusterLenderPool's or SelfiePool's flashLoan(). P1-IMP-06 establishes zero-tolerance but only on primary test contracts.
**Why:** A fix that passes on 2 contracts but regresses on 2 others is a net negative Plan 01 wouldn't catch without the full 7-contract suite.
**How:**
1. Expand TP preservation to ALL 7 baseline contracts.
2. P1-IMP-05's cost level (a) "full 7-contract pipeline" becomes required, not optional.
3. Add to Assumption 1: "Pattern fix effects are cross-contract. 7-contract baseline is the minimum regression suite."
**Impacts:** Plan 01 scope (must run full suite), P1-IMP-05, P1-IMP-06
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Measurement Foundation):** Withstands scrutiny. The evidence is specific and grounded. Interacts with P2-IMP-07's scope erosion — requiring full 7-contract pipeline is the kind of Session 0 prerequisite that inflates Plan 01, but P2-IMP-07 already captures this.

---

### P2-IMP-03: Plan 01's "binary answer" is unfalsifiable — no scenario produces a definitive "no"
**Target:** CONTEXT
**What:** Plan 01 frames its value as a binary "does the detect → improve → re-detect cycle work?" But a YAML exclusion fix for access-tierb-001 WILL reduce FPs — the exclusion targets functions that are structurally present in the corpus. The real experiment is not about cycle existence. It is about: (a) whether the measurement pipeline is reproducible, (b) what the effort-to-improvement ratio looks like, and (c) whether the regression-free constraint is achievable.
**Why:** An unfalsifiable experiment is not a go/no-go gate — it is a demonstration. The rest of the phase builds on Plan 01 as a gate. If that gate always passes, the "gate" is an illusion.
**How:**
1. In Plan 01 `what it delivers`: replace "Binary answer" with: "Three-outcome measurement process: (a) pipeline reproducibility — run identical detection twice, check count stability; (b) YAML exclusion effectiveness — measurable FP reduction without TP loss; (c) effort-to-improvement ratio — LOC changed per FP removed."
2. Add explicit falsification criteria: "Outcome A fails if identical runs produce different counts (stop). Outcome B fails if zero FPs removed or any TP lost (revert). Outcome C fails if fix requires >200 LOC (scope mis-set)."
3. Remove "Binary answer" from `<domain>`. Replace: "Verified measurement process: reproducible pipeline + first quantified effort/FP ratio."
4. In Assumption 1: "HIGH confidence on FP reduction (structural); MEDIUM on TP preservation (depends on fix precision); LOW on effort ratio estimate (first measurement)."
**Impacts:** Plan 01 framing and success criteria
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** creative-structural
**Status:** implemented
**Adversarial note (Experiment Design):** The three-outcome reframe separates the trivially true result (YAML fix reduces FPs on view functions) from the actually informative results (pipeline stability, TP preservation, effort cost). Resolves interaction with P2-IMP-07: reproducibility and effort-ratio are lightweight measurements that replace the hollow binary.

---

### P2-IMP-04: Plan 05's schema extraction cannot discover what experiments weren't designed to observe — deeper circularity
**Target:** CONTEXT
**What:** P1-IMP-04 splits schema into Track A/B. But experiments measure what the designer thought important. Plan 05 schemas capture those measurements. The question "what did we NOT design experiments to observe?" is structurally unanswerable from results. Example: 14 redundant firings for ReentrancyClassic — no experiment measures REDUNDANCY as first-class metric. Plan 05 won't produce a `redundancy_ratio` field.
**Why:** Not fatal — but should be named so Plan 05's output is correctly scoped.
**How:**
1. Add to Plan 05: "Mandatory deliverable: 'Unobserved Phenomena' list — metrics baseline suggests are relevant but no experiment measured. Candidates: redundancy ratio, per-severity precision, time-to-first-TP."
2. "Schemas reflect what was measured, not what matters. The gap is 3.1c's design space."
**Impacts:** Plan 05 deliverables, 3.1c input quality
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** Plan 01, Plan 04
**Classification:** creative-structural
**Status:** implemented
**Adversarial note (Experiment Design):** Withstands the lens. The "Unobserved Phenomena" deliverable costs one LLM prompt and produces a named list. The three candidates are concrete and observable-but-unmeasured in the raw baseline. Risk: list grows into a 3.1c planning doc — framing should cap it at "candidates list, not a design specification."

---

### P2-IMP-05: `has_access_gate` is already in the `none:` block but not working — implies builder/property bug, not pattern YAML bug
**Target:** CONTEXT
**What:** The YAML is already correct by design: `none: has_access_gate=true` should exclude guarded functions. The pattern fires on onlyOwner-protected functions and balance-check-guarded functions despite this. Either: (a) the builder does not set `has_access_gate=true` for modifier-based access control, or (b) the builder sets it but the pattern engine ignores it in `tier_a_required` mode when Tier B tags are absent. Either path leads outside YAML territory. Plan 01's assumption "the pattern fix is straightforward" is directly falsified: the right condition IS in the YAML and IS NOT working.
**Why:** This is not a gap to research around — it is a precondition failure for Plan 01's core mechanism. If the builder doesn't compute `has_access_gate` for modifier-based control, then adding MORE `none:` conditions will also silently fail for any property the builder doesn't compute.
**How:**
1. See P2-ADV-1-01 for replacement diagnostic protocol.
**Impacts:** Plan 01 confidence (may drop to MEDIUM), scope (may expand beyond YAML)
**Research needed:** yes — what does `has_access_gate` currently compute?
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Measurement Foundation):** The original framing adds a research question and a caveat. Too weak. The observation is a precondition failure: Session 0 must verify property values on a known-guarded function before any YAML fix is attempted. Replaced by P2-ADV-1-01.

---

### P2-IMP-06: Finding counting policy creates hidden coupling between Plan 01 and Plan 05
**Target:** CONTEXT
**What:** The baseline contains three distinct counting conventions, not two: (1) per-pattern-firing on all functions including dependencies, (2) per-pattern-firing on target contracts only (75 total per Baseline Snapshot), (3) per-vulnerability-class after deduplication (44 total per Executive Summary). Plan 01 needs one for delta. Plan 05 needs one for schema fields. The 2x difference cascades through three phases.
**Why:** Locking "per-pattern-firing" for Plan 01 is correct but insufficient without also specifying dependency-contract exclusion policy (the baseline already excludes dependencies, giving 75 not a larger number).
**How:**
1. In `<decisions>`: "Finding counting policy for 3.1e: per-pattern-firing on target contracts only (excluding ERC20, Address, SafeTransferLib dependencies). Basis: detection-baseline.md Baseline Snapshot (75 total). Record in `.vrs/experiments/counting-policy.md` during Session 0."
2. Plan 05 schemas: include `counting_method` field with enum `{per_firing_target_only | per_vuln_class | per_firing_all}`. Default: `per_firing_target_only`.
3. In `<deferred>`: "Finding deduplication (per-vulnerability-class) as separate improvement axis. Estimated 3x noise reduction when implemented."
4. Cascade note for 3.1f: "All future precision measurements inherit `per_firing_target_only` convention until 3.1f explicitly migrates to deduplication."
**Impacts:** Plan 01, Plan 05, 3.1f
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Measurement Foundation):** The original "per-pattern-firing" doesn't specify dependency exclusion, which is the other dimension creating metric variation. Without explicit documentation, Session 0's re-run risks including or excluding dependencies differently.

---

### P2-IMP-07: Plan 01 has absorbed 6+ deliverables from Pass 1 — scope erosion defeats the ~50 LOC constraint
**Target:** CONTEXT
**What:** Plan 01 has absorbed infrastructure work from 7+ Pass 1 improvements. After additions: methodology lock (P2-IMP-01), 7-contract regression suite (P2-IMP-02), TP preservation checklist, cost instrumentation at 3 levels (P1-IMP-05), negative control designation, Tier A boundary notes. These are experiment setup, not experiment execution. The sprint constraint (~50 LOC) applies to the experiment, not to measurement setup.
**Why:** Session 0 is the only way to preserve the plan's sprint character. But Session 0 must be scoped just as strictly: if Session 0 has no ceiling, the inflation migrates.
**How:**
1. In Plan 01 deliverables: remove all measurement infrastructure items. Replace with: "Before/after FP counts on 7-contract suite, TP preservation confirmed. ~50 LOC YAML changes + ~20 LOC comparison script."
2. In `<decisions>`, define Session 0 scope ceiling: "Session 0 (timebox: 1 session max): (a) run fresh pipeline, record FP/TP counts as confirmed baseline; (b) write rubric v1.0 for 2 dimensions; (c) capture 1 real transcript; (d) optional: EVMbench scan. NOTHING ELSE."
3. Add to `<domain>`: "Session 0 is not a plan — it has no improvement loop, no deliverables file, no pass-fail gate. It is purely prerequisite completion."
4. "Total phase budget = Session 0 (1 session) + Sessions 1–7 (experiments). Session 0 must not consume more than 1 session."
**Impacts:** Plan 01 scope reduction, Session 0 refined
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Scope Discipline):** "Move to Session 0" is a scope migration instruction, not a scope reduction. Without a ceiling on Session 0, six passes collectively assign: baseline re-run, rubric write, transcript capture, EVMbench scan, methodology lock, counting policy, and TP enumeration. That is a 2–3 session budget disguised as "setup." The How must be a bounded list, not an open migration target.

---

### P2-IMP-08: EVMbench reference is cargo-culted — paper unread, claims from secondary descriptions
**Target:** CONTEXT
**What:** EVMbench referenced in 4 CONTEXT locations but `<research_needs>` still lists "Read EVMbench paper" as open. No research spike completed. Plan 05 says "Reference EVMbench methodology" — vacuous if nobody has read the methodology.
**Why:** Adds apparent rigor without actual content. Either read in Session 0 or explicitly defer.
**How:**
1. Plan 05: remove "Reference EVMbench where applicable." Replace: "Optional stretch if paper read during Session 0."
2. Move EVMbench reading to Session 0: "30 min to scan for detection-scoring fields. Output: bullet points or 'not relevant.'"
3. Decisions: "EVMbench is potential reference, not required. Plan 05 succeeds without it."
**Impacts:** Plan 05 false dependency removed
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** cosmetic
**Status:** implemented
**Adversarial note (Scope Discipline):** Withstands scrutiny. Removes a phantom prerequisite and makes a correct tradeoff. No scope-inflating second-order effects.

---

### P2-IMP-09: The 7-move reasoning decomposition does not exist in the evaluator — Plan 02 tests against a phantom framework
**Target:** CONTEXT
**What:** CLAUDE.md declares a "7-move reasoning decomposition" (HYPOTHESIS_FORMATION through SELF_CRITIQUE). The codebase confirms zero references in any .py or .yaml file. Actual evaluation contracts use {graph_utilization, evidence_quality, reasoning_depth, exploit_path_construction, arbitration_quality, evidence_weighing, investigation_depth} — 7 ad-hoc names, not the 7 declared moves. Plan 02's go/no-go is meant to decide 3.1c's 7-move investment, but the experiment tests ad-hoc dimensions with no structural relationship to the 7 moves. The confound: a "go" confirms LLM can score ad-hoc dimensions, which says nothing about 7-move validity.
**Why:** Two distinct questions: (a) "does LLM-as-judge produce better scores than heuristics on these dimensions?" and (b) "is the 7-move decomposition the right framework for 3.1c?" Plan 02 can answer (a) but is being used to justify (b). The go/no-go collapses both into one binary.
**How:**
1. In `<decisions>`: "Plan 02 evaluates LLM scoring against existing contract dimensions. It does NOT validate the 7-move decomposition. The 7-move framework remains unimplemented and untested — its validity is a 3.1c design decision."
2. In Plan 02 deliverables: "Per-dimension LLM evaluation recommendation for EXISTING contract dimensions."
3. In `<domain>`: "7-move framework validation is deferred to 3.1c. Plan 02 tests LLM-as-judge on ad-hoc dimensions — a necessary but different question."
4. Optional deferred: CLAUDE.md caveat that "7-move decomposition" is aspiration, not implemented infrastructure.
**Impacts:** Plan 02 scope clarity, 3.1c expectations
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Framework Validity):** The original How stops at documentation cleanup. The stronger fix clarifies the inference chain: go/no-go from Plan 02 cannot license the 7-move investment because the experiment tests a different decomposition. Without this, a "go" will silently validate the 7-move approach, which it does not.

---

### P2-IMP-10: The go/no-go binary is a false dichotomy — LLM evaluation likely works for SOME dimensions and not others
**Target:** CONTEXT
**What:** Plan 02 frames outcome as single binary: "go/no-go on LLM-as-judge for 3.1c." But evaluation contracts define 5+ dimensions. LLM may be excellent at `evidence_quality` (can verify citations) and terrible at `reasoning_depth` (subjective). A single gate collapses this into all-or-nothing investment.
**Why:** Most likely outcome is mixed. The right answer is "use LLM for dimensions X and Y, keep heuristics for Z." This changes 3.1c from "one evaluator" to "hybrid per dimension."
**How:**
1. Replace "go/no-go" with: "Per-dimension LLM evaluation recommendation matrix: {LLM_adds_signal | LLM_equivalent | LLM_unreliable}."
2. Success: "LLM_adds_signal on >= 2 dimensions: invest. 0 dimensions: no-go. 1: extend test."
3. Decision: "LLM evaluation investment is per-dimension, not all-or-nothing."
**Impacts:** Plan 02 deliverable structure, 3.1c architecture
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Framework Validity):** Withstands scrutiny. For `exploit_path_construction` and `arbitration_quality`, heuristic scores DEFAULT-30 — so any LLM score is "adds signal" by construction. The matrix should call this out explicitly (see P2-IMP-15). Strengthens the case for per-dimension resolution.

---

### P2-IMP-11: Agent Teams preference is wrong for Plan 02 — simple single-prompt scoring should use claude -p
**Target:** CONTEXT
**What:** Plan 02's core LLM operation is: fill REASONING_PROMPT_TEMPLATE, send to LLM, parse JSON response. Stateless single-prompt with no multi-turn context. The CONTEXT has "Agent Teams preferred, fall back to claude -p if simple enough." This IS simple enough. Running through Agent Teams conflates "does the rubric work?" with "does Agent Teams work for scoring?" — two separate questions.
**Why:** A test of rubric quality should not have orchestration quality as a confounding variable. The current decision locks in Agent Teams without distinguishing "tasks where coordination adds value" vs "tasks where coordination introduces noise."
**How:**
1. In `<decisions>` Agent Teams section: "Exception: stateless single-prompt tasks where the question is 'does this rubric produce informative scores?' use `claude -p --output-format json`. Orchestration overhead must not be a confounding variable."
2. Plan 02 method: "Use `claude -p --output-format json` for all scoring calls. Agent Teams deferred to 3.1c where orchestration IS the thing being tested."
3. Remove "Agent Teams vs claude -p for evaluation" from `<research_needs>`. Resolved: "For Plan 02: claude -p. Question reopened in 3.1c."
4. Keep Agent Teams as default for tasks where coordination genuinely matters.
**Impacts:** Plan 02 execution speed, research_needs reduction
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Experiment Design):** The core insight — rubric quality test should not have orchestration as confounding variable — is a valid experimental design principle. The enhanced How adds the distinction at the decisions level, preventing the same conflation in Plan 03.

---

### P2-IMP-12: Security reasoning follows attack-chain logic, not general reasoning moves — rubric style matters
**Target:** CONTEXT
**What:** Existing dimensions are structurally generic (graph_utilization, evidence_quality, reasoning_depth). An agent could score 80 on "reasoning_depth" — proxy: `len(set(tool_sequence)) * 20 + 30` (line 386-390) — while producing a chain that fails to trace data flow from user input to exploitable state. The heuristic proxy is pure behavioral count with no semantic content.
**Why:** This is an empirical question. The two-variant test produces evidence about rubric form sensitivity before 3.1c commits. If scores diverge significantly between generic and security-specific rubric on the same transcript, 3.1c should use security-specific. If they converge, generic is cheaper.
**How:**
1. Plan 02 rubric design task: "For `evidence_quality` (richest heuristic handler), write TWO rubric variants: (a) generic form, (b) security-chain form specifying data flow tracing, guard identification, exploit scenario construction. Test both on identical transcripts."
2. Success criterion: "If score divergence between (a) and (b) exceeds 15 points on >= 2 transcripts, security-specific rubric is recommended for 3.1c."
3. Restrict two-variant test to one dimension for sprint scope. Adds ~3 extra LLM calls, not a session.
4. In `<domain>`: "Rubric style recommendation (generic vs security-chain) is a Plan 02 deliverable."
**Impacts:** Plan 02 rubric design, 3.1c evaluation dimensions
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** creative-structural
**Status:** implemented
**Adversarial note (Framework Validity):** Original is directionally correct but too expansive ("at least one dimension" risks all dimensions). Scoped to one dimension (evidence_quality) with concrete 15-point divergence threshold so the recommendation is falsifiable, not subjective.

---

### P2-IMP-13: `{observed}` in the prompt template is undefined — determines whether LLM evaluation CAN outperform heuristic
**Target:** CONTEXT
**What:** Template takes `{observed}` but no code path populates it. Heuristic uses parsed extracts (tool_sequence, bskg_queries, response_text). If `{observed}` receives the same parsed extracts, LLM evaluation is redundant by construction. If it receives the 10K+ raw transcript, it blows the 6K token budget. Must be designed as a structured middle ground.
**Why:** Concrete failure: Plan 02 fills `{observed}` with `str(tool_sequence)` — LLM scores tool diversity, same as heuristic. Produces perfect agreement (false go) for wrong reason.
**How:**
1. Add to Plan 02 tasks: "Define `{observed}` spec. Minimum: BSKG queries with results (not just counts), key reasoning excerpts, evidence citations. Max 4K tokens."
2. Decision: "`{observed}` must contain info the heuristic CANNOT access. If identical, LLM evaluation is redundant by construction."
**Impacts:** Plan 02 wiring, determines if LLM CAN outperform heuristic
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Framework Validity):** Most operationally consequential item. The `{expected}` field also has no population path — see P2-ADV-2-02. The rubric is stored nowhere. Plan 02 must define BOTH what goes in `{expected}` AND `{observed}` before the first call can produce interpretable results.

---

### P2-IMP-14: Assumption 3 is confirmed false — calibration transcripts deleted, not "needs verification"
**Target:** CONTEXT
**What:** Assumption 3 states transcripts "exist and are scoreable" with "location needs verification." Confirmed empty (`.gitkeep` only). Plan 02's entire comparison model depends on having calibration anchors. With no transcripts, Plan 02 must generate anchor transcripts from scratch — designing what "good" vs "mediocre" vs "bad" reasoning looks like for security analysis, then crafting or capturing them. This is non-trivial and should be called out as a session-cost driver.
**Why:** Anchor design is where the "80 LOC / 1 session" estimate most visibly breaks down. The anchor design decision is also a hidden dependency for Plan 03: adversarial transcripts are compared against the same anchors.
**How:**
1. Rewrite Assumption 3: "Calibration transcripts DO NOT exist. `.vrs/observations/calibration/` is empty. Plan 02 must generate its own anchor transcripts."
2. Add to Plan 02 deliverables, listed first: "Anchor generation: design 3 anchor transcripts (good/mediocre/bad) matching the security reasoning task. Good = graph-first, TP identified with citation. Bad = no graph queries, hallucinated finding. Mediocre = graph queries but weak evidence chain."
3. Move transcript location from `<research_needs>` to resolved.
4. Cost note: "Anchor generation is a human-judgment task. Budget 1-2 hours of focused work before scoring calls can begin."
5. Cross-reference P2-IMP-16's LOC realism item.
**Impacts:** Assumption 3 accuracy, research_needs reduction, Plan 02 first deliverable
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Measurement Foundation):** Original corrects factual error but loses the implication: anchor design is creative and judgment-intensive work that cannot be scripted. It is the Plan 02 task most likely to cause session blocking.

---

### P2-IMP-15: `exploit_path_construction` and 4+ dimensions silently score 30/100 — Plan 02 comparison contaminated
**Target:** CONTEXT
**What:** `_heuristic_dimension_score` (lines 359-443) matches dimension names by substring. `exploit_path_construction` from `agent-vrs-attacker.yaml` matches NONE — receives default 30. Same for `arbitration_quality`, `evidence_weighing`, `investigation_depth`. The contamination is directional: on default-30 dimensions, any LLM score above 30 produces false "LLM adds signal." Any below 30 produces false "LLM agrees with heuristic." Neither is interpretable.
**Why:** Exclusion alone produces a comparison matrix covering only 4 of 5 attacker dimensions. The coverage gap is itself a finding: "heuristic has no coverage of security-specific dimensions." Plan 02 should report this. If only tested on dimensions with real handlers, the go/no-go is underconfident.
**How:**
1. Plan 02 step 1: "Audit dimension coverage. For each dimension in all 10 evaluation contracts, classify: {has_real_heuristic_handler | default_30}. Output: coverage table. Expected: ~30% default-30."
2. Reframe comparison: "Primary: dimensions with real handlers (LLM vs heuristic). Secondary: default-30 dimensions (LLM standalone, no comparison baseline)."
3. Deliverable adjustment: "Report separately: (a) LLM vs heuristic agreement on covered dimensions (Spearman rho), (b) LLM scores on uncovered dimensions (standalone value assessment). Go decision requires (a). (b) is additive."
4. Flag for 3.1c: "Security-specific dimensions have NO heuristic baseline. 3.1c must either build heuristics or accept LLM-only scoring."
**Impacts:** Plan 02 comparison validity, IMP-11 Spearman rho, IMP-12 divergence hypotheses
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Measurement Foundation):** Original correctly identifies contamination. Enhancement makes two-tier reporting explicit and calls out 3.1c implication: if heuristic never covered security-specific dimensions, "LLM adds signal" is predetermined on those dimensions. Different claim with different implications for 3.1c investment.

---

### P2-IMP-16: Plan 02's ~80 LOC estimate is unrealistic — honest scoping is 1-1.5 sessions
**Target:** CONTEXT
**What:** Plan 02's mandatory work after Pass 1+2: rubric write + freeze (ADV-201, CSC-02), `{observed}` spec (P2-IMP-13), dimension audit for default-30 coverage gaps (P2-IMP-15), anchor generation (IMP-10), scoring calls (minimum 6), calibration chain logging (IMP-17), divergence hypotheses (IMP-12), Spearman rho (IMP-11). Estimated at 1 session minimum. Stretch: rubric style variants (P2-IMP-12), persona stability (IMP-13, 18 calls). Total ~0.5 session additional.
**Why:** An unrealistic LOC estimate signals scope not reconciled across passes. P1-ADV-501 set the phase at 5–7 sessions. P2-IMP-07 added Session 0. If Plan 02 is 1.5 sessions (vs ~0.5 implied by "80 LOC"), remaining plans must absorb the difference.
**How:**
1. Replace "~80 LOC script" with session estimate: "Core Plan 02 = 1 session. Stretch = 0.5 additional session."
2. Define MANDATORY items: rubric write + freeze, `{observed}` spec, dimension audit, anchor generation, 6 scoring calls, calibration chain logging, divergence hypotheses, Spearman rho.
3. Define STRETCH items: rubric style variants (P2-IMP-12), persona stability (IMP-13, 18 calls).
4. Budget update: "Session 0 (1) + Plan 01 (1) + Plan 02 (1-1.5) + Plan 03/04 merged (1.5–2) + Plan 05 (0.5) = 5–6 sessions. Within 7-session ceiling IF stretch items truly deferred."
5. In `<decisions>`: "Stretch items require explicit go-ahead after core Plan 02 completes."
**Impacts:** Plan 02 scope estimate, ADV-501 budget
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Scope Discipline):** "1-1.5 sessions" without specifying mandatory vs stretch allows scope creep during execution. The two-tier list freezes the decision now, not at execution time.

---

### P2-IMP-17: "Goodhart risk" is a category error — the heuristic was DESIGNED as a disposable proxy
**Target:** CONTEXT
**What:** Plan 03's stated purpose — "Quantify Goodhart risk" — tests the wrong property. The heuristic is explicitly temporary infrastructure. The experiment should answer: "What is the VALIDITY COEFFICIENT — does it rank transcripts in an order that correlates with actual reasoning quality?" High validity = useful cheap filter despite gameability. Low validity = noise regardless of gameability. The Goodhart framing assumes the heuristic is being treated as the real measure; the validity coefficient framing asks whether it is even a useful proxy.
**Why:** Goodhart risk is a concern when an agent optimizes TOWARD the proxy. No agent is optimizing toward heuristic scores. The actual risk is misleading DIAGNOSIS — marking bad transcripts as good not because anything optimized for it, but because the heuristic lacks validity. That is a validity problem, not Goodhart.
**How:**
1. See P2-ADV-2-01 for replacement experiment design.
**Impacts:** Plan 03 reframed. 3.1c receives validity coefficient instead of binary Goodhart finding.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 02
**Classification:** creative-structural
**Status:** reframed
**Adversarial note (Framework Validity):** The REFRAME is necessary rather than ENHANCE because the Goodhart framing targets the wrong property entirely. Measuring gameability of a proxy nobody is gaming produces predictable "yes, gameable" that adds no information. Replaced by P2-ADV-2-01.

---

### P2-IMP-18: Plans 03 and 04 should merge — same corpus, same technique, same customer
**Target:** CONTEXT
**What:** Plans 03 and 04 should merge into a single "Evaluator Assessment" experiment. Plan 04's 65-FP taxonomy classification becomes Phase 0 of merged Plan 03 and can run immediately (no blocking dependency on Plans 01–02). Taxonomy results directly inform adversarial transcript design (P2-IMP-22). Eliminates one inter-plan waiting slot and produces more focused transcripts.
**Why:** The separation was designed when Plan 03 was a simple 5-archetype exercise and Plan 04 its own experiment. After Pass 1 expansions, Plan 03 already needs Plan 04's output. The plans have converged in practice.
**How:**
1. Rename: "Plan 03/04: Evaluator Assessment (Taxonomy + Adversarial Matrix)."
2. Phase 0 (taxonomy): classify 65 FPs using ACTION-oriented prompt (per P2-IMP-19 if accepted), tag fix cost. Runs immediately.
3. Phase 1 (adversarial generation): one transcript per taxonomy category (per P2-IMP-22). Min 3, max 8. LLM-Flatterer mandatory.
4. Preserve ADV-301 scope gate: "Phase 0 = mandatory. Phase 1 = mandatory. EST = stretch. Cross-model = stretch. Inadvertent Goodhart = removed (P2-IMP-21)."
5. Mark Plan 04 as "MERGED into Plan 03" with forward reference.
6. "Phase 0 is NOT a new pre-experiment — it IS an experiment. If LLM produces < 2 categories from 65 FPs, that's a finding (degenerate corpus)."
7. Update Plan 05 dependency: "Plans 01, merged-Plan-03/04."
**Impacts:** Plans 03+04 merge, Plan 05 dependency changes, session budget
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Scope Discipline):** Merge saves ~1 session AND produces better experiments. Risk: "Phase 0" sounds small but is a full LLM analysis on 65 FPs. The How makes Phase 0 a named deliverable with its own timebox. Conflict: P2-IMP-19 (action taxonomy) affects Phase 0 prompt design. P2-IMP-22 (data-driven count) only coherent if merge accepted.

---

### P2-IMP-19: Plan 04's taxonomy classifies detection system behavior — 3.1f needs IMPROVEMENT ACTIONS instead
**Target:** CONTEXT
**What:** The improvement is directionally correct but proposes premature optimization. Grouping 65 FPs "by what fix resolves them" requires the LLM to simultaneously discover categories AND estimate fix strategies AND assign LOC costs — three inference steps in one prompt. This is not categorization; it is estimation masquerading as categorization. The right framing is two-pass: undirected discovery first, action mapping second.
**Why:** Single-pass "improvement action" framing biases toward fix-obvious clusters and misses failure modes where the fix is unknown. A discovery task should not be steered by what the output consumer wants.
**How:**
1. See P2-ADV-4-01 for replacement two-pass taxonomy design.
**Impacts:** Plan 04 deliverable reframed, 3.1f receives both descriptive and prescriptive taxonomy
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** creative-structural
**Status:** reframed
**Adversarial note (Experiment Design):** Replacing "failure categories" with "improvement action categories" as the single LLM prompt creates confirmation bias toward fix-visible failures. FPs where fix is "unknown" or "architectural" will be under-represented. Replaced by P2-ADV-4-01.

---

### P2-IMP-20: Gameability matrix "catches" criterion needs explanation quality check, not just low scores
**Target:** CONTEXT
**What:** P1-IMP-23 success criterion: "LLM-score < 70 on >= 4 of 7+ archetypes where heuristic >= 70." But scoring low is necessary, not sufficient — the LLM must score low FOR THE RIGHT REASON. A harsh LLM that scores everything low "catches" all adversarial transcripts by this criterion.
**Why:** Concrete failure: LLM scores "keyword stuffer" at 40 (pass!) with explanation "reasoning lacked depth" — generic criticism unrelated to actual gaming mechanism.
**How:**
1. Add matrix column: "LLM identifies gaming mechanism: yes/partial/no."
2. Pre-specify what LLM explanation should identify per archetype.
3. Amend go criterion: "LLM-score < 70 AND identifies mechanism on >= 3 of 6 mandatory archetypes."
4. Zero-cost addition — LLM already produces explanations.
**Impacts:** Plan 03 go/no-go strengthened
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** Plan 02
**Classification:** structural
**Status:** implemented
**Adversarial note (Experiment Design):** Withstands the lens. Score+explanation check is the standard meta-evaluation pattern. One note: pre-specifying expected mechanisms per archetype requires rubric-writing work that should be a Plan 03 task, not a CONTEXT decision.

---

### P2-IMP-21: Inadvertent Goodhart measurement is impossible with zero real transcripts — defer to 3.1c
**Target:** CONTEXT
**What:** P1-IMP-25 proposes measuring whether real agent transcripts have drifted toward high scores without quality. Problem: ZERO real transcripts exist. Calibration transcripts deleted. REASONING_PROMPT_TEMPLATE never called. Most likely outcome: "unquantified — known gap."
**Why:** Carrying scope for a measurement that almost certainly produces no data is the scope inflation P1-ADV-501 warns about.
**How:**
1. Move to `<deferred>`: "Inadvertent Goodhart — requires real transcript corpus. Deferred to 3.1c."
2. Remove from Plan 03 scope entirely.
3. Remove from Assumption 4.
**Impacts:** Plan 03 scope reduced, ADV-501 budget gains slack
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Scope Discipline):** Deferral is not "avoiding the question" — it is correctly scoped. Inadvertent Goodhart requires a corpus of real transcripts under production conditions, which 3.1c will generate. Also removes the downstream "cross-model validation deferred to 3.1c if inadvertent HIGH" clause from P1-IMP-25.

---

### P2-IMP-22: Adversarial transcript count should be data-driven — one per discovered failure mode, not pre-specified
**Target:** CONTEXT
**What:** Pre-specifying adversarial transcript count (first 5, then 8+) is arbitrary. If Plan 04 taxonomy produces N failure categories, producing one per category aligns coverage with failure landscape.
**Why:** Data-driven count is correct but depends on P2-IMP-18 (merge). If merge rejected and Plans 03+04 sequential, Plan 03 runs BEFORE taxonomy is available.
**How:**
1. Conditional on P2-IMP-18 merge: "Count = taxonomy category count. Min 3 (below 3 = taxonomy collapsed, investigate), max 8. LLM-Flatterer mandatory regardless."
2. Conditional on merge rejection: "Plan 03 uses 5 pre-specified archetypes (name-dropper, bash-first, query-spammer, keyword-stuffer, perfect-faker). Plan 04 post-hoc annotates which maps to which category. Mismatches = coverage gaps."
3. Make dependency explicit in Plan 03: "Transcript count strategy depends on merge decision."
4. Replace min-3 floor with: "If taxonomy < 3 categories, flag as taxonomy collapse before proceeding."
**Impacts:** Plan 03 transcript count data-driven, matrix aligned with taxonomy
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 04 taxonomy
**Classification:** structural
**Status:** implemented
**Adversarial note (Experiment Design):** Assumes P2-IMP-18 merge is accepted. Without merge, data-driven count creates circular dependency. The enhanced How provides both paths so the improvement is not orphaned.

---

### P2-IMP-23: P1-CSC-03's mixed-outcome routing over-engineers — human judgment already handles this
**Target:** CONTEXT
**What:** P1-CSC-03 pre-specifies routing rules for mixed matrix outcomes using a Haiku/hand-crafted distinction that (a) doesn't exist yet and (b) disappears if P2-IMP-18 merge accepted. But removing all pre-registration violates IMP-12 pre-registration principle and creates post-hoc interpretation risk.
**Why:** Pre-registration is a scope discipline tool, not inflation. The problem with P1-CSC-03 is its rules reference a model-family distinction designed before experiments ran. Fix: pre-register simpler, model-agnostic interpretation rules.
**How:**
1. Replace CSC-03 routing: "Pre-register three thresholds before running Plan 03: (a) >= 4/N caught with mechanism explanation: go; (b) 2–3/N: conditional — extend; (c) <= 1/N: no-go."
2. Remove model-family-specific routing (Haiku vs hand-crafted).
3. Presentation format: "human receives matrix + pre-registered thresholds + recommendation."
4. In `<decisions>`: "Matrix interpretation thresholds are pre-registered. Human approves against thresholds, not ad-hoc judgment."
5. If P2-IMP-18 merge accepted: update thresholds to reference taxonomy categories.
**Impacts:** Plan 03 simplified, P1-CSC-03 addressed
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** implemented
**Adversarial note (Scope Discipline):** Original remedy ("human judgment") is correct in principle but creates execution risk: the reviewer is the same person who designed the experiments, under sprint pressure. Pre-registration costs 5 lines of text and eliminates confirmation bias.

---

### P2-IMP-24: Assumption 5 is a testable hypothesis, not an assumption — framing biases the experiment
**Target:** CONTEXT
**What:** Assumption 5: "LLM failure taxonomy will differ from hand-designed categories." This is the EXPERIMENT OUTCOME, not a precondition. Framing as assumption biases toward novelty — makes matching categories look like failure.
**Why:** If LLM discovers categories matching {test_bug, llm_variance, transient, genuine_gap}, that's POSITIVE (hand-designed were correct!) not failure.
**How:**
1. Move to Plan 04 hypothesis: "Hypothesis: categories will differ. If match: validated. If differ: use discovered."
2. Success criterion: "produces categories grounded in data" — not "produces different categories."
3. LLM prompt: do NOT mention hand-designed categories. Compare AFTER discovery.
**Impacts:** Plan 04 becomes hypothesis-testing, removes confirmation bias
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** creative-structural
**Status:** implemented
**Adversarial note (Framework Validity):** Confirmed on both diagnosis and fix. Critical addition: "do NOT mention hand-designed categories in the LLM prompt, compare AFTER discovery" is the operational guarantee preventing confirmation bias.

---

## Adversarial CREATE Items

### P2-ADV-1-01: Builder diagnostic protocol — verify BSKG property values before any YAML fix
**Target:** CONTEXT
**Source:** Adversarial review (Measurement Foundation) — mandatory REFRAME replacement for P2-IMP-05
**Status:** implemented
**Adversarial note (ADV Validation):** Confirmed — builder diagnostic is a sound prerequisite for Plan 01. Validates that BSKG property values are correct before YAML tuning proceeds.

**What:** Add a Plan 01 diagnostic protocol as a Session 0 prerequisite: before any YAML edit to access-tierb-001, query the BSKG directly for `has_access_gate`, `state_mutability`, `is_constructor`, and `has_external_calls` property values on three known-guarded functions (SelfiePool.emergencyExit with onlyGovernance, SideEntrance.withdraw with balance check, ReentrancyWithGuard.withdraw with nonReentrant). Compare actual vs expected. Document: "Which `none:` properties compute correctly? Which do not?"

**Why:** Plan 01 assumes YAML tuning is the fix path. If `has_access_gate` is not computed correctly, any additional `none:` conditions relying on builder-computed properties will silently fail. The before/after measurement will show no delta, and the correct interpretation is "builder bug" not "YAML approach is wrong" — without diagnostic, interpretation is ambiguous.

**How:**
1. Add to Plan 01 as hard prerequisite: "Diagnostic: run `alphaswarm query` or inspect graph JSON for property values on 3 known-guarded functions. Expected: `has_access_gate=true`. If differs, bug is in builder."
2. If builder bug: "Plan 01 scope changes to builder fix + regression test. LOC ~100-200. Confidence drops to MEDIUM. Human approval required."
3. If builder correct but pattern fires anyway: "Bug is in pattern engine's `tier_a_required` logic."
4. Only if all properties compute correctly: "proceed with YAML tuning as originally scoped."

**Cross-references:** P2-IMP-05 (reframed), P1-IMP-01 (tier_a_required semantics — complementary)
**Adversarial note:** P1-IMP-01 asks what happens logically under tag-absence; this asks what the builder actually computes. Both converge on Session 0 diagnostic.
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Classification:** structural

---

### P2-ADV-1-02: Session 0 measurement cascade — six prerequisites collectively define a real work session
**Target:** CONTEXT
**Source:** Adversarial review (Measurement Foundation) — cross-item synthesis
**Status:** implemented
**Adversarial note (ADV Validation):** Withstands scrutiny. Six named prerequisites + concrete checklist prevents scope migration.

**What:** The six measurement foundation items collectively reveal: every measurement dimension in Plans 01 and 02 has at least one broken prerequisite. Together: (a) baseline discrepancy (IMP-01), (b) 7-contract regression suite (IMP-02), (c) BSKG property diagnostic (IMP-05/ADV-1-01), (d) counting policy lock (IMP-06), (e) anchor transcript generation (IMP-14), (f) heuristic dimension audit (IMP-15). None individually large, but together: a session that must complete before Plans 01-02 can generate valid measurements.

**Why:** If six prerequisites together require a full session (4-6 hours), and Plans 01-05 each require a session, the sprint is "1 calibration + 5 execution = 6-8 sessions total." Still a sprint — but Session 0 is a real cost, not a warmup.

**How:**
1. `<decisions>`: "Session 0 is a real work session. Scope: baseline re-run, property diagnostic, counting policy lock, anchor design, dimension audit. Estimated: 1 session."
2. Plans 01 and 02 preconditions: "Requires Session 0 complete."
3. Session 0 checklist in `.vrs/experiments/session-0-checklist.md`.
4. This does NOT extend the sprint — makes true structure explicit.

**Cross-references:** P2-IMP-01, 02, 05, 06, 14, 15
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Classification:** structural

---

### P2-ADV-2-01: Heuristic validity coefficient experiment design — replace Goodhart framing
**Target:** CONTEXT
**Source:** Adversarial review (Framework Validity) — mandatory REFRAME replacement for P2-IMP-17
**Status:** implemented
**Adversarial note (ADV Validation):** Correctly implements REFRAME. Spearman coefficient is standard validation. Decision rule justified.

**What:** Replace Plan 03's Goodhart risk framing with validity coefficient measurement. After Plan 02 produces LLM scores for 6 transcripts, compute Spearman rank correlation between heuristic and LLM scores per dimension. Report: (a) correlation coefficient per dimension, (b) adversarial divergence (heuristic score under gaming vs LLM score) as secondary. Decision rule: validity >= 0.6 on >= 2 dimensions = keep as cheap pre-filter; < 0.6 across all = discard; mixed = keep only high-correlation dimensions.

**Why:** Without replacement, P2-IMP-17's REFRAME leaves Plan 03 with no primary deliverable. The validity coefficient is actionable where gameability is not: 3.1c can use "heuristic has validity 0.7 on evidence_quality, 0.3 on reasoning_depth" for per-dimension evaluator selection.

**How:**
1. Plan 03 deliverables: "Primary: Heuristic validity coefficient — Spearman rho per dimension. Secondary: Adversarial divergence."
2. `<domain>`: Replace "Quantified Goodhart risk" with "Heuristic evaluator validity assessment."
3. Decision rule in `<decisions>`: "Heuristic survives where validity >= 0.6. Below = noise, remove."
4. Sequential dependency: REQUIRES Plan 02 LLM scores.

**Cross-references:** P2-IMP-17 (reframed), P2-IMP-10, P2-IMP-15
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Classification:** structural

---

### P2-ADV-2-02: Plan 02's `{expected}` field has no rubric population path — same gap as `{observed}`
**Target:** CONTEXT
**Source:** Adversarial review (Framework Validity) — cross-item interaction between P2-IMP-13 and P2-IMP-12
**Status:** implemented
**Adversarial note (ADV Validation):** Gap correctly identified. Enhanced with storage format (inline script), content structure (scoring bands), and wiring path ({expected} population).

**What:** P2-IMP-13 identifies `{observed}` is unpopulated. `{expected}` — the rubric content field — also has no population path. The evaluation contract `reasoning_dimensions` stores dimension NAMES but no rubric TEXT specifying what good behavior looks like. Plan 02 must define rubric text for each dimension before the first LLM call. Writing rubrics IS the primary intellectual work of Plan 02, currently invisible in the plan description.

**Why:** The absence of rubric text is structurally more limiting than absent observed data. You can extract observed data mechanically. You cannot mechanically generate rubric text — it requires judgment about what constitutes good security reasoning.

**How:**
1. Plan 02 task: write {expected} as rubric text per dimension. Form: inline text in scoring script (not separate artifact). Content per dimension: describe scores of 90+, 50-70, below 30 with security-reasoning specifics. Example: evidence_quality at 90+ = "finds key dataflow fact and cites node ID"; at 50-70 = "names a fact but citation weak"; below 30 = "generic claim."
2. Time: 30-60 min per dimension for first draft.
3. Integration: rubric text populates {expected} field in template before first LLM call.
4. Decision: "Rubric text is primary intellectual deliverable. Infrastructure is secondary."

**Cross-references:** P2-IMP-13, P2-IMP-12
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Classification:** structural

---

### P2-ADV-3-01: Session 0 needs its own scope ceiling — scope migrates not reduces
**Target:** CONTEXT
**Source:** Adversarial review (Scope Discipline) — cross-item gap
**Status:** implemented
**Adversarial note (ADV Validation):** Three-task ceiling concrete and bounded. Explicit exclusions prevent scope drift. Cross-references integrate multiple lenses.

**What:** P2-IMP-07, P1-SYN-03, P1-ADV-201, P1-ADV-102, P1-ADV-202, and CONTEXT's Session 0 pattern collectively assign: fresh pipeline baseline, rubric write + freeze, real transcript capture, EVMbench scan, counting methodology lock, TP enumeration, cost instrumentation. This is 2–3 sessions disguised as "setup." No ceiling or bounded checklist exists.

**Why:** The phase was inserted to prevent v5.0 anti-pattern (infrastructure before experiments). Pass 1 correctly diagnosed plan inflation. But they relocated scope to Session 0 rather than eliminating it. The experiment-before-infrastructure principle must apply to Session 0 itself.

**How:**
1. Add `<session_zero>` section to CONTEXT with EXACTLY: "(a) Run fresh pipeline on 7 contracts — record FP/TP counts (30 min). (b) Write rubric v1.0 for reasoning_depth and evidence_quality (20 min). (c) Optional: EVMbench scan (30 min). STOP."
2. Explicitly exclude: EVMbench full methodology, persona stability setup, multi-variant rubric, cross-contract TP enumeration beyond (a).
3. `<decisions>`: "Session 0 ceiling: 1 session, 3 bounded tasks. Additional setup requires a plan slot."
4. Real transcript capture (P1-ADV-202) is NOT Session 0 — it requires running a real agent workflow, which IS an experiment. Belongs in Plan 02.

**Cross-references:** P2-IMP-07, P1-SYN-03, P1-ADV-102, P1-ADV-201, P1-ADV-202, P1-ADV-501
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Classification:** structural

---

### P2-ADV-3-02: After all improvements, is this still a sprint? — total session budget recount
**Target:** CONTEXT
**Source:** Adversarial review (Scope Discipline) — binding lens question
**Status:** implemented
**Adversarial note (ADV Validation):** Withstands scrutiny on core claim. Minor language tension with P2-ADV-1-02 ("still sprint" vs "research project"). Align to "5-6 session empirical research phase" pre-merge.

**What:** Current count: Session 0 (1), Plan 01 (1), Plan 02 core (1) + stretch (0.5), merged Plan 03/04 (1.5–2), Plan 05 (0.5). Total: 5–6 core, 5.5–7 with stretch. Within P1-ADV-501's 7-session ceiling — but only if Session 0 stays bounded, all stretch is truly deferred, inadvertent Goodhart deferral holds, and routing simplification holds. Five sequential preconditions.

**Why:** A sprint requiring 5 preconditions to stay within budget is a well-managed research project, not a sprint. The CONTEXT should make this explicit so the executor starts with accurate expectations.

**How:**
1. `<decisions>`: "Budget recount: Session 0 (1) + Plans 01–05 core (4.5) = 5.5 sessions. This is a 5–6 session research project. The 'empirical sprint' label is retained for brevity but the time commitment is a research phase."
2. Option A: keep 5.5 estimate, update domain to acknowledge research-phase scope.
3. Option B: cut scope to restore sprint character — Plan 05 collapses into Plan 03/04 outputs.
4. Require human decision on A vs B before execution.

**Cross-references:** P1-ADV-501, P2-IMP-16, P2-IMP-07, P2-IMP-18, P2-IMP-21
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Classification:** structural

---

### P2-ADV-4-01: Two-pass taxonomy design as concrete Plan 04 sub-task
**Target:** CONTEXT
**Source:** Adversarial review (Experiment Design) — mandatory REFRAME replacement for P2-IMP-19
**Status:** implemented
**Adversarial note (ADV Validation):** Withstands scrutiny. Two-pass prevents frame bias. Minor enhancement opportunity: clarify Pass 1→2 data flow.

**What:** Plan 04 should use two-pass LLM taxonomy: Pass 1 undirected discovery (cluster FPs by natural similarity, no fix framing), Pass 2 action mapping per cluster (YAML-fixable, label-dependency, architectural, unknown). This produces both descriptive taxonomy for 3.1c AND prescriptive taxonomy for 3.1f.

**Why:** Single-pass action framing biases toward fix-obvious clusters. FPs where fix is unknown will be under-represented. Discovery task should not be steered by consumer needs — discover first, map second.

**How:**
1. Plan 04 description: "Two-pass taxonomy. Pass 1: undirected clustering (no fix framing). Pass 2: action mapping per cluster. Outputs: descriptive_clusters.json + action_map.json."
2. Deliverables: "(a) descriptive taxonomy for 3.1c schema design, (b) action-mapped taxonomy for 3.1f routing. Kept separate to prevent frame collapse."
3. `<decisions>`: "Plan 04 prompt is two-pass by construction. Single-pass is anti-pattern here."

**Cross-references:** P2-IMP-19 (reframed), P2-IMP-18 (if merged, Pass 1 informs adversarial design), P2-IMP-22
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Classification:** creative-structural

---

### P2-ADV-4-02: Explanation quality pre-specification needs a concrete task slot in Plan 03
**Target:** CONTEXT
**Source:** Adversarial review (Experiment Design) — from P2-IMP-20 interaction
**Status:** implemented
**Adversarial note (ADV Validation):** Pre-specification principle correct. Enhanced with conditional paths for merge/no-merge, storage format, and Plan 03 sequencing.

**What:** P2-IMP-20 requires pre-specifying expected LLM explanations per archetype before running adversarial transcripts. This is non-trivial design work missing from Plan 03's deliverables and LOC estimate.

**Why:** If pre-specification happens during execution, expected mechanisms will be written after seeing LLM outputs — defeating the purpose. Must be written before transcripts are crafted.

**How:**
1. Plan 03 sequencing: write explanation specs BEFORE transcript crafting.
   - If P2-IMP-18 merge ACCEPTED: for each taxonomy category discovered in Phase 0, write expected LLM explanation. Stored in markdown table.
   - If merge REJECTED: for each pre-specified archetype (name-dropper, bash-first, query-spammer, keyword-stuffer, perfect-faker), write expected explanation. Stored in markdown table.
2. Content per archetype/category: "LLM should identify mechanism X." Example: for keyword-stuffer, expected = "LLM identifies repetition of security terms without semantic depth."
3. Purpose: evaluator uses this spec to score LLM explanation quality (P2-IMP-20).
4. Time: 10-15 min per archetype. Total: 30 LOC (markdown table + specs).
5. Task slot in Plan 03: "Pre-specification (before transcript design): 30 min."

**Cross-references:** P2-IMP-20, P2-IMP-22
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Classification:** structural

---

## Cross-Cutting Synthesis Items

### P2-SYN-01: Every experiment lacks pre-registered interpretation rules — post-hoc analysis risk is systemic
**Target:** CONTEXT
**What:** Five items across three different review groups independently identify the same structural gap: experiments define what to measure but not how to interpret results before running them. P2-IMP-03 (Experiment Design lens) shows Plan 01's binary answer is unfalsifiable. P2-IMP-10 (Framework Validity lens) shows Plan 02's go/no-go collapses mixed outcomes. P2-IMP-20 (Experiment Design lens) shows Plan 03's "catches" criterion lacks explanation quality check. P2-IMP-23 (Scope Discipline lens) shows Plan 03's routing rules are over-engineered but removing pre-registration is worse. P2-IMP-24 (Framework Validity lens) shows Plan 04's assumption pre-judges outcome. Each item fixes one experiment. None addresses the systemic pattern: the phase has no pre-registration discipline as a design principle.
**Why:** Fixing each experiment's interpretation rules individually risks inconsistent rigor levels across plans and creates no guard against the same gap appearing in future experiments (e.g., if Plan 05's schema extraction criteria are also post-hoc). A single decision establishing pre-registration as a phase-wide principle prevents the pattern from recurring and makes individual fixes coherent.
**How:**
1. Add to `<decisions>`: "Pre-registration principle: every experiment must specify, BEFORE execution, (a) what constitutes success, (b) what constitutes failure, (c) what the ambiguous-middle interpretation rule is. These three items are written into the plan description, not discovered during analysis."
2. Add to Plan 05 (currently missing pre-registration): "Success: schemas capture >= 80% of observed data fields. Failure: schemas require fields no experiment produced data for. Ambiguous: schemas capture data but 'Unobserved Phenomena' list exceeds 5 items."
3. During merge, verify each plan description includes its pre-registered interpretation rules per the items that already address them (Plans 01-04).
**Impacts:** Plans 01-05 (all experiments)
**Components:** P2-IMP-03, P2-IMP-10, P2-IMP-20, P2-IMP-23, P2-IMP-24
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
**Adversarial note (ADV Validation):** Correctly identifies systemic pattern across 5 independent observations. Phase-wide principle prevents fragmented rigor.

---

### P2-SYN-02: Plan 02 has three unpopulated template inputs discovered across two review groups — requires a unified wiring task
**Target:** CONTEXT
**What:** Three items across Measurement Foundation and Framework Validity lenses independently discover that Plan 02's REASONING_PROMPT_TEMPLATE has no populated inputs: P2-IMP-13 (Framework Validity) finds `{observed}` is undefined, P2-ADV-2-02 (Framework Validity) finds `{expected}` has no rubric text, and P2-IMP-14 (Measurement Foundation) confirms calibration transcripts do not exist. Each proposes its own fix. But the three gaps are not independent — they form a single wiring problem: Plan 02 cannot make its first LLM call until all three are resolved, and the design choices interact (rubric text constrains what `{observed}` must contain; anchor transcript quality determines whether scores are interpretable). No item addresses the ordering dependency or the interaction.
**Why:** If these are resolved independently, the rubric might specify criteria that `{observed}` data cannot support, or anchor transcripts might not exercise the rubric's scoring bands. A single "Plan 02 wiring" task that resolves all three in sequence (rubric first, then observed spec informed by rubric, then anchors that exercise both) produces a coherent first LLM call.
**How:**
1. Add to Plan 02 deliverables as ordered sequence: "(1) Write rubric text per dimension (what scores 90+, 50-70, below 30) — this is `{expected}`. (2) Define `{observed}` spec: must contain info the heuristic cannot access, constrained by rubric requirements. (3) Design 3 anchor transcripts that exercise rubric scoring bands. These three are sequential — each constrains the next."
2. In `<decisions>`: "Plan 02 wiring order is rubric -> observed spec -> anchors. Parallel execution risks incoherent inputs."
**Impacts:** Plan 02
**Components:** P2-IMP-13, P2-IMP-14, P2-ADV-2-02
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)
**Adversarial note (ADV Validation):** Correctly identifies three gaps as one dependency chain. Ordered sequence (rubric→observed→anchors) logically sound.

---

## Cascade Gap Items

### P2-CSC-01: Plan 02 decoupled from 7-move validation leaves 3.1c with no empirical input on framework choice
**Target:** CONTEXT
**What:** P2-IMP-09 (enhanced) correctly decouples Plan 02's go/no-go from the 7-move reasoning decomposition, stating "7-move framework validity is a 3.1c design decision." But 3.1c's CONTEXT currently lists Plan 02's go/no-go as the input for its 7-move investment decision (3.1c Plans 07-12 build on this assumption). After P2-IMP-09, 3.1c receives "LLM can score ad-hoc dimensions" but has zero empirical input on whether the 7-move decomposition is valid. The gap: 3.1c must now design its own validation experiment for the 7-move framework, which is not currently in any 3.1c plan.
**Why:** Without this cascade note, 3.1c will proceed as if Plan 02 validated the 7-move approach (because the original framing said it would). The decoupling is correct but incomplete without updating 3.1c's expectations.
**How:**
1. Add to `<deferred>` or 3.1c handoff notes: "3.1c must design its own 7-move validation experiment. Plan 02 provides LLM-as-judge capability evidence, not framework validation. 3.1c Plans 07-12 should not assume 7-move is validated."
2. In `<domain>`, add to "What this phase does NOT deliver": "Validation of the 7-move reasoning decomposition (deferred to 3.1c)."
**Impacts:** 3.1c Plans 07-12
**Trigger:** P2-IMP-09
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)
**Adversarial note (ADV Validation):** Cascade is real. Decoupling correct but incomplete without updating 3.1c expectations.

---

### P2-CSC-02: Merged Plan 03/04 with degenerate taxonomy produces no adversarial transcripts — fallback path undefined
**Target:** CONTEXT
**What:** P2-IMP-18 (enhanced) merges Plans 03 and 04 so that taxonomy (Phase 0) drives adversarial transcript count (Phase 1). Step 6 says "If LLM produces < 2 categories from 65 FPs, that's a finding (degenerate corpus)." But if taxonomy collapses to < 2 categories, Phase 1 has no meaningful input: the data-driven transcript count (P2-IMP-22) would produce 1-2 transcripts, below the min-3 floor. The merged plan has no fallback path for this scenario — it flags the finding but does not specify what Phase 1 does next.
**Why:** The taxonomy collapse is not hypothetical. The 65 FPs are dominated by access-tierb-001 on DeFi contracts (P1 Taxonomy lens). If the LLM clusters by pattern rather than by failure mechanism, most FPs land in one cluster. Without a fallback, the merged plan stalls at Phase 0 with a "finding" but no path to Plan 03's primary deliverable (validity coefficient).
**How:**
1. Add to merged Plan 03/04: "Taxonomy collapse fallback: if < 3 categories, Phase 1 reverts to 5 pre-specified archetypes (name-dropper, bash-first, query-spammer, keyword-stuffer, perfect-faker). The taxonomy collapse itself is reported as a finding for 3.1c — 'corpus too narrow for data-driven adversarial design.'"
2. This is the same fallback as P2-IMP-22's conditional-on-merge-rejection path, applied to the within-merge degenerate case.
**Impacts:** Merged Plan 03/04
**Trigger:** P2-IMP-18
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)
**Adversarial note (ADV Validation):** Taxonomy collapse plausible given corpus constraints. Fallback preserves validity testing. "Report as finding" ensures 3.1c visibility.

---

## Convergence Assessment

**Structural:** 25 (includes creative-structural) — 17 IMP + 8 ADV-CREATE
**Creative-structural:** 6 IMP (P2-IMP-03, 04, 12, 17, 19, 24) + 1 ADV (P2-ADV-4-01)
**Cosmetic:** 1 (P2-IMP-08)
**Ratio:** 3.8% cosmetic (1/26 counted items)
**Signal:** ACTIVE — substantial structural findings remain
**Note:** Pass 2, convergence gate is INFORMATIONAL only (pass < 3)

---

## Post-Review Synthesis
**Items created:** P2-SYN-01, P2-SYN-02, P2-CSC-01, P2-CSC-02
**Key insight:** The phase's experiments share a systemic lack of pre-registered interpretation rules (5 items across 3 lenses converge on this), and Plan 02's template wiring problem is actually one sequential dependency chain (rubric -> observed -> anchors) that three independently-discovered gaps must resolve in order. The most consequential cascade is P2-IMP-09's 7-move decoupling, which leaves 3.1c without the validation input it currently expects.
