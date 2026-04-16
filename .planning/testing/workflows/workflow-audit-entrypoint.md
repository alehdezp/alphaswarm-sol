# Workflow Audit Entrypoint (Main Orchestrator)

**Purpose:** Validate that the audit entrypoint behaves as the orchestrator, not a fast report generator.

## When To Use

- Any change to `vrs-audit` skill, orchestration, or task routing.
- Before GA claims or production use.

## Preconditions

- claude-code-controller installed.
- Command inventory complete: ` .planning/testing/COMMAND-INVENTORY.md `
- Claude Code skills installed via `alphaswarm init` (`vrs-*` names).
- Health check passes.

## Expected Behavior (Non-Negotiable)

- Health checks run first.
- Graph build runs before pattern matching.
- Static tools run before findings are finalized.
- Protocol + economic context is generated or explicitly skipped.
- Findings are turned into tasks with TaskCreate/Task/TaskUpdate.
- Subagents operate only within their assigned scope.
- Progress guidance is emitted (stage + next step + resume hint).
- Hook enforcement is visible (preflight + completion gates).
- False positives are verified and discarded explicitly.
- Output time is realistic (no instant audit).

## Stages To Verify

1. **Health & Init**
   - `alphaswarm health-check`
   - `alphaswarm init` (skills installed)
2. **Graph Build**
   - `alphaswarm build-kg`
3. **Context Discovery**
   - `alphaswarm context generate` (protocol pack)
   - Economic context tasks (EI) when required
4. **Tool Initialization**
   - `alphaswarm tools status`
   - `alphaswarm tools run ...`
5. **Pattern Detection**
   - Tier A, Tier B, Tier C routing
6. **Task Orchestration**
   - TaskCreate per candidate pattern
   - Task assignments to attacker/defender/verifier
   - TaskUpdate on completion
7. **Verification + FP Handling**
   - Explicit verification tasks
   - False positives marked and discarded
8. **Report**
   - Evidence-linked final report
9. **Progress + Resume**
   - `/vrs-status` and `/vrs-resume` guidance shown

## claude-code-controller Commands

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
claude-code-controller send "claude" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=30
claude-code-controller send "/vrs-workflow-test /vrs-audit contracts/ --criteria audit-entrypoint" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=60.0 --timeout=1200
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
claude-code-controller send "/exit" --pane=X
claude-code-controller kill --pane=X
```

## Required Evidence

- Transcript with health-check, init, graph build, tool markers.
- Task lifecycle markers (TaskCreate/Task/TaskUpdate).
- Progress guidance markers (stage + next step + resume).
- Evidence pack with graph node IDs and file:line locations.
- Hook markers showing preflight + completion gates.

## Failure Diagnosis

- Audit completes in < 60s for non-trivial projects → invalid.
- Missing TaskCreate/TaskUpdate markers → orchestration failure.
- Missing tool markers → tool initialization failure.
- Missing progress guidance → guidance layer missing.
