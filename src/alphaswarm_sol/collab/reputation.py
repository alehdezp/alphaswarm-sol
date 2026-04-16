"""
Reputation System

Tracks auditor reputation based on finding quality and validation accuracy.
Higher reputation = more weight in consensus.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ReputationAction(Enum):
    """Actions that affect reputation."""
    # Positive
    FINDING_CONFIRMED = "finding_confirmed"     # Finding validated by consensus
    FIRST_DISCOVERY = "first_discovery"         # First to find vulnerability
    VALIDATION_CORRECT = "validation_correct"   # Vote matched consensus
    HIGH_SEVERITY = "high_severity"             # Finding was critical/high

    # Negative
    FINDING_REJECTED = "finding_rejected"       # False positive
    VALIDATION_WRONG = "validation_wrong"       # Vote disagreed with consensus
    SPAM_SUBMISSION = "spam_submission"         # Low-quality submission


class ReputationLevel(Enum):
    """Reputation tier levels."""
    NEWCOMER = "newcomer"         # 0-49
    CONTRIBUTOR = "contributor"   # 50-99
    TRUSTED = "trusted"           # 100-199
    EXPERT = "expert"             # 200-499
    MASTER = "master"             # 500+


@dataclass
class ReputationEvent:
    """A single reputation change event."""
    action: ReputationAction
    points: int
    finding_id: Optional[str] = None
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "points": self.points,
            "finding_id": self.finding_id,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AuditorProfile:
    """
    Profile for an auditor in the network.
    """
    auditor_id: str
    name: Optional[str] = None
    verified: bool = False        # Identity verified

    # Reputation
    reputation_score: int = 50    # Starting reputation
    level: ReputationLevel = ReputationLevel.NEWCOMER
    reputation_history: List[ReputationEvent] = field(default_factory=list)

    # Statistics
    findings_submitted: int = 0
    findings_confirmed: int = 0
    findings_rejected: int = 0
    validations_performed: int = 0
    validations_correct: int = 0

    # Streaks
    current_streak: int = 0       # Consecutive confirmed findings
    best_streak: int = 0

    # Metadata
    joined_at: datetime = field(default_factory=datetime.now)
    last_active: Optional[datetime] = None

    def __post_init__(self):
        self._update_level()

    def _update_level(self):
        """Update reputation level based on score."""
        if self.reputation_score >= 500:
            self.level = ReputationLevel.MASTER
        elif self.reputation_score >= 200:
            self.level = ReputationLevel.EXPERT
        elif self.reputation_score >= 100:
            self.level = ReputationLevel.TRUSTED
        elif self.reputation_score >= 50:
            self.level = ReputationLevel.CONTRIBUTOR
        else:
            self.level = ReputationLevel.NEWCOMER

    def add_reputation(self, action: ReputationAction, points: int, finding_id: Optional[str] = None):
        """Add reputation event."""
        event = ReputationEvent(
            action=action,
            points=points,
            finding_id=finding_id,
            description=f"{action.value}: {points:+d} points",
        )
        self.reputation_history.append(event)
        self.reputation_score = max(0, self.reputation_score + points)
        self._update_level()
        self.last_active = datetime.now()

    def get_trust_weight(self) -> float:
        """Get weight for this auditor's votes in consensus."""
        base_weights = {
            ReputationLevel.NEWCOMER: 0.5,
            ReputationLevel.CONTRIBUTOR: 1.0,
            ReputationLevel.TRUSTED: 1.5,
            ReputationLevel.EXPERT: 2.0,
            ReputationLevel.MASTER: 3.0,
        }

        base = base_weights[self.level]

        # Bonus for accuracy
        if self.validations_performed > 10:
            accuracy = self.validations_correct / self.validations_performed
            base *= (0.5 + accuracy)  # 0.5x to 1.5x multiplier

        return base

    def get_finding_accuracy(self) -> float:
        """Get finding confirmation rate."""
        if self.findings_submitted == 0:
            return 0.0
        return self.findings_confirmed / self.findings_submitted

    def get_validation_accuracy(self) -> float:
        """Get validation accuracy rate."""
        if self.validations_performed == 0:
            return 0.0
        return self.validations_correct / self.validations_performed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "auditor_id": self.auditor_id,
            "name": self.name,
            "verified": self.verified,
            "reputation_score": self.reputation_score,
            "level": self.level.value,
            "trust_weight": self.get_trust_weight(),
            "statistics": {
                "findings_submitted": self.findings_submitted,
                "findings_confirmed": self.findings_confirmed,
                "findings_rejected": self.findings_rejected,
                "finding_accuracy": round(self.get_finding_accuracy(), 2),
                "validations_performed": self.validations_performed,
                "validations_correct": self.validations_correct,
                "validation_accuracy": round(self.get_validation_accuracy(), 2),
            },
            "current_streak": self.current_streak,
            "best_streak": self.best_streak,
            "joined_at": self.joined_at.isoformat(),
        }


class ReputationSystem:
    """
    Manages auditor reputation across the network.
    """

    # Default point values for actions
    POINT_VALUES = {
        ReputationAction.FINDING_CONFIRMED: 10,
        ReputationAction.FIRST_DISCOVERY: 20,
        ReputationAction.VALIDATION_CORRECT: 2,
        ReputationAction.HIGH_SEVERITY: 5,
        ReputationAction.FINDING_REJECTED: -15,
        ReputationAction.VALIDATION_WRONG: -3,
        ReputationAction.SPAM_SUBMISSION: -20,
    }

    def __init__(self):
        self.profiles: Dict[str, AuditorProfile] = {}

    def register_auditor(
        self,
        auditor_id: str,
        name: Optional[str] = None
    ) -> AuditorProfile:
        """Register a new auditor."""
        profile = AuditorProfile(
            auditor_id=auditor_id,
            name=name,
        )
        self.profiles[auditor_id] = profile
        return profile

    def get_profile(self, auditor_id: str) -> Optional[AuditorProfile]:
        """Get auditor profile."""
        return self.profiles.get(auditor_id)

    def get_or_create_profile(self, auditor_id: str) -> AuditorProfile:
        """Get or create auditor profile."""
        if auditor_id not in self.profiles:
            return self.register_auditor(auditor_id)
        return self.profiles[auditor_id]

    def record_finding_confirmed(self, auditor_id: str, finding_id: str, is_first: bool = False, is_high: bool = False):
        """Record a confirmed finding."""
        profile = self.get_or_create_profile(auditor_id)

        # Base points
        points = self.POINT_VALUES[ReputationAction.FINDING_CONFIRMED]
        profile.add_reputation(ReputationAction.FINDING_CONFIRMED, points, finding_id)

        # First discovery bonus
        if is_first:
            first_points = self.POINT_VALUES[ReputationAction.FIRST_DISCOVERY]
            profile.add_reputation(ReputationAction.FIRST_DISCOVERY, first_points, finding_id)

        # High severity bonus
        if is_high:
            high_points = self.POINT_VALUES[ReputationAction.HIGH_SEVERITY]
            profile.add_reputation(ReputationAction.HIGH_SEVERITY, high_points, finding_id)

        # Update statistics
        profile.findings_confirmed += 1
        profile.current_streak += 1
        profile.best_streak = max(profile.best_streak, profile.current_streak)

    def record_finding_rejected(self, auditor_id: str, finding_id: str):
        """Record a rejected finding."""
        profile = self.get_or_create_profile(auditor_id)

        points = self.POINT_VALUES[ReputationAction.FINDING_REJECTED]
        profile.add_reputation(ReputationAction.FINDING_REJECTED, points, finding_id)

        profile.findings_rejected += 1
        profile.current_streak = 0  # Reset streak

    def record_finding_submitted(self, auditor_id: str):
        """Record a finding submission."""
        profile = self.get_or_create_profile(auditor_id)
        profile.findings_submitted += 1
        profile.last_active = datetime.now()

    def record_validation(self, auditor_id: str, was_correct: bool, finding_id: str):
        """Record a validation vote."""
        profile = self.get_or_create_profile(auditor_id)

        if was_correct:
            points = self.POINT_VALUES[ReputationAction.VALIDATION_CORRECT]
            profile.add_reputation(ReputationAction.VALIDATION_CORRECT, points, finding_id)
            profile.validations_correct += 1
        else:
            points = self.POINT_VALUES[ReputationAction.VALIDATION_WRONG]
            profile.add_reputation(ReputationAction.VALIDATION_WRONG, points, finding_id)

        profile.validations_performed += 1

    def get_leaderboard(self, limit: int = 10) -> List[AuditorProfile]:
        """Get top auditors by reputation."""
        sorted_profiles = sorted(
            self.profiles.values(),
            key=lambda p: p.reputation_score,
            reverse=True
        )
        return sorted_profiles[:limit]

    def get_by_level(self, level: ReputationLevel) -> List[AuditorProfile]:
        """Get all auditors at a specific level."""
        return [p for p in self.profiles.values() if p.level == level]

    def get_active_validators(self, min_reputation: int = 100) -> List[AuditorProfile]:
        """Get auditors eligible to validate."""
        cutoff = datetime.now() - timedelta(days=30)
        return [
            p for p in self.profiles.values()
            if p.reputation_score >= min_reputation
            and p.last_active and p.last_active > cutoff
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics."""
        total = len(self.profiles)
        by_level = {}
        for level in ReputationLevel:
            by_level[level.value] = len(self.get_by_level(level))

        avg_reputation = sum(p.reputation_score for p in self.profiles.values()) / total if total > 0 else 0

        return {
            "total_auditors": total,
            "by_level": by_level,
            "average_reputation": round(avg_reputation, 1),
            "active_validators": len(self.get_active_validators()),
        }
