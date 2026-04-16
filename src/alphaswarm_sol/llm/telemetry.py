"""
Telemetry and Metrics Collection

Tracks LLM analysis performance, cost, and quality metrics.
Enables continuous feedback and improvement.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import json
import os
from pathlib import Path


class TriageLevel(Enum):
    """Analysis triage levels."""
    SKIP = 0
    QUICK = 1
    FOCUSED = 2
    DEEP = 3


class Verdict(Enum):
    """Analysis verdict."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    VULNERABLE = "vulnerable"


@dataclass
class AnalysisEvent:
    """Single function analysis telemetry."""
    # Identity
    event_id: str
    timestamp: datetime
    session_id: str

    # Input
    function_id: str
    contract_name: str
    source_tokens: int  # Raw source token count

    # Triage
    triage_level: TriageLevel
    triage_reason: str

    # Context
    context_tokens: int  # After compression
    compression_ratio: float
    context_tier: int  # 1-5

    # LLM Interaction
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    cached: bool
    cost_usd: float

    # Output
    verdict: Verdict
    confidence: float
    findings: List[Dict] = field(default_factory=list)

    # Ground Truth (when available)
    ground_truth: Optional[Verdict] = None
    is_correct: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "function_id": self.function_id,
            "contract_name": self.contract_name,
            "source_tokens": self.source_tokens,
            "triage_level": self.triage_level.value,
            "triage_reason": self.triage_reason,
            "context_tokens": self.context_tokens,
            "compression_ratio": self.compression_ratio,
            "context_tier": self.context_tier,
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_ms": self.latency_ms,
            "cached": self.cached,
            "cost_usd": self.cost_usd,
            "verdict": self.verdict.value,
            "confidence": self.confidence,
            "findings": self.findings,
            "ground_truth": self.ground_truth.value if self.ground_truth else None,
            "is_correct": self.is_correct
        }


@dataclass
class SessionMetrics:
    """Aggregated metrics for an analysis session."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None

    # Counts
    functions_analyzed: int = 0
    level_0_skipped: int = 0
    level_1_quick: int = 0
    level_2_focused: int = 0
    level_3_deep: int = 0

    # Quality (when ground truth available)
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0

    # Efficiency
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    cache_hits: int = 0

    @property
    def precision(self) -> float:
        """Calculate precision: TP / (TP + FP)."""
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        """Calculate recall: TP / (TP + FN)."""
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        """Calculate F1 score: 2 * (P * R) / (P + R)."""
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def false_positive_rate(self) -> float:
        """Calculate FP rate: FP / (FP + TN)."""
        denom = self.false_positives + self.true_negatives
        return self.false_positives / denom if denom > 0 else 0.0

    @property
    def skip_rate(self) -> float:
        """Calculate Level 0 skip rate."""
        return self.level_0_skipped / self.functions_analyzed if self.functions_analyzed > 0 else 0.0

    @property
    def cost_per_function(self) -> float:
        """Calculate average cost per function."""
        return self.total_cost_usd / self.functions_analyzed if self.functions_analyzed > 0 else 0.0

    @property
    def cost_per_true_positive(self) -> float:
        """Calculate cost per true positive found."""
        return self.total_cost_usd / self.true_positives if self.true_positives > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency per function."""
        return self.total_latency_ms / self.functions_analyzed if self.functions_analyzed > 0 else 0.0

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        return self.cache_hits / self.functions_analyzed if self.functions_analyzed > 0 else 0.0

    @property
    def avg_tokens_per_function(self) -> float:
        """Calculate average tokens per function."""
        return self.total_tokens / self.functions_analyzed if self.functions_analyzed > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "functions_analyzed": self.functions_analyzed,
            "level_0_skipped": self.level_0_skipped,
            "level_1_quick": self.level_1_quick,
            "level_2_focused": self.level_2_focused,
            "level_3_deep": self.level_3_deep,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "false_positive_rate": self.false_positive_rate,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "total_latency_ms": self.total_latency_ms,
            "cache_hits": self.cache_hits,
            "skip_rate": self.skip_rate,
            "cost_per_function": self.cost_per_function,
            "cost_per_true_positive": self.cost_per_true_positive,
            "avg_latency_ms": self.avg_latency_ms,
            "cache_hit_rate": self.cache_hit_rate,
            "avg_tokens_per_function": self.avg_tokens_per_function,
        }


class TelemetryCollector:
    """Collects and persists telemetry data."""

    def __init__(self, storage_path: str = "metrics/telemetry.jsonl"):
        """
        Initialize telemetry collector.

        Args:
            storage_path: Path to store telemetry data
        """
        self.storage_path = storage_path
        self.current_session: Optional[SessionMetrics] = None
        self.events: List[AnalysisEvent] = []

        # Ensure storage directory exists
        Path(storage_path).parent.mkdir(parents=True, exist_ok=True)

    def start_session(self) -> str:
        """
        Start a new analysis session.

        Returns:
            Session ID
        """
        import uuid
        session_id = str(uuid.uuid4())
        self.current_session = SessionMetrics(
            session_id=session_id,
            start_time=datetime.now()
        )
        return session_id

    def record_event(self, event: AnalysisEvent):
        """
        Record a single analysis event.

        Args:
            event: AnalysisEvent to record
        """
        self.events.append(event)
        self._update_session(event)
        self._persist_event(event)

    def end_session(self) -> Optional[SessionMetrics]:
        """
        End current session and return metrics.

        Returns:
            SessionMetrics if session exists, None otherwise
        """
        if self.current_session:
            self.current_session.end_time = datetime.now()
            self._persist_session(self.current_session)
        return self.current_session

    def get_session_metrics(self) -> Optional[SessionMetrics]:
        """
        Get current session metrics without ending session.

        Returns:
            SessionMetrics if session exists, None otherwise
        """
        return self.current_session

    def _update_session(self, event: AnalysisEvent):
        """
        Update session aggregates from event.

        Args:
            event: AnalysisEvent to aggregate
        """
        s = self.current_session
        if not s:
            return

        s.functions_analyzed += 1
        s.total_tokens += event.prompt_tokens + event.completion_tokens
        s.total_cost_usd += event.cost_usd
        s.total_latency_ms += event.latency_ms

        if event.cached:
            s.cache_hits += 1

        # Update level counts
        level_map = {
            TriageLevel.SKIP: "level_0_skipped",
            TriageLevel.QUICK: "level_1_quick",
            TriageLevel.FOCUSED: "level_2_focused",
            TriageLevel.DEEP: "level_3_deep",
        }
        attr = level_map.get(event.triage_level)
        if attr:
            setattr(s, attr, getattr(s, attr) + 1)

        # Update quality metrics if ground truth available
        if event.ground_truth is not None:
            predicted_vuln = event.verdict == Verdict.VULNERABLE
            actual_vuln = event.ground_truth == Verdict.VULNERABLE

            if predicted_vuln and actual_vuln:
                s.true_positives += 1
                event.is_correct = True
            elif predicted_vuln and not actual_vuln:
                s.false_positives += 1
                event.is_correct = False
            elif not predicted_vuln and actual_vuln:
                s.false_negatives += 1
                event.is_correct = False
            else:
                s.true_negatives += 1
                event.is_correct = True

    def _persist_event(self, event: AnalysisEvent):
        """
        Persist event to storage.

        Args:
            event: AnalysisEvent to persist
        """
        try:
            with open(self.storage_path, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception as e:
            # Don't fail analysis on telemetry error
            print(f"Warning: Failed to persist event: {e}")

    def _persist_session(self, session: SessionMetrics):
        """
        Persist session summary.

        Args:
            session: SessionMetrics to persist
        """
        session_path = self.storage_path.replace(".jsonl", "_sessions.jsonl")
        try:
            with open(session_path, "a") as f:
                f.write(json.dumps(session.to_dict()) + "\n")
        except Exception as e:
            # Don't fail analysis on telemetry error
            print(f"Warning: Failed to persist session: {e}")

    def load_events(self, session_id: Optional[str] = None) -> List[AnalysisEvent]:
        """
        Load events from storage.

        Args:
            session_id: Optional session ID to filter by

        Returns:
            List of AnalysisEvent
        """
        events = []
        if not os.path.exists(self.storage_path):
            return events

        with open(self.storage_path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if session_id and data.get("session_id") != session_id:
                        continue

                    # Reconstruct event
                    event = AnalysisEvent(
                        event_id=data["event_id"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        session_id=data["session_id"],
                        function_id=data["function_id"],
                        contract_name=data["contract_name"],
                        source_tokens=data["source_tokens"],
                        triage_level=TriageLevel(data["triage_level"]),
                        triage_reason=data["triage_reason"],
                        context_tokens=data["context_tokens"],
                        compression_ratio=data["compression_ratio"],
                        context_tier=data["context_tier"],
                        provider=data["provider"],
                        model=data["model"],
                        prompt_tokens=data["prompt_tokens"],
                        completion_tokens=data["completion_tokens"],
                        latency_ms=data["latency_ms"],
                        cached=data["cached"],
                        cost_usd=data["cost_usd"],
                        verdict=Verdict(data["verdict"]),
                        confidence=data["confidence"],
                        findings=data.get("findings", []),
                        ground_truth=Verdict(data["ground_truth"]) if data.get("ground_truth") else None,
                        is_correct=data.get("is_correct")
                    )
                    events.append(event)
                except Exception as e:
                    print(f"Warning: Failed to load event: {e}")

        return events


# Global collector instance
_collector: Optional[TelemetryCollector] = None


def get_collector(storage_path: str = "metrics/telemetry.jsonl") -> TelemetryCollector:
    """
    Get global telemetry collector instance.

    Args:
        storage_path: Path to store telemetry data

    Returns:
        TelemetryCollector instance
    """
    global _collector
    if _collector is None:
        _collector = TelemetryCollector(storage_path)
    return _collector
