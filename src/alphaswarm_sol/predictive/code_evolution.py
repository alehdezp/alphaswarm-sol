"""
Code Evolution Analysis

Tracks how code changes over time and identifies risky patterns:
- Rushed changes (many commits in short time)
- Complexity spikes (sudden increase in complexity)
- Churn hotspots (files changed frequently)
- Developer patterns (single developer, weekend commits)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)


class ChangeVelocity(Enum):
    """Rate of code changes."""
    STABLE = "stable"           # < 5 changes/month
    MODERATE = "moderate"       # 5-15 changes/month
    ACTIVE = "active"           # 15-30 changes/month
    RAPID = "rapid"             # 30-50 changes/month
    FRANTIC = "frantic"         # > 50 changes/month


class ComplexityTrend(Enum):
    """Trend in code complexity."""
    DECREASING = "decreasing"   # Getting simpler
    STABLE = "stable"           # No significant change
    INCREASING = "increasing"   # Getting more complex
    SPIKING = "spiking"         # Sudden major increase


@dataclass
class CodeChange:
    """A single code change record."""
    change_id: str
    timestamp: datetime
    author: str
    files_changed: int
    lines_added: int
    lines_removed: int
    commit_message: Optional[str] = None

    # Derived metrics
    churn: int = 0  # lines_added + lines_removed
    is_weekend: bool = False
    is_night: bool = False  # 10pm - 6am

    def __post_init__(self):
        self.churn = self.lines_added + self.lines_removed
        self.is_weekend = self.timestamp.weekday() >= 5
        hour = self.timestamp.hour
        self.is_night = hour >= 22 or hour < 6

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "timestamp": self.timestamp.isoformat(),
            "author": self.author,
            "files_changed": self.files_changed,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "churn": self.churn,
            "is_weekend": self.is_weekend,
            "is_night": self.is_night,
        }


@dataclass
class FileHotspot:
    """A file that changes frequently."""
    file_path: str
    change_count: int
    total_churn: int
    unique_authors: int
    last_changed: datetime
    risk_score: float = 0.0     # Calculated based on change patterns

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "change_count": self.change_count,
            "total_churn": self.total_churn,
            "unique_authors": self.unique_authors,
            "risk_score": round(self.risk_score, 3),
        }


@dataclass
class ComplexitySnapshot:
    """Complexity measurement at a point in time."""
    timestamp: datetime
    total_functions: int
    avg_cyclomatic: float
    max_cyclomatic: int
    total_lines: int
    external_calls: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_functions": self.total_functions,
            "avg_cyclomatic": round(self.avg_cyclomatic, 2),
            "max_cyclomatic": self.max_cyclomatic,
            "total_lines": self.total_lines,
        }


@dataclass
class EvolutionMetrics:
    """Aggregated code evolution metrics."""
    protocol_id: str

    # Velocity metrics
    velocity: ChangeVelocity = ChangeVelocity.STABLE
    changes_last_7_days: int = 0
    changes_last_30_days: int = 0
    avg_changes_per_month: float = 0.0

    # Complexity metrics
    complexity_trend: ComplexityTrend = ComplexityTrend.STABLE
    complexity_delta_30d: float = 0.0  # % change in avg complexity

    # Churn metrics
    total_churn_30d: int = 0
    hotspot_count: int = 0

    # Developer metrics
    unique_authors_30d: int = 0
    bus_factor: int = 1  # How many devs can be lost

    # Timing red flags
    weekend_changes_pct: float = 0.0
    night_changes_pct: float = 0.0

    # Risk indicators
    rushed_release_detected: bool = False
    complexity_spike_detected: bool = False

    def get_risk_score(self) -> float:
        """Calculate evolution-based risk score."""
        score = 0.0

        # Velocity risk
        velocity_scores = {
            ChangeVelocity.STABLE: 0.0,
            ChangeVelocity.MODERATE: 0.1,
            ChangeVelocity.ACTIVE: 0.2,
            ChangeVelocity.RAPID: 0.4,
            ChangeVelocity.FRANTIC: 0.6,
        }
        score += velocity_scores[self.velocity]

        # Complexity trend risk
        if self.complexity_trend == ComplexityTrend.SPIKING:
            score += 0.3
        elif self.complexity_trend == ComplexityTrend.INCREASING:
            score += 0.1

        # Bus factor risk
        if self.bus_factor == 1:
            score += 0.2
        elif self.bus_factor == 2:
            score += 0.1

        # Rushed release risk
        if self.rushed_release_detected:
            score += 0.3

        # Weekend/night changes (may indicate pressure)
        if self.weekend_changes_pct > 0.3:
            score += 0.1
        if self.night_changes_pct > 0.2:
            score += 0.1

        return min(1.0, score)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "velocity": self.velocity.value,
            "changes_last_7_days": self.changes_last_7_days,
            "changes_last_30_days": self.changes_last_30_days,
            "complexity_trend": self.complexity_trend.value,
            "complexity_delta_30d": round(self.complexity_delta_30d, 2),
            "total_churn_30d": self.total_churn_30d,
            "hotspot_count": self.hotspot_count,
            "unique_authors_30d": self.unique_authors_30d,
            "bus_factor": self.bus_factor,
            "weekend_changes_pct": round(self.weekend_changes_pct, 2),
            "night_changes_pct": round(self.night_changes_pct, 2),
            "rushed_release_detected": self.rushed_release_detected,
            "complexity_spike_detected": self.complexity_spike_detected,
            "evolution_risk_score": round(self.get_risk_score(), 3),
        }


class CodeEvolutionAnalyzer:
    """
    Analyzes code evolution patterns to identify risk indicators.
    """

    # Thresholds
    HOTSPOT_THRESHOLD = 5         # Changes to be considered hotspot
    RUSHED_THRESHOLD = 20         # Changes in 7 days = rushed
    COMPLEXITY_SPIKE_PCT = 50     # 50% increase = spike

    def __init__(self):
        self.changes: Dict[str, List[CodeChange]] = {}  # protocol_id -> changes
        self.complexity_history: Dict[str, List[ComplexitySnapshot]] = {}
        self.metrics: Dict[str, EvolutionMetrics] = {}

    def record_change(
        self,
        protocol_id: str,
        author: str,
        files_changed: int,
        lines_added: int,
        lines_removed: int,
        commit_message: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> CodeChange:
        """Record a code change."""
        if protocol_id not in self.changes:
            self.changes[protocol_id] = []

        change = CodeChange(
            change_id=hashlib.sha256(
                f"{protocol_id}:{timestamp or datetime.now()}:{author}".encode()
            ).hexdigest()[:12],
            timestamp=timestamp or datetime.now(),
            author=author,
            files_changed=files_changed,
            lines_added=lines_added,
            lines_removed=lines_removed,
            commit_message=commit_message,
        )

        self.changes[protocol_id].append(change)
        return change

    def record_complexity(
        self,
        protocol_id: str,
        total_functions: int,
        avg_cyclomatic: float,
        max_cyclomatic: int,
        total_lines: int,
        external_calls: int = 0,
        timestamp: Optional[datetime] = None
    ) -> ComplexitySnapshot:
        """Record a complexity snapshot."""
        if protocol_id not in self.complexity_history:
            self.complexity_history[protocol_id] = []

        snapshot = ComplexitySnapshot(
            timestamp=timestamp or datetime.now(),
            total_functions=total_functions,
            avg_cyclomatic=avg_cyclomatic,
            max_cyclomatic=max_cyclomatic,
            total_lines=total_lines,
            external_calls=external_calls,
        )

        self.complexity_history[protocol_id].append(snapshot)
        return snapshot

    def analyze(self, protocol_id: str) -> EvolutionMetrics:
        """Analyze evolution metrics for a protocol."""
        metrics = EvolutionMetrics(protocol_id=protocol_id)

        changes = self.changes.get(protocol_id, [])
        if not changes:
            self.metrics[protocol_id] = metrics
            return metrics

        now = datetime.now()
        cutoff_7d = now - timedelta(days=7)
        cutoff_30d = now - timedelta(days=30)

        # Filter recent changes
        recent_7d = [c for c in changes if c.timestamp >= cutoff_7d]
        recent_30d = [c for c in changes if c.timestamp >= cutoff_30d]

        # Velocity metrics
        metrics.changes_last_7_days = len(recent_7d)
        metrics.changes_last_30_days = len(recent_30d)

        if len(changes) > 0:
            # Calculate average over all time
            first_change = min(c.timestamp for c in changes)
            months = max(1, (now - first_change).days / 30)
            metrics.avg_changes_per_month = len(changes) / months

        # Determine velocity
        metrics.velocity = self._determine_velocity(metrics.changes_last_30_days)

        # Churn metrics
        metrics.total_churn_30d = sum(c.churn for c in recent_30d)

        # Developer metrics
        authors_30d = set(c.author for c in recent_30d)
        metrics.unique_authors_30d = len(authors_30d)

        # Bus factor (based on contribution distribution)
        metrics.bus_factor = self._calculate_bus_factor(recent_30d)

        # Timing patterns
        if recent_30d:
            metrics.weekend_changes_pct = sum(1 for c in recent_30d if c.is_weekend) / len(recent_30d)
            metrics.night_changes_pct = sum(1 for c in recent_30d if c.is_night) / len(recent_30d)

        # Rushed release detection
        metrics.rushed_release_detected = metrics.changes_last_7_days >= self.RUSHED_THRESHOLD

        # Complexity analysis
        snapshots = self.complexity_history.get(protocol_id, [])
        if len(snapshots) >= 2:
            old_snapshot = snapshots[0]
            new_snapshot = snapshots[-1]

            if old_snapshot.avg_cyclomatic > 0:
                delta_pct = (
                    (new_snapshot.avg_cyclomatic - old_snapshot.avg_cyclomatic)
                    / old_snapshot.avg_cyclomatic * 100
                )
                metrics.complexity_delta_30d = delta_pct

                if delta_pct >= self.COMPLEXITY_SPIKE_PCT:
                    metrics.complexity_trend = ComplexityTrend.SPIKING
                    metrics.complexity_spike_detected = True
                elif delta_pct >= 20:
                    metrics.complexity_trend = ComplexityTrend.INCREASING
                elif delta_pct <= -20:
                    metrics.complexity_trend = ComplexityTrend.DECREASING
                else:
                    metrics.complexity_trend = ComplexityTrend.STABLE

        # Hotspot analysis
        metrics.hotspot_count = len(self.find_hotspots(protocol_id))

        self.metrics[protocol_id] = metrics
        return metrics

    def _determine_velocity(self, changes_per_month: int) -> ChangeVelocity:
        """Determine change velocity category."""
        if changes_per_month < 5:
            return ChangeVelocity.STABLE
        elif changes_per_month < 15:
            return ChangeVelocity.MODERATE
        elif changes_per_month < 30:
            return ChangeVelocity.ACTIVE
        elif changes_per_month < 50:
            return ChangeVelocity.RAPID
        else:
            return ChangeVelocity.FRANTIC

    def _calculate_bus_factor(self, changes: List[CodeChange]) -> int:
        """Calculate bus factor from contribution distribution."""
        if not changes:
            return 1

        # Count changes per author
        author_counts: Dict[str, int] = {}
        for c in changes:
            author_counts[c.author] = author_counts.get(c.author, 0) + 1

        if not author_counts:
            return 1

        total = sum(author_counts.values())
        sorted_authors = sorted(author_counts.values(), reverse=True)

        # Bus factor = number of authors needed for 50% of changes
        cumulative = 0
        bus_factor = 0
        for count in sorted_authors:
            cumulative += count
            bus_factor += 1
            if cumulative >= total * 0.5:
                break

        return bus_factor

    def find_hotspots(
        self,
        protocol_id: str,
        threshold: Optional[int] = None
    ) -> List[FileHotspot]:
        """Find frequently changed files."""
        changes = self.changes.get(protocol_id, [])
        if not changes:
            return []

        threshold = threshold or self.HOTSPOT_THRESHOLD

        # Track per-file stats
        file_stats: Dict[str, Dict[str, Any]] = {}

        # This is a simplified version - in production you'd track actual files
        # For now, simulate based on change patterns
        for change in changes:
            # Simulate file distribution
            for i in range(change.files_changed):
                file_path = f"file_{i % 10}.sol"  # Simplified
                if file_path not in file_stats:
                    file_stats[file_path] = {
                        "count": 0,
                        "churn": 0,
                        "authors": set(),
                        "last_changed": change.timestamp,
                    }
                file_stats[file_path]["count"] += 1
                file_stats[file_path]["churn"] += change.churn // max(1, change.files_changed)
                file_stats[file_path]["authors"].add(change.author)
                if change.timestamp > file_stats[file_path]["last_changed"]:
                    file_stats[file_path]["last_changed"] = change.timestamp

        # Convert to hotspots
        hotspots = []
        for path, stats in file_stats.items():
            if stats["count"] >= threshold:
                hotspot = FileHotspot(
                    file_path=path,
                    change_count=stats["count"],
                    total_churn=stats["churn"],
                    unique_authors=len(stats["authors"]),
                    last_changed=stats["last_changed"],
                )
                # Risk score based on frequency and churn
                hotspot.risk_score = min(1.0, (stats["count"] / 20) + (stats["churn"] / 1000))
                hotspots.append(hotspot)

        return sorted(hotspots, key=lambda h: h.risk_score, reverse=True)

    def detect_rushed_release(self, protocol_id: str, window_days: int = 7) -> bool:
        """Detect if there was a rushed release."""
        changes = self.changes.get(protocol_id, [])
        if not changes:
            return False

        now = datetime.now()
        cutoff = now - timedelta(days=window_days)
        recent = [c for c in changes if c.timestamp >= cutoff]

        return len(recent) >= self.RUSHED_THRESHOLD

    def get_metrics(self, protocol_id: str) -> Optional[EvolutionMetrics]:
        """Get cached metrics or analyze."""
        if protocol_id not in self.metrics:
            return self.analyze(protocol_id)
        return self.metrics.get(protocol_id)

    def get_all_risky_protocols(self, risk_threshold: float = 0.5) -> List[str]:
        """Get protocols with high evolution risk."""
        risky = []
        for protocol_id, metrics in self.metrics.items():
            if metrics.get_risk_score() >= risk_threshold:
                risky.append(protocol_id)
        return risky

    def get_statistics(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        total_protocols = len(self.changes)
        total_changes = sum(len(c) for c in self.changes.values())

        if not self.metrics:
            return {
                "total_protocols": total_protocols,
                "total_changes": total_changes,
            }

        risk_scores = [m.get_risk_score() for m in self.metrics.values()]
        rushed = sum(1 for m in self.metrics.values() if m.rushed_release_detected)
        spiking = sum(1 for m in self.metrics.values() if m.complexity_spike_detected)

        return {
            "total_protocols": total_protocols,
            "total_changes": total_changes,
            "avg_risk_score": round(sum(risk_scores) / len(risk_scores), 3) if risk_scores else 0,
            "rushed_releases": rushed,
            "complexity_spikes": spiking,
            "frantic_protocols": sum(
                1 for m in self.metrics.values()
                if m.velocity == ChangeVelocity.FRANTIC
            ),
        }
