"""Label validation and quality scoring.

This module provides validation of labels against the taxonomy and
quality scoring for label sets. Used to ensure label integrity and
provide metrics for label quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .overlay import LabelOverlay
from .schema import FunctionLabel, LabelConfidence, LabelSet, LabelSource
from .taxonomy import (
    CORE_TAXONOMY,
    LabelCategory,
    LabelDefinition,
    get_all_label_ids,
    get_label_by_id,
    is_valid_label,
)


class ValidationStatus(str, Enum):
    """Status of a label validation check."""

    VALID = "valid"  # Label passes all checks
    INVALID_LABEL = "invalid_label"  # Label ID not in taxonomy
    MISSING_REASONING = "missing_reasoning"  # LOW confidence requires reasoning
    DUPLICATE_LABEL = "duplicate_label"  # Same label applied twice
    CONFLICTING_LABELS = "conflicting_labels"  # Mutually exclusive labels
    STALE_LABEL = "stale_label"  # Source code has changed
    INVALID_CATEGORY = "invalid_category"  # Category doesn't match label ID


@dataclass
class ValidationResult:
    """Result of validating a single label.

    Attributes:
        status: Validation status
        label: The label that was validated
        message: Human-readable validation message
        fix_suggestion: Optional suggestion for fixing the issue
    """

    status: ValidationStatus
    label: FunctionLabel
    message: str
    fix_suggestion: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Check if the validation passed."""
        return self.status == ValidationStatus.VALID

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "status": self.status.value,
            "label_id": self.label.label_id,
            "message": self.message,
            "fix_suggestion": self.fix_suggestion,
        }


@dataclass
class LabelSetValidation:
    """Result of validating a label set.

    Attributes:
        function_id: ID of the function whose labels were validated
        results: Individual validation results for each label
        has_errors: Whether any validation errors were found
        error_count: Number of validation errors
    """

    function_id: str
    results: List[ValidationResult] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if any validation errors were found."""
        return any(not r.is_valid for r in self.results)

    @property
    def error_count(self) -> int:
        """Get number of validation errors."""
        return sum(1 for r in self.results if not r.is_valid)

    @property
    def valid_count(self) -> int:
        """Get number of valid labels."""
        return sum(1 for r in self.results if r.is_valid)

    def get_errors(self) -> List[ValidationResult]:
        """Get only the error results."""
        return [r for r in self.results if not r.is_valid]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "function_id": self.function_id,
            "results": [r.to_dict() for r in self.results],
            "has_errors": self.has_errors,
            "error_count": self.error_count,
            "valid_count": self.valid_count,
        }


@dataclass
class ConfidenceDistribution:
    """Distribution of confidence levels in a label set.

    Attributes:
        high: Count of HIGH confidence labels
        medium: Count of MEDIUM confidence labels
        low: Count of LOW confidence labels
        total: Total label count
    """

    high: int = 0
    medium: int = 0
    low: int = 0

    @property
    def total(self) -> int:
        """Total label count."""
        return self.high + self.medium + self.low

    @property
    def high_ratio(self) -> float:
        """Ratio of HIGH confidence labels."""
        return self.high / self.total if self.total > 0 else 0.0

    @property
    def low_ratio(self) -> float:
        """Ratio of LOW confidence labels."""
        return self.low / self.total if self.total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
            "total": self.total,
            "high_ratio": round(self.high_ratio, 3),
            "low_ratio": round(self.low_ratio, 3),
        }


@dataclass
class QualityScore:
    """Quality metrics for a label set or overlay.

    Attributes:
        confidence_distribution: Distribution of confidence levels
        coverage_score: Percentage of categories covered (0.0-1.0)
        reasoning_completeness: Percentage of LOW confidence labels with reasoning
        overall_score: Weighted overall quality score (0.0-1.0)
    """

    confidence_distribution: ConfidenceDistribution
    coverage_score: float
    reasoning_completeness: float
    overall_score: float = 0.0

    def __post_init__(self):
        """Calculate overall score if not provided."""
        if self.overall_score == 0.0:
            self.overall_score = self._calculate_overall()

    def _calculate_overall(self) -> float:
        """Calculate weighted overall score.

        Weights:
        - High confidence ratio: 40%
        - Coverage: 30%
        - Reasoning completeness: 20%
        - Low confidence penalty: 10%
        """
        high_ratio_score = self.confidence_distribution.high_ratio * 0.4
        coverage_score = self.coverage_score * 0.3
        reasoning_score = self.reasoning_completeness * 0.2
        # Low confidence penalty (subtract from score)
        low_penalty = self.confidence_distribution.low_ratio * 0.1

        return min(1.0, max(0.0, high_ratio_score + coverage_score + reasoning_score - low_penalty))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "confidence_distribution": self.confidence_distribution.to_dict(),
            "coverage_score": round(self.coverage_score, 3),
            "reasoning_completeness": round(self.reasoning_completeness, 3),
            "overall_score": round(self.overall_score, 3),
        }


@dataclass
class PrecisionEstimate:
    """Estimated precision of label assignments.

    Attributes:
        estimated_precision: Estimated precision (0.0-1.0)
        confidence_interval: Confidence interval tuple (low, high)
        sample_size: Number of labels evaluated
        method: Method used for estimation
    """

    estimated_precision: float
    confidence_interval: Tuple[float, float]
    sample_size: int
    method: str  # "heuristic" or "ground_truth"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "estimated_precision": round(self.estimated_precision, 3),
            "confidence_interval": [round(x, 3) for x in self.confidence_interval],
            "sample_size": self.sample_size,
            "method": self.method,
        }


# Labels that conflict with each other (cannot both be true)
CONFLICTING_LABEL_PAIRS: List[Tuple[str, str]] = [
    # Access control conflicts
    ("access_control.owner_only", "access_control.no_restriction"),
    ("access_control.role_based", "access_control.no_restriction"),
    ("access_control.permissioned", "access_control.no_restriction"),
    ("access_control.owner_only", "access_control.role_based"),
    # State mutation conflicts
    ("state_mutation.writes_critical", "state_mutation.no_state_change"),
    ("state_mutation.initializes_state", "state_mutation.no_state_change"),
    # External interaction conflicts (can have external calls or not, but not both)
    ("external_interaction.calls_trusted", "external_interaction.no_external_calls"),
    ("external_interaction.calls_untrusted", "external_interaction.no_external_calls"),
    ("external_interaction.reads_oracle", "external_interaction.no_external_calls"),
    # Temporal conflicts
    ("temporal.enforces_timelock", "temporal.no_temporal_constraint"),
    ("temporal.checks_deadline", "temporal.no_temporal_constraint"),
]


class LabelValidator:
    """Validates labels against the taxonomy and quality rules.

    Provides validation for:
    - Label IDs against taxonomy
    - Reasoning requirements for LOW confidence
    - Conflicting label detection
    - Staleness detection (if source hash available)
    """

    def __init__(self, strict_reasoning: bool = True):
        """Initialize validator.

        Args:
            strict_reasoning: If True, LOW confidence labels must have reasoning
        """
        self.strict_reasoning = strict_reasoning
        self._valid_labels = set(get_all_label_ids())
        self._categories = set(cat.value for cat in LabelCategory)

    def validate_label(
        self,
        label: FunctionLabel,
        existing_labels: Optional[List[FunctionLabel]] = None,
        current_source_hash: Optional[str] = None,
    ) -> ValidationResult:
        """Validate a single label.

        Args:
            label: Label to validate
            existing_labels: Other labels on the same function (for conflict detection)
            current_source_hash: Current hash of function source (for staleness)

        Returns:
            ValidationResult with status and details
        """
        # Check if label ID is valid
        if not is_valid_label(label.label_id):
            return ValidationResult(
                status=ValidationStatus.INVALID_LABEL,
                label=label,
                message=f"Label ID '{label.label_id}' is not in the taxonomy",
                fix_suggestion=f"Use one of: {', '.join(sorted(self._valid_labels)[:5])}...",
            )

        # Check category matches label ID
        label_def = get_label_by_id(label.label_id)
        if label_def:
            expected_category = label_def.category.value
            actual_category = label.category
            if actual_category != expected_category:
                return ValidationResult(
                    status=ValidationStatus.INVALID_CATEGORY,
                    label=label,
                    message=f"Label category '{actual_category}' doesn't match expected '{expected_category}'",
                    fix_suggestion=None,
                )

        # Check reasoning requirement for LOW confidence
        if self.strict_reasoning:
            if label.confidence == LabelConfidence.LOW and not label.reasoning:
                return ValidationResult(
                    status=ValidationStatus.MISSING_REASONING,
                    label=label,
                    message="LOW confidence labels must include reasoning",
                    fix_suggestion="Add reasoning explaining why confidence is low",
                )

        # Check for staleness if hash provided
        if current_source_hash and label.source_hash:
            if label.source_hash != current_source_hash:
                return ValidationResult(
                    status=ValidationStatus.STALE_LABEL,
                    label=label,
                    message="Label source hash doesn't match current function source",
                    fix_suggestion="Re-evaluate the label with updated source code",
                )

        # Check for conflicts with existing labels
        if existing_labels:
            for existing in existing_labels:
                if self._labels_conflict(label.label_id, existing.label_id):
                    return ValidationResult(
                        status=ValidationStatus.CONFLICTING_LABELS,
                        label=label,
                        message=f"Label '{label.label_id}' conflicts with existing '{existing.label_id}'",
                        fix_suggestion="Remove one of the conflicting labels",
                    )

        # All checks passed
        return ValidationResult(
            status=ValidationStatus.VALID,
            label=label,
            message="Label is valid",
        )

    def validate_label_set(
        self,
        label_set: LabelSet,
        current_source_hash: Optional[str] = None,
    ) -> LabelSetValidation:
        """Validate all labels in a label set.

        Args:
            label_set: Label set to validate
            current_source_hash: Current hash of function source

        Returns:
            LabelSetValidation with all results
        """
        validation = LabelSetValidation(function_id=label_set.function_id)

        # Track seen labels for duplicate detection
        seen_labels: Dict[str, FunctionLabel] = {}

        for label in label_set.labels:
            # Check for duplicates
            if label.label_id in seen_labels:
                validation.results.append(
                    ValidationResult(
                        status=ValidationStatus.DUPLICATE_LABEL,
                        label=label,
                        message=f"Duplicate label '{label.label_id}' in set",
                        fix_suggestion="Remove the duplicate label",
                    )
                )
                continue

            # Validate against existing labels
            existing = list(seen_labels.values())
            result = self.validate_label(label, existing, current_source_hash)
            validation.results.append(result)

            if result.is_valid:
                seen_labels[label.label_id] = label

        return validation

    def validate_overlay(
        self,
        overlay: LabelOverlay,
        source_hashes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, LabelSetValidation]:
        """Validate all labels in an overlay.

        Args:
            overlay: Overlay to validate
            source_hashes: Mapping from function_id to current source hash

        Returns:
            Dict mapping function_id to validation results
        """
        results: Dict[str, LabelSetValidation] = {}
        source_hashes = source_hashes or {}

        for function_id, label_set in overlay.labels.items():
            current_hash = source_hashes.get(function_id)
            results[function_id] = self.validate_label_set(label_set, current_hash)

        return results

    def score_labels(
        self,
        overlay: LabelOverlay,
        function_count: Optional[int] = None,
    ) -> QualityScore:
        """Calculate quality score for label overlay.

        Args:
            overlay: Overlay to score
            function_count: Total number of functions (for coverage calculation)

        Returns:
            QualityScore with metrics
        """
        # Calculate confidence distribution
        distribution = ConfidenceDistribution()
        low_with_reasoning = 0
        low_count = 0
        categories_seen: set = set()

        for label_set in overlay.labels.values():
            for label in label_set.labels:
                # Count confidence levels
                if label.confidence == LabelConfidence.HIGH:
                    distribution.high += 1
                elif label.confidence == LabelConfidence.MEDIUM:
                    distribution.medium += 1
                else:
                    distribution.low += 1
                    low_count += 1
                    if label.reasoning:
                        low_with_reasoning += 1

                # Track categories
                categories_seen.add(label.category)

        # Calculate coverage score
        total_categories = len(LabelCategory)
        coverage = len(categories_seen) / total_categories if total_categories > 0 else 0.0

        # Alternatively use function coverage if function_count provided
        if function_count and function_count > 0:
            function_coverage = len(overlay.labels) / function_count
            # Blend category coverage with function coverage
            coverage = (coverage * 0.5) + (function_coverage * 0.5)

        # Calculate reasoning completeness
        reasoning_completeness = low_with_reasoning / low_count if low_count > 0 else 1.0

        return QualityScore(
            confidence_distribution=distribution,
            coverage_score=coverage,
            reasoning_completeness=reasoning_completeness,
        )

    def get_precision_estimate(
        self,
        overlay: LabelOverlay,
        ground_truth: Optional[Dict[str, List[str]]] = None,
    ) -> PrecisionEstimate:
        """Estimate precision of label assignments.

        If ground truth is provided, calculates actual precision.
        Otherwise, uses heuristic based on confidence distribution.

        Args:
            overlay: Overlay to evaluate
            ground_truth: Optional mapping from function_id to correct label IDs

        Returns:
            PrecisionEstimate with precision and confidence interval
        """
        if ground_truth:
            return self._calculate_ground_truth_precision(overlay, ground_truth)
        else:
            return self._estimate_heuristic_precision(overlay)

    def _calculate_ground_truth_precision(
        self,
        overlay: LabelOverlay,
        ground_truth: Dict[str, List[str]],
    ) -> PrecisionEstimate:
        """Calculate precision using ground truth labels.

        Args:
            overlay: Overlay with predicted labels
            ground_truth: Mapping from function_id to correct label IDs

        Returns:
            PrecisionEstimate based on ground truth comparison
        """
        correct = 0
        total = 0

        for function_id, label_set in overlay.labels.items():
            true_labels = set(ground_truth.get(function_id, []))

            for label in label_set.labels:
                total += 1
                if label.label_id in true_labels:
                    correct += 1

        precision = correct / total if total > 0 else 0.0

        # Wilson score confidence interval for binomial proportion
        # Simplified version
        if total > 0:
            import math

            z = 1.96  # 95% confidence
            p = precision
            n = total
            denominator = 1 + z * z / n
            center = (p + z * z / (2 * n)) / denominator
            margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denominator
            ci_low = max(0.0, center - margin)
            ci_high = min(1.0, center + margin)
        else:
            ci_low, ci_high = 0.0, 1.0

        return PrecisionEstimate(
            estimated_precision=precision,
            confidence_interval=(ci_low, ci_high),
            sample_size=total,
            method="ground_truth",
        )

    def _estimate_heuristic_precision(
        self,
        overlay: LabelOverlay,
    ) -> PrecisionEstimate:
        """Estimate precision using heuristics based on confidence.

        Heuristic assumptions:
        - HIGH confidence labels: ~95% precision
        - MEDIUM confidence labels: ~75% precision
        - LOW confidence labels: ~50% precision

        Args:
            overlay: Overlay to evaluate

        Returns:
            PrecisionEstimate based on heuristics
        """
        high_count = 0
        medium_count = 0
        low_count = 0

        for label_set in overlay.labels.values():
            for label in label_set.labels:
                if label.confidence == LabelConfidence.HIGH:
                    high_count += 1
                elif label.confidence == LabelConfidence.MEDIUM:
                    medium_count += 1
                else:
                    low_count += 1

        total = high_count + medium_count + low_count
        if total == 0:
            return PrecisionEstimate(
                estimated_precision=0.0,
                confidence_interval=(0.0, 1.0),
                sample_size=0,
                method="heuristic",
            )

        # Weighted average based on assumed precision per confidence level
        weighted_precision = (
            (high_count * 0.95) + (medium_count * 0.75) + (low_count * 0.50)
        ) / total

        # Confidence interval widens with more low-confidence labels
        low_ratio = low_count / total
        margin = 0.1 + (low_ratio * 0.15)  # 10-25% margin

        return PrecisionEstimate(
            estimated_precision=weighted_precision,
            confidence_interval=(
                max(0.0, weighted_precision - margin),
                min(1.0, weighted_precision + margin),
            ),
            sample_size=total,
            method="heuristic",
        )

    def _labels_conflict(self, label1: str, label2: str) -> bool:
        """Check if two labels conflict with each other.

        Args:
            label1: First label ID
            label2: Second label ID

        Returns:
            True if labels conflict, False otherwise
        """
        for pair in CONFLICTING_LABEL_PAIRS:
            if (label1 == pair[0] and label2 == pair[1]) or (
                label1 == pair[1] and label2 == pair[0]
            ):
                return True
        return False


def validate_labels(
    labels: List[FunctionLabel],
    strict_reasoning: bool = True,
) -> List[ValidationResult]:
    """Convenience function to validate a list of labels.

    Args:
        labels: Labels to validate
        strict_reasoning: If True, LOW confidence requires reasoning

    Returns:
        List of validation results
    """
    validator = LabelValidator(strict_reasoning=strict_reasoning)
    results = []
    seen: List[FunctionLabel] = []

    for label in labels:
        result = validator.validate_label(label, seen)
        results.append(result)
        if result.is_valid:
            seen.append(label)

    return results


__all__ = [
    "ValidationStatus",
    "ValidationResult",
    "LabelSetValidation",
    "ConfidenceDistribution",
    "QualityScore",
    "PrecisionEstimate",
    "CONFLICTING_LABEL_PAIRS",
    "LabelValidator",
    "validate_labels",
]
