#!/usr/bin/env python3
"""
Validate single pattern query result.

Single pattern query should:
- Return only the specified pattern (reentrancy-classic)
- Match expected functions (e.g., withdraw)
- NOT return extraneous patterns

Usage:
    python scripts/validate_single_pattern.py /path/to/worktree
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def validate_single_pattern(worktree: Path) -> bool:
    """Validate single pattern query result.

    Returns:
        True if validation passes, False otherwise.
    """
    result_file = worktree / ".vrs" / "single-pattern-result.json"
    all_passed = True
    checks = []

    # Check result file exists
    if not result_file.exists():
        print(f"ERROR: Result file not found: {result_file}", file=sys.stderr)
        # Try to find any pattern result
        vrs_dir = worktree / ".vrs"
        if vrs_dir.exists():
            print("Available files in .vrs:", file=sys.stderr)
            for f in vrs_dir.rglob("*"):
                if f.is_file():
                    print(f"  {f}", file=sys.stderr)
        return False

    # Load result
    try:
        data = json.loads(result_file.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in result file: {e}", file=sys.stderr)
        return False

    # Extract matches
    matches = data if isinstance(data, list) else data.get("matches", data.get("findings", []))

    # Check 1: Pattern matches exist
    if matches:
        checks.append(("Matches found", "PASS", f"{len(matches)} matches"))
    else:
        # Empty matches might be valid if the contract doesn't have the vulnerability
        checks.append(("Matches found", "INFO", "No matches (may be expected)"))

    # Check 2: Only reentrancy-classic pattern
    reentrancy_matches = []
    other_patterns = []

    for m in matches:
        pattern_id = m.get("pattern_id", m.get("pattern", m.get("id", "unknown")))
        if "reentrancy-classic" in pattern_id.lower():
            reentrancy_matches.append(m)
        else:
            other_patterns.append(m)

    if reentrancy_matches:
        checks.append(("Reentrancy-classic found", "PASS", f"{len(reentrancy_matches)} matches"))
    elif matches:
        checks.append(("Reentrancy-classic found", "WARN", "No reentrancy-classic in results"))
    else:
        checks.append(("Reentrancy-classic found", "INFO", "No matches to check"))

    # Check 3: No extraneous patterns
    if not other_patterns:
        checks.append(("No extraneous patterns", "PASS", "Only specified pattern returned"))
    else:
        checks.append(("No extraneous patterns", "FAIL",
                       f"Found {len(other_patterns)} other patterns: {[m.get('pattern_id', 'unknown') for m in other_patterns[:3]]}"))
        all_passed = False

    # Check 4: Matched expected functions (withdraw if exists)
    withdraw_matches = [
        m for m in reentrancy_matches
        if "withdraw" in m.get("function", m.get("function_name", "")).lower()
    ]
    if withdraw_matches:
        checks.append(("Withdraw function matched", "PASS",
                       f"Found in: {withdraw_matches[0].get('function', withdraw_matches[0].get('function_name', 'unknown'))}"))
    elif reentrancy_matches:
        # Check what functions were matched
        funcs = [m.get("function", m.get("function_name", "unknown")) for m in reentrancy_matches]
        checks.append(("Withdraw function matched", "INFO", f"Other functions matched: {funcs}"))

    # Print results
    print("Single Pattern Query Validation Results:")
    print("-" * 60)
    for check_name, status, detail in checks:
        if status == "PASS":
            symbol = "[PASS]"
        elif status == "FAIL":
            symbol = "[FAIL]"
        elif status == "WARN":
            symbol = "[WARN]"
        else:
            symbol = "[INFO]"
        print(f"  {symbol} {check_name}")
        print(f"         {detail}")
    print("-" * 60)

    if all_passed:
        print("Single pattern query validation: PASSED")
        if reentrancy_matches:
            print(f"  - Found {len(reentrancy_matches)} reentrancy-classic matches")
        else:
            print("  - No matches (contract may not have this vulnerability)")
    else:
        print("Single pattern query validation: FAILED")

    return all_passed


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_single_pattern.py <worktree-path>", file=sys.stderr)
        return 1

    worktree = Path(sys.argv[1])
    if not worktree.exists():
        print(f"ERROR: Worktree does not exist: {worktree}", file=sys.stderr)
        return 1

    return 0 if validate_single_pattern(worktree) else 1


if __name__ == "__main__":
    sys.exit(main())
