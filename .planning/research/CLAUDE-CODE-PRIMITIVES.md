# Claude Code Orchestration Primitives — Canonical Taxonomy

**Purpose:** Single source of truth for terminology across all research and planning docs.
**Rule:** Every research doc MUST use these terms consistently. If unsure, cite this file.

---

## Quick Reference

| Primitive | What It Is | Location | Invocation |
|-----------|-----------|----------|------------|
| **Teammate** | Peer Claude instance in an Agent Team | `.claude/agents/*.md` | `TeamCreate` + `Task(team_name=...)` |
| **Subagent** | Child Claude instance, reports to parent only | N/A (spawned inline) | `Task(subagent_type=...)` |
| **Skill** | Instruction file loaded on `/slash-command` | `.claude/skills/*/SKILL.md` | `Skill` tool or `/name` |
| **Hook** | Deterministic script gating tool execution | `.claude/hooks/*.py` | Automatic (event-driven) |
| **Agent Definition** | Markdown defining a teammate's role/tools/model | `.claude/agents/*.md` | Referenced at teammate spawn |

---

## Detailed Definitions

### 1. Agent Teams (Teammates)

**What:** Multiple Claude Code instances working as **peers** with shared infrastructure.

**Key properties:**
- Peer-to-peer communication via `SendMessage` (DMs, broadcast)
- Shared task list with DAG dependencies (`TaskCreate/Update/List`)
- Each teammate has its own context window (separate Claude instance)
- Created via `TeamCreate`, teammates spawned via `Task(team_name=...)`
- Persistent state: `~/.claude/teams/{team-name}/`, `~/.claude/tasks/{team-name}/`
- Can have persistent memory (`memory: project` in agent frontmatter)

**When to use:** Adversarial debate, parallel investigation, multi-perspective analysis.

**NOT:** A subagent. Teammates talk to each other; subagents only report to parent.

### 2. Subagents

**What:** Child Claude instances spawned by the `Task` tool. Report results **back to parent only**.

**Key properties:**
- No peer communication (cannot DM other subagents)
- Parent receives result when subagent finishes
- Lighter weight than Agent Teams (no team infrastructure)
- Spawned via `Task(subagent_type="...", prompt="...")`
- No shared task list — parent manages coordination

**When to use:** Isolated research, single-purpose investigation, context isolation for large outputs.

**NOT:** A teammate. Subagents cannot send messages to peers. They return a result to the caller.

### 3. Skills

**What:** Instruction files that tell Claude Code **what to do** when invoked via slash command.

**Key properties:**
- Files at `.claude/skills/{name}/SKILL.md` (or `.claude/skills/{name}.md`)
- Invoked by user typing `/skill-name` or by `Skill` tool
- Loaded into Claude's context as instructions (not a separate process)
- Can trigger tool use, subagent spawning, or team creation
- Have YAML frontmatter (name, description, triggers, model)

**When to use:** Defining reusable workflows, entry points, orchestration recipes.

**NOT:** A command. "Commands" (`.claude/commands/`) is the **legacy** term from before skills existed. Current Claude Code uses skills. Some third-party repos still use the commands directory.

### 4. Hooks

**What:** Deterministic scripts that run **automatically** on Claude Code lifecycle events.

**Key properties:**
- Configured in `.claude/settings.json` under `"hooks"` key
- Event types: `PreToolUse`, `PostToolUse`, `Stop`, `SessionStart`, `UserPromptSubmit`, etc.
- Can **block** actions (exit code 2) or **log/inject** context (exit code 0)
- Run as external processes (Python, shell, etc.)
- Deterministic — not LLM-powered (use `type: "command"`, not `type: "agent"`)

**When to use:** Enforcement gates, logging, context injection, validation.

**NOT:** A skill or an agent. Hooks are automatic and deterministic. They don't require user invocation.

### 5. Agent Definitions

**What:** Markdown files that define a **teammate's** identity, tools, model, and instructions.

**Key properties:**
- Files at `.claude/agents/{name}.md`
- YAML frontmatter: `name`, `description`, `model`, `tools`, `disallowedTools`, `memory`, `hooks`
- Body (below frontmatter): system prompt for the agent
- Referenced when spawning a teammate into an Agent Team
- Can also be used as `subagent_type` in `Task` tool

**When to use:** Defining specialized roles (attacker, defender, verifier, researcher).

---

## Common Confusion Points

### "Spawn an agent" — Teammate or Subagent?

| Context | Correct Term | Why |
|---------|-------------|-----|
| Inside `TeamCreate` team, uses `SendMessage` | **Teammate** | Has peer communication |
| Via `Task(subagent_type=...)`, no team | **Subagent** | Reports to parent only |
| Agent definition file (`.claude/agents/*.md`) | **Agent definition** | The file, not the instance |

### "Commands" vs "Skills"

| Term | Status | Location |
|------|--------|----------|
| Commands (`.claude/commands/`) | **Legacy** | Third-party repos may still use this |
| Skills (`.claude/skills/`) | **Current** | Official Claude Code convention |

### Agent Teams vs Task-tool subagents

| Feature | Agent Teams (Teammates) | Task-tool (Subagents) |
|---------|------------------------|----------------------|
| Peer DMs | Yes (`SendMessage`) | No |
| Shared task list | Yes (`TaskCreate/Update`) | No |
| Team infrastructure | Yes (`~/.claude/teams/`) | No |
| Multiple active at once | Yes (parallel peers) | Yes (parallel children) |
| Communication pattern | Peer-to-peer mesh | Star (parent-child) |
| Cost | ~5-7x single session | ~2-3x per subagent |
| Best for | Debate, adversarial analysis | Research, isolated tasks |

---

## Correct Usage Examples

**Creating an Agent Team for debate:**
```
TeamCreate("vrs-audit-project")              # Create team
Task(name="attacker", team_name="...", ...)   # Spawn teammate
Task(name="defender", team_name="...", ...)   # Spawn teammate
SendMessage(recipient="attacker", ...)        # Peer DM
```
The attacker and defender are **teammates**, not subagents.

**Spawning a subagent for research:**
```
Task(subagent_type="Explore", prompt="Find all access control patterns")
```
This is a **subagent** — it returns results to the caller. No team, no DMs.

**Invoking a skill:**
```
/vrs-audit contracts/
```
This loads the **skill** instructions. The skill may then create teams or spawn subagents.

**Hook blocking unsafe action:**
```json
// .claude/settings.json
{ "hooks": { "PreToolUse": [{ "matcher": "Read", "hooks": [{ "type": "command", "command": "python3 .claude/hooks/check.py" }] }] } }
```
This is a **hook** — deterministic, automatic, not user-invoked.

---

## Cross-Reference to Research Docs

| Document | Primary Concepts Covered |
|----------|-------------------------|
| `agent-teams-migration/REPORT-02-technical-architecture.md` | Agent Teams mechanics, teammates, messaging |
| `agent-teams-migration/REPORT-01-opinions-creative-uses.md` | Teammate patterns, cost comparison with subagents |
| `agent-teams-migration/BLOG-POST-self-testing-frontier.md` | Self-testing via teams, skill invocation |
| `agent-teams-migration/REPORT-05-gap-analysis.md` | Quality gates, teammate orchestration |
| `agent-teams-migration/ROADMAP.md` | Migration from legacy to teammates + skills |
| `claude-code-agent-techniques/RESEARCH-SUMMARY.md` | Subagent patterns, hooks, skill authoring |
| `claude-code-hooks-mastery/RESEARCH-SUMMARY.md` | Hook lifecycle, task orchestration, skill validation |
| `../new-milestone/reports/w2-agent-teams-architecture.md` | Complete debate protocol using teammates |
