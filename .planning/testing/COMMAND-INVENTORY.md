# Command Inventory

**Purpose:** Record verified commands required for testing workflows.

## Status

- This file must be completed before running real environment validation.

## Verification Process

Use claude-code-controller to run each command and capture a transcript. Store transcripts under
`.vrs/testing/runs/command-inventory/<run_id>/transcript.txt` and update the table.

Automation helper (optional):

```bash
python scripts/run_command_inventory.py --pane <PANE_ID> --session-label vrs-demo-command-inventory-<timestamp>
```

Validation:

```bash
python3 scripts/verify_command_inventory.py --strict --min-lines 50
```

## Inventory

| Command Purpose | Command | Verified | Verified At | Transcript | Notes |
|---|---|---|---|---|---|
| Install AlphaSwarm CLI | `uv tool install -e .` | no | | | |
| Initialize project + install Claude Code skills | `uv run alphaswarm init .` | no | | | |
| Health check (project readiness) | `uv run alphaswarm health-check --project . --json` | no | | | |
| Run AlphaSwarm CLI | `uv run alphaswarm --help` | no | | | |
| Build knowledge graph | `uv run alphaswarm build-kg contracts/` | **VERIFIED** | 2026-03-01 | Plan 3.1c.1-04 | Verified via Agent Teams (agent-x, agent-y) in isolated worktrees + concurrent race test. Identity-based output to `.vrs/graphs/{identity}/`. |
| Query graph (with --graph) | `uv run alphaswarm query "pattern:..." --graph {stem_or_path}` | **VERIFIED** | 2026-03-01 | Plan 3.1c.1-04 | Verified via Agent Teams + cross-contamination queries. `# result:` header contract confirmed. |
| Query graph (ambiguous) | `uv run alphaswarm query "..."` (no --graph, multiple graphs) | **VERIFIED** | 2026-03-01 | Plan 3.1c.1-04 | Error-when-ambiguous: exit 1, lists available stems. |
| Generate protocol context | `uv run alphaswarm context generate . --docs ./docs --output .vrs/context/protocol-pack.yaml --force` | no | | | |
| Check tools status | `uv run alphaswarm tools status` | no | | | |
| Run tools | `uv run alphaswarm tools run contracts/ --tools slither,aderyn` | no | | | |
| Claude Code CLI | `claude` | no | | | |
| Claude Code skills enablement | `uv run alphaswarm init .` | no | | | Installed skills are `vrs-*` |

## Notes

- `alphaswarm init` copies skills into `.claude/skills/vrs-*`.
- Add new rows for any additional tooling or workflows.
