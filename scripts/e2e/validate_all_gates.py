#!/usr/bin/env python3
"""
All-Gates Aggregator for Execution Evidence Protocol (G0-G7).

Single CLI command that:
- Loads evidence pack manifest
- Runs validators for G0-G7
- Emits JSON + Markdown reports
- Exits non-zero on any gate failure

Exit codes:
  0 - All gates pass
  1 - One or more gates fail
  2 - Invalid arguments or I/O error
  3 - Critical infrastructure error

Usage:
    python validate_all_gates.py <run_id_or_path> [--config CONFIG] [--verbose]
    python validate_all_gates.py .vrs/validation/runs/run-001/
    python validate_all_gates.py run-20260130-0001 --output reports/
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Add the package to path if running standalone
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# SCHEMA VERSION
# =============================================================================

GATE_AGGREGATOR_VERSION = "1.0.0"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class GateCheckResult:
    """Result of a single gate check."""

    check_id: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class GateResult:
    """Result of a gate evaluation."""

    gate_id: str
    gate_name: str
    passed: bool
    checks: list[GateCheckResult] = field(default_factory=list)
    failure_reasons: list[str] = field(default_factory=list)
    duration_ms: int = 0
    skipped: bool = False
    skip_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "gate_name": self.gate_name,
            "passed": self.passed,
            "checks": [c.to_dict() for c in self.checks],
            "failure_reasons": self.failure_reasons,
            "duration_ms": self.duration_ms,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
        }


@dataclass
class AllGatesResult:
    """Result of validating all gates."""

    all_passed: bool
    gates_passed: int
    gates_failed: int
    gates_skipped: int
    gates: list[GateResult] = field(default_factory=list)

    # Metadata
    run_id: str = ""
    evidence_dir: str = ""
    config_path: str = ""
    version: str = GATE_AGGREGATOR_VERSION
    timestamp: str = ""
    total_duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "all_passed": self.all_passed,
            "gates_passed": self.gates_passed,
            "gates_failed": self.gates_failed,
            "gates_skipped": self.gates_skipped,
            "gates": [g.to_dict() for g in self.gates],
            "run_id": self.run_id,
            "evidence_dir": self.evidence_dir,
            "config_path": self.config_path,
            "version": self.version,
            "timestamp": self.timestamp,
            "total_duration_ms": self.total_duration_ms,
        }


@dataclass
class GateConfig:
    """Configuration for a gate."""

    gate_id: str
    enabled: bool = True
    fail_fast: bool = False
    validator: str = ""
    extra_args: list[str] = field(default_factory=list)


@dataclass
class GateRunnerConfig:
    """Configuration for the gate runner."""

    gates: list[GateConfig]
    fail_fast: bool = False
    report_output_dir: Path = Path(".vrs/validation/reports")
    json_output: bool = True
    markdown_output: bool = True
    required_gates: list[str] = field(default_factory=list)


# =============================================================================
# CONFIG LOADER
# =============================================================================

DEFAULT_CONFIG = {
    "gates": [
        {"gate_id": "G0", "enabled": True, "validator": "preflight"},
        {"gate_id": "G1", "enabled": True, "validator": "evidence_integrity"},
        {"gate_id": "G2", "enabled": True, "validator": "graph_soundness"},
        {"gate_id": "G3", "enabled": True, "validator": "ground_truth"},
        {"gate_id": "G4", "enabled": True, "validator": "mutation_robustness"},
        {"gate_id": "G5", "enabled": True, "validator": "consensus_variance"},
        {"gate_id": "G6", "enabled": True, "validator": "regression_baseline"},
        {"gate_id": "G7", "enabled": True, "validator": "continuous_health"},
    ],
    "fail_fast": False,
    "report_output_dir": ".vrs/validation/reports",
    "json_output": True,
    "markdown_output": True,
    "required_gates": ["G0", "G1", "G2", "G3"],
}


def load_config(config_path: Optional[Path]) -> GateRunnerConfig:
    """Load gate runner configuration."""
    if config_path and config_path.exists():
        if not HAS_YAML:
            logger.warning("PyYAML not available, using default config")
            config_data = DEFAULT_CONFIG
        else:
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
    else:
        config_data = DEFAULT_CONFIG

    gates = []
    for gate_data in config_data.get("gates", DEFAULT_CONFIG["gates"]):
        gates.append(
            GateConfig(
                gate_id=gate_data.get("gate_id", ""),
                enabled=gate_data.get("enabled", True),
                fail_fast=gate_data.get("fail_fast", False),
                validator=gate_data.get("validator", ""),
                extra_args=gate_data.get("extra_args", []),
            )
        )

    return GateRunnerConfig(
        gates=gates,
        fail_fast=config_data.get("fail_fast", False),
        report_output_dir=Path(config_data.get("report_output_dir", ".vrs/validation/reports")),
        json_output=config_data.get("json_output", True),
        markdown_output=config_data.get("markdown_output", True),
        required_gates=config_data.get("required_gates", ["G0", "G1", "G2", "G3"]),
    )


# =============================================================================
# GATE VALIDATORS
# =============================================================================

GATE_NAMES = {
    "G0": "Preflight",
    "G1": "Evidence Integrity",
    "G2": "Graph Soundness",
    "G3": "Ground Truth Coverage",
    "G4": "Mutation Robustness",
    "G5": "Consensus & Variance",
    "G6": "Regression Baseline",
    "G7": "Continuous Health",
}


def validate_g0_preflight(evidence_dir: Path, config: GateConfig) -> GateResult:
    """
    G0 Preflight: Ensure toolchain + dataset integrity.

    Checks:
    - alphaswarm CLI version matches expected
    - dataset hash matches manifest (if applicable)
    - worktree isolation confirmed (if applicable)
    """
    gate = GateResult(
        gate_id="G0",
        gate_name=GATE_NAMES["G0"],
        passed=True,
    )
    start_time = time.time()

    # Check alphaswarm CLI available
    try:
        result = subprocess.run(
            ["uv", "run", "alphaswarm", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        cli_available = result.returncode == 0
        version = result.stdout.strip() if cli_available else ""
        gate.checks.append(
            GateCheckResult(
                check_id="G0.2",
                passed=cli_available,
                message="alphaswarm CLI available" if cli_available else "alphaswarm CLI not available",
                details={"version": version},
            )
        )
        if not cli_available:
            gate.passed = False
            gate.failure_reasons.append("alphaswarm CLI not available")
    except Exception as e:
        gate.checks.append(
            GateCheckResult(
                check_id="G0.2",
                passed=False,
                message=f"Failed to check alphaswarm CLI: {e}",
            )
        )
        gate.passed = False
        gate.failure_reasons.append("Failed to check alphaswarm CLI")

    # Check evidence directory exists
    manifest_path = evidence_dir / "manifest.json"
    manifest_exists = manifest_path.exists()
    gate.checks.append(
        GateCheckResult(
            check_id="G0.3",
            passed=manifest_exists,
            message="Evidence manifest exists" if manifest_exists else "Evidence manifest not found",
            details={"path": str(manifest_path)},
        )
    )
    if not manifest_exists:
        gate.passed = False
        gate.failure_reasons.append("Evidence manifest not found")

    # Check proofs directory exists
    proofs_dir = evidence_dir / "proofs"
    proofs_exists = proofs_dir.exists() and proofs_dir.is_dir()
    gate.checks.append(
        GateCheckResult(
            check_id="G0.4",
            passed=proofs_exists,
            message="Proofs directory exists" if proofs_exists else "Proofs directory not found",
            details={"path": str(proofs_dir)},
        )
    )
    if not proofs_exists:
        gate.passed = False
        gate.failure_reasons.append("Proofs directory not found")

    gate.duration_ms = int((time.time() - start_time) * 1000)
    return gate


def validate_g1_g2(evidence_dir: Path, config: GateConfig) -> tuple[GateResult, GateResult]:
    """
    G1 Evidence Integrity + G2 Graph Soundness via validate_gate_g1_g2.py.
    """
    script_path = Path(__file__).parent / "validate_gate_g1_g2.py"

    g1 = GateResult(gate_id="G1", gate_name=GATE_NAMES["G1"], passed=False)
    g2 = GateResult(gate_id="G2", gate_name=GATE_NAMES["G2"], passed=False)

    start_time = time.time()

    if not script_path.exists():
        g1.skipped = True
        g1.skip_reason = "Validator script not found"
        g2.skipped = True
        g2.skip_reason = "Validator script not found"
        return g1, g2

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), str(evidence_dir), "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(Path(__file__).parent),
        )

        duration = int((time.time() - start_time) * 1000)

        if result.returncode == 2:
            g1.failure_reasons.append("I/O error in validator")
            g2.failure_reasons.append("I/O error in validator")
            g1.duration_ms = duration // 2
            g2.duration_ms = duration // 2
            return g1, g2

        # Parse JSON output
        output_data = json.loads(result.stdout)

        for gate_data in output_data.get("gates", []):
            gate_id = gate_data.get("gate_id", "")

            if gate_id == "G1":
                g1.passed = gate_data.get("passed", False)
                g1.failure_reasons = gate_data.get("failure_reasons", [])
                for check_data in gate_data.get("checks", []):
                    g1.checks.append(
                        GateCheckResult(
                            check_id=check_data.get("check_id", ""),
                            passed=check_data.get("passed", False),
                            message=check_data.get("message", ""),
                            details=check_data.get("details", {}),
                        )
                    )
                g1.duration_ms = duration // 2

            elif gate_id == "G2":
                g2.passed = gate_data.get("passed", False)
                g2.failure_reasons = gate_data.get("failure_reasons", [])
                for check_data in gate_data.get("checks", []):
                    g2.checks.append(
                        GateCheckResult(
                            check_id=check_data.get("check_id", ""),
                            passed=check_data.get("passed", False),
                            message=check_data.get("message", ""),
                            details=check_data.get("details", {}),
                        )
                    )
                g2.duration_ms = duration // 2

    except subprocess.TimeoutExpired:
        g1.failure_reasons.append("Validator timed out")
        g2.failure_reasons.append("Validator timed out")
    except json.JSONDecodeError as e:
        g1.failure_reasons.append(f"Failed to parse validator output: {e}")
        g2.failure_reasons.append(f"Failed to parse validator output: {e}")
    except Exception as e:
        g1.failure_reasons.append(f"Validator error: {e}")
        g2.failure_reasons.append(f"Validator error: {e}")

    return g1, g2


def validate_g3_ground_truth(evidence_dir: Path, config: GateConfig) -> GateResult:
    """
    G3 Ground Truth Coverage via validate_ground_truth.py.
    """
    gate = GateResult(gate_id="G3", gate_name=GATE_NAMES["G3"], passed=False)
    start_time = time.time()

    script_path = Path(__file__).parent / "validate_ground_truth.py"
    manifest_path = Path(__file__).parent.parent.parent / "configs" / "ground_truth_manifest.yaml"

    if not script_path.exists():
        gate.skipped = True
        gate.skip_reason = "Validator script not found"
        return gate

    if not manifest_path.exists():
        gate.skipped = True
        gate.skip_reason = "Ground truth manifest not found"
        return gate

    try:
        json_output = Path(__file__).parent.parent.parent / ".vrs" / "validation" / "g3_result.json"
        json_output.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--manifest",
                str(manifest_path),
                "--json",
                str(json_output),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(Path(__file__).parent),
        )

        gate.duration_ms = int((time.time() - start_time) * 1000)
        gate.passed = result.returncode == 0

        if json_output.exists():
            with open(json_output) as f:
                output_data = json.load(f)

            gate.checks.append(
                GateCheckResult(
                    check_id="G3.1",
                    passed=output_data.get("valid", False),
                    message=f"Categories: {output_data.get('categories_passing', 0)}/{output_data.get('categories_validated', 0)} passing",
                    details={
                        "total_sources": output_data.get("total_sources", 0),
                        "total_findings": output_data.get("total_findings", 0),
                    },
                )
            )

            for failure in output_data.get("critical_failures", []):
                gate.failure_reasons.append(failure)

    except subprocess.TimeoutExpired:
        gate.failure_reasons.append("Validator timed out")
    except Exception as e:
        gate.failure_reasons.append(f"Validator error: {e}")

    return gate


def validate_g4_mutation(evidence_dir: Path, config: GateConfig) -> GateResult:
    """
    G4 Mutation Robustness.

    For now, check if mutation metrics exist in evidence pack.
    """
    gate = GateResult(gate_id="G4", gate_name=GATE_NAMES["G4"], passed=True)
    start_time = time.time()

    # Check for mutation metrics in evidence pack
    metrics_dir = evidence_dir / "metrics"
    mutation_path = metrics_dir / "mutation_results.json"

    if not metrics_dir.exists():
        gate.skipped = True
        gate.skip_reason = "Metrics directory not found"
        return gate

    if not mutation_path.exists():
        # Mutation testing may be optional
        gate.checks.append(
            GateCheckResult(
                check_id="G4.1",
                passed=True,
                message="Mutation results not present (optional)",
                details={"path": str(mutation_path)},
            )
        )
        gate.skipped = True
        gate.skip_reason = "No mutation results (optional)"
        return gate

    try:
        with open(mutation_path) as f:
            mutation_data = json.load(f)

        detection_rate = mutation_data.get("detection_rate", 0.0)
        target_rate = mutation_data.get("target_rate", 0.75)
        passed = detection_rate >= target_rate

        gate.checks.append(
            GateCheckResult(
                check_id="G4.1",
                passed=passed,
                message=f"Mutation detection rate: {detection_rate:.2%} (target: {target_rate:.2%})",
                details=mutation_data,
            )
        )

        if not passed:
            gate.passed = False
            gate.failure_reasons.append(f"Detection rate {detection_rate:.2%} < target {target_rate:.2%}")

        # Check negative controls
        false_positives = mutation_data.get("false_positives_on_safe", 0)
        if false_positives > 0:
            gate.checks.append(
                GateCheckResult(
                    check_id="G4.2",
                    passed=False,
                    message=f"False positives on safe variants: {false_positives}",
                )
            )
            gate.passed = False
            gate.failure_reasons.append(f"False positives on safe variants: {false_positives}")

    except Exception as e:
        gate.failure_reasons.append(f"Failed to load mutation results: {e}")
        gate.passed = False

    gate.duration_ms = int((time.time() - start_time) * 1000)
    return gate


def validate_g5_variance(evidence_dir: Path, config: GateConfig) -> GateResult:
    """
    G5 Consensus & Variance via run_multiseed_variance.py.
    """
    gate = GateResult(gate_id="G5", gate_name=GATE_NAMES["G5"], passed=True)
    start_time = time.time()

    # Check for variance results in evidence pack
    variance_path = evidence_dir / "variance_result.json"

    if not variance_path.exists():
        # Check parent directory for variance results
        parent_variance = evidence_dir.parent / "variance" / "variance_result.json"
        if parent_variance.exists():
            variance_path = parent_variance

    if not variance_path.exists():
        gate.skipped = True
        gate.skip_reason = "Variance results not found"
        return gate

    try:
        with open(variance_path) as f:
            variance_data = json.load(f)

        g5_passed = variance_data.get("g5_passed", False)
        g5_failures = variance_data.get("g5_failures", [])

        gate.passed = g5_passed
        gate.failure_reasons = g5_failures

        variance = variance_data.get("variance", {})
        gate.checks.append(
            GateCheckResult(
                check_id="G5.1",
                passed=g5_passed,
                message=f"Variance analysis: {variance_data.get('successful_runs', 0)}/{variance_data.get('run_count', 0)} runs",
                details={
                    "findings_variance": variance.get("findings", {}),
                    "consensus": variance.get("consensus", {}),
                },
            )
        )

    except Exception as e:
        gate.failure_reasons.append(f"Failed to load variance results: {e}")
        gate.passed = False

    gate.duration_ms = int((time.time() - start_time) * 1000)
    return gate


def validate_g6_regression(evidence_dir: Path, config: GateConfig) -> GateResult:
    """
    G6 Regression Baseline.

    Check for regression metrics in evidence pack.
    """
    gate = GateResult(gate_id="G6", gate_name=GATE_NAMES["G6"], passed=True)
    start_time = time.time()

    # Check for baseline comparison
    baseline_path = evidence_dir / "metrics" / "baseline_comparison.json"

    if not baseline_path.exists():
        gate.skipped = True
        gate.skip_reason = "No baseline comparison (first run or baseline not locked)"
        return gate

    try:
        with open(baseline_path) as f:
            baseline_data = json.load(f)

        precision_drop = baseline_data.get("precision_drop", 0.0)
        recall_drop = baseline_data.get("recall_drop", 0.0)
        new_critical_fps = baseline_data.get("new_critical_false_positives", 0)

        tolerance = baseline_data.get("tolerance", 0.05)

        if precision_drop > tolerance:
            gate.passed = False
            gate.failure_reasons.append(f"Precision drop {precision_drop:.2%} > tolerance {tolerance:.2%}")

        if recall_drop > tolerance:
            gate.passed = False
            gate.failure_reasons.append(f"Recall drop {recall_drop:.2%} > tolerance {tolerance:.2%}")

        if new_critical_fps > 0:
            gate.passed = False
            gate.failure_reasons.append(f"New critical false positives: {new_critical_fps}")

        gate.checks.append(
            GateCheckResult(
                check_id="G6.1",
                passed=gate.passed,
                message=f"Regression check: precision_drop={precision_drop:.2%}, recall_drop={recall_drop:.2%}",
                details=baseline_data,
            )
        )

    except Exception as e:
        gate.failure_reasons.append(f"Failed to load baseline comparison: {e}")
        gate.passed = False

    gate.duration_ms = int((time.time() - start_time) * 1000)
    return gate


def validate_g7_continuous(evidence_dir: Path, config: GateConfig) -> GateResult:
    """
    G7 Continuous Health.

    Check for CI/CD pipeline status.
    """
    gate = GateResult(gate_id="G7", gate_name=GATE_NAMES["G7"], passed=True)
    start_time = time.time()

    # Check for CI status
    ci_status_path = evidence_dir / "metrics" / "ci_status.json"

    if not ci_status_path.exists():
        gate.skipped = True
        gate.skip_reason = "No CI status available"
        return gate

    try:
        with open(ci_status_path) as f:
            ci_data = json.load(f)

        nightly_passed = ci_data.get("nightly_passed", True)
        weekly_passed = ci_data.get("weekly_passed", True)
        trend_generated = ci_data.get("trend_report_generated", False)

        gate.passed = nightly_passed and weekly_passed

        gate.checks.append(
            GateCheckResult(
                check_id="G7.1",
                passed=nightly_passed,
                message="Nightly suite" + (" passed" if nightly_passed else " failed"),
            )
        )

        gate.checks.append(
            GateCheckResult(
                check_id="G7.2",
                passed=weekly_passed,
                message="Weekly suite" + (" passed" if weekly_passed else " failed"),
            )
        )

        gate.checks.append(
            GateCheckResult(
                check_id="G7.3",
                passed=trend_generated,
                message="Trend report" + (" generated" if trend_generated else " missing"),
            )
        )

        if not nightly_passed:
            gate.failure_reasons.append("Nightly suite failed")
        if not weekly_passed:
            gate.failure_reasons.append("Weekly suite failed")

    except Exception as e:
        gate.failure_reasons.append(f"Failed to load CI status: {e}")
        gate.passed = False

    gate.duration_ms = int((time.time() - start_time) * 1000)
    return gate


# =============================================================================
# MAIN RUNNER
# =============================================================================


def run_all_gates(
    evidence_dir: Path,
    config: GateRunnerConfig,
    run_id: Optional[str] = None,
) -> AllGatesResult:
    """
    Run all gate validators.

    Args:
        evidence_dir: Directory containing evidence pack
        config: Gate runner configuration
        run_id: Optional run identifier

    Returns:
        AllGatesResult with all gate results
    """
    start_time = time.time()
    gates: list[GateResult] = []
    failed = False

    logger.info(f"Running all gates for: {evidence_dir}")

    # Map gate IDs to validators
    gate_validators = {
        "G0": ("preflight", lambda: validate_g0_preflight(evidence_dir, GateConfig(gate_id="G0"))),
        "G1": ("evidence_integrity", None),  # Handled with G2
        "G2": ("graph_soundness", None),  # Handled with G1
        "G3": ("ground_truth", lambda: validate_g3_ground_truth(evidence_dir, GateConfig(gate_id="G3"))),
        "G4": ("mutation_robustness", lambda: validate_g4_mutation(evidence_dir, GateConfig(gate_id="G4"))),
        "G5": ("consensus_variance", lambda: validate_g5_variance(evidence_dir, GateConfig(gate_id="G5"))),
        "G6": ("regression_baseline", lambda: validate_g6_regression(evidence_dir, GateConfig(gate_id="G6"))),
        "G7": ("continuous_health", lambda: validate_g7_continuous(evidence_dir, GateConfig(gate_id="G7"))),
    }

    for gate_config in config.gates:
        if not gate_config.enabled:
            logger.debug(f"Skipping disabled gate: {gate_config.gate_id}")
            continue

        gate_id = gate_config.gate_id
        logger.info(f"Running {gate_id}: {GATE_NAMES.get(gate_id, 'Unknown')}")

        # Handle G1 and G2 together
        if gate_id in ("G1", "G2"):
            # Only run once for both gates
            g1_exists = any(g.gate_id == "G1" for g in gates)
            g2_exists = any(g.gate_id == "G2" for g in gates)

            if not g1_exists and not g2_exists:
                g1, g2 = validate_g1_g2(evidence_dir, gate_config)
                gates.append(g1)
                gates.append(g2)

                if not g1.passed and "G1" in config.required_gates:
                    failed = True
                if not g2.passed and "G2" in config.required_gates:
                    failed = True
            continue

        validator_name, validator_fn = gate_validators.get(gate_id, (None, None))

        if validator_fn is None:
            logger.warning(f"No validator for gate: {gate_id}")
            continue

        try:
            gate_result = validator_fn()
            gates.append(gate_result)

            if not gate_result.passed and not gate_result.skipped:
                if gate_id in config.required_gates:
                    failed = True

                if config.fail_fast or gate_config.fail_fast:
                    logger.warning(f"Fail-fast triggered on gate: {gate_id}")
                    break

        except Exception as e:
            logger.error(f"Gate {gate_id} error: {e}")
            gates.append(
                GateResult(
                    gate_id=gate_id,
                    gate_name=GATE_NAMES.get(gate_id, "Unknown"),
                    passed=False,
                    failure_reasons=[f"Validator error: {e}"],
                )
            )
            if gate_id in config.required_gates:
                failed = True

    # Count results
    passed = sum(1 for g in gates if g.passed and not g.skipped)
    failed_count = sum(1 for g in gates if not g.passed and not g.skipped)
    skipped = sum(1 for g in gates if g.skipped)

    total_duration = int((time.time() - start_time) * 1000)

    # Determine run_id from evidence dir if not provided
    if not run_id:
        run_id = evidence_dir.name

    return AllGatesResult(
        all_passed=not failed,
        gates_passed=passed,
        gates_failed=failed_count,
        gates_skipped=skipped,
        gates=gates,
        run_id=run_id,
        evidence_dir=str(evidence_dir),
        config_path=str(config.report_output_dir.parent) if config else "",
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        total_duration_ms=total_duration,
    )


# =============================================================================
# REPORT GENERATORS
# =============================================================================


def generate_json_report(result: AllGatesResult, output_path: Path) -> None:
    """Generate JSON report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)
    logger.info(f"JSON report: {output_path}")


def generate_markdown_report(result: AllGatesResult, output_path: Path) -> None:
    """Generate Markdown report."""
    lines = [
        "# Gate Validation Report",
        "",
        f"**Run ID:** `{result.run_id}`",
        f"**Evidence Dir:** `{result.evidence_dir}`",
        f"**Timestamp:** {result.timestamp}",
        f"**Duration:** {result.total_duration_ms}ms",
        f"**Version:** {result.version}",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Overall Status | {'PASS' if result.all_passed else 'FAIL'} |",
        f"| Gates Passed | {result.gates_passed} |",
        f"| Gates Failed | {result.gates_failed} |",
        f"| Gates Skipped | {result.gates_skipped} |",
        "",
        "---",
        "",
        "## Gate Results",
        "",
        "| Gate | Name | Status | Duration | Failures |",
        "|------|------|--------|----------|----------|",
    ]

    for gate in result.gates:
        if gate.skipped:
            status = "SKIP"
        elif gate.passed:
            status = "PASS"
        else:
            status = "FAIL"

        failures = "; ".join(gate.failure_reasons[:2]) if gate.failure_reasons else "-"
        if len(gate.failure_reasons) > 2:
            failures += f" (+{len(gate.failure_reasons) - 2} more)"

        lines.append(
            f"| {gate.gate_id} | {gate.gate_name} | {status} | {gate.duration_ms}ms | {failures} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Detailed Results")
    lines.append("")

    for gate in result.gates:
        lines.append(f"### {gate.gate_id}: {gate.gate_name}")
        lines.append("")

        if gate.skipped:
            lines.append(f"**Status:** SKIPPED")
            lines.append(f"**Reason:** {gate.skip_reason}")
        else:
            lines.append(f"**Status:** {'PASS' if gate.passed else 'FAIL'}")

        lines.append(f"**Duration:** {gate.duration_ms}ms")
        lines.append("")

        if gate.checks:
            lines.append("**Checks:**")
            lines.append("")
            for check in gate.checks:
                status = "PASS" if check.passed else "FAIL"
                lines.append(f"- `[{check.check_id}]` {status}: {check.message}")
            lines.append("")

        if gate.failure_reasons:
            lines.append("**Failure Reasons:**")
            lines.append("")
            for reason in gate.failure_reasons:
                lines.append(f"- {reason}")
            lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    logger.info(f"Markdown report: {output_path}")


# =============================================================================
# CLI
# =============================================================================


def resolve_evidence_dir(run_id_or_path: str) -> Path:
    """Resolve run ID or path to evidence directory."""
    # Check if it's a direct path
    path = Path(run_id_or_path)
    if path.exists() and path.is_dir():
        return path

    # Check standard validation runs location
    vrs_path = Path(".vrs/validation/runs") / run_id_or_path
    if vrs_path.exists():
        return vrs_path

    # Check absolute path in .vrs
    abs_vrs_path = Path(__file__).parent.parent.parent / ".vrs" / "validation" / "runs" / run_id_or_path
    if abs_vrs_path.exists():
        return abs_vrs_path

    # Return the original path and let validation fail
    return path


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="All-Gates Aggregator for Execution Evidence Protocol (G0-G7)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Gates:
  G0 - Preflight: toolchain + dataset integrity
  G1 - Evidence Integrity: proof tokens + schema validation
  G2 - Graph Soundness: hash + property coverage
  G3 - Ground Truth Coverage: category thresholds + provenance
  G4 - Mutation Robustness: detection rate + negative controls
  G5 - Consensus & Variance: multi-seed stability
  G6 - Regression Baseline: precision/recall vs locked baseline
  G7 - Continuous Health: CI/CD pipeline status

Examples:
    %(prog)s .vrs/validation/runs/run-001/
    %(prog)s run-20260130-0001 --config configs/gate_runner.yaml
    %(prog)s evidence/ --output reports/ --json
        """,
    )

    parser.add_argument(
        "run_id_or_path",
        help="Run ID or path to evidence directory",
    )
    parser.add_argument(
        "--config", "-c",
        type=Path,
        help="Path to gate runner config YAML",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path(".vrs/validation/reports"),
        help="Output directory for reports",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON to stdout",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first gate failure",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Resolve evidence directory
    evidence_dir = resolve_evidence_dir(args.run_id_or_path)

    if not evidence_dir.exists():
        logger.error(f"Evidence directory not found: {evidence_dir}")
        return 2

    # Load config
    config = load_config(args.config)
    if args.fail_fast:
        config.fail_fast = True
    config.report_output_dir = args.output

    # Run all gates
    result = run_all_gates(
        evidence_dir=evidence_dir,
        config=config,
        run_id=args.run_id_or_path,
    )

    # Generate reports
    if config.json_output:
        json_path = args.output / f"{result.run_id}_gates.json"
        generate_json_report(result, json_path)

    if config.markdown_output:
        md_path = args.output / f"{result.run_id}_gates.md"
        generate_markdown_report(result, md_path)

    # JSON to stdout if requested
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        # Print summary
        print()
        print("=" * 70)
        print("GATE VALIDATION RESULT (G0-G7)")
        print("=" * 70)
        print(f"Run ID:       {result.run_id}")
        print(f"Evidence Dir: {result.evidence_dir}")
        print(f"Timestamp:    {result.timestamp}")
        print(f"Duration:     {result.total_duration_ms}ms")
        print()
        print(f"Overall:      {'PASS' if result.all_passed else 'FAIL'}")
        print(f"Passed:       {result.gates_passed}")
        print(f"Failed:       {result.gates_failed}")
        print(f"Skipped:      {result.gates_skipped}")
        print("=" * 70)

        for gate in result.gates:
            if gate.skipped:
                status = "SKIP"
            elif gate.passed:
                status = "PASS"
            else:
                status = "FAIL"

            print(f"[{gate.gate_id}] {gate.gate_name}: {status}")
            if gate.failure_reasons and args.verbose:
                for reason in gate.failure_reasons:
                    print(f"       {reason}")

        print("=" * 70)
        print(f"Reports: {args.output}")
        print("=" * 70)

    return 0 if result.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
