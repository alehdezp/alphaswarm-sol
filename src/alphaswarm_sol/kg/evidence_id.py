"""Canonical Evidence ID Generation for Knowledge Graph.

This module provides the canonical evidence_id_for() function that generates
deterministic, graph-versioned evidence identifiers. These IDs tie evidence
to specific graph builds for reproducible gating and auditing.

Key Features:
- Deterministic: Same inputs always produce same ID
- Graph-versioned: IDs include build hash for reproducibility
- Source-linked: IDs encode file path and line range
- Operation-aware: Semantic operations can be included for precision

Evidence ID Format: EVD-<8-hex-chars>
Where hex = SHA256(build_hash:node_id:file:line_start:line_end:semantic_op)[:8]

Reference: docs/reference/graph-interface-v2.md
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.kg.schema import Evidence

# Re-export core types from llm.evidence_ids for convenience
from alphaswarm_sol.llm.evidence_ids import (
    EvidenceID as _LLMEvidenceID,
    EvidenceIDError,
    EvidenceRegistry,
    EvidenceResolutionError,
    SourceSpan,
    EVIDENCE_ID_PATTERN,
    BUILD_HASH_PATTERN,
    validate_evidence_id,
    validate_build_hash,
)

# Re-export graph hash utilities
from alphaswarm_sol.kg.graph_hash import (
    compute_graph_hash,
    extract_build_hash,
    validate_build_hash as validate_build_hash_strict,
    BUILD_HASH_LENGTH,
)


def evidence_id_for(
    build_hash: str,
    node_id: str,
    file: str,
    line_start: int,
    line_end: Optional[int] = None,
    semantic_op: Optional[str] = None,
    *,
    column: int = 0,
) -> str:
    """Generate canonical evidence ID for graph evidence.

    This is the primary function for generating evidence IDs. It produces
    deterministic IDs that can be used for evidence gating, deduplication,
    and audit trails.

    Args:
        build_hash: 12-char graph build hash (required for reproducibility)
        node_id: Graph node or edge ID this evidence relates to
        file: Source file path
        line_start: Starting line number (1-indexed)
        line_end: Ending line number (optional, defaults to line_start)
        semantic_op: Semantic operation name (optional, for precision)
        column: Column number (0-indexed, default 0)

    Returns:
        Deterministic evidence ID (EVD-xxxxxxxx format)

    Raises:
        EvidenceIDError: If build_hash format is invalid

    Example:
        >>> evidence_id_for(
        ...     build_hash="a1b2c3d4e5f6",
        ...     node_id="F-withdraw-abc123",
        ...     file="Token.sol",
        ...     line_start=42,
        ...     line_end=45,
        ...     semantic_op="TRANSFERS_VALUE_OUT"
        ... )
        'EVD-7e3f2a1c'
    """
    # Validate build hash
    if not BUILD_HASH_PATTERN.match(build_hash):
        raise EvidenceIDError(
            f"Invalid build_hash format: {build_hash} (expected {BUILD_HASH_LENGTH} hex chars)"
        )

    # Normalize line_end
    if line_end is None:
        line_end = line_start

    # Build deterministic content string
    # Order: build_hash, node_id, file, line_start, line_end, column, semantic_op
    content_parts = [
        build_hash,
        node_id,
        file,
        str(line_start),
        str(line_end),
        str(column),
    ]

    # Only include semantic_op if provided (for backward compatibility)
    if semantic_op:
        content_parts.append(semantic_op)

    content = ":".join(content_parts)
    hash_val = hashlib.sha256(content.encode()).hexdigest()[:8]
    return f"EVD-{hash_val}"


def evidence_id_for_evidence(
    build_hash: str,
    node_id: str,
    evidence: "Evidence",
    semantic_op: Optional[str] = None,
) -> str:
    """Generate evidence ID from an Evidence dataclass.

    Convenience function that extracts fields from Evidence object.

    Args:
        build_hash: 12-char graph build hash
        node_id: Graph node or edge ID
        evidence: Evidence dataclass with file/line info
        semantic_op: Optional semantic operation name

    Returns:
        Deterministic evidence ID
    """
    return evidence_id_for(
        build_hash=build_hash,
        node_id=node_id,
        file=evidence.file,
        line_start=evidence.line_start or 1,
        line_end=evidence.line_end,
        semantic_op=semantic_op,
    )


def evidence_ids_for_node(
    build_hash: str,
    node_id: str,
    evidence_list: Sequence["Evidence"],
    semantic_op: Optional[str] = None,
) -> List[str]:
    """Generate evidence IDs for all evidence items in a node.

    Args:
        build_hash: 12-char graph build hash
        node_id: Graph node ID
        evidence_list: List of Evidence objects
        semantic_op: Optional semantic operation name

    Returns:
        List of evidence IDs (preserves order, includes duplicates)
    """
    return [
        evidence_id_for_evidence(build_hash, node_id, e, semantic_op)
        for e in evidence_list
    ]


@dataclass(frozen=True)
class CanonicalEvidenceID:
    """Canonical evidence identifier with full provenance.

    This class captures all components used to generate an evidence ID,
    enabling resolution back to source locations and reproducibility checks.

    Unlike the simple evidence_id_for() function, this class preserves
    the original inputs for later resolution.
    """

    build_hash: str
    node_id: str
    file: str
    line_start: int
    line_end: int
    column: int = 0
    semantic_op: Optional[str] = None
    id: str = field(init=False)

    def __post_init__(self) -> None:
        """Compute the deterministic evidence ID."""
        if not BUILD_HASH_PATTERN.match(self.build_hash):
            raise EvidenceIDError(
                f"Invalid build_hash format: {self.build_hash} (expected {BUILD_HASH_LENGTH} hex chars)"
            )

        computed_id = evidence_id_for(
            build_hash=self.build_hash,
            node_id=self.node_id,
            file=self.file,
            line_start=self.line_start,
            line_end=self.line_end,
            semantic_op=self.semantic_op,
            column=self.column,
        )
        object.__setattr__(self, "id", computed_id)

    def __str__(self) -> str:
        """Return the evidence ID string."""
        return self.id

    def __hash__(self) -> int:
        """Hash based on ID for use in sets/dicts."""
        return hash(self.id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns v2 contract-compatible evidence_ref format.
        """
        result: Dict[str, Any] = {
            "file": self.file,
            "line": self.line_start,
            "node_id": self.node_id,
            "snippet_id": self.id,
            "build_hash": self.build_hash,
        }
        if self.line_end != self.line_start:
            result["line_end"] = self.line_end
        if self.column > 0:
            result["column"] = self.column
        if self.semantic_op:
            result["semantic_op"] = self.semantic_op
        return result

    @classmethod
    def from_evidence(
        cls,
        build_hash: str,
        node_id: str,
        evidence: "Evidence",
        semantic_op: Optional[str] = None,
    ) -> "CanonicalEvidenceID":
        """Create from Evidence dataclass.

        Args:
            build_hash: 12-char graph build hash
            node_id: Graph node or edge ID
            evidence: Evidence dataclass
            semantic_op: Optional semantic operation

        Returns:
            CanonicalEvidenceID instance
        """
        return cls(
            build_hash=build_hash,
            node_id=node_id,
            file=evidence.file,
            line_start=evidence.line_start or 1,
            line_end=evidence.line_end or evidence.line_start or 1,
            semantic_op=semantic_op,
        )


class EvidenceIDRegistry:
    """Registry for tracking evidence IDs within a graph build.

    Maintains bidirectional mapping between evidence IDs and their
    source locations. Used for validation and resolution during
    evidence gating.

    This extends EvidenceRegistry from llm.evidence_ids with
    semantic operation support and bulk registration.
    """

    def __init__(self, build_hash: str) -> None:
        """Initialize registry.

        Args:
            build_hash: 12-char graph build hash

        Raises:
            EvidenceIDError: If build_hash format is invalid
        """
        if not BUILD_HASH_PATTERN.match(build_hash):
            raise EvidenceIDError(
                f"Invalid build_hash format: {build_hash} (expected {BUILD_HASH_LENGTH} hex chars)"
            )

        self.build_hash = build_hash
        self._registry: Dict[str, CanonicalEvidenceID] = {}
        self._by_node: Dict[str, List[str]] = {}  # node_id -> [evidence_ids]

    def register(
        self,
        node_id: str,
        file: str,
        line_start: int,
        line_end: Optional[int] = None,
        semantic_op: Optional[str] = None,
        column: int = 0,
    ) -> CanonicalEvidenceID:
        """Register evidence and return its canonical ID.

        Args:
            node_id: Graph node or edge ID
            file: Source file path
            line_start: Starting line number
            line_end: Ending line number (optional)
            semantic_op: Semantic operation (optional)
            column: Column number (default 0)

        Returns:
            CanonicalEvidenceID with deterministic ID
        """
        evidence = CanonicalEvidenceID(
            build_hash=self.build_hash,
            node_id=node_id,
            file=file,
            line_start=line_start,
            line_end=line_end or line_start,
            column=column,
            semantic_op=semantic_op,
        )

        self._registry[evidence.id] = evidence

        if node_id not in self._by_node:
            self._by_node[node_id] = []
        if evidence.id not in self._by_node[node_id]:
            self._by_node[node_id].append(evidence.id)

        return evidence

    def register_evidence(
        self,
        node_id: str,
        evidence: "Evidence",
        semantic_op: Optional[str] = None,
    ) -> CanonicalEvidenceID:
        """Register from Evidence dataclass.

        Args:
            node_id: Graph node or edge ID
            evidence: Evidence dataclass
            semantic_op: Optional semantic operation

        Returns:
            CanonicalEvidenceID
        """
        return self.register(
            node_id=node_id,
            file=evidence.file,
            line_start=evidence.line_start or 1,
            line_end=evidence.line_end,
            semantic_op=semantic_op,
        )

    def resolve(self, evidence_id: str) -> CanonicalEvidenceID:
        """Resolve evidence ID to its full provenance.

        Args:
            evidence_id: Evidence ID string (EVD-xxxxxxxx)

        Returns:
            CanonicalEvidenceID with full source location

        Raises:
            EvidenceResolutionError: If ID not found or invalid format
        """
        if not EVIDENCE_ID_PATTERN.match(evidence_id):
            raise EvidenceResolutionError(f"Invalid evidence ID format: {evidence_id}")

        if evidence_id not in self._registry:
            raise EvidenceResolutionError(
                f"Evidence ID {evidence_id} not found in registry"
            )

        return self._registry[evidence_id]

    def get(self, evidence_id: str) -> Optional[CanonicalEvidenceID]:
        """Get evidence by ID, returning None if not found.

        Args:
            evidence_id: Evidence ID string

        Returns:
            CanonicalEvidenceID or None
        """
        return self._registry.get(evidence_id)

    def contains(self, evidence_id: str) -> bool:
        """Check if evidence ID is registered.

        Args:
            evidence_id: Evidence ID string

        Returns:
            True if registered
        """
        return evidence_id in self._registry

    def get_by_node(self, node_id: str) -> List[CanonicalEvidenceID]:
        """Get all evidence for a specific node.

        Args:
            node_id: Graph node ID

        Returns:
            List of CanonicalEvidenceID objects for the node
        """
        evidence_ids = self._by_node.get(node_id, [])
        return [self._registry[eid] for eid in evidence_ids if eid in self._registry]

    def all_ids(self) -> List[str]:
        """Return all registered evidence IDs."""
        return list(self._registry.keys())

    def count(self) -> int:
        """Return count of registered evidence."""
        return len(self._registry)

    def to_evidence_refs(self) -> List[Dict[str, Any]]:
        """Export all evidence as v2 contract evidence_refs.

        Returns:
            List of evidence reference dictionaries
        """
        return [e.to_dict() for e in self._registry.values()]


def compute_evidence_id_deterministic(
    build_hash: str,
    node_id: str,
    file: str,
    line_start: int,
    line_end: Optional[int] = None,
    semantic_op: Optional[str] = None,
) -> str:
    """Alias for evidence_id_for() - explicit naming for determinism contracts.

    This function name explicitly indicates deterministic behavior for
    use in contracts and tests.
    """
    return evidence_id_for(
        build_hash=build_hash,
        node_id=node_id,
        file=file,
        line_start=line_start,
        line_end=line_end,
        semantic_op=semantic_op,
    )


__all__ = [
    # Primary function
    "evidence_id_for",
    "evidence_id_for_evidence",
    "evidence_ids_for_node",
    "compute_evidence_id_deterministic",
    # Classes
    "CanonicalEvidenceID",
    "EvidenceIDRegistry",
    # Re-exports from llm.evidence_ids
    "EvidenceIDError",
    "EvidenceResolutionError",
    "SourceSpan",
    "EvidenceRegistry",
    "validate_evidence_id",
    "validate_build_hash",
    # Re-exports from graph_hash
    "compute_graph_hash",
    "extract_build_hash",
    "BUILD_HASH_LENGTH",
    # Patterns
    "EVIDENCE_ID_PATTERN",
    "BUILD_HASH_PATTERN",
]
