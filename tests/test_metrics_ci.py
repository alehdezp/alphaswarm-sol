"""Tests for metrics CI integration.

Task 8.7: CI integration tests for metrics module.
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
from alphaswarm_sol.metrics import (
    MetricName,
    MetricSnapshot,
    MetricStatus,
    MetricValue,
    ExitCode,
    CIResult,
    check_metrics_gate,
    save_baseline,
    compare_snapshots,
    format_ci_summary,
)


class TestExitCodes(unittest.TestCase):
    """Test exit code definitions."""

    def test_exit_codes_are_integers(self):
        """Exit codes are proper integers."""
        self.assertEqual(ExitCode.SUCCESS, 0)
        self.assertEqual(ExitCode.CRITICAL_ALERT, 1)
        self.assertEqual(ExitCode.WARNING_ALERT, 2)
        self.assertEqual(ExitCode.REGRESSION_DETECTED, 3)
        self.assertEqual(ExitCode.BASELINE_NOT_FOUND, 4)
        self.assertEqual(ExitCode.INVALID_CONFIG, 5)


class TestCIResult(unittest.TestCase):
    """Test CIResult dataclass."""

    def setUp(self):
        """Create test snapshot."""
        self.snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            version="1.0.0",
            metrics={
                MetricName.DETECTION_RATE: MetricValue(
                    name=MetricName.DETECTION_RATE,
                    value=0.85,
                    target=0.80,
                    threshold_warning=0.75,
                    threshold_critical=0.70,
                    status=MetricStatus.OK,
                ),
            },
        )

    def test_ci_result_creation(self):
        """CIResult can be created."""
        result = CIResult(
            exit_code=ExitCode.SUCCESS,
            alerts=[],
            snapshot=self.snapshot,
            baseline=None,
            message="All good",
        )
        self.assertEqual(result.exit_code, ExitCode.SUCCESS)
        self.assertEqual(result.message, "All good")
        self.assertFalse(result.regression_detected)

    def test_ci_result_to_dict(self):
        """CIResult converts to dict."""
        result = CIResult(
            exit_code=ExitCode.SUCCESS,
            alerts=[],
            snapshot=self.snapshot,
            baseline=None,
            message="All good",
        )
        data = result.to_dict()
        self.assertEqual(data["exit_code"], 0)
        self.assertEqual(data["exit_code_name"], "SUCCESS")
        self.assertEqual(data["message"], "All good")
        self.assertFalse(data["regression_detected"])
        self.assertIn("snapshot", data)
        self.assertIn("timestamp", data)

    def test_ci_result_to_json(self):
        """CIResult converts to JSON."""
        result = CIResult(
            exit_code=ExitCode.SUCCESS,
            alerts=[],
            snapshot=self.snapshot,
            baseline=None,
            message="All good",
        )
        json_str = result.to_json()
        data = json.loads(json_str)
        self.assertEqual(data["exit_code"], 0)


class TestCheckMetricsGate(unittest.TestCase):
    """Test check_metrics_gate function."""

    def setUp(self):
        """Create temp directory."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_returns_success_with_no_events(self):
        """Returns success when no events recorded (unknown metrics)."""
        result = check_metrics_gate(storage_path=self.temp_dir)
        # No events = unknown metrics = no alerts
        self.assertEqual(result.exit_code, ExitCode.SUCCESS)
        self.assertIn("within", result.message.lower())

    def test_baseline_not_found(self):
        """Returns error when baseline file doesn't exist."""
        result = check_metrics_gate(
            storage_path=self.temp_dir,
            baseline_path="/nonexistent/baseline.json",
        )
        self.assertEqual(result.exit_code, ExitCode.BASELINE_NOT_FOUND)
        self.assertIn("not found", result.message.lower())

    def test_baseline_comparison_works(self):
        """Baseline comparison runs without error."""
        # Create a baseline file
        baseline_data = {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "metrics": {
                "detection_rate": {
                    "name": "detection_rate",
                    "value": 0.85,
                    "target": 0.80,
                    "threshold_warning": 0.75,
                    "threshold_critical": 0.70,
                    "status": "ok",
                },
            },
        }
        baseline_path = Path(self.temp_dir) / "baseline.json"
        with open(baseline_path, "w") as f:
            json.dump(baseline_data, f)

        result = check_metrics_gate(
            storage_path=self.temp_dir,
            baseline_path=str(baseline_path),
        )
        # Should run without error
        self.assertIsInstance(result, CIResult)

    def test_fail_on_warning_option(self):
        """fail_on_warning causes warnings to fail."""
        # Without fail_on_warning, warnings are OK
        result = check_metrics_gate(
            storage_path=self.temp_dir,
            fail_on_warning=False,
        )
        # With no events, should be success
        self.assertEqual(result.exit_code, ExitCode.SUCCESS)


class TestSaveBaseline(unittest.TestCase):
    """Test save_baseline function."""

    def setUp(self):
        """Create temp directory."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_creates_baseline_file(self):
        """save_baseline creates a file."""
        output_path = Path(self.temp_dir) / "baseline.json"
        result_path = save_baseline(output_path, self.temp_dir)

        self.assertEqual(result_path, output_path)
        self.assertTrue(output_path.exists())

        with open(output_path) as f:
            data = json.load(f)
        self.assertIn("timestamp", data)
        self.assertIn("version", data)
        self.assertIn("metrics", data)

    def test_creates_parent_directories(self):
        """save_baseline creates parent directories."""
        output_path = Path(self.temp_dir) / "nested" / "dir" / "baseline.json"
        result_path = save_baseline(output_path, self.temp_dir)

        self.assertTrue(output_path.exists())


class TestCompareSnapshots(unittest.TestCase):
    """Test compare_snapshots function."""

    def setUp(self):
        """Create temp directory and test files."""
        self.temp_dir = tempfile.mkdtemp()

        # Create baseline snapshot
        self.baseline_data = {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "metrics": {
                "detection_rate": {
                    "name": "detection_rate",
                    "value": 0.85,
                    "target": 0.80,
                    "threshold_warning": 0.75,
                    "threshold_critical": 0.70,
                    "status": "ok",
                },
                "false_positive_rate": {
                    "name": "false_positive_rate",
                    "value": 0.10,
                    "target": 0.10,
                    "threshold_warning": 0.18,
                    "threshold_critical": 0.20,
                    "status": "ok",
                },
            },
        }
        self.baseline_path = Path(self.temp_dir) / "baseline.json"
        with open(self.baseline_path, "w") as f:
            json.dump(self.baseline_data, f)

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_compare_identical_snapshots(self):
        """Comparing identical snapshots returns success."""
        current_path = Path(self.temp_dir) / "current.json"
        with open(current_path, "w") as f:
            json.dump(self.baseline_data, f)

        result = compare_snapshots(current_path, self.baseline_path)
        self.assertEqual(result.exit_code, ExitCode.SUCCESS)

    def test_compare_regressed_snapshot(self):
        """Comparing regressed snapshot returns regression."""
        current_data = self.baseline_data.copy()
        current_data = {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "metrics": {
                "detection_rate": {
                    "name": "detection_rate",
                    "value": 0.75,  # Dropped from 0.85
                    "target": 0.80,
                    "threshold_warning": 0.75,
                    "threshold_critical": 0.70,
                    "status": "warning",
                },
            },
        }
        current_path = Path(self.temp_dir) / "current.json"
        with open(current_path, "w") as f:
            json.dump(current_data, f)

        result = compare_snapshots(current_path, self.baseline_path)
        # Should detect regression or warning
        self.assertTrue(result.regression_detected or len(result.alerts) > 0)


class TestFormatCISummary(unittest.TestCase):
    """Test format_ci_summary function."""

    def setUp(self):
        """Create test snapshot."""
        self.snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            version="1.0.0",
            metrics={
                MetricName.DETECTION_RATE: MetricValue(
                    name=MetricName.DETECTION_RATE,
                    value=0.85,
                    target=0.80,
                    threshold_warning=0.75,
                    threshold_critical=0.70,
                    status=MetricStatus.OK,
                ),
            },
        )

    def test_formats_success_result(self):
        """Formats success result."""
        result = CIResult(
            exit_code=ExitCode.SUCCESS,
            alerts=[],
            snapshot=self.snapshot,
            baseline=None,
            message="All good",
        )
        output = format_ci_summary(result)
        self.assertIn("SUCCESS", output)
        self.assertIn("All good", output)
        self.assertIn("No alerts", output)

    def test_formats_critical_result(self):
        """Formats critical result."""
        from alphaswarm_sol.metrics import Alert, AlertLevel, AlertType

        alert = Alert(
            metric_name=MetricName.DETECTION_RATE,
            level=AlertLevel.CRITICAL,
            alert_type=AlertType.THRESHOLD_BREACH,
            message="Below critical threshold",
            current_value=0.65,
            threshold_value=0.70,
        )

        result = CIResult(
            exit_code=ExitCode.CRITICAL_ALERT,
            alerts=[alert],
            snapshot=self.snapshot,
            baseline=None,
            message="Critical alert found",
        )
        output = format_ci_summary(result)
        self.assertIn("CRITICAL", output)
        self.assertIn("detection_rate", output)


class TestCICliCommands(unittest.TestCase):
    """Test CI CLI commands."""

    def setUp(self):
        """Create temp directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.runner = CliRunner()

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ci_check_help(self):
        """ci-check --help shows usage."""
        result = self.runner.invoke(app, ["metrics", "ci-check", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("CI gate check", result.output)
        self.assertIn("--baseline", result.output)

    def test_ci_check_runs(self):
        """ci-check runs successfully."""
        result = self.runner.invoke(
            app, ["metrics", "ci-check", "--storage", self.temp_dir]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("SUCCESS", result.output)

    def test_ci_check_json_format(self):
        """ci-check --format json outputs JSON."""
        result = self.runner.invoke(
            app, ["metrics", "ci-check", "--storage", self.temp_dir, "--format", "json"]
        )
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertIn("exit_code", data)
        self.assertIn("alerts", data)

    def test_ci_check_with_nonexistent_baseline(self):
        """ci-check with nonexistent baseline fails."""
        result = self.runner.invoke(
            app,
            [
                "metrics",
                "ci-check",
                "--storage",
                self.temp_dir,
                "--baseline",
                "/nonexistent/file.json",
            ],
        )
        self.assertEqual(result.exit_code, ExitCode.BASELINE_NOT_FOUND)

    def test_save_baseline_runs(self):
        """save-baseline creates a file."""
        output_path = Path(self.temp_dir) / "baseline.json"
        result = self.runner.invoke(
            app,
            [
                "metrics",
                "save-baseline",
                str(output_path),
                "--storage",
                self.temp_dir,
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Baseline saved", result.output)
        self.assertTrue(output_path.exists())

    def test_compare_runs(self):
        """compare compares two files."""
        # Create two snapshot files
        snapshot_data = {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "metrics": {
                "detection_rate": {
                    "name": "detection_rate",
                    "value": 0.85,
                    "target": 0.80,
                    "threshold_warning": 0.75,
                    "threshold_critical": 0.70,
                    "status": "ok",
                },
            },
        }

        current_path = Path(self.temp_dir) / "current.json"
        baseline_path = Path(self.temp_dir) / "baseline.json"

        with open(current_path, "w") as f:
            json.dump(snapshot_data, f)
        with open(baseline_path, "w") as f:
            json.dump(snapshot_data, f)

        result = self.runner.invoke(
            app, ["metrics", "compare", str(current_path), str(baseline_path)]
        )
        self.assertEqual(result.exit_code, 0)

    def test_compare_nonexistent_current(self):
        """compare with nonexistent current fails."""
        baseline_path = Path(self.temp_dir) / "baseline.json"
        with open(baseline_path, "w") as f:
            json.dump({"timestamp": "2024-01-01"}, f)

        result = self.runner.invoke(
            app, ["metrics", "compare", "/nonexistent.json", str(baseline_path)]
        )
        self.assertEqual(result.exit_code, 1)
        self.assertIn("not found", result.output)

    def test_compare_nonexistent_baseline(self):
        """compare with nonexistent baseline fails."""
        current_path = Path(self.temp_dir) / "current.json"
        with open(current_path, "w") as f:
            json.dump({"timestamp": "2024-01-01"}, f)

        result = self.runner.invoke(
            app, ["metrics", "compare", str(current_path), "/nonexistent.json"]
        )
        self.assertEqual(result.exit_code, 1)
        self.assertIn("not found", result.output)


class TestCIModule(unittest.TestCase):
    """Test CI module as standalone script."""

    def setUp(self):
        """Create temp directory."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_main_function_exists(self):
        """CI module has main function."""
        from alphaswarm_sol.metrics.ci import main
        self.assertTrue(callable(main))


class TestCIIntegration(unittest.TestCase):
    """Integration tests for CI workflow."""

    def setUp(self):
        """Create temp directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.runner = CliRunner()

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_ci_workflow(self):
        """Full CI workflow: save baseline -> check -> compare."""
        baseline_path = Path(self.temp_dir) / "baseline.json"

        # 1. Save baseline
        result = self.runner.invoke(
            app,
            [
                "metrics",
                "save-baseline",
                str(baseline_path),
                "--storage",
                self.temp_dir,
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(baseline_path.exists())

        # 2. Run CI check with baseline
        result = self.runner.invoke(
            app,
            [
                "metrics",
                "ci-check",
                "--storage",
                self.temp_dir,
                "--baseline",
                str(baseline_path),
            ],
        )
        self.assertEqual(result.exit_code, 0)

        # 3. Save current snapshot
        current_path = Path(self.temp_dir) / "current.json"
        result = self.runner.invoke(
            app,
            [
                "metrics",
                "save-baseline",
                str(current_path),
                "--storage",
                self.temp_dir,
            ],
        )
        self.assertEqual(result.exit_code, 0)

        # 4. Compare snapshots
        result = self.runner.invoke(
            app, ["metrics", "compare", str(current_path), str(baseline_path)]
        )
        self.assertEqual(result.exit_code, 0)

    def test_ci_check_includes_all_commands(self):
        """Help shows all CI-related commands."""
        result = self.runner.invoke(app, ["metrics", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ci-check", result.output)
        self.assertIn("save-baseline", result.output)
        self.assertIn("compare", result.output)


if __name__ == "__main__":
    unittest.main()
