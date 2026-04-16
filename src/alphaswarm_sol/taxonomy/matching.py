"""Phase 13: Tag-Based Pattern Matching.

This module provides functionality for matching patterns using risk tags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from alphaswarm_sol.taxonomy.tags import (
    RiskCategory,
    RiskTag,
    get_tag_category,
    get_tags_in_category,
)
from alphaswarm_sol.taxonomy.storage import NodeTags, TagStore


class MatchOperator(str, Enum):
    """Match operators for tag patterns."""
    HAS = "has"               # Node has the tag
    NOT_HAS = "not_has"       # Node does not have the tag
    HAS_ANY = "has_any"       # Node has any of the tags
    HAS_ALL = "has_all"       # Node has all of the tags
    HAS_CATEGORY = "has_category"  # Node has any tag in category
    CONFIDENCE_GTE = "confidence_gte"  # Tag confidence >= value
    CONFIDENCE_LTE = "confidence_lte"  # Tag confidence <= value


@dataclass
class TagCondition:
    """A single condition in a tag pattern.

    Attributes:
        operator: Match operator
        tag: Tag for single-tag operations
        tags: Tags for multi-tag operations
        category: Category for category operations
        value: Value for comparison operations
    """
    operator: MatchOperator
    tag: Optional[RiskTag] = None
    tags: Optional[List[RiskTag]] = None
    category: Optional[RiskCategory] = None
    value: Optional[float] = None

    def evaluate(self, node_tags: Optional[NodeTags]) -> bool:
        """Evaluate condition against node tags.

        Args:
            node_tags: Tags assigned to a node

        Returns:
            True if condition is satisfied
        """
        if node_tags is None:
            # No tags means conditions requiring tags fail
            if self.operator == MatchOperator.NOT_HAS:
                return True
            return False

        if self.operator == MatchOperator.HAS:
            return node_tags.has_tag(self.tag) if self.tag else False

        elif self.operator == MatchOperator.NOT_HAS:
            return not node_tags.has_tag(self.tag) if self.tag else True

        elif self.operator == MatchOperator.HAS_ANY:
            if not self.tags:
                return False
            return any(node_tags.has_tag(t) for t in self.tags)

        elif self.operator == MatchOperator.HAS_ALL:
            if not self.tags:
                return False
            return all(node_tags.has_tag(t) for t in self.tags)

        elif self.operator == MatchOperator.HAS_CATEGORY:
            return node_tags.has_category(self.category) if self.category else False

        elif self.operator == MatchOperator.CONFIDENCE_GTE:
            if not self.tag or self.value is None:
                return False
            for assignment in node_tags.assignments:
                if assignment.tag == self.tag and assignment.confidence >= self.value:
                    return True
            return False

        elif self.operator == MatchOperator.CONFIDENCE_LTE:
            if not self.tag or self.value is None:
                return False
            for assignment in node_tags.assignments:
                if assignment.tag == self.tag and assignment.confidence <= self.value:
                    return True
            return False

        return False


@dataclass
class TagPattern:
    """A pattern for matching nodes by tags.

    Supports AND/OR logic through all_conditions and any_conditions.

    Attributes:
        name: Pattern name
        all_conditions: All must match (AND logic)
        any_conditions: At least one must match (OR logic)
        none_conditions: None must match (NOT logic)
    """
    name: str = ""
    all_conditions: List[TagCondition] = field(default_factory=list)
    any_conditions: List[TagCondition] = field(default_factory=list)
    none_conditions: List[TagCondition] = field(default_factory=list)

    def matches(self, node_tags: Optional[NodeTags]) -> bool:
        """Check if pattern matches node tags.

        Args:
            node_tags: Tags assigned to a node

        Returns:
            True if pattern matches
        """
        # All conditions must pass
        if self.all_conditions:
            if not all(c.evaluate(node_tags) for c in self.all_conditions):
                return False

        # At least one must pass (if any specified)
        if self.any_conditions:
            if not any(c.evaluate(node_tags) for c in self.any_conditions):
                return False

        # None must pass
        if self.none_conditions:
            if any(c.evaluate(node_tags) for c in self.none_conditions):
                return False

        return True


@dataclass
class TagMatchResult:
    """Result of a tag pattern match.

    Attributes:
        matched: Whether pattern matched
        node_id: ID of the matched node
        pattern_name: Name of the pattern
        matched_tags: Tags that contributed to the match
        confidence: Overall match confidence
        evidence: Evidence for the match
    """
    matched: bool
    node_id: str = ""
    pattern_name: str = ""
    matched_tags: List[RiskTag] = field(default_factory=list)
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "matched": self.matched,
            "node_id": self.node_id,
            "pattern_name": self.pattern_name,
            "matched_tags": [t.value for t in self.matched_tags],
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


class TagMatcher:
    """Matches nodes against tag patterns.

    Provides efficient pattern matching using tag store indexes.
    """

    def __init__(self, store: TagStore):
        """Initialize matcher with tag store.

        Args:
            store: Tag store to match against
        """
        self.store = store

    def match_pattern(
        self,
        pattern: TagPattern,
        node_id: Optional[str] = None,
    ) -> List[TagMatchResult]:
        """Match pattern against nodes.

        Args:
            pattern: Pattern to match
            node_id: Optional specific node to check

        Returns:
            List of match results
        """
        results = []

        if node_id:
            # Match against specific node
            node_tags = self.store.get_node_tags(node_id)
            result = self._match_single(pattern, node_id, node_tags)
            if result.matched:
                results.append(result)
        else:
            # Use indexes for efficient matching
            candidate_ids = self._get_candidates(pattern)
            for nid in candidate_ids:
                node_tags = self.store.get_node_tags(nid)
                result = self._match_single(pattern, nid, node_tags)
                if result.matched:
                    results.append(result)

        return results

    def _get_candidates(self, pattern: TagPattern) -> Set[str]:
        """Get candidate node IDs for pattern.

        Uses indexes to quickly find potential matches.
        """
        candidates: Optional[Set[str]] = None

        # Use all_conditions to narrow candidates
        for condition in pattern.all_conditions:
            cond_candidates = self._get_condition_candidates(condition)
            if cond_candidates is not None:
                if candidates is None:
                    candidates = cond_candidates
                else:
                    candidates &= cond_candidates

        # Use any_conditions to add candidates
        if pattern.any_conditions:
            any_candidates: Set[str] = set()
            for condition in pattern.any_conditions:
                cond_candidates = self._get_condition_candidates(condition)
                if cond_candidates:
                    any_candidates |= cond_candidates
            if candidates is None:
                candidates = any_candidates
            else:
                # Must satisfy both all and any
                candidates &= any_candidates

        # If no conditions, return all nodes
        if candidates is None:
            candidates = set(
                node_id for node_id in self.store._node_tags.keys()
            )

        return candidates

    def _get_condition_candidates(
        self,
        condition: TagCondition,
    ) -> Optional[Set[str]]:
        """Get candidates for a single condition."""
        if condition.operator == MatchOperator.HAS:
            if condition.tag:
                return set(self.store.query_by_tag(condition.tag))

        elif condition.operator == MatchOperator.HAS_ANY:
            if condition.tags:
                result: Set[str] = set()
                for tag in condition.tags:
                    result |= set(self.store.query_by_tag(tag))
                return result

        elif condition.operator == MatchOperator.HAS_ALL:
            if condition.tags:
                result = set(self.store.query_by_tag(condition.tags[0]))
                for tag in condition.tags[1:]:
                    result &= set(self.store.query_by_tag(tag))
                return result

        elif condition.operator == MatchOperator.HAS_CATEGORY:
            if condition.category:
                return set(self.store.query_by_category(condition.category))

        return None

    def _match_single(
        self,
        pattern: TagPattern,
        node_id: str,
        node_tags: Optional[NodeTags],
    ) -> TagMatchResult:
        """Match pattern against single node."""
        matched = pattern.matches(node_tags)

        if not matched:
            return TagMatchResult(matched=False, node_id=node_id)

        # Collect evidence
        matched_tags: List[RiskTag] = []
        evidence: List[str] = []
        total_confidence = 0.0
        count = 0

        if node_tags:
            for assignment in node_tags.assignments:
                # Check if this tag contributed to match
                contributed = False
                for condition in pattern.all_conditions:
                    if condition.tag == assignment.tag:
                        contributed = True
                        break
                for condition in pattern.any_conditions:
                    if condition.tag == assignment.tag:
                        contributed = True
                        break
                    if condition.tags and assignment.tag in condition.tags:
                        contributed = True
                        break

                if contributed:
                    matched_tags.append(assignment.tag)
                    evidence.append(assignment.reason)
                    total_confidence += assignment.confidence
                    count += 1

        avg_confidence = total_confidence / count if count > 0 else 1.0

        return TagMatchResult(
            matched=True,
            node_id=node_id,
            pattern_name=pattern.name,
            matched_tags=matched_tags,
            confidence=avg_confidence,
            evidence=evidence,
        )

    def find_by_tag(self, tag: RiskTag) -> List[str]:
        """Find all nodes with a specific tag.

        Args:
            tag: Tag to search for

        Returns:
            List of node IDs
        """
        return self.store.query_by_tag(tag)

    def find_by_category(self, category: RiskCategory) -> List[str]:
        """Find all nodes with any tag in category.

        Args:
            category: Category to search for

        Returns:
            List of node IDs
        """
        return self.store.query_by_category(category)

    def find_high_risk(
        self,
        min_confidence: float = 0.8,
        categories: Optional[List[RiskCategory]] = None,
    ) -> List[TagMatchResult]:
        """Find high-risk nodes.

        Args:
            min_confidence: Minimum confidence threshold
            categories: Optional categories to filter by

        Returns:
            List of match results
        """
        results = []

        for node_id, node_tags in self.store._node_tags.items():
            for assignment in node_tags.assignments:
                if assignment.confidence >= min_confidence:
                    if categories is None or get_tag_category(assignment.tag) in categories:
                        results.append(TagMatchResult(
                            matched=True,
                            node_id=node_id,
                            matched_tags=[assignment.tag],
                            confidence=assignment.confidence,
                            evidence=[assignment.reason],
                        ))
                        break  # One result per node

        # Sort by confidence
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results


# Convenience functions

def match_tag_pattern(
    store: TagStore,
    pattern: TagPattern,
) -> List[TagMatchResult]:
    """Match a tag pattern against store.

    Args:
        store: Tag store
        pattern: Pattern to match

    Returns:
        List of match results
    """
    matcher = TagMatcher(store)
    return matcher.match_pattern(pattern)


def has_risk_tag(
    store: TagStore,
    node_id: str,
    tag: RiskTag,
) -> bool:
    """Check if node has a specific risk tag.

    Args:
        store: Tag store
        node_id: Node ID
        tag: Tag to check

    Returns:
        True if node has tag
    """
    node_tags = store.get_node_tags(node_id)
    if node_tags:
        return node_tags.has_tag(tag)
    return False


# Predefined patterns for common vulnerabilities

REENTRANCY_PATTERN = TagPattern(
    name="reentrancy",
    all_conditions=[
        TagCondition(operator=MatchOperator.HAS, tag=RiskTag.CEI_VIOLATION),
    ],
    any_conditions=[
        TagCondition(operator=MatchOperator.HAS, tag=RiskTag.EXTERNAL_CALL),
        TagCondition(operator=MatchOperator.HAS, tag=RiskTag.STATE_AFTER_CALL),
    ],
)

ACCESS_CONTROL_PATTERN = TagPattern(
    name="access_control",
    any_conditions=[
        TagCondition(operator=MatchOperator.HAS, tag=RiskTag.MISSING_ACCESS_CONTROL),
        TagCondition(operator=MatchOperator.HAS, tag=RiskTag.TX_ORIGIN),
        TagCondition(operator=MatchOperator.HAS, tag=RiskTag.PRIVILEGED_WRITE),
    ],
)

ORACLE_MANIPULATION_PATTERN = TagPattern(
    name="oracle_manipulation",
    all_conditions=[
        TagCondition(operator=MatchOperator.HAS_CATEGORY, category=RiskCategory.ORACLE),
    ],
    any_conditions=[
        TagCondition(operator=MatchOperator.HAS, tag=RiskTag.STALE_PRICE),
        TagCondition(operator=MatchOperator.HAS, tag=RiskTag.SINGLE_SOURCE),
        TagCondition(operator=MatchOperator.HAS, tag=RiskTag.MANIPULATION),
    ],
)

DOS_PATTERN = TagPattern(
    name="dos",
    any_conditions=[
        TagCondition(operator=MatchOperator.HAS, tag=RiskTag.UNBOUNDED_LOOP),
        TagCondition(operator=MatchOperator.HAS, tag=RiskTag.EXTERNAL_IN_LOOP),
        TagCondition(operator=MatchOperator.HAS, tag=RiskTag.GAS_GRIEFING),
    ],
)


__all__ = [
    "MatchOperator",
    "TagCondition",
    "TagPattern",
    "TagMatchResult",
    "TagMatcher",
    "match_tag_pattern",
    "has_risk_tag",
    "REENTRANCY_PATTERN",
    "ACCESS_CONTROL_PATTERN",
    "ORACLE_MANIPULATION_PATTERN",
    "DOS_PATTERN",
]
