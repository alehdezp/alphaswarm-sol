"""Tests for dashboard modules."""

import pytest

from alphaswarm_sol.dashboards import (
    AccuracyDashboard,
    LatencyDashboard,
    OpsDashboard,
    OutputFormat,
    render_accuracy_dashboard,
    render_latency_dashboard,
    render_ops_dashboard,
)


class TestLatencyDashboard:
    """Tests for latency dashboard."""

    def test_render_markdown_format(self):
        """Test markdown format rendering."""
        dashboard = LatencyDashboard()
        output = dashboard.render(format=OutputFormat.MARKDOWN, window_hours=24)

        assert "# Latency Dashboard" in output
        assert "Pool Completion Latency" in output
        assert "P50" in output
        assert "P95" in output
        assert "P99" in output
        assert "Agent Latency Breakdown" in output

    def test_render_json_format(self):
        """Test JSON format rendering."""
        dashboard = LatencyDashboard()
        output = dashboard.render(format=OutputFormat.JSON, window_hours=24)

        assert '"pool_latency"' in output
        assert '"agent_breakdown"' in output
        assert '"p50_seconds"' in output
        assert '"p95_seconds"' in output

    def test_render_toon_format(self):
        """Test TOON format rendering."""
        dashboard = LatencyDashboard()
        output = dashboard.render(format=OutputFormat.TOON, window_hours=24)

        assert "# Latency Dashboard" in output
        assert "[pool_latency]" in output
        assert "[[agent_breakdown]]" in output
        assert "p50_seconds =" in output
        assert "p95_seconds =" in output

    def test_get_pool_latency_stats(self):
        """Test getting pool latency stats."""
        dashboard = LatencyDashboard()
        stats = dashboard.get_pool_latency_stats(window_hours=24)

        assert stats.window_hours == 24
        assert stats.p50_seconds >= 0
        assert stats.p95_seconds >= 0
        assert stats.p99_seconds >= 0
        assert stats.mean_seconds >= 0

    def test_get_agent_latency_breakdown(self):
        """Test getting agent latency breakdown."""
        dashboard = LatencyDashboard()
        breakdowns = dashboard.get_agent_latency_breakdown(window_hours=24)

        assert len(breakdowns) > 0
        for bd in breakdowns:
            assert bd.agent_type
            assert bd.mean_seconds >= 0
            assert bd.p95_seconds >= 0
            assert bd.invocation_count >= 0


class TestAccuracyDashboard:
    """Tests for accuracy dashboard."""

    def test_render_includes_precision(self):
        """Test that accuracy dashboard includes precision metrics."""
        dashboard = AccuracyDashboard()
        output = dashboard.render(format=OutputFormat.MARKDOWN, window_hours=24)

        assert "# Accuracy Dashboard" in output
        assert "Precision" in output
        assert "Recall" in output
        assert "F1 Score" in output

    def test_render_includes_pattern_breakdown(self):
        """Test that accuracy dashboard includes per-pattern breakdown."""
        dashboard = AccuracyDashboard()
        output = dashboard.render(format=OutputFormat.MARKDOWN, window_hours=24)

        assert "Per-Pattern Breakdown" in output
        # Should have at least one pattern in placeholder data
        assert "reentrancy" in output.lower() or "Pattern" in output

    def test_render_json_format(self):
        """Test JSON format rendering."""
        dashboard = AccuracyDashboard()
        output = dashboard.render(format=OutputFormat.JSON, window_hours=24)

        assert '"overall"' in output
        assert '"pattern_breakdown"' in output
        assert '"precision"' in output
        assert '"recall"' in output

    def test_render_toon_format(self):
        """Test TOON format rendering."""
        dashboard = AccuracyDashboard()
        output = dashboard.render(format=OutputFormat.TOON, window_hours=24)

        assert "# Accuracy Dashboard" in output
        assert "[overall]" in output
        assert "[[pattern_breakdown]]" in output
        assert "precision =" in output

    def test_get_accuracy_stats(self):
        """Test getting accuracy stats."""
        dashboard = AccuracyDashboard()
        stats = dashboard.get_accuracy_stats(window_hours=24)

        assert stats.window_hours == 24
        assert 0 <= stats.precision <= 1
        assert 0 <= stats.recall <= 1
        assert 0 <= stats.f1_score <= 1
        assert stats.true_positives >= 0
        assert stats.false_positives >= 0

    def test_get_pattern_breakdown(self):
        """Test getting pattern breakdown."""
        dashboard = AccuracyDashboard()
        breakdowns = dashboard.get_pattern_breakdown(window_hours=24)

        assert len(breakdowns) > 0
        for bd in breakdowns:
            assert bd.pattern_id
            assert 0 <= bd.precision <= 1
            assert 0 <= bd.recall <= 1

    def test_get_confidence_calibration(self):
        """Test getting confidence calibration."""
        dashboard = AccuracyDashboard()
        calibration = dashboard.get_confidence_calibration(window_hours=24)

        assert len(calibration) > 0
        for cal in calibration:
            assert cal.confidence_bucket
            assert 0 <= cal.expected_accuracy <= 1
            assert 0 <= cal.actual_accuracy <= 1
            assert cal.count >= 0


class TestOpsDashboard:
    """Tests for ops dashboard."""

    def test_render_includes_slo_status(self):
        """Test that ops dashboard includes SLO status."""
        dashboard = OpsDashboard()
        output = dashboard.render(format=OutputFormat.MARKDOWN, window_hours=24)

        assert "# Operations Dashboard" in output
        assert "SLO Status" in output

    def test_render_includes_pool_health(self):
        """Test that ops dashboard includes pool health."""
        dashboard = OpsDashboard()
        output = dashboard.render(format=OutputFormat.MARKDOWN, window_hours=24)

        assert "Pool Health" in output
        assert "Active" in output or "Completed" in output

    def test_render_includes_active_incidents(self):
        """Test that ops dashboard includes active incidents."""
        dashboard = OpsDashboard()
        output = dashboard.render(format=OutputFormat.MARKDOWN, window_hours=24)

        assert "Active Incidents" in output

    def test_render_includes_cost_summary(self):
        """Test that ops dashboard includes cost summary."""
        dashboard = OpsDashboard()
        output = dashboard.render(format=OutputFormat.MARKDOWN, window_hours=24)

        assert "Cost Summary" in output

    def test_render_json_format(self):
        """Test JSON format rendering."""
        dashboard = OpsDashboard()
        output = dashboard.render(format=OutputFormat.JSON, window_hours=24)

        assert '"slo_status"' in output
        assert '"pool_health"' in output
        assert '"active_incidents"' in output
        assert '"cost_summary"' in output

    def test_render_toon_format(self):
        """Test TOON format rendering."""
        dashboard = OpsDashboard()
        output = dashboard.render(format=OutputFormat.TOON, window_hours=24)

        assert "# Operations Dashboard" in output
        assert "[[slo_status]]" in output
        assert "[[pool_health]]" in output
        assert "[[active_incidents]]" in output
        assert "[[cost_summary]]" in output

    def test_get_pool_health(self):
        """Test getting pool health summaries."""
        dashboard = OpsDashboard()
        summaries = dashboard.get_pool_health(window_hours=24)

        assert len(summaries) > 0
        for summary in summaries:
            assert summary.pool_id
            assert summary.status in ["healthy", "degraded", "unhealthy"]
            assert summary.active_beads >= 0
            assert summary.completed_beads >= 0

    def test_get_slo_status_summary(self):
        """Test getting SLO status summary."""
        dashboard = OpsDashboard()
        summaries = dashboard.get_slo_status_summary(window_hours=24)

        assert len(summaries) > 0
        for summary in summaries:
            assert summary.slo_id
            assert summary.status in ["healthy", "warning", "violated"]
            assert summary.current_value >= 0

    def test_get_active_incidents(self):
        """Test getting active incidents."""
        dashboard = OpsDashboard()
        incidents = dashboard.get_active_incidents()

        # May or may not have incidents
        for incident in incidents:
            assert incident.incident_id
            assert incident.severity
            assert incident.title

    def test_get_cost_summary(self):
        """Test getting cost summaries."""
        dashboard = OpsDashboard()
        summaries = dashboard.get_cost_summary()

        # May be empty if no ledgers
        for summary in summaries:
            assert summary.pool_id
            assert summary.total_cost_usd >= 0
            assert summary.total_requests >= 0


class TestConvenienceFunctions:
    """Tests for convenience rendering functions."""

    def test_render_latency_dashboard(self):
        """Test latency dashboard convenience function."""
        output = render_latency_dashboard(
            format=OutputFormat.MARKDOWN, window_hours=24
        )

        assert "# Latency Dashboard" in output

    def test_render_accuracy_dashboard(self):
        """Test accuracy dashboard convenience function."""
        output = render_accuracy_dashboard(
            format=OutputFormat.MARKDOWN, window_hours=24
        )

        assert "# Accuracy Dashboard" in output

    def test_render_ops_dashboard(self):
        """Test ops dashboard convenience function."""
        output = render_ops_dashboard(format=OutputFormat.MARKDOWN, window_hours=24)

        assert "# Operations Dashboard" in output
