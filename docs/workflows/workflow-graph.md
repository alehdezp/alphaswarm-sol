# Workflow Graph Build And Query

**Purpose:** Define expected graph construction and validation behavior.

## Inputs

- Contracts path

## Outputs

- `.vrs/graphs/*.toon`
- Query outputs with evidence refs

## Skills

- `vrs-graph-contract-validate`
- vrs-graph-retrieve
- `vrs-slice-unify`
- `vrs-taint-extend`
- `vrs-vql-help`

## Traceability

- Skill definitions: `docs/guides/skills-basics.md`, `src/alphaswarm_sol/skills/registry.yaml`
- Subagent definitions (if used): `src/alphaswarm_sol/agents/catalog.yaml`

## Steps

1. Claude Code triggers graph build through workflow tooling.
2. Claude Code executes graph query/retrieval steps (CLI is optional dev/tooling path).
3. Validate output against Graph Interface v2 contract.

## Success

- Evidence refs include graph node IDs and file:line.

## Failure

- Query output missing evidence or contract violations.

## Testing

- `.planning/testing/workflows/workflow-graph.md`
