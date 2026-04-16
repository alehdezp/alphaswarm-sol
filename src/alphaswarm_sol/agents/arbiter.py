"""
P2-T5: Adversarial Arbiter

Judges attacker vs defender arguments using evidence-based decision rules.
Produces final verdicts with high confidence by combining multiple evidence sources.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class VerdictType(Enum):
    """Types of verdicts."""

    VULNERABLE = "vulnerable"
    SAFE = "safe"
    UNCERTAIN = "uncertain"


class ConfidenceLevel(Enum):
    """Confidence levels for verdicts."""

    DEFINITIVE = "definitive"  # 0.95-1.0 (formal proof)
    HIGH = "high"  # 0.80-0.90 (cross-graph + spec violation)
    MODERATE = "moderate"  # 0.70-0.85 (strong guards)
    SUGGESTIVE = "suggestive"  # 0.60-0.75 (pattern match)
    INDICATIVE = "indicative"  # 0.50-0.65 (behavioral signatures)
    UNCERTAIN = "uncertain"  # < 0.50 (heuristics only)


class EvidenceType(Enum):
    """Types of evidence."""

    FORMAL_PROOF = "formal_proof"  # Z3 SAT/UNSAT
    CROSS_GRAPH = "cross_graph"  # VIOLATES/IMPLEMENTS edges
    GUARD_ANALYSIS = "guard_analysis"  # Guard presence
    PATTERN_MATCH = "pattern_match"  # Pattern matching
    BEHAVIORAL_SIG = "behavioral_sig"  # Operation sequences
    HEURISTIC = "heuristic"  # General heuristics


class WinningSide(Enum):
    """Which side won the debate."""

    ATTACKER = "attacker"
    DEFENDER = "defender"
    INCONCLUSIVE = "inconclusive"


@dataclass
class Evidence:
    """A piece of evidence for or against vulnerability."""

    evidence_type: EvidenceType
    weight: float  # Intrinsic weight of evidence type
    confidence: float  # Confidence in this specific evidence
    supports_vulnerable: bool  # True = attacker, False = defender
    description: str
    source: str  # Which agent provided this
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceChain:
    """Chain of evidence supporting a verdict."""

    all_evidence: List[Evidence] = field(default_factory=list)
    attacker_evidence: List[Evidence] = field(default_factory=list)
    defender_evidence: List[Evidence] = field(default_factory=list)

    def add(self, evidence: Evidence):
        """Add evidence to appropriate chain."""
        self.all_evidence.append(evidence)
        if evidence.supports_vulnerable:
            self.attacker_evidence.append(evidence)
        else:
            self.defender_evidence.append(evidence)


@dataclass
class ArbitrationResult:
    """Final arbitration result."""

    verdict: VerdictType
    confidence: float  # 0.0-1.0
    confidence_level: ConfidenceLevel
    winning_side: WinningSide
    explanation: str
    evidence_chain: EvidenceChain
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdversarialArbiter:
    """
    Arbiter that judges attacker vs defender arguments.

    Uses evidence-based decision rules with priority ordering:
    1. Formal proof (Z3) → DEFINITIVE
    2. Cross-graph + violation → HIGH
    3. Guard strength analysis → MODERATE
    4. Pattern matching → SUGGESTIVE
    5. Behavioral signatures → INDICATIVE
    6. Heuristics only → UNCERTAIN
    """

    # Evidence type weights (intrinsic trust in evidence type)
    EVIDENCE_WEIGHTS = {
        EvidenceType.FORMAL_PROOF: 1.0,
        EvidenceType.CROSS_GRAPH: 0.8,
        EvidenceType.GUARD_ANALYSIS: 0.7,
        EvidenceType.PATTERN_MATCH: 0.6,
        EvidenceType.BEHAVIORAL_SIG: 0.5,
        EvidenceType.HEURISTIC: 0.3,
    }

    def __init__(self):
        """Initialize arbiter."""
        self.logger = logging.getLogger(__name__)

    def arbitrate(
        self,
        attacker_result: Optional[Any] = None,
        defender_result: Optional[Any] = None,
        verifier_result: Optional[Any] = None,
        cross_graph_context: Optional[Any] = None,
    ) -> ArbitrationResult:
        """
        Arbitrate between attacker and defender.

        Args:
            attacker_result: Result from AttackerAgent
            defender_result: Result from DefenderAgent
            verifier_result: Optional result from VerifierAgent
            cross_graph_context: Optional cross-graph context

        Returns:
            ArbitrationResult with verdict and explanation
        """
        try:
            # Collect all evidence
            evidence_chain = self._collect_evidence(
                attacker_result, defender_result, verifier_result, cross_graph_context
            )

            # Make decision based on evidence
            verdict, confidence, winning_side = self._make_decision(evidence_chain)

            # Determine confidence level
            confidence_level = self._get_confidence_level(confidence, evidence_chain)

            # Generate explanation
            explanation = self._generate_explanation(
                verdict, winning_side, evidence_chain
            )

            # Generate recommendations
            recommendations = self._generate_recommendations(
                verdict, evidence_chain, attacker_result, defender_result
            )

            return ArbitrationResult(
                verdict=verdict,
                confidence=confidence,
                confidence_level=confidence_level,
                winning_side=winning_side,
                explanation=explanation,
                evidence_chain=evidence_chain,
                recommendations=recommendations,
                metadata={
                    "attacker_confidence": (
                        attacker_result.confidence
                        if attacker_result and hasattr(attacker_result, "confidence")
                        else 0.0
                    ),
                    "defender_confidence": (
                        defender_result.confidence
                        if defender_result and hasattr(defender_result, "confidence")
                        else 0.0
                    ),
                    "evidence_count": len(evidence_chain.all_evidence),
                },
            )

        except Exception as e:
            self.logger.error(f"Arbitration error: {e}", exc_info=True)
            return ArbitrationResult(
                verdict=VerdictType.UNCERTAIN,
                confidence=0.0,
                confidence_level=ConfidenceLevel.UNCERTAIN,
                winning_side=WinningSide.INCONCLUSIVE,
                explanation=f"Error during arbitration: {str(e)}",
                evidence_chain=EvidenceChain(),
                metadata={"error": str(e)},
            )

    def _collect_evidence(
        self,
        attacker_result: Optional[Any],
        defender_result: Optional[Any],
        verifier_result: Optional[Any],
        cross_graph_context: Optional[Any],
    ) -> EvidenceChain:
        """Collect evidence from all sources."""
        chain = EvidenceChain()

        # Collect attacker evidence
        if attacker_result and hasattr(attacker_result, "matched") and attacker_result.matched:
            attack = attacker_result.attack if hasattr(attacker_result, "attack") else None
            if attack:
                # Pattern match evidence
                chain.add(
                    Evidence(
                        evidence_type=EvidenceType.PATTERN_MATCH,
                        weight=self.EVIDENCE_WEIGHTS[EvidenceType.PATTERN_MATCH],
                        confidence=attacker_result.confidence,
                        supports_vulnerable=True,
                        description=f"Attack detected: {attack.category.value if hasattr(attack, 'category') else 'unknown'}",
                        source="attacker",
                        details={
                            "exploitability": attack.exploitability_score
                            if hasattr(attack, "exploitability_score")
                            else 0.0,
                            "category": attack.category.value
                            if hasattr(attack, "category")
                            else "unknown",
                        },
                    )
                )

                # Behavioral signature evidence if present
                if hasattr(attack, "metadata") and "behavioral_signature" in attack.metadata:
                    chain.add(
                        Evidence(
                            evidence_type=EvidenceType.BEHAVIORAL_SIG,
                            weight=self.EVIDENCE_WEIGHTS[EvidenceType.BEHAVIORAL_SIG],
                            confidence=0.7,
                            supports_vulnerable=True,
                            description="Vulnerable behavioral signature detected",
                            source="attacker",
                        )
                    )

        # Collect defender evidence
        if defender_result and hasattr(defender_result, "matched") and defender_result.matched:
            defenses = (
                defender_result.defenses
                if hasattr(defender_result, "defenses")
                else []
            )

            for defense in defenses:
                # Guard evidence
                if hasattr(defense, "guards_identified") and defense.guards_identified:
                    for guard in defense.guards_identified:
                        chain.add(
                            Evidence(
                                evidence_type=EvidenceType.GUARD_ANALYSIS,
                                weight=self.EVIDENCE_WEIGHTS[
                                    EvidenceType.GUARD_ANALYSIS
                                ],
                                confidence=guard.strength
                                if hasattr(guard, "strength")
                                else 0.7,
                                supports_vulnerable=False,
                                description=f"Guard present: {guard.name if hasattr(guard, 'name') else 'unknown'}",
                                source="defender",
                                details={
                                    "guard_type": guard.guard_type
                                    if hasattr(guard, "guard_type")
                                    else "unknown",
                                    "blocks_attacks": guard.blocks_attacks
                                    if hasattr(guard, "blocks_attacks")
                                    else [],
                                },
                            )
                        )

                # Rebuttal evidence (high weight)
                if hasattr(defense, "rebuts_attack") and defense.rebuts_attack:
                    chain.add(
                        Evidence(
                            evidence_type=EvidenceType.GUARD_ANALYSIS,
                            weight=0.85,  # Rebuttals are strong evidence
                            confidence=defense.strength
                            if hasattr(defense, "strength")
                            else 0.8,
                            supports_vulnerable=False,
                            description=f"Rebuttal: {defense.claim if hasattr(defense, 'claim') else 'Unknown'}",
                            source="defender",
                        )
                    )

        # Collect verifier evidence (highest priority)
        if verifier_result and hasattr(verifier_result, "verified"):
            chain.add(
                Evidence(
                    evidence_type=EvidenceType.FORMAL_PROOF,
                    weight=self.EVIDENCE_WEIGHTS[EvidenceType.FORMAL_PROOF],
                    confidence=0.95,
                    supports_vulnerable=not verifier_result.verified,
                    description="Formal verification result",
                    source="verifier",
                )
            )

        # Collect cross-graph evidence
        if cross_graph_context:
            # Would check for VIOLATES/IMPLEMENTS edges
            # Simplified for now
            pass

        return chain

    def _make_decision(
        self, evidence_chain: EvidenceChain
    ) -> tuple[VerdictType, float, WinningSide]:
        """
        Make decision based on evidence.

        Priority-based decision rules:
        1. If formal proof exists → follow it (highest priority)
        2. Weight evidence by type and confidence
        3. Compare attacker vs defender weighted scores
        4. Require minimum threshold for verdict
        """
        # Check for formal proof (highest priority)
        formal_proofs = [
            e for e in evidence_chain.all_evidence if e.evidence_type == EvidenceType.FORMAL_PROOF
        ]
        if formal_proofs:
            proof = formal_proofs[0]  # Take first/strongest
            verdict = (
                VerdictType.VULNERABLE
                if proof.supports_vulnerable
                else VerdictType.SAFE
            )
            winning_side = (
                WinningSide.ATTACKER
                if proof.supports_vulnerable
                else WinningSide.DEFENDER
            )
            return verdict, 0.95, winning_side

        # Calculate weighted scores
        attacker_score = self._calculate_weighted_score(
            evidence_chain.attacker_evidence
        )
        defender_score = self._calculate_weighted_score(
            evidence_chain.defender_evidence
        )

        # Determine verdict
        if abs(attacker_score - defender_score) < 0.1:
            # Too close to call
            return VerdictType.UNCERTAIN, 0.5, WinningSide.INCONCLUSIVE

        if attacker_score > defender_score:
            confidence = min(0.9, attacker_score)  # Cap at 0.9 without formal proof
            return VerdictType.VULNERABLE, confidence, WinningSide.ATTACKER
        else:
            confidence = min(0.9, defender_score)
            return VerdictType.SAFE, confidence, WinningSide.DEFENDER

    def _calculate_weighted_score(self, evidence_list: List[Evidence]) -> float:
        """Calculate weighted evidence score."""
        if not evidence_list:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for evidence in evidence_list:
            # Combined score = evidence type weight × specific confidence
            score = evidence.weight * evidence.confidence
            weighted_sum += score
            total_weight += evidence.weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _get_confidence_level(
        self, confidence: float, evidence_chain: EvidenceChain
    ) -> ConfidenceLevel:
        """Determine confidence level category."""
        # Check evidence types
        has_formal_proof = any(
            e.evidence_type == EvidenceType.FORMAL_PROOF
            for e in evidence_chain.all_evidence
        )
        has_cross_graph = any(
            e.evidence_type == EvidenceType.CROSS_GRAPH
            for e in evidence_chain.all_evidence
        )
        has_guards = any(
            e.evidence_type == EvidenceType.GUARD_ANALYSIS
            for e in evidence_chain.all_evidence
        )

        if has_formal_proof:
            return ConfidenceLevel.DEFINITIVE
        elif confidence >= 0.80 and has_cross_graph:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.70 and has_guards:
            return ConfidenceLevel.MODERATE
        elif confidence >= 0.60:
            return ConfidenceLevel.SUGGESTIVE
        elif confidence >= 0.50:
            return ConfidenceLevel.INDICATIVE
        else:
            return ConfidenceLevel.UNCERTAIN

    def _generate_explanation(
        self,
        verdict: VerdictType,
        winning_side: WinningSide,
        evidence_chain: EvidenceChain,
    ) -> str:
        """Generate human-readable explanation."""
        lines = []

        # Verdict statement
        lines.append(f"Verdict: {verdict.value.upper()}")
        lines.append(f"Winning Side: {winning_side.value}")

        # Evidence summary
        attacker_count = len(evidence_chain.attacker_evidence)
        defender_count = len(evidence_chain.defender_evidence)
        lines.append(
            f"Evidence: {attacker_count} attacker, {defender_count} defender"
        )

        # Key evidence
        if verdict == VerdictType.VULNERABLE:
            key_evidence = evidence_chain.attacker_evidence[:2]  # Top 2
            if key_evidence:
                lines.append("Key attacker evidence:")
                for e in key_evidence:
                    lines.append(f"  - {e.description}")
        elif verdict == VerdictType.SAFE:
            key_evidence = evidence_chain.defender_evidence[:2]
            if key_evidence:
                lines.append("Key defender evidence:")
                for e in key_evidence:
                    lines.append(f"  - {e.description}")

        return "\n".join(lines)

    def _generate_recommendations(
        self,
        verdict: VerdictType,
        evidence_chain: EvidenceChain,
        attacker_result: Optional[Any],
        defender_result: Optional[Any],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if verdict == VerdictType.VULNERABLE:
            # Suggest mitigations based on attack type
            if attacker_result and hasattr(attacker_result, "attack"):
                attack = attacker_result.attack
                if hasattr(attack, "category"):
                    category = attack.category.value if hasattr(attack.category, "value") else str(attack.category)

                    if "state_manipulation" in category or "reentrancy" in category:
                        recommendations.append(
                            "Add reentrancy guard (ReentrancyGuard modifier)"
                        )
                        recommendations.append(
                            "Follow Checks-Effects-Interactions pattern"
                        )
                    elif "access" in category:
                        recommendations.append(
                            "Add access control (onlyOwner or role-based)"
                        )
                    elif "economic" in category:
                        recommendations.append("Add oracle staleness checks")
                        recommendations.append("Implement slippage protection")

        elif verdict == VerdictType.SAFE:
            # Acknowledge good practices
            if defender_result and hasattr(defender_result, "defenses"):
                guard_types = set()
                for defense in defender_result.defenses:
                    if hasattr(defense, "guards_identified"):
                        for guard in defense.guards_identified:
                            if hasattr(guard, "guard_type"):
                                guard_types.add(guard.guard_type)

                if guard_types:
                    recommendations.append(
                        f"Maintain current protections: {', '.join(guard_types)}"
                    )

        elif verdict == VerdictType.UNCERTAIN:
            recommendations.append("Manual audit recommended")
            recommendations.append("Consider formal verification")

        return recommendations
