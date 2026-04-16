"""ContextMergeBead - bead for context-merge outputs.

Per 05.5-CONTEXT.md:
- Each bead = one vuln class to investigate
- Contains merged context (protocol + vulndoc)
- Full evidence chain inline in bead
- Created via /vrs-create-bead-context-merge skill
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import yaml

from alphaswarm_sol.agents.context.types import ContextBundle


class ContextBeadStatus(Enum):
    """Status of context-merge bead."""
    PENDING = "pending"  # Created, not yet picked up
    IN_PROGRESS = "in_progress"  # Being processed by vuln-discovery
    COMPLETE = "complete"  # Vuln-discovery finished
    FAILED = "failed"  # Processing failed


@dataclass
class ContextMergeBead:
    """Bead for storing verified context-merge output.

    This bead type is distinct from VulnerabilityBead:
    - VulnerabilityBead = finding to investigate
    - ContextMergeBead = context bundle for vuln-discovery

    Attributes:
        id: Unique bead ID (auto-generated hash)
        vulnerability_class: Category/subcategory being analyzed
        context_bundle: Verified ContextBundle from merge
        protocol_name: Protocol being analyzed
        target_scope: Contracts in scope
        verification_score: Quality score from verifier
        verification_warnings: List of quality warnings
        status: Bead processing status
        created_at: Creation timestamp
        created_by: Agent that created this bead
        pool_id: Pool this bead belongs to
        finding_bead_ids: IDs of finding beads created from this context
        metadata: Additional metadata
    """

    # Identity
    id: str
    vulnerability_class: str
    protocol_name: str

    # Context (embedded inline per 05.5-CONTEXT.md)
    context_bundle: ContextBundle
    target_scope: List[str]

    # Quality tracking
    verification_score: float
    verification_warnings: List[str] = field(default_factory=list)

    # Status
    status: ContextBeadStatus = ContextBeadStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "context-merge-agent"

    # Pool association
    pool_id: Optional[str] = None

    # Downstream tracking
    finding_bead_ids: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def generate_id(vuln_class: str, protocol_name: str, timestamp: datetime) -> str:
        """Generate deterministic bead ID.

        Args:
            vuln_class: Vulnerability class (e.g., "reentrancy/classic")
            protocol_name: Protocol name
            timestamp: Creation timestamp

        Returns:
            Bead ID in format CTX-{hash}
        """
        content = f"{vuln_class}:{protocol_name}:{timestamp.isoformat()}"
        return f"CTX-{hashlib.sha256(content.encode()).hexdigest()[:12]}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "type": "context_merge",  # Distinguish from vulnerability beads
            "vulnerability_class": self.vulnerability_class,
            "protocol_name": self.protocol_name,
            "context_bundle": self.context_bundle.to_dict(),
            "target_scope": self.target_scope,
            "verification_score": self.verification_score,
            "verification_warnings": self.verification_warnings,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "pool_id": self.pool_id,
            "finding_bead_ids": self.finding_bead_ids,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextMergeBead":
        """Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            ContextMergeBead instance
        """
        return cls(
            id=data["id"],
            vulnerability_class=data["vulnerability_class"],
            protocol_name=data["protocol_name"],
            context_bundle=ContextBundle.from_dict(data["context_bundle"]),
            target_scope=data.get("target_scope", []),
            verification_score=data.get("verification_score", 0.0),
            verification_warnings=data.get("verification_warnings", []),
            status=ContextBeadStatus(data.get("status", "pending")),
            created_at=datetime.fromisoformat(data["created_at"]),
            created_by=data.get("created_by", "context-merge-agent"),
            pool_id=data.get("pool_id"),
            finding_bead_ids=data.get("finding_bead_ids", []),
            metadata=data.get("metadata", {}),
        )

    def to_yaml(self) -> str:
        """Serialize to YAML for storage.

        Returns:
            YAML string
        """
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "ContextMergeBead":
        """Deserialize from YAML.

        Args:
            yaml_str: YAML string

        Returns:
            ContextMergeBead instance
        """
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON.

        Args:
            indent: Indentation level for JSON formatting

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def add_finding_bead(self, finding_bead_id: str) -> None:
        """Track finding bead created from this context.

        Args:
            finding_bead_id: ID of the finding bead
        """
        if finding_bead_id not in self.finding_bead_ids:
            self.finding_bead_ids.append(finding_bead_id)

    def mark_complete(self) -> None:
        """Mark context bead as complete."""
        self.status = ContextBeadStatus.COMPLETE

    def mark_failed(self, error: str) -> None:
        """Mark context bead as failed.

        Args:
            error: Error message describing the failure
        """
        self.status = ContextBeadStatus.FAILED
        self.metadata["failure_reason"] = error

    def get_system_prompt(self) -> str:
        """Get system prompt for vuln-discovery agent.

        Returns:
            Formatted system prompt string
        """
        return self.context_bundle.to_system_prompt()

    def get_user_context(self) -> str:
        """Get user context for vuln-discovery agent.

        Returns:
            Formatted user context string
        """
        return self.context_bundle.to_user_context()
