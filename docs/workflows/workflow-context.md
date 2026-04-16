# Workflow Context Generation

**Purpose:** Define protocol + economic context expectations.

## Inputs

- Contracts path
- Docs path or URLs

## Outputs

- `.vrs/context/protocol-pack.yaml`
- Economic context artifacts (EI/CTL outputs)

## Skills

- `vrs-context-pack`
- `vrs-economic-context`
- `vrs-taxonomy-migrate`

## Subagents

- `vrs-context-packer`

## Traceability

- Skill definitions: `docs/guides/skills-basics.md`, `src/alphaswarm_sol/skills/registry.yaml`
- Subagent definitions (if used): `src/alphaswarm_sol/agents/catalog.yaml`

## Steps

1. Generate protocol context pack.
2. Generate economic context (if enabled).
3. Gate Tier C patterns on context availability.

## Success

- Context exists before Tier C execution.

## Failure

- Tier C runs without context or with missing labels.

## Testing

- `.planning/testing/workflows/workflow-graph.md`
