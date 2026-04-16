# Workflow Bead Lifecycle

**Purpose:** Define bead creation, update, and listing behavior.

## Inputs

- Findings and evidence

## Outputs

- Bead records with status and evidence

## Skills

- `vrs-bead-create`
- `vrs-bead-update`
- `vrs-bead-list`
- `vrs-investigate`
- `vrs-create-bead-finding`
- `vrs-create-bead-context-merge`

## Traceability

- Skill definitions: `docs/guides/skills-basics.md`, `src/alphaswarm_sol/skills/registry.yaml`
- Subagent definitions (if used): `src/alphaswarm_sol/agents/catalog.yaml`

## Steps

1. Create bead per finding.
2. Update bead status during investigation.
3. List and filter beads for review.

## Success

- Beads track evidence and progress.

## Failure

- Findings without beads or status updates.

## Testing

- `.planning/testing/workflows/workflow-skills.md`
