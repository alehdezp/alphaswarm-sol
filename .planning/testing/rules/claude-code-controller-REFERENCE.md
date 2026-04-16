# claude-code-controller Reference

This is a testing-focused reference. The canonical source is `.planning/testing/rules/canonical/claude-code-controller-instructions.md`.

## Always Launch A Shell First

```bash
claude-code-controller launch "zsh"
```

## Minimal Command Set

```bash
claude-code-controller send "cmd" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=60
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt

# Local mode note: if claude-code-controller reports MODE: LOCAL, use shell redirection instead:
claude-code-controller capture --pane=X > .vrs/testing/runs/<run_id>/transcript.txt
claude-code-controller kill --pane=X
```

## Canonical Workflow Pattern

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
claude-code-controller send "claude" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=30
claude-code-controller send "/vrs-workflow-test ..." --pane=X
claude-code-controller wait_idle --pane=X --idle-time=15.0 --timeout=300
claude-code-controller capture --pane=X
claude-code-controller send "/exit" --pane=X
claude-code-controller kill --pane=X
```

## Requirements

- Use claude-code-controller only for interactive tests.
- Always capture output and store it in `.vrs/testing/runs/<run_id>/`.
- Never reuse sessions or panes.
- Use the demo session label `vrs-demo-{workflow}-{timestamp}` for every run.
- Run claude-code-controller outside your active development claude-code-agent-teams session to spawn a separate demo session.
- Never kill panes outside the current `vrs-demo-*` run.
