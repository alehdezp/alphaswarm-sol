"""Folder Discovery for VulnDocs Framework.

This module provides utilities for traversing and discovering vulnerabilities,
categories, and patterns within the vulndocs folder structure.

Design:
- Finds categories, vulnerabilities, and patterns automatically
- Returns lightweight dataclasses for navigation
- Skips .meta/ folder and hidden/underscore-prefixed folders
- Works with empty folders (returns empty lists)

Part of Plan 05.4-03: Progressive Validation Framework
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class CategoryInfo:
    """Information about a vulnerability category.

    Attributes:
        path: Path to category folder
        name: Category name (folder name)
        has_overview: Whether overview.md exists
    """

    path: Path
    name: str
    has_overview: bool


@dataclass
class VulnerabilityInfo:
    """Information about a vulnerability subcategory.

    Attributes:
        path: Path to vulnerability folder
        category: Parent category name
        subcategory: Subcategory name
        has_index: Whether index.yaml exists
    """

    path: Path
    category: str
    subcategory: str
    has_index: bool


@dataclass
class PatternInfo:
    """Information about a pattern file.

    Attributes:
        path: Path to pattern YAML file
        pattern_id: Pattern identifier from filename
        vulndoc: Expected vulndoc reference (category/subcategory)
    """

    path: Path
    pattern_id: str
    vulndoc: str  # Expected category/subcategory path


def discover_categories(root: Path) -> List[CategoryInfo]:
    """Discover all top-level categories in vulndocs folder.

    Finds all folders in root that are not .meta/, hidden, or _prefixed folders.
    A category folder may contain:
    - overview.md (optional category-level overview)
    - Subcategory folders with index.yaml files

    Args:
        root: Path to vulndocs root folder

    Returns:
        List of CategoryInfo objects, sorted by name

    Example:
        >>> from pathlib import Path
        >>> categories = discover_categories(Path("vulndocs"))
        >>> for cat in categories:
        ...     print(f"{cat.name}: overview={cat.has_overview}")
    """
    if not root.exists() or not root.is_dir():
        return []

    categories = []

    for item in root.iterdir():
        # Skip non-directories
        if not item.is_dir():
            continue

        # Skip hidden folders and special folders
        if item.name.startswith('.') or item.name.startswith('_'):
            continue

        # Check for overview.md
        has_overview = (item / "overview.md").exists()

        categories.append(CategoryInfo(
            path=item,
            name=item.name,
            has_overview=has_overview
        ))

    # Sort by name for consistent ordering
    categories.sort(key=lambda c: c.name)

    return categories


def discover_vulnerabilities(root: Path) -> List[VulnerabilityInfo]:
    """Discover all vulnerability folders with index.yaml files.

    A vulnerability folder is identified by the presence of an index.yaml file.
    These folders are typically at depth 2 (category/subcategory/) or 3
    (category/subcategory/variant/).

    Args:
        root: Path to vulndocs root folder

    Returns:
        List of VulnerabilityInfo objects, sorted by category then subcategory

    Example:
        >>> from pathlib import Path
        >>> vulns = discover_vulnerabilities(Path("vulndocs"))
        >>> for vuln in vulns:
        ...     print(f"{vuln.category}/{vuln.subcategory}: index={vuln.has_index}")
    """
    if not root.exists() or not root.is_dir():
        return []

    vulnerabilities = []

    # Get all categories first
    categories = discover_categories(root)

    for category in categories:
        # Look for subcategory folders
        for item in category.path.iterdir():
            if not item.is_dir():
                continue

            # Skip hidden and special folders
            if item.name.startswith('.') or item.name.startswith('_'):
                continue

            # Check if this is a vulnerability folder (has index.yaml)
            has_index = (item / "index.yaml").exists()

            if has_index:
                vulnerabilities.append(VulnerabilityInfo(
                    path=item,
                    category=category.name,
                    subcategory=item.name,
                    has_index=has_index
                ))
            else:
                # Check one level deeper for 3-level nesting (category/subcategory/variant/)
                for subitem in item.iterdir():
                    if not subitem.is_dir():
                        continue

                    if subitem.name.startswith('.') or subitem.name.startswith('_'):
                        continue

                    has_subindex = (subitem / "index.yaml").exists()
                    if has_subindex:
                        # Use parent/child as category/subcategory
                        vulnerabilities.append(VulnerabilityInfo(
                            path=subitem,
                            category=f"{category.name}/{item.name}",
                            subcategory=subitem.name,
                            has_index=has_subindex
                        ))

    # Sort by category then subcategory
    vulnerabilities.sort(key=lambda v: (v.category, v.subcategory))

    return vulnerabilities


def discover_patterns(vuln_path: Path) -> List[PatternInfo]:
    """Discover pattern YAML files within a vulnerability folder.

    Patterns are stored in a patterns/ subfolder within each vulnerability.
    Each pattern YAML file should have a vulndoc field linking back to its parent.

    Args:
        vuln_path: Path to vulnerability folder

    Returns:
        List of PatternInfo objects, sorted by pattern_id

    Example:
        >>> from pathlib import Path
        >>> patterns = discover_patterns(Path("vulndocs/oracle/price-manipulation"))
        >>> for p in patterns:
        ...     print(f"{p.pattern_id} -> {p.vulndoc}")
    """
    if not vuln_path.exists() or not vuln_path.is_dir():
        return []

    patterns_dir = vuln_path / "patterns"
    if not patterns_dir.exists() or not patterns_dir.is_dir():
        return []

    # Determine expected vulndoc path from folder structure
    # vuln_path could be:
    # - vulndocs/category/subcategory -> vulndoc = category/subcategory
    # - vulndocs/category/subcat/variant -> vulndoc = category/subcat/variant

    parts = vuln_path.parts

    # Find the vulndocs root (last occurrence of "vulndocs" in path)
    try:
        vulndocs_idx = len(parts) - 1 - parts[::-1].index("vulndocs")
    except ValueError:
        # vulndocs not in path, use last 2-3 parts
        vulndocs_idx = max(0, len(parts) - 3)

    # Take parts after vulndocs
    vuln_parts = parts[vulndocs_idx + 1:]
    expected_vulndoc = "/".join(vuln_parts)

    patterns = []

    for pattern_file in patterns_dir.glob("*.yaml"):
        # Skip hidden files
        if pattern_file.name.startswith('.'):
            continue

        # Pattern ID is filename without extension
        pattern_id = pattern_file.stem

        patterns.append(PatternInfo(
            path=pattern_file,
            pattern_id=pattern_id,
            vulndoc=expected_vulndoc
        ))

    # Sort by pattern_id
    patterns.sort(key=lambda p: p.pattern_id)

    return patterns


def get_expected_files() -> List[str]:
    """Get list of expected files in a vulnerability folder.

    These are the recommended files per the 05.4-CONTEXT.md structure:
    - index.yaml (REQUIRED)
    - overview.md (recommended)
    - detection.md (recommended)
    - verification.md (recommended)
    - exploits.md (optional but valuable)

    Returns:
        List of expected filenames

    Example:
        >>> files = get_expected_files()
        >>> print(files)
        ['index.yaml', 'overview.md', 'detection.md', 'verification.md', 'exploits.md']
    """
    return [
        "index.yaml",
        "overview.md",
        "detection.md",
        "verification.md",
        "exploits.md"
    ]
