"""Context-filtered label retrieval.

This module provides context-aware label filtering to prevent
irrelevant labels from polluting LLM context. For example, when
analyzing reentrancy, access_control labels may not be relevant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .overlay import LabelOverlay
from .schema import FunctionLabel, LabelConfidence, LabelSet
from .taxonomy import LabelCategory


# Mapping from analysis context to relevant label categories
# Context names align with vulnerability patterns and security analysis focuses
CONTEXT_TO_CATEGORIES: Dict[str, Set[str]] = {
    # Reentrancy analysis: external calls, value handling, state mutation
    "reentrancy": {
        LabelCategory.EXTERNAL_INTERACTION.value,
        LabelCategory.VALUE_HANDLING.value,
        LabelCategory.STATE_MUTATION.value,
    },
    # Access control analysis: access restrictions, state mutations
    "access_control": {
        LabelCategory.ACCESS_CONTROL.value,
        LabelCategory.STATE_MUTATION.value,
    },
    # Oracle manipulation: external interactions (oracles), value handling
    "oracle_manipulation": {
        LabelCategory.EXTERNAL_INTERACTION.value,
        LabelCategory.VALUE_HANDLING.value,
        LabelCategory.INVARIANTS.value,
    },
    # Price oracle analysis (alias for oracle_manipulation)
    "price_oracle": {
        LabelCategory.EXTERNAL_INTERACTION.value,
        LabelCategory.VALUE_HANDLING.value,
        LabelCategory.INVARIANTS.value,
    },
    # Flash loan attacks: external calls, value handling, state mutation
    "flash_loan": {
        LabelCategory.EXTERNAL_INTERACTION.value,
        LabelCategory.VALUE_HANDLING.value,
        LabelCategory.STATE_MUTATION.value,
        LabelCategory.INVARIANTS.value,
    },
    # Frontrunning/MEV: temporal constraints, value handling
    "frontrunning": {
        LabelCategory.TEMPORAL.value,
        LabelCategory.VALUE_HANDLING.value,
        LabelCategory.EXTERNAL_INTERACTION.value,
    },
    # MEV (alias for frontrunning)
    "mev": {
        LabelCategory.TEMPORAL.value,
        LabelCategory.VALUE_HANDLING.value,
        LabelCategory.EXTERNAL_INTERACTION.value,
    },
    # Privilege escalation: access control, state mutation
    "privilege_escalation": {
        LabelCategory.ACCESS_CONTROL.value,
        LabelCategory.STATE_MUTATION.value,
    },
    # Denial of service: external calls, invariants
    "dos": {
        LabelCategory.EXTERNAL_INTERACTION.value,
        LabelCategory.INVARIANTS.value,
        LabelCategory.VALUE_HANDLING.value,
    },
    # Integer overflow/underflow: value handling, invariants
    "integer_overflow": {
        LabelCategory.VALUE_HANDLING.value,
        LabelCategory.INVARIANTS.value,
    },
    # Initialization: state mutation, access control
    "initialization": {
        LabelCategory.STATE_MUTATION.value,
        LabelCategory.ACCESS_CONTROL.value,
    },
    # Balance manipulation: value handling, invariants
    "balance_manipulation": {
        LabelCategory.VALUE_HANDLING.value,
        LabelCategory.INVARIANTS.value,
        LabelCategory.STATE_MUTATION.value,
    },
    # Token approval: access control, value handling
    "token_approval": {
        LabelCategory.ACCESS_CONTROL.value,
        LabelCategory.VALUE_HANDLING.value,
    },
    # Delegate call: external interaction, state mutation
    "delegatecall": {
        LabelCategory.EXTERNAL_INTERACTION.value,
        LabelCategory.STATE_MUTATION.value,
        LabelCategory.ACCESS_CONTROL.value,
    },
    # General security (all categories)
    "general": {
        cat.value for cat in LabelCategory
    },
    # All categories (explicit alias)
    "all": {
        cat.value for cat in LabelCategory
    },
}


@dataclass
class FilteredLabels:
    """Result of filtering labels for a context.

    Attributes:
        function_id: ID of the function
        labels_included: Labels relevant to the context
        labels_filtered_out: Labels excluded from context
        context: The analysis context used for filtering
    """

    function_id: str
    labels_included: List[FunctionLabel] = field(default_factory=list)
    labels_filtered_out: List[FunctionLabel] = field(default_factory=list)
    context: str = ""

    @property
    def included_count(self) -> int:
        """Number of included labels."""
        return len(self.labels_included)

    @property
    def filtered_out_count(self) -> int:
        """Number of filtered out labels."""
        return len(self.labels_filtered_out)

    @property
    def total_count(self) -> int:
        """Total labels before filtering."""
        return self.included_count + self.filtered_out_count

    @property
    def filter_ratio(self) -> float:
        """Ratio of labels filtered out (0.0 = none, 1.0 = all)."""
        if self.total_count == 0:
            return 0.0
        return self.filtered_out_count / self.total_count

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "function_id": self.function_id,
            "context": self.context,
            "labels_included": [l.to_dict() for l in self.labels_included],
            "labels_filtered_out": [l.to_dict() for l in self.labels_filtered_out],
            "included_count": self.included_count,
            "filtered_out_count": self.filtered_out_count,
        }


class LabelFilter:
    """Filter labels by analysis context.

    Provides context-aware label retrieval to prevent irrelevant
    labels from polluting LLM context windows.

    Example:
        overlay = LabelOverlay()
        overlay.add_label("fn1", FunctionLabel("access_control.owner_only", ...))
        overlay.add_label("fn1", FunctionLabel("external_interaction.calls_untrusted", ...))

        filter = LabelFilter(overlay)
        result = filter.get_filtered_labels("fn1", "reentrancy")
        # result.labels_included contains calls_untrusted (relevant)
        # result.labels_filtered_out contains owner_only (not relevant)
    """

    def __init__(
        self,
        overlay: LabelOverlay,
        default_min_confidence: LabelConfidence = LabelConfidence.MEDIUM,
    ):
        """Initialize filter.

        Args:
            overlay: Label overlay to filter
            default_min_confidence: Default minimum confidence threshold
        """
        self.overlay = overlay
        self.default_min_confidence = default_min_confidence

    def get_filtered_labels(
        self,
        function_id: str,
        context: str,
        min_confidence: Optional[LabelConfidence] = None,
    ) -> FilteredLabels:
        """Get labels filtered by analysis context.

        Args:
            function_id: Function ID to get labels for
            context: Analysis context (e.g., "reentrancy", "access_control")
            min_confidence: Minimum confidence threshold (uses default if None)

        Returns:
            FilteredLabels with included and excluded labels
        """
        min_conf = min_confidence or self.default_min_confidence
        relevant_categories = get_relevant_categories(context)

        result = FilteredLabels(
            function_id=function_id,
            context=context,
        )

        label_set = self.overlay.get_labels(function_id)
        for label in label_set.labels:
            # Apply confidence threshold
            if label.confidence.threshold() < min_conf.threshold():
                result.labels_filtered_out.append(label)
                continue

            # Apply category filter
            if label.category in relevant_categories:
                result.labels_included.append(label)
            else:
                result.labels_filtered_out.append(label)

        return result

    def get_labels_for_pattern(
        self,
        function_id: str,
        pattern_id: str,
        min_confidence: Optional[LabelConfidence] = None,
    ) -> FilteredLabels:
        """Get labels filtered for a specific pattern.

        Maps pattern IDs to contexts and filters accordingly.

        Args:
            function_id: Function ID to get labels for
            pattern_id: Pattern ID (e.g., "reentrancy-classic", "access-control-weak")
            min_confidence: Minimum confidence threshold

        Returns:
            FilteredLabels with included and excluded labels
        """
        # Map pattern ID to context
        context = self._pattern_to_context(pattern_id)
        return self.get_filtered_labels(function_id, context, min_confidence)

    def format_labels_for_llm(
        self,
        function_id: str,
        context: str,
        include_reasoning: bool = True,
        include_filtered_summary: bool = False,
    ) -> str:
        """Format labels as text for LLM context.

        Args:
            function_id: Function ID to get labels for
            context: Analysis context
            include_reasoning: Whether to include reasoning for labels
            include_filtered_summary: Whether to note what was filtered

        Returns:
            Formatted string for LLM context
        """
        filtered = self.get_filtered_labels(function_id, context)

        if not filtered.labels_included:
            if include_filtered_summary and filtered.labels_filtered_out:
                return f"No relevant labels for {context} analysis ({filtered.filtered_out_count} labels filtered out as not relevant)"
            return "No relevant labels"

        lines = [f"Labels for {context} analysis:"]
        for label in filtered.labels_included:
            line = f"- {label.label_id} ({label.confidence.value})"
            if include_reasoning and label.reasoning:
                line += f": {label.reasoning}"
            lines.append(line)

        if include_filtered_summary and filtered.labels_filtered_out:
            lines.append(f"\n({filtered.filtered_out_count} additional labels filtered as not relevant to {context})")

        return "\n".join(lines)

    def get_functions_by_label_in_context(
        self,
        label_id: str,
        context: str,
        min_confidence: Optional[LabelConfidence] = None,
    ) -> List[str]:
        """Find functions with a label that's relevant to the context.

        Only returns functions where the label is both present AND
        relevant to the specified context.

        Args:
            label_id: Label ID to search for
            context: Analysis context for relevance filtering
            min_confidence: Minimum confidence threshold

        Returns:
            List of function IDs with the relevant label
        """
        min_conf = min_confidence or self.default_min_confidence
        relevant_categories = get_relevant_categories(context)

        # Extract category from label_id
        label_category = label_id.split(".")[0] if "." in label_id else label_id

        # Check if this label is relevant to the context
        if label_category not in relevant_categories:
            return []

        # Get functions with this label
        return self.overlay.get_functions_with_label(label_id, min_conf)

    def get_all_filtered_labels(
        self,
        context: str,
        min_confidence: Optional[LabelConfidence] = None,
    ) -> Dict[str, FilteredLabels]:
        """Get filtered labels for all functions in the overlay.

        Args:
            context: Analysis context
            min_confidence: Minimum confidence threshold

        Returns:
            Dict mapping function_id to FilteredLabels
        """
        results: Dict[str, FilteredLabels] = {}
        for function_id in self.overlay.get_all_functions():
            results[function_id] = self.get_filtered_labels(
                function_id, context, min_confidence
            )
        return results

    def get_context_statistics(
        self,
        context: str,
    ) -> Dict[str, Any]:
        """Get statistics about labels in a context.

        Args:
            context: Analysis context

        Returns:
            Dictionary with statistics
        """
        all_filtered = self.get_all_filtered_labels(context)

        total_included = sum(f.included_count for f in all_filtered.values())
        total_filtered = sum(f.filtered_out_count for f in all_filtered.values())
        functions_with_relevant = sum(
            1 for f in all_filtered.values() if f.included_count > 0
        )

        return {
            "context": context,
            "functions_analyzed": len(all_filtered),
            "functions_with_relevant_labels": functions_with_relevant,
            "total_labels_included": total_included,
            "total_labels_filtered_out": total_filtered,
            "average_filter_ratio": (
                total_filtered / (total_included + total_filtered)
                if (total_included + total_filtered) > 0
                else 0.0
            ),
            "relevant_categories": list(get_relevant_categories(context)),
        }

    def _pattern_to_context(self, pattern_id: str) -> str:
        """Map pattern ID to analysis context.

        Args:
            pattern_id: Pattern ID (e.g., "reentrancy-classic")

        Returns:
            Context string
        """
        pattern_lower = pattern_id.lower()

        # Pattern to context mapping
        pattern_context_map = {
            "reentrancy": "reentrancy",
            "access": "access_control",
            "oracle": "oracle_manipulation",
            "price": "price_oracle",
            "flash": "flash_loan",
            "front": "frontrunning",
            "mev": "mev",
            "privilege": "privilege_escalation",
            "dos": "dos",
            "denial": "dos",
            "overflow": "integer_overflow",
            "underflow": "integer_overflow",
            "init": "initialization",
            "balance": "balance_manipulation",
            "approval": "token_approval",
            "delegate": "delegatecall",
        }

        for key, ctx in pattern_context_map.items():
            if key in pattern_lower:
                return ctx

        return "general"


def get_relevant_categories(context: str) -> Set[str]:
    """Get label categories relevant to an analysis context.

    Args:
        context: Analysis context name

    Returns:
        Set of relevant category values
    """
    context_lower = context.lower()

    if context_lower in CONTEXT_TO_CATEGORIES:
        return CONTEXT_TO_CATEGORIES[context_lower]

    # Fuzzy match for context names
    for key, categories in CONTEXT_TO_CATEGORIES.items():
        if key in context_lower or context_lower in key:
            return categories

    # Default to all categories if context unknown
    return CONTEXT_TO_CATEGORIES["general"]


def filter_labels_for_context(
    labels: List[FunctionLabel],
    context: str,
    min_confidence: LabelConfidence = LabelConfidence.MEDIUM,
) -> List[FunctionLabel]:
    """Convenience function to filter a label list by context.

    Args:
        labels: Labels to filter
        context: Analysis context
        min_confidence: Minimum confidence threshold

    Returns:
        Filtered list of labels
    """
    relevant_categories = get_relevant_categories(context)
    threshold = min_confidence.threshold()

    return [
        label
        for label in labels
        if label.category in relevant_categories
        and label.confidence.threshold() >= threshold
    ]


__all__ = [
    "CONTEXT_TO_CATEGORIES",
    "FilteredLabels",
    "LabelFilter",
    "get_relevant_categories",
    "filter_labels_for_context",
]
