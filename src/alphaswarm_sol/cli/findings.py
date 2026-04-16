"""
Findings CLI Commands

CLI interface for managing vulnerability findings.
Supports list, show, next, update, refresh, and export operations.

Philosophy: "Persistent state enables seamless session handoff"
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Optional

import typer

from alphaswarm_sol.findings.model import (
    Finding,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
)
from alphaswarm_sol.findings.store import FindingsStore

findings_app = typer.Typer(help="Manage vulnerability findings")


class OutputFormat(str, Enum):
    """Output format options."""

    TABLE = "table"
    JSON = "json"
    CSV = "csv"


class ExportFormat(str, Enum):
    """Export format options."""

    JSON = "json"
    SARIF = "sarif"
    CSV = "csv"
    MARKDOWN = "markdown"


def _get_store(vkg_dir: Optional[Path] = None) -> FindingsStore:
    """Get findings store, creating directory if needed."""
    if vkg_dir is None:
        vkg_dir = Path.cwd() / ".vrs"
    return FindingsStore(vkg_dir)


def _severity_style(severity: FindingSeverity) -> tuple[str, bool]:
    """Get color and bold for severity level."""
    styles = {
        FindingSeverity.CRITICAL: ("red", True),
        FindingSeverity.HIGH: ("yellow", True),
        FindingSeverity.MEDIUM: ("blue", False),
        FindingSeverity.LOW: ("green", False),
        FindingSeverity.INFO: ("white", False),
    }
    return styles.get(severity, ("white", False))


def _status_emoji(status: FindingStatus) -> str:
    """Get emoji for status."""
    emojis = {
        FindingStatus.PENDING: ".",
        FindingStatus.INVESTIGATING: "*",
        FindingStatus.CONFIRMED: "+",
        FindingStatus.FALSE_POSITIVE: "-",
        FindingStatus.ESCALATED: "!",
        FindingStatus.FIXED: "~",
    }
    return emojis.get(status, ".")


def _print_findings_table(findings: list[Finding]) -> None:
    """Print findings as a formatted table."""
    if not findings:
        typer.echo("No findings found.")
        return

    # Header
    header = f"{'ID':<12} {'SEVERITY':<10} {'PATTERN':<25} {'LOCATION':<25} {'STATUS':<12}"
    typer.echo(header)
    typer.echo("-" * len(header))

    for f in findings:
        loc = f"{f.location.file}:{f.location.line}"
        if len(loc) > 24:
            loc = "..." + loc[-21:]

        pattern = f.pattern
        if len(pattern) > 24:
            pattern = pattern[:22] + ".."

        color, bold = _severity_style(f.severity)
        severity_text = f.severity.value.upper()

        # Format line
        line = f"{f.id:<12} {severity_text:<10} {pattern:<25} {loc:<25} {f.status.value:<12}"
        typer.echo(line)


def _print_summary(findings: list[Finding], store: FindingsStore) -> None:
    """Print findings summary statistics."""
    stats = store.stats()
    parts = [f"Total: {stats['total']} findings"]

    for status, count in stats.get("by_status", {}).items():
        parts.append(f"{count} {status}")

    typer.echo()
    typer.echo(" | ".join(parts))


def _format_finding_detail(finding: Finding) -> str:
    """Format complete finding details for display."""
    lines = []

    # Header
    lines.append(f"Finding {finding.id}: {finding.pattern}")
    lines.append("=" * 60)
    lines.append("")

    # Basic info
    loc_str = str(finding.location)
    if finding.location.function:
        loc_str += f" ({finding.location.function})"
    lines.append(f"Location: {loc_str}")

    conf_pct = {"high": "90", "medium": "70", "low": "50"}.get(
        finding.confidence.value, "50"
    )
    lines.append(
        f"Severity: {finding.severity.value.upper()} | "
        f"Confidence: {conf_pct}% | Status: {finding.status.value}"
    )
    lines.append("")

    # Description
    lines.append("Description:")
    for line in finding.description.split("\n"):
        lines.append(f"  {line}")
    lines.append("")

    # Behavioral signature
    if finding.evidence.behavioral_signature:
        lines.append(f"Behavioral Signature: {finding.evidence.behavioral_signature}")
        lines.append("")

    # Evidence
    if finding.evidence.properties_matched:
        lines.append("Properties Matched:")
        for prop in finding.evidence.properties_matched:
            lines.append(f"  + {prop}")
        lines.append("")

    if finding.evidence.properties_missing:
        lines.append("Properties Missing (required for safety):")
        for prop in finding.evidence.properties_missing:
            lines.append(f"  - {prop}")
        lines.append("")

    # Code snippet
    if finding.evidence.code_snippet:
        lines.append("Code:")
        lines.append("```solidity")
        lines.append(finding.evidence.code_snippet)
        lines.append("```")
        lines.append("")

    # Explanation
    if finding.evidence.explanation:
        lines.append("Why Vulnerable:")
        for line in finding.evidence.explanation.split("\n"):
            lines.append(f"  {line}")
        lines.append("")

    # Verification steps
    if finding.verification_steps:
        lines.append("Verification Steps:")
        for i, step in enumerate(finding.verification_steps, 1):
            lines.append(f"  {i}. {step}")
        lines.append("")

    # Fix recommendation
    if finding.recommended_fix:
        lines.append("Recommended Fix:")
        for line in finding.recommended_fix.split("\n"):
            lines.append(f"  {line}")
        lines.append("")

    # References
    if finding.cwe or finding.swc:
        refs = []
        if finding.cwe:
            refs.append(finding.cwe)
        if finding.swc:
            refs.append(finding.swc)
        lines.append(f"References: {', '.join(refs)}")
        lines.append("")

    # Investigation notes
    if finding.investigator_notes:
        lines.append("Investigation Notes:")
        lines.append(f"  {finding.investigator_notes}")
        lines.append("")

    if finding.status_reason:
        lines.append(f"Status Reason: {finding.status_reason}")
        lines.append("")

    # Actions
    lines.append("Actions:")
    lines.append(f"  vkg findings update {finding.id} --status confirmed")
    lines.append(
        f"  vkg findings update {finding.id} --status false-positive --reason \"...\""
    )

    return "\n".join(lines)


@findings_app.command("list")
def list_findings(
    status: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (pending, investigating, confirmed, false_positive, escalated, fixed)",
    ),
    severity: Optional[str] = typer.Option(
        None,
        "--severity",
        help="Filter by severity (critical, high, medium, low, info)",
    ),
    pattern: Optional[str] = typer.Option(
        None, "--pattern", "-p", help="Filter by pattern ID"
    ),
    limit: int = typer.Option(50, "--limit", "-l", help="Limit results"),
    fmt: OutputFormat = typer.Option(
        OutputFormat.TABLE, "--format", "-f", help="Output format"
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None, "--vkg-dir", help="Path to .vrs directory"
    ),
) -> None:
    """List all findings with optional filters."""
    store = _get_store(vkg_dir)

    # Parse filter values
    status_filter = FindingStatus(status) if status else None
    severity_filter = FindingSeverity(severity) if severity else None

    findings = store.list(
        status=status_filter,
        severity=severity_filter,
        pattern=pattern,
        limit=limit,
    )

    if fmt == OutputFormat.JSON:
        output = {
            "findings": [f.to_dict() for f in findings],
            "summary": store.stats(),
        }
        typer.echo(json.dumps(output, indent=2))
    elif fmt == OutputFormat.CSV:
        # CSV header
        typer.echo("id,severity,confidence,pattern,file,line,function,status,description")
        for f in findings:
            desc = f.description.replace('"', '""')[:100]
            typer.echo(
                f'"{f.id}","{f.severity.value}","{f.confidence.value}",'
                f'"{f.pattern}","{f.location.file}",{f.location.line},'
                f'"{f.location.function or ""}","{f.status.value}","{desc}"'
            )
    else:
        _print_findings_table(findings)
        _print_summary(findings, store)


@findings_app.command("show")
def show_finding(
    finding_id: str = typer.Argument(..., help="Finding ID (e.g., VKG-001)"),
    vkg_dir: Optional[Path] = typer.Option(
        None, "--vkg-dir", help="Path to .vrs directory"
    ),
) -> None:
    """Show detailed information about a finding."""
    store = _get_store(vkg_dir)
    finding = store.get(finding_id)

    if not finding:
        typer.echo(f"Finding not found: {finding_id}", err=True)
        raise typer.Exit(code=1)

    typer.echo(_format_finding_detail(finding))


@findings_app.command("next")
def next_finding(
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status (default: pending or escalated)"
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None, "--vkg-dir", help="Path to .vrs directory"
    ),
) -> None:
    """Get the next highest-priority finding to investigate."""
    store = _get_store(vkg_dir)

    if status:
        # Filter by specific status
        status_filter = FindingStatus(status)
        findings = store.list(status=status_filter, limit=1)
        finding = findings[0] if findings else None
    else:
        # Default: get next pending/escalated by priority
        finding = store.get_next()

    if not finding:
        typer.echo("No findings matching criteria.")
        typer.echo()
        typer.echo("Run 'vkg analyze' to detect vulnerabilities.")
        return

    typer.echo(_format_finding_detail(finding))


@findings_app.command("update")
def update_finding(
    finding_id: str = typer.Argument(..., help="Finding ID to update"),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="New status (pending, investigating, confirmed, false_positive, escalated, fixed)",
    ),
    reason: Optional[str] = typer.Option(
        None, "--reason", "-r", help="Reason for status change"
    ),
    note: Optional[str] = typer.Option(
        None, "--note", "-n", help="Add investigation note"
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None, "--vkg-dir", help="Path to .vrs directory"
    ),
) -> None:
    """Update finding status or add investigation notes."""
    store = _get_store(vkg_dir)
    finding = store.get(finding_id)

    if not finding:
        typer.echo(f"Finding not found: {finding_id}", err=True)
        raise typer.Exit(code=1)

    if not status and not note:
        typer.echo("Provide --status or --note to update the finding.", err=True)
        raise typer.Exit(code=1)

    old_status = finding.status.value

    # Validate: false_positive requires reason
    if status == "false_positive" and not reason:
        typer.echo(
            "Error: --reason is required when marking as false_positive", err=True
        )
        typer.echo("Example: --status false_positive --reason 'Protected by modifier'")
        raise typer.Exit(code=1)

    # Update status
    if status:
        new_status = FindingStatus(status)
        store.update(
            finding_id, status=new_status, reason=reason or "", notes=note or ""
        )
        typer.echo(f"Updated {finding_id}: {old_status} -> {status}")
    elif note:
        # Just add note without status change
        store.update(finding_id, notes=note)
        typer.echo(f"Added note to {finding_id}")

    if note:
        typer.echo(f"Note: {note}")

    store.save()


@findings_app.command("escalate")
def escalate_finding(
    finding_id: str = typer.Argument(..., help="Finding ID to escalate"),
    reason: str = typer.Option(
        ..., "--reason", "-r", help="Reason for escalation (required)"
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None, "--vkg-dir", help="Path to .vrs directory"
    ),
) -> None:
    """Escalate a finding for human review."""
    store = _get_store(vkg_dir)
    finding = store.get(finding_id)

    if not finding:
        typer.echo(f"Finding not found: {finding_id}", err=True)
        raise typer.Exit(code=1)

    old_status = finding.status.value
    store.update(finding_id, status=FindingStatus.ESCALATED, reason=reason)
    store.save()

    typer.echo(f"Escalated {finding_id}: {old_status} -> escalated")
    typer.echo(f"Reason: {reason}")
    typer.echo()
    typer.echo("This finding will be prioritized in 'vkg findings next'")


@findings_app.command("status")
def findings_status(
    fmt: OutputFormat = typer.Option(
        OutputFormat.TABLE, "--format", "-f", help="Output format"
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None, "--vkg-dir", help="Path to .vrs directory"
    ),
) -> None:
    """
    Show audit status for session handoff.

    Provides complete state needed to resume an audit in a new session.
    Designed for LLM agents that need to understand current audit state.
    """
    store = _get_store(vkg_dir)
    stats = store.stats()
    next_finding = store.get_next()

    if fmt == OutputFormat.JSON:
        # JSON output for programmatic consumption
        output = {
            "session_state": {
                "audit_status": _get_audit_phase(stats),
                "total_findings": stats["total"],
                "pending": stats.get("by_status", {}).get("pending", 0),
                "investigating": stats.get("by_status", {}).get("investigating", 0),
                "confirmed": stats.get("by_status", {}).get("confirmed", 0),
                "false_positive": stats.get("by_status", {}).get("false_positive", 0),
                "escalated": stats.get("by_status", {}).get("escalated", 0),
                "fixed": stats.get("by_status", {}).get("fixed", 0),
            },
            "severity_breakdown": stats.get("by_severity", {}),
            "next_action": _get_next_action(stats, next_finding),
            "next_finding": next_finding.to_dict() if next_finding else None,
            "recommended_commands": _get_recommended_commands(stats, next_finding),
        }
        typer.echo(json.dumps(output, indent=2))
    else:
        _print_session_status(stats, next_finding)


def _get_audit_phase(stats: dict) -> str:
    """Determine current audit phase."""
    total = stats["total"]
    if total == 0:
        return "not_started"

    pending = stats.get("by_status", {}).get("pending", 0)
    investigating = stats.get("by_status", {}).get("investigating", 0)
    confirmed = stats.get("by_status", {}).get("confirmed", 0)
    escalated = stats.get("by_status", {}).get("escalated", 0)

    if pending + investigating + escalated == 0:
        return "complete"
    elif pending == total:
        return "ready_for_investigation"
    elif investigating > 0:
        return "investigation_in_progress"
    elif escalated > 0:
        return "needs_human_review"
    else:
        return "in_progress"


def _get_next_action(stats: dict, next_finding: Optional[Finding]) -> dict:
    """Determine the recommended next action."""
    total = stats["total"]

    if total == 0:
        return {
            "action": "build_and_analyze",
            "description": "No findings yet. Run vkg build followed by vkg analyze.",
        }

    pending = stats.get("by_status", {}).get("pending", 0)
    escalated = stats.get("by_status", {}).get("escalated", 0)

    if pending == 0 and escalated == 0:
        return {
            "action": "generate_report",
            "description": "All findings investigated. Generate final report.",
        }

    if escalated > 0 and next_finding and next_finding.status == FindingStatus.ESCALATED:
        return {
            "action": "review_escalated",
            "description": f"Review escalated finding {next_finding.id}",
            "finding_id": next_finding.id,
        }

    if next_finding:
        return {
            "action": "investigate_next",
            "description": f"Investigate {next_finding.id} ({next_finding.severity.value.upper()})",
            "finding_id": next_finding.id,
        }

    return {
        "action": "review_status",
        "description": "Check findings list for items needing attention.",
    }


def _get_recommended_commands(stats: dict, next_finding: Optional[Finding]) -> list[str]:
    """Generate list of recommended commands."""
    commands = []
    total = stats["total"]

    if total == 0:
        commands.append("vkg build contracts/")
        commands.append("vkg analyze")
        return commands

    pending = stats.get("by_status", {}).get("pending", 0)
    escalated = stats.get("by_status", {}).get("escalated", 0)

    if pending > 0 or escalated > 0:
        commands.append("vkg findings next")
        if next_finding:
            commands.append(f"vkg findings show {next_finding.id}")
            commands.append(f"vkg findings update {next_finding.id} --status confirmed")
            commands.append(
                f"vkg findings update {next_finding.id} --status false_positive --reason '...'"
            )
    else:
        commands.append("vkg findings export --format sarif")
        commands.append("vkg findings list --status confirmed")

    return commands


def _print_session_status(stats: dict, next_finding: Optional[Finding]) -> None:
    """Print human-readable session status."""
    total = stats["total"]
    phase = _get_audit_phase(stats)

    typer.echo("=" * 60)
    typer.echo("VKG Audit Session Status")
    typer.echo("=" * 60)
    typer.echo()

    # Phase indicator
    phase_labels = {
        "not_started": "Not Started - Run 'vkg analyze' to begin",
        "ready_for_investigation": "Ready for Investigation",
        "investigation_in_progress": "Investigation In Progress",
        "needs_human_review": "Needs Human Review (has escalated findings)",
        "complete": "Complete - All findings investigated",
        "in_progress": "In Progress",
    }
    typer.echo(f"Phase: {phase_labels.get(phase, phase)}")
    typer.echo()

    # Statistics
    typer.echo("Findings Summary:")
    typer.echo(f"  Total: {total}")
    if total > 0:
        for status in ["pending", "investigating", "confirmed", "false_positive", "escalated", "fixed"]:
            count = stats.get("by_status", {}).get(status, 0)
            if count > 0:
                typer.echo(f"  {status.title().replace('_', ' ')}: {count}")

        typer.echo()
        typer.echo("By Severity:")
        for sev in ["critical", "high", "medium", "low", "info"]:
            count = stats.get("by_severity", {}).get(sev, 0)
            if count > 0:
                typer.echo(f"  {sev.upper()}: {count}")

    typer.echo()

    # Next action
    next_action = _get_next_action(stats, next_finding)
    typer.echo(f"Next Action: {next_action['description']}")
    typer.echo()

    # Recommended commands
    typer.echo("Recommended Commands:")
    for cmd in _get_recommended_commands(stats, next_finding):
        typer.echo(f"  {cmd}")

    typer.echo()
    typer.echo("=" * 60)


@findings_app.command("refresh")
def refresh_findings(
    stale_only: bool = typer.Option(
        False, "--stale-only", help="Only show stale findings"
    ),
    clear: bool = typer.Option(
        False, "--clear", help="Clear all findings and start fresh"
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None, "--vkg-dir", help="Path to .vrs directory"
    ),
) -> None:
    """Check findings freshness or clear all findings."""
    store = _get_store(vkg_dir)

    if clear:
        count = len(store)
        store.clear()
        store.save()
        typer.echo(f"Cleared {count} findings.")
        typer.echo("Run 'vkg analyze' to generate new findings.")
        return

    # Check for stale findings
    # In future: compare graph fingerprint with finding timestamps
    findings = list(store)
    if not findings:
        typer.echo("No findings to check.")
        return

    typer.echo(f"Checking {len(findings)} findings...")
    typer.echo()

    # Group by status
    stats = store.stats()
    typer.echo("Current findings by status:")
    for status, count in stats.get("by_status", {}).items():
        typer.echo(f"  {status}: {count}")

    typer.echo()
    typer.echo("Note: Stale detection requires graph fingerprinting (coming soon)")
    typer.echo("Run 'vkg analyze' to refresh findings after code changes.")


@findings_app.command("export")
def export_findings(
    fmt: ExportFormat = typer.Option(
        ExportFormat.JSON, "--format", "-f", help="Export format"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path (default: stdout)"
    ),
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status"
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None, "--vkg-dir", help="Path to .vrs directory"
    ),
) -> None:
    """Export findings to various formats."""
    store = _get_store(vkg_dir)

    status_filter = FindingStatus(status) if status else None
    findings = store.list(status=status_filter, limit=1000)

    if fmt == ExportFormat.JSON:
        content = store.to_json()
    elif fmt == ExportFormat.SARIF:
        content = _export_sarif(findings)
    elif fmt == ExportFormat.CSV:
        content = _export_csv(findings)
    elif fmt == ExportFormat.MARKDOWN:
        content = _export_markdown(findings)
    else:
        typer.echo(f"Unsupported format: {fmt}", err=True)
        raise typer.Exit(code=1)

    if output:
        output.write_text(content)
        typer.echo(f"Exported {len(findings)} findings to {output}")
    else:
        typer.echo(content)


def _export_sarif(findings: list[Finding]) -> str:
    """Export findings in SARIF 2.1.0 format."""
    from datetime import datetime, timezone

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "True VKG",
                        "version": "4.0.0",
                        "informationUri": "https://github.com/alphaswarm/alphaswarm",
                        "rules": _build_sarif_rules(findings),
                    }
                },
                "results": [_finding_to_sarif_result(f) for f in findings],
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "endTimeUtc": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            }
        ],
    }
    return json.dumps(sarif, indent=2)


def _build_sarif_rules(findings: list[Finding]) -> list[dict]:
    """Build unique SARIF rules from findings."""
    patterns = {}
    for f in findings:
        if f.pattern not in patterns:
            patterns[f.pattern] = {
                "id": f.pattern,
                "name": f.pattern.replace("-", " ").title(),
                "shortDescription": {"text": f.description[:200]},
                "defaultConfiguration": {
                    "level": _severity_to_sarif_level(f.severity)
                },
                "properties": {
                    "tags": [f.severity.value],
                },
            }
            if f.cwe:
                patterns[f.pattern]["properties"]["cwe"] = f.cwe

    return list(patterns.values())


def _severity_to_sarif_level(severity: FindingSeverity) -> str:
    """Convert VKG severity to SARIF level."""
    mapping = {
        FindingSeverity.CRITICAL: "error",
        FindingSeverity.HIGH: "error",
        FindingSeverity.MEDIUM: "warning",
        FindingSeverity.LOW: "note",
        FindingSeverity.INFO: "note",
    }
    return mapping.get(severity, "warning")


def _finding_to_sarif_result(finding: Finding) -> dict:
    """Convert a Finding to SARIF result format."""
    result = {
        "ruleId": finding.pattern,
        "level": _severity_to_sarif_level(finding.severity),
        "message": {"text": finding.description},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": finding.location.file},
                    "region": {
                        "startLine": finding.location.line,
                        "startColumn": finding.location.column or 1,
                    },
                }
            }
        ],
        "fingerprints": {"vkg/v1": finding.id},
        "properties": {
            "confidence": finding.confidence.value,
            "status": finding.status.value,
        },
    }

    if finding.location.end_line:
        result["locations"][0]["physicalLocation"]["region"]["endLine"] = (
            finding.location.end_line
        )

    if finding.evidence.behavioral_signature:
        result["properties"]["behavioralSignature"] = (
            finding.evidence.behavioral_signature
        )

    return result


def _export_csv(findings: list[Finding]) -> str:
    """Export findings as CSV."""
    lines = [
        "id,severity,confidence,pattern,file,line,function,contract,status,description"
    ]

    for f in findings:
        desc = f.description.replace('"', '""')[:200]
        lines.append(
            f'"{f.id}","{f.severity.value}","{f.confidence.value}",'
            f'"{f.pattern}","{f.location.file}",{f.location.line},'
            f'"{f.location.function or ""}","{f.location.contract or ""}",'
            f'"{f.status.value}","{desc}"'
        )

    return "\n".join(lines)


def _export_markdown(findings: list[Finding]) -> str:
    """Export findings as Markdown report."""
    lines = ["# Security Findings Report", ""]
    lines.append(f"**Total Findings:** {len(findings)}")
    lines.append("")

    # Summary by severity
    by_severity: dict[str, int] = {}
    for f in findings:
        by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1

    lines.append("## Summary by Severity")
    lines.append("")
    lines.append("| Severity | Count |")
    lines.append("|----------|-------|")
    for sev in ["critical", "high", "medium", "low", "info"]:
        if sev in by_severity:
            lines.append(f"| {sev.upper()} | {by_severity[sev]} |")
    lines.append("")

    # Individual findings
    lines.append("## Findings")
    lines.append("")

    for f in findings:
        lines.append(f"### {f.id}: {f.title}")
        lines.append("")
        lines.append(f"- **Severity:** {f.severity.value.upper()}")
        lines.append(f"- **Confidence:** {f.confidence.value}")
        lines.append(f"- **Pattern:** `{f.pattern}`")
        lines.append(f"- **Location:** `{f.location}`")
        lines.append(f"- **Status:** {f.status.value}")
        lines.append("")
        lines.append("**Description:**")
        lines.append(f"> {f.description}")
        lines.append("")

        if f.evidence.behavioral_signature:
            lines.append(f"**Behavioral Signature:** `{f.evidence.behavioral_signature}`")
            lines.append("")

        if f.evidence.code_snippet:
            lines.append("**Code:**")
            lines.append("```solidity")
            lines.append(f.evidence.code_snippet)
            lines.append("```")
            lines.append("")

        if f.recommended_fix:
            lines.append("**Recommended Fix:**")
            lines.append(f"> {f.recommended_fix}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)
