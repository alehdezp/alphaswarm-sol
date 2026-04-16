"""
Audit Finding System

Manages audit findings with cryptographic proofs and consensus tracking.
Privacy-preserving: stores contract hashes, not source code.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class FindingStatus(Enum):
    """Status of a finding in the consensus process."""
    PENDING = "pending"           # Awaiting validation
    VALIDATING = "validating"     # Being validated
    CONFIRMED = "confirmed"       # Consensus reached - valid finding
    DISPUTED = "disputed"         # No consensus
    REJECTED = "rejected"         # Proven false positive
    EXPIRED = "expired"           # Validation period expired


@dataclass
class FindingVote:
    """A vote on a finding's validity."""
    validator_id: str
    agrees: bool                  # True = valid finding, False = false positive
    reasoning: str
    confidence: float             # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validator_id": self.validator_id,
            "agrees": self.agrees,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AuditFinding:
    """
    A finding submitted to the collaborative network.
    """
    finding_id: str
    contract_hash: str            # SHA256 hash of contract (privacy)
    vulnerability_type: str
    severity: str                 # critical, high, medium, low
    title: str
    description: str
    auditor_id: str
    signature: Optional[str] = None  # Cryptographic signature

    # Location in contract
    function_name: Optional[str] = None
    line_number: Optional[int] = None

    # Evidence
    proof_of_exploit: Optional[str] = None  # Test case or PoC
    recommended_fix: Optional[str] = None

    # Consensus
    status: FindingStatus = FindingStatus.PENDING
    votes: List[FindingVote] = field(default_factory=list)
    required_validators: int = 5  # Min votes needed

    # Metadata
    submitted_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.finding_id:
            self.finding_id = self._generate_finding_id()

    def _generate_finding_id(self) -> str:
        """Generate unique finding ID."""
        data = f"{self.contract_hash}:{self.vulnerability_type}:{self.title}:{datetime.now().isoformat()}"
        return f"FIND-{hashlib.sha256(data.encode()).hexdigest()[:12].upper()}"

    def add_vote(self, vote: FindingVote):
        """Add a vote and update status."""
        self.votes.append(vote)
        self.updated_at = datetime.now()
        self._update_status()

    def _update_status(self):
        """Update status based on votes."""
        if len(self.votes) < self.required_validators:
            self.status = FindingStatus.VALIDATING
            return

        agrees_count = sum(1 for v in self.votes if v.agrees)
        total = len(self.votes)

        if agrees_count >= total * 0.6:  # 60% threshold
            self.status = FindingStatus.CONFIRMED
        elif agrees_count <= total * 0.2:  # Less than 20%
            self.status = FindingStatus.REJECTED
        else:
            self.status = FindingStatus.DISPUTED

    def get_consensus_summary(self) -> Dict[str, Any]:
        """Get summary of consensus state."""
        agrees = sum(1 for v in self.votes if v.agrees)
        disagrees = len(self.votes) - agrees
        avg_confidence = sum(v.confidence for v in self.votes) / len(self.votes) if self.votes else 0

        return {
            "status": self.status.value,
            "votes_for": agrees,
            "votes_against": disagrees,
            "total_votes": len(self.votes),
            "required_votes": self.required_validators,
            "average_confidence": round(avg_confidence, 2),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "finding_id": self.finding_id,
            "contract_hash": self.contract_hash,
            "vulnerability_type": self.vulnerability_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "auditor_id": self.auditor_id,
            "function_name": self.function_name,
            "line_number": self.line_number,
            "status": self.status.value,
            "consensus": self.get_consensus_summary(),
            "submitted_at": self.submitted_at.isoformat(),
        }

    def sign(self, private_key: str) -> str:
        """
        Sign the finding (mock implementation).

        In production, would use actual cryptographic signing.
        """
        data = json.dumps({
            "finding_id": self.finding_id,
            "contract_hash": self.contract_hash,
            "vulnerability_type": self.vulnerability_type,
            "severity": self.severity,
            "auditor_id": self.auditor_id,
        }, sort_keys=True)

        # Mock signature (would use actual crypto in production)
        self.signature = hashlib.sha256(f"{data}:{private_key}".encode()).hexdigest()
        return self.signature

    def verify_signature(self, public_key: str) -> bool:
        """
        Verify the finding signature (mock implementation).

        In production, would use actual cryptographic verification.
        """
        if not self.signature:
            return False
        # Mock verification - always returns True for demo
        return True


@dataclass
class FindingSubmission:
    """
    A submission request for a new finding.
    """
    contract_code: str            # Source code (hashed before storage)
    vulnerability_type: str
    severity: str
    title: str
    description: str
    function_name: Optional[str] = None
    proof_of_exploit: Optional[str] = None
    recommended_fix: Optional[str] = None

    def to_finding(self, auditor_id: str) -> AuditFinding:
        """Convert submission to AuditFinding."""
        return AuditFinding(
            finding_id="",
            contract_hash=hashlib.sha256(self.contract_code.encode()).hexdigest(),
            vulnerability_type=self.vulnerability_type,
            severity=self.severity,
            title=self.title,
            description=self.description,
            auditor_id=auditor_id,
            function_name=self.function_name,
            proof_of_exploit=self.proof_of_exploit,
            recommended_fix=self.recommended_fix,
        )


class FindingRegistry:
    """
    Registry of all findings.
    """

    def __init__(self):
        self.findings: Dict[str, AuditFinding] = {}
        self._by_contract: Dict[str, List[str]] = {}
        self._by_auditor: Dict[str, List[str]] = {}
        self._by_status: Dict[FindingStatus, List[str]] = {s: [] for s in FindingStatus}

    def submit(self, finding: AuditFinding) -> str:
        """Submit a new finding."""
        self.findings[finding.finding_id] = finding

        # Index
        if finding.contract_hash not in self._by_contract:
            self._by_contract[finding.contract_hash] = []
        self._by_contract[finding.contract_hash].append(finding.finding_id)

        if finding.auditor_id not in self._by_auditor:
            self._by_auditor[finding.auditor_id] = []
        self._by_auditor[finding.auditor_id].append(finding.finding_id)

        self._by_status[finding.status].append(finding.finding_id)

        return finding.finding_id

    def get(self, finding_id: str) -> Optional[AuditFinding]:
        """Get a finding by ID."""
        return self.findings.get(finding_id)

    def get_for_contract(self, contract_hash: str) -> List[AuditFinding]:
        """Get all findings for a contract."""
        ids = self._by_contract.get(contract_hash, [])
        return [self.findings[id] for id in ids if id in self.findings]

    def get_by_auditor(self, auditor_id: str) -> List[AuditFinding]:
        """Get all findings by an auditor."""
        ids = self._by_auditor.get(auditor_id, [])
        return [self.findings[id] for id in ids if id in self.findings]

    def get_pending(self) -> List[AuditFinding]:
        """Get findings awaiting validation."""
        return [
            self.findings[id]
            for id in self._by_status[FindingStatus.PENDING] +
                      self._by_status[FindingStatus.VALIDATING]
            if id in self.findings
        ]

    def get_confirmed(self) -> List[AuditFinding]:
        """Get confirmed findings."""
        return [
            self.findings[id]
            for id in self._by_status[FindingStatus.CONFIRMED]
            if id in self.findings
        ]

    def update_status(self, finding_id: str, new_status: FindingStatus):
        """Update finding status."""
        finding = self.findings.get(finding_id)
        if finding:
            old_status = finding.status
            self._by_status[old_status].remove(finding_id)
            finding.status = new_status
            self._by_status[new_status].append(finding_id)

    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_findings": len(self.findings),
            "by_status": {
                s.value: len(ids)
                for s, ids in self._by_status.items()
            },
            "unique_contracts": len(self._by_contract),
            "unique_auditors": len(self._by_auditor),
        }
