"""Phase 20: Report Generation.

This module provides functionality for generating security reports
in various formats (HTML, Markdown, JSON).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from alphaswarm_sol.kg.schema import KnowledgeGraph


class ReportFormat(str, Enum):
    """Supported report formats."""
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"
    TEXT = "text"


class Severity(str, Enum):
    """Finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Verdict(str, Enum):
    """Verdict for a finding after verification."""
    PENDING = "pending"              # Not yet verified
    CONFIRMED = "confirmed"          # Verified as true positive
    FALSE_POSITIVE = "false_positive"  # Verified as false positive
    INCONCLUSIVE = "inconclusive"    # Could not determine
    WONT_FIX = "wont_fix"            # True positive but accepted risk


class TestResult(str, Enum):
    """Result of test execution."""
    NOT_RUN = "not_run"
    PASSED = "passed"      # Test ran and assertion passed (vuln confirmed)
    FAILED = "failed"      # Test ran but assertion failed (might be FP)
    ERROR = "error"        # Test threw error (compilation, runtime)


@dataclass
class Finding:
    """A security finding with optional verification status.

    Attributes:
        id: Finding identifier (e.g., "VKG-001")
        title: Finding title
        severity: Severity level
        description: Description
        location: Code location
        evidence: Evidence for the finding
        recommendation: Fix recommendation

        # Verification fields (Task 4.9)
        verdict: Verification verdict
        verdict_evidence: Evidence supporting verdict
        verdict_timestamp: When verdict was set
        test_scaffold_id: ID of generated test scaffold
        test_result: Result of test execution
        auditor_notes: Free-form notes from auditor
    """
    # Original fields
    id: str
    title: str
    severity: Severity
    description: str = ""
    location: str = ""
    evidence: List[str] = field(default_factory=list)
    recommendation: str = ""

    # Verification fields (NEW - Task 4.9)
    verdict: Verdict = Verdict.PENDING
    verdict_evidence: List[str] = field(default_factory=list)
    verdict_timestamp: Optional[datetime] = None
    test_scaffold_id: Optional[str] = None
    test_result: TestResult = TestResult.NOT_RUN
    auditor_notes: str = ""

    def set_verdict(
        self,
        verdict: Verdict,
        evidence: Optional[List[str]] = None,
        notes: str = "",
    ) -> None:
        """Set the verdict for this finding.

        Args:
            verdict: The verdict
            evidence: Evidence supporting the verdict
            notes: Auditor notes
        """
        self.verdict = verdict
        self.verdict_evidence = evidence or []
        self.verdict_timestamp = datetime.now()
        if notes:
            self.auditor_notes = notes

    def link_test(self, scaffold_id: str) -> None:
        """Link a test scaffold to this finding.

        Args:
            scaffold_id: ID of the test scaffold
        """
        self.test_scaffold_id = scaffold_id

    def record_test_result(self, result: TestResult) -> None:
        """Record the result of test execution.

        Args:
            result: The test result
        """
        self.test_result = result

    @property
    def is_verified(self) -> bool:
        """Check if finding has been verified."""
        return self.verdict != Verdict.PENDING

    @property
    def is_true_positive(self) -> bool:
        """Check if finding is confirmed true positive."""
        return self.verdict == Verdict.CONFIRMED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity.value,
            "description": self.description,
            "location": self.location,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            # Verification fields
            "verdict": self.verdict.value,
            "verdict_evidence": self.verdict_evidence,
            "verdict_timestamp": self.verdict_timestamp.isoformat() if self.verdict_timestamp else None,
            "test_scaffold_id": self.test_scaffold_id,
            "test_result": self.test_result.value,
            "auditor_notes": self.auditor_notes,
        }


@dataclass
class ReportSection:
    """A section of the report.

    Attributes:
        title: Section title
        content: Section content
        findings: Findings in this section
        subsections: Nested subsections
    """
    title: str
    content: str = ""
    findings: List[Finding] = field(default_factory=list)
    subsections: List["ReportSection"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "content": self.content,
            "findings": [f.to_dict() for f in self.findings],
            "subsections": [s.to_dict() for s in self.subsections],
        }


@dataclass
class SecurityReport:
    """Complete security report.

    Attributes:
        title: Report title
        project_name: Name of the audited project
        date: Report date
        auditor: Auditor name
        summary: Executive summary
        sections: Report sections
        findings: All findings
        metadata: Additional metadata
    """
    title: str
    project_name: str = ""
    date: str = field(default_factory=lambda: datetime.now().isoformat()[:10])
    auditor: str = "True VKG"
    summary: str = ""
    sections: List[ReportSection] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.LOW)

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "project_name": self.project_name,
            "date": self.date,
            "auditor": self.auditor,
            "summary": self.summary,
            "sections": [s.to_dict() for s in self.sections],
            "findings": [f.to_dict() for f in self.findings],
            "metadata": self.metadata,
            "stats": {
                "total": self.total_findings,
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
            },
        }

    def add_finding(self, finding: Finding) -> None:
        """Add a finding to the report."""
        self.findings.append(finding)

    def add_section(self, section: ReportSection) -> None:
        """Add a section to the report."""
        self.sections.append(section)


class ReportGenerator:
    """Generates security reports from knowledge graphs.

    Analyzes the graph and produces formatted reports.
    """

    def __init__(self, graph: KnowledgeGraph):
        """Initialize generator.

        Args:
            graph: Knowledge graph to report on
        """
        self.graph = graph

    def generate(
        self,
        project_name: str = "",
        include_info: bool = True,
    ) -> SecurityReport:
        """Generate a security report.

        Args:
            project_name: Name of the project
            include_info: Whether to include INFO findings

        Returns:
            SecurityReport
        """
        report = SecurityReport(
            title=f"Security Analysis Report: {project_name or 'Unknown Project'}",
            project_name=project_name,
        )

        # Extract findings from graph
        findings = self._extract_findings(include_info)
        for finding in findings:
            report.add_finding(finding)

        # Create sections
        report.add_section(self._create_summary_section(findings))
        report.add_section(self._create_findings_section(findings))
        report.add_section(self._create_contracts_section())

        # Generate summary
        report.summary = self._generate_summary(report)

        return report

    def _extract_findings(self, include_info: bool) -> List[Finding]:
        """Extract findings from the graph."""
        findings: List[Finding] = []
        finding_counter = 0

        for node in self.graph.nodes.values():
            if node.type != "Function":
                continue

            props = node.properties
            contract_name = props.get("contract_name", "Unknown")
            location = f"{contract_name}.{node.label}"

            # Check for reentrancy
            if props.get("state_write_after_external_call"):
                if not props.get("has_reentrancy_guard"):
                    finding_counter += 1
                    findings.append(Finding(
                        id=f"REEN-{finding_counter:03d}",
                        title="Potential Reentrancy Vulnerability",
                        severity=Severity.CRITICAL,
                        description="State is modified after an external call without a reentrancy guard.",
                        location=location,
                        evidence=["state_write_after_external_call=True", "has_reentrancy_guard=False"],
                        recommendation="Add a ReentrancyGuard or use the CEI pattern.",
                    ))

            # Check for access control
            if props.get("writes_privileged_state"):
                if not props.get("has_access_gate"):
                    finding_counter += 1
                    findings.append(Finding(
                        id=f"AUTH-{finding_counter:03d}",
                        title="Missing Access Control",
                        severity=Severity.HIGH,
                        description="Function modifies privileged state without access control.",
                        location=location,
                        evidence=["writes_privileged_state=True", "has_access_gate=False"],
                        recommendation="Add access control modifier (onlyOwner, onlyRole).",
                    ))

            # Check for oracle issues
            if props.get("reads_oracle_price"):
                if not props.get("has_staleness_check"):
                    finding_counter += 1
                    findings.append(Finding(
                        id=f"ORAC-{finding_counter:03d}",
                        title="Oracle Price Without Staleness Check",
                        severity=Severity.MEDIUM,
                        description="Oracle price is read without checking for staleness.",
                        location=location,
                        evidence=["reads_oracle_price=True", "has_staleness_check=False"],
                        recommendation="Add staleness check for oracle prices.",
                    ))

            # Check for DoS
            if props.get("has_unbounded_loop"):
                finding_counter += 1
                findings.append(Finding(
                    id=f"DOS-{finding_counter:03d}",
                    title="Unbounded Loop",
                    severity=Severity.MEDIUM,
                    description="Function contains an unbounded loop that could cause DoS.",
                    location=location,
                    evidence=["has_unbounded_loop=True"],
                    recommendation="Add loop bounds or use pagination.",
                ))

            # Check for slippage
            if props.get("swap_like") and props.get("risk_missing_slippage_parameter"):
                finding_counter += 1
                findings.append(Finding(
                    id=f"SLIP-{finding_counter:03d}",
                    title="Missing Slippage Protection",
                    severity=Severity.MEDIUM,
                    description="Swap function lacks slippage protection parameter.",
                    location=location,
                    evidence=["swap_like=True", "risk_missing_slippage_parameter=True"],
                    recommendation="Add minAmountOut parameter for slippage protection.",
                ))

            # Check for ecrecover
            if props.get("uses_ecrecover"):
                if not props.get("checks_zero_address"):
                    finding_counter += 1
                    findings.append(Finding(
                        id=f"SIG-{finding_counter:03d}",
                        title="Unchecked ecrecover Result",
                        severity=Severity.MEDIUM,
                        description="ecrecover result is not checked for zero address.",
                        location=location,
                        evidence=["uses_ecrecover=True", "checks_zero_address=False"],
                        recommendation="Check that recovered address is not zero.",
                    ))

        # Sort by severity
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        findings.sort(key=lambda f: severity_order[f.severity])

        return findings

    def _create_summary_section(self, findings: List[Finding]) -> ReportSection:
        """Create the summary section."""
        critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high = sum(1 for f in findings if f.severity == Severity.HIGH)
        medium = sum(1 for f in findings if f.severity == Severity.MEDIUM)
        low = sum(1 for f in findings if f.severity == Severity.LOW)

        content = f"""
This report summarizes the security analysis of the smart contracts.

**Finding Summary:**
- Critical: {critical}
- High: {high}
- Medium: {medium}
- Low: {low}
- Total: {len(findings)}
"""

        return ReportSection(
            title="Executive Summary",
            content=content.strip(),
        )

    def _create_findings_section(self, findings: List[Finding]) -> ReportSection:
        """Create the findings section."""
        return ReportSection(
            title="Detailed Findings",
            findings=findings,
        )

    def _create_contracts_section(self) -> ReportSection:
        """Create the contracts overview section."""
        contracts: Dict[str, int] = {}

        for node in self.graph.nodes.values():
            if node.type == "Function":
                contract = node.properties.get("contract_name", "Unknown")
                contracts[contract] = contracts.get(contract, 0) + 1

        content = "**Analyzed Contracts:**\n"
        for contract, func_count in sorted(contracts.items()):
            content += f"- {contract}: {func_count} functions\n"

        return ReportSection(
            title="Contracts Overview",
            content=content.strip(),
        )

    def _generate_summary(self, report: SecurityReport) -> str:
        """Generate executive summary."""
        if report.critical_count > 0:
            risk = "CRITICAL"
        elif report.high_count > 0:
            risk = "HIGH"
        elif report.medium_count > 0:
            risk = "MEDIUM"
        elif report.total_findings > 0:
            risk = "LOW"
        else:
            risk = "NONE"

        return f"Overall Risk Level: {risk}. Found {report.total_findings} issues."

    def to_markdown(self, report: SecurityReport) -> str:
        """Convert report to Markdown format."""
        lines = [
            f"# {report.title}",
            "",
            f"**Date:** {report.date}",
            f"**Auditor:** {report.auditor}",
            "",
            f"## Summary",
            f"{report.summary}",
            "",
        ]

        for section in report.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            if section.content:
                lines.append(section.content)
                lines.append("")

            for finding in section.findings:
                lines.append(f"### [{finding.severity.value.upper()}] {finding.id}: {finding.title}")
                lines.append("")
                lines.append(f"**Location:** `{finding.location}`")
                lines.append("")
                lines.append(finding.description)
                lines.append("")
                if finding.evidence:
                    lines.append("**Evidence:**")
                    for e in finding.evidence:
                        lines.append(f"- `{e}`")
                    lines.append("")
                if finding.recommendation:
                    lines.append(f"**Recommendation:** {finding.recommendation}")
                    lines.append("")

        return "\n".join(lines)

    def to_html(self, report: SecurityReport) -> str:
        """Convert report to HTML format."""
        severity_colors = {
            Severity.CRITICAL: "#dc3545",
            Severity.HIGH: "#fd7e14",
            Severity.MEDIUM: "#ffc107",
            Severity.LOW: "#17a2b8",
            Severity.INFO: "#6c757d",
        }

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{report.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; border-bottom: 1px solid #ddd; }}
        .finding {{ margin: 20px 0; padding: 15px; border-radius: 5px; }}
        .critical {{ background: #fce4e4; border-left: 4px solid #dc3545; }}
        .high {{ background: #fff3e0; border-left: 4px solid #fd7e14; }}
        .medium {{ background: #fffde7; border-left: 4px solid #ffc107; }}
        .low {{ background: #e3f2fd; border-left: 4px solid #17a2b8; }}
        .location {{ font-family: monospace; background: #f5f5f5; padding: 2px 6px; }}
        .evidence {{ font-family: monospace; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>{report.title}</h1>
    <p><strong>Date:</strong> {report.date} | <strong>Auditor:</strong> {report.auditor}</p>
    <p><strong>Summary:</strong> {report.summary}</p>
"""

        for section in report.sections:
            html += f"<h2>{section.title}</h2>\n"
            if section.content:
                html += f"<p>{section.content.replace(chr(10), '<br>')}</p>\n"

            for finding in section.findings:
                html += f"""
    <div class="finding {finding.severity.value}">
        <h3>[{finding.severity.value.upper()}] {finding.id}: {finding.title}</h3>
        <p><span class="location">{finding.location}</span></p>
        <p>{finding.description}</p>
        <p><strong>Recommendation:</strong> {finding.recommendation}</p>
    </div>
"""

        html += "</body></html>"
        return html


def generate_report(
    graph: KnowledgeGraph,
    project_name: str = "",
    format: ReportFormat = ReportFormat.MARKDOWN,
) -> str:
    """Generate a security report from a knowledge graph.

    Convenience function for quick report generation.

    Args:
        graph: Knowledge graph to report on
        project_name: Name of the project
        format: Output format

    Returns:
        Formatted report string
    """
    generator = ReportGenerator(graph)
    report = generator.generate(project_name)

    if format == ReportFormat.MARKDOWN:
        return generator.to_markdown(report)
    elif format == ReportFormat.HTML:
        return generator.to_html(report)
    elif format == ReportFormat.JSON:
        import json
        return json.dumps(report.to_dict(), indent=2)
    else:
        return generator.to_markdown(report)


__all__ = [
    "ReportFormat",
    "Severity",
    "Verdict",
    "TestResult",
    "Finding",
    "ReportSection",
    "SecurityReport",
    "ReportGenerator",
    "generate_report",
]
