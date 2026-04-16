# Workflow Tool Initialization

**Purpose:** Define expected static tool execution behavior.

## Inputs

- Tool availability
- Contract scope

## Outputs

- Tool outputs and markers in transcripts
- Findings attached to evidence packs

## Skills

- `vrs-tool-slither`
- `vrs-tool-aderyn`
- `vrs-tool-mythril`
- `vrs-tool-coordinator`

## Traceability

- Skill definitions: `docs/guides/skills-basics.md`, `src/alphaswarm_sol/skills/registry.yaml`
- Subagent definitions (if used): `src/alphaswarm_sol/agents/catalog.yaml`

## Steps

1. Claude Code runs tool status checks via `vrs-tool-*` workflow steps.
2. Claude Code executes tool scans (CLI is a subordinate tool call surface).
3. Attach outputs to evidence packs.

## Success

- Tool markers visible before findings are finalized.

## Failure

- Audit reports findings without tool initialization.

## Testing

- `.planning/testing/workflows/workflow-tools.md`
