# Workflow Skill Testing

**Purpose:** Validate that skills load, execute, and chain correctly in real CLI sessions.

## When To Use

- Any change to a skill definition or skill registry.

## Preconditions

- claude-code-controller installed.
- Skills inventory from ` src/alphaswarm_sol/skills/registry.yaml `.
- Skills installed via `alphaswarm init` under `.claude/skills/vrs-*`.

## Steps

1. Select a single skill and run it in isolation.
2. Run a multi-skill chain that exercises routing.
3. Capture transcripts and evidence packs for each run.

## claude-code-controller Commands

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
claude-code-controller send "claude" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=30
claude-code-controller send "/vrs-workflow-test /vrs-audit contracts/ --criteria skill" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=15.0 --timeout=300
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
claude-code-controller send "/exit" --pane=X
claude-code-controller kill --pane=X
```

## Required Evidence

- Transcript with skill invocation markers.
- Report with duration and tokens.

## Failure Diagnosis

- Missing skill invocation indicates load failure.
- Incorrect chain order indicates routing failure.
