"""Phase 12: Swarm Mode for Parallel Micro-Agent Execution.

This module provides parallel execution of multiple micro-agents,
enabling fast verification of multiple findings simultaneously.

Key features:
- Concurrent execution with semaphore control
- Progress tracking
- Cost aggregation
- Graceful error handling
- Result aggregation

Usage:
    from alphaswarm_sol.agents.swarm import (
        SwarmManager,
        SwarmConfig,
        SwarmResult,
        swarm_verify,
    )

    # Simple usage
    results = await swarm_verify(findings, parallel=5)

    # Advanced usage
    manager = SwarmManager(config)
    result = await manager.verify_all(beads)
    print(f"Total cost: ${result.total_cost_usd:.2f}")
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar
import logging

from alphaswarm_sol.beads import VulnerabilityBead, VerdictType
from alphaswarm_sol.agents.microagent import (
    MicroAgent,
    MicroAgentConfig,
    MicroAgentResult,
    MicroAgentStatus,
    MicroAgentType,
    VerificationMicroAgent,
    TestGenMicroAgent,
    create_verifier,
    create_test_generator,
)
from alphaswarm_sol.agents.sdk import (
    SDKManager,
    SDKType,
    sdk_available,
    get_fallback_message,
)


logger = logging.getLogger(__name__)


class SwarmStatus(str, Enum):
    """Status of swarm execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"  # Some succeeded, some failed
    FAILED = "failed"


@dataclass
class SwarmConfig:
    """Configuration for swarm execution.

    Attributes:
        max_parallel: Maximum concurrent agents
        timeout_seconds: Total swarm timeout
        budget_per_agent_usd: Budget per micro-agent
        total_budget_usd: Total budget for entire swarm
        agent_timeout_seconds: Timeout per agent
        agent_type: Type of agents to spawn
        fail_fast: Stop on first failure
    """
    max_parallel: int = 5
    timeout_seconds: int = 600  # 10 minutes total
    budget_per_agent_usd: float = 0.50
    total_budget_usd: float = 10.00
    agent_timeout_seconds: int = 120
    agent_type: MicroAgentType = MicroAgentType.VERIFIER
    fail_fast: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_parallel": self.max_parallel,
            "timeout_seconds": self.timeout_seconds,
            "budget_per_agent_usd": self.budget_per_agent_usd,
            "total_budget_usd": self.total_budget_usd,
            "agent_timeout_seconds": self.agent_timeout_seconds,
            "agent_type": self.agent_type.value,
            "fail_fast": self.fail_fast,
        }


@dataclass
class SwarmProgress:
    """Progress tracking for swarm execution.

    Attributes:
        total: Total number of tasks
        completed: Number completed successfully
        failed: Number failed
        pending: Number still pending
        in_progress: Number currently running
        current_cost_usd: Current total cost
    """
    total: int = 0
    completed: int = 0
    failed: int = 0
    pending: int = 0
    in_progress: int = 0
    current_cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "pending": self.pending,
            "in_progress": self.in_progress,
            "current_cost_usd": round(self.current_cost_usd, 4),
            "percent_complete": round(
                (self.completed + self.failed) / max(1, self.total) * 100, 1
            ),
        }


@dataclass
class SwarmResult:
    """Result from swarm execution.

    Attributes:
        status: Overall swarm status
        results: List of individual agent results
        progress: Final progress state
        duration_seconds: Total execution time
        config: Configuration used
        timestamp: When execution completed
    """
    status: SwarmStatus
    results: List[MicroAgentResult] = field(default_factory=list)
    progress: SwarmProgress = field(default_factory=SwarmProgress)
    duration_seconds: float = 0.0
    config: Optional[SwarmConfig] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "results": [r.to_dict() for r in self.results],
            "progress": self.progress.to_dict(),
            "duration_seconds": self.duration_seconds,
            "config": self.config.to_dict() if self.config else None,
            "timestamp": self.timestamp.isoformat(),
            "summary": self.get_summary(),
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        confirmed = sum(1 for r in self.results if r.verdict == VerdictType.TRUE_POSITIVE)
        rejected = sum(1 for r in self.results if r.verdict == VerdictType.FALSE_POSITIVE)
        inconclusive = sum(1 for r in self.results if r.verdict == VerdictType.INCONCLUSIVE)

        return {
            "total_tasks": self.progress.total,
            "confirmed_vulnerabilities": confirmed,
            "rejected_findings": rejected,
            "inconclusive": inconclusive,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "avg_cost_per_task_usd": round(
                self.total_cost_usd / max(1, len(self.results)), 4
            ),
            "avg_duration_seconds": round(
                sum(r.duration_seconds for r in self.results) / max(1, len(self.results)), 2
            ),
        }

    @property
    def total_cost_usd(self) -> float:
        """Total cost of all agent executions."""
        return sum(r.cost.estimated_cost_usd for r in self.results)

    @property
    def successful_results(self) -> List[MicroAgentResult]:
        """Results that completed successfully."""
        return [r for r in self.results if r.is_success]

    @property
    def confirmed_findings(self) -> List[MicroAgentResult]:
        """Results where vulnerability was confirmed."""
        return [r for r in self.results if r.is_confirmed]

    @property
    def rejected_findings(self) -> List[MicroAgentResult]:
        """Results where finding was rejected."""
        return [r for r in self.results if r.is_rejected]


class SwarmManager:
    """Manager for parallel micro-agent execution.

    Coordinates multiple micro-agents running in parallel with:
    - Concurrency control via semaphore
    - Progress tracking
    - Budget enforcement
    - Timeout handling

    Example:
        manager = SwarmManager(SwarmConfig(max_parallel=5))
        result = await manager.verify_all(beads)

        for r in result.confirmed_findings:
            print(f"Confirmed: {r.reasoning}")
    """

    def __init__(self, config: Optional[SwarmConfig] = None):
        """Initialize swarm manager.

        Args:
            config: Swarm configuration
        """
        self.config = config or SwarmConfig()
        self.sdk_manager = SDKManager()
        self._progress = SwarmProgress()
        self._progress_callback: Optional[Callable[[SwarmProgress], None]] = None

    def set_progress_callback(
        self,
        callback: Callable[[SwarmProgress], None]
    ) -> None:
        """Set callback for progress updates.

        Args:
            callback: Function called with progress updates
        """
        self._progress_callback = callback

    def _update_progress(self) -> None:
        """Update progress and notify callback."""
        if self._progress_callback:
            self._progress_callback(self._progress)

    async def verify_all(
        self,
        beads: List[VulnerabilityBead],
    ) -> SwarmResult:
        """Verify all beads in parallel.

        Args:
            beads: List of VulnerabilityBeads to verify

        Returns:
            SwarmResult with all results
        """
        if not beads:
            return SwarmResult(
                status=SwarmStatus.COMPLETED,
                config=self.config,
            )

        # Check SDK availability
        if not self.sdk_manager.any_available():
            logger.warning("No SDK available for swarm verification")
            return SwarmResult(
                status=SwarmStatus.FAILED,
                progress=SwarmProgress(
                    total=len(beads),
                    failed=len(beads),
                ),
                config=self.config,
            )

        start_time = time.time()

        # Initialize progress
        self._progress = SwarmProgress(
            total=len(beads),
            pending=len(beads),
        )
        self._update_progress()

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.config.max_parallel)

        # Create agents and execute
        results: List[MicroAgentResult] = []

        async def verify_with_semaphore(bead: VulnerabilityBead) -> MicroAgentResult:
            async with semaphore:
                self._progress.pending -= 1
                self._progress.in_progress += 1
                self._update_progress()

                try:
                    agent = create_verifier(
                        budget_usd=self.config.budget_per_agent_usd,
                        timeout_seconds=self.config.agent_timeout_seconds,
                    )
                    result = await agent.execute(bead)

                    if result.is_success:
                        self._progress.completed += 1
                    else:
                        self._progress.failed += 1

                    self._progress.current_cost_usd += result.cost.estimated_cost_usd

                    return result

                except Exception as e:
                    self._progress.failed += 1
                    return MicroAgentResult(
                        agent_type=MicroAgentType.VERIFIER,
                        status=MicroAgentStatus.FAILED,
                        error=str(e),
                    )
                finally:
                    self._progress.in_progress -= 1
                    self._update_progress()

        # Execute all with total timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    *[verify_with_semaphore(bead) for bead in beads],
                    return_exceptions=False if self.config.fail_fast else True,
                ),
                timeout=self.config.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error("Swarm execution timed out")
            return SwarmResult(
                status=SwarmStatus.PARTIAL,
                results=results,
                progress=self._progress,
                duration_seconds=time.time() - start_time,
                config=self.config,
            )

        # Handle exceptions in results
        processed_results: List[MicroAgentResult] = []
        for r in results:
            if isinstance(r, Exception):
                processed_results.append(MicroAgentResult(
                    agent_type=MicroAgentType.VERIFIER,
                    status=MicroAgentStatus.FAILED,
                    error=str(r),
                ))
            else:
                processed_results.append(r)

        # Determine final status
        all_success = all(r.is_success for r in processed_results)
        all_failed = all(not r.is_success for r in processed_results)

        if all_success:
            status = SwarmStatus.COMPLETED
        elif all_failed:
            status = SwarmStatus.FAILED
        else:
            status = SwarmStatus.PARTIAL

        return SwarmResult(
            status=status,
            results=processed_results,
            progress=self._progress,
            duration_seconds=time.time() - start_time,
            config=self.config,
        )

    async def generate_tests(
        self,
        beads: List[VulnerabilityBead],
    ) -> SwarmResult:
        """Generate tests for all beads in parallel.

        Args:
            beads: List of VulnerabilityBeads

        Returns:
            SwarmResult with test generation results
        """
        if not beads:
            return SwarmResult(
                status=SwarmStatus.COMPLETED,
                config=self.config,
            )

        start_time = time.time()

        self._progress = SwarmProgress(
            total=len(beads),
            pending=len(beads),
        )

        semaphore = asyncio.Semaphore(self.config.max_parallel)
        results: List[MicroAgentResult] = []

        async def generate_with_semaphore(bead: VulnerabilityBead) -> MicroAgentResult:
            async with semaphore:
                self._progress.pending -= 1
                self._progress.in_progress += 1
                self._update_progress()

                try:
                    agent = create_test_generator(
                        budget_usd=self.config.budget_per_agent_usd * 2,  # Test gen costs more
                        timeout_seconds=self.config.agent_timeout_seconds * 1.5,
                    )
                    result = await agent.execute(bead)

                    if result.is_success:
                        self._progress.completed += 1
                    else:
                        self._progress.failed += 1

                    self._progress.current_cost_usd += result.cost.estimated_cost_usd
                    return result

                except Exception as e:
                    self._progress.failed += 1
                    return MicroAgentResult(
                        agent_type=MicroAgentType.TEST_GENERATOR,
                        status=MicroAgentStatus.FAILED,
                        error=str(e),
                    )
                finally:
                    self._progress.in_progress -= 1
                    self._update_progress()

        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    *[generate_with_semaphore(bead) for bead in beads],
                    return_exceptions=True,
                ),
                timeout=self.config.timeout_seconds,
            )
        except asyncio.TimeoutError:
            return SwarmResult(
                status=SwarmStatus.PARTIAL,
                results=results,
                progress=self._progress,
                duration_seconds=time.time() - start_time,
                config=self.config,
            )

        processed_results = []
        for r in results:
            if isinstance(r, Exception):
                processed_results.append(MicroAgentResult(
                    agent_type=MicroAgentType.TEST_GENERATOR,
                    status=MicroAgentStatus.FAILED,
                    error=str(r),
                ))
            else:
                processed_results.append(r)

        all_success = all(r.is_success for r in processed_results)
        all_failed = all(not r.is_success for r in processed_results)

        status = (
            SwarmStatus.COMPLETED if all_success
            else SwarmStatus.FAILED if all_failed
            else SwarmStatus.PARTIAL
        )

        return SwarmResult(
            status=status,
            results=processed_results,
            progress=self._progress,
            duration_seconds=time.time() - start_time,
            config=self.config,
        )


# Convenience functions

async def swarm_verify(
    beads: List[VulnerabilityBead],
    parallel: int = 5,
    budget_per_agent: float = 0.50,
    timeout: int = 600,
) -> SwarmResult:
    """Verify multiple beads in parallel.

    Convenience function for simple parallel verification.

    Args:
        beads: List of VulnerabilityBeads
        parallel: Max concurrent agents
        budget_per_agent: Budget per agent in USD
        timeout: Total timeout in seconds

    Returns:
        SwarmResult with all results
    """
    config = SwarmConfig(
        max_parallel=parallel,
        budget_per_agent_usd=budget_per_agent,
        timeout_seconds=timeout,
    )
    manager = SwarmManager(config)
    return await manager.verify_all(beads)


async def swarm_generate_tests(
    beads: List[VulnerabilityBead],
    parallel: int = 3,  # Lower default - test gen is more intensive
    budget_per_agent: float = 1.00,
    timeout: int = 900,
) -> SwarmResult:
    """Generate tests for multiple beads in parallel.

    Args:
        beads: List of VulnerabilityBeads
        parallel: Max concurrent agents
        budget_per_agent: Budget per agent in USD
        timeout: Total timeout in seconds

    Returns:
        SwarmResult with test generation results
    """
    config = SwarmConfig(
        max_parallel=parallel,
        budget_per_agent_usd=budget_per_agent,
        timeout_seconds=timeout,
        agent_type=MicroAgentType.TEST_GENERATOR,
    )
    manager = SwarmManager(config)
    return await manager.generate_tests(beads)


def create_swarm_manager(
    max_parallel: int = 5,
    total_budget_usd: float = 10.00,
) -> SwarmManager:
    """Create a swarm manager with basic configuration.

    Args:
        max_parallel: Max concurrent agents
        total_budget_usd: Total budget

    Returns:
        Configured SwarmManager
    """
    config = SwarmConfig(
        max_parallel=max_parallel,
        total_budget_usd=total_budget_usd,
    )
    return SwarmManager(config)
