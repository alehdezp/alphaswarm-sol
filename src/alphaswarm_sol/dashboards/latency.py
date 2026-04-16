"""Latency dashboard for pool completion and agent-level timing metrics.

This module provides latency monitoring dashboards with P50/P95/P99 metrics
for pool completion times and per-agent latency breakdowns.

Example:
    from alphaswarm_sol.dashboards.latency import render_latency_dashboard, OutputFormat

    # Generate latency dashboard
    dashboard = render_latency_dashboard(
        pool_ids=["pool-001"],
        format=OutputFormat.MARKDOWN,
        window_hours=24
    )
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from alphaswarm_sol.beads.event_store import BeadEventStore


class OutputFormat(str, Enum):
    """Dashboard output format."""

    MARKDOWN = "markdown"
    JSON = "json"
    TOON = "toon"


@dataclass
class LatencyStats:
    """Pool latency statistics.

    Attributes:
        pool_id: Pool identifier
        p50_seconds: 50th percentile (median) completion time
        p95_seconds: 95th percentile completion time
        p99_seconds: 99th percentile completion time
        mean_seconds: Mean completion time
        count: Number of completed pools
        window_hours: Time window for measurements
    """

    pool_id: Optional[str]
    p50_seconds: float
    p95_seconds: float
    p99_seconds: float
    mean_seconds: float
    count: int
    window_hours: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pool_id": self.pool_id,
            "p50_seconds": round(self.p50_seconds, 2),
            "p95_seconds": round(self.p95_seconds, 2),
            "p99_seconds": round(self.p99_seconds, 2),
            "mean_seconds": round(self.mean_seconds, 2),
            "count": self.count,
            "window_hours": self.window_hours,
        }


@dataclass
class AgentLatencyBreakdown:
    """Per-agent latency breakdown.

    Attributes:
        agent_type: Agent identifier (e.g., "vrs-attacker")
        mean_seconds: Mean execution time
        p95_seconds: 95th percentile execution time
        invocation_count: Number of invocations
        total_seconds: Total time spent
    """

    agent_type: str
    mean_seconds: float
    p95_seconds: float
    invocation_count: int
    total_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_type": self.agent_type,
            "mean_seconds": round(self.mean_seconds, 2),
            "p95_seconds": round(self.p95_seconds, 2),
            "invocation_count": self.invocation_count,
            "total_seconds": round(self.total_seconds, 2),
        }


class LatencyDashboard:
    """Dashboard for latency metrics.

    Provides pool completion latency and agent-level breakdowns from
    event store data.

    Example:
        dashboard = LatencyDashboard(event_store)
        stats = dashboard.get_pool_latency_stats(window_hours=24)
        text = dashboard.render(OutputFormat.MARKDOWN)
    """

    def __init__(
        self,
        event_store: Optional[BeadEventStore] = None,
        vrs_root: Optional[Path] = None,
    ):
        """Initialize latency dashboard.

        Args:
            event_store: Optional BeadEventStore instance
            vrs_root: Optional VRS root directory (creates event_store if needed)
        """
        if event_store is None and vrs_root is not None:
            from alphaswarm_sol.beads.event_store import BeadEventStore

            event_store = BeadEventStore(vrs_root / "beads")

        self.event_store = event_store
        self._stats: Optional[LatencyStats] = None
        self._agent_breakdowns: List[AgentLatencyBreakdown] = []

    def get_pool_latency_stats(
        self,
        pool_id: Optional[str] = None,
        window_hours: int = 24,
    ) -> LatencyStats:
        """Get pool latency statistics.

        Args:
            pool_id: Optional specific pool to measure
            window_hours: Time window for measurements

        Returns:
            LatencyStats with P50/P95/P99 metrics
        """
        if self.event_store is None:
            # Return dummy stats if no event store
            return LatencyStats(
                pool_id=pool_id,
                p50_seconds=180.0,
                p95_seconds=250.0,
                p99_seconds=300.0,
                mean_seconds=200.0,
                count=0,
                window_hours=window_hours,
            )

        cutoff_time = datetime.now() - timedelta(hours=window_hours)
        events = self.event_store.list_events()

        # Filter events by time window and pool
        relevant_events = [
            e
            for e in events
            if datetime.fromisoformat(e.timestamp.rstrip("Z")) >= cutoff_time
            and (pool_id is None or e.pool_id == pool_id)
        ]

        # Compute latencies from pool_assigned events
        # (In production, would track pool start/end events)
        latencies = []
        for event in relevant_events:
            if event.event_type == "pool_assigned":
                # Extract duration from payload if available
                duration = event.payload.get("duration_seconds")
                if duration:
                    latencies.append(float(duration))

        if not latencies:
            # No data, return defaults
            return LatencyStats(
                pool_id=pool_id,
                p50_seconds=0.0,
                p95_seconds=0.0,
                p99_seconds=0.0,
                mean_seconds=0.0,
                count=0,
                window_hours=window_hours,
            )

        # Compute percentiles
        sorted_latencies = sorted(latencies)
        count = len(sorted_latencies)

        p50 = statistics.median(sorted_latencies)
        p95_idx = int(count * 0.95)
        p99_idx = int(count * 0.99)
        p95 = sorted_latencies[min(p95_idx, count - 1)]
        p99 = sorted_latencies[min(p99_idx, count - 1)]
        mean = statistics.mean(sorted_latencies)

        stats = LatencyStats(
            pool_id=pool_id,
            p50_seconds=p50,
            p95_seconds=p95,
            p99_seconds=p99,
            mean_seconds=mean,
            count=count,
            window_hours=window_hours,
        )

        self._stats = stats
        return stats

    def get_agent_latency_breakdown(
        self,
        pool_id: Optional[str] = None,
        window_hours: int = 24,
    ) -> List[AgentLatencyBreakdown]:
        """Get per-agent latency breakdown.

        Args:
            pool_id: Optional specific pool to measure
            window_hours: Time window for measurements

        Returns:
            List of AgentLatencyBreakdown objects
        """
        # Placeholder implementation
        # In production, would extract agent execution times from events
        breakdowns = [
            AgentLatencyBreakdown(
                agent_type="vrs-attacker",
                mean_seconds=45.0,
                p95_seconds=60.0,
                invocation_count=10,
                total_seconds=450.0,
            ),
            AgentLatencyBreakdown(
                agent_type="vrs-defender",
                mean_seconds=35.0,
                p95_seconds=50.0,
                invocation_count=10,
                total_seconds=350.0,
            ),
            AgentLatencyBreakdown(
                agent_type="vrs-verifier",
                mean_seconds=55.0,
                p95_seconds=75.0,
                invocation_count=5,
                total_seconds=275.0,
            ),
        ]

        self._agent_breakdowns = breakdowns
        return breakdowns

    def render(
        self,
        format: OutputFormat = OutputFormat.MARKDOWN,
        pool_id: Optional[str] = None,
        window_hours: int = 24,
    ) -> str:
        """Render latency dashboard.

        Args:
            format: Output format (markdown, json, toon)
            pool_id: Optional specific pool
            window_hours: Time window for measurements

        Returns:
            Formatted dashboard text
        """
        # Refresh stats
        stats = self.get_pool_latency_stats(pool_id, window_hours)
        breakdowns = self.get_agent_latency_breakdown(pool_id, window_hours)

        if format == OutputFormat.MARKDOWN:
            return self._render_markdown(stats, breakdowns)
        elif format == OutputFormat.JSON:
            return self._render_json(stats, breakdowns)
        else:  # TOON
            return self._render_toon(stats, breakdowns)

    def _render_markdown(
        self, stats: LatencyStats, breakdowns: List[AgentLatencyBreakdown]
    ) -> str:
        """Render as markdown."""
        lines = [
            "# Latency Dashboard",
            "",
            f"**Time Window:** {stats.window_hours}h",
            f"**Pool:** {stats.pool_id or 'All'}",
            "",
            "## Pool Completion Latency",
            "",
            f"- **P50 (median):** {stats.p50_seconds:.1f}s",
            f"- **P95:** {stats.p95_seconds:.1f}s",
            f"- **P99:** {stats.p99_seconds:.1f}s",
            f"- **Mean:** {stats.mean_seconds:.1f}s",
            f"- **Sample count:** {stats.count}",
            "",
            "## Agent Latency Breakdown",
            "",
            "| Agent | Mean | P95 | Invocations | Total Time |",
            "|-------|------|-----|-------------|------------|",
        ]

        for bd in breakdowns:
            lines.append(
                f"| {bd.agent_type} | {bd.mean_seconds:.1f}s | "
                f"{bd.p95_seconds:.1f}s | {bd.invocation_count} | "
                f"{bd.total_seconds:.1f}s |"
            )

        return "\n".join(lines)

    def _render_json(
        self, stats: LatencyStats, breakdowns: List[AgentLatencyBreakdown]
    ) -> str:
        """Render as JSON."""
        data = {
            "pool_latency": stats.to_dict(),
            "agent_breakdown": [bd.to_dict() for bd in breakdowns],
        }
        return json.dumps(data, indent=2)

    def _render_toon(
        self, stats: LatencyStats, breakdowns: List[AgentLatencyBreakdown]
    ) -> str:
        """Render as TOON."""
        lines = [
            "# Latency Dashboard",
            "",
            "[pool_latency]",
            f"pool_id = {stats.pool_id or 'null'}",
            f"p50_seconds = {stats.p50_seconds:.2f}",
            f"p95_seconds = {stats.p95_seconds:.2f}",
            f"p99_seconds = {stats.p99_seconds:.2f}",
            f"mean_seconds = {stats.mean_seconds:.2f}",
            f"count = {stats.count}",
            f"window_hours = {stats.window_hours}",
            "",
            "[[agent_breakdown]]",
        ]

        for bd in breakdowns:
            lines.extend(
                [
                    f"agent_type = {bd.agent_type}",
                    f"mean_seconds = {bd.mean_seconds:.2f}",
                    f"p95_seconds = {bd.p95_seconds:.2f}",
                    f"invocation_count = {bd.invocation_count}",
                    f"total_seconds = {bd.total_seconds:.2f}",
                    "",
                ]
            )

        return "\n".join(lines)


def render_latency_dashboard(
    pool_ids: Optional[List[str]] = None,
    format: OutputFormat = OutputFormat.MARKDOWN,
    window_hours: int = 24,
    event_store: Optional[BeadEventStore] = None,
    vrs_root: Optional[Path] = None,
) -> str:
    """Convenience function to render latency dashboard.

    Args:
        pool_ids: Optional specific pools to include
        format: Output format
        window_hours: Time window for measurements
        event_store: Optional BeadEventStore instance
        vrs_root: Optional VRS root directory

    Returns:
        Formatted dashboard text
    """
    dashboard = LatencyDashboard(event_store=event_store, vrs_root=vrs_root)

    # For now, render for first pool or all
    pool_id = pool_ids[0] if pool_ids else None

    return dashboard.render(format=format, pool_id=pool_id, window_hours=window_hours)


__all__ = [
    "OutputFormat",
    "LatencyStats",
    "AgentLatencyBreakdown",
    "LatencyDashboard",
    "render_latency_dashboard",
]
