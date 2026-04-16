# Claude Code Orchestration (Hooks + Tasks)

**Purpose:** Define how AlphaSwarm should use Claude Code hooks, subagents, and task orchestration to enforce real‑world workflows.

## When To Load

- When designing or debugging orchestration behavior.
- When refining audit workflow stages.
- When adding or modifying hooks or subagent routing.

## Core Primitives

**Hooks**
- Deterministic gates for tool calls and completion.
- Used to block unsafe or incomplete behavior.

**Tasks (TaskCreate/TaskUpdate/TaskList/TaskGet)**
- Explicit orchestration state and ownership.
- Required before findings are emitted.

**Subagents**
- Isolated contexts for scope‑limited work.
- Tool restrictions enforce safety and focus.

**Output Styles**
- Structured outputs for reports, evidence packs, and task summaries.

## Platform Constraints (Must Respect)

- Subagents run in isolated contexts and **cannot spawn other subagents**.
- Subagent tool access is allowlisted; use the minimum required tools.
- Subagents may run in foreground or background; background runs cannot use MCP tools.
- Skills can be preloaded into subagents; skills are not inherited automatically.

## Meta‑Prompting Patterns (Use Selectively)

Meta‑prompting should be reserved for workflows that require guaranteed structure:

- **Template prompts:** define exact sections for plans, reports, or evidence.
- **Self‑validated prompts:** enforce required sections using Stop hooks and validators.
- **Team prompts:** builder + validator agents to increase trust in output quality.

## Applied Reasoning Patterns (Use Selectively)

These patterns should only be used when ambiguity or risk justifies extra cost:

- **Plan‑then‑execute:** create an explicit task plan before running tools.
- **Reason‑act loops:** interleave reasoning with tool use and cite evidence.
- **Reflection passes:** add a verifier critique step before finalizing.
- **Branching checks:** explore multiple hypotheses for ambiguous findings.

## Hook Enforcement Patterns

**PreToolUse**
- Block tool calls when `.vrs/settings.yaml` disallows a tool.
- Block tool calls if required preflight gates failed.

**UserPromptSubmit**
- Log prompts and inject current stage/state.
- Reject invalid commands (e.g., `/vrs:` naming).

**Stop / SubagentStop**
- Block completion if TaskCreate/TaskUpdate markers are missing.
- Block completion if evidence sections are incomplete.

**SessionStart / SessionEnd**
- Load `.vrs/state/current.yaml` and persist run summaries.
- Write transcripts and evidence pack pointers.

**PreCompact**
- Snapshot transcripts before compaction.

## Task Orchestration Contract (Audit)

1. **TaskCreate** for each pattern candidate.
2. **TaskUpdate** with evidence and verdicts before reporting.
3. **TaskList/TaskGet** used for progress and resume.

No findings may be emitted without a corresponding task lifecycle.

## Progress UX (Status Line + State)

Use session data to display progress:

- Update `.claude/data/sessions/{session_id}.json` extras:
  - `stage.current`
  - `stage.completed[]`
  - `stage.next`
  - `tasks.pending[]`
  - `tasks.completed[]`

Expose the same information in `.vrs/state/current.yaml` for automation/tooling access (including CLI/debug workflows).

## Subagent Constraints

- Single responsibility per subagent.
- Tool allowlist only (minimum required tools).
- No nested subagent spawning.
- Use foreground subagents for workflows requiring user interaction.

## AlphaSwarm Workflow Mapping

- Audit entrypoint: `docs/workflows/workflow-audit.md`
- Task orchestration: `docs/workflows/workflow-tasks.md`
- Progress + resume: `docs/workflows/workflow-progress.md`
- Verification: `docs/workflows/workflow-verify.md`

## Testing

All orchestration behavior must be validated via Agent Teams (native Claude Code) or `ClaudeCodeRunner` (headless `claude --print`):

- `docs/reference/testing-framework.md`
- `.planning/testing/workflows/workflow-orchestration.md`
