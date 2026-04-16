# GAP-02: SendMessage to Idle Agent Viability

**Created by:** improve-phase
**Source:** P1-IMP-02
**Priority:** HIGH
**Status:** resolved
**depends_on:** []
**Researched:** 2026-02-18

## Question

Can you send a message to an idle teammate agent (via SendMessage) and have it wake up and respond? Is this a reliable mechanism for agent debriefing?

## Context

P1-IMP-02 identifies that the debrief protocol's Layer 1 (PRIMARY layer) depends on SendMessage-to-idle-agent working. The stub returns `success=False`. If this doesn't work, the debrief strategy collapses to Layer 4 (keyword-matching transcript fallback, confidence=0.0), degrading 3.1c-05, 3.1c-07, and all investigation/orchestration evaluations.

Affected plans: 3.1c-05 (Debrief Protocol), 3.1c-07 (Evaluator), 3.1c-09/10/11.

## Research Approach

- Search Claude Code documentation for SendMessage behavior with idle agents
- Check Agent Teams documentation for teammate lifecycle
- Look for official examples of post-task agent communication
- Authoritative: Claude Code docs, Agent Teams guide

## Findings

### Source 1: SendMessage Tool Description (AUTHORITATIVE — in-session tool definition)

The SendMessage tool description provided to every Claude Code session explicitly documents idle-agent messaging behavior. Verbatim quotes:

> "Idle teammates can receive messages. Sending a message to an idle teammate wakes them up and they will process it normally."

> "A teammate going idle immediately after sending you a message does NOT mean they are done or unavailable. Idle simply means they are waiting for input."

> "Do not treat idle as an error. A teammate sending a message and then going idle is the normal flow — they sent their message and are now waiting for a response."

**Confidence: HIGH.** This is the canonical tool definition that Claude Code actually uses at runtime. It is first-party authoritative documentation.

### Source 2: Official Agent Teams Documentation (code.claude.com/docs/en/agent-teams)

The official docs confirm the messaging architecture:

- **Automatic message delivery:** "when teammates send messages, they're delivered automatically to recipients. The lead doesn't need to poll for updates."
- **Idle notifications:** "when a teammate finishes and stops, they automatically notify the lead."
- **Architecture includes a Mailbox component** described as: "Messaging system for communication between agents."
- **Context and Communication section** confirms each teammate has its own context window and messages are automatically delivered.

The docs do NOT explicitly document the "send to idle agent wakes them up" behavior in the agent-teams page itself — that behavior is documented in the SendMessage tool definition (Source 1).

**Confidence: HIGH.** Official Anthropic documentation.

### Source 3: Known Bug — Idle Notification Timing (anthropics/claude-code #24246)

A filed bug report (labeled `bug`, `has repro`, `area:core`, open as of 2026-02-08) documents a real-world problem with idle notifications:

**Problem:** Idle notifications arrive with a delay, causing the team lead to misinterpret the agent's state. The timeline mismatch is:
1. Teammate works, sends status update, ends turn (triggers idle notification)
2. Lead receives status update, responds
3. Idle notification finally arrives (delayed), making it look like the teammate went idle *after* receiving the response

**Impact on debrief design:** This means the idle-notification signal is unreliable for timing purposes. The lead cannot use idle notifications to determine *when* an agent actually became idle. However, this does NOT affect SendMessage delivery — the bug is about notification *ordering*, not message delivery failure.

**Confidence: HIGH.** First-party bug report with detailed reproduction on the anthropics/claude-code repository.

### Source 4: Official Limitations Section (code.claude.com/docs/en/agent-teams)

The documented limitations are:
- **No session resumption with in-process teammates**: `/resume` and `/rewind` do not restore in-process teammates. After resuming, the lead may attempt to message teammates that no longer exist.
- **Task status can lag**: teammates sometimes fail to mark tasks as completed.
- **Shutdown can be slow**: teammates finish their current request/tool call before shutting down.
- **No nested teams**: teammates cannot spawn their own teams.
- **One team per session.**

**Critical finding:** None of the listed limitations mention SendMessage-to-idle-agent being unreliable or unsupported. The only message-delivery caveat is the session-resumption case (teammate no longer exists).

**Confidence: HIGH.** Official docs.

### Source 5: TeammateIdle Hook (code.claude.com/docs/en/hooks)

The hooks documentation confirms that `TeammateIdle` is a supported hook event. When a teammate is about to go idle, the hook fires. Importantly, exit code 2 from a TeammateIdle hook "sends feedback and keeps the teammate working." This confirms that:

1. The idle state is a real, well-defined state in the Agent Teams lifecycle
2. An idle teammate CAN be kept working (via hook feedback)
3. The platform explicitly supports intercepting the idle transition

**Confidence: HIGH.** Official hooks reference documentation.

### Source 6: Community Validation (multiple Exa sources)

Multiple blog posts and tutorials from Feb 2026 confirm that Agent Teams messaging works as documented. The Reddit walkthrough, alexop.dev post, and Medium articles all describe lead-to-teammate messaging as functional. No source reports SendMessage-to-idle-agent as broken.

**Confidence: MEDIUM-HIGH.** Multiple independent community sources agreeing.

## Synthesis

### Core Answer: YES, SendMessage to idle agents works and is officially supported.

The evidence is unambiguous:

| Evidence | What It Shows | Confidence |
|----------|---------------|------------|
| Tool definition | "Sending a message to an idle teammate wakes them up" | HIGH |
| Official docs | Mailbox architecture, automatic delivery | HIGH |
| Bug #24246 | Messages DO deliver; only notification timing is buggy | HIGH |
| Hooks reference | TeammateIdle hook can keep agents working | HIGH |
| Limitations section | No mention of message delivery failure | HIGH |
| Community | No reports of broken idle-agent messaging | MEDIUM-HIGH |

### Caveats and Risks

1. **Session resumption breaks messaging.** If the session is interrupted and resumed, in-process teammates are NOT restored. Any SendMessage to a non-existent teammate will fail. This is documented officially.

2. **Idle notification timing is unreliable.** Bug #24246 shows idle notifications can arrive out of order. If the debrief protocol relies on "wait for idle notification, then send debrief questions," the timing may be wrong. The agent might still be processing when the idle notification arrives.

3. **Agent Teams is experimental.** The feature is behind `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` flag. Behavior may change.

4. **No guaranteed response time.** The docs say the teammate "will process it normally" but don't guarantee when or how quickly. The teammate processes the message on its next turn.

5. **Context window limits.** A teammate that has been working for a long time may have a nearly-full context window. The debrief questions add to that context. If the window is exhausted, the response may be truncated or the agent may fail.

## Recommendation

**Verdict: SendMessage-to-idle-agent is VIABLE as the primary debrief mechanism (Layer 1).** Implement it with the following design constraints:

### 1. Keep the 4-layer cascade — it is correct

The existing cascade design (SendMessage > Hook Gate > Transcript > Skip) is the right architecture. The research confirms Layer 1 should work in live execution, but the fallback layers protect against the real failure modes (session resumption, context exhaustion, experimental-feature instability).

### 2. Implement Layer 1 (SendMessage debrief) for live execution only

The current stub correctly returns `success=False` in simulated mode. For live (headless/interactive) execution:

```python
def attempt_send_message_layer(agent_name, questions, **kwargs):
    simulated = kwargs.get("simulated", True)
    if simulated:
        return LayerResult(layer_name="send_message", success=False,
                           error="Simulated mode -- no live agent to message")

    # Live mode: send debrief questions via SendMessage
    # 1. Format questions as a single debrief prompt
    # 2. Send via SendMessage to the (possibly idle) teammate
    # 3. Wait for response (teammate wakes up automatically)
    # 4. Parse structured response
    ...
```

### 3. Do NOT rely on idle notifications for debrief timing

Given bug #24246, do not use idle notifications as the trigger for sending debrief questions. Instead:
- **Option A (preferred):** Use the `TaskCompleted` hook to trigger debrief. When the task is marked complete, the hook fires and the debrief protocol sends questions immediately.
- **Option B:** Use `TeammateIdle` hook with exit code 2 to intercept the idle transition and inject debrief questions before the agent fully stops.
- **Option C (simplest):** After the orchestrator (team lead) receives the agent's final status message, immediately send debrief questions via SendMessage. Do not wait for or depend on idle notifications.

### 4. Design debrief questions for single-turn response

Since the teammate processes the message "normally" on its next turn, structure the debrief as a single prompt that can be answered in one response. Do not design a multi-turn debrief conversation — that adds complexity and failure modes.

### 5. Add timeout and fallback

If the SendMessage debrief does not receive a response within a reasonable timeout (e.g., 60-120 seconds), fall through to Layer 2 (hook gate) or Layer 3 (transcript analysis). This handles:
- Teammate that has been terminated
- Context window exhaustion
- Experimental feature instability

### 6. Guard against session resumption

Before sending a debrief message, verify the teammate still exists by checking the team config file at `~/.claude/teams/{team-name}/config.json`. If the member list does not include the target agent, skip directly to Layer 2.

### Impact on Plan 3.1c-05

The debrief protocol design is **validated**. No architectural changes needed. The implementation priorities are:

1. **Phase 1 (now):** Keep stub behavior for simulated mode. Focus on Layers 2-3 which work today.
2. **Phase 2 (with live execution):** Implement Layer 1 using SendMessage. Use TaskCompleted hook as the trigger, not idle notifications.
3. **Phase 3 (hardening):** Add timeout, teammate-existence checks, and context-window guards.

### Confidence Assessment

| Claim | Confidence | Basis |
|-------|------------|-------|
| SendMessage to idle agents works | **HIGH** | Tool definition + official docs + no contrary evidence |
| Idle notifications have timing bugs | **HIGH** | Bug #24246 with reproduction steps |
| Session resumption breaks messaging | **HIGH** | Official limitations documentation |
| Feature stability long-term | **MEDIUM** | Experimental flag, may change |
| Single-turn debrief is sufficient | **MEDIUM** | Architectural inference, not empirically tested |

## Sources

### Primary (HIGH confidence)
- SendMessage tool definition — in-session Claude Code tool schema (canonical)
- https://code.claude.com/docs/en/agent-teams — Official Agent Teams documentation
- https://code.claude.com/docs/en/hooks — Official Hooks reference (TeammateIdle, TaskCompleted)

### Secondary (HIGH confidence)
- https://github.com/anthropics/claude-code/issues/24246 — Bug report on idle notification timing

### Tertiary (MEDIUM-HIGH confidence)
- https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/ — Community walkthrough
- https://www.reddit.com/r/ClaudeCode/comments/1qz8tyy/ — Community setup guide
- https://medium.com/@kargarisaac/agent-teams-with-claude-code-and-claude-agent-sdk-e7de4e0cb03e — Tutorial with practical examples
