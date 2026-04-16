#!/usr/bin/env python3
"""
Gate Evaluator for /vrs-full-testing Results

Evaluates QA gates against evidence packs and outputs pass/fail status
with machine-readable JSON and human-readable summary.

Exit codes:
- 0: All gates passed (GA eligible)
- 1: One or more blocking gates failed
- 2: Configuration or input error

Usage:
    python full_testing_gate_check.py evidence/
    python full_testing_gate_check.py evidence/ --json
    python full_testing_gate_check.py evidence/ --gates G01,G02,G03
    python full_testing_gate_check.py evidence/ --baseline prior-evidence/
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


# =============================================================================
# Gate Definitions (from 07.3.1.5-GATES.md)
# =============================================================================
GATE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "G01": {
        "name": "Stage Completion",
        "description": "All test suites completed successfully",
        "metric_source": "manifest.json",
        "threshold": "All suites passed",
        "blocking": True,
        "category": "critical",
    },
    "G02": {
        "name": "Precision",
        "description": "Detection accuracy (minimize false positives)",
        "metric_source": "metrics/accuracy.json",
        "threshold": ">= 0.85",
        "threshold_value": 0.85,
        "blocking": True,
        "category": "critical",
    },
    "G03": {
        "name": "Recall",
        "description": "Detection coverage (minimize false negatives)",
        "metric_source": "metrics/accuracy.json",
        "threshold": ">= 0.80",
        "threshold_value": 0.80,
        "blocking": True,
        "category": "critical",
    },
    "G04": {
        "name": "F1 Score",
        "description": "Balanced precision/recall measure",
        "metric_source": "metrics/accuracy.json",
        "threshold": ">= 0.82",
        "threshold_value": 0.82,
        "blocking": True,
        "category": "critical",
    },
    "G05": {
        "name": "Debug Coverage",
        "description": "All agents/skills have debug records",
        "metric_source": "debug/index.json",
        "threshold": "100% coverage",
        "blocking": True,
        "category": "observability",
    },
    "G06": {
        "name": "Tier-C Detection",
        "description": "Label-dependent patterns functional",
        "metric_source": "metrics/accuracy.json",
        "threshold": ">= 1 Tier-C TP",
        "threshold_value": 1,
        "blocking": True,
        "category": "functional",
    },
    "G07": {
        "name": "Economic Context",
        "description": "Oracle/pricing scenarios validated",
        "metric_source": "manifest.json",
        "threshold": ">= 1 oracle scenario passed",
        "threshold_value": 1,
        "blocking": True,
        "category": "functional",
    },
    "G08": {
        "name": "Agent Agreement",
        "description": "Multi-agent debate consistency",
        "metric_source": "metrics/agreement.json",
        "threshold": ">= 0.90",
        "threshold_value": 0.90,
        "blocking": False,
        "category": "quality",
    },
    "G09": {
        "name": "Transcript Validity",
        "description": "All transcripts have valid markers",
        "metric_source": "manifest.json",
        "threshold": "All markers valid",
        "blocking": True,
        "category": "validation",
    },
    "G10": {
        "name": "Duration Validity",
        "description": "No mocked/simulated runs (min 5s)",
        "metric_source": "manifest.json",
        "threshold": "> 5000ms",
        "threshold_value": 5000,
        "blocking": True,
        "category": "validation",
    },
}

# Gate evaluation order (early exit on blocking failures)
GATE_EVALUATION_ORDER = [
    "G09",  # Transcript Validity (pack must be valid to evaluate)
    "G10",  # Duration Validity (no mocked runs)
    "G05",  # Debug Coverage (observability required)
    "G01",  # Stage Completion (all suites passed)
    "G02",  # Precision
    "G03",  # Recall
    "G04",  # F1 Score
    "G06",  # Tier-C Detection
    "G07",  # Economic Context
    "G08",  # Agent Agreement (warning only)
]


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class GateResult:
    """Result of evaluating a single gate."""

    gate_id: str
    name: str
    status: Literal["PASS", "FAIL", "WARN", "SKIP"]
    value: Any = None
    threshold: str = ""
    reason: str = ""
    blocking: bool = True
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "gate_id": self.gate_id,
            "name": self.name,
            "status": self.status,
            "value": self.value,
            "threshold": self.threshold,
            "reason": self.reason,
            "blocking": self.blocking,
            "details": self.details,
        }


@dataclass
class GateEvaluationReport:
    """Complete gate evaluation report."""

    ga_gate_status: Literal["PASS", "FAIL", "WARN"]
    gates_passed: list[str] = field(default_factory=list)
    gates_failed: list[str] = field(default_factory=list)
    gates_warned: list[str] = field(default_factory=list)
    gates_skipped: list[str] = field(default_factory=list)
    blocking_failures: int = 0
    warnings: int = 0
    evaluated_at: str = ""
    evidence_pack: str = ""
    results: list[GateResult] = field(default_factory=list)
    regression_check: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "ga_gate_status": self.ga_gate_status,
            "gates_passed": self.gates_passed,
            "gates_failed": self.gates_failed,
            "gates_warned": self.gates_warned,
            "gates_skipped": self.gates_skipped,
            "blocking_failures": self.blocking_failures,
            "warnings": self.warnings,
            "evaluated_at": self.evaluated_at,
            "evidence_pack": self.evidence_pack,
            "results": [r.to_dict() for r in self.results],
            "regression_check": self.regression_check,
        }


# =============================================================================
# File Loading Utilities
# =============================================================================
def load_json_safe(path: Path) -> dict[str, Any] | None:
    """Load JSON file, return None if missing or invalid."""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None


def get_nested(data: dict[str, Any], path: str, default: Any = None) -> Any:
    """Get nested dictionary value using dot notation."""
    keys = path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is None:
            return default
    return current


# =============================================================================
# Individual Gate Evaluators
# =============================================================================
def evaluate_g01_stage_completion(manifest: dict[str, Any]) -> GateResult:
    """G01: All test suites completed successfully."""
    gate_def = GATE_DEFINITIONS["G01"]
    result = GateResult(
        gate_id="G01",
        name=gate_def["name"],
        status="PASS",
        threshold=gate_def["threshold"],
        blocking=gate_def["blocking"],
    )

    suites = manifest.get("suites", {})
    if not suites:
        result.status = "FAIL"
        result.reason = "No suites found in manifest"
        result.value = "0/0"
        return result

    failed_suites = []
    passed_count = 0
    total_count = len(suites)

    for suite_id, suite_data in suites.items():
        status = suite_data.get("status", "unknown")
        if status == "passed":
            passed_count += 1
        else:
            failed_suites.append(f"{suite_id}: {status}")

    result.value = f"{passed_count}/{total_count}"
    result.details = {"failed_suites": failed_suites}

    if failed_suites:
        result.status = "FAIL"
        result.reason = f"Suites failed: {', '.join(failed_suites)}"

    return result


def evaluate_g02_precision(accuracy: dict[str, Any]) -> GateResult:
    """G02: Precision >= 0.85."""
    gate_def = GATE_DEFINITIONS["G02"]
    result = GateResult(
        gate_id="G02",
        name=gate_def["name"],
        status="PASS",
        threshold=gate_def["threshold"],
        blocking=gate_def["blocking"],
    )

    precision = get_nested(accuracy, "overall.precision")
    if precision is None:
        result.status = "FAIL"
        result.reason = "Precision metric not found in accuracy.json"
        return result

    result.value = precision
    threshold = gate_def["threshold_value"]

    if precision < threshold:
        result.status = "FAIL"
        result.reason = f"Precision {precision:.3f} < {threshold} threshold"
        # Include top FPs if available
        fps = get_nested(accuracy, "false_positives", [])
        if fps:
            result.details["top_false_positives"] = fps[:5]

    return result


def evaluate_g03_recall(accuracy: dict[str, Any]) -> GateResult:
    """G03: Recall >= 0.80."""
    gate_def = GATE_DEFINITIONS["G03"]
    result = GateResult(
        gate_id="G03",
        name=gate_def["name"],
        status="PASS",
        threshold=gate_def["threshold"],
        blocking=gate_def["blocking"],
    )

    recall = get_nested(accuracy, "overall.recall")
    if recall is None:
        result.status = "FAIL"
        result.reason = "Recall metric not found in accuracy.json"
        return result

    result.value = recall
    threshold = gate_def["threshold_value"]

    if recall < threshold:
        result.status = "FAIL"
        result.reason = f"Recall {recall:.3f} < {threshold} threshold"
        # Include FNs if available
        fns = get_nested(accuracy, "false_negatives", [])
        if fns:
            result.details["false_negatives"] = fns

    return result


def evaluate_g04_f1_score(accuracy: dict[str, Any]) -> GateResult:
    """G04: F1 Score >= 0.82."""
    gate_def = GATE_DEFINITIONS["G04"]
    result = GateResult(
        gate_id="G04",
        name=gate_def["name"],
        status="PASS",
        threshold=gate_def["threshold"],
        blocking=gate_def["blocking"],
    )

    f1_score = get_nested(accuracy, "overall.f1_score")
    if f1_score is None:
        result.status = "FAIL"
        result.reason = "F1 score not found in accuracy.json"
        return result

    result.value = f1_score
    threshold = gate_def["threshold_value"]

    if f1_score < threshold:
        result.status = "FAIL"
        result.reason = f"F1 {f1_score:.3f} < {threshold} threshold"

    return result


def evaluate_g05_debug_coverage(
    manifest: dict[str, Any], debug_index: dict[str, Any] | None
) -> GateResult:
    """G05: 100% debug coverage for all agents."""
    gate_def = GATE_DEFINITIONS["G05"]
    result = GateResult(
        gate_id="G05",
        name=gate_def["name"],
        status="PASS",
        threshold=gate_def["threshold"],
        blocking=gate_def["blocking"],
    )

    # Check manifest debug section
    debug_info = manifest.get("debug", {})
    if not debug_info.get("enabled", False):
        result.status = "FAIL"
        result.reason = "Debug mode not enabled"
        return result

    validation = debug_info.get("validation", {})
    if not validation.get("all_records_valid", False):
        result.status = "FAIL"
        errors = validation.get("validation_errors", [])
        result.reason = f"Debug records invalid: {len(errors)} errors"
        result.details["validation_errors"] = errors[:10]  # Limit output
        return result

    records_count = debug_info.get("records_count", 0)
    result.value = f"{records_count} records"

    if debug_index:
        records = debug_index.get("records", [])
        failed_records = [r for r in records if r.get("status") != "success"]
        if failed_records:
            result.status = "FAIL"
            result.reason = f"{len(failed_records)} debug records failed"
            result.details["failed_records"] = [
                r.get("skill_or_agent") for r in failed_records
            ]

    return result


def evaluate_g06_tier_c_detection(accuracy: dict[str, Any]) -> GateResult:
    """G06: At least 1 Tier-C true positive."""
    gate_def = GATE_DEFINITIONS["G06"]
    result = GateResult(
        gate_id="G06",
        name=gate_def["name"],
        status="PASS",
        threshold=gate_def["threshold"],
        blocking=gate_def["blocking"],
    )

    tier_c = get_nested(accuracy, "by_category.tier_c_labels", {})
    true_positives = tier_c.get("true_positives", 0)
    result.value = true_positives

    if true_positives < 1:
        result.status = "FAIL"
        result.reason = "No Tier-C true positives detected"
        result.details["tier_c_stats"] = tier_c

    return result


def evaluate_g07_economic_context(manifest: dict[str, Any]) -> GateResult:
    """G07: At least 1 oracle/pricing scenario passed."""
    gate_def = GATE_DEFINITIONS["G07"]
    result = GateResult(
        gate_id="G07",
        name=gate_def["name"],
        status="PASS",
        threshold=gate_def["threshold"],
        blocking=gate_def["blocking"],
    )

    scenarios = manifest.get("scenarios", [])
    economic_categories = ["oracle", "pricing", "economic"]

    oracle_scenarios = [
        s for s in scenarios if s.get("category") in economic_categories
    ]
    passed_oracle = [s for s in oracle_scenarios if s.get("status") == "passed"]

    result.value = f"{len(passed_oracle)}/{len(oracle_scenarios)}"
    result.details["oracle_scenarios"] = [
        {"id": s.get("id"), "status": s.get("status")} for s in oracle_scenarios
    ]

    if len(passed_oracle) < 1:
        result.status = "FAIL"
        failed = [s for s in oracle_scenarios if s.get("status") != "passed"]
        result.reason = f"No oracle scenarios passed ({len(failed)} failed)"
        result.details["failed_scenarios"] = [s.get("id") for s in failed]

    return result


def evaluate_g08_agent_agreement(agreement: dict[str, Any] | None) -> GateResult:
    """G08: Agent agreement rate >= 0.90 (warning only)."""
    gate_def = GATE_DEFINITIONS["G08"]
    result = GateResult(
        gate_id="G08",
        name=gate_def["name"],
        status="PASS",
        threshold=gate_def["threshold"],
        blocking=gate_def["blocking"],
    )

    if agreement is None:
        result.status = "WARN"
        result.reason = "Agreement metrics not found"
        return result

    rate = agreement.get("overall_agreement_rate", 0)
    result.value = rate
    threshold = gate_def["threshold_value"]

    if rate < threshold:
        result.status = "WARN"
        result.reason = f"Agreement {rate:.3f} < {threshold} threshold"
        # Include disagreement scenarios
        by_debate = agreement.get("by_debate", [])
        disagreements = [d for d in by_debate if not d.get("agreement", True)]
        result.details["disagreement_scenarios"] = [
            d.get("scenario") for d in disagreements
        ]

    return result


def evaluate_g09_transcript_validity(manifest: dict[str, Any]) -> GateResult:
    """G09: All transcripts have valid markers."""
    gate_def = GATE_DEFINITIONS["G09"]
    result = GateResult(
        gate_id="G09",
        name=gate_def["name"],
        status="PASS",
        threshold=gate_def["threshold"],
        blocking=gate_def["blocking"],
    )

    validation = manifest.get("validation", {})

    if not validation.get("pack_valid", False):
        result.status = "FAIL"
        errors = validation.get("errors", [])
        result.reason = "Evidence pack invalid"
        result.details["errors"] = errors[:10]
        return result

    if not validation.get("all_transcripts_present", False):
        result.status = "FAIL"
        result.reason = "Missing transcripts"
        return result

    if not validation.get("all_markers_valid", False):
        result.status = "FAIL"
        result.reason = "Invalid markers in transcripts"
        return result

    # Count valid transcripts
    scenarios = manifest.get("scenarios", [])
    result.value = f"{len(scenarios)} valid"

    return result


def evaluate_g10_duration_validity(manifest: dict[str, Any]) -> GateResult:
    """G10: All scenarios have duration > 5000ms."""
    gate_def = GATE_DEFINITIONS["G10"]
    result = GateResult(
        gate_id="G10",
        name=gate_def["name"],
        status="PASS",
        threshold=gate_def["threshold"],
        blocking=gate_def["blocking"],
    )

    scenarios = manifest.get("scenarios", [])
    if not scenarios:
        result.status = "FAIL"
        result.reason = "No scenarios found in manifest"
        return result

    min_duration = gate_def["threshold_value"]
    invalid_scenarios = []

    for scenario in scenarios:
        duration = scenario.get("duration_ms", 0)
        if duration <= min_duration:
            invalid_scenarios.append(
                {"id": scenario.get("id"), "duration_ms": duration}
            )

    result.value = f"All > {min_duration}ms"

    if invalid_scenarios:
        result.status = "FAIL"
        result.reason = f"{len(invalid_scenarios)} scenarios with invalid duration"
        result.value = f"{len(invalid_scenarios)} invalid"
        result.details["invalid_scenarios"] = invalid_scenarios

    return result


# =============================================================================
# Regression Check
# =============================================================================
def check_regression(
    current_accuracy: dict[str, Any], baseline_path: Path
) -> dict[str, Any] | None:
    """Compare current metrics against baseline for regression detection."""
    baseline_accuracy = load_json_safe(baseline_path / "metrics" / "accuracy.json")
    if baseline_accuracy is None:
        return None

    result = {
        "baseline_run_id": baseline_path.name,
        "checks": [],
        "status": "PASS",
    }

    # Regression thresholds from GATES.md
    thresholds = {
        "precision": 0.05,  # Max -5% regression
        "recall": 0.05,
        "f1_score": 0.03,  # Max -3% regression
    }

    for metric, max_regression in thresholds.items():
        current_val = get_nested(current_accuracy, f"overall.{metric}", 0)
        baseline_val = get_nested(baseline_accuracy, f"overall.{metric}", 0)
        delta = current_val - baseline_val

        check = {
            "metric": metric,
            "baseline_value": baseline_val,
            "current_value": current_val,
            "delta": delta,
            "threshold": max_regression,
            "status": "PASS" if delta >= -max_regression else "FAIL",
        }
        result["checks"].append(check)

        if check["status"] == "FAIL":
            result["status"] = "FAIL"

    return result


# =============================================================================
# Main Evaluation Logic
# =============================================================================
def evaluate_gates(
    evidence_pack_path: Path,
    gates_to_check: list[str] | None = None,
    baseline_path: Path | None = None,
    early_exit: bool = True,
) -> GateEvaluationReport:
    """
    Evaluate all QA gates against an evidence pack.

    Args:
        evidence_pack_path: Path to evidence pack directory
        gates_to_check: Optional list of specific gate IDs to check
        baseline_path: Optional path to baseline for regression check
        early_exit: If True, stop on first blocking failure

    Returns:
        GateEvaluationReport with all results
    """
    report = GateEvaluationReport(
        ga_gate_status="PASS",
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        evidence_pack=evidence_pack_path.name,
    )

    # Load required files
    manifest = load_json_safe(evidence_pack_path / "manifest.json")
    accuracy = load_json_safe(evidence_pack_path / "metrics" / "accuracy.json")
    agreement = load_json_safe(evidence_pack_path / "metrics" / "agreement.json")
    debug_index = load_json_safe(evidence_pack_path / "debug" / "index.json")

    if manifest is None:
        report.ga_gate_status = "FAIL"
        report.results.append(
            GateResult(
                gate_id="MANIFEST",
                name="Manifest Check",
                status="FAIL",
                reason=f"manifest.json not found in {evidence_pack_path}",
                blocking=True,
            )
        )
        report.blocking_failures = 1
        return report

    # Determine which gates to evaluate
    gates_order = gates_to_check if gates_to_check else GATE_EVALUATION_ORDER

    # Evaluate each gate
    for gate_id in gates_order:
        if gate_id not in GATE_DEFINITIONS:
            report.gates_skipped.append(gate_id)
            continue

        result: GateResult

        # Route to appropriate evaluator
        if gate_id == "G01":
            result = evaluate_g01_stage_completion(manifest)
        elif gate_id == "G02":
            if accuracy is None:
                result = GateResult(
                    gate_id="G02",
                    name="Precision",
                    status="FAIL",
                    reason="accuracy.json not found",
                    blocking=True,
                )
            else:
                result = evaluate_g02_precision(accuracy)
        elif gate_id == "G03":
            if accuracy is None:
                result = GateResult(
                    gate_id="G03",
                    name="Recall",
                    status="FAIL",
                    reason="accuracy.json not found",
                    blocking=True,
                )
            else:
                result = evaluate_g03_recall(accuracy)
        elif gate_id == "G04":
            if accuracy is None:
                result = GateResult(
                    gate_id="G04",
                    name="F1 Score",
                    status="FAIL",
                    reason="accuracy.json not found",
                    blocking=True,
                )
            else:
                result = evaluate_g04_f1_score(accuracy)
        elif gate_id == "G05":
            result = evaluate_g05_debug_coverage(manifest, debug_index)
        elif gate_id == "G06":
            if accuracy is None:
                result = GateResult(
                    gate_id="G06",
                    name="Tier-C Detection",
                    status="FAIL",
                    reason="accuracy.json not found",
                    blocking=True,
                )
            else:
                result = evaluate_g06_tier_c_detection(accuracy)
        elif gate_id == "G07":
            result = evaluate_g07_economic_context(manifest)
        elif gate_id == "G08":
            result = evaluate_g08_agent_agreement(agreement)
        elif gate_id == "G09":
            result = evaluate_g09_transcript_validity(manifest)
        elif gate_id == "G10":
            result = evaluate_g10_duration_validity(manifest)
        else:
            result = GateResult(
                gate_id=gate_id,
                name="Unknown",
                status="SKIP",
                reason=f"No evaluator for gate {gate_id}",
                blocking=False,
            )

        report.results.append(result)

        # Categorize result
        if result.status == "PASS":
            report.gates_passed.append(gate_id)
        elif result.status == "FAIL":
            report.gates_failed.append(gate_id)
            if result.blocking:
                report.blocking_failures += 1
                report.ga_gate_status = "FAIL"
                if early_exit:
                    # Mark remaining gates as skipped
                    remaining = gates_order[gates_order.index(gate_id) + 1 :]
                    report.gates_skipped.extend(remaining)
                    break
        elif result.status == "WARN":
            report.gates_warned.append(gate_id)
            report.warnings += 1
            if report.ga_gate_status == "PASS":
                report.ga_gate_status = "WARN"
        elif result.status == "SKIP":
            report.gates_skipped.append(gate_id)

    # Regression check if baseline provided
    if baseline_path and accuracy:
        report.regression_check = check_regression(accuracy, baseline_path)
        if report.regression_check and report.regression_check["status"] == "FAIL":
            report.ga_gate_status = "FAIL"
            report.blocking_failures += 1

    return report


# =============================================================================
# Report Output
# =============================================================================
def print_markdown_report(report: GateEvaluationReport) -> None:
    """Print report in markdown format (human-readable)."""
    print("# /vrs-full-testing Gate Report")
    print()
    print(f"**Run ID:** {report.evidence_pack}")
    print(f"**Evaluated:** {report.evaluated_at}")
    print(f"**Status:** {report.ga_gate_status}")
    print()

    print("## Gate Results")
    print()
    print("| Gate | Name | Status | Value | Threshold |")
    print("|------|------|--------|-------|-----------|")

    for result in report.results:
        status_emoji = {
            "PASS": "PASS",
            "FAIL": "FAIL",
            "WARN": "WARN",
            "SKIP": "SKIP",
        }.get(result.status, "?")

        value_str = str(result.value) if result.value is not None else "-"
        print(
            f"| {result.gate_id} | {result.name} | {status_emoji} | "
            f"{value_str} | {result.threshold} |"
        )

    print()
    print("## Summary")
    print()
    print(f"- **Passed:** {len(report.gates_passed)}/{len(report.results)} gates")
    print(f"- **Warnings:** {report.warnings}")
    print(f"- **Blocking Failures:** {report.blocking_failures}")
    print()
    print(f"**GA Gate Decision:** {report.ga_gate_status}")

    # Print failure details
    if report.gates_failed:
        print()
        print("## Failure Details")
        print()
        for result in report.results:
            if result.status == "FAIL":
                print(f"### {result.gate_id}: {result.name}")
                print()
                print(f"**Reason:** {result.reason}")
                if result.details:
                    print()
                    print("**Details:**")
                    print("```json")
                    print(json.dumps(result.details, indent=2))
                    print("```")
                print()

    # Regression check results
    if report.regression_check:
        print()
        print("## Regression Check")
        print()
        print(f"**Baseline:** {report.regression_check.get('baseline_run_id', 'N/A')}")
        print(f"**Status:** {report.regression_check.get('status', 'N/A')}")
        print()
        print("| Metric | Baseline | Current | Delta | Threshold | Status |")
        print("|--------|----------|---------|-------|-----------|--------|")
        for check in report.regression_check.get("checks", []):
            print(
                f"| {check['metric']} | {check['baseline_value']:.3f} | "
                f"{check['current_value']:.3f} | {check['delta']:+.3f} | "
                f"{check['threshold']} | {check['status']} |"
            )


def print_summary_report(report: GateEvaluationReport) -> None:
    """Print concise summary with failing gate IDs and reasons."""
    print("=" * 70)
    print(f"GATE EVALUATION: {report.ga_gate_status}")
    print("=" * 70)
    print()

    if report.gates_failed:
        print("FAILED GATES:")
        for result in report.results:
            if result.status == "FAIL":
                print(f"  GATE_FAIL: {result.gate_id} - {result.reason}")
        print()

    if report.gates_warned:
        print("WARNINGS:")
        for result in report.results:
            if result.status == "WARN":
                print(f"  GATE_WARN: {result.gate_id} - {result.reason}")
        print()

    print(f"Passed: {len(report.gates_passed)}")
    print(f"Failed: {len(report.gates_failed)}")
    print(f"Warned: {len(report.gates_warned)}")
    print(f"Skipped: {len(report.gates_skipped)}")
    print()
    print(f"GA Decision: {report.ga_gate_status}")


# =============================================================================
# CLI Entry Point
# =============================================================================
def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate QA gates for /vrs-full-testing results"
    )
    parser.add_argument(
        "evidence_pack",
        type=Path,
        help="Path to evidence pack directory",
    )
    parser.add_argument(
        "--gates",
        type=str,
        help="Comma-separated list of gate IDs to check (default: all)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Path to baseline evidence pack for regression check",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Output results as Markdown",
    )
    parser.add_argument(
        "--no-early-exit",
        action="store_true",
        help="Continue evaluating all gates even after blocking failure",
    )

    args = parser.parse_args()

    # Validate evidence pack path
    if not args.evidence_pack.exists():
        print(f"ERROR: Evidence pack not found: {args.evidence_pack}", file=sys.stderr)
        return 2

    # Parse gate list if provided
    gates_to_check = None
    if args.gates:
        gates_to_check = [g.strip() for g in args.gates.split(",")]
        invalid_gates = [g for g in gates_to_check if g not in GATE_DEFINITIONS]
        if invalid_gates:
            print(f"ERROR: Unknown gates: {invalid_gates}", file=sys.stderr)
            return 2

    # Run evaluation
    report = evaluate_gates(
        evidence_pack_path=args.evidence_pack,
        gates_to_check=gates_to_check,
        baseline_path=args.baseline,
        early_exit=not args.no_early_exit,
    )

    # Output results
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    elif args.markdown:
        print_markdown_report(report)
    else:
        print_summary_report(report)

    # Return appropriate exit code
    if report.ga_gate_status == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
