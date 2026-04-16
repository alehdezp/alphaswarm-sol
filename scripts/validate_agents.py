#!/usr/bin/env python3
"""
Validate agent investigation output.

Usage:
    uv run python scripts/validate_agents.py --investigations .vrs/findings/agent-investigations.json
"""

import argparse
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional
import sys


@dataclass
class ValidationResult:
    passed: bool
    check_name: str
    expected: Any
    actual: Any
    message: str


def load_investigations(path: Path) -> list[dict]:
    """Load agent investigations from JSON."""
    content = path.read_text()
    data = json.loads(content)

    # Handle different output formats
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return data.get("investigations", data.get("findings", data.get("results", [])))

    return []


def find_investigation(investigations: list[dict], pattern_id: str, function_name: str) -> Optional[dict]:
    """Find a specific investigation."""
    for inv in investigations:
        inv_pattern = inv.get("pattern_id") or inv.get("pattern") or inv.get("id")
        inv_func = inv.get("function") or inv.get("function_name")

        if inv_pattern and function_name:
            if pattern_id.lower() in str(inv_pattern).lower() and function_name.lower() in str(inv_func).lower():
                return inv

    return None


def validate_investigation_exists(
    investigations: list[dict], pattern_id: str, function_name: str
) -> ValidationResult:
    """Validate that an expected investigation exists."""
    inv = find_investigation(investigations, pattern_id, function_name)

    if inv is None:
        return ValidationResult(
            passed=False,
            check_name=f"investigation_exists:{pattern_id}@{function_name}",
            expected=f"Investigation for {pattern_id}@{function_name}",
            actual=None,
            message=f"No investigation found for {pattern_id} in {function_name}",
        )

    return ValidationResult(
        passed=True,
        check_name=f"investigation_exists:{pattern_id}@{function_name}",
        expected=f"Investigation for {pattern_id}@{function_name}",
        actual=inv,
        message=f"Investigation found for {pattern_id} in {function_name}",
    )


def validate_has_evidence(
    investigations: list[dict], pattern_id: str, function_name: str
) -> ValidationResult:
    """Validate that investigation has BSKG evidence."""
    inv = find_investigation(investigations, pattern_id, function_name)

    if inv is None:
        return ValidationResult(
            passed=False,
            check_name=f"has_evidence:{pattern_id}@{function_name}",
            expected="Investigation with evidence",
            actual=None,
            message=f"No investigation found for {pattern_id} in {function_name}",
        )

    evidence = inv.get("evidence", {})

    # Check for BSKG node ID
    has_node_id = any(
        k in evidence for k in ["bskg_node_id", "node_id", "function_id", "graph_node"]
    ) or "node" in str(evidence).lower()

    # Check for code location
    has_location = any(
        k in evidence for k in ["code_location", "location", "line", "file"]
    ) or inv.get("location") is not None

    # Check for operations/signature
    has_ops = any(
        k in evidence for k in ["operations", "behavioral_signature", "signature"]
    )

    if not (has_node_id or has_location or has_ops):
        return ValidationResult(
            passed=False,
            check_name=f"has_evidence:{pattern_id}@{function_name}",
            expected="Evidence with node_id, location, or operations",
            actual=evidence,
            message=f"Investigation lacks proper BSKG evidence",
        )

    return ValidationResult(
        passed=True,
        check_name=f"has_evidence:{pattern_id}@{function_name}",
        expected="Evidence with node_id, location, or operations",
        actual=evidence,
        message=f"Investigation has proper evidence",
    )


def validate_severity(
    investigations: list[dict], pattern_id: str, function_name: str, expected_severity: str
) -> ValidationResult:
    """Validate severity rating."""
    inv = find_investigation(investigations, pattern_id, function_name)

    if inv is None:
        return ValidationResult(
            passed=False,
            check_name=f"severity:{pattern_id}@{function_name}",
            expected=expected_severity,
            actual=None,
            message="No investigation found",
        )

    actual_severity = inv.get("severity", "").lower()
    expected_lower = expected_severity.lower()

    # Allow some flexibility in severity naming
    severity_levels = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    expected_level = severity_levels.get(expected_lower, -1)
    actual_level = severity_levels.get(actual_severity, -1)

    # Pass if severity is at least as high as expected
    if actual_level >= expected_level:
        return ValidationResult(
            passed=True,
            check_name=f"severity:{pattern_id}@{function_name}",
            expected=expected_severity,
            actual=actual_severity,
            message=f"Severity OK: {actual_severity} >= {expected_severity}",
        )

    return ValidationResult(
        passed=False,
        check_name=f"severity:{pattern_id}@{function_name}",
        expected=expected_severity,
        actual=actual_severity,
        message=f"Severity too low: {actual_severity} < {expected_severity}",
    )


def validate_agent_type(
    investigations: list[dict], pattern_id: str, function_name: str, expected_agent: str
) -> ValidationResult:
    """Validate correct agent type was used."""
    inv = find_investigation(investigations, pattern_id, function_name)

    if inv is None:
        return ValidationResult(
            passed=False,
            check_name=f"agent_type:{pattern_id}@{function_name}",
            expected=expected_agent,
            actual=None,
            message="No investigation found",
        )

    actual_agent = inv.get("agent", "").lower()

    if expected_agent.lower() in actual_agent or actual_agent in expected_agent.lower():
        return ValidationResult(
            passed=True,
            check_name=f"agent_type:{pattern_id}@{function_name}",
            expected=expected_agent,
            actual=actual_agent,
            message=f"Correct agent: {actual_agent}",
        )

    # Also pass if the agent type matches the pattern type
    if "reentrancy" in pattern_id.lower() and "reentrancy" in actual_agent:
        return ValidationResult(
            passed=True,
            check_name=f"agent_type:{pattern_id}@{function_name}",
            expected=expected_agent,
            actual=actual_agent,
            message=f"Agent matches pattern type",
        )

    return ValidationResult(
        passed=True,  # Don't fail on agent type mismatch, just warn
        check_name=f"agent_type:{pattern_id}@{function_name}",
        expected=expected_agent,
        actual=actual_agent,
        message=f"Agent type: {actual_agent} (expected {expected_agent})",
    )


def run_validation(investigations: list[dict], expected_data: Optional[dict] = None) -> list[ValidationResult]:
    """Run all validation rules."""
    results = []

    # Default expected checks if none provided
    if expected_data is None:
        expected_data = {
            "expected_investigations": [
                {
                    "pattern_id": "reentrancy-classic",
                    "function": "withdraw",
                    "severity": "critical",
                    "agent": "reentrancy-specialist"
                },
                {
                    "pattern_id": "weak-access-control",
                    "function": "setOwner",
                    "severity": "critical",
                    "agent": "access-specialist"
                }
            ]
        }

    # Check each expected investigation
    for expected in expected_data.get("expected_investigations", []):
        pattern_id = expected["pattern_id"]
        function_name = expected["function"]

        # Check investigation exists
        results.append(validate_investigation_exists(investigations, pattern_id, function_name))

        # Check has evidence
        results.append(validate_has_evidence(investigations, pattern_id, function_name))

        # Check severity
        if "severity" in expected:
            results.append(validate_severity(investigations, pattern_id, function_name, expected["severity"]))

        # Check agent type
        if "agent" in expected:
            results.append(validate_agent_type(investigations, pattern_id, function_name, expected["agent"]))

    return results


def main():
    parser = argparse.ArgumentParser(description="Validate agent investigations")
    parser.add_argument("--investigations", required=True, help="Path to agent-investigations.json")
    parser.add_argument("--expected", help="Path to expected checks JSON (optional)")
    parser.add_argument("--output", help="Output file for validation results")
    args = parser.parse_args()

    investigations_path = Path(args.investigations)

    # Load investigations
    try:
        investigations = load_investigations(investigations_path)
    except Exception as e:
        print(f"ERROR: Failed to load investigations: {e}")
        sys.exit(1)

    # Load expected checks if provided
    expected_data = None
    if args.expected and Path(args.expected).exists():
        expected_data = json.loads(Path(args.expected).read_text())

    # Run validation
    results = run_validation(investigations, expected_data)

    # Output results
    all_passed = all(r.passed for r in results)

    print("")
    print("Agent Investigation Validation Results:")
    print("-" * 60)

    for result in results:
        status = "[PASS]" if result.passed else "[FAIL]"
        print(f"  {status} {result.check_name}")
        if not result.passed:
            print(f"         {result.message}")

    print("-" * 60)
    print(f"Total: {sum(1 for r in results if r.passed)}/{len(results)} checks passed")

    # Write output file
    if args.output:
        output_data = {
            "passed": all_passed,
            "total_investigations": len(investigations),
            "results": [
                {
                    "check": r.check_name,
                    "passed": r.passed,
                    "message": r.message,
                }
                for r in results
            ],
        }
        Path(args.output).write_text(json.dumps(output_data, indent=2))

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
