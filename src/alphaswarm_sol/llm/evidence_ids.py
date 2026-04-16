"""Deterministic Evidence ID Generator and Resolver.

This module provides deterministic evidence references tied to graph build hashes.
All evidence IDs are reproducible and can be resolved back to source locations.

Key responsibilities:
1. Generate deterministic evidence IDs from build hash + node + span
2. Resolve evidence IDs back to source locations
3. Provide helpers for clause matrix and evidence_refs construction
4. Validate evidence ID format and build hash consistency

Reference: docs/reference/graph-interface-v2.md
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# Evidence ID format: EVD-<8-hex-chars>
EVIDENCE_ID_PATTERN = re.compile(r"^EVD-[0-9a-f]{8}$")

# Build hash format: 12 hex characters
BUILD_HASH_PATTERN = re.compile(r"^[0-9a-f]{12}$")


class EvidenceIDError(Exception):
    """Raised when evidence ID operations fail."""

    pass


class EvidenceResolutionError(Exception):
    """Raised when evidence resolution fails."""

    pass


@dataclass(frozen=True)
class SourceSpan:
    """Source code span for evidence references.

    Represents a range in source code that can be uniquely identified.
    """

    file: str
    line_start: int
    line_end: Optional[int] = None
    column_start: int = 0
    column_end: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate span parameters."""
        if self.line_start < 1:
            raise ValueError(f"line_start must be >= 1, got {self.line_start}")
        if self.line_end is not None and self.line_end < self.line_start:
            raise ValueError(
                f"line_end ({self.line_end}) cannot be before line_start ({self.line_start})"
            )
        if self.column_start < 0:
            raise ValueError(f"column_start must be >= 0, got {self.column_start}")

    @property
    def line(self) -> int:
        """Primary line number (1-indexed)."""
        return self.line_start

    @property
    def column(self) -> int:
        """Primary column number (0-indexed)."""
        return self.column_start

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result: Dict[str, Any] = {
            "file": self.file,
            "line": self.line_start,
        }
        if self.line_end is not None and self.line_end != self.line_start:
            result["line_end"] = self.line_end
        if self.column_start > 0:
            result["column"] = self.column_start
        if self.column_end is not None:
            result["column_end"] = self.column_end
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceSpan":
        """Create from dictionary representation."""
        return cls(
            file=str(data.get("file", "")),
            line_start=int(data.get("line", data.get("line_start", 1))),
            line_end=data.get("line_end"),
            column_start=int(data.get("column", data.get("column_start", 0))),
            column_end=data.get("column_end"),
        )


@dataclass(frozen=True)
class EvidenceID:
    """Deterministic evidence identifier.

    Evidence IDs are computed from:
    - build_hash: 12-char graph build hash
    - node_id: Graph node identifier
    - span: Source code span

    The ID format is EVD-<8-hex>, where the hex is derived from SHA256.
    """

    build_hash: str
    node_id: str
    span: SourceSpan
    id: str = field(init=False)

    def __post_init__(self) -> None:
        """Compute the deterministic evidence ID."""
        # Validate build hash
        if not BUILD_HASH_PATTERN.match(self.build_hash):
            raise EvidenceIDError(
                f"Invalid build_hash format: {self.build_hash} (expected 12 hex chars)"
            )

        # Compute deterministic ID
        content = (
            f"{self.build_hash}:{self.node_id}:{self.span.line}:{self.span.column}"
        )
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:8]
        object.__setattr__(self, "id", f"EVD-{hash_val}")

    def __str__(self) -> str:
        """Return the evidence ID string."""
        return self.id

    def to_dict(self) -> Dict[str, Any]:
        """Convert to evidence_ref dictionary format for v2 contract."""
        result: Dict[str, Any] = {
            "file": self.span.file,
            "line": self.span.line,
            "node_id": self.node_id,
            "snippet_id": self.id,
            "build_hash": self.build_hash,
        }
        if self.span.column > 0:
            result["column"] = self.span.column
        return result


@dataclass
class EvidenceRegistry:
    """Registry for tracking and resolving evidence IDs.

    Maintains a mapping from evidence IDs back to their source locations.
    Used for validation and resolution.
    """

    build_hash: str
    _registry: Dict[str, EvidenceID] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate build hash."""
        if not BUILD_HASH_PATTERN.match(self.build_hash):
            raise EvidenceIDError(
                f"Invalid build_hash format: {self.build_hash} (expected 12 hex chars)"
            )

    def register(self, node_id: str, span: SourceSpan) -> EvidenceID:
        """Register an evidence reference and return its ID.

        Args:
            node_id: Graph node identifier
            span: Source code span

        Returns:
            EvidenceID with deterministic ID
        """
        evidence = EvidenceID(
            build_hash=self.build_hash,
            node_id=node_id,
            span=span,
        )
        self._registry[evidence.id] = evidence
        return evidence

    def resolve(self, evidence_id: str) -> EvidenceID:
        """Resolve an evidence ID back to its components.

        Args:
            evidence_id: Evidence ID string (EVD-xxxxxxxx)

        Returns:
            EvidenceID with full source location

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

    def get(self, evidence_id: str) -> Optional[EvidenceID]:
        """Get evidence by ID, returning None if not found.

        Args:
            evidence_id: Evidence ID string

        Returns:
            EvidenceID or None
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

    def all_ids(self) -> List[str]:
        """Return all registered evidence IDs."""
        return list(self._registry.keys())

    def count(self) -> int:
        """Return count of registered evidence."""
        return len(self._registry)


def generate_evidence_id(
    build_hash: str, node_id: str, line: int, column: int = 0
) -> str:
    """Generate deterministic evidence ID.

    This is a convenience function for simple cases. For full functionality,
    use EvidenceID directly.

    Format: EVD-<hash-8>
    Where hash = SHA256(build_hash:node_id:line:column)[:8]

    Args:
        build_hash: 12-char graph build hash
        node_id: Graph node identifier
        line: Line number (1-indexed)
        column: Column number (0-indexed, default 0)

    Returns:
        Deterministic evidence ID (EVD-xxxxxxxx)
    """
    content = f"{build_hash}:{node_id}:{line}:{column}"
    hash_val = hashlib.sha256(content.encode()).hexdigest()[:8]
    return f"EVD-{hash_val}"


def validate_evidence_id(evidence_id: str) -> bool:
    """Validate evidence ID format.

    Args:
        evidence_id: Evidence ID string to validate

    Returns:
        True if valid format
    """
    return EVIDENCE_ID_PATTERN.match(evidence_id) is not None


def validate_build_hash(build_hash: str) -> bool:
    """Validate build hash format.

    Args:
        build_hash: Build hash string to validate

    Returns:
        True if valid format (12 hex chars)
    """
    return BUILD_HASH_PATTERN.match(build_hash) is not None


def parse_evidence_id(evidence_id: str) -> Tuple[str, str]:
    """Parse evidence ID into prefix and hash components.

    Args:
        evidence_id: Evidence ID string (EVD-xxxxxxxx)

    Returns:
        Tuple of (prefix, hash) e.g. ("EVD", "a1b2c3d4")

    Raises:
        EvidenceIDError: If invalid format
    """
    if not validate_evidence_id(evidence_id):
        raise EvidenceIDError(f"Invalid evidence ID format: {evidence_id}")

    prefix, hash_part = evidence_id.split("-", 1)
    return prefix, hash_part


# ============================================================================
# Clause Matrix Helpers
# ============================================================================


@dataclass
class ClauseEvidence:
    """Evidence for a single pattern clause.

    Used to build clause_matrix entries in v2 contract format.
    """

    clause_id: str
    status: str  # "matched" | "failed" | "unknown"
    evidence_refs: List[EvidenceID] = field(default_factory=list)
    omission_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate status value."""
        valid_statuses = {"matched", "failed", "unknown"}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status: {self.status}, must be one of {valid_statuses}")

    def to_dict(self, build_hash: str) -> Dict[str, Any]:
        """Convert to clause_matrix entry format.

        Args:
            build_hash: Build hash to include in evidence refs

        Returns:
            Clause matrix entry dictionary
        """
        return {
            "clause": self.clause_id,
            "status": self.status,
            "evidence_refs": [e.to_dict() for e in self.evidence_refs],
            "omission_refs": self.omission_refs,
        }


class ClauseMatrixBuilder:
    """Builder for constructing clause matrix entries.

    Helps ensure all clauses have proper evidence or omission linkage.
    """

    def __init__(self, registry: EvidenceRegistry) -> None:
        """Initialize builder.

        Args:
            registry: Evidence registry for ID generation
        """
        self.registry = registry
        self._clauses: Dict[str, ClauseEvidence] = {}

    def add_matched(
        self,
        clause_id: str,
        node_id: str,
        span: SourceSpan,
        *,
        extra_refs: Optional[List[Tuple[str, SourceSpan]]] = None,
    ) -> EvidenceID:
        """Add a matched clause with evidence.

        Args:
            clause_id: Clause identifier (e.g., "reentrancy-classic:all:0")
            node_id: Graph node that provides evidence
            span: Source span for the evidence
            extra_refs: Additional evidence references (node_id, span) tuples

        Returns:
            Primary EvidenceID created
        """
        primary = self.registry.register(node_id, span)
        evidence_refs = [primary]

        if extra_refs:
            for extra_node, extra_span in extra_refs:
                evidence_refs.append(self.registry.register(extra_node, extra_span))

        self._clauses[clause_id] = ClauseEvidence(
            clause_id=clause_id,
            status="matched",
            evidence_refs=evidence_refs,
        )
        return primary

    def add_failed(
        self,
        clause_id: str,
        node_id: Optional[str] = None,
        span: Optional[SourceSpan] = None,
        *,
        reason: Optional[str] = None,
    ) -> None:
        """Add a failed clause.

        Args:
            clause_id: Clause identifier
            node_id: Optional node that shows failure
            span: Optional source span
            reason: Optional reason for failure (goes in omission_refs)
        """
        evidence_refs = []
        if node_id and span:
            evidence_refs.append(self.registry.register(node_id, span))

        omission_refs = [reason] if reason else []

        self._clauses[clause_id] = ClauseEvidence(
            clause_id=clause_id,
            status="failed",
            evidence_refs=evidence_refs,
            omission_refs=omission_refs,
        )

    def add_unknown(
        self,
        clause_id: str,
        omission_reason: str,
        *,
        extra_reasons: Optional[List[str]] = None,
    ) -> None:
        """Add an unknown clause with omission reason.

        Args:
            clause_id: Clause identifier
            omission_reason: Primary reason for unknown status
            extra_reasons: Additional omission reasons
        """
        omission_refs = [omission_reason]
        if extra_reasons:
            omission_refs.extend(extra_reasons)

        self._clauses[clause_id] = ClauseEvidence(
            clause_id=clause_id,
            status="unknown",
            evidence_refs=[],
            omission_refs=omission_refs,
        )

    def build(self) -> List[Dict[str, Any]]:
        """Build the clause matrix.

        Returns:
            List of clause matrix entries in v2 contract format
        """
        return [
            clause.to_dict(self.registry.build_hash)
            for clause in self._clauses.values()
        ]

    def get_clause_lists(
        self,
    ) -> Tuple[List[str], List[str], List[str]]:
        """Get matched, failed, and unknown clause lists.

        Returns:
            Tuple of (matched_clauses, failed_clauses, unknown_clauses)
        """
        matched = []
        failed = []
        unknown = []

        for clause_id, clause in self._clauses.items():
            if clause.status == "matched":
                matched.append(clause_id)
            elif clause.status == "failed":
                failed.append(clause_id)
            else:
                unknown.append(clause_id)

        return matched, failed, unknown

    def get_all_evidence_refs(self) -> List[Dict[str, Any]]:
        """Get all evidence refs across all clauses (for finding-level evidence_refs).

        Returns:
            Deduplicated list of evidence_ref dictionaries
        """
        seen: set[str] = set()
        refs = []

        for clause in self._clauses.values():
            for evidence in clause.evidence_refs:
                if evidence.id not in seen:
                    seen.add(evidence.id)
                    refs.append(evidence.to_dict())

        return refs


# ============================================================================
# Evidence Ref Construction Helpers
# ============================================================================


def build_evidence_ref(
    build_hash: str,
    node_id: str,
    file: str,
    line: int,
    column: int = 0,
    snippet: Optional[str] = None,
) -> Dict[str, Any]:
    """Build an evidence_ref dictionary for v2 contract.

    Args:
        build_hash: 12-char graph build hash
        node_id: Graph node identifier
        file: Source file path
        line: Line number (1-indexed)
        column: Column number (0-indexed)
        snippet: Optional code snippet (max 200 chars)

    Returns:
        Evidence reference dictionary
    """
    ref: Dict[str, Any] = {
        "file": file,
        "line": line,
        "node_id": node_id,
        "snippet_id": generate_evidence_id(build_hash, node_id, line, column),
        "build_hash": build_hash,
    }
    if column > 0:
        ref["column"] = column
    if snippet:
        ref["snippet"] = snippet[:200]
    return ref


def build_evidence_refs_from_nodes(
    build_hash: str,
    nodes: List[Dict[str, Any]],
    file_key: str = "file",
    line_key: str = "line",
    node_id_key: str = "id",
) -> List[Dict[str, Any]]:
    """Build evidence_refs from a list of node dictionaries.

    Args:
        build_hash: 12-char graph build hash
        nodes: List of node dictionaries with file/line info
        file_key: Key for file path in node dict
        line_key: Key for line number in node dict
        node_id_key: Key for node ID in node dict

    Returns:
        List of evidence reference dictionaries
    """
    refs = []
    for node in nodes:
        file = node.get(file_key, "")
        line = node.get(line_key, 0)
        node_id = node.get(node_id_key, "")

        if file and line > 0 and node_id:
            refs.append(
                build_evidence_ref(
                    build_hash=build_hash,
                    node_id=node_id,
                    file=file,
                    line=line,
                )
            )

    return refs


__all__ = [
    # Core classes
    "EvidenceID",
    "EvidenceRegistry",
    "SourceSpan",
    # Clause matrix helpers
    "ClauseEvidence",
    "ClauseMatrixBuilder",
    # Functions
    "generate_evidence_id",
    "validate_evidence_id",
    "validate_build_hash",
    "parse_evidence_id",
    "build_evidence_ref",
    "build_evidence_refs_from_nodes",
    # Exceptions
    "EvidenceIDError",
    "EvidenceResolutionError",
    # Constants
    "EVIDENCE_ID_PATTERN",
    "BUILD_HASH_PATTERN",
]
