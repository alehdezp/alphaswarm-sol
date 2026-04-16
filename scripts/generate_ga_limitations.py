#!/usr/bin/env python3
"""GA Limitations Aggregator - Produce limitations report for GA dossier.

This script aggregates gaps, validation results, and improvements into a
comprehensive limitations report for GA release decision.

Purpose:
- Load gap summary from .vrs/testing/gaps/ via GapTracker
- Read GA reports from .vrs/testing/reports/
- Aggregate blockers, failure categories, FP/FN stats
- Write JSON for dossier integration

Example:
    uv run python scripts/generate_ga_limitations.py --output .vrs/testing/reports/limitations.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alphaswarm_sol.testing.gaps import GapTracker, GapSeverity, GapStatus, GapCategory

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class BlockerEntry:
    """A GA blocker entry."""

    gap_id: str
    title: str
    severity: str
    category: str
    root_cause: str
    affected_component: str
    status: str


@dataclass
class FailureCategory:
    """Aggregated failure category."""

    category: str
    count: int
    examples: list[str]
    root_causes: list[str]


@dataclass
class FalsePositiveNegative:
    """FP/FN tracking entry."""

    pattern_id: str
    fp_count: int
    fn_count: int
    fn_examples: list[str]
    fp_examples: list[str]


@dataclass
class BacklogItem:
    """Improvement backlog item."""

    item_id: str
    source: str
    category: str
    description: str
    priority: str
    complexity: str
    deferred_reason: str | None = None


@dataclass
class LimitationsReport:
    """Full GA limitations report."""

    generated_at: str
    ga_status: str  # GO | CONDITIONAL_GO | NO_GO
    ga_rationale: str

    # Blockers
    blockers: list[dict[str, Any]] = field(default_factory=list)
    blocker_count: int = 0

    # Failure categories
    failure_categories: list[dict[str, Any]] = field(default_factory=list)
    top_failure_category: str | None = None

    # FP/FN stats
    false_positives_by_pattern: list[dict[str, Any]] = field(default_factory=list)
    false_negatives_by_pattern: list[dict[str, Any]] = field(default_factory=list)
    total_fp: int = 0
    total_fn: int = 0

    # Gap summary
    total_gaps: int = 0
    gaps_by_severity: dict[str, int] = field(default_factory=dict)
    gaps_by_category: dict[str, int] = field(default_factory=dict)
    gaps_by_status: dict[str, int] = field(default_factory=dict)

    # Validation metrics
    validation_metrics: dict[str, Any] = field(default_factory=dict)

    # Backlog
    backlog_items: list[dict[str, Any]] = field(default_factory=list)
    backlog_count: int = 0
    backlog_by_priority: dict[str, int] = field(default_factory=dict)

    # Recommendations
    recommendations: list[str] = field(default_factory=list)


def load_ga_reports(reports_dir: Path) -> dict[str, Any]:
    """Load all GA reports from directory.

    Args:
        reports_dir: Directory containing JSON reports

    Returns:
        Dict mapping report name to report data
    """
    reports = {}

    if not reports_dir.exists():
        logger.warning(f"Reports directory not found: {reports_dir}")
        return reports

    for report_file in reports_dir.glob("*.json"):
        try:
            data = json.loads(report_file.read_text())
            reports[report_file.stem] = data
            logger.info(f"Loaded report: {report_file.name}")
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to load report {report_file.name}: {e}")

    return reports


def extract_blockers(tracker: GapTracker) -> list[BlockerEntry]:
    """Extract GA blockers from gap tracker.

    Args:
        tracker: GapTracker instance

    Returns:
        List of blocker entries
    """
    blockers = []

    # Get all critical gaps that are still open
    critical_gaps = tracker.list_gaps(severity=GapSeverity.CRITICAL, status=GapStatus.OPEN)

    for gap in critical_gaps:
        blockers.append(
            BlockerEntry(
                gap_id=gap.gap_id,
                title=gap.title,
                severity=gap.severity.value,
                category=gap.category.value,
                root_cause=gap.root_cause,
                affected_component=gap.affected_component,
                status=gap.status.value,
            )
        )

    return blockers


def aggregate_failure_categories(tracker: GapTracker) -> list[FailureCategory]:
    """Aggregate gaps by category for failure analysis.

    Args:
        tracker: GapTracker instance

    Returns:
        List of failure categories with counts
    """
    categories: dict[str, FailureCategory] = {}

    for gap in tracker.list_gaps():
        cat = gap.category.value
        if cat not in categories:
            categories[cat] = FailureCategory(
                category=cat, count=0, examples=[], root_causes=[]
            )

        categories[cat].count += 1
        if len(categories[cat].examples) < 3:  # Keep top 3 examples
            categories[cat].examples.append(gap.title)
        if gap.root_cause not in categories[cat].root_causes:
            categories[cat].root_causes.append(gap.root_cause)

    # Sort by count descending
    return sorted(categories.values(), key=lambda x: x.count, reverse=True)


def extract_fp_fn_from_reports(reports: dict[str, Any]) -> tuple[list[FalsePositiveNegative], int, int]:
    """Extract FP/FN statistics from validation reports.

    Args:
        reports: Dict of loaded reports

    Returns:
        Tuple of (FP/FN list, total FP, total FN)
    """
    fp_fn_by_pattern: dict[str, FalsePositiveNegative] = {}
    total_fp = 0
    total_fn = 0

    # Extract from pattern-precision report
    if "pattern-precision" in reports:
        patterns_data = reports["pattern-precision"].get("patterns", [])
        for p in patterns_data:
            pattern_id = p.get("pattern_id", "unknown")
            fp_count = len(p.get("false_positives", []))
            fn_count = len(p.get("false_negatives", []))

            if pattern_id not in fp_fn_by_pattern:
                fp_fn_by_pattern[pattern_id] = FalsePositiveNegative(
                    pattern_id=pattern_id,
                    fp_count=0,
                    fn_count=0,
                    fn_examples=[],
                    fp_examples=[],
                )

            entry = fp_fn_by_pattern[pattern_id]
            entry.fp_count += fp_count
            entry.fn_count += fn_count
            entry.fn_examples.extend(p.get("false_negatives", [])[:3])
            entry.fp_examples.extend(p.get("false_positives", [])[:3])

            total_fp += fp_count
            total_fn += fn_count

    # Extract from shadow-audit report
    if "shadow-audit" in reports:
        shadow = reports["shadow-audit"]
        by_pattern = shadow.get("by_pattern", {})
        for pattern_id, data in by_pattern.items():
            missed = data.get("missed", 0)
            if isinstance(missed, int):
                total_fn += missed
            else:
                total_fn += len(missed) if isinstance(missed, list) else 0

    # Extract from adversarial-mutation report
    if "adversarial-mutation" in reports:
        adv = reports["adversarial-mutation"]
        for segment_data in adv.get("segments", {}).values():
            fn = segment_data.get("false_negatives", 0)
            fp = segment_data.get("false_positives", 0)
            total_fn += fn
            total_fp += fp

    return list(fp_fn_by_pattern.values()), total_fp, total_fn


def extract_validation_metrics(reports: dict[str, Any]) -> dict[str, Any]:
    """Extract key validation metrics from all reports.

    Args:
        reports: Dict of loaded reports

    Returns:
        Dict of validation metrics
    """
    metrics = {}

    # Shadow audit metrics
    if "shadow-audit" in reports:
        shadow = reports["shadow-audit"]
        metrics["shadow_audit"] = {
            "precision": shadow.get("precision", 0),
            "recall": shadow.get("recall", 0),
            "f1_score": shadow.get("f1_score", 0),
            "passes_gate": shadow.get("passes_gate", False),
        }

    # Pattern precision metrics
    if "pattern-precision" in reports:
        pp = reports["pattern-precision"]
        metrics["pattern_precision"] = pp.get("aggregate_metrics", {})
        metrics["pattern_summary"] = pp.get("summary", {})

    # Behavioral signatures
    if "behavioral-signatures" in reports:
        bs = reports["behavioral-signatures"]
        metrics["behavioral_signatures"] = {
            "unique_signatures": bs.get("unique_signatures", 0),
            "total_functions": bs.get("total_functions", 0),
            "functions_with_signatures": bs.get("functions_with_signatures", 0),
        }

    # Agent E2E
    if "agent-e2e" in reports:
        e2e = reports["agent-e2e"]
        flows = e2e.get("flows", {})
        metrics["agent_e2e"] = {
            flow_name: {
                "runs_passed": flow_data.get("runs_passed", 0),
                "runs_failed": flow_data.get("runs_failed", 0),
                "total_runs": flow_data.get("total_runs", 0),
            }
            for flow_name, flow_data in flows.items()
        }

    # Context A/B
    if "context-ab" in reports:
        cab = reports["context-ab"]
        metrics["context_ab"] = {
            "decision": cab.get("decision", {}).get("include_context_for_ga", "UNKNOWN"),
            "avg_precision_delta": cab.get("aggregate", {}).get("avg_precision_delta", 0),
            "avg_recall_delta": cab.get("aggregate", {}).get("avg_recall_delta", 0),
        }

    # Adversarial stress
    if "adversarial-mutation" in reports:
        adv = reports["adversarial-mutation"]
        metrics["adversarial"] = {
            "overall_precision": adv.get("overall", {}).get("precision", 0),
            "overall_recall": adv.get("overall", {}).get("recall", 0),
            "ga_recommendation": adv.get("ga_recommendation", ""),
        }

    return metrics


def determine_ga_status(
    blockers: list[BlockerEntry],
    metrics: dict[str, Any],
) -> tuple[str, str]:
    """Determine GA status based on blockers and metrics.

    Args:
        blockers: List of GA blockers
        metrics: Validation metrics

    Returns:
        Tuple of (status, rationale)
    """
    # Check for hard blockers
    if blockers:
        return (
            "NO_GO",
            f"{len(blockers)} critical gap(s) remain open: "
            + ", ".join(b.gap_id for b in blockers),
        )

    # Check shadow audit gate
    shadow = metrics.get("shadow_audit", {})
    if shadow and not shadow.get("passes_gate", True):
        return (
            "CONDITIONAL_GO",
            f"Shadow audit gate not passed. Precision: {shadow.get('precision', 0):.0%}, "
            f"Recall: {shadow.get('recall', 0):.0%}",
        )

    # Check adversarial recommendation
    adv = metrics.get("adversarial", {})
    adv_rec = adv.get("ga_recommendation", "")
    if adv_rec and "fail" in adv_rec.lower():
        return (
            "CONDITIONAL_GO",
            f"Adversarial stress tests recommend conditional pass: {adv_rec}",
        )

    # All gates pass
    return (
        "GO",
        "All GA gates pass. Shadow audit precision/recall within thresholds. "
        "No critical blockers.",
    )


def generate_recommendations(
    ga_status: str,
    failure_categories: list[FailureCategory],
    fp_fn: list[FalsePositiveNegative],
    metrics: dict[str, Any],
) -> list[str]:
    """Generate recommendations based on analysis.

    Args:
        ga_status: GO/CONDITIONAL_GO/NO_GO
        failure_categories: List of failure categories
        fp_fn: FP/FN stats by pattern
        metrics: Validation metrics

    Returns:
        List of recommendations
    """
    recommendations = []

    # Status-based recommendations
    if ga_status == "NO_GO":
        recommendations.append("BLOCKER: Resolve all critical gaps before GA release")
    elif ga_status == "CONDITIONAL_GO":
        recommendations.append(
            "Document known limitations in release notes"
        )
        recommendations.append(
            "Consider additional validation for affected patterns"
        )

    # Failure category recommendations
    if failure_categories:
        top_cat = failure_categories[0]
        if top_cat.count > 10:
            recommendations.append(
                f"POST-GA: Address '{top_cat.category}' category gaps ({top_cat.count} issues)"
            )

    # FP/FN recommendations
    high_fn_patterns = [p for p in fp_fn if p.fn_count > 2]
    if high_fn_patterns:
        patterns_str = ", ".join(p.pattern_id for p in high_fn_patterns[:3])
        recommendations.append(
            f"POST-GA: Improve recall for patterns with high FN: {patterns_str}"
        )

    high_fp_patterns = [p for p in fp_fn if p.fp_count > 2]
    if high_fp_patterns:
        patterns_str = ", ".join(p.pattern_id for p in high_fp_patterns[:3])
        recommendations.append(
            f"POST-GA: Reduce false positives for patterns: {patterns_str}"
        )

    # Context-based recommendations
    context = metrics.get("context_ab", {})
    if context.get("decision") == "INCLUDE":
        recommendations.append(
            "RELEASE: Include protocol context pack in default workflow"
        )

    # If no specific recommendations, add general ones
    if len(recommendations) < 2:
        recommendations.append("Monitor real-world performance post-GA")
        recommendations.append("Collect user feedback on pattern accuracy")

    return recommendations


def load_backlog(backlog_path: Path) -> list[BacklogItem]:
    """Load existing backlog items.

    Args:
        backlog_path: Path to backlog YAML file

    Returns:
        List of backlog items
    """
    if not backlog_path.exists():
        return []

    try:
        data = yaml.safe_load(backlog_path.read_text())
        items = []
        for entry in data.get("improvements", []):
            items.append(
                BacklogItem(
                    item_id=entry.get("id", "UNKNOWN"),
                    source=entry.get("source", ""),
                    category=entry.get("category", ""),
                    description=entry.get("description", ""),
                    priority=entry.get("priority", "medium"),
                    complexity=entry.get("complexity", "medium"),
                    deferred_reason=entry.get("deferred_reason"),
                )
            )
        return items
    except Exception as e:
        logger.warning(f"Failed to load backlog: {e}")
        return []


def generate_limitations_report(
    gaps_dir: Path,
    reports_dir: Path,
    backlog_path: Path | None = None,
) -> LimitationsReport:
    """Generate comprehensive GA limitations report.

    Args:
        gaps_dir: Directory containing gap YAML files
        reports_dir: Directory containing JSON reports
        backlog_path: Path to backlog YAML file (optional)

    Returns:
        LimitationsReport instance
    """
    # Initialize tracker (creates dir if not exists)
    tracker = GapTracker(gaps_dir)

    # Load reports
    reports = load_ga_reports(reports_dir)

    # Extract blockers
    blockers = extract_blockers(tracker)

    # Aggregate failure categories
    failure_categories = aggregate_failure_categories(tracker)

    # Extract FP/FN
    fp_fn, total_fp, total_fn = extract_fp_fn_from_reports(reports)

    # Get gap summary
    gap_summary = tracker.get_summary()

    # Extract validation metrics
    validation_metrics = extract_validation_metrics(reports)

    # Determine GA status
    ga_status, ga_rationale = determine_ga_status(blockers, validation_metrics)

    # Generate recommendations
    recommendations = generate_recommendations(
        ga_status, failure_categories, fp_fn, validation_metrics
    )

    # Load backlog if exists
    backlog_items = []
    if backlog_path and backlog_path.exists():
        backlog_items = load_backlog(backlog_path)

    # Build backlog stats
    backlog_by_priority: dict[str, int] = {}
    for item in backlog_items:
        p = item.priority
        backlog_by_priority[p] = backlog_by_priority.get(p, 0) + 1

    # Build report
    report = LimitationsReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        ga_status=ga_status,
        ga_rationale=ga_rationale,
        blockers=[asdict(b) for b in blockers],
        blocker_count=len(blockers),
        failure_categories=[asdict(fc) for fc in failure_categories],
        top_failure_category=failure_categories[0].category if failure_categories else None,
        false_positives_by_pattern=[asdict(p) for p in fp_fn if p.fp_count > 0],
        false_negatives_by_pattern=[asdict(p) for p in fp_fn if p.fn_count > 0],
        total_fp=total_fp,
        total_fn=total_fn,
        total_gaps=gap_summary["total"],
        gaps_by_severity=gap_summary["by_severity"],
        gaps_by_category=gap_summary["by_category"],
        gaps_by_status=gap_summary["by_status"],
        validation_metrics=validation_metrics,
        backlog_items=[asdict(bi) for bi in backlog_items],
        backlog_count=len(backlog_items),
        backlog_by_priority=backlog_by_priority,
        recommendations=recommendations,
    )

    return report


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate GA limitations report from gaps and validation results"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".vrs/testing/reports/limitations.json"),
        help="Output path for JSON report (default: .vrs/testing/reports/limitations.json)",
    )
    parser.add_argument(
        "--gaps-dir",
        type=Path,
        default=Path(".vrs/testing/gaps"),
        help="Directory containing gap YAML files (default: .vrs/testing/gaps)",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path(".vrs/testing/reports"),
        help="Directory containing GA reports (default: .vrs/testing/reports)",
    )
    parser.add_argument(
        "--backlog",
        type=Path,
        default=Path(".vrs/backlog/v0.5.1.yaml"),
        help="Path to backlog YAML file (default: .vrs/backlog/v0.5.1.yaml)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Generate report
    logger.info("Generating GA limitations report...")
    report = generate_limitations_report(
        gaps_dir=args.gaps_dir,
        reports_dir=args.reports_dir,
        backlog_path=args.backlog,
    )

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Write report
    args.output.write_text(json.dumps(asdict(report), indent=2))
    logger.info(f"Report written to: {args.output}")

    # Print summary
    print("\n" + "=" * 60)
    print("GA LIMITATIONS REPORT SUMMARY")
    print("=" * 60)
    print(f"\nGA Status: {report.ga_status}")
    print(f"Rationale: {report.ga_rationale}")
    print(f"\nBlockers: {report.blocker_count}")
    print(f"Total Gaps: {report.total_gaps}")
    print(f"  - Critical: {report.gaps_by_severity.get('critical', 0)}")
    print(f"  - High: {report.gaps_by_severity.get('high', 0)}")
    print(f"  - Medium: {report.gaps_by_severity.get('medium', 0)}")
    print(f"  - Low: {report.gaps_by_severity.get('low', 0)}")
    print(f"\nTotal FP: {report.total_fp}")
    print(f"Total FN: {report.total_fn}")
    print(f"\nBacklog Items: {report.backlog_count}")
    print("\nRecommendations:")
    for rec in report.recommendations:
        print(f"  - {rec}")

    print("\n" + "=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
