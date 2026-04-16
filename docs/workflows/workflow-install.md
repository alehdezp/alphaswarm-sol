# Workflow Install And Init

**Purpose:** Define expected install + init behavior in production.

## Inputs

- Project path
- Tool availability

## Outputs

- `.vrs/` directory created
- `.claude/skills/vrs-*` installed
- Health check status

## Skills

- `vrs-health-check`

## Traceability

- Skill definitions: `docs/guides/skills-basics.md`, `src/alphaswarm_sol/skills/registry.yaml`
- Subagent definitions (if used): `src/alphaswarm_sol/agents/catalog.yaml`

## Steps

1. Install package (`uv tool install -e .`) as tooling dependency.
2. Start Claude Code in the project and run `/vrs-health-check`.
3. If initialization is required, orchestrator invokes `uv run alphaswarm init`.
4. Re-run `/vrs-health-check` and verify required tools.

## Success

- Skills installed with `vrs-*` naming
- Health check shows required tools

## Failure

- Missing skills or failed health check

## Testing

- `.planning/testing/workflows/workflow-cli-install.md`
