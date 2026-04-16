"""CLI commands for VulnDocs management."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from alphaswarm_sol.vulndocs.scaffold import (
    scaffold_vulnerability,
    validate_scaffold_inputs,
)
from alphaswarm_sol.vulndocs.validation import (
    validate_framework,
    IssueType,
)
from alphaswarm_sol.vulndocs.types import ValidationLevel


console = Console()
vulndocs_app = typer.Typer(help="VulnDocs management commands")


@vulndocs_app.command("validate")
def validate(
    path: str = typer.Argument("vulndocs", help="Path to vulndocs root directory"),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as errors"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON for CI"),
) -> None:
    """Validate VulnDocs framework structure and content.

    Runs progressive validation and displays results with colored output.
    Exit code 1 if errors found (or warnings with --strict).

    Examples:
        uv run alphaswarm vulndocs validate
        uv run alphaswarm vulndocs validate vulndocs/ --strict
        uv run alphaswarm vulndocs validate --json
    """
    root = Path(path)

    if not root.exists():
        console.print(f"[red]Error:[/red] Path not found: {root}")
        raise typer.Exit(code=1)

    # Run validation
    validation = validate_framework(root)

    if json_output:
        # JSON output for CI
        output = {
            "root": str(validation.root),
            "total_errors": validation.total_errors,
            "total_warnings": validation.total_warnings,
            "total_suggestions": validation.total_suggestions,
            "results": [
                {
                    "path": r.path,
                    "level": r.level.value,
                    "issues": [
                        {
                            "type": i.type.value,
                            "message": i.message,
                            "field": i.field,
                        }
                        for i in r.issues
                    ],
                }
                for r in validation.results
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        # Rich formatted output
        console.print("\n[bold]VulnDocs Validation Results[/bold]\n")

        if not validation.results:
            console.print("[yellow]No vulnerabilities found to validate[/yellow]")
        else:
            # Create table
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Path", style="cyan")
            table.add_column("Level", style="green")
            table.add_column("Issues", style="yellow")

            for result in validation.results:
                # Level icon
                level_icons = {
                    ValidationLevel.MINIMAL: "⚪",
                    ValidationLevel.STANDARD: "🟡",
                    ValidationLevel.COMPLETE: "🟢",
                    ValidationLevel.EXCELLENT: "🌟",
                }
                level_icon = level_icons.get(result.level, "❓")
                level_str = f"{level_icon} {result.level.value.upper()}"

                # Issue count
                error_count = sum(1 for i in result.issues if i.type == IssueType.ERROR)
                warning_count = sum(1 for i in result.issues if i.type == IssueType.WARNING)
                suggestion_count = sum(1 for i in result.issues if i.type == IssueType.SUGGESTION)

                issues_parts = []
                if error_count:
                    issues_parts.append(f"[red]{error_count} error{'s' if error_count > 1 else ''}[/red]")
                if warning_count:
                    issues_parts.append(f"[yellow]{warning_count} warning{'s' if warning_count > 1 else ''}[/yellow]")
                if suggestion_count:
                    issues_parts.append(f"[cyan]{suggestion_count} suggestion{'s' if suggestion_count > 1 else ''}[/cyan]")

                issues_str = ", ".join(issues_parts) if issues_parts else "[green]None[/green]"

                table.add_row(result.path, level_str, issues_str)

            console.print(table)

            # Show detailed issues
            if validation.total_errors or validation.total_warnings or validation.total_suggestions:
                console.print("\n[bold]Issues:[/bold]\n")

                for result in validation.results:
                    if result.issues:
                        console.print(f"[cyan]{result.path}[/cyan]:")
                        for issue in result.issues:
                            if issue.type == IssueType.ERROR:
                                console.print(f"  [red]ERROR:[/red] {issue.message}")
                            elif issue.type == IssueType.WARNING:
                                console.print(f"  [yellow]WARNING:[/yellow] {issue.message}")
                            else:
                                console.print(f"  [cyan]SUGGESTION:[/cyan] {issue.message}")

        # Summary
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Validated: {len(validation.results)} entries")
        console.print(f"  Errors: [red]{validation.total_errors}[/red]")
        console.print(f"  Warnings: [yellow]{validation.total_warnings}[/yellow]")
        console.print(f"  Suggestions: [cyan]{validation.total_suggestions}[/cyan]")

    # Exit code
    if validation.has_errors:
        raise typer.Exit(code=1)
    if strict and validation.has_warnings:
        console.print("\n[yellow]Strict mode: treating warnings as errors[/yellow]")
        raise typer.Exit(code=1)


@vulndocs_app.command("scaffold")
def scaffold(
    category: str = typer.Argument(..., help="Category ID (e.g., 'oracle')"),
    subcategory: str = typer.Argument(..., help="Subcategory ID (e.g., 'price-manipulation')"),
    severity: str = typer.Option("medium", "--severity", "-s", help="Severity level (critical/high/medium/low)"),
    root: str = typer.Option("vulndocs", "--root", "-r", help="VulnDocs root directory"),
) -> None:
    """Create a new vulnerability from template.

    Creates the full vulnerability structure including index.yaml,
    markdown files, and patterns/ folder.

    Examples:
        uv run alphaswarm vulndocs scaffold oracle price-manipulation
        uv run alphaswarm vulndocs scaffold access-control weak-randomness --severity high
    """
    root_path = Path(root)

    if not root_path.exists():
        console.print(f"[red]Error:[/red] VulnDocs root not found: {root_path}")
        console.print("[yellow]Hint:[/yellow] Run from project root or specify --root")
        raise typer.Exit(code=1)

    # Validate inputs
    errors = validate_scaffold_inputs(category, subcategory)
    if errors:
        console.print("[red]Validation errors:[/red]")
        for error in errors:
            console.print(f"  • {error}")
        raise typer.Exit(code=1)

    try:
        # Create vulnerability
        vuln_path = scaffold_vulnerability(root_path, category, subcategory, severity)

        # Display created structure
        console.print(f"\n[green]✓[/green] Created vulnerability: [cyan]{category}/{subcategory}[/cyan]\n")

        tree = Tree(f"[bold]{vuln_path.name}/[/bold]")
        tree.add("[cyan]index.yaml[/cyan]")
        tree.add("overview.md")
        tree.add("detection.md")
        tree.add("verification.md")
        tree.add("exploits.md")
        tree.add("[bold]patterns/[/bold]")

        console.print(tree)

        console.print("\n[bold]Next steps:[/bold]")
        console.print(f"  1. Edit [cyan]{vuln_path}/index.yaml[/cyan] with vulnerability metadata")
        console.print(f"  2. Fill in [cyan]{vuln_path}/overview.md[/cyan] with description")
        console.print(f"  3. Add detection logic to [cyan]{vuln_path}/detection.md[/cyan]")
        console.print(f"  4. Create patterns in [cyan]{vuln_path}/patterns/[/cyan]")
        console.print(f"\n  Run: [yellow]uv run alphaswarm vulndocs validate[/yellow] to check")

    except FileExistsError:
        console.print(f"[red]Error:[/red] Vulnerability already exists: {category}/{subcategory}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@vulndocs_app.command("info")
def info(
    path: str = typer.Argument("vulndocs", help="Path to vulndocs root directory"),
) -> None:
    """Show VulnDocs framework statistics.

    Displays summary of categories, vulnerabilities, patterns, and
    validation coverage.

    Examples:
        uv run alphaswarm vulndocs info
        uv run alphaswarm vulndocs info /path/to/vulndocs
    """
    root = Path(path)

    if not root.exists():
        console.print(f"[red]Error:[/red] Path not found: {root}")
        raise typer.Exit(code=1)

    # Collect statistics
    categories = []
    vulnerabilities = []
    patterns = []
    level_counts = {level: 0 for level in ValidationLevel}

    if root.exists():
        for category_dir in root.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith("_"):
                categories.append(category_dir.name)

                for vuln_dir in category_dir.iterdir():
                    if vuln_dir.is_dir():
                        vuln_path = f"{category_dir.name}/{vuln_dir.name}"
                        vulnerabilities.append(vuln_path)

                        # Count patterns
                        patterns_dir = vuln_dir / "patterns"
                        if patterns_dir.exists():
                            pattern_files = list(patterns_dir.glob("*.yaml"))
                            patterns.extend(pattern_files)

    # Run validation to get levels
    validation = validate_framework(root)
    for result in validation.results:
        level_counts[result.level] += 1

    # Display statistics
    console.print("\n[bold]VulnDocs Framework Statistics[/bold]\n")

    # Summary table
    summary_table = Table(show_header=False)
    summary_table.add_row("[cyan]Categories[/cyan]", str(len(categories)))
    summary_table.add_row("[cyan]Vulnerabilities[/cyan]", str(len(vulnerabilities)))
    summary_table.add_row("[cyan]Patterns[/cyan]", str(len(patterns)))
    console.print(summary_table)

    # Validation levels
    console.print("\n[bold]Validation Levels:[/bold]")
    level_table = Table(show_header=True, header_style="bold")
    level_table.add_column("Level")
    level_table.add_column("Count", justify="right")

    for level in ValidationLevel:
        count = level_counts[level]
        if count > 0:
            level_table.add_row(level.value.upper(), str(count))

    console.print(level_table)

    # Coverage gaps
    if vulnerabilities:
        vulns_without_patterns = []
        for vuln_path in vulnerabilities:
            category, subcategory = vuln_path.split("/")
            patterns_dir = root / category / subcategory / "patterns"
            if not patterns_dir.exists() or not list(patterns_dir.glob("*.yaml")):
                vulns_without_patterns.append(vuln_path)

        if vulns_without_patterns:
            console.print("\n[yellow]Coverage Gaps:[/yellow]")
            console.print(f"  {len(vulns_without_patterns)} vulnerabilities without patterns:")
            for vuln in vulns_without_patterns[:5]:
                console.print(f"    • {vuln}")
            if len(vulns_without_patterns) > 5:
                console.print(f"    ... and {len(vulns_without_patterns) - 5} more")


@vulndocs_app.command("list")
def list_vulns(
    path: str = typer.Argument("vulndocs", help="Path to vulndocs root directory"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    level: Optional[str] = typer.Option(None, "--level", "-l", help="Filter by validation level"),
) -> None:
    """List all vulnerabilities in the framework.

    Optionally filter by category or validation level.

    Examples:
        uv run alphaswarm vulndocs list
        uv run alphaswarm vulndocs list --category oracle
        uv run alphaswarm vulndocs list --level excellent
    """
    root = Path(path)

    if not root.exists():
        console.print(f"[red]Error:[/red] Path not found: {root}")
        raise typer.Exit(code=1)

    # Run validation to get levels
    validation = validate_framework(root)

    # Filter results
    results = validation.results

    if category:
        results = [r for r in results if r.path.startswith(category + "/")]

    if level:
        try:
            target_level = ValidationLevel(level.lower())
            results = [r for r in results if r.level == target_level]
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid level: {level}")
            console.print(f"Valid levels: {', '.join(l.value for l in ValidationLevel)}")
            raise typer.Exit(code=1)

    if not results:
        console.print("[yellow]No vulnerabilities found matching filters[/yellow]")
        return

    # Display table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Path", style="cyan")
    table.add_column("Level", style="green")
    table.add_column("Issues", justify="right")

    for result in sorted(results, key=lambda r: r.path):
        level_icons = {
            ValidationLevel.MINIMAL: "⚪",
            ValidationLevel.STANDARD: "🟡",
            ValidationLevel.COMPLETE: "🟢",
            ValidationLevel.EXCELLENT: "🌟",
        }
        level_icon = level_icons.get(result.level, "❓")
        level_str = f"{level_icon} {result.level.value.upper()}"

        issue_count = len(result.issues)
        issues_str = str(issue_count) if issue_count > 0 else "[green]0[/green]"

        table.add_row(result.path, level_str, issues_str)

    console.print(f"\n[bold]Vulnerabilities ({len(results)}):[/bold]\n")
    console.print(table)
