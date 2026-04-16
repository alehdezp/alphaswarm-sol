"""Tests for rollback capability.

Task 7.6: Learning state rollback and degradation detection.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from alphaswarm_sol.learning.rollback import (
    LearningSnapshot,
    VersionManager,
    DegradationAlert,
    AutoRollback,
    rollback_pattern,
    rollback_to_baseline,
)


class TestLearningSnapshot(unittest.TestCase):
    """Test LearningSnapshot dataclass."""

    def test_create_basic(self):
        """Create basic snapshot."""
        snapshot = LearningSnapshot(
            snapshot_id="snap-001",
            timestamp=datetime.now(),
            description="Test snapshot",
            confidence_values={"vm-001": 0.85, "auth-003": 0.75},
        )
        self.assertEqual(snapshot.snapshot_id, "snap-001")
        self.assertEqual(snapshot.confidence_values["vm-001"], 0.85)
        self.assertFalse(snapshot.is_baseline)

    def test_baseline_flag(self):
        """Test baseline flag."""
        snapshot = LearningSnapshot(
            snapshot_id="baseline-001",
            timestamp=datetime.now(),
            description="Baseline",
            confidence_values={"vm-001": 0.90},
            is_baseline=True,
        )
        self.assertTrue(snapshot.is_baseline)

    def test_to_dict(self):
        """Convert to dict."""
        snapshot = LearningSnapshot(
            snapshot_id="snap-001",
            timestamp=datetime.now(),
            description="Test",
            confidence_values={"vm-001": 0.85},
            metadata={"source": "test"},
        )
        d = snapshot.to_dict()
        self.assertEqual(d["snapshot_id"], "snap-001")
        self.assertEqual(d["confidence_values"]["vm-001"], 0.85)
        self.assertEqual(d["metadata"]["source"], "test")

    def test_from_dict(self):
        """Create from dict."""
        data = {
            "snapshot_id": "snap-002",
            "timestamp": "2026-01-08T12:00:00",
            "description": "From dict",
            "confidence_values": {"pattern-1": 0.80},
            "is_baseline": True,
            "metadata": {"key": "value"},
        }
        snapshot = LearningSnapshot.from_dict(data)
        self.assertEqual(snapshot.snapshot_id, "snap-002")
        self.assertTrue(snapshot.is_baseline)
        self.assertEqual(snapshot.confidence_values["pattern-1"], 0.80)

    def test_round_trip(self):
        """Dict round-trip preserves data."""
        snapshot = LearningSnapshot(
            snapshot_id="snap-round-trip",
            timestamp=datetime.now(),
            description="Round trip test",
            confidence_values={"p1": 0.75, "p2": 0.85},
            is_baseline=True,
            metadata={"nested": {"key": "value"}},
        )
        restored = LearningSnapshot.from_dict(snapshot.to_dict())
        self.assertEqual(restored.snapshot_id, snapshot.snapshot_id)
        self.assertEqual(restored.confidence_values, snapshot.confidence_values)
        self.assertEqual(restored.is_baseline, snapshot.is_baseline)


class TestVersionManager(unittest.TestCase):
    """Test VersionManager class."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = VersionManager(Path(self.temp_dir))

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_snapshot(self):
        """Create snapshot."""
        values = {"vm-001": 0.85, "auth-003": 0.75}
        snapshot_id = self.manager.create_snapshot("Test snapshot", values)

        self.assertTrue(snapshot_id.startswith("snap_"))
        self.assertEqual(self.manager.get_snapshot_count(), 1)

    def test_retrieve_snapshot(self):
        """Retrieve created snapshot."""
        values = {"vm-001": 0.85}
        snapshot_id = self.manager.create_snapshot("Test", values)

        snapshot = self.manager.get_snapshot(snapshot_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.confidence_values["vm-001"], 0.85)

    def test_create_baseline(self):
        """Create baseline snapshot."""
        values = {"vm-001": 0.90}
        snapshot_id = self.manager.create_snapshot(
            "Baseline", values, is_baseline=True
        )

        baseline = self.manager.get_baseline()
        self.assertIsNotNone(baseline)
        self.assertEqual(baseline.snapshot_id, snapshot_id)
        self.assertTrue(baseline.is_baseline)

    def test_only_one_baseline(self):
        """Only one baseline at a time."""
        self.manager.create_snapshot("First", {"vm-001": 0.80}, is_baseline=True)
        self.manager.create_snapshot("Second", {"vm-001": 0.90}, is_baseline=True)

        # Should have 2 snapshots but only one baseline
        snapshots = self.manager.list_snapshots()
        baselines = [s for s in snapshots if s.is_baseline]
        self.assertEqual(len(baselines), 1)
        self.assertEqual(baselines[0].description, "Second")

    def test_rollback_to_snapshot(self):
        """Rollback to snapshot."""
        original_values = {"vm-001": 0.90, "auth-003": 0.85}
        snapshot_id = self.manager.create_snapshot("Original", original_values)

        restored = self.manager.rollback_to(snapshot_id)
        self.assertEqual(restored["vm-001"], 0.90)
        self.assertEqual(restored["auth-003"], 0.85)

    def test_rollback_creates_record(self):
        """Rollback creates a new snapshot."""
        snapshot_id = self.manager.create_snapshot("Original", {"vm-001": 0.90})
        initial_count = self.manager.get_snapshot_count()

        self.manager.rollback_to(snapshot_id)
        self.assertEqual(self.manager.get_snapshot_count(), initial_count + 1)

    def test_rollback_nonexistent_raises(self):
        """Rollback to nonexistent snapshot raises."""
        with self.assertRaises(ValueError):
            self.manager.rollback_to("nonexistent-snapshot")

    def test_list_snapshots(self):
        """List all snapshots."""
        self.manager.create_snapshot("First", {"p1": 0.80})
        self.manager.create_snapshot("Second", {"p2": 0.85})
        self.manager.create_snapshot("Third", {"p3": 0.90})

        snapshots = self.manager.list_snapshots()
        self.assertEqual(len(snapshots), 3)

    def test_delete_snapshot(self):
        """Delete a snapshot."""
        snapshot_id = self.manager.create_snapshot("Delete me", {"p1": 0.80})

        deleted = self.manager.delete_snapshot(snapshot_id)
        self.assertTrue(deleted)
        self.assertIsNone(self.manager.get_snapshot(snapshot_id))

    def test_cannot_delete_baseline(self):
        """Cannot delete baseline snapshot."""
        snapshot_id = self.manager.create_snapshot(
            "Baseline", {"p1": 0.90}, is_baseline=True
        )

        with self.assertRaises(ValueError):
            self.manager.delete_snapshot(snapshot_id)

    def test_delete_nonexistent_returns_false(self):
        """Delete nonexistent returns False."""
        result = self.manager.delete_snapshot("nonexistent")
        self.assertFalse(result)

    def test_persistence(self):
        """Snapshots persist across manager instances."""
        values = {"vm-001": 0.85}
        snapshot_id = self.manager.create_snapshot(
            "Persistent", values, is_baseline=True
        )

        # Create new manager
        new_manager = VersionManager(Path(self.temp_dir))
        self.assertEqual(new_manager.get_snapshot_count(), 1)

        baseline = new_manager.get_baseline()
        self.assertIsNotNone(baseline)
        self.assertEqual(baseline.confidence_values["vm-001"], 0.85)

    def test_metadata_preserved(self):
        """Metadata is preserved."""
        snapshot_id = self.manager.create_snapshot(
            "With metadata",
            {"p1": 0.85},
            metadata={"source": "test", "count": 42},
        )

        snapshot = self.manager.get_snapshot(snapshot_id)
        self.assertEqual(snapshot.metadata["source"], "test")
        self.assertEqual(snapshot.metadata["count"], 42)


class TestSnapshotCleanup(unittest.TestCase):
    """Test snapshot cleanup functionality."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = VersionManager(Path(self.temp_dir))
        self.manager.MAX_SNAPSHOTS = 5  # Lower for testing

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cleanup_old_snapshots(self):
        """Old snapshots are cleaned up."""
        # Create more than MAX_SNAPSHOTS
        for i in range(8):
            self.manager.create_snapshot(f"Snapshot {i}", {"p1": 0.80 + i * 0.01})

        # Should only have MAX_SNAPSHOTS
        self.assertLessEqual(
            self.manager.get_snapshot_count(),
            self.manager.MAX_SNAPSHOTS,
        )

    def test_baseline_not_cleaned_up(self):
        """Baseline is never cleaned up."""
        self.manager.create_snapshot(
            "Baseline", {"p1": 0.90}, is_baseline=True
        )

        # Create many more snapshots
        for i in range(10):
            self.manager.create_snapshot(f"Snapshot {i}", {"p1": 0.80})

        # Baseline should still exist
        baseline = self.manager.get_baseline()
        self.assertIsNotNone(baseline)


class TestDegradationAlert(unittest.TestCase):
    """Test DegradationAlert dataclass."""

    def test_create_alert(self):
        """Create alert."""
        alert = DegradationAlert(
            pattern_id="vm-001",
            current_precision=0.75,
            baseline_precision=0.90,
            drop=0.15,
            threshold=0.10,
            rollback_triggered=True,
        )
        self.assertEqual(alert.pattern_id, "vm-001")
        self.assertEqual(alert.drop, 0.15)
        self.assertTrue(alert.rollback_triggered)

    def test_to_message(self):
        """Format as message."""
        alert = DegradationAlert(
            pattern_id="vm-001",
            current_precision=0.75,
            baseline_precision=0.90,
            drop=0.15,
            threshold=0.10,
            rollback_triggered=True,
        )
        message = alert.to_message()
        self.assertIn("DEGRADATION", message)
        self.assertIn("vm-001", message)
        self.assertIn("rollback triggered", message.lower())


class TestAutoRollback(unittest.TestCase):
    """Test AutoRollback class."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = VersionManager(Path(self.temp_dir))

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_triggers_on_degradation(self):
        """Triggers on significant degradation."""
        self.manager.create_snapshot(
            "Baseline", {"vm-001": 0.90}, is_baseline=True
        )

        auto = AutoRollback(self.manager, degradation_threshold=0.10)

        # 15% drop - should trigger
        alert = auto.check_degradation("vm-001", 0.75)
        self.assertIsNotNone(alert)
        self.assertTrue(alert.rollback_triggered)

    def test_no_trigger_within_threshold(self):
        """No trigger when within rollback threshold."""
        self.manager.create_snapshot(
            "Baseline", {"vm-001": 0.90}, is_baseline=True
        )

        # Set alert threshold high so small drop doesn't alert
        auto = AutoRollback(
            self.manager,
            degradation_threshold=0.10,
            alert_threshold=0.08,  # Higher than 5%
        )

        # 5% drop - should not trigger alert or rollback
        alert = auto.check_degradation("vm-001", 0.85)
        self.assertIsNone(alert)

        # 9% drop - alerts but no rollback
        alert = auto.check_degradation("vm-001", 0.81)
        self.assertIsNotNone(alert)
        self.assertFalse(alert.rollback_triggered)

    def test_alert_without_rollback(self):
        """Alert triggered but no auto-rollback."""
        self.manager.create_snapshot(
            "Baseline", {"vm-001": 0.90}, is_baseline=True
        )

        auto = AutoRollback(
            self.manager,
            degradation_threshold=0.10,
            alert_threshold=0.05,
        )

        # 7% drop - above alert but below rollback threshold
        alert = auto.check_degradation("vm-001", 0.83, auto_rollback=False)
        self.assertIsNotNone(alert)
        self.assertFalse(alert.rollback_triggered)

    def test_no_baseline_returns_none(self):
        """No alert if no baseline."""
        auto = AutoRollback(self.manager)
        alert = auto.check_degradation("vm-001", 0.75)
        self.assertIsNone(alert)

    def test_pattern_not_in_baseline_returns_none(self):
        """No alert if pattern not in baseline."""
        self.manager.create_snapshot(
            "Baseline", {"other-pattern": 0.90}, is_baseline=True
        )

        auto = AutoRollback(self.manager)
        alert = auto.check_degradation("vm-001", 0.75)
        self.assertIsNone(alert)

    def test_alerts_recorded(self):
        """Alerts are recorded."""
        self.manager.create_snapshot(
            "Baseline", {"vm-001": 0.90}, is_baseline=True
        )

        auto = AutoRollback(self.manager, degradation_threshold=0.10)
        auto.check_degradation("vm-001", 0.75)
        auto.check_degradation("vm-001", 0.70)

        alerts = auto.get_alerts()
        self.assertEqual(len(alerts), 2)

    def test_clear_alerts(self):
        """Clear alerts."""
        self.manager.create_snapshot(
            "Baseline", {"vm-001": 0.90}, is_baseline=True
        )

        auto = AutoRollback(self.manager, degradation_threshold=0.10)
        auto.check_degradation("vm-001", 0.75)
        auto.clear_alerts()

        self.assertEqual(len(auto.get_alerts()), 0)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rollback_pattern(self):
        """rollback_pattern function."""
        manager = VersionManager(self.storage_path)
        snapshot_id = manager.create_snapshot(
            "Test", {"vm-001": 0.85, "auth-003": 0.75}
        )

        value = rollback_pattern("vm-001", snapshot_id, self.storage_path)
        self.assertEqual(value, 0.85)

    def test_rollback_pattern_missing_returns_default(self):
        """Missing pattern returns default."""
        manager = VersionManager(self.storage_path)
        snapshot_id = manager.create_snapshot("Test", {"other": 0.90})

        value = rollback_pattern("vm-001", snapshot_id, self.storage_path)
        self.assertEqual(value, 0.7)  # Default

    def test_rollback_to_baseline(self):
        """rollback_to_baseline function."""
        manager = VersionManager(self.storage_path)
        manager.create_snapshot(
            "Baseline", {"vm-001": 0.90}, is_baseline=True
        )

        value = rollback_to_baseline("vm-001", self.storage_path)
        self.assertEqual(value, 0.90)

    def test_rollback_to_baseline_no_baseline(self):
        """No baseline returns None."""
        value = rollback_to_baseline("vm-001", self.storage_path)
        self.assertIsNone(value)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = VersionManager(Path(self.temp_dir))

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_confidence_values(self):
        """Handle empty confidence values."""
        snapshot_id = self.manager.create_snapshot("Empty", {})

        snapshot = self.manager.get_snapshot(snapshot_id)
        self.assertEqual(snapshot.confidence_values, {})

    def test_corrupted_manifest(self):
        """Handle corrupted manifest."""
        # Create valid snapshot
        self.manager.create_snapshot("Test", {"p1": 0.85})

        # Corrupt manifest
        manifest_file = Path(self.temp_dir) / "snapshot_manifest.json"
        with open(manifest_file, "w") as f:
            f.write("invalid json {{{")

        # Should handle gracefully
        new_manager = VersionManager(Path(self.temp_dir))
        self.assertEqual(new_manager.get_snapshot_count(), 0)

    def test_many_patterns(self):
        """Handle many patterns in snapshot."""
        values = {f"pattern-{i}": 0.70 + i * 0.005 for i in range(100)}
        snapshot_id = self.manager.create_snapshot("Many patterns", values)

        snapshot = self.manager.get_snapshot(snapshot_id)
        self.assertEqual(len(snapshot.confidence_values), 100)


if __name__ == "__main__":
    unittest.main()
