"""
Bounty System

Enables competitive audits with rewards for finding vulnerabilities.
Supports timed bounties, severity-based rewards, and fair distribution.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import logging

from alphaswarm_sol.collab.findings import AuditFinding, FindingStatus
from alphaswarm_sol.collab.reputation import ReputationLevel

logger = logging.getLogger(__name__)


class BountyStatus(Enum):
    """Status of a bounty."""
    DRAFT = "draft"               # Not yet active
    ACTIVE = "active"             # Accepting submissions
    REVIEW = "review"             # Submissions under review
    COMPLETED = "completed"       # Bounty ended, rewards distributed
    CANCELLED = "cancelled"       # Cancelled by sponsor


class RewardTier(Enum):
    """Reward tiers based on severity."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


@dataclass
class RewardStructure:
    """Reward structure for a bounty."""
    critical: float = 10000.0
    high: float = 5000.0
    medium: float = 1000.0
    low: float = 250.0
    informational: float = 50.0

    # Bonus multipliers
    first_blood_multiplier: float = 1.5   # First to find a vuln type
    unique_multiplier: float = 1.2         # Only one to find it

    def get_reward(self, severity: str, is_first: bool = False, is_unique: bool = False) -> float:
        """Calculate reward for a finding."""
        base = {
            "critical": self.critical,
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
            "informational": self.informational,
        }.get(severity, 0)

        if is_first:
            base *= self.first_blood_multiplier
        if is_unique:
            base *= self.unique_multiplier

        return base

    def to_dict(self) -> Dict[str, Any]:
        return {
            "critical": self.critical,
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
            "informational": self.informational,
            "first_blood_multiplier": self.first_blood_multiplier,
            "unique_multiplier": self.unique_multiplier,
        }


@dataclass
class BountyScope:
    """Scope of a bounty (what contracts/functions are in scope)."""
    contract_hashes: List[str] = field(default_factory=list)
    included_functions: Optional[List[str]] = None  # None = all
    excluded_functions: List[str] = field(default_factory=list)

    # What's in scope
    in_scope_vulns: List[str] = field(default_factory=list)  # Empty = all
    out_of_scope_vulns: List[str] = field(default_factory=list)

    def is_in_scope(self, contract_hash: str, function_name: Optional[str], vuln_type: str) -> bool:
        """Check if a finding is in scope."""
        # Check contract
        if self.contract_hashes and contract_hash not in self.contract_hashes:
            return False

        # Check function
        if function_name:
            if self.included_functions and function_name not in self.included_functions:
                return False
            if function_name in self.excluded_functions:
                return False

        # Check vulnerability type
        if self.out_of_scope_vulns and vuln_type in self.out_of_scope_vulns:
            return False
        if self.in_scope_vulns and vuln_type not in self.in_scope_vulns:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_count": len(self.contract_hashes),
            "included_functions": self.included_functions,
            "excluded_functions": self.excluded_functions,
            "in_scope_vulns": self.in_scope_vulns,
            "out_of_scope_vulns": self.out_of_scope_vulns,
        }


@dataclass
class BountySubmission:
    """A submission to a bounty."""
    submission_id: str
    bounty_id: str
    auditor_id: str
    finding_id: str

    # Evaluation
    is_valid: bool = False
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None

    # Reward
    reward_amount: float = 0.0
    is_first_blood: bool = False

    # Timing
    submitted_at: datetime = field(default_factory=datetime.now)
    evaluated_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.submission_id:
            self.submission_id = self._generate_id()

    def _generate_id(self) -> str:
        data = f"{self.bounty_id}:{self.auditor_id}:{datetime.now().isoformat()}"
        return f"SUB-{hashlib.sha256(data.encode()).hexdigest()[:12].upper()}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "submission_id": self.submission_id,
            "bounty_id": self.bounty_id,
            "auditor_id": self.auditor_id,
            "finding_id": self.finding_id,
            "is_valid": self.is_valid,
            "is_duplicate": self.is_duplicate,
            "reward_amount": self.reward_amount,
            "is_first_blood": self.is_first_blood,
            "submitted_at": self.submitted_at.isoformat(),
        }


@dataclass
class Bounty:
    """A security bounty program."""
    bounty_id: str
    title: str
    description: str
    sponsor_id: str             # Who's paying

    # Configuration
    scope: BountyScope = field(default_factory=BountyScope)
    rewards: RewardStructure = field(default_factory=RewardStructure)
    total_pool: float = 0.0     # Maximum payout

    # Requirements
    min_reputation: int = 0     # Minimum reputation to participate
    max_participants: Optional[int] = None
    requires_kyc: bool = False

    # Timeline
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    review_period_days: int = 7

    # State
    status: BountyStatus = BountyStatus.DRAFT
    participants: List[str] = field(default_factory=list)
    submissions: List[BountySubmission] = field(default_factory=list)
    total_rewarded: float = 0.0

    # Tracking first blood
    _first_by_vuln_type: Dict[str, str] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.bounty_id:
            self.bounty_id = self._generate_id()

    def _generate_id(self) -> str:
        data = f"{self.title}:{self.sponsor_id}:{datetime.now().isoformat()}"
        return f"BOUNTY-{hashlib.sha256(data.encode()).hexdigest()[:8].upper()}"

    def is_active(self) -> bool:
        """Check if bounty is currently accepting submissions."""
        if self.status != BountyStatus.ACTIVE:
            return False
        now = datetime.now()
        if self.start_time and now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False
        return True

    def can_participate(self, auditor_id: str, reputation: int) -> bool:
        """Check if an auditor can participate."""
        if reputation < self.min_reputation:
            return False
        if self.max_participants and len(self.participants) >= self.max_participants:
            if auditor_id not in self.participants:
                return False
        return True

    def get_remaining_pool(self) -> float:
        """Get remaining reward pool."""
        return max(0, self.total_pool - self.total_rewarded)

    def get_time_remaining(self) -> Optional[timedelta]:
        """Get time remaining until bounty ends."""
        if not self.end_time:
            return None
        remaining = self.end_time - datetime.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    def to_dict(self) -> Dict[str, Any]:
        time_remaining = self.get_time_remaining()
        return {
            "bounty_id": self.bounty_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "is_active": self.is_active(),
            "total_pool": self.total_pool,
            "total_rewarded": self.total_rewarded,
            "remaining_pool": self.get_remaining_pool(),
            "participants": len(self.participants),
            "submissions": len(self.submissions),
            "rewards": self.rewards.to_dict(),
            "scope": self.scope.to_dict(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "time_remaining_hours": time_remaining.total_seconds() / 3600 if time_remaining else None,
        }


class BountyManager:
    """
    Manages bounty programs.
    """

    def __init__(self):
        self.bounties: Dict[str, Bounty] = {}
        self._by_sponsor: Dict[str, List[str]] = {}
        self._by_participant: Dict[str, List[str]] = {}

    def create_bounty(
        self,
        title: str,
        description: str,
        sponsor_id: str,
        total_pool: float,
        scope: Optional[BountyScope] = None,
        rewards: Optional[RewardStructure] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_reputation: int = 0
    ) -> Bounty:
        """Create a new bounty."""
        bounty = Bounty(
            bounty_id="",
            title=title,
            description=description,
            sponsor_id=sponsor_id,
            scope=scope or BountyScope(),
            rewards=rewards or RewardStructure(),
            total_pool=total_pool,
            min_reputation=min_reputation,
            start_time=start_time,
            end_time=end_time,
        )

        self.bounties[bounty.bounty_id] = bounty

        # Index
        if sponsor_id not in self._by_sponsor:
            self._by_sponsor[sponsor_id] = []
        self._by_sponsor[sponsor_id].append(bounty.bounty_id)

        return bounty

    def activate_bounty(self, bounty_id: str) -> bool:
        """Activate a bounty to start accepting submissions."""
        bounty = self.bounties.get(bounty_id)
        if not bounty:
            return False

        if bounty.status != BountyStatus.DRAFT:
            return False

        bounty.status = BountyStatus.ACTIVE
        if not bounty.start_time:
            bounty.start_time = datetime.now()

        return True

    def join_bounty(self, bounty_id: str, auditor_id: str, reputation: int) -> bool:
        """Join a bounty as a participant."""
        bounty = self.bounties.get(bounty_id)
        if not bounty:
            return False

        if not bounty.is_active():
            return False

        if not bounty.can_participate(auditor_id, reputation):
            return False

        if auditor_id not in bounty.participants:
            bounty.participants.append(auditor_id)

            if auditor_id not in self._by_participant:
                self._by_participant[auditor_id] = []
            self._by_participant[auditor_id].append(bounty_id)

        return True

    def submit_finding(
        self,
        bounty_id: str,
        auditor_id: str,
        finding: AuditFinding
    ) -> Optional[BountySubmission]:
        """Submit a finding to a bounty."""
        bounty = self.bounties.get(bounty_id)
        if not bounty:
            logger.warning(f"Bounty not found: {bounty_id}")
            return None

        if not bounty.is_active():
            logger.warning(f"Bounty {bounty_id} is not active")
            return None

        if auditor_id not in bounty.participants:
            logger.warning(f"Auditor {auditor_id} not participating in {bounty_id}")
            return None

        # Check scope
        if not bounty.scope.is_in_scope(
            finding.contract_hash,
            finding.function_name,
            finding.vulnerability_type
        ):
            logger.warning(f"Finding out of scope for bounty {bounty_id}")
            return None

        submission = BountySubmission(
            submission_id="",
            bounty_id=bounty_id,
            auditor_id=auditor_id,
            finding_id=finding.finding_id,
        )

        bounty.submissions.append(submission)
        return submission

    def evaluate_submission(
        self,
        submission_id: str,
        is_valid: bool,
        is_duplicate: bool = False,
        duplicate_of: Optional[str] = None
    ) -> Optional[BountySubmission]:
        """Evaluate a bounty submission."""
        # Find submission
        submission = None
        bounty = None
        for b in self.bounties.values():
            for s in b.submissions:
                if s.submission_id == submission_id:
                    submission = s
                    bounty = b
                    break

        if not submission or not bounty:
            return None

        submission.is_valid = is_valid
        submission.is_duplicate = is_duplicate
        submission.duplicate_of = duplicate_of
        submission.evaluated_at = datetime.now()

        # Calculate reward if valid and not duplicate
        if is_valid and not is_duplicate:
            # Need to get the finding to know severity
            # For now, assume we have a callback or the finding is passed
            # This is a simplified version
            submission.reward_amount = self._calculate_reward(bounty, submission)

            # Update bounty totals
            bounty.total_rewarded += submission.reward_amount

        return submission

    def _calculate_reward(self, bounty: Bounty, submission: BountySubmission) -> float:
        """Calculate reward for a submission."""
        # This would normally look up the finding severity
        # For demo, use medium as default
        severity = "medium"

        # Check first blood
        vuln_type = "unknown"  # Would come from finding
        is_first = False
        if vuln_type not in bounty._first_by_vuln_type:
            bounty._first_by_vuln_type[vuln_type] = submission.auditor_id
            is_first = True
            submission.is_first_blood = True

        # Check if unique
        is_unique = sum(
            1 for s in bounty.submissions
            if s.is_valid and not s.is_duplicate
        ) == 1

        reward = bounty.rewards.get_reward(severity, is_first, is_unique)

        # Cap at remaining pool
        reward = min(reward, bounty.get_remaining_pool())

        return reward

    def end_bounty(self, bounty_id: str) -> Optional[Dict[str, Any]]:
        """End a bounty and finalize results."""
        bounty = self.bounties.get(bounty_id)
        if not bounty:
            return None

        bounty.status = BountyStatus.COMPLETED

        # Generate summary
        valid_submissions = [s for s in bounty.submissions if s.is_valid and not s.is_duplicate]
        rewards_by_auditor: Dict[str, float] = {}
        for s in valid_submissions:
            if s.auditor_id not in rewards_by_auditor:
                rewards_by_auditor[s.auditor_id] = 0
            rewards_by_auditor[s.auditor_id] += s.reward_amount

        return {
            "bounty_id": bounty_id,
            "title": bounty.title,
            "status": "completed",
            "total_participants": len(bounty.participants),
            "total_submissions": len(bounty.submissions),
            "valid_findings": len(valid_submissions),
            "total_rewarded": bounty.total_rewarded,
            "remaining_pool": bounty.get_remaining_pool(),
            "rewards_by_auditor": rewards_by_auditor,
            "top_hunters": sorted(
                rewards_by_auditor.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
        }

    def cancel_bounty(self, bounty_id: str) -> bool:
        """Cancel a bounty."""
        bounty = self.bounties.get(bounty_id)
        if not bounty:
            return False

        if bounty.status == BountyStatus.COMPLETED:
            return False

        bounty.status = BountyStatus.CANCELLED
        return True

    def get_active_bounties(self) -> List[Bounty]:
        """Get all active bounties."""
        return [b for b in self.bounties.values() if b.is_active()]

    def get_bounties_for_auditor(self, auditor_id: str) -> List[Bounty]:
        """Get bounties an auditor is participating in."""
        bounty_ids = self._by_participant.get(auditor_id, [])
        return [self.bounties[bid] for bid in bounty_ids if bid in self.bounties]

    def get_bounties_by_sponsor(self, sponsor_id: str) -> List[Bounty]:
        """Get bounties created by a sponsor."""
        bounty_ids = self._by_sponsor.get(sponsor_id, [])
        return [self.bounties[bid] for bid in bounty_ids if bid in self.bounties]

    def get_leaderboard(self, bounty_id: str) -> List[Dict[str, Any]]:
        """Get leaderboard for a specific bounty."""
        bounty = self.bounties.get(bounty_id)
        if not bounty:
            return []

        rewards_by_auditor: Dict[str, Dict[str, Any]] = {}
        for s in bounty.submissions:
            if not s.is_valid or s.is_duplicate:
                continue

            if s.auditor_id not in rewards_by_auditor:
                rewards_by_auditor[s.auditor_id] = {
                    "auditor_id": s.auditor_id,
                    "total_reward": 0,
                    "findings_count": 0,
                    "first_bloods": 0,
                }

            rewards_by_auditor[s.auditor_id]["total_reward"] += s.reward_amount
            rewards_by_auditor[s.auditor_id]["findings_count"] += 1
            if s.is_first_blood:
                rewards_by_auditor[s.auditor_id]["first_bloods"] += 1

        return sorted(
            rewards_by_auditor.values(),
            key=lambda x: x["total_reward"],
            reverse=True
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get bounty system statistics."""
        total_bounties = len(self.bounties)
        active = len(self.get_active_bounties())
        completed = sum(1 for b in self.bounties.values() if b.status == BountyStatus.COMPLETED)

        total_pool = sum(b.total_pool for b in self.bounties.values())
        total_rewarded = sum(b.total_rewarded for b in self.bounties.values())
        total_participants = len(self._by_participant)

        return {
            "total_bounties": total_bounties,
            "active_bounties": active,
            "completed_bounties": completed,
            "total_pool": total_pool,
            "total_rewarded": total_rewarded,
            "total_participants": total_participants,
            "average_pool": total_pool / total_bounties if total_bounties else 0,
        }
