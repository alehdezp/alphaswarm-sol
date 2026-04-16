"""Tests for workspace.py — WorkspaceManager."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from .lib import workspace as workspace_module
from .lib.workspace import WorkspaceManager


class TestWorkspaceManager:
    @pytest.fixture
    def scenario_dir(self, tmp_path: Path) -> Path:
        """Create a minimal scenario directory."""
        d = tmp_path / "test-scenario"
        d.mkdir()
        (d / "contracts").mkdir()
        (d / "contracts" / "Vault.sol").write_text("// SPDX-License-Identifier: MIT")
        return d

    @pytest.fixture
    def mgr(self, tmp_path: Path) -> WorkspaceManager:
        return WorkspaceManager(base_dir=tmp_path)

    def test_setup_creates_hooks(self, mgr: WorkspaceManager, scenario_dir: Path):
        ws = mgr.setup(scenario_dir)
        assert ws == scenario_dir.resolve()
        assert (ws / ".claude" / "hooks" / "log_session.py").exists()
        assert (ws / ".claude" / "settings.json").exists()

    def test_setup_writes_settings(self, mgr: WorkspaceManager, scenario_dir: Path):
        mgr.setup(scenario_dir)
        settings = json.loads((scenario_dir / ".claude" / "settings.json").read_text())
        assert "hooks" in settings
        assert "SubagentStop" in settings["hooks"]
        assert "Stop" in settings["hooks"]

    def test_setup_cleans_previous_artifacts(self, mgr: WorkspaceManager, scenario_dir: Path):
        # Create old artifacts
        testing_dir = scenario_dir / ".vrs" / "testing"
        testing_dir.mkdir(parents=True)
        (testing_dir / "session.json").write_text("{}")

        mgr.setup(scenario_dir)
        assert not testing_dir.exists()

    def test_setup_preserves_existing_settings(self, mgr: WorkspaceManager, scenario_dir: Path):
        """Existing settings.json keys should survive hook installation."""
        claude_dir = scenario_dir / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text(json.dumps({"model": "opus"}))

        mgr.setup(scenario_dir)
        settings = json.loads((claude_dir / "settings.json").read_text())
        assert settings["model"] == "opus"
        assert "hooks" in settings

    def test_setup_nonexistent_dir_raises(self, mgr: WorkspaceManager, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            mgr.setup(tmp_path / "nonexistent")

    def test_get_session_info_empty(self, mgr: WorkspaceManager, scenario_dir: Path):
        info = mgr.get_session_info(scenario_dir)
        assert info == {}

    def test_get_session_info_with_data(self, mgr: WorkspaceManager, scenario_dir: Path):
        testing_dir = scenario_dir / ".vrs" / "testing"
        testing_dir.mkdir(parents=True)
        (testing_dir / "session.json").write_text(json.dumps({
            "events": [
                {"agent_id": "a1", "agent_transcript_path": "/tmp/t.jsonl"},
            ]
        }))
        info = mgr.get_session_info(scenario_dir)
        assert len(info["events"]) == 1
        assert info["events"][0]["agent_id"] == "a1"

    def test_get_transcript_paths(self, mgr: WorkspaceManager, scenario_dir: Path, tmp_path: Path):
        # Create a fake transcript file
        transcript = tmp_path / "agent-a1.jsonl"
        transcript.write_text('{"type": "user"}\n')

        testing_dir = scenario_dir / ".vrs" / "testing"
        testing_dir.mkdir(parents=True)
        (testing_dir / "session.json").write_text(json.dumps({
            "events": [
                {"agent_id": "a1", "agent_transcript_path": str(transcript)},
                {"agent_id": "a2", "agent_transcript_path": "/nonexistent.jsonl"},
            ]
        }))
        paths = mgr.get_transcript_paths(scenario_dir)
        assert "a1" in paths
        assert paths["a1"] == transcript
        # a2 doesn't exist, should be excluded
        assert "a2" not in paths

    def test_cleanup(self, mgr: WorkspaceManager, scenario_dir: Path):
        testing_dir = scenario_dir / ".vrs" / "testing"
        testing_dir.mkdir(parents=True)
        (testing_dir / "session.json").write_text("{}")

        mgr.cleanup(scenario_dir)
        assert not testing_dir.exists()
        # .vrs itself may still exist, that's fine
        # contracts should be untouched
        assert (scenario_dir / "contracts" / "Vault.sol").exists()

    def test_cleanup_noop_when_no_artifacts(self, mgr: WorkspaceManager, scenario_dir: Path):
        """Cleanup should not error if nothing to clean."""
        mgr.cleanup(scenario_dir)  # No .vrs/testing/ exists

    def test_idempotent_hook_install(self, mgr: WorkspaceManager, scenario_dir: Path):
        """Installing hooks twice should not duplicate entries."""
        mgr.setup(scenario_dir)
        mgr.setup(scenario_dir)
        settings = json.loads((scenario_dir / ".claude" / "settings.json").read_text())
        # Each event should have exactly 1 hook entry
        assert len(settings["hooks"]["SubagentStop"]) == 1
        assert len(settings["hooks"]["Stop"]) == 1

    def test_hook_timeout_is_30(self, mgr: WorkspaceManager, scenario_dir: Path):
        """Hook timeout must be 30s, not the old 5s default."""
        mgr.setup(scenario_dir)
        settings = json.loads((scenario_dir / ".claude" / "settings.json").read_text())
        for event_name in ("SubagentStop", "Stop"):
            group = settings["hooks"][event_name][0]
            hook_entry = group["hooks"][0]
            assert hook_entry["timeout"] == 30, (
                f"{event_name} timeout should be 30, got {hook_entry['timeout']}"
            )

    def test_observations_dir_created(self, mgr: WorkspaceManager, scenario_dir: Path):
        """setup() must create .vrs/observations/ for hook JSONL output."""
        ws = mgr.setup(scenario_dir)
        obs_dir = ws / ".vrs" / "observations"
        assert obs_dir.is_dir()

    def test_extra_hooks_registered(self, mgr: WorkspaceManager, scenario_dir: Path):
        """Extra hooks passed to setup() should appear in settings.json."""
        mgr.setup(scenario_dir, extra_hooks=[
            ("PreToolUse", "python3 .claude/hooks/observe_tools.py"),
            ("PostToolUse", "python3 .claude/hooks/observe_tools.py", 15),
        ])
        settings = json.loads((scenario_dir / ".claude" / "settings.json").read_text())

        # PreToolUse should be registered with default timeout
        assert "PreToolUse" in settings["hooks"]
        pre_hook = settings["hooks"]["PreToolUse"][0]["hooks"][0]
        assert pre_hook["command"] == "python3 .claude/hooks/observe_tools.py"
        assert pre_hook["timeout"] == 30  # default

        # PostToolUse should be registered with custom timeout
        assert "PostToolUse" in settings["hooks"]
        post_hook = settings["hooks"]["PostToolUse"][0]["hooks"][0]
        assert post_hook["timeout"] == 15  # custom

    def test_extra_hooks_dedup(self, mgr: WorkspaceManager, scenario_dir: Path):
        """Extra hooks with same command as default should not duplicate."""
        mgr.setup(scenario_dir, extra_hooks=[
            ("SubagentStop", "python3 .claude/hooks/log_session.py"),
        ])
        settings = json.loads((scenario_dir / ".claude" / "settings.json").read_text())
        assert len(settings["hooks"]["SubagentStop"]) == 1

    def test_multi_hook_per_event(self, mgr: WorkspaceManager, scenario_dir: Path):
        """Multiple different hooks for the same event should all be registered."""
        mgr.setup(scenario_dir, extra_hooks=[
            ("SubagentStop", "python3 .claude/hooks/debrief_gate.py"),
            ("SubagentStop", "python3 .claude/hooks/observe_stop.py"),
        ])
        settings = json.loads((scenario_dir / ".claude" / "settings.json").read_text())
        # 1 default (log_session) + 2 extra = 3 hook groups
        assert len(settings["hooks"]["SubagentStop"]) == 3
        commands = [
            g["hooks"][0]["command"]
            for g in settings["hooks"]["SubagentStop"]
        ]
        assert "python3 .claude/hooks/log_session.py" in commands
        assert "python3 .claude/hooks/debrief_gate.py" in commands
        assert "python3 .claude/hooks/observe_stop.py" in commands

    def test_extra_hook_script_is_staged_when_source_exists(
        self,
        mgr: WorkspaceManager,
        scenario_dir: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If a referenced extra hook exists in hook source dir, it is copied."""
        hooks_src = tmp_path / "hooks_src"
        hooks_src.mkdir()
        # WorkspaceManager always copies log_session.py from hook source dir.
        (hooks_src / "log_session.py").write_text("# default hook")
        (hooks_src / "observe_tools.py").write_text("# extra hook")

        monkeypatch.setattr(workspace_module, "_HOOKS_DIR", hooks_src)

        ws = mgr.setup(scenario_dir, extra_hooks=[
            ("PreToolUse", "python3 .claude/hooks/observe_tools.py"),
        ])
        assert (ws / ".claude" / "hooks" / "observe_tools.py").exists()

    def test_create_observation_dir_idempotent(self, mgr: WorkspaceManager, scenario_dir: Path) -> None:
        """create_observation_dir can be called repeatedly."""
        p1 = mgr.create_observation_dir(scenario_dir)
        p2 = mgr.create_observation_dir(scenario_dir)
        assert p1 == p2
        assert p1.is_dir()

    def test_sandbox_roundtrip(self, mgr: WorkspaceManager, scenario_dir: Path) -> None:
        """create_sandbox/restore_from_sandbox round-trips .claude state."""
        claude_dir = scenario_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        original = claude_dir / "settings.json"
        original.write_text('{"model":"sonnet"}')

        sandbox = mgr.create_sandbox(scenario_dir)
        assert sandbox.exists()
        # Mutate live .claude and verify restore overwrites it.
        original.write_text('{"model":"opus"}')
        mgr.restore_from_sandbox(scenario_dir)
        restored = (scenario_dir / ".claude" / "settings.json").read_text()
        assert restored == '{"model":"sonnet"}'


class TestJujutsuWorkspaceIsolation:
    """Tests for Jujutsu workspace isolation methods (3.1b-04)."""

    @pytest.fixture
    def mgr(self, tmp_path: Path) -> WorkspaceManager:
        return WorkspaceManager(base_dir=tmp_path)

    def test_create_workspace_raises_when_jj_missing(self, mgr: WorkspaceManager) -> None:
        """create_workspace should raise RuntimeError when jj is not installed."""
        with patch("tests.workflow_harness.lib.workspace.shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="jj not found"):
                mgr.create_workspace("test-ws")

    def test_create_workspace_calls_jj(self, mgr: WorkspaceManager, tmp_path: Path) -> None:
        """create_workspace should call jj workspace add with correct args."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        with (
            patch("tests.workflow_harness.lib.workspace.shutil.which", return_value="/usr/bin/jj"),
            patch("tests.workflow_harness.lib.workspace.subprocess.run", return_value=mock_result) as mock_run,
        ):
            result = mgr.create_workspace("test-ws")
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert cmd[0] == "jj"
            assert "workspace" in cmd
            assert "add" in cmd
            assert "test-ws" in cmd

    def test_create_workspace_source_dir_not_found(self, mgr: WorkspaceManager, tmp_path: Path) -> None:
        """create_workspace should raise FileNotFoundError for missing source_dir."""
        with patch("tests.workflow_harness.lib.workspace.shutil.which", return_value="/usr/bin/jj"):
            with pytest.raises(FileNotFoundError, match="Source directory not found"):
                mgr.create_workspace("test-ws", source_dir=tmp_path / "nonexistent")

    def test_forget_workspace_is_idempotent(self, mgr: WorkspaceManager) -> None:
        """forget_workspace should not raise even if workspace doesn't exist."""
        with (
            patch("tests.workflow_harness.lib.workspace.shutil.which", return_value="/usr/bin/jj"),
            patch(
                "tests.workflow_harness.lib.workspace.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "jj", stderr="No such workspace"),
            ),
        ):
            # Should not raise
            mgr.forget_workspace("nonexistent-ws")

    def test_forget_workspace_calls_jj(self, mgr: WorkspaceManager) -> None:
        """forget_workspace should call jj workspace forget."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        with (
            patch("tests.workflow_harness.lib.workspace.shutil.which", return_value="/usr/bin/jj"),
            patch("tests.workflow_harness.lib.workspace.subprocess.run", return_value=mock_result) as mock_run,
        ):
            mgr.forget_workspace("test-ws")
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert cmd[0] == "jj"
            assert "workspace" in cmd
            assert "forget" in cmd
            assert "test-ws" in cmd

    def test_list_workspaces_parses_output(self, mgr: WorkspaceManager) -> None:
        """list_workspaces should parse jj workspace list output correctly."""
        mock_result = MagicMock()
        mock_result.stdout = "default: (no description)\ntest-ws-1: my test\ntest-ws-2: other\n"
        with (
            patch("tests.workflow_harness.lib.workspace.shutil.which", return_value="/usr/bin/jj"),
            patch("tests.workflow_harness.lib.workspace.subprocess.run", return_value=mock_result),
        ):
            names = mgr.list_workspaces()
            assert "default" in names
            assert "test-ws-1" in names
            assert "test-ws-2" in names

    def test_list_workspaces_empty_when_jj_missing(self, mgr: WorkspaceManager) -> None:
        """list_workspaces should return empty list when jj is not installed."""
        with patch("tests.workflow_harness.lib.workspace.shutil.which", return_value=None):
            names = mgr.list_workspaces()
            assert names == []

    def test_list_workspaces_empty_on_error(self, mgr: WorkspaceManager) -> None:
        """list_workspaces should return empty list on jj command failure."""
        with (
            patch("tests.workflow_harness.lib.workspace.shutil.which", return_value="/usr/bin/jj"),
            patch(
                "tests.workflow_harness.lib.workspace.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "jj", stderr="Not a jj repo"),
            ),
        ):
            names = mgr.list_workspaces()
            assert names == []

    def test_snapshot_operation_extracts_id(self, mgr: WorkspaceManager) -> None:
        """snapshot_operation should extract operation ID from jj op log."""
        mock_result = MagicMock()
        mock_result.stdout = "abc123def456\n"
        with (
            patch("tests.workflow_harness.lib.workspace.shutil.which", return_value="/usr/bin/jj"),
            patch("tests.workflow_harness.lib.workspace.subprocess.run", return_value=mock_result),
        ):
            op_id = mgr.snapshot_operation()
            assert op_id == "abc123def456"

    def test_snapshot_operation_raises_on_empty(self, mgr: WorkspaceManager) -> None:
        """snapshot_operation should raise if jj returns empty output."""
        mock_result = MagicMock()
        mock_result.stdout = "\n"
        with (
            patch("tests.workflow_harness.lib.workspace.shutil.which", return_value="/usr/bin/jj"),
            patch("tests.workflow_harness.lib.workspace.subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(RuntimeError, match="empty output"):
                mgr.snapshot_operation()

    def test_snapshot_operation_raises_when_jj_missing(self, mgr: WorkspaceManager) -> None:
        """snapshot_operation should raise RuntimeError when jj is not installed."""
        with patch("tests.workflow_harness.lib.workspace.shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="jj not found"):
                mgr.snapshot_operation()

    def test_rollback_calls_jj(self, mgr: WorkspaceManager) -> None:
        """rollback should call jj op restore with the operation ID."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        with (
            patch("tests.workflow_harness.lib.workspace.shutil.which", return_value="/usr/bin/jj"),
            patch("tests.workflow_harness.lib.workspace.subprocess.run", return_value=mock_result) as mock_run,
        ):
            mgr.rollback("abc123")
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert cmd[0] == "jj"
            assert "op" in cmd
            assert "restore" in cmd
            assert "abc123" in cmd

    def test_rollback_raises_when_jj_missing(self, mgr: WorkspaceManager) -> None:
        """rollback should raise RuntimeError when jj is not installed."""
        with patch("tests.workflow_harness.lib.workspace.shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="jj not found"):
                mgr.rollback("abc123")

    def test_create_jj_workspace_delegates(self, mgr: WorkspaceManager, tmp_path: Path) -> None:
        """create_jj_workspace should delegate to create_workspace."""
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        with patch.object(mgr, "create_workspace", return_value=tmp_path / "run-ws") as mock_create:
            result = mgr.create_jj_workspace(corpus, "001")
            assert result == tmp_path / "run-ws"
            mock_create.assert_called_once_with("test-run-001", source_dir=corpus)

    def test_forget_jj_workspace_delegates(self, mgr: WorkspaceManager, tmp_path: Path) -> None:
        """forget_jj_workspace should delegate to forget_workspace."""
        with patch.object(mgr, "forget_workspace") as mock_forget:
            mgr.forget_jj_workspace(tmp_path, "001")
            mock_forget.assert_called_once_with("test-run-001")

    def test_rollback_jj_workspace_uses_previous_op(self, mgr: WorkspaceManager, tmp_path: Path) -> None:
        """rollback_jj_workspace should pick previous op and call rollback()."""
        mock_result = MagicMock()
        mock_result.stdout = "op-current\nop-previous\n"
        with (
            patch("tests.workflow_harness.lib.workspace.shutil.which", return_value="/usr/bin/jj"),
            patch("tests.workflow_harness.lib.workspace._run_jj", return_value=mock_result),
            patch.object(mgr, "rollback") as mock_rollback,
        ):
            mgr.rollback_jj_workspace(tmp_path)
            mock_rollback.assert_called_once_with("op-previous", workspace_dir=tmp_path.resolve())
