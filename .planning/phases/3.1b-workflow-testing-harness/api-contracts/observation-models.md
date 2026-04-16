# API Contract: Observation Models

**Location:** `tests/workflow_harness/lib/output_collector.py` (new file)
**3.1b Plans:** 3.1b-02 (models), 3.1b-04 (TeamObservation integration), 3.1b-05 (EvaluationGuidance in DSL)
**3.1c Consumers:** 3.1c-01 (Assessment Data Structures), 3.1c-03 (Observation Parser), 3.1c-07 (Reasoning Evaluator), 3.1c-08 (Evaluation Runner), 3.1c-10 (Agent Tests), 3.1c-11 (Orchestrator Tests)

## Parse/Execute Boundary

- **3.1b parses:** Collects agent transcripts, team events, and run artifacts into structured dataclasses. Stores `EvaluationGuidance` from scenario YAML.
- **3.1c executes:** Feeds collected data to evaluation pipeline (scorer, evaluator, runner). Interprets `EvaluationGuidance` to select hooks and evaluation dimensions.

---

## AgentObservation Dataclass

```python
from dataclasses import dataclass, field
from typing import Any

from tests.workflow_harness.lib.transcript_parser import TranscriptParser, BSKGQuery

@dataclass
class InboxMessage:
    """A SendMessage exchange between agents.

    Attributes:
        sender: Sender agent identifier.
        recipient: Recipient agent identifier or "broadcast".
        content: Full message body text.
        timestamp: ISO 8601 timestamp.
        message_type: Classification — "task_assignment", "finding", "question",
            "response", "shutdown_request", or "general".

    Note: Field was renamed from ``agent_id`` to ``sender`` during 3.1b-07
    implementation to better reflect semantics. Implementation is canonical.
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
        agent_type: Role classification — "attacker", "defender", "verifier", etc.
        transcript: Parsed transcript for this agent's session. None if agent died
            before producing output or if transcript file was not found.
            Callers MUST None-check before accessing transcript methods.
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
```

**Failure modes:**
- `transcript` may have zero records if agent died before producing output. `bskg_queries` will be empty.
- `messages_sent` / `messages_received` may be empty for agents that don't participate in inter-agent messaging.
- `agent_type` is derived from the event stream's `agent_type` or `subagent_type` field (case-insensitive matching).

---

## TeamObservation Dataclass

```python
from tests.workflow_harness.lib.controller_events import EventStream

@dataclass
class EvidenceFlowEdge:
    """An edge in the evidence flow graph between agents.

    Attributes:
        from_agent: Sender agent_id.
        to_agent: Receiver agent_id.
        evidence_type: Classification of what was shared — "finding", "query_result",
            "verdict", "question", "rebuttal".
        content_preview: First 200 chars of the message content.
        timestamp: ISO 8601 timestamp of the exchange.
    """

    from_agent: str
    to_agent: str
    evidence_type: str
    content_preview: str
    timestamp: str

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
        ...

    def cross_agent_evidence_flow(self) -> list[EvidenceFlowEdge]:
        """Reconstruct the evidence flow graph from SendMessage exchanges.

        Analyzes all InboxMessage objects across agents to build a directed graph
        of evidence sharing. Each edge represents one message classified by
        evidence_type.

        Returns:
            List of EvidenceFlowEdge in chronological order.
            Empty list if no inter-agent messages exist.
        """
        ...

    def debate_turns(self) -> list[DebateTurn]:
        """Extract structured debate turns from inter-agent messages.

        Orders all messages chronologically and classifies each as a debate turn.
        Uses heuristics to detect back-references (substring matching on prior
        turn content).

        Returns:
            List of DebateTurn in chronological order.
            Empty list if no inter-agent debate occurred.
        """
        ...
```

**Failure modes:**
- `get_agent_by_type()` returns `None` when no agent of that type exists. Callers must handle this (e.g., in tests that expect 3 agents but only 2 spawned).
- `cross_agent_evidence_flow()` returns empty list for single-agent runs. This is not an error.
- `debate_turns()` returns empty list when agents don't exchange messages. This is expected for non-debate workflows.
- `events` is `None` when constructed without an event stream (e.g., from transcript-only data).

---

## OutputCollector and CollectedOutput

```python
@dataclass
class CollectedOutput:
    """Aggregated output from a single scenario run.

    Attributes:
        scenario_name: Name of the scenario that was executed.
        run_id: Unique identifier for this run (UUID or timestamp-based).
        transcript: Parsed transcript of the primary session.
        team_observation: Cross-agent observation, or None for single-agent runs.
        structured_output: Parsed JSON output from the agent, or None if
            JSON parsing failed or no schema was specified.
        tool_sequence: Ordered list of tool names invoked during the run.
        bskg_queries: All BSKG queries from the primary transcript.
        duration_ms: Total execution time in milliseconds.
        cost_usd: Estimated API cost in USD.
        failure_notes: Free-text failure classification. Empty string means no failure.
            Filled by the evaluator, not the collector.
        response_text: Raw agent response text for grading against the full response
            (not just the summary). Empty string if not captured.
    """

    scenario_name: str
    run_id: str
    transcript: TranscriptParser
    team_observation: TeamObservation | None = None
    structured_output: dict[str, Any] | None = None
    tool_sequence: list[str] = field(default_factory=list)
    bskg_queries: list[BSKGQuery] = field(default_factory=list)
    duration_ms: float = 0.0
    cost_usd: float = 0.0
    failure_notes: str = ""
    response_text: str = ""


class OutputCollector:
    """Collect and aggregate run results into CollectedOutput.

    Bridges the gap between raw run artifacts and the structured data
    3.1c evaluation needs.

    Example:
        >>> collector = OutputCollector()
        >>> output = collector.collect(
        ...     scenario_name="reentrancy-basic",
        ...     run_id="run-001",
        ...     transcript=parser,
        ...     team_observation=team_obs,
        ...     duration_ms=12500.0,
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
    ) -> CollectedOutput:
        """Aggregate run artifacts into a CollectedOutput.

        Args:
            scenario_name: Name of the executed scenario.
            run_id: Unique run identifier.
            transcript: Parsed primary transcript. None if not available.
            team_observation: Cross-agent observation (None for single-agent).
            structured_output: Parsed JSON output from the agent.
            duration_ms: Total execution time in milliseconds.
            cost_usd: Estimated API cost in USD.
            failure_notes: Free-text failure classification.

        Returns:
            CollectedOutput with all fields populated from available sources.

        Note: ``response_text`` is NOT set by collect(). Callers must set it
        on the returned CollectedOutput if they need it for grading:
        ``output.response_text = raw_text``.
        """
        ...
```

**Failure modes:**
- `transcript` is `None` when collecting from metadata-only data. `tool_sequence` and `bskg_queries` will be empty lists.
- `team_observation` is `None` for all single-agent runs. Consumers must not assume it exists.
- `response_text` is always empty string from `collect()`. Set it manually if needed.

---

## EvaluationGuidance Dataclass

```python
@dataclass
class EvaluationGuidance:
    """Per-scenario guidance for the 3.1c evaluation pipeline.

    Stored in scenario YAML under the `evaluation_guidance:` key.
    3.1b parses and stores this; 3.1c reads it to configure evaluation.

    Note: `run_gvs` and `run_reasoning` flags are owned by 3.1c's
    `EvaluationConfig` (Pydantic model), not by this 3.1b dataclass.

    Attributes:
        reasoning_questions: Questions for the LLM reasoning evaluator to answer
            about this scenario's run. Example: "Did the agent check for reentrancy
            before concluding the contract is safe?"
        hooks_if_failed: Hook scripts to enable on re-run if evaluation fails.
            Paths relative to the scenario's workspace root.
    """

    reasoning_questions: list[str] = field(default_factory=list)
    hooks_if_failed: list[str] = field(default_factory=list)

    def to_pydantic_dict(self) -> dict[str, Any]:
        """Return a dict suitable for constructing 3.1c's EvaluationConfig.

        3.1c-08 (Evaluation Runner) owns the full conversion via
        `EvaluationConfig.from_guidance(guidance)`. This method provides
        the raw data bridge.
        """
        ...
```

**3.1c consumers:**
- 3.1c-06: Uses `reasoning_questions` to configure evaluation contract dimensions.
- 3.1c-07: Reasoning evaluator receives `reasoning_questions` as additional prompting.
- 3.1c-08: Evaluation runner uses `to_pydantic_dict()` to construct `EvaluationConfig` which owns `run_gvs` and `run_reasoning` flags.

**Failure modes:**
- All fields have defaults. A scenario with no `evaluation_guidance:` block gets default behavior (run GVS + reasoning, no specific questions, no failure hooks).
- Empty `reasoning_questions` list means the evaluator uses only the default template, with no scenario-specific focus.

---

## Example Usage

```python
from tests.workflow_harness.lib.output_collector import (
    AgentObservation, TeamObservation, OutputCollector,
    CollectedOutput, EvaluationGuidance, InboxMessage,
)
from tests.workflow_harness.lib.transcript_parser import TranscriptParser
from tests.workflow_harness.lib.controller_events import EventStream
from pathlib import Path

# Single-agent run
parser = TranscriptParser(Path("session.jsonl"))
collector = OutputCollector()
output = collector.collect(
    scenario_name="health-check-basic",
    run_id="run-001",
    transcript=parser,
)
assert output.team_observation is None

# Team run
attacker_obs = AgentObservation(
    agent_id="agent-1",
    agent_type="attacker",
    transcript=TranscriptParser(Path("agent-1.jsonl")),
)
team_obs = TeamObservation(
    agents={"agent-1": attacker_obs},
    events=EventStream([{"type": "agent:spawned", "agent_type": "attacker"}]),
)
output = collector.collect(
    scenario_name="audit-basic",
    run_id="run-002",
    transcript=parser,
    team_observation=team_obs,
)
attacker = team_obs.get_agent_by_type("attacker")
assert attacker is not None

# EvaluationGuidance from scenario YAML
guidance = EvaluationGuidance(
    reasoning_questions=["Did the agent query the graph before concluding?"],
)
# Convert to dict for 3.1c's EvaluationConfig
config_dict = guidance.to_pydantic_dict()
```
