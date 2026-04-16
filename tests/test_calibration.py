"""Tests for Phase 14: Confidence Calibration System.

Tests cover:
- CalibrationDataset (Task 14.1)
- PatternCalibrator (Tasks 14.2 & 14.3)
- ContextFactors (Task 14.4)
- CalibrationPlotter (Task 14.5)
- ConfidenceExplainer (Task 14.6)
- CalibrationValidator (Task 14.7)
"""

import json
import tempfile
import unittest
from pathlib import Path

from alphaswarm_sol.calibration import (
    # Dataset
    CalibrationDataset,
    LabeledFinding,
    Label,
    load_benchmark_data,
    # Calibrator
    PatternCalibrator,
    CalibratorConfig,
    CalibrationMethod,
    calibrate_finding,
    # Context
    ContextFactors,
    ContextConfig,
    apply_context_factors,
    GUARD_MULTIPLIERS,
    # Visualization
    CalibrationPlotter,
    plot_reliability_diagram,
    plot_confidence_histogram,
    plot_before_after,
    # Explanation
    ConfidenceExplainer,
    ConfidenceExplanation,
    explain_confidence,
    format_explanation,
    # Validation
    CalibrationValidator,
    CalibrationMetrics,
    brier_score,
    expected_calibration_error,
    validate_calibration,
)


class TestLabel(unittest.TestCase):
    """Test Label enum."""

    def test_label_values(self):
        """Test label string values."""
        self.assertEqual(Label.TRUE_POSITIVE.value, "tp")
        self.assertEqual(Label.FALSE_POSITIVE.value, "fp")
        self.assertEqual(Label.UNCERTAIN.value, "uncertain")
        self.assertEqual(Label.OUT_OF_SCOPE.value, "oos")

    def test_label_from_string(self):
        """Test creating labels from strings."""
        self.assertEqual(Label("tp"), Label.TRUE_POSITIVE)
        self.assertEqual(Label("fp"), Label.FALSE_POSITIVE)


class TestLabeledFinding(unittest.TestCase):
    """Test LabeledFinding dataclass."""

    def test_create_labeled_finding(self):
        """Test creating a labeled finding."""
        finding = LabeledFinding(
            finding_id="test-001",
            pattern_id="vm-001",
            raw_confidence=0.8,
            label=Label.TRUE_POSITIVE,
            file="test.sol",
            line=42,
        )

        self.assertEqual(finding.finding_id, "test-001")
        self.assertEqual(finding.pattern_id, "vm-001")
        self.assertEqual(finding.raw_confidence, 0.8)
        self.assertEqual(finding.label, Label.TRUE_POSITIVE)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        finding = LabeledFinding(
            finding_id="test-001",
            pattern_id="vm-001",
            raw_confidence=0.8,
            label=Label.TRUE_POSITIVE,
        )

        d = finding.to_dict()
        self.assertEqual(d["finding_id"], "test-001")
        self.assertEqual(d["label"], "tp")

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "finding_id": "test-001",
            "pattern_id": "vm-001",
            "raw_confidence": 0.8,
            "label": "tp",
        }

        finding = LabeledFinding.from_dict(data)
        self.assertEqual(finding.finding_id, "test-001")
        self.assertEqual(finding.label, Label.TRUE_POSITIVE)


class TestCalibrationDataset(unittest.TestCase):
    """Test CalibrationDataset class."""

    def test_empty_dataset(self):
        """Test empty dataset."""
        dataset = CalibrationDataset()
        self.assertEqual(len(dataset), 0)
        self.assertEqual(dataset.get_all_patterns(), set())

    def test_add_finding(self):
        """Test adding a finding."""
        dataset = CalibrationDataset()

        finding = LabeledFinding(
            finding_id="test-001",
            pattern_id="vm-001",
            raw_confidence=0.8,
            label=Label.TRUE_POSITIVE,
        )

        dataset.add(finding)
        self.assertEqual(len(dataset), 1)
        self.assertIn("vm-001", dataset.get_all_patterns())

    def test_pattern_stats(self):
        """Test pattern statistics calculation."""
        dataset = CalibrationDataset()

        # Add 3 TPs and 2 FPs
        for i in range(3):
            dataset.add(LabeledFinding(
                finding_id=f"tp-{i}",
                pattern_id="vm-001",
                raw_confidence=0.8,
                label=Label.TRUE_POSITIVE,
            ))

        for i in range(2):
            dataset.add(LabeledFinding(
                finding_id=f"fp-{i}",
                pattern_id="vm-001",
                raw_confidence=0.8,
                label=Label.FALSE_POSITIVE,
            ))

        stats = dataset.get_pattern_stats("vm-001")
        self.assertEqual(stats.true_positives, 3)
        self.assertEqual(stats.false_positives, 2)
        self.assertEqual(stats.total_labeled, 5)
        self.assertEqual(stats.precision, 0.6)

    def test_load_from_bounds(self):
        """Test loading from bounds file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "vm-001": {
                    "sample_size": 10,
                    "observed_precision": 0.7,
                    "initial": 0.8,
                },
                "auth-001": {
                    "sample_size": 5,
                    "observed_precision": 0.8,
                    "initial": 0.75,
                },
            }, f)
            bounds_path = f.name

        try:
            dataset = CalibrationDataset()
            loaded = dataset.load_from_bounds(bounds_path)

            self.assertEqual(loaded, 2)  # 2 patterns
            self.assertEqual(len(dataset), 15)  # 10 + 5 findings
            self.assertIn("vm-001", dataset.get_all_patterns())
        finally:
            Path(bounds_path).unlink()

    def test_split(self):
        """Test train/validation split."""
        dataset = CalibrationDataset()

        # Add 10 findings
        for i in range(10):
            dataset.add(LabeledFinding(
                finding_id=f"finding-{i}",
                pattern_id="vm-001",
                raw_confidence=0.8,
                label=Label.TRUE_POSITIVE if i < 7 else Label.FALSE_POSITIVE,
            ))

        train, val = dataset.split(train_ratio=0.8, seed=42)

        self.assertEqual(len(train) + len(val), 10)
        self.assertGreater(len(train), len(val))

    def test_filter_by_labels(self):
        """Test filtering by labels."""
        dataset = CalibrationDataset()

        dataset.add(LabeledFinding(
            finding_id="tp-1",
            pattern_id="vm-001",
            raw_confidence=0.8,
            label=Label.TRUE_POSITIVE,
        ))
        dataset.add(LabeledFinding(
            finding_id="unc-1",
            pattern_id="vm-001",
            raw_confidence=0.5,
            label=Label.UNCERTAIN,
        ))

        filtered = dataset.filter_by_labels({Label.TRUE_POSITIVE})
        self.assertEqual(len(filtered), 1)

    def test_save_and_load_json(self):
        """Test saving and loading from JSON."""
        dataset = CalibrationDataset()
        dataset.add(LabeledFinding(
            finding_id="test-001",
            pattern_id="vm-001",
            raw_confidence=0.8,
            label=Label.TRUE_POSITIVE,
        ))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_path = f.name

        try:
            dataset.save_to_json(json_path)

            loaded_dataset = CalibrationDataset()
            loaded_count = loaded_dataset.load_from_json(json_path)

            self.assertEqual(loaded_count, 1)
            self.assertEqual(len(loaded_dataset), 1)
        finally:
            Path(json_path).unlink()


class TestPatternCalibrator(unittest.TestCase):
    """Test PatternCalibrator class."""

    def test_create_calibrator(self):
        """Test creating a calibrator."""
        calibrator = PatternCalibrator()
        self.assertIsNotNone(calibrator)

    def test_calibrate_unknown_pattern(self):
        """Test calibrating unknown pattern uses defaults."""
        calibrator = PatternCalibrator()

        result = calibrator.calibrate("unknown-pattern", 0.8)

        self.assertEqual(result.pattern_id, "unknown-pattern")
        self.assertIsNotNone(result.calibrated_confidence)
        self.assertEqual(result.method_used, CalibrationMethod.BAYESIAN)

    def test_calibrate_clamps_to_bounds(self):
        """Test calibration respects absolute bounds."""
        config = CalibratorConfig(
            absolute_min=0.1,
            absolute_max=0.9,
        )
        calibrator = PatternCalibrator(config=config)

        result = calibrator.calibrate("test-pattern", 0.99)
        self.assertLessEqual(result.calibrated_confidence, 0.9)

        result = calibrator.calibrate("test-pattern", 0.01)
        self.assertGreaterEqual(result.calibrated_confidence, 0.1)

    def test_from_bounds_file(self):
        """Test loading calibrator from bounds file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "vm-001": {
                    "pattern_id": "vm-001",
                    "lower_bound": 0.5,
                    "upper_bound": 0.9,
                    "initial": 0.7,
                    "observed_precision": 0.75,
                    "sample_size": 20,
                },
            }, f)
            bounds_path = f.name

        try:
            calibrator = PatternCalibrator.from_bounds_file(bounds_path)

            result = calibrator.calibrate("vm-001", 0.8)
            self.assertEqual(result.pattern_id, "vm-001")
            self.assertIsNotNone(result.bounds_used)
        finally:
            Path(bounds_path).unlink()

    def test_calibrate_finding_function(self):
        """Test convenience function."""
        result = calibrate_finding("test-pattern", 0.7)

        self.assertEqual(result.pattern_id, "test-pattern")
        self.assertIsNotNone(result.calibrated_confidence)

    def test_calibration_result_to_dict(self):
        """Test CalibrationResult serialization."""
        calibrator = PatternCalibrator()
        result = calibrator.calibrate("test-pattern", 0.8)

        d = result.to_dict()
        self.assertIn("pattern_id", d)
        self.assertIn("raw_confidence", d)
        self.assertIn("calibrated_confidence", d)
        self.assertIn("method_used", d)

    def test_save_and_load(self):
        """Test saving and loading calibrator state."""
        calibrator = PatternCalibrator()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            save_path = f.name

        try:
            calibrator.save(save_path)
            loaded = PatternCalibrator.load(save_path)

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.config.absolute_min, calibrator.config.absolute_min)
        finally:
            Path(save_path).unlink()


class TestContextFactors(unittest.TestCase):
    """Test ContextFactors class."""

    def test_create_context_factors(self):
        """Test creating context factors."""
        factors = ContextFactors()
        self.assertIsNotNone(factors)

    def test_apply_single_factor(self):
        """Test applying a single factor."""
        factors = ContextFactors()

        result = factors.apply(
            confidence=0.8,
            present_factors={"has_reentrancy_guard"},
        )

        # Reentrancy guard multiplier is 0.2
        self.assertLess(result.adjusted_confidence, 0.8)
        self.assertEqual(len(result.factors_applied), 1)

    def test_apply_multiple_factors(self):
        """Test applying multiple factors multiplicatively."""
        factors = ContextFactors()

        result = factors.apply(
            confidence=0.8,
            present_factors={"has_reentrancy_guard", "has_onlyowner"},
        )

        # Multiple guards should reduce confidence more
        self.assertEqual(len(result.factors_applied), 2)
        self.assertLess(result.adjusted_confidence, 0.8 * 0.4)  # Max of single guard

    def test_pattern_specific_adjustment(self):
        """Test pattern-specific factor adjustment."""
        factors = ContextFactors()

        # Reentrancy guard is extra effective against reentrancy patterns
        result = factors.apply(
            confidence=0.8,
            present_factors={"has_reentrancy_guard"},
            pattern_id="vm-001-reentrancy",
        )

        # Should be even lower due to pattern-specific boost
        self.assertLess(result.adjusted_confidence, 0.8 * 0.2)

    def test_minimum_multiplier_respected(self):
        """Test minimum multiplier is respected."""
        config = ContextConfig(min_multiplier=0.1)
        factors = ContextFactors(config=config)

        result = factors.apply(
            confidence=0.8,
            present_factors={"has_reentrancy_guard", "has_nonreentrant_modifier", "has_mutex_lock"},
        )

        # Even with multiple strong guards, shouldn't go below min
        self.assertGreaterEqual(result.combined_multiplier, 0.1)

    def test_unknown_factor_ignored(self):
        """Test unknown factors are ignored."""
        factors = ContextFactors()

        result = factors.apply(
            confidence=0.8,
            present_factors={"unknown_factor"},
        )

        self.assertEqual(result.adjusted_confidence, 0.8)
        self.assertEqual(len(result.factors_applied), 0)

    def test_apply_context_factors_function(self):
        """Test convenience function."""
        result = apply_context_factors(
            confidence=0.8,
            present_factors={"has_access_gate"},
        )

        self.assertLess(result.adjusted_confidence, 0.8)

    def test_context_result_to_dict(self):
        """Test ContextResult serialization."""
        factors = ContextFactors()
        result = factors.apply(
            confidence=0.8,
            present_factors={"has_reentrancy_guard"},
        )

        d = result.to_dict()
        self.assertIn("original_confidence", d)
        self.assertIn("adjusted_confidence", d)
        self.assertIn("factors_applied", d)

    def test_custom_multipliers(self):
        """Test custom multipliers override defaults."""
        config = ContextConfig(
            custom_multipliers={"custom_guard": 0.1}
        )
        factors = ContextFactors(config=config)

        result = factors.apply(
            confidence=0.8,
            present_factors={"custom_guard"},
        )

        self.assertAlmostEqual(result.adjusted_confidence, 0.08)


class TestCalibrationPlotter(unittest.TestCase):
    """Test CalibrationPlotter class."""

    def test_create_plotter(self):
        """Test creating a plotter."""
        plotter = CalibrationPlotter()
        self.assertIsNotNone(plotter)

    def test_add_points(self):
        """Test adding data points."""
        plotter = CalibrationPlotter()

        plotter.add_point(0.8, 1)
        plotter.add_point(0.6, 0)
        plotter.add_points([0.7, 0.9], [1, 1])

        # Should have 4 points total
        data = plotter.compute_reliability()
        self.assertEqual(data.n_samples, 4)

    def test_compute_reliability_empty(self):
        """Test computing reliability with no data."""
        plotter = CalibrationPlotter()
        data = plotter.compute_reliability()

        self.assertEqual(data.n_samples, 0)
        self.assertEqual(data.expected_calibration_error, 0.0)

    def test_compute_reliability_perfect(self):
        """Test computing reliability with perfect calibration."""
        plotter = CalibrationPlotter(n_bins=10)

        # Add perfectly calibrated data: 80% confidence, 80% actual
        for i in range(80):
            plotter.add_point(0.8, 1)  # TP
        for i in range(20):
            plotter.add_point(0.8, 0)  # FP

        data = plotter.compute_reliability()

        # ECE should be low (data matches confidence)
        self.assertLess(data.expected_calibration_error, 0.1)

    def test_compute_reliability_poor(self):
        """Test computing reliability with poor calibration."""
        plotter = CalibrationPlotter(n_bins=10)

        # Add poorly calibrated data: 80% confidence, but only 20% actual
        for i in range(20):
            plotter.add_point(0.8, 1)  # TP
        for i in range(80):
            plotter.add_point(0.8, 0)  # FP

        data = plotter.compute_reliability()

        # ECE should be high (big gap between predicted and actual)
        self.assertGreater(data.expected_calibration_error, 0.3)

    def test_reliability_data_to_dict(self):
        """Test ReliabilityData serialization."""
        plotter = CalibrationPlotter()
        plotter.add_points([0.8, 0.6], [1, 0])

        data = plotter.compute_reliability()
        d = data.to_dict()

        self.assertIn("n_samples", d)
        self.assertIn("expected_calibration_error", d)
        self.assertIn("bins", d)

    def test_clear(self):
        """Test clearing data."""
        plotter = CalibrationPlotter()
        plotter.add_point(0.8, 1)

        plotter.clear()
        data = plotter.compute_reliability()

        self.assertEqual(data.n_samples, 0)

    def test_plot_reliability_diagram_function(self):
        """Test convenience function."""
        data = plot_reliability_diagram(
            predicted=[0.8, 0.6, 0.7],
            actual=[1, 0, 1],
        )

        self.assertEqual(data.n_samples, 3)


class TestConfidenceExplainer(unittest.TestCase):
    """Test ConfidenceExplainer class."""

    def test_create_explainer(self):
        """Test creating an explainer."""
        explainer = ConfidenceExplainer()
        self.assertIsNotNone(explainer)

    def test_explain_basic(self):
        """Test basic explanation generation."""
        explainer = ConfidenceExplainer()

        explanation = explainer.explain(
            confidence=0.75,
            pattern_id="vm-001",
        )

        self.assertEqual(explanation.confidence, 0.75)
        self.assertEqual(explanation.pattern_id, "vm-001")
        self.assertEqual(explanation.level, "high")
        self.assertIn("reentrancy", explanation.pattern_description.lower())

    def test_explain_with_evidence(self):
        """Test explanation with evidence."""
        explainer = ConfidenceExplainer()

        explanation = explainer.explain(
            confidence=0.85,
            pattern_id="vm-001",
            positive_evidence=["External call before state update"],
            negative_evidence=["Function is internal"],
        )

        self.assertEqual(len(explanation.positive_factors), 1)
        self.assertEqual(len(explanation.negative_factors), 1)

    def test_explain_with_context(self):
        """Test explanation with context adjustments."""
        factors = ContextFactors()
        context_result = factors.apply(0.8, {"has_reentrancy_guard"})

        explainer = ConfidenceExplainer()
        explanation = explainer.explain(
            confidence=0.16,  # After adjustment
            pattern_id="vm-001",
            context_result=context_result,
        )

        self.assertGreater(len(explanation.context_adjustments), 0)

    def test_confidence_levels(self):
        """Test confidence level assignment."""
        explainer = ConfidenceExplainer()

        # Critical
        exp = explainer.explain(0.95, "test")
        self.assertEqual(exp.level, "critical")

        # High
        exp = explainer.explain(0.75, "test")
        self.assertEqual(exp.level, "high")

        # Medium
        exp = explainer.explain(0.55, "test")
        self.assertEqual(exp.level, "medium")

        # Low
        exp = explainer.explain(0.35, "test")
        self.assertEqual(exp.level, "low")

        # Very low
        exp = explainer.explain(0.15, "test")
        self.assertEqual(exp.level, "very_low")

    def test_to_markdown(self):
        """Test markdown output."""
        explainer = ConfidenceExplainer()
        explanation = explainer.explain(0.75, "vm-001")

        md = explanation.to_markdown()
        self.assertIn("##", md)
        self.assertIn("75.0%", md)

    def test_to_text(self):
        """Test plain text output."""
        explainer = ConfidenceExplainer()
        explanation = explainer.explain(0.75, "vm-001")

        text = explanation.to_text()
        self.assertIn("75.0%", text)
        self.assertIn("vm-001", text)

    def test_to_dict(self):
        """Test dictionary output."""
        explainer = ConfidenceExplainer()
        explanation = explainer.explain(0.75, "vm-001")

        d = explanation.to_dict()
        self.assertIn("confidence", d)
        self.assertIn("level", d)
        self.assertIn("pattern_id", d)

    def test_explain_confidence_function(self):
        """Test convenience function."""
        explanation = explain_confidence(0.75, "vm-001")

        self.assertEqual(explanation.confidence, 0.75)

    def test_format_explanation_function(self):
        """Test format function."""
        explanation = explain_confidence(0.75, "vm-001")

        text = format_explanation(explanation, "text")
        self.assertIn("75.0%", text)

        md = format_explanation(explanation, "markdown")
        self.assertIn("##", md)

        json_str = format_explanation(explanation, "json")
        self.assertIn('"confidence"', json_str)


class TestCalibrationValidator(unittest.TestCase):
    """Test CalibrationValidator class."""

    def test_create_validator(self):
        """Test creating a validator."""
        validator = CalibrationValidator()
        self.assertIsNotNone(validator)

    def test_brier_score_perfect(self):
        """Test Brier score with perfect predictions."""
        # Perfect predictions: 1.0 for TP, 0.0 for FP
        predicted = [1.0, 1.0, 0.0, 0.0]
        actual = [1, 1, 0, 0]

        score = brier_score(predicted, actual)
        self.assertEqual(score, 0.0)

    def test_brier_score_worst(self):
        """Test Brier score with worst predictions."""
        # Worst: predict opposite
        predicted = [0.0, 0.0, 1.0, 1.0]
        actual = [1, 1, 0, 0]

        score = brier_score(predicted, actual)
        self.assertEqual(score, 1.0)

    def test_brier_score_medium(self):
        """Test Brier score with medium predictions."""
        # Always predict 0.5
        predicted = [0.5, 0.5, 0.5, 0.5]
        actual = [1, 1, 0, 0]

        score = brier_score(predicted, actual)
        self.assertEqual(score, 0.25)  # (0.5)^2 = 0.25

    def test_ece_perfect(self):
        """Test ECE with perfect calibration."""
        # 80% confidence, 80% actual
        predicted = [0.8] * 100
        actual = [1] * 80 + [0] * 20

        ece = expected_calibration_error(predicted, actual)
        self.assertLess(ece, 0.05)  # Should be close to 0

    def test_ece_poor(self):
        """Test ECE with poor calibration."""
        # 80% confidence, only 20% actual
        predicted = [0.8] * 100
        actual = [1] * 20 + [0] * 80

        ece = expected_calibration_error(predicted, actual)
        self.assertGreater(ece, 0.5)  # Big gap

    def test_compute_metrics(self):
        """Test computing full metrics."""
        validator = CalibrationValidator()

        # Add some predictions
        for i in range(50):
            validator.add_prediction(0.8, 1)
        for i in range(50):
            validator.add_prediction(0.8, 0)

        metrics = validator.compute_metrics()

        self.assertEqual(metrics.n_samples, 100)
        self.assertEqual(metrics.n_true_positives, 50)
        self.assertEqual(metrics.n_false_positives, 50)
        self.assertIsNotNone(metrics.brier_score)
        self.assertIsNotNone(metrics.expected_calibration_error)

    def test_is_well_calibrated(self):
        """Test well-calibrated check."""
        # Create perfectly calibrated data
        validator = CalibrationValidator()
        for i in range(80):
            validator.add_prediction(0.8, 1)
        for i in range(20):
            validator.add_prediction(0.8, 0)

        metrics = validator.compute_metrics()
        self.assertTrue(metrics.is_well_calibrated())

        # Create poorly calibrated data
        validator.clear()
        for i in range(20):
            validator.add_prediction(0.8, 1)
        for i in range(80):
            validator.add_prediction(0.8, 0)

        metrics = validator.compute_metrics()
        self.assertFalse(metrics.is_well_calibrated())

    def test_validate_from_dataset(self):
        """Test validation from dataset."""
        dataset = CalibrationDataset()

        for i in range(10):
            dataset.add(LabeledFinding(
                finding_id=f"tp-{i}",
                pattern_id="vm-001",
                raw_confidence=0.8,
                label=Label.TRUE_POSITIVE,
            ))
        for i in range(10):
            dataset.add(LabeledFinding(
                finding_id=f"fp-{i}",
                pattern_id="vm-001",
                raw_confidence=0.8,
                label=Label.FALSE_POSITIVE,
            ))

        validator = CalibrationValidator()
        metrics = validator.validate_from_dataset(dataset, "vm-001")

        self.assertEqual(metrics.n_samples, 20)

    def test_compare_calibrations(self):
        """Test comparing before/after calibration."""
        validator = CalibrationValidator()

        actuals = [1] * 80 + [0] * 20

        # Before: poorly calibrated (predict 0.5 always)
        before = [0.5] * 100

        # After: well calibrated (predict 0.8)
        after = [0.8] * 100

        comparison = validator.compare_calibrations(before, after, actuals)

        self.assertIn("before", comparison)
        self.assertIn("after", comparison)
        self.assertIn("improvements", comparison)
        self.assertTrue(comparison["is_improved"])

    def test_validate_calibration_function(self):
        """Test convenience function."""
        metrics = validate_calibration(
            predictions=[0.8, 0.6, 0.7],
            actuals=[1, 0, 1],
        )

        self.assertEqual(metrics.n_samples, 3)

    def test_metrics_to_dict(self):
        """Test CalibrationMetrics serialization."""
        validator = CalibrationValidator()
        validator.add_predictions([0.8, 0.6], [1, 0])

        metrics = validator.compute_metrics()
        d = metrics.to_dict()

        self.assertIn("brier_score", d)
        self.assertIn("expected_calibration_error", d)
        self.assertIn("n_samples", d)

    def test_metrics_summary(self):
        """Test metrics summary generation."""
        validator = CalibrationValidator()
        validator.add_predictions([0.8] * 80 + [0.2] * 20, [1] * 80 + [0] * 20)

        metrics = validator.compute_metrics()
        summary = metrics.summary()

        self.assertIn("Calibration Validation Results", summary)
        self.assertIn("Brier Score", summary)
        self.assertIn("ECE", summary)


class TestIntegration(unittest.TestCase):
    """Integration tests for the calibration system."""

    def test_full_calibration_workflow(self):
        """Test complete calibration workflow."""
        # 1. Create dataset
        dataset = CalibrationDataset()
        for i in range(80):
            dataset.add(LabeledFinding(
                finding_id=f"tp-{i}",
                pattern_id="vm-001",
                raw_confidence=0.8,
                label=Label.TRUE_POSITIVE,
            ))
        for i in range(20):
            dataset.add(LabeledFinding(
                finding_id=f"fp-{i}",
                pattern_id="vm-001",
                raw_confidence=0.8,
                label=Label.FALSE_POSITIVE,
            ))

        # 2. Create calibrator and calibrate
        calibrator = PatternCalibrator()
        result = calibrator.calibrate("vm-001", 0.8)

        # 3. Apply context factors
        factors = ContextFactors()
        context_result = factors.apply(
            confidence=result.calibrated_confidence,
            present_factors={"has_access_gate"},
            pattern_id="vm-001",
        )

        # 4. Generate explanation
        explanation = explain_confidence(
            confidence=context_result.adjusted_confidence,
            pattern_id="vm-001",
            context_result=context_result,
            calibration_result=result,
        )

        # 5. Validate
        validator = CalibrationValidator()
        metrics = validator.validate_from_dataset(dataset, "vm-001")

        # Assertions
        self.assertIsNotNone(result.calibrated_confidence)
        self.assertLess(context_result.adjusted_confidence, result.calibrated_confidence)
        self.assertEqual(explanation.pattern_id, "vm-001")
        self.assertEqual(metrics.n_samples, 100)

    def test_reliability_diagram_workflow(self):
        """Test reliability diagram generation."""
        plotter = CalibrationPlotter(n_bins=5)

        # Add varied calibration data
        plotter.add_points(
            predicted=[0.1, 0.1, 0.3, 0.3, 0.5, 0.5, 0.7, 0.7, 0.9, 0.9],
            actual=[0, 0, 0, 1, 0, 1, 1, 1, 1, 1],
        )

        data = plotter.compute_reliability()

        self.assertEqual(data.n_samples, 10)
        self.assertGreater(len(data.bins), 0)

    def test_context_with_calibration(self):
        """Test context factors integrated with calibration."""
        # Start with high confidence
        initial = 0.9

        # Calibrate
        calibrator = PatternCalibrator()
        cal_result = calibrator.calibrate("vm-001", initial)

        # Apply strong guard
        factors = ContextFactors()
        ctx_result = factors.apply(
            confidence=cal_result.calibrated_confidence,
            present_factors={"has_reentrancy_guard", "has_nonreentrant_modifier"},
            pattern_id="vm-001",
        )

        # Should be significantly reduced
        self.assertLess(ctx_result.adjusted_confidence, initial * 0.5)

        # Generate explanation
        explanation = explain_confidence(
            confidence=ctx_result.adjusted_confidence,
            pattern_id="vm-001",
            context_result=ctx_result,
            calibration_result=cal_result,
        )

        # Should show context adjustments
        self.assertGreater(len(explanation.context_adjustments), 0)


if __name__ == "__main__":
    unittest.main()
