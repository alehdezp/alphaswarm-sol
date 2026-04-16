# Workflow End-To-End Validation

**Purpose:** Validate full audits against external ground truth with real metrics.

## When To Use

- GA validation and release readiness checks.

## Preconditions

- claude-code-controller installed.
- External ground truth identified and documented.
- Scenario manifest entry includes `requires_ground_truth: true` and a valid `ground_truth_ref`.

## Steps

1. Run the full audit workflow in LIVE mode.
2. Fetch ground truth in the evaluator/controller context (not the Claude session).
3. Compare findings to external ground truth.
3. Verify tool-initialization stage executed (static tools run).
4. Record metrics with honest limitations.
5. Capture evidence packs and reports.

## claude-code-controller Commands

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
claude-code-controller send "claude" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=30
claude-code-controller send "/vrs-workflow-test /vrs-audit contracts/ --criteria e2e" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=60.0 --timeout=1200
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
claude-code-controller send "/exit" --pane=X
claude-code-controller kill --pane=X
```

## Required Evidence

- Transcript with tool and agent markers.
- Report with precision, recall, limitations, and duration.
- Ground truth provenance file (`ground_truth.json`) and `ground_truth_ref`.
- Evidence that false positives were discarded or marked.

## Failure Diagnosis

- Perfect metrics indicate likely fabrication.
- Missing provenance indicates invalid validation.
- Missing tool markers indicates tool initialization failure.
