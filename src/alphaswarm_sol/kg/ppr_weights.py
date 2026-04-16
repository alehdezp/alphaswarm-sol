"""Edge weight calculation for PPR.

Task 9.1: Edge weights determine how probability flows through the graph.
Security-relevant edges get higher weights, guarded edges get lower weights.

Based on R9.1 research: edge-weights.md
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List


class EdgeType(Enum):
    """VKG edge types with security relevance."""

    CALLS = "calls"
    CALLS_EXTERNAL = "calls_external"
    DELEGATECALL = "delegatecall"
    READS_STATE = "reads_state"
    WRITES_STATE = "writes_state"
    HAS_MODIFIER = "has_modifier"
    INHERITS = "inherits"
    USES = "uses"
    USES_VARIABLE = "uses_variable"
    EMITS_EVENT = "emits_event"
    HAS_PARAMETER = "has_parameter"
    HAS_LOOP = "has_loop"
    CONTAINS = "contains"
    DEFINES = "defines"


# Base weights per edge type (from R9.1 research)
BASE_WEIGHTS: Dict[str, float] = {
    # High security relevance
    "calls_external": 1.5,
    "delegatecall": 2.0,
    "writes_state": 1.3,
    # Neutral
    "calls": 1.0,
    "reads_state": 0.8,
    "uses_variable": 0.7,
    # Guards and structure
    "has_modifier": 0.5,
    "inherits": 0.6,
    "uses": 0.5,
    "emits_event": 0.4,
    "has_parameter": 0.5,
    "has_loop": 0.6,
    "contains": 0.4,
    "defines": 0.3,
}


def calculate_edge_weight(
    edge: Dict[str, Any],
    base_weights: Dict[str, float] | None = None,
) -> float:
    """Calculate PPR weight for an edge.

    Args:
        edge: Edge dictionary with type, risk_score, guards_at_source
        base_weights: Override base weights (for tuning)

    Returns:
        Weight value (unnormalized)
    """
    if base_weights is None:
        base_weights = BASE_WEIGHTS

    # Get edge type
    edge_type = edge.get("type", "uses")
    if isinstance(edge_type, EdgeType):
        edge_type = edge_type.value

    # Normalize edge type string
    edge_type = edge_type.lower().replace("-", "_")

    # Base weight
    weight = base_weights.get(edge_type, 0.5)

    # Risk adjustment: increase weight for risky edges (1.0 - 2.0x range)
    risk_score = edge.get("risk_score", 0.0)
    if isinstance(risk_score, (int, float)) and risk_score > 0:
        weight *= 1.0 + min(risk_score, 1.0)

    # Taint adjustment: increase weight for tainted data flow
    if edge.get("taint_source") or edge.get("is_tainted"):
        weight *= 1.3

    # Guard penalty: decrease weight for guarded edges
    if edge.get("guards_at_source"):
        weight *= 0.6
    elif edge.get("has_guard") or edge.get("is_guarded"):
        weight *= 0.7

    # Ensure minimum weight
    return max(weight, 0.01)


def calculate_edge_weights_batch(
    edges: List[Dict[str, Any]],
    base_weights: Dict[str, float] | None = None,
) -> Dict[str, float]:
    """Calculate weights for multiple edges.

    Args:
        edges: List of edge dictionaries
        base_weights: Override base weights

    Returns:
        Dictionary mapping edge_id to weight (unnormalized)
    """
    weights = {}
    for edge in edges:
        edge_id = edge.get("id")
        if edge_id is None:
            source = edge.get("source", edge.get("from", ""))
            target = edge.get("target", edge.get("to", ""))
            edge_id = f"{source}->{target}"

        weights[edge_id] = calculate_edge_weight(edge, base_weights)

    return weights


def normalize_weights(
    weights: Dict[str, float],
    out_edges: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, float]:
    """Normalize weights so outgoing weights sum to 1 per source node.

    This is CRITICAL for PPR correctness - ensures valid probability distribution.

    Args:
        weights: Unnormalized edge weights (edge_id -> weight)
        out_edges: Mapping of source_node -> list of outgoing edges

    Returns:
        Normalized weights (edge_id -> normalized_weight)
    """
    normalized = {}

    for source_node, edges in out_edges.items():
        # Calculate total weight from this source
        edge_ids = []
        for e in edges:
            edge_id = e.get("id")
            if edge_id is None:
                target = e.get("target", e.get("to", ""))
                edge_id = f"{source_node}->{target}"
            edge_ids.append(edge_id)

        total = sum(weights.get(eid, 1.0) for eid in edge_ids)

        if total > 0:
            for eid in edge_ids:
                normalized[eid] = weights.get(eid, 1.0) / total
        else:
            # No outgoing edges or zero total - distribute uniformly
            for eid in edge_ids:
                normalized[eid] = 1.0 / max(len(edge_ids), 1)

    return normalized


def get_weight_for_edge_type(edge_type: str) -> float:
    """Get base weight for an edge type.

    Args:
        edge_type: Edge type string

    Returns:
        Base weight (before normalization)
    """
    edge_type = edge_type.lower().replace("-", "_")
    return BASE_WEIGHTS.get(edge_type, 0.5)


def create_analysis_weights(analysis_type: str) -> Dict[str, float]:
    """Create tuned weights for specific analysis types.

    Args:
        analysis_type: Type of analysis (reentrancy, access_control, dos, oracle)

    Returns:
        Tuned base weights dictionary
    """
    weights = BASE_WEIGHTS.copy()

    if analysis_type == "reentrancy":
        weights["calls_external"] = 2.0
        weights["delegatecall"] = 2.5
        weights["writes_state"] = 1.5

    elif analysis_type == "access_control":
        weights["has_modifier"] = 0.8  # Less penalty for guards
        weights["calls_external"] = 1.2

    elif analysis_type == "dos":
        weights["has_loop"] = 1.5
        weights["calls_external"] = 1.3

    elif analysis_type == "oracle":
        weights["reads_state"] = 1.3
        weights["calls_external"] = 1.4

    return weights
