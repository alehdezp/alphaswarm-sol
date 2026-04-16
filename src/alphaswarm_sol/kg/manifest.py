"""
Build Manifest Generator

Creates build_manifest.json for every VKG graph build with:
- Build metadata (timestamp, version, host)
- Input file hashes
- Output file checksums
- Build configuration
- Reproducibility verification

This ensures:
1. Build provenance tracking
2. Cache invalidation correctness
3. Determinism verification
4. Audit trail for security analysis
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (OSError, IOError):
        return "unavailable"


def compute_content_hash(content: str | bytes) -> str:
    """Compute SHA-256 hash of content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def get_vkg_version() -> str:
    """Get VKG version from package metadata."""
    try:
        from importlib.metadata import version
        return version("alphaswarm")
    except Exception:
        return "0.0.0-dev"


def get_environment_info() -> dict[str, Any]:
    """Collect environment information for reproducibility."""
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.system(),
        "platform_version": platform.version(),
        "machine": platform.machine(),
        "hostname_hash": hashlib.sha256(platform.node().encode()).hexdigest()[:12],
    }


def create_build_manifest(
    source_files: list[Path],
    graph_data: dict[str, Any],
    output_path: Path,
    build_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a build manifest for a VKG graph build.

    Args:
        source_files: List of Solidity source files processed
        graph_data: The built graph data
        output_path: Where the graph was saved
        build_config: Optional build configuration

    Returns:
        Build manifest dictionary
    """
    manifest = {
        "manifest_version": "1.0",
        "vkg_version": get_vkg_version(),
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": get_environment_info(),
        "inputs": {
            "source_count": len(source_files),
            "source_files": [],
            "total_size_bytes": 0,
        },
        "outputs": {
            "graph_path": str(output_path),
            "node_count": 0,
            "edge_count": 0,
            "graph_hash": "",
        },
        "config": build_config or {},
        "verification": {
            "reproducible": True,
            "determinism_tested": False,
        },
    }

    # Input file information
    total_size = 0
    for src in sorted(source_files):
        if src.exists():
            size = src.stat().st_size
            total_size += size
            manifest["inputs"]["source_files"].append({
                "path": str(src),
                "hash": compute_file_hash(src),
                "size_bytes": size,
            })
    manifest["inputs"]["total_size_bytes"] = total_size

    # Output information
    if "graph" in graph_data:
        nodes = graph_data["graph"].get("nodes", [])
        edges = graph_data["graph"].get("edges", [])
        manifest["outputs"]["node_count"] = len(nodes)
        manifest["outputs"]["edge_count"] = len(edges)

    # Compute graph hash for determinism verification
    graph_json = json.dumps(graph_data, sort_keys=True, separators=(",", ":"))
    manifest["outputs"]["graph_hash"] = compute_content_hash(graph_json)

    # Extract solc version if available
    if "metadata" in graph_data:
        manifest["config"]["solc_version"] = graph_data["metadata"].get("solc_version_selected")

    return manifest


def save_manifest(manifest: dict[str, Any], output_dir: Path) -> Path:
    """
    Save manifest to build_manifest.json in the output directory.

    Args:
        manifest: Build manifest dictionary
        output_dir: Directory to save manifest to

    Returns:
        Path to saved manifest file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "build_manifest.json"

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest_path


def verify_manifest(manifest_path: Path, graph_path: Path) -> dict[str, Any]:
    """
    Verify a build manifest against current graph.

    Args:
        manifest_path: Path to build_manifest.json
        graph_path: Path to graph.json

    Returns:
        Verification result with status and details
    """
    result = {
        "valid": False,
        "manifest_found": manifest_path.exists(),
        "graph_found": graph_path.exists(),
        "hash_match": False,
        "details": [],
    }

    if not manifest_path.exists():
        result["details"].append("Manifest not found")
        return result

    if not graph_path.exists():
        result["details"].append("Graph not found")
        return result

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)

        with open(graph_path) as f:
            graph_data = json.load(f)

        # Verify graph hash
        graph_json = json.dumps(graph_data, sort_keys=True, separators=(",", ":"))
        current_hash = compute_content_hash(graph_json)
        expected_hash = manifest["outputs"]["graph_hash"]

        result["hash_match"] = current_hash == expected_hash
        if result["hash_match"]:
            result["details"].append("Graph hash matches manifest")
        else:
            result["details"].append(f"Hash mismatch: expected {expected_hash[:12]}..., got {current_hash[:12]}...")

        # Verify node/edge counts
        nodes = graph_data.get("graph", {}).get("nodes", [])
        edges = graph_data.get("graph", {}).get("edges", [])

        expected_nodes = manifest["outputs"]["node_count"]
        expected_edges = manifest["outputs"]["edge_count"]

        if len(nodes) == expected_nodes and len(edges) == expected_edges:
            result["details"].append(f"Node/edge counts match: {len(nodes)} nodes, {len(edges)} edges")
        else:
            result["details"].append(f"Count mismatch: expected {expected_nodes}/{expected_edges}, got {len(nodes)}/{len(edges)}")

        result["valid"] = result["hash_match"]

    except Exception as e:
        result["details"].append(f"Verification error: {e}")

    return result


def compare_manifests(manifest1_path: Path, manifest2_path: Path) -> dict[str, Any]:
    """
    Compare two build manifests to detect differences.

    Useful for:
    - Debugging non-deterministic builds
    - Tracking changes across builds
    - CI regression detection

    Args:
        manifest1_path: Path to first manifest
        manifest2_path: Path to second manifest

    Returns:
        Comparison result with differences
    """
    result = {
        "identical": False,
        "differences": [],
    }

    try:
        with open(manifest1_path) as f:
            m1 = json.load(f)
        with open(manifest2_path) as f:
            m2 = json.load(f)

        # Compare key fields
        if m1["outputs"]["graph_hash"] != m2["outputs"]["graph_hash"]:
            result["differences"].append({
                "field": "graph_hash",
                "value1": m1["outputs"]["graph_hash"][:16] + "...",
                "value2": m2["outputs"]["graph_hash"][:16] + "...",
            })

        if m1["outputs"]["node_count"] != m2["outputs"]["node_count"]:
            result["differences"].append({
                "field": "node_count",
                "value1": m1["outputs"]["node_count"],
                "value2": m2["outputs"]["node_count"],
            })

        if m1["outputs"]["edge_count"] != m2["outputs"]["edge_count"]:
            result["differences"].append({
                "field": "edge_count",
                "value1": m1["outputs"]["edge_count"],
                "value2": m2["outputs"]["edge_count"],
            })

        if m1.get("vkg_version") != m2.get("vkg_version"):
            result["differences"].append({
                "field": "vkg_version",
                "value1": m1.get("vkg_version"),
                "value2": m2.get("vkg_version"),
            })

        result["identical"] = len(result["differences"]) == 0

    except Exception as e:
        result["differences"].append({"error": str(e)})

    return result
