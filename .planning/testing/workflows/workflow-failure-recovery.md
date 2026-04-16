# Workflow Failure Recovery And Diagnosis

**Purpose:** Validate that failures are detected, classified, and recoverable.

## When To Use

- Any change to error handling or retry logic.
- After introducing new skills or agents.

## Preconditions

- claude-code-controller installed.
- Failure taxonomy available in context.

## Steps

1. Run a workflow with a known failure injection.
2. Capture transcript and error classification output.
3. Verify progress guidance indicates restart or resume path.
4. Re-run with corrected input and new session.
5. Compare the recovery path to expected behavior.

## Optional Quick-Fix Loop (If Safe)

- If failure is a simple import/path issue, apply a single targeted fix.
- Re-run once in a new demo session and compare transcripts.
- Do not retry repeatedly; record the failure if it persists.

## claude-code-controller Commands

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
claude-code-controller send "claude" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=30
claude-code-controller send "/vrs-workflow-test /vrs-audit contracts/ --criteria failure" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=20.0 --timeout=300
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
claude-code-controller send "/exit" --pane=X
claude-code-controller kill --pane=X
```

## Required Evidence

- Transcript with failure markers and recovery behavior.
- Report with failure classification and remediation hints.
- Evidence of restart/resume guidance (status or resume output).

## Failure Diagnosis

- Missing classification indicates diagnostic failure.
- Reusing sessions indicates test contamination.
