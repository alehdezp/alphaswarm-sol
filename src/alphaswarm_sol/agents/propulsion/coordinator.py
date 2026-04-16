"""Multi-Agent Coordinator for Propulsion System.

Implements SDK-06 (propulsion/autonomous work-pulling) and SDK-08 (CLI/SDK parity).
The coordinator orchestrates multiple agents processing beads from a pool.

Key features:
- Pool-based bead distribution
- Role-based agent spawning with task type routing
- Parallel attacker/defender execution
- Verifier assignment when both attacker and defender complete
- CLI/SDK artifact parity via CoordinatorReport
- Cost tracking and threshold enforcement

Per 05.3-CONTEXT.md (Plan 08):
- Attacker: TaskType.CRITICAL (needs deep reasoning)
- Defender: TaskType.ANALYZE (fast analysis)
- Verifier: TaskType.CRITICAL (needs accuracy)
- Test builder: TaskType.CODE (code generation)

Usage:
    from alphaswarm_sol.agents.propulsion import AgentCoordinator, CoordinatorConfig
    from alphaswarm_sol.agents.runtime import create_runtime

    runtime = create_runtime()
    coordinator = AgentCoordinator(runtime, CoordinatorConfig(
        agents_per_role={"attacker": 2, "defender": 2, "verifier": 1}
    ))
    coordinator.setup_for_pool(pool, beads)
    report = await coordinator.run(timeout=3600)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING

from alphaswarm_sol.agents.runtime.types import TaskType

if TYPE_CHECKING:
    from alphaswarm_sol.agents.runtime import AgentRuntime, AgentConfig, AgentResponse
    from alphaswarm_sol.orchestration.schemas import Pool
    from alphaswarm_sol.beads.schema import VulnerabilityBead

logger = logging.getLogger(__name__)


class CoordinatorStatus(str, Enum):
    """Status of the coordinator."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETE = "complete"
    FAILED = "failed"
    COST_EXCEEDED = "cost_exceeded"


@dataclass
class CoordinatorConfig:
    """Configuration for agent coordinator.

    Attributes:
        agents_per_role: Number of concurrent agents per role
        enable_supervisor: Whether to run supervisor monitoring
        supervisor_check_interval: Seconds between supervisor checks
        enable_integration: Whether to run final integration
        poll_interval: Seconds between work polling
        work_timeout: Timeout per work item in seconds
        cost_threshold_usd: Optional cost threshold to abort execution
    """

    agents_per_role: Dict[str, int] = field(
        default_factory=lambda: {
            "attacker": 2,
            "defender": 2,
            "verifier": 1,
            "test_builder": 1,
        }
    )
    enable_supervisor: bool = True
    supervisor_check_interval: int = 60
    enable_integration: bool = True
    poll_interval: float = 1.0
    work_timeout: int = 300
    cost_threshold_usd: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agents_per_role": self.agents_per_role,
            "enable_supervisor": self.enable_supervisor,
            "supervisor_check_interval": self.supervisor_check_interval,
            "enable_integration": self.enable_integration,
            "poll_interval": self.poll_interval,
            "work_timeout": self.work_timeout,
            "cost_threshold_usd": self.cost_threshold_usd,
        }


@dataclass
class WorkResult:
    """Result of processing one work item.

    Attributes:
        bead_id: ID of the processed bead
        agent_role: Role of the agent that processed it
        success: Whether processing succeeded
        response: Agent response if successful
        error: Error message if failed
        duration_ms: Processing duration in milliseconds
        resumed: Whether this was resumed from previous state
        runtime_used: Which runtime was selected
        model_used: Which model was used
        cost_usd: Cost for this execution
    """

    bead_id: str
    agent_role: str
    success: bool
    response: Optional[Any] = None
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
            "agent_role": self.agent_role,
            "success": self.success,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "resumed": self.resumed,
            "runtime_used": self.runtime_used,
            "model_used": self.model_used,
            "cost_usd": round(self.cost_usd, 6),
        }


@dataclass
class CostBreakdown:
    """Cost breakdown for coordinator execution.

    Attributes:
        total_cost_usd: Total cost across all executions
        by_role: Cost breakdown by agent role
        by_runtime: Cost breakdown by runtime
        by_model: Cost breakdown by model
    """

    total_cost_usd: float = 0.0
    by_role: Dict[str, float] = field(default_factory=dict)
    by_runtime: Dict[str, float] = field(default_factory=dict)
    by_model: Dict[str, float] = field(default_factory=dict)

    def add(
        self,
        cost_usd: float,
        role: str,
        runtime: str,
        model: str,
    ) -> None:
        """Add cost entry."""
        self.total_cost_usd += cost_usd
        self.by_role[role] = self.by_role.get(role, 0.0) + cost_usd
        self.by_runtime[runtime] = self.by_runtime.get(runtime, 0.0) + cost_usd
        self.by_model[model] = self.by_model.get(model, 0.0) + cost_usd

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_cost_usd": round(self.total_cost_usd, 6),
            "by_role": {k: round(v, 6) for k, v in self.by_role.items()},
            "by_runtime": {k: round(v, 6) for k, v in self.by_runtime.items()},
            "by_model": {k: round(v, 6) for k, v in self.by_model.items()},
        }


@dataclass
class CoordinatorReport:
    """Report from coordinator execution.

    This is the contract for SDK-08 parity - both CLI and SDK
    produce the same report format for consistent artifact outputs.

    Attributes:
        status: Final coordinator status
        total_beads: Total beads in the pool
        completed_beads: Successfully processed beads
        failed_beads: Failed bead count
        results_by_role: Count of results per role
        duration_seconds: Total execution duration
        stuck_work: List of bead IDs that got stuck
        verdicts: Verdicts produced (optional)
        cost_breakdown: Cost breakdown by role/runtime/model
    """

    status: CoordinatorStatus
    total_beads: int
    completed_beads: int
    failed_beads: int
    results_by_role: Dict[str, int]
    duration_seconds: float
    stuck_work: List[str]
    verdicts: List[Dict[str, Any]] = field(default_factory=list)
    cost_breakdown: Optional[CostBreakdown] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        This is the artifact contract for SDK-08 parity.
        CLI and SDK both use this format.
        """
        result = {
            "status": self.status.value,
            "total_beads": self.total_beads,
            "completed_beads": self.completed_beads,
            "failed_beads": self.failed_beads,
            "results_by_role": self.results_by_role,
            "duration_seconds": self.duration_seconds,
            "stuck_work": self.stuck_work,
            "verdicts": self.verdicts,
        }
        if self.cost_breakdown:
            result["cost_breakdown"] = self.cost_breakdown.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoordinatorReport":
        """Create from dictionary."""
        cost_data = data.get("cost_breakdown")
        cost_breakdown = None
        if cost_data:
            cost_breakdown = CostBreakdown(
                total_cost_usd=cost_data.get("total_cost_usd", 0.0),
                by_role=cost_data.get("by_role", {}),
                by_runtime=cost_data.get("by_runtime", {}),
                by_model=cost_data.get("by_model", {}),
            )

        return cls(
            status=CoordinatorStatus(data["status"]),
            total_beads=data["total_beads"],
            completed_beads=data["completed_beads"],
            failed_beads=data["failed_beads"],
            results_by_role=data["results_by_role"],
            duration_seconds=data["duration_seconds"],
            stuck_work=data["stuck_work"],
            verdicts=data.get("verdicts", []),
            cost_breakdown=cost_breakdown,
        )


# Role to task type mapping per 05.3-CONTEXT.md
ROLE_TO_TASK_TYPE: Dict[str, TaskType] = {
    "attacker": TaskType.CRITICAL,
    "defender": TaskType.ANALYZE,
    "verifier": TaskType.CRITICAL,
    "test_builder": TaskType.CODE,
}


class AgentCoordinator:
    """Coordinates multiple agents processing a pool of beads.

    Orchestrates:
    1. Pool/bead intake and distribution
    2. Parallel attacker/defender execution with task type routing
    3. Verifier assignment when both attacker and defender complete
    4. Supervisor monitoring for stuck work
    5. Integration of final results
    6. Cost tracking and threshold enforcement

    Per 05.2-CONTEXT.md:
    - Pool config specifies how many agents per role
    - Beads distributed round-robin to attacker/defender
    - Verifier processes beads only after both attacker and defender complete

    Per 05.3-CONTEXT.md (Plan 08):
    - Attacker: TaskType.CRITICAL
    - Defender: TaskType.ANALYZE
    - Verifier: TaskType.CRITICAL
    - Test builder: TaskType.CODE

    Usage:
        coordinator = AgentCoordinator(runtime, config)
        coordinator.setup_for_pool(pool, beads)
        report = await coordinator.run(timeout=3600)
    """

    def __init__(
        self,
        runtime: "AgentRuntime",
        config: Optional[CoordinatorConfig] = None,
    ):
        """Initialize coordinator.

        Args:
            runtime: Agent runtime for spawning agents
            config: Coordinator configuration
        """
        self.runtime = runtime
        self.config = config or CoordinatorConfig()
        self._status = CoordinatorStatus.IDLE
        self._pool: Optional["Pool"] = None
        self._beads: List["VulnerabilityBead"] = []
        self._bead_registry: Dict[str, "VulnerabilityBead"] = {}

        # Track completion for verifier assignment
        self._attacker_complete: Set[str] = set()
        self._defender_complete: Set[str] = set()
        self._verifier_queue: List[str] = []

        # Results tracking
        self._results: List[WorkResult] = []
        self._stuck_work: List[str] = []

        # Cost tracking
        self._cost_breakdown = CostBreakdown()

    def setup_for_pool(
        self, pool: "Pool", beads: List["VulnerabilityBead"]
    ) -> None:
        """Set up coordinator for a pool of beads.

        Args:
            pool: Pool to process
            beads: Beads to distribute to agents
        """
        self._pool = pool
        self._beads = beads

        # Register beads for lookup
        for bead in beads:
            self._bead_registry[bead.id] = bead

        # Clear previous state
        self._attacker_complete.clear()
        self._defender_complete.clear()
        self._verifier_queue.clear()
        self._results.clear()
        self._stuck_work.clear()
        self._cost_breakdown = CostBreakdown()

        logger.info(
            "Coordinator setup complete",
            extra={
                "pool_id": pool.id if pool else "no-pool",
                "bead_count": len(beads),
            },
        )

    async def run(self, timeout: Optional[int] = None) -> CoordinatorReport:
        """Run coordinated agent execution.

        Execution phases:
        1. Spawn attacker and defender agents for each bead in parallel
        2. As both complete for a bead, assign to verifier queue
        3. Run verifier agents on completed beads
        4. Check for stuck work (supervisor)
        5. Compile and return report

        Args:
            timeout: Optional timeout in seconds

        Returns:
            CoordinatorReport with execution results
        """
        self._status = CoordinatorStatus.RUNNING
        start_time = datetime.now()

        try:
            # Phase 1: Run attacker and defender in parallel
            await self._run_analysis_phase(timeout)

            # Check cost threshold after analysis phase
            if self._should_abort_for_cost():
                logger.warning(
                    f"Cost threshold exceeded: ${self._cost_breakdown.total_cost_usd:.4f}"
                )
                self._status = CoordinatorStatus.COST_EXCEEDED
                duration = (datetime.now() - start_time).total_seconds()
                return self._compile_report(duration)

            # Phase 2: Run verifiers on completed beads
            await self._run_verification_phase(timeout)

            # Phase 3: Supervisor check for stuck work
            if self.config.enable_supervisor:
                self._check_stuck_work()

            self._status = CoordinatorStatus.COMPLETE

        except asyncio.TimeoutError:
            logger.warning("Coordinator timeout reached")
            self._status = CoordinatorStatus.FAILED

        except Exception as e:
            logger.error(f"Coordinator failed: {e}")
            self._status = CoordinatorStatus.FAILED
            raise

        duration = (datetime.now() - start_time).total_seconds()
        return self._compile_report(duration)

    def _should_abort_for_cost(self) -> bool:
        """Check if cost threshold has been exceeded."""
        if self.config.cost_threshold_usd is None:
            return False
        return self._cost_breakdown.total_cost_usd >= self.config.cost_threshold_usd

    async def _run_analysis_phase(self, timeout: Optional[int]) -> None:
        """Run attacker and defender analysis on all beads."""
        from alphaswarm_sol.agents.runtime import AgentRole, AgentConfig

        tasks = []

        for bead in self._beads:
            # Spawn attacker agent with CRITICAL task type
            tasks.append(
                self._process_bead(
                    bead,
                    "attacker",
                    TaskType.CRITICAL,
                    self._on_attacker_complete,
                    timeout,
                )
            )
            # Spawn defender agent with ANALYZE task type
            tasks.append(
                self._process_bead(
                    bead,
                    "defender",
                    TaskType.ANALYZE,
                    self._on_defender_complete,
                    timeout,
                )
            )

        # Run all in parallel with configured concurrency
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_verification_phase(self, timeout: Optional[int]) -> None:
        """Run verifier on beads that have completed analysis."""
        tasks = []

        for bead_id in self._verifier_queue:
            bead = self._bead_registry.get(bead_id)
            if bead:
                # Verifier uses CRITICAL task type for accuracy
                tasks.append(
                    self._process_bead(
                        bead,
                        "verifier",
                        TaskType.CRITICAL,
                        None,
                        timeout,
                    )
                )

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_bead(
        self,
        bead: "VulnerabilityBead",
        role: str,
        task_type: TaskType,
        on_complete: Optional[Callable[[str, Any], None]],
        timeout: Optional[int],
    ) -> WorkResult:
        """Process a single bead with the specified role.

        Args:
            bead: Bead to process
            role: Agent role (attacker, defender, verifier)
            task_type: Task type for routing and model selection
            on_complete: Callback when complete
            timeout: Timeout in seconds

        Returns:
            WorkResult from processing
        """
        from alphaswarm_sol.agents.runtime import AgentRole, AgentConfig

        start_time = time.monotonic()
        work_timeout = timeout or self.config.work_timeout

        try:
            # Build role-specific prompt
            prompt = self._build_prompt(bead, role)

            # Get agent config
            agent_config = self._get_agent_config(role)

            # Log runtime selection
            logger.info(
                f"Processing bead {bead.id} with role={role}, task_type={task_type.value}"
            )

            # Execute with timeout
            response = await asyncio.wait_for(
                self.runtime.spawn_agent(agent_config, prompt),
                timeout=work_timeout,
            )

            duration_ms = int((time.monotonic() - start_time) * 1000)

            # Extract runtime and model info from response
            runtime_used = ""
            model_used = ""
            cost_usd = 0.0

            if hasattr(response, "metadata") and response.metadata:
                runtime_used = response.metadata.get("runtime_used", "")
            if hasattr(response, "model"):
                model_used = response.model or ""
            if hasattr(response, "cost_usd"):
                cost_usd = response.cost_usd or 0.0

            result = WorkResult(
                bead_id=bead.id,
                agent_role=role,
                success=True,
                response=response,
                duration_ms=duration_ms,
                runtime_used=runtime_used,
                model_used=model_used,
                cost_usd=cost_usd,
            )

            # Track costs
            self._cost_breakdown.add(
                cost_usd=cost_usd,
                role=role,
                runtime=runtime_used or "unknown",
                model=model_used or "unknown",
            )

            # Trigger callback
            if on_complete:
                on_complete(bead.id, response)

            self._results.append(result)
            return result

        except asyncio.TimeoutError:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            result = WorkResult(
                bead_id=bead.id,
                agent_role=role,
                success=False,
                error="Timeout",
                duration_ms=duration_ms,
            )
            self._results.append(result)
            return result

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            result = WorkResult(
                bead_id=bead.id,
                agent_role=role,
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )
            self._results.append(result)
            return result

    def _on_attacker_complete(self, bead_id: str, response: Any) -> None:
        """Handle attacker completing work on a bead.

        If defender has also completed, assign to verifier queue.
        """
        self._attacker_complete.add(bead_id)
        self._check_verifier_assignment(bead_id)

    def _on_defender_complete(self, bead_id: str, response: Any) -> None:
        """Handle defender completing work on a bead.

        If attacker has also completed, assign to verifier queue.
        """
        self._defender_complete.add(bead_id)
        self._check_verifier_assignment(bead_id)

    def _check_verifier_assignment(self, bead_id: str) -> None:
        """Assign bead to verifier if both attacker and defender completed.

        This is the key workflow gate: verifier only processes beads
        after BOTH attacker AND defender have completed their analysis.
        """
        if (
            bead_id in self._attacker_complete
            and bead_id in self._defender_complete
            and bead_id not in self._verifier_queue
        ):
            logger.info(
                f"Bead {bead_id}: Both attacker and defender complete, "
                "assigning to verifier"
            )
            self._verifier_queue.append(bead_id)

    def _build_prompt(self, bead: "VulnerabilityBead", role: str) -> str:
        """Build role-specific prompt from bead."""
        # Get base prompt from bead
        base_prompt = ""
        if hasattr(bead, "get_llm_prompt"):
            base_prompt = bead.get_llm_prompt()
        elif hasattr(bead, "hypothesis"):
            base_prompt = f"Analyze: {bead.hypothesis}"
        else:
            base_prompt = f"Analyze bead {bead.id}"

        role_instructions = {
            "attacker": (
                "You are a security researcher looking for vulnerabilities. "
                "Focus on constructing an exploit scenario."
            ),
            "defender": (
                "You are a security researcher looking for mitigations. "
                "Focus on finding safe patterns and guards."
            ),
            "verifier": (
                "You are a verification agent. "
                "Cross-check the attacker and defender analysis and synthesize a verdict."
            ),
            "test_builder": (
                "You are a test engineer. "
                "Generate a Foundry test to demonstrate the vulnerability."
            ),
        }

        instruction = role_instructions.get(
            role, "Analyze this potential vulnerability."
        )
        return f"{base_prompt}\n\n## Your Role: {role.upper()}\n{instruction}"

    def _get_agent_config(self, role: str) -> "AgentConfig":
        """Get agent configuration for role."""
        from alphaswarm_sol.agents.runtime import AgentRole, AgentConfig

        # Map string role to enum
        role_map = {
            "attacker": AgentRole.ATTACKER,
            "defender": AgentRole.DEFENDER,
            "verifier": AgentRole.VERIFIER,
            "test_builder": AgentRole.TEST_BUILDER,
        }

        agent_role = role_map.get(role, AgentRole.ATTACKER)

        # System prompts per role
        system_prompts = {
            "attacker": (
                "You are an expert security auditor specializing in smart contract "
                "vulnerabilities. Your goal is to find and articulate attack paths."
            ),
            "defender": (
                "You are a smart contract security engineer. "
                "Your goal is to find mitigations, guards, and safe patterns."
            ),
            "verifier": (
                "You are a verification specialist. "
                "Your goal is to cross-check evidence and produce a final verdict."
            ),
            "test_builder": (
                "You are a Solidity test engineer. "
                "Your goal is to write Foundry tests that demonstrate vulnerabilities."
            ),
        }

        return AgentConfig(
            role=agent_role,
            system_prompt=system_prompts.get(role, "You are a security analyst."),
            tools=[],
        )

    def _check_stuck_work(self) -> None:
        """Check for any stuck work items."""
        # Beads that weren't fully processed
        for bead in self._beads:
            if bead.id not in self._attacker_complete:
                self._stuck_work.append(f"{bead.id}:attacker")
            if bead.id not in self._defender_complete:
                self._stuck_work.append(f"{bead.id}:defender")

    def _compile_report(self, duration: float) -> CoordinatorReport:
        """Compile execution report."""
        completed = sum(1 for r in self._results if r.success)
        failed = sum(1 for r in self._results if not r.success)

        # Count by role
        by_role: Dict[str, int] = {}
        for result in self._results:
            role = result.agent_role
            by_role[role] = by_role.get(role, 0) + 1

        return CoordinatorReport(
            status=self._status,
            total_beads=len(self._beads),
            completed_beads=completed,
            failed_beads=failed,
            results_by_role=by_role,
            duration_seconds=duration,
            stuck_work=self._stuck_work,
            cost_breakdown=self._cost_breakdown,
        )

    def stop(self) -> None:
        """Stop coordinator gracefully."""
        self._status = CoordinatorStatus.PAUSED

    @property
    def status(self) -> CoordinatorStatus:
        """Get current coordinator status."""
        return self._status

    @property
    def attacker_complete_count(self) -> int:
        """Get count of beads completed by attacker."""
        return len(self._attacker_complete)

    @property
    def defender_complete_count(self) -> int:
        """Get count of beads completed by defender."""
        return len(self._defender_complete)

    @property
    def verifier_pending_count(self) -> int:
        """Get count of beads waiting for verifier."""
        return len(self._verifier_queue)

    @property
    def total_cost_usd(self) -> float:
        """Get total cost of all executions."""
        return self._cost_breakdown.total_cost_usd

    def get_cost_breakdown(self) -> CostBreakdown:
        """Get cost breakdown."""
        return self._cost_breakdown


__all__ = [
    "CoordinatorStatus",
    "CoordinatorConfig",
    "CoordinatorReport",
    "CostBreakdown",
    "AgentCoordinator",
    "WorkResult",
    "ROLE_TO_TASK_TYPE",
]
