"""VQL Label Query Functions.

Provides functions for querying semantic labels in VQL.

Usage in VQL:
    FIND functions WHERE has_label('access_control.owner_only')
    FIND functions WHERE label_confidence('access_control.owner_only') >= 'high'
    FIND functions WHERE labels_in_category('access_control')
    FIND functions WHERE missing_label('access_control.no_restriction')
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from alphaswarm_sol.labels.schema import LabelConfidence, FunctionLabel, LabelSet
from alphaswarm_sol.labels.overlay import LabelOverlay
from alphaswarm_sol.labels.filter import LabelFilter

if TYPE_CHECKING:
    from alphaswarm_sol.kg.schema import Node


# Global overlay reference (set by executor)
_current_overlay: Optional[LabelOverlay] = None
_current_filter: Optional[LabelFilter] = None
_current_context: Optional[str] = None


def set_label_context(
    overlay: LabelOverlay,
    analysis_context: Optional[str] = None,
) -> None:
    """Set the label overlay and context for VQL queries.

    Called by executor before running queries.

    Args:
        overlay: Label overlay to query
        analysis_context: Optional context for filtering
    """
    global _current_overlay, _current_filter, _current_context
    _current_overlay = overlay
    _current_filter = LabelFilter(overlay) if overlay else None
    _current_context = analysis_context


def clear_label_context() -> None:
    """Clear label context after query execution."""
    global _current_overlay, _current_filter, _current_context
    _current_overlay = None
    _current_filter = None
    _current_context = None


def _get_node_id(node: Any) -> str:
    """Extract node ID from various node representations.

    Args:
        node: Node object or dict with 'id' key

    Returns:
        Node ID string
    """
    if hasattr(node, "id"):
        return node.id
    if isinstance(node, dict) and "id" in node:
        return node["id"]
    return str(node)


def _confidence_value(confidence: LabelConfidence) -> float:
    """Get numeric value for confidence comparison.

    Args:
        confidence: LabelConfidence enum value

    Returns:
        Numeric threshold value
    """
    return {"high": 0.8, "medium": 0.5, "low": 0.0}[confidence.value]


def has_label(node: Any, label_id: str, min_confidence: str = "medium") -> bool:
    """Check if a node has a specific label.

    VQL: has_label('access_control.owner_only')
    VQL: has_label('access_control.owner_only', 'high')

    Args:
        node: Graph node to check
        label_id: Label ID to look for
        min_confidence: Minimum confidence ('low', 'medium', 'high')

    Returns:
        True if node has the label with sufficient confidence
    """
    if not _current_overlay:
        return False

    node_id = _get_node_id(node)
    label_set = _current_overlay.get_labels(node_id)
    min_conf = LabelConfidence(min_confidence)
    min_val = _confidence_value(min_conf)

    for label in label_set.labels:
        if label.label_id == label_id:
            if _confidence_value(label.confidence) >= min_val:
                return True
    return False


def missing_label(node: Any, label_id: str) -> bool:
    """Check if a node is missing a specific label.

    VQL: missing_label('access_control.owner_only')

    Args:
        node: Graph node to check
        label_id: Label ID that should be absent

    Returns:
        True if node does NOT have the label
    """
    return not has_label(node, label_id, min_confidence="low")


def has_any_label(node: Any, *label_ids: str) -> bool:
    """Check if a node has any of the specified labels.

    VQL: has_any_label('access_control.owner_only', 'access_control.role_based')

    Args:
        node: Graph node to check
        label_ids: Label IDs to check for

    Returns:
        True if node has at least one of the labels
    """
    for label_id in label_ids:
        if has_label(node, label_id):
            return True
    return False


def has_all_labels(node: Any, *label_ids: str) -> bool:
    """Check if a node has all of the specified labels.

    VQL: has_all_labels('state_mutation.writes_critical', 'external_interaction.calls_external')

    Args:
        node: Graph node to check
        label_ids: Label IDs that must all be present

    Returns:
        True if node has all the labels
    """
    for label_id in label_ids:
        if not has_label(node, label_id):
            return False
    return True


def label_confidence(node: Any, label_id: str) -> str:
    """Get the confidence level of a label.

    VQL: label_confidence('access_control.owner_only') == 'high'

    Args:
        node: Graph node to check
        label_id: Label ID to get confidence for

    Returns:
        Confidence level ('high', 'medium', 'low') or 'none' if not present
    """
    if not _current_overlay:
        return "none"

    node_id = _get_node_id(node)
    label_set = _current_overlay.get_labels(node_id)
    for label in label_set.labels:
        if label.label_id == label_id:
            return label.confidence.value
    return "none"


def labels_in_category(node: Any, category: str) -> List[str]:
    """Get all labels in a category for a node.

    VQL: labels_in_category('access_control')

    Args:
        node: Graph node to check
        category: Category name

    Returns:
        List of label IDs in that category
    """
    if not _current_overlay:
        return []

    node_id = _get_node_id(node)
    label_set = _current_overlay.get_labels(node_id)
    return [
        label.label_id
        for label in label_set.labels
        if label.category == category
    ]


def has_category(node: Any, category: str) -> bool:
    """Check if a node has any label in a category.

    VQL: has_category('access_control')

    Args:
        node: Graph node to check
        category: Category name

    Returns:
        True if node has any label in the category
    """
    return len(labels_in_category(node, category)) > 0


def label_count(node: Any, category: Optional[str] = None) -> int:
    """Count labels on a node.

    VQL: label_count()
    VQL: label_count('access_control')

    Args:
        node: Graph node to check
        category: Optional category to filter by

    Returns:
        Number of labels (in category if specified)
    """
    if not _current_overlay:
        return 0

    node_id = _get_node_id(node)
    label_set = _current_overlay.get_labels(node_id)
    if category:
        return len([lbl for lbl in label_set.labels if lbl.category == category])
    return len(label_set.labels)


def get_label_reasoning(node: Any, label_id: str) -> Optional[str]:
    """Get the reasoning for a label assignment.

    VQL: get_label_reasoning('access_control.owner_only')

    Args:
        node: Graph node to check
        label_id: Label ID

    Returns:
        Reasoning string or None
    """
    if not _current_overlay:
        return None

    node_id = _get_node_id(node)
    label_set = _current_overlay.get_labels(node_id)
    for label in label_set.labels:
        if label.label_id == label_id:
            return label.reasoning
    return None


def get_label_source(node: Any, label_id: str) -> Optional[str]:
    """Get the source of a label assignment.

    VQL: get_label_source('access_control.owner_only')

    Args:
        node: Graph node to check
        label_id: Label ID

    Returns:
        Source string ('llm', 'user_override', 'pattern') or None
    """
    if not _current_overlay:
        return None

    node_id = _get_node_id(node)
    label_set = _current_overlay.get_labels(node_id)
    for label in label_set.labels:
        if label.label_id == label_id:
            return label.source.value
    return None


def get_all_labels(node: Any, min_confidence: str = "low") -> List[str]:
    """Get all label IDs for a node.

    VQL: get_all_labels()
    VQL: get_all_labels('high')

    Args:
        node: Graph node to check
        min_confidence: Minimum confidence filter

    Returns:
        List of label IDs
    """
    if not _current_overlay:
        return []

    node_id = _get_node_id(node)
    label_set = _current_overlay.get_labels(node_id)
    min_conf = LabelConfidence(min_confidence)
    min_val = _confidence_value(min_conf)

    return [
        label.label_id
        for label in label_set.labels
        if _confidence_value(label.confidence) >= min_val
    ]


def has_high_confidence_label(node: Any, label_id: str) -> bool:
    """Check if node has a label with HIGH confidence.

    Convenience function for common pattern.

    Args:
        node: Graph node to check
        label_id: Label ID to look for

    Returns:
        True if node has the label with HIGH confidence
    """
    return has_label(node, label_id, min_confidence="high")


def labels_filtered_for_context(node: Any, context: str) -> List[str]:
    """Get labels filtered by analysis context.

    Uses LabelFilter to get context-relevant labels.

    VQL: labels_filtered_for_context('reentrancy')

    Args:
        node: Graph node to check
        context: Analysis context (e.g., 'reentrancy', 'access_control')

    Returns:
        List of relevant label IDs
    """
    if not _current_filter:
        return []

    node_id = _get_node_id(node)
    filtered = _current_filter.get_filtered_labels(node_id, context)
    return [label.label_id for label in filtered.labels_included]


# Function registry for executor integration
LABEL_FUNCTIONS: Dict[str, Callable] = {
    "has_label": has_label,
    "missing_label": missing_label,
    "has_any_label": has_any_label,
    "has_all_labels": has_all_labels,
    "label_confidence": label_confidence,
    "labels_in_category": labels_in_category,
    "has_category": has_category,
    "label_count": label_count,
    "get_label_reasoning": get_label_reasoning,
    "get_label_source": get_label_source,
    "get_all_labels": get_all_labels,
    "has_high_confidence_label": has_high_confidence_label,
    "labels_filtered_for_context": labels_filtered_for_context,
}


def register_label_functions(executor: Any) -> None:
    """Register label functions with VQL executor.

    Args:
        executor: VQL executor instance
    """
    for name, func in LABEL_FUNCTIONS.items():
        if hasattr(executor, "register_function"):
            executor.register_function(name, func)
        elif hasattr(executor, "functions"):
            executor.functions[name] = func


def get_available_functions() -> Dict[str, str]:
    """Get documentation for available label functions.

    Returns:
        Dict mapping function name to usage description
    """
    return {
        "has_label": "has_label('label_id', [min_confidence]) - Check if node has label",
        "missing_label": "missing_label('label_id') - Check if node lacks label",
        "has_any_label": "has_any_label('label1', 'label2', ...) - Check for any label",
        "has_all_labels": "has_all_labels('label1', 'label2', ...) - Check for all labels",
        "label_confidence": "label_confidence('label_id') - Get label confidence",
        "labels_in_category": "labels_in_category('category') - Get labels in category",
        "has_category": "has_category('category') - Check for any label in category",
        "label_count": "label_count([category]) - Count labels",
        "get_label_reasoning": "get_label_reasoning('label_id') - Get label reasoning",
        "get_label_source": "get_label_source('label_id') - Get label source",
        "get_all_labels": "get_all_labels([min_confidence]) - Get all label IDs",
        "has_high_confidence_label": "has_high_confidence_label('label_id') - Check for high confidence",
        "labels_filtered_for_context": "labels_filtered_for_context('context') - Get context-relevant labels",
    }


__all__ = [
    # Context management
    "set_label_context",
    "clear_label_context",
    # Query functions
    "has_label",
    "missing_label",
    "has_any_label",
    "has_all_labels",
    "label_confidence",
    "labels_in_category",
    "has_category",
    "label_count",
    "get_label_reasoning",
    "get_label_source",
    "get_all_labels",
    "has_high_confidence_label",
    "labels_filtered_for_context",
    # Registry
    "LABEL_FUNCTIONS",
    "register_label_functions",
    "get_available_functions",
]
