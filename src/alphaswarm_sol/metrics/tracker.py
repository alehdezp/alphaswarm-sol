"""High-level metrics tracker combining recording and calculation.

Task 8.2b: Unified interface for metrics.

Usage:
    tracker = MetricsTracker()

    # Record events during scan
    tracker.record_detection(
        contract_id="test.sol",
        pattern_id="vm-001",
        function_name="withdraw",
        line_number=42,
        expected=True,
        detected=True,
    )

    # Calculate metrics
    snapshot = tracker.calculate_metrics()
    print(snapshot.metrics[MetricName.DETECTION_RATE].value)
"""

from __future__ import annotations

from pathlib import Path

from .calculator import MetricCalculator
from .event_store import EventStore
from .recorder import MetricsRecorder
from .storage import HistoryStore
from .types import MetricName, MetricSnapshot


class MetricsTracker:
    """Unified interface for recording and calculating metrics.

    This class provides a single point of access for both recording
    metric events and calculating metric values.
    """

    def __init__(self, storage_path: Path | str | None = None):
        """Initialize tracker.

        Args:
            storage_path: Override default storage path
        """
        if storage_path is None:
            from ..config import METRICS_CONFIG

            storage_path = Path(METRICS_CONFIG.get("storage_path", ".vrs/metrics"))

        self.storage_path = Path(storage_path)

        # Create event store
        self.store = EventStore(self.storage_path / "events")

        # Create recorder with same store
        self.recorder = MetricsRecorder(self.storage_path)

        # Create calculator with same store
        self.calculator = MetricCalculator(self.store)

        # Create history store
        self.history = HistoryStore(self.storage_path / "history")

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
            contract_id: Contract identifier
            pattern_id: Pattern ID (e.g., "vm-001")
            function_name: Function where detection occurred
            line_number: Line number in source
            expected: Whether this was expected (from MANIFEST)
            detected: Whether VKG detected it

        Returns:
            Event ID
        """
        return self.recorder.detection(
            contract_id=contract_id,
            pattern_id=pattern_id,
            function_name=function_name,
            line_number=line_number,
            expected=expected,
            detected=detected,
        )

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
        return self.recorder.timing(
            operation=operation,
            contract_id=contract_id,
            duration_seconds=duration_seconds,
        )

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
            compiled: Whether scaffold compiled
            error_message: Error if compilation failed

        Returns:
            Event ID
        """
        return self.recorder.scaffold(
            finding_id=finding_id,
            pattern_id=pattern_id,
            compiled=compiled,
            error_message=error_message,
        )

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
            auto_resolved: Whether resolved without human escalation
            tokens_used: Number of tokens used

        Returns:
            Event ID
        """
        return self.recorder.verdict(
            finding_id=finding_id,
            pattern_id=pattern_id,
            verdict=verdict,
            auto_resolved=auto_resolved,
            tokens_used=tokens_used,
        )

    def calculate_metrics(
        self,
        days: int = 7,
        completed_phases: set[str] | None = None,
    ) -> MetricSnapshot:
        """Calculate all metrics from recent events.

        Args:
            days: Number of days of events to include
            completed_phases: Set of completed phase names

        Returns:
            MetricSnapshot with all calculated metrics
        """
        return self.calculator.calculate_all(
            days=days,
            completed_phases=completed_phases,
        )

    def get_event_count(self, days: int = 1) -> int:
        """Get total number of events in the last N days.

        Args:
            days: Number of days to look back

        Returns:
            Event count
        """
        return self.store.count_events(days=days)

    def clear_events(self) -> None:
        """Clear all recorded events (for testing)."""
        self.store.clear()

    # History methods

    def save_snapshot(self, snapshot: MetricSnapshot | None = None) -> Path:
        """Save a metric snapshot to history.

        Args:
            snapshot: Snapshot to save. If None, calculates current metrics.

        Returns:
            Path to saved file
        """
        if snapshot is None:
            snapshot = self.calculate_metrics()
        return self.history.save(snapshot)

    def get_latest_snapshot(self) -> MetricSnapshot | None:
        """Get the most recent saved snapshot.

        Returns:
            Most recent MetricSnapshot or None if no history
        """
        return self.history.get_latest()

    def get_history(
        self,
        days: int = 30,
        limit: int | None = None,
    ) -> list[MetricSnapshot]:
        """Get snapshots from the last N days.

        Args:
            days: Number of days to look back
            limit: Maximum number of snapshots

        Returns:
            List of MetricSnapshots, oldest first
        """
        return self.history.get_history(days=days, limit=limit)

    def get_metric_trend(
        self,
        metric_name: MetricName,
        days: int = 30,
    ) -> list[tuple]:
        """Get trend data for a specific metric.

        Args:
            metric_name: The metric to track
            days: Number of days to look back

        Returns:
            List of (timestamp, value) tuples
        """
        return self.history.get_metric_trend(metric_name, days)

    def get_metric_statistics(
        self,
        metric_name: MetricName,
        days: int = 30,
    ) -> dict[str, float] | None:
        """Get statistics for a metric over time.

        Args:
            metric_name: The metric to analyze
            days: Number of days to analyze

        Returns:
            Dict with min, max, avg, latest values or None
        """
        return self.history.get_statistics(metric_name, days)

    def cleanup_history(self, retention_days: int = 90) -> int:
        """Remove old snapshots from history.

        Args:
            retention_days: Keep snapshots from last N days

        Returns:
            Number of snapshots removed
        """
        return self.history.cleanup(retention_days)
