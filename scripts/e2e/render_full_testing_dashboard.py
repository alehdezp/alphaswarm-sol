#!/usr/bin/env python3
"""
Dashboard renderer for /vrs-full-testing results.

Reads evidence packs and generates markdown/JSON dashboards with:
- Gate status summary
- Scenario coverage heatmap
- Debug-mode compliance
- Failure taxonomy breakdown
- Perfect metrics investigation
- Regression analysis (if baseline exists)

Usage:
    python render_full_testing_dashboard.py evidence-pack/ [--output dashboard.md] [--json]
    python render_full_testing_dashboard.py evidence-pack/ --baseline baseline-pack/
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class GateResult:
    """Result for a single QA gate."""

    gate_id: str
    name: str
    status: str  # PASS, FAIL, WARN
    value: str
    threshold: str
    blocking: bool


@dataclass
class CategoryCoverage:
    """Coverage metrics for a scenario category."""

    category: str
    total: int
    passed: int
    failed: int
    skipped: int

    @property
    def coverage_pct(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100


@dataclass
class FailureEntry:
    """Single failure entry."""

    scenario_id: str
    error_code: str
    category: str
    message: str
    retry_eligible: bool


@dataclass
class PerfectMetricCheck:
    """Check result for perfect metrics investigation."""

    metric: str
    value: float
    threshold: str
    triggered: bool


@dataclass
class RegressionEntry:
    """Regression comparison entry."""

    metric: str
    baseline: float
    current: float
    delta: float
    threshold: float
    status: str  # PASS, FAIL


@dataclass
class DashboardData:
    """Complete dashboard data."""

    run_id: str
    evaluated_at: str
    duration_ms: int
    overall_status: str

    # Gate summary
    gates: list[GateResult] = field(default_factory=list)
    gates_passed: list[str] = field(default_factory=list)
    gates_failed: list[str] = field(default_factory=list)
    gates_warned: list[str] = field(default_factory=list)
    blocking_failures: int = 0

    # Coverage
    coverage_by_category: list[CategoryCoverage] = field(default_factory=list)
    negative_controls: list[dict[str, Any]] = field(default_factory=list)
    overall_coverage_pct: float = 0.0

    # Debug compliance
    debug_enabled: bool = False
    debug_records_count: int = 0
    debug_compliance_rate: float = 0.0
    debug_by_agent: dict[str, dict[str, Any]] = field(default_factory=dict)
    debug_by_skill: dict[str, dict[str, Any]] = field(default_factory=dict)
    debug_validation_errors: list[str] = field(default_factory=list)

    # Failures
    failures: list[FailureEntry] = field(default_factory=list)
    failures_by_category: dict[str, int] = field(default_factory=dict)

    # Perfect metrics
    perfect_metric_checks: list[PerfectMetricCheck] = field(default_factory=list)
    perfect_metrics_triggered: bool = False

    # Regression
    baseline_run_id: str | None = None
    regressions: list[RegressionEntry] = field(default_factory=list)
    scenario_regressions: list[dict[str, Any]] = field(default_factory=list)

    evidence_pack_path: str = ""


# =============================================================================
# Evidence Pack Loader
# =============================================================================


def load_json_file(path: Path) -> dict[str, Any] | None:
    """Load JSON file if exists, return None otherwise."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: Failed to load {path}: {e}", file=sys.stderr)
        return None


def load_evidence_pack(pack_path: Path) -> dict[str, Any]:
    """Load all evidence pack files."""
    manifest = load_json_file(pack_path / "manifest.json") or {}
    accuracy = load_json_file(pack_path / "metrics" / "accuracy.json") or {}
    agreement = load_json_file(pack_path / "metrics" / "agreement.json") or {}
    debug_index = load_json_file(pack_path / "debug" / "index.json") or {}

    return {
        "manifest": manifest,
        "accuracy": accuracy,
        "agreement": agreement,
        "debug_index": debug_index,
        "path": str(pack_path),
    }


# =============================================================================
# Gate Evaluation
# =============================================================================

GATE_DEFINITIONS = [
    ("G01", "Stage Completion", True),
    ("G02", "Precision", True),
    ("G03", "Recall", True),
    ("G04", "F1 Score", True),
    ("G05", "Debug Coverage", True),
    ("G06", "Tier-C Detection", True),
    ("G07", "Economic Context", True),
    ("G08", "Agent Agreement", False),  # Warning only
    ("G09", "Transcript Validity", True),
    ("G10", "Duration Validity", True),
]


def evaluate_gates(data: dict[str, Any]) -> list[GateResult]:
    """Evaluate all QA gates from evidence pack data."""
    manifest = data.get("manifest", {})
    accuracy = data.get("accuracy", {})
    agreement = data.get("agreement", {})

    results = []

    # G01: Stage Completion
    suites = manifest.get("suites", {})
    all_passed = all(s.get("status") == "passed" for s in suites.values()) if suites else False
    suite_count = len(suites)
    passed_count = sum(1 for s in suites.values() if s.get("status") == "passed")
    results.append(
        GateResult(
            gate_id="G01",
            name="Stage Completion",
            status="PASS" if all_passed else "FAIL",
            value=f"{passed_count}/{suite_count}",
            threshold="All passed",
            blocking=True,
        )
    )

    # G02: Precision
    precision = accuracy.get("overall", {}).get("precision")
    if precision is not None:
        status = "PASS" if precision >= 0.85 else "FAIL"
        results.append(
            GateResult(
                gate_id="G02",
                name="Precision",
                status=status,
                value=f"{precision:.2f}",
                threshold=">= 0.85",
                blocking=True,
            )
        )
    else:
        results.append(
            GateResult(
                gate_id="G02",
                name="Precision",
                status="FAIL",
                value="N/A",
                threshold=">= 0.85",
                blocking=True,
            )
        )

    # G03: Recall
    recall = accuracy.get("overall", {}).get("recall")
    if recall is not None:
        status = "PASS" if recall >= 0.80 else "FAIL"
        results.append(
            GateResult(
                gate_id="G03",
                name="Recall",
                status=status,
                value=f"{recall:.2f}",
                threshold=">= 0.80",
                blocking=True,
            )
        )
    else:
        results.append(
            GateResult(
                gate_id="G03",
                name="Recall",
                status="FAIL",
                value="N/A",
                threshold=">= 0.80",
                blocking=True,
            )
        )

    # G04: F1 Score
    f1 = accuracy.get("overall", {}).get("f1_score")
    if f1 is not None:
        status = "PASS" if f1 >= 0.82 else "FAIL"
        results.append(
            GateResult(
                gate_id="G04",
                name="F1 Score",
                status=status,
                value=f"{f1:.2f}",
                threshold=">= 0.82",
                blocking=True,
            )
        )
    else:
        results.append(
            GateResult(
                gate_id="G04",
                name="F1 Score",
                status="FAIL",
                value="N/A",
                threshold=">= 0.82",
                blocking=True,
            )
        )

    # G05: Debug Coverage
    debug = manifest.get("debug", {})
    debug_enabled = debug.get("enabled", False)
    validation = debug.get("validation", {})
    all_valid = validation.get("all_records_valid", False)
    records_count = debug.get("records_count", 0)

    if debug_enabled and all_valid:
        status = "PASS"
        value = f"{records_count}/{records_count}"
    else:
        status = "FAIL"
        value = f"{records_count} (invalid)" if not all_valid else "disabled"

    results.append(
        GateResult(
            gate_id="G05",
            name="Debug Coverage",
            status=status,
            value=value,
            threshold="100%",
            blocking=True,
        )
    )

    # G06: Tier-C Detection
    tier_c = accuracy.get("by_category", {}).get("tier_c_labels", {})
    tier_c_tps = tier_c.get("true_positives", 0)
    status = "PASS" if tier_c_tps >= 1 else "FAIL"
    results.append(
        GateResult(
            gate_id="G06",
            name="Tier-C Detection",
            status=status,
            value=f"{tier_c_tps} TPs",
            threshold=">= 1",
            blocking=True,
        )
    )

    # G07: Economic Context
    scenarios = manifest.get("scenarios", [])
    oracle_categories = ["oracle", "pricing", "economic"]
    oracle_passed = sum(
        1
        for s in scenarios
        if s.get("category") in oracle_categories and s.get("status") == "passed"
    )
    oracle_total = sum(1 for s in scenarios if s.get("category") in oracle_categories)
    status = "PASS" if oracle_passed >= 1 else "FAIL"
    results.append(
        GateResult(
            gate_id="G07",
            name="Economic Context",
            status=status,
            value=f"{oracle_passed}/{oracle_total}",
            threshold=">= 1",
            blocking=True,
        )
    )

    # G08: Agent Agreement (warning only)
    agreement_rate = agreement.get("overall_agreement_rate")
    if agreement_rate is not None:
        status = "PASS" if agreement_rate >= 0.90 else "WARN"
        results.append(
            GateResult(
                gate_id="G08",
                name="Agent Agreement",
                status=status,
                value=f"{agreement_rate:.2f}",
                threshold=">= 0.90",
                blocking=False,
            )
        )
    else:
        results.append(
            GateResult(
                gate_id="G08",
                name="Agent Agreement",
                status="WARN",
                value="N/A",
                threshold=">= 0.90",
                blocking=False,
            )
        )

    # G09: Transcript Validity
    validation = manifest.get("validation", {})
    pack_valid = validation.get("pack_valid", False)
    markers_valid = validation.get("all_markers_valid", False)
    transcripts_present = validation.get("all_transcripts_present", False)

    if pack_valid and markers_valid and transcripts_present:
        status = "PASS"
        scenario_count = len(scenarios)
        value = f"{scenario_count}/{scenario_count}"
    else:
        status = "FAIL"
        value = "invalid"

    results.append(
        GateResult(
            gate_id="G09",
            name="Transcript Validity",
            status=status,
            value=value,
            threshold="All valid",
            blocking=True,
        )
    )

    # G10: Duration Validity
    all_valid_duration = all(s.get("duration_ms", 0) > 5000 for s in scenarios) if scenarios else False
    invalid_count = sum(1 for s in scenarios if s.get("duration_ms", 0) <= 5000)

    if all_valid_duration:
        status = "PASS"
        value = "All > 5s"
    else:
        status = "FAIL"
        value = f"{invalid_count} invalid"

    results.append(
        GateResult(
            gate_id="G10",
            name="Duration Validity",
            status=status,
            value=value,
            threshold="> 5000ms",
            blocking=True,
        )
    )

    return results


# =============================================================================
# Coverage Analysis
# =============================================================================

CATEGORY_ORDER = [
    "reentrancy",
    "access",
    "oracle",
    "pricing",
    "upgradeability",
    "flash_loan",
    "governance",
    "erc_standards",
    "math",
    "cross_contract",
    "mev",
    "parser",
    "tier_c",
    "workflow",
    "failure_injection",
]


def compute_coverage(manifest: dict[str, Any]) -> list[CategoryCoverage]:
    """Compute scenario coverage by category."""
    scenarios = manifest.get("scenarios", [])

    # Group by category
    by_category: dict[str, dict[str, int]] = {}
    for s in scenarios:
        cat = s.get("category", "unknown")
        if cat not in by_category:
            by_category[cat] = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
        by_category[cat]["total"] += 1

        status = s.get("status", "skipped")
        if status == "passed":
            by_category[cat]["passed"] += 1
        elif status == "failed":
            by_category[cat]["failed"] += 1
        else:
            by_category[cat]["skipped"] += 1

    # Convert to list, maintaining order
    results = []
    for cat in CATEGORY_ORDER:
        if cat in by_category:
            data = by_category[cat]
            results.append(
                CategoryCoverage(
                    category=cat,
                    total=data["total"],
                    passed=data["passed"],
                    failed=data["failed"],
                    skipped=data["skipped"],
                )
            )

    # Add any remaining categories
    for cat, data in by_category.items():
        if cat not in CATEGORY_ORDER:
            results.append(
                CategoryCoverage(
                    category=cat,
                    total=data["total"],
                    passed=data["passed"],
                    failed=data["failed"],
                    skipped=data["skipped"],
                )
            )

    return results


def extract_negative_controls(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract negative control scenario results."""
    scenarios = manifest.get("scenarios", [])
    negative_ids = {f"S{i:02d}" for i in [6, 10, 18, 20, 27, 30, 36, 38, 44, 46, 51, 54, 60, 62, 67, 70, 74, 79, 89]}

    results = []
    for s in scenarios:
        if s.get("id") in negative_ids:
            results.append(
                {
                    "id": s.get("id"),
                    "scenario": s.get("name", ""),
                    "expected": "TN",
                    "actual": "TN" if s.get("status") == "passed" else "FP",
                    "status": "PASS" if s.get("status") == "passed" else "FAIL",
                }
            )

    return results


# =============================================================================
# Perfect Metrics Detection
# =============================================================================


def check_perfect_metrics(accuracy: dict[str, Any]) -> list[PerfectMetricCheck]:
    """Check for suspiciously perfect metrics."""
    checks = []
    overall = accuracy.get("overall", {})

    for metric_name, display_name in [
        ("precision", "Precision"),
        ("recall", "Recall"),
        ("f1_score", "F1 Score"),
    ]:
        value = overall.get(metric_name)
        if value is not None:
            triggered = value == 1.0
            checks.append(
                PerfectMetricCheck(
                    metric=display_name,
                    value=value,
                    threshold="!= 1.0",
                    triggered=triggered,
                )
            )

    return checks


# =============================================================================
# Failure Analysis
# =============================================================================


def analyze_failures(manifest: dict[str, Any]) -> tuple[list[FailureEntry], dict[str, int]]:
    """Analyze failures from evidence pack."""
    scenarios = manifest.get("scenarios", [])
    failures = []
    by_category: dict[str, int] = {}

    for s in scenarios:
        if s.get("status") == "failed":
            error = s.get("error", {})
            error_code = error.get("code", "E-UNKNOWN")
            category = error.get("category", "unknown")

            failures.append(
                FailureEntry(
                    scenario_id=s.get("id", ""),
                    error_code=error_code,
                    category=category,
                    message=error.get("message", ""),
                    retry_eligible=error.get("retry_eligible", False),
                )
            )

            by_category[category] = by_category.get(category, 0) + 1

    return failures, by_category


# =============================================================================
# Debug Compliance
# =============================================================================


def analyze_debug_compliance(
    manifest: dict[str, Any], debug_index: dict[str, Any]
) -> tuple[dict[str, dict], dict[str, dict], list[str], float]:
    """Analyze debug-mode compliance."""
    by_agent: dict[str, dict[str, Any]] = {}
    by_skill: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    records = debug_index.get("records", [])

    for record in records:
        name = record.get("skill_or_agent", "")
        status = record.get("status", "error")
        duration = record.get("duration_ms", 0)

        # Classify as agent or skill
        if name.startswith("/vrs-"):
            target = by_skill
        elif name.startswith("vrs-"):
            target = by_agent
        else:
            target = by_skill  # Default to skill

        if name not in target:
            target[name] = {"invocations": 0, "records": 0, "valid": 0, "total_duration_ms": 0}

        target[name]["invocations"] += 1
        target[name]["records"] += 1
        if status == "success":
            target[name]["valid"] += 1
        else:
            errors.append(f"{name}: {record.get('error', 'unknown error')}")
        target[name]["total_duration_ms"] += duration

    # Calculate averages
    for target in [by_agent, by_skill]:
        for name, data in target.items():
            if data["records"] > 0:
                data["avg_duration_ms"] = data["total_duration_ms"] / data["records"]
            else:
                data["avg_duration_ms"] = 0

    # Compliance rate
    total_records = len(records)
    valid_records = sum(1 for r in records if r.get("status") == "success")
    compliance_rate = (valid_records / total_records * 100) if total_records > 0 else 0.0

    return by_agent, by_skill, errors, compliance_rate


# =============================================================================
# Regression Analysis
# =============================================================================


def compare_with_baseline(
    current: dict[str, Any], baseline: dict[str, Any]
) -> tuple[list[RegressionEntry], list[dict[str, Any]]]:
    """Compare current run with baseline for regressions."""
    metric_regressions = []
    scenario_changes = []

    current_accuracy = current.get("accuracy", {}).get("overall", {})
    baseline_accuracy = baseline.get("accuracy", {}).get("overall", {})

    # Metric thresholds (max allowed regression)
    thresholds = {
        "precision": 0.05,
        "recall": 0.05,
        "f1_score": 0.03,
    }

    for metric, threshold in thresholds.items():
        current_val = current_accuracy.get(metric)
        baseline_val = baseline_accuracy.get(metric)

        if current_val is not None and baseline_val is not None:
            delta = current_val - baseline_val
            status = "PASS" if delta >= -threshold else "FAIL"

            metric_regressions.append(
                RegressionEntry(
                    metric=metric.replace("_", " ").title(),
                    baseline=baseline_val,
                    current=current_val,
                    delta=delta,
                    threshold=threshold,
                    status=status,
                )
            )

    # Scenario-level comparison
    current_scenarios = {s.get("id"): s for s in current.get("manifest", {}).get("scenarios", [])}
    baseline_scenarios = {s.get("id"): s for s in baseline.get("manifest", {}).get("scenarios", [])}

    for scenario_id in set(current_scenarios.keys()) | set(baseline_scenarios.keys()):
        current_status = current_scenarios.get(scenario_id, {}).get("status")
        baseline_status = baseline_scenarios.get(scenario_id, {}).get("status")

        if current_status != baseline_status:
            if baseline_status == "passed" and current_status == "failed":
                change = "REGRESSION"
            elif baseline_status == "failed" and current_status == "passed":
                change = "IMPROVEMENT"
            else:
                change = "CHANGED"

            scenario_changes.append(
                {
                    "scenario_id": scenario_id,
                    "baseline": baseline_status or "N/A",
                    "current": current_status or "N/A",
                    "change": change,
                }
            )

    return metric_regressions, scenario_changes


# =============================================================================
# Dashboard Builder
# =============================================================================


def build_dashboard(
    data: dict[str, Any], baseline_data: dict[str, Any] | None = None
) -> DashboardData:
    """Build complete dashboard data from evidence pack."""
    manifest = data.get("manifest", {})
    accuracy = data.get("accuracy", {})
    debug_index = data.get("debug_index", {})

    # Basic info
    run_id = manifest.get("run_id", "unknown")
    evaluated_at = manifest.get("evaluated_at", datetime.utcnow().isoformat() + "Z")
    duration_ms = manifest.get("duration_ms", 0)

    # Evaluate gates
    gates = evaluate_gates(data)
    gates_passed = [g.gate_id for g in gates if g.status == "PASS"]
    gates_failed = [g.gate_id for g in gates if g.status == "FAIL"]
    gates_warned = [g.gate_id for g in gates if g.status == "WARN"]
    blocking_failures = sum(1 for g in gates if g.status == "FAIL" and g.blocking)

    # Overall status
    if blocking_failures > 0:
        overall_status = "FAIL"
    elif gates_warned:
        overall_status = "WARN"
    else:
        overall_status = "PASS"

    # Coverage
    coverage_by_category = compute_coverage(manifest)
    negative_controls = extract_negative_controls(manifest)
    total_scenarios = sum(c.total for c in coverage_by_category)
    passed_scenarios = sum(c.passed for c in coverage_by_category)
    overall_coverage_pct = (passed_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0.0

    # Debug compliance
    debug = manifest.get("debug", {})
    by_agent, by_skill, debug_errors, compliance_rate = analyze_debug_compliance(manifest, debug_index)

    # Failures
    failures, failures_by_category = analyze_failures(manifest)

    # Perfect metrics check
    perfect_checks = check_perfect_metrics(accuracy)
    perfect_triggered = any(c.triggered for c in perfect_checks)

    # Regression analysis
    regressions = []
    scenario_regressions = []
    baseline_run_id = None

    if baseline_data:
        baseline_run_id = baseline_data.get("manifest", {}).get("run_id")
        regressions, scenario_regressions = compare_with_baseline(data, baseline_data)

    return DashboardData(
        run_id=run_id,
        evaluated_at=evaluated_at,
        duration_ms=duration_ms,
        overall_status=overall_status,
        gates=gates,
        gates_passed=gates_passed,
        gates_failed=gates_failed,
        gates_warned=gates_warned,
        blocking_failures=blocking_failures,
        coverage_by_category=coverage_by_category,
        negative_controls=negative_controls,
        overall_coverage_pct=overall_coverage_pct,
        debug_enabled=debug.get("enabled", False),
        debug_records_count=debug.get("records_count", 0),
        debug_compliance_rate=compliance_rate,
        debug_by_agent=by_agent,
        debug_by_skill=by_skill,
        debug_validation_errors=debug_errors,
        failures=failures,
        failures_by_category=failures_by_category,
        perfect_metric_checks=perfect_checks,
        perfect_metrics_triggered=perfect_triggered,
        baseline_run_id=baseline_run_id,
        regressions=regressions,
        scenario_regressions=scenario_regressions,
        evidence_pack_path=data.get("path", ""),
    )


# =============================================================================
# Markdown Renderer
# =============================================================================


def format_duration(ms: int) -> str:
    """Format duration in human-readable format."""
    seconds = ms // 1000
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def render_markdown(dashboard: DashboardData) -> str:
    """Render dashboard as markdown."""
    lines = []

    # Header
    lines.append("# /vrs-full-testing Dashboard")
    lines.append("")
    lines.append(f"**Run ID:** {dashboard.run_id}")
    lines.append(f"**Date:** {dashboard.evaluated_at[:10]}")
    lines.append(f"**Duration:** {format_duration(dashboard.duration_ms)}")
    lines.append(f"**Status:** {dashboard.overall_status}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. Gate Status Summary
    lines.append("## 1. Gate Status Summary")
    lines.append("")
    lines.append(f"**Overall Status:** {dashboard.overall_status}")
    lines.append(f"**Evaluated:** {dashboard.evaluated_at}")
    lines.append(f"**Evidence Pack:** {dashboard.evidence_pack_path}")
    lines.append("")
    lines.append("| Gate | Name | Status | Value | Threshold | Blocking |")
    lines.append("|------|------|--------|-------|-----------|----------|")

    for g in dashboard.gates:
        blocking = "Yes" if g.blocking else "No"
        lines.append(f"| {g.gate_id} | {g.name} | {g.status} | {g.value} | {g.threshold} | {blocking} |")

    lines.append("")
    lines.append("**Summary:**")
    lines.append(f"- Passed: {len(dashboard.gates_passed)}/10 gates")
    if dashboard.gates_warned:
        lines.append(f"- Warnings: {len(dashboard.gates_warned)} ({', '.join(dashboard.gates_warned)})")
    lines.append(f"- Blocking Failures: {dashboard.blocking_failures}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 2. Scenario Coverage Heatmap
    lines.append("## 2. Scenario Coverage Heatmap")
    lines.append("")
    lines.append("### By Category")
    lines.append("")
    lines.append("| Category | Total | Passed | Failed | Skipped | Coverage |")
    lines.append("|----------|-------|--------|--------|---------|----------|")

    total_all = passed_all = failed_all = skipped_all = 0
    for c in dashboard.coverage_by_category:
        lines.append(
            f"| {c.category.replace('_', ' ').title()} | {c.total} | {c.passed} | {c.failed} | {c.skipped} | {c.coverage_pct:.0f}% |"
        )
        total_all += c.total
        passed_all += c.passed
        failed_all += c.failed
        skipped_all += c.skipped

    overall_pct = (passed_all / total_all * 100) if total_all > 0 else 0
    lines.append(f"| **TOTAL** | **{total_all}** | **{passed_all}** | **{failed_all}** | **{skipped_all}** | **{overall_pct:.0f}%** |")
    lines.append("")

    # Negative controls
    if dashboard.negative_controls:
        lines.append("### Negative Control Analysis")
        lines.append("")
        lines.append("| ID | Scenario | Expected | Actual | Status |")
        lines.append("|----|----------|----------|--------|--------|")
        for nc in dashboard.negative_controls[:10]:  # Limit to first 10
            lines.append(f"| {nc['id']} | {nc['scenario'][:30]} | {nc['expected']} | {nc['actual']} | {nc['status']} |")
        if len(dashboard.negative_controls) > 10:
            lines.append(f"| ... | ({len(dashboard.negative_controls) - 10} more) | ... | ... | ... |")

        tn_count = sum(1 for nc in dashboard.negative_controls if nc["actual"] == "TN")
        fp_count = len(dashboard.negative_controls) - tn_count
        lines.append("")
        lines.append("**Negative Control Summary:**")
        lines.append(f"- Total: {len(dashboard.negative_controls)} negative controls")
        lines.append(f"- True Negatives: {tn_count} ({tn_count / len(dashboard.negative_controls) * 100:.0f}%)")
        lines.append(f"- False Positives: {fp_count} ({fp_count / len(dashboard.negative_controls) * 100:.0f}%)")

    lines.append("")
    lines.append("---")
    lines.append("")

    # 3. Debug-Mode Compliance
    lines.append("## 3. Debug-Mode Compliance")
    lines.append("")
    compliance_status = "COMPLIANT" if dashboard.debug_compliance_rate == 100 else "NON-COMPLIANT"
    lines.append(f"**Status:** {compliance_status}")
    lines.append(f"**Debug Mode:** {'Enabled' if dashboard.debug_enabled else 'Disabled'}")
    lines.append(f"**Records Captured:** {dashboard.debug_records_count}")
    lines.append("")

    if dashboard.debug_by_agent:
        lines.append("### Agent Debug Records")
        lines.append("")
        lines.append("| Agent | Invocations | Records | Valid | Duration (avg) |")
        lines.append("|-------|-------------|---------|-------|----------------|")
        for name, data in dashboard.debug_by_agent.items():
            avg_duration = format_duration(int(data.get("avg_duration_ms", 0)))
            lines.append(f"| {name} | {data['invocations']} | {data['records']} | {data['valid']} | {avg_duration} |")
        lines.append("")

    if dashboard.debug_by_skill:
        lines.append("### Skill Debug Records")
        lines.append("")
        lines.append("| Skill | Invocations | Records | Valid | Duration (avg) |")
        lines.append("|-------|-------------|---------|-------|----------------|")
        for name, data in dashboard.debug_by_skill.items():
            avg_duration = format_duration(int(data.get("avg_duration_ms", 0)))
            lines.append(f"| {name} | {data['invocations']} | {data['records']} | {data['valid']} | {avg_duration} |")
        lines.append("")

    lines.append(f"**Debug Compliance Rate:** {dashboard.debug_compliance_rate:.0f}%")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 4. Failure Taxonomy Breakdown
    lines.append("## 4. Failure Taxonomy Breakdown")
    lines.append("")

    if dashboard.failures:
        lines.append("### By Error Category")
        lines.append("")
        lines.append("| Category | Count | Examples |")
        lines.append("|----------|-------|----------|")
        for cat, count in dashboard.failures_by_category.items():
            examples = ", ".join(f.error_code for f in dashboard.failures if f.category == cat)[:50]
            lines.append(f"| {cat.title()} | {count} | {examples} |")
        lines.append("")

        lines.append("### Detailed Failure List")
        lines.append("")
        lines.append("| Scenario | Error Code | Category | Message | Retry |")
        lines.append("|----------|------------|----------|---------|-------|")
        for f in dashboard.failures[:10]:
            msg = f.message[:40] + "..." if len(f.message) > 40 else f.message
            retry = "Yes" if f.retry_eligible else "No"
            lines.append(f"| {f.scenario_id} | {f.error_code} | {f.category} | {msg} | {retry} |")
        if len(dashboard.failures) > 10:
            lines.append(f"| ... | ... | ... | ({len(dashboard.failures) - 10} more) | ... |")
    else:
        lines.append("No failures recorded.")

    lines.append("")
    lines.append("---")
    lines.append("")

    # 5. Perfect Metrics Investigation
    lines.append("## 5. Perfect Metrics Investigation")
    lines.append("")
    lines.append(f"**Status:** {'TRIGGERED' if dashboard.perfect_metrics_triggered else 'NOT_TRIGGERED'}")
    lines.append("")

    if dashboard.perfect_metric_checks:
        lines.append("### Metric Checks")
        lines.append("")
        lines.append("| Metric | Value | Threshold | Status |")
        lines.append("|--------|-------|-----------|--------|")
        for check in dashboard.perfect_metric_checks:
            status = "INVESTIGATE" if check.triggered else "OK"
            lines.append(f"| {check.metric} | {check.value:.2f} | {check.threshold} | {status} |")
        lines.append("")

    if dashboard.perfect_metrics_triggered:
        lines.append("### Investigation Required")
        lines.append("")
        lines.append("Perfect metrics (precision=1.0 OR recall=1.0) trigger investigation:")
        lines.append("- Is the corpus too easy?")
        lines.append("- Are negative controls included?")
        lines.append("- Is ground truth correctly defined?")
        lines.append("- Are edge cases covered?")
        lines.append("")
        lines.append("**Recommendation:** Manual review required for perfect metrics.")

    lines.append("")
    lines.append("---")
    lines.append("")

    # 6. Regression Analysis (if baseline)
    if dashboard.baseline_run_id:
        lines.append("## 6. Regression Analysis")
        lines.append("")
        lines.append(f"**Baseline Run:** {dashboard.baseline_run_id}")
        lines.append(f"**Current Run:** {dashboard.run_id}")
        lines.append("")

        if dashboard.regressions:
            lines.append("### Metric Comparison")
            lines.append("")
            lines.append("| Metric | Baseline | Current | Delta | Threshold | Status |")
            lines.append("|--------|----------|---------|-------|-----------|--------|")
            for r in dashboard.regressions:
                delta_str = f"+{r.delta:.2f}" if r.delta >= 0 else f"{r.delta:.2f}"
                lines.append(f"| {r.metric} | {r.baseline:.2f} | {r.current:.2f} | {delta_str} | <= {r.threshold:.2f} | {r.status} |")
            lines.append("")

        if dashboard.scenario_regressions:
            lines.append("### Scenario Changes")
            lines.append("")
            lines.append("| Scenario | Baseline | Current | Change |")
            lines.append("|----------|----------|---------|--------|")
            for sr in dashboard.scenario_regressions[:10]:
                lines.append(f"| {sr['scenario_id']} | {sr['baseline']} | {sr['current']} | {sr['change']} |")

            regression_count = sum(1 for sr in dashboard.scenario_regressions if sr["change"] == "REGRESSION")
            improvement_count = sum(1 for sr in dashboard.scenario_regressions if sr["change"] == "IMPROVEMENT")
            lines.append("")
            lines.append(f"**Regression Count:** {regression_count}")
            lines.append(f"**Improvement Count:** {improvement_count}")

        lines.append("")
        lines.append("---")
        lines.append("")

    # Appendix
    lines.append("## Appendix")
    lines.append("")
    lines.append("### Evidence Pack Contents")
    lines.append("- manifest.json")
    lines.append("- metrics/accuracy.json")
    lines.append("- metrics/agreement.json")
    lines.append("- debug/index.json")
    lines.append(f"- transcripts/ ({sum(c.total for c in dashboard.coverage_by_category)} files)")
    lines.append("")
    lines.append("### Run Configuration")
    lines.append(f"- Scenarios: {sum(c.total for c in dashboard.coverage_by_category)}")
    lines.append("- Suites: 4")
    lines.append(f"- Debug Mode: {'Enabled' if dashboard.debug_enabled else 'Disabled'}")
    if dashboard.baseline_run_id:
        lines.append(f"- Baseline: {dashboard.baseline_run_id}")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# JSON Renderer
# =============================================================================


def render_json(dashboard: DashboardData) -> str:
    """Render dashboard as JSON."""
    data = {
        "run_id": dashboard.run_id,
        "evaluated_at": dashboard.evaluated_at,
        "duration_ms": dashboard.duration_ms,
        "status": dashboard.overall_status,
        "gate_summary": {
            "ga_gate_status": dashboard.overall_status,
            "gates_passed": dashboard.gates_passed,
            "gates_failed": dashboard.gates_failed,
            "gates_warned": dashboard.gates_warned,
            "blocking_failures": dashboard.blocking_failures,
            "gates": [
                {
                    "gate_id": g.gate_id,
                    "name": g.name,
                    "status": g.status,
                    "value": g.value,
                    "threshold": g.threshold,
                    "blocking": g.blocking,
                }
                for g in dashboard.gates
            ],
        },
        "coverage": {
            "by_category": {
                c.category: {
                    "total": c.total,
                    "passed": c.passed,
                    "failed": c.failed,
                    "skipped": c.skipped,
                    "coverage_pct": c.coverage_pct,
                }
                for c in dashboard.coverage_by_category
            },
            "negative_controls": dashboard.negative_controls,
            "overall_percentage": dashboard.overall_coverage_pct,
        },
        "debug_compliance": {
            "enabled": dashboard.debug_enabled,
            "compliance_rate": dashboard.debug_compliance_rate,
            "records_count": dashboard.debug_records_count,
            "by_agent": dashboard.debug_by_agent,
            "by_skill": dashboard.debug_by_skill,
            "validation_errors": dashboard.debug_validation_errors,
        },
        "failures": {
            "total": len(dashboard.failures),
            "by_category": dashboard.failures_by_category,
            "detailed_list": [
                {
                    "scenario_id": f.scenario_id,
                    "error_code": f.error_code,
                    "category": f.category,
                    "message": f.message,
                    "retry_eligible": f.retry_eligible,
                }
                for f in dashboard.failures
            ],
        },
        "perfect_metrics_check": {
            "triggered": dashboard.perfect_metrics_triggered,
            "checks": [
                {
                    "metric": c.metric,
                    "value": c.value,
                    "threshold": c.threshold,
                    "triggered": c.triggered,
                }
                for c in dashboard.perfect_metric_checks
            ],
        },
        "evidence_pack": dashboard.evidence_pack_path,
    }

    # Add regression if baseline exists
    if dashboard.baseline_run_id:
        data["regression"] = {
            "baseline_run_id": dashboard.baseline_run_id,
            "metric_regressions": [
                {
                    "metric": r.metric,
                    "baseline": r.baseline,
                    "current": r.current,
                    "delta": r.delta,
                    "threshold": r.threshold,
                    "status": r.status,
                }
                for r in dashboard.regressions
            ],
            "scenario_changes": dashboard.scenario_regressions,
            "regressions": sum(1 for sr in dashboard.scenario_regressions if sr["change"] == "REGRESSION"),
            "improvements": sum(1 for sr in dashboard.scenario_regressions if sr["change"] == "IMPROVEMENT"),
        }

    return json.dumps(data, indent=2)


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Render /vrs-full-testing dashboard from evidence pack"
    )
    parser.add_argument("evidence_pack", type=Path, help="Path to evidence pack directory")
    parser.add_argument("--output", "-o", type=Path, help="Output file path")
    parser.add_argument("--json", action="store_true", help="Output JSON format instead of Markdown")
    parser.add_argument("--baseline", type=Path, help="Baseline evidence pack for regression analysis")

    args = parser.parse_args()

    # Load evidence pack
    if not args.evidence_pack.exists():
        print(f"Error: Evidence pack not found: {args.evidence_pack}", file=sys.stderr)
        sys.exit(1)

    data = load_evidence_pack(args.evidence_pack)

    # Load baseline if provided
    baseline_data = None
    if args.baseline:
        if not args.baseline.exists():
            print(f"Warning: Baseline pack not found: {args.baseline}", file=sys.stderr)
        else:
            baseline_data = load_evidence_pack(args.baseline)

    # Build dashboard
    dashboard = build_dashboard(data, baseline_data)

    # Render output
    if args.json:
        output = render_json(dashboard)
        default_ext = ".json"
    else:
        output = render_markdown(dashboard)
        default_ext = ".md"

    # Write output
    if args.output:
        output_path = args.output
    else:
        output_path = args.evidence_pack / f"full-testing-dashboard{default_ext}"

    output_path.write_text(output)
    print(f"Dashboard written to: {output_path}")

    # Exit with appropriate code
    if dashboard.overall_status == "FAIL":
        sys.exit(1)
    elif dashboard.overall_status == "WARN":
        sys.exit(0)  # Warnings don't fail
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
