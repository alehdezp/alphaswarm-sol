"""Propulsion Engine for Autonomous Agent Work-Pulling.

This module implements the propulsion engine that enables agents to
autonomously pull work from their hooks (inboxes) and process beads.

Per PHILOSOPHY.md:
- Agents pull work from their hooks (inboxes)
- Context-fresh: new agent instance per bead
- Work state persists so agents can resume

Per 05.2-CONTEXT.md:
- Hybrid work claiming: orchestrator assigns, agents can pull more
- Configurable agents per role
- Beads distributed round-robin

Per 05.3-CONTEXT.md (Plan 08):
- Propulsion engine uses new runtime factory
- Task type is passed to runtime for model selection
- Rankings store is integrated for feedback
- Fallback from free models to paid models works

Integration Flow:
    PropulsionEngine.execute_agent(role, task_type)
        -> ModelSelector.select(profile)
        -> TaskRouter.route(role, task_type)
        -> Runtime.execute(config, messages, model=selected_model)
        -> FeedbackCollector.record(feedback)

Usage:
    from alphaswarm_sol.agents.propulsion import PropulsionEngine, PropulsionConfig

    engine = PropulsionEngine(
        runtime=runtime,
        inboxes={AgentRole.ATTACKER: attacker_inbox},
        config=PropulsionConfig(max_concurrent_per_role=2),
    )
    results = await engine.run(timeout=300)
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from alphaswarm_sol.agents.hooks import WorkClaim
from alphaswarm_sol.agents.hooks.inbox import AgentInbox
from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentResponse, AgentRole
from alphaswarm_sol.agents.runtime import AgentRuntime
from alphaswarm_sol.agents.runtime.router import route_to_runtime, TaskRouter, RoutingPolicy
from alphaswarm_sol.agents.runtime.types import TaskType
from alphaswarm_sol.agents.ranking import (
    RankingsStore,
    ModelSelector,
    FeedbackCollector,
    TaskFeedback,
    TaskProfile,
    Complexity,
)
from alphaswarm_sol.beads.schema import VulnerabilityBead

logger = logging.getLogger(__name__)


# Default quality score for successful executions (no explicit quality signal)
DEFAULT_QUALITY_SCORE = 0.75


@dataclass
class PropulsionConfig:
    """Configuration for propulsion engine.

    Attributes:
        max_concurrent_per_role: Maximum concurrent agents per role (default 2)
        poll_interval_seconds: Interval between work checks (default 1.0)
        work_timeout_seconds: Timeout for individual work items (default 300)
        enable_resume: Whether to resume from work_state (default True)
        enable_fallback: Whether to fallback to Claude Code on failure (default True)
        enable_workspace_isolation: Whether to use jj workspaces for parallel agents (Phase 07.3.1.9)
        pool_id: Pool ID for workspace isolation (required if enable_workspace_isolation)
        cost_threshold_usd: Optional cost threshold to abort execution
        on_complete: Callback when work completes successfully
        on_error: Callback when work fails

    Usage:
        config = PropulsionConfig(
            max_concurrent_per_role=3,
            work_timeout_seconds=600,
            enable_workspace_isolation=True,
            pool_id="audit-001",
            on_complete=lambda bead_id, resp: print(f"Done: {bead_id}"),
        )
    """

    max_concurrent_per_role: int = 2
    poll_interval_seconds: float = 1.0
    work_timeout_seconds: int = 300
    enable_resume: bool = True
    enable_fallback: bool = True
    enable_workspace_isolation: bool = False
    pool_id: Optional[str] = None
    cost_threshold_usd: Optional[float] = None
    on_complete: Optional[Callable[[str, AgentResponse], None]] = None
    on_error: Optional[Callable[[str, Exception], None]] = None

    # Backward compatibility property
    @property
    def enable_worktree_isolation(self) -> bool:
        """Deprecated: Use enable_workspace_isolation instead."""
        import warnings
        warnings.warn(
            "enable_worktree_isolation is deprecated, use enable_workspace_isolation",
            DeprecationWarning,
            stacklevel=2
        )
        return self.enable_workspace_isolation

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "max_concurrent_per_role": self.max_concurrent_per_role,
            "poll_interval_seconds": self.poll_interval_seconds,
            "work_timeout_seconds": self.work_timeout_seconds,
            "enable_resume": self.enable_resume,
            "enable_fallback": self.enable_fallback,
            "enable_workspace_isolation": self.enable_workspace_isolation,
            "pool_id": self.pool_id,
            "cost_threshold_usd": self.cost_threshold_usd,
        }


@dataclass
class WorkResult:
    """Result of processing one work item.

    Attributes:
        bead_id: ID of the bead processed
        agent_role: Role of the agent that processed it
        success: Whether processing succeeded
        response: AgentResponse if successful
        error: Error message if failed
        duration_ms: Processing duration in milliseconds
        resumed: Whether this was resumed work
        runtime_used: Which runtime was selected
        model_used: Which model was used
        cost_usd: Cost for this execution

    Usage:
        result = WorkResult(
            bead_id="VKG-001",
            agent_role=AgentRole.ATTACKER,
            success=True,
            response=response,
            duration_ms=1500,
            runtime_used="opencode",
            model_used="deepseek/deepseek-v3.2",
            cost_usd=0.0012,
        )
    """

    bead_id: str
    agent_role: AgentRole
    success: bool
    response: Optional[AgentResponse] = None
    error: Optional[str] = None
    duration_ms: int = 0
    resumed: bool = False
    runtime_used: str = ""
    model_used: str = ""
    cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "bead_id": self.bead_id,
            "agent_role": self.agent_role.value,
            "success": self.success,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "resumed": self.resumed,
            "runtime_used": self.runtime_used,
            "model_used": self.model_used,
            "cost_usd": self.cost_usd,
        }


@dataclass
class CostSummary:
    """Summary of execution costs.

    Attributes:
        total_cost_usd: Total cost across all executions
        by_runtime: Cost breakdown by runtime
        by_model: Cost breakdown by model
        by_role: Cost breakdown by agent role
        execution_count: Total number of executions
    """

    total_cost_usd: float = 0.0
    by_runtime: Dict[str, float] = field(default_factory=dict)
    by_model: Dict[str, float] = field(default_factory=dict)
    by_role: Dict[str, float] = field(default_factory=dict)
    execution_count: int = 0

    def add_execution(
        self,
        cost_usd: float,
        runtime: str,
        model: str,
        role: str,
    ) -> None:
        """Add execution cost to summary."""
        self.total_cost_usd += cost_usd
        self.by_runtime[runtime] = self.by_runtime.get(runtime, 0.0) + cost_usd
        self.by_model[model] = self.by_model.get(model, 0.0) + cost_usd
        self.by_role[role] = self.by_role.get(role, 0.0) + cost_usd
        self.execution_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_cost_usd": round(self.total_cost_usd, 6),
            "by_runtime": {k: round(v, 6) for k, v in self.by_runtime.items()},
            "by_model": {k: round(v, 6) for k, v in self.by_model.items()},
            "by_role": {k: round(v, 6) for k, v in self.by_role.items()},
            "execution_count": self.execution_count,
        }


class PropulsionEngine:
    """Autonomous work-pulling engine for agents.

    Per PHILOSOPHY.md:
    - Agents pull work from their hooks (inboxes)
    - Context-fresh: new agent instance per bead
    - Work state persists so agents can resume

    Per 05.2-CONTEXT.md:
    - Hybrid work claiming: orchestrator assigns, agents can pull more
    - Configurable agents per role
    - Beads distributed round-robin

    Per 05.3-CONTEXT.md (Plan 08):
    - Uses TaskRouter for runtime selection based on role/task type
    - Uses ModelSelector for optimal model selection from rankings
    - Records feedback via FeedbackCollector
    - Supports fallback from free to paid models

    Attributes:
        runtime: AgentRuntime for spawning agents
        inboxes: Map of AgentRole to AgentInbox
        config: PropulsionConfig settings
        rankings_store: RankingsStore for model rankings
        selector: ModelSelector for model selection
        feedback_collector: FeedbackCollector for recording feedback
        router: TaskRouter for runtime routing

    Usage:
        engine = PropulsionEngine(runtime, inboxes)
        results = await engine.run(timeout=300)

        # With callbacks
        config = PropulsionConfig(
            on_complete=lambda bid, resp: print(f"Done: {bid}"),
            on_error=lambda bid, e: print(f"Failed: {bid}: {e}"),
        )
        engine = PropulsionEngine(runtime, inboxes, config)
        results = await engine.run()
    """

    def __init__(
        self,
        runtime: AgentRuntime,
        inboxes: Dict[AgentRole, AgentInbox],
        config: Optional[PropulsionConfig] = None,
        rankings_store: Optional[RankingsStore] = None,
    ) -> None:
        """Initialize propulsion engine.

        Args:
            runtime: AgentRuntime for agent execution
            inboxes: Map of role to inbox for that role
            config: Optional configuration
            rankings_store: Optional RankingsStore for model rankings
        """
        self.runtime = runtime
        self.inboxes = inboxes
        self.config = config or PropulsionConfig()
        self._running = False
        self._active_tasks: Dict[str, asyncio.Task] = {}  # task_id -> task
        self._results: List[WorkResult] = []

        # Initialize ranking system components
        self.rankings_store = rankings_store or RankingsStore()
        self.selector = ModelSelector(self.rankings_store)
        self.feedback_collector = FeedbackCollector(self.rankings_store)
        self.router = TaskRouter()

        # Cost tracking
        self._cost_summary = CostSummary()

        # Fallback tracking
        self._fallback_count = 0

        # Workspace isolation (Phase 07.3.1.9 - jujutsu-based)
        self._workspace_manager = None
        if self.config.enable_workspace_isolation:
            from alphaswarm_sol.orchestration.workspace import WorkspaceManager
            try:
                self._workspace_manager = WorkspaceManager()
                logger.info("Workspace isolation enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize WorkspaceManager: {e}")
                self._workspace_manager = None

    async def run(self, timeout: Optional[int] = None) -> List[WorkResult]:
        """Run propulsion until all inboxes empty or timeout.

        Continuously polls inboxes and spawns agents to process work.
        Each bead gets a context-fresh agent instance.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            List of WorkResult for all processed items

        Usage:
            results = await engine.run(timeout=600)
            for r in results:
                if r.success:
                    print(f"{r.bead_id}: completed in {r.duration_ms}ms")
                else:
                    print(f"{r.bead_id}: failed - {r.error}")
        """
        self._running = True
        self._results = []
        start = datetime.now()

        try:
            while self._running:
                # Check timeout
                if timeout and (datetime.now() - start).total_seconds() > timeout:
                    logger.info("Propulsion timeout reached")
                    break

                # Check cost threshold
                if self._should_abort_for_cost():
                    logger.warning(
                        f"Cost threshold exceeded: ${self._cost_summary.total_cost_usd:.4f} "
                        f">= ${self.config.cost_threshold_usd}"
                    )
                    break

                # Check if any work remains
                if not self._has_work():
                    # Wait for active tasks to complete
                    if self._active_tasks:
                        await asyncio.sleep(self.config.poll_interval_seconds)
                        continue
                    else:
                        logger.info("All work complete")
                        break

                # Spawn workers for each role
                for role, inbox in self.inboxes.items():
                    await self._spawn_if_needed(role, inbox)

                await asyncio.sleep(self.config.poll_interval_seconds)

        finally:
            self._running = False
            # Wait for remaining tasks
            if self._active_tasks:
                await asyncio.gather(
                    *self._active_tasks.values(), return_exceptions=True
                )

        return self._results

    def _should_abort_for_cost(self) -> bool:
        """Check if cost threshold has been exceeded."""
        if self.config.cost_threshold_usd is None:
            return False
        return self._cost_summary.total_cost_usd >= self.config.cost_threshold_usd

    async def _spawn_if_needed(self, role: AgentRole, inbox: AgentInbox) -> None:
        """Spawn agent for role if under concurrency limit.

        Args:
            role: Agent role to spawn for
            inbox: Inbox to claim work from
        """
        # Count active tasks for this role
        active_for_role = sum(
            1 for task_id in self._active_tasks if task_id.startswith(role.value)
        )

        if active_for_role >= self.config.max_concurrent_per_role:
            return

        # Claim work
        claim = inbox.claim_work()
        if claim is None:
            return

        # Spawn context-fresh agent
        task_id = f"{role.value}_{claim.bead.id}"
        task = asyncio.create_task(self._process_work(role, claim))
        self._active_tasks[task_id] = task

        # Add callback for cleanup
        task.add_done_callback(lambda t: self._on_task_done(task_id, role, claim))

    async def _process_work(self, role: AgentRole, claim: WorkClaim) -> WorkResult:
        """Process single work item with context-fresh agent.

        Per 05.2-CONTEXT.md: Context-fresh (new instance per bead)
        Per 05.3-CONTEXT.md: Uses TaskRouter + ModelSelector

        Args:
            role: Role of the agent to spawn
            claim: WorkClaim with bead to process

        Returns:
            WorkResult with outcome
        """
        start = datetime.now()
        bead = claim.bead

        # Check for resumable work state
        resumed = False
        work_context = ""
        if self.config.enable_resume and bead.work_state:
            work_context = f"\n\nResuming from previous state:\n{bead.work_state}"
            resumed = True

        # Determine task type from role
        task_type = self._get_task_type_for_role(role)

        # Build agent prompt
        prompt = self._build_agent_prompt(bead, role, work_context)

        # Create unique agent ID for workspace isolation
        agent_id = f"{role.value}_{bead.id}"

        # Get agent config for this role (with workspace if enabled)
        agent_config = self._get_agent_config(role, agent_id=agent_id)

        try:
            # Execute with new runtime integration
            response = await self._execute_with_routing(
                agent_config=agent_config,
                prompt=prompt,
                role=role,
                task_type=task_type,
            )

            # Save work state for resumability
            self._save_work_state(bead, role, response)

            duration = int((datetime.now() - start).total_seconds() * 1000)
            result = WorkResult(
                bead_id=bead.id,
                agent_role=role,
                success=True,
                response=response,
                duration_ms=duration,
                resumed=resumed,
                runtime_used=response.metadata.get("runtime_used", ""),
                model_used=response.model,
                cost_usd=response.cost_usd,
            )

            if self.config.on_complete:
                self.config.on_complete(bead.id, response)

            return result

        except asyncio.TimeoutError:
            duration = int((datetime.now() - start).total_seconds() * 1000)
            result = WorkResult(
                bead_id=bead.id,
                agent_role=role,
                success=False,
                error="Timeout",
                duration_ms=duration,
                resumed=resumed,
            )
            if self.config.on_error:
                self.config.on_error(bead.id, TimeoutError("Work timeout"))
            return result

        except Exception as e:
            duration = int((datetime.now() - start).total_seconds() * 1000)
            result = WorkResult(
                bead_id=bead.id,
                agent_role=role,
                success=False,
                error=str(e),
                duration_ms=duration,
                resumed=resumed,
            )
            if self.config.on_error:
                self.config.on_error(bead.id, e)
            return result

    async def _execute_with_routing(
        self,
        agent_config: AgentConfig,
        prompt: str,
        role: AgentRole,
        task_type: TaskType,
    ) -> AgentResponse:
        """Execute agent with routing and model selection.

        Integration flow:
        1. ModelSelector.select(profile) -> best model
        2. TaskRouter.route(role, task_type) -> runtime
        3. runtime.execute(config, messages, model) -> response
        4. FeedbackCollector.record(feedback) -> update rankings

        Fallback logic:
        - If OpenCode fails, retry with Claude Code

        Args:
            agent_config: Agent configuration
            prompt: User prompt
            role: Agent role
            task_type: Task type for routing

        Returns:
            AgentResponse with execution results
        """
        # Build task profile for model selection
        profile = TaskProfile(
            task_type=task_type,
            complexity=Complexity.MODERATE,
            accuracy_critical=(role in (AgentRole.ATTACKER, AgentRole.VERIFIER)),
            latency_sensitive=(role == AgentRole.DEFENDER),
        )

        # Select best model from rankings
        model = self.selector.select(profile)
        logger.debug(f"Selected model '{model}' for {role.value}/{task_type.value}")

        # Route to appropriate runtime
        policy = RoutingPolicy(
            task_type=task_type,
            role=role,
            accuracy_critical=profile.accuracy_critical,
            latency_sensitive=profile.latency_sensitive,
        )
        runtime = self.router.route(policy)
        runtime_name = self._get_runtime_name(runtime)
        logger.info(
            f"Routing {role.value} task to {runtime_name} with model {model}"
        )

        # Execute with selected runtime and model
        messages = [{"role": "user", "content": prompt}]
        start_time = time.monotonic()

        try:
            # Try primary execution
            response = await asyncio.wait_for(
                runtime.execute(agent_config, messages),
                timeout=self.config.work_timeout_seconds,
            )

            # Add runtime metadata
            response.metadata["runtime_used"] = runtime_name
            latency_ms = int((time.monotonic() - start_time) * 1000)
            response.latency_ms = latency_ms

            # Record feedback for ranking updates
            await self._record_feedback(
                task_type=task_type,
                model=response.model or model,
                response=response,
                success=True,
            )

            # Track costs
            self._cost_summary.add_execution(
                cost_usd=response.cost_usd,
                runtime=runtime_name,
                model=response.model or model,
                role=role.value,
            )

            return response

        except Exception as primary_error:
            logger.warning(f"Primary runtime failed: {primary_error}")

            # Attempt fallback if enabled
            if self.config.enable_fallback and runtime_name != "claude_code":
                logger.info("Attempting fallback to Claude Code runtime")
                self._fallback_count += 1

                fallback_runtime = route_to_runtime(
                    role=role,
                    task_type=TaskType.CRITICAL,  # Force Claude Code
                    accuracy_critical=True,
                )
                fallback_runtime_name = self._get_runtime_name(fallback_runtime)

                fallback_response = await asyncio.wait_for(
                    fallback_runtime.execute(agent_config, messages),
                    timeout=self.config.work_timeout_seconds,
                )

                fallback_response.metadata["runtime_used"] = fallback_runtime_name
                fallback_response.metadata["fallback"] = True
                fallback_response.metadata["primary_error"] = str(primary_error)

                latency_ms = int((time.monotonic() - start_time) * 1000)
                fallback_response.latency_ms = latency_ms

                # Record feedback for fallback
                await self._record_feedback(
                    task_type=task_type,
                    model=fallback_response.model or "claude",
                    response=fallback_response,
                    success=True,
                )

                # Track costs
                self._cost_summary.add_execution(
                    cost_usd=fallback_response.cost_usd,
                    runtime=fallback_runtime_name,
                    model=fallback_response.model or "claude",
                    role=role.value,
                )

                return fallback_response

            # Re-raise if no fallback or fallback disabled
            raise

    async def _record_feedback(
        self,
        task_type: TaskType,
        model: str,
        response: AgentResponse,
        success: bool,
    ) -> None:
        """Record feedback for model ranking updates.

        Args:
            task_type: Task type executed
            model: Model used
            response: Response received
            success: Whether execution succeeded
        """
        try:
            feedback = TaskFeedback(
                task_id=str(uuid.uuid4()),
                model_id=model,
                task_type=task_type.value,
                success=success,
                latency_ms=response.latency_ms,
                tokens_used=response.total_tokens,
                quality_score=self._estimate_quality(response),
                cost_usd=response.cost_usd,
                timestamp=datetime.now(),
            )
            self.feedback_collector.record(feedback)
            logger.debug(f"Recorded feedback for {model}/{task_type.value}")
        except Exception as e:
            # Don't fail execution if feedback recording fails
            logger.warning(f"Failed to record feedback: {e}")

    def _estimate_quality(self, response: AgentResponse) -> float:
        """Estimate quality score from response.

        Uses heuristics since we don't have explicit quality signals:
        - Non-empty content: base score
        - Longer content: higher score
        - Tool usage: slight bonus

        Args:
            response: AgentResponse to evaluate

        Returns:
            Quality score 0.0-1.0
        """
        if not response.content:
            return 0.0

        # Base score for non-empty response
        score = DEFAULT_QUALITY_SCORE

        # Bonus for longer responses (up to 0.15)
        content_length = len(response.content)
        if content_length > 500:
            score += min(0.15, content_length / 10000)

        # Small bonus for tool usage
        if response.tool_calls:
            score += 0.05

        return min(1.0, score)

    def _get_runtime_name(self, runtime: AgentRuntime) -> str:
        """Get name of runtime for logging/tracking.

        Args:
            runtime: AgentRuntime instance

        Returns:
            Runtime name string
        """
        # Get class name and derive runtime type
        class_name = runtime.__class__.__name__.lower()

        if "opencode" in class_name:
            return "opencode"
        elif "claude" in class_name:
            return "claude_code"
        elif "codex" in class_name:
            return "codex"
        elif "anthropic" in class_name:
            return "anthropic"
        elif "openai" in class_name:
            return "openai"
        else:
            return class_name

    def _get_task_type_for_role(self, role: AgentRole) -> TaskType:
        """Map agent role to task type for routing.

        Per 05.3-CONTEXT.md:
        - Attacker: CRITICAL (needs deep reasoning)
        - Defender: ANALYZE (fast analysis)
        - Verifier: CRITICAL (needs accuracy)
        - Test builder: CODE (code generation)
        - Supervisor: ANALYZE (orchestration)
        - Integrator: SUMMARIZE (synthesis)

        Args:
            role: Agent role

        Returns:
            Corresponding TaskType
        """
        role_to_task_type = {
            AgentRole.ATTACKER: TaskType.CRITICAL,
            AgentRole.DEFENDER: TaskType.ANALYZE,
            AgentRole.VERIFIER: TaskType.CRITICAL,
            AgentRole.TEST_BUILDER: TaskType.CODE,
            AgentRole.SUPERVISOR: TaskType.ANALYZE,
            AgentRole.INTEGRATOR: TaskType.SUMMARIZE,
        }
        return role_to_task_type.get(role, TaskType.ANALYZE)

    def _on_task_done(
        self, task_id: str, role: AgentRole, claim: WorkClaim
    ) -> None:
        """Handle task completion.

        Args:
            task_id: ID of completed task
            role: Role of the agent
            claim: Original work claim
        """
        task = self._active_tasks.pop(task_id, None)
        if task is None:
            return

        # Release workspace if isolation is enabled
        agent_id = f"{role.value}_{claim.bead.id}"
        if self._workspace_manager and self.config.pool_id:
            try:
                self._workspace_manager.release(
                    pool_id=self.config.pool_id,
                    agent_id=agent_id,
                )
            except Exception as e:
                logger.warning(f"Failed to release workspace for {agent_id}: {e}")

        try:
            result = task.result()
            self._results.append(result)

            inbox = self.inboxes.get(role)
            if inbox:
                if result.success:
                    inbox.complete_work(claim.bead.id)
                else:
                    inbox.fail_work(claim.bead.id)

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            # Mark as failed
            inbox = self.inboxes.get(role)
            if inbox:
                inbox.fail_work(claim.bead.id)

    def _has_work(self) -> bool:
        """Check if any inbox has pending work.

        Returns:
            True if any inbox has pending beads
        """
        return any(inbox.pending_count > 0 for inbox in self.inboxes.values())

    def _build_agent_prompt(
        self, bead: VulnerabilityBead, role: AgentRole, extra_context: str = ""
    ) -> str:
        """Build role-specific prompt from bead.

        Args:
            bead: VulnerabilityBead to analyze
            role: Agent role for role-specific instructions
            extra_context: Additional context (e.g., resume state)

        Returns:
            Complete prompt string
        """
        base_prompt = bead.get_llm_prompt()

        role_instructions = {
            AgentRole.ATTACKER: "Focus on constructing an exploit scenario.",
            AgentRole.DEFENDER: "Focus on finding mitigations and safe patterns.",
            AgentRole.VERIFIER: "Cross-check evidence and synthesize verdict.",
            AgentRole.TEST_BUILDER: "Generate a Foundry test to demonstrate the vulnerability.",
            AgentRole.SUPERVISOR: "Monitor progress and identify stuck work.",
            AgentRole.INTEGRATOR: "Merge verdicts and synthesize final determination.",
        }

        instruction = role_instructions.get(role, "Analyze this vulnerability.")
        return f"{base_prompt}\n\n## Your Role: {role.value.upper()}\n{instruction}{extra_context}"

    def _get_agent_config(
        self,
        role: AgentRole,
        agent_id: Optional[str] = None,
    ) -> AgentConfig:
        """Get agent config for role.

        Args:
            role: Agent role
            agent_id: Optional agent ID for workspace allocation

        Returns:
            AgentConfig with role-specific system prompt
        """
        from alphaswarm_sol.agents.roles.prompts import (
            ATTACKER_SYSTEM_PROMPT,
            DEFENDER_SYSTEM_PROMPT,
            VERIFIER_SYSTEM_PROMPT,
            TEST_BUILDER_SYSTEM_PROMPT,
            SUPERVISOR_SYSTEM_PROMPT,
            INTEGRATOR_SYSTEM_PROMPT,
        )

        prompts = {
            AgentRole.ATTACKER: ATTACKER_SYSTEM_PROMPT,
            AgentRole.DEFENDER: DEFENDER_SYSTEM_PROMPT,
            AgentRole.VERIFIER: VERIFIER_SYSTEM_PROMPT,
            AgentRole.TEST_BUILDER: TEST_BUILDER_SYSTEM_PROMPT,
            AgentRole.SUPERVISOR: SUPERVISOR_SYSTEM_PROMPT,
            AgentRole.INTEGRATOR: INTEGRATOR_SYSTEM_PROMPT,
        }

        # Allocate workspace if isolation is enabled
        workdir = None
        if self._workspace_manager and self.config.pool_id and agent_id:
            try:
                workspace_path = self._workspace_manager.allocate(
                    pool_id=self.config.pool_id,
                    agent_id=agent_id,
                    metadata={"role": role.value},
                )
                workdir = str(workspace_path)
                logger.debug(f"Allocated workspace for {agent_id}: {workdir}")
            except Exception as e:
                logger.warning(f"Failed to allocate workspace for {agent_id}: {e}")

        return AgentConfig(
            role=role,
            system_prompt=prompts.get(role, "You are a security auditor."),
            tools=[],
            workdir=workdir,
            metadata={"agent_id": agent_id} if agent_id else {},
        )

    def _save_work_state(
        self, bead: VulnerabilityBead, role: AgentRole, response: AgentResponse
    ) -> None:
        """Save work state for resumability.

        Args:
            bead: Bead to update
            role: Role that processed it
            response: Agent response
        """
        if bead.work_state is None:
            bead.work_state = {}

        bead.work_state["last_response_summary"] = response.content[:500]
        bead.work_state["tokens_used"] = {
            "input": response.input_tokens,
            "output": response.output_tokens,
        }
        bead.last_agent = role.value
        bead.last_updated = datetime.now()

    def stop(self) -> None:
        """Stop propulsion gracefully.

        Sets running flag to False. Active tasks will complete but
        no new work will be claimed.
        """
        self._running = False

    def cleanup_workspaces(self) -> int:
        """Cleanup all workspaces for the current pool.

        Phase 07.3.1.9: Should be called after the propulsion run completes
        to release workspace resources.

        Returns:
            Number of workspaces cleaned up
        """
        if not self._workspace_manager or not self.config.pool_id:
            return 0

        try:
            return self._workspace_manager.cleanup_pool(self.config.pool_id)
        except Exception as e:
            logger.warning(f"Failed to cleanup workspaces: {e}")
            return 0

    def cleanup_worktrees(self) -> int:
        """Deprecated: Use cleanup_workspaces instead."""
        import warnings
        warnings.warn(
            "cleanup_worktrees is deprecated, use cleanup_workspaces",
            DeprecationWarning,
            stacklevel=2
        )
        return self.cleanup_workspaces()

    def get_workspace_manager(self):
        """Get the workspace manager instance.

        Returns:
            WorkspaceManager if isolation is enabled, None otherwise
        """
        return self._workspace_manager

    def get_worktree_manager(self):
        """Deprecated: Use get_workspace_manager instead."""
        import warnings
        warnings.warn(
            "get_worktree_manager is deprecated, use get_workspace_manager",
            DeprecationWarning,
            stacklevel=2
        )
        return self._workspace_manager

    def get_cost_summary(self) -> CostSummary:
        """Get aggregated cost summary.

        Returns:
            CostSummary with cost breakdown by runtime, model, and role
        """
        return self._cost_summary

    def get_fallback_rate(self) -> float:
        """Get rate of fallbacks to paid models.

        Returns:
            Fallback rate as a fraction (0.0 to 1.0)
        """
        if self._cost_summary.execution_count == 0:
            return 0.0
        return self._fallback_count / self._cost_summary.execution_count

    def get_route_statistics(self) -> Dict[str, int]:
        """Get routing statistics from the router.

        Returns:
            Dictionary of runtime names to route counts
        """
        return self.router.get_route_statistics()

    async def execute_agent(
        self,
        config: AgentConfig,
        messages: List[Dict[str, Any]],
        task_type: TaskType = TaskType.ANALYZE,
    ) -> AgentResponse:
        """Execute agent with configuration and messages.

        Convenience method for direct agent execution without work queue.

        Args:
            config: Agent configuration
            messages: Conversation messages
            task_type: Task type for model selection (default: ANALYZE)

        Returns:
            AgentResponse with content and usage

        Raises:
            RuntimeError: On permanent errors
            TimeoutError: On timeout
        """
        # Build prompt from messages
        prompt_parts = []
        for msg in messages:
            content = msg.get("content", "")
            if content:
                prompt_parts.append(content)
        prompt = "\n".join(prompt_parts)

        # Execute with routing
        response = await self._execute_with_routing(
            agent_config=config,
            prompt=prompt,
            role=config.role,
            task_type=task_type,
        )

        return response

    async def spawn_agent(
        self,
        config: AgentConfig,
        task: str,
        task_type: Optional[TaskType] = None,
    ) -> AgentResponse:
        """Spawn a context-fresh agent for a single task.

        Args:
            config: Agent configuration
            task: Task description
            task_type: Optional task type override

        Returns:
            AgentResponse from the spawned agent
        """
        # Use provided task type or derive from role
        if task_type is None:
            task_type = self._get_task_type_for_role(config.role)

        messages = [{"role": "user", "content": task}]
        return await self.execute_agent(config, messages, task_type)


__all__ = [
    "PropulsionConfig",
    "WorkResult",
    "CostSummary",
    "PropulsionEngine",
]
