"""Protocol dossier ingestion with diff beacon and staleness tracking.

Per 05.11-CONTEXT.md: Dossier ingestion with source attribution, confidence,
staleness rules, and game-theoretic payoff fields.

Key features:
- DossierBuilder: Accept doc sources + governance proposals, normalize records
- DossierRecord: Structured record with provenance and TTL
- Diff beacon: Detect changes and mark stale fields
- PayoffField integration: Wire payoff models into context pack

Usage:
    from alphaswarm_sol.context.dossier import DossierBuilder, DossierRecord

    builder = DossierBuilder()

    # Add sources
    builder.add_doc_source("whitepaper-v1.2", "whitepaper.md", "docs", "2025-01-15")
    builder.add_governance_proposal("prop-42", "Emergency timelock change", "2025-01-20")

    # Build dossier records
    records = builder.build_records()

    # Check for stale records
    stale = [r for r in records if r.is_stale()]

    # Integrate with context pack
    pack = builder.build_context_pack()
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .types import (
    Confidence,
    ExpectationProvenance,
    SourceAttribution,
    Role,
    Assumption,
    Invariant,
)

if TYPE_CHECKING:
    from .schema import ProtocolContextPack


@dataclass
class DossierSource:
    """A source document for dossier ingestion.

    Per 05.11-CONTEXT.md: Every fact needs source_id, source_date,
    and source_type for staleness and confidence tracking.

    Attributes:
        source_id: Unique identifier for this source
        path: File path or URL
        source_type: Type (docs, governance, on-chain, audit, code)
        source_date: Date of the source (ISO format)
        content_hash: Hash of content for change detection
        tier: Reliability tier (1=official, 2=audit, 3=community)
        expires_at: Optional TTL for staleness tracking
    """

    source_id: str
    path: str
    source_type: str  # docs, governance, on-chain, audit, code
    source_date: str  # ISO format
    content_hash: str = ""
    tier: int = 1
    expires_at: Optional[str] = None

    def compute_hash(self, content: str) -> str:
        """Compute content hash for change detection.

        Args:
            content: Source content

        Returns:
            SHA-256 hash (first 16 characters)
        """
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "source_id": self.source_id,
            "path": self.path,
            "source_type": self.source_type,
            "source_date": self.source_date,
            "tier": self.tier,
        }
        if self.content_hash:
            result["content_hash"] = self.content_hash
        if self.expires_at:
            result["expires_at"] = self.expires_at
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DossierSource":
        """Create DossierSource from dictionary."""
        return cls(
            source_id=str(data.get("source_id", "")),
            path=str(data.get("path", "")),
            source_type=str(data.get("source_type", "")),
            source_date=str(data.get("source_date", "")),
            content_hash=str(data.get("content_hash", "")),
            tier=int(data.get("tier", 3)),
            expires_at=data.get("expires_at"),
        )


@dataclass
class DossierRecord:
    """A normalized record from dossier ingestion.

    Per 05.11-CONTEXT.md: Records capture extracted facts with provenance,
    confidence, and staleness tracking.

    Attributes:
        record_id: Unique identifier for this record
        record_type: Type (role, assumption, invariant, value_flow, etc.)
        content: The actual content/data
        provenance: Expectation provenance (declared/inferred/hypothesis)
        confidence: Confidence level
        source: Source attribution
        created_at: When this record was created
        last_verified: When this record was last verified
        is_stale_flag: Whether marked as stale by diff beacon
        conflict_refs: References to conflicting records
        evidence_refs: References to supporting evidence
    """

    record_id: str
    record_type: str  # role, assumption, invariant, value_flow, etc.
    content: Dict[str, Any]
    provenance: ExpectationProvenance
    confidence: Confidence
    source: SourceAttribution
    created_at: str = ""
    last_verified: str = ""
    is_stale_flag: bool = False
    conflict_refs: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize timestamps if not set."""
        now = datetime.utcnow().isoformat() + "Z"
        if not self.created_at:
            self.created_at = now
        if not self.last_verified:
            self.last_verified = now

    def is_stale(self, current_date: Optional[str] = None) -> bool:
        """Check if this record is stale.

        Stale if:
        - Explicitly marked stale by diff beacon
        - Source has expired based on TTL
        - Last verified is older than 90 days

        Args:
            current_date: Current date in ISO format (defaults to today)

        Returns:
            True if record is stale
        """
        if self.is_stale_flag:
            return True

        if self.source.is_stale(current_date):
            return True

        # Check if last verified is too old (90 days)
        if current_date is None:
            current_date = datetime.utcnow().strftime("%Y-%m-%d")

        try:
            verified = datetime.fromisoformat(self.last_verified.replace("Z", "+00:00"))
            current = datetime.fromisoformat(current_date.replace("Z", "+00:00"))
            age = current - verified
            return age > timedelta(days=90)
        except (ValueError, AttributeError):
            return False

    def mark_stale(self, reason: str = "") -> None:
        """Mark this record as stale.

        Args:
            reason: Reason for marking stale
        """
        self.is_stale_flag = True
        if reason:
            self.conflict_refs.append(f"stale:{reason}")

    def refresh(self, new_source: Optional[SourceAttribution] = None) -> None:
        """Refresh this record with current timestamp.

        Args:
            new_source: Optional new source attribution
        """
        self.last_verified = datetime.utcnow().isoformat() + "Z"
        self.is_stale_flag = False
        if new_source:
            self.source = new_source

    def has_conflicts(self) -> bool:
        """Check if this record has conflicts."""
        return len(self.conflict_refs) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "record_id": self.record_id,
            "record_type": self.record_type,
            "content": self.content,
            "provenance": self.provenance.value,
            "confidence": self.confidence.value,
            "source": self.source.to_dict(),
            "created_at": self.created_at,
            "last_verified": self.last_verified,
            "is_stale_flag": self.is_stale_flag,
            "conflict_refs": self.conflict_refs,
            "evidence_refs": self.evidence_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DossierRecord":
        """Create DossierRecord from dictionary."""
        provenance = data.get("provenance", "inferred")
        if isinstance(provenance, str):
            provenance = ExpectationProvenance.from_string(provenance)

        confidence = data.get("confidence", "unknown")
        if isinstance(confidence, str):
            confidence = Confidence.from_string(confidence)

        return cls(
            record_id=str(data.get("record_id", "")),
            record_type=str(data.get("record_type", "")),
            content=dict(data.get("content", {})),
            provenance=provenance,
            confidence=confidence,
            source=SourceAttribution.from_dict(data.get("source", {})),
            created_at=str(data.get("created_at", "")),
            last_verified=str(data.get("last_verified", "")),
            is_stale_flag=bool(data.get("is_stale_flag", False)),
            conflict_refs=list(data.get("conflict_refs", [])),
            evidence_refs=list(data.get("evidence_refs", [])),
        )


@dataclass
class DiffBeacon:
    """Change detection beacon for dossier sources.

    Per 05.11-CONTEXT.md: Lightweight diff beacon compares docs + governance
    proposals against the dossier and marks fields as stale without manual review.

    Attributes:
        source_hashes: Map of source_id to content_hash
        last_check: When the last diff check was performed
        stale_sources: List of source_ids marked as stale
    """

    source_hashes: Dict[str, str] = field(default_factory=dict)
    last_check: str = ""
    stale_sources: List[str] = field(default_factory=list)

    def record_hash(self, source_id: str, content_hash: str) -> None:
        """Record a source content hash.

        Args:
            source_id: Source identifier
            content_hash: Content hash
        """
        self.source_hashes[source_id] = content_hash
        self.last_check = datetime.utcnow().isoformat() + "Z"

    def check_changed(self, source_id: str, new_content: str) -> bool:
        """Check if source content has changed.

        Args:
            source_id: Source identifier
            new_content: New content to check

        Returns:
            True if content has changed
        """
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()[:16]
        old_hash = self.source_hashes.get(source_id)

        if old_hash is None:
            # New source, record it
            self.record_hash(source_id, new_hash)
            return False

        if new_hash != old_hash:
            # Content changed
            self.stale_sources.append(source_id)
            self.record_hash(source_id, new_hash)
            return True

        return False

    def get_stale_sources(self) -> List[str]:
        """Get list of stale source IDs."""
        return self.stale_sources.copy()

    def clear_stale(self) -> None:
        """Clear the stale sources list."""
        self.stale_sources = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "source_hashes": self.source_hashes,
            "last_check": self.last_check,
            "stale_sources": self.stale_sources,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiffBeacon":
        """Create DiffBeacon from dictionary."""
        return cls(
            source_hashes=dict(data.get("source_hashes", {})),
            last_check=str(data.get("last_check", "")),
            stale_sources=list(data.get("stale_sources", [])),
        )


class DossierBuilder:
    """Builder for protocol dossiers from multiple sources.

    Per 05.11-CONTEXT.md: Accept doc sources + governance proposals,
    normalize into structured DossierRecord with provenance.

    Key features:
    - Add doc sources, governance proposals, on-chain config
    - Normalize into DossierRecord with provenance
    - Detect changes via diff beacon and mark stale fields
    - Surface unknowns when sources are stale or contradictory
    - Wire into ContextPackBuilder

    Usage:
        builder = DossierBuilder()

        # Add sources
        builder.add_doc_source("whitepaper-v1.2", "whitepaper.md", "2025-01-15")
        builder.add_governance_proposal("prop-42", "Emergency timelock", "2025-01-20")

        # Build records
        records = builder.build_records()

        # Check for stale/conflicting records
        stale = builder.get_stale_records()
        conflicts = builder.get_conflicting_records()
    """

    def __init__(self) -> None:
        """Initialize the dossier builder."""
        self._sources: List[DossierSource] = []
        self._records: List[DossierRecord] = []
        self._diff_beacon = DiffBeacon()
        self._warnings: List[str] = []

    def add_doc_source(
        self,
        source_id: str,
        path: str,
        source_date: str,
        tier: int = 1,
        content: Optional[str] = None,
        expires_at: Optional[str] = None,
    ) -> None:
        """Add a documentation source.

        Args:
            source_id: Unique identifier for this source
            path: File path or URL
            source_date: Date of the source (ISO format)
            tier: Reliability tier (1=official, 2=audit, 3=community)
            content: Optional content for hash computation
            expires_at: Optional TTL for staleness tracking
        """
        source = DossierSource(
            source_id=source_id,
            path=path,
            source_type="docs",
            source_date=source_date,
            tier=tier,
            expires_at=expires_at,
        )

        if content:
            source.content_hash = source.compute_hash(content)
            # Check for changes via diff beacon
            if self._diff_beacon.check_changed(source_id, content):
                self._warnings.append(f"Source '{source_id}' content has changed - marking stale")

        self._sources.append(source)

    def add_governance_proposal(
        self,
        source_id: str,
        description: str,
        source_date: str,
        content: Optional[str] = None,
        expires_at: Optional[str] = None,
    ) -> None:
        """Add a governance proposal source.

        Args:
            source_id: Unique identifier (e.g., "prop-42")
            description: Proposal description
            source_date: Date of the proposal
            content: Optional content for hash computation
            expires_at: Optional TTL
        """
        source = DossierSource(
            source_id=source_id,
            path=f"governance:{source_id}",
            source_type="governance",
            source_date=source_date,
            tier=1,  # Governance is authoritative
            expires_at=expires_at,
        )

        if content:
            source.content_hash = source.compute_hash(content)
            if self._diff_beacon.check_changed(source_id, content):
                self._warnings.append(f"Governance proposal '{source_id}' has changed - marking stale")

        self._sources.append(source)

    def add_on_chain_config(
        self,
        source_id: str,
        config_data: Dict[str, Any],
        source_date: str,
        block_number: Optional[int] = None,
    ) -> None:
        """Add on-chain configuration source.

        Args:
            source_id: Unique identifier (e.g., "timelock-config")
            config_data: Configuration data from chain
            source_date: Date of extraction
            block_number: Optional block number for reference
        """
        import json

        content = json.dumps(config_data, sort_keys=True)
        source = DossierSource(
            source_id=source_id,
            path=f"onchain:{source_id}:{block_number}" if block_number else f"onchain:{source_id}",
            source_type="on-chain",
            source_date=source_date,
            content_hash=hashlib.sha256(content.encode()).hexdigest()[:16],
            tier=1,  # On-chain is authoritative
        )

        if self._diff_beacon.check_changed(source_id, content):
            self._warnings.append(f"On-chain config '{source_id}' has changed - marking stale")

        self._sources.append(source)

    def add_record(
        self,
        record_type: str,
        content: Dict[str, Any],
        source_id: str,
        provenance: ExpectationProvenance = ExpectationProvenance.DECLARED,
        confidence: Confidence = Confidence.INFERRED,
        evidence_refs: Optional[List[str]] = None,
    ) -> str:
        """Add a dossier record.

        Args:
            record_type: Type (role, assumption, invariant, value_flow, etc.)
            content: Record content
            source_id: Reference to source
            provenance: Expectation provenance
            confidence: Confidence level
            evidence_refs: Optional evidence references

        Returns:
            Record ID
        """
        # Find source
        source = next((s for s in self._sources if s.source_id == source_id), None)
        if not source:
            self._warnings.append(f"Source '{source_id}' not found for record")
            source_attr = SourceAttribution(
                source_id=source_id,
                source_date=datetime.utcnow().strftime("%Y-%m-%d"),
                source_type="unknown",
            )
        else:
            source_attr = SourceAttribution(
                source_id=source.source_id,
                source_date=source.source_date,
                source_type=source.source_type,
                expires_at=source.expires_at,
            )

        record_id = f"{record_type}:{source_id}:{len(self._records)}"
        record = DossierRecord(
            record_id=record_id,
            record_type=record_type,
            content=content,
            provenance=provenance,
            confidence=confidence,
            source=source_attr,
            evidence_refs=evidence_refs or [],
        )

        # Check if source is stale
        if source_id in self._diff_beacon.stale_sources:
            record.mark_stale("source_changed")

        self._records.append(record)
        return record_id

    def build_records(self) -> List[DossierRecord]:
        """Build and return all dossier records.

        Returns:
            List of DossierRecord objects
        """
        return self._records.copy()

    def get_stale_records(self) -> List[DossierRecord]:
        """Get all stale records.

        Returns:
            List of stale DossierRecord objects
        """
        return [r for r in self._records if r.is_stale()]

    def get_conflicting_records(self) -> List[DossierRecord]:
        """Get all records with conflicts.

        Returns:
            List of conflicting DossierRecord objects
        """
        return [r for r in self._records if r.has_conflicts()]

    def get_unknown_records(self) -> List[DossierRecord]:
        """Get records that should trigger unknowns.

        Per 05.11-CONTEXT.md: Surface unknowns when sources are stale
        or contradictory.

        Returns:
            List of records requiring unknown handling
        """
        unknowns = []
        for record in self._records:
            if record.is_stale() or record.has_conflicts():
                unknowns.append(record)
            elif record.provenance == ExpectationProvenance.HYPOTHESIS:
                unknowns.append(record)
            elif record.confidence == Confidence.UNKNOWN:
                unknowns.append(record)
        return unknowns

    def extract_roles(self) -> List[Role]:
        """Extract Role objects from dossier records.

        Returns:
            List of Role objects
        """
        roles = []
        for record in self._records:
            if record.record_type == "role":
                role = Role(
                    name=str(record.content.get("name", "")),
                    capabilities=list(record.content.get("capabilities", [])),
                    trust_assumptions=list(record.content.get("trust_assumptions", [])),
                    confidence=record.confidence,
                    description=str(record.content.get("description", "")),
                    provenance=record.provenance,
                    source_id=record.source.source_id,
                    source_date=record.source.source_date,
                    source_type=record.source.source_type,
                    expires_at=record.source.expires_at,
                )
                roles.append(role)
        return roles

    def extract_assumptions(self) -> List[Assumption]:
        """Extract Assumption objects from dossier records.

        Returns:
            List of Assumption objects
        """
        assumptions = []
        for record in self._records:
            if record.record_type == "assumption":
                assumption = Assumption(
                    description=str(record.content.get("description", "")),
                    category=str(record.content.get("category", "")),
                    affects_functions=list(record.content.get("affects_functions", [])),
                    confidence=record.confidence,
                    source=record.source.source_id,
                    tags=list(record.content.get("tags", [])),
                    provenance=record.provenance,
                    source_id=record.source.source_id,
                    source_date=record.source.source_date,
                    source_type=record.source.source_type,
                    expires_at=record.source.expires_at,
                    scope=str(record.content.get("scope", "")),
                )
                assumptions.append(assumption)
        return assumptions

    def extract_invariants(self) -> List[Invariant]:
        """Extract Invariant objects from dossier records.

        Returns:
            List of Invariant objects
        """
        invariants = []
        for record in self._records:
            if record.record_type == "invariant":
                invariant = Invariant(
                    formal=dict(record.content.get("formal", {})),
                    natural_language=str(record.content.get("natural_language", "")),
                    confidence=record.confidence,
                    source=record.source.source_id,
                    category=str(record.content.get("category", "")),
                    critical=bool(record.content.get("critical", False)),
                    provenance=record.provenance,
                    source_id=record.source.source_id,
                    source_date=record.source.source_date,
                    source_type=record.source.source_type,
                    expires_at=record.source.expires_at,
                )
                invariants.append(invariant)
        return invariants

    @property
    def warnings(self) -> List[str]:
        """Get warnings from dossier building."""
        return self._warnings.copy()

    @property
    def diff_beacon(self) -> DiffBeacon:
        """Get the diff beacon for change tracking."""
        return self._diff_beacon

    def to_dict(self) -> Dict[str, Any]:
        """Convert builder state to dictionary for serialization."""
        return {
            "sources": [s.to_dict() for s in self._sources],
            "records": [r.to_dict() for r in self._records],
            "diff_beacon": self._diff_beacon.to_dict(),
            "warnings": self._warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DossierBuilder":
        """Create DossierBuilder from dictionary."""
        builder = cls()
        builder._sources = [DossierSource.from_dict(s) for s in data.get("sources", [])]
        builder._records = [DossierRecord.from_dict(r) for r in data.get("records", [])]
        builder._diff_beacon = DiffBeacon.from_dict(data.get("diff_beacon", {}))
        builder._warnings = list(data.get("warnings", []))
        return builder


# Export all types
__all__ = [
    "DossierSource",
    "DossierRecord",
    "DiffBeacon",
    "DossierBuilder",
]
