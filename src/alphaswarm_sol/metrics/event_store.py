"""Event storage for metrics.

Task 8.2a: Persistence layer for metric events.

Events are stored in daily JSON files in the format:
    .vrs/metrics/events/events-YYYY-MM-DD.json
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .events import (
    DetectionEvent,
    TimingEvent,
    ScaffoldEvent,
    VerdictEvent,
    EventType,
    MetricEvent,
    event_from_dict,
)


class EventStore:
    """Stores metric events to disk.

    Events are organized by day for efficient querying and cleanup.
    """

    def __init__(self, storage_path: Path | str):
        """Initialize event store.

        Args:
            storage_path: Directory to store event files.
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_file_for_date(self, date: datetime) -> Path:
        """Get event file for a specific date."""
        date_str = date.strftime("%Y-%m-%d")
        return self.storage_path / f"events-{date_str}.json"

    def _get_today_file(self) -> Path:
        """Get today's event file."""
        return self._get_file_for_date(datetime.now())

    def _load_events_from_file(self, filepath: Path) -> list[dict[str, Any]]:
        """Load events from a specific file."""
        if not filepath.exists():
            return []
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Corrupted file, return empty
            return []

    def _save_events_to_file(self, filepath: Path, events: list[dict[str, Any]]) -> None:
        """Save events to a specific file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(events, f, indent=2)

    def _generate_id(self) -> str:
        """Generate unique event ID."""
        return f"evt-{uuid.uuid4().hex[:8]}"

    def _append_event(self, event_dict: dict[str, Any]) -> None:
        """Append an event to today's file."""
        filepath = self._get_today_file()
        events = self._load_events_from_file(filepath)
        events.append(event_dict)
        self._save_events_to_file(filepath, events)

    def record_detection(
        self,
        contract_id: str,
        pattern_id: str,
        function_name: str,
        line_number: int,
        expected: bool,
        detected: bool,
    ) -> str:
        """Record a detection event.

        Args:
            contract_id: Contract identifier (e.g., filename)
            pattern_id: Pattern ID (e.g., "vm-001")
            function_name: Function where detection occurred
            line_number: Line number in source
            expected: Whether this was an expected vulnerability (from MANIFEST)
            detected: Whether AlphaSwarm detected it

        Returns:
            Event ID
        """
        event = DetectionEvent(
            event_id=self._generate_id(),
            contract_id=contract_id,
            pattern_id=pattern_id,
            function_name=function_name,
            line_number=line_number,
            expected=expected,
            detected=detected,
        )
        self._append_event(event.to_dict())
        return event.event_id

    def record_timing(
        self,
        operation: str,
        contract_id: str,
        duration_seconds: float,
    ) -> str:
        """Record a timing event.

        Args:
            operation: Operation type ("scan", "build_graph", "query")
            contract_id: Contract identifier
            duration_seconds: Duration in seconds

        Returns:
            Event ID
        """
        event = TimingEvent(
            event_id=self._generate_id(),
            operation=operation,
            contract_id=contract_id,
            duration_seconds=duration_seconds,
        )
        self._append_event(event.to_dict())
        return event.event_id

    def record_scaffold(
        self,
        finding_id: str,
        pattern_id: str,
        compiled: bool,
        error_message: str | None = None,
    ) -> str:
        """Record a scaffold compilation event.

        Args:
            finding_id: Finding identifier
            pattern_id: Pattern ID
            compiled: Whether scaffold compiled successfully
            error_message: Error message if compilation failed

        Returns:
            Event ID
        """
        event = ScaffoldEvent(
            event_id=self._generate_id(),
            finding_id=finding_id,
            pattern_id=pattern_id,
            compiled=compiled,
            error_message=error_message,
        )
        self._append_event(event.to_dict())
        return event.event_id

    def record_verdict(
        self,
        finding_id: str,
        pattern_id: str,
        verdict: str,
        auto_resolved: bool,
        tokens_used: int,
    ) -> str:
        """Record an LLM verdict event.

        Args:
            finding_id: Finding identifier
            pattern_id: Pattern ID
            verdict: Verdict ("confirmed", "rejected", "uncertain")
            auto_resolved: Whether LLM resolved without human escalation
            tokens_used: Number of tokens used

        Returns:
            Event ID
        """
        event = VerdictEvent(
            event_id=self._generate_id(),
            finding_id=finding_id,
            pattern_id=pattern_id,
            verdict=verdict,
            auto_resolved=auto_resolved,
            tokens_used=tokens_used,
        )
        self._append_event(event.to_dict())
        return event.event_id

    def get_events(
        self,
        event_type: EventType | None = None,
        days: int = 1,
    ) -> list[dict[str, Any]]:
        """Get events from the last N days.

        Args:
            event_type: Filter by event type (None for all types)
            days: Number of days to look back (default 1 = today only)

        Returns:
            List of event dictionaries
        """
        all_events: list[dict[str, Any]] = []

        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            filepath = self._get_file_for_date(date)
            all_events.extend(self._load_events_from_file(filepath))

        if event_type:
            all_events = [e for e in all_events if e.get("event_type") == event_type.value]

        return all_events

    def get_events_typed(
        self,
        event_type: EventType | None = None,
        days: int = 1,
    ) -> list[MetricEvent]:
        """Get events as typed dataclasses.

        Args:
            event_type: Filter by event type (None for all types)
            days: Number of days to look back

        Returns:
            List of typed event objects
        """
        event_dicts = self.get_events(event_type=event_type, days=days)
        events: list[MetricEvent] = []

        for data in event_dicts:
            try:
                events.append(event_from_dict(data))
            except (ValueError, KeyError):
                # Skip malformed events
                continue

        return events

    def count_events(
        self,
        event_type: EventType | None = None,
        days: int = 1,
    ) -> int:
        """Count events from the last N days.

        Args:
            event_type: Filter by event type
            days: Number of days to look back

        Returns:
            Event count
        """
        return len(self.get_events(event_type=event_type, days=days))

    def clear(self) -> None:
        """Clear all events (for testing)."""
        for filepath in self.storage_path.glob("events-*.json"):
            filepath.unlink()

    def list_event_files(self) -> list[Path]:
        """List all event files."""
        return sorted(self.storage_path.glob("events-*.json"))
