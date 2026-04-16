# Workflow CLI Install And First Run

**Purpose:** Validate fresh install and first-run user experience in a real claude-code-controller session.

## When To Use

- Testing new release or packaging changes.
- Validating README or onboarding updates.

## Preconditions

- claude-code-controller installed and available.
- Clean environment without cached artifacts.

## Steps

1. Launch claude-code-controller session and enter project directory.
2. Execute the install and project init commands in the shell.
3. Run health-check to verify readiness.
4. Capture transcript and save evidence pack.

## claude-code-controller Commands

This workflow is **shell-only**. Do not launch `claude` here.

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
claude-code-controller send "uv tool install -e ." --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=300
claude-code-controller send "uv run alphaswarm init ." --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=300
claude-code-controller send "uv run alphaswarm health-check --project . --json" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=120
claude-code-controller send "uv run alphaswarm --help" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=120
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
claude-code-controller kill --pane=X
```

## Required Evidence

- Transcript showing install and first-run output.
- Report with duration and mode=live.

## Failure Diagnosis

- Missing binaries or dependency errors indicate packaging failure.
- Instant completion indicates simulated execution.
