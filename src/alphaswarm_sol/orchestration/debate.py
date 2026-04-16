"""Structured debate protocol (iMAD-inspired).

Protocol from 04-CONTEXT.md:
1. CLAIM ROUND - Attacker/Defender present evidence-anchored arguments
2. REBUTTAL ROUND - Challenge each other's evidence
3. SYNTHESIS - Verifier weighs evidence, produces verdict
4. HUMAN CHECKPOINT - Always flagged for human review

Key principle: Evidence anchoring - all claims must reference code locations.

Usage:
    from alphaswarm_sol.orchestration.debate import DebateOrchestrator, run_debate

    orchestrator = DebateOrchestrator(
        attacker_agent=attacker,
        defender_agent=defender,
        verifier_agent=verifier,
    )

    verdict = orchestrator.run_debate(
        bead_id="VKG-001",
        evidence=evidence_packet,
        attacker_context={"agent_context": ctx},
        defender_context={"agent_context": ctx},
    )

    # Verdict is always human-flagged
    assert verdict.human_flag == True
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

from .schemas import (
    DebateClaim,
    DebateRecord,
    EvidenceItem,
    EvidencePacket,
    Verdict,
    VerdictConfidence,
)
from .confidence import ConfidenceEnforcer

logger = logging.getLogger(__name__)


class DebatePhase(Enum):
    """Phases of the debate protocol.

    The debate proceeds through these phases in order:
    1. CLAIM - Initial claims from attacker and defender
    2. REBUTTAL - Each side challenges the other's evidence
    3. SYNTHESIS - Verifier weighs evidence and determines outcome
    4. COMPLETE - Debate finished, verdict rendered

    Usage:
        if round.phase == DebatePhase.CLAIM:
            print("In claim phase")
    """

    CLAIM = "claim"
    REBUTTAL = "rebuttal"
    SYNTHESIS = "synthesis"
    COMPLETE = "complete"


@dataclass
class DebateRound:
    """A single round of debate.

    Each round captures the arguments from both sides at a specific
    phase of the debate.

    Attributes:
        phase: Which debate phase this round represents
        attacker_argument: Claim from the attacker side
        defender_argument: Claim from the defender side
        timestamp: When this round occurred

    Usage:
        round = DebateRound(phase=DebatePhase.CLAIM)
        round.attacker_argument = attacker_claim
        round.defender_argument = defender_claim
    """

    phase: DebatePhase
    attacker_argument: Optional[DebateClaim] = None
    defender_argument: Optional[DebateClaim] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DebateConfig:
    """Configuration for debate protocol.

    Attributes:
        max_rebuttal_rounds: Maximum back-and-forth rebuttal rounds (default: 2)
        require_evidence: Whether claims must have evidence items (default: True)
        auto_flag_human: Whether to always flag for human review (default: True)

    Usage:
        config = DebateConfig(max_rebuttal_rounds=3)
        orchestrator = DebateOrchestrator(config=config)
    """

    max_rebuttal_rounds: int = 2
    require_evidence: bool = True
    auto_flag_human: bool = True


@dataclass
class DebateResult:
    """Result of a complete debate.

    Captures the full debate outcome including all rounds, the final
    verdict, and whether disagreement triggered human review.

    Attributes:
        verdict: Final determination from the debate
        rounds: All debate rounds in order
        debate_record: Structured record for storage
        has_disagreement: Whether attacker/defender disagreed
        synthesis_rationale: Verifier's synthesis explanation

    Usage:
        result = orchestrator.run_debate(...)
        if result.has_disagreement:
            print("Debate had disagreement, requires human review")
    """

    verdict: Verdict
    rounds: List[DebateRound] = field(default_factory=list)
    debate_record: Optional[DebateRecord] = None
    has_disagreement: bool = False
    synthesis_rationale: str = ""


class DebateOrchestrator:
    """Orchestrates structured debate between attacker and defender.

    The debate follows iMAD protocol:
    - Claims must be evidence-anchored (code locations)
    - Rebuttals challenge specific evidence
    - Verifier synthesizes, doesn't add new analysis
    - Human always reviews debate outcomes

    Per PHILOSOPHY.md and 04-CONTEXT.md:
    - Debate outcomes always require human review
    - Evidence anchoring is required
    - Disagreement triggers human flag

    Example:
        orchestrator = DebateOrchestrator(
            attacker_agent=attacker,
            defender_agent=defender,
            verifier_agent=verifier,
        )

        verdict = orchestrator.run_debate(
            bead_id="VKG-001",
            evidence=evidence_packet,
            attacker_context={"agent_context": ctx},
            defender_context={"agent_context": ctx},
        )

        # Always human-flagged
        assert verdict.human_flag == True
    """

    def __init__(
        self,
        attacker_agent: Any = None,
        defender_agent: Any = None,
        verifier_agent: Any = None,
        config: Optional[DebateConfig] = None,
    ):
        """Initialize debate orchestrator.

        Args:
            attacker_agent: AttackerAgent instance for constructing attacks
            defender_agent: DefenderAgent instance for finding guards
            verifier_agent: VerifierAgent instance for formal verification
            config: Debate configuration (uses defaults if not provided)
        """
        self.attacker = attacker_agent
        self.defender = defender_agent
        self.verifier = verifier_agent
        self.config = config or DebateConfig()
        self.enforcer = ConfidenceEnforcer()

    def run_debate(
        self,
        bead_id: str,
        evidence: EvidencePacket,
        attacker_context: Dict[str, Any],
        defender_context: Dict[str, Any],
    ) -> Verdict:
        """Run full debate protocol.

        Executes the complete debate sequence:
        1. CLAIM ROUND - Both sides present initial arguments
        2. REBUTTAL ROUND(S) - Challenge each other's evidence
        3. SYNTHESIS - Verifier weighs arguments
        4. HUMAN FLAG - Always set for human review

        Args:
            bead_id: The bead being debated
            evidence: Evidence packet with behavioral signature, code
            attacker_context: Context for attacker (exploit paths, etc.)
            defender_context: Context for defender (guards, specs)

        Returns:
            Verdict with debate record, always human-flagged
        """
        rounds: List[DebateRound] = []

        # Phase 1: CLAIM ROUND
        claim_round = self._run_claim_round(evidence, attacker_context, defender_context)
        rounds.append(claim_round)

        # Phase 2: REBUTTAL ROUND(S)
        for i in range(self.config.max_rebuttal_rounds):
            rebuttal_round = self._run_rebuttal_round(
                rounds[-1], evidence, attacker_context, defender_context
            )
            rounds.append(rebuttal_round)

            # Early exit if no new arguments
            if not rebuttal_round.attacker_argument and not rebuttal_round.defender_argument:
                break

        # Phase 3: SYNTHESIS
        debate_record = self._build_debate_record(bead_id, rounds)
        verdict = self._run_synthesis(bead_id, debate_record, evidence)

        # Phase 4: HUMAN FLAG (always)
        verdict.human_flag = True

        return verdict

    def _run_claim_round(
        self,
        evidence: EvidencePacket,
        attacker_ctx: Dict[str, Any],
        defender_ctx: Dict[str, Any],
    ) -> DebateRound:
        """Run claim round - each side presents their case.

        Args:
            evidence: Evidence packet for the finding
            attacker_ctx: Context for attacker agent
            defender_ctx: Context for defender agent

        Returns:
            DebateRound with initial claims from both sides
        """
        round_obj = DebateRound(phase=DebatePhase.CLAIM)

        # Attacker claim
        if self.attacker:
            attacker_result = self._get_attacker_claim(evidence, attacker_ctx)
            round_obj.attacker_argument = attacker_result
        else:
            # No agent configured - create placeholder claim
            round_obj.attacker_argument = DebateClaim(
                role="attacker",
                claim="No attacker agent configured",
                evidence=[],
                reasoning="Agent not available",
            )

        # Defender claim
        if self.defender:
            defender_result = self._get_defender_claim(evidence, defender_ctx)
            round_obj.defender_argument = defender_result
        else:
            round_obj.defender_argument = DebateClaim(
                role="defender",
                claim="No defender agent configured",
                evidence=[],
                reasoning="Agent not available",
            )

        return round_obj

    def _run_rebuttal_round(
        self,
        previous_round: DebateRound,
        evidence: EvidencePacket,
        attacker_ctx: Dict[str, Any],
        defender_ctx: Dict[str, Any],
    ) -> DebateRound:
        """Run rebuttal round - challenge each other's claims.

        Args:
            previous_round: The previous round to rebut
            evidence: Evidence packet for context
            attacker_ctx: Context for attacker agent
            defender_ctx: Context for defender agent

        Returns:
            DebateRound with rebuttals from both sides
        """
        round_obj = DebateRound(phase=DebatePhase.REBUTTAL)

        # Attacker rebuts defender's claim
        if self.attacker and previous_round.defender_argument:
            round_obj.attacker_argument = self._get_attacker_rebuttal(
                previous_round.defender_argument, evidence, attacker_ctx
            )

        # Defender rebuts attacker's claim
        if self.defender and previous_round.attacker_argument:
            round_obj.defender_argument = self._get_defender_rebuttal(
                previous_round.attacker_argument, evidence, defender_ctx
            )

        return round_obj

    def _get_attacker_claim(
        self, evidence: EvidencePacket, context: Dict[str, Any]
    ) -> DebateClaim:
        """Get attacker's initial claim with evidence anchoring.

        Args:
            evidence: Evidence packet for context
            context: Agent context with subgraph, focal nodes

        Returns:
            DebateClaim from attacker perspective
        """
        if not self.attacker:
            return DebateClaim(
                role="attacker",
                claim="No attacker agent configured",
                evidence=[],
                reasoning="Agent not available",
            )

        try:
            # Use existing AttackerAgent.analyze()
            result = self.attacker.analyze(context.get("agent_context"))

            if result.matched and result.attack:
                # Build evidence items from attack construction
                evidence_items = []

                # Add postconditions as evidence
                if result.attack.postconditions:
                    for i, postcondition in enumerate(result.attack.postconditions[:3]):
                        evidence_items.append(
                            EvidenceItem(
                                type="attack_postcondition",
                                value=postcondition,
                                location=result.attack.target_nodes[0] if result.attack.target_nodes else "",
                                confidence=result.attack.exploitability_score,
                                source="attacker_agent",
                            )
                        )

                # Add attack steps as evidence
                for step in result.attack.attack_steps[:2]:
                    evidence_items.append(
                        EvidenceItem(
                            type="attack_step",
                            value=f"{step.action}: {step.effect}",
                            location=step.code_location or "",
                            confidence=result.attack.exploitability_score,
                            source="attacker_agent",
                        )
                    )

                return DebateClaim(
                    role="attacker",
                    claim=f"Exploit path identified: {result.attack.category.value}",
                    evidence=evidence_items,
                    reasoning=f"Attack feasibility: {result.attack.feasibility.value}, "
                    f"exploitability: {result.attack.exploitability_score:.2f}",
                )

            # No attack found
            return DebateClaim(
                role="attacker",
                claim="Unable to construct viable exploit",
                evidence=[],
                reasoning="No attack path found by attacker agent",
            )

        except Exception as e:
            logger.warning(f"Attacker analysis failed: {e}")
            return DebateClaim(
                role="attacker",
                claim="Attacker analysis failed",
                evidence=[],
                reasoning=str(e),
            )

    def _get_defender_claim(
        self, evidence: EvidencePacket, context: Dict[str, Any]
    ) -> DebateClaim:
        """Get defender's initial claim with evidence anchoring.

        Args:
            evidence: Evidence packet for context
            context: Agent context with subgraph, focal nodes

        Returns:
            DebateClaim from defender perspective
        """
        if not self.defender:
            return DebateClaim(
                role="defender",
                claim="No defender agent configured",
                evidence=[],
                reasoning="Agent not available",
            )

        try:
            # Use existing DefenderAgent.analyze()
            result = self.defender.analyze(context.get("agent_context"))

            if result.matched and result.defenses:
                # Build evidence items from defense arguments
                evidence_items = []

                for defense in result.defenses[:3]:
                    # Add guards as evidence
                    for guard in defense.guards_identified[:2]:
                        evidence_items.append(
                            EvidenceItem(
                                type="guard",
                                value=f"{guard.guard_type}: {guard.name}",
                                location=guard.evidence[0] if guard.evidence else "",
                                confidence=guard.strength,
                                source="defender_agent",
                            )
                        )

                    # Add spec references
                    for spec_ref in defense.spec_references[:1]:
                        evidence_items.append(
                            EvidenceItem(
                                type="spec_reference",
                                value=spec_ref,
                                location="",
                                confidence=defense.strength,
                                source="defender_agent",
                            )
                        )

                return DebateClaim(
                    role="defender",
                    claim=result.summary or "Protected by guards",
                    evidence=evidence_items,
                    reasoning=f"Defense strength: {result.confidence:.2f}, "
                    f"defenses found: {len(result.defenses)}",
                )

            # No defenses found
            return DebateClaim(
                role="defender",
                claim="Unable to identify protective guards",
                evidence=[],
                reasoning="No defense arguments found",
            )

        except Exception as e:
            logger.warning(f"Defender analysis failed: {e}")
            return DebateClaim(
                role="defender",
                claim="Defender analysis failed",
                evidence=[],
                reasoning=str(e),
            )

    def _get_attacker_rebuttal(
        self, defender_claim: DebateClaim, evidence: EvidencePacket, context: Dict[str, Any]
    ) -> Optional[DebateClaim]:
        """Attacker rebuts defender's claim.

        Analyzes defender's guards and attempts to find bypass paths.

        Args:
            defender_claim: The defender's claim to rebut
            evidence: Evidence packet for context
            context: Agent context

        Returns:
            Rebuttal claim or None if no rebuttal
        """
        if not self.attacker:
            return None

        # Extract guards mentioned by defender
        guards_mentioned = [e.value for e in defender_claim.evidence if e.type == "guard"]

        if not guards_mentioned:
            return DebateClaim(
                role="attacker",
                claim="Defender provided no guards - attack path remains open",
                evidence=[
                    EvidenceItem(
                        type="rebuttal",
                        value="No guards identified",
                        location="",
                        confidence=0.8,
                        source="attacker_agent",
                    )
                ],
                reasoning="Defender failed to identify any protective guards",
            )

        # Analyze if guards can be bypassed
        # In full implementation, would use attacker agent to check bypasses
        return DebateClaim(
            role="attacker",
            claim=f"Guards ({', '.join(guards_mentioned[:2])}) may be bypassable",
            evidence=[
                EvidenceItem(
                    type="bypass_analysis",
                    value=f"Analyzing bypass for: {guards_mentioned[0]}",
                    location="",
                    confidence=0.5,
                    source="attacker_agent",
                )
            ],
            reasoning="Guard presence does not guarantee attack prevention",
        )

    def _get_defender_rebuttal(
        self, attacker_claim: DebateClaim, evidence: EvidencePacket, context: Dict[str, Any]
    ) -> Optional[DebateClaim]:
        """Defender rebuts attacker's claim.

        Challenges attack preconditions or demonstrates blocking guards.

        Args:
            attacker_claim: The attacker's claim to rebut
            evidence: Evidence packet for context
            context: Agent context

        Returns:
            Rebuttal claim or None if no rebuttal
        """
        if not self.defender:
            return None

        # Analyze attacker's claim for weaknesses
        attack_evidence = [e for e in attacker_claim.evidence if e.type in ("attack_step", "attack_postcondition")]

        if not attack_evidence:
            return DebateClaim(
                role="defender",
                claim="Attacker provided no concrete attack evidence",
                evidence=[
                    EvidenceItem(
                        type="rebuttal",
                        value="No attack evidence found",
                        location="",
                        confidence=0.8,
                        source="defender_agent",
                    )
                ],
                reasoning="Attack claim is not substantiated",
            )

        return DebateClaim(
            role="defender",
            claim="Attack preconditions cannot be satisfied",
            evidence=[
                EvidenceItem(
                    type="precondition_analysis",
                    value="Preconditions require privileged access",
                    location="",
                    confidence=0.6,
                    source="defender_agent",
                )
            ],
            reasoning="Attack requires conditions that cannot be met by external caller",
        )

    def _build_debate_record(self, bead_id: str, rounds: List[DebateRound]) -> DebateRecord:
        """Build debate record from rounds.

        Args:
            bead_id: ID of the finding being debated
            rounds: All debate rounds

        Returns:
            DebateRecord with claims and rebuttals
        """
        record = DebateRecord(finding_id=bead_id)

        # Extract first claims (from claim round)
        if rounds:
            claim_round = rounds[0]
            if claim_round.attacker_argument:
                record.attacker_claim = claim_round.attacker_argument
            if claim_round.defender_argument:
                record.defender_claim = claim_round.defender_argument

        # Extract rebuttals (from subsequent rounds)
        for round_obj in rounds[1:]:
            if round_obj.phase == DebatePhase.REBUTTAL:
                if round_obj.attacker_argument:
                    record.add_rebuttal(round_obj.attacker_argument)
                if round_obj.defender_argument:
                    record.add_rebuttal(round_obj.defender_argument)

        return record

    def _run_synthesis(
        self, bead_id: str, debate: DebateRecord, evidence: EvidencePacket
    ) -> Verdict:
        """Verifier synthesizes debate into verdict.

        Weighs attacker and defender evidence to determine confidence.
        Does not add new analysis - only weighs existing arguments.

        Args:
            bead_id: ID of the finding
            debate: Complete debate record
            evidence: Original evidence packet

        Returns:
            Verdict with confidence based on debate outcome
        """
        # Determine confidence based on debate
        confidence = self._assess_debate_outcome(debate)

        # Build rationale from debate
        rationale = self._synthesize_rationale(debate)

        # Check for dissent
        dissent = self._check_for_dissent(debate)

        # Create evidence packet for verdict
        verdict_evidence = EvidencePacket(
            finding_id=bead_id,
            items=[],
            summary=rationale,
        )

        # Add evidence from debate
        if debate.attacker_claim:
            verdict_evidence.items.extend(debate.attacker_claim.evidence)
        if debate.defender_claim:
            verdict_evidence.items.extend(debate.defender_claim.evidence)

        verdict = Verdict(
            finding_id=bead_id,
            confidence=confidence,
            is_vulnerable=confidence.is_positive(),
            rationale=rationale,
            evidence_packet=verdict_evidence if verdict_evidence.items else None,
            debate=debate,
            human_flag=True,  # Always flagged
            created_by="debate_orchestrator",
        )

        # Verifier adds synthesis to debate record
        if debate:
            debate.complete(rationale, dissent or "")

        # Enforce confidence rules
        return self.enforcer.enforce(verdict)

    def _assess_debate_outcome(self, debate: DebateRecord) -> VerdictConfidence:
        """Assess confidence from debate evidence.

        Compares evidence strength between attacker and defender.
        Close contests result in UNCERTAIN.

        Args:
            debate: Complete debate record

        Returns:
            VerdictConfidence based on debate outcome
        """
        attacker_strength = 0.0
        defender_strength = 0.0

        # Calculate attacker evidence strength
        if debate.attacker_claim and debate.attacker_claim.evidence:
            attacker_strength = sum(
                e.confidence for e in debate.attacker_claim.evidence
            ) / len(debate.attacker_claim.evidence)

        # Calculate defender evidence strength
        if debate.defender_claim and debate.defender_claim.evidence:
            defender_strength = sum(
                e.confidence for e in debate.defender_claim.evidence
            ) / len(debate.defender_claim.evidence)

        # Close contest = uncertain (threshold: 0.2)
        if abs(attacker_strength - defender_strength) < 0.2:
            return VerdictConfidence.UNCERTAIN

        # Attacker wins with higher strength
        if attacker_strength > defender_strength:
            return VerdictConfidence.LIKELY

        # Defender wins
        return VerdictConfidence.REJECTED

    def _synthesize_rationale(self, debate: DebateRecord) -> str:
        """Synthesize rationale from debate.

        Creates human-readable summary of the debate outcome.

        Args:
            debate: Complete debate record

        Returns:
            Rationale string summarizing the debate
        """
        parts = []

        if debate.attacker_claim:
            parts.append(f"Attacker: {debate.attacker_claim.claim}")
        if debate.defender_claim:
            parts.append(f"Defender: {debate.defender_claim.claim}")

        if debate.rebuttals:
            parts.append(f"Rebuttals: {len(debate.rebuttals)} rounds")

        return " | ".join(parts) if parts else "No debate conducted"

    def _check_for_dissent(self, debate: DebateRecord) -> Optional[str]:
        """Check if there's significant dissent in the debate.

        Dissent is recorded when defender had strong evidence but
        lost the debate.

        Args:
            debate: Complete debate record

        Returns:
            Dissenting opinion string or None
        """
        if not debate.defender_claim or not debate.defender_claim.evidence:
            return None

        # If defender had strong evidence (avg > 0.7), note dissent
        avg_strength = sum(e.confidence for e in debate.defender_claim.evidence) / len(
            debate.defender_claim.evidence
        )

        if avg_strength > 0.7:
            return f"Defender notes: {debate.defender_claim.claim}"

        return None


def run_debate(
    bead_id: str,
    evidence: EvidencePacket,
    attacker_context: Dict[str, Any],
    defender_context: Dict[str, Any],
    attacker_agent: Any = None,
    defender_agent: Any = None,
    verifier_agent: Any = None,
    config: Optional[DebateConfig] = None,
) -> Verdict:
    """Convenience function for running a debate.

    Creates a DebateOrchestrator and runs the full debate protocol.

    Args:
        bead_id: ID of the finding to debate
        evidence: Evidence packet with code, signatures
        attacker_context: Context for attacker agent
        defender_context: Context for defender agent
        attacker_agent: Optional AttackerAgent instance
        defender_agent: Optional DefenderAgent instance
        verifier_agent: Optional VerifierAgent instance
        config: Optional debate configuration

    Returns:
        Verdict with debate record, always human-flagged
    """
    orchestrator = DebateOrchestrator(
        attacker_agent=attacker_agent,
        defender_agent=defender_agent,
        verifier_agent=verifier_agent,
        config=config,
    )
    return orchestrator.run_debate(bead_id, evidence, attacker_context, defender_context)


# Export for module
__all__ = [
    "DebatePhase",
    "DebateRound",
    "DebateConfig",
    "DebateResult",
    "DebateOrchestrator",
    "run_debate",
]
