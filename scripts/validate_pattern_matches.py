#!/usr/bin/env python3
"""
Validate pattern matching output against expected ground truth.

This script validates that pattern matching produces correct results:
- Expected patterns are matched (true positives)
- Safe functions are NOT matched (no false positives)
- Calculates precision, recall, and F1 metrics

Usage:
    uv run python scripts/validate_pattern_matches.py \\
        --matches .vrs/findings/pattern-matches.json \\
        --expected expected/pattern-matches.json \\
        --output validation-results.json

Exit codes:
    0 - All validations passed
    1 - Validation failed (missing expected matches or false positives)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class ValidationResult:
    """Single validation check result."""

    passed: bool
    check_name: str
    expected: Any
    actual: Any
    message: str


def load_matches(matches_path: Path) -> list[dict]:
    """Load pattern matches from JSON.

    Handles multiple output formats:
    - Direct list of matches
    - Object with 'matches', 'findings', or 'results' key

    Args:
        matches_path: Path to pattern matches JSON file

    Returns:
        List of match dictionaries
    """
    content = matches_path.read_text()
    data = json.loads(content)

    # Handle different output formats
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        # Try common keys
        for key in ["matches", "findings", "results", "patterns"]:
            if key in data:
                return data[key]
        # If no known key, try to extract from nested structure
        if "data" in data and isinstance(data["data"], list):
            return data["data"]
        # Return empty if no matches found
        return []

    return []


def normalize_match(match: dict) -> dict:
    """Normalize match dictionary to standard format.

    Args:
        match: Raw match dictionary

    Returns:
        Normalized match with standard keys
    """
    # Extract pattern ID
    pattern_id = (
        match.get("pattern_id")
        or match.get("pattern")
        or match.get("id")
        or match.get("rule_id")
        or ""
    )

    # Extract function name
    function_name = (
        match.get("function")
        or match.get("function_name")
        or match.get("location", {}).get("function")
        or match.get("target", {}).get("function")
        or ""
    )

    # Extract tier
    tier = match.get("tier") or match.get("confidence_tier") or "unknown"

    # Extract confidence
    confidence = match.get("confidence") or match.get("score") or 0.0

    return {
        "pattern_id": pattern_id.lower() if pattern_id else "",
        "function": function_name.lower() if function_name else "",
        "tier": str(tier).upper(),
        "confidence": float(confidence),
        "raw": match,
    }


def find_match(
    matches: list[dict], pattern_id: str, function_name: str
) -> Optional[dict]:
    """Find a specific pattern match by pattern ID and function name.

    Args:
        matches: List of normalized matches
        pattern_id: Pattern ID to find (e.g., 'reentrancy-classic')
        function_name: Function name to find (e.g., 'withdraw')

    Returns:
        Matching dictionary or None if not found
    """
    pattern_lower = pattern_id.lower()
    func_lower = function_name.lower()

    for match in matches:
        normalized = normalize_match(match)
        match_pattern = normalized["pattern_id"]
        match_func = normalized["function"]

        # Check for pattern match (flexible - allows partial matching for pattern IDs)
        pattern_matches = (
            pattern_lower in match_pattern or match_pattern in pattern_lower
        )

        # Check for function match - must be exact or exact substring match
        # Avoid 'withdraw' matching 'safeWithdraw' (they are different functions)
        func_matches = (
            func_lower == match_func  # Exact match
            or func_lower == match_func.split(".")[-1]  # Match after contract prefix
            or match_func == func_lower.split(".")[-1]  # Match after contract prefix
        )

        if pattern_matches and func_matches:
            return normalized

    return None


def validate_expected_match(
    matches: list[dict], expected: dict
) -> ValidationResult:
    """Validate that an expected pattern was matched.

    Args:
        matches: List of actual matches
        expected: Expected match specification

    Returns:
        ValidationResult indicating pass/fail
    """
    pattern_id = expected["pattern_id"]
    function_name = expected["function"]

    match = find_match(matches, pattern_id, function_name)

    if match is None:
        return ValidationResult(
            passed=False,
            check_name=f"expected_match:{pattern_id}@{function_name}",
            expected=expected,
            actual=None,
            message=f"Expected pattern '{pattern_id}' not found for function '{function_name}'",
        )

    # Validate tier if specified
    expected_tier = expected.get("tier")
    if expected_tier:
        actual_tier = match.get("tier", "unknown")
        if actual_tier != "UNKNOWN" and expected_tier.upper() != actual_tier:
            return ValidationResult(
                passed=False,
                check_name=f"expected_match:{pattern_id}@{function_name}",
                expected=expected,
                actual=match,
                message=f"Tier mismatch: expected '{expected_tier}', got '{actual_tier}'",
            )

    # Validate confidence if specified
    expected_conf = expected.get("confidence") or expected.get("confidence_min")
    if expected_conf:
        actual_conf = match.get("confidence", 0)
        # Allow 20% tolerance below expected
        min_acceptable = float(expected_conf) * 0.8
        if actual_conf < min_acceptable:
            return ValidationResult(
                passed=False,
                check_name=f"expected_match:{pattern_id}@{function_name}",
                expected=expected,
                actual=match,
                message=f"Confidence too low: expected >= {min_acceptable:.2f}, got {actual_conf:.2f}",
            )

    return ValidationResult(
        passed=True,
        check_name=f"expected_match:{pattern_id}@{function_name}",
        expected=expected,
        actual=match,
        message=f"Pattern '{pattern_id}' correctly matched for '{function_name}'",
    )


def validate_expected_no_match(
    matches: list[dict], expected: dict
) -> ValidationResult:
    """Validate that a pattern was NOT matched (false positive check).

    Args:
        matches: List of actual matches
        expected: Expected no-match specification

    Returns:
        ValidationResult indicating pass/fail
    """
    pattern_id = expected["pattern_id"]
    function_name = expected["function"]
    reason = expected.get("reason", "should not be flagged")

    match = find_match(matches, pattern_id, function_name)

    if match is not None:
        return ValidationResult(
            passed=False,
            check_name=f"expected_no_match:{pattern_id}@{function_name}",
            expected=f"No match for {pattern_id}@{function_name}",
            actual=match,
            message=f"FALSE POSITIVE: Pattern '{pattern_id}' incorrectly matched for '{function_name}'. Reason: {reason}",
        )

    return ValidationResult(
        passed=True,
        check_name=f"expected_no_match:{pattern_id}@{function_name}",
        expected=f"No match for {pattern_id}@{function_name}",
        actual=None,
        message=f"Correctly did NOT match '{pattern_id}' for '{function_name}'",
    )


def validate_match_count(matches: list[dict], min_count: int = 1) -> ValidationResult:
    """Validate minimum number of matches found.

    Args:
        matches: List of actual matches
        min_count: Minimum required matches

    Returns:
        ValidationResult indicating pass/fail
    """
    count = len(matches)

    if count < min_count:
        return ValidationResult(
            passed=False,
            check_name="match_count",
            expected=f">= {min_count}",
            actual=count,
            message=f"Too few matches: expected >= {min_count}, got {count}",
        )

    return ValidationResult(
        passed=True,
        check_name="match_count",
        expected=f">= {min_count}",
        actual=count,
        message=f"Match count OK: {count} matches found",
    )


def run_validation(matches: list[dict], expected_data: dict) -> list[ValidationResult]:
    """Run all validation rules against matches.

    Args:
        matches: List of actual matches
        expected_data: Expected matches specification

    Returns:
        List of ValidationResult objects
    """
    results = []

    # Basic count check
    results.append(validate_match_count(matches, min_count=1))

    # Check expected matches (true positives)
    for expected in expected_data.get("expected_matches", []):
        results.append(validate_expected_match(matches, expected))

    # Check expected NO matches (false positive prevention)
    # Handle both 'expected_no_match' and 'expected_no_matches' keys
    no_match_list = expected_data.get("expected_no_match", []) or expected_data.get(
        "expected_no_matches", []
    )
    for expected in no_match_list:
        results.append(validate_expected_no_match(matches, expected))

    return results


def calculate_metrics(results: list[ValidationResult], expected_data: dict) -> dict:
    """Calculate precision, recall, and F1 metrics.

    Args:
        results: List of validation results
        expected_data: Expected matches specification

    Returns:
        Dictionary with TP, FN, FP, TN, precision, recall, F1
    """
    # True positives: expected matches that were found
    tp = sum(
        1
        for r in results
        if r.check_name.startswith("expected_match:") and r.passed
    )

    # False negatives: expected matches that were NOT found
    fn = sum(
        1
        for r in results
        if r.check_name.startswith("expected_match:") and not r.passed
    )

    # False positives: expected NO matches that WERE found (incorrectly)
    fp = sum(
        1
        for r in results
        if r.check_name.startswith("expected_no_match:") and not r.passed
    )

    # True negatives: expected NO matches that were NOT found (correctly)
    tn = sum(
        1
        for r in results
        if r.check_name.startswith("expected_no_match:") and r.passed
    )

    # Calculate metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "true_positives": tp,
        "false_negatives": fn,
        "false_positives": fp,
        "true_negatives": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate pattern matches against ground truth",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--matches",
        required=True,
        type=Path,
        help="Path to pattern-matches.json (actual results)",
    )
    parser.add_argument(
        "--expected",
        required=True,
        type=Path,
        help="Path to expected matches JSON (ground truth)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for validation results JSON",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    args = parser.parse_args()

    matches_path = args.matches
    expected_path = args.expected

    # Load actual matches
    print("")
    print("Pattern Match Validation")
    print("-" * 60)

    try:
        print(f"Loading matches from: {matches_path}")
        matches = load_matches(matches_path)
        print(f"  Found {len(matches)} matches")
    except Exception as e:
        print(f"ERROR: Failed to load matches: {e}")
        sys.exit(1)

    # Load expected data
    if not expected_path.exists():
        print(f"WARNING: Expected file not found: {expected_path}")
        print(f"Found {len(matches)} pattern matches (no ground truth to compare)")
        sys.exit(0)

    try:
        print(f"Loading expected from: {expected_path}")
        expected_data = json.loads(expected_path.read_text())
        expected_count = len(expected_data.get("expected_matches", []))
        no_match_count = len(
            expected_data.get("expected_no_match", [])
            or expected_data.get("expected_no_matches", [])
        )
        print(f"  Expected matches: {expected_count}")
        print(f"  Expected no-matches: {no_match_count}")
    except Exception as e:
        print(f"ERROR: Failed to load expected data: {e}")
        sys.exit(1)

    # Run validation
    print("")
    print("Running validation...")
    results = run_validation(matches, expected_data)
    metrics = calculate_metrics(results, expected_data)

    # Output results
    all_passed = all(r.passed for r in results)

    print("")
    print("Validation Results:")
    print("-" * 60)

    for result in results:
        status = "[PASS]" if result.passed else "[FAIL]"
        print(f"  {status} {result.check_name}")
        if args.verbose or not result.passed:
            print(f"         {result.message}")

    print("-" * 60)
    passed_count = sum(1 for r in results if r.passed)
    print(f"Total: {passed_count}/{len(results)} checks passed")

    print("")
    print("Metrics:")
    print(f"  Precision: {metrics['precision']:.2%}")
    print(f"  Recall:    {metrics['recall']:.2%}")
    print(f"  F1 Score:  {metrics['f1_score']:.2%}")
    print(
        f"  TP: {metrics['true_positives']}, "
        f"FN: {metrics['false_negatives']}, "
        f"FP: {metrics['false_positives']}, "
        f"TN: {metrics['true_negatives']}"
    )

    # Write output file
    if args.output:
        output_data = {
            "passed": all_passed,
            "total_matches": len(matches),
            "metrics": metrics,
            "results": [
                {
                    "check": r.check_name,
                    "passed": r.passed,
                    "message": r.message,
                }
                for r in results
            ],
        }
        args.output.write_text(json.dumps(output_data, indent=2))
        print(f"\nResults written to: {args.output}")

    # Final verdict
    print("")
    if all_passed:
        print("VALIDATION PASSED")
    else:
        print("VALIDATION FAILED")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
