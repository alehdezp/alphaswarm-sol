#!/usr/bin/env python3
"""
Aggregate metrics from all Wave 2 test results.

Usage:
    uv run python scripts/aggregate_metrics.py --results-dir .vrs/testing/results/
    uv run python scripts/aggregate_metrics.py --results-dir .vrs/testing/results/ --output .vrs/ga-metrics.json
"""

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import yaml


@dataclass
class TestMetrics:
    """Metrics from a single test run."""
    test_id: str
    fixture: str
    ground_truth_source: str
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    duration_ms: float
    tp_by_type: Dict[str, int] = field(default_factory=dict)
    fp_by_type: Dict[str, int] = field(default_factory=dict)
    fn_by_type: Dict[str, int] = field(default_factory=dict)


@dataclass
class AggregatedMetrics:
    """Aggregated metrics across all tests."""
    total_tests: int
    total_true_positives: int
    total_false_positives: int
    total_false_negatives: int
    overall_precision: float
    overall_recall: float
    overall_f1: float
    total_duration_ms: float
    by_vulnerability_type: Dict[str, Dict] = field(default_factory=dict)
    by_ground_truth_source: Dict[str, Dict] = field(default_factory=dict)
    tests: List[TestMetrics] = field(default_factory=list)


def load_test_result(result_file: Path) -> Optional[TestMetrics]:
    """Load metrics from a single test result file."""
    try:
        data = json.loads(result_file.read_text())

        # Validate required fields
        required = ["test_id", "true_positives", "false_positives", "false_negatives"]
        if not all(k in data for k in required):
            print(f"WARNING: Missing required fields in {result_file}")
            return None

        tp = data["true_positives"]
        fp = data["false_positives"]
        fn = data["false_negatives"]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return TestMetrics(
            test_id=data["test_id"],
            fixture=data.get("fixture", "unknown"),
            ground_truth_source=data.get("ground_truth_source", "unknown"),
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            duration_ms=data.get("duration_ms", 0),
            tp_by_type=data.get("tp_by_type", {}),
            fp_by_type=data.get("fp_by_type", {}),
            fn_by_type=data.get("fn_by_type", {}),
        )
    except Exception as e:
        print(f"ERROR loading {result_file}: {e}")
        return None


def aggregate_by_vulnerability_type(tests: List[TestMetrics]) -> Dict[str, Dict]:
    """Aggregate metrics by vulnerability type."""
    by_type = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    for test in tests:
        for vuln_type, count in test.tp_by_type.items():
            by_type[vuln_type]["tp"] += count
        for vuln_type, count in test.fp_by_type.items():
            by_type[vuln_type]["fp"] += count
        for vuln_type, count in test.fn_by_type.items():
            by_type[vuln_type]["fn"] += count

    result = {}
    for vuln_type, counts in by_type.items():
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        result[vuln_type] = {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        }

    return result


def aggregate_by_source(tests: List[TestMetrics]) -> Dict[str, Dict]:
    """Aggregate metrics by ground truth source."""
    by_source = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "count": 0})

    for test in tests:
        source = test.ground_truth_source
        by_source[source]["tp"] += test.true_positives
        by_source[source]["fp"] += test.false_positives
        by_source[source]["fn"] += test.false_negatives
        by_source[source]["count"] += 1

    result = {}
    for source, counts in by_source.items():
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        result[source] = {
            "tests_count": counts["count"],
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        }

    return result


def aggregate_metrics(results_dir: Path) -> AggregatedMetrics:
    """Aggregate all test metrics."""
    # Find all result files
    result_files = list(results_dir.glob("**/metrics.json"))

    if not result_files:
        # Also try test-specific result files
        result_files = list(results_dir.glob("**/test-*.json"))

    if not result_files:
        raise FileNotFoundError(f"No result files found in {results_dir}")

    print(f"Found {len(result_files)} result files")

    # Load all tests
    tests = []
    for rf in result_files:
        test = load_test_result(rf)
        if test:
            tests.append(test)

    if not tests:
        raise ValueError("No valid test results found")

    # Calculate totals
    total_tp = sum(t.true_positives for t in tests)
    total_fp = sum(t.false_positives for t in tests)
    total_fn = sum(t.false_negatives for t in tests)
    total_duration = sum(t.duration_ms for t in tests)

    # Calculate overall metrics
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return AggregatedMetrics(
        total_tests=len(tests),
        total_true_positives=total_tp,
        total_false_positives=total_fp,
        total_false_negatives=total_fn,
        overall_precision=round(precision, 4),
        overall_recall=round(recall, 4),
        overall_f1=round(f1, 4),
        total_duration_ms=total_duration,
        by_vulnerability_type=aggregate_by_vulnerability_type(tests),
        by_ground_truth_source=aggregate_by_source(tests),
        tests=tests,
    )


def generate_report(metrics: AggregatedMetrics) -> str:
    """Generate human-readable metrics report."""
    lines = [
        "=" * 60,
        "ALPHASWARM GA VALIDATION METRICS REPORT",
        "=" * 60,
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## OVERALL METRICS",
        "",
        f"| Metric | Value | Target | Status |",
        f"|--------|-------|--------|--------|",
        f"| Tests Run | {metrics.total_tests} | - | - |",
        f"| True Positives | {metrics.total_true_positives} | - | - |",
        f"| False Positives | {metrics.total_false_positives} | - | - |",
        f"| False Negatives | {metrics.total_false_negatives} | - | - |",
        f"| **Precision** | **{metrics.overall_precision:.2%}** | >= 70% | {'PASS' if metrics.overall_precision >= 0.70 else 'FAIL'} |",
        f"| **Recall** | **{metrics.overall_recall:.2%}** | >= 60% | {'PASS' if metrics.overall_recall >= 0.60 else 'FAIL'} |",
        f"| **F1 Score** | **{metrics.overall_f1:.2%}** | >= 65% | {'PASS' if metrics.overall_f1 >= 0.65 else 'FAIL'} |",
        f"| Total Duration | {metrics.total_duration_ms / 1000:.1f}s | - | - |",
        "",
        "## BY VULNERABILITY TYPE",
        "",
        "| Type | TP | FP | FN | Precision | Recall | F1 |",
        "|------|----|----|----|-----------|---------|----|",
    ]

    for vuln_type, data in sorted(metrics.by_vulnerability_type.items()):
        lines.append(
            f"| {vuln_type} | {data['true_positives']} | {data['false_positives']} | "
            f"{data['false_negatives']} | {data['precision']:.2%} | {data['recall']:.2%} | {data['f1_score']:.2%} |"
        )

    lines.extend([
        "",
        "## BY GROUND TRUTH SOURCE",
        "",
        "| Source | Tests | TP | FP | FN | Precision | Recall |",
        "|--------|-------|----|----|----|-----------|---------| ",
    ])

    for source, data in sorted(metrics.by_ground_truth_source.items()):
        lines.append(
            f"| {source} | {data['tests_count']} | {data['true_positives']} | {data['false_positives']} | "
            f"{data['false_negatives']} | {data['precision']:.2%} | {data['recall']:.2%} |"
        )

    lines.extend([
        "",
        "## INDIVIDUAL TEST RESULTS",
        "",
        "| Test | Fixture | TP | FP | FN | Precision | Recall | Duration |",
        "|------|---------|----|----|----|-----------|---------|---------| ",
    ])

    for test in metrics.tests:
        lines.append(
            f"| {test.test_id} | {test.fixture} | {test.true_positives} | {test.false_positives} | "
            f"{test.false_negatives} | {test.precision:.2%} | {test.recall:.2%} | {test.duration_ms/1000:.1f}s |"
        )

    lines.extend([
        "",
        "=" * 60,
        "END OF REPORT",
        "=" * 60,
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Aggregate GA validation metrics")
    parser.add_argument("--results-dir", required=True, help="Directory containing test results")
    parser.add_argument("--output", help="Output JSON file for aggregated metrics")
    parser.add_argument("--report", help="Output markdown report file")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)

    if not results_dir.exists():
        print(f"ERROR: Results directory does not exist: {results_dir}")
        exit(1)

    # Aggregate metrics
    metrics = aggregate_metrics(results_dir)

    # Output JSON
    output_data = {
        "generated_at": datetime.now().isoformat(),
        "total_tests": metrics.total_tests,
        "total_true_positives": metrics.total_true_positives,
        "total_false_positives": metrics.total_false_positives,
        "total_false_negatives": metrics.total_false_negatives,
        "overall_precision": metrics.overall_precision,
        "overall_recall": metrics.overall_recall,
        "overall_f1": metrics.overall_f1,
        "total_duration_ms": metrics.total_duration_ms,
        "by_vulnerability_type": metrics.by_vulnerability_type,
        "by_ground_truth_source": metrics.by_ground_truth_source,
        "tests": [
            {
                "test_id": t.test_id,
                "fixture": t.fixture,
                "ground_truth_source": t.ground_truth_source,
                "true_positives": t.true_positives,
                "false_positives": t.false_positives,
                "false_negatives": t.false_negatives,
                "precision": t.precision,
                "recall": t.recall,
                "f1_score": t.f1_score,
                "duration_ms": t.duration_ms,
            }
            for t in metrics.tests
        ],
        "ga_gate_passed": (
            metrics.overall_precision >= 0.70 and
            metrics.overall_recall >= 0.60 and
            metrics.overall_f1 >= 0.65
        ),
    }

    if args.output:
        Path(args.output).write_text(json.dumps(output_data, indent=2))
        print(f"Metrics saved to: {args.output}")
    else:
        print(json.dumps(output_data, indent=2))

    # Generate report
    report = generate_report(metrics)

    if args.report:
        Path(args.report).write_text(report)
        print(f"Report saved to: {args.report}")
    else:
        print("\n" + report)

    # Exit code based on GA gate
    if output_data["ga_gate_passed"]:
        print("\n** GA GATE: PASSED **")
        exit(0)
    else:
        print("\n** GA GATE: FAILED **")
        exit(1)


if __name__ == "__main__":
    main()
