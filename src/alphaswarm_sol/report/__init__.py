"""
Report Generation Module

Provides analysis completeness reports and finding summaries.
"""

from alphaswarm_sol.report.completeness import CompletenessReport, generate_completeness_report
from alphaswarm_sol.report.cost_dashboard import (
    render_cost_dashboard,
    render_summary_dashboard,
    render_multi_pool_dashboard,
    render_compact_summary,
    render_toon_summary,
)

__all__ = [
    "CompletenessReport",
    "generate_completeness_report",
    "render_cost_dashboard",
    "render_summary_dashboard",
    "render_multi_pool_dashboard",
    "render_compact_summary",
    "render_toon_summary",
]
