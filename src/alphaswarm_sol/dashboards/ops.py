"""Operations dashboard for SLO status, pool health, incidents, and costs.

This module provides a unified operations overview dashboard aggregating:
- SLO compliance status (red/yellow/green)
- Pool health summaries
- Active incidents
- Cost breakdowns

Example:
    from alphaswarm_sol.dashboards.ops import render_ops_dashboard, OutputFormat

    # Generate ops dashboard
    dashboard = render_ops_dashboard(
        pool_ids=["pool-001"],
        format=OutputFormat.MARKDOWN,
        window_hours=24
    )
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from alphaswarm_sol.dashboards.latency import OutputFormat
from alphaswarm_sol.metrics.cost_ledger import CostLedger, PoolCostSummary, get_all_pool_summaries
from alphaswarm_sol.reliability.slo import SLOStatus, SLOTracker


@dataclass
class PoolHealthSummary:
    """Pool health summary.

    Attributes:
        pool_id: Pool identifier
        status: Health status (healthy, degraded, unhealthy)
        active_beads: Number of active beads
        completed_beads: Number of completed beads
        failed_beads: Number of failed beads
        avg_latency_seconds: Average bead completion latency
        success_rate: Bead success rate percentage
    """

    pool_id: str
    status: str
    active_beads: int
    completed_beads: int
    failed_beads: int
    avg_latency_seconds: float
    success_rate: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pool_id": self.pool_id,
            "status": self.status,
            "active_beads": self.active_beads,
            "completed_beads": self.completed_beads,
            "failed_beads": self.failed_beads,
            "avg_latency_seconds": round(self.avg_latency_seconds, 2),
            "success_rate": round(self.success_rate, 3),
        }


@dataclass
class SLOStatusSummary:
    """SLO status summary.

    Attributes:
        slo_id: SLO identifier
        status: Status (healthy, warning, violated)
        current_value: Current measured value
        target: Target value
        alert_threshold: Alert threshold value
    """

    slo_id: str
    status: SLOStatus
    current_value: float
    target: float
    alert_threshold: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "slo_id": self.slo_id,
            "status": self.status.value,
            "current_value": round(self.current_value, 2),
            "target": self.target,
            "alert_threshold": self.alert_threshold,
        }


@dataclass
class IncidentSummary:
    """Incident summary.

    Attributes:
        incident_id: Incident identifier
        severity: Severity level (critical, high, medium, low)
        title: Incident title
        pool_ids: Affected pool IDs
        started_at: When incident started
        status: Current status (active, investigating, resolved)
    """

    incident_id: str
    severity: str
    title: str
    pool_ids: List[str] = field(default_factory=list)
    started_at: str = ""
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "incident_id": self.incident_id,
            "severity": self.severity,
            "title": self.title,
            "pool_ids": self.pool_ids,
            "started_at": self.started_at,
            "status": self.status,
        }


class OpsDashboard:
    """Operations overview dashboard.

    Aggregates SLO status, pool health, active incidents, and cost summaries
    into a unified operator-facing dashboard.

    Example:
        dashboard = OpsDashboard(slo_tracker=tracker, cost_ledgers=ledgers)
        summary = dashboard.get_pool_health(pool_ids=["pool-001"])
        text = dashboard.render(OutputFormat.MARKDOWN)
    """

    def __init__(
        self,
        slo_tracker: Optional[SLOTracker] = None,
        cost_ledgers: Optional[Dict[str, CostLedger]] = None,
        vrs_root: Optional[Path] = None,
    ):
        """Initialize ops dashboard.

        Args:
            slo_tracker: Optional SLOTracker instance
            cost_ledgers: Optional dictionary of pool_id -> CostLedger
            vrs_root: Optional VRS root directory
        """
        self.slo_tracker = slo_tracker
        self.cost_ledgers = cost_ledgers or {}
        self.vrs_root = vrs_root

    def get_pool_health(
        self,
        pool_ids: Optional[List[str]] = None,
        window_hours: int = 24,
    ) -> List[PoolHealthSummary]:
        """Get pool health summaries.

        Args:
            pool_ids: Optional specific pools to include
            window_hours: Time window for measurements

        Returns:
            List of PoolHealthSummary objects
        """
        # Placeholder implementation
        summaries = [
            PoolHealthSummary(
                pool_id="pool-001",
                status="healthy",
                active_beads=5,
                completed_beads=45,
                failed_beads=2,
                avg_latency_seconds=180.5,
                success_rate=0.957,
            ),
            PoolHealthSummary(
                pool_id="pool-002",
                status="degraded",
                active_beads=8,
                completed_beads=32,
                failed_beads=5,
                avg_latency_seconds=250.2,
                success_rate=0.865,
            ),
        ]

        if pool_ids:
            summaries = [s for s in summaries if s.pool_id in pool_ids]

        return summaries

    def get_slo_status_summary(
        self,
        window_hours: int = 24,
    ) -> List[SLOStatusSummary]:
        """Get SLO status summary.

        Args:
            window_hours: Time window for measurements

        Returns:
            List of SLOStatusSummary objects
        """
        if self.slo_tracker is None:
            # Return placeholder if no tracker
            return [
                SLOStatusSummary(
                    slo_id="pool_success_rate",
                    status=SLOStatus.HEALTHY,
                    current_value=95.5,
                    target=95.0,
                    alert_threshold=90.0,
                ),
                SLOStatusSummary(
                    slo_id="pool_completion_latency_p95",
                    status=SLOStatus.WARNING,
                    current_value=320.0,
                    target=300.0,
                    alert_threshold=360.0,
                ),
            ]

        summaries = []
        for slo_id, slo in self.slo_tracker.slos.items():
            # Measure SLO
            measurement = self.slo_tracker.measure_slo(
                slo_id=slo_id, window_minutes=window_hours * 60
            )

            # Check for violation
            violation = self.slo_tracker.check_slo(slo_id, measurement)

            status = violation.status if violation else SLOStatus.HEALTHY

            summaries.append(
                SLOStatusSummary(
                    slo_id=slo_id,
                    status=status,
                    current_value=measurement.value,
                    target=slo.target,
                    alert_threshold=slo.alert_threshold,
                )
            )

        return summaries

    def get_active_incidents(
        self,
        pool_ids: Optional[List[str]] = None,
    ) -> List[IncidentSummary]:
        """Get active incidents.

        Args:
            pool_ids: Optional filter by affected pools

        Returns:
            List of IncidentSummary objects
        """
        # Placeholder implementation
        incidents = [
            IncidentSummary(
                incident_id="INC-001",
                severity="high",
                title="Pool completion latency P95 exceeding threshold",
                pool_ids=["pool-002"],
                started_at="2026-01-29T17:30:00Z",
                status="investigating",
            ),
        ]

        if pool_ids:
            incidents = [
                i for i in incidents if any(pid in pool_ids for pid in i.pool_ids)
            ]

        return incidents

    def get_cost_summary(
        self,
        pool_ids: Optional[List[str]] = None,
    ) -> List[PoolCostSummary]:
        """Get cost summaries for pools.

        Args:
            pool_ids: Optional specific pools to include

        Returns:
            List of PoolCostSummary objects
        """
        # Use global summaries if no ledgers provided
        if not self.cost_ledgers:
            summaries = get_all_pool_summaries()
        else:
            summaries = [ledger.summary() for ledger in self.cost_ledgers.values()]

        if pool_ids:
            summaries = [s for s in summaries if s.pool_id in pool_ids]

        return summaries

    def render(
        self,
        format: OutputFormat = OutputFormat.MARKDOWN,
        pool_ids: Optional[List[str]] = None,
        window_hours: int = 24,
    ) -> str:
        """Render ops dashboard.

        Args:
            format: Output format (markdown, json, toon)
            pool_ids: Optional specific pools to include
            window_hours: Time window for measurements

        Returns:
            Formatted dashboard text
        """
        # Gather all data
        pool_health = self.get_pool_health(pool_ids, window_hours)
        slo_status = self.get_slo_status_summary(window_hours)
        incidents = self.get_active_incidents(pool_ids)
        cost_summaries = self.get_cost_summary(pool_ids)

        if format == OutputFormat.MARKDOWN:
            return self._render_markdown(pool_health, slo_status, incidents, cost_summaries)
        elif format == OutputFormat.JSON:
            return self._render_json(pool_health, slo_status, incidents, cost_summaries)
        else:  # TOON
            return self._render_toon(pool_health, slo_status, incidents, cost_summaries)

    def _render_markdown(
        self,
        pool_health: List[PoolHealthSummary],
        slo_status: List[SLOStatusSummary],
        incidents: List[IncidentSummary],
        cost_summaries: List[PoolCostSummary],
    ) -> str:
        """Render as markdown."""
        lines = [
            "# Operations Dashboard",
            "",
            "## SLO Status",
            "",
        ]

        # SLO status with colors
        for slo in slo_status:
            status_icon = {
                SLOStatus.HEALTHY: "🟢",
                SLOStatus.WARNING: "🟡",
                SLOStatus.VIOLATED: "🔴",
            }.get(slo.status, "⚪")

            lines.append(
                f"- {status_icon} **{slo.slo_id}:** {slo.current_value:.2f} "
                f"(target: {slo.target:.2f}, threshold: {slo.alert_threshold:.2f})"
            )

        lines.extend(
            [
                "",
                "## Pool Health",
                "",
                "| Pool | Status | Active | Completed | Failed | Avg Latency | Success Rate |",
                "|------|--------|--------|-----------|--------|-------------|--------------|",
            ]
        )

        for ph in pool_health:
            status_icon = {
                "healthy": "🟢",
                "degraded": "🟡",
                "unhealthy": "🔴",
            }.get(ph.status, "⚪")

            lines.append(
                f"| {ph.pool_id} | {status_icon} {ph.status} | {ph.active_beads} | "
                f"{ph.completed_beads} | {ph.failed_beads} | {ph.avg_latency_seconds:.1f}s | "
                f"{ph.success_rate:.1%} |"
            )

        lines.extend(
            [
                "",
                "## Active Incidents",
                "",
            ]
        )

        if incidents:
            for inc in incidents:
                severity_icon = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢",
                }.get(inc.severity, "⚪")

                lines.append(
                    f"- {severity_icon} **{inc.incident_id}** [{inc.severity.upper()}] {inc.title}"
                )
                lines.append(f"  - Pools: {', '.join(inc.pool_ids)}")
                lines.append(f"  - Status: {inc.status}")
                lines.append(f"  - Started: {inc.started_at}")
                lines.append("")
        else:
            lines.append("No active incidents")
            lines.append("")

        lines.extend(
            [
                "## Cost Summary",
                "",
                "| Pool | Total Cost | Requests | Avg/Request | Budget Used |",
                "|------|------------|----------|-------------|-------------|",
            ]
        )

        for cs in cost_summaries:
            budget_pct = (
                f"{cs.budget_utilization_pct:.1f}%"
                if cs.budget_utilization_pct is not None
                else "N/A"
            )
            lines.append(
                f"| {cs.pool_id} | ${cs.total_cost_usd:.2f} | {cs.total_requests} | "
                f"${cs.avg_cost_per_request:.4f} | {budget_pct} |"
            )

        return "\n".join(lines)

    def _render_json(
        self,
        pool_health: List[PoolHealthSummary],
        slo_status: List[SLOStatusSummary],
        incidents: List[IncidentSummary],
        cost_summaries: List[PoolCostSummary],
    ) -> str:
        """Render as JSON."""
        data = {
            "slo_status": [s.to_dict() for s in slo_status],
            "pool_health": [ph.to_dict() for ph in pool_health],
            "active_incidents": [i.to_dict() for i in incidents],
            "cost_summary": [cs.to_dict() for cs in cost_summaries],
        }
        return json.dumps(data, indent=2)

    def _render_toon(
        self,
        pool_health: List[PoolHealthSummary],
        slo_status: List[SLOStatusSummary],
        incidents: List[IncidentSummary],
        cost_summaries: List[PoolCostSummary],
    ) -> str:
        """Render as TOON."""
        lines = [
            "# Operations Dashboard",
            "",
            "[[slo_status]]",
        ]

        for slo in slo_status:
            lines.extend(
                [
                    f"slo_id = {slo.slo_id}",
                    f"status = {slo.status.value}",
                    f"current_value = {slo.current_value:.2f}",
                    f"target = {slo.target}",
                    f"alert_threshold = {slo.alert_threshold}",
                    "",
                ]
            )

        lines.append("[[pool_health]]")

        for ph in pool_health:
            lines.extend(
                [
                    f"pool_id = {ph.pool_id}",
                    f"status = {ph.status}",
                    f"active_beads = {ph.active_beads}",
                    f"completed_beads = {ph.completed_beads}",
                    f"failed_beads = {ph.failed_beads}",
                    f"avg_latency_seconds = {ph.avg_latency_seconds:.2f}",
                    f"success_rate = {ph.success_rate:.3f}",
                    "",
                ]
            )

        lines.append("[[active_incidents]]")

        for inc in incidents:
            lines.extend(
                [
                    f"incident_id = {inc.incident_id}",
                    f"severity = {inc.severity}",
                    f"title = {inc.title}",
                    f"pool_ids = {','.join(inc.pool_ids)}",
                    f"started_at = {inc.started_at}",
                    f"status = {inc.status}",
                    "",
                ]
            )

        lines.append("[[cost_summary]]")

        for cs in cost_summaries:
            lines.extend(
                [
                    f"pool_id = {cs.pool_id}",
                    f"total_cost_usd = {cs.total_cost_usd:.4f}",
                    f"total_requests = {cs.total_requests}",
                    f"avg_cost_per_request = {cs.avg_cost_per_request:.4f}",
                    f"budget_utilization_pct = {cs.budget_utilization_pct or 0.0:.1f}",
                    "",
                ]
            )

        return "\n".join(lines)


def render_ops_dashboard(
    pool_ids: Optional[List[str]] = None,
    format: OutputFormat = OutputFormat.MARKDOWN,
    window_hours: int = 24,
    slo_tracker: Optional[SLOTracker] = None,
    cost_ledgers: Optional[Dict[str, CostLedger]] = None,
    vrs_root: Optional[Path] = None,
) -> str:
    """Convenience function to render ops dashboard.

    Args:
        pool_ids: Optional specific pools to include
        format: Output format
        window_hours: Time window for measurements
        slo_tracker: Optional SLOTracker instance
        cost_ledgers: Optional cost ledgers
        vrs_root: Optional VRS root directory

    Returns:
        Formatted dashboard text
    """
    dashboard = OpsDashboard(
        slo_tracker=slo_tracker,
        cost_ledgers=cost_ledgers,
        vrs_root=vrs_root,
    )

    return dashboard.render(format=format, pool_ids=pool_ids, window_hours=window_hours)


__all__ = [
    "PoolHealthSummary",
    "SLOStatusSummary",
    "IncidentSummary",
    "OpsDashboard",
    "render_ops_dashboard",
]
