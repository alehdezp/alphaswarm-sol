"""Evidence lineage tracking and chain building.

This module provides evidence provenance tracking, enabling auditors to trace
verdicts back to their source evidence (BSKG nodes, tool findings, manual input)
through a complete lineage chain.

Design Principles:
1. Provenance: Every evidence reference tracks source_type and source_id
2. Chain building: Lineage steps record transformations and verifications
3. Queryable: Find all evidence derived from a specific source
4. Compliance-ready: Complete audit trail for decision justification

Usage:
    from alphaswarm_sol.observability.lineage import (
        LineageTracker, SourceType, build_lineage_chain
    )

    tracker = LineageTracker()
    lineage = tracker.create_lineage(
        evidence_id="ev-001",
        source_type=SourceType.BSKG,
        source_id="node_func_vault_123",
        extracting_agent="vrs-attacker"
    )

    # Add transformation
    tracker.add_transformation(
        evidence_id="ev-001",
        transform_type="confidence_upgrade",
        transforming_agent="vrs-verifier",
        metadata={"from": "POSSIBLE", "to": "LIKELY"}
    )

    # Query by source
    derived = tracker.query_by_source(SourceType.BSKG, "node_func_vault_123")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class SourceType(Enum):
    """Evidence source types for lineage tracking."""

    BSKG = "bskg"  # BSKG graph node
    TOOL = "tool"  # External tool finding (Slither, Mythril, etc.)
    MANUAL = "manual"  # Manual input from user
    DERIVED = "derived"  # Derived from other evidence


@dataclass
class LineageStep:
    """Single step in evidence lineage chain.

    Each step represents a transformation, extraction, or verification
    operation on evidence.

    Attributes:
        step_type: Type of operation ("origin", "extraction", "transformation", "verification")
        source_type: Source type for this step
        source_id: Source identifier
        agent: Optional agent that performed the operation
        timestamp: ISO 8601 timestamp when step occurred
        metadata: Additional step-specific metadata
    """

    step_type: str  # "origin", "extraction", "transformation", "verification"
    source_type: SourceType
    source_id: str
    agent: Optional[str]
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "step_type": self.step_type,
            "source_type": self.source_type.value,
            "source_id": self.source_id,
            "agent": self.agent,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LineageStep":
        """Deserialize from dictionary."""
        return cls(
            step_type=data["step_type"],
            source_type=SourceType(data["source_type"]),
            source_id=data["source_id"],
            agent=data.get("agent"),
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class EvidenceLineage:
    """Complete evidence lineage from origin to current state.

    Tracks the full provenance chain for evidence, including:
    - Origin (where evidence came from)
    - Extractions (agents that extracted it)
    - Transformations (modifications, confidence upgrades)
    - Verifications (agents that verified it)

    Attributes:
        evidence_id: Evidence identifier
        current_source_type: Current source type
        current_source_id: Current source identifier
        chain: List of lineage steps in chronological order
        created_at: ISO 8601 timestamp when lineage created
        last_accessed: ISO 8601 timestamp when lineage last accessed
    """

    evidence_id: str
    current_source_type: SourceType
    current_source_id: str
    chain: List[LineageStep]
    created_at: str
    last_accessed: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for logging."""
        return {
            "evidence_id": self.evidence_id,
            "current_source_type": self.current_source_type.value,
            "current_source_id": self.current_source_id,
            "chain": [step.to_dict() for step in self.chain],
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceLineage":
        """Deserialize from dictionary."""
        return cls(
            evidence_id=data["evidence_id"],
            current_source_type=SourceType(data["current_source_type"]),
            current_source_id=data["current_source_id"],
            chain=[LineageStep.from_dict(step) for step in data["chain"]],
            created_at=data["created_at"],
            last_accessed=data["last_accessed"],
        )


class LineageTracker:
    """Track and query evidence lineage.

    Provides in-memory tracking of evidence lineage chains with optional
    persistence to disk for long-term audit trails.

    Attributes:
        _lineages: In-memory cache of evidence lineages
        _storage_path: Optional path for persistent storage

    Example:
        tracker = LineageTracker()

        # Create lineage for BSKG-sourced evidence
        lineage = tracker.create_lineage(
            evidence_id="ev-001",
            source_type=SourceType.BSKG,
            source_id="node_func_vault_withdraw_123",
            extracting_agent="vrs-attacker"
        )

        # Add transformation step
        tracker.add_transformation(
            evidence_id="ev-001",
            transform_type="confidence_upgrade",
            transforming_agent="vrs-verifier",
            metadata={"from": "POSSIBLE", "to": "LIKELY"}
        )

        # Query all evidence from BSKG node
        derived = tracker.query_by_source(
            SourceType.BSKG,
            "node_func_vault_withdraw_123"
        )
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize lineage tracker.

        Args:
            storage_path: Optional path for persistent lineage storage
        """
        self._lineages: Dict[str, EvidenceLineage] = {}
        self._storage_path = storage_path

        if storage_path:
            storage_path.parent.mkdir(parents=True, exist_ok=True)

    def create_lineage(
        self,
        evidence_id: str,
        source_type: SourceType,
        source_id: str,
        extracting_agent: str,
    ) -> EvidenceLineage:
        """Create new lineage for evidence extracted from source.

        Args:
            evidence_id: Evidence identifier
            source_type: Source type (BSKG, TOOL, MANUAL, DERIVED)
            source_id: Source identifier (node ID, finding ID, etc.)
            extracting_agent: Agent that extracted the evidence

        Returns:
            EvidenceLineage with origin and extraction steps
        """
        now = datetime.utcnow().isoformat() + "Z"

        # Create origin step
        origin_step = LineageStep(
            step_type="origin",
            source_type=source_type,
            source_id=source_id,
            agent=None,
            timestamp=now,
            metadata={"origin_type": source_type.value},
        )

        # Create extraction step
        extraction_step = LineageStep(
            step_type="extraction",
            source_type=source_type,
            source_id=source_id,
            agent=extracting_agent,
            timestamp=now,
            metadata={"extracting_agent": extracting_agent},
        )

        lineage = EvidenceLineage(
            evidence_id=evidence_id,
            current_source_type=source_type,
            current_source_id=source_id,
            chain=[origin_step, extraction_step],
            created_at=now,
            last_accessed=now,
        )

        self._lineages[evidence_id] = lineage
        return lineage

    def add_transformation(
        self,
        evidence_id: str,
        transform_type: str,
        transforming_agent: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add transformation step to existing lineage.

        Args:
            evidence_id: Evidence identifier
            transform_type: Type of transformation (e.g., "confidence_upgrade")
            transforming_agent: Agent that performed transformation
            metadata: Optional metadata about transformation

        Raises:
            KeyError: If evidence_id not found in tracker
        """
        if evidence_id not in self._lineages:
            raise KeyError(f"Evidence {evidence_id} not found in lineage tracker")

        lineage = self._lineages[evidence_id]
        now = datetime.utcnow().isoformat() + "Z"

        transform_step = LineageStep(
            step_type="transformation",
            source_type=SourceType.DERIVED,
            source_id=evidence_id,
            agent=transforming_agent,
            timestamp=now,
            metadata={
                "transform_type": transform_type,
                **(metadata or {}),
            },
        )

        lineage.chain.append(transform_step)
        lineage.last_accessed = now
        lineage.current_source_type = SourceType.DERIVED

    def add_verification(
        self,
        evidence_id: str,
        verifying_agent: str,
        verification_result: str,
    ) -> None:
        """Add verification step to lineage.

        Args:
            evidence_id: Evidence identifier
            verifying_agent: Agent that performed verification
            verification_result: Verification outcome (e.g., "confirmed", "rejected")

        Raises:
            KeyError: If evidence_id not found in tracker
        """
        if evidence_id not in self._lineages:
            raise KeyError(f"Evidence {evidence_id} not found in lineage tracker")

        lineage = self._lineages[evidence_id]
        now = datetime.utcnow().isoformat() + "Z"

        verification_step = LineageStep(
            step_type="verification",
            source_type=lineage.current_source_type,
            source_id=lineage.current_source_id,
            agent=verifying_agent,
            timestamp=now,
            metadata={
                "verification_result": verification_result,
                "verifying_agent": verifying_agent,
            },
        )

        lineage.chain.append(verification_step)
        lineage.last_accessed = now

    def get_lineage(self, evidence_id: str) -> Optional[EvidenceLineage]:
        """Get lineage for evidence ID.

        Args:
            evidence_id: Evidence identifier

        Returns:
            EvidenceLineage if found, None otherwise
        """
        lineage = self._lineages.get(evidence_id)
        if lineage:
            lineage.last_accessed = datetime.utcnow().isoformat() + "Z"
        return lineage

    def query_by_source(
        self,
        source_type: SourceType,
        source_id: str,
    ) -> List[EvidenceLineage]:
        """Find all evidence derived from a specific source.

        Args:
            source_type: Source type to query
            source_id: Source identifier to query

        Returns:
            List of EvidenceLineage objects matching the source
        """
        results: List[EvidenceLineage] = []

        for lineage in self._lineages.values():
            # Check if any step in chain matches source
            for step in lineage.chain:
                if step.source_type == source_type and step.source_id == source_id:
                    results.append(lineage)
                    break

        return results

    def build_lineage_chain(self, evidence_id: str) -> List[Dict[str, Any]]:
        """Build full lineage chain for audit logging.

        Args:
            evidence_id: Evidence identifier

        Returns:
            List of lineage step dictionaries in chronological order

        Raises:
            KeyError: If evidence_id not found in tracker
        """
        if evidence_id not in self._lineages:
            raise KeyError(f"Evidence {evidence_id} not found in lineage tracker")

        lineage = self._lineages[evidence_id]
        return [step.to_dict() for step in lineage.chain]


def build_lineage_chain(
    evidence_id: str,
    tracker: LineageTracker,
) -> List[Dict[str, Any]]:
    """Helper function to build lineage chain.

    Args:
        evidence_id: Evidence identifier
        tracker: LineageTracker instance

    Returns:
        List of lineage step dictionaries

    Raises:
        KeyError: If evidence_id not found in tracker
    """
    return tracker.build_lineage_chain(evidence_id)


__all__ = [
    "SourceType",
    "LineageStep",
    "EvidenceLineage",
    "LineageTracker",
    "build_lineage_chain",
]
