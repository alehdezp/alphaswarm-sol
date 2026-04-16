# API Contract: Hooks and Workspace

**Location:** `tests/workflow_harness/lib/workspace.py`
**3.1b Plans:** 3.1b-03 (hooks infrastructure, DONE), 3.1b-04 (Jujutsu workspace isolation)
**3.1c Consumers:** 3.1c-02 (Observation Hooks), 3.1c-05 (Debrief Protocol), 3.1c-12 (Improvement Loop + Regression)

## Parse/Execute Boundary

- **3.1b provides:** Hook registration infrastructure, observation directory creation, Jujutsu workspace lifecycle management.
- **3.1c provides:** The actual hook scripts (6 observation + 2 debrief), debrief protocol logic, improvement loop sandbox.

---

## WorkspaceManager.install_hooks()

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass
class HookConfig:
    """Configuration for a single hook registration.

    Attributes:
        event_type: Claude Code hook event name. Valid values:
            "PreToolUse", "PostToolUse", "SubagentStart", "SubagentStop",
            "Stop", "SessionStart", "TeammateIdle", "TaskCompleted"
        script_path: Path to the hook script, relative to workspace root.
            Example: ".claude/hooks/observe_tools.py"
        timeout: Maximum seconds for hook execution. Default: 30.
            RS-02 recommends 30s. Claude Code default is 60s.
    """

    event_type: str
    script_path: str  # Relative to workspace root, used as shell command prefix
    timeout: int = 30
```

**Note on current implementation:** The existing `install_hooks()` method accepts
`extra_hooks` as `list[tuple[str, str] | tuple[str, str, int]]`. The `HookConfig`
dataclass above is the TARGET contract for 3.1b-02/03 to implement. During the
transition, the tuple format remains supported alongside `HookConfig`.

```python
class WorkspaceManager:
    """Manage isolated test workspaces for scenario execution.

    Existing methods (MUST NOT CHANGE SIGNATURES):
    - __init__(self, base_dir: Path) -> None
    - setup(self, scenario_dir: Path, extra_hooks=None) -> Path
    - install_hooks(self, workspace: Path, extra_hooks=None) -> None
    - get_session_info(self, workspace: Path) -> dict[str, Any]
    - get_transcript_paths(self, workspace: Path) -> dict[str, Path]
    - cleanup(self, workspace: Path) -> None
    """

    def install_hooks(
        self,
        workspace: Path,
        extra_hooks: list[tuple[str, str] | tuple[str, str, int]] | None = None,
        hook_configs: list[HookConfig] | None = None,
    ) -> None:
        """Install hook scripts and write .claude/settings.json.

        Copies the default log_session.py hook and registers it for
        SubagentStop and Stop events. Additional hooks are registered via
        extra_hooks (tuple format, backward compatible) or hook_configs
        (HookConfig format, preferred).

        Both extra_hooks and hook_configs can be provided simultaneously;
        they are merged. Deduplication by (event_type, command) prevents
        duplicate registrations.

        Args:
            workspace: Path to the scenario workspace.
            extra_hooks: Legacy tuple format — (event_name, command) or
                (event_name, command, timeout).
            hook_configs: Preferred format — list of HookConfig instances.
        """
        ...
```

**3.1c consumer expectations:**
- 3.1c-02 registers 6 observation hooks + 2 debrief hooks via `hook_configs`.
- 3.1c-05 registers TeammateIdle and TaskCompleted hooks with exit code 2 behavior.
- All hooks use `type: "command"` in settings.json (NEVER `type: "prompt"` per Bug #20221).

**Failure modes:**
- Calling `install_hooks()` with both `extra_hooks` and `hook_configs` merges both lists. No error.
- Duplicate hooks (same event_type + same command) are silently deduplicated via `_ensure_hook()`.
- Invalid event_type names are written to settings.json as-is. Claude Code ignores unknown event types.

---

## _ensure_hook() (Internal, Stable)

```python
def _ensure_hook(
    hooks: dict,
    event_name: str,
    command: str,
    timeout: int = 30,
) -> None:
    """Ensure a hook command exists for the given event, without duplicating.

    Uses the nested format Claude Code expects:
        {"hooks": [{"type": "command", "command": "...", "timeout": N}]}

    Multiple hooks per event type are supported. Each call appends a new
    group if the command isn't already registered.

    This function is internal but its behavior is stable — 3.1c relies
    on deduplication semantics.
    """
    ...
```

**Contract guarantees:**
- Multiple hooks per event type ARE supported (not just one).
- Deduplication is by exact command string match.
- All hooks use `type: "command"` format (no `type: "prompt"`).

---

## .vrs/observations/ Directory Convention

```
workspace_root/
  .vrs/
    observations/
      {session_id}.jsonl          # Primary session observations
      subagents/
        agent-{agent_id}.jsonl    # Per-agent observations (optional)
```

**JSONL record schema:**

```python
@dataclass
class ObservationRecord:
    """A single observation record in the JSONL file.

    Written by hooks to .vrs/observations/{session_id}.jsonl.
    Each line is a self-contained JSON object (crash-safe: partial writes
    don't corrupt prior lines).

    Attributes:
        timestamp: ISO 8601 timestamp when the event occurred.
        event_type: Hook event name (e.g., "PreToolUse", "SubagentStop").
        hook_name: Name of the hook script that produced this record.
        session_id: Claude Code session identifier.
        payload: Event-specific data dict. Contents vary by event_type:
            - PreToolUse: {"tool_name": str, "arguments": dict}
            - PostToolUse: {"tool_name": str, "duration_ms": int, "success": bool, "result_preview": str}
            - SubagentStart: {"agent_name": str, "role": str, "model": str}
            - SubagentStop: {"agent_name": str, "transcript_path": str}
            - Stop: {"reason": str}
            - SessionStart: {"working_directory": str, "model": str}
            - TeammateIdle: {"teammate_name": str, "team_name": str}
            - TaskCompleted: {"task_id": str, "task_subject": str, "teammate_name": str}
    """

    timestamp: str
    event_type: str
    hook_name: str
    session_id: str
    payload: dict[str, Any]
```

**File naming:**
- `{session_id}.jsonl` — The session_id comes from the Claude Code session (available in hook environment as `$SESSION_ID` or from the hook input JSON).
- File is created on first write by the hook. `WorkspaceManager.setup()` creates the `.vrs/observations/` directory.

**3.1c consumer expectations:**
- 3.1c-03 (Observation Parser) reads these files and produces `ObservationSummary`.
- Each line is independently parseable (crash-safe append-only design).
- Invalid JSON lines are skipped with warnings by the parser.

---

## Jujutsu Workspace API

```python
class WorkspaceManager:
    # ... existing methods ...

    def create_workspace(self, name: str, source_dir: Path | None = None) -> Path:
        """Create an isolated Jujutsu workspace for test execution.

        Uses `jj workspace add {name}` to create an isolated copy of the
        repository state. The workspace shares the same repository but has
        its own working copy — changes in the workspace don't affect the
        main worktree.

        Args:
            name: Workspace name (e.g., "test-run-001", "improvement-exp-1").
                Must be unique within the repository.
            source_dir: Directory to create workspace from. Defaults to
                self._base_dir. Must be inside a Jujutsu repository.

        Returns:
            Absolute path to the created workspace directory.

        Raises:
            RuntimeError: If `jj workspace add` fails (e.g., Jujutsu not installed,
                name already exists, not in a jj repository).
            FileNotFoundError: If source_dir doesn't exist.
        """
        ...

    def forget_workspace(self, name: str) -> None:
        """Remove a Jujutsu workspace without deleting files.

        Uses `jj workspace forget {name}` to detach the workspace from
        the repository. The working copy directory remains on disk but is
        no longer tracked by Jujutsu.

        Args:
            name: Workspace name previously created via create_workspace().

        Raises:
            RuntimeError: If `jj workspace forget` fails (e.g., workspace
                doesn't exist).
        """
        ...

    def rollback(self, op_id: str, workspace_dir: Path | None = None) -> None:
        """Rollback workspace to a previous Jujutsu operation.

        Uses `jj op restore {op_id}` to revert the workspace state.

        Args:
            op_id: Jujutsu operation ID to restore (from `jj op log`).
            workspace_dir: Directory to run the rollback in. Defaults to
                self._base_dir.

        Raises:
            RuntimeError: If `jj op restore` fails (e.g., invalid op_id).
        """
        ...

    def list_workspaces(self) -> list[str]:
        """List all Jujutsu workspaces in the repository.

        Uses `jj workspace list` to enumerate workspaces.

        Returns:
            List of workspace names. Includes the default workspace.
            Empty list if not in a Jujutsu repository.
        """
        ...
```

**3.1c consumer expectations:**
- 3.1c-12 uses `create_workspace()` for improvement loop sandboxing.
- 3.1c-12 uses `forget_workspace()` for cleanup after improvement experiments.
- 3.1c-12 uses `rollback()` to restore workspace state if improvement fails.
- Multiple workspaces can coexist simultaneously (no limit).

**Failure modes:**
- `create_workspace()` raises `RuntimeError` if Jujutsu is not installed. 3.1c should handle this gracefully with a fallback to `.claude.sandbox/` copy approach.
- `forget_workspace()` raises `RuntimeError` if workspace doesn't exist (idempotency not guaranteed — caller should catch).
- `list_workspaces()` returns empty list (not error) if not in a jj repository.

---

## SendMessage Capture Format

For inter-agent message capture (used by 3.1c-05 debrief and 3.1c-11 orchestrator tests):

```python
@dataclass
class CapturedMessage:
    """A captured SendMessage exchange from the event stream.

    Attributes:
        agent_id: Sender agent identifier.
        recipient: Recipient agent identifier.
        content: Full message body. MUST be the complete text, not a preview
            or metadata-only stub.
        timestamp: ISO 8601 timestamp.
        message_type: "dm" (direct message), "broadcast", or "shutdown_request".
    """

    agent_id: str
    recipient: str
    content: str
    timestamp: str
    message_type: str = "dm"
```

**Critical requirement:** Content MUST be the full message body. Previous implementations
captured only metadata stubs. 3.1c-05 (debrief) and 3.1c-11 (orchestrator) need the
actual message text to evaluate evidence flow and debate quality.

---

## Example Usage

```python
from tests.workflow_harness.lib.workspace import WorkspaceManager, HookConfig
from pathlib import Path

mgr = WorkspaceManager(Path("examples/testing"))

# Setup with observation hooks (3.1c-02 pattern)
hooks = [
    HookConfig("PreToolUse", "python3 .claude/hooks/observe_tools.py", timeout=10),
    HookConfig("PostToolUse", "python3 .claude/hooks/observe_tools.py", timeout=10),
    HookConfig("SubagentStop", "python3 .claude/hooks/observe_agents.py"),
    HookConfig("TeammateIdle", "python3 .claude/hooks/debrief_gate.py", timeout=60),
]
ws = mgr.setup(Path("examples/testing/vault-project"), hook_configs=hooks)

# Jujutsu workspace isolation (3.1c-12 pattern)
test_ws = mgr.create_workspace("improvement-exp-1", source_dir=ws)
# ... run improvement experiment in test_ws ...
mgr.forget_workspace("improvement-exp-1")

# List workspaces
workspaces = mgr.list_workspaces()
# ["default", "improvement-exp-1"]  (before forget)

# Rollback if needed
mgr.rollback("abc123", workspace_dir=test_ws)
```
