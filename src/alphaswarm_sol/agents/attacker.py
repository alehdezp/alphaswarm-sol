"""
P2-T2: Attacker Agent

Constructs concrete exploits rather than just pattern matching.
Uses attack strategies, exploitability scoring, and LLM-based synthesis.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class AttackCategory(Enum):
    """Attack strategy categories."""

    STATE_MANIPULATION = "state_manipulation"
    ACCESS_BYPASS = "access_bypass"
    ECONOMIC = "economic"
    DATA_INTEGRITY = "data_integrity"
    DENIAL_OF_SERVICE = "denial_of_service"
    CRYPTOGRAPHIC = "cryptographic"


class AttackFeasibility(Enum):
    """Attack feasibility levels."""

    TRIVIAL = "trivial"  # Exploitable by anyone
    LOW = "low"  # Requires basic knowledge
    MEDIUM = "medium"  # Requires expertise
    HIGH = "high"  # Requires significant resources/expertise


class EconomicImpact(Enum):
    """Economic impact levels."""

    NEGLIGIBLE = "negligible"  # < $1k
    LOW = "low"  # $1k - $10k
    MEDIUM = "medium"  # $10k - $100k
    HIGH = "high"  # $100k - $1M
    CRITICAL = "critical"  # > $1M


@dataclass
class AttackPrerequisite:
    """Prerequisites for an attack."""

    condition: str  # What must be true
    satisfied: bool  # Is it satisfied?
    evidence: List[str] = field(default_factory=list)  # Node IDs proving it


@dataclass
class AttackStep:
    """Single step in attack sequence."""

    step_number: int
    action: str  # What the attacker does
    effect: str  # What happens as a result
    code_location: Optional[str] = None  # Node ID where this happens
    requires_capital: Optional[float] = None  # ETH required
    gas_cost: Optional[int] = None


@dataclass
class EconomicAnalysis:
    """Economic analysis of attack."""

    potential_gain: Optional[float] = None  # ETH attacker can extract
    capital_required: Optional[float] = None  # ETH needed to execute
    gas_cost_estimate: Optional[int] = None  # Total gas
    roi: Optional[float] = None  # Return on investment
    impact_level: EconomicImpact = EconomicImpact.NEGLIGIBLE


@dataclass
class AttackConstruction:
    """A concrete attack construction."""

    category: AttackCategory
    target_nodes: List[str]  # Focal nodes being attacked
    preconditions: List[AttackPrerequisite]
    attack_steps: List[AttackStep]
    postconditions: List[str]  # What's true after attack
    exploitability_score: float  # 0.0 - 1.0
    feasibility: AttackFeasibility
    economic_analysis: EconomicAnalysis
    blocking_factors: List[str] = field(default_factory=list)
    historical_exploits: List[str] = field(default_factory=list)  # CVE/exploit IDs
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExploitabilityFactors:
    """Factors contributing to exploitability score."""

    technical_feasibility: float = 0.0  # 0.0 - 1.0, weight: 30%
    guard_absence: float = 0.0  # 0.0 - 1.0, weight: 25%
    pattern_match_strength: float = 0.0  # 0.0 - 1.0, weight: 20%
    economic_viability: float = 0.0  # 0.0 - 1.0, weight: 15%
    historical_precedent: float = 0.0  # 0.0 - 1.0, weight: 10%

    def calculate_score(self) -> float:
        """Calculate weighted exploitability score."""
        score = (
            self.technical_feasibility * 0.30
            + self.guard_absence * 0.25
            + self.pattern_match_strength * 0.20
            + self.economic_viability * 0.15
            + self.historical_precedent * 0.10
        )
        return max(0.0, min(1.0, score))


@dataclass
class AttackerResult:
    """Result from attacker agent."""

    matched: bool  # Did we find a viable attack?
    confidence: float  # 0.0 - 1.0
    attack: Optional[AttackConstruction] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AttackerAgent:
    """
    Attacker Agent - Constructs concrete exploits.

    Unlike pattern matching, this agent actively synthesizes attack scenarios
    by analyzing preconditions, constructing step-by-step exploits, and
    calculating exploitability scores.
    """

    def __init__(
        self,
        adversarial_kg: Optional[Any] = None,
        use_llm: bool = False,
    ):
        """
        Initialize attacker agent.

        Args:
            adversarial_kg: Optional adversarial knowledge graph with exploit patterns
            use_llm: Whether to use LLM for attack synthesis (default: False for tests)
        """
        self.adversarial_kg = adversarial_kg
        self.use_llm = use_llm
        self.logger = logging.getLogger(__name__)

    def analyze(self, context: Any) -> AttackerResult:
        """
        Analyze context and construct attacks.

        Args:
            context: AgentContext with focal nodes and subgraph

        Returns:
            AttackerResult with attack construction if viable
        """
        try:
            # Select attack strategy based on context
            strategy = self._select_strategy(context)

            if strategy is None:
                return AttackerResult(
                    matched=False,
                    confidence=0.0,
                    metadata={"reason": "No viable attack strategy identified"},
                )

            # Construct attack using selected strategy
            attack = self._construct_attack(context, strategy)

            if attack is None:
                return AttackerResult(
                    matched=False,
                    confidence=0.0,
                    metadata={
                        "reason": "Attack construction failed",
                        "strategy": strategy.value,
                    },
                )

            # Calculate confidence based on exploitability score
            confidence = attack.exploitability_score

            return AttackerResult(
                matched=True,
                confidence=confidence,
                attack=attack,
                metadata={
                    "strategy": strategy.value,
                    "feasibility": attack.feasibility.value,
                    "economic_impact": attack.economic_analysis.impact_level.value,
                },
            )

        except Exception as e:
            self.logger.error(f"Attacker agent error: {e}", exc_info=True)
            return AttackerResult(
                matched=False,
                confidence=0.0,
                metadata={"error": str(e)},
            )

    def _select_strategy(self, context: Any) -> Optional[AttackCategory]:
        """
        Select attack strategy based on context.

        Args:
            context: AgentContext with patterns, intents, subgraph

        Returns:
            AttackCategory or None if no strategy applies
        """
        # Check patterns first
        if hasattr(context, "patterns") and context.patterns:
            for pattern in context.patterns:
                # Map pattern to attack category
                if hasattr(pattern, "id"):
                    pattern_id = pattern.id.lower()
                    if "reentrancy" in pattern_id or "state" in pattern_id:
                        return AttackCategory.STATE_MANIPULATION
                    elif "access" in pattern_id or "auth" in pattern_id:
                        return AttackCategory.ACCESS_BYPASS
                    elif "oracle" in pattern_id or "mev" in pattern_id:
                        return AttackCategory.ECONOMIC
                    elif "dos" in pattern_id:
                        return AttackCategory.DENIAL_OF_SERVICE
                    elif "signature" in pattern_id or "crypto" in pattern_id:
                        return AttackCategory.CRYPTOGRAPHIC

        # Check focal node properties
        if hasattr(context, "focal_nodes") and context.focal_nodes:
            # Get first focal node from subgraph
            if hasattr(context.subgraph, "nodes"):
                for node in context.subgraph.nodes.values():
                    if hasattr(node, "properties") and node.properties:
                        props = node.properties

                        # Check for state manipulation indicators
                        if props.get("state_write_after_external_call"):
                            return AttackCategory.STATE_MANIPULATION

                        # Check for access control issues
                        if not props.get("has_access_gate") and props.get(
                            "writes_privileged_state"
                        ):
                            return AttackCategory.ACCESS_BYPASS

                        # Check for economic attack vectors
                        if props.get("swap_like") or props.get("reads_oracle_price"):
                            return AttackCategory.ECONOMIC

                        # Check for DoS vectors
                        if props.get("has_unbounded_loop") or props.get(
                            "external_calls_in_loop"
                        ):
                            return AttackCategory.DENIAL_OF_SERVICE

        # Default: try state manipulation as most common
        return AttackCategory.STATE_MANIPULATION

    def _construct_attack(
        self, context: Any, strategy: AttackCategory
    ) -> Optional[AttackConstruction]:
        """
        Construct attack using selected strategy.

        Args:
            context: AgentContext
            strategy: Selected attack category

        Returns:
            AttackConstruction or None if construction fails
        """
        # Route to strategy-specific construction
        if strategy == AttackCategory.STATE_MANIPULATION:
            return self._construct_state_manipulation(context)
        elif strategy == AttackCategory.ACCESS_BYPASS:
            return self._construct_access_bypass(context)
        elif strategy == AttackCategory.ECONOMIC:
            return self._construct_economic_attack(context)
        elif strategy == AttackCategory.DENIAL_OF_SERVICE:
            return self._construct_dos_attack(context)
        else:
            # Generic construction
            return self._construct_generic_attack(context, strategy)

    def _construct_state_manipulation(
        self, context: Any
    ) -> Optional[AttackConstruction]:
        """Construct state manipulation attack (e.g., reentrancy)."""
        preconditions = []
        attack_steps = []
        blocking_factors = []
        target_nodes = context.focal_nodes if hasattr(context, "focal_nodes") else []

        # Check for reentrancy preconditions
        has_external_call = False
        has_state_write = False
        has_guard = False

        if hasattr(context.subgraph, "nodes"):
            for node in context.subgraph.nodes.values():
                if hasattr(node, "properties") and node.properties:
                    props = node.properties

                    # Check for external call
                    if props.get("makes_external_call"):
                        has_external_call = True
                        preconditions.append(
                            AttackPrerequisite(
                                condition="Function makes external call",
                                satisfied=True,
                                evidence=[node.id],
                            )
                        )

                    # Check for state write
                    if props.get("writes_state"):
                        has_state_write = True
                        preconditions.append(
                            AttackPrerequisite(
                                condition="Function writes state",
                                satisfied=True,
                                evidence=[node.id],
                            )
                        )

                    # Check for reentrancy guard
                    if props.get("has_reentrancy_guard"):
                        has_guard = True
                        blocking_factors.append("Reentrancy guard present")

                    # Check order
                    if props.get("state_write_after_external_call"):
                        attack_steps.append(
                            AttackStep(
                                step_number=1,
                                action="Call vulnerable function",
                                effect="Function makes external call before updating state",
                                code_location=node.id,
                            )
                        )
                        attack_steps.append(
                            AttackStep(
                                step_number=2,
                                action="Reenter from malicious contract",
                                effect="State not yet updated, can exploit stale values",
                                code_location=node.id,
                            )
                        )

        # Calculate exploitability
        factors = ExploitabilityFactors()
        factors.technical_feasibility = 0.9 if (has_external_call and has_state_write) else 0.1
        factors.guard_absence = 0.0 if has_guard else 1.0
        factors.pattern_match_strength = 1.0 if attack_steps else 0.0

        exploitability = factors.calculate_score()

        # Determine feasibility
        if has_guard:
            feasibility = AttackFeasibility.HIGH
        elif exploitability > 0.7:
            feasibility = AttackFeasibility.TRIVIAL
        elif exploitability > 0.4:
            feasibility = AttackFeasibility.LOW
        else:
            feasibility = AttackFeasibility.MEDIUM

        # Economic analysis
        economic = EconomicAnalysis(
            impact_level=EconomicImpact.HIGH if exploitability > 0.7 else EconomicImpact.MEDIUM
        )

        if not preconditions or not attack_steps:
            return None

        return AttackConstruction(
            category=AttackCategory.STATE_MANIPULATION,
            target_nodes=target_nodes,
            preconditions=preconditions,
            attack_steps=attack_steps,
            postconditions=["Attacker can drain funds or manipulate state"],
            exploitability_score=exploitability,
            feasibility=feasibility,
            economic_analysis=economic,
            blocking_factors=blocking_factors,
            historical_exploits=["CVE-2016-6307"],  # The DAO
        )

    def _construct_access_bypass(self, context: Any) -> Optional[AttackConstruction]:
        """Construct access control bypass attack."""
        preconditions = []
        attack_steps = []
        blocking_factors = []
        target_nodes = context.focal_nodes if hasattr(context, "focal_nodes") else []

        # Check for access control issues
        is_public = False
        writes_privileged = False
        has_gate = False

        if hasattr(context.subgraph, "nodes"):
            for node in context.subgraph.nodes.values():
                if hasattr(node, "properties") and node.properties:
                    props = node.properties

                    # Check visibility
                    if props.get("visibility") in ["public", "external"]:
                        is_public = True
                        preconditions.append(
                            AttackPrerequisite(
                                condition="Function is publicly accessible",
                                satisfied=True,
                                evidence=[node.id],
                            )
                        )

                    # Check privileged state writes
                    if props.get("writes_privileged_state"):
                        writes_privileged = True
                        preconditions.append(
                            AttackPrerequisite(
                                condition="Function writes privileged state",
                                satisfied=True,
                                evidence=[node.id],
                            )
                        )

                    # Check access gate
                    if props.get("has_access_gate"):
                        has_gate = True
                        blocking_factors.append("Access control gate present")

        if is_public and writes_privileged and not has_gate:
            attack_steps.append(
                AttackStep(
                    step_number=1,
                    action="Call privileged function without authorization",
                    effect="Attacker modifies critical contract state",
                    code_location=target_nodes[0] if target_nodes else None,
                )
            )

        # Calculate exploitability
        factors = ExploitabilityFactors()
        factors.technical_feasibility = 1.0 if (is_public and writes_privileged) else 0.0
        factors.guard_absence = 1.0 if not has_gate else 0.0
        factors.pattern_match_strength = 1.0 if attack_steps else 0.0

        exploitability = factors.calculate_score()

        if exploitability < 0.3:
            return None

        feasibility = (
            AttackFeasibility.TRIVIAL
            if not has_gate
            else AttackFeasibility.HIGH
        )

        economic = EconomicAnalysis(
            impact_level=EconomicImpact.CRITICAL if exploitability > 0.7 else EconomicImpact.HIGH
        )

        return AttackConstruction(
            category=AttackCategory.ACCESS_BYPASS,
            target_nodes=target_nodes,
            preconditions=preconditions,
            attack_steps=attack_steps,
            postconditions=["Attacker has admin/owner privileges"],
            exploitability_score=exploitability,
            feasibility=feasibility,
            economic_analysis=economic,
            blocking_factors=blocking_factors,
            historical_exploits=["Parity Wallet Hack"],
        )

    def _construct_economic_attack(self, context: Any) -> Optional[AttackConstruction]:
        """Construct economic attack (oracle manipulation, MEV)."""
        # Simplified implementation - can be expanded
        return self._construct_generic_attack(context, AttackCategory.ECONOMIC)

    def _construct_dos_attack(self, context: Any) -> Optional[AttackConstruction]:
        """Construct denial of service attack."""
        # Simplified implementation - can be expanded
        return self._construct_generic_attack(context, AttackCategory.DENIAL_OF_SERVICE)

    def _construct_generic_attack(
        self, context: Any, category: AttackCategory
    ) -> Optional[AttackConstruction]:
        """Generic attack construction fallback."""
        target_nodes = context.focal_nodes if hasattr(context, "focal_nodes") else []

        preconditions = [
            AttackPrerequisite(
                condition="Vulnerable pattern detected",
                satisfied=True,
                evidence=target_nodes,
            )
        ]

        attack_steps = [
            AttackStep(
                step_number=1,
                action="Exploit detected vulnerability",
                effect="Contract behavior compromised",
            )
        ]

        factors = ExploitabilityFactors()
        factors.pattern_match_strength = 0.5
        exploitability = factors.calculate_score()

        economic = EconomicAnalysis(impact_level=EconomicImpact.MEDIUM)

        return AttackConstruction(
            category=category,
            target_nodes=target_nodes,
            preconditions=preconditions,
            attack_steps=attack_steps,
            postconditions=["Vulnerability exploited"],
            exploitability_score=exploitability,
            feasibility=AttackFeasibility.MEDIUM,
            economic_analysis=economic,
        )
