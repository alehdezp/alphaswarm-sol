"""Loader for Investigation Patterns.

Task 13.11: Load investigation patterns from YAML files.

Patterns are now located in vulndocs/{category}/{subcategory}/patterns/
following the unified VulnDocs structure.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from alphaswarm_sol.investigation.schema import InvestigationPattern

logger = logging.getLogger(__name__)


class InvestigationLoader:
    """Load investigation patterns from files.

    Example:
        loader = InvestigationLoader()
        pattern = loader.load_file(Path("vulndocs/reentrancy/classic/patterns/inv-bl-001.yaml"))
        all_patterns = loader.load_all_vulndocs(Path("vulndocs"))
    """

    def __init__(self) -> None:
        """Initialize loader."""
        self._cache: Dict[str, InvestigationPattern] = {}

    def load_file(self, path: Path) -> Optional[InvestigationPattern]:
        """Load a single investigation pattern from file.

        Args:
            path: Path to YAML file

        Returns:
            InvestigationPattern or None if loading fails
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning(f"Empty pattern file: {path}")
                return None

            # Validate it's an investigation pattern
            if data.get("type") != "investigation":
                logger.debug(f"Not an investigation pattern: {path}")
                return None

            pattern = InvestigationPattern.from_dict(data)
            self._cache[pattern.id] = pattern

            logger.debug(f"Loaded investigation pattern: {pattern.id}")
            return pattern

        except yaml.YAMLError as e:
            logger.error(f"YAML error loading {path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading {path}: {e}")
            return None

    def load_directory(self, path: Path) -> List[InvestigationPattern]:
        """Load all investigation patterns from a directory.

        Args:
            path: Directory path

        Returns:
            List of loaded patterns
        """
        patterns = []

        if not path.is_dir():
            logger.warning(f"Not a directory: {path}")
            return patterns

        for file_path in path.glob("*.yaml"):
            pattern = self.load_file(file_path)
            if pattern:
                patterns.append(pattern)

        for file_path in path.glob("*.yml"):
            pattern = self.load_file(file_path)
            if pattern:
                patterns.append(pattern)

        logger.info(f"Loaded {len(patterns)} investigation patterns from {path}")
        return patterns

    def load_builtin(self) -> List[InvestigationPattern]:
        """Load built-in investigation patterns from vulndocs.

        Searches for investigation patterns across all vulndocs categories.
        Uses centralized vulndocs resolution for cwd-independent operation.

        Returns:
            List of built-in patterns
        """
        from alphaswarm_sol.vulndocs.resolution import vulndocs_read_path_as_path

        return self.load_all_vulndocs(vulndocs_read_path_as_path())

    def load_all_vulndocs(self, vulndocs_root: Path) -> List[InvestigationPattern]:
        """Load all investigation patterns from vulndocs structure.

        Searches vulndocs/{category}/{subcategory}/patterns/ for investigation patterns.

        Args:
            vulndocs_root: Path to vulndocs root directory

        Returns:
            List of loaded patterns
        """
        patterns = []

        if not vulndocs_root.is_dir():
            return patterns

        # Search all patterns/ directories within vulndocs
        for pattern_file in vulndocs_root.glob("**/patterns/*.yaml"):
            pattern = self.load_file(pattern_file)
            if pattern:
                patterns.append(pattern)

        for pattern_file in vulndocs_root.glob("**/patterns/*.yml"):
            pattern = self.load_file(pattern_file)
            if pattern:
                patterns.append(pattern)

        logger.info(f"Loaded {len(patterns)} investigation patterns from {vulndocs_root}")
        return patterns

    def get_cached(self, pattern_id: str) -> Optional[InvestigationPattern]:
        """Get a cached pattern by ID.

        Args:
            pattern_id: Pattern ID

        Returns:
            Cached pattern or None
        """
        return self._cache.get(pattern_id)

    def clear_cache(self) -> None:
        """Clear the pattern cache."""
        self._cache.clear()


# Global loader instance
_loader: Optional[InvestigationLoader] = None


def get_loader() -> InvestigationLoader:
    """Get the global loader instance."""
    global _loader
    if _loader is None:
        _loader = InvestigationLoader()
    return _loader


def load_investigation_pattern(path: Path) -> Optional[InvestigationPattern]:
    """Load a single investigation pattern.

    Convenience function using global loader.

    Args:
        path: Path to YAML file

    Returns:
        InvestigationPattern or None
    """
    return get_loader().load_file(path)


def load_all_investigations(
    directory: Optional[Path] = None,
) -> List[InvestigationPattern]:
    """Load all investigation patterns.

    Args:
        directory: Optional directory path. If None, loads built-in patterns.

    Returns:
        List of patterns
    """
    loader = get_loader()
    if directory:
        return loader.load_directory(directory)
    return loader.load_builtin()
