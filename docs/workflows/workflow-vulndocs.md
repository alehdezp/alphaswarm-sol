# Workflow VulnDocs Pipeline

**Purpose:** Define discovery, addition, refinement, and validation of VulnDocs.

## Inputs

- Vulnerability research sources
- VulnDocs entries

## Outputs

- Validated VulnDocs entries
- Updated patterns and tests

## Skills

- `vrs-discover`
- `vrs-research`
- `vrs-ingest-url`
- `vrs-add-vulnerability`
- `vrs-merge-findings`
- `vrs-refine`
- `vrs-pattern-forge`
- `vrs-test-pattern`
- `vrs-pattern-verify`
- `vrs-pattern-batch`
- `vrs-validate-vulndocs`

## Subagents

- `vrs-prevalidator`

## Traceability

- Skill definitions: `docs/guides/skills-basics.md`, `src/alphaswarm_sol/skills/registry.yaml`
- Subagent definitions (if used): `src/alphaswarm_sol/agents/catalog.yaml`

## Steps

1. Discover or add new vulnerability entries.
2. Refine patterns based on feedback.
3. Validate with `vrs-validate-vulndocs`.

## Success

- VulnDocs entries validated and linked to tests.

## Failure

- Changes merged without validation.

## Testing

- `.planning/testing/workflows/workflow-docs-validation.md`
