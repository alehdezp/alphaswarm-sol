"""Tier Routing Policy for Cost-Effective Model Selection.

This module implements a tiered routing policy that escalates from
cheap validators to expensive experts based on risk, evidence, and budget.

Key features:
- Validator-first approach (cheap tier by default)
- Configurable escalation thresholds
- Evidence-based tier selection
- Budget-aware downgrade logic
- Routing metadata with rationale

Usage:
    from alphaswarm_sol.llm.routing_policy import (
        TierRoutingPolicy,
        RoutingDecision,
        EscalationReason,
    )

    policy = TierRoutingPolicy()

    # Route a task
    decision = policy.route(
        task_type="tier_b_verification",
        risk_score=0.8,
        evidence_completeness=0.4,
        budget_remaining=5.0,
    )

    print(f"Selected tier: {decision.tier}")
    print(f"Rationale: {decision.rationale}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

from alphaswarm_sol.llm.tiers import ModelTier, ModelTierConfig


logger = logging.getLogger(__name__)


class EscalationReason(str, Enum):
    """Reasons for tier escalation or downgrade."""

    # Escalation reasons
    HIGH_RISK = "high_risk"
    LOW_EVIDENCE = "low_evidence"
    COMPLEX_PATTERN = "complex_pattern"
    CRITICAL_SEVERITY = "critical_severity"
    CROSS_CONTRACT = "cross_contract"
    BUSINESS_LOGIC = "business_logic"
    VALIDATOR_FAILURE = "validator_failure"

    # Downgrade reasons
    BUDGET_LIMITED = "budget_limited"
    SIMPLE_TASK = "simple_task"
    HIGH_EVIDENCE = "high_evidence"

    # Default
    DEFAULT_TIER = "default_tier"


@dataclass
class EscalationThresholds:
    """Configurable thresholds for tier escalation.

    Attributes:
        risk_score_standard: Risk score threshold to escalate from CHEAP to STANDARD
        risk_score_premium: Risk score threshold to escalate to PREMIUM
        evidence_completeness_low: Below this, escalate to higher tier for evidence
        evidence_completeness_high: Above this, may downgrade tier
        budget_low_threshold_usd: Below this, force budget-aware downgrades
        budget_critical_threshold_usd: Below this, only CHEAP tier allowed
    """

    # Risk-based escalation (0.0 - 1.0)
    risk_score_standard: float = 0.5
    risk_score_premium: float = 0.8

    # Evidence-based escalation (0.0 - 1.0)
    evidence_completeness_low: float = 0.3
    evidence_completeness_high: float = 0.8

    # Budget-based downgrade (USD)
    budget_low_threshold_usd: float = 2.0
    budget_critical_threshold_usd: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "risk_score_standard": self.risk_score_standard,
            "risk_score_premium": self.risk_score_premium,
            "evidence_completeness_low": self.evidence_completeness_low,
            "evidence_completeness_high": self.evidence_completeness_high,
            "budget_low_threshold_usd": self.budget_low_threshold_usd,
            "budget_critical_threshold_usd": self.budget_critical_threshold_usd,
        }


@dataclass
class RoutingDecision:
    """Result of a tier routing decision.

    Attributes:
        tier: Selected model tier
        rationale: Human-readable explanation
        escalation_reasons: List of reasons that influenced the decision
        estimated_cost_usd: Estimated cost for this tier
        original_tier: Tier before any escalation/downgrade
        was_escalated: Whether tier was escalated from original
        was_downgraded: Whether tier was downgraded from original
        metadata: Additional context for auditing
        timestamp: When the decision was made
    """

    tier: ModelTier
    rationale: str
    escalation_reasons: List[EscalationReason] = field(default_factory=list)
    estimated_cost_usd: float = 0.0
    original_tier: Optional[ModelTier] = None
    was_escalated: bool = False
    was_downgraded: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tier": self.tier.value,
            "rationale": self.rationale,
            "escalation_reasons": [r.value for r in self.escalation_reasons],
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "original_tier": self.original_tier.value if self.original_tier else None,
            "was_escalated": self.was_escalated,
            "was_downgraded": self.was_downgraded,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    @property
    def tier_changed(self) -> bool:
        """Whether tier was changed from original."""
        return self.was_escalated or self.was_downgraded


# Task type to default tier mapping (validator-first approach)
TASK_DEFAULT_TIERS: Dict[str, ModelTier] = {
    # CHEAP tier - simple validation tasks
    "evidence_extraction": ModelTier.CHEAP,
    "pattern_validation": ModelTier.CHEAP,
    "code_parsing": ModelTier.CHEAP,
    "format_validation": ModelTier.CHEAP,
    "syntax_check": ModelTier.CHEAP,

    # STANDARD tier - analysis tasks
    "tier_b_verification": ModelTier.STANDARD,
    "context_analysis": ModelTier.STANDARD,
    "fp_filtering": ModelTier.STANDARD,
    "guard_analysis": ModelTier.STANDARD,

    # PREMIUM tier - complex reasoning tasks
    "exploit_synthesis": ModelTier.PREMIUM,
    "business_logic_analysis": ModelTier.PREMIUM,
    "multi_step_reasoning": ModelTier.PREMIUM,
    "attack_path_generation": ModelTier.PREMIUM,
    "cross_contract_analysis": ModelTier.PREMIUM,
}


class TierRoutingPolicy:
    """Tier routing policy for cost-effective model selection.

    This policy implements a validator-first approach:
    1. Start with the cheapest viable tier for the task
    2. Escalate based on risk, evidence gaps, and pattern complexity
    3. Downgrade when budget is constrained

    Example:
        policy = TierRoutingPolicy()

        # Simple task - stays cheap
        decision = policy.route(
            task_type="pattern_validation",
            risk_score=0.2,
            evidence_completeness=0.9,
        )
        assert decision.tier == ModelTier.CHEAP

        # High risk - escalates
        decision = policy.route(
            task_type="tier_b_verification",
            risk_score=0.9,
            evidence_completeness=0.3,
        )
        assert decision.tier == ModelTier.PREMIUM
    """

    def __init__(
        self,
        thresholds: Optional[EscalationThresholds] = None,
        tier_config: Optional[ModelTierConfig] = None,
        default_tier: ModelTier = ModelTier.CHEAP,
    ):
        """Initialize routing policy.

        Args:
            thresholds: Escalation thresholds (uses defaults if not provided)
            tier_config: Model tier configuration
            default_tier: Default tier when no task type mapping exists
        """
        self.thresholds = thresholds or EscalationThresholds()
        self.tier_config = tier_config or ModelTierConfig()
        self.default_tier = default_tier

    @property
    def validator_tier(self) -> ModelTier:
        """The validator (cheap) tier for simple checks."""
        return ModelTier.CHEAP

    @property
    def specialist_tier(self) -> ModelTier:
        """The specialist (standard) tier for analysis."""
        return ModelTier.STANDARD

    @property
    def expert_tier(self) -> ModelTier:
        """The expert (premium) tier for complex reasoning."""
        return ModelTier.PREMIUM

    def route(
        self,
        task_type: str,
        risk_score: float = 0.0,
        evidence_completeness: float = 1.0,
        budget_remaining: Optional[float] = None,
        severity: Optional[str] = None,
        pattern_type: Optional[str] = None,
        pool_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> RoutingDecision:
        """Route a task to the appropriate tier.

        Args:
            task_type: Type of task (e.g., "tier_b_verification")
            risk_score: Risk score (0.0 - 1.0)
            evidence_completeness: How complete the evidence is (0.0 - 1.0)
            budget_remaining: Remaining budget in USD (None = unlimited)
            severity: Severity level (optional, for escalation hints)
            pattern_type: Pattern being analyzed (optional, for complexity hints)
            pool_id: Pool ID for per-pool configuration
            workflow_id: Workflow ID for per-workflow configuration

        Returns:
            RoutingDecision with tier selection and rationale
        """
        # 1. Get base tier from task type
        base_tier = TASK_DEFAULT_TIERS.get(task_type.lower(), self.default_tier)
        original_tier = base_tier
        reasons: List[EscalationReason] = [EscalationReason.DEFAULT_TIER]

        # 2. Check for escalation conditions
        escalation_tier, escalation_reasons = self._check_escalation(
            base_tier=base_tier,
            risk_score=risk_score,
            evidence_completeness=evidence_completeness,
            severity=severity,
            pattern_type=pattern_type,
        )

        if escalation_tier != base_tier:
            base_tier = escalation_tier
            reasons = escalation_reasons

        # 3. Check for budget-based downgrade
        final_tier, downgrade_reasons = self._check_budget_downgrade(
            current_tier=base_tier,
            budget_remaining=budget_remaining,
        )

        was_escalated = self._tier_to_int(final_tier) > self._tier_to_int(original_tier)
        was_downgraded = self._tier_to_int(final_tier) < self._tier_to_int(base_tier)

        if was_downgraded:
            reasons = downgrade_reasons

        # 4. Estimate cost
        estimated_cost = self._estimate_tier_cost(final_tier)

        # 5. Build rationale
        rationale = self._build_rationale(
            final_tier=final_tier,
            original_tier=original_tier,
            reasons=reasons,
            task_type=task_type,
            risk_score=risk_score,
            evidence_completeness=evidence_completeness,
            budget_remaining=budget_remaining,
        )

        return RoutingDecision(
            tier=final_tier,
            rationale=rationale,
            escalation_reasons=reasons,
            estimated_cost_usd=estimated_cost,
            original_tier=original_tier,
            was_escalated=was_escalated,
            was_downgraded=was_downgraded,
            metadata={
                "task_type": task_type,
                "risk_score": risk_score,
                "evidence_completeness": evidence_completeness,
                "budget_remaining": budget_remaining,
                "severity": severity,
                "pattern_type": pattern_type,
                "pool_id": pool_id,
                "workflow_id": workflow_id,
                "thresholds": self.thresholds.to_dict(),
            },
        )

    def _check_escalation(
        self,
        base_tier: ModelTier,
        risk_score: float,
        evidence_completeness: float,
        severity: Optional[str],
        pattern_type: Optional[str],
    ) -> tuple[ModelTier, List[EscalationReason]]:
        """Check if escalation is needed.

        Returns:
            Tuple of (new_tier, reasons)
        """
        reasons: List[EscalationReason] = []
        escalated_tier = base_tier

        # Risk-based escalation
        if risk_score >= self.thresholds.risk_score_premium:
            escalated_tier = ModelTier.PREMIUM
            reasons.append(EscalationReason.HIGH_RISK)
        elif risk_score >= self.thresholds.risk_score_standard:
            if self._tier_to_int(escalated_tier) < self._tier_to_int(ModelTier.STANDARD):
                escalated_tier = ModelTier.STANDARD
                reasons.append(EscalationReason.HIGH_RISK)

        # Evidence-based escalation (low evidence needs better analysis)
        if evidence_completeness < self.thresholds.evidence_completeness_low:
            if self._tier_to_int(escalated_tier) < self._tier_to_int(ModelTier.STANDARD):
                escalated_tier = ModelTier.STANDARD
                reasons.append(EscalationReason.LOW_EVIDENCE)

        # Severity-based escalation
        if severity and severity.lower() in ["critical", "high"]:
            if self._tier_to_int(escalated_tier) < self._tier_to_int(ModelTier.STANDARD):
                escalated_tier = ModelTier.STANDARD
                reasons.append(EscalationReason.CRITICAL_SEVERITY)

        # Pattern complexity escalation
        if pattern_type:
            complex_patterns = [
                "business-logic", "cross-contract", "flash-loan",
                "governance", "economic", "oracle-manipulation",
            ]
            if any(p in pattern_type.lower() for p in complex_patterns):
                escalated_tier = ModelTier.PREMIUM
                reasons.append(EscalationReason.COMPLEX_PATTERN)

        return escalated_tier, reasons if reasons else [EscalationReason.DEFAULT_TIER]

    def _check_budget_downgrade(
        self,
        current_tier: ModelTier,
        budget_remaining: Optional[float],
    ) -> tuple[ModelTier, List[EscalationReason]]:
        """Check if budget-based downgrade is needed.

        Returns:
            Tuple of (new_tier, reasons)
        """
        if budget_remaining is None:
            return current_tier, []

        reasons: List[EscalationReason] = []

        # Critical budget - force CHEAP
        if budget_remaining <= self.thresholds.budget_critical_threshold_usd:
            if current_tier != ModelTier.CHEAP:
                logger.warning(
                    f"Budget critical (${budget_remaining:.2f}), "
                    f"forcing CHEAP tier from {current_tier.value}"
                )
                reasons.append(EscalationReason.BUDGET_LIMITED)
                return ModelTier.CHEAP, reasons

        # Low budget - cap at STANDARD
        if budget_remaining <= self.thresholds.budget_low_threshold_usd:
            if current_tier == ModelTier.PREMIUM:
                logger.info(
                    f"Budget low (${budget_remaining:.2f}), "
                    f"downgrading from PREMIUM to STANDARD"
                )
                reasons.append(EscalationReason.BUDGET_LIMITED)
                return ModelTier.STANDARD, reasons

        return current_tier, reasons

    def _tier_to_int(self, tier: ModelTier) -> int:
        """Convert tier to integer for comparison."""
        return {
            ModelTier.CHEAP: 0,
            ModelTier.STANDARD: 1,
            ModelTier.PREMIUM: 2,
        }[tier]

    def _estimate_tier_cost(self, tier: ModelTier) -> float:
        """Estimate cost for a tier (per request).

        Uses tier cost weights from config.
        """
        base_cost = 0.01  # $0.01 base cost per request
        weight = self.tier_config.tier_cost_weights.get(tier, 1.0)
        return base_cost * weight

    def _build_rationale(
        self,
        final_tier: ModelTier,
        original_tier: ModelTier,
        reasons: List[EscalationReason],
        task_type: str,
        risk_score: float,
        evidence_completeness: float,
        budget_remaining: Optional[float],
    ) -> str:
        """Build human-readable rationale for the routing decision."""
        parts = [f"Selected {final_tier.value} tier for {task_type}"]

        if final_tier != original_tier:
            direction = "escalated" if self._tier_to_int(final_tier) > self._tier_to_int(original_tier) else "downgraded"
            parts.append(f"({direction} from {original_tier.value})")

        reason_strs = []
        for reason in reasons:
            if reason == EscalationReason.HIGH_RISK:
                reason_strs.append(f"high risk score ({risk_score:.2f})")
            elif reason == EscalationReason.LOW_EVIDENCE:
                reason_strs.append(f"low evidence ({evidence_completeness:.2f})")
            elif reason == EscalationReason.BUDGET_LIMITED:
                reason_strs.append(f"budget constrained (${budget_remaining:.2f} remaining)")
            elif reason == EscalationReason.COMPLEX_PATTERN:
                reason_strs.append("complex pattern type")
            elif reason == EscalationReason.CRITICAL_SEVERITY:
                reason_strs.append("critical/high severity")
            elif reason == EscalationReason.DEFAULT_TIER:
                reason_strs.append("default for task type")

        if reason_strs:
            parts.append("due to " + ", ".join(reason_strs))

        return " ".join(parts)

    def get_escalation_path(self, from_tier: ModelTier) -> List[ModelTier]:
        """Get the escalation path from a given tier.

        Args:
            from_tier: Starting tier

        Returns:
            List of tiers in escalation order (not including from_tier)
        """
        all_tiers = [ModelTier.CHEAP, ModelTier.STANDARD, ModelTier.PREMIUM]
        start_idx = all_tiers.index(from_tier)
        return all_tiers[start_idx + 1:]


def create_routing_policy(
    risk_threshold: float = 0.5,
    evidence_threshold: float = 0.3,
    budget_threshold: float = 2.0,
) -> TierRoutingPolicy:
    """Create a routing policy with custom thresholds.

    Args:
        risk_threshold: Risk score to escalate from CHEAP to STANDARD
        evidence_threshold: Evidence completeness below which to escalate
        budget_threshold: Budget below which to consider downgrades

    Returns:
        Configured TierRoutingPolicy
    """
    thresholds = EscalationThresholds(
        risk_score_standard=risk_threshold,
        evidence_completeness_low=evidence_threshold,
        budget_low_threshold_usd=budget_threshold,
    )
    return TierRoutingPolicy(thresholds=thresholds)


def route_task(
    task_type: str,
    risk_score: float = 0.0,
    evidence_completeness: float = 1.0,
    budget_remaining: Optional[float] = None,
    policy: Optional[TierRoutingPolicy] = None,
) -> RoutingDecision:
    """Convenience function to route a single task.

    Args:
        task_type: Type of task
        risk_score: Risk score (0.0 - 1.0)
        evidence_completeness: Evidence completeness (0.0 - 1.0)
        budget_remaining: Remaining budget in USD
        policy: Optional policy (uses default if not provided)

    Returns:
        RoutingDecision
    """
    if policy is None:
        policy = TierRoutingPolicy()
    return policy.route(
        task_type=task_type,
        risk_score=risk_score,
        evidence_completeness=evidence_completeness,
        budget_remaining=budget_remaining,
    )
