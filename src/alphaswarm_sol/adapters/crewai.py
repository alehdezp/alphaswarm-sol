"""CrewAI Adapter for AlphaSwarm VRS.

Implements the OrchestratorAdapter interface for CrewAI framework,
enabling VRS workflows to run with crew-based task delegation while
preserving evidence contracts and BSKG requirements.

Key Features:
- Maps VRS agents to CrewAI Agent instances with roles and goals
- Task delegation workflow for investigation steps
- Evidence preservation through crew memory
- Sequential and hierarchical process support

Usage:
    from alphaswarm_sol.adapters.crewai import CrewAIAdapter, CrewAIConfig

    config = CrewAIConfig(
        name="crewai",
        process_type="sequential",
        memory_enabled=True,
    )
    adapter = CrewAIAdapter(config)

    # Execute crew investigation
    bead_updated = await adapter.execute_crew(bead)

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
# Reason: CrewAI has its own agent definition model (roles, goals, backstories)
# that differs significantly from VRS. Wrapping VRS agents to run in CrewAI is
# complex and provides limited value since VRS already has working runtimes
# (OpenCode, Claude Code, Codex CLI) that execute agents directly.
#
# Current limitations:
# - execute_agent returns placeholder response (no actual CrewAI execution)
# - No actual Crew.kickoff() execution
# - Handoff preserves evidence but doesn't execute target
#
# Future work (if needed):
# - Create native CrewAI agents from VRS agent configs
# - Implement proper Crew orchestration with task delegation
# - Handle CrewAI-specific memory and process configuration
#
# For production use, prefer:
# - AgentsSdkAdapter (OpenAI Agents SDK)
# - ClaudeCodeAdapter (Claude Code CLI)
# - BeadsGasTownAdapter (Git-backed orchestration)
# ===============================================================================

EXPERIMENTAL = True

# Lazy imports for optional dependency
HAS_CREWAI = False
try:
    from crewai import Agent, Task, Crew, Process
    HAS_CREWAI = True
except ImportError:
    # Mock classes for type checking when crewai not installed
    Agent = None
    Task = None
    Crew = None
    Process = None


# VRS role to CrewAI role/goal/backstory mapping
VRS_TO_CREWAI_ROLE = {
    AgentRole.ATTACKER: {
        "role": "Security Attacker",
        "goal": "Find exploitation paths for potential vulnerabilities",
        "backstory": (
            "Expert in constructing attack vectors and exploit chains. "
            "Specializes in identifying how vulnerabilities can be weaponized "
            "and assessing their exploitability and impact."
        ),
    },
    AgentRole.DEFENDER: {
        "role": "Security Defender",
        "goal": "Identify guards, mitigations, and protective mechanisms",
        "backstory": (
            "Expert in defensive security patterns and mitigation strategies. "
            "Specializes in finding access controls, validation checks, and "
            "safety mechanisms that prevent exploitation."
        ),
    },
    AgentRole.VERIFIER: {
        "role": "Security Verifier",
        "goal": "Synthesize evidence into verdicts with confidence assessment",
        "backstory": (
            "Expert in evidence evaluation and cross-checking security claims. "
            "Specializes in weighing attack and defense evidence to produce "
            "accurate verdicts with calibrated confidence levels."
        ),
    },
    AgentRole.SUPERVISOR: {
        "role": "Security Orchestrator",
        "goal": "Coordinate investigation workflow and manage agent handoffs",
        "backstory": (
            "Expert in security investigation orchestration. "
            "Specializes in coordinating multi-agent workflows, managing "
            "evidence flow, and ensuring investigation completeness."
        ),
    },
}


@dataclass
class CrewAIConfig(AdapterConfig):
    """Configuration for CrewAI adapter.

    Attributes:
        name: Adapter name (default: "crewai")
        capabilities: Set of capabilities (auto-populated if not provided)
        process_type: Crew process type
            - "sequential": Tasks executed in order (default)
            - "hierarchical": Manager coordinates tasks
        verbose: Whether to enable verbose logging
        memory_enabled: Whether to enable crew memory (default True)
        max_iterations: Maximum task iterations per agent
    """

    # Override parent fields with defaults
    name: str = "crewai"
    capabilities: Set[Any] = field(
        default_factory=lambda: ADAPTER_CAPABILITIES["crewai"].capabilities
    )

    # Adapter-specific fields
    process_type: str = "sequential"  # "sequential" | "hierarchical"
    verbose: bool = False
    memory_enabled: bool = True
    max_iterations: int = 5


class VrsCrew:
    """VRS Agent Crew for CrewAI execution.

    Creates a crew of CrewAI Agent instances mapped from VRS roles
    and coordinates investigation workflow through task delegation.

    Attributes:
        adapter: Parent CrewAIAdapter instance
        bead: VulnerabilityBead being investigated
        agents: Dictionary of role -> Agent
        tasks: List of investigation tasks
        crew: Crew instance for execution
    """

    def __init__(self, adapter: CrewAIAdapter, bead: VulnerabilityBead):
        """Initialize VRS crew for CrewAI.

        Args:
            adapter: CrewAIAdapter instance
            bead: VulnerabilityBead to investigate
        """
        self.adapter = adapter
        self.bead = bead
        self.agents: Dict[AgentRole, Any] = {}
        self.tasks: List[Any] = []
        self.crew: Optional[Any] = None

        # Create crew if CrewAI is available
        if HAS_CREWAI:
            self._initialize_crew()

    def _initialize_crew(self) -> None:
        """Initialize crew agents, tasks, and crew instance."""
        if not HAS_CREWAI:
            return

        # Create VRS agents
        for role in [AgentRole.ATTACKER, AgentRole.DEFENDER, AgentRole.VERIFIER]:
            agent_config = AgentConfig(
                role=role,
                system_prompt="",  # Prompts embedded in role/goal/backstory
                tools=[],
                metadata={
                    "bead_id": self.bead.id,
                    "vulnerability_class": self.bead.vulnerability_class,
                },
            )
            agent = self._create_vrs_agent(role, agent_config)
            self.agents[role] = agent

        # Create investigation tasks
        self.tasks = self._create_investigation_tasks(self.bead)

        # Assemble crew
        agent_list = list(self.agents.values())
        process_enum = Process.sequential if self.adapter.config_typed.process_type == "sequential" else Process.hierarchical

        self.crew = Crew(
            agents=agent_list,
            tasks=self.tasks,
            process=process_enum,
            verbose=self.adapter.config_typed.verbose,
            memory=self.adapter.config_typed.memory_enabled,
        )

    def _create_vrs_agent(self, role: AgentRole, config: AgentConfig) -> Any:
        """Create CrewAI Agent from VRS agent config.

        Args:
            role: VRS agent role
            config: Agent configuration

        Returns:
            CrewAI Agent instance (or None if CrewAI not available)
        """
        if not HAS_CREWAI:
            return None

        # Get role mapping
        role_config = VRS_TO_CREWAI_ROLE.get(
            role,
            {
                "role": f"VRS {role.value}",
                "goal": "Analyze smart contract security",
                "backstory": "Expert in Solidity security analysis",
            },
        )

        # Create CrewAI Agent with VRS role configuration
        agent = Agent(
            role=role_config["role"],
            goal=role_config["goal"],
            backstory=role_config["backstory"],
            verbose=self.adapter.config_typed.verbose,
            allow_delegation=False,  # VRS agents work independently
            tools=[],  # Tools would be configured per role
        )

        return agent

    def _create_investigation_tasks(self, bead: VulnerabilityBead) -> List[Any]:
        """Create investigation tasks for crew workflow.

        Args:
            bead: VulnerabilityBead being investigated

        Returns:
            List of CrewAI Task instances
        """
        if not HAS_CREWAI:
            return []

        tasks = []

        # Task 1: Attack path analysis (attacker)
        if AgentRole.ATTACKER in self.agents:
            attack_task = Task(
                description=(
                    f"Analyze the {bead.vulnerability_class} vulnerability "
                    f"in function {bead.vulnerable_code.function_name if bead.vulnerable_code else 'unknown'}. "
                    f"Construct exploit paths with attack preconditions, exploitation steps, "
                    f"and impact assessment. Focus on how the vulnerability can be weaponized."
                ),
                expected_output=(
                    "Attack analysis with: attack preconditions, exploitation steps, "
                    "exploitability assessment, and potential impact"
                ),
                agent=self.agents[AgentRole.ATTACKER],
            )
            tasks.append(attack_task)

        # Task 2: Guard detection (defender)
        if AgentRole.DEFENDER in self.agents:
            defense_task = Task(
                description=(
                    f"Search for guards and mitigations that protect against the "
                    f"{bead.vulnerability_class} vulnerability. Look for access controls, "
                    f"validation checks, reentrancy guards, and other safety mechanisms."
                ),
                expected_output=(
                    "Defense analysis with: guards found, mitigation analysis, "
                    "residual risks, and protective mechanism assessment"
                ),
                agent=self.agents[AgentRole.DEFENDER],
            )
            tasks.append(defense_task)

        # Task 3: Verdict synthesis (verifier)
        if AgentRole.VERIFIER in self.agents:
            verify_task = Task(
                description=(
                    f"Cross-check evidence from attack and defense analysis. "
                    f"Synthesize a verdict on whether {bead.vulnerability_class} is exploitable. "
                    f"Assess evidence quality and provide confidence level."
                ),
                expected_output=(
                    "Verification verdict with: verdict (vulnerable/safe), confidence level, "
                    "evidence quality assessment, and rationale"
                ),
                agent=self.agents[AgentRole.VERIFIER],
            )
            tasks.append(verify_task)

        return tasks

    async def kickoff(self) -> Dict[str, Any]:
        """Execute crew investigation workflow.

        Returns:
            Dictionary with investigation results and evidence
        """
        if not HAS_CREWAI or not self.crew:
            return {
                "success": False,
                "error": "CrewAI not available or crew not initialized",
            }

        # Execute crew workflow (would use actual CrewAI execution in real deployment)
        # For now, return placeholder result
        return {
            "success": True,
            "crew_size": len(self.agents),
            "task_count": len(self.tasks),
            "bead_id": self.bead.id,
            "evidence_preserved": True,
            "process_type": self.adapter.config_typed.process_type,
        }


class CrewAIAdapter(OrchestratorAdapter):
    """CrewAI orchestrator adapter (EXPERIMENTAL).

    WARNING: This adapter is experimental and returns placeholder responses.
    See module-level documentation for details and alternatives.

    Maps VRS agents to CrewAI crew structure with task-based delegation.
    Supports sequential and hierarchical process coordination.

    For production use, prefer:
    - AgentsSdkAdapter (OpenAI Agents SDK)
    - ClaudeCodeAdapter (Claude Code CLI)
    - BeadsGasTownAdapter (Git-backed orchestration)

    Example:
        config = CrewAIConfig(name="crewai", process_type="sequential")
        adapter = CrewAIAdapter(config)

        # Execute crew investigation
        bead_updated = await adapter.execute_crew(bead)

        # Single agent execution
        response = await adapter.execute_agent(agent_config, messages)
    """

    def __init__(self, config: CrewAIConfig):
        """Initialize CrewAI adapter.

        Args:
            config: CrewAIConfig with crew settings
        """
        # Initialize base with adapter-specific capabilities
        if not config.capabilities:
            config.capabilities = ADAPTER_CAPABILITIES["crewai"].capabilities

        super().__init__(config)
        self.config_typed = config

        # Crew storage for multi-bead orchestration
        self._crews: Dict[str, VrsCrew] = {}

        # Trace context storage
        self._trace_storage: Dict[str, TraceContext] = {}

    async def execute_agent(
        self, config: AgentConfig, messages: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Execute single agent with CrewAI (EXPERIMENTAL - returns placeholder).

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
            "CrewAIAdapter.execute_agent is experimental and returns a placeholder. "
            "For production use, prefer AgentsSdkAdapter, ClaudeCodeAdapter, or BeadsGasTownAdapter.",
            category=UserWarning,
            stacklevel=2,
        )

        if not HAS_CREWAI:
            return AgentResponse(
                content="CrewAI not installed. Install with: pip install crewai",
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cost_usd=0.0,
                model="n/a",
                metadata={"error": "crewai_not_available", "experimental": True},
                tool_calls=[],
            )

        # Get role mapping
        role_config = VRS_TO_CREWAI_ROLE.get(config.role)
        if not role_config:
            return AgentResponse(
                content=f"No CrewAI mapping for role {config.role}",
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cost_usd=0.0,
                model="n/a",
                metadata={"error": "role_not_mapped", "experimental": True},
                tool_calls=[],
            )

        # Create single agent with single task
        agent = Agent(
            role=role_config["role"],
            goal=role_config["goal"],
            backstory=role_config["backstory"],
            verbose=self.config_typed.verbose,
            allow_delegation=False,
            tools=[],
        )

        # Extract task from messages
        task_description = messages[-1]["content"] if messages else "Analyze security"
        task = Task(
            description=task_description,
            expected_output="Security analysis result",
            agent=agent,
        )

        # Execute single agent task (placeholder - real implementation would run crew)
        return AgentResponse(
            content="Agent execution placeholder (EXPERIMENTAL)",
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
            cost_usd=0.0,
            model="crewai",
            metadata={"agent_role": role_config["role"], "experimental": True},
            tool_calls=[],
        )

    async def handoff(self, ctx: HandoffContext) -> HandoffResult:
        """Hand off execution between CrewAI agents.

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

        # CrewAI uses task delegation for handoffs
        # Evidence stored in crew memory and task context
        handoff_metadata = {
            "source_agent": ctx.source_agent,
            "target_agent": ctx.target_agent,
            "bead_id": ctx.bead_id,
            "evidence_snapshot": ctx.evidence_snapshot,
            "trace_id": ctx.trace_id,
        }

        # Store trace context
        if ctx.trace_id:
            trace = TraceContext(
                trace_id=ctx.trace_id,
                span_id=str(uuid.uuid4()),
                parent_span_id=ctx.parent_span_id,
                operation="crewai.handoff",
            )
            self._trace_storage[ctx.trace_id] = trace

        # In real implementation, would create Task delegation with context
        # For now, return success with evidence preserved flag
        return HandoffResult(
            success=True,
            evidence_preserved=True,
            trace_continued=bool(ctx.trace_id),
            metadata=handoff_metadata,
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
        """Get CrewAI adapter capabilities.

        Returns:
            Set of supported capabilities
        """
        return ADAPTER_CAPABILITIES["crewai"].capabilities

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
            "adapter": "crewai",
        }

    def import_trace(self, data: Dict[str, Any]) -> TraceContext:
        """Import trace context from external format.

        Args:
            data: Dictionary in external trace format

        Returns:
            TraceContext instance
        """
        return TraceContext.from_dict(data)

    async def execute_crew(self, bead: VulnerabilityBead) -> VulnerabilityBead:
        """Execute crew investigation workflow for bead.

        Args:
            bead: VulnerabilityBead to investigate

        Returns:
            Updated VulnerabilityBead with investigation results
        """
        # Create VRS crew
        crew = VrsCrew(self, bead)
        self._crews[bead.id] = crew

        # Run crew investigation
        result = await crew.kickoff()

        # Extract verdict from crew output (placeholder)
        if result.get("success"):
            bead.metadata["crewai_crew_executed"] = True
            bead.metadata["crew_result"] = result

        return bead
