"""Parse controller event stream into typed objects for workflow assertions.

The claude-code-controller emits events as the session progresses:
agent:spawned, agent:exited, message, task:completed, idle, etc.

This module wraps raw event dicts into ControllerEvent dataclasses
and provides an EventStream with query methods for clean test assertions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ControllerEvent:
    """A single event from the controller event stream.

    Attributes:
        event_type: Event kind (agent:spawned, agent:exited, message,
                    task:completed, idle, result, error, system)
        timestamp: Unix timestamp (seconds) when event was emitted
        agent_id: Agent identifier (if applicable)
        agent_type: Subagent type (if applicable, e.g. "BSKG Attacker")
        data: Full event payload dict
    """

    event_type: str
    timestamp: float = 0.0
    agent_id: str | None = None
    agent_type: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ControllerEvent:
        """Create from a raw controller event dict."""
        return cls(
            event_type=raw.get("type", raw.get("event", "unknown")),
            timestamp=float(raw.get("timestamp", 0)),
            agent_id=raw.get("agent_id") or raw.get("agentId"),
            agent_type=raw.get("agent_type") or raw.get("agentType") or raw.get("subagent_type"),
            data=raw,
        )


class EventStream:
    """Queryable collection of controller events.

    Parses raw event dicts into ControllerEvent objects and provides
    filtering/querying methods for test assertions.

    Example:
        >>> stream = EventStream([{"type": "agent:spawned", "agent_type": "attacker"}])
        >>> assert len(stream.agents_spawned()) == 1
    """

    def __init__(self, events: list[dict[str, Any]]) -> None:
        self._events = [ControllerEvent.from_dict(e) for e in events]

    @property
    def events(self) -> list[ControllerEvent]:
        """All events in order."""
        return list(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def of_type(self, event_type: str) -> list[ControllerEvent]:
        """Filter events by type."""
        return [e for e in self._events if e.event_type == event_type]

    def agents_spawned(self) -> list[ControllerEvent]:
        """All agent:spawned events."""
        return self.of_type("agent:spawned")

    def agents_exited(self) -> list[ControllerEvent]:
        """All agent:exited events."""
        return self.of_type("agent:exited")

    def messages(self) -> list[ControllerEvent]:
        """All message events (inter-agent DMs, broadcasts)."""
        return self.of_type("message")

    def tasks_completed(self) -> list[ControllerEvent]:
        """All task:completed events."""
        return self.of_type("task:completed")

    def results(self) -> list[ControllerEvent]:
        """All result events (final output)."""
        return self.of_type("result")

    def errors(self) -> list[ControllerEvent]:
        """All error events."""
        return self.of_type("error")

    def agent_ids(self) -> set[str]:
        """Unique agent IDs seen across all events."""
        return {e.agent_id for e in self._events if e.agent_id}

    def agent_types(self) -> set[str]:
        """Unique agent types seen across all events."""
        return {e.agent_type for e in self._events if e.agent_type}

    def agent_by_type(self, agent_type: str) -> ControllerEvent | None:
        """Find the first spawned event for a given agent type (case-insensitive)."""
        agent_type_lower = agent_type.lower()
        for e in self.agents_spawned():
            if e.agent_type and e.agent_type.lower() == agent_type_lower:
                return e
        return None

    def events_for_agent(self, agent_id: str) -> list[ControllerEvent]:
        """All events for a specific agent ID."""
        return [e for e in self._events if e.agent_id == agent_id]

    def events_between(self, start_type: str, end_type: str) -> list[ControllerEvent]:
        """Events occurring between the first occurrence of start_type and end_type."""
        collecting = False
        result: list[ControllerEvent] = []
        for e in self._events:
            if not collecting and e.event_type == start_type:
                collecting = True
                result.append(e)
            elif collecting:
                result.append(e)
                if e.event_type == end_type:
                    break
        return result

    def duration_seconds(self) -> float:
        """Total duration from first to last event timestamp."""
        timestamps = [e.timestamp for e in self._events if e.timestamp > 0]
        if len(timestamps) < 2:
            return 0.0
        return max(timestamps) - min(timestamps)

    def total_cost_usd(self) -> float:
        """Extract total cost from result events (if present)."""
        for e in self.results():
            cost = e.data.get("cost_usd") or e.data.get("costUsd") or e.data.get("cost")
            if cost is not None:
                try:
                    return float(cost)
                except (ValueError, TypeError):
                    continue
        return 0.0

    def has_event(self, event_type: str) -> bool:
        """Check if any event of the given type exists."""
        return len(self.of_type(event_type)) > 0

    def first_event(self) -> ControllerEvent | None:
        """First event in the stream."""
        return self._events[0] if self._events else None

    def last_event(self) -> ControllerEvent | None:
        """Last event in the stream."""
        return self._events[-1] if self._events else None
