# Guide: Jujutsu Workspace-Based Test Scenarios

**Purpose:** Use jj workspaces to create isolated, reusable, real-world test scenarios.

## When To Use

- When testing a workflow in isolation without polluting the main workspace.
- When you need to reset to a known state and re-run the same scenario.
- When comparing behavior across multiple workflows in parallel.

## Core Rules

- One jj workspace per scenario.
- One claude-code-controller session per run.
- Never reuse sessions across workspaces.
- Always record transcripts to `.vrs/testing/runs/<run_id>/transcript.txt` inside the workspace.
- Use a dedicated demo session label for every workflow run.

## Workspace Pattern

```bash
# Create a dedicated workspace for a scenario
jj workspace add ../vrs-ws-audit-001 --name ws-audit-001 -r @

# Run tests inside the workspace (claude-code-controller required)
cd ../vrs-ws-audit-001

# After completion, forget the workspace and remove directory
jj workspace forget ws-audit-001
rm -rf ../vrs-ws-audit-001
```

## Creating a Test Workspace

1. Create workspace from current revision:
   ```bash
   jj workspace add /tmp/vrs-workspaces/test-001 --name test-001 -r @
   ```

2. Create workspace from specific revision:
   ```bash
   jj workspace add /tmp/vrs-workspaces/test-002 --name test-002 -r <commit-id>
   ```

3. List active workspaces:
   ```bash
   jj workspace list
   ```

## Cleaning Up Workspaces

1. Forget workspace from jj tracking:
   ```bash
   jj workspace forget test-001
   ```

2. Remove workspace directory:
   ```bash
   rm -rf /tmp/vrs-workspaces/test-001
   ```

## Rollback to Checkpoint

Instead of git checkout, use jj edit:
```bash
cd /tmp/vrs-workspaces/test-001
jj edit <checkpoint-revision>
```

## Scenario Isolation Strategy

- Use jj workspaces to isolate:
  - Workflow-specific state (`.vrs/`)
  - Scenario-specific settings files
  - Evidence packs and transcripts
- Keep a baseline scenario and clone it per workflow.

## Evidence Requirements

- Store transcripts under the workspace's `.vrs/testing/runs/<run_id>/`.
- Link transcript paths in:
  - `.planning/testing/DOCS-VALIDATION-STATUS.md`
  - `.planning/testing/ALIGNMENT-LEDGER-TEMPLATE.md`

## Recommended Naming

- Workspace: `vrs-ws-{workflow}-{id}`
- claude-code-agent-teams session label: `vrs-demo-{workflow}-{timestamp}`

## Parallel Runs

- Use one jj workspace per workflow run.
- Use a unique demo session label per run.
- If any conflicts appear, stop the run and restart with a new session label.

## Jujutsu Quick Reference

| Task | Git Worktree | JJ Workspace |
|------|--------------|--------------|
| Create | `git worktree add <path> <branch>` | `jj workspace add <path> -r <rev>` |
| Create named | `git worktree add -b <name> <path> <ref>` | `jj workspace add <path> --name <name> -r <rev>` |
| Remove | `git worktree remove <path>` | `jj workspace forget <name>` + `rm -rf <path>` |
| List | `git worktree list` | `jj workspace list` |
| Prune | `git worktree prune` | N/A (automatic) |
| Repo root | `git rev-parse --show-toplevel` | `jj root` |
| Current revision | `git rev-parse HEAD` | `jj log -r @ -T commit_id --no-graph` |

### Key Differences

1. **No branch required**: JJ workspaces don't require creating branches
2. **Named workspaces**: Use `--name` to identify workspaces
3. **Two-step cleanup**: `forget` removes tracking, `rm -rf` removes files
4. **Operation log**: Use `jj op log` to see workspace operation history
5. **Undo support**: Use `jj undo` to reverse workspace operations
