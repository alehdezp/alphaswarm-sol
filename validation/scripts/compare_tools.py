#!/usr/bin/env python3
"""Compare VKG findings with Slither and Aderyn.

Uses the orchestration module to run tools and compares findings
to identify VKG's unique value proposition.

Usage:
    python compare_tools.py <project_path>
    python compare_tools.py <project_path> --output comparison.json
    python compare_tools.py <project_path> --markdown
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
from dataclasses import dataclass
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from alphaswarm_sol.orchestration import (
    ToolRunner,
    ToolResult,
    ToolStatus,
    deduplicate_findings,
    get_unique_to_tool,
)


@dataclass
class ToolComparisonResult:
    """Result of tool comparison analysis."""
    project: str
    tool_results: Dict[str, Dict[str, Any]]
    overlap_analysis: Dict[str, List[Dict[str, Any]]]
    unique_value: Dict[str, List[Dict[str, Any]]]
    metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project": self.project,
            "tool_results": self.tool_results,
            "overlap_analysis": self.overlap_analysis,
            "unique_value": self.unique_value,
            "metrics": self.metrics,
        }


def analyze_tool_overlap(
    findings: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Analyze which tools found which findings.

    Returns:
        {
            "vkg_only": [...],
            "slither_only": [...],
            "aderyn_only": [...],
            "vkg_slither": [...],
            "vkg_aderyn": [...],
            "slither_aderyn": [...],
            "all_three": [...],
        }
    """
    # Group findings by file and line bucket
    def location_key(f: Dict[str, Any]) -> str:
        file = Path(f.get("file", "unknown")).name
        line = f.get("line", 0)
        # Use 10-line buckets to account for minor differences
        line_bucket = (line // 10) * 10
        return f"{file}:{line_bucket}"

    # Group by location
    by_location: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for f in findings:
        key = location_key(f)
        by_location[key].append(f)

    result = {
        "vkg_only": [],
        "slither_only": [],
        "aderyn_only": [],
        "vkg_slither": [],
        "vkg_aderyn": [],
        "slither_aderyn": [],
        "all_three": [],
    }

    for key, group in by_location.items():
        tools: Set[str] = {f.get("source", "unknown") for f in group}

        # Determine overlap category
        if tools == {"vkg"}:
            result["vkg_only"].append({"location": key, "findings": group})
        elif tools == {"slither"}:
            result["slither_only"].append({"location": key, "findings": group})
        elif tools == {"aderyn"}:
            result["aderyn_only"].append({"location": key, "findings": group})
        elif tools == {"vkg", "slither"}:
            result["vkg_slither"].append({"location": key, "findings": group})
        elif tools == {"vkg", "aderyn"}:
            result["vkg_aderyn"].append({"location": key, "findings": group})
        elif tools == {"slither", "aderyn"}:
            result["slither_aderyn"].append({"location": key, "findings": group})
        elif len(tools) >= 3 or {"vkg", "slither", "aderyn"}.issubset(tools):
            result["all_three"].append({"location": key, "findings": group})
        else:
            # Partial matches - assign to the most specific category
            if "vkg" in tools:
                if "slither" in tools:
                    result["vkg_slither"].append({"location": key, "findings": group})
                elif "aderyn" in tools:
                    result["vkg_aderyn"].append({"location": key, "findings": group})
                else:
                    result["vkg_only"].append({"location": key, "findings": group})

    return result


def calculate_comparison_metrics(
    results: List[ToolResult],
    overlap: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """Calculate comparison metrics."""
    # Get finding counts per tool
    findings_by_tool = {}
    for r in results:
        if r.status == ToolStatus.SUCCESS:
            findings_by_tool[r.tool] = len(r.findings)
        else:
            findings_by_tool[r.tool] = 0

    # Calculate unique findings
    unique_counts = {
        "vkg_only": len(overlap.get("vkg_only", [])),
        "slither_only": len(overlap.get("slither_only", [])),
        "aderyn_only": len(overlap.get("aderyn_only", [])),
    }

    # Calculate agreement
    agreement_counts = {
        "all_three": len(overlap.get("all_three", [])),
        "vkg_slither": len(overlap.get("vkg_slither", [])),
        "vkg_aderyn": len(overlap.get("vkg_aderyn", [])),
        "slither_aderyn": len(overlap.get("slither_aderyn", [])),
    }

    # VKG value metrics
    vkg_unique = unique_counts["vkg_only"]
    vkg_with_agreement = (
        agreement_counts["vkg_slither"] +
        agreement_counts["vkg_aderyn"] +
        agreement_counts["all_three"]
    )
    missed_by_vkg = agreement_counts["slither_aderyn"]

    return {
        "findings_by_tool": findings_by_tool,
        "unique_findings": unique_counts,
        "agreement": agreement_counts,
        "vkg_metrics": {
            "total_findings": findings_by_tool.get("vkg", 0),
            "unique_to_vkg": vkg_unique,
            "corroborated": vkg_with_agreement,
            "missed_by_vkg": missed_by_vkg,
        },
    }


def identify_unique_value(
    overlap: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Identify VKG's unique value proposition findings."""
    return {
        "vkg_unique": overlap.get("vkg_only", []),
        "vkg_corroborated": (
            overlap.get("vkg_slither", []) +
            overlap.get("vkg_aderyn", []) +
            overlap.get("all_three", [])
        ),
        "vkg_gaps": overlap.get("slither_aderyn", []),
    }


def compare_tools(
    project_path: Path,
    skip_missing: bool = True,
) -> ToolComparisonResult:
    """Run all tools on a project and compare findings.

    Args:
        project_path: Path to Solidity project
        skip_missing: Skip tools not installed

    Returns:
        ToolComparisonResult with full analysis
    """
    runner = ToolRunner(project_path)

    # Check available tools
    available = runner.get_available_tools()
    print(f"Available tools: {', '.join(available)}")

    # Run all tools
    results = runner.run_all(skip_missing=skip_missing)

    # Collect all findings
    all_findings = []
    tool_summaries = {}
    for r in results:
        tool_summaries[r.tool] = {
            "status": r.status.value,
            "findings_count": len(r.findings),
            "execution_time": r.execution_time,
            "error": r.error,
        }
        if r.status == ToolStatus.SUCCESS:
            all_findings.extend(r.findings)
            print(f"  {r.tool}: {len(r.findings)} findings")
        else:
            print(f"  {r.tool}: {r.status.value}")

    # Analyze overlap
    overlap = analyze_tool_overlap(all_findings)

    # Calculate metrics
    metrics = calculate_comparison_metrics(results, overlap)

    # Identify unique value
    unique_value = identify_unique_value(overlap)

    return ToolComparisonResult(
        project=str(project_path),
        tool_results=tool_summaries,
        overlap_analysis=overlap,
        unique_value=unique_value,
        metrics=metrics,
    )


def format_markdown_report(result: ToolComparisonResult) -> str:
    """Format comparison result as Markdown."""
    lines = []
    lines.append(f"# Tool Comparison: {result.project}")
    lines.append("")

    # Tool results summary
    lines.append("## Tool Results")
    lines.append("")
    lines.append("| Tool | Status | Findings | Time |")
    lines.append("|------|--------|----------|------|")
    for tool, data in result.tool_results.items():
        status = "✓" if data["status"] == "success" else "✗"
        count = data.get("findings_count", 0)
        time_s = data.get("execution_time", 0)
        lines.append(f"| {tool} | {status} | {count} | {time_s:.1f}s |")
    lines.append("")

    # Overlap analysis
    lines.append("## Overlap Analysis")
    lines.append("")
    lines.append("| Category | Count | Description |")
    lines.append("|----------|-------|-------------|")

    overlap = result.overlap_analysis
    lines.append(f"| VKG Only | {len(overlap.get('vkg_only', []))} | Unique to VKG |")
    lines.append(f"| Slither Only | {len(overlap.get('slither_only', []))} | Unique to Slither |")
    lines.append(f"| Aderyn Only | {len(overlap.get('aderyn_only', []))} | Unique to Aderyn |")
    lines.append(f"| VKG + Slither | {len(overlap.get('vkg_slither', []))} | Both agree |")
    lines.append(f"| VKG + Aderyn | {len(overlap.get('vkg_aderyn', []))} | Both agree |")
    lines.append(f"| Slither + Aderyn | {len(overlap.get('slither_aderyn', []))} | VKG missed |")
    lines.append(f"| All Three | {len(overlap.get('all_three', []))} | Unanimous |")
    lines.append("")

    # VKG unique value
    lines.append("## VKG Unique Value")
    lines.append("")
    vkg_metrics = result.metrics.get("vkg_metrics", {})
    lines.append(f"- **Unique findings:** {vkg_metrics.get('unique_to_vkg', 0)}")
    lines.append(f"- **Corroborated findings:** {vkg_metrics.get('corroborated', 0)}")
    lines.append(f"- **Findings VKG missed:** {vkg_metrics.get('missed_by_vkg', 0)}")
    lines.append("")

    # VKG unique findings details
    vkg_unique = result.unique_value.get("vkg_unique", [])
    if vkg_unique:
        lines.append("### VKG-Unique Findings")
        lines.append("")
        for item in vkg_unique[:10]:  # Limit to first 10
            location = item.get("location", "unknown")
            findings = item.get("findings", [])
            if findings:
                f = findings[0]
                lines.append(f"- **{location}**: {f.get('category', 'unknown')} - {f.get('id', 'unknown')}")
        lines.append("")

    # Gaps (what VKG missed)
    vkg_gaps = result.unique_value.get("vkg_gaps", [])
    if vkg_gaps:
        lines.append("### VKG Gaps (Missed by VKG)")
        lines.append("")
        for item in vkg_gaps[:10]:
            location = item.get("location", "unknown")
            findings = item.get("findings", [])
            if findings:
                sources = set(f.get("source", "unknown") for f in findings)
                categories = set(f.get("category", "unknown") for f in findings)
                lines.append(f"- **{location}**: {', '.join(categories)} (found by {', '.join(sources)})")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compare VKG with Slither/Aderyn")
    parser.add_argument("project_path", help="Path to Solidity project")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--markdown", "-m", action="store_true", help="Generate Markdown report")
    parser.add_argument("--skip-missing", action="store_true", default=True, help="Skip missing tools")

    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        print(f"Error: Project path not found: {project_path}")
        return

    print(f"Comparing tools on: {project_path}")
    print()

    result = compare_tools(project_path, skip_missing=args.skip_missing)

    # Output
    if args.markdown:
        content = format_markdown_report(result)
        if args.output:
            Path(args.output).write_text(content)
            print(f"\nMarkdown report saved to: {args.output}")
        else:
            print()
            print(content)
    else:
        if args.output:
            with open(args.output, "w") as f:
                json.dump(result.to_dict(), f, indent=2)
            print(f"\nJSON report saved to: {args.output}")
        else:
            print()
            print(json.dumps(result.to_dict(), indent=2))

    # Summary
    print()
    print("=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    metrics = result.metrics
    print(f"Findings: VKG={metrics['findings_by_tool'].get('vkg', 0)}, "
          f"Slither={metrics['findings_by_tool'].get('slither', 0)}, "
          f"Aderyn={metrics['findings_by_tool'].get('aderyn', 0)}")
    print(f"Unique: VKG={metrics['unique_findings']['vkg_only']}, "
          f"Slither={metrics['unique_findings']['slither_only']}, "
          f"Aderyn={metrics['unique_findings']['aderyn_only']}")
    print(f"Agreement: All three={metrics['agreement']['all_three']}")


if __name__ == "__main__":
    main()
