"""Report generation for VulnDocs coverage analysis.

Generates various report formats:
- Coverage matrix (category x section)
- Gap reports with recommendations
- Trend reports (over time)
- TOON-formatted reports for LLM consumption
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Any, Dict, List, Optional
import json

from alphaswarm_sol.vulndocs.analysis.coverage import (
    CoverageAnalyzer,
    CoverageReport,
    CategoryCoverage,
    CoverageLevel,
    THREAT_MODEL_CATEGORIES,
)
from alphaswarm_sol.vulndocs.analysis.gaps import (
    GapFinder,
    GapAnalysisResult,
    GapSeverity,
)


class ReportFormat(Enum):
    """Output formats for reports."""

    MARKDOWN = "markdown"
    JSON = "json"
    TOON = "toon"  # Token-optimized output notation
    HTML = "html"
    CSV = "csv"


@dataclass
class CoverageMatrixCell:
    """Single cell in the coverage matrix."""

    category: str
    section: str
    coverage_level: CoverageLevel
    doc_count: int = 0
    has_content: bool = False


@dataclass
class CoverageMatrix:
    """Matrix showing coverage across categories and sections.

    Sections: detection, exploitation, mitigation, examples
    Categories: reentrancy, access-control, oracle, etc.
    """

    # Matrix data
    cells: List[CoverageMatrixCell] = field(default_factory=list)

    # Dimensions
    categories: List[str] = field(default_factory=list)
    sections: List[str] = field(default_factory=lambda: [
        "detection", "exploitation", "mitigation", "examples"
    ])

    # Summary stats
    total_cells: int = 0
    covered_cells: int = 0
    coverage_percent: float = 0.0

    def get_cell(self, category: str, section: str) -> Optional[CoverageMatrixCell]:
        """Get a specific cell."""
        for cell in self.cells:
            if cell.category == category and cell.section == section:
                return cell
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        matrix_data = {}
        for cell in self.cells:
            if cell.category not in matrix_data:
                matrix_data[cell.category] = {}
            matrix_data[cell.category][cell.section] = {
                "level": cell.coverage_level.value,
                "doc_count": cell.doc_count,
                "has_content": cell.has_content,
            }

        return {
            "matrix": matrix_data,
            "categories": self.categories,
            "sections": self.sections,
            "total_cells": self.total_cells,
            "covered_cells": self.covered_cells,
            "coverage_percent": round(self.coverage_percent, 2),
        }

    def to_markdown(self) -> str:
        """Render as markdown table."""
        lines = [
            "| Category | Detection | Exploitation | Mitigation | Examples |",
            "|----------|-----------|--------------|------------|----------|",
        ]

        for category in self.categories:
            row = f"| {THREAT_MODEL_CATEGORIES.get(category, {}).get('display', category)} |"
            for section in self.sections:
                cell = self.get_cell(category, section)
                if cell:
                    emoji = {
                        CoverageLevel.FULL: "✅",
                        CoverageLevel.PARTIAL: "🟡",
                        CoverageLevel.MINIMAL: "🟠",
                        CoverageLevel.NONE: "❌",
                    }.get(cell.coverage_level, "❓")
                    row += f" {emoji} |"
                else:
                    row += " ❓ |"
            lines.append(row)

        lines.append("")
        lines.append(f"**Coverage:** {self.coverage_percent:.1f}% ({self.covered_cells}/{self.total_cells} cells)")

        return "\n".join(lines)

    def to_toon(self) -> str:
        """Render in TOON format for LLM consumption."""
        lines = ["[COVERAGE_MATRIX]"]

        for category in self.categories:
            cat_display = THREAT_MODEL_CATEGORIES.get(category, {}).get("display", category)
            levels = []
            for section in self.sections:
                cell = self.get_cell(category, section)
                if cell:
                    level_short = {
                        CoverageLevel.FULL: "F",
                        CoverageLevel.PARTIAL: "P",
                        CoverageLevel.MINIMAL: "M",
                        CoverageLevel.NONE: "N",
                    }.get(cell.coverage_level, "?")
                    levels.append(f"{section[0].upper()}:{level_short}")

            lines.append(f"{cat_display}: {' '.join(levels)}")

        lines.append(f"[/COVERAGE_MATRIX coverage={self.coverage_percent:.0f}%]")
        return "\n".join(lines)


class ReportGenerator:
    """Generates coverage and gap reports.

    Example:
        generator = ReportGenerator()

        # Generate coverage matrix
        matrix = generator.generate_matrix()
        print(matrix.to_markdown())

        # Generate full report
        report = generator.generate_full_report()

        # Export in different formats
        generator.export(report, ReportFormat.MARKDOWN, "coverage_report.md")
    """

    def __init__(
        self,
        analyzer: Optional[CoverageAnalyzer] = None,
        gap_finder: Optional[GapFinder] = None,
    ):
        """Initialize report generator.

        Args:
            analyzer: Coverage analyzer instance
            gap_finder: Gap finder instance
        """
        self.analyzer = analyzer or CoverageAnalyzer()
        self.gap_finder = gap_finder or GapFinder()

    def generate_matrix(self) -> CoverageMatrix:
        """Generate coverage matrix.

        Returns:
            CoverageMatrix showing coverage by category and section
        """
        matrix = CoverageMatrix()
        matrix.categories = list(THREAT_MODEL_CATEGORIES.keys())

        for category in matrix.categories:
            # Get category coverage
            cat_coverage = self.analyzer.get_category_coverage(category)

            for section in matrix.sections:
                cell = CoverageMatrixCell(
                    category=category,
                    section=section,
                    coverage_level=CoverageLevel.NONE,
                )

                if cat_coverage and cat_coverage.total_docs > 0:
                    # Determine coverage level based on section
                    if section == "detection":
                        if cat_coverage.docs_with_detection > 0:
                            cell.has_content = True
                            if cat_coverage.docs_with_detection >= cat_coverage.total_docs * 0.8:
                                cell.coverage_level = CoverageLevel.FULL
                            elif cat_coverage.docs_with_detection >= cat_coverage.total_docs * 0.5:
                                cell.coverage_level = CoverageLevel.PARTIAL
                            else:
                                cell.coverage_level = CoverageLevel.MINIMAL
                        cell.doc_count = cat_coverage.docs_with_detection

                    elif section == "exploitation":
                        if cat_coverage.docs_with_testing > 0:
                            cell.has_content = True
                            if cat_coverage.docs_with_testing >= cat_coverage.total_docs * 0.8:
                                cell.coverage_level = CoverageLevel.FULL
                            elif cat_coverage.docs_with_testing >= cat_coverage.total_docs * 0.5:
                                cell.coverage_level = CoverageLevel.PARTIAL
                            else:
                                cell.coverage_level = CoverageLevel.MINIMAL
                        cell.doc_count = cat_coverage.docs_with_testing

                    elif section == "mitigation":
                        if cat_coverage.docs_with_fixes > 0:
                            cell.has_content = True
                            if cat_coverage.docs_with_fixes >= cat_coverage.total_docs * 0.8:
                                cell.coverage_level = CoverageLevel.FULL
                            elif cat_coverage.docs_with_fixes >= cat_coverage.total_docs * 0.5:
                                cell.coverage_level = CoverageLevel.PARTIAL
                            else:
                                cell.coverage_level = CoverageLevel.MINIMAL
                        cell.doc_count = cat_coverage.docs_with_fixes

                    elif section == "examples":
                        if cat_coverage.docs_with_exploits > 0:
                            cell.has_content = True
                            if cat_coverage.docs_with_exploits >= cat_coverage.total_docs * 0.8:
                                cell.coverage_level = CoverageLevel.FULL
                            elif cat_coverage.docs_with_exploits >= cat_coverage.total_docs * 0.5:
                                cell.coverage_level = CoverageLevel.PARTIAL
                            else:
                                cell.coverage_level = CoverageLevel.MINIMAL
                        cell.doc_count = cat_coverage.docs_with_exploits

                matrix.cells.append(cell)

        # Calculate summary
        matrix.total_cells = len(matrix.cells)
        matrix.covered_cells = sum(
            1 for c in matrix.cells if c.coverage_level != CoverageLevel.NONE
        )
        if matrix.total_cells > 0:
            matrix.coverage_percent = matrix.covered_cells / matrix.total_cells * 100

        return matrix

    def generate_full_report(
        self,
        format: ReportFormat = ReportFormat.MARKDOWN,
    ) -> str:
        """Generate comprehensive coverage report.

        Args:
            format: Output format

        Returns:
            Formatted report string
        """
        # Gather data
        coverage_report = self.analyzer.analyze()
        gap_result = self.gap_finder.find_all_gaps()
        matrix = self.generate_matrix()

        if format == ReportFormat.JSON:
            return self._format_json(coverage_report, gap_result, matrix)
        elif format == ReportFormat.TOON:
            return self._format_toon(coverage_report, gap_result, matrix)
        elif format == ReportFormat.CSV:
            return self._format_csv(coverage_report, gap_result, matrix)
        elif format == ReportFormat.HTML:
            return self._format_html(coverage_report, gap_result, matrix)
        else:
            return self._format_markdown(coverage_report, gap_result, matrix)

    def _format_markdown(
        self,
        coverage: CoverageReport,
        gaps: GapAnalysisResult,
        matrix: CoverageMatrix,
    ) -> str:
        """Format as markdown."""
        lines = [
            "# VulnDocs Knowledge Coverage Report",
            "",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
            "## Executive Summary",
            "",
            f"- **Overall Coverage:** {coverage.overall_coverage:.1f}%",
            f"- **Threat Model Coverage:** {coverage.threat_model_coverage:.1f}%",
            f"- **Documents:** {coverage.total_documents}",
            f"- **Patterns Linked:** {coverage.linked_patterns}/{coverage.total_patterns}",
            f"- **Critical Gaps:** {gaps.critical_count}",
            "",
            "## Coverage Matrix",
            "",
            matrix.to_markdown(),
            "",
            "## Category Details",
            "",
        ]

        # Category details
        for cat in coverage.categories:
            critical_marker = " 🔴" if cat.is_critical else ""
            lines.extend([
                f"### {cat.display_name}{critical_marker}",
                "",
                f"- **Documents:** {cat.total_docs}",
                f"- **Subcategories:** {cat.covered_subcategories}/{cat.expected_subcategories}",
                f"- **Patterns:** {cat.linked_patterns}/{cat.expected_patterns}",
                f"- **Coverage:** {cat.coverage_percent:.0f}% ({cat.coverage_level.value})",
                "",
            ])

            if cat.missing_subcategories:
                lines.append(f"**Missing Subcategories:** {', '.join(cat.missing_subcategories)}")
                lines.append("")

            if cat.missing_patterns:
                lines.append(f"**Missing Patterns:** {', '.join(cat.missing_patterns)}")
                lines.append("")

        # Gap summary
        if gaps.gaps:
            lines.extend([
                "## Knowledge Gaps",
                "",
                f"Total gaps identified: {len(gaps.gaps)}",
                "",
                f"- Critical: {gaps.critical_count}",
                f"- High: {gaps.high_count}",
                f"- Medium: {gaps.medium_count}",
                f"- Low: {gaps.low_count}",
                "",
                "### Top Priority Gaps",
                "",
            ])

            for gap in gaps.priority_queue[:10]:
                lines.extend([
                    f"**{gap.title}** ({gap.severity.value})",
                    f"- {gap.description}",
                    f"- *Recommendation:* {gap.recommendation}",
                    f"- *Effort:* {gap.effort}",
                    "",
                ])

        # Completeness scores
        lines.extend([
            "## Completeness Scores",
            "",
            f"- **Overall:** {gaps.overall_completeness:.1f}%",
            f"- **Detection:** {gaps.detection_completeness:.1f}%",
            f"- **Exploitation:** {gaps.exploitation_completeness:.1f}%",
            f"- **Mitigation:** {gaps.mitigation_completeness:.1f}%",
            "",
        ])

        return "\n".join(lines)

    def _format_json(
        self,
        coverage: CoverageReport,
        gaps: GapAnalysisResult,
        matrix: CoverageMatrix,
    ) -> str:
        """Format as JSON."""
        data = {
            "generated": datetime.now().isoformat(),
            "coverage": coverage.to_dict(),
            "gaps": gaps.to_dict(),
            "matrix": matrix.to_dict(),
        }
        return json.dumps(data, indent=2)

    def _format_toon(
        self,
        coverage: CoverageReport,
        gaps: GapAnalysisResult,
        matrix: CoverageMatrix,
    ) -> str:
        """Format in TOON for LLM consumption."""
        lines = [
            "[VULNDOCS_COVERAGE]",
            f"overall={coverage.overall_coverage:.0f}% threat_model={coverage.threat_model_coverage:.0f}%",
            f"docs={coverage.total_documents} patterns={coverage.linked_patterns}/{coverage.total_patterns}",
            f"gaps: critical={gaps.critical_count} high={gaps.high_count} medium={gaps.medium_count}",
            "",
            matrix.to_toon(),
            "",
            "[CATEGORY_STATUS]",
        ]

        for cat in coverage.categories:
            status = cat.coverage_level.value[0].upper()  # F/P/M/N
            critical = "!" if cat.is_critical else ""
            lines.append(
                f"{cat.display_name}{critical}: {status} "
                f"({cat.covered_subcategories}/{cat.expected_subcategories}sub "
                f"{cat.linked_patterns}/{cat.expected_patterns}pat)"
            )

        lines.append("[/CATEGORY_STATUS]")

        if gaps.priority_queue:
            lines.extend([
                "",
                "[PRIORITY_GAPS]",
            ])
            for gap in gaps.priority_queue[:5]:
                sev = gap.severity.value[0].upper()
                lines.append(f"{sev}: {gap.title} -> {gap.recommendation}")
            lines.append("[/PRIORITY_GAPS]")

        lines.extend([
            "",
            "[COMPLETENESS]",
            f"detection={gaps.detection_completeness:.0f}%",
            f"exploitation={gaps.exploitation_completeness:.0f}%",
            f"mitigation={gaps.mitigation_completeness:.0f}%",
            "[/COMPLETENESS]",
            "",
            "[/VULNDOCS_COVERAGE]",
        ])

        return "\n".join(lines)

    def _format_csv(
        self,
        coverage: CoverageReport,
        gaps: GapAnalysisResult,
        matrix: CoverageMatrix,
    ) -> str:
        """Format as CSV."""
        lines = [
            "# Coverage Report",
            "metric,value",
            f"overall_coverage,{coverage.overall_coverage:.1f}",
            f"threat_model_coverage,{coverage.threat_model_coverage:.1f}",
            f"total_documents,{coverage.total_documents}",
            f"linked_patterns,{coverage.linked_patterns}",
            f"total_patterns,{coverage.total_patterns}",
            f"critical_gaps,{gaps.critical_count}",
            "",
            "# Category Coverage",
            "category,display_name,is_critical,docs,subcats_covered,subcats_expected,patterns_linked,patterns_expected,coverage_percent,level",
        ]

        for cat in coverage.categories:
            lines.append(
                f"{cat.category},{cat.display_name},{cat.is_critical},"
                f"{cat.total_docs},{cat.covered_subcategories},{cat.expected_subcategories},"
                f"{cat.linked_patterns},{cat.expected_patterns},"
                f"{cat.coverage_percent:.1f},{cat.coverage_level.value}"
            )

        lines.extend([
            "",
            "# Gaps",
            "severity,type,category,title,recommendation,effort,priority",
        ])

        for gap in gaps.gaps:
            lines.append(
                f"{gap.severity.value},{gap.gap_type.value},{gap.category},"
                f"\"{gap.title}\",\"{gap.recommendation}\",{gap.effort},{gap.priority}"
            )

        return "\n".join(lines)

    def _format_html(
        self,
        coverage: CoverageReport,
        gaps: GapAnalysisResult,
        matrix: CoverageMatrix,
    ) -> str:
        """Format as HTML."""
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<title>VulnDocs Coverage Report</title>",
            "<style>",
            "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }",
            "h1, h2, h3 { color: #333; }",
            "table { border-collapse: collapse; width: 100%; margin: 20px 0; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background: #f5f5f5; }",
            ".critical { color: #d32f2f; }",
            ".high { color: #f57c00; }",
            ".medium { color: #fbc02d; }",
            ".low { color: #388e3c; }",
            ".coverage-full { background: #c8e6c9; }",
            ".coverage-partial { background: #fff9c4; }",
            ".coverage-minimal { background: #ffe0b2; }",
            ".coverage-none { background: #ffcdd2; }",
            ".metric { display: inline-block; margin: 10px; padding: 10px; background: #f5f5f5; border-radius: 4px; }",
            ".metric-value { font-size: 24px; font-weight: bold; }",
            ".metric-label { font-size: 12px; color: #666; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>VulnDocs Coverage Report</h1>",
            f"<p><em>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</em></p>",
            "",
            "<h2>Summary</h2>",
            "<div>",
            f"<div class='metric'><div class='metric-value'>{coverage.overall_coverage:.0f}%</div><div class='metric-label'>Overall Coverage</div></div>",
            f"<div class='metric'><div class='metric-value'>{coverage.total_documents}</div><div class='metric-label'>Documents</div></div>",
            f"<div class='metric'><div class='metric-value'>{coverage.linked_patterns}/{coverage.total_patterns}</div><div class='metric-label'>Patterns</div></div>",
            f"<div class='metric'><div class='metric-value critical'>{gaps.critical_count}</div><div class='metric-label'>Critical Gaps</div></div>",
            "</div>",
            "",
            "<h2>Coverage Matrix</h2>",
            "<table>",
            "<tr><th>Category</th><th>Detection</th><th>Exploitation</th><th>Mitigation</th><th>Examples</th></tr>",
        ]

        for category in matrix.categories:
            cat_display = THREAT_MODEL_CATEGORIES.get(category, {}).get("display", category)
            html.append(f"<tr><td>{cat_display}</td>")
            for section in matrix.sections:
                cell = matrix.get_cell(category, section)
                if cell:
                    css_class = f"coverage-{cell.coverage_level.value}"
                    html.append(f"<td class='{css_class}'>{cell.coverage_level.value}</td>")
                else:
                    html.append("<td>-</td>")
            html.append("</tr>")

        html.extend([
            "</table>",
            "",
            "<h2>Priority Gaps</h2>",
            "<table>",
            "<tr><th>Severity</th><th>Title</th><th>Recommendation</th><th>Effort</th></tr>",
        ])

        for gap in gaps.priority_queue[:10]:
            html.append(
                f"<tr><td class='{gap.severity.value}'>{gap.severity.value}</td>"
                f"<td>{gap.title}</td>"
                f"<td>{gap.recommendation}</td>"
                f"<td>{gap.effort}</td></tr>"
            )

        html.extend([
            "</table>",
            "</body>",
            "</html>",
        ])

        return "\n".join(html)

    def export(
        self,
        content: str,
        format: ReportFormat,
        filepath: str,
    ) -> None:
        """Export report to file.

        Args:
            content: Report content
            format: Report format
            filepath: Output file path
        """
        with open(filepath, "w") as f:
            f.write(content)


# =============================================================================
# Convenience Functions
# =============================================================================


def generate_coverage_report(format: ReportFormat = ReportFormat.MARKDOWN) -> str:
    """Generate coverage report in specified format.

    Args:
        format: Output format

    Returns:
        Formatted report string
    """
    generator = ReportGenerator()
    return generator.generate_full_report(format)


def generate_coverage_matrix() -> CoverageMatrix:
    """Generate coverage matrix.

    Returns:
        CoverageMatrix instance
    """
    generator = ReportGenerator()
    return generator.generate_matrix()


def get_toon_summary() -> str:
    """Get TOON-formatted coverage summary for LLM.

    Returns:
        TOON-formatted string
    """
    generator = ReportGenerator()
    return generator.generate_full_report(ReportFormat.TOON)
