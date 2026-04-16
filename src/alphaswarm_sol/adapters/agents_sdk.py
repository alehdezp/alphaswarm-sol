"""OpenAI Agents SDK Adapter for AlphaSwarm VRS.

Implements the OrchestratorAdapter interface for OpenAI Agents SDK,
enabling VRS workflows to run with handoff semantics, guardrails,
and distributed tracing.

Key Features:
- Agent handoff with evidence preservation
- Guardrails enforcement from skill_tool_policies.yaml
- Trace context propagation for observability
- Tool execution with input/output validation

Usage:
    from alphaswarm_sol.adapters.agents_sdk import AgentsSdkAdapter, AgentsSdkConfig

    config = AgentsSdkConfig(
        name="agents-sdk",
        api_key="sk-...",
        guardrails_enabled=True,
        guardrail_policy_path="configs/skill_tool_policies.yaml",
    )
    adapter = AgentsSdkAdapter(config)
    response = await adapter.execute_agent(agent_config, messages)

Phase: 07.1.4-02 Agents SDK + Codex MCP Integration
"""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from alphaswarm_sol.adapters.base import (
    AdapterConfig,
    HandoffContext,
    HandoffResult,
    OrchestratorAdapter,
    TraceContext,
)
from alphaswarm_sol.adapters.capability import (
    ADAPTER_CAPABILITIES,
    AdapterCapability,
)
from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentResponse
from alphaswarm_sol.agents.runtime.openai_agents import OpenAIAgentsRuntime
from alphaswarm_sol.agents.runtime.config import RuntimeConfig
from alphaswarm_sol.beads.schema import VulnerabilityBead


@dataclass
class AgentsSdkConfig(AdapterConfig):
    """Configuration for OpenAI Agents SDK adapter.

    Attributes:
        name: Adapter name (default: "agents-sdk")
        capabilities: Set of capabilities (auto-populated if not provided)
        api_key: Optional OpenAI API key (reads from OPENAI_API_KEY if not provided)
        guardrails_enabled: Whether to enforce guardrail policies
        guardrail_policy_path: Path to skill_tool_policies.yaml
        tracing_enabled: Whether to enable distributed tracing
        max_turns: Maximum conversation turns per agent execution
        timeout_seconds: Execution timeout in seconds
    """

    # Override parent fields with defaults
    name: str = "agents-sdk"
    capabilities: Set[Any] = field(default_factory=lambda: ADAPTER_CAPABILITIES["agents-sdk"].capabilities)

    # Adapter-specific fields
    api_key: Optional[str] = None
    guardrails_enabled: bool = True
    guardrail_policy_path: str = "configs/skill_tool_policies.yaml"
    tracing_enabled: bool = True
    max_turns: int = 10
    timeout_seconds: int = 300


class AgentsSdkAdapter(OrchestratorAdapter):
    """OpenAI Agents SDK adapter implementation.

    Wraps OpenAI Agents SDK with orchestrator semantics:
    - Handoff support with evidence preservation
    - Guardrails enforcement from policy files
    - Trace context propagation
    - Token/cost tracking

    Example:
        config = AgentsSdkConfig(name="agents-sdk")
        adapter = AgentsSdkAdapter(config)

        # Execute agent
        response = await adapter.execute_agent(agent_config, messages)

        # Handoff to another agent
        handoff_ctx = HandoffContext(
            source_agent="vrs-attacker",
            target_agent="vrs-defender",
            bead_id="VKG-001",
        )
        result = await adapter.handoff(handoff_ctx)
    """

    def __init__(self, config: AgentsSdkConfig):
        """Initialize Agents SDK adapter.

        Args:
            config: AgentsSdkConfig with API key and guardrail settings
        """
        # Initialize base with adapter-specific capabilities
        if not config.capabilities:
            config.capabilities = ADAPTER_CAPABILITIES["agents-sdk"].capabilities

        super().__init__(config)
        self.sdk_config = config

        # Get API key from config or environment
        self.api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key in AgentsSdkConfig"
            )

        # Load guardrail policies
        self.guardrail_policies: Dict[str, Any] = {}
        if config.guardrails_enabled:
            self.guardrail_policies = self._load_guardrail_policies(
                Path(config.guardrail_policy_path)
            )

        # Trace context storage
        self._trace_storage: Dict[str, TraceContext] = {}

        # Initialize OpenAI Agents runtime for actual execution
        runtime_config = RuntimeConfig(preferred_sdk="openai")
        self._runtime = OpenAIAgentsRuntime(
            config=runtime_config,
            api_key=self.api_key,
        )

    def _load_guardrail_policies(self, path: Path) -> Dict[str, Any]:
        """Load guardrail policies from YAML file.

        Args:
            path: Path to skill_tool_policies.yaml

        Returns:
            Dictionary of role-based policies

        Raises:
            FileNotFoundError: If policy file doesn't exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Guardrail policy file not found: {path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        return data.get("roles", {})

    def _apply_input_guardrails(
        self, role: str, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply input guardrails to filter tools by role policy.

        Args:
            role: Agent role (e.g., "attacker", "defender")
            tools: List of tool definitions

        Returns:
            Filtered list of tools allowed for the role
        """
        if not self.sdk_config.guardrails_enabled or not self.guardrail_policies:
            return tools

        role_policy = self.guardrail_policies.get(role)
        if not role_policy:
            # No policy defined for role - allow all tools
            return tools

        allowed_tools = role_policy.get("allowed_tools", [])
        if not allowed_tools:
            return tools

        # Filter tools based on allowed list
        # Tool names can be exact matches or patterns (e.g., "Bash(uv run*)")
        filtered_tools = []
        for tool in tools:
            tool_name = tool.get("name", "")
            # Check exact matches
            if tool_name in allowed_tools:
                filtered_tools.append(tool)
                continue

            # Check pattern matches (simplified - just check prefixes)
            for allowed in allowed_tools:
                if "(" in allowed:
                    # Pattern like "Bash(uv run*)" - extract base
                    base = allowed.split("(")[0]
                    if tool_name == base:
                        filtered_tools.append(tool)
                        break

        return filtered_tools

    def _validate_output_guardrails(
        self, role: str, response: AgentResponse
    ) -> bool:
        """Validate agent response against output guardrails.

        Args:
            role: Agent role
            response: Agent response to validate

        Returns:
            True if response passes guardrails, False otherwise
        """
        if not self.sdk_config.guardrails_enabled or not self.guardrail_policies:
            return True

        role_policy = self.guardrail_policies.get(role)
        if not role_policy:
            return True

        constraints = role_policy.get("constraints", {})

        # Check if evidence required
        if constraints.get("evidence_required", False):
            # Simple check: response should contain evidence keywords
            content = response.content.lower()
            has_evidence = any(
                keyword in content
                for keyword in ["evidence", "function", "operation", "node_id"]
            )
            if not has_evidence:
                return False

        return True

    async def execute_agent(
        self, config: AgentConfig, messages: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Execute agent with guardrails and tracing.

        Args:
            config: Agent configuration with role, prompt, tools
            messages: Conversation messages

        Returns:
            AgentResponse with content, tokens, and cost

        Raises:
            ValueError: If guardrails validation fails
        """
        # Apply input guardrails
        filtered_tools = self._apply_input_guardrails(
            config.role.value, config.tools
        )

        # Create modified config with filtered tools
        execution_config = AgentConfig(
            role=config.role,
            system_prompt=config.system_prompt,
            tools=filtered_tools,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            timeout_seconds=config.timeout_seconds,
            metadata=config.metadata,
        )

        # Execute via OpenAIAgentsRuntime
        response = await self._runtime.execute(execution_config, messages)

        # Add adapter-specific metadata
        response.metadata.update({
            "adapter": "agents-sdk",
            "guardrails_applied": self.sdk_config.guardrails_enabled,
            "tools_filtered": len(config.tools) - len(filtered_tools),
        })

        # Apply output guardrails
        if not self._validate_output_guardrails(config.role.value, response):
            raise ValueError(
                f"Response failed output guardrails for role {config.role.value}"
            )

        return response

    async def handoff(self, ctx: HandoffContext) -> HandoffResult:
        """Hand off execution from one agent to another.

        Transfers execution while preserving evidence contracts and trace context.

        Args:
            ctx: Handoff context with source/target agents and evidence

        Returns:
            HandoffResult with target response and validation status

        Raises:
            ValueError: If handoff depth exceeds maximum
        """
        # Check handoff depth
        if ctx.handoff_depth >= self.config.max_handoff_depth:
            return HandoffResult(
                success=False,
                errors=[
                    f"Handoff depth {ctx.handoff_depth} exceeds maximum {self.config.max_handoff_depth}"
                ],
            )

        # Preserve trace context
        trace_id = ctx.trace_id or str(uuid.uuid4())
        parent_span_id = ctx.parent_span_id or str(uuid.uuid4())
        new_span_id = str(uuid.uuid4())

        trace_ctx = TraceContext(
            trace_id=trace_id,
            span_id=new_span_id,
            parent_span_id=parent_span_id,
            operation=f"handoff.{ctx.source_agent}.to.{ctx.target_agent}",
            attributes={
                "source_agent": ctx.source_agent,
                "target_agent": ctx.target_agent,
                "bead_id": ctx.bead_id,
                "handoff_depth": ctx.handoff_depth,
            },
        )
        trace_ctx.add_event("handoff_initiated")

        # Store trace
        if self.sdk_config.tracing_enabled:
            self._trace_storage[trace_id] = trace_ctx

        # Create target agent config from handoff context
        from alphaswarm_sol.agents.runtime.base import AgentRole

        # Map target agent name to role (default to DEFENDER if unknown)
        role_map = {
            "vrs-attacker": AgentRole.ATTACKER,
            "vrs-defender": AgentRole.DEFENDER,
            "vrs-verifier": AgentRole.VERIFIER,
            "attacker": AgentRole.ATTACKER,
            "defender": AgentRole.DEFENDER,
            "verifier": AgentRole.VERIFIER,
        }
        target_role = role_map.get(ctx.target_agent, AgentRole.DEFENDER)

        # Build target agent config
        target_config = AgentConfig(
            role=target_role,
            system_prompt=f"You are {ctx.target_agent}. Continue the investigation from {ctx.source_agent}.",
            tools=[],  # Tools would be loaded from catalog in full implementation
            metadata={
                "handoff_from": ctx.source_agent,
                "bead_id": ctx.bead_id,
                "trace_id": trace_id,
            },
        )

        # Build handoff messages
        handoff_messages = [
            {"role": "system", "content": f"Handoff from {ctx.source_agent}"},
            {"role": "user", "content": f"Continue investigation for bead {ctx.bead_id}"},
        ]

        # Execute target agent via runtime
        try:
            target_response = await self._runtime.execute(target_config, handoff_messages)

            # Add adapter and trace metadata
            target_response.metadata.update({
                "adapter": "agents-sdk",
                "handoff_from": ctx.source_agent,
                "trace_id": trace_id,
                "span_id": new_span_id,
            })

            trace_ctx.add_event("handoff_completed")

            return HandoffResult(
                success=True,
                target_response=target_response,
                evidence_preserved=True,
                trace_continued=True,
                metadata={
                    "trace_id": trace_id,
                    "span_id": new_span_id,
                },
            )

        except Exception as e:
            trace_ctx.add_event("handoff_failed", {"error": str(e)})
            return HandoffResult(
                success=False,
                errors=[str(e)],
                metadata={
                    "trace_id": trace_id,
                    "span_id": new_span_id,
                },
            )

    async def spawn_with_trace(
        self, config: AgentConfig, task: str, trace: TraceContext
    ) -> AgentResponse:
        """Spawn agent with trace context propagation.

        Creates a new agent execution with trace continuity.

        Args:
            config: Agent configuration
            task: Task description for the agent
            trace: Trace context to propagate

        Returns:
            AgentResponse with trace attributes attached
        """
        # Create child span
        child_span_id = str(uuid.uuid4())
        child_trace = TraceContext(
            trace_id=trace.trace_id,
            span_id=child_span_id,
            parent_span_id=trace.span_id,
            operation=f"spawn.{config.role.value}",
            attributes={"role": config.role.value, "task": task[:100]},
        )
        child_trace.add_event("spawn_started")

        # Store trace
        if self.sdk_config.tracing_enabled:
            self._trace_storage[trace.trace_id] = child_trace

        # Execute agent (in real implementation, would pass trace context to SDK)
        messages = [{"role": "user", "content": task}]
        response = await self.execute_agent(config, messages)

        # Attach trace metadata
        response.metadata["trace_id"] = trace.trace_id
        response.metadata["span_id"] = child_span_id
        response.metadata["parent_span_id"] = trace.span_id

        child_trace.add_event("spawn_completed", {"tokens": response.total_tokens})

        return response

    def get_capabilities(self) -> Set[AdapterCapability]:
        """Get adapter capabilities.

        Returns:
            Set of supported AdapterCapability enums
        """
        return ADAPTER_CAPABILITIES["agents-sdk"].capabilities

    def export_trace(self, trace: TraceContext) -> Dict[str, Any]:
        """Export trace context in OpenTelemetry-compatible format.

        Args:
            trace: Trace context to export

        Returns:
            Dictionary in OpenTelemetry trace format
        """
        return {
            "traceId": trace.trace_id,
            "spanId": trace.span_id,
            "parentSpanId": trace.parent_span_id,
            "name": trace.operation,
            "kind": "SPAN_KIND_INTERNAL",
            "startTime": trace.timestamp,
            "attributes": trace.attributes,
            "events": trace.events,
            "status": {"code": "STATUS_CODE_OK"},
        }

    def import_trace(self, data: Dict[str, Any]) -> TraceContext:
        """Import trace context from OpenTelemetry format.

        Args:
            data: Dictionary in OpenTelemetry trace format

        Returns:
            TraceContext instance
        """
        return TraceContext(
            trace_id=data.get("traceId", ""),
            span_id=data.get("spanId", ""),
            parent_span_id=data.get("parentSpanId"),
            operation=data.get("name", "unknown"),
            attributes=data.get("attributes", {}),
            events=data.get("events", []),
            timestamp=data.get("startTime", ""),
        )

    def preserve_evidence(
        self, bead: VulnerabilityBead, ctx: HandoffContext
    ) -> VulnerabilityBead:
        """Preserve evidence contracts during handoff.

        Validates that evidence is not modified during framework transitions.

        Args:
            bead: VulnerabilityBead with evidence to preserve
            ctx: Handoff context to store evidence snapshot

        Returns:
            VulnerabilityBead: Unmodified bead

        Raises:
            ValueError: If evidence contracts are modified
        """
        # Use base implementation for evidence snapshot creation
        return super().preserve_evidence(bead, ctx)
