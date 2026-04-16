"""Canonical artifact schemas for the orchestration layer.

This module defines the canonical schemas for orchestration artifacts:
- PoolStatus: Status enum for pool lifecycle
- VerdictConfidence: Confidence bucket enum for verdicts
- Scope: Audit scope definition
- EvidenceItem: Single piece of evidence
- EvidencePacket: Collection of evidence for a finding
- DebateClaim: Structured claim from attacker/defender
- DebateRecord: Full debate transcript
- Verdict: Final determination with confidence and evidence
- Pool: Batch container for audit waves (renamed from "convoy")

Design Principles:
1. YAML-first: All schemas serialize to human-readable YAML
2. Evidence-anchored: Claims must reference code locations
3. Human-flagged: All verdicts require human review
4. Deterministic: Same inputs produce same outputs

Usage:
    from alphaswarm_sol.orchestration.schemas import (
        Pool, PoolStatus, Verdict, VerdictConfidence,
        Scope, EvidencePacket, EvidenceItem
    )

    # Create a scope
    scope = Scope(
        files=["contracts/Vault.sol"],
        contracts=["Vault"],
        focus_areas=["reentrancy", "access-control"]
    )

    # Create an evidence packet
    evidence = EvidencePacket(
        finding_id="VKG-042",
        items=[EvidenceItem(
            type="behavioral_signature",
            value="R:bal->X:out->W:bal",
            location="contracts/Vault.sol:142"
        )]
    )

    # Create a verdict
    verdict = Verdict(
        finding_id="VKG-042",
        confidence=VerdictConfidence.LIKELY,
        is_vulnerable=True,
        rationale="External call before state update",
        evidence_packet=evidence
    )

    # Create a pool
    pool = Pool(
        id="audit-wave-erc4626",
        scope=scope,
        bead_ids=["VKG-042", "VKG-043"]
    )
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import yaml


class PoolStatus(Enum):
    """Status of a pool through its lifecycle.

    Lifecycle:
    INTAKE -> CONTEXT -> BEADS -> EXECUTE -> VERIFY -> INTEGRATE -> COMPLETE

    - INTAKE: Initial state, receiving scope
    - CONTEXT: Loading protocol context pack
    - BEADS: Creating beads from targets
    - EXECUTE: Running agent analysis (batch by role)
    - VERIFY: Multi-agent debate and verification
    - INTEGRATE: Merging results to evidence
    - COMPLETE: All phases done
    - FAILED: Error during processing
    - PAUSED: Waiting for human input

    Usage:
        status = PoolStatus.INTAKE
        if scope_received:
            status = PoolStatus.CONTEXT
    """
    INTAKE = "intake"
    CONTEXT = "context"
    BEADS = "beads"
    EXECUTE = "execute"
    VERIFY = "verify"
    INTEGRATE = "integrate"
    COMPLETE = "complete"
    FAILED = "failed"
    PAUSED = "paused"

    @classmethod
    def from_string(cls, value: str) -> "PoolStatus":
        """Create PoolStatus from string, case-insensitive.

        Args:
            value: Status string ("intake", "INTAKE", etc.)

        Returns:
            PoolStatus enum value

        Raises:
            ValueError: If value is not a valid status
        """
        return cls(value.lower().strip())

    def is_terminal(self) -> bool:
        """Check if this is a terminal status (complete or failed)."""
        return self in (PoolStatus.COMPLETE, PoolStatus.FAILED)

    def is_active(self) -> bool:
        """Check if this is an active processing status."""
        return self not in (PoolStatus.COMPLETE, PoolStatus.FAILED, PoolStatus.PAUSED)

    def next_phase(self) -> Optional["PoolStatus"]:
        """Get the next phase in the normal lifecycle.

        Returns:
            Next PoolStatus or None if terminal
        """
        order = [
            PoolStatus.INTAKE,
            PoolStatus.CONTEXT,
            PoolStatus.BEADS,
            PoolStatus.EXECUTE,
            PoolStatus.VERIFY,
            PoolStatus.INTEGRATE,
            PoolStatus.COMPLETE,
        ]
        try:
            idx = order.index(self)
            if idx < len(order) - 1:
                return order[idx + 1]
        except ValueError:
            pass
        return None


class VerdictConfidence(Enum):
    """Confidence bucket for verdicts.

    Based on PHILOSOPHY.md requirements:
    - CONFIRMED: Test passes OR multi-agent consensus with strong evidence
    - LIKELY: Strong behavioral signature, no contradicting evidence
    - UNCERTAIN: Conflicting evidence OR missing context
    - REJECTED: Proven false positive

    Usage:
        confidence = VerdictConfidence.LIKELY
        if test_passed:
            confidence = VerdictConfidence.CONFIRMED
    """
    CONFIRMED = "confirmed"
    LIKELY = "likely"
    UNCERTAIN = "uncertain"
    REJECTED = "rejected"

    @classmethod
    def from_string(cls, value: str) -> "VerdictConfidence":
        """Create VerdictConfidence from string, case-insensitive.

        Args:
            value: Confidence string ("confirmed", "LIKELY", etc.)

        Returns:
            VerdictConfidence enum value

        Raises:
            ValueError: If value is not a valid confidence
        """
        return cls(value.lower().strip())

    def is_positive(self) -> bool:
        """Check if this represents a positive finding (vulnerable)."""
        return self in (VerdictConfidence.CONFIRMED, VerdictConfidence.LIKELY)

    def requires_human_review(self) -> bool:
        """Check if this confidence level requires human review.

        Per PHILOSOPHY.md, all verdicts require human review.
        """
        return True  # Always True per design


@dataclass
class Scope:
    """Audit scope definition.

    Defines what should be audited: files, contracts, and focus areas.

    Attributes:
        files: List of file paths to audit
        contracts: List of contract names to focus on
        focus_areas: Vulnerability categories to prioritize
        exclude_patterns: Glob patterns to exclude
        metadata: Additional scope metadata

    Usage:
        scope = Scope(
            files=["contracts/Vault.sol", "contracts/Token.sol"],
            contracts=["Vault", "VaultFactory"],
            focus_areas=["reentrancy", "access-control"]
        )
    """
    files: List[str]
    contracts: List[str] = field(default_factory=list)
    focus_areas: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "files": self.files,
            "contracts": self.contracts,
            "focus_areas": self.focus_areas,
            "exclude_patterns": self.exclude_patterns,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scope":
        """Create Scope from dictionary."""
        return cls(
            files=list(data.get("files", [])),
            contracts=list(data.get("contracts", [])),
            focus_areas=list(data.get("focus_areas", [])),
            exclude_patterns=list(data.get("exclude_patterns", [])),
            metadata=dict(data.get("metadata", {})),
        )

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "Scope":
        """Create Scope from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)

    def matches_file(self, file_path: str) -> bool:
        """Check if a file path is within scope."""
        # Direct match
        if file_path in self.files:
            return True
        # Check exclude patterns
        import fnmatch
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return False
        # Check if any scope file is a prefix (directory scope)
        for scope_file in self.files:
            if file_path.startswith(scope_file.rstrip("/") + "/"):
                return True
            if scope_file.endswith("/") and file_path.startswith(scope_file):
                return True
        return False


@dataclass
class EvidenceItem:
    """Single piece of evidence supporting a finding.

    Evidence items are the atomic units of proof. Each item has:
    - A type describing what kind of evidence it is
    - The actual value/content
    - A code location where the evidence was found

    Attributes:
        type: Type of evidence (behavioral_signature, code_pattern, etc.)
        value: The evidence content
        location: Code location (file:line format)
        confidence: How reliable this evidence is (0.0-1.0)
        source: Where this evidence came from (vkg, attacker, defender, etc.)

    Usage:
        evidence = EvidenceItem(
            type="behavioral_signature",
            value="R:bal->X:out->W:bal",
            location="contracts/Vault.sol:142",
            confidence=0.95,
            source="vkg"
        )
    """
    type: str
    value: str
    location: str
    confidence: float = 1.0
    source: str = "vkg"

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type,
            "value": self.value,
            "location": self.location,
            "confidence": self.confidence,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceItem":
        """Create EvidenceItem from dictionary."""
        return cls(
            type=str(data.get("type", "")),
            value=str(data.get("value", "")),
            location=str(data.get("location", "")),
            confidence=float(data.get("confidence", 1.0)),
            source=str(data.get("source", "vkg")),
        )


@dataclass
class EvidencePacket:
    """Collection of evidence for a finding.

    An evidence packet aggregates all evidence items related to a single
    finding. It provides methods to assess overall strength and coverage.

    Attributes:
        finding_id: ID of the associated finding
        items: List of evidence items
        summary: Optional summary of the evidence
        created_at: When the packet was created
        updated_at: Last update time

    Usage:
        packet = EvidencePacket(
            finding_id="VKG-042",
            items=[
                EvidenceItem(type="signature", value="R:bal->X:out->W:bal", location="Vault.sol:142"),
                EvidenceItem(type="guard_missing", value="no nonReentrant", location="Vault.sol:140"),
            ],
            summary="Reentrancy pattern detected without guard"
        )
    """
    finding_id: str
    items: List[EvidenceItem] = field(default_factory=list)
    summary: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_item(self, item: EvidenceItem) -> None:
        """Add an evidence item to the packet."""
        self.items.append(item)
        self.updated_at = datetime.now()

    def get_by_type(self, evidence_type: str) -> List[EvidenceItem]:
        """Get all items of a specific type."""
        return [item for item in self.items if item.type == evidence_type]

    def get_by_source(self, source: str) -> List[EvidenceItem]:
        """Get all items from a specific source."""
        return [item for item in self.items if item.source == source]

    @property
    def average_confidence(self) -> float:
        """Calculate average confidence across all items."""
        if not self.items:
            return 0.0
        return sum(item.confidence for item in self.items) / len(self.items)

    @property
    def locations(self) -> List[str]:
        """Get unique locations from all items."""
        return list(set(item.location for item in self.items))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "finding_id": self.finding_id,
            "items": [item.to_dict() for item in self.items],
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidencePacket":
        """Create EvidencePacket from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        else:
            updated_at = datetime.now()

        return cls(
            finding_id=str(data.get("finding_id", "")),
            items=[EvidenceItem.from_dict(i) for i in data.get("items", [])],
            summary=str(data.get("summary", "")),
            created_at=created_at,
            updated_at=updated_at,
        )

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "EvidencePacket":
        """Create EvidencePacket from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)


@dataclass
class DebateClaim:
    """Structured claim from an attacker or defender.

    Each claim in the debate must be evidence-anchored with specific
    code locations and reasoning.

    Attributes:
        role: Who made this claim ("attacker" or "defender")
        claim: The main assertion
        evidence: List of evidence items supporting the claim
        reasoning: Explanation of how evidence supports claim
        timestamp: When the claim was made

    Usage:
        claim = DebateClaim(
            role="attacker",
            claim="This function is vulnerable to reentrancy",
            evidence=[EvidenceItem(...)],
            reasoning="External call at L142 happens before balance update at L145"
        )
    """
    role: str  # "attacker" or "defender"
    claim: str
    evidence: List[EvidenceItem]
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "role": self.role,
            "claim": self.claim,
            "evidence": [e.to_dict() for e in self.evidence],
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DebateClaim":
        """Create DebateClaim from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        else:
            timestamp = datetime.now()

        return cls(
            role=str(data.get("role", "")),
            claim=str(data.get("claim", "")),
            evidence=[EvidenceItem.from_dict(e) for e in data.get("evidence", [])],
            reasoning=str(data.get("reasoning", "")),
            timestamp=timestamp,
        )


@dataclass
class DebateRecord:
    """Full debate transcript for a finding.

    Records the structured debate between attacker and defender,
    including rebuttals and the verifier's synthesis.

    Per 04-CONTEXT.md debate protocol:
    1. CLAIM ROUND: Attacker and Defender make initial claims
    2. REBUTTAL ROUND: Each challenges the other's evidence
    3. SYNTHESIS: Verifier weighs evidence and produces verdict

    Attributes:
        finding_id: ID of the finding being debated
        attacker_claim: Initial attacker claim
        defender_claim: Initial defender claim
        rebuttals: List of rebuttal claims
        verifier_summary: Verifier's synthesis of the debate
        dissenting_opinion: Minority view for human review
        started_at: When debate started
        completed_at: When debate completed

    Usage:
        record = DebateRecord(
            finding_id="VKG-042",
            attacker_claim=DebateClaim(role="attacker", ...),
            defender_claim=DebateClaim(role="defender", ...)
        )
    """
    finding_id: str
    attacker_claim: Optional[DebateClaim] = None
    defender_claim: Optional[DebateClaim] = None
    rebuttals: List[DebateClaim] = field(default_factory=list)
    verifier_summary: str = ""
    dissenting_opinion: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def add_rebuttal(self, rebuttal: DebateClaim) -> None:
        """Add a rebuttal to the debate."""
        self.rebuttals.append(rebuttal)

    def complete(self, summary: str, dissent: str = "") -> None:
        """Mark debate as complete with verifier summary."""
        self.verifier_summary = summary
        self.dissenting_opinion = dissent
        self.completed_at = datetime.now()

    @property
    def is_complete(self) -> bool:
        """Check if debate has been completed."""
        return self.completed_at is not None

    @property
    def has_claims(self) -> bool:
        """Check if both sides have made claims."""
        return self.attacker_claim is not None and self.defender_claim is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "finding_id": self.finding_id,
            "attacker_claim": self.attacker_claim.to_dict() if self.attacker_claim else None,
            "defender_claim": self.defender_claim.to_dict() if self.defender_claim else None,
            "rebuttals": [r.to_dict() for r in self.rebuttals],
            "verifier_summary": self.verifier_summary,
            "dissenting_opinion": self.dissenting_opinion,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DebateRecord":
        """Create DebateRecord from dictionary."""
        started_at = data.get("started_at")
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)
        else:
            started_at = datetime.now()

        completed_at = data.get("completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)
        else:
            completed_at = None

        attacker_data = data.get("attacker_claim")
        defender_data = data.get("defender_claim")

        return cls(
            finding_id=str(data.get("finding_id", "")),
            attacker_claim=DebateClaim.from_dict(attacker_data) if attacker_data else None,
            defender_claim=DebateClaim.from_dict(defender_data) if defender_data else None,
            rebuttals=[DebateClaim.from_dict(r) for r in data.get("rebuttals", [])],
            verifier_summary=str(data.get("verifier_summary", "")),
            dissenting_opinion=str(data.get("dissenting_opinion", "")),
            started_at=started_at,
            completed_at=completed_at,
        )

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "DebateRecord":
        """Create DebateRecord from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)


@dataclass
class Verdict:
    """Final determination on a finding.

    A verdict captures the final decision about whether a finding
    represents a real vulnerability, including confidence, evidence,
    and debate transcript.

    Per PHILOSOPHY.md:
    - All verdicts require human review (human_flag always True)
    - Confidence requires evidence (no "likely/confirmed" without proof)
    - Dissenting opinions are preserved

    Attributes:
        finding_id: ID of the finding
        confidence: Confidence bucket
        is_vulnerable: Whether the finding is a real vulnerability
        rationale: Explanation of the verdict
        evidence_packet: Supporting evidence
        debate: Optional debate record
        human_flag: Always True per design
        created_at: When verdict was made
        created_by: Agent/process that created the verdict

    Usage:
        verdict = Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="CEI violation confirmed, no guard present",
            evidence_packet=evidence
        )
    """
    finding_id: str
    confidence: VerdictConfidence
    is_vulnerable: bool
    rationale: str
    evidence_packet: Optional[EvidencePacket] = None
    debate: Optional[DebateRecord] = None
    human_flag: bool = True  # Always True per PHILOSOPHY.md
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "vkg"

    def __post_init__(self) -> None:
        """Validate verdict constraints."""
        # Per PHILOSOPHY.md: no "likely/confirmed" without evidence
        if self.confidence.is_positive() and self.is_vulnerable:
            if not self.evidence_packet or not self.evidence_packet.items:
                if self.confidence == VerdictConfidence.CONFIRMED:
                    raise ValueError("CONFIRMED verdict requires evidence")
                # LIKELY is allowed without evidence but should be flagged
        # Human flag is always true
        self.human_flag = True

    @property
    def requires_action(self) -> bool:
        """Check if this verdict requires human action."""
        return self.is_vulnerable and self.confidence.is_positive()

    @property
    def summary(self) -> str:
        """Get one-line summary of the verdict."""
        status = "VULNERABLE" if self.is_vulnerable else "SAFE"
        return f"{self.finding_id}: {status} ({self.confidence.value})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "finding_id": self.finding_id,
            "confidence": self.confidence.value,
            "is_vulnerable": self.is_vulnerable,
            "rationale": self.rationale,
            "evidence_packet": self.evidence_packet.to_dict() if self.evidence_packet else None,
            "debate": self.debate.to_dict() if self.debate else None,
            "human_flag": self.human_flag,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Verdict":
        """Create Verdict from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()

        evidence_data = data.get("evidence_packet")
        debate_data = data.get("debate")

        # Handle confidence parsing
        confidence = data.get("confidence", "uncertain")
        if isinstance(confidence, str):
            confidence = VerdictConfidence.from_string(confidence)

        return cls(
            finding_id=str(data.get("finding_id", "")),
            confidence=confidence,
            is_vulnerable=bool(data.get("is_vulnerable", False)),
            rationale=str(data.get("rationale", "")),
            evidence_packet=EvidencePacket.from_dict(evidence_data) if evidence_data else None,
            debate=DebateRecord.from_dict(debate_data) if debate_data else None,
            human_flag=True,  # Always True
            created_at=created_at,
            created_by=str(data.get("created_by", "vkg")),
        )

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "Verdict":
        """Create Verdict from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)


@dataclass
class Pool:
    """Batch container for audit waves.

    A Pool groups beads together for batch processing through the
    orchestration pipeline. Named "pool" (not "convoy") per 04-CONTEXT.md.

    Lifecycle:
    INTAKE -> CONTEXT -> BEADS -> EXECUTE -> VERIFY -> INTEGRATE -> COMPLETE

    Attributes:
        id: Unique pool identifier
        scope: What's being audited
        bead_ids: List of bead IDs in this pool
        status: Current lifecycle status
        verdicts: Map of finding_id -> Verdict
        phases_complete: List of completed phases
        metadata: Additional pool metadata
        created_at: When pool was created
        updated_at: Last update time
        initiated_by: What triggered pool creation

    Usage:
        pool = Pool(
            id="audit-wave-erc4626",
            scope=Scope(files=["contracts/Vault.sol"]),
            bead_ids=["VKG-042", "VKG-043"]
        )
        pool.advance_phase()  # INTAKE -> CONTEXT
        pool.add_bead("VKG-044")
        pool.record_verdict(verdict)
    """
    id: str
    scope: Scope
    bead_ids: List[str] = field(default_factory=list)
    status: PoolStatus = PoolStatus.INTAKE
    verdicts: Dict[str, Verdict] = field(default_factory=dict)
    phases_complete: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    initiated_by: str = ""

    def __post_init__(self) -> None:
        """Generate ID if not provided."""
        if not self.id:
            # Generate deterministic ID from scope
            content = str(self.scope.files) + str(self.created_at.isoformat())
            hash_hex = hashlib.sha256(content.encode()).hexdigest()[:12]
            self.id = f"pool-{hash_hex}"

    def add_bead(self, bead_id: str) -> None:
        """Add a bead to the pool.

        Args:
            bead_id: ID of the bead to add
        """
        if bead_id not in self.bead_ids:
            self.bead_ids.append(bead_id)
            self.updated_at = datetime.now()

    def remove_bead(self, bead_id: str) -> bool:
        """Remove a bead from the pool.

        Args:
            bead_id: ID of the bead to remove

        Returns:
            True if removed, False if not found
        """
        if bead_id in self.bead_ids:
            self.bead_ids.remove(bead_id)
            self.updated_at = datetime.now()
            return True
        return False

    def record_verdict(self, verdict: Verdict) -> None:
        """Record a verdict for a finding.

        Args:
            verdict: Verdict to record
        """
        self.verdicts[verdict.finding_id] = verdict
        self.updated_at = datetime.now()

    def get_verdict(self, finding_id: str) -> Optional[Verdict]:
        """Get verdict for a finding.

        Args:
            finding_id: ID of the finding

        Returns:
            Verdict if found, None otherwise
        """
        return self.verdicts.get(finding_id)

    def advance_phase(self) -> bool:
        """Advance to the next phase in the lifecycle.

        Returns:
            True if advanced, False if already terminal
        """
        next_status = self.status.next_phase()
        if next_status:
            self.phases_complete.append(self.status.value)
            self.status = next_status
            self.updated_at = datetime.now()
            return True
        return False

    def set_status(self, status: PoolStatus) -> None:
        """Set pool status directly.

        Args:
            status: New status
        """
        self.status = status
        self.updated_at = datetime.now()

    def fail(self, reason: str = "") -> None:
        """Mark pool as failed.

        Args:
            reason: Failure reason
        """
        self.status = PoolStatus.FAILED
        if reason:
            self.metadata["failure_reason"] = reason
        self.updated_at = datetime.now()

    def pause(self, reason: str = "") -> None:
        """Pause pool for human input.

        Saves current status so it can be restored on resume.

        Args:
            reason: Pause reason
        """
        # Save current status before pausing
        self.metadata["paused_from_status"] = self.status.value
        self.status = PoolStatus.PAUSED
        if reason:
            self.metadata["pause_reason"] = reason
        self.updated_at = datetime.now()

    def resume(self) -> None:
        """Resume pool from paused state.

        Restores to the status that was active when paused, then advances
        to the next phase (completing the paused phase).
        """
        if self.status == PoolStatus.PAUSED:
            # Get the status we were paused from
            paused_from = self.metadata.pop("paused_from_status", None)
            if paused_from:
                # Mark the paused phase as complete and advance
                paused_status = PoolStatus(paused_from)
                self.phases_complete.append(paused_status.value)
                next_phase = paused_status.next_phase()
                if next_phase:
                    self.status = next_phase
                else:
                    # Already at terminal, just restore
                    self.status = paused_status
            elif self.phases_complete:
                # Fallback: use last completed phase
                last_complete = PoolStatus(self.phases_complete[-1])
                next_phase = last_complete.next_phase()
                if next_phase:
                    self.status = next_phase
            else:
                self.status = PoolStatus.INTAKE
            self.metadata.pop("pause_reason", None)
            self.updated_at = datetime.now()

    @property
    def is_complete(self) -> bool:
        """Check if pool processing is complete."""
        return self.status == PoolStatus.COMPLETE

    @property
    def is_failed(self) -> bool:
        """Check if pool has failed."""
        return self.status == PoolStatus.FAILED

    @property
    def is_active(self) -> bool:
        """Check if pool is actively processing."""
        return self.status.is_active()

    @property
    def pending_beads(self) -> List[str]:
        """Get beads without verdicts."""
        return [bid for bid in self.bead_ids if bid not in self.verdicts]

    @property
    def completed_beads(self) -> List[str]:
        """Get beads with verdicts."""
        return [bid for bid in self.bead_ids if bid in self.verdicts]

    @property
    def vulnerable_count(self) -> int:
        """Count of vulnerable findings."""
        return sum(1 for v in self.verdicts.values() if v.is_vulnerable)

    @property
    def confirmed_count(self) -> int:
        """Count of confirmed vulnerable findings."""
        return sum(
            1 for v in self.verdicts.values()
            if v.is_vulnerable and v.confidence == VerdictConfidence.CONFIRMED
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "scope": self.scope.to_dict(),
            "bead_ids": self.bead_ids,
            "status": self.status.value,
            "verdicts": {k: v.to_dict() for k, v in self.verdicts.items()},
            "phases_complete": self.phases_complete,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "initiated_by": self.initiated_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pool":
        """Create Pool from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        else:
            updated_at = datetime.now()

        status = data.get("status", "intake")
        if isinstance(status, str):
            status = PoolStatus.from_string(status)

        verdicts_data = data.get("verdicts", {})
        verdicts = {k: Verdict.from_dict(v) for k, v in verdicts_data.items()}

        return cls(
            id=str(data.get("id", "")),
            scope=Scope.from_dict(data.get("scope", {"files": []})),
            bead_ids=list(data.get("bead_ids", [])),
            status=status,
            verdicts=verdicts,
            phases_complete=list(data.get("phases_complete", [])),
            metadata=dict(data.get("metadata", {})),
            created_at=created_at,
            updated_at=updated_at,
            initiated_by=str(data.get("initiated_by", "")),
        )

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "Pool":
        """Create Pool from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)


# =============================================================================
# Role Contracts - Strict input/output contracts for agent roles
# =============================================================================


class UnknownReason(Enum):
    """Reason why a field or aspect is unknown.

    Used for explicit unknown handling in role contracts.
    """
    MISSING_EVIDENCE = "missing_evidence"
    OUT_OF_SCOPE = "out_of_scope"
    REQUIRES_EXPANSION = "requires_expansion"
    CONFLICTING_SIGNALS = "conflicting_signals"

    @classmethod
    def from_string(cls, value: str) -> "UnknownReason":
        """Create UnknownReason from string, case-insensitive."""
        return cls(value.lower().strip())


@dataclass
class UnknownItem:
    """Explicit unknown declaration.

    Role contracts require explicit unknown handling - this captures what
    is unknown and why.

    Attributes:
        field: The field or aspect that is unknown
        reason: Why this is unknown (from UnknownReason)

    Usage:
        unknown = UnknownItem(
            field="external_call_target",
            reason=UnknownReason.MISSING_EVIDENCE
        )
    """
    field: str
    reason: UnknownReason

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "field": self.field,
            "reason": self.reason.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnknownItem":
        """Create UnknownItem from dictionary."""
        reason = data.get("reason", "missing_evidence")
        if isinstance(reason, str):
            reason = UnknownReason.from_string(reason)
        return cls(
            field=str(data.get("field", "")),
            reason=reason,
        )


class ScoutStatus(Enum):
    """Status of scout hypothesis."""
    CANDIDATE = "candidate"
    NOT_MATCHED = "not_matched"
    UNKNOWN = "unknown"


@dataclass
class ScoutHypothesis:
    """Output contract for Pattern Scout agent.

    Fast pattern triage with evidence references and explicit unknown handling.
    Evidence refs are REQUIRED even if empty to enforce evidence-first thinking.

    Attributes:
        pattern_id: Pattern being evaluated
        status: Triage result (candidate, not_matched, unknown)
        evidence_refs: Evidence supporting the hypothesis (required)
        unknowns: Explicit unknown handling (required)
        confidence: Scout confidence (max 0.70 for Tier B)
        notes: Additional context for verifier

    Usage:
        hypothesis = ScoutHypothesis(
            pattern_id="reentrancy-classic",
            status=ScoutStatus.CANDIDATE,
            evidence_refs=["node:fn:withdraw:123"],
            unknowns=[UnknownItem(field="external_call_target", reason=UnknownReason.MISSING_EVIDENCE)],
            confidence=0.65
        )
    """
    pattern_id: str
    status: ScoutStatus
    evidence_refs: List[str]  # Required, validates evidence ID format
    unknowns: List[UnknownItem]  # Required, explicit unknown handling
    confidence: float = 0.5
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate constraints."""
        # Validate evidence refs format
        import re
        evidence_pattern = re.compile(r"^(node|edge|fn):[a-zA-Z0-9_:-]+$|^EVD-[A-Za-z0-9]+$")
        for ref in self.evidence_refs:
            if not evidence_pattern.match(ref):
                raise ValueError(f"Invalid evidence ref format: {ref}")
        # Confidence cap for Tier B
        if self.confidence > 0.70:
            raise ValueError(f"Scout confidence must be <= 0.70, got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "status": self.status.value,
            "evidence_refs": self.evidence_refs,
            "unknowns": [u.to_dict() for u in self.unknowns],
            "confidence": self.confidence,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScoutHypothesis":
        """Create ScoutHypothesis from dictionary."""
        status = data.get("status", "unknown")
        if isinstance(status, str):
            status = ScoutStatus(status.lower())
        return cls(
            pattern_id=str(data.get("pattern_id", "")),
            status=status,
            evidence_refs=list(data.get("evidence_refs", [])),
            unknowns=[UnknownItem.from_dict(u) for u in data.get("unknowns", [])],
            confidence=float(data.get("confidence", 0.5)),
            notes=str(data.get("notes", "")),
        )


class VerificationStatus(Enum):
    """Status of verification result."""
    MATCHED = "matched"
    NOT_MATCHED = "not_matched"
    UNKNOWN = "unknown"


@dataclass
class VerificationResult:
    """Output contract for Pattern Verifier agent.

    Evidence-first validation with counter-signals and explicit unknowns.

    Attributes:
        pattern_id: Pattern being verified
        status: Verification result
        evidence_refs: Evidence confirming the match (required)
        counter_signals: Guards or anti-patterns that weaken the finding
        unknowns: Explicit unknown handling (required)
        confidence: Verification confidence
        notes: Verification notes

    Usage:
        result = VerificationResult(
            pattern_id="reentrancy-classic",
            status=VerificationStatus.MATCHED,
            evidence_refs=["edge:call:45"],
            counter_signals=["nonReentrant"],
            unknowns=[]
        )
    """
    pattern_id: str
    status: VerificationStatus
    evidence_refs: List[str]
    counter_signals: List[str]
    unknowns: List[UnknownItem]
    confidence: float = 0.7
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate constraints."""
        import re
        evidence_pattern = re.compile(r"^(node|edge|fn):[a-zA-Z0-9_:-]+$|^EVD-[A-Za-z0-9]+$")
        for ref in self.evidence_refs:
            if not evidence_pattern.match(ref):
                raise ValueError(f"Invalid evidence ref format: {ref}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "status": self.status.value,
            "evidence_refs": self.evidence_refs,
            "counter_signals": self.counter_signals,
            "unknowns": [u.to_dict() for u in self.unknowns],
            "confidence": self.confidence,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationResult":
        """Create VerificationResult from dictionary."""
        status = data.get("status", "unknown")
        if isinstance(status, str):
            status = VerificationStatus(status.lower())
        return cls(
            pattern_id=str(data.get("pattern_id", "")),
            status=status,
            evidence_refs=list(data.get("evidence_refs", [])),
            counter_signals=list(data.get("counter_signals", [])),
            unknowns=[UnknownItem.from_dict(u) for u in data.get("unknowns", [])],
            confidence=float(data.get("confidence", 0.7)),
            notes=str(data.get("notes", "")),
        )


class ContradictionStatus(Enum):
    """Status of contradiction report."""
    REFUTED = "refuted"
    CHALLENGED = "challenged"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class CounterargumentType(Enum):
    """Type of counterargument in contradiction report."""
    GUARD_PRESENT = "guard_present"
    ANTI_SIGNAL = "anti_signal"
    SAFE_ORDERING = "safe_ordering"
    ECONOMIC_CONSTRAINT = "economic_constraint"
    MISSING_PRECONDITION = "missing_precondition"


class CounterargumentStrength(Enum):
    """Strength of a counterargument."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


@dataclass
class Counterargument:
    """Evidence-backed counterargument.

    Attributes:
        type: Type of counterargument
        claim: The refutation claim
        evidence_refs: Evidence supporting the counterargument (required)
        strength: Counterargument strength
    """
    type: CounterargumentType
    claim: str
    evidence_refs: List[str]
    strength: CounterargumentStrength

    def __post_init__(self) -> None:
        """Validate evidence refs."""
        import re
        evidence_pattern = re.compile(r"^(node|edge|fn):[a-zA-Z0-9_:-]+$|^EVD-[A-Za-z0-9]+$")
        for ref in self.evidence_refs:
            if not evidence_pattern.match(ref):
                raise ValueError(f"Invalid evidence ref format: {ref}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type.value,
            "claim": self.claim,
            "evidence_refs": self.evidence_refs,
            "strength": self.strength.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Counterargument":
        """Create Counterargument from dictionary."""
        return cls(
            type=CounterargumentType(data.get("type", "guard_present")),
            claim=str(data.get("claim", "")),
            evidence_refs=list(data.get("evidence_refs", [])),
            strength=CounterargumentStrength(data.get("strength", "moderate")),
        )


class ResidualRisk(Enum):
    """Residual risk after refutation."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ContradictionReport:
    """Output contract for Contradiction agent.

    Refutation-only with evidence-backed counterarguments.

    Attributes:
        finding_id: Finding being challenged
        status: Refutation outcome
        counterarguments: Evidence-backed counterarguments (required even if empty)
        confidence: Refutation confidence
        residual_risk: Remaining risk after refutation
        notes: Refutation notes

    Usage:
        report = ContradictionReport(
            finding_id="FND-001",
            status=ContradictionStatus.CHALLENGED,
            counterarguments=[Counterargument(...)],
            confidence=0.75
        )
    """
    finding_id: str
    status: ContradictionStatus
    counterarguments: List[Counterargument]
    confidence: float = 0.5
    residual_risk: ResidualRisk = ResidualRisk.MEDIUM
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate finding_id format."""
        import re
        if not re.match(r"^(FND|AS)-[A-Za-z0-9-]+$", self.finding_id):
            raise ValueError(f"Invalid finding_id format: {self.finding_id}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "finding_id": self.finding_id,
            "status": self.status.value,
            "counterarguments": [c.to_dict() for c in self.counterarguments],
            "confidence": self.confidence,
            "residual_risk": self.residual_risk.value,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContradictionReport":
        """Create ContradictionReport from dictionary."""
        status = data.get("status", "insufficient_evidence")
        if isinstance(status, str):
            status = ContradictionStatus(status.lower())
        residual = data.get("residual_risk", "medium")
        if isinstance(residual, str):
            residual = ResidualRisk(residual.lower())
        return cls(
            finding_id=str(data.get("finding_id", "")),
            status=status,
            counterarguments=[Counterargument.from_dict(c) for c in data.get("counterarguments", [])],
            confidence=float(data.get("confidence", 0.5)),
            residual_risk=residual,
            notes=str(data.get("notes", "")),
        )


class CompositionStatus(Enum):
    """Status of composition proposal."""
    PROPOSED = "proposed"
    INVALID = "invalid"
    DUPLICATE = "duplicate"


@dataclass
class ComposedPattern:
    """A composed pattern from operation-signature algebra.

    Attributes:
        name: Composed pattern name
        operation: Composition operation (e.g., 'A + B', 'A ; B')
        base_patterns: Constituent pattern IDs
        evidence_refs: Evidence supporting the composition (required)
        confidence: Composition confidence (max 0.70 for Tier B)
        signature: Composed behavioral signature
        unknowns: Unknown aspects of the composition
        notes: Composition notes
    """
    name: str
    operation: str
    base_patterns: List[str]
    evidence_refs: List[str]
    confidence: float = 0.5
    signature: str = ""
    unknowns: List[UnknownItem] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate constraints."""
        import re
        evidence_pattern = re.compile(r"^(node|edge|fn):[a-zA-Z0-9_:-]+$|^EVD-[A-Za-z0-9]+$")
        for ref in self.evidence_refs:
            if not evidence_pattern.match(ref):
                raise ValueError(f"Invalid evidence ref format: {ref}")
        if self.confidence > 0.70:
            raise ValueError(f"Composition confidence must be <= 0.70, got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "operation": self.operation,
            "signature": self.signature,
            "base_patterns": self.base_patterns,
            "evidence_refs": self.evidence_refs,
            "confidence": self.confidence,
            "tier": "B",  # Always Tier B for compositions
            "unknowns": [u.to_dict() for u in self.unknowns],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComposedPattern":
        """Create ComposedPattern from dictionary."""
        return cls(
            name=str(data.get("name", "")),
            operation=str(data.get("operation", "")),
            base_patterns=list(data.get("base_patterns", [])),
            evidence_refs=list(data.get("evidence_refs", [])),
            confidence=float(data.get("confidence", 0.5)),
            signature=str(data.get("signature", "")),
            unknowns=[UnknownItem.from_dict(u) for u in data.get("unknowns", [])],
            notes=str(data.get("notes", "")),
        )


@dataclass
class RejectedComposition:
    """A rejected composition with reason."""
    operation: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {"operation": self.operation, "reason": self.reason}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RejectedComposition":
        """Create RejectedComposition from dictionary."""
        return cls(
            operation=str(data.get("operation", "")),
            reason=str(data.get("reason", "")),
        )


@dataclass
class CompositionProposal:
    """Output contract for Pattern Composer agent.

    Operation-signature algebra for composite vulnerabilities.

    Attributes:
        composition_id: Unique composition batch ID
        status: Composition batch status
        compositions: Proposed composed patterns
        rejected: Rejected compositions with reasons

    Usage:
        proposal = CompositionProposal(
            composition_id="COMP-abc123",
            status=CompositionStatus.PROPOSED,
            compositions=[ComposedPattern(...)]
        )
    """
    composition_id: str
    status: CompositionStatus
    compositions: List[ComposedPattern]
    rejected: List[RejectedComposition] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate composition_id format."""
        import re
        if not re.match(r"^COMP-[A-Za-z0-9]+$", self.composition_id):
            raise ValueError(f"Invalid composition_id format: {self.composition_id}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "composition_id": self.composition_id,
            "status": self.status.value,
            "compositions": [c.to_dict() for c in self.compositions],
            "rejected": [r.to_dict() for r in self.rejected],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompositionProposal":
        """Create CompositionProposal from dictionary."""
        status = data.get("status", "proposed")
        if isinstance(status, str):
            status = CompositionStatus(status.lower())
        return cls(
            composition_id=str(data.get("composition_id", "")),
            status=status,
            compositions=[ComposedPattern.from_dict(c) for c in data.get("compositions", [])],
            rejected=[RejectedComposition.from_dict(r) for r in data.get("rejected", [])],
        )


class SynthesisStatus(Enum):
    """Status of synthesis result."""
    SYNTHESIZED = "synthesized"
    CONFLICTED = "conflicted"
    INSUFFICIENT = "insufficient"


class ConflictType(Enum):
    """Type of conflict in synthesis."""
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"
    CONFIDENCE_DISAGREEMENT = "confidence_disagreement"
    SCOPE_OVERLAP = "scope_overlap"
    TEMPORAL_CONFLICT = "temporal_conflict"


class ConflictResolution(Enum):
    """Resolution strategy for conflicts."""
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    USE_CONFIDENCE_BOUNDS = "use_confidence_bounds"
    MERGE_WITH_UNION = "merge_with_union"
    VERIFY_WITH_ORDERING_PROOF = "verify_with_ordering_proof"


@dataclass
class ConfidenceBounds:
    """Confidence bounds from synthesis.

    Attributes:
        lower: Lower confidence bound (pessimistic)
        upper: Upper confidence bound (optimistic)
        method: Method used to compute bounds
    """
    lower: float
    upper: float
    method: str

    def __post_init__(self) -> None:
        """Validate bounds."""
        if not 0.0 <= self.lower <= 1.0:
            raise ValueError(f"Lower bound must be 0-1, got {self.lower}")
        if not 0.0 <= self.upper <= 1.0:
            raise ValueError(f"Upper bound must be 0-1, got {self.upper}")
        if self.lower > self.upper:
            raise ValueError(f"Lower bound ({self.lower}) cannot exceed upper ({self.upper})")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {"lower": self.lower, "upper": self.upper, "method": self.method}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfidenceBounds":
        """Create ConfidenceBounds from dictionary."""
        return cls(
            lower=float(data.get("lower", 0.0)),
            upper=float(data.get("upper", 1.0)),
            method=str(data.get("method", "")),
        )


@dataclass
class SynthesizedCluster:
    """A synthesized finding cluster.

    Attributes:
        cluster_id: Unique cluster ID
        name: Synthesized finding name
        severity: Synthesized severity
        constituent_findings: Finding IDs that were merged
        confidence_bounds: Confidence range from synthesis
        convergent_evidence: Evidence shared across findings
        affected_functions: Functions affected by this cluster
        unknowns: Propagated unknowns
        conflicts: Unresolved conflict IDs
        notes: Synthesis notes
    """
    cluster_id: str
    name: str
    severity: str
    constituent_findings: List[str]
    confidence_bounds: ConfidenceBounds
    convergent_evidence: List[str] = field(default_factory=list)
    affected_functions: List[str] = field(default_factory=list)
    unknowns: List[UnknownItem] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate cluster_id format."""
        import re
        if not re.match(r"^CLU-[A-Za-z0-9]+$", self.cluster_id):
            raise ValueError(f"Invalid cluster_id format: {self.cluster_id}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "cluster_id": self.cluster_id,
            "name": self.name,
            "severity": self.severity,
            "constituent_findings": self.constituent_findings,
            "convergent_evidence": self.convergent_evidence,
            "confidence_bounds": self.confidence_bounds.to_dict(),
            "affected_functions": self.affected_functions,
            "unknowns": [u.to_dict() for u in self.unknowns],
            "conflicts": self.conflicts,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SynthesizedCluster":
        """Create SynthesizedCluster from dictionary."""
        return cls(
            cluster_id=str(data.get("cluster_id", "")),
            name=str(data.get("name", "")),
            severity=str(data.get("severity", "medium")),
            constituent_findings=list(data.get("constituent_findings", [])),
            confidence_bounds=ConfidenceBounds.from_dict(data.get("confidence_bounds", {})),
            convergent_evidence=list(data.get("convergent_evidence", [])),
            affected_functions=list(data.get("affected_functions", [])),
            unknowns=[UnknownItem.from_dict(u) for u in data.get("unknowns", [])],
            conflicts=list(data.get("conflicts", [])),
            notes=str(data.get("notes", "")),
        )


@dataclass
class SynthesisConflict:
    """A conflict detected during synthesis.

    Attributes:
        finding_a: First conflicting finding
        finding_b: Second conflicting finding
        conflict_type: Type of conflict
        description: Conflict description
        resolution: Resolution strategy
    """
    finding_a: str
    finding_b: str
    conflict_type: ConflictType
    resolution: ConflictResolution
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "finding_a": self.finding_a,
            "finding_b": self.finding_b,
            "conflict_type": self.conflict_type.value,
            "description": self.description,
            "resolution": self.resolution.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SynthesisConflict":
        """Create SynthesisConflict from dictionary."""
        return cls(
            finding_a=str(data.get("finding_a", "")),
            finding_b=str(data.get("finding_b", "")),
            conflict_type=ConflictType(data.get("conflict_type", "contradictory_evidence")),
            resolution=ConflictResolution(data.get("resolution", "human_review_required")),
            description=str(data.get("description", "")),
        )


@dataclass
class EvidenceStats:
    """Evidence aggregation statistics."""
    total_evidence_refs: int = 0
    unique_evidence_refs: int = 0
    convergent_refs: int = 0
    orphan_refs: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_evidence_refs": self.total_evidence_refs,
            "unique_evidence_refs": self.unique_evidence_refs,
            "convergent_refs": self.convergent_refs,
            "orphan_refs": self.orphan_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceStats":
        """Create EvidenceStats from dictionary."""
        return cls(
            total_evidence_refs=int(data.get("total_evidence_refs", 0)),
            unique_evidence_refs=int(data.get("unique_evidence_refs", 0)),
            convergent_refs=int(data.get("convergent_refs", 0)),
            orphan_refs=int(data.get("orphan_refs", 0)),
        )


@dataclass
class SynthesizedFinding:
    """Output contract for Finding Synthesizer agent.

    Convergent evidence merging with confidence boundaries.

    Attributes:
        synthesis_id: Unique synthesis batch ID
        status: Synthesis outcome
        synthesized_findings: Merged finding clusters
        conflicts: Unresolved conflicts requiring human review
        evidence_stats: Evidence aggregation statistics

    Usage:
        finding = SynthesizedFinding(
            synthesis_id="SYN-abc123",
            status=SynthesisStatus.SYNTHESIZED,
            synthesized_findings=[SynthesizedCluster(...)]
        )
    """
    synthesis_id: str
    status: SynthesisStatus
    synthesized_findings: List[SynthesizedCluster]
    conflicts: List[SynthesisConflict] = field(default_factory=list)
    evidence_stats: Optional[EvidenceStats] = None

    def __post_init__(self) -> None:
        """Validate synthesis_id format."""
        import re
        if not re.match(r"^SYN-[A-Za-z0-9]+$", self.synthesis_id):
            raise ValueError(f"Invalid synthesis_id format: {self.synthesis_id}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "synthesis_id": self.synthesis_id,
            "status": self.status.value,
            "synthesized_findings": [f.to_dict() for f in self.synthesized_findings],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "evidence_stats": self.evidence_stats.to_dict() if self.evidence_stats else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SynthesizedFinding":
        """Create SynthesizedFinding from dictionary."""
        status = data.get("status", "synthesized")
        if isinstance(status, str):
            status = SynthesisStatus(status.lower())
        stats_data = data.get("evidence_stats")
        return cls(
            synthesis_id=str(data.get("synthesis_id", "")),
            status=status,
            synthesized_findings=[SynthesizedCluster.from_dict(f) for f in data.get("synthesized_findings", [])],
            conflicts=[SynthesisConflict.from_dict(c) for c in data.get("conflicts", [])],
            evidence_stats=EvidenceStats.from_dict(stats_data) if stats_data else None,
        )


# =============================================================================
# Append-Only Delta Schema - Deterministic merge ordering (Phase 5.10-10)
# =============================================================================


class DeltaType(Enum):
    """Type of delta entry in merge pipeline.

    Deltas are immutable entries that track changes to findings.
    """
    FINDING_ADD = "finding_add"
    FINDING_UPDATE = "finding_update"
    EVIDENCE_ADD = "evidence_add"
    CONFIDENCE_CHANGE = "confidence_change"
    VERDICT_ADD = "verdict_add"


@dataclass
class DeltaEntry:
    """Immutable delta entry for append-only merge pipeline.

    Delta entries are the atomic units of change tracking. Each entry is
    immutable once created and contains evidence IDs for reproducibility.

    Attributes:
        delta_id: Unique deterministic ID for this delta
        delta_type: Type of change (add, update, etc.)
        target_id: ID of the entity being modified (finding/bead/verdict)
        evidence_ids: Evidence IDs supporting this delta (required)
        source_batch: Batch ID that produced this delta
        timestamp: When delta was created (ISO format)
        payload: The actual delta content (immutable after creation)
        ordering_key: Deterministic key for merge ordering

    Usage:
        delta = DeltaEntry(
            delta_type=DeltaType.FINDING_ADD,
            target_id="FND-001",
            evidence_ids=["EVD-abc123", "EVD-def456"],
            source_batch="batch-001",
            payload={"severity": "high", "confidence": 0.85}
        )
    """
    delta_type: DeltaType
    target_id: str
    evidence_ids: List[str]
    source_batch: str
    payload: Dict[str, Any]
    timestamp: str = ""
    delta_id: str = ""
    ordering_key: str = ""

    def __post_init__(self) -> None:
        """Generate deterministic IDs and validate."""
        import re
        from datetime import datetime

        # Set timestamp if not provided
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

        # Validate evidence IDs format
        evidence_pattern = re.compile(r"^(node|edge|fn|EVD):[A-Za-z0-9_:-]+$|^EVD-[A-Za-z0-9]+$")
        for eid in self.evidence_ids:
            if not evidence_pattern.match(eid):
                raise ValueError(f"Invalid evidence ID format: {eid}")

        # Generate deterministic delta_id from content hash
        if not self.delta_id:
            self.delta_id = self._compute_delta_id()

        # Generate deterministic ordering key
        if not self.ordering_key:
            self.ordering_key = self._compute_ordering_key()

    def _compute_delta_id(self) -> str:
        """Compute deterministic delta ID from content.

        The delta ID is a stable hash of:
        - delta_type
        - target_id
        - sorted evidence_ids
        - sorted payload keys/values

        This ensures identical deltas produce identical IDs regardless of
        creation order or batch.
        """
        import json

        # Create deterministic content string
        content_parts = [
            self.delta_type.value,
            self.target_id,
            "|".join(sorted(self.evidence_ids)),
            json.dumps(self.payload, sort_keys=True, default=str),
        ]
        content = "::".join(content_parts)

        # Hash for stable ID
        hash_hex = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"DELTA-{hash_hex}"

    def _compute_ordering_key(self) -> str:
        """Compute deterministic ordering key for merge.

        Ordering key ensures deterministic merge order:
        1. By delta_type priority (FINDING_ADD < EVIDENCE_ADD < etc.)
        2. By target_id (alphabetically)
        3. By delta_id (for identical targets)

        This guarantees replays produce identical merged output.
        """
        # Priority order for delta types
        type_priority = {
            DeltaType.FINDING_ADD: "0",
            DeltaType.EVIDENCE_ADD: "1",
            DeltaType.CONFIDENCE_CHANGE: "2",
            DeltaType.FINDING_UPDATE: "3",
            DeltaType.VERDICT_ADD: "4",
        }
        priority = type_priority.get(self.delta_type, "9")
        return f"{priority}:{self.target_id}:{self.delta_id}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "delta_id": self.delta_id,
            "delta_type": self.delta_type.value,
            "target_id": self.target_id,
            "evidence_ids": self.evidence_ids,
            "source_batch": self.source_batch,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "ordering_key": self.ordering_key,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeltaEntry":
        """Create DeltaEntry from dictionary."""
        delta_type = data.get("delta_type", "finding_add")
        if isinstance(delta_type, str):
            delta_type = DeltaType(delta_type)
        return cls(
            delta_id=str(data.get("delta_id", "")),
            delta_type=delta_type,
            target_id=str(data.get("target_id", "")),
            evidence_ids=list(data.get("evidence_ids", [])),
            source_batch=str(data.get("source_batch", "")),
            timestamp=str(data.get("timestamp", "")),
            payload=dict(data.get("payload", {})),
            ordering_key=str(data.get("ordering_key", "")),
        )


class ConflictType(Enum):
    """Type of merge conflict detected.

    Conflicts occur when concurrent deltas make incompatible claims
    about the same target.
    """
    EVIDENCE_MISMATCH = "evidence_mismatch"  # Same target, different evidence
    CONFIDENCE_CONFLICT = "confidence_conflict"  # Conflicting confidence claims
    PAYLOAD_DIVERGENCE = "payload_divergence"  # Different payloads for same target


@dataclass
class MergeConflict:
    """A conflict detected during delta merge.

    Conflicts are quarantined for resolver agent review rather than
    silently discarded or auto-resolved.

    Attributes:
        conflict_id: Unique conflict identifier
        conflict_type: Type of conflict detected
        delta_a: First conflicting delta
        delta_b: Second conflicting delta
        description: Human-readable conflict description
        timestamp: When conflict was detected
        resolved: Whether conflict has been resolved
        resolution: Resolution outcome (if resolved)

    Usage:
        conflict = MergeConflict(
            conflict_type=ConflictType.EVIDENCE_MISMATCH,
            delta_a=delta1,
            delta_b=delta2,
            description="Deltas have different evidence for FND-001"
        )
    """
    conflict_type: ConflictType
    delta_a: DeltaEntry
    delta_b: DeltaEntry
    description: str = ""
    conflict_id: str = ""
    timestamp: str = ""
    resolved: bool = False
    resolution: Optional[str] = None

    def __post_init__(self) -> None:
        """Generate conflict ID and timestamp."""
        from datetime import datetime

        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

        if not self.conflict_id:
            # Deterministic conflict ID from delta IDs
            content = f"{self.delta_a.delta_id}:{self.delta_b.delta_id}:{self.conflict_type.value}"
            hash_hex = hashlib.sha256(content.encode()).hexdigest()[:12]
            self.conflict_id = f"CONFLICT-{hash_hex}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type.value,
            "delta_a": self.delta_a.to_dict(),
            "delta_b": self.delta_b.to_dict(),
            "description": self.description,
            "timestamp": self.timestamp,
            "resolved": self.resolved,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MergeConflict":
        """Create MergeConflict from dictionary."""
        conflict_type = data.get("conflict_type", "evidence_mismatch")
        if isinstance(conflict_type, str):
            conflict_type = ConflictType(conflict_type)
        return cls(
            conflict_id=str(data.get("conflict_id", "")),
            conflict_type=conflict_type,
            delta_a=DeltaEntry.from_dict(data.get("delta_a", {})),
            delta_b=DeltaEntry.from_dict(data.get("delta_b", {})),
            description=str(data.get("description", "")),
            timestamp=str(data.get("timestamp", "")),
            resolved=bool(data.get("resolved", False)),
            resolution=data.get("resolution"),
        )


@dataclass
class MergeBatch:
    """A batch of deltas for merge pipeline.

    MergeBatch is the unit of work for the append-only merge pipeline.
    Each batch contains deltas from a single source/agent and includes
    a stable hash for cache keying.

    Attributes:
        batch_id: Unique batch identifier
        source: Source agent/process that created this batch
        deltas: List of delta entries (append-only)
        graph_hash: Hash of the graph state when batch was created
        pcp_version: PCP version used for this batch
        created_at: Batch creation timestamp
        merged_at: When batch was merged (None if pending)
        stable_hash: Deterministic hash of batch contents

    Usage:
        batch = MergeBatch(
            source="pattern_scout",
            deltas=[delta1, delta2],
            graph_hash="abc123",
            pcp_version="2.0"
        )
    """
    source: str
    deltas: List[DeltaEntry]
    graph_hash: str
    pcp_version: str = "2.0"
    batch_id: str = ""
    created_at: str = ""
    merged_at: Optional[str] = None
    stable_hash: str = ""

    def __post_init__(self) -> None:
        """Generate batch ID, timestamps, and stable hash."""
        from datetime import datetime

        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"

        # Compute stable hash first (needed for batch_id)
        if not self.stable_hash:
            self.stable_hash = self._compute_stable_hash()

        if not self.batch_id:
            # Deterministic batch ID from source + stable hash
            content = f"{self.source}:{self.stable_hash}"
            hash_hex = hashlib.sha256(content.encode()).hexdigest()[:12]
            self.batch_id = f"BATCH-{hash_hex}"

    def _compute_stable_hash(self) -> str:
        """Compute stable hash of batch contents.

        Hash includes:
        - graph_hash
        - pcp_version
        - sorted delta IDs

        This ensures identical batches have identical hashes for cache keying.
        """
        delta_ids = sorted(d.delta_id for d in self.deltas)
        content = f"{self.graph_hash}:{self.pcp_version}:{','.join(delta_ids)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def add_delta(self, delta: DeltaEntry) -> None:
        """Add a delta to the batch (append-only).

        Recomputes stable hash after adding.
        """
        self.deltas.append(delta)
        self.stable_hash = self._compute_stable_hash()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "batch_id": self.batch_id,
            "source": self.source,
            "deltas": [d.to_dict() for d in self.deltas],
            "graph_hash": self.graph_hash,
            "pcp_version": self.pcp_version,
            "created_at": self.created_at,
            "merged_at": self.merged_at,
            "stable_hash": self.stable_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MergeBatch":
        """Create MergeBatch from dictionary."""
        return cls(
            batch_id=str(data.get("batch_id", "")),
            source=str(data.get("source", "")),
            deltas=[DeltaEntry.from_dict(d) for d in data.get("deltas", [])],
            graph_hash=str(data.get("graph_hash", "")),
            pcp_version=str(data.get("pcp_version", "2.0")),
            created_at=str(data.get("created_at", "")),
            merged_at=data.get("merged_at"),
            stable_hash=str(data.get("stable_hash", "")),
        )


@dataclass
class MergeResult:
    """Result of merge pipeline execution.

    Captures merged deltas, detected conflicts, and audit trail.

    Attributes:
        merged_deltas: Successfully merged deltas in deterministic order
        conflicts: Conflicts quarantined for resolver agent
        audit_trail: List of merge operations performed
        output_hash: Stable hash of merged output
        idempotent: Whether this merge was idempotent (replay produced same result)

    Usage:
        result = merge_findings(batches)
        if result.conflicts:
            # Route to resolver agent
            resolver.handle(result.conflicts)
    """
    merged_deltas: List[DeltaEntry]
    conflicts: List[MergeConflict] = field(default_factory=list)
    audit_trail: List[str] = field(default_factory=list)
    output_hash: str = ""
    idempotent: bool = True

    def __post_init__(self) -> None:
        """Compute output hash if not provided."""
        if not self.output_hash and self.merged_deltas:
            # Deterministic hash of merged output
            delta_ids = [d.delta_id for d in self.merged_deltas]
            content = ",".join(delta_ids)
            self.output_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "merged_deltas": [d.to_dict() for d in self.merged_deltas],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "audit_trail": self.audit_trail,
            "output_hash": self.output_hash,
            "idempotent": self.idempotent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MergeResult":
        """Create MergeResult from dictionary."""
        return cls(
            merged_deltas=[DeltaEntry.from_dict(d) for d in data.get("merged_deltas", [])],
            conflicts=[MergeConflict.from_dict(c) for c in data.get("conflicts", [])],
            audit_trail=list(data.get("audit_trail", [])),
            output_hash=str(data.get("output_hash", "")),
            idempotent=bool(data.get("idempotent", True)),
        )


# =============================================================================
# Diversity Policy - Enforce distinct reasoning modes across parallel agents
# =============================================================================


class DiversityPathType(Enum):
    """Primary reasoning mode for diversity enforcement.

    operation_first: Focus on semantic operations and behavioral signatures
    guard_first: Focus on guards, counter-signals, and defensive patterns
    invariant_first: Focus on protocol invariants and economic constraints
    """
    OPERATION_FIRST = "operation_first"
    GUARD_FIRST = "guard_first"
    INVARIANT_FIRST = "invariant_first"


class AssignmentStrategy(Enum):
    """Strategy for assigning diversity paths to agents."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    COST_BALANCED = "cost_balanced"


@dataclass
class DiversityPath:
    """Reasoning path assignment for diversity enforcement.

    Attributes:
        path_type: Primary reasoning mode
        focus: What to prioritize
        constraints: Constraints on this reasoning path

    Usage:
        path = DiversityPath(
            path_type=DiversityPathType.OPERATION_FIRST,
            focus="semantic operations and behavioral signatures",
            constraints=["no guard analysis", "no economic reasoning"]
        )
    """
    path_type: DiversityPathType
    focus: str
    constraints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "path_type": self.path_type.value,
            "focus": self.focus,
            "constraints": self.constraints,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiversityPath":
        """Create DiversityPath from dictionary."""
        path_type = data.get("path_type", "operation_first")
        if isinstance(path_type, str):
            path_type = DiversityPathType(path_type.lower())
        return cls(
            path_type=path_type,
            focus=str(data.get("focus", "")),
            constraints=list(data.get("constraints", [])),
        )


@dataclass
class DiversityPolicy:
    """Policy enforcing distinct reasoning modes across parallel agents.

    Ensures that parallel agents use different reasoning approaches to
    maximize coverage and reduce blind spots.

    Attributes:
        policy_id: Policy identifier
        paths: Available reasoning paths (at least 3)
        min_distinct_paths: Minimum distinct paths required in parallel execution
        assignment_strategy: How to assign paths to agents

    Usage:
        policy = DiversityPolicy(
            policy_id="default-diversity",
            paths=[
                DiversityPath(path_type=DiversityPathType.OPERATION_FIRST, ...),
                DiversityPath(path_type=DiversityPathType.GUARD_FIRST, ...),
                DiversityPath(path_type=DiversityPathType.INVARIANT_FIRST, ...),
            ],
            min_distinct_paths=2
        )
    """
    policy_id: str
    paths: List[DiversityPath]
    min_distinct_paths: int = 2
    assignment_strategy: AssignmentStrategy = AssignmentStrategy.ROUND_ROBIN

    def __post_init__(self) -> None:
        """Validate policy constraints."""
        if len(self.paths) < 3:
            raise ValueError(f"Diversity policy requires at least 3 paths, got {len(self.paths)}")
        if not 2 <= self.min_distinct_paths <= 3:
            raise ValueError(f"min_distinct_paths must be 2-3, got {self.min_distinct_paths}")
        # Ensure all three path types are present
        path_types = {p.path_type for p in self.paths}
        required = {DiversityPathType.OPERATION_FIRST, DiversityPathType.GUARD_FIRST, DiversityPathType.INVARIANT_FIRST}
        missing = required - path_types
        if missing:
            raise ValueError(f"Diversity policy missing required path types: {missing}")

    def assign_path(self, agent_index: int) -> DiversityPath:
        """Assign a path to an agent based on strategy.

        Args:
            agent_index: Index of the agent (0-based)

        Returns:
            DiversityPath assigned to this agent
        """
        if self.assignment_strategy == AssignmentStrategy.ROUND_ROBIN:
            return self.paths[agent_index % len(self.paths)]
        elif self.assignment_strategy == AssignmentStrategy.RANDOM:
            import random
            return random.choice(self.paths)
        else:  # COST_BALANCED - not implemented, defaults to round robin
            return self.paths[agent_index % len(self.paths)]

    def validate_assignments(self, assigned_paths: List[DiversityPath]) -> bool:
        """Validate that assignments meet diversity requirements.

        Args:
            assigned_paths: List of paths assigned to agents

        Returns:
            True if diversity requirements are met
        """
        unique_types = {p.path_type for p in assigned_paths}
        return len(unique_types) >= self.min_distinct_paths

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "policy_id": self.policy_id,
            "paths": [p.to_dict() for p in self.paths],
            "min_distinct_paths": self.min_distinct_paths,
            "assignment_strategy": self.assignment_strategy.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiversityPolicy":
        """Create DiversityPolicy from dictionary."""
        strategy = data.get("assignment_strategy", "round_robin")
        if isinstance(strategy, str):
            strategy = AssignmentStrategy(strategy.lower())
        return cls(
            policy_id=str(data.get("policy_id", "")),
            paths=[DiversityPath.from_dict(p) for p in data.get("paths", [])],
            min_distinct_paths=int(data.get("min_distinct_paths", 2)),
            assignment_strategy=strategy,
        )

    @classmethod
    def default(cls) -> "DiversityPolicy":
        """Create the default diversity policy.

        Returns:
            Default policy with operation-first, guard-first, and invariant-first paths
        """
        return cls(
            policy_id="default-diversity-v1",
            paths=[
                DiversityPath(
                    path_type=DiversityPathType.OPERATION_FIRST,
                    focus="Semantic operations and behavioral signatures",
                    constraints=["Prioritize operation ordering", "Detect CEI violations"]
                ),
                DiversityPath(
                    path_type=DiversityPathType.GUARD_FIRST,
                    focus="Guards, counter-signals, and defensive patterns",
                    constraints=["Search for reentrancy locks", "Identify access controls", "Find anti-signals"]
                ),
                DiversityPath(
                    path_type=DiversityPathType.INVARIANT_FIRST,
                    focus="Protocol invariants and economic constraints",
                    constraints=["Consider economic feasibility", "Check protocol assumptions", "Validate invariants"]
                ),
            ],
            min_distinct_paths=2,
            assignment_strategy=AssignmentStrategy.ROUND_ROBIN,
        )


# Export all schema types
__all__ = [
    # Original exports
    "PoolStatus",
    "VerdictConfidence",
    "Scope",
    "EvidenceItem",
    "EvidencePacket",
    "DebateClaim",
    "DebateRecord",
    "Verdict",
    "Pool",
    # Role contracts
    "UnknownReason",
    "UnknownItem",
    "ScoutStatus",
    "ScoutHypothesis",
    "VerificationStatus",
    "VerificationResult",
    "ContradictionStatus",
    "CounterargumentType",
    "CounterargumentStrength",
    "Counterargument",
    "ResidualRisk",
    "ContradictionReport",
    "CompositionStatus",
    "ComposedPattern",
    "RejectedComposition",
    "CompositionProposal",
    "SynthesisStatus",
    "ConflictType",
    "ConflictResolution",
    "ConfidenceBounds",
    "SynthesizedCluster",
    "SynthesisConflict",
    "EvidenceStats",
    "SynthesizedFinding",
    # Diversity policy
    "DiversityPathType",
    "AssignmentStrategy",
    "DiversityPath",
    "DiversityPolicy",
    # Delta schema (Phase 5.10-10)
    "DeltaType",
    "DeltaEntry",
    "MergeConflict",
    "MergeBatch",
    "MergeResult",
]
