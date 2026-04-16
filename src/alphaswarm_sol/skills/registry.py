"""
Skill registry loader and validation.

Provides:
- list_registry() - List all registered skills
- get_skill_entry(id) - Get specific skill by ID
- validate_registry() - Validate registry against schema
- filter_by_status() - Filter skills by lifecycle status
- filter_by_category() - Filter skills by category
- list_deprecated() - List deprecated and sunset skills
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml


# Project root detection
def _find_project_root() -> Path:
    """Find project root by looking for pyproject.toml."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not find project root (pyproject.toml not found)")


PROJECT_ROOT = _find_project_root()
REGISTRY_PATH = PROJECT_ROOT / "src" / "alphaswarm_sol" / "skills" / "registry.yaml"
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "skill_registry_v1.json"


def load_registry() -> Dict[str, Any]:
    """
    Load skill registry from YAML file.

    Returns:
        Registry dictionary with version and skills list

    Raises:
        FileNotFoundError: If registry file doesn't exist
        yaml.YAMLError: If registry file is invalid YAML
    """
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Registry not found: {REGISTRY_PATH}")

    with open(REGISTRY_PATH, "r") as f:
        return yaml.safe_load(f)


def list_registry() -> List[Dict[str, Any]]:
    """
    List all skills in registry.

    Returns:
        List of skill entry dictionaries
    """
    registry = load_registry()
    return registry.get("skills", [])


def get_skill_entry(skill_id: str) -> Optional[Dict[str, Any]]:
    """
    Get specific skill entry by ID.

    Args:
        skill_id: Skill identifier (kebab-case)

    Returns:
        Skill entry dictionary or None if not found
    """
    skills = list_registry()
    for skill in skills:
        if skill.get("id") == skill_id:
            return skill
    return None


def filter_by_status(status: str) -> List[Dict[str, Any]]:
    """
    Filter skills by lifecycle status.

    Args:
        status: One of "active", "deprecated", "experimental", "sunset"

    Returns:
        List of skill entries with matching status
    """
    skills = list_registry()
    return [s for s in skills if s.get("status") == status]


def filter_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Filter skills by category.

    Args:
        category: Category name (e.g., "orchestration", "investigation")

    Returns:
        List of skill entries in category
    """
    skills = list_registry()
    return [s for s in skills if s.get("category") == category]


def list_deprecated() -> List[Dict[str, Any]]:
    """
    List all deprecated and sunset skills.

    Returns:
        List of skill entries with status "deprecated" or "sunset"
    """
    skills = list_registry()
    return [s for s in skills if s.get("status") in ["deprecated", "sunset"]]


def list_shipped() -> List[Dict[str, Any]]:
    """
    List skills with shipped location.

    Returns:
        List of skill entries with shipped location set
    """
    skills = list_registry()
    return [
        s for s in skills
        if s.get("location", {}).get("shipped") is not None
    ]


def list_dev_only() -> List[Dict[str, Any]]:
    """
    List dev-only skills (no shipped location).

    Returns:
        List of skill entries without shipped location
    """
    skills = list_registry()
    return [
        s for s in skills
        if s.get("location", {}).get("shipped") is None
    ]


def validate_registry() -> List[str]:
    """
    Validate registry against schema and integrity rules.

    Checks:
    - Schema validation (if jsonschema available)
    - No duplicate IDs
    - Valid version strings (semantic versioning)
    - Required fields present
    - File paths exist (if specified)
    - Replacement references valid

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Load registry
    try:
        registry = load_registry()
    except Exception as e:
        return [f"Failed to load registry: {e}"]

    # Validate schema if jsonschema available
    try:
        import jsonschema
        with open(SCHEMA_PATH, "r") as f:
            schema = json.load(f)
        try:
            jsonschema.validate(registry, schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation failed: {e.message}")
    except ImportError:
        # jsonschema not available, skip schema validation
        pass

    skills = registry.get("skills", [])

    # Check for duplicate IDs
    ids = [s.get("id") for s in skills]
    duplicates = [skill_id for skill_id in ids if ids.count(skill_id) > 1]
    if duplicates:
        errors.append(f"Duplicate skill IDs: {set(duplicates)}")

    # Validate each skill entry
    for i, skill in enumerate(skills):
        skill_id = skill.get("id", f"skill-{i}")

        # Required fields
        for field in ["id", "name", "version", "status"]:
            if field not in skill:
                errors.append(f"[{skill_id}] Missing required field: {field}")

        # Version format (semantic versioning)
        version = skill.get("version", "")
        if version:
            parts = version.split(".")
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                errors.append(f"[{skill_id}] Invalid version format: {version} (expected X.Y.Z)")

        # Status enum
        status = skill.get("status")
        valid_statuses = ["active", "deprecated", "experimental", "sunset"]
        if status and status not in valid_statuses:
            errors.append(f"[{skill_id}] Invalid status: {status} (expected one of {valid_statuses})")

        # Location file existence
        location = skill.get("location", {})
        for loc_type in ["shipped", "dev"]:
            loc_path = location.get(loc_type)
            if loc_path:
                full_path = PROJECT_ROOT / loc_path
                if not full_path.exists():
                    errors.append(f"[{skill_id}] Location file not found: {loc_path}")

        # At least one location must be specified
        if not location.get("shipped") and not location.get("dev"):
            errors.append(f"[{skill_id}] No location specified (shipped or dev required)")

        # Replacement references
        replaces = skill.get("replaces")
        if replaces:
            if replaces not in ids:
                errors.append(f"[{skill_id}] replaces references unknown skill: {replaces}")

        deprecated_by = skill.get("deprecated_by")
        if deprecated_by:
            if deprecated_by not in ids:
                errors.append(f"[{skill_id}] deprecated_by references unknown skill: {deprecated_by}")

    return errors


def check_duplicates() -> List[str]:
    """
    Check for duplicate skill IDs.

    Returns:
        List of duplicate skill IDs
    """
    skills = list_registry()
    ids = [s.get("id") for s in skills]
    return list(set([skill_id for skill_id in ids if ids.count(skill_id) > 1]))


def get_registry_stats() -> Dict[str, Any]:
    """
    Get registry statistics.

    Returns:
        Dictionary with stats:
        - total: Total number of skills
        - by_status: Count by status
        - by_category: Count by category
        - shipped: Number with shipped location
        - dev_only: Number without shipped location
    """
    skills = list_registry()

    stats = {
        "total": len(skills),
        "by_status": {},
        "by_category": {},
        "shipped": 0,
        "dev_only": 0,
    }

    for skill in skills:
        # Count by status
        status = skill.get("status", "unknown")
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

        # Count by category
        category = skill.get("category", "uncategorized")
        stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

        # Count location types
        location = skill.get("location", {})
        if location.get("shipped"):
            stats["shipped"] += 1
        else:
            stats["dev_only"] += 1

    return stats


def main():
    """CLI entry point for registry operations."""
    import sys

    if len(sys.argv) < 2:
        print("Skill Registry")
        print("\nUsage:")
        print("  python -m alphaswarm_sol.skills.registry validate")
        print("  python -m alphaswarm_sol.skills.registry check-duplicates")
        print("  python -m alphaswarm_sol.skills.registry list-deprecated")
        print("  python -m alphaswarm_sol.skills.registry stats")
        sys.exit(1)

    command = sys.argv[1]

    if command == "validate":
        errors = validate_registry()
        if errors:
            print("❌ Registry validation failed:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print("✅ Registry is valid")
            stats = get_registry_stats()
            print(f"\nRegistered skills: {stats['total']}")
            print(f"  Active: {stats['by_status'].get('active', 0)}")
            print(f"  Deprecated: {stats['by_status'].get('deprecated', 0)}")
            print(f"  Experimental: {stats['by_status'].get('experimental', 0)}")
            print(f"  Sunset: {stats['by_status'].get('sunset', 0)}")

    elif command == "check-duplicates":
        duplicates = check_duplicates()
        if duplicates:
            print("❌ Duplicate skill IDs found:")
            for dup in duplicates:
                print(f"  - {dup}")
            sys.exit(1)
        else:
            print("✅ No duplicate IDs")

    elif command == "list-deprecated":
        deprecated = list_deprecated()
        if deprecated:
            print(f"Deprecated/Sunset skills ({len(deprecated)}):")
            for skill in deprecated:
                print(f"  - {skill['id']} ({skill['status']})")
                if skill.get('deprecated_by'):
                    print(f"    → Use: {skill['deprecated_by']}")
                if skill.get('sunset_date'):
                    print(f"    ⚠️  Sunset: {skill['sunset_date']}")
        else:
            print("No deprecated skills")

    elif command == "stats":
        stats = get_registry_stats()
        print(f"Registry Statistics")
        print(f"\nTotal skills: {stats['total']}")
        print(f"\nBy status:")
        for status, count in sorted(stats['by_status'].items()):
            print(f"  {status}: {count}")
        print(f"\nBy category:")
        for category, count in sorted(stats['by_category'].items()):
            print(f"  {category}: {count}")
        print(f"\nBy location:")
        print(f"  Shipped: {stats['shipped']}")
        print(f"  Dev-only: {stats['dev_only']}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
