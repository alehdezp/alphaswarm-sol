"""Phase 21: Detection Metrics.

This module provides metrics calculation for vulnerability detection,
including precision, recall, F1 score, and confusion matrix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class ConfusionMatrix:
    """Confusion matrix for binary classification.

    Attributes:
        true_positives: Correctly detected vulnerabilities
        false_positives: Incorrectly flagged as vulnerable
        true_negatives: Correctly identified as safe
        false_negatives: Missed vulnerabilities
    """
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0

    @property
    def total(self) -> int:
        """Total samples."""
        return self.true_positives + self.false_positives + self.true_negatives + self.false_negatives

    @property
    def precision(self) -> float:
        """Calculate precision (TP / (TP + FP))."""
        denominator = self.true_positives + self.false_positives
        if denominator == 0:
            return 0.0
        return self.true_positives / denominator

    @property
    def recall(self) -> float:
        """Calculate recall (TP / (TP + FN))."""
        denominator = self.true_positives + self.false_negatives
        if denominator == 0:
            return 0.0
        return self.true_positives / denominator

    @property
    def f1_score(self) -> float:
        """Calculate F1 score (harmonic mean of precision and recall)."""
        p, r = self.precision, self.recall
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)

    @property
    def accuracy(self) -> float:
        """Calculate accuracy ((TP + TN) / total)."""
        if self.total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / self.total

    @property
    def false_positive_rate(self) -> float:
        """Calculate FPR (FP / (FP + TN))."""
        denominator = self.false_positives + self.true_negatives
        if denominator == 0:
            return 0.0
        return self.false_positives / denominator

    @property
    def false_negative_rate(self) -> float:
        """Calculate FNR (FN / (FN + TP))."""
        denominator = self.false_negatives + self.true_positives
        if denominator == 0:
            return 0.0
        return self.false_negatives / denominator

    def add_prediction(self, predicted: bool, actual: bool) -> None:
        """Add a prediction to the matrix.

        Args:
            predicted: Predicted class (True = vulnerable)
            actual: Actual class (True = vulnerable)
        """
        if predicted and actual:
            self.true_positives += 1
        elif predicted and not actual:
            self.false_positives += 1
        elif not predicted and actual:
            self.false_negatives += 1
        else:
            self.true_negatives += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "true_negatives": self.true_negatives,
            "false_negatives": self.false_negatives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "accuracy": round(self.accuracy, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "false_negative_rate": round(self.false_negative_rate, 4),
        }


@dataclass
class DetectionMetrics:
    """Comprehensive detection metrics.

    Attributes:
        overall: Overall confusion matrix
        by_category: Confusion matrix per vulnerability category
        by_severity: Confusion matrix per severity level
        detection_times_ms: Detection times in milliseconds
    """
    overall: ConfusionMatrix = field(default_factory=ConfusionMatrix)
    by_category: Dict[str, ConfusionMatrix] = field(default_factory=dict)
    by_severity: Dict[str, ConfusionMatrix] = field(default_factory=dict)
    detection_times_ms: List[float] = field(default_factory=list)

    @property
    def avg_detection_time_ms(self) -> float:
        """Average detection time."""
        if not self.detection_times_ms:
            return 0.0
        return sum(self.detection_times_ms) / len(self.detection_times_ms)

    @property
    def precision(self) -> float:
        """Overall precision."""
        return self.overall.precision

    @property
    def recall(self) -> float:
        """Overall recall."""
        return self.overall.recall

    @property
    def f1_score(self) -> float:
        """Overall F1 score."""
        return self.overall.f1_score

    def add_result(
        self,
        predicted: bool,
        actual: bool,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        detection_time_ms: Optional[float] = None,
    ) -> None:
        """Add a detection result.

        Args:
            predicted: Whether vulnerability was predicted
            actual: Whether vulnerability actually exists
            category: Vulnerability category
            severity: Vulnerability severity
            detection_time_ms: Time to detect
        """
        self.overall.add_prediction(predicted, actual)

        if category:
            if category not in self.by_category:
                self.by_category[category] = ConfusionMatrix()
            self.by_category[category].add_prediction(predicted, actual)

        if severity:
            if severity not in self.by_severity:
                self.by_severity[severity] = ConfusionMatrix()
            self.by_severity[severity].add_prediction(predicted, actual)

        if detection_time_ms is not None:
            self.detection_times_ms.append(detection_time_ms)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall": self.overall.to_dict(),
            "by_category": {k: v.to_dict() for k, v in self.by_category.items()},
            "by_severity": {k: v.to_dict() for k, v in self.by_severity.items()},
            "avg_detection_time_ms": round(self.avg_detection_time_ms, 2),
            "total_samples": self.overall.total,
        }

    def to_report(self) -> str:
        """Generate human-readable report."""
        lines = ["=== Detection Metrics Report ===", ""]

        # Overall metrics
        lines.append("Overall Metrics:")
        lines.append(f"  Precision: {self.overall.precision:.2%}")
        lines.append(f"  Recall: {self.overall.recall:.2%}")
        lines.append(f"  F1 Score: {self.overall.f1_score:.2%}")
        lines.append(f"  Accuracy: {self.overall.accuracy:.2%}")
        lines.append(f"  FP Rate: {self.overall.false_positive_rate:.2%}")
        lines.append("")

        # By category
        if self.by_category:
            lines.append("By Category:")
            for cat, matrix in sorted(self.by_category.items()):
                lines.append(f"  {cat}: P={matrix.precision:.2%} R={matrix.recall:.2%} F1={matrix.f1_score:.2%}")
            lines.append("")

        # By severity
        if self.by_severity:
            lines.append("By Severity:")
            for sev, matrix in sorted(self.by_severity.items()):
                lines.append(f"  {sev}: P={matrix.precision:.2%} R={matrix.recall:.2%}")
            lines.append("")

        # Performance
        if self.detection_times_ms:
            lines.append("Performance:")
            lines.append(f"  Avg Detection Time: {self.avg_detection_time_ms:.2f}ms")
            lines.append(f"  Total Samples: {self.overall.total}")

        return "\n".join(lines)


class MetricsCalculator:
    """Calculates metrics from detection results.

    Compares predicted findings against ground truth to calculate
    precision, recall, and other metrics.
    """

    def __init__(self):
        """Initialize calculator."""
        self._metrics = DetectionMetrics()

    def add_sample(
        self,
        predicted_vulns: List[str],
        actual_vulns: List[str],
        category: Optional[str] = None,
        severity: Optional[str] = None,
        detection_time_ms: Optional[float] = None,
    ) -> None:
        """Add a sample for evaluation.

        Args:
            predicted_vulns: List of predicted vulnerability types
            actual_vulns: List of actual vulnerability types
            category: Vulnerability category
            severity: Severity level
            detection_time_ms: Detection time
        """
        predicted_set = set(predicted_vulns)
        actual_set = set(actual_vulns)

        # Calculate for each vulnerability type
        all_types = predicted_set | actual_set
        for vuln_type in all_types:
            is_predicted = vuln_type in predicted_set
            is_actual = vuln_type in actual_set

            self._metrics.add_result(
                predicted=is_predicted,
                actual=is_actual,
                category=category or vuln_type,
                severity=severity,
                detection_time_ms=detection_time_ms,
            )

    def add_binary_result(
        self,
        predicted: bool,
        actual: bool,
        category: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> None:
        """Add a binary detection result.

        Args:
            predicted: Whether vulnerability was predicted
            actual: Whether vulnerability actually exists
            category: Vulnerability category
            severity: Severity level
        """
        self._metrics.add_result(
            predicted=predicted,
            actual=actual,
            category=category,
            severity=severity,
        )

    def get_metrics(self) -> DetectionMetrics:
        """Get calculated metrics.

        Returns:
            DetectionMetrics instance
        """
        return self._metrics

    def reset(self) -> None:
        """Reset all metrics."""
        self._metrics = DetectionMetrics()

    def meets_targets(
        self,
        precision_target: float = 0.9,
        recall_target: float = 0.8,
        fp_rate_target: float = 0.05,
    ) -> Dict[str, bool]:
        """Check if metrics meet targets.

        Args:
            precision_target: Target precision (default: 90%)
            recall_target: Target recall (default: 80%)
            fp_rate_target: Target FP rate (default: 5%)

        Returns:
            Dictionary of target status
        """
        return {
            "precision_met": self._metrics.precision >= precision_target,
            "recall_met": self._metrics.recall >= recall_target,
            "fp_rate_met": self._metrics.overall.false_positive_rate <= fp_rate_target,
            "all_met": (
                self._metrics.precision >= precision_target
                and self._metrics.recall >= recall_target
                and self._metrics.overall.false_positive_rate <= fp_rate_target
            ),
        }


def calculate_metrics(
    predictions: List[Dict[str, Any]],
    ground_truth: List[Dict[str, Any]],
) -> DetectionMetrics:
    """Calculate metrics from predictions and ground truth.

    Convenience function for quick metrics calculation.

    Args:
        predictions: List of predictions with 'id' and 'vulnerabilities' keys
        ground_truth: List of ground truth with 'id' and 'vulnerabilities' keys

    Returns:
        DetectionMetrics
    """
    calculator = MetricsCalculator()

    # Build lookup for ground truth
    truth_lookup = {item['id']: item.get('vulnerabilities', []) for item in ground_truth}

    for pred in predictions:
        sample_id = pred['id']
        pred_vulns = pred.get('vulnerabilities', [])
        actual_vulns = truth_lookup.get(sample_id, [])

        calculator.add_sample(pred_vulns, actual_vulns)

    return calculator.get_metrics()


__all__ = [
    "ConfusionMatrix",
    "DetectionMetrics",
    "MetricsCalculator",
    "calculate_metrics",
]
