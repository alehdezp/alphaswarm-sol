"""Metric calculation engine.

Task 8.2b: Calculate AlphaSwarm metrics from recorded events.

The calculator takes raw events from the EventStore and computes
the 8 key metrics defined in definitions.py.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .definitions import METRIC_DEFINITIONS, get_available_metrics
from .event_store import EventStore
from .events import EventType
from .types import MetricName, MetricSnapshot, MetricStatus, MetricValue


class MetricCalculator:
    """Calculates AlphaSwarm metrics from recorded events."""

    def __init__(self, event_store: EventStore):
        """Initialize calculator.

        Args:
            event_store: EventStore to read events from
        """
        self.store = event_store

    def calculate_all(
        self,
        days: int = 7,
        completed_phases: set[str] | None = None,
    ) -> MetricSnapshot:
        """Calculate all available metrics from recent events.

        Args:
            days: Number of days of events to include
            completed_phases: Set of completed phase names for dependency checking

        Returns:
            MetricSnapshot with all calculated metrics
        """
        available = get_available_metrics(completed_phases)
        metrics: dict[MetricName, MetricValue] = {}

        for name in available:
            try:
                value = self._calculate_metric(name, days)
                if value is not None:
                    metrics[name] = value
            except Exception:
                # Skip metrics that fail to calculate
                pass

        return MetricSnapshot(
            timestamp=datetime.now(),
            version=self._get_version(),
            metrics=metrics,
        )

    def calculate_single(
        self,
        name: MetricName,
        days: int = 7,
    ) -> MetricValue | None:
        """Calculate a single metric.

        Args:
            name: Metric name
            days: Number of days of events to include

        Returns:
            MetricValue or None if calculation fails
        """
        return self._calculate_metric(name, days)

    def _calculate_metric(
        self,
        name: MetricName,
        days: int,
    ) -> MetricValue | None:
        """Calculate a single metric by name."""
        defn = METRIC_DEFINITIONS[name]

        if name == MetricName.DETECTION_RATE:
            return self._calc_detection_rate(defn, days)
        elif name == MetricName.FALSE_POSITIVE_RATE:
            return self._calc_fp_rate(defn, days)
        elif name == MetricName.PATTERN_PRECISION:
            return self._calc_pattern_precision(defn, days)
        elif name == MetricName.TIME_TO_DETECTION:
            return self._calc_time_to_detection(defn, days)
        elif name == MetricName.SCAFFOLD_COMPILE_RATE:
            return self._calc_scaffold_compile_rate(defn, days)
        elif name == MetricName.LLM_AUTONOMY:
            return self._calc_llm_autonomy(defn, days)
        elif name == MetricName.TOKEN_EFFICIENCY:
            return self._calc_token_efficiency(defn, days)
        elif name == MetricName.ESCALATION_RATE:
            return self._calc_escalation_rate(defn, days)
        else:
            return None

    def _calc_detection_rate(self, defn: Any, days: int) -> MetricValue:
        """Calculate detection rate: detected / expected.

        This measures how many known vulnerabilities VKG successfully detects.
        """
        events = self.store.get_events(EventType.DETECTION, days=days)

        if not events:
            return self._make_unknown(defn)

        # Count expected vulnerabilities that were detected
        expected_events = [e for e in events if e.get("expected", False)]
        if not expected_events:
            return self._make_unknown(defn)

        detected_count = sum(1 for e in expected_events if e.get("detected", False))
        rate = detected_count / len(expected_events)

        return self._make_value(defn, rate)

    def _calc_fp_rate(self, defn: Any, days: int) -> MetricValue:
        """Calculate false positive rate: FP / (FP + TP).

        TP: expected AND detected
        FP: NOT expected AND detected
        """
        events = self.store.get_events(EventType.DETECTION, days=days)

        if not events:
            return self._make_unknown(defn)

        # TP: expected AND detected
        tp = sum(1 for e in events if e.get("expected", False) and e.get("detected", False))
        # FP: NOT expected AND detected
        fp = sum(1 for e in events if not e.get("expected", False) and e.get("detected", False))

        if tp + fp == 0:
            return self._make_unknown(defn)

        rate = fp / (fp + tp)
        return self._make_value(defn, rate)

    def _calc_pattern_precision(self, defn: Any, days: int) -> MetricValue:
        """Calculate average precision per pattern.

        Groups events by pattern_id, calculates precision for each,
        then returns the average.
        """
        events = self.store.get_events(EventType.DETECTION, days=days)

        if not events:
            return self._make_unknown(defn)

        # Group by pattern
        by_pattern: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for e in events:
            pattern_id = e.get("pattern_id", "unknown")
            by_pattern[pattern_id].append(e)

        # Calculate precision per pattern
        precisions: list[float] = []
        for pattern_id, pattern_events in by_pattern.items():
            tp = sum(1 for e in pattern_events if e.get("expected", False) and e.get("detected", False))
            fp = sum(1 for e in pattern_events if not e.get("expected", False) and e.get("detected", False))

            if tp + fp > 0:
                precisions.append(tp / (tp + fp))

        if not precisions:
            return self._make_unknown(defn)

        avg_precision = sum(precisions) / len(precisions)
        return self._make_value(defn, avg_precision)

    def _calc_time_to_detection(self, defn: Any, days: int) -> MetricValue:
        """Calculate average scan time."""
        events = self.store.get_events(EventType.TIMING, days=days)

        # Filter to scan operations
        scan_events = [e for e in events if e.get("operation") == "scan"]

        if not scan_events:
            return self._make_unknown(defn)

        avg_time = sum(e.get("duration_seconds", 0) for e in scan_events) / len(scan_events)
        return self._make_value(defn, avg_time)

    def _calc_scaffold_compile_rate(self, defn: Any, days: int) -> MetricValue:
        """Calculate scaffold compilation rate."""
        events = self.store.get_events(EventType.SCAFFOLD, days=days)

        if not events:
            return self._make_unknown(defn)

        compiled = sum(1 for e in events if e.get("compiled", False))
        rate = compiled / len(events)
        return self._make_value(defn, rate)

    def _calc_llm_autonomy(self, defn: Any, days: int) -> MetricValue:
        """Calculate LLM autonomy rate."""
        events = self.store.get_events(EventType.VERDICT, days=days)

        if not events:
            return self._make_unknown(defn)

        auto_resolved = sum(1 for e in events if e.get("auto_resolved", False))
        rate = auto_resolved / len(events)
        return self._make_value(defn, rate)

    def _calc_token_efficiency(self, defn: Any, days: int) -> MetricValue:
        """Calculate average tokens per resolution."""
        events = self.store.get_events(EventType.VERDICT, days=days)

        if not events:
            return self._make_unknown(defn)

        avg_tokens = sum(e.get("tokens_used", 0) for e in events) / len(events)
        return self._make_value(defn, avg_tokens)

    def _calc_escalation_rate(self, defn: Any, days: int) -> MetricValue:
        """Calculate human escalation rate."""
        events = self.store.get_events(EventType.VERDICT, days=days)

        if not events:
            return self._make_unknown(defn)

        escalated = sum(1 for e in events if not e.get("auto_resolved", True))
        rate = escalated / len(events)
        return self._make_value(defn, rate)

    def _make_value(self, defn: Any, value: float) -> MetricValue:
        """Create MetricValue from definition and calculated value."""
        mv = MetricValue(
            name=defn.name,
            value=value,
            target=defn.target,
            threshold_warning=defn.threshold_warning,
            threshold_critical=defn.threshold_critical,
            unit=defn.unit,
            timestamp=datetime.now(),
        )
        mv.status = mv.evaluate_status()
        return mv

    def _make_unknown(self, defn: Any) -> MetricValue:
        """Create unknown MetricValue when no data available."""
        return MetricValue(
            name=defn.name,
            value=0.0,
            target=defn.target,
            threshold_warning=defn.threshold_warning,
            threshold_critical=defn.threshold_critical,
            unit=defn.unit,
            status=MetricStatus.UNKNOWN,
            timestamp=datetime.now(),
        )

    def _get_version(self) -> str:
        """Get VKG version."""
        try:
            from alphaswarm_sol import __version__

            return __version__
        except (ImportError, AttributeError):
            return "unknown"


def create_calculator(storage_path: Path | str | None = None) -> MetricCalculator:
    """Factory function to create calculator with default storage.

    Args:
        storage_path: Override default storage path

    Returns:
        MetricCalculator instance
    """
    from ..config import METRICS_CONFIG

    if storage_path is None:
        storage_path = Path(METRICS_CONFIG.get("storage_path", ".vrs/metrics"))

    store = EventStore(Path(storage_path) / "events")
    return MetricCalculator(store)
