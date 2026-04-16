"""Phase 13: Tag Assignment.

This module provides functionality for assigning risk tags to nodes
based on their properties, operations, and LLM analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from alphaswarm_sol.kg.schema import Node
from alphaswarm_sol.taxonomy.tags import (
    RiskCategory,
    RiskTag,
    get_tag_category,
    get_tag_description,
)


@dataclass
class TagAssignment:
    """Represents a tag assignment to a node.

    Attributes:
        tag: The assigned risk tag
        confidence: Confidence score (0.0 - 1.0)
        source: Source of the assignment (property, operation, llm, manual)
        reason: Reason for the assignment
        evidence: Supporting evidence
    """
    tag: RiskTag
    confidence: float = 1.0
    source: str = "property"
    reason: str = ""
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tag": self.tag.value,
            "category": get_tag_category(self.tag).value,
            "confidence": self.confidence,
            "source": self.source,
            "reason": self.reason,
            "evidence": self.evidence,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TagAssignment":
        return TagAssignment(
            tag=RiskTag(data.get("tag", "business_logic")),
            confidence=float(data.get("confidence", 1.0)),
            source=data.get("source", "property"),
            reason=data.get("reason", ""),
            evidence=data.get("evidence", []),
        )


# Property-based tag rules
PROPERTY_TAG_RULES: Dict[str, List[tuple]] = {
    # Format: property_name -> [(value, tag, confidence, reason)]
    "uses_tx_origin": [
        (True, RiskTag.TX_ORIGIN, 0.95, "Function uses tx.origin for authentication"),
    ],
    "has_access_gate": [
        (False, RiskTag.MISSING_ACCESS_CONTROL, 0.7, "No access control detected"),
    ],
    "writes_privileged_state": [
        (True, RiskTag.PRIVILEGED_WRITE, 0.8, "Writes to privileged state"),
    ],
    "state_write_after_external_call": [
        (True, RiskTag.CEI_VIOLATION, 0.9, "State written after external call"),
        (True, RiskTag.STATE_AFTER_CALL, 0.9, "CEI pattern violation"),
    ],
    "has_reentrancy_guard": [
        (False, RiskTag.EXTERNAL_CALL, 0.6, "External calls without reentrancy guard"),
    ],
    "reads_oracle_price": [
        (True, RiskTag.MANIPULATION, 0.5, "Reads oracle price (verify manipulation resistance)"),
    ],
    "has_staleness_check": [
        (False, RiskTag.STALE_PRICE, 0.8, "No staleness check on oracle price"),
    ],
    "swap_like": [
        (True, RiskTag.SANDWICH, 0.6, "Swap-like function may be sandwiched"),
    ],
    "risk_missing_slippage_parameter": [
        (True, RiskTag.SLIPPAGE, 0.85, "Missing slippage protection"),
    ],
    "risk_missing_deadline_check": [
        (True, RiskTag.NO_DEADLINE, 0.85, "Missing deadline check"),
    ],
    "has_unbounded_loop": [
        (True, RiskTag.UNBOUNDED_LOOP, 0.9, "Contains unbounded loop"),
    ],
    "external_calls_in_loop": [
        (True, RiskTag.EXTERNAL_IN_LOOP, 0.9, "External calls inside loop"),
    ],
    "uses_ecrecover": [
        (True, RiskTag.ECRECOVER_ZERO, 0.7, "Uses ecrecover (check zero address)"),
    ],
    "checks_zero_address": [
        (False, RiskTag.ECRECOVER_ZERO, 0.8, "ecrecover without zero address check"),
    ],
    "uses_block_timestamp": [
        (True, RiskTag.WEAK_RANDOMNESS, 0.5, "Uses block.timestamp (weak for randomness)"),
    ],
    "uses_delegatecall": [
        (True, RiskTag.DELEGATECALL_RISK, 0.7, "Uses delegatecall"),
    ],
    "is_initializer_like": [
        (True, RiskTag.UNPROTECTED_INIT, 0.6, "Initializer function detected"),
    ],
    "uses_erc20_transfer": [
        (True, RiskTag.NO_RETURN_CHECK, 0.5, "Uses ERC20 transfer (check return)"),
    ],
    "token_return_guarded": [
        (False, RiskTag.NO_RETURN_CHECK, 0.8, "Token transfer return not checked"),
    ],
    "is_proxy_like": [
        (True, RiskTag.UNINITIALIZED_PROXY, 0.5, "Proxy contract detected"),
    ],
    "upgradeable_without_storage_gap": [
        (True, RiskTag.NO_STORAGE_GAP, 0.85, "Upgradeable without storage gap"),
    ],
}

# Operation-based tag rules
OPERATION_TAG_RULES: Dict[str, List[tuple]] = {
    # Format: operation_name -> [(tag, confidence, reason)]
    "TRANSFERS_VALUE_OUT": [
        (RiskTag.EXTERNAL_CALL, 0.7, "Transfers value externally"),
    ],
    "CALLS_EXTERNAL": [
        (RiskTag.EXTERNAL_CALL, 0.6, "Makes external calls"),
    ],
    "CALLS_UNTRUSTED": [
        (RiskTag.UNTRUSTED_CALL, 0.85, "Calls untrusted address"),
    ],
    "MODIFIES_OWNER": [
        (RiskTag.PRIVILEGED_WRITE, 0.9, "Modifies owner"),
    ],
    "MODIFIES_ROLES": [
        (RiskTag.PRIVILEGED_WRITE, 0.85, "Modifies access roles"),
    ],
    "READS_ORACLE": [
        (RiskTag.MANIPULATION, 0.5, "Reads oracle data"),
    ],
    "PERFORMS_DIVISION": [
        (RiskTag.DIVISION_BY_ZERO, 0.4, "Performs division"),
        (RiskTag.PRECISION_LOSS, 0.3, "Division may lose precision"),
    ],
    "INITIALIZES_STATE": [
        (RiskTag.UNPROTECTED_INIT, 0.5, "Initializes state"),
    ],
}


class TagAssigner:
    """Assigns risk tags to nodes based on rules and analysis.

    Combines property-based, operation-based, and custom rules
    to assign relevant risk tags.
    """

    def __init__(
        self,
        min_confidence: float = 0.5,
        property_rules: Optional[Dict] = None,
        operation_rules: Optional[Dict] = None,
    ):
        """Initialize assigner.

        Args:
            min_confidence: Minimum confidence for tag assignment
            property_rules: Optional custom property rules
            operation_rules: Optional custom operation rules
        """
        self.min_confidence = min_confidence
        self.property_rules = property_rules or PROPERTY_TAG_RULES
        self.operation_rules = operation_rules or OPERATION_TAG_RULES

    def assign_tags(self, node: Node) -> List[TagAssignment]:
        """Assign all applicable tags to a node.

        Args:
            node: Node to analyze

        Returns:
            List of tag assignments
        """
        assignments: List[TagAssignment] = []
        seen_tags: Set[RiskTag] = set()

        # Property-based assignments
        prop_assignments = self._assign_from_properties(node)
        for assignment in prop_assignments:
            if assignment.tag not in seen_tags and assignment.confidence >= self.min_confidence:
                assignments.append(assignment)
                seen_tags.add(assignment.tag)

        # Operation-based assignments
        op_assignments = self._assign_from_operations(node)
        for assignment in op_assignments:
            if assignment.tag not in seen_tags and assignment.confidence >= self.min_confidence:
                assignments.append(assignment)
                seen_tags.add(assignment.tag)

        # Combined analysis (higher confidence when multiple signals)
        assignments = self._boost_combined_signals(assignments)

        # Sort by confidence
        assignments.sort(key=lambda a: a.confidence, reverse=True)
        return assignments

    def _assign_from_properties(self, node: Node) -> List[TagAssignment]:
        """Assign tags based on node properties."""
        assignments: List[TagAssignment] = []

        for prop_name, rules in self.property_rules.items():
            prop_value = node.properties.get(prop_name)
            if prop_value is None:
                continue

            for rule in rules:
                expected_value, tag, confidence, reason = rule
                if prop_value == expected_value:
                    assignments.append(TagAssignment(
                        tag=tag,
                        confidence=confidence,
                        source="property",
                        reason=reason,
                        evidence=[f"{prop_name}={prop_value}"],
                    ))

        return assignments

    def _assign_from_operations(self, node: Node) -> List[TagAssignment]:
        """Assign tags based on semantic operations."""
        assignments: List[TagAssignment] = []
        operations = node.properties.get("semantic_ops", [])

        for op in operations:
            rules = self.operation_rules.get(op, [])
            for rule in rules:
                tag, confidence, reason = rule
                assignments.append(TagAssignment(
                    tag=tag,
                    confidence=confidence,
                    source="operation",
                    reason=reason,
                    evidence=[f"operation:{op}"],
                ))

        return assignments

    def _boost_combined_signals(
        self, assignments: List[TagAssignment]
    ) -> List[TagAssignment]:
        """Boost confidence when multiple signals point to same issue."""
        # Group by category
        category_counts: Dict[RiskCategory, List[TagAssignment]] = {}
        for assignment in assignments:
            category = get_tag_category(assignment.tag)
            category_counts.setdefault(category, []).append(assignment)

        # Boost if multiple tags in same category
        boosted: List[TagAssignment] = []
        for assignment in assignments:
            category = get_tag_category(assignment.tag)
            count = len(category_counts.get(category, []))
            if count > 1:
                # Boost confidence (max 0.95)
                boost = min(0.1 * (count - 1), 0.2)
                new_confidence = min(assignment.confidence + boost, 0.95)
                boosted.append(TagAssignment(
                    tag=assignment.tag,
                    confidence=new_confidence,
                    source=assignment.source,
                    reason=assignment.reason,
                    evidence=assignment.evidence + [f"boosted:{count}_signals"],
                ))
            else:
                boosted.append(assignment)

        return boosted


def assign_tags_from_properties(node: Node) -> List[TagAssignment]:
    """Assign tags based on node properties.

    Convenience function for quick property-based assignment.

    Args:
        node: Node to analyze

    Returns:
        List of tag assignments
    """
    assigner = TagAssigner()
    return assigner._assign_from_properties(node)


def assign_tags_from_operations(node: Node) -> List[TagAssignment]:
    """Assign tags based on semantic operations.

    Convenience function for quick operation-based assignment.

    Args:
        node: Node to analyze

    Returns:
        List of tag assignments
    """
    assigner = TagAssigner()
    return assigner._assign_from_operations(node)


__all__ = [
    "TagAssignment",
    "TagAssigner",
    "PROPERTY_TAG_RULES",
    "OPERATION_TAG_RULES",
    "assign_tags_from_properties",
    "assign_tags_from_operations",
]
