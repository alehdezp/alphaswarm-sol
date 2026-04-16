"""Attack synthesis engine for game-theoretic vulnerability analysis.

Per 05.11-06: The AttackSynthesisEngine models each vulnerability as a 3-player
game between Attacker, Protocol, and MEV Searchers, computing payoff matrices
that enable Nash equilibrium analysis.

Key Features:
- 3-player game model: Attacker, Protocol, MEV Searchers
- Payoff tensor: 3D array of payoffs for each strategy combination
- Expected value computation including MEV extraction, slippage, flashloan fees
- Strategy enumeration for exploit paths, defenses, and MEV tactics

Usage:
    from alphaswarm_sol.economics.gate.attack_synthesis import (
        AttackSynthesisEngine,
        AttackPayoffMatrix,
        compute_attack_ev,
    )

    engine = AttackSynthesisEngine()
    matrix = engine.compute_attack_ev(
        vulnerability={"id": "reentrancy-1", "severity": "high", ...},
        protocol_state={"tvl_usd": 10_000_000, "gas_price_gwei": 50},
    )

    print(f"Attacker strategies: {matrix.attacker_strategies}")
    print(f"Protocol defenses: {matrix.protocol_strategies}")
    print(f"MEV strategies: {matrix.mev_strategies}")
    print(f"Is attack dominant: {matrix.dominant_strategies}")
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

from ..payoff import AttackPayoff, DefensePayoff, PayoffMatrix, PayoffPlayer

logger = logging.getLogger(__name__)


# =============================================================================
# Strategy Enumerations
# =============================================================================


class AttackStrategy(Enum):
    """Attack strategies for the attacker player.

    Represents the action space for an attacker considering whether
    and how to exploit a vulnerability.
    """

    ABSTAIN = "abstain"  # Don't attack (honest behavior)
    DIRECT_EXPLOIT = "direct_exploit"  # Simple direct exploitation
    FLASHLOAN_EXPLOIT = "flashloan_exploit"  # Exploit with flash loan capital
    MULTISTEP_EXPLOIT = "multistep_exploit"  # Complex multi-transaction attack
    SANDWICH_ATTACK = "sandwich_attack"  # Sandwich victim transactions
    GOVERNANCE_EXPLOIT = "governance_exploit"  # Exploit via governance proposal
    ORACLE_MANIPULATION = "oracle_manipulation"  # Manipulate price oracle

    @classmethod
    def from_pattern(cls, pattern_id: str) -> "AttackStrategy":
        """Infer attack strategy from vulnerability pattern.

        Args:
            pattern_id: Pattern identifier (e.g., "reentrancy-classic")

        Returns:
            Most appropriate attack strategy for the pattern
        """
        pattern_lower = pattern_id.lower()

        if "flash" in pattern_lower:
            return cls.FLASHLOAN_EXPLOIT
        elif "sandwich" in pattern_lower or "frontrun" in pattern_lower:
            return cls.SANDWICH_ATTACK
        elif "governance" in pattern_lower or "vote" in pattern_lower:
            return cls.GOVERNANCE_EXPLOIT
        elif "oracle" in pattern_lower or "price" in pattern_lower:
            return cls.ORACLE_MANIPULATION
        elif "reentran" in pattern_lower or "cross-function" in pattern_lower:
            return cls.MULTISTEP_EXPLOIT
        else:
            return cls.DIRECT_EXPLOIT


class ProtocolDefense(Enum):
    """Defense strategies for the protocol player.

    Represents available defenses a protocol can deploy against attacks.
    """

    NO_DEFENSE = "no_defense"  # No active defense
    TIMELOCK = "timelock"  # Timelock delay on sensitive operations
    RATE_LIMIT = "rate_limit"  # Rate limiting on value extraction
    PAUSE_MECHANISM = "pause_mechanism"  # Emergency pause capability
    REENTRANCY_GUARD = "reentrancy_guard"  # Reentrancy protection
    ACCESS_CONTROL = "access_control"  # Role-based access control
    ORACLE_VALIDATION = "oracle_validation"  # Oracle price bounds checking
    MEV_PROTECTION = "mev_protection"  # MEV protection (private tx, flashbots)
    MONITORING = "monitoring"  # Active monitoring and response

    @classmethod
    def from_guard_types(cls, guard_types: List[str]) -> List["ProtocolDefense"]:
        """Map guard types from KG to defense strategies.

        Args:
            guard_types: List of guard type strings from knowledge graph

        Returns:
            List of corresponding protocol defenses
        """
        mapping = {
            "reentrancy_guard": cls.REENTRANCY_GUARD,
            "access_control": cls.ACCESS_CONTROL,
            "timelock": cls.TIMELOCK,
            "rate_limit": cls.RATE_LIMIT,
            "pause": cls.PAUSE_MECHANISM,
            "oracle_check": cls.ORACLE_VALIDATION,
            "monitoring": cls.MONITORING,
        }

        defenses = []
        for guard in guard_types:
            guard_lower = guard.lower().replace("-", "_")
            for key, defense in mapping.items():
                if key in guard_lower:
                    defenses.append(defense)
                    break

        return defenses if defenses else [cls.NO_DEFENSE]


class MEVStrategy(Enum):
    """MEV strategies for MEV searcher players.

    Represents tactics MEV searchers can employ around an attack.
    """

    ABSTAIN = "abstain"  # Don't participate
    FRONTRUN = "frontrun"  # Front-run the attacker
    BACKRUN = "backrun"  # Back-run to capture arbitrage
    SANDWICH = "sandwich"  # Full sandwich (front + back)
    COPY_ATTACK = "copy_attack"  # Copy and front-run the entire attack
    LIQUIDATE = "liquidate"  # Liquidate positions created by attack
    PROTECT = "protect"  # Use Flashbots to protect transaction


# =============================================================================
# Cost Models
# =============================================================================


@dataclass
class CostModel:
    """Cost model for attack execution.

    Attributes:
        gas_price_gwei: Current gas price in Gwei
        eth_price_usd: ETH price in USD
        flashloan_fee_bps: Flash loan fee in basis points (default 9 = 0.09%)
        slippage_bps: Expected slippage in basis points
        oracle_manipulation_cost_usd: Cost to manipulate oracle prices
    """

    gas_price_gwei: float = 50.0
    eth_price_usd: float = 2000.0
    flashloan_fee_bps: float = 9.0  # 0.09% Aave/dYdX fee
    slippage_bps: float = 50.0  # 0.5% slippage
    oracle_manipulation_cost_usd: float = 10000.0

    def gas_cost_usd(self, gas_units: int) -> float:
        """Calculate gas cost in USD.

        Args:
            gas_units: Gas units consumed

        Returns:
            Gas cost in USD
        """
        gas_eth = (self.gas_price_gwei * gas_units) / 1e9
        return gas_eth * self.eth_price_usd

    def flashloan_fee_usd(self, principal_usd: float) -> float:
        """Calculate flash loan fee.

        Args:
            principal_usd: Flash loan principal in USD

        Returns:
            Flash loan fee in USD
        """
        return principal_usd * (self.flashloan_fee_bps / 10000)

    def slippage_cost_usd(self, trade_volume_usd: float) -> float:
        """Calculate expected slippage cost.

        Args:
            trade_volume_usd: Trade volume in USD

        Returns:
            Expected slippage cost in USD
        """
        return trade_volume_usd * (self.slippage_bps / 10000)


# =============================================================================
# Attack Payoff Matrix
# =============================================================================


@dataclass
class AttackPayoffMatrix:
    """3-player game payoff matrix for attack analysis.

    Per 05.11-06: Models vulnerability as a 3-player game with:
    - Attacker strategies (exploit paths)
    - Protocol defenses (guards, pauses)
    - MEV searcher strategies (frontrun, backrun, sandwich)

    The payoff_tensor is a 3D numpy array where:
    - Axis 0: Attacker strategies
    - Axis 1: Protocol strategies
    - Axis 2: MEV strategies

    Each cell contains a tuple of (attacker_payoff, protocol_payoff, mev_payoff).

    Attributes:
        vulnerability_id: ID of the vulnerability being analyzed
        scenario: Scenario name (e.g., "reentrancy", "oracle_manipulation")
        attacker_strategies: List of available attack strategies
        protocol_strategies: List of available defense strategies
        mev_strategies: List of available MEV strategies
        payoff_tensor: 3D array of payoffs indexed by strategies
        dominant_strategies: Dict mapping player to dominant strategy
        expected_value_usd: Attacker's expected value at equilibrium
        cost_model: Cost parameters used in computation
        evidence_refs: References to supporting evidence
    """

    vulnerability_id: str
    scenario: str
    attacker_strategies: List[AttackStrategy]
    protocol_strategies: List[ProtocolDefense]
    mev_strategies: List[MEVStrategy]
    payoff_tensor: NDArray[np.float64]  # Shape: (A, P, M, 3) for 3 players
    dominant_strategies: Dict[str, str] = field(default_factory=dict)
    expected_value_usd: float = 0.0
    cost_model: Optional[CostModel] = None
    evidence_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate tensor dimensions match strategy counts."""
        expected_shape = (
            len(self.attacker_strategies),
            len(self.protocol_strategies),
            len(self.mev_strategies),
            3,  # 3 players
        )
        if self.payoff_tensor.shape != expected_shape:
            raise ValueError(
                f"Payoff tensor shape {self.payoff_tensor.shape} does not match "
                f"expected shape {expected_shape} from strategy counts"
            )

    def get_payoff(
        self,
        attacker_strategy: AttackStrategy,
        protocol_strategy: ProtocolDefense,
        mev_strategy: MEVStrategy,
    ) -> Tuple[float, float, float]:
        """Get payoffs for a specific strategy profile.

        Args:
            attacker_strategy: Attacker's chosen strategy
            protocol_strategy: Protocol's chosen defense
            mev_strategy: MEV searcher's chosen tactic

        Returns:
            Tuple of (attacker_payoff, protocol_payoff, mev_payoff)
        """
        a_idx = self.attacker_strategies.index(attacker_strategy)
        p_idx = self.protocol_strategies.index(protocol_strategy)
        m_idx = self.mev_strategies.index(mev_strategy)

        payoffs = self.payoff_tensor[a_idx, p_idx, m_idx]
        return (float(payoffs[0]), float(payoffs[1]), float(payoffs[2]))

    def attacker_best_response(
        self,
        protocol_strategy: ProtocolDefense,
        mev_strategy: MEVStrategy,
    ) -> Tuple[AttackStrategy, float]:
        """Find attacker's best response to given protocol and MEV strategies.

        Args:
            protocol_strategy: Protocol's strategy
            mev_strategy: MEV searcher's strategy

        Returns:
            Tuple of (best_strategy, expected_payoff)
        """
        p_idx = self.protocol_strategies.index(protocol_strategy)
        m_idx = self.mev_strategies.index(mev_strategy)

        attacker_payoffs = self.payoff_tensor[:, p_idx, m_idx, 0]
        best_idx = int(np.argmax(attacker_payoffs))

        return (
            self.attacker_strategies[best_idx],
            float(attacker_payoffs[best_idx]),
        )

    def protocol_best_response(
        self,
        attacker_strategy: AttackStrategy,
        mev_strategy: MEVStrategy,
    ) -> Tuple[ProtocolDefense, float]:
        """Find protocol's best response to given attacker and MEV strategies.

        Note: Protocol maximizes its payoff (minimizes loss, since payoffs are negative).

        Args:
            attacker_strategy: Attacker's strategy
            mev_strategy: MEV searcher's strategy

        Returns:
            Tuple of (best_defense, expected_payoff)
        """
        a_idx = self.attacker_strategies.index(attacker_strategy)
        m_idx = self.mev_strategies.index(mev_strategy)

        protocol_payoffs = self.payoff_tensor[a_idx, :, m_idx, 1]
        best_idx = int(np.argmax(protocol_payoffs))  # Max = minimize loss

        return (
            self.protocol_strategies[best_idx],
            float(protocol_payoffs[best_idx]),
        )

    def mev_best_response(
        self,
        attacker_strategy: AttackStrategy,
        protocol_strategy: ProtocolDefense,
    ) -> Tuple[MEVStrategy, float]:
        """Find MEV searcher's best response to given attacker and protocol strategies.

        Args:
            attacker_strategy: Attacker's strategy
            protocol_strategy: Protocol's strategy

        Returns:
            Tuple of (best_mev_strategy, expected_payoff)
        """
        a_idx = self.attacker_strategies.index(attacker_strategy)
        p_idx = self.protocol_strategies.index(protocol_strategy)

        mev_payoffs = self.payoff_tensor[a_idx, p_idx, :, 2]
        best_idx = int(np.argmax(mev_payoffs))

        return (
            self.mev_strategies[best_idx],
            float(mev_payoffs[best_idx]),
        )

    def is_attack_dominant(self) -> bool:
        """Check if any attack strategy dominates abstaining.

        Returns:
            True if at least one attack strategy has higher EV than abstaining
        """
        if AttackStrategy.ABSTAIN not in self.attacker_strategies:
            return True

        abstain_idx = self.attacker_strategies.index(AttackStrategy.ABSTAIN)
        abstain_payoffs = self.payoff_tensor[abstain_idx, :, :, 0]
        abstain_max = float(np.max(abstain_payoffs))

        # Check if any attack strategy beats abstaining in any scenario
        for i, strategy in enumerate(self.attacker_strategies):
            if strategy != AttackStrategy.ABSTAIN:
                attack_payoffs = self.payoff_tensor[i, :, :, 0]
                if float(np.max(attack_payoffs)) > abstain_max:
                    return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "vulnerability_id": self.vulnerability_id,
            "scenario": self.scenario,
            "attacker_strategies": [s.value for s in self.attacker_strategies],
            "protocol_strategies": [s.value for s in self.protocol_strategies],
            "mev_strategies": [s.value for s in self.mev_strategies],
            "payoff_tensor": self.payoff_tensor.tolist(),
            "dominant_strategies": self.dominant_strategies,
            "expected_value_usd": self.expected_value_usd,
            "evidence_refs": self.evidence_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AttackPayoffMatrix":
        """Create AttackPayoffMatrix from dictionary."""
        return cls(
            vulnerability_id=str(data.get("vulnerability_id", "")),
            scenario=str(data.get("scenario", "")),
            attacker_strategies=[
                AttackStrategy(s) for s in data.get("attacker_strategies", ["abstain"])
            ],
            protocol_strategies=[
                ProtocolDefense(s) for s in data.get("protocol_strategies", ["no_defense"])
            ],
            mev_strategies=[
                MEVStrategy(s) for s in data.get("mev_strategies", ["abstain"])
            ],
            payoff_tensor=np.array(data.get("payoff_tensor", [[[[0, 0, 0]]]])),
            dominant_strategies=dict(data.get("dominant_strategies", {})),
            expected_value_usd=float(data.get("expected_value_usd", 0)),
            evidence_refs=list(data.get("evidence_refs", [])),
        )


# =============================================================================
# Attack Synthesis Engine
# =============================================================================


class AttackSynthesisEngine:
    """Engine for synthesizing attack payoff matrices.

    Per 05.11-06: Computes 3-player payoff matrices for vulnerabilities,
    modeling attacker profit, protocol loss, and MEV extraction.

    The engine:
    1. Enumerates available strategies for each player
    2. Computes payoffs for each strategy combination
    3. Builds the payoff tensor
    4. Identifies dominant strategies

    Usage:
        engine = AttackSynthesisEngine()

        matrix = engine.compute_attack_ev(
            vulnerability={"id": "vuln-1", "severity": "high", ...},
            protocol_state={"tvl_usd": 10_000_000, ...},
        )

        if matrix.is_attack_dominant():
            print("Attack is economically rational")
    """

    def __init__(
        self,
        default_gas_units: int = 500_000,
        default_success_prob: float = 0.5,
        mev_extraction_rate: float = 0.3,
    ):
        """Initialize attack synthesis engine.

        Args:
            default_gas_units: Default gas consumption estimate
            default_success_prob: Default attack success probability
            mev_extraction_rate: Rate at which MEV searchers extract value (0-1)
        """
        self.default_gas_units = default_gas_units
        self.default_success_prob = default_success_prob
        self.mev_extraction_rate = mev_extraction_rate

    def compute_attack_ev(
        self,
        vulnerability: Dict[str, Any],
        protocol_state: Optional[Dict[str, Any]] = None,
        gas_price_gwei: Optional[float] = None,
        tvl_usd: Optional[float] = None,
    ) -> AttackPayoffMatrix:
        """Compute attack payoff matrix for a vulnerability.

        Per 05.11-06: Models vulnerability as 3-player game with payoffs
        computed for each strategy combination.

        Args:
            vulnerability: Vulnerability data dict with:
                - id: Vulnerability identifier
                - severity: Severity level (critical/high/medium/low)
                - pattern_id: Pattern identifier (optional)
                - potential_profit_usd: Estimated profit (optional)
                - success_probability: Success probability (optional)
                - guard_types: List of active guards (optional)
                - gas_cost_estimate: Gas units estimate (optional)
            protocol_state: Optional protocol context with:
                - tvl_usd: Total value locked
                - gas_price_gwei: Current gas price
                - eth_price_usd: ETH price
                - detection_probability: Protocol's detection capability
                - timelock_seconds: Timelock delay
                - has_pause: Whether protocol can pause
            gas_price_gwei: Override gas price (uses protocol_state or default)
            tvl_usd: Override TVL (uses protocol_state or default)

        Returns:
            AttackPayoffMatrix with 3-player game model
        """
        protocol_state = protocol_state or {}
        vuln_id = vulnerability.get("id", self._generate_id(vulnerability))

        # Build cost model
        cost_model = CostModel(
            gas_price_gwei=gas_price_gwei or protocol_state.get("gas_price_gwei", 50.0),
            eth_price_usd=protocol_state.get("eth_price_usd", 2000.0),
            flashloan_fee_bps=protocol_state.get("flashloan_fee_bps", 9.0),
            slippage_bps=protocol_state.get("slippage_bps", 50.0),
        )

        # Get TVL for profit estimation
        effective_tvl = tvl_usd or protocol_state.get("tvl_usd", 1_000_000)

        # Enumerate strategies
        attacker_strategies = self._enumerate_attacker_strategies(vulnerability)
        protocol_strategies = self._enumerate_protocol_strategies(vulnerability, protocol_state)
        mev_strategies = self._enumerate_mev_strategies(vulnerability)

        # Build payoff tensor
        payoff_tensor = self._build_payoff_tensor(
            vulnerability=vulnerability,
            protocol_state=protocol_state,
            cost_model=cost_model,
            tvl_usd=effective_tvl,
            attacker_strategies=attacker_strategies,
            protocol_strategies=protocol_strategies,
            mev_strategies=mev_strategies,
        )

        # Find dominant strategies
        dominant_strategies = self._find_dominant_strategies(
            payoff_tensor,
            attacker_strategies,
            protocol_strategies,
            mev_strategies,
        )

        # Compute expected value at dominant profile
        ev = self._compute_equilibrium_ev(
            payoff_tensor,
            attacker_strategies,
            protocol_strategies,
            mev_strategies,
            dominant_strategies,
        )

        # Build scenario name
        scenario = self._infer_scenario(vulnerability)

        matrix = AttackPayoffMatrix(
            vulnerability_id=vuln_id,
            scenario=scenario,
            attacker_strategies=attacker_strategies,
            protocol_strategies=protocol_strategies,
            mev_strategies=mev_strategies,
            payoff_tensor=payoff_tensor,
            dominant_strategies=dominant_strategies,
            expected_value_usd=ev,
            cost_model=cost_model,
            evidence_refs=vulnerability.get("evidence_refs", []),
        )

        logger.info(
            f"GATE: Synthesized matrix for {vuln_id}, "
            f"EV=${ev:,.2f}, attack_dominant={matrix.is_attack_dominant()}"
        )

        return matrix

    def _generate_id(self, vulnerability: Dict[str, Any]) -> str:
        """Generate stable ID for vulnerability."""
        content = str(sorted(vulnerability.items()))
        return f"vuln-{hashlib.sha256(content.encode()).hexdigest()[:8]}"

    def _enumerate_attacker_strategies(
        self,
        vulnerability: Dict[str, Any],
    ) -> List[AttackStrategy]:
        """Enumerate available attack strategies for vulnerability.

        Args:
            vulnerability: Vulnerability data

        Returns:
            List of applicable attack strategies
        """
        strategies = [AttackStrategy.ABSTAIN]  # Always include abstain

        pattern_id = vulnerability.get("pattern_id", "")
        severity = vulnerability.get("severity", "medium").lower()

        # Add primary strategy based on pattern
        primary = AttackStrategy.from_pattern(pattern_id)
        if primary != AttackStrategy.ABSTAIN:
            strategies.append(primary)

        # Add complementary strategies based on severity
        if severity in ("critical", "high"):
            if AttackStrategy.FLASHLOAN_EXPLOIT not in strategies:
                strategies.append(AttackStrategy.FLASHLOAN_EXPLOIT)
            if AttackStrategy.MULTISTEP_EXPLOIT not in strategies:
                strategies.append(AttackStrategy.MULTISTEP_EXPLOIT)

        # Direct exploit is always an option
        if AttackStrategy.DIRECT_EXPLOIT not in strategies:
            strategies.append(AttackStrategy.DIRECT_EXPLOIT)

        return strategies

    def _enumerate_protocol_strategies(
        self,
        vulnerability: Dict[str, Any],
        protocol_state: Dict[str, Any],
    ) -> List[ProtocolDefense]:
        """Enumerate available protocol defenses.

        Args:
            vulnerability: Vulnerability data
            protocol_state: Protocol state

        Returns:
            List of applicable defense strategies
        """
        defenses = [ProtocolDefense.NO_DEFENSE]

        # Add defenses from guard types
        guard_types = vulnerability.get("guard_types", [])
        if guard_types:
            defenses.extend(ProtocolDefense.from_guard_types(guard_types))

        # Add defenses from protocol state
        if protocol_state.get("has_timelock") or protocol_state.get("timelock_seconds", 0) > 0:
            defenses.append(ProtocolDefense.TIMELOCK)

        if protocol_state.get("has_pause") or protocol_state.get("emergency_pause_capable"):
            defenses.append(ProtocolDefense.PAUSE_MECHANISM)

        if protocol_state.get("detection_probability", 0) > 0.5:
            defenses.append(ProtocolDefense.MONITORING)

        if protocol_state.get("has_mev_protection"):
            defenses.append(ProtocolDefense.MEV_PROTECTION)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for d in defenses:
            if d not in seen:
                seen.add(d)
                unique.append(d)

        return unique

    def _enumerate_mev_strategies(
        self,
        vulnerability: Dict[str, Any],
    ) -> List[MEVStrategy]:
        """Enumerate available MEV strategies.

        Args:
            vulnerability: Vulnerability data

        Returns:
            List of applicable MEV strategies
        """
        strategies = [MEVStrategy.ABSTAIN]

        pattern_id = vulnerability.get("pattern_id", "").lower()
        mev_exposure = vulnerability.get("mev_exposure", "low")

        # High MEV exposure patterns
        if any(x in pattern_id for x in ["sandwich", "frontrun", "swap", "amm", "dex"]):
            strategies.extend([MEVStrategy.FRONTRUN, MEVStrategy.SANDWICH])

        # Flash loan attacks can be copied
        if "flash" in pattern_id:
            strategies.append(MEVStrategy.COPY_ATTACK)

        # Liquidation opportunities
        if any(x in pattern_id for x in ["liquidat", "collateral", "borrow"]):
            strategies.append(MEVStrategy.LIQUIDATE)

        # Add basic MEV if exposure is not negligible
        if mev_exposure != "none":
            if MEVStrategy.FRONTRUN not in strategies:
                strategies.append(MEVStrategy.FRONTRUN)
            if MEVStrategy.BACKRUN not in strategies:
                strategies.append(MEVStrategy.BACKRUN)

        return strategies

    def _build_payoff_tensor(
        self,
        vulnerability: Dict[str, Any],
        protocol_state: Dict[str, Any],
        cost_model: CostModel,
        tvl_usd: float,
        attacker_strategies: List[AttackStrategy],
        protocol_strategies: List[ProtocolDefense],
        mev_strategies: List[MEVStrategy],
    ) -> NDArray[np.float64]:
        """Build 3D payoff tensor for all strategy combinations.

        Args:
            vulnerability: Vulnerability data
            protocol_state: Protocol state
            cost_model: Cost model for calculations
            tvl_usd: Total value locked
            attacker_strategies: Available attack strategies
            protocol_strategies: Available defense strategies
            mev_strategies: Available MEV strategies

        Returns:
            4D numpy array of shape (A, P, M, 3) with payoffs
        """
        n_attacker = len(attacker_strategies)
        n_protocol = len(protocol_strategies)
        n_mev = len(mev_strategies)

        # Initialize tensor: (attackers, protocols, mev, 3 players)
        tensor = np.zeros((n_attacker, n_protocol, n_mev, 3), dtype=np.float64)

        # Base profit from vulnerability
        base_profit = self._estimate_base_profit(vulnerability, tvl_usd)
        success_prob = vulnerability.get("success_probability", self.default_success_prob)
        gas_units = vulnerability.get("gas_cost_estimate", self.default_gas_units)

        for a_idx, a_strat in enumerate(attacker_strategies):
            for p_idx, p_strat in enumerate(protocol_strategies):
                for m_idx, m_strat in enumerate(mev_strategies):
                    payoffs = self._compute_payoffs(
                        attacker_strategy=a_strat,
                        protocol_strategy=p_strat,
                        mev_strategy=m_strat,
                        base_profit=base_profit,
                        success_prob=success_prob,
                        gas_units=gas_units,
                        cost_model=cost_model,
                        protocol_state=protocol_state,
                    )
                    tensor[a_idx, p_idx, m_idx] = payoffs

        return tensor

    def _compute_payoffs(
        self,
        attacker_strategy: AttackStrategy,
        protocol_strategy: ProtocolDefense,
        mev_strategy: MEVStrategy,
        base_profit: float,
        success_prob: float,
        gas_units: int,
        cost_model: CostModel,
        protocol_state: Dict[str, Any],
    ) -> NDArray[np.float64]:
        """Compute payoffs for a specific strategy profile.

        Args:
            attacker_strategy: Attacker's strategy
            protocol_strategy: Protocol's defense
            mev_strategy: MEV searcher's tactic
            base_profit: Base extractable profit
            success_prob: Base success probability
            gas_units: Gas consumption
            cost_model: Cost model
            protocol_state: Protocol state

        Returns:
            Array of [attacker_payoff, protocol_payoff, mev_payoff]
        """
        # Abstaining attacker: everyone gets 0
        if attacker_strategy == AttackStrategy.ABSTAIN:
            return np.array([0.0, 0.0, 0.0])

        # Adjust success probability based on defense
        effective_success = self._adjust_success_for_defense(
            success_prob, protocol_strategy, protocol_state
        )

        # Calculate attack costs
        gas_cost = cost_model.gas_cost_usd(gas_units)

        # Strategy-specific modifiers
        profit_modifier, extra_cost = self._get_strategy_modifiers(
            attacker_strategy, base_profit, cost_model
        )

        adjusted_profit = base_profit * profit_modifier
        total_cost = gas_cost + extra_cost

        # MEV extraction
        mev_extraction = self._compute_mev_extraction(
            mev_strategy, adjusted_profit, effective_success
        )

        # Attacker payoff: expected profit - costs - MEV loss
        attacker_expected = effective_success * adjusted_profit - total_cost - mev_extraction
        attacker_payoff = attacker_expected

        # Protocol payoff: negative of loss (higher = better for protocol)
        protocol_loss = effective_success * adjusted_profit
        protocol_payoff = -protocol_loss  # Negative because loss

        # Adjust protocol payoff for defense costs
        defense_cost = self._get_defense_cost(protocol_strategy, base_profit)
        protocol_payoff -= defense_cost

        # MEV payoff
        mev_payoff = mev_extraction if mev_strategy != MEVStrategy.ABSTAIN else 0.0

        return np.array([attacker_payoff, protocol_payoff, mev_payoff])

    def _estimate_base_profit(
        self,
        vulnerability: Dict[str, Any],
        tvl_usd: float,
    ) -> float:
        """Estimate base extractable profit from vulnerability.

        Args:
            vulnerability: Vulnerability data
            tvl_usd: Total value locked

        Returns:
            Estimated profit in USD
        """
        # Use provided profit if available
        if "potential_profit_usd" in vulnerability:
            return float(vulnerability["potential_profit_usd"])

        # Estimate based on severity
        severity = vulnerability.get("severity", "medium").lower()
        extraction_rates = {
            "critical": 0.10,  # 10% of TVL
            "high": 0.05,      # 5% of TVL
            "medium": 0.01,    # 1% of TVL
            "low": 0.001,      # 0.1% of TVL
        }

        rate = extraction_rates.get(severity, 0.01)
        return min(tvl_usd * rate, 10_000_000)  # Cap at $10M

    def _adjust_success_for_defense(
        self,
        base_success: float,
        defense: ProtocolDefense,
        protocol_state: Dict[str, Any],
    ) -> float:
        """Adjust success probability based on active defense.

        Args:
            base_success: Base success probability
            defense: Active defense strategy
            protocol_state: Protocol state

        Returns:
            Adjusted success probability
        """
        defense_effectiveness = {
            ProtocolDefense.NO_DEFENSE: 0.0,
            ProtocolDefense.TIMELOCK: 0.3,  # 30% reduction
            ProtocolDefense.RATE_LIMIT: 0.4,
            ProtocolDefense.PAUSE_MECHANISM: 0.5,
            ProtocolDefense.REENTRANCY_GUARD: 0.8,  # Very effective against reentrancy
            ProtocolDefense.ACCESS_CONTROL: 0.6,
            ProtocolDefense.ORACLE_VALIDATION: 0.5,
            ProtocolDefense.MEV_PROTECTION: 0.2,
            ProtocolDefense.MONITORING: 0.3,
        }

        reduction = defense_effectiveness.get(defense, 0.0)

        # Additional reduction from detection probability
        detection_prob = protocol_state.get("detection_probability", 0.0)
        reduction = min(1.0, reduction + detection_prob * 0.3)

        return max(0.0, base_success * (1 - reduction))

    def _get_strategy_modifiers(
        self,
        strategy: AttackStrategy,
        base_profit: float,
        cost_model: CostModel,
    ) -> Tuple[float, float]:
        """Get profit modifier and extra cost for attack strategy.

        Args:
            strategy: Attack strategy
            base_profit: Base profit
            cost_model: Cost model

        Returns:
            Tuple of (profit_modifier, extra_cost)
        """
        if strategy == AttackStrategy.FLASHLOAN_EXPLOIT:
            # Flash loans amplify capital but cost fees
            return (2.0, cost_model.flashloan_fee_usd(base_profit * 10))

        elif strategy == AttackStrategy.MULTISTEP_EXPLOIT:
            # More complex, higher gas, moderate amplification
            return (1.5, cost_model.gas_cost_usd(1_000_000))

        elif strategy == AttackStrategy.SANDWICH_ATTACK:
            # Slippage affects profit
            slippage_cost = cost_model.slippage_cost_usd(base_profit * 2)
            return (0.8, slippage_cost)

        elif strategy == AttackStrategy.GOVERNANCE_EXPLOIT:
            # Slow but potentially high payoff
            return (3.0, 50_000)  # Token acquisition costs

        elif strategy == AttackStrategy.ORACLE_MANIPULATION:
            # Requires capital to manipulate
            return (2.0, cost_model.oracle_manipulation_cost_usd)

        else:  # DIRECT_EXPLOIT
            return (1.0, 0.0)

    def _compute_mev_extraction(
        self,
        mev_strategy: MEVStrategy,
        attacker_profit: float,
        success_prob: float,
    ) -> float:
        """Compute MEV extraction from attacker profit.

        Args:
            mev_strategy: MEV strategy
            attacker_profit: Attacker's expected profit
            success_prob: Attack success probability

        Returns:
            MEV extraction amount
        """
        if mev_strategy == MEVStrategy.ABSTAIN:
            return 0.0

        extraction_rates = {
            MEVStrategy.FRONTRUN: 0.2,
            MEVStrategy.BACKRUN: 0.1,
            MEVStrategy.SANDWICH: 0.35,
            MEVStrategy.COPY_ATTACK: 0.8,  # Copies most of the profit
            MEVStrategy.LIQUIDATE: 0.15,
            MEVStrategy.PROTECT: 0.0,  # Protection doesn't extract
        }

        rate = extraction_rates.get(mev_strategy, 0.1)
        return attacker_profit * success_prob * rate

    def _get_defense_cost(
        self,
        defense: ProtocolDefense,
        base_profit: float,
    ) -> float:
        """Get cost of implementing a defense.

        Args:
            defense: Defense strategy
            base_profit: Base profit (for relative cost estimation)

        Returns:
            Defense implementation cost
        """
        # Costs as fraction of potential loss
        cost_fractions = {
            ProtocolDefense.NO_DEFENSE: 0.0,
            ProtocolDefense.TIMELOCK: 0.01,
            ProtocolDefense.RATE_LIMIT: 0.02,
            ProtocolDefense.PAUSE_MECHANISM: 0.03,
            ProtocolDefense.REENTRANCY_GUARD: 0.01,
            ProtocolDefense.ACCESS_CONTROL: 0.02,
            ProtocolDefense.ORACLE_VALIDATION: 0.02,
            ProtocolDefense.MEV_PROTECTION: 0.05,
            ProtocolDefense.MONITORING: 0.1,  # Ongoing cost
        }

        fraction = cost_fractions.get(defense, 0.01)
        return base_profit * fraction

    def _find_dominant_strategies(
        self,
        payoff_tensor: NDArray[np.float64],
        attacker_strategies: List[AttackStrategy],
        protocol_strategies: List[ProtocolDefense],
        mev_strategies: List[MEVStrategy],
    ) -> Dict[str, str]:
        """Find dominant strategies for each player.

        Uses maxmin strategy: maximize worst-case payoff.

        Args:
            payoff_tensor: 4D payoff tensor
            attacker_strategies: Attack strategies
            protocol_strategies: Defense strategies
            mev_strategies: MEV strategies

        Returns:
            Dict mapping player name to dominant strategy
        """
        # Attacker's maxmin (maximize minimum payoff over opponent strategies)
        attacker_mins = np.min(payoff_tensor[:, :, :, 0], axis=(1, 2))
        best_attacker_idx = int(np.argmax(attacker_mins))
        attacker_dominant = attacker_strategies[best_attacker_idx]

        # Protocol's maxmin
        protocol_mins = np.min(payoff_tensor[:, :, :, 1], axis=(0, 2))
        best_protocol_idx = int(np.argmax(protocol_mins))
        protocol_dominant = protocol_strategies[best_protocol_idx]

        # MEV's maxmin
        mev_mins = np.min(payoff_tensor[:, :, :, 2], axis=(0, 1))
        best_mev_idx = int(np.argmax(mev_mins))
        mev_dominant = mev_strategies[best_mev_idx]

        return {
            PayoffPlayer.ATTACKER.value: attacker_dominant.value,
            PayoffPlayer.PROTOCOL.value: protocol_dominant.value,
            PayoffPlayer.MEV_SEARCHER.value: mev_dominant.value,
        }

    def _compute_equilibrium_ev(
        self,
        payoff_tensor: NDArray[np.float64],
        attacker_strategies: List[AttackStrategy],
        protocol_strategies: List[ProtocolDefense],
        mev_strategies: List[MEVStrategy],
        dominant_strategies: Dict[str, str],
    ) -> float:
        """Compute attacker's expected value at dominant strategy profile.

        Args:
            payoff_tensor: 4D payoff tensor
            attacker_strategies: Attack strategies
            protocol_strategies: Defense strategies
            mev_strategies: MEV strategies
            dominant_strategies: Dominant strategies for each player

        Returns:
            Attacker's expected value at equilibrium
        """
        a_strat = AttackStrategy(dominant_strategies[PayoffPlayer.ATTACKER.value])
        p_strat = ProtocolDefense(dominant_strategies[PayoffPlayer.PROTOCOL.value])
        m_strat = MEVStrategy(dominant_strategies[PayoffPlayer.MEV_SEARCHER.value])

        a_idx = attacker_strategies.index(a_strat)
        p_idx = protocol_strategies.index(p_strat)
        m_idx = mev_strategies.index(m_strat)

        return float(payoff_tensor[a_idx, p_idx, m_idx, 0])

    def _infer_scenario(self, vulnerability: Dict[str, Any]) -> str:
        """Infer scenario name from vulnerability data.

        Args:
            vulnerability: Vulnerability data

        Returns:
            Scenario name string
        """
        pattern_id = vulnerability.get("pattern_id", "")
        if pattern_id:
            return pattern_id.replace("-", "_").lower()

        severity = vulnerability.get("severity", "unknown")
        return f"{severity}_vulnerability"


# =============================================================================
# Convenience Functions
# =============================================================================


def compute_attack_ev(
    vulnerability: Dict[str, Any],
    protocol_state: Optional[Dict[str, Any]] = None,
    gas_price_gwei: Optional[float] = None,
    tvl_usd: Optional[float] = None,
) -> AttackPayoffMatrix:
    """Convenience function to compute attack EV for a vulnerability.

    Per 05.11-06: Wraps AttackSynthesisEngine.compute_attack_ev().

    Args:
        vulnerability: Vulnerability data dict
        protocol_state: Optional protocol context
        gas_price_gwei: Override gas price
        tvl_usd: Override TVL

    Returns:
        AttackPayoffMatrix with 3-player game model

    Usage:
        matrix = compute_attack_ev(
            vulnerability={"id": "vuln-1", "severity": "high"},
            protocol_state={"tvl_usd": 10_000_000},
        )
        print(f"Attack dominant: {matrix.is_attack_dominant()}")
    """
    engine = AttackSynthesisEngine()
    return engine.compute_attack_ev(
        vulnerability=vulnerability,
        protocol_state=protocol_state,
        gas_price_gwei=gas_price_gwei,
        tvl_usd=tvl_usd,
    )


# =============================================================================
# Module Exports
# =============================================================================


__all__ = [
    "AttackStrategy",
    "ProtocolDefense",
    "MEVStrategy",
    "CostModel",
    "AttackPayoffMatrix",
    "AttackSynthesisEngine",
    "compute_attack_ev",
]
