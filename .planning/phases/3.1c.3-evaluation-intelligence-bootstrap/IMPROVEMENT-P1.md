# Improvement Pass 1

**Date:** 2026-03-02
**Phase:** 3.1c.3
**Status:** reviewed

## Pipeline Status

| Stage | Count | Items |
|-------|-------|-------|
| Confirmed | 17 | P1-IMP-02,03,04,06,09,10,13,14,17,19,20,22,23,24,25,27,29 |
| Enhanced | 11 | P1-IMP-01,05,07,08,11,15,16,18,21,26,28 |
| Reframed | 1 | P1-IMP-12 → P1-ADV-21 |
| Created | 1 | P1-ADV-21 (neutral schema owner) |
| Rejected | 0 | — |
| Prerequisites | 7 | P1-IMP-01,02,03,05,07,18; P1-ADV-21 |
| Research needed | 3 | P1-IMP-13,17,28 |

**Total:** 37 items (29 original + 1 ADV-CREATE + 3 SYN + 4 CSC)
**Net actionable:** 37 (0 rejected)
**Pipeline:** [discuss] ~ → [improve] ✓ → [pre-impl] ! → [research] ~ → [implement] — → [plan] — → [execute] —
**Next:** /msd:resolve-blockers 3.1c.3 — 7 prerequisites + 3 research items

## Improvements

### P1-IMP-01: Plan 10 "Agent Interview Integration" Assumes a Non-Existent Automated Debrief Pipeline
**Target:** PLAN-10
**What:** Plan 10 interview integration emits interview_questions output with no named consumer in any downstream plan. The debrief pipeline that would consume it was manual in 3.1c.2 and is not specified in Plans 11-12.
**Why:** Dead output is worse than no output — it creates a false impression of pipeline integration while the data accumulates unread. Splitting into a gated subtask preserves the dead-output problem inside the gate.
**How:** 
1. In Plan 10 Task (interview integration), add a verify step: name the downstream plan and task that reads interview_questions. If none exists, mark output as observability artifact only (not pipeline input).
2. Add a done criterion: "interview_questions.json is either (a) consumed by a named Plan 11/12 task with explicit file path, or (b) documented as human-readable artifact with no automation dependency."
3. Gate the automation subtask on debrief protocol existence, with log message citing the blocking plan/task.

### P1-IMP-02: Plan 10 Activation Threshold Is Circular — Per-Move Scores Don't Exist Until Plan 02 Ships
**Target:** PLAN-10
**What:** Plan 10's `is_active()` gate is "3+ results with per-move scores." Execution feedback finding #1 states: "per-move scores don't exist yet (Plan 02 builds them)." Plan 10 depends on Plan 02, but the activation gate does not reference this dependency explicitly. If Plan 02 is not yet complete when evaluation results accumulate, the gate condition `has_per_move_scores` will never become true regardless of result count.
**Why:** A gate that can never open because its input doesn't exist yet creates a silent failure mode: the engine appears inactive for legitimate reasons (insufficient data) when the real reason is a missing upstream deliverable. This makes debugging harder and the activation state untrustworthy. The gate condition should be split into two independent sub-conditions: `results_count >= 3` (data volume) AND `per_move_scores_available()` (infrastructure readiness), and the plan must explicitly state that the second condition depends on Plan 02 completion.
**How:** 
1. In Plan 10 frontmatter `depends_on`, verify Plan 02 is listed. If not, add it.
2. In the `is_active()` implementation task, change the gate logic from a single combined condition to two explicit checks with separate log messages: `"Waiting for data volume (need 3+)"` vs `"Waiting for per-move score infrastructure (Plan 02)"`. This makes the inactive reason observable at runtime.
3. Add a done criterion to the `is_active()` task: "running `engine.is_active()` with 3 results but no per-move scores returns `False` with reason `'per_move_scores_unavailable'`, not `'insufficient_data'`."
**Impacts:** Plan 10 task ordering — the is_active() task must be written after Plan 02 is confirmed complete
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — feature-flag gating on upstream readiness is standard; the specific framing is new here
**Prerequisite:** yes — Plan 02 per-move score output must be finalized before Plan 10 gate logic is implemented
**Status:** confirmed
**Origin:** NOVEL — execution_feedback finding #1 directly contradicts Plan 10's is_active() gate; no prior passes needed to surface this

### P1-IMP-03: Plan 11 Dependency Chain Is Unrealistically Deep — 4 Upstream Plans, Any One Can Block
**Target:** PLAN-11
**What:** Plan 11 depends on Plans 03, 04, 08, and 10 — the deepest dependency chain in the phase. Plan 10 itself has activation issues (IMP-01, IMP-02). Plan 11's `is_active()` gate adds "5+ results + coverage radar active" on top. This creates a scenario where Plan 11 cannot activate until every upstream plan has shipped AND coverage radar is generating data. With only 4 real evaluation observations (execution feedback finding #1), the 5+ threshold is barely reachable even if all upstream plans are perfect.
**Why:** A 4-deep dependency chain with a data threshold that barely exceeds the current observation count means Plan 11 has near-zero probability of being exercised during this phase. The plan is not wrong in intent — a planning bridge that knows what tests have run is genuinely useful — but shipping it in 3.1c.3 as a dependent-of-dependents with a 5-result gate is premature. This is the classic mistake of building the top layer of a pyramid before the base is load-bearing. Either (a) reduce the dependency to Plan 08 only (minimal viable bridge) or (b) explicitly mark Plan 11 as a Phase 3.1c.4+ plan.
**How:** 
1. In Plan 11 frontmatter, add a `risk: "HIGH — blocked until Plans 03, 04, 08, 10 all active; with 4 real observations, 5+ threshold may not be met in 3.1c.3"` field.
2. Create a minimal-viable variant task: Plan 11 Task 1 should be a stripped version that only reads progress.json (from Plan 08) and ROADMAP.md, and writes static suggestions to planning-suggestions.json — no dependency on Plans 03/04/10. Gate this variant at `results_count >= 3` (not 5+). The full adaptive version (with scenario_synthesizer integration from Plans 03/04 and recommendation engine from Plan 10) becomes Task 2, gated at `results_count >= 5 AND plans_03_04_10_active`.
3. Add a done criterion to Task 1: "with exactly 3 results and no coverage radar, `planning_bridge.is_active()` returns True and `planning-suggestions.json` contains at least one non-empty suggestion derived from progress.json data alone."
**Impacts:** Plan 11 confidence: LOW-MEDIUM remains appropriate but should be noted as "likely Phase 3.1c.4 for full activation"
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 1 — planning-aware test bridges are rare; the simplification pattern is general
**Prerequisite:** yes — Plan 08 progress.json format must be stable before Plan 11 Task 1 can be written
**Status:** confirmed
**Origin:** NOVEL — the dependency depth and observation count gap are visible from execution_feedback + plan structure; not derivable from prior passes

### P1-IMP-04: Plan 11 Planning Bridge Invokes GSD CLI Tools That Can't Find Decimal-Numbered Phases
**Target:** PLAN-11
**What:** Plan 11 mentions "experiment-before-continue protocol" and integration with the MSD/GSD planning system. Execution feedback finding #3 is explicit: "`gsd-tools.cjs find-phase '3.1c.2'` returned `found: false`." If the planning bridge generates suggestions that reference phase identifiers like "3.1c.3" and those identifiers cannot be resolved by the GSD CLI, any CLI-invoked actions (like `/msd:insert-phase`) will silently fail.
**Why:** The bridge outputs `planning-suggestions.json` which is described as suggestions, not auto-executed (Decision D-7). However, if the suggestions contain phase references that the CLI cannot resolve, a human following the suggestion will hit the same `found: false` error — making the output not just unhelpful but actively misleading. The bridge should either (a) avoid emitting CLI-invocable phase references until decimal phase support is verified, or (b) emit plain-text descriptions with a caveat that GSD CLI requires the phase to be created first.
**How:** 
1. In Plan 11's suggestions output task, add an action step: "before emitting any phase reference in planning-suggestions.json, verify the phase identifier resolves via `gsd-tools.cjs find-phase`; if it returns `found: false`, emit the suggestion as `type: manual_action` with `cli_status: unresolvable` rather than `type: cli_action`."
2. Add a done criterion: "when the bridge generates a suggestion referencing phase '3.1c.3', the output JSON shows `cli_status: unresolvable` (or the equivalent) rather than a bare phase name that implies CLI executability."
3. Cross-reference execution_feedback finding #3 in the plan's assumptions section so the executor knows this is a known broken surface.
**Impacts:** Plan 11 output format — suggestions JSON schema needs a `cli_status` field
**Research needed:** no — execution feedback is direct evidence
**Confidence:** HIGH
**Prior art:** 3 — graceful degradation when CLI tools fail is a standard pattern
**Prerequisite:** no — the fix is additive to Plan 11's output schema
**Status:** confirmed
**Origin:** NOVEL — execution_feedback finding #3 directly contradicts Plan 11's implicit assumption about GSD CLI capability; no prior passes needed

### P1-IMP-05: Plan 12 "Re-Run Evaluation" Step Assumes evaluation_runner Is the Canonical Execution Path — It Is Not
**Target:** PLAN-12
**What:** Plan 12 "Re-Run Evaluation" step silently passes when the original failure was sourced from an Agent Teams session (not evaluation_runner), producing an `applied_unverified` status with no follow-up gate.
**Why:** The hotfix protocol's done criteria include "evaluation re-runs successfully," but that criterion is meaningless when the re-run uses a different execution path than the original failure. Unverified hotfixes accumulate silently.
**How:** 
1. In Plan 12, Task for re-run step: add precondition check — inspect observation JSON for `execution_path` field. If value is `agent_teams`, runner-based re-run is structurally non-equivalent.
2. On path mismatch: emit `VERIFICATION_PATH_MISMATCH` in hotfix record. Block promotion to `applied` status.
3. Define escalation path: `applied_unverified` hotfixes must be reviewed and signed off in the next calibration batch before they can count toward done criteria.
4. Add to Plan 12 done criteria: "No hotfix remains in `applied_unverified` state at phase close without explicit sign-off."

### P1-IMP-06: Plan 12 Hotfix Safety Scope ("test infrastructure only") Is Not Enforceable by File-Count Alone
**Target:** PLAN-12
**What:** Domain Decision D-6 states "Hotfixes ONLY for test infrastructure, patterns, evaluation contracts — NEVER production agent prompts." Plan 12 implements this as "max 1 file, < 20 LOC" guardrails. These are size constraints, not scope constraints. A subagent instructed to fix "test infrastructure" can trivially modify `src/alphaswarm_sol/skills/registry.yaml` (a production file) in under 20 LOC and it would pass the size guardrail while violating D-6. Execution feedback finding #5 confirms that "prompt-based restrictions + post-hoc validation" is the working two-layer pattern — but Plan 12 appears to rely on size guardrails alone.
**Why:** D-6 is a hard constraint. Violations ship broken production code. The gap between "this is a safety rule" and "the enforcement mechanism actually prevents violations" is exactly where real incidents happen. Size-based guardrails prevent large changes; they do not prevent targeted dangerous changes. The fix is to add a path whitelist (only files under `tests/`, `src/alphaswarm_sol/testing/`, `vulndocs/`, or similarly scoped directories) as a second enforcement layer, plus post-hoc validation that checks the modified file path against the whitelist before committing.
**How:** 
1. In Plan 12's hotfix execution task, add an action step: "before spawning the hotfix subagent, construct the subagent prompt to include an explicit allowed-paths list: `tests/`, `src/alphaswarm_sol/testing/`, `vulndocs/` — same two-layer pattern as isolation enforcement from 3.1c.2."
2. In the post-hotfix validation step (before commit), add a path check: parse the git diff of the subagent's work; if any modified file path falls outside the allowed directories, revert the change, log the violation as `scope_violation`, and set hotfix status to `REJECTED`.
3. Add a done criterion: "a test demonstrates that a hotfix subagent that attempts to modify `src/alphaswarm_sol/skills/registry.yaml` is rejected at the post-hotfix validation step with status `scope_violation`, and the file is reverted."
**Impacts:** Plan 12 — adds one validation task; increases confidence that D-6 is actually enforced
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — path-based allowlists for automated changes are a standard CI safety pattern; the combination with subagent prompting is the novelty
**Prerequisite:** no — additive to existing Plan 12 structure
**Status:** confirmed
**Origin:** NOVEL — the gap between D-6 policy and Plan 12's size-only guardrails is visible from the domain section and plan description without any prior pass artifacts

### P1-IMP-07: Plans 10-12 Collectively Assume 3.1c.3 Has Enough Evaluation Data — It Does Not Yet
**Target:** PLAN-10
**What:** Plans 10-12 have zero scored observations at phase start. Bootstrap fixtures are needed, but must represent the actual schema variants that will appear in production — including the degraded path (TRANSCRIPT_UNAVAILABLE, None per-move scores) not just the ideal path.
**Why:** Fixtures that look like ideal-path outputs allow Plan 10-12 integration tests to pass in CI while real evaluations produce degraded data that the code has never handled. This inverts the purpose of bootstrap testing.
**How:** 
1. Add a bootstrap fixtures task to Plan 10 Task 1 (before integration tests).
2. Create 3 fixture files: one ideal-path (all per-move scores populated), one degraded-path (degradation_reason set, per-move scores None), one partial-path (some moves scored, some None).
3. All downstream Plan 10-12 integration tests MUST pass with all three fixture types before the plan is marked complete.
4. Done criterion: "fixtures cover ideal, degraded, and partial schema variants; integration tests pass all three."

### P1-IMP-08: Plan 01 Silently Fails for Agent Teams Teammates — Architectural Mismatch
**Target:** PLAN-01
**What:** Plan 01 deploys hooks that fire only in the orchestrator session. Downstream modules (Plans 02-06) will consume orchestrator-view events and incorrectly treat them as agent reasoning data, unless the field provenance is explicit.
**Why:** Without a schema manifest, each downstream plan author independently discovers which fields are empty for teammate sessions, producing inconsistent fallback behaviors across 5 plans.
**How:** 
1. Plan 01 Task (hook deployment) done criteria must include: produce a hook_output_manifest.json specifying for each output field: data_source (orchestrator_session | teammate_session | unavailable), population_rate (always | sometimes | never), and fallback_value.
2. Test both spawn paths (Task() subagent and TeamCreate worktree) explicitly in Plan 01 verify steps.
3. Plans 02-06 must cite hook_output_manifest.json fields when specifying their input contracts — this is a PREREQUISITE gate, not a documentation note.

### P1-IMP-09: Env-Var Hook Activation Will Silently No-Op in Teammate Sessions
**Target:** PLAN-01
**What:** Plan 01 states hooks are "controlled by evaluation contracts (not always-on)." The mechanism for this control is unspecified in the plan description, but execution feedback from 3.1c.2 confirms that env-vars (`_GUARD_PROFILE`, `DELEGATE_GUARD_CONFIG`) set in the main session do NOT propagate to Agent Teams child processes. If Plan 01's hook activation mechanism uses env-vars (the natural implementation choice for "not always-on"), it will silently produce no hook events in teammate sessions — the exact sessions being evaluated.
**Why:** "Silently no-op" is the worst failure mode. The verification step ("confirm JSONL file is produced with correct ObservationRecord schema") will still pass if the orchestrator emits any events, masking the fact that teammate-session hooks never fired. The plan has no verification that hooks actually fire during evaluation sessions specifically, only that hooks fire in some session.
**How:** 
1. In Plan 01, Task for JSONL writer implementation: add an explicit action step — "Document the hook activation mechanism. If using env-vars: add a note that env-var activation does NOT propagate to Agent Teams worktree-isolated processes. Provide an alternative mechanism (e.g., `.vrs/eval-session-active` sentinel file checked in a PreToolUse hook body, which IS evaluated per-invocation in any session that runs a tool)."
2. Add a verification step to Plan 01: "After deploying hooks, run an Agent Teams session with one teammate. Confirm EITHER (a) hook events appear for that teammate, OR (b) the plan's documentation explicitly states teammate hook events are not captured and downstream consumers are aware of this."
**Impacts:** Plan 01 verification gap closes; Plans 04-06 (intelligence modules consuming hook data) need updated input assumptions
**Research needed:** no — directly observed in 3.1c.2 execution
**Confidence:** HIGH
**Prior art:** 3 — env-var scoping is well-understood; the specific Claude Code / worktree propagation behavior is empirically established here
**Prerequisite:** no
**Status:** confirmed
**Origin:** NOVEL — empirical finding from execution feedback, not deducible from reading Plan 01 alone

### P1-IMP-10: Plan 02 Has No Fallback When Transcript Input Is Unavailable
**Target:** PLAN-02
**What:** Plan 02 defines a `reasoning_decomposer.py` that "takes a transcript + evaluator output and produces per-move scores." The plan depends on Plan 01 for transcripts. Execution feedback from 3.1c.2 proves that in the primary evaluation mode (Agent Teams + worktree isolation), transcripts have `TRANSCRIPT_UNAVAILABLE` status. Plan 02 has no stated behavior for when its required input is absent — no fallback, no graceful degradation, no documentation of when per-move scoring is feasible.
**Why:** Without a defined behavior for unavailable transcripts, the decomposer will either throw an exception (crashing the evaluation pipeline) or silently return empty scores (causing intelligence modules in Plans 03-06 and Plan 10 to operate on zero signal). Neither outcome is acceptable. The "canonical transcript schema" Plan 02 claims to define will be aspirational for Agent Teams evaluations — the schema will exist but its fields will be empty for the primary use case.
**How:** 
1. Add to Plan 02 frontmatter `must_haves`: "reasoning_decomposer.py MUST define a degraded-mode behavior when transcript is None or TRANSCRIPT_UNAVAILABLE. Degraded mode returns a ReasoningDecomposerResult with all move scores = None and a populated `degradation_reason` field. Consumers MUST NOT treat None scores as 0."
2. Add a Task in Plan 02 specifically for transcript source enumeration: "Before implementing per-move scoring, enumerate which transcript sources are available per spawn path: (a) Task() subagent — what fields are populated? (b) Agent Teams teammate — what fields are populated? Use this as the implementation contract for the decomposer's input handling."
3. Add a done criterion: "Unit test covers the TRANSCRIPT_UNAVAILABLE input case and asserts degraded-mode output (not exception, not zero scores)."
**Impacts:** Plan 02 confidence MEDIUM → stays MEDIUM but failure mode is bounded; Plan 10 (recommendation system consuming per-move scores) needs awareness that scores may be None
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — graceful degradation / null-object patterns are standard; the specific application here is domain-specific
**Prerequisite:** no — this is a design constraint that must be established before Plan 02 implementation begins
**Status:** confirmed
**Origin:** NOVEL — directly caused by execution feedback showing TRANSCRIPT_UNAVAILABLE; not deducible from Plan 02 text alone

### P1-IMP-11: Worktree Cleanup Racing Hook Capture — Ordering Constraint Missing
**Target:** PLAN-01
**What:** JSONL transcript output path is worktree-relative; if worktree teardown races hook buffer flush, written data is incomplete or lost even if the path is later corrected.
**Why:** Silent data loss in observation artifacts invalidates downstream intelligence modules (Plans 02-08 all consume these). The bug is non-obvious because the file exists but is truncated.
**How:** 
1. In Plan 01, hook output path: set `TRANSCRIPT_PATH` to `$PROJECT_ROOT/.vrs/observations/<session_id>/transcript.jsonl` — never relative to `$WORKTREE_ROOT`.
2. Add explicit flush barrier in hook teardown: hook must call `fsync` (or equivalent) and emit a sentinel `{"type":"TRANSCRIPT_END"}` record before signaling completion.
3. In Plan 01 done criteria: add assertion — `TRANSCRIPT_PATH` resolves to a path that does NOT contain any active worktree directory prefix.
4. Add integration test: create worktree, write partial JSONL via hook, trigger teardown, verify file at project-root path is complete (sentinel present).

### P1-IMP-12: Plan 02 "Canonical Transcript Schema" Ownership Claim Is Premature
**Target:** PLAN-02
**What:** Plan 02 states it "defines the canonical transcript schema that all upstream producers (hooks, JSONL parser, evaluation runner) must conform to." This is an inversion of dependency direction. The producers (hooks in Plan 01, evaluation runner in the existing harness) exist before Plan 02. Plan 02 is written as if it defines the schema that producers must conform to — but if producers are already running (Plan 01 executes in Wave 1, Plan 02 in Wave 1 as well but after Plan 01), the schema is defined by what producers emit, not what Plan 02 wishes they emit.
**Why:** If Plan 02 defines the schema AFTER Plan 01 deploys hooks, there are two outcomes: (a) the schema matches what Plan 01 produces — in which case Plan 02's claim is redundant and documentation-only, or (b) the schema doesn't match — in which case Plan 01 must be retrofitted, creating a dependency cycle within Wave 1. The correct design is: Plan 01 defines the JSONL event schema as part of hook deployment, and Plan 02 consumes that schema. The "canonical" authority should be Plan 01, not Plan 02.
**How:** 
1. In Plan 01 frontmatter `must_haves`: add "Plan 01 MUST define and document the `ObservationRecord` JSONL schema as part of hook deployment. This schema is the contract for all consumers including Plan 02."
2. In Plan 02 frontmatter: change "defines the canonical transcript schema" to "consumes the ObservationRecord schema defined in Plan 01 and maps it to per-move scoring inputs." Remove any implication that Plan 02 owns the schema.
3. Verify Plan 02 depends_on Plan 01 (it does per the area description) — no change needed there, but the schema ownership reversal resolves the conceptual inversion.
**Impacts:** Plan 01 gains schema-ownership task (minor scope increase); Plan 02 loses an ill-defined responsibility
**Research needed:** no
**Confidence:** MEDIUM — this is a design clarity issue, not a runtime failure. If implementers read both plans together they'll likely get it right. But the stated inversion creates confusion.
**Prior art:** 5 — producer-defines-schema, consumer-maps-to-domain is standard
**Prerequisite:** no
**Status:** reframed
**Origin:** NOVEL — deducible from reading both plans together and noticing the ownership inversion; not flagged anywhere

### P1-IMP-13: Assumption 3 is Structurally False for the Primary Evaluation Mode
**Target:** CONTEXT
**What:** Assumption 3 states "JSONL transcripts from hooks are accessible post-session for intelligence module consumption — validated by 3.1c.2 JSONL verification." This is false for Agent Teams teammates (worktree-isolated), which IS the primary evaluation mode for 3.1c and beyond. 3.1c.2 execution returned TRANSCRIPT_UNAVAILABLE for all 4 agents. The phrase "validated by 3.1c.2" inverts the actual finding — 3.1c.2 DISCOVERED the gap, it didn't validate the capability.
**Why:** Every plan in this phase that processes JSONL transcripts is downstream of this assumption. If Plans 01-02 ship a JSONL hook pipeline that only captures orchestrator-side events (not teammate events), then Plans 03-12 receive structurally incomplete data. The intelligence modules (Plans 03-06) will produce analysis on the wrong process — the orchestrator's tool calls, not the teammate's reasoning steps. Plans built on that will produce confidently-wrong results. The current wording actively misleads the planner: "validated" implies it works, when 3.1c.2 proved it doesn't for the mode that matters.
**How:** 
1. Split Assumption 3 into two scoped assumptions:
   - "3a: JSONL transcripts ARE accessible for Task() subagents and the orchestrator session itself."
   - "3b: JSONL transcripts are NOT natively accessible for worktree-isolated Agent Teams teammates — this is Gap-1 from 3.1c.2 VERIFICATION.md. Plan 01 must explicitly address the remediation path (polling worktree `.claude/` directories, transcript relay, or alternative capture)."
2. Add a new assumption: "3c: Env-var propagation does NOT reach Agent Teams teammate subprocesses in worktree isolation mode. Any hook activation or configuration that relies on env vars will only take effect in the orchestrator process." This was empirically confirmed in 3.1c.2.
3. Update the parenthetical "(validated by 3.1c.2 JSONL verification)" → "(Gap-1 from 3.1c.2 VERIFICATION.md — remediation is Plan 01's primary objective)."
**Impacts:** All 12 plans — directly impacts Plans 01-02 (hook/transcript infrastructure), cascades to Plans 03-12 (intelligence modules that consume transcript data). Confidence on Plans 03-06 should be recalibrated to MEDIUM or lower until Plan 01's remediation is validated.
**Research needed:** yes — What mechanisms does Claude Code expose (if any) for worktree-isolated subprocesses to relay events back to a parent session's hook listeners? Is polling the worktree `.claude/` directory viable? Does the worktree have its own `.claude/settings.json` and does that trigger its own hook pipeline?
**Confidence:** HIGH
**Prior art:** 1 — The two-process boundary (orchestrator vs isolated subprocess) is a known systems problem, but the specific Claude Code worktree + hooks interaction has no documented precedent.
**Prerequisite:** yes — Gap-1 remediation (how transcripts cross the worktree boundary) must be resolved before Plan 01 can be designed with confidence. This is the foundational question of the entire phase.
**Status:** confirmed
**Origin:** NOVEL — The 3.1c.2 execution feedback directly invalidates a load-bearing assumption. This gap would exist in the original CONTEXT.md even without prior passes, because the assumption was written before 3.1c.2 ran.

### P1-IMP-14: Missing Explicit Two-Mode Architecture Assumption
**Target:** CONTEXT
**What:** The Base Assumptions section has no entry acknowledging that the evaluation framework operates in two structurally different execution modes with different observability profiles: (A) Task() subagents which may inherit env vars and produce accessible JSONL, and (B) TeamCreate+teammate with worktree isolation which has no env-var inheritance, no accessible JSONL, and no delegate_guard enforcement. The phase goal says "activate Tier 2 Intelligence layer" but the intelligence layer's inputs (transcripts) come from Mode B, which the hooks can't observe.
**Why:** Without making this dichotomy explicit as an assumption, every plan author will implicitly assume Mode A behavior (which is simpler and works). When they design intelligence modules that "consume JSONL transcripts," they will design for the wrong data source. The fix isn't just wording — the phase needs to either (a) solve Mode B observability in Wave 1 before anything else, or (b) explicitly scope the entire phase to Mode A evaluations only and acknowledge that Mode B observability is deferred. Currently neither decision is made, so plans will be designed with ambiguous scope.
**How:** 
1. Add a new assumption to Base Assumptions: "A-new: The evaluation framework operates in two modes with different observability properties. Mode A (Task() subagents): env-var inheritance works, hooks fire in the subprocess context, JSONL may be accessible. Mode B (TeamCreate+worktree teammates): no env-var inheritance, hooks fire only in the orchestrator context, teammate-side JSONL is inaccessible without explicit relay. Plans 03-12 (intelligence modules) should specify which mode's data they consume."
2. Add a corresponding key decision: "D-new: This phase scopes intelligence module activation to [Mode A only / Mode B with relay mechanism from Plan 01 / both with explicit fallbacks]. If Plan 01's relay mechanism fails, Plans 03-06 fall back to orchestrator-side events only." The planner must make this decision before Wave 1 begins.
**Impacts:** Plans 01-02 (must define the relay or scope), Plans 03-06 (must reference which mode's data they process), Plan 09 (meta-tests must use data from the correct mode).
**Research needed:** no — The modes are empirically established by 3.1c.2 findings. The decision is architectural, not research.
**Confidence:** HIGH
**Prior art:** 2 — Multi-process observability is a well-understood systems problem, but the specific Claude Code session/worktree boundary and what "hooks" means across that boundary is novel.
**Prerequisite:** no — This is an assumption/decision framing issue; it doesn't block writing the assumption itself.
**Status:** confirmed
**Origin:** NOVEL — This gap exists in the original CONTEXT.md regardless of prior passes. The two-mode dichotomy was empirically confirmed by 3.1c.2 but the structural absence of this assumption is an original omission.

### P1-IMP-15: D-8's "Plan 12 Data" Reference is Ambiguous and May Use Wrong Failure Mode
**Target:** CONTEXT
**What:** D-8's "Plan 12 data" reference is ambiguous between two datasets with incompatible failure signatures. Using the pre-3.1c.2 raw-Python-import dataset as meta-test fixtures calibrates intelligence modules against a failure mode that isolation hardening already eliminated.
**Why:** Plan 12 Batch 1 produced two failure sets: (A) agents falling back to raw Python imports because CLI queries returned 0 results — a pre-3.1c.2 failure mode now fixed by isolation hardening; (B) CLI functioning but validator logic bugs — the post-3.1c.2 failure set that represents current-state failure modes. Meta-tests built on dataset A will pass when modules detect "raw Python use" but that signal no longer appears in production sessions. D-8 must pin to dataset B or explicitly exclude dataset A fixtures.
**How:** 
1. In CONTEXT.md D-8, replace "Plan 12 known-bad transcripts" with explicit dataset identifier: "Plan 12 Batch 1 Post-3.1c.2 fixtures (CLI functional, validator logic failures only — see `.vrs/observations/plan12/` filtering for sessions where agents used CLI tools)."
2. Add a note: "Pre-3.1c.2 raw-Python-import transcripts are NOT valid meta-test fixtures — failure mode no longer occurs in isolated sessions."
3. Cross-reference P1-IMP-25 to avoid duplicate handling.

### P1-IMP-16: Phase Goal Claims "Prove It Works" Without a Falsifiability Criterion
**Target:** CONTEXT
**What:** The phase goal "prove it works" has no falsifiability criterion. No condition exists under which a module is declared unfit at phase close. All 10 modules ship as "done" if they activate and produce any output.
**Why:** Without a floor criterion, phase 3.1c.3 cannot fail. A module that always returns `is_active() = False` satisfies "activated" if it doesn't crash. A module that emits random output satisfies "produces output." The phase goal requires a minimum bar that distinguishes activation from validation, and a stated condition under which the phase does NOT close.
**How:** 
1. Add a key decision D-9 to CONTEXT.md: "Phase 3.1c.3 proof criterion — each module must (a) pass its own meta-test against at least one known-bad fixture from the post-3.1c.2 dataset AND (b) `is_active()` must return True on that fixture. Modules that activate but fail their meta-test are flagged UNVALIDATED and are NOT counted toward phase completion. Full behavioral validation deferred to 3.1f."
2. Update the phase goal sentence to reference D-9 explicitly.
3. This creates a falsifiable bar without requiring production data.

### P1-IMP-17: Assumption 4 Claims Stub Interfaces Are Correct Without Specifying Which Stubs
**Target:** CONTEXT
**What:** Assumption 4 states "3 existing intelligence module stubs have correct `is_active()` interfaces." It does not name the 3 modules, reference any file paths, or specify what "correct" means for the interface contract. A stub could have `is_active()` returning a hardcoded `False` and satisfy this assumption literally. If those stubs are the entry points Plans 03-06 extend, and they have incorrect behavior (not just wrong signatures), the plans will fail silently.
**Why:** This is a prerequisite-state assumption — it asserts something is already built and correct. Unlike assumptions about external infrastructure (which can be verified at runtime), a wrong stub interface will be discovered mid-task, causing plan failure at an unrecoverable point. The cost of silence here is high: a plan that reaches Task 3 before discovering the stub interface is incompatible with the module activation system has wasted all prior work and must be re-planned.
**How:** 
1. Name the 3 specific stubs and their file paths: e.g., "CoverageRadar at `src/.../intelligence/coverage_radar.py`, ScenarioSynthesizer at `...`, Fingerprinter at `...`."
2. Specify the interface contract: "correct means `is_active()` returns bool, is callable without arguments, and the class can be instantiated without triggering data pipeline calls." If the stubs currently return hardcoded False, note that — Plans 03-06 will need to change that.
**Impacts:** Plans 03-06 (the plans that extend these stubs directly).
**Research needed:** yes — What are the actual file paths and current `is_active()` implementations for the 3 stubs? Do they match the interface the intelligence activation system expects?
**Confidence:** MEDIUM
**Prior art:** 4 — Interface contract verification before extension is standard practice; the specific gap is the missing specificity in the assumption text.
**Prerequisite:** no — This is a documentation clarity issue, but it becomes a hard prerequisite if the stubs are wrong.
**Status:** confirmed
**Origin:** NOVEL — The vagueness of Assumption 4 is an original omission. Naming specific stubs requires reading source files that are not in scope for prior improvement passes.

### P1-IMP-18: Coverage Radar Has No Real Data Source — Hook Transcripts Unavailable
**Target:** PLAN-03
**What:** Plan 03 coverage radar depends on Plan 02 decomposer output, which depends on transcript data unavailable for worktree teammates. Without a specified fallback, the radar produces no output in the primary evaluation mode.
**Why:** The cascade failure is: hooks don't fire in teammates → no transcripts → Plan 02 returns None scores → Plan 03 has no input. A fallback that maps observation JSON fields directly to coverage dimensions breaks the cascade at the Plan 02 → Plan 03 link, but only if the field mapping is explicitly specified and testable.
**How:** 
1. Add to Plan 03 a field mapping table: observation JSON field → coverage dimension (e.g., tool_sequence length → QUERY_FORMULATION coverage, finding_count > 0 → CONCLUSION_SYNTHESIS coverage).
2. Plan 03 Task 1 verify step: run coverage radar against 4 existing observation JSON files; assert non-empty report with data_source: "observation_json" in report header.
3. Done criterion: coverage report logs data_source field; passes with both Plan 02 output and raw observation JSON as input.

### P1-IMP-19: Counterfactual Replayer Will Record Empty Trajectories — Hook Blindspot
**Target:** PLAN-06
**What:** Plan 06 states the replayer "records agent execution trajectories from hook-captured events." Execution feedback finding #1 confirms hooks fire in the orchestrator only, not in worktree-isolated Agent Teams teammates. The actual agent execution — the tool calls, query sequences, reasoning steps — happens inside isolated teammates. The orchestrator sees only the final result handed back.
**Why:** This is not a subtle risk — it's a guaranteed empty or misleading output. The trajectory will show the orchestrator's view (start, send, receive, done) but nothing about what the agent actually did. Counterfactual analysis ("what if the agent had queried differently?") requires the agent's actual query sequence. That data is in observation JSONs (tool_sequence field) — NOT in hook events.
**How:** 
1. In Plan 06, Task 1 action steps: change "records agent execution trajectories from hook-captured events" to "records agent execution trajectories from observation JSON `tool_sequence` and `query_count` fields, with hook events used only for orchestrator-level timing markers."
2. In Plan 06, Task 1 done criteria: add "trajectory for any of the 4 existing 3.1c.2 observation files contains ≥3 internal tool calls (not just orchestrator events)" — this forces the implementation to read from observation JSONs rather than hook events.
**Impacts:** Plan 06 confidence LOW-MEDIUM -> LOW without fix. Plan 07 validation of the replayer will also be testing an empty trajectory recorder.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — Trajectory recording from structured logs (not hooks) is a known pattern; the observation JSON schema is project-specific but reading structured output is not novel.
**Prerequisite:** no — observation JSONs from 3.1c.2 already exist. The replayer can be built against those directly.
**Status:** confirmed
**Origin:** NOVEL — Directly caused by the execution feedback finding that hooks don't fire in isolated teammates. This is not derivable from CONTEXT.md alone.

### P1-IMP-20: Contract Healer Bimodal Detection Cannot Activate — Data Starvation
**Target:** PLAN-05
**What:** Plan 05 extends `contract_healer.py` with bimodal detection. Bimodal detection is a distribution analysis technique: you need enough runs to distinguish two clusters from noise. With 4 calibration observations from 3.1c.2 (confirmed by execution feedback), any distribution analysis will have meaningless results. The plan does not specify a minimum activation threshold for the healer's bimodal detection, unlike the fingerprinter (20 runs) and scenario synthesizer (5 results).
**Why:** Without an explicit activation gate, the healer will run bimodal detection on 4 data points and produce a "bimodal distribution detected" or "no bimodality" verdict that is statistically meaningless. If this output is consumed downstream (Plan 10 closed-loop system), it will act on noise. A meaningless detection output is worse than no output because it creates false confidence.
**How:** 
1. In Plan 05, frontmatter or Task 1, add: "Bimodal detection in contract_healer MUST be gated on `n >= 15` observations with the same contract template. Below threshold, emit `status: insufficient_data` rather than a bimodal verdict."
2. In Plan 05, Task 1 done criteria: add "when fed the 4 existing 3.1c.2 observations, healer emits `status: insufficient_data` for bimodal analysis rather than attempting a verdict."
**Impacts:** Plan 05 confidence MEDIUM stays MEDIUM but the done criteria become more realistic. Plan 10 (closed-loop) dependency becomes safer.
**Research needed:** no — minimum sample sizes for bimodal detection are well-established (rule of thumb: ≥15 per mode, ≥30 total for reliable detection).
**Confidence:** HIGH
**Prior art:** 5 — Minimum sample size guards before distribution analysis is standard statistical practice.
**Prerequisite:** no
**Status:** confirmed
**Origin:** NOVEL — The 4-observation data starvation is confirmed by execution feedback. The plan's omission of an activation threshold is visible from reading Plan 05 alone.

### P1-IMP-21: Scenario Synthesizer Activation Gate Is Below Minimum Useful Signal
**Target:** PLAN-04
**What:** Plan 04 scenario synthesizer gates on 5 runs but produces noise on low-n data. The prompt analyzer and gap detector have different data dependencies that are not distinguished.
**Why:** The prompt analyzer can operate on orchestrator-level prompts (available from any spawn path via hook events). The gap detector requires per-move scores from Plan 02 (unavailable until transcripts exist). Conflating them into a single activation gate means both are blocked by the higher-barrier dependency.
**How:** 
1. Split Plan 04 into two activation tiers: Tier 1 (prompt analyzer) activates at n >= 1, consuming orchestrator-prompt fields from hook events — label as data_source: "orchestrator_hook". Tier 2 (gap detector) activates at n >= 10, consuming per-move scores from Plan 02 output — label as data_source: "decomposer_output".
2. Each generated scenario stub must include a confidence annotation derived from the activating tier.
3. Done criterion: Plan 04 produces Tier 1 stubs from existing 4 observations; Tier 2 stubs remain empty until Plan 02 output exists.

### P1-IMP-22: Plan 03 Severity Weighting Is Undefined Without Evaluation Dimension Taxonomy
**Target:** PLAN-03
**What:** Plan 03 states "severity-weighted gap prioritization: Core 3x, Important 2x, Standard 1x." The weights are defined but the mapping of evaluation dimensions to severity tiers is not. The plan also states `EXPECTED_DIMENSIONS` is trimmed from 7 to 3 — but which 3 dimensions are Core vs Important vs Standard is not specified anywhere in the plan content.
**Why:** This is a plan-level verification gap. The done criteria say "severity-weighted gap report" but provide no ground truth for what the correct weights should produce. A reviewer running the verification step cannot distinguish correct weighting from incorrect weighting.
**How:** 
1. In Plan 03, Task 1 action steps: add "Define `DIMENSION_SEVERITY_MAP: dict[str, Literal['Core', 'Important', 'Standard']]` with explicit entries for all 3 retained dimensions before any weighting code is written. This map becomes the ground truth for verification."
2. In Plan 03, Task 1 done criteria: add "DIMENSION_SEVERITY_MAP is present as a module-level constant and matches the 3 retained dimensions exactly (no runtime lookup, no inference)."
**Impacts:** Plan 03 done criteria become verifiable. No confidence change.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Explicit constant maps for classification schemes is standard practice.
**Prerequisite:** no
**Status:** confirmed
**Origin:** NOVEL — The missing taxonomy is visible from reading Plan 03 alone without any prior improvement context.

### P1-IMP-23: Plan 06 Fingerprinter 20-Run Threshold Means It Ships as Dead Code
**Target:** PLAN-06
**What:** Plan 06 delivers `fingerprinter.py` with "behavioral signature schema + `is_active` stub (activates after 20 runs)." With 4 existing observations and the evaluation cadence implied by this phase (calibration batches of ~4-8 runs), the fingerprinter will not activate for many weeks. Plan 07 (self-validation) tests all modules from Plans 01-06 — but it cannot meaningfully test an inert stub.
**Why:** Shipping dead code with a distant activation threshold in a bootstrap phase creates a validation theater problem: Plan 07 "passes" fingerprinter validation by confirming the stub exists and returns False. No real behavior is tested. If the behavioral signature schema is wrong or incomplete, it won't be discovered until 20 runs are accumulated — at which point fixing the schema is much more expensive.
**How:** 
1. In Plan 06, Task 2 (fingerprinter): add a done criterion: "schema is validated against at least 2 of the existing 3.1c.2 observation files — each observation should be parseable into a fingerprint struct even in inactive mode (dry-run path). Schema completeness validated now, not at 20-run activation."
2. In Plan 07 (cross-area note only, not a proposed fix): Plan 07's fingerprinter test should be noted as needing a dry-run mode test, not just `is_active() == False` check.
**Impacts:** Plan 06 deliverable quality improves without scope change. Plan 07 gets a more meaningful validation target.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Testing schema completeness against real data before activation thresholds is standard. "Parse but don't act" dry-run paths are well-established.
**Prerequisite:** no
**Status:** confirmed
**Origin:** NOVEL — The 20-run threshold vs 4-observation reality is directly visible from reading Plan 06 + execution feedback. No prior improvement context needed.

### P1-IMP-24: Plan 07 "Both Spawn Paths Tested" is Broken by Design — TeamCreate Path Cannot Produce Valid EvaluationResult
**Target:** CONTEXT
**What:** The Plan 07 description states "Both spawn paths tested: Task() subagent AND TeamCreate+Task(team_name=...)" as a deliverable. But the domain explicitly states: "Assumption 3: JSONL transcripts from hooks are accessible post-session — 3.1c.2 showed this is NOT true for Agent Teams teammates." The TeamCreate path in worktrees produces TRANSCRIPT_UNAVAILABLE. An EvaluationRunner that expects a JSONL transcript will receive nothing from the TeamCreate path — the pipeline fails silently or raises on missing transcript, not because the framework is broken, but because the input data structurally doesn't exist.
**Why:** Conflating two spawn paths that produce structurally different outputs into a single "both paths tested" deliverable creates a meta-test suite with an internal contradiction. The validation criteria cannot be the same across paths. Either the test correctly documents path-specific expectations (in which case it's two separate tests, not "both paths tested" as a unit), or it papers over the asymmetry and gives false confidence. The domain already acknowledges this failure mode explicitly. Plan 07 ignores it.
**How:** 
1. In CONTEXT.md Plan 07 description, replace "Both spawn paths tested: Task() subagent AND TeamCreate+Task(team_name=...)" with two explicit sub-deliverables: (a) Task() path: full EvaluationResult including JSONL transcript, hook data, scoring; (b) TeamCreate path: observation JSON only, TRANSCRIPT_UNAVAILABLE accepted, scoring from observation signals only — validated against Plan 08's diagnostics module (which can work from observation JSONs per IMP-03 below).
2. Add an explicit assertion matrix to the Plan 07 description: a table mapping spawn path → expected data fields present → what absence of each field means for validation verdict. This makes the asymmetry a design artifact rather than a bug.
**Impacts:** Plan 07 confidence should drop from HIGH to MEDIUM until the assertion matrix is defined. Plan 12 (which depends on Plan 07 for verification) may also need to specify which spawn path its validation uses.
**Research needed:** no — the asymmetry is already documented in the domain and execution feedback
**Confidence:** HIGH
**Prior art:** 2 — spawn-path asymmetry is analogous to test doubles vs real I/O in unit testing, but the specific TRANSCRIPT_UNAVAILABLE failure mode is unique to Claude Code Agent Teams
**Prerequisite:** no
**Status:** confirmed
**Origin:** NOVEL — this gap exists in the original CONTEXT.md regardless of prior improvement passes

### P1-IMP-25: Plan 07 Should Use ACTUAL Plan 12 Batch 1 Failure Data, Not "Fabricated" Synthetic Equivalents
**Target:** CONTEXT
**What:** Plan 07 states: "Scoring validation: known-good (Plan 09 data) vs known-bad (Plan 12 data) → 20pt differential." The execution feedback confirms: "Known-bad data from Plan 12 Batch 1: the failure-analysis.md documents the exact false-positive patterns." The CONTEXT description implies these are real datasets. But it also says "Anti-fabrication validation: suspicious patterns trigger investigation" — suggesting the framework is being tested against synthetic fabricated data.
**Why:** Meta-tests that use synthetic bad data give false confidence. The real failure data already exists at `.vrs/observations/plan12/cal-*.json`. Using real data means: (a) the anti-fabrication checks are tested against signals that actually triggered in production, (b) the 20pt differential claim is grounded in empirical observation rather than assumption, (c) if the framework cannot detect the real Plan 12 failures, that is a genuine gap worth knowing.
**How:** 
1. In CONTEXT.md Plan 07 description, change "known-bad (Plan 12 data)" to "known-bad (ACTUAL Plan 12 Batch 1 failure observations from `.vrs/observations/plan12/cal-*.json`, NOT synthetic fabrications)."
2. Add a note that anti-fabrication validation should use the signals actually observed in 3.1c.2: uniform_confidence (all 1.0), uniform_severity, Python module import fallback — not hypothetical patterns.
**Impacts:** Plan 07 deliverable quality. If real data is used, the 20pt differential claim becomes a falsifiable assertion rather than a design target.
**Research needed:** no — the real data location is documented in execution feedback and project memory
**Confidence:** HIGH
**Prior art:** 4 — using real failure corpora to validate detection systems is standard practice in anomaly detection
**Prerequisite:** no — `.vrs/observations/plan12/cal-*.json` already exists
**Status:** confirmed
**Origin:** NOVEL — real-vs-synthetic data distinction is visible in original CONTEXT.md + execution feedback combination

### P1-IMP-26: Plan 08 Graph Diagnostics Does NOT Need Hooks — Observation JSONs Are Sufficient, and the Dependency on Plan 01 Should Be Softened
**Target:** CONTEXT
**What:** Plan 08 lists Plan 01 (hooks) as a hard dependency, but observation JSONs from past runs already contain sufficient graph query data for most diagnostic checks — the hard dependency blocks Plan 08 from operating on historical data.
**Why:** If Plan 08 can only diagnose failures in live sessions (hooks present), it cannot retroactively analyze the Plan 12 Batch 1 failure corpus, which is the most data-rich source available.
**How:** 
1. Audit Plan 08's diagnostic checks: for each check, classify as `hooks_required` (needs real-time call context: raw query string, call stack, timing) or `json_sufficient` (can run on observation JSON fields: query_count, result_count, status flags, agent_id).
2. Implement Plan 08 with two data adapters: `HookAdapter` (Plan 01 present) and `ObservationJsonAdapter` (historical data).
3. Mark Plan 01 as a soft dependency: Plan 08 activates `ObservationJsonAdapter` by default; upgrades to `HookAdapter` when hooks are available.
4. Document which diagnostic checks degrade in `ObservationJsonAdapter` mode (e.g., root-cause analysis loses call-stack depth).

### P1-IMP-27: Plan 08 Duplicates agent_execution_validator.py — Scope Must Be Differentiated or Plan Merged
**Target:** CONTEXT
**What:** The execution feedback states: "agent_execution_validator.py already has 12+ checks: Plan 08's graph diagnostics may overlap with existing validator checks (unverified_node_ids, graph_stats validation). Ensure no duplication."
**Why:** Duplicate diagnostic systems degrade trust in both. When `agent_execution_validator` says PASS and `graph_diagnostics` says FAIL (or vice versa), the operator has no decision rule. The right design is either: (a) Plan 08 explicitly extends `agent_execution_validator.py` rather than creating a new module, or (b) Plan 08 is scoped exclusively to NEW capabilities not in the validator (specifically: WHY a query failed — root cause analysis and fix recommendations — which the validator does not do). Option (b) is cleaner and preserves Plan 08's unique value: not detection, but diagnosis.
**How:** 
1. In CONTEXT.md Plan 08 description, add an explicit non-overlap constraint: "`graph_diagnostics.py` does NOT re-implement detection. It consumes validator output (PASS/FAIL per check) and adds root-cause analysis and fix recommendations. Activation: only after validator detects a failure."
2. Remove "graph structure report" from Plan 08's deliverables (this is already in the validator). Replace with "fix recommendation generation: for each validator failure category, emit a human-readable diagnosis and concrete remediation step."
**Impacts:** Plan 08 scope narrows but becomes more clearly differentiated. Dependency on the existing validator becomes explicit.
**Research needed:** no — the validator's check list is documented in project memory
**Confidence:** HIGH
**Prior art:** 4 — root-cause-analysis layers on top of detection systems are a standard pattern (linters + formatters, validators + fixers)
**Prerequisite:** no — `agent_execution_validator.py` already exists
**Status:** confirmed
**Origin:** NOVEL — duplication is visible from original CONTEXT.md + execution feedback without prior improvement passes

### P1-IMP-28: Plan 09 Jujutsu Workspace Isolation Conflicts with Existing Git Worktree Isolation — Mechanism Must Be Reconciled
**Target:** CONTEXT
**What:** Plan 09 uses `jj workspace` commands for snapshot/restore, but the project uses git worktrees exclusively and `jj` availability is unverified. The plan as written will fail unconditionally on this environment.
**Why:** Git worktrees are the confirmed isolation mechanism (cited in execution feedback). Plan 09's repeatability goal (snapshot before test, restore after) is valid but the implementation must not depend on an unavailable tool.
**How:** 
1. Add `is_jj_available()` check at Plan 09 module init. Gate all `jj` calls behind this check.
2. Implement git-based fallback for snapshot/restore: before evaluation session, capture HEAD commit hash + `git stash` of any dirty state as the "snapshot." After session, `git checkout <HEAD>` + `git stash pop` as the "restore." Store snapshot metadata in `.vrs/snapshots/<session_id>.json`.
3. Scope `jj` usage to evaluation repeatability scenarios only (Plan 09's stated purpose). Do NOT use `jj` for agent isolation — git worktrees remain the isolation mechanism.
4. Add to Plan 09 done criteria: "snapshot/restore round-trip verified on git-only environment without jj installed."

### P1-IMP-29: Plan 09 Worktree Cleanup Timing Problem Is Not Addressed — Jujutsu Restore Does Not Fix the Root Cause
**Target:** CONTEXT
**What:** The execution feedback documents: "Worktrees were cleaned up before validation in 3.1c.2, causing false failures. Any workspace/worktree lifecycle needs explicit ordering: validate → THEN cleanup."
**Why:** If Plan 09 is sold as the solution to the cleanup-before-validation problem but does not actually address it, Plan 12 (which depends on Plan 07 for verification) will hit the same false-failure bug that plagued 3.1c.2. The fix for cleanup ordering is a code change in the WorkspaceManager or EvaluationRunner lifecycle, not a Jujutsu snapshot.
**How:** 
1. In CONTEXT.md Plan 09 description, add explicit lifecycle deliverable: "WorkspaceManager lifecycle enforces: agent_completion → data_collection → validation → cleanup. Cleanup is NEVER called before EvaluationResult is finalized. This is a separate deliverable from snapshot/restore."
2. Note that the "Workspace rollback test" in Plan 07 should test this ordering explicitly: assert that cleanup does not run until `result.status` is set.
**Impacts:** Plan 09 and Plan 07 both affected. Without this, the worktree false-failure bug from 3.1c.2 will recur.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — cleanup-after-assertion ordering is a standard test teardown pattern (setUp/tearDown, pytest fixtures with yield)
**Prerequisite:** no
**Status:** confirmed
**Origin:** NOVEL — the lifecycle ordering problem is documented in execution feedback and is visible without prior passes


### P1-ADV-21: Transcript Schema Needs Neutral Owner — Neither Plan 01 Nor Plan 02
**Target:** CONTEXT
**What:** Transcript schema definition has no neutral owner — it is claimed by Plan 02 but produced by Plan 01, creating a circular dependency where each plan's implementation diverges.
**Why:** Schema disagreements between producer (Plan 01 hooks) and consumer (Plan 02 parser) will surface as silent field mismatches at runtime. No plan has authority to break the tie at review time.
**How:**
1. Create `src/alphaswarm_sol/testing/evaluation/transcript_schema.py` (or equivalent constants module) as the single source of truth for JSONL field names, required fields, and sentinel values.
2. Plan 01 imports from this module when emitting records. Plan 02 imports from this module when parsing. Neither plan "owns" the schema — both reference it.
3. Update CONTEXT.md: add explicit note that `transcript_schema.py` is the canonical schema source; Plans 01 and 02 are producer/consumer respectively.
4. Add schema version field (`schema_version`) to all records emitted by Plan 01 hooks. Plan 02 parser rejects records with mismatched version and emits `SCHEMA_VERSION_MISMATCH`.
**Impacts:** Plans 01, 02, and all downstream consumers (03-08)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** yes — shared schema module must be created before Plan 01 or Plan 02 can finalize their I/O contracts
**Status:** open
**Origin:** CREATE from REFRAME of P1-IMP-12 (adversarial review: Plan Coherence lens)

## Adversarial Lenses

| Lens | Brief | Items | Attack Vector |
|------|-------|-------|---------------|
| Data Void Cascade | Starting from the proven fact that hooks don't fire in worktree teammates, trace the causal chain from Plan 01 through Plans 02-06 to Plans 10-12 activation gates. | IMP-01,02,03,07,08,09,10,13,14,18,19,20,21,23,24 | Does each improvement diagnose WHERE in the cascade data disappears, or do some diagnose symptoms rather than root causes? |
| Plan Coherence | Plans 02, 03, 08, 09, 12 have overlapping scope, conflicting mechanisms, or undefined boundaries with existing infrastructure. | IMP-05,06,11,12,22,25,26,27,28,29 | Is each scope conflict genuine (would block executor), or manufactured overlap that competent executors would naturally resolve? |
| Foundational Framing | CONTEXT.md goal says "prove it works" with no failure definition; D-8 references ambiguous dataset; Assumption 4 makes unverifiable claims about stubs. | IMP-04,15,16,17 | Does each improvement identify a real framing gap that misleads planners, or is it nitpicking documentation precision? |

## Cross-Area Concerns

- **Plans 03-06 (Intelligence Modules A)**: All depend on Plan 01's hook output. Hooks capture orchestrator events only — not teammate reasoning. Coverage radar, scenario synthesizer, and behavioral fingerprinter are operating on boundary-event data.
- **Plan 07 ↔ Plan 09**: Plan 07's workspace rollback test depends on Plan 09's mechanism. If `jj` is unavailable (IMP-28 prerequisite), Plan 07 needs the git fallback from IMP-28.
- **Plan 08 ↔ validator**: Plan 08 and agent_execution_validator.py have detection overlap. IMP-27 scopes Plan 08 to root-cause analysis only.
- **Plans 10-12 (Closed-Loop)**: All have data-volume gates on zero scored observations. Bootstrap fixtures (IMP-07) must cover degraded-path schema.

## Post-Review Synthesis

3 cross-cutting patterns + 4 cascade gaps identified.

### P1-SYN-01: Producerless Output Pattern — Systems Write Results Nobody Reads
**Target:** CONTEXT
**What:** Four items (IMP-01, IMP-08, IMP-19, ADV-21) show the same structural weakness: plans produce artifacts with no declared downstream consumer. "Write output" is treated as equivalent to "deliver value."
**Why:** Without producer-consumer contracts, outputs are either never consumed (dead code) or consumed with incompatible format assumptions (silent data corruption).
**How:**
1. Add an "Artifact Registry" to CONTEXT.md listing every persistent output, producing plan, consuming plan.
2. For any artifact where consumer is TBD, assign owning plan responsible for schema definition.
**Components:** IMP-01, IMP-08, IMP-19, ADV-21
**Confidence:** HIGH | **Status:** open | **Source:** synthesis

### P1-SYN-02: Silent Activation Failure — Gates No-Op Instead of Blocking
**Target:** CONTEXT
**What:** Five items (IMP-02, IMP-09, IMP-10, IMP-20, IMP-22) show activation gates that fail silently. Partial activation is indistinguishable from silent failure.
**Why:** Intelligence modules feed regression baselines and promotion decisions. Silent partial activation corrupts downstream decisions without any alert.
**How:**
1. Define `ActivationStatus` enum (ACTIVE | DEGRADED | BLOCKED | INSUFFICIENT_DATA) for all intelligence modules.
2. Require INFO-level activation status logging, not DEBUG.
3. For each gated plan, add explicit "BLOCKED path" section describing downstream impact.
**Components:** IMP-02, IMP-09, IMP-10, IMP-20, IMP-22
**Confidence:** HIGH | **Status:** open | **Source:** synthesis

### P1-SYN-03: Unfalsifiable Success — Phase Goal Lacks Testable Floor Criteria
**Target:** CONTEXT
**What:** Three items (IMP-06, IMP-13, IMP-16) show success defined as activity (ran, executed) not outcomes (output is correct, assumption holds under test).
**Why:** Phase 3.1c has documented history: Plan 12 Batch 1 ran and produced files later found entirely invalid. Same failure structurally guaranteed without falsifiable criteria.
**How:**
1. Rewrite Phase Goal with measurable floor criterion (e.g., 3+ modules must detect known defect in known-bad input).
2. For each plan claiming to "validate," add deliberately broken input that must produce FAIL.
3. Phase-exit checklist: "Can deliverable be demonstrated to fail on crafted bad input?"
**Components:** IMP-06, IMP-13, IMP-16
**Confidence:** HIGH | **Status:** open | **Source:** synthesis

### P1-CSC-01: Fixture Contract Becomes Multi-Plan Dependency
**Target:** PLAN-02 | **Trigger:** IMP-07
**What:** After IMP-07, bootstrap fixtures become shared prereq for Plans 02, 10, 12. No plan currently declares this dependency.
**How:** Add fixture version field; declare explicit dependencies in plan headers; add pre-run fixture validation.
**Confidence:** HIGH | **Status:** open | **Source:** synthesis (cascade)

### P1-CSC-02: Git Fallback Path Needs Integration Tests
**Target:** PLAN-01 | **Trigger:** IMP-28
**What:** Once git fallback for jujutsu exists, it has no integration tests — invisible until jj-absent machine runs a plan.
**How:** Force `is_available()` to False in test; verify git fallback creates valid worktree; CI matrix entry for jj-absent env.
**Confidence:** HIGH | **Status:** open | **Source:** synthesis (cascade)

### P1-CSC-03: Severity Schema Lock Becomes Cross-Plan Dependency
**Target:** PLAN-04 | **Trigger:** IMP-22
**What:** After IMP-22 locks weighting, any Plan 03 schema change silently breaks Plans 04/05 threshold logic.
**How:** Add severity schema version constant; consuming plans assert version match; cross-plan integration test.
**Confidence:** HIGH | **Status:** open | **Source:** synthesis (cascade)

### P1-CSC-04: Hook Output Manifest Becomes Maintenance Contract
**Target:** PLAN-02 | **Trigger:** IMP-08
**What:** hook_output_manifest.json becomes ground truth for all consumers. Adding hooks without updating manifest = silent data loss.
**How:** Auto-generate manifest from hook registration (not hand-authored); integrity check in preflight; CI test for manifest drift.
**Confidence:** HIGH | **Status:** open | **Source:** synthesis (cascade)

## Convergence

Pass 1: 37 items total (29 original + 1 ADV-CREATE + 3 SYN + 4 CSC)
Structural: 37 | Cosmetic: 0 | Ratio: 0% cosmetic
Threshold: 80% (default novelty)
Signal: ACTIVE

