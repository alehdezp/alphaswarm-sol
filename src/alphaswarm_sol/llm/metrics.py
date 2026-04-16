"""
Metrics Analysis and Drift Detection

Analyzes telemetry data to compute trends, detect drift, and generate insights.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from .telemetry import TelemetryCollector, SessionMetrics, AnalysisEvent


@dataclass
class DriftAlert:
    """Alert for detected metric drift."""
    metric: str
    baseline: float
    current: float
    drift_pct: float
    severity: str  # "warning" or "critical"
    timestamp: datetime
    message: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "metric": self.metric,
            "baseline": self.baseline,
            "current": self.current,
            "drift_pct": self.drift_pct,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
        }


@dataclass
class MetricsTrend:
    """Trend analysis for a metric over time."""
    metric: str
    values: List[float]
    timestamps: List[datetime]
    mean: float
    median: float
    std_dev: float
    min_val: float
    max_val: float
    trend_direction: str  # "improving", "degrading", "stable"
    trend_strength: float  # 0.0 to 1.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "metric": self.metric,
            "count": len(self.values),
            "mean": self.mean,
            "median": self.median,
            "std_dev": self.std_dev,
            "min": self.min_val,
            "max": self.max_val,
            "trend_direction": self.trend_direction,
            "trend_strength": self.trend_strength,
        }


class MetricsAnalyzer:
    """Analyzes telemetry data to generate insights."""

    def __init__(self, collector: TelemetryCollector):
        """
        Initialize analyzer.

        Args:
            collector: TelemetryCollector instance
        """
        self.collector = collector

    def analyze_session(self, session: SessionMetrics) -> Dict[str, any]:
        """
        Analyze a single session's metrics.

        Args:
            session: SessionMetrics to analyze

        Returns:
            Dict with analysis results
        """
        analysis = {
            "session_id": session.session_id,
            "duration_seconds": (
                (session.end_time - session.start_time).total_seconds()
                if session.end_time else 0
            ),
            "throughput_functions_per_second": (
                session.functions_analyzed / ((session.end_time - session.start_time).total_seconds())
                if session.end_time and (session.end_time - session.start_time).total_seconds() > 0
                else 0
            ),
            "quality": {
                "precision": session.precision,
                "recall": session.recall,
                "f1": session.f1,
                "fp_rate": session.false_positive_rate,
            },
            "efficiency": {
                "skip_rate": session.skip_rate,
                "cost_per_function": session.cost_per_function,
                "cost_per_true_positive": session.cost_per_true_positive,
                "avg_latency_ms": session.avg_latency_ms,
                "cache_hit_rate": session.cache_hit_rate,
                "avg_tokens_per_function": session.avg_tokens_per_function,
            },
            "distribution": {
                "level_0_pct": session.level_0_skipped / session.functions_analyzed * 100 if session.functions_analyzed > 0 else 0,
                "level_1_pct": session.level_1_quick / session.functions_analyzed * 100 if session.functions_analyzed > 0 else 0,
                "level_2_pct": session.level_2_focused / session.functions_analyzed * 100 if session.functions_analyzed > 0 else 0,
                "level_3_pct": session.level_3_deep / session.functions_analyzed * 100 if session.functions_analyzed > 0 else 0,
            }
        }

        return analysis

    def compute_trend(
        self,
        metric_name: str,
        window_days: int = 7
    ) -> Optional[MetricsTrend]:
        """
        Compute trend for a metric over time window.

        Args:
            metric_name: Name of metric to trend
            window_days: Number of days to analyze

        Returns:
            MetricsTrend if data available, None otherwise
        """
        # Load all events in window
        cutoff = datetime.now() - timedelta(days=window_days)
        events = self.collector.load_events()
        events = [e for e in events if e.timestamp >= cutoff]

        if not events:
            return None

        # Extract metric values
        values: List[float] = []
        timestamps: List[datetime] = []

        for event in events:
            # Extract metric based on name
            val = self._extract_metric(event, metric_name)
            if val is not None:
                values.append(val)
                timestamps.append(event.timestamp)

        if not values:
            return None

        # Compute statistics
        mean_val = statistics.mean(values)
        median_val = statistics.median(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
        min_val = min(values)
        max_val = max(values)

        # Compute trend direction (simple linear regression approximation)
        direction, strength = self._compute_trend_direction(values)

        return MetricsTrend(
            metric=metric_name,
            values=values,
            timestamps=timestamps,
            mean=mean_val,
            median=median_val,
            std_dev=std_dev,
            min_val=min_val,
            max_val=max_val,
            trend_direction=direction,
            trend_strength=strength,
        )

    def _extract_metric(self, event: AnalysisEvent, metric_name: str) -> Optional[float]:
        """Extract metric value from event."""
        metric_map = {
            "confidence": event.confidence,
            "latency_ms": float(event.latency_ms),
            "cost_usd": event.cost_usd,
            "compression_ratio": event.compression_ratio,
            "context_tokens": float(event.context_tokens),
            "total_tokens": float(event.prompt_tokens + event.completion_tokens),
        }
        return metric_map.get(metric_name)

    def _compute_trend_direction(self, values: List[float]) -> Tuple[str, float]:
        """
        Compute trend direction using simple slope analysis.

        Returns:
            Tuple of (direction, strength)
        """
        if len(values) < 2:
            return "stable", 0.0

        # Simple linear approximation: compare first half to second half
        n = len(values)
        first_half = values[:n//2]
        second_half = values[n//2:]

        first_mean = statistics.mean(first_half)
        second_mean = statistics.mean(second_half)

        if first_mean == 0:
            return "stable", 0.0

        change_pct = (second_mean - first_mean) / abs(first_mean)

        # Determine direction and strength
        if abs(change_pct) < 0.05:
            return "stable", abs(change_pct)
        elif change_pct > 0:
            return "increasing", abs(change_pct)
        else:
            return "decreasing", abs(change_pct)


class DriftDetector:
    """Detects drift in quality and efficiency metrics."""

    # Thresholds for drift detection
    THRESHOLDS = {
        "precision": {"warning": 0.05, "critical": 0.10},
        "recall": {"warning": 0.05, "critical": 0.10},
        "f1": {"warning": 0.05, "critical": 0.10},
        "cost_per_function": {"warning": 0.20, "critical": 0.50},
        "avg_latency_ms": {"warning": 0.30, "critical": 0.50},
        "fp_rate": {"warning": 0.02, "critical": 0.05},
        "skip_rate": {"warning": 0.10, "critical": 0.20},
    }

    def __init__(self, baseline: Dict[str, float]):
        """
        Initialize drift detector.

        Args:
            baseline: Baseline metrics to compare against
        """
        self.baseline = baseline
        self.alerts: List[DriftAlert] = []

    def check(self, current: Dict[str, float]) -> List[DriftAlert]:
        """
        Check current metrics against baseline.

        Args:
            current: Current metrics

        Returns:
            List of DriftAlert
        """
        alerts = []

        for metric, thresholds in self.THRESHOLDS.items():
            if metric not in current or metric not in self.baseline:
                continue

            base_val = self.baseline[metric]
            curr_val = current[metric]

            if base_val == 0:
                continue

            # Calculate drift percentage
            drift = abs(curr_val - base_val) / abs(base_val)

            # Check thresholds
            if drift >= thresholds["critical"]:
                msg = f"{metric} drifted {drift*100:.1f}% from baseline (critical)"
                alerts.append(DriftAlert(
                    metric=metric,
                    baseline=base_val,
                    current=curr_val,
                    drift_pct=drift,
                    severity="critical",
                    timestamp=datetime.now(),
                    message=msg
                ))
            elif drift >= thresholds["warning"]:
                msg = f"{metric} drifted {drift*100:.1f}% from baseline (warning)"
                alerts.append(DriftAlert(
                    metric=metric,
                    baseline=base_val,
                    current=curr_val,
                    drift_pct=drift,
                    severity="warning",
                    timestamp=datetime.now(),
                    message=msg
                ))

        self.alerts.extend(alerts)
        return alerts

    def set_baseline(self, metrics: Dict[str, float]):
        """
        Update baseline metrics.

        Args:
            metrics: New baseline values
        """
        self.baseline = metrics

    def get_alerts(self, severity: Optional[str] = None) -> List[DriftAlert]:
        """
        Get all alerts, optionally filtered by severity.

        Args:
            severity: Optional severity filter ("warning" or "critical")

        Returns:
            List of DriftAlert
        """
        if severity:
            return [a for a in self.alerts if a.severity == severity]
        return self.alerts


class FeedbackLoop:
    """Continuous feedback loop for metric-driven improvement."""

    def __init__(
        self,
        collector: TelemetryCollector,
        baseline: Dict[str, float]
    ):
        """
        Initialize feedback loop.

        Args:
            collector: TelemetryCollector instance
            baseline: Baseline metrics
        """
        self.collector = collector
        self.analyzer = MetricsAnalyzer(collector)
        self.drift_detector = DriftDetector(baseline)
        self.improvement_history: List[Dict] = []

    def run_cycle(self) -> Dict[str, any]:
        """
        Run one feedback cycle.

        Returns:
            Dict with cycle results including alerts and recommendations
        """
        # Get current session metrics
        session = self.collector.get_session_metrics()
        if not session:
            return {"error": "No active session"}

        # Analyze session
        analysis = self.analyzer.analyze_session(session)

        # Check for drift
        current_metrics = {
            "precision": session.precision,
            "recall": session.recall,
            "f1": session.f1,
            "cost_per_function": session.cost_per_function,
            "avg_latency_ms": session.avg_latency_ms,
            "fp_rate": session.false_positive_rate,
            "skip_rate": session.skip_rate,
        }
        alerts = self.drift_detector.check(current_metrics)

        # Generate recommendations
        recommendations = self._generate_recommendations(analysis, alerts)

        return {
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis,
            "alerts": [a.to_dict() for a in alerts],
            "recommendations": recommendations,
        }

    def _generate_recommendations(
        self,
        analysis: Dict,
        alerts: List[DriftAlert]
    ) -> List[str]:
        """
        Generate actionable recommendations based on analysis.

        Args:
            analysis: Session analysis
            alerts: Drift alerts

        Returns:
            List of recommendation strings
        """
        recs = []

        # Quality recommendations
        quality = analysis["quality"]
        if quality["precision"] < 0.85:
            recs.append("QUALITY: Precision below target (85%). Review false positive patterns.")
        if quality["recall"] < 0.80:
            recs.append("QUALITY: Recall below target (80%). Review false negative patterns.")
        if quality["fp_rate"] > 0.05:
            recs.append("QUALITY: FP rate above target (5%). Tighten triage rules.")

        # Efficiency recommendations
        efficiency = analysis["efficiency"]
        if efficiency["skip_rate"] < 0.40:
            recs.append("EFFICIENCY: Skip rate below target (40%). Review Level 0 triage rules.")
        if efficiency["cache_hit_rate"] < 0.70:
            recs.append("EFFICIENCY: Cache hit rate below target (70%). Increase cache duration.")
        if efficiency["cost_per_function"] > 0.001:  # $0.001
            recs.append("EFFICIENCY: Cost per function high. Review token budgets and compression.")

        # Drift-based recommendations
        for alert in alerts:
            if alert.severity == "critical":
                recs.append(f"CRITICAL DRIFT: {alert.message}. Investigate immediately.")

        return recs

    def apply_tuning(self, adjustments: Dict[str, any]):
        """
        Apply tuning adjustments based on feedback.

        Args:
            adjustments: Dict of parameter adjustments
        """
        # Record tuning action
        self.improvement_history.append({
            "timestamp": datetime.now().isoformat(),
            "adjustments": adjustments,
        })

        # Note: Actual parameter updates would happen in respective components
        # This is a placeholder for the feedback loop integration
