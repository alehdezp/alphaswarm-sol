"""
Consensus Validation System

Implements weighted voting for finding validation.
Validators are selected based on reputation and expertise.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import random
import logging

from alphaswarm_sol.collab.reputation import AuditorProfile, ReputationLevel, ReputationSystem

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Status of a validation round."""
    PENDING = "pending"           # Not started
    RECRUITING = "recruiting"     # Selecting validators
    IN_PROGRESS = "in_progress"   # Voting active
    QUORUM_REACHED = "quorum_reached"  # Enough votes
    COMPLETED = "completed"       # Consensus determined
    EXPIRED = "expired"           # Timeout
    FAILED = "failed"             # Could not reach consensus


@dataclass
class ValidationVote:
    """A single validation vote."""
    validator_id: str
    is_valid: bool               # True = valid finding, False = false positive
    confidence: float            # 0.0 to 1.0
    reasoning: str
    evidence: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    # Computed after voting
    weight: float = 1.0          # Based on validator reputation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validator_id": self.validator_id,
            "is_valid": self.is_valid,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "weight": self.weight,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ValidationRequest:
    """Request for validation of a finding."""
    request_id: str
    finding_id: str
    contract_hash: str
    vulnerability_type: str
    severity: str
    description: str

    # Validation configuration
    min_validators: int = 5
    max_validators: int = 15
    quorum_threshold: float = 0.6  # 60% agreement
    timeout_hours: int = 72

    # State
    status: ValidationStatus = ValidationStatus.PENDING
    selected_validators: List[str] = field(default_factory=list)
    votes: List[ValidationVote] = field(default_factory=list)

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.request_id:
            self.request_id = self._generate_request_id()

    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        data = f"{self.finding_id}:{datetime.now().isoformat()}"
        return f"VAL-{hashlib.sha256(data.encode()).hexdigest()[:12].upper()}"

    def is_expired(self) -> bool:
        """Check if validation has expired."""
        if self.status in [ValidationStatus.COMPLETED, ValidationStatus.FAILED]:
            return False
        if self.started_at:
            return datetime.now() > self.started_at + timedelta(hours=self.timeout_hours)
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "finding_id": self.finding_id,
            "vulnerability_type": self.vulnerability_type,
            "severity": self.severity,
            "status": self.status.value,
            "validators": len(self.selected_validators),
            "votes_received": len(self.votes),
            "quorum_threshold": self.quorum_threshold,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ConsensusResult:
    """Result of consensus validation."""
    request_id: str
    finding_id: str

    # Outcome
    is_valid: bool               # Consensus decision
    confidence: float            # Overall confidence
    agreement_ratio: float       # % of weighted votes in agreement

    # Statistics
    total_votes: int
    weighted_for: float
    weighted_against: float

    # Voters
    validators_agreed: List[str]
    validators_disagreed: List[str]

    # Timing
    completed_at: datetime = field(default_factory=datetime.now)
    duration_hours: float = 0.0

    def is_strong_consensus(self) -> bool:
        """Check if consensus is strong (>80% agreement)."""
        return self.agreement_ratio >= 0.8

    def is_disputed(self) -> bool:
        """Check if result is disputed (close vote)."""
        return 0.4 <= self.agreement_ratio <= 0.6

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "finding_id": self.finding_id,
            "is_valid": self.is_valid,
            "confidence": round(self.confidence, 3),
            "agreement_ratio": round(self.agreement_ratio, 3),
            "is_strong_consensus": self.is_strong_consensus(),
            "is_disputed": self.is_disputed(),
            "total_votes": self.total_votes,
            "validators_agreed": len(self.validators_agreed),
            "validators_disagreed": len(self.validators_disagreed),
            "completed_at": self.completed_at.isoformat(),
        }


class ValidatorSelector:
    """
    Selects validators for a finding based on expertise and reputation.
    """

    def __init__(self, reputation_system: ReputationSystem):
        self.reputation = reputation_system
        self._expertise: Dict[str, Set[str]] = {}  # auditor_id -> vuln types

    def register_expertise(self, auditor_id: str, vulnerability_types: List[str]):
        """Register an auditor's areas of expertise."""
        if auditor_id not in self._expertise:
            self._expertise[auditor_id] = set()
        self._expertise[auditor_id].update(vulnerability_types)

    def get_expertise(self, auditor_id: str) -> Set[str]:
        """Get auditor's expertise areas."""
        return self._expertise.get(auditor_id, set())

    def select_validators(
        self,
        vulnerability_type: str,
        exclude_auditor: str,
        count: int = 5,
        min_reputation: int = 100
    ) -> List[str]:
        """
        Select validators for a finding.

        Selection criteria:
        1. Exclude the original auditor
        2. Prefer experts in the vulnerability type
        3. Weight by reputation
        4. Ensure diversity (not all from same tier)
        """
        candidates = []

        for auditor_id, profile in self.reputation.profiles.items():
            # Skip the finding author
            if auditor_id == exclude_auditor:
                continue

            # Check minimum reputation
            if profile.reputation_score < min_reputation:
                continue

            # Calculate selection weight
            weight = self._calculate_selection_weight(
                profile,
                vulnerability_type
            )
            candidates.append((auditor_id, weight))

        if not candidates:
            return []

        # Weighted random selection
        selected = []
        remaining = list(candidates)

        while len(selected) < count and remaining:
            total_weight = sum(w for _, w in remaining)
            if total_weight == 0:
                break

            # Weighted random choice
            r = random.uniform(0, total_weight)
            cumulative = 0
            for i, (auditor_id, weight) in enumerate(remaining):
                cumulative += weight
                if cumulative >= r:
                    selected.append(auditor_id)
                    remaining.pop(i)
                    break

        return selected

    def _calculate_selection_weight(
        self,
        profile: AuditorProfile,
        vulnerability_type: str
    ) -> float:
        """Calculate selection weight for an auditor."""
        weight = 1.0

        # Reputation weight
        weight *= profile.get_trust_weight()

        # Expertise bonus
        if vulnerability_type in self.get_expertise(profile.auditor_id):
            weight *= 2.0

        # Activity bonus (recently active)
        if profile.last_active:
            days_inactive = (datetime.now() - profile.last_active).days
            if days_inactive < 7:
                weight *= 1.5
            elif days_inactive < 30:
                weight *= 1.2

        # Accuracy bonus
        if profile.validations_performed > 10:
            accuracy = profile.get_validation_accuracy()
            weight *= (0.5 + accuracy)

        return weight


class ConsensusValidator:
    """
    Manages consensus-based validation of findings.
    """

    def __init__(
        self,
        reputation_system: ReputationSystem,
        selector: Optional[ValidatorSelector] = None
    ):
        self.reputation = reputation_system
        self.selector = selector or ValidatorSelector(reputation_system)
        self.requests: Dict[str, ValidationRequest] = {}
        self.results: Dict[str, ConsensusResult] = {}

    def create_validation_request(
        self,
        finding_id: str,
        contract_hash: str,
        vulnerability_type: str,
        severity: str,
        description: str,
        submitter_id: str,
        min_validators: int = 5
    ) -> ValidationRequest:
        """Create a new validation request."""
        request = ValidationRequest(
            request_id="",
            finding_id=finding_id,
            contract_hash=contract_hash,
            vulnerability_type=vulnerability_type,
            severity=severity,
            description=description,
            min_validators=min_validators,
        )

        # Select validators
        validators = self.selector.select_validators(
            vulnerability_type=vulnerability_type,
            exclude_auditor=submitter_id,
            count=min_validators * 2,  # Select extra in case some don't respond
            min_reputation=100
        )

        request.selected_validators = validators
        request.status = ValidationStatus.RECRUITING if validators else ValidationStatus.FAILED

        self.requests[request.request_id] = request
        return request

    def start_validation(self, request_id: str) -> bool:
        """Start the validation process."""
        request = self.requests.get(request_id)
        if not request:
            return False

        if len(request.selected_validators) < request.min_validators:
            request.status = ValidationStatus.FAILED
            return False

        request.status = ValidationStatus.IN_PROGRESS
        request.started_at = datetime.now()
        return True

    def submit_vote(
        self,
        request_id: str,
        validator_id: str,
        is_valid: bool,
        confidence: float,
        reasoning: str,
        evidence: Optional[str] = None
    ) -> Optional[ValidationVote]:
        """Submit a validation vote."""
        request = self.requests.get(request_id)
        if not request:
            logger.warning(f"Request not found: {request_id}")
            return None

        # Check validator is selected
        if validator_id not in request.selected_validators:
            logger.warning(f"Validator {validator_id} not selected for {request_id}")
            return None

        # Check not already voted
        if any(v.validator_id == validator_id for v in request.votes):
            logger.warning(f"Validator {validator_id} already voted on {request_id}")
            return None

        # Check request is active
        if request.status not in [ValidationStatus.IN_PROGRESS, ValidationStatus.RECRUITING]:
            logger.warning(f"Request {request_id} is not accepting votes")
            return None

        # Create vote
        vote = ValidationVote(
            validator_id=validator_id,
            is_valid=is_valid,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence,
        )

        # Set vote weight based on reputation
        profile = self.reputation.get_profile(validator_id)
        if profile:
            vote.weight = profile.get_trust_weight()

        request.votes.append(vote)

        # Start if we just got first vote
        if request.status == ValidationStatus.RECRUITING:
            request.status = ValidationStatus.IN_PROGRESS
            request.started_at = datetime.now()

        # Check if quorum reached
        if len(request.votes) >= request.min_validators:
            request.status = ValidationStatus.QUORUM_REACHED
            self._try_complete(request_id)

        return vote

    def _try_complete(self, request_id: str) -> Optional[ConsensusResult]:
        """Try to complete validation if quorum reached."""
        request = self.requests.get(request_id)
        if not request:
            return None

        if len(request.votes) < request.min_validators:
            return None

        # Calculate weighted consensus
        weighted_for = sum(
            v.weight * v.confidence
            for v in request.votes if v.is_valid
        )
        weighted_against = sum(
            v.weight * v.confidence
            for v in request.votes if not v.is_valid
        )

        total_weighted = weighted_for + weighted_against
        if total_weighted == 0:
            return None

        agreement_ratio = max(weighted_for, weighted_against) / total_weighted
        is_valid = weighted_for > weighted_against

        # Calculate overall confidence
        avg_confidence = sum(v.confidence for v in request.votes) / len(request.votes)
        overall_confidence = avg_confidence * agreement_ratio

        # Group validators
        agreed = [v.validator_id for v in request.votes if v.is_valid == is_valid]
        disagreed = [v.validator_id for v in request.votes if v.is_valid != is_valid]

        # Calculate duration
        duration = 0.0
        if request.started_at:
            duration = (datetime.now() - request.started_at).total_seconds() / 3600

        result = ConsensusResult(
            request_id=request_id,
            finding_id=request.finding_id,
            is_valid=is_valid,
            confidence=overall_confidence,
            agreement_ratio=agreement_ratio if is_valid else (1 - agreement_ratio),
            total_votes=len(request.votes),
            weighted_for=weighted_for,
            weighted_against=weighted_against,
            validators_agreed=agreed,
            validators_disagreed=disagreed,
            duration_hours=duration,
        )

        # Update request status
        request.status = ValidationStatus.COMPLETED
        request.completed_at = datetime.now()

        self.results[request_id] = result
        return result

    def get_result(self, request_id: str) -> Optional[ConsensusResult]:
        """Get consensus result for a request."""
        return self.results.get(request_id)

    def check_expired(self) -> List[str]:
        """Check for expired validation requests."""
        expired = []
        for request_id, request in self.requests.items():
            if request.is_expired() and request.status != ValidationStatus.EXPIRED:
                request.status = ValidationStatus.EXPIRED
                expired.append(request_id)
        return expired

    def get_pending_for_validator(self, validator_id: str) -> List[ValidationRequest]:
        """Get pending validation requests for a validator."""
        pending = []
        for request in self.requests.values():
            if request.status in [ValidationStatus.RECRUITING, ValidationStatus.IN_PROGRESS]:
                if validator_id in request.selected_validators:
                    if not any(v.validator_id == validator_id for v in request.votes):
                        pending.append(request)
        return pending

    def get_statistics(self) -> Dict[str, Any]:
        """Get consensus system statistics."""
        total = len(self.requests)
        completed = sum(1 for r in self.requests.values() if r.status == ValidationStatus.COMPLETED)

        avg_votes = 0
        avg_agreement = 0
        if self.results:
            avg_votes = sum(r.total_votes for r in self.results.values()) / len(self.results)
            avg_agreement = sum(r.agreement_ratio for r in self.results.values()) / len(self.results)

        valid_findings = sum(1 for r in self.results.values() if r.is_valid)
        strong_consensus = sum(1 for r in self.results.values() if r.is_strong_consensus())

        return {
            "total_requests": total,
            "completed": completed,
            "pending": total - completed,
            "average_votes_per_request": round(avg_votes, 1),
            "average_agreement_ratio": round(avg_agreement, 3),
            "findings_validated": valid_findings,
            "findings_rejected": len(self.results) - valid_findings,
            "strong_consensus_rate": round(strong_consensus / len(self.results), 3) if self.results else 0,
        }
