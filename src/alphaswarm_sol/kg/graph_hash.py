"""Graph Build Hash Utility.

This module provides deterministic build hash computation for knowledge graphs.
Build hashes uniquely identify a specific graph build and are used to tie
evidence references to reproducible source locations.

Key responsibilities:
1. Compute deterministic build hash from graph content
2. Compute build hash from source files
3. Validate build hash consistency across evidence
4. Support incremental hash updates

Reference: docs/reference/graph-interface-v2.md
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from alphaswarm_sol.kg.schema import KnowledgeGraph


# Build hash format: 12 hex characters
BUILD_HASH_LENGTH = 12
BUILD_HASH_PATTERN = re.compile(r"^[0-9a-f]{12}$")


class BuildHashError(Exception):
    """Raised when build hash operations fail."""

    pass


def compute_graph_hash(
    graph: Union[Dict[str, Any], "KnowledgeGraph"],
    *,
    include_metadata: bool = True,
    canonical: bool = True,
) -> str:
    """Compute deterministic build hash from graph content.

    The hash is computed from:
    - Sorted node IDs and their core properties
    - Sorted edge IDs and their connections
    - Optionally, metadata (excludes timestamps)

    Args:
        graph: Knowledge graph (dict or KnowledgeGraph object)
        include_metadata: Whether to include metadata in hash (default True)
        canonical: Whether to sort keys for determinism (default True)

    Returns:
        12-character hex build hash
    """
    # Convert to dict if needed
    if hasattr(graph, "to_dict"):
        graph_dict = graph.to_dict()
    else:
        graph_dict = graph

    # Build canonical representation
    hash_content: Dict[str, Any] = {}

    # Include sorted node IDs and types
    nodes = graph_dict.get("nodes", [])
    if isinstance(nodes, dict):
        nodes = list(nodes.values())

    sorted_nodes = sorted(
        [(n.get("id", ""), n.get("type", ""), n.get("label", "")) for n in nodes]
    )
    hash_content["nodes"] = sorted_nodes

    # Include sorted edge IDs and connections
    edges = graph_dict.get("edges", [])
    if isinstance(edges, dict):
        edges = list(edges.values())

    sorted_edges = sorted(
        [
            (e.get("id", ""), e.get("type", ""), e.get("source", ""), e.get("target", ""))
            for e in edges
        ]
    )
    hash_content["edges"] = sorted_edges

    # Include metadata (excluding timestamps)
    if include_metadata:
        metadata = graph_dict.get("metadata", {})
        # Filter out non-deterministic fields
        filtered_metadata = {
            k: v
            for k, v in metadata.items()
            if k not in ("timestamp", "build_time", "created_at", "updated_at")
        }
        if filtered_metadata:
            hash_content["metadata"] = filtered_metadata

    # Serialize to JSON
    sort_keys = canonical
    content = json.dumps(hash_content, sort_keys=sort_keys, default=str)

    # Compute hash
    return hashlib.sha256(content.encode()).hexdigest()[:BUILD_HASH_LENGTH]


def compute_source_hash(
    sources: Union[str, Path, List[Union[str, Path]]],
    *,
    normalize_whitespace: bool = False,
) -> str:
    """Compute build hash from source file contents.

    Args:
        sources: Single file path, directory, or list of paths
        normalize_whitespace: Whether to normalize whitespace (default False)

    Returns:
        12-character hex build hash
    """
    # Normalize to list of paths
    if isinstance(sources, (str, Path)):
        sources = [sources]

    # Collect all source content
    content_parts: List[str] = []

    for source in sources:
        source_path = Path(source)

        if source_path.is_file():
            _add_file_content(source_path, content_parts, normalize_whitespace)
        elif source_path.is_dir():
            # Find all Solidity files
            for sol_file in sorted(source_path.rglob("*.sol")):
                _add_file_content(sol_file, content_parts, normalize_whitespace)
        else:
            raise BuildHashError(f"Source not found: {source_path}")

    if not content_parts:
        raise BuildHashError("No source content found")

    # Join with delimiter for determinism
    combined = "\n---FILE_BOUNDARY---\n".join(content_parts)

    return hashlib.sha256(combined.encode()).hexdigest()[:BUILD_HASH_LENGTH]


def _add_file_content(
    file_path: Path,
    content_parts: List[str],
    normalize_whitespace: bool,
) -> None:
    """Add file content to the content parts list.

    Args:
        file_path: Path to file
        content_parts: List to append content to
        normalize_whitespace: Whether to normalize whitespace
    """
    content = file_path.read_text(encoding="utf-8")

    if normalize_whitespace:
        # Normalize line endings and collapse multiple blank lines
        content = content.replace("\r\n", "\n")
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = content.strip()

    # Include relative path in content for disambiguation
    content_parts.append(f"// File: {file_path.name}\n{content}")


def compute_content_hash(content: str) -> str:
    """Compute build hash from raw content string.

    Useful for computing hash from concatenated sources.

    Args:
        content: Source content string

    Returns:
        12-character hex build hash
    """
    return hashlib.sha256(content.encode()).hexdigest()[:BUILD_HASH_LENGTH]


def compute_incremental_hash(
    base_hash: str,
    additional_content: str,
) -> str:
    """Compute incremental hash by combining base hash with new content.

    Useful for updating hash when sources change.

    Args:
        base_hash: Existing build hash
        additional_content: New content to incorporate

    Returns:
        12-character hex build hash
    """
    if not validate_build_hash(base_hash):
        raise BuildHashError(f"Invalid base hash: {base_hash}")

    combined = f"{base_hash}:{additional_content}"
    return hashlib.sha256(combined.encode()).hexdigest()[:BUILD_HASH_LENGTH]


def validate_build_hash(build_hash: str) -> bool:
    """Validate build hash format.

    Args:
        build_hash: Build hash string to validate

    Returns:
        True if valid format (12 hex chars)
    """
    return BUILD_HASH_PATTERN.match(build_hash) is not None


def validate_build_hash_strict(build_hash: str) -> None:
    """Validate build hash format, raising on invalid.

    Args:
        build_hash: Build hash string to validate

    Raises:
        BuildHashError: If invalid format
    """
    if not validate_build_hash(build_hash):
        raise BuildHashError(
            f"Invalid build hash format: {build_hash} (expected {BUILD_HASH_LENGTH} hex chars)"
        )


def check_build_hash_consistency(
    expected_hash: str,
    evidence_refs: List[Dict[str, Any]],
) -> List[str]:
    """Check that all evidence refs have consistent build hash.

    Args:
        expected_hash: Expected build hash
        evidence_refs: List of evidence reference dictionaries

    Returns:
        List of inconsistency error messages (empty if consistent)
    """
    errors: List[str] = []

    for i, ref in enumerate(evidence_refs):
        ref_hash = ref.get("build_hash", "")
        if ref_hash and ref_hash != expected_hash:
            errors.append(
                f"evidence_refs[{i}]: build_hash mismatch "
                f"(got {ref_hash}, expected {expected_hash})"
            )

    return errors


def embed_build_hash(
    graph_dict: Dict[str, Any],
    build_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """Embed build hash into graph metadata.

    If no hash is provided, computes one from the graph.

    Args:
        graph_dict: Graph dictionary to update
        build_hash: Optional pre-computed hash

    Returns:
        Updated graph dictionary with build_hash in metadata
    """
    if build_hash is None:
        build_hash = compute_graph_hash(graph_dict)

    # Ensure metadata exists
    if "metadata" not in graph_dict:
        graph_dict["metadata"] = {}

    graph_dict["metadata"]["build_hash"] = build_hash

    return graph_dict


def extract_build_hash(
    graph: Union[Dict[str, Any], "KnowledgeGraph"],
    *,
    compute_if_missing: bool = False,
) -> Optional[str]:
    """Extract build hash from graph metadata.

    Args:
        graph: Knowledge graph
        compute_if_missing: Whether to compute hash if not present

    Returns:
        Build hash string or None
    """
    if hasattr(graph, "metadata"):
        metadata = graph.metadata
    elif isinstance(graph, dict):
        metadata = graph.get("metadata", {})
    else:
        metadata = {}

    build_hash = metadata.get("build_hash")

    if build_hash is None and compute_if_missing:
        build_hash = compute_graph_hash(graph)

    return build_hash


class BuildHashTracker:
    """Tracks build hashes across graph operations.

    Useful for maintaining hash consistency during graph construction
    and modification.
    """

    def __init__(self, initial_hash: Optional[str] = None) -> None:
        """Initialize tracker.

        Args:
            initial_hash: Optional initial build hash
        """
        self._current_hash = initial_hash
        self._history: List[str] = []

    @property
    def current(self) -> Optional[str]:
        """Get current build hash."""
        return self._current_hash

    @property
    def history(self) -> List[str]:
        """Get hash history."""
        return list(self._history)

    def set(self, build_hash: str) -> None:
        """Set current build hash.

        Args:
            build_hash: New build hash

        Raises:
            BuildHashError: If invalid format
        """
        validate_build_hash_strict(build_hash)

        if self._current_hash is not None:
            self._history.append(self._current_hash)

        self._current_hash = build_hash

    def update_from_graph(
        self,
        graph: Union[Dict[str, Any], "KnowledgeGraph"],
    ) -> str:
        """Update hash from graph content.

        Args:
            graph: Knowledge graph

        Returns:
            New build hash
        """
        new_hash = compute_graph_hash(graph)
        self.set(new_hash)
        return new_hash

    def update_from_sources(
        self,
        sources: Union[str, Path, List[Union[str, Path]]],
    ) -> str:
        """Update hash from source files.

        Args:
            sources: Source files or directory

        Returns:
            New build hash
        """
        new_hash = compute_source_hash(sources)
        self.set(new_hash)
        return new_hash

    def validate_consistent(self, build_hash: str) -> bool:
        """Check if a build hash matches current.

        Args:
            build_hash: Hash to check

        Returns:
            True if matches current hash
        """
        return self._current_hash == build_hash


__all__ = [
    # Core functions
    "compute_graph_hash",
    "compute_source_hash",
    "compute_content_hash",
    "compute_incremental_hash",
    # Validation
    "validate_build_hash",
    "validate_build_hash_strict",
    "check_build_hash_consistency",
    # Embedding/extraction
    "embed_build_hash",
    "extract_build_hash",
    # Tracker class
    "BuildHashTracker",
    # Exceptions
    "BuildHashError",
    # Constants
    "BUILD_HASH_LENGTH",
    "BUILD_HASH_PATTERN",
]
