# [P2-T3] Defender Agent

**Phase**: 2 - Adversarial Agents
**Task ID**: P2-T3
**Status**: NOT_STARTED
**Priority**: CRITICAL
**Estimated Effort**: 3-4 days
**Actual Effort**: -

---

## Executive Summary

Implement the **Defender Agent** that argues for safety - actively looking for reasons why code is NOT vulnerable. This creates the adversarial debate that produces high-quality verdicts. The defender uses specifications from the Domain KG, analyzes guards/protections, and generates evidence-based rebuttals to attacker claims.

**Research Basis**: Adversarial debate in LLMs (Irving et al.) shows that having explicit attacker and defender perspectives produces more accurate conclusions than single-perspective analysis.

**Key Innovation**: Defender doesn't just check for guards - it actively constructs counter-arguments to attacker claims, citing specific code patterns and spec compliance as evidence.

---

## Dependencies

### Required Before Starting
- [ ] [P2-T1] Agent Router - Provides context
- [ ] [P0-T1] Domain Knowledge Graph - Provides specs for compliance checking
- [ ] [P2-T2] Attacker Agent - Receives attacker claims to rebut

### Blocks These Tasks
- [P2-T5] Adversarial Arbiter - Uses defender findings to make verdicts

---

## Objectives

### Primary Objectives
1. Implement `DefenderAgent` class that argues for safety
2. Create defense arguments based on specifications compliance
3. Identify and catalog all guards, mitigations, and protections
4. Generate evidence-based rebuttals to specific attacker claims
5. Quantify defense strength with transparent reasoning

### Stretch Goals
1. Proactive defense suggestions (what WOULD make code safe)
2. Historical defense patterns from audits
3. Defense score breakdown by category

---

## Success Criteria

### Must Have (Definition of Done)
- [ ] `DefenseArgument` dataclass with evidence and strength
- [ ] Guard detection: reentrancy, access control, CEI pattern, pausable
- [ ] Spec compliance checking with Domain KG
- [ ] Rebuttal generation for attacker claims
- [ ] Defense strength quantification (0.0-1.0)
- [ ] 95%+ test coverage
- [ ] Documentation in docs/reference/defender-agent.md

### Should Have
- [ ] Multiple defense types per vulnerability
- [ ] Unsatisfiable precondition detection
- [ ] Defense category breakdown

### Nice to Have
- [ ] Proactive defense suggestions
- [ ] Defense pattern library

---

## Technical Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DEFENDER AGENT ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   INPUT                                                                          │
│   ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐        │
│   │   AgentContext     │  │   Attacker         │  │   Domain KG        │        │
│   │   (from Router)    │  │   Results          │  │   (Specs)          │        │
│   │   - focal_nodes    │  │   (if available)   │  │   - ERC specs      │        │
│   │   - subgraph       │  │                    │  │   - invariants     │        │
│   └─────────┬──────────┘  └─────────┬──────────┘  └─────────┬──────────┘        │
│             │                       │                       │                    │
│             └───────────────────────┼───────────────────────┘                    │
│                                     │                                            │
│   DEFENSE ANALYSIS ═══════════════════════════════════════════════════════════  │
│                                     │                                            │
│   ┌─────────────────────────────────▼─────────────────────────────────────────┐ │
│   │                      GUARD ANALYZER                                        │ │
│   │                                                                            │ │
│   │   Checks:                         Detects:                                 │ │
│   │   ├── has_reentrancy_guard ────► nonReentrant modifier                    │ │
│   │   ├── has_access_gate ─────────► onlyOwner, role checks                   │ │
│   │   ├── behavioral_signature ────► CEI pattern compliance                   │ │
│   │   ├── has_pause_mechanism ─────► Pausable contract                        │ │
│   │   ├── uses_safe_erc20 ─────────► SafeTransfer usage                       │ │
│   │   └── input_validation ────────► require/revert checks                    │ │
│   │                                                                            │ │
│   └─────────────────────────────────┬─────────────────────────────────────────┘ │
│                                     │                                            │
│   ┌─────────────────────────────────▼─────────────────────────────────────────┐ │
│   │                    SPEC COMPLIANCE CHECKER                                 │ │
│   │                                                                            │ │
│   │   For each function:                                                       │ │
│   │   1. Find matching specs from Domain KG                                   │ │
│   │   2. Check IMPLEMENTS edges                                               │ │
│   │   3. Verify invariants are preserved                                      │ │
│   │   4. Check no VIOLATES edges exist                                        │ │
│   │                                                                            │ │
│   └─────────────────────────────────┬─────────────────────────────────────────┘ │
│                                     │                                            │
│   ┌─────────────────────────────────▼─────────────────────────────────────────┐ │
│   │                      REBUTTAL GENERATOR                                    │ │
│   │                      (if attacker claims exist)                            │ │
│   │                                                                            │ │
│   │   Rebuttal Strategies:                                                    │ │
│   │   ├── GUARD_BLOCKS: "nonReentrant prevents callback exploitation"        │ │
│   │   ├── PRECONDITION_FALSE: "attacker cannot satisfy require(balance > 0)" │ │
│   │   ├── INVARIANT_PRESERVED: "balance accounting prevents double-spend"    │ │
│   │   └── SPEC_COMPLIANT: "implementation follows ERC4626 correctly"         │ │
│   │                                                                            │ │
│   └─────────────────────────────────┬─────────────────────────────────────────┘ │
│                                     │                                            │
│   OUTPUT                            ▼                                            │
│   ┌────────────────────────────────────────────────────────────────────────┐    │
│   │  AgentResult                                                            │    │
│   │    ├── agent_type: DEFENDER                                            │    │
│   │    ├── findings: List[DefenseArgument]                                 │    │
│   │    ├── confidence: float (aggregated defense strength)                 │    │
│   │    └── summary: str                                                    │    │
│   └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Guard Strength Ratings

Evidence-based strength ratings for different guard types:

| Guard Type | Strength | Rationale |
|------------|----------|-----------|
| ReentrancyGuard | 0.95 | Proven effective, widely audited |
| onlyOwner | 0.85 | Strong when ownership is secure |
| AccessControl (roles) | 0.85 | Enterprise-grade pattern |
| CEI Pattern | 0.80 | Prevents reentrancy structurally |
| SafeERC20 | 0.90 | Handles edge cases in token transfers |
| Pausable | 0.70 | Reactive (emergency), not preventive |
| Input validation | 0.60 | Depends on what's validated |

### Key Data Structures

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


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
    evidence: List[str]
    blocks_attacks: List[str]


@dataclass
class Rebuttal:
    """A rebuttal to an attacker claim."""
    attack_id: str
    attack_description: str
    strategy: RebuttalStrategy
    claim: str
    evidence: List[str]
    unsatisfiable_preconditions: List[str]
    blocking_guards: List[str]
    strength: float
    reasoning: str


@dataclass
class DefenseArgument:
    """An argument for why code is safe."""
    id: str
    claim: str
    defense_type: DefenseType

    # Evidence
    evidence: List[str]
    guards_identified: List[GuardInfo]
    spec_references: List[str]

    # Strength
    strength: float
    strength_reasoning: str
    strength_factors: Dict[str, float]

    # Rebuttal info
    rebuts_attack: Optional[str]
    rebuttal: Optional[Rebuttal]


class DefenderAgent:
    """
    Agent that argues for safety.

    Analyzes code from defensive perspective:
    1. What protections exist?
    2. What specifications are correctly implemented?
    3. What invariants are preserved?
    4. Why are attacker claims wrong?
    """

    GUARD_STRENGTHS = {
        "reentrancy_guard": 0.95,
        "onlyOwner": 0.85,
        "role_based": 0.85,
        "pausable": 0.70,
        "cei_pattern": 0.80,
        "safe_erc20": 0.90,
        "input_validation": 0.60,
    }

    GUARD_PROTECTIONS = {
        "reentrancy_guard": ["reentrancy_classic", "reentrancy_cross_function"],
        "onlyOwner": ["unauthorized_access", "privilege_escalation"],
        "role_based": ["unauthorized_access", "privilege_escalation"],
        "pausable": ["emergency_drain", "exploit_ongoing"],
        "cei_pattern": ["reentrancy_classic"],
        "safe_erc20": ["unchecked_return", "non_standard_erc20"],
    }

    def __init__(self, llm_client, domain_kg: "DomainKnowledgeGraph"):
        self.llm = llm_client
        self.domain_kg = domain_kg

    def analyze(self, context: "AgentContext") -> "AgentResult":
        """Analyze from defender perspective."""
        defenses = []

        for node_id in context.focal_nodes:
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
            if context.upstream_results:
                rebuttals = self._generate_rebuttals(node, context)
                defenses.extend(rebuttals)

        return AgentResult(
            agent_type=AgentType.DEFENDER,
            findings=defenses,
            confidence=self._compute_overall_defense_strength(defenses),
            summary=self._generate_summary(defenses),
        )

    def _analyze_guards(self, node: "Node", context: "AgentContext") -> List[DefenseArgument]:
        """Identify security guards and protections."""
        guards = []

        # Check reentrancy guard
        if node.properties.get("has_reentrancy_guard"):
            guards.append(self._create_guard_defense(
                node, "reentrancy_guard", "nonReentrant",
                "Function is protected against reentrancy attacks"
            ))

        # Check access control
        if node.properties.get("has_access_gate"):
            modifiers = node.properties.get("modifiers", [])
            guard_type = "role_based" if any("role" in m.lower() for m in modifiers) else "onlyOwner"
            guards.append(self._create_guard_defense(
                node, guard_type, ", ".join(modifiers),
                "Function has access control restricting callers"
            ))

        # Check CEI pattern
        if self._follows_cei_pattern(node):
            guards.append(DefenseArgument(
                id=f"guard_cei_{node.id}",
                claim="Function follows Checks-Effects-Interactions pattern",
                defense_type=DefenseType.CEI_PATTERN,
                evidence=["State updates before external calls"],
                guards_identified=[GuardInfo(
                    guard_type="cei_pattern", name="CEI",
                    strength=0.80, evidence=["State before call"],
                    blocks_attacks=["reentrancy_classic"]
                )],
                spec_references=[],
                strength=0.80,
                strength_reasoning="CEI prevents reentrancy structurally",
                strength_factors={"pattern_compliance": 0.80},
                rebuts_attack=None,
                rebuttal=None,
            ))

        # Check SafeERC20
        if node.properties.get("uses_safe_erc20"):
            guards.append(self._create_guard_defense(
                node, "safe_erc20", "SafeERC20",
                "Function uses SafeERC20 for token transfers"
            ))

        return guards

    def _follows_cei_pattern(self, node: "Node") -> bool:
        """Check if behavioral signature follows CEI pattern."""
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

        return last_write_idx < first_external_idx

    def _create_guard_defense(self, node, guard_type, name, claim):
        """Create a guard-based defense argument."""
        strength = self.GUARD_STRENGTHS.get(guard_type, 0.5)
        return DefenseArgument(
            id=f"guard_{guard_type}_{node.id}",
            claim=claim,
            defense_type=DefenseType.GUARD_PRESENT,
            evidence=[f"{name} detected"],
            guards_identified=[GuardInfo(
                guard_type=guard_type, name=name,
                strength=strength, evidence=[f"{name} present"],
                blocks_attacks=self.GUARD_PROTECTIONS.get(guard_type, [])
            )],
            spec_references=[],
            strength=strength,
            strength_reasoning=f"{name} is a proven protective mechanism",
            strength_factors={"guard_strength": strength},
            rebuts_attack=None,
            rebuttal=None,
        )

    def _check_spec_compliance(self, node: "Node", context: "AgentContext") -> List[DefenseArgument]:
        """Check if function complies with specifications."""
        defenses = []

        for spec in context.specs:
            implements_edges = [
                e for e in context.cross_edges
                if e.source_id == node.id and e.target_id == spec.id
                and e.relation == CrossGraphRelation.IMPLEMENTS
            ]

            violates_edges = [
                e for e in context.cross_edges
                if e.source_id == node.id and e.target_id == spec.id
                and e.relation == CrossGraphRelation.VIOLATES
            ]

            if implements_edges and not violates_edges:
                defenses.append(DefenseArgument(
                    id=f"spec_compliance_{node.id}_{spec.id}",
                    claim=f"Function correctly implements {spec.name}",
                    defense_type=DefenseType.SPEC_COMPLIANT,
                    evidence=[f"IMPLEMENTS edge, no violations"],
                    guards_identified=[],
                    spec_references=[spec.id],
                    strength=0.80,
                    strength_reasoning="Spec compliance indicates correctness",
                    strength_factors={"implements": 0.4, "no_violations": 0.4},
                    rebuts_attack=None,
                    rebuttal=None,
                ))

        return defenses

    def _check_safe_patterns(self, node: "Node", context: "AgentContext") -> List[DefenseArgument]:
        """Check for known safe coding patterns."""
        defenses = []

        # Pull payment pattern
        if self._uses_pull_pattern(node):
            defenses.append(DefenseArgument(
                id=f"pattern_pull_{node.id}",
                claim="Uses pull payment pattern",
                defense_type=DefenseType.INVARIANT_PRESERVED,
                evidence=["User pulls funds, no push"],
                guards_identified=[],
                spec_references=[],
                strength=0.75,
                strength_reasoning="Pull pattern reduces reentrancy surface",
                strength_factors={"pattern_safety": 0.75},
                rebuts_attack=None,
                rebuttal=None,
            ))

        return defenses

    def _uses_pull_pattern(self, node: "Node") -> bool:
        """Check if function uses pull payment pattern."""
        label = node.label.lower()
        return ("withdraw" in label or "claim" in label) and \
               node.properties.get("reads_user_balance", False)

    def _generate_rebuttals(self, node: "Node", context: "AgentContext") -> List[DefenseArgument]:
        """Generate rebuttals to attacker claims."""
        rebuttals = []

        for upstream in context.upstream_results:
            if upstream.agent_type != AgentType.ATTACKER:
                continue

            for attack in upstream.findings:
                # Strategy 1: Check if guards block attack
                blocking_guards = self._find_blocking_guards(node, attack)
                if blocking_guards:
                    rebuttals.append(self._create_guard_rebuttal(node, attack, blocking_guards))
                    continue

                # Strategy 2: Check unsatisfiable preconditions
                unsatisfiable = self._find_unsatisfiable_preconditions(node, attack)
                if unsatisfiable:
                    rebuttals.append(self._create_precondition_rebuttal(node, attack, unsatisfiable))
                    continue

                # Strategy 3: Use LLM for complex rebuttal
                llm_rebuttal = self._llm_generate_rebuttal(node, attack, context)
                if llm_rebuttal:
                    rebuttals.append(llm_rebuttal)

        return rebuttals

    def _find_blocking_guards(self, node: "Node", attack) -> List[GuardInfo]:
        """Find guards that would block this attack."""
        blocking = []
        pattern_id = attack.pattern_used.id if attack.pattern_used else ""

        for guard_type, blocked_patterns in self.GUARD_PROTECTIONS.items():
            if pattern_id in blocked_patterns and self._has_guard(node, guard_type):
                blocking.append(GuardInfo(
                    guard_type=guard_type, name=guard_type,
                    strength=self.GUARD_STRENGTHS.get(guard_type, 0.5),
                    evidence=[f"Blocks {pattern_id}"],
                    blocks_attacks=[pattern_id]
                ))

        return blocking

    def _has_guard(self, node: "Node", guard_type: str) -> bool:
        """Check if node has a specific guard type."""
        checks = {
            "reentrancy_guard": lambda n: n.properties.get("has_reentrancy_guard"),
            "onlyOwner": lambda n: n.properties.get("has_access_gate"),
            "role_based": lambda n: n.properties.get("has_access_gate"),
            "cei_pattern": lambda n: self._follows_cei_pattern(n),
            "safe_erc20": lambda n: n.properties.get("uses_safe_erc20"),
        }
        check = checks.get(guard_type)
        return check(node) if check else False

    def _create_guard_rebuttal(self, node, attack, blocking_guards):
        """Create rebuttal based on blocking guards."""
        guard_names = [g.name for g in blocking_guards]
        max_strength = max(g.strength for g in blocking_guards)

        return DefenseArgument(
            id=f"rebuttal_guard_{node.id}_{attack.id}",
            claim=f"Attack blocked by {', '.join(guard_names)}",
            defense_type=DefenseType.GUARD_PRESENT,
            evidence=[f"Guards {guard_names} block this attack pattern"],
            guards_identified=blocking_guards,
            spec_references=[],
            strength=max_strength,
            strength_reasoning="Guards designed to prevent this attack",
            strength_factors={"blocking_guards": max_strength},
            rebuts_attack=attack.id,
            rebuttal=Rebuttal(
                attack_id=attack.id,
                attack_description=attack.description,
                strategy=RebuttalStrategy.GUARD_BLOCKS,
                claim=f"Blocked by {guard_names}",
                evidence=[f"Guard {g.name}: {g.strength}" for g in blocking_guards],
                unsatisfiable_preconditions=[],
                blocking_guards=guard_names,
                strength=max_strength,
                reasoning="Guards prevent attack execution",
            ),
        )

    def _find_unsatisfiable_preconditions(self, node, attack) -> List[str]:
        """Find preconditions that cannot be satisfied."""
        unsatisfiable = []

        for precondition in attack.preconditions:
            p_lower = precondition.lower()
            if "no reentrancy guard" in p_lower and node.properties.get("has_reentrancy_guard"):
                unsatisfiable.append(precondition)
            elif "no access control" in p_lower and node.properties.get("has_access_gate"):
                unsatisfiable.append(precondition)
            elif "public function" in p_lower and node.properties.get("visibility") == "internal":
                unsatisfiable.append(precondition)

        return unsatisfiable

    def _create_precondition_rebuttal(self, node, attack, unsatisfiable):
        """Create rebuttal based on unsatisfiable preconditions."""
        return DefenseArgument(
            id=f"rebuttal_precond_{node.id}_{attack.id}",
            claim="Attack requires unsatisfiable preconditions",
            defense_type=DefenseType.PRECONDITION_UNSATISFIABLE,
            evidence=[f"Unsatisfiable: {unsatisfiable}"],
            guards_identified=[],
            spec_references=[],
            strength=0.85,
            strength_reasoning="Attack impossible without preconditions",
            strength_factors={"unsatisfiable": len(unsatisfiable) * 0.2},
            rebuts_attack=attack.id,
            rebuttal=Rebuttal(
                attack_id=attack.id,
                attack_description=attack.description,
                strategy=RebuttalStrategy.PRECONDITION_FALSE,
                claim="Preconditions cannot be met",
                evidence=unsatisfiable,
                unsatisfiable_preconditions=unsatisfiable,
                blocking_guards=[],
                strength=0.85,
                reasoning="Required conditions are false",
            ),
        )

    def _llm_generate_rebuttal(self, node, attack, context) -> Optional[DefenseArgument]:
        """Use LLM for complex rebuttal generation."""
        prompt = f"""You are defending this code against an attack claim.

Attack: {attack.description}
Pattern: {attack.pattern_used.name if attack.pattern_used else 'unknown'}
Preconditions: {attack.preconditions}

Function: {node.label}
Guards: {node.properties.get('modifiers', [])}
Has Reentrancy Guard: {node.properties.get('has_reentrancy_guard', False)}
Has Access Control: {node.properties.get('has_access_gate', False)}

Respond in JSON:
{{"has_defense": <true|false>, "claim": "<defense>", "evidence": ["<e1>"], "strength": <0.0-1.0>, "reasoning": "<why>"}}
"""
        response = self.llm.analyze(prompt, response_format="json")

        if response.get("has_defense") and response.get("strength", 0) > 0.3:
            return DefenseArgument(
                id=f"rebuttal_llm_{node.id}_{attack.id}",
                claim=response.get("claim", ""),
                defense_type=DefenseType.GUARD_PRESENT,
                evidence=response.get("evidence", []),
                guards_identified=[],
                spec_references=[],
                strength=response.get("strength", 0.5),
                strength_reasoning=response.get("reasoning", ""),
                strength_factors={"llm_analysis": response.get("strength", 0.5)},
                rebuts_attack=attack.id,
                rebuttal=Rebuttal(
                    attack_id=attack.id,
                    attack_description=attack.description,
                    strategy=RebuttalStrategy.GUARD_BLOCKS,
                    claim=response.get("claim", ""),
                    evidence=response.get("evidence", []),
                    unsatisfiable_preconditions=[],
                    blocking_guards=[],
                    strength=response.get("strength", 0.5),
                    reasoning=response.get("reasoning", ""),
                ),
            )
        return None

    def _compute_overall_defense_strength(self, defenses: List[DefenseArgument]) -> float:
        """Compute aggregated defense strength."""
        if not defenses:
            return 0.0

        rebuttals = [d for d in defenses if d.rebuts_attack]
        non_rebuttals = [d for d in defenses if not d.rebuts_attack]

        rebuttal_strength = sum(d.strength for d in rebuttals) / len(rebuttals) if rebuttals else 0
        defense_strength = sum(d.strength for d in non_rebuttals) / len(non_rebuttals) if non_rebuttals else 0

        if rebuttals and non_rebuttals:
            return 0.6 * rebuttal_strength + 0.4 * defense_strength
        return rebuttal_strength or defense_strength

    def _generate_summary(self, defenses: List[DefenseArgument]) -> str:
        """Generate human-readable summary."""
        if not defenses:
            return "No defenses identified"

        lines = [f"Defense Summary: {len(defenses)} arguments"]
        rebuttals = [d for d in defenses if d.rebuts_attack]
        if rebuttals:
            lines.append(f"Rebuttals: {len(rebuttals)}")
        return "\n".join(lines)
```

---

## Implementation Plan

### Phase 1: Data Structures (0.5 days)
- [ ] Create enums and dataclasses
- [ ] Write unit tests for data structures
- **Checkpoint**: Can create defense arguments

### Phase 2: Guard Analysis (1 day)
- [ ] Implement `_analyze_guards()`
- [ ] Implement `_follows_cei_pattern()`
- [ ] Write tests for each guard type
- **Checkpoint**: Detects all major guard types

### Phase 3: Spec & Pattern Checking (0.5 days)
- [ ] Implement `_check_spec_compliance()`
- [ ] Implement `_check_safe_patterns()`
- **Checkpoint**: Verifies spec compliance

### Phase 4: Rebuttal Generation (1.5 days)
- [ ] Implement `_generate_rebuttals()`
- [ ] Implement `_find_blocking_guards()`
- [ ] Implement `_find_unsatisfiable_preconditions()`
- [ ] Implement `_llm_generate_rebuttal()`
- **Checkpoint**: Generates rebuttals

### Phase 5: Integration (0.5 days)
- [ ] Integration tests with AttackerAgent
- [ ] Performance benchmarks
- **Checkpoint**: Full defender working

---

## Validation Tests

```python
def test_defender_identifies_reentrancy_guard():
    """Test defender finds reentrancy guard."""
    agent = DefenderAgent(llm_client, domain_kg)
    context = create_context(MockNode(has_reentrancy_guard=True))
    result = agent.analyze(context)

    guard_defenses = [d for d in result.findings if d.defense_type == DefenseType.GUARD_PRESENT]
    assert len(guard_defenses) > 0
    assert guard_defenses[0].strength >= 0.9

def test_defender_rebuts_attack_on_protected_function():
    """Test defender rebuts attacker claim on protected function."""
    attacker_result = AgentResult(
        agent_type=AgentType.ATTACKER,
        findings=[create_reentrancy_attack("fn_safe")],
    )

    context = create_context(
        MockNode(has_reentrancy_guard=True),
        upstream_results=[attacker_result],
    )

    result = DefenderAgent(llm_client, domain_kg).analyze(context)

    rebuttals = [d for d in result.findings if d.rebuts_attack is not None]
    assert len(rebuttals) > 0
    assert rebuttals[0].strength > 0.7

def test_ultimate_defender_protects_safe_code():
    """Ultimate: Defender correctly defends safe code."""
    node = MockNode(
        has_reentrancy_guard=True,
        has_access_gate=True,
        behavioral_signature="R:bal→W:bal→X:out",  # CEI
    )

    attacker_result = AgentResult(
        agent_type=AgentType.ATTACKER,
        findings=[MockAttack(pattern_id="reentrancy_classic")],
    )

    result = DefenderAgent(llm_client, domain_kg).analyze(
        create_context(node, upstream_results=[attacker_result])
    )

    assert result.confidence > 0.8  # High confidence code is safe
    rebuttals = [d for d in result.findings if d.rebuts_attack]
    assert len(rebuttals) > 0
    assert rebuttals[0].rebuttal.strategy == RebuttalStrategy.GUARD_BLOCKS
```

---

## Metrics & Measurement

| Metric | Target | Pass/Fail |
|--------|--------|-----------|
| Guard types detected | 6+ | - |
| Correct rebuttals on safe code | 90%+ | - |
| Defense strength accuracy | 85%+ | - |
| Analysis time per function | <500ms | - |

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
| 2026-01-03 | Enhanced with full detail | Claude |
