"""Causal loss amplification analysis for exploitation chains.

Per 05.11-CONTEXT.md: Analyze AMPLIFIES edges (flash loans, leverage, etc.)
to compute loss amplification factors from causal chains.

Key features:
- CausalAnalyzer: Compute loss amplification from causal chains
- LossAmplificationFactor: Result with base/amplified loss and sources
- trace_loss_path: Root cause -> loss attribution

Usage:
    from alphaswarm_sol.economics.causal_analysis import (
        CausalAnalyzer,
        LossAmplificationFactor,
        compute_loss_amplification,
    )

    analyzer = CausalAnalyzer()

    # Compute amplification for a causal chain
    factor = analyzer.compute_loss_amplification(causal_chain)
    print(f"Amplification: {factor.amplification_multiplier:.1f}x")
    print(f"Sources: {factor.amplification_sources}")

    # Trace loss path from root cause
    path = analyzer.trace_loss_path(causal_chain)
    print(f"Root cause: {path.root_cause_id}")
    print(f"Final loss attribution: {path.attribution}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.context.linker import CausalChainLink
    from alphaswarm_sol.context.types import CausalEdge


class AmplificationType(Enum):
    """Types of loss amplification in DeFi exploits.

    Per 05.11-CONTEXT.md: AMPLIFIES edges represent ways that initial
    losses can be magnified through DeFi mechanics.
    """

    FLASH_LOAN = "flash_loan"  # Capital-free attack, 100x+ amplification
    LEVERAGE = "leverage"  # Borrowed funds multiply exposure, 10x typical
    CASCADING_LIQUIDATION = "cascading_liquidation"  # Liquidation triggers more liquidations
    ORACLE_MANIPULATION = "oracle_manipulation"  # Price manipulation affects multiple protocols
    GOVERNANCE_CAPTURE = "governance_capture"  # Control over protocol parameters
    TOKEN_MINT = "token_mint"  # Unbounded token minting
    REENTRANCY = "reentrancy"  # Multiple extraction in single tx
    POOL_DRAIN = "pool_drain"  # Complete pool extraction
    BRIDGE_EXPLOIT = "bridge_exploit"  # Cross-chain loss multiplication
    MEV_SANDWICH = "mev_sandwich"  # MEV extraction from victims

    @classmethod
    def from_string(cls, value: str) -> "AmplificationType":
        """Create AmplificationType from string, case-insensitive."""
        normalized = value.lower().strip().replace("-", "_").replace(" ", "_")
        try:
            return cls(normalized)
        except ValueError:
            # Default to leverage for unknown types
            return cls.LEVERAGE


# Default amplification multipliers by type
AMPLIFICATION_MULTIPLIERS = {
    AmplificationType.FLASH_LOAN: 100.0,
    AmplificationType.LEVERAGE: 10.0,
    AmplificationType.CASCADING_LIQUIDATION: 5.0,
    AmplificationType.ORACLE_MANIPULATION: 20.0,
    AmplificationType.GOVERNANCE_CAPTURE: 50.0,
    AmplificationType.TOKEN_MINT: 1000.0,
    AmplificationType.REENTRANCY: 10.0,
    AmplificationType.POOL_DRAIN: 1.0,  # Full extraction, no multiplier
    AmplificationType.BRIDGE_EXPLOIT: 100.0,
    AmplificationType.MEV_SANDWICH: 2.0,
}


@dataclass
class AmplificationSource:
    """A source of loss amplification in a causal chain.

    Attributes:
        amplification_type: Type of amplification
        multiplier: Amplification multiplier (e.g., 100x for flash loans)
        description: Human-readable description
        edge_id: ID of the causal edge that represents this amplification
        confidence: Confidence in this amplification factor (0-1)
    """

    amplification_type: AmplificationType
    multiplier: float
    description: str = ""
    edge_id: str = ""
    confidence: float = 0.5

    def __post_init__(self) -> None:
        """Validate confidence range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "amplification_type": self.amplification_type.value,
            "multiplier": round(self.multiplier, 2),
            "description": self.description,
            "edge_id": self.edge_id,
            "confidence": round(self.confidence, 2),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AmplificationSource":
        """Create AmplificationSource from dictionary."""
        amp_type = data.get("amplification_type", "leverage")
        if isinstance(amp_type, str):
            amp_type = AmplificationType.from_string(amp_type)

        return cls(
            amplification_type=amp_type,
            multiplier=float(data.get("multiplier", 1.0)),
            description=str(data.get("description", "")),
            edge_id=str(data.get("edge_id", "")),
            confidence=float(data.get("confidence", 0.5)),
        )


@dataclass
class LossAmplificationFactor:
    """Result of causal loss amplification analysis.

    Per 05.11-CONTEXT.md: Represents the loss amplification from a causal chain,
    with base loss, amplified loss, and sources of amplification.

    Attributes:
        base_loss: Initial loss before amplification (USD)
        amplified_loss: Loss after applying amplification (USD)
        amplification_multiplier: Combined multiplier from all sources
        amplification_sources: List of amplification sources
        confidence: Overall confidence in amplification estimate (0-1)
        evidence_refs: Evidence supporting this analysis
        notes: Additional analysis notes
    """

    base_loss: float
    amplified_loss: float
    amplification_multiplier: float
    amplification_sources: List[AmplificationSource] = field(default_factory=list)
    confidence: float = 0.5
    evidence_refs: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate confidence range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")

    @property
    def has_flash_loan(self) -> bool:
        """Whether amplification includes flash loan."""
        return any(
            s.amplification_type == AmplificationType.FLASH_LOAN
            for s in self.amplification_sources
        )

    @property
    def has_leverage(self) -> bool:
        """Whether amplification includes leverage."""
        return any(
            s.amplification_type == AmplificationType.LEVERAGE
            for s in self.amplification_sources
        )

    @property
    def is_high_amplification(self) -> bool:
        """Whether this is high amplification (>= 10x)."""
        return self.amplification_multiplier >= 10.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "base_loss": round(self.base_loss, 2),
            "amplified_loss": round(self.amplified_loss, 2),
            "amplification_multiplier": round(self.amplification_multiplier, 2),
            "amplification_sources": [s.to_dict() for s in self.amplification_sources],
            "confidence": round(self.confidence, 2),
            "evidence_refs": self.evidence_refs,
            "notes": self.notes,
            "has_flash_loan": self.has_flash_loan,
            "has_leverage": self.has_leverage,
            "is_high_amplification": self.is_high_amplification,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LossAmplificationFactor":
        """Create LossAmplificationFactor from dictionary."""
        return cls(
            base_loss=float(data.get("base_loss", 0)),
            amplified_loss=float(data.get("amplified_loss", 0)),
            amplification_multiplier=float(data.get("amplification_multiplier", 1.0)),
            amplification_sources=[
                AmplificationSource.from_dict(s)
                for s in data.get("amplification_sources", [])
            ],
            confidence=float(data.get("confidence", 0.5)),
            evidence_refs=list(data.get("evidence_refs", [])),
            notes=list(data.get("notes", [])),
        )


@dataclass
class LossPath:
    """Traced loss path from root cause to final loss.

    Represents the path through a causal chain that leads from the
    initial vulnerability to the final financial loss.

    Attributes:
        root_cause_id: Starting vulnerability/condition
        loss_node_id: Final loss outcome node
        path_steps: Ordered list of step IDs in the path
        attribution: How loss is attributed (percentage per step)
        total_loss_usd: Total expected loss in USD
        probability: Probability of this path being taken (0-1)
    """

    root_cause_id: str
    loss_node_id: str
    path_steps: List[str] = field(default_factory=list)
    attribution: Dict[str, float] = field(default_factory=dict)
    total_loss_usd: float = 0.0
    probability: float = 0.5

    def __post_init__(self) -> None:
        """Validate probability range."""
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError(f"probability must be 0.0-1.0, got {self.probability}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "root_cause_id": self.root_cause_id,
            "loss_node_id": self.loss_node_id,
            "path_steps": self.path_steps,
            "attribution": self.attribution,
            "total_loss_usd": round(self.total_loss_usd, 2),
            "probability": round(self.probability, 2),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LossPath":
        """Create LossPath from dictionary."""
        return cls(
            root_cause_id=str(data.get("root_cause_id", "")),
            loss_node_id=str(data.get("loss_node_id", "")),
            path_steps=list(data.get("path_steps", [])),
            attribution=dict(data.get("attribution", {})),
            total_loss_usd=float(data.get("total_loss_usd", 0)),
            probability=float(data.get("probability", 0.5)),
        )


class CausalAnalyzer:
    """Analyzer for causal loss amplification in exploitation chains.

    Per 05.11-CONTEXT.md: Analyzes AMPLIFIES edges to compute how initial
    losses can be magnified through DeFi mechanics like flash loans,
    leverage, cascading liquidations, etc.

    Usage:
        analyzer = CausalAnalyzer()

        # Compute amplification for a causal chain
        factor = analyzer.compute_loss_amplification(chain)

        # Trace loss path
        path = analyzer.trace_loss_path(chain)
    """

    def __init__(
        self,
        causal_edges: Optional[List["CausalEdge"]] = None,
        amplification_multipliers: Optional[Dict[AmplificationType, float]] = None,
    ) -> None:
        """Initialize the causal analyzer.

        Args:
            causal_edges: Optional list of causal edges for analysis
            amplification_multipliers: Optional custom multipliers by type
        """
        self._causal_edges = causal_edges or []
        self._multipliers = amplification_multipliers or AMPLIFICATION_MULTIPLIERS.copy()

    def compute_loss_amplification(
        self,
        causal_chain: "CausalChainLink",
        base_loss_usd: float = 100000.0,
    ) -> LossAmplificationFactor:
        """Compute loss amplification factor from a causal chain.

        Per 05.11-CONTEXT.md: Analyzes AMPLIFIES edges in the chain and
        computes the total loss amplification multiplier.

        Args:
            causal_chain: CausalChainLink to analyze
            base_loss_usd: Base loss amount in USD for calculation

        Returns:
            LossAmplificationFactor with full analysis
        """
        amplification_sources: List[AmplificationSource] = []
        total_multiplier = 1.0
        notes: List[str] = []
        evidence_refs: List[str] = list(causal_chain.evidence_refs)

        # Analyze each step in the chain for AMPLIFIES edges
        for step_id in causal_chain.exploit_steps:
            # Check if this step has associated amplification
            amp_type, amp_mult = self._detect_amplification_type(step_id)

            if amp_type and amp_mult > 1.0:
                source = AmplificationSource(
                    amplification_type=amp_type,
                    multiplier=amp_mult,
                    description=f"Amplification via {amp_type.value} at step {step_id}",
                    edge_id=step_id,
                    confidence=causal_chain.probability_chain,
                )
                amplification_sources.append(source)
                notes.append(f"Detected {amp_type.value}: {amp_mult:.1f}x amplification")

        # Combine multipliers (additive, not multiplicative, to avoid explosion)
        # Use max multiplier + partial contribution from others
        if amplification_sources:
            sorted_sources = sorted(amplification_sources, key=lambda s: s.multiplier, reverse=True)
            total_multiplier = sorted_sources[0].multiplier
            for source in sorted_sources[1:]:
                # Add 10% of each additional source
                total_multiplier += (source.multiplier - 1.0) * 0.1

        # Apply chain probability to reduce confidence
        confidence = causal_chain.probability_chain * 0.8  # Slight discount

        amplified_loss = base_loss_usd * total_multiplier

        return LossAmplificationFactor(
            base_loss=base_loss_usd,
            amplified_loss=amplified_loss,
            amplification_multiplier=total_multiplier,
            amplification_sources=amplification_sources,
            confidence=confidence,
            evidence_refs=evidence_refs,
            notes=notes,
        )

    def _detect_amplification_type(
        self,
        step_id: str,
    ) -> tuple[Optional[AmplificationType], float]:
        """Detect amplification type from a step ID.

        Args:
            step_id: Step identifier to analyze

        Returns:
            Tuple of (AmplificationType or None, multiplier)
        """
        step_lower = step_id.lower()

        # Check for flash loan indicators
        if any(kw in step_lower for kw in ["flash", "flashloan", "flash_loan"]):
            return AmplificationType.FLASH_LOAN, self._multipliers[AmplificationType.FLASH_LOAN]

        # Check for leverage indicators
        if any(kw in step_lower for kw in ["leverage", "borrow", "margin"]):
            return AmplificationType.LEVERAGE, self._multipliers[AmplificationType.LEVERAGE]

        # Check for liquidation cascade
        if any(kw in step_lower for kw in ["liquidat", "cascade", "liquidation"]):
            return AmplificationType.CASCADING_LIQUIDATION, self._multipliers[AmplificationType.CASCADING_LIQUIDATION]

        # Check for oracle manipulation
        if any(kw in step_lower for kw in ["oracle", "price_manip", "twap"]):
            return AmplificationType.ORACLE_MANIPULATION, self._multipliers[AmplificationType.ORACLE_MANIPULATION]

        # Check for governance capture
        if any(kw in step_lower for kw in ["governance", "capture", "proposal"]):
            return AmplificationType.GOVERNANCE_CAPTURE, self._multipliers[AmplificationType.GOVERNANCE_CAPTURE]

        # Check for token minting
        if any(kw in step_lower for kw in ["mint", "inflate", "token_mint"]):
            return AmplificationType.TOKEN_MINT, self._multipliers[AmplificationType.TOKEN_MINT]

        # Check for reentrancy
        if any(kw in step_lower for kw in ["reentran", "reentrancy", "callback"]):
            return AmplificationType.REENTRANCY, self._multipliers[AmplificationType.REENTRANCY]

        # Check for pool drain
        if any(kw in step_lower for kw in ["drain", "empty", "pool_drain"]):
            return AmplificationType.POOL_DRAIN, self._multipliers[AmplificationType.POOL_DRAIN]

        # Check for bridge exploit
        if any(kw in step_lower for kw in ["bridge", "cross_chain", "crosschain"]):
            return AmplificationType.BRIDGE_EXPLOIT, self._multipliers[AmplificationType.BRIDGE_EXPLOIT]

        # Check for MEV sandwich
        if any(kw in step_lower for kw in ["mev", "sandwich", "frontrun"]):
            return AmplificationType.MEV_SANDWICH, self._multipliers[AmplificationType.MEV_SANDWICH]

        return None, 1.0

    def trace_loss_path(
        self,
        causal_chain: "CausalChainLink",
        total_loss_usd: float = 100000.0,
    ) -> LossPath:
        """Trace loss path from root cause to final loss.

        Args:
            causal_chain: CausalChainLink to trace
            total_loss_usd: Total loss amount for attribution

        Returns:
            LossPath with attribution
        """
        # Build attribution based on step count (equal distribution)
        step_count = len(causal_chain.exploit_steps)
        if step_count == 0:
            attribution = {causal_chain.root_cause_id: 1.0}
        else:
            attribution = {step_id: 1.0 / step_count for step_id in causal_chain.exploit_steps}

        return LossPath(
            root_cause_id=causal_chain.root_cause_id,
            loss_node_id=causal_chain.financial_loss_id,
            path_steps=causal_chain.exploit_steps,
            attribution=attribution,
            total_loss_usd=total_loss_usd,
            probability=causal_chain.probability_chain,
        )

    def add_causal_edge(self, edge: "CausalEdge") -> None:
        """Add a causal edge for analysis."""
        self._causal_edges.append(edge)

    def set_multiplier(self, amp_type: AmplificationType, multiplier: float) -> None:
        """Set custom multiplier for an amplification type."""
        self._multipliers[amp_type] = multiplier


def compute_loss_amplification(
    causal_chain: "CausalChainLink",
    base_loss_usd: float = 100000.0,
    causal_edges: Optional[List["CausalEdge"]] = None,
) -> LossAmplificationFactor:
    """Convenience function to compute loss amplification.

    Args:
        causal_chain: CausalChainLink to analyze
        base_loss_usd: Base loss amount in USD
        causal_edges: Optional list of causal edges

    Returns:
        LossAmplificationFactor with full analysis
    """
    analyzer = CausalAnalyzer(causal_edges=causal_edges)
    return analyzer.compute_loss_amplification(causal_chain, base_loss_usd)


# Export all types
__all__ = [
    "AmplificationType",
    "AMPLIFICATION_MULTIPLIERS",
    "AmplificationSource",
    "LossAmplificationFactor",
    "LossPath",
    "CausalAnalyzer",
    "compute_loss_amplification",
]
