"""Grimoire Registry.

Task 13.1: Registry for discovering and managing grimoires.

The registry provides:
- Grimoire discovery and loading
- Category-based lookup
- Skill name resolution
- Version management
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from alphaswarm_sol.grimoires.schema import Grimoire

logger = logging.getLogger(__name__)


class GrimoireRegistry:
    """Registry for managing grimoire definitions.

    Grimoires can be:
    - Built-in (shipped with VKG)
    - Custom (user-defined in project .vrs/ directory)
    - External (loaded from remote sources)

    Example:
        registry = GrimoireRegistry()
        registry.load_builtin()

        # Get grimoire by ID
        grimoire = registry.get("grimoire-reentrancy")

        # Find by category
        grimoires = registry.find_by_category("reentrancy")

        # Find by skill name
        grimoire = registry.find_by_skill("/test-reentrancy")
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._grimoires: Dict[str, Grimoire] = {}
        self._by_category: Dict[str, Set[str]] = {}
        self._by_skill: Dict[str, str] = {}
        self._loaded_sources: Set[str] = set()

    def register(self, grimoire: Grimoire) -> None:
        """Register a grimoire.

        Args:
            grimoire: Grimoire to register

        Raises:
            ValueError: If grimoire with same ID already exists
        """
        if grimoire.id in self._grimoires:
            existing = self._grimoires[grimoire.id]
            if existing.version == grimoire.version:
                logger.debug(f"Grimoire {grimoire.id} already registered, skipping")
                return
            logger.warning(
                f"Replacing grimoire {grimoire.id} "
                f"v{existing.version} with v{grimoire.version}"
            )

        self._grimoires[grimoire.id] = grimoire

        # Index by category
        if grimoire.category not in self._by_category:
            self._by_category[grimoire.category] = set()
        self._by_category[grimoire.category].add(grimoire.id)

        # Index by skill name
        if grimoire.skill:
            self._by_skill[grimoire.skill] = grimoire.id
            for alias in grimoire.aliases:
                self._by_skill[alias] = grimoire.id

        logger.debug(f"Registered grimoire: {grimoire.id} ({grimoire.category})")

    def unregister(self, grimoire_id: str) -> bool:
        """Unregister a grimoire.

        Args:
            grimoire_id: ID of grimoire to remove

        Returns:
            True if grimoire was removed, False if not found
        """
        if grimoire_id not in self._grimoires:
            return False

        grimoire = self._grimoires.pop(grimoire_id)

        # Remove from category index
        if grimoire.category in self._by_category:
            self._by_category[grimoire.category].discard(grimoire_id)
            if not self._by_category[grimoire.category]:
                del self._by_category[grimoire.category]

        # Remove from skill index
        if grimoire.skill and grimoire.skill in self._by_skill:
            del self._by_skill[grimoire.skill]
        for alias in grimoire.aliases:
            if alias in self._by_skill:
                del self._by_skill[alias]

        return True

    def get(self, grimoire_id: str) -> Optional[Grimoire]:
        """Get grimoire by ID.

        Args:
            grimoire_id: Grimoire identifier

        Returns:
            Grimoire if found, None otherwise
        """
        return self._grimoires.get(grimoire_id)

    def find_by_category(self, category: str) -> List[Grimoire]:
        """Find all grimoires for a category.

        Args:
            category: Vulnerability category (e.g., "reentrancy")

        Returns:
            List of matching grimoires
        """
        grimoire_ids = self._by_category.get(category, set())
        return [self._grimoires[gid] for gid in grimoire_ids]

    def find_by_skill(self, skill_name: str) -> Optional[Grimoire]:
        """Find grimoire by skill name.

        Args:
            skill_name: Skill name (e.g., "/test-reentrancy")

        Returns:
            Grimoire if found, None otherwise
        """
        grimoire_id = self._by_skill.get(skill_name)
        if grimoire_id:
            return self._grimoires.get(grimoire_id)
        return None

    def find_by_subcategory(self, subcategory: str) -> List[Grimoire]:
        """Find grimoires that handle a specific subcategory.

        Args:
            subcategory: Vulnerability subcategory (e.g., "cross-function")

        Returns:
            List of matching grimoires
        """
        results = []
        for grimoire in self._grimoires.values():
            if subcategory in grimoire.subcategories:
                results.append(grimoire)
        return results

    def find_by_tags(self, tags: List[str], match_all: bool = False) -> List[Grimoire]:
        """Find grimoires by tags.

        Args:
            tags: Tags to search for
            match_all: If True, grimoire must have all tags

        Returns:
            List of matching grimoires
        """
        results = []
        tag_set = set(tags)

        for grimoire in self._grimoires.values():
            grimoire_tags = set(grimoire.tags)
            if match_all:
                if tag_set.issubset(grimoire_tags):
                    results.append(grimoire)
            else:
                if tag_set & grimoire_tags:
                    results.append(grimoire)

        return results

    def list_all(self) -> List[Grimoire]:
        """Get all registered grimoires.

        Returns:
            List of all grimoires
        """
        return list(self._grimoires.values())

    def list_categories(self) -> List[str]:
        """Get all registered categories.

        Returns:
            List of category names
        """
        return sorted(self._by_category.keys())

    def list_skills(self) -> List[str]:
        """Get all registered skill names.

        Returns:
            List of skill names
        """
        return sorted(self._by_skill.keys())

    def load_from_file(self, path: Path) -> int:
        """Load grimoires from a JSON file.

        Args:
            path: Path to JSON file containing grimoire definitions

        Returns:
            Number of grimoires loaded
        """
        path_str = str(path.resolve())
        if path_str in self._loaded_sources:
            logger.debug(f"Already loaded: {path}")
            return 0

        if not path.exists():
            logger.warning(f"Grimoire file not found: {path}")
            return 0

        try:
            with open(path) as f:
                data = json.load(f)

            count = 0
            grimoires = data if isinstance(data, list) else [data]

            for grimoire_data in grimoires:
                grimoire = Grimoire.from_dict(grimoire_data)
                self.register(grimoire)
                count += 1

            self._loaded_sources.add(path_str)
            logger.info(f"Loaded {count} grimoires from {path}")
            return count

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {path}: {e}")
            return 0
        except Exception as e:
            logger.error(f"Error loading {path}: {e}")
            return 0

    def load_from_directory(self, directory: Path) -> int:
        """Load all grimoires from a directory.

        Args:
            directory: Directory containing grimoire JSON files

        Returns:
            Total number of grimoires loaded
        """
        if not directory.exists():
            logger.warning(f"Grimoire directory not found: {directory}")
            return 0

        total = 0
        for path in directory.glob("*.json"):
            total += self.load_from_file(path)

        return total

    def load_builtin(self) -> int:
        """Load built-in grimoires shipped with VKG.

        Returns:
            Number of grimoires loaded
        """
        builtin_dir = Path(__file__).parent / "builtin"
        if builtin_dir.exists():
            return self.load_from_directory(builtin_dir)

        # No built-in grimoires yet - that's OK for initial implementation
        logger.debug("No built-in grimoires directory found")
        return 0

    def load_project(self, project_path: Path) -> int:
        """Load project-specific grimoires from .vrs directory.

        Args:
            project_path: Root of the project

        Returns:
            Number of grimoires loaded
        """
        vkg_dir = project_path / ".vrs" / "grimoires"
        if vkg_dir.exists():
            return self.load_from_directory(vkg_dir)
        return 0

    def save_to_file(self, path: Path, grimoire_ids: Optional[List[str]] = None) -> int:
        """Save grimoires to a JSON file.

        Args:
            path: Path to write to
            grimoire_ids: Optional list of grimoire IDs to save (all if None)

        Returns:
            Number of grimoires saved
        """
        if grimoire_ids:
            grimoires = [
                self._grimoires[gid]
                for gid in grimoire_ids
                if gid in self._grimoires
            ]
        else:
            grimoires = list(self._grimoires.values())

        data = [g.to_dict() for g in grimoires]

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        return len(grimoires)

    def clear(self) -> None:
        """Clear all registered grimoires."""
        self._grimoires.clear()
        self._by_category.clear()
        self._by_skill.clear()
        self._loaded_sources.clear()

    def __len__(self) -> int:
        """Get number of registered grimoires."""
        return len(self._grimoires)

    def __contains__(self, grimoire_id: str) -> bool:
        """Check if grimoire is registered."""
        return grimoire_id in self._grimoires


# Global registry instance
_global_registry: Optional[GrimoireRegistry] = None


def get_registry() -> GrimoireRegistry:
    """Get the global grimoire registry.

    Creates and initializes the registry on first call.

    Returns:
        Global GrimoireRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = GrimoireRegistry()
        _global_registry.load_builtin()
    return _global_registry


def get_grimoire(grimoire_id: str) -> Optional[Grimoire]:
    """Get a grimoire by ID from the global registry.

    Args:
        grimoire_id: Grimoire identifier

    Returns:
        Grimoire if found, None otherwise
    """
    return get_registry().get(grimoire_id)


def list_grimoires() -> List[Grimoire]:
    """List all grimoires from the global registry.

    Returns:
        List of all registered grimoires
    """
    return get_registry().list_all()


def get_grimoire_for_category(category: str) -> Optional[Grimoire]:
    """Get the primary grimoire for a vulnerability category.

    If multiple grimoires exist for a category, returns the first one
    (typically the most general one).

    Args:
        category: Vulnerability category

    Returns:
        Primary grimoire for category, or None
    """
    grimoires = get_registry().find_by_category(category)
    return grimoires[0] if grimoires else None


def register_grimoire(grimoire: Grimoire) -> None:
    """Register a grimoire in the global registry.

    Args:
        grimoire: Grimoire to register
    """
    get_registry().register(grimoire)


def reset_registry() -> None:
    """Reset the global registry (mainly for testing)."""
    global _global_registry
    _global_registry = None
