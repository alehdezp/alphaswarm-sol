"""Helpers for selecting solc versions based on pragma."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Optional, Tuple


_PRAGMA_RE = re.compile(r"^\s*pragma\s+solidity\s+([^;]+);", re.MULTILINE)
_MISSING_IMPORT_RE = re.compile(r"Source \"(?P<path>[^\"]+)\" not found")


def select_solc_for_file(file_path: Path) -> Optional[Tuple[str, str]]:
    """Select a solc version using solc-select based on pragma.

    Returns (solc binary, version) to pass to Slither, or None if no selection.
    """

    constraint = _extract_pragma_constraint(file_path)
    if not constraint:
        return None

    version = _select_version_from_constraint(constraint)
    if not version:
        return None

    solc_select = shutil.which("solc-select")
    if not solc_select:
        return None

    auto_install = os.getenv("TRUE_VKG_SOLC_AUTO_INSTALL", "1").lower() not in {"0", "false", "no"}
    if auto_install:
        subprocess.run([solc_select, "install", version], check=False, capture_output=True, text=True)
    subprocess.run([solc_select, "use", version], check=False, capture_output=True, text=True)
    solc_bin = _resolve_solc_select_binary(solc_select, version)
    return solc_bin or "solc", version


def _resolve_solc_select_binary(solc_select: str, version: str) -> Optional[str]:
    env_dir = os.getenv("SOLC_SELECT_DIR")
    candidate_dirs = []
    if env_dir:
        candidate_dirs.append(Path(env_dir))
    solc_select_path = Path(solc_select).resolve()
    if solc_select_path.parent.name == "bin":
        candidate_dirs.append(solc_select_path.parent.parent / ".solc-select")
    candidate_dirs.append(Path.home() / ".solc-select")
    for base in candidate_dirs:
        candidate = base / "artifacts" / f"solc-{version}" / f"solc-{version}"
        if candidate.exists():
            return str(candidate)
    return None


def _extract_pragma_constraint(file_path: Path) -> str | None:
    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception:
        return None
    match = _PRAGMA_RE.search(text)
    if not match:
        return None
    return match.group(1).strip()


def _select_version_from_constraint(constraint: str) -> str | None:
    match = re.search(r"(\d+\.\d+\.\d+)", constraint)
    if match:
        return match.group(1)
    match = re.search(r"(\d+\.\d+)", constraint)
    if match:
        return f"{match.group(1)}.0"
    return None


def extract_missing_imports(message: str) -> list[str]:
    return [match.group("path") for match in _MISSING_IMPORT_RE.finditer(message)]
