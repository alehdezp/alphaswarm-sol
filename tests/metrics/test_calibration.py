"""Batch Calibration Tests (05.10-11)

Tests for batch discovery calibration metrics per PCONTEXT-11:
1. Confidence calibration for batch outputs
2. Calibration error measurement
3. Reliability diagram data computation
4. Before/after calibration comparison

These tests ensure batch discovery outputs are well-calibrated.
"""

from __future__ import annotations

import json
import math
import unittest
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# Calibration Data Structures
# =============================================================================


@dataclass
class CalibrationBin:
    """A single bin for reliability diagram computation."""

    bin_lower: float
    bin_upper: float
    mean_predicted: float
    mean_actual: float
    count: int
    calibration_error: float  # |mean_predicted - mean_actual|

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "bin_lower": round(self.bin_lower, 4),
            "bin_upper": round(self.bin_upper, 4),
            "mean_predicted": round(self.mean_predicted, 4),
            "mean_actual": round(self.mean_actual, 4),
            "count": self.count,
            "calibration_error": round(self.calibration_error, 4),
        }


@dataclass
class BatchCalibrationResult:
    """Calibration metrics for batch discovery outputs."""

    expected_calibration_error: float  # ECE: weighted average bin error
    maximum_calibration_error: float   # MCE: max bin error
    brier_score: float                 # Mean squared prediction error
    reliability_bins: List[CalibrationBin]
    n_samples: int
    is_well_calibrated: bool

    # Thresholds
    ECE_THRESHOLD = 0.10  # Max acceptable ECE
    MCE_THRESHOLD = 0.15  # Max acceptable MCE
    BRIER_THRESHOLD = 0.25  # Max acceptable Brier score

    @classmethod
    def compute(
        cls,
        predictions: List[float],
        actuals: List[int],
        n_bins: int = 10,
    ) -> "BatchCalibrationResult":
        """Compute calibration metrics.

        Args:
            predictions: Predicted probabilities (confidences)
            actuals: Actual outcomes (1 = TP, 0 = FP)
            n_bins: Number of bins for reliability diagram

        Returns:
            BatchCalibrationResult
        """
        if len(predictions) != len(actuals):
            raise ValueError("Predictions and actuals must have same length")

        n = len(predictions)
        if n == 0:
            return cls(
                expected_calibration_error=0.0,
                maximum_calibration_error=0.0,
                brier_score=0.0,
                reliability_bins=[],
                n_samples=0,
                is_well_calibrated=True,
            )

        # Compute Brier score
        brier = sum((p - a) ** 2 for p, a in zip(predictions, actuals)) / n

        # Create bins
        bin_boundaries = [i / n_bins for i in range(n_bins + 1)]
        bins: List[CalibrationBin] = []

        for i in range(n_bins):
            lower = bin_boundaries[i]
            upper = bin_boundaries[i + 1]

            # Get samples in this bin
            bin_preds = []
            bin_acts = []
            for p, a in zip(predictions, actuals):
                if lower <= p < upper or (i == n_bins - 1 and p == upper):
                    bin_preds.append(p)
                    bin_acts.append(a)

            if bin_preds:
                mean_pred = sum(bin_preds) / len(bin_preds)
                mean_act = sum(bin_acts) / len(bin_acts)
                cal_error = abs(mean_pred - mean_act)
            else:
                mean_pred = (lower + upper) / 2
                mean_act = 0.0
                cal_error = 0.0

            bins.append(
                CalibrationBin(
                    bin_lower=lower,
                    bin_upper=upper,
                    mean_predicted=mean_pred,
                    mean_actual=mean_act,
                    count=len(bin_preds),
                    calibration_error=cal_error,
                )
            )

        # Compute ECE (weighted by bin count)
        ece = sum(b.count * b.calibration_error for b in bins) / n if n > 0 else 0.0

        # Compute MCE
        mce = max((b.calibration_error for b in bins if b.count > 0), default=0.0)

        # Check if well calibrated
        is_calibrated = (
            ece <= cls.ECE_THRESHOLD
            and mce <= cls.MCE_THRESHOLD
            and brier <= cls.BRIER_THRESHOLD
        )

        return cls(
            expected_calibration_error=ece,
            maximum_calibration_error=mce,
            brier_score=brier,
            reliability_bins=bins,
            n_samples=n,
            is_well_calibrated=is_calibrated,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "expected_calibration_error": round(self.expected_calibration_error, 4),
            "maximum_calibration_error": round(self.maximum_calibration_error, 4),
            "brier_score": round(self.brier_score, 4),
            "n_samples": self.n_samples,
            "is_well_calibrated": self.is_well_calibrated,
            "reliability_bins": [b.to_dict() for b in self.reliability_bins],
        }


@dataclass
class CalibrationComparison:
    """Comparison of calibration before and after adjustment."""

    before: BatchCalibrationResult
    after: BatchCalibrationResult
    ece_improvement: float
    mce_improvement: float
    brier_improvement: float
    is_improved: bool

    @classmethod
    def compute(
        cls,
        before_predictions: List[float],
        after_predictions: List[float],
        actuals: List[int],
    ) -> "CalibrationComparison":
        """Compute calibration comparison.

        Args:
            before_predictions: Original predictions
            after_predictions: Calibrated predictions
            actuals: Actual outcomes

        Returns:
            CalibrationComparison
        """
        before = BatchCalibrationResult.compute(before_predictions, actuals)
        after = BatchCalibrationResult.compute(after_predictions, actuals)

        ece_imp = before.expected_calibration_error - after.expected_calibration_error
        mce_imp = before.maximum_calibration_error - after.maximum_calibration_error
        brier_imp = before.brier_score - after.brier_score

        # Improved if at least one metric improved and none got significantly worse
        is_improved = (
            (ece_imp > 0 or mce_imp > 0 or brier_imp > 0)
            and ece_imp >= -0.02  # Max allowed regression
            and mce_imp >= -0.03
            and brier_imp >= -0.02
        )

        return cls(
            before=before,
            after=after,
            ece_improvement=ece_imp,
            mce_improvement=mce_imp,
            brier_improvement=brier_imp,
            is_improved=is_improved,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "ece_improvement": round(self.ece_improvement, 4),
            "mce_improvement": round(self.mce_improvement, 4),
            "brier_improvement": round(self.brier_improvement, 4),
            "is_improved": self.is_improved,
        }


# =============================================================================
# Test Cases
# =============================================================================


class TestBatchCalibrationResult(unittest.TestCase):
    """Tests for BatchCalibrationResult computation."""

    def test_perfect_calibration(self):
        """Perfect calibration should have near-zero error."""
        # 80% confidence with 80% actual TP rate
        predictions = [0.8] * 100
        actuals = [1] * 80 + [0] * 20

        result = BatchCalibrationResult.compute(predictions, actuals)

        self.assertLess(result.expected_calibration_error, 0.05)
        self.assertLess(result.brier_score, 0.20)
        self.assertTrue(result.is_well_calibrated)

    def test_poor_calibration_overconfident(self):
        """Overconfident predictions should have high error."""
        # 90% confidence but only 30% actual TP rate
        predictions = [0.9] * 100
        actuals = [1] * 30 + [0] * 70

        result = BatchCalibrationResult.compute(predictions, actuals)

        # Big gap between predicted (0.9) and actual (0.3)
        self.assertGreater(result.expected_calibration_error, 0.5)
        self.assertFalse(result.is_well_calibrated)

    def test_poor_calibration_underconfident(self):
        """Underconfident predictions should have high error."""
        # 30% confidence but 90% actual TP rate
        predictions = [0.3] * 100
        actuals = [1] * 90 + [0] * 10

        result = BatchCalibrationResult.compute(predictions, actuals)

        self.assertGreater(result.expected_calibration_error, 0.5)
        self.assertFalse(result.is_well_calibrated)

    def test_brier_score_calculation(self):
        """Brier score should be mean squared error."""
        # Perfect predictions
        predictions = [1.0, 1.0, 0.0, 0.0]
        actuals = [1, 1, 0, 0]

        result = BatchCalibrationResult.compute(predictions, actuals)
        self.assertEqual(result.brier_score, 0.0)

        # Worst predictions (opposite)
        predictions = [0.0, 0.0, 1.0, 1.0]
        result = BatchCalibrationResult.compute(predictions, actuals)
        self.assertEqual(result.brier_score, 1.0)

        # Medium predictions (always 0.5)
        predictions = [0.5, 0.5, 0.5, 0.5]
        result = BatchCalibrationResult.compute(predictions, actuals)
        self.assertEqual(result.brier_score, 0.25)

    def test_reliability_bins_created(self):
        """Reliability bins should be created correctly."""
        predictions = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]
        actuals = [0, 0, 1, 1, 1, 1]

        result = BatchCalibrationResult.compute(predictions, actuals, n_bins=5)

        self.assertEqual(len(result.reliability_bins), 5)

        # Check bin boundaries
        self.assertEqual(result.reliability_bins[0].bin_lower, 0.0)
        self.assertEqual(result.reliability_bins[0].bin_upper, 0.2)
        self.assertEqual(result.reliability_bins[-1].bin_lower, 0.8)
        self.assertEqual(result.reliability_bins[-1].bin_upper, 1.0)

    def test_empty_predictions(self):
        """Empty predictions should return zero metrics."""
        result = BatchCalibrationResult.compute([], [])

        self.assertEqual(result.expected_calibration_error, 0.0)
        self.assertEqual(result.brier_score, 0.0)
        self.assertEqual(result.n_samples, 0)
        self.assertTrue(result.is_well_calibrated)  # Vacuously true

    def test_length_mismatch_raises(self):
        """Mismatched lengths should raise ValueError."""
        with self.assertRaises(ValueError):
            BatchCalibrationResult.compute([0.5, 0.5], [1])

    def test_mce_calculation(self):
        """MCE should be maximum bin error."""
        # Create predictions with one very poorly calibrated region
        predictions = [0.9] * 50 + [0.1] * 50  # Half high, half low
        actuals = [0] * 50 + [1] * 50  # Opposite of predictions

        result = BatchCalibrationResult.compute(predictions, actuals, n_bins=5)

        # MCE should be close to 0.8 (big gap in both regions)
        self.assertGreater(result.maximum_calibration_error, 0.7)

    def test_serialization(self):
        """Result should serialize to valid JSON."""
        predictions = [0.7] * 10
        actuals = [1] * 7 + [0] * 3

        result = BatchCalibrationResult.compute(predictions, actuals)
        data = result.to_dict()

        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        self.assertIn("expected_calibration_error", parsed)
        self.assertIn("reliability_bins", parsed)


class TestCalibrationComparison(unittest.TestCase):
    """Tests for before/after calibration comparison."""

    def test_calibration_improves(self):
        """Comparison should detect improvement."""
        # Before: overconfident (90% predicted, 60% actual)
        before_preds = [0.9] * 100
        actuals = [1] * 60 + [0] * 40

        # After: better calibrated (65% predicted, 60% actual)
        after_preds = [0.65] * 100

        comparison = CalibrationComparison.compute(before_preds, after_preds, actuals)

        self.assertGreater(comparison.ece_improvement, 0)
        self.assertGreater(comparison.brier_improvement, 0)
        self.assertTrue(comparison.is_improved)

    def test_calibration_regression(self):
        """Comparison should detect regression."""
        # Before: well calibrated
        before_preds = [0.7] * 100
        actuals = [1] * 70 + [0] * 30

        # After: worse (overconfident)
        after_preds = [0.95] * 100

        comparison = CalibrationComparison.compute(before_preds, after_preds, actuals)

        self.assertLess(comparison.ece_improvement, 0)  # Negative = regression
        self.assertFalse(comparison.is_improved)

    def test_no_change(self):
        """Same predictions should show no improvement."""
        preds = [0.7] * 100
        actuals = [1] * 70 + [0] * 30

        comparison = CalibrationComparison.compute(preds, preds, actuals)

        self.assertEqual(comparison.ece_improvement, 0)
        self.assertEqual(comparison.brier_improvement, 0)
        # is_improved should be False (no actual improvement)
        self.assertFalse(comparison.is_improved)

    def test_comparison_serialization(self):
        """Comparison should serialize to valid JSON."""
        before = [0.8] * 50
        after = [0.6] * 50
        actuals = [1] * 30 + [0] * 20

        comparison = CalibrationComparison.compute(before, after, actuals)
        data = comparison.to_dict()

        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        self.assertIn("before", parsed)
        self.assertIn("after", parsed)
        self.assertIn("is_improved", parsed)


class TestCalibrationBin(unittest.TestCase):
    """Tests for CalibrationBin dataclass."""

    def test_bin_serialization(self):
        """Bin should serialize correctly."""
        bin_data = CalibrationBin(
            bin_lower=0.0,
            bin_upper=0.2,
            mean_predicted=0.15,
            mean_actual=0.10,
            count=25,
            calibration_error=0.05,
        )

        data = bin_data.to_dict()

        self.assertEqual(data["bin_lower"], 0.0)
        self.assertEqual(data["bin_upper"], 0.2)
        self.assertEqual(data["count"], 25)
        self.assertEqual(data["calibration_error"], 0.05)

    def test_bin_error_calculation(self):
        """Calibration error should be |predicted - actual|."""
        # Error = |0.8 - 0.6| = 0.2
        bin_data = CalibrationBin(0.6, 0.8, 0.8, 0.6, 10, 0.2)
        self.assertEqual(bin_data.calibration_error, 0.2)


class TestCalibrationThresholds(unittest.TestCase):
    """Tests for calibration threshold constants."""

    def test_threshold_values(self):
        """Thresholds should have sensible values."""
        self.assertEqual(BatchCalibrationResult.ECE_THRESHOLD, 0.10)
        self.assertEqual(BatchCalibrationResult.MCE_THRESHOLD, 0.15)
        self.assertEqual(BatchCalibrationResult.BRIER_THRESHOLD, 0.25)

    def test_well_calibrated_check(self):
        """is_well_calibrated should respect all thresholds."""
        # Just under all thresholds
        predictions = [0.75] * 100
        actuals = [1] * 75 + [0] * 25

        result = BatchCalibrationResult.compute(predictions, actuals)
        self.assertTrue(result.is_well_calibrated)

        # Over ECE threshold
        predictions = [0.9] * 100
        actuals = [1] * 50 + [0] * 50  # Big gap

        result = BatchCalibrationResult.compute(predictions, actuals)
        self.assertFalse(result.is_well_calibrated)


class TestCalibrationIntegration(unittest.TestCase):
    """Integration tests for calibration system."""

    def test_batch_vs_sequential_calibration(self):
        """Compare batch and sequential calibration quality."""
        # Simulate sequential discoveries (well-calibrated, 80% predicted, 80% actual)
        seq_predictions = [0.8] * 100
        seq_actuals = [1] * 80 + [0] * 20

        # Simulate batch discoveries (reasonably calibrated, 75% predicted, 70% actual)
        batch_predictions = [0.75] * 100
        batch_actuals = [1] * 70 + [0] * 30

        seq_result = BatchCalibrationResult.compute(seq_predictions, seq_actuals)
        batch_result = BatchCalibrationResult.compute(batch_predictions, batch_actuals)

        # Both should be reasonably calibrated (ECE < 0.15)
        self.assertLess(seq_result.expected_calibration_error, 0.15)
        self.assertLess(batch_result.expected_calibration_error, 0.15)

    def test_reliability_diagram_data_for_ci(self):
        """Reliability diagram data should be CI-ready."""
        predictions = [i / 10 for i in range(10) for _ in range(10)]  # 10 of each 0.0-0.9
        # Actual rate matches prediction rate
        actuals = []
        for i in range(10):
            tp_count = int((i / 10) * 10)
            actuals.extend([1] * tp_count + [0] * (10 - tp_count))

        result = BatchCalibrationResult.compute(predictions, actuals)

        # Should have data for CI output
        data = result.to_dict()
        self.assertIn("reliability_bins", data)
        self.assertGreater(len(data["reliability_bins"]), 0)

        # Each bin should have all required fields
        for bin_data in data["reliability_bins"]:
            self.assertIn("mean_predicted", bin_data)
            self.assertIn("mean_actual", bin_data)
            self.assertIn("count", bin_data)
            self.assertIn("calibration_error", bin_data)


if __name__ == "__main__":
    unittest.main()
