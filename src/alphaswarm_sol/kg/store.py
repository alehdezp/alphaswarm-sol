"""Local storage for VKG graphs with per-contract isolation.

Stores each contract's graph in a hash-based subdirectory using a canonical
contract identity. Supports atomic writes, skip-if-exists caching, staleness
detection, and backward-compatible flat file fallback.

Decision references: D-2b (per-contract graph storage), D-meta (meta.json schema).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

from alphaswarm_sol.kg.schema import KnowledgeGraph
from alphaswarm_sol.kg.toon import toon_dumps, toon_loads

logger = logging.getLogger(__name__)

FORMAT_VERSION = "alphaswarm-kg-v1"


EXPECTED_SCHEMA_VERSION = 1


class CorruptGraphError(Exception):
    """Raised when a graph directory contains partial/corrupt write artifacts."""


class SchemaVersionMismatchError(Exception):
    """Raised when meta.json schema_version != expected."""

    def __init__(self, identity: str, found: int, expected: int) -> None:
        self.identity = identity
        self.found = found
        self.expected = expected
        super().__init__(
            f"[error] meta.json schema version mismatch in graph {identity}: "
            f"found {found}, expected {expected}"
        )


@dataclass
class GraphInfo:
    """Structured information about an available graph."""

    identity: str
    stem: str
    source_contract: str
    dir_path: Path
    meta: GraphMetadata


class GraphMetadata(BaseModel):
    """Pydantic model for meta.json sidecar per D-meta schema.

    This is the cross-plan interface contract between Plan 02 (producer) and
    Plan 03 (consumer). All fields are mandatory, extra fields forbidden.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int
    built_at: str
    graph_hash: str
    contract_paths: list[str]
    stem: str
    source_contract: str
    identity: str
    slither_version: str
    project_root_type: str

    @field_validator("schema_version")
    @classmethod
    def check_schema_version(cls, v: int) -> int:
        if v != 1:
            raise ValueError(f"Unsupported schema_version: {v}")
        return v

    @field_validator("identity")
    @classmethod
    def check_identity_length(cls, v: str) -> str:
        if len(v) != 12 or not all(c in "0123456789abcdef" for c in v):
            raise ValueError(f"identity must be 12 hex chars, got: {v!r}")
        return v


@dataclass
class GraphStore:
    """Persist and load knowledge graphs on disk with per-contract isolation.

    Directory layout:
        root/
          {identity}/
            graph.toon    (or graph.json)
            meta.json
          {identity2}/
            graph.toon
            meta.json
          graph.toon      (legacy flat file, backward compat)
    """

    root: Path

    def _ensure_root(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        graph: KnowledgeGraph,
        *,
        identity: str | None = None,
        meta: dict[str, Any] | None = None,
        format: Literal["toon", "json"] = "toon",
        force: bool = False,
        overwrite: bool = False,
    ) -> Path:
        """Persist knowledge graph to disk.

        When identity is provided, writes to {root}/{identity}/graph.{ext} with
        atomic tmp+rename semantics and meta.json sidecar.

        When identity is None, falls back to legacy flat file behavior for
        backward compatibility.

        Args:
            graph: Knowledge graph to save.
            identity: 12-hex-char contract identity hash. When provided, enables
                per-contract isolation.
            meta: Metadata dict for meta.json sidecar. Required when identity is set.
            format: Output format - "toon" (default) or "json" (legacy).
            force: If True, overwrite existing graph even when identity matches.
            overwrite: Legacy alias for force (backward compat).

        Returns:
            Path to saved graph file.
        """
        effective_force = force or overwrite
        self._ensure_root()

        if identity is not None:
            return self._save_isolated(graph, identity=identity, meta=meta or {},
                                       format=format, force=effective_force)
        else:
            return self._save_flat(graph, format=format, overwrite=effective_force)

    def _save_isolated(
        self,
        graph: KnowledgeGraph,
        *,
        identity: str,
        meta: dict[str, Any],
        format: Literal["toon", "json"],
        force: bool,
    ) -> Path:
        """Save graph to hash-based subdirectory with atomic writes."""
        hash_dir = self.root / identity
        hash_dir.mkdir(parents=True, exist_ok=True)

        ext = ".toon" if format == "toon" else ".json"
        target = hash_dir / f"graph{ext}"
        tmp_target = hash_dir / f"graph{ext}.tmp"

        # Skip-if-exists: return early if target already exists and not forced
        if target.exists() and not force:
            logger.info("Graph already exists at %s, skipping (use --force to rebuild)", target)
            return target

        # Build payload
        payload = {
            "format": FORMAT_VERSION,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "graph": graph.to_dict(),
        }

        # Atomic write: write to tmp, then os.replace()
        if format == "toon":
            toon_payload = {
                "format": FORMAT_VERSION,
                "saved_at": payload["saved_at"],
                "graph_json": json.dumps(payload["graph"], separators=(",", ":")),
            }
            tmp_target.write_text(toon_dumps(toon_payload), encoding="utf-8")
        else:
            tmp_target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        os.replace(str(tmp_target), str(target))

        # Write meta.json atomically
        self._write_meta(hash_dir, meta, identity)

        return target

    def _write_meta(
        self, hash_dir: Path, meta: dict[str, Any], identity: str
    ) -> None:
        """Write and validate meta.json sidecar atomically."""
        # Ensure identity is in the meta dict
        meta_with_identity = {**meta, "identity": identity}

        # Validate via Pydantic model
        validated = GraphMetadata(**meta_with_identity)

        meta_path = hash_dir / "meta.json"
        meta_tmp = hash_dir / "meta.json.tmp"

        meta_tmp.write_text(
            validated.model_dump_json(indent=2), encoding="utf-8"
        )
        os.replace(str(meta_tmp), str(meta_path))

    def _save_flat(
        self,
        graph: KnowledgeGraph,
        *,
        format: Literal["toon", "json"],
        overwrite: bool,
    ) -> Path:
        """Legacy flat file save (backward compat)."""
        payload = {
            "format": FORMAT_VERSION,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "graph": graph.to_dict(),
        }

        ext = ".toon" if format == "toon" else ".json"
        target = self.root / f"graph{ext}"

        if target.exists() and not overwrite:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            target = self.root / f"graph-{timestamp}{ext}"

        if format == "toon":
            toon_payload = {
                "format": FORMAT_VERSION,
                "saved_at": payload["saved_at"],
                "graph_json": json.dumps(payload["graph"], separators=(",", ":")),
            }
            target.write_text(toon_dumps(toon_payload), encoding="utf-8")
        else:
            target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return target

    def load(
        self,
        path: Path | None = None,
        *,
        identity: str | None = None,
    ) -> KnowledgeGraph:
        """Load knowledge graph from disk.

        Args:
            path: Explicit path to load from. Takes precedence over identity.
            identity: Contract identity hash. Loads from {root}/{identity}/graph.toon.

        Returns:
            Loaded KnowledgeGraph.

        Raises:
            CorruptGraphError: If partial write artifacts (.tmp) detected without
                a completed graph file.
            FileNotFoundError: If no graph file found.
        """
        if path is not None:
            return self._load_from_path(path)

        if identity is not None:
            return self._load_by_identity(identity)

        # Legacy: try flat files at root
        return self._load_flat()

    def _load_by_identity(self, identity: str) -> KnowledgeGraph:
        """Load graph from identity-based subdirectory."""
        hash_dir = self.root / identity

        if hash_dir.is_dir():
            # Check for corrupt state: .tmp without completed file
            self._check_corrupt(hash_dir)

            toon_path = hash_dir / "graph.toon"
            json_path = hash_dir / "graph.json"

            if toon_path.exists():
                return self._load_from_path(toon_path)
            if json_path.exists():
                return self._load_from_path(json_path)

            raise FileNotFoundError(
                f"No graph file in identity directory: {hash_dir}"
            )

        # Backward compatibility: try flat file with deprecation warning
        return self._load_flat_with_deprecation()

    def _load_flat(self) -> KnowledgeGraph:
        """Load from flat files at root (no identity)."""
        toon_path = self.root / "graph.toon"
        json_path = self.root / "graph.json"
        path = toon_path if toon_path.exists() else json_path
        return self._load_from_path(path)

    def _load_flat_with_deprecation(self) -> KnowledgeGraph:
        """Load from flat file with deprecation warning."""
        toon_path = self.root / "graph.toon"
        json_path = self.root / "graph.json"

        if toon_path.exists() or json_path.exists():
            logger.warning(
                "Loading from legacy flat graph file. "
                "Please rebuild with 'alphaswarm build-kg' for per-contract isolation."
            )
            path = toon_path if toon_path.exists() else json_path
            return self._load_from_path(path)

        raise FileNotFoundError(
            f"No graph found at {self.root}. "
            "Run 'alphaswarm build-kg <path>' first."
        )

    def _check_corrupt(self, directory: Path) -> None:
        """Check for partial write artifacts indicating corruption."""
        for tmp_file in directory.glob("*.tmp"):
            # A .tmp without a corresponding completed file means interrupted write
            completed_name = tmp_file.name.removesuffix(".tmp")
            completed_path = directory / completed_name
            if not completed_path.exists():
                raise CorruptGraphError(
                    f"Partial write detected: {tmp_file} exists without {completed_path}. "
                    "The previous build was interrupted. "
                    "Remove the .tmp file and rebuild with --force."
                )

    def _load_from_path(self, path: Path) -> KnowledgeGraph:
        """Load graph from an explicit file path."""
        content = path.read_text(encoding="utf-8")

        if path.suffix == ".toon":
            data = toon_loads(content)
            graph_json = data.get("graph_json")
            graph_data: dict[str, Any] = json.loads(graph_json) if graph_json else {}
        else:
            data = json.loads(content)
            graph_data = data.get("graph") or {}
        return KnowledgeGraph.from_dict(graph_data)

    def load_meta(self, identity: str) -> GraphMetadata | None:
        """Load meta.json for a given identity.

        Args:
            identity: Contract identity hash.

        Returns:
            Validated GraphMetadata or None if not found.
        """
        meta_path = self.root / identity / "meta.json"
        if not meta_path.exists():
            return None
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return GraphMetadata(**data)

    def list_identities(self) -> list[str]:
        """List all identity subdirectories that contain a graph.

        Returns:
            List of identity hashes with graph files.
        """
        identities: list[str] = []
        if not self.root.exists():
            return identities
        for entry in sorted(self.root.iterdir()):
            if entry.is_dir() and len(entry.name) == 12:
                if (entry / "graph.toon").exists() or (entry / "graph.json").exists():
                    identities.append(entry.name)
        return identities

    def check_fresh(self, identity: str, current_source_hash: str) -> bool:
        """Check if stored graph is fresh relative to current source files.

        Args:
            identity: Contract identity hash.
            current_source_hash: SHA-256 hash of current source file contents.

        Returns:
            True if graph is fresh (hashes match), False if stale.
        """
        meta = self.load_meta(identity)
        if meta is None:
            return False
        return meta.graph_hash == current_source_hash


def list_available_graphs(root: Path) -> list[GraphInfo]:
    """List all valid graphs in a root directory with structured metadata.

    Scans {root}/{identity}/ subdirectories for graph files (graph.toon or
    graph.json) with meta.json sidecars. Validates schema_version at load time.

    This is the shared utility used by:
    - Error-when-ambiguous graph resolution (cli/main.py)
    - --graph stem-based lookup (cli/main.py)

    Args:
        root: Root directory to scan (typically .vrs/graphs/).

    Returns:
        List of GraphInfo for each valid graph found.

    Raises:
        SchemaVersionMismatchError: If any meta.json has wrong schema_version.
    """
    graphs: list[GraphInfo] = []

    if not root.exists() or not root.is_dir():
        return graphs

    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        # Only consider 12-hex-char identity directories
        if len(entry.name) != 12:
            continue

        # Must have a completed graph file (not just .tmp)
        has_toon = (entry / "graph.toon").exists()
        has_json = (entry / "graph.json").exists()
        if not has_toon and not has_json:
            continue

        # Check for .tmp without completed file (corrupt)
        for tmp_file in entry.glob("*.tmp"):
            completed_name = tmp_file.name.removesuffix(".tmp")
            if not (entry / completed_name).exists():
                logger.warning("Skipping corrupt graph at %s: partial write detected", entry)
                continue

        # Load and validate meta.json
        meta_path = entry / "meta.json"
        if not meta_path.exists():
            logger.warning("Skipping graph at %s: no meta.json", entry)
            continue

        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping graph at %s: meta.json parse error: %s", entry, exc)
            continue

        # Validate schema_version before full model validation
        sv = data.get("schema_version")
        if sv != EXPECTED_SCHEMA_VERSION:
            raise SchemaVersionMismatchError(
                identity=entry.name,
                found=sv if isinstance(sv, int) else -1,
                expected=EXPECTED_SCHEMA_VERSION,
            )

        try:
            meta = GraphMetadata(**data)
        except Exception as exc:
            logger.warning("Skipping graph at %s: invalid meta.json: %s", entry, exc)
            continue

        graphs.append(
            GraphInfo(
                identity=meta.identity,
                stem=meta.stem,
                source_contract=meta.source_contract,
                dir_path=entry,
                meta=meta,
            )
        )

    return graphs
