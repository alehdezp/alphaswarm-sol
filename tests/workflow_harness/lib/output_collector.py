"""Collect and aggregate scenario run results into structured observation models.

Provides the core data models for team-level and agent-level observations,
and an OutputCollector that bridges raw run artifacts into the structured
data that the 3.1c evaluation pipeline needs.

Key models:
- InboxMessage: A SendMessage exchange between agents
- AgentObservation: Per-agent transcript + queries + messages
- TeamObservation: Cross-agent observation linking agents to event stream
- CollectedOutput: Aggregated output from a single scenario run
- EvaluationGuidance: Per-scenario guidance for the evaluation pipeline
- OutputCollector: Aggregates run artifacts into CollectedOutput
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from tests.workflow_harness.lib.controller_events import EventStream
from tests.workflow_harness.lib.transcript_parser import BSKGQuery, TranscriptParser


@dataclass
class InboxMessage:
    """A SendMessage exchange between agents.

    Attributes:
        sender: Sender agent identifier.
        recipient: Recipient agent identifier or "broadcast".
        content: Full message body text.
        timestamp: ISO 8601 timestamp.
        message_type: Classification -- "task_assignment", "finding", "question",
            "response", "shutdown_request", or "general".
    """

    sender: str
    recipient: str
    content: str
    timestamp: str
    message_type: str = "general"


@dataclass
class AgentObservation:
    """Observation data for a single agent within a team run.

    Attributes:
        agent_id: Unique agent identifier from the event stream.
        agent_type: Role classification -- "attacker", "defender", "verifier", etc.
        transcript: Parsed transcript for this agent's session.
        bskg_queries: BSKG queries extracted from this agent's transcript.
        messages_sent: SendMessage calls FROM this agent.
        messages_received: SendMessage calls TO this agent.
    """

    agent_id: str
    agent_type: str
    transcript: TranscriptParser | None = None
    bskg_queries: list[BSKGQuery] = field(default_factory=list)
    messages_sent: list[InboxMessage] = field(default_factory=list)
    messages_received: list[InboxMessage] = field(default_factory=list)


@dataclass
class EvidenceFlowEdge:
    """An edge in the evidence flow graph between agents.

    Attributes:
        from_agent: Sender agent_id.
        to_agent: Receiver agent_id.
        evidence_type: Classification of what was shared -- "finding", "query_result",
            "verdict", "question", "rebuttal".
        content_preview: First 200 chars of the message content.
        timestamp: ISO 8601 timestamp of the exchange.
        fidelity_score: Evidence fidelity metric (Plan 11, IMP-31). Measures how well
            structured evidence tuples (function_name, vulnerability_class, severity)
            are preserved across agent handoffs. Computed as
            |intersection| / max(|source_tuples|, 1). None if not yet computed.
    """

    from_agent: str
    to_agent: str
    evidence_type: str
    content_preview: str
    timestamp: str
    fidelity_score: float | None = None

    @staticmethod
    def extract_evidence_tuples(text: str) -> set[tuple[str, str, str]]:
        """Extract structured (function_name, vulnerability_class, severity) tuples from text.

        Looks for patterns like:
        - "function withdraw() ... reentrancy ... CRITICAL"
        - "transferFrom: access-control (HIGH)"
        - Explicit tuple-like: "(withdraw, reentrancy, critical)"

        Returns:
            Set of (function_name, vulnerability_class, severity) tuples, all lowercased.
        """
        tuples: set[tuple[str, str, str]] = set()

        # Pattern 1: explicit tuple format "(func, vuln_class, severity)"
        explicit = re.findall(
            r"\(\s*(\w+)\s*,\s*([\w-]+)\s*,\s*(critical|high|medium|low|info)\s*\)",
            text,
            re.IGNORECASE,
        )
        for func, vuln, sev in explicit:
            tuples.add((func.lower(), vuln.lower(), sev.lower()))

        # Pattern 2: "function_name: vuln_class (SEVERITY)" or "function_name ... vuln_class ... SEVERITY"
        structured = re.findall(
            r"(\w+)\s*[:]\s*([\w-]+)\s*\(\s*(critical|high|medium|low|info)\s*\)",
            text,
            re.IGNORECASE,
        )
        for func, vuln, sev in structured:
            tuples.add((func.lower(), vuln.lower(), sev.lower()))

        # Pattern 3: severity keyword near function name and vuln class
        severity_re = r"(critical|high|medium|low|info)"
        vuln_classes = [
            "reentrancy", "access-control", "overflow", "underflow",
            "front-running", "oracle-manipulation", "dos", "delegation",
            "signature", "initialization", "privilege-escalation",
            "unprotected", "unchecked", "missing-guard",
        ]
        for vuln_cls in vuln_classes:
            pattern = (
                r"(\w+)\s+.*?" + re.escape(vuln_cls) + r".*?" + severity_re
            )
            matches = re.findall(pattern, text, re.IGNORECASE)
            for func, sev in matches:
                if len(func) > 2 and func.lower() not in ("the", "and", "for", "has", "was", "are"):
                    tuples.add((func.lower(), vuln_cls.lower(), sev.lower()))

        return tuples

    @staticmethod
    def compute_fidelity(
        source_text: str, target_text: str
    ) -> float:
        """Compute evidence fidelity between source and target agent text.

        Args:
            source_text: Text from the source agent (e.g., attacker findings).
            target_text: Text from the target agent (e.g., verifier assessment).

        Returns:
            Fidelity score: |intersection| / max(|source_tuples|, 1).
            Returns 0.0 if no tuples extracted from source.
        """
        source_tuples = EvidenceFlowEdge.extract_evidence_tuples(source_text)
        target_tuples = EvidenceFlowEdge.extract_evidence_tuples(target_text)
        if not source_tuples:
            return 0.0
        intersection = source_tuples & target_tuples
        return len(intersection) / max(len(source_tuples), 1)


@dataclass
class DebateTurn:
    """A single turn in a multi-agent debate.

    Attributes:
        turn_number: 1-based turn index.
        agent_id: Agent who spoke.
        agent_type: Agent role (attacker/defender/verifier).
        content_preview: First 500 chars of the message.
        references_prior: Whether this turn references a prior turn's content.
        timestamp: ISO 8601 timestamp.
    """

    turn_number: int
    agent_id: str
    agent_type: str
    content_preview: str
    references_prior: bool
    timestamp: str


@dataclass
class TeamObservation:
    """Cross-agent observation for a team run.

    Links individual agent transcripts to the team event stream.

    Attributes:
        agents: Mapping from agent_id to AgentObservation.
        events: The team's event stream (spawns, messages, completions).
    """

    agents: dict[str, AgentObservation] = field(default_factory=dict)
    events: EventStream | None = None

    def get_agent_by_type(self, agent_type: str) -> AgentObservation | None:
        """Find the first agent with the given type (case-insensitive).

        Args:
            agent_type: Role to match (e.g., "attacker", "defender").

        Returns:
            The matching AgentObservation, or None if no agent of that type exists.
        """
        agent_type_lower = agent_type.lower()
        for obs in self.agents.values():
            if obs.agent_type.lower() == agent_type_lower:
                return obs
        return None

    def cross_agent_evidence_flow(self) -> list[EvidenceFlowEdge]:
        """Reconstruct the evidence flow graph from SendMessage exchanges.

        Analyzes all InboxMessage objects across agents to build a directed graph
        of evidence sharing. Each edge represents one message classified by
        evidence_type. Computes fidelity_score for edges where both source and
        target agent text are available (Plan 11, IMP-31).

        Returns:
            List of EvidenceFlowEdge in chronological order.
            Empty list if no inter-agent messages exist.
        """
        all_messages: list[tuple[str, InboxMessage]] = []
        for agent_id, obs in self.agents.items():
            for msg in obs.messages_sent:
                all_messages.append((agent_id, msg))

        # Sort by timestamp
        all_messages.sort(key=lambda x: x[1].timestamp)

        # Build agent text lookup for fidelity computation
        agent_full_text: dict[str, str] = {}
        for agent_id, obs in self.agents.items():
            texts = [m.content for m in obs.messages_sent]
            agent_full_text[agent_id] = " ".join(texts)

        edges: list[EvidenceFlowEdge] = []
        for sender_id, msg in all_messages:
            evidence_type = self._classify_evidence_type(msg.content)

            # Compute fidelity if both agents have text
            fidelity = None
            source_text = agent_full_text.get(sender_id, "")
            target_text = agent_full_text.get(msg.recipient, "")
            if source_text and target_text:
                fidelity = EvidenceFlowEdge.compute_fidelity(source_text, target_text)

            edges.append(EvidenceFlowEdge(
                from_agent=sender_id,
                to_agent=msg.recipient,
                evidence_type=evidence_type,
                content_preview=msg.content[:200],
                timestamp=msg.timestamp,
                fidelity_score=fidelity,
            ))

        return edges

    @staticmethod
    def _classify_evidence_type(content: str) -> str:
        """Classify message content into an evidence type."""
        content_lower = content.lower()
        if any(kw in content_lower for kw in ("finding", "vulnerability", "detected")):
            return "finding"
        if any(kw in content_lower for kw in ("verdict", "confirmed", "rejected")):
            return "verdict"
        if any(kw in content_lower for kw in ("query", "graph", "bskg", "node")):
            return "query_result"
        if any(kw in content_lower for kw in ("rebuttal", "disagree", "counter")):
            return "rebuttal"
        if "?" in content_lower:
            return "question"
        return "finding"

    def debate_turns(self) -> list[DebateTurn]:
        """Extract structured debate turns from inter-agent messages.

        Orders all messages chronologically and classifies each as a debate turn.
        Uses heuristics to detect back-references (substring matching on prior
        turn content).

        Returns:
            List of DebateTurn in chronological order.
            Empty list if no inter-agent debate occurred.
        """
        # Collect all sent messages with agent info
        all_messages: list[tuple[AgentObservation, InboxMessage]] = []
        for obs in self.agents.values():
            for msg in obs.messages_sent:
                all_messages.append((obs, msg))

        # Sort by timestamp
        all_messages.sort(key=lambda x: x[1].timestamp)

        turns: list[DebateTurn] = []
        prior_previews: list[str] = []

        for turn_num, (obs, msg) in enumerate(all_messages, start=1):
            preview = msg.content[:500]

            # Check if this turn references prior content
            references_prior = False
            for prior in prior_previews:
                # Check for 20+ char substring match
                check_len = min(len(prior), 50)
                if check_len >= 20 and prior[:check_len] in msg.content:
                    references_prior = True
                    break

            turns.append(DebateTurn(
                turn_number=turn_num,
                agent_id=obs.agent_id,
                agent_type=obs.agent_type,
                content_preview=preview,
                references_prior=references_prior,
                timestamp=msg.timestamp,
            ))
            prior_previews.append(preview)

        return turns



@dataclass
class CollectedOutput:
    """Aggregated output from a single scenario run.

    Attributes:
        scenario_name: Name of the scenario that was executed.
        run_id: Unique identifier for this run (UUID or timestamp-based).
        transcript: Parsed transcript of the primary session.
        team_observation: Cross-agent observation, or None for single-agent runs.
        structured_output: Parsed JSON output from the agent, or None.
        tool_sequence: Ordered list of tool names invoked during the run.
        bskg_queries: All BSKG queries from the primary transcript.
        duration_ms: Total execution time in milliseconds.
        cost_usd: Estimated API cost in USD.
        failure_notes: Free-text failure classification. Empty string means no failure.
        response_text: Raw agent response text for grading against the full response
            (not just the summary). Empty string if not captured.
    """

    scenario_name: str
    run_id: str
    transcript: TranscriptParser | None = None
    team_observation: TeamObservation | None = None
    structured_output: dict[str, Any] | None = None
    tool_sequence: list[str] = field(default_factory=list)
    bskg_queries: list[BSKGQuery] = field(default_factory=list)
    duration_ms: float = 0.0
    cost_usd: float = 0.0
    failure_notes: str = ""
    response_text: str = ""


@dataclass
class EvaluationGuidance:
    """Per-scenario guidance for the 3.1c evaluation pipeline.

    Stored in scenario YAML under the ``evaluation_guidance:`` key.
    3.1b parses and stores this; 3.1c reads it to configure evaluation.

    Note: ``run_gvs`` and ``run_reasoning`` flags are owned by 3.1c's
    ``EvaluationConfig`` (Pydantic model in ``evaluation/models.py``),
    not by this 3.1b dataclass.

    Attributes:
        reasoning_questions: Questions for the LLM reasoning evaluator to answer
            about this scenario's run.
        hooks_if_failed: Hook scripts to enable on re-run if evaluation fails.
    """

    reasoning_questions: list[str] = field(default_factory=list)
    hooks_if_failed: list[str] = field(default_factory=list)

    def to_pydantic_dict(self) -> dict[str, Any]:
        """Return a dict suitable for constructing 3.1c's EvaluationConfig.

        3.1c-08 (Evaluation Runner) owns the full conversion via
        ``EvaluationConfig.from_guidance(guidance)``. This method provides
        the raw data bridge.

        Returns:
            Dict with ``reasoning_questions`` and ``hooks_if_failed`` keys.
        """
        return {
            "reasoning_questions": list(self.reasoning_questions),
            "hooks_if_failed": list(self.hooks_if_failed),
        }


class OutputCollector:
    """Collect and aggregate run results into CollectedOutput.

    Bridges the gap between raw run artifacts and the structured data
    the 3.1c evaluation pipeline needs.

    Example:
        >>> collector = OutputCollector()
        >>> output = collector.collect(
        ...     scenario_name="reentrancy-basic",
        ...     run_id="run-001",
        ...     transcript=parser,
        ... )
        >>> print(output.bskg_queries)
    """

    def collect(
        self,
        scenario_name: str,
        run_id: str,
        transcript: TranscriptParser | None = None,
        team_observation: TeamObservation | None = None,
        structured_output: dict[str, Any] | None = None,
        duration_ms: float = 0.0,
        cost_usd: float = 0.0,
        failure_notes: str = "",
        response_text: str = "",
    ) -> CollectedOutput:
        """Aggregate run artifacts into a CollectedOutput.

        Args:
            scenario_name: Name of the executed scenario.
            run_id: Unique run identifier.
            transcript: Parsed primary transcript.
            team_observation: Cross-agent observation (None for single-agent).
            structured_output: Parsed JSON output from the agent.
            duration_ms: Total execution time in milliseconds.
            cost_usd: Estimated API cost in USD.
            failure_notes: Free-text failure classification.
            response_text: Raw agent response text for grading.

        Returns:
            CollectedOutput with all fields populated from available sources.
        """
        tool_sequence: list[str] = []
        bskg_queries: list[BSKGQuery] = []

        if transcript is not None:
            tool_sequence = transcript.get_tool_sequence()
            bskg_queries = transcript.get_bskg_queries()

        return CollectedOutput(
            scenario_name=scenario_name,
            run_id=run_id,
            transcript=transcript,
            team_observation=team_observation,
            structured_output=structured_output,
            tool_sequence=tool_sequence,
            bskg_queries=bskg_queries,
            duration_ms=duration_ms,
            cost_usd=cost_usd,
            failure_notes=failure_notes,
            response_text=response_text,
        )

    def summary(self, output: CollectedOutput) -> str:
        """Produce human-readable summary of collected output.

        Args:
            output: The CollectedOutput to summarize.

        Returns:
            Multi-line string with scenario name, run ID, tool count,
            BSKG query count, citation rate, duration, cost, failure notes.
        """
        citation_rate = None
        if output.transcript is not None:
            citation_rate = output.transcript.graph_citation_rate()

        citation_str = f"{citation_rate:.1%}" if citation_rate is not None else "N/A"
        lines = [
            f"Scenario: {output.scenario_name}",
            f"Run ID: {output.run_id}",
            f"Tools used: {len(output.tool_sequence)}",
            f"BSKG queries: {len(output.bskg_queries)}",
            f"Citation rate: {citation_str}",
            f"Duration: {output.duration_ms:.0f}ms",
            f"Cost: ${output.cost_usd:.4f}",
        ]
        if output.failure_notes:
            lines.append(f"Failure: {output.failure_notes}")
        if output.team_observation is not None:
            lines.append(f"Team agents: {len(output.team_observation.agents)}")

        return "\n".join(lines)


# Backward-compatible alias. InboxMessage is the canonical type for
# inter-agent messages. CapturedMessage was used in early 3.1b API
# contract docs; prefer InboxMessage in new code.
CapturedMessage = InboxMessage
