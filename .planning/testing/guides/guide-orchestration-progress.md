# Guide Orchestration Progress And Guidance

**Purpose:** Make orchestration state, progress, and next steps explicit during tests.

## When To Use

- Any orchestration or audit workflow test.
- Any time you need to resume or restart a run.

## Required Behavior

The orchestrator must emit:
- Current stage (health, graph, tools, tasks, verify, report).
- What has completed.
- What is next and why.
- How to resume or restart.
- Status line updates with current stage and next step.

Canonical marker strings live in `.planning/testing/MARKER-REGISTRY.yaml`.

## Commands

```bash
/vrs-status
/vrs-status --verbose
/vrs-resume
/vrs-resume --list-checkpoints
/vrs-checkpoint --create <name>
/vrs-rollback <checkpoint-id>
```

## Resume Semantics

- **Resume** continues from last checkpoint.
- **Restart** starts a new run with a new session and evidence pack.
- **Rollback** uses a checkpoint when a run is contaminated.

## State Files

- `.vrs/testing/state/current.yaml` — active session (testing)
- `.vrs/state/current.yaml` — expected production runtime state
- `.vrs/testing/state/history/` — archived sessions

## Status Line Extras (Required)

Update `.claude/data/sessions/{session_id}.json` extras:
- `stage.current`
- `stage.completed[]`
- `stage.next`
- `tasks.pending[]`
- `tasks.completed[]`

Reference: `docs/reference/claude-code-orchestration.md`.

## claude-code-controller Check (After Audit)

```bash
claude-code-controller send "/vrs-status --verbose" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=120
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
```

## Failure Diagnosis

- Missing stage markers → guidance layer absent.
- Status shows no active session after audit → state not persisted.
