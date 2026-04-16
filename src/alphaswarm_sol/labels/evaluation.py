"""Label Evaluation Harness.

Measures label precision, detection delta, and token efficiency for
evaluating the semantic labeling system.

The evaluation harness supports:
- Precision metrics (TP, FP, FN, precision, recall, F1)
- Detection delta (improvement from labels)
- Token usage tracking
- Exit gate checking for phase completion

Exit Gate Criteria (LABEL-12):
- Label precision >= 0.75
- Detection delta >= +5%
- Token budget <= 6000 per call
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from alphaswarm_sol.labels.schema import FunctionLabel, LabelConfidence, LabelSet
from alphaswarm_sol.labels.overlay import LabelOverlay
from alphaswarm_sol.labels.validator import LabelValidator, QualityScore

if TYPE_CHECKING:
    from alphaswarm_sol.kg.schema import KnowledgeGraph

logger = logging.getLogger(__name__)


@dataclass
class PrecisionMetrics:
    """Precision metrics for label evaluation.

    Attributes:
        true_positives: Labels correctly predicted (in both predicted and GT)
        false_positives: Labels incorrectly predicted (in predicted but not GT)
        false_negatives: Labels missed (in GT but not predicted)
        total_predicted: Total number of predicted labels
        total_ground_truth: Total number of ground truth labels
    """

    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    total_predicted: int = 0
    total_ground_truth: int = 0

    @property
    def precision(self) -> float:
        """Calculate precision = TP / (TP + FP).

        Returns:
            Precision score (0.0-1.0), 0.0 if no predictions
        """
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)

    @property
    def recall(self) -> float:
        """Calculate recall = TP / (TP + FN).

        Returns:
            Recall score (0.0-1.0), 0.0 if no ground truth
        """
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)

    @property
    def f1_score(self) -> float:
        """Calculate F1 = 2 * (P * R) / (P + R).

        Returns:
            F1 score (0.0-1.0), 0.0 if precision and recall are both 0
        """
        p, r = self.precision, self.recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary with all metrics
        """
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "total_predicted": self.total_predicted,
            "total_ground_truth": self.total_ground_truth,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
        }


@dataclass
class DetectionMetrics:
    """Detection metrics comparing with/without labels.

    Attributes:
        baseline_findings: Findings without labels (Tier A/B only)
        label_findings: Findings with labels (Tier A/B/C)
        new_findings: Additional findings from labels
        lost_findings: Findings lost after adding labels
    """

    baseline_findings: int = 0
    label_findings: int = 0
    new_findings: int = 0
    lost_findings: int = 0

    @property
    def detection_delta(self) -> float:
        """Calculate detection improvement percentage.

        Returns:
            Delta as percentage (e.g., 10.0 means +10% improvement)
            Returns inf if baseline is 0 and new findings > 0
        """
        if self.baseline_findings == 0:
            return float('inf') if self.new_findings > 0 else 0.0
        return (self.new_findings - self.lost_findings) / self.baseline_findings * 100

    @property
    def net_change(self) -> int:
        """Net change in findings count.

        Returns:
            Positive for improvement, negative for regression
        """
        return self.new_findings - self.lost_findings

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary with all metrics
        """
        return {
            "baseline_findings": self.baseline_findings,
            "label_findings": self.label_findings,
            "new_findings": self.new_findings,
            "lost_findings": self.lost_findings,
            "detection_delta": round(self.detection_delta, 2) if self.detection_delta != float('inf') else "inf",
            "net_change": self.net_change,
        }


@dataclass
class TokenMetrics:
    """Token usage metrics for LLM labeling.

    Attributes:
        total_tokens: Total tokens used across all calls
        total_cost_usd: Estimated cost in USD
        functions_labeled: Number of functions labeled
        avg_tokens_per_function: Average tokens per function
        max_tokens_single_call: Maximum tokens in a single call
    """

    total_tokens: int = 0
    total_cost_usd: float = 0.0
    functions_labeled: int = 0
    avg_tokens_per_function: float = 0.0
    max_tokens_single_call: int = 0

    def calculate_averages(self) -> None:
        """Calculate average metrics from totals."""
        if self.functions_labeled > 0:
            self.avg_tokens_per_function = self.total_tokens / self.functions_labeled

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary with all metrics
        """
        return {
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "functions_labeled": self.functions_labeled,
            "avg_tokens_per_function": round(self.avg_tokens_per_function, 2),
            "max_tokens_single_call": self.max_tokens_single_call,
        }


@dataclass
class EvaluationReport:
    """Complete evaluation report.

    Attributes:
        precision_metrics: Label precision metrics
        detection_metrics: Detection improvement metrics
        token_metrics: Token usage metrics
        quality_scores: Quality scores per function
        passed_exit_gate: Whether evaluation passes exit gate
        exit_gate_details: Detailed pass/fail for each criterion
    """

    precision_metrics: PrecisionMetrics = field(default_factory=PrecisionMetrics)
    detection_metrics: DetectionMetrics = field(default_factory=DetectionMetrics)
    token_metrics: TokenMetrics = field(default_factory=TokenMetrics)
    quality_scores: Dict[str, QualityScore] = field(default_factory=dict)
    passed_exit_gate: bool = False
    exit_gate_details: Dict[str, bool] = field(default_factory=dict)

    def check_exit_gate(
        self,
        min_precision: float = 0.75,
        min_detection_delta: float = 5.0,
        max_tokens_per_call: int = 6000,
    ) -> bool:
        """Check if evaluation passes exit gate criteria.

        Exit gate criteria (LABEL-12):
        - Label precision >= 0.75 (75%)
        - Detection delta >= +5%
        - Token budget per call <= 6000

        Args:
            min_precision: Minimum precision required (default 0.75)
            min_detection_delta: Minimum detection improvement % (default 5.0)
            max_tokens_per_call: Maximum tokens per labeling call (default 6000)

        Returns:
            True if all criteria pass
        """
        # Handle infinite delta (baseline was 0)
        delta = self.detection_metrics.detection_delta
        delta_met = delta >= min_detection_delta if delta != float('inf') else True

        self.exit_gate_details = {
            "precision_met": self.precision_metrics.precision >= min_precision,
            "detection_delta_met": delta_met,
            "token_budget_met": self.token_metrics.max_tokens_single_call <= max_tokens_per_call,
        }
        self.passed_exit_gate = all(self.exit_gate_details.values())
        return self.passed_exit_gate

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of full report
        """
        return {
            "precision": self.precision_metrics.to_dict(),
            "detection": self.detection_metrics.to_dict(),
            "tokens": self.token_metrics.to_dict(),
            "exit_gate": {
                "passed": self.passed_exit_gate,
                "details": self.exit_gate_details,
            },
        }

    def summary(self) -> str:
        """Generate human-readable summary.

        Returns:
            Summary string for logging/display
        """
        lines = [
            "=== Evaluation Report ===",
            f"Precision: {self.precision_metrics.precision:.2%}",
            f"Recall: {self.precision_metrics.recall:.2%}",
            f"F1 Score: {self.precision_metrics.f1_score:.2%}",
            f"Detection Delta: {self.detection_metrics.detection_delta:+.1f}%",
            f"Total Tokens: {self.token_metrics.total_tokens:,}",
            f"Exit Gate: {'PASS' if self.passed_exit_gate else 'FAIL'}",
        ]
        return "\n".join(lines)


class LabelEvaluator:
    """Evaluates label quality against ground truth.

    The evaluator compares predicted labels against a ground truth
    overlay to calculate precision, recall, and F1 metrics.

    Usage:
        ground_truth = load_all_ground_truth()
        evaluator = LabelEvaluator(ground_truth)
        report = evaluator.evaluate(predicted_overlay, token_metrics)
        print(f"Precision: {report.precision_metrics.precision:.2%}")
    """

    def __init__(self, ground_truth: LabelOverlay):
        """Initialize evaluator.

        Args:
            ground_truth: Ground truth labels to compare against
        """
        self.ground_truth = ground_truth
        self.validator = LabelValidator()

    def evaluate(
        self,
        predicted: LabelOverlay,
        token_metrics: Optional[TokenMetrics] = None,
        baseline_findings: Optional[int] = None,
        label_findings: Optional[int] = None,
    ) -> EvaluationReport:
        """Evaluate predicted labels against ground truth.

        Args:
            predicted: Predicted labels from labeler
            token_metrics: Optional token usage metrics
            baseline_findings: Findings without labels (for delta)
            label_findings: Findings with labels (for delta)

        Returns:
            EvaluationReport with all metrics
        """
        report = EvaluationReport()

        # Calculate precision metrics
        report.precision_metrics = self._calculate_precision(predicted)

        # Calculate detection delta if provided
        if baseline_findings is not None and label_findings is not None:
            report.detection_metrics = self._calculate_detection(
                baseline_findings, label_findings
            )

        # Add token metrics
        if token_metrics:
            report.token_metrics = token_metrics

        # Calculate quality scores per function using validator
        for func_id, label_set in predicted.labels.items():
            # Create a mini-overlay for this function
            mini_overlay = LabelOverlay()
            for label in label_set.labels:
                mini_overlay.add_label(func_id, label)
            report.quality_scores[func_id] = self.validator.score_labels(mini_overlay)

        # Check exit gate
        report.check_exit_gate()

        return report

    def _calculate_precision(self, predicted: LabelOverlay) -> PrecisionMetrics:
        """Calculate precision metrics against ground truth.

        Args:
            predicted: Predicted labels

        Returns:
            PrecisionMetrics with TP, FP, FN counts
        """
        metrics = PrecisionMetrics()

        # Get all function IDs from both overlays
        all_funcs = set(self.ground_truth.labels.keys()) | set(predicted.labels.keys())

        for func_id in all_funcs:
            gt_labels = self.ground_truth.get_labels(func_id)
            pred_labels = predicted.get_labels(func_id)

            gt_label_ids = {l.label_id for l in gt_labels.labels}
            pred_label_ids = {l.label_id for l in pred_labels.labels}

            # True positives: in both GT and predicted
            tp = gt_label_ids & pred_label_ids
            metrics.true_positives += len(tp)

            # False positives: in predicted but not GT
            fp = pred_label_ids - gt_label_ids
            metrics.false_positives += len(fp)

            # False negatives: in GT but not predicted
            fn = gt_label_ids - pred_label_ids
            metrics.false_negatives += len(fn)

        metrics.total_predicted = sum(len(ls.labels) for ls in predicted.labels.values())
        metrics.total_ground_truth = sum(len(ls.labels) for ls in self.ground_truth.labels.values())

        return metrics

    def _calculate_detection(
        self,
        baseline: int,
        with_labels: int,
    ) -> DetectionMetrics:
        """Calculate detection improvement metrics.

        Args:
            baseline: Findings without labels
            with_labels: Findings with labels

        Returns:
            DetectionMetrics with delta calculation
        """
        metrics = DetectionMetrics()
        metrics.baseline_findings = baseline
        metrics.label_findings = with_labels
        metrics.new_findings = max(0, with_labels - baseline)
        metrics.lost_findings = max(0, baseline - with_labels)
        return metrics

    def evaluate_by_category(
        self,
        predicted: LabelOverlay,
    ) -> Dict[str, PrecisionMetrics]:
        """Evaluate precision per label category.

        Args:
            predicted: Predicted labels

        Returns:
            Dict mapping category to precision metrics
        """
        category_metrics: Dict[str, PrecisionMetrics] = {}

        # Get all function IDs
        all_funcs = set(self.ground_truth.labels.keys()) | set(predicted.labels.keys())

        for func_id in all_funcs:
            gt_labels = self.ground_truth.get_labels(func_id)
            pred_labels = predicted.get_labels(func_id)

            # Group by category
            gt_by_cat: Dict[str, Set[str]] = {}
            for label in gt_labels.labels:
                cat = label.category
                if cat not in gt_by_cat:
                    gt_by_cat[cat] = set()
                gt_by_cat[cat].add(label.label_id)

            pred_by_cat: Dict[str, Set[str]] = {}
            for label in pred_labels.labels:
                cat = label.category
                if cat not in pred_by_cat:
                    pred_by_cat[cat] = set()
                pred_by_cat[cat].add(label.label_id)

            # Calculate metrics per category
            all_cats = set(gt_by_cat.keys()) | set(pred_by_cat.keys())
            for cat in all_cats:
                if cat not in category_metrics:
                    category_metrics[cat] = PrecisionMetrics()

                gt_ids = gt_by_cat.get(cat, set())
                pred_ids = pred_by_cat.get(cat, set())

                category_metrics[cat].true_positives += len(gt_ids & pred_ids)
                category_metrics[cat].false_positives += len(pred_ids - gt_ids)
                category_metrics[cat].false_negatives += len(gt_ids - pred_ids)

        return category_metrics


def run_evaluation(
    predicted_overlay: LabelOverlay,
    ground_truth_overlay: LabelOverlay,
    token_metrics: Optional[TokenMetrics] = None,
) -> EvaluationReport:
    """Convenience function to run evaluation.

    Args:
        predicted_overlay: Labels from labeler
        ground_truth_overlay: Known-correct labels
        token_metrics: Optional token usage

    Returns:
        EvaluationReport with all metrics
    """
    evaluator = LabelEvaluator(ground_truth_overlay)
    return evaluator.evaluate(predicted_overlay, token_metrics)


def compare_overlays(
    overlay_a: LabelOverlay,
    overlay_b: LabelOverlay,
) -> Dict[str, Any]:
    """Compare two overlays for differences.

    Args:
        overlay_a: First overlay
        overlay_b: Second overlay

    Returns:
        Dictionary with comparison results
    """
    all_funcs = set(overlay_a.labels.keys()) | set(overlay_b.labels.keys())

    only_in_a: List[str] = []
    only_in_b: List[str] = []
    different: List[str] = []
    same: List[str] = []

    for func_id in all_funcs:
        labels_a = {l.label_id for l in overlay_a.get_labels(func_id).labels}
        labels_b = {l.label_id for l in overlay_b.get_labels(func_id).labels}

        if labels_a == labels_b:
            same.append(func_id)
        elif not labels_b:
            only_in_a.append(func_id)
        elif not labels_a:
            only_in_b.append(func_id)
        else:
            different.append(func_id)

    return {
        "same": same,
        "only_in_a": only_in_a,
        "only_in_b": only_in_b,
        "different": different,
        "total_a": len(overlay_a.labels),
        "total_b": len(overlay_b.labels),
    }


__all__ = [
    "PrecisionMetrics",
    "DetectionMetrics",
    "TokenMetrics",
    "EvaluationReport",
    "LabelEvaluator",
    "run_evaluation",
    "compare_overlays",
]
