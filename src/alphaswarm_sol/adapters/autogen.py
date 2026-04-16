"""AutoGen Adapter for AlphaSwarm VRS.

Implements the OrchestratorAdapter interface for Microsoft AutoGen and Magentic-One,
enabling VRS workflows to run with team chat orchestration while preserving
evidence contracts and BSKG requirements.

Key Features:
- Maps VRS agents to AutoGen ConversableAgent instances
- Team chat coordination (round-robin, selector, swarm)
- Evidence preservation through conversation context
- Distributed tracing across team handoffs

Usage:
    from alphaswarm_sol.adapters.autogen import AutoGenAdapter, AutoGenConfig

    config = AutoGenConfig(
        name="autogen",
        team_type="swarm",
        max_rounds=10,
    )
    adapter = AutoGenAdapter(config)

    # Execute team investigation
    bead_updated = await adapter.execute_team(bead)

Phase: 07.1.4-04 AutoGen & CrewAI Adapters
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

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
from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentResponse, AgentRole
from alphaswarm_sol.beads.schema import VulnerabilityBead

# ===============================================================================
# EXPERIMENTAL STATUS
# ===============================================================================
#
# This adapter is EXPERIMENTAL and provides limited functionality.
#
# Reason: AutoGen has its own agent definition model that differs significantly
# from VRS. Wrapping VRS agents to run in AutoGen is complex and provides
# limited value since VRS already has working runtimes (OpenCode, Claude Code,
# Codex CLI) that execute agents directly.
#
# Current limitations:
# - execute_agent returns placeholder response (no actual AutoGen execution)
# - No actual AutoGen GroupChat/ConversableAgent execution
# - Handoff preserves evidence but doesn't execute target
#
# Future work (if needed):
# - Create native AutoGen agents from VRS agent configs
# - Implement proper GroupChat orchestration with LLM config
# - Handle AutoGen-specific memory and conversation state
#
# For production use, prefer:
# - AgentsSdkAdapter (OpenAI Agents SDK)
# - ClaudeCodeAdapter (Claude Code CLI)
# - BeadsGasTownAdapter (Git-backed orchestration)
# ===============================================================================

EXPERIMENTAL = True

# Lazy imports for optional dependency
HAS_AUTOGEN = False
try:
    from autogen import ConversableAgent, GroupChat, GroupChatManager
    HAS_AUTOGEN = True
except ImportError:
    # Mock classes for type checking when autogen not installed
    ConversableAgent = None
    GroupChat = None
    GroupChatManager = None


# VRS role to AutoGen agent name mapping
VRS_TO_AUTOGEN_ROLE = {
    AgentRole.ATTACKER: "attacker_agent",
    AgentRole.DEFENDER: "defender_agent",
    AgentRole.VERIFIER: "verifier_agent",
    AgentRole.SUPERVISOR: "orchestrator_agent",
}


@dataclass
class AutoGenConfig(AdapterConfig):
    """Configuration for AutoGen adapter.

    Attributes:
        name: Adapter name (default: "autogen")
        capabilities: Set of capabilities (auto-populated if not provided)
        team_type: Team coordination pattern
            - "round_robin": Sequential agent turns
            - "selector": Dynamic agent selection
            - "swarm": Agent-driven handoffs (default)
        max_rounds: Maximum conversation rounds
        human_input_mode: Human interaction mode
            - "NEVER": No human input (default for automation)
            - "TERMINATE": Only on termination
            - "ALWAYS": After every agent message
        code_execution_enabled: Whether to enable code execution (default False for safety)
    """

    # Override parent fields with defaults
    name: str = "autogen"
    capabilities: Set[Any] = field(
        default_factory=lambda: ADAPTER_CAPABILITIES["autogen"].capabilities
    )

    # Adapter-specific fields
    team_type: str = "swarm"  # "round_robin" | "selector" | "swarm"
    max_rounds: int = 10
    human_input_mode: str = "NEVER"  # "NEVER" | "TERMINATE" | "ALWAYS"
    code_execution_enabled: bool = False  # Disabled for safety


class VrsTeam:
    """VRS Agent Team for AutoGen execution.

    Creates a team of ConversableAgent instances mapped from VRS roles
    and coordinates investigation workflow through team chat.

    Attributes:
        adapter: Parent AutoGenAdapter instance
        bead: VulnerabilityBead being investigated
        agents: Dictionary of role -> ConversableAgent
        manager: GroupChatManager for coordination
    """

    def __init__(self, adapter: AutoGenAdapter, bead: VulnerabilityBead):
        """Initialize VRS team for AutoGen.

        Args:
            adapter: AutoGenAdapter instance
            bead: VulnerabilityBead to investigate
        """
        self.adapter = adapter
        self.bead = bead
        self.agents: Dict[AgentRole, Any] = {}
        self.manager: Optional[Any] = None

        # Create agents if AutoGen is available
        if HAS_AUTOGEN:
            self._initialize_team()

    def _initialize_team(self) -> None:
        """Initialize team agents and manager."""
        if not HAS_AUTOGEN:
            return

        # Create VRS agents
        for role in [AgentRole.ATTACKER, AgentRole.DEFENDER, AgentRole.VERIFIER]:
            agent_config = AgentConfig(
                role=role,
                system_prompt=self._get_role_prompt(role),
                tools=[],  # Tools would be configured per role
                metadata={
                    "bead_id": self.bead.id,
                    "vulnerability_class": self.bead.vulnerability_class,
                },
            )
            agent = self._create_vrs_agent(role, agent_config)
            self.agents[role] = agent

    def _get_role_prompt(self, role: AgentRole) -> str:
        """Get system prompt for VRS role.

        Args:
            role: Agent role

        Returns:
            System prompt string
        """
        prompts = {
            AgentRole.ATTACKER: (
                "You are a security attacker agent. Your goal is to construct "
                "exploit paths for the potential vulnerability. Focus on attack "
                "preconditions, exploitation steps, and impact assessment."
            ),
            AgentRole.DEFENDER: (
                "You are a security defender agent. Your goal is to identify "
                "guards, mitigations, and protective mechanisms. Look for access "
                "controls, validation checks, and safety patterns."
            ),
            AgentRole.VERIFIER: (
                "You are a security verifier agent. Your goal is to cross-check "
                "evidence from attacker and defender, then synthesize a verdict. "
                "Consider confidence levels and evidence quality."
            ),
        }
        return prompts.get(
            role, "You are a security analysis agent for Solidity smart contracts."
        )

    def _create_vrs_agent(self, role: AgentRole, config: AgentConfig) -> Any:
        """Create AutoGen ConversableAgent from VRS agent config.

        Args:
            role: VRS agent role
            config: Agent configuration

        Returns:
            ConversableAgent instance (or None if AutoGen not available)
        """
        if not HAS_AUTOGEN:
            return None

        agent_name = VRS_TO_AUTOGEN_ROLE.get(role, f"vrs_{role.value}")

        # Create ConversableAgent with VRS configuration
        agent = ConversableAgent(
            name=agent_name,
            system_message=config.system_prompt,
            llm_config=False,  # Would configure LLM settings in real deployment
            human_input_mode=self.adapter.config_typed.human_input_mode,
            code_execution_config=False,  # Disabled for safety
        )

        return agent

    async def run(self, task: str) -> Dict[str, Any]:
        """Execute team investigation workflow.

        Args:
            task: Investigation task description

        Returns:
            Dictionary with investigation results and evidence
        """
        if not HAS_AUTOGEN or not self.agents:
            return {
                "success": False,
                "error": "AutoGen not available or team not initialized",
            }

        # Create group chat for team coordination
        agent_list = list(self.agents.values())
        groupchat = GroupChat(
            agents=agent_list,
            messages=[],
            max_round=self.adapter.config_typed.max_rounds,
        )

        # Create manager
        self.manager = GroupChatManager(groupchat=groupchat, llm_config=False)

        # Execute team chat (would use actual AutoGen execution in real deployment)
        # For now, return placeholder result
        return {
            "success": True,
            "team_size": len(agent_list),
            "max_rounds": self.adapter.config_typed.max_rounds,
            "bead_id": self.bead.id,
            "evidence_preserved": True,
        }


class AutoGenAdapter(OrchestratorAdapter):
    """AutoGen orchestrator adapter (EXPERIMENTAL).

    WARNING: This adapter is experimental and returns placeholder responses.
    See module-level documentation for details and alternatives.

    Maps VRS agents to AutoGen team structure with chat-based coordination.
    Supports team types: round-robin, selector, and swarm orchestration.

    For production use, prefer:
    - AgentsSdkAdapter (OpenAI Agents SDK)
    - ClaudeCodeAdapter (Claude Code CLI)
    - BeadsGasTownAdapter (Git-backed orchestration)

    Example:
        config = AutoGenConfig(name="autogen", team_type="swarm")
        adapter = AutoGenAdapter(config)

        # Execute team investigation
        bead_updated = await adapter.execute_team(bead)

        # Single agent execution
        response = await adapter.execute_agent(agent_config, messages)
    """

    def __init__(self, config: AutoGenConfig):
        """Initialize AutoGen adapter.

        Args:
            config: AutoGenConfig with team settings
        """
        # Initialize base with adapter-specific capabilities
        if not config.capabilities:
            config.capabilities = ADAPTER_CAPABILITIES["autogen"].capabilities

        super().__init__(config)
        self.config_typed = config

        # Team storage for multi-bead orchestration
        self._teams: Dict[str, VrsTeam] = {}

        # Trace context storage
        self._trace_storage: Dict[str, TraceContext] = {}

    async def execute_agent(
        self, config: AgentConfig, messages: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Execute single agent with AutoGen (EXPERIMENTAL - returns placeholder).

        WARNING: This method is not fully implemented. For production use,
        consider AgentsSdkAdapter, ClaudeCodeAdapter, or BeadsGasTownAdapter.

        Args:
            config: Agent configuration
            messages: Conversation messages

        Returns:
            AgentResponse with agent output (placeholder)
        """
        import warnings
        warnings.warn(
            "AutoGenAdapter.execute_agent is experimental and returns a placeholder. "
            "For production use, prefer AgentsSdkAdapter, ClaudeCodeAdapter, or BeadsGasTownAdapter.",
            category=UserWarning,
            stacklevel=2,
        )

        if not HAS_AUTOGEN:
            return AgentResponse(
                content="AutoGen not installed. Install with: pip install pyautogen",
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cost_usd=0.0,
                model="n/a",
                metadata={"error": "autogen_not_available", "experimental": True},
                tool_calls=[],
            )

        # Create single agent
        agent_name = VRS_TO_AUTOGEN_ROLE.get(config.role, f"vrs_{config.role.value}")
        agent = ConversableAgent(
            name=agent_name,
            system_message=config.system_prompt,
            llm_config=False,
            human_input_mode=self.config_typed.human_input_mode,
            code_execution_config=False,
        )

        # Execute single turn (placeholder - real implementation would run agent)
        return AgentResponse(
            content="Agent execution placeholder (EXPERIMENTAL)",
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
            cost_usd=0.0,
            model="autogen",
            metadata={"agent_name": agent_name, "experimental": True},
            tool_calls=[],
        )

    async def handoff(self, ctx: HandoffContext) -> HandoffResult:
        """Hand off execution between AutoGen agents.

        Args:
            ctx: Handoff context with source/target agents and evidence

        Returns:
            HandoffResult with target agent response
        """
        # Validate handoff depth
        if ctx.handoff_depth >= self.config.max_handoff_depth:
            return HandoffResult(
                success=False,
                errors=[
                    f"Handoff depth {ctx.handoff_depth} exceeds max {self.config.max_handoff_depth}"
                ],
            )

        # Pass context via conversation context (AutoGen uses shared chat)
        # Evidence snapshot stored in HandoffContext for validation
        handoff_message = {
            "role": "system",
            "content": f"Handoff from {ctx.source_agent} to {ctx.target_agent}",
            "metadata": {
                "bead_id": ctx.bead_id,
                "evidence_snapshot": ctx.evidence_snapshot,
                "trace_id": ctx.trace_id,
            },
        }

        # Store trace context
        if ctx.trace_id:
            trace = TraceContext(
                trace_id=ctx.trace_id,
                span_id=str(uuid.uuid4()),
                parent_span_id=ctx.parent_span_id,
                operation="autogen.handoff",
            )
            self._trace_storage[ctx.trace_id] = trace

        # In real implementation, would execute target agent with context
        # For now, return success with evidence preserved flag
        return HandoffResult(
            success=True,
            evidence_preserved=True,
            trace_continued=bool(ctx.trace_id),
            metadata={"handoff_message": handoff_message},
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
            AgentResponse with trace attributes attached
        """
        # Store trace context
        self._trace_storage[trace.trace_id] = trace

        # Create messages with trace metadata
        messages = [
            {
                "role": "user",
                "content": task,
                "trace_id": trace.trace_id,
                "span_id": trace.span_id,
            }
        ]

        # Execute agent with trace
        response = await self.execute_agent(config, messages)

        # Attach trace attributes to response
        response.metadata["trace_id"] = trace.trace_id
        response.metadata["span_id"] = trace.span_id

        return response

    def get_capabilities(self) -> Set[AdapterCapability]:
        """Get AutoGen adapter capabilities.

        Returns:
            Set of supported capabilities
        """
        return ADAPTER_CAPABILITIES["autogen"].capabilities

    def export_trace(self, trace: TraceContext) -> Dict[str, Any]:
        """Export trace context for interoperability.

        Args:
            trace: Trace context to export

        Returns:
            Dictionary in external trace format
        """
        return {
            "trace_id": trace.trace_id,
            "span_id": trace.span_id,
            "parent_span_id": trace.parent_span_id,
            "operation": trace.operation,
            "attributes": trace.attributes,
            "events": trace.events,
            "timestamp": trace.timestamp,
            "adapter": "autogen",
        }

    def import_trace(self, data: Dict[str, Any]) -> TraceContext:
        """Import trace context from external format.

        Args:
            data: Dictionary in external trace format

        Returns:
            TraceContext instance
        """
        return TraceContext.from_dict(data)

    async def execute_team(self, bead: VulnerabilityBead) -> VulnerabilityBead:
        """Execute team investigation workflow for bead.

        Args:
            bead: VulnerabilityBead to investigate

        Returns:
            Updated VulnerabilityBead with investigation results
        """
        # Create VRS team
        team = VrsTeam(self, bead)
        self._teams[bead.id] = team

        # Run team investigation
        task = f"Investigate {bead.vulnerability_class} vulnerability in {bead.vulnerable_code.function_name if bead.vulnerable_code else 'unknown function'}"
        result = await team.run(task)

        # Extract verdict from team output (placeholder)
        if result.get("success"):
            bead.metadata["autogen_team_executed"] = True
            bead.metadata["team_result"] = result

        return bead
