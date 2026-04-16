# Workflow Grammar And In-Situ Testing

**Purpose:** Validate that agents follow workflow grammar and produce structured outputs.

## When To Use

- When adding new workflows that require strict output structure.
- When validating in-situ reasoning formats.

## Preconditions

- claude-code-controller installed.
- Grammar definition ready for the workflow.

## Steps

1. Provide the grammar to the workflow.
2. Run the workflow in isolation.
3. Validate output against grammar constraints.
4. Capture structured outputs and transcripts.

## claude-code-controller Commands

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
claude-code-controller send "claude" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=30
claude-code-controller send "/vrs-workflow-test /vrs-audit contracts/ --criteria grammar" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=20.0 --timeout=300
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
claude-code-controller send "/exit" --pane=X
claude-code-controller kill --pane=X
```

## Required Evidence

- Transcript showing grammar compliance.
- Structured output file linked in report.

