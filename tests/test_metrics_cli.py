"""Tests for metrics CLI commands.

Task 8.5: CLI tests for metrics module.
"""

import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from alphaswarm_sol.cli.main import app
from alphaswarm_sol.metrics import MetricName, MetricSnapshot, MetricStatus, MetricValue


class TestMetricsCLI(unittest.TestCase):
    """Test metrics CLI commands."""

    def setUp(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.runner = CliRunner()

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_metrics_help(self):
        """metrics --help shows available commands."""
        result = self.runner.invoke(app, ["metrics", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("show", result.output)
        self.assertIn("history", result.output)
        self.assertIn("alerts", result.output)
        self.assertIn("save", result.output)
        self.assertIn("definitions", result.output)

    def test_metrics_show(self):
        """metrics show displays current metrics."""
        result = self.runner.invoke(
            app, ["metrics", "show", "--storage", self.temp_dir]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("VKG Metrics", result.output)

    def test_metrics_show_json(self):
        """metrics show --format json outputs JSON."""
        result = self.runner.invoke(
            app, ["metrics", "show", "--storage", self.temp_dir, "--format", "json"]
        )
        self.assertEqual(result.exit_code, 0)
        # Should be valid JSON
        data = json.loads(result.output)
        self.assertIn("timestamp", data)
        self.assertIn("version", data)
        self.assertIn("metrics", data)

    def test_metrics_definitions(self):
        """metrics definitions shows all metric definitions."""
        result = self.runner.invoke(app, ["metrics", "definitions"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("detection_rate", result.output)
        self.assertIn("false_positive_rate", result.output)
        self.assertIn("Target", result.output)

    def test_metrics_definitions_json(self):
        """metrics definitions --format json outputs JSON."""
        result = self.runner.invoke(
            app, ["metrics", "definitions", "--format", "json"]
        )
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertIn("detection_rate", data)
        self.assertIn("formula", data["detection_rate"])

    def test_metrics_definitions_single(self):
        """metrics definitions --metric shows single metric."""
        result = self.runner.invoke(
            app, ["metrics", "definitions", "--metric", "detection_rate"]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("detection_rate", result.output)
        # Should not have other metrics
        self.assertNotIn("false_positive_rate", result.output)

    def test_metrics_definitions_invalid(self):
        """metrics definitions --metric with invalid metric fails."""
        result = self.runner.invoke(
            app, ["metrics", "definitions", "--metric", "invalid_metric"]
        )
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Unknown metric", result.output)

    def test_metrics_save(self):
        """metrics save creates a snapshot file."""
        result = self.runner.invoke(
            app, ["metrics", "save", "--storage", self.temp_dir]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Snapshot saved", result.output)

        # Check file was created
        history_dir = Path(self.temp_dir) / "history"
        json_files = list(history_dir.glob("*.json"))
        self.assertEqual(len(json_files), 1)

    def test_metrics_history_empty(self):
        """metrics history with no data shows message."""
        result = self.runner.invoke(
            app, ["metrics", "history", "--storage", self.temp_dir]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No history found", result.output)

    def test_metrics_history_with_data(self):
        """metrics history shows saved snapshots."""
        # Save a snapshot first
        self.runner.invoke(
            app, ["metrics", "save", "--storage", self.temp_dir]
        )

        # Now view history
        result = self.runner.invoke(
            app, ["metrics", "history", "--storage", self.temp_dir]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Metric History", result.output)

    def test_metrics_alerts_no_alerts(self):
        """metrics alerts with no data shows no alerts."""
        result = self.runner.invoke(
            app, ["metrics", "alerts", "--storage", self.temp_dir]
        )
        self.assertEqual(result.exit_code, 0)
        # With no events, metrics are unknown, so no alerts
        self.assertIn("No alerts", result.output)

    def test_metrics_alerts_json(self):
        """metrics alerts --format json outputs JSON."""
        result = self.runner.invoke(
            app, ["metrics", "alerts", "--storage", self.temp_dir, "--format", "json"]
        )
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertIsInstance(data, list)

    def test_metrics_cleanup_dry_run(self):
        """metrics cleanup --dry-run shows what would be deleted."""
        # Save a snapshot first
        self.runner.invoke(
            app, ["metrics", "save", "--storage", self.temp_dir]
        )

        result = self.runner.invoke(
            app, ["metrics", "cleanup", "--storage", self.temp_dir, "--dry-run"]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Would delete", result.output)

    def test_metrics_cleanup(self):
        """metrics cleanup removes old snapshots."""
        # Save a snapshot first
        self.runner.invoke(
            app, ["metrics", "save", "--storage", self.temp_dir]
        )

        result = self.runner.invoke(
            app, ["metrics", "cleanup", "--storage", self.temp_dir, "--retention", "90"]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Removed", result.output)

    def test_metrics_stats_no_data(self):
        """metrics stats with no data shows message."""
        result = self.runner.invoke(
            app,
            ["metrics", "stats", "--storage", self.temp_dir, "--metric", "detection_rate"],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No data available", result.output)

    def test_metrics_stats_invalid_metric(self):
        """metrics stats with invalid metric fails."""
        result = self.runner.invoke(
            app,
            ["metrics", "stats", "--storage", self.temp_dir, "--metric", "invalid"],
        )
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Unknown metric", result.output)


class TestMetricsCLIIntegration(unittest.TestCase):
    """Integration tests for metrics CLI."""

    def setUp(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.runner = CliRunner()

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_workflow(self):
        """Full workflow: save -> show -> history -> alerts."""
        # Save snapshot
        result = self.runner.invoke(
            app, ["metrics", "save", "--storage", self.temp_dir]
        )
        self.assertEqual(result.exit_code, 0)

        # Show current metrics
        result = self.runner.invoke(
            app, ["metrics", "show", "--storage", self.temp_dir]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("VKG Metrics", result.output)

        # View history
        result = self.runner.invoke(
            app, ["metrics", "history", "--storage", self.temp_dir]
        )
        self.assertEqual(result.exit_code, 0)

        # Check alerts
        result = self.runner.invoke(
            app, ["metrics", "alerts", "--storage", self.temp_dir]
        )
        self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
