"""Registry for Investigation Patterns.

Task 13.11: Manage and lookup investigation patterns.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from alphaswarm_sol.investigation.loader import InvestigationLoader
from alphaswarm_sol.investigation.schema import InvestigationPattern

logger = logging.getLogger(__name__)


class InvestigationRegistry:
    """Registry for investigation patterns.

    Provides lookup by:
    - Pattern ID
    - Category
    - Tags

    Example:
        registry = InvestigationRegistry()
        registry.load_builtin()

        pattern = registry.get("inv-bl-001")
        business_logic = registry.find_by_category("business-logic")
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._patterns: Dict[str, InvestigationPattern] = {}
        self._by_category: Dict[str, List[str]] = {}
        self._by_tag: Dict[str, List[str]] = {}
        self._loader = InvestigationLoader()

    def register(self, pattern: InvestigationPattern) -> None:
        """Register an investigation pattern.

        Args:
            pattern: Pattern to register
        """
        self._patterns[pattern.id] = pattern

        # Index by category
        category = pattern.category
        if category not in self._by_category:
            self._by_category[category] = []
        if pattern.id not in self._by_category[category]:
            self._by_category[category].append(pattern.id)

        # Index by tags
        for tag in pattern.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = []
            if pattern.id not in self._by_tag[tag]:
                self._by_tag[tag].append(pattern.id)

        logger.debug(f"Registered investigation pattern: {pattern.id}")

    def unregister(self, pattern_id: str) -> bool:
        """Unregister a pattern.

        Args:
            pattern_id: ID of pattern to remove

        Returns:
            True if pattern was removed
        """
        if pattern_id not in self._patterns:
            return False

        pattern = self._patterns.pop(pattern_id)

        # Remove from category index
        category = pattern.category
        if category in self._by_category:
            self._by_category[category] = [
                pid for pid in self._by_category[category]
                if pid != pattern_id
            ]

        # Remove from tag index
        for tag in pattern.tags:
            if tag in self._by_tag:
                self._by_tag[tag] = [
                    pid for pid in self._by_tag[tag]
                    if pid != pattern_id
                ]

        return True

    def get(self, pattern_id: str) -> Optional[InvestigationPattern]:
        """Get pattern by ID.

        Args:
            pattern_id: Pattern ID

        Returns:
            Pattern or None
        """
        return self._patterns.get(pattern_id)

    def find_by_category(self, category: str) -> List[InvestigationPattern]:
        """Find patterns by category.

        Args:
            category: Category name

        Returns:
            List of matching patterns
        """
        pattern_ids = self._by_category.get(category, [])
        return [self._patterns[pid] for pid in pattern_ids if pid in self._patterns]

    def find_by_tag(self, tag: str) -> List[InvestigationPattern]:
        """Find patterns by tag.

        Args:
            tag: Tag name

        Returns:
            List of matching patterns
        """
        pattern_ids = self._by_tag.get(tag, [])
        return [self._patterns[pid] for pid in pattern_ids if pid in self._patterns]

    def find_by_trigger(
        self,
        node_properties: Dict[str, bool],
    ) -> List[InvestigationPattern]:
        """Find patterns whose triggers match node properties.

        Args:
            node_properties: Dictionary of property names to values

        Returns:
            List of patterns whose triggers are satisfied
        """
        matching = []

        for pattern in self._patterns.values():
            trigger = pattern.trigger
            if not trigger.graph_signals:
                # No signals = always matches
                matching.append(pattern)
                continue

            results = []
            for signal in trigger.graph_signals:
                prop = signal.property
                expected = signal.value
                actual = node_properties.get(prop, False)

                if expected is True:
                    results.append(bool(actual))
                else:
                    results.append(actual == expected)

            if not results:
                matching.append(pattern)
            elif trigger.require_all:
                if all(results):
                    matching.append(pattern)
            else:
                if any(results):
                    matching.append(pattern)

        return matching

    def list_all(self) -> List[InvestigationPattern]:
        """List all registered patterns.

        Returns:
            List of all patterns
        """
        return list(self._patterns.values())

    def list_categories(self) -> List[str]:
        """List all categories.

        Returns:
            List of category names
        """
        return list(self._by_category.keys())

    def list_tags(self) -> List[str]:
        """List all tags.

        Returns:
            List of tag names
        """
        return list(self._by_tag.keys())

    def load_file(self, path: Path) -> int:
        """Load patterns from a file.

        Args:
            path: Path to YAML file

        Returns:
            Number of patterns loaded
        """
        pattern = self._loader.load_file(path)
        if pattern:
            self.register(pattern)
            return 1
        return 0

    def load_directory(self, path: Path) -> int:
        """Load patterns from a directory.

        Args:
            path: Directory path

        Returns:
            Number of patterns loaded
        """
        patterns = self._loader.load_directory(path)
        for pattern in patterns:
            self.register(pattern)
        return len(patterns)

    def load_builtin(self) -> int:
        """Load built-in patterns.

        Returns:
            Number of patterns loaded
        """
        patterns = self._loader.load_builtin()
        for pattern in patterns:
            self.register(pattern)
        return len(patterns)

    def __len__(self) -> int:
        """Get number of registered patterns."""
        return len(self._patterns)

    def __contains__(self, pattern_id: str) -> bool:
        """Check if pattern is registered."""
        return pattern_id in self._patterns

    def __iter__(self) -> Iterator[InvestigationPattern]:
        """Iterate over patterns."""
        return iter(self._patterns.values())


# Global registry instance
_registry: Optional[InvestigationRegistry] = None


def get_investigation_registry() -> InvestigationRegistry:
    """Get the global investigation registry.

    Initializes and loads built-in patterns on first call.

    Returns:
        Global registry instance
    """
    global _registry
    if _registry is None:
        _registry = InvestigationRegistry()
        _registry.load_builtin()
    return _registry


def reset_investigation_registry() -> None:
    """Reset the global registry."""
    global _registry
    _registry = None


def get_investigation(pattern_id: str) -> Optional[InvestigationPattern]:
    """Get an investigation pattern by ID.

    Convenience function using global registry.

    Args:
        pattern_id: Pattern ID

    Returns:
        Pattern or None
    """
    return get_investigation_registry().get(pattern_id)


def list_investigations(
    category: Optional[str] = None,
    tag: Optional[str] = None,
) -> List[InvestigationPattern]:
    """List investigation patterns.

    Args:
        category: Optional category filter
        tag: Optional tag filter

    Returns:
        List of matching patterns
    """
    registry = get_investigation_registry()

    if category:
        return registry.find_by_category(category)
    if tag:
        return registry.find_by_tag(tag)
    return registry.list_all()
