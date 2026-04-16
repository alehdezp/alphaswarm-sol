"""Centralized vulndocs path resolution.

Replaces all cwd-relative Path("vulndocs") constructions with package-aware
resolution that works from any working directory (Jujutsu workspaces,
non-project paths, wheel installs).

Design per CONTEXT.md D-1 (dual-mode resolution):
- vulndocs_read_path() -> Traversable (importlib.resources for reads)
- vulndocs_write_path() -> Path (__file__-relative for writes)

Design per CONTEXT.md D-1a (ALPHASWARM_VULNDOCS_DIR contract):
- Env var overrides BOTH read and write paths with validation.

Task 2 finding: collision-use-alternate-path.
importlib.resources uses _vulndocs_data to avoid collision with
the alphaswarm_sol.vulndocs Python subpackage.
"""

from __future__ import annotations

import importlib.resources
import logging
import os
from importlib.resources.abc import Traversable
from pathlib import Path

logger = logging.getLogger(__name__)

# The bundled data path inside the package, chosen to avoid namespace
# collision with the alphaswarm_sol.vulndocs Python subpackage.
_BUNDLED_DATA_SUBPATH = "_vulndocs_data"


class VulndocsConfigError(Exception):
    """Raised when ALPHASWARM_VULNDOCS_DIR is set but invalid."""


class VulndocsPathConflict(Exception):
    """Raised when dual vulndocs roots are detected at import time."""


def vulndocs_read_path() -> Traversable:
    """Return a Traversable for reading vulndocs pattern data.

    Resolution order:
    1. ALPHASWARM_VULNDOCS_DIR env var (validated per D-1a)
    2. importlib.resources.files("alphaswarm_sol").joinpath("_vulndocs_data")
       (for wheel installs)
    3. __file__-relative fallback to project-root vulndocs/
       (for editable installs where _vulndocs_data isn't bundled yet)

    Returns:
        Traversable that can navigate vulndocs categories.
        In editable installs this is a Path; in wheel installs it may not be.
    """
    override = _get_env_override()
    if override is not None:
        return override

    # Try importlib.resources first (works in both wheel and editable)
    pkg_path = importlib.resources.files("alphaswarm_sol").joinpath(
        _BUNDLED_DATA_SUBPATH
    )
    # Check if the bundled data path exists and has content
    if _traversable_has_yamls(pkg_path):
        return pkg_path

    # Fallback: __file__-relative for editable installs where vulndocs
    # data hasn't been force-included yet (normal development workflow)
    file_relative = _file_relative_vulndocs()
    if file_relative.is_dir():
        return file_relative

    # Last resort: return the importlib path even if empty
    # (will fail downstream with a clear error)
    return pkg_path


def vulndocs_read_path_as_path() -> Path:
    """Return a concrete Path for reading vulndocs data.

    For consumers that genuinely need a filesystem Path (e.g., they use
    .glob(), the / operator, or pass the path to external tools).

    In editable installs, vulndocs_read_path() already returns a Path,
    so this is a no-op cast. In wheel installs, this falls back to the
    __file__-relative path (which is always a real filesystem path for
    editable installs) or the env override.

    Prefer vulndocs_read_path() (Traversable) for new code.
    Use this only when the consumer API requires Path.
    """
    result = vulndocs_read_path()
    if isinstance(result, Path):
        return result
    # Non-Path Traversable (e.g., zip-backed wheel install).
    # Fall back to __file__-relative which is always a real Path.
    override = _get_env_override()
    if override is not None:
        return override
    return _file_relative_vulndocs()


def vulndocs_write_path() -> Path:
    """Return a writable Path for vulndocs data (editable installs).

    Resolution order:
    1. ALPHASWARM_VULNDOCS_DIR env var (validated per D-1a)
    2. __file__-relative path to project root vulndocs/

    Returns:
        Path suitable for writing new vulndocs entries.
    """
    override = _get_env_override()
    if override is not None:
        # Override is always a Path (validated as directory)
        return override

    return _file_relative_vulndocs()


def _get_env_override() -> Path | None:
    """Check and validate ALPHASWARM_VULNDOCS_DIR env var.

    Per D-1a contract:
    - Not-exists -> VulndocsConfigError
    - Not-a-directory -> VulndocsConfigError
    - Empty of YAMLs -> WARNING log (no raise)

    Returns:
        Validated Path or None if env var not set.
    """
    env_val = os.environ.get("ALPHASWARM_VULNDOCS_DIR")
    if not env_val:
        return None

    p = Path(env_val)

    if not p.exists():
        raise VulndocsConfigError(
            f"ALPHASWARM_VULNDOCS_DIR={env_val!r} does not exist"
        )

    if not p.is_dir():
        raise VulndocsConfigError(
            f"ALPHASWARM_VULNDOCS_DIR={env_val!r} is not a directory"
        )

    # Check for YAML files (warn if empty)
    yaml_files = list(p.glob("**/*.yaml")) + list(p.glob("**/*.yml"))
    if not yaml_files:
        logger.warning(
            "ALPHASWARM_VULNDOCS_DIR=%r exists but contains no YAML files",
            env_val,
        )

    return p


def _file_relative_vulndocs() -> Path:
    """Return __file__-relative path to project root vulndocs/.

    This resolves symlinks to handle editable installs correctly.
    Path: resolution.py -> vulndocs/ -> alphaswarm_sol/ -> src/ -> project_root/
    """
    return Path(__file__).resolve().parent.parent.parent.parent / "vulndocs"


def _traversable_has_yamls(t: Traversable) -> bool:
    """Check if a Traversable has any YAML content (non-recursive, quick check)."""
    try:
        for child in t.iterdir():
            if child.is_dir():
                # Has at least one subdirectory — likely real vulndocs data
                return True
        return False
    except (FileNotFoundError, OSError, TypeError):
        return False


def _assert_single_vulndocs_root() -> None:
    """Detect dual-root conflict at import time.

    When both importlib.resources and __file__-relative resolve to
    DIFFERENT paths with YAML files, this likely indicates a broken
    install with both editable and wheel vulndocs present.

    Suppressible via ALPHASWARM_SKIP_VULNDOCS_CONFLICT_CHECK=1.

    Raises:
        VulndocsPathConflict: When dual roots detected.
    """
    if os.environ.get("ALPHASWARM_SKIP_VULNDOCS_CONFLICT_CHECK") == "1":
        return

    # If env override is set, no conflict possible (single source of truth)
    if os.environ.get("ALPHASWARM_VULNDOCS_DIR"):
        return

    pkg_path = importlib.resources.files("alphaswarm_sol").joinpath(
        _BUNDLED_DATA_SUBPATH
    )
    file_path = _file_relative_vulndocs()

    pkg_has_data = _traversable_has_yamls(pkg_path)
    file_has_data = file_path.is_dir() and any(file_path.glob("**/*.yaml"))

    if not (pkg_has_data and file_has_data):
        return  # Only one root has data — no conflict

    # Both have data. Check if they're the same path.
    # In editable installs, importlib.resources resolves to the source tree,
    # so both paths may point to the same place.
    try:
        pkg_resolved = Path(str(pkg_path)).resolve()
        file_resolved = file_path.resolve()
        if pkg_resolved == file_resolved:
            return  # Same path — no conflict
    except (TypeError, ValueError):
        pass  # pkg_path might not be convertible to Path (zip-backed)

    raise VulndocsPathConflict(
        f"Dual vulndocs roots detected:\n"
        f"  importlib.resources: {pkg_path}\n"
        f"  __file__-relative:   {file_path}\n"
        f"Set ALPHASWARM_SKIP_VULNDOCS_CONFLICT_CHECK=1 to suppress."
    )


# Run conflict check at import time
_assert_single_vulndocs_root()
