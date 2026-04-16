"""
Collaborative Network

Main orchestration layer for the collaborative audit network.
Coordinates findings, reputation, consensus, and bounties.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json
import logging

from alphaswarm_sol.collab.findings import (
    AuditFinding,
    FindingStatus,
    FindingSubmission,
    FindingRegistry,
    FindingVote,
)
from alphaswarm_sol.collab.reputation import (
    AuditorProfile,
    ReputationSystem,
    ReputationAction,
    ReputationLevel,
)
from alphaswarm_sol.collab.consensus import (
    ConsensusValidator,
    ConsensusResult,
    ValidationRequest,
    ValidationStatus,
    ValidatorSelector,
)

logger = logging.getLogger(__name__)


@dataclass
class NetworkConfig:
    """Configuration for the collaborative network."""
    # Validation settings
    min_validators: int = 5
    max_validators: int = 15
    quorum_threshold: float = 0.6
    validation_timeout_hours: int = 72

    # Reputation settings
    min_reputation_to_submit: int = 0      # Newcomers can submit
    min_reputation_to_validate: int = 100  # Need some reputation to validate
    min_reputation_for_bounties: int = 50  # Need some reputation for bounties

    # Rate limiting
    max_submissions_per_day: int = 10
    max_validations_per_day: int = 50

    # Severity weights for reputation
    severity_weights: Dict[str, float] = field(default_factory=lambda: {
        "critical": 2.0,
        "high": 1.5,
        "medium": 1.0,
        "low": 0.5,
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_validators": self.min_validators,
            "quorum_threshold": self.quorum_threshold,
            "validation_timeout_hours": self.validation_timeout_hours,
            "min_reputation_to_submit": self.min_reputation_to_submit,
            "min_reputation_to_validate": self.min_reputation_to_validate,
        }


class NetworkEventType(Enum):
    """Types of network events."""
    FINDING_SUBMITTED = "finding_submitted"
    FINDING_VALIDATED = "finding_validated"
    FINDING_REJECTED = "finding_rejected"
    AUDITOR_JOINED = "auditor_joined"
    AUDITOR_LEVELED_UP = "auditor_leveled_up"
    BOUNTY_CREATED = "bounty_created"
    BOUNTY_CLAIMED = "bounty_claimed"
    CONSENSUS_REACHED = "consensus_reached"


@dataclass
class NetworkEvent:
    """An event in the network."""
    event_type: NetworkEventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class NetworkStatistics:
    """Network-wide statistics."""
    total_auditors: int
    active_auditors: int
    total_findings: int
    confirmed_findings: int
    rejected_findings: int
    pending_validations: int
    total_validations_performed: int
    average_reputation: float
    by_severity: Dict[str, int]
    by_vulnerability_type: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_auditors": self.total_auditors,
            "active_auditors": self.active_auditors,
            "total_findings": self.total_findings,
            "confirmed_findings": self.confirmed_findings,
            "rejected_findings": self.rejected_findings,
            "pending_validations": self.pending_validations,
            "average_reputation": round(self.average_reputation, 1),
            "by_severity": self.by_severity,
            "top_vulnerability_types": dict(
                sorted(self.by_vulnerability_type.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
        }


class CollaborativeNetwork:
    """
    Main collaborative audit network.

    Coordinates:
    - Finding submission and storage
    - Validator selection and consensus
    - Reputation tracking
    - Event notifications
    """

    def __init__(self, config: Optional[NetworkConfig] = None):
        self.config = config or NetworkConfig()

        # Core components
        self.findings = FindingRegistry()
        self.reputation = ReputationSystem()
        self.selector = ValidatorSelector(self.reputation)
        self.consensus = ConsensusValidator(self.reputation, self.selector)

        # Event tracking
        self.events: List[NetworkEvent] = []
        self._event_handlers: Dict[NetworkEventType, List[Callable]] = {
            t: [] for t in NetworkEventType
        }

        # Indexes
        self._by_vulnerability_type: Dict[str, List[str]] = {}
        self._submission_counts: Dict[str, Dict[str, int]] = {}  # auditor -> date -> count

    def register_auditor(
        self,
        auditor_id: str,
        name: Optional[str] = None,
        expertise: Optional[List[str]] = None
    ) -> AuditorProfile:
        """Register a new auditor in the network."""
        profile = self.reputation.register_auditor(auditor_id, name)

        if expertise:
            self.selector.register_expertise(auditor_id, expertise)

        self._emit_event(NetworkEventType.AUDITOR_JOINED, {
            "auditor_id": auditor_id,
            "name": name,
        })

        return profile

    def submit_finding(
        self,
        auditor_id: str,
        submission: FindingSubmission,
        auto_validate: bool = True
    ) -> Optional[AuditFinding]:
        """
        Submit a new finding to the network.

        Args:
            auditor_id: The submitting auditor's ID
            submission: The finding submission
            auto_validate: Whether to automatically start validation

        Returns:
            The created AuditFinding, or None if submission failed
        """
        # Check auditor exists
        profile = self.reputation.get_or_create_profile(auditor_id)

        # Check reputation minimum
        if profile.reputation_score < self.config.min_reputation_to_submit:
            logger.warning(f"Auditor {auditor_id} reputation too low to submit")
            return None

        # Check rate limit
        if not self._check_submission_rate_limit(auditor_id):
            logger.warning(f"Auditor {auditor_id} exceeded submission rate limit")
            return None

        # Create finding
        finding = submission.to_finding(auditor_id)
        finding_id = self.findings.submit(finding)

        # Update indexes
        if finding.vulnerability_type not in self._by_vulnerability_type:
            self._by_vulnerability_type[finding.vulnerability_type] = []
        self._by_vulnerability_type[finding.vulnerability_type].append(finding_id)

        # Update submission count
        self.reputation.record_finding_submitted(auditor_id)
        self._record_submission(auditor_id)

        # Emit event
        self._emit_event(NetworkEventType.FINDING_SUBMITTED, {
            "finding_id": finding_id,
            "auditor_id": auditor_id,
            "vulnerability_type": finding.vulnerability_type,
            "severity": finding.severity,
        })

        # Auto-start validation
        if auto_validate:
            self.start_validation(finding_id)

        return finding

    def start_validation(self, finding_id: str) -> Optional[ValidationRequest]:
        """Start consensus validation for a finding."""
        finding = self.findings.get(finding_id)
        if not finding:
            logger.warning(f"Finding not found: {finding_id}")
            return None

        # Create validation request
        request = self.consensus.create_validation_request(
            finding_id=finding_id,
            contract_hash=finding.contract_hash,
            vulnerability_type=finding.vulnerability_type,
            severity=finding.severity,
            description=finding.description,
            submitter_id=finding.auditor_id,
            min_validators=self.config.min_validators,
        )

        # Start validation
        if request.status != ValidationStatus.FAILED:
            self.consensus.start_validation(request.request_id)
            finding.status = FindingStatus.VALIDATING

        return request

    def submit_validation(
        self,
        finding_id: str,
        validator_id: str,
        is_valid: bool,
        confidence: float,
        reasoning: str,
        evidence: Optional[str] = None
    ) -> Optional[ConsensusResult]:
        """
        Submit a validation vote for a finding.

        Returns ConsensusResult if consensus was reached, None otherwise.
        """
        # Check validator reputation
        profile = self.reputation.get_profile(validator_id)
        if not profile or profile.reputation_score < self.config.min_reputation_to_validate:
            logger.warning(f"Validator {validator_id} not eligible")
            return None

        # Find the validation request for this finding
        request = None
        for req in self.consensus.requests.values():
            if req.finding_id == finding_id and req.status in [
                ValidationStatus.RECRUITING,
                ValidationStatus.IN_PROGRESS,
                ValidationStatus.QUORUM_REACHED
            ]:
                request = req
                break

        if not request:
            logger.warning(f"No active validation for finding {finding_id}")
            return None

        # Submit vote
        vote = self.consensus.submit_vote(
            request_id=request.request_id,
            validator_id=validator_id,
            is_valid=is_valid,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence,
        )

        if not vote:
            return None

        # Check if consensus reached
        result = self.consensus.get_result(request.request_id)
        if result:
            self._process_consensus_result(result)
            return result

        return None

    def _process_consensus_result(self, result: ConsensusResult):
        """Process a consensus result and update reputation."""
        finding = self.findings.get(result.finding_id)
        if not finding:
            return

        # Update finding status
        if result.is_valid:
            finding.status = FindingStatus.CONFIRMED
            self._emit_event(NetworkEventType.FINDING_VALIDATED, {
                "finding_id": finding.finding_id,
                "auditor_id": finding.auditor_id,
                "confidence": result.confidence,
            })

            # Reward the submitter
            is_high = finding.severity in ["critical", "high"]
            self.reputation.record_finding_confirmed(
                finding.auditor_id,
                finding.finding_id,
                is_first=True,  # TODO: Check if duplicate
                is_high=is_high
            )

        else:
            finding.status = FindingStatus.REJECTED
            self._emit_event(NetworkEventType.FINDING_REJECTED, {
                "finding_id": finding.finding_id,
                "auditor_id": finding.auditor_id,
            })

            # Penalize the submitter
            self.reputation.record_finding_rejected(
                finding.auditor_id,
                finding.finding_id
            )

        # Update validator reputation
        for validator_id in result.validators_agreed:
            self.reputation.record_validation(validator_id, True, result.finding_id)

        for validator_id in result.validators_disagreed:
            self.reputation.record_validation(validator_id, False, result.finding_id)

        # Emit consensus event
        self._emit_event(NetworkEventType.CONSENSUS_REACHED, {
            "finding_id": finding.finding_id,
            "is_valid": result.is_valid,
            "agreement_ratio": result.agreement_ratio,
            "total_votes": result.total_votes,
        })

    def get_findings_for_contract(self, contract_hash: str) -> List[AuditFinding]:
        """Get all findings for a contract."""
        return self.findings.get_for_contract(contract_hash)

    def get_confirmed_findings(
        self,
        vulnerability_type: Optional[str] = None,
        min_severity: Optional[str] = None
    ) -> List[AuditFinding]:
        """Get confirmed findings with optional filters."""
        confirmed = self.findings.get_confirmed()

        if vulnerability_type:
            confirmed = [f for f in confirmed if f.vulnerability_type == vulnerability_type]

        if min_severity:
            severity_order = ["low", "medium", "high", "critical"]
            min_idx = severity_order.index(min_severity) if min_severity in severity_order else 0
            confirmed = [
                f for f in confirmed
                if f.severity in severity_order[min_idx:]
            ]

        return confirmed

    def get_pending_validations(self, validator_id: str) -> List[ValidationRequest]:
        """Get pending validation requests for a validator."""
        return self.consensus.get_pending_for_validator(validator_id)

    def get_leaderboard(self, limit: int = 10) -> List[AuditorProfile]:
        """Get top auditors by reputation."""
        return self.reputation.get_leaderboard(limit)

    def get_auditor_profile(self, auditor_id: str) -> Optional[Dict[str, Any]]:
        """Get an auditor's full profile with statistics."""
        profile = self.reputation.get_profile(auditor_id)
        if not profile:
            return None

        findings = self.findings.get_by_auditor(auditor_id)

        return {
            **profile.to_dict(),
            "findings": [f.to_dict() for f in findings[:10]],
            "total_findings": len(findings),
        }

    def get_statistics(self) -> NetworkStatistics:
        """Get network-wide statistics."""
        finding_stats = self.findings.get_statistics()
        reputation_stats = self.reputation.get_statistics()
        consensus_stats = self.consensus.get_statistics()

        # Count by severity
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in self.findings.findings.values():
            if finding.severity in by_severity:
                by_severity[finding.severity] += 1

        # Count by vulnerability type
        by_type = {}
        for vuln_type, finding_ids in self._by_vulnerability_type.items():
            by_type[vuln_type] = len(finding_ids)

        return NetworkStatistics(
            total_auditors=reputation_stats["total_auditors"],
            active_auditors=reputation_stats["active_validators"],
            total_findings=finding_stats["total_findings"],
            confirmed_findings=finding_stats["by_status"]["confirmed"],
            rejected_findings=finding_stats["by_status"]["rejected"],
            pending_validations=consensus_stats["pending"],
            total_validations_performed=sum(
                p.validations_performed for p in self.reputation.profiles.values()
            ),
            average_reputation=reputation_stats["average_reputation"],
            by_severity=by_severity,
            by_vulnerability_type=by_type,
        )

    def search_findings(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[AuditFinding]:
        """Search findings by keyword and filters."""
        results = []
        query_lower = query.lower()

        for finding in self.findings.findings.values():
            # Text search
            if query_lower not in finding.title.lower() and \
               query_lower not in finding.description.lower() and \
               query_lower not in finding.vulnerability_type.lower():
                continue

            # Apply filters
            if filters:
                if "severity" in filters and finding.severity != filters["severity"]:
                    continue
                if "status" in filters and finding.status.value != filters["status"]:
                    continue
                if "vulnerability_type" in filters and \
                   finding.vulnerability_type != filters["vulnerability_type"]:
                    continue

            results.append(finding)

        return results

    def _check_submission_rate_limit(self, auditor_id: str) -> bool:
        """Check if auditor can submit (rate limiting)."""
        today = datetime.now().strftime("%Y-%m-%d")
        if auditor_id not in self._submission_counts:
            return True
        if today not in self._submission_counts[auditor_id]:
            return True
        return self._submission_counts[auditor_id][today] < self.config.max_submissions_per_day

    def _record_submission(self, auditor_id: str):
        """Record a submission for rate limiting."""
        today = datetime.now().strftime("%Y-%m-%d")
        if auditor_id not in self._submission_counts:
            self._submission_counts[auditor_id] = {}
        if today not in self._submission_counts[auditor_id]:
            self._submission_counts[auditor_id][today] = 0
        self._submission_counts[auditor_id][today] += 1

    def _emit_event(self, event_type: NetworkEventType, data: Dict[str, Any]):
        """Emit a network event."""
        event = NetworkEvent(event_type=event_type, data=data)
        self.events.append(event)

        # Notify handlers
        for handler in self._event_handlers[event_type]:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    def on_event(self, event_type: NetworkEventType, handler: Callable):
        """Register an event handler."""
        self._event_handlers[event_type].append(handler)

    def export_knowledge_base(self) -> Dict[str, Any]:
        """Export the network's confirmed findings as a knowledge base."""
        confirmed = self.findings.get_confirmed()

        return {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "findings_count": len(confirmed),
            "findings": [
                {
                    "vulnerability_type": f.vulnerability_type,
                    "severity": f.severity,
                    "title": f.title,
                    "description": f.description,
                    "function_name": f.function_name,
                    "recommended_fix": f.recommended_fix,
                    "consensus": f.get_consensus_summary(),
                }
                for f in confirmed
            ],
            "statistics": self.get_statistics().to_dict(),
        }
