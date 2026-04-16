#!/usr/bin/env python3
"""Validate all Use Case Scenario YAML files against the schema.

Loads every .yaml file under .planning/testing/scenarios/use-cases/ (recursively,
excluding _schema.yaml), checks required fields, valid enum values, and ID format.

Exit code 0 if all valid, 1 if any errors.

Usage:
    python scripts/validate_scenarios.py
    python scripts/validate_scenarios.py --verbose
    python scripts/validate_scenarios.py --path .planning/testing/scenarios/use-cases/audit/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCENARIOS_DIR = PROJECT_ROOT / ".planning" / "testing" / "scenarios" / "use-cases"

ID_PATTERN = re.compile(r"^UC-[A-Z]+-\d{3}$")

VALID_WORKFLOWS = {
    "vrs-audit",
    "vrs-investigate",
    "vrs-verify",
    "vrs-debate",
    "vrs-attacker",
    "vrs-defender",
    "vrs-health-check",
    "graph-build",
    "tool-run",
    "failure",
}

VALID_CATEGORIES = {
    "audit",
    "investigate",
    "verify",
    "debate",
    "agents",
    "tools",
    "graph",
    "failure",
    "cross-workflow",
}

VALID_TIERS = {"core", "important", "mechanical"}

VALID_STATUSES = {"draft", "ready", "validated", "broken"}


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------


def validate_scenario(filepath: Path, verbose: bool = False) -> list[str]:
    """Validate a single scenario YAML file.

    Returns a list of error strings. Empty list means valid.
    """
    errors: list[str] = []

    # Load YAML
    try:
        with open(filepath) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"]

    if not isinstance(data, dict):
        return ["File does not contain a YAML mapping (expected top-level dict)"]

    # --- Required top-level fields ---

    # id
    scenario_id = data.get("id")
    if not scenario_id:
        errors.append("Missing required field: id")
    elif not isinstance(scenario_id, str):
        errors.append(f"id must be a string, got {type(scenario_id).__name__}")
    elif not ID_PATTERN.match(scenario_id):
        errors.append(f"id '{scenario_id}' does not match pattern UC-[A-Z]+-NNN")

    # name
    name = data.get("name")
    if not name:
        errors.append("Missing required field: name")
    elif not isinstance(name, str):
        errors.append(f"name must be a string, got {type(name).__name__}")

    # workflow
    workflow = data.get("workflow")
    if not workflow:
        errors.append("Missing required field: workflow")
    elif workflow not in VALID_WORKFLOWS:
        errors.append(f"workflow '{workflow}' not in valid set: {sorted(VALID_WORKFLOWS)}")

    # category
    category = data.get("category")
    if not category:
        errors.append("Missing required field: category")
    elif category not in VALID_CATEGORIES:
        errors.append(f"category '{category}' not in valid set: {sorted(VALID_CATEGORIES)}")

    # tier
    tier = data.get("tier")
    if not tier:
        errors.append("Missing required field: tier")
    elif tier not in VALID_TIERS:
        errors.append(f"tier '{tier}' not in valid set: {sorted(VALID_TIERS)}")

    # status
    status = data.get("status")
    if not status:
        errors.append("Missing required field: status")
    elif status not in VALID_STATUSES:
        errors.append(f"status '{status}' not in valid set: {sorted(VALID_STATUSES)}")

    # --- input ---
    input_data = data.get("input")
    if not input_data:
        errors.append("Missing required field: input")
    elif not isinstance(input_data, dict):
        errors.append("input must be a mapping")
    else:
        for field in ("contract", "command", "context"):
            val = input_data.get(field)
            if not val:
                errors.append(f"Missing required field: input.{field}")
            elif not isinstance(val, str):
                errors.append(f"input.{field} must be a string")

    # --- expected_behavior ---
    eb = data.get("expected_behavior")
    if not eb:
        errors.append("Missing required field: expected_behavior")
    elif not isinstance(eb, dict):
        errors.append("expected_behavior must be a mapping")
    else:
        if not eb.get("summary"):
            errors.append("Missing required field: expected_behavior.summary")

        for list_field in ("must_happen", "must_not_happen"):
            val = eb.get(list_field)
            if val is None:
                errors.append(f"Missing required field: expected_behavior.{list_field}")
            elif not isinstance(val, list):
                errors.append(f"expected_behavior.{list_field} must be a list")
            elif len(val) == 0:
                errors.append(f"expected_behavior.{list_field} must not be empty")
            else:
                for i, item in enumerate(val):
                    if not isinstance(item, str):
                        errors.append(
                            f"expected_behavior.{list_field}[{i}] must be a string"
                        )

        # Optional: expected_findings
        ef = eb.get("expected_findings")
        if ef is not None:
            if not isinstance(ef, dict):
                errors.append("expected_behavior.expected_findings must be a mapping")
            else:
                mc = ef.get("min_count")
                if mc is not None and not isinstance(mc, int):
                    errors.append(
                        "expected_behavior.expected_findings.min_count must be an integer"
                    )

    # --- evaluation ---
    evaluation = data.get("evaluation")
    if not evaluation:
        errors.append("Missing required field: evaluation")
    elif not isinstance(evaluation, dict):
        errors.append("evaluation must be a mapping")
    else:
        pt = evaluation.get("pass_threshold")
        if pt is None:
            errors.append("Missing required field: evaluation.pass_threshold")
        elif not isinstance(pt, int):
            errors.append("evaluation.pass_threshold must be an integer")
        elif not (0 <= pt <= 100):
            errors.append(f"evaluation.pass_threshold must be 0-100, got {pt}")

        kd = evaluation.get("key_dimensions")
        if kd is None:
            errors.append("Missing required field: evaluation.key_dimensions")
        elif not isinstance(kd, list):
            errors.append("evaluation.key_dimensions must be a list")
        elif len(kd) == 0:
            errors.append("evaluation.key_dimensions must not be empty")
        else:
            for i, dim in enumerate(kd):
                if not isinstance(dim, dict):
                    errors.append(f"evaluation.key_dimensions[{i}] must be a mapping")
                else:
                    if not dim.get("name"):
                        errors.append(
                            f"evaluation.key_dimensions[{i}].name is required"
                        )
                    if not dim.get("description"):
                        errors.append(
                            f"evaluation.key_dimensions[{i}].description is required"
                        )

        rs = evaluation.get("regression_signals")
        if rs is None:
            errors.append("Missing required field: evaluation.regression_signals")
        elif not isinstance(rs, list):
            errors.append("evaluation.regression_signals must be a list")
        elif len(rs) == 0:
            errors.append("evaluation.regression_signals must not be empty")

    # --- links (optional) ---
    links = data.get("links")
    if links is not None:
        if not isinstance(links, dict):
            errors.append("links must be a mapping")
        else:
            rs_list = links.get("related_scenarios")
            if rs_list is not None:
                if not isinstance(rs_list, list):
                    errors.append("links.related_scenarios must be a list")

    return errors


def check_input_paths(filepath: Path) -> list[str]:
    """Check that input.contract paths exist on disk.

    Returns a list of warning strings (non-fatal).
    """
    warnings: list[str] = []
    try:
        with open(filepath) as f:
            data = yaml.safe_load(f)
    except Exception:
        return []

    if not isinstance(data, dict):
        return []

    input_data = data.get("input", {})
    if not isinstance(input_data, dict):
        return []

    contract_path = input_data.get("contract", "")
    if contract_path:
        full_path = PROJECT_ROOT / contract_path
        if not full_path.exists():
            warnings.append(f"input.contract path not found: {contract_path}")

    return warnings


def check_workflow_contract_mapping(filepath: Path) -> list[str]:
    """Check that workflow values resolve to real evaluation contract files.

    Returns a list of warning strings (non-fatal).
    """
    warnings: list[str] = []
    try:
        with open(filepath) as f:
            data = yaml.safe_load(f)
    except Exception:
        return []

    if not isinstance(data, dict):
        return []

    workflow = data.get("workflow", "")
    if not workflow:
        return []

    # Try to resolve via the contract loader mapping
    try:
        from alphaswarm_sol.testing.evaluation.contract_loader import (
            resolve_contract_id,
            _CONTRACTS_DIR,
        )
        resolved = resolve_contract_id(workflow)
        contract_file = _CONTRACTS_DIR / f"{resolved}.yaml"
        if not contract_file.exists():
            warnings.append(
                f"workflow '{workflow}' resolves to '{resolved}' "
                f"but no contract file at {contract_file.relative_to(PROJECT_ROOT)}"
            )
    except ImportError:
        pass  # contract_loader not available

    return warnings


def discover_scenarios(base_dir: Path) -> list[Path]:
    """Find all scenario YAML files recursively."""
    scenarios = []
    for path in sorted(base_dir.rglob("*.yaml")):
        # Skip the schema file and any dotfiles
        if path.name.startswith("_") or path.name.startswith("."):
            continue
        scenarios.append(path)
    return scenarios


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Use Case Scenario YAML files"
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_SCENARIOS_DIR,
        help="Directory to scan for scenario YAML files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show details for passing files too",
    )
    parser.add_argument(
        "--check-paths",
        action="store_true",
        help="Verify input.contract file paths exist on disk",
    )
    parser.add_argument(
        "--check-contracts",
        action="store_true",
        help="Verify workflow values resolve to real evaluation contract files",
    )
    args = parser.parse_args()

    scenarios_dir = args.path
    if not scenarios_dir.exists():
        print(f"ERROR: Directory not found: {scenarios_dir}")
        return 1

    files = discover_scenarios(scenarios_dir)
    if not files:
        print(f"WARNING: No scenario YAML files found in {scenarios_dir}")
        return 0

    total_errors = 0
    total_warnings = 0
    passed = 0
    failed = 0

    print(f"Validating {len(files)} scenario files in {scenarios_dir}\n")

    for filepath in files:
        rel_path = filepath.relative_to(PROJECT_ROOT)
        errors = validate_scenario(filepath, verbose=args.verbose)

        # Optional path and contract checks (warnings, not errors)
        warnings: list[str] = []
        if args.check_paths:
            warnings.extend(check_input_paths(filepath))
        if args.check_contracts:
            warnings.extend(check_workflow_contract_mapping(filepath))

        if errors:
            failed += 1
            total_errors += len(errors)
            print(f"FAIL  {rel_path}")
            for err in errors:
                print(f"      - {err}")
        else:
            passed += 1
            if args.verbose:
                print(f"OK    {rel_path}")

        if warnings:
            total_warnings += len(warnings)
            for w in warnings:
                print(f"WARN  {rel_path}: {w}")

    # Summary
    print(f"\n{'='*60}")
    summary = f"Results: {passed} passed, {failed} failed, {total_errors} total errors"
    if total_warnings:
        summary += f", {total_warnings} warnings"
    print(summary)
    print(f"{'='*60}")

    if failed > 0:
        print("\nValidation FAILED")
        return 1
    else:
        print("\nAll scenarios valid")
        return 0


if __name__ == "__main__":
    sys.exit(main())
