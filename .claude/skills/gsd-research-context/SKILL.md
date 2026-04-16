---
name: gsd-research-context
description: |
  Automate Get Shit Done (GSD) research and context generation for roadmap/phase planning in Claude Code and Codex.

  Use when you need to:
  - Read .planning/ROADMAP.md and propose or insert new phases
  - Generate phase context/research docs with deep Exa MCP search
  - Include relevant skills/subagents in plan context for orchestration
  - Enforce final plan steps: tests, critique subagent review, and docs updates

# Claude Code 2.1 Features
slash_command: gsd-research-context
context: fork

# Tool permissions
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash(cat*)
  - Bash(rg*)
  - mcp__exa-search__web_search_exa
  - Task
---

# GSD Research & Context Generator

You generate roadmap research and phase context for GSD-style planning. Always use Exa MCP deep search for investigations.

## Workflow

1) **Scope the phase**
   - Identify target phase position in `.planning/ROADMAP.md`
   - Define goals, dependencies, and constraints

2) **Deep research (mandatory)**
   - Use `mcp__exa-search__web_search_exa` with `type: deep`
   - Prefer GitHub repos, docs, and high-signal blogs/Medium
   - Collect 6–12 sources with dates and URLs

3) **Generate phase context**
   - Write `PHASE-CONTEXT.md` and `PHASE-RESEARCH.md`
   - Include recommended skills/subagents to load
   - Call out tool usage and evidence requirements

4) **Plan structure requirements (mandatory)**
   - The last steps of every plan MUST include:
     - Run tests relevant to the change
     - Critique results with a subagent (use `skill-auditor` or a phase-specific critic)
     - Document additions in `docs/` via the docs-curation agent
   - Every plan MUST include a **Skills/Subagents to Load** section
   - Every plan MUST include a **Tooling Update** step when tools/skills/agents change

5) **Skill injection**
   - Explicitly list skills/subagents to load inside the plan context
   - Include at least: `agent-skillcraft`, `gsd-research-context`

## References
- Plan template: `.claude/skills/gsd-research-context/references/plan-template.md`

## Output Contract
Provide:
- Phase context + research files
- Source list (URLs + access date)
- Skill/subagent list to load
- Tool usage notes
