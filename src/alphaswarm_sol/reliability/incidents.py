"""Incident detection and management from SLO violations.

This module provides incident detection and lifecycle management:
- Convert SLO violations into incidents
- Track incident severity and status
- Update incident state through lifecycle
- Generate alerts for incident response

Design Principles:
1. Incidents are created from SLO violations
2. Severity maps to SLOStatus (WARNING -> MEDIUM, VIOLATED -> HIGH)
3. Incidents can be acknowledged, resolved, or closed
4. All state transitions are tracked with timestamps

Example:
    from alphaswarm_sol.reliability.incidents import IncidentDetector
    from alphaswarm_sol.reliability.slo import SLOViolation

    detector = IncidentDetector()

    # Create incident from violation
    incident = detector.detect_from_slo_violations([violation])

    # Update status
    detector.update_incident_status(incident.id, IncidentStatus.ACKNOWLEDGED)

    # Resolve incident
    detector.resolve_incident(incident.id, resolution="Fixed access control")
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IncidentSeverity(str, Enum):
    """Incident severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    """Incident lifecycle status."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class Incident:
    """Incident record from SLO violation.

    Attributes:
        id: Unique incident identifier
        title: Brief incident description
        description: Detailed incident information
        severity: Incident severity level
        status: Current lifecycle status
        slo_id: Which SLO was violated
        affected_pools: Pool IDs affected by this incident
        created_at: When incident was created
        acknowledged_at: When incident was acknowledged
        resolved_at: When incident was resolved
        closed_at: When incident was closed
        resolution: Resolution description
        metadata: Additional incident metadata
    """

    id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    slo_id: str
    affected_pools: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    resolution: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "status": self.status.value,
            "slo_id": self.slo_id,
            "affected_pools": self.affected_pools,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": (
                self.acknowledged_at.isoformat() if self.acknowledged_at else None
            ),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "resolution": self.resolution,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Incident":
        """Create from dictionary."""
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            description=str(data["description"]),
            severity=IncidentSeverity(data["severity"]),
            status=IncidentStatus(data["status"]),
            slo_id=str(data["slo_id"]),
            affected_pools=list(data.get("affected_pools", [])),
            created_at=datetime.fromisoformat(data["created_at"]),
            acknowledged_at=(
                datetime.fromisoformat(data["acknowledged_at"])
                if data.get("acknowledged_at")
                else None
            ),
            resolved_at=(
                datetime.fromisoformat(data["resolved_at"])
                if data.get("resolved_at")
                else None
            ),
            closed_at=(
                datetime.fromisoformat(data["closed_at"])
                if data.get("closed_at")
                else None
            ),
            resolution=data.get("resolution"),
            metadata=dict(data.get("metadata", {})),
        )


class IncidentDetector:
    """Detect and manage incidents from SLO violations.

    Creates incident records from SLO violations and manages their lifecycle.
    Provides incident tracking with status updates and resolution.

    Example:
        detector = IncidentDetector()

        # Detect incidents from violations
        incidents = detector.detect_from_slo_violations(violations)

        # Update incident
        detector.update_incident_status(incident.id, IncidentStatus.INVESTIGATING)

        # Resolve incident
        detector.resolve_incident(incident.id, "Applied rate limiting")
    """

    def __init__(self):
        """Initialize incident detector."""
        self._incidents: Dict[str, Incident] = {}

    def detect_from_slo_violations(
        self, violations: List["SLOViolation"]
    ) -> List[Incident]:
        """Create incidents from SLO violations.

        Args:
            violations: List of SLO violations

        Returns:
            List of created incidents
        """
        from .slo import SLOStatus

        incidents = []

        for violation in violations:
            # Map SLO status to incident severity
            if violation.status == SLOStatus.WARNING:
                severity = IncidentSeverity.MEDIUM
            elif violation.status == SLOStatus.VIOLATED:
                severity = IncidentSeverity.HIGH
            else:
                continue  # Skip healthy status

            # Create incident
            incident = Incident(
                id=str(uuid.uuid4()),
                title=f"SLO Violation: {violation.slo_id}",
                description=violation.message,
                severity=severity,
                status=IncidentStatus.OPEN,
                slo_id=violation.slo_id,
                affected_pools=violation.affected_pools.copy(),
                metadata={
                    "measured_value": violation.measured_value,
                    "target": violation.target,
                    "alert_threshold": violation.alert_threshold,
                    "violation_timestamp": violation.timestamp.isoformat(),
                },
            )

            self._incidents[incident.id] = incident
            incidents.append(incident)

            logger.info(
                f"Created incident {incident.id} from {violation.slo_id} violation"
            )

        return incidents

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get incident by ID.

        Args:
            incident_id: Incident identifier

        Returns:
            Incident if found, None otherwise
        """
        return self._incidents.get(incident_id)

    def list_incidents(
        self,
        status: Optional[IncidentStatus] = None,
        severity: Optional[IncidentSeverity] = None,
        slo_id: Optional[str] = None,
    ) -> List[Incident]:
        """List incidents with optional filters.

        Args:
            status: Optional filter by status
            severity: Optional filter by severity
            slo_id: Optional filter by SLO ID

        Returns:
            List of incidents matching filters
        """
        incidents = list(self._incidents.values())

        if status:
            incidents = [i for i in incidents if i.status == status]
        if severity:
            incidents = [i for i in incidents if i.severity == severity]
        if slo_id:
            incidents = [i for i in incidents if i.slo_id == slo_id]

        return incidents

    def update_incident_status(
        self, incident_id: str, status: IncidentStatus
    ) -> Optional[Incident]:
        """Update incident status.

        Args:
            incident_id: Incident identifier
            status: New status

        Returns:
            Updated incident if found, None otherwise
        """
        incident = self._incidents.get(incident_id)
        if incident is None:
            logger.warning(f"Incident {incident_id} not found")
            return None

        incident.status = status

        # Update timestamps
        if status == IncidentStatus.ACKNOWLEDGED and incident.acknowledged_at is None:
            incident.acknowledged_at = datetime.now()
        elif status == IncidentStatus.RESOLVED and incident.resolved_at is None:
            incident.resolved_at = datetime.now()
        elif status == IncidentStatus.CLOSED and incident.closed_at is None:
            incident.closed_at = datetime.now()

        logger.info(f"Updated incident {incident_id} status to {status.value}")
        return incident

    def resolve_incident(
        self, incident_id: str, resolution: str
    ) -> Optional[Incident]:
        """Resolve an incident.

        Args:
            incident_id: Incident identifier
            resolution: Resolution description

        Returns:
            Resolved incident if found, None otherwise
        """
        incident = self._incidents.get(incident_id)
        if incident is None:
            logger.warning(f"Incident {incident_id} not found")
            return None

        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = datetime.now()
        incident.resolution = resolution

        logger.info(f"Resolved incident {incident_id}: {resolution}")
        return incident

    def close_incident(self, incident_id: str) -> Optional[Incident]:
        """Close an incident.

        Args:
            incident_id: Incident identifier

        Returns:
            Closed incident if found, None otherwise
        """
        incident = self._incidents.get(incident_id)
        if incident is None:
            logger.warning(f"Incident {incident_id} not found")
            return None

        incident.status = IncidentStatus.CLOSED
        incident.closed_at = datetime.now()

        logger.info(f"Closed incident {incident_id}")
        return incident


__all__ = [
    "IncidentSeverity",
    "IncidentStatus",
    "Incident",
    "IncidentDetector",
]
