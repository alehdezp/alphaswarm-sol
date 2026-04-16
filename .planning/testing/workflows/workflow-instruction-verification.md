# Workflow Instruction Verification For Subagents

**Purpose:** Validate that instructions are correct before delegating testing to subagents.

## Why This Exists

Subagents must receive validated instructions. If instructions are wrong, the test results are unreliable.

## When To Use

- Before introducing new testing instructions to subagents.
- Before using a new workflow or prompt template.

## Preconditions

- claude-code-controller installed.
- The instruction text or workflow prompt is finalized.

## Steps

1. Run the instruction in a controlled claude-code-controller session.
2. Confirm the instruction triggers the correct workflow and tools.
3. Capture transcript and evaluate against expected markers.
4. Only then delegate the same instruction to subagents.

## claude-code-controller Commands

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
claude-code-controller send "claude" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=30
claude-code-controller send "<instruction text or workflow command>" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=15.0 --timeout=300
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
claude-code-controller send "/exit" --pane=X
claude-code-controller kill --pane=X
```

## Required Evidence

- Transcript showing the instruction executed as intended.
- Report confirming the instruction did not deviate.

