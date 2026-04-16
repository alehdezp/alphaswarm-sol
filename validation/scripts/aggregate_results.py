#!/usr/bin/env python3
"""Aggregate validation results across all projects.

Usage:
    python aggregate_results.py
    python aggregate_results.py --output report.json
    python aggregate_results.py --markdown
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from alphaswarm_sol.validation.ground_truth import (
    ProjectGroundTruth,
    VulnerabilityCategory,
)


VALIDATION_DIR = Path(__file__).parent.parent
GROUND_TRUTH_DIR = VALIDATION_DIR / "ground-truth"
RESULTS_DIR = VALIDATION_DIR / "results"


def load_all_ground_truth() -> List[ProjectGroundTruth]:
    """Load all ground truth files."""
    projects = []
    for path in sorted(GROUND_TRUTH_DIR.glob("*.yaml")):
        try:
            gt = ProjectGroundTruth.load(path)
            projects.append(gt)
        except Exception as e:
            print(f"Warning: Failed to load {path}: {e}")
    return projects


def aggregate_by_category(projects: List[ProjectGroundTruth]) -> Dict[str, Dict[str, int]]:
    """Aggregate findings by vulnerability category across projects.

    Returns:
        Dict mapping category to counts:
        {
            "reentrancy": {"total": 5, "vkg_detectable": 5},
            "access_control": {"total": 8, "vkg_detectable": 7},
            ...
        }
    """
    by_category: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "vkg_detectable": 0})

    for gt in projects:
        for finding in gt.findings:
            cat = finding.category.value
            by_category[cat]["total"] += 1
            if finding.vkg_should_find:
                by_category[cat]["vkg_detectable"] += 1

    return dict(by_category)


def aggregate_by_severity(projects: List[ProjectGroundTruth]) -> Dict[str, Dict[str, int]]:
    """Aggregate findings by severity across projects."""
    by_severity: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "vkg_detectable": 0})

    for gt in projects:
        for finding in gt.findings:
            sev = finding.severity.value
            by_severity[sev]["total"] += 1
            if finding.vkg_should_find:
                by_severity[sev]["vkg_detectable"] += 1

    return dict(by_severity)


def aggregate_by_project_type(projects: List[ProjectGroundTruth]) -> Dict[str, Dict[str, Any]]:
    """Aggregate findings by project type (lending, dex, nft, etc)."""
    by_type: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"projects": [], "total_findings": 0, "vkg_detectable": 0}
    )

    for gt in projects:
        ptype = gt.project_type
        by_type[ptype]["projects"].append(gt.project_name)
        by_type[ptype]["total_findings"] += gt.total_findings
        by_type[ptype]["vkg_detectable"] += len(gt.vkg_detectable_findings)

    return dict(by_type)


def calculate_coverage_metrics(projects: List[ProjectGroundTruth]) -> Dict[str, float]:
    """Calculate overall coverage metrics."""
    total_findings = sum(gt.total_findings for gt in projects)
    total_vkg_detectable = sum(len(gt.vkg_detectable_findings) for gt in projects)

    # Calculate by severity
    high_plus = 0
    high_plus_detectable = 0
    for gt in projects:
        for f in gt.findings:
            if f.severity.value in ("critical", "high"):
                high_plus += 1
                if f.vkg_should_find:
                    high_plus_detectable += 1

    return {
        "total_findings": total_findings,
        "vkg_detectable": total_vkg_detectable,
        "vkg_coverage_pct": round(total_vkg_detectable / total_findings * 100, 1) if total_findings > 0 else 0,
        "high_severity_total": high_plus,
        "high_severity_detectable": high_plus_detectable,
        "high_severity_coverage_pct": round(high_plus_detectable / high_plus * 100, 1) if high_plus > 0 else 0,
    }


def identify_gaps(projects: List[ProjectGroundTruth]) -> Dict[str, List[str]]:
    """Identify categories where VKG cannot detect findings."""
    gaps: Dict[str, List[str]] = defaultdict(list)

    for gt in projects:
        for finding in gt.findings:
            if not finding.vkg_should_find:
                gaps[finding.category.value].append(
                    f"{gt.project_name}: {finding.title}"
                )

    return dict(gaps)


def generate_aggregate_report(projects: List[ProjectGroundTruth]) -> Dict[str, Any]:
    """Generate comprehensive aggregate report."""
    return {
        "summary": {
            "total_projects": len(projects),
            "projects": [gt.project_name for gt in projects],
            "project_types": list(set(gt.project_type for gt in projects)),
        },
        "coverage_metrics": calculate_coverage_metrics(projects),
        "by_category": aggregate_by_category(projects),
        "by_severity": aggregate_by_severity(projects),
        "by_project_type": aggregate_by_project_type(projects),
        "gaps": identify_gaps(projects),
        "vkg_detectable_categories": [c.value for c in VulnerabilityCategory.vkg_detectable()],
        "out_of_scope_categories": [c.value for c in VulnerabilityCategory.out_of_scope()],
    }


def format_markdown_report(report: Dict[str, Any]) -> str:
    """Format aggregate report as Markdown."""
    lines = []
    lines.append("# VKG Validation Aggregate Report")
    lines.append("")

    # Summary
    summary = report["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Projects analyzed:** {summary['total_projects']}")
    lines.append(f"- **Projects:** {', '.join(summary['projects'])}")
    lines.append(f"- **Project types:** {', '.join(summary['project_types'])}")
    lines.append("")

    # Coverage metrics
    metrics = report["coverage_metrics"]
    lines.append("## Coverage Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total findings | {metrics['total_findings']} |")
    lines.append(f"| VKG detectable | {metrics['vkg_detectable']} |")
    lines.append(f"| Coverage | {metrics['vkg_coverage_pct']}% |")
    lines.append(f"| High/Critical total | {metrics['high_severity_total']} |")
    lines.append(f"| High/Critical detectable | {metrics['high_severity_detectable']} |")
    lines.append(f"| High/Critical coverage | {metrics['high_severity_coverage_pct']}% |")
    lines.append("")

    # By category
    lines.append("## Findings by Category")
    lines.append("")
    lines.append("| Category | Total | VKG Detectable | Coverage |")
    lines.append("|----------|-------|----------------|----------|")
    for cat, counts in sorted(report["by_category"].items()):
        total = counts["total"]
        detectable = counts["vkg_detectable"]
        pct = round(detectable / total * 100, 0) if total > 0 else 0
        lines.append(f"| {cat} | {total} | {detectable} | {pct:.0f}% |")
    lines.append("")

    # By severity
    lines.append("## Findings by Severity")
    lines.append("")
    lines.append("| Severity | Total | VKG Detectable | Coverage |")
    lines.append("|----------|-------|----------------|----------|")
    for sev in ["critical", "high", "medium", "low"]:
        if sev in report["by_severity"]:
            counts = report["by_severity"][sev]
            total = counts["total"]
            detectable = counts["vkg_detectable"]
            pct = round(detectable / total * 100, 0) if total > 0 else 0
            lines.append(f"| {sev.upper()} | {total} | {detectable} | {pct:.0f}% |")
    lines.append("")

    # By project type
    lines.append("## Findings by Project Type")
    lines.append("")
    lines.append("| Type | Projects | Total | VKG Detectable |")
    lines.append("|------|----------|-------|----------------|")
    for ptype, data in sorted(report["by_project_type"].items()):
        projects_str = ", ".join(data["projects"])
        lines.append(f"| {ptype} | {projects_str} | {data['total_findings']} | {data['vkg_detectable']} |")
    lines.append("")

    # Gaps
    if report["gaps"]:
        lines.append("## Out of Scope (Gaps)")
        lines.append("")
        lines.append("These findings require semantic understanding and are not detectable by VKG:")
        lines.append("")
        for cat, findings in sorted(report["gaps"].items()):
            lines.append(f"### {cat}")
            for f in findings:
                lines.append(f"- {f}")
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Aggregate validation results")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--markdown", "-m", action="store_true", help="Generate Markdown report")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")

    args = parser.parse_args()

    # Load all ground truth
    projects = load_all_ground_truth()

    if not projects:
        print("No ground truth files found!")
        return

    if not args.quiet:
        print(f"Loaded {len(projects)} ground truth files")
        for gt in projects:
            print(f"  - {gt.project_name} ({gt.project_type}): {gt.total_findings} findings")
        print()

    # Generate report
    report = generate_aggregate_report(projects)

    # Output
    if args.markdown:
        content = format_markdown_report(report)
        if args.output:
            Path(args.output).write_text(content)
            print(f"Markdown report saved to: {args.output}")
        else:
            print(content)
    else:
        if args.output:
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2)
            print(f"JSON report saved to: {args.output}")
        else:
            print(json.dumps(report, indent=2))

    # Print summary
    if not args.quiet:
        metrics = report["coverage_metrics"]
        print()
        print("=" * 60)
        print("AGGREGATE SUMMARY")
        print("=" * 60)
        print(f"  Total findings: {metrics['total_findings']}")
        print(f"  VKG detectable: {metrics['vkg_detectable']} ({metrics['vkg_coverage_pct']}%)")
        print(f"  High/Critical: {metrics['high_severity_detectable']}/{metrics['high_severity_total']} ({metrics['high_severity_coverage_pct']}%)")


if __name__ == "__main__":
    main()
