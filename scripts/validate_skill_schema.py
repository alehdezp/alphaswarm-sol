#!/usr/bin/env python3
"""
Validate skill frontmatter against schema v2.

Usage:
    python scripts/validate_skill_schema.py .claude/skills/vrs/audit.md
    python scripts/validate_skill_schema.py .claude/skills/
    python scripts/validate_skill_schema.py --strict src/alphaswarm_sol/shipping/skills/
    python scripts/validate_skill_schema.py --warn .claude/skills/
"""

import sys
from pathlib import Path
from typing import Optional

import click

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.alphaswarm_sol.skills.skill_schema import validate_skill_schema


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Fail on missing frontmatter (default: warn only)"
)
@click.option(
    "--warn",
    is_flag=True,
    default=False,
    help="Warn mode: report violations but don't fail (exit 0)"
)
@click.option(
    "--schema",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to skill_schema_v2.json (auto-detected if omitted)"
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Output results as JSON"
)
def main(
    path: Path,
    strict: bool,
    warn: bool,
    schema: Optional[Path],
    output_json: bool
):
    """
    Validate skill frontmatter against schema v2.

    PATH can be a single skill .md file or a directory to scan recursively.

    Modes:
    - Default: Fail if frontmatter is invalid (missing fields, wrong types)
    - --strict: Also fail if frontmatter is missing entirely
    - --warn: Report violations but exit 0 (useful for gradual migration)
    """
    is_valid, errors = validate_skill_schema(path, strict=strict, schema_path=schema)

    if output_json:
        import json
        result = {
            "valid": is_valid,
            "path": str(path),
            "errors": errors
        }
        click.echo(json.dumps(result, indent=2))
    else:
        # Human-readable output
        if is_valid:
            click.secho("✓ Validation passed", fg="green")
            for msg in errors:
                click.echo(f"  {msg}")
        else:
            click.secho("✗ Validation failed", fg="red")
            for msg in errors:
                if msg.startswith("WARNING:"):
                    click.secho(f"  {msg}", fg="yellow")
                else:
                    click.secho(f"  {msg}", fg="red")

    # Exit code logic
    if warn:
        # Warn mode: always exit 0
        sys.exit(0)
    else:
        # Normal mode: exit 1 if invalid
        sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
