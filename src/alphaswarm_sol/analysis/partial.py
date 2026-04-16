"""
Partial Result Handling

Utilities for working with incomplete analysis results.
"""

from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .results import AggregatedResults, SourceResult


def format_partial_results(results: AggregatedResults) -> str:
    """Format results with partial indicators as plain text."""
    lines = []

    if results.complete:
        lines.append("Analysis Results (Complete)")
    else:
        failed_count = len(results.incomplete_sources)
        lines.append(f"Analysis Results (Partial - {failed_count} source(s) failed)")

    lines.append("")

    for source in results.sources:
        status = "[OK]" if source.complete else "[!]"
        finding_count = len(source.findings)

        if source.complete:
            status_text = f"Complete ({finding_count} findings)"
        else:
            status_text = source.error or "Failed"
            if finding_count > 0:
                status_text += f" ({finding_count} partial findings)"

        lines.append(f"  {source.source}: {status} {status_text}")
        if source.runtime_ms > 0:
            lines.append(f"    Runtime: {source.runtime_ms}ms")

    lines.append("")
    lines.append(f"Total findings: {results.total_findings}")

    if not results.complete:
        lines.append("")
        lines.append("Note: Some sources failed. Results may be incomplete.")

        retry_sources = [s for s in results.sources if not s.complete and s.retry_command]
        if retry_sources:
            lines.append("")
            lines.append("Retry commands:")
            for source in retry_sources:
                lines.append(f"  {source.source}: {source.retry_command}")

    return "\n".join(lines)


def render_partial_results_rich(
    results: AggregatedResults,
    console: Console,
    show_findings: bool = False,
) -> None:
    """Render results with rich formatting."""
    # Status table
    table = Table(title="Analysis Results", show_header=True)
    table.add_column("Source", style="cyan")
    table.add_column("Status")
    table.add_column("Findings", justify="right")
    table.add_column("Runtime", justify="right", style="dim")
    table.add_column("Details", style="dim")

    for source in results.sources:
        if source.complete:
            status = "[green]OK[/green]"
        else:
            status = "[yellow]FAILED[/yellow]"

        runtime = f"{source.runtime_ms}ms" if source.runtime_ms > 0 else "-"

        table.add_row(
            source.source,
            status,
            str(len(source.findings)),
            runtime,
            source.error or "",
        )

    console.print(table)

    # Summary
    console.print()
    if results.complete:
        console.print(
            f"[green]Complete:[/green] {results.total_findings} findings from "
            f"{results.total_sources} source(s)"
        )
    else:
        console.print(
            f"[yellow]Partial:[/yellow] {results.total_findings} findings from "
            f"{len(results.successful_sources)}/{results.total_sources} source(s)"
        )
        console.print("[yellow]Some sources failed. Results may be incomplete.[/yellow]")

        # Retry hints
        retry_sources = [s for s in results.sources if not s.complete and s.retry_command]
        if retry_sources:
            console.print()
            console.print("[bold]Retry commands:[/bold]")
            for source in retry_sources:
                console.print(f"  [dim]{source.retry_command}[/dim]")

    # Optionally show findings
    if show_findings and results.total_findings > 0:
        console.print()
        console.print("[bold]Findings:[/bold]")
        for finding in results.get_all_findings()[:10]:  # Limit to 10
            source = finding.get("_source", "unknown")
            title = finding.get("title", finding.get("id", "Unknown"))
            console.print(f"  [{source}] {title}")
        if results.total_findings > 10:
            console.print(f"  ... and {results.total_findings - 10} more")


def merge_partial_results(
    existing: AggregatedResults,
    new: AggregatedResults,
) -> AggregatedResults:
    """
    Merge new results into existing, replacing failed sources.

    Use case: User retries a failed source, merge new results.

    Priority: New results take precedence for matching sources.
    """
    merged = AggregatedResults()

    # Track which sources we've seen in new results
    new_sources = {s.source for s in new.sources}

    # Add all new results first (they take priority)
    for source in new.sources:
        merged.add_result(source)

    # Add existing results for sources not in new
    for source in existing.sources:
        if source.source not in new_sources:
            merged.add_result(source)

    return merged


def combine_results(*result_sets: AggregatedResults) -> AggregatedResults:
    """Combine multiple result sets into one.

    Sources from later sets override sources from earlier sets.
    """
    combined = AggregatedResults()

    seen_sources = {}  # source_name -> SourceResult

    for results in result_sets:
        for source in results.sources:
            seen_sources[source.source] = source

    for source in seen_sources.values():
        combined.add_result(source)

    return combined


class PartialResultHandler:
    """Handles partial result scenarios."""

    def __init__(
        self,
        console: Optional[Console] = None,
        auto_suggest_retry: bool = True,
    ):
        self.console = console or Console()
        self.auto_suggest_retry = auto_suggest_retry

    def handle(
        self,
        results: AggregatedResults,
        show_findings: bool = False,
    ) -> bool:
        """
        Handle partial results.

        Returns True if all results complete, False if partial.
        """
        render_partial_results_rich(results, self.console, show_findings=show_findings)

        if not results.complete and self.auto_suggest_retry:
            self._offer_retry(results)

        return results.complete

    def _offer_retry(self, results: AggregatedResults) -> None:
        """Offer retry options for failed sources."""
        failed = [s for s in results.sources if not s.complete and s.retry_command]

        if not failed:
            return

        self.console.print()
        panel_content = []
        for source in failed:
            panel_content.append(f"[cyan]{source.source}:[/cyan] {source.retry_command}")

        if panel_content:
            self.console.print(
                Panel(
                    "\n".join(panel_content),
                    title="[yellow]Retry Options[/yellow]",
                    border_style="yellow",
                )
            )

    def format_summary(self, results: AggregatedResults) -> str:
        """Get a one-line summary of results."""
        if results.complete:
            return f"Complete: {results.total_findings} findings"
        else:
            return (
                f"Partial: {results.total_findings} findings "
                f"({len(results.successful_sources)}/{results.total_sources} sources)"
            )

    def should_warn(self, results: AggregatedResults) -> bool:
        """Check if results warrant a warning."""
        # Warn if any required sources failed
        return not results.complete

    def get_recommendations(self, results: AggregatedResults) -> List[str]:
        """Get recommendations for improving results."""
        recommendations = []

        for source in results.sources:
            if not source.complete:
                if "timeout" in (source.error or "").lower():
                    recommendations.append(
                        f"Increase timeout for {source.source} or check for infinite loops"
                    )
                elif "not found" in (source.error or "").lower():
                    recommendations.append(
                        f"Install {source.source} or check PATH configuration"
                    )
                elif source.retry_command:
                    recommendations.append(f"Retry {source.source}: {source.retry_command}")

        return recommendations
