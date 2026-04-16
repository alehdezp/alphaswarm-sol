"""Tests for label evaluation harness.

Tests cover:
- PrecisionMetrics calculations (perfect, partial, zero division)
- DetectionMetrics delta (improvement, regression)
- TokenMetrics averaging
- LabelEvaluator with ground truth
- Exit gate checking (pass, fail)
- run_evaluation convenience function
"""

import pytest
from alphaswarm_sol.labels.schema import FunctionLabel, LabelConfidence, LabelSource, LabelSet
from alphaswarm_sol.labels.overlay import LabelOverlay
from alphaswarm_sol.labels.evaluation import (
    LabelEvaluator,
    EvaluationReport,
    PrecisionMetrics,
    DetectionMetrics,
    TokenMetrics,
    run_evaluation,
    compare_overlays,
)


class TestPrecisionMetrics:
    """Test precision metrics calculations."""

    def test_perfect_precision(self):
        """Test 100% precision when all predictions are correct."""
        metrics = PrecisionMetrics(
            true_positives=10,
            false_positives=0,
            false_negatives=0,
        )
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0
        assert metrics.f1_score == 1.0

    def test_partial_precision(self):
        """Test partial precision with some errors."""
        metrics = PrecisionMetrics(
            true_positives=8,
            false_positives=2,
            false_negatives=2,
        )
        assert metrics.precision == 0.8  # 8 / (8 + 2)
        assert metrics.recall == 0.8     # 8 / (8 + 2)
        assert abs(metrics.f1_score - 0.8) < 0.001  # 2 * (0.8 * 0.8) / (0.8 + 0.8)

    def test_high_precision_low_recall(self):
        """Test when precision is high but recall is low."""
        metrics = PrecisionMetrics(
            true_positives=2,
            false_positives=0,
            false_negatives=8,
        )
        assert metrics.precision == 1.0  # 2 / (2 + 0)
        assert metrics.recall == 0.2     # 2 / (2 + 8)

    def test_low_precision_high_recall(self):
        """Test when precision is low but recall is high."""
        metrics = PrecisionMetrics(
            true_positives=8,
            false_positives=12,
            false_negatives=2,
        )
        assert metrics.precision == 0.4  # 8 / (8 + 12)
        assert metrics.recall == 0.8     # 8 / (8 + 2)

    def test_zero_division_no_predictions(self):
        """Test handling of zero division when no predictions."""
        metrics = PrecisionMetrics(
            true_positives=0,
            false_positives=0,
            false_negatives=5,
        )
        assert metrics.precision == 0.0
        assert metrics.recall == 0.0
        assert metrics.f1_score == 0.0

    def test_zero_division_empty(self):
        """Test handling when everything is zero."""
        metrics = PrecisionMetrics(
            true_positives=0,
            false_positives=0,
            false_negatives=0,
        )
        assert metrics.precision == 0.0
        assert metrics.recall == 0.0
        assert metrics.f1_score == 0.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        metrics = PrecisionMetrics(
            true_positives=8,
            false_positives=2,
            false_negatives=2,
            total_predicted=10,
            total_ground_truth=10,
        )
        d = metrics.to_dict()
        assert d["true_positives"] == 8
        assert d["false_positives"] == 2
        assert d["precision"] == 0.8
        assert d["recall"] == 0.8


class TestDetectionMetrics:
    """Test detection delta calculations."""

    def test_improvement(self):
        """Test detection improvement (positive delta)."""
        metrics = DetectionMetrics(
            baseline_findings=10,
            label_findings=12,
            new_findings=2,
            lost_findings=0,
        )
        assert metrics.detection_delta == 20.0  # 2 / 10 * 100
        assert metrics.net_change == 2

    def test_regression(self):
        """Test detection regression (negative delta)."""
        metrics = DetectionMetrics(
            baseline_findings=10,
            label_findings=8,
            new_findings=0,
            lost_findings=2,
        )
        assert metrics.detection_delta == -20.0  # (0 - 2) / 10 * 100
        assert metrics.net_change == -2

    def test_mixed_change(self):
        """Test mixed improvements and regressions."""
        metrics = DetectionMetrics(
            baseline_findings=10,
            label_findings=11,
            new_findings=3,
            lost_findings=2,
        )
        assert metrics.detection_delta == 10.0  # (3 - 2) / 10 * 100
        assert metrics.net_change == 1

    def test_zero_baseline(self):
        """Test when baseline is zero."""
        metrics = DetectionMetrics(
            baseline_findings=0,
            label_findings=5,
            new_findings=5,
            lost_findings=0,
        )
        assert metrics.detection_delta == float('inf')

    def test_zero_baseline_no_new(self):
        """Test when baseline is zero and no new findings."""
        metrics = DetectionMetrics(
            baseline_findings=0,
            label_findings=0,
            new_findings=0,
            lost_findings=0,
        )
        assert metrics.detection_delta == 0.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        metrics = DetectionMetrics(
            baseline_findings=10,
            label_findings=12,
            new_findings=2,
            lost_findings=0,
        )
        d = metrics.to_dict()
        assert d["baseline_findings"] == 10
        assert d["detection_delta"] == 20.0


class TestTokenMetrics:
    """Test token metrics calculations."""

    def test_calculate_averages(self):
        """Test average calculation."""
        metrics = TokenMetrics(
            total_tokens=1000,
            functions_labeled=10,
        )
        metrics.calculate_averages()
        assert metrics.avg_tokens_per_function == 100.0

    def test_zero_functions(self):
        """Test when no functions labeled."""
        metrics = TokenMetrics(
            total_tokens=0,
            functions_labeled=0,
        )
        metrics.calculate_averages()
        assert metrics.avg_tokens_per_function == 0.0

    def test_to_dict(self):
        """Test serialization."""
        metrics = TokenMetrics(
            total_tokens=5000,
            total_cost_usd=0.05,
            functions_labeled=50,
            max_tokens_single_call=500,
        )
        metrics.calculate_averages()
        d = metrics.to_dict()
        assert d["total_tokens"] == 5000
        assert d["avg_tokens_per_function"] == 100.0


class TestLabelEvaluator:
    """Test label evaluator."""

    @pytest.fixture
    def ground_truth(self):
        """Create ground truth overlay."""
        overlay = LabelOverlay()
        overlay.add_label(
            "func_1",
            FunctionLabel("access_control.owner_only", LabelConfidence.HIGH, LabelSource.USER_OVERRIDE)
        )
        overlay.add_label(
            "func_1",
            FunctionLabel("state_mutation.writes_critical", LabelConfidence.MEDIUM, LabelSource.USER_OVERRIDE)
        )
        overlay.add_label(
            "func_2",
            FunctionLabel("value_handling.transfers_value_out", LabelConfidence.HIGH, LabelSource.USER_OVERRIDE)
        )
        return overlay

    @pytest.fixture
    def predicted_perfect(self, ground_truth):
        """Create perfect prediction (matches ground truth exactly)."""
        # Create a new overlay with the same labels
        overlay = LabelOverlay()
        overlay.add_label(
            "func_1",
            FunctionLabel("access_control.owner_only", LabelConfidence.HIGH, LabelSource.LLM)
        )
        overlay.add_label(
            "func_1",
            FunctionLabel("state_mutation.writes_critical", LabelConfidence.MEDIUM, LabelSource.LLM)
        )
        overlay.add_label(
            "func_2",
            FunctionLabel("value_handling.transfers_value_out", LabelConfidence.HIGH, LabelSource.LLM)
        )
        return overlay

    @pytest.fixture
    def predicted_partial(self):
        """Create partial prediction with errors."""
        overlay = LabelOverlay()
        # Match one label
        overlay.add_label(
            "func_1",
            FunctionLabel("access_control.owner_only", LabelConfidence.HIGH, LabelSource.LLM)
        )
        # Miss one label (state_mutation.writes_critical)
        # Add false positive
        overlay.add_label(
            "func_1",
            FunctionLabel("external_interaction.calls_external", LabelConfidence.MEDIUM, LabelSource.LLM)
        )
        # Miss func_2 entirely
        return overlay

    def test_perfect_evaluation(self, ground_truth, predicted_perfect):
        """Test evaluation with perfect prediction."""
        evaluator = LabelEvaluator(ground_truth)
        report = evaluator.evaluate(predicted_perfect)

        assert report.precision_metrics.precision == 1.0
        assert report.precision_metrics.recall == 1.0
        assert report.precision_metrics.true_positives == 3
        assert report.precision_metrics.false_positives == 0
        assert report.precision_metrics.false_negatives == 0

    def test_partial_evaluation(self, ground_truth, predicted_partial):
        """Test evaluation with partial prediction."""
        evaluator = LabelEvaluator(ground_truth)
        report = evaluator.evaluate(predicted_partial)

        # 1 true positive (access_control.owner_only)
        # 1 false positive (external_interaction.calls_external)
        # 2 false negatives (state_mutation.writes_critical, value_handling.transfers_value_out)
        assert report.precision_metrics.true_positives == 1
        assert report.precision_metrics.false_positives == 1
        assert report.precision_metrics.false_negatives == 2
        assert report.precision_metrics.precision == 0.5

    def test_evaluate_with_detection_metrics(self, ground_truth, predicted_perfect):
        """Test evaluation with detection metrics."""
        evaluator = LabelEvaluator(ground_truth)
        report = evaluator.evaluate(
            predicted_perfect,
            baseline_findings=10,
            label_findings=12,
        )

        assert report.detection_metrics.baseline_findings == 10
        assert report.detection_metrics.label_findings == 12
        assert report.detection_metrics.new_findings == 2
        assert report.detection_metrics.detection_delta == 20.0

    def test_exit_gate_pass(self, ground_truth, predicted_perfect):
        """Test exit gate passing all criteria."""
        evaluator = LabelEvaluator(ground_truth)
        report = evaluator.evaluate(
            predicted_perfect,
            token_metrics=TokenMetrics(total_tokens=5000, max_tokens_single_call=5000),
        )

        # Set detection metrics for exit gate test
        report.detection_metrics.baseline_findings = 10
        report.detection_metrics.label_findings = 11
        report.detection_metrics.new_findings = 1

        passed = report.check_exit_gate(
            min_precision=0.75,
            min_detection_delta=5.0,
            max_tokens_per_call=6000,
        )

        assert passed
        assert report.exit_gate_details["precision_met"]
        assert report.exit_gate_details["detection_delta_met"]
        assert report.exit_gate_details["token_budget_met"]

    def test_exit_gate_fail_precision(self, ground_truth, predicted_partial):
        """Test exit gate failing on precision."""
        evaluator = LabelEvaluator(ground_truth)
        report = evaluator.evaluate(predicted_partial)

        passed = report.check_exit_gate(min_precision=0.75)

        assert not passed
        assert not report.exit_gate_details["precision_met"]

    def test_exit_gate_fail_tokens(self, ground_truth, predicted_perfect):
        """Test exit gate failing on token budget."""
        evaluator = LabelEvaluator(ground_truth)
        report = evaluator.evaluate(
            predicted_perfect,
            token_metrics=TokenMetrics(max_tokens_single_call=8000),
        )

        # Set detection metrics
        report.detection_metrics.baseline_findings = 10
        report.detection_metrics.new_findings = 1

        passed = report.check_exit_gate(max_tokens_per_call=6000)

        assert not passed
        assert not report.exit_gate_details["token_budget_met"]

    def test_evaluate_by_category(self, ground_truth, predicted_partial):
        """Test category-wise evaluation."""
        evaluator = LabelEvaluator(ground_truth)
        cat_metrics = evaluator.evaluate_by_category(predicted_partial)

        # access_control: 1 TP (owner_only)
        assert "access_control" in cat_metrics
        assert cat_metrics["access_control"].true_positives == 1
        assert cat_metrics["access_control"].false_positives == 0

        # external_interaction: 1 FP (calls_external not in GT)
        assert "external_interaction" in cat_metrics
        assert cat_metrics["external_interaction"].false_positives == 1


class TestRunEvaluation:
    """Test convenience function."""

    def test_run_evaluation(self):
        """Test run_evaluation function."""
        gt = LabelOverlay()
        gt.add_label(
            "f1",
            FunctionLabel("access_control.owner_only", LabelConfidence.HIGH, LabelSource.USER_OVERRIDE)
        )

        pred = LabelOverlay()
        pred.add_label(
            "f1",
            FunctionLabel("access_control.owner_only", LabelConfidence.MEDIUM, LabelSource.LLM)
        )

        report = run_evaluation(pred, gt)

        assert report.precision_metrics.precision == 1.0
        assert report.precision_metrics.true_positives == 1

    def test_run_evaluation_with_tokens(self):
        """Test run_evaluation with token metrics."""
        gt = LabelOverlay()
        gt.add_label(
            "f1",
            FunctionLabel("access_control.owner_only", LabelConfidence.HIGH, LabelSource.USER_OVERRIDE)
        )

        pred = LabelOverlay()
        pred.add_label(
            "f1",
            FunctionLabel("access_control.owner_only", LabelConfidence.MEDIUM, LabelSource.LLM)
        )

        token_metrics = TokenMetrics(total_tokens=1000, functions_labeled=1)
        report = run_evaluation(pred, gt, token_metrics)

        assert report.token_metrics.total_tokens == 1000


class TestCompareOverlays:
    """Test overlay comparison."""

    def test_compare_same(self):
        """Test comparing identical overlays."""
        overlay = LabelOverlay()
        overlay.add_label(
            "f1",
            FunctionLabel("access_control.owner_only", LabelConfidence.HIGH, LabelSource.LLM)
        )

        result = compare_overlays(overlay, overlay)

        assert "f1" in result["same"]
        assert len(result["only_in_a"]) == 0
        assert len(result["only_in_b"]) == 0
        assert len(result["different"]) == 0

    def test_compare_different(self):
        """Test comparing different overlays."""
        overlay_a = LabelOverlay()
        overlay_a.add_label(
            "f1",
            FunctionLabel("access_control.owner_only", LabelConfidence.HIGH, LabelSource.LLM)
        )

        overlay_b = LabelOverlay()
        overlay_b.add_label(
            "f1",
            FunctionLabel("access_control.role_based", LabelConfidence.HIGH, LabelSource.LLM)
        )

        result = compare_overlays(overlay_a, overlay_b)

        assert "f1" in result["different"]
        assert len(result["same"]) == 0

    def test_compare_only_in_one(self):
        """Test comparing overlays with unique functions."""
        overlay_a = LabelOverlay()
        overlay_a.add_label(
            "f1",
            FunctionLabel("access_control.owner_only", LabelConfidence.HIGH, LabelSource.LLM)
        )

        overlay_b = LabelOverlay()
        overlay_b.add_label(
            "f2",
            FunctionLabel("access_control.role_based", LabelConfidence.HIGH, LabelSource.LLM)
        )

        result = compare_overlays(overlay_a, overlay_b)

        assert "f1" in result["only_in_a"]
        assert "f2" in result["only_in_b"]


class TestEvaluationReport:
    """Test evaluation report methods."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        report = EvaluationReport()
        report.precision_metrics = PrecisionMetrics(
            true_positives=8,
            false_positives=2,
        )
        report.check_exit_gate()

        d = report.to_dict()

        assert "precision" in d
        assert "detection" in d
        assert "tokens" in d
        assert "exit_gate" in d
        assert d["precision"]["precision"] == 0.8

    def test_summary(self):
        """Test summary generation."""
        report = EvaluationReport()
        report.precision_metrics = PrecisionMetrics(
            true_positives=8,
            false_positives=2,
        )
        report.detection_metrics = DetectionMetrics(
            baseline_findings=10,
            new_findings=1,
        )
        report.check_exit_gate()

        summary = report.summary()

        assert "Precision: 80.00%" in summary
        assert "Exit Gate:" in summary
