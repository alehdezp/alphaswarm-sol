"""Historical storage for metric snapshots.

Task 8.3: Store and query metric history for trend analysis.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

from .types import MetricSnapshot, MetricName


class HistoryStore:
    """Stores and retrieves historical metric snapshots."""

    def __init__(self, storage_path: Path | str):
        """Initialize storage.

        Args:
            storage_path: Directory for storing snapshots
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save(self, snapshot: MetricSnapshot) -> Path:
        """Save a metric snapshot.

        Args:
            snapshot: MetricSnapshot to persist

        Returns:
            Path to saved file
        """
        # Use timestamp for filename (YYYY-MM-DD_HH-MM-SS.json)
        filename = snapshot.timestamp.strftime("%Y-%m-%d_%H-%M-%S.json")
        filepath = self.storage_path / filename

        with open(filepath, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

        return filepath

    def load(self, filepath: Path) -> MetricSnapshot:
        """Load a snapshot from file.

        Args:
            filepath: Path to snapshot file

        Returns:
            Loaded MetricSnapshot
        """
        with open(filepath) as f:
            data = json.load(f)
        return MetricSnapshot.from_dict(data)

    def get_latest(self) -> MetricSnapshot | None:
        """Get the most recent snapshot.

        Returns:
            Most recent MetricSnapshot or None if no history
        """
        snapshots = list(self._iter_snapshots())
        if not snapshots:
            return None
        return snapshots[-1]  # Sorted by timestamp, so last is latest

    def get_history(
        self,
        days: int = 30,
        limit: int | None = None,
    ) -> list[MetricSnapshot]:
        """Get snapshots from the last N days.

        Args:
            days: Number of days to look back
            limit: Maximum number of snapshots to return

        Returns:
            List of MetricSnapshots, oldest first
        """
        cutoff = datetime.now() - timedelta(days=days)
        snapshots = [
            s for s in self._iter_snapshots()
            if s.timestamp >= cutoff
        ]

        if limit:
            snapshots = snapshots[-limit:]

        return snapshots

    def get_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[MetricSnapshot]:
        """Get snapshots within a date range.

        Args:
            start: Start datetime (inclusive)
            end: End datetime (inclusive)

        Returns:
            List of MetricSnapshots in range
        """
        return [
            s for s in self._iter_snapshots()
            if start <= s.timestamp <= end
        ]

    def count(self) -> int:
        """Count total stored snapshots."""
        return sum(1 for _ in self.storage_path.glob("*.json"))

    def cleanup(self, retention_days: int = 90) -> int:
        """Remove snapshots older than retention period.

        Args:
            retention_days: Keep snapshots from last N days

        Returns:
            Number of snapshots removed
        """
        cutoff = datetime.now() - timedelta(days=retention_days)
        removed = 0

        for filepath in self.storage_path.glob("*.json"):
            try:
                snapshot = self.load(filepath)
                if snapshot.timestamp < cutoff:
                    filepath.unlink()
                    removed += 1
            except Exception:
                # Skip malformed files
                pass

        return removed

    def get_metric_trend(
        self,
        metric_name: MetricName,
        days: int = 30,
    ) -> list[tuple[datetime, float]]:
        """Get trend data for a specific metric.

        Args:
            metric_name: The metric to track
            days: Number of days to look back

        Returns:
            List of (timestamp, value) tuples
        """
        history = self.get_history(days=days)
        trend = []

        for snapshot in history:
            if metric_name in snapshot.metrics:
                trend.append((
                    snapshot.timestamp,
                    snapshot.metrics[metric_name].value,
                ))

        return trend

    def get_statistics(
        self,
        metric_name: MetricName,
        days: int = 30,
    ) -> dict[str, float] | None:
        """Calculate statistics for a metric over time.

        Args:
            metric_name: The metric to analyze
            days: Number of days to analyze

        Returns:
            Dict with min, max, avg, latest values or None if no data
        """
        trend = self.get_metric_trend(metric_name, days)
        if not trend:
            return None

        values = [v for _, v in trend]
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1],
            "count": len(values),
        }

    def _iter_snapshots(self) -> Iterator[MetricSnapshot]:
        """Iterate through all snapshots in chronological order."""
        files = sorted(self.storage_path.glob("*.json"))
        for filepath in files:
            try:
                yield self.load(filepath)
            except Exception:
                # Skip malformed files
                pass


def create_history_store(storage_path: Path | str | None = None) -> HistoryStore:
    """Factory function to create history store with default path.

    Args:
        storage_path: Override default path

    Returns:
        HistoryStore instance
    """
    if storage_path is None:
        from ..config import METRICS_CONFIG

        storage_path = Path(METRICS_CONFIG.get("storage_path", ".vrs/metrics")) / "history"

    return HistoryStore(storage_path)
