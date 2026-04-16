# Improvement Pass 12

**Pass:** 12
**Date:** 2026-02-19
**Prior passes read:** 1-11 (via IMPROVEMENT-DIGEST.md + IMPROVEMENT-P11.md active items)
**Areas analyzed:** Evaluation Framework (Plans 06, 07), Test Execution (Plans 09, 10, 11)
**Agent count:** 2 improvement agents, 4 adversarial reviewers, 1 synthesis agent
**Status:** complete

<!-- File-level status: in-progress | complete -->

## Pipeline Status

<!-- Auto-populated by workflows. Shows pending actions across ALL passes for this phase. -->

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 1 | 1 | P11-IMP-10 (Plan 02 transcripts) |
| Research | 0 | 5 | All resolved (2026-02-19) |
| Gaps | 0 | 0 | — |
| Merge-ready | 0 | 35 | All P12 items merged (2026-02-19) |
| Implemented | 15 | — | IMP-01,02,06,07,08,09,11,12 + ADV-1-01,2-01,3-01,4-01 + SYN-01 + CSC-01,02 |

**Pipeline:** [improve] done → [adversarial] done → [synthesis] done → [implement] ✓
**Next recommended:** All P12 items merged. /msd:plan-phase 3.1c or another /msd:improve-phase 3.1c

## Improvements

### P12-IMP-01: Existing Contracts Use Dimensions Not in Dimension Registry or Move-Type Enum
**Target:** CONTEXT
**Status:** implemented
**Verdict:** ENHANCE (Schema Integrity lens)
**What:** The 10 existing contracts + 4 templates collectively use 27 distinct dimension names. Of these, 19 are NOT in either the 7-move-type enum (HYPOTHESIS_FORMATION, QUERY_FORMULATION, RESULT_INTERPRETATION, EVIDENCE_INTEGRATION, CONTRADICTION_HANDLING, CONCLUSION_SYNTHESIS, SELF_CRITIQUE) or the 8 domain dimensions listed in CONTEXT.md's Dimension Registry decision. The domain dimension registry file (`contracts/dimension_registry.yaml`) referenced in CONTEXT.md does NOT EXIST on disk — there is no file to validate against. What exists is a prose list in CONTEXT.md.

Furthermore, the current schema (`evaluation_contract.schema.json`) sets `items: {type: string, minLength: 1}` for `reasoning_dimensions` — no enum constraint exists in the schema. Therefore, today's contracts already pass schema validation regardless of what dimensions they declare. The proposed Schema Hardening adds validation, but the mechanism for validating dimensions is unspecified: the CONTEXT says "Schema `pattern` or CI validation script" — these are two very different enforcement mechanisms with different failure modes.

The original improvement proposed expanding the domain dimension list from "~6-8" to "~15". The actual number of non-7-move-type dimensions in use across all 14 files is 27, not 15. The proposed list omits: `arbitration_quality`, `consensus_quality`, `creative_adversarial_thinking`, `evidence_weighing`, `hypothesis_testing`, `investigation_depth`, `review_thoroughness`, `task_completion`, `task_delegation`, `verdict_justification`, `verification_thoroughness`, `conclusion_support`.
**Why:** Three distinct failures converge:
1. The registry file does not exist — there is nothing to validate against.
2. The schema has no dimension enum constraint — validation would pass even after hardening unless a CI script is added.
3. The proposed dimension list (15 items) undercounts the actual dimension vocabulary (27 items) by 12 dimensions.
**How:**
1. Create `src/alphaswarm_sol/testing/evaluation/contracts/dimension_registry.yaml` as an actual file (not just a prose list in CONTEXT.md). Populate with all 27 dimensions currently in use. Format: `dimensions: [...]` YAML list.
2. In CONTEXT.md Dimension Registry section, update the prose description to reference the file as authoritative. Replace `~6-8` with the actual count. Note: the two namespaces (7-move enum in schema, domain dimensions in registry file) are the union that validation must accept.
3. Choose ONE enforcement mechanism and specify it concretely: either (a) add `enum` to schema `reasoning_dimensions.items` (simpler but requires schema update when new dimensions added) or (b) add a CI script `validate_dimensions.py` that loads the registry file and rejects unknown names (flexible but introduces a new artifact). Document which approach in CONTEXT.md under Schema Hardening.
4. In Plan 06 deliverables, replace "pre-flight step: run `validate_mapping_completeness()`" with a step that specifically creates the registry file and runs dimension validation against all 14 existing contracts before the atomic commit.
5. Plan 07's `DIMENSION_TO_MOVE_TYPES` must be sized to the full registry (27 domain dimensions + 7 move types). The current plan assumes "~6-8" dimensions — the actual number is 27 contract-specific dimensions that need mappings.
**Impacts:** Plan 06 Schema Hardening scope (registry file creation is now a deliverable). Plan 07 `DIMENSION_TO_MOVE_TYPES` map is ~3.5x larger than assumed.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Adversarial note (Schema Integrity):** The improvement correctly identifies the failure but systematically undercounts it. The proposed expansion to 15 dimensions would still leave 12 contract dimensions failing validation on day one. The dimension registry file doesn't exist at all — this is a CREATE gap, not an EXPAND gap. Additionally, if the migration script (IMP-02) inserts missing fields into contracts, it cannot insert dimensions — dimensions are workflow-specific and cannot have template defaults. This means dimension validation must PASS for existing contracts (registry must include them all), not be fixed by migration.

---

### P12-IMP-02: Schema Migration Matrix and Script for Atomic Commit
**Target:** CONTEXT
**Status:** implemented
**Verdict:** ENHANCE (Schema Integrity lens)
**What:** The current schema (`evaluation_contract.schema.json`) diverges from the Schema Hardening Field Manifest in 10 confirmed ways: `evaluation_config` is not in `required`; `evaluation_config` has no inner `required`; `additionalProperties: true` at top level; `metadata` has no `additionalProperties: false`; `hooks` field absent from schema entirely; `status` field absent; `coverage_axes` field absent; `evaluation_config.debate_enabled` absent; `evaluation_config.run_mode` absent; `debrief_wait_seconds` absent. The existing contracts further diverge: `agent-vrs-attacker.yaml` has no `evaluation_config`, no `hooks`, no `status`, and uses deprecated `metadata.evaluation_depth`.

No migration script or per-file checklist exists. The CONTEXT describes the commit as "atomic" but the only guidance is the Field Manifest table — a 14-row table with no mapping to individual files.
**Why:** An "atomic commit" with 15 coordinated edits (14 files + 1 schema) has one critical coordination risk: the migration script must NOT insert dimensions (workflow-specific, no valid default) but MUST insert `evaluation_config`, `hooks`, `status`, and `coverage_axes` with template defaults. These are asymmetric migration operations. A script that inserts all missing fields with template defaults will produce identical `hooks` arrays in Core investigation contracts and Standard stub contracts — which is wrong. Core investigation needs `[PreToolUse, PostToolUse, PostToolUseFailure, SubagentStart, SubagentStop, Stop, PreCompact, SessionEnd]`; Standard needs `[Stop, SessionEnd]`.

Additionally, `metadata.evaluation_depth` deprecation is not just "remove the field" — it is "copy the value to `evaluation_config.depth` if `evaluation_config` doesn't already have it." A script that removes the deprecated field without migrating the value will silently lose tier/depth information for the 7 contracts that use it.
**How:**
1. In Plan 06 deliverables, specify the Schema Migration Matrix as a literal table in CONTEXT.md (14 files × required fields, with current state: present/absent/needs-change). This table is the pre-commit checklist.
2. In Plan 06 deliverables, add migration script specification: `migrate_contracts.py` (~60 LOC) with THREE distinct operation types:
   - `insert_with_category_default(field, category_defaults_map)` — for `hooks` and `evaluation_config`, uses contract's `category` field to select correct defaults.
   - `migrate_deprecated(old_path, new_path)` — for `metadata.evaluation_depth` → `evaluation_config.depth`, only if `evaluation_config.depth` is absent.
   - `set_if_absent(field, value)` — for `status: active`, `coverage_axes: []`.
   The script must NOT set `reasoning_dimensions` — these are workflow-specific.
3. Specify that the script is a one-time idempotent migration (run → diff → commit), not a CI validator. Separate the migration script from dimension validation.
4. After migration, the existing 10 contracts gain ~5 new fields each. The 4 templates already have `evaluation_config` — the script must skip contracts where fields are already present.
**Impacts:** Plan 06 task count (+1 migration script), Plan 08 runner (depends on hardened schema). The 60 LOC estimate is more realistic than 40 given category-aware field insertion.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Adversarial note (Schema Integrity):** The original How misses the asymmetry between field types in migration: some fields have universal defaults (`status: active`), some require category-aware defaults (`hooks` arrays), and some are a value-migration not an insertion (`metadata.evaluation_depth` → `evaluation_config.depth`). If the migration script sets wrong `hooks` arrays, Plan 02's pre-session hook installation will install the wrong hooks, and the entire observation pipeline will be misconfigured. This cascades into Plans 03, 04, 07, and 08.

---

### P12-IMP-03: DimensionScore Missing `applicable` Field Despite Being a Locked Decision
**Target:** CONTEXT
**Status:** reframed
**Verdict:** REFRAME (Model Completeness lens)
**Original framing:** "CONTEXT.md says DimensionScore gains applicable: bool = True. But actual model in models.py has no applicable field. Plan 07, 08, 12 all depend on this field. Plan 01 gap — must add field before Plan 07."
**Reframed assessment:** The CONTEXT.md specification for `DimensionScore.applicable` is complete and unambiguous — it appears in three separate locations: Mode-Aware Dimension Filtering (IMP-25), Plan 01 deliverable 3, and per-category move applicability prose. The Plan 01 exit criteria already lock DC-1/DC-2/DC-3. The problem is not a CONTEXT gap; it is that the implementation (`models.py`) has not been executed yet. P12-IMP-03 conflates "not yet built" with "not yet specified," and its How field proposes confirming things in CONTEXT that are already confirmed. The actual risk is the `ScoreCard.effective_score()` edge case when ALL dimensions are non-applicable — see P12-ADV-2-01.
**Adversarial note (Model Completeness):** Three separate CONTEXT locations already specify `DimensionScore.applicable: bool = True` and `ScoreCard.effective_score()` as Plan 01 deliverables with locked exit criteria. The real gap accidentally pointed to is `effective_score()` behavior when all dimensions are `applicable=False`. That edge case needs one sentence in CONTEXT, not a restatement of IMP-25.
**Research needed:** no
**Confidence:** HIGH → N/A (reframed)
**Prior art:** 5
**Prerequisite:** no (reframed — see P12-ADV-2-01)

---

### P12-IMP-04: EvaluationPlugin Protocol Signature Mismatch With Actual Usage
**Target:** CONTEXT
**Status:** rejected
**Verdict:** REJECT (Model Completeness lens)
**Rejection reason:** Already fully addressed by existing CONTEXT. Evidence: (1) KCI Known Issues table: "EvaluationPlugin Protocol Missing Context Kwarg | Bug | Plan 01 | MEDIUM" — already triaged and owned. (2) KCI §A: Full diagnosis with file + line number (`reasoning_evaluator.py:201`), root cause, and fix: "add `context: dict[str, Any] | None = None` to Protocol (see DC-3)." (3) DC-3 section: Specifies the exact corrected signature. (4) Plan 01 deliverable 4: "EvaluationPlugin protocol with `context` param (DC-3). Hard exit criterion." The item adds nothing beyond what is already specified word-for-word, including a unit test for the exact failure mode.
**Research needed:** no
**Confidence:** MEDIUM → N/A (rejected)
**Prior art:** 4
**Prerequisite:** no

---

### P12-IMP-05: ground_truth_rubric Flow Has No Contract-to-Evaluator Wiring Specification
**Target:** CONTEXT
**Status:** reframed
**Verdict:** REFRAME (Schema Integrity lens)
**Original framing:** "ground_truth_rubric missing from Schema Hardening Field Manifest, schema, and REASONING_PROMPT_TEMPLATE has no `{rubric}` placeholder. No concrete wiring between 'rubric in YAML' and 'rubric in LLM prompt.'"
**Reframed assessment:** The wiring gap is real, but the proposed fix — adding `ground_truth_rubric` to the Schema Hardening atomic commit — creates a scope boundary violation. The atomic commit is already a 15-coordinated-edit operation. `ground_truth_rubric` is not a phantom field — it is a Plan 06 deliverable 8, already specified in CONTEXT.md. The gap is not that the field is missing from the manifest; it is that its TYPE, FORMAT, and PROMPT INJECTION MECHANISM are underspecified. Adding it to the atomic commit expands an already-large coordinated operation and couples schema structure with rubric content authoring. See P12-ADV-1-01 for the correct two-part specification.
**Adversarial note (Schema Integrity):** Adding `ground_truth_rubric` to the Schema Hardening atomic commit requires Core-tier contracts to include rubric text as part of the commit — meaning rubric text must be authored before the commit lands. That's a content prerequisite, not a schema prerequisite. Separating these is the right abstraction: schema first, content second, prompt wiring third.
**Research needed:** no
**Confidence:** MEDIUM → N/A (reframed)
**Prior art:** 2
**Prerequisite:** no (reframed — see P12-ADV-1-01)

---

### P12-IMP-06: Plans 09-10 Concurrent Execution Creates Shared State Corruption
**Target:** CONTEXT
**Status:** implemented
**Verdict:** ENHANCE (Execution Ordering lens)
**What:** The CONTEXT Shared Execution Note asserts Plans 09+10 are "parallelizable" while also specifying a single `progress.json` path, a single `.vrs/observations/` directory (no per-plan subdirectory), and a single `BaselineManager` keyed by `(workflow_id, run_mode, debate_enabled, effort_level)`. These three shared artifacts are all written during live evaluation runs. The conflict is not hypothetical: `os.replace()` atomicity guarantees a single write won't be read mid-write, but it does not prevent two concurrent plans from each performing a read-modify-write cycle on `progress.json` and clobbering each other's `completed_workflows` count. The BaselineManager's rolling 20-score windows can receive out-of-order entries from interleaved runs, silently corrupting variance calculations that Plan 12 Part 1 depends on.

The CONTEXT already states "Recommend running sub-waves in separate CC sessions to bound per-session cost and enable resumption." Plans 09+10 operating in the same session while writing to the same artifacts creates the exact zombie-artifact contamination scenario that FS-02 and FS-04 are designed to prevent — but those mitigations assume a single writer at a time.
**Why:** The CONTEXT simultaneously asserts parallelism ("parallelizable") and recommends against it ("separate CC sessions"), leaving the implementer with no authoritative resolution. The problem is not just shared state — it is a specification contradiction.
**How:**
1. **Clarify the parallelism claim in the Shared Execution Note.** Change "Plans 09+10 are parallelizable" to "Plans 09+10 may share the `/vrs-test-suite` skill in sequential sub-wave execution within a single session, or be run in separate sessions." Remove any implication of true concurrent execution.
2. **Add plan-scoped observation subdirectories:** `.vrs/observations/plan09/` and `.vrs/observations/plan10/` with per-plan session prefixes. The `ObservationParser` session_id filter already reads `{session_id}.jsonl` — per-plan subdirs ensure no cross-contamination without changing the parser.
3. **Serialise the execution order explicitly in the Cross-Plan Dependencies table:** Add `09 → 10` with `What: "sequential — shared progress.json + BaselineManager write safety"` and `Hard: YES`. This makes the ordering authoritative rather than implied.
4. **Gate Plan 10 Core sub-wave on Plan 09 Core sub-wave completion** (not just on Plan 08). Add the missing intra-Wave-6 dependency edges.
**Impacts:** Plans 09, 10, 11 execution ordering. Plan 08 runner needs plan-scoped progress file path.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Adversarial note (Execution Ordering):** The original How is correct in direction but undersells the root cause. The rewrite changes the target from fixing the artifacts to fixing the specification contradiction that causes the corruption risk.

---

### P12-IMP-07: Budget Estimates Systematically Undercount Debate Overhead
**Target:** CONTEXT
**Status:** implemented
**Verdict:** ENHANCE (Execution Ordering lens)
**What:** The CONTEXT defines three named timing concepts with specific figures: `per_workflow_execution_time` (Core investigation 15-30 min), `per_workflow_scoring_time` (~2-5 min), and `per_workflow_budget_ceiling` (default 2700s = 45 min). Separately, the Evaluator Debate Protocol states "Debate adds 5-15 min per Core workflow" and mandates `IMP-20 evaluation_timeout must use 900s budget when debate is enabled.` The conflict: the 2700s ceiling covers CC-level workflow execution, while the 900s evaluation timeout covers Python-level scoring. These are on different layers. The actual failure path: a 30-min Core investigation + 15-min debate overhead runs for 45 min total execution, consuming the entire 2700s ceiling before Python scoring (~2-5 min) even begins. The CC skill then writes `status: interrupted` and the entry never reaches the BaselineManager — meaning the most important workflows systematically fail to establish a baseline.
**Why:** The 900s IMP-20 timeout is for the evaluator LLM call, not for the total wall-clock budget. Three timing figures are in the same Shared Execution Note but are never summed to a total. Maximum case: 30 min execution + 15 min debate + 5 min scoring = 50 min = 3000s, exceeding 2700s. The 45 min ceiling is labeled as "~3-5x expected execution time" but this multiplier was derived before debate was added.
**How:**
1. **Add a fourth named timing concept** to the Budget Estimates block: `per_workflow_total_ceiling_with_debate: 3600s (60 min)` when `debate_enabled=True`. Mark as binding override of the 2700s default. Update Plan 08 deliverable 11: "CC skill reads `debate_enabled` from contract; if True, uses 3600s ceiling instead of 2700s default."
2. **Add a budget sanity formula** to the Shared Execution Note: `total_ceiling >= per_workflow_execution_time_p95 + debate_overhead_p95 + per_workflow_scoring_time_p95`. Require verification after first Core sub-wave run.
3. **Update Plan 08 exit criterion** from "full pipeline on 1 workflow produces report" to "full pipeline on 1 workflow WITH debate enabled produces report within 3600s ceiling."
4. **Distinguish the 900s IMP-20 evaluator timeout** from the 2700s/3600s CC-level ceiling. They currently share no cross-reference. Add note: "IMP-20 900s evaluation_timeout covers Python scoring layer only; CC skill ceiling (2700s/3600s) covers total wall-clock including execution + debate + scoring."
**Impacts:** Plan 08 budget ceiling logic. Plan 12 Part 0 timing estimates.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Adversarial note (Execution Ordering):** The original IMP-07 correctly identifies the arithmetic failure but incorrectly frames the fix as Plan 08 reading `debate_enabled` — already implied by IMP-20. The actual gap is that three named timing concepts are never combined into a total, and the 3-5x safety multiplier was calculated against pre-debate figures. The rewrite makes the formula explicit so it can be verified.

---

### P12-IMP-08: Evidence Fidelity Across Handoffs (Plan 11) Has No Concrete Metric
**Target:** CONTEXT
**Status:** implemented
**Verdict:** ENHANCE (Model Completeness lens)
**What:** Plan 11 deliverable 3 ("Evidence Fidelity Across Handoffs") specifies `EvidenceFlowEdge` with "semantic content comparison, NOT node ID matching" but provides no similarity threshold, comparison method, score range, or pass/fail criterion. The existing `EvidenceFlowEdge` dataclass in `tests/workflow_harness/lib/output_collector.py` (lines 68-84) has five fields: `from_agent, to_agent, evidence_type, content_preview, timestamp` — no fidelity metric. The original improvement misrouted the field: it proposed adding `fidelity_score` to `EvidenceFlowEdge` in Plan 01, but `EvidenceFlowEdge` lives in `output_collector.py` (a 3.1b dataclass file), not in Plan 01's `models.py`.
**Why:** Without a concrete metric, Plan 11's implementer faces two failure modes: (a) skip fidelity scoring entirely and declare deliverable 3 complete via `EvidenceFlowEdge` construction alone, or (b) invent an ad hoc metric that is incomparable across runs, invalidating regression detection.
**How:**
1. Add to Plan 11 deliverable 3 in CONTEXT.md: "Evidence fidelity metric: extract structured tuples `(function_name, vulnerability_class, severity)` from attacker's finding text and verifier's assessment text using regex against `EvidenceFlowEdge.content_preview`. Compute `fidelity_score = |intersection| / max(|attacker_tuples|, 1)`. Threshold: >= 0.6 for Core tier pass, recorded as WARN not FAIL (evidence degrades in serialization — hard fail is too brittle). Store as `EvidenceFlowEdge.fidelity_score: float | None = None`."
2. The `fidelity_score` field belongs in `output_collector.py` (the existing `EvidenceFlowEdge` dataclass in 3.1b), NOT in Plan 01's `models.py`. Add to Plan 11 deliverables: "Extend `EvidenceFlowEdge` dataclass in `tests/workflow_harness/lib/output_collector.py` with `fidelity_score: float | None = None`."
3. Add to Plan 11 exit criteria: "At least 1 Core orchestrator run produces non-None `fidelity_score` for attacker→verifier edge."
**Impacts:** Plan 11 deliverable 3 becomes implementable. File attribution corrected to output_collector.py.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Adversarial note (Model Completeness):** The item correctly identifies a real implementability gap. However, `EvidenceFlowEdge` is a `@dataclass` in `output_collector.py`, not a Pydantic model in Plan 01's `models.py`. Sending the field to Plan 01 creates a cross-module dependency in the wrong direction. The Jaccard threshold of 0.6 is reasonable given regex-based extraction on `content_preview` (200-char truncation), but should be WARN not hard FAIL to account for legitimate evidence compression during SendMessage. Conditional note: If Plan 01 KCI decision converts `EvidenceFlowEdge` to Pydantic, the field moves to Plan 01 scope retroactively.

---

### P12-IMP-09: No Smoke Test Gate Before Full Sub-Wave Rollout
**Target:** CONTEXT
**Status:** implemented
**Verdict:** CONFIRM (Execution Ordering lens)
**What:** The staged rollout describes sub-waves (a/b/c) but no "sub-wave zero" validates `/vrs-test-suite` can complete ONE workflow end-to-end. The `--dry-run` mode (IMP-04) exists but is not positioned as a hard gate before sub-wave (a).
**Why:** `/vrs-test-suite` does not yet exist. The first run on real Agent Teams is high-risk. Making dry-run a formal Gate 0 prevents wasting 10x Core workflow budget on a skill that cannot orchestrate correctly. Pre-flight activation test (P11-IMP-13) validates ACTIVATION but not EXECUTION.
**How:**
1. Add to Shared Execution Note: "Gate 0 (dry-run): Before sub-wave (a), run `/vrs-test-suite --dry-run` on 1 Core investigation workflow. Exit criteria: (a) Agent Teams spawned and completed, (b) debrief artifact written, (c) exit report passes schema validation, (d) delegate mode contamination check passes. Gate 0 failure HALTS all sub-waves."
2. Plan 09: add "Gate 0 dry-run validation" as first task.
**Impacts:** Plan 09 gains a hard prerequisite task.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Adversarial note (Execution Ordering):** Item withstands scrutiny. The CONTEXT acknowledges `/vrs-test-suite` doesn't exist yet but describes `--dry-run` as a deliverable of Plans 09-11 themselves — circular bootstrapping. Gate 0 must succeed BEFORE pre-flight activation test (P11-IMP-13). Gate 0's success definition must reference `SuiteExitReport` schema (Plan 01 deliverable 10), meaning Plan 01 must be complete before Gate 0 can be evaluated — already captured in dependency table. Second-order: Gate 0 should use `run_mode=headless` and explicitly NOT require debrief to avoid becoming a multi-hour blocker.

---

### P12-IMP-10: Sub-Wave Rollout Creates Implicit Circular Ordering That Contradicts Wave 6
**Target:** CONTEXT
**Status:** reframed
**Verdict:** REFRAME (Execution Ordering lens)
**Original framing:** "Plan 10 Core HITL gate blocks Plan 09 sub-wave (b). But both are Wave 6 peers. Implicit ordering never resolved."
**Reframed assessment:** The CONTEXT contains a genuine specification error. Plan 10 exit criteria state: "Core HITL gate passage required before Plans 09/11 sub-waves." Reading carefully: Plan 10's Core gate must pass before Plans 09 AND 11 can run sub-waves (b)/(c). But Plan 09 and Plan 10 share `/vrs-test-suite`. Sub-wave (a) Core for both must run before either can pass a Core HITL gate. The actual constraint is: `09a AND 10a` must both complete and pass HITL before either `09b` or `10b` can proceed. The current text says `10 Core gate → 09/11 sub-waves`, omitting that `09 Core` must also complete first. The correct abstraction is a **missing joint gate**: the CONTEXT needs a "Wave 6 Core HITL Gate" that gates on ALL of 09a + 10a completion, not just Plan 10's Core results. See P12-ADV-3-01 for the authoritative execution schedule.
**Adversarial note (Execution Ordering):** The original framing targets "implicit circular ordering" — the correct abstraction is a missing joint gate. The current text creates a false asymmetry (Plan 10 gates Plan 09) when the correct structure is a symmetric joint gate.
**Research needed:** no
**Confidence:** MEDIUM → N/A (reframed)
**Prior art:** 4
**Prerequisite:** no (reframed — see P12-ADV-3-01)

---

### P12-IMP-11: Delegate Mode Enforcement Has No Violation Recovery Path
**Target:** CONTEXT
**Status:** implemented
**Verdict:** ENHANCE (Enforcement & Ground Truth lens)
**What:** The delegate mode enforcement chain (P11-IMP-12 → P11-ADV-5-02 → P11-CSC-01) specifies detection via JSONL contamination analysis and defines what counts as a violation. What it does not specify is the remediation path when a violation is confirmed: should the result be (a) excluded from baseline, (b) not counted toward sub-wave gate passage, or (c) trigger a full re-run? The HITL reviewer at the Core gate has no documented decision tree for partial violations.
**Why:** Prompt-based enforcement is breakable by the model. Specifically: (1) the SessionValidityManifest (`FS-04`, Plan 08 SVM) has no `delegate_mode_violation` condition — violations are not currently routed through the existing invalid-session exclusion path; (2) Plan 09's exit criterion states "zero delegate mode violations in final gate-passing run set" but does not specify what to do with the contaminated result before re-run; (3) if violations are common during early runs, they will stall sub-wave gate passage indefinitely without a documented re-run protocol.
**How:**
1. In CONTEXT.md `/vrs-test-suite Delegate Mode Constraint` section, add: "**Violation remediation:** (a) Run Plan 08's `_check_session_validity()` — delegate mode violation is a 5th SVM condition that produces `valid=False, reasons=['delegate_mode_violation']`. (b) Violated results receive `EvaluationResult(status='invalid_session', reasons=['delegate_mode_violation: true'])` — excluded from baseline storage via the same guard as other invalid sessions. (c) For sub-wave gate passage, violated results do NOT count toward required workflow count — must be re-run. (d) If >2 violations occur in a single sub-wave, HALT and inspect SKILL.md prompt discipline before proceeding."
2. In Plan 08 deliverables, add SVM check 5: "`_check_delegate_mode(session_id, obs_dir) -> bool` — reads orchestrator JSONL, confirms zero `Read` or `Bash` entries targeting `.sol`, `.py`, or `vulndocs/` paths outside the P11-CSC-01 allowed-reads whitelist. ~15 LOC. Integrate into `_check_session_validity()` as 5th condition."
3. Plan 09 exit criteria: expand to: "Zero delegate mode violations in final gate-passing run set; any violations in prior runs documented with re-run count in exit report's `remediation_log` field."
4. Add `delegate_mode_violation` as a new `reasons` string to `SessionValidityManifest` model in Plan 01 (companion to `interrupted`, `stale`, `debrief_absent`).
**Impacts:** Plan 09 exit criteria. Plan 08 runner gains violation check in SessionValidityManifest. Plan 01 gains one `reasons` string.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Adversarial note (Enforcement & Ground Truth):** The original How proposes `delegate_mode_violation: true` as a standalone exit-report field — this bypasses the SessionValidityManifest that already handles all other invalid-session conditions. The SVM is a designed chokepoint in Plan 08. Adding a 5th SVM condition (~15 LOC) is architecturally correct; adding a parallel flag is architecturally wrong. Critical: if merged with the parallel-flag approach, `evaluation_runner.py:263`'s unconditional `update_baseline()` call will NOT catch delegate mode violations — contaminated results silently enter the baseline.

---

### P12-IMP-12: Prestep P1 (Multi-Agent Ground Truth) Has No Owner, Timeline, or Exit Criteria
**Target:** CONTEXT
**Status:** implemented
**Verdict:** ENHANCE (Enforcement & Ground Truth lens)
**What:** Prestep P1 is the only hard dependency in Plans 09-11 that has no concrete authoring specification. It states "Add 10-15 multi-agent ground truth templates" but does not define: the schema of each template, how templates relate to existing `corpus/ground_truth.yaml`, what constitutes a "valid" evidence flow tuple, or how templates are validated. The authoring effort involves domain knowledge about attacker/defender/verifier interactions that cannot be delegated to a script.
**Why:** P1 has three compounding gaps beyond ownership: (1) **Format gap:** No YAML schema exists for multi-agent ground truth. The existing `corpus/ground_truth.yaml` is a single-agent detection format. Multi-agent templates require a fundamentally different schema capturing cross-agent evidence handoffs. (2) **Validation gap:** No validation script checks template well-formedness before Plan 11 runs. Improperly structured templates silently produce wrong fidelity scores. (3) **Scope estimate realism:** "8-16 hours" assumes the author already understands expected interaction patterns. First 2-3 templates will take 2-4 hours each as format is discovered through iteration. Estimate is optimistic by 50-100%.
**How:**
1. Add a schema definition step as P1's FIRST task: "Define `ground_truth_multiagent_schema.yaml` (~40 LOC) specifying: `contract` (path to corpus contract), `vulnerability_category` (enum: reentrancy, access-control, etc.), `attacker_expected` (list of `{function, vulnerability_class, severity}`), `defender_expected` (list of `{mitigation_type, location}`), `verifier_expected` ({verdict: confirmed|disputed|unresolvable, rationale_keywords: list}), `evidence_flow_tuples` (list of `{source_agent, target_agent, evidence_key, expected_present: bool}`)."
2. Add a validation script: "`validate_multiagent_ground_truth.py` (~30 LOC) that runs JSON Schema validation against each template. Integrate into CI (`scripts/validate_scenarios.py`)."
3. Owner and timing: "P1 must be owned by the same person running Plan 11 Stage 4. Estimated effort: 12-24 hours (3h schema design + 2-4h per template x 10, with first 3 templates taking 4h each until format stabilizes). Can begin during Plans 09-10 Core sub-waves. HARD GATE: must complete before Plan 11 Core sub-wave."
4. Exit criteria: "10+ templates, covering >= 3 vulnerability categories (reentrancy, access-control, + 1 other), each with >= 2 evidence flow tuples, all passing `validate_multiagent_ground_truth.py`. Templates sourced from existing 18 corpus contracts."
5. Add P1's schema definition as a dependency in Cross-Plan Dependencies table: `P1-schema | P1-templates | Must define schema before authoring templates | YES`.
**Impacts:** Plan 11 timing. Prestep P1 becomes concrete with schema-first approach.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Adversarial note (Enforcement & Ground Truth):** P12-IMP-12 misses the most dangerous gap: no schema for templates means Plan 11's fidelity scorer will be written against a format invented ad-hoc. Once Plan 11's scorer is written against that format, changing the template schema requires rewriting the scorer. Schema must be defined FIRST — it is the contract between P1 (authors) and Plan 11 (consumers). See also P12-ADV-4-01 for the circular dependency between P1 schema and Plan 11 metric.

---

## Adversarial CREATE Items

### P12-ADV-1-01: ground_truth_rubric Needs Two-Part Specification Across Plans 06 and 07
**Source:** Adversarial review (Schema Integrity lens)
**Cross-references:** P12-IMP-05 (reframed)
**Target:** CONTEXT
**Status:** implemented

**What:** `ground_truth_rubric` is specified as a Plan 06 deliverable and a Plan 07 deliverable. But the specification has two distinct underspecifications:

**Part A — Schema field specification (Plan 06):**
- Type: `string` vs `list[str]` (one rubric per finding vs one combined rubric)
- Required for: Core tier only vs all tiers
- Format: free prose vs structured YAML vs templated chain format
- Maximum length constraint needed (token budget: < 6k per LLM call — rubric consumes budget from the same call as the agent transcript)

**Part B — Prompt injection contract (Plan 07):**
- Where in `REASONING_PROMPT_TEMPLATE` the rubric appears (before or after observed behavior)
- How to handle the absent-rubric case (omit section vs insert "No rubric provided")
- How binary "adequate coverage" maps to a 0-100 score
**Why:** Without Part A, contract authors produce rubrics of inconsistent format and length, some overflowing token budget. Without Part B, Plan 07 implementers have no agreed scoring boundary, and Plan 12 cannot use rubric scores as regression signals.
**How:**
1. Add to CONTEXT.md Implementation Decisions a new subsection "ground_truth_rubric Specification": (a) type: `string`, optional at all tiers (Core SHOULD include it, Standard MAY omit), (b) max length: 500 tokens (~400 words), (c) format: free prose, one sentence per expected finding.
2. Plan 06 deliverable 8: "Core contracts MUST include rubric text. Format: one sentence per corpus finding. Max 500 tokens."
3. Plan 07 deliverable 9: "Inject rubric as `## Expected Reasoning Coverage\n{rubric}` section. When absent, omit section entirely. Score mapping: rubric present + all findings covered = 80+, partial = 40-79, none = 0-39. Store as named dimension `rubric_coverage` separate from other dimensions."
4. Add `ground_truth_rubric` to Schema Hardening Field Manifest as an OPTIONAL field (not required). This avoids making it part of the atomic commit's REQUIRED array.
**Confidence:** HIGH
**Research needed:** no
**Prerequisite:** no
**Adversarial note:** `rubric_coverage` would be the 28th domain dimension requiring a DIMENSION_TO_MOVE_TYPES mapping (connects to IMP-01 registry expansion).

---

### P12-ADV-2-01: ScoreCard.effective_score() Undefined When All Dimensions Are Non-Applicable
**Source:** Adversarial review (Model Completeness lens)
**Cross-references:** P12-IMP-03 (reframed)
**Target:** CONTEXT
**Status:** implemented

**What:** `ScoreCard.effective_score()` is referenced by Plan 08 (mode-aware filtering), Plan 12 (baseline keying), and the Mode-Aware Dimension Filtering section, but its behavior when ALL dimensions are `applicable=False` is unspecified. If a support workflow runs in headless mode and every dimension gets `applicable=False` via the Mode Capability Matrix, `effective_score()` must return a defined value rather than divide-by-zero, return 0 (misrepresenting silence as failure), or raise.
**Why:** Plan 08's pre-run check suggests the all-non-applicable case is reachable in production. A support workflow with `run_mode=headless` gets `debrief=False`, and if it also skips GVS (`run_gvs: false`) and uses Support category (all 7 move types N/A per per-category move applicability table), then `effective_score()` receives all-non-applicable dimensions. Plan 12 uses `effective_score()` for baseline keying — a zero-return here versus a `None`-return produces different baseline entries.
**How:**
1. In CONTEXT.md Plan 01 deliverable 3, extend the `ScoreCard.effective_score()` spec: "When all dimensions are `applicable=False`, returns `None` (not 0) to distinguish 'no applicable dimensions evaluated' from 'all dimensions scored zero'. Plan 08 runner: if `effective_score() is None`, log WARNING and set `overall_score = 0` with `capability_gating_failed = True` to exclude from baseline."
2. Plan 12 Part 1: baseline keying skips results where `effective_score() is None` (cannot regress what was never measured).
**Confidence:** HIGH
**Research needed:** no
**Prerequisite:** no

---

### P12-ADV-3-01: Joint Wave 6 Core Gate is Unspecified — Missing Authoritative Execution Schedule
**Source:** Adversarial review (Execution Ordering lens)
**Cross-references:** P12-IMP-06, P12-IMP-07, P12-IMP-09, P12-IMP-10 (reframed)
**Target:** CONTEXT
**Status:** implemented

**What:** The CONTEXT has no single authoritative execution schedule for Wave 6 (Plans 09-11). The Shared Execution Note describes Plans 09+10 as "parallelizable" and describes staged sub-wave rollout (a/b/c), but never combines these into a complete execution sequence showing which tasks from which plans run in which order, what gates exist between stages, and what the total wall-clock budget is. Missing schedule creates three ambiguities: (1) whether 09a and 10a run simultaneously or sequentially; (2) who owns the Core HITL gate decision; (3) total Wave 6 wall-clock under debate-enabled conditions.
**Why:** Without an authoritative execution schedule, `/msd:plan-phase` will generate incorrect task breakdowns for Plans 09-11. The CONTEXT has all the ingredients (timing figures, sub-wave structure, gate conditions, budget ceiling) but never assembles them into a total.
**How:**
1. Add a "Wave 6 Execution Schedule" section to the Shared Execution Note:
   - **Stage 1 (Gate 0):** Dry-run `/vrs-test-suite` on 1 Core workflow. Gate criteria: 4 exit conditions from P12-IMP-09. Est. ~30-60 min.
   - **Stage 2 (Core sub-wave 09a+10a joint):** Plans 09 Core (~10 skills) and Plan 10 Core (~10 agents) run sequentially within a single session. Est. per-workflow: 20-45 min (non-debate), 30-60 min (debate). Total: ~4-8 hours.
   - **Stage 3 (Joint Core HITL gate):** Human reviews Core results for BOTH 09 and 10. Gate owner: human reviewer. Exit: no workflow has `evaluation_complete: False` for >50% of Core runs; at least 8 of 10 Core contracts pass capability check.
   - **Stage 4 (Important sub-waves 09b+10b+11 joint):** Plans 09, 10, 11 Important-tier. Plan 11 additionally requires Prestep P1. Est. total: ~6-10 hours.
   - **Stage 5 (Spot-check gate):** Human spot-checks 3 Important-tier results per plan.
   - **Stage 6 (Standard sub-waves 09c+10c+11c):** Headless, structural check only. ~3-6 min/workflow. Total: ~3-5 hours.
2. Total Wave 6 wall-clock estimates: non-debate best case ~14 hours, debate-enabled worst case ~26 hours. Recommend separate CC sessions per stage.
3. Add `09a+10a` → joint HITL gate → `09b+10b+11` edges to Cross-Plan Dependencies table with `Hard: YES`.
**Confidence:** HIGH
**Research needed:** no
**Prerequisite:** no
**Adversarial note:** All four items in the Execution Ordering group (IMP-06, 07, 09, 10) are symptoms of the same missing artifact — this schedule absorbs and unifies them.

---

### P12-ADV-4-01: P1 Schema and Plan 11 Evidence Fidelity Have a Circular Dependency
**Source:** Adversarial review (Enforcement & Ground Truth lens)
**Cross-references:** P12-IMP-12, P12-IMP-08
**Target:** CONTEXT
**Status:** implemented

**What:** P1 (multi-agent ground truth templates) must define a schema for evidence flow tuples. Plan 11 deliverable 3 (evidence fidelity scoring per P12-IMP-08) must define what fields it extracts from templates to compute fidelity. These two specifications are mutually constraining: P1 schema cannot be finalized without knowing what Plan 11 will extract; Plan 11's fidelity scorer cannot be written without knowing P1's schema. Neither P12-IMP-12 nor P12-IMP-08 acknowledges this dependency.
**Why:** If P1 templates are authored before Plan 11's fidelity metric is specified (the most likely order, since P1 starts in Stages 1-3 while Plan 11 is Stage 4), the templates will embed evidence tuples in whatever format the author finds natural. When Plan 11 implements fidelity scoring, it will either adapt its metric to the chosen format (metric driven by convenience, not validity) or require templates to be retrofitted (rework). The correct resolution requires a joint schema-metric design step.
**How:**
1. Add to CONTEXT.md Cross-Plan Dependencies: "P1-schema design | Plan 11 deliverable 3 | Evidence fidelity metric and P1 template schema must be co-designed in a single ~2h joint session before P1 template authoring begins. Output: `P1_schema.md` specifying both template YAML fields and Plan 11 extraction contract."
2. Add to P1 timing: "Schema design requires Plan 11's evidence fidelity metric specification to be drafted first. Timeline adjustment: P1 schema cannot begin until after Plan 11 deliverable 3 spec is locked (Wave 3 parallel to Plan 07)."
**Confidence:** HIGH
**Research needed:** no
**Prerequisite:** no
**Adversarial note:** P12-IMP-08 specifies extracting `(function_name, vulnerability_class, severity)` tuples. P12-IMP-12's proposed template format includes `attacker_expected: list[{function, vulnerability_class, severity}]`. These happen to match — but only because this review checked both. If authored independently, they would likely diverge.

---

## Synthesis Items

### P12-SYN-01: New Scored Concepts Lack a Governance Process for Entering the Evaluation Vocabulary
**Target:** CONTEXT
**What:** Three items across different review groups independently introduce or expand scored concepts without any unified process for how new dimensions and metrics enter the evaluation vocabulary and get wired to the scoring pipeline. P12-IMP-01 discovers 27 domain dimensions exist (vs the assumed 6-8). P12-ADV-1-01 proposes `rubric_coverage` as the 28th domain dimension. P12-IMP-08 proposes `fidelity_score` as a new metric on `EvidenceFlowEdge`. Each item specifies its own concept in isolation, but the CONTEXT has no "how to add a new scored concept" process covering: (a) registration in the dimension registry, (b) creation of a `DIMENSION_TO_MOVE_TYPES` mapping entry, (c) addition to at least one evaluation contract, (d) prompt template section authoring for Plan 07. Without this, every future improvement pass that introduces a new dimension will independently re-discover the same wiring requirements.
**Why:** Addressing this as a unified concern prevents the dimension vocabulary from growing ad-hoc. IMP-01 already shows the consequence of uncontrolled growth: 19 dimensions exist in contracts with no registry entry, no move-type mapping, and no prompt template. Fixing IMP-01 by adding 27 entries to the registry without a process guarantee means Pass 13 could introduce dimension #28 with the same gap. The process also disambiguates scored concepts that ARE dimensions (like `rubric_coverage`) from scored concepts that are NOT dimensions (like `fidelity_score`), preventing architectural confusion about where new metrics belong.
**How:**
1. Add to CONTEXT.md Implementation Decisions a new subsection "New Scored Concept Governance": "To add a new evaluation dimension: (a) add name to `dimension_registry.yaml`, (b) add `DIMENSION_TO_MOVE_TYPES` mapping entry in `reasoning_evaluator.py` specifying which of the 7 move types inform this dimension, (c) add dimension to at least one evaluation contract's `reasoning_dimensions` list, (d) add prompt template section to appropriate category template in Plan 07. All four steps must land in the same commit. Metrics that are NOT dimensions (e.g., `fidelity_score` on `EvidenceFlowEdge`) do not require steps (a)-(d) and must NOT be added to the dimension registry."
2. In Plan 06 deliverables, add: "Run governance checklist on all 27 existing dimensions before atomic commit. Flag any dimension that has a registry entry but no move-type mapping as INCOMPLETE."
**Impacts:** Plans 06, 07, 12 (any plan that introduces scored concepts)
**Components:** P12-IMP-01, P12-ADV-1-01, P12-IMP-08
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)

---

### P12-CSC-01: IMP-01 Registry Expansion Creates 25 Unmapped Dimension-to-Move-Type Entries With No Authoring Specification
**Target:** CONTEXT
**What:** P12-IMP-01 (enhanced) expands the dimension registry from ~8 to 27 domain dimensions. Plan 07 deliverable 6 specifies `DIMENSION_TO_MOVE_TYPES: dict[str, list[str]]` with two example mappings (`graph_utilization` and `evidence_quality`). When IMP-01 is implemented, Plan 07 must produce mappings for all 27 dimensions. The CONTEXT provides no specification for HOW to create these mappings -- which move types are appropriate for each dimension is a judgment call with no documented criteria. For example, should `creative_adversarial_thinking` map to `HYPOTHESIS_FORMATION` alone, or also `SELF_CRITIQUE`? Should `task_delegation` (an orchestration-specific dimension) map to `EVIDENCE_INTEGRATION`? Without authoring criteria, 25 mappings will be invented ad-hoc during Plan 07 implementation. Incorrect mappings cause the evaluator to ask the wrong questions for a dimension, silently producing meaningless scores that pass all validation.
**Why:** The dimension-to-move-type mapping is the junction between what contracts declare (Plan 06) and what the evaluator measures (Plan 07). A wrong mapping means a dimension is scored against irrelevant reasoning moves -- e.g., scoring `task_delegation` against `QUERY_FORMULATION` would evaluate whether an orchestrator formulated graph queries, which is meaningless for delegation quality.
**How:**
1. Add to CONTEXT.md Plan 07 deliverable 6: "Before writing `DIMENSION_TO_MOVE_TYPES`, define a mapping authoring rubric: (a) for each dimension, identify the primary behavioral signal the dimension measures; (b) select move types whose evaluation questions directly assess that signal; (c) exclude move types where the dimension has no behavioral overlap; (d) validate that each mapping has 1-3 move types (mappings with 0 produce `applicable=False`; mappings with >3 dilute focus). Document reasoning for non-obvious mappings (e.g., `task_delegation` -> `EVIDENCE_INTEGRATION` because delegation quality is measured by evidence-passing between agents)."
2. Plan 07 exit criteria: add "All 27+ domain dimensions in the registry have non-empty `DIMENSION_TO_MOVE_TYPES` entries. No entry has >3 move types without documented justification."
**Impacts:** Plan 07 scope and LOC estimate (~20 LOC for 8 dimensions becomes ~60 LOC for 27 dimensions + rubric)
**Trigger:** P12-IMP-01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

---

### P12-CSC-02: ADV-3-01 Wave 6 Execution Schedule Has No Intra-Stage Failure Policy
**Target:** CONTEXT
**What:** P12-ADV-3-01 (open) defines a 6-stage Wave 6 execution schedule with gates between stages. But no stage specifies what happens when an individual workflow fails WITHIN a stage. Stage 2 runs ~20 Core workflows sequentially. If workflow #3 of 20 fails (capability check fails, CC crashes, delegate mode violation, timeout), the schedule provides no guidance: does the stage halt entirely? Skip the workflow and continue? Count it as a failure toward the Stage 3 gate threshold ("at least 8 of 10 Core contracts pass")? The Stage 3 gate specifies "at least 8 of 10 Core contracts pass capability check" -- implying up to 2 failures are acceptable -- but Stage 2 has no mechanism to record or surface per-workflow failures for the gate reviewer. The `progress.json` artifact tracks `completed_workflows` count but not `failed_workflows` or `failure_reasons`.
**Why:** Without intra-stage failure handling, the most likely behavior is that CC skill `/vrs-test-suite` writes `status: interrupted` for the failed workflow and continues to the next. But the Stage 3 HITL reviewer then receives a progress report with no structured failure information -- they must manually inspect JSONL to determine whether the 2 "missing" results were infrastructure failures (re-runnable) or capability failures (genuine). This distinction determines whether the gate passes.
**How:**
1. Add to ADV-3-01's Stage 2 specification: "Per-workflow failure handling: if a workflow fails (timeout, crash, delegate violation), write `EvaluationResult(status='failed', reasons=[...])` to exit report and continue to next workflow. Do not halt the stage. The exit report's `per_workflow_results` array distinguishes `completed`, `failed`, and `skipped` entries."
2. Add to ADV-3-01's Stage 3 gate: "Gate reviewer receives structured failure summary: `{completed: N, failed: N, skipped: N, failure_reasons: [...]}`. Gate passage requires: (a) completed >= 8, AND (b) no failure has `reasons=['delegate_mode_violation']` (any delegate violation = gate fail regardless of count)."
3. Add `failed_workflows: int` and `failure_summary: list[dict]` to `EvaluationProgress` model in Plan 01 (currently tracks only `completed_workflows`).
**Impacts:** Plan 01 (`EvaluationProgress` gains failure tracking fields), Plan 08 (progress writer), Plans 09-10 (exit report structure)
**Trigger:** P12-ADV-3-01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

---

## Summary

| Status | Count | Items |
|--------|-------|-------|
| implemented | 15 | IMP-01, 02, 06, 07, 08, 09, 11, 12 + ADV-1-01, 2-01, 3-01, 4-01 + SYN-01 + CSC-01, CSC-02 |
| rejected | 1 | IMP-04 |
| reframed | 3 | IMP-03, 05, 10 |
| **Total** | **19** | 15 implemented + 1 rejected + 3 reframed |

## Post-Review Synthesis
**Items created:** P12-SYN-01, P12-CSC-01, P12-CSC-02
**Key insight:** The dimension vocabulary has grown 3.5x beyond what the CONTEXT specifies (27 actual vs 8 assumed), and three independent items propose adding scored concepts without any shared governance process. This creates a cascade: IMP-01's registry expansion requires 25 unmapped dimension-to-move-type entries in Plan 07 with no authoring criteria, while ADV-3-01's execution schedule specifies inter-stage gates but no intra-stage failure handling, leaving the HITL reviewer without structured data to make gate decisions.
