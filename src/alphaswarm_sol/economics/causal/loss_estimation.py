"""Loss estimation with amplification factors for causal exploitation graphs.

Per 05.11-07-PLAN.md: Loss estimation methodology that accounts for:
- TVL exposure
- Rate limits and caps
- Cooldowns
- Amplification factors from AMPLIFIES edges

Key features:
- LossEstimator: Estimate loss from causal paths
- LossEstimate: Result with base loss, amplified loss, and breakdown
- ProtocolState: Protocol-specific state for loss calculation

Usage:
    from alphaswarm_sol.economics.causal.loss_estimation import (
        LossEstimator,
        LossEstimate,
        ProtocolState,
    )

    # Create protocol state
    state = ProtocolState(
        tvl_usd=10_000_000,
        rate_limit_per_tx=1_000_000,
        cooldown_seconds=3600,
    )

    # Estimate loss for a causal path
    estimator = LossEstimator()
    estimate = estimator.estimate_loss(path, state)

    print(f"Base loss: ${estimate.base_loss_usd:,.2f}")
    print(f"Amplified loss: ${estimate.amplified_loss_usd:,.2f}")
    print(f"Amplification: {estimate.amplification_factor:.1f}x")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from alphaswarm_sol.context.types import Confidence

if TYPE_CHECKING:
    from .exploitation_graph import CausalPath, CEGEdge


class AmplifierCategory(Enum):
    """Categories of loss amplification.

    Per 05.11-07-PLAN.md: AMPLIFIES edges represent mechanisms
    that multiply the base loss.
    """

    FLASH_LOAN = "flash_loan"  # Capital-free attack, 100x typical
    LEVERAGE = "leverage"  # Borrowed funds, 10x typical
    LIQUIDITY_DEPTH = "liquidity_depth"  # Deep liquidity extraction
    CASCADING_LIQUIDATION = "cascading_liquidation"  # Liquidation triggers more
    ORACLE_MANIPULATION = "oracle_manipulation"  # Price manipulation
    GOVERNANCE_CAPTURE = "governance_capture"  # Control parameters
    REENTRANCY = "reentrancy"  # Multiple extraction per tx
    CROSS_CHAIN = "cross_chain"  # Bridge-based amplification

    @classmethod
    def from_string(cls, value: str) -> "AmplifierCategory":
        """Create AmplifierCategory from string."""
        normalized = value.lower().strip().replace("-", "_").replace(" ", "_")
        try:
            return cls(normalized)
        except ValueError:
            return cls.LEVERAGE

    @property
    def default_multiplier(self) -> float:
        """Default amplification multiplier for this category."""
        multipliers = {
            AmplifierCategory.FLASH_LOAN: 100.0,
            AmplifierCategory.LEVERAGE: 10.0,
            AmplifierCategory.LIQUIDITY_DEPTH: 5.0,
            AmplifierCategory.CASCADING_LIQUIDATION: 5.0,
            AmplifierCategory.ORACLE_MANIPULATION: 20.0,
            AmplifierCategory.GOVERNANCE_CAPTURE: 50.0,
            AmplifierCategory.REENTRANCY: 10.0,
            AmplifierCategory.CROSS_CHAIN: 100.0,
        }
        return multipliers.get(self, 1.0)


@dataclass
class ProtocolState:
    """Protocol state for loss estimation.

    Captures protocol-specific values that affect loss calculation.

    Attributes:
        tvl_usd: Total value locked in USD
        rate_limit_per_tx: Maximum value per transaction (USD)
        cooldown_seconds: Cooldown between operations
        max_slippage: Maximum slippage tolerance (0-1)
        gas_price_gwei: Current gas price
        block_time_seconds: Average block time
        flash_loan_fee: Flash loan fee percentage (0-1)
        governance_timelock_seconds: Governance timelock duration
        oracle_update_frequency: Oracle update frequency in seconds
    """

    tvl_usd: float = 10_000_000.0
    rate_limit_per_tx: float = 0.0  # 0 = no limit
    cooldown_seconds: int = 0  # 0 = no cooldown
    max_slippage: float = 0.01  # 1%
    gas_price_gwei: float = 50.0
    block_time_seconds: float = 12.0
    flash_loan_fee: float = 0.0009  # 0.09%
    governance_timelock_seconds: int = 172800  # 2 days
    oracle_update_frequency: int = 3600  # 1 hour

    def __post_init__(self) -> None:
        """Validate ranges."""
        if self.tvl_usd < 0:
            raise ValueError(f"tvl_usd must be >= 0, got {self.tvl_usd}")
        if self.max_slippage < 0 or self.max_slippage > 1:
            raise ValueError(f"max_slippage must be 0-1, got {self.max_slippage}")

    @property
    def has_rate_limit(self) -> bool:
        """Whether protocol has rate limiting."""
        return self.rate_limit_per_tx > 0

    @property
    def has_cooldown(self) -> bool:
        """Whether protocol has cooldown."""
        return self.cooldown_seconds > 0

    @property
    def max_extractable_per_tx(self) -> float:
        """Maximum value extractable in a single transaction."""
        if self.has_rate_limit:
            return min(self.rate_limit_per_tx, self.tvl_usd)
        return self.tvl_usd

    @property
    def txs_to_drain(self) -> int:
        """Minimum transactions needed to drain TVL."""
        if not self.has_rate_limit:
            return 1
        if self.rate_limit_per_tx <= 0:
            return 1
        return max(1, int(self.tvl_usd / self.rate_limit_per_tx))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tvl_usd": round(self.tvl_usd, 2),
            "rate_limit_per_tx": round(self.rate_limit_per_tx, 2),
            "cooldown_seconds": self.cooldown_seconds,
            "max_slippage": round(self.max_slippage, 4),
            "gas_price_gwei": round(self.gas_price_gwei, 2),
            "block_time_seconds": round(self.block_time_seconds, 2),
            "flash_loan_fee": round(self.flash_loan_fee, 4),
            "governance_timelock_seconds": self.governance_timelock_seconds,
            "oracle_update_frequency": self.oracle_update_frequency,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProtocolState":
        """Create ProtocolState from dictionary."""
        return cls(
            tvl_usd=float(data.get("tvl_usd", 10_000_000)),
            rate_limit_per_tx=float(data.get("rate_limit_per_tx", 0)),
            cooldown_seconds=int(data.get("cooldown_seconds", 0)),
            max_slippage=float(data.get("max_slippage", 0.01)),
            gas_price_gwei=float(data.get("gas_price_gwei", 50)),
            block_time_seconds=float(data.get("block_time_seconds", 12)),
            flash_loan_fee=float(data.get("flash_loan_fee", 0.0009)),
            governance_timelock_seconds=int(data.get("governance_timelock_seconds", 172800)),
            oracle_update_frequency=int(data.get("oracle_update_frequency", 3600)),
        )


@dataclass
class AmplificationBreakdown:
    """Breakdown of amplification factors.

    Attributes:
        category: Amplification category
        multiplier: Applied multiplier
        source_node: Node that provides amplification
        confidence: Confidence in this factor
        description: Human-readable description
    """

    category: AmplifierCategory
    multiplier: float
    source_node: str = ""
    confidence: Confidence = Confidence.INFERRED
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category.value,
            "multiplier": round(self.multiplier, 2),
            "source_node": self.source_node,
            "confidence": self.confidence.value,
            "description": self.description,
        }


@dataclass
class LossEstimate:
    """Estimated loss from a causal exploitation path.

    Per 05.11-07-PLAN.md: Loss estimate with base loss, amplified loss,
    and breakdown of amplification factors.

    Attributes:
        base_loss_usd: Initial loss before amplification
        amplified_loss_usd: Loss after applying amplification
        amplification_factor: Total amplification multiplier
        amplification_breakdown: Per-factor breakdown
        exposure_percentage: Percentage of TVL at risk (0-1)
        attack_cost_usd: Estimated attack cost
        net_profit_usd: Expected attacker profit
        confidence: Confidence in the estimate
        notes: Analysis notes
        evidence_refs: Supporting evidence
    """

    base_loss_usd: float
    amplified_loss_usd: float
    amplification_factor: float = 1.0
    amplification_breakdown: List[AmplificationBreakdown] = field(default_factory=list)
    exposure_percentage: float = 0.0
    attack_cost_usd: float = 0.0
    net_profit_usd: float = 0.0
    confidence: Confidence = Confidence.INFERRED
    notes: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Calculate derived values."""
        if self.net_profit_usd == 0 and self.amplified_loss_usd > 0:
            self.net_profit_usd = self.amplified_loss_usd - self.attack_cost_usd

    @property
    def is_profitable(self) -> bool:
        """Whether the attack is profitable."""
        return self.net_profit_usd > 0

    @property
    def has_amplification(self) -> bool:
        """Whether amplification was applied."""
        return self.amplification_factor > 1.0

    @property
    def roi_percentage(self) -> float:
        """Return on investment for attacker (0-1+)."""
        if self.attack_cost_usd <= 0:
            return float('inf') if self.net_profit_usd > 0 else 0
        return self.net_profit_usd / self.attack_cost_usd

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "base_loss_usd": round(self.base_loss_usd, 2),
            "amplified_loss_usd": round(self.amplified_loss_usd, 2),
            "amplification_factor": round(self.amplification_factor, 2),
            "amplification_breakdown": [b.to_dict() for b in self.amplification_breakdown],
            "exposure_percentage": round(self.exposure_percentage, 4),
            "attack_cost_usd": round(self.attack_cost_usd, 2),
            "net_profit_usd": round(self.net_profit_usd, 2),
            "is_profitable": self.is_profitable,
            "roi_percentage": round(self.roi_percentage, 2) if self.roi_percentage != float('inf') else "inf",
            "confidence": self.confidence.value,
            "notes": self.notes,
            "evidence_refs": self.evidence_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LossEstimate":
        """Create LossEstimate from dictionary."""
        confidence = data.get("confidence", "inferred")
        if isinstance(confidence, str):
            confidence = Confidence.from_string(confidence)

        return cls(
            base_loss_usd=float(data.get("base_loss_usd", 0)),
            amplified_loss_usd=float(data.get("amplified_loss_usd", 0)),
            amplification_factor=float(data.get("amplification_factor", 1.0)),
            amplification_breakdown=[],  # Not deserialized in detail
            exposure_percentage=float(data.get("exposure_percentage", 0)),
            attack_cost_usd=float(data.get("attack_cost_usd", 0)),
            net_profit_usd=float(data.get("net_profit_usd", 0)),
            confidence=confidence,
            notes=list(data.get("notes", [])),
            evidence_refs=list(data.get("evidence_refs", [])),
        )


class LossEstimator:
    """Estimator for loss from causal exploitation paths.

    Per 05.11-07-PLAN.md: Estimates loss with:
    - TVL exposure consideration
    - Rate limit and cap handling
    - Cooldown accounting
    - Amplification factor application

    Usage:
        estimator = LossEstimator()

        # Basic estimation
        estimate = estimator.estimate_loss(path, protocol_state)

        # Counterfactual estimation
        cf_estimate = estimator.estimate_counterfactual_loss(
            path,
            protocol_state,
            counterfactual_query,
        )
    """

    def __init__(
        self,
        default_gas_cost_usd: float = 500.0,
        flash_loan_cost_multiplier: float = 0.001,
    ) -> None:
        """Initialize the loss estimator.

        Args:
            default_gas_cost_usd: Default gas cost for attacks
            flash_loan_cost_multiplier: Flash loan cost as percentage of borrowed
        """
        self._default_gas_cost = default_gas_cost_usd
        self._flash_loan_cost_mult = flash_loan_cost_multiplier

    def estimate_loss(
        self,
        path: "CausalPath",
        protocol_state: ProtocolState,
    ) -> LossEstimate:
        """Estimate loss from a causal exploitation path.

        Args:
            path: CausalPath to estimate loss for
            protocol_state: Protocol state for calculation

        Returns:
            LossEstimate with full analysis
        """
        # Calculate base loss from protocol state
        base_loss = self._calculate_base_loss(path, protocol_state)

        # Get amplification breakdown from path
        amplification_breakdown = self._extract_amplification(path)

        # Calculate total amplification factor
        amplification_factor = path.amplification_factor
        if amplification_breakdown:
            # Use max + partial contribution from others
            sorted_amp = sorted(amplification_breakdown, key=lambda b: b.multiplier, reverse=True)
            if sorted_amp:
                amplification_factor = sorted_amp[0].multiplier
                for breakdown in sorted_amp[1:]:
                    amplification_factor += (breakdown.multiplier - 1.0) * 0.1

        # Apply amplification
        amplified_loss = base_loss * amplification_factor

        # Cap at TVL
        amplified_loss = min(amplified_loss, protocol_state.tvl_usd)

        # Calculate attack cost
        attack_cost = self._calculate_attack_cost(path, protocol_state, amplification_breakdown)

        # Calculate exposure percentage
        exposure_percentage = amplified_loss / protocol_state.tvl_usd if protocol_state.tvl_usd > 0 else 0

        # Net profit
        net_profit = amplified_loss - attack_cost

        # Build notes
        notes = []
        if protocol_state.has_rate_limit:
            notes.append(f"Rate limit: ${protocol_state.rate_limit_per_tx:,.0f} per tx")
        if protocol_state.has_cooldown:
            notes.append(f"Cooldown: {protocol_state.cooldown_seconds}s between operations")
        if amplification_factor > 1:
            notes.append(f"Amplification: {amplification_factor:.1f}x from {len(amplification_breakdown)} source(s)")

        return LossEstimate(
            base_loss_usd=base_loss,
            amplified_loss_usd=amplified_loss,
            amplification_factor=amplification_factor,
            amplification_breakdown=amplification_breakdown,
            exposure_percentage=exposure_percentage,
            attack_cost_usd=attack_cost,
            net_profit_usd=net_profit,
            confidence=Confidence.INFERRED if path.is_high_probability else Confidence.UNKNOWN,
            notes=notes,
            evidence_refs=path.evidence_refs,
        )

    def estimate_counterfactual_loss(
        self,
        path: "CausalPath",
        protocol_state: ProtocolState,
        counterfactual_condition: str,
        loss_reduction_factor: float = 0.5,
    ) -> LossEstimate:
        """Estimate loss with a counterfactual condition applied.

        Args:
            path: CausalPath to estimate loss for
            protocol_state: Protocol state for calculation
            counterfactual_condition: What-if condition
            loss_reduction_factor: Reduction in loss from counterfactual (0-1)

        Returns:
            LossEstimate with counterfactual applied
        """
        # Get base estimate
        base_estimate = self.estimate_loss(path, protocol_state)

        # Apply counterfactual reduction
        reduced_amplified_loss = base_estimate.amplified_loss_usd * (1.0 - loss_reduction_factor)

        return LossEstimate(
            base_loss_usd=base_estimate.base_loss_usd,
            amplified_loss_usd=reduced_amplified_loss,
            amplification_factor=base_estimate.amplification_factor * (1.0 - loss_reduction_factor),
            amplification_breakdown=base_estimate.amplification_breakdown,
            exposure_percentage=reduced_amplified_loss / protocol_state.tvl_usd if protocol_state.tvl_usd > 0 else 0,
            attack_cost_usd=base_estimate.attack_cost_usd,
            net_profit_usd=reduced_amplified_loss - base_estimate.attack_cost_usd,
            confidence=Confidence.INFERRED,
            notes=base_estimate.notes + [f"Counterfactual: {counterfactual_condition} reduces loss by {loss_reduction_factor:.0%}"],
            evidence_refs=base_estimate.evidence_refs,
        )

    def _calculate_base_loss(
        self,
        path: "CausalPath",
        protocol_state: ProtocolState,
    ) -> float:
        """Calculate base loss from path and protocol state.

        Args:
            path: CausalPath to analyze
            protocol_state: Protocol state

        Returns:
            Base loss in USD
        """
        # Base loss is proportional to path probability and TVL exposure
        base_exposure = protocol_state.max_extractable_per_tx
        probability_adjusted = base_exposure * path.cumulative_probability

        return probability_adjusted

    def _extract_amplification(
        self,
        path: "CausalPath",
    ) -> List[AmplificationBreakdown]:
        """Extract amplification factors from path.

        Args:
            path: CausalPath to analyze

        Returns:
            List of AmplificationBreakdown objects
        """
        breakdown: List[AmplificationBreakdown] = []

        # Check nodes for amplifier types
        for node in path.nodes:
            if node.is_amplifier:
                # Detect category from node name
                category = self._detect_amplifier_category(node.name)
                breakdown.append(AmplificationBreakdown(
                    category=category,
                    multiplier=category.default_multiplier,
                    source_node=node.id,
                    description=f"Amplification from {node.name}",
                ))

        # Check edges for AMPLIFIES type
        for edge in path.edges:
            if edge.is_amplifying:
                category = self._detect_amplifier_category(edge.target)
                breakdown.append(AmplificationBreakdown(
                    category=category,
                    multiplier=edge.amplification_factor,
                    source_node=edge.target,
                    description=edge.description or f"Amplification via {edge.target}",
                ))

        return breakdown

    def _detect_amplifier_category(
        self,
        identifier: str,
    ) -> AmplifierCategory:
        """Detect amplifier category from identifier.

        Args:
            identifier: Node/edge identifier

        Returns:
            AmplifierCategory
        """
        id_lower = identifier.lower()

        if any(kw in id_lower for kw in ["flash", "flashloan"]):
            return AmplifierCategory.FLASH_LOAN
        if any(kw in id_lower for kw in ["leverage", "borrow", "margin"]):
            return AmplifierCategory.LEVERAGE
        if any(kw in id_lower for kw in ["liquidat", "cascade"]):
            return AmplifierCategory.CASCADING_LIQUIDATION
        if any(kw in id_lower for kw in ["oracle", "price"]):
            return AmplifierCategory.ORACLE_MANIPULATION
        if any(kw in id_lower for kw in ["governance", "capture"]):
            return AmplifierCategory.GOVERNANCE_CAPTURE
        if any(kw in id_lower for kw in ["reentran", "callback"]):
            return AmplifierCategory.REENTRANCY
        if any(kw in id_lower for kw in ["bridge", "cross_chain"]):
            return AmplifierCategory.CROSS_CHAIN
        if any(kw in id_lower for kw in ["liquidity", "depth", "pool"]):
            return AmplifierCategory.LIQUIDITY_DEPTH

        return AmplifierCategory.LEVERAGE  # Default

    def _calculate_attack_cost(
        self,
        path: "CausalPath",
        protocol_state: ProtocolState,
        amplification: List[AmplificationBreakdown],
    ) -> float:
        """Calculate estimated attack cost.

        Args:
            path: CausalPath to analyze
            protocol_state: Protocol state
            amplification: Amplification breakdown

        Returns:
            Attack cost in USD
        """
        cost = self._default_gas_cost

        # Add flash loan cost if used
        for amp in amplification:
            if amp.category == AmplifierCategory.FLASH_LOAN:
                # Flash loan cost is percentage of borrowed amount
                flash_loan_amount = protocol_state.tvl_usd * 0.1  # Assume 10% of TVL borrowed
                cost += flash_loan_amount * protocol_state.flash_loan_fee

        # Add gas cost for multi-tx attacks
        if protocol_state.has_rate_limit:
            txs_needed = protocol_state.txs_to_drain
            cost += self._default_gas_cost * (txs_needed - 1)

        return cost


# Export all types
__all__ = [
    "AmplifierCategory",
    "ProtocolState",
    "AmplificationBreakdown",
    "LossEstimate",
    "LossEstimator",
]
