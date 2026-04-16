# Improvement Pass 6

**Pass:** 6
**Date:** 2026-02-19
**Prior passes read:** 1-5 (via IMPROVEMENT-DIGEST.md)
**Areas:** Agent Teams & Multi-Agent Testing Primacy, Transcript Pipeline & Pre-Phase Viability, Adaptive Evaluation Workflow & CC Capability Leverage
**Agents spawned:** 3 improvement + 1 research
**Status:** complete

<!-- File-level status: complete -->

## Improvements

### P6-IMP-01: Smart Selection Matrix Excludes SubagentStart/Stop from Investigation — But Investigation Agents ARE Subagents
**Target:** CONTEXT
**What:** The Smart Selection Matrix marks SubagentStart/Stop hooks as "NO" for Investigation. Investigation agents (attacker, defender, verifier) ARE subagents — SubagentStart carries `agent_type` and timestamp, the only hook signal that enables per-role attribution of tool calls in a multi-agent Investigation run. Without SubagentStart for Investigation, BSKG queries cannot be assigned to attacker vs verifier. The matrix currently has SubagentStart/Stop "YES" only for Orchestration, which already has TeamCreate/SendMessage for role attribution — the hooks are more redundant there than for Investigation. Change SubagentStart/Stop to "YES" for Investigation (keep "YES" for Orchestration). Add matrix header note: "SubagentStart carries agent_type and task_description — required for per-role analysis in multi-agent Investigation runs." Update Plan 06 investigation contract templates to include SubagentStart/Stop in `hooks` field.
**Why:** Without per-role hook attribution, Plan 04 (GVS temporal scoring) and Plan 07 (per-agent reasoning evaluation) cannot distinguish which agent produced which tool calls. The matrix fix is operationally blocked until Plan 02 delivers `obs_subagent_start.py` — this hook does not exist (see ADV-01).
**How:** (0) Plan 02 must deliver `obs_subagent_start.py` (PREREQUISITE — see ADV-01). (1) Change SubagentStart/Stop from "NO" to "YES" for Investigation. (2) Add attribution note to matrix header. (3) Plan 06 investigation contract templates gain `hooks: [PreToolUse, PostToolUse, SubagentStart, SubagentStop, Stop]`. (4) Note: "SubagentStart/Stop are passive (exit 0) — installing costs nothing. 'NO' means scoring doesn't use them, not that they're suppressed."
**Impacts:** Plan 06 (investigation contracts gain 2 hooks), Smart Selection Matrix table, Plan 02 (new hook required first)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 -- hook lifecycle events are standard in agent framework testing
**Prerequisite:** yes -- Plan 02 must deliver obs_subagent_start.py before matrix change is functional (see ADV-01)
**Status:** enhanced

**Adversarial note (Agent Teams Architecture Coherence):** The original improvement correctly identified the matrix error but missed the blocking prerequisite: `obs_subagent_start.py` does not exist in `tests/workflow_harness/hooks/`. The existing `obs_agent_stop.py` covers SubagentStop; `obs_session_start.py` covers SessionStart (top-level session), not SubagentStart (Task-spawned agent). These are distinct CC hook events. Installing a matrix entry that references a non-existent hook produces a matrix that says "YES" but delivers no data. The rewrite foregrounds this as step (0). The role-attribution value is also stronger than the original "temporal scoring" framing — SubagentStart is the definitive role-boundary marker for per-agent evaluation scoring across the full Investigation pipeline (GVS + ReasoningEvaluator + debrief).

---

### P6-IMP-02: TeamManager Is a Data Model Stub — Needs Explicit Role Decision
**Target:** CONTEXT
**What:** CONTEXT.md lists TeamManager under Infrastructure Available with `send_message()` and `get_team_observation()` as operational primitives. Inspection of `team_manager.py` confirms it is a bookkeeping layer: `create_team()` sets an env var, `spawn_teammate()` appends to a dict, `send_message()` appends to a list — no subprocess invocation. Plan 05 says "Build debrief support as TeamManager extension" implying it becomes a subprocess orchestrator. Plans 09-11 are described as pytest files at `tests/workflow_harness/test_skill_evaluation.py` — but the locked Debrief Integration Contract states Layer 1 (SendMessage) is called by "the Claude Code test orchestrator (Plans 09-11)." Python pytest files cannot call CC's SendMessage tool. This is a load-bearing architectural incoherence: pytest cannot simultaneously be the test runner AND the CC orchestrator that executes SendMessage. Path (b) is correct: TeamManager stays a data model and observation assembler. But recording this as an Implementation Decision note is insufficient — Plans 09-11 must be restructured as CC skills with thin pytest wrappers, or the "Agent Teams as primary" mandate is a slogan, not architecture.
**Why:** If Plans 09-11 remain pytest files driving CC via subprocess (headless `claude -p`), SendMessage is unavailable, debrief integration contract breaks, and interactive Agent Teams evaluation is impossible from the test suite. The note proposed by the improvement resolves TeamManager's role but leaves the pytest/CC contradiction unresolved.
**How:** (1) Add Implementation Decision: "TeamManager remains a data model and observation assembler. Real Agent Teams lifecycle (TeamCreate, spawn, SendMessage, shutdown) is managed by Claude Code test orchestrator skills (Plans 09-11). Plan 05 debrief extension means reading serialized DebriefResponse from disk, not invoking SendMessage from Python." (2) Restructure Plans 09-11: test orchestration lives in CC skills (e.g., `/vrs-test-suite`), thin pytest wrappers read structured exit reports from `.vrs/evaluations/` and assert on schema validity and score thresholds. (3) Update CONTEXT.md Location Resolution: Plans 09-11 produce skills at `src/alphaswarm_sol/shipping/skills/test-suite/`, not pytest files as primary artifacts. See ADV-02 for full elaboration.
**Impacts:** Plan 05 scope clarification, Plans 09-11 architectural restructuring (CC skills as primary, pytest as thin assertion layer), TeamManager scope stays narrow
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 -- CC execution model (skills run in CC sessions, not called from Python)
**Prerequisite:** no
**Status:** reframed

**Original framing:** "TeamManager Is a Data Model Stub — Needs Explicit Role Decision" — proposes adding an Implementation Decision note resolving TeamManager's role.

**Adversarial note (Agent Teams Architecture Coherence):** The original framing targets the right symptom (TeamManager confusion) but misses the deeper problem it exposes: the pytest-vs-CC orchestration contradiction. Adding a note that says "Plans 09-11 gain explicit subprocess responsibility" does not resolve the contradiction — subprocess (headless) means no SendMessage, which breaks the debrief integration contract. The reframe shows the decision has two parts: (a) TeamManager stays data model (correct, accept), AND (b) Plans 09-11 must become CC skills with thin pytest wrappers (the structural implication the original framing avoided). Without (b), Path b is documented but not implemented. ADV-02 provides the full structural elaboration.

---

### P6-IMP-03: Sequential Execution Constraint Makes Full Suite Take 9-17 Hours
**Target:** CONTEXT
**What:** Agent Teams cannot spawn from subagents. Sequential execution of all 51 workflows is expensive. The improvement proposes using headless `claude --print` for Standard tier (26 workflows) to enable parallel execution, while Core/Important remain interactive. The wall-clock math in the proposal is also incomplete: it counts only workflow time, not evaluation time (dual-Opus sequential adds ~15min per Core workflow on top of the ~20min workflow = ~600min for Core alone, not 200min).
**Why:** Using headless for Standard tier makes headless the DEFAULT evaluation mode for 51% of the suite by workflow count. CONTEXT.md states "Primary realism: interactive Claude Code Agent Teams" and "Cost is NOT a constraint. All tiers get Opus evaluation." The headless proposal is not a secondary mode — it becomes primary by volume. The real problem is regression cadence, not architecture.
**How:** (1) Add wall-clock estimates to Plans 09-11 with corrected math (workflow time + evaluation time + debrief time for each tier). (2) Define two run cadences: "fast regression" = Core-only (~10 workflows, run-on-commit or daily), "full suite" = all 51 workflows (weekly or release-gated). Standard tier is NOT evaluated on every regression run. (3) If Standard tier genuinely needs a faster mode, classify it explicitly as "structural validation only" (capability contract pass/fail, no reasoning depth, no debrief) with a mode label that prevents comparison to interactive scores. (4) IMP-06 (Mode Capability Matrix) MUST be implemented before any headless-for-Standard decision — without it, headless scores enter the baseline without run_mode keying, causing false positives on regression detection when a workflow transitions from headless to interactive evaluation.
**Impacts:** Plans 09-11 (execution mode per tier, corrected wall-clock estimates), Plan 12 (regression cadence: fast/full), Testing Tiers table (note that Standard uses structural validation only in fast regression)
**Research needed:** no -- GAP-11 RESOLVED: YES, hooks fire in `--print` mode (PreToolUse, PostToolUse, Stop, SubagentStart/Stop, SessionStart, PreCompact). PermissionRequest does NOT fire. All observation hooks are viable in headless. Headless confirmed viable for structural validation.
**Confidence:** MEDIUM
**Prior art:** 2 -- no established pattern for mixing interactive and headless evaluation tiers
**Prerequisite:** yes -- IMP-06 (Mode Capability Matrix) must be implemented before headless-for-Standard is adopted, to prevent apples-to-oranges baseline contamination
**Status:** reframed

**Original framing:** "Sequential Execution Constraint Makes Full Suite Take 9-17 Hours" — proposes headless `claude --print` for Standard tier as the parallelism solution.

**Adversarial note (Agent Teams Architecture Coherence):** The headless-for-Standard proposal directly conflicts with "Agent Teams first" and "ALL tiers get reasoning evaluation." Using headless for 26 of 51 workflows (51% by count) makes headless the statistical majority execution mode. The phase mandate is diluted structurally, not just in spirit. The real fix is cadence design: a fast-regression pass (Core only) handles commit-level feedback; the full suite runs less frequently. This keeps Agent Teams primary everywhere without the architectural erosion. The wall-clock estimate error is also material: Core at 20min workflow + 30min evaluation + 15min debrief = 65min/workflow x 10 = 10.8 hours for Core alone. The original 9-hour estimate for ALL 51 was already underestimated for Core. IMP-06 is flagged as a hard prerequisite: without mode-keyed baselines, headless scores are silently polluted into interactive regression windows.

---

### P6-IMP-04: Debrief Integration Contract Creates Untested LLM-to-Disk JSON Handoff
**Target:** CONTEXT
**What:** The orchestrator must serialize `DebriefResponse` to JSON on disk for Python to read. LLM-generated JSON is non-deterministic: slightly different field names, markdown fences, schema variants. The runner encounters parse failures and silently falls to Layer 3 (transcript analysis) with no error signal.
**Why:** The most critical debrief step — structured data serialization — is delegated to a prompt-driven orchestrator with no validation. Silent fallback erodes the Agent Teams primacy mandate.
**How:** (1) Add `DebriefResponseValidator` to Plan 05 (~20 LOC Pydantic/JSON Schema). On failure, log WARNING with violation details, fall to Layer 3 with explicit "artifact malformed" signal. (2) Add concrete JSON example to test orchestrator skill template (LLMs reproduce examples more reliably than schemas). (3) Update HITL scenario 05: "Verify debrief artifact passes schema validation."
**Impacts:** Plan 05 (+20 LOC validator), Plans 09-11 skill templates, HITL 05
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 -- JSON validation for LLM artifacts is established; novel piece is the LLM-writes-to-disk-for-Python handoff
**Prerequisite:** no
**Status:** enhanced

**Adversarial note (Agent Teams Architecture Coherence):** This improvement withstands scrutiny under the Agent Teams lens. The `debrief_protocol.py` code confirms the problem path: `_extract_debrief_from_observations` already returns `answers: []` for hook_gate results (Known Code Issue: Debrief Confidence Mislabeling), and `attempt_send_message_layer` currently returns `success=False` with "Live agent debrief not yet implemented." When real Layer 1 fires via CC skill, the JSON artifact on disk is the sole data path to Python — validation is essential, not optional. Cross-conflict: IMP-07 (agent-side debrief contract) must define what "structurally valid" debrief content looks like before IMP-04's validator can enforce it meaningfully. A validator that accepts structurally-sound but semantically-empty debrief JSON provides false confidence. Ordering dependency: IMP-07's debrief prompt template and structured response format must be defined before IMP-04's `DebriefResponseValidator` schema is finalized.

**Adversarial note (CC Capability Integration Justification):** Original How treated a ~20 LOC Pydantic validator as the core deliverable, but the real leverage is in the skill prompt example — prevention beats detection. The rewrite separates the two failure modes (malformed JSON vs schema mismatch), clarifies that `DebriefResponse` is already a Pydantic model in `debrief_protocol.py` so the validator is specifically the pre-parse fence-stripping step, and adds a `layer_used="send_message_malformed"` signal so the improvement loop can distinguish silent Layer 1 skip from Layer 1 execution that produced garbage. Two concrete additions to the original How: (1) embed a concrete worked JSON example of `DebriefResponse` in the orchestrator skill template — this is the primary prevention mechanism, not the validator; (2) extend `LAYER_NAMES` tuple at `debrief_protocol.py:64` from `("send_message", "hook_gate", "transcript_analysis", "skip")` to include `"send_message_malformed"` or exhaustiveness checks will fail at runtime. The HITL scenario 05 check should be made concrete: "check `.vrs/observations/{session_id}_debrief.json` contains all required fields without markdown fences" rather than just "passes schema validation."

---

### P6-IMP-05: Interactive Debrief Marked "YES" for Orchestration but "NO" for Investigation — Inverts the Value
**Target:** CONTEXT
**What:** Investigation agents (attacker, defender, verifier) would benefit from interactive debrief in principle — "Why that query? What alternatives?" would produce the self-describing failure narratives in Reasoning Evaluation Deep Dive. However, adding interactive debrief to Investigation based on this intuition conflicts with a documented constraint: "Compaction destroys structured context — keep debrief questions concise." Investigation agents run longest (BSKG queries, code reading, multi-step hypothesis chains) and are most likely to have undergone compaction before debrief fires. Post-compaction agents retain compressed summaries, not full reasoning traces. "Why that specific query on line 47?" is unanswerable after compaction. Orchestration debrief questions are coordination-level ("How did you route the task?") — answerable from compressed summary because they are structural.
**Why:** The value inversion claim rests on an assumption (investigation agents retain rich post-task reasoning memory) that the compaction constraint directly contradicts. Implementing interactive debrief for Investigation before validating compaction survival would add substantial Plan 05 scope that may be rendered moot when compaction destroys the answers.
**How:** (1) Do NOT change the matrix until compaction boundary data exists. (2) Extend Prestep P2 "Quick debrief viability pilot" to target a long-running investigation agent specifically (>10min session to force compaction likelihood). Measure: what reasoning trace survives? Can the agent answer "Why that query?" with specific evidence, or only generic summaries? (3) If P2 pilot shows >70% of specific reasoning questions are answered with verifiable transcript citations, then add `debrief_mode: "none" | "standard" | "interactive"` to contracts and enable interactive for Core investigation agents. (4) If P2 pilot shows compaction destroys specificity, keep Investigation at blocking debrief (Layer 1 structural confirmation) without interactive follow-up.
**Impacts:** Prestep P2 (extended scope to test investigation agent compaction boundary), Plan 05 and matrix change deferred pending P2 results
**Research needed:** no -- GAP-13 RESOLVED: Compaction DESTROYS specific reasoning traces. Post-compaction agents retain structural summaries but lose epistemic specifics. IMP-05 deferral is correct. Recommended: use PreCompact hook to set `compacted: bool` flag, select debrief question depth accordingly (structural-only for compacted, detailed for non-compacted).
**Confidence:** MEDIUM
**Prior art:** 1 -- Multi-turn agent debrief for evaluation is novel in LLM testing
**Prerequisite:** yes -- Prestep P2 viability pilot must complete with investigation-specific data before matrix inversion is adopted
**Status:** reframed

**Original framing:** "Interactive Debrief Marked 'YES' for Orchestration but 'NO' for Investigation — Inverts the Value" — proposes switching interactive debrief from Orchestration to Investigation based on the intuition that investigation agents have richer reasoning to debrief.

**Adversarial note (Agent Teams Architecture Coherence):** The inversion intuition is directionally appealing but is built on wishful thinking. The key undocumented assumption: investigation agents still have their full reasoning context available when debrief fires. The existing Debrief Strategy section of CONTEXT.md contradicts this: "Compaction destroys structured context." Investigation agents are the highest compaction risk due to session length. The reframe makes this a research question (Prestep P2) rather than an immediate architectural change, protecting Plan 05 scope from being spent on interactive debrief infrastructure that compaction may render useless. Orchestration debrief is NOT wrong — coordination pattern recall survives compaction better than specific epistemic trace recall. The matrix should stay until P2 data exists.

---

### P6-IMP-06: Primary/Secondary Mode Distinction Lacks Mode Capability Matrix
**Target:** CONTEXT
**What:** Design says "Primary: interactive Agent Teams, Secondary: headless" but never specifies which evaluation dimensions are unavailable in headless mode. Scoring treats both identically — same contracts, dimensions, weights. Add a Mode Capability Matrix as a locked Implementation Decision (not discretionary prose): rows=evaluation dimensions (debrief Layer 1 SendMessage, debrief Layer 2 hook gate, hook-based GVS, interactive follow-up, message flow scoring), columns=run_mode values from DC-1 (simulated / headless / interactive). Each cell: AVAILABLE | UNAVAILABLE | PARTIAL. Plan 08 runner uses `run_mode` from `EvaluationResult` to filter N/A dimensions BEFORE computing `ScoreCard.overall_score`. Plan 12 baseline is keyed by `(workflow_id, run_mode)` — regression detection never compares headless baseline to interactive result. Exit gates 3-5 annotated: "Requires `run_mode == 'interactive'` for Core tier."
**Why:** Without this matrix, headless scores (which lack debrief) are numerically compared to interactive scores in BaselineManager. A headless score of 85 and an interactive score of 72 (where debrief revealed pattern-matching not reasoning) are treated as equivalent data points. Regression detection will produce noise. Teams will drift toward headless for speed without understanding the signal degradation.
**How:** (1) Add Mode Capability Matrix table to Implementation Decisions as locked constraint — not left to Claude's discretion. (2) Plan 08 runner applies mode-aware dimension filtering using `run_mode` field (DC-1 mandates this field already exists). (3) Plan 12 BaselineManager key becomes `(workflow_id, run_mode)` tuple. (4) Exit gates 3-5 gain explicit `run_mode == 'interactive'` annotation for Core tier. (5) This matrix is a PREREQUISITE for IMP-03's headless-for-Standard proposal — cannot adopt headless tier without knowing what it loses.
**Impacts:** Plan 08 (mode-aware dimension filtering), Plan 12 (per-mode baseline keying), Exit gates 3-5 (interactive requirement for Core), IMP-03 (blocked on this until matrix exists)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 -- separating dimensions by instrumentation is standard (unit vs integration coverage)
**Prerequisite:** no
**Status:** enhanced

**Adversarial note (Agent Teams Architecture Coherence):** The original improvement is correct but understated. Framing it as "document which dimensions are unavailable" misses the enforcement angle: without the matrix as a locked Implementation Decision, it is advisory and will be ignored under schedule pressure. The enhancement elevates it to a structural constraint that Plan 08 must enforce at scoring time (mode-aware filtering) and Plan 12 must enforce at baseline-keying time. The cross-dependency with IMP-03 is also explicit: IMP-03 cannot safely adopt headless-for-Standard without this matrix in place, because headless scores will contaminate interactive baselines in BaselineManager. IMP-06 is therefore a prerequisite for IMP-03, not just a related improvement.

---

### P6-IMP-07: Blocking Debrief Has No Agent-Side Contract
**Target:** CONTEXT
**What:** Smart Selection Matrix marks "Blocking debrief: YES" for Investigation. The debrief cascade specifies how the orchestrator collects data, but no shipped agent spec includes debrief behavior instructions. Investigation agents (~5,135 lines of prose across vrs-attacker, vrs-defender, vrs-verifier) will respond conversationally to debrief questions — variable structure, no confidence fields, no key-uncertainties list — and the `DebriefResponseValidator` (IMP-04) will fail to parse. However, adding debrief behavior to shipped agent specs modifies production behavior: these agents receive SendMessage in real audit sessions. Any debrief instruction added to the agent spec will fire when a real audit orchestrator sends a message, potentially injecting structured debrief JSON into a live audit conversation. The agent-side contract must include isolation to prevent this.
**Why:** SendMessage wakes an idle agent but does not guarantee structured responses. The specific debrief response format required by `DebriefResponse` (layer_used, questions, answers, confidence) will never be produced by an agent instructed only to "respond to debrief questions." Two research questions block safe implementation: (Q1) Does the agent retain enough reasoning trace after compaction to answer specific debrief questions? (Q2) How do you isolate debrief behavior to evaluation sessions without modifying production agent prompts per-run?
**How:** (1) Plan 05: add debrief prompt template for investigation agents specifying: structured answer format matching DebriefResponse schema, confidence per answer (0.0-1.0), key-uncertainties list. (2) Debrief isolation via SubagentStart hook context injection (GAP-14 resolved): evaluation runner creates `.vrs/evaluation_mode` marker file; a SubagentStart hook checks for the marker and injects debrief instructions via `additionalContext`. NO shipped agent spec modification needed — zero production contamination risk. (3) Plan 06: Core contracts include `debrief_prompt` field. (4) Prestep P4: extend from "verify agent wakes" to "verify agent responds with parseable structured data" AND "verify debrief behavior does not fire in non-evaluation sessions (marker file absent)." (5) Add PreCompact hook to set `compacted: bool` flag; select debrief question depth accordingly (structural-only for compacted agents, detailed for non-compacted).
**Impacts:** Plan 05 (debrief template + isolation sentinel design), Plan 06 (debrief_prompt field in Core contracts), Prestep P4 (extended verification), shipped agent specs (conditional debrief section — careful production impact analysis required)
**Research needed:** no -- GAP-14 RESOLVED: (Q1) Idle agents have full context IF no compaction; compressed only if compacted. Observable via PreCompact hook flag. (Q2) Use SubagentStart hook `additionalContext` injection — evaluation runner creates `.vrs/evaluation_mode` marker file, SubagentStart hook checks for it before injecting debrief instructions. NO shipped agent spec modification needed. Zero production contamination risk.
**Confidence:** MEDIUM
**Prior art:** 2 -- Structured self-assessment prompts exist in LLM evaluation, but for idle post-task CC agents is novel
**Prerequisite:** yes -- Prestep P4 must verify structured response quality AND isolation, not just wake-and-respond. IMP-04's DebriefResponseValidator schema must be finalized first (ordering dependency: schema before template, template before validator).
**Status:** enhanced

**Adversarial note (Agent Teams Architecture Coherence):** The original improvement correctly identified the missing agent-side contract but missed the production contamination risk. Adding debrief behavior to shipped agent specs is not scoped to evaluation — these specs define how agents behave in all contexts. A real audit orchestrator that sends a SendMessage (for coordination, not evaluation) to an agent with debrief instructions will receive structured debrief JSON instead of coordination content, breaking the live audit session. The isolation sentinel (environment variable or marker file checked by the agent at debrief-question receipt) is the minimum viable guard. The two research questions are both elevated: Q1 (compaction survival) is shared with IMP-05, and Q2 (evaluation isolation) is a new risk identified here. Both must be answered by Prestep P4 before Plan 05 proceeds with agent spec modification.

---

### P6-IMP-08: P0 Must Become Hard Gate With Exit Criteria — Pre-Phase Not Needed
**Target:** CONTEXT
**What:** Prestep P0 says "Capture 3-5 transcripts" with no exit criteria, no failure protocol, no timeline. It only blocks "evaluation contract authoring" per section header. Meanwhile, Plans 03-12 all depend on assumptions about JSONL structure that are UNVERIFIED. The user asked "create a pre-phase?" — answer: no. The work fits within Plan 02. A separate phase adds bureaucratic overhead without safety.
**Why:** A vague prestep provides zero protection. If P0 has no exit criteria, it gets declared "good enough" after one transcript. The 12-plan pipeline depends on assumptions that could be wrong. A hard gate prevents skipping.
**How:** (1) Replace P0 text with concrete exit criteria: (a) 3+ real transcripts from distinct workflow categories (investigation, orchestration, tool-integration), (b) TranscriptParser.get_tool_calls() returns >0 on all 3, (c) ObservationParser.parse() returns parse_errors==0 on 1+ hooked session, (d) Document structural surprises as Known Code Issues. (2) Failure protocol: if TranscriptParser fails, STOP 3.1c execution. (3) Add P0 blocking dependency to Plans 03-12. (4) Add Plan 02 exit criteria: "Delivered 3+ real transcripts to tests/workflow_harness/fixtures/real_sessions/". (5) Do NOT create a separate pre-phase.
**Impacts:** Plans 03-12 gain hard dependency on P0. Plan 02 gains deliverable.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 -- standard quality gate pattern
**Prerequisite:** no
**Status:** open

---

### P6-IMP-09: Hooks Do Not Capture tool_use_id Despite CONTEXT.md Requiring It
**Target:** CONTEXT
**What:** Plan 02 says "Capture `tool_use_id` from hook payloads." Plan 03 says "Replace LIFO with `tool_use_id`-based pairing." But grep confirms ZERO occurrences of `tool_use_id` in hooks directory. The LIFO pairing at observation_parser.py:161 is the only mechanism. CONTEXT.md frames this as "remaining scope" when it is entirely unaddressed.
**Why:** LIFO breaks on parallel tool calls (routine CC behavior). 3 parallel Reads → first result pairs with third Read (most recent), not first. All subsequent pairing is wrong. Cascades into wrong timing, wrong result attribution, wrong evaluation scores.
**How:** (1) Add Known Code Issue: "Hooks receive tool_use_id in input (confirmed by official CC docs — GAP-12 resolved) but obs_tool_use.py and obs_tool_result.py do not EXTRACT it from input_data. This is a ~2 LOC fix per hook, not a missing-field infrastructure problem. Pairing remains LIFO-broken until extraction is added." (2) Change Plan 02 text from "Capture `tool_use_id`" to "CRITICAL: Extract `tool_use_id` from hook input_data (~2 LOC per hook). Without this, Plan 03 pairing fix is impossible." (3) Make tool_use_id extraction a hard Plan 02 exit criterion. (4) Note: CC fires ONE PreToolUse per tool_use, no batching — each parallel call gets its own hook invocation (GAP-12 confirmed).
**Impacts:** Plan 02 (hard exit criterion), Plan 03 (blocked on Plan 02 delivery)
**Research needed:** no -- GAP-10 already confirmed the field exists in hook payloads
**Confidence:** HIGH
**Prior art:** 5 -- standard field extraction from JSON
**Prerequisite:** no
**Status:** open

---

### P6-IMP-10: ObservationWriter Fix Is Correct Architecture But Underspecified
**Target:** CONTEXT
**What:** CONTEXT.md correctly identifies `threading.Lock()` → `fcntl.flock()`. But underspecified: (a) advisory locks are sufficient because all writers cooperate (must document), (b) Windows: `fcntl` doesn't exist → hooks crash on import, (c) lock timeout: if held too long, hook killed mid-write corrupting JSONL.
**Why:** Shared-file with flock IS correct (per-hook files worse: lose ordering, require merge step). But implementation needs: non-blocking with retry (`LOCK_EX | LOCK_NB`), platform detection (`try: import fcntl` / `except ImportError`), complete line before releasing lock.
**How:** Expand Plan 02 ObservationWriter spec: (1) `fcntl.flock(f.fileno(), LOCK_EX)` with file handle, (2) platform guard via try/except ImportError → fall back to threading.Lock with warning, (3) document advisory locks sufficient because cooperative.
**Impacts:** Plan 02 implementation detail
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 -- fcntl.flock is well-documented POSIX pattern
**Prerequisite:** no
**Status:** open

---

### P6-IMP-11: TranscriptParser and ObservationParser Are Conflated in Plan 03
**Target:** CONTEXT
**What:** Plan 03 says "Extends TranscriptParser" but ObservationParser does NOT extend it. They parse fundamentally different JSONL: TranscriptParser reads CC native transcripts (user/assistant/progress records); ObservationParser reads hook-generated JSONL ({timestamp, session_id, event_type, hook_name, data}). Different schemas, producers, consumers.
**Why:** An implementer reading "Extends TranscriptParser" will try impossible inheritance. The two parsers should remain separate.
**How:** Change Plan 03 text to: "Parallel parser for hook-generated observation data. Does NOT extend TranscriptParser — different data source and schema." Add data flow note: "TranscriptParser reads CC native JSONL. ObservationParser reads hook-generated JSONL. Both feed CollectedOutput via different paths."
**Impacts:** Plan 03 clarity. No structural change.
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 -- documentation correction
**Prerequisite:** no
**Status:** open

---

### P6-IMP-12: Concrete Failure Scenario — Parallel Tool Calls Corrupt Observation Pairing
**Target:** CONTEXT
**What:** When CC makes 3 parallel Reads, LIFO pairing assigns Result-A to Read-C (wrong), silently drops Result-B, cascades wrong data into GVS citation rates and evaluation scores. This is not hypothetical — CC routinely makes parallel calls.
**Why:** Strengthens urgency of P6-IMP-09. The failure is the default behavior for any real session, not a corner case.
**How:** Add this scenario to Known Code Issues. Ensure Plan 02 exit criteria include: "Validated pairing correctness on a real session with >= 2 parallel tool calls."
**Impacts:** Plans 03, 04, 07, 08 all consume paired data
**Research needed:** no -- GAP-12 RESOLVED: CC fires ONE PreToolUse per tool_use, no batching. Each parallel call gets its own hook invocation. Interleaving between tool_use and tool_result events from concurrent calls is the norm.
**Confidence:** HIGH
**Prior art:** 5 -- well-understood race condition
**Prerequisite:** no
**Status:** open

---

### P6-IMP-13: Evaluator-as-Skill — Replace Python Runner with Skill-Dispatched Evaluation
**Target:** CONTEXT
**What:** Plan 07 defines `ReasoningEvaluator` as a Python class calling CC via Task tool. Plan 08 defines a Python `EvaluationRunner` calling it. This is Python-orchestrates-CC. Invert: make evaluation a skill `/vrs-evaluate` that CC dispatches natively. The Python runner becomes a thin `claude -p` caller.
**Why:** A skill-based evaluator gets: (1) native CC tool access without subprocess marshalling, (2) SendMessage for evaluator debate, (3) skill composition (`/vrs-evaluate` can call other skills), (4) evaluation becomes self-testable by the framework. The dual-Opus approach requires two sequential Task spawns; a skill does the same with less plumbing.
**How:** (1) Create `src/alphaswarm_sol/shipping/skills/evaluate/SKILL.md`. (2) Modify Plan 08 runner to invoke via `claude -p --append-system-prompt-file`. (3) Keep `ReasoningEvaluator` as heuristic fallback for simulated mode.
**Impacts:** Plan 07 (architecture change), Plan 08 (thinner runner), Plans 09-11 (uniform dispatch)
**Research needed:** yes -- Does `--append-system-prompt-file` support structured JSON output reliably for full `EvaluationResult`?
**Confidence:** MEDIUM
**Prior art:** 2 -- Skill-based evaluation dispatch is novel; project has 34 skills but none self-evaluating
**Prerequisite:** no
**Status:** open

---

### P6-IMP-14: Evaluator Debate via SendMessage Instead of Dual-Independent Scoring
**Target:** CONTEXT
**What:** Plan 07 specifies "TWO independent evaluator subagents score same transcript." This is the weakest multi-evaluator design — isolated judges who never communicate. Replace with debate: Evaluator A scores, Evaluator B sees A's output and must agree/disagree with justification. Disagreements become richer meta-evaluation signal.
**Why:** Independent dual scoring wastes B's potential. When B sees A's reasoning, it catches logical errors, identifies justified-score-wrong-explanation cases, produces calibrated disagreements citing transcript evidence. This mirrors the project's own attacker/defender/verifier debate model. CC capability leveraged: SendMessage between teammate evaluators.
**How:** (1) Change dual-Opus from "independent" to "sequential with visibility." (2) Meta-evaluation becomes: count/severity of disagreements, consensus dimensions. (3) Add `EvaluatorDisagreement` model to Plan 01: dimension, A_score, B_score, B_justification, resolved_score. (4) Update meta-evaluation section.
**Impacts:** Plan 07 (debate protocol), Plan 01 (new model), Plan 12 (richer metaprompting from structured disagreements)
**Research needed:** no -- SendMessage already verified (GAP-02); attacker/defender debate is existence proof
**Confidence:** HIGH
**Prior art:** 3 -- Debate evaluation established in RLHF (Irving et al. 2018). Novel: implementing via CC Agent Teams.
**Prerequisite:** no
**Status:** open

---

### P6-IMP-15: Pull 3 Intelligence Modules from v2 to v1 — They Work on Day 1
**Target:** CONTEXT
**What:** CONTEXT.md defers ALL 12 intelligence modules to v2 stubs. Three can be v1 with <200 LOC total using existing data sources:
1. `coverage_radar.py` (marked "Day 1"): Cross-reference contracts vs runs. ~100 LOC.
2. `contract_healer.py` (marked "Day 1"): Detect ceiling/floor/zero-variance scores from BaselineManager's 20-score windows. ~30 LOC.
3. `tier_manager.py` (marked "After first batch"): Promotion/demotion thresholds already specified in VISION.md. ~50 LOC on BaselineManager.
**Why:** Calling these "v2 stubs" when they activate Day 1 with <200 LOC is artificial deferral. Coverage radar during Plans 09-11 shows "10 of 51 tested, here are 41 gaps prioritized by severity." Contract healer during baseline prevents wasting improvement cycles on poorly calibrated contracts.
**How:** (1) Move these 3 from stubs to Plan 12 Part 5 with real implementations. (2) Activation thresholds: coverage_radar=immediate, contract_healer=after 5 runs, tier_manager=after 3 runs. (3) Keep remaining 9 as stubs. (4) Update exit gate 16: "At least 3 intelligence modules ACTIVE."
**Impacts:** Plan 12 scope increase (~200 LOC), Exit gate 16 strengthened
**Research needed:** no -- all use existing data sources
**Confidence:** HIGH
**Prior art:** 4 -- coverage analysis, anomaly detection, threshold management are all established
**Prerequisite:** no
**Status:** open

---

### P6-IMP-16: Hook Composition Pipeline — Derived Observations in Real Time
**Target:** CONTEXT
**What:** Currently each hook is independent. No mechanism for a hook to read another's output and produce derived observations. Concrete case: `_check_graph_first` in GVS needs to know if first Bash was `alphaswarm`. A `derived_graph_first.py` hook could compute this IN REAL TIME with full tool_input, eliminating flawed post-hoc regex.
**Why:** Some analysis is trivially computable at observation time with MORE accuracy (hook sees full command, not 500-char preview). However: CC hooks are independent processes with no ordering guarantees — "composition" means reading another hook's JSONL, introducing race conditions.
**How:** (1) Add "Derived Observation Hooks" to Plan 02. (2) Implement ONE: `derived_graph_first.py` tracking first alphaswarm Bash and first Read. (3) GVS reads this observation instead of post-hoc computation. (4) Document pattern for future derived hooks.
**Impacts:** Plan 02 (+1 hook ~40 LOC), Plan 04 (removes `_check_graph_first` post-hoc), fixes Known Code Issue
**Research needed:** yes -- Do hooks on same event type execute in deterministic order? Race condition risk.
**Confidence:** LOW
**Prior art:** 1 -- Hook composition analogous to middleware chains but CC hooks are independent processes
**Prerequisite:** yes -- Verify hook execution ordering for same-event hooks
**Status:** rejected

**Adversarial note (CC Capability Integration Justification):** Rejected for three compounding reasons. First, the problem it claims to solve already has a specified fix: Known Code Issues documents the `_check_graph_first` false-positive bug and Plan 04 specifies the fix as "filter `tool_sequence` for `alphaswarm` substrings before determining `first_bash`" (~5 LOC). A new hook mechanism is not needed to fix a 5-LOC problem. Second, the item self-declares LOW confidence and a blocking prerequisite (hook execution ordering) with no resolution path — the research question is not in the resolved gaps list and cannot be answered without real CC session data, which requires P0 to complete first. Third, "derived hooks reading other hooks' JSONL" is hook composition by side-channel: a derived hook reads from a shared append-only file that another hook may still be writing to (the `fcntl.flock` fix in IMP-10 is not yet implemented). This introduces a new class of race condition that the improvement acknowledges but does not resolve. Implementing a complex new pattern with an open race condition to replace a 5-LOC filter is not justified. The Plan 04 filter should be implemented as already specified; hook composition remains deferred until ordering is verified on real session data.

---

### P6-IMP-17: Weave Improvement Signal INTO Evaluation, Not After
**Target:** CONTEXT
**What:** Plan 12 (Wave 7) executes AFTER all tests. It re-analyzes scores to find low dimensions. Proposal: add `improvement_hints` to `EvaluationResult` that fire DURING Wave 6 scoring. When dimension scores <40, evaluator produces immediate hypothesis. Example: "QUERY_FORMULATION scored 32. Hypothesis: agent lacks 'narrow queries to <10 results' instruction."
**Why:** This front-loads diagnostics so Wave 7 starts with a prioritized hypothesis queue WITH evidence. Saves one full diagnostic pass (~30 min per dimension). The evaluator already generates failure narratives; extending to improvement hints is small scope.
**How:** (1) Add `improvement_hints: list[ImprovementHint]` to EvaluationResult (Plan 01). (2) `ImprovementHint`: dimension, score, hypothesis, suggested_change, kill_criterion, confidence. (3) Plan 07: generate hints when dimension <40. (4) Plan 12 Part 2: read pre-computed hints instead of re-analyzing.
**Impacts:** Plan 01 (new model), Plan 07 (extend failure narrative step), Plan 12 Part 2 (simplified)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 3 -- "Inline diagnostics" from CI (e.g., GitHub Actions annotations)
**Prerequisite:** no
**Status:** open

---

### P6-IMP-18: MCP Server for Evaluation Data — Queryable History
**Target:** CONTEXT
**Original framing:** "Evaluation results go to `.vrs/evaluations/` as JSON files. No programmatic access during sessions. An MCP server exposing `get_evaluation_summary`, `get_coverage_gaps`, `get_regression_report` makes evaluation data a first-class CC resource."
**What:** The improvement loop (Plan 12) needs CC to reason over aggregated evaluation history without reading dozens of JSON files individually. The right delivery mechanism is a CLI command, not an MCP server. Add `alphaswarm evaluation summary [--workflow WORKFLOW_ID] [--format json|table]` that reads `.vrs/evaluations/` and `progress.json` (see P6-ADV-04), aggregates scores, and outputs the same 4 data views the original MCP proposal offered: workflow scores, coverage report, regression alerts, improvement queue. CC calls this via Bash, the same way it already calls all other alphaswarm commands. Zero new dependencies, zero server process, zero MCP discovery configuration.
**Why:** CC already has programmatic access to any file via the Read tool and to any CLI command via the Bash tool. FastMCP is not in pyproject.toml (verified by inspection of `pyproject.toml` dependencies); adding it creates a new installation dependency for a testing-internal feature that will never ship to users. The improvement loop is human-in-the-loop, not an autonomous CC session continuously querying evaluation history — evaluation history is batch-written and read once per improvement session, exactly the use case a CLI command handles best. MCP adds value when CC needs live, reactive access to a changing data source across concurrent sessions; that is not this use case.
**How:** (1) Add `evaluation` subcommand group to the existing `alphaswarm` CLI (typer pattern already established; entry point at `src/alphaswarm_sol/cli.py`; must not touch `executor.py` or `builder_legacy.py`). (2) Implement `alphaswarm evaluation summary` (~80 LOC): reads `.vrs/evaluations/progress.json` as primary source, per-workflow JSON files as detail source; computes score trends, coverage gaps, regression alerts, improvement queue. (3) Support `--format json` and `--format table`. (4) Handle missing `.vrs/evaluations/` gracefully: "No evaluation runs found — run the test suite first." (5) Update Plan 12 improvement loop: "Query history via `alphaswarm evaluation summary --format json` before each improvement cycle." (6) Defer MCP to v2 if CLI proves insufficient after real improvement cycles.
**Impacts:** CLI module (+~80 LOC, no new deps), Plan 12 (improvement loop references CLI command), eliminates FastMCP prerequisite and both research questions
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5
**Prerequisite:** no (depends on P6-ADV-04 for full value, degrades gracefully without progress.json)
**Status:** reframed

**Adversarial note (CC Capability Integration Justification):** The MCP framing assumes "programmatic access during sessions" requires a running server process. It does not. FastMCP is not in pyproject.toml (confirmed). Adding it introduces a new installation dependency for a feature that is testing-internal and will never ship to users. The improvement self-listed two research questions (FastMCP Python version compatibility, CC MCP server discovery for local Python servers) — both eliminated by the CLI approach. The reframe preserves all four proposed data views at roughly one-quarter the LOC with zero new dependencies. The MCP pattern would be appropriate if evaluation data needed reactive cross-session access; evaluation history is batch-written and read once per human improvement session.

---

### P6-IMP-19: Notification Hooks for Long-Running Evaluation Progress
**Target:** CONTEXT
**What:** Full 51-workflow suite takes 6+ hours. Progress is logged to file. CC supports notification hooks on SubagentStop/TaskCompleted that could emit: "15/51 complete. Current: agent-vrs-defender. ETA: 4h 12m. Last score: 72/100."
**Why:** Zero-effort from runner's perspective — hooks fire on existing events. ~30 LOC leveraging existing CC capability.
**How:** (1) Add `notify_progress.py` to Plan 02 scope. (2) Triggers on TaskCompleted. (3) Reads `.vrs/evaluations/progress.json`. (4) Sends macOS notification via `osascript`.
**Impacts:** Plan 02 (+1 hook ~30 LOC), Plan 08 (writes progress.json)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 -- system notifications from build tools are standard
**Prerequisite:** no
**Status:** rejected

**Adversarial note (CC Capability Integration Justification):** Rejected as out-of-scope developer convenience that introduces platform coupling and a hidden inter-plan dependency. Four specific problems: (1) **Platform lock-in contradicts IMP-10.** IMP-10 requires an `ImportError` platform guard for `fcntl` because non-POSIX systems lack it. `osascript` is macOS-exclusive with no Linux or Windows equivalent. A testing framework improvement that only works on macOS is a local convenience, not a framework improvement. (2) **Silent Plan 08 dependency.** The hook reads `.vrs/evaluations/progress.json` which Plan 08 does not currently write. This silently adds a Plan 08 deliverable without updating Plan 08's spec. If `progress.json` does not exist, the hook exits silently — the claimed "zero-effort" value disappears. The actual deliverable needed is `progress.json` from Plan 08, captured in P6-ADV-04. (3) **Misattributed CC capability.** CC hooks are not "notification hooks" — they are observation hooks that fire on session events. Using a hook to shell out to `osascript` is running an OS command from within a hook process, identical in mechanism to calling `echo` or `wall`. The claim that this "leverages existing CC capability" conflates the trigger mechanism with the delivery mechanism. (4) **Scope category mismatch.** The improvement register for this phase targets evaluation architecture: contracts, debrief protocol, reasoning evaluator, baseline. A macOS notification convenience belongs in a developer dotfile or contributing guide, not in the 12-plan evaluation framework improvement register.

---

### P6-IMP-20: Dual-Opus Sequential Timeout Cascade — Evaluation Stage Needs Its Own Budget
**Target:** CONTEXT
**What:** Plan 07 uses dual-Opus sequentially. Plan 08 specifies per-scenario timeout (600s, Core may need 900-1800s). No document addresses EVALUATOR timeouts separately. Failure: 50KB transcript, Evaluator A takes 4 min, B takes 5 min. Workflow took 8 min. Total: 17 min but scenario timeout was 10 min. B killed mid-assessment. Baseline absorbs mixed single/dual-rater scores. Regression detection compares apples to oranges.
**Why:** CONTEXT.md specifies workflow timeouts but not evaluation-stage timeouts. This gap will bite during Core-tier runs where transcripts are longest.
**How:** (1) Add `evaluation_timeout` to contracts (default 300s standard, 600s deep). (2) Add `evaluation_complete: bool` to EvaluationResult. If B times out, result is partial. (3) BaselineManager filters: partial evaluations excluded from baseline unless opted in.
**Impacts:** Plan 01 (new field), Plan 07 (timeout handling), Plan 08 (separate budgets), Plan 12 (baseline filtering)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 4 -- timeout budgeting for multi-stage pipelines is standard
**Prerequisite:** no
**Status:** open

---

### P6-ADV-01: Missing obs_subagent_start.py Hook Blocks IMP-01 Matrix Fix
**Target:** CONTEXT
**What:** IMP-01 proposes adding SubagentStart/Stop to the Investigation row of the Smart Selection Matrix. The existing hook inventory in `tests/workflow_harness/hooks/` contains no `obs_subagent_start.py`. The existing `obs_agent_stop.py` covers SubagentStop; `obs_session_start.py` covers SessionStart (top-level session), not SubagentStart (Task-spawned agent). These are distinct CC hook events. The matrix fix is operationally meaningless until this hook exists — the matrix says "YES" for SubagentStart/Investigation but the evaluation pipeline receives no data.
**Why:** The Smart Selection Matrix drives hook installation in pre-session setup (locked Implementation Decision). If investigation contracts list SubagentStart but no hook captures it, the evaluator sees a matrix entry marked "YES" with no corresponding JSONL data. This is the same failure mode as the debrief gate stubs: nominal compliance, zero function. SubagentStart also carries `agent_type` and `task_description` — without capturing these fields, per-role tool call attribution is impossible for multi-agent Investigation runs (attacker vs verifier cannot be distinguished in the GVS or ReasoningEvaluator).
**How:** (1) Plan 02 scope must explicitly add `obs_subagent_start.py` capturing: timestamp, agent_id, agent_type, task_description, parent_session_id. (~40 LOC, matches structure of obs_agent_stop.py). (2) CONTEXT.md Known Code Issues: "SubagentStart hook missing — obs_subagent_start.py does not exist. IMP-01 matrix change is blocked on Plan 02 delivery." (3) IMP-01 How section: add "(0) Plan 02 must deliver obs_subagent_start.py as prerequisite." (4) Contract template-investigation.yaml update (hooks field) is conditional on Plan 02 delivery.
**Impacts:** Plan 02 (new hook ~40 LOC), IMP-01 (gains prerequisite dependency), investigation contracts
**Research needed:** no
**Confidence:** HIGH
**Prerequisite:** yes -- Plan 02 must deliver obs_subagent_start.py before the matrix change is functional
**Status:** open

**Source:** Adversarial review (Agent Teams Architecture Coherence)
**Adversarial note (Agent Teams Architecture Coherence):** Discovered while verifying IMP-01's claim that "installing costs nothing." The cost is not CPU — it is the absence of the hook script itself. Scanning `tests/workflow_harness/hooks/` confirms: obs_tool_use.py, obs_tool_result.py, obs_bskg_query.py, obs_message.py, obs_session_start.py, obs_agent_stop.py, debrief_gate.py, debrief_task_complete.py. No obs_subagent_start.py. The existing obs_session_start.py is a SessionStart hook (top-level CC session initialization event), not a SubagentStart hook (fires when an agent is Task-spawned). They are different events in CC's hook system. IMP-01's matrix change creates a false signal of coverage without this prerequisite.

---

### P6-ADV-02: Plans 09-11 Architectural Conflict — Pytest Cannot Drive Agent Teams Lifecycle
**Target:** CONTEXT
**What:** CONTEXT.md locates Plans 09-11 at `tests/workflow_harness/test_skill_evaluation.py`, `test_agent_evaluation.py`, `test_orchestrator_evaluation.py` — standard pytest files. The locked Execution Model states "ALL evaluation runs through Claude Code subagents (Task tool with prompt). NEVER direct Anthropic API calls." The locked Debrief Integration Contract states "Layer 1 (SendMessage) is called by the Claude Code test orchestrator (Plans 09-11)." Pytest files cannot call CC's SendMessage tool — that is a CC native tool available only within a Claude Code session. Python has no SendMessage API. Plans 09-11 cannot simultaneously be pytest files AND the entity that calls SendMessage. If Plans 09-11 drive CC via subprocess (`claude -p` / headless), SendMessage is unavailable, the debrief integration contract breaks, and interactive Agent Teams evaluation is structurally impossible from the test suite.
**Why:** This is a load-bearing architectural contradiction that makes "Agent Teams as primary" impossible to satisfy if Plans 09-11 remain pytest files. It will surface as a Wave 6 blocker after Plans 01-08 are implemented. The contradiction is between three locked decisions: (1) Execution Model (CC subagents only), (2) Debrief Integration Contract (Plans 09-11 call SendMessage), and (3) CONTEXT.md locating Plans 09-11 as pytest files. All three cannot be simultaneously true.
**How:** (1) Restructure Plans 09-11: the primary artifact is a CC skill (e.g., `/vrs-test-suite`) that orchestrates real Agent Teams workflows, calls SendMessage for debrief, and writes structured YAML/JSON exit reports to `.vrs/evaluations/`. (2) The pytest files at `tests/workflow_harness/test_skill_evaluation.py` et al. become thin wrappers that invoke `claude -p skill:vrs-test-suite` and assert on the structured exit report (schema validity, score thresholds, gate conditions). (3) Update CONTEXT.md Location Resolution table: Plans 09-11 primary artifact is `src/alphaswarm_sol/shipping/skills/test-suite/`. (4) Exit gate passage is redefined: "CC skill `/vrs-test-suite` writes a conformant exit report" replaces "pytest suite passes."
**Impacts:** Plans 09-11 (architectural redesign — CC skills as primary, pytest as thin assertion layer), CONTEXT.md Location Resolution table, Exit gates (gate passage criteria updated), Wave 6 execution plan
**Research needed:** yes -- Can a CC skill write machine-readable YAML/JSON exit reports that pytest can assert on without parsing transcript text? What is the interface contract between the CC skill exit artifact and the pytest assertion layer?
**Confidence:** HIGH
**Prerequisite:** yes -- IMP-02's TeamManager role decision must be recorded as an Implementation Decision first (ADV-02 is the structural implication of Path b from IMP-02; both must land together)
**Status:** open

**Source:** Adversarial review (Agent Teams Architecture Coherence)
**Adversarial note (Agent Teams Architecture Coherence):** Discovered by cross-examining IMP-02's resolution (Path b: "Plans 09-11 gain explicit subprocess responsibility") against the Debrief Integration Contract ("Layer 1 is called by the Claude Code test orchestrator (Plans 09-11)"). Subprocess = headless = no SendMessage = debrief layer 1 never fires from Plans 09-11. The contradiction is not theoretical — it determines whether the debrief architecture works at all. IMP-02 records the resolution as a note; ADV-02 supplies the structural consequence that note implies. Both must be adopted together or the contradiction persists.

---

## Adversarial Review: Agent Teams Architecture Coherence
**Items reviewed:** 6 (P6-IMP-01, P6-IMP-02, P6-IMP-03, P6-IMP-05, P6-IMP-06, P6-IMP-07)
**Verdicts:** ENHANCED: 3 (IMP-01, IMP-06, IMP-07), REFRAMED: 3 (IMP-02, IMP-03, IMP-05), CONFIRMED: 1 (IMP-04, cross-conflict check only), CREATE: 2 (ADV-01, ADV-02)
**Cross-group conflicts:**
- IMP-03 (headless for Standard tier) directly conflicts with the phase domain mandate ("ALL tiers get reasoning evaluation") and with IMP-06 (mode capability matrix must exist before headless tier decisions). IMP-06 is a prerequisite for IMP-03.
- IMP-05 (interactive debrief for Investigation) conflicts with the compaction constraint documented in CONTEXT.md Debrief Strategy. The assumption that investigation agents retain full reasoning trace post-compaction is contradicted by the same document that motivated the debrief design.
- IMP-07 (agent-side debrief contract) modifying shipped agent specs creates a production contamination risk: debrief behavior fires in real audit sessions when any SendMessage arrives. This interaction is unaddressed by IMP-07 and creates a conflict with the production audit use case.
- IMP-04 (debrief JSON validation, in other_improvements group) depends on IMP-07 defining the structured response format. IMP-04's validator cannot be finalized before IMP-07's debrief prompt template and schema are specified.
- P6-ADV-02 (Plans 09-11 architectural conflict) affects the other_improvements group: IMP-04 (debrief JSON validation) assumes the CC orchestrator skill writes a valid DebriefResponse artifact. If Plans 09-11 remain pytest files driving headless CC, SendMessage never fires and IMP-04's validator is never reached. IMP-04's value is contingent on ADV-02 being resolved first.
**Second-order risks:**
1. If IMP-01 is applied without ADV-01 (missing obs_subagent_start.py), investigation contracts list a hook that generates no data, causing silent per-role attribution failures in GVS and ReasoningEvaluator that accumulate into a corrupted baseline where all tool calls appear unattributed.
2. If IMP-02 is applied as a documentation note only — without restructuring Plans 09-11 as CC skills — the pytest/SendMessage contradiction (ADV-02) persists and will surface as a Wave 6 blocker after Plans 01-08 implementation effort is complete and irreversible.
3. If IMP-03 is applied before IMP-06, Standard-tier headless scores enter BaselineManager without run_mode keying. First regression detection run comparing headless baseline to interactive result will produce systematic false positives for all debrief-dependent dimensions.
4. If IMP-05 is applied (interactive debrief for Investigation) before Prestep P2 compaction viability test, Plan 05 implementation effort for multi-turn interactive debrief may be rendered moot when real investigation agent sessions reveal post-compaction context loss. The investigation agents are the highest compaction risk by session length.
5. If IMP-07 adds debrief behavior to shipped agent specs without isolation sentinels (environment variable or marker file checked at debrief-question receipt), real audit orchestrators sending any SendMessage to a debriefed agent will receive structured JSON debrief responses instead of coordination content, breaking live audit sessions.

---

### P6-IMP-13: Evaluator-as-Skill (Updated by Adversarial Review)
**Status:** reframed

**Original framing:** "Plan 07 defines `ReasoningEvaluator` as a Python class calling CC via Task tool. Plan 08 defines a Python `EvaluationRunner` calling it. This is Python-orchestrates-CC. Invert: make evaluation a skill `/vrs-evaluate` that CC dispatches natively. The Python runner becomes a thin `claude -p` caller."

**Reframed What:** The evaluator's weakness is not its Python shell — it is the absence of a real LLM call path and calibration data. The correct improvement is: keep `ReasoningEvaluator` as a Python class but activate the proven `claude -p --json-schema` call path (GAP-01 resolved). The Python runner stays intact. The `/vrs-evaluate` skill wrapper is dropped as premature indirection that solves the wrong problem.
**Why (reframed):** The proposed inversion adds a marshalling layer (Python → `claude -p` → skill → subagent) without addressing the root problem: `reasoning_evaluator.py:505-560` `_check_model_capability` matches description keywords against observation text, producing scores like 45 regardless of whether the agent actually reasoned well. A Python class calling `claude -p --json-schema` directly (GAP-01 resolved) achieves identical CC access with less overhead and preserves the existing `EvaluationPlugin` protocol. "Skill composition" benefit is speculative — no shipped skill currently calls another skill. "Self-testable" benefit creates a bootstrapping paradox: the framework must evaluate its own evaluation skill before calibration exists. The `--append-system-prompt-file` reliability for full `EvaluationResult` JSON output is explicitly marked `research_needed: yes` — this disqualifies the MEDIUM confidence claim on the core mechanism.
**How (reframed):** (1) In Plan 07, implement `ReasoningEvaluator._llm_evaluate_dimension()` that calls `claude -p --output-format json --json-schema <DimensionScore.schema>` using `REASONING_PROMPT_TEMPLATE` already present in `reasoning_evaluator.py:40-55`. This is ~30 LOC, confirmed viable per GAP-01. (2) Keep the Python `EvaluationRunner` as-is. (3) Drop the `/vrs-evaluate` skill proposal. (4) If skill composition is desired post-calibration, extract after the evaluator is proven on real data.
**Impacts (reframed):** Plan 07 (add real LLM call path to existing Python class), no architectural change to Plans 08-11
**Research needed:** no — GAP-01 confirmed `claude -p --json-schema` works
**Confidence:** HIGH (reframe)

**Adversarial note (Evaluation Innovation Viability):** The original improvement solves the wrong problem. Confirmed by reading `reasoning_evaluator.py:505-560`: `_check_model_capability` keyword-matches description text against observations, producing scores detached from actual reasoning quality. Moving this logic into a skill prompt does not fix it — it relocates it. The reframe targets the actual gap: replace the keyword heuristic with a real `claude -p --json-schema` LLM call using the prompt template already written. GAP-01 is resolved and confirms this mechanism works. The `research_needed: yes` on `--append-system-prompt-file` in the original is a self-disqualifier that the improvement's own confidence rating of MEDIUM ignores. Second-order effect: if evaluation had become a shipped skill, tier-routing logic (Core gets deep evaluation, Standard gets lite) currently handled cleanly in Python branching would need to be embedded in the skill prompt, making it harder to version-control and unit-test.

---

### P6-IMP-14: Evaluator Debate via SendMessage Instead of Dual-Independent Scoring (Updated by Adversarial Review)
**Status:** enhanced

**What (updated):** Replace dual-independent Opus scoring with a blind-then-debate sequential protocol. Evaluator B receives transcript + A's raw dimension scores (not A's explanations) and commits its own scores before seeing A's reasoning. Disagreements >10pt per dimension trigger a structured exchange where B sees A's explanation and writes a rebuttal. Structured `EvaluatorDisagreement` records drive richer metaprompting in Plan 12. Tie-breaking: unresolved disputes use the lower score with `unreliable: true` on that dimension.
**Why (updated):** The original "sequential with visibility" design exposes B to A's full output before B scores, creating anchoring bias: sequential peer review literature documents that reviewers who see prior scores drift toward them even when instructed to judge independently. The blind-then-debate protocol preserves the debate's information benefit while preventing anchoring. The `resolved_by` field and conservative tie-breaking (lower score wins) prevent runner blockage on persistent disagreements.
**How (updated):** (1) Change dual-Opus to "blind-then-debate sequential": B receives transcript + A's scores only; A's explanations withheld until B commits its own scores. (2) Debate phase triggered on >10pt divergence per dimension; B then sees A's explanation and writes structured rebuttal. (3) Add `EvaluatorDisagreement` model to Plan 01: `dimension, A_score, B_score, B_justification, resolved_score, resolved_by: Literal["consensus", "a_wins", "b_wins", "escalated"]`. (4) Tie-breaking: if unresolved after one exchange, use the lower score and flag `unreliable: true` for that dimension. (5) Update Plans 07 and 12 accordingly. (6) Note: evaluation_timeout (IMP-20) must account for debate round-trips — deep-with-debate budget should be 900s, not 600s.
**Impacts:** Plan 07 (blind-then-debate protocol), Plan 01 (`EvaluatorDisagreement` model + `resolved_by`), Plan 12 (disagreement-driven metaprompting), IMP-20 (timeout budget coordination required)

**Adversarial note (Evaluation Innovation Viability):** The original proposal is directionally sound but has an anchoring bias problem it does not address. When B sees A's full output (scores + reasoning) before committing, B systematically drifts toward A's position — documented in sequential peer review literature and RLHF calibration studies. The blind-then-debate protocol (B sees scores only before committing, then explanations during debate) preserves the information benefit without the anchoring. The `resolved_by` enum and conservative tie-breaking prevent the runner from blocking indefinitely on contested dimensions. Second-order cross-group conflict: IMP-03 (wall-clock estimates, other group) must be updated — debate adds 5-15 min per Core workflow with contested dimensions. Also: both evaluators should spawn in separate sessions (different `session_id`) to avoid response-caching effects that could cause B to produce near-identical reasoning to A even in the blind phase.

---

### P6-IMP-15: Pull 3 Intelligence Modules from v2 to v1 (Updated by Adversarial Review)
**Status:** enhanced

**What (updated):** Three intelligence modules promoted from v2 stubs to real v1 implementations in Plan 12 Part 5, with corrected LOC estimates and a schema prerequisite for coverage_radar:
1. `tier_manager.py` (~50 LOC on BaselineManager): Wraps existing BaselineManager thresholds. Activates after 3 runs. Human approval for demotion via `tier_demotion_proposals.yaml` (required by locked Implementation Decisions).
2. `contract_healer.py` (~30-50 LOC): Ceiling/floor/zero-variance detection from BaselineManager's 20-score windows. Activates after 5 real runs. Exit gate 16 verification: "exists + `is_active()` returns False before threshold" — not "has fired."
3. `coverage_radar.py` (~150-200 LOC, not ~100 LOC): Cross-references contracts vs runs on 4 axes. REQUIRES `coverage_axes` field added to evaluation contract schema in Plan 06 Wave 1. Current contracts have `category` (4 values) but NOT vuln-class/semantic-op/reasoning-skill/query-pattern axes. Without this field, coverage_radar can only count "N of 51 contracts run" — not a radar.
**Why (updated):** The v2 deferral is artificial for tier_manager and contract_healer. Coverage_radar requires a schema prerequisite that the original improvement missed. The "existing data sources" claim is partially false for coverage_radar — the axis data does not exist in any current contract.
**How (updated):** (1) Move tier_manager and contract_healer to Plan 12 Part 5. (2) Move coverage_radar to Plan 12 Part 5 with prerequisite: add optional `coverage_axes: {vuln_class: list[str], semantic_op: list[str], reasoning_skill: list[str], query_pattern: list[str]}` to evaluation contract schema in Plan 06 Wave 1 (same atomic commit as Schema Hardening, IMP-01+ADV-01+ADV-02). (3) Update exit gate 16: "At least 2 intelligence modules have real implementations with passing `is_active()` unit tests; coverage_radar activates if any contract has `coverage_axes` populated." (4) Specify human approval mechanism for tier demotion: `tier_demotion_proposals.yaml` requiring manual review before `apply_demotions()`. (5) Keep remaining 9 modules as stubs.
**Impacts:** Plan 12 scope increase (~250 LOC revised), Plan 06 schema change (coverage_axes field, atomic with Schema Hardening), Exit gate 16 revised

**Adversarial note (Evaluation Innovation Viability):** The original's ~100 LOC estimate for coverage_radar is the main factual problem. Code inspection confirms evaluation contracts have `category` (4 values: investigation/tool/orchestration/support) but no axis fields for vuln-class, semantic-op, reasoning-skill, or query-pattern. The 4-axis heat map requires these fields. Without them, coverage_radar reports "10 of 51 contracts run" with no severity-weighted gap prioritization — not a radar, just a counter. The ENHANCE makes the schema prerequisite explicit and schedules it in Plan 06 Wave 1 alongside Schema Hardening. The human-approval gate for tier demotion was absent from the original, which would have made tier_manager apply automatic demotions in violation of the locked Implementation Decisions ("Demotion requires human approval"). Exit gate 16 is also corrected: it cannot verify contract_healer "has fired" (requires 5 runs at phase completion) but can verify `is_active()` returns False before threshold — an objectively verifiable criterion.

---

### P6-IMP-17: Weave Improvement Signal INTO Evaluation, Not After (Updated by Adversarial Review)
**Status:** enhanced

**What (updated):** Add `improvement_hints: list[ImprovementHint]` to `EvaluationResult`. When dimension scores <40, Plan 07 generates immediate improvement hypotheses during scoring. `ImprovementHint` adds `baseline_score` (required to evaluate kill criteria after re-testing) and `calibration_status: Literal["uncalibrated", "calibrated"]`. Pre-calibration hints are excluded from the automated hypothesis queue and routed to human review only. Post-calibration hints enter the automated queue but `suggested_change` remains HITL-gated per Pillar 4 Rule E.
**Why (updated):** The original's noise contamination problem: improvement hints generated by a miscalibrated evaluator encode its biases as actionable guidance. Before exit gate 6 passes (evaluator distinguishes good from bad, differential >20pt, meta-eval agreement >80%), every hint is a product of a keyword heuristic with unknown reliability. CI annotation analogy breaks down: linters have known false-positive rates; pre-calibration evaluator hints do not. The `baseline_score` field is required so kill criteria are evaluable after re-testing — the original omitted this, making kill criteria structurally unevaluable.
**How (updated):** (1) Add `improvement_hints: list[ImprovementHint]` to `EvaluationResult` (Plan 01). (2) `ImprovementHint` fields: `dimension: str, score: int, baseline_score: int, hypothesis: str, suggested_change: str, kill_criterion: str, confidence: float, calibration_status: Literal["uncalibrated", "calibrated"]`. (3) Plan 07: generate hints when dimension <40; set `calibration_status` by checking `run_mode == "interactive"` AND this workflow has >= 3 prior meta-evaluation runs with >80% inter-rater agreement. (4) Plan 12 Part 2: `calibrated` hints enter automated queue; `uncalibrated` hints written to `.vrs/evaluations/uncalibrated_hints.jsonl` for human review. (5) `suggested_change` is read-only for automation; applying it requires HITL per Pillar 4 Rule E.
**Impacts:** Plan 01 (ImprovementHint model with calibration_status + baseline_score), Plan 07 (calibration check at hint generation), Plan 12 Part 2 (two-queue consumer)

**Adversarial note (Evaluation Innovation Viability):** The original improvement is sound in direction but has a critical Goodhart's Law risk: inline hints generated by a miscalibrated evaluator teach the improvement loop to optimize for evaluator satisfaction, not agent quality. Example: QUERY_FORMULATION scores 32 because the heuristic penalizes broad queries even when strategically appropriate. Hint: "agent lacks narrow query instruction." Engineer adds it. Agent over-narrows. Evaluator scores higher. Behavior got worse. The `calibration_status` field and two-queue consumer enforce the guard. The `baseline_score` addition is required for kill criterion evaluability — if a hint says "this change should improve QUERY_FORMULATION by 15 points" but the score at hint generation is not recorded, there is no baseline to measure 15 points from after re-testing.

---

### P6-IMP-20: Dual-Opus Sequential Timeout Cascade (Updated by Adversarial Review)
**Status:** confirmed

**How (addition):** The original How is correct. One addition required by P6-IMP-14 (debate protocol): if debate is adopted, the combined timeout for A + blind-phase + B + debate exchange exceeds 600s for Core-tier runs with multiple contested dimensions. Add: (4) if P6-IMP-14 is implemented, add `debate_enabled: bool` to evaluation contracts and use 900s evaluation budget when debate is enabled (standard=300s, deep=600s, deep-with-debate=900s). These two improvements must coordinate in their Plan 01 schema additions.

**Adversarial note (Evaluation Innovation Viability):** The timeout cascade analysis is correct and the failure scenario is concrete. The `evaluation_complete: bool` field is the right signal — simpler than a partial-result enum and sufficient for BaselineManager filtering. The conservative default (exclude partial unless opted-in) correctly prevents mixed single/dual-rater scores from corrupting rolling 20-window variance estimates. The only addition needed is coordination with IMP-14's debate protocol: if debate is implemented without adjusting evaluation budgets, every contested Core-tier run will produce `evaluation_complete: false` because the combined A + debate + B time exceeds the 600s deep budget. The `debate_enabled` field and 900s budget cap this interaction.

---

## P6-ADV-03: Calibration Bootstrap Trap — The Evaluator Cannot Self-Validate Before External Ground Truth Is Wired
**Target:** CONTEXT
**What:** Exit gate 6 requires the dual-Opus evaluator to "distinguish good from bad (differential > 20 points)" and achieve "meta-evaluation agreement > 80% for Core." Both criteria are satisfiable by an evaluator that reliably scores everything at 45 (bad) or 85 (good) with >20pt differential, regardless of whether those labels correspond to actual agent quality. The calibration loop is closed: the first 30+ transcripts used to calibrate the evaluator are also evaluated BY it. Inter-rater agreement merely confirms that two Opus instances agree — not that they agree correctly.

The project has ONE external ground truth signal today: the detection baseline in `docs/workflows/workflow-improvement.md` (Precision=13.3%, Recall=83.3%) and the 18 corpus contracts with known TP/FP/miss outcomes in `corpus/ground_truth.yaml`. Neither is wired to the evaluation framework.
**Why this gap matters:** All downstream improvements — improvement hints (IMP-17), metaprompting (Plan 12 Part 3), regression detection (Plan 12), tier promotion (IMP-15's tier_manager) — consume evaluation scores as ground truth. If those scores encode the evaluator's self-referential bias, every improvement cycle optimizes for evaluator satisfaction, not agent capability. IMP-13, IMP-14, IMP-15, and IMP-17 all assume the evaluator produces meaningful scores. None checks whether evaluator scores correlate with known external outcomes. This is Goodhart's Law at the architecture level.
**How:** (1) Add "Calibration Anchor Protocol" to CONTEXT.md Implementation Decisions: before exit gate 6 is checked, run the 4 Core investigation agents on the 18 corpus contracts and compare evaluation EVIDENCE_INTEGRATION and CONCLUSION_SYNTHESIS scores against known detection outcomes from `corpus/ground_truth.yaml`. Agents that find known vulnerabilities must score higher than agents that miss them. (2) Add to exit gate 6: "Evaluator correctly rank-orders agents by detection outcome on corpus ground truth: TP-finding agent > FP-reporting agent > miss agent on CONCLUSION_SYNTHESIS (Spearman rho > 0.6). This ranking must hold independently of inter-rater agreement." (3) External anchor must run BEFORE any `calibrated` hints (IMP-17) or metaprompting changes are accepted. (4) Add to Experiment Ledger Protocol: each Wave 7 change must include a counterexample scenario from corpus ground truth.
**Impacts:** CONTEXT.md Implementation Decisions (Calibration Anchor Protocol), Exit gate 6 (external rank-order criterion added), Plan 12 Part 1 (anchor run before baseline), Experiment Ledger Protocol
**Source:** Adversarial review (Evaluation Innovation Viability)
**Adversarial note (Evaluation Innovation Viability):** This gap is not covered by any existing improvement across all 20 items. It is the highest-severity risk in the 3.1c design: a self-sealing evaluation loop that produces consistent scores while being systematically wrong about agent quality. `corpus/ground_truth.yaml` already exists — this is not a new data requirement. Wiring the evaluator to it requires ~20 LOC in Plan 12 and one additional exit gate criterion. The cost is low; the risk of omission is that Phase 3.1c's entire improvement loop optimizes in the wrong direction.

---

### P6-ADV-04: `progress.json` Data Contract Is Unspecified Across Plans 08 and 12
**Target:** CONTEXT
**What:** Both rejected IMP-19 and reframed IMP-18 depend on a `progress.json` file that Plan 08 does not specify writing and Plan 12 does not specify reading. No data model, write frequency, file location, or schema is defined anywhere. Without it, the reframed IMP-18 CLI command (`alphaswarm evaluation summary`) degrades to reading individual evaluation JSON files one by one — the same problem it was meant to solve. The improvement loop (Plan 12) cannot query "which workflows completed at what score" without per-file iteration.
**Why:** A 6-17 hour evaluation run with no queryable progress state forces the human reviewer to parse raw log output. Plan 12's improvement cycle needs to know which workflows scored below threshold before choosing which dimensions to target. Multiple improvements in this pass were reaching for this data contract independently without naming it.
**How:** (1) Add `EvaluationProgress` model to Plan 01: `total_workflows: int`, `completed_workflows: int`, `current_workflow: str | None`, `scores_by_workflow: dict[str, int]`, `started_at: datetime`, `estimated_completion: datetime | None`. (2) Plan 08: after each workflow completes, write `EvaluationProgress` to `.vrs/evaluations/progress.json` using atomic write (`os.replace()` after writing to temp file — avoids partial reads during long runs). ~40 LOC. (3) Plan 12: read `progress.json` as the entry point for "which workflows scored below threshold." (4) The CLI command in reframed IMP-18 reads `progress.json` as primary source. (5) Note: `os.replace()` is POSIX-atomic on same filesystem; document this platform assumption.
**Impacts:** Plan 01 (+1 model ~20 LOC), Plan 08 (+atomic progress write ~40 LOC), Plan 12 (reads progress.json as starting point), reframed IMP-18 (depends on this for full aggregation value)
**Research needed:** no
**Confidence:** HIGH
**Prior art:** 5 -- progress state files are standard for long-running pipelines (pytest-xdist, cargo)
**Prerequisite:** no
**Status:** open

**Source:** Adversarial review (CC Capability Integration Justification)
**Adversarial note (CC Capability Integration Justification):** The rejection of IMP-19 and the reframe of IMP-18 both assumed a stable progress data source exists. It does not. This CREATE item captures the essential deliverable that both items were circling around. Without `progress.json`, the reframed IMP-18 CLI command degrades to reading individual JSON files, defeating its purpose. The data contract must be in Plan 01 and Plan 08 before either IMP-18's CLI command or any downstream consumer can be reliably implemented.

---

## Adversarial Review: CC Capability Integration Justification
**Items reviewed:** 4 (P6-IMP-04, P6-IMP-16, P6-IMP-18, P6-IMP-19)
**Verdicts:** ENHANCE: 1 (IMP-04), REJECT: 2 (IMP-16, IMP-19), REFRAME: 1 (IMP-18), CREATE: 1 (P6-ADV-04)
**Cross-group conflicts:**
- IMP-19 (rejected) and reframed IMP-18 both reference `progress.json` from Plan 08. This file is not in Plan 08's current scope. P6-ADV-04 creates the explicit data contract. Not addressed by Agent Teams group (IMP-01-07), Transcript Pipeline group (IMP-08-12), or Evaluation Innovation group (IMP-13-15, 17, 20).
- IMP-16 (rejected) claimed to fix the `_check_graph_first` bug. Evaluation Innovation items do not touch this bug. The Plan 04 ~5 LOC fix remains as specified in Known Code Issues. Rejection eliminates only the proposed hook mechanism.
- Reframed IMP-18 adds an `evaluation` subcommand to the `alphaswarm` CLI. No other group's improvements touch the CLI. Implementation must not touch `executor.py` or `builder_legacy.py` per CLAUDE.md.
- Enhanced IMP-04 adds `layer_used="send_message_malformed"` and a CC Capability note. The Agent Teams reviewer's CONFIRM note is also present on IMP-04 — both notes now coexist. No conflict; the notes address complementary concerns (cross-group dependency for the Agent Teams note, failure-mode precision for the CC Capability note).
- IMP-18 REFRAME depends on P6-ADV-04. The Evaluation Innovation reviewer's ADV-03 (Calibration Bootstrap Trap) and this ADV-04 are independent; they address different gaps.
**Second-order risks:**
- IMP-04 ENHANCE: `LAYER_NAMES` tuple at `debrief_protocol.py:64` must be extended to include `"send_message_malformed"` in the same commit as the validator. If extended in isolation without updating the `LAYER_FUNCTIONS` list (which is parallel to `LAYER_NAMES`), index errors will fire at runtime.
- IMP-16 REJECT: The `_check_graph_first` bug remains in `graph_value_scorer.py:170-193`. Plan 04 owns the ~5 LOC fix. If Plan 04 is implemented without consulting Known Code Issues, the false-positive persists silently.
- IMP-18 REFRAME: The CLI aggregator reads `.vrs/evaluations/` which may not exist on clean installs. The two-line guard is required in the spec.
- P6-ADV-04 CREATE: Atomic `os.replace()` is POSIX-atomic on same filesystem. On Windows with different-drive source/dest, it is non-atomic. Project targets macOS/Linux (consistent with IMP-10's fcntl approach) — acceptable, but must be documented.


## Adversarial Review: Evaluation Innovation Viability
**Items reviewed:** 5 (P6-IMP-13, P6-IMP-14, P6-IMP-15, P6-IMP-17, P6-IMP-20)
**Verdicts:** REFRAME: 1 (IMP-13), ENHANCE: 3 (IMP-14, IMP-15, IMP-17), CONFIRM: 1 (IMP-20), CREATE: 1 (P6-ADV-03)

**Cross-group conflicts:**
- IMP-13 (evaluator-as-skill, reframed) vs IMP-04 (debrief validation, other group) and IMP-18 (MCP server, other group): if evaluation had become a shipped skill, DebriefResponseValidator and MCP query logic would need to be embedded in the skill prompt, fragmenting validation across two systems. The reframe (keep Python runner, add real LLM call path) resolves this conflict by maintaining Python as the coordination layer.
- IMP-14 (debate, enhanced) vs IMP-03 (wall-clock analysis, other group): debate adds 5-15 min per Core-tier workflow where dimensions disagree by >10pt. IMP-03's wall-clock estimates for the Core sub-wave (~200 min) are understated if debate is adopted. IMP-03's wall-clock table must add a "with-debate" column for Core tier.
- IMP-15 (coverage_radar schema change) vs Schema Hardening decision (locked, IMP-01+ADV-01+ADV-02 atomic commit): adding `coverage_axes` to contract schema must land in the same atomic commit as Schema Hardening. Both affect Plan 06 Wave 1. This is a coordination constraint between IMP-15's prerequisite and the locked Schema Hardening changes — a single atomic commit prevents invalid intermediate states.
- IMP-20 (evaluation_complete + evaluation_timeout) vs Schema Hardening: adding `evaluation_complete` and `evaluation_timeout` to EvaluationResult and contracts while `additionalProperties: false` is locked means these fields must be in the Schema Hardening commit or they will fail validation. Single atomic commit constraint applies here too.

**Second-order risks:**
1. IMP-14 (debate): Anchoring bias mitigated by blind-then-debate protocol in the ENHANCE. Remaining risk: both Opus evaluators in the same session may share response caching at the model level, causing B to produce near-identical reasoning to A even in the blind phase. Mitigation: spawn A and B in separate sessions with different `session_id` values.
2. IMP-15 (coverage_radar prerequisite): `coverage_axes` schema field must be defined in Plan 06 Wave 1 before Core contracts are hand-authored, otherwise all 10 Core contracts must be retrofitted. Scheduling is a dependency, not a blocker, but must be captured explicitly in Plan 06's authoring order.
3. IMP-17 (inline hints): `suggested_change` must be HITL-only per CONTEXT.md Pillar 4 Rule E. If automation reads and applies `suggested_change` without human review, the improvement loop operates autonomously in violation of a locked decision. The two-queue consumer in the ENHANCE routes all hints to human review until `calibration_status: "calibrated"`.
4. P6-ADV-03 (calibration anchor): if the external anchor reveals systematic evaluator miscalibration (likely given the keyword-matching baseline), exit gate 6 may be permanently blocked until evaluator work is done. This is the correct behavior. The temptation to satisfy exit gate 6 on inter-rater agreement alone, without the external rank-order criterion, must be explicitly ruled out in the gate definition.
5. IMP-20 + IMP-14 coordination: if debate protocol is implemented without adjusting evaluation budgets, every contested Core-tier run produces `evaluation_complete: false` because A + debate + B exceeds 600s. The `debate_enabled` field and 900s budget cap this interaction — but only if both improvements are implemented together. If IMP-14 lands before IMP-20's debate-budget addition, there will be a window where debate silently times out B on every Core-tier run.
