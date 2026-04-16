"""Phase 9: Agent Consensus.

The AgentConsensus class aggregates results from multiple verification agents
and produces a final verdict based on agreement between agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from enum import Enum

from alphaswarm_sol.agents.base import (
    VerificationAgent,
    AgentResult,
    AgentEvidence,
)

if TYPE_CHECKING:
    from alphaswarm_sol.kg.subgraph import SubGraph


class Verdict(str, Enum):
    """Consensus verdict levels."""
    HIGH_RISK = "HIGH_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    LOW_RISK = "LOW_RISK"
    LIKELY_SAFE = "LIKELY_SAFE"


@dataclass
class ConsensusResult:
    """Result of multi-agent consensus.

    Aggregates findings from all agents and produces a final verdict.
    """
    verdict: Verdict
    agents_agreed: int
    total_agents: int
    agent_results: List[AgentResult] = field(default_factory=list)
    evidence: List[AgentEvidence] = field(default_factory=list)
    confidence: float = 0.0
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "agents_agreed": self.agents_agreed,
            "total_agents": self.total_agents,
            "agent_results": [r.to_dict() for r in self.agent_results],
            "evidence": [e.to_dict() for e in self.evidence],
            "confidence": self.confidence,
            "summary": self.summary,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ConsensusResult":
        verdict_str = data.get("verdict", "LIKELY_SAFE")
        try:
            verdict = Verdict(verdict_str)
        except ValueError:
            verdict = Verdict.LIKELY_SAFE

        return ConsensusResult(
            verdict=verdict,
            agents_agreed=int(data.get("agents_agreed", 0)),
            total_agents=int(data.get("total_agents", 0)),
            agent_results=[AgentResult.from_dict(r) for r in data.get("agent_results", [])],
            evidence=[AgentEvidence.from_dict(e) for e in data.get("evidence", [])],
            confidence=float(data.get("confidence", 0.0)),
            summary=str(data.get("summary", "")),
        )


class AgentConsensus:
    """Multi-agent consensus system.

    Aggregates results from multiple verification agents to produce
    a final verdict. The verdict is based on the proportion of agents
    that found vulnerabilities.

    Verdict thresholds:
    - HIGH_RISK: >= 75% of agents found issues
    - MEDIUM_RISK: >= 50% of agents found issues
    - LOW_RISK: At least 1 agent found issues
    - LIKELY_SAFE: No agents found issues
    """

    # Threshold for each verdict level (proportion of agents agreeing)
    HIGH_RISK_THRESHOLD = 0.75
    MEDIUM_RISK_THRESHOLD = 0.50

    def __init__(
        self,
        agents: List[VerificationAgent],
        high_risk_threshold: float = 0.75,
        medium_risk_threshold: float = 0.50,
    ):
        """Initialize the consensus system.

        Args:
            agents: List of verification agents to use
            high_risk_threshold: Proportion for HIGH_RISK verdict
            medium_risk_threshold: Proportion for MEDIUM_RISK verdict
        """
        self.agents = agents
        self.high_risk_threshold = high_risk_threshold
        self.medium_risk_threshold = medium_risk_threshold

    def verify(self, subgraph: "SubGraph", query: str = "") -> ConsensusResult:
        """Run all agents and compute consensus verdict.

        Args:
            subgraph: SubGraph to analyze
            query: Optional query context

        Returns:
            ConsensusResult with verdict and aggregated evidence
        """
        # Run all agents
        results = []
        for agent in self.agents:
            try:
                result = agent.analyze(subgraph, query)
                results.append(result)
            except Exception as e:
                # Create error result for failed agent
                results.append(AgentResult(
                    agent=agent.agent_name,
                    matched=False,
                    findings=[],
                    confidence=0.0,
                    metadata={"error": str(e)},
                ))

        # Count agents with findings
        agents_with_findings = sum(1 for r in results if r.matched)
        total_agents = len(self.agents)

        # Determine verdict
        if total_agents == 0:
            verdict = Verdict.LIKELY_SAFE
        else:
            proportion = agents_with_findings / total_agents

            if proportion >= self.high_risk_threshold:
                verdict = Verdict.HIGH_RISK
            elif proportion >= self.medium_risk_threshold:
                verdict = Verdict.MEDIUM_RISK
            elif agents_with_findings >= 1:
                verdict = Verdict.LOW_RISK
            else:
                verdict = Verdict.LIKELY_SAFE

        # Merge evidence from all agents
        merged_evidence = self._merge_evidence(results)

        # Compute overall confidence
        confidence = self._compute_consensus_confidence(results, verdict)

        # Generate summary
        summary = self._generate_summary(results, verdict)

        return ConsensusResult(
            verdict=verdict,
            agents_agreed=agents_with_findings,
            total_agents=total_agents,
            agent_results=results,
            evidence=merged_evidence,
            confidence=confidence,
            summary=summary,
        )

    def _merge_evidence(self, results: List[AgentResult]) -> List[AgentEvidence]:
        """Merge evidence from all agent results.

        Deduplicates evidence based on source nodes and description.
        """
        merged = []
        seen = set()

        for result in results:
            for evidence in result.evidence:
                # Create a key for deduplication
                key = (
                    evidence.type.value if hasattr(evidence.type, 'value') else str(evidence.type),
                    evidence.description,
                    tuple(sorted(evidence.source_nodes)),
                )
                if key not in seen:
                    seen.add(key)
                    merged.append(evidence)

        # Sort by confidence
        merged.sort(key=lambda e: e.confidence, reverse=True)

        return merged

    def _compute_consensus_confidence(
        self, results: List[AgentResult], verdict: Verdict
    ) -> float:
        """Compute overall confidence score for the consensus.

        Takes into account:
        - Agreement between agents
        - Individual agent confidences
        - Verdict severity
        """
        if not results:
            return 0.0

        # Base confidence from agent agreement
        matched = [r for r in results if r.matched]
        total = len(results)

        if total == 0:
            return 0.0

        agreement_ratio = len(matched) / total

        # Weight by individual agent confidences
        if matched:
            avg_confidence = sum(r.confidence for r in matched) / len(matched)
        else:
            avg_confidence = sum(r.confidence for r in results) / total

        # Combine agreement and confidence
        combined = (agreement_ratio * 0.4) + (avg_confidence * 0.6)

        # Adjust based on verdict
        if verdict == Verdict.HIGH_RISK:
            combined *= 1.1  # Boost for high agreement
        elif verdict == Verdict.LIKELY_SAFE and agreement_ratio == 0:
            combined *= 0.9  # Slight penalty for no findings (might be FN)

        return min(combined, 1.0)

    def _generate_summary(
        self, results: List[AgentResult], verdict: Verdict
    ) -> str:
        """Generate a human-readable summary of the consensus."""
        matched = [r for r in results if r.matched]
        total = len(results)
        matched_count = len(matched)

        if verdict == Verdict.HIGH_RISK:
            return (
                f"HIGH RISK: {matched_count}/{total} agents detected vulnerabilities. "
                f"Strong consensus on security issues. Immediate review recommended."
            )
        elif verdict == Verdict.MEDIUM_RISK:
            return (
                f"MEDIUM RISK: {matched_count}/{total} agents detected potential issues. "
                f"Partial consensus on vulnerabilities. Further investigation needed."
            )
        elif verdict == Verdict.LOW_RISK:
            return (
                f"LOW RISK: {matched_count}/{total} agents flagged possible issues. "
                f"Limited agreement - may be false positive. Verify manually."
            )
        else:
            return (
                f"LIKELY SAFE: {matched_count}/{total} agents found no issues. "
                f"No vulnerabilities detected by any agent."
            )

    def add_agent(self, agent: VerificationAgent) -> None:
        """Add an agent to the consensus system."""
        self.agents.append(agent)

    def remove_agent(self, agent_name: str) -> bool:
        """Remove an agent by name."""
        for i, agent in enumerate(self.agents):
            if agent.agent_name == agent_name:
                self.agents.pop(i)
                return True
        return False

    def list_agents(self) -> List[str]:
        """List all agent names."""
        return [agent.agent_name for agent in self.agents]
