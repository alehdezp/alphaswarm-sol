"""Bead management CLI commands."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from alphaswarm_sol.beads.jsonl_storage import BeadJSONLStorage

app = typer.Typer(help="Bead management commands")
console = Console()


def get_storage(project: Path = Path(".")) -> BeadJSONLStorage:
    """Get bead storage for project."""
    return BeadJSONLStorage(project / ".beads")


@app.command("create")
def bead_create(
    title: str = typer.Argument(..., help="Brief description of investigation"),
    severity: str = typer.Option(
        "medium",
        "--severity", "-s",
        help="Severity: critical, high, medium, low",
    ),
    pattern: Optional[str] = typer.Option(
        None,
        "--pattern", "-p",
        help="Pattern ID that triggered this",
    ),
    location: Optional[str] = typer.Option(
        None,
        "--location", "-l",
        help="File:function location",
    ),
    priority: int = typer.Option(
        0,
        "--priority",
        help="Priority (0 = highest)",
    ),
    parent: Optional[str] = typer.Option(
        None,
        "--parent",
        help="Parent bead ID for hierarchy",
    ),
    json_output: bool = typer.Option(
        False,
        "--json", "-j",
        help="Output as JSON",
    ),
) -> None:
    """Create a new security investigation bead.

    Example:
        alphaswarm bead create "Check reentrancy in withdraw"
        alphaswarm bead create "Verify access control" -s high -l src/Vault.sol:withdraw
    """
    storage = get_storage()
    bead_id = storage.create(
        title=title,
        severity=severity,
        pattern_id=pattern,
        location=location,
        priority=priority,
        parent_id=parent,
    )

    if json_output:
        bead = storage.get(bead_id)
        console.print(json.dumps(bead.__dict__, indent=2))
    else:
        console.print(f"[green]Created bead:[/green] {bead_id}")
        console.print(f"  Title: {title}")
        console.print(f"  Severity: {severity}")


@app.command("update")
def bead_update(
    bead_id: str = typer.Argument(..., help="Bead ID to update"),
    status: Optional[str] = typer.Option(
        None,
        "--status", "-s",
        help="New status: open, in_progress, complete, blocked",
    ),
    notes: Optional[str] = typer.Option(
        None,
        "--notes", "-n",
        help="Additional notes",
    ),
    blocked_by: Optional[str] = typer.Option(
        None,
        "--blocked-by", "-b",
        help="ID of blocking bead",
    ),
) -> None:
    """Update a bead's status.

    Example:
        alphaswarm bead update bd-a1b2c3d4 --status in_progress
        alphaswarm bead update bd-a1b2c3d4 --status blocked --blocked-by bd-e5f6g7h8
    """
    storage = get_storage()
    try:
        bead = storage.update(
            bead_id=bead_id,
            status=status,
            notes=notes,
            blocked_by=blocked_by,
        )
        console.print(f"[green]Updated bead:[/green] {bead_id}")
        console.print(f"  Status: {bead.status}")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("list")
def bead_list(
    status: Optional[str] = typer.Option(
        None,
        "--status", "-s",
        help="Filter by status",
    ),
    severity: Optional[str] = typer.Option(
        None,
        "--severity",
        help="Filter by severity",
    ),
    ready: bool = typer.Option(
        False,
        "--ready", "-r",
        help="Show only ready beads (open, not blocked)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json", "-j",
        help="Output as JSON",
    ),
) -> None:
    """List beads with optional filtering.

    Example:
        alphaswarm bead list
        alphaswarm bead list --status open
        alphaswarm bead list --ready
    """
    storage = get_storage()

    if ready:
        beads = storage.get_ready()
    else:
        beads = storage.list(status=status, severity=severity)

    if json_output:
        console.print(json.dumps([b.__dict__ for b in beads], indent=2))
        return

    if not beads:
        console.print("[dim]No beads found[/dim]")
        return

    table = Table(title="Beads")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="yellow")
    table.add_column("Severity", style="red")
    table.add_column("Priority", style="dim")

    severity_colors = {
        "critical": "[red]critical[/red]",
        "high": "[orange3]high[/orange3]",
        "medium": "[yellow]medium[/yellow]",
        "low": "[green]low[/green]",
    }

    for bead in beads:
        sev = severity_colors.get(bead.severity, bead.severity)
        table.add_row(
            bead.id,
            bead.title[:50] + ("..." if len(bead.title) > 50 else ""),
            bead.status,
            sev,
            str(bead.priority),
        )

    console.print(table)


@app.command("show")
def bead_show(
    bead_id: str = typer.Argument(..., help="Bead ID to show"),
    json_output: bool = typer.Option(
        False,
        "--json", "-j",
        help="Output as JSON",
    ),
) -> None:
    """Show details of a specific bead.

    Example:
        alphaswarm bead show bd-a1b2c3d4
    """
    storage = get_storage()
    bead = storage.get(bead_id)

    if not bead:
        console.print(f"[red]Bead not found:[/red] {bead_id}")
        raise typer.Exit(1)

    if json_output:
        console.print(json.dumps(bead.__dict__, indent=2))
        return

    console.print(f"[bold]Bead {bead.id}[/bold]")
    console.print(f"  Title: {bead.title}")
    console.print(f"  Status: {bead.status}")
    console.print(f"  Severity: {bead.severity}")
    console.print(f"  Priority: {bead.priority}")
    if bead.pattern_id:
        console.print(f"  Pattern: {bead.pattern_id}")
    if bead.location:
        console.print(f"  Location: {bead.location}")
    if bead.blockers:
        console.print(f"  Blocked by: {', '.join(bead.blockers)}")
    if bead.notes:
        console.print(f"  Notes: {bead.notes}")
    console.print(f"  Created: {bead.created_at}")
    console.print(f"  Updated: {bead.updated_at}")
