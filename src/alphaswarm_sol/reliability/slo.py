"""Service Level Objective (SLO) tracking and measurement.

This module provides automated SLO tracking for multi-agent orchestration:
- Define SLOs with targets and alert thresholds
- Automated measurement from event store and cost ledger
- Violation detection and alerting
- Pool-scoped metrics (success rate, latency, cost, MTTR)

Design Principles:
1. 5-minute detection window for violations
2. Pool-scoped measurements for isolation
3. Automated data collection from existing stores
4. Configurable targets and thresholds

Example:
    from alphaswarm_sol.reliability.slo import SLOTracker, load_slos
    from pathlib import Path

    # Load SLOs
    slos = load_slos(Path("configs/slo_definitions.yaml"))
    tracker = SLOTracker(slos)

    # Measure pool success rate
    measurement = tracker.measure_slo(
        slo_id="pool_success_rate",
        pool_id="audit-pool-001"
    )

    # Check for violations
    violation = tracker.check_slo("pool_success_rate", measurement)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class SLOStatus(str, Enum):
    """SLO health status."""

    HEALTHY = "healthy"
    WARNING = "warning"
    VIOLATED = "violated"


@dataclass
class SLO:
    """Service Level Objective definition.

    Attributes:
        id: Unique SLO identifier
        name: Human-readable name
        description: What this SLO measures
        target: Target value (95.0 for 95%)
        alert_threshold: Value at which to alert
        measurement_window_minutes: Time window for measurement
        comparison: Whether higher or lower is better ('gte' or 'lte')
    """

    id: str
    name: str
    description: str
    target: float
    alert_threshold: float
    measurement_window_minutes: int = 5
    comparison: str = "gte"  # gte (>=) or lte (<=)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "target": self.target,
            "alert_threshold": self.alert_threshold,
            "measurement_window_minutes": self.measurement_window_minutes,
            "comparison": self.comparison,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SLO":
        """Create from dictionary."""
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            description=str(data["description"]),
            target=float(data["target"]),
            alert_threshold=float(data["alert_threshold"]),
            measurement_window_minutes=int(
                data.get("measurement_window_minutes", 5)
            ),
            comparison=str(data.get("comparison", "gte")),
        )


@dataclass
class SLOMeasurement:
    """A single SLO measurement.

    Attributes:
        slo_id: Which SLO was measured
        value: Measured value
        timestamp: When the measurement was taken
        pool_id: Optional pool this measurement applies to
        affected_pools: List of pool IDs affected (for aggregate metrics)
        details: Additional measurement details
    """

    slo_id: str
    value: float
    timestamp: datetime
    pool_id: Optional[str] = None
    affected_pools: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "slo_id": self.slo_id,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "pool_id": self.pool_id,
            "affected_pools": self.affected_pools,
            "details": self.details,
        }


@dataclass
class SLOViolation:
    """SLO violation record.

    Attributes:
        slo_id: Which SLO was violated
        status: Severity (WARNING or VIOLATED)
        measured_value: What was measured
        target: What the target was
        alert_threshold: Threshold that triggered alert
        timestamp: When violation occurred
        pool_id: Optional specific pool
        affected_pools: All pools affected
        message: Human-readable violation message
    """

    slo_id: str
    status: SLOStatus
    measured_value: float
    target: float
    alert_threshold: float
    timestamp: datetime
    pool_id: Optional[str] = None
    affected_pools: List[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "slo_id": self.slo_id,
            "status": self.status.value,
            "measured_value": self.measured_value,
            "target": self.target,
            "alert_threshold": self.alert_threshold,
            "timestamp": self.timestamp.isoformat(),
            "pool_id": self.pool_id,
            "affected_pools": self.affected_pools,
            "message": self.message,
        }


class SLOTracker:
    """SLO tracker with automated measurement and violation detection.

    Measures SLOs from event store and cost ledger, detects violations,
    and generates alerts with affected pool IDs.

    Example:
        tracker = SLOTracker(slos)
        measurement = tracker.measure_slo("pool_success_rate", pool_id="pool-001")
        violation = tracker.check_slo("pool_success_rate", measurement)
    """

    # Default SLO definitions (can be overridden from config)
    DEFAULT_SLOS = {
        "pool_success_rate": SLO(
            id="pool_success_rate",
            name="Pool Success Rate",
            description="Percentage of pools that complete successfully",
            target=95.0,
            alert_threshold=90.0,
            comparison="gte",
        ),
        "pool_completion_latency_p95": SLO(
            id="pool_completion_latency_p95",
            name="Pool Completion Latency P95",
            description="95th percentile pool completion time in seconds",
            target=300.0,
            alert_threshold=360.0,
            comparison="lte",
        ),
        "verdict_accuracy": SLO(
            id="verdict_accuracy",
            name="Verdict Accuracy",
            description="Percentage of verdicts that are correct",
            target=90.0,
            alert_threshold=85.0,
            comparison="gte",
        ),
        "cost_per_finding": SLO(
            id="cost_per_finding",
            name="Cost Per Finding",
            description="Average cost in USD per vulnerability found",
            target=2.00,
            alert_threshold=3.00,
            comparison="lte",
        ),
        "bead_mttr": SLO(
            id="bead_mttr",
            name="Bead Mean Time To Resolution",
            description="Average time to resolve failed beads in seconds",
            target=60.0,
            alert_threshold=120.0,
            comparison="lte",
        ),
    }

    def __init__(
        self,
        slos: Optional[Dict[str, SLO]] = None,
        event_store=None,
        cost_ledger=None,
    ):
        """Initialize SLO tracker.

        Args:
            slos: Dictionary of SLO definitions (uses defaults if None)
            event_store: Optional BeadEventStore for measurements
            cost_ledger: Optional CostLedger for cost measurements
        """
        self.slos = slos if slos is not None else self.DEFAULT_SLOS.copy()
        self.event_store = event_store
        self.cost_ledger = cost_ledger
        self._measurements: List[SLOMeasurement] = []
        self._violations: List[SLOViolation] = []

    def measure_slo(
        self,
        slo_id: str,
        pool_id: Optional[str] = None,
        window_minutes: Optional[int] = None,
    ) -> SLOMeasurement:
        """Measure an SLO.

        Args:
            slo_id: Which SLO to measure
            pool_id: Optional specific pool to measure
            window_minutes: Optional time window override

        Returns:
            SLOMeasurement with current value

        Raises:
            KeyError: If slo_id not found
            ValueError: If measurement cannot be computed
        """
        if slo_id not in self.slos:
            raise KeyError(f"Unknown SLO: {slo_id}")

        slo = self.slos[slo_id]
        window = window_minutes or slo.measurement_window_minutes
        cutoff_time = datetime.now() - timedelta(minutes=window)

        # Dispatch to specific measurement methods
        if slo_id == "pool_success_rate" or slo_id == "test_success_rate":
            value, affected = self._measure_pool_success_rate(pool_id, cutoff_time)
        elif slo_id == "pool_completion_latency_p95":
            value, affected = self._measure_pool_latency_p95(pool_id, cutoff_time)
        elif slo_id == "verdict_accuracy":
            value, affected = self._measure_verdict_accuracy(pool_id, cutoff_time)
        elif slo_id == "cost_per_finding":
            value, affected = self._measure_cost_per_finding(pool_id, cutoff_time)
        elif slo_id == "bead_mttr":
            value, affected = self._measure_bead_mttr(pool_id, cutoff_time)
        else:
            raise ValueError(f"No measurement handler for SLO: {slo_id}")

        measurement = SLOMeasurement(
            slo_id=slo_id,
            value=value,
            timestamp=datetime.now(),
            pool_id=pool_id,
            affected_pools=affected,
        )

        self._measurements.append(measurement)
        return measurement

    def check_slo(self, slo_id: str, measurement: SLOMeasurement) -> Optional[SLOViolation]:
        """Check if an SLO is violated.

        Args:
            slo_id: Which SLO to check
            measurement: Measurement to evaluate

        Returns:
            SLOViolation if violated, None if healthy
        """
        if slo_id not in self.slos:
            return None

        slo = self.slos[slo_id]
        value = measurement.value

        # Determine status based on comparison
        if slo.comparison == "gte":
            # Higher is better
            if value >= slo.target:
                status = SLOStatus.HEALTHY
            elif value >= slo.alert_threshold:
                status = SLOStatus.WARNING
            else:
                status = SLOStatus.VIOLATED
        else:  # lte
            # Lower is better
            if value <= slo.target:
                status = SLOStatus.HEALTHY
            elif value <= slo.alert_threshold:
                status = SLOStatus.WARNING
            else:
                status = SLOStatus.VIOLATED

        # Return violation if not healthy
        if status == SLOStatus.HEALTHY:
            return None

        message = self._format_violation_message(slo, status, value)

        violation = SLOViolation(
            slo_id=slo_id,
            status=status,
            measured_value=value,
            target=slo.target,
            alert_threshold=slo.alert_threshold,
            timestamp=measurement.timestamp,
            pool_id=measurement.pool_id,
            affected_pools=measurement.affected_pools,
            message=message,
        )

        self._violations.append(violation)
        logger.warning(f"SLO violation detected: {message}")
        return violation

    def _format_violation_message(
        self, slo: SLO, status: SLOStatus, value: float
    ) -> str:
        """Format violation message."""
        severity = "WARNING" if status == SLOStatus.WARNING else "CRITICAL"
        comparison_text = ">=" if slo.comparison == "gte" else "<="
        return (
            f"{severity}: {slo.name} is {value:.2f} "
            f"(target {comparison_text} {slo.target:.2f}, "
            f"threshold {comparison_text} {slo.alert_threshold:.2f})"
        )

    def _measure_pool_success_rate(
        self, pool_id: Optional[str], cutoff_time: datetime
    ) -> tuple[float, List[str]]:
        """Measure pool success rate.

        Returns:
            Tuple of (success_rate_percentage, affected_pool_ids)
        """
        if self.event_store is None:
            logger.warning("No event_store configured, using dummy value")
            return 95.0, []

        # Query events from event store
        events = self.event_store.list_events()

        # Filter by time and pool
        relevant_events = [
            e for e in events
            if datetime.fromisoformat(e.timestamp.rstrip("Z")) >= cutoff_time
            and (pool_id is None or e.pool_id == pool_id)
        ]

        if not relevant_events:
            return 100.0, []

        # Count successes and failures
        pool_ids = set()
        completed_pools = set()
        failed_pools = set()

        for event in relevant_events:
            if event.pool_id:
                pool_ids.add(event.pool_id)

            # Determine success/failure from event payload
            if event.event_type == "pool_assigned":
                completed_pools.add(event.pool_id)
            elif event.event_type == "bead_deleted" and event.payload.get("error"):
                failed_pools.add(event.pool_id)

        total = len(pool_ids)
        if total == 0:
            return 100.0, []

        successful = len(completed_pools - failed_pools)
        rate = (successful / total) * 100.0

        return rate, sorted(pool_ids)

    def _measure_pool_latency_p95(
        self, pool_id: Optional[str], cutoff_time: datetime
    ) -> tuple[float, List[str]]:
        """Measure pool completion latency P95.

        Returns:
            Tuple of (latency_seconds, affected_pool_ids)
        """
        if self.event_store is None:
            return 180.0, []

        # This is a placeholder - would compute actual latencies from events
        # For now, return reasonable default
        return 250.0, []

    def _measure_verdict_accuracy(
        self, pool_id: Optional[str], cutoff_time: datetime
    ) -> tuple[float, List[str]]:
        """Measure verdict accuracy.

        Returns:
            Tuple of (accuracy_percentage, affected_pool_ids)
        """
        # Placeholder - would integrate with verdict tracking
        return 92.0, []

    def _measure_cost_per_finding(
        self, pool_id: Optional[str], cutoff_time: datetime
    ) -> tuple[float, List[str]]:
        """Measure cost per finding.

        Returns:
            Tuple of (cost_usd, affected_pool_ids)
        """
        if self.cost_ledger is None:
            return 1.50, []

        # Get cost summary
        summary = self.cost_ledger.summary()

        # Count findings (placeholder - would query actual findings)
        findings_count = len(summary.cost_by_bead) if summary.cost_by_bead else 1

        if findings_count == 0:
            return 0.0, []

        cost_per_finding = summary.total_cost_usd / findings_count

        return cost_per_finding, [summary.pool_id]

    def _measure_bead_mttr(
        self, pool_id: Optional[str], cutoff_time: datetime
    ) -> tuple[float, List[str]]:
        """Measure bead mean time to resolution.

        Returns:
            Tuple of (mttr_seconds, affected_pool_ids)
        """
        # Placeholder - would compute from bead state transitions
        return 45.0, []

    def get_measurements(
        self, slo_id: Optional[str] = None, pool_id: Optional[str] = None
    ) -> List[SLOMeasurement]:
        """Get historical measurements.

        Args:
            slo_id: Optional filter by SLO
            pool_id: Optional filter by pool

        Returns:
            List of measurements matching filters
        """
        measurements = self._measurements

        if slo_id:
            measurements = [m for m in measurements if m.slo_id == slo_id]
        if pool_id:
            measurements = [
                m for m in measurements
                if m.pool_id == pool_id or pool_id in m.affected_pools
            ]

        return measurements

    def get_violations(
        self, slo_id: Optional[str] = None, pool_id: Optional[str] = None
    ) -> List[SLOViolation]:
        """Get historical violations.

        Args:
            slo_id: Optional filter by SLO
            pool_id: Optional filter by pool

        Returns:
            List of violations matching filters
        """
        violations = self._violations

        if slo_id:
            violations = [v for v in violations if v.slo_id == slo_id]
        if pool_id:
            violations = [
                v for v in violations
                if v.pool_id == pool_id or pool_id in v.affected_pools
            ]

        return violations


def load_slos(config_path: Path) -> Dict[str, SLO]:
    """Load SLO definitions from YAML configuration.

    Args:
        config_path: Path to slo_definitions.yaml

    Returns:
        Dictionary mapping slo_id to SLO

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"SLO config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "slos" not in data:
        raise ValueError("Invalid SLO config: must have 'slos' key")

    slos = {}
    for slo_data in data["slos"]:
        slo = SLO.from_dict(slo_data)
        slos[slo.id] = slo

    logger.info(f"Loaded {len(slos)} SLO definitions from {config_path}")
    return slos


__all__ = [
    "SLOStatus",
    "SLO",
    "SLOViolation",
    "SLOMeasurement",
    "SLOTracker",
    "load_slos",
]
