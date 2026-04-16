"""
Graph Version Tracking

Tracks knowledge graph versions for staleness detection and reproducibility.

Version Schema:
- version_id: Human-readable ID (e.g., "v1-abc123")
- fingerprint: SHA256 hash of normalized graph structure
- code_hash: SHA256 hash of source files
- created_at: Timestamp of version creation
- source_files: List of analyzed source files
- slither_version: Version of Slither used
- vkg_version: Version of VKG used
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


@dataclass
class GraphVersion:
    """
    Version identifier for a knowledge graph.

    Attributes:
        version_id: Human-readable version ID (e.g., "v1-abc12345")
        fingerprint: SHA256 hash of the normalized graph
        code_hash: SHA256 hash of the source files
        created_at: When this version was created
        source_files: List of source file paths analyzed
        slither_version: Slither version used for analysis
        vkg_version: VKG version used for analysis
        metadata: Additional version metadata
    """

    version_id: str
    fingerprint: str
    code_hash: str
    created_at: datetime
    source_files: List[str] = field(default_factory=list)
    slither_version: Optional[str] = None
    vkg_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "version_id": self.version_id,
            "fingerprint": self.fingerprint,
            "code_hash": self.code_hash,
            "created_at": self.created_at.isoformat(),
            "source_files": self.source_files,
            "slither_version": self.slither_version,
            "vkg_version": self.vkg_version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphVersion":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        return cls(
            version_id=data.get("version_id", "unknown"),
            fingerprint=data.get("fingerprint", ""),
            code_hash=data.get("code_hash", ""),
            created_at=created_at,
            source_files=data.get("source_files", []),
            slither_version=data.get("slither_version"),
            vkg_version=data.get("vkg_version"),
            metadata=data.get("metadata", {}),
        )

    @property
    def short_id(self) -> str:
        """Get shortened version ID for display."""
        return self.version_id

    def __eq__(self, other: object) -> bool:
        """Two versions are equal if their fingerprints match."""
        if not isinstance(other, GraphVersion):
            return False
        return self.fingerprint == other.fingerprint

    def __hash__(self) -> int:
        """Hash based on fingerprint."""
        return hash(self.fingerprint)


class VersionGenerator:
    """
    Generates deterministic versions for knowledge graphs.

    The version ID is human-readable and includes a counter and
    fingerprint prefix. The fingerprint is a deterministic SHA256
    hash of the normalized graph structure.
    """

    def __init__(self, counter_start: int = 0):
        """
        Initialize generator.

        Args:
            counter_start: Starting value for version counter
        """
        self._counter = counter_start

    def generate(
        self,
        graph: Any,
        source_files: Optional[List[Union[str, Path]]] = None,
        slither_version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GraphVersion:
        """
        Generate version for a knowledge graph.

        Args:
            graph: Knowledge graph object (must have to_dict or nodes/edges)
            source_files: List of source file paths
            slither_version: Slither version used
            metadata: Additional metadata to store

        Returns:
            GraphVersion with deterministic identifiers
        """
        source_files = source_files or []
        paths = [Path(f) if isinstance(f, str) else f for f in source_files]

        # Generate fingerprint (deterministic hash of graph)
        fingerprint = self._hash_graph(graph)

        # Generate code hash (hash of source files)
        code_hash = self._hash_files(paths)

        # Generate version ID
        self._counter += 1
        short_fp = fingerprint[:8]
        version_id = f"v{self._counter}-{short_fp}"

        return GraphVersion(
            version_id=version_id,
            fingerprint=fingerprint,
            code_hash=code_hash,
            created_at=datetime.now(),
            source_files=[str(f) for f in paths],
            slither_version=slither_version,
            vkg_version=self._get_vkg_version(),
            metadata=metadata or {},
        )

    def _hash_graph(self, graph: Any) -> str:
        """
        Generate deterministic SHA256 hash of graph.

        Normalizes the graph to a canonical JSON representation
        before hashing to ensure determinism.
        """
        try:
            # Try to_dict method
            if hasattr(graph, "to_dict"):
                data = graph.to_dict()
            # Try nodes/edges attributes
            elif hasattr(graph, "nodes") and hasattr(graph, "edges"):
                nodes = graph.nodes
                edges = graph.edges

                # Handle dict-like or list-like nodes
                if isinstance(nodes, dict):
                    node_list = []
                    for k, v in sorted(nodes.items()):
                        if hasattr(v, "to_dict"):
                            node_list.append(v.to_dict())
                        else:
                            node_list.append({"id": k, "value": str(v)})
                else:
                    node_list = sorted(
                        [n.to_dict() if hasattr(n, "to_dict") else str(n) for n in nodes],
                        key=str,
                    )

                # Handle edges similarly
                if isinstance(edges, dict):
                    edge_list = []
                    for k, v in sorted(edges.items()):
                        if hasattr(v, "to_dict"):
                            edge_list.append(v.to_dict())
                        else:
                            edge_list.append({"id": k, "value": str(v)})
                else:
                    edge_list = sorted(
                        [e.to_dict() if hasattr(e, "to_dict") else str(e) for e in edges],
                        key=str,
                    )

                data = {"nodes": node_list, "edges": edge_list}
            # For dicts
            elif isinstance(graph, dict):
                data = graph
            # Fallback to string representation
            else:
                data = {"raw": str(graph)}

            # Canonical JSON (sorted keys, consistent formatting)
            canonical = json.dumps(data, sort_keys=True, default=str, ensure_ascii=True)
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        except Exception as e:
            logger.warning(f"Graph hashing failed: {e}, using string hash")
            return hashlib.sha256(str(graph).encode("utf-8")).hexdigest()

    def _hash_files(self, files: List[Path]) -> str:
        """
        Generate combined hash of source files.

        Includes file contents and paths to detect both content
        changes and file moves/renames.
        """
        hasher = hashlib.sha256()

        for f in sorted(files, key=str):
            # Include file path
            hasher.update(str(f).encode("utf-8"))

            # Include file contents if exists
            if isinstance(f, Path) and f.exists():
                try:
                    hasher.update(f.read_bytes())
                except Exception as e:
                    logger.warning(f"Could not read {f}: {e}")
                    hasher.update(f"ERROR:{e}".encode("utf-8"))

        return hasher.hexdigest()

    def _get_vkg_version(self) -> str:
        """Get current VKG version."""
        try:
            from alphaswarm_sol import __version__

            return __version__
        except (ImportError, AttributeError):
            return "unknown"

    def reset_counter(self, value: int = 0) -> None:
        """Reset the version counter."""
        self._counter = value


class VersionStore:
    """
    Persistent storage for graph versions.

    Stores versions as JSON files in a versions directory and
    maintains a pointer to the current version.
    """

    def __init__(self, vkg_dir: Union[str, Path]):
        """
        Initialize version store.

        Args:
            vkg_dir: Path to .vkg or .vrs directory
        """
        self.vkg_dir = Path(vkg_dir)
        self.versions_dir = self.vkg_dir / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = self.vkg_dir / "current_version.json"

    def save(self, version: GraphVersion) -> Path:
        """
        Save version to store and update current pointer.

        Args:
            version: GraphVersion to save

        Returns:
            Path to saved version file
        """
        # Save version file
        path = self.versions_dir / f"{version.version_id}.json"
        path.write_text(json.dumps(version.to_dict(), indent=2))

        # Update current version pointer
        pointer = {
            "current": version.version_id,
            "path": str(path),
            "updated_at": datetime.now().isoformat(),
        }
        self.current_file.write_text(json.dumps(pointer, indent=2))

        logger.debug(f"Saved version {version.version_id} to {path}")
        return path

    def load(self, version_id: str) -> Optional[GraphVersion]:
        """
        Load version by ID.

        Args:
            version_id: Version ID to load

        Returns:
            GraphVersion or None if not found
        """
        path = self.versions_dir / f"{version_id}.json"
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text())
            return GraphVersion.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load version {version_id}: {e}")
            return None

    def get_current(self) -> Optional[GraphVersion]:
        """
        Get current (most recent) version.

        Returns:
            Current GraphVersion or None
        """
        if not self.current_file.exists():
            return None

        try:
            pointer = json.loads(self.current_file.read_text())
            return self.load(pointer["current"])
        except Exception as e:
            logger.error(f"Failed to get current version: {e}")
            return None

    def set_current(self, version_id: str) -> bool:
        """
        Set current version pointer.

        Args:
            version_id: Version ID to set as current

        Returns:
            True if successful
        """
        version = self.load(version_id)
        if not version:
            return False

        pointer = {
            "current": version_id,
            "path": str(self.versions_dir / f"{version_id}.json"),
            "updated_at": datetime.now().isoformat(),
        }
        self.current_file.write_text(json.dumps(pointer, indent=2))
        return True

    def list_versions(self) -> List[GraphVersion]:
        """
        List all stored versions.

        Returns:
            List of GraphVersion sorted by creation time (newest first)
        """
        versions = []

        for path in self.versions_dir.glob("v*.json"):
            try:
                data = json.loads(path.read_text())
                versions.append(GraphVersion.from_dict(data))
            except Exception as e:
                logger.warning(f"Failed to load version from {path}: {e}")

        return sorted(versions, key=lambda v: v.created_at, reverse=True)

    def delete(self, version_id: str) -> bool:
        """
        Delete a version.

        Args:
            version_id: Version ID to delete

        Returns:
            True if deleted
        """
        path = self.versions_dir / f"{version_id}.json"
        if not path.exists():
            return False

        # Don't delete current version
        current = self.get_current()
        if current and current.version_id == version_id:
            logger.warning("Cannot delete current version")
            return False

        path.unlink()
        return True

    def prune(self, keep_count: int = 10) -> int:
        """
        Remove old versions, keeping most recent N.

        Args:
            keep_count: Number of versions to keep

        Returns:
            Number of versions deleted
        """
        versions = self.list_versions()
        if len(versions) <= keep_count:
            return 0

        deleted = 0
        for version in versions[keep_count:]:
            if self.delete(version.version_id):
                deleted += 1

        return deleted

    def clear(self) -> int:
        """
        Clear all versions (except current).

        Returns:
            Number of versions deleted
        """
        current = self.get_current()
        deleted = 0

        for path in self.versions_dir.glob("v*.json"):
            version_id = path.stem
            if current and version_id == current.version_id:
                continue
            path.unlink()
            deleted += 1

        return deleted
