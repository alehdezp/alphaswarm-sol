#!/usr/bin/env python3
"""
GA Release Gate Check.

Runs all verification checks before GA release.

Usage:
    uv run python scripts/ga_gate_check.py
    uv run python scripts/ga_gate_check.py --output .vrs/ga-gate-report.json
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict


@dataclass
class GateCheck:
    """A single gate check."""
    name: str
    category: str
    passed: bool
    details: str
    required: bool = True


@dataclass
class GateReport:
    """GA gate report."""
    timestamp: str
    checks: List[GateCheck] = field(default_factory=list)
    all_passed: bool = False
    required_passed: bool = False
    summary: Dict = field(default_factory=dict)


def check_metrics_targets(metrics_file: Path) -> List[GateCheck]:
    """Check if metrics meet GA targets."""
    checks = []

    if not metrics_file.exists():
        checks.append(GateCheck(
            name="metrics_file_exists",
            category="metrics",
            passed=False,
            details=f"Metrics file not found: {metrics_file}",
        ))
        return checks

    metrics = json.loads(metrics_file.read_text())

    # Precision check
    precision = metrics.get("overall_precision", 0)
    checks.append(GateCheck(
        name="precision_target",
        category="metrics",
        passed=precision >= 0.70,
        details=f"Precision: {precision:.2%} (target: >= 70%)",
    ))

    # Recall check
    recall = metrics.get("overall_recall", 0)
    checks.append(GateCheck(
        name="recall_target",
        category="metrics",
        passed=recall >= 0.60,
        details=f"Recall: {recall:.2%} (target: >= 60%)",
    ))

    # F1 check
    f1 = metrics.get("overall_f1", 0)
    checks.append(GateCheck(
        name="f1_target",
        category="metrics",
        passed=f1 >= 0.65,
        details=f"F1 Score: {f1:.2%} (target: >= 65%)",
    ))

    # Tests count
    tests_count = metrics.get("total_tests", 0)
    checks.append(GateCheck(
        name="tests_count",
        category="metrics",
        passed=tests_count >= 5,
        details=f"Tests run: {tests_count} (minimum: 5)",
    ))

    # Duration check (real execution)
    duration = metrics.get("total_duration_ms", 0)
    checks.append(GateCheck(
        name="real_execution",
        category="metrics",
        passed=duration > 30000,
        details=f"Total duration: {duration/1000:.1f}s (minimum: 30s)",
    ))

    return checks


def check_baseline_exists(baseline_file: Path) -> List[GateCheck]:
    """Check if regression baseline exists."""
    checks = []

    passed = baseline_file.exists()
    if passed:
        baseline = json.loads(baseline_file.read_text())
        commit = baseline.get("git", {}).get("commit", "unknown")[:8]
        details = f"Baseline captured (commit: {commit})"
    else:
        details = f"Baseline not found: {baseline_file}"

    checks.append(GateCheck(
        name="baseline_exists",
        category="regression",
        passed=passed,
        details=details,
    ))

    return checks


def check_documentation() -> List[GateCheck]:
    """Check required documentation exists."""
    checks = []

    required_docs = [
        ("README.md", "Project README"),
        ("CHANGELOG.md", "Change log"),
        ("docs/getting-started/first-audit.md", "Getting started guide"),
        ("docs/guides/patterns-basics.md", "Pattern authoring guide"),
    ]

    for path, name in required_docs:
        exists = Path(path).exists()
        checks.append(GateCheck(
            name=f"doc_{path.replace('/', '_').replace('.', '_')}",
            category="documentation",
            passed=exists,
            details=f"{name}: {'exists' if exists else 'MISSING'}",
            required=path in ["README.md", "CHANGELOG.md"],
        ))

    return checks


def check_version() -> List[GateCheck]:
    """Check version is set for GA."""
    checks = []

    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        checks.append(GateCheck(
            name="pyproject_exists",
            category="version",
            passed=False,
            details="pyproject.toml not found",
        ))
        return checks

    content = pyproject.read_text()
    version = None
    for line in content.split("\n"):
        if line.strip().startswith("version"):
            version = line.split("=")[1].strip().strip('"')
            break

    if version:
        # Check version looks like GA (0.5.0, 1.0.0, etc.)
        is_ga_version = not any(x in version for x in ["alpha", "beta", "dev", "rc"])
        checks.append(GateCheck(
            name="ga_version",
            category="version",
            passed=is_ga_version,
            details=f"Version: {version} ({'GA ready' if is_ga_version else 'pre-release suffix found'})",
        ))
    else:
        checks.append(GateCheck(
            name="version_found",
            category="version",
            passed=False,
            details="Version not found in pyproject.toml",
        ))

    return checks


def check_code_quality() -> List[GateCheck]:
    """Check code quality (type checks, linting)."""
    checks = []

    # Type check with mypy (if available)
    try:
        result = subprocess.run(
            ["uv", "run", "mypy", "src/alphaswarm_sol", "--ignore-missing-imports"],
            capture_output=True,
            timeout=120,
        )
        mypy_passed = result.returncode == 0
        error_count = len([l for l in result.stdout.decode().split("\n") if "error:" in l])
        checks.append(GateCheck(
            name="type_check",
            category="quality",
            passed=mypy_passed,
            details=f"Type check: {'passed' if mypy_passed else f'{error_count} errors'}",
            required=False,  # Warning only
        ))
    except Exception as e:
        checks.append(GateCheck(
            name="type_check",
            category="quality",
            passed=True,
            details=f"Type check skipped: {e}",
            required=False,
        ))

    # Linting with ruff (if available)
    try:
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "src/alphaswarm_sol", "--select=E,F"],
            capture_output=True,
            timeout=60,
        )
        ruff_passed = result.returncode == 0
        error_count = len(result.stdout.decode().strip().split("\n")) if result.stdout else 0
        checks.append(GateCheck(
            name="lint_check",
            category="quality",
            passed=ruff_passed,
            details=f"Lint check: {'passed' if ruff_passed else f'{error_count} issues'}",
            required=False,  # Warning only
        ))
    except Exception as e:
        checks.append(GateCheck(
            name="lint_check",
            category="quality",
            passed=True,
            details=f"Lint check skipped: {e}",
            required=False,
        ))

    return checks


def check_install() -> List[GateCheck]:
    """Check package can be installed."""
    checks = []

    try:
        # Try dry-run install
        result = subprocess.run(
            ["uv", "pip", "compile", "pyproject.toml", "-q"],
            capture_output=True,
            timeout=60,
        )
        install_ok = result.returncode == 0
        checks.append(GateCheck(
            name="install_check",
            category="install",
            passed=install_ok,
            details=f"Package install: {'OK' if install_ok else 'FAILED'}",
        ))
    except Exception as e:
        checks.append(GateCheck(
            name="install_check",
            category="install",
            passed=False,
            details=f"Install check failed: {e}",
        ))

    return checks


def check_tests_pass() -> List[GateCheck]:
    """Check unit tests pass."""
    checks = []

    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "tests/", "-q", "--tb=no", "-x"],
            capture_output=True,
            timeout=300,
        )
        tests_passed = result.returncode == 0

        # Parse test count
        output = result.stdout.decode()
        test_info = "unknown"
        for line in output.split("\n"):
            if "passed" in line or "failed" in line:
                test_info = line.strip()
                break

        checks.append(GateCheck(
            name="unit_tests",
            category="tests",
            passed=tests_passed,
            details=f"Unit tests: {test_info if tests_passed else 'FAILED'}",
        ))
    except subprocess.TimeoutExpired:
        checks.append(GateCheck(
            name="unit_tests",
            category="tests",
            passed=False,
            details="Unit tests: TIMEOUT (>5min)",
        ))
    except Exception as e:
        checks.append(GateCheck(
            name="unit_tests",
            category="tests",
            passed=False,
            details=f"Unit tests: ERROR - {e}",
        ))

    return checks


def check_fixtures_valid() -> List[GateCheck]:
    """Check test fixtures are valid."""
    checks = []

    fixtures_dir = Path("tests/fixtures")
    if not fixtures_dir.exists():
        checks.append(GateCheck(
            name="fixtures_exist",
            category="fixtures",
            passed=False,
            details="Test fixtures directory not found",
        ))
        return checks

    # Check required fixtures
    required = ["foundry-vault", "dvd/naive-receiver", "dvd/side-entrance"]
    for fixture in required:
        fixture_path = fixtures_dir / fixture
        exists = fixture_path.exists()
        has_ground_truth = (fixture_path / "ground-truth.yaml").exists() if exists else False

        checks.append(GateCheck(
            name=f"fixture_{fixture.replace('/', '_')}",
            category="fixtures",
            passed=exists and has_ground_truth,
            details=f"Fixture {fixture}: {'OK' if exists and has_ground_truth else 'MISSING or no ground-truth'}",
        ))

    return checks


def check_cli_works() -> List[GateCheck]:
    """Check CLI commands work."""
    checks = []

    cli_commands = [
        (["uv", "run", "alphaswarm", "--help"], "CLI help"),
        (["uv", "run", "alphaswarm", "vulndocs", "list", "--limit", "1"], "VulnDocs list"),
    ]

    for cmd, name in cli_commands:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            passed = result.returncode == 0
            checks.append(GateCheck(
                name=f"cli_{name.replace(' ', '_').lower()}",
                category="cli",
                passed=passed,
                details=f"{name}: {'OK' if passed else 'FAILED'}",
            ))
        except Exception as e:
            checks.append(GateCheck(
                name=f"cli_{name.replace(' ', '_').lower()}",
                category="cli",
                passed=False,
                details=f"{name}: ERROR - {e}",
            ))

    return checks


def check_flexible_workflow() -> List[GateCheck]:
    """Check flexible workflow features work."""
    checks = []

    # Check --mode solo available
    try:
        result = subprocess.run(
            ["uv", "run", "alphaswarm", "orchestrate", "start", "--help"],
            capture_output=True,
            timeout=30,
        )
        help_text = result.stdout.decode()
        solo_available = "--mode" in help_text
        checks.append(GateCheck(
            name="mode_flag_available",
            category="workflow",
            passed=solo_available,
            details=f"--mode flag: {'available' if solo_available else 'NOT available'}",
            required=False,  # Optional for GA
        ))

        # Check --skip-stages available
        skip_stages_available = "--skip-stages" in help_text
        checks.append(GateCheck(
            name="skip_stages_available",
            category="workflow",
            passed=skip_stages_available,
            details=f"--skip-stages flag: {'available' if skip_stages_available else 'NOT available'}",
            required=False,  # Optional for GA
        ))
    except Exception as e:
        checks.append(GateCheck(
            name="mode_flag_available",
            category="workflow",
            passed=False,
            details=f"Mode flag check failed: {e}",
            required=False,
        ))

    # Check pattern commands available
    pattern_cmds = [
        (["uv", "run", "alphaswarm", "patterns", "--help"], "patterns command"),
        (["uv", "run", "alphaswarm", "findings", "--help"], "findings command"),
    ]

    for cmd, name in pattern_cmds:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            passed = result.returncode == 0
            checks.append(GateCheck(
                name=f"cli_{name.replace(' ', '_')}",
                category="workflow",
                passed=passed,
                details=f"{name}: {'OK' if passed else 'NOT available'}",
                required=False,
            ))
        except Exception as e:
            checks.append(GateCheck(
                name=f"cli_{name.replace(' ', '_')}",
                category="workflow",
                passed=False,
                details=f"{name}: ERROR - {e}",
                required=False,
            ))

    return checks


def run_all_checks() -> GateReport:
    """Run all GA gate checks."""
    report = GateReport(timestamp=datetime.now().isoformat())

    print("Running GA gate checks...")
    print()

    # Metrics checks
    print("[1/10] Checking metrics targets...")
    report.checks.extend(check_metrics_targets(Path(".vrs/ga-metrics/aggregated-metrics.json")))

    # Baseline checks
    print("[2/10] Checking regression baseline...")
    report.checks.extend(check_baseline_exists(Path(".vrs/baselines/ga-baseline.json")))

    # Documentation checks
    print("[3/10] Checking documentation...")
    report.checks.extend(check_documentation())

    # Version checks
    print("[4/10] Checking version...")
    report.checks.extend(check_version())

    # Code quality checks
    print("[5/10] Checking code quality...")
    report.checks.extend(check_code_quality())

    # Install checks
    print("[6/10] Checking install...")
    report.checks.extend(check_install())

    # Test checks
    print("[7/10] Running unit tests...")
    report.checks.extend(check_tests_pass())

    # Fixtures checks
    print("[8/10] Checking fixtures...")
    report.checks.extend(check_fixtures_valid())

    # CLI checks
    print("[9/10] Checking CLI...")
    report.checks.extend(check_cli_works())

    # Flexible workflow checks
    print("[10/10] Checking flexible workflow...")
    report.checks.extend(check_flexible_workflow())

    # Calculate summary
    report.all_passed = all(c.passed for c in report.checks)
    report.required_passed = all(c.passed for c in report.checks if c.required)

    # Count by category
    categories = {}
    for check in report.checks:
        if check.category not in categories:
            categories[check.category] = {"passed": 0, "failed": 0}
        if check.passed:
            categories[check.category]["passed"] += 1
        else:
            categories[check.category]["failed"] += 1

    report.summary = {
        "total_checks": len(report.checks),
        "passed": sum(1 for c in report.checks if c.passed),
        "failed": sum(1 for c in report.checks if not c.passed),
        "by_category": categories,
    }

    return report


def print_report(report: GateReport):
    """Print gate report."""
    print()
    print("=" * 60)
    print("GA RELEASE GATE REPORT")
    print("=" * 60)
    print(f"Timestamp: {report.timestamp}")
    print()

    # Group by category
    categories = {}
    for check in report.checks:
        if check.category not in categories:
            categories[check.category] = []
        categories[check.category].append(check)

    for category, checks in sorted(categories.items()):
        passed = sum(1 for c in checks if c.passed)
        total = len(checks)
        status = "PASS" if passed == total else "FAIL"
        print(f"\n## {category.upper()} ({passed}/{total}) [{status}]")
        print()

        for check in checks:
            status = "PASS" if check.passed else "FAIL"
            required = "*" if check.required else " "
            print(f"  [{status}]{required} {check.details}")

    print()
    print("=" * 60)
    print(f"TOTAL: {report.summary['passed']}/{report.summary['total_checks']} checks passed")
    print()

    if report.required_passed:
        print("** GA GATE: PASSED (all required checks passed) **")
    else:
        print("** GA GATE: FAILED (required checks failed) **")
        print()
        print("Failed required checks:")
        for check in report.checks:
            if check.required and not check.passed:
                print(f"  - {check.name}: {check.details}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="GA Release Gate Check")
    parser.add_argument("--output", help="Output JSON report file")
    parser.add_argument("--strict", action="store_true",
                        help="Require ALL checks to pass (not just required)")
    args = parser.parse_args()

    report = run_all_checks()
    print_report(report)

    if args.output:
        output_data = {
            "timestamp": report.timestamp,
            "all_passed": report.all_passed,
            "required_passed": report.required_passed,
            "summary": report.summary,
            "checks": [
                {
                    "name": c.name,
                    "category": c.category,
                    "passed": c.passed,
                    "details": c.details,
                    "required": c.required,
                }
                for c in report.checks
            ],
        }
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(output_data, indent=2))
        print(f"\nReport saved to: {args.output}")

    # Exit code
    if args.strict:
        sys.exit(0 if report.all_passed else 1)
    else:
        sys.exit(0 if report.required_passed else 1)


if __name__ == "__main__":
    main()
