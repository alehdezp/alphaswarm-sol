#!/usr/bin/env python3
"""
Validate Threat-to-Pattern Matrix against actual patterns.

This script ensures the threat matrix in docs/architecture/threat-pattern-matrix.md
is accurate and not just decorative documentation.

Usage:
    python scripts/validate_threat_matrix.py
    python scripts/validate_threat_matrix.py --update-matrix
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import yaml

# Threat categories and their expected pattern prefixes
THREAT_CATEGORIES = {
    "access_control": {
        "prefixes": ["auth-", "weak-access", "tx-origin", "msg-sender-auth", "has-user-input-writes"],
        "pattern_keywords": ["access", "gate", "authorization", "privileged"],
    },
    "reentrancy": {
        "prefixes": ["reentrancy-", "state-write-after-call"],
        "pattern_keywords": ["reentrancy", "reentrant", "callback"],
    },
    "oracle": {
        "prefixes": ["oracle-"],
        "pattern_keywords": ["oracle", "price", "feed", "staleness", "chainlink"],
    },
    "mev_ordering": {
        "prefixes": ["mev-"],
        "pattern_keywords": ["mev", "slippage", "deadline", "frontrun", "sandwich"],
    },
    "governance": {
        "prefixes": ["gov-", "governance-"],
        "pattern_keywords": ["governance", "vote", "proposal", "timelock"],
    },
    "upgradeability": {
        "prefixes": ["upgrade-", "proxy-", "initializer-"],
        "pattern_keywords": ["upgrade", "proxy", "implementation", "storage gap", "initializer"],
    },
    "token_flaws": {
        "prefixes": ["token-"],
        "pattern_keywords": ["erc20", "transfer", "approve", "fee-on-transfer", "erc777"],
    },
    "dos": {
        "prefixes": ["dos-"],
        "pattern_keywords": ["dos", "unbounded", "loop", "gas", "revert"],
    },
    "crypto": {
        "prefixes": ["crypto-", "merkle-"],
        "pattern_keywords": ["signature", "ecrecover", "chainid", "permit", "replay"],
    },
}


def load_patterns(patterns_dir: Path) -> Dict[str, dict]:
    """Load all YAML patterns from the patterns directory."""
    patterns = {}

    for yaml_file in patterns_dir.rglob("*.yaml"):
        try:
            with open(yaml_file) as f:
                content = yaml.safe_load(f)
                if content and isinstance(content, dict):
                    pattern_id = content.get("id", yaml_file.stem)
                    patterns[pattern_id] = {
                        "file": str(yaml_file),
                        "name": content.get("name", pattern_id),
                        "severity": content.get("severity", "unknown"),
                        "lens": content.get("lens", []),
                        "raw": content,
                    }
        except Exception as e:
            print(f"Warning: Failed to parse {yaml_file}: {e}", file=sys.stderr)

    return patterns


def categorize_pattern(pattern_id: str, pattern_data: dict) -> Set[str]:
    """Determine which threat categories a pattern belongs to."""
    categories = set()

    pattern_id_lower = pattern_id.lower()
    pattern_name_lower = pattern_data.get("name", "").lower()

    for category, config in THREAT_CATEGORIES.items():
        # Check prefixes
        for prefix in config["prefixes"]:
            if pattern_id_lower.startswith(prefix):
                categories.add(category)
                break

        # Check keywords in name
        for keyword in config["pattern_keywords"]:
            if keyword in pattern_id_lower or keyword in pattern_name_lower:
                categories.add(category)
                break

    return categories


def parse_matrix_patterns(matrix_path: Path) -> Dict[str, List[str]]:
    """Extract pattern IDs mentioned in the threat matrix."""
    matrix_patterns = {}

    with open(matrix_path) as f:
        content = f.read()

    # Parse pattern tables
    current_category = None
    for line in content.split("\n"):
        # Detect category headers
        if line.startswith("## "):
            category_match = re.search(r"## \d+\. (.+)", line)
            if category_match:
                current_category = category_match.group(1).lower().replace(" ", "_").replace("/", "_")
                matrix_patterns[current_category] = []

        # Extract pattern IDs from table rows
        if current_category and line.startswith("| `"):
            pattern_match = re.search(r"\| `([^`]+)`", line)
            if pattern_match:
                matrix_patterns[current_category].append(pattern_match.group(1))

    return matrix_patterns


def validate_matrix(patterns_dir: Path, matrix_path: Path) -> Tuple[List[str], List[str], Dict[str, Set[str]]]:
    """
    Validate that the threat matrix matches actual patterns.

    Returns:
        - errors: Critical issues (patterns in matrix don't exist)
        - warnings: Non-critical issues (patterns exist but not in matrix)
        - coverage: Mapping of category -> actual patterns
    """
    errors = []
    warnings = []
    coverage = {}

    # Load actual patterns
    patterns = load_patterns(patterns_dir)
    print(f"Loaded {len(patterns)} patterns from {patterns_dir}")

    # Parse matrix
    matrix_patterns = parse_matrix_patterns(matrix_path)
    print(f"Found {sum(len(v) for v in matrix_patterns.values())} pattern references in matrix")

    # Build actual coverage
    for pattern_id, pattern_data in patterns.items():
        categories = categorize_pattern(pattern_id, pattern_data)
        for category in categories:
            if category not in coverage:
                coverage[category] = set()
            coverage[category].add(pattern_id)

    # Check matrix patterns exist
    all_pattern_ids = set(patterns.keys())
    for category, matrix_ids in matrix_patterns.items():
        for pattern_id in matrix_ids:
            # Normalize pattern ID for matching
            normalized = pattern_id.lower().replace("-", "_")
            found = False
            for actual_id in all_pattern_ids:
                if pattern_id == actual_id or normalized in actual_id.lower().replace("-", "_"):
                    found = True
                    break

            if not found:
                errors.append(f"Matrix references non-existent pattern: {pattern_id} (category: {category})")

    # Check for patterns not in matrix
    matrix_all = set()
    for ids in matrix_patterns.values():
        matrix_all.update(ids)

    for pattern_id in all_pattern_ids:
        categories = categorize_pattern(pattern_id, patterns[pattern_id])
        if categories and pattern_id not in matrix_all:
            warnings.append(f"Pattern exists but not in matrix: {pattern_id} (categories: {categories})")

    return errors, warnings, coverage


def generate_coverage_report(coverage: Dict[str, Set[str]]) -> str:
    """Generate a coverage summary report."""
    lines = [
        "# Threat Coverage Validation Report",
        "",
        "## Pattern Coverage by Threat Category",
        "",
        "| Category | Pattern Count | Patterns |",
        "|----------|--------------|----------|",
    ]

    for category in sorted(THREAT_CATEGORIES.keys()):
        patterns = sorted(coverage.get(category, set()))
        count = len(patterns)
        pattern_list = ", ".join(patterns[:5])
        if len(patterns) > 5:
            pattern_list += f" (+{len(patterns)-5} more)"
        lines.append(f"| {category} | {count} | {pattern_list} |")

    # Summary
    total = sum(len(p) for p in coverage.values())
    covered = sum(1 for c, p in coverage.items() if len(p) > 0)

    lines.extend([
        "",
        "## Summary",
        "",
        f"- Total patterns categorized: {total}",
        f"- Categories with coverage: {covered}/{len(THREAT_CATEGORIES)}",
        "",
    ])

    # Gaps
    gaps = [c for c in THREAT_CATEGORIES.keys() if len(coverage.get(c, set())) == 0]
    if gaps:
        lines.append("## GAPS - Categories without patterns:")
        for gap in gaps:
            lines.append(f"- {gap}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Validate Threat-to-Pattern Matrix")
    parser.add_argument("--patterns-dir", default="patterns", help="Patterns directory")
    parser.add_argument("--matrix", default="docs/architecture/threat-pattern-matrix.md", help="Matrix file")
    parser.add_argument("--update-matrix", action="store_true", help="Update matrix with findings")
    parser.add_argument("--ci", action="store_true", help="CI mode - exit 1 on errors")
    args = parser.parse_args()

    # Resolve paths
    root = Path(__file__).parent.parent
    patterns_dir = root / args.patterns_dir
    matrix_path = root / args.matrix

    if not patterns_dir.exists():
        print(f"Error: Patterns directory not found: {patterns_dir}", file=sys.stderr)
        sys.exit(1)

    if not matrix_path.exists():
        print(f"Error: Matrix file not found: {matrix_path}", file=sys.stderr)
        sys.exit(1)

    # Validate
    errors, warnings, coverage = validate_matrix(patterns_dir, matrix_path)

    # Print report
    print("\n" + "=" * 60)
    print(generate_coverage_report(coverage))
    print("=" * 60 + "\n")

    # Print errors
    if errors:
        print("ERRORS (matrix references non-existent patterns):")
        for error in errors:
            print(f"  - {error}")
        print()

    # Print warnings
    if warnings:
        print("WARNINGS (patterns not documented in matrix):")
        for warning in warnings[:20]:  # Limit output
            print(f"  - {warning}")
        if len(warnings) > 20:
            print(f"  ... and {len(warnings) - 20} more")
        print()

    # Summary
    print("=" * 60)
    print(f"Validation complete: {len(errors)} errors, {len(warnings)} warnings")

    if args.ci and errors:
        print("\nCI MODE: Failing due to errors")
        sys.exit(1)

    if errors:
        print("\nFix errors before merging!")
        sys.exit(1)
    else:
        print("\nMatrix validation passed!")


if __name__ == "__main__":
    main()
