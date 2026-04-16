"""Phase 10: Cross-Contract Similarity Index.

This module provides functionality for indexing and finding similar functions
across multiple contracts based on structural and behavioral properties.

Key features:
- Structural hashing: Fingerprints based on code structure
- Behavioral indexing: Functions grouped by behavioral signature
- Similarity scoring: Multiple metrics for finding similar code
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

from alphaswarm_sol.kg.schema import Node


class SimilarityType(str, Enum):
    """Types of similarity between functions."""
    STRUCTURAL = "structural"  # Same code structure/hash
    BEHAVIORAL = "behavioral"  # Same behavioral signature
    PROPERTY = "property"      # Similar property set
    COMBINED = "combined"      # Weighted combination


@dataclass
class SimilarFunction:
    """Represents a similar function match."""
    function: Node
    similarity_type: SimilarityType
    score: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_id": self.function.id,
            "function_label": self.function.label,
            "similarity_type": self.similarity_type.value,
            "score": self.score,
            "details": self.details,
        }


@dataclass
class StructuralFingerprint:
    """Structural fingerprint for a function.

    Captures code structure independently of variable names.
    """
    visibility: str
    has_parameters: bool
    parameter_count: int
    has_return: bool
    has_modifiers: bool
    writes_state: bool
    reads_state: bool
    has_loops: bool
    has_conditionals: bool
    has_external_calls: bool
    has_internal_calls: bool
    operation_count: int

    def to_hash(self) -> str:
        """Compute a hash from the fingerprint."""
        components = [
            self.visibility,
            str(self.has_parameters),
            str(self.parameter_count),
            str(self.has_return),
            str(self.has_modifiers),
            str(self.writes_state),
            str(self.reads_state),
            str(self.has_loops),
            str(self.has_conditionals),
            str(self.has_external_calls),
            str(self.has_internal_calls),
            str(self.operation_count),
        ]
        fingerprint = "|".join(components)
        return hashlib.sha256(fingerprint.encode()).hexdigest()[:16]


def compute_structural_fingerprint(fn: Node) -> StructuralFingerprint:
    """Compute structural fingerprint for a function node.

    Args:
        fn: Function node from the knowledge graph

    Returns:
        StructuralFingerprint capturing code structure
    """
    props = fn.properties

    # Extract visibility
    visibility = props.get("visibility", "internal")

    # Parameter information
    param_types = props.get("param_types", [])
    has_parameters = len(param_types) > 0
    parameter_count = len(param_types)

    # Return information
    return_types = props.get("return_types", [])
    has_return = len(return_types) > 0

    # Modifiers
    modifiers = props.get("modifiers", [])
    has_modifiers = len(modifiers) > 0

    # State access
    writes_state = props.get("writes_state", False)
    reads_state = props.get("reads_state", False)

    # Control flow
    has_loops = props.get("has_unbounded_loop", False) or props.get("has_loop", False)
    has_conditionals = props.get("has_conditionals", False) or props.get("has_if_statement", False)

    # Calls
    has_external_calls = props.get("has_external_calls", False)
    has_internal_calls = props.get("has_internal_calls", False)

    # Operation count from semantic ops
    semantic_ops = props.get("semantic_ops", [])
    operation_count = len(semantic_ops)

    return StructuralFingerprint(
        visibility=visibility,
        has_parameters=has_parameters,
        parameter_count=parameter_count,
        has_return=has_return,
        has_modifiers=has_modifiers,
        writes_state=writes_state,
        reads_state=reads_state,
        has_loops=has_loops,
        has_conditionals=has_conditionals,
        has_external_calls=has_external_calls,
        has_internal_calls=has_internal_calls,
        operation_count=operation_count,
    )


def compute_structural_hash(fn: Node) -> str:
    """Compute a structural hash for a function.

    Args:
        fn: Function node

    Returns:
        16-character hex hash of structural fingerprint
    """
    fingerprint = compute_structural_fingerprint(fn)
    return fingerprint.to_hash()


def compute_property_similarity(fn1: Node, fn2: Node) -> float:
    """Compute property-based similarity between two functions.

    Uses Jaccard similarity on security-relevant properties.

    Args:
        fn1: First function node
        fn2: Second function node

    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Properties to compare
    security_props = [
        "visibility",
        "has_access_gate",
        "has_reentrancy_guard",
        "writes_state",
        "reads_state",
        "has_external_calls",
        "uses_delegatecall",
        "reads_oracle_price",
        "uses_ecrecover",
        "swap_like",
        "writes_privileged_state",
        "is_initializer_like",
    ]

    # Boolean properties
    bool_props1: Set[str] = set()
    bool_props2: Set[str] = set()

    for prop in security_props:
        val1 = fn1.properties.get(prop)
        val2 = fn2.properties.get(prop)

        if isinstance(val1, bool) and val1:
            bool_props1.add(prop)
        elif isinstance(val1, str):
            bool_props1.add(f"{prop}:{val1}")

        if isinstance(val2, bool) and val2:
            bool_props2.add(prop)
        elif isinstance(val2, str):
            bool_props2.add(f"{prop}:{val2}")

    # Jaccard similarity
    if not bool_props1 and not bool_props2:
        return 1.0  # Both empty = identical

    intersection = len(bool_props1 & bool_props2)
    union = len(bool_props1 | bool_props2)

    return intersection / union if union > 0 else 0.0


def compute_operation_similarity(fn1: Node, fn2: Node) -> float:
    """Compute similarity based on semantic operations.

    Args:
        fn1: First function node
        fn2: Second function node

    Returns:
        Similarity score between 0.0 and 1.0
    """
    ops1 = set(fn1.properties.get("semantic_ops", []))
    ops2 = set(fn2.properties.get("semantic_ops", []))

    if not ops1 and not ops2:
        return 1.0

    intersection = len(ops1 & ops2)
    union = len(ops1 | ops2)

    return intersection / union if union > 0 else 0.0


def compute_signature_similarity(sig1: str, sig2: str) -> float:
    """Compute similarity between behavioral signatures.

    Uses edit distance normalized by max length.

    Args:
        sig1: First behavioral signature
        sig2: Second behavioral signature

    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Both empty = no signature to compare, return 0
    if not sig1 and not sig2:
        return 0.0

    if sig1 == sig2:
        return 1.0

    if not sig1 or not sig2:
        return 0.0

    # Parse signatures into operation sequences
    ops1 = sig1.split("→") if sig1 else []
    ops2 = sig2.split("→") if sig2 else []

    # Compute longest common subsequence
    m, n = len(ops1), len(ops2)
    if m == 0 or n == 0:
        return 0.0

    # LCS dynamic programming
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ops1[i - 1] == ops2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    lcs_length = dp[m][n]
    max_length = max(m, n)

    return lcs_length / max_length


class SimilarityIndex:
    """Index for finding similar functions across contracts.

    Maintains multiple indexes for efficient similarity lookup:
    - Structural index: Hash -> [functions]
    - Behavioral index: Signature -> [functions]
    - Property index: Property set hash -> [functions]

    Example:
        >>> index = SimilarityIndex()
        >>> for fn in graph.nodes.values():
        ...     if fn.type == "Function":
        ...         index.index_function(fn)
        >>> similar = index.find_similar(target_fn, threshold=0.85)
    """

    def __init__(self):
        """Initialize empty indexes."""
        # Structural hash -> list of functions
        self.structural_index: Dict[str, List[Node]] = {}
        # Behavioral signature -> list of functions
        self.behavioral_index: Dict[str, List[Node]] = {}
        # All indexed functions
        self._functions: Dict[str, Node] = {}

    def index_function(self, fn: Node) -> None:
        """Add a function to the indexes.

        Args:
            fn: Function node to index
        """
        if fn.type != "Function":
            return

        # Store function
        self._functions[fn.id] = fn

        # Index by structural hash
        struct_hash = compute_structural_hash(fn)
        self.structural_index.setdefault(struct_hash, []).append(fn)

        # Index by behavioral signature
        sig = fn.properties.get("behavioral_signature", "")
        if sig:
            self.behavioral_index.setdefault(sig, []).append(fn)

    def index_graph(self, graph: Any) -> int:
        """Index all functions from a knowledge graph.

        Args:
            graph: KnowledgeGraph with function nodes

        Returns:
            Number of functions indexed
        """
        count = 0
        for node in graph.nodes.values():
            if node.type == "Function":
                self.index_function(node)
                count += 1
        return count

    def find_similar(
        self,
        fn: Node,
        threshold: float = 0.85,
        max_results: int = 10,
        similarity_types: Optional[List[SimilarityType]] = None,
    ) -> List[SimilarFunction]:
        """Find functions similar to the given function.

        Args:
            fn: Target function to find matches for
            threshold: Minimum similarity score (0.0-1.0)
            max_results: Maximum number of results to return
            similarity_types: Types of similarity to consider

        Returns:
            List of SimilarFunction matches, sorted by score descending
        """
        if similarity_types is None:
            similarity_types = [
                SimilarityType.STRUCTURAL,
                SimilarityType.BEHAVIORAL,
                SimilarityType.PROPERTY,
            ]

        similar: List[SimilarFunction] = []
        seen_ids: Set[str] = {fn.id}  # Exclude self

        # Structural matches (exact hash match = score 1.0)
        if SimilarityType.STRUCTURAL in similarity_types:
            struct_hash = compute_structural_hash(fn)
            for match in self.structural_index.get(struct_hash, []):
                if match.id not in seen_ids:
                    seen_ids.add(match.id)
                    similar.append(SimilarFunction(
                        function=match,
                        similarity_type=SimilarityType.STRUCTURAL,
                        score=1.0,
                        details={"structural_hash": struct_hash},
                    ))

        # Behavioral matches (exact signature = score 1.0, partial = computed)
        if SimilarityType.BEHAVIORAL in similarity_types:
            target_sig = fn.properties.get("behavioral_signature", "")
            if target_sig:
                # Exact matches
                for match in self.behavioral_index.get(target_sig, []):
                    if match.id not in seen_ids:
                        seen_ids.add(match.id)
                        similar.append(SimilarFunction(
                            function=match,
                            similarity_type=SimilarityType.BEHAVIORAL,
                            score=1.0,
                            details={"behavioral_signature": target_sig},
                        ))

                # Partial matches - check all other signatures
                for sig, matches in self.behavioral_index.items():
                    if sig != target_sig:
                        sig_score = compute_signature_similarity(target_sig, sig)
                        if sig_score >= threshold:
                            for match in matches:
                                if match.id not in seen_ids:
                                    seen_ids.add(match.id)
                                    similar.append(SimilarFunction(
                                        function=match,
                                        similarity_type=SimilarityType.BEHAVIORAL,
                                        score=sig_score,
                                        details={
                                            "target_signature": target_sig,
                                            "match_signature": sig,
                                        },
                                    ))

        # Property-based matches (scan all functions)
        if SimilarityType.PROPERTY in similarity_types:
            for candidate in self._functions.values():
                if candidate.id not in seen_ids:
                    prop_score = compute_property_similarity(fn, candidate)
                    if prop_score >= threshold:
                        seen_ids.add(candidate.id)
                        similar.append(SimilarFunction(
                            function=candidate,
                            similarity_type=SimilarityType.PROPERTY,
                            score=prop_score,
                            details={"property_similarity": prop_score},
                        ))

        # Sort by score descending and limit results
        similar.sort(key=lambda x: x.score, reverse=True)
        return similar[:max_results]

    def find_by_signature(self, signature: str) -> List[Node]:
        """Find all functions with a specific behavioral signature.

        Args:
            signature: Behavioral signature to match

        Returns:
            List of matching function nodes
        """
        return self.behavioral_index.get(signature, [])

    def find_by_structural_hash(self, hash_val: str) -> List[Node]:
        """Find all functions with a specific structural hash.

        Args:
            hash_val: Structural hash to match

        Returns:
            List of matching function nodes
        """
        return self.structural_index.get(hash_val, [])

    def get_signature_groups(self) -> Dict[str, List[Node]]:
        """Get all functions grouped by behavioral signature.

        Useful for finding patterns across contracts.

        Returns:
            Dict mapping signature to list of functions
        """
        return dict(self.behavioral_index)

    def get_structural_groups(self) -> Dict[str, List[Node]]:
        """Get all functions grouped by structural hash.

        Returns:
            Dict mapping structural hash to list of functions
        """
        return dict(self.structural_index)

    def get_statistics(self) -> Dict[str, Any]:
        """Get index statistics.

        Returns:
            Dict with index statistics
        """
        return {
            "total_functions": len(self._functions),
            "unique_structural_hashes": len(self.structural_index),
            "unique_signatures": len(self.behavioral_index),
            "largest_structural_group": max(
                (len(v) for v in self.structural_index.values()),
                default=0
            ),
            "largest_behavioral_group": max(
                (len(v) for v in self.behavioral_index.values()),
                default=0
            ),
        }

    def clear(self) -> None:
        """Clear all indexes."""
        self.structural_index.clear()
        self.behavioral_index.clear()
        self._functions.clear()


__all__ = [
    "SimilarityType",
    "SimilarFunction",
    "StructuralFingerprint",
    "SimilarityIndex",
    "compute_structural_fingerprint",
    "compute_structural_hash",
    "compute_property_similarity",
    "compute_operation_similarity",
    "compute_signature_similarity",
]
