"""Phase 14: Tier B Pattern Integration.

This module provides Tier B (LLM/semantic) pattern matching using risk tags.
Tier B complements deterministic Tier A detection with semantic context.

Aggregation Modes:
- tier_a_only: Only Tier A results matter (default, fully deterministic)
- tier_a_required: Tier A must match, Tier B provides additional context
- voting: Both tiers vote, configurable threshold for match

"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node
from alphaswarm_sol.taxonomy.tags import RiskCategory, RiskTag, get_tag_category
from alphaswarm_sol.taxonomy.storage import TagStore, NodeTags
from alphaswarm_sol.taxonomy.assignment import TagAssigner, TagAssignment


class AggregationMode(str, Enum):
    """Aggregation modes for combining Tier A and Tier B results."""
    TIER_A_ONLY = "tier_a_only"
    TIER_A_REQUIRED = "tier_a_required"
    VOTING = "voting"


class ConfidenceLevel(str, Enum):
    """Confidence level thresholds for tag matching."""
    LOW = "low"           # >= 0.3
    MEDIUM = "medium"     # >= 0.5
    HIGH = "high"         # >= 0.7
    VERY_HIGH = "very_high"  # >= 0.9

    def threshold(self) -> float:
        """Get numeric threshold for confidence level."""
        return {
            ConfidenceLevel.LOW: 0.3,
            ConfidenceLevel.MEDIUM: 0.5,
            ConfidenceLevel.HIGH: 0.7,
            ConfidenceLevel.VERY_HIGH: 0.9,
        }[self]


@dataclass
class TierBCondition:
    """A Tier B condition based on risk tags.

    Attributes:
        type: Condition type (has_risk_tag, has_any_risk_tag, has_category)
        value: Tag, tags, or category value
        min_confidence: Minimum confidence level for match
    """
    type: str  # "has_risk_tag", "has_any_risk_tag", "has_all_risk_tags", "has_category"
    value: Any  # RiskTag, List[RiskTag], or RiskCategory
    min_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


@dataclass
class TierBMatch:
    """Result of Tier B matching.

    Attributes:
        matched: Whether Tier B conditions matched
        matched_tags: Tags that contributed to match
        confidence: Average confidence of matched tags
        evidence: Evidence from tag assignments
    """
    matched: bool = False
    matched_tags: List[RiskTag] = field(default_factory=list)
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)


@dataclass
class TierResult:
    """Combined result from Tier A and Tier B.

    Attributes:
        tier_a_matched: Tier A match result
        tier_b_matched: Tier B match result (if applicable)
        tier_b_context: Additional context from Tier B
        final_matched: Final match after aggregation
        aggregation_mode: Mode used for aggregation
    """
    tier_a_matched: bool
    tier_b_matched: Optional[bool] = None
    tier_b_context: Optional[TierBMatch] = None
    final_matched: bool = False
    aggregation_mode: str = "tier_a_only"

    def with_tier_b_context(self, tier_b: TierBMatch) -> "TierResult":
        """Create new result with Tier B context added."""
        return TierResult(
            tier_a_matched=self.tier_a_matched,
            tier_b_matched=tier_b.matched,
            tier_b_context=tier_b,
            final_matched=self.tier_a_matched,  # Tier A is primary
            aggregation_mode=self.aggregation_mode,
        )


class TierBMatcher:
    """Matches Tier B conditions using risk tags.

    Provides semantic detection complementing deterministic Tier A.
    """

    def __init__(self, tag_store: Optional[TagStore] = None):
        """Initialize with optional pre-populated tag store.

        Args:
            tag_store: Optional tag store. If None, tags will be assigned
                       on-demand using TagAssigner.
        """
        self.tag_store = tag_store or TagStore()
        self.assigner = TagAssigner(min_confidence=0.3)

    def ensure_node_tags(self, node: Node) -> NodeTags:
        """Ensure node has tags assigned.

        Args:
            node: Node to check/assign tags

        Returns:
            NodeTags for the node
        """
        existing = self.tag_store.get_node_tags(node.id)
        if existing:
            return existing

        # Assign tags from properties and operations
        assignments = self.assigner.assign_tags(node)
        for assignment in assignments:
            self.tag_store.add_tag(node.id, assignment)

        return self.tag_store.get_node_tags(node.id) or NodeTags(node_id=node.id)

    def match_condition(
        self,
        node: Node,
        condition: TierBCondition,
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Match a single Tier B condition.

        Args:
            node: Node to check
            condition: Condition to evaluate

        Returns:
            Tuple of (matched, details)
        """
        node_tags = self.ensure_node_tags(node)
        threshold = condition.min_confidence.threshold()

        matched = False
        matched_tags: List[RiskTag] = []
        evidence: List[str] = []

        if condition.type == "has_risk_tag":
            # Single tag check
            tag = self._parse_tag(condition.value)
            if tag:
                for assignment in node_tags.assignments:
                    if assignment.tag == tag and assignment.confidence >= threshold:
                        matched = True
                        matched_tags.append(tag)
                        evidence.append(assignment.reason)
                        break

        elif condition.type == "has_any_risk_tag":
            # Any of the tags
            tags = self._parse_tags(condition.value)
            for tag in tags:
                for assignment in node_tags.assignments:
                    if assignment.tag == tag and assignment.confidence >= threshold:
                        matched = True
                        matched_tags.append(tag)
                        evidence.append(assignment.reason)
                        break
                if matched:
                    break

        elif condition.type == "has_all_risk_tags":
            # All tags required
            tags = self._parse_tags(condition.value)
            found_tags = []
            for tag in tags:
                for assignment in node_tags.assignments:
                    if assignment.tag == tag and assignment.confidence >= threshold:
                        found_tags.append(tag)
                        evidence.append(assignment.reason)
                        break
            matched = len(found_tags) == len(tags)
            matched_tags = found_tags

        elif condition.type == "has_category":
            # Any tag in category
            category = self._parse_category(condition.value)
            if category:
                for assignment in node_tags.assignments:
                    if get_tag_category(assignment.tag) == category and assignment.confidence >= threshold:
                        matched = True
                        matched_tags.append(assignment.tag)
                        evidence.append(assignment.reason)
                        break

        details = {
            "condition_type": condition.type,
            "expected": str(condition.value),
            "min_confidence": condition.min_confidence.value,
            "matched": matched,
            "matched_tags": [t.value for t in matched_tags],
            "evidence": evidence,
        }

        return matched, details

    def match_tier_b(
        self,
        node: Node,
        all_conditions: List[TierBCondition],
        any_conditions: List[TierBCondition],
        none_conditions: List[TierBCondition],
    ) -> TierBMatch:
        """Match all Tier B conditions for a node.

        Args:
            node: Node to evaluate
            all_conditions: All must match
            any_conditions: At least one must match
            none_conditions: None must match

        Returns:
            TierBMatch result
        """
        all_matched_tags: List[RiskTag] = []
        all_evidence: List[str] = []
        total_confidence = 0.0
        count = 0

        # All conditions must pass
        if all_conditions:
            for cond in all_conditions:
                matched, details = self.match_condition(node, cond)
                if not matched:
                    return TierBMatch(matched=False)
                if details:
                    all_matched_tags.extend([
                        RiskTag(t) for t in details.get("matched_tags", [])
                    ])
                    all_evidence.extend(details.get("evidence", []))

        # At least one must pass
        if any_conditions:
            any_matched = False
            for cond in any_conditions:
                matched, details = self.match_condition(node, cond)
                if matched:
                    any_matched = True
                    if details:
                        all_matched_tags.extend([
                            RiskTag(t) for t in details.get("matched_tags", [])
                        ])
                        all_evidence.extend(details.get("evidence", []))
                    break
            if not any_matched:
                return TierBMatch(matched=False)

        # None must pass
        if none_conditions:
            for cond in none_conditions:
                matched, _ = self.match_condition(node, cond)
                if matched:
                    return TierBMatch(matched=False)

        # Calculate average confidence from matched assignments
        node_tags = self.ensure_node_tags(node)
        for tag in all_matched_tags:
            for assignment in node_tags.assignments:
                if assignment.tag == tag:
                    total_confidence += assignment.confidence
                    count += 1
                    break

        avg_confidence = total_confidence / count if count > 0 else 1.0

        return TierBMatch(
            matched=True,
            matched_tags=list(set(all_matched_tags)),
            confidence=avg_confidence,
            evidence=list(set(all_evidence)),
        )

    def _parse_tag(self, value: Any) -> Optional[RiskTag]:
        """Parse a value into a RiskTag."""
        if isinstance(value, RiskTag):
            return value
        if isinstance(value, str):
            try:
                return RiskTag(value)
            except ValueError:
                return None
        return None

    def _parse_tags(self, value: Any) -> List[RiskTag]:
        """Parse a value into a list of RiskTags."""
        if isinstance(value, list):
            tags = []
            for v in value:
                tag = self._parse_tag(v)
                if tag:
                    tags.append(tag)
            return tags
        tag = self._parse_tag(value)
        return [tag] if tag else []

    def _parse_category(self, value: Any) -> Optional[RiskCategory]:
        """Parse a value into a RiskCategory."""
        if isinstance(value, RiskCategory):
            return value
        if isinstance(value, str):
            try:
                return RiskCategory(value)
            except ValueError:
                return None
        return None


def aggregate_tier_results(
    tier_a_matched: bool,
    tier_b: Optional[TierBMatch],
    mode: AggregationMode,
    voting_threshold: int = 2,
) -> TierResult:
    """Aggregate Tier A and Tier B results.

    Args:
        tier_a_matched: Whether Tier A matched
        tier_b: Tier B match result (if available)
        mode: Aggregation mode to use
        voting_threshold: Minimum tiers required for voting mode

    Returns:
        Combined TierResult
    """
    if mode == AggregationMode.TIER_A_ONLY:
        return TierResult(
            tier_a_matched=tier_a_matched,
            tier_b_matched=tier_b.matched if tier_b else None,
            tier_b_context=tier_b,
            final_matched=tier_a_matched,
            aggregation_mode=mode.value,
        )

    if mode == AggregationMode.TIER_A_REQUIRED:
        if not tier_a_matched:
            return TierResult(
                tier_a_matched=False,
                final_matched=False,
                aggregation_mode=mode.value,
            )
        # Tier A matched, add Tier B context
        return TierResult(
            tier_a_matched=True,
            tier_b_matched=tier_b.matched if tier_b else None,
            tier_b_context=tier_b,
            final_matched=True,  # Tier A is the gate
            aggregation_mode=mode.value,
        )

    if mode == AggregationMode.VOTING:
        # Count matching tiers
        matched_count = 0
        if tier_a_matched:
            matched_count += 1
        if tier_b and tier_b.matched:
            matched_count += 1

        final_matched = matched_count >= voting_threshold

        return TierResult(
            tier_a_matched=tier_a_matched,
            tier_b_matched=tier_b.matched if tier_b else None,
            tier_b_context=tier_b,
            final_matched=final_matched,
            aggregation_mode=mode.value,
        )

    # Default fallback
    return TierResult(
        tier_a_matched=tier_a_matched,
        final_matched=tier_a_matched,
        aggregation_mode=mode.value,
    )


def parse_tier_b_conditions(data: Optional[Dict[str, Any]]) -> tuple[
    List[TierBCondition], List[TierBCondition], List[TierBCondition]
]:
    """Parse Tier B conditions from pattern data.

    Args:
        data: Tier B section from pattern YAML

    Returns:
        Tuple of (all_conditions, any_conditions, none_conditions)
    """
    if not data:
        return [], [], []

    def parse_condition(item: Dict[str, Any]) -> Optional[TierBCondition]:
        """Parse a single condition."""
        # Check for condition type
        for cond_type in ["has_risk_tag", "has_any_risk_tag", "has_all_risk_tags", "has_category"]:
            if cond_type in item:
                value = item[cond_type]
                min_conf_str = item.get("min_confidence", "medium")
                try:
                    min_conf = ConfidenceLevel(min_conf_str)
                except ValueError:
                    min_conf = ConfidenceLevel.MEDIUM
                return TierBCondition(
                    type=cond_type,
                    value=value,
                    min_confidence=min_conf,
                )
        return None

    all_conds = []
    any_conds = []
    none_conds = []

    for item in data.get("all", []) or []:
        cond = parse_condition(item)
        if cond:
            all_conds.append(cond)

    for item in data.get("any", []) or []:
        cond = parse_condition(item)
        if cond:
            any_conds.append(cond)

    for item in data.get("none", []) or []:
        cond = parse_condition(item)
        if cond:
            none_conds.append(cond)

    return all_conds, any_conds, none_conds


__all__ = [
    "AggregationMode",
    "ConfidenceLevel",
    "TierBCondition",
    "TierBMatch",
    "TierResult",
    "TierBMatcher",
    "aggregate_tier_results",
    "parse_tier_b_conditions",
]
