# Improvement Pass 10

**Pass:** 10
**Date:** 2026-02-19
**Prior passes read:** 1-9 (via IMPROVEMENT-DIGEST.md)
**Areas:** 4 (Data Pipeline, Scoring Engine, Execution Layer, Improvement Loop)
**Agents:** 4 improvement + 5 adversarial + synthesis pending
**Status:** complete

<!-- File-level status: in-progress | complete -->

## Pipeline Status

<!-- Auto-populated by workflows. Shows pending actions across ALL passes for this phase. -->

| Stage | Pending | Done | Blockers |
|-------|---------|------|----------|
| Prerequisites | 1 | 0 | P10-IMP-05 (5-min runtime verification — field confirmed in schema) |
| Research | 0 | 2 | — (IMP-05, IMP-20 resolved via web research) |
| Gaps | 0 | 0 | — |
| Merge-ready | 33 | 0 | — |

**Pipeline:** [improve] ✓ → [adversarial] ✓ → [synthesis] ✓ → [research] ✓ → [implement] ~
**Next recommended:** /msd:implement-improvements 3.1c

## Adversarial Review Summary

**Lenses:** 5 (Data Integrity, Protocol Efficiency, Execution Architecture, Improvement Loop, Novel Capability)
**Verdicts:** 13 ENHANCE, 5 CONFIRM, 6 REFRAME, 1 REJECT
**CREATE items:** 11 (mandatory companions to REFRAMEs + cross-item analysis)

## Improvements

### P10-IMP-01: Hooks Enum Missing 4 of 12 CC Hook Events
**Target:** CONTEXT
**What:** The `hooks` field enum in Smart Selection Matrix Encoding (~line 185) lists 8 values: `[PreToolUse, PostToolUse, SubagentStart, SubagentStop, Stop, SessionStart, TeammateIdle, TaskCompleted]`. CC now has 12 hook lifecycle events. Missing: `PostToolUseFailure`, `PermissionRequest`, `Notification`, `UserPromptSubmit`.
**Why:** `PostToolUseFailure` fires when a tool call fails — directly relevant for distinguishing "agent didn't use graph" from "tool call failed" in GVS scoring. `PermissionRequest` could auto-approve known-safe operations during evaluation runs. Omitting from schema means contracts cannot declare them, hooks cannot be installed, and Plan 02 fail-fast validation rejects future use. The enum should match CC's documented capabilities.
**How:**
1. Expand enum to all 12 CC events in Smart Selection Matrix Encoding section
2. Update category template defaults: Investigation gains `PostToolUseFailure` (captures failed graph queries). Other categories unchanged — new events are opt-in via per-contract override
3. Plan 02 gains deliverable: `obs_tool_failure.py` hook (~25 LOC) capturing `tool_name`, `tool_use_id`, `error_message`, `error_type`
**Impacts:** Plans 02, 06 (schema), 04 (GVS can distinguish failure modes)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — CC hook docs explicit about 12 events; bringing design into alignment
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Data Integrity) — confirmed directionally correct; enhanced How to specify `PostToolUseFailure` captures `tool_name, tool_use_id, error_message, error_type` for GVS failure-mode discrimination.

### P10-IMP-02: ObservationWriter Silent Data Loss on JSON Serialization Failure
**Target:** CONTEXT
**What:** `observation_writer.py:75` calls `json.dumps(record)` with no `default` parameter. Non-serializable types (datetime, bytes) raise `TypeError`, silently losing the entire observation. No handler for serialization errors exists.
**Why:** Silent data loss in the writer means downstream consumers (parser, GVS, evaluator) operate on incomplete data with no detection mechanism. Only triggers on unusual tool outputs that synthetic tests never produce.
**How:**
1. Add to Known Code Issues: "ObservationWriter JSON Serialization Not Defensive" — Owner: Plan 02, Severity: MEDIUM
2. Plan 02: wrap `json.dumps` with `default=str` fallback + `_serialize_errors: int` counter for degraded observation detection. ~5 LOC
**Impacts:** Plan 02 (+5 LOC), Plan 03 parser gains degraded record awareness
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Standard defensive JSON serialization
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Data Integrity) — confirmed; enhanced to specify `_serialize_errors` counter must be exposed in `ObservationSummary.metadata` for downstream degradation detection.

### P10-IMP-03: ObservationParser Loads ALL Session Files Indiscriminately
**Target:** CONTEXT
**What:** `observation_parser.py:109-121` `_load()` iterates ALL `*.jsonl` files in the observations directory. No filtering by session_id. Parser loads every record from every session, picks session_id from first record encountered. When multiple evaluation runs accumulate, parser mixes observations across sessions.
**Why:** Correctness bug, not performance. In normal operation after first run, parser will mix observations from different sessions into a single ObservationSummary. Tool pairing crosses session boundaries. The writer already names files `{session_id}.jsonl` — the read side just needs to match the write-side design.
**How:**
1. Add to Known Code Issues: "ObservationParser Does Not Filter by Session ID" — Owner: Plan 03, Severity: HIGH
2. Plan 03: `ObservationParser` constructor gains required `session_id: str` parameter. Load only `{session_id}.jsonl` (O(1) instead of O(N)). Simple because writer already uses per-session filenames
**Impacts:** Plans 03, 04, 07, 08 consume correct per-session data
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — File-per-session already the write-side design
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Data Integrity) — confirmed correctness bug; enhanced to clarify O(1) lookup vs O(N) scan and compatibility with IMP-20's sentinel approach.

### P10-IMP-04: No Observation Schema Versioning Creates Silent Incompatibility
**Target:** CONTEXT
**What:** JSONL records have no `schema_version` field. When Plan 02 adds `tool_use_id` and Plan 01 adds typed submodels, parser needs to handle both old and new formats. Currently no mechanism to distinguish record formats during the transition period.
**Why:** During Plan 02→03 transition, or when re-analyzing old evaluation runs, parser encounters mixed-format records. Adding `schema_version` (~1 field) makes format evolution explicit rather than relying on presence/absence checks for every new field.
**How:**
1. Plan 02: add `schema_version: str` field to JSONL records. `"1.0"` current, bump to `"1.1"` with `tool_use_id`
2. Plan 03: check `schema_version`. Records without it treated as `"0.9"` (pre-versioning) with LIFO fallback
**Impacts:** Plans 02, 03 gain ~5 LOC each. Forward-compatible schema evolution
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 4 — Standard schema evolution for append-only logs
**Prerequisite:** no
**Status:** reframed
**Adversarial verdict:** REFRAME (Data Integrity) — schema_version field is premature when the schema has no consumers yet. Real problem is stale observation files from prior runs contaminating current analysis. See P10-ADV-1-01 (Observation File Staleness Guard).

### P10-IMP-05: tool_use_id Availability Not Verified in CC Hook Input
**Target:** CONTEXT
**What:** The CRITICAL pairing fix chain depends on `tool_use_id` being present in CC hook input JSON (Plan 02 hard exit criterion). The CONTEXT references hook input schemas at `.vrs/debug/phase-3.1b/research/hook-verification-findings.md` but never confirms `tool_use_id` was found. If CC does not include this field, the entire fix chain collapses.
**Why:** CC hooks receive JSON from the CC process — the schema is determined by Anthropic's implementation. If `tool_use_id` is absent, alternative pairing strategies are needed (timestamp proximity, sequence numbers). This is an unverified prerequisite for the project's most critical fix.
**How:**
1. In "Observation Pairing Is Broken" bug entry, add prerequisite check: "Verify `tool_use_id` presence by running test hook that dumps raw stdin. If absent, alternative pairing by `(tool_name, timestamp_window)` with collision detection"
2. In Prestep P0 exit criteria, add: "(e) `tool_use_id` confirmed in PreToolUse/PostToolUse hook stdin, or alternative pairing strategy documented"
**Impacts:** Plan 02 exit criteria may need revision. Prerequisite discovery, not new scope
**Research needed:** no — RESOLVED. `tool_use_id` IS documented in official CC hook input schemas for PreToolUse and PostToolUse. GitHub issue #13241 (Dec 2025) reported it was `null` in PostToolUse — a confirmed bug. Multiple authoritative sources (official docs, VS Code hooks docs, community repos) include `tool_use_id: "string"` in PreToolUse input schema. Prestep P0 should verify non-null in current CC version (~5 min test: write PreToolUse hook that dumps stdin, run one tool call, check output).
**Research resolved by:** resolve-blockers web research (2026-02-19)
**Confidence:** HIGH (upgraded from MEDIUM — field confirmed in schema)
**Prior art:** 4 (upgraded — field documented across multiple sources)
**Prerequisite:** yes — Must be verified during P0 before Plan 02 (but now a 5-min verification, not open research)
**Status:** implemented
**Adversarial verdict:** CONFIRM (Data Integrity) — correctly identifies unverified prerequisite. Research resolved: field exists in schema, just needs runtime verification of non-null.

### P10-IMP-06: fcntl.flock() Fix Over-Specified — POSIX Atomic Append May Suffice
**Target:** CONTEXT
**What:** The threading.Lock fix prescribes `fcntl.flock()` with platform fallback (~20 LOC). But POSIX guarantees atomic append for writes under PIPE_BUF (4096 bytes). Typical observation records are 200-500 bytes with compact JSON. A simpler fix: bound line length and rely on atomic append.
**Why:** Eliminates platform fallback complexity entirely. The `fcntl.flock()` fix works IF implemented correctly (lock on file descriptor, not lockfile), but a naive implementation would fail. The simpler approach (assert lines < 4096, rely on POSIX) is more robust and ~5 LOC vs ~20 LOC.
**How:**
1. Replace fix description in bug entry: "Either (a) `fcntl.flock(f.fileno(), LOCK_EX)` inside `with open()` block, or (b) assert JSONL lines < 4096 bytes (PIPE_BUF) and rely on POSIX atomic append. Option (b) is simpler. Both valid; Plan 02 implementer chooses."
2. Add rationale: "POSIX guarantees `write()` <= PIPE_BUF to O_APPEND files is atomic. Python `open(path, 'a')` uses O_APPEND."
**Impacts:** Plan 02 may be simplified (~5 LOC vs ~20 LOC)
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3 — POSIX atomic append well-established; "bound line length" less commonly documented as deliberate strategy
**Prerequisite:** no
**Status:** rejected
**Adversarial verdict:** REJECT (Data Integrity) — POSIX atomic append guarantee applies to `write()` syscall, not Python's buffered `f.write()`. Python may split a single `f.write()` into multiple `write()` syscalls for lines >4096 bytes. The `fcntl.flock()` fix is correct; the simplification is architecturally unsound. Existing Plan 02 fix is already well-specified.

### P10-IMP-07: Debate Protocol Cost-Benefit Unverified Against Calibration Anchor
**Target:** CONTEXT
**What:** Evaluator Debate Protocol (blind-then-debate, dual-Opus, 5-15 min per Core workflow) assumes value over the Calibration Anchor Protocol. The anchor already provides external ground truth validation (Spearman rho > 0.6). The debate's incremental value is assumed, never quantified.
**Why:** Debate adds ~$0.50-2.00 per workflow doubled, plus 5-15 min latency, plus complexity (EvaluatorDisagreement model, tie-breaking). If single-evaluator scores already correlate well with ground truth rankings, debate provides diminishing returns. The context should require cost-benefit validation before committing to debate for all Core workflows.
**How:**
1. Add validation requirement to Evaluator Debate Protocol: "Before exit gate 6, run single-evaluator alongside debate on 3 Core investigation workflows. If single-evaluator rank ordering matches debate (Kendall tau > 0.8), document debate as optional rather than Core default"
2. Plan 07 gains gating task: debate-value-validation
**Impacts:** Plan 07 may simplify significantly. Plan 08 wall-clock estimates may halve for Core
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3 — Inter-rater reliability studies exist; applying debate to LLM evaluators is novel
**Prerequisite:** no
**Status:** reframed
**Adversarial verdict:** REFRAME (Protocol Efficiency) — debate and calibration anchor protect against different failure modes (inter-rater noise vs rank-order accuracy). Kendall tau on 3 workflows cannot distinguish "debate is redundant" from "unambiguous transcripts." See P10-ADV-2-01 (Post-Debate Demotion Mechanism).

### P10-IMP-08: Graph-Reasoning Coherence Silent Failure on Non-Corpus Contracts
**Target:** CONTEXT
**What:** Plan 04 deliverable 4 says Graph-Reasoning Coherence is "Only computable for corpus contracts with ground truth." But no mechanism detects non-corpus contracts to set `applicable=False`. Investigation workflows on non-corpus contracts will either score 0 (poisoning weighted average) or crash.
**Why:** Any Investigation workflow run outside the 18-corpus set has a broken coherence dimension. The `applicable` field exists but no code path sets it based on ground truth availability.
**How:**
1. Plan 04 deliverable 4: replace "Only computable for corpus contracts with ground truth" with explicit guard: "`_check_citation_relevance()` must begin with `if context is None or context.get('ground_truth_entry') is None: return DimensionScore(name='graph_reasoning_coherence', applicable=False)`. ~3 LOC
2. Plan 01 deliverable 3: confirm `DimensionScore.applicable` already defined (`applicable: bool = True`). Guard produces `applicable=False` which `ScoreCard.effective_score()` already excludes
3. Add to Known Code Issues: "Graph-Reasoning Coherence Crashes on Non-Corpus Contracts" — Owner: Plan 04, Severity: HIGH
4. Plan 06 contracts: add `graph_reasoning_coherence: true` only for Core investigation contracts where corpus ground truth exists. All other contracts: `graph_reasoning_coherence: false`
**Impacts:** Plan 04 (+3 LOC), Plan 06 authoring guidance, Plan 06→08→04 data flow dependency for Cross-Plan Dependencies table
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Not a new capability; wiring existing `applicable=False` pattern
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Novel Capability) — correctly reframed as "missing application of existing pattern" not "new guard." Enhanced How targets correct location (`_check_citation_relevance()`) with concrete code.

### P10-IMP-09: Debrief Layer 1 SendMessage Has No Timeout Specification
**Target:** CONTEXT
**What:** SendMessage "has no delivery confirmation" and "always returns success even if recipient dead." No timeout specified for how long the CC test orchestrator waits for debrief response. Agent may be compacted, slow, or crashed. Without timeout, orchestrator blocks indefinitely with no fallback trigger to Layer 4.
**Why:** Concrete failure scenario: during test teardown in Plans 09-11, skill sends debrief questions, agent is dead/compacted, orchestrator hangs forever. No delivery confirmation means can't distinguish "thinking" from "dead."
**How:** _(original How superseded by REFRAME — see P10-ADV-5-01)_
**Impacts:** Plan 05, Plans 09-11
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4
**Prerequisite:** no
**Status:** reframed
**Adversarial verdict:** REFRAME (Novel Capability) — framing assumes blocking wait loop that doesn't exist in actual architecture. CC skill sends SendMessage then reads artifact from disk; no blocking read. Real failure mode is artifact absence, not infinite block. Timeout solves wrong problem. See P10-ADV-5-01 (Dead-Agent Debrief Artifact Validation).

### P10-IMP-10: Unmapped Dimension Fallback to Keyword Heuristic Is Self-Defeating
**Target:** CONTEXT
**What:** Plan 07 deliverable 6 says "Unmapped dimensions fall back to heuristic with logged warning." The heuristic is documented as "near-zero signal" and "Not substantially better than hardcoded 50" (Known Code Issues). Allowing silent fallback to a mechanism explicitly identified as broken defeats the purpose of the LLM evaluator.
**Why:** Any dimension accidentally omitted from DIMENSION_TO_MOVE_TYPES produces garbage scores with only a log warning. Better: unmapped = `applicable=False` with loud warning, not garbage heuristic.
**How:**
1. Change Plan 07 deliverable 6: "Unmapped dimensions produce `DimensionScore(score=0, applicable=False)` with WARNING including 'unmapped' to distinguish from mode-filtered N/A"
2. Add to Plan 07 exit criteria: "No dimension uses keyword heuristic fallback"
**Impacts:** Plan 07 stricter but cleaner. Plan 08 effective_score() already handles applicable=False
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Fail-safe with explicit N/A
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** CONFIRM (Protocol Efficiency) — withstands scrutiny. WARNING must distinguish `DIMENSION_UNMAPPED` from `DIMENSION_MODE_FILTERED` as distinct codes in warning message.

### P10-IMP-11: Plan 04 Exit Criterion "30+ Transcripts" Unreachable at Wave 3
**Target:** CONTEXT
**What:** Plan 04 exit criteria: "calibrated with 30+ transcripts." Plan 04 is Wave 3. Only 3+ transcripts exist at Wave 3 (from Plan 02). Plans 09-11 (Wave 6) produce the bulk. The 30-transcript gate cannot be satisfied when Plan 04 executes.
**Why:** Creates impossible gate. Either silently deferred (hidden re-entry), includes synthetic data (contradicts constraints), or blocks until Wave 6 (breaks dependency chain). None acceptable.
**How:**
1. Plan 04 exit criteria: change "calibrated with 30+ transcripts" to "Wave 3 gate: Checkbox < 30, genuine > 70 on 3+ real transcripts from Plan 02. Note: calibration on 30+ transcripts deferred to Wave 6"
2. Add soft dependency to Cross-Plan Dependencies: "12 Part 0 → 04 | Post-calibration re-validation on 30+ transcripts | NO"
3. Plan 12 Part 0 scope: "Re-validate GVS thresholds on corpus transcripts. If checkbox or genuine threshold shifts >15pt vs Wave 3 values, open regression issue before accepting Plan 12 improvement loop results"
4. Plan 04 CONTEXT entry must say "Wave 3 provisional calibration" — prevent future readers treating 3-transcript calibration as settled
**Impacts:** Plan 04 becomes achievable. Plan 12 gains re-validation subtask with regression threshold
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Standard phased validation
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Protocol Efficiency) — original correct in splitting gate but incomplete: no regression threshold, no provisional labeling, no action for drift. Enhanced adds >15pt threshold, provisional label, and Wave 6 re-validation action.

### P10-IMP-12: Evaluator LLM Calls Should Batch Dimensions, Not Call Per-Dimension
**Target:** CONTEXT
**What:** Evaluator Debate Protocol specifies separate sessions per evaluator. With per-dimension `claude -p` calls, debate means 14-21 subprocess invocations per Core workflow (7 dimensions × 2 evaluators + rebuttals). Each has ~5-10s startup overhead = 2.3-3.5 min pure startup.
**Why:** The context doesn't specify whether evaluator processes all dimensions in one call or one-per-dimension. Batching all 7 dimensions into a single evaluator call reduces from 14 calls to 2-3 calls, halving overhead.
**How:** _(original How superseded by REFRAME — see P10-ADV-2-02)_
**Impacts:** Plan 07
**Research needed:** yes
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Status:** reframed
**Adversarial verdict:** REFRAME (Protocol Efficiency) — the real efficiency question is debate granularity (per-dimension vs category-level rebuttals), not subprocess count. Batching doesn't eliminate per-dimension rebuttals. LLM evaluators assessing multiple criteria simultaneously exhibit halo effects. See P10-ADV-2-02 (Rebuttal Granularity Pilot).

### P10-IMP-13: ImprovementHint Calibration Gate Creates Undocumented Human Bottleneck
**Target:** CONTEXT
**What:** Improvement Hints Protocol: uncalibrated hints routed to human review only. Calibration requires exit gate 6. Exit gate 6 requires evaluator tuning. Tuning uses improvement loop. Loop uses hints. All hints are HITL-gated until calibration completes. The sequential dependency Part 0 → human review → Part 2 is not reflected in time estimates.
**Why:** Part 2 cannot begin until Part 0 passes AND human approves initial hint batch. Budget 1-2 days human review latency. Currently undocumented bottleneck.
**How:**
1. Plan 12 Part 2: add "Part 2 cannot begin until: (a) Part 0 calibration anchor passes Spearman rho > 0.6 gate, AND (b) human reviews `.vrs/evaluations/uncalibrated_hints.jsonl` and approves/rejects initial batch. Budget 1-2 days for human review latency between Part 0 completion and Part 2 start"
2. Add explicit timeline: "Minimum realistic Plan 12 timeline: Day 1-2 Part 0 (calibration runs + human approval of hints), Day 3-4 Part 1 (baseline establishment), Day 5-7 Part 2 (improvement variants), Day 8-10 Part 3 (metaprompting). Total: ~2 weeks minimum including human latency"
3. After Part 0 completes, CC skill should print: "Calibration complete. Review `.vrs/evaluations/uncalibrated_hints.jsonl` before running Part 2. Estimated review time: 1-2 hours per 10 hints"
4. Add HITL checkpoint to Plans 09-11: "Plans 09-11 should not run concurrently with Plan 12 Part 2 — hint generation during active test runs creates race between new hints and human review queue"
**Impacts:** Plan 12 time estimates become realistic. Race condition between Plans 09-11 and Plan 12 Part 2 documented
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Standard dependency chain analysis
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Protocol Efficiency) — original identified bottleneck but didn't provide timeline, CLI notification, or race condition with Plans 09-11 hint generation. Enhanced adds 2-week minimum timeline, CLI surface mechanism, and concurrent execution guard.

### P10-IMP-14: Headless Mode for Standard/Important Tier Should Be Binding Decision
**Target:** CONTEXT
**What:** Mode Capability Matrix documents what's available per run_mode. Budget estimates assume 45 min/workflow uniformly. But Standard tier needs "Lite" evaluation — no debrief, no interactive follow-up. Standard workflows could run headless at ~5-10 min/workflow instead of 45 min, cutting Standard sub-wave from ~10 hours to ~4-5 hours.
**Why:** Without binding run_mode-per-tier decision, implementers default to interactive for everything (safe choice), wasting 6+ hours on Standard tier workflows that gain nothing from interactivity.
**How:**
1. Add Implementation Decision "Tier-to-Run-Mode Binding" immediately after Mode Capability Matrix:
   - Core: `run_mode=interactive`
   - Important (Investigation): `run_mode=interactive`
   - Important (Tool/Support): `run_mode=headless`
   - Standard (all categories): `run_mode=headless`
   - Per-contract override: `evaluation_config.run_mode` overrides tier default (contract wins, tier is default)
2. Add `run_mode_default` to Schema Hardening Field Manifest as optional field
3. Plan 08: runner reads tier-to-mode table from config constant, NOT hardcoded. Plan 06 contracts can override via `evaluation_config.run_mode`
4. Revise Plans 09-11 budget: Important Investigation stays interactive (~15-20 min), Important Tool headless (~5-8 min), Standard all headless (~3-6 min)
5. Note: Investigation Important-tier stays interactive because it needs GVS + debrief for "standard reasoning" evaluation depth
**Impacts:** Plans 06 (schema field), 08 (tier-mode table), 09-11 (budget, session spawning), 12 (baseline keyed by run_mode)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — `claude --print` documented; tier-based mode selection straightforward
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Execution Architecture) — original missing: what happens when Core contract has `run_mode: headless`? Enhanced makes priority explicit (contract wins, tier is default) and adds schema field for machine-verifiable override.

### P10-IMP-15: /vrs-test-suite Skill Has No Design Specification
**Target:** CONTEXT
**What:** Plans 09-11 Architectural Restructuring declares primary artifact is CC skill `/vrs-test-suite`. Location Resolution confirms "Not yet created." But nowhere is the skill's behavior specified: input params, exit report schema, workflow iteration, Python runner handoff protocol. The dual-layer diagram shows layers but not the handoff.
**Why:** This is the single most important artifact in the Execution Layer with zero specification. Implementers face a blank page at Wave 6. Exit report schema is critical because pytest wrappers assert on it and Plan 12 baseline reads it.
**How:** _(original How superseded by REFRAME — see P10-ADV-3-01)_
**Impacts:** Plans 01, 08, 09-11, 12
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3
**Prerequisite:** no
**Status:** reframed
**Adversarial verdict:** REFRAME (Execution Architecture) — CONTEXT.md is wrong place for authoritative skill spec. The spec belongs in SKILL.md stub (`src/alphaswarm_sol/shipping/skills/test-suite/SKILL.md`) following same pattern as every other shipped skill. Exit report schema belongs in type system (Plan 01 Pydantic + JSON Schema), not prose. See P10-ADV-3-01 (SKILL.md Stub at Creation Time).

### P10-IMP-16: Python Runner vs CC Skill Scoring Boundary Ambiguous in Plan 08
**Target:** CONTEXT
**What:** Plan 08 described as "Full pipeline orchestrator" AND lists CC-skill-side concerns (kill support, tier filtering). EvaluationRunner at `tests/workflow_harness/lib/evaluation_runner.py` is Python, yet deliverable 11 describes "CC skill polls kill-file" — this is CC behavior, not Python runner. Document conflates two orchestrators.
**Why:** Implementer faces fundamental question: is EvaluationRunner the Python scoring pipeline (post-hoc) or the overall lifecycle orchestrator? If former, kill/filter/progress belong in CC skill. If latter, dual-layer separation is fiction. Ambiguity causes duplicate logic or vestigial layer.
**How:**
1. Split Plan 08 deliverables into two labeled subsections:
   - **EvaluationRunner (Python, `tests/workflow_harness/lib/evaluation_runner.py`):** Deliverables 1, 2, 3, 5, 7. Contract: takes `(session_id, contract)`, reads JSONL + debrief, runs GVS + reasoning evaluator, returns `EvaluationResult`. No filesystem side-effects. ~200 LOC
   - **Suite Orchestration (CC Skill, `src/alphaswarm_sol/shipping/skills/test-suite/`):** Deliverables 4, 8, 10, 11, 12, 13. Plan 08 DESIGN DECISIONS that Plans 09-11 implement
2. Update dual-layer diagram: annotate "CC skill calls `python evaluation_runner.py --session-id {id} --contract {path}`" at layer boundary
3. Plan 08 exit criterion: "EvaluationRunner runs standalone on fixture session without importing any CC skill code" — enforces separation
4. Move deliverable 11's CC skill path text to Plans 09-11 shared execution note
**Impacts:** Plan 08 scope clarification, Plans 09-11 gain explicit implementation targets
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — Orchestration/scoring separation standard; CC-skill-as-orchestrator novel
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Execution Architecture) — original moves deliverables to subsection but they still land in Plan 08. Real fix: EvaluationRunner is Plan 08's deliverable, CC skill orchestration is Plans 09-11's deliverable. Plan 08 contributes design spec for how skill calls runner.

### P10-IMP-17: Budget Estimates Self-Contradict (45 min vs 6-9 min per Workflow)
**Target:** CONTEXT
**What:** Plans 09-11 shared note: "Core sub-wave (~10, no debate): ~7.5 hours (45 min/workflow)." Plan 08 deliverable 6: "~6-9 min/workflow (Core), ~10 min/workflow (all tiers average)." These contradict: 45 min vs 6-9 min. The 45-minute figure appears to be the per_workflow_budget timeout ceiling (default 2700s) confused with expected duration.
**Why:** 5x overestimate leads to under-investment in re-running evaluations and over-design of optimization strategies. Accurate estimates determine whether staged rollout gates are necessary or could run end-to-end.
**How:**
1. Establish three named timing concepts in Plan 08 deliverable 6:
   - `per_workflow_execution_time`: how long real CC session takes. Estimate: Core investigation 15-30 min (attacker+defender+verifier), Tool integration 3-8 min, Support 1-3 min. Mark `[ESTIMATE: update after first Core run]`
   - `per_workflow_scoring_time`: Python evaluation pipeline time. Estimate: ~2-5 min (GVS + dual-Opus LLM calls). Mark similarly
   - `per_workflow_budget_ceiling`: timeout after which CC skill writes `interrupted`. Default 2700s (45 min) = ~3-5x expected execution time for Core. This is the 45 min figure; NOT expected duration
2. Revise shared execution note with three named concepts and explicit uncertainty markers
3. Add: "Revise estimates after first Core sub-wave run. If execution_time exceeds 30 min for Core, reassess budget_ceiling"
4. Remove "3-4 days" total estimate — replace with "pending first Core run measurement"
**Impacts:** Plans 09-11 planning. Plan 08 deliverable 6 becomes canonical timing reference
**Research needed:** no
**Confidence:** MEDIUM — all estimates carry explicit uncertainty markers
**Prior art:** 4 — Standard estimation reconciliation
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Execution Architecture) — original underestimates impact. 45 min vs 6-9 min discrepancy affects whether HITL gate review happens same-day. Enhanced names three distinct timing concepts (execution, scoring, ceiling) and marks all as provisional.

### P10-IMP-18: Model Selection Clarification — Evaluation Model vs System Under Test
**Target:** CONTEXT
**What:** "Cost is NOT a constraint. All tiers get Opus evaluation" (line ~1453). This conflates evaluation model (LLM that judges reasoning) with workflow execution model (LLM running the skill/agent being tested). Research shows `CLAUDE_CODE_SUBAGENT_MODEL` allows per-agent model selection.
**Why:** Prevents future implementer from "optimizing" by running Standard agents on Sonnet, then wondering why behavioral baselines shift. The system-under-test model must match its agent definition.
**How:**
1. Add clarifying note to Testing Tiers: "All tiers get Opus evaluation (the evaluator LLM). Workflow being tested runs on whatever model its agent/skill definition specifies — this is system-under-test, not a cost decision. Do NOT use CLAUDE_CODE_SUBAGENT_MODEL to override agent models during evaluation. Evaluator model remains Opus regardless of evaluation depth"
**Impacts:** Plans 09-11 implementation guidance. Prevents baseline contamination. See also P10-ADV-3-02 (depth-to-model binding)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Standard testing principle
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** CONFIRM (Execution Architecture) — passes scrutiny. Added "Evaluator model remains Opus regardless of evaluation depth" to prevent future shallow-depth Sonnet optimization. See P10-ADV-3-02 for hardcoded constant enforcement.

### P10-IMP-19: Skill Authoring Quality Check Missing from Evaluation Framework
**Target:** CONTEXT
**What:** The framework evaluates "does the skill work?" but not "is the skill well-authored?" These are independent quality axes. Skill authoring quality (concise descriptions, clear triggers, minimal permissions, well-structured SKILL.md) is absent from the evaluation pipeline.
**Why:** A skill can pass all behavioral evaluations while having bloated SKILL.md wasting context, unclear triggers confusing users, or excessive permissions creating security risks. If skill authoring quality degrades, behavioral evaluation eventually degrades too (worse prompts → worse behavior), but root cause is obscured. The user explicitly wants skills reviewed with /writing-skills.
**How:** _(original How superseded by REFRAME — see P10-ADV-5-02)_
**Impacts:** Plan 09
**Research needed:** yes
**Confidence:** MEDIUM
**Prior art:** 4
**Prerequisite:** no
**Status:** reframed
**Adversarial verdict:** REFRAME (Novel Capability) — conflates structural completeness (deterministic linting) with authoring quality (LLM-based evaluation). User's `/writing-skills` mention names LLM-based path, not a linter. 50-LOC script addresses structural completeness only, leaving actual quality problem unaddressed. See P10-ADV-5-02 (LLM-Based Skill Quality Evaluation, two-tier approach).

### P10-IMP-20: Zombie Subagent After Timeout — Undocumented Failure Scenario
**Target:** CONTEXT
**What:** Plan 08 acknowledges "CC skill cannot interrupt running subagent mid-execution." But does not explore the failure: Core investigation spawns attacker + defender + verifier. Attacker enters infinite loop. 45-min timeout fires. CC skill writes `status: interrupted` and starts next workflow. But zombie attacker still runs, writing to JSONL file. New workflow's hooks interleave with zombie's hooks in shared `.vrs/observations/` directory.
**Why:** Not hypothetical — LLM agents entering unproductive loops is known. Zombie subagent writes corrupted observations to shared directory. Per-session file naming only protects if session IDs differ, but zombie's hooks use the OLD session ID while new workflow starts a NEW session.
**How:**
1. Add Documented Failure Scenario FS-02: "Late Zombie Artifact Contamination" — Mechanism: interrupted session's subagent completes after next workflow starts, writes complete observations, scoring pipeline processes it as valid result contaminating baseline
2. Mitigations:
   - (a) EvaluationResult at `interrupted` status NEVER written to baseline (verify deliverable 2 covers late-completing sessions)
   - (b) CC skill writes `{session_id}.interrupted` sentinel in observation directory upon timeout. EvaluationRunner checks sentinel before scoring — if found, skip regardless of JSONL completeness. ~5 LOC
   - (c) 60-second grace period before starting next workflow
3. Plan 08 EvaluationRunner: add sentinel check (~5 LOC). Plan 02 ObservationWriter: ignore write attempts after sentinel detected
4. Note: per-workflow observation subdirectory NOT required — sentinel file sufficient and simpler
**Impacts:** Plans 02 (+5 LOC), 08 (+5 LOC sentinel check)
**Research needed:** no — RESOLVED. CC fires `SubagentStop` hook when a subagent finishes (documented in official hook lifecycle: 14 events). The CC skill can install a SubagentStop hook that writes a `{session_id}.completed` marker file. This provides definitive termination detection. The 60-second grace period is still useful as a fallback (SubagentStop may not fire if subagent crashes), but is no longer the primary mechanism. SubagentStop hook + sentinel file = complete zombie detection.
**Research resolved by:** resolve-blockers web research (2026-02-19)
**Confidence:** HIGH (upgraded from MEDIUM — SubagentStop confirmed in hook lifecycle)
**Prior art:** 3 (upgraded — SubagentStop documented but zombie-detection-via-hook pattern is novel)
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Execution Architecture) — original proposes per-workflow directory (over-engineering). Per-session JSONL naming already prevents file-level interleaving. Real risk is phantom-valid-artifact from late completion, solved by sentinel file (~5 LOC) not directory restructuring.

### P10-IMP-21: Plan 12 Part 1 Baseline Key Missing `debate_enabled`
**Target:** CONTEXT
**What:** Plan 12 Part 1 says baseline "Keyed by `(workflow_id, run_mode)`" but the locked Implementation Decision "Debate Baseline Key (ADV-3-01)" mandates triple `(workflow_id, run_mode, debate_enabled)`. Plan Summary contradicts Implementation Decision.
**Why:** Not cosmetic. Planner reading Plan 12 literally implements 2-field BaselineKey. Baseline without `debate_enabled` mixes debate and non-debate scores, making regression detection unreliable.
**How:**
1. Plan 12 Part 1: change "Keyed by `(workflow_id, run_mode)`" to "Keyed by `(workflow_id, run_mode, debate_enabled)`"
2. Verify no other Plan Summary references 2-field baseline key
**Impacts:** Plan 12 implementation correctness
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 — Copy-paste fix from existing decision
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** CONFIRM (Loop Operability) — Part 1 description inconsistency with locked decision is real but already authoritatively resolved in Implementation Decisions. Fix narrows to adding `debate_enabled` to Part 1 description sentence specifically.

### P10-IMP-22: v2 Automated Trigger Deferral Lacks Rationale
**Target:** CONTEXT
**What:** Deferred Ideas says "v1 uses manual trigger protocol" for re-evaluation but doesn't explain WHY automation is deferred when SessionStart hooks + `claude --print` make it trivially achievable. Without rationale, future reviewers re-propose it (already rejected in prior passes).
**Why:** Missing rationale invites re-proposal loop. The manual protocol is correct because human judgment on score deltas prevents FS-01 self-sealing loop. One sentence fixes the documentation gap.
**How:**
1. Add rationale to v1 Manual Trigger Protocol section: "Rationale: v1 automation deferred because (a) real improvement cycles haven't run — cannot validate trigger heuristics without data, (b) automated re-evaluation without human approval creates vector for Goodhart's Law gaming (framework optimizes for triggers it generates), (c) HITL gate (Pillar 4, Rule E) for prompt changes requires human-initiated context, not automated queuing"
2. Same rationale also added to Deferred Ideas v2 automated trigger entry
**Impacts:** None — documentation clarity only. Prevents re-proposal loop
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Loop Operability) — original "1-sentence rationale" too minimal. Real risk is implementor treating manual as merely delayed, not structurally excluded. Enhanced connects deferral to Goodhart's Law FS-01 failure mode.

### P10-IMP-23: Plan 12 Part 0 Infrastructure Diagnostic Has No Early-Exit Guard
**Target:** CONTEXT
**What:** Part 0 outputs `infrastructure_misses.yaml` and Part 2 reads it to skip patterns. But no threshold blocks Part 2 if most patterns are infrastructure misses. If 25 of 28 Tier A patterns are infrastructure misses, Part 2 proceeds with 3 addressable patterns — spending hours on improvements that cannot satisfy exit gate 18's denominator floor (20 Tier A).
**Why:** Concrete failure: Part 0 finds massive infrastructure gaps, Part 2 burns 8+ hours on 3 patterns, then exit gate 18 fails. The denominator floor exists but only at exit gate time, not at Part 0.
**How:**
1. Add early-exit guard to Part 2 startup (~5 LOC): after reading `infrastructure_misses.yaml`, count addressable targets. If `addressable_count < 5`, HALT Part 2 and write `part2_blocked.yaml` with reason `insufficient_addressable_patterns` and counts: `{total_low_scoring, bskg_gaps, vulndocs_gaps, addressable}`
2. This is distinct from denominator floor in exit gates — runtime guard on Part 2 execution, not phase gate
3. Rationale includes contamination risk: low-addressable runs that complete produce ExperimentLedgerEntry records counting toward N=5 convergence threshold, potentially declaring CONVERGED_PLATEAU when real issue is infrastructure
**Impacts:** Plan 12 Part 2 prevents wasted compute AND convergence contamination
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Early-exit guards already used elsewhere in context
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Loop Operability) — original undershoots risk. Not just "Part 2 wastes time" but improvement loop produces valid-looking ExperimentLedgerEntry records with no signal, contaminating convergence detection.

### P10-IMP-24: Experiment Ledger Has No Storage Location or Format
**Target:** CONTEXT
**What:** Experiment Ledger Protocol defines 5 required fields. `ExperimentLedgerEntry` model in Plan 01. But nowhere specifies WHERE the ledger is stored or in what format. CLI `alphaswarm evaluation summary` needs to read it. Convergence detection reads past entries. Calibration Anchor says "each entry must include counterexample" — implies append-only and queryable.
**Why:** Planner implementing Plan 12 Part 2 decides storage ad-hoc. Should be locked because CLI, convergence detection, and calibration all read it.
**How:**
1. Add to Experiment Ledger Protocol and Plan 12 Part 2 description:
   - Storage path: `.vrs/evaluations/experiment_ledger.jsonl` (append-only, one `ExperimentLedgerEntry` per line)
   - Format: Pydantic `.model_dump_json()` serialization (consistent with `.vrs/evaluations/` artifacts)
   - Reader API: `ExperimentLedger.load(path) -> list[ExperimentLedgerEntry]` with `filter_by_dimension(dim)` for convergence detection; `filter_by_workflow(wf)` for Failure Reporter
2. Location Resolution table: `| ExperimentLedger | .vrs/evaluations/experiment_ledger.jsonl | Created in Plan 12 Part 2 |`
3. CLI addition: `alphaswarm evaluation ledger [--dimension DIM] [--format json|table]` (~40 LOC)
4. Plan 01: add round-trip test `ExperimentLedgerEntry → jsonl line → reload` to verify append-only format
**Impacts:** Plan 01 (round-trip test), Plan 12 Parts 2, 3, 4; CLI implementation. Convergence detection and Failure Reporter gain read path
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Same JSONL pattern as existing artifacts
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Loop Operability) — highest-severity gap. Experiment Ledger is data backbone of improvement loop. Without storage spec, in-memory-only ledger means CONVERGED_PLATEAU classifications can't persist across 3-4 day staged execution. Enhanced adds reader API and Plan 01 round-trip test.

### P10-IMP-25: 9 Intelligence Module Stubs Create Maintenance Burden With Zero Value
**Target:** CONTEXT
**What:** 12 intelligence modules: 3 real, 9 stubs. Each stub requires Python file, unit test, `__init__.py` entry, activation threshold = ~15-20 LOC × 9 = ~135-180 LOC of code that does nothing except pass `is_active() -> False`.
**Why:** Stubs exist to "show the roadmap" but the roadmap is already shown by the Intelligence Module table in CONTEXT.md. Stubs create illusion of progress and impose maintenance cost when any interface change requires updating 9 files. The interface is not stable yet (no real data has flowed). `intelligence/ROADMAP.md` achieves same goal with zero maintenance.
**How:** _(original How superseded by REFRAME — see P10-ADV-4-01)_
**Impacts:** Plan 12 Part 5, exit gate 16
**Research needed:** no
**Confidence:** MEDIUM
**Prior art:** 3
**Prerequisite:** no
**Status:** reframed
**Adversarial verdict:** REFRAME (Loop Operability) — misidentifies problem as "LOC cost" when real issue is "exit gate cheapness." Eliminating stubs and using ROADMAP.md would DELETE the verifiable gate. Correct fix: strengthen exit gate 16 to test activation logic against mock stores, not just `is_active()` existence. See P10-ADV-4-01 (Strengthen Exit Gate 16).

### P10-IMP-26: Plan 12 Part 2 Improvement Variants Have No Time Budget
**Target:** CONTEXT
**What:** Part 2: "3-5 sequential variants. ~25 min/dimension/variant." With 5 low-scoring dimensions × 5 variants = 25 variants × 25 min = ~10.4 hours. Per improvement cycle, with convergence allowing 5 cycles for Core = potentially 50+ hours before convergence halts it.
**Why:** Without per-cycle budget, Part 2 can consume 50+ hours. Experiment Ledger has per-entry kill criteria but no aggregate budget. Makes "v1 manually-triggered" impractical as human must babysit for days.
**How:**
1. Add to Plan 12 Part 2 description:
   - **Session budget:** Maximum 3 improvement cycles per CC session. After 3 cycles, write `part2_checkpoint.yaml` with current state and exit cleanly. Human restarts Part 2 in new session from checkpoint
   - **Aggregate budget:** Maximum 20 dimension-improvement targets per Part 2 run. Beyond 20, generate `FailureReport` for remaining dimensions with `recommendation: escalate_to_human` and proceed to Part 4
   - **Priority queue:** Dimensions in priority order: (1) Core scoring < 30, (2) Core 30-50, (3) Important < 30. Stop when budget exhausted
2. Add budget parameters to Plan 12 exit criterion: "Part 2 stays within 3-cycle session budget (checkpoint written on exit) and 20-target aggregate budget (surplus generates FailureReports)"
**Impacts:** Plan 12 Part 2 — concrete session and aggregate stopping criteria
**Research needed:** no
**Confidence:** MEDIUM — Numbers are judgment calls; principle (bounded cycles) HIGH
**Prior art:** 4 — Standard time-boxing
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** ENHANCE (Loop Operability) — original vague. Enhanced provides concrete session budget (3 cycles) forcing checkpoint discipline from day 1, required for multi-day staged execution. Aggregate budget (20 targets) prevents unbounded loop. Priority queue ensures highest-impact dimensions addressed first.

### P10-IMP-27: Research "Parallel Baseline via Agent Teams" Violates Sequential Constraint
**Target:** RESEARCH
**What:** Research finding #9 suggests parallel baseline collection via Agent Teams. But locked constraint: "Agent Teams must execute sequentially in top-level sessions." Parallel sessions require 5 independent terminals or CI-based parallelism, not Agent Teams.
**Why:** Research finding is misleading if consumed by planner. Proposed parallelization violates locked constraint.
**How:**
1. Add note to research finding: "Constraint: CONTEXT.md locks Agent Teams to sequential sessions. Parallelism requires 5 independent terminals or CI (`claude --print` in parallel GitHub Actions jobs), not Agent Teams"
**Impacts:** Research accuracy. Prevents future confusion
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no
**Status:** implemented
**Adversarial verdict:** CONFIRM (Loop Operability) — correctly identifies constraint violation risk. Scoped: annotation belongs in RESEARCH.md Open Questions as standing instruction for future research spike authors.

## Adversarial CREATE Items

### P10-ADV-1-01: Observation File Staleness Guard
**Target:** CONTEXT
**Source:** Adversarial review (Data Integrity) — replacement for REFRAME of P10-IMP-04
**Cross-references:** P10-IMP-04
**What:** The real risk is not missing schema_version but stale observation files from prior runs contaminating current analysis. ObservationParser loads ALL `*.jsonl` files in the directory (per IMP-03). If prior run's files exist, current analysis mixes sessions. The guard: before each evaluation run, validate that observation files in the target directory have timestamps within the current session window. Stale files (>1 hour old at run start) produce a WARNING and are excluded from parsing.
**Why:** Schema versioning solves a problem that doesn't exist yet (no consumers of old-format records). Stale file contamination happens NOW on every re-run. IMP-03's session_id filter partially solves this but doesn't handle the case where a prior session used the same session_id pattern or left partial writes.
**How:**
1. Plan 03: `ObservationParser` constructor checks file mtime against session start time. Files older than `max_staleness_seconds` (default 3600) produce WARNING and are skipped
2. Plan 08: EvaluationRunner passes session start time to parser
3. Add to Known Code Issues: "Stale Observation Files" — Owner: Plan 03, Severity: MEDIUM
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

### P10-ADV-2-01: Post-Debate Demotion Mechanism for Core Tier
**Target:** CONTEXT
**Source:** Adversarial review (Protocol Efficiency) — replacement for REFRAME of P10-IMP-07
**Cross-references:** P10-IMP-07
**What:** After first 5 Core-tier runs with debate enabled, measure per-dimension disagreement distribution. If median disagreement < 5pt (meaning debate almost never triggers rebuttals), document formal demotion path: debate moves to re-validation-only for workflows with stable score history (CV < 0.1 over 5 runs). Preserves debate for new/unstable workflows while allowing cost reduction where it demonstrably adds no value.
**Why:** The cost concern in IMP-07 is legitimate (5-15 min/workflow × 10 Core = 50-150 min debate overhead per cycle). But eliminating debate based on 3-workflow pre-measurement is premature. Correct instrument is behavioral demotion conditioned on observed stability, not structural removal before data exists.
**How:**
1. Add to Evaluator Debate Protocol: "Debate demotion path: after 5 Core-tier runs, measure median per-dimension disagreement. If median < 5pt across >70% of dimensions, workflow may be demoted to 'debate-optional' for subsequent re-validation runs. Tracked in `pending_tier_changes.yaml` with `debate_optional: true`. Re-evaluation restores debate-required if disagreement rises above 10pt"
2. Plan 07 observation deliverable: "Log per-dimension A/B score deltas to `.vrs/evaluations/debate_disagreements.jsonl` for all Core runs"
3. Plan 12 Part 1 reads `debate_disagreements.jsonl` to identify demotion candidates
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

### P10-ADV-2-02: Rebuttal Granularity Pilot — Batch vs Per-Dimension
**Target:** CONTEXT
**Source:** Adversarial review (Protocol Efficiency) — replacement for REFRAME of P10-IMP-12
**Cross-references:** P10-IMP-12
**What:** Before committing to per-dimension or batch debate architecture in Plan 07, run 2-hour pilot using 6 existing calibration transcripts to compare: (a) 7 separate per-dimension evaluator calls, (b) 1 batch call with array JSON schema. Compare on: rebuttal specificity, halo effect presence, subprocess count.
**Why:** Batch vs per-dimension has real quality tradeoff. LLM evaluators assessing multiple criteria simultaneously exhibit halo effects. Calibration transcripts provide ready-made test set with known quality bands.
**How:**
1. Plan 07 pre-implementation checklist: "Run batch vs per-dimension pilot on 6 calibration transcripts (2 hours). Record: rebuttal specificity (binary: cites dimension-specific evidence vs generic), halo effect delta (non-contested dimension scores in batch vs per-dimension), subprocess count"
2. If batch produces >80% specific rebuttals AND no halo effect (deltas < 5pt): adopt batch. Otherwise: keep per-dimension
3. Result in Implementation Decision "Evaluator Debate Granularity" with pilot data
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

### P10-ADV-3-01: SKILL.md Stub for /vrs-test-suite at Wave 1
**Target:** CONTEXT
**Source:** Adversarial review (Execution Architecture) — replacement for REFRAME of P10-IMP-15
**Cross-references:** P10-IMP-15
**What:** Create `src/alphaswarm_sol/shipping/skills/test-suite/SKILL.md` stub during Wave 1 (alongside Plan 01), not at Wave 6. Stub contains: (a) skill purpose, (b) input parameters with types/defaults, (c) exit report schema reference, (d) per-workflow loop pseudocode (6-8 steps), (e) TODO markers for Wave 2-5 decisions. CONTEXT.md retains only architectural framing pointer.
**Why:** Every other shipped skill has SKILL.md. Writing spec in CONTEXT.md creates second authoritative source. Exit report schema belongs in type system (Plan 01 Pydantic + JSON Schema), not prose.
**How:**
1. Wave 1: create SKILL.md stub with `[TO-FILL: Plan 09]` markers
2. Create `.vrs/schemas/test_suite_exit_report.schema.json`
3. Add `SuiteExitReport` Pydantic model to Plan 01 deliverables
4. Update Plans 09-11 Location Resolution: point to SKILL.md for spec
5. Plan 08 exit criterion: "SKILL.md stub exists and SuiteExitReport schema validates synthetic exit report"
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

### P10-ADV-3-02: Depth-to-Evaluator-Model Binding
**Target:** CONTEXT
**Source:** Adversarial review (Execution Architecture) — companion to CONFIRM of P10-IMP-18
**Cross-references:** P10-IMP-18
**What:** IMP-18 clarifies "all tiers get Opus evaluation" but `evaluation_config.depth` has three values (shallow/standard/deep). A future implementer could parameterize evaluator model by depth. Binding: evaluator model determined by depth setting, and for v1 all depths use Opus.
**Why:** Plan 07's `_llm_evaluate_dimension()` calls `claude -p`. Nothing constrains which model. Parameterizing by depth makes Standard (shallow, Sonnet) scores incomparable to Core (deep, Opus) — breaking Plan 12 regression baseline.
**How:**
1. Add to Evaluator LLM Call Path: "v1: always `claude-opus-4-6` for `_llm_evaluate_dimension()` regardless of depth. Depth controls which dimensions evaluated and question count — NOT evaluator model. Changing evaluator model requires new baseline key"
2. Plan 07: hardcode `EVALUATOR_MODEL = "claude-opus-4-6"` as named constant
3. Plan 12 Part 1: note model change requires baseline reset
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

### P10-ADV-3-03: Timeout Ceiling vs Expected Duration Propagation to Plan 12
**Target:** CONTEXT
**Source:** Adversarial review (Execution Architecture) — cross-item analysis of P10-IMP-17 + P10-IMP-26
**Cross-references:** P10-IMP-17, P10-IMP-26
**What:** The 45 min / 6-9 min contradiction has downstream effect: Plan 12 Part 2 estimates "~25 min/dimension/variant" (unexplained). If derived from wrong 45-min baseline, also wrong by 5x factor. IMP-26's 3-hour cap based on this figure — incompatible assumptions.
**Why:** Plan 12 implementers use variant estimate to plan improvement loop. Wrong estimate in either direction makes 3-hour cap either over-constraining or under-constraining.
**How:**
1. After IMP-17 reconciles Core timing, trace through Plan 12 Part 2's "25 min" figure: execution + evaluation time?
2. Define: `improvement_variant_time = per_workflow_execution_time + per_workflow_scoring_time`. Mark `[ESTIMATE]`
3. IMP-26's 3-hour cap should reference this named estimate
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

### P10-ADV-4-01: Strengthen Exit Gate 16 to Prevent Stub-Pass Gaming
**Target:** CONTEXT
**Source:** Adversarial review (Loop Operability) — replacement for REFRAME of P10-IMP-25
**Cross-references:** P10-IMP-25
**Priority:** HIGH
**What:** Exit gate 16 is trivially satisfiable. A stub `is_active() -> False` passes any unit test asserting bool return. Gate says "passes `is_active()` unit tests" but doesn't specify what tests assert.
**Why:** 9 stubs with `is_active() -> False` + 3 real modules = gate satisfied without demonstrating activation thresholds trigger in realistic store states.
**How:** Rewrite exit gate 16:
"(a) `tier_manager`, `contract_healer`, `coverage_radar` have real implementations with `is_active()` returning `True` under specified conditions: `tier_manager` True when `store.run_count >= 3`, `contract_healer` True when `store.run_count >= 5`, `coverage_radar` True when any contract has `coverage_axes` populated
(b) Unit tests verify BOTH states (True and False) for each real module using mock stores at boundary counts
(c) `get_active_modules()` test: zero-run store returns empty; 5-run store with populated `coverage_axes` returns `['coverage_radar']`
(d) 9 stubs return `is_active() -> False` with mandatory `# TODO(v2): activation threshold = ...` comment. CI grep check: 9 matches required"
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

### P10-ADV-4-02: Experiment Ledger Cross-Session Continuity
**Target:** CONTEXT
**Source:** Adversarial review (Loop Operability) — cross-item analysis of P10-IMP-24 + P10-IMP-26
**Cross-references:** P10-IMP-24, P10-IMP-26
**Priority:** HIGH
**What:** Convergence detection classifies CONVERGED_HIGH/PLATEAU/LOW after N cycles per dimension. Session budget (IMP-26) checkpoints after 3 cycles. These interact: if ledger not durably persisted between sessions, convergence detection can't count across sessions.
**Why:** Plan 12 runs across multiple CC sessions (3-4 days). Without durable `experiment_ledger.jsonl` (IMP-24) AND explicit cross-session load in convergence detection, N-cycle counter resets to 0 each session. Dimension could receive N=5 across 5 sessions without triggering CONVERGED_PLATEAU.
**How:**
1. Plan 12 Part 3: "Convergence detection MUST load ALL prior entries from `experiment_ledger.jsonl` at startup (not just current session). `filter_by_dimension(dim)` returns entries across all sessions. N-cycle count cumulative"
2. Checkpoint `part2_checkpoint.yaml` records targeted dimensions and current cycle count — convergence reads checkpoint AND ledger to reconstruct state
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

### P10-ADV-5-01: Dead-Agent Debrief Artifact Validation
**Target:** CONTEXT
**Source:** Adversarial review (Novel Capability) — replacement for REFRAME of P10-IMP-09
**Cross-references:** P10-IMP-09
**What:** Real failure mode is artifact absence after elapsed wait, not infinite blocking loop. CC skill sends SendMessage then reads artifact from disk — no blocking read. Add bounded artifact-presence check with sentinel for dead-agent detection.
**Why:** SendMessage returns success even if recipient dead (CC platform behavior). Without artifact-presence check with bounded wait, runner reads missing file and either crashes or silently falls through with no record of Layer 1 attempt.
**How:**
1. Plan 05 deliverable 3: `DebriefResponseValidator` adds `layer_used="send_message_no_response"` signal
2. Plans 09-11 CC skill: post-SendMessage artifact-presence check with configurable wait (default `debrief_wait_seconds: 60`). If absent after wait: write sentinel JSON `{layer_used: "send_message_no_response", answers: [], confidence: 0.0}`, continue to Layer 3
3. Add Documented Failure Scenario FS-03: "Dead Agent — Layer 1 Returns Success, Artifact Never Written"
4. `debrief_wait_seconds: int = 60` added to evaluation contract schema + Schema Hardening Field Manifest
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

### P10-ADV-5-02: LLM-Based Skill Quality Evaluation (Two-Tier)
**Target:** CONTEXT
**Source:** Adversarial review (Novel Capability) — replacement for REFRAME of P10-IMP-19
**Cross-references:** P10-IMP-19
**What:** Two-tier approach separating concerns: Tier 1 (structural completeness, ~20 LOC deterministic): SKILL.md exists, has trigger section, has example, no duplicate tools. Hard blocker. Tier 2 (LLM authoring quality): invoke `agent-skillcraft` quality checklist via `claude -p` as rubric. Produces scored dimensions: description_clarity, trigger_precision, context_efficiency, permission_minimality (each 0-100). Writes `skill_quality_scores.yaml`. Scores below 60 generate `ImprovementHint` entries.
**Why:** User's `/writing-skills` mention names LLM-based path. Deterministic linter catches "no trigger section"; LLM evaluation catches "trigger section is ambiguous." Implementing only Tier 1 creates false confidence.
**How:**
1. Implementation Decision "Skill Quality Evaluation (Two-Tier)": Tier 1 structural (hard blocker, ~20 LOC), Tier 2 LLM quality (scored, Core/Important skills only)
2. Plan 09 deliverables: "Tier 1 structural check" + "Tier 2 LLM quality evaluation using agent-skillcraft checklist (~40 LOC wrapper around `claude -p`)"
3. `skill_quality_scores.yaml` in Plan 09 outputs, Location Resolution table
4. ImprovementHint generation for dimensions below 60, routed to human review
5. NOT scored in baseline — Plan 12 reads in Part 3 only (metaprompting input)
6. Token budget: ~2k per skill × 30 skills = ~60k tokens. Pre-suite step, not per-workflow
7. **Note:** Tier 2 requires Plan 07's `claude -p --json-schema` path — add Plan 07 → Plan 09 dependency to Cross-Plan Dependencies table
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** no
**Status:** implemented

## Post-Review Synthesis

### P10-SYN-01: Scattered Observation Pipeline Health Signals Have No Aggregation Point
**Target:** CONTEXT
**What:** Three separate items each add a distinct data-quality signal to the observation pipeline but none of them propagates the signal to a consumer that can act on it. P10-IMP-02 (enhanced) adds `_serialize_errors: int` counter to ObservationWriter. P10-IMP-03 (enhanced) adds session-id filtering that silently drops cross-session records. P10-ADV-1-01 adds an mtime staleness guard that WARNING-logs stale files. Each signal stays local to its detection point. Plan 08 EvaluationRunner — which decides whether to score a session — never sees any of these signals. An `ObservationSummary.data_quality` sub-object collecting all three would let Plan 08 apply a unified "data quality gate" before scoring starts instead of silently producing misleading EvaluationResults.
**Why:** Individually, each guard reduces a specific failure mode. Together, they leave an invisible quality gap: a session with 3 serialize errors, 12 dropped cross-session records, and 2 stale files still produces a fully-scored `EvaluationResult` that enters the baseline. The improvement loop (Plan 12) then operates on contaminated signal. Aggregating into `ObservationSummary.data_quality` makes degraded sessions detectable and rejectable in one place instead of requiring Plan 08 to query three separate counters.
**How:**
1. Plan 01: Add `ObservationDataQuality` Pydantic sub-model: `serialize_errors: int = 0`, `cross_session_records_dropped: int = 0`, `stale_files_excluded: int = 0`, `degraded: bool` (True if any field > 0). ~10 LOC
2. Plan 03: `ObservationParser.parse()` returns `ObservationSummary` with `data_quality: ObservationDataQuality` populated from writer counter (IMP-02), session filter (IMP-03), and staleness guard (ADV-1-01)
3. Plan 08: EvaluationRunner checks `obs_summary.data_quality.degraded` before scoring. If True, set `EvaluationResult.data_quality_warning: str` (populated from quality fields). Do NOT reject automatically — human decides via progress.json. ~10 LOC guard
4. Plan 12 Part 1 baseline: exclude sessions with `data_quality_warning` present from variance computation. Include in baseline only after human review of warning
**Impacts:** Plans 01, 03, 08, 12
**Components:** P10-IMP-02, P10-IMP-03, P10-ADV-1-01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Standard pipeline health aggregation pattern
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)

### P10-SYN-02: Three Artifact-Contamination Mitigations Use Incompatible Detection Mechanisms
**Target:** CONTEXT
**What:** Three separate items each address the same root pattern — a prior or parallel session's artifacts appearing valid to the current session's consumers — but propose independent mechanisms with no shared contract. P10-ADV-1-01 detects contamination via file mtime (staleness guard in ObservationParser). P10-IMP-20 (enhanced) detects contamination via a `{session_id}.interrupted` sentinel file written by the CC skill. P10-ADV-5-01 detects debrief artifact absence via a bounded wait then writes a `send_message_no_response` sentinel JSON. These three mechanisms are not aware of each other. A zombie session (IMP-20) may write complete JSONL that passes the staleness guard (it is recent) and passes the session-id filter (same session namespace), while the interrupted sentinel exists — but Plan 08 only checks the sentinel, not the staleness guard, and only in some code paths. No single "session validity manifest" ties these together.
**Why:** Individually each guard addresses its specific scenario. But they can contradict each other: ADV-1-01 may allow a zombie-written file as "recent enough" while IMP-20's sentinel says "interrupted." If Plan 08 checks them independently (or worse, only one of them), it can produce valid-looking EvaluationResults for contaminated sessions. The issue is not that any single guard is wrong — it is that three guards protecting the same invariant ("this session's artifacts are trustworthy") have no shared enforcement point.
**How:**
1. Add Implementation Decision "Session Validity Manifest": before Plan 08 scores any session, it constructs a `SessionValidityManifest` by checking in order: (a) `{session_id}.interrupted` sentinel absent (IMP-20), (b) observation file mtime within staleness window (ADV-1-01), (c) debrief artifact present OR sentinel JSON `send_message_no_response` written (ADV-5-01). All three checks apply regardless of run_mode. Manifest: `{session_id, valid: bool, reasons: list[str]}`
2. Plan 08 EvaluationRunner: add `_check_session_validity(session_id, obs_dir, debrief_dir) -> SessionValidityManifest` (~25 LOC). Score only if `manifest.valid`. If invalid, write `EvaluationResult(status="invalid_session", reasons=manifest.reasons)` — never enters baseline
3. Add `SessionValidityManifest` Pydantic model to Plan 01 deliverables
4. Document in Documented Failure Scenarios: "FS-04: Valid-Looking Artifacts from Invalid Session — Three Contamination Guards Must All Pass"
**Impacts:** Plans 01 (model), 03 (staleness check feeds manifest), 05 (debrief artifact feeds manifest), 08 (manifest check before scoring), 12 (invalid sessions excluded from baseline)
**Components:** P10-IMP-20, P10-ADV-1-01, P10-ADV-5-01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — Session validity as a unified pre-scoring check is novel in this architecture; individual guards are standard
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cross-cutting)

### P10-CSC-01: New PostToolUseFailure Hook Produces Record Type ObservationParser Cannot Handle
**Target:** CONTEXT
**What:** P10-IMP-01 (enhanced) adds `obs_tool_failure.py` hook producing JSONL records with `event_type: tool_failure` (or equivalent). ObservationParser (Plan 03) currently handles `PreToolUse`, `PostToolUse`, `SubagentStart`, `SubagentStop`, `Stop`, `SessionStart`, `TeammateIdle`, `TaskCompleted`. No parser branch handles the new failure event type. The parser will either silently skip these records or route them to the wrong handler, producing incorrect `ObservationSummary.tool_counts` and potentially corrupting the tool-pairing logic.
**Why:** Silent skip would mean GVS never sees failed graph queries — the exact failure-mode discrimination that IMP-01 was added to enable. Wrong handler would corrupt tool sequence analysis used by Plan 04. This gap opens the moment IMP-01 is implemented and obs_tool_failure.py starts writing records, before Plan 03 is updated.
**How:**
1. Plan 03 deliverable addition: "Add `_handle_tool_failure(record)` branch to ObservationParser. Populate new `ObservationSummary.tool_failures: list[ToolFailureRecord]` field. `ToolFailureRecord`: `tool_name, tool_use_id, error_type, timestamp`. ~15 LOC"
2. Plan 01: add `ToolFailureRecord` Pydantic model and `tool_failures: list[ToolFailureRecord] = []` to `ObservationSummary`
3. Plan 04 GVS: when `PostToolUseFailure` events present for `alphaswarm query` calls, treat as "query attempted but failed" — count toward graph-first compliance check (agent tried) but reduce result_utilization score (no result to utilize). ~10 LOC
4. Cross-Plan Dependencies table: add "01 → 03 | ToolFailureRecord model | YES" and "02 (IMP-01) → 03 | tool_failure event type handling | YES"
**Impacts:** Plans 01, 03, 04
**Trigger:** P10-IMP-01
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Standard parser extension for new record types
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

### P10-CSC-02: Provisional GVS Calibration Invalidates Early ExperimentLedger Entries When Wave 6 Threshold Shifts
**Target:** CONTEXT
**What:** P10-IMP-11 (enhanced) correctly splits GVS calibration into "Wave 3 provisional (3 transcripts, checkbox < 30 / genuine > 70)" and "Wave 6 re-validation (30+ transcripts)." If Wave 6 re-validation finds thresholds shift >15pt (the regression threshold IMP-11 specifies), all ExperimentLedgerEntry records from Plan 12 Parts 0-2 were scored using the wrong GVS thresholds. Plan 12 convergence detection reads these entries to classify dimensions as CONVERGED_HIGH/PLATEAU/LOW. Entries scored under miscalibrated GVS may have reached CONVERGED_PLATEAU at a score that was actually CONVERGED_HIGH under correct calibration, or vice versa. No item defines what happens to prior ledger entries when calibration drifts.
**Why:** Convergence classifications are irreversible under current design — CONVERGED_PLATEAU triggers human review queue, CONVERGED_LOW generates FailureReport and halts attempts. If Wave 6 reveals calibration drift >15pt, prior classifications are suspect. The improvement loop may have halted improvement on a dimension that was actually performing well, or continued on one that was actually failing.
**How:**
1. Add to Plan 12 Part 0 Wave 6 re-validation scope: "If GVS thresholds shift >15pt, mark all ExperimentLedgerEntry records with `calibration_epoch: 'provisional'`. Convergence detection re-reads all provisional entries and reclassifies using updated thresholds before emitting any new CONVERGED_* declarations. ~20 LOC in `ExperimentLedger.reclassify_provisional(new_thresholds)`"
2. Plan 01: add `calibration_epoch: Literal['provisional', 'calibrated'] = 'provisional'` to `ExperimentLedgerEntry`. Entries become `calibrated` only after Wave 6 re-validation passes (threshold shift <15pt)
3. Plan 12 Part 3 convergence detection: before classifying a dimension as CONVERGED_PLATEAU or CONVERGED_LOW, verify all N entries for that dimension have `calibration_epoch == 'calibrated'`. If any `provisional`, defer classification until re-validation runs
4. Add note to Plan 12 Part 0: "Wave 6 re-validation is the trigger for `reclassify_provisional()` — do not run improvement loop Part 2 until provisional entries either confirm calibration or are reclassified"
**Impacts:** Plans 01 (model field), 12 Parts 0, 2, 3
**Trigger:** P10-IMP-11
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 — Calibration epoch tracking for multi-phase validation is uncommon but the pattern (mark-then-reclassify) is standard
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

### P10-CSC-03: Tier-to-Run-Mode Binding Creates Silent Debrief Score Zeros for Pre-Binding Contracts
**Target:** CONTEXT
**What:** P10-IMP-14 (enhanced) adds a "Tier-to-Run-Mode Binding" Implementation Decision that sets Standard tier to `run_mode=headless`. The Mode Capability Matrix (already locked) marks debrief Layer 1 (SendMessage) and Layer 2 (hook gate) as UNAVAILABLE in headless. The existing 10 evaluation contracts and 4 templates were authored before this binding decision — some may declare `debrief: true` (or the equivalent in their `evaluation_config`). When Plan 08 runner applies the binding and runs Standard contracts headless, debrief collection will find no artifact, no hook gate fired, and fall through to Layer 4 (transcript analysis fallback). If Layer 4 also returns empty (which it often does for headless runs with no blocking gate), the debrief dimension scores 0. This 0 enters `ScoreCard.effective_score()` and contaminates the Standard baseline.
**Why:** The binding is correct. The problem is that existing contracts may have `debrief: true` which the runner will try to honor, producing score-poisoning zeros. The fix is an audit of existing contracts before the binding goes into effect, not after first-run failures surface the issue.
**How:**
1. Add to Tier-to-Run-Mode Binding Implementation Decision: "Contract Audit Required: Before Plan 08 implements tier-mode binding, run audit: `grep -r 'debrief: true' src/alphaswarm_sol/testing/evaluation/contracts/` and cross-reference against Standard-tier contracts. Any Standard contract with `debrief: true` must be updated to `debrief: false` before binding goes into effect. ~5 min audit, ~2 min per contract fix"
2. Plan 06 authoring guidance: "Standard-tier contracts MUST NOT declare `debrief: true`. Validator rejects Standard contracts with debrief enabled (cross-check against tier-mode binding table). ~5 LOC validator addition"
3. Plan 08 EvaluationRunner: add pre-run check — if `contract.evaluation_config.debrief == true` AND `effective_run_mode == 'headless'`, log ERROR and set `DimensionScore(name='debrief', applicable=False)` immediately (do not attempt debrief collection). ~5 LOC. Prevents score-poisoning zeros
**Impacts:** Plans 06 (validator), 08 (pre-run check), existing 10 contracts (audit + patch)
**Trigger:** P10-IMP-14
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Mode-incompatible configuration detection at startup is standard
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

### P10-CSC-04: EvaluationRunner Standalone Exit Criterion Has No Fixture Format Specification
**Target:** CONTEXT
**What:** P10-IMP-16 (enhanced) adds exit criterion to Plan 08: "EvaluationRunner runs standalone on fixture session without importing any CC skill code." This criterion is sound but immediately creates a gap: no existing item defines what a valid EvaluationRunner test fixture looks like. EvaluationRunner takes `(session_id, contract)` and reads from `.vrs/observations/{session_id}.jsonl` and `.vrs/observations/{session_id}_debrief.json`. A test fixture must provide both files. Without a fixture format specification, implementers will create a minimal fixture (empty JSONL, empty debrief JSON) that trivially satisfies the exit criterion while testing none of the parsing, pairing, or scoring logic.
**Why:** The standalone criterion was designed to enforce layer separation (EvaluationRunner does not import CC skill code). But if the fixture is trivially minimal, the exit criterion is satisfied structurally (imports are clean) without exercising any behavioral correctness. The criterion becomes a linting check, not an integration test. Plans 09-11 then inherit a runner that passed its "standalone" test on empty data.
**How:**
1. Add to Plan 08: "Fixture Session Specification: the standalone exit criterion requires a fixture session that includes: (a) JSONL with >= 5 records covering at minimum `PreToolUse`, `PostToolUse`, `SubagentStop`, and `Stop` event types, including >= 1 paired `PreToolUse`+`PostToolUse` with matching `tool_use_id`; (b) debrief JSON artifact matching `DebriefResponse` schema with >= 1 non-empty answer; (c) at least 1 BSKG query result record parseable by ObservationParser. Fixture lives at `tests/workflow_harness/fixtures/evaluation_runner/`"
2. Plan 08 exit criterion update: "EvaluationRunner produces `EvaluationResult` with non-zero `observation_summary.tool_counts`, non-null `graph_value_score`, and non-null `reasoning_assessment` on the standard fixture session"
3. Create fixture generator script `scripts/generate_evaluation_fixture.py` (~40 LOC) that produces conformant fixture JSONL + debrief JSON from a schema. Used for Plan 08 testing and future regression tests
**Impacts:** Plan 08 (exit criterion tightened, fixture spec added), Plans 09-11 (runner they inherit was tested on realistic data)
**Trigger:** P10-IMP-16
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 — Fixture specification for integration tests is standard; the gap (missing fixture format) is specific to this architecture
**Prerequisite:** no
**Status:** implemented
**Source:** Post-review synthesis (cascade)

## Post-Review Synthesis
**Items created:** P10-SYN-01, P10-SYN-02, P10-CSC-01, P10-CSC-02, P10-CSC-03, P10-CSC-04
**Key insight:** Two systemic patterns emerged: (1) data-quality signals are detected locally but never aggregated for Plan 08 to gate on, allowing contaminated sessions to silently enter the baseline — SYN-01 and SYN-02 address this by adding an `ObservationDataQuality` sub-model and a unified `SessionValidityManifest`; (2) four enhanced items (IMP-01, IMP-11, IMP-14, IMP-16) each open a downstream gap their own How section does not close — CSC-01 through CSC-04 each name the specific consumer that breaks and the concrete fix required.
