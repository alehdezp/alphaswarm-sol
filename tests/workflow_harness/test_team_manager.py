"""Tests for TeamManager — Agent Teams lifecycle and message capture."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from .lib.team_manager import TeamManager
from .lib.output_collector import AgentObservation, InboxMessage, TeamObservation


class TestTeamManagerCreation:
    """Test TeamManager initialization and team creation."""

    def test_default_team_name(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        assert tm.team_name.startswith("test-")
        assert len(tm.team_name) == 13  # "test-" + 8 hex chars

    def test_custom_team_name(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path, team_name="my-team")
        assert tm.team_name == "my-team"

    def test_workspace_path_resolved(self, tmp_path: Path) -> None:
        relative = tmp_path / "sub" / ".." / "sub"
        relative.mkdir(parents=True, exist_ok=True)
        tm = TeamManager(workspace_path=relative)
        assert tm.workspace_path == (tmp_path / "sub").resolve()

    def test_initial_state(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        assert not tm.active
        assert tm.messages == []
        assert tm.teammates == {}

    def test_create_team_returns_name(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path, team_name="audit-01")
        name = tm.create_team("Security audit team")
        assert name == "audit-01"
        assert tm.active

    def test_create_team_sets_env_var(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        tm.create_team()
        assert os.environ.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1"

    def test_create_team_twice_raises(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        tm.create_team()
        with pytest.raises(RuntimeError, match="already active"):
            tm.create_team()


class TestTeamManagerSpawn:
    """Test teammate spawning."""

    @pytest.fixture
    def active_team(self, tmp_path: Path) -> TeamManager:
        tm = TeamManager(workspace_path=tmp_path, team_name="test-team")
        tm.create_team()
        return tm

    def test_spawn_teammate(self, active_team: TeamManager) -> None:
        agent_id = active_team.spawn_teammate("attacker", "vrs-attacker", "Find vulns")
        assert agent_id == "test-team-attacker"
        assert "attacker" in active_team.teammates
        assert active_team.teammates["attacker"]["agent_type"] == "vrs-attacker"

    def test_spawn_duplicate_raises(self, active_team: TeamManager) -> None:
        active_team.spawn_teammate("attacker", "vrs-attacker", "Find vulns")
        with pytest.raises(ValueError, match="already exists"):
            active_team.spawn_teammate("attacker", "vrs-attacker", "Find vulns again")

    def test_spawn_without_active_team_raises(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        with pytest.raises(RuntimeError, match="not active"):
            tm.spawn_teammate("attacker", "vrs-attacker", "Find vulns")


class TestMessageCapture:
    """Test full message content capture."""

    @pytest.fixture
    def team_with_agents(self, tmp_path: Path) -> TeamManager:
        tm = TeamManager(workspace_path=tmp_path, team_name="msg-team")
        tm.create_team("Message test team")
        tm.spawn_teammate("attacker", "vrs-attacker", "Find vulns")
        tm.spawn_teammate("defender", "vrs-defender", "Check guards")
        return tm

    def test_send_message_captures_full_content(self, team_with_agents: TeamManager) -> None:
        content = "Analyze the withdraw() function for reentrancy vulnerabilities"
        team_with_agents.send_message("attacker", content)

        assert len(team_with_agents.messages) == 1
        msg = team_with_agents.messages[0]
        assert msg["sender"] == "orchestrator"
        assert msg["recipient"] == "attacker"
        assert msg["content"] == content  # FULL content, not truncated
        assert msg["message_type"] == "message"
        assert msg["timestamp"]  # ISO 8601 timestamp present

    def test_send_message_to_unknown_raises(self, team_with_agents: TeamManager) -> None:
        with pytest.raises(ValueError, match="Unknown recipient"):
            team_with_agents.send_message("verifier", "Check this")

    def test_send_message_without_active_team_raises(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        with pytest.raises(RuntimeError, match="not active"):
            tm.send_message("attacker", "Check this")

    def test_broadcast_sends_to_all(self, team_with_agents: TeamManager) -> None:
        team_with_agents.broadcast("New evidence found")
        assert len(team_with_agents.messages) == 2
        recipients = {m["recipient"] for m in team_with_agents.messages}
        assert recipients == {"attacker", "defender"}
        # All should be broadcast type
        assert all(m["message_type"] == "broadcast" for m in team_with_agents.messages)
        # All should have same content
        assert all(m["content"] == "New evidence found" for m in team_with_agents.messages)

    def test_broadcast_without_active_team_raises(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        with pytest.raises(RuntimeError, match="not active"):
            tm.broadcast("Hello")

    def test_multiple_messages_preserve_order(self, team_with_agents: TeamManager) -> None:
        team_with_agents.send_message("attacker", "First")
        team_with_agents.send_message("defender", "Second")
        team_with_agents.send_message("attacker", "Third")

        assert len(team_with_agents.messages) == 3
        assert team_with_agents.messages[0]["content"] == "First"
        assert team_with_agents.messages[1]["content"] == "Second"
        assert team_with_agents.messages[2]["content"] == "Third"


class TestTeamObservation:
    """Test TeamObservation building from captured data."""

    def test_get_team_observation_empty(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        tm.create_team()
        obs = tm.get_team_observation()
        assert isinstance(obs, TeamObservation)
        assert obs.agents == {}

    def test_get_team_observation_with_agents(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path, team_name="obs-team")
        tm.create_team()
        tm.spawn_teammate("attacker", "vrs-attacker", "Find vulns")
        tm.spawn_teammate("defender", "vrs-defender", "Check guards")

        tm.send_message("attacker", "Check reentrancy")
        tm.send_message("defender", "Validate access controls")

        obs = tm.get_team_observation()
        assert len(obs.agents) == 2

        # Check attacker observation
        attacker = obs.get_agent_by_type("vrs-attacker")
        assert attacker is not None
        assert attacker.agent_id == "obs-team-attacker"
        assert len(attacker.messages_received) == 1
        assert attacker.messages_received[0].content == "Check reentrancy"

        # Check defender observation
        defender = obs.get_agent_by_type("vrs-defender")
        assert defender is not None
        assert len(defender.messages_received) == 1
        assert defender.messages_received[0].content == "Validate access controls"

    def test_observation_messages_are_inbox_messages(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path, team_name="inbox-team")
        tm.create_team()
        tm.spawn_teammate("attacker", "vrs-attacker", "Task")
        tm.send_message("attacker", "Analyze this")

        obs = tm.get_team_observation()
        attacker = obs.get_agent_by_type("vrs-attacker")
        assert attacker is not None
        msg = attacker.messages_received[0]
        assert isinstance(msg, InboxMessage)
        assert msg.sender == "orchestrator"
        assert msg.recipient == "attacker"
        assert msg.content == "Analyze this"
        assert msg.message_type == "message"

    def test_observation_transcript_none_when_no_files(self, tmp_path: Path) -> None:
        """Transcript should be None when no JSONL file exists."""
        tm = TeamManager(workspace_path=tmp_path)
        tm.create_team()
        tm.spawn_teammate("attacker", "vrs-attacker", "Task")
        obs = tm.get_team_observation()
        attacker = obs.get_agent_by_type("vrs-attacker")
        assert attacker is not None
        assert attacker.transcript is None
        assert attacker.bskg_queries == []

    def test_observation_includes_explicit_event_stream(self, tmp_path: Path) -> None:
        """set_event_stream should attach events to TeamObservation."""
        tm = TeamManager(workspace_path=tmp_path)
        tm.create_team()
        tm.spawn_teammate("attacker", "vrs-attacker", "Task")
        tm.set_event_stream([{"type": "agent:spawned", "agent_id": "a1"}])

        obs = tm.get_team_observation()
        assert obs.events is not None
        assert obs.events.has_event("agent:spawned")

    def test_observation_loads_event_stream_from_session(self, tmp_path: Path) -> None:
        """TeamManager should load EventStream from .vrs/testing/session.json."""
        tm = TeamManager(workspace_path=tmp_path)
        tm.create_team()
        tm.spawn_teammate("attacker", "vrs-attacker", "Task")

        session_dir = tmp_path / ".vrs" / "testing"
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "session.json").write_text(json.dumps({
            "events": [
                {"type": "agent:spawned", "agent_id": "a1"},
                {"type": "task:completed", "agent_id": "a1"},
            ],
        }))

        obs = tm.get_team_observation()
        assert obs.events is not None
        assert obs.events.has_event("agent:spawned")
        assert obs.events.has_event("task:completed")


class TestShutdown:
    """Test shutdown and cleanup."""

    def test_shutdown_teammate(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        tm.create_team()
        tm.spawn_teammate("attacker", "vrs-attacker", "Task")
        tm.shutdown_teammate("attacker")

        assert len(tm.messages) == 1
        assert tm.messages[0]["message_type"] == "shutdown_request"
        assert tm.messages[0]["recipient"] == "attacker"

    def test_shutdown_unknown_raises(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        tm.create_team()
        with pytest.raises(ValueError, match="Unknown teammate"):
            tm.shutdown_teammate("nonexistent")

    def test_shutdown_all(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        tm.create_team()
        tm.spawn_teammate("attacker", "vrs-attacker", "Task")
        tm.spawn_teammate("defender", "vrs-defender", "Task")
        tm.shutdown_all()

        shutdown_msgs = [m for m in tm.messages if m["message_type"] == "shutdown_request"]
        assert len(shutdown_msgs) == 2

    def test_shutdown_all_when_inactive_noop(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        tm.shutdown_all()  # Should not raise

    def test_delete_team(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        tm.create_team()
        assert tm.active
        tm.delete_team()
        assert not tm.active

    def test_delete_team_idempotent(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        tm.create_team()
        tm.delete_team()
        tm.delete_team()  # Should not raise


class TestContextManager:
    """Test context manager ensures cleanup."""

    def test_context_manager_calls_shutdown_and_delete(self, tmp_path: Path) -> None:
        with TeamManager(workspace_path=tmp_path) as tm:
            tm.create_team()
            tm.spawn_teammate("attacker", "vrs-attacker", "Task")

        # After context exit, team should be inactive
        assert not tm.active
        # Shutdown messages should have been sent
        shutdown_msgs = [m for m in tm.messages if m["message_type"] == "shutdown_request"]
        assert len(shutdown_msgs) == 1

    def test_context_manager_cleanup_on_exception(self, tmp_path: Path) -> None:
        tm = TeamManager(workspace_path=tmp_path)
        with pytest.raises(ValueError):
            with tm:
                tm.create_team()
                tm.spawn_teammate("attacker", "vrs-attacker", "Task")
                raise ValueError("Simulated error")

        # Even on exception, cleanup should have occurred
        assert not tm.active

    def test_context_manager_no_orphan_teams(self, tmp_path: Path) -> None:
        """Ensure no orphan teams remain after context manager exit."""
        managers: list[TeamManager] = []
        for i in range(3):
            with TeamManager(workspace_path=tmp_path, team_name=f"team-{i}") as tm:
                tm.create_team()
                tm.spawn_teammate("worker", "vrs-attacker", f"Task {i}")
                managers.append(tm)

        # All should be inactive
        for tm in managers:
            assert not tm.active


class TestSandbox:
    """Test sandbox .claude/ copying."""

    def test_setup_sandbox_copies_skills(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create a fake skills directory
        skills_src = tmp_path / "source_skills"
        skills_src.mkdir()
        (skills_src / "vrs-audit").mkdir()
        (skills_src / "vrs-audit" / "SKILL.md").write_text("# VRS Audit Skill")

        tm = TeamManager(workspace_path=workspace)
        tm.setup_sandbox(skills_dir=skills_src)

        dest = workspace / ".claude" / "skills" / "vrs-audit" / "SKILL.md"
        assert dest.exists()
        assert dest.read_text() == "# VRS Audit Skill"

    def test_setup_sandbox_copies_agents(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        agents_src = tmp_path / "source_agents"
        agents_src.mkdir()
        (agents_src / "attacker.md").write_text("# Attacker Agent")

        tm = TeamManager(workspace_path=workspace)
        tm.setup_sandbox(agents_dir=agents_src)

        dest = workspace / ".claude" / "agents" / "attacker.md"
        assert dest.exists()
        assert dest.read_text() == "# Attacker Agent"

    def test_setup_sandbox_none_dirs_noop(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        tm = TeamManager(workspace_path=workspace)
        tm.setup_sandbox()  # No dirs, should not create anything
        assert not (workspace / ".claude" / "skills").exists()
        assert not (workspace / ".claude" / "agents").exists()

    def test_setup_sandbox_nonexistent_dir_skipped(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        tm = TeamManager(workspace_path=workspace)
        tm.setup_sandbox(skills_dir=tmp_path / "nonexistent")
        assert not (workspace / ".claude" / "skills").exists()

    def test_teardown_sandbox_removes_copied_dirs(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        skills_src = tmp_path / "source_skills"
        skills_src.mkdir()
        (skills_src / "test-skill").mkdir()

        agents_src = tmp_path / "source_agents"
        agents_src.mkdir()
        (agents_src / "test-agent.md").write_text("agent")

        tm = TeamManager(workspace_path=workspace)
        tm.setup_sandbox(skills_dir=skills_src, agents_dir=agents_src)
        assert (workspace / ".claude" / "skills").exists()
        assert (workspace / ".claude" / "agents").exists()

        tm.teardown_sandbox()
        assert not (workspace / ".claude" / "skills").exists()
        assert not (workspace / ".claude" / "agents").exists()

    def test_teardown_sandbox_idempotent(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        tm = TeamManager(workspace_path=workspace)
        tm.teardown_sandbox()  # No setup done, should not raise
        tm.teardown_sandbox()  # Called twice, should not raise

    def test_delete_team_calls_teardown(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        skills_src = tmp_path / "source_skills"
        skills_src.mkdir()
        (skills_src / "skill.md").write_text("skill")

        tm = TeamManager(workspace_path=workspace)
        tm.create_team()
        tm.setup_sandbox(skills_dir=skills_src)
        assert (workspace / ".claude" / "skills").exists()

        tm.delete_team()
        assert not (workspace / ".claude" / "skills").exists()
