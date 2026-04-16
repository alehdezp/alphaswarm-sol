"""Batch dismissal system with cross-agent verification.

Enables efficient dismissal of related false positives while ensuring
reliability through multi-agent verification per PHILOSOPHY.md.

Key principles:
- Batch dismissal requires 2-of-2 agent agreement
- All dismissals are logged and challengeable
- Conflict = NOT dismissed (conservative)
- One re-challenge per dismissal, then final

Usage:
    from alphaswarm_sol.orchestration.dismissal import (
        BatchDismissal, DismissalReason, DismissalCategory, dismiss_beads
    )

    # Create a dismissal reason
    reason = DismissalReason(
        category=DismissalCategory.FALSE_POSITIVE,
        explanation="SafeMath library usage prevents overflow",
        evidence=["Uses checked arithmetic", "Version >= 0.8.0"],
        pattern_id="integer-overflow"
    )

    # Propose batch dismissal (needs verification)
    dismissal = BatchDismissal(Path(".vrs/dismissals"))
    log_id = dismissal.propose_dismissal(
        bead_ids=["VKG-001", "VKG-002"],
        reason=reason,
        proposing_agent="verifier-agent-001"
    )

    # Second agent verifies
    agreed = dismissal.verify_dismissal(
        log_id=log_id,
        verifying_agent="verifier-agent-002",
        agrees=True
    )

    # User can challenge within challenge window
    if not satisfied:
        dismissal.challenge_dismissal(log_id, "user", "Guard may be bypassable")
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib
import json
import logging
import yaml

logger = logging.getLogger(__name__)


class DismissalCategory(str, Enum):
    """Categories for batch dismissal.

    Provides structured categorization for why beads are being dismissed,
    enabling pattern tracking and future automation improvements.

    Categories:
    - FALSE_POSITIVE: Pattern matched but code is actually safe
    - LIBRARY_CODE: Finding in trusted library code (OpenZeppelin, etc.)
    - INTENTIONAL_PATTERN: Developer intentionally used this pattern
    - MITIGATED: Vulnerability exists but is mitigated elsewhere
    - DUPLICATE: Same finding reported by multiple tools
    - OUT_OF_SCOPE: Outside the audit scope

    Usage:
        category = DismissalCategory.FALSE_POSITIVE
        category_str = category.value  # "false_positive"
    """

    FALSE_POSITIVE = "false_positive"
    LIBRARY_CODE = "library_code"
    INTENTIONAL_PATTERN = "intentional_pattern"
    MITIGATED = "mitigated"
    DUPLICATE = "duplicate"
    OUT_OF_SCOPE = "out_of_scope"

    @classmethod
    def from_string(cls, value: str) -> "DismissalCategory":
        """Create DismissalCategory from string, case-insensitive.

        Args:
            value: Category string

        Returns:
            DismissalCategory enum value

        Raises:
            ValueError: If value is not a valid category
        """
        normalized = value.lower().strip().replace("-", "_").replace(" ", "_")
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(f"Unknown dismissal category: {value}")


@dataclass
class DismissalReason:
    """Reason for batch dismissal with evidence.

    Captures the complete rationale for dismissing one or more beads,
    including supporting evidence that can be audited later.

    Attributes:
        category: Dismissal category (e.g., FALSE_POSITIVE)
        explanation: Human-readable explanation of why dismissing
        evidence: List of code references or facts supporting dismissal
        pattern_id: Pattern ID if dismissing a known FP pattern (optional)

    Usage:
        reason = DismissalReason(
            category=DismissalCategory.LIBRARY_CODE,
            explanation="OpenZeppelin SafeMath v4.x is trusted",
            evidence=[
                "File: @openzeppelin/contracts/utils/math/SafeMath.sol",
                "Version: 4.9.0 (audited)"
            ],
            pattern_id="integer-overflow"
        )
    """

    category: DismissalCategory
    explanation: str
    evidence: List[str]
    pattern_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category.value,
            "explanation": self.explanation,
            "evidence": self.evidence,
            "pattern_id": self.pattern_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DismissalReason":
        """Create DismissalReason from dictionary.

        Args:
            data: Dictionary with reason fields

        Returns:
            DismissalReason instance
        """
        category_str = data.get("category", "false_positive")
        category = DismissalCategory.from_string(category_str)

        return cls(
            category=category,
            explanation=str(data.get("explanation", "")),
            evidence=list(data.get("evidence", [])),
            pattern_id=data.get("pattern_id"),
        )


@dataclass
class DismissalLog:
    """Log entry for a batch dismissal.

    Tracks the complete lifecycle of a dismissal:
    1. Proposal by first agent
    2. Verification by second agent (2-of-2 agreement required)
    3. Optional challenge by user
    4. Final resolution

    Attributes:
        id: Unique dismissal log ID
        bead_ids: List of bead IDs being dismissed
        reason: Dismissal reason with evidence
        dismissed_by: Agent ID that proposed dismissal
        dismissed_at: When dismissal was proposed
        verified_by: Second agent ID (for cross-verification)
        verified_at: When verification occurred
        consensus: True if both agents agreed to dismiss
        challenged: Whether user challenged this dismissal
        challenge_result: Reason for challenge or resolution
        challenge_by: Who challenged (user ID)
        challenge_at: When challenge was made

    Usage:
        log = DismissalLog(
            id="DISM-001",
            bead_ids=["VKG-001", "VKG-002"],
            reason=reason,
            dismissed_by="agent-001",
            dismissed_at=datetime.now(),
            consensus=False  # Not yet verified
        )
    """

    id: str
    bead_ids: List[str]
    reason: DismissalReason
    dismissed_by: str
    dismissed_at: datetime
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    consensus: bool = False
    challenged: bool = False
    challenge_result: Optional[str] = None
    challenge_by: Optional[str] = None
    challenge_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "bead_ids": self.bead_ids,
            "reason": self.reason.to_dict(),
            "dismissed_by": self.dismissed_by,
            "dismissed_at": self.dismissed_at.isoformat(),
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "consensus": self.consensus,
            "challenged": self.challenged,
            "challenge_result": self.challenge_result,
            "challenge_by": self.challenge_by,
            "challenge_at": self.challenge_at.isoformat() if self.challenge_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DismissalLog":
        """Create DismissalLog from dictionary.

        Args:
            data: Dictionary with log fields

        Returns:
            DismissalLog instance
        """
        # Parse timestamps
        dismissed_at_str = data.get("dismissed_at")
        if isinstance(dismissed_at_str, str):
            dismissed_at = datetime.fromisoformat(dismissed_at_str)
        else:
            dismissed_at = datetime.now()

        verified_at_str = data.get("verified_at")
        verified_at = None
        if isinstance(verified_at_str, str):
            verified_at = datetime.fromisoformat(verified_at_str)

        challenge_at_str = data.get("challenge_at")
        challenge_at = None
        if isinstance(challenge_at_str, str):
            challenge_at = datetime.fromisoformat(challenge_at_str)

        return cls(
            id=str(data.get("id", "")),
            bead_ids=list(data.get("bead_ids", [])),
            reason=DismissalReason.from_dict(data.get("reason", {})),
            dismissed_by=str(data.get("dismissed_by", "")),
            dismissed_at=dismissed_at,
            verified_by=data.get("verified_by"),
            verified_at=verified_at,
            consensus=bool(data.get("consensus", False)),
            challenged=bool(data.get("challenged", False)),
            challenge_result=data.get("challenge_result"),
            challenge_by=data.get("challenge_by"),
            challenge_at=challenge_at,
        )

    @property
    def is_finalized(self) -> bool:
        """Whether this dismissal has been finalized (verified or challenged)."""
        return self.consensus or self.challenged

    @property
    def is_effective(self) -> bool:
        """Whether this dismissal is currently effective (agreed, not challenged)."""
        return self.consensus and not self.challenged


class BatchDismissal:
    """Batch dismissal with cross-agent verification.

    Per CONTEXT.md requirements:
    - Batch dismissal requires 2-of-2 agent agreement
    - All dismissals are logged and challengeable
    - Conflict = NOT dismissed (conservative)
    - One re-challenge per dismissal, then final

    The batch dismissal system enables efficient handling of related
    false positives while maintaining auditability and human oversight.

    Attributes:
        storage_path: Directory for storing dismissal logs
        log_file: Path to the YAML log file

    Usage:
        dismissal = BatchDismissal(Path(".vrs/dismissals"))

        # Propose dismissal (first agent)
        log_id = dismissal.propose_dismissal(
            bead_ids=["VKG-001", "VKG-002"],
            reason=reason,
            proposing_agent="agent-001"
        )

        # Verify dismissal (second agent)
        agreed = dismissal.verify_dismissal(
            log_id=log_id,
            verifying_agent="agent-002",
            agrees=True
        )

        # Get all dismissed beads
        dismissed = dismissal.get_dismissed_beads()
    """

    def __init__(self, storage_path: Path):
        """Initialize batch dismissal system.

        Args:
            storage_path: Directory for storing dismissal logs
        """
        self.storage_path = Path(storage_path)
        self.log_file = self.storage_path / "dismissal_log.yaml"
        self._logs: List[DismissalLog] = []
        self._load_logs()

    def _load_logs(self) -> None:
        """Load existing dismissal logs from storage."""
        if not self.log_file.exists():
            return

        try:
            with open(self.log_file, "r") as f:
                data = yaml.safe_load(f) or {}

            logs_data = data.get("logs", [])
            self._logs = [DismissalLog.from_dict(log) for log in logs_data]
            logger.debug(f"Loaded {len(self._logs)} dismissal logs from {self.log_file}")
        except Exception as e:
            logger.warning(f"Failed to load dismissal logs: {e}")
            self._logs = []

    def _save_logs(self) -> None:
        """Save dismissal logs to storage."""
        self.storage_path.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "logs": [log.to_dict() for log in self._logs],
        }

        try:
            with open(self.log_file, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            logger.debug(f"Saved {len(self._logs)} dismissal logs to {self.log_file}")
        except Exception as e:
            logger.error(f"Failed to save dismissal logs: {e}")
            raise

    def _generate_id(self) -> str:
        """Generate unique dismissal log ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = hashlib.sha256(
            f"{timestamp}-{len(self._logs)}".encode()
        ).hexdigest()[:6]
        return f"DISM-{timestamp}-{random_suffix.upper()}"

    def _get_log(self, log_id: str) -> Optional[DismissalLog]:
        """Get dismissal log by ID.

        Args:
            log_id: Dismissal log ID

        Returns:
            DismissalLog if found, None otherwise
        """
        for log in self._logs:
            if log.id == log_id:
                return log
        return None

    def propose_dismissal(
        self,
        bead_ids: List[str],
        reason: DismissalReason,
        proposing_agent: str,
    ) -> str:
        """Propose batch dismissal - needs verification.

        Creates a dismissal proposal that requires a second agent to verify
        before the beads are actually dismissed.

        Args:
            bead_ids: List of bead IDs to dismiss
            reason: Dismissal reason with evidence
            proposing_agent: ID of the agent proposing dismissal

        Returns:
            Dismissal log ID for tracking

        Raises:
            ValueError: If bead_ids is empty

        Usage:
            log_id = dismissal.propose_dismissal(
                bead_ids=["VKG-001", "VKG-002"],
                reason=reason,
                proposing_agent="agent-001"
            )
        """
        if not bead_ids:
            raise ValueError("Cannot propose dismissal with empty bead_ids")

        log_id = self._generate_id()
        log = DismissalLog(
            id=log_id,
            bead_ids=bead_ids,
            reason=reason,
            dismissed_by=proposing_agent,
            dismissed_at=datetime.now(),
            verified_by=None,
            verified_at=None,
            consensus=False,  # Not yet verified
        )
        self._logs.append(log)
        self._save_logs()

        logger.info(
            f"Dismissal proposed: {log_id} for {len(bead_ids)} beads "
            f"by {proposing_agent} ({reason.category.value})"
        )
        return log_id

    def verify_dismissal(
        self,
        log_id: str,
        verifying_agent: str,
        agrees: bool,
        counter_reason: Optional[str] = None,
    ) -> bool:
        """Second agent verifies dismissal.

        Per CONTEXT.md: 2-of-2 agreement required for batch dismissals.
        If agents disagree, beads are NOT dismissed (conservative).

        Args:
            log_id: Dismissal log ID to verify
            verifying_agent: ID of the verifying agent
            agrees: Whether the verifying agent agrees with dismissal
            counter_reason: Reason for disagreement (if not agreeing)

        Returns:
            True if dismissal is finalized (both agree), False if disagreement

        Raises:
            ValueError: If log not found or agent tries to self-verify

        Usage:
            agreed = dismissal.verify_dismissal(
                log_id="DISM-001",
                verifying_agent="agent-002",
                agrees=True
            )
            if agreed:
                print("Beads dismissed")
            else:
                print("Dismissal rejected - beads remain active")
        """
        log = self._get_log(log_id)
        if not log:
            raise ValueError(f"Dismissal log not found: {log_id}")

        if log.dismissed_by == verifying_agent:
            raise ValueError(
                f"Cannot self-verify dismissal. Proposing agent: {log.dismissed_by}, "
                f"verifying agent: {verifying_agent}"
            )

        if log.verified_by is not None:
            raise ValueError(f"Dismissal already verified by: {log.verified_by}")

        log.verified_by = verifying_agent
        log.verified_at = datetime.now()
        log.consensus = agrees

        if not agrees:
            # Disagreement -> NOT dismissed, log counter reason
            log.challenge_result = counter_reason or "Verifying agent disagreed"
            logger.info(
                f"Dismissal rejected: {log_id} - {verifying_agent} disagreed. "
                f"Reason: {log.challenge_result}"
            )
        else:
            logger.info(
                f"Dismissal verified: {log_id} - consensus reached. "
                f"{len(log.bead_ids)} beads dismissed."
            )

        self._save_logs()
        return agrees

    def challenge_dismissal(
        self,
        log_id: str,
        challenger: str,
        reason: str,
    ) -> bool:
        """User challenges a dismissal.

        Per CONTEXT.md: One re-challenge per dismissal, then final.
        Challenges mark dismissal for re-verification and reopen beads.

        Args:
            log_id: Dismissal log ID to challenge
            challenger: ID of the challenger (user or agent)
            reason: Reason for challenging

        Returns:
            True if challenge was recorded

        Raises:
            ValueError: If log not found or already challenged

        Usage:
            dismissal.challenge_dismissal(
                log_id="DISM-001",
                challenger="user",
                reason="Guard may be bypassable via flash loan"
            )
        """
        log = self._get_log(log_id)
        if not log:
            raise ValueError(f"Dismissal log not found: {log_id}")

        if log.challenged:
            raise ValueError(
                f"Dismissal already challenged (one challenge limit). "
                f"Previous challenge by: {log.challenge_by}"
            )

        log.challenged = True
        log.challenge_result = reason
        log.challenge_by = challenger
        log.challenge_at = datetime.now()
        log.consensus = False  # Reopen for verification

        logger.info(
            f"Dismissal challenged: {log_id} by {challenger}. "
            f"Reason: {reason}. Beads reopened."
        )

        self._save_logs()
        return True

    def get_dismissed_beads(self) -> List[str]:
        """Get all successfully dismissed bead IDs.

        Returns beads that have:
        - Consensus (2-of-2 agreement)
        - Not been challenged

        Returns:
            List of bead IDs that are effectively dismissed
        """
        dismissed: List[str] = []
        for log in self._logs:
            if log.is_effective:
                dismissed.extend(log.bead_ids)
        return dismissed

    def get_pending_verifications(self) -> List[DismissalLog]:
        """Get dismissals awaiting verification.

        Returns:
            List of DismissalLog entries that need second agent verification
        """
        return [
            log
            for log in self._logs
            if not log.consensus and log.verified_by is None and not log.challenged
        ]

    def get_challenges(self) -> List[DismissalLog]:
        """Get challenged dismissals.

        Returns:
            List of DismissalLog entries that have been challenged
        """
        return [log for log in self._logs if log.challenged]

    def get_all_logs(self) -> List[DismissalLog]:
        """Get all dismissal logs.

        Returns:
            List of all DismissalLog entries
        """
        return list(self._logs)

    def get_log_by_bead(self, bead_id: str) -> Optional[DismissalLog]:
        """Find dismissal log containing a specific bead.

        Args:
            bead_id: Bead ID to search for

        Returns:
            DismissalLog containing the bead, or None
        """
        for log in self._logs:
            if bead_id in log.bead_ids:
                return log
        return None

    def is_bead_dismissed(self, bead_id: str) -> bool:
        """Check if a bead is currently dismissed.

        Args:
            bead_id: Bead ID to check

        Returns:
            True if bead is effectively dismissed
        """
        return bead_id in self.get_dismissed_beads()

    def get_dismissal_stats(self) -> Dict[str, Any]:
        """Get statistics about dismissals.

        Returns:
            Dictionary with dismissal statistics
        """
        total = len(self._logs)
        pending = len(self.get_pending_verifications())
        agreed = sum(1 for log in self._logs if log.consensus and not log.challenged)
        rejected = sum(
            1 for log in self._logs if log.verified_by and not log.consensus
        )
        challenged = len(self.get_challenges())

        # Category breakdown
        by_category: Dict[str, int] = {}
        for log in self._logs:
            cat = log.reason.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "total_proposals": total,
            "pending_verification": pending,
            "agreed": agreed,
            "rejected": rejected,
            "challenged": challenged,
            "beads_dismissed": len(self.get_dismissed_beads()),
            "by_category": by_category,
        }


def dismiss_beads(
    bead_ids: List[str],
    reason: DismissalReason,
    storage_path: Path,
    proposing_agent: str,
) -> str:
    """Convenience function to propose batch dismissal.

    Creates a BatchDismissal instance and proposes dismissal in one call.
    The dismissal still needs verification by a second agent.

    Args:
        bead_ids: List of bead IDs to dismiss
        reason: Dismissal reason with evidence
        storage_path: Directory for storing dismissal logs
        proposing_agent: ID of the agent proposing dismissal

    Returns:
        Dismissal log ID for tracking

    Usage:
        log_id = dismiss_beads(
            bead_ids=["VKG-001", "VKG-002"],
            reason=DismissalReason(
                category=DismissalCategory.FALSE_POSITIVE,
                explanation="SafeMath prevents overflow",
                evidence=["Version >= 0.8.0"]
            ),
            storage_path=Path(".vrs/dismissals"),
            proposing_agent="agent-001"
        )
    """
    dismissal = BatchDismissal(storage_path)
    return dismissal.propose_dismissal(bead_ids, reason, proposing_agent)


# Export for module
__all__ = [
    "DismissalCategory",
    "DismissalReason",
    "DismissalLog",
    "BatchDismissal",
    "dismiss_beads",
]
