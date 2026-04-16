# Workflow Progress And Resume

**Purpose:** Define progress guidance, checkpoints, and resume behavior.

## Inputs

- Current run state

## Outputs

- Status summary
- Resume guidance
- Status line updates
- Run-id and namespace summary
- Lock status (if applicable)

## Run Identity And Isolation

- Each run generates a unique run-id at start and records it in run state.
- All artifacts, evidence, and transcripts are namespaced by run-id.
- If a run-id collision is detected, the run must halt or mint a new run-id and log the change.
- Parallel runs may share read-only inputs, but must not share mutable state.

## Locking Policy

- Default policy is namespace isolation rather than global locking.
- If a workflow requires exclusive access, it must create an explicit lock and emit a clear error when the lock is already held.
- Lock acquisition and release should be visible in the status summary.

## Skills

- `vrs-status`
- `vrs-resume`
- `vrs-checkpoint`
- `vrs-rollback`
- `vrs-orch-resume`
- `vrs-track-gap`

## Subagents

- `vrs-supervisor`

## Traceability

- Skill definitions: `docs/guides/skills-basics.md`, `src/alphaswarm_sol/skills/registry.yaml`
- Subagent definitions (if used): `src/alphaswarm_sol/agents/catalog.yaml`

## Steps

1. Emit run-id and namespace plus current stage and completed stages.
2. Provide next-step guidance.
3. Allow resume or rollback via checkpoints.
4. Update session status line extras (run-id, stage, next step).
5. Surface lock status and collision handling when a lock is required.

## Success

- Users can resume or restart without guesswork.
- Status line reflects run-id, current stage, and next step.
- Parallel runs are isolated by run-id namespace.

## Failure

- No status or resume guidance after audits.
- Status line or state file never updates.
- Run-id or lock status is missing from progress output.

## Testing

- `.planning/testing/guides/guide-orchestration-progress.md`
- `.planning/testing/workflows/workflow-orchestration.md`

## Related

- `docs/reference/claude-code-orchestration.md`
