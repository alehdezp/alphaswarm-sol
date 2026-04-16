"""Dashboard modules for latency, cost, accuracy, and SLO monitoring.

This package provides operator-facing dashboards for multi-agent orchestration
visibility. Dashboards render metrics in multiple formats (markdown, JSON, TOON)
and can be generated on-demand via CLI.

Modules:
    latency: Pool completion latency and agent-level latency breakdowns
    accuracy: Verdict accuracy and per-pattern precision metrics
    ops: Operations overview with SLO status, pool health, incidents

Example:
    from alphaswarm_sol.dashboards import render_ops_dashboard, OutputFormat

    # Generate ops dashboard
    dashboard_text = render_ops_dashboard(
        pool_ids=["pool-001", "pool-002"],
        format=OutputFormat.MARKDOWN,
        window_hours=24
    )
"""

from alphaswarm_sol.dashboards.accuracy import (
    AccuracyDashboard,
    AccuracyStats,
    ConfidenceCalibration,
    PatternAccuracyBreakdown,
    render_accuracy_dashboard,
)
from alphaswarm_sol.dashboards.latency import (
    AgentLatencyBreakdown,
    LatencyDashboard,
    LatencyStats,
    OutputFormat,
    render_latency_dashboard,
)
from alphaswarm_sol.dashboards.ops import (
    OpsDashboard,
    PoolHealthSummary,
    SLOStatusSummary,
    render_ops_dashboard,
)

__all__ = [
    # Output formats
    "OutputFormat",
    # Latency
    "LatencyDashboard",
    "LatencyStats",
    "AgentLatencyBreakdown",
    "render_latency_dashboard",
    # Accuracy
    "AccuracyDashboard",
    "AccuracyStats",
    "PatternAccuracyBreakdown",
    "ConfidenceCalibration",
    "render_accuracy_dashboard",
    # Ops
    "OpsDashboard",
    "PoolHealthSummary",
    "SLOStatusSummary",
    "render_ops_dashboard",
]
