# Improvement Pass 13

**Pass:** 13
**Date:** 2026-02-20
**Prior passes:** 12 (261 merged, 12 rejected, 14 reframed, 1 active from P11)
**Areas:** Observation Pipeline (Plans 02, 03), Scoring Engine (Plans 04, 05)
**Agents:** 12 (4 improvement + 6 adversarial + 1 synthesis + 1 ADV validation)
**Status:** complete

## Pipeline Status

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 2 (P11-IMP-10, P13-IMP-19) | 0 | Plan 02 real transcripts, Plan 02/03 timestamps |
| Research | 6 | 0 | IMP-08 Track B, IMP-10, IMP-11, ADV-1-01, ADV-2-01, ADV-4-01 |
| Gaps | 0 | 13 | — |
| Merge-ready | 19 | 0 | — |

**Pipeline:** `[prereqs: 2 pending] → [research: 6 pending] → [merge: 19 ready] → [implement]`
**Next:** `/msd:resolve-blockers 3.1c` (pre-implement → research-gap)

**Post-validation status breakdown:**
- Enhanced: 11 (IMP-01, IMP-05, IMP-06, IMP-07, IMP-08, IMP-10, IMP-16, IMP-18, IMP-19, ADV-1-03, ADV-2-01)
- Confirmed: 15 (IMP-09, IMP-11, IMP-12, ADV-1-01, ADV-1-02, ADV-2-02, ADV-3-01, ADV-3-02, ADV-4-01, ADV-4-02, ADV-5-01, ADV-6-01, SYN-01, SYN-02, CSC-01)
- Reframed: 6 (IMP-02, IMP-14, IMP-15, IMP-21, IMP-22, IMP-23)
- Rejected: 6 (IMP-03, IMP-04, IMP-13, IMP-17, IMP-20)
- Net actionable: 27 (12 enhanced/confirmed originals + 12 ADV + 3 SYN/CSC, all validated)

## Improvements

---

### AREA: Observation Pipeline (Plans 02, 03) — Standard Analysis

---

### P13-IMP-01: PostToolUse Hooks Use Wrong Field Name — Silent Data Loss
**Target:** CONTEXT
**What:** Both `obs_tool_result.py` (line 26) and `obs_bskg_query.py` (line 40) read `input_data.get("tool_output", "")`. The official CC PostToolUse schema uses `tool_response`, not `tool_output`. Every PostToolUse hook silently captures empty strings for result data. GVS cannot differentiate BSKG-query-that-returned-data from BSKG-query-that-failed — the primary scoring signal is permanently blind.
**Why:** This is a data loss bug. Every downstream consumer (Plans 03, 04, 07) receives hollow data. The BSKG result node ID extraction specified in Plan 02 deliverable 5 will NEVER work until this is fixed. Note: `tool_response` is a dict for most tools requiring the existing `str()` cast.
**How:**
1. In `obs_tool_result.py` line 26: change `input_data.get("tool_output", "")` to `input_data.get("tool_response", "")`.
2. In `obs_bskg_query.py` line 40: same substitution.
3. Note: `tool_response` for PostToolUse is a dict (per docs), not a plain string. The `str(tool_output)[:500]` cast must remain since the value may be dict, list, or str.
4. Add integration test: fire a real or mock PostToolUse event, assert `result_length > 0`.
5. Plan 02 exit criterion must name this field fix as a HARD EXIT CRITERION.
**Impacts:** Plan 02 (HARD blocker), Plan 04 GVS, Plan 03
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented
**Adversarial note (Platform Schema Bugs):** The docs confirm `tool_response` unambiguously. The bug was never caught because zero real transcripts exist — hooks were never validated against live sessions. The `str()` serialization should confirm dict-to-string coercion works correctly in `obs_bskg_query.py` which filters for Bash results specifically.

### P13-IMP-02: Hook Enum Contains Factually Wrong Locked Decision About PermissionRequest
**Target:** CONTEXT
**What:** CONTEXT.md line 234-236 contains a locked Implementation Decision from P11-IMP-01 stating "removed PermissionRequest which is not a distinct hook event." The CC docs unambiguously list PermissionRequest as a distinct event with its own input schema and decision control section. This locked decision is factually wrong. The confirmable event count from docs is 12 standard + potentially Setup (13-14). TeammateIdle and TaskCompleted in the current enum need sourcing — they are NOT in the CC hooks lifecycle table.
**Why:** If the locked decision text stays wrong, future improvement passes will keep re-removing PermissionRequest. The root error must be corrected at source.
**How:** See P13-ADV-2-01 (CREATE) for the corrected action plan.
**Impacts:** Plan 06 (schema enum)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** reframed
**Adversarial note (Platform Schema Bugs):** The "15 events" claim in the original had no sourcing. TeammateIdle and TaskCompleted may be Agent Teams SDK additions that postdate the doc snapshot, or fabricated — highest-risk unverified assumption in the hooks section. The REFRAME companion (ADV-2-01) carries the corrected framing.

### P13-IMP-03: Prompt-Type Hooks Can Transform Debrief Layer 3
**Target:** CONTEXT
**Status:** rejected
**Adversarial note (Debrief Value):** Directly contradicted by locked Implementation Decision. BUG #20221 flags `type: "prompt"` SubagentStop hooks as BROKEN. The item also misidentifies the target: Layer 3 is keyword-heuristic transcript extraction, not an LLM shell-out. A prompt-type hook would instrument Layer 1 or 2, not Layer 3. Merging this would inject a factual error into a locked decision table.

### P13-IMP-04: transcript_path Enables Direct Transcript Reading — obs_precompact Design Should Use It
**Target:** CONTEXT
**Status:** rejected
**Adversarial note (Compaction Resilience):** The "no TranscriptParser import" constraint is a locked architectural decision (P11-ADV-1-02, CONTEXT.md lines 598-607) with a specific failure-mode justification: if Python path is misconfigured in the hook subprocess, the import fails silently, the compacted marker is never written, and compaction-aware debrief degrades to 7 detailed questions with no error signal. The inline JSONL parsing in obs_precompact is ~15 LOC — below the 20-LOC threshold that triggered this item. No action required.

### P13-IMP-05: obs_session_start.py Ignores `source` and `agent_type` Fields
**Target:** CONTEXT
**What:** `obs_session_start.py` captures only `session_id`, `cwd`, and `model`. The CC SessionStart input schema also provides `source` (values: `"startup"`, `"resume"`, `"clear"`, `"compact"`) and conditionally `agent_type`. The `source` field is operationally critical: a session starting from `"compact"` means the evaluation must not score reasoning continuity. A session from `"resume"` means the agent has prior context the evaluator cannot see.
**Why:** Without `source`, the runner cannot distinguish session types. The `source == "compact"` provides a second confirmation path alongside PreCompact's `.compacted` marker.
**How:**
1. In `obs_session_start.py`, add `source` and `agent_type` to the data dict.
2. Update `ObservationParser` to extract `source` from session_start records.
3. Plan 08 runner: if `source in ("compact", "resume")`, annotate `EvaluationResult.metadata` with `session_continuity: partial`.
4. Add unit test: mock SessionStart input with `source: "compact"` and `agent_type: "Explore"`, verify both appear in written JSONL.
**Impacts:** Plan 02 (~5 LOC), Plan 03 (dual-detection path with PreCompact), Plan 08
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented
**Adversarial note (Platform Schema Bugs):** Correct per docs. Second-order: `source == "compact"` creates dual-detection path with PreCompact's `.compacted` marker. Plan 03 must handle both without double-counting.

### P13-IMP-06: SubagentStart Input Schema Differs From Plan 02 Deliverable 4 Specification
**Target:** CONTEXT
**What:** Plan 02 deliverable 4 specifies capturing `task_description` and `parent_session_id` — neither exists in the CC SubagentStart schema. The actual schema provides: `session_id`, `transcript_path`, `cwd`, `permission_mode`, `hook_event_name`, `agent_id`, `agent_type`. These fields were designed into CONTEXT.md without runtime verification — the same root failure mode as IMP-01 but with invented fields rather than a misspelled real field.
**Why:** Implementers will either write empty strings or waste time. Attribution via `agent_type` only works when agents use named types. Anonymous Task spawns will show generic `agent_type`.
**How:**
1. Update Plan 02 deliverable 4: remove `task_description` and `parent_session_id`, replace with `session_id (parent), transcript_path, cwd`.
2. Update CONTEXT.md line 2143: "SubagentStart carries `agent_id` and `agent_type`; task prompt context is NOT available in SubagentStart input."
3. The `obs_subagent_start.py` spec becomes ~20 LOC, not 40.
4. Document capability gap: attribution impossible for anonymous Task spawns.
**Impacts:** Plan 02 (corrected spec, reduced LOC), Plan 03
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented
**Adversarial note (Platform Schema Bugs):** Two invented fields — worse than IMP-01's misspelled real field. Plan 02 scope estimate inflated by ~50% on this deliverable.

### P13-IMP-07: ObservationParser Multi-Session File Loading Is Unbounded
**Target:** CONTEXT
**What:** `observation_parser.py:109` loads ALL `.jsonl` files from observations directory. Since `observation_writer.py` writes `{session_id}.jsonl` per session, multiple runs accumulate and mix. Constructor should accept `session_id: str | None = None`; when provided, `_load()` reads only `{session_id}.jsonl`. Validate derived session_id against constructor parameter.
**Why:** Score contamination: `bskg_query_count` and `tool_count` inflated by prior runs. GVS and ReasoningEvaluator both receive contaminated data, silently corrupting scores.
**How:**
1. Change constructor: `def __init__(self, obs_dir: Path, session_id: str | None = None):`
2. In `_load()`: if `self._session_id`, load only `{session_id}.jsonl`; else glob with warning.
3. Validate in `parse()`: mismatch adds to `parse_errors`.
4. Update ALL call sites atomically (see P13-ADV-6-01).
5. Add unit test: two `.jsonl` files, assert filtered parser returns only matching session.
**Impacts:** Plan 03 (constructor), Plan 08 (must pass session_id)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Adversarial note (Compaction Resilience):** Bug confirmed by direct inspection of both files. The call-site migration must be atomic — see P13-ADV-6-01.

---

### AREA: Observation Pipeline (Plans 02, 03) — Creative Challenge

---

### P13-IMP-08: Eliminate Passive Hooks — Use TranscriptParser as Single Data Source (Track A/B Split)
**Target:** CONTEXT
**What:** TranscriptParser already extracts richer data than the passive hooks for every event type EXCEPT two: `PostToolUseFailure` and `PreCompact`. Split into two tracks: **Track A** (immediate, no research) — eliminate 5 passive hooks (`obs_tool_use.py`, `obs_bskg_query.py`, `obs_tool_result.py`, `obs_message.py`, `obs_session_start.py`, `obs_agent_stop.py`), add `to_observation_summary()` to TranscriptParser (~60 LOC), mark ObservationWriter deprecated. **Track B** (conditional on research) — verify whether `PostToolUseFailure` events appear in transcript JSONL; if yes, complete elimination; if no, retain sole passive observation hook.
**Why:** (1) Data fidelity: transcript is authoritative with full content and tool_use_id pairing. Hooks receive truncated previews and have broken field names (IMP-01). (2) Net LOC reduction: ~330 (not 580 — ObservationParser becomes thin adapter, not deletion). (3) Prior art: METR, simonw, LobeHub all parse CC transcripts directly.
**How:**
1. Track A: add `to_observation_summary()` to TranscriptParser. In `EvaluationRunner.run()`, replace `ObservationParser(obs_dir)` with `TranscriptParser(transcript_path).to_observation_summary()`.
2. Mark ObservationWriter deprecated (do not delete yet — test dependencies).
3. Track B: verify PostToolUseFailure in transcript JSONL. If present, complete elimination. If not, retain `obs_tool_failure.py` as sole passive hook.
4. DO NOT collapse Plan 03 until ObservationParser deletion is confirmed — consumers must be re-wired first.
**Impacts:** Plan 02 scope reduces ~50% (Track A). Plan 03 transforms to adapter. Plan 04 simplifies.
**Research needed:** no (resolved 2026-02-20 — PostToolUseFailure is a hook event only, NOT a transcript event type. Tool failures appear in transcript JSONL as normal `tool_result` blocks with `is_error: true`. TranscriptParser can extract failures natively → Track B resolved: complete elimination is possible. No need to retain `obs_tool_failure.py`.)
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Research resolved by:** resolve-blockers CC platform research (official hooks docs, GitHub issues #4831, #4366)
**Adversarial note (Pipeline Elimination):** The original 580 LOC savings is ~40% inflated (net ~330). Most "eliminated" hooks either haven't been built yet (scope reduction, not deletion) or become adapters. The Track A/B split correctly separates high-confidence deletions from research-gated decisions. Critical cross-group conflict: IMP-14 wants to ENHANCE obs_bskg_query.py while this item proposes deprecating it — see P13-ADV-1-02.

### P13-IMP-09: The Threading Lock vs fcntl.flock Debate Is Moot — Hooks Run in Separate Processes
**Target:** CONTEXT
**What:** ObservationWriter uses threading.Lock but hooks are separate processes. The concurrency guarantee has NEVER worked. Each process gets its own lock instance.
**Why:** If IMP-08 accepted, this disappears (record in KCI as "eliminated rather than fixed"). If rejected, the fix requires concurrent-process validation testing.
**How:**
1. If IMP-08 accepted: document in KCI "threading.Lock was never process-safe; architecture eliminated rather than fixed."
2. If rejected: change deliverable to "fcntl.flock + integration test proving correct JSONL under 3 concurrent hook processes."
**Impacts:** Plan 02 deliverable 1
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented
**Adversarial note (Pipeline Elimination):** Factually correct. Every observation JSONL file produced with concurrent tool calls is potentially corrupted. Contained because zero real transcripts exist.

### P13-IMP-10: Retain Only 3 Hooks: 2 Debrief Gates + 1 PreCompact (Schema Enum Stays Full)
**Target:** CONTEXT
**What:** The only hooks that MUST exist are: `debrief_gate.py` (blocking), `debrief_task_complete.py` (blocking), `obs_precompact.py` (observation-only). All evaluation runs post-hoc on transcript. The `hooks` schema enum must NOT be reduced to custom names — it must remain the full CC event vocabulary (14-15 events per IMP-02 correction). The category template defaults should slim to these 3 essential hooks.
**Why:** Reducing hooks simplifies Plan 02 and reduces per-tool-call latency. But the schema enum is a vocabulary definition, not an installation checklist — future contracts may need additional hook events.
**How:**
1. In Plan 02, restructure deliverables around 3 hooks. Remove deliverables for 6 passive hooks.
2. Update category template defaults: investigation = `[Stop, PreCompact, TeammateIdle, TaskCompleted]`; tool = `[Stop]`; orchestration = `[TeammateIdle, TaskCompleted, PreCompact]`.
3. Schema enum: remain the full CC event vocabulary.
4. Research: PreCompact receives `transcript_path` only — obs_precompact must read file synchronously before returning (see P13-ADV-1-01).
**Impacts:** Plan 02 reduces from 13 deliverables to ~6. Plan 06 schema unchanged.
**Research needed:** no (resolved 2026-02-20 — PreCompact receives `transcript_path` as standard input field. Default timeout is 600s for command hooks. CC waits for sync hooks to complete before proceeding, but PreCompact CANNOT block compaction via exit code 2. For obs_precompact: use synchronous mode (do NOT set `async: true`), read transcript to completion before returning. CC waits for hook return, then compacts. Race risk mitigated by sync execution.)
**Confidence:** HIGH
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented
**Research resolved by:** resolve-blockers CC platform research (official hooks docs — PreCompact section, exit code 2 behavior table, timeout defaults)
**Adversarial note (Pipeline Elimination):** PreCompact input provides transcript_path only, not pre-compaction data inline. obs_precompact's value is as a TRIGGER for capturing BSKG inventory AT compaction time by reading the transcript before CC rewrites it. Race condition risk surfaced in P13-ADV-1-01.

### P13-IMP-11: SubagentStart Is Available in Transcripts — Do Not Create a Hook for It
**Target:** CONTEXT
**What:** CC records subagent lifecycle in transcript via Task tool calls. The OutputCollector already populates TeamObservation from transcript data. Creating obs_subagent_start.py adds latency and produces data already available. CC docs confirm subagents get their own JSONL at `subagents/agent-{id}.jsonl`.
**Why:** Architecturally inconsistent with how team observations are already built.
**How:**
1. Remove Plan 02 deliverable 4.
2. Add `get_subagent_spawns()` to TranscriptParser (~80-100 LOC for full lifecycle extraction including subagent transcript reading, not 30 as originally estimated).
3. Wire into OutputCollector.collect().
**Impacts:** Plan 02 loses one deliverable.
**Research needed:** no (resolved 2026-02-20 — Task tool_result in transcript does NOT include spawned agent's session_id or transcript_path. Contains only the agent's final text response. SubagentStop hook provides `agent_id`, `agent_type`, `agent_transcript_path`. Subagent transcripts stored at `{session_id}/subagents/agent-{agent_id}.jsonl`. TranscriptParser can discover subagent transcripts via filesystem glob of `subagents/agent-*.jsonl` — simpler than hook data dependency.)
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Research resolved by:** resolve-blockers CC platform research (official hooks docs — SubagentStop section, GitHub issues #7881, #16424, #1770)
**Adversarial note (Pipeline Elimination):** Directionally correct. LOC estimate corrected from 30 to 80-100 for full subagent lifecycle extraction.

### P13-IMP-12: The Two-Parser Design Is Technical Debt Masquerading as Architecture
**Target:** CONTEXT
**What:** ObservationParser produces overlapping but inferior data to TranscriptParser. GVS uses `collected_output.transcript` (TranscriptParser) directly and has zero imports from ObservationParser. The "different data source" justification is circular.
**Why:** GVS confirmed: `graph_value_scorer.py` uses TranscriptParser as primary for citation_rate. ObservationParser is being built with no proven consumer that cannot be served by TranscriptParser.
**How:**
1. Redefine ObservationParser as thin adapter over TranscriptParser (~40 LOC).
2. Keep ObservationSummary interface unchanged — Plans 07 and 08 protected.
3. Reduce Plan 03 deliverables to: adapter implementation, GroundTruthAdapter validation, real transcript testing.
4. The 17 test functions in test_observation_parser.py become adapter behavior tests.
**Impacts:** Plan 03 scope reduces significantly.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Adversarial note (Pipeline Elimination):** GVS code confirms the claim. ObservationParser is loaded in Stage 3 of evaluation_runner.py and passed as optional parameter — downstream consumers may not even use it.

### P13-IMP-13: Concrete Failure Scenario — Compaction Destroys Observation Data Mid-Evaluation
**Target:** CONTEXT
**Status:** rejected
**Adversarial note (Compaction Resilience):** Already comprehensively addressed by 5 locked decisions: obs_precompact.py (P11-IMP-08), GVS _get_node_inventory() merge, DebriefResponse.compacted, compacted marker + 3-question fallback (P11-IMP-04), CalibrationConfig compaction rate tracking. The "research needed" question is answered by the architecture: hooks write to filesystem, filesystem is not compacted. If this assumption is wrong, it's a much larger problem than this item scopes.

---

### AREA: Scoring Engine (Plans 04, 05) — Standard Analysis

---

### P13-IMP-14: GVS Citation Rate Fallback Should Use Observation-Based Node-ID Matching
**Target:** CONTEXT
**What:** The PRIMARY citation path (`transcript.graph_citation_rate()` via TranscriptParser) must remain — it provides node-ID-level matching that is strictly richer than hook data. The real unresolved bug is the FALLBACK path's keyword-soup regex (`node:|edge:|graph:|BSKG|build-kg`). The compaction-survival problem is already solved by P11-IMP-08's precompact_snapshot.
**Why:** The fallback fires in simulated/headless runs on Standard-tier contracts. The keyword soup produces near-zero-signal scores that contaminate GVS calibration.
**How:** See P13-ADV-3-01 (CREATE) for the concrete fallback upgrade specification.
**Impacts:** Plan 04 fallback path
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** reframed
**Adversarial note (GVS Architecture):** The original proposed demoting TranscriptParser from PRIMARY to secondary — this would use `result_preview: str(tool_output)[:1000]` (a 1000-char truncation) as citation source, strictly worse than TranscriptParser's full JSONL parsing. The locked decision "Evaluator MUST receive CollectedOutput to preserve TranscriptParser for citation rate" directly forbids this demotion.

### P13-IMP-15: Agent-Type Hooks as Debrief Layer Alternative (Deferred Research)
**Target:** CONTEXT
**What:** When BUG #20221 is resolved in a future platform release, evaluate whether a `type: "prompt"` SubagentStop hook provides a higher-fidelity Layer 1 alternative compared to the current SendMessage-while-idle approach. Key questions: (a) does agent have full reasoning context at SubagentStop? (b) does hook fire before/after transcript finalization? (c) can exit code 2 block? This is deferred research, NOT a v1 implementation item.
**Why:** The original framing "replace Layers 3-4" targets the wrong abstraction. Layers 3-4 are a degradation sequence, not data channels. An agent-type hook at SubagentStop is architecturally a Layer 1 variant, not a replacement for transcript analysis.
**How:** See P13-ADV-4-01 (CREATE) for the CONTEXT.md addition.
**Impacts:** Deferred research item for CONTEXT.md
**Research needed:** yes — BUG #20221 resolution
**Confidence:** MEDIUM
**Prior art:** 1
**Prerequisite:** no
**Status:** reframed
**Adversarial note (Debrief Value):** Layer 3 (transcript analysis) cannot be replaced by agent interrogation because the agent may be dead, compacted, or non-cooperative. Layer 4 is a fail-safe nil case. The reframe correctly captures this as a deferred Layer 1 alternative evaluation.

### P13-IMP-16: GVS Is a Transcript Grader — Architecture Should Say So Explicitly
**Target:** CONTEXT
**What:** Add grader taxonomy: "GVS and reasoning move scores are *transcript graders* (assess execution quality). Detection accuracy is an *outcome grader* (assesses task completion). These can diverge." If Spearman rho(GVS, detection_accuracy) < 0.3, this is a GVS failure condition requiring diagnosis — do NOT auto-substitute detection accuracy.
**Why:** Without the taxonomy, implementers treating GVS scores as quality evidence produce a self-sealing loop. The rho < 0.3 threshold is a halt condition, not a graceful fallback — automatic fallback masks root cause.
**How:**
1. Add "Grader Taxonomy" subsection to Evaluation Architecture in CONTEXT.md (~4 sentences).
2. Add to KCI: "GVS-Detection Divergence Detector — Plan 12 Part 1 must compute rho and HALT if < 0.3."
3. No code change — architectural documentation only.
**Impacts:** Plan 12 Part 0 (~10 LOC measurement), Calibration Anchor Protocol
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Adversarial note (Evaluation Integrity):** The rho < 0.3 reframing from "fallback" to "halt condition" is critical — auto-substitution would mask GVS failure.

### P13-IMP-17: Position Bias in Evaluator Debate Protocol Is Unaddressed
**Target:** CONTEXT
**Status:** rejected
**Adversarial note (Evaluation Integrity):** Conflicts with the locked Evaluator Debate Protocol (IMP-14). The sequential protocol was deliberately designed to replace the parallel dispatch that IMP-17 proposes reverting to. The anchoring concern is legitimate but CodeJudgeBench evidence does not transfer to structured rubric evaluation. The correct fix is instrumentation (log B's pre-exposure score) — see P13-ADV-5-01 (CREATE).

### P13-IMP-18: GVS Could Verify Citations by Re-Running Queries (TIR-Judge Pattern)
**Target:** CONTEXT
**What:** v2 scope (re-run queries) correctly deferred. v1 opportunity (result_preview comparison) has hard prerequisite: Plan 04's "Citation Rate Fallback Is Keyword Soup" bug must be fixed first. Building result_preview comparison on broken citation detection adds a second unreliable signal.
**Why:** After Plan 04 fixes citation detection, `_check_citation_fidelity()` (~20 LOC) cross-references cited node IDs against result_preview captured in PostToolUse events.
**How:**
1. Add note under PreCompact GVS Citation Preservation: "v1 citation fidelity improvement blocked on Plan 04 citation detection fix."
2. Add v2 row to Intelligence Module Activation table: query re-execution deferred until deterministic graph snapshot support.
**Impacts:** No v1 impact. v2 backlog.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Status:** implemented
**Adversarial note (Evaluation Integrity):** The v1 prerequisite on Plan 04's bug fix is correctly identified. Without it, result_preview comparison adds complexity on top of broken detection.

### P13-IMP-19: _check_graph_first Bug Is Worse Than Documented — Data Model Fix Required
**Target:** CONTEXT
**What:** `tool_sequence` is `list[str]` with tool names only — no command content. The CONTEXT.md ~5 LOC fix ("filter for alphaswarm substring") cannot work on tool names alone. The fix requires threading `obs_summary` into `_check_graph_first()` to use observation timestamps for precise ordering.
**Why:** Concrete failure: `pip install` (Bash) before Read before `alphaswarm query` (Bash) scores graph_first=True incorrectly. The 5-LOC estimate is wrong.
**How:**
1. Refactor `_check_graph_first()`: add optional `obs_summary` parameter (~15 LOC).
2. When obs_summary contains bskg_query events, use timestamps. When absent, conservative False.
3. Exit criteria: three test cases — (a) BSKG before Read, (b) non-BSKG Bash before Read, (c) Read before BSKG.
**Impacts:** Plan 04 deliverable 3 (~15 LOC, not 5)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Depends on plans:** Plan 02/03 (observation pipeline timestamps)
**Status:** implemented
**Adversarial note (GVS Architecture):** The "data model change" framing undersells a concrete fix. The observation pipeline already emits timestamps; the fix is wiring them into _check_graph_first.

---

### AREA: Scoring Engine (Plans 04, 05) — Creative Challenge

---

### P13-IMP-20: GVS Should Be Demoted from Scorer to Evaluator Input
**Target:** CONTEXT
**Status:** rejected
**Adversarial note (GVS Architecture):** Violates locked CONTEXT.md Mode Capability Matrix ("Hook-based GVS" AVAILABLE in headless/interactive). Removes the ONLY deterministic enforcement of the Graph-First Rule. The 66-combo calibration IS the validation mechanism, not a burden. The LLM evaluator interpreting graph facts is non-deterministic — it cannot reliably enforce a rule that PHILOSOPHY.md makes mandatory. Contradicts IMP-12 and IMP-16 which support keeping GVS as a separate component.

### P13-IMP-21: Debrief Signal Uniqueness — Layer 1 Only Has Scoring Value
**Target:** CONTEXT
**What:** Only Layer 1 (SendMessage to live interactive agent) provides signal not already present in the transcript. Layers 2-4 re-extract transcript through increasingly lossy mechanisms. The `debrief_layer_weight` contract field should prevent Layers 2-4 from diluting `effective_score()` while keeping Layer 1 as valid scoring input.
**Why:** The CoT faithfulness evidence does not directly apply (it studies in-context reasoning tokens, not retrospective debriefs). METR measures outcomes, not reasoning. The actual problem: Layer 2 returns `answers: []` (confirmed bug). Layer 3 is keyword heuristics on the same transcript the evaluator reads. For 41 of 51 workflows (headless), debrief produces zero unique signal.
**How:** See P13-ADV-4-02 (CREATE) for the weight-field specification.
**Impacts:** Plan 05 retains architecture. Plan 07 gains weight guard.
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Status:** reframed
**Adversarial note (Debrief Value):** The binary "diagnostic-only" framing is too coarse. A weight parameter preserves the cascade (justified for Layer 1 interactive mode) while preventing Layers 2-4 noise from diluting scores. The `DebriefResponse.compacted` and `degraded` flags are complementary, not overlapping — `degraded` is quality signal, `applicable` is inclusion gate.

### P13-IMP-22: Three-System Overhead Budget Needs Empirical Measurement, Not Static Ceiling
**Target:** CONTEXT
**What:** The budget sanity formula (`total_ceiling >= execution_p95 + debate_p95 + scoring_p95`) is underspecified because `scoring_p95` has no empirical baseline. A static budget ceiling is premature before the first real run.
**Why:** If measured overhead exceeds 30% of execution time, this triggers IMP-20/21 reconsideration — not automatic ceiling enforcement. Premature ceiling constrains future evaluation capabilities.
**How:**
1. Update Plan 08 budget note: `scoring_p95` MUST be measured from first Core sub-wave run.
2. Plan 12 Part 0: validate wall-clock estimates within 25% of measured values.
3. If `scoring_p95 / execution_p95 > 0.30`, initiate IMP-20/21 reconsideration.
**Impacts:** Plan 08 estimates become provisional. Plan 12 Part 0 gains measurement.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** reframed
**Adversarial note (Evaluation Integrity):** The "budget ceiling" remedy targets the symptom. The real problem is `scoring_p95` was never estimated. The reframe defers ceiling to empirical data and links to IMP-20/21 reconsideration at 30% threshold.

### P13-IMP-23: GVS graph_first — Preserve Binary Check, Add Graduated Score
**Target:** CONTEXT
**What:** The binary `graph_first_compliant: bool` must be preserved as the hard Graph-First Rule enforcement check. Add a graduated `graph_first_score: float` (0.0-1.0) measuring proportion of code-reading calls preceded by at least one BSKG query. The graduated score feeds the LLM evaluator as diagnostic signal for the `graph_utilization` dimension.
**Why:** The Graph-First Rule is a hard architectural constraint, not a soft preference. An agent reading files before querying IS violating the architecture. The real problem is false positives from Bash conflation (IMP-19's territory). The graduated score exposes the distinction between "reads 1 file then uses graph extensively" vs "never uses graph" without removing enforcement.
**How:** See P13-ADV-3-02 (CREATE) for specification.
**Impacts:** Plan 04 deliverable, Plan 01 model
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 2
**Prerequisite:** no
**Status:** reframed
**Adversarial note (GVS Architecture):** The "penalizes intelligent agents" framing assumes graph-first violations are legitimate. CONTEXT.md's Graph-First Rule is unqualified. The reframe preserves deterministic enforcement while adding diagnostic nuance.

---

## Adversarial CREATE Items

---

### P13-ADV-1-01: PreCompact Synchronous Read Race Condition Is Unresolved
**Target:** CONTEXT
**What:** PreCompact hook receives `transcript_path` but it is undocumented whether CC holds the transcript file open exclusively during hook execution. If the hook returns before reading completes, CC may begin rewriting the JSONL. The current obs_precompact design does not address this race.
**Why:** If this race is real, obs_precompact's pre-compaction BSKG inventory capture is unreliable. Since PreCompact is the ONE observation hook retained in the 3-hook architecture, this directly threatens compaction-handling capability.
**How:**
1. In Plan 02 deliverable 10: "obs_precompact.py MUST open and read transcript_path to completion before returning exit 0. Do not defer or background the read. Return time must be < 2s."
2. Add research: "Verify CC PreCompact hook timeout behavior."
3. Add to KCI: "PreCompact Synchronous Read Race."
**Research needed:** no (resolved 2026-02-20 — CC PreCompact hook is synchronous by default: CC waits for hook to return before proceeding with compaction. Default timeout is 600s for command hooks. PreCompact CANNOT block compaction via exit code 2 (shows stderr to user only). Race condition mitigated: as long as obs_precompact runs synchronously (no `async: true`), CC waits for it to finish, then compacts. The 2s return time target is well within the 600s timeout. File exclusivity during hook execution is not documented but the sync wait behavior means the transcript is available for reading.)
**Confidence:** HIGH
**Status:** implemented
**Research resolved by:** resolve-blockers CC platform research (official hooks docs — PreCompact section, exit code 2 behavior table, timeout defaults)
**Adversarial note (ADV Validation):** Race condition correctly identified. Synchronous read requirement is architectural. Research resolved: CC's sync hook behavior provides a safe window for reading.
**Source:** Adversarial review (Pipeline Elimination)
**Cross-references:** P13-IMP-10

### P13-ADV-1-02: IMP-08 Track A vs IMP-14 — Direct Contradiction Requires Resolution
**Target:** CONTEXT
**What:** IMP-08 proposes deprecating `obs_bskg_query.py`. IMP-14's reframe (ADV-3-01) proposes using obs_bskg_query.py data as the fallback citation source. If both accepted, result is incoherent.
**Why:** Cross-group conflict. Decision determines Plan 04 GVS data flow and Plan 02 hook deliverables.
**How:**
1. Before merging either: resolve GVS Data Source Decision.
2. If TranscriptParser wins: IMP-14/ADV-3-01 fallback must use TranscriptParser exclusively.
3. If hooks win: IMP-08 Track A must exclude obs_bskg_query from deprecation scope.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented
**Adversarial note (ADV Validation):** Critical merge blocker correctly surfaced. The three-way decision (TranscriptParser, hooks, integration) is exhaustive. No implementation can proceed until resolved.
**Source:** Adversarial review (Pipeline Elimination)
**Cross-references:** P13-IMP-08, P13-IMP-14, P13-ADV-3-01

### P13-ADV-1-03: LOC Savings Claim Is Inflated — Net ~330, Not 580
**Target:** CONTEXT
**What:** IMP-08's 580 LOC savings includes ObservationParser (becomes adapter, not deleted), obs_tool_failure.py (not yet built — scope reduction, not deletion), and ignores the ~60 LOC addition. Net real reduction: ~330 LOC.
**Why:** Accurate numbers prevent future confidence erosion.
**How:**
1. In IMP-08 What field, replace the 580 LOC claim with net ~330: "hooks deleted ~580 - ObservationParser kept ~200 - TranscriptParser added ~60 = ~330."
2. In IMP-08 Why field, add LOC breakdown: "ObservationParser becomes ~40-LOC adapter (not ~200 deletion), obs_tool_failure.py was never built (scope reduction, not deletion ~80 LOC)."
3. Update Prior art to reference ADV-1-03.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented
**Adversarial note (ADV Validation):** Math validated against P13-IMP-08 breakdown. How field enhanced with concrete edit targets.
**Source:** Adversarial review (Pipeline Elimination)

### P13-ADV-2-01: Correct Locked P11-IMP-01 Decision That PermissionRequest Is Not a Distinct Hook Event
**Target:** CONTEXT
**What:** CONTEXT.md locked decision "removed PermissionRequest which is not a distinct hook event" is factually wrong per CC docs. PermissionRequest IS listed as a distinct event with its own input schema and decision control. Correct the locked decision, add PermissionRequest to enum, verify TeammateIdle and TaskCompleted sourcing.
**Why:** If locked text stays wrong, future passes will keep re-removing PermissionRequest.
**How:**
1. In CONTEXT.md "Implementation Decisions" section (line 234-236), correct locked decision text: ORIGINAL "removed PermissionRequest which is not a distinct hook event" → REVISED "PermissionRequest is a distinct hook event (CC docs confirmed). Retained in hooks enum."
2. Research: Verify TeammateIdle and TaskCompleted against official CC hooks lifecycle table. If found: document source. If NOT found: annotate in enum comment as "Agent Teams SDK extension events (added post-v1)." If unclear: flag for human review.
3. Verify Setup hook registrability: test locally that Setup hook can be registered without CC version mismatch errors.
4. Update schema enum to include PermissionRequest with documented input schema fields.
**Research needed:** no (resolved 2026-02-20 — All three verified against official CC hooks docs: (1) PermissionRequest: CONFIRMED as first-class hook event with `tool_name`, `tool_input`, `permission_suggestions` input and `allow`/`deny` decision control. (2) TeammateIdle: CONFIRMED as real hook event, added in v2.1.33, fires when teammate goes idle, can block via exit code 2, input includes `teammate_name`/`team_name`. (3) TaskCompleted: CONFIRMED as real hook event, added in v2.1.33, fires when task marked complete, can block, input includes `task_id`/`task_subject`/`task_description`/`teammate_name`/`team_name`. Both are core CC events, NOT SDK extensions. (4) Setup: DENIED — absent from current official hooks docs (15 events listed, Setup not among them). May have existed in earlier versions. Do NOT include in enum.)
**Confidence:** HIGH
**Status:** implemented
**Research resolved by:** resolve-blockers CC platform research (official hooks docs, claudelog.com changelog v2.1.33)
**Adversarial note (ADV Validation):** Core finding (locked decision is factually wrong) is solid. How field enhanced with exact edit targets. All research questions resolved with high confidence.
**Source:** Adversarial review (Platform Schema Bugs)
**Cross-references:** P13-IMP-02

### P13-ADV-2-02: All Hook Schema Confidence Claims Are Theoretical — No Live Validation Exists
**Target:** CONTEXT
**What:** Every "HIGH confidence" schema claim rests on docs-vs-code comparison, not runtime verification. The docs snapshot may be ahead of or behind the deployed CC version. Plan 02 deliverable 8 ("validate against real sessions") must be promoted to HARD EXIT CRITERION.
**Why:** The field name bug (IMP-01) was never caught because live validation never happened.
**How:**
1. Add PREREQUISITE to Plan 02: run 5-minute live validation script before any hook fix lands.
2. Store raw stdin JSON dumps at `tests/workflow_harness/fixtures/hook_schema_snapshots/` as golden files.
3. CI step: re-run schema snapshots if `claude --version` changes.
4. Promote Plan 02 deliverable 8 to HARD EXIT CRITERION.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented
**Adversarial note (ADV Validation):** Correct and proportionate. The field name bug (IMP-01) proves the gap. Golden file approach is industry-standard. CI trigger on version change prevents false negatives.
**Source:** Adversarial review (Platform Schema Bugs)
**Cross-references:** P13-IMP-01, P13-IMP-05, P13-IMP-06

### P13-ADV-3-01: Upgrade GVS Citation Rate Fallback to Observation-Based Node-ID Matching
**Target:** CONTEXT
**What:** Replace keyword-soup fallback regex (`node:|edge:|graph:|BSKG|build-kg`) with structured fallback that cross-references BSKG query node IDs (`[FCE]-\w+-\w+` pattern) from obs_bskg_query.py observations against conclusion text. PRIMARY path (`transcript.graph_citation_rate()`) unchanged.
**Why:** KCI "Citation Rate Fallback Is Keyword Soup" is HIGH severity. The fallback primarily matters for simulated/headless Standard-tier runs.
**How:**
1. In GVS `score()`: extract node IDs from `context.get('obs_summary', {}).get('bskg_query_events', [])`.
2. Fallback: `matched_node_ids = set(node_ids) & set(re.findall(r'[FCE]-\w+-\w+', response_text))`.
3. ~30 LOC in GVS, ~15 LOC in ObservationParser.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented
**Adversarial note (ADV Validation):** Correct and precise. Implementation blocked until SYN-01 (GVS Data Requirements) gates it — if TranscriptParser becomes sole data source, must re-specify against TranscriptParser.
**Source:** Adversarial review (GVS Architecture)
**Cross-references:** P13-IMP-14

### P13-ADV-3-02: Add Graduated graph_first_score to GVS Alongside Binary graph_first_compliant
**Target:** CONTEXT
**What:** Add `graph_first_score: float` to `GraphValueScore` — proportion of Read/Bash calls preceded by at least one BSKG query. Binary `graph_first_compliant` preserved for regression detection. Graduated score fed to LLM evaluator as diagnostic context for `graph_utilization` dimension.
**Why:** Exposes distinction between "reads 1 file before querying" vs "never queries graph" without removing enforcement.
**How:**
1. Add `graph_first_score: float = 0.0` to `GraphValueScore`.
2. Compute in `_check_graph_first()` refactor alongside `graph_first_compliant`.
3. Pass to Plan 07 evaluator context for `graph_utilization` dimension.
4. ~20 LOC total.
**Research needed:** no
**Confidence:** MEDIUM
**Status:** implemented
**Adversarial note (ADV Validation):** Architecturally sound — preserves deterministic rule while adding diagnostic nuance. Dependency on IMP-19 refactor correctly sequenced.
**Source:** Adversarial review (GVS Architecture)
**Cross-references:** P13-IMP-23, P13-IMP-19

### P13-ADV-4-01: Deferred Research — SubagentStop Prompt-Hook as Layer 1 Alternative
**Target:** CONTEXT
**What:** Add to Debrief Strategy section: "When BUG #20221 is resolved, evaluate SubagentStop prompt-hook as Layer 1 alternative. Criteria: (a) agent context integrity at SubagentStop, (b) hook fire timing relative to transcript finalization, (c) exit code 2 blocking availability. Deferred research, not v1."
**Research needed:** no (resolved 2026-02-20 — This item IS a "record deferred research" note, not an item that needs research before merge. The action is to add a CONTEXT.md note recording that BUG #20221 should be evaluated when resolved. The research question is the content of the note, not a blocker for merging it.)
**Confidence:** MEDIUM
**Status:** implemented
**Research resolved by:** resolve-blockers reclassification (item is a documentation note, not a research-gated action)
**Adversarial note (ADV Validation):** Properly scoped as deferred research. BUG #20221 reference is specific. Adding to CONTEXT.md prevents loss of institutional knowledge.
**Source:** Adversarial review (Debrief Value)
**Cross-references:** P13-IMP-15

### P13-ADV-4-02: Add debrief_layer_weight Contract Field for Layer-Aware Scoring
**Target:** CONTEXT
**What:** Add `debrief_layer_weight` to Schema Hardening Field Manifest (float 0.0-1.0, default 1.0). Plan 07: multiply debrief-derived dimension scores by this weight. Headless contracts SHOULD set 0.0. Plan 08: warn if `layer_used != 'send_message'` and weight > 0.0.
**Why:** Prevents Layers 2-4 from contributing zero-signal data to `effective_score()` while preserving Layer 1 as valid scoring input for interactive sessions.
**How:**
1. Add field to Schema Hardening Field Manifest.
2. Plan 07: `_apply_debrief_weight()` guard.
3. Plan 08: pre-run warning check.
4. `debrief_layer_weight` and `DebriefResponse.compacted` are complementary: `degraded` = quality signal, `applicable` = inclusion gate.
**Research needed:** no
**Confidence:** MEDIUM
**Status:** implemented
**Adversarial note (ADV Validation):** Well-designed safety valve. Default 1.0 prevents surprise behavior changes. Plan 08 warning check catches misconfiguration.
**Source:** Adversarial review (Debrief Value)
**Cross-references:** P13-IMP-21, P2-IMP-16

### P13-ADV-5-01: Add B_score_pre_exposure to Detect Anchoring in Debate Protocol
**Target:** CONTEXT
**What:** Add `B_score_pre_exposure: int | None` to `EvaluatorDisagreement` model. Capture B's initial commit before transmitting A's raw scores. Plan 12 Part 1: compute delta(B_pre, B_post) distribution — if median delta < 3pt across Core dimensions, flag for human review.
**Why:** The debate protocol produces no evidence about whether it is functioning as designed. Without B's pre-exposure score, anchoring cannot be detected or ruled out.
**How:**
1. Add field to `EvaluatorDisagreement` in Plan 01 (~15 LOC).
2. Plan 07: capture B's commit in separate session before transmitting A's scores (~20 LOC).
3. Plan 12 Part 1: analysis (~10 LOC).
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented
**Adversarial note (ADV Validation):** Correctly instruments anchoring vulnerability. 3-point threshold is reasonable (LLM scoring variance typically 5-10 points). Optional field preserves backward compatibility.
**Source:** Adversarial review (Evaluation Integrity)
**Cross-references:** P13-IMP-17

### P13-ADV-6-01: ObservationParser Call Sites Must Be Audited Atomically for session_id
**Target:** CONTEXT
**What:** When IMP-07's session_id filter is implemented, ALL `ObservationParser()` instantiation sites (~4 call sites) must be updated in the same commit. Partial migration creates worse divergence than no migration.
**Why:** If one call site filters and others don't, scores diverge non-deterministically between components.
**How:**
1. Before implementing IMP-07: `grep -r "ObservationParser(" tests/ src/` to enumerate call sites.
2. Update all atomically.
3. Add `warnings.warn()` to no-session-id constructor path.
**Research needed:** no
**Confidence:** HIGH
**Status:** implemented
**Adversarial note (ADV Validation):** Process discipline item preventing partial migration. Atomic update requirement is critical for consistency.
**Source:** Adversarial review (Compaction Resilience)
**Cross-references:** P13-IMP-07

---

## Synthesis Items

---

### P13-SYN-01: Scoring Engine Assumes Observation Data That Hook Elimination Removes
**Target:** CONTEXT
**What:** Three scoring engine items require observation pipeline data flowing into GVS: IMP-19 needs `obs_summary` timestamps for `_check_graph_first()`, ADV-3-01 needs `bskg_query_events` from observations for citation rate fallback, and ADV-3-02 needs per-tool-call ordering data for graduated `graph_first_score`. Meanwhile, IMP-08 Track A proposes eliminating the hooks that produce this data, and IMP-12 redefines ObservationParser as a thin adapter over TranscriptParser. ADV-1-02 caught the specific IMP-08 vs ADV-3-01 conflict but not the broader pattern: ALL three scoring improvements assume observation data exists in a form that the pipeline elimination items propose removing.
**Why:** Resolving ADV-1-02 (the IMP-08 vs IMP-14 conflict) in isolation is insufficient. If TranscriptParser wins as the sole data source, all three scoring items must be re-specified to derive their data from TranscriptParser -- and TranscriptParser's `to_observation_summary()` method (IMP-08's proposed ~60 LOC addition) must be designed to emit the specific fields these consumers need: timestamped BSKG query events, extracted node IDs, and per-tool-call ordering. Designing these independently risks TranscriptParser producing a generic summary that lacks the precise fields GVS requires.
**How:**
1. Before merging IMP-08 Track A: compile a concrete "GVS Data Requirements" manifest listing every field that `_check_graph_first()`, citation rate fallback, and `graph_first_score` consume from observation data. Fields: `bskg_query_events[].timestamp`, `bskg_query_events[].node_ids`, `tool_sequence_with_timestamps[]`.
2. Add this manifest as a HARD PREREQUISITE for `TranscriptParser.to_observation_summary()` design -- the method's return type must satisfy these consumers, not just provide a generic summary.
3. Update Plan 04 exit criteria: "GVS integration test passes with TranscriptParser-sourced data (if IMP-08 accepted) OR observation-sourced data (if rejected)."
**Impacts:** Plan 02 (TranscriptParser.to_observation_summary design), Plan 04 (GVS data flow)
**Components:** P13-IMP-08, P13-IMP-19, P13-ADV-1-02, P13-ADV-3-01, P13-ADV-3-02
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** implemented
**Adversarial note (ADV Validation):** Highest-value item in P13 cycle. Prevents eliminating infrastructure before consumers are migrated. GVS Data Requirements manifest is non-negotiable before IMP-08 Track A merges.
**Source:** Post-review synthesis (cross-cutting)

### P13-SYN-02: Untested Platform Assumptions Extend Beyond Hooks to TranscriptParser
**Target:** CONTEXT
**What:** ADV-2-02 correctly identifies that hook schema claims are theoretical (no live validation). But the same unvalidated-assumption pattern extends to the TranscriptParser convergence: IMP-08, IMP-10, IMP-11, and IMP-12 all propose making TranscriptParser the sole data source, yet TranscriptParser has NEVER been validated against real CC transcripts (CONTEXT.md line 1094-1099: "TranscriptParser has never parsed a real transcript"). The architecture is pivoting from one unvalidated data source (hooks) to another unvalidated data source (transcript JSONL) based on the assumption that transcript structure matches expectations. ADV-2-02's golden file approach covers hooks only, not transcript structure.
**Why:** ADV-2-02's live validation addresses half the problem. If Plan 02's Prestep P0 (capture 3+ real transcripts) reveals structural surprises in transcript JSONL -- different content block types, unexpected compaction artifacts, missing tool_use_id fields -- the entire TranscriptParser-as-sole-source architecture collapses before it is built. The validation must cover BOTH data sources before committing to either architecture.
**How:**
1. Extend ADV-2-02's golden file approach: alongside hook schema snapshots, store 3+ real transcript JSONL files at `tests/workflow_harness/fixtures/real_sessions/` as TranscriptParser golden files.
2. Add Prestep P0 exit criterion: "TranscriptParser.to_observation_summary() (if IMP-08 accepted) produces equivalent or richer data than ObservationParser.parse() on the same real session." This gates the hook elimination decision on empirical evidence, not theoretical analysis.
3. Sequence constraint: do NOT merge IMP-08 Track A until Prestep P0 completes. If TranscriptParser fails on real transcripts, IMP-08 is rejected and the hook architecture is retained.
**Impacts:** Plan 02 (Prestep P0 scope expansion), IMP-08 (gated on P0)
**Components:** P13-IMP-08, P13-IMP-10, P13-IMP-11, P13-IMP-12, P13-ADV-2-02
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Adversarial note (ADV Validation):** Correctly identifies validation gap in foundation assumption. Prestep P0 approach is standard acceptance testing. Explicit sequence constraint prevents catastrophic rework.
**Source:** Post-review synthesis (cross-cutting)

---

## Cascade Gap Items

---

### P13-CSC-01: IMP-08 Track A Eliminates SessionStart Source Field With No Replacement Path
**Target:** CONTEXT
**What:** IMP-05 (enhanced, status open) adds `source` and `agent_type` fields to `obs_session_start.py` -- these are operationally critical for detecting compact/resume sessions. IMP-08 Track A (enhanced, status open) eliminates `obs_session_start.py` as a passive hook. If IMP-08 Track A is implemented, IMP-05's fix has no implementation target. The `source` field (values: `"startup"`, `"resume"`, `"clear"`, `"compact"`) is NOT present in transcript JSONL entries -- it is only available via the SessionStart hook input schema. TranscriptParser has no method to extract session source type, and cannot: this metadata is provided by CC to the hook subprocess via stdin, not written to the transcript file.
**Why:** Without `source`, the runner loses the dual-detection path for compaction (IMP-05's main value proposition). The PreCompact `.compacted` marker becomes the sole detection mechanism. If PreCompact has a race condition (ADV-1-01), there is no fallback. The `resume` detection capability is lost entirely -- no other mechanism detects whether an agent has prior context the evaluator cannot see.
**How:**
1. If IMP-08 Track A is accepted: add `obs_session_start.py` to the retained hooks list alongside the 3 hooks in IMP-10 (debrief_gate, debrief_task_complete, obs_precompact). Total: 4 hooks, not 3.
2. Update IMP-10's category template defaults to include SessionStart: investigation = `[SessionStart, Stop, PreCompact, TeammateIdle, TaskCompleted]`.
3. Alternative: if SessionStart hook is rejected, downgrade IMP-05 to "deferred -- source field unavailable without hook" and document that compaction detection relies solely on PreCompact marker.
**Impacts:** Plan 02 (hook count), IMP-05 (implementation target), IMP-10 (template defaults)
**Trigger:** P13-IMP-08
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** implemented
**Adversarial note (ADV Validation):** Essential cascade item. If IMP-08 Track A accepted without addressing this, IMP-05 becomes unimplementable. Two-path resolution is complete.
**Source:** Post-review synthesis (cascade)

---

## Convergence Assessment

**Post-adversarial results:**
- Structural improvements: 12 enhanced/confirmed originals + 12 ADV creates = 24 actionable
- Rejected: 6 (IMP-03, IMP-04, IMP-13, IMP-17, IMP-20 — all violated locked decisions or were already addressed)
- Reframed: 6 (IMP-02, IMP-14, IMP-15, IMP-21, IMP-22, IMP-23 — all carried forward as ADV creates)
- Key cross-group conflict: IMP-08 (eliminate hooks) vs IMP-14/ADV-3-01 (enhance hooks for GVS) — requires explicit resolution before Plan 02/04 implementation

**Critical findings:**
1. The adversarial review caught that IMP-20 (demote GVS) violated a locked decision and the Graph-First Rule — correctly rejected
2. The position bias concern (IMP-17) was legitimate but the proposed fix was wrong — instrumentation (ADV-5-01) is the correct response
3. The debrief debate (IMP-21) was reframed from binary "diagnostic-only" to a nuanced weight-field approach (ADV-4-02)
4. The two strongest architectural proposals (IMP-08 Track A/B and IMP-12 adapter) both survived review with refinements

> This pass reaches deep architectural territory. The 6 rejections all share a common pattern: proposals that would remove deterministic enforcement mechanisms or override locked decisions. The 12 ADV creates add precision that the original items lacked. The IMP-08 vs IMP-14 conflict is the key resolution needed before merging. Another pass is NOT recommended — the fundamental architectural questions are surfaced and the adversarial review has sharpened the actionable items.

## Post-Review Synthesis
**Items created:** P13-SYN-01, P13-SYN-02, P13-CSC-01
**Key insight:** The hook elimination proposal (IMP-08) and scoring engine improvements (IMP-19, ADV-3-01, ADV-3-02) were reviewed in separate groups and appear compatible individually, but together they create an incoherent data flow: the scoring engine is being enhanced to consume observation data that the pipeline is being redesigned to stop producing. The ADV-1-02 conflict flag caught one instance but the pattern is systemic -- and the replacement data source (TranscriptParser) shares the same fundamental validation gap (zero real transcripts) as the hooks it would replace.
