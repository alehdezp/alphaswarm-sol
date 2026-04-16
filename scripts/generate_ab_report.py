#!/usr/bin/env python3
"""
Generate A/B comparison report in markdown.

This script takes the output from collect_ab_metrics.py and generates
a human-readable markdown report comparing solo vs swarm mode performance.

Usage:
    uv run python scripts/generate_ab_report.py \
        --results results.json \
        --output report.md

Output:
    Markdown report with tables comparing precision, recall, F1, FP/FN,
    timing overhead, and a recommendation.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def generate_report(results: dict) -> str:
    """Generate markdown report from A/B results."""
    solo = results["solo"]["aggregate"]
    swarm = results["swarm"]["aggregate"]
    comp = results["comparison"]
    summary = results.get("summary", {})

    # Generate per-worktree tables
    solo_details = results["solo"].get("per_worktree", [])
    swarm_details = results["swarm"].get("per_worktree", [])

    solo_table = generate_worktree_table(solo_details, "Solo")
    swarm_table = generate_worktree_table(swarm_details, "Swarm")

    # Determine verdicts
    precision_verdict = "SWARM BETTER" if comp["swarm_improves_precision"] else "SOLO BETTER"
    recall_verdict = "SWARM BETTER" if comp["swarm_improves_recall"] else "SOLO BETTER"
    f1_verdict = "SWARM BETTER" if comp["swarm_improves_f1"] else "SOLO BETTER"

    # Generate recommendation
    if comp["swarm_improves_f1"]:
        recommendation = "**Recommendation:** Use SWARM mode for production audits"
        recommendation_reason = "Multi-agent debate provides measurable accuracy improvement."
    elif comp["f1_delta"] >= -0.05 and comp.get("swarm_reduces_fp", False):
        recommendation = "**Recommendation:** Consider SWARM mode for high-stakes audits"
        recommendation_reason = "While F1 improvement is minimal, debate reduces false positives."
    else:
        recommendation = "**Recommendation:** SOLO mode may be sufficient for quick checks"
        recommendation_reason = "Swarm overhead not justified by accuracy gains."

    report = f"""# A/B Comparison Report: Solo vs Swarm Mode

**Generated:** {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}

---

## Executive Summary

| Metric | Solo Mode | Swarm Mode | Delta | Verdict |
|--------|-----------|------------|-------|---------|
| Precision | {solo['precision']:.2%} | {swarm['precision']:.2%} | {comp['precision_delta']:+.2%} | {precision_verdict} |
| Recall | {solo['recall']:.2%} | {swarm['recall']:.2%} | {comp['recall_delta']:+.2%} | {recall_verdict} |
| F1 Score | {solo['f1_score']:.2%} | {swarm['f1_score']:.2%} | {comp['f1_delta']:+.2%} | {f1_verdict} |

{recommendation}
{recommendation_reason}

---

## False Positive/Negative Analysis

| Metric | Solo Mode | Swarm Mode | Reduction |
|--------|-----------|------------|-----------|
| False Positives | {solo['total_false_positives']} | {swarm['total_false_positives']} | {comp['fp_reduction']:+d} |
| False Negatives | {solo['total_false_negatives']} | {swarm['total_false_negatives']} | {comp['fn_reduction']:+d} |
| True Positives | {solo['total_true_positives']} | {swarm['total_true_positives']} | {swarm['total_true_positives'] - solo['total_true_positives']:+d} |

**Interpretation:**
- Swarm mode {'reduces' if comp['swarm_reduces_fp'] else 'increases'} false positives by {abs(comp['fp_reduction'])} findings.
- Swarm mode {'reduces' if comp['swarm_reduces_fn'] else 'increases'} false negatives by {abs(comp['fn_reduction'])} findings.

---

## Performance Overhead

| Metric | Solo Mode | Swarm Mode | Overhead |
|--------|-----------|------------|----------|
| Total Duration | {solo['total_duration_seconds']}s | {swarm['total_duration_seconds']}s | {comp['time_overhead_ratio']:.1f}x |
| Avg Duration | {solo['avg_duration_seconds']:.0f}s | {swarm['avg_duration_seconds']:.0f}s | - |
| Total Runs | {solo['total_runs']} | {swarm['total_runs']} | - |

**Cost Analysis:**
- Time overhead: {comp['time_overhead_ratio']:.1f}x (swarm takes {comp['time_overhead_ratio']:.1f}x longer than solo)
- Token overhead: {comp.get('token_overhead_ratio', 0):.1f}x (estimated from multi-agent coordination)

---

## Per-Worktree Results

### Solo Mode Runs

{solo_table}

### Swarm Mode Runs

{swarm_table}

---

## Conclusion

**Multi-Agent Debate Value:**

| Factor | Value | Verdict |
|--------|-------|---------|
| Precision improvement | {comp['precision_delta']:+.2%} | {'Worth it' if comp['precision_delta'] > 0.05 else 'Marginal' if comp['precision_delta'] > 0 else 'No improvement'} |
| Recall improvement | {comp['recall_delta']:+.2%} | {'Worth it' if comp['recall_delta'] > 0.05 else 'Marginal' if comp['recall_delta'] > 0 else 'No improvement'} |
| F1 improvement | {comp['f1_delta']:+.2%} | {'Worth it' if comp['f1_delta'] > 0.05 else 'Marginal' if comp['f1_delta'] > 0 else 'No improvement'} |
| FP reduction | {comp['fp_reduction']} | {'Significant' if comp['fp_reduction'] > 2 else 'Minor' if comp['fp_reduction'] > 0 else 'None'} |
| Time overhead | {comp['time_overhead_ratio']:.1f}x | {'Acceptable' if comp['time_overhead_ratio'] < 2.5 else 'High' if comp['time_overhead_ratio'] < 3.5 else 'Very high'} |

**Final Verdict:**
{'Multi-agent debate (swarm mode) is recommended for production audits due to measurable accuracy improvements.' if comp['swarm_improves_f1'] else 'Solo mode is sufficient for most use cases; consider swarm mode only for high-stakes audits.'}

---

## Raw Data

### Solo Mode Aggregate

```json
{json.dumps(solo, indent=2)}
```

### Swarm Mode Aggregate

```json
{json.dumps(swarm, indent=2)}
```

### Comparison Statistics

```json
{json.dumps(comp, indent=2)}
```

---

*Report generated from A/B test comparing AlphaSwarm.sol solo vs swarm modes.*
*Solo mode: Single-agent analysis. Swarm mode: Multi-agent debate (attacker + defender + verifier).*
"""
    return report


def generate_worktree_table(details: list[dict], mode: str) -> str:
    """Generate a table for per-worktree results."""
    if not details:
        return "*No worktree data available*"

    rows = []
    for d in details:
        wt_name = d.get("worktree", "unknown")
        duration = d.get("duration_seconds", 0)
        tp = d.get("true_positives", 0)
        fp = d.get("false_positives", 0)
        fn = d.get("false_negatives", 0)
        precision = d.get("precision", 0)
        recall = d.get("recall", 0)
        f1 = d.get("f1_score", 0)
        error = d.get("error", "")

        # Truncate worktree name for display
        short_name = wt_name.replace("ab-solo-", "").replace("ab-swarm-", "")

        if error:
            rows.append(f"| {short_name} | {duration}s | - | - | - | ERROR: {error[:30]}... |")
        else:
            rows.append(f"| {short_name} | {duration}s | {tp}/{tp+fn} | {fp} | {precision:.2%} / {recall:.2%} | {f1:.2%} |")

    header = "| Worktree | Duration | TP/Total | FP | P/R | F1 |"
    separator = "|----------|----------|----------|----|----|-----|"

    return "\n".join([header, separator] + rows)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate A/B comparison report in markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --results ab-comparison-results.json --output ab-final-report.md
        """,
    )
    parser.add_argument(
        "--results",
        required=True,
        help="Path to results JSON from collect_ab_metrics.py",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output markdown file path",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output",
    )
    args = parser.parse_args()

    # Load results
    results_path = Path(args.results)
    if not results_path.exists():
        print(f"ERROR: Results file not found: {results_path}", file=sys.stderr)
        return 1

    try:
        results = json.loads(results_path.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in results file: {e}", file=sys.stderr)
        return 1

    # Validate required keys
    required_keys = ["solo", "swarm", "comparison"]
    for key in required_keys:
        if key not in results:
            print(f"ERROR: Missing required key in results: {key}", file=sys.stderr)
            return 1

    # Generate report
    report = generate_report(results)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)

    if args.verbose:
        print(f"Report written to: {output_path}", file=sys.stderr)

    # Also print to stdout
    print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
