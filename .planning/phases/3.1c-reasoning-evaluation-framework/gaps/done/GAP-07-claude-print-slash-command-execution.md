# GAP-07: Claude --print Slash Command Execution

**Created by:** improve-phase
**Source:** P2-IMP-18
**Priority:** HIGH
**Status:** RESOLVED
**depends_on:** [GAP-01]

## Question

Does `claude --print -p "Run /vrs-audit on tests/contracts/ReentrancyClassic.sol"` actually execute the skill and produce meaningful output? Can slash commands be invoked programmatically via `claude --print`?

## Context

P2-IMP-18 identifies the elephant in the room: the evaluation framework needs to programmatically execute workflows, but workflows are slash commands running inside Claude Code. If `claude --print` can't invoke skills, the entire "real workflow execution" model needs rethinking. Options include: headless skill execution, interactive sessions with hooks, or scripted prompts.

Affected plans: 3.1c-09/10/11 (workflow test suites), 3.1c-08 (runner execution model).

## Research Approach

- Search Claude Code documentation for `--print` mode capabilities
- Check if skills/slash commands work in non-interactive mode
- Look for `claude -p` examples with skill invocation
- Test whether tools are available in `--print` mode
- Sources: Claude Code docs, GitHub issues/discussions

## Findings

**Confidence: HIGH** (based on official Anthropic documentation at code.claude.com, Feb 2026)

### Critical Discovery: Slash Commands Do NOT Work in `-p` Mode

The official Claude Code documentation at `code.claude.com/docs/en/headless` states explicitly:

> **"User-invoked skills like `/commit` and built-in commands are only available in interactive mode. In `-p` mode, describe the task you want to accomplish instead."**

This is the definitive answer. The `/slash-command` invocation syntax is an interactive-mode feature. You cannot write `claude -p "/vrs-audit contracts/"` and expect the skill to load.

### However: Skills ARE Available in `-p` Mode (via natural language)

Skills are **loaded into context** in `-p` mode -- they just cannot be invoked with `/` syntax. The mechanism works as follows:

1. **Skills with `disable-model-invocation: false` (the default)** are available for Claude to load automatically when the prompt is relevant to the skill's `description` field.
2. **Skills with `disable-model-invocation: true`** are NOT available in `-p` mode at all -- they require explicit `/name` invocation which is interactive-only.
3. **CLAUDE.md is loaded** in `-p` mode, providing project context.
4. **Subagents defined in `.claude/agents/`** are available in `-p` mode (via the Task tool).
5. **MCP servers** are available in `-p` mode.

Therefore, the correct invocation pattern is:

```bash
# WRONG -- slash commands don't work in -p mode
claude -p "/vrs-audit tests/contracts/ReentrancyClassic.sol"

# RIGHT -- describe the task, let Claude load the skill automatically
claude -p "Perform a security audit of tests/contracts/ReentrancyClassic.sol following the vrs-audit workflow"
```

For this to work, the skill's `description` field must be rich enough for Claude to match it to the prompt. The skill must have `disable-model-invocation: false` (or omit the field, since false is the default).

### Reliability Concern: Skill Auto-Loading Is Probabilistic

Multiple community reports (HN discussion, Reddit) confirm that Claude does not always load skills unprompted. The model decides based on description matching, which is non-deterministic. Mitigations:

1. **Explicit skill mention in prompt**: "Follow the vrs-audit skill instructions" increases loading probability.
2. **`--append-system-prompt`**: Inject "Always load the vrs-audit skill for this task" into the system prompt.
3. **`--system-prompt-file`**: Use a file that references the skill content directly.
4. **Direct content injection**: Instead of relying on skill auto-loading, pipe the skill content into the prompt or use `--append-system-prompt-file` pointing to the skill's SKILL.md.

### Agent SDK Alternative (Python/TypeScript)

The Claude Agent SDK (`claude-agent-sdk` / `@anthropic-ai/claude-agent-sdk`) provides programmatic control with `query()`:

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt="Perform a security audit of tests/contracts/ReentrancyClassic.sol",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Grep", "Glob", "Bash", "Task"],
        permission_mode="bypassPermissions",
        setting_sources=["project"],  # Load .claude/skills/, CLAUDE.md, etc.
        max_turns=30,
    ),
):
    ...
```

Key SDK capabilities:
- `setting_sources=["project"]` loads skills, CLAUDE.md, agents, and MCP servers from the project directory.
- `agents` parameter can define subagents programmatically (inline, no files needed).
- `allowed_tools` controls what the agent can do.
- `permission_mode="bypassPermissions"` removes all prompts (required for headless).
- Structured output via `json_schema` parameter.
- ~12-second startup overhead per `query()` call.

### Agent Teams: NOT Available in `-p` Mode

Agent Teams are an **interactive-mode feature**. Key constraints:

1. **Experimental and disabled by default** -- requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
2. **Requires interactive session** -- the team lead must be an interactive Claude Code session. Teammates are spawned as separate Claude Code instances (either in-process or in tmux panes).
3. **No nested teams** -- teammates cannot spawn their own teams.
4. **`-p` mode is single-shot** -- it runs one query and exits, which is incompatible with the persistent team coordination model.

The SDK article by Isaac Kargar (Feb 2026) suggests Agent Teams may be usable from the Agent SDK using `ClaudeSDKClient` (stateful, bidirectional), but this is unconfirmed in official docs and would require a persistent session, not a one-shot `query()`.

**For evaluation purposes**: Workflows that use Agent Teams (e.g., `/vrs-audit` with attacker/defender/verifier) CANNOT be run via `claude -p`. They require either:
- An interactive session with hooks to observe behavior
- The Agent SDK with `ClaudeSDKClient` for stateful multi-turn interaction
- Decomposition into single-agent subworkflows that CAN run in `-p` mode

### Subagents: Available in `-p` Mode

Unlike Agent Teams, subagents work in `-p` mode:

- The `Task` tool is available, allowing Claude to spawn subagents.
- Subagents from `.claude/agents/` are discovered when `setting_sources=["project"]` is set (SDK) or when run from the project directory (CLI).
- The `--agents` CLI flag can define subagents inline as JSON.
- Subagents report back to the main agent; they don't communicate peer-to-peer.

```bash
claude -p "Use the vrs-attacker subagent to analyze tests/contracts/ReentrancyClassic.sol for exploit paths" \
  --allowedTools "Read,Grep,Glob,Bash,Task" \
  --agents '{"vrs-attacker": {"description": "Construct exploit paths", "prompt": "You are a security attacker agent...", "tools": ["Read","Grep","Glob"]}}'
```

### Summary Table: Feature Availability in `-p` Mode

| Feature | Available in `-p`? | Notes |
|---------|-------------------|-------|
| Tools (Read, Bash, etc.) | YES | Use `--allowedTools` to auto-approve |
| CLAUDE.md loading | YES | Loaded from working directory |
| Skills (auto-load) | YES* | Only if `disable-model-invocation: false`; probabilistic |
| Skills (`/slash` invocation) | **NO** | Interactive-only |
| Subagents (Task tool) | YES | From `.claude/agents/` or `--agents` flag |
| Agent Teams | **NO** | Requires interactive session |
| MCP servers | YES | Configured in settings or via `--mcp-*` flags |
| Hooks | YES | Fire normally in `-p` mode |
| `--json-schema` structured output | YES | Enforces output format |
| Session continuation (`--continue`) | YES | Can chain multiple `-p` calls |

## Recommendation

### Workflow Execution Strategy for the Evaluation Framework

Categorize the 51 shipped workflows into three tiers based on execution complexity:

#### Tier 1: Single-Agent Workflows (35+ workflows) -- Use `claude -p`

Most shipped skills (tool skills, bead management, health checks, pattern verification) are single-agent workflows. Execute via:

```bash
claude -p "Perform [workflow description] on [target]" \
  --allowedTools "Read,Grep,Glob,Bash,Task,Write,Edit" \
  --append-system-prompt "You MUST follow the vrs-[skill-name] skill instructions for this task." \
  --output-format json \
  --max-turns 20 \
  --max-budget-usd 2.00
```

**Reliability enhancement**: Do NOT rely on skill auto-loading alone. Use `--append-system-prompt-file` pointing to the skill's SKILL.md to guarantee the instructions are in context:

```bash
claude -p "Audit tests/contracts/ReentrancyClassic.sol" \
  --append-system-prompt-file .claude/skills/vrs-audit/SKILL.md \
  --allowedTools "Read,Grep,Glob,Bash,Task,Write,Edit" \
  --output-format json
```

This eliminates the probabilistic skill-matching problem entirely by injecting the skill content directly into the system prompt.

#### Tier 2: Subagent-Orchestrated Workflows (10-12 workflows) -- Use `claude -p` with `--agents`

Workflows like `/vrs-verify`, `/vrs-investigate`, `/vrs-debate` that use attacker/defender/verifier subagents CAN work in `-p` mode because subagents (Task tool) are available. The main agent orchestrates; subagents run sequentially within the session.

```bash
claude -p "Investigate the reentrancy vulnerability in ReentrancyClassic.sol using attacker and defender agents" \
  --append-system-prompt-file .claude/skills/vrs-investigate/SKILL.md \
  --allowedTools "Read,Grep,Glob,Bash,Task,Write,Edit" \
  --agents '{
    "vrs-attacker": {"description":"Construct exploit paths for vulnerabilities","prompt":"...","tools":["Read","Grep","Glob"]},
    "vrs-defender": {"description":"Find guards and mitigations","prompt":"...","tools":["Read","Grep","Glob"]}
  }' \
  --output-format json \
  --max-turns 40
```

**Key insight**: Subagents in `-p` mode run sequentially (main spawns attacker, gets result, spawns defender, gets result, synthesizes). This is NOT the same as Agent Teams with parallel peer communication. For evaluation purposes this is acceptable -- we evaluate reasoning quality, not parallelism.

#### Tier 3: Agent Team Workflows (3-5 workflows) -- Use Agent SDK or Decompose

The full `/vrs-audit` orchestration with parallel attacker/defender/verifier teams CANNOT run in `-p` mode. Two options:

**Option A (Recommended): Decompose into Tier 2 subworkflows.**
Instead of testing the full Agent Team orchestration, test each role independently:
- Test attacker reasoning: `claude -p "As the attacker agent, find exploit paths in X.sol"`
- Test defender reasoning: `claude -p "As the defender agent, identify mitigations in X.sol"`
- Test verifier reasoning: `claude -p "Given these findings [attacker output], verify correctness"`
- Test orchestration logic separately (unit tests on the skill instructions)

**Option B (Advanced): Use the Claude Agent SDK with `ClaudeSDKClient`.**

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

options = ClaudeAgentOptions(
    permission_mode="bypassPermissions",
    setting_sources=["project"],
    allowed_tools=["Read", "Grep", "Glob", "Bash", "Task", "Write", "Edit",
                    "TeamCreate", "TaskCreate", "TaskUpdate", "SendMessage"],
)

async with ClaudeSDKClient(options=options) as client:
    # Multi-turn interaction to drive Agent Team workflow
    result = await client.query("Create an agent team to audit X.sol with attacker, defender, verifier roles")
    # ... continue driving the session
```

This is more complex, requires a persistent process, and Agent Teams remain experimental. Defer to Phase 4 or later.

### Implementation Priority

1. **Immediate (3.1c)**: Build the evaluation runner using `claude -p` with `--append-system-prompt-file` for Tier 1+2 workflows. This covers ~90% of shipped workflows.
2. **Deferred (Phase 4)**: Agent Team evaluation via SDK `ClaudeSDKClient` or workflow decomposition.
3. **Always**: Use `--output-format json` + `--json-schema` for structured evaluation output. Use `--max-turns` and `--max-budget-usd` as safety limits.

### Runner Architecture Implications

The evaluation runner (`tests/workflow_harness/lib/evaluation_runner.py`) should:

1. **Store skill content paths** in scenario configs, not rely on `/slash` invocation.
2. **Use `--append-system-prompt-file`** to inject skill instructions deterministically.
3. **Capture session IDs** from JSON output for `--resume` chaining if multi-step evaluation is needed.
4. **Use hooks** (`PreToolUse`, `PostToolUse`) for observation capture even in `-p` mode.
5. **Set `--max-turns`** per workflow category (5 for simple tool skills, 20 for investigations, 40 for multi-agent debates).

### Sources

1. https://code.claude.com/docs/en/headless -- Official programmatic usage docs (Feb 2026)
2. https://code.claude.com/docs/en/skills -- Official skills documentation (Feb 2026)
3. https://code.claude.com/docs/en/agent-teams -- Official Agent Teams documentation (Feb 2026)
4. https://code.claude.com/docs/en/sub-agents -- Official subagents documentation (Feb 2026)
5. https://code.claude.com/docs/en/cli-reference -- CLI reference with all flags (Feb 2026)
6. https://platform.claude.com/docs/en/agent-sdk/overview -- Agent SDK overview (Feb 2026)
7. https://docs.anthropic.com/en/docs/claude-code/sdk/subagents -- SDK subagents docs (Feb 2026)
8. Community reports on HN (agentskills.io discussion) confirming skill auto-loading is probabilistic
