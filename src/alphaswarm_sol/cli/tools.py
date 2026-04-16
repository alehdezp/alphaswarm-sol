"""
Tools subcommand for VKG CLI.

Provides visibility into tool availability and system state,
plus commands for running static analysis tools.

Commands:
- status: Show tool availability status
- check: Check if a specific tool is available
- list: List all known tools (with optional --health check)
- doctor: Diagnose tool and configuration issues
- refresh: Clear tool availability cache
- run: Run a single static analysis tool on a project
- analyze: Run full tool analysis pipeline (coordinate -> execute -> dedupe -> beads)
- install: Show installation instructions for tools
- config: Show tool configuration
"""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from alphaswarm_sol.core.tiers import Tier, DEPENDENCIES, get_tier_dependencies
from alphaswarm_sol.core.availability import AvailabilityChecker, AvailabilityReport
from alphaswarm_sol.core.tool_registry import ToolRegistry, ToolInfo

tools_app = typer.Typer(help="Tool management commands")
console = Console()


def _get_tier_display_name(tier: Tier) -> str:
    """Get human-readable tier name."""
    names = {
        Tier.CORE: "Core (Required)",
        Tier.ENHANCEMENT: "Enhancement (Optional)",
        Tier.OPTIONAL: "Nice-to-Have",
    }
    return names.get(tier, tier.name)


def _get_status_badge(available: bool) -> str:
    """Get status badge for display."""
    if available:
        return "[green]\u2713[/green]"  # Check mark
    return "[yellow]![/yellow]"


@tools_app.command("status")
def status(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show more details"),
) -> None:
    """Show status of all VKG tools and dependencies."""
    checker = AvailabilityChecker()
    reports = checker.check_all()

    if json_output:
        _output_json(checker, reports)
    else:
        _output_rich(checker, reports, verbose)


def _output_json(checker: AvailabilityChecker, reports: list) -> None:
    """Output status as JSON."""
    try:
        effective_tier = checker.get_effective_tier(raise_on_critical=False)
        effective_tier_name = effective_tier.name
    except RuntimeError:
        effective_tier_name = "UNAVAILABLE"

    output = {
        "effective_tier": effective_tier_name,
        "tiers": [r.to_dict() for r in reports],
        "dependencies": {},
    }

    for dep_name, dep in DEPENDENCIES.items():
        output["dependencies"][dep_name] = {
            "tier": dep.tier.name,
            "available": dep.is_available(),
            "version": dep.get_version(),
            "description": dep.description,
            "install_hint": dep.install_hint,
        }

    typer.echo(json.dumps(output, indent=2))


def _output_rich(
    checker: AvailabilityChecker,
    reports: list,
    verbose: bool,
) -> None:
    """Output status with rich formatting."""
    # Build table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Tool", style="cyan", min_width=15)
    table.add_column("Version", min_width=10)
    table.add_column("Status", min_width=15)
    if verbose:
        table.add_column("Description", style="dim")

    missing_tools = []
    counts = {tier: {"total": 0, "available": 0} for tier in Tier}

    for report in sorted(reports, key=lambda r: r.tier.value):
        tier_deps = get_tier_dependencies(report.tier)

        # Add tier section header
        tier_name = _get_tier_display_name(report.tier)
        if verbose:
            table.add_row(
                f"[bold magenta]{tier_name}[/bold magenta]", "", "", ""
            )
        else:
            table.add_row(f"[bold magenta]{tier_name}[/bold magenta]", "", "")

        for dep in tier_deps:
            counts[report.tier]["total"] += 1
            is_available = dep.name in report.available

            if is_available:
                counts[report.tier]["available"] += 1

            version = dep.get_version() if is_available else "-"
            badge = _get_status_badge(is_available)

            if is_available:
                status_text = f"{badge} Ready"
            else:
                status_text = f"{badge} Not installed"
                if dep.install_hint:
                    missing_tools.append((dep.name, dep.install_hint))

            if verbose:
                table.add_row(
                    f"  {dep.name}",
                    version or "-",
                    status_text,
                    dep.description,
                )
            else:
                table.add_row(f"  {dep.name}", version or "-", status_text)

    # Print table
    console.print(Panel(table, title="VKG Tool Status", border_style="blue"))

    # Print summary
    console.print()

    # Effective tier
    try:
        effective = checker.get_effective_tier(raise_on_critical=False)
        tier_color = {
            Tier.CORE: "red",
            Tier.ENHANCEMENT: "yellow",
            Tier.OPTIONAL: "green",
        }.get(effective, "white")
        console.print(
            f"[bold]Effective Tier:[/bold] [{tier_color}]{effective.name}[/{tier_color}]"
        )
    except RuntimeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

    # Tier counts
    counts_str = " | ".join(
        f"{_get_tier_display_name(tier).split()[0]}: "
        f"{counts[tier]['available']}/{counts[tier]['total']}"
        for tier in Tier
    )
    console.print(f"[dim]{counts_str}[/dim]")

    # Missing tools
    if missing_tools:
        console.print()
        console.print("[bold]To install missing tools:[/bold]")
        for name, hint in missing_tools:
            console.print(f"  [cyan]{name}[/cyan]: [dim]{hint}[/dim]")


@tools_app.command("check")
def check(
    tool: str = typer.Argument(..., help="Tool name to check"),
) -> None:
    """Check if a specific tool is available."""
    if tool not in DEPENDENCIES:
        typer.echo(f"Unknown tool: {tool}", err=True)
        typer.echo(f"Available tools: {', '.join(sorted(DEPENDENCIES.keys()))}")
        raise typer.Exit(code=1)

    dep = DEPENDENCIES[tool]
    is_available = dep.is_available()

    if is_available:
        version = dep.get_version()
        typer.echo(f"{tool}: OK (version: {version or 'unknown'})")
    else:
        typer.echo(f"{tool}: NOT AVAILABLE", err=True)
        if dep.install_hint:
            typer.echo(f"Install with: {dep.install_hint}")
        raise typer.Exit(code=1)


@tools_app.command("list")
def list_tools(
    tier_filter: Optional[str] = typer.Option(
        None, "--tier", "-t", help="Filter by tier (core, enhancement, optional)"
    ),
    check_health: bool = typer.Option(
        False, "--health", "-h", help="Check tool health/availability"
    ),
) -> None:
    """List all known tools.

    Use --health to check tool availability and versions.

    Examples:
        uv run alphaswarm tools list
        uv run alphaswarm tools list --health
        uv run alphaswarm tools list --tier core --health
    """
    from alphaswarm_sol.tools.registry import ToolRegistry as StaticToolRegistry

    filter_tier = None
    if tier_filter:
        tier_map = {
            "core": Tier.CORE,
            "enhancement": Tier.ENHANCEMENT,
            "optional": Tier.OPTIONAL,
        }
        filter_tier = tier_map.get(tier_filter.lower())
        if filter_tier is None:
            typer.echo(f"Unknown tier: {tier_filter}", err=True)
            typer.echo(f"Valid tiers: core, enhancement, optional")
            raise typer.Exit(code=1)

    # If health check requested, use static analysis registry
    if check_health:
        static_registry = StaticToolRegistry()
        table = Table(title="VKG Tool Registry")
        table.add_column("Tool", style="cyan")
        table.add_column("Tier", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Version", style="yellow")
        table.add_column("Install", style="dim")

        for name, info in static_registry.TOOL_DEFINITIONS.items():
            health = static_registry.check_tool(name)
            if health.healthy:
                status = "[green]OK"
                version = health.version or "-"
            elif health.installed:
                status = "[yellow]Unhealthy"
                version = health.version or "-"
            else:
                status = "[red]Missing"
                version = "-"

            install_hint = info.install_hint
            if len(install_hint) > 50:
                install_hint = install_hint[:50] + "..."

            table.add_row(
                name,
                str(info.tier),
                status,
                version,
                install_hint
            )

        console.print(table)
        return

    # Original tier-based listing
    for tier in Tier:
        # Skip tiers that don't match filter
        if filter_tier is not None and tier != filter_tier:
            continue

        tier_deps = get_tier_dependencies(tier)
        if not tier_deps:
            continue

        typer.echo(f"\n{_get_tier_display_name(tier)}:")
        for dep in tier_deps:
            typer.echo(f"  - {dep.name}: {dep.description}")


@tools_app.command("doctor")
def doctor(
    fix: bool = typer.Option(False, "--fix", help="Attempt to fix issues"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show details"),
) -> None:
    """Diagnose tool and configuration issues."""
    console.print("[bold]VKG Doctor[/bold]")
    console.print("=" * 40)

    issues = []
    warnings = []

    # Check core dependencies
    checker = AvailabilityChecker()
    reports = checker.check_all()

    core_report = next(r for r in reports if r.tier == Tier.CORE)
    if core_report.degraded:
        for missing in core_report.unavailable:
            dep = DEPENDENCIES.get(missing)
            issues.append({
                "severity": "critical",
                "tool": missing,
                "message": f"Core dependency '{missing}' is not available",
                "fix": dep.install_hint if dep else None,
            })

    # Check enhancement tools
    enhancement_report = next(r for r in reports if r.tier == Tier.ENHANCEMENT)
    if enhancement_report.degraded:
        for missing in enhancement_report.unavailable:
            dep = DEPENDENCIES.get(missing)
            warnings.append({
                "severity": "warning",
                "tool": missing,
                "message": f"Enhancement tool '{missing}' not available",
                "fix": dep.install_hint if dep else None,
            })

    # Report issues
    if issues:
        console.print("\n[bold red]Critical Issues:[/bold red]")
        for issue in issues:
            console.print(f"  [red]\u2717[/red] {issue['message']}")
            if issue["fix"] and verbose:
                console.print(f"    Fix: {issue['fix']}")

    if warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warn in warnings:
            console.print(f"  [yellow]![/yellow] {warn['message']}")
            if warn["fix"] and verbose:
                console.print(f"    Fix: {warn['fix']}")

    if not issues and not warnings:
        console.print("\n[bold green]\u2713 All checks passed[/bold green]")
        raise typer.Exit(code=0)

    # Summary
    console.print()
    if issues:
        console.print(f"[red]{len(issues)} critical issue(s)[/red]")
        console.print("VKG may not function correctly until resolved.")
        raise typer.Exit(code=1)
    elif warnings:
        console.print(f"[yellow]{len(warnings)} warning(s)[/yellow]")
        console.print("VKG will run with reduced functionality.")
        raise typer.Exit(code=0)


@tools_app.command("refresh")
def refresh() -> None:
    """Refresh tool availability cache."""
    registry = ToolRegistry()
    registry.clear_cache()

    checker = AvailabilityChecker()
    checker.clear_cache()

    typer.echo("Tool availability cache cleared.")
    typer.echo("Run 'vkg tools status' to see updated status.")


# =============================================================================
# Static Analysis Tool Integration Commands (Phase 5.1)
# =============================================================================


@tools_app.command("run")
def run_tool(
    tool: str = typer.Argument(..., help="Tool name to run (slither, aderyn, mythril, etc.)"),
    project_path: Path = typer.Argument(..., help="Path to Solidity project"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file for results"),
    output_format: str = typer.Option("json", "--format", "-f", help="Output format (json, sarif)"),
    timeout: int = typer.Option(120, "--timeout", "-t", help="Timeout in seconds"),
) -> None:
    """Run a single static analysis tool on a project.

    Executes a specified tool and returns findings in VKG format.
    Tools must be installed separately.

    Examples:
        uv run alphaswarm tools run slither ./contracts
        uv run alphaswarm tools run aderyn ./src -o findings.json
        uv run alphaswarm tools run mythril ./contracts --timeout 300
    """
    from alphaswarm_sol.tools.executor import ToolExecutor
    from alphaswarm_sol.tools.config import get_optimal_config
    from alphaswarm_sol.tools.registry import ToolRegistry as StaticToolRegistry

    # Check tool is available
    registry = StaticToolRegistry()
    if not registry.check_tool(tool).healthy:
        health = registry.check_tool(tool)
        console.print(f"[red]Tool not available: {tool}[/red]")
        if health.error:
            console.print(f"[yellow]Error: {health.error}[/yellow]")
        hint = registry.get_install_hint(tool)
        console.print(f"[yellow]Install with: {hint}[/yellow]")
        raise typer.Exit(code=1)

    # Verify project path exists
    if not project_path.exists():
        console.print(f"[red]Project path not found: {project_path}[/red]")
        raise typer.Exit(code=1)

    # Get config and run
    config = get_optimal_config(tool)
    config.timeout = timeout

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        progress.add_task(f"Running {tool}...", total=None)
        executor = ToolExecutor()
        result = executor.execute_tool(tool, config, project_path)

    if result.success:
        console.print(f"[green]Tool completed: {len(result.findings)} findings in {result.execution_time:.1f}s[/green]")

        if output:
            if output_format == "sarif":
                from alphaswarm_sol.tools.adapters.sarif import SARIFAdapter
                adapter = SARIFAdapter()
                sarif = adapter.to_sarif(result.findings, tool, "latest")
                output.write_text(json.dumps(sarif, indent=2))
            else:
                output.write_text(json.dumps([f.to_dict() for f in result.findings], indent=2))
            console.print(f"[green]Output written to {output}[/green]")
        else:
            # Print summary
            for finding in result.findings[:5]:
                sev = finding.severity.upper()
                title = finding.title[:60] if finding.title else finding.rule_id
                console.print(f"  - [bold]{sev}[/bold]: {title}")
            if len(result.findings) > 5:
                console.print(f"  ... and {len(result.findings) - 5} more")
    else:
        console.print(f"[red]Tool failed: {result.error}[/red]")
        raise typer.Exit(code=1)


@tools_app.command("analyze")
def analyze_project(
    project_path: Path = typer.Argument(..., help="Path to Solidity project"),
    tools_list: Optional[str] = typer.Option(None, "--tools", "-t", help="Comma-separated tools to run"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory for results"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip result cache"),
    create_beads: bool = typer.Option(True, "--beads/--no-beads", help="Create beads from findings"),
) -> None:
    """Run full tool analysis pipeline on a project.

    Coordinates tool selection based on project characteristics,
    executes tools in parallel, deduplicates findings, and
    optionally creates investigation beads.

    Pipeline: analyze -> coordinate -> execute -> deduplicate -> beads

    Examples:
        uv run alphaswarm tools analyze ./contracts
        uv run alphaswarm tools analyze ./src --tools slither,aderyn
        uv run alphaswarm tools analyze ./contracts -o ./results --beads
    """
    from alphaswarm_sol.tools.coordinator import ToolCoordinator
    from alphaswarm_sol.tools.executor import ToolExecutor
    from alphaswarm_sol.orchestration.dedup import SemanticDeduplicator
    from alphaswarm_sol.beads.from_tools import create_beads_from_tools

    # Verify project path
    if not project_path.exists():
        console.print(f"[red]Project path not found: {project_path}[/red]")
        raise typer.Exit(code=1)

    # Analyze project and create strategy
    console.print("[bold]Analyzing project...[/bold]")
    coordinator = ToolCoordinator()
    analysis = coordinator.analyze_project(project_path)
    console.print(f"  Contracts: {analysis.contract_count}")
    console.print(f"  Lines: {analysis.total_lines}")
    console.print(f"  Complexity: {analysis.complexity_score}/10")

    # Get strategy
    if tools_list:
        tool_names = [t.strip() for t in tools_list.split(",")]
        strategy = coordinator.create_strategy(analysis, tool_names)
    else:
        strategy = coordinator.create_strategy(analysis, None)

    console.print(f"\n[bold]Strategy: {len(strategy.tools_to_run)} tools[/bold]")
    console.print(f"  {coordinator.explain_strategy(strategy)[:200]}...")

    if not strategy.tools_to_run:
        console.print("[yellow]No tools available to run. Install tools with 'uv run alphaswarm tools install'[/yellow]")
        raise typer.Exit(code=1)

    # Execute tools
    console.print("\n[bold]Running tools...[/bold]")
    executor = ToolExecutor()
    results = executor.execute_strategy(strategy, project_path, use_cache=not no_cache)

    # Report results
    total_findings = sum(len(r.findings) for r in results)
    console.print(f"\n[bold]Results: {total_findings} raw findings[/bold]")
    for result in results:
        status = "[green]OK" if result.success else "[red]FAIL"
        cache_str = "[dim](cached)[/dim]" if result.from_cache else ""
        console.print(f"  {result.tool}: {len(result.findings)} findings {status} {cache_str}")

    # Deduplicate
    console.print("\n[bold]Deduplicating...[/bold]")
    all_findings = []
    for result in results:
        all_findings.extend(result.findings)

    deduplicator = SemanticDeduplicator()
    deduped, stats = deduplicator.deduplicate(all_findings)
    console.print(f"  {stats.input_count} -> {stats.output_count} ({stats.reduction_percent:.0f}% reduction)")

    # Create beads if requested
    if create_beads and deduped:
        console.print("\n[bold]Creating beads...[/bold]")
        # Extract representative findings from deduplicated groups
        representative_findings = []
        for d in deduped:
            if d.findings:
                # Use first finding as representative
                from alphaswarm_sol.tools.adapters.sarif import VKGFinding
                first = d.findings[0]
                finding = VKGFinding(
                    source=first.get("source", "unknown"),
                    rule_id=first.get("rule_id", "unknown"),
                    title=first.get("title", ""),
                    description=first.get("description", ""),
                    severity=d.severity,
                    category=d.category,
                    file=d.file,
                    line=d.line,
                    function=d.function,
                    confidence=d.confidence,
                    vkg_pattern=d.vkg_pattern,
                )
                representative_findings.append(finding)

        beads = create_beads_from_tools(representative_findings, project_path)
        console.print(f"  {len(beads)} beads created (confidence=uncertain)")

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            beads_file = output_dir / "tool_beads.yaml"
            import yaml
            with open(beads_file, "w") as f:
                yaml.dump([b.to_dict() for b in beads], f, default_flow_style=False)
            console.print(f"  [green]Beads saved to {beads_file}[/green]")

    # Save findings if output specified
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        findings_file = output_dir / "findings.json"
        with open(findings_file, "w") as f:
            json.dump([d.to_dict() for d in deduped], f, indent=2)
        console.print(f"[green]Findings saved to {findings_file}[/green]")

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Tools run: {len([r for r in results if r.success])}/{len(results)}")
    console.print(f"  Raw findings: {total_findings}")
    console.print(f"  Deduplicated: {len(deduped)}")
    if create_beads and deduped:
        console.print(f"  Beads created: {len(beads)}")


@tools_app.command("install")
def install_tools(
    tools_list: Optional[str] = typer.Option(None, "--tools", "-t", help="Comma-separated tools to install"),
    tier: Optional[int] = typer.Option(None, "--tier", help="Install all tools of this tier (0, 1, or 2)"),
    all_tools: bool = typer.Option(False, "--all", "-a", help="Show instructions for all tools"),
) -> None:
    """Show installation instructions for analysis tools.

    This command displays installation commands for static analysis tools.
    Tools must be installed separately using pip, cargo, or other package managers.

    Tiers:
      0 = Core (required): slither
      1 = Recommended: aderyn, mythril, echidna, foundry, semgrep
      2 = Optional: halmos, medusa, solc, crytic-compile

    Examples:
        uv run alphaswarm tools install
        uv run alphaswarm tools install --tier 0
        uv run alphaswarm tools install --tools slither,aderyn
        uv run alphaswarm tools install --all
    """
    from alphaswarm_sol.tools.registry import ToolRegistry as StaticToolRegistry, ToolTier

    registry = StaticToolRegistry()

    console.print("[bold]Tool Installation Guide[/bold]")
    console.print("=" * 50)

    # Determine which tools to show
    if tools_list:
        tool_names = [t.strip() for t in tools_list.split(",")]
    elif tier is not None:
        tool_tier = ToolTier(tier)
        tool_names = registry.get_tools_by_tier(tool_tier)
    elif all_tools:
        tool_names = list(registry.TOOL_DEFINITIONS.keys())
    else:
        # Show missing tools
        tool_names = registry.get_missing_tools()
        if not tool_names:
            console.print("\n[green]All tools are installed![/green]")
            console.print("Run 'uv run alphaswarm tools list --health' to see status.")
            return

    console.print(f"\n[bold]Installation commands for {len(tool_names)} tools:[/bold]\n")

    for name in tool_names:
        info = registry.TOOL_DEFINITIONS.get(name)
        if info:
            health = registry.check_tool(name)
            status = "[green](installed)[/green]" if health.healthy else "[yellow](missing)[/yellow]"
            console.print(f"[cyan]{name}[/cyan] {status}")
            console.print(f"  {info.description}")
            console.print(f"  [dim]Install:[/dim] {info.install_hint}")
            console.print(f"  [dim]Tier:[/dim] {info.tier.name}")
            console.print()

    console.print("=" * 50)
    console.print("[dim]After installing, run 'uv run alphaswarm tools list --health' to verify.[/dim]")


@tools_app.command("config")
def show_config(
    tool: Optional[str] = typer.Argument(None, help="Tool name (omit for all tools)"),
    project_path: Optional[Path] = typer.Option(None, "--project", "-p", help="Project path for overrides"),
    show_defaults: bool = typer.Option(False, "--defaults", "-d", help="Show VKG optimal defaults"),
) -> None:
    """Show tool configuration.

    Displays the configuration for a tool, including timeouts,
    excluded paths, and excluded detectors.

    Examples:
        uv run alphaswarm tools config slither
        uv run alphaswarm tools config --defaults
        uv run alphaswarm tools config slither --project ./myproject
    """
    from alphaswarm_sol.tools.config import get_optimal_config, load_tool_config, VKG_OPTIMAL_CONFIGS
    import yaml

    if show_defaults:
        console.print("[bold]VKG Optimal Configurations[/bold]")
        console.print("=" * 50)
        console.print(yaml.dump(VKG_OPTIMAL_CONFIGS, default_flow_style=False))
        return

    if tool:
        # Show config for specific tool
        if project_path:
            config = load_tool_config(tool, project_path)
            console.print(f"[bold]Configuration for {tool}[/bold] (with project overrides)")
        else:
            config = get_optimal_config(tool)
            console.print(f"[bold]Configuration for {tool}[/bold] (VKG defaults)")

        console.print("=" * 50)
        console.print(yaml.dump(config.to_dict(), default_flow_style=False))
    else:
        # Show all tool configs
        console.print("[bold]Tool Configurations[/bold]")
        console.print("=" * 50)
        console.print()
        console.print("Use 'uv run alphaswarm tools config <tool>' for specific tool config.")
        console.print("Use 'uv run alphaswarm tools config --defaults' to see all defaults.")
        console.print()

        # Brief summary
        table = Table(title="Available Tools")
        table.add_column("Tool", style="cyan")
        table.add_column("Timeout", style="yellow")
        table.add_column("Exclude Paths")

        for tool_name, defaults in VKG_OPTIMAL_CONFIGS.items():
            timeout = str(defaults.get("timeout", 120))
            exclude = ", ".join(defaults.get("exclude_paths", [])[:3])
            if len(defaults.get("exclude_paths", [])) > 3:
                exclude += "..."
            table.add_row(tool_name, timeout, exclude)

        console.print(table)
