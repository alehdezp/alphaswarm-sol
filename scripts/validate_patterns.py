#!/usr/bin/env python3
"""Validate patterns against taxonomy registry (Phase 5.9-13).

This script validates that patterns use registered operations from the
taxonomy registry, detecting deprecated operations and unknown names.

Usage:
  python scripts/validate_patterns.py --strict
  python scripts/validate_patterns.py --check-taxonomy --patterns vulndocs/
  python scripts/validate_patterns.py --check-vql --vql-files tests/

Exit codes:
  0 - All validations passed
  1 - Errors found (unknown operations, deprecated without migration)
  2 - Warnings treated as errors (deprecated operations in strict mode)

Environment:
  FAIL_ON_WARNING=true    Treat warnings as errors
  FAIL_ON_DEPRECATED=true Fail on deprecated operation usage
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml


def load_taxonomy_registry():
    """Load canonical taxonomy from registry.

    Returns:
        OpsTaxonomyRegistry instance

    Raises:
        ImportError: If taxonomy module not available
    """
    # Add src to path for direct script execution
    src_path = Path(__file__).parent.parent / "src"
    if src_path.exists() and str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    from alphaswarm_sol.kg.taxonomy import OpsTaxonomyRegistry

    return OpsTaxonomyRegistry()


def validate_patterns(patterns_dir: Path, registry) -> Tuple[List[str], List[str]]:
    """Validate all pattern files in directory.

    Args:
        patterns_dir: Directory containing patterns
        registry: Taxonomy registry instance

    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []

    # Find all pattern YAML files
    pattern_files = list(patterns_dir.rglob("*.yaml")) + list(patterns_dir.rglob("*.yml"))

    for pattern_file in pattern_files:
        # Skip non-pattern files
        if "patterns" not in str(pattern_file):
            continue

        try:
            file_errors, file_warnings = validate_pattern_operations(pattern_file, registry)
            errors.extend(file_errors)
            warnings.extend(file_warnings)
        except Exception as e:
            errors.append(f"{pattern_file}: Failed to parse - {e}")

    return errors, warnings


def validate_pattern_operations(pattern_path: Path, registry) -> Tuple[List[str], List[str]]:
    """Check pattern uses registered operations.

    Args:
        pattern_path: Path to pattern YAML file
        registry: Taxonomy registry instance

    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []

    with open(pattern_path) as f:
        try:
            pattern = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return [f"{pattern_path}: Invalid YAML - {e}"], []

    if not pattern or not isinstance(pattern, dict):
        return [], []

    # Extract operations used in pattern
    operations = extract_operations_from_pattern(pattern)

    for op in operations:
        # Check if operation is registered
        if not registry.is_valid_operation(op):
            errors.append(f"{pattern_path}: Unknown operation '{op}'")
        elif registry.is_deprecated(op):
            canonical = registry.resolve(op)
            warnings.append(
                f"{pattern_path}: Deprecated operation '{op}', use '{canonical}'"
            )

    return errors, warnings


def extract_operations_from_pattern(pattern: dict) -> Set[str]:
    """Extract all operation references from pattern.

    Args:
        pattern: Pattern dictionary

    Returns:
        Set of operation names referenced
    """
    operations: Set[str] = set()

    # Handle match section
    match_section = pattern.get("match", {})

    # Tier A matching
    tier_a = match_section.get("tier_a", {})
    operations.update(_extract_from_tier(tier_a))

    # Tier B matching
    tier_b = match_section.get("tier_b", {})
    operations.update(_extract_from_tier(tier_b))

    # Tier C matching (label-dependent)
    tier_c = match_section.get("tier_c", [])
    if isinstance(tier_c, list):
        for clause in tier_c:
            if isinstance(clause, dict):
                # Labels may reference operations indirectly
                if "has_label" in clause:
                    label = clause["has_label"]
                    # Extract operation from label path (e.g., "state_mutation.balance_update")
                    ops = _extract_ops_from_label(label)
                    operations.update(ops)

    # Handle detection section (older format)
    detection = pattern.get("detection", {})
    operations.update(_extract_from_tier(detection))

    return operations


def _extract_from_tier(tier: dict) -> Set[str]:
    """Extract operations from tier matching section.

    Args:
        tier: Tier matching dictionary (all, any, none)

    Returns:
        Set of operation names
    """
    operations: Set[str] = set()

    # Handle 'all', 'any', 'none' clause lists
    for clause_list_key in ["all", "any", "none"]:
        clauses = tier.get(clause_list_key, [])
        if not isinstance(clauses, list):
            continue

        for clause in clauses:
            if not isinstance(clause, dict):
                continue

            # Direct operation references
            if "has_operation" in clause:
                operations.add(clause["has_operation"])

            if "has_all_operations" in clause:
                ops = clause["has_all_operations"]
                if isinstance(ops, list):
                    operations.update(ops)

            if "has_any_operation" in clause:
                ops = clause["has_any_operation"]
                if isinstance(ops, list):
                    operations.update(ops)

            # Sequence ordering
            if "sequence_order" in clause:
                seq = clause["sequence_order"]
                if isinstance(seq, dict):
                    if "before" in seq:
                        operations.add(seq["before"])
                    if "after" in seq:
                        operations.add(seq["after"])

            # Behavioral signature
            if "behavioral_signature" in clause:
                sig = clause["behavioral_signature"]
                # Parse signature like "R:bal->X:out->W:bal"
                ops = _extract_ops_from_signature(sig)
                operations.update(ops)

    return operations


def _extract_ops_from_label(label: str) -> Set[str]:
    """Extract operation references from a label path.

    Labels like "state_mutation.balance_update" may imply operations.
    This is a heuristic mapping - not all labels map to operations.

    Args:
        label: Label path string

    Returns:
        Set of operation names (may be empty)
    """
    # Common label-to-operation mappings
    label_op_map = {
        "balance_update": "WRITES_USER_BALANCE",
        "balance_read": "READS_USER_BALANCE",
        "value_transfer": "TRANSFERS_VALUE_OUT",
        "external_call": "CALLS_EXTERNAL",
        "untrusted_call": "CALLS_UNTRUSTED",
        "owner_change": "MODIFIES_OWNER",
        "role_change": "MODIFIES_ROLES",
        "oracle_read": "READS_ORACLE",
        "permission_check": "CHECKS_PERMISSION",
    }

    operations: Set[str] = set()
    label_lower = label.lower()

    for label_part, op in label_op_map.items():
        if label_part in label_lower:
            operations.add(op)

    return operations


def _extract_ops_from_signature(signature: str) -> Set[str]:
    """Extract operations from behavioral signature.

    Signatures use short codes like "R:bal->X:out->W:bal".
    This maps short codes back to canonical operation names.

    Args:
        signature: Behavioral signature string

    Returns:
        Set of operation names
    """
    # Short code to operation mapping
    short_code_map = {
        "X:out": "TRANSFERS_VALUE_OUT",
        "X:in": "RECEIVES_VALUE_IN",
        "R:bal": "READS_USER_BALANCE",
        "W:bal": "WRITES_USER_BALANCE",
        "C:auth": "CHECKS_PERMISSION",
        "M:own": "MODIFIES_OWNER",
        "M:role": "MODIFIES_ROLES",
        "X:call": "CALLS_EXTERNAL",
        "X:unk": "CALLS_UNTRUSTED",
        "R:ext": "READS_EXTERNAL_VALUE",
        "M:crit": "MODIFIES_CRITICAL_STATE",
        "I:init": "INITIALIZES_STATE",
        "R:orc": "READS_ORACLE",
        "L:arr": "LOOPS_OVER_ARRAY",
        "U:time": "USES_TIMESTAMP",
        "U:blk": "USES_BLOCK_DATA",
        "A:div": "PERFORMS_DIVISION",
        "A:mul": "PERFORMS_MULTIPLICATION",
        "V:in": "VALIDATES_INPUT",
        "E:evt": "EMITS_EVENT",
    }

    operations: Set[str] = set()

    # Extract short codes from signature
    # Handle formats like "R:bal->X:out->W:bal" or "R:bal → X:out → W:bal"
    parts = re.split(r"[-→>]+", signature)

    for part in parts:
        part = part.strip()
        if part in short_code_map:
            operations.add(short_code_map[part])

    return operations


def taxonomy_check(registry) -> Dict[str, any]:
    """Return taxonomy registry statistics.

    Args:
        registry: Taxonomy registry instance

    Returns:
        Dictionary with registry statistics
    """
    return {
        "version": registry.version,
        "canonical_ops": len(registry.canonical_ops()),
        "canonical_edges": len(registry.canonical_edges()),
        "deprecated_count": len([op for op in registry.canonical_ops() if registry.is_deprecated(op)]),
    }


def validate_vql_files(vql_dir: Path, registry) -> Tuple[List[str], List[str]]:
    """Check VQL files use registered operations.

    Args:
        vql_dir: Directory containing VQL files or tests
        registry: Taxonomy registry instance

    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []

    # Find VQL files
    vql_files = list(vql_dir.rglob("*.vql"))

    # Also check Python test files that might contain VQL queries
    py_files = list(vql_dir.rglob("*.py"))

    for vql_file in vql_files:
        try:
            with open(vql_file) as f:
                content = f.read()

            file_errors, file_warnings = _validate_vql_content(content, vql_file, registry)
            errors.extend(file_errors)
            warnings.extend(file_warnings)
        except Exception as e:
            errors.append(f"{vql_file}: Failed to read - {e}")

    # Check Python files for embedded VQL
    for py_file in py_files:
        try:
            with open(py_file) as f:
                content = f.read()

            # Look for VQL patterns in strings
            if "FIND" in content and "WHERE" in content:
                file_errors, file_warnings = _validate_vql_content(content, py_file, registry)
                errors.extend(file_errors)
                warnings.extend(file_warnings)
        except Exception as e:
            # Skip files that can't be read
            pass

    return errors, warnings


def _validate_vql_content(content: str, source_path: Path, registry) -> Tuple[List[str], List[str]]:
    """Validate VQL content for registered operations.

    Args:
        content: VQL or Python file content
        source_path: Source file path for error messages
        registry: Taxonomy registry instance

    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []

    # Extract potential operation names (SCREAMING_SNAKE_CASE)
    ops = set(re.findall(r"\b([A-Z][A-Z_]+[A-Z])\b", content))

    # Filter to likely operation names
    op_prefixes = (
        "TRANSFERS_",
        "READS_",
        "WRITES_",
        "CHECKS_",
        "MODIFIES_",
        "CALLS_",
        "USES_",
        "PERFORMS_",
        "VALIDATES_",
        "EMITS_",
        "LOOPS_",
        "INITIALIZES_",
        "RECEIVES_",
    )

    for op in ops:
        if op.startswith(op_prefixes):
            if not registry.is_valid_operation(op):
                errors.append(f"{source_path}: Unknown operation '{op}'")
            elif registry.is_deprecated(op):
                canonical = registry.resolve(op)
                warnings.append(f"{source_path}: Deprecated operation '{op}', use '{canonical}'")

    return errors, warnings


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate patterns against taxonomy registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Exit codes:")[1] if "Exit codes:" in __doc__ else "",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any warning (same as FAIL_ON_WARNING=true)",
    )
    parser.add_argument(
        "--check-taxonomy",
        action="store_true",
        help="Check pattern operations against taxonomy registry",
    )
    parser.add_argument(
        "--check-vql",
        action="store_true",
        help="Check VQL files against taxonomy registry",
    )
    parser.add_argument(
        "--patterns",
        type=Path,
        default=Path("vulndocs/"),
        help="Pattern directory (default: vulndocs/)",
    )
    parser.add_argument(
        "--vql-files",
        type=Path,
        default=Path("tests/"),
        help="VQL files directory (default: tests/)",
    )
    parser.add_argument(
        "--show-stats",
        action="store_true",
        help="Show taxonomy registry statistics",
    )
    args = parser.parse_args()

    # Determine fail-fast settings
    fail_on_warning = args.strict or os.environ.get("FAIL_ON_WARNING") == "true"
    fail_on_deprecated = os.environ.get("FAIL_ON_DEPRECATED") == "true"

    print("=" * 60)
    print("Pattern Taxonomy Validation (Phase 5.9-13)")
    print("=" * 60)
    print()

    # Load taxonomy registry
    try:
        registry = load_taxonomy_registry()
        print(f"Taxonomy version: {registry.version}")
        print(f"Canonical operations: {len(registry.canonical_ops())}")
        print(f"Canonical edge types: {len(registry.canonical_edges())}")
        print()
    except ImportError as e:
        print(f"ERROR: Failed to load taxonomy registry - {e}")
        print("Make sure alphaswarm_sol package is installed.")
        sys.exit(1)

    if args.show_stats:
        stats = taxonomy_check(registry)
        print("Taxonomy Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print()
        sys.exit(0)

    all_errors = []
    all_warnings = []

    # Validate patterns
    if args.check_taxonomy:
        print(f"Checking patterns in: {args.patterns}")
        if not args.patterns.exists():
            print(f"  WARNING: Pattern directory not found: {args.patterns}")
        else:
            errors, warnings = validate_patterns(args.patterns, registry)
            all_errors.extend(errors)
            all_warnings.extend(warnings)
            print(f"  Patterns checked: {len(list(args.patterns.rglob('*.yaml')))}")
            print(f"  Errors: {len(errors)}")
            print(f"  Warnings: {len(warnings)}")
        print()

    # Validate VQL files
    if args.check_vql:
        print(f"Checking VQL files in: {args.vql_files}")
        if not args.vql_files.exists():
            print(f"  WARNING: VQL directory not found: {args.vql_files}")
        else:
            errors, warnings = validate_vql_files(args.vql_files, registry)
            all_errors.extend(errors)
            all_warnings.extend(warnings)
            print(f"  VQL files checked: {len(list(args.vql_files.rglob('*.vql')))}")
            print(f"  Errors: {len(errors)}")
            print(f"  Warnings: {len(warnings)}")
        print()

    # If no specific checks requested, run both
    if not args.check_taxonomy and not args.check_vql:
        print("Running default checks (taxonomy + VQL)...")
        print()

        if args.patterns.exists():
            print(f"Checking patterns in: {args.patterns}")
            errors, warnings = validate_patterns(args.patterns, registry)
            all_errors.extend(errors)
            all_warnings.extend(warnings)
            print(f"  Patterns checked: {len(list(args.patterns.rglob('*.yaml')))}")
            print(f"  Errors: {len(errors)}")
            print(f"  Warnings: {len(warnings)}")
            print()

    # Report findings
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print()

    if all_warnings:
        print("WARNINGS:")
        for warning in all_warnings[:20]:  # Limit output
            print(f"  {warning}")
        if len(all_warnings) > 20:
            print(f"  ... and {len(all_warnings) - 20} more")
        print()

    if all_errors:
        print("ERRORS:")
        for error in all_errors[:20]:  # Limit output
            print(f"  {error}")
        if len(all_errors) > 20:
            print(f"  ... and {len(all_errors) - 20} more")
        print()

    # Exit codes
    if all_errors:
        print(f"FATAL: {len(all_errors)} error(s) found")
        sys.exit(1)

    if all_warnings and (fail_on_warning or fail_on_deprecated):
        print(f"FATAL: {len(all_warnings)} warning(s) treated as errors")
        print("  (FAIL_ON_WARNING or FAIL_ON_DEPRECATED is set)")
        sys.exit(2)

    print("Pattern taxonomy validation PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
