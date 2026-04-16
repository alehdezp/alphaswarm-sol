# Guide claude-code-controller Usage

**Purpose:** Provide practical claude-code-controller usage patterns for specific testing workflows.

## Global Requirements

- Use claude-code-controller for all interactive tests.
- Always launch `zsh` first.
- Always capture output and store it in `.vrs/testing/runs/<run_id>/` (transcripts/ may be a symlink index).
- Always terminate the pane after capture.
- Run every test inside a dedicated demo claude-code-agent-teams session that is separate from any dev session.

**Local mode capture note:** If claude-code-controller reports `MODE: LOCAL (inside claude-code-agent-teams)`, `claude-code-controller capture` may not accept `--output`. Use shell redirection instead:

```bash
claude-code-controller capture --pane=X > .vrs/testing/runs/<run_id>/transcript.txt
```

## Session Naming

- Use `vrs-demo-{workflow}-{timestamp}` for every test session label.
- Never reuse a session or pane across tests.
- Record the session label and pane ID in both `manifest.json` and `report.json`.
- If claude-code-controller does not support naming sessions directly, still record the label in `manifest.json` and transcript header.
- claude-code-controller runs MUST be launched from a shell/session that is separate from your active development claude-code-agent-teams session.

## Demo Session Policy

- The demo session is testing-only and must not be shared with development work.
- One workflow run equals one demo session label.
- If you are unsure, start a new demo session and treat the old one as stale.
- Run claude-code-controller outside any dev claude-code-agent-teams session so it spawns a clean, managed session.

## Parallel Sessions

- Use a unique demo session label for each workflow run.
- Use a separate jj workspace or run directory per workflow to avoid `.vrs/` collisions.
- Capture and store transcripts under `.vrs/testing/runs/<run_id>/` per workflow run.

## Safeguards

- Check `claude-code-controller status` or `claude-code-controller list_panes` before starting.
- If any stale panes exist, use `claude-code-controller cleanup` before creating a new demo session.
- Never run `claude-code-controller kill` on panes that do not belong to the active `vrs-demo-*` run.

## Base Sequence

```bash
claude-code-controller launch "zsh"
claude-code-controller send "cd /path/to/project" --pane=X
claude-code-controller wait_idle --pane=X
claude-code-controller send "claude" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=30
```

## Shell-Only Steps (Pre-Claude)

Shell commands must run **before** launching `claude`. If you need to run shell
commands after `claude` is open, exit and restart the session or use a separate
pane and `claude-code-controller execute` there.

```bash
claude-code-controller execute "uv run alphaswarm health-check --project . --json" --pane=X
claude-code-controller execute "uv run alphaswarm build-kg contracts/" --pane=X
```

## Claude-Only Steps (Post-Launch)

After `claude` starts, **only** send slash commands and Claude prompts. Do not
send raw shell commands in the Claude session.

## Skill Test Pattern

```bash
claude-code-controller send "/vrs-workflow-test /vrs-audit contracts/ --criteria skill" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=15.0 --timeout=300
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
```

## Agent Test Pattern

```bash
claude-code-controller send "/vrs-workflow-test /vrs-audit contracts/ --criteria agent" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=20.0 --timeout=300
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
```

## Orchestration Test Pattern

```bash
claude-code-controller send "/vrs-workflow-test /vrs-audit contracts/ --criteria orchestration" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=30.0 --timeout=600
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
```

## Progress Guidance Check (Optional)

```bash
claude-code-controller send "/vrs-status --verbose" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=10.0 --timeout=120
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
```

## End-To-End Pattern

```bash
claude-code-controller send "/vrs-workflow-test /vrs-audit contracts/ --criteria e2e" --pane=X
claude-code-controller wait_idle --pane=X --idle-time=60.0 --timeout=1200
claude-code-controller capture --pane=X --output=.vrs/testing/runs/<run_id>/transcript.txt
```

## Cleanup

```bash
claude-code-controller send "/exit" --pane=X
claude-code-controller kill --pane=X
```
