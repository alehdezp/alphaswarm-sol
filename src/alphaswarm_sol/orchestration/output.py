"""Output Report Generation for Orchestrator Mode (Phase 5 Task 5.8).

Generates combined reports from orchestrated tool runs with economic risk metadata.

Per 05.11-CONTEXT.md: Risk metadata with game-theoretic, causal, and systemic
components is included in findings for prioritization (not correctness).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from alphaswarm_sol.orchestration.runner import ToolResult, ToolStatus
from alphaswarm_sol.orchestration.dedup import DeduplicatedFinding, get_disagreements

if TYPE_CHECKING:
    from alphaswarm_sol.economics.risk import RiskBreakdown


@dataclass
class FindingRiskMetadata:
    """Economic risk metadata for a finding.

    Per 05.11-CONTEXT.md: Risk metadata with three components:
    1. Base risk (VAR, PRIV, OFFCHAIN, GOV, INCENTIVE)
    2. Game-theoretic EV adjustment
    3. Causal amplification factor
    4. Systemic risk factor

    This metadata affects prioritization only, not correctness.
    """

    economic_risk: float = 0.0  # Total risk score 0-10
    attack_ev_score: float = 1.0  # Game-theoretic EV multiplier
    loss_amplification: float = 1.0  # Causal loss amplification
    systemic_risk: float = 1.0  # Cross-protocol systemic factor
    risk_breakdown: Optional[Dict[str, Any]] = None  # Full breakdown
    priority: str = "medium"  # Derived priority level

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "economic_risk": round(self.economic_risk, 2),
            "attack_ev_score": round(self.attack_ev_score, 2),
            "loss_amplification": round(self.loss_amplification, 2),
            "systemic_risk": round(self.systemic_risk, 2),
            "risk_breakdown": self.risk_breakdown,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FindingRiskMetadata":
        """Create FindingRiskMetadata from dictionary."""
        return cls(
            economic_risk=float(data.get("economic_risk", 0.0)),
            attack_ev_score=float(data.get("attack_ev_score", 1.0)),
            loss_amplification=float(data.get("loss_amplification", 1.0)),
            systemic_risk=float(data.get("systemic_risk", 1.0)),
            risk_breakdown=data.get("risk_breakdown"),
            priority=str(data.get("priority", "medium")),
        )

    @classmethod
    def from_risk_breakdown(cls, breakdown: "RiskBreakdown") -> "FindingRiskMetadata":
        """Create FindingRiskMetadata from RiskBreakdown.

        Args:
            breakdown: RiskBreakdown from economic risk scorer

        Returns:
            FindingRiskMetadata instance
        """
        return cls(
            economic_risk=breakdown.total_score,
            attack_ev_score=breakdown.attack_ev_score,
            loss_amplification=breakdown.loss_amplification_factor,
            systemic_risk=breakdown.systemic_risk_factor,
            risk_breakdown=breakdown.to_dict(),
            priority=breakdown.priority.value,
        )


@dataclass
class OrchestratorReport:
    """Combined report from orchestrator run.

    Contains aggregated findings from all tools with deduplication,
    agreement analysis, and economic risk metadata.

    Per 05.11-CONTEXT.md: Findings include risk metadata with:
    - Game-theoretic expected value
    - Causal loss amplification
    - Cross-protocol systemic risk
    """

    project: str
    timestamp: str
    tools_run: List[str] = field(default_factory=list)
    tools_skipped: List[str] = field(default_factory=list)
    total_findings: int = 0
    deduplicated_findings: int = 0
    findings_by_tool: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    disagreements: int = 0
    high_confidence_count: int = 0
    high_economic_risk_count: int = 0  # Count of findings with risk >= 6
    findings: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "project": self.project,
            "timestamp": self.timestamp,
            "summary": {
                "tools_run": self.tools_run,
                "tools_skipped": self.tools_skipped,
                "total_raw_findings": self.total_findings,
                "deduplicated_findings": self.deduplicated_findings,
                "disagreements": self.disagreements,
                "high_confidence": self.high_confidence_count,
                "high_economic_risk": self.high_economic_risk_count,
            },
            "tools": self.findings_by_tool,
            "findings": self.findings,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: Path) -> None:
        """Save report to file.

        Args:
            path: Output file path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.to_json())


def generate_report(
    project_path: str,
    tool_results: List[ToolResult],
    deduped: List[DeduplicatedFinding],
    risk_metadata: Optional[Dict[str, "FindingRiskMetadata"]] = None,
) -> OrchestratorReport:
    """Generate orchestrator report from tool results.

    Per 05.11-CONTEXT.md: Include economic risk metadata in findings for
    prioritization (not correctness).

    Args:
        project_path: Path to analyzed project
        tool_results: Results from each tool
        deduped: Deduplicated findings
        risk_metadata: Optional mapping from finding ID to risk metadata

    Returns:
        Complete orchestrator report with economic risk metrics
    """
    tools_run = [r.tool for r in tool_results if r.status == ToolStatus.SUCCESS]
    tools_skipped = [r.tool for r in tool_results if r.status != ToolStatus.SUCCESS]

    # Build per-tool summary
    findings_by_tool: Dict[str, Dict[str, Any]] = {}
    for r in tool_results:
        findings_by_tool[r.tool] = {
            "status": r.status.value,
            "count": len(r.findings),
            "execution_time_seconds": round(r.execution_time, 2),
            "error": r.error,
        }

    # Count various metrics
    total_findings = sum(
        len(r.findings) for r in tool_results if r.status == ToolStatus.SUCCESS
    )
    disagreements = len(get_disagreements(deduped))
    high_confidence = sum(1 for d in deduped if d.high_confidence)

    # Build findings with risk metadata
    findings_list = []
    high_economic_risk_count = 0
    risk_metadata = risk_metadata or {}

    for d in deduped:
        finding_dict = d.to_dict()

        # Add risk metadata if available
        finding_id = finding_dict.get("id", "")
        if finding_id and finding_id in risk_metadata:
            risk_meta = risk_metadata[finding_id]
            finding_dict["risk_metadata"] = risk_meta.to_dict()
            if risk_meta.economic_risk >= 6.0:
                high_economic_risk_count += 1

        findings_list.append(finding_dict)

    return OrchestratorReport(
        project=project_path,
        timestamp=datetime.now().isoformat(),
        tools_run=tools_run,
        tools_skipped=tools_skipped,
        total_findings=total_findings,
        deduplicated_findings=len(deduped),
        findings_by_tool=findings_by_tool,
        disagreements=disagreements,
        high_confidence_count=high_confidence,
        high_economic_risk_count=high_economic_risk_count,
        findings=findings_list,
    )


def format_report(report: OrchestratorReport, verbose: bool = False) -> str:
    """Format report as human-readable text.

    Args:
        report: Orchestrator report
        verbose: Include detailed findings

    Returns:
        Formatted string
    """
    lines = []
    lines.append("=" * 60)
    lines.append("ORCHESTRATOR REPORT")
    lines.append("=" * 60)
    lines.append(f"Project: {report.project}")
    lines.append(f"Timestamp: {report.timestamp}")
    lines.append("")

    # Tool summary
    lines.append("TOOLS:")
    for tool in report.tools_run:
        info = report.findings_by_tool.get(tool, {})
        count = info.get("count", 0)
        time_s = info.get("execution_time_seconds", 0)
        lines.append(f"  ✓ {tool}: {count} findings ({time_s:.1f}s)")

    for tool in report.tools_skipped:
        info = report.findings_by_tool.get(tool, {})
        error = info.get("error", "skipped")
        lines.append(f"  ✗ {tool}: {error}")

    lines.append("")

    # Findings summary
    lines.append("FINDINGS SUMMARY:")
    lines.append(f"  Total raw findings: {report.total_findings}")
    lines.append(f"  After deduplication: {report.deduplicated_findings}")
    lines.append(f"  High confidence (multi-tool): {report.high_confidence_count}")
    lines.append(f"  High economic risk (>=6): {report.high_economic_risk_count}")
    lines.append(f"  Disagreements: {report.disagreements}")
    lines.append("")

    # Severity breakdown
    severity_counts: Dict[str, int] = {}
    for f in report.findings:
        sev = f.get("severity", "unknown")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    lines.append("BY SEVERITY:")
    for sev in ["critical", "high", "medium", "low", "info"]:
        if sev in severity_counts:
            lines.append(f"  {sev.upper()}: {severity_counts[sev]}")

    if verbose and report.findings:
        lines.append("")
        lines.append("DETAILED FINDINGS:")
        lines.append("-" * 40)
        for f in report.findings:
            sources = ", ".join(f.get("sources", []))
            agreement = "✓" if f.get("agreement") else "⚠"
            lines.append(
                f"  [{f.get('severity', 'unknown').upper()}] {f.get('category', 'unknown')}"
            )
            lines.append(f"    File: {f.get('file', 'unknown')}:{f.get('line', 0)}")
            lines.append(f"    Sources: {sources} {agreement}")
            lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def format_markdown_report(report: OrchestratorReport) -> str:
    """Format report as Markdown.

    Args:
        report: Orchestrator report

    Returns:
        Markdown formatted string
    """
    lines = []
    lines.append(f"# Orchestrator Report: {report.project}")
    lines.append("")
    lines.append(f"*Generated: {report.timestamp}*")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Tools Run | {', '.join(report.tools_run)} |")
    lines.append(f"| Total Raw Findings | {report.total_findings} |")
    lines.append(f"| Deduplicated | {report.deduplicated_findings} |")
    lines.append(f"| High Confidence | {report.high_confidence_count} |")
    lines.append(f"| High Economic Risk | {report.high_economic_risk_count} |")
    lines.append(f"| Disagreements | {report.disagreements} |")
    lines.append("")

    # Tool breakdown
    lines.append("## Tool Results")
    lines.append("")
    lines.append("| Tool | Status | Findings | Time |")
    lines.append("|------|--------|----------|------|")
    for tool, info in report.findings_by_tool.items():
        status = "✓" if info.get("status") == "success" else "✗"
        count = info.get("count", 0)
        time_s = info.get("execution_time_seconds", 0)
        lines.append(f"| {tool} | {status} | {count} | {time_s:.1f}s |")
    lines.append("")

    # Findings by severity
    lines.append("## Findings by Severity")
    lines.append("")
    for sev in ["critical", "high", "medium", "low"]:
        sev_findings = [f for f in report.findings if f.get("severity") == sev]
        if sev_findings:
            lines.append(f"### {sev.upper()} ({len(sev_findings)})")
            lines.append("")
            for f in sev_findings:
                sources = ", ".join(f.get("sources", []))
                agreement = "✓ agreed" if f.get("agreement") else "⚠ disagreement"
                lines.append(f"- **{f.get('category', 'unknown')}**")
                lines.append(f"  - Location: `{f.get('file', 'unknown')}:{f.get('line', 0)}`")
                lines.append(f"  - Sources: {sources} ({agreement})")
            lines.append("")

    # Disagreements section
    disagreements = [f for f in report.findings if not f.get("agreement")]
    if disagreements:
        lines.append("## ⚠ Disagreements (Manual Review Required)")
        lines.append("")
        lines.append("These findings have conflicting assessments from different tools:")
        lines.append("")
        for f in disagreements:
            lines.append(f"- **{f.get('file', 'unknown')}:{f.get('line', 0)}**")
            lines.append(f"  - Category: {f.get('category', 'unknown')}")
            lines.append(f"  - Sources: {', '.join(f.get('sources', []))}")
        lines.append("")

    return "\n".join(lines)
