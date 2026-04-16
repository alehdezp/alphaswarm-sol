"""Game-theoretic payoff field definitions for attack modeling.

Per 05.11-CONTEXT.md: Payoff fields enable economic reasoning about attack
viability, expected profits, and defender responses. The payoff matrix supports
3-player game analysis (Attacker, Protocol, MEV Searchers).

Types defined here:
- AttackPayoff: Expected profit, costs, and success probability for attackers
- DefensePayoff: Detection probability, mitigation cost, and timelock delays
- PayoffOutcome: Possible outcome with probability and payoff amounts
- PayoffMatrix: Game-theoretic model with Nash equilibrium stub

Usage:
    from alphaswarm_sol.economics.payoff import (
        AttackPayoff,
        DefensePayoff,
        PayoffMatrix,
    )

    attack = AttackPayoff(
        expected_profit_usd=100000,
        gas_cost_usd=500,
        mev_risk=0.3,
        success_probability=0.7
    )

    defense = DefensePayoff(
        detection_probability=0.8,
        mitigation_cost_usd=50000,
        timelock_delay_seconds=86400
    )

    matrix = PayoffMatrix(
        scenario="oracle_manipulation",
        attacker_payoff=attack,
        defender_payoff=defense
    )

    print(f"Attack EV: ${matrix.attacker_expected_value:,.2f}")
    print(f"Is profitable: {matrix.is_attack_profitable}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PayoffPlayer(Enum):
    """Players in the game-theoretic model.

    Per 05.11-CONTEXT.md: 3-player game model for attack analysis.

    Players:
    - ATTACKER: Entity attempting to exploit vulnerability
    - PROTOCOL: Protocol/defender trying to prevent exploitation
    - MEV_SEARCHER: MEV actors who may front-run or sandwich attacks
    """

    ATTACKER = "attacker"
    PROTOCOL = "protocol"
    MEV_SEARCHER = "mev_searcher"


@dataclass
class AttackPayoff:
    """Attack payoff model for game-theoretic analysis.

    Per 05.11-CONTEXT.md: Captures expected profit, costs, and success
    probability for attacker reasoning.

    Attributes:
        expected_profit_usd: Expected profit if attack succeeds (USD)
        gas_cost_usd: Gas cost to execute attack (USD)
        mev_risk: Probability of MEV searcher front-running (0.0-1.0)
        success_probability: Probability of successful exploitation (0.0-1.0)
        capital_required_usd: Capital required to execute (flash loans, etc.)
        execution_complexity: Complexity estimate (low/medium/high)
        detection_risk: Risk of being detected/flagged (0.0-1.0)
        evidence_refs: References to evidence supporting these estimates

    Usage:
        attack = AttackPayoff(
            expected_profit_usd=100000,
            gas_cost_usd=500,
            mev_risk=0.3,
            success_probability=0.7
        )

        print(f"Net expected value: ${attack.expected_value:,.2f}")
    """

    expected_profit_usd: float
    gas_cost_usd: float = 0.0
    mev_risk: float = 0.0
    success_probability: float = 0.5
    capital_required_usd: float = 0.0
    execution_complexity: str = "medium"  # low, medium, high
    detection_risk: float = 0.0
    evidence_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate probability ranges."""
        if not 0.0 <= self.mev_risk <= 1.0:
            raise ValueError(f"mev_risk must be 0.0-1.0, got {self.mev_risk}")
        if not 0.0 <= self.success_probability <= 1.0:
            raise ValueError(f"success_probability must be 0.0-1.0, got {self.success_probability}")
        if not 0.0 <= self.detection_risk <= 1.0:
            raise ValueError(f"detection_risk must be 0.0-1.0, got {self.detection_risk}")

    @property
    def expected_value(self) -> float:
        """Calculate expected value of the attack.

        EV = P(success) * profit - costs - P(MEV) * profit * MEV_share
        """
        mev_loss = self.expected_profit_usd * self.mev_risk * 0.5  # Assume 50% MEV extraction
        return (
            self.success_probability * self.expected_profit_usd
            - self.gas_cost_usd
            - mev_loss
        )

    @property
    def is_profitable(self) -> bool:
        """Check if attack has positive expected value."""
        return self.expected_value > 0

    @property
    def risk_adjusted_value(self) -> float:
        """Calculate risk-adjusted expected value (accounting for detection)."""
        detection_penalty = self.expected_profit_usd * self.detection_risk
        return self.expected_value - detection_penalty

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "expected_profit_usd": self.expected_profit_usd,
            "gas_cost_usd": self.gas_cost_usd,
            "mev_risk": self.mev_risk,
            "success_probability": self.success_probability,
            "capital_required_usd": self.capital_required_usd,
            "execution_complexity": self.execution_complexity,
            "detection_risk": self.detection_risk,
            "evidence_refs": self.evidence_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AttackPayoff":
        """Create AttackPayoff from dictionary."""
        return cls(
            expected_profit_usd=float(data.get("expected_profit_usd", 0)),
            gas_cost_usd=float(data.get("gas_cost_usd", 0)),
            mev_risk=float(data.get("mev_risk", 0)),
            success_probability=float(data.get("success_probability", 0.5)),
            capital_required_usd=float(data.get("capital_required_usd", 0)),
            execution_complexity=str(data.get("execution_complexity", "medium")),
            detection_risk=float(data.get("detection_risk", 0)),
            evidence_refs=list(data.get("evidence_refs", [])),
        )


@dataclass
class DefensePayoff:
    """Defense payoff model for game-theoretic analysis.

    Per 05.11-CONTEXT.md: Captures detection probability, mitigation costs,
    and response capabilities for defender reasoning.

    Attributes:
        detection_probability: Probability of detecting attack (0.0-1.0)
        mitigation_cost_usd: Cost to implement mitigation (USD)
        timelock_delay_seconds: Timelock delay for governance actions
        response_time_seconds: Time to respond to detected attack
        insurance_coverage_usd: Insurance coverage amount (USD)
        emergency_pause_capable: Whether protocol can emergency pause
        evidence_refs: References to evidence supporting these estimates

    Usage:
        defense = DefensePayoff(
            detection_probability=0.8,
            mitigation_cost_usd=50000,
            timelock_delay_seconds=86400
        )

        print(f"Expected loss: ${defense.expected_loss(100000):,.2f}")
    """

    detection_probability: float = 0.5
    mitigation_cost_usd: float = 0.0
    timelock_delay_seconds: int = 0
    response_time_seconds: int = 0
    insurance_coverage_usd: float = 0.0
    emergency_pause_capable: bool = False
    evidence_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate probability range."""
        if not 0.0 <= self.detection_probability <= 1.0:
            raise ValueError(f"detection_probability must be 0.0-1.0, got {self.detection_probability}")

    def expected_loss(self, attack_profit: float) -> float:
        """Calculate expected loss from an attack.

        Args:
            attack_profit: Attacker's expected profit

        Returns:
            Expected loss to protocol
        """
        # Loss = (1 - P(detect)) * attack_profit + mitigation cost
        undetected_loss = (1 - self.detection_probability) * attack_profit
        covered = min(undetected_loss, self.insurance_coverage_usd)
        return undetected_loss - covered + self.mitigation_cost_usd

    @property
    def can_respond_before_execution(self) -> bool:
        """Check if response can happen before attack executes."""
        return self.timelock_delay_seconds > self.response_time_seconds

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "detection_probability": self.detection_probability,
            "mitigation_cost_usd": self.mitigation_cost_usd,
            "timelock_delay_seconds": self.timelock_delay_seconds,
            "response_time_seconds": self.response_time_seconds,
            "insurance_coverage_usd": self.insurance_coverage_usd,
            "emergency_pause_capable": self.emergency_pause_capable,
            "evidence_refs": self.evidence_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DefensePayoff":
        """Create DefensePayoff from dictionary."""
        return cls(
            detection_probability=float(data.get("detection_probability", 0.5)),
            mitigation_cost_usd=float(data.get("mitigation_cost_usd", 0)),
            timelock_delay_seconds=int(data.get("timelock_delay_seconds", 0)),
            response_time_seconds=int(data.get("response_time_seconds", 0)),
            insurance_coverage_usd=float(data.get("insurance_coverage_usd", 0)),
            emergency_pause_capable=bool(data.get("emergency_pause_capable", False)),
            evidence_refs=list(data.get("evidence_refs", [])),
        )


@dataclass
class PayoffOutcome:
    """A possible outcome in the payoff matrix.

    Per 05.11-CONTEXT.md: Represents one cell in the game-theoretic payoff matrix
    with probability and payoffs for each player.

    Attributes:
        name: Outcome name (e.g., "attack_succeeds", "detected_and_blocked")
        probability: Probability of this outcome (0.0-1.0)
        attacker_payoff_usd: Attacker's payoff in this outcome
        protocol_payoff_usd: Protocol's payoff (usually negative = loss)
        mev_payoff_usd: MEV searcher's payoff
        description: Human-readable description
    """

    name: str
    probability: float
    attacker_payoff_usd: float
    protocol_payoff_usd: float
    mev_payoff_usd: float = 0.0
    description: str = ""

    def __post_init__(self) -> None:
        """Validate probability range."""
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError(f"probability must be 0.0-1.0, got {self.probability}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "probability": self.probability,
            "attacker_payoff_usd": self.attacker_payoff_usd,
            "protocol_payoff_usd": self.protocol_payoff_usd,
            "mev_payoff_usd": self.mev_payoff_usd,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PayoffOutcome":
        """Create PayoffOutcome from dictionary."""
        return cls(
            name=str(data.get("name", "")),
            probability=float(data.get("probability", 0)),
            attacker_payoff_usd=float(data.get("attacker_payoff_usd", 0)),
            protocol_payoff_usd=float(data.get("protocol_payoff_usd", 0)),
            mev_payoff_usd=float(data.get("mev_payoff_usd", 0)),
            description=str(data.get("description", "")),
        )


@dataclass
class PayoffMatrix:
    """Game-theoretic payoff matrix for attack analysis.

    Per 05.11-CONTEXT.md: 3-player game model (Attacker, Protocol, MEV Searchers)
    with a heuristic equilibrium proxy when strategy space is unspecified.

    Attributes:
        scenario: Scenario name (e.g., "oracle_manipulation", "reentrancy")
        attacker_payoff: Attacker's payoff model
        defender_payoff: Defender's payoff model
        outcomes: List of possible outcomes with probabilities
        tvl_at_risk_usd: Total value locked at risk (USD)
        evidence_refs: References to supporting evidence

    Usage:
        matrix = PayoffMatrix(
            scenario="oracle_manipulation",
            attacker_payoff=attack,
            defender_payoff=defense
        )

        print(f"Attack EV: ${matrix.attacker_expected_value:,.2f}")
        print(f"Is profitable: {matrix.is_attack_profitable}")

        # Nash equilibrium (heuristic proxy)
        eq = matrix.compute_nash_equilibrium()
    """

    scenario: str
    attacker_payoff: AttackPayoff
    defender_payoff: DefensePayoff
    outcomes: List[PayoffOutcome] = field(default_factory=list)
    tvl_at_risk_usd: float = 0.0
    evidence_refs: List[str] = field(default_factory=list)

    @property
    def attacker_expected_value(self) -> float:
        """Calculate attacker's expected value from this scenario."""
        return self.attacker_payoff.expected_value

    @property
    def defender_expected_loss(self) -> float:
        """Calculate defender's expected loss from this scenario."""
        return self.defender_payoff.expected_loss(self.attacker_payoff.expected_profit_usd)

    @property
    def is_attack_profitable(self) -> bool:
        """Check if attack is profitable for attacker."""
        return self.attacker_payoff.is_profitable

    @property
    def is_high_risk(self) -> bool:
        """Check if this is a high-risk scenario.

        High risk = profitable attack + low detection + high TVL.
        """
        return (
            self.is_attack_profitable
            and self.defender_payoff.detection_probability < 0.5
            and self.tvl_at_risk_usd > 100000
        )

    def compute_nash_equilibrium(self) -> Dict[str, Any]:
        """Compute Nash equilibrium for this game.

        Heuristic equilibrium proxy when a full strategy space is not provided.

        The Nash equilibrium identifies the stable strategy profile where
        no player can improve their payoff by unilaterally changing strategy.

        Returns:
            Dict with equilibrium strategies for each player
        """
        # Heuristic equilibrium proxy. Full computation requires a defined
        # strategy space and best-response iteration (see economics/gate/nash_solver.py).
        # and iterative best response calculation

        # Simple heuristic for now: attack if profitable, defend if detection high
        attack_strategy = "exploit" if self.is_attack_profitable else "abstain"
        defend_strategy = "active_monitoring" if self.defender_payoff.detection_probability > 0.5 else "passive"
        mev_strategy = "front_run" if self.attacker_payoff.mev_risk > 0.3 else "abstain"

        return {
            "status": "heuristic",
            "note": "Use economics/gate/nash_solver.py for full equilibrium solving",
            "heuristic_strategies": {
                PayoffPlayer.ATTACKER.value: attack_strategy,
                PayoffPlayer.PROTOCOL.value: defend_strategy,
                PayoffPlayer.MEV_SEARCHER.value: mev_strategy,
            },
            "expected_values": {
                PayoffPlayer.ATTACKER.value: self.attacker_expected_value,
                PayoffPlayer.PROTOCOL.value: -self.defender_expected_loss,
            },
            "is_attack_profitable": self.is_attack_profitable,
        }

    def add_outcome(
        self,
        name: str,
        probability: float,
        attacker_payoff_usd: float,
        protocol_payoff_usd: float,
        mev_payoff_usd: float = 0.0,
        description: str = "",
    ) -> None:
        """Add a possible outcome to the matrix.

        Args:
            name: Outcome name
            probability: Probability of this outcome
            attacker_payoff_usd: Attacker's payoff
            protocol_payoff_usd: Protocol's payoff (usually negative)
            mev_payoff_usd: MEV searcher's payoff
            description: Human-readable description
        """
        self.outcomes.append(
            PayoffOutcome(
                name=name,
                probability=probability,
                attacker_payoff_usd=attacker_payoff_usd,
                protocol_payoff_usd=protocol_payoff_usd,
                mev_payoff_usd=mev_payoff_usd,
                description=description,
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "scenario": self.scenario,
            "attacker_payoff": self.attacker_payoff.to_dict(),
            "defender_payoff": self.defender_payoff.to_dict(),
            "outcomes": [o.to_dict() for o in self.outcomes],
            "tvl_at_risk_usd": self.tvl_at_risk_usd,
            "evidence_refs": self.evidence_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PayoffMatrix":
        """Create PayoffMatrix from dictionary."""
        return cls(
            scenario=str(data.get("scenario", "")),
            attacker_payoff=AttackPayoff.from_dict(data.get("attacker_payoff", {})),
            defender_payoff=DefensePayoff.from_dict(data.get("defender_payoff", {})),
            outcomes=[PayoffOutcome.from_dict(o) for o in data.get("outcomes", [])],
            tvl_at_risk_usd=float(data.get("tvl_at_risk_usd", 0)),
            evidence_refs=list(data.get("evidence_refs", [])),
        )


# Export all types
__all__ = [
    "PayoffPlayer",
    "AttackPayoff",
    "DefensePayoff",
    "PayoffOutcome",
    "PayoffMatrix",
]
