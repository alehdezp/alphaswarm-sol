"""
Graph Fingerprinting Module

Generates stable fingerprints for VKG graphs to detect changes.
Fingerprints are deterministic: same code = same fingerprint.

Usage:
    from alphaswarm_sol.kg.fingerprint import fingerprint_graph, compare_fingerprints

    fp1 = fingerprint_graph(graph_data)
    fp2 = fingerprint_graph(graph_data)
    assert fp1 == fp2  # Same graph = same fingerprint

For node/edge ID generation:
    from alphaswarm_sol.kg.fingerprint import stable_node_id, stable_edge_id

    node_id = stable_node_id('function', 'Token', 'transfer', 'transfer(address,uint256)')
    edge_id = stable_edge_id('CALLS', source_id, target_id)
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.kg.schema import KnowledgeGraph as KGType


__all__ = [
    # Stable ID generation
    "stable_node_id",
    "stable_edge_id",
    # Graph fingerprinting
    "graph_fingerprint",
    "fingerprint_graph",
    "fingerprint_node",
    "fingerprint_edge",
    # Comparison and verification
    "compare_fingerprints",
    "verify_determinism",
    # Persistence
    "save_fingerprint",
    "load_fingerprint",
]


# -----------------------------------------------------------------------------
# Stable ID Generation
# -----------------------------------------------------------------------------

def stable_node_id(
    kind: str,
    contract: str,
    name: str,
    signature: str | None = None,
    *,
    schema_version: str = "2.0",
) -> str:
    """Generate deterministic node ID from semantic content.

    Unlike the original _node_id which included file paths,
    this generates IDs based only on semantic identity:
    - Contract name
    - Entity name (function, variable, etc.)
    - Signature (for functions)

    This ensures the same entity always gets the same ID,
    regardless of file location or processing order.

    Args:
        kind: Node type (function, state_variable, contract, etc.)
        contract: Parent contract name
        name: Entity name
        signature: Function signature (optional)
        schema_version: Graph schema version (included in hash)

    Returns:
        Stable node ID in format "{kind}:{hash12}"

    Examples:
        >>> stable_node_id('function', 'Token', 'transfer', 'transfer(address,uint256)')
        'function:a1b2c3d4e5f6'
        >>> stable_node_id('contract', 'Token', 'Token')
        'contract:f7e8d9c0b1a2'
    """
    components = [schema_version, kind, contract, name]
    if signature:
        components.append(signature)
    raw = ":".join(components)
    return f"{kind}:{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def stable_edge_id(
    edge_type: str,
    source_id: str,
    target_id: str,
    *,
    qualifier: str | None = None,
) -> str:
    """Generate deterministic edge ID.

    Args:
        edge_type: Edge relationship type
        source_id: Source node ID
        target_id: Target node ID
        qualifier: Optional qualifier for multiple edges between same nodes

    Returns:
        Stable edge ID in format "{edge_type}:{hash12}"

    Examples:
        >>> stable_edge_id('CALLS', 'function:abc123', 'function:def456')
        'CALLS:7890abcd1234'
        >>> stable_edge_id('WRITES', 'function:abc123', 'state_variable:xyz789', qualifier='line_42')
        'WRITES:fedcba987654'
    """
    components = [edge_type, source_id, target_id]
    if qualifier:
        components.append(qualifier)
    raw = ":".join(components)
    return f"{edge_type}:{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


# -----------------------------------------------------------------------------
# Graph Fingerprinting (KnowledgeGraph objects)
# -----------------------------------------------------------------------------

# Properties that are unstable across builds (file paths, timestamps, etc.)
_UNSTABLE_KEYS = frozenset({
    "file_path",
    "file",
    "absolute_path",
    "build_time",
    "timestamp",
    "line_start",
    "line_end",
})


def _stable_properties(props: dict[str, Any], exclude_unstable: bool) -> dict[str, Any]:
    """Filter properties to exclude unstable ones.

    Args:
        props: Property dictionary
        exclude_unstable: Whether to exclude unstable keys

    Returns:
        Filtered property dictionary
    """
    if not exclude_unstable:
        return props
    return {k: v for k, v in props.items() if k not in _UNSTABLE_KEYS}


def graph_fingerprint(
    graph: "KGType",
    *,
    include_schema_version: bool = True,
    exclude_unstable: bool = True,
) -> str:
    """Compute deterministic fingerprint of graph content.

    This is the primary fingerprinting function for KnowledgeGraph objects.
    It produces a stable SHA256 hash that is independent of:
    - File paths
    - Processing order
    - Timestamps

    Args:
        graph: KnowledgeGraph to fingerprint
        include_schema_version: Include schema version in fingerprint
        exclude_unstable: Exclude properties that may vary (timestamps, etc.)

    Returns:
        Stable SHA256 fingerprint (64 hex characters)

    Example:
        >>> from alphaswarm_sol.kg.schema import KnowledgeGraph
        >>> graph = KnowledgeGraph()
        >>> fp1 = graph_fingerprint(graph)
        >>> fp2 = graph_fingerprint(graph)
        >>> assert fp1 == fp2  # Always deterministic
    """
    hasher = hashlib.sha256()

    # Include schema version
    if include_schema_version:
        hasher.update(b"schema:2.0\n")

    # Process nodes in sorted order (by ID)
    for node_id in sorted(graph.nodes.keys()):
        node = graph.nodes[node_id]
        # Exclude unstable properties
        props = _stable_properties(node.properties, exclude_unstable)
        node_data = f"node:{node_id}:{node.label}:{json.dumps(props, sort_keys=True)}\n"
        hasher.update(node_data.encode())

    # Process edges in sorted order
    for edge_id in sorted(graph.edges.keys()):
        edge = graph.edges[edge_id]
        edge_data = f"edge:{edge_id}:{edge.source}:{edge.target}:{edge.type}\n"
        hasher.update(edge_data.encode())

    # Include rich edges in fingerprint
    for rich_edge_id in sorted(graph.rich_edges.keys()):
        rich_edge = graph.rich_edges[rich_edge_id]
        re_data = f"rich_edge:{rich_edge_id}:{rich_edge.source}:{rich_edge.target}:{rich_edge.type}\n"
        hasher.update(re_data.encode())

    return hasher.hexdigest()


# -----------------------------------------------------------------------------
# Legacy Fingerprinting (dict-based graphs)
# -----------------------------------------------------------------------------


def _stable_json(obj: Any) -> str:
    """Convert object to stable JSON string (sorted keys, no extra whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _hash_string(s: str) -> str:
    """Create SHA256 hash of string."""
    return hashlib.sha256(s.encode()).hexdigest()


def fingerprint_node(node: dict) -> str:
    """
    Create fingerprint for a single node.

    Only includes semantic properties, not file paths or line numbers
    which can change across builds.
    """
    # Extract stable properties
    stable_props = {}
    props = node.get("properties", {})

    # Semantic properties that define behavior
    semantic_keys = [
        "visibility",
        "payable",
        "has_access_gate",
        "has_reentrancy_guard",
        "has_external_calls",
        "has_internal_calls",
        "has_loops",
        "has_unbounded_loop",
        "writes_state",
        "reads_state",
        "state_write_after_external_call",
        "is_value_transfer",
        "uses_msg_sender",
        "uses_tx_origin",
        "uses_ecrecover",
        "uses_delegatecall",
        "uses_call",
        "uses_transfer",
        "uses_erc20_transfer",
        "has_staleness_check",
        "semantic_ops",
        "semantic_role",
    ]

    for key in semantic_keys:
        if key in props:
            stable_props[key] = props[key]

    # Include node type and label (without path info)
    fingerprint_data = {
        "type": node.get("type"),
        "label": node.get("label"),
        "properties": stable_props,
    }

    return _hash_string(_stable_json(fingerprint_data))


def fingerprint_edge(edge: dict) -> str:
    """Create fingerprint for a single edge."""
    fingerprint_data = {
        "type": edge.get("type"),
        "source": edge.get("source"),
        "target": edge.get("target"),
        "label": edge.get("label"),
    }
    return _hash_string(_stable_json(fingerprint_data))


def fingerprint_graph(graph_data: dict) -> dict:
    """
    Create comprehensive fingerprint for a VKG graph.

    Returns a dictionary containing:
    - full_hash: Hash of entire graph structure
    - node_count: Number of nodes
    - edge_count: Number of edges
    - node_type_counts: Counts by node type
    - semantic_summary: Summary of key semantic properties
    - version: Fingerprint format version
    """
    graph = graph_data.get("graph", graph_data)
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    # Count node types
    node_type_counts = {}
    for node in nodes:
        node_type = node.get("type", "Unknown")
        node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1

    # Count key semantic properties
    semantic_counts = {
        "has_access_gate": 0,
        "has_reentrancy_guard": 0,
        "state_write_after_external_call": 0,
        "has_unbounded_loop": 0,
        "is_value_transfer": 0,
        "uses_delegatecall": 0,
    }

    for node in nodes:
        props = node.get("properties", {})
        for key in semantic_counts:
            if props.get(key):
                semantic_counts[key] += 1

    # Create node fingerprints (sorted for stability)
    node_fingerprints = sorted([fingerprint_node(n) for n in nodes])

    # Create edge fingerprints (sorted for stability)
    edge_fingerprints = sorted([fingerprint_edge(e) for e in edges])

    # Create full graph hash
    full_data = {
        "nodes": node_fingerprints,
        "edges": edge_fingerprints,
    }
    full_hash = _hash_string(_stable_json(full_data))

    return {
        "version": "1.0",
        "full_hash": full_hash,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_type_counts": node_type_counts,
        "semantic_summary": semantic_counts,
        "node_fingerprints": node_fingerprints[:10],  # First 10 for debugging
    }


def compare_fingerprints(fp1: dict, fp2: dict) -> dict:
    """
    Compare two fingerprints and return difference summary.

    Returns:
        Dictionary with comparison results:
        - identical: bool - Whether fingerprints match exactly
        - hash_match: bool - Whether full hashes match
        - node_count_diff: int - Difference in node counts
        - edge_count_diff: int - Difference in edge counts
        - type_diffs: dict - Differences in node type counts
        - semantic_diffs: dict - Differences in semantic property counts
    """
    identical = fp1.get("full_hash") == fp2.get("full_hash")

    node_diff = (fp2.get("node_count", 0) - fp1.get("node_count", 0))
    edge_diff = (fp2.get("edge_count", 0) - fp1.get("edge_count", 0))

    # Compare node type counts
    types1 = fp1.get("node_type_counts", {})
    types2 = fp2.get("node_type_counts", {})
    all_types = set(types1.keys()) | set(types2.keys())
    type_diffs = {}
    for t in all_types:
        diff = types2.get(t, 0) - types1.get(t, 0)
        if diff != 0:
            type_diffs[t] = diff

    # Compare semantic counts
    sem1 = fp1.get("semantic_summary", {})
    sem2 = fp2.get("semantic_summary", {})
    all_props = set(sem1.keys()) | set(sem2.keys())
    semantic_diffs = {}
    for p in all_props:
        diff = sem2.get(p, 0) - sem1.get(p, 0)
        if diff != 0:
            semantic_diffs[p] = diff

    return {
        "identical": identical,
        "hash_match": identical,
        "node_count_diff": node_diff,
        "edge_count_diff": edge_diff,
        "type_diffs": type_diffs,
        "semantic_diffs": semantic_diffs,
    }


def verify_determinism(graph_data: dict, runs: int = 10) -> bool:
    """
    Verify that fingerprinting is deterministic across multiple runs.

    Returns True if all runs produce identical fingerprints.
    """
    fingerprints = []
    for _ in range(runs):
        fp = fingerprint_graph(graph_data)
        fingerprints.append(fp["full_hash"])

    return len(set(fingerprints)) == 1


def save_fingerprint(fingerprint: dict, path: str) -> None:
    """Save fingerprint to JSON file."""
    with open(path, "w") as f:
        json.dump(fingerprint, f, indent=2, sort_keys=True)


def load_fingerprint(path: str) -> dict:
    """Load fingerprint from JSON file."""
    with open(path) as f:
        return json.load(f)
