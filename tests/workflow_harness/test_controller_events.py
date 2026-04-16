"""Tests for controller_events.py — EventStream and ControllerEvent."""

from __future__ import annotations

import pytest

from .lib.controller_events import ControllerEvent, EventStream


# ---------------------------------------------------------------------------
# ControllerEvent.from_dict
# ---------------------------------------------------------------------------


class TestControllerEventFromDict:
    def test_basic_fields(self):
        raw = {
            "type": "agent:spawned",
            "timestamp": 1700000000.5,
            "agent_id": "abc-123",
            "agent_type": "attacker",
        }
        e = ControllerEvent.from_dict(raw)
        assert e.event_type == "agent:spawned"
        assert e.timestamp == 1700000000.5
        assert e.agent_id == "abc-123"
        assert e.agent_type == "attacker"
        assert e.data is raw

    def test_alternative_key_names(self):
        """Controller may use camelCase or alternative keys."""
        raw = {
            "event": "message",
            "agentId": "def-456",
            "agentType": "defender",
        }
        e = ControllerEvent.from_dict(raw)
        assert e.event_type == "message"
        assert e.agent_id == "def-456"
        assert e.agent_type == "defender"

    def test_subagent_type_key(self):
        raw = {"type": "agent:spawned", "subagent_type": "verifier"}
        e = ControllerEvent.from_dict(raw)
        assert e.agent_type == "verifier"

    def test_missing_fields_default_gracefully(self):
        e = ControllerEvent.from_dict({})
        assert e.event_type == "unknown"
        assert e.timestamp == 0
        assert e.agent_id is None
        assert e.agent_type is None


# ---------------------------------------------------------------------------
# EventStream
# ---------------------------------------------------------------------------


def _make_stream(events: list[dict]) -> EventStream:
    return EventStream(events)


class TestEventStream:
    def test_empty_stream(self):
        stream = _make_stream([])
        assert len(stream) == 0
        assert stream.agents_spawned() == []
        assert stream.agent_ids() == set()
        assert stream.duration_seconds() == 0.0
        assert stream.first_event() is None
        assert stream.last_event() is None

    def test_agents_spawned(self):
        stream = _make_stream([
            {"type": "agent:spawned", "agent_type": "attacker", "agent_id": "a1"},
            {"type": "message", "agent_id": "a1"},
            {"type": "agent:spawned", "agent_type": "defender", "agent_id": "a2"},
        ])
        spawned = stream.agents_spawned()
        assert len(spawned) == 2
        assert spawned[0].agent_type == "attacker"
        assert spawned[1].agent_type == "defender"

    def test_agents_exited(self):
        stream = _make_stream([
            {"type": "agent:exited", "agent_type": "attacker", "agent_id": "a1"},
        ])
        assert len(stream.agents_exited()) == 1

    def test_messages(self):
        stream = _make_stream([
            {"type": "message", "agent_id": "a1"},
            {"type": "message", "agent_id": "a2"},
        ])
        assert len(stream.messages()) == 2

    def test_tasks_completed(self):
        stream = _make_stream([
            {"type": "task:completed", "subject": "Run analysis"},
        ])
        assert len(stream.tasks_completed()) == 1

    def test_agent_ids(self):
        stream = _make_stream([
            {"type": "agent:spawned", "agent_id": "a1"},
            {"type": "message", "agent_id": "a2"},
            {"type": "agent:exited", "agent_id": "a1"},
        ])
        assert stream.agent_ids() == {"a1", "a2"}

    def test_agent_types(self):
        stream = _make_stream([
            {"type": "agent:spawned", "agent_type": "Attacker"},
            {"type": "agent:spawned", "agent_type": "Defender"},
        ])
        assert stream.agent_types() == {"Attacker", "Defender"}

    def test_agent_by_type_case_insensitive(self):
        stream = _make_stream([
            {"type": "agent:spawned", "agent_type": "BSKG Attacker", "agent_id": "a1"},
        ])
        assert stream.agent_by_type("bskg attacker") is not None
        assert stream.agent_by_type("BSKG Attacker") is not None
        assert stream.agent_by_type("nonexistent") is None

    def test_events_for_agent(self):
        stream = _make_stream([
            {"type": "agent:spawned", "agent_id": "a1"},
            {"type": "message", "agent_id": "a2"},
            {"type": "agent:exited", "agent_id": "a1"},
        ])
        a1_events = stream.events_for_agent("a1")
        assert len(a1_events) == 2
        assert a1_events[0].event_type == "agent:spawned"
        assert a1_events[1].event_type == "agent:exited"

    def test_events_between(self):
        stream = _make_stream([
            {"type": "system"},
            {"type": "agent:spawned"},
            {"type": "message"},
            {"type": "agent:exited"},
            {"type": "result"},
        ])
        between = stream.events_between("agent:spawned", "agent:exited")
        assert len(between) == 3
        assert between[0].event_type == "agent:spawned"
        assert between[-1].event_type == "agent:exited"

    def test_events_between_no_end(self):
        """If end event doesn't exist, return from start to end of stream."""
        stream = _make_stream([
            {"type": "agent:spawned"},
            {"type": "message"},
        ])
        between = stream.events_between("agent:spawned", "agent:exited")
        assert len(between) == 2

    def test_duration_seconds(self):
        stream = _make_stream([
            {"type": "start", "timestamp": 100.0},
            {"type": "middle", "timestamp": 110.0},
            {"type": "end", "timestamp": 130.0},
        ])
        assert stream.duration_seconds() == 30.0

    def test_duration_single_event(self):
        stream = _make_stream([{"type": "single", "timestamp": 100.0}])
        assert stream.duration_seconds() == 0.0

    def test_total_cost_usd(self):
        stream = _make_stream([
            {"type": "result", "cost_usd": 0.042},
        ])
        assert stream.total_cost_usd() == pytest.approx(0.042)

    def test_total_cost_camelcase(self):
        stream = _make_stream([
            {"type": "result", "costUsd": 1.23},
        ])
        assert stream.total_cost_usd() == pytest.approx(1.23)

    def test_total_cost_missing(self):
        stream = _make_stream([{"type": "result"}])
        assert stream.total_cost_usd() == 0.0

    def test_has_event(self):
        stream = _make_stream([{"type": "error", "message": "oops"}])
        assert stream.has_event("error")
        assert not stream.has_event("success")

    def test_first_last_event(self):
        stream = _make_stream([
            {"type": "first"},
            {"type": "middle"},
            {"type": "last"},
        ])
        assert stream.first_event().event_type == "first"
        assert stream.last_event().event_type == "last"
