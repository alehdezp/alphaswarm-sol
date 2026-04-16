"""Template loader for investigation guides.

This module loads YAML investigation templates and converts them into
InvestigationGuide objects that can be used in VulnerabilityBead creation.

Available templates:
- reentrancy: Classic, cross-function, cross-contract reentrancy
- access_control: Missing access control, privilege escalation
- oracle: Staleness, manipulation, missing checks
- dos: Unbounded loops, griefing, revert bombs
- mev: Frontrunning, sandwich, slippage
- token: ERC20 issues, fee-on-transfer, return values
- upgrade: Proxy issues, storage collision, initialization

Usage:
    from alphaswarm_sol.beads.templates import load_template, list_available_templates

    # Load a specific template
    guide = load_template("reentrancy")

    # List all available templates
    templates = list_available_templates()

    # Get template version
    version = get_template_version("reentrancy")
"""

from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

from ..schema import InvestigationGuide
from ..types import InvestigationStep


TEMPLATES_DIR = Path(__file__).parent

# Cache loaded templates to avoid repeated disk reads
_template_cache: Dict[str, Dict[str, Any]] = {}


def _load_yaml(template_path: Path) -> Optional[Dict[str, Any]]:
    """Load and cache YAML template data.

    Args:
        template_path: Path to YAML file

    Returns:
        Parsed YAML data or None if file doesn't exist
    """
    cache_key = str(template_path)
    if cache_key in _template_cache:
        return _template_cache[cache_key]

    if not template_path.exists():
        return None

    with open(template_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    _template_cache[cache_key] = data
    return data


def load_template(vulnerability_class: str) -> Optional[InvestigationGuide]:
    """Load investigation template for a vulnerability class.

    Loads a YAML template and converts it into an InvestigationGuide
    object suitable for use in VulnerabilityBead creation.

    Args:
        vulnerability_class: One of: reentrancy, access_control, oracle,
                            dos, mev, token, upgrade

    Returns:
        InvestigationGuide if template exists, None otherwise

    Example:
        guide = load_template("reentrancy")
        if guide:
            print(f"Loaded {len(guide.steps)} investigation steps")
    """
    # Normalize class name to match file naming convention
    class_name = vulnerability_class.lower().replace("-", "_").replace(" ", "_")
    template_path = TEMPLATES_DIR / f"{class_name}.yaml"

    data = _load_yaml(template_path)
    if data is None:
        return None

    # Convert investigation_steps from YAML to InvestigationStep objects
    steps = []
    for step_data in data.get("investigation_steps", []):
        step = InvestigationStep(
            step_number=step_data.get("step_number", 0),
            action=step_data.get("action", ""),
            look_for=step_data.get("look_for", ""),
            evidence_needed=step_data.get("evidence_needed", ""),
            red_flag=step_data.get("red_flag"),
            safe_if=step_data.get("safe_if"),
        )
        steps.append(step)

    return InvestigationGuide(
        steps=steps,
        questions_to_answer=data.get("questions_to_answer", []),
        common_false_positives=data.get("common_false_positives", []),
        key_indicators=data.get("key_indicators", []),
        safe_patterns=data.get("safe_patterns", []),
    )


def list_available_templates() -> List[str]:
    """List all available vulnerability class templates.

    Scans the templates directory for YAML files and returns
    their names (without .yaml extension).

    Returns:
        List of template names (e.g., ["reentrancy", "access_control", ...])

    Example:
        templates = list_available_templates()
        print(f"Found {len(templates)} templates")
        for t in templates:
            print(f"  - {t}")
    """
    templates = []
    for path in TEMPLATES_DIR.glob("*.yaml"):
        # Skip any private/hidden files
        if path.name.startswith("_"):
            continue
        templates.append(path.stem)
    return sorted(templates)


def get_template_version(vulnerability_class: str) -> Optional[str]:
    """Get version of a template.

    Templates include a version field for tracking updates.
    This allows checking if a template has been updated.

    Args:
        vulnerability_class: One of: reentrancy, access_control, oracle,
                            dos, mev, token, upgrade

    Returns:
        Version string (e.g., "1.0") or None if template doesn't exist

    Example:
        version = get_template_version("reentrancy")
        print(f"Template version: {version}")
    """
    class_name = vulnerability_class.lower().replace("-", "_").replace(" ", "_")
    template_path = TEMPLATES_DIR / f"{class_name}.yaml"

    data = _load_yaml(template_path)
    if data is None:
        return None

    return str(data.get("version", ""))


def get_template_metadata(vulnerability_class: str) -> Optional[Dict[str, Any]]:
    """Get full metadata for a template.

    Returns all non-content metadata from the template including
    version, last_updated, and vulnerability_class fields.

    Args:
        vulnerability_class: One of: reentrancy, access_control, oracle,
                            dos, mev, token, upgrade

    Returns:
        Dict with version, last_updated, vulnerability_class or None

    Example:
        meta = get_template_metadata("reentrancy")
        print(f"Last updated: {meta['last_updated']}")
    """
    class_name = vulnerability_class.lower().replace("-", "_").replace(" ", "_")
    template_path = TEMPLATES_DIR / f"{class_name}.yaml"

    data = _load_yaml(template_path)
    if data is None:
        return None

    return {
        "vulnerability_class": data.get("vulnerability_class", class_name),
        "version": str(data.get("version", "")),
        "last_updated": str(data.get("last_updated", "")),
    }


def clear_cache() -> None:
    """Clear the template cache.

    Useful when templates are modified during development
    or testing and need to be reloaded.

    Example:
        clear_cache()
        guide = load_template("reentrancy")  # Forces fresh load
    """
    global _template_cache
    _template_cache = {}


# Export for module
__all__ = [
    "load_template",
    "list_available_templates",
    "get_template_version",
    "get_template_metadata",
    "clear_cache",
]
