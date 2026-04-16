"""VKG health check command."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from alphaswarm_sol.core.availability import (
    check_tool_available,
    check_vulndocs_available,
    check_skills_available,
    get_available_tools,
    REQUIRED_TOOLS,
    OPTIONAL_TOOLS,
)

app = typer.Typer(help="Health check commands")
console = Console()


@app.callback(invoke_without_command=True)
def health_check(
    ctx: typer.Context,
    project: Path = typer.Option(
        Path("."),
        "--project",
        "-p",
        help="Project directory to check",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output results as JSON",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed information",
    ),
) -> None:
    """Validate True VKG installation and configuration.

    Checks:
    1. CLI availability (alphaswarm command)
    2. Required tools (Slither)
    3. Optional tools (Aderyn, Mythril, Foundry, etc.)
    4. Vulndocs presence
    5. Skills loaded (.claude/vrs/*.md)

    Example:
        alphaswarm health-check
        alphaswarm health-check --json
        alphaswarm health-check --project ./my-project --verbose
    """
    results = run_health_check(project, verbose=verbose)

    if json_output:
        console.print_json(json.dumps(results, indent=2))
        return

    # Display results
    display_health_results(results, verbose=verbose)

    # Exit with error if any required checks failed
    if not results["healthy"]:
        raise typer.Exit(1)


def run_health_check(project: Path, verbose: bool = False) -> dict:
    """Run health check and return results dict.

    Args:
        project: Project directory to check
        verbose: Include extra details

    Returns:
        Dict with health check results
    """
    results = {
        "healthy": True,
        "project": str(project.absolute()),
        "checks": {},
        "fixes": [],
    }

    # Check 1: CLI (always passes if we're running)
    results["checks"]["cli"] = {
        "status": "pass",
        "message": "alphaswarm CLI available",
    }

    # Check 2: Required tools
    for tool in REQUIRED_TOOLS:
        status = check_tool_available(tool)
        if status.available:
            results["checks"][f"tool_{tool}"] = {
                "status": "pass",
                "message": f"{tool} available",
                "version": status.version,
                "path": status.path,
            }
        else:
            results["healthy"] = False
            results["checks"][f"tool_{tool}"] = {
                "status": "fail",
                "message": status.error,
                "required": True,
            }
            if tool == "slither":
                results["fixes"].append(
                    f"Install {tool}: pip install slither-analyzer"
                )
            else:
                results["fixes"].append(
                    f"Install {tool}: pip install {tool}"
                )

    # Check 3: Optional tools
    for tool in OPTIONAL_TOOLS:
        status = check_tool_available(tool)
        if status.available:
            results["checks"][f"tool_{tool}"] = {
                "status": "pass",
                "message": f"{tool} available",
                "version": status.version,
            }
        else:
            results["checks"][f"tool_{tool}"] = {
                "status": "warn",
                "message": f"{tool} not available (optional)",
            }

    # Check 4: Vulndocs
    vd_available, vd_path, vd_error = check_vulndocs_available()
    if vd_available:
        results["checks"]["vulndocs"] = {
            "status": "pass",
            "message": "Vulndocs found",
            "path": str(vd_path),
        }
    else:
        results["checks"]["vulndocs"] = {
            "status": "warn",
            "message": vd_error,
        }

    # Check 5: Skills
    sk_available, sk_count, sk_error = check_skills_available(project)
    if sk_available:
        results["checks"]["skills"] = {
            "status": "pass",
            "message": f"{sk_count} skills loaded",
        }
    else:
        # Skills are optional for VKG, warn only
        results["checks"]["skills"] = {
            "status": "warn",
            "message": sk_error or "Skills not installed",
        }
        results["fixes"].append(
            "Initialize skills: Create .claude/vrs/ directory and add skill files"
        )

    # Check 6: Beads directory
    beads_dir = project / ".beads"
    if beads_dir.exists():
        results["checks"]["beads"] = {
            "status": "pass",
            "message": "Beads directory exists",
        }
    else:
        results["checks"]["beads"] = {
            "status": "warn",
            "message": "Beads directory not found (created on first use)",
        }

    return results


def display_health_results(results: dict, verbose: bool = False) -> None:
    """Display health check results in a table."""
    table = Table(title="True VKG Health Check")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Details", style="dim")

    status_styles = {
        "pass": "[green]PASS[/green]",
        "warn": "[yellow]WARN[/yellow]",
        "fail": "[red]FAIL[/red]",
    }

    for name, check in results["checks"].items():
        status = status_styles.get(check["status"], check["status"])
        details = check.get("message", "")
        if verbose and "version" in check:
            details += f" (v{check['version']})"
        table.add_row(name, status, details)

    console.print(table)

    if results["fixes"]:
        console.print("\n[bold]Suggested fixes:[/bold]")
        for fix in results["fixes"]:
            console.print(f"  [yellow]*[/yellow] {fix}")

    if results["healthy"]:
        console.print("\n[green]VKG is healthy![/green]")
    else:
        console.print("\n[red]VKG has issues that need attention.[/red]")
