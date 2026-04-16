"""Economic risk scoring with game-theoretic, causal, and systemic components.

Per 05.11-CONTEXT.md: Economic risk is a secondary priority signal (0-10) used to
triage findings and decide verification depth. It does NOT affect correctness or
confidence - only prioritization.

Components:
1. Base risk (VAR, PRIV, OFFCHAIN, GOV, INCENTIVE)
2. Game-theoretic adjustment (attack expected value)
3. Causal amplification factor (from exploitation chains)
4. Systemic risk factor (from cross-protocol dependencies)

Usage:
    from alphaswarm_sol.economics.risk import (
        EconomicRiskScorer,
        RiskBreakdown,
        compute_economic_risk,
    )

    # Build scorer with payoff and causal analysis
    scorer = EconomicRiskScorer(
        payoff_matrix=payoff_matrix,
        causal_analyzer=causal_analyzer,
        systemic_scorer=systemic_scorer,
    )

    # Compute risk for a finding
    breakdown = scorer.compute_risk(
        value_at_risk_usd=1_000_000,
        privilege_concentration=0.7,
        offchain_reliance=0.5,
        governance_mutability=0.8,
        incentive_misalignment=0.6,
        causal_chain=chain,
    )

    print(f"Economic risk: {breakdown.total_score:.1f}/10")
    print(f"Components: {breakdown.to_dict()}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .payoff import PayoffMatrix
    from .causal_analysis import CausalAnalyzer, LossAmplificationFactor
    from .systemic_risk import SystemicRiskScorer, SystemicRiskScore
    from alphaswarm_sol.context.linker import CausalChainLink


class RiskPriority(Enum):
    """Risk priority levels for verification depth.

    Per 05.11-CONTEXT.md: Risk affects verification priority, not correctness.
    """

    CRITICAL = "critical"  # 8-10: Full multi-agent verification
    HIGH = "high"  # 6-8: Enhanced verification with debate
    MEDIUM = "medium"  # 4-6: Standard verification
    LOW = "low"  # 2-4: Lightweight verification
    MINIMAL = "minimal"  # 0-2: Basic pattern check only

    @classmethod
    def from_score(cls, score: float) -> "RiskPriority":
        """Map risk score to priority level.

        Args:
            score: Risk score 0-10

        Returns:
            RiskPriority enum value
        """
        if score >= 8.0:
            return cls.CRITICAL
        elif score >= 6.0:
            return cls.HIGH
        elif score >= 4.0:
            return cls.MEDIUM
        elif score >= 2.0:
            return cls.LOW
        else:
            return cls.MINIMAL


@dataclass
class RiskBreakdown:
    """Detailed breakdown of economic risk components.

    Per 05.11-CONTEXT.md: Risk breakdown is transparent and auditable.
    All components are visible in findings and beads.

    Attributes:
        total_score: Final economic risk score (0-10)
        base_score: Base risk before multipliers (0-10)
        value_at_risk_score: VAR component (0-4)
        privilege_concentration_score: PRIV component (0-2)
        offchain_reliance_score: OFFCHAIN component (0-2)
        governance_mutability_score: GOV component (0-1)
        incentive_misalignment_score: INCENTIVE component (0-1)
        attack_ev_score: Game-theoretic EV adjustment (multiplier)
        loss_amplification_factor: Causal amplification (multiplier, capped at 3x)
        systemic_risk_factor: Cross-protocol systemic factor (multiplier)
        priority: Derived priority level for verification depth
        evidence_refs: Evidence supporting risk assessment
        notes: Additional context notes
    """

    total_score: float
    base_score: float
    value_at_risk_score: float
    privilege_concentration_score: float
    offchain_reliance_score: float
    governance_mutability_score: float
    incentive_misalignment_score: float
    attack_ev_score: float = 1.0  # Multiplier from game-theoretic analysis
    loss_amplification_factor: float = 1.0  # Causal amplification multiplier
    systemic_risk_factor: float = 1.0  # Systemic risk multiplier
    priority: RiskPriority = RiskPriority.MEDIUM
    evidence_refs: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate score ranges."""
        if not 0.0 <= self.total_score <= 10.0:
            # Cap at 10 if exceeded due to multipliers
            self.total_score = min(10.0, max(0.0, self.total_score))
        if not 0.0 <= self.base_score <= 10.0:
            self.base_score = min(10.0, max(0.0, self.base_score))
        # Derive priority from total score
        self.priority = RiskPriority.from_score(self.total_score)

    @property
    def is_high_risk(self) -> bool:
        """Whether this is a high-risk finding (>= 6)."""
        return self.total_score >= 6.0

    @property
    def is_economically_rational(self) -> bool:
        """Whether the attack is economically rational (EV > 0)."""
        return self.attack_ev_score > 1.0

    @property
    def has_causal_amplification(self) -> bool:
        """Whether there is causal loss amplification."""
        return self.loss_amplification_factor > 1.0

    @property
    def has_systemic_risk(self) -> bool:
        """Whether there is cross-protocol systemic risk."""
        return self.systemic_risk_factor > 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_score": round(self.total_score, 2),
            "base_score": round(self.base_score, 2),
            "components": {
                "value_at_risk": round(self.value_at_risk_score, 2),
                "privilege_concentration": round(self.privilege_concentration_score, 2),
                "offchain_reliance": round(self.offchain_reliance_score, 2),
                "governance_mutability": round(self.governance_mutability_score, 2),
                "incentive_misalignment": round(self.incentive_misalignment_score, 2),
            },
            "multipliers": {
                "attack_ev_score": round(self.attack_ev_score, 2),
                "loss_amplification_factor": round(self.loss_amplification_factor, 2),
                "systemic_risk_factor": round(self.systemic_risk_factor, 2),
            },
            "priority": self.priority.value,
            "is_economically_rational": self.is_economically_rational,
            "has_causal_amplification": self.has_causal_amplification,
            "has_systemic_risk": self.has_systemic_risk,
            "evidence_refs": self.evidence_refs,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskBreakdown":
        """Create RiskBreakdown from dictionary."""
        components = data.get("components", {})
        multipliers = data.get("multipliers", {})

        return cls(
            total_score=float(data.get("total_score", 0)),
            base_score=float(data.get("base_score", 0)),
            value_at_risk_score=float(components.get("value_at_risk", 0)),
            privilege_concentration_score=float(components.get("privilege_concentration", 0)),
            offchain_reliance_score=float(components.get("offchain_reliance", 0)),
            governance_mutability_score=float(components.get("governance_mutability", 0)),
            incentive_misalignment_score=float(components.get("incentive_misalignment", 0)),
            attack_ev_score=float(multipliers.get("attack_ev_score", 1.0)),
            loss_amplification_factor=float(multipliers.get("loss_amplification_factor", 1.0)),
            systemic_risk_factor=float(multipliers.get("systemic_risk_factor", 1.0)),
            evidence_refs=list(data.get("evidence_refs", [])),
            notes=list(data.get("notes", [])),
        )


class EconomicRiskScorer:
    """Compute economic risk scores with three major components.

    Per 05.11-CONTEXT.md: Risk is for prioritization ONLY, never correctness.

    Components:
    1. Base risk: VAR, PRIV, OFFCHAIN, GOV, INCENTIVE (0-10)
    2. Game-theoretic adjustment: Attack EV multiplier (1.0-2.0x)
    3. Causal amplification: Loss amplification from chains (1.0-3.0x cap)
    4. Systemic risk: Cross-protocol cascade factor (1.0-1.5x)

    Usage:
        scorer = EconomicRiskScorer()

        breakdown = scorer.compute_risk(
            value_at_risk_usd=1_000_000,
            privilege_concentration=0.7,
        )
    """

    # TVL thresholds for VAR scaling (in USD)
    VAR_THRESHOLDS = [
        (100_000_000, 4.0),  # >= $100M -> max VAR
        (10_000_000, 3.0),  # >= $10M
        (1_000_000, 2.0),  # >= $1M
        (100_000, 1.0),  # >= $100K
        (0, 0.5),  # < $100K -> min VAR
    ]

    # Attack EV thresholds for game-theoretic multiplier (in ETH equivalent)
    EV_THRESHOLDS = [
        (100.0, 2.0),  # >= 100 ETH -> max multiplier
        (10.0, 1.5),  # >= 10 ETH -> medium multiplier
        (0.0, 1.0),  # EV > 0 -> slight boost
    ]

    def __init__(
        self,
        payoff_matrix: Optional["PayoffMatrix"] = None,
        causal_analyzer: Optional["CausalAnalyzer"] = None,
        systemic_scorer: Optional["SystemicRiskScorer"] = None,
    ) -> None:
        """Initialize the economic risk scorer.

        Args:
            payoff_matrix: Optional PayoffMatrix for game-theoretic analysis
            causal_analyzer: Optional CausalAnalyzer for loss amplification
            systemic_scorer: Optional SystemicRiskScorer for systemic risk
        """
        self._payoff_matrix = payoff_matrix
        self._causal_analyzer = causal_analyzer
        self._systemic_scorer = systemic_scorer

    def compute_risk(
        self,
        value_at_risk_usd: float = 0.0,
        privilege_concentration: float = 0.0,
        offchain_reliance: float = 0.0,
        governance_mutability: float = 0.0,
        incentive_misalignment: float = 0.0,
        causal_chain: Optional["CausalChainLink"] = None,
        protocol_id: Optional[str] = None,
        evidence_refs: Optional[List[str]] = None,
    ) -> RiskBreakdown:
        """Compute economic risk score with full breakdown.

        Per 05.11-CONTEXT.md: Risk affects verification priority but never
        confidence or correctness.

        Args:
            value_at_risk_usd: Total value at risk in USD
            privilege_concentration: Privilege concentration (0-1)
            offchain_reliance: Off-chain reliance factor (0-1)
            governance_mutability: Governance mutability factor (0-1)
            incentive_misalignment: Incentive misalignment factor (0-1)
            causal_chain: Optional CausalChainLink for amplification
            protocol_id: Optional protocol ID for systemic risk
            evidence_refs: Evidence references for risk assessment

        Returns:
            RiskBreakdown with full component analysis
        """
        notes: List[str] = []
        refs = evidence_refs or []

        # 1. Compute base risk components
        var_score = self._compute_var_score(value_at_risk_usd)
        priv_score = min(2.0, privilege_concentration * 2.0)
        offchain_score = min(2.0, offchain_reliance * 2.0)
        gov_score = min(1.0, governance_mutability)
        incentive_score = min(1.0, incentive_misalignment)

        base_score = var_score + priv_score + offchain_score + gov_score + incentive_score
        base_score = min(10.0, base_score)  # Cap at 10

        # 2. Compute game-theoretic adjustment
        attack_ev_score = self._compute_attack_ev_score()
        if attack_ev_score > 1.0:
            notes.append(f"Attack economically rational (EV multiplier: {attack_ev_score:.2f}x)")

        # 3. Compute causal amplification factor
        loss_amplification = self._compute_loss_amplification(causal_chain)
        if loss_amplification > 1.0:
            notes.append(f"Causal loss amplification: {loss_amplification:.2f}x")

        # 4. Compute systemic risk factor
        systemic_factor = self._compute_systemic_factor(protocol_id)
        if systemic_factor > 1.0:
            notes.append(f"Cross-protocol systemic risk: {systemic_factor:.2f}x")

        # 5. Calculate total score with multipliers
        # Multipliers are applied additively to avoid score explosion
        # Total = base * (1 + (attack_ev - 1) * 0.3 + (loss_amp - 1) * 0.4 + (systemic - 1) * 0.3)
        adjustment = (
            (attack_ev_score - 1.0) * 0.3
            + (loss_amplification - 1.0) * 0.4
            + (systemic_factor - 1.0) * 0.3
        )
        total_score = base_score * (1.0 + adjustment)
        total_score = min(10.0, total_score)  # Cap at 10

        return RiskBreakdown(
            total_score=total_score,
            base_score=base_score,
            value_at_risk_score=var_score,
            privilege_concentration_score=priv_score,
            offchain_reliance_score=offchain_score,
            governance_mutability_score=gov_score,
            incentive_misalignment_score=incentive_score,
            attack_ev_score=attack_ev_score,
            loss_amplification_factor=loss_amplification,
            systemic_risk_factor=systemic_factor,
            evidence_refs=refs,
            notes=notes,
        )

    def _compute_var_score(self, value_at_risk_usd: float) -> float:
        """Compute value-at-risk component score (0-4).

        Args:
            value_at_risk_usd: TVL or asset exposure in USD

        Returns:
            VAR score 0-4
        """
        for threshold, score in self.VAR_THRESHOLDS:
            if value_at_risk_usd >= threshold:
                return score
        return 0.5  # Minimum if no threshold matched

    def _compute_attack_ev_score(self) -> float:
        """Compute game-theoretic EV adjustment multiplier (1.0-2.0).

        Uses PayoffMatrix if available to determine if attack is economically
        rational and how profitable it would be.

        Returns:
            Attack EV multiplier (1.0 = no adjustment, 2.0 = max)
        """
        if not self._payoff_matrix:
            return 1.0

        if not self._payoff_matrix.is_attack_profitable:
            return 1.0  # No adjustment if not profitable

        # Use attacker expected value to determine multiplier
        # Convert to ETH-equivalent for threshold comparison
        ev_usd = self._payoff_matrix.attacker_expected_value
        ev_eth = ev_usd / 3000  # Approximate ETH price

        for threshold, multiplier in self.EV_THRESHOLDS:
            if ev_eth >= threshold:
                return multiplier

        return 1.0

    def _compute_loss_amplification(
        self,
        causal_chain: Optional["CausalChainLink"] = None,
    ) -> float:
        """Compute causal loss amplification factor (1.0-3.0).

        Uses CausalAnalyzer if available to analyze amplification from
        AMPLIFIES edges (flash loans, leverage, etc.).

        Args:
            causal_chain: Optional CausalChainLink to analyze

        Returns:
            Loss amplification factor (capped at 3.0x)
        """
        if not self._causal_analyzer or not causal_chain:
            return 1.0

        try:
            amplification = self._causal_analyzer.compute_loss_amplification(causal_chain)
            # Cap at 3x to prevent score explosion
            return min(3.0, amplification.amplification_multiplier)
        except Exception:
            return 1.0

    def _compute_systemic_factor(self, protocol_id: Optional[str] = None) -> float:
        """Compute systemic risk factor from cross-protocol dependencies.

        Uses SystemicRiskScorer if available to determine cascade risk.

        Args:
            protocol_id: Optional protocol ID for lookup

        Returns:
            Systemic risk factor (1.0-1.5x)
        """
        if not self._systemic_scorer or not protocol_id:
            return 1.0

        try:
            systemic_score = self._systemic_scorer.compute_systemic_risk(protocol_id)
            # Convert 0-10 score to 1.0-1.5 multiplier
            return 1.0 + (systemic_score.total_score / 10.0) * 0.5
        except Exception:
            return 1.0

    def set_payoff_matrix(self, matrix: "PayoffMatrix") -> None:
        """Set or update the payoff matrix for game-theoretic analysis."""
        self._payoff_matrix = matrix

    def set_causal_analyzer(self, analyzer: "CausalAnalyzer") -> None:
        """Set or update the causal analyzer for loss amplification."""
        self._causal_analyzer = analyzer

    def set_systemic_scorer(self, scorer: "SystemicRiskScorer") -> None:
        """Set or update the systemic risk scorer."""
        self._systemic_scorer = scorer


def compute_economic_risk(
    value_at_risk_usd: float = 0.0,
    privilege_concentration: float = 0.0,
    offchain_reliance: float = 0.0,
    governance_mutability: float = 0.0,
    incentive_misalignment: float = 0.0,
    payoff_matrix: Optional["PayoffMatrix"] = None,
    causal_chain: Optional["CausalChainLink"] = None,
    causal_analyzer: Optional["CausalAnalyzer"] = None,
    systemic_scorer: Optional["SystemicRiskScorer"] = None,
    protocol_id: Optional[str] = None,
    evidence_refs: Optional[List[str]] = None,
) -> RiskBreakdown:
    """Convenience function to compute economic risk.

    Args:
        value_at_risk_usd: Total value at risk in USD
        privilege_concentration: Privilege concentration (0-1)
        offchain_reliance: Off-chain reliance factor (0-1)
        governance_mutability: Governance mutability factor (0-1)
        incentive_misalignment: Incentive misalignment factor (0-1)
        payoff_matrix: Optional PayoffMatrix for game-theoretic analysis
        causal_chain: Optional CausalChainLink for amplification
        causal_analyzer: Optional CausalAnalyzer for loss computation
        systemic_scorer: Optional SystemicRiskScorer for systemic risk
        protocol_id: Optional protocol ID for systemic risk lookup
        evidence_refs: Evidence references for risk assessment

    Returns:
        RiskBreakdown with full component analysis
    """
    scorer = EconomicRiskScorer(
        payoff_matrix=payoff_matrix,
        causal_analyzer=causal_analyzer,
        systemic_scorer=systemic_scorer,
    )

    return scorer.compute_risk(
        value_at_risk_usd=value_at_risk_usd,
        privilege_concentration=privilege_concentration,
        offchain_reliance=offchain_reliance,
        governance_mutability=governance_mutability,
        incentive_misalignment=incentive_misalignment,
        causal_chain=causal_chain,
        protocol_id=protocol_id,
        evidence_refs=evidence_refs,
    )


# Export all types
__all__ = [
    "RiskPriority",
    "RiskBreakdown",
    "EconomicRiskScorer",
    "compute_economic_risk",
]
