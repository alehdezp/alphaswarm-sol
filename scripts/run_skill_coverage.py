#!/usr/bin/env python3
"""
Skill Coverage Validation Runner for GA Release Gate.

Executes comprehensive skill validation:
- Schema validation against skill_schema_v2
- Registry validation (integrity, duplicates, file paths)
- Guardrail policy validation for core roles
- Skill unit tests (tests/skills/)

Usage:
    uv run python scripts/run_skill_coverage.py
    uv run python scripts/run_skill_coverage.py --json
    uv run python scripts/run_skill_coverage.py --help

Phase: 07.3-ga-validation
Plan: 04
"""

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CheckResult:
    """Result of a single validation check."""

    name: str
    passed: bool
    exit_code: int
    output: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_ms: int = 0


@dataclass
class SkillCoverageReport:
    """Full skill coverage validation report."""

    timestamp: str
    overall_passed: bool
    checks: List[CheckResult]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "overall_passed": self.overall_passed,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "exit_code": c.exit_code,
                    "output": c.output,
                    "errors": c.errors,
                    "warnings": c.warnings,
                    "duration_ms": c.duration_ms,
                }
                for c in self.checks
            ],
            "summary": self.summary,
        }


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SHIPPING_DIR = PROJECT_ROOT / "src" / "alphaswarm_sol" / "shipping"
SHIPPED_SKILLS_DIR = SHIPPING_DIR / "skills"
REPORTS_DIR = PROJECT_ROOT / ".vrs" / "testing" / "reports"

# Core skills for guardrail validation
CORE_SKILLS_FOR_GUARDRAILS = [
    ("src/alphaswarm_sol/shipping/skills/audit.md", "attacker"),
    ("src/alphaswarm_sol/shipping/skills/investigate.md", "attacker"),
    ("src/alphaswarm_sol/shipping/skills/verify.md", "verifier"),
    ("src/alphaswarm_sol/shipping/skills/debate.md", "attacker"),
    ("src/alphaswarm_sol/shipping/agents/vrs-attacker.md", "attacker"),
    ("src/alphaswarm_sol/shipping/agents/vrs-defender.md", "defender"),
    ("src/alphaswarm_sol/shipping/agents/vrs-verifier.md", "verifier"),
]


def run_command(cmd: List[str], cwd: Path, timeout: int = 120) -> tuple[int, str]:
    """
    Run a command and capture output.

    Args:
        cmd: Command and arguments
        cwd: Working directory
        timeout: Timeout in seconds

    Returns:
        (exit_code, output)
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return 124, f"Command timed out after {timeout}s"
    except Exception as e:
        return 1, f"Command failed: {e}"


def check_skill_schema_validation() -> CheckResult:
    """
    Run skill schema validation against shipped skills.

    Command: python scripts/validate_skill_schema.py src/alphaswarm_sol/shipping/skills --strict
    """
    import time

    start = time.time()

    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "validate_skill_schema.py"),
        str(SHIPPED_SKILLS_DIR),
        "--strict",
    ]

    exit_code, output = run_command(cmd, PROJECT_ROOT)

    duration_ms = int((time.time() - start) * 1000)

    # Parse output for errors/warnings
    errors = []
    warnings = []
    for line in output.splitlines():
        if "ERROR" in line.upper() or line.startswith("  ") and ":" in line and "Validation failed" not in line:
            if "WARNING:" in line:
                warnings.append(line.strip())
            elif line.strip() and not line.startswith("✓") and not line.startswith("✗"):
                errors.append(line.strip())

    passed = exit_code == 0

    return CheckResult(
        name="skill_schema_validation",
        passed=passed,
        exit_code=exit_code,
        output=output,
        errors=errors if not passed else [],
        warnings=warnings,
        duration_ms=duration_ms,
    )


def check_registry_validation() -> CheckResult:
    """
    Run registry validation.

    Command: uv run python -m alphaswarm_sol.skills.registry validate
    """
    import time

    start = time.time()

    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "alphaswarm_sol.skills.registry",
        "validate",
    ]

    exit_code, output = run_command(cmd, PROJECT_ROOT)

    duration_ms = int((time.time() - start) * 1000)

    # Parse output for errors
    errors = []
    for line in output.splitlines():
        if line.strip().startswith("- "):
            errors.append(line.strip()[2:])  # Remove "- " prefix

    passed = exit_code == 0

    return CheckResult(
        name="registry_validation",
        passed=passed,
        exit_code=exit_code,
        output=output,
        errors=errors if not passed else [],
        warnings=[],
        duration_ms=duration_ms,
    )


def check_guardrails_validation() -> CheckResult:
    """
    Run guardrail policy validation for core skills.

    Command: uv run python -m alphaswarm_sol.skills.guardrails <skill> --role <role>
    """
    import time

    start = time.time()

    all_outputs = []
    all_errors = []
    all_warnings = []
    all_passed = True

    for skill_path, role in CORE_SKILLS_FOR_GUARDRAILS:
        full_path = PROJECT_ROOT / skill_path

        # Skip if file doesn't exist (will be caught by registry validation)
        if not full_path.exists():
            all_warnings.append(f"Skill not found: {skill_path}")
            continue

        cmd = [
            "uv",
            "run",
            "python",
            "-m",
            "alphaswarm_sol.skills.guardrails",
            str(full_path),
            "--role",
            role,
        ]

        exit_code, output = run_command(cmd, PROJECT_ROOT, timeout=30)

        all_outputs.append(f"=== {skill_path} ({role}) ===")
        all_outputs.append(output)

        if exit_code != 0:
            all_passed = False
            for line in output.splitlines():
                if line.strip().startswith(""):  # Unicode checkmark for errors
                    all_errors.append(f"[{skill_path}] {line.strip()}")

        # Collect warnings even from passing checks
        for line in output.splitlines():
            if "warning" in line.lower() or "Warning" in line:
                all_warnings.append(f"[{skill_path}] {line.strip()}")

    duration_ms = int((time.time() - start) * 1000)

    return CheckResult(
        name="guardrails_validation",
        passed=all_passed,
        exit_code=0 if all_passed else 1,
        output="\n".join(all_outputs),
        errors=all_errors,
        warnings=all_warnings,
        duration_ms=duration_ms,
    )


def check_skill_tests() -> CheckResult:
    """
    Run skill unit tests.

    Command: uv run pytest tests/skills/ -v
    """
    import time

    start = time.time()

    tests_dir = PROJECT_ROOT / "tests" / "skills"

    # Check if tests directory exists
    if not tests_dir.exists():
        return CheckResult(
            name="skill_tests",
            passed=False,
            exit_code=1,
            output="tests/skills/ directory not found",
            errors=["tests/skills/ directory not found"],
            warnings=[],
            duration_ms=0,
        )

    cmd = [
        "uv",
        "run",
        "pytest",
        str(tests_dir),
        "-v",
        "--tb=short",
    ]

    exit_code, output = run_command(cmd, PROJECT_ROOT, timeout=300)

    duration_ms = int((time.time() - start) * 1000)

    # Parse output for test failures
    errors = []
    for line in output.splitlines():
        if "FAILED" in line:
            errors.append(line.strip())
        elif "ERROR" in line and "test" in line.lower():
            errors.append(line.strip())

    passed = exit_code == 0

    return CheckResult(
        name="skill_tests",
        passed=passed,
        exit_code=exit_code,
        output=output,
        errors=errors if not passed else [],
        warnings=[],
        duration_ms=duration_ms,
    )


def generate_summary(checks: List[CheckResult]) -> Dict[str, Any]:
    """Generate summary statistics from check results."""
    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    failed = total - passed

    return {
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "N/A",
        "total_errors": sum(len(c.errors) for c in checks),
        "total_warnings": sum(len(c.warnings) for c in checks),
        "total_duration_ms": sum(c.duration_ms for c in checks),
        "check_details": {
            c.name: {"passed": c.passed, "errors": len(c.errors), "warnings": len(c.warnings)}
            for c in checks
        },
    }


def run_skill_coverage() -> SkillCoverageReport:
    """Run all skill coverage checks and generate report."""
    timestamp = datetime.utcnow().isoformat() + "Z"

    checks = []

    # Run all checks
    print("Running skill schema validation...")
    checks.append(check_skill_schema_validation())
    print(f"  {'PASS' if checks[-1].passed else 'FAIL'}")

    print("Running registry validation...")
    checks.append(check_registry_validation())
    print(f"  {'PASS' if checks[-1].passed else 'FAIL'}")

    print("Running guardrails validation...")
    checks.append(check_guardrails_validation())
    print(f"  {'PASS' if checks[-1].passed else 'FAIL'}")

    print("Running skill tests...")
    checks.append(check_skill_tests())
    print(f"  {'PASS' if checks[-1].passed else 'FAIL'}")

    # Generate summary
    summary = generate_summary(checks)

    # Determine overall pass/fail
    overall_passed = all(c.passed for c in checks)

    return SkillCoverageReport(
        timestamp=timestamp,
        overall_passed=overall_passed,
        checks=checks,
        summary=summary,
    )


def save_report(report: SkillCoverageReport, output_path: Optional[Path] = None) -> Path:
    """Save report to JSON file."""
    if output_path is None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = REPORTS_DIR / "skill-coverage.json"

    with open(output_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    return output_path


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run skill coverage validation for GA release gate"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output report as JSON to stdout (in addition to saving file)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for JSON report (default: .vrs/testing/reports/skill-coverage.json)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save report to file (only print to stdout)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Skill Coverage Validation Runner")
    print("=" * 60)
    print()

    report = run_skill_coverage()

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Overall: {'PASS' if report.overall_passed else 'FAIL'}")
    print(f"Checks: {report.summary['passed']}/{report.summary['total_checks']} passed")
    print(f"Total errors: {report.summary['total_errors']}")
    print(f"Total warnings: {report.summary['total_warnings']}")
    print(f"Duration: {report.summary['total_duration_ms']}ms")
    print()

    # Print failed checks with errors
    for check in report.checks:
        if not check.passed:
            print(f"FAILED: {check.name}")
            for error in check.errors[:5]:  # Limit to first 5 errors
                print(f"  - {error}")
            if len(check.errors) > 5:
                print(f"  ... and {len(check.errors) - 5} more errors")
            print()

    # Save report
    if not args.no_save:
        output_path = save_report(report, args.output)
        print(f"Report saved to: {output_path}")

    # JSON output
    if args.json:
        print()
        print("JSON Report:")
        print(json.dumps(report.to_dict(), indent=2))

    # Exit code
    sys.exit(0 if report.overall_passed else 1)


if __name__ == "__main__":
    main()
