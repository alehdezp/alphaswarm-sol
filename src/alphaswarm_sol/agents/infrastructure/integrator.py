"""Integrator Agent for Multi-Agent Verdict Integration.

This module implements the IntegratorAgent per PHILOSOPHY.md Infrastructure Roles:
- Deduplicates overlapping verdicts
- Merges evidence from multiple sources
- Finalizes verdicts per bead
- Routes conflicts to debate protocol

Usage:
    from alphaswarm_sol.agents.infrastructure import IntegratorAgent, IntegratorConfig

    integrator = IntegratorAgent(config=IntegratorConfig())
    result = integrator.integrate(bead, verdicts)

    if result.conflict_detected:
        print("Debate was triggered")
    print(f"Final verdict: {result.is_vulnerable} ({result.confidence.value})")
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from alphaswarm_sol.agents.runtime import AgentRole, AgentRuntime
from alphaswarm_sol.beads.schema import VulnerabilityBead
from alphaswarm_sol.orchestration.confidence import ConfidenceEnforcer
from alphaswarm_sol.orchestration.debate import DebateOrchestrator
from alphaswarm_sol.orchestration.schemas import EvidenceItem, EvidencePacket, VerdictConfidence

logger = logging.getLogger(__name__)


@dataclass
class AgentVerdict:
    """Single agent's verdict on a bead.

    Represents the analysis result from one agent (attacker, defender, or verifier).

    Attributes:
        agent_role: Which agent produced this verdict
        is_vulnerable: Agent's determination on vulnerability status
        confidence: Agent's confidence in their determination (0.0-1.0)
        rationale: Explanation of the verdict
        evidence: List of evidence items supporting the verdict

    Usage:
        verdict = AgentVerdict(
            agent_role=AgentRole.ATTACKER,
            is_vulnerable=True,
            confidence=0.9,
            rationale="Found reentrancy vulnerability",
            evidence=[EvidenceItem(type="pattern", value="R:bal->X:out->W:bal", location="Vault.sol:42")],
        )
    """

    agent_role: AgentRole
    is_vulnerable: bool
    confidence: float
    rationale: str
    evidence: List[EvidenceItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_role": self.agent_role.value,
            "is_vulnerable": self.is_vulnerable,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "evidence": [e.to_dict() for e in self.evidence],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentVerdict":
        """Create AgentVerdict from dictionary."""
        return cls(
            agent_role=AgentRole(data["agent_role"]),
            is_vulnerable=bool(data["is_vulnerable"]),
            confidence=float(data["confidence"]),
            rationale=str(data.get("rationale", "")),
            evidence=[EvidenceItem.from_dict(e) for e in data.get("evidence", [])],
        )


@dataclass
class IntegratorConfig:
    """Configuration for integrator agent.

    Attributes:
        conflict_threshold: Confidence difference above which = conflict (default: 0.3)
        require_all_agents: Whether to require all agents for integration (default: False)
        auto_debate_on_conflict: Whether to automatically trigger debate on conflict (default: True)
        high_confidence_threshold: Threshold for high confidence disagreement (default: 0.7)

    Usage:
        config = IntegratorConfig(
            conflict_threshold=0.4,
            auto_debate_on_conflict=True,
        )
    """

    conflict_threshold: float = 0.3
    require_all_agents: bool = False
    auto_debate_on_conflict: bool = True
    high_confidence_threshold: float = 0.7

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "conflict_threshold": self.conflict_threshold,
            "require_all_agents": self.require_all_agents,
            "auto_debate_on_conflict": self.auto_debate_on_conflict,
            "high_confidence_threshold": self.high_confidence_threshold,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntegratorConfig":
        """Create IntegratorConfig from dictionary."""
        return cls(
            conflict_threshold=float(data.get("conflict_threshold", 0.3)),
            require_all_agents=bool(data.get("require_all_agents", False)),
            auto_debate_on_conflict=bool(data.get("auto_debate_on_conflict", True)),
            high_confidence_threshold=float(data.get("high_confidence_threshold", 0.7)),
        )


@dataclass
class MergedVerdict:
    """Result of integrating multiple agent verdicts.

    Represents the final integrated verdict from all agents, including
    evidence merging and conflict resolution.

    Attributes:
        bead_id: ID of the bead this verdict is for
        is_vulnerable: Final vulnerability determination
        confidence: Confidence level per PHILOSOPHY.md buckets
        merged_evidence: All evidence items merged and deduplicated
        agent_verdicts: Map of role name to individual agent verdicts
        conflict_detected: Whether agents had conflicting verdicts
        debate_triggered: Whether debate protocol was invoked
        rationale: Human-readable explanation of the verdict

    Usage:
        result = integrator.integrate(bead, verdicts)
        print(f"Verdict: {result.is_vulnerable}, Confidence: {result.confidence.value}")
        if result.debate_triggered:
            print("Resolved via debate")
    """

    bead_id: str
    is_vulnerable: bool
    confidence: VerdictConfidence
    merged_evidence: List[EvidenceItem]
    agent_verdicts: Dict[str, AgentVerdict]
    conflict_detected: bool
    debate_triggered: bool
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "bead_id": self.bead_id,
            "is_vulnerable": self.is_vulnerable,
            "confidence": self.confidence.value,
            "merged_evidence": [e.to_dict() for e in self.merged_evidence],
            "agent_verdicts": {k: v.to_dict() for k, v in self.agent_verdicts.items()},
            "conflict_detected": self.conflict_detected,
            "debate_triggered": self.debate_triggered,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MergedVerdict":
        """Create MergedVerdict from dictionary."""
        return cls(
            bead_id=str(data["bead_id"]),
            is_vulnerable=bool(data["is_vulnerable"]),
            confidence=VerdictConfidence.from_string(data["confidence"]),
            merged_evidence=[EvidenceItem.from_dict(e) for e in data.get("merged_evidence", [])],
            agent_verdicts={k: AgentVerdict.from_dict(v) for k, v in data.get("agent_verdicts", {}).items()},
            conflict_detected=bool(data.get("conflict_detected", False)),
            debate_triggered=bool(data.get("debate_triggered", False)),
            rationale=str(data.get("rationale", "")),
        )


class IntegratorAgent:
    """Merges verdicts from multiple agents into final determination.

    Integration process:
    1. Collect verdicts from attacker, defender, verifier
    2. Check for conflicts (disagreement on vulnerability)
    3. If conflict: route to debate protocol
    4. If agreement: merge evidence, determine confidence
    5. Apply confidence enforcement rules

    Per PHILOSOPHY.md Infrastructure Roles:
    - Integrator dedupes overlaps, merges evidence, finalizes verdicts
    - Conflicts route to debate protocol
    - All verdicts require human review

    Usage:
        from alphaswarm_sol.agents.infrastructure import IntegratorAgent, IntegratorConfig

        integrator = IntegratorAgent(
            config=IntegratorConfig(auto_debate_on_conflict=True),
            debate_orchestrator=DebateOrchestrator(),
        )

        result = integrator.integrate(bead, {
            AgentRole.ATTACKER: attacker_verdict,
            AgentRole.DEFENDER: defender_verdict,
            AgentRole.VERIFIER: verifier_verdict,
        })

        if result.is_vulnerable:
            print(f"VULNERABLE ({result.confidence.value}): {result.rationale}")
    """

    def __init__(
        self,
        config: Optional[IntegratorConfig] = None,
        debate_orchestrator: Optional[DebateOrchestrator] = None,
        confidence_enforcer: Optional[ConfidenceEnforcer] = None,
        runtime: Optional[AgentRuntime] = None,
    ):
        """Initialize integrator agent.

        Args:
            config: Integrator configuration. Uses defaults if not provided.
            debate_orchestrator: Orchestrator for conflict resolution. Created if not provided.
            confidence_enforcer: Enforcer for confidence rules. Created if not provided.
            runtime: Optional agent runtime for LLM-assisted integration.
        """
        self.config = config or IntegratorConfig()
        self.debate = debate_orchestrator or DebateOrchestrator()
        self.enforcer = confidence_enforcer or ConfidenceEnforcer()
        self.runtime = runtime

    def integrate(
        self,
        bead: VulnerabilityBead,
        verdicts: Dict[AgentRole, AgentVerdict],
    ) -> MergedVerdict:
        """Integrate multiple agent verdicts into final verdict.

        Args:
            bead: The vulnerability bead being analyzed
            verdicts: Map of agent role to their verdict

        Returns:
            MergedVerdict with final determination

        Raises:
            ValueError: If require_all_agents=True and agents are missing
        """
        if self.config.require_all_agents:
            required = {AgentRole.ATTACKER, AgentRole.DEFENDER, AgentRole.VERIFIER}
            missing = required - set(verdicts.keys())
            if missing:
                raise ValueError(f"Missing required agent verdicts: {missing}")

        # Check for conflicts
        conflict = self._detect_conflict(verdicts)

        if conflict and self.config.auto_debate_on_conflict:
            # Route to debate protocol
            logger.info(f"Conflict detected for {bead.id}, triggering debate")
            debate_result = self._trigger_debate(bead, verdicts)
            return self._verdict_from_debate(bead.id, debate_result, verdicts)

        # No conflict - merge evidence
        merged_evidence = self._merge_evidence(verdicts)
        is_vulnerable = self._determine_vulnerability(verdicts)
        confidence = self._determine_confidence(verdicts, merged_evidence)
        rationale = self._generate_rationale(verdicts, is_vulnerable)

        return MergedVerdict(
            bead_id=bead.id,
            is_vulnerable=is_vulnerable,
            confidence=confidence,
            merged_evidence=merged_evidence,
            agent_verdicts={r.value: v for r, v in verdicts.items()},
            conflict_detected=conflict,
            debate_triggered=False,
            rationale=rationale,
        )

    def _detect_conflict(self, verdicts: Dict[AgentRole, AgentVerdict]) -> bool:
        """Detect if agents have conflicting verdicts.

        Conflict conditions:
        1. Attacker says vulnerable, defender says safe
        2. Both have high confidence but opposite conclusions

        Args:
            verdicts: Map of agent role to their verdict

        Returns:
            True if conflict detected, False otherwise
        """
        attacker = verdicts.get(AgentRole.ATTACKER)
        defender = verdicts.get(AgentRole.DEFENDER)

        if attacker and defender:
            # Conflict: attacker says vulnerable, defender says safe
            if attacker.is_vulnerable and not defender.is_vulnerable:
                return True
            # Conflict: both claim opposite with high confidence
            if attacker.is_vulnerable != defender.is_vulnerable:
                threshold = self.config.high_confidence_threshold
                if attacker.confidence > threshold and defender.confidence > threshold:
                    return True

        return False

    def _merge_evidence(
        self, verdicts: Dict[AgentRole, AgentVerdict]
    ) -> List[EvidenceItem]:
        """Merge evidence from all agents, deduplicating by content.

        Evidence items are deduplicated by hashing their type and value.
        Source attribution is preserved via source field.

        Args:
            verdicts: Map of agent role to their verdict

        Returns:
            List of deduplicated evidence items
        """
        seen_hashes: Set[str] = set()
        merged: List[EvidenceItem] = []

        for role, verdict in verdicts.items():
            for evidence in verdict.evidence:
                # Hash evidence for deduplication
                content_hash = hashlib.sha256(
                    f"{evidence.type}:{evidence.value}".encode()
                ).hexdigest()[:12]

                if content_hash not in seen_hashes:
                    seen_hashes.add(content_hash)
                    # Create new evidence item with source attribution
                    merged.append(
                        EvidenceItem(
                            type=evidence.type,
                            value=evidence.value,
                            location=evidence.location,
                            confidence=evidence.confidence,
                            source=role.value,
                        )
                    )

        return merged

    def _determine_vulnerability(
        self, verdicts: Dict[AgentRole, AgentVerdict]
    ) -> bool:
        """Determine final vulnerability status.

        Priority order:
        1. Verifier's verdict takes precedence if present
        2. If attacker and defender agree, use that
        3. If they disagree, higher confidence wins
        4. Single agent case: use available verdict

        Args:
            verdicts: Map of agent role to their verdict

        Returns:
            True if vulnerable, False otherwise
        """
        # Verifier's verdict takes precedence if present
        verifier = verdicts.get(AgentRole.VERIFIER)
        if verifier:
            return verifier.is_vulnerable

        # Otherwise, weighted average of attacker/defender
        attacker = verdicts.get(AgentRole.ATTACKER)
        defender = verdicts.get(AgentRole.DEFENDER)

        if attacker and defender:
            # If both agree, use that
            if attacker.is_vulnerable == defender.is_vulnerable:
                return attacker.is_vulnerable
            # Otherwise, higher confidence wins
            if attacker.confidence > defender.confidence:
                return attacker.is_vulnerable
            return defender.is_vulnerable

        # Single agent case
        if attacker:
            return attacker.is_vulnerable
        if defender:
            return defender.is_vulnerable

        return False

    def _determine_confidence(
        self,
        verdicts: Dict[AgentRole, AgentVerdict],
        evidence: List[EvidenceItem],
    ) -> VerdictConfidence:
        """Determine confidence level per PHILOSOPHY.md buckets.

        Confidence rules:
        - CONFIRMED: requires test pass (not achievable without test)
        - LIKELY: unanimous agreement with high avg confidence (>= 0.9)
                  or unanimous agreement with good confidence (>= 0.7)
        - UNCERTAIN: single agent, disagreement, or low confidence

        Args:
            verdicts: Map of agent role to their verdict
            evidence: Merged evidence items

        Returns:
            VerdictConfidence level
        """
        # Check for unanimous agreement
        all_verdicts = list(verdicts.values())
        if len(all_verdicts) >= 2:
            all_agree = all(v.is_vulnerable == all_verdicts[0].is_vulnerable for v in all_verdicts)
            avg_confidence = sum(v.confidence for v in all_verdicts) / len(all_verdicts)

            if all_agree and avg_confidence >= 0.9:
                # Still needs test for CONFIRMED - return LIKELY
                return VerdictConfidence.LIKELY
            elif all_agree and avg_confidence >= 0.7:
                return VerdictConfidence.LIKELY
            elif all_agree:
                return VerdictConfidence.UNCERTAIN

        # Single agent or disagreement
        return VerdictConfidence.UNCERTAIN

    def _generate_rationale(
        self,
        verdicts: Dict[AgentRole, AgentVerdict],
        is_vulnerable: bool,
    ) -> str:
        """Generate human-readable rationale for the verdict.

        Args:
            verdicts: Map of agent role to their verdict
            is_vulnerable: Final vulnerability determination

        Returns:
            Human-readable rationale string
        """
        parts = []
        for role, verdict in sorted(verdicts.items(), key=lambda x: x[0].value):
            status = "vulnerable" if verdict.is_vulnerable else "safe"
            parts.append(f"{role.value}: {status} (conf={verdict.confidence:.0%})")

        summary = "VULNERABLE" if is_vulnerable else "SAFE"
        return f"Integrated verdict: {summary}. {'; '.join(parts)}"

    def _trigger_debate(
        self,
        bead: VulnerabilityBead,
        verdicts: Dict[AgentRole, AgentVerdict],
    ) -> Any:
        """Trigger debate protocol for conflicting verdicts.

        Uses the existing debate orchestrator from Phase 4.

        Args:
            bead: The vulnerability bead being debated
            verdicts: Map of agent role to their verdict

        Returns:
            Debate result from DebateOrchestrator
        """
        # Build evidence packet from verdicts
        evidence_items = []
        for role, verdict in verdicts.items():
            evidence_items.extend(verdict.evidence)

        evidence_packet = EvidencePacket(
            finding_id=bead.id,
            items=evidence_items,
            summary=f"Evidence from {len(verdicts)} agents",
        )

        # Build context for debate
        attacker_ctx = {"agent_context": verdicts.get(AgentRole.ATTACKER)}
        defender_ctx = {"agent_context": verdicts.get(AgentRole.DEFENDER)}

        # Run debate using existing Phase 4 infrastructure
        return self.debate.run_debate(
            bead_id=bead.id,
            evidence=evidence_packet,
            attacker_context=attacker_ctx,
            defender_context=defender_ctx,
        )

    def _verdict_from_debate(
        self,
        bead_id: str,
        debate_result: Any,
        verdicts: Dict[AgentRole, AgentVerdict],
    ) -> MergedVerdict:
        """Create merged verdict from debate result.

        Args:
            bead_id: ID of the bead
            debate_result: Result from debate orchestrator
            verdicts: Original agent verdicts

        Returns:
            MergedVerdict based on debate outcome
        """
        # Extract verdict from debate outcome
        is_vulnerable = debate_result.is_vulnerable
        confidence = VerdictConfidence.from_string(debate_result.confidence.value)

        return MergedVerdict(
            bead_id=bead_id,
            is_vulnerable=is_vulnerable,
            confidence=confidence,
            merged_evidence=self._merge_evidence(verdicts),
            agent_verdicts={r.value: v for r, v in verdicts.items()},
            conflict_detected=True,
            debate_triggered=True,
            rationale=f"Resolved via debate: {debate_result.rationale}",
        )


# Export for module
__all__ = [
    "AgentVerdict",
    "IntegratorConfig",
    "MergedVerdict",
    "IntegratorAgent",
]
