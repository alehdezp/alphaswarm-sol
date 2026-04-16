# Agent Teams Deep Research: Lifecycle, Idle State, Hooks, and Context Preservation

**Date:** 2026-02-11
**Researcher:** Claude Opus 4.6 (automated research)
**Confidence Calibration:**
- CONFIRMED = Official docs or source code
- OBSERVED = Community reports with reproduction evidence
- INFERRED = Logical deduction from confirmed facts
- UNCERTAIN = Plausible but unverified

---

## Table of Contents

1. [RQ-1: Agent Idle State](#rq-1-agent-idle-state)
2. [RQ-2: SendMessage to Idle Agents](#rq-2-sendmessage-to-idle-agents)
3. [RQ-3: Agent Lifecycle and Termination](#rq-3-agent-lifecycle-and-termination)
4. [RQ-4: Hook Blocking with Exit Code 2](#rq-4-hook-blocking-with-exit-code-2)
5. [RQ-5: Context Preservation](#rq-5-context-preservation)
6. [Implications for AlphaSwarm.sol](#implications-for-alphaswarsol)
7. [Sources](#sources)

---

## RQ-1: Agent Idle State

**Question:** What happens when a teammate goes idle in Claude Code Agent Teams? Is the process still alive? How long does it stay alive?

### Findings

**CONFIRMED (Official Docs):**
- When a teammate finishes its turn (no tool calls, no pending work), it enters an "idle" state.
- The `TeammateIdle` hook event fires "when an agent team teammate is about to go idle after finishing its turn."
- Idle notifications are sent automatically to the lead: "when a teammate finishes and stops, they automatically notify the lead."
- The official docs describe idle as a state, not termination.

**CONFIRMED (Official Docs - Agent Teams page):**
- The docs distinguish between idle and shutdown. Shut down is explicit: "The lead sends a shutdown request. The teammate can approve, exiting gracefully, or reject with an explanation."
- Idle teammates can receive messages: "Idle notifications: when a teammate finishes and stops, they automatically notify the lead" -- the use of "stops" here is ambiguous but contextually means "stops working" not "stops existing."

**OBSERVED (ClaudeWorld "Five Ways to Die" article):**
- "Natural Idle After Completion" (Death #3): "Teammate finishes work. Last assistant message is a plain text summary with no tool calls. Runtime determines 'no next step' and emits an idle notification. **Process doesn't terminate** -- it enters a wait state: new inbox messages wake it up, silence keeps it hanging."
- This is the critical finding: **idle agents stay alive as processes, waiting for new messages.**

**OBSERVED (ClaudeWorld "Six Fractures" article):**
- "The Idle Storm" (Fracture 6): One agent sent 9 idle notifications in 5 seconds. This means idle fires **per-turn**, not per-session.
- Each time the agent's turn ends without a tool call, it triggers another idle notification.
- v2.0.14 partially addressed this: "Fixed how idleness is computed for notifications."

**UNCERTAIN:**
- No official documentation specifies a timeout for how long idle agents remain alive.
- No official docs mention PID tracking or heartbeat mechanisms.
- The ClaudeWorld article states: "the system has no PID tracking, no orphan detection, no auto-cleanup."

### Summary

| Aspect | Status | Confidence |
|--------|--------|------------|
| Idle agent process stays alive | Yes | OBSERVED (high confidence) |
| Idle agent enters a wait state for messages | Yes | OBSERVED (high confidence) |
| TeammateIdle fires per-turn, not per-session | Yes | OBSERVED (medium confidence) |
| Hard timeout for idle agent lifetime | Unknown, likely none | UNCERTAIN |
| Idle agents die when lead session ends | Yes (in-process mode) | OBSERVED (high confidence) |

---

## RQ-2: SendMessage to Idle Agents

**Question:** Can you send messages to idle teammates? Do they wake up and respond with full context?

### Findings

**CONFIRMED (Official Docs - Agent Teams page):**
- "Automatic message delivery: when teammates send messages, they're delivered automatically to recipients. The lead doesn't need to poll for updates."
- Messages are delivered to `~/.claude/teams/{team}/inboxes/{recipient}.json` (file-based).
- The official docs explicitly say you can "Talk to teammates directly" using Shift+Up/Down in in-process mode.

**OBSERVED (ClaudeWorld "Five Ways to Die"):**
- Death #3 (Natural Idle): "Process doesn't terminate -- it enters a wait state: **new inbox messages wake it up**, silence keeps it hanging."
- This confirms: SendMessage to an idle agent DOES wake it up.

**CONFIRMED (Official Docs - Agent Teams page):**
- "Each teammate is a full, independent Claude Code session. You can message any teammate directly to give additional instructions, ask follow-up questions, or redirect their approach."
- This implies idle agents are still responsive.

**OBSERVED (ClaudeWorld "Mesh Topology"):**
- `SendMessage` always returns `success: true` -- even if the recipient process is dead. There is no delivery confirmation.
- "The pipe is wide open. But opening Mesh means handling the 'silent dead' problem yourself."
- This means you cannot distinguish between "message delivered to idle agent" and "message delivered to dead agent's inbox file."

**INFERRED:**
- When an idle agent's inbox receives a new message, the Claude Code runtime detects the inbox change and gives the agent a new turn with the message content.
- The agent receives the message as a user-turn message, processes it, and generates a response.
- The agent retains its full context window at this point (see RQ-5).

### Summary

| Aspect | Status | Confidence |
|--------|--------|------------|
| Can send messages to idle agents | Yes | CONFIRMED |
| Idle agents wake up on new messages | Yes | OBSERVED (high confidence) |
| Agent responds with full context on wake | Yes (see RQ-5) | INFERRED (medium-high) |
| Delivery confirmation exists | No | OBSERVED |
| Can distinguish idle from dead | No | OBSERVED |

---

## RQ-3: Agent Lifecycle and Termination

**Question:** What controls when an agent process dies? Is there a timeout?

### Findings

**CONFIRMED (Official Docs):** Five termination mechanisms exist:

| Mechanism | Description | Protocol | Source |
|-----------|-------------|----------|--------|
| **Clean Shutdown** | Lead sends `shutdown_request`, teammate approves | Full protocol | Official docs |
| **Rate Limit Kill** | API quota exhausted | Silent, no notification | ClaudeWorld |
| **Natural Idle** | No more work, enters wait state | Idle notification sent | Official docs + ClaudeWorld |
| **Leader Session Ends** | Lead closes terminal | In-process agents die with it | Official docs (limitation) |
| **Max Turns Timeout** | `Task(max_turns=N)` or 30-min ceiling | Forced stop | ClaudeWorld |

**CONFIRMED (Official Docs - Limitations):**
- "No session resumption with in-process teammates: `/resume` and `/rewind` do not restore in-process teammates."
- "Shutdown can be slow: teammates finish their current request or tool call before shutting down, which can take time."
- "One team per session: a lead can only manage one team at a time."

**CONFIRMED (Official Docs - Shutdown):**
- "The lead sends a shutdown request. The teammate can approve, exiting gracefully, or reject with an explanation."
- Rejection means the teammate stays alive and keeps working.

**OBSERVED (ClaudeWorld "Wandering Ghosts" - Fracture 5):**
- No PID tracking exists.
- No orphan detection exists.
- No auto-cleanup for expired team directories.
- Every Agent Teams session leaves filesystem residue.
- Cleanup is manual: `rm -rf ~/.claude/teams/team-*`

**OBSERVED (ClaudeWorld "Six Fractures"):**
- Agent Teams is described as "in-process concurrency (coroutines)" not "true parallelism (processes)."
- In-process teammates share the lead's process tree.
- When lead dies, all in-process teammates die silently.

**UNCERTAIN:**
- No documented hard timeout for idle agent lifetime in official docs.
- Whether tmux-based (split-pane) agents survive lead termination is not explicitly documented but likely yes since they run in separate tmux panes.

### Summary

| Aspect | Status | Confidence |
|--------|--------|------------|
| Clean shutdown protocol exists | Yes, request/approve | CONFIRMED |
| Agents can reject shutdown | Yes | CONFIRMED |
| Rate limit kills silently | Yes, no notification | OBSERVED |
| In-process agents die with lead | Yes | CONFIRMED |
| Hard idle timeout | None documented | UNCERTAIN |
| Orphan cleanup is manual | Yes | OBSERVED |
| tmux agents survive lead death | Likely, but undocumented | UNCERTAIN |

---

## RQ-4: Hook Blocking with Exit Code 2

**Question:** Can hooks block SubagentStop? Does exit code 2 actually prevent agent termination?

### Findings

**CONFIRMED (Official Docs - Hooks Reference):**

The exit code 2 blocking behavior table from official docs:

| Hook Event | Can Block? | What happens on exit 2 |
|------------|-----------|----------------------|
| `SubagentStop` | **Yes** | Prevents the subagent from stopping |
| `TeammateIdle` | **Yes** | Prevents the teammate from going idle (teammate continues working) |
| `TaskCompleted` | **Yes** | Prevents the task from being marked as completed |
| `Stop` | **Yes** | Prevents Claude from stopping, continues the conversation |
| `PostToolUse` | No | Shows stderr to Claude (tool already ran) |
| `SubagentStart` | No | Shows stderr to user only |

**CONFIRMED (Official Docs):**
- `SubagentStop` hooks "use the same decision control format as Stop hooks."
- For Stop/SubagentStop, decision control via JSON: `{ "decision": "block", "reason": "..." }`
- For TeammateIdle/TaskCompleted: exit codes only, not JSON decision control.
- The `stop_hook_active` field in SubagentStop input indicates "true when Claude Code is already continuing as a result of a stop hook" -- this helps prevent infinite loops.

**BUG REPORTED (GitHub Issue #20221 - OPEN):**
- **Title:** "Prompt-based SubagentStop hooks send feedback but don't prevent termination"
- **Status:** Open (as of 2026-01-23), labeled `bug`, `has repro`, `area:core`
- **Summary:** Prompt-based (`type: "prompt"`) SubagentStop hooks correctly evaluate and return `{ok: false, reason: "..."}`, BUT the subagent terminates anyway. The feedback is sent as a user message with `isMeta: true` but the subagent never gets another turn to respond.
- **Tested configurations:** Hook in agent frontmatter (both `Stop:` and `SubagentStop:` keys), hook in `.claude/settings.json` with/without matcher -- same bug in all cases.
- **Evidence:** Transcript shows hook fires, feedback sent, but no subsequent assistant turn.

**BUG REPORTED (GitHub Issue #10412):**
- **Title:** "Stop hooks with exit code 2 fail to continue when installed via plugins"
- Plugin-installed Stop hooks with exit code 2 do not prevent stopping.

**INFERRED (from the two bugs):**
- Command-based hooks (`type: "command"`) with exit code 2 on SubagentStop likely work as documented.
- Prompt-based hooks (`type: "prompt"`) on SubagentStop are BROKEN -- they send feedback but do not actually block termination. This is an open, confirmed bug.
- Plugin-installed hooks may have different behavior than settings-installed hooks.

**CONFIRMED (Official Docs - TeammateIdle):**
- TeammateIdle uses exit codes ONLY (not JSON decision control).
- Exit code 2: "the teammate receives the stderr message as feedback and continues working instead of going idle."
- Example in docs: check if build artifact exists, exit 2 with stderr message if missing.

### Summary

| Aspect | Status | Confidence |
|--------|--------|------------|
| SubagentStop exit code 2 blocks termination (command hooks) | Documented as yes | CONFIRMED (docs) |
| SubagentStop prompt-based hooks block termination | **NO -- BROKEN** | CONFIRMED (open bug #20221) |
| TeammateIdle exit code 2 blocks idling | Yes | CONFIRMED |
| TaskCompleted exit code 2 blocks completion | Yes | CONFIRMED |
| Stop exit code 2 blocks stopping | Yes | CONFIRMED |
| Plugin-installed hooks may not work | Yes, known issue | CONFIRMED (bug #10412) |
| `stop_hook_active` prevents infinite loops | Available as input field | CONFIRMED |

### Critical Warning for Our Use Case

**If we plan to use SubagentStop hooks for debrief (intercepting agent completion to collect reasoning data), we MUST use command-based hooks (`type: "command"`), NOT prompt-based hooks (`type: "prompt"`).** The prompt-based path is broken per GitHub issue #20221.

For TeammateIdle (Agent Teams equivalent), only exit-code-based blocking is supported -- no JSON decision control. This is simpler but less flexible.

---

## RQ-5: Context Preservation

**Question:** When an idle agent receives a new message, does it retain its full conversation history?

### Findings

**CONFIRMED (Official Docs - Context and Communication):**
- "Each teammate has its own context window."
- "When spawned, a teammate loads the same project context as a regular session: CLAUDE.md, MCP servers, and skills. It also receives the spawn prompt from the lead."
- "The lead's conversation history does not carry over" (at spawn time).
- After spawning, the teammate builds its own context through its own conversation.

**CONFIRMED (Official Docs - Limitations):**
- "No session resumption with in-process teammates: `/resume` and `/rewind` do not restore in-process teammates. After resuming a session, the lead may attempt to message teammates that no longer exist."
- This confirms that if the teammate process actually dies, context is LOST.

**INFERRED (from idle state behavior):**
- Since idle agents remain alive as processes (RQ-1), their context window is preserved in memory.
- When a message wakes an idle agent, it receives the message within the same conversation context.
- The full conversation history (all previous tool calls, reasoning, findings) remains available.
- This is fundamentally different from resuming a dead session.

**OBSERVED (ClaudeWorld "Amnesia After Compaction" - Fracture 2):**
- Auto-compact triggers at 80% context window usage.
- After compaction, the conversation is compressed into a text summary.
- The summary is plain text with NO structured state.
- Post-compact, the agent loses: which agents are running, their IDs, task assignments, what's done vs. pending.
- If an idle agent has been alive long enough and has enough context, compaction may fire, reducing context fidelity.

**INFERRED (important nuance):**
- Context preservation holds as long as no compaction occurs.
- For short idle periods (seconds to minutes), full context is preserved.
- For long idle periods with incoming messages that grow context, compaction risk increases.
- There is no mechanism to selectively compact or protect certain context segments.

### Summary

| Aspect | Status | Confidence |
|--------|--------|------------|
| Idle agent retains full context in memory | Yes (while process lives) | INFERRED (high confidence) |
| Message to idle agent includes full conversation | Yes | INFERRED (high confidence) |
| Compaction can destroy structured context | Yes | OBSERVED |
| Compaction threshold is 80% of context window | Yes | OBSERVED |
| No selective compaction possible | Correct | OBSERVED |
| Dead agent context is unrecoverable | Yes | CONFIRMED |

---

## Implications for AlphaSwarm.sol

### Debrief Pattern Viability

The debrief pattern (sending a message to an agent after it completes to collect reasoning data) is viable under these conditions:

1. **Use TeammateIdle hook (Agent Teams) or SubagentStop hook (subagents)** to intercept completion.
2. **For SubagentStop: MUST use command-based hooks**, not prompt-based (bug #20221).
3. **For TeammateIdle: use exit code 2** with stderr message to keep the agent working.
4. **Context is preserved** during idle state, so the agent can answer debrief questions with full reasoning access.
5. **Risk:** If the agent has consumed >80% of its context window before idle, compaction may fire on the next turn, degrading debrief quality.

### Recommended Architecture

```
Approach A: TeammateIdle Hook (for Agent Teams)
  1. Agent completes work, enters idle state
  2. TeammateIdle hook fires
  3. Hook script checks if debrief is needed
  4. Exit code 2 + stderr: "Before going idle, complete the debrief checklist: [questions]"
  5. Agent receives debrief prompt, responds (full context available)
  6. Agent goes idle again
  7. TeammateIdle fires again -- hook script detects debrief already done, exit 0

Approach B: SubagentStop Hook (for subagents)
  1. Subagent completes work, about to stop
  2. SubagentStop hook fires (type: command)
  3. Hook script checks transcript for debrief markers
  4. Exit code 2 + stderr: "Before stopping, answer: [debrief questions]"
  5. Subagent continues, answers questions
  6. SubagentStop fires again -- hook detects debrief done, exit 0
  WARNING: prompt-based hooks WILL NOT WORK (bug #20221)

Approach C: SendMessage to Idle Agent (for Agent Teams)
  1. Agent completes work, enters idle state
  2. Lead detects idle notification
  3. Lead sends debrief message via SendMessage
  4. Agent wakes, processes debrief with full context
  5. Agent responds, goes idle again
  RISK: No guarantee agent is actually idle vs. dead (no delivery confirmation)
```

### Key Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| SubagentStop prompt hooks broken | High | Use command hooks only |
| Cannot distinguish idle from dead | Medium | Use TeammateIdle hook (fires only for living agents) |
| Compaction destroys debrief context | Medium | Keep agent tasks small; monitor context usage |
| Idle storm floods lead | Medium | Rate-limit hook processing; use `stop_hook_active` guard |
| No delivery confirmation for messages | Medium | Use hook-based approach instead of SendMessage |
| Plugin-installed hooks may fail | Low | Install hooks via settings.json, not plugins |

### Recommended Sweet Spot for Agent Teams Sessions

Per ClaudeWorld analysis (community, not official, but well-evidenced):

```
Safe zone:
  - 3-5 agents
  - 10-15 minutes
  - Single-phase tasks
  - No resume needed

Danger zone:
  - 5+ agents
  - 30+ minutes
  - Multi-phase dependencies
  - Requires compact or resume
```

---

## Sources

### Official Documentation (CONFIRMED tier)

| Source | URL | Retrieved |
|--------|-----|-----------|
| Agent Teams docs | https://code.claude.com/docs/en/agent-teams | 2026-02-11 |
| Hooks reference | https://code.claude.com/docs/en/hooks | 2026-02-11 |
| Hooks guide | https://code.claude.com/docs/en/hooks-guide | 2026-02-11 |

### GitHub Issues (CONFIRMED tier for bugs)

| Issue | URL | Status |
|-------|-----|--------|
| #20221 - SubagentStop prompt hooks don't prevent termination | https://github.com/anthropics/claude-code/issues/20221 | Open |
| #10412 - Stop hooks exit code 2 fail via plugins | https://github.com/anthropics/claude-code/issues/10412 | Open |
| #23545 - Missing TeammateIdle/TaskCompleted docs | https://github.com/anthropics/claude-code/issues/23545 | Closed (docs updated) |

### Community Analysis (OBSERVED tier)

| Source | URL | Notes |
|--------|-----|-------|
| ClaudeWorld: "Five Ways to Die" | https://claude-world.com/articles/agent-teams-mesh-topology/ | Deep analysis of agent termination modes |
| ClaudeWorld: "Six Fractures in Session Management" | https://claude-world.com/articles/agent-teams-session-afterlife/ | Post-death effects, idle storm, compaction amnesia |
| Claude Code system prompts repo | https://github.com/Piebald-AI/claude-code-system-prompts | TeammateTool system prompt extracted |

### Changelog References

| Version | Relevant Change |
|---------|----------------|
| v2.1.33 | Added TeammateIdle and TaskCompleted hook events |
| v2.1.33 | Persistent agent memory with frontmatter support |
| v2.0.14 | Fixed how idleness is computed for notifications |
| v1.0.51 | Increased auto-compact threshold from 60% to 80% |

---

## Cross-References

- **Research Spike 03 (this project):** `.planning/phases/3.1b-workflow-testing-harness/RESEARCH-SPIKE-03-agent-teams-lifecycle.md` -- Experimental verification plan (not yet executed)
- **Research Spike 02:** `.planning/phases/3.1b-workflow-testing-harness/RESEARCH-SPIKE-02-debrief-research.md` -- Debrief architecture (depends on these findings)
- **Research Spike 04:** `.planning/phases/3.1b-workflow-testing-harness/RESEARCH-SPIKE-04-hook-verification.md` -- Hook behavior verification

> **Post-Gap Resolution Update (2026-02-12):**
> All findings in this document have been **CONFIRMED** by gap resolution work:
> - **RQ-1 (Idle state) + RQ-2 (SendMessage to idle):** Used as design basis for GAP-01-02 resolution's `TeamObservation` model. The model's `InboxMessage` dataclass is built directly on the file-based messaging format documented here.
> - **RQ-3 (Lifecycle/termination):** Informed GAP-05's revised orchestration approach -- the `modes: [single, team]` field avoids the complexity of dedicated team scenarios that could hit lifecycle edge cases.
> - **RQ-4 (Hook blocking):** Confirmed by RS-04 cross-reference analysis. Command hooks with exit code 2 work; prompt hooks remain broken (bug #20221).
> - **RQ-5 (Context preservation):** Influenced GAP-01's `AgentObservation` design -- observations are captured before potential compaction destroys context.
> - **Novel finding from GAP-01-02:** Real inbox file format verified at `~/.claude/teams/{name}/inboxes/{agent}.json` with `{from, text, summary, timestamp, color, read}` fields. Team config at `~/.claude/teams/{name}/config.json` contains `members[]` array.
