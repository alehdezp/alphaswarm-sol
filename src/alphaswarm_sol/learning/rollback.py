"""Rollback capability for learning changes.

Task 7.6: Enable manual and automatic rollback of learning changes
when degradation is detected. This is the SAFETY NET for the learning system.

Key concepts:
- LearningSnapshot: Point-in-time capture of learning state
- VersionManager: Create, list, and restore snapshots
- AutoRollback: Automatic rollback when degradation detected
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class LearningSnapshot:
    """A snapshot of learning state.

    Captures the confidence values for all patterns at a point in time,
    allowing rollback if learning degrades performance.

    Attributes:
        snapshot_id: Unique identifier for the snapshot
        timestamp: When the snapshot was created
        description: Human-readable description
        confidence_values: Pattern ID to confidence value mapping
        is_baseline: Whether this is the baseline (protected) snapshot
    """

    snapshot_id: str
    timestamp: datetime
    description: str
    confidence_values: Dict[str, float]
    is_baseline: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "confidence_values": self.confidence_values,
            "is_baseline": self.is_baseline,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningSnapshot":
        """Create from dict."""
        return cls(
            snapshot_id=data["snapshot_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            description=data["description"],
            confidence_values=data.get("confidence_values", {}),
            is_baseline=data.get("is_baseline", False),
            metadata=data.get("metadata", {}),
        )


class VersionManager:
    """Manage learning state versions for rollback.

    Provides snapshot creation, retrieval, and rollback functionality.
    Automatically cleans up old snapshots to prevent storage bloat.
    """

    MAX_SNAPSHOTS = 20  # Keep last 20 non-baseline snapshots

    def __init__(self, storage_path: Path):
        """Initialize version manager.

        Args:
            storage_path: Directory for storing snapshots
        """
        self.storage_path = storage_path
        self.snapshots_dir = storage_path / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self._snapshots: List[LearningSnapshot] = []
        self._load_manifest()

    def create_snapshot(
        self,
        description: str,
        confidence_values: Dict[str, float],
        is_baseline: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new snapshot of learning state.

        Args:
            description: Human-readable description
            confidence_values: Pattern confidence values to store
            is_baseline: Whether this is the baseline snapshot
            metadata: Optional additional data

        Returns:
            Snapshot ID
        """
        # If setting as baseline, unmark existing baseline
        if is_baseline:
            for snap in self._snapshots:
                snap.is_baseline = False

        snapshot_id = f"snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        snapshot = LearningSnapshot(
            snapshot_id=snapshot_id,
            timestamp=datetime.now(),
            description=description,
            confidence_values=confidence_values.copy(),
            is_baseline=is_baseline,
            metadata=metadata or {},
        )

        # Save snapshot data file
        snapshot_file = self.snapshots_dir / f"{snapshot_id}.json"
        with open(snapshot_file, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

        self._snapshots.append(snapshot)
        self._save_manifest()
        self._cleanup_old_snapshots()

        return snapshot_id

    def get_snapshot(self, snapshot_id: str) -> Optional[LearningSnapshot]:
        """Get a specific snapshot.

        Args:
            snapshot_id: ID of snapshot to retrieve

        Returns:
            LearningSnapshot or None if not found
        """
        for snap in self._snapshots:
            if snap.snapshot_id == snapshot_id:
                # Load full data from file
                return self._load_snapshot_data(snap)
        return None

    def get_baseline(self) -> Optional[LearningSnapshot]:
        """Get the baseline snapshot.

        Returns:
            Baseline LearningSnapshot or None
        """
        for snap in self._snapshots:
            if snap.is_baseline:
                return self._load_snapshot_data(snap)
        return None

    def list_snapshots(self) -> List[LearningSnapshot]:
        """List all snapshots (without full confidence data).

        Returns:
            List of LearningSnapshot objects
        """
        return list(self._snapshots)

    def rollback_to(self, snapshot_id: str) -> Dict[str, float]:
        """Rollback to a specific snapshot.

        Args:
            snapshot_id: ID of snapshot to rollback to

        Returns:
            Confidence values from that snapshot

        Raises:
            ValueError: If snapshot not found
        """
        snapshot = self.get_snapshot(snapshot_id)
        if snapshot is None:
            raise ValueError(f"Snapshot not found: {snapshot_id}")

        # Create a rollback record
        self.create_snapshot(
            f"Rollback to {snapshot_id}",
            snapshot.confidence_values,
            metadata={"rollback_from": snapshot_id},
        )

        return snapshot.confidence_values.copy()

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot.

        Args:
            snapshot_id: ID of snapshot to delete

        Returns:
            True if deleted, False if not found

        Note:
            Cannot delete baseline snapshot
        """
        for snap in self._snapshots:
            if snap.snapshot_id == snapshot_id:
                if snap.is_baseline:
                    raise ValueError("Cannot delete baseline snapshot")
                # Remove data file
                snapshot_file = self.snapshots_dir / f"{snapshot_id}.json"
                if snapshot_file.exists():
                    snapshot_file.unlink()
                self._snapshots.remove(snap)
                self._save_manifest()
                return True
        return False

    def get_snapshot_count(self) -> int:
        """Get number of snapshots.

        Returns:
            Snapshot count
        """
        return len(self._snapshots)

    def _load_snapshot_data(self, snapshot: LearningSnapshot) -> LearningSnapshot:
        """Load full snapshot data from file.

        Args:
            snapshot: Snapshot with minimal data

        Returns:
            Snapshot with full confidence_values loaded
        """
        snapshot_file = self.snapshots_dir / f"{snapshot.snapshot_id}.json"
        if snapshot_file.exists():
            try:
                with open(snapshot_file, "r") as f:
                    data = json.load(f)
                    return LearningSnapshot.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass
        # Return the snapshot as-is if file not found or corrupted
        return snapshot

    def _load_manifest(self) -> None:
        """Load snapshot manifest."""
        manifest_file = self.storage_path / "snapshot_manifest.json"
        if not manifest_file.exists():
            return

        try:
            with open(manifest_file, "r") as f:
                data = json.load(f)

            self._snapshots = []
            for item in data.get("snapshots", []):
                self._snapshots.append(
                    LearningSnapshot(
                        snapshot_id=item["snapshot_id"],
                        timestamp=datetime.fromisoformat(item["timestamp"]),
                        description=item["description"],
                        confidence_values={},  # Load on demand
                        is_baseline=item.get("is_baseline", False),
                        metadata=item.get("metadata", {}),
                    )
                )
        except (json.JSONDecodeError, KeyError):
            self._snapshots = []

    def _save_manifest(self) -> None:
        """Save snapshot manifest."""
        manifest_file = self.storage_path / "snapshot_manifest.json"
        data = {
            "snapshots": [
                {
                    "snapshot_id": s.snapshot_id,
                    "timestamp": s.timestamp.isoformat(),
                    "description": s.description,
                    "is_baseline": s.is_baseline,
                    "metadata": s.metadata,
                }
                for s in self._snapshots
            ]
        }
        with open(manifest_file, "w") as f:
            json.dump(data, f, indent=2)

    def _cleanup_old_snapshots(self) -> None:
        """Remove old snapshots beyond limit.

        Keeps baseline and most recent MAX_SNAPSHOTS non-baseline snapshots.
        """
        non_baseline = [s for s in self._snapshots if not s.is_baseline]
        if len(non_baseline) > self.MAX_SNAPSHOTS:
            to_remove = non_baseline[: -self.MAX_SNAPSHOTS]
            for snap in to_remove:
                snapshot_file = self.snapshots_dir / f"{snap.snapshot_id}.json"
                if snapshot_file.exists():
                    snapshot_file.unlink()
                self._snapshots.remove(snap)
            self._save_manifest()


@dataclass
class DegradationAlert:
    """Alert for detected degradation."""

    pattern_id: str
    current_precision: float
    baseline_precision: float
    drop: float
    threshold: float
    rollback_triggered: bool
    timestamp: datetime = field(default_factory=datetime.now)

    def to_message(self) -> str:
        """Format as alert message."""
        lines = [
            f"DEGRADATION DETECTED: Pattern {self.pattern_id}",
            f"  Current precision: {self.current_precision:.1%}",
            f"  Baseline precision: {self.baseline_precision:.1%}",
            f"  Drop: {self.drop:.1%}",
            f"  Threshold: {self.threshold:.1%}",
        ]
        if self.rollback_triggered:
            lines.append("  Action: Automatic rollback triggered")
        else:
            lines.append("  Action: Alert only (below rollback threshold)")
        return "\n".join(lines)


class AutoRollback:
    """Automatic rollback on degradation detection.

    Monitors pattern precision and automatically rolls back to baseline
    when significant degradation is detected.
    """

    def __init__(
        self,
        version_manager: VersionManager,
        degradation_threshold: float = 0.10,
        alert_threshold: float = 0.05,
    ):
        """Initialize auto-rollback.

        Args:
            version_manager: VersionManager for snapshots
            degradation_threshold: Precision drop to trigger rollback (default 10%)
            alert_threshold: Precision drop to trigger alert (default 5%)
        """
        self.version_manager = version_manager
        self.degradation_threshold = degradation_threshold
        self.alert_threshold = alert_threshold
        self._alerts: List[DegradationAlert] = []

    def check_degradation(
        self,
        pattern_id: str,
        current_precision: float,
        auto_rollback: bool = True,
    ) -> Optional[DegradationAlert]:
        """Check if pattern has degraded.

        Args:
            pattern_id: Pattern to check
            current_precision: Current precision value
            auto_rollback: Whether to auto-rollback on degradation

        Returns:
            DegradationAlert if degradation detected, None otherwise
        """
        baseline = self.version_manager.get_baseline()
        if baseline is None:
            return None

        baseline_precision = baseline.confidence_values.get(pattern_id)
        if baseline_precision is None:
            return None

        drop = baseline_precision - current_precision

        # Check for degradation
        if drop > self.alert_threshold:
            rollback_triggered = False

            if drop > self.degradation_threshold and auto_rollback:
                # Trigger rollback
                self.version_manager.rollback_to(baseline.snapshot_id)
                rollback_triggered = True

            alert = DegradationAlert(
                pattern_id=pattern_id,
                current_precision=current_precision,
                baseline_precision=baseline_precision,
                drop=drop,
                threshold=self.degradation_threshold,
                rollback_triggered=rollback_triggered,
            )
            self._alerts.append(alert)
            return alert

        return None

    def get_alerts(self) -> List[DegradationAlert]:
        """Get all recorded alerts.

        Returns:
            List of DegradationAlert objects
        """
        return list(self._alerts)

    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self._alerts = []


def rollback_pattern(
    pattern_id: str,
    snapshot_id: str,
    storage_path: Path,
) -> float:
    """Convenience function to rollback a pattern.

    Args:
        pattern_id: Pattern to rollback
        snapshot_id: Snapshot ID to rollback to
        storage_path: Path to learning storage

    Returns:
        Restored confidence value for the pattern
    """
    manager = VersionManager(storage_path)
    values = manager.rollback_to(snapshot_id)
    return values.get(pattern_id, 0.7)  # Default if not found


def rollback_to_baseline(
    pattern_id: str,
    storage_path: Path,
) -> Optional[float]:
    """Rollback a pattern to baseline.

    Args:
        pattern_id: Pattern to rollback
        storage_path: Path to learning storage

    Returns:
        Restored confidence value, or None if no baseline
    """
    manager = VersionManager(storage_path)
    baseline = manager.get_baseline()
    if baseline is None:
        return None

    values = manager.rollback_to(baseline.snapshot_id)
    return values.get(pattern_id)
