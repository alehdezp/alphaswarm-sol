"""Canonical contract identity for per-contract graph isolation.

Provides a single shared utility for computing deterministic contract identities
used by ALL components (build-kg, query, --graph resolution, GraphStore).

Decision references: D-2a (contract identity spec), D-2b (per-contract storage).
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

IDENTITY_LENGTH = 12  # hex chars


def contract_identity(paths: list[Path]) -> str:
    """Compute canonical contract identity hash from input paths.

    The identity is deterministic, order-independent, and symlink-resolving.
    Uses os.path.realpath() per decision D-2a (not os.path.abspath()).

    Args:
        paths: List of Solidity file or directory paths.

    Returns:
        12-character hex string uniquely identifying this set of contracts.
    """
    if not paths:
        raise ValueError("contract_identity requires at least one path")

    # Resolve each path via os.path.realpath (follows symlinks, canonicalizes)
    resolved = [os.path.realpath(str(p)) for p in paths]

    # Strip trailing slashes
    resolved = [r.rstrip(os.sep) for r in resolved]

    # Sort for order-independence
    resolved.sort()

    # Join with newline separator
    joined = "\n".join(resolved)

    # SHA-256 hash, truncate to 12 hex chars
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:IDENTITY_LENGTH]


def _resolve_project_root(inputs: list[Path]) -> tuple[Path, str]:
    """Resolve the project root directory.

    Uses git rev-parse --show-toplevel when available, falls back to cwd.

    Args:
        inputs: Input file/directory paths (uses first path's parent for git lookup).

    Returns:
        Tuple of (project_root_path, source_type) where source_type is
        "git_toplevel" or "fallback_cwd".
    """
    if not inputs:
        return Path.cwd(), "fallback_cwd"

    # Determine working directory for git command
    first_path = Path(os.path.realpath(str(inputs[0])))
    work_dir = first_path.parent if first_path.is_file() else first_path

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            toplevel = result.stdout.strip()
            return Path(toplevel), "git_toplevel"
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    print(
        "[WARNING] Not inside a git repository, using cwd as project root",
        file=sys.stderr,
    )
    return Path.cwd(), "fallback_cwd"


def filter_dependency_paths(
    all_paths: list[Path],
    project_root: Path,
    *,
    compilation_unit: object | None = None,
) -> list[Path]:
    """Filter out dependency paths from contract file list.

    Uses Slither's source_mapping.is_dependency flag as primary filter.
    Falls back to project-root prefix matching for raw solc output.

    Args:
        all_paths: All source file paths from compilation.
        project_root: Resolved project root directory.
        compilation_unit: Optional Slither compilation unit for is_dependency check.

    Returns:
        Filtered list containing only project-owned source files.
    """
    project_root_real = os.path.realpath(str(project_root))
    filtered: list[Path] = []

    for p in all_paths:
        real_p = os.path.realpath(str(p))

        # Primary filter: use Slither's is_dependency flag when available
        if compilation_unit is not None:
            is_dep = _check_slither_dependency(p, compilation_unit)
            if is_dep is not None:
                if is_dep:
                    logger.warning("Excluded dependency path: %s", p)
                    continue
                filtered.append(p)
                continue

        # Fallback: project root prefix matching
        if real_p.startswith(project_root_real):
            filtered.append(p)
        else:
            logger.warning("Excluded dependency path (outside project root): %s", p)

    return filtered


def _check_slither_dependency(
    path: Path, compilation_unit: object
) -> bool | None:
    """Check if a path is a dependency using Slither's source_mapping.

    Args:
        path: File path to check.
        compilation_unit: Slither compilation unit.

    Returns:
        True if dependency, False if not, None if flag unavailable.
    """
    try:
        # Slither compilation units expose source_mapping with is_dependency
        if hasattr(compilation_unit, "source_mapping"):
            sm = compilation_unit.source_mapping
            if hasattr(sm, "is_dependency"):
                return bool(sm.is_dependency(str(path)))
    except Exception:
        pass
    return None
