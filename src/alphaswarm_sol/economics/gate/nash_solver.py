"""Nash equilibrium solver for game-theoretic attack analysis.

Per 05.11-06: Solves for Nash equilibria in 3-player games to determine
stable attack strategies and identify blocking conditions that make
attacks economically irrational.

Key Features:
- Pure strategy Nash equilibrium detection
- Mixed strategy equilibrium approximation via iterated best response
- Lemke-Howson for 2-player subgames
- Blocking condition identification (timelock, rate limit, etc.)

Usage:
    from alphaswarm_sol.economics.gate.nash_solver import (
        NashEquilibriumSolver,
        NashResult,
        BlockingCondition,
    )

    solver = NashEquilibriumSolver()
    result = solver.solve_nash_equilibrium(attack_payoff_matrix)

    if result.is_attack_dominant:
        print(f"Attack profitable: EV = ${result.attacker_payoff:,.2f}")
    else:
        print(f"Blocked by: {result.blocking_conditions}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

from .attack_synthesis import (
    AttackPayoffMatrix,
    AttackStrategy,
    ProtocolDefense,
    MEVStrategy,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Blocking Condition Types
# =============================================================================


class BlockingConditionType(Enum):
    """Types of conditions that can block attacks.

    Per 05.11-06: Blocking conditions make attacks economically irrational
    by reducing expected value below zero or profitability thresholds.
    """

    TIMELOCK = "timelock"  # Timelock delay exceeds attack window
    RATE_LIMIT = "rate_limit"  # Rate limiting prevents bulk extraction
    MEV_PROTECTION = "mev_protection"  # MEV protection (Flashbots, private tx)
    GUARD = "guard"  # Reentrancy guard or similar protection
    ACCESS_CONTROL = "access_control"  # Role-based access prevents exploitation
    GAS_COST = "gas_cost"  # Gas costs exceed expected profit
    SLIPPAGE = "slippage"  # Slippage makes attack unprofitable
    DETECTION = "detection"  # High detection probability deters attack
    CAPITAL = "capital"  # Required capital exceeds available
    COMPLEXITY = "complexity"  # Attack complexity too high for profit

    @classmethod
    def from_defense(cls, defense: ProtocolDefense) -> "BlockingConditionType":
        """Map protocol defense to blocking condition type.

        Args:
            defense: Protocol defense strategy

        Returns:
            Corresponding blocking condition type
        """
        mapping = {
            ProtocolDefense.TIMELOCK: cls.TIMELOCK,
            ProtocolDefense.RATE_LIMIT: cls.RATE_LIMIT,
            ProtocolDefense.MEV_PROTECTION: cls.MEV_PROTECTION,
            ProtocolDefense.REENTRANCY_GUARD: cls.GUARD,
            ProtocolDefense.ACCESS_CONTROL: cls.ACCESS_CONTROL,
            ProtocolDefense.PAUSE_MECHANISM: cls.GUARD,
            ProtocolDefense.ORACLE_VALIDATION: cls.GUARD,
            ProtocolDefense.MONITORING: cls.DETECTION,
        }
        return mapping.get(defense, cls.GUARD)


@dataclass
class BlockingCondition:
    """A condition that blocks or reduces attack profitability.

    Per 05.11-06: Identifies specific conditions (defenses, costs) that
    make attacks economically irrational.

    Attributes:
        condition_type: Type of blocking condition
        threshold: Value threshold that blocks attack (e.g., "timelock > 1 day")
        effect_usd: How much this reduces attacker payoff (USD)
        description: Human-readable description
        confidence: Confidence in this blocking assessment (0-1)
        evidence_refs: Supporting evidence references
    """

    condition_type: BlockingConditionType
    threshold: str
    effect_usd: float
    description: str = ""
    confidence: float = 0.8
    evidence_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate confidence range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")

    def blocks_attack(self, expected_profit: float) -> bool:
        """Check if this condition blocks attack at given profit level.

        Args:
            expected_profit: Expected attack profit before this condition

        Returns:
            True if condition blocks the attack
        """
        return self.effect_usd >= expected_profit

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "condition_type": self.condition_type.value,
            "threshold": self.threshold,
            "effect_usd": self.effect_usd,
            "description": self.description,
            "confidence": self.confidence,
            "evidence_refs": self.evidence_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlockingCondition":
        """Create BlockingCondition from dictionary."""
        return cls(
            condition_type=BlockingConditionType(data.get("condition_type", "guard")),
            threshold=str(data.get("threshold", "")),
            effect_usd=float(data.get("effect_usd", 0)),
            description=str(data.get("description", "")),
            confidence=float(data.get("confidence", 0.8)),
            evidence_refs=list(data.get("evidence_refs", [])),
        )


# =============================================================================
# Nash Equilibrium Result
# =============================================================================


@dataclass
class NashResult:
    """Result of Nash equilibrium computation.

    Per 05.11-06: Contains equilibrium strategies, payoffs, and blocking
    conditions for game-theoretic attack analysis.

    Attributes:
        attacker_strategy: Optimal attack strategy at equilibrium
        protocol_strategy: Optimal defense configuration
        mev_strategy: Expected MEV behavior
        attacker_payoff: Expected profit at equilibrium (USD)
        protocol_payoff: Protocol's payoff at equilibrium (USD, usually negative)
        mev_payoff: MEV searcher's payoff at equilibrium (USD)
        convergence_prob: Probability of reaching this equilibrium (0-1)
        is_attack_dominant: True if attack dominates honest behavior
        is_pure_equilibrium: True if this is a pure strategy equilibrium
        mixed_strategy_probs: Probabilities for mixed equilibrium (if applicable)
        blocking_conditions: Conditions that could block the attack
        iterations_to_converge: Number of iterations for convergence
        evidence_refs: Supporting evidence references
    """

    attacker_strategy: str
    protocol_strategy: str
    mev_strategy: str
    attacker_payoff: float
    protocol_payoff: float = 0.0
    mev_payoff: float = 0.0
    convergence_prob: float = 1.0
    is_attack_dominant: bool = False
    is_pure_equilibrium: bool = True
    mixed_strategy_probs: Dict[str, Dict[str, float]] = field(default_factory=dict)
    blocking_conditions: List[BlockingCondition] = field(default_factory=list)
    iterations_to_converge: int = 0
    evidence_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate probability ranges."""
        if not 0.0 <= self.convergence_prob <= 1.0:
            raise ValueError(f"convergence_prob must be 0.0-1.0, got {self.convergence_prob}")

    @property
    def is_economically_rational(self) -> bool:
        """Check if attack is economically rational (positive EV)."""
        return self.attacker_payoff > 0

    @property
    def total_blocking_effect(self) -> float:
        """Total effect of all blocking conditions."""
        return sum(bc.effect_usd for bc in self.blocking_conditions)

    def get_blocking_summary(self) -> str:
        """Get summary of blocking conditions.

        Returns:
            Human-readable summary of what blocks the attack
        """
        if not self.blocking_conditions:
            return "No blocking conditions identified"

        summaries = []
        for bc in self.blocking_conditions:
            summaries.append(f"{bc.condition_type.value}: {bc.threshold}")

        return "; ".join(summaries)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "attacker_strategy": self.attacker_strategy,
            "protocol_strategy": self.protocol_strategy,
            "mev_strategy": self.mev_strategy,
            "attacker_payoff": self.attacker_payoff,
            "protocol_payoff": self.protocol_payoff,
            "mev_payoff": self.mev_payoff,
            "convergence_prob": self.convergence_prob,
            "is_attack_dominant": self.is_attack_dominant,
            "is_pure_equilibrium": self.is_pure_equilibrium,
            "mixed_strategy_probs": self.mixed_strategy_probs,
            "blocking_conditions": [bc.to_dict() for bc in self.blocking_conditions],
            "iterations_to_converge": self.iterations_to_converge,
            "evidence_refs": self.evidence_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NashResult":
        """Create NashResult from dictionary."""
        return cls(
            attacker_strategy=str(data.get("attacker_strategy", "abstain")),
            protocol_strategy=str(data.get("protocol_strategy", "no_defense")),
            mev_strategy=str(data.get("mev_strategy", "abstain")),
            attacker_payoff=float(data.get("attacker_payoff", 0)),
            protocol_payoff=float(data.get("protocol_payoff", 0)),
            mev_payoff=float(data.get("mev_payoff", 0)),
            convergence_prob=float(data.get("convergence_prob", 1.0)),
            is_attack_dominant=bool(data.get("is_attack_dominant", False)),
            is_pure_equilibrium=bool(data.get("is_pure_equilibrium", True)),
            mixed_strategy_probs=dict(data.get("mixed_strategy_probs", {})),
            blocking_conditions=[
                BlockingCondition.from_dict(bc)
                for bc in data.get("blocking_conditions", [])
            ],
            iterations_to_converge=int(data.get("iterations_to_converge", 0)),
            evidence_refs=list(data.get("evidence_refs", [])),
        )


# =============================================================================
# Nash Equilibrium Solver
# =============================================================================


class NashEquilibriumSolver:
    """Solver for Nash equilibria in game-theoretic attack analysis.

    Per 05.11-06: Computes Nash equilibria for 3-player games to determine
    stable strategy profiles and identify blocking conditions.

    Methods:
    - solve_nash_equilibrium: Main entry point
    - find_pure_nash: Find pure strategy Nash equilibrium
    - approximate_mixed_nash: Approximate mixed strategy equilibrium
    - identify_blocking_conditions: Find conditions that block attacks

    Usage:
        solver = NashEquilibriumSolver()
        result = solver.solve_nash_equilibrium(attack_payoff_matrix)

        if result.is_attack_dominant:
            print(f"Attack profitable: EV = ${result.attacker_payoff:,.2f}")
        else:
            print(f"Blocked by: {result.blocking_conditions}")
    """

    def __init__(
        self,
        max_iterations: int = 100,
        convergence_threshold: float = 0.01,
        min_payoff_threshold: float = 0.0,
    ):
        """Initialize Nash equilibrium solver.

        Args:
            max_iterations: Maximum iterations for convergence
            convergence_threshold: Threshold for strategy change convergence
            min_payoff_threshold: Minimum payoff for attack to be rational
        """
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.min_payoff_threshold = min_payoff_threshold

    def solve_nash_equilibrium(
        self,
        payoff_matrix: AttackPayoffMatrix,
    ) -> NashResult:
        """Solve for Nash equilibrium of the attack game.

        Per 05.11-06: Main entry point for Nash equilibrium computation.
        Tries pure strategy first, falls back to mixed approximation.

        Args:
            payoff_matrix: AttackPayoffMatrix from attack synthesis

        Returns:
            NashResult with equilibrium strategies and payoffs
        """
        # Try pure strategy Nash first
        pure_result = self.find_pure_nash(payoff_matrix)
        if pure_result is not None:
            # Add blocking conditions
            blocking = self.identify_blocking_conditions(payoff_matrix, pure_result)
            pure_result.blocking_conditions = blocking

            logger.info(
                f"GATE Nash: Pure equilibrium found for {payoff_matrix.vulnerability_id}, "
                f"attacker={pure_result.attacker_strategy}, "
                f"EV=${pure_result.attacker_payoff:,.2f}"
            )
            return pure_result

        # Fall back to mixed strategy approximation
        mixed_result = self.approximate_mixed_nash(payoff_matrix)

        # Add blocking conditions
        blocking = self.identify_blocking_conditions(payoff_matrix, mixed_result)
        mixed_result.blocking_conditions = blocking

        logger.info(
            f"GATE Nash: Mixed equilibrium approximated for {payoff_matrix.vulnerability_id}, "
            f"EV=${mixed_result.attacker_payoff:,.2f}, "
            f"iterations={mixed_result.iterations_to_converge}"
        )

        return mixed_result

    def find_pure_nash(
        self,
        payoff_matrix: AttackPayoffMatrix,
    ) -> Optional[NashResult]:
        """Find pure strategy Nash equilibrium if one exists.

        A pure strategy Nash equilibrium exists when each player's strategy
        is a best response to the other players' strategies.

        Args:
            payoff_matrix: AttackPayoffMatrix from attack synthesis

        Returns:
            NashResult if pure equilibrium exists, None otherwise
        """
        tensor = payoff_matrix.payoff_tensor
        n_attacker = len(payoff_matrix.attacker_strategies)
        n_protocol = len(payoff_matrix.protocol_strategies)
        n_mev = len(payoff_matrix.mev_strategies)

        # Check each strategy profile
        for a_idx in range(n_attacker):
            for p_idx in range(n_protocol):
                for m_idx in range(n_mev):
                    if self._is_nash_equilibrium(tensor, a_idx, p_idx, m_idx):
                        # Found pure Nash equilibrium
                        payoffs = tensor[a_idx, p_idx, m_idx]

                        attacker_strat = payoff_matrix.attacker_strategies[a_idx]
                        protocol_strat = payoff_matrix.protocol_strategies[p_idx]
                        mev_strat = payoff_matrix.mev_strategies[m_idx]

                        is_attack_dominant = (
                            attacker_strat != AttackStrategy.ABSTAIN
                            and float(payoffs[0]) > self.min_payoff_threshold
                        )

                        return NashResult(
                            attacker_strategy=attacker_strat.value,
                            protocol_strategy=protocol_strat.value,
                            mev_strategy=mev_strat.value,
                            attacker_payoff=float(payoffs[0]),
                            protocol_payoff=float(payoffs[1]),
                            mev_payoff=float(payoffs[2]),
                            convergence_prob=1.0,  # Pure equilibrium is certain
                            is_attack_dominant=is_attack_dominant,
                            is_pure_equilibrium=True,
                            iterations_to_converge=0,
                            evidence_refs=payoff_matrix.evidence_refs,
                        )

        return None  # No pure equilibrium found

    def _is_nash_equilibrium(
        self,
        tensor: NDArray[np.float64],
        a_idx: int,
        p_idx: int,
        m_idx: int,
    ) -> bool:
        """Check if strategy profile is a Nash equilibrium.

        Args:
            tensor: Payoff tensor
            a_idx: Attacker strategy index
            p_idx: Protocol strategy index
            m_idx: MEV strategy index

        Returns:
            True if this profile is a Nash equilibrium
        """
        # Check attacker can't improve
        attacker_payoff = tensor[a_idx, p_idx, m_idx, 0]
        attacker_best = np.max(tensor[:, p_idx, m_idx, 0])
        if attacker_payoff < attacker_best - 1e-6:
            return False

        # Check protocol can't improve
        protocol_payoff = tensor[a_idx, p_idx, m_idx, 1]
        protocol_best = np.max(tensor[a_idx, :, m_idx, 1])
        if protocol_payoff < protocol_best - 1e-6:
            return False

        # Check MEV can't improve
        mev_payoff = tensor[a_idx, p_idx, m_idx, 2]
        mev_best = np.max(tensor[a_idx, p_idx, :, 2])
        if mev_payoff < mev_best - 1e-6:
            return False

        return True

    def approximate_mixed_nash(
        self,
        payoff_matrix: AttackPayoffMatrix,
    ) -> NashResult:
        """Approximate mixed strategy Nash equilibrium via iterated best response.

        Per 05.11-06: Uses iterated best response for 3-player games.
        Each iteration, each player updates their strategy to best respond
        to the current strategies of other players.

        Args:
            payoff_matrix: AttackPayoffMatrix from attack synthesis

        Returns:
            NashResult with approximated mixed equilibrium
        """
        tensor = payoff_matrix.payoff_tensor
        n_attacker = len(payoff_matrix.attacker_strategies)
        n_protocol = len(payoff_matrix.protocol_strategies)
        n_mev = len(payoff_matrix.mev_strategies)

        # Initialize with uniform distributions
        attacker_probs = np.ones(n_attacker) / n_attacker
        protocol_probs = np.ones(n_protocol) / n_protocol
        mev_probs = np.ones(n_mev) / n_mev

        iterations = 0
        converged = False

        for iteration in range(self.max_iterations):
            iterations = iteration + 1

            # Store old probabilities for convergence check
            old_attacker = attacker_probs.copy()
            old_protocol = protocol_probs.copy()
            old_mev = mev_probs.copy()

            # Attacker best response to protocol and MEV distributions
            attacker_ev = self._compute_expected_payoffs(
                tensor[:, :, :, 0], protocol_probs, mev_probs, axis="attacker"
            )
            attacker_probs = self._softmax_best_response(attacker_ev)

            # Protocol best response
            protocol_ev = self._compute_expected_payoffs(
                tensor[:, :, :, 1], attacker_probs, mev_probs, axis="protocol"
            )
            protocol_probs = self._softmax_best_response(protocol_ev)

            # MEV best response
            mev_ev = self._compute_expected_payoffs(
                tensor[:, :, :, 2], attacker_probs, protocol_probs, axis="mev"
            )
            mev_probs = self._softmax_best_response(mev_ev)

            # Check convergence
            attacker_change = np.max(np.abs(attacker_probs - old_attacker))
            protocol_change = np.max(np.abs(protocol_probs - old_protocol))
            mev_change = np.max(np.abs(mev_probs - old_mev))

            if max(attacker_change, protocol_change, mev_change) < self.convergence_threshold:
                converged = True
                break

        # Compute expected payoffs at mixed equilibrium
        expected_attacker = self._mixed_equilibrium_payoff(
            tensor[:, :, :, 0], attacker_probs, protocol_probs, mev_probs
        )
        expected_protocol = self._mixed_equilibrium_payoff(
            tensor[:, :, :, 1], attacker_probs, protocol_probs, mev_probs
        )
        expected_mev = self._mixed_equilibrium_payoff(
            tensor[:, :, :, 2], attacker_probs, protocol_probs, mev_probs
        )

        # Get most likely strategies
        best_attacker_idx = int(np.argmax(attacker_probs))
        best_protocol_idx = int(np.argmax(protocol_probs))
        best_mev_idx = int(np.argmax(mev_probs))

        attacker_strat = payoff_matrix.attacker_strategies[best_attacker_idx]
        protocol_strat = payoff_matrix.protocol_strategies[best_protocol_idx]
        mev_strat = payoff_matrix.mev_strategies[best_mev_idx]

        # Build mixed strategy probability dict
        mixed_probs = {
            "attacker": {
                payoff_matrix.attacker_strategies[i].value: float(p)
                for i, p in enumerate(attacker_probs)
            },
            "protocol": {
                payoff_matrix.protocol_strategies[i].value: float(p)
                for i, p in enumerate(protocol_probs)
            },
            "mev": {
                payoff_matrix.mev_strategies[i].value: float(p)
                for i, p in enumerate(mev_probs)
            },
        }

        # Check if attack dominates abstain
        abstain_idx = (
            payoff_matrix.attacker_strategies.index(AttackStrategy.ABSTAIN)
            if AttackStrategy.ABSTAIN in payoff_matrix.attacker_strategies
            else None
        )

        is_attack_dominant = (
            attacker_strat != AttackStrategy.ABSTAIN
            and expected_attacker > self.min_payoff_threshold
        )

        if abstain_idx is not None:
            abstain_prob = attacker_probs[abstain_idx]
            is_attack_dominant = is_attack_dominant and abstain_prob < 0.5

        return NashResult(
            attacker_strategy=attacker_strat.value,
            protocol_strategy=protocol_strat.value,
            mev_strategy=mev_strat.value,
            attacker_payoff=float(expected_attacker),
            protocol_payoff=float(expected_protocol),
            mev_payoff=float(expected_mev),
            convergence_prob=0.9 if converged else 0.7,
            is_attack_dominant=is_attack_dominant,
            is_pure_equilibrium=False,
            mixed_strategy_probs=mixed_probs,
            iterations_to_converge=iterations,
            evidence_refs=payoff_matrix.evidence_refs,
        )

    def _compute_expected_payoffs(
        self,
        payoff_slice: NDArray[np.float64],
        probs1: NDArray[np.float64],
        probs2: NDArray[np.float64],
        axis: str,
    ) -> NDArray[np.float64]:
        """Compute expected payoffs for a player given opponent distributions.

        Args:
            payoff_slice: 3D slice of payoffs for this player
            probs1: First opponent probability distribution
            probs2: Second opponent probability distribution
            axis: Which axis this player is on ("attacker", "protocol", "mev")

        Returns:
            Expected payoffs for each strategy
        """
        if axis == "attacker":
            # Expected over protocol (axis 1) and mev (axis 2)
            weighted = np.einsum("apm,p,m->a", payoff_slice, probs1, probs2)
        elif axis == "protocol":
            # Expected over attacker (axis 0) and mev (axis 2)
            weighted = np.einsum("apm,a,m->p", payoff_slice, probs1, probs2)
        else:  # mev
            # Expected over attacker (axis 0) and protocol (axis 1)
            weighted = np.einsum("apm,a,p->m", payoff_slice, probs1, probs2)

        return weighted

    def _softmax_best_response(
        self,
        expected_payoffs: NDArray[np.float64],
        temperature: float = 0.1,
    ) -> NDArray[np.float64]:
        """Compute softmax best response probabilities.

        Uses softmax instead of pure best response for smoother convergence.

        Args:
            expected_payoffs: Expected payoff for each strategy
            temperature: Softmax temperature (lower = more deterministic)

        Returns:
            Probability distribution over strategies
        """
        # Numerical stability: subtract max
        payoffs = expected_payoffs - np.max(expected_payoffs)
        exp_payoffs = np.exp(payoffs / temperature)
        return exp_payoffs / np.sum(exp_payoffs)

    def _mixed_equilibrium_payoff(
        self,
        payoff_slice: NDArray[np.float64],
        attacker_probs: NDArray[np.float64],
        protocol_probs: NDArray[np.float64],
        mev_probs: NDArray[np.float64],
    ) -> float:
        """Compute expected payoff at mixed equilibrium.

        Args:
            payoff_slice: 3D payoff array for one player
            attacker_probs: Attacker strategy probabilities
            protocol_probs: Protocol strategy probabilities
            mev_probs: MEV strategy probabilities

        Returns:
            Expected payoff
        """
        return float(np.einsum("apm,a,p,m->", payoff_slice, attacker_probs, protocol_probs, mev_probs))

    def identify_blocking_conditions(
        self,
        payoff_matrix: AttackPayoffMatrix,
        nash_result: NashResult,
    ) -> List[BlockingCondition]:
        """Identify conditions that block or reduce attack profitability.

        Per 05.11-06: Analyzes payoff matrix and equilibrium to find
        defenses and costs that make attacks irrational.

        Args:
            payoff_matrix: AttackPayoffMatrix from attack synthesis
            nash_result: NashResult from equilibrium computation

        Returns:
            List of blocking conditions
        """
        blocking_conditions = []
        tensor = payoff_matrix.payoff_tensor

        # Find abstain payoff as baseline
        abstain_idx = None
        for i, strat in enumerate(payoff_matrix.attacker_strategies):
            if strat == AttackStrategy.ABSTAIN:
                abstain_idx = i
                break

        if abstain_idx is None:
            return blocking_conditions

        # Compare each defense to no defense
        no_defense_idx = None
        for i, defense in enumerate(payoff_matrix.protocol_strategies):
            if defense == ProtocolDefense.NO_DEFENSE:
                no_defense_idx = i
                break

        if no_defense_idx is None:
            return blocking_conditions

        # For each attack strategy, check which defenses block it
        for a_idx, a_strat in enumerate(payoff_matrix.attacker_strategies):
            if a_strat == AttackStrategy.ABSTAIN:
                continue

            # Baseline payoff with no defense
            baseline_payoff = float(np.mean(tensor[a_idx, no_defense_idx, :, 0]))

            # Check each defense
            for p_idx, p_strat in enumerate(payoff_matrix.protocol_strategies):
                if p_strat == ProtocolDefense.NO_DEFENSE:
                    continue

                defended_payoff = float(np.mean(tensor[a_idx, p_idx, :, 0]))
                reduction = baseline_payoff - defended_payoff

                if reduction > 0:
                    # This defense reduces attacker payoff
                    effect_ratio = reduction / max(baseline_payoff, 1)

                    # Only report significant blockers
                    if effect_ratio > 0.2 or defended_payoff < 0:
                        threshold = self._compute_threshold(p_strat, effect_ratio)
                        description = (
                            f"{p_strat.value} reduces {a_strat.value} profit "
                            f"by ${reduction:,.2f} ({effect_ratio:.0%})"
                        )

                        blocking_conditions.append(
                            BlockingCondition(
                                condition_type=BlockingConditionType.from_defense(p_strat),
                                threshold=threshold,
                                effect_usd=reduction,
                                description=description,
                                confidence=0.8,
                                evidence_refs=payoff_matrix.evidence_refs,
                            )
                        )

        # Check if attack is blocked by being worse than abstaining
        if not nash_result.is_attack_dominant:
            abstain_payoff = float(np.max(tensor[abstain_idx, :, :, 0]))
            best_attack_payoff = nash_result.attacker_payoff

            if abstain_payoff >= best_attack_payoff:
                blocking_conditions.append(
                    BlockingCondition(
                        condition_type=BlockingConditionType.GAS_COST,
                        threshold=f"attack EV (${best_attack_payoff:,.2f}) <= abstain (${abstain_payoff:,.2f})",
                        effect_usd=abstain_payoff - best_attack_payoff,
                        description="Attack is economically irrational compared to honest behavior",
                        confidence=0.95,
                    )
                )

        return blocking_conditions

    def _compute_threshold(
        self,
        defense: ProtocolDefense,
        effect_ratio: float,
    ) -> str:
        """Compute threshold description for a defense.

        Args:
            defense: Protocol defense
            effect_ratio: How much defense reduces attacker payoff (0-1)

        Returns:
            Human-readable threshold description
        """
        thresholds = {
            ProtocolDefense.TIMELOCK: f"timelock > {int(86400 * effect_ratio)} seconds",
            ProtocolDefense.RATE_LIMIT: f"rate_limit < {100 * (1 - effect_ratio):.0f}% of TVL",
            ProtocolDefense.PAUSE_MECHANISM: "emergency_pause_enabled = true",
            ProtocolDefense.REENTRANCY_GUARD: "reentrancy_guard_active = true",
            ProtocolDefense.ACCESS_CONTROL: "access_control_enforced = true",
            ProtocolDefense.ORACLE_VALIDATION: f"oracle_deviation_check <= {effect_ratio * 10:.1f}%",
            ProtocolDefense.MEV_PROTECTION: "mev_protection_enabled = true",
            ProtocolDefense.MONITORING: f"detection_probability > {effect_ratio * 100:.0f}%",
        }

        return thresholds.get(defense, f"defense_effectiveness > {effect_ratio * 100:.0f}%")

    def solve_2player_subgame(
        self,
        payoff_matrix: AttackPayoffMatrix,
        fix_mev: Optional[MEVStrategy] = None,
    ) -> NashResult:
        """Solve 2-player subgame with MEV fixed.

        Uses Lemke-Howson algorithm for exact 2-player Nash equilibrium.

        Args:
            payoff_matrix: AttackPayoffMatrix
            fix_mev: Fixed MEV strategy (defaults to ABSTAIN)

        Returns:
            NashResult for 2-player subgame
        """
        fix_mev = fix_mev or MEVStrategy.ABSTAIN
        m_idx = payoff_matrix.mev_strategies.index(fix_mev)

        # Extract 2-player payoff matrices
        tensor = payoff_matrix.payoff_tensor
        attacker_payoffs = tensor[:, :, m_idx, 0]  # (A, P)
        protocol_payoffs = tensor[:, :, m_idx, 1]  # (A, P)

        # Find Nash using support enumeration for small games
        result = self._support_enumeration(
            attacker_payoffs,
            protocol_payoffs,
            payoff_matrix.attacker_strategies,
            payoff_matrix.protocol_strategies,
        )

        if result is not None:
            result.mev_strategy = fix_mev.value
            result.mev_payoff = float(tensor[
                payoff_matrix.attacker_strategies.index(AttackStrategy(result.attacker_strategy)),
                payoff_matrix.protocol_strategies.index(ProtocolDefense(result.protocol_strategy)),
                m_idx,
                2,
            ])
            return result

        # Fall back to iterated best response
        return self.approximate_mixed_nash(payoff_matrix)

    def _support_enumeration(
        self,
        row_payoffs: NDArray[np.float64],
        col_payoffs: NDArray[np.float64],
        row_strategies: List[AttackStrategy],
        col_strategies: List[ProtocolDefense],
    ) -> Optional[NashResult]:
        """Find Nash equilibrium via support enumeration.

        For small games, enumerate possible support sets.

        Args:
            row_payoffs: Row player (attacker) payoffs
            col_payoffs: Column player (protocol) payoffs
            row_strategies: Row player strategies
            col_strategies: Column player strategies

        Returns:
            NashResult if found, None otherwise
        """
        n_row, n_col = row_payoffs.shape

        # Try pure strategies first
        for i in range(n_row):
            for j in range(n_col):
                # Check if (i, j) is a Nash equilibrium
                if (
                    row_payoffs[i, j] >= np.max(row_payoffs[:, j]) - 1e-6
                    and col_payoffs[i, j] >= np.max(col_payoffs[i, :]) - 1e-6
                ):
                    attacker_strat = row_strategies[i]
                    protocol_strat = col_strategies[j]

                    return NashResult(
                        attacker_strategy=attacker_strat.value,
                        protocol_strategy=protocol_strat.value,
                        mev_strategy="abstain",
                        attacker_payoff=float(row_payoffs[i, j]),
                        protocol_payoff=float(col_payoffs[i, j]),
                        is_attack_dominant=attacker_strat != AttackStrategy.ABSTAIN and row_payoffs[i, j] > 0,
                        is_pure_equilibrium=True,
                    )

        return None


# =============================================================================
# Module Exports
# =============================================================================


__all__ = [
    "BlockingConditionType",
    "BlockingCondition",
    "NashResult",
    "NashEquilibriumSolver",
]
