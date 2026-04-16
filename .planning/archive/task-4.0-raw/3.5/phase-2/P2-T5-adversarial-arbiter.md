# [P2-T5] Adversarial Arbiter

**Phase**: 2 - Adversarial Agents
**Task ID**: P2-T5
**Status**: NOT_STARTED
**Priority**: CRITICAL
**Estimated Effort**: 3-4 days
**Actual Effort**: -

---

## Executive Summary

Implement the **Adversarial Arbiter** that judges attacker vs defender arguments using evidence from the verifier and cross-graph context. This produces final verdicts with high confidence by combining multiple evidence sources.

**Key Innovation**: Uses principled decision rules based on evidence types, not just confidence averaging. The arbiter acts as an impartial judge that weighs formal proofs above heuristics, while still considering cross-graph intelligence when formal methods are inconclusive.

---

## Architecture

```
                     ┌─────────────────────────────────────────────────────────┐
                     │                 AdversarialArbiter                      │
                     │                                                         │
  AttackerResult ───►│  ┌────────────────────────────────────────────────┐    │
                     │  │            Evidence Aggregator                  │    │
  DefenderResult ───►│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐        │    │
                     │  │  │Attacker │  │Defender │  │Verifier │        │    │
  VerifierResult ───►│  │  │Evidence │  │Evidence │  │Evidence │        │    │
                     │  │  └────┬────┘  └────┬────┘  └────┬────┘        │    │
  CrossGraphCtx ────►│  │       │            │            │              │    │
                     │  │       ▼            ▼            ▼              │    │
                     │  │  ┌────────────────────────────────────┐       │    │
                     │  │  │        Evidence Weight Matrix       │       │    │
                     │  │  │  ┌──────────────────────────────┐  │       │    │
                     │  │  │  │ FORMAL_PROOF:     1.0        │  │       │    │
                     │  │  │  │ CROSS_GRAPH:      0.8        │  │       │    │
                     │  │  │  │ GUARD_ANALYSIS:   0.7        │  │       │    │
                     │  │  │  │ PATTERN_MATCH:    0.6        │  │       │    │
                     │  │  │  │ BEHAVIORAL_SIG:   0.5        │  │       │    │
                     │  │  │  │ HEURISTIC:        0.3        │  │       │    │
                     │  │  │  └──────────────────────────────┘  │       │    │
                     │  │  └────────────────────────────────────┘       │    │
                     │  └──────────────────┬─────────────────────────────┘    │
                     │                     │                                   │
                     │                     ▼                                   │
                     │  ┌────────────────────────────────────────────────┐    │
                     │  │              Decision Engine                    │    │
                     │  │                                                 │    │
                     │  │  Priority Order:                                │    │
                     │  │  1. Formal proof (Z3)         → DEFINITIVE     │    │
                     │  │  2. Cross-graph + violation   → HIGH CONF      │    │
                     │  │  3. Guard strength analysis   → MODERATE       │    │
                     │  │  4. Pattern matching          → SUGGESTIVE     │    │
                     │  │  5. Behavioral signatures     → INDICATIVE     │    │
                     │  │  6. Heuristics only           → UNCERTAIN      │    │
                     │  │                                                 │    │
                     │  └──────────────────┬─────────────────────────────┘    │
                     │                     │                                   │
                     │                     ▼                                   │
                     │  ┌────────────────────────────────────────────────┐    │
                     │  │           Explanation Generator                 │    │
                     │  │                                                 │    │
                     │  │  Components:                                    │    │
                     │  │  - Verdict justification                        │    │
                     │  │  - Evidence breakdown                           │    │
                     │  │  - Attack/defense summary                       │    │
                     │  │  - Recommendations                              │    │
                     │  │                                                 │    │
                     │  └──────────────────┬─────────────────────────────┘    │
                     │                     │                                   │
                     └─────────────────────┼───────────────────────────────────┘
                                           │
                                           ▼
                               ┌───────────────────────┐
                               │  ArbitrationResult    │
                               │  - verdict            │
                               │  - confidence         │
                               │  - winning_side       │
                               │  - explanation        │
                               │  - evidence_chain     │
                               │  - recommendations    │
                               └───────────────────────┘
```

---

## Decision Matrix

The arbiter uses a **priority-based decision matrix** where higher-priority evidence types override lower ones:

### Evidence Priority Levels

| Level | Evidence Type | Confidence Range | Verdict Type | Example |
|-------|---------------|------------------|--------------|---------|
| **P1** | Formal Proof (Z3 SAT/UNSAT) | 0.95-1.0 | DEFINITIVE | Z3 proves path feasible |
| **P2** | Cross-Graph + Spec Violation | 0.80-0.90 | HIGH | VIOLATES edge + similar exploit |
| **P3** | Strong Guards Present | 0.70-0.85 | MODERATE | ReentrancyGuard + CEI pattern |
| **P4** | Pattern Match | 0.60-0.75 | SUGGESTIVE | Matches known vuln pattern |
| **P5** | Behavioral Signature | 0.50-0.65 | INDICATIVE | R:bal→X:out→W:bal ordering |
| **P6** | Heuristics Only | 0.30-0.50 | UNCERTAIN | Name-based, no semantic proof |

### Verdict Determination Rules

```
RULE 1: FORMAL_PROOF_FEASIBLE
  IF verifier.is_proven AND verifier.path_feasible
  THEN verdict = VULNERABLE, confidence = 0.95

RULE 2: FORMAL_PROOF_INFEASIBLE
  IF verifier.is_proven AND NOT verifier.path_feasible
  THEN verdict = SAFE, confidence = 0.90

RULE 3: CROSS_GRAPH_HIGH_SIGNAL
  IF cross_graph.has_violation AND cross_graph.has_similar_exploit AND NOT defender.has_strong_guard
  THEN verdict = LIKELY_VULNERABLE, confidence = cross_graph.composite_score

RULE 4: CROSS_GRAPH_VIOLATION_ONLY
  IF cross_graph.has_violation AND NOT cross_graph.has_similar_exploit
  THEN verdict = UNCERTAIN (with vuln bias), confidence = 0.6

RULE 5: STRONG_DEFENSE
  IF defender.overall_strength > 0.8 AND defender.has_multiple_guards
  THEN verdict = LIKELY_SAFE, confidence = defender.overall_strength

RULE 6: ATTACK_WITHOUT_DEFENSE
  IF attacker.has_valid_attack AND defender.overall_strength < 0.4
  THEN verdict = LIKELY_VULNERABLE, confidence = 0.7

RULE 7: CONTESTED
  IF attacker.confidence > 0.6 AND defender.confidence > 0.6
  THEN verdict = UNCERTAIN, requires_manual_review = True

RULE 8: INSUFFICIENT_EVIDENCE
  DEFAULT verdict = UNCERTAIN, confidence = 0.5
```

### Confidence Calculation Formula

```python
def calculate_final_confidence(
    attacker: AgentResult,
    defender: AgentResult,
    verifier: Optional[VerificationResult],
    cross_context: List[VulnerabilityCandidate],
) -> float:
    """
    Calculate final confidence using weighted evidence.

    Formula:
    confidence = Σ(evidence_weight × evidence_strength) / Σ(evidence_weight)

    With adjustments:
    - Formal proof: overrides all others (confidence = proof_confidence)
    - Conflicting evidence: reduces confidence by conflict_penalty
    - Multiple concordant signals: bonus of 0.05 per additional signal
    """

    weights = {
        "formal_proof": 1.0,
        "cross_graph": 0.8,
        "guard_analysis": 0.7,
        "pattern_match": 0.6,
        "behavioral": 0.5,
        "heuristic": 0.3,
    }

    # Start with base from decision rule
    base_confidence = rule_confidence

    # Apply concordance bonus
    concordant_signals = count_signals_agreeing_with_verdict(...)
    concordance_bonus = min(0.15, concordant_signals * 0.05)

    # Apply conflict penalty
    conflicting_signals = count_signals_opposing_verdict(...)
    conflict_penalty = min(0.20, conflicting_signals * 0.10)

    return clamp(base_confidence + concordance_bonus - conflict_penalty, 0.0, 1.0)
```

---

## Dependencies

### Required Before Starting
- [ ] [P2-T2] Attacker Agent - Provides attack constructions to evaluate
- [ ] [P2-T3] Defender Agent - Provides defense arguments to evaluate
- [ ] [P2-T4] LLMDFA Verifier - Provides formal verification results
- [ ] [P0-T3] Cross-Graph Linker - Provides cross-graph context

### Blocks These Tasks
- Phase 2 completion gate
- [P3-T1] Iterative Reasoning Engine (uses arbiter for verdicts)
- [P3-T2] Causal Reasoning Engine (uses verdicts as targets)

---

## Objectives

1. Implement verdict decision rules with clear priority
2. Create evidence aggregation with weighted scoring
3. Handle contested cases and uncertainty
4. Generate human-readable explanations with evidence chains
5. Support appeal/re-arbitration with new evidence

---

## Technical Design

### Key Data Structures

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import json


class Verdict(Enum):
    """Final verdict on vulnerability status."""
    VULNERABLE = "vulnerable"           # Confirmed vulnerable (formal proof or overwhelming evidence)
    LIKELY_VULNERABLE = "likely_vulnerable"  # Strong evidence of vulnerability
    UNCERTAIN = "uncertain"             # Insufficient evidence either way
    LIKELY_SAFE = "likely_safe"         # Strong evidence of safety
    SAFE = "safe"                       # Confirmed safe (formal proof or overwhelming defense)


class EvidenceType(Enum):
    """Types of evidence with associated weights."""
    FORMAL_PROOF = "formal_proof"           # Z3 SAT/UNSAT
    CROSS_GRAPH_VIOLATION = "cross_graph_violation"  # VIOLATES edge
    CROSS_GRAPH_EXPLOIT = "cross_graph_exploit"      # Similar exploit in DB
    GUARD_PRESENT = "guard_present"         # Security guard detected
    PATTERN_MATCH = "pattern_match"         # Vuln pattern matched
    BEHAVIORAL_SIGNATURE = "behavioral_sig"  # Operation ordering
    SPEC_COMPLIANCE = "spec_compliance"     # Implements spec correctly
    HEURISTIC = "heuristic"                 # Name-based, no semantic proof


class EvidenceDirection(Enum):
    """Which side this evidence supports."""
    SUPPORTS_ATTACKER = "supports_attacker"
    SUPPORTS_DEFENDER = "supports_defender"
    NEUTRAL = "neutral"


EVIDENCE_WEIGHTS: Dict[EvidenceType, float] = {
    EvidenceType.FORMAL_PROOF: 1.0,
    EvidenceType.CROSS_GRAPH_VIOLATION: 0.8,
    EvidenceType.CROSS_GRAPH_EXPLOIT: 0.85,
    EvidenceType.GUARD_PRESENT: 0.7,
    EvidenceType.PATTERN_MATCH: 0.6,
    EvidenceType.BEHAVIORAL_SIGNATURE: 0.5,
    EvidenceType.SPEC_COMPLIANCE: 0.65,
    EvidenceType.HEURISTIC: 0.3,
}


@dataclass
class EvidenceItem:
    """A single piece of evidence for arbitration."""
    id: str
    evidence_type: EvidenceType
    direction: EvidenceDirection
    strength: float  # 0.0 to 1.0
    description: str
    source_agent: str  # "attacker", "defender", "verifier", "cross_graph"
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def weighted_strength(self) -> float:
        """Get strength weighted by evidence type."""
        return self.strength * EVIDENCE_WEIGHTS[self.evidence_type]


@dataclass
class EvidenceChain:
    """Collection of evidence items supporting a position."""
    items: List[EvidenceItem] = field(default_factory=list)

    def add(self, item: EvidenceItem) -> None:
        self.items.append(item)

    def for_attacker(self) -> List[EvidenceItem]:
        return [e for e in self.items if e.direction == EvidenceDirection.SUPPORTS_ATTACKER]

    def for_defender(self) -> List[EvidenceItem]:
        return [e for e in self.items if e.direction == EvidenceDirection.SUPPORTS_DEFENDER]

    def weighted_sum(self, direction: EvidenceDirection) -> float:
        """Calculate weighted sum for a direction."""
        relevant = [e for e in self.items if e.direction == direction]
        if not relevant:
            return 0.0
        return sum(e.weighted_strength for e in relevant)

    def has_formal_proof(self) -> bool:
        return any(e.evidence_type == EvidenceType.FORMAL_PROOF for e in self.items)

    def strongest_evidence(self) -> Optional[EvidenceItem]:
        """Get the strongest piece of evidence."""
        if not self.items:
            return None
        return max(self.items, key=lambda e: e.weighted_strength)


@dataclass
class Recommendation:
    """Recommendation based on verdict."""
    action: str  # "fix", "review", "verify", "accept"
    priority: str  # "critical", "high", "medium", "low"
    description: str
    suggested_fix: Optional[str] = None


@dataclass
class ArbitrationResult:
    """Complete result of adversarial arbitration."""
    # Core verdict
    verdict: Verdict
    confidence: float

    # Winner determination
    winning_side: str  # "attacker", "defender", "neither"
    winning_argument: str

    # Evidence breakdown
    evidence_chain: EvidenceChain
    attacker_evidence_score: float
    defender_evidence_score: float

    # Decision metadata
    decision_rule_used: str
    requires_manual_review: bool = False

    # Cross-graph context
    violated_specs: List[str] = field(default_factory=list)
    similar_exploits: List[str] = field(default_factory=list)

    # Human explanation
    explanation: str = ""
    detailed_breakdown: Dict[str, Any] = field(default_factory=dict)

    # Actionable output
    recommendations: List[Recommendation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        return {
            "verdict": self.verdict.value,
            "confidence": round(self.confidence, 3),
            "winning_side": self.winning_side,
            "winning_argument": self.winning_argument,
            "decision_rule": self.decision_rule_used,
            "requires_review": self.requires_manual_review,
            "attacker_score": round(self.attacker_evidence_score, 3),
            "defender_score": round(self.defender_evidence_score, 3),
            "violated_specs": self.violated_specs,
            "similar_exploits": self.similar_exploits,
            "explanation": self.explanation,
            "recommendations": [
                {"action": r.action, "priority": r.priority, "description": r.description}
                for r in self.recommendations
            ],
        }


class AdversarialArbiter:
    """
    Judges attacker vs defender using evidence-based rules.

    Decision Rules (priority order):
    1. If verifier PROVES path feasible → VULNERABLE (confidence 0.95)
    2. If verifier PROVES path infeasible → SAFE (confidence 0.90)
    3. If cross-graph shows violation + similar exploit + no mitigation → LIKELY_VULNERABLE
    4. If cross-graph shows violation only → UNCERTAIN (with vuln bias)
    5. If defender has strong guards (>0.8) → LIKELY_SAFE
    6. If attacker has valid attack + weak defense (<0.4) → LIKELY_VULNERABLE
    7. If both sides have strong arguments → UNCERTAIN (requires manual review)
    8. Default → UNCERTAIN
    """

    # Thresholds for decision making
    FORMAL_PROOF_CONFIDENCE = 0.95
    FORMAL_DISPROOF_CONFIDENCE = 0.90
    HIGH_CROSS_GRAPH_CONFIDENCE = 0.80
    STRONG_DEFENSE_THRESHOLD = 0.8
    WEAK_DEFENSE_THRESHOLD = 0.4
    CONTEST_THRESHOLD = 0.6

    def __init__(self, linker: "CrossGraphLinker"):
        self.linker = linker

    def arbitrate(
        self,
        attacker_result: "AgentResult",
        defender_result: "AgentResult",
        verifier_result: Optional["VerificationResult"],
        focal_node: str,
    ) -> ArbitrationResult:
        """
        Arbitrate between attacker and defender.

        Args:
            attacker_result: Result from AttackerAgent
            defender_result: Result from DefenderAgent
            verifier_result: Result from LLMDFA Verifier (may be None)
            focal_node: The node being evaluated

        Returns:
            ArbitrationResult with verdict, confidence, and explanation
        """
        # Step 1: Gather all evidence
        evidence_chain = self._gather_evidence(
            attacker_result, defender_result, verifier_result, focal_node
        )

        # Step 2: Get cross-graph context
        cross_context = self.linker.query_vulnerabilities(focal_node)

        # Step 3: Apply decision rules
        result = self._apply_decision_rules(
            evidence_chain,
            attacker_result,
            defender_result,
            verifier_result,
            cross_context,
        )

        # Step 4: Generate explanation
        result.explanation = self._generate_explanation(result)
        result.detailed_breakdown = self._generate_breakdown(result, evidence_chain)

        # Step 5: Generate recommendations
        result.recommendations = self._generate_recommendations(result)

        return result

    def _gather_evidence(
        self,
        attacker: "AgentResult",
        defender: "AgentResult",
        verifier: Optional["VerificationResult"],
        focal_node: str,
    ) -> EvidenceChain:
        """Collect and normalize all evidence into an EvidenceChain."""
        chain = EvidenceChain()

        # Attacker evidence
        for i, attack in enumerate(attacker.findings):
            chain.add(EvidenceItem(
                id=f"atk_{i}",
                evidence_type=self._classify_attack_evidence(attack),
                direction=EvidenceDirection.SUPPORTS_ATTACKER,
                strength=attack.exploitability,
                description=attack.description,
                source_agent="attacker",
                raw_data={"attack": attack.__dict__},
            ))

        # Defender evidence
        for i, defense in enumerate(defender.findings):
            chain.add(EvidenceItem(
                id=f"def_{i}",
                evidence_type=self._classify_defense_evidence(defense),
                direction=EvidenceDirection.SUPPORTS_DEFENDER,
                strength=defense.strength,
                description=defense.claim,
                source_agent="defender",
                raw_data={"defense": defense.__dict__},
            ))

        # Verifier evidence (highest priority)
        if verifier and verifier.is_proven:
            direction = (
                EvidenceDirection.SUPPORTS_ATTACKER
                if verifier.path_feasible
                else EvidenceDirection.SUPPORTS_DEFENDER
            )
            chain.add(EvidenceItem(
                id="verifier_proof",
                evidence_type=EvidenceType.FORMAL_PROOF,
                direction=direction,
                strength=1.0,  # Formal proofs are definitive
                description=f"Z3 {'proved' if verifier.path_feasible else 'disproved'} attack path",
                source_agent="verifier",
                raw_data={"verifier": verifier.__dict__},
            ))

        # Cross-graph evidence
        cross_evidence = self._gather_cross_graph_evidence(focal_node)
        for e in cross_evidence:
            chain.add(e)

        return chain

    def _gather_cross_graph_evidence(self, focal_node: str) -> List[EvidenceItem]:
        """Gather evidence from cross-graph relationships."""
        evidence = []

        # Check for VIOLATES edges
        violations = self.linker.get_violations(focal_node)
        for v in violations:
            evidence.append(EvidenceItem(
                id=f"violation_{v.spec_id}",
                evidence_type=EvidenceType.CROSS_GRAPH_VIOLATION,
                direction=EvidenceDirection.SUPPORTS_ATTACKER,
                strength=v.severity_score,
                description=f"Violates spec: {v.spec_name}",
                source_agent="cross_graph",
                raw_data={"violation": v.__dict__},
            ))

        # Check for similar exploits
        similar = self.linker.find_similar_exploits(focal_node)
        for s in similar:
            evidence.append(EvidenceItem(
                id=f"exploit_{s.exploit_id}",
                evidence_type=EvidenceType.CROSS_GRAPH_EXPLOIT,
                direction=EvidenceDirection.SUPPORTS_ATTACKER,
                strength=s.similarity_score,
                description=f"Similar to known exploit: {s.exploit_name}",
                source_agent="cross_graph",
                raw_data={"exploit": s.__dict__},
            ))

        # Check for IMPLEMENTS edges (defense)
        implementations = self.linker.get_implementations(focal_node)
        for impl in implementations:
            evidence.append(EvidenceItem(
                id=f"implements_{impl.spec_id}",
                evidence_type=EvidenceType.SPEC_COMPLIANCE,
                direction=EvidenceDirection.SUPPORTS_DEFENDER,
                strength=impl.compliance_score,
                description=f"Correctly implements: {impl.spec_name}",
                source_agent="cross_graph",
                raw_data={"implementation": impl.__dict__},
            ))

        return evidence

    def _classify_attack_evidence(self, attack: "AttackConstruction") -> EvidenceType:
        """Classify what type of evidence an attack represents."""
        if attack.has_formal_analysis:
            return EvidenceType.FORMAL_PROOF
        if attack.has_behavioral_sequence:
            return EvidenceType.BEHAVIORAL_SIGNATURE
        if attack.pattern_used:
            return EvidenceType.PATTERN_MATCH
        return EvidenceType.HEURISTIC

    def _classify_defense_evidence(self, defense: "DefenseArgument") -> EvidenceType:
        """Classify what type of evidence a defense represents."""
        if defense.argument_type == "guard_present":
            return EvidenceType.GUARD_PRESENT
        if defense.argument_type == "spec_compliant":
            return EvidenceType.SPEC_COMPLIANCE
        if defense.argument_type == "invariant_preserved":
            return EvidenceType.BEHAVIORAL_SIGNATURE
        return EvidenceType.HEURISTIC

    def _apply_decision_rules(
        self,
        evidence: EvidenceChain,
        attacker: "AgentResult",
        defender: "AgentResult",
        verifier: Optional["VerificationResult"],
        cross_context: List["VulnerabilityCandidate"],
    ) -> ArbitrationResult:
        """Apply priority-based decision rules to reach verdict."""

        attacker_score = evidence.weighted_sum(EvidenceDirection.SUPPORTS_ATTACKER)
        defender_score = evidence.weighted_sum(EvidenceDirection.SUPPORTS_DEFENDER)

        # RULE 1: Formal proof - path feasible → VULNERABLE
        if verifier and verifier.is_proven and verifier.path_feasible:
            return ArbitrationResult(
                verdict=Verdict.VULNERABLE,
                confidence=self.FORMAL_PROOF_CONFIDENCE,
                winning_side="attacker",
                winning_argument="Z3 formally proved attack path is feasible",
                evidence_chain=evidence,
                attacker_evidence_score=attacker_score,
                defender_evidence_score=defender_score,
                decision_rule_used="RULE_1_FORMAL_PROOF_FEASIBLE",
                violated_specs=self._extract_violations(cross_context),
                similar_exploits=self._extract_exploits(cross_context),
            )

        # RULE 2: Formal proof - path infeasible → SAFE
        if verifier and verifier.is_proven and not verifier.path_feasible:
            return ArbitrationResult(
                verdict=Verdict.SAFE,
                confidence=self.FORMAL_DISPROOF_CONFIDENCE,
                winning_side="defender",
                winning_argument="Z3 formally proved attack path is infeasible",
                evidence_chain=evidence,
                attacker_evidence_score=attacker_score,
                defender_evidence_score=defender_score,
                decision_rule_used="RULE_2_FORMAL_PROOF_INFEASIBLE",
            )

        # RULE 3: Cross-graph high signal (violation + exploit + no strong defense)
        has_violation = any(
            e.evidence_type == EvidenceType.CROSS_GRAPH_VIOLATION
            for e in evidence.for_attacker()
        )
        has_similar_exploit = any(
            e.evidence_type == EvidenceType.CROSS_GRAPH_EXPLOIT
            for e in evidence.for_attacker()
        )
        has_strong_defense = defender.confidence > self.STRONG_DEFENSE_THRESHOLD

        if has_violation and has_similar_exploit and not has_strong_defense:
            # Calculate composite confidence from cross-graph signals
            cross_signals = [
                e for e in evidence.for_attacker()
                if e.evidence_type in (EvidenceType.CROSS_GRAPH_VIOLATION, EvidenceType.CROSS_GRAPH_EXPLOIT)
            ]
            composite = sum(e.strength for e in cross_signals) / len(cross_signals)

            return ArbitrationResult(
                verdict=Verdict.LIKELY_VULNERABLE,
                confidence=min(0.90, self.HIGH_CROSS_GRAPH_CONFIDENCE + composite * 0.1),
                winning_side="attacker",
                winning_argument="Cross-graph shows spec violation + similar known exploit + no adequate defense",
                evidence_chain=evidence,
                attacker_evidence_score=attacker_score,
                defender_evidence_score=defender_score,
                decision_rule_used="RULE_3_CROSS_GRAPH_HIGH_SIGNAL",
                violated_specs=self._extract_violations(cross_context),
                similar_exploits=self._extract_exploits(cross_context),
            )

        # RULE 4: Cross-graph violation only → UNCERTAIN (with vuln bias)
        if has_violation and not has_similar_exploit:
            return ArbitrationResult(
                verdict=Verdict.UNCERTAIN,
                confidence=0.60,
                winning_side="attacker",  # Slight bias
                winning_argument="Spec violation detected but no similar known exploit",
                evidence_chain=evidence,
                attacker_evidence_score=attacker_score,
                defender_evidence_score=defender_score,
                decision_rule_used="RULE_4_CROSS_GRAPH_VIOLATION_ONLY",
                requires_manual_review=True,
                violated_specs=self._extract_violations(cross_context),
            )

        # RULE 5: Strong defense → LIKELY_SAFE
        if defender.confidence > self.STRONG_DEFENSE_THRESHOLD:
            strong_guards = [
                e for e in evidence.for_defender()
                if e.evidence_type == EvidenceType.GUARD_PRESENT and e.strength > 0.7
            ]
            if len(strong_guards) >= 1:
                return ArbitrationResult(
                    verdict=Verdict.LIKELY_SAFE,
                    confidence=defender.confidence,
                    winning_side="defender",
                    winning_argument=f"Strong guards present: {[g.description for g in strong_guards]}",
                    evidence_chain=evidence,
                    attacker_evidence_score=attacker_score,
                    defender_evidence_score=defender_score,
                    decision_rule_used="RULE_5_STRONG_DEFENSE",
                )

        # RULE 6: Attack without defense → LIKELY_VULNERABLE
        has_valid_attack = attacker.confidence > self.CONTEST_THRESHOLD
        weak_defense = defender.confidence < self.WEAK_DEFENSE_THRESHOLD

        if has_valid_attack and weak_defense:
            return ArbitrationResult(
                verdict=Verdict.LIKELY_VULNERABLE,
                confidence=0.70,
                winning_side="attacker",
                winning_argument="Valid attack construction with insufficient defense",
                evidence_chain=evidence,
                attacker_evidence_score=attacker_score,
                defender_evidence_score=defender_score,
                decision_rule_used="RULE_6_ATTACK_WITHOUT_DEFENSE",
            )

        # RULE 7: Contested (both sides have strong arguments)
        if attacker.confidence > self.CONTEST_THRESHOLD and defender.confidence > self.CONTEST_THRESHOLD:
            return ArbitrationResult(
                verdict=Verdict.UNCERTAIN,
                confidence=0.50,
                winning_side="neither",
                winning_argument="Both attacker and defender have strong arguments",
                evidence_chain=evidence,
                attacker_evidence_score=attacker_score,
                defender_evidence_score=defender_score,
                decision_rule_used="RULE_7_CONTESTED",
                requires_manual_review=True,
            )

        # RULE 8: Default - insufficient evidence
        return ArbitrationResult(
            verdict=Verdict.UNCERTAIN,
            confidence=0.50,
            winning_side="neither",
            winning_argument="Insufficient evidence for confident verdict",
            evidence_chain=evidence,
            attacker_evidence_score=attacker_score,
            defender_evidence_score=defender_score,
            decision_rule_used="RULE_8_INSUFFICIENT_EVIDENCE",
            requires_manual_review=True,
        )

    def _extract_violations(self, context: List["VulnerabilityCandidate"]) -> List[str]:
        """Extract violated spec names from context."""
        violations = []
        for c in context:
            if hasattr(c, 'violated_specs'):
                violations.extend(c.violated_specs)
        return list(set(violations))

    def _extract_exploits(self, context: List["VulnerabilityCandidate"]) -> List[str]:
        """Extract similar exploit names from context."""
        exploits = []
        for c in context:
            if hasattr(c, 'attack_patterns'):
                exploits.extend(c.attack_patterns)
        return list(set(exploits))

    def _generate_explanation(self, result: ArbitrationResult) -> str:
        """Generate human-readable explanation of the verdict."""
        explanations = {
            "RULE_1_FORMAL_PROOF_FEASIBLE": (
                f"**VERDICT: VULNERABLE** (Confidence: {result.confidence:.0%})\n\n"
                f"The Z3 constraint solver formally proved that the attack path is feasible. "
                f"This is definitive evidence that the vulnerability can be exploited.\n\n"
                f"**Winning Argument:** {result.winning_argument}\n\n"
                f"**Evidence:**\n"
                f"- Attacker evidence score: {result.attacker_evidence_score:.2f}\n"
                f"- Defender evidence score: {result.defender_evidence_score:.2f}\n"
            ),
            "RULE_2_FORMAL_PROOF_INFEASIBLE": (
                f"**VERDICT: SAFE** (Confidence: {result.confidence:.0%})\n\n"
                f"The Z3 constraint solver formally proved that the attack path is infeasible. "
                f"The constraints required for the attack cannot be satisfied.\n\n"
                f"**Winning Argument:** {result.winning_argument}\n"
            ),
            "RULE_3_CROSS_GRAPH_HIGH_SIGNAL": (
                f"**VERDICT: LIKELY VULNERABLE** (Confidence: {result.confidence:.0%})\n\n"
                f"Cross-graph analysis shows strong vulnerability indicators:\n"
                f"- Violated specifications: {', '.join(result.violated_specs) or 'None'}\n"
                f"- Similar known exploits: {', '.join(result.similar_exploits) or 'None'}\n"
                f"- No adequate defensive measures detected\n\n"
                f"**Winning Argument:** {result.winning_argument}\n"
            ),
            "RULE_4_CROSS_GRAPH_VIOLATION_ONLY": (
                f"**VERDICT: UNCERTAIN** (Confidence: {result.confidence:.0%})\n\n"
                f"A specification violation was detected, but no similar known exploits "
                f"were found in the database. Manual review is recommended.\n\n"
                f"**Violated Specs:** {', '.join(result.violated_specs) or 'None'}\n"
            ),
            "RULE_5_STRONG_DEFENSE": (
                f"**VERDICT: LIKELY SAFE** (Confidence: {result.confidence:.0%})\n\n"
                f"Strong defensive measures are present that should prevent exploitation.\n\n"
                f"**Winning Argument:** {result.winning_argument}\n"
            ),
            "RULE_6_ATTACK_WITHOUT_DEFENSE": (
                f"**VERDICT: LIKELY VULNERABLE** (Confidence: {result.confidence:.0%})\n\n"
                f"A valid attack construction exists with insufficient defensive measures.\n\n"
                f"**Winning Argument:** {result.winning_argument}\n"
            ),
            "RULE_7_CONTESTED": (
                f"**VERDICT: UNCERTAIN** (Confidence: {result.confidence:.0%})\n\n"
                f"Both attacker and defender have presented strong arguments. "
                f"Manual expert review is required to resolve this dispute.\n\n"
                f"**Attacker Score:** {result.attacker_evidence_score:.2f}\n"
                f"**Defender Score:** {result.defender_evidence_score:.2f}\n"
            ),
            "RULE_8_INSUFFICIENT_EVIDENCE": (
                f"**VERDICT: UNCERTAIN** (Confidence: {result.confidence:.0%})\n\n"
                f"Insufficient evidence to make a confident determination. "
                f"Additional analysis or manual review is recommended.\n"
            ),
        }

        return explanations.get(
            result.decision_rule_used,
            f"Verdict: {result.verdict.value} with confidence {result.confidence:.0%}"
        )

    def _generate_breakdown(
        self,
        result: ArbitrationResult,
        evidence: EvidenceChain,
    ) -> Dict[str, Any]:
        """Generate detailed breakdown for debugging/transparency."""
        return {
            "decision_rule": result.decision_rule_used,
            "evidence_summary": {
                "total_items": len(evidence.items),
                "for_attacker": len(evidence.for_attacker()),
                "for_defender": len(evidence.for_defender()),
            },
            "evidence_by_type": {
                etype.value: len([e for e in evidence.items if e.evidence_type == etype])
                for etype in EvidenceType
            },
            "strongest_attacker_evidence": (
                evidence.strongest_evidence().__dict__
                if evidence.for_attacker()
                else None
            ),
            "strongest_defender_evidence": (
                evidence.strongest_evidence().__dict__
                if evidence.for_defender()
                else None
            ),
        }

    def _generate_recommendations(self, result: ArbitrationResult) -> List[Recommendation]:
        """Generate actionable recommendations based on verdict."""
        recommendations = []

        if result.verdict == Verdict.VULNERABLE:
            recommendations.append(Recommendation(
                action="fix",
                priority="critical",
                description="Immediate remediation required. Vulnerability is confirmed exploitable.",
                suggested_fix="Apply recommended guards and follow Checks-Effects-Interactions pattern.",
            ))

        elif result.verdict == Verdict.LIKELY_VULNERABLE:
            recommendations.append(Recommendation(
                action="fix",
                priority="high",
                description="Strong evidence of vulnerability. Remediation highly recommended.",
                suggested_fix="Review attack construction and apply appropriate mitigations.",
            ))

        elif result.verdict == Verdict.UNCERTAIN:
            recommendations.append(Recommendation(
                action="review",
                priority="medium",
                description="Manual expert review recommended to resolve uncertainty.",
            ))
            if result.requires_manual_review:
                recommendations.append(Recommendation(
                    action="verify",
                    priority="medium",
                    description="Consider additional formal verification or testing.",
                ))

        elif result.verdict == Verdict.LIKELY_SAFE:
            recommendations.append(Recommendation(
                action="verify",
                priority="low",
                description="Defense appears adequate. Verify guards are correctly implemented.",
            ))

        elif result.verdict == Verdict.SAFE:
            recommendations.append(Recommendation(
                action="accept",
                priority="low",
                description="Code is confirmed safe. No action required.",
            ))

        return recommendations

    def re_arbitrate(
        self,
        previous_result: ArbitrationResult,
        new_evidence: List[EvidenceItem],
    ) -> ArbitrationResult:
        """
        Re-arbitrate with additional evidence (appeal process).

        Args:
            previous_result: The previous arbitration result
            new_evidence: Additional evidence items to consider

        Returns:
            New ArbitrationResult incorporating all evidence
        """
        # Merge evidence chains
        combined = EvidenceChain()
        combined.items = previous_result.evidence_chain.items + new_evidence

        # Re-apply rules with combined evidence
        # (Implementation would re-run _apply_decision_rules with updated evidence)
        # This allows for iterative refinement of verdicts
        pass
```

---

## Success Criteria

- [ ] Decision rules implemented with clear priority ordering
- [ ] Evidence aggregation with weighted scoring working
- [ ] All 8 decision rules correctly applied
- [ ] Human-readable explanations generated
- [ ] Recommendations actionable and appropriate
- [ ] Contested cases flagged for manual review
- [ ] Re-arbitration (appeal) supported
- [ ] Integration tests with Attacker/Defender/Verifier passing

---

## Validation Tests

```python
import pytest
from true_vkg.agents.arbiter import (
    AdversarialArbiter, Verdict, EvidenceType, EvidenceDirection,
    EvidenceItem, EvidenceChain, ArbitrationResult
)


class TestDecisionRules:
    """Test each decision rule in isolation."""

    def test_rule1_formal_proof_feasible_yields_vulnerable(self):
        """RULE 1: Formal proof feasible → VULNERABLE."""
        arbiter = AdversarialArbiter(mock_linker)

        # Create verifier result that proves path feasible
        verifier_result = VerificationResult(
            path_feasible=True,
            is_proven=True,
            constraints_satisfied=["balance > 0", "caller != owner"],
            proof_steps=["Step 1: ...", "Step 2: ..."],
        )

        result = arbiter.arbitrate(
            attacker_result=create_attack_result(confidence=0.8),
            defender_result=create_defense_result(confidence=0.6),
            verifier_result=verifier_result,
            focal_node="fn_withdraw_vuln",
        )

        assert result.verdict == Verdict.VULNERABLE
        assert result.confidence >= 0.95
        assert result.winning_side == "attacker"
        assert "RULE_1" in result.decision_rule_used
        assert not result.requires_manual_review

    def test_rule2_formal_proof_infeasible_yields_safe(self):
        """RULE 2: Formal proof infeasible → SAFE."""
        arbiter = AdversarialArbiter(mock_linker)

        verifier_result = VerificationResult(
            path_feasible=False,
            is_proven=True,
            constraints_unsatisfiable=["balance >= 0 AND balance < 0"],
        )

        result = arbiter.arbitrate(
            attacker_result=create_attack_result(confidence=0.8),
            defender_result=create_defense_result(confidence=0.3),
            verifier_result=verifier_result,
            focal_node="fn_withdraw_safe",
        )

        assert result.verdict == Verdict.SAFE
        assert result.confidence >= 0.90
        assert result.winning_side == "defender"
        assert "RULE_2" in result.decision_rule_used

    def test_rule3_cross_graph_high_signal_yields_likely_vulnerable(self):
        """RULE 3: Cross-graph violation + exploit + weak defense → LIKELY_VULNERABLE."""
        # Setup linker to return violation and similar exploit
        linker = MockLinker()
        linker.add_violation("fn_test", "ERC20_TRANSFER_SPEC", severity=0.9)
        linker.add_similar_exploit("fn_test", "CVE-2021-REENTRANCY", similarity=0.85)

        arbiter = AdversarialArbiter(linker)

        result = arbiter.arbitrate(
            attacker_result=create_attack_result(confidence=0.7),
            defender_result=create_defense_result(confidence=0.4),  # Weak defense
            verifier_result=None,  # No formal proof
            focal_node="fn_test",
        )

        assert result.verdict == Verdict.LIKELY_VULNERABLE
        assert result.confidence >= 0.80
        assert result.winning_side == "attacker"
        assert "RULE_3" in result.decision_rule_used
        assert "ERC20_TRANSFER_SPEC" in result.violated_specs
        assert "CVE-2021-REENTRANCY" in result.similar_exploits

    def test_rule4_violation_only_yields_uncertain(self):
        """RULE 4: Violation but no exploit → UNCERTAIN with vuln bias."""
        linker = MockLinker()
        linker.add_violation("fn_test", "ERC20_SPEC", severity=0.8)
        # No similar exploit

        arbiter = AdversarialArbiter(linker)

        result = arbiter.arbitrate(
            attacker_result=create_attack_result(confidence=0.5),
            defender_result=create_defense_result(confidence=0.5),
            verifier_result=None,
            focal_node="fn_test",
        )

        assert result.verdict == Verdict.UNCERTAIN
        assert result.requires_manual_review
        assert "RULE_4" in result.decision_rule_used

    def test_rule5_strong_defense_yields_likely_safe(self):
        """RULE 5: Strong guards → LIKELY_SAFE."""
        arbiter = AdversarialArbiter(MockLinker())

        # Create defender with strong guard evidence
        defender = create_defense_result(
            confidence=0.85,
            guards=["ReentrancyGuard", "onlyOwner"],
            guard_strength=0.9,
        )

        result = arbiter.arbitrate(
            attacker_result=create_attack_result(confidence=0.5),
            defender_result=defender,
            verifier_result=None,
            focal_node="fn_protected",
        )

        assert result.verdict == Verdict.LIKELY_SAFE
        assert result.winning_side == "defender"
        assert "RULE_5" in result.decision_rule_used

    def test_rule6_attack_without_defense_yields_likely_vulnerable(self):
        """RULE 6: Valid attack + weak defense → LIKELY_VULNERABLE."""
        arbiter = AdversarialArbiter(MockLinker())

        result = arbiter.arbitrate(
            attacker_result=create_attack_result(confidence=0.75),
            defender_result=create_defense_result(confidence=0.2),  # Very weak
            verifier_result=None,
            focal_node="fn_unprotected",
        )

        assert result.verdict == Verdict.LIKELY_VULNERABLE
        assert "RULE_6" in result.decision_rule_used

    def test_rule7_contested_yields_uncertain_with_review(self):
        """RULE 7: Both sides strong → UNCERTAIN + manual review."""
        arbiter = AdversarialArbiter(MockLinker())

        result = arbiter.arbitrate(
            attacker_result=create_attack_result(confidence=0.75),
            defender_result=create_defense_result(confidence=0.75),
            verifier_result=None,
            focal_node="fn_contested",
        )

        assert result.verdict == Verdict.UNCERTAIN
        assert result.winning_side == "neither"
        assert result.requires_manual_review
        assert "RULE_7" in result.decision_rule_used

    def test_rule8_insufficient_evidence_default(self):
        """RULE 8: Default when no other rule applies."""
        arbiter = AdversarialArbiter(MockLinker())

        result = arbiter.arbitrate(
            attacker_result=create_attack_result(confidence=0.3),
            defender_result=create_defense_result(confidence=0.3),
            verifier_result=None,
            focal_node="fn_unknown",
        )

        assert result.verdict == Verdict.UNCERTAIN
        assert "RULE_8" in result.decision_rule_used


class TestEvidenceAggregation:
    """Test evidence collection and weighting."""

    def test_evidence_chain_weighted_sum(self):
        """Test weighted sum calculation."""
        chain = EvidenceChain()

        # Add formal proof (weight 1.0, strength 1.0) = 1.0
        chain.add(EvidenceItem(
            id="proof",
            evidence_type=EvidenceType.FORMAL_PROOF,
            direction=EvidenceDirection.SUPPORTS_ATTACKER,
            strength=1.0,
            description="Z3 proved feasible",
            source_agent="verifier",
        ))

        # Add pattern match (weight 0.6, strength 0.8) = 0.48
        chain.add(EvidenceItem(
            id="pattern",
            evidence_type=EvidenceType.PATTERN_MATCH,
            direction=EvidenceDirection.SUPPORTS_ATTACKER,
            strength=0.8,
            description="Matches reentrancy pattern",
            source_agent="attacker",
        ))

        attacker_sum = chain.weighted_sum(EvidenceDirection.SUPPORTS_ATTACKER)
        assert attacker_sum == pytest.approx(1.48, rel=0.01)

    def test_evidence_chain_has_formal_proof(self):
        """Test formal proof detection."""
        chain = EvidenceChain()
        assert not chain.has_formal_proof()

        chain.add(EvidenceItem(
            id="proof",
            evidence_type=EvidenceType.FORMAL_PROOF,
            direction=EvidenceDirection.SUPPORTS_ATTACKER,
            strength=1.0,
            description="...",
            source_agent="verifier",
        ))

        assert chain.has_formal_proof()


class TestExplanationGeneration:
    """Test human-readable explanation generation."""

    def test_vulnerable_explanation_includes_key_info(self):
        """Test VULNERABLE explanation has necessary details."""
        arbiter = AdversarialArbiter(MockLinker())

        result = arbiter.arbitrate(
            attacker_result=create_attack_result(confidence=0.8),
            defender_result=create_defense_result(confidence=0.3),
            verifier_result=VerificationResult(path_feasible=True, is_proven=True),
            focal_node="fn_vuln",
        )

        assert "VULNERABLE" in result.explanation
        assert "Z3" in result.explanation or "formally" in result.explanation.lower()
        assert str(int(result.confidence * 100)) in result.explanation

    def test_contested_explanation_requests_review(self):
        """Test contested explanation mentions manual review."""
        arbiter = AdversarialArbiter(MockLinker())

        result = arbiter.arbitrate(
            attacker_result=create_attack_result(confidence=0.7),
            defender_result=create_defense_result(confidence=0.7),
            verifier_result=None,
            focal_node="fn_contested",
        )

        assert "review" in result.explanation.lower() or "manual" in result.explanation.lower()


class TestRecommendations:
    """Test recommendation generation."""

    def test_vulnerable_gets_critical_fix_recommendation(self):
        """VULNERABLE verdict should get critical priority fix."""
        arbiter = AdversarialArbiter(MockLinker())

        result = arbiter.arbitrate(
            attacker_result=create_attack_result(confidence=0.9),
            defender_result=create_defense_result(confidence=0.2),
            verifier_result=VerificationResult(path_feasible=True, is_proven=True),
            focal_node="fn_vuln",
        )

        assert len(result.recommendations) > 0
        critical_recs = [r for r in result.recommendations if r.priority == "critical"]
        assert len(critical_recs) > 0
        assert critical_recs[0].action == "fix"

    def test_safe_gets_accept_recommendation(self):
        """SAFE verdict should get accept recommendation."""
        arbiter = AdversarialArbiter(MockLinker())

        result = arbiter.arbitrate(
            attacker_result=create_attack_result(confidence=0.3),
            defender_result=create_defense_result(confidence=0.9),
            verifier_result=VerificationResult(path_feasible=False, is_proven=True),
            focal_node="fn_safe",
        )

        accept_recs = [r for r in result.recommendations if r.action == "accept"]
        assert len(accept_recs) > 0


class TestUltimateArbiterIntegration:
    """Integration test with real Attacker and Defender agents."""

    def test_full_adversarial_pipeline_on_vulnerable_code(self):
        """Test complete pipeline: Attacker → Defender → Arbiter on vulnerable code."""
        # Setup
        graph = build_graph_from_source(REENTRANCY_VULNERABLE_CODE)
        domain_kg = create_domain_kg_with_specs()
        linker = CrossGraphLinker(domain_kg)

        # Run attacker
        attacker = AttackerAgent(llm_client, domain_kg)
        attacker_result = attacker.analyze(create_context(graph, "fn_withdraw"))

        # Run defender (receives attacker claims)
        defender = DefenderAgent(llm_client, domain_kg)
        defender_context = create_context(
            graph, "fn_withdraw",
            upstream_results=[attacker_result]
        )
        defender_result = defender.analyze(defender_context)

        # Run verifier
        verifier = LLMDFAVerifier(llm_client)
        verifier_result = verifier.verify_paths(
            attacker_result.findings,
            graph,
        )

        # Arbitrate
        arbiter = AdversarialArbiter(linker)
        final_verdict = arbiter.arbitrate(
            attacker_result,
            defender_result,
            verifier_result,
            "fn_withdraw",
        )

        # Assert vulnerable code is detected
        assert final_verdict.verdict in (Verdict.VULNERABLE, Verdict.LIKELY_VULNERABLE)
        assert final_verdict.confidence >= 0.7
        assert final_verdict.winning_side == "attacker"

        # Assert explanation and recommendations exist
        assert len(final_verdict.explanation) > 50
        assert len(final_verdict.recommendations) > 0

    def test_full_adversarial_pipeline_on_safe_code(self):
        """Test complete pipeline on protected code."""
        graph = build_graph_from_source(REENTRANCY_SAFE_CODE_WITH_GUARD)
        domain_kg = create_domain_kg_with_specs()
        linker = CrossGraphLinker(domain_kg)

        # Run full pipeline
        attacker_result = AttackerAgent(llm_client, domain_kg).analyze(...)
        defender_result = DefenderAgent(llm_client, domain_kg).analyze(...)
        verifier_result = LLMDFAVerifier(llm_client).verify_paths(...)

        final_verdict = AdversarialArbiter(linker).arbitrate(
            attacker_result,
            defender_result,
            verifier_result,
            "fn_safe_withdraw",
        )

        # Assert safe code is recognized
        assert final_verdict.verdict in (Verdict.SAFE, Verdict.LIKELY_SAFE)
        assert final_verdict.winning_side == "defender"


# Test fixtures
REENTRANCY_VULNERABLE_CODE = '''
contract Vulnerable {
    mapping(address => uint256) balances;

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        (bool success,) = msg.sender.call{value: amount}("");
        require(success);
        balances[msg.sender] -= amount;  // State update AFTER external call
    }
}
'''

REENTRANCY_SAFE_CODE_WITH_GUARD = '''
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract Safe is ReentrancyGuard {
    mapping(address => uint256) balances;

    function withdraw(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;  // CEI: State update BEFORE external call
        (bool success,) = msg.sender.call{value: amount}("");
        require(success);
    }
}
'''
```

---

## Integration Points

### Input From Other Tasks
- **P2-T2 Attacker Agent**: `AgentResult` with `AttackConstruction` findings
- **P2-T3 Defender Agent**: `AgentResult` with `DefenseArgument` findings
- **P2-T4 LLMDFA Verifier**: `VerificationResult` with path feasibility proof
- **P0-T3 Cross-Graph Linker**: `VulnerabilityCandidate` list with cross-graph context

### Output To Other Tasks
- **P3-T1 Iterative Engine**: Verdicts trigger iterative refinement
- **P3-T2 Causal Engine**: Verdicts used as targets for root cause analysis
- **User/Reports**: Final verdicts with explanations and recommendations

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
| 2026-01-03 | Enhanced with decision matrix, evidence weighting, complete implementation | Claude |
