# GSD Phase Plan Template (Condensed)

## Required Sections
- Goal
- Entry Gate
- Exit Gate
- Tasks (with tools per task)
- Skills/Subagents to Load
- Validation
- Tooling Update (if new tools/skills/agents are introduced)

## Mandatory Final Steps (every plan)
1) Run relevant tests
2) Critique results with subagent
3) Update docs/ for new additions

## Tool Guidance (per task)
- Research: `mcp__exa-search__web_search_exa` (type: deep)
- Code analysis: `rg`, `uv run alphaswarm query`, `uv run alphaswarm build-kg`
- Validation: `uv run pytest` or task-specific runner
