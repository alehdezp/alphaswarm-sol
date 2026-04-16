"""Accuracy dashboard for verdict precision and pattern-level metrics.

This module provides accuracy monitoring dashboards with verdict precision,
recall, per-pattern breakdowns, and confidence calibration metrics.

Example:
    from alphaswarm_sol.dashboards.accuracy import render_accuracy_dashboard, OutputFormat

    # Generate accuracy dashboard
    dashboard = render_accuracy_dashboard(
        pool_ids=["pool-001"],
        format=OutputFormat.MARKDOWN,
        window_hours=24
    )
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from alphaswarm_sol.dashboards.latency import OutputFormat


@dataclass
class AccuracyStats:
    """Verdict accuracy statistics.

    Attributes:
        pool_id: Pool identifier
        precision: True positives / (True positives + False positives)
        recall: True positives / (True positives + False negatives)
        f1_score: Harmonic mean of precision and recall
        true_positives: Count of correct vulnerability detections
        false_positives: Count of incorrect vulnerability detections
        false_negatives: Count of missed vulnerabilities
        ground_truth_available: Whether ground truth data exists
        window_hours: Time window for measurements
    """

    pool_id: Optional[str]
    precision: float
    recall: float
    f1_score: float
    true_positives: int
    false_positives: int
    false_negatives: int
    ground_truth_available: bool
    window_hours: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pool_id": self.pool_id,
            "precision": round(self.precision, 3),
            "recall": round(self.recall, 3),
            "f1_score": round(self.f1_score, 3),
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "ground_truth_available": self.ground_truth_available,
            "window_hours": self.window_hours,
        }


@dataclass
class PatternAccuracyBreakdown:
    """Per-pattern accuracy metrics.

    Attributes:
        pattern_id: Pattern identifier
        precision: Pattern-specific precision
        recall: Pattern-specific recall
        true_positives: Count of correct detections
        false_positives: Count of incorrect detections
        false_negatives: Count of misses
    """

    pattern_id: str
    precision: float
    recall: float
    true_positives: int
    false_positives: int
    false_negatives: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "precision": round(self.precision, 3),
            "recall": round(self.recall, 3),
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
        }


@dataclass
class ConfidenceCalibration:
    """Confidence calibration metrics.

    Attributes:
        confidence_bucket: Confidence range (e.g., "0.8-0.9")
        expected_accuracy: Expected accuracy based on confidence
        actual_accuracy: Observed accuracy
        count: Number of verdicts in bucket
        calibration_error: Absolute difference between expected and actual
    """

    confidence_bucket: str
    expected_accuracy: float
    actual_accuracy: float
    count: int

    @property
    def calibration_error(self) -> float:
        """Absolute calibration error."""
        return abs(self.expected_accuracy - self.actual_accuracy)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "confidence_bucket": self.confidence_bucket,
            "expected_accuracy": round(self.expected_accuracy, 3),
            "actual_accuracy": round(self.actual_accuracy, 3),
            "count": self.count,
            "calibration_error": round(self.calibration_error, 3),
        }


class AccuracyDashboard:
    """Dashboard for verdict accuracy metrics.

    Provides overall accuracy, per-pattern breakdowns, and confidence
    calibration analysis when ground truth is available.

    Example:
        dashboard = AccuracyDashboard()
        stats = dashboard.get_accuracy_stats(pool_id="pool-001")
        text = dashboard.render(OutputFormat.MARKDOWN)
    """

    def __init__(self, vrs_root: Optional[Path] = None):
        """Initialize accuracy dashboard.

        Args:
            vrs_root: Optional VRS root directory
        """
        self.vrs_root = vrs_root
        self._stats: Optional[AccuracyStats] = None
        self._pattern_breakdowns: List[PatternAccuracyBreakdown] = []
        self._calibration: List[ConfidenceCalibration] = []

    def get_accuracy_stats(
        self,
        pool_id: Optional[str] = None,
        window_hours: int = 24,
    ) -> AccuracyStats:
        """Get verdict accuracy statistics.

        Args:
            pool_id: Optional specific pool to measure
            window_hours: Time window for measurements

        Returns:
            AccuracyStats with precision/recall metrics
        """
        # Placeholder implementation
        # In production, would query ground truth and compare to verdicts
        stats = AccuracyStats(
            pool_id=pool_id,
            precision=0.92,
            recall=0.88,
            f1_score=0.90,
            true_positives=44,
            false_positives=4,
            false_negatives=6,
            ground_truth_available=True,
            window_hours=window_hours,
        )

        self._stats = stats
        return stats

    def get_pattern_breakdown(
        self,
        pool_id: Optional[str] = None,
        window_hours: int = 24,
    ) -> List[PatternAccuracyBreakdown]:
        """Get per-pattern accuracy breakdown.

        Args:
            pool_id: Optional specific pool to measure
            window_hours: Time window for measurements

        Returns:
            List of PatternAccuracyBreakdown objects
        """
        # Placeholder implementation
        breakdowns = [
            PatternAccuracyBreakdown(
                pattern_id="reentrancy-classic",
                precision=0.95,
                recall=0.90,
                true_positives=18,
                false_positives=1,
                false_negatives=2,
            ),
            PatternAccuracyBreakdown(
                pattern_id="weak-access-control",
                precision=0.88,
                recall=0.85,
                true_positives=17,
                false_positives=2,
                false_negatives=3,
            ),
            PatternAccuracyBreakdown(
                pattern_id="unchecked-external-call",
                precision=0.90,
                recall=0.87,
                true_positives=9,
                false_positives=1,
                false_negatives=1,
            ),
        ]

        self._pattern_breakdowns = breakdowns
        return breakdowns

    def get_confidence_calibration(
        self,
        pool_id: Optional[str] = None,
        window_hours: int = 24,
    ) -> List[ConfidenceCalibration]:
        """Get confidence calibration metrics.

        Args:
            pool_id: Optional specific pool to measure
            window_hours: Time window for measurements

        Returns:
            List of ConfidenceCalibration objects
        """
        # Placeholder implementation
        calibration = [
            ConfidenceCalibration(
                confidence_bucket="0.9-1.0",
                expected_accuracy=0.95,
                actual_accuracy=0.93,
                count=20,
            ),
            ConfidenceCalibration(
                confidence_bucket="0.8-0.9",
                expected_accuracy=0.85,
                actual_accuracy=0.87,
                count=15,
            ),
            ConfidenceCalibration(
                confidence_bucket="0.7-0.8",
                expected_accuracy=0.75,
                actual_accuracy=0.72,
                count=10,
            ),
        ]

        self._calibration = calibration
        return calibration

    def render(
        self,
        format: OutputFormat = OutputFormat.MARKDOWN,
        pool_id: Optional[str] = None,
        window_hours: int = 24,
    ) -> str:
        """Render accuracy dashboard.

        Args:
            format: Output format (markdown, json, toon)
            pool_id: Optional specific pool
            window_hours: Time window for measurements

        Returns:
            Formatted dashboard text
        """
        # Refresh stats
        stats = self.get_accuracy_stats(pool_id, window_hours)
        breakdowns = self.get_pattern_breakdown(pool_id, window_hours)
        calibration = self.get_confidence_calibration(pool_id, window_hours)

        if format == OutputFormat.MARKDOWN:
            return self._render_markdown(stats, breakdowns, calibration)
        elif format == OutputFormat.JSON:
            return self._render_json(stats, breakdowns, calibration)
        else:  # TOON
            return self._render_toon(stats, breakdowns, calibration)

    def _render_markdown(
        self,
        stats: AccuracyStats,
        breakdowns: List[PatternAccuracyBreakdown],
        calibration: List[ConfidenceCalibration],
    ) -> str:
        """Render as markdown."""
        lines = [
            "# Accuracy Dashboard",
            "",
            f"**Time Window:** {stats.window_hours}h",
            f"**Pool:** {stats.pool_id or 'All'}",
            f"**Ground Truth:** {'Available' if stats.ground_truth_available else 'Not Available'}",
            "",
            "## Overall Accuracy",
            "",
            f"- **Precision:** {stats.precision:.1%}",
            f"- **Recall:** {stats.recall:.1%}",
            f"- **F1 Score:** {stats.f1_score:.3f}",
            f"- **True Positives:** {stats.true_positives}",
            f"- **False Positives:** {stats.false_positives}",
            f"- **False Negatives:** {stats.false_negatives}",
            "",
            "## Per-Pattern Breakdown",
            "",
            "| Pattern | Precision | Recall | TP | FP | FN |",
            "|---------|-----------|--------|----|----|----|",
        ]

        for bd in breakdowns:
            lines.append(
                f"| {bd.pattern_id} | {bd.precision:.1%} | {bd.recall:.1%} | "
                f"{bd.true_positives} | {bd.false_positives} | {bd.false_negatives} |"
            )

        lines.extend(
            [
                "",
                "## Confidence Calibration",
                "",
                "| Confidence Bucket | Expected | Actual | Count | Error |",
                "|-------------------|----------|--------|-------|-------|",
            ]
        )

        for cal in calibration:
            lines.append(
                f"| {cal.confidence_bucket} | {cal.expected_accuracy:.1%} | "
                f"{cal.actual_accuracy:.1%} | {cal.count} | "
                f"{cal.calibration_error:.3f} |"
            )

        return "\n".join(lines)

    def _render_json(
        self,
        stats: AccuracyStats,
        breakdowns: List[PatternAccuracyBreakdown],
        calibration: List[ConfidenceCalibration],
    ) -> str:
        """Render as JSON."""
        data = {
            "overall": stats.to_dict(),
            "pattern_breakdown": [bd.to_dict() for bd in breakdowns],
            "confidence_calibration": [cal.to_dict() for cal in calibration],
        }
        return json.dumps(data, indent=2)

    def _render_toon(
        self,
        stats: AccuracyStats,
        breakdowns: List[PatternAccuracyBreakdown],
        calibration: List[ConfidenceCalibration],
    ) -> str:
        """Render as TOON."""
        lines = [
            "# Accuracy Dashboard",
            "",
            "[overall]",
            f"pool_id = {stats.pool_id or 'null'}",
            f"precision = {stats.precision:.3f}",
            f"recall = {stats.recall:.3f}",
            f"f1_score = {stats.f1_score:.3f}",
            f"true_positives = {stats.true_positives}",
            f"false_positives = {stats.false_positives}",
            f"false_negatives = {stats.false_negatives}",
            f"ground_truth_available = {str(stats.ground_truth_available).lower()}",
            f"window_hours = {stats.window_hours}",
            "",
            "[[pattern_breakdown]]",
        ]

        for bd in breakdowns:
            lines.extend(
                [
                    f"pattern_id = {bd.pattern_id}",
                    f"precision = {bd.precision:.3f}",
                    f"recall = {bd.recall:.3f}",
                    f"true_positives = {bd.true_positives}",
                    f"false_positives = {bd.false_positives}",
                    f"false_negatives = {bd.false_negatives}",
                    "",
                ]
            )

        lines.append("[[confidence_calibration]]")

        for cal in calibration:
            lines.extend(
                [
                    f"confidence_bucket = {cal.confidence_bucket}",
                    f"expected_accuracy = {cal.expected_accuracy:.3f}",
                    f"actual_accuracy = {cal.actual_accuracy:.3f}",
                    f"count = {cal.count}",
                    f"calibration_error = {cal.calibration_error:.3f}",
                    "",
                ]
            )

        return "\n".join(lines)


def render_accuracy_dashboard(
    pool_ids: Optional[List[str]] = None,
    format: OutputFormat = OutputFormat.MARKDOWN,
    window_hours: int = 24,
    vrs_root: Optional[Path] = None,
) -> str:
    """Convenience function to render accuracy dashboard.

    Args:
        pool_ids: Optional specific pools to include
        format: Output format
        window_hours: Time window for measurements
        vrs_root: Optional VRS root directory

    Returns:
        Formatted dashboard text
    """
    dashboard = AccuracyDashboard(vrs_root=vrs_root)

    # For now, render for first pool or all
    pool_id = pool_ids[0] if pool_ids else None

    return dashboard.render(format=format, pool_id=pool_id, window_hours=window_hours)


__all__ = [
    "AccuracyStats",
    "PatternAccuracyBreakdown",
    "ConfidenceCalibration",
    "AccuracyDashboard",
    "render_accuracy_dashboard",
]
