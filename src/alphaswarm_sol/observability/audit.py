"""Structured audit logging with evidence lineage.

This module provides a structured audit logger built on structlog, enabling
category-specific logging methods for compliance, debugging, and governance.

All audit log entries include:
- timestamp: ISO 8601 timestamp
- trace_id: Correlation ID for end-to-end visibility
- pool_id: Pool association for scoped queries
- category: AuditCategory enum value
- event: Specific event type within category

Design Principles:
1. Structured: JSON-formatted logs for machine parsing
2. Correlated: trace_id links logs to OpenTelemetry spans
3. Categorized: Enum-based categories for consistent filtering
4. Provenance: Evidence lineage chains for compliance

Usage:
    from alphaswarm_sol.observability.audit import AuditLogger, AuditCategory

    logger = AuditLogger()
    logger.log_verdict(
        pool_id="pool-123",
        bead_id="VKG-042",
        verdict="vulnerable",
        confidence="LIKELY",
        evidence_refs=["ev-001", "ev-002"],
        agent_type="vrs-attacker",
        trace_id="trace_abc123"
    )
"""

from __future__ import annotations

import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


class AuditCategory(Enum):
    """Audit log categories for filtering and compliance."""

    VERDICT_ASSIGNMENT = "verdict_assignment"
    CONFIDENCE_UPGRADE = "confidence_upgrade"
    EVIDENCE_USAGE = "evidence_usage"
    POLICY_VIOLATION = "policy_violation"
    POOL_LIFECYCLE = "pool_lifecycle"
    COST_TRACKING = "cost_tracking"
    TOOL_EXECUTION = "tool_execution"
    HANDOFF = "handoff"


class AuditLogger:
    """Structured audit logger with evidence lineage.

    Provides category-specific logging methods for AlphaSwarm orchestration.
    All logs are JSON-formatted with consistent schema and trace correlation.

    Attributes:
        logger: Configured structlog logger instance
        log_path: Optional file path for persistent audit logs

    Example:
        logger = AuditLogger()
        logger.log_verdict(
            pool_id="pool-123",
            bead_id="VKG-042",
            verdict="vulnerable",
            confidence="LIKELY",
            evidence_refs=["ev-001"],
            agent_type="vrs-attacker",
            trace_id="trace_abc123"
        )
    """

    def __init__(self, log_path: Optional[Path] = None):
        """Initialize audit logger with structlog configuration.

        Args:
            log_path: Optional file path for persistent audit logs.
                     If not provided, logs to stderr only.
        """
        self.log_path = log_path
        self._configure_structlog()
        self.logger = structlog.get_logger("alphaswarm.audit")

    def _configure_structlog(self) -> None:
        """Configure structlog with JSON processor and timestamp."""
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # If log_path provided, configure file handler
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_verdict(
        self,
        pool_id: str,
        bead_id: str,
        verdict: str,
        confidence: str,
        evidence_refs: List[str],
        agent_type: str,
        trace_id: Optional[str] = None,
    ) -> None:
        """Log verdict assignment with evidence lineage.

        Args:
            pool_id: Pool identifier
            bead_id: Bead identifier
            verdict: Verdict string (e.g., "vulnerable", "safe")
            confidence: Confidence level (e.g., "LIKELY", "CONFIRMED")
            evidence_refs: List of evidence IDs supporting verdict
            agent_type: Agent type that made the verdict (e.g., "vrs-attacker")
            trace_id: Optional trace correlation ID
        """
        self.logger.info(
            "audit.verdict.assigned",
            # Identifiers
            pool_id=pool_id,
            bead_id=bead_id,
            trace_id=trace_id or "none",
            timestamp=datetime.utcnow().isoformat() + "Z",
            # Verdict details
            verdict=verdict,
            confidence=confidence,
            agent_type=agent_type,
            # Evidence lineage
            evidence_refs=evidence_refs,
            evidence_count=len(evidence_refs),
            # Audit metadata
            category=AuditCategory.VERDICT_ASSIGNMENT.value,
            severity="high",
            requires_review=True,
        )

    def log_confidence_upgrade(
        self,
        pool_id: str,
        bead_id: str,
        from_confidence: str,
        to_confidence: str,
        evidence_refs: List[str],
        agent_type: str,
        trace_id: Optional[str] = None,
    ) -> None:
        """Log confidence level upgrade with justification.

        Args:
            pool_id: Pool identifier
            bead_id: Bead identifier
            from_confidence: Previous confidence level
            to_confidence: New confidence level
            evidence_refs: List of evidence IDs justifying upgrade
            agent_type: Agent type that performed upgrade
            trace_id: Optional trace correlation ID
        """
        self.logger.info(
            "audit.confidence.upgraded",
            # Identifiers
            pool_id=pool_id,
            bead_id=bead_id,
            trace_id=trace_id or "none",
            timestamp=datetime.utcnow().isoformat() + "Z",
            # Upgrade details
            from_confidence=from_confidence,
            to_confidence=to_confidence,
            agent_type=agent_type,
            # Evidence justification
            evidence_refs=evidence_refs,
            evidence_count=len(evidence_refs),
            # Audit metadata
            category=AuditCategory.CONFIDENCE_UPGRADE.value,
            severity="high",
            requires_review=True,
        )

    def log_evidence_usage(
        self,
        evidence_id: str,
        source_type: str,  # "bskg", "tool", "manual", "derived"
        source_id: str,
        used_by_agent: str,
        used_in_verdict: str,
        pool_id: str,
        trace_id: Optional[str] = None,
    ) -> None:
        """Log evidence usage for lineage tracking.

        Args:
            evidence_id: Evidence identifier
            source_type: Evidence source type ("bskg", "tool", "manual", "derived")
            source_id: Source identifier (node ID, finding ID, etc.)
            used_by_agent: Agent type that used the evidence
            used_in_verdict: Verdict ID where evidence was used
            pool_id: Pool identifier
            trace_id: Optional trace correlation ID
        """
        self.logger.info(
            "audit.evidence.used",
            # Evidence details
            evidence_id=evidence_id,
            source_type=source_type,
            source_id=source_id,
            # Usage context
            used_by_agent=used_by_agent,
            used_in_verdict=used_in_verdict,
            pool_id=pool_id,
            trace_id=trace_id or "none",
            timestamp=datetime.utcnow().isoformat() + "Z",
            # Audit metadata
            category=AuditCategory.EVIDENCE_USAGE.value,
        )

    def log_policy_violation(
        self,
        pool_id: str,
        policy_id: str,
        violation_type: str,
        actor: str,
        severity: str,  # "critical", "high", "medium", "low"
        suggested_action: str,  # "block", "alert", "sanitize"
        details: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> None:
        """Log policy violation for governance.

        Args:
            pool_id: Pool identifier
            policy_id: Policy identifier (e.g., "cost_budget.hard_limit")
            violation_type: Type of violation (e.g., "budget_exceeded")
            actor: Who/what caused the violation (agent type, "system", etc.)
            severity: Violation severity ("critical", "high", "medium", "low")
            suggested_action: Recommended action ("block", "alert", "sanitize")
            details: Additional violation context
            trace_id: Optional trace correlation ID
        """
        self.logger.warning(
            "audit.policy.violated",
            # Policy details
            policy_id=policy_id,
            violation_type=violation_type,
            severity=severity,
            suggested_action=suggested_action,
            # Actor information
            actor=actor,
            # Context
            pool_id=pool_id,
            trace_id=trace_id or "none",
            timestamp=datetime.utcnow().isoformat() + "Z",
            # Details
            **details,
            # Audit metadata
            category=AuditCategory.POLICY_VIOLATION.value,
            requires_investigation=True,
        )

    def log_pool_event(
        self,
        pool_id: str,
        event_type: str,  # "created", "started", "completed", "failed"
        details: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> None:
        """Log pool lifecycle event.

        Args:
            pool_id: Pool identifier
            event_type: Event type ("created", "started", "completed", "failed")
            details: Additional event context
            trace_id: Optional trace correlation ID
        """
        # Determine log level based on event type
        log_level = "info"
        if event_type == "failed":
            log_level = "error"

        log_method = getattr(self.logger, log_level)
        log_method(
            f"audit.pool.{event_type}",
            # Pool details
            pool_id=pool_id,
            event_type=event_type,
            trace_id=trace_id or "none",
            timestamp=datetime.utcnow().isoformat() + "Z",
            # Details
            **details,
            # Audit metadata
            category=AuditCategory.POOL_LIFECYCLE.value,
        )


__all__ = [
    "AuditCategory",
    "AuditLogger",
]
