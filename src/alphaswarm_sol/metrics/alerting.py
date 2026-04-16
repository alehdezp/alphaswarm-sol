"""Alerting system for metric degradation.

Task 8.4: Monitor metrics and generate alerts when values cross thresholds
or regress from baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .types import MetricName, MetricStatus, MetricSnapshot, MetricValue, LOWER_IS_BETTER_METRICS


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts."""

    THRESHOLD_BREACH = "threshold_breach"  # Value crossed threshold
    DEGRADATION = "degradation"  # Value worse than baseline
    RECOVERY = "recovery"  # Value improved from previous alert state
    MISSING_DATA = "missing_data"  # Metric not available


@dataclass
class Alert:
    """A single alert about a metric."""

    metric_name: MetricName
    level: AlertLevel
    alert_type: AlertType
    message: str
    current_value: float
    threshold_value: float
    timestamp: datetime = field(default_factory=datetime.now)
    previous_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "metric_name": self.metric_name.value,
            "level": self.level.value,
            "alert_type": self.alert_type.value,
            "message": self.message,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "timestamp": self.timestamp.isoformat(),
            "previous_value": self.previous_value,
        }

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"[{self.level.value.upper()}] {self.message}"


class AlertChecker:
    """Checks metrics and generates alerts."""

    def __init__(
        self,
        regression_threshold: float = 0.05,
    ):
        """Initialize checker.

        Args:
            regression_threshold: Percent change to consider regression (default 5%)
        """
        self.regression_threshold = regression_threshold

    def check_snapshot(
        self,
        snapshot: MetricSnapshot,
        baseline: MetricSnapshot | None = None,
    ) -> list[Alert]:
        """Check a snapshot for alertable conditions.

        Args:
            snapshot: Current metric snapshot to check
            baseline: Optional baseline to compare against for regressions

        Returns:
            List of generated alerts
        """
        alerts: list[Alert] = []

        for name, metric in snapshot.metrics.items():
            # Evaluate status from the value (don't rely on stored status)
            status = metric.evaluate_status()

            # Skip if status is UNKNOWN (means it was explicitly set as unknown)
            # Check both evaluated status and if it was explicitly marked unknown
            if metric.status == MetricStatus.UNKNOWN:
                continue

            # Check threshold breaches
            if status == MetricStatus.WARNING:
                alerts.append(self._threshold_alert(
                    metric, AlertLevel.WARNING
                ))
            elif status == MetricStatus.CRITICAL:
                alerts.append(self._threshold_alert(
                    metric, AlertLevel.CRITICAL
                ))

            # Check for regression from baseline
            if baseline and name in baseline.metrics:
                baseline_metric = baseline.metrics[name]
                # Skip if baseline was explicitly marked unknown
                if baseline_metric.status != MetricStatus.UNKNOWN:
                    if self._is_regression(metric, baseline_metric):
                        alerts.append(self._regression_alert(
                            metric, baseline_metric
                        ))

        return alerts

    def check_metric(
        self,
        metric: MetricValue,
        baseline_value: float | None = None,
    ) -> list[Alert]:
        """Check a single metric for alerts.

        Args:
            metric: MetricValue to check
            baseline_value: Optional baseline value for regression detection

        Returns:
            List of generated alerts
        """
        alerts: list[Alert] = []

        # Skip unknown status
        if metric.status == MetricStatus.UNKNOWN:
            return alerts

        # Check threshold
        status = metric.evaluate_status()
        if status == MetricStatus.WARNING:
            alerts.append(self._threshold_alert(metric, AlertLevel.WARNING))
        elif status == MetricStatus.CRITICAL:
            alerts.append(self._threshold_alert(metric, AlertLevel.CRITICAL))

        # Check regression
        if baseline_value is not None:
            baseline_metric = MetricValue(
                name=metric.name,
                value=baseline_value,
                target=metric.target,
                threshold_warning=metric.threshold_warning,
                threshold_critical=metric.threshold_critical,
            )
            if self._is_regression(metric, baseline_metric):
                alerts.append(self._regression_alert(metric, baseline_metric))

        return alerts

    def has_critical(self, alerts: list[Alert]) -> bool:
        """Check if any alerts are critical."""
        return any(a.level == AlertLevel.CRITICAL for a in alerts)

    def has_warning(self, alerts: list[Alert]) -> bool:
        """Check if any alerts are warning or higher."""
        return any(a.level in (AlertLevel.WARNING, AlertLevel.CRITICAL) for a in alerts)

    def get_critical_alerts(self, alerts: list[Alert]) -> list[Alert]:
        """Filter to only critical alerts."""
        return [a for a in alerts if a.level == AlertLevel.CRITICAL]

    def get_warning_alerts(self, alerts: list[Alert]) -> list[Alert]:
        """Filter to warning alerts."""
        return [a for a in alerts if a.level == AlertLevel.WARNING]

    def get_regressions(self, alerts: list[Alert]) -> list[Alert]:
        """Filter to regression alerts."""
        return [a for a in alerts if a.alert_type == AlertType.DEGRADATION]

    def _threshold_alert(
        self,
        metric: MetricValue,
        level: AlertLevel,
    ) -> Alert:
        """Create alert for threshold breach."""
        if metric.name in LOWER_IS_BETTER_METRICS:
            threshold = (
                metric.threshold_warning
                if level == AlertLevel.WARNING
                else metric.threshold_critical
            )
            message = (
                f"{metric.name.value} is {self._format_value(metric.value, metric.name)} "
                f"(exceeds {level.value} threshold: {self._format_value(threshold, metric.name)})"
            )
        else:
            threshold = (
                metric.threshold_warning
                if level == AlertLevel.WARNING
                else metric.threshold_critical
            )
            message = (
                f"{metric.name.value} is {self._format_value(metric.value, metric.name)} "
                f"(below {level.value} threshold: {self._format_value(threshold, metric.name)})"
            )

        return Alert(
            metric_name=metric.name,
            level=level,
            alert_type=AlertType.THRESHOLD_BREACH,
            message=message,
            current_value=metric.value,
            threshold_value=threshold,
        )

    def _regression_alert(
        self,
        current: MetricValue,
        baseline: MetricValue,
    ) -> Alert:
        """Create alert for regression from baseline."""
        if current.name in LOWER_IS_BETTER_METRICS:
            delta = current.value - baseline.value
            direction = "increased" if delta > 0 else "decreased"
        else:
            delta = baseline.value - current.value
            direction = "decreased" if delta > 0 else "increased"

        message = (
            f"{current.name.value} {direction} from "
            f"{self._format_value(baseline.value, current.name)} to "
            f"{self._format_value(current.value, current.name)}"
        )

        # Determine severity based on how bad the regression is
        level = AlertLevel.WARNING
        if current.name in LOWER_IS_BETTER_METRICS:
            # If current now exceeds critical threshold, make it critical
            if current.value >= current.threshold_critical:
                level = AlertLevel.CRITICAL
        else:
            # If current now below critical threshold, make it critical
            if current.value <= current.threshold_critical:
                level = AlertLevel.CRITICAL

        return Alert(
            metric_name=current.name,
            level=level,
            alert_type=AlertType.DEGRADATION,
            message=message,
            current_value=current.value,
            threshold_value=baseline.value,
            previous_value=baseline.value,
        )

    def _is_regression(
        self,
        current: MetricValue,
        baseline: MetricValue,
    ) -> bool:
        """Check if current is significantly worse than baseline."""
        # Define significant regression threshold
        threshold = self.regression_threshold

        if current.name in LOWER_IS_BETTER_METRICS:
            # Lower is better, so increase is regression
            return current.value > baseline.value * (1 + threshold)
        else:
            # Higher is better, so decrease is regression
            return current.value < baseline.value * (1 - threshold)

    def _format_value(self, value: float, name: MetricName) -> str:
        """Format value based on metric type."""
        if name in (MetricName.TOKEN_EFFICIENCY,):
            return f"{value:.0f} tokens"
        elif name in (MetricName.TIME_TO_DETECTION,):
            return f"{value:.1f}s"
        else:
            return f"{value:.1%}"


def check_alerts(
    snapshot: MetricSnapshot,
    baseline: MetricSnapshot | None = None,
    regression_threshold: float = 0.05,
) -> list[Alert]:
    """Convenience function to check a snapshot for alerts.

    Args:
        snapshot: Current metric snapshot
        baseline: Optional baseline for regression detection
        regression_threshold: Percent change to consider regression

    Returns:
        List of alerts
    """
    checker = AlertChecker(regression_threshold=regression_threshold)
    return checker.check_snapshot(snapshot, baseline)
