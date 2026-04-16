"""Scaffold creation utilities for VulnDocs framework.

This module provides utilities for creating new vulnerabilities, categories,
and patterns from templates.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class TemplateRenderer:
    """Renders templates with variable substitution."""

    def __init__(self, template_content: str):
        """Initialize renderer with template content.

        Args:
            template_content: Template string with {{variable}} placeholders
        """
        self.template = template_content

    def render(self, variables: Dict[str, str]) -> str:
        """Render template with provided variables.

        Args:
            variables: Dictionary of variable name -> value

        Returns:
            Rendered template string
        """
        result = self.template
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, value)
        return result


def validate_scaffold_inputs(category: str, subcategory: str) -> List[str]:
    """Validate inputs for scaffold creation.

    Checks:
    - Lowercase with hyphens only
    - No invalid characters
    - Reasonable length

    Args:
        category: Category name
        subcategory: Subcategory name

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Pattern for valid names: lowercase letters, numbers, hyphens
    valid_pattern = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')

    if not valid_pattern.match(category):
        errors.append(
            f"Category '{category}' must be lowercase with hyphens only "
            f"(e.g., 'oracle', 'access-control')"
        )

    if not valid_pattern.match(subcategory):
        errors.append(
            f"Subcategory '{subcategory}' must be lowercase with hyphens only "
            f"(e.g., 'price-manipulation', 'weak-randomness')"
        )

    if len(category) < 2 or len(category) > 50:
        errors.append("Category name must be 2-50 characters")

    if len(subcategory) < 2 or len(subcategory) > 50:
        errors.append("Subcategory name must be 2-50 characters")

    return errors


def scaffold_category(root: Path, category_id: str, name: str) -> Path:
    """Create a new category folder from template.

    Args:
        root: Root vulndocs directory
        category_id: Category ID (e.g., 'oracle')
        name: Display name (e.g., 'Oracle Vulnerabilities')

    Returns:
        Path to created category folder

    Raises:
        FileExistsError: If category already exists
        FileNotFoundError: If template not found
    """
    category_path = root / category_id

    if category_path.exists():
        raise FileExistsError(f"Category already exists: {category_path}")

    # Create category folder
    category_path.mkdir(parents=True, exist_ok=False)

    # Load template from .meta/templates
    template_path = root / ".meta" / "templates" / "category.yaml"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    template_content = template_path.read_text()

    # Render template
    renderer = TemplateRenderer(template_content)
    content = renderer.render({
        "category": category_id,
        "name": name,
        "date": datetime.now().strftime("%Y-%m-%d"),
    })

    # Write overview.md
    overview_path = category_path / "overview.md"
    overview_path.write_text(content)

    return category_path


def scaffold_vulnerability(
    root: Path,
    category: str,
    subcategory: str,
    severity: str = "medium",
) -> Path:
    """Create a new vulnerability folder from template.

    Creates the full vulnerability structure:
    - category/subcategory/ folder
    - index.yaml with metadata
    - overview.md, detection.md, verification.md, exploits.md
    - patterns/ subfolder

    Args:
        root: Root vulndocs directory
        category: Category ID
        subcategory: Subcategory ID
        severity: Severity level (critical, high, medium, low)

    Returns:
        Path to created vulnerability folder

    Raises:
        FileExistsError: If vulnerability already exists
        FileNotFoundError: If template not found
    """
    # Validate inputs
    errors = validate_scaffold_inputs(category, subcategory)
    if errors:
        raise ValueError(f"Invalid input: {', '.join(errors)}")

    vuln_path = root / category / subcategory

    if vuln_path.exists():
        raise FileExistsError(f"Vulnerability already exists: {vuln_path}")

    # Create vulnerability folder
    vuln_path.mkdir(parents=True, exist_ok=False)

    # Create patterns subfolder
    patterns_path = vuln_path / "patterns"
    patterns_path.mkdir(exist_ok=True)

    # Template directory from .meta/templates
    template_dir = root / ".meta" / "templates" / "subcategory"
    if not template_dir.exists():
        raise FileNotFoundError(f"Template directory not found: {template_dir}")

    # Template variables
    variables = {
        "category": category,
        "subcategory": subcategory,
        "severity": severity,
        "vulndoc": f"{category}/{subcategory}",
        "date": datetime.now().strftime("%Y-%m-%d"),
    }

    # Copy and render all template files
    template_files = [
        "index.yaml",
        "overview.md",
        "detection.md",
        "verification.md",
        "exploits.md",
    ]

    for filename in template_files:
        template_path = template_dir / filename
        if not template_path.exists():
            # Skip optional templates
            continue

        template_content = template_path.read_text()
        renderer = TemplateRenderer(template_content)
        content = renderer.render(variables)

        output_path = vuln_path / filename
        output_path.write_text(content)

    return vuln_path


def scaffold_pattern(
    vuln_path: Path,
    pattern_id: str,
    name: str,
) -> Path:
    """Create a new pattern YAML from template.

    Args:
        vuln_path: Path to vulnerability folder
        pattern_id: Pattern ID (e.g., 'oracle-001-twap')
        name: Display name (e.g., 'TWAP Manipulation')

    Returns:
        Path to created pattern file

    Raises:
        FileExistsError: If pattern already exists
        FileNotFoundError: If template or vulnerability not found
    """
    if not vuln_path.exists():
        raise FileNotFoundError(f"Vulnerability folder not found: {vuln_path}")

    patterns_dir = vuln_path / "patterns"
    patterns_dir.mkdir(exist_ok=True)

    pattern_path = patterns_dir / f"{pattern_id}.yaml"

    if pattern_path.exists():
        raise FileExistsError(f"Pattern already exists: {pattern_path}")

    # Load template
    # Navigate up to find vulndocs root
    current = vuln_path
    while current.name not in ("vulndocs", "") and current.parent != current:
        current = current.parent

    if current.name != "vulndocs":
        # Try relative to vuln_path - use .meta/templates
        template_path = vuln_path.parent.parent / ".meta" / "templates" / "pattern.yaml"
    else:
        template_path = current / ".meta" / "templates" / "pattern.yaml"

    if not template_path.exists():
        raise FileNotFoundError(f"Pattern template not found: {template_path}")

    template_content = template_path.read_text()

    # Extract vulndoc path from vuln_path
    # vuln_path should be like: .../vulndocs/category/subcategory
    parts = vuln_path.parts
    if len(parts) >= 2:
        category = parts[-2]
        subcategory = parts[-1]
        vulndoc = f"{category}/{subcategory}"
    else:
        vulndoc = "category/subcategory"

    # Render template
    renderer = TemplateRenderer(template_content)
    content = renderer.render({
        "pattern_id": pattern_id,
        "name": name,
        "vulndoc": vulndoc,
    })

    pattern_path.write_text(content)

    return pattern_path
