# Legacy Infrastructure Sweep Record

**Date:** 2026-02-11
**Plan:** 3.1-02

## Sweep Results

### Pattern: `tmux` (case-insensitive)

| Scope | Hits |
|-------|------|
| `src/alphaswarm_sol/**/*.py` | 0 |
| `src/alphaswarm_sol/**/*.yaml` | 0 |
| `configs/**/*.yaml` | 0 |
| `.claude/skills/**` | 0 |
| `.claude/agents/**` | 0 |

### Pattern: `jujutsu|jj-workspace` (case-insensitive)

| Scope | Hits | Notes |
|-------|------|-------|
| `src/alphaswarm_sol/**/*.py` | 18 | All in ACTIVE workspace infrastructure (`orchestration/workspace.py`, `testing/flexible/`). NOT legacy -- these are the current jujutsu workspace system. |

### Pattern: `MasterOrchestrator|AgenticRunner|self_improving_runner|tmux_harness|tmux_controller|tmux_cli_wrapper`

| Scope | Hits | Notes |
|-------|------|-------|
| `src/alphaswarm_sol/**/*.py` | 7 | `master_orchestrator.py` (self-references), `self_improving_runner.py` (self-references), `workflow/__init__.py` (imports self_improving_runner). All files still exist on disk. |
| `.claude/skills/**` | 0 | |
| `.claude/agents/**` | 0 | |

### Files already deleted from disk (tmux infrastructure)

- `src/alphaswarm_sol/testing/tmux_harness.py` -- MISSING (deleted)
- `src/alphaswarm_sol/testing/workflow/tmux_cli_wrapper.py` -- MISSING (deleted)
- `src/alphaswarm_sol/testing/workflow/tmux_controller.py` -- MISSING (deleted)
- `configs/tmux_cli_markers.yaml` -- MISSING (deleted)

### Assessment

1. **Zero tmux references** remain in production code or configs.
2. **Jujutsu references** are all in ACTIVE workspace infrastructure (not legacy).
3. **`workflow/__init__.py`** exports `self_improving_runner` which still exists on disk -- import succeeds.
4. **No dead skill/agent .md files** found referencing legacy infrastructure.
5. **`skill_tool_policies.yaml`** has no tmux/legacy enforcement fields. The `full-testing-orchestrator` role references `git worktree*` but this is a valid tool command.
6. **`registry.yaml`** has 53 skills, all appear to reference existing entries.

## Archived Files

- `skill_tool_policies.yaml.orig` -- pre-modification copy
- `registry.yaml.orig` -- pre-modification copy
- `workflow__init__.py.orig` -- pre-modification copy
