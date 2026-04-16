"""Per-scenario workspace setup and teardown for workflow tests.

Each test scenario runs in an isolated workspace under examples/testing/.
This module handles:
- Copying the hook template into the workspace
- Cleaning .vrs/testing/ artifacts between runs
- Creating .vrs/observations/ for hook output (3.1c convention)
- Reading session metadata written by hooks
- Mapping agent types to JSONL transcript paths
- Jujutsu workspace isolation for repeatable test runs (3.1b-04)
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class HookConfig:
    """Typed hook configuration for install_hooks().

    Provides a structured alternative to the tuple-based extra_hooks API.
    Both APIs coexist -- HookConfig is preferred for new code (3.1c+).

    Attributes:
        event_type: Hook event name (e.g. "PreToolUse", "SubagentStop").
        script_path: Shell command to execute (e.g. "python3 .claude/hooks/observe.py").
        timeout: Max seconds for hook execution (default 30).
        is_async: If True, the hook runs asynchronously (non-blocking).
            Used for bifurcated installation (P11-ADV-2-01): headless mode
            EvaluationRunner installs hooks before ClaudeCodeRunner.run();
            interactive mode requires pre-session setup.
    """

    event_type: str
    script_path: str
    timeout: int = 30
    is_async: bool = False


# Hook template lives alongside the harness code
_HOOKS_DIR = Path(__file__).parent.parent / "hooks"

# Default timeout for hook execution (seconds).
# RS-02 recommends 30s — long enough for marker-file checks, not excessive.
# Claude Code's default is 60s; 5s (the previous value) was too short.
DEFAULT_HOOK_TIMEOUT = 30


class WorkspaceManager:
    """Manage isolated test workspaces for scenario execution.

    Each workspace is a directory under base_dir containing:
    - contracts/*.sol (the code under test)
    - ground-truth.yaml (expected findings)
    - .claude/settings.json (hook configuration, installed by this manager)
    - .vrs/testing/session.json (written by hooks at runtime)
    - .vrs/observations/ (JSONL output from hook scripts)

    Example:
        >>> mgr = WorkspaceManager(Path("examples/testing"))
        >>> ws = mgr.setup(Path("examples/testing/unstoppable"))
        >>> # ... run controller session against ws ...
        >>> info = mgr.get_session_info(ws)
        >>> mgr.cleanup(ws)
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def setup(
        self,
        scenario_dir: Path,
        extra_hooks: list[tuple[str, str] | tuple[str, str, int]] | None = None,
    ) -> Path:
        """Prepare workspace: install hooks, clean .vrs/testing/, return ready path.

        Args:
            scenario_dir: Path to the scenario directory (absolute or relative).
            extra_hooks: Additional hooks as (event_name, command) or
                (event_name, command, timeout) tuples. These are registered
                alongside the default SubagentStop/Stop logging hooks.

        Returns:
            Absolute path to the prepared workspace.
        """
        workspace = scenario_dir.resolve()
        if not workspace.is_dir():
            raise FileNotFoundError(f"Scenario directory not found: {workspace}")

        self.install_hooks(workspace, extra_hooks=extra_hooks)

        # Clean previous test artifacts
        testing_dir = workspace / ".vrs" / "testing"
        if testing_dir.exists():
            shutil.rmtree(testing_dir)

        # Create observations directory for hook JSONL output (3.1c convention)
        self.create_observation_dir(workspace)

        return workspace

    def install_hooks(
        self,
        workspace: Path,
        extra_hooks: list[tuple[str, str] | tuple[str, str, int]] | None = None,
        hook_configs: list[HookConfig] | None = None,
    ) -> None:
        """Install hook scripts and write .claude/settings.json.

        Copies the default log_session.py hook and registers it for
        SubagentStop and Stop events. Additional hooks can be registered
        via extra_hooks (tuple API) or hook_configs (typed API) without
        clobbering existing entries.

        Args:
            workspace: Path to the scenario workspace.
            extra_hooks: Additional hooks as (event_name, command) or
                (event_name, command, timeout) tuples.
            hook_configs: Additional hooks as HookConfig objects (preferred
                for new code). Processed after extra_hooks.
        """
        # Create .claude/hooks/ in workspace
        hooks_dest = workspace / ".claude" / "hooks"
        hooks_dest.mkdir(parents=True, exist_ok=True)

        # Copy default hook script
        hook_src = _HOOKS_DIR / "log_session.py"
        if hook_src.exists():
            shutil.copy2(hook_src, hooks_dest / "log_session.py")

        # Write settings.json with hook registrations
        settings_path = workspace / ".claude" / "settings.json"
        settings = _read_json(settings_path) if settings_path.exists() else {}

        # Merge hooks — preserve existing settings, add ours
        hooks = settings.setdefault("hooks", {})
        _ensure_hook(hooks, "SubagentStop", "python3 .claude/hooks/log_session.py")
        _ensure_hook(hooks, "Stop", "python3 .claude/hooks/log_session.py")

        # Register caller-provided extra hooks (3.1c uses this for observation hooks)
        for entry in extra_hooks or []:
            if len(entry) == 3:
                event_name, command, timeout = entry
            else:
                event_name, command = entry
                timeout = DEFAULT_HOOK_TIMEOUT
            _ensure_hook(hooks, event_name, command, timeout=timeout)

        # Register typed HookConfig entries (preferred API for 3.1c+)
        for hc in hook_configs or []:
            _ensure_hook(
                hooks, hc.event_type, hc.script_path,
                timeout=hc.timeout, is_async=hc.is_async,
            )

        # Stage referenced hook scripts into workspace/.claude/hooks when source
        # files are available (default hooks dir or explicit absolute paths).
        for command in _iter_hook_commands(hooks):
            _stage_hook_script(workspace, command)

        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

    def create_observation_dir(self, workspace: Path) -> Path:
        """Create and return ``workspace/.vrs/observations`` directory."""
        obs_dir = workspace / ".vrs" / "observations"
        obs_dir.mkdir(parents=True, exist_ok=True)
        return obs_dir

    def create_sandbox(self, workspace: Path) -> Path:
        """Fallback sandbox for prompt experimentation.

        Copies ``workspace/.claude`` to ``workspace/.claude.sandbox``.
        If ``.claude`` doesn't exist, creates an empty sandbox directory.
        """
        ws = workspace.resolve()
        claude_dir = ws / ".claude"
        sandbox_dir = ws / ".claude.sandbox"

        if sandbox_dir.exists():
            shutil.rmtree(sandbox_dir)
        if claude_dir.exists():
            shutil.copytree(claude_dir, sandbox_dir)
        else:
            sandbox_dir.mkdir(parents=True, exist_ok=True)
        return sandbox_dir

    def restore_from_sandbox(self, workspace: Path) -> None:
        """Restore ``workspace/.claude`` from ``workspace/.claude.sandbox``."""
        ws = workspace.resolve()
        claude_dir = ws / ".claude"
        sandbox_dir = ws / ".claude.sandbox"

        if not sandbox_dir.exists():
            return
        if claude_dir.exists():
            shutil.rmtree(claude_dir)
        shutil.move(str(sandbox_dir), str(claude_dir))

    def create_jj_workspace(self, corpus_project: Path, run_id: str) -> Path:
        """Compatibility wrapper for 3.1c docs: create Jujutsu workspace."""
        return self.create_workspace(f"test-run-{run_id}", source_dir=corpus_project)

    def forget_jj_workspace(self, workspace: Path, run_id: str) -> None:
        """Compatibility wrapper for 3.1c docs: forget Jujutsu workspace."""
        del workspace  # Included for API compatibility.
        self.forget_workspace(f"test-run-{run_id}")

    def rollback_jj_workspace(self, workspace: Path) -> None:
        """Rollback workspace to previous Jujutsu operation."""
        _require_jj()
        ws = workspace.resolve()
        result = _run_jj(
            ["op", "log", "--limit", "2", "--no-graph", "--template", "self.id()"],
            cwd=ws,
        )
        ops = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if len(ops) < 2:
            raise RuntimeError("Could not determine previous Jujutsu operation for rollback")
        self.rollback(ops[1], workspace_dir=ws)

    def get_session_info(self, workspace: Path) -> dict[str, Any]:
        """Read .vrs/testing/session.json written by hooks.

        Returns empty dict if file doesn't exist yet (hooks haven't fired).
        """
        session_path = workspace / ".vrs" / "testing" / "session.json"
        if not session_path.exists():
            return {}
        return _read_json(session_path)

    def get_transcript_paths(self, workspace: Path) -> dict[str, Path]:
        """Map agent_type → JSONL transcript path from session info.

        Reads the hook-written session.json and extracts transcript paths
        from SubagentStop events.

        Returns:
            Dict mapping agent identifier to transcript file Path.
            Keys are agent_id strings (or "main" for the primary session).
        """
        info = self.get_session_info(workspace)
        paths: dict[str, Path] = {}
        for event in info.get("events", []):
            transcript = event.get("agent_transcript_path")
            agent_id = event.get("agent_id") or event.get("session_id") or "main"
            if transcript:
                p = Path(transcript)
                if p.exists():
                    paths[agent_id] = p
        return paths

    # --- Jujutsu workspace isolation (3.1b-04) ---

    def create_workspace(self, name: str, source_dir: Path | None = None) -> Path:
        """Create an isolated Jujutsu workspace for a test run.

        Uses ``jj workspace add {name}`` to create an isolated copy of the
        repository state. The workspace shares the same repository but has
        its own working copy -- changes in the workspace don't affect the
        main worktree.

        Args:
            name: Workspace name (e.g., "test-run-001"). Must be unique
                within the repository.
            source_dir: Directory to create workspace from. Defaults to
                self._base_dir. Must be inside a Jujutsu repository.

        Returns:
            Absolute path to the created workspace directory.

        Raises:
            RuntimeError: If ``jj`` is not available or workspace creation fails.
            FileNotFoundError: If source_dir doesn't exist.
        """
        _require_jj()
        work_dir = (source_dir or self._base_dir).resolve()
        if not work_dir.is_dir():
            raise FileNotFoundError(f"Source directory not found: {work_dir}")

        workspace_path = work_dir / name
        result = _run_jj(["workspace", "add", str(workspace_path), "--name", name], cwd=work_dir)
        return workspace_path.resolve()

    def forget_workspace(self, name: str) -> None:
        """Clean up a Jujutsu workspace after test run.

        Uses ``jj workspace forget {name}`` to detach the workspace from
        the repository. Idempotent: does not error if workspace already
        forgotten.

        Args:
            name: Workspace name previously created via create_workspace().
        """
        _require_jj()
        try:
            _run_jj(["workspace", "forget", name], cwd=self._base_dir)
        except RuntimeError:
            # Idempotent: silently ignore if workspace doesn't exist
            pass

    def rollback(self, op_id: str, workspace_dir: Path | None = None) -> None:
        """Rollback to a previous Jujutsu operation state.

        Uses ``jj op restore {op_id}`` to revert workspace state.

        Args:
            op_id: Jujutsu operation ID to restore (from ``jj op log``).
            workspace_dir: Directory to run the rollback in. Defaults to
                self._base_dir.

        Raises:
            RuntimeError: If ``jj op restore`` fails (e.g., invalid op_id).
        """
        _require_jj()
        work_dir = (workspace_dir or self._base_dir).resolve()
        _run_jj(["op", "restore", op_id], cwd=work_dir)

    def list_workspaces(self) -> list[str]:
        """List all Jujutsu workspaces for the current repo.

        Uses ``jj workspace list`` to enumerate workspaces.

        Returns:
            List of workspace names. Empty list if not in a jj repository
            or if jj is not available.
        """
        if not shutil.which("jj"):
            return []
        try:
            result = _run_jj(["workspace", "list"], cwd=self._base_dir)
        except RuntimeError:
            return []
        names: list[str] = []
        for line in result.stdout.strip().splitlines():
            # jj workspace list format: "name: description" or just "name"
            # The first token before any colon or whitespace is the name
            stripped = line.strip()
            if stripped:
                name = stripped.split(":")[0].split()[0]
                names.append(name)
        return names

    def snapshot_operation(self) -> str:
        """Capture current Jujutsu operation ID for later rollback.

        Uses ``jj op log --limit 1`` to get the latest operation ID.

        Returns:
            Operation ID string.

        Raises:
            RuntimeError: If jj is not available or command fails.
        """
        _require_jj()
        result = _run_jj(
            ["op", "log", "--limit", "1", "--no-graph", "--template", "self.id()"],
            cwd=self._base_dir,
        )
        op_id = result.stdout.strip()
        if not op_id:
            raise RuntimeError("Could not capture Jujutsu operation ID: empty output")
        return op_id

    def cleanup(self, workspace: Path) -> None:
        """Remove .vrs/testing/ artifacts (not contracts or ground truth)."""
        testing_dir = workspace / ".vrs" / "testing"
        if testing_dir.exists():
            shutil.rmtree(testing_dir)


def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file, returning empty dict on error."""
    try:
        with open(path) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _ensure_hook(
    hooks: dict,
    event_name: str,
    command: str,
    timeout: int = DEFAULT_HOOK_TIMEOUT,
    is_async: bool = False,
) -> None:
    """Ensure a hook command exists for the given event, without duplicating.

    Uses the nested format Claude Code expects::

        {"hooks": [{"type": "command", "command": "...", "timeout": N}]}

    Multiple hooks per event type are supported — each call appends a new
    group if the command isn't already registered.

    Args:
        hooks: The ``settings["hooks"]`` dict to modify in place.
        event_name: Hook event (e.g. ``"SubagentStop"``, ``"PreToolUse"``).
        command: Shell command to execute.
        timeout: Max seconds for hook execution (default 30).
        is_async: If True, mark hook as async in the config (P11-ADV-2-01).
    """
    hook_entry: dict[str, Any] = {
        "type": "command",
        "command": command,
        "timeout": timeout,
    }
    if is_async:
        hook_entry["async"] = True
    event_hooks = hooks.get(event_name, [])
    if not isinstance(event_hooks, list):
        event_hooks = []

    # Check if our command is already registered (dedup by command string)
    for entry in event_hooks:
        if isinstance(entry, dict):
            # Direct hook entry
            if entry.get("command") == command:
                return
            # Nested hooks list
            inner = entry.get("hooks", [])
            for h in inner:
                if isinstance(h, dict) and h.get("command") == command:
                    return

    # Add our hook (using the nested format Claude Code expects)
    event_hooks.append({"hooks": [hook_entry]})
    hooks[event_name] = event_hooks


def _iter_hook_commands(hooks: dict[str, Any]) -> list[str]:
    """Collect all hook command strings from settings hooks dict."""
    commands: list[str] = []
    for event_groups in hooks.values():
        if not isinstance(event_groups, list):
            continue
        for group in event_groups:
            if not isinstance(group, dict):
                continue
            entries = group.get("hooks")
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                cmd = entry.get("command")
                if isinstance(cmd, str) and cmd:
                    commands.append(cmd)
    return commands


def _extract_hook_script_token(command: str) -> str | None:
    """Extract a ``.claude/hooks/*.py`` token from a hook command."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    for token in tokens:
        if ".claude/hooks/" in token and token.endswith(".py"):
            return token
    return None


def _stage_hook_script(workspace: Path, command: str) -> None:
    """Copy referenced hook script into ``workspace/.claude/hooks`` when possible.

    This is best-effort: if no source script is found, the hook registration
    remains and runtime resolution is left to the caller environment.
    """
    token = _extract_hook_script_token(command)
    if token is None:
        return

    script_path = Path(token)
    if script_path.is_absolute():
        src_candidates = [script_path]
        dest = workspace / ".claude" / "hooks" / script_path.name
    else:
        normalized = script_path.as_posix()
        if not normalized.startswith(".claude/hooks/"):
            return
        dest = workspace / normalized
        src_candidates = [
            Path.cwd() / normalized,
            _HOOKS_DIR / script_path.name,
        ]

    if dest.exists():
        return

    for src in src_candidates:
        if src.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            return


# --- Jujutsu helpers ---

_JJ_TIMEOUT = 30  # seconds per jj command


def _require_jj() -> None:
    """Check that jj (Jujutsu) is installed and available on PATH.

    Raises:
        RuntimeError: If ``jj`` binary is not found.
    """
    if not shutil.which("jj"):
        raise RuntimeError(
            "jj not found. Install Jujutsu (https://jj-vcs.github.io/jj/) "
            "to use workspace isolation features."
        )


def _run_jj(
    args: list[str],
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    """Run a jj command with standard error handling.

    Args:
        args: Arguments to pass to ``jj`` (e.g., ["workspace", "add", "name"]).
        cwd: Working directory for the command.

    Returns:
        CompletedProcess result with captured stdout/stderr.

    Raises:
        RuntimeError: If the command fails (non-zero exit code or timeout).
    """
    try:
        result = subprocess.run(
            ["jj", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=_JJ_TIMEOUT,
        )
        return result
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"jj {' '.join(args)} failed (exit {e.returncode}): {e.stderr.strip()}"
        ) from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"jj {' '.join(args)} timed out after {_JJ_TIMEOUT}s"
        ) from e
