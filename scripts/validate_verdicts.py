#!/usr/bin/env python3
"""
Validate multi-agent debate verdicts.

Usage:
    uv run python scripts/validate_verdicts.py --verdicts .vrs/findings/verdicts.json
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


def load_verdicts(path: Path) -> list[dict]:
    """Load verdicts from JSON."""
    content = path.read_text()
    data = json.loads(content)

    # Handle different output formats
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return data.get("verdicts", data.get("findings", data.get("results", [])))

    return []


def find_verdict(verdicts: list[dict], pattern_id: str, function_name: str) -> Optional[dict]:
    """Find a specific verdict."""
    for verdict in verdicts:
        v_pattern = verdict.get("pattern_id") or verdict.get("pattern") or verdict.get("id")
        v_func = verdict.get("function") or verdict.get("function_name")

        if v_pattern and function_name:
            if pattern_id.lower() in str(v_pattern).lower() and function_name.lower() in str(v_func).lower():
                return verdict

    return None


def validate_verdict_exists(
    verdicts: list[dict], pattern_id: str, function_name: str
) -> ValidationResult:
    """Validate that a verdict exists for the finding."""
    verdict = find_verdict(verdicts, pattern_id, function_name)

    if verdict is None:
        return ValidationResult(
            passed=False,
            check_name=f"verdict_exists:{pattern_id}@{function_name}",
            expected=f"Verdict for {pattern_id}@{function_name}",
            actual=None,
            message=f"No verdict found for {pattern_id} in {function_name}",
        )

    return ValidationResult(
        passed=True,
        check_name=f"verdict_exists:{pattern_id}@{function_name}",
        expected=f"Verdict for {pattern_id}@{function_name}",
        actual=verdict,
        message=f"Verdict found for {pattern_id} in {function_name}",
    )


def validate_verdict_outcome(
    verdicts: list[dict], pattern_id: str, function_name: str, expected_verdict: str
) -> ValidationResult:
    """Validate the verdict outcome (CONFIRMED, DISPUTED, REJECTED)."""
    verdict = find_verdict(verdicts, pattern_id, function_name)

    if verdict is None:
        return ValidationResult(
            passed=False,
            check_name=f"verdict_outcome:{pattern_id}@{function_name}",
            expected=expected_verdict,
            actual=None,
            message="No verdict found",
        )

    # Extract actual verdict from various possible structures
    actual_verdict = None
    verifier = verdict.get("verifier_verdict", verdict.get("verifier", verdict.get("verdict_details", {})))
    if isinstance(verifier, dict):
        actual_verdict = verifier.get("verdict", verifier.get("outcome", verifier.get("decision")))
    elif isinstance(verifier, str):
        actual_verdict = verifier

    # Also check top-level verdict field
    if actual_verdict is None:
        actual_verdict = verdict.get("verdict", verdict.get("outcome"))

    if actual_verdict is None:
        return ValidationResult(
            passed=False,
            check_name=f"verdict_outcome:{pattern_id}@{function_name}",
            expected=expected_verdict,
            actual=None,
            message="Verdict outcome not found in structure",
        )

    actual_verdict = str(actual_verdict).upper()
    expected_upper = expected_verdict.upper()

    if actual_verdict == expected_upper:
        return ValidationResult(
            passed=True,
            check_name=f"verdict_outcome:{pattern_id}@{function_name}",
            expected=expected_verdict,
            actual=actual_verdict,
            message=f"Verdict correct: {actual_verdict}",
        )

    return ValidationResult(
        passed=False,
        check_name=f"verdict_outcome:{pattern_id}@{function_name}",
        expected=expected_verdict,
        actual=actual_verdict,
        message=f"Verdict mismatch: expected {expected_verdict}, got {actual_verdict}",
    )


def validate_has_attacker_claim(
    verdicts: list[dict], pattern_id: str, function_name: str
) -> ValidationResult:
    """Validate that verdict has attacker claim."""
    verdict = find_verdict(verdicts, pattern_id, function_name)

    if verdict is None:
        return ValidationResult(
            passed=False,
            check_name=f"has_attacker:{pattern_id}@{function_name}",
            expected="Attacker claim present",
            actual=None,
            message="No verdict found",
        )

    attacker = verdict.get("attacker_claim", verdict.get("attacker", {}))
    has_exploit = "exploit" in str(attacker).lower() or "path" in str(attacker).lower()
    has_evidence = "evidence" in str(attacker).lower() or len(attacker) > 0

    if has_exploit or has_evidence:
        return ValidationResult(
            passed=True,
            check_name=f"has_attacker:{pattern_id}@{function_name}",
            expected="Attacker claim present",
            actual=attacker,
            message="Attacker claim present with exploit/evidence",
        )

    return ValidationResult(
        passed=False,
        check_name=f"has_attacker:{pattern_id}@{function_name}",
        expected="Attacker claim with exploit path",
        actual=attacker,
        message="Attacker claim missing or incomplete",
    )


def validate_has_defender_claim(
    verdicts: list[dict], pattern_id: str, function_name: str
) -> ValidationResult:
    """Validate that verdict has defender claim."""
    verdict = find_verdict(verdicts, pattern_id, function_name)

    if verdict is None:
        return ValidationResult(
            passed=False,
            check_name=f"has_defender:{pattern_id}@{function_name}",
            expected="Defender claim present",
            actual=None,
            message="No verdict found",
        )

    defender = verdict.get("defender_claim", verdict.get("defender", {}))

    # Defender claim can be empty if no guards found, but should exist
    if defender is not None and (isinstance(defender, dict) or isinstance(defender, str)):
        return ValidationResult(
            passed=True,
            check_name=f"has_defender:{pattern_id}@{function_name}",
            expected="Defender claim present",
            actual=defender,
            message="Defender claim present",
        )

    return ValidationResult(
        passed=False,
        check_name=f"has_defender:{pattern_id}@{function_name}",
        expected="Defender claim present",
        actual=defender,
        message="Defender claim missing",
    )


def validate_has_verifier_verdict(
    verdicts: list[dict], pattern_id: str, function_name: str
) -> ValidationResult:
    """Validate that verdict has verifier decision."""
    verdict = find_verdict(verdicts, pattern_id, function_name)

    if verdict is None:
        return ValidationResult(
            passed=False,
            check_name=f"has_verifier:{pattern_id}@{function_name}",
            expected="Verifier verdict present",
            actual=None,
            message="No verdict found",
        )

    verifier = verdict.get("verifier_verdict", verdict.get("verifier", verdict.get("final_verdict", {})))

    has_verdict = any(
        k in str(verifier).lower() for k in ["verdict", "confirmed", "disputed", "rejected", "decision"]
    )
    has_reasoning = "reason" in str(verifier).lower() or "evidence" in str(verifier).lower()

    if has_verdict:
        return ValidationResult(
            passed=True,
            check_name=f"has_verifier:{pattern_id}@{function_name}",
            expected="Verifier verdict present",
            actual=verifier,
            message="Verifier verdict present" + (" with reasoning" if has_reasoning else ""),
        )

    return ValidationResult(
        passed=False,
        check_name=f"has_verifier:{pattern_id}@{function_name}",
        expected="Verifier verdict with decision",
        actual=verifier,
        message="Verifier verdict missing or incomplete",
    )


def run_validation(verdicts: list[dict], expected_data: Optional[dict] = None) -> list[ValidationResult]:
    """Run all validation rules."""
    results = []

    # Default expected verdicts if none provided
    if expected_data is None:
        expected_data = {
            "expected_verdicts": [
                {
                    "pattern_id": "reentrancy-classic",
                    "function": "withdraw",
                    "expected_outcome": "CONFIRMED",
                    "expected_severity": "critical"
                },
                {
                    "pattern_id": "weak-access-control",
                    "function": "setOwner",
                    "expected_outcome": "CONFIRMED",
                    "expected_severity": "critical"
                }
            ]
        }

    # Check each expected verdict
    for expected in expected_data.get("expected_verdicts", []):
        pattern_id = expected["pattern_id"]
        function_name = expected["function"]

        # Check verdict exists
        results.append(validate_verdict_exists(verdicts, pattern_id, function_name))

        # Check verdict outcome
        if "expected_outcome" in expected:
            results.append(validate_verdict_outcome(verdicts, pattern_id, function_name, expected["expected_outcome"]))

        # Check debate phases present
        results.append(validate_has_attacker_claim(verdicts, pattern_id, function_name))
        results.append(validate_has_defender_claim(verdicts, pattern_id, function_name))
        results.append(validate_has_verifier_verdict(verdicts, pattern_id, function_name))

    return results


def main():
    parser = argparse.ArgumentParser(description="Validate debate verdicts")
    parser.add_argument("--verdicts", required=True, help="Path to verdicts.json")
    parser.add_argument("--expected", help="Path to expected checks JSON (optional)")
    parser.add_argument("--output", help="Output file for validation results")
    args = parser.parse_args()

    verdicts_path = Path(args.verdicts)

    # Load verdicts
    try:
        verdicts = load_verdicts(verdicts_path)
    except Exception as e:
        print(f"ERROR: Failed to load verdicts: {e}")
        sys.exit(1)

    # Load expected checks if provided
    expected_data = None
    if args.expected and Path(args.expected).exists():
        expected_data = json.loads(Path(args.expected).read_text())

    # Run validation
    results = run_validation(verdicts, expected_data)

    # Output results
    all_passed = all(r.passed for r in results)

    print("")
    print("Verdict Validation Results:")
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
            "total_verdicts": len(verdicts),
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
