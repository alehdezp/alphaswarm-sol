# GAP-03: delegate_guard.py config loading timing and process tree scope

**Created by:** improve-phase
**Source:** P1-ADV-2-01
**Priority:** HIGH
**Status:** active
**depends_on:** []

## Question

Does delegate_guard.py read config at invocation time (per PreToolUse call) or at import time (once, at session start)? Which process tree scope applies — parent evaluator only, or inherited by Agent Teams child processes? If invocation-time, a `--config <path>` flag or env var works. If import-time, env-var gating is needed instead.

## Context

Without a fail-safe scoping mechanism, the guard is either always strict (blocks dev) or always permissive (no eval protection). The symlink approach was rejected because obs hooks are observation-only and cannot block/abort on failure. The correct mechanism depends on whether config is read fresh per call or cached at import.

## Research Approach

1. Read delegate_guard.py source code to trace config loading path
2. Determine if `_load_config()` is called per-invocation or cached
3. Analyze how Claude Code hooks work — does each PreToolUse event invoke a fresh Python process or reuse one?
4. Determine if hooks configured in a parent session propagate to Agent Teams child processes

## Findings

**Confidence:** HIGH (source code analysis + Claude Code hooks documentation cross-reference)

### 1. Config Is Read at INVOCATION Time (Per PreToolUse Call)

The `delegate_guard.py` source code (lines 78-87) shows:

```python
def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    config = _load_config()  # <-- Called EVERY invocation
```

`_load_config()` is called inside `main()`, not at module import time. There is no caching (`@lru_cache`, module-level variable, or class-level singleton). Every time the hook runs, it reads the config file from disk.

### 2. Each Hook Invocation Is a FRESH Process

Claude Code hooks of type `"command"` are executed as **shell commands** (child processes). Per the official documentation (code.claude.com/docs/en/hooks):

> "Hooks are user-defined shell commands that execute at specific points in Claude Code's lifecycle."

Each `PreToolUse` event spawns a fresh shell process that runs the hook command. For delegate_guard.py, this means:
1. Claude Code detects a tool call
2. Claude Code spawns a new process: `python3 delegate_guard.py` (with JSON piped to stdin)
3. The process reads stdin, calls `_load_config()` (reads YAML from disk), evaluates patterns, exits
4. The process terminates

**There is no process reuse.** Each invocation is a completely independent process with no state from previous calls.

### 3. Config Search Path Follows Working Directory

`_load_config()` searches three locations (lines 28-33):

```python
search_paths = [
    Path(__file__).parent / config_name,           # 1. Same dir as hook script
    Path(os.getcwd()) / ".claude" / "hooks" / config_name,  # 2. CWD-based
    Path(os.getcwd()) / ".vrs" / "config" / config_name,    # 3. CWD-based
]
```

The first path is **relative to the hook script file** (absolute, won't change). The second and third paths are **relative to `os.getcwd()`** (the working directory at invocation time).

**Implication:** If a teammate runs in a worktree (different CWD), path 1 still resolves (it's script-relative), but paths 2 and 3 would point to the worktree's `.claude/hooks/` and `.vrs/config/` directories. The hook script itself is referenced by absolute path in `.claude/settings.json`, so **path 1 is the reliable config source across all process scopes**.

### 4. Hook Propagation to Agent Teams Child Processes

Claude Code hooks are configured in `.claude/settings.json` (project-level) or `~/.claude/settings.json` (user-level). Since **v2.1.63**, project configs and auto-memory are **shared across git worktrees** of the same repository.

**This means:**
- A `PreToolUse` hook defined in `.claude/settings.json` applies to ALL sessions in the same project, including Agent Teams teammates (which are independent Claude Code instances)
- With worktree isolation, teammates inherit the **project-level** hooks from the main repo's `.claude/settings.json` because worktree config sharing is automatic
- The hook command path (`"$CLAUDE_PROJECT_DIR"/.claude/hooks/guard-full-tests.sh`) uses `$CLAUDE_PROJECT_DIR`, which resolves to the project root for all sessions in the same project

**CRITICAL INSIGHT:** This means delegate_guard.py, when configured as a project-level PreToolUse hook, is **automatically active for all Agent Teams teammates**, including those in worktrees. The guard applies to the ENTIRE process tree, not just the parent evaluator.

### 5. Per-Session Scoping Mechanism

Since config is read at invocation time and the hook applies globally, per-session scoping can be achieved through:

**Option A (RECOMMENDED): Environment variable gating.**
Add an env var check at the top of delegate_guard.py:
```python
if os.environ.get("ALPHASWARM_EVAL_MODE") != "1":
    sys.exit(0)  # Not in eval mode, allow everything
```
Then `evaluation_runner.py` sets `ALPHASWARM_EVAL_MODE=1` before spawning teammates. Child processes inherit env vars.

**Option B: Config path override via env var.**
```python
config_path_override = os.environ.get("DELEGATE_GUARD_CONFIG")
if config_path_override:
    return _parse_simple_yaml(Path(config_path_override))
```
Then `evaluation_runner.py` sets `DELEGATE_GUARD_CONFIG=/path/to/delegate_guard_config_eval.yaml`.

**Option C: Separate config file for eval.**
Place `delegate_guard_config_eval.yaml` in the same directory as the hook script. Rename the default config and use the eval config only when deployed. This is the simplest but least flexible approach -- requires file manipulation before eval sessions.

### 6. Current Project Hook Configuration

The current `.claude/settings.json` has only one PreToolUse hook:
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/guard-full-tests.sh",
        "timeout": 5
      }]
    }]
  }
}
```

delegate_guard.py is NOT currently registered as a project-level hook. It exists in `tests/workflow_harness/hooks/` as a standalone script. To activate it for evaluations, it must be either:
- Added to `.claude/settings.json` (applies globally -- needs env var gating)
- Configured via the Claude Agent SDK's hook options (applies only to SDK-spawned sessions)
- Symlinked/copied into the hook execution path during eval session setup

## Recommendation

**Do:** Use **env-var gating (Option A)** combined with **env-var config path override (Option B)** for maximum flexibility. Both are zero-risk because config is read at invocation time per call.

**Specific actions:**

1. **Add env-var gating to delegate_guard.py:** At the top of `main()`, check `ALPHASWARM_EVAL_MODE`. If not set or not `"1"`, exit 0 immediately (allow all). This makes the guard safe to register globally.

2. **Add config path override:** Check `DELEGATE_GUARD_CONFIG` env var for an alternative config file path. If set, use it instead of the default search paths. This allows evaluation_runner.py to point to `delegate_guard_config_eval.yaml` explicitly.

3. **Register delegate_guard.py as a project-level PreToolUse hook** in `.claude/settings.json` with no matcher (applies to all tools). With env-var gating, it's a no-op during dev sessions.

4. **In evaluation_runner.py preflight (Stage 1):** Set both env vars before spawning any agent:
   ```python
   os.environ["ALPHASWARM_EVAL_MODE"] = "1"
   os.environ["DELEGATE_GUARD_CONFIG"] = str(eval_config_path)
   ```
   Verify the config file exists and contains the required `blocked_patterns`. Fail-fast if absent.

5. **Rewrite P1-IMP-05 / P1-ADV-2-01 in CONTEXT.md:** "Guard scoping uses invocation-time env-var gating (`ALPHASWARM_EVAL_MODE=1` + `DELEGATE_GUARD_CONFIG=/path/to/eval.yaml`). Config is read fresh on every PreToolUse call (no caching). Hooks propagate to Agent Teams child processes via project-level config sharing (v2.1.63). No symlinks needed."

**Impacts:** Plan 01 (must implement env-var gating + config override in delegate_guard.py), Plan 04 (must register hook in settings.json), evaluation_runner.py (must set env vars in preflight).
