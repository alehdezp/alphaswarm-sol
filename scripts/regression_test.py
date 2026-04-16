#!/usr/bin/env python3
"""
Run regression test comparing current metrics against baseline.

Usage:
    uv run python scripts/regression_test.py --baseline .vrs/baselines/ga-baseline.json --current .vrs/ga-metrics/aggregated-metrics.json
"""

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class RegressionResult:
    """Result of regression comparison."""
    metric: str
    baseline: float
    current: float
    threshold: float
    passed: bool
    delta: float
    delta_pct: float


def compare_metrics(baseline: Dict, current: Dict) -> List[RegressionResult]:
    """Compare current metrics against baseline."""
    results = []
    thresholds = baseline.get("regression_thresholds", {})

    comparisons = [
        ("precision", "precision_max_drop", baseline["metrics"]["precision"], current["overall_precision"]),
        ("recall", "recall_max_drop", baseline["metrics"]["recall"], current["overall_recall"]),
        ("f1_score", "f1_max_drop", baseline["metrics"]["f1_score"], current["overall_f1"]),
    ]

    for metric, threshold_key, base_val, curr_val in comparisons:
        threshold = thresholds.get(threshold_key, 0.05)
        delta = curr_val - base_val
        delta_pct = (delta / base_val * 100) if base_val > 0 else 0

        # Passed if current >= baseline - threshold
        passed = curr_val >= (base_val - threshold)

        results.append(RegressionResult(
            metric=metric,
            baseline=base_val,
            current=curr_val,
            threshold=threshold,
            passed=passed,
            delta=delta,
            delta_pct=delta_pct,
        ))

    return results


def compare_by_type(baseline: Dict, current: Dict) -> Dict[str, List[RegressionResult]]:
    """Compare metrics by vulnerability type."""
    base_types = baseline.get("by_vulnerability_type", {})
    curr_types = current.get("by_vulnerability_type", {})

    results = {}

    for vuln_type in set(base_types.keys()) | set(curr_types.keys()):
        base_data = base_types.get(vuln_type, {})
        curr_data = curr_types.get(vuln_type, {})

        type_results = []
        for metric in ["precision", "recall", "f1_score"]:
            base_val = base_data.get(metric, 0)
            curr_val = curr_data.get(metric, 0)
            delta = curr_val - base_val

            # Use 10% threshold for per-type comparisons
            passed = delta >= -0.10

            type_results.append(RegressionResult(
                metric=metric,
                baseline=base_val,
                current=curr_val,
                threshold=0.10,
                passed=passed,
                delta=delta,
                delta_pct=(delta / base_val * 100) if base_val > 0 else 0,
            ))

        results[vuln_type] = type_results

    return results


def generate_report(
    baseline: Dict,
    current: Dict,
    overall_results: List[RegressionResult],
    type_results: Dict[str, List[RegressionResult]]
) -> str:
    """Generate regression test report."""
    all_passed = all(r.passed for r in overall_results)

    lines = [
        "=" * 60,
        "REGRESSION TEST REPORT",
        "=" * 60,
        f"Generated: {datetime.now().isoformat()}",
        "",
        f"Baseline commit: {baseline['git']['commit'][:8]}...",
        f"Baseline date:   {baseline['created_at']}",
        "",
        "## OVERALL METRICS",
        "",
        "| Metric | Baseline | Current | Delta | Threshold | Status |",
        "|--------|----------|---------|-------|-----------|--------|",
    ]

    for r in overall_results:
        status = "PASS" if r.passed else "FAIL"
        delta_str = f"{r.delta:+.2%} ({r.delta_pct:+.1f}%)"
        lines.append(
            f"| {r.metric} | {r.baseline:.2%} | {r.current:.2%} | {delta_str} | "
            f"-{r.threshold:.0%} | {status} |"
        )

    lines.extend([
        "",
        "## BY VULNERABILITY TYPE",
        "",
    ])

    for vuln_type, results in sorted(type_results.items()):
        any_fail = any(not r.passed for r in results)
        status = "WARN" if any_fail else "OK"
        lines.append(f"### {vuln_type} ({status})")
        lines.append("")
        lines.append("| Metric | Baseline | Current | Delta |")
        lines.append("|--------|----------|---------|-------|")

        for r in results:
            lines.append(
                f"| {r.metric} | {r.baseline:.2%} | {r.current:.2%} | {r.delta:+.2%} |"
            )
        lines.append("")

    lines.extend([
        "## VERDICT",
        "",
        f"**{'PASSED' if all_passed else 'FAILED'}** - ",
        f"{'No regressions detected' if all_passed else 'Regressions detected in overall metrics'}",
        "",
        "=" * 60,
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run regression test")
    parser.add_argument("--baseline", required=True, help="Path to baseline JSON")
    parser.add_argument("--current", required=True, help="Path to current metrics JSON")
    parser.add_argument("--output", help="Output report file")
    args = parser.parse_args()

    baseline_file = Path(args.baseline)
    current_file = Path(args.current)

    if not baseline_file.exists():
        print(f"ERROR: Baseline not found: {baseline_file}")
        exit(1)

    if not current_file.exists():
        print(f"ERROR: Current metrics not found: {current_file}")
        exit(1)

    baseline = json.loads(baseline_file.read_text())
    current = json.loads(current_file.read_text())

    # Run comparisons
    overall_results = compare_metrics(baseline, current)
    type_results = compare_by_type(baseline, current)

    # Generate report
    report = generate_report(baseline, current, overall_results, type_results)

    if args.output:
        Path(args.output).write_text(report)
        print(f"Report saved to: {args.output}")
    else:
        print(report)

    # Exit code based on regression status
    all_passed = all(r.passed for r in overall_results)
    if all_passed:
        print("\nREGRESSION TEST: PASSED")
        exit(0)
    else:
        print("\nREGRESSION TEST: FAILED")
        exit(1)


if __name__ == "__main__":
    main()
