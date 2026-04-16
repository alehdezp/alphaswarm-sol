"""Phase 5: Tier C Label-Aware Pattern Integration.

This module provides Tier C (semantic label) pattern matching.
Tier C complements Tier A (deterministic) and Tier B (risk tags)
with semantic label conditions.

Condition Types:
- has_label: Function has a specific label
- has_any_label: Function has any of the specified labels
- has_all_labels: Function has all specified labels
- missing_label: Function is missing a specific label
- has_category: Function has any label in a category
- label_confidence: Label has minimum confidence level

Aggregation Modes:
- tier_a_only: Only Tier A results matter (default, fully deterministic)
- tier_a_required: Tier A must match, Tier B/C provide additional context
- tier_abc_all: All present tiers must match
- voting: All tiers vote, majority wins
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.kg.schema import KnowledgeGraph, Node
    from alphaswarm_sol.queries.tier_b import TierBMatch


class TierCConditionType(str, Enum):
    """Types of Tier C conditions."""

    HAS_LABEL = "has_label"
    HAS_ANY_LABEL = "has_any_label"
    HAS_ALL_LABELS = "has_all_labels"
    MISSING_LABEL = "missing_label"
    HAS_CATEGORY = "has_category"
    LABEL_CONFIDENCE = "label_confidence"


@dataclass
class TierCCondition:
    """A Tier C condition based on semantic labels.

    Attributes:
        type: Condition type
        value: Label ID(s) or category
        min_confidence: Minimum confidence for match
        context: Optional analysis context for filtering
    """

    type: TierCConditionType
    value: Any  # str, List[str], or category name
    min_confidence: str = "medium"  # "low", "medium", "high"
    context: Optional[str] = None  # For context-filtered matching

    def __post_init__(self):
        """Ensure type is enum."""
        if isinstance(self.type, str):
            self.type = TierCConditionType(self.type)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TierCCondition":
        """Create from dictionary (parsed from YAML pattern).

        Args:
            data: Dictionary with type, value, min_confidence, context

        Returns:
            TierCCondition instance
        """
        return cls(
            type=TierCConditionType(data.get("type", "has_label")),
            value=data.get("value"),
            min_confidence=data.get("min_confidence", "medium"),
            context=data.get("context"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation
        """
        result = {
            "type": self.type.value,
            "value": self.value,
            "min_confidence": self.min_confidence,
        }
        if self.context:
            result["context"] = self.context
        return result


@dataclass
class TierCMatch:
    """Result of Tier C matching.

    Attributes:
        matched: Whether conditions were satisfied
        matched_labels: Labels that contributed to match
        confidence: Average confidence of matched labels
        evidence: Evidence for the match
        missing_labels: Labels that were expected but not found
    """

    matched: bool = False
    matched_labels: List[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    missing_labels: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "matched": self.matched,
            "matched_labels": self.matched_labels,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "missing_labels": self.missing_labels,
        }


@dataclass
class TierCResult:
    """Combined result from Tier A, B, and C.

    Attributes:
        tier_a_matched: Tier A (deterministic) result
        tier_b_matched: Tier B (risk tag) result
        tier_c_matched: Tier C (label) result
        tier_c_context: Detailed Tier C match info
        final_matched: Final result after aggregation
        aggregation_mode: Mode used
    """

    tier_a_matched: bool
    tier_b_matched: Optional[bool] = None
    tier_c_matched: Optional[bool] = None
    tier_c_context: Optional[TierCMatch] = None
    final_matched: bool = False
    aggregation_mode: str = "tier_a_only"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation
        """
        result = {
            "tier_a_matched": self.tier_a_matched,
            "final_matched": self.final_matched,
            "aggregation_mode": self.aggregation_mode,
        }
        if self.tier_b_matched is not None:
            result["tier_b_matched"] = self.tier_b_matched
        if self.tier_c_matched is not None:
            result["tier_c_matched"] = self.tier_c_matched
        if self.tier_c_context:
            result["tier_c_context"] = self.tier_c_context.to_dict()
        return result


class TierCMatcher:
    """Match patterns based on semantic labels.

    Provides label-based detection complementing deterministic Tier A
    and risk tag-based Tier B.

    Usage:
        from alphaswarm_sol.labels import LabelOverlay
        from alphaswarm_sol.queries.tier_c import TierCMatcher, TierCCondition, TierCConditionType

        matcher = TierCMatcher(label_overlay)

        # Check conditions
        conditions = [
            TierCCondition(TierCConditionType.HAS_LABEL, "access_control.owner_only"),
            TierCCondition(TierCConditionType.MISSING_LABEL, "access_control.role_based"),
        ]
        result = matcher.match(node_id, conditions_all=conditions)

        # Pattern-level matching
        result = matcher.match_pattern(node_id, pattern_def)
    """

    def __init__(
        self,
        overlay: "LabelOverlay",
        analysis_context: Optional[str] = None,
    ):
        """Initialize matcher.

        Args:
            overlay: Label overlay to match against
            analysis_context: Optional global context for filtering
        """
        from alphaswarm_sol.labels.filter import LabelFilter
        from alphaswarm_sol.labels.schema import LabelConfidence

        self.overlay = overlay
        self.filter = LabelFilter(overlay)
        self.analysis_context = analysis_context
        self._LabelConfidence = LabelConfidence

    def match(
        self,
        node_id: str,
        conditions_all: Optional[List[TierCCondition]] = None,
        conditions_any: Optional[List[TierCCondition]] = None,
        conditions_none: Optional[List[TierCCondition]] = None,
    ) -> TierCMatch:
        """Match Tier C conditions for a node.

        Args:
            node_id: Function node ID
            conditions_all: All must match
            conditions_any: At least one must match
            conditions_none: None must match

        Returns:
            TierCMatch with result details
        """
        label_set = self.overlay.get_labels(node_id)
        result = TierCMatch()

        # Evaluate ALL conditions
        if conditions_all:
            for cond in conditions_all:
                if not self._evaluate_condition(label_set, cond, result):
                    result.matched = False
                    return result

        # Evaluate ANY conditions
        if conditions_any:
            any_matched = False
            for cond in conditions_any:
                if self._evaluate_condition(label_set, cond, result):
                    any_matched = True
                    break
            if not any_matched:
                result.matched = False
                return result

        # Evaluate NONE conditions
        if conditions_none:
            for cond in conditions_none:
                # For NONE, we want the condition to NOT match
                temp_result = TierCMatch()
                if self._evaluate_condition(label_set, cond, temp_result):
                    result.matched = False
                    result.evidence.append(
                        f"Forbidden condition matched: {cond.type.value}"
                    )
                    return result

        # All conditions passed
        result.matched = True

        # Calculate average confidence
        if result.matched_labels:
            confidences = []
            for label_id in result.matched_labels:
                label = label_set.get_label(label_id)
                if label:
                    confidences.append(self._confidence_value(label.confidence))
            result.confidence = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )

        return result

    def match_for_pattern(
        self,
        node_id: str,
        tier_c_all: List["TierCConditionSpec"],
        tier_c_any: List["TierCConditionSpec"],
        tier_c_none: List["TierCConditionSpec"],
    ) -> TierCMatch:
        """Match Tier C conditions from PatternDefinition specs.

        Converts TierCConditionSpec objects to TierCCondition for matching.

        Args:
            node_id: Function node ID
            tier_c_all: All conditions must match
            tier_c_any: At least one must match
            tier_c_none: None must match

        Returns:
            TierCMatch with result details
        """

        def to_condition(spec: "TierCConditionSpec") -> TierCCondition:
            return TierCCondition(
                type=TierCConditionType(spec.type),
                value=spec.value,
                min_confidence=spec.min_confidence,
                context=spec.context,
            )

        all_conds = [to_condition(s) for s in tier_c_all] if tier_c_all else None
        any_conds = [to_condition(s) for s in tier_c_any] if tier_c_any else None
        none_conds = [to_condition(s) for s in tier_c_none] if tier_c_none else None

        return self.match(node_id, all_conds, any_conds, none_conds)

    def _evaluate_condition(
        self,
        label_set: "LabelSet",
        condition: TierCCondition,
        result: TierCMatch,
    ) -> bool:
        """Evaluate a single condition.

        Args:
            label_set: Labels for the function
            condition: Condition to evaluate
            result: TierCMatch to update with evidence

        Returns:
            True if condition matched
        """
        from alphaswarm_sol.labels.schema import FunctionLabel

        labels = label_set.labels

        # Apply context filtering if specified
        if condition.context or self.analysis_context:
            ctx = condition.context or self.analysis_context
            filtered = self.filter.get_filtered_labels(label_set.function_id, ctx)
            labels = filtered.labels_included

        # Filter by confidence threshold
        min_conf = self._parse_confidence(condition.min_confidence)
        labels = [l for l in labels if l.confidence.threshold() >= min_conf.threshold()]

        label_ids = {l.label_id for l in labels}

        if condition.type == TierCConditionType.HAS_LABEL:
            if condition.value in label_ids:
                result.matched_labels.append(condition.value)
                result.evidence.append(f"Has label: {condition.value}")
                return True
            result.missing_labels.append(condition.value)
            return False

        elif condition.type == TierCConditionType.HAS_ANY_LABEL:
            target_labels = (
                condition.value
                if isinstance(condition.value, list)
                else [condition.value]
            )
            for label in target_labels:
                if label in label_ids:
                    result.matched_labels.append(label)
                    result.evidence.append(f"Has label: {label}")
                    return True
            result.missing_labels.extend(target_labels)
            return False

        elif condition.type == TierCConditionType.HAS_ALL_LABELS:
            target_labels = (
                condition.value
                if isinstance(condition.value, list)
                else [condition.value]
            )
            if all(label in label_ids for label in target_labels):
                result.matched_labels.extend(target_labels)
                result.evidence.append(f"Has all labels: {target_labels}")
                return True
            missing = [l for l in target_labels if l not in label_ids]
            result.missing_labels.extend(missing)
            return False

        elif condition.type == TierCConditionType.MISSING_LABEL:
            if condition.value not in label_ids:
                result.evidence.append(
                    f"Missing label (as expected): {condition.value}"
                )
                return True
            return False

        elif condition.type == TierCConditionType.HAS_CATEGORY:
            category = condition.value
            for label in labels:
                if label.category == category:
                    result.matched_labels.append(label.label_id)
                    result.evidence.append(
                        f"Has category {category}: {label.label_id}"
                    )
                    return True
            return False

        elif condition.type == TierCConditionType.LABEL_CONFIDENCE:
            # Check if a label has the specified confidence
            if isinstance(condition.value, dict):
                target_label = condition.value.get("label")
                target_confidence = condition.value.get("confidence", "medium")
            else:
                target_label = condition.value
                target_confidence = "medium"

            target_min_conf = self._parse_confidence(target_confidence)
            for label in labels:
                if label.label_id == target_label:
                    if label.confidence.threshold() >= target_min_conf.threshold():
                        result.matched_labels.append(label.label_id)
                        result.evidence.append(
                            f"Label {target_label} has >= {target_confidence} confidence"
                        )
                        return True
            return False

        return False

    def _parse_confidence(self, confidence: str) -> "LabelConfidence":
        """Parse confidence string to enum.

        Args:
            confidence: "low", "medium", or "high"

        Returns:
            LabelConfidence enum value
        """
        try:
            return self._LabelConfidence(confidence)
        except ValueError:
            return self._LabelConfidence.MEDIUM

    @staticmethod
    def _confidence_value(confidence: "LabelConfidence") -> float:
        """Get numeric value for confidence.

        Args:
            confidence: LabelConfidence enum

        Returns:
            Numeric value (0.0, 0.5, or 0.8)
        """
        return confidence.threshold()


def parse_tier_c_conditions(data: Dict[str, Any]) -> tuple:
    """Parse Tier C conditions from pattern YAML.

    Args:
        data: Pattern definition dict with tier_c_all, tier_c_any, tier_c_none

    Returns:
        Tuple of (conditions_all, conditions_any, conditions_none)
    """

    def parse_list(items: Optional[List[Dict]]) -> List[TierCCondition]:
        if not items:
            return []
        return [TierCCondition.from_dict(item) for item in items]

    return (
        parse_list(data.get("tier_c_all", [])),
        parse_list(data.get("tier_c_any", [])),
        parse_list(data.get("tier_c_none", [])),
    )


def aggregate_tier_results(
    tier_a: bool,
    tier_b: Optional["TierBMatch"] = None,
    tier_c: Optional[TierCMatch] = None,
    mode: str = "tier_a_only",
) -> TierCResult:
    """Aggregate results from all tiers.

    Modes:
    - tier_a_only: Only Tier A matters
    - tier_a_required: Tier A must match, B/C provide context
    - tier_abc_all: All present tiers must match
    - voting: Majority vote among tiers

    Args:
        tier_a: Tier A result
        tier_b: Tier B match result (optional)
        tier_c: Tier C match result (optional)
        mode: Aggregation mode

    Returns:
        TierCResult with final_matched
    """
    result = TierCResult(
        tier_a_matched=tier_a,
        tier_b_matched=tier_b.matched if tier_b else None,
        tier_c_matched=tier_c.matched if tier_c else None,
        tier_c_context=tier_c,
        aggregation_mode=mode,
    )

    if mode == "tier_a_only":
        result.final_matched = tier_a

    elif mode == "tier_a_required":
        if not tier_a:
            result.final_matched = False
        else:
            # Tier A matched, check if other tiers add context
            result.final_matched = True

    elif mode == "tier_abc_all":
        # All present tiers must match
        tiers = [tier_a]
        if tier_b is not None:
            tiers.append(tier_b.matched)
        if tier_c is not None:
            tiers.append(tier_c.matched)
        result.final_matched = all(tiers)

    elif mode == "voting":
        # Majority vote
        votes = [tier_a]
        if tier_b is not None:
            votes.append(tier_b.matched)
        if tier_c is not None:
            votes.append(tier_c.matched)
        result.final_matched = sum(votes) > len(votes) / 2

    else:
        result.final_matched = tier_a

    return result


# Type imports for type hints (avoid circular imports)
if TYPE_CHECKING:
    from alphaswarm_sol.labels.overlay import LabelOverlay
    from alphaswarm_sol.labels.schema import FunctionLabel, LabelConfidence, LabelSet
    from alphaswarm_sol.queries.patterns import TierCConditionSpec


__all__ = [
    "TierCConditionType",
    "TierCCondition",
    "TierCMatch",
    "TierCResult",
    "TierCMatcher",
    "parse_tier_c_conditions",
    "aggregate_tier_results",
]
