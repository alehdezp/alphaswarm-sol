# [P2-T2] Attacker Agent

**Phase**: 2 - Adversarial Agents
**Task ID**: P2-T2
**Status**: NOT_STARTED
**Priority**: CRITICAL
**Estimated Effort**: 4-5 days
**Actual Effort**: -

---

## Executive Summary

Implement the **Attacker Agent** that thinks like an adversary - actively trying to construct exploit scenarios rather than passively matching patterns. This agent asks "How would I exploit this?" and produces concrete attack constructions with preconditions, steps, and expected outcomes.

**Key Innovation**: Not just pattern matching, but active attack synthesis using adversarial KG patterns as templates. Combines formal analysis (behavioral signatures, operation ordering) with LLM creativity for novel attack paths.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              ATTACKER AGENT                                       │
│                                                                                   │
│  Input: AgentContext with focal nodes, patterns, cross-graph edges                │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                        ATTACK STRATEGY SELECTOR                              │ │
│  │                                                                              │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │ │
│  │  │ State Manip  │  │ Access Bypass│  │ Economic     │  │ Data Integrity│   │ │
│  │  │              │  │              │  │              │  │               │   │ │
│  │  │ • Reentrancy │  │ • Missing AC │  │ • Flash Loan │  │ • Oracle Manip│   │ │
│  │  │ • Race cond  │  │ • tx.origin  │  │ • MEV/Frontrun│  │ • Price Feed │   │ │
│  │  │ • State lock │  │ • Privilege  │  │ • Arb exploit│  │ • Data poison │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │ │
│  │                                                                              │ │
│  └───────────────────────────────┬──────────────────────────────────────────────┘ │
│                                  │                                                │
│                                  ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                        PATTERN APPLICABILITY CHECK                           │ │
│  │                                                                              │ │
│  │  For each (focal_node, pattern) pair:                                        │ │
│  │                                                                              │ │
│  │  1. Check required operations present                                        │ │
│  │  2. Check operation ordering matches attack pattern                          │ │
│  │  3. Check guards/mitigations absent                                          │ │
│  │  4. Check economic preconditions satisfiable                                 │ │
│  │                                                                              │ │
│  │  Applicability Score = Σ(matched_criteria * weight) / total_weight           │ │
│  │                                                                              │ │
│  └───────────────────────────────┬──────────────────────────────────────────────┘ │
│                                  │                                                │
│                                  ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                        ATTACK CONSTRUCTOR (LLM)                              │ │
│  │                                                                              │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐    │ │
│  │  │                      Attack Prompt Template                          │    │ │
│  │  │                                                                      │    │ │
│  │  │  • Code context (behavioral signature, operations)                   │    │ │
│  │  │  • Pattern template (from adversarial KG)                            │    │ │
│  │  │  • Historical exploits (SIMILAR_TO edges)                            │    │ │
│  │  │  • Function intent (to violate)                                      │    │ │
│  │  │  • Economic context (TVL, token types)                               │    │ │
│  │  │                                                                      │    │ │
│  │  └─────────────────────────────────────────────────────────────────────┘    │ │
│  │                                  │                                           │ │
│  │                                  ▼                                           │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐    │ │
│  │  │                   AttackConstruction Output                          │    │ │
│  │  │                                                                      │    │ │
│  │  │  • Preconditions (what must be true)                                 │    │ │
│  │  │  • Attack steps (ordered transactions)                               │    │ │
│  │  │  • Economic impact (profit, capital required)                        │    │ │
│  │  │  • Feasibility assessment                                            │    │ │
│  │  │  • Blocking factors (what might prevent)                             │    │ │
│  │  │                                                                      │    │ │
│  │  └─────────────────────────────────────────────────────────────────────┘    │ │
│  │                                                                              │ │
│  └───────────────────────────────┬──────────────────────────────────────────────┘ │
│                                  │                                                │
│                                  ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                      EXPLOITABILITY SCORER                                   │ │
│  │                                                                              │ │
│  │  exploitability = (                                                          │ │
│  │      technical_feasibility * 0.30 +                                          │ │
│  │      guard_absence * 0.25 +                                                  │ │
│  │      pattern_match_strength * 0.20 +                                         │ │
│  │      economic_viability * 0.15 +                                             │ │
│  │      historical_precedent * 0.10                                             │ │
│  │  )                                                                           │ │
│  │                                                                              │ │
│  │  Thresholds:                                                                 │ │
│  │  • > 0.8: CRITICAL (immediate exploit possible)                              │ │
│  │  • > 0.6: HIGH (exploit with some effort)                                    │ │
│  │  • > 0.4: MEDIUM (theoretical exploit)                                       │ │
│  │  • < 0.4: LOW (blocked or unlikely)                                          │ │
│  │                                                                              │ │
│  └───────────────────────────────┬──────────────────────────────────────────────┘ │
│                                  │                                                │
│                                  ▼                                                │
│                     ┌───────────────────────────┐                                 │
│                     │      AgentResult          │                                 │
│                     │  - findings: List[Attack] │                                 │
│                     │  - confidence: float      │                                 │
│                     │  - summary: str           │                                 │
│                     └───────────────────────────┘                                 │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## Attack Strategy Categories

The attacker agent uses categorized attack strategies to guide attack construction:

### Strategy Matrix

| Category | Attack Type | Required Operations | Key Indicators | Typical Profit |
|----------|-------------|---------------------|----------------|----------------|
| **State Manipulation** | Reentrancy | `TRANSFERS_VALUE_OUT` + `WRITES_USER_BALANCE` | X:out before W:bal | Drain funds |
| **State Manipulation** | TOCTOU | `READS_STATE` → `CHECKS` → `WRITES_STATE` | Gap between check/use | Variable |
| **Access Bypass** | Missing Access Control | `WRITES_PRIVILEGED_STATE` | No `CHECKS_PERMISSION` | Admin takeover |
| **Access Bypass** | tx.origin | `CHECKS_TX_ORIGIN` | Missing msg.sender | Phishing |
| **Economic** | Flash Loan | `READS_EXTERNAL_VALUE` + `TRANSFERS_VALUE` | Price dependency | Arbitrage |
| **Economic** | MEV/Frontrun | `READS_ORACLE` + `WRITES_STATE` | Public mempool | Sandwich |
| **Data Integrity** | Oracle Manipulation | `READS_ORACLE` | No staleness check | Price manipulation |
| **Data Integrity** | Signature Malleability | Uses ecrecover | No s-value check | Replay |

### Attack Complexity Levels

```
┌─────────────────────────────────────────────────────────────────┐
│                    ATTACK COMPLEXITY PYRAMID                     │
│                                                                  │
│                        ┌───────────┐                             │
│                        │THEORETICAL│  Requires multiple          │
│                        │           │  unlikely conditions         │
│                        └─────┬─────┘                             │
│                              │                                    │
│                    ┌─────────┴─────────┐                         │
│                    │      COMPLEX      │  Multi-step, timing      │
│                    │                   │  dependent, coordination │
│                    └─────────┬─────────┘                         │
│                              │                                    │
│              ┌───────────────┴───────────────┐                   │
│              │          MODERATE             │  Requires setup    │
│              │                               │  (flash loan, etc) │
│              └───────────────┬───────────────┘                   │
│                              │                                    │
│         ┌────────────────────┴────────────────────┐              │
│         │               TRIVIAL                   │  Single tx,   │
│         │                                         │  no setup     │
│         └─────────────────────────────────────────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Dependencies

### Required Before Starting
- [ ] [P2-T1] Agent Router - Provides context and focal node selection
- [ ] [P0-T2] Adversarial Knowledge Graph - Provides attack patterns and exploit history
- [ ] [P1-T2] LLM Intent Annotator - Provides function intent to violate

### Blocks These Tasks
- [P2-T3] Defender Agent - Receives attack claims to rebut
- [P2-T5] Adversarial Arbiter - Uses attacker findings for verdict
- [P3-T4] Attack Path Synthesis - Builds on attack constructions

---

## Objectives

1. Implement `AttackerAgent` class that constructs concrete exploits
2. Create attack strategy selection based on code properties
3. Generate step-by-step attack sequences with preconditions
4. Calculate exploitability scores with transparent formula
5. Link attacks to historical exploits via adversarial KG
6. Estimate economic impact and capital requirements
7. Identify blocking factors that might prevent exploitation

---

## Technical Design

### Key Data Structures

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum


class AttackCategory(Enum):
    """High-level attack category."""
    STATE_MANIPULATION = "state_manipulation"
    ACCESS_BYPASS = "access_bypass"
    ECONOMIC = "economic"
    DATA_INTEGRITY = "data_integrity"
    DENIAL_OF_SERVICE = "denial_of_service"
    CRYPTOGRAPHIC = "cryptographic"


class AttackFeasibility(Enum):
    """How feasible is this attack to execute."""
    TRIVIAL = "trivial"        # Single tx, no special requirements (0.9-1.0)
    MODERATE = "moderate"      # Requires setup like flash loan (0.7-0.9)
    COMPLEX = "complex"        # Multi-step, timing dependent (0.4-0.7)
    THEORETICAL = "theoretical" # Requires unlikely conditions (0.0-0.4)


class EconomicImpact(Enum):
    """Estimated economic severity."""
    CRITICAL = "critical"      # Total loss possible (TVL drain)
    HIGH = "high"              # Significant loss (>10% TVL)
    MEDIUM = "medium"          # Moderate loss (1-10% TVL)
    LOW = "low"                # Minor loss (<1% TVL)
    UNKNOWN = "unknown"        # Cannot estimate


@dataclass
class AttackPrerequisite:
    """A prerequisite for the attack to work."""
    id: str
    description: str
    is_satisfied: Optional[bool]  # None if unknown
    how_to_satisfy: Optional[str]  # How attacker can ensure this
    blocks_attack_if_false: bool = True


@dataclass
class AttackStep:
    """A single step in an attack sequence."""
    order: int
    description: str
    transaction: Optional[str]  # Pseudocode/Solidity for the tx
    function_call: Optional[str]  # e.g., "withdraw(1000)"
    requires: List[str]  # What must be true before this step
    produces: List[str]  # What this step achieves
    gas_estimate: Optional[int] = None
    value_sent: Optional[str] = None  # ETH sent with tx

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order": self.order,
            "description": self.description,
            "transaction": self.transaction,
            "function_call": self.function_call,
            "requires": self.requires,
            "produces": self.produces,
        }


@dataclass
class EconomicAnalysis:
    """Economic analysis of an attack."""
    estimated_profit: str  # e.g., "Drain 100 ETH contract balance"
    required_capital: str  # e.g., "Flash loan of 1000 ETH"
    break_even_point: Optional[str]  # e.g., "Profitable if gas < 0.1 ETH"
    capital_at_risk: Optional[str]  # e.g., "None (flash loan repaid)"
    time_sensitivity: Optional[str]  # e.g., "Must execute before price update"
    competition_risk: Optional[str]  # e.g., "MEV bots may frontrun"


@dataclass
class AttackConstruction:
    """
    A concrete attack scenario constructed by the Attacker Agent.

    This is NOT just pattern matching - it's an active construction
    of HOW to exploit the code with specific steps and values.
    """
    # Identification
    id: str
    target_function: str
    target_contract: Optional[str] = None

    # Pattern source
    pattern_used: Optional["AttackPattern"] = None
    pattern_id: str = ""
    category: AttackCategory = AttackCategory.STATE_MANIPULATION

    # Attack details
    description: str = ""
    preconditions: List[AttackPrerequisite] = field(default_factory=list)
    attack_steps: List[AttackStep] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)  # What attacker achieves

    # Feasibility assessment
    feasibility: AttackFeasibility = AttackFeasibility.MODERATE
    feasibility_reasoning: str = ""

    # Economic analysis
    economic: Optional[EconomicAnalysis] = None
    impact: EconomicImpact = EconomicImpact.UNKNOWN

    # Exploitability scoring
    exploitability: float = 0.0
    exploitability_breakdown: Dict[str, float] = field(default_factory=dict)

    # Evidence
    evidence: List[str] = field(default_factory=list)
    blocking_factors: List[str] = field(default_factory=list)
    confidence: float = 0.0

    # Cross-graph links
    similar_exploits: List[str] = field(default_factory=list)
    violated_specs: List[str] = field(default_factory=list)

    # Code references
    behavioral_signature: str = ""
    has_behavioral_sequence: bool = False
    has_formal_analysis: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target_function": self.target_function,
            "category": self.category.value,
            "description": self.description,
            "feasibility": self.feasibility.value,
            "exploitability": round(self.exploitability, 3),
            "impact": self.impact.value,
            "steps": [s.to_dict() for s in self.attack_steps],
            "blocking_factors": self.blocking_factors,
            "similar_exploits": self.similar_exploits,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class ExploitabilityFactors:
    """Factors that contribute to exploitability score."""
    technical_feasibility: float = 0.0  # Can the attack be executed? (0-1)
    guard_absence: float = 0.0          # Are protective guards missing? (0-1)
    pattern_match_strength: float = 0.0  # How well does code match pattern? (0-1)
    economic_viability: float = 0.0      # Is attack profitable? (0-1)
    historical_precedent: float = 0.0    # Similar attacks succeeded before? (0-1)

    def calculate_score(self) -> float:
        """Calculate weighted exploitability score."""
        return (
            self.technical_feasibility * 0.30 +
            self.guard_absence * 0.25 +
            self.pattern_match_strength * 0.20 +
            self.economic_viability * 0.15 +
            self.historical_precedent * 0.10
        )


class AttackerAgent:
    """
    Agent that thinks like an attacker.

    NOT just pattern matching - actively constructs exploit scenarios
    using patterns as templates and historical exploits as guides.
    """

    # Attack strategy configuration
    STRATEGY_PRIORITIES = [
        AttackCategory.STATE_MANIPULATION,  # Most common, highest impact
        AttackCategory.ECONOMIC,
        AttackCategory.ACCESS_BYPASS,
        AttackCategory.DATA_INTEGRITY,
        AttackCategory.CRYPTOGRAPHIC,
        AttackCategory.DENIAL_OF_SERVICE,
    ]

    # Weights for exploitability calculation
    EXPLOITABILITY_WEIGHTS = {
        "technical_feasibility": 0.30,
        "guard_absence": 0.25,
        "pattern_match_strength": 0.20,
        "economic_viability": 0.15,
        "historical_precedent": 0.10,
    }

    def __init__(
        self,
        llm_client,
        adversarial_kg: "AdversarialKnowledgeGraph",
    ):
        self.llm = llm_client
        self.adversarial_kg = adversarial_kg

    def analyze(self, context: "AgentContext") -> "AgentResult":
        """
        Analyze from attacker perspective.

        For each focal node, try to construct attacks using matched patterns.
        """
        attacks = []

        for node_id in context.focal_nodes:
            node = context.subgraph.nodes.get(node_id)
            if not node:
                continue

            # Get intent (what we're trying to violate)
            intent = context.intents.get(node_id)

            # Select applicable attack strategies
            strategies = self._select_strategies(node)

            # For each matched pattern, try to construct attack
            for pattern in context.patterns:
                if not self._pattern_applies(node, pattern):
                    continue

                # Get applicability score
                applicability = self._calculate_applicability(node, pattern)
                if applicability < 0.3:
                    continue

                # Construct attack
                attack = self._construct_attack(
                    node, pattern, intent, context, strategies
                )

                if attack and attack.exploitability > 0.3:
                    attacks.append(attack)

        # Rank by exploitability
        attacks.sort(key=lambda a: -a.exploitability)

        return AgentResult(
            agent_type=AgentType.ATTACKER,
            findings=attacks,
            confidence=max(a.confidence for a in attacks) if attacks else 0.0,
            summary=self._generate_summary(attacks),
        )

    def _select_strategies(self, node: "Node") -> List[AttackCategory]:
        """Select applicable attack strategies based on node properties."""
        strategies = []

        # State manipulation strategies
        if self._has_state_manipulation_potential(node):
            strategies.append(AttackCategory.STATE_MANIPULATION)

        # Access bypass strategies
        if self._has_access_bypass_potential(node):
            strategies.append(AttackCategory.ACCESS_BYPASS)

        # Economic strategies
        if self._has_economic_potential(node):
            strategies.append(AttackCategory.ECONOMIC)

        # Data integrity strategies
        if self._has_data_integrity_potential(node):
            strategies.append(AttackCategory.DATA_INTEGRITY)

        return strategies

    def _has_state_manipulation_potential(self, node: "Node") -> bool:
        """Check if node has state manipulation attack potential."""
        props = node.properties

        # Reentrancy potential
        if props.get("state_write_after_external_call"):
            return True

        # Race condition potential
        sig = props.get("behavioral_signature", "")
        if "R:" in sig and "W:" in sig:
            return True

        return False

    def _has_access_bypass_potential(self, node: "Node") -> bool:
        """Check if node has access control bypass potential."""
        props = node.properties

        # Missing access control on privileged operation
        if props.get("writes_privileged_state") and not props.get("has_access_gate"):
            return True

        # tx.origin usage
        if props.get("uses_tx_origin"):
            return True

        return False

    def _has_economic_potential(self, node: "Node") -> bool:
        """Check if node has economic exploit potential."""
        props = node.properties

        # Price dependency without protection
        if props.get("reads_oracle_price") and not props.get("has_staleness_check"):
            return True

        # Flash loan potential
        if props.get("uses_external_balance_check"):
            return True

        return False

    def _has_data_integrity_potential(self, node: "Node") -> bool:
        """Check if node has data integrity attack potential."""
        props = node.properties

        # Oracle manipulation potential
        if props.get("reads_oracle_price"):
            return True

        # Signature issues
        if props.get("uses_ecrecover") and not props.get("checks_sig_s"):
            return True

        return False

    def _pattern_applies(self, node: "Node", pattern: "AttackPattern") -> bool:
        """Check if attack pattern applies to this node."""
        props = node.properties

        # Check required operations
        for op in pattern.required_operations:
            if not props.get(f"has_{op.lower()}"):
                return False

        # Check forbidden mitigations
        for mitigation in pattern.blocked_by:
            if props.get(mitigation):
                return False

        return True

    def _calculate_applicability(
        self,
        node: "Node",
        pattern: "AttackPattern",
    ) -> float:
        """Calculate how well the pattern applies to this node."""
        score = 0.0
        max_score = 0.0

        props = node.properties

        # Required operations (weight: 3 each)
        for op in pattern.required_operations:
            max_score += 3
            if props.get(f"has_{op.lower()}"):
                score += 3

        # Operation ordering (weight: 2)
        if pattern.required_ordering:
            max_score += 2
            sig = props.get("behavioral_signature", "")
            if self._check_ordering(sig, pattern.required_ordering):
                score += 2

        # Absence of mitigations (weight: 2 each)
        for mitigation in pattern.blocked_by:
            max_score += 2
            if not props.get(mitigation):
                score += 2

        return score / max_score if max_score > 0 else 0.0

    def _check_ordering(
        self,
        signature: str,
        ordering: List[Tuple[str, str]],
    ) -> bool:
        """Check if behavioral signature matches required ordering."""
        for before, after in ordering:
            if before not in signature or after not in signature:
                return False
            if signature.index(before) >= signature.index(after):
                return False
        return True

    def _construct_attack(
        self,
        node: "Node",
        pattern: "AttackPattern",
        intent: Optional["FunctionIntent"],
        context: "AgentContext",
        strategies: List[AttackCategory],
    ) -> Optional[AttackConstruction]:
        """
        Construct a concrete attack using the pattern as a template.

        Uses LLM to synthesize attack based on:
        1. The code structure
        2. The attack pattern template
        3. Historical exploit examples
        4. The function's intended behavior (to violate)
        """
        # Get historical exploits for this pattern
        similar_exploits = self.adversarial_kg.get_related_exploits(pattern.id)

        # Calculate exploitability factors
        factors = self._calculate_exploitability_factors(
            node, pattern, similar_exploits, context
        )

        # Build prompt
        prompt = self._build_attack_prompt(
            node, pattern, intent, similar_exploits, context, factors
        )

        # Get LLM to construct attack
        response = self.llm.analyze(prompt, response_format="json")

        # Parse response
        attack = self._parse_attack_response(response, node, pattern, factors)

        if attack:
            # Add cross-graph links
            attack.similar_exploits = [e.name for e in similar_exploits[:3]]
            attack.behavioral_signature = node.properties.get("behavioral_signature", "")
            attack.has_behavioral_sequence = bool(attack.behavioral_signature)

        return attack

    def _calculate_exploitability_factors(
        self,
        node: "Node",
        pattern: "AttackPattern",
        exploits: List["ExploitRecord"],
        context: "AgentContext",
    ) -> ExploitabilityFactors:
        """Calculate individual factors for exploitability score."""
        factors = ExploitabilityFactors()
        props = node.properties

        # 1. Technical feasibility (can the attack be executed?)
        feasibility = 1.0
        if props.get("has_reentrancy_guard"):
            feasibility -= 0.4
        if props.get("has_access_gate"):
            feasibility -= 0.2
        if pattern.complexity == "complex":
            feasibility -= 0.2
        factors.technical_feasibility = max(0.0, feasibility)

        # 2. Guard absence (are protective measures missing?)
        guard_absence = 1.0
        guards_to_check = ["has_reentrancy_guard", "has_access_gate", "has_staleness_check"]
        for guard in guards_to_check:
            if props.get(guard):
                guard_absence -= 0.3
        factors.guard_absence = max(0.0, guard_absence)

        # 3. Pattern match strength
        factors.pattern_match_strength = self._calculate_applicability(node, pattern)

        # 4. Economic viability
        if props.get("transfers_value_out"):
            factors.economic_viability = 0.8
        elif props.get("writes_privileged_state"):
            factors.economic_viability = 0.6
        else:
            factors.economic_viability = 0.3

        # 5. Historical precedent
        if exploits:
            # Higher score for more/larger exploits
            factors.historical_precedent = min(1.0, len(exploits) * 0.2)
            if any(e.loss_usd > 1_000_000 for e in exploits):
                factors.historical_precedent = min(1.0, factors.historical_precedent + 0.3)

        return factors

    def _build_attack_prompt(
        self,
        node: "Node",
        pattern: "AttackPattern",
        intent: Optional["FunctionIntent"],
        exploits: List["ExploitRecord"],
        context: "AgentContext",
        factors: ExploitabilityFactors,
    ) -> str:
        """Build prompt for attack construction."""

        exploit_context = ""
        if exploits:
            exploit_context = f"""
## Historical Exploits Using This Pattern

{self._format_exploits(exploits[:3])}

Learn from these exploits. What made them successful? Apply similar techniques.
"""

        intent_context = ""
        if intent:
            intent_context = f"""
## Function's Intended Behavior (To Violate)

- Business Purpose: {intent.business_purpose.value}
- Trust Assumptions: {[a.description for a in intent.trust_assumptions]}
- Expected Invariants: {[i.description for i in intent.inferred_invariants]}

Your goal is to VIOLATE these assumptions and invariants.
"""

        return f"""You are a security researcher constructing an exploit scenario.

## Target Function

Name: {node.label}
Contract: {node.properties.get('contract_name', 'Unknown')}
Visibility: {node.properties.get('visibility', 'unknown')}
Modifiers: {node.properties.get('modifiers', [])}
Behavioral Signature: {node.properties.get('behavioral_signature', 'N/A')}

## Semantic Operations Detected

{self._format_operations(node)}

## Code Structure

```solidity
{context.subgraph.get_code_context(node.id) if hasattr(context.subgraph, 'get_code_context') else 'Code not available'}
```

## Attack Pattern to Apply

ID: {pattern.id}
Name: {pattern.name}
Description: {pattern.description}
Required Operations: {pattern.required_operations}
Typical Attack Flow: {pattern.detection_hints}

## Exploitability Assessment

- Technical Feasibility: {factors.technical_feasibility:.2f}
- Guard Absence: {factors.guard_absence:.2f}
- Pattern Match: {factors.pattern_match_strength:.2f}
- Economic Viability: {factors.economic_viability:.2f}
- Historical Precedent: {factors.historical_precedent:.2f}
- **Combined Score**: {factors.calculate_score():.2f}

{exploit_context}

{intent_context}

## Your Task

Construct a CONCRETE attack scenario. Think step by step:

1. What preconditions must be true for this attack to work?
2. What specific transactions would an attacker execute?
3. What tools/capital does the attacker need (flash loans, MEV, etc.)?
4. What would the attacker gain?
5. What might block this attack?

Respond in this JSON format:
{{
    "description": "<1-2 sentence attack summary>",
    "category": "<state_manipulation|access_bypass|economic|data_integrity|denial_of_service|cryptographic>",
    "preconditions": [
        {{
            "description": "<condition that must be true>",
            "how_to_satisfy": "<how attacker ensures this>",
            "blocks_if_false": true
        }}
    ],
    "attack_steps": [
        {{
            "order": 1,
            "description": "<what attacker does>",
            "function_call": "<e.g., 'withdraw(1000)'>",
            "transaction": "<pseudocode or detailed tx>",
            "requires": ["<precondition>"],
            "produces": ["<result>"]
        }}
    ],
    "postconditions": ["<what attacker achieves>"],
    "feasibility": "<trivial|moderate|complex|theoretical>",
    "feasibility_reasoning": "<why this feasibility level>",
    "economic": {{
        "estimated_profit": "<what attacker gains>",
        "required_capital": "<what attacker needs>",
        "break_even_point": "<when profitable>",
        "capital_at_risk": "<potential loss>",
        "time_sensitivity": "<timing constraints>",
        "competition_risk": "<MEV/frontrun risk>"
    }},
    "impact": "<critical|high|medium|low>",
    "evidence": ["<why this attack is viable>"],
    "blocking_factors": ["<what might prevent this>"],
    "confidence": <0.0-1.0>
}}

Be SPECIFIC and CONCRETE. Include actual function calls and parameter values.
If you cannot construct a viable attack, explain why in blocking_factors and set confidence low.
"""

    def _format_operations(self, node: "Node") -> str:
        """Format semantic operations for prompt."""
        props = node.properties
        ops = []

        operation_keys = [
            ("transfers_value_out", "TRANSFERS_VALUE_OUT"),
            ("reads_user_balance", "READS_USER_BALANCE"),
            ("writes_user_balance", "WRITES_USER_BALANCE"),
            ("calls_external", "CALLS_EXTERNAL"),
            ("reads_oracle_price", "READS_ORACLE"),
            ("writes_privileged_state", "MODIFIES_PRIVILEGED_STATE"),
            ("checks_permission", "CHECKS_PERMISSION"),
        ]

        for prop, name in operation_keys:
            if props.get(prop):
                ops.append(f"- {name}")

        return "\n".join(ops) if ops else "- No significant operations detected"

    def _format_exploits(self, exploits: List["ExploitRecord"]) -> str:
        """Format historical exploits for prompt."""
        lines = []
        for exp in exploits:
            lines.append(f"""
**{exp.name}** ({exp.date})
- Loss: ${exp.loss_usd:,}
- Summary: {exp.attack_summary}
- Key Steps: {exp.attack_steps[:3]}
- Root Cause: {exp.root_cause}
""")
        return "\n".join(lines)

    def _parse_attack_response(
        self,
        response: str,
        node: "Node",
        pattern: "AttackPattern",
        factors: ExploitabilityFactors,
    ) -> Optional[AttackConstruction]:
        """Parse LLM response into AttackConstruction."""
        import json
        import re

        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                return None

            data = json.loads(json_match.group())

            # Parse preconditions
            preconditions = []
            for i, p in enumerate(data.get("preconditions", [])):
                if isinstance(p, dict):
                    preconditions.append(AttackPrerequisite(
                        id=f"pre_{i}",
                        description=p.get("description", ""),
                        is_satisfied=None,
                        how_to_satisfy=p.get("how_to_satisfy"),
                        blocks_attack_if_false=p.get("blocks_if_false", True),
                    ))
                else:
                    preconditions.append(AttackPrerequisite(
                        id=f"pre_{i}",
                        description=str(p),
                        is_satisfied=None,
                        how_to_satisfy=None,
                    ))

            # Parse attack steps
            steps = []
            for s in data.get("attack_steps", []):
                steps.append(AttackStep(
                    order=s.get("order", len(steps) + 1),
                    description=s.get("description", ""),
                    transaction=s.get("transaction"),
                    function_call=s.get("function_call"),
                    requires=s.get("requires", []),
                    produces=s.get("produces", []),
                ))

            # Parse economic analysis
            econ_data = data.get("economic", {})
            economic = EconomicAnalysis(
                estimated_profit=econ_data.get("estimated_profit", "Unknown"),
                required_capital=econ_data.get("required_capital", "Unknown"),
                break_even_point=econ_data.get("break_even_point"),
                capital_at_risk=econ_data.get("capital_at_risk"),
                time_sensitivity=econ_data.get("time_sensitivity"),
                competition_risk=econ_data.get("competition_risk"),
            )

            # Map feasibility
            feasibility_map = {
                "trivial": AttackFeasibility.TRIVIAL,
                "moderate": AttackFeasibility.MODERATE,
                "complex": AttackFeasibility.COMPLEX,
                "theoretical": AttackFeasibility.THEORETICAL,
            }
            feasibility = feasibility_map.get(
                data.get("feasibility", "moderate").lower(),
                AttackFeasibility.MODERATE
            )

            # Map impact
            impact_map = {
                "critical": EconomicImpact.CRITICAL,
                "high": EconomicImpact.HIGH,
                "medium": EconomicImpact.MEDIUM,
                "low": EconomicImpact.LOW,
            }
            impact = impact_map.get(
                data.get("impact", "unknown").lower(),
                EconomicImpact.UNKNOWN
            )

            # Map category
            category_map = {
                "state_manipulation": AttackCategory.STATE_MANIPULATION,
                "access_bypass": AttackCategory.ACCESS_BYPASS,
                "economic": AttackCategory.ECONOMIC,
                "data_integrity": AttackCategory.DATA_INTEGRITY,
                "denial_of_service": AttackCategory.DENIAL_OF_SERVICE,
                "cryptographic": AttackCategory.CRYPTOGRAPHIC,
            }
            category = category_map.get(
                data.get("category", "state_manipulation").lower(),
                AttackCategory.STATE_MANIPULATION
            )

            # Calculate final exploitability
            exploitability = factors.calculate_score()

            # Adjust based on blocking factors
            blocking_count = len(data.get("blocking_factors", []))
            exploitability *= max(0.3, 1.0 - blocking_count * 0.1)

            return AttackConstruction(
                id=f"attack_{pattern.id}_{node.id}",
                target_function=node.label,
                pattern_used=pattern,
                pattern_id=pattern.id,
                category=category,
                description=data.get("description", ""),
                preconditions=preconditions,
                attack_steps=steps,
                postconditions=data.get("postconditions", []),
                feasibility=feasibility,
                feasibility_reasoning=data.get("feasibility_reasoning", ""),
                economic=economic,
                impact=impact,
                exploitability=exploitability,
                exploitability_breakdown={
                    "technical_feasibility": factors.technical_feasibility,
                    "guard_absence": factors.guard_absence,
                    "pattern_match_strength": factors.pattern_match_strength,
                    "economic_viability": factors.economic_viability,
                    "historical_precedent": factors.historical_precedent,
                },
                evidence=data.get("evidence", []),
                blocking_factors=data.get("blocking_factors", []),
                confidence=data.get("confidence", 0.5),
            )

        except (json.JSONDecodeError, KeyError) as e:
            return None

    def _generate_summary(self, attacks: List[AttackConstruction]) -> str:
        """Generate summary of attack findings."""
        if not attacks:
            return "No viable attacks constructed."

        high_severity = [a for a in attacks if a.exploitability > 0.7]
        medium_severity = [a for a in attacks if 0.4 < a.exploitability <= 0.7]
        low_severity = [a for a in attacks if a.exploitability <= 0.4]

        lines = [
            f"Constructed {len(attacks)} attack scenarios:",
            f"  - Critical/High: {len(high_severity)}",
            f"  - Medium: {len(medium_severity)}",
            f"  - Low: {len(low_severity)}",
        ]

        if high_severity:
            lines.append("\nMost exploitable attacks:")
            for a in high_severity[:3]:
                lines.append(f"  - {a.target_function}: {a.description[:50]}... (exp: {a.exploitability:.2f})")

        return "\n".join(lines)
```

---

## Success Criteria

- [ ] AttackConstruction dataclass complete with all fields
- [ ] Attack strategy selection based on node properties
- [ ] Attack synthesis working for reentrancy patterns
- [ ] Attack synthesis working for oracle manipulation patterns
- [ ] Attack synthesis working for access control patterns
- [ ] Links to historical exploits in output
- [ ] Exploitability scoring with transparent formula
- [ ] Economic impact analysis included
- [ ] Blocking factors correctly identified
- [ ] Confidence calibrated (high for obvious vulns, low for edge cases)

---

## Validation Tests

```python
import pytest
from true_vkg.agents.attacker import (
    AttackerAgent, AttackConstruction, AttackFeasibility,
    AttackCategory, EconomicImpact, ExploitabilityFactors
)


class TestAttackStrategySelection:
    """Test attack strategy selection based on node properties."""

    def test_reentrancy_selects_state_manipulation(self):
        """Reentrancy-prone code should select state manipulation strategy."""
        agent = AttackerAgent(mock_llm, adversarial_kg)

        node = create_node(properties={
            "state_write_after_external_call": True,
            "transfers_value_out": True,
        })

        strategies = agent._select_strategies(node)
        assert AttackCategory.STATE_MANIPULATION in strategies

    def test_missing_access_control_selects_bypass(self):
        """Missing access control should select access bypass strategy."""
        agent = AttackerAgent(mock_llm, adversarial_kg)

        node = create_node(properties={
            "writes_privileged_state": True,
            "has_access_gate": False,
        })

        strategies = agent._select_strategies(node)
        assert AttackCategory.ACCESS_BYPASS in strategies

    def test_oracle_reader_selects_data_integrity(self):
        """Oracle reading without staleness check should select data integrity."""
        agent = AttackerAgent(mock_llm, adversarial_kg)

        node = create_node(properties={
            "reads_oracle_price": True,
            "has_staleness_check": False,
        })

        strategies = agent._select_strategies(node)
        assert AttackCategory.DATA_INTEGRITY in strategies


class TestExploitabilityScoring:
    """Test exploitability score calculation."""

    def test_unprotected_reentrancy_high_score(self):
        """Unprotected reentrancy should have high exploitability."""
        factors = ExploitabilityFactors(
            technical_feasibility=1.0,  # No guards
            guard_absence=1.0,          # No protections
            pattern_match_strength=0.9, # Strong match
            economic_viability=0.8,     # Transfers value
            historical_precedent=0.8,   # DAO-style
        )

        score = factors.calculate_score()
        assert score > 0.8

    def test_protected_function_low_score(self):
        """Protected function should have low exploitability."""
        factors = ExploitabilityFactors(
            technical_feasibility=0.3,  # Guards present
            guard_absence=0.0,          # All protections active
            pattern_match_strength=0.5, # Partial match
            economic_viability=0.8,     # Transfers value
            historical_precedent=0.2,   # Few similar exploits
        )

        score = factors.calculate_score()
        assert score < 0.4


class TestAttackConstruction:
    """Test attack construction via LLM."""

    def test_construct_reentrancy_attack(self):
        """Test attack construction for reentrancy."""
        agent = AttackerAgent(llm_client, adversarial_kg)

        context = create_attacker_context(
            focal_nodes=["fn_withdraw_vuln"],
            patterns=[adversarial_kg.patterns["reentrancy_classic"]],
        )

        result = agent.analyze(context)

        assert len(result.findings) > 0
        attack = result.findings[0]

        # Should construct viable attack
        assert attack.feasibility in [AttackFeasibility.TRIVIAL, AttackFeasibility.MODERATE]
        assert len(attack.attack_steps) >= 2  # At least: call + re-enter
        assert attack.exploitability >= 0.7

        # Should have economic analysis
        assert attack.economic is not None
        assert attack.economic.estimated_profit != "Unknown"

    def test_attack_blocked_by_guard(self):
        """Test that protected functions get low-confidence attacks."""
        agent = AttackerAgent(llm_client, adversarial_kg)

        context = create_attacker_context(
            focal_nodes=["fn_withdraw_safe"],  # Has reentrancy guard
            patterns=[adversarial_kg.patterns["reentrancy_classic"]],
        )

        result = agent.analyze(context)

        if result.findings:
            attack = result.findings[0]
            # Should identify blocking factor
            assert len(attack.blocking_factors) > 0
            assert any(
                "guard" in b.lower() or "protected" in b.lower() or "nonReentrant" in b
                for b in attack.blocking_factors
            )
            # Low exploitability due to protection
            assert attack.exploitability < 0.5

    def test_attack_links_to_historical_exploits(self):
        """Test that attacks reference similar historical exploits."""
        agent = AttackerAgent(llm_client, adversarial_kg)

        context = create_attacker_context(
            focal_nodes=["fn_withdraw_vuln"],
            patterns=[adversarial_kg.patterns["reentrancy_classic"]],
        )

        result = agent.analyze(context)
        attack = result.findings[0]

        # Should reference DAO or similar
        assert len(attack.similar_exploits) > 0


class TestUltimateAttackerAgent:
    """Ultimate integration tests."""

    def test_ultimate_attacker_constructs_dao_exploit(self):
        """
        Ultimate test: Attacker agent constructs The DAO-style exploit.

        Given DAO-vulnerable code, should produce attack with:
        1. Flash loan or large balance precondition
        2. Call to vulnerable withdraw
        3. Fallback that re-enters
        4. Drain reasoning
        """
        agent = AttackerAgent(llm_client, adversarial_kg)

        # DAO-style vulnerable code
        context = create_context_from_code(DAO_VULNERABLE_CODE, ["withdraw"])
        context.patterns = [adversarial_kg.patterns["reentrancy_classic"]]

        result = agent.analyze(context)

        assert len(result.findings) > 0
        attack = result.findings[0]

        # Must be high exploitability
        assert attack.exploitability >= 0.7

        # Must have re-entrance step
        assert any(
            "re-enter" in step.description.lower() or
            "callback" in step.description.lower() or
            "fallback" in step.description.lower()
            for step in attack.attack_steps
        )

        # Must mention draining funds
        assert any(
            "drain" in p.lower() or "steal" in p.lower() or "all" in p.lower()
            for p in attack.postconditions
        )

        # Must reference DAO
        assert any("dao" in exp.lower() for exp in attack.similar_exploits)

        # Must have concrete steps
        assert all(step.description for step in attack.attack_steps)
        assert len(attack.attack_steps) >= 2

        print("SUCCESS: Attacker constructed DAO-style exploit")
        print(f"Attack: {attack.description}")
        print(f"Exploitability: {attack.exploitability:.2f}")
        print(f"Steps: {[s.description for s in attack.attack_steps]}")

    def test_attacker_constructs_oracle_manipulation(self):
        """Test oracle manipulation attack construction."""
        agent = AttackerAgent(llm_client, adversarial_kg)

        context = create_context_from_code(ORACLE_VULNERABLE_CODE, ["getPrice"])
        context.patterns = [adversarial_kg.patterns["oracle_manipulation"]]

        result = agent.analyze(context)

        assert len(result.findings) > 0
        attack = result.findings[0]

        # Should identify oracle manipulation opportunity
        assert attack.category == AttackCategory.DATA_INTEGRITY
        assert any("price" in step.description.lower() or "oracle" in step.description.lower()
                   for step in attack.attack_steps)

    def test_attacker_respects_gas_limits(self):
        """Test that complex attacks note gas constraints."""
        agent = AttackerAgent(llm_client, adversarial_kg)

        context = create_context_from_code(LOOP_BASED_CODE, ["processMany"])
        context.patterns = [adversarial_kg.patterns["unbounded_loop"]]

        result = agent.analyze(context)

        if result.findings:
            attack = result.findings[0]
            # Should mention gas in preconditions or blocking factors
            has_gas_consideration = any(
                "gas" in str(p).lower() for p in attack.preconditions
            ) or any(
                "gas" in b.lower() for b in attack.blocking_factors
            )
            # Note: This may not always apply, depends on attack type


# Test fixtures
DAO_VULNERABLE_CODE = '''
contract Vulnerable {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        (bool success,) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= amount;
    }
}
'''

ORACLE_VULNERABLE_CODE = '''
contract OracleConsumer {
    IOracle public oracle;

    function getPrice() external view returns (uint256) {
        // No staleness check - vulnerable to stale prices
        (, int256 price,,,) = oracle.latestRoundData();
        return uint256(price);
    }
}
'''

LOOP_BASED_CODE = '''
contract LoopVulnerable {
    address[] public users;

    function processMany() external {
        // Unbounded loop - potential DoS
        for (uint i = 0; i < users.length; i++) {
            payable(users[i]).transfer(1 ether);
        }
    }
}
'''
```

---

## Integration Points

### Input From Other Tasks
- **P2-T1 Agent Router**: `AgentContext` with focal nodes and pattern matches
- **P0-T2 Adversarial KG**: Attack patterns and historical exploit database
- **P1-T2 LLM Intent Annotator**: Function intent (trust assumptions to violate)

### Output To Other Tasks
- **P2-T3 Defender Agent**: `AttackConstruction` claims to rebut
- **P2-T4 LLMDFA Verifier**: Attack paths to formally verify
- **P2-T5 Adversarial Arbiter**: Attack findings for verdict decision

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
| 2026-01-03 | Enhanced with attack strategies, exploitability scoring, economic analysis, comprehensive tests | Claude |
