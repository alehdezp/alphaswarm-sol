"""Task 14.7: Calibration Validation.

Measures calibration quality using standard metrics:
- Brier Score: Mean squared error between predictions and outcomes
- Expected Calibration Error (ECE): Average calibration gap across bins
- Maximum Calibration Error (MCE): Worst bin calibration

Philosophy:
- Numbers without validation are meaningless
- Track metrics over time to ensure calibration doesn't drift
- Compare before/after to prove improvement
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from alphaswarm_sol.calibration.dataset import CalibrationDataset, Label, LabeledFinding


@dataclass
class CalibrationMetrics:
    """Comprehensive calibration metrics."""

    # Core metrics
    brier_score: float  # Lower is better (0-1)
    expected_calibration_error: float  # ECE - lower is better
    max_calibration_error: float  # MCE - worst bin error

    # Discrimination metrics
    auroc: Optional[float] = None  # Area under ROC
    auprc: Optional[float] = None  # Area under PR curve

    # Sample info
    n_samples: int = 0
    n_true_positives: int = 0
    n_false_positives: int = 0

    # Per-bin breakdown
    bin_metrics: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "brier_score": round(self.brier_score, 4),
            "expected_calibration_error": round(self.expected_calibration_error, 4),
            "max_calibration_error": round(self.max_calibration_error, 4),
            "auroc": round(self.auroc, 4) if self.auroc is not None else None,
            "auprc": round(self.auprc, 4) if self.auprc is not None else None,
            "n_samples": self.n_samples,
            "n_true_positives": self.n_true_positives,
            "n_false_positives": self.n_false_positives,
            "bin_metrics": self.bin_metrics,
        }

    def is_well_calibrated(self, ece_threshold: float = 0.10) -> bool:
        """Check if calibration meets quality threshold."""
        return self.expected_calibration_error <= ece_threshold

    def summary(self) -> str:
        """Generate human-readable summary."""
        status = "GOOD" if self.is_well_calibrated() else "NEEDS IMPROVEMENT"
        lines = [
            f"Calibration Validation Results ({status})",
            "=" * 50,
            f"Samples: {self.n_samples} (TP: {self.n_true_positives}, FP: {self.n_false_positives})",
            "",
            "Core Metrics:",
            f"  Brier Score:     {self.brier_score:.4f} (lower is better, 0 = perfect)",
            f"  ECE:             {self.expected_calibration_error:.4f} (< 0.10 = well calibrated)",
            f"  Max Cal Error:   {self.max_calibration_error:.4f}",
        ]

        if self.auroc is not None:
            lines.append(f"  AUROC:           {self.auroc:.4f}")
        if self.auprc is not None:
            lines.append(f"  AUPRC:           {self.auprc:.4f}")

        if self.bin_metrics:
            lines.append("")
            lines.append("Per-Bin Breakdown:")
            for bm in self.bin_metrics:
                if bm["count"] > 0:
                    lines.append(
                        f"  [{bm['bin_lower']:.1f}-{bm['bin_upper']:.1f}]: "
                        f"n={bm['count']}, pred={bm['avg_predicted']:.2f}, "
                        f"actual={bm['avg_actual']:.2f}, error={bm['error']:.3f}"
                    )

        return "\n".join(lines)


class CalibrationValidator:
    """Validate calibration quality with comprehensive metrics.

    Example:
        validator = CalibrationValidator()

        # Add predictions and outcomes
        for finding in findings:
            actual = 1 if finding.is_true_positive else 0
            validator.add_prediction(finding.confidence, actual)

        # Get metrics
        metrics = validator.compute_metrics()
        print(f"ECE: {metrics.expected_calibration_error:.4f}")
        print(f"Well calibrated: {metrics.is_well_calibrated()}")

        # Validate from dataset
        metrics = validator.validate_from_dataset(dataset)
    """

    def __init__(self, n_bins: int = 10):
        """Initialize validator.

        Args:
            n_bins: Number of bins for ECE calculation
        """
        self.n_bins = n_bins
        self._predictions: List[float] = []
        self._actuals: List[int] = []

    def add_prediction(self, predicted: float, actual: int) -> None:
        """Add a prediction-outcome pair.

        Args:
            predicted: Predicted probability (confidence)
            actual: Actual outcome (1 for TP, 0 for FP)
        """
        self._predictions.append(predicted)
        self._actuals.append(actual)

    def add_predictions(
        self,
        predictions: List[float],
        actuals: List[int],
    ) -> None:
        """Add multiple prediction-outcome pairs."""
        self._predictions.extend(predictions)
        self._actuals.extend(actuals)

    def clear(self) -> None:
        """Clear all data."""
        self._predictions = []
        self._actuals = []

    def compute_metrics(self) -> CalibrationMetrics:
        """Compute all calibration metrics.

        Returns:
            CalibrationMetrics with comprehensive results
        """
        if len(self._predictions) == 0:
            return CalibrationMetrics(
                brier_score=0.0,
                expected_calibration_error=0.0,
                max_calibration_error=0.0,
                n_samples=0,
            )

        predicted = np.array(self._predictions)
        actual = np.array(self._actuals)

        # Brier score
        brier = brier_score(predicted, actual)

        # ECE and MCE with bin breakdown
        ece, mce, bin_metrics = self._compute_calibration_error(predicted, actual)

        # Sample counts
        n_tp = int(np.sum(actual == 1))
        n_fp = int(np.sum(actual == 0))

        # Optional: AUROC and AUPRC if sklearn available
        auroc = None
        auprc = None
        try:
            from sklearn.metrics import roc_auc_score, average_precision_score
            if n_tp > 0 and n_fp > 0:  # Need both classes
                auroc = roc_auc_score(actual, predicted)
                auprc = average_precision_score(actual, predicted)
        except ImportError:
            pass

        return CalibrationMetrics(
            brier_score=brier,
            expected_calibration_error=ece,
            max_calibration_error=mce,
            auroc=auroc,
            auprc=auprc,
            n_samples=len(predicted),
            n_true_positives=n_tp,
            n_false_positives=n_fp,
            bin_metrics=bin_metrics,
        )

    def _compute_calibration_error(
        self,
        predicted: np.ndarray,
        actual: np.ndarray,
    ) -> Tuple[float, float, List[Dict[str, Any]]]:
        """Compute ECE, MCE, and per-bin metrics."""
        bin_boundaries = np.linspace(0, 1, self.n_bins + 1)
        bin_metrics = []

        weighted_error_sum = 0.0
        max_error = 0.0
        total_count = 0

        for i in range(self.n_bins):
            bin_lower = bin_boundaries[i]
            bin_upper = bin_boundaries[i + 1]

            # Find points in this bin
            if i == self.n_bins - 1:
                in_bin = (predicted >= bin_lower) & (predicted <= bin_upper)
            else:
                in_bin = (predicted >= bin_lower) & (predicted < bin_upper)

            count = np.sum(in_bin)

            if count > 0:
                avg_predicted = np.mean(predicted[in_bin])
                avg_actual = np.mean(actual[in_bin])
                error = abs(avg_predicted - avg_actual)

                weighted_error_sum += error * count
                max_error = max(max_error, error)
                total_count += count
            else:
                avg_predicted = (bin_lower + bin_upper) / 2
                avg_actual = 0.0
                error = 0.0

            bin_metrics.append({
                "bin_lower": bin_lower,
                "bin_upper": bin_upper,
                "count": int(count),
                "avg_predicted": float(avg_predicted),
                "avg_actual": float(avg_actual),
                "error": float(error),
            })

        ece = weighted_error_sum / total_count if total_count > 0 else 0.0

        return ece, max_error, bin_metrics

    def validate_from_dataset(
        self,
        dataset: CalibrationDataset,
        pattern_id: Optional[str] = None,
    ) -> CalibrationMetrics:
        """Validate calibration from a labeled dataset.

        Args:
            dataset: CalibrationDataset with labeled findings
            pattern_id: Optional pattern to filter by

        Returns:
            CalibrationMetrics for the dataset
        """
        self.clear()

        if pattern_id:
            findings = dataset.get_findings_for_pattern(pattern_id)
        else:
            findings = [
                f for p in dataset.get_all_patterns()
                for f in dataset.get_findings_for_pattern(p)
            ]

        for finding in findings:
            if finding.label in {Label.TRUE_POSITIVE, Label.FALSE_POSITIVE}:
                actual = 1 if finding.label == Label.TRUE_POSITIVE else 0
                self.add_prediction(finding.raw_confidence, actual)

        return self.compute_metrics()

    def compare_calibrations(
        self,
        before_predictions: List[float],
        after_predictions: List[float],
        actuals: List[int],
    ) -> Dict[str, Any]:
        """Compare before/after calibration.

        Args:
            before_predictions: Pre-calibration predictions
            after_predictions: Post-calibration predictions
            actuals: Actual outcomes

        Returns:
            Comparison results
        """
        # Before metrics
        self.clear()
        self.add_predictions(before_predictions, actuals)
        before_metrics = self.compute_metrics()

        # After metrics
        self.clear()
        self.add_predictions(after_predictions, actuals)
        after_metrics = self.compute_metrics()

        # Compute improvements
        brier_improvement = before_metrics.brier_score - after_metrics.brier_score
        ece_improvement = before_metrics.expected_calibration_error - after_metrics.expected_calibration_error

        return {
            "before": before_metrics.to_dict(),
            "after": after_metrics.to_dict(),
            "improvements": {
                "brier_score": round(brier_improvement, 4),
                "ece": round(ece_improvement, 4),
                "brier_improvement_pct": round(brier_improvement / before_metrics.brier_score * 100, 1) if before_metrics.brier_score > 0 else 0,
                "ece_improvement_pct": round(ece_improvement / before_metrics.expected_calibration_error * 100, 1) if before_metrics.expected_calibration_error > 0 else 0,
            },
            "is_improved": ece_improvement > 0,
        }


def brier_score(predicted: np.ndarray | List[float], actual: np.ndarray | List[int]) -> float:
    """Calculate Brier score (mean squared error).

    Args:
        predicted: Predicted probabilities
        actual: Actual outcomes (0 or 1)

    Returns:
        Brier score (lower is better, 0 = perfect)
    """
    predicted = np.array(predicted)
    actual = np.array(actual)

    if len(predicted) == 0:
        return 0.0

    return float(np.mean((predicted - actual) ** 2))


def expected_calibration_error(
    predicted: np.ndarray | List[float],
    actual: np.ndarray | List[int],
    n_bins: int = 10,
) -> float:
    """Calculate Expected Calibration Error.

    ECE measures how well confidence scores match actual accuracy.
    Lower is better, 0 = perfectly calibrated.

    Args:
        predicted: Predicted probabilities
        actual: Actual outcomes
        n_bins: Number of calibration bins

    Returns:
        ECE value
    """
    predicted = np.array(predicted)
    actual = np.array(actual)

    if len(predicted) == 0:
        return 0.0

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    weighted_error_sum = 0.0
    total_count = 0

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]

        if i == n_bins - 1:
            in_bin = (predicted >= bin_lower) & (predicted <= bin_upper)
        else:
            in_bin = (predicted >= bin_lower) & (predicted < bin_upper)

        count = np.sum(in_bin)
        if count > 0:
            avg_predicted = np.mean(predicted[in_bin])
            avg_actual = np.mean(actual[in_bin])
            error = abs(avg_predicted - avg_actual)
            weighted_error_sum += error * count
            total_count += count

    return weighted_error_sum / total_count if total_count > 0 else 0.0


def validate_calibration(
    predictions: List[float],
    actuals: List[int],
    n_bins: int = 10,
) -> CalibrationMetrics:
    """Convenience function to validate calibration.

    Args:
        predictions: List of predicted probabilities
        actuals: List of actual outcomes
        n_bins: Number of bins

    Returns:
        CalibrationMetrics
    """
    validator = CalibrationValidator(n_bins=n_bins)
    validator.add_predictions(predictions, actuals)
    return validator.compute_metrics()


def validate_pattern_calibration(
    dataset: CalibrationDataset,
    pattern_id: str,
    n_bins: int = 10,
) -> CalibrationMetrics:
    """Validate calibration for a specific pattern.

    Args:
        dataset: CalibrationDataset
        pattern_id: Pattern to validate
        n_bins: Number of bins

    Returns:
        CalibrationMetrics for the pattern
    """
    validator = CalibrationValidator(n_bins=n_bins)
    return validator.validate_from_dataset(dataset, pattern_id)


def generate_validation_report(
    dataset: CalibrationDataset,
    output_path: Optional[str] = None,
) -> str:
    """Generate comprehensive validation report for all patterns.

    Args:
        dataset: CalibrationDataset to validate
        output_path: Optional path to save report

    Returns:
        Report as string
    """
    lines = [
        "Calibration Validation Report",
        "=" * 60,
        "",
    ]

    # Overall metrics
    validator = CalibrationValidator()
    overall_metrics = validator.validate_from_dataset(dataset)
    lines.append("Overall Metrics:")
    lines.append(f"  Total samples: {overall_metrics.n_samples}")
    lines.append(f"  Brier Score: {overall_metrics.brier_score:.4f}")
    lines.append(f"  ECE: {overall_metrics.expected_calibration_error:.4f}")
    lines.append(f"  MCE: {overall_metrics.max_calibration_error:.4f}")
    lines.append("")

    # Per-pattern metrics
    lines.append("Per-Pattern Metrics:")
    lines.append("-" * 60)

    patterns = sorted(dataset.get_all_patterns())
    well_calibrated = 0
    needs_improvement = 0

    for pattern_id in patterns:
        metrics = validate_pattern_calibration(dataset, pattern_id)
        if metrics.n_samples < 5:
            continue  # Skip patterns with insufficient data

        status = "OK" if metrics.is_well_calibrated() else "NEEDS WORK"
        if metrics.is_well_calibrated():
            well_calibrated += 1
        else:
            needs_improvement += 1

        lines.append(
            f"  {pattern_id}: ECE={metrics.expected_calibration_error:.3f}, "
            f"Brier={metrics.brier_score:.3f}, n={metrics.n_samples} [{status}]"
        )

    lines.append("")
    lines.append(f"Summary: {well_calibrated} well-calibrated, {needs_improvement} need improvement")

    report = "\n".join(lines)

    if output_path:
        from pathlib import Path
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(report)

    return report
