# Improvement Pass 15

**Pass:** 15
**Date:** 2026-02-23
**Prior passes read:** 14 (via IMPROVEMENT-DIGEST.md: 288 merged from P1-P13, P14 with 25 items in-progress)
**Areas:** Strategic Vision Alignment, 3.1e Empirical Integration, 3.1f Forward Path & Interface, Orchestration Model & Agent Architecture, Data Pipeline Reality (Plans 01-03), Evaluation Quality (Plans 04-07), Execution & Improvement Loop (Plans 08-12)
**Agent count:** 7 improvement agents, 5 adversarial reviewers (sonnet), 1 synthesis (pending)
**Cross-pollination:** 3.1e (Evaluation Zero), 3.1f (Proven Loop Closure), broader AlphaSwarm mission alignment
**Status:** complete

<!-- File-level status: in-progress | complete -->

## Pipeline Status

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 0 | 0 | — |
| Research | 0 | 4 | — (all resolved 2026-02-23) |
| Gaps | 0 | 0 | — |
| Merge-ready | 0 | 21 (P14) + 38 (P15) | — |

**Pipeline:** [discuss] done → [improve] done → [adversarial] done → [synthesis] done → [pre-impl] — → [research] done → [implement] done
**Merged:** 2026-02-23 — 59 items merged into 3.1c-CONTEXT.md (21 from P14 + 38 from P15)

### Research Resolution (2026-02-23)

**R1: P14-ADV-4-02 — Temperature flag for `claude -p`**
- **Finding:** Claude Code v2.1.50 has NO `--temperature` flag. Not in `--help` output. No `CLAUDE_DEFAULT_TEMPERATURE` environment variable.
- **Verdict:** UNAVAILABLE. Temperature is a known non-determinism source.
- **Action:** Document in CalibrationConfig as `temperature: null` (platform-imposed, not controllable). Plan 07: `EVALUATOR_TEMPERATURE` constant NOT created. Add to CalibrationConfig: `temperature_controllable: bool = False`. Debate reproducibility relies on `--effort high` only. Plan 12 BaselineKey does NOT include temperature field (nothing to vary).

**R2: P14-ADV-2-02 — Opus pricing and `claude -p` usage metadata**
- **Finding:** `claude -p --output-format json` returns `{result, model, usage, cost_usd}` — cost metadata IS available per call. The `usage` field contains token counts. The `cost_usd` field provides per-call cost. This was confirmed via SFEIR Institute documentation on Claude Code headless mode.
- **Verdict:** COST TRACKING IS POSSIBLE per `claude -p` call. The P14-IMP-10 reframe claiming "claude -p does not return cost metadata" is INCORRECT.
- **Action:** Plan 07: after each `claude -p` evaluation call, parse `cost_usd` from JSON output. Plan 08: accumulate per-workflow scoring cost in EvaluationResult as `scoring_cost_usd: float | None`. Plan 12 Part 0: total calibration cost reported. HITL gate: if cumulative cost exceeds 2x estimate, pause for approval. Per-dimension cost estimate: ~$0.03-0.04 at Opus 4.6 pricing (confirmed from ccusage data showing typical session costs). Per Core workflow scoring: ~$0.60-0.80 (10 applicable dimensions x 2 evaluators). Per-run cost ceiling of $10 IS now enforceable via `cost_usd` accumulation + circuit breaker.

**R3: P15-IMP-17 — Parallel `claude --print` isolation**
- **Finding:** Multiple `claude -p` sessions CAN run in parallel. Each `claude -p` invocation is a stateless one-shot — no shared session state. Git worktrees provide filesystem isolation (confirmed by multiple community guides: ccswitch, cmux, tmux-based workflows). Each `claude -p` call gets its own API context window. No shared process state between `--print` invocations.
- **Conditions verified:** (a) Separate working directories via worktrees or subdirectories — YES, standard practice. (b) File locking for shared resources (BaselineManager) — REQUIRED, not automatic. (c) Circuit-breaker state read-only during parallel execution — ACHIEVABLE via file-based locking.
- **Verdict:** PARALLEL SAFE with conditions. Each `claude -p` is stateless. Filesystem isolation is the only concern.
- **Action:** Plan 08: `max_parallel_headless: int = 1` default, increment to 3 after isolation test passes. Conditions: (a) each session writes to `{session_id}/` subdirectory (enforced by EvaluationRunner), (b) BaselineManager uses `fcntl.flock()` file locking for write operations, (c) circuit-breaker reads `.vrs/evaluations/circuit_breaker.json` but does NOT write during parallel execution — writes happen in coordinator only. Agent Teams remain sequential (shared session state).

**R4: P15-ADV-4-01 — Context token consumption per headless run**
- **Finding:** Claude Code context window is 200K tokens (standard) or 1M (premium). Each `claude -p` call is independent — context is NOT accumulated across calls. The coordinator (interactive session) accumulates context for its own management loop. Per the Mode Capability Matrix, headless runs are `claude -p` one-shots that return JSON results to disk. The coordinator reads only summary fields (`workflow_id`, `overall_score`, `gate_pass`) from disk — NOT full exit reports inline.
- **Verdict:** CONTEXT EXHAUSTION IS A COORDINATOR PROBLEM, NOT A HEADLESS PROBLEM. Each headless run has its own full 200K window. The coordinator must avoid reading full results inline.
- **Action:** Locked decision confirmed: "Exit reports written to `.vrs/evaluations/{workflow_id}_{run_id}.json`. Coordinator reads summary fields only via `jq` extraction or Python JSON parsing." Context ceiling: 51 headless runs produce 51 JSON files on disk — coordinator never holds more than summary data for all 51 (~5K tokens). Plan 09 exit: 10 headless runs produce readable summary without coordinator context warnings. Mode Capability Matrix: headless unlimited (each gets own window), interactive limited by coordinator context (~20 workflows before context pressure).

## Adversarial Lenses

| Lens | Brief | Items | Attack Vector |
|------|-------|-------|---------------|
| Scope Reduction Coherence | 7 items aggressively reduce 3.1c scope — design gate, Plan 06/12 reduction, headless-first, sequential calibration, 3.2 tagging | IMP-01,03,12,35,36,37,39 | Do combined reductions leave enough data for meaningful calibration (rho > 0.6 with 15 contracts, 20 sessions)? |
| Cross-Phase Interface Integrity | 9 items define 3.1e/3.1f interfaces — override protocols, artifact schemas, variant tester wrapping, Goodhart ownership | IMP-06,07,09,10,11,13,14,15,16 | Are these interface contracts premature — specifying schemas before 3.1e experiments run? |
| Empirical Validation Demand | 9 items demand empirical validation — 7-move taxonomy, debate, DEFAULT-30, dimensions, rubric wiring | IMP-02,04,08,29,30,31,32,33,34 | Does demanding validation of EVERY design decision create analysis paralysis? Are all demands equally justified? |
| Orchestration Architecture | 7 items address orchestration — parallel execution, skill decomposition, mode profiles, delegate enforcement | IMP-17,18,19,20,21,22,23 | Does splitting an unwritten skill add coordination overhead that outweighs reliability benefits? |
| Pipeline Data Integrity | 9 items address pipeline correctness — type separation, P0 checks, null contracts, hook health, bug fixes | IMP-05,24,25,26,27,28,38,40,41 | Is 39% of items on plumbing over-engineering for a system with zero evaluations? |

## Improvements

<!-- ============================================================ -->
<!-- AREA 1: Strategic Vision Alignment (5 items) -->
<!-- ============================================================ -->

### P15-IMP-01: Declare Design-Complete Gate Before Further Improvement Passes
**Target:** CONTEXT
**What:** 288 merged improvements across 13 passes with zero real evaluations is over-design. Add locked decision: "CONTEXT.md is design-complete as of Pass 14. Further improvement passes blocked until (a) Plan 02 P0 delivers 3+ real transcripts AND (b) Plan 07 produces at least one real LLM evaluation call with non-degenerate DimensionScore (std dev > 5pt across scored dimensions, at least one score outside [45, 55]). Exceptions: bug fixes to existing locked decisions and cross-phase alignment items from 3.1e/3.1f results."
**Why:** Each additional pass adds specification complexity without empirical validation. Gate redirects effort from refinement to implementation.
**How:**
1. Add Implementation Decision "Design Completion Gate" with strengthened non-degeneracy condition
2. Add to Exit Gate section: gate satisfied when P0 transcripts exist AND non-degenerate LLM evaluation produced
3. Exception path (self-contained, no cross-reference to other P15 items): "If 3.1e experiments produce data that directly falsifies a locked decision, implementer writes one-paragraph override request citing data. Override applied in next /msd:implement-improvements without full improvement pass."
**Impacts:** All future improvement passes blocked until empirical data exists.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Scope Reduction Coherence):** Gate condition strengthened from "one LLM call" to "non-degenerate LLM call" (std dev > 5pt). Exception path made self-contained — no dependency on other P15 items.

### P15-IMP-02: Grader Taxonomy Divergence Diagnostic Branch
**Target:** CONTEXT
**What:** At 13.3% precision, Spearman rho between reasoning quality and detection accuracy will likely be near zero even with working evaluator. Add two-branch diagnostic to Calibration Anchor: if rho < 0.3, compute partial_rho on TRUE POSITIVE subset only. If partial_rho_tp_only > 0.6: "detection noise" — proceed with TP-only baseline. If partial_rho_tp_only < 0.3: "evaluator failure" — No-Go Fallback.
**Why:** Without diagnostic, No-Go Fallback fires for wrong reason and stops valid work.
**How:**
1. Add two-branch diagnostic to Calibration Anchor Protocol as locked decision
2. Add `partial_rho_tp_only: float | None` and `anchor_diagnosis: Literal["calibrated", "detection_noise", "evaluator_failure", "pending"]` to CalibrationConfig
3. Plan 12 Part 0 exit criterion: "TP-only filter implemented. If rho < 0.3, partial_rho computed and diagnosis recorded."
4. Cross-reference P15-IMP-37 — TP-only filter applies to both Phase 1 (20-session) and Phase 2 (72-session)
**Impacts:** Plan 12 Part 0, CalibrationConfig model, Plan 01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Empirical Validation Demand):** How enhanced with data model recording point (anchor_diagnosis) and downstream Plan 12 cross-reference.

### P15-IMP-03: Reduce Plan 06 Stub Contracts — reasoning_dimensions Gap
**Target:** CONTEXT
**What:** Tiered Contract Authoring already stubs Standard tier. The real gap: Schema Hardening prohibits category-level defaults for `reasoning_dimensions`, so stub contracts have no valid way to specify dimensions. Fix: stub contracts carry `reasoning_dimensions: []` with `run_reasoning: false`.
**Why:** Existing policy covers Standard stubs but doesn't resolve the reasoning_dimensions/Schema Hardening conflict.
**How:**
1. In Schema Hardening atomic commit, add: "If `reasoning_dimensions: []` AND `evaluation_config.run_reasoning: true`, validator rejects. Stub template: `reasoning_dimensions: []`, `run_reasoning: false`, `status: stub`."
2. Plan 06 exit criterion: "15 Core+Important contracts hand-authored. 36 Standard stubs with valid schema. Results flagged `contract_quality: stub` in EvaluationResult."
**Impacts:** Plan 06 scope, Schema Hardening
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Scope Reduction Coherence):** Rewritten to target the actual gap (reasoning_dimensions conflict), not the already-locked stub policy.

### P15-IMP-04: Missing Evaluation-to-Detection Bridge in ImprovementHints
**Target:** CONTEXT
**What:** No mechanism translates evaluation scores into actionable detection improvements. ImprovementHint has `suggested_change` but no `target_component` field.
**Why:** The entire evaluation framework exists to improve detection (13.3% → higher). Without routing, hints require human interpretation.
**How:** (see P15-ADV-3-01 for corrected framing)
**Impacts:** Plan 01 model, Plan 07 hint generation, Plan 12 improvement cycle
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Empirical Validation Demand):** Reframed — `target_component` enum should be discovered from data after real evaluations, not designed a priori. Replaced by P15-ADV-3-01.

### P15-IMP-05: Plan 01 Type Audit — Separate Bridge Types from Internal Types
**Target:** CONTEXT
**What:** Of 30+ types, exactly 5 bridge types carry spec-vs-reality risk: `ToolUseData`, `ToolResultData`, `SubagentData`, `SessionData`, `ObservationSummary`. Remaining ~27 are internal. Categorize explicitly as Group A (bridge, PROVISIONAL) and Group B (internal, finalize in Wave 1).
**Why:** The "30+ types" framing obscures which types need real-data validation.
**How:**
1. Plan 01 deliverables: Group A (5 bridge types) with PROVISIONAL annotations, Group B (~27 internal) finalized in Wave 1
2. Plan 01 exit criterion: "Group B types fully specified with round-trip tests. Group A has PROVISIONAL annotations."
3. Cross-reference P15-IMP-26 — SubagentData fields get KNOWN_ABSENT (stronger than PROVISIONAL)
**Impacts:** Plan 01 scope clarity, Plan 02 P0 validation scope
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Pipeline Data Integrity):** How enhanced with concrete 5-type list and cross-reference to IMP-26 KNOWN_ABSENT tier.

<!-- ============================================================ -->
<!-- AREA 2: 3.1e Empirical Integration (6 items) -->
<!-- ============================================================ -->

### P15-IMP-06: Empirical Override Protocol for Locked Decisions
**Target:** CONTEXT
**What:** Proposed three-state formal amendment machinery (CONFIRM/AMEND/REVOKE) for locked decisions.
**Why:** Locked decisions built on zero empirical data need an amendment path.
**How:** (see P15-ADV-2-01 for corrected framing)
**Impacts:** All locked decisions
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Cross-Phase Interface Integrity):** Three-state protocol adds specification weight — the anti-pattern IMP-01 is trying to stop. Replaced by lightweight per-plan permission gates (P15-ADV-2-01).

### P15-IMP-07: Pre-Planned What-If Scenarios for 3.1e Failures
**Target:** CONTEXT
**What:** Three failure scenarios with pre-planned responses, now with specific artifact paths: (A) LLM degeneracy trigger in `.vrs/experiments/plan-02/llm-scores.jsonl`; (B) 7-move mismatch in Plan 07 Sub-task 0; (C) Zero heuristic validity in `.vrs/experiments/plan-03/validity-matrix.json`.
**Why:** Without pre-planned responses with concrete measurement sources, failures trigger unstructured redesign.
**How:**
1. Add "3.1e Failure Response Matrix" to CONTEXT (~15 lines, three rows with trigger+artifact path+affected plans+response)
2. Plans 07 and 12 gain: "Before implementing [feature], consult matrix row [A/B/C]"
3. Matrix is READ-ONLY — not amended by 3.1e results
**Impacts:** Plans 07, 08, 12
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Cross-Phase Interface Integrity):** Enhanced with specific artifact paths. READ-ONLY matrix distinguishes this from over-engineered override protocol (IMP-06).

### P15-IMP-08: 7-Move Reasoning Validation Task Missing from All Plans
**Target:** CONTEXT
**What:** 3.1e defers 7-move validation to 3.1c, but no 3.1c plan contains a validation task. Zero code references for the 7-move decomposition.
**Why:** If taxonomy doesn't map to real agent behavior, 27 dimensions map to fictional move boundaries.
**How:**
1. Add to Plan 07 deliverables: "Sub-task 0: Manually annotate 2 real transcripts with move boundaries. If <4 distinguishable, merge. Gate before per-dimension scoring."
2. Plan 07 exit criteria: "7-move taxonomy validated OR reduced to empirically observable moves."
**Impacts:** Plan 07 gains validation sub-task. Dimension registry may shrink.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** no
**Depends on plans:** Plan 02 (real transcripts)
**Classification:** structural
**Status:** confirmed
**Adversarial note (Empirical Validation Demand):** Withstands scrutiny. Low-cost gate (2 transcripts, 1 hour) with high consequence if skipped. NOT a duplicate of IMP-29 — IMP-08 is governance (missing plan task), IMP-29 is execution (annotation method).

### P15-IMP-09: Cross-Phase Artifact Contracts for 3.1e→3.1c Data
**Target:** CONTEXT
**What:** Proposed pre-specified YAML schemas for 3.1e→3.1c artifact data.
**Why:** P14-IMP-23 and P14-IMP-24 specify soft dependencies but not artifact format.
**How:** (see P15-ADV-2-02 for corrected framing)
**Impacts:** Plans 07, 12
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Cross-Phase Interface Integrity):** Pre-specifying field names for unobserved artifacts is the v5.0 anti-pattern. 3.1e Plan 05 owns schema definition. Replaced by consumption contracts with fallbacks (P15-ADV-2-02).

### P15-IMP-10: Provisional Scoring Bands Need Config, Not Constants
**Target:** CONTEXT
**What:** Scoring bands (80+/40-79/0-39) hardcoded. Make config-driven with current values as defaults.
**Why:** 3.1e may recommend different bands. ~5 LOC change.
**How:**
1. Mark bands as PROVISIONAL in ground_truth_rubric
2. Plan 07: read from `evaluation_config.yaml` instead of constants
**Impacts:** Plan 07, Plan 06 contracts
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (Cross-Phase Interface Integrity):** Withstands scrutiny. Adds loading mechanism without pre-specifying new values. Clean.

### P15-IMP-11: GVS Content Validation Policy from 3.1e
**Target:** CONTEXT
**What:** Document 3.1e's evaluation layer content validation policy (proxy-only layers 1-2, LLM defense layer 3) in 3.1c GVS Architecture section.
**Why:** Prevents recurring GVS content feature proposals (P6-IMP-16, P7-IMP-09 already rejected).
**How:**
1. Add to GVS Architecture: "GVS is a PROXY scorer (layers 1-2). Content quality evaluation is exclusively Plan 07's LLM evaluator (layer 3)."
**Impacts:** GVS Architecture locked decision
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (Cross-Phase Interface Integrity):** Documents an already-decided 3.1e policy. Minimal, correct, prevents scope creep.

<!-- ============================================================ -->
<!-- AREA 3: 3.1f Forward Path & Interface (5 items) -->
<!-- ============================================================ -->

### P15-IMP-12: Hard Boundary Between Plan 12 and 3.1f Scope
**Target:** CONTEXT
**What:** Plan 12 Parts 0-1 (calibration, variance) = 3.1c. Parts 2-5 = 3.1f. Explicit boundary with handoff artifacts.
**Why:** Without boundary, Plan 12 builds what 3.1f rebuilds.
**How:**
1. Add Implementation Decision "Plan 12 / 3.1f Boundary" per original specification
2. Plan 12 exit criteria: remove Parts 2-5. Add handoff artifact documentation.
3. Handoff artifacts (schema-stable): `calibration_config.yaml`, `variance_summary.yaml`, `baseline_data/`, `experiment_ledger.jsonl` (empty, with `decision: Literal['accept', 'reject', 'abandoned']` per IMP-40)
4. Add corresponding entry in 3.1f CONTEXT.md: "3.1f receives from Plan 12: [artifact list]. Does NOT re-implement."
5. Parts 2-5 text migrates to 3.1f CONTEXT.md as reference material (absorbed from rejected IMP-36)
**Impacts:** Plan 12 reduced from ~2 weeks to ~3-4 days. 3.1f gains concrete inputs.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Scope Reduction Coherence):** Absorbed IMP-36's unique detail (Parts 2-5 text migration). Added schema stability for experiment_ledger.jsonl. Added 3.1f CONTEXT.md entry.

### P15-IMP-13: EvaluationResult Needs FailureSignal for 3.1f Classifier
**Target:** CONTEXT
**What:** Add PROVISIONAL `FailureSignal` model with four taxonomy-independent signal types: `below_threshold`, `high_variance`, `evaluator_disagreement`, `infrastructure_failure`. Add `failure_signals: list[FailureSignal] = []` to EvaluationResult.
**Why:** 3.1f needs machine-readable input. Four values are taxonomy-independent — safe regardless of what 3.1e discovers.
**How:**
1. Plan 01: FailureSignal model with PROVISIONAL annotation. `signal_type: Literal["below_threshold", "high_variance", "evaluator_disagreement", "infrastructure_failure"]`
2. Plan 08: populate failure_signals using 3.1c-internal signal types only
3. 3.1f Plan 01: consumes failure_signals as primary input, applies 3.1e taxonomy as secondary mapping
**Impacts:** Plan 01 model, Plan 08. 3.1f gains typed input.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Cross-Phase Interface Integrity):** PROVISIONAL annotation and narrowed enum prevents hard conflict with 3.1e taxonomy.

### P15-IMP-14: 3.1f Variant Tester Must Wrap Plan 12 Infrastructure
**Target:** CONTEXT
**What:** 3.1f Plan 02 wraps Plan 12's WorkspaceManager, not independent git branch isolation.
**Why:** 3.1f Assumption 3 uses git branch isolation while Plan 12 specifies Jujutsu WorkspaceManager — conflict if not explicit.
**How:**
1. Plan 12 exit criteria: "WorkspaceManager API documented for 3.1f"
2. CONTEXT cross-phase: "3.1f Variant Tester is thin wrapper (~50 LOC) around Plan 12 WorkspaceManager + BaselineManager.check_batch()"
**Impacts:** Plan 12, 3.1f Plan 02
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (Cross-Phase Interface Integrity):** Withstands scrutiny. Prevents real git vs Jujutsu conflict.

### P15-IMP-15: Goodhart Mitigation — Timing-Aware Ownership
**Target:** CONTEXT
**What:** Specify timing-aware sequenced ownership: if `goodhart_risk.yaml` exists before Plan 12 Part 0, implement per risk_level. If absent, implement provisional human-review gate. Add `implementation: Literal["provisional", "implemented"]` handshake field.
**Why:** 3.1e Plan 03/04 Phase 2 may not complete before Plan 12 Part 0 starts. Both branches need explicit specification.
**How:**
1. Add to CONTEXT Cross-Phase: Goodhart ownership sequence with both branches
2. Add `implementation` handshake field to goodhart_risk.yaml consumption contract
3. 3.1f Plan 03 LOC estimate depends on which branch Plan 12 took
**Impacts:** Plan 12, 3.1f Plan 03
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Cross-Phase Interface Integrity):** Timing mismatch is the real risk. Handshake field makes decision branch visible to 3.1f.

### P15-IMP-16: Cross-Phase Interface Questions Must Be Answered in CONTEXT
**Target:** CONTEXT
**What:** Proposed answering all 5 cross-phase interface questions definitively.
**Why:** Open questions after 14 passes are a defect.
**How:** (see P15-ADV-2-03 for corrected framing)
**Impacts:** Planning clarity for 3.1f
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Cross-Phase Interface Integrity):** 2 of 5 questions are implementation-dependent. Replaced by consolidation with definitive + provisional answers (P15-ADV-2-03).

<!-- ============================================================ -->
<!-- AREA 4: Orchestration Model (7 items) -->
<!-- ============================================================ -->

### P15-IMP-17: Sequential Execution Constraint — Session-Type Distinction
**Target:** CONTEXT
**What:** Replace blanket sequential constraint with session-type distinction. Headless `claude --print` MAY run in parallel when: (a) each session writes to `{session_id}/` subdirectory, (b) BaselineManager uses file locking, (c) circuit-breaker state is read-only during parallel execution.
**Why:** Serial execution of 51 workflows at 15-30 min each means 12-25h wall-clock.
**How:**
1. Replace execution constraint with conditional: Agent Teams sequential, headless parallel with 3 conditions
2. Add parallel execution row to Mode Capability Matrix
3. Plan 08: `max_parallel_headless: int = 1` (increment after isolation test)
**Impacts:** Plan 08, Mode Capability Matrix
**Research needed:** no — RESOLVED 2026-02-23: parallel `claude -p` is safe (stateless one-shot calls). Filesystem isolation via worktrees/subdirectories is standard practice. File locking needed for BaselineManager only.
**Confidence:** HIGH (upgraded from MEDIUM after research)
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Orchestration Architecture):** Enhanced with three specific parallel-safety conditions and anchor to Headless Platform Feature Verification Rule.

### P15-IMP-18: /vrs-test-suite Skill Decomposition
**Target:** CONTEXT
**What:** Proposed splitting into coordinator + 4 sub-skills.
**Why:** Monolithic skill unreliable for 8+ concerns.
**How:** (see P15-ADV-4-01 for corrected framing)
**Impacts:** Plans 09-11
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Orchestration Architecture):** Pre-optimizes unwritten skill. The /vrs-audit analogy fails — audit runs once, test suite runs 51 times. Real problem is context exhaustion from 51-workflow fan-out. Replaced by P15-ADV-4-01.

### P15-IMP-19: Mode-Specific Execution Profiles Instead of Conditional Logic
**Target:** CONTEXT
**What:** Three mode-specific profiles (interactive_investigation, headless_tool, headless_standard) dispatched by coordinator.
**Why:** Prompt-level conditionals degrade reliability. Profiles align with locked Tier-to-Run-Mode Binding.
**How:**
1. Three execution profiles as prompt templates in coordinator skill
2. Coordinator selects based on contract's run_mode
**Impacts:** Plans 09-11 implementation approach
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (Orchestration Architecture):** Fills gap in Plans 09-11 mode handling. Aligns with existing Mode Capability Matrix.

### P15-IMP-20: TeamManager Scope Boundary — Objective Enforcement
**Target:** CONTEXT
**What:** TeamManager is Pydantic BaseModel with no methods crossing Python/CC boundary. Prohibited: `send_*`, `spawn_*`, `shutdown`, `wait_*`. Add grep-based exit criterion.
**Why:** Current "remains a data model" language is aspirational, not prescriptive.
**How:**
1. Amend TeamManager Role Decision with specific prohibitions
2. Plan 05 exit criterion: "`grep -r 'def send' src/alphaswarm_sol/testing/` returns 0 matches on TeamManager"
**Impacts:** Plan 05 scope
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Orchestration Architecture):** Enhanced with prohibited method patterns and objective exit criterion.

### P15-IMP-21: SendMessage Delivery Validation for Debrief Scoring
**Target:** CONTEXT
**What:** Add `delivery_status: Literal["delivered", "phantom", "not_attempted"]` to DebriefResponse. Phantom debriefs scored as `applicable=False` with `degraded=True`.
**Why:** Without classification, phantom debriefs dilute signal.
**How:**
1. Plan 01: add delivery_status to DebriefResponse
2. Plan 05: after SendMessage + wait, check artifact. If absent: phantom
3. Plan 07: phantom debriefs → debrief dimensions `applicable=False`. Branch differently from not_attempted.
**Impacts:** Plan 01, Plan 05, Plan 07
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (Orchestration Architecture):** Well-specified. Plan 07 must branch phantom vs not_attempted differently.

### P15-IMP-22: PreToolUse Hook for Config-Driven Delegate Mode Enforcement
**Target:** CONTEXT
**What:** `delegate_guard.py` (PreToolUse, blocking, ~25 LOC) as 6th essential hook. Reads blocked list from config file, not hardcoded. Returns exit 2 on match.
**Why:** Prompt-based constraints are weakest enforcement.
**How:**
1. Config-driven: `delegate_guard_config.yaml` with `blocked_tools`, `blocked_patterns`, `allowed_reads`
2. 6th essential hook (blocking, PreToolUse)
3. Plan 09 exit: negative test (blocks .sol Read) AND positive test (permits .vrs/ Read)
**Impacts:** Plan 02 (hook count 5→6), Plan 09 enforcement
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Orchestration Architecture):** Enhanced: config-driven blocked list prevents maintenance trap. Positive + negative tests prevent false-blocking.

### P15-IMP-23: Compaction Preservation Protocol Consolidation
**Target:** CONTEXT
**What:** Consolidate 6 scattered compaction decisions into one section.
**Why:** Scattered specification increases implementation error risk.
**How:** Add "Compaction Event Protocol" section cross-referencing all 6 decisions.
**Impacts:** Documentation consolidation
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** cosmetic
**Status:** rejected
**Adversarial note (Orchestration Architecture):** Creates 7th maintenance location rather than reducing to 6. Right fix is cross-reference annotations within existing sections. Documentation hygiene, not architecture.

<!-- ============================================================ -->
<!-- AREA 5: Data Pipeline (Plans 01-03) (5 items) -->
<!-- ============================================================ -->

### P15-IMP-24: P0 Gate Structural Completeness Check
**Target:** CONTEXT
**What:** P0 must verify parsed output contains fields downstream plans consume: non-empty `bskg_query_events` (if BSKG used), `tool_sequence_with_timestamps`, non-null `tool_use_id`. Negative test: non-BSKG transcript produces `bskg_query_events == []` (not None).
**Why:** P0 can pass while silently producing empty fields. PostToolUse bug demonstrates this class of failure.
**How:**
1. P0 exit criteria: `to_observation_summary()` produces non-empty bskg_query_events on BSKG transcript
2. Negative test: non-BSKG transcript → `bskg_query_events == []`
3. ToolUseData entries have non-null tool_use_id (count nulls, HALT if >0)
**Impacts:** Plan 02 P0 gate
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (Pipeline Data Integrity):** Code-confirmed via PostToolUse bug history. Negative test is key addition.

### P15-IMP-25: ObservationSummary Interface Contract
**Target:** CONTEXT
**What:** Proposed GUARANTEED/CONDITIONAL/DERIVED taxonomy for ObservationSummary fields.
**Why:** Consumers implement inconsistent null-handling.
**How:** (see P15-ADV-5-01 for corrected framing)
**Impacts:** Plans 01, 04, 07, 08
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Pipeline Data Integrity):** New taxonomy adds consumer burden. Simpler fix: producer-side null-safety contract (`[]` not `None`). Replaced by P15-ADV-5-01.

### P15-IMP-26: SubagentData KNOWN_ABSENT Annotation Tier
**Target:** CONTEXT
**What:** Add KNOWN_ABSENT annotation tier to P14-ADV-1-01 convention. Format: `# KNOWN_ABSENT: {field} confirmed not in CC {schema} as of {date}. Source: {IMP ref}`. Apply to `task_description` and `parent_session_id`.
**Why:** PROVISIONAL ("uncertain") vs KNOWN_ABSENT ("confirmed missing") are semantically different. KNOWN_ABSENT fields should NOT generate P0 failures when absent.
**How:**
1. Add KNOWN_ABSENT tier with annotation format template
2. Apply to SubagentData.task_description and .parent_session_id in Plan 01/02
3. P0: if KNOWN_ABSENT field appears, document as CC platform change (don't block P0)
4. P0 exit criterion: "KNOWN_ABSENT fields absent (expected). If present: document, don't block."
**Impacts:** Plan 01, Plan 02
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Pipeline Data Integrity):** Enhanced with format template, P0 behavior for unexpected presence, and semantic distinction from PROVISIONAL.

### P15-IMP-27: Hook Health Check After Installation
**Target:** CONTEXT
**What:** ~15 LOC post-installation health check: fire one tool call, verify hook wrote expected output with correct field names.
**Why:** "Installed and not crashing" is insufficient (PostToolUse bug). Must verify output structure.
**How:**
1. Plan 02 deliverables: health check (~15 LOC) as part of deliverable 2 (before golden file snapshots)
2. Plan 02 exit criteria: "Hook health check passes. Observation file contains correct schema."
**Impacts:** Plan 02
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (Pipeline Data Integrity):** PostToolUse bug is direct historical evidence. Must run BEFORE golden file creation.

### P15-IMP-28: GroundTruthAdapter Error Handling for Uncatalogued Patterns
**Target:** CONTEXT
**What:** ~10 ground truth patterns with no catalog entry need `tier='uncatalogued'`. Update `NormalizedFinding.tier` Literal and accuracy reporting.
**Why:** Silently excluded 13% makes accuracy metrics misleading.
**How:**
1. Plan 01 NormalizedFinding: `tier: Literal["A","B","C","uncatalogued"]`
2. Plan 03 normalize(): return NormalizedFinding with tier='uncatalogued' (not None, not raise)
3. Plans 09-11 accuracy: `per_tier_accuracy` includes 'uncatalogued' bucket
4. Plan 03 exit criterion + test: uncatalogued pattern handled without crash
5. Model change and adapter change in same commit (atomicity)
**Impacts:** Plan 01, Plan 03, Plans 09-11
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Pipeline Data Integrity):** Enhanced with upstream model change, downstream accuracy dict, and atomicity requirement.

<!-- ============================================================ -->
<!-- AREA 6: Evaluation Quality (Plans 04-07) (6 items) -->
<!-- ============================================================ -->

### P15-IMP-29: 7-Move Reasoning — Manual Annotation Method
**Target:** CONTEXT
**What:** Before implementing per-move scoring, manually annotate 2 real transcripts with move boundaries. If <4 distinguishable, merge to observable subset.
**Why:** Taxonomy designed from theory. Real transcripts may not exhibit distinct phases.
**How:**
1. Plan 07 deliverable 0: annotate 2 transcripts. Move boundary criterion: "two moves distinguishable if they appear as clearly separate reasoning phases with different tool use or text content"
2. Contingency: if only 3 moves, reduce dimension count accordingly
**Impacts:** Plan 07, dimension registry, Plan 06 contracts
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** no
**Depends on plans:** Plan 02 (real transcripts)
**Classification:** structural
**Status:** confirmed
**Adversarial note (Empirical Validation Demand):** Correctly minimal validation demand (2 transcripts, ~1 hour). Not a duplicate of IMP-08 — IMP-29 is execution method, IMP-08 is governance gap.

### P15-IMP-30: Dimension Whitelist — Invert Default to active_dimensions
**Target:** CONTEXT
**What:** Contracts specify `active_dimensions: list[str]` (whitelist). Unlisted dimensions default to `applicable=False`. Core contracts: 8-12 dimensions. Standard: 4-6 or omit (receives zero scored).
**Why:** Current "all applicable unless filtered" requires 1,377 dimension entries across 51 contracts. Whitelist reduces to ~300.
**How:**
1. Dimension Registry: add `active_dimensions` whitelist default
2. Add `active_dimensions` to Schema Hardening Field Manifest
3. Plan 06: Core+Important contracts have explicit whitelists. Standard stubs may omit (zero scored).
4. Plan 07: iterate active_dimensions. Fallback: if field absent, iterate full registry (backward compat)
**Impacts:** Plan 06, Plan 07, dimension registry
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Empirical Validation Demand):** Enhanced with backward compatibility for existing 10 contracts and Schema Hardening Field Manifest impact.

### P15-IMP-31: Self-Consistency Gate Before Debate Protocol
**Target:** CONTEXT
**What:** Run single evaluator 3x on same transcript. If max std dev < 5pt: debate-optional. If 5-15pt: debate recommended. If > 15pt: evaluator instability — investigate prompt, don't enable debate.
**Why:** 51 workflows x 3 debate evaluations = 153 Opus calls. Self-consistency check on 1 transcript reveals if debate is necessary.
**How:**
1. Add self-consistency gate as locked sub-decision in Evaluator Debate Protocol
2. Add `consistency_class: Literal["stable", "recommended", "unstable"]` to CalibrationConfig
3. Plan 07 exit criterion: self-consistency gate passes for at least one Core workflow
4. Cross-reference P15-IMP-37: check runs during Phase 1 calibration
**Impacts:** Plan 07, Wave 6 wall-clock
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 07
**Classification:** structural
**Status:** enhanced
**Adversarial note (Empirical Validation Demand):** Enhanced with instability branch (> 15pt). Missing from original — more dangerous than cost argument.

### P15-IMP-32: DEFAULT-30 Dimensions Must Return applicable=False
**Target:** CONTEXT
**What:** `exploit_path_construction`, `arbitration_quality`, `evidence_weighing`, `investigation_depth` silently score DEFAULT-30 (no heuristic handler). Change to return `DimensionScore(applicable=False)`.
**Why:** DEFAULT-30 contaminates baselines and inflates GVS calibration denominator with zero-information signals.
**How:**
1. Plan 07: dimensions without handler return `applicable=False`
2. Add `has_handler: bool` to dimension registry
3. Plan 04 GVS: exclude non-applicable dimensions from grid search
4. Verify DimensionScore model has `applicable: bool = True` field — if absent, add to Plan 01
**Impacts:** Plan 04, Plan 07, baseline quality. Note: removing 4 dimensions from denominator will inflate overall scores — calibration baseline must be established AFTER this fix.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (Empirical Validation Demand):** Code-confirmed at reasoning_evaluator.py:371. Second-order: score inflation from denominator reduction — Plan 12 must run AFTER this fix.

### P15-IMP-33: REASONING_PROMPT_TEMPLATE {expected} and {observed} Wiring Gap
**Target:** CONTEXT
**What:** `{expected}` template variable has no wiring to Plan 06 rubric text. Three plans touch data flow but none owns end-to-end path. Additionally, `{observed}` is equally unwired.
**Why:** Zero invocations ever. Plumbing gap between Plans 06, 07, 08.
**How:**
1. Cross-Plan Dependencies: "Plan 08 passes `ground_truth_rubric` from contract to Plan 07 via `context['ground_truth_rubric']`. Plan 07 fills `{expected}`."
2. Plan 07 exit criteria: "Template fills BOTH `{expected}` AND `{observed}` from context dict. Test with and without rubric."
**Impacts:** Plans 06, 07, 08 data flow
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (Empirical Validation Demand):** Code-confirmed. `{observed}` equally unwired — exit criteria must cover both variables.

### P15-IMP-34: Heuristic Evaluator Mediocre Band Limitation
**Target:** CONTEXT
**What:** Document mediocre band compression at 53 as structural limitation of keyword matching.
**Why:** Prevent future heuristic fix proposals.
**How:** Add note to Known Code Issues.
**Impacts:** Documentation only
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** Plan 02
**Classification:** cosmetic
**Status:** rejected
**Adversarial note (Empirical Validation Demand):** Self-resolving limitation (Plan 07 LLM evaluator replaces heuristic). Already documented in 3.1e-CONTEXT.md. Documentation overhead without implementation value. If recurring proposals are the concern, IMP-01's Design Completion Gate handles it.

<!-- ============================================================ -->
<!-- AREA 7: Execution & Improvement Loop (Plans 08-12) (7 items) -->
<!-- ============================================================ -->

### P15-IMP-35: Headless-First Wave 6 Execution Order
**Target:** CONTEXT
**What:** Restructure Wave 6 to headless-first. Originally framed as "validates the full scoring pipeline."
**Why:** Headless-first reduces cost-at-risk for pipeline bugs.
**How:** (see P15-ADV-1-01 for corrected framing)
**Impacts:** Wave 6 execution order, Plans 09-11
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** reframed
**Adversarial note (Scope Reduction Coherence):** "Validates the full scoring pipeline" is false — headless-first validates only the headless pipeline. Interactive pipeline (debrief, SendMessage, debate) remains unvalidated. Replaced by P15-ADV-1-01 with interactive validation gate.

### P15-IMP-36: Split Plan 12 at Parts 0-1 / 2-5 Boundary
**Target:** CONTEXT
**What:** Near-duplicate of IMP-12.
**Confidence:** HIGH
**Classification:** structural
**Status:** rejected
**Adversarial note (Scope Reduction Coherence):** Duplicate of P15-IMP-12 which is more complete. Unique detail (Parts 2-5 text migration) absorbed into IMP-12 How step 5.

### P15-IMP-37: Sequential Calibration Anchor — Quality-Spread Agents
**Target:** CONTEXT
**What:** Start with 2 agents x 10 contracts = 20 sessions. If rho > 0.6: done. If [0.3, 0.6): expand to 72. If < 0.3: HALT. Agents must represent quality spread.
**Why:** 72 sessions expensive. 20 sufficient if agents have known quality spread.
**How:**
1. Sequential anchoring Phase 1: 2 agents x 10 contracts. Agents MUST represent quality spread (1 highest-quality from 3.1e Plan 02, 1 lowest-quality). If 3.1e not run, defer selection.
2. CalibrationConfig: `anchor_phase: Literal["partial", "full"]`
3. Re-validation default: Phase 1 (20 sessions) not full 72
**Impacts:** Plan 12 Part 0 cost reduction
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Scope Reduction Coherence):** At 13.3% precision with 2 arbitrary agents, rho will be near zero from corpus homogeneity, not evaluator failure. Agent selection MUST include quality-spread agents.

### P15-IMP-38: update_baseline() Bug Fix — Three-Condition AND Gate
**Target:** CONTEXT
**What:** Replace partial fix (`!= 'invalid_session'`) with three-condition AND gate: (a) SessionValidityManifest.valid == True, (b) status == 'completed', (c) effective_score() is not None. All three required.
**Why:** Partial fix permits baseline updates for `failed` and `timeout` sessions. Condition (c) prevents zero-scored baseline from all-inapplicable dimensions.
**How:**
1. Plan 08 deliverable 16: REPLACE existing partial fix text with three-condition guard (~3 LOC)
2. Negative test per condition: invalid session, failed status, None effective_score — baseline NOT updated
3. Exit criterion: "3 negative fixtures + 1 positive fixture"
**Impacts:** Plan 08
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Pipeline Data Integrity):** Three-condition AND REPLACES existing partial fix (not adds to). Condition (c) was missing from original.

### P15-IMP-39: Tag 3.2-Critical Workflows — Reporting Priority, Not Execution Override
**Target:** CONTEXT
**What:** Tag 8 audit-pipeline workflows as `3.2_critical: true`. Execute in natural tier (not Stage 1). Wave 6 Exit Report leads with these results.
**Why:** 3.2 readiness signal from reporting prioritization, not execution order override (which conflicts with headless-first).
**How:**
1. Tag `3.2_critical: true` on 8 workflows in Plans 09/10
2. Wave 6 Exit Report Section 1 = 3.2 critical path results
3. 3.2 readiness signal definition: 3 of 8 critical workflows score above tier threshold on CONCLUSION_SYNTHESIS and EVIDENCE_INTEGRATION
**Impacts:** Wave 6 exit reporting, 3.2 readiness timeline
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Scope Reduction Coherence):** Original conflicted with headless-first (both claimed Stage 1). Reframed as reporting priority, not execution ordering.

### P15-IMP-40: Experiment Ledger 'abandoned' Decision State
**Target:** CONTEXT
**What:** Add `"abandoned"` to ExperimentLedgerEntry.decision. Add `abandon_reason: str | None`. Convergence detection excludes abandoned entries.
**Why:** Circuit breaker HALT produces partial data with no valid state. Without "abandoned", partial experiments look like failed ones.
**How:**
1. Plan 01: add `"abandoned"` to decision Literal, add `abandon_reason: str | None = None`
2. Plan 12 Part 2: circuit breaker sets `decision: "abandoned"` with halt reason
3. Convergence: `exclude_abandoned: bool = True` parameter
4. Note: model change must land in 3.1c Plan 01 regardless of IMP-12 Plan 12 split (3.1f has type dependency)
**Impacts:** Plan 01 model, Plan 12
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Pipeline Data Integrity):** Enhanced with abandon_reason field, exclude_abandoned parameter, and cross-scope note for Plan 12 split.

### P15-IMP-41: Circuit Breaker Failure Taxonomy — Literal Enum
**Target:** CONTEXT
**What:** Replace free-text `failure_reasons[0]` matching with `InfrastructureFailureType` Literal enum. Classification at detection site (Plan 08), not circuit breaker (Plans 09-11).
**Why:** Free-text matching defeated by misspelling or rephrasing.
**How:**
1. Plan 01: `InfrastructureFailureType = Literal["hook_installation_failed", "contract_schema_invalid", "delegate_mode_violation", "session_timeout", "debrief_collection_failed", "scoring_pipeline_error", "unknown"]`. Use Literal (not Enum class) for Pydantic serialization.
2. EvaluationResult: `infrastructure_failure_type: InfrastructureFailureType | None = None`
3. Plan 08: classify at detection site. Circuit breaker reads typed field.
4. P14-IMP-18: tier-aware thresholds (3 for Core/Important, 5 for Standard)
5. Plan 09 exit: circuit breaker triggers on fixture with 3 consecutive identical types
**Impacts:** Plan 01, Plan 08, Plans 09-11. Note: must use same enum as IMP-13 FailureSignal to avoid 3.1f type mismatch.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** enhanced
**Adversarial note (Pipeline Data Integrity):** Literal not Enum for Pydantic compatibility. Classification at detection site prevents string→enum remapping in Plans 09-11.

<!-- ============================================================ -->
<!-- ADVERSARIAL CREATE ITEMS -->
<!-- ============================================================ -->

### P15-ADV-1-01: Interactive Pipeline Validation Gate Before Stage 3
**Target:** CONTEXT
**What:** Headless-first reorder (IMP-35) validates headless pipeline only. Add micro-validation between Stage 2 and Stage 3: run ONE interactive Core workflow in dry-run mode before committing to full Stage 3. Validates: SendMessage delivery, debrief_gate.py blocking, debrief collection, interactive DimensionScore output.
**Why:** Interactive pipeline has no validation checkpoint before expensive Stage 3-4 runs. /vrs-test-suite already has --dry-run mode.
**How:**
1. Wave 6: between Stage 2 and Stage 3, add "Interactive Pipeline Validation: `/vrs-test-suite --dry-run --tier core --workflow vrs-attacker`"
2. Gate: dry-run must produce conformant exit report with non-null debrief artifact
3. Stage 1-2 = headless pipeline valid. Dry-run gate = interactive pipeline valid. Both required before Stage 3.
**Impacts:** Wave 6 execution schedule
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** Plan 09 (--dry-run mode)
**Classification:** structural
**Status:** confirmed
**Adversarial note (ADV Validation):** Confirmed — concrete How, correct flags, no cross-group conflicts, complete fields. Dry-run gate is well-specified and verifiable.
**Source:** Adversarial review (Scope Reduction Coherence)
**Cross-references:** replaces: P15-IMP-35

### P15-ADV-2-01: Lightweight Empirical Permission Gates (replaces IMP-06)
**Target:** CONTEXT
**What:** Replace three-state override protocol with per-plan permission gates. Each plan implementing a 3.1e-vulnerable decision gets one-line check: "Before implementing [X], verify 3.1e [artifact] does not contradict. If it does, flag for human review."
**Why:** Pre-specifying falsification thresholds requires 3.1e data to calibrate. Human judgment at implementation point is the fix, not a protocol.
**How:**
1. Plan 07: "Before implementing debate, check 3.1e Plan 02 result file. If LLM scores show degenerate spread (implementer judgment), implement single-evaluator only."
2. Plan 07: "Before implementing 7-move scoring, check 3.1e Plan 02 results. If LLM_unreliable on all primary-tier, reduce to heuristic-only."
3. Plan 04: "GVS weight architecture is provisional. If 3.1e Plan 03/04 shows only query_coverage is informative, reduce to single-proxy."
4. NO global override protocol, formal states, or amendment process.
**Impacts:** Plans 04, 07 — sentence additions only
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 02 (artifact: 3.1e Plan 02 result file), Plan 04 (artifact: 3.1e Plans 03/04 results)
**Classification:** structural
**Status:** enhanced
**Adversarial note (ADV Validation):** Operationalize judgment criteria: Plan 07 debate gate → "if all LLM dimensions score within ±5pt of 50 = degenerate"; Plan 07 7-move gate → "if evaluation_complete=False on >50% of transcripts = unreliable"; Plan 04 GVS gate → "if query_coverage is sole dimension with correlation >0.3 while others <0.1 = single-proxy". Missing depends_on_plans added.
**Source:** Adversarial review (Cross-Phase Interface Integrity)
**Cross-references:** replaces: P15-IMP-06

### P15-ADV-2-02: Consumption Contracts With Fallbacks (replaces IMP-09)
**Target:** CONTEXT
**What:** Instead of pre-specified artifact schemas, define consumption contracts: expected path, minimum format ("YAML, any structure"), fallback if absent. Field names NOT specified — 3.1e Plan 05 owns schemas.
**Why:** 3.1e Plan 05 ("Extract Schemas From Reality") owns schema extraction. 3.1c pre-specifying field names constrains discovery.
**How:**
1. Add "3.1e Artifact Consumption" section (3 entries): failure_taxonomy.yaml (fallback: P14-IMP-23 categories), goodhart_risk.yaml (fallback: P14-IMP-24 human-review gate), LLM matrix (fallback: single-evaluator only)
2. Each entry: path, minimum format, fallback. Field names NOT specified.
3. Note: "3.1e Plan 05 owns schema. 3.1c amends when Plan 05 delivers."
**Impacts:** Plans 07, 12
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 07 (3.1e Plan 05 schema or fallback), Plan 12 (3.1e Plan 05 schema or fallback)
**Classification:** structural
**Status:** enhanced
**Adversarial note (ADV Validation):** Plans 07 and 12 need to know whether 3.1e Plan 05 has delivered. If absent by their start, they must use fallbacks. Missing depends_on_plans added for sequencing.
**Source:** Adversarial review (Cross-Phase Interface Integrity)
**Cross-references:** replaces: P15-IMP-09

### P15-ADV-2-03: Cross-Phase Consolidation Section (replaces IMP-16)
**Target:** CONTEXT
**What:** Add "Cross-Phase Interface Summary" (~25 lines) with 5 numbered subsections. Definitive answers for questions 1, 3, 5. Provisional answers with amendment triggers for questions 2, 4.
**Why:** Answers scattered across 7+ items. Consolidation without new specification.
**How:**
1. Five subsections: (1) 3.1f interfaces = EvaluationResult+WorkspaceManager+calibration artifacts (definitive). (2) EvaluationResult richness = provisional yes with FailureSignal (amend when Plan 08 implemented). (3) Plan 12/3.1f boundary = definitive per IMP-12. (4) Handoff formats = calibration artifacts definitive, LLM matrix provisional. (5) Improvement loop redundancy = none after IMP-12 (definitive).
2. Each cites source items. Provisional answers include amendment trigger.
**Impacts:** Planning clarity for 3.1f
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (ADV Validation):** Confirmed — consolidation without new specification, all fields complete, no conflicts.
**Source:** Adversarial review (Cross-Phase Interface Integrity)
**Cross-references:** replaces: P15-IMP-16

### P15-ADV-2-04: 3.1e-to-3.1c Minimum-Wait Sequencing Policy
**Target:** CONTEXT
**What:** Add sequencing policy: Plans 01-11 have no 3.1e dependency (run in parallel). Plan 12 Part 0 requires 3.1e Session 0 + Plan 01 (not full 3.1e). 3.1f requires 3.1c + 3.1e Plans 03/04 + 05.
**Why:** Individual fallbacks exist (IMP-14, IMP-15, ADV-2-02) but don't answer: "When can Plan 12 start?"
**How:**
1. Add to Cross-Phase Interface Summary (ADV-2-03): "3.1e Sequencing Policy" subsection
2. Each line cites minimum artifact, not full plan completion
**Impacts:** Plans 11-12 sequencing clarity
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** Plan 11 (3.1e Session 0 before Plan 12 Part 0 starts), Plan 12 Part 0 (3.1e Plan 01 before Part 0 starts)
**Classification:** structural
**Status:** enhanced
**Adversarial note (ADV Validation):** Sequencing policy declares when other phases can start. Missing depends_on_plans added as forward-reference dependencies for /msd:plan-phase readiness gates.
**Source:** Adversarial review (Cross-Phase Interface Integrity) — holistic gap

### P15-ADV-3-01: ImprovementHint target_component Discovered From Data (replaces IMP-04)
**Target:** CONTEXT
**What:** Defer `target_component` enum to Plan 12 Part 1 after observing real ImprovementHint content. Plan 07 produces raw hints with `suggested_change` text only. After 20+ real DimensionScores, classify observed targets empirically.
**Why:** Defining enum before any evaluations treats routing taxonomy as design fact. Most common failure mode may be absent from proposed enum.
**How:**
1. ImprovementHint: mark target_component as DEFERRED FIELD (v1 omits it)
2. Plan 12 Part 1: classify 20+ real hints by target, then define enum
3. Remove target_component from Plan 07 scope
**Impacts:** Plan 07 (removes deliverable), Plan 12 Part 1 (adds deliverable)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** Plan 07, Plan 12 Part 0
**Classification:** structural
**Status:** confirmed
**Adversarial note (ADV Validation):** Confirmed — DEFERRED FIELD pattern is correct, concrete tasks, proper depends_on_plans.
**Source:** Adversarial review (Empirical Validation Demand)
**Cross-references:** replaces: P15-IMP-04

### P15-ADV-4-01: Coordinator Context Exhaustion Boundary for 51-Run Fan-Out
**Target:** CONTEXT
**What:** /vrs-test-suite must manage 51 workflow runs without context exhaustion. Each workflow writes exit report to disk; coordinator reads only summary fields (workflow_id, overall_score, gate_pass).
**Why:** 51 exit reports inline will exhaust context window. /vrs-audit analogy fails — audit runs once, test suite runs 51 times.
**How:**
1. Locked decision: "Coordinator MUST NOT accumulate run-level output inline. Exit reports written to `.vrs/evaluations/{workflow_id}_{run_id}.json`. Coordinator reads schema-valid summary fields only."
2. Context ceiling row in Mode Capability Matrix: 51 headless, 20 interactive
3. Plan 09 exit: 10 headless runs without context exhaustion warnings
**Impacts:** Plans 09-11 skill design, Plan 08 wave sizes
**Research needed:** no — RESOLVED 2026-02-23: each `claude -p` gets own 200K context window (stateless). Context exhaustion is a coordinator problem only — coordinator reads summary fields from disk, not full reports inline. 51 headless runs produce ~5K tokens of summary data in coordinator.
**Confidence:** HIGH
**Prior art:** 1
**Prerequisite:** no
**Depends on plans:** Plan 09
**Classification:** structural
**Status:** confirmed
**Adversarial note (ADV Validation):** Confirmed — research-verified (R4), concrete locked decision, verifiable exit criterion. Primary reliability risk addressed.
**Source:** Adversarial review (Orchestration Architecture)
**Cross-references:** replaces: P15-IMP-18

### P15-ADV-4-02: Coordinator Failure Isolation Model
**Target:** CONTEXT
**What:** try/continue model for workflow failures. Each failure writes `{workflow_id}.failed.json`. Wave completion requires all workflows to have exit report OR .failed.json — no silent gaps.
**Why:** Single flaky workflow can abort 4-hour Wave 6 run. Partial results become ambiguous.
**How:**
1. Locked decision: "Workflow Failure Isolation: try/continue. Each failure writes .failed.json with error context."
2. Plan 08 runner: if .failed.json count > 20% of wave, escalate to human review
3. Plan 09 exit: coordinator handles simulated failure without aborting wave
**Impacts:** Plans 09-11, Plan 08
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** Plan 09
**Classification:** structural
**Status:** confirmed
**Adversarial note (ADV Validation):** Confirmed — try/continue model is concrete, testable, with escalation threshold.
**Source:** Adversarial review (Orchestration Architecture) — holistic gap

### P15-ADV-5-01: ObservationSummary Null-Safety Return Contract (replaces IMP-25)
**Target:** CONTEXT
**What:** `to_observation_summary()` must return typed-empty values (`[]` not `None`) for absent-but-optional fields. KNOWN_ABSENT fields return `None`. Distinguishes "agent didn't use feature" from "platform doesn't provide this."
**Why:** Silent `None` vs `[]` divergence is the most common source of hard-to-diagnose pipeline failures.
**How:**
1. Plan 02 deliverable 1: "All list-typed fields return `[]` when feature not used. KNOWN_ABSENT fields return `None`."
2. P0 exit: "No list-typed field is `None` on any real transcript."
3. Plan 04 GVS: consume `len(obs.bskg_query_events) == 0` as `applicable=False`, not `None` check
**Impacts:** Plan 02, Plans 04, 07, 08
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 02
**Classification:** structural
**Status:** confirmed
**Adversarial note (ADV Validation):** Confirmed — null-safety contract is concrete, three discrete execution points, correct flags.
**Source:** Adversarial review (Pipeline Data Integrity)
**Cross-references:** replaces: P15-IMP-25

### P15-ADV-5-02: Hook Installation Order Constraint in Plan 02
**Target:** CONTEXT
**What:** Hook health check (IMP-27) must run BEFORE golden file snapshot tests. If health check runs after, golden files may capture wrong data.
**Why:** Test integrity — golden files must be created from validated hook output.
**How:**
1. Plan 02 deliverables: health check is part of deliverable 2, runs before deliverable 4 (golden files)
2. Plan 02 exit criterion 5: "Prerequisite: hook health check passed"
**Impacts:** Plan 02 deliverable ordering
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (ADV Validation):** Confirmed — ordering constraint is clear, correct flags.
**Source:** Adversarial review (Pipeline Data Integrity) — holistic gap

## Convergence Assessment

**Total items:** 51 (41 original + 10 adversarial CREATE)
**Verdicts:** 11 confirmed, 17 enhanced, 7 reframed (terminal), 3 rejected (terminal), 10 CREATE, 3 pending synthesis
**Net actionable:** 41 (11 confirmed + 17 enhanced + 10 CREATE + 3 gap CREATEs)
**Structural improvements:** 49 (includes creative-structural)
**Cosmetic improvements:** 2 (IMP-23 rejected, IMP-34 rejected)
**Creative-structural:** 0
**Ratio:** ~4% cosmetic (2/51)

> Pass 15 produced substantive structural findings across all 7 areas. The highest-impact items are: (1) IMP-01 Design Completion Gate — stops further specification without data, (2) IMP-12 Plan 12/3.1f boundary — cuts 3.1c timeline by 40%, (3) ADV-4-01 context exhaustion boundary — addresses primary reliability risk. Cross-area duplicate detection caught IMP-36 (dup of IMP-12) and validated IMP-08/IMP-29 as non-duplicates. Key systemic risk: combined scope reductions (IMP-03 + IMP-37 + IMP-12) may hollow out calibration anchor. The 4% cosmetic ratio is far below convergence threshold — structural issues remain but are increasingly targeted and narrow.

<!-- ============================================================ -->
<!-- SYNTHESIS ITEMS -->
<!-- ============================================================ -->

### P15-SYN-01: Plan 07 Accumulates Three Unsequenced Pre-Implementation Gates
**Target:** CONTEXT
**What:** IMP-08 (7-move taxonomy validation: Sub-task 0), IMP-29 (manual annotation method: deliverable 0), and IMP-31 (self-consistency gate before debate) each add a "gate before expensive work" requirement to Plan 07 — all dependent on Plan 02 real transcripts. No item specifies: (a) what order these gates run in, (b) whether they share transcript inputs, (c) what happens if gates 1 and 2 pass but gate 3 fails (evaluator instability discovered mid-plan). The three gates form an implicit validation Phase 0 for Plan 07, but no item names it or gives it a recovery path.
**Why:** If gates are implemented as independent sub-tasks without an integrated sequence, Plan 07 implementers will discover the ordering question at implementation time. Gate 3 failure (evaluator instability, std dev > 15pt) invalidates the scoring approach that gates 1 and 2 enabled. Without a shared recovery path, a late-discovered failure cascades into Plan 07 scope ambiguity.
**How:**
1. Add "Plan 07 Validation Phase 0" as locked decision in CONTEXT: three gates run IN ORDER on the same 2 real transcripts from Plan 02 P0. Sequence: (a) 7-move boundary annotation (IMP-08/IMP-29), (b) dimension whitelist verification against annotated moves, (c) self-consistency run (IMP-31).
2. If gate (a) reduces moves to <4: dimension count shrinks; proceed. If gate (c) shows std dev > 15pt: HALT Plan 07 implementation, file evaluator instability diagnosis before resuming.
3. Plan 07 exit criterion update: "Phase 0 gates (a), (b), (c) all passed and recorded in `.vrs/plan07/phase0_results.yaml`."
**Impacts:** Plan 07 (unified Phase 0 sequencing), Plan 02 (Phase 0 must specify which 2 transcripts Plan 07 will use)
**Components:** P15-IMP-08, P15-IMP-29, P15-IMP-31
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 02 (real transcripts for Phase 0)
**Classification:** structural
**Status:** confirmed
**Adversarial note (ADV Validation):** Confirmed — Phase 0 sequencing is well-scoped, three gates IN ORDER with recovery paths. High-value synthesis.
**Source:** Post-review synthesis (cross-cutting)

### P15-SYN-02: P15 Adds Eight New Inter-Plan Dependencies Not Reflected in Cross-Plan Dependencies Table
**Target:** CONTEXT
**What:** The Cross-Plan Dependencies table is declared the "single source of truth for dependency ordering." P15 items create at minimum 8 new inter-plan dependencies that are not in the table: IMP-08 (Plan 02 → Plan 07: real transcripts for Phase 0), IMP-12 (Plan 12 → 3.1f: handoff artifact API), IMP-13 (Plan 01 → Plan 08: FailureSignal model), IMP-21 (Plan 01 → Plan 05 → Plan 07: delivery_status field chain), IMP-33 (Plan 08 → Plan 07: rubric context dict wiring), IMP-38 (Plan 08: effective_score dependency chain), IMP-41 (Plan 01 → Plans 08, 09-11: InfrastructureFailureType consistency with IMP-13 FailureSignal), ADV-3-01 (Plan 07 → Plan 12 Part 1: deferred target_component classification). No individual item updates the table; each assumes the table will be updated at merge time, but the instruction "Future improvement passes that discover new phantom fields must add them to this manifest" applies only to the Schema Hardening Field Manifest, not the dependency table.
**Why:** The table is used by `/msd:plan-phase` to establish task ordering. Missing rows mean plan tasks may be created without correct sequencing constraints, causing implementers to discover dependencies mid-wave.
**How:**
1. Add 8 rows to Cross-Plan Dependencies table in CONTEXT at implementation time (this item authorizes and lists them — implementer inserts at merge):
   - `02 → 07`: "Phase 0 transcripts for 7-move annotation and self-consistency" (YES)
   - `12 → 3.1f`: "WorkspaceManager + BaselineManager API documented for Variant Tester" (YES)
   - `01 → 08`: "FailureSignal model for EvaluationResult population" (YES)
   - `01 → 05 → 07`: "DebriefResponse.delivery_status field for phantom debrief handling" (YES, chain)
   - `08 → 07`: "ground_truth_rubric context dict key for {expected} template variable" (YES)
   - `01 → 08 → 09-11`: "InfrastructureFailureType Literal must match FailureSignal.signal_type mapping" (YES)
   - `07 → 12 Part 1`: "20+ real DimensionScores required before target_component enum defined" (NO — data dependency)
   - `01 → 09-11`: "ExperimentLedgerEntry abandoned state available in 3.1f consumer" (YES)
2. Add to Cross-Plan Dependencies table governance note: "Any improvement item creating a new inter-plan data flow must include a table row in its How steps."
**Impacts:** Cross-Plan Dependencies table, planning clarity for all affected plans
**Components:** P15-IMP-08, P15-IMP-12, P15-IMP-13, P15-IMP-21, P15-IMP-33, P15-IMP-41, P15-ADV-3-01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (ADV Validation):** Confirmed — 8 explicit table rows, governance note. Meta-item that prevents planning breakage.
**Source:** Post-review synthesis (cross-cutting)

### P15-SYN-03: CalibrationConfig Field Accumulation — Three Items Add Fields Without Compound Audit
**Target:** CONTEXT
**What:** IMP-02 adds `partial_rho_tp_only` and `anchor_diagnosis` to CalibrationConfig. IMP-31 adds `consistency_class`. IMP-37 adds `anchor_phase`. The existing CalibrationConfig (locked in CONTEXT.md) already has 7 fields: `evaluator_model`, `effort_level`, `debate_enabled`, `evaluator_prompt_hash`, `n_transcripts`, `spearman_rho`, `calibration_timestamp`. P15 adds 4 more fields across 3 separate items. No item checks for field name collisions, model size, or whether the combined model still has a coherent single responsibility.
**Why:** CalibrationConfig is consumed in Plan 12 Part 0 (write), Plan 12 Part 1 (re-validate), and startup guard (assert match). Each new field expands the assertion surface. `anchor_diagnosis` and `consistency_class` are evaluation diagnostic outputs — they may belong in a separate `CalibrationDiagnostics` model rather than the configuration artifact that controls re-run behavior. Mixing configuration fields with diagnostic fields in one model obscures which fields are inputs (must match current constants) vs outputs (recorded once, informational).
**How:**
1. Plan 01: split CalibrationConfig into two models: `CalibrationConfig` (inputs only: `evaluator_model`, `effort_level`, `debate_enabled`, `evaluator_prompt_hash`) and `CalibrationResult` (outputs: `n_transcripts`, `spearman_rho`, `partial_rho_tp_only`, `anchor_diagnosis`, `consistency_class`, `anchor_phase`, `calibration_timestamp`).
2. Plan 12 startup guard asserts on `CalibrationConfig` fields only (not `CalibrationResult` outputs).
3. Update IMP-02, IMP-31, IMP-37 How steps to target `CalibrationResult` instead of `CalibrationConfig` in implementation notes.
**Impacts:** Plan 01, Plan 12 Part 0 write path, Plan 12 startup guard
**Components:** P15-IMP-02, P15-IMP-31, P15-IMP-37
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (ADV Validation):** Confirmed — CalibrationConfig/CalibrationResult split is well-specified, correct input/output separation.
**Source:** Post-review synthesis (cross-cutting)

<!-- ============================================================ -->
<!-- CASCADE GAP ITEMS -->
<!-- ============================================================ -->

### P15-CSC-01: IMP-32 Score Inflation Makes Pre-Existing Baseline Entries Incomparable
**Target:** CONTEXT
**What:** IMP-32 (confirmed) changes 4 dimensions from DEFAULT-30 to `applicable=False`, reducing the scoring denominator and inflating `effective_score()` for all sessions. Any baseline entries written BEFORE IMP-32 is merged will use the old denominator and will be systematically lower than entries written after. If Plan 12 runs calibration anchor on a mix of pre- and post-IMP-32 baseline entries, Spearman rho will reflect denominator change rather than agent quality.
**Why:** The baseline is keyed by `(workflow_id, run_mode, debate_enabled, effort_level)` per existing locked decisions. Denominator version is not a key dimension. Post-IMP-32 sessions will appear "better" than pre-IMP-32 sessions for the same agent on the same contract, creating false regression signals and contaminating the calibration anchor.
**How:**
1. Add to IMP-32 CONTEXT text: "BREAKING CHANGE: merge of this fix MUST be followed by `alphaswarm evaluation reset-baseline` clearing all prior entries. Plan 12 Part 0 must run after this reset."
2. Add `scoring_denominator_version: int = 1` to `BaselineKey` model in Plan 01. Increment to 2 when IMP-32 merges.
3. BaselineManager: on load, reject entries with `scoring_denominator_version != current`. Log count of rejected entries.
4. Plan 12 Part 0 exit criterion: "Baseline empty or all entries have current scoring_denominator_version."
**Impacts:** Plan 01 (BaselineKey), Plan 08 (BaselineManager), Plan 12 Part 0
**Trigger:** P15-IMP-32
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 01 (BaselineKey model), Plan 08 (BaselineManager load path)
**Classification:** structural
**Status:** confirmed
**Adversarial note (ADV Validation):** Confirmed — scoring_denominator_version is concrete, detects real cascade risk from IMP-32.
**Source:** Post-review synthesis (cascade)

### P15-CSC-02: IMP-38 Condition (c) + IMP-30 "Zero Scored" Standard Stubs Create Unresolvable Sub-Wave Gate Counts
**Target:** CONTEXT
**What:** IMP-38 (enhanced) adds condition (c) to update_baseline(): `effective_score() is not None`. IMP-30 (enhanced) says Standard stubs that omit `active_dimensions` receive "zero scored" — meaning all dimensions are `applicable=False`, and `effective_score()` returns `None`. When Plans 09-11 run Standard-tier headless workflows using stub contracts, these sessions will: complete without error, pass SessionValidityManifest conditions (a) and (b), but fail condition (c), and therefore not update the baseline. Sub-wave gate counts in Plans 09-11 define passage as "N workflows completed" — but IMP-38's condition (c) means some "completed" workflows don't contribute to the baseline. The gate definition becomes ambiguous: does "completed" mean attempted, or baseline-updated?
**Why:** Plans 09-11 will silently produce zero-contributing runs for Standard stubs. Wave 6 exit reports may show "51 workflows completed" while the baseline has entries only for Core and Important tiers. Plan 12 calibration anchor uses baseline data — if Standard tier is systematically absent, sample sizes are wrong and rho calculations exclude 50% of the workflow population.
**How:**
1. Add `baseline_update_status: Literal["updated", "skipped_null_score", "skipped_invalid", "skipped_failed"]` to EvaluationResult in Plan 01.
2. Plans 09-11 sub-wave gate counts: distinguish "workflow attempted" from "baseline updated." Gate passage requires N baseline-updated results (not N attempted).
3. IMP-30: Standard stubs with omitted `active_dimensions` should receive a minimal sentinel dimension (e.g., `task_completion`) to ensure at least one scoreable dimension exists, preventing null effective_score. OR document that Standard stubs explicitly do not contribute to baseline, and gate counts for Standard sub-wave use "attempted" not "updated."
4. CONTEXT: add decision "Standard-tier stub contracts are evaluated for coverage tracking only; they do not contribute to baseline. Sub-wave gate counts for Standard tier use attempted-count, not baseline-updated-count."
**Impacts:** Plan 01 (EvaluationResult), Plans 09-11 (gate count definition), Plan 12 (sample size assumptions)
**Trigger:** P15-IMP-38
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Depends on plans:** Plan 01 (EvaluationResult model)
**Classification:** structural
**Status:** confirmed
**Adversarial note (ADV Validation):** Confirmed — gate count ambiguity is real, Standard stubs baseline exclusion is correct resolution.
**Source:** Post-review synthesis (cascade)

### P15-CSC-03: IMP-13 FailureSignal and IMP-41 InfrastructureFailureType Are Parallel Taxonomies With No Defined Mapping
**Target:** CONTEXT
**What:** IMP-13 (enhanced) creates `FailureSignal.signal_type: Literal["below_threshold", "high_variance", "evaluator_disagreement", "infrastructure_failure"]` — 4 values, taxonomy-independent, for 3.1f consumption. IMP-41 (enhanced) creates `InfrastructureFailureType: Literal["hook_installation_failed", "contract_schema_invalid", "delegate_mode_violation", "session_timeout", "debrief_collection_failed", "scoring_pipeline_error", "unknown"]` — 7 values, infrastructure-specific, for circuit breaker routing. IMP-41 notes "must use same enum as IMP-13 FailureSignal to avoid 3.1f type mismatch." But the two enums are structurally different: IMP-13's `infrastructure_failure` is a single catch-all, while IMP-41 provides 7 distinct subtypes. The "same enum" instruction is impossible as written — they have different cardinalities and semantics.
**Why:** If Plan 01 implements both independently, Plan 08 will need to map `InfrastructureFailureType` values to `FailureSignal.signal_type` values, but no mapping is specified. 3.1f consuming `failure_signals` will receive `signal_type="infrastructure_failure"` without knowing whether the root cause was a hook failure, schema error, or timeout — losing the diagnostic specificity that IMP-41 was designed to provide.
**How:**
1. Resolve the relationship explicitly in Plan 01: `FailureSignal` remains the 4-value cross-phase interface (IMP-13). `InfrastructureFailureType` is the 7-value internal classification (IMP-41). Define a static mapping: `INFRA_TO_SIGNAL: dict[InfrastructureFailureType, FailureSignal.signal_type]` where all 7 infra types map to `"infrastructure_failure"` (the catch-all).
2. Plan 08: when setting `infrastructure_failure_type`, also append `FailureSignal(signal_type="infrastructure_failure", detail=infrastructure_failure_type)` to `failure_signals`. Add `detail: str | None = None` to FailureSignal for this purpose.
3. 3.1f consumes `FailureSignal.signal_type` for routing, and `FailureSignal.detail` for diagnosis. No 3.1f code needs to know `InfrastructureFailureType` values.
4. Remove the ambiguous "must use same enum" note from IMP-41 and replace with this mapping specification.
**Impacts:** Plan 01 (both models + mapping), Plan 08 (population logic), 3.1f Plan 01 (consumption contract)
**Trigger:** P15-IMP-41
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** none
**Classification:** structural
**Status:** confirmed
**Adversarial note (ADV Validation):** Confirmed — mapping model resolves type hierarchy incompatibility, detail field preserves diagnostic specificity for 3.1f.
**Source:** Post-review synthesis (cascade)

## Post-Review Synthesis
**Items created:** P15-SYN-01, P15-SYN-02, P15-SYN-03, P15-CSC-01, P15-CSC-02, P15-CSC-03
**Key insight:** The most consequential cross-cutting gap is the Cross-Plan Dependencies table not being updated to reflect 8 new inter-plan data flows introduced by P15 items — this threatens wave execution ordering at implementation time. The most dangerous cascade is P15-CSC-03: IMP-13 and IMP-41 instruct "use the same enum" for two structurally incompatible type hierarchies, which will cause a silent type mismatch between 3.1c's internal failure classification and 3.1f's cross-phase interface unless an explicit mapping model is defined in Plan 01.
