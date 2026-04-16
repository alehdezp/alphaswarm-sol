"""
P2-T6: Enhanced Agent Consensus

Integrates adversarial debate system with existing voting-based consensus.
Supports both modes with backward compatibility.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from alphaswarm_sol.agents.consensus import AgentConsensus, ConsensusResult, Verdict
from alphaswarm_sol.agents.arbiter import (
    AdversarialArbiter,
    ArbitrationResult,
    VerdictType,
)
from alphaswarm_sol.agents.attacker import AttackerAgent, AttackerResult
from alphaswarm_sol.agents.defender import DefenderAgent, DefenderResult
from alphaswarm_sol.routing import AgentRouter, AgentType, AgentContext

if TYPE_CHECKING:
    from alphaswarm_sol.kg.subgraph import SubGraph
    from alphaswarm_sol.agents.base import VerificationAgent

logger = logging.getLogger(__name__)


class ConsensusMode(str, Enum):
    """Consensus modes."""

    ADVERSARIAL = "adversarial"  # New: Attacker vs Defender with Arbiter
    VOTING = "voting"  # Old: 4-agent voting
    AUTO = "auto"  # Auto-select based on context


@dataclass
class EnhancedConsensusResult:
    """
    Enhanced consensus result supporting both modes.

    Provides unified interface regardless of underlying consensus mechanism.
    """

    verdict: Verdict
    confidence: float
    mode: ConsensusMode
    summary: str

    # Mode-specific results
    arbitration: Optional[ArbitrationResult] = None  # For adversarial mode
    voting_result: Optional[ConsensusResult] = None  # For voting mode

    # Unified fields
    evidence: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "verdict": self.verdict.value,
            "confidence": self.confidence,
            "mode": self.mode.value,
            "summary": self.summary,
            "metadata": self.metadata,
        }

        if self.arbitration:
            result["arbitration"] = {
                "verdict": self.arbitration.verdict.value,
                "confidence": self.arbitration.confidence,
                "confidence_level": self.arbitration.confidence_level.value,
                "winning_side": self.arbitration.winning_side.value,
                "explanation": self.arbitration.explanation,
                "recommendations": self.arbitration.recommendations,
            }

        if self.voting_result:
            result["voting"] = self.voting_result.to_dict()

        return result


class EnhancedAgentConsensus:
    """
    Enhanced consensus system supporting both voting and adversarial modes.

    Modes:
    - ADVERSARIAL: New debate system (Attacker vs Defender with Arbiter)
    - VOTING: Legacy 4-agent voting
    - AUTO: Automatically choose based on available agents

    Backward Compatibility:
    - Voting mode uses existing AgentConsensus
    - API compatible with old consensus.verify()
    - Deprecation warnings for voting mode
    """

    def __init__(
        self,
        mode: ConsensusMode = ConsensusMode.ADVERSARIAL,
        agents: Optional[List["VerificationAgent"]] = None,
        kg: Optional[Any] = None,
        high_risk_threshold: float = 0.75,
        medium_risk_threshold: float = 0.50,
    ):
        """
        Initialize enhanced consensus.

        Args:
            mode: Consensus mode (adversarial, voting, auto)
            agents: List of agents (for voting mode)
            kg: Knowledge graph (for adversarial mode)
            high_risk_threshold: Threshold for HIGH_RISK verdict (voting mode)
            medium_risk_threshold: Threshold for MEDIUM_RISK verdict (voting mode)
        """
        self.mode = mode
        self.kg = kg
        self.logger = logging.getLogger(__name__)

        # Always initialize voting_consensus (even if None) for compatibility
        self.voting_consensus = None
        # Initialize voting if: (1) voting mode, (2) auto mode, or (3) agents provided (for override capability)
        if agents and (mode == ConsensusMode.VOTING or mode == ConsensusMode.AUTO or mode == ConsensusMode.ADVERSARIAL):
            self.voting_consensus = AgentConsensus(
                agents, high_risk_threshold, medium_risk_threshold
            )

        # Always initialize adversarial components (even if partially) for compatibility
        self.router = None
        self.attacker = None
        self.defender = None
        self.arbiter = None

        # Initialize adversarial components if needed
        if mode == ConsensusMode.ADVERSARIAL or mode == ConsensusMode.AUTO:
            self.router = AgentRouter(kg) if kg else None
            self.attacker = AttackerAgent()
            self.defender = DefenderAgent()
            self.arbiter = AdversarialArbiter()

            # Register agents if router exists
            if self.router:
                self.router.register_agent(AgentType.ATTACKER, self.attacker)
                self.router.register_agent(AgentType.DEFENDER, self.defender)

    def verify(
        self,
        subgraph: "SubGraph",
        query: str = "",
        mode_override: Optional[ConsensusMode] = None,
    ) -> EnhancedConsensusResult:
        """
        Run consensus verification.

        Args:
            subgraph: SubGraph to analyze
            query: Optional query context
            mode_override: Override configured mode for this call

        Returns:
            EnhancedConsensusResult with verdict and evidence
        """
        effective_mode = mode_override or self.mode

        # Auto mode: choose based on available components
        if effective_mode == ConsensusMode.AUTO:
            effective_mode = self._auto_select_mode()

        # Route to appropriate analysis
        if effective_mode == ConsensusMode.ADVERSARIAL:
            return self._adversarial_analysis(subgraph, query)
        elif effective_mode == ConsensusMode.VOTING:
            return self._voting_analysis(subgraph, query)
        else:
            raise ValueError(f"Unknown consensus mode: {effective_mode}")

    def _auto_select_mode(self) -> ConsensusMode:
        """Auto-select mode based on available components."""
        # Prefer adversarial if available
        if self.router and self.kg:
            return ConsensusMode.ADVERSARIAL

        # Fall back to voting if available
        if self.voting_consensus:
            warnings.warn(
                "Auto-selecting VOTING mode. Consider upgrading to ADVERSARIAL mode.",
                DeprecationWarning,
                stacklevel=2,
            )
            return ConsensusMode.VOTING

        # Default to adversarial
        return ConsensusMode.ADVERSARIAL

    def _adversarial_analysis(
        self, subgraph: "SubGraph", query: str
    ) -> EnhancedConsensusResult:
        """
        Run adversarial debate analysis.

        Pipeline:
        1. Route to attacker agent
        2. Route to defender agent (with attacker results)
        3. Arbitrate between them
        4. Convert to unified result format
        """
        try:
            # Extract focal nodes from subgraph
            focal_nodes = self._extract_focal_nodes(subgraph)

            # Route to attacker and defender with chaining
            if self.router:
                results = self.router.route_with_chaining(focal_nodes=focal_nodes)

                attacker_result = results.get(AgentType.ATTACKER)
                defender_result = results.get(AgentType.DEFENDER)
            else:
                # Manual execution without router
                # Create minimal context for agents
                from unittest.mock import Mock

                mock_subgraph = Mock()
                mock_subgraph.nodes = {}
                mock_subgraph.edges = {}
                mock_subgraph.focal_nodes = focal_nodes

                context = AgentContext(
                    agent_type=AgentType.ATTACKER,
                    focal_nodes=focal_nodes,
                    subgraph=mock_subgraph,
                    upstream_results=[],
                )

                attacker_result = self.attacker.analyze(context)

                # Update context for defender
                context.agent_type = AgentType.DEFENDER
                context.upstream_results = [attacker_result]
                defender_result = self.defender.analyze(context)

            # Arbitrate
            arbitration = self.arbiter.arbitrate(
                attacker_result=attacker_result,
                defender_result=defender_result,
                verifier_result=None,
                cross_graph_context=None,
            )

            # Convert to unified format
            return self._convert_arbitration_to_result(
                arbitration, attacker_result, defender_result
            )

        except Exception as e:
            self.logger.error(f"Adversarial analysis error: {e}", exc_info=True)
            return EnhancedConsensusResult(
                verdict=Verdict.LIKELY_SAFE,
                confidence=0.0,
                mode=ConsensusMode.ADVERSARIAL,
                summary=f"Error during adversarial analysis: {str(e)}",
                metadata={"error": str(e)},
            )

    def _voting_analysis(
        self, subgraph: "SubGraph", query: str
    ) -> EnhancedConsensusResult:
        """
        Run voting-based consensus (legacy mode).

        Emits deprecation warning.
        """
        # Emit deprecation warning
        warnings.warn(
            "Voting consensus mode is deprecated. "
            "Consider upgrading to adversarial mode for improved accuracy. "
            "Voting mode will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )

        if not self.voting_consensus:
            raise ValueError("Voting mode requires agents to be configured")

        # Run voting consensus
        voting_result = self.voting_consensus.verify(subgraph, query)

        # Convert to unified format
        return EnhancedConsensusResult(
            verdict=voting_result.verdict,
            confidence=voting_result.confidence,
            mode=ConsensusMode.VOTING,
            summary=voting_result.summary,
            voting_result=voting_result,
            evidence=voting_result.evidence,
            metadata={
                "agents_agreed": voting_result.agents_agreed,
                "total_agents": voting_result.total_agents,
            },
        )

    def _convert_arbitration_to_result(
        self,
        arbitration: ArbitrationResult,
        attacker_result: Optional[AttackerResult],
        defender_result: Optional[DefenderResult],
    ) -> EnhancedConsensusResult:
        """
        Convert ArbitrationResult to EnhancedConsensusResult.

        Maps VerdictType to Verdict and preserves all evidence.
        """
        # Map VerdictType to Verdict
        verdict_map = {
            VerdictType.VULNERABLE: Verdict.HIGH_RISK,
            VerdictType.SAFE: Verdict.LIKELY_SAFE,
            VerdictType.UNCERTAIN: Verdict.MEDIUM_RISK,
        }

        verdict = verdict_map.get(arbitration.verdict, Verdict.MEDIUM_RISK)

        # Adjust verdict based on confidence
        if arbitration.verdict == VerdictType.VULNERABLE:
            if arbitration.confidence >= 0.8:
                verdict = Verdict.HIGH_RISK
            elif arbitration.confidence >= 0.5:
                verdict = Verdict.MEDIUM_RISK
            else:
                verdict = Verdict.LOW_RISK

        # Build summary
        summary = f"{arbitration.explanation}\n\nRecommendations:\n"
        for rec in arbitration.recommendations:
            summary += f"  - {rec}\n"

        # Collect evidence
        evidence = list(arbitration.evidence_chain.all_evidence)

        return EnhancedConsensusResult(
            verdict=verdict,
            confidence=arbitration.confidence,
            mode=ConsensusMode.ADVERSARIAL,
            summary=summary,
            arbitration=arbitration,
            evidence=evidence,
            metadata={
                "winning_side": arbitration.winning_side.value,
                "confidence_level": arbitration.confidence_level.value,
                "attacker_confidence": (
                    attacker_result.confidence if attacker_result else 0.0
                ),
                "defender_confidence": (
                    defender_result.confidence if defender_result else 0.0
                ),
                "evidence_count": len(evidence),
            },
        )

    def _extract_focal_nodes(self, subgraph: "SubGraph") -> List[str]:
        """Extract focal node IDs from subgraph."""
        # Try to get focal nodes from subgraph
        if hasattr(subgraph, "focal_nodes") and subgraph.focal_nodes:
            # Limit to 5 even if more provided
            focal = subgraph.focal_nodes
            return focal[:5] if len(focal) > 5 else focal

        # Fall back to extracting from graph
        if hasattr(subgraph, "nodes"):
            # Prioritize function nodes
            function_nodes = [
                n.id
                for n in subgraph.nodes.values()
                if n.type.value == "function" if hasattr(n, "type")
            ]
            if function_nodes:
                return function_nodes[:5]  # Limit to 5

            # Fall back to any nodes
            return list(subgraph.nodes.keys())[:5]

        return []

    def add_agent(self, agent: "VerificationAgent") -> None:
        """Add agent to voting consensus (backward compatibility)."""
        if self.voting_consensus:
            self.voting_consensus.add_agent(agent)
        else:
            raise ValueError("Cannot add agents in adversarial mode")

    def remove_agent(self, agent_name: str) -> bool:
        """Remove agent from voting consensus (backward compatibility)."""
        if self.voting_consensus:
            return self.voting_consensus.remove_agent(agent_name)
        return False

    def list_agents(self) -> List[str]:
        """List agents (mode-aware)."""
        if self.mode == ConsensusMode.ADVERSARIAL:
            return ["AttackerAgent", "DefenderAgent", "AdversarialArbiter"]
        elif self.voting_consensus:
            return self.voting_consensus.list_agents()
        return []
