#!/usr/bin/env python
"""
Update skill golden output fixtures.

This script helps maintain golden test fixtures for skill output validation.
It can validate existing goldens against schemas or provide guidance for manual updates.

Usage:
    python scripts/update_skill_goldens.py [--validate-only] [--verbose]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from jsonschema import ValidationError, validate
except ImportError:
    print("Error: jsonschema not installed. Run: uv pip install jsonschema")
    sys.exit(1)


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).resolve().parent.parent


def load_json_file(path: Path) -> Dict:
    """Load JSON file."""
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")


def validate_golden(
    golden_path: Path, schema_path: Path, verbose: bool = False
) -> Tuple[bool, List[str]]:
    """Validate a golden file against its schema."""
    errors = []

    if not golden_path.exists():
        errors.append(f"Golden file not found: {golden_path}")
        return False, errors

    if not schema_path.exists():
        errors.append(f"Schema file not found: {schema_path}")
        return False, errors

    try:
        golden = load_json_file(golden_path)
        schema = load_json_file(schema_path)

        validate(instance=golden, schema=schema)

        if verbose:
            print(f"✓ {golden_path.name}: Valid")
        return True, []

    except ValidationError as e:
        errors.append(f"{golden_path.name}: {e.message}")
        if verbose:
            print(f"✗ {golden_path.name}: {e.message}")
        return False, errors

    except Exception as e:
        errors.append(f"{golden_path.name}: {str(e)}")
        if verbose:
            print(f"✗ {golden_path.name}: {str(e)}")
        return False, errors


def validate_all_goldens(verbose: bool = False) -> Tuple[int, int]:
    """Validate all golden fixtures against their schemas."""
    project_root = get_project_root()
    goldens_dir = project_root / "tests" / "skills" / "goldens"
    schemas_dir = project_root / "schemas"

    # Define golden -> schema mappings
    golden_schema_map = {
        "secure_reviewer.json": "secure_reviewer_output.json",
        # Add more mappings when schemas are available
        # "attacker.json": "attacker_output.json",
        # "defender.json": "defender_output.json",
        # "verifier.json": "verifier_output.json",
    }

    passed = 0
    failed = 0
    all_errors = []

    print(f"\nValidating golden fixtures in {goldens_dir}\n")

    for golden_name, schema_name in golden_schema_map.items():
        golden_path = goldens_dir / golden_name
        schema_path = schemas_dir / schema_name

        is_valid, errors = validate_golden(golden_path, schema_path, verbose)

        if is_valid:
            passed += 1
        else:
            failed += 1
            all_errors.extend(errors)

    # Check for goldens without schemas
    for golden_file in goldens_dir.glob("*.json"):
        if golden_file.name not in golden_schema_map:
            if verbose:
                print(f"⚠ {golden_file.name}: No schema defined (skipped)")

    print(f"\nResults: {passed} passed, {failed} failed")

    if all_errors:
        print("\nErrors:")
        for error in all_errors:
            print(f"  - {error}")

    return passed, failed


def print_update_guide():
    """Print guidance for updating golden fixtures."""
    print("""
Golden Update Guide
===================

Golden fixtures are manually maintained. To update:

1. Edit JSON files directly in tests/skills/goldens/
2. Ensure changes match the skill's output contract
3. Validate: python scripts/update_skill_goldens.py --validate-only
4. Run tests: uv run pytest tests/skills/test_skill_goldens.py -v

Golden Fixture Checklist:
-------------------------
☐ All required fields present (per schema)
☐ Evidence items have code_location OR graph_node_id (not both)
☐ Confidence scores between 0.0 and 1.0
☐ Graph queries present (graph-first requirement)
☐ Mode-specific fields included (creative_hypotheses or refutations)
☐ No actual vulnerability data from real projects
☐ Data is deterministic (no timestamps, UUIDs, or random values)

Available Schemas:
------------------
- schemas/secure_reviewer_output.json (for secure_reviewer.json)
- More schemas to be added as output contracts are defined

For more details, see: tests/skills/goldens/README.md
""")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update and validate skill golden output fixtures"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing goldens, don't regenerate",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )
    parser.add_argument(
        "--guide",
        action="store_true",
        help="Print update guide and exit",
    )

    args = parser.parse_args()

    if args.guide:
        print_update_guide()
        return 0

    # Currently we only support validation
    # Automatic regeneration would require templates or model calls
    if args.validate_only or True:  # Always validate for now
        passed, failed = validate_all_goldens(verbose=args.verbose)

        if failed > 0:
            print("\n💡 Tip: Use --guide for update instructions")
            return 1

        print("\n✓ All golden fixtures are valid")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
