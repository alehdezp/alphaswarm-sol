"""Tests for output_collector.py — OutputCollector, TeamObservation, and related models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .lib.output_collector import (
    AgentObservation,
    CollectedOutput,
    DebateTurn,
    EvaluationGuidance,
    EvidenceFlowEdge,
    InboxMessage,
    OutputCollector,
    TeamObservation,
)
from .lib.controller_events import EventStream
from .lib.transcript_parser import BSKGQuery, TranscriptParser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl(tmp_path: Path, records: list[dict]) -> Path:
    """Write records as JSONL and return the file path."""
    p = tmp_path / "test_transcript.jsonl"
    with open(p, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return p


def _make_transcript(tmp_path: Path, tool_name: str = "Bash", command: str = "ls") -> TranscriptParser:
    """Create a minimal TranscriptParser with one tool call."""
    records = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tu_1",
                        "name": tool_name,
                        "input": {"command": command},
                    }
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tu_1",
                        "content": "result data",
                    }
                ]
            },
        },
    ]
    return TranscriptParser(_write_jsonl(tmp_path, records))


def _make_bskg_transcript(tmp_path: Path) -> TranscriptParser:
    """Create a transcript with alphaswarm query calls."""
    records = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tu_1",
                        "name": "Bash",
                        "input": {"command": "uv run alphaswarm query 'reentrancy'"},
                    }
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tu_1",
                        "content": "Found 3 vulnerable functions in withdraw",
                    }
                ]
            },
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tu_2",
                        "name": "Write",
                        "input": {
                            "file_path": "/report.md",
                            "content": "Found 3 vulnerable functions in withdraw confirmed",
                        },
                    }
                ]
            },
        },
    ]
    return TranscriptParser(_write_jsonl(tmp_path, records))


# ---------------------------------------------------------------------------
# InboxMessage tests
# ---------------------------------------------------------------------------


class TestInboxMessage:
    def test_creation_with_defaults(self):
        msg = InboxMessage(
            sender="agent-1",
            recipient="agent-2",
            content="Hello",
            timestamp="2026-01-15T10:00:00Z",
        )
        assert msg.sender == "agent-1"
        assert msg.recipient == "agent-2"
        assert msg.message_type == "general"

    def test_creation_with_custom_type(self):
        msg = InboxMessage(
            sender="agent-1",
            recipient="broadcast",
            content="Shutdown",
            timestamp="2026-01-15T10:00:00Z",
            message_type="shutdown_request",
        )
        assert msg.message_type == "shutdown_request"


# ---------------------------------------------------------------------------
# AgentObservation tests
# ---------------------------------------------------------------------------


class TestAgentObservation:
    def test_creation_with_defaults(self):
        obs = AgentObservation(agent_id="a1", agent_type="attacker")
        assert obs.agent_id == "a1"
        assert obs.agent_type == "attacker"
        assert obs.transcript is None
        assert obs.bskg_queries == []
        assert obs.messages_sent == []
        assert obs.messages_received == []

    def test_creation_with_transcript(self, tmp_path: Path):
        transcript = _make_transcript(tmp_path)
        obs = AgentObservation(
            agent_id="a1",
            agent_type="attacker",
            transcript=transcript,
        )
        assert obs.transcript is not None
        assert len(obs.transcript.get_tool_calls()) == 1


# ---------------------------------------------------------------------------
# TeamObservation tests
# ---------------------------------------------------------------------------


class TestTeamObservation:
    def test_get_agent_by_type_returns_correct_agent(self):
        attacker = AgentObservation(agent_id="a1", agent_type="attacker")
        defender = AgentObservation(agent_id="a2", agent_type="defender")
        team = TeamObservation(agents={"a1": attacker, "a2": defender})

        found = team.get_agent_by_type("attacker")
        assert found is not None
        assert found.agent_id == "a1"

        found = team.get_agent_by_type("defender")
        assert found is not None
        assert found.agent_id == "a2"

    def test_get_agent_by_type_case_insensitive(self):
        attacker = AgentObservation(agent_id="a1", agent_type="Attacker")
        team = TeamObservation(agents={"a1": attacker})
        found = team.get_agent_by_type("attacker")
        assert found is not None

    def test_get_agent_by_type_returns_none_when_not_found(self):
        team = TeamObservation(agents={})
        assert team.get_agent_by_type("attacker") is None

    def test_get_agent_by_type_with_no_agents(self):
        team = TeamObservation()
        assert team.get_agent_by_type("verifier") is None

    def test_cross_agent_evidence_flow_empty_when_no_messages(self):
        attacker = AgentObservation(agent_id="a1", agent_type="attacker")
        team = TeamObservation(agents={"a1": attacker})
        edges = team.cross_agent_evidence_flow()
        assert edges == []

    def test_cross_agent_evidence_flow_traces_messages(self):
        msg = InboxMessage(
            sender="a1",
            recipient="a2",
            content="Found vulnerability in withdraw function",
            timestamp="2026-01-15T10:00:00Z",
        )
        attacker = AgentObservation(
            agent_id="a1",
            agent_type="attacker",
            messages_sent=[msg],
        )
        defender = AgentObservation(
            agent_id="a2",
            agent_type="defender",
            messages_received=[msg],
        )
        team = TeamObservation(agents={"a1": attacker, "a2": defender})

        edges = team.cross_agent_evidence_flow()
        assert len(edges) == 1
        assert edges[0].from_agent == "a1"
        assert edges[0].to_agent == "a2"
        assert edges[0].evidence_type == "finding"

    def test_debate_turns_empty_when_no_messages(self):
        team = TeamObservation(agents={})
        assert team.debate_turns() == []

    def test_debate_turns_ordered_chronologically(self):
        msg1 = InboxMessage(
            sender="a1", recipient="a2",
            content="I found a reentrancy vulnerability",
            timestamp="2026-01-15T10:00:00Z",
        )
        msg2 = InboxMessage(
            sender="a2", recipient="a1",
            content="The function has a guard",
            timestamp="2026-01-15T10:01:00Z",
        )
        attacker = AgentObservation(
            agent_id="a1", agent_type="attacker", messages_sent=[msg1],
        )
        defender = AgentObservation(
            agent_id="a2", agent_type="defender", messages_sent=[msg2],
        )
        team = TeamObservation(agents={"a1": attacker, "a2": defender})

        turns = team.debate_turns()
        assert len(turns) == 2
        assert turns[0].turn_number == 1
        assert turns[0].agent_id == "a1"
        assert turns[0].agent_type == "attacker"
        assert turns[1].turn_number == 2
        assert turns[1].agent_id == "a2"
        assert turns[1].agent_type == "defender"

    def test_team_with_event_stream(self):
        events = EventStream([
            {"type": "agent:spawned", "agent_type": "attacker", "agent_id": "a1"},
        ])
        team = TeamObservation(
            agents={"a1": AgentObservation(agent_id="a1", agent_type="attacker")},
            events=events,
        )
        assert team.events is not None
        assert len(team.events.agents_spawned()) == 1


# ---------------------------------------------------------------------------
# CollectedOutput tests
# ---------------------------------------------------------------------------


class TestCollectedOutput:
    def test_creation_with_all_fields(self, tmp_path: Path):
        transcript = _make_transcript(tmp_path)
        team = TeamObservation(agents={})
        output = CollectedOutput(
            scenario_name="test-scenario",
            run_id="run-001",
            transcript=transcript,
            team_observation=team,
            structured_output={"status": "ok"},
            tool_sequence=["Bash", "Read"],
            bskg_queries=[],
            duration_ms=1500.0,
            cost_usd=0.05,
            failure_notes="",
        )
        assert output.scenario_name == "test-scenario"
        assert output.run_id == "run-001"
        assert output.transcript is not None
        assert output.team_observation is not None
        assert output.structured_output == {"status": "ok"}
        assert output.tool_sequence == ["Bash", "Read"]
        assert output.duration_ms == 1500.0
        assert output.cost_usd == 0.05

    def test_creation_with_defaults(self):
        output = CollectedOutput(scenario_name="s", run_id="r")
        assert output.transcript is None
        assert output.team_observation is None
        assert output.structured_output is None
        assert output.tool_sequence == []
        assert output.bskg_queries == []
        assert output.duration_ms == 0.0
        assert output.cost_usd == 0.0
        assert output.failure_notes == ""


# ---------------------------------------------------------------------------
# EvaluationGuidance tests
# ---------------------------------------------------------------------------


class TestEvaluationGuidance:
    def test_creation_with_defaults(self):
        guidance = EvaluationGuidance()
        assert guidance.reasoning_questions == []
        assert guidance.hooks_if_failed == []

    def test_creation_with_custom_values(self):
        guidance = EvaluationGuidance(
            reasoning_questions=["Did the agent query the graph?"],
            hooks_if_failed=["hooks/extra_logging.py"],
        )
        assert len(guidance.reasoning_questions) == 1
        assert guidance.hooks_if_failed == ["hooks/extra_logging.py"]

    def test_to_pydantic_dict(self):
        guidance = EvaluationGuidance(
            reasoning_questions=["Q1"],
            hooks_if_failed=["h1.py"],
        )
        d = guidance.to_pydantic_dict()
        assert d == {
            "reasoning_questions": ["Q1"],
            "hooks_if_failed": ["h1.py"],
        }


# ---------------------------------------------------------------------------
# OutputCollector tests
# ---------------------------------------------------------------------------


class TestOutputCollector:
    def test_collect_builds_output_from_transcript(self, tmp_path: Path):
        transcript = _make_bskg_transcript(tmp_path)
        collector = OutputCollector()
        output = collector.collect(
            scenario_name="reentrancy-basic",
            run_id="run-001",
            transcript=transcript,
            duration_ms=2000.0,
            cost_usd=0.10,
        )
        assert output.scenario_name == "reentrancy-basic"
        assert output.run_id == "run-001"
        assert len(output.tool_sequence) == 2  # Bash + Write
        assert len(output.bskg_queries) == 1
        assert output.bskg_queries[0].query_type == "query"
        assert output.duration_ms == 2000.0
        assert output.cost_usd == 0.10
        assert output.team_observation is None

    def test_collect_with_no_transcript(self):
        collector = OutputCollector()
        output = collector.collect(
            scenario_name="empty",
            run_id="run-002",
        )
        assert output.transcript is None
        assert output.tool_sequence == []
        assert output.bskg_queries == []

    def test_collect_with_team_observation(self, tmp_path: Path):
        transcript = _make_transcript(tmp_path)
        attacker = AgentObservation(agent_id="a1", agent_type="attacker")
        team = TeamObservation(agents={"a1": attacker})
        collector = OutputCollector()
        output = collector.collect(
            scenario_name="team-test",
            run_id="run-003",
            transcript=transcript,
            team_observation=team,
        )
        assert output.team_observation is not None
        assert "a1" in output.team_observation.agents

    def test_collect_with_failure_notes(self, tmp_path: Path):
        collector = OutputCollector()
        output = collector.collect(
            scenario_name="fail",
            run_id="run-004",
            failure_notes="Agent crashed on tool call 3",
        )
        assert output.failure_notes == "Agent crashed on tool call 3"

    def test_summary_produces_readable_string(self, tmp_path: Path):
        transcript = _make_bskg_transcript(tmp_path)
        collector = OutputCollector()
        output = collector.collect(
            scenario_name="reentrancy-basic",
            run_id="run-001",
            transcript=transcript,
            duration_ms=2000.0,
            cost_usd=0.10,
        )
        summary = collector.summary(output)
        assert "reentrancy-basic" in summary
        assert "run-001" in summary
        assert "Tools used:" in summary
        assert "BSKG queries:" in summary
        assert "Citation rate:" in summary
        assert "Duration:" in summary
        assert "Cost:" in summary

    def test_summary_includes_failure_notes(self, tmp_path: Path):
        collector = OutputCollector()
        output = collector.collect(
            scenario_name="fail",
            run_id="run-004",
            failure_notes="Timeout after 60s",
        )
        summary = collector.summary(output)
        assert "Failure: Timeout after 60s" in summary

    def test_summary_includes_team_info(self, tmp_path: Path):
        transcript = _make_transcript(tmp_path)
        team = TeamObservation(agents={
            "a1": AgentObservation(agent_id="a1", agent_type="attacker"),
            "a2": AgentObservation(agent_id="a2", agent_type="defender"),
        })
        collector = OutputCollector()
        output = collector.collect(
            scenario_name="team",
            run_id="run-005",
            transcript=transcript,
            team_observation=team,
        )
        summary = collector.summary(output)
        assert "Team agents: 2" in summary
