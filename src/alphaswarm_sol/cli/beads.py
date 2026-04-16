"""
CLI Commands for Beads

CLI interface for managing vulnerability investigation beads.
Supports list, show, next, verdict, note, context, and generate operations.

Philosophy: "Self-contained investigation packages for LLM-driven audit"
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Optional

import typer

from alphaswarm_sol.beads.schema import VulnerabilityBead
from alphaswarm_sol.beads.storage import BeadStorage
from alphaswarm_sol.beads.types import BeadStatus, Severity, VerdictType, Verdict

beads_app = typer.Typer(help="Manage vulnerability investigation beads")


# Default storage location
DEFAULT_BEAD_DIR = Path(".vrs/beads")


class OutputFormat(str, Enum):
    """Output format options for list command."""

    TABLE = "table"
    JSON = "json"
    COMPACT = "compact"


class ShowFormat(str, Enum):
    """Output format options for show command."""

    FULL = "full"
    JSON = "json"
    LLM = "llm"


class ContextFormat(str, Enum):
    """Output format options for context command."""

    SUMMARY = "summary"
    FULL = "full"
    JSON = "json"


def _get_storage(vkg_dir: Optional[Path] = None) -> BeadStorage:
    """Get bead storage instance."""
    if vkg_dir is None:
        vkg_dir = Path.cwd() / ".vrs" / "beads"
    return BeadStorage(vkg_dir)


def _severity_order(severity: Severity) -> int:
    """Get sort order for severity (lower = higher priority)."""
    order = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
        Severity.INFO: 4,
    }
    return order.get(severity, 5)


def _print_bead_full(bead: VulnerabilityBead) -> None:
    """Print full bead details in human-readable format."""
    typer.echo(f"\n{'='*70}")
    typer.echo(f"BEAD: {bead.id}")
    typer.echo(f"{'='*70}")

    typer.echo(f"\n## SUMMARY")
    typer.echo(f"  Vulnerability Class: {bead.vulnerability_class}")
    typer.echo(f"  Pattern: {bead.pattern_id}")
    typer.echo(f"  Severity: {bead.severity.value.upper()}")
    typer.echo(f"  Confidence: {bead.confidence:.0%}")
    typer.echo(f"  Status: {bead.status.value}")

    typer.echo(f"\n## VULNERABLE CODE")
    typer.echo(f"  File: {bead.vulnerable_code.file_path}")
    typer.echo(f"  Contract: {bead.vulnerable_code.contract_name}")
    typer.echo(f"  Function: {bead.vulnerable_code.function_name}")
    typer.echo(f"  Lines: {bead.vulnerable_code.start_line}-{bead.vulnerable_code.end_line}")
    typer.echo(f"\n```solidity")
    typer.echo(bead.vulnerable_code.source)
    typer.echo(f"```")

    typer.echo(f"\n## WHY FLAGGED")
    typer.echo(f"  {bead.pattern_context.why_flagged}")

    if bead.pattern_context.matched_properties:
        typer.echo(f"\n  Matched Properties:")
        for prop in bead.pattern_context.matched_properties:
            typer.echo(f"    - {prop}")

    typer.echo(f"\n## INVESTIGATION STEPS")
    for step in bead.investigation_guide.steps:
        typer.echo(f"\n  Step {step.step_number}: {step.action}")
        typer.echo(f"    Look for: {step.look_for}")
        if step.red_flag:
            typer.echo(f"    RED FLAG: {step.red_flag}")
        if step.safe_if:
            typer.echo(f"    Safe if: {step.safe_if}")

    typer.echo(f"\n## QUESTIONS TO ANSWER")
    for q in bead.investigation_guide.questions_to_answer:
        typer.echo(f"  - {q}")

    if bead.similar_exploits:
        typer.echo(f"\n## SIMILAR EXPLOITS")
        for exploit in bead.similar_exploits:
            typer.echo(f"  - {exploit.name} ({exploit.date}): {exploit.loss}")

    typer.echo(f"\n## FIX RECOMMENDATIONS")
    for fix in bead.fix_recommendations:
        typer.echo(f"  - {fix}")

    if bead.test_context:
        typer.echo(f"\n## TEST SCAFFOLD")
        typer.echo(f"  Attack Scenario: {bead.test_context.attack_scenario}")
        if bead.test_context.setup_requirements:
            typer.echo(f"  Setup Requirements:")
            for req in bead.test_context.setup_requirements:
                typer.echo(f"    - {req}")

    if bead.verdict:
        typer.echo(f"\n## VERDICT")
        typer.echo(f"  Type: {bead.verdict.type.value}")
        typer.echo(f"  Reason: {bead.verdict.reason}")
        typer.echo(f"  Confidence: {bead.verdict.confidence:.0%}")

    if bead.notes:
        typer.echo(f"\n## NOTES")
        for note in bead.notes:
            typer.echo(f"  - {note}")

    typer.echo(f"\n{'='*70}\n")


@beads_app.command("list")
def list_beads(
    status: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (pending, investigating, confirmed, rejected)",
    ),
    vuln_class: Optional[str] = typer.Option(
        None,
        "--class",
        help="Filter by vulnerability class",
    ),
    severity: Optional[str] = typer.Option(
        None,
        "--severity",
        help="Filter by severity (critical, high, medium, low)",
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format",
        "-f",
        help="Output format",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """List all beads, optionally filtered.

    Examples:
        vkg beads list
        vkg beads list --status pending
        vkg beads list --class reentrancy --severity critical
        vkg beads list --format json
    """
    storage = _get_storage(vkg_dir)
    beads = storage.list_beads()

    # Apply filters
    if status:
        try:
            status_enum = BeadStatus(status)
            beads = [b for b in beads if b.status == status_enum]
        except ValueError:
            typer.echo(f"Invalid status: {status}", err=True)
            raise typer.Exit(code=1)

    if vuln_class:
        beads = [b for b in beads if b.vulnerability_class == vuln_class]

    if severity:
        try:
            severity_enum = Severity(severity)
            beads = [b for b in beads if b.severity == severity_enum]
        except ValueError:
            typer.echo(f"Invalid severity: {severity}", err=True)
            raise typer.Exit(code=1)

    if not beads:
        typer.echo("No beads found matching criteria.")
        return

    if fmt == OutputFormat.JSON:
        typer.echo(json.dumps([b.to_dict() for b in beads], indent=2))
        return  # No summary for JSON output
    elif fmt == OutputFormat.COMPACT:
        for bead in beads:
            typer.echo(
                f"{bead.id} | {bead.vulnerability_class} | "
                f"{bead.severity.value} | {bead.status.value}"
            )
    else:  # table
        typer.echo(
            f"{'ID':<20} {'Class':<15} {'Severity':<10} {'Status':<12} {'Confidence':<10}"
        )
        typer.echo("-" * 75)
        for bead in beads:
            typer.echo(
                f"{bead.id:<20} {bead.vulnerability_class:<15} "
                f"{bead.severity.value:<10} {bead.status.value:<12} {bead.confidence:.0%}"
            )

    typer.echo(f"\nTotal: {len(beads)} beads")


@beads_app.command("show")
def show_bead(
    bead_id: str = typer.Argument(..., help="Bead ID (e.g., VKG-0001-abc123)"),
    fmt: ShowFormat = typer.Option(
        ShowFormat.FULL,
        "--format",
        "-f",
        help="Output format",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """Show details of a specific bead.

    Examples:
        vkg beads show VKG-0001-abc123
        vkg beads show VKG-0001-abc123 --format json
        vkg beads show VKG-0001-abc123 --format llm  # LLM investigation prompt
    """
    storage = _get_storage(vkg_dir)
    bead = storage.get_bead(bead_id)

    if bead is None:
        typer.echo(f"Error: Bead {bead_id} not found", err=True)
        raise typer.Exit(code=1)

    if fmt == ShowFormat.JSON:
        typer.echo(bead.to_json())
    elif fmt == ShowFormat.LLM:
        typer.echo(bead.get_llm_prompt())
    else:  # full
        _print_bead_full(bead)


@beads_app.command("next")
def next_bead(
    severity: Optional[str] = typer.Option(
        None,
        "--severity",
        "-s",
        help="Minimum severity to show (critical, high, medium, low)",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """Get the next priority bead for investigation.

    Priority order:
    1. Critical severity, pending status
    2. High severity, pending status
    3. Medium severity, pending status
    4. Low severity, pending status

    Example:
        vkg beads next
        vkg beads next --severity high
    """
    storage = _get_storage(vkg_dir)
    beads = storage.list_beads()

    # Filter to pending only
    pending = [b for b in beads if b.status == BeadStatus.PENDING]

    if not pending:
        typer.echo("No pending beads to investigate.")
        return

    # Sort by severity (highest first)
    pending.sort(key=lambda b: _severity_order(b.severity))

    # Filter by minimum severity if specified
    if severity:
        try:
            min_severity = Severity(severity)
            min_order = _severity_order(min_severity)
            pending = [b for b in pending if _severity_order(b.severity) <= min_order]
        except ValueError:
            typer.echo(f"Invalid severity: {severity}", err=True)
            raise typer.Exit(code=1)

    if not pending:
        typer.echo(f"No pending beads at {severity} severity or higher.")
        return

    # Get next (highest priority pending)
    next_b = pending[0]

    typer.echo(f"\n## NEXT BEAD TO INVESTIGATE")
    typer.echo(f"Total pending: {len(pending)}")
    typer.echo()

    # Show full bead
    _print_bead_full(next_b)

    # Mark as investigating
    next_b.status = BeadStatus.INVESTIGATING
    storage.save_bead(next_b)
    typer.echo(f"Status updated to 'investigating'")


@beads_app.command("verdict")
def set_verdict(
    bead_id: str = typer.Argument(..., help="Bead ID to update"),
    confirmed: bool = typer.Option(
        False,
        "--confirmed",
        help="Mark as confirmed true positive",
    ),
    rejected: bool = typer.Option(
        False,
        "--rejected",
        help="Mark as rejected false positive",
    ),
    inconclusive: bool = typer.Option(
        False,
        "--inconclusive",
        help="Mark as inconclusive",
    ),
    reason: str = typer.Option(
        ...,
        "--reason",
        "-r",
        help="Reason for verdict (required)",
    ),
    confidence: float = typer.Option(
        0.8,
        "--confidence",
        "-c",
        help="Confidence in verdict (0-1)",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """Set verdict on a bead.

    Examples:
        vkg beads verdict VKG-0001 --confirmed --reason "Exploit confirmed via PoC"
        vkg beads verdict VKG-0001 --rejected --reason "Has nonReentrant modifier"
        vkg beads verdict VKG-0001 --inconclusive --reason "Need more context"
    """
    # Check exactly one verdict type specified
    verdict_count = sum([confirmed, rejected, inconclusive])
    if verdict_count == 0:
        typer.echo(
            "Error: Must specify --confirmed, --rejected, or --inconclusive", err=True
        )
        raise typer.Exit(code=1)
    if verdict_count > 1:
        typer.echo(
            "Error: Can only specify one of --confirmed, --rejected, or --inconclusive",
            err=True,
        )
        raise typer.Exit(code=1)

    storage = _get_storage(vkg_dir)
    bead = storage.get_bead(bead_id)

    if bead is None:
        typer.echo(f"Error: Bead {bead_id} not found", err=True)
        raise typer.Exit(code=1)

    # Determine verdict type
    if confirmed:
        verdict_type = VerdictType.TRUE_POSITIVE
        type_name = "confirmed"
    elif rejected:
        verdict_type = VerdictType.FALSE_POSITIVE
        type_name = "rejected"
    else:
        verdict_type = VerdictType.INCONCLUSIVE
        type_name = "inconclusive"

    verdict = Verdict(
        type=verdict_type,
        reason=reason,
        confidence=confidence,
        evidence=[reason],
    )

    bead.set_verdict(verdict)
    storage.save_bead(bead)

    typer.echo(f"Verdict set for {bead_id}:")
    typer.echo(f"  Type: {type_name}")
    typer.echo(f"  Reason: {reason}")
    typer.echo(f"  Status: {bead.status.value}")


@beads_app.command("note")
def add_note(
    bead_id: str = typer.Argument(..., help="Bead ID"),
    note_text: str = typer.Argument(..., help="Note text to add"),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """Add an investigation note to a bead.

    Example:
        vkg beads note VKG-0001-abc123 "Checked modifiers, none found"
    """
    storage = _get_storage(vkg_dir)
    bead = storage.get_bead(bead_id)

    if bead is None:
        typer.echo(f"Error: Bead {bead_id} not found", err=True)
        raise typer.Exit(code=1)

    bead.add_note(note_text)
    storage.save_bead(bead)

    typer.echo(f"Note added to {bead_id}")


@beads_app.command("context")
def get_context(
    fmt: ContextFormat = typer.Option(
        ContextFormat.SUMMARY,
        "--format",
        "-f",
        help="Output format",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """Get session context - summary of all beads.

    Useful for LLM context window - shows what has been investigated.

    Example:
        vkg beads context
        vkg beads context --format json
    """
    storage = _get_storage(vkg_dir)
    beads = storage.list_beads()

    if not beads:
        typer.echo("No beads in session.")
        return

    # Group by status
    by_status: dict[str, list[VulnerabilityBead]] = {}
    for bead in beads:
        status = bead.status.value
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(bead)

    if fmt == ContextFormat.JSON:
        typer.echo(
            json.dumps(
                {
                    "total": len(beads),
                    "by_status": {k: len(v) for k, v in by_status.items()},
                    "beads": [b.to_dict() for b in beads],
                },
                indent=2,
            )
        )
        return

    typer.echo(f"\n## SESSION CONTEXT")
    typer.echo(f"Total Beads: {len(beads)}")
    typer.echo()

    for status, status_beads in by_status.items():
        typer.echo(f"### {status.upper()} ({len(status_beads)})")
        for bead in status_beads:
            if fmt == ContextFormat.FULL:
                typer.echo(
                    f"  {bead.id}: {bead.vulnerability_class} in "
                    f"{bead.vulnerable_code.function_name}"
                )
                if bead.verdict:
                    typer.echo(
                        f"    Verdict: {bead.verdict.type.value} - {bead.verdict.reason}"
                    )
            else:  # summary
                typer.echo(f"  - {bead.id} ({bead.severity.value})")
        typer.echo()


@beads_app.command("generate")
def generate_beads(
    project_path: str = typer.Argument(..., help="Path to Solidity project"),
    graph_path: Optional[str] = typer.Option(
        None,
        "--graph",
        "-g",
        help="Graph path or contract stem (e.g., 'Token'). Skip build step.",
    ),
    pattern: Optional[str] = typer.Option(
        None,
        "--pattern",
        "-p",
        help="Only generate for specific pattern ID",
    ),
    pattern_dir: Optional[str] = typer.Option(
        None,
        "--pattern-dir",
        help="Directory with pattern packs",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """Generate beads from pattern analysis.

    Example:
        vkg beads generate ./contracts
        vkg beads generate ./contracts --pattern vm-001
        vkg beads generate ./contracts --graph .vrs/graphs/graph.json
    """
    from alphaswarm_sol.beads.creator import BeadCreator
    from alphaswarm_sol.kg.builder import VKGBuilder
    from alphaswarm_sol.kg.store import GraphStore
    from alphaswarm_sol.queries.patterns import PatternEngine

    project = Path(project_path)
    if not project.exists():
        typer.echo(f"Error: Path not found: {project}", err=True)
        raise typer.Exit(code=1)

    # Load or build graph
    if graph_path:
        typer.echo(f"Loading graph from {graph_path}...")
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        graph, _ = resolve_and_load_graph(graph_path)
    else:
        typer.echo(f"Building knowledge graph for {project}...")
        try:
            builder = VKGBuilder(project if project.is_dir() else project.parent)
            graph = builder.build(project)
            typer.echo(f"Graph built: {len(graph.nodes)} nodes")
        except Exception as e:
            typer.echo(f"Error building graph: {e}", err=True)
            raise typer.Exit(code=1)

    typer.echo("Running pattern analysis...")

    try:
        pdir = Path(pattern_dir) if pattern_dir else None
        engine = PatternEngine(pattern_dir=pdir)

        if pattern:
            # Run specific pattern
            results = engine.run_pattern(graph, pattern)
        else:
            # Run all patterns
            results = engine.run_all_patterns(graph)

        typer.echo(f"Found {len(results)} pattern matches")
    except Exception as e:
        typer.echo(f"Error in pattern analysis: {e}", err=True)
        raise typer.Exit(code=1)

    if not results:
        typer.echo("No pattern matches found. No beads to create.")
        return

    typer.echo("Creating beads...")

    try:
        creator = BeadCreator(graph)
        beads = creator.create_beads_from_findings(results)
        typer.echo(f"Created {len(beads)} beads")
    except Exception as e:
        typer.echo(f"Error creating beads: {e}", err=True)
        raise typer.Exit(code=1)

    # Save beads
    storage = _get_storage(vkg_dir)
    for bead in beads:
        storage.save_bead(bead)

    typer.echo(f"\nSaved {len(beads)} beads to {storage.path}")
    typer.echo(f"\nRun 'vkg beads list' to see all beads")
    typer.echo(f"Run 'vkg beads next' to start investigating")


@beads_app.command("summary")
def summary(
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """Show summary statistics for beads.

    Example:
        vkg beads summary
    """
    storage = _get_storage(vkg_dir)
    stats = storage.get_summary()

    typer.echo("\n## BEADS SUMMARY")
    typer.echo(f"Total: {stats['total']} beads")

    if stats["total"] == 0:
        typer.echo("\nNo beads found. Run 'vkg beads generate <path>' to create beads.")
        return

    typer.echo("\n### By Status")
    for status, count in stats["by_status"].items():
        typer.echo(f"  {status}: {count}")

    typer.echo("\n### By Severity")
    for severity, count in stats["by_severity"].items():
        typer.echo(f"  {severity}: {count}")

    typer.echo("\n### By Vulnerability Class")
    for vuln_class, count in stats["by_class"].items():
        typer.echo(f"  {vuln_class}: {count}")


@beads_app.command("clear")
def clear_beads(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """Clear all beads from storage.

    Example:
        vkg beads clear
        vkg beads clear --force
    """
    storage = _get_storage(vkg_dir)
    count = storage.count()

    if count == 0:
        typer.echo("No beads to clear.")
        return

    if not force:
        confirm = typer.confirm(f"Delete {count} beads? This cannot be undone.")
        if not confirm:
            typer.echo("Cancelled.")
            return

    deleted = storage.clear()
    typer.echo(f"Cleared {deleted} beads.")
