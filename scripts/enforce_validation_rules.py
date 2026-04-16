#!/usr/bin/env python3
"""
Enforce VALIDATION-RULES.md during plan execution.

This script runs pre/post execution checks to ensure validation plans
comply with mandatory rules. Failures BLOCK plan completion.

Usage:
    # Pre-execution: check dependencies exist
    python enforce_validation_rules.py --pre-check PLAN_ID

    # Post-execution: validate outputs
    python enforce_validation_rules.py --post-check PLAN_ID

    # Check wave gates
    python enforce_validation_rules.py --wave-gate WAVE_NUMBER

    # Full validation of all reports
    python enforce_validation_rules.py --validate-all

Exit codes:
    0: All checks passed
    1: Validation failures (BLOCKING)
    2: Warnings only (non-blocking)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# ============================================================================
# CONSTANTS
# ============================================================================

# Minimum duration thresholds by operation type (Rule F3)
MIN_DURATIONS = {
    "smoke_test": 5000,       # 5 seconds
    "agent_unit": 30000,      # 30 seconds
    "integration": 60000,     # 1 minute
    "e2e_audit": 120000,      # 2 minutes
    "full_audit": 180000,     # 3 minutes
}

# Minimum transcript lines by type (Rule F1)
MIN_TRANSCRIPT_LINES = {
    "smoke": 50,
    "agent": 100,
    "e2e": 200,
    "debate": 300,
}

# Required tool invocation markers (Rule F2)
REQUIRED_MARKERS = [
    r"alphaswarm\s+build-kg",
    r"Knowledge graph.*built",
    r"Attacker:|Defender:|Verifier:",
    r"\.sol\s*$|contracts/\w+\.sol",
]

# Plan dependencies
PLAN_DEPENDENCIES = {
    "02-v4": [
        "src/alphaswarm_sol/testing/blind_sandbox.py",
        "src/alphaswarm_sol/testing/supervision_loop.py",
    ],
    "02.5-v4": [
        ".vrs/testing/reports/smoke-test.json",
    ],
    "03-v4": [
        ".vrs/testing/reports/smoke-test.json",
    ],
    "04-v4": [
        ".vrs/testing/reports/agent-unit-tests.json",
    ],
    "05-v4": [
        ".vrs/testing/reports/orchestration-integration.json",
        ".vrs/corpus/ground-truth.yaml",
    ],
    "05.5-v4": [
        ".vrs/testing/reports/e2e-audit-validation.json",
    ],
    "06-v4": [
        ".vrs/testing/reports/orchestration-integration.json",
        ".vrs/corpus/ground-truth.yaml",
    ],
    "07-v4": [
        ".vrs/testing/reports/e2e-audit-validation.json",
        ".vrs/testing/reports/solo-vs-swarm-ab.json",
    ],
    "08-v4": [
        ".vrs/testing/reports/e2e-audit-validation.json",
        ".vrs/testing/reports/solo-vs-swarm-ab.json",
        ".vrs/testing/reports/blind-validation.json",
    ],
    "08.5-v4": [
        ".vrs/testing/reports/ga-metrics-summary.json",
        ".vrs/testing/reports/ga-gate-evaluation.json",
    ],
}

# Wave gate conditions
WAVE_GATES = {
    3: {
        "name": "Smoke Verification",
        "files": [".vrs/testing/reports/smoke-test.json"],
        "checks": [
            ("smoke-test.json", "status", "passed"),
            ("smoke-test.json", "duration_ms", ">= 5000"),
        ],
    },
    4: {
        "name": "Agent Verification",
        "files": [".vrs/testing/reports/agent-unit-tests.json"],
        "checks": [
            ("agent-unit-tests.json", "all_passed", True),
        ],
    },
    5: {
        "name": "Integration Verification",
        "files": [".vrs/testing/reports/orchestration-integration.json"],
        "checks": [],
    },
    6: {
        "name": "E2E Verification",
        "files": [
            ".vrs/testing/reports/e2e-audit-validation.json",
            ".vrs/testing/reports/solo-vs-swarm-ab.json",
        ],
        "checks": [],
    },
    7: {
        "name": "Blind Verification",
        "files": [".vrs/testing/reports/blind-validation.json"],
        "checks": [],
    },
}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ValidationResult:
    """Result of a validation check."""
    rule: str
    passed: bool
    message: str
    severity: str = "error"  # "error" or "warning"

    def __str__(self) -> str:
        status = "PASS" if self.passed else self.severity.upper()
        return f"[{status}] {self.rule}: {self.message}"


# ============================================================================
# RULE CHECKERS
# ============================================================================

def check_rule_a1_live_mode(report: dict, path: Path) -> ValidationResult:
    """A1: LIVE mode required for validation."""
    mode = report.get("mode") or report.get("metadata", {}).get("mode")

    if mode in ["mock", "simulated"]:
        return ValidationResult(
            rule="A1",
            passed=False,
            message=f"Report uses {mode} mode, not 'live'",
        )

    if mode != "live":
        return ValidationResult(
            rule="A1",
            passed=False,
            message=f"Mode declaration missing or invalid: {mode}",
        )

    return ValidationResult(
        rule="A1",
        passed=True,
        message="LIVE mode confirmed",
    )


def check_rule_a3_duration(report: dict, path: Path) -> ValidationResult:
    """A3: Real duration required."""
    duration_ms = report.get("duration_ms", 0)

    if duration_ms < 1000:
        return ValidationResult(
            rule="A3",
            passed=False,
            message=f"Duration too short: {duration_ms}ms (minimum 1000ms)",
        )

    return ValidationResult(
        rule="A3",
        passed=True,
        message=f"Duration valid: {duration_ms}ms",
    )


def check_rule_c1_perfect_metrics(report: dict, path: Path) -> ValidationResult:
    """C1: Perfect metrics are suspicious."""
    precision = report.get("precision", 0)
    recall = report.get("recall", 0)

    if precision >= 0.95 and recall >= 0.98:
        return ValidationResult(
            rule="C1",
            passed=False,
            message=f"Suspiciously perfect metrics (P={precision:.2f}, R={recall:.2f})",
            severity="warning",
        )

    return ValidationResult(
        rule="C1",
        passed=True,
        message="Metrics within expected variance",
    )


def check_rule_c3_variance(report: dict, path: Path) -> ValidationResult:
    """C3: Variance required across test cases."""
    by_contract = report.get("by_contract", [])

    if len(by_contract) < 2:
        return ValidationResult(
            rule="C3",
            passed=True,
            message="Not enough test cases for variance check",
        )

    # Check if all precision values are identical
    precisions = [c.get("precision") for c in by_contract if c.get("precision") is not None]
    if len(set(precisions)) == 1 and len(precisions) > 1:
        return ValidationResult(
            rule="C3",
            passed=False,
            message=f"All precision values identical: {precisions[0]}",
            severity="warning",
        )

    return ValidationResult(
        rule="C3",
        passed=True,
        message="Metrics show expected variance",
    )


def check_rule_e2_limitations(report: dict, path: Path) -> ValidationResult:
    """E2: Limitations section required."""
    limitations = report.get("limitations", [])

    if not limitations:
        return ValidationResult(
            rule="E2",
            passed=False,
            message="No limitations section",
        )

    return ValidationResult(
        rule="E2",
        passed=True,
        message=f"{len(limitations)} limitations documented",
    )


def check_rule_f3_duration_by_operation(report: dict, path: Path) -> ValidationResult:
    """F3: Duration must be realistic for operation type."""
    operation = report.get("operation", "unknown")
    duration_ms = report.get("duration_ms", 0)

    min_duration = MIN_DURATIONS.get(operation, 5000)

    if duration_ms < min_duration:
        return ValidationResult(
            rule="F3",
            passed=False,
            message=f"{operation} duration {duration_ms}ms < {min_duration}ms minimum",
        )

    return ValidationResult(
        rule="F3",
        passed=True,
        message=f"{operation} duration valid: {duration_ms}ms",
    )


def check_rule_f4_evidence(report: dict, path: Path) -> ValidationResult:
    """F4: Cross-evidence verification for findings."""
    findings = report.get("findings", [])

    if not findings:
        return ValidationResult(
            rule="F4",
            passed=True,
            message="No findings to verify",
        )

    missing_evidence = []
    for i, finding in enumerate(findings):
        finding_id = finding.get("id", f"finding-{i}")

        if not finding.get("graph_nodes"):
            missing_evidence.append(f"{finding_id}: no graph_nodes")
        if not finding.get("pattern_id"):
            missing_evidence.append(f"{finding_id}: no pattern_id")

        location = finding.get("location", "")
        if not location or ":" not in location:
            missing_evidence.append(f"{finding_id}: no valid location")

    if missing_evidence:
        return ValidationResult(
            rule="F4",
            passed=False,
            message=f"Missing evidence: {', '.join(missing_evidence[:3])}{'...' if len(missing_evidence) > 3 else ''}",
        )

    return ValidationResult(
        rule="F4",
        passed=True,
        message=f"All {len(findings)} findings have evidence",
    )


# ============================================================================
# TRANSCRIPT VALIDATION
# ============================================================================

def check_rule_f1_transcript_length(transcript: str, path: Path) -> ValidationResult:
    """F1: Transcript length verification."""
    lines = transcript.strip().split('\n')

    # Determine transcript type from filename
    filename = path.name.lower()
    if "smoke" in filename:
        min_lines = MIN_TRANSCRIPT_LINES["smoke"]
    elif "agent" in filename:
        min_lines = MIN_TRANSCRIPT_LINES["agent"]
    elif "e2e" in filename or "audit" in filename:
        min_lines = MIN_TRANSCRIPT_LINES["e2e"]
    elif "debate" in filename:
        min_lines = MIN_TRANSCRIPT_LINES["debate"]
    else:
        min_lines = 50  # Default minimum

    if len(lines) < min_lines:
        return ValidationResult(
            rule="F1",
            passed=False,
            message=f"Transcript has {len(lines)} lines (minimum {min_lines})",
        )

    # Check for Claude prompt markers
    if not any('>>>' in line for line in lines):
        return ValidationResult(
            rule="F1",
            passed=False,
            message="No Claude prompt markers (>>>) found",
        )

    return ValidationResult(
        rule="F1",
        passed=True,
        message=f"Transcript valid: {len(lines)} lines",
    )


def check_rule_f2_tool_invocations(transcript: str, path: Path) -> ValidationResult:
    """F2: Required tool invocations in transcript."""
    marker_matches = sum(
        1 for pattern in REQUIRED_MARKERS
        if re.search(pattern, transcript, re.IGNORECASE | re.MULTILINE)
    )

    if marker_matches < 2:
        return ValidationResult(
            rule="F2",
            passed=False,
            message=f"Only {marker_matches}/4 tool markers found (need >= 2)",
        )

    return ValidationResult(
        rule="F2",
        passed=True,
        message=f"{marker_matches}/4 tool markers found",
    )


# ============================================================================
# DEPENDENCY & GATE CHECKS
# ============================================================================

def check_dependencies(plan_id: str) -> list[ValidationResult]:
    """Check that required artifacts exist before execution."""
    results = []

    deps = PLAN_DEPENDENCIES.get(plan_id, [])

    for dep in deps:
        dep_path = Path(dep)
        if not dep_path.exists():
            results.append(ValidationResult(
                rule="G2",
                passed=False,
                message=f"Missing dependency: {dep}",
            ))
        else:
            results.append(ValidationResult(
                rule="G2",
                passed=True,
                message=f"Dependency found: {dep}",
            ))

    return results


def check_wave_gate(wave: int) -> list[ValidationResult]:
    """Check wave gate conditions."""
    results = []

    gate = WAVE_GATES.get(wave)
    if not gate:
        return [ValidationResult(
            rule="G3",
            passed=True,
            message=f"No gate defined for wave {wave}",
        )]

    # Check required files
    for file_path in gate["files"]:
        path = Path(file_path)
        if not path.exists():
            results.append(ValidationResult(
                rule="G3",
                passed=False,
                message=f"Gate '{gate['name']}': Missing {file_path}",
            ))
        else:
            results.append(ValidationResult(
                rule="G3",
                passed=True,
                message=f"Gate '{gate['name']}': Found {file_path}",
            ))

    # Check value conditions
    for filename, field, expected in gate.get("checks", []):
        file_path = Path(f".vrs/testing/reports/{filename}")
        if not file_path.exists():
            continue

        try:
            with open(file_path) as f:
                data = json.load(f)

            actual = data.get(field)

            # Handle comparison operators
            if isinstance(expected, str) and expected.startswith(">="):
                threshold = int(expected.split()[1])
                passed = actual >= threshold
            else:
                passed = actual == expected

            results.append(ValidationResult(
                rule="G3",
                passed=passed,
                message=f"Gate '{gate['name']}': {field}={actual} (expected {expected})",
            ))
        except Exception as e:
            results.append(ValidationResult(
                rule="G3",
                passed=False,
                message=f"Gate '{gate['name']}': Error reading {filename}: {e}",
            ))

    return results


# ============================================================================
# MAIN VALIDATION FUNCTIONS
# ============================================================================

def validate_report(path: Path) -> list[ValidationResult]:
    """Validate a single report against all rules."""
    results = []

    try:
        with open(path) as f:
            report = json.load(f)
    except Exception as e:
        return [ValidationResult(
            rule="PARSE",
            passed=False,
            message=f"Failed to parse report: {e}",
        )]

    # Run all report checks
    results.append(check_rule_a1_live_mode(report, path))
    results.append(check_rule_a3_duration(report, path))
    results.append(check_rule_c1_perfect_metrics(report, path))
    results.append(check_rule_c3_variance(report, path))
    results.append(check_rule_e2_limitations(report, path))
    results.append(check_rule_f3_duration_by_operation(report, path))
    results.append(check_rule_f4_evidence(report, path))

    return results


def validate_transcript(path: Path) -> list[ValidationResult]:
    """Validate a single transcript against anti-fabrication rules."""
    results = []

    try:
        transcript = path.read_text()
    except Exception as e:
        return [ValidationResult(
            rule="PARSE",
            passed=False,
            message=f"Failed to read transcript: {e}",
        )]

    results.append(check_rule_f1_transcript_length(transcript, path))
    results.append(check_rule_f2_tool_invocations(transcript, path))

    return results


def pre_execution_check(plan_id: str) -> tuple[bool, list[ValidationResult]]:
    """Run pre-execution checks for a plan."""
    results = check_dependencies(plan_id)

    # Check if any blocking failures
    blocking_failures = [r for r in results if not r.passed and r.severity == "error"]

    return len(blocking_failures) == 0, results


def post_execution_check(plan_id: str) -> tuple[bool, list[ValidationResult]]:
    """Run post-execution validation for a plan."""
    results = []

    # Find reports for this plan
    reports_dir = Path(".vrs/testing/reports")
    if reports_dir.exists():
        for path in reports_dir.glob("*.json"):
            results.extend(validate_report(path))

    # Find transcripts
    transcripts_dir = Path(".vrs/testing/transcripts")
    if transcripts_dir.exists():
        for path in transcripts_dir.glob("*.txt"):
            results.extend(validate_transcript(path))

    # Check if any blocking failures
    blocking_failures = [r for r in results if not r.passed and r.severity == "error"]

    return len(blocking_failures) == 0, results


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Enforce VALIDATION-RULES.md")
    parser.add_argument("--pre-check", metavar="PLAN_ID", help="Run pre-execution checks")
    parser.add_argument("--post-check", metavar="PLAN_ID", help="Run post-execution validation")
    parser.add_argument("--wave-gate", metavar="WAVE", type=int, help="Check wave gate conditions")
    parser.add_argument("--validate-all", action="store_true", help="Validate all reports/transcripts")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all results, not just failures")

    args = parser.parse_args()

    all_results = []
    passed = True

    if args.pre_check:
        print(f"\n=== Pre-Execution Check: {args.pre_check} ===\n")
        passed, results = pre_execution_check(args.pre_check)
        all_results.extend(results)

    if args.post_check:
        print(f"\n=== Post-Execution Validation: {args.post_check} ===\n")
        passed, results = post_execution_check(args.post_check)
        all_results.extend(results)

    if args.wave_gate is not None:
        print(f"\n=== Wave Gate Check: Wave {args.wave_gate} ===\n")
        results = check_wave_gate(args.wave_gate)
        all_results.extend(results)
        blocking = [r for r in results if not r.passed and r.severity == "error"]
        passed = len(blocking) == 0

    if args.validate_all:
        print("\n=== Validating All Reports and Transcripts ===\n")
        passed, results = post_execution_check("all")
        all_results.extend(results)

    # Print results
    failures = [r for r in all_results if not r.passed]
    warnings = [r for r in all_results if not r.passed and r.severity == "warning"]
    errors = [r for r in all_results if not r.passed and r.severity == "error"]

    if args.verbose:
        for r in all_results:
            print(r)
    else:
        for r in failures:
            print(r)

    # Summary
    print(f"\n=== Summary ===")
    print(f"Total checks: {len(all_results)}")
    print(f"Passed: {len(all_results) - len(failures)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Errors: {len(errors)}")

    if errors:
        print("\nBLOCKING: Fix errors before proceeding.")
        sys.exit(1)
    elif warnings:
        print("\nWARNINGS: Review before proceeding.")
        sys.exit(2)
    else:
        print("\nAll checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
