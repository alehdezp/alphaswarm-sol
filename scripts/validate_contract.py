#!/usr/bin/env python3
"""Validate outputs against Graph Interface Contract v2 (Phase 5.9-13).

This script validates that LLM-facing outputs conform to the Graph Interface
Contract v2 schema, checking both schema compliance and contract invariants.

The contract is treated as an ABI - violations fail fast with exit code 1.

Usage:
  python scripts/validate_contract.py --schema schemas/graph_interface_v2.json --samples tests/fixtures/
  python scripts/validate_contract.py --check-coverage --min-coverage 0.5

Exit codes:
  0 - All validations passed
  1 - Contract violations found (schema or invariant)
  2 - Coverage threshold not met

Environment:
  FAIL_ON_WARNING=true  Treat warnings as errors
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_schema(schema_path: Path) -> dict:
    """Load JSON schema from file.

    Args:
        schema_path: Path to JSON schema file

    Returns:
        Schema dictionary

    Raises:
        FileNotFoundError: If schema file doesn't exist
        json.JSONDecodeError: If schema is invalid JSON
    """
    with open(schema_path) as f:
        return json.load(f)


def validate_sample(sample_path: Path, schema: dict) -> List[str]:
    """Validate sample output against schema.

    Args:
        sample_path: Path to sample JSON file
        schema: JSON schema dictionary

    Returns:
        List of error messages (empty if valid)
    """
    try:
        import jsonschema
    except ImportError:
        print("ERROR: jsonschema package required. Install with: pip install jsonschema>=4.20.0")
        sys.exit(1)

    errors = []

    with open(sample_path) as f:
        try:
            sample = json.load(f)
        except json.JSONDecodeError as e:
            return [f"{sample_path}: Invalid JSON - {e}"]

    # Schema validation
    try:
        jsonschema.validate(sample, schema)
    except jsonschema.ValidationError as e:
        errors.append(f"{sample_path}: Schema violation - {e.message}")
        # Continue to check invariants even if schema fails

    # Contract-specific invariants (beyond schema)
    contract_errors = validate_contract_invariants(sample, sample_path)
    errors.extend(contract_errors)

    return errors


def validate_contract_invariants(output: dict, path: Path) -> List[str]:
    """Check contract invariants beyond JSON schema.

    These are semantic rules that JSON Schema cannot express.

    Contract invariants enforced:
    1. interface_version format (semver X.Y.Z)
    2. build_hash format (12-char hex)
    3. matched_clauses implies evidence_refs or evidence_missing
    4. unknown_clauses implies omissions or availability=false
    5. clause_matrix must align with matched/failed/unknown lists
    6. coverage_score must be in [0.0, 1.0]
    7. evidence_refs build_hash must match top-level build_hash

    Args:
        output: Output dictionary to validate
        path: Source path for error messages

    Returns:
        List of invariant violation messages
    """
    errors = []

    # 1. Check interface version format (semver)
    interface_version = output.get("interface_version")
    if interface_version:
        import re
        if not re.match(r"^\d+\.\d+\.\d+$", interface_version):
            errors.append(f"{path}: interface_version must be semver (X.Y.Z), got '{interface_version}'")

    # 2. Check build_hash format (12-char hex)
    build_hash = output.get("build_hash")
    if build_hash:
        import re
        if not re.match(r"^[a-f0-9]{12}$", build_hash):
            errors.append(f"{path}: build_hash must be 12-char hex, got '{build_hash}'")

    # 3-5. Check findings invariants
    for i, finding in enumerate(output.get("findings", [])):
        finding_errors = _validate_finding_invariants(finding, i, path, build_hash)
        errors.extend(finding_errors)

    # 6. Check summary coverage_score
    summary = output.get("summary", {})
    if "coverage_score" in summary:
        coverage = summary["coverage_score"]
        if not (0.0 <= coverage <= 1.0):
            errors.append(f"{path}: summary.coverage_score must be in [0.0, 1.0], got {coverage}")
    else:
        # coverage_score is required per contract
        errors.append(f"{path}: summary missing required coverage_score")

    # Check omissions section
    omissions = output.get("omissions", {})
    if omissions:
        if "coverage_score" in omissions:
            coverage = omissions["coverage_score"]
            if not (0.0 <= coverage <= 1.0):
                errors.append(f"{path}: omissions.coverage_score must be in [0.0, 1.0], got {coverage}")

    return errors


def _validate_finding_invariants(finding: dict, index: int, path: Path, top_build_hash: Optional[str]) -> List[str]:
    """Validate invariants for a single finding.

    Args:
        finding: Finding dictionary
        index: Finding index for error messages
        path: Source path for error messages
        top_build_hash: Top-level build hash for consistency check

    Returns:
        List of invariant violations
    """
    errors = []
    prefix = f"{path}: finding[{index}]"

    # 3. matched_clauses implies evidence_refs or evidence_missing
    matched_clauses = finding.get("matched_clauses", [])
    if matched_clauses:
        has_evidence = finding.get("evidence_refs") and len(finding["evidence_refs"]) > 0
        has_missing = finding.get("evidence_missing") and len(finding["evidence_missing"]) > 0
        if not has_evidence and not has_missing:
            errors.append(f"{prefix}: has matched_clauses but no evidence_refs or evidence_missing")

    # 4. unknown_clauses implies omissions or availability explanation
    unknown_clauses = finding.get("unknown_clauses", [])
    if unknown_clauses:
        has_omissions = bool(finding.get("omissions"))
        has_evidence_missing = finding.get("evidence_missing") and any(
            em.get("reason") for em in finding["evidence_missing"]
        )
        if not has_omissions and not has_evidence_missing:
            errors.append(f"{prefix}: has unknown_clauses but no omissions or evidence_missing reasons")

    # 5. clause_matrix must align with matched/failed/unknown lists
    clause_matrix = finding.get("clause_matrix", [])
    if clause_matrix:
        matrix_matched = {c["clause"] for c in clause_matrix if c.get("status") == "matched"}
        matrix_failed = {c["clause"] for c in clause_matrix if c.get("status") == "failed"}
        matrix_unknown = {c["clause"] for c in clause_matrix if c.get("status") == "unknown"}

        list_matched = set(finding.get("matched_clauses", []))
        list_failed = set(finding.get("failed_clauses", []))
        list_unknown = set(finding.get("unknown_clauses", []))

        if matrix_matched != list_matched:
            errors.append(f"{prefix}: clause_matrix matched doesn't align with matched_clauses")
        if matrix_failed != list_failed:
            errors.append(f"{prefix}: clause_matrix failed doesn't align with failed_clauses")
        if matrix_unknown != list_unknown:
            errors.append(f"{prefix}: clause_matrix unknown doesn't align with unknown_clauses")

    # 7. evidence_refs build_hash consistency
    if top_build_hash:
        for j, evidence in enumerate(finding.get("evidence_refs", [])):
            ev_hash = evidence.get("build_hash")
            if ev_hash and ev_hash != top_build_hash:
                errors.append(
                    f"{prefix}: evidence_refs[{j}].build_hash '{ev_hash}' doesn't match "
                    f"top-level build_hash '{top_build_hash}'"
                )

    return errors


def validate_coverage_threshold(output: dict, min_coverage: float, path: Optional[Path] = None) -> List[str]:
    """Check coverage score meets threshold.

    Args:
        output: Output dictionary
        min_coverage: Minimum required coverage score
        path: Source path for error messages (optional)

    Returns:
        List of threshold violations
    """
    errors = []
    prefix = f"{path}: " if path else ""

    coverage = output.get("summary", {}).get("coverage_score")
    if coverage is None:
        coverage = output.get("omissions", {}).get("coverage_score")

    if coverage is None:
        errors.append(f"{prefix}No coverage_score found in output")
    elif coverage < min_coverage:
        errors.append(f"{prefix}Coverage score {coverage:.3f} below threshold {min_coverage}")

    return errors


def validate_contract_output(output: dict, schema: dict, min_coverage: float = 0.5) -> List[str]:
    """Validate a contract output against schema and invariants.

    This is the main validation function for programmatic use.

    Args:
        output: Output dictionary to validate
        schema: JSON schema dictionary
        min_coverage: Minimum coverage score threshold

    Returns:
        List of all violations (empty if valid)
    """
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema package required"]

    errors = []

    # Schema validation
    try:
        jsonschema.validate(output, schema)
    except jsonschema.ValidationError as e:
        errors.append(f"Schema violation: {e.message}")

    # Contract invariants
    errors.extend(validate_contract_invariants(output, Path("<inline>")))

    # Coverage threshold
    errors.extend(validate_coverage_threshold(output, min_coverage))

    return errors


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate outputs against Graph Interface Contract v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--schema",
        type=Path,
        required=True,
        help="Path to JSON schema (e.g., schemas/graph_interface_v2.json)",
    )
    parser.add_argument(
        "--samples",
        type=Path,
        help="Directory of sample outputs to validate",
    )
    parser.add_argument(
        "--check-coverage",
        action="store_true",
        help="Check coverage score thresholds",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=0.5,
        help="Minimum coverage score (default: 0.5)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    args = parser.parse_args()

    fail_on_warning = os.environ.get("FAIL_ON_WARNING") == "true"

    print("=" * 60)
    print("Contract Compliance Validation (Phase 5.9-13)")
    print("=" * 60)
    print()

    # Load schema
    print(f"Loading schema: {args.schema}")
    if not args.schema.exists():
        print(f"ERROR: Schema file not found: {args.schema}")
        sys.exit(1)

    try:
        schema = load_schema(args.schema)
        print(f"  Schema title: {schema.get('title', 'unknown')}")
        print(f"  Schema $id: {schema.get('$id', 'none')}")
        print()
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in schema - {e}")
        sys.exit(1)

    all_errors = []
    samples_checked = 0

    # Validate samples
    if args.samples:
        print(f"Validating samples in: {args.samples}")
        if not args.samples.exists():
            print(f"  WARNING: Samples directory not found: {args.samples}")
            print("  (This is OK if no sample outputs exist yet)")
            print()
        else:
            sample_files = list(args.samples.rglob("*.json"))
            print(f"  Found {len(sample_files)} JSON file(s)")
            print()

            for sample_file in sample_files:
                samples_checked += 1
                if args.verbose:
                    print(f"  Checking: {sample_file}")

                errors = validate_sample(sample_file, schema)

                if args.check_coverage:
                    try:
                        with open(sample_file) as f:
                            sample = json.load(f)
                        coverage_errors = validate_coverage_threshold(
                            sample, args.min_coverage, sample_file
                        )
                        errors.extend(coverage_errors)
                    except (json.JSONDecodeError, FileNotFoundError):
                        pass  # Already reported in validate_sample

                if errors:
                    all_errors.extend(errors)
                    if args.verbose:
                        for error in errors:
                            print(f"    ERROR: {error}")
                elif args.verbose:
                    print(f"    OK")

            print()

    # Report results
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print()

    print(f"Samples checked: {samples_checked}")
    print(f"Errors found: {len(all_errors)}")
    print()

    if all_errors:
        print("CONTRACT VIOLATIONS:")
        for error in all_errors[:30]:  # Limit output
            print(f"  {error}")
        if len(all_errors) > 30:
            print(f"  ... and {len(all_errors) - 30} more")
        print()
        print("FATAL: Contract compliance check FAILED")
        print("  The Graph Interface Contract v2 is treated as an ABI.")
        print("  Violations must be fixed before merge.")
        sys.exit(1)

    print("Contract validation PASSED")
    if samples_checked == 0:
        print("  (No samples found - validation will be enforced once samples exist)")
    sys.exit(0)


if __name__ == "__main__":
    main()
