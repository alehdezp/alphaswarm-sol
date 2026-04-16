"""Skills for True VKG.

Task 18.2: Vulnerability knowledge mining skills.

Available Skills:
- /vuln-crawl: Crawl vulnerability sources (Haiku workers)
- /vuln-process: Process content into summaries (Haiku workers)
- /vuln-merge: Merge summaries into documents (Opus orchestrator)
- /vuln-link: Link documents to VKG patterns (Opus linker)
- /vuln-build: Full pipeline orchestrator

Shipped VRS Skills:
The shipping/ module contains skills and agents that are distributed to target
projects via `alphaswarm init`. These are the user-facing skills for the
VRS product (audit, investigate, verify, debate, health-check).

Usage:
    # In Claude Code, invoke skills with:
    /vuln-build reentrancy
    /vuln-crawl --category oracle
    /vuln-merge --all
"""

from pathlib import Path

from alphaswarm_sol.skills.vuln_build import (
    VulnBuildSkill,
    vuln_build_skill,
)
from alphaswarm_sol.skills.registry import (
    list_registry,
    get_skill_entry,
    validate_registry,
    filter_by_status,
    filter_by_category,
    list_deprecated,
    list_shipped,
    list_dev_only,
    get_registry_stats,
)

__all__ = [
    "VulnBuildSkill",
    "vuln_build_skill",
    "get_shipped_skills_path",
    "list_shipped_skills",
    # Registry API
    "list_registry",
    "get_skill_entry",
    "validate_registry",
    "filter_by_status",
    "filter_by_category",
    "list_deprecated",
    "list_shipped",
    "list_dev_only",
    "get_registry_stats",
]


def get_shipped_skills_path() -> Path:
    """Return path to shipped skills directory.

    Delegates to the canonical shipping module.

    Returns:
        Path to the shipping/skills/ directory containing skill markdown files.
    """
    from alphaswarm_sol.shipping import get_shipped_skills_path as _get_path
    return _get_path()


def list_shipped_skills() -> list[str]:
    """List all shipped skill files.

    Returns:
        List of skill filenames (*.md) excluding README.md.
    """
    skills_dir = get_shipped_skills_path()
    return sorted(
        f.name for f in skills_dir.glob("*.md") if f.name != "README.md"
    )
