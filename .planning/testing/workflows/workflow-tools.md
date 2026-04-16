# Workflow External Tools

**Purpose:** Validate tool integration for Slither, Mythril, and Aderyn.

## When To Use

- Any change to tool integration or tool configuration.

## Preconditions

- claude-code-controller installed.
- Tools installed and available.

## Steps

1. Run tool status checks.
2. Execute tool scans on a known contract.
3. Capture tool outputs and transcripts.

## claude-code-controller Commands

This workflow is **shell-only**. Do not launch `claude` here.

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
claude-code-controller send "uv run alphaswarm tools status" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=120
claude-code-controller send "uv run alphaswarm tools run contracts/ --tools slither,aderyn" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=20.0 --timeout=600
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
claude-code-controller kill --pane=X
```

## Required Evidence

- Transcript showing tool invocation markers.
- Logs indicating tool outputs.

## Failure Diagnosis

- Missing tool markers indicates integration failure.
- Tool errors indicate environment setup issues.
