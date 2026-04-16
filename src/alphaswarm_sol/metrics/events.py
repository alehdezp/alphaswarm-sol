"""Metric event types for recording.

Task 8.2a: Event dataclasses for metric recording.

Events are the raw data that gets recorded. They are later aggregated
to calculate metric values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """Types of metric events."""

    DETECTION = "detection"
    TIMING = "timing"
    SCAFFOLD = "scaffold"
    VERDICT = "verdict"


@dataclass
class DetectionEvent:
    """Records whether a vulnerability was detected.

    Used to calculate:
    - Detection Rate: detected_vulns / expected_vulns
    - False Positive Rate: FP / (FP + TP)
    - Pattern Precision: TP / (TP + FP) per pattern
    """

    event_id: str
    event_type: EventType = field(default=EventType.DETECTION, init=False)
    timestamp: datetime = field(default_factory=datetime.now)

    # Detection context
    contract_id: str = ""
    pattern_id: str = ""
    function_name: str = ""
    line_number: int = 0

    # Outcome
    expected: bool = False  # Was this in MANIFEST.yaml?
    detected: bool = False  # Did VKG find it?

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "contract_id": self.contract_id,
            "pattern_id": self.pattern_id,
            "function_name": self.function_name,
            "line_number": self.line_number,
            "expected": self.expected,
            "detected": self.detected,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DetectionEvent:
        """Deserialize from dictionary."""
        return cls(
            event_id=data["event_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            contract_id=data.get("contract_id", ""),
            pattern_id=data.get("pattern_id", ""),
            function_name=data.get("function_name", ""),
            line_number=data.get("line_number", 0),
            expected=data.get("expected", False),
            detected=data.get("detected", False),
        )


@dataclass
class TimingEvent:
    """Records timing for operations.

    Used to calculate:
    - Time to Detection: avg(scan_duration_per_contract)
    """

    event_id: str
    event_type: EventType = field(default=EventType.TIMING, init=False)
    timestamp: datetime = field(default_factory=datetime.now)

    # Timing context
    operation: str = ""  # "scan", "build_graph", "query"
    contract_id: str = ""
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "contract_id": self.contract_id,
            "duration_seconds": self.duration_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimingEvent:
        """Deserialize from dictionary."""
        return cls(
            event_id=data["event_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            operation=data.get("operation", ""),
            contract_id=data.get("contract_id", ""),
            duration_seconds=data.get("duration_seconds", 0.0),
        )


@dataclass
class ScaffoldEvent:
    """Records scaffold compilation result.

    Used to calculate:
    - Scaffold Compile Rate: compiled_scaffolds / total_scaffolds

    Dependency: Phase 6 (Beads)
    """

    event_id: str
    event_type: EventType = field(default=EventType.SCAFFOLD, init=False)
    timestamp: datetime = field(default_factory=datetime.now)

    # Scaffold context
    finding_id: str = ""
    pattern_id: str = ""

    # Outcome
    compiled: bool = False
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "finding_id": self.finding_id,
            "pattern_id": self.pattern_id,
            "compiled": self.compiled,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScaffoldEvent:
        """Deserialize from dictionary."""
        return cls(
            event_id=data["event_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            finding_id=data.get("finding_id", ""),
            pattern_id=data.get("pattern_id", ""),
            compiled=data.get("compiled", False),
            error_message=data.get("error_message"),
        )


@dataclass
class VerdictEvent:
    """Records LLM verdict on finding.

    Used to calculate:
    - LLM Autonomy: auto_resolved / total_tier_b_findings
    - Token Efficiency: avg(tokens_per_finding_resolution)
    - Escalation Rate: human_escalations / total_tier_b_findings

    Dependency: Phase 6 (Beads) + Phase 11 (LLM)
    """

    event_id: str
    event_type: EventType = field(default=EventType.VERDICT, init=False)
    timestamp: datetime = field(default_factory=datetime.now)

    # Verdict context
    finding_id: str = ""
    pattern_id: str = ""

    # Outcome
    verdict: str = ""  # "confirmed", "rejected", "uncertain"
    auto_resolved: bool = False  # Was human escalation needed?
    tokens_used: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "finding_id": self.finding_id,
            "pattern_id": self.pattern_id,
            "verdict": self.verdict,
            "auto_resolved": self.auto_resolved,
            "tokens_used": self.tokens_used,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerdictEvent:
        """Deserialize from dictionary."""
        return cls(
            event_id=data["event_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            finding_id=data.get("finding_id", ""),
            pattern_id=data.get("pattern_id", ""),
            verdict=data.get("verdict", ""),
            auto_resolved=data.get("auto_resolved", False),
            tokens_used=data.get("tokens_used", 0),
        )


# Type alias for any event
MetricEvent = DetectionEvent | TimingEvent | ScaffoldEvent | VerdictEvent


def event_from_dict(data: dict[str, Any]) -> MetricEvent:
    """Deserialize an event from dictionary based on event_type."""
    event_type = data.get("event_type", "")

    if event_type == EventType.DETECTION.value:
        return DetectionEvent.from_dict(data)
    elif event_type == EventType.TIMING.value:
        return TimingEvent.from_dict(data)
    elif event_type == EventType.SCAFFOLD.value:
        return ScaffoldEvent.from_dict(data)
    elif event_type == EventType.VERDICT.value:
        return VerdictEvent.from_dict(data)
    else:
        raise ValueError(f"Unknown event type: {event_type}")
