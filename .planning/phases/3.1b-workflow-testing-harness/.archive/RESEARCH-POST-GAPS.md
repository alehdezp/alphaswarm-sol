# Phase 3.1b Research Post-Gap Resolution Summary

**Date:** 2026-02-12
**Scope:** Cross-reference of all 3.1b research files against GAP-01 through GAP-11 resolutions
**Purpose:** Capture what research was confirmed, extended, superseded, or newly discovered during gap resolution

---

## 1. Research Confirmed by Gap Work

These research findings were validated and used directly by gap resolution agents.

### 1.1 Agent Teams Idle State + SendMessage (AGENT-TEAMS-DEEP-RESEARCH.md)

| Research Finding | Gap Resolution | Status |
|-----------------|---------------|--------|
| RQ-1: Idle agents stay alive as processes in wait state | GAP-01-02: Used as design basis for `TeamObservation` model | CONFIRMED |
| RQ-2: SendMessage DOES wake idle agents | GAP-01-02: `InboxMessage` dataclass built on this finding | CONFIRMED |
| RQ-3: Five termination mechanisms (clean shutdown, rate limit, natural idle, leader death, max turns) | GAP-05: Informed `modes: [single, team]` approach to avoid lifecycle complexity | CONFIRMED |
| RQ-4: Command hooks with exit code 2 work; prompt hooks broken (bug #20221) | RS-04 + GAP-01-02: All observation hooks use command type only | CONFIRMED |
| RQ-5: Context preserved during idle (until compaction at 80% window) | GAP-01-02: `AgentObservation` captures data before potential compaction | CONFIRMED |
| SendMessage returns success:true even for dead agents | GAP-01-02: Acknowledged as remaining risk, mitigated by hook-based approach | CONFIRMED |

### 1.2 Hook Verification (hook-verification-findings.md / RS-04)

| Research Finding | Gap Resolution | Status |
|-----------------|---------------|--------|
| Event type from JSON stdin (`hook_event_name`), not env var | All gap resolution hooks use JSON stdin | CONFIRMED |
| Hook timeout 30s (was 5s, fixed) | Downstream consumers accept default timeout | CONFIRMED |
| `.vrs/observations/` directory convention | GAP-01-02 writes observations to this directory | CONFIRMED |
| `extra_hooks` API on `install_hooks()` | GAP-01-02 observation infrastructure uses this API | CONFIRMED |
| Iteration 3 (Smart Selection / HookConfig) DROPPED per Philosophy Rule A | No gap resolution needed HookConfig; tuple API sufficient | CONFIRMED |

### 1.3 Companion Bridge Protocol (companion-bridge-findings.md / RS-01)

| Research Finding | Gap Resolution | Status |
|-----------------|---------------|--------|
| REST endpoint is `POST /api/sessions/create` (not `/api/sessions`) | Not directly consumed by gaps (Companion deferred) | CONFIRMED but DEFERRED |
| Browser WS uses single JSON per frame, NOT NDJSON | Same | CONFIRMED but DEFERRED |
| `bypassPermissions` eliminates `can_use_tool` events entirely | Same | CONFIRMED but DEFERRED |
| Direct CLI subprocess (`claude -p --output-format stream-json`) provides same protocol | GAP-03: Validates that Companion is not uniquely needed | CONFIRMED |

### 1.4 Transcript Format + TranscriptParser (3.1b-RESEARCH.md)

| Research Finding | Gap Resolution | Status |
|-----------------|---------------|--------|
| JSONL record types: user, assistant, progress, file-history-snapshot | GAP-02: BSKGQuery extraction parses these record types | CONFIRMED |
| `_records` internal attribute is stable | GAP-04: Documented as stability contract with versioning convention | CONFIRMED |
| ISO 8601 timestamps enable duration computation | GAP-02: Used for `BSKGQuery.timestamp` field | CONFIRMED |
| `tool_use_id` links tool_use to tool_result | GAP-02: Used for query result extraction | CONFIRMED |

### 1.5 Eval Framework (3.1b-RESEARCH.md)

| Research Finding | Gap Resolution | Status |
|-----------------|---------------|--------|
| Tasks + Trials + Graders model from Anthropic blog | GAP-09: EvaluationGuidance + escalation_rules follow this model | CONFIRMED |
| pass@k / pass^k metrics for stochastic evaluation | GAP-05: `modes: [single, team]` enables comparative pass@k | CONFIRMED |
| Three grader types: code-based, model-based, human | GAP-09: Escalation rules implement model-based grading with LLM assessment | CONFIRMED |

---

## 2. Research Extended by Gap Work

These findings were correct but incomplete. Gap resolution work extended them with additional detail.

### 2.1 Basic `has_bskg_query()` -> Structured `BSKGQuery` Extraction (GAP-02)

**Original research** (3.1b-RESEARCH.md): TranscriptParser has `has_bskg_query()` -- a boolean string match detecting `alphaswarm query` or `alphaswarm build-kg` in Bash tool calls.

**Gap extension:** GAP-02 designed structured extraction:
- `BSKGQuery` dataclass with `query_type` (pattern/nl/build-kg/property), `query_text`, `raw_command`, `result`, `timestamp`, `tool_call_index`
- `get_bskg_queries()` method returning `list[BSKGQuery]`
- `graph_citation_rate()` metric computing the ratio of conclusions that cite graph evidence
- `_check_citation()` helper correlating query results with subsequent Write/SendMessage content
- Classification regex for query types (e.g., `pattern:` prefix for pattern queries)

**Impact:** Extends a boolean presence check into a full structured analysis pipeline. The original research correctly identified the gap but underestimated the extraction complexity.

### 2.2 Multi-Agent Correlation Gap -> TeamObservation Model (GAP-01)

**Original research** (3.1b-RESEARCH.md): Noted that EventStream provides event-level building blocks but "What's missing is the transcript-level and message-level linking."

**Gap extension:** GAP-01 designed the complete linking model:
- `AgentObservation`: Per-agent transcript summary with tool calls, BSKG queries, findings, timing
- `TeamObservation`: Cross-agent correlation with `evidence_chain()`, `agreement_depth()`, `message_flow()`, `per_agent_graph_usage()`
- `InboxMessage`: Parsed from `~/.claude/teams/{name}/inboxes/{agent}.json`
- `CollectedOutput`: Aggregation container with `failure_notes: str` (GAP-11)

**Impact:** Fills the identified gap with ~480 LOC of structured models. The research correctly identified the need; the gap resolution provided the design.

### 2.3 Hooks Extensibility -> `extra_hooks` API (RS-04 + GAP-01-02)

**Original research** (hook-verification-findings.md): Fixed `install_hooks()` to accept `extra_hooks` parameter.

**Gap extension:** GAP-01-02 defined the specific hooks needed:
- PreToolUse observation hook (captures tool selection decisions)
- PostToolUse observation hook (captures tool results)
- SubagentStop observation hook (captures agent completion data)
- TeammateIdle observation hook (captures idle/debrief events)

**Impact:** The API designed in RS-04 is confirmed sufficient. No API changes needed.

### 2.4 TranscriptParser Extension Pattern -> `_records` Stability Contract (GAP-04)

**Original research** (3.1b-RESEARCH.md): Showed extension pattern for adding `timestamp` and `duration_ms` to `ToolCall`.

**Gap extension:** GAP-04 formalized:
- `_records` stability contract: "The `_records` attribute is a list[dict] of raw JSONL records. Its structure is stable and can be accessed by extension methods."
- Naming conventions: `get_*/has_*/*_index` for public methods
- Docstring version tags: `@since 3.1b-02`
- Option A (Direct Method Addition) chosen over subclassing or mixins

**Impact:** Codifies what was implicit in the research pattern into an explicit contract for future extensions.

---

## 3. Research Superseded by Gap Work

These findings were correct at research time but have been replaced by gap resolution decisions.

### 3.1 Companion as PRIMARY Tool (RS-01 Verdict) -> Deferred to Wave 4 (GAP-03)

**Original research** (companion-bridge-findings.md): "Companion is the **primary tool for workflow testing**, not secondary."

**Superseded by:** GAP-03 confirmed that Companion has ZERO blocking 3.1c consumers. The 3.1c exit gate (context.md line 1621) explicitly marks Companion as NICE-TO-HAVE. The 3.1b-04 dependency on 3.1b-01 was confirmed FALSE -- TeamManager uses native Agent Teams API.

**New status:** Companion is Wave 4 (deferred). Still technically valuable for interactive debugging and multi-session management, but not on the critical path.

### 3.2 Dedicated Orchestration Scenario (Original GAP-05) -> `modes` Field (GAP-05 REVISED)

**Original design:** A dedicated `multi-agent-reentrancy-debate/` scenario with `LendingVault.sol`, `SafeLendingVault.sol`, team-specific ground truth, and `agent_team` configuration (~200 LOC).

**Superseded by:** `modes: [single, team]` field on ANY scenario (~20 LOC). The comparative approach (single vs team output) is more informative than dedicated team scenarios.

### 3.3 Full Failure Classification Engine (Original GAP-11) -> `failure_notes: str` (GAP-11 REVISED)

**Original design:** ~450 LOC failure classification system with structured taxonomy.

**Superseded by:** Simple `failure_notes: str` field on `CollectedOutput` (~4 LOC). Philosophy: instrument first, classify later. The structured taxonomy can be built once there is enough data to inform categories.

### 3.4 Separate `workflow-categories.yaml` (Original GAP-10) -> `category` Field on `catalog.yaml` (GAP-10 REVISED)

**Original design:** Separate YAML file mapping agents to workflow categories.

**Superseded by:** Adding `category` field directly to existing `catalog.yaml` (24 agents) and `registry.yaml` (34 skills). Five categories: investigation, orchestration, evaluation, tooling, utility.

### 3.5 Separate `external-sources.yaml` (Original GAP-08) -> VulnDocs IS the Source (GAP-08 REVISED)

**Original design:** Maintain a separate registry mapping external vulnerability databases to scenario coverage.

**Superseded by:** VulnDocs (680+ patterns) IS the authoritative source. External databases (SWC, SolidityLang bugs, Ethernaut) are mapped via a one-time audit script, not a maintained registry.

---

## 4. Novel Findings from Gap Resolution

Discoveries made during gap resolution that were NOT present in any prior research file.

### 4.1 Training Data Contamination Protocol (GAP-06-07-08)

**Source:** GAP-06-07-08 resolution, informed by academic papers.

**Key papers discovered:**
- **SC-Bench** (arxiv:2410.06176): Warns that well-known vulnerable contracts exist in LLM training data from 2024 onward. Testing with recognizable contracts measures recall, not reasoning.
- **Compositional Generalization** (arxiv:2601.06914): LLMs achieve 98%+ accuracy on known reentrancy patterns via memorization.
- **Benchmark Contamination Surveys** (arxiv:2406.04244): Systematic analysis of contamination across ML benchmarks.

**Protocol (5 rules):**
1. No standard educational contracts (Ethernaut, DamnVulnerableDeFi, SWC test cases)
2. No exact code from blog posts, audit reports, or tutorials
3. All contracts must be freshly authored with non-standard naming
4. Vulnerability patterns must be composed from VulnDocs behavioral specs, not copied from examples
5. Each contract must pass a "novelty check" -- would a human auditor recognize this from training data?

**Impact:** This is a cross-cutting constraint affecting all corpus creation (3.1b-06) and evaluation (3.1c).

### 4.2 Real Inbox File Format (GAP-01-02)

**Source:** GAP-01-02 codebase investigation.

**Location:** `~/.claude/teams/{team_name}/inboxes/{agent_name}.json`

**Format:** JSON array of message objects:
```json
{
  "from": "team-lead",
  "text": "...",
  "summary": "...",
  "timestamp": 1707753600000,
  "color": "blue",
  "read": false
}
```

**Team config:** `~/.claude/teams/{team_name}/config.json` contains `members[]` array with `agentId`, `name`, `agentType`, `model`, `cwd` per member.

**Impact:** Enables the `InboxMessage` dataclass in `TeamObservation` model and verifies that message parsing can be done without Companion.

### 4.3 False Dependency Confirmation (GAP-03)

**Source:** GAP-03 investigation of 3.1c exit gate.

**Finding:** 3.1b-04's declared dependency on 3.1b-01 is FALSE. Evidence:
- 3.1c exit gate (context.md line 1621) marks Companion as NICE-TO-HAVE
- TeamManager uses native Agent Teams API (`TeamCreate`, `SendMessage`, `TeamDelete`), not Companion sessions
- Zero 3.1c plans declare a hard dependency on `CompanionBridge` or `CompanionSession`
- The only 3.1c consumer of Companion is 3.1c-12 (regression baseline), and even there it is optional

**Impact:** Unblocked the entire critical path by removing a false serial dependency.

### 4.4 Adversarial Scenario Categories (GAP-06)

**Source:** GAP-06 resolution.

Three categories with 15 techniques:

| Category | Techniques | What It Validates |
|----------|-----------|-------------------|
| A: Name Obfuscation | 5 (renamed functions, misleading names, deep call chains, dead code, safe-but-scary names) | Behavioral detection independent of naming |
| B: Protocol Complexity | 5 (multi-contract split, proxy, custom callback, state machine, economic rounding) | Cross-contract and protocol-level reasoning |
| C: Honeypot Inversions | 5 (fake vuln behind guard, timelock, combined fix, inverted assert, safe math wrapper) | False positive resistance |

**Impact:** Provides the adversarial design toolkit for corpus creation (3.1b-06).

### 4.5 Pattern-Derived Generation Pipeline (GAP-07)

**Source:** GAP-07 resolution.

Six-step pipeline for generating test contracts from VulnDocs patterns:
1. Select pattern from VulnDocs (e.g., `oracle-manipulation`)
2. Extract behavioral operations (e.g., `READS_EXTERNAL_VALUE`, `WRITES_USER_BALANCE`)
3. Choose novel domain context (e.g., NFT marketplace instead of DeFi lending)
4. Compose contract with operations in vulnerable arrangement
5. Apply adversarial technique from GAP-06 category
6. Validate against contamination protocol

**Impact:** Provides a systematic method for corpus expansion beyond the initial 10-12 curated scenarios.

### 4.6 Escalation Rules Schema (GAP-09)

**Source:** GAP-09 resolution.

`EvaluationGuidance` extended with `escalation_rules`:
- 11 condition types (e.g., `graph_citation_rate < 0.3`, `false_positive_count > 2`, `no_tool_use_after_turn_3`)
- 5 action types: `add_evaluation_question`, `increase_trial_count`, `flag_for_human_review`, `switch_to_model_grader`, `mark_inconclusive`
- Conditions are per-scenario, enabling adaptive evaluation

**Impact:** Enables smart evaluation that adjusts behavior based on observed agent performance.

### 4.7 Corpus Composition (GAP-06-07-08)

**Source:** Combined GAP-06/07/08 resolution.

12-scenario corpus composition:
| Type | Count | Source |
|------|-------|--------|
| Standard | 3 | Direct from VulnDocs behavioral specs |
| Adversarial | 4 | GAP-06 categories A/B/C + contamination protocol |
| Orchestration | 2 | Any scenario with `modes: [single, team]` |
| FP Control | 3 | Safe contracts that should produce zero findings |

**Impact:** Defines the concrete corpus for 3.1b-06 implementation.

---

## 5. Remaining Research Gaps

### 5.1 Empirical Hook Fire Test (Deferred to 3.1b-07)

RS-04 closed via cross-reference analysis. The one thing cross-reference cannot prove is "do hooks actually fire on MY machine in a real Claude Code session?" This belongs in the 3.1b-07 Interactive Smoke Test.

### 5.2 Companion Multi-Session Management (Deferred to Wave 4)

The Companion bridge is technically validated (RS-01 verified all endpoints) but no implementation work has been done. When Wave 4 begins, the RS-01 findings should be re-verified against the then-current Companion version (was 0.20.3 at research time).

### 5.3 Agent Teams Experimental Feature Stability

Agent Teams are behind `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. The research is based on current behavior. Claude Code updates may change Agent Teams internals. The 30-day validity window (until 2026-03-11) from the original research applies.

### 5.4 Compaction Impact on Debrief Quality

AGENT-TEAMS-DEEP-RESEARCH.md identified that auto-compaction at 80% context window can destroy structured context. No mitigation strategy has been designed. For short debrief sequences (1-2 turns), this is low risk. For longer debrief protocols, this needs attention.

---

## 6. Recommendations for Plan Generation

### Priority Order for Implementation

Based on the confirmed wave execution order (GAP-03):

1. **Wave 1 (parallel, start immediately):** 3.1b-02 (Parser+Collector), 3.1b-03 (Hooks -- DONE), 3.1b-06 (Corpus)
2. **Wave 2:** 3.1b-04 (Agent Teams) -- depends on 02+03
3. **Wave 3:** 3.1b-05 (DSL) -- depends on 04
4. **Wave 4:** 3.1b-01 (Companion) -- NICE-TO-HAVE, independent
5. **Wave 5:** 3.1b-07 (Smoke Test) -- depends on all above

### Key Design Decisions Already Made

| Decision | Source | Impact |
|----------|--------|--------|
| Direct method addition for TranscriptParser | GAP-04, Option A | No subclassing; add methods + `_records` stability contract |
| `modes: [single, team]` for orchestration | GAP-05 REVISED | ~20 LOC, any scenario can be team-tested |
| `failure_notes: str` for failure tracking | GAP-11 REVISED | ~4 LOC, instrument-first approach |
| `category` field on catalog.yaml | GAP-10 REVISED | No separate taxonomy file |
| VulnDocs as authoritative source | GAP-08 REVISED | One-time audit script, not maintained registry |
| Training Data Contamination Protocol | GAP-06 | 5 rules, cross-cutting constraint on all corpus work |
| Command hooks only (not prompt hooks) | RS-04 + Bug #20221 | Prompt-based SubagentStop hooks are broken |

### Files Updated by This Review

| File | Update Type |
|------|------------|
| `.planning/phases/3.1b-workflow-testing-harness/3.1b-RESEARCH.md` | Inline post-gap notes (summary, locked decisions, open question #1, confidence breakdown) |
| `.vrs/debug/phase-3.1b/research/companion-bridge-findings.md` | Inline post-gap note on verdict section (Companion deprioritized) |
| `.planning/research/AGENT-TEAMS-DEEP-RESEARCH.md` | Inline post-gap note confirming all findings |
| `.vrs/debug/phase-3.1b/research/hook-verification-findings.md` | Inline post-gap note confirming all findings |
| `.planning/phases/3.1b-workflow-testing-harness/RESEARCH-POST-GAPS.md` | This file (new) |
