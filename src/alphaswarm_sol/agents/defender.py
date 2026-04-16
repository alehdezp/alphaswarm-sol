"""
P2-T3: Defender Agent

Argues for safety by identifying guards, checking spec compliance, and generating
rebuttals to attacker claims.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class DefenseType(Enum):
    """Types of defense arguments."""

    GUARD_PRESENT = "guard_present"
    INVARIANT_PRESERVED = "invariant_preserved"
    SPEC_COMPLIANT = "spec_compliant"
    PRECONDITION_UNSATISFIABLE = "precondition_unsatisfiable"
    CEI_PATTERN = "cei_pattern"
    SAFE_LIBRARY = "safe_library"


class RebuttalStrategy(Enum):
    """Strategies for rebutting attacker claims."""

    GUARD_BLOCKS = "guard_blocks"
    PRECONDITION_FALSE = "precondition_false"
    INVARIANT_MAINTAINED = "invariant_maintained"
    SPEC_REQUIRES_SAFETY = "spec_requires_safety"
    EXECUTION_ORDER = "execution_order"


@dataclass
class GuardInfo:
    """Information about a detected guard."""

    guard_type: str
    name: str
    strength: float
    evidence: List[str] = field(default_factory=list)
    blocks_attacks: List[str] = field(default_factory=list)


@dataclass
class Rebuttal:
    """A rebuttal to an attacker claim."""

    attack_id: str
    attack_description: str
    strategy: RebuttalStrategy
    claim: str
    evidence: List[str] = field(default_factory=list)
    unsatisfiable_preconditions: List[str] = field(default_factory=list)
    blocking_guards: List[str] = field(default_factory=list)
    strength: float = 0.0
    reasoning: str = ""


@dataclass
class DefenseArgument:
    """An argument for why code is safe."""

    id: str
    claim: str
    defense_type: DefenseType

    # Evidence
    evidence: List[str] = field(default_factory=list)
    guards_identified: List[GuardInfo] = field(default_factory=list)
    spec_references: List[str] = field(default_factory=list)

    # Strength
    strength: float = 0.0
    strength_reasoning: str = ""
    strength_factors: Dict[str, float] = field(default_factory=dict)

    # Rebuttal info
    rebuts_attack: Optional[str] = None
    rebuttal: Optional[Rebuttal] = None


@dataclass
class DefenderResult:
    """Result from defender agent."""

    matched: bool  # Did we find defenses?
    confidence: float  # Overall defense strength 0.0-1.0
    defenses: List[DefenseArgument] = field(default_factory=list)
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class DefenderAgent:
    """
    Agent that argues for safety.

    Analyzes code from defensive perspective:
    1. What protections exist?
    2. What specifications are correctly implemented?
    3. What invariants are preserved?
    4. Why are attacker claims wrong?
    """

    # Evidence-based strength ratings
    GUARD_STRENGTHS = {
        "reentrancy_guard": 0.95,
        "only_owner": 0.85,
        "role_based": 0.85,
        "pausable": 0.70,
        "cei_pattern": 0.80,
        "safe_erc20": 0.90,
        "input_validation": 0.60,
    }

    # Maps guard types to attack categories they block
    GUARD_PROTECTIONS = {
        "reentrancy_guard": ["reentrancy_classic", "reentrancy_cross_function"],
        "only_owner": ["unauthorized_access", "privilege_escalation"],
        "role_based": ["unauthorized_access", "privilege_escalation"],
        "pausable": ["emergency_drain", "exploit_ongoing"],
        "cei_pattern": ["reentrancy_classic"],
        "safe_erc20": ["unchecked_return", "non_standard_erc20"],
    }

    def __init__(self, domain_kg: Optional[Any] = None, use_llm: bool = False):
        """
        Initialize defender agent.

        Args:
            domain_kg: Optional domain knowledge graph with specs
            use_llm: Whether to use LLM for complex rebuttals (default: False for tests)
        """
        self.domain_kg = domain_kg
        self.use_llm = use_llm
        self.logger = logging.getLogger(__name__)

    def analyze(self, context: Any) -> DefenderResult:
        """
        Analyze from defender perspective.

        Args:
            context: AgentContext with focal nodes and subgraph

        Returns:
            DefenderResult with defense arguments
        """
        try:
            defenses = []

            for node_id in context.focal_nodes:
                # Get node from subgraph
                node = None
                if hasattr(context.subgraph, "nodes"):
                    node = context.subgraph.nodes.get(node_id)

                if not node:
                    continue

                # Phase 1: Analyze guards
                guard_defenses = self._analyze_guards(node, context)
                defenses.extend(guard_defenses)

                # Phase 2: Check spec compliance
                spec_defenses = self._check_spec_compliance(node, context)
                defenses.extend(spec_defenses)

                # Phase 3: Check safe patterns
                pattern_defenses = self._check_safe_patterns(node, context)
                defenses.extend(pattern_defenses)

                # Phase 4: Rebut attacker claims
                if hasattr(context, "upstream_results") and context.upstream_results:
                    rebuttals = self._generate_rebuttals(node, context)
                    defenses.extend(rebuttals)

            # Compute overall defense strength
            confidence = self._compute_overall_defense_strength(defenses)
            summary = self._generate_summary(defenses)

            return DefenderResult(
                matched=len(defenses) > 0,
                confidence=confidence,
                defenses=defenses,
                summary=summary,
                metadata={
                    "guard_count": len(
                        [d for d in defenses if d.defense_type == DefenseType.GUARD_PRESENT]
                    ),
                    "rebuttal_count": len([d for d in defenses if d.rebuts_attack]),
                },
            )

        except Exception as e:
            self.logger.error(f"Defender agent error: {e}", exc_info=True)
            return DefenderResult(
                matched=False,
                confidence=0.0,
                metadata={"error": str(e)},
            )

    def _analyze_guards(self, node: Any, context: Any) -> List[DefenseArgument]:
        """Identify security guards and protections."""
        guards = []

        if not hasattr(node, "properties"):
            return guards

        props = node.properties

        # Check reentrancy guard
        if props.get("has_reentrancy_guard"):
            guards.append(
                self._create_guard_defense(
                    node,
                    "reentrancy_guard",
                    "nonReentrant",
                    "Function is protected against reentrancy attacks",
                )
            )

        # Check access control
        if props.get("has_access_gate"):
            modifiers = props.get("modifiers", [])
            guard_type = (
                "role_based"
                if any("role" in m.lower() for m in modifiers)
                else "only_owner"
            )
            guards.append(
                self._create_guard_defense(
                    node,
                    guard_type,
                    ", ".join(modifiers) if modifiers else "access control",
                    "Function has access control restricting callers",
                )
            )

        # Check CEI pattern
        if self._follows_cei_pattern(node):
            guards.append(
                DefenseArgument(
                    id=f"guard_cei_{node.id}",
                    claim="Function follows Checks-Effects-Interactions pattern",
                    defense_type=DefenseType.CEI_PATTERN,
                    evidence=["State updates before external calls"],
                    guards_identified=[
                        GuardInfo(
                            guard_type="cei_pattern",
                            name="CEI",
                            strength=0.80,
                            evidence=["State before call"],
                            blocks_attacks=["reentrancy_classic"],
                        )
                    ],
                    strength=0.80,
                    strength_reasoning="CEI prevents reentrancy structurally",
                    strength_factors={"pattern_compliance": 0.80},
                )
            )

        # Check SafeERC20
        if props.get("uses_safe_erc20"):
            guards.append(
                self._create_guard_defense(
                    node,
                    "safe_erc20",
                    "SafeERC20",
                    "Function uses SafeERC20 for token transfers",
                )
            )

        # Check pausable
        if props.get("has_pause_mechanism"):
            guards.append(
                self._create_guard_defense(
                    node,
                    "pausable",
                    "Pausable",
                    "Function can be paused in emergency",
                )
            )

        return guards

    def _follows_cei_pattern(self, node: Any) -> bool:
        """Check if behavioral signature follows CEI pattern."""
        if not hasattr(node, "properties"):
            return False

        sig = node.properties.get("behavioral_signature", "")
        if not sig or "W:" not in sig or "X:" not in sig:
            return False

        parts = sig.split("→")
        last_write_idx = -1
        first_external_idx = len(parts)

        for i, part in enumerate(parts):
            if part.startswith("W:"):
                last_write_idx = i
            if part.startswith("X:") and first_external_idx == len(parts):
                first_external_idx = i

        # CEI: Writes happen before external calls
        return last_write_idx < first_external_idx

    def _create_guard_defense(
        self, node: Any, guard_type: str, name: str, claim: str
    ) -> DefenseArgument:
        """Create a guard-based defense argument."""
        strength = self.GUARD_STRENGTHS.get(guard_type, 0.5)
        blocks = self.GUARD_PROTECTIONS.get(guard_type, [])

        return DefenseArgument(
            id=f"guard_{guard_type}_{node.id}",
            claim=claim,
            defense_type=DefenseType.GUARD_PRESENT,
            evidence=[f"{name} detected"],
            guards_identified=[
                GuardInfo(
                    guard_type=guard_type,
                    name=name,
                    strength=strength,
                    evidence=[f"{name} present"],
                    blocks_attacks=blocks,
                )
            ],
            strength=strength,
            strength_reasoning=f"{name} is a proven protective mechanism",
            strength_factors={"guard_strength": strength},
        )

    def _check_spec_compliance(self, node: Any, context: Any) -> List[DefenseArgument]:
        """Check if function complies with specifications."""
        defenses = []

        # Only check if we have specs in context
        if not hasattr(context, "specs") or not context.specs:
            return defenses

        for spec in context.specs:
            # Simple check: if spec is referenced, assume implementation
            # In real implementation, would check IMPLEMENTS/VIOLATES edges
            defenses.append(
                DefenseArgument(
                    id=f"spec_compliance_{node.id}_{spec.id if hasattr(spec, 'id') else 'unknown'}",
                    claim=f"Function correctly implements specification",
                    defense_type=DefenseType.SPEC_COMPLIANT,
                    evidence=["Spec reference found"],
                    spec_references=[spec.id if hasattr(spec, "id") else "unknown"],
                    strength=0.80,
                    strength_reasoning="Spec compliance indicates correctness",
                    strength_factors={"implements": 0.4, "no_violations": 0.4},
                )
            )

        return defenses

    def _check_safe_patterns(self, node: Any, context: Any) -> List[DefenseArgument]:
        """Check for known safe coding patterns."""
        defenses = []

        if not hasattr(node, "properties"):
            return defenses

        props = node.properties

        # Pull payment pattern
        if self._uses_pull_pattern(node):
            defenses.append(
                DefenseArgument(
                    id=f"pattern_pull_{node.id}",
                    claim="Uses pull payment pattern",
                    defense_type=DefenseType.INVARIANT_PRESERVED,
                    evidence=["User pulls funds, no push"],
                    strength=0.75,
                    strength_reasoning="Pull pattern reduces reentrancy surface",
                    strength_factors={"pattern_safety": 0.75},
                )
            )

        # Input validation
        if props.get("has_input_validation"):
            defenses.append(
                DefenseArgument(
                    id=f"pattern_validation_{node.id}",
                    claim="Function validates inputs",
                    defense_type=DefenseType.INVARIANT_PRESERVED,
                    evidence=["Input validation present"],
                    strength=0.60,
                    strength_reasoning="Input validation prevents invalid states",
                    strength_factors={"validation": 0.60},
                )
            )

        return defenses

    def _uses_pull_pattern(self, node: Any) -> bool:
        """Check if function uses pull payment pattern."""
        if not hasattr(node, "label") or not hasattr(node, "properties"):
            return False

        # Handle Mock objects and non-string labels
        try:
            label = str(node.label).lower() if node.label else ""
        except (TypeError, AttributeError):
            return False

        props = node.properties

        return ("withdraw" in label or "claim" in label) and props.get(
            "reads_user_balance", False
        )

    def _generate_rebuttals(self, node: Any, context: Any) -> List[DefenseArgument]:
        """Generate rebuttals to attacker claims."""
        rebuttals = []

        for upstream in context.upstream_results:
            # Check if this is an attacker result
            if not hasattr(upstream, "attack") or not upstream.attack:
                continue

            attack = upstream.attack

            # Strategy 1: Check if guards block attack
            blocking_guards = self._find_blocking_guards(node, attack)
            if blocking_guards:
                rebuttals.append(
                    self._create_guard_rebuttal(node, attack, blocking_guards)
                )
                continue

            # Strategy 2: Check unsatisfiable preconditions
            unsatisfiable = self._find_unsatisfiable_preconditions(node, attack)
            if unsatisfiable:
                rebuttals.append(
                    self._create_precondition_rebuttal(node, attack, unsatisfiable)
                )

        return rebuttals

    def _find_blocking_guards(self, node: Any, attack: Any) -> List[GuardInfo]:
        """Find guards that would block this attack."""
        blocking = []

        # Get attack category
        category = None
        if hasattr(attack, "category"):
            category = attack.category.value if hasattr(attack.category, "value") else str(attack.category)

        # Map category to pattern IDs
        category_to_patterns = {
            "state_manipulation": ["reentrancy_classic", "reentrancy_cross_function"],
            "access_bypass": ["unauthorized_access", "privilege_escalation"],
        }

        patterns = category_to_patterns.get(category, [])

        # Check each guard type
        for guard_type, blocked_patterns in self.GUARD_PROTECTIONS.items():
            # Check if guard blocks any of the attack patterns
            if any(p in blocked_patterns for p in patterns):
                if self._has_guard(node, guard_type):
                    blocking.append(
                        GuardInfo(
                            guard_type=guard_type,
                            name=guard_type,
                            strength=self.GUARD_STRENGTHS.get(guard_type, 0.5),
                            evidence=[f"Blocks {category}"],
                            blocks_attacks=patterns,
                        )
                    )

        return blocking

    def _has_guard(self, node: Any, guard_type: str) -> bool:
        """Check if node has a specific guard type."""
        if not hasattr(node, "properties"):
            return False

        props = node.properties

        checks = {
            "reentrancy_guard": lambda: props.get("has_reentrancy_guard", False),
            "only_owner": lambda: props.get("has_access_gate", False),
            "role_based": lambda: props.get("has_access_gate", False),
            "cei_pattern": lambda: self._follows_cei_pattern(node),
            "safe_erc20": lambda: props.get("uses_safe_erc20", False),
            "pausable": lambda: props.get("has_pause_mechanism", False),
        }

        check = checks.get(guard_type)
        return check() if check else False

    def _create_guard_rebuttal(
        self, node: Any, attack: Any, blocking_guards: List[GuardInfo]
    ) -> DefenseArgument:
        """Create rebuttal based on blocking guards."""
        guard_names = [g.name for g in blocking_guards]
        max_strength = max(g.strength for g in blocking_guards)

        attack_id = attack.id if hasattr(attack, "id") else "unknown"
        attack_desc = getattr(attack, "postconditions", ["Unknown attack"])[0] if hasattr(attack, "postconditions") else "Unknown attack"

        return DefenseArgument(
            id=f"rebuttal_guard_{node.id}_{attack_id}",
            claim=f"Attack blocked by {', '.join(guard_names)}",
            defense_type=DefenseType.GUARD_PRESENT,
            evidence=[f"Guards {guard_names} block this attack pattern"],
            guards_identified=blocking_guards,
            strength=max_strength,
            strength_reasoning="Guards designed to prevent this attack",
            strength_factors={"blocking_guards": max_strength},
            rebuts_attack=attack_id,
            rebuttal=Rebuttal(
                attack_id=attack_id,
                attack_description=attack_desc,
                strategy=RebuttalStrategy.GUARD_BLOCKS,
                claim=f"Blocked by {', '.join(guard_names)}",
                evidence=[f"Guard {g.name}: {g.strength}" for g in blocking_guards],
                blocking_guards=guard_names,
                strength=max_strength,
                reasoning="Guards prevent attack execution",
            ),
        )

    def _find_unsatisfiable_preconditions(
        self, node: Any, attack: Any
    ) -> List[str]:
        """Find preconditions that cannot be satisfied."""
        unsatisfiable = []

        if not hasattr(attack, "preconditions"):
            return unsatisfiable

        if not hasattr(node, "properties"):
            return unsatisfiable

        props = node.properties

        for precond in attack.preconditions:
            # Check if precondition object or string
            condition = precond.condition if hasattr(precond, "condition") else str(precond)
            c_lower = condition.lower()

            # Check various precondition types
            if "reentrancy" in c_lower and props.get("has_reentrancy_guard"):
                unsatisfiable.append(condition)
            elif "access" in c_lower and props.get("has_access_gate"):
                unsatisfiable.append(condition)
            elif "public" in c_lower and props.get("visibility") == "internal":
                unsatisfiable.append(condition)

        return unsatisfiable

    def _create_precondition_rebuttal(
        self, node: Any, attack: Any, unsatisfiable: List[str]
    ) -> DefenseArgument:
        """Create rebuttal based on unsatisfiable preconditions."""
        attack_id = attack.id if hasattr(attack, "id") else "unknown"
        attack_desc = getattr(attack, "postconditions", ["Unknown attack"])[0] if hasattr(attack, "postconditions") else "Unknown attack"

        strength = min(0.85, len(unsatisfiable) * 0.2 + 0.45)

        return DefenseArgument(
            id=f"rebuttal_precond_{node.id}_{attack_id}",
            claim="Attack requires unsatisfiable preconditions",
            defense_type=DefenseType.PRECONDITION_UNSATISFIABLE,
            evidence=[f"Unsatisfiable: {', '.join(unsatisfiable[:3])}"],
            strength=strength,
            strength_reasoning="Attack impossible without preconditions",
            strength_factors={"unsatisfiable": len(unsatisfiable) * 0.2},
            rebuts_attack=attack_id,
            rebuttal=Rebuttal(
                attack_id=attack_id,
                attack_description=attack_desc,
                strategy=RebuttalStrategy.PRECONDITION_FALSE,
                claim="Preconditions cannot be met",
                evidence=unsatisfiable,
                unsatisfiable_preconditions=unsatisfiable,
                strength=strength,
                reasoning="Required conditions are false",
            ),
        )

    def _compute_overall_defense_strength(
        self, defenses: List[DefenseArgument]
    ) -> float:
        """Compute aggregated defense strength."""
        if not defenses:
            return 0.0

        rebuttals = [d for d in defenses if d.rebuts_attack]
        non_rebuttals = [d for d in defenses if not d.rebuts_attack]

        rebuttal_strength = (
            sum(d.strength for d in rebuttals) / len(rebuttals) if rebuttals else 0.0
        )
        defense_strength = (
            sum(d.strength for d in non_rebuttals) / len(non_rebuttals)
            if non_rebuttals
            else 0.0
        )

        # Weight rebuttals higher (60%) than general defenses (40%)
        if rebuttals and non_rebuttals:
            return 0.6 * rebuttal_strength + 0.4 * defense_strength
        return rebuttal_strength or defense_strength

    def _generate_summary(self, defenses: List[DefenseArgument]) -> str:
        """Generate human-readable summary."""
        if not defenses:
            return "No defenses identified"

        lines = [f"Defense Summary: {len(defenses)} arguments"]

        guards = [d for d in defenses if d.defense_type == DefenseType.GUARD_PRESENT]
        if guards:
            lines.append(f"Guards: {len(guards)}")

        rebuttals = [d for d in defenses if d.rebuts_attack]
        if rebuttals:
            lines.append(f"Rebuttals: {len(rebuttals)}")

        specs = [d for d in defenses if d.defense_type == DefenseType.SPEC_COMPLIANT]
        if specs:
            lines.append(f"Spec Compliance: {len(specs)}")

        return " | ".join(lines)
