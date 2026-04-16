"""CLI commands for dashboard generation.

Provides on-demand dashboard generation for operations monitoring.

Usage:
    alphaswarm ops dashboard --type latency --format markdown
    alphaswarm ops dashboard --type accuracy --format json
    alphaswarm ops dashboard --type ops --format toon --output ops.toon
"""

from pathlib import Path
from typing import List, Optional

import typer

from alphaswarm_sol.dashboards import (
    OutputFormat,
    render_accuracy_dashboard,
    render_latency_dashboard,
    render_ops_dashboard,
)

ops_app = typer.Typer(help="Operations and monitoring commands")


@ops_app.command(name="dashboard")
def dashboard_cmd(
    dashboard_type: str = typer.Option(
        "ops",
        "--type",
        help="Dashboard type to generate",
        case_sensitive=False,
    ),
    output_format: str = typer.Option(
        "markdown",
        "--format",
        help="Output format",
        case_sensitive=False,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: stdout)",
    ),
    window_hours: int = typer.Option(
        24,
        "--window-hours",
        help="Time window in hours for metrics",
    ),
    pool_id: List[str] = typer.Option(
        None,
        "--pool-id",
        help="Specific pool IDs to include (can specify multiple)",
    ),
    vrs_root: Optional[Path] = typer.Option(
        None,
        "--vrs-root",
        help="VRS root directory (default: .vrs)",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
):
    """Generate operations dashboard.

    Examples:

        alphaswarm ops dashboard

        alphaswarm ops dashboard --type latency --format json

        alphaswarm ops dashboard --type accuracy --pool-id pool-001

        alphaswarm ops dashboard --output ops-report.md
    """
    # Validate dashboard type
    dashboard_type = dashboard_type.lower()
    if dashboard_type not in ["latency", "accuracy", "ops"]:
        typer.echo(f"Error: Invalid dashboard type '{dashboard_type}'. Must be one of: latency, accuracy, ops", err=True)
        raise typer.Exit(code=1)

    # Validate format
    output_format = output_format.lower()
    if output_format not in ["markdown", "json", "toon"]:
        typer.echo(f"Error: Invalid format '{output_format}'. Must be one of: markdown, json, toon", err=True)
        raise typer.Exit(code=1)

    # Convert format string to enum
    fmt = OutputFormat(output_format)

    # Convert pool_id list to proper format (or None if empty)
    pool_ids = pool_id if pool_id else None

    # Default VRS root
    if vrs_root is None:
        vrs_root = Path(".vrs")

    # Generate dashboard
    try:
        if dashboard_type == "latency":
            content = render_latency_dashboard(
                pool_ids=pool_ids,
                format=fmt,
                window_hours=window_hours,
                vrs_root=vrs_root,
            )
        elif dashboard_type == "accuracy":
            content = render_accuracy_dashboard(
                pool_ids=pool_ids,
                format=fmt,
                window_hours=window_hours,
                vrs_root=vrs_root,
            )
        else:  # ops
            content = render_ops_dashboard(
                pool_ids=pool_ids,
                format=fmt,
                window_hours=window_hours,
                vrs_root=vrs_root,
            )

        # Output to file or stdout
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content, encoding="utf-8")
            typer.echo(f"Dashboard written to {output}")
        else:
            typer.echo(content)

    except Exception as e:
        typer.echo(f"Error generating dashboard: {e}", err=True)
        raise typer.Exit(code=1)


__all__ = ["ops_app", "dashboard_cmd"]
