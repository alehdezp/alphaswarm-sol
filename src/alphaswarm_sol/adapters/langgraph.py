"""LangGraph Swarm Adapter.

Executes AlphaSwarm VRS agents as LangGraph state graph nodes with
bead-aware checkpointing for deterministic replay and recovery.

Key Features:
- VRS agents as state graph nodes (attacker, defender, verifier)
- Checkpointing maps to bead state for replay capability
- Evidence preservation across all graph transitions
- Trace propagation for observability
- Conditional routing based on investigation flow

Architecture:
    VrsStateGraph: State graph with VRS agent nodes
    LangGraphAdapter: OrchestratorAdapter implementation
    BeadCheckpointer: Bead-aware persistence layer

Usage:
    from alphaswarm_sol.adapters.langgraph import LangGraphAdapter, LangGraphConfig

    # Create adapter with persistence
    config = LangGraphConfig(
        name="langgraph",
        persistence_path=".langgraph_checkpoints",
        enable_replay=True,
    )
    adapter = LangGraphAdapter(config)

    # Execute full workflow
    result_bead = await adapter.execute_workflow(bead, {})

    # Replay from checkpoint
    state = await adapter.replay_from_checkpoint(checkpoint_id)

Phase: 07.1.4-03 LangGraph Adapter with Persistence
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentResponse
from alphaswarm_sol.agents.runtime.factory import create_runtime, RuntimeType
from alphaswarm_sol.beads.schema import VulnerabilityBead
from alphaswarm_sol.beads.types import BeadStatus

from .base import (
    AdapterConfig,
    HandoffContext,
    HandoffResult,
    OrchestratorAdapter,
    TraceContext,
)
from .capability import ADAPTER_CAPABILITIES, AdapterCapability

# Lazy import for langgraph to avoid hard dependency
try:
    from langgraph.graph import StateGraph, END
    from typing_extensions import TypedDict

    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    StateGraph = None  # type: ignore
    END = "END"  # type: ignore
    TypedDict = dict  # type: ignore


@dataclass
class LangGraphConfig(AdapterConfig):
    """Configuration for LangGraph adapter.

    Attributes:
        persistence_path: Path for checkpoint storage (default ".langgraph_checkpoints")
        enable_replay: Enable checkpoint replay (default True)
        max_concurrent_nodes: Maximum concurrent node execution (default 4)
        state_schema: Optional custom state schema (default VrsState)

    Example:
        config = LangGraphConfig(
            name="langgraph",
            capabilities=ADAPTER_CAPABILITIES["langgraph"].capabilities,
            persistence_path=".langgraph_checkpoints",
            enable_replay=True,
            max_concurrent_nodes=4,
        )
    """

    persistence_path: str = ".langgraph_checkpoints"
    enable_replay: bool = True
    max_concurrent_nodes: int = 4
    state_schema: Optional[Any] = None


class VrsState(TypedDict):
    """State schema for VRS investigation graph.

    Attributes:
        bead: Serialized VulnerabilityBead
        messages: Conversation history across agents
        current_agent: Current agent role (attacker, defender, verifier)
        evidence: Accumulated evidence from all agents
        trace_context: Trace propagation data
        checkpoint_id: Checkpoint ID for replay
        verdict_reached: Whether a verdict has been reached
        next_agent: Next agent to execute (for routing)
    """

    bead: Dict[str, Any]
    messages: List[Dict[str, Any]]
    current_agent: str
    evidence: Dict[str, Any]
    trace_context: Dict[str, Any]
    checkpoint_id: str
    verdict_reached: bool
    next_agent: str


class VrsStateGraph:
    """State graph for VRS investigation workflow.

    Creates a LangGraph StateGraph with nodes for each VRS agent role
    and conditional edges based on investigation flow.

    Investigation Flow:
        attacker -> defender -> verifier -> END
        (with conditional routing based on evidence)

    Example:
        graph = VrsStateGraph(adapter)
        compiled = graph.compile()
        result = await compiled.ainvoke(initial_state)
    """

    def __init__(self, adapter: "LangGraphAdapter"):
        """Initialize state graph.

        Args:
            adapter: LangGraphAdapter instance for agent execution
        """
        if not HAS_LANGGRAPH:
            raise ImportError(
                "langgraph is not installed. Install with: pip install langgraph"
            )

        self.adapter = adapter
        self.graph = StateGraph(VrsState)

        # Add nodes for each VRS agent
        self.graph.add_node("attacker", self._create_agent_node("vrs-attacker"))
        self.graph.add_node("defender", self._create_agent_node("vrs-defender"))
        self.graph.add_node("verifier", self._create_agent_node("vrs-verifier"))

        # Set entry point
        self.graph.set_entry_point("attacker")

        # Add conditional edges
        self.graph.add_conditional_edges(
            "attacker",
            self._route_next_agent,
            {"defender": "defender", "END": END},
        )
        self.graph.add_conditional_edges(
            "defender",
            self._route_next_agent,
            {"verifier": "verifier", "END": END},
        )
        self.graph.add_conditional_edges(
            "verifier",
            self._route_next_agent,
            {"END": END},
        )

    def _create_agent_node(self, role: str) -> Callable:
        """Create agent node function for graph.

        Args:
            role: Agent role (e.g., "vrs-attacker", "vrs-defender")

        Returns:
            Async function that executes agent and updates state
        """

        async def agent_node(state: VrsState) -> VrsState:
            """Execute agent and update state."""
            # Create agent config
            agent_config = AgentConfig(
                role=role,
                model="claude-sonnet-4",  # Default model
                prompt_template="",  # Will be populated from bead
                tools=[],  # Tools from catalog
                metadata={"bead_id": state["bead"]["id"]},
            )

            # Execute agent
            response = await self.adapter.execute_agent(
                agent_config, state["messages"]
            )

            # Update state
            new_messages = state["messages"] + [
                {"role": "assistant", "content": response.content, "agent": role}
            ]

            # Preserve evidence
            new_evidence = {**state["evidence"], f"{role}_evidence": response.metadata}

            # Update trace
            trace_context = state["trace_context"].copy()
            trace_context["last_agent"] = role

            return {
                **state,
                "messages": new_messages,
                "current_agent": role,
                "evidence": new_evidence,
                "trace_context": trace_context,
            }

        return agent_node

    def _route_next_agent(self, state: VrsState) -> str:
        """Determine next agent based on current state.

        Args:
            state: Current graph state

        Returns:
            Next node name or "END"
        """
        current = state["current_agent"]

        # Check if verdict reached
        if state.get("verdict_reached", False):
            return "END"

        # Standard flow: attacker -> defender -> verifier -> END
        routing = {
            "vrs-attacker": "defender",
            "vrs-defender": "verifier",
            "vrs-verifier": "END",
        }

        return routing.get(current, "END")

    def compile(self) -> Any:
        """Compile graph with checkpointer.

        Returns:
            Compiled graph ready for execution
        """
        # Compile with checkpointer if enabled
        if self.adapter.config.enable_replay and self.adapter.checkpointer:
            return self.graph.compile(checkpointer=self.adapter.checkpointer)
        return self.graph.compile()


class LangGraphAdapter(OrchestratorAdapter):
    """LangGraph orchestrator adapter with bead-aware persistence.

    Executes VRS agents as LangGraph state graph nodes with checkpointing
    that maps to bead state for deterministic replay.

    Capabilities:
    - TOOL_EXECUTION: Execute tools within graph nodes
    - MEMORY_PERSISTENT: Checkpoint state for replay
    - TRACE_PROPAGATION: Propagate trace context through graph
    - HANDOFF_ASYNC: Async handoffs between agents
    - BEAD_REPLAY: Replay bead investigation from checkpoint

    Example:
        config = LangGraphConfig(
            name="langgraph",
            capabilities=ADAPTER_CAPABILITIES["langgraph"].capabilities,
        )
        adapter = LangGraphAdapter(config)

        # Execute workflow
        result = await adapter.execute_workflow(bead, {})

        # Replay from checkpoint
        state = await adapter.replay_from_checkpoint(checkpoint_id)
    """

    def __init__(self, config: LangGraphConfig):
        """Initialize LangGraph adapter.

        Args:
            config: LangGraph adapter configuration
        """
        if not HAS_LANGGRAPH:
            raise ImportError(
                "langgraph is not installed. Install with: pip install langgraph"
            )

        super().__init__(config)
        self.config: LangGraphConfig = config

        # Create runtime for agent execution
        # Use OpenCode as default cost-optimized runtime
        self._runtime = create_runtime(sdk=RuntimeType.OPENCODE)

        # Initialize checkpointer
        from .checkpointer import BeadCheckpointer

        self.checkpointer = (
            BeadCheckpointer(Path(config.persistence_path))
            if config.enable_replay
            else None
        )

        # Create state graph
        self.state_graph = VrsStateGraph(self)
        self.compiled_graph = self.state_graph.compile()

    async def execute_agent(
        self, config: AgentConfig, messages: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Execute single agent via runtime factory.

        Args:
            config: Agent configuration
            messages: Conversation messages

        Returns:
            AgentResponse with content and metadata
        """
        # Execute via runtime factory (OpenCode default for cost optimization)
        response = await self._runtime.execute(config, messages)
        response.metadata["adapter"] = "langgraph"
        return response

    async def handoff(self, ctx: HandoffContext) -> HandoffResult:
        """Hand off execution from one agent to another.

        Updates graph state with handoff context and triggers next node.
        Creates checkpoint after handoff for replay capability.

        Args:
            ctx: Handoff context with source/target agents and evidence

        Returns:
            HandoffResult with checkpoint ID and target response
        """
        # Validate handoff depth
        if ctx.handoff_depth >= self.config.max_handoff_depth:
            return HandoffResult(
                success=False,
                errors=[
                    f"Max handoff depth ({self.config.max_handoff_depth}) exceeded"
                ],
            )

        try:
            # Update state for handoff
            state_update = {
                "current_agent": ctx.source_agent,
                "next_agent": ctx.target_agent,
                "evidence": ctx.evidence_snapshot,
                "trace_context": {
                    "trace_id": ctx.trace_id,
                    "parent_span_id": ctx.parent_span_id,
                    "handoff_depth": ctx.handoff_depth,
                },
            }

            # Create checkpoint if enabled
            checkpoint_id = None
            if self.checkpointer:
                # Convert to VrsState format
                vrs_state: VrsState = {
                    "bead": {},  # Will be populated from context
                    "messages": [],
                    "current_agent": ctx.source_agent,
                    "evidence": ctx.evidence_snapshot,
                    "trace_context": state_update["trace_context"],
                    "checkpoint_id": str(uuid.uuid4()),
                    "verdict_reached": False,
                    "next_agent": ctx.target_agent,
                }
                checkpoint_id = self.checkpointer.save(vrs_state, ctx.source_agent)

            # Execute target agent via runtime
            target_config = AgentConfig(
                role=ctx.target_agent,
                model="claude-sonnet-4",
                prompt_template="",
                tools=[],
                metadata={"handoff_context": ctx.to_dict()},
            )
            target_response = await self._runtime.execute(target_config, [])

            return HandoffResult(
                success=True,
                target_response=target_response,
                evidence_preserved=True,
                trace_continued=True,
                metadata={"checkpoint_id": checkpoint_id},
            )

        except Exception as e:
            return HandoffResult(
                success=False, errors=[f"Handoff failed: {str(e)}"]
            )

    async def spawn_with_trace(
        self, config: AgentConfig, task: str, trace: TraceContext
    ) -> AgentResponse:
        """Spawn agent with trace context propagation.

        Args:
            config: Agent configuration
            task: Task description
            trace: Trace context to propagate

        Returns:
            AgentResponse with trace attributes
        """
        # Add trace context to config metadata
        config.metadata["trace_context"] = trace.to_dict()
        config.metadata["task"] = task

        # Execute agent via runtime
        response = await self._runtime.execute(
            config, [{"role": "user", "content": task}]
        )

        # Attach trace attributes to response
        response.metadata["trace_id"] = trace.trace_id
        response.metadata["span_id"] = trace.span_id
        response.metadata["adapter"] = "langgraph"

        return response

    async def execute_workflow(
        self, bead: VulnerabilityBead, config: Dict[str, Any]
    ) -> VulnerabilityBead:
        """Execute full VRS workflow as state graph.

        Args:
            bead: VulnerabilityBead to investigate
            config: Workflow configuration

        Returns:
            Updated VulnerabilityBead with verdict
        """
        # Create initial state
        initial_state: VrsState = {
            "bead": bead.to_dict(),
            "messages": [],
            "current_agent": "",
            "evidence": {},
            "trace_context": {
                "trace_id": str(uuid.uuid4()),
                "operation": "vrs.workflow",
            },
            "checkpoint_id": "",
            "verdict_reached": False,
            "next_agent": "attacker",
        }

        # Execute graph
        final_state = await self.compiled_graph.ainvoke(initial_state)

        # Update bead with results
        bead.work_state = {
            "final_state": final_state,
            "messages": final_state["messages"],
            "evidence": final_state["evidence"],
        }
        bead.status = BeadStatus.VERIFIED

        return bead

    async def replay_from_checkpoint(self, checkpoint_id: str) -> VrsState:
        """Replay graph execution from checkpoint.

        Args:
            checkpoint_id: Checkpoint ID to replay from

        Returns:
            Restored VrsState

        Raises:
            ValueError: If checkpoint not found or invalid
        """
        if not self.checkpointer:
            raise ValueError("Checkpointer not enabled")

        checkpoint_state = self.checkpointer.load(checkpoint_id)

        # Resume graph execution from checkpoint
        resumed_state = await self.compiled_graph.ainvoke(
            checkpoint_state.graph_state
        )

        return resumed_state

    def get_capabilities(self) -> Set[AdapterCapability]:
        """Get adapter capabilities.

        Returns:
            Set of supported capabilities
        """
        return ADAPTER_CAPABILITIES["langgraph"].capabilities

    def export_trace(self, trace: TraceContext) -> Dict[str, Any]:
        """Export trace context to OpenTelemetry format.

        Args:
            trace: Trace context to export

        Returns:
            Dictionary in OpenTelemetry format
        """
        return {
            "traceparent": f"00-{trace.trace_id}-{trace.span_id}-01",
            "tracestate": "",
            "attributes": trace.attributes,
            "events": trace.events,
        }

    def import_trace(self, data: Dict[str, Any]) -> TraceContext:
        """Import trace context from OpenTelemetry format.

        Args:
            data: Dictionary in OpenTelemetry format

        Returns:
            TraceContext instance
        """
        # Parse traceparent header (W3C Trace Context format)
        traceparent = data.get("traceparent", "")
        parts = traceparent.split("-")

        if len(parts) >= 4:
            trace_id = parts[1]
            span_id = parts[2]
        else:
            trace_id = str(uuid.uuid4())
            span_id = str(uuid.uuid4())[:16]

        return TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            operation="imported",
            attributes=data.get("attributes", {}),
            events=data.get("events", []),
        )

    def preserve_evidence(
        self, bead: VulnerabilityBead, ctx: HandoffContext
    ) -> VulnerabilityBead:
        """Preserve evidence contracts during handoff.

        Overrides base implementation to add graph state snapshot.

        Args:
            bead: VulnerabilityBead with evidence
            ctx: Handoff context

        Returns:
            Unmodified bead with snapshot in context
        """
        # Call parent implementation
        bead = super().preserve_evidence(bead, ctx)

        # Add graph state snapshot to bead work_state
        if not bead.work_state:
            bead.work_state = {}

        bead.work_state["handoff_snapshot"] = {
            "source_agent": ctx.source_agent,
            "target_agent": ctx.target_agent,
            "timestamp": ctx.timestamp,
            "evidence": ctx.evidence_snapshot,
        }

        return bead
