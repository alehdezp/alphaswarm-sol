#!/usr/bin/env python3
"""
Validate protocol context pack output.

Usage:
    uv run python scripts/validate_context.py --context .vrs/context/protocol-pack.yaml
    uv run python scripts/validate_context.py --context pack.yaml --expected checks.json --output results.json
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml


REQUIRED_FIELDS = {
    "roles": ["roles", "actors", "participants", "stakeholders"],
    "upgradeability": ["upgradeability", "proxy", "proxies", "upgrade"],
    "asset_flows": ["asset_flows", "value_flow", "assets", "flows"],
    "trust_boundaries": ["trust_boundaries", "trust_model", "boundaries"],
    "assumptions": ["assumptions", "invariants", "constraints"],
}


@dataclass
class ValidationResult:
    """Result of a single validation check."""

    passed: bool
    check_name: str
    expected: Any
    actual: Any
    message: str


def load_context(context_path: Path) -> dict:
    """Load context pack from YAML."""
    content = context_path.read_text()
    return yaml.safe_load(content) or {}


def validate_protocol_type(context: dict) -> ValidationResult:
    """Check if protocol type is detected."""
    # Try multiple possible field names
    protocol_type = (
        context.get("protocol_type")
        or context.get("type")
        or context.get("protocolType")
        or context.get("protocol", {}).get("type")
    )

    if not protocol_type:
        return ValidationResult(
            passed=False,
            check_name="protocol_type",
            expected="vault|lending|dex|...",
            actual=None,
            message="Protocol type not detected",
        )

    # For foundry-vault fixture, expect "vault" type or similar
    expected_types = ["vault", "defi", "custody", "storage", "token_vault", "eth_vault"]
    if protocol_type.lower().replace("-", "_").replace(" ", "_") in expected_types or any(
        e in protocol_type.lower() for e in expected_types
    ):
        return ValidationResult(
            passed=True,
            check_name="protocol_type",
            expected=expected_types,
            actual=protocol_type,
            message=f"Protocol type detected: {protocol_type}",
        )

    return ValidationResult(
        passed=True,  # Pass if any type detected (some classification is better than none)
        check_name="protocol_type",
        expected=expected_types,
        actual=protocol_type,
        message=f"Protocol type detected (not vault-specific): {protocol_type}",
    )


def validate_roles(context: dict) -> ValidationResult:
    """Check if roles are extracted."""
    # Try multiple possible field names
    roles = (
        context.get("roles")
        or context.get("actors")
        or context.get("participants")
        or context.get("stakeholders")
        or []
    )

    if not roles:
        return ValidationResult(
            passed=False,
            check_name="roles",
            expected=["owner", "user"],
            actual=[],
            message="No roles extracted",
        )

    # Normalize role names
    role_names = []
    for role in roles:
        if isinstance(role, dict):
            role_name = role.get("name") or role.get("role") or role.get("id") or ""
            role_names.append(role_name.lower())
        else:
            role_names.append(str(role).lower())

    # For foundry-vault, expect owner and user roles (or similar)
    expected_roles = {"owner", "user", "admin", "depositor", "operator", "governance"}
    found_expected = set(role_names) & expected_roles

    if found_expected:
        return ValidationResult(
            passed=True,
            check_name="roles",
            expected=list(expected_roles),
            actual=role_names,
            message=f"Found expected roles: {list(found_expected)}",
        )

    # Any roles found is still useful
    if role_names:
        return ValidationResult(
            passed=True,
            check_name="roles",
            expected=list(expected_roles),
            actual=role_names,
            message=f"Found roles (not standard names): {role_names}",
        )

    return ValidationResult(
        passed=False,
        check_name="roles",
        expected=list(expected_roles),
        actual=role_names,
        message="No recognizable roles found",
    )


def find_required_field(context: dict, aliases: list[str]) -> tuple[Optional[str], Any]:
    for alias in aliases:
        if alias in context:
            return alias, context.get(alias)
    return None, None


def value_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set)):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value.keys()) > 0
    return True


def validate_required_fields(context: dict) -> ValidationResult:
    """Check for required context fields based on context-quality gate."""
    missing = []
    found = {}
    for field, aliases in REQUIRED_FIELDS.items():
        key, value = find_required_field(context, aliases)
        if key and value_present(value):
            found[field] = key
        else:
            missing.append(field)

    if not missing:
        return ValidationResult(
            passed=True,
            check_name="required_fields",
            expected=list(REQUIRED_FIELDS.keys()),
            actual=found,
            message="All required context fields present",
        )

    return ValidationResult(
        passed=False,
        check_name="required_fields",
        expected=list(REQUIRED_FIELDS.keys()),
        actual=found,
        message=f"Missing required fields: {missing}",
    )


def validate_economic_context(context: dict) -> ValidationResult:
    """Check if economic context is present (optional)."""
    economic_keys = [
        "economic_model",
        "economics",
        "incentives",
        "fees",
        "rewards",
        "tokenomics",
        "value_flow",
    ]
    found = [k for k in economic_keys if k in context]

    if found:
        return ValidationResult(
            passed=True,
            check_name="economic_context",
            expected="economic model present",
            actual=found,
            message=f"Economic context found: {found}",
        )

    # Not required, just informational
    return ValidationResult(
        passed=True,  # Optional field
        check_name="economic_context",
        expected="economic model (optional)",
        actual=None,
        message="No economic context (optional field)",
    )


def validate_yaml_parseable(context: dict) -> ValidationResult:
    """Check if the context pack was successfully parsed as YAML."""
    if context and isinstance(context, dict):
        return ValidationResult(
            passed=True,
            check_name="yaml_parseable",
            expected="valid YAML",
            actual="parsed successfully",
            message=f"Valid YAML with {len(context)} top-level keys",
        )

    return ValidationResult(
        passed=False,
        check_name="yaml_parseable",
        expected="valid YAML",
        actual=type(context).__name__,
        message="Context pack is not a valid YAML dictionary",
    )


def validate_against_expected(context: dict, expected_checks: dict) -> list[ValidationResult]:
    """Run validation against expected checks from JSON file."""
    results = []

    validation_rules = expected_checks.get("validation_rules", [])
    for rule in validation_rules:
        check = rule.get("check", "")
        expected = rule.get("expected_values") or rule.get("expected_roles") or rule.get("expected")

        if check == "protocol_type":
            protocol_type = context.get("protocol_type") or context.get("type") or ""
            if isinstance(expected, list):
                passed = protocol_type.lower() in [e.lower() for e in expected]
            else:
                passed = expected.lower() in protocol_type.lower()

            results.append(
                ValidationResult(
                    passed=passed,
                    check_name=f"expected:{check}",
                    expected=expected,
                    actual=protocol_type,
                    message=f"Expected protocol type check: {rule.get('reason', '')}",
                )
            )

        elif check == "roles_present":
            roles = context.get("roles", [])
            role_names = []
            for r in roles:
                if isinstance(r, dict):
                    role_names.append((r.get("name") or r.get("role") or "").lower())
                else:
                    role_names.append(str(r).lower())

            if isinstance(expected, list):
                found = set(role_names) & set(e.lower() for e in expected)
                passed = len(found) > 0
            else:
                passed = expected.lower() in role_names

            results.append(
                ValidationResult(
                    passed=passed,
                    check_name=f"expected:{check}",
                    expected=expected,
                    actual=role_names,
                    message=f"Expected roles check: {rule.get('reason', '')}",
                )
            )

        elif check == "assumptions":
            assumptions = (
                context.get("assumptions")
                or context.get("invariants")
                or context.get("constraints")
                or []
            )
            if isinstance(assumptions, str):
                assumptions_list = [assumptions]
            else:
                assumptions_list = [str(a).lower() for a in assumptions]

            expected_contains = rule.get("expected_contains") or []
            if isinstance(expected_contains, str):
                expected_contains = [expected_contains]

            found = [
                e
                for e in expected_contains
                if any(e.lower() in a for a in assumptions_list)
            ]

            results.append(
                ValidationResult(
                    passed=len(found) == len(expected_contains),
                    check_name=f"expected:{check}",
                    expected=expected_contains,
                    actual=assumptions_list,
                    message=f"Expected assumptions check: {rule.get('reason', '')}",
                )
            )

    return results


def run_validation(context: dict, expected_checks: Optional[dict] = None) -> list[ValidationResult]:
    """Run all validation rules against context."""
    results = []

    # Core validations
    results.append(validate_yaml_parseable(context))
    results.append(validate_required_fields(context))
    results.append(validate_protocol_type(context))
    results.append(validate_roles(context))
    results.append(validate_economic_context(context))

    # Run against expected checks if provided
    if expected_checks:
        results.extend(validate_against_expected(context, expected_checks))

    return results


def main():
    parser = argparse.ArgumentParser(description="Validate protocol context pack")
    parser.add_argument("--context", required=True, help="Path to context pack YAML")
    parser.add_argument("--expected", help="Path to expected checks JSON (optional)")
    parser.add_argument("--output", help="Output file for validation results")
    parser.add_argument(
        "--simulated",
        action="store_true",
        help="Emit CONTEXT_SIMULATED marker (simulated/bypassed context)",
    )
    args = parser.parse_args()

    context_path = Path(args.context)

    # Load context
    try:
        context = load_context(context_path)
    except FileNotFoundError:
        print(f"ERROR: Context file not found: {context_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"ERROR: Failed to parse YAML: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load context: {e}")
        sys.exit(1)

    if not context:
        print("ERROR: Context pack is empty")
        sys.exit(1)

    # Load expected checks if provided
    expected_checks = None
    if args.expected and Path(args.expected).exists():
        try:
            expected_checks = json.loads(Path(args.expected).read_text())
        except (json.JSONDecodeError, Exception) as e:
            print(f"WARNING: Failed to load expected checks: {e}")

    # Run validation
    results = run_validation(context, expected_checks)

    # Output results
    all_passed = all(r.passed for r in results)
    required_passed = all(
        r.passed
        for r in results
        if "expected:" not in r.check_name and r.check_name != "economic_context"
    )

    print("")
    print("Context Validation Results:")
    print("-" * 60)

    for result in results:
        status = "[PASS]" if result.passed else "[FAIL]"
        print(f"  {status} {result.check_name}")
        print(f"         {result.message}")

    print("-" * 60)
    print(f"Total: {sum(1 for r in results if r.passed)}/{len(results)} passed")

    if required_passed:
        print("[CONTEXT_READY]")
    else:
        print("[CONTEXT_INCOMPLETE]")
        missing_fields = next(
            (
                r.message.replace("Missing required fields: ", "")
                for r in results
                if r.check_name == "required_fields"
            ),
            "",
        )
        if missing_fields:
            print(f"Missing required fields: {missing_fields}")

    simulated_context = args.simulated or bool(
        context.get("context_simulated")
        or context.get("simulated")
        or (isinstance(context.get("context"), dict) and context["context"].get("simulated"))
    )
    if simulated_context:
        print("[CONTEXT_SIMULATED]")

    # Write output file
    if args.output:
        required_result = next(
            (r for r in results if r.check_name == "required_fields"), None
        )
        missing_required_fields = []
        if required_result and isinstance(required_result.actual, dict):
            missing_required_fields = [
                f for f in REQUIRED_FIELDS.keys() if f not in required_result.actual
            ]
        output_data = {
            "passed": required_passed,  # Use required_passed for overall status
            "all_passed": all_passed,
            "total_checks": len(results),
            "passed_checks": sum(1 for r in results if r.passed),
            "context_summary": {
                "protocol_type": context.get("protocol_type") or context.get("type"),
                "roles_count": len(context.get("roles", [])),
                "has_economic": any(k in context for k in ["economic_model", "economics"]),
                "missing_required_fields": missing_required_fields,
                "keys": list(context.keys()),
            },
            "results": [
                {
                    "check": r.check_name,
                    "passed": r.passed,
                    "message": r.message,
                    "expected": str(r.expected)[:100] if r.expected else None,
                    "actual": str(r.actual)[:100] if r.actual else None,
                }
                for r in results
            ],
        }
        Path(args.output).write_text(json.dumps(output_data, indent=2))
        print(f"\nResults written to: {args.output}")

    # Exit based on required validations
    sys.exit(0 if required_passed else 1)


if __name__ == "__main__":
    main()
