#!/usr/bin/env python3
"""
Collect and compare metrics from A/B test runs.

This script aggregates metrics from solo and swarm mode test runs and
computes comparison statistics to quantify the value of multi-agent debate.

Usage:
    uv run python scripts/collect_ab_metrics.py \
        --solo-worktrees "wt1,wt2,wt3" \
        --swarm-worktrees "wt1,wt2,wt3" \
        --output results.json

Output:
    JSON with aggregated metrics for each mode and comparison statistics.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class WorktreeMetrics:
    """Metrics from a single worktree run."""
    worktree: str
    mode: str
    duration_seconds: int
    ground_truth_count: int
    findings_count: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    error: str | None = None


@dataclass
class AggregateMetrics:
    """Aggregated metrics across multiple worktrees."""
    mode: str
    total_runs: int
    total_ground_truth: int
    total_findings: int
    total_true_positives: int
    total_false_positives: int
    total_false_negatives: int
    precision: float
    recall: float
    f1_score: float
    total_duration_seconds: int
    avg_duration_seconds: float


@dataclass
class ModeComparison:
    """Comparison of solo vs swarm mode."""
    precision_delta: float
    recall_delta: float
    f1_delta: float
    fp_reduction: int
    fn_reduction: int
    time_overhead_ratio: float
    token_overhead_ratio: float  # Placeholder for future token analysis
    swarm_improves_precision: bool
    swarm_improves_recall: bool
    swarm_improves_f1: bool
    swarm_reduces_fp: bool
    swarm_reduces_fn: bool


def load_worktree_metrics(worktree_name: str, mode: str) -> WorktreeMetrics:
    """Load metrics from a single worktree."""
    base_path = Path("/tmp/vrs-worktrees") / worktree_name

    # Default values
    metrics = WorktreeMetrics(
        worktree=worktree_name,
        mode=mode,
        duration_seconds=0,
        ground_truth_count=0,
        findings_count=0,
        true_positives=0,
        false_positives=0,
        false_negatives=0,
        precision=0.0,
        recall=0.0,
        f1_score=0.0,
        error=None,
    )

    # Load run info
    run_info_path = base_path / "run-info.json"
    if run_info_path.exists():
        try:
            run_info = json.loads(run_info_path.read_text())
            metrics.duration_seconds = run_info.get("duration_seconds", 0)
        except (json.JSONDecodeError, KeyError) as e:
            metrics.error = f"Failed to load run-info.json: {e}"
    else:
        metrics.error = "run-info.json not found"

    # Load comparison metrics
    metrics_path = base_path / "metrics.json"
    if metrics_path.exists():
        try:
            data = json.loads(metrics_path.read_text())
            metrics.ground_truth_count = data.get("ground_truth_count", 0)
            metrics.findings_count = data.get("findings_count", 0)
            metrics.true_positives = data.get("true_positives", 0)
            metrics.false_positives = data.get("false_positives", 0)
            metrics.false_negatives = data.get("false_negatives", 0)
            metrics.precision = data.get("precision", 0.0)
            metrics.recall = data.get("recall", 0.0)
            metrics.f1_score = data.get("f1_score", 0.0)
            if "error" in data:
                metrics.error = data["error"]
        except (json.JSONDecodeError, KeyError) as e:
            metrics.error = f"Failed to load metrics.json: {e}"
    elif metrics.error is None:
        metrics.error = "metrics.json not found"

    return metrics


def aggregate_metrics(worktree_names: list[str], mode: str) -> tuple[AggregateMetrics, list[WorktreeMetrics]]:
    """Aggregate metrics across multiple worktrees."""
    all_metrics: list[WorktreeMetrics] = []

    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_gt = 0
    total_findings = 0
    total_duration = 0

    for wt_name in worktree_names:
        m = load_worktree_metrics(wt_name.strip(), mode)
        all_metrics.append(m)

        total_tp += m.true_positives
        total_fp += m.false_positives
        total_fn += m.false_negatives
        total_gt += m.ground_truth_count
        total_findings += m.findings_count
        total_duration += m.duration_seconds

    # Compute aggregate precision/recall/F1
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    aggregate = AggregateMetrics(
        mode=mode,
        total_runs=len(worktree_names),
        total_ground_truth=total_gt,
        total_findings=total_findings,
        total_true_positives=total_tp,
        total_false_positives=total_fp,
        total_false_negatives=total_fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1_score=round(f1, 4),
        total_duration_seconds=total_duration,
        avg_duration_seconds=round(total_duration / len(worktree_names), 2) if worktree_names else 0,
    )

    return aggregate, all_metrics


def compare_modes(solo: AggregateMetrics, swarm: AggregateMetrics) -> ModeComparison:
    """Compare solo vs swarm mode results."""
    # Avoid division by zero for time overhead
    solo_duration = max(solo.total_duration_seconds, 1)

    return ModeComparison(
        precision_delta=round(swarm.precision - solo.precision, 4),
        recall_delta=round(swarm.recall - solo.recall, 4),
        f1_delta=round(swarm.f1_score - solo.f1_score, 4),
        fp_reduction=solo.total_false_positives - swarm.total_false_positives,
        fn_reduction=solo.total_false_negatives - swarm.total_false_negatives,
        time_overhead_ratio=round(swarm.total_duration_seconds / solo_duration, 2),
        token_overhead_ratio=0.0,  # Placeholder - requires transcript token counting
        swarm_improves_precision=swarm.precision > solo.precision,
        swarm_improves_recall=swarm.recall > solo.recall,
        swarm_improves_f1=swarm.f1_score > solo.f1_score,
        swarm_reduces_fp=swarm.total_false_positives < solo.total_false_positives,
        swarm_reduces_fn=swarm.total_false_negatives < solo.total_false_negatives,
    )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect and compare metrics from A/B test runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --solo-worktrees "wt1,wt2" --swarm-worktrees "wt3,wt4" --output results.json
    %(prog)s --solo-worktrees "ab-solo-naive-receiver,ab-solo-vault" --swarm-worktrees "ab-swarm-naive-receiver,ab-swarm-vault" --output comparison.json
        """,
    )
    parser.add_argument(
        "--solo-worktrees",
        required=True,
        help="Comma-separated list of solo mode worktree names",
    )
    parser.add_argument(
        "--swarm-worktrees",
        required=True,
        help="Comma-separated list of swarm mode worktree names",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file path",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output",
    )
    args = parser.parse_args()

    # Parse worktree lists
    solo_wts = [w.strip() for w in args.solo_worktrees.split(",") if w.strip()]
    swarm_wts = [w.strip() for w in args.swarm_worktrees.split(",") if w.strip()]

    if not solo_wts:
        print("ERROR: No solo worktrees specified", file=sys.stderr)
        return 1
    if not swarm_wts:
        print("ERROR: No swarm worktrees specified", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"Loading {len(solo_wts)} solo worktrees...", file=sys.stderr)

    solo_agg, solo_details = aggregate_metrics(solo_wts, "solo")

    if args.verbose:
        print(f"Loading {len(swarm_wts)} swarm worktrees...", file=sys.stderr)

    swarm_agg, swarm_details = aggregate_metrics(swarm_wts, "swarm")

    # Compare modes
    comparison = compare_modes(solo_agg, swarm_agg)

    # Build result
    result = {
        "solo": {
            "aggregate": asdict(solo_agg),
            "per_worktree": [asdict(m) for m in solo_details],
        },
        "swarm": {
            "aggregate": asdict(swarm_agg),
            "per_worktree": [asdict(m) for m in swarm_details],
        },
        "comparison": asdict(comparison),
        "summary": {
            "recommendation": "Use SWARM mode for production audits"
                if comparison.swarm_improves_f1
                else "SOLO mode may be sufficient",
            "f1_improvement": f"{comparison.f1_delta:+.2%}",
            "time_overhead": f"{comparison.time_overhead_ratio:.1f}x",
            "fp_reduction": comparison.fp_reduction,
            "fn_reduction": comparison.fn_reduction,
        },
    }

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2))

    # Print to stdout as well
    print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
