"""Tests for learning CLI commands.

Task 7.7: CLI interface for learning control.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from alphaswarm_sol.cli.learn import learn_app


class TestLearnCLI(unittest.TestCase):
    """Test learning CLI commands."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.learning_dir = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _patch_learning_dir(self):
        """Create a patch for DEFAULT_LEARNING_DIR."""
        return patch("alphaswarm_sol.cli.learn._get_learning_dir", return_value=self.learning_dir)

    def test_enable(self):
        """Test enable command."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["enable"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("ENABLED", result.output)

            # Check config was saved
            config_path = self.learning_dir / "config.json"
            self.assertTrue(config_path.exists())
            with open(config_path) as f:
                config = json.load(f)
            self.assertTrue(config["enabled"])

    def test_disable(self):
        """Test disable command."""
        with self._patch_learning_dir():
            # First enable
            self.runner.invoke(learn_app, ["enable"])

            # Then disable
            result = self.runner.invoke(learn_app, ["disable"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("DISABLED", result.output)

            # Check config was updated
            config_path = self.learning_dir / "config.json"
            with open(config_path) as f:
                config = json.load(f)
            self.assertFalse(config["enabled"])

    def test_status(self):
        """Test status command."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["status"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Learning Status", result.output)
            self.assertIn("Enabled:", result.output)
            self.assertIn("Decay half-life:", result.output)

    def test_status_after_enable(self):
        """Test status shows enabled after enable command."""
        with self._patch_learning_dir():
            self.runner.invoke(learn_app, ["enable"])
            result = self.runner.invoke(learn_app, ["status"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Enabled: True", result.output)

    def test_stats_no_data(self):
        """Test stats with no data."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["stats"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Learning Stats", result.output)

    def test_history_no_data(self):
        """Test history with no data."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["history"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Learning History", result.output)

    def test_history_limit(self):
        """Test history with limit option."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["history", "--limit", "5"])
            self.assertEqual(result.exit_code, 0)

    def test_reset_no_confirm(self):
        """Test reset without confirmation."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["reset", "vm-001"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Run with --confirm to proceed", result.output)

    def test_reset_with_confirm(self):
        """Test reset with confirmation."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["reset", "vm-001", "--confirm"])
            self.assertEqual(result.exit_code, 0)
            # Should say no baseline found since we haven't set one
            self.assertIn("No baseline found", result.output)

    def test_rollback_list(self):
        """Test rollback --list."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["rollback", "--list"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("No snapshots available", result.output)

    def test_rollback_no_confirm(self):
        """Test rollback without confirmation."""
        with self._patch_learning_dir():
            # Create a snapshot first
            from alphaswarm_sol.learning.rollback import VersionManager
            manager = VersionManager(self.learning_dir)
            snapshot_id = manager.create_snapshot("Test", {"vm-001": 0.85})

            result = self.runner.invoke(learn_app, ["rollback", snapshot_id])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Run with --confirm to proceed", result.output)

    def test_rollback_with_confirm(self):
        """Test rollback with confirmation."""
        with self._patch_learning_dir():
            # Create a snapshot first
            from alphaswarm_sol.learning.rollback import VersionManager
            manager = VersionManager(self.learning_dir)
            snapshot_id = manager.create_snapshot("Test", {"vm-001": 0.85})

            result = self.runner.invoke(learn_app, ["rollback", snapshot_id, "--confirm"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Rolled back", result.output)

    def test_rollback_nonexistent(self):
        """Test rollback to nonexistent snapshot."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["rollback", "nonexistent", "--confirm"])
            self.assertNotEqual(result.exit_code, 0)

    def test_snapshot_create(self):
        """Test snapshot creation."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["snapshot", "Test snapshot"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Created snapshot", result.output)

    def test_snapshot_create_baseline(self):
        """Test snapshot creation with baseline flag."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["snapshot", "Baseline snapshot", "--baseline"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("BASELINE", result.output)

    def test_export(self):
        """Test export command."""
        with self._patch_learning_dir():
            export_path = self.learning_dir / "export.json"
            result = self.runner.invoke(learn_app, ["export", str(export_path)])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Exported to", result.output)
            self.assertTrue(export_path.exists())

            # Check export content
            with open(export_path) as f:
                data = json.load(f)
            self.assertIn("events", data)
            self.assertIn("bounds", data)
            self.assertIn("snapshots", data)
            self.assertIn("exported_at", data)

    def test_import_file_not_found(self):
        """Test import with nonexistent file."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["import", "nonexistent.json"])
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("File not found", result.output)

    def test_import_valid_file(self):
        """Test import with valid file."""
        with self._patch_learning_dir():
            # Create a valid export file
            import_path = self.learning_dir / "import.json"
            data = {
                "events": [],
                "bounds": {},
                "snapshots": [],
                "exported_at": "2026-01-08T00:00:00",
            }
            with open(import_path, "w") as f:
                json.dump(data, f)

            result = self.runner.invoke(learn_app, ["import", str(import_path)])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Import complete", result.output)

    def test_overlay_enable_disable(self):
        """Test overlay enable/disable commands."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["overlay", "enable"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Overlay ENABLED", result.output)

            result = self.runner.invoke(learn_app, ["overlay", "disable"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Overlay DISABLED", result.output)

    def test_overlay_status(self):
        """Test overlay status command."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["overlay", "status"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Overlay Status", result.output)

    def test_overlay_export(self):
        """Test overlay export command."""
        with self._patch_learning_dir():
            from alphaswarm_sol.learning.overlay import LearningOverlayStore

            store = LearningOverlayStore(self.learning_dir)
            store.record_label(
                node_id="function:abc",
                label="IS_REENTRANCY_GUARD",
                pattern_id="vm-001",
                bead_id="VKG-0001",
                confidence=0.95,
            )

            export_path = self.learning_dir / "overlay_export.json"
            result = self.runner.invoke(
                learn_app, ["overlay", "export", str(export_path)]
            )
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(export_path.exists())

    def test_import_merge(self):
        """Test import with merge flag."""
        with self._patch_learning_dir():
            # Create a valid export file
            import_path = self.learning_dir / "import.json"
            data = {
                "events": [],
                "bounds": {},
                "snapshots": [],
            }
            with open(import_path, "w") as f:
                json.dump(data, f)

            result = self.runner.invoke(learn_app, ["import", str(import_path), "--merge"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Merging", result.output)

    def test_import_invalid_json(self):
        """Test import with invalid JSON."""
        with self._patch_learning_dir():
            import_path = self.learning_dir / "invalid.json"
            with open(import_path, "w") as f:
                f.write("invalid json {{{")

            result = self.runner.invoke(learn_app, ["import", str(import_path)])
            self.assertNotEqual(result.exit_code, 0)

    def test_alerts_no_alerts(self):
        """Test alerts with no alerts."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["alerts"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("No degradation alerts", result.output)


class TestLearnCLIConfig(unittest.TestCase):
    """Test learning CLI config persistence."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.learning_dir = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _patch_learning_dir(self):
        """Create a patch for DEFAULT_LEARNING_DIR."""
        return patch("alphaswarm_sol.cli.learn._get_learning_dir", return_value=self.learning_dir)

    def test_config_persistence(self):
        """Test config persists across commands."""
        with self._patch_learning_dir():
            # Enable learning
            self.runner.invoke(learn_app, ["enable"])

            # Check status shows enabled
            result = self.runner.invoke(learn_app, ["status"])
            self.assertIn("Enabled: True", result.output)

            # Disable learning
            self.runner.invoke(learn_app, ["disable"])

            # Check status shows disabled
            result = self.runner.invoke(learn_app, ["status"])
            self.assertIn("Enabled: False", result.output)

    def test_default_config_values(self):
        """Test default config values."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["status"])
            self.assertIn("Decay half-life: 30 days", result.output)
            self.assertIn("Auto-rollback threshold: 10%", result.output)


class TestLearnCLISnapshots(unittest.TestCase):
    """Test learning CLI snapshot operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.learning_dir = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _patch_learning_dir(self):
        """Create a patch for DEFAULT_LEARNING_DIR."""
        return patch("alphaswarm_sol.cli.learn._get_learning_dir", return_value=self.learning_dir)

    def test_snapshot_list_after_create(self):
        """Test listing snapshots after creation."""
        with self._patch_learning_dir():
            # Create a snapshot
            self.runner.invoke(learn_app, ["snapshot", "First snapshot"])

            # List snapshots
            result = self.runner.invoke(learn_app, ["rollback", "--list"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Available Snapshots", result.output)
            self.assertIn("First snapshot", result.output)

    def test_snapshot_baseline_marker(self):
        """Test baseline marker in snapshot list."""
        with self._patch_learning_dir():
            # Create a baseline snapshot
            self.runner.invoke(learn_app, ["snapshot", "Baseline", "--baseline"])

            # List snapshots
            result = self.runner.invoke(learn_app, ["rollback", "--list"])
            self.assertIn("BASELINE", result.output)

    def test_rollback_to_baseline(self):
        """Test rollback to baseline when no snapshot_id provided."""
        with self._patch_learning_dir():
            # Create baseline first
            from alphaswarm_sol.learning.rollback import VersionManager
            manager = VersionManager(self.learning_dir)
            manager.create_snapshot("Baseline", {"vm-001": 0.85}, is_baseline=True)

            # Rollback without snapshot_id should use baseline
            result = self.runner.invoke(learn_app, ["rollback", "--confirm"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Rolled back", result.output)

    def test_rollback_no_baseline(self):
        """Test rollback fails gracefully with no baseline."""
        with self._patch_learning_dir():
            result = self.runner.invoke(learn_app, ["rollback", "--confirm"])
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("No baseline snapshot found", result.output)


class TestLearnCLIExportImport(unittest.TestCase):
    """Test learning CLI export/import operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.learning_dir = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _patch_learning_dir(self):
        """Create a patch for DEFAULT_LEARNING_DIR."""
        return patch("alphaswarm_sol.cli.learn._get_learning_dir", return_value=self.learning_dir)

    def test_export_with_snapshots(self):
        """Test export includes snapshots."""
        with self._patch_learning_dir():
            # Create snapshots
            from alphaswarm_sol.learning.rollback import VersionManager
            manager = VersionManager(self.learning_dir)
            manager.create_snapshot("Snap 1", {"vm-001": 0.85})
            manager.create_snapshot("Snap 2", {"vm-001": 0.90})

            # Export
            export_path = self.learning_dir / "export.json"
            result = self.runner.invoke(learn_app, ["export", str(export_path)])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Snapshots: 2", result.output)

    def test_export_reports_counts(self):
        """Test export reports event and pattern counts."""
        with self._patch_learning_dir():
            export_path = self.learning_dir / "export.json"
            result = self.runner.invoke(learn_app, ["export", str(export_path)])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Events:", result.output)
            self.assertIn("Patterns:", result.output)
            self.assertIn("Snapshots:", result.output)


if __name__ == "__main__":
    unittest.main()
