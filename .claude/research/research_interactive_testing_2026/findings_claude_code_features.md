# Claude Code Features Research: Interactive Agent Testing Framework

**Research Date:** 2026-03-01
**Coverage Period:** Late January 2026 through February 28, 2026
**Latest Version Found:** v2.1.63 (Feb 28, 2026)
**Confidence Level:** HIGH (cross-referenced official docs, GitHub releases, and community sources)

---

## Table of Contents

1. [Hook System Updates](#1-hook-system-updates)
2. [Agent Teams Improvements](#2-agent-teams-improvements)
3. [Worktree Isolation and Sandboxing](#3-worktree-isolation-and-sandboxing)
4. [Claude Agent SDK (Python + TypeScript)](#4-claude-agent-sdk-python--typescript)
5. [Transcript and Output Capture](#5-transcript-and-output-capture)
6. [Testing and Evaluation Ecosystem](#6-testing-and-evaluation-ecosystem)
7. [Version-by-Version Changelog Summary](#7-version-by-version-changelog-summary)
8. [Application to Interactive Testing Framework](#8-application-to-interactive-testing-framework)

---

## 1. Hook System Updates

### 1.1 Complete Hook Event Catalog (18 Events)

As of v2.1.63, Claude Code supports **18 hook lifecycle events**. The following is the complete list with version introduced:

| Event | Description | Matcher Support | Version |
|---|---|---|---|
| `SessionStart` | Session begins/resumes | `startup`, `resume`, `clear`, `compact` | Early |
| `SessionEnd` | Session terminates | `clear`, `logout`, `prompt_input_exit`, etc. | Early |
| `UserPromptSubmit` | User submits a prompt | No matcher | Early |
| `PreToolUse` | Before tool call executes (can block) | Tool name regex | Early |
| `PostToolUse` | After tool call succeeds | Tool name regex | Early |
| `PostToolUseFailure` | After tool call fails | Tool name regex | Early |
| `PermissionRequest` | Permission dialog appears | Tool name regex | Early |
| `Notification` | Claude Code sends notification | Notification type | Early |
| `Stop` | Claude finishes responding | No matcher | Early |
| `SubagentStart` | Subagent spawned | Agent type name | v2.1.43 |
| `SubagentStop` | Subagent finishes | Agent type name | Earlier |
| `TeammateIdle` | Agent team teammate about to go idle | No matcher | **v2.1.33** |
| `TaskCompleted` | Task being marked complete | No matcher | **v2.1.33** |
| `ConfigChange` | Configuration file modified | Config source type | **v2.1.49** |
| `WorktreeCreate` | Worktree created via `--worktree` or `isolation: "worktree"` | No matcher | **v2.1.50** |
| `WorktreeRemove` | Worktree removed (session exit or subagent finish) | No matcher | **v2.1.50** |
| `PreCompact` | Before context compaction | `manual`, `auto` | Recent |
| *(MCP tool events)* | MCP server tools appear as regular tools in PreToolUse/PostToolUse/etc. | `mcp__<server>__<tool>` | Recent |

**Source:** https://code.claude.com/docs/en/hooks

### 1.2 Four Hook Types

Claude Code now supports **four distinct hook execution types**:

#### a) Command Hooks (`type: "command"`)
Traditional shell command execution. Input via stdin JSON, output via exit codes + stdout/stderr.

```json
{
  "type": "command",
  "command": "jq -r '.tool_input.command' | xargs validate.sh",
  "timeout": 30
}
```

#### b) HTTP Hooks (`type: "http"`) -- NEW in v2.1.63
POST JSON payloads to HTTP endpoints. Receive JSON responses. Supports custom headers with env var interpolation via `allowedEnvVars`.

```json
{
  "type": "http",
  "url": "http://localhost:8080/hooks/tool-use",
  "headers": {
    "Authorization": "Bearer $MY_TOKEN"
  },
  "allowedEnvVars": ["MY_TOKEN"]
}
```

**Security (v2.1.51):** HTTP hooks now route through sandbox network proxy when sandboxing is enabled, enforcing domain allowlist. HTTP hooks are NOT supported for `SessionStart`/`Setup` events.

**Security (v2.1.51):** Fixed issue where HTTP hooks could interpolate arbitrary environment variables; now requires explicit `allowedEnvVars` list.

#### c) Prompt Hooks (`type: "prompt"`)
Send a prompt to a fast Claude model (Haiku by default) for single-turn yes/no evaluation. Returns `{"ok": true}` or `{"ok": false, "reason": "..."}`.

```json
{
  "type": "prompt",
  "prompt": "Check if all tasks are complete. If not, respond with {\"ok\": false, \"reason\": \"what remains\"}.",
  "model": "haiku"
}
```

- Uses `$ARGUMENTS` placeholder to inject hook input data
- Configurable model via `model` field
- Stop hook receives `model` parameter (v2.0.41)

#### d) Agent Hooks (`type: "agent"`)
Spawn a multi-turn subagent with tool access (Read, Grep, Glob) for deep verification. Same `ok`/`reason` response format as prompt hooks but with longer default timeout (60s) and up to 50 tool-use turns.

```json
{
  "type": "agent",
  "prompt": "Verify that all unit tests pass. Run the test suite and check results. $ARGUMENTS",
  "timeout": 120
}
```

**Key difference from prompt hooks:** Agent hooks can actually read files, search code, and run commands to verify conditions against the actual codebase state.

### 1.3 Hook Input/Output Enhancements

**`last_assistant_message` field (v2.1.50):**
Added to `Stop` and `SubagentStop` hook inputs. Provides the final assistant response text so hooks can access it WITHOUT parsing transcript files. This is critical for automated evaluation.

**`SubagentStop` fields (v2.0.42+):**
Includes `agent_id` and `agent_transcript_path` -- direct access to the subagent's transcript file path.

**`SubagentStart` (v2.1.43):**
New hook event when subagents initialize. Matcher filters by agent type.

**`stop_hook_active` field:**
Available in Stop hook input to prevent infinite loops when Stop hooks trigger continuation.

**PreToolUse context injection (v2.1.9):**
PreToolUse hooks can return `additionalContext` to inject information into the model's context.

**PreToolUse input modification (v2.0.10):**
PreToolUse hooks can modify tool inputs before execution.

### 1.4 Structured JSON Output

Hooks can return structured JSON for fine-grained control:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Use rg instead of grep"
  }
}
```

Permission decisions: `"allow"`, `"deny"`, `"ask"`.
PostToolUse/Stop: `{"decision": "block"}`.
TeammateIdle/TaskCompleted: Exit code 2 sends feedback and keeps the agent working.

---

## 2. Agent Teams Improvements

### 2.1 Core Architecture (v2.1.32+)

Agent Teams are a research preview (experimental flag required: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`).

**Components:**
- **Team Lead**: Main session that creates team, spawns teammates, coordinates
- **Teammates**: Independent Claude Code instances with own context windows
- **Shared Task List**: File-based coordination with three states (pending, in-progress, completed)
- **Mailbox**: JSON file-based messaging system between agents

**Storage:**
- Team config: `~/.claude/teams/{team-name}/config.json`
- Task list: `~/.claude/tasks/{team-name}/`

**Source:** https://code.claude.com/docs/en/agent-teams

### 2.2 Display Modes

- **In-process**: All teammates in main terminal. `Shift+Down` cycles through.
- **Split panes**: Each teammate gets own pane via tmux or iTerm2.
- **Auto**: Default; uses split panes if already in tmux, otherwise in-process.

### 2.3 Key Capabilities

- **Plan approval mode**: Teammates work in read-only plan mode until lead approves
- **Direct teammate messaging**: Send messages to any teammate directly
- **Self-claim tasks**: After finishing, teammates pick up next unassigned task
- **File-lock based task claiming**: Prevents race conditions
- **Task dependencies**: Blocked tasks automatically unblock when dependencies complete
- **Bulk agent kill (v2.1.53)**: `Ctrl+F` sends single aggregate notification

### 2.4 Agent Teams Hook Events

**`TeammateIdle` (v2.1.33):**
Fires when a teammate is about to go idle. Exit code 2 sends feedback and keeps teammate working. Critical for quality gates.

**`TaskCompleted` (v2.1.33):**
Fires when a task is being marked complete. Exit code 2 prevents completion and sends feedback. Enables post-task validation.

### 2.5 Agent Frontmatter Enhancements

**`memory` frontmatter (v2.1.33):**
Agents support persistent memory with user, project, or local scope.

**`isolation: worktree` in agent definitions (v2.1.50):**
Agents can declaratively specify worktree isolation in their frontmatter.

**`Task(agent_type)` restrictions (v2.1.33):**
Restrict which sub-agents can be spawned via `Task(agent_type)` syntax in agent `tools` frontmatter.

### 2.6 Memory Leak Fixes

- v2.1.50: Fixed memory leak where completed teammate tasks weren't garbage collected
- v2.1.50: Fixed memory leak where completed task state objects were never removed from AppState
- v2.1.63: Fixed memory leak where long-running teammates retained all messages after compaction
- v2.1.59: Improved memory usage in multi-agent sessions by releasing completed subagent task state

### 2.7 Known Limitations

- No session resumption with in-process teammates (`/resume` and `/rewind` don't restore)
- Task status can lag (teammates may fail to mark tasks completed)
- One team per session; no nested teams
- Lead is fixed for team lifetime
- Permissions set at spawn time for all teammates (can change individually after)
- Split panes require tmux or iTerm2

---

## 3. Worktree Isolation and Sandboxing

### 3.1 Declarative Worktree Isolation (v2.1.50)

Agents can now specify `isolation: worktree` in their frontmatter definition:

```yaml
---
name: refactor-agent
description: Handles large-scale refactoring tasks
isolation: worktree
---
```

Every time this agent runs, it automatically gets its own git worktree. This is stored in `.claude/worktrees/`.

**CLI flag (v2.1.49):** `--worktree` or `-w` flag for CLI sessions.

### 3.2 Worktree Hook Events (v2.1.50)

**`WorktreeCreate`:** Fires when a worktree is created. Can be used for custom VCS setup (e.g., jujutsu workspace).

**`WorktreeRemove`:** Fires when a worktree is removed (session exit or subagent finish). Can be used for cleanup.

Example for jujutsu VCS:
```json
{
  "WorktreeCreate": [{
    "hooks": [{
      "type": "command",
      "command": "input=$(cat); name=$(echo \"$input\" | jq -r '.name'); cwd=$(echo \"$input\" | jq -r '.cwd'); mkdir -p \"$cwd/.claude/worktrees\" && jj workspace add \"$cwd/.claude/worktrees/$name\" >/dev/null 2>&1 && echo \"$cwd/.claude/worktrees/$name\""
    }]
  }],
  "WorktreeRemove": [{
    "hooks": [{
      "type": "command",
      "command": "input=$(cat); wt=$(echo \"$input\" | jq -r '.worktree_path'); jj workspace forget \"$wt\" 2>/dev/null; rm -rf \"$wt\""
    }]
  }]
}
```

### 3.3 Worktree Config Sharing (v2.1.63)

Project configs and auto-memory are now shared across git worktrees of the same repository. This means agents in worktrees see the same CLAUDE.md and project settings.

### 3.4 CLAUDE_CODE_SIMPLE Mode (v2.1.50)

Extended to fully strip down: disables MCP tools, attachments, hooks, CLAUDE.md file loading, skills, session memory, custom agents, and CLAUDE.md token counting. Useful for creating minimal agent environments.

### 3.5 Sandbox Network Proxy (v2.1.51)

HTTP hooks are now routed through the sandbox network proxy when sandboxing is enabled, enforcing the domain allowlist.

---

## 4. Claude Agent SDK (Python + TypeScript)

### 4.1 Overview

The Claude Code SDK has been **renamed to Claude Agent SDK** (`pip install claude-agent-sdk` / `npm install @anthropic-ai/claude-agent-sdk`). It provides the same tools, agent loop, and context management that power Claude Code, available as a library.

**Python requires:** 3.10+
**GitHub:** https://github.com/anthropics/claude-agent-sdk-python
**PyPI:** https://pypi.org/project/claude-agent-sdk/

### 4.2 Two Execution Modes

#### `query()` -- Simple, One-Off Tasks

```python
import anyio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    async for message in query(
        prompt="Find and fix the bug in auth.py",
        options=ClaudeAgentOptions(allowed_tools=["Read", "Edit", "Bash"]),
    ):
        print(message)

anyio.run(main)
```

#### `ClaudeSDKClient` -- Interactive Sessions

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async with ClaudeSDKClient(options=options) as client:
    await client.query("Your prompt here")
    async for msg in client.receive_response():
        print(msg)
```

**Key difference:** `ClaudeSDKClient` additionally enables custom tools and hooks defined as Python functions, plus session reuse, interrupts, and continuous conversation.

### 4.3 Feature Comparison

| Feature | `query()` | `ClaudeSDKClient` |
|---|---|---|
| Session | Creates new each time | Reuses same session |
| Conversation | Single exchange | Multi-exchange |
| Streaming | Supported | Supported |
| Interrupts | Not supported | Supported |
| Hooks | Supported | Supported |
| Custom Tools | Supported | Supported |
| Continue Chat | No | Yes |

### 4.4 Custom Tools (In-Process SDK MCP Servers)

Define tools as Python functions without separate server processes:

```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions, ClaudeSDKClient

@tool("greet", "Greet a user", {"name": str})
async def greet_user(args):
    return {"content": [{"type": "text", "text": f"Hello, {args['name']}!"}]}

server = create_sdk_mcp_server(
    name="my-tools",
    version="1.0.0",
    tools=[greet_user]
)

options = ClaudeAgentOptions(
    mcp_servers={"tools": server},
    allowed_tools=["mcp__tools__greet"]
)
```

Benefits: No subprocess management, no IPC overhead, type safety, easier debugging.

### 4.5 SDK Hooks (Python Functions)

Hooks can be defined as Python functions in the SDK:

```python
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher

async def check_bash_command(input_data, tool_use_id, context):
    tool_name = input_data["tool_name"]
    tool_input = input_data["tool_input"]

    if tool_name != "Bash":
        return {}

    command = tool_input.get("command", "")
    if "foo.sh" in command:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Blocked pattern"
            }
        }
    return {}

options = ClaudeAgentOptions(
    allowed_tools=["Bash"],
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[check_bash_command]),
        ],
    }
)
```

### 4.6 Key ClaudeAgentOptions Fields

- `system_prompt`: Custom system prompt
- `max_turns`: Limit conversation turns
- `allowed_tools`: List of tools Claude can use (e.g., `["Read", "Edit", "Bash", "Skill"]`)
- `permission_mode`: `'acceptEdits'` for auto-accept file edits
- `cwd`: Working directory (string or Path)
- `mcp_servers`: Dict of MCP servers (in-process or external)
- `hooks`: Hook configuration dict
- `cli_path`: Custom Claude Code CLI path
- `setting_sources`: `["project", "user"]` to load filesystem settings

### 4.7 SDK Environment Variables (v2.1.51)

New SDK caller variables:
- `CLAUDE_CODE_ACCOUNT_UUID`
- `CLAUDE_CODE_USER_EMAIL`
- `CLAUDE_CODE_ORGANIZATION_UUID`

### 4.8 SDK Rate Limits (v2.1.45)

Added `SDKRateLimitInfo` and `SDKRateLimitEvent` types for programmatic rate limit handling.

### 4.9 SDK Budget Control

`--max-budget-usd` flag available for controlling costs in SDK sessions.

---

## 5. Transcript and Output Capture

### 5.1 SubagentStop Transcript Path

The `SubagentStop` hook input includes `agent_transcript_path` -- a direct filesystem path to the complete subagent transcript. Available since v2.0.42.

### 5.2 last_assistant_message (v2.1.50)

The `Stop` and `SubagentStop` hook inputs now include `last_assistant_message` -- the final assistant response text. This eliminates the need to parse transcript files for the most common case (capturing what the agent said).

### 5.3 Langfuse Integration

Full tracing integration available via Claude Code hooks + Langfuse CLI:

- Installs hook handlers that capture all Claude Code events
- Traces prompts, tool calls, reasoning, and outputs
- Links traces to git commits
- Monitors latency, costs, and quality across sessions

**Source:** https://langfuse.com/integrations/other/claude-code

### 5.4 LangSmith Integration

LangSmith (LangChain) also supports tracing Claude Code sessions:

- Full detailed logs of Claude Code operations
- Observation of tool calls, decisions, and outputs

**Source:** https://docs.smith.langchain.com/observability/how_to_guides/claude_code

### 5.5 Claude Agent SDK Tracing

The Claude Agent SDK supports OpenTelemetry-based tracing:

```python
# Via Langfuse
os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
os.environ["LANGSMITH_OTEL_ONLY"] = "true"
```

This enables full observability of SDK-driven agent sessions.

---

## 6. Testing and Evaluation Ecosystem

### 6.1 Promptfoo Claude Agent SDK Provider

Promptfoo has a dedicated Claude Agent SDK provider for running evaluations:

**Provider IDs:** `anthropic:claude-agent-sdk` or `anthropic:claude-code`

```yaml
providers:
  - id: anthropic:claude-agent-sdk
    config:
      allowed_tools: ["Read", "Edit", "Bash"]
      permission_mode: "acceptEdits"
      cwd: "/path/to/project"
      max_turns: 10
```

**Key capabilities:**
- Define custom subagents with specific tools and permissions
- Run evaluations against test datasets
- Compare agent behavior across models
- Score with LLM-as-judge or deterministic graders

**Source:** https://www.promptfoo.dev/docs/providers/claude-agent-sdk/

### 6.2 Promptfoo Agent Evaluation Guide

Promptfoo provides a dedicated guide for evaluating coding agents:

**Capability tiers:**
- Tier 0 (Text): Plain LLM, can generate code but can't read files
- Tier 1 (Agentic): Agent SDK, can read/write files, run commands, iterate

**Key differences in agent evals:**
- Non-determinism compounds (temperature affects every tool call)
- Intermediate steps matter (cost, latency, failure modes)
- Capability is gated by architecture (harness determines what's possible)

**Source:** https://www.promptfoo.dev/docs/guides/evaluate-coding-agents/

### 6.3 Langfuse Agent Skill Evaluation

Langfuse published a blog post (2026-02-26) on evaluating AI agent skills:

**Pipeline:**
1. Store user prompts as Dataset in Langfuse
2. Run experiments by spinning up coding agents via Claude Agent SDK
3. Trace agent behavior
4. Score output with LLM-as-judge
5. Iterate on skill definition

This is very close to AlphaSwarm's evaluation framework concept.

**Source:** https://langfuse.com/blog/2026-02-26-evaluate-ai-agent-skills

### 6.4 MLflow + Claude Agent SDK

MLflow supports auto-logging for Claude Agent SDK sessions:

- Prototype agent with SDK
- Instrument with MLflow for tracing
- Evaluate with MLflow's evaluation framework

**Source:** https://mlflow.org/blog/mlflow-autolog-claude-agents-sdk

### 6.5 General Agent Evaluation (Academic)

A recent arXiv paper (Feb 2026) proposes the **Exgentic** framework for general-purpose agent evaluation, benchmarking Claude Code among other systems.

**Source:** https://arxiv.org/html/2602.22953v1

---

## 7. Version-by-Version Changelog Summary

### v2.1.63 (Feb 28, 2026) -- LATEST
- HTTP hooks (POST JSON to URL, receive JSON back)
- `/simplify` and `/batch` bundled slash commands
- Project configs + auto memory shared across worktrees
- `ENABLE_CLAUDEAI_MCP_SERVERS=false` env var
- 10+ memory leak fixes (hooks config, permission handler, bash prefix cache, MCP tool/resource cache, git root detection, JSON parsing, WebSocket transport, IDE host IP cache, file count cache, long-running teammates)
- Fixed `/clear` not resetting cached skills

### v2.1.59 (Feb 26, 2026)
- Auto-memory: Claude automatically saves useful context
- `/copy` with interactive code block picker
- Smarter per-subcommand bash prefix suggestions
- Memory improvements for multi-agent sessions

### v2.1.53 (Feb 25, 2026)
- Bulk agent kill (`Ctrl+F`) with aggregate notification
- Fixed `--worktree` sometimes being ignored on first launch
- Multiple Windows stability fixes

### v2.1.51 (Feb 24, 2026)
- `claude remote-control` subcommand for external builds
- HTTP hooks routed through sandbox network proxy
- Security fix: HTTP hooks env var interpolation requires `allowedEnvVars`
- Security fix: `statusLine`/`fileSuggestion` hook commands required workspace trust
- SDK caller environment variables
- Tool results >50K chars persisted to disk (was 100K)

### v2.1.50 (Feb 21, 2026)
- **WorktreeCreate/WorktreeRemove hook events**
- **`isolation: worktree` in agent definitions**
- **`last_assistant_message` in Stop/SubagentStop hook inputs**
- CLAUDE_CODE_SIMPLE extended (disables MCP, attachments, hooks, CLAUDE.md)
- LSP `startupTimeout` configuration
- Massive memory leak fix wave (6+ separate fixes)

### v2.1.49 (Prior)
- `--worktree` (`-w`) CLI flag
- `ConfigChange` hook event

### v2.1.45 (Prior)
- SDK rate limit types (`SDKRateLimitInfo`, `SDKRateLimitEvent`)

### v2.1.43 (Prior)
- `SubagentStart` hook event

### v2.1.33 (Feb 15, 2026)
- **TeammateIdle and TaskCompleted hook events**
- **`memory` frontmatter for agents**
- **Task(agent_type) sub-agent restrictions**
- Plugin name in skill descriptions

### v2.1.32 (Prior)
- Agent Teams research preview launch

---

## 8. Application to Interactive Testing Framework

### 8.1 Directly Applicable Features for AlphaSwarm Evaluation

#### A. Claude Agent SDK for Programmatic Agent Spawning

**Feature:** `query()` and `ClaudeSDKClient` from `claude-agent-sdk`

**Application:** Instead of spawning Agent Teams via interactive Claude Code sessions (which suffer from auto-update binary staleness), use the Python SDK to programmatically spawn evaluation agents:

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def run_evaluation(contract_path: str, prompt: str):
    options = ClaudeAgentOptions(
        allowed_tools=["Bash", "Read"],  # Restrict to CLI tools only
        cwd=contract_path,               # Isolate to contract directory
        max_turns=30,                     # Bound execution
        system_prompt="You are a security auditor...",
    )

    transcript = []
    async for message in query(prompt=prompt, options=options):
        transcript.append(message)

    return transcript
```

**Advantages over current approach:**
- No auto-update binary staleness problem
- Programmatic control of allowed_tools (true tool restriction, not prompt-based)
- Direct transcript capture via message iterator
- Budget control via `--max-budget-usd`
- No need for TeamCreate/SendMessage coordination overhead

#### B. SDK Hooks for Evaluation Observation

**Feature:** Python-function hooks in SDK

**Application:** Define hooks that capture every tool call, every reasoning step, in real-time:

```python
evaluation_log = []

async def observe_tool_use(input_data, tool_use_id, context):
    evaluation_log.append({
        "event": "tool_use",
        "tool": input_data["tool_name"],
        "input": input_data["tool_input"],
        "timestamp": time.time()
    })
    return {}  # Allow all

async def observe_stop(input_data, tool_use_id, context):
    evaluation_log.append({
        "event": "stop",
        "last_message": input_data.get("last_assistant_message", ""),
    })
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PostToolUse": [HookMatcher(matcher=".*", hooks=[observe_tool_use])],
        "Stop": [HookMatcher(hooks=[observe_stop])],
    }
)
```

This replaces the need for transcript file parsing entirely.

#### C. Custom MCP Tools for Evaluation Boundaries

**Feature:** In-process SDK MCP servers via `@tool` decorator

**Application:** Create custom `build-kg` and `query` tools that wrap the real CLI but add observation:

```python
@tool("build_kg", "Build knowledge graph from Solidity contract", {"contract_path": str})
async def observed_build_kg(args):
    # Run real CLI
    result = subprocess.run(["uv", "run", "alphaswarm", "build-kg", args["contract_path"]], capture_output=True)

    # Record observation
    evaluation_log.append({"event": "build_kg", "contract": args["contract_path"], "success": result.returncode == 0})

    return {"content": [{"type": "text", "text": result.stdout}]}
```

This gives the agent ONLY the tools you define, with full observation.

#### D. Worktree Isolation for Clean Agent Environments

**Feature:** `isolation: worktree` + `WorktreeCreate`/`WorktreeRemove` hooks

**Application:** Define evaluation agents with declarative worktree isolation:

```yaml
---
name: evaluation-auditor
description: Security auditor for evaluation
isolation: worktree
tools: ["Bash", "Read"]
---
```

Each evaluation run gets its own git worktree automatically. Use `WorktreeCreate` hooks to set up the evaluation environment (copy contract files, install dependencies) and `WorktreeRemove` hooks to capture results before cleanup.

#### E. TeammateIdle + TaskCompleted for Quality Gates

**Feature:** These hook events fire when teammates go idle or complete tasks

**Application:** Use `TeammateIdle` to inject follow-up questions ("WHY did you reach this conclusion?") and `TaskCompleted` to validate output before accepting:

```json
{
  "TaskCompleted": [{
    "hooks": [{
      "type": "agent",
      "prompt": "Review the completed task output. Verify: 1) Agent used build-kg CLI, 2) Agent queried the graph, 3) Conclusions cite graph evidence. If any are missing, return {\"ok\": false, \"reason\": \"Missing: ...\"}"
    }]
  }]
}
```

#### F. last_assistant_message for Transcript-Free Evaluation

**Feature:** Stop/SubagentStop hooks now include `last_assistant_message`

**Application:** Capture the agent's final output without parsing transcript files:

```python
async def capture_evaluation_result(input_data, tool_use_id, context):
    final_output = input_data.get("last_assistant_message", "")
    # Score the output directly
    evaluation_results.append({
        "output": final_output,
        "agent_id": input_data.get("session_id"),
    })
    return {}
```

#### G. CLAUDE_CODE_SIMPLE for Minimal Agent Environments

**Feature:** Extended CLAUDE_CODE_SIMPLE mode (v2.1.50)

**Application:** When spawning evaluation agents, use CLAUDE_CODE_SIMPLE to strip all project context:
- Disables MCP tools, attachments, hooks, CLAUDE.md loading
- Creates a truly "blank slate" agent that cannot leak project knowledge
- Solves the context isolation problem that plagued Plan 12

### 8.2 Architecture Recommendation

Based on these findings, the optimal architecture for the interactive testing framework would be:

```
Evaluation Runner (Python)
    |
    +-- Claude Agent SDK (query() or ClaudeSDKClient)
    |       |
    |       +-- allowed_tools: custom MCP tools only
    |       +-- cwd: isolated contract directory
    |       +-- hooks: Python-function observers
    |       +-- system_prompt: evaluation-specific (no project context)
    |       +-- max_turns: bounded
    |       |
    |       +-- Custom MCP Server (in-process)
    |               +-- build_kg tool (wraps CLI, logs usage)
    |               +-- query tool (wraps CLI, logs queries + results)
    |               +-- read_contract tool (wraps Read, restricts to contract dir)
    |
    +-- Observation Layer
    |       +-- Hook-based tool use logging
    |       +-- last_assistant_message capture
    |       +-- Timing and cost tracking
    |
    +-- Scoring Pipeline
            +-- Graph value scoring
            +-- Reasoning decomposition
            +-- Dual-evaluator assessment
```

**This approach eliminates:**
1. Auto-update binary staleness (SDK manages its own lifecycle)
2. Context leakage (custom tools + restricted cwd + no CLAUDE.md)
3. Transcript parsing (SDK hooks capture everything in-process)
4. Shared graph state (each agent runs in isolated cwd with its own build)
5. Agent Teams coordination overhead (direct programmatic control)

### 8.3 Key URLs and References

| Resource | URL |
|---|---|
| Claude Code Releases | https://github.com/anthropics/claude-code/releases |
| Claude Code CHANGELOG | https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md |
| Hooks Reference (Official) | https://code.claude.com/docs/en/hooks |
| Hooks Guide (Official) | https://code.claude.com/docs/en/hooks-guide |
| Agent Teams (Official) | https://code.claude.com/docs/en/agent-teams |
| Agent SDK Python (GitHub) | https://github.com/anthropics/claude-agent-sdk-python |
| Agent SDK Python (PyPI) | https://pypi.org/project/claude-agent-sdk/ |
| Agent SDK Docs | https://docs.claude.com/en/docs/agent-sdk/overview |
| Agent SDK Python Reference | https://docs.claude.com/en/api/agent-sdk/python |
| Custom Tools (SDK) | https://docs.claude.com/en/api/agent-sdk/custom-tools |
| Promptfoo Agent SDK Provider | https://www.promptfoo.dev/docs/providers/claude-agent-sdk/ |
| Promptfoo Agent Eval Guide | https://www.promptfoo.dev/docs/guides/evaluate-coding-agents/ |
| Langfuse Claude Code Tracing | https://langfuse.com/integrations/other/claude-code |
| Langfuse Agent SDK Integration | https://langfuse.com/integrations/frameworks/claude-agent-sdk |
| Langfuse Agent Skill Eval Blog | https://langfuse.com/blog/2026-02-26-evaluate-ai-agent-skills |
| MLflow + Claude Agent SDK | https://mlflow.org/blog/mlflow-autolog-claude-agents-sdk |
| Headless Mode (Official) | https://code.claude.com/docs/en/headless |
| Worktree Guide | https://www.verdent.ai/guides/claude-code-worktree-setup-guide |
| Autonomy Blog Post | https://www.anthropic.com/news/enabling-claude-code-to-work-more-autonomously |
