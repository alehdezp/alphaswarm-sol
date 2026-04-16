"""Cost dashboard rendering for pools.

This module provides dashboard output for cost tracking:
- Compact markdown summaries
- Per-pool and multi-pool views
- Budget status visualization
- Agent/bead cost breakdown

Integrates with:
- alphaswarm_sol.metrics.cost_ledger: Pool cost tracking
- alphaswarm_sol.orchestration.pool: Pool management

Usage:
    from alphaswarm_sol.report.cost_dashboard import render_cost_dashboard
    from alphaswarm_sol.metrics.cost_ledger import CostLedger

    ledger = CostLedger(pool_id="pool-abc123")
    # ... record usage ...

    # Render dashboard
    dashboard = render_cost_dashboard(ledger)
    print(dashboard)

    # Or render multiple pools
    multi_dashboard = render_multi_pool_dashboard([ledger1, ledger2])
"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..metrics.cost_ledger import CostLedger, PoolCostSummary


def render_cost_dashboard(
    ledger: "CostLedger",
    include_entries: bool = False,
    max_entries: int = 10,
) -> str:
    """Render a cost dashboard for a single pool.

    Args:
        ledger: CostLedger to render
        include_entries: Whether to include recent entries
        max_entries: Maximum entries to show if include_entries is True

    Returns:
        Markdown-formatted dashboard string
    """
    summary = ledger.summary()
    return _render_summary(summary, include_entries, ledger, max_entries)


def render_summary_dashboard(summary: "PoolCostSummary") -> str:
    """Render a cost dashboard from a summary (no entry details).

    Args:
        summary: PoolCostSummary to render

    Returns:
        Markdown-formatted dashboard string
    """
    return _render_summary(summary, include_entries=False)


def _render_summary(
    summary: "PoolCostSummary",
    include_entries: bool = False,
    ledger: Optional["CostLedger"] = None,
    max_entries: int = 10,
) -> str:
    """Internal helper to render summary."""
    lines: List[str] = []

    # Header
    lines.append(f"## Cost Dashboard: {summary.pool_id}")
    lines.append("")

    # Budget status bar
    if summary.budget_max_usd is not None:
        budget_bar = _render_budget_bar(
            summary.total_cost_usd,
            summary.budget_max_usd,
        )
        lines.append(f"**Budget:** {budget_bar}")
        lines.append("")

    # Summary metrics table
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Cost | ${summary.total_cost_usd:.4f} |")
    lines.append(f"| Total Tokens | {summary.total_tokens:,} |")
    lines.append(f"| Input Tokens | {summary.total_input_tokens:,} |")
    lines.append(f"| Output Tokens | {summary.total_output_tokens:,} |")
    lines.append(f"| Requests | {summary.total_requests} |")

    if summary.total_requests > 0:
        lines.append(f"| Avg Cost/Request | ${summary.avg_cost_per_request:.4f} |")

    if summary.budget_max_usd is not None:
        lines.append(f"| Budget Limit | ${summary.budget_max_usd:.2f} |")
        if summary.budget_remaining_usd is not None:
            lines.append(f"| Budget Remaining | ${summary.budget_remaining_usd:.2f} |")
        if summary.budget_utilization_pct is not None:
            lines.append(f"| Budget Used | {summary.budget_utilization_pct:.1f}% |")

    lines.append("")

    # Cost by agent
    if summary.cost_by_agent:
        lines.append("### Cost by Agent")
        lines.append("")
        lines.append("| Agent | Cost | % of Total |")
        lines.append("|-------|------|------------|")
        for agent, cost in sorted(
            summary.cost_by_agent.items(), key=lambda x: -x[1]
        ):
            pct = (cost / summary.total_cost_usd * 100) if summary.total_cost_usd > 0 else 0
            lines.append(f"| {agent} | ${cost:.4f} | {pct:.1f}% |")
        lines.append("")

    # Cost by model
    if summary.cost_by_model:
        lines.append("### Cost by Model")
        lines.append("")
        lines.append("| Model | Cost | % of Total |")
        lines.append("|-------|------|------------|")
        for model, cost in sorted(
            summary.cost_by_model.items(), key=lambda x: -x[1]
        ):
            pct = (cost / summary.total_cost_usd * 100) if summary.total_cost_usd > 0 else 0
            lines.append(f"| {model} | ${cost:.4f} | {pct:.1f}% |")
        lines.append("")

    # Cost by bead (if any)
    if summary.cost_by_bead:
        lines.append("### Cost by Bead")
        lines.append("")
        lines.append("| Bead ID | Cost | % of Total |")
        lines.append("|---------|------|------------|")
        for bead, cost in sorted(
            summary.cost_by_bead.items(), key=lambda x: -x[1]
        )[:10]:  # Limit to top 10
            pct = (cost / summary.total_cost_usd * 100) if summary.total_cost_usd > 0 else 0
            lines.append(f"| {bead} | ${cost:.4f} | {pct:.1f}% |")
        if len(summary.cost_by_bead) > 10:
            lines.append(f"| ... | ({len(summary.cost_by_bead) - 10} more) | |")
        lines.append("")

    # Warnings
    if summary.warnings:
        lines.append("### Warnings")
        lines.append("")
        for warning in summary.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    # Recent entries (if requested and ledger provided)
    if include_entries and ledger is not None:
        entries = ledger.get_entries()
        if entries:
            lines.append("### Recent Entries")
            lines.append("")
            lines.append("| Time | Agent | Model | Tokens | Cost |")
            lines.append("|------|-------|-------|--------|------|")
            for entry in entries[-max_entries:]:
                time_str = entry.timestamp.strftime("%H:%M:%S")
                tokens = entry.input_tokens + entry.output_tokens
                lines.append(
                    f"| {time_str} | {entry.agent_type} | {entry.model} | "
                    f"{tokens:,} | ${entry.cost_usd:.4f} |"
                )
            if len(entries) > max_entries:
                lines.append(f"| ... | ({len(entries) - max_entries} more) | | | |")
            lines.append("")

    return "\n".join(lines)


def _render_budget_bar(spent: float, budget: float, width: int = 20) -> str:
    """Render a visual budget bar.

    Args:
        spent: Amount spent
        budget: Budget limit
        width: Width of the bar in characters

    Returns:
        String representation like "[========..] 80% ($8.00/$10.00)"
    """
    if budget <= 0:
        return "No budget set"

    pct = min(100.0, (spent / budget) * 100)
    filled = int((pct / 100) * width)
    empty = width - filled

    # Choose status indicator
    if pct >= 100:
        status = "EXCEEDED"
        bar_char = "X"
    elif pct >= 80:
        status = "WARNING"
        bar_char = "!"
    else:
        status = "OK"
        bar_char = "="

    bar = f"[{bar_char * filled}{'.' * empty}]"
    return f"{bar} {pct:.1f}% (${spent:.2f}/${budget:.2f}) {status}"


def render_multi_pool_dashboard(ledgers: List["CostLedger"]) -> str:
    """Render a dashboard for multiple pools.

    Args:
        ledgers: List of CostLedger objects to render

    Returns:
        Markdown-formatted multi-pool dashboard
    """
    if not ledgers:
        return "## Cost Dashboard\n\nNo pools tracked."

    lines: List[str] = []
    lines.append("## Cost Dashboard: All Pools")
    lines.append("")

    # Aggregate stats
    total_cost = sum(l.total_cost for l in ledgers)
    total_tokens = sum(l.total_tokens for l in ledgers)
    total_requests = sum(len(l.get_entries()) for l in ledgers)

    lines.append("### Aggregate Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Pools | {len(ledgers)} |")
    lines.append(f"| Total Cost | ${total_cost:.4f} |")
    lines.append(f"| Total Tokens | {total_tokens:,} |")
    lines.append(f"| Total Requests | {total_requests} |")
    lines.append("")

    # Per-pool summary table
    lines.append("### Per-Pool Summary")
    lines.append("")
    lines.append("| Pool ID | Cost | Tokens | Requests | Budget Status |")
    lines.append("|---------|------|--------|----------|---------------|")

    for ledger in sorted(ledgers, key=lambda l: -l.total_cost):
        summary = ledger.summary()
        budget_status = "N/A"
        if summary.budget_max_usd is not None:
            pct = summary.budget_utilization_pct or 0
            if pct >= 100:
                budget_status = f"EXCEEDED ({pct:.0f}%)"
            elif pct >= 80:
                budget_status = f"WARNING ({pct:.0f}%)"
            else:
                budget_status = f"OK ({pct:.0f}%)"

        lines.append(
            f"| {ledger.pool_id} | ${summary.total_cost_usd:.4f} | "
            f"{summary.total_tokens:,} | {summary.total_requests} | "
            f"{budget_status} |"
        )

    lines.append("")

    return "\n".join(lines)


def render_compact_summary(summary: "PoolCostSummary") -> str:
    """Render a one-line compact summary for CLI output.

    Args:
        summary: PoolCostSummary to render

    Returns:
        Single-line summary string
    """
    budget_part = ""
    if summary.budget_max_usd is not None:
        pct = summary.budget_utilization_pct or 0
        budget_part = f" | Budget: {pct:.0f}%"

    return (
        f"{summary.pool_id}: ${summary.total_cost_usd:.4f} | "
        f"{summary.total_tokens:,} tokens | "
        f"{summary.total_requests} requests{budget_part}"
    )


def render_toon_summary(summary: "PoolCostSummary") -> str:
    """Render summary in TOON format for token-efficient output.

    Args:
        summary: PoolCostSummary to render

    Returns:
        TOON-formatted summary
    """
    # TOON header
    lines: List[str] = []
    lines.append("---")
    lines.append(f"pool: {summary.pool_id}")
    lines.append(f"cost_usd: {summary.total_cost_usd:.4f}")
    lines.append(f"tokens: {summary.total_tokens}")
    lines.append(f"requests: {summary.total_requests}")

    if summary.budget_max_usd is not None:
        lines.append(f"budget_max: {summary.budget_max_usd:.2f}")
        lines.append(f"budget_pct: {summary.budget_utilization_pct or 0:.1f}")

    # Agent costs as compact array
    if summary.cost_by_agent:
        agent_parts = [f"{k}:{v:.4f}" for k, v in summary.cost_by_agent.items()]
        lines.append(f"by_agent: [{', '.join(agent_parts)}]")

    lines.append("---")

    return "\n".join(lines)


__all__ = [
    "render_cost_dashboard",
    "render_summary_dashboard",
    "render_multi_pool_dashboard",
    "render_compact_summary",
    "render_toon_summary",
]
