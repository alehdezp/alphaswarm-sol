"""CLI commands for VulnDocs knowledge discovery and management.

Commands for:
- Fetching new findings from Solodit
- Scanning for emerging vulnerabilities via Exa
- Reviewing discovery queues
- Managing VulnDocs integration
- Validating VulnDocs structure (Phase 5.4)
- Scaffolding new vulnerabilities (Phase 5.4)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

vulndocs_app = typer.Typer(
    help="VulnDocs knowledge discovery and management commands"
)

console = Console()


def _parse_since(since: str) -> int:
    """Parse --since argument to days.

    Supports formats: 7d, 1w, 2w, 30d
    """
    since = since.lower().strip()

    if since.endswith("d"):
        return int(since[:-1])
    elif since.endswith("w"):
        return int(since[:-1]) * 7
    else:
        try:
            return int(since)
        except ValueError:
            raise typer.BadParameter(
                f"Invalid --since format: {since}. Use: 7d, 1w, 30d"
            )


@vulndocs_app.command("fetch-solodit")
def fetch_solodit(
    since: str = typer.Option(
        "7d", "--since", "-s", help="How far back to fetch (e.g., 7d, 1w, 30d)"
    ),
    max_results: int = typer.Option(
        50, "--max", "-m", help="Maximum results to fetch"
    ),
    cache_dir: str | None = typer.Option(
        None, "--cache-dir", help="Cache directory (default: .vrs/discovery)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be fetched without queuing"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Fetch new audit findings from Solodit.

    Fetches new vulnerability findings from Solodit and queues them
    for human review. Does NOT auto-integrate into VulnDocs.

    Examples:
        # Fetch findings from last 7 days
        uv run alphaswarm vulndocs fetch-solodit

        # Fetch last 2 weeks
        uv run alphaswarm vulndocs fetch-solodit --since 2w

        # Dry run to see what would be fetched
        uv run alphaswarm vulndocs fetch-solodit --dry-run --verbose
    """
    try:
        from alphaswarm_sol.vulndocs.scrapers import SoloditFetcher

        days_back = _parse_since(since)

        if verbose:
            typer.echo(f"Fetching Solodit findings from last {days_back} days...")

        # Create fetcher
        fetcher = SoloditFetcher(
            cache_dir=Path(cache_dir) if cache_dir else None
        )

        # Check if crawl4ai is available
        if not fetcher._crawl4ai_available:
            typer.echo(
                "Warning: crawl4ai not installed. Install with: pip install crawl4ai",
                err=True,
            )
            typer.echo("Solodit fetching requires crawl4ai for web scraping.", err=True)

        # Fetch findings
        findings = asyncio.run(
            fetcher.fetch_new(days_back=days_back, max_results=max_results)
        )

        if not findings:
            typer.echo("No new findings found.")
            return

        typer.echo(f"Found {len(findings)} new findings")

        if verbose:
            typer.echo("")
            for f in findings:
                typer.echo(f"  [{f.severity}] {f.title}")
                typer.echo(f"    Category: {f.suggested_category}")
                typer.echo(f"    Operations: {', '.join(f.suggested_operations)}")
                typer.echo("")

        if dry_run:
            typer.echo("Dry run - findings not queued")
        else:
            queued = fetcher.queue_for_review(findings)
            typer.echo(f"Queued {queued} findings for review")
            typer.echo(f"Review with: uv run alphaswarm vulndocs review-queue")

    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@vulndocs_app.command("scan-exa")
def scan_exa(
    days: int = typer.Option(7, "--days", "-d", help="Days to look back"),
    category: str | None = typer.Option(
        None, "--category", "-c", help="Filter by category (e.g., reentrancy, oracle)"
    ),
    cache_dir: str | None = typer.Option(
        None, "--cache-dir", help="Cache directory"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be found without queuing"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Scan for emerging vulnerabilities using Exa search.

    Uses Exa API to discover new vulnerability research, exploit
    writeups, and security articles. Queues discoveries for human review.

    Requires EXA_API_KEY environment variable.

    Examples:
        # Scan last 7 days
        uv run alphaswarm vulndocs scan-exa

        # Scan specific category
        uv run alphaswarm vulndocs scan-exa --category reentrancy

        # Dry run
        uv run alphaswarm vulndocs scan-exa --dry-run --verbose
    """
    try:
        import os

        from alphaswarm_sol.vulndocs.automation import ExaScanner

        # Check for API key
        if not os.environ.get("EXA_API_KEY"):
            typer.echo(
                "Error: EXA_API_KEY environment variable not set", err=True
            )
            typer.echo(
                "Get your API key from: https://exa.ai/dashboard/api-keys", err=True
            )
            raise typer.Exit(code=1)

        if verbose:
            typer.echo(f"Scanning Exa for vulnerabilities from last {days} days...")
            if category:
                typer.echo(f"Filtering by category: {category}")

        # Create scanner
        scanner = ExaScanner(
            cache_dir=Path(cache_dir) if cache_dir else None
        )

        # Scan
        discoveries = asyncio.run(
            scanner.scan(days_back=days, category_filter=category)
        )

        if not discoveries:
            typer.echo("No new discoveries found.")
            return

        typer.echo(f"Found {len(discoveries)} discoveries")

        if verbose:
            typer.echo("")
            for d in discoveries:
                typer.echo(f"  [{d.relevance_score:.2f}] {d.title}")
                typer.echo(f"    Query: {d.query_matched}")
                typer.echo(f"    URL: {d.url}")
                typer.echo("")

        if dry_run:
            typer.echo("Dry run - discoveries not queued")
        else:
            queued = scanner.queue_for_review(discoveries)
            typer.echo(f"Queued {queued} discoveries for review")
            typer.echo(f"Review with: uv run alphaswarm vulndocs review-queue")

    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@vulndocs_app.command("review-queue")
def review_queue(
    source: str = typer.Option(
        "all", "--source", "-s", help="Source to review (solodit, exa, all)"
    ),
    limit: int = typer.Option(10, "--limit", "-l", help="Items to show"),
    cache_dir: str | None = typer.Option(
        None, "--cache-dir", help="Cache directory"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactive review mode"
    ),
) -> None:
    """Review pending discoveries in the queue.

    Shows pending items from Solodit and Exa scans that require
    human review before VulnDocs integration.

    Actions in interactive mode:
    - ACCEPT: Accept for VulnDocs integration
    - MERGE: Merge into existing pattern
    - REJECT: Reject (not relevant)
    - DEFER: Defer for later

    Examples:
        # Show pending items
        uv run alphaswarm vulndocs review-queue

        # Interactive review
        uv run alphaswarm vulndocs review-queue --interactive

        # Review specific source
        uv run alphaswarm vulndocs review-queue --source solodit
    """
    try:
        cache_path = Path(cache_dir) if cache_dir else Path(".vrs/discovery")

        # Gather pending items
        pending_items: list[tuple[str, dict]] = []

        if source in ("all", "solodit"):
            solodit_queue = cache_path / "solodit_queue.yaml"
            if solodit_queue.exists():
                import yaml

                with open(solodit_queue) as f:
                    data = yaml.safe_load(f) or {}
                for item in data.get("pending_review", [])[:limit]:
                    pending_items.append(("solodit", item))

        if source in ("all", "exa"):
            exa_queue = cache_path / "exa_queue.yaml"
            if exa_queue.exists():
                import yaml

                with open(exa_queue) as f:
                    data = yaml.safe_load(f) or {}
                for item in data.get("pending_review", [])[:limit]:
                    pending_items.append(("exa", item))

        if not pending_items:
            typer.echo("No pending items in review queue.")
            typer.echo("")
            typer.echo("Fetch new discoveries with:")
            typer.echo("  uv run alphaswarm vulndocs fetch-solodit")
            typer.echo("  uv run alphaswarm vulndocs scan-exa")
            return

        typer.echo(f"Pending Review: {len(pending_items)} items")
        typer.echo("=" * 60)
        typer.echo("")

        for i, (src, item) in enumerate(pending_items[:limit], 1):
            _print_review_item(i, src, item)

        if interactive:
            _run_interactive_review(cache_path, pending_items[:limit])

    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def _print_review_item(index: int, source: str, item: dict) -> None:
    """Print a single review item."""
    typer.echo(f"{index}. [{source.upper()}] {item.get('title', 'Untitled')}")

    if source == "solodit":
        typer.echo(f"   Severity: {item.get('severity', 'UNKNOWN')}")
        typer.echo(f"   Category: {item.get('suggested_category', 'unknown')}")
        if item.get("suggested_operations"):
            typer.echo(f"   Operations: {', '.join(item['suggested_operations'])}")
    elif source == "exa":
        typer.echo(f"   Query: {item.get('query_matched', '')}")
        typer.echo(f"   Score: {item.get('relevance_score', 0):.2f}")

    typer.echo(f"   URL: {item.get('url', '')}")
    typer.echo("")


def _run_interactive_review(cache_path: Path, items: list[tuple[str, dict]]) -> None:
    """Run interactive review mode."""
    import yaml

    from alphaswarm_sol.vulndocs.scrapers import SoloditFetcher

    typer.echo("-" * 60)
    typer.echo("Interactive Review Mode")
    typer.echo("Commands: [a]ccept, [m]erge, [r]eject, [d]efer, [s]kip, [q]uit")
    typer.echo("-" * 60)
    typer.echo("")

    solodit_fetcher = SoloditFetcher(cache_dir=cache_path)

    for i, (source, item) in enumerate(items, 1):
        typer.echo(f"Item {i}/{len(items)}")
        _print_review_item(i, source, item)

        while True:
            action = typer.prompt("Action", default="s")
            action = action.lower().strip()

            if action in ("a", "accept"):
                if source == "solodit":
                    solodit_fetcher.mark_processed(
                        item["id"], "ACCEPT", item.get("suggested_category")
                    )
                typer.echo("  Accepted for integration")
                break
            elif action in ("m", "merge"):
                target = typer.prompt("  Merge into (category path)")
                if source == "solodit":
                    solodit_fetcher.mark_processed(item["id"], "MERGE", target)
                typer.echo(f"  Marked for merge into {target}")
                break
            elif action in ("r", "reject"):
                if source == "solodit":
                    solodit_fetcher.mark_processed(item["id"], "REJECT")
                typer.echo("  Rejected")
                break
            elif action in ("d", "defer"):
                typer.echo("  Deferred for later")
                break
            elif action in ("s", "skip"):
                typer.echo("  Skipped")
                break
            elif action in ("q", "quit"):
                typer.echo("Exiting review")
                return
            else:
                typer.echo("  Unknown action. Try: a, m, r, d, s, q")

        typer.echo("")

    typer.echo("Review complete!")


@vulndocs_app.command("queue-status")
def queue_status(
    cache_dir: str | None = typer.Option(
        None, "--cache-dir", help="Cache directory"
    ),
) -> None:
    """Show status of discovery queues.

    Displays counts of pending and processed items from all
    discovery sources.

    Example:
        uv run alphaswarm vulndocs queue-status
    """
    try:
        import yaml

        cache_path = Path(cache_dir) if cache_dir else Path(".vrs/discovery")

        typer.echo("Discovery Queue Status")
        typer.echo("=" * 40)

        # Solodit queue
        solodit_queue = cache_path / "solodit_queue.yaml"
        if solodit_queue.exists():
            with open(solodit_queue) as f:
                data = yaml.safe_load(f) or {}
            pending = len(data.get("pending_review", []))
            processed = len(data.get("processed", []))
            last_updated = data.get("last_updated", "Never")
            typer.echo(f"Solodit: {pending} pending, {processed} processed")
            typer.echo(f"  Last updated: {last_updated}")
        else:
            typer.echo("Solodit: No queue found")

        typer.echo("")

        # Exa queue
        exa_queue = cache_path / "exa_queue.yaml"
        if exa_queue.exists():
            with open(exa_queue) as f:
                data = yaml.safe_load(f) or {}
            pending = len(data.get("pending_review", []))
            processed = len(data.get("processed", []))
            last_scan = data.get("last_scan", "Never")
            typer.echo(f"Exa: {pending} pending, {processed} processed")
            typer.echo(f"  Last scan: {last_scan}")
        else:
            typer.echo("Exa: No queue found")

        typer.echo("")
        typer.echo("Commands:")
        typer.echo("  Fetch Solodit: uv run alphaswarm vulndocs fetch-solodit")
        typer.echo("  Scan Exa: uv run alphaswarm vulndocs scan-exa")
        typer.echo("  Review: uv run alphaswarm vulndocs review-queue")

    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc



# Phase 5.4: Framework validation and scaffolding commands


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
    from alphaswarm_sol.vulndocs.validation import validate_framework
    from alphaswarm_sol.vulndocs.types import ValidationLevel

    root = Path(path)

    if not root.exists():
        console.print(f"[red]Error:[/red] Path not found: {root}")
        raise typer.Exit(code=1)

    # Run validation
    validation = validate_framework(root)

    if json_output:
        # JSON output for CI
        output = {
            "root": str(root),
            "total_errors": sum(len(r.errors) for r in validation.vulnerabilities),
            "total_warnings": sum(len(r.warnings) for r in validation.vulnerabilities),
            "total_suggestions": sum(len(r.suggestions) for r in validation.vulnerabilities),
            "results": [
                {
                    "path": str(r.path.relative_to(root)),
                    "level": r.level.value if r.level else "none",
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "suggestions": r.suggestions,
                }
                for r in validation.vulnerabilities
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        # Rich formatted output
        console.print("\n[bold]VulnDocs Validation Results[/bold]\n")

        if not validation.vulnerabilities:
            console.print("[yellow]No vulnerabilities found to validate[/yellow]")
        else:
            # Create table
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Path", style="cyan")
            table.add_column("Level", style="green")
            table.add_column("Issues", style="yellow")

            for result in validation.vulnerabilities:
                # Level icon
                level_icons = {
                    ValidationLevel.MINIMAL: "⚪",
                    ValidationLevel.STANDARD: "🟡",
                    ValidationLevel.COMPLETE: "🟢",
                    ValidationLevel.EXCELLENT: "🌟",
                }
                level_icon = level_icons.get(result.level, "❓") if result.level else "❌"
                level_str = f"{level_icon} {result.level.value.upper()}" if result.level else "❌ FAILED"

                # Issue count
                error_count = len(result.errors)
                warning_count = len(result.warnings)
                suggestion_count = len(result.suggestions)

                issues_parts = []
                if error_count:
                    issues_parts.append(f"[red]{error_count} error{'s' if error_count > 1 else ''}[/red]")
                if warning_count:
                    issues_parts.append(f"[yellow]{warning_count} warning{'s' if warning_count > 1 else ''}[/yellow]")
                if suggestion_count:
                    issues_parts.append(f"[cyan]{suggestion_count} suggestion{'s' if suggestion_count > 1 else ''}[/cyan]")

                issues_str = ", ".join(issues_parts) if issues_parts else "[green]None[/green]"

                table.add_row(str(result.path.relative_to(root)), level_str, issues_str)

            console.print(table)

            # Show detailed issues
            total_errors = sum(len(r.errors) for r in validation.vulnerabilities)
            total_warnings = sum(len(r.warnings) for r in validation.vulnerabilities)
            total_suggestions = sum(len(r.suggestions) for r in validation.vulnerabilities)

            if total_errors or total_warnings or total_suggestions:
                console.print("\n[bold]Issues:[/bold]\n")

                for result in validation.vulnerabilities:
                    if result.errors or result.warnings or result.suggestions:
                        console.print(f"[cyan]{result.path.relative_to(root)}[/cyan]:")
                        for error in result.errors:
                            console.print(f"  [red]ERROR:[/red] {error}")
                        for warning in result.warnings:
                            console.print(f"  [yellow]WARNING:[/yellow] {warning}")
                        for suggestion in result.suggestions:
                            console.print(f"  [cyan]SUGGESTION:[/cyan] {suggestion}")

        # Summary
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Validated: {len(validation.vulnerabilities)} entries")
        console.print(f"  Errors: [red]{sum(len(r.errors) for r in validation.vulnerabilities)}[/red]")
        console.print(f"  Warnings: [yellow]{sum(len(r.warnings) for r in validation.vulnerabilities)}[/yellow]")
        console.print(f"  Suggestions: [cyan]{sum(len(r.suggestions) for r in validation.vulnerabilities)}[/cyan]")

    # Exit code
    if validation.has_errors:
        raise typer.Exit(code=1)
    if strict and any(r.has_warnings for r in validation.vulnerabilities):
        console.print("\n[yellow]Strict mode: treating warnings as errors[/yellow]")
        raise typer.Exit(code=1)


@vulndocs_app.command("scaffold")
def scaffold_cmd(
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
    from alphaswarm_sol.vulndocs.scaffold import (
        scaffold_vulnerability,
        validate_scaffold_inputs,
    )

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
def info_cmd(
    path: str = typer.Argument("vulndocs", help="Path to vulndocs root directory"),
) -> None:
    """Show VulnDocs framework statistics.

    Displays summary of categories, vulnerabilities, patterns, and
    validation coverage.

    Examples:
        uv run alphaswarm vulndocs info
        uv run alphaswarm vulndocs info /path/to/vulndocs
    """
    from alphaswarm_sol.vulndocs.validation import validate_framework
    from alphaswarm_sol.vulndocs.discovery import discover_categories, discover_patterns
    from alphaswarm_sol.vulndocs.types import ValidationLevel

    root = Path(path)

    if not root.exists():
        console.print(f"[red]Error:[/red] Path not found: {root}")
        raise typer.Exit(code=1)

    # Collect statistics
    categories = discover_categories(root)
    validation = validate_framework(root)

    # Count patterns from validation results
    total_patterns = 0
    for result in validation.vulnerabilities:
        patterns_dir = result.path / "patterns"
        if patterns_dir.exists():
            total_patterns += len(list(patterns_dir.glob("*.yaml")))

    level_counts = {level: 0 for level in ValidationLevel}
    for result in validation.vulnerabilities:
        if result.level:
            level_counts[result.level] += 1

    # Display statistics
    console.print("\n[bold]VulnDocs Framework Statistics[/bold]\n")

    # Summary table
    summary_table = Table(show_header=False)
    summary_table.add_row("[cyan]Categories[/cyan]", str(len(categories)))
    summary_table.add_row("[cyan]Vulnerabilities[/cyan]", str(len(validation.vulnerabilities)))
    summary_table.add_row("[cyan]Patterns[/cyan]", str(total_patterns))
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
    if validation.vulnerabilities:
        vulns_without_patterns = [
            r for r in validation.vulnerabilities 
            if not (r.path / "patterns").exists() or not list((r.path / "patterns").glob("*.yaml"))
        ]

        if vulns_without_patterns:
            console.print("\n[yellow]Coverage Gaps:[/yellow]")
            console.print(f"  {len(vulns_without_patterns)} vulnerabilities without patterns:")
            for result in vulns_without_patterns[:5]:
                console.print(f"    • {result.path.relative_to(root)}")
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
    from alphaswarm_sol.vulndocs.validation import validate_framework
    from alphaswarm_sol.vulndocs.types import ValidationLevel

    root = Path(path)

    if not root.exists():
        console.print(f"[red]Error:[/red] Path not found: {root}")
        raise typer.Exit(code=1)

    # Run validation to get levels
    validation = validate_framework(root)

    # Filter results
    results = validation.vulnerabilities

    if category:
        results = [r for r in results if str(r.path.relative_to(root)).startswith(category + "/")]

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

    for result in sorted(results, key=lambda r: str(r.path)):
        level_icons = {
            ValidationLevel.MINIMAL: "⚪",
            ValidationLevel.STANDARD: "🟡",
            ValidationLevel.COMPLETE: "🟢",
            ValidationLevel.EXCELLENT: "🌟",
        }
        level_icon = level_icons.get(result.level, "❓") if result.level else "❌"
        level_str = f"{level_icon} {result.level.value.upper()}" if result.level else "❌ FAILED"

        issue_count = len(result.errors) + len(result.warnings)
        issues_str = str(issue_count) if issue_count > 0 else "[green]0[/green]"

        table.add_row(str(result.path.relative_to(root)), level_str, issues_str)

    console.print(f"\n[bold]Vulnerabilities ({len(results)}):[/bold]\n")
    console.print(table)
