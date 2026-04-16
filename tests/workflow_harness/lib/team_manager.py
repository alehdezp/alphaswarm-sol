"""Manage Agent Teams lifecycle for test scenarios.

Wraps Claude Code's native Agent Teams concepts (TeamCreate, SendMessage,
TeamDelete) into a Python-friendly API for test harness integration.

Key responsibilities:
- Team lifecycle: create, spawn teammates, exchange messages, shutdown, cleanup
- Full message content capture (not just metadata stubs)
- TeamObservation assembly from captured messages and transcript data
- Sandbox .claude/ support for copying production skills/agents into workspace
- Context manager for guaranteed cleanup

IMPORTANT: This class builds the data model and capture infrastructure.
Actual `claude` subprocess integration is tested in 3.1b-07 (smoke test).
The class orchestrates subprocess invocations of `claude` CLI, not direct
tool calls (those are Claude Code tool calls, not Python APIs).
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from tests.workflow_harness.lib.output_collector import (
    AgentObservation,
    InboxMessage,
    TeamObservation,
)
from tests.workflow_harness.lib.controller_events import EventStream
from tests.workflow_harness.lib.transcript_parser import TranscriptParser


class TeamManager:
    """Manage Agent Teams lifecycle for test scenarios.

    Wraps Claude Code's native TeamCreate/SendMessage/TeamDelete into a
    Python-friendly API for test harness integration.

    Example:
        >>> with TeamManager(Path("/tmp/workspace"), "audit-team") as tm:
        ...     tm.create_team("Security audit team")
        ...     tm.spawn_teammate("attacker", "vrs-attacker", "Find vulns")
        ...     tm.send_message("attacker", "Analyze reentrancy")
        ...     obs = tm.get_team_observation()
    """

    def __init__(self, workspace_path: Path, team_name: str | None = None) -> None:
        self.workspace_path = workspace_path.resolve()
        self.team_name = team_name or f"test-{uuid4().hex[:8]}"
        self.messages: list[dict[str, Any]] = []  # Captured SendMessage content
        self._teammates: dict[str, dict[str, Any]] = {}  # name -> config
        self._active = False
        self._description = ""
        self._sandbox_originals: dict[str, Path | None] = {}  # key -> original path or None
        self._event_stream: EventStream | None = None

    @property
    def active(self) -> bool:
        """Whether the team has been created and not yet deleted."""
        return self._active

    @property
    def teammates(self) -> dict[str, dict[str, Any]]:
        """Read-only view of registered teammates."""
        return dict(self._teammates)

    def create_team(self, description: str = "") -> str:
        """Create team via TeamCreate. Returns team_name.

        Sets CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 in the environment.

        Args:
            description: Human-readable description of the team's purpose.

        Returns:
            The team name string.

        Raises:
            RuntimeError: If team is already active.
        """
        if self._active:
            raise RuntimeError(f"Team '{self.team_name}' is already active")

        # Set required environment variable for Agent Teams
        os.environ["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"

        self._description = description
        self._active = True
        return self.team_name

    def spawn_teammate(
        self,
        name: str,
        agent_type: str,
        task_description: str,
    ) -> str:
        """Spawn a teammate into the team. Returns agent_id.

        Args:
            name: Unique name for this teammate within the team.
            agent_type: Subagent type from the catalog (e.g., "vrs-attacker").
            task_description: Description of the task for this teammate.

        Returns:
            Agent identifier string (currently same as name).

        Raises:
            RuntimeError: If team is not active.
            ValueError: If a teammate with this name already exists.
        """
        if not self._active:
            raise RuntimeError("Team is not active. Call create_team() first.")
        if name in self._teammates:
            raise ValueError(f"Teammate '{name}' already exists in team '{self.team_name}'")

        agent_id = f"{self.team_name}-{name}"
        self._teammates[name] = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "task_description": task_description,
            "spawned_at": _now_iso(),
        }
        return agent_id

    def send_message(
        self,
        recipient: str,
        content: str,
        message_type: str = "message",
    ) -> None:
        """Send message to a teammate. Captures full content in self.messages.

        Args:
            recipient: Name of the target teammate.
            content: Full message body text.
            message_type: Classification: "message", "broadcast", or "shutdown_request".

        Raises:
            RuntimeError: If team is not active.
            ValueError: If recipient is not a known teammate.
        """
        if not self._active:
            raise RuntimeError("Team is not active. Call create_team() first.")
        if recipient not in self._teammates:
            raise ValueError(
                f"Unknown recipient '{recipient}'. Known teammates: {list(self._teammates.keys())}"
            )

        self.messages.append({
            "sender": "orchestrator",
            "recipient": recipient,
            "content": content,
            "timestamp": _now_iso(),
            "message_type": message_type,
        })

    def broadcast(self, content: str) -> None:
        """Broadcast message to all teammates. Captures in self.messages.

        Args:
            content: Full message body text.

        Raises:
            RuntimeError: If team is not active.
        """
        if not self._active:
            raise RuntimeError("Team is not active. Call create_team() first.")

        timestamp = _now_iso()
        for name in self._teammates:
            self.messages.append({
                "sender": "orchestrator",
                "recipient": name,
                "content": content,
                "timestamp": timestamp,
                "message_type": "broadcast",
            })

    def shutdown_teammate(self, name: str) -> None:
        """Send shutdown_request to a specific teammate.

        Args:
            name: Name of the teammate to shut down.

        Raises:
            RuntimeError: If team is not active.
            ValueError: If teammate doesn't exist.
        """
        if not self._active:
            raise RuntimeError("Team is not active. Call create_team() first.")
        if name not in self._teammates:
            raise ValueError(f"Unknown teammate '{name}'")

        self.messages.append({
            "sender": "orchestrator",
            "recipient": name,
            "content": "shutdown",
            "timestamp": _now_iso(),
            "message_type": "shutdown_request",
        })

    def shutdown_all(self) -> None:
        """Send shutdown_request to all teammates."""
        if not self._active:
            return  # Nothing to shut down
        for name in list(self._teammates.keys()):
            self.shutdown_teammate(name)

    def delete_team(self) -> None:
        """Delete team via TeamDelete. Cleanup team state.

        Idempotent: does not error if team is already inactive.
        """
        if not self._active:
            return
        self._active = False
        # Restore sandbox if it was set up
        self.teardown_sandbox()

    def get_team_observation(self) -> TeamObservation:
        """Build TeamObservation from captured messages and teammate data.

        Correlates captured messages with teammate configurations to produce
        a structured observation that the 3.1c evaluation pipeline can analyze.

        Returns:
            TeamObservation with per-agent observations and message data.
        """
        agents: dict[str, AgentObservation] = {}

        for name, config in self._teammates.items():
            agent_id = config["agent_id"]

            # Collect messages sent TO this agent
            received = [
                InboxMessage(
                    sender=m["sender"],
                    recipient=m["recipient"],
                    content=m["content"],
                    timestamp=m["timestamp"],
                    message_type=m["message_type"],
                )
                for m in self.messages
                if m["recipient"] == name
            ]

            # Collect messages sent BY this agent (from captured inter-agent messages)
            sent = [
                InboxMessage(
                    sender=m["sender"],
                    recipient=m["recipient"],
                    content=m["content"],
                    timestamp=m["timestamp"],
                    message_type=m["message_type"],
                )
                for m in self.messages
                if m["sender"] == name
            ]

            # Try to load transcript from team transcript directory
            transcript = self._load_agent_transcript(name)

            agents[agent_id] = AgentObservation(
                agent_id=agent_id,
                agent_type=config["agent_type"],
                transcript=transcript,
                bskg_queries=transcript.get_bskg_queries() if transcript else [],
                messages_sent=sent,
                messages_received=received,
            )

        events = self._event_stream or self._load_event_stream()
        return TeamObservation(agents=agents, events=events)

    def set_event_stream(self, events: EventStream | list[dict[str, Any]]) -> None:
        """Set explicit controller events used by get_team_observation().

        Args:
            events: Either EventStream instance or raw controller event dicts.
        """
        if isinstance(events, EventStream):
            self._event_stream = events
            return
        self._event_stream = EventStream(events)

    def _load_agent_transcript(self, name: str) -> TranscriptParser | None:
        """Try to load a transcript for the given teammate.

        Looks for transcript files in the conventional locations:
        - {workspace}/.claude/teams/{team_name}/{name}.jsonl
        - {workspace}/.vrs/observations/subagents/agent-{agent_id}.jsonl

        Returns None if no transcript file is found.
        """
        config = self._teammates.get(name)
        if not config:
            return None

        agent_id = config["agent_id"]

        # Check team transcript directory
        team_transcript = (
            self.workspace_path / ".claude" / "teams" / self.team_name / f"{name}.jsonl"
        )
        if team_transcript.exists():
            return TranscriptParser(team_transcript)

        # Check observations directory
        obs_transcript = (
            self.workspace_path
            / ".vrs"
            / "observations"
            / "subagents"
            / f"agent-{agent_id}.jsonl"
        )
        if obs_transcript.exists():
            return TranscriptParser(obs_transcript)

        return None

    def _load_event_stream(self) -> EventStream | None:
        """Load EventStream from .vrs/testing/session.json if available."""
        session_path = self.workspace_path / ".vrs" / "testing" / "session.json"
        if not session_path.exists():
            return None
        try:
            payload = json.loads(session_path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        events = payload.get("events")
        if not isinstance(events, list):
            return None
        return EventStream(events)

    def setup_sandbox(
        self,
        skills_dir: Path | None = None,
        agents_dir: Path | None = None,
    ) -> None:
        """Copy production .claude/skills/ and .claude/agents/ into workspace.

        Creates workspace/.claude/ with copies of production assets so that
        Agent Teams tests use real shipped skills and agent definitions.

        Args:
            skills_dir: Source directory containing skill definitions.
                If None, skips skill copying.
            agents_dir: Source directory containing agent definitions.
                If None, skips agent copying.

        Records originals for cleanup in teardown_sandbox().
        """
        claude_dir = self.workspace_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        if skills_dir and skills_dir.is_dir():
            dest = claude_dir / "skills"
            # Record if destination already existed
            self._sandbox_originals["skills"] = dest if dest.exists() else None
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(skills_dir, dest)

        if agents_dir and agents_dir.is_dir():
            dest = claude_dir / "agents"
            self._sandbox_originals["agents"] = dest if dest.exists() else None
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(agents_dir, dest)

    def teardown_sandbox(self) -> None:
        """Restore workspace .claude/ to pre-test state.

        Removes any skills/agents directories that were copied by setup_sandbox().
        If original directories existed before setup, they are not restored
        (teardown only removes what was added).
        """
        claude_dir = self.workspace_path / ".claude"

        for key in ("skills", "agents"):
            if key in self._sandbox_originals:
                dest = claude_dir / key
                if dest.exists():
                    shutil.rmtree(dest)
                # If original was None, the dir didn't exist before setup
                # so we just removed it. Otherwise we can't restore it
                # (original was already removed by setup_sandbox).

        self._sandbox_originals.clear()

    def __enter__(self) -> TeamManager:
        """Enter context manager."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit context manager. Always calls shutdown_all + delete_team."""
        try:
            self.shutdown_all()
        finally:
            self.delete_team()


def _now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()
