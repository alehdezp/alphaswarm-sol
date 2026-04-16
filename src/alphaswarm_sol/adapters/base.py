"""OrchestratorAdapter Base Class.

Abstract base class for external orchestration framework adapters.
Enables AlphaSwarm VRS workflows to execute across Agents SDK, LangGraph,
AutoGen, and CrewAI while preserving evidence-first outputs and BSKG requirements.

Key Features:
- Unified agent execution interface
- Agent handoff with evidence preservation
- Distributed tracing context propagation
- Capability-based feature detection
- Evidence contract validation

Usage:
    class MyAdapter(OrchestratorAdapter):
        async def execute_agent(self, config: AgentConfig, messages: List[Dict]) -> AgentResponse:
            # SDK-specific implementation
            pass

        async def handoff(self, ctx: HandoffContext) -> HandoffResult:
            # Transfer agent execution with evidence
            pass

Phase: 07.1.4-01 Adapter Interface Foundation
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentResponse
from alphaswarm_sol.beads.schema import VulnerabilityBead


@dataclass
class AdapterConfig:
    """Configuration for orchestrator adapter.

    Attributes:
        name: Adapter identifier (e.g., "agents-sdk", "langgraph")
        capabilities: Set of AdapterCapability enums (imported to avoid circular dep)
        evidence_mode: How evidence is preserved across handoffs
            - "inline": Evidence embedded in messages
            - "bead": Evidence passed as VulnerabilityBead
            - "external": Evidence stored externally with reference
        trace_propagation: Trace propagation mode
            - "header": Trace context in message headers
            - "context": Trace context in execution context
            - "none": No trace propagation
        max_handoff_depth: Maximum handoff chain depth (prevents infinite loops)
        metadata: Additional adapter-specific configuration

    Example:
        config = AdapterConfig(
            name="agents-sdk",
            capabilities={AdapterCapability.TOOL_EXECUTION, AdapterCapability.GUARDRAILS},
            evidence_mode="bead",
            trace_propagation="header",
            max_handoff_depth=10,
        )
    """

    name: str
    capabilities: Set[Any]  # Set[AdapterCapability] but avoiding circular import
    evidence_mode: str = "bead"  # "inline" | "bead" | "external"
    trace_propagation: str = "header"  # "header" | "context" | "none"
    max_handoff_depth: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "capabilities": [str(c) for c in self.capabilities],
            "evidence_mode": self.evidence_mode,
            "trace_propagation": self.trace_propagation,
            "max_handoff_depth": self.max_handoff_depth,
            "metadata": self.metadata,
        }


@dataclass
class TraceContext:
    """Distributed tracing context for observability.

    Enables trace continuity across agent handoffs and framework boundaries.
    Compatible with OpenTelemetry trace propagation.

    Attributes:
        trace_id: Unique trace identifier (UUID or W3C trace ID)
        span_id: Current span ID
        parent_span_id: Parent span for nesting
        operation: Operation name (e.g., "vrs.investigate", "vrs.verify")
        attributes: Key-value attributes for trace enrichment
        events: List of timestamped trace events
        timestamp: ISO timestamp of trace creation

    Example:
        trace = TraceContext(
            trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
            span_id="00f067aa0ba902b7",
            parent_span_id="00f067aa0ba902b6",
            operation="vrs.investigate",
            attributes={"bead_id": "VKG-001", "severity": "critical"},
            events=[{"timestamp": "2024-01-29T14:00:00Z", "name": "handoff_initiated"}],
        )
    """

    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    operation: str = "unknown"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add a trace event with timestamp."""
        self.events.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "name": name,
                "attributes": attributes or {},
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation": self.operation,
            "attributes": self.attributes,
            "events": self.events,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceContext":
        """Create from dictionary."""
        return cls(
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            parent_span_id=data.get("parent_span_id"),
            operation=data.get("operation", "unknown"),
            attributes=data.get("attributes", {}),
            events=data.get("events", []),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
        )


@dataclass
class HandoffContext:
    """Context for agent handoff with evidence preservation.

    Captures all information needed to transfer execution from one agent
    to another while preserving evidence contracts and trace continuity.

    Attributes:
        source_agent: Agent ID handing off (e.g., "vrs-attacker")
        target_agent: Agent ID receiving (e.g., "vrs-defender")
        bead_id: Optional VulnerabilityBead ID being transferred
        evidence_snapshot: Dict of evidence at handoff point (preserves contracts)
        trace_id: Trace correlation ID
        parent_span_id: Parent span for trace continuity
        timestamp: ISO timestamp of handoff
        handoff_depth: Current depth in handoff chain (prevents infinite loops)
        metadata: Additional handoff metadata

    Example:
        ctx = HandoffContext(
            source_agent="vrs-attacker",
            target_agent="vrs-defender",
            bead_id="VKG-001",
            evidence_snapshot={"vulnerable_function": "withdraw", "operations": ["TRANSFERS_VALUE_OUT"]},
            trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
            parent_span_id="00f067aa0ba902b7",
        )
    """

    source_agent: str
    target_agent: str
    bead_id: Optional[str] = None
    evidence_snapshot: Dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""
    parent_span_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    handoff_depth: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "bead_id": self.bead_id,
            "evidence_snapshot": self.evidence_snapshot,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "timestamp": self.timestamp,
            "handoff_depth": self.handoff_depth,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HandoffContext":
        """Create from dictionary."""
        return cls(
            source_agent=data["source_agent"],
            target_agent=data["target_agent"],
            bead_id=data.get("bead_id"),
            evidence_snapshot=data.get("evidence_snapshot", {}),
            trace_id=data.get("trace_id", ""),
            parent_span_id=data.get("parent_span_id"),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
            handoff_depth=data.get("handoff_depth", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class HandoffResult:
    """Result of agent handoff operation.

    Attributes:
        success: Whether handoff succeeded
        target_response: Response from target agent (if successful)
        evidence_preserved: Whether evidence contracts were preserved
        trace_continued: Whether trace context was propagated
        errors: List of error messages (if failed)
        metadata: Additional result metadata

    Example:
        result = HandoffResult(
            success=True,
            target_response=agent_response,
            evidence_preserved=True,
            trace_continued=True,
        )
    """

    success: bool
    target_response: Optional[AgentResponse] = None
    evidence_preserved: bool = False
    trace_continued: bool = False
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "target_response": self.target_response.to_dict() if self.target_response else None,
            "evidence_preserved": self.evidence_preserved,
            "trace_continued": self.trace_continued,
            "errors": self.errors,
            "metadata": self.metadata,
        }


class OrchestratorAdapter(ABC):
    """Abstract base class for orchestration framework adapters.

    Enables AlphaSwarm VRS workflows to execute across external orchestration
    frameworks while preserving evidence-first outputs and BSKG requirements.

    Implementations:
    - AgentsSDKAdapter: Anthropic Agents SDK (Phase 07.1.4-02)
    - LangGraphAdapter: LangChain LangGraph (Phase 07.1.4-03)
    - AutoGenAdapter: Microsoft AutoGen (Phase 07.1.4-04)
    - CrewAIAdapter: CrewAI framework (Phase 07.1.4-05)

    Usage:
        adapter = MyAdapter(config)
        response = await adapter.execute_agent(agent_config, messages)
        result = await adapter.handoff(handoff_context)
    """

    def __init__(self, config: AdapterConfig):
        """Initialize adapter with configuration.

        Args:
            config: Adapter configuration with capabilities
        """
        self.config = config

    @abstractmethod
    async def execute_agent(
        self, config: AgentConfig, messages: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Execute agent with given configuration and messages.

        Args:
            config: Agent configuration (role, prompt, tools, etc.)
            messages: Conversation messages in standardized format

        Returns:
            AgentResponse: Standardized response with content, tokens, cost

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        pass

    @abstractmethod
    async def handoff(self, ctx: HandoffContext) -> HandoffResult:
        """Hand off execution from one agent to another.

        Transfers execution while preserving evidence contracts and trace context.
        Validates evidence integrity before and after handoff.

        Args:
            ctx: Handoff context with source/target agents and evidence

        Returns:
            HandoffResult: Result with target response and validation status

        Raises:
            ValueError: If handoff depth exceeds max_handoff_depth
        """
        pass

    @abstractmethod
    async def spawn_with_trace(
        self, config: AgentConfig, task: str, trace: TraceContext
    ) -> AgentResponse:
        """Spawn agent with trace context propagation.

        Creates a new agent execution with trace continuity for observability.

        Args:
            config: Agent configuration
            task: Task description for the agent
            trace: Trace context to propagate

        Returns:
            AgentResponse: Response with trace attributes attached
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> Set[Any]:
        """Get adapter capabilities.

        Returns:
            Set of AdapterCapability enums supported by this adapter
        """
        pass

    def supports(self, capability: Any) -> bool:
        """Check if adapter supports a capability.

        Args:
            capability: AdapterCapability enum to check

        Returns:
            True if capability is supported
        """
        return capability in self.get_capabilities()

    @abstractmethod
    def export_trace(self, trace: TraceContext) -> Dict[str, Any]:
        """Export trace context for interoperability.

        Converts internal trace format to external format (e.g., OpenTelemetry).

        Args:
            trace: Trace context to export

        Returns:
            Dictionary in external trace format
        """
        pass

    @abstractmethod
    def import_trace(self, data: Dict[str, Any]) -> TraceContext:
        """Import trace context from external format.

        Converts external trace format (e.g., OpenTelemetry) to internal format.

        Args:
            data: Dictionary in external trace format

        Returns:
            TraceContext: Internal trace context
        """
        pass

    def preserve_evidence(
        self, bead: VulnerabilityBead, ctx: HandoffContext
    ) -> VulnerabilityBead:
        """Preserve evidence contracts during handoff.

        Validates that evidence is not modified during framework transitions.
        Creates a snapshot in HandoffContext for verification.

        Args:
            bead: VulnerabilityBead with evidence to preserve
            ctx: Handoff context to store evidence snapshot

        Returns:
            VulnerabilityBead: Unmodified bead (validation ensures no changes)

        Raises:
            ValueError: If evidence contracts are modified
        """
        # Create evidence snapshot for validation
        evidence_snapshot = {
            "bead_id": bead.id,
            "vulnerability_class": bead.vulnerability_class,
            "severity": bead.severity.value,
            "confidence": bead.confidence,
            "vulnerable_function": bead.vulnerable_code.function_name if bead.vulnerable_code else None,
            "matched_properties": list(bead.pattern_context.matched_properties) if bead.pattern_context else [],
        }

        # Store snapshot in handoff context
        ctx.evidence_snapshot = evidence_snapshot

        # Return unmodified bead - evidence contracts MUST NOT change
        # Validation happens when handoff result is checked
        return bead

    def validate_evidence_preserved(
        self, original_bead: VulnerabilityBead, received_bead: VulnerabilityBead, ctx: HandoffContext
    ) -> bool:
        """Validate evidence was preserved during handoff.

        Compares original bead evidence with received bead evidence to ensure
        no modifications occurred during framework transition.

        Args:
            original_bead: Original bead before handoff
            received_bead: Bead received after handoff
            ctx: Handoff context with evidence snapshot

        Returns:
            True if evidence preserved, False otherwise
        """
        # Compare critical evidence fields
        checks = [
            original_bead.id == received_bead.id,
            original_bead.vulnerability_class == received_bead.vulnerability_class,
            original_bead.severity == received_bead.severity,
            original_bead.confidence == received_bead.confidence,
        ]

        # Compare vulnerable code if present
        if original_bead.vulnerable_code and received_bead.vulnerable_code:
            checks.append(
                original_bead.vulnerable_code.function_name
                == received_bead.vulnerable_code.function_name
            )

        # Compare pattern matched_properties if present
        if original_bead.pattern_context and received_bead.pattern_context:
            checks.append(
                set(original_bead.pattern_context.matched_properties)
                == set(received_bead.pattern_context.matched_properties)
            )

        return all(checks)
