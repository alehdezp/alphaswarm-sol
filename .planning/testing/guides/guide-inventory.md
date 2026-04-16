# Guide Inventory And Coverage

**Purpose:** Ensure full coverage of skills, agents, workflows, tools, and CLI entrypoints.

## Inventory Sources

- Skills registry
  ` src/alphaswarm_sol/skills/registry.yaml `
- Agents catalog
  ` src/alphaswarm_sol/agents/catalog.yaml `
- CLI entrypoints
  ` src/ ` and ` pyproject.toml `

## Required Output

- A single inventory list with unique IDs.
- A mapping from each inventory item to at least one scenario.
- A coverage report that flags gaps as blockers.

## Suggested Commands

```bash
rg -n "^\s*-\s+name:" src/alphaswarm_sol/skills/registry.yaml
rg -n "^\s*-\s+name:" src/alphaswarm_sol/agents/catalog.yaml
rg -n "typer\.Typer|@app\.command" src/
```

