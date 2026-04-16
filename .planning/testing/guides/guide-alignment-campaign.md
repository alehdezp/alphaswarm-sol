# Alignment Campaign Guide

**Purpose:** Align skills, subagents, and workflows with ` docs/workflows/ ` expectations and verify the alignment through real claude-code-controller runs with efficient coverage.

## When To Load

- Before planning or executing a new phase.
- After any change to skills, subagents, orchestration, or workflow docs.
- When audit output does not match intended behavior.

## Inputs

- ` docs/workflows/README.md `
- ` docs/workflows/workflow-*.md `
- ` docs/reference/testing-framework.md `
- ` .planning/testing/scenarios/SCENARIO-MANIFEST.yaml `
- ` .planning/testing/COMMAND-INVENTORY.md `
- ` src/alphaswarm_sol/skills/registry.yaml `
- ` src/alphaswarm_sol/agents/catalog.yaml `

## Outputs

- Alignment ledger that maps workflow -> skills -> subagents -> commands.
- Cross-links updated in `docs/workflows/README.md`, `docs/guides/skills-basics.md`, and `docs/reference/agents.md`.
- Evidence packs per run with claude-code-agent-teams transcripts and tool markers.
- Mismatch list with failure classification.
- Doc updates applied before skill changes.
- Updated ` .planning/testing/DOCS-VALIDATION-STATUS.md ` entries.

## Process

1. Build an alignment ledger for each workflow.
2. Ensure skills and subagents link back to workflow contracts and debugging guides.
   - Update `workflow_refs` in `src/alphaswarm_sol/skills/registry.yaml`.
   - Update `workflow_refs` in `src/alphaswarm_sol/agents/catalog.yaml`.
   - Validate with `scripts/validate_workflow_refs.py` (checks refs + cross-links).
   - Use `scripts/validate_workflow_refs.py --strict` to fail on missing Skills/Subagents links.
2. Select a coverage spiral that starts with the audit entrypoint and expands outward.
3. Run a golden path claude-code-controller test for each workflow in the spiral.
4. Compare output to workflow contract and classify mismatches.
5. Update docs first, then update skills and subagents, then re-run.
6. Record evidence and update validation status.
7. Expand coverage with delta runs only where changes occurred.

## Coverage Spiral (Recommended Order)

- Audit entrypoint and progress guidance.
- Graph build, context generation, and graph-first usage.
- Static tools initialization and tool markers in transcripts.
- Pattern detection with TaskCreate and TaskUpdate lifecycle.
- Subagent routing for attacker, defender, verifier, and specialists.
- Tier C gating and label-dependent patterns.
- Pattern lattice verification for complex Tier B/C scenarios.
- E2E validation with external ground truth.
- Legacy workflows from earlier phases (no regressions).

## Efficiency Rules

- Prefer the smallest workflow that exercises the change.
- One change, one targeted run, then update the ledger.
- Avoid full E2E reruns when a smaller workflow can verify the fix.

## Failure Classification

- Prompt or instruction failure.
- Skill load or naming failure.
- Orchestration or Task lifecycle failure.
- Graph or context generation failure.
- Tool execution failure.
- Settings or state mismatch.
- Evidence or transcript failure.

## Definition Of Done

- Every core workflow has at least one claude-code-controller transcript.
- Every critical skill and subagent has a corresponding workflow run.
- Mismatches are resolved or recorded in the super report.
- Docs, skills, and tests reflect the same workflow contract.
