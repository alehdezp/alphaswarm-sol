"""Core metric types and definitions.

Task 8.0: Base types for the metrics module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MetricName(Enum):
    """The 8 key VKG metrics."""

    DETECTION_RATE = "detection_rate"
    FALSE_POSITIVE_RATE = "false_positive_rate"
    PATTERN_PRECISION = "pattern_precision"
    SCAFFOLD_COMPILE_RATE = "scaffold_compile_rate"
    LLM_AUTONOMY = "llm_autonomy"
    TIME_TO_DETECTION = "time_to_detection"
    TOKEN_EFFICIENCY = "token_efficiency"
    ESCALATION_RATE = "escalation_rate"


class MetricStatus(Enum):
    """Metric health status."""

    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


# Metrics where lower values are better
LOWER_IS_BETTER_METRICS = frozenset({
    MetricName.FALSE_POSITIVE_RATE,
    MetricName.ESCALATION_RATE,
    MetricName.TIME_TO_DETECTION,
    MetricName.TOKEN_EFFICIENCY,
})


@dataclass
class MetricValue:
    """A single metric measurement."""

    name: MetricName
    value: float
    target: float
    threshold_warning: float
    threshold_critical: float
    status: MetricStatus = MetricStatus.UNKNOWN
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def evaluate_status(self) -> MetricStatus:
        """Determine status based on value vs thresholds.

        For metrics where LOWER is better (FP rate, escalation rate, time, tokens):
            - value <= target: OK
            - value <= warning threshold: WARNING
            - value > warning threshold: CRITICAL

        For metrics where HIGHER is better (detection rate, precision, autonomy):
            - value >= target: OK
            - value >= warning threshold: WARNING
            - value < warning threshold: CRITICAL
        """
        if self.name in LOWER_IS_BETTER_METRICS:
            # Lower is better
            if self.value <= self.target:
                return MetricStatus.OK
            elif self.value <= self.threshold_warning:
                return MetricStatus.WARNING
            else:
                return MetricStatus.CRITICAL
        else:
            # Higher is better
            if self.value >= self.target:
                return MetricStatus.OK
            elif self.value >= self.threshold_warning:
                return MetricStatus.WARNING
            else:
                return MetricStatus.CRITICAL

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name.value,
            "value": self.value,
            "target": self.target,
            "threshold_warning": self.threshold_warning,
            "threshold_critical": self.threshold_critical,
            "status": self.status.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MetricValue:
        """Deserialize from dictionary."""
        return cls(
            name=MetricName(data["name"]),
            value=data["value"],
            target=data["target"],
            threshold_warning=data["threshold_warning"],
            threshold_critical=data["threshold_critical"],
            status=MetricStatus(data.get("status", "unknown")),
            unit=data.get("unit", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
        )


@dataclass
class MetricSnapshot:
    """Point-in-time snapshot of all metrics."""

    timestamp: datetime
    version: str  # VKG version
    metrics: dict[MetricName, MetricValue]
    run_id: str = ""  # Optional identifier for this run

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "run_id": self.run_id,
            "metrics": {
                name.value: val.to_dict()
                for name, val in self.metrics.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MetricSnapshot:
        """Deserialize from storage."""
        metrics = {}
        for name_str, val_data in data.get("metrics", {}).items():
            try:
                metric_name = MetricName(name_str)
                metrics[metric_name] = MetricValue.from_dict(val_data)
            except ValueError:
                # Skip unknown metrics (forwards compatibility)
                pass

        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            version=data.get("version", "unknown"),
            run_id=data.get("run_id", ""),
            metrics=metrics,
        )

    def get_status_summary(self) -> dict[MetricStatus, int]:
        """Get count of metrics by status."""
        summary: dict[MetricStatus, int] = {s: 0 for s in MetricStatus}
        for metric in self.metrics.values():
            status = metric.evaluate_status()
            summary[status] += 1
        return summary

    def has_critical(self) -> bool:
        """Check if any metric is in critical state."""
        return any(
            m.evaluate_status() == MetricStatus.CRITICAL
            for m in self.metrics.values()
        )

    def has_warning(self) -> bool:
        """Check if any metric is in warning state."""
        return any(
            m.evaluate_status() == MetricStatus.WARNING
            for m in self.metrics.values()
        )
