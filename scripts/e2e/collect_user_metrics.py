#!/usr/bin/env python3
"""
User Journey Metrics Collector.

Collects UX metrics from evidence packs and generates a pass/fail report
based on the thresholds defined in configs/user_journey_metrics.yaml.

Usage:
    # Collect metrics from an evidence pack
    python scripts/e2e/collect_user_metrics.py \\
        --evidence-pack .vrs/validation/runs/run-001 \\
        --output reports/user_journey_metrics.md

    # Collect from multiple runs and aggregate
    python scripts/e2e/collect_user_metrics.py \\
        --evidence-packs .vrs/validation/runs/run-* \\
        --output reports/user_journey_metrics.md \\
        --aggregate

    # Check against gates only
    python scripts/e2e/collect_user_metrics.py \\
        --evidence-pack .vrs/validation/runs/run-001 \\
        --gates-only

    # Output JSON instead of markdown
    python scripts/e2e/collect_user_metrics.py \\
        --evidence-pack .vrs/validation/runs/run-001 \\
        --format json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import yaml

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "configs" / "user_journey_metrics.yaml"
DEFAULT_OUTPUT_PATH = Path(__file__).parent.parent.parent / "reports" / "user_journey_metrics.md"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class MetricResult:
    """Result for a single metric measurement."""
    metric_id: str
    name: str
    value: Union[int, float, bool, None]
    unit: str
    threshold_level: str  # "excellent", "acceptable", "concerning", "critical", "unknown"
    passed: bool
    threshold_value: Optional[Union[int, float, bool]] = None
    persona: Optional[str] = None
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "threshold_level": self.threshold_level,
            "passed": self.passed,
            "threshold_value": self.threshold_value,
            "persona": self.persona,
            "details": self.details,
        }


@dataclass
class GateResult:
    """Result for a quality gate evaluation."""
    gate_id: str
    name: str
    description: str
    passed: bool
    criteria_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "gate_id": self.gate_id,
            "name": self.name,
            "description": self.description,
            "passed": self.passed,
            "criteria_results": self.criteria_results,
        }


@dataclass
class MetricsReport:
    """Complete metrics report."""
    run_id: str
    persona: Optional[str]
    timestamp: str
    metrics: list[MetricResult]
    gates: list[GateResult]
    overall_passed: bool
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "persona": self.persona,
            "timestamp": self.timestamp,
            "metrics": [m.to_dict() for m in self.metrics],
            "gates": [g.to_dict() for g in self.gates],
            "overall_passed": self.overall_passed,
            "summary": self.summary,
        }


# ============================================================================
# Metric Extraction
# ============================================================================

def extract_metric_value(
    evidence: dict[str, Any],
    metric_config: dict[str, Any],
    transcript_content: Optional[str] = None,
) -> Union[int, float, bool, None]:
    """
    Extract a metric value from evidence pack data.

    Args:
        evidence: Evidence pack manifest data
        metric_config: Metric configuration from YAML
        transcript_content: Optional transcript content for pattern matching

    Returns:
        Extracted metric value or None if not found
    """
    source = metric_config.get("source", {})

    # Direct evidence pack field
    if "evidence_pack_field" in source:
        field_path = source["evidence_pack_field"]
        value = get_nested_value(evidence, field_path)

        # Apply calculation if specified
        if value is not None and "calculation" in source:
            calculation = source["calculation"]
            if calculation == "duration_ms / 1000":
                value = value / 1000
            elif "count(outcome ==" in calculation:
                # This is an aggregation calculation for multiple runs
                # For single run, convert outcome to percentage
                if value == "success":
                    value = 100.0
                elif value == "partial":
                    value = 50.0
                else:
                    value = 0.0
            # Add more calculations as needed
        elif value is not None and isinstance(value, int) and field_path.endswith(".duration_ms"):
            # Auto-convert duration_ms to seconds
            value = value / 1000

        return value

    # Transcript pattern matching
    if "transcript_pattern" in source and transcript_content:
        pattern = source["transcript_pattern"]
        match = re.search(pattern, transcript_content)
        if match:
            if match.groups():
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    return 1  # Pattern found
            return 1  # Pattern found but no capture group

    # Friction point field
    if "friction_point_field" in source:
        friction_points = evidence.get("friction_points", [])
        field_spec = source["friction_point_field"]

        if "count where category" in field_spec:
            # Parse categories from spec
            match = re.search(r"category in \[([^\]]+)\]", field_spec)
            if match:
                categories = [c.strip() for c in match.group(1).split(",")]
                count = sum(
                    1 for fp in friction_points
                    if fp.get("category") in categories
                )
                return count

        if "recovery_duration" in field_spec:
            # Calculate average recovery duration
            durations = [
                fp.get("recovery_duration_seconds", 0)
                for fp in friction_points
                if fp.get("category") == "blocker"
            ]
            return statistics.mean(durations) if durations else None

    # File exists check
    if "file_exists_check" in source:
        file_path = source["file_exists_check"]
        # This would need context from the run directory
        return None  # Placeholder

    return None


def get_nested_value(data: dict[str, Any], path: str) -> Any:
    """
    Get a nested value from a dictionary using dot notation.

    Args:
        data: Dictionary to search
        path: Dot-separated path (e.g., "stages.install.duration_ms")

    Returns:
        Value at path or None if not found
    """
    parts = path.split(".")
    current = data

    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None

        if current is None:
            return None

    return current


def evaluate_threshold(
    value: Union[int, float, bool, None],
    thresholds: dict[str, Any],
    persona: Optional[str] = None,
    persona_targets: Optional[dict[str, Any]] = None,
) -> tuple[str, bool, Optional[Union[int, float, bool]]]:
    """
    Evaluate a metric value against thresholds.

    Args:
        value: The metric value
        thresholds: Threshold configuration
        persona: Optional persona for persona-specific targets
        persona_targets: Persona-specific thresholds

    Returns:
        (threshold_level, passed, applicable_threshold)
    """
    if value is None:
        return "unknown", False, None

    # Boolean metrics
    if "required" in thresholds:
        required = thresholds["required"]
        passed = value == required
        return "required" if passed else "failed", passed, required

    # Use persona target if available
    applicable_threshold = None
    if persona and persona_targets and persona in persona_targets:
        applicable_threshold = persona_targets[persona]

    # Determine level based on thresholds
    level = "critical"
    passed = False

    if applicable_threshold is not None:
        # Check against persona-specific threshold
        if isinstance(applicable_threshold, bool):
            passed = value == applicable_threshold
            level = "acceptable" if passed else "critical"
        elif isinstance(value, (int, float)):
            # For time/count metrics, lower is better (check if <= threshold)
            # For rate metrics, higher is better (check if >= threshold)
            if thresholds.get("excellent", 0) < thresholds.get("acceptable", 0):
                # Lower is better
                passed = value <= applicable_threshold
            else:
                # Higher is better
                passed = value >= applicable_threshold
            level = "acceptable" if passed else "concerning"
        return level, passed, applicable_threshold

    # Standard threshold evaluation
    excellent = thresholds.get("excellent")
    acceptable = thresholds.get("acceptable")
    concerning = thresholds.get("concerning")
    critical = thresholds.get("critical")

    if excellent is not None and isinstance(value, (int, float)):
        # Determine if lower or higher is better
        if excellent < acceptable if acceptable is not None else True:
            # Lower is better (time metrics)
            if value <= excellent:
                return "excellent", True, excellent
            elif acceptable is not None and value <= acceptable:
                return "acceptable", True, acceptable
            elif concerning is not None and value <= concerning:
                return "concerning", False, concerning
            else:
                return "critical", False, critical
        else:
            # Higher is better (rate metrics)
            if value >= excellent:
                return "excellent", True, excellent
            elif acceptable is not None and value >= acceptable:
                return "acceptable", True, acceptable
            elif concerning is not None and value >= concerning:
                return "concerning", False, concerning
            else:
                return "critical", False, critical

    return "unknown", False, None


# ============================================================================
# Gate Evaluation
# ============================================================================

def evaluate_gate(
    gate_config: dict[str, Any],
    metrics: list[MetricResult],
    persona: Optional[str] = None,
) -> GateResult:
    """
    Evaluate a quality gate against collected metrics.

    Args:
        gate_config: Gate configuration from YAML
        metrics: List of collected metric results
        persona: Optional persona for filtering

    Returns:
        GateResult with pass/fail and criteria details
    """
    gate_id = gate_config.get("name", "unknown")
    criteria = gate_config.get("criteria", [])
    criteria_results = []
    all_passed = True

    for criterion in criteria:
        metric_id_suffix = criterion.get("metric", "")
        operator = criterion.get("operator", ">=")
        threshold = criterion.get("value")
        all_personas = criterion.get("all_personas", False)
        criterion_persona = criterion.get("persona")

        # Skip if persona-specific and doesn't match
        if criterion_persona and persona and criterion_persona != persona:
            continue

        # Find matching metric
        matching_metrics = [
            m for m in metrics
            if m.metric_id.endswith(metric_id_suffix) or m.name.lower().replace(" ", "_") == metric_id_suffix
        ]

        if not matching_metrics:
            criteria_results.append({
                "metric": metric_id_suffix,
                "status": "missing",
                "passed": False,
            })
            all_passed = False
            continue

        for metric in matching_metrics:
            if all_personas or (not criterion_persona) or (criterion_persona == persona):
                # Evaluate criterion
                passed = evaluate_criterion(metric.value, operator, threshold)
                criteria_results.append({
                    "metric": metric.metric_id,
                    "operator": operator,
                    "threshold": threshold,
                    "actual": metric.value,
                    "passed": passed,
                })
                if not passed:
                    all_passed = False

    return GateResult(
        gate_id=gate_id,
        name=gate_config.get("name", ""),
        description=gate_config.get("description", ""),
        passed=all_passed,
        criteria_results=criteria_results,
    )


def evaluate_criterion(
    value: Union[int, float, bool, str, None],
    operator: str,
    threshold: Union[int, float, bool],
) -> bool:
    """Evaluate a single criterion."""
    if value is None:
        return False

    # Handle string values
    if isinstance(value, str):
        # For string outcomes like "success"
        if operator == "==":
            return value == str(threshold)
        elif operator == "!=":
            return value != str(threshold)
        # Try to convert to number if possible
        try:
            value = float(value)
        except ValueError:
            # Can't compare string with number for >=, <=, etc.
            return False

    # Handle boolean comparison
    if isinstance(value, bool) and isinstance(threshold, bool):
        if operator == "==":
            return value == threshold
        elif operator == "!=":
            return value != threshold
        return False

    # Numeric comparisons
    try:
        if operator == ">=":
            return value >= threshold
        elif operator == ">":
            return value > threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "<":
            return value < threshold
        elif operator == "==":
            return value == threshold
        elif operator == "!=":
            return value != threshold
    except TypeError:
        return False

    return False


# ============================================================================
# Report Generation
# ============================================================================

def collect_metrics(
    evidence_path: Path,
    config: dict[str, Any],
    persona: Optional[str] = None,
) -> MetricsReport:
    """
    Collect metrics from an evidence pack.

    Args:
        evidence_path: Path to evidence pack directory
        config: Metrics configuration
        persona: Optional persona for persona-specific thresholds

    Returns:
        MetricsReport with collected metrics and gate evaluations
    """
    # Load evidence manifest
    manifest_path = evidence_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path) as f:
        evidence = json.load(f)

    # Try to load transcript for pattern matching
    transcript_content = None
    transcript_dir = evidence_path / "transcripts"
    if transcript_dir.exists():
        transcripts = list(transcript_dir.glob("*.txt"))
        if transcripts:
            transcript_content = "\n".join(t.read_text() for t in transcripts)

    # Collect metrics
    metrics_config = config.get("metrics", {})
    metrics = []

    for metric_id, metric_cfg in metrics_config.items():
        value = extract_metric_value(evidence, metric_cfg, transcript_content)
        thresholds = metric_cfg.get("thresholds", {})
        persona_targets = metric_cfg.get("persona_targets", {})

        level, passed, threshold_value = evaluate_threshold(
            value, thresholds, persona, persona_targets
        )

        metrics.append(MetricResult(
            metric_id=metric_cfg.get("id", metric_id),
            name=metric_cfg.get("name", metric_id),
            value=value,
            unit=metric_cfg.get("unit", ""),
            threshold_level=level,
            passed=passed,
            threshold_value=threshold_value,
            persona=persona,
        ))

    # Evaluate gates
    gates_config = config.get("gates", {})
    gates = []

    for gate_id, gate_cfg in gates_config.items():
        gate_result = evaluate_gate(gate_cfg, metrics, persona)
        gates.append(gate_result)

    # Determine overall pass/fail
    # P0 gate must pass for overall pass
    p0_gates = [g for g in gates if "p0" in g.gate_id.lower()]
    overall_passed = all(g.passed for g in p0_gates) if p0_gates else all(g.passed for g in gates)

    # Build summary
    summary = {
        "total_metrics": len(metrics),
        "passed_metrics": sum(1 for m in metrics if m.passed),
        "failed_metrics": sum(1 for m in metrics if not m.passed),
        "unknown_metrics": sum(1 for m in metrics if m.value is None),
        "total_gates": len(gates),
        "passed_gates": sum(1 for g in gates if g.passed),
        "failed_gates": sum(1 for g in gates if not g.passed),
    }

    return MetricsReport(
        run_id=evidence.get("run_id", "unknown"),
        persona=persona,
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        metrics=metrics,
        gates=gates,
        overall_passed=overall_passed,
        summary=summary,
    )


def render_markdown_report(report: MetricsReport, config: dict[str, Any]) -> str:
    """
    Render a metrics report as markdown.

    Args:
        report: MetricsReport to render
        config: Configuration for reference

    Returns:
        Markdown string
    """
    lines = [
        "# User Journey Metrics Report",
        "",
        f"**Run ID:** {report.run_id}",
        f"**Persona:** {report.persona or 'all'}",
        f"**Generated:** {report.timestamp}",
        f"**Overall Status:** {'PASS' if report.overall_passed else 'FAIL'}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Metrics Collected | {report.summary.get('total_metrics', 0)} |",
        f"| Metrics Passed | {report.summary.get('passed_metrics', 0)} |",
        f"| Metrics Failed | {report.summary.get('failed_metrics', 0)} |",
        f"| Unknown/Missing | {report.summary.get('unknown_metrics', 0)} |",
        f"| Gates Evaluated | {report.summary.get('total_gates', 0)} |",
        f"| Gates Passed | {report.summary.get('passed_gates', 0)} |",
        "",
        "---",
        "",
        "## Quality Gates",
        "",
    ]

    for gate in report.gates:
        status = "PASS" if gate.passed else "FAIL"
        lines.append(f"### {gate.name}: {status}")
        lines.append("")
        lines.append(f"{gate.description}")
        lines.append("")

        if gate.criteria_results:
            lines.append("| Metric | Operator | Threshold | Actual | Status |")
            lines.append("|--------|----------|-----------|--------|--------|")
            for cr in gate.criteria_results:
                actual = cr.get("actual", "N/A")
                if isinstance(actual, float):
                    actual = f"{actual:.2f}"
                status_icon = "PASS" if cr.get("passed", False) else "FAIL"
                lines.append(
                    f"| {cr.get('metric', 'unknown')} | {cr.get('operator', '')} | "
                    f"{cr.get('threshold', 'N/A')} | {actual} | {status_icon} |"
                )
            lines.append("")

    lines.extend([
        "---",
        "",
        "## Metric Details",
        "",
        "| ID | Name | Value | Unit | Level | Status |",
        "|-----|------|-------|------|-------|--------|",
    ])

    for metric in report.metrics:
        value = metric.value
        if isinstance(value, float):
            value = f"{value:.2f}"
        elif value is None:
            value = "N/A"
        status = "PASS" if metric.passed else "FAIL"
        lines.append(
            f"| {metric.metric_id} | {metric.name} | {value} | "
            f"{metric.unit} | {metric.threshold_level} | {status} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Recommendations",
        "",
    ])

    # Generate recommendations based on failures
    failed_metrics = [m for m in report.metrics if not m.passed and m.value is not None]
    if failed_metrics:
        lines.append("The following metrics require attention:")
        lines.append("")
        for m in failed_metrics:
            lines.append(f"- **{m.name}**: Current value ({m.value}) is {m.threshold_level}. "
                        f"Target: {m.threshold_value}")
    else:
        lines.append("All measured metrics are within acceptable thresholds.")

    unknown_metrics = [m for m in report.metrics if m.value is None]
    if unknown_metrics:
        lines.append("")
        lines.append("The following metrics could not be measured:")
        lines.append("")
        for m in unknown_metrics:
            lines.append(f"- **{m.name}**: Data not available in evidence pack")

    lines.extend([
        "",
        "---",
        "",
        "## References",
        "",
        "- Configuration: `configs/user_journey_metrics.yaml`",
        "- Gate Definitions: `phases/07.3.2-execution-evidence-protocol/07.3.2-GATES.md`",
        "- Phase Design: `07.3.4-PHASE-DESIGN.md`",
        "",
    ])

    return "\n".join(lines)


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect user journey metrics from evidence packs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect from single evidence pack
  %(prog)s --evidence-pack .vrs/validation/runs/run-001

  # Collect with persona-specific thresholds
  %(prog)s --evidence-pack .vrs/validation/runs/run-001 --persona novice

  # Output JSON format
  %(prog)s --evidence-pack .vrs/validation/runs/run-001 --format json

  # Check gates only
  %(prog)s --evidence-pack .vrs/validation/runs/run-001 --gates-only
""",
    )

    parser.add_argument(
        "--evidence-pack",
        type=Path,
        help="Path to evidence pack directory",
    )
    parser.add_argument(
        "--evidence-packs",
        type=Path,
        nargs="+",
        help="Multiple evidence pack directories for aggregation",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Metrics configuration file (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output file path (default: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--persona",
        choices=["novice", "intermediate", "power_user"],
        help="Persona for persona-specific thresholds",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--gates-only",
        action="store_true",
        help="Only check quality gates, don't output full report",
    )
    parser.add_argument(
        "--aggregate",
        action="store_true",
        help="Aggregate metrics across multiple runs",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration
    if not args.config.exists():
        logger.error(f"Configuration file not found: {args.config}")
        return 1

    with open(args.config) as f:
        config = yaml.safe_load(f)

    logger.info(f"Loaded configuration from {args.config}")

    # Collect from single pack or aggregate
    evidence_paths = []
    if args.evidence_pack:
        evidence_paths = [args.evidence_pack]
    elif args.evidence_packs:
        evidence_paths = args.evidence_packs
    else:
        # Look for most recent run
        runs_dir = Path(".vrs/validation/runs")
        if runs_dir.exists():
            runs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
            if runs:
                evidence_paths = [runs[0]]
                logger.info(f"Using most recent run: {runs[0]}")

    if not evidence_paths:
        logger.error("No evidence pack specified. Use --evidence-pack or --evidence-packs")
        return 1

    # Collect metrics
    reports = []
    for evidence_path in evidence_paths:
        if not evidence_path.exists():
            logger.warning(f"Evidence pack not found: {evidence_path}")
            continue

        try:
            report = collect_metrics(evidence_path, config, args.persona)
            reports.append(report)
            logger.info(f"Collected metrics from {evidence_path}")
        except Exception as e:
            logger.error(f"Failed to collect from {evidence_path}: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()

    if not reports:
        logger.error("No metrics collected")
        return 1

    # Use first report (or aggregate in future)
    report = reports[0]

    # Gates-only mode
    if args.gates_only:
        print("\nQuality Gate Results:")
        print("=" * 40)
        for gate in report.gates:
            status = "PASS" if gate.passed else "FAIL"
            print(f"  {gate.name}: {status}")
        print("=" * 40)
        print(f"Overall: {'PASS' if report.overall_passed else 'FAIL'}")
        return 0 if report.overall_passed else 1

    # Generate output
    if args.format == "json":
        output = json.dumps(report.to_dict(), indent=2)
    else:
        output = render_markdown_report(report, config)

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        f.write(output)

    logger.info(f"Report written to {args.output}")
    print(f"\nMetrics Report: {args.output}")
    print(f"Overall Status: {'PASS' if report.overall_passed else 'FAIL'}")
    print(f"Metrics: {report.summary.get('passed_metrics', 0)}/{report.summary.get('total_metrics', 0)} passed")
    print(f"Gates: {report.summary.get('passed_gates', 0)}/{report.summary.get('total_gates', 0)} passed")

    return 0 if report.overall_passed else 1


if __name__ == "__main__":
    sys.exit(main())
