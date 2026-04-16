# Improvement Pass 19

**Date:** 2026-02-26
**Phase:** 3.1c
**Status:** complete

## Pipeline Status

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 0 | 0 | — |
| Research | 0 | 0 | — |
| Gaps | 0 | 13 | — |
| Merge-ready | 0 | 0 | — |

**Pipeline:** [discuss] ✓ → [improve] ! → [pre-impl] — → [research] — → [implement] — → [plan] ✓ → [execute] —
**Next:** /msd:resolve-blockers 3.1c — 14 IMP item(s) never adversarially reviewed

## Improvements

### P19-IMP-01: Plans 09+10+11 Sequential Ordering Not in Frontmatter — Executor Will Parallelize and Corrupt Shared State
**Target:** PLAN-09, PLAN-10, PLAN-11
**What:** All three plans have `depends_on: ["3.1c-08"]` only. An executor reading frontmatter sees three plans with the same upstream dependency and will attempt to parallelize them. CONTEXT.md and the research section both confirm "Wave 6: [09+10+11] SEQUENTIAL within wave" and that "shared BaselineManager prevents concurrent writes." The joint HITL gate (09a+10a must both complete before Important sub-waves begin) is entirely absent from frontmatter.
**Why:** When an executor parallelizes Plans 09+10+11, BaselineManager receives concurrent writes. The research section explicitly names this as a hard sequential constraint. The joint HITL gate cannot be coordinated if the executor has already launched all three concurrently.
**How:** 
1. In Plan 10 frontmatter, change `depends_on: ["3.1c-08"]` to `depends_on: ["3.1c-08", "3.1c-09"]` — enforces Plan 09 completes before Plan 10 starts.
2. In Plan 11 frontmatter, change `depends_on: ["3.1c-08"]` to `depends_on: ["3.1c-08", "3.1c-10"]` — enforces Plan 10 completes before Plan 11 starts.
3. In Plan 09 frontmatter `must_haves` or `notes`, add: "Joint HITL gate: Plan 09 Core sub-wave (T1) and Plan 10 Core sub-wave (T1) must BOTH complete before any Important sub-wave begins. Plan 09's HITL checkpoint is the Joint HITL gate for both 09a and 10a — Plan 10 must have reached its own T1 completion before the joint gate can be evaluated. Coordinate with Plan 10 executor before proceeding to Important sub-wave."
**Impacts:** Plan 10 and Plan 11 dependency chains corrected. Wave 6 sequential execution enforced structurally rather than by convention.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Sequential dependency expression in task frontmatter is standard. The fix is mechanical.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — This dependency omission exists in the original plan files independent of any improvement pass. A first-time executor reading only the plan frontmatter hits this immediately.

### P19-IMP-02: Plan 03 Done Criteria Do Not Require Real Plan 02 Hook Payloads — Adapter Validated Against Incomplete Data
**Target:** PLAN-03
**What:** Plan 03 frontmatter correctly lists `depends_on: ["3.1c-01", "3.1c-02"]`. However, Plan 03 Task 2 done criteria for "validate on real transcripts" do not specify that the transcripts must contain `tool_use_id` fields produced by Plan 02's hooks. An executor can satisfy the done criteria using synthetic fixtures or transcripts captured before Plan 02's hooks were installed — both of which lack `tool_use_id`. The research confirms the `tool_use_id` field in hook payloads is a hard dependency for Plan 03's LIFO→tool_use_id fix.
**Why:** Specific failure: Plan 03 Task 2 done criteria appear satisfied (real transcripts validated, tests pass). But if the "real transcripts" predate Plan 02's hook installation, they contain no `tool_use_id` fields. The ObservationParser adapter's LIFO→tool_use_id refactor was tested against LIFO-format data only. When Plan 07's first real LLM evaluation call processes observations, the pairing logic fails silently — observations are dropped, not errored. Plan 07 Task 1 gate appears to pass (no exception) but produces unreliable dimension scores because observation coverage is lower than expected.
**How:** 
1. In Plan 03 Task 2 done criteria, change from "validated on real transcripts" to: "validated on real transcripts produced by Plan 02's hook implementation, confirmed via log inspection to contain `tool_use_id` fields in hook payload JSON — synthetic fixtures and pre-Plan-02-hook transcripts do not qualify."
2. In Plan 03 Task 2 action, add: "Before running validation, confirm that the transcript source directory contains at least one file with `tool_use_id` in its hook payload. Log the source directory and one example payload as evidence. If no tool_use_id-containing transcripts exist, STOP — Plan 02 Task 2 hooks are not yet installed."
**Impacts:** Plan 03 Task 2 done criteria become disk-observable and dependency-specific. Downstream Plan 07 receives correctly paired observations.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Dependency specification in done criteria is standard.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — The underspecified done criteria exist in the original Plan 03 file.

### P19-IMP-03: 3.1e Deferred Item 3 (Bridge Transformer ~150 LOC) Assigned to "Plan 05 or 06" But Absent from Both Plan Task Lists
**Target:** PLAN-05
**What:** CONTEXT.md assigns 3.1e deferred Item 3 (bridge transformer ~150 LOC) to "Plan 05 or 06." Plan 05's task list (Task 1: debrief cascade, Task 2: prompt template + tests) has no bridge transformer task. Plan 06's task list (Task 1: schema hardening, Task 2: 41 contracts) has no bridge transformer task. The bridge transformer converts Plan 02 hook payloads to Plan 07's EvaluationInput format. Without it, Plan 07's first real LLM call gate receives malformed input.
**Why:** Specific failure: Plan 07 Task 1, action "First real LLM call gate" — the gate requires valid `EvaluationInput` objects. These are produced by the bridge transformer from Plan 02 hook payloads. If bridge.py does not exist, Plan 07 Task 1 either (a) raises an import error, (b) receives None inputs and passes a vacuous gate, or (c) the executor discovers the gap during HITL review and must diagnose the missing 3.1e item without documentation pointing back to Plan 05. Option (c) is the most likely and most expensive: Plans 01-06 have completed, HITL is active, and the missing deliverable requires re-opening a completed plan.
**How:** 
1. In Plan 05, add Task 3 with title "Implement Bridge Transformer (3.1e Item 3, ~150 LOC)." Action: "Implement `bridge.py` in the evaluation pipeline package directory. The bridge transformer is an adapter class with a single method `transform(hook_payload: dict) -> EvaluationInput`. Input schema: Plan 02 hook payload JSON (fields: tool_use_id, timestamp, session_id, raw_observation, hook_type). Output schema: `EvaluationInput` (fields: dimension, move_type, evidence_excerpt, session_id, tool_use_id). Include a null-safety path: if hook_payload lacks tool_use_id, log a warning and return None (callers filter None). Validate against at least one real Plan 02 hook payload fixture." Done criteria: "`bridge.py` exists in evaluation pipeline package, unit tests pass against real Plan 02 hook payload fixture, `EvaluationInput` output validates against Plan 07 schema."
2. Update Plan 05 `must_haves` to include: "bridge.py implemented and validated against Plan 02 hook output format before Plan 05 is marked complete — Plan 07 Task 1 cannot proceed without it."
3. In Plan 07 Task 1 action, add as first step: "Verify `bridge.py` exists in the evaluation pipeline package. If absent, STOP — Plan 05 Task 3 is incomplete. Do not proceed to Phase 0 gates."
**Impacts:** Plan 05 gains a deliverable task for a 3.1e committed item. Plan 07 Task 1 gate has an explicit prerequisite check.
**Research needed:** no — the 3.1e deferred item specification provides the ~150 LOC estimate and format description.
**Confidence:** HIGH
**Prior art:** 1 — Adapter/bridge pattern is established; the specific schema conversion for this evaluation pipeline is novel.
**Prerequisite:** no — Plan 02 must complete first (providing hook output format), already captured in Plan 05's depends_on chain.
**Status:** implemented
**Origin:** NOVEL — The missing task exists in the original plan files independent of any improvement pass.

### P19-IMP-04: 3.1e Deferred Items 4+5 (Self-Evaluation Check, Construct Disambiguation) Have No Tasks in Plan 01 or Plan 09
**Target:** PLAN-01
**What:** CONTEXT.md assigns Item 5 (construct disambiguation as schema pre-condition) explicitly to Plan 01, and Item 4 (self-evaluation check) to "Plan 01 or 09." Plan 01 Task 1 (Pydantic models + Track A/B/C annotation) and Task 2 (SKILL.md stub) contain neither. Plan 09 Task 1 (complete SKILL.md, Gate 0 dry-run, pre-flight activation test) contains no self-evaluation check. Research confirms both absences. Item 5 is flagged as a schema pre-condition for Plan 06's dimension registry.
**Why:** Item 5 being a schema pre-condition means Plan 06's dimension registry (27+ dims) may contain dimensions with overlapping behavioral signatures. Specific failure chain: Plan 01 builds Pydantic models without construct disambiguation → Plan 06 registers 27+ dimensions with no overlap check → Plan 07 evaluates against ambiguous dimensions → dimension scores are unreliable but no gate rejects them → Plan 12's calibration anchor shows high variance → Plan 12 Task 3's intelligence modules attribute the variance to "agent behavior" → 3.1f handoff artifacts contain a false conclusion that propagates to the next phase.
**How:** 
1. In Plan 01 Task 1 action steps, add: "Implement construct disambiguation as a `disambiguation_check()` classmethod on the base dimension Pydantic model (3.1e deferred Item 5). The method accepts a registry of all registered dimensions and raises `ConstructAmbiguityError` if this dimension's `behavioral_signature` overlaps with another registered dimension's signature by more than a defined threshold. This is a schema pre-condition: Plan 06 Task 1 must call `disambiguation_check()` on each registered dimension before the registry is finalized."
2. In Plan 01 Task 1 done criteria, add: "`disambiguation_check()` callable on all dimension models" and "at least one pytest case raises `ConstructAmbiguityError` on a deliberately overlapping dimension pair."
3. In Plan 09 Task 1 action steps, add: "Implement self-evaluation check (3.1e deferred Item 4): before scoring agent runs, verify the evaluator's own outputs on a held-out calibration sample fall within expected variance bounds. Produce `.vrs/experiments/plan-09/self-eval-check.json` with schema `{verdict: 'PASS'|'FAIL', evaluator_variance: float, threshold: float, sessions_checked: int}`." In Plan 09 Task 1 done criteria, add: "self-eval-check.json exists with `verdict: PASS`."
**Impacts:** Plan 01 gains two missing deliverables. Plan 06 Task 1 gains an upstream schema pre-condition it must invoke. Plan 09 Task 1 gains a verifiable self-evaluation artifact.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 2 — Construct disambiguation exists in psychometrics; adaptation to LLM evaluation dimension schemas requires domain knowledge not in standard references.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — Missing tasks exist in the original plan files independent of improvement passes.

### P19-IMP-05: Plan 02 Missing GO/NO-GO Gate Task — Track B Finalization Has No Executable Decision Point and Plan 04 Permission Gate Has No Upstream Producer
**Target:** PLAN-02
**What:** 3.1e deferred Item 1 is the "GO confirmation gate" — an explicit evaluation of captured transcripts producing a GO/NO-GO decision that unlocks Track B across all plans. Item 2 (validity re-scoring) is the mechanism. Plan 02 Task 1 captures transcripts and Task 2 implements 6 hooks, but no task runs validity re-scoring or produces a GO/NO-GO verdict. Research confirms: "NO explicit GO/NO-GO gate task for 3.1e deferred Item 1" and "NO explicit validity re-scoring task for 3.1e deferred Item 2."
**Why:** Specific failure: Executor completes Plan 02 Task 1 (transcripts captured) and Task 2 (hooks implemented). Plan 02 is marked complete. Plans 03-08 proceed. Plan 04 Task 1 reads validity-matrix.json — file is absent (never produced) or stale from 3.1e. Plan 04 Task 1 gate fails. The executor faces a dead end: validity-matrix.json was supposed to come from Plan 02, but Plan 02 is already marked complete and has no task that produces it. Reopening a completed plan without documentation of this dependency loop wastes significant execution time.
**How:** 
1. Add Task 3 to Plan 02 with title "GO/NO-GO Gate: Track B Finalization (3.1e Items 1+2)." Action: "For each transcript captured in Task 1: run validity re-scoring — verify session has > N tool calls (define N from 3.1e specification), no PreCompact truncation in session log, no cache-replay signature (check for identical tool outputs across sessions). Produce `.vrs/experiments/plan-02/transcript-validity-report.json` with per-transcript fields: `{transcript_id, verdict: 'GO'|'NO-GO', tool_call_count, precompact_detected: bool, cache_replay_detected: bool}`. If fewer than 3 transcripts receive GO verdict, STOP — capture additional real transcripts before proceeding. On success, update `.vrs/experiments/plan-03-04/validity-matrix.json` with Plan 02 entry: `{plan: '3.1c-02', gate_timestamp: ISO8601, go_transcripts: [transcript_id...], verdict: 'GO'}`." Done criteria: "`transcript-validity-report.json` exists with >= 3 GO verdicts" and "`validity-matrix.json` contains Plan 02 GO entry."
2. In Plan 02 `must_haves`, add: "Plan 02 is NOT complete until Task 3 GO gate produces >= 3 valid transcripts and validity-matrix.json is updated. Plans 03+ MUST NOT begin until this gate passes."
3. In Plan 04 Task 1 action, update the `validity-matrix.json` permission gate note to: "This file is produced by Plan 02 Task 3. If file is absent or lacks Plan 02 GO entry, Plan 02 is incomplete — do not proceed with Plan 04."
**Impacts:** Plan 02 gains an explicit gate task with disk-observable done criteria. Plan 04 Task 1 permission gate has a documented upstream producer. Track B finalization is no longer implicit.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — GO/NO-GO gates with disk-observable artifacts are standard in multi-phase engineering.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — The missing gate task exists in the original Plan 02 files.

### P19-IMP-06: Plan 07 and Plan 12 HITL Checkpoints Are Unnumbered Tasks With No Disk-Observable Done Criteria — Human Review Silently Skipped
**Target:** PLAN-07
**What:** Plan 07 has Task 1 (auto) and Task 3 (auto), with the HITL checkpoint described as "acts as Task 2 — not numbered." Plan 12 has the same pattern: Task 1 (auto, Part 0) and Task 3 (auto, Part 1), with an unnumbered HITL checkpoint between them. The checkpoints have no task ID, no done criteria, and produce no disk artifact. An executor completing Task 1 sees Task 3 as the next executable task and proceeds directly. The autonomous=false designation for both plans is not enforced structurally.
**Why:** Specific failure for Plan 07: autonomous=false exists because Task 1's first real LLM call (`_llm_evaluate_dimension()`) outputs require human validation before Task 3's blind-then-debate protocol is built on top. If the checkpoint is silently skipped, Task 3 executes on unvalidated LLM evaluator outputs. Plan 08 builds its pipeline on top of an unvalidated evaluator. Plan 12's calibration anchor (72 sessions) uses an evaluator that was never validated at its first gate — systematic evaluator bias introduced at Plan 07 Task 1 propagates through Plans 08, 09, 10, 11, and 12 before being diagnosable.
**How:** 
1. In Plan 07, formalize the checkpoint as Task 2 with title "HITL Gate: Phase 0 LLM Evaluator Validation." Action: "Human reviewer inspects Task 1 outputs: (a) Phase 0 gate a/b/c pass/fail results, (b) at least one complete `_llm_evaluate_dimension()` output (prompt sent + response received + score extracted), (c) DIMENSION_TO_MOVE_TYPES mapping coverage. Produces disk artifact: `.vrs/experiments/plan-07/hitl-gate-01.json` with schema `{decision: 'GO'|'NO-GO', reviewer: string, timestamp: ISO8601, issues: string[], notes: string}`. On NO-GO: document specific issue in `issues` array, revise Task 1 outputs, repeat." Done criteria: "`.vrs/experiments/plan-07/hitl-gate-01.json` exists with `decision: 'GO'`."
2. In Plan 07 Task 3, add as first action step: "Verify `.vrs/experiments/plan-07/hitl-gate-01.json` exists and contains `decision: 'GO'`. If absent or NO-GO, STOP — Task 2 HITL gate has not passed."
3. In Plan 12, formalize the checkpoint as Task 2 with title "HITL Gate: Calibration Anchor Review." Action: "Human reviewer inspects Task 1 results: (a) 72-session calibration anchor summary, (b) infrastructure diagnostic output, (c) Goodhart screen verdict. Produces `.vrs/experiments/plan-12/hitl-gate-01.json` with same schema." Done criteria: "`.vrs/experiments/plan-12/hitl-gate-01.json` exists with `decision: 'GO'`."
4. In Plan 12 Task 3, add as first action step: "Verify `.vrs/experiments/plan-12/hitl-gate-01.json` exists with `decision: 'GO'`. If absent or NO-GO, STOP."
**Impacts:** Plan 07 HITL checkpoint becomes disk-observable and executor-verifiable. Plan 12 HITL checkpoint gains same property. autonomous=false semantics are enforced structurally rather than by convention.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — HITL gate artifacts with disk-observable decision records are standard in human-in-the-loop pipeline design.
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — The missing task formalization exists in the original plan files. Any executor reading Plans 07 or 12 encounters this on first pass.

### P19-IMP-07: Wave 1 Parallelism Contradiction Causes Plan 06 to Fail
**Target:** PLAN-06
**What:** Plan 06 frontmatter correctly states `depends_on: ["3.1c-01"]`, but CONTEXT.md Wave 1 description states "zero dependencies" for Plan 06. Any executor that reads the wave description as authoritative will attempt to parallelize 01 and 06 within Wave 1, causing Plan 06 Task 1 ("Schema hardening + dimension registry") to fail because it requires Plan 01's Pydantic models as inputs — there are no models to harden yet.
**Why:** The contradiction between the wave description and the frontmatter creates a genuine ambiguity. An executor reading "Wave 1: [3.1c-01] + [3.1c-06] (zero dependencies)" will not check the frontmatter `depends_on` field because the wave description already appears to answer the ordering question. This is a silent failure: Plan 06 Task 1 will import models that don't exist yet, produce an ImportError or empty schema, and the executor may not connect the cause (wrong wave ordering) to the symptom.
**How:** 
1. In PLAN-06 frontmatter, add a `note` field or inline comment: "Wave 1 execution is SEQUENTIAL not parallel. Plan 06 MUST start after Plan 01 Task 2 is complete (models.py exists). The CONTEXT.md Wave 1 'zero dependencies' label refers to upstream phase dependencies, not intra-wave ordering."
2. In PLAN-06 Task 1 action step, add a prerequisite check as the first action: "Verify `src/alphaswarm_sol/testing/evaluation/models.py` exists and contains at least ReasoningAssessment, CalibrationConfig, and EvaluatorConstants before proceeding. If missing, STOP — Plan 01 has not completed."
**Impacts:** Plan 06 confidence MEDIUM -> HIGH (removes silent failure mode)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — dependency declaration vs. wave description conflict is a known CI/CD ordering problem with established solutions (explicit sequential markers)
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the wave description vs. frontmatter contradiction exists in CONTEXT.md independent of any prior improvement pass content

### P19-IMP-08: Wave 2 Sequential Dependency Between Plan 02 and Plan 03 Not Encoded
**Target:** PLAN-03
**What:** Plan 03 `depends_on: ["3.1c-01", "3.1c-02"]` correctly lists 02 as a dependency, but both 02 and 03 are `wave: 2`. The CONTEXT.md execution order states "02 -> 03" sequentially. Any executor that interprets wave membership as parallelism eligibility will start 03 before 02 completes. Plan 03 Task 1 ("Refactor ObservationParser as TranscriptParser adapter") requires `transcript_parser.py` from Plan 02 and the real `tool_use_id` hook payload — neither exists until Plan 02 Task 2 completes. This is not just a file-missing error; the adapter validation in Plan 03 Task 2 explicitly references `@3.1c-02-SUMMARY.md`, which doesn't exist until Plan 02 finishes.
**Why:** Unlike Plan 06 (where the wave description says "zero dependencies"), Plan 03 correctly lists the dependency in frontmatter. The risk is executors using wave-based scheduling that treats same-wave plans as parallelizable after all upstream waves complete. A task scheduler that launches all Wave 2 plans simultaneously will create a race condition: 03 needs 02's outputs, but 02 may not have produced them.
**How:** 
1. In PLAN-03 frontmatter, change `wave: 2` to `wave: 2b` (or add a `sequence_within_wave: 2` field), and add a plan-level note: "Within Wave 2, Plan 03 is sequentially AFTER Plan 02. Do not start Plan 03 until Plan 02 is fully ALIGNED."
2. In PLAN-03 Task 1 action steps, add as first action: "Confirm `hooks/transcript_parser.py` exists and `TranscriptParser.to_observation_summary()` is implemented (Plan 02 Task 1 output). Confirm at least one real session exists in `fixtures/real_sessions/`. If either is missing, STOP."
**Impacts:** Plan 03 confidence MEDIUM -> HIGH
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — same-wave sequential dependency is a standard pipeline ordering problem
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the intra-wave sequential dependency gap exists in the original plan structure regardless of improvement passes

### P19-IMP-09: Plans 09/10/11 Missing Sequential Ordering Creates BaselineManager Corruption Risk
**Target:** PLAN-10
**What:** Plans 09, 10, and 11 all have `depends_on: ["3.1c-08"]` and `wave: 6`. CONTEXT.md states they "execute SEQUENTIALLY within Wave 6 (shared progress.json and BaselineManager prevent concurrent writes)." The plans themselves have no frontmatter encoding this sequential ordering — an executor using a wave-based scheduler would launch all three concurrently. Plan 10 references `@3.1c-09-SUMMARY.md` and Plan 11 references `@3.1c-10-SUMMARY.md`, but these summary files are only created when the prior plan completes. Concurrent execution causes Plan 10 to start without 09's summary (silently missing skill evaluation data in the shared BaselineManager), and Plan 11 to start without 10's summary.
**Why:** BaselineManager concurrent writes are explicitly flagged as the reason for sequential execution. If 09 and 10 write to `progress.json` simultaneously, the later write silently overwrites partial data. This is not a crash — it's silent data corruption in the baseline, which propagates into Plan 12's calibration anchor. The calibration anchor with corrupted baseline data will produce wrong thresholds that persist into 3.1f.
**How:** 
1. In PLAN-10 frontmatter, change `depends_on: ["3.1c-08"]` to `depends_on: ["3.1c-08", "3.1c-09"]`. Add note: "Sequential within Wave 6. BaselineManager and progress.json are shared with Plans 09 and 11 — concurrent writes will corrupt baseline data."
2. In PLAN-11 frontmatter, change `depends_on: ["3.1c-08"]` to `depends_on: ["3.1c-08", "3.1c-09", "3.1c-10"]`. Add note: "Sequential within Wave 6. Must start after Plan 10 is fully ALIGNED. Requires @3.1c-10-SUMMARY.md to exist."
**Impacts:** Plans 10 and 11 ordering integrity. Plan 12 calibration correctness depends on this being fixed.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — concurrent write prevention via sequential dependency is standard practice
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the frontmatter gap (09/10/11 all showing `depends_on: ["3.1c-08"]` only) exists in the plans as authored, not introduced by improvement passes

### P19-IMP-10: 3.1e Deferred Item 3 (Bridge Transformer ~150 LOC) Has No Plan Owner
**Target:** PLAN-05
**What:** CONTEXT.md research section states Item 3 (bridge transformer, ~150 LOC) is assigned to "Plan 05 or 06." Plan 05's task list covers the four-layer debrief cascade, debrief_gate.py, debrief_task_complete.py, and integration tests. Plan 06's task list covers schema hardening and evaluation contracts. Neither plan has a task that mentions "bridge transformer" or the ~150 LOC implementation. An executor reading Plan 05 or Plan 06 will not discover they are responsible for this deliverable — it exists only in CONTEXT.md's deferred items table, which executors may not cross-reference mid-plan.
**Why:** This is a concrete missing deliverable, not an ambiguity. Item 3 bridges observation data to evaluation input format — without it, Plan 07 (Reasoning Evaluator) cannot receive properly formatted input from Plans 04/05. The gap is silent: Plan 07 will fail at runtime when it attempts to consume bridge transformer output that was never built, and the executor will blame Plan 07's implementation rather than the missing upstream deliverable.
**How:** 
1. In PLAN-05, add Task 3 (after Task 2): "Implement bridge transformer (~150 LOC). File: `src/alphaswarm_sol/testing/evaluation/bridge_transformer.py`. Transforms ObservationSummary (Plan 03 output) into ReasoningEvaluator input format. Gate: only implement if Item 1 GO confirmation received in Plan 02. If Item 1 is NO-GO, create a stub with NotImplementedError and a clear docstring explaining the gate." Done criteria: `bridge_transformer.py` exists, `transform(ObservationSummary) -> EvaluatorInput` passes a round-trip test with a fixture session.
2. In PLAN-05 frontmatter `must_haves`, add: "bridge_transformer.py exists at the expected path, contains transform() method, and has at least one passing test."
**Impacts:** Plan 05 scope increase (one task added). Plan 07 confidence LOW -> MEDIUM (removes upstream dependency gap).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — bridge/adapter patterns between pipeline stages are common; the specific 150 LOC scope estimate comes from 3.1e research
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the missing task is a gap in the plan as authored. The 3.1e deferred items mapping predates pass 19.

### P19-IMP-11: Plan 12 Task Numbering Gap (Task 2 Missing) Will Confuse Executor
**Target:** PLAN-12
**What:** Plan 12 task sequence is: Task 1 (auto) → HITL checkpoint → Task 3 (auto). Task 2 is missing from the numbering. The HITL checkpoint is not numbered as Task 2, leaving a gap. An executor seeing "Task 1... Task 3" will either: (a) search for a missing Task 2 and waste time, (b) assume the plan is incomplete, or (c) incorrectly treat the HITL checkpoint as Task 2 and skip it (since their tooling may look for numbered tasks only).
**Why:** HITL checkpoints in other plans (07, 09, 10) are similarly positioned between numbered tasks but the gap is not created there because those plans go 1 → HITL → 3 only in Plan 12. The risk is an autonomous executor skipping the HITL checkpoint because it's not numbered. Plan 12 is `autonomous: false`, which means HITL is mandatory — skipping it would allow the calibration anchor to proceed without human review of the Infrastructure Diagnostic output.
**How:** 
1. In PLAN-12, renumber the HITL checkpoint as "Task 2 (HITL checkpoint)" explicitly, making the sequence Task 1 → Task 2 (HITL) → Task 3. Update the task header to read: "Task 2: HITL Checkpoint — Human review of Infrastructure Diagnostic and CalibrationConfig before proceeding to baseline establishment."
2. In PLAN-12 Task 2 done criteria, add: "Human has reviewed and explicitly approved Infrastructure Diagnostic output. Approval recorded in session notes. Calibration config thresholds confirmed as reasonable before Task 3 begins."
**Impacts:** Plan 12 executor clarity. No plan dependencies affected.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — sequential task numbering with no gaps is standard practice in any plan format
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the numbering gap is a structural flaw in PLAN-12 as authored

### P19-IMP-12: 3.1e Deferred Item 4 (Self-Evaluation Check) Has Ambiguous Plan Assignment
**Target:** PLAN-01
**What:** CONTEXT.md research section states Item 4 (self-evaluation architectural constraint) is assigned to "Plan 01 or Plan 09." Plan 01 task list covers Pydantic models, SKILL.md stub, and SuiteExitReport schema. Plan 09 covers skill evaluation execution. Neither plan has a task explicitly implementing the self-evaluation check. The ambiguity "Plan 01 or 09" is unresolved — an executor reading Plan 01 will not add a self-evaluation constraint (it looks like models work), and an executor reading Plan 09 will assume Plan 01 handled it.
**Why:** Item 4 is an architectural constraint that must be encoded somewhere before evaluation runs. If it is not in any plan task, it will not be built. Self-evaluation (an agent evaluating its own transcript) is listed as a potential validity threat in CONTEXT.md — if it occurs undetected, evaluation scores are invalid. The constraint must be enforced either in the data model (Plan 01) or in the runner gate (Plan 09). "Plan 01 or 09" leaves both plans able to assume the other handled it.
**How:** 
1. In PLAN-01 Task 1, add an action step: "Add `self_evaluation_guard: bool = True` field to EvaluationConfig. Add a validator that raises ValueError if the evaluator session_id matches the evaluated session_id. Document as Item 4 self-evaluation architectural constraint." This resolves the ambiguity by making Plan 01 the owner.
2. In PLAN-01 Task 2 done criteria, add: "EvaluationConfig rejects self-evaluation (evaluator_session == evaluated_session raises ValueError) with a test case confirming rejection."
**Impacts:** Plan 01 scope (minor addition). Removes Item 4 ownership ambiguity.
**Research needed:** no
**Confidence:** MEDIUM — the right layer (model vs. runner guard) is an architectural choice; placing it in Plan 01 models is the lower-risk option since it enforces the constraint earliest in the pipeline
**Prior art:** 3 — self-reference guards in evaluation pipelines are known patterns (e.g., cross-validation exclusion rules)
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the "Plan 01 or 09" ambiguity in CONTEXT.md is a genuine gap not introduced by any improvement pass

### P19-IMP-13: Joint 09a+10a HITL Gate Not Reflected in Either Plan 09 or Plan 10 Frontmatter
**Target:** PLAN-09
**What:** CONTEXT.md Cross-Plan Dependencies states: "09a+10a joint HITL gate must pass before 09b+10b+11 Important sub-waves." Plan 09 Task 3 (Important + Standard sub-waves) has a HITL checkpoint before it, but that checkpoint is described as Plan 09's internal gate, not as a joint gate with Plan 10. An executor running Plan 09 will pass its own HITL checkpoint and proceed to 09b without knowing that Plan 10's 10a must also be complete. Similarly, Plan 10 has its own internal HITL but no knowledge that it must coordinate with Plan 09's gate.
**Why:** The joint gate exists because the Core sub-waves (09a + 10a) together produce the baseline signal needed to judge whether Important sub-waves are worth running. If the executor treats these as independent HITL checkpoints, they may approve 09b before 10a completes, causing 09b to run against an incomplete baseline. This is not caught by test failures — 09b runs "successfully" but its Important-tier results are compared against a baseline that doesn't include Core agent scores from 10a.
**How:** 
1. In PLAN-09 Task 3 action steps (before Important sub-wave tasks), add: "JOINT GATE: Confirm @3.1c-10-SUMMARY-CORE.md exists (Plan 10 Task 1 complete) before proceeding to Important sub-wave. This joint gate (09a+10a) is defined in Cross-Plan Dependencies. If Plan 10 Task 1 is not complete, PAUSE here."
2. In PLAN-09 frontmatter `must_haves`, add: "Important sub-wave (09b) does not begin until Plan 10 Task 1 (Core agent evaluations) is confirmed complete."
**Impacts:** Plan 09 execution sequencing. Plan 11 indirectly benefits (11's Important sub-wave also needs both 09a+10a).
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — joint gate / rendezvous barrier patterns are standard in parallel pipeline coordination
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the cross-plan joint gate is documented in CONTEXT.md but not encoded in either plan's tasks or frontmatter

### P19-IMP-14: Stale CONTEXT.md Line Number References Across All 12 Plans
**Target:** PLAN-01
**What:** Every plan references specific line ranges in CONTEXT.md: Plan 01 cites "lines 1853-1990," Plan 02 cites "lines 1992-2075" and "lines 1740-1800," Plan 08 cites "lines 2373-2481" and "lines 2436-2474," etc. After 17 improvement passes that merged 373 items into a 3340-line CONTEXT.md, these line numbers are almost certainly wrong. An executor using these line references to load implementation decisions will read the wrong sections. The risk is highest for Plans 07, 08, and 12, which reference two CONTEXT.md ranges each — a navigator loading both stale ranges may miss the actual relevant section entirely.
**Why:** This is an executor-facing failure, not a design flaw. An executor that dutifully loads "lines 2373-2481" from the current 3340-line CONTEXT.md will read whatever content happens to be at those lines today — which may be a different plan's section, a merged improvement item, or a cross-phase alignment block. This produces incorrect implementation choices silently, since the executor has no way to know the content drifted.
**How:** 
1. In PLAN-01, PLAN-02, PLAN-03, PLAN-04, PLAN-05, PLAN-06, PLAN-07, PLAN-08, PLAN-09, PLAN-10, PLAN-11, and PLAN-12: replace all `@3.1c-CONTEXT.md (lines NNN-NNN, ...)` references with section-name anchors. For example, replace `@3.1c-CONTEXT.md (lines 1853-1990, Plan 01 section)` with `@3.1c-CONTEXT.md (section: "Plan 01: Assessment Data Structures")`. This makes the reference robust to line-number drift.
2. As an immediate verification step executable now: in PLAN-08 verify that the content at lines 2373-2481 of the current CONTEXT.md actually covers the Plan 08 section. If it does not, the stale reference problem is confirmed and all 12 plans need the section-name fix urgently before executor handoff.
**Impacts:** All 12 plans. If stale references cause executors to load wrong sections, implementation decisions made in passes 1-17 are invisible to the executor — the entire improvement investment is wasted.
**Research needed:** no — the line drift is deterministic given 17 improvement passes with 373 merged items
**Confidence:** HIGH
**Prior art:** 5 — section-name anchors vs. line-number references is standard documentation practice
**Prerequisite:** no
**Status:** implemented
**Origin:** NOVEL — the stale line reference problem is a structural gap that predates all improvement passes and was not addressed in any of the 373 merged items


## Convergence Assessment

**Novel improvements:** 6
**Filtered observations (not proposed):**
- DERIVATIVE: 0
- DEDUCIBLE: 0 — all items require cross-referencing plan task lists against the CONTEXT.md research section and 3.1e deferred item table; none are discoverable from a single read-through of one file
**Cosmetic (of novel):** 0
**Self-justification ratio:** 0%

All 6 items are structural execution blockers discoverable from the original plan files:
- IMP-01: Missing sequential dependencies in Plan 10+11 frontmatter — executor parallelizes Wave 6, corrupts BaselineManager
- IMP-02: Plan 03 Task 2 done criteria underspecified — adapter validated against pre-hook transcripts, fails silently on real data
- IMP-03: Bridge transformer (3.1e Item 3) unassigned to any plan task — Plan 07 gate fails with opaque diagnostic path
- IMP-04: 3.1e Items 4+5 unassigned in Plan 01 and Plan 09 — schema pre-condition missing, self-evaluation check falls through
- IMP-05: No GO/NO-GO gate task in Plan 02 — Track B implicit, Plan 04 permission gate has no upstream producer
- IMP-06: HITL checkpoints in Plans 07+12 unnumbered with no done criteria — human review silently skipped, evaluator bias propagates

No self-justifying loop detected. All items would exist if prior improvement passes had never run.


## Convergence Assessment

**Novel improvements:** 8
**Filtered observations (not proposed):**
- DERIVATIVE: 0
- DEDUCIBLE: 0 — all items require cross-referencing multiple plan files, frontmatter, and CONTEXT.md simultaneously; none are visible from a single read-through

**Cosmetic (of novel):** 0 — all 8 items are structural (execution failure risk)

**Self-justification ratio:** 0% — no items address inconsistencies introduced by prior passes; all address gaps in the plan files as authored

**Summary of structural failure modes covered:**
1. IMP-01: Plan 06 wave label vs. frontmatter contradiction → silent parallelism failure
2. IMP-02: Plan 03 same-wave sequential dependency not encoded → race condition
3. IMP-03: Plans 09/10/11 frontmatter missing sequential ordering → BaselineManager corruption
4. IMP-04: Bridge transformer (~150 LOC) has no plan owner → missing deliverable
5. IMP-05: Plan 12 Task 2 numbering gap → executor confusion / HITL skip risk
6. IMP-06: Item 4 self-evaluation check "Plan 01 or 09" ambiguity → neither plan owns it
7. IMP-07: Joint 09a+10a gate not in either plan's tasks → premature Important sub-wave execution
8. IMP-08: Stale line-number references in all 12 plans → executor loads wrong CONTEXT.md sections

