# Workflow Documentation Validation

**Purpose:** Validate that testing docs themselves are usable, accurate, and executable.

## When To Use

- After modifying any workflow or guide.
- Before delegating instructions to subagents.

## Preconditions

- claude-code-controller installed.
- Updated docs in ` .planning/testing/ `.

## Steps

1. Run instruction verification for the updated workflow.
2. Execute the workflow in a real claude-code-controller session.
3. Capture transcripts and compare to expected markers.
4. Update docs immediately if any mismatch is found.

## claude-code-controller Commands (Template)

Use the exact workflow command from the doc you are validating.

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
claude-code-controller send "claude" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=30
claude-code-controller send "<workflow command from docs>" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=20.0 --timeout=600
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
claude-code-controller send "/exit" --pane=X
claude-code-controller kill --pane=X
```

## Policy

Documentation is part of the system. Every workflow doc must be executed at least once in a real run.

This includes:

- `docs/workflows/` (product expectations)
- `.planning/testing/` (test execution workflows)

## Required Evidence

- Transcript showing the workflow ran as documented.
- Evidence pack with report and environment metadata.

## Failure Diagnosis

- Missing markers indicate doc-command mismatch.
- Missing evidence indicates doc incompleteness.
