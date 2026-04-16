# Guide Add A New Workflow Test

**Purpose:** Define how to add a new workflow test that is reusable, evidence-first, and claude-code-controller compliant.

## When To Use

- Adding a new feature or workflow that needs validation.
- Creating a new test scenario not covered by existing workflows.

## Steps

1. Define the workflow intent and expected outcome.
2. Select the correct tier (skill, agent, workflow, e2e, tools, graph).
3. Create a workflow doc in ` .planning/testing/workflows/ `.
4. Add a scenario entry using ` .planning/testing/templates/scenario-manifest.yaml `.
5. Define required evidence and ground truth.
6. Add the workflow to ` .planning/testing/DOC-INDEX.md `.
7. Run `workflow-instruction-verification` before delegating to subagents.
8. Include a dedicated demo session label (`vrs-demo-{workflow}-{timestamp}`) in the workflow instructions.

## Required Sections In Workflow Doc

- Purpose
- When To Use
- Preconditions
- Steps
- claude-code-controller Commands
- Required Evidence
- Failure Diagnosis

## Instruction Verification

Before giving the workflow to subagents, run:

- ` .planning/testing/workflows/workflow-instruction-verification.md `

This ensures the instructions trigger the correct workflow and markers.
