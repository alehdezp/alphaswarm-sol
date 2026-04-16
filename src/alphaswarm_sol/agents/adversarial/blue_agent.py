"""Blue Team Agent for defense generation and patch recommendations.

Per 05.11-08-PLAN.md: Blue Agent generates defenses that break attack causal chains,
proposes patches with cost analysis, and synthesizes invariants.

Key Features:
- Defense generation: Patches that break causal chain
- Cost analysis: Implementation cost vs prevented loss
- Invariant synthesis: Suggest require() statements
- Integration with mitigation knowledge base

Usage:
    from alphaswarm_sol.agents.adversarial.blue_agent import (
        BlueAgent,
        DefensePlan,
        PatchRecommendation,
        Mitigation,
    )

    agent = BlueAgent()
    defense = agent.generate_defense(
        attack_plan=red_agent_output,
        mitigation_db=known_mitigations,
    )

    print(f"Patches: {len(defense.patches)}")
    print(f"Cost estimate: ${defense.cost_estimate:,.2f}")
    print(f"Effectiveness: {defense.effectiveness:.1%}")
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Mitigation Types
# =============================================================================


class MitigationType(Enum):
    """Types of mitigations."""

    REENTRANCY_GUARD = "reentrancy_guard"
    ACCESS_CONTROL = "access_control"
    INPUT_VALIDATION = "input_validation"
    ORACLE_VALIDATION = "oracle_validation"
    TIMELOCK = "timelock"
    RATE_LIMIT = "rate_limit"
    PAUSE_MECHANISM = "pause_mechanism"
    CEI_PATTERN = "cei_pattern"
    SAFE_MATH = "safe_math"
    SAFE_ERC20 = "safe_erc20"
    FLASH_LOAN_GUARD = "flash_loan_guard"
    MEV_PROTECTION = "mev_protection"
    INVARIANT_CHECK = "invariant_check"


class PatchComplexity(Enum):
    """Complexity levels for patches."""

    TRIVIAL = "trivial"  # One-line fix
    SIMPLE = "simple"  # Few lines, no architecture change
    MODERATE = "moderate"  # Multiple files, minor refactoring
    COMPLEX = "complex"  # Significant refactoring required
    ARCHITECTURAL = "architectural"  # Major redesign needed


# =============================================================================
# Patch and Mitigation Types
# =============================================================================


@dataclass
class PatchRecommendation:
    """A recommended code patch to mitigate an attack.

    Attributes:
        id: Unique patch identifier
        file_path: Path to file to patch
        line_range: Tuple of (start_line, end_line) to modify
        description: Human-readable description
        code_snippet: Suggested code change
        rationale: Why this blocks the attack
        breaks_chain_at: Which causal chain node this blocks
        complexity: Implementation complexity
        gas_impact: Estimated gas cost change (can be negative)
        evidence_refs: Supporting evidence
    """

    id: str
    file_path: str
    line_range: Tuple[int, int]
    description: str
    code_snippet: str
    rationale: str
    breaks_chain_at: str = ""
    complexity: PatchComplexity = PatchComplexity.SIMPLE
    gas_impact: int = 0
    evidence_refs: List[str] = field(default_factory=list)

    @property
    def implementation_cost_usd(self) -> float:
        """Estimate implementation cost based on complexity.

        Returns:
            Estimated cost in USD (engineering time)
        """
        costs = {
            PatchComplexity.TRIVIAL: 100,
            PatchComplexity.SIMPLE: 500,
            PatchComplexity.MODERATE: 2000,
            PatchComplexity.COMPLEX: 10000,
            PatchComplexity.ARCHITECTURAL: 50000,
        }
        return costs.get(self.complexity, 1000)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "line_range": list(self.line_range),
            "description": self.description,
            "code_snippet": self.code_snippet,
            "rationale": self.rationale,
            "breaks_chain_at": self.breaks_chain_at,
            "complexity": self.complexity.value,
            "gas_impact": self.gas_impact,
            "evidence_refs": self.evidence_refs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatchRecommendation":
        """Create PatchRecommendation from dictionary."""
        complexity = data.get("complexity", "simple")
        if isinstance(complexity, str):
            complexity = PatchComplexity(complexity)

        line_range = data.get("line_range", [0, 0])
        if isinstance(line_range, list):
            line_range = tuple(line_range)

        return cls(
            id=str(data.get("id", "")),
            file_path=str(data.get("file_path", "")),
            line_range=line_range,  # type: ignore
            description=str(data.get("description", "")),
            code_snippet=str(data.get("code_snippet", "")),
            rationale=str(data.get("rationale", "")),
            breaks_chain_at=str(data.get("breaks_chain_at", "")),
            complexity=complexity,
            gas_impact=int(data.get("gas_impact", 0)),
            evidence_refs=list(data.get("evidence_refs", [])),
        )


@dataclass
class Mitigation:
    """A mitigation measure (broader than a single patch).

    Attributes:
        id: Unique mitigation identifier
        mitigation_type: Type of mitigation
        name: Human-readable name
        description: Detailed description
        effectiveness: How much of attack prevented (0-1)
        implementation_steps: Steps to implement
        required_patches: Patches needed to implement
        config_changes: Configuration changes needed
        deployment_risk: Risk level of deployment
        rollback_plan: How to roll back if needed
    """

    id: str
    mitigation_type: MitigationType
    name: str
    description: str = ""
    effectiveness: float = 0.0
    implementation_steps: List[str] = field(default_factory=list)
    required_patches: List[str] = field(default_factory=list)
    config_changes: Dict[str, Any] = field(default_factory=dict)
    deployment_risk: str = "low"
    rollback_plan: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "mitigation_type": self.mitigation_type.value,
            "name": self.name,
            "description": self.description,
            "effectiveness": self.effectiveness,
            "implementation_steps": self.implementation_steps,
            "required_patches": self.required_patches,
            "config_changes": self.config_changes,
            "deployment_risk": self.deployment_risk,
            "rollback_plan": self.rollback_plan,
        }


@dataclass
class DefensePlan:
    """Complete defense plan against an attack.

    Per 05.11-08: Contains patches, mitigations, cost analysis, and side effects.

    Attributes:
        id: Unique defense plan identifier
        attack_plan_id: ID of attack being defended against
        patches: Code changes recommended
        mitigations: Broader mitigation measures
        cost_estimate: Total implementation cost in USD
        effectiveness: Overall effectiveness (0-1)
        side_effects: Potential negative impacts
        invariants_suggested: require() statements to add
        evidence_refs: Supporting evidence
        metadata: Additional metadata
    """

    id: str
    attack_plan_id: str
    patches: List[PatchRecommendation] = field(default_factory=list)
    mitigations: List[Mitigation] = field(default_factory=list)
    cost_estimate: Decimal = Decimal("0")
    effectiveness: float = 0.0
    side_effects: List[str] = field(default_factory=list)
    invariants_suggested: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Calculate cost estimate from patches."""
        if not self.cost_estimate and self.patches:
            self.cost_estimate = Decimal(
                str(sum(p.implementation_cost_usd for p in self.patches))
            )

    @property
    def cost_benefit_ratio(self) -> float:
        """Calculate cost/benefit ratio.

        Returns:
            Ratio of prevented loss to implementation cost (higher = better)
        """
        prevented_loss = self.metadata.get("prevented_loss_usd", 0)
        if float(self.cost_estimate) == 0:
            return float("inf") if prevented_loss > 0 else 0.0
        return prevented_loss / float(self.cost_estimate)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "attack_plan_id": self.attack_plan_id,
            "patches": [p.to_dict() for p in self.patches],
            "mitigations": [m.to_dict() for m in self.mitigations],
            "cost_estimate": str(self.cost_estimate),
            "effectiveness": self.effectiveness,
            "side_effects": self.side_effects,
            "invariants_suggested": self.invariants_suggested,
            "evidence_refs": self.evidence_refs,
            "metadata": self.metadata,
        }


# =============================================================================
# Blue Agent
# =============================================================================


class BlueAgent:
    """Blue Team agent for defense generation.

    Per 05.11-08: Generates defenses that break attack causal chains,
    proposes patches with cost analysis, and synthesizes invariants.

    Key Features:
    - Analyze attack causal chain to find break points
    - Generate patches that block specific attack steps
    - Cost-benefit analysis of defenses
    - Invariant synthesis from attack patterns

    Usage:
        agent = BlueAgent()
        defense = agent.generate_defense(attack_plan, mitigation_db)
    """

    # Mitigation effectiveness by type and attack pattern
    MITIGATION_EFFECTIVENESS = {
        MitigationType.REENTRANCY_GUARD: {
            "reentrancy": 0.95,
            "callback": 0.90,
            "default": 0.3,
        },
        MitigationType.ACCESS_CONTROL: {
            "access": 0.95,
            "privilege": 0.90,
            "unauthorized": 0.85,
            "default": 0.4,
        },
        MitigationType.ORACLE_VALIDATION: {
            "oracle": 0.85,
            "price": 0.80,
            "manipulation": 0.75,
            "default": 0.2,
        },
        MitigationType.TIMELOCK: {
            "governance": 0.80,
            "admin": 0.75,
            "upgrade": 0.70,
            "default": 0.3,
        },
        MitigationType.CEI_PATTERN: {
            "reentrancy": 0.80,
            "state": 0.75,
            "default": 0.3,
        },
        MitigationType.FLASH_LOAN_GUARD: {
            "flash": 0.85,
            "loan": 0.80,
            "default": 0.2,
        },
    }

    def __init__(
        self,
        mitigation_db: Optional[Dict[str, Any]] = None,
        use_llm: bool = False,
    ):
        """Initialize Blue Agent.

        Args:
            mitigation_db: Optional database of known mitigations
            use_llm: Enable LLM for defense generation
        """
        self.mitigation_db = mitigation_db or {}
        self.use_llm = use_llm
        self._effective_defenses: List[DefensePlan] = []

    def generate_defense(
        self,
        attack_plan: Any,
        mitigation_db: Optional[Dict[str, Any]] = None,
    ) -> DefensePlan:
        """Generate defense plan against an attack.

        Per 05.11-08: Proposes patches that break attack causal chain.

        Args:
            attack_plan: AttackPlan from Red Agent
            mitigation_db: Optional additional mitigations

        Returns:
            DefensePlan with patches, mitigations, and cost analysis
        """
        db = mitigation_db or self.mitigation_db
        attack_id = getattr(attack_plan, "id", "unknown")
        vuln_id = getattr(attack_plan, "vulnerability_id", "unknown")

        logger.info(f"BlueAgent: Generating defense for attack {attack_id}")

        # Analyze attack to find defense opportunities
        causal_chain = self._extract_causal_chain(attack_plan)
        exploit_steps = self._extract_exploit_steps(attack_plan)

        # Generate patches for each break point
        patches = self._generate_patches(attack_plan, causal_chain)

        # Find applicable mitigations
        mitigations = self._find_mitigations(attack_plan, db)

        # Synthesize invariants
        invariants = self._synthesize_invariants(attack_plan, causal_chain)

        # Identify side effects
        side_effects = self._identify_side_effects(patches, mitigations)

        # Calculate overall effectiveness
        effectiveness = self._calculate_effectiveness(
            attack_plan, patches, mitigations
        )

        # Calculate cost
        cost = Decimal(str(sum(p.implementation_cost_usd for p in patches)))
        for mitigation in mitigations:
            # Add mitigation-specific costs
            if mitigation.config_changes:
                cost += Decimal("500")  # Config change cost

        # Build defense plan
        defense = DefensePlan(
            id=f"defense:{attack_id}:{self._generate_id(patches)}",
            attack_plan_id=attack_id,
            patches=patches,
            mitigations=mitigations,
            cost_estimate=cost,
            effectiveness=effectiveness,
            side_effects=side_effects,
            invariants_suggested=invariants,
            evidence_refs=getattr(attack_plan, "evidence_refs", []),
            metadata={
                "vulnerability_id": vuln_id,
                "causal_chain_length": len(causal_chain),
                "exploit_steps": len(exploit_steps),
                "prevented_loss_usd": float(
                    getattr(attack_plan, "expected_profit", 0)
                ) * effectiveness,
            },
        )

        # Track effective defenses
        if effectiveness > 0.5:
            self._effective_defenses.append(defense)

        logger.info(
            f"BlueAgent: Generated defense for {attack_id}, "
            f"effectiveness={effectiveness:.1%}, cost=${float(cost):,.2f}"
        )

        return defense

    def _generate_id(self, data: Any) -> str:
        """Generate stable ID from data."""
        content = str(data)
        return hashlib.sha256(content.encode()).hexdigest()[:8]

    def _extract_causal_chain(self, attack_plan: Any) -> List[str]:
        """Extract causal chain from attack plan.

        Args:
            attack_plan: AttackPlan

        Returns:
            List of causal chain node IDs
        """
        if hasattr(attack_plan, "causal_chain"):
            return list(attack_plan.causal_chain)

        # Infer from exploit path
        chain = []
        if hasattr(attack_plan, "exploit_path"):
            path = attack_plan.exploit_path
            if hasattr(path, "transactions"):
                for tx in path.transactions:
                    chain.append(f"step:{tx.function_name or tx.action}")

        return chain

    def _extract_exploit_steps(self, attack_plan: Any) -> List[Dict[str, Any]]:
        """Extract exploit steps from attack plan.

        Args:
            attack_plan: AttackPlan

        Returns:
            List of exploit step dictionaries
        """
        steps = []
        if hasattr(attack_plan, "exploit_path"):
            path = attack_plan.exploit_path
            if hasattr(path, "transactions"):
                for tx in path.transactions:
                    steps.append(tx.to_dict() if hasattr(tx, "to_dict") else {})

        return steps

    def _generate_patches(
        self,
        attack_plan: Any,
        causal_chain: List[str],
    ) -> List[PatchRecommendation]:
        """Generate patches to block attack.

        Args:
            attack_plan: AttackPlan
            causal_chain: Causal chain nodes

        Returns:
            List of patch recommendations
        """
        patches: List[PatchRecommendation] = []
        vuln_id = getattr(attack_plan, "vulnerability_id", "unknown")

        # Determine attack pattern
        pattern = self._infer_attack_pattern(attack_plan)

        # Generate pattern-specific patches
        if "reentrancy" in pattern:
            patches.append(self._create_reentrancy_patch(attack_plan, causal_chain))
            patches.append(self._create_cei_patch(attack_plan, causal_chain))

        if "access" in pattern or "auth" in pattern:
            patches.append(self._create_access_control_patch(attack_plan, causal_chain))

        if "oracle" in pattern or "price" in pattern:
            patches.append(self._create_oracle_patch(attack_plan, causal_chain))

        if "flash" in pattern:
            patches.append(self._create_flash_loan_patch(attack_plan, causal_chain))

        if "governance" in pattern:
            patches.append(self._create_timelock_patch(attack_plan, causal_chain))

        # Always add input validation as defense in depth
        patches.append(self._create_validation_patch(attack_plan, causal_chain))

        # Filter out None patches and deduplicate
        patches = [p for p in patches if p is not None]
        seen_ids = set()
        unique_patches = []
        for p in patches:
            if p.id not in seen_ids:
                seen_ids.add(p.id)
                unique_patches.append(p)

        return unique_patches

    def _infer_attack_pattern(self, attack_plan: Any) -> str:
        """Infer attack pattern from plan.

        Args:
            attack_plan: AttackPlan

        Returns:
            Pattern string for matching
        """
        pattern = ""

        # Check vulnerability ID
        vuln_id = getattr(attack_plan, "vulnerability_id", "").lower()
        pattern += vuln_id

        # Check metadata
        metadata = getattr(attack_plan, "metadata", {})
        if "severity" in metadata:
            pattern += f" {metadata['severity']}"

        # Check causal chain
        chain = getattr(attack_plan, "causal_chain", [])
        pattern += " " + " ".join(str(c).lower() for c in chain)

        # Check exploit path
        if hasattr(attack_plan, "exploit_path"):
            path = attack_plan.exploit_path
            if hasattr(path, "transactions"):
                for tx in path.transactions:
                    tx_type = getattr(tx, "tx_type", None)
                    if tx_type:
                        pattern += f" {tx_type.value if hasattr(tx_type, 'value') else tx_type}"

        return pattern.lower()

    def _create_reentrancy_patch(
        self,
        attack_plan: Any,
        causal_chain: List[str],
    ) -> PatchRecommendation:
        """Create reentrancy guard patch."""
        vuln_id = getattr(attack_plan, "vulnerability_id", "unknown")
        func_name = self._get_vulnerable_function(attack_plan)

        return PatchRecommendation(
            id=f"patch:reentrancy:{vuln_id}",
            file_path="contracts/Vulnerable.sol",
            line_range=(1, 10),
            description="Add reentrancy guard modifier",
            code_snippet=f"""
// Add OpenZeppelin ReentrancyGuard
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract Vulnerable is ReentrancyGuard {{
    function {func_name}() external nonReentrant {{
        // ... existing code
    }}
}}
""".strip(),
            rationale="ReentrancyGuard prevents recursive calls by using a mutex lock",
            breaks_chain_at="step:callback_abuse" if "callback" in str(causal_chain) else "step:reentry",
            complexity=PatchComplexity.SIMPLE,
            gas_impact=2300,  # SLOAD + SSTORE for mutex
        )

    def _create_cei_patch(
        self,
        attack_plan: Any,
        causal_chain: List[str],
    ) -> PatchRecommendation:
        """Create CEI pattern refactor patch."""
        vuln_id = getattr(attack_plan, "vulnerability_id", "unknown")
        func_name = self._get_vulnerable_function(attack_plan)

        return PatchRecommendation(
            id=f"patch:cei:{vuln_id}",
            file_path="contracts/Vulnerable.sol",
            line_range=(10, 30),
            description="Refactor to Checks-Effects-Interactions pattern",
            code_snippet=f"""
function {func_name}() external {{
    // CHECKS
    require(balances[msg.sender] > 0, "No balance");

    // EFFECTS (update state before external call)
    uint256 amount = balances[msg.sender];
    balances[msg.sender] = 0;

    // INTERACTIONS (external call last)
    (bool success,) = msg.sender.call{{value: amount}}("");
    require(success, "Transfer failed");
}}
""".strip(),
            rationale="CEI pattern prevents reentrancy by updating state before external calls",
            breaks_chain_at="step:state_manipulation",
            complexity=PatchComplexity.MODERATE,
            gas_impact=0,  # No additional gas
        )

    def _create_access_control_patch(
        self,
        attack_plan: Any,
        causal_chain: List[str],
    ) -> PatchRecommendation:
        """Create access control patch."""
        vuln_id = getattr(attack_plan, "vulnerability_id", "unknown")
        func_name = self._get_vulnerable_function(attack_plan)

        return PatchRecommendation(
            id=f"patch:access:{vuln_id}",
            file_path="contracts/Vulnerable.sol",
            line_range=(1, 15),
            description="Add access control modifier",
            code_snippet=f"""
// Add OpenZeppelin Access Control
import "@openzeppelin/contracts/access/Ownable.sol";

contract Vulnerable is Ownable {{
    function {func_name}() external onlyOwner {{
        // ... existing privileged code
    }}
}}
""".strip(),
            rationale="Access control restricts function to authorized callers only",
            breaks_chain_at="step:unauthorized_call",
            complexity=PatchComplexity.SIMPLE,
            gas_impact=2600,  # SLOAD for owner check
        )

    def _create_oracle_patch(
        self,
        attack_plan: Any,
        causal_chain: List[str],
    ) -> PatchRecommendation:
        """Create oracle validation patch."""
        vuln_id = getattr(attack_plan, "vulnerability_id", "unknown")

        return PatchRecommendation(
            id=f"patch:oracle:{vuln_id}",
            file_path="contracts/Vulnerable.sol",
            line_range=(20, 40),
            description="Add oracle price validation with bounds and staleness checks",
            code_snippet="""
function getValidatedPrice() internal view returns (uint256) {
    (
        uint80 roundId,
        int256 price,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    ) = priceFeed.latestRoundData();

    // Staleness check
    require(block.timestamp - updatedAt < MAX_STALENESS, "Stale price");

    // Sanity bounds
    require(price > MIN_PRICE && price < MAX_PRICE, "Price out of bounds");

    // Round completeness
    require(answeredInRound >= roundId, "Round not complete");

    return uint256(price);
}
""".strip(),
            rationale="Validates oracle data freshness and sanity to prevent manipulation",
            breaks_chain_at="step:price_manipulation",
            complexity=PatchComplexity.MODERATE,
            gas_impact=5000,  # Additional oracle calls
        )

    def _create_flash_loan_patch(
        self,
        attack_plan: Any,
        causal_chain: List[str],
    ) -> PatchRecommendation:
        """Create flash loan guard patch."""
        vuln_id = getattr(attack_plan, "vulnerability_id", "unknown")
        func_name = self._get_vulnerable_function(attack_plan)

        return PatchRecommendation(
            id=f"patch:flashloan:{vuln_id}",
            file_path="contracts/Vulnerable.sol",
            line_range=(1, 20),
            description="Add flash loan protection",
            code_snippet=f"""
// Flash loan guard
mapping(address => uint256) private lastBlock;

modifier noFlashLoan() {{
    require(lastBlock[msg.sender] != block.number, "Flash loan detected");
    lastBlock[msg.sender] = block.number;
    _;
}}

function {func_name}() external noFlashLoan {{
    // ... existing code
}}
""".strip(),
            rationale="Prevents same-block arbitrage by tracking caller block numbers",
            breaks_chain_at="step:flash_loan_borrow",
            complexity=PatchComplexity.SIMPLE,
            gas_impact=5000,  # SLOAD + SSTORE
        )

    def _create_timelock_patch(
        self,
        attack_plan: Any,
        causal_chain: List[str],
    ) -> PatchRecommendation:
        """Create timelock patch for governance."""
        vuln_id = getattr(attack_plan, "vulnerability_id", "unknown")

        return PatchRecommendation(
            id=f"patch:timelock:{vuln_id}",
            file_path="contracts/Governance.sol",
            line_range=(1, 30),
            description="Add timelock for governance actions",
            code_snippet="""
// Use OpenZeppelin TimelockController
import "@openzeppelin/contracts/governance/TimelockController.sol";

contract GovernedProtocol {
    TimelockController public timelock;
    uint256 public constant DELAY = 2 days;

    function scheduleParameterChange(
        bytes32 parameterId,
        uint256 newValue
    ) external onlyGovernance {
        timelock.schedule(
            address(this),
            0,
            abi.encodeWithSelector(this.executeChange.selector, parameterId, newValue),
            bytes32(0),
            bytes32(0),
            DELAY
        );
    }
}
""".strip(),
            rationale="Timelock provides delay for community review of governance actions",
            breaks_chain_at="step:governance_exploit",
            complexity=PatchComplexity.COMPLEX,
            gas_impact=50000,  # Timelock scheduling gas
        )

    def _create_validation_patch(
        self,
        attack_plan: Any,
        causal_chain: List[str],
    ) -> PatchRecommendation:
        """Create input validation patch."""
        vuln_id = getattr(attack_plan, "vulnerability_id", "unknown")
        func_name = self._get_vulnerable_function(attack_plan)

        return PatchRecommendation(
            id=f"patch:validation:{vuln_id}",
            file_path="contracts/Vulnerable.sol",
            line_range=(15, 25),
            description="Add input validation checks",
            code_snippet=f"""
function {func_name}(uint256 amount, address recipient) external {{
    // Input validation
    require(amount > 0, "Amount must be positive");
    require(amount <= MAX_AMOUNT, "Amount exceeds maximum");
    require(recipient != address(0), "Invalid recipient");
    require(recipient != address(this), "Cannot send to self");

    // ... existing code
}}
""".strip(),
            rationale="Input validation prevents edge cases and invalid parameters",
            breaks_chain_at="step:exploit_entry",
            complexity=PatchComplexity.TRIVIAL,
            gas_impact=200,  # Minimal gas for require statements
        )

    def _get_vulnerable_function(self, attack_plan: Any) -> str:
        """Get vulnerable function name from attack plan."""
        if hasattr(attack_plan, "exploit_path"):
            path = attack_plan.exploit_path
            if hasattr(path, "transactions") and path.transactions:
                for tx in path.transactions:
                    if hasattr(tx, "function_name") and tx.function_name:
                        return tx.function_name
        return "vulnerableFunction"

    def _find_mitigations(
        self,
        attack_plan: Any,
        db: Dict[str, Any],
    ) -> List[Mitigation]:
        """Find applicable mitigations from database.

        Args:
            attack_plan: AttackPlan
            db: Mitigation database

        Returns:
            List of applicable mitigations
        """
        mitigations: List[Mitigation] = []
        pattern = self._infer_attack_pattern(attack_plan)

        # Check each mitigation type
        for mit_type, effectiveness_map in self.MITIGATION_EFFECTIVENESS.items():
            # Find best matching pattern
            best_effectiveness = effectiveness_map.get("default", 0.0)
            for key, eff in effectiveness_map.items():
                if key in pattern and key != "default":
                    best_effectiveness = max(best_effectiveness, eff)

            if best_effectiveness > 0.5:  # Only include effective mitigations
                mitigation = Mitigation(
                    id=f"mitigation:{mit_type.value}",
                    mitigation_type=mit_type,
                    name=mit_type.value.replace("_", " ").title(),
                    description=f"Apply {mit_type.value} to block attack pattern",
                    effectiveness=best_effectiveness,
                    implementation_steps=[
                        f"Identify all entry points vulnerable to {pattern.split()[0]}",
                        f"Apply {mit_type.value} to each entry point",
                        "Test with attack simulation",
                        "Deploy and monitor",
                    ],
                    deployment_risk="low" if best_effectiveness > 0.8 else "medium",
                )
                mitigations.append(mitigation)

        return mitigations

    def _synthesize_invariants(
        self,
        attack_plan: Any,
        causal_chain: List[str],
    ) -> List[str]:
        """Synthesize invariant require() statements.

        Args:
            attack_plan: AttackPlan
            causal_chain: Causal chain nodes

        Returns:
            List of invariant statements
        """
        invariants: List[str] = []
        pattern = self._infer_attack_pattern(attack_plan)

        if "reentrancy" in pattern:
            invariants.append("require(!locked, 'Reentrancy detected');")
            invariants.append("require(balances[msg.sender] >= amount, 'Insufficient balance');")

        if "access" in pattern or "auth" in pattern:
            invariants.append("require(msg.sender == owner, 'Not authorized');")
            invariants.append("require(hasRole(ADMIN_ROLE, msg.sender), 'Missing role');")

        if "oracle" in pattern:
            invariants.append("require(block.timestamp - lastUpdate < STALENESS_THRESHOLD, 'Stale oracle');")
            invariants.append("require(price > MIN_PRICE && price < MAX_PRICE, 'Price out of bounds');")

        if "flash" in pattern:
            invariants.append("require(lastBlock[msg.sender] != block.number, 'Same-block operation');")

        if "governance" in pattern:
            invariants.append("require(block.timestamp >= proposalTime + DELAY, 'Timelock not expired');")

        # Always include basic invariants
        invariants.append("require(amount > 0, 'Zero amount');")
        invariants.append("require(recipient != address(0), 'Zero address');")

        return list(set(invariants))  # Deduplicate

    def _identify_side_effects(
        self,
        patches: List[PatchRecommendation],
        mitigations: List[Mitigation],
    ) -> List[str]:
        """Identify potential side effects of defenses.

        Args:
            patches: Proposed patches
            mitigations: Proposed mitigations

        Returns:
            List of potential side effects
        """
        side_effects: List[str] = []

        for patch in patches:
            if patch.gas_impact > 5000:
                side_effects.append(
                    f"Patch {patch.id} adds ~{patch.gas_impact} gas per call"
                )
            if patch.complexity == PatchComplexity.COMPLEX:
                side_effects.append(
                    f"Patch {patch.id} requires significant refactoring, risk of regression"
                )
            if patch.complexity == PatchComplexity.ARCHITECTURAL:
                side_effects.append(
                    f"Patch {patch.id} requires architectural changes, consider migration plan"
                )

        for mitigation in mitigations:
            if mitigation.mitigation_type == MitigationType.TIMELOCK:
                side_effects.append(
                    "Timelock adds delay to legitimate governance actions"
                )
            if mitigation.mitigation_type == MitigationType.FLASH_LOAN_GUARD:
                side_effects.append(
                    "Flash loan guard may block legitimate arbitrage"
                )
            if mitigation.mitigation_type == MitigationType.RATE_LIMIT:
                side_effects.append(
                    "Rate limiting may affect high-volume legitimate users"
                )

        return list(set(side_effects))

    def _calculate_effectiveness(
        self,
        attack_plan: Any,
        patches: List[PatchRecommendation],
        mitigations: List[Mitigation],
    ) -> float:
        """Calculate overall defense effectiveness.

        Args:
            attack_plan: Attack being defended
            patches: Proposed patches
            mitigations: Proposed mitigations

        Returns:
            Overall effectiveness (0-1)
        """
        if not patches and not mitigations:
            return 0.0

        # Calculate from mitigations (use max effectiveness)
        mit_effectiveness = max(
            (m.effectiveness for m in mitigations),
            default=0.0,
        )

        # Patches add incremental protection
        patch_bonus = min(len(patches) * 0.05, 0.2)  # Up to 20% bonus

        # Combined effectiveness (diminishing returns)
        combined = mit_effectiveness + (1 - mit_effectiveness) * patch_bonus

        return min(combined, 0.99)  # Cap at 99%

    def get_effective_defenses(self) -> List[DefensePlan]:
        """Get list of effective defenses for improvement loop.

        Returns:
            List of defense plans with effectiveness > 50%
        """
        return [d for d in self._effective_defenses if d.effectiveness > 0.5]

    def clear_defense_history(self) -> None:
        """Clear defense history for new simulation."""
        self._effective_defenses.clear()


# =============================================================================
# Module Exports
# =============================================================================


__all__ = [
    "BlueAgent",
    "DefensePlan",
    "PatchRecommendation",
    "PatchComplexity",
    "Mitigation",
    "MitigationType",
]
