"""SubCoordinator - orchestrates parallel context-merge agents.

Per 05.5-CONTEXT.md:
- Spawns context-merge agents in parallel for each vuln class
- Respects max_parallel concurrency limit
- Ends after context-merge beads created (does not spawn vuln-discovery)
- Timeout per class prevents runaway tasks
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from alphaswarm_sol.agents.context.bead_factory import ContextBeadFactory
from alphaswarm_sol.agents.context.extractor import VulndocContextExtractor
from alphaswarm_sol.agents.context.merger import ContextMerger
from alphaswarm_sol.agents.context.verifier import ContextVerifier
from alphaswarm_sol.agents.orchestration.context_merge_agent import (
    ContextMergeAgent,
    ContextMergeConfig,
    ContextMergeResult,
)

if TYPE_CHECKING:
    from alphaswarm_sol.beads.context_merge import ContextMergeBead
    from alphaswarm_sol.context.schema import ProtocolContextPack


@dataclass
class SubCoordinatorConfig:
    """Configuration for SubCoordinator.

    Attributes:
        max_parallel: Maximum number of parallel context-merge agents (default 10)
        timeout_per_class_seconds: Timeout per vuln class in seconds (default 300)
        context_merge_config: Configuration for ContextMergeAgent
    """

    max_parallel: int = 10
    timeout_per_class_seconds: int = 300
    context_merge_config: ContextMergeConfig = field(default_factory=ContextMergeConfig)


@dataclass
class SubCoordinatorResult:
    """Result of SubCoordinator execution.

    Attributes:
        success: Whether all classes completed (even if some failed)
        beads_created: List of successfully created beads
        failed_classes: List of vuln classes that failed
        errors: Dict mapping vuln_class to error messages
        total_classes: Total number of classes processed
        successful_classes: Number of classes that succeeded
    """

    success: bool
    beads_created: List[ContextMergeBead]
    failed_classes: List[str]
    errors: Dict[str, List[str]] = field(default_factory=dict)
    total_classes: int = 0
    successful_classes: int = 0


class SubCoordinator:
    """Orchestrates parallel context-merge agents.

    The sub-coordinator spawns a ContextMergeAgent for each vulnerability
    class and manages parallel execution with concurrency limits and timeouts.

    After all context-merge beads are created, the sub-coordinator STOPS.
    It does NOT spawn vuln-discovery agents. That is handled by the parent
    orchestrator or next phase.

    Attributes:
        MODEL: Claude model to use for this agent
        ROLE: Agent role for tracking
        protocol_pack: Protocol context pack
        target_scope: List of contract files to analyze
        vuln_classes: List of vulnerability classes to process
        pool_id: Pool ID for bead association
        config: SubCoordinatorConfig instance
        vulndocs_root: Path to vulndocs root directory
    """

    MODEL = "claude-opus-4-5"
    ROLE = "SUPERVISOR"

    def __init__(
        self,
        protocol_pack: ProtocolContextPack,
        target_scope: List[str],
        vuln_classes: List[str],
        pool_id: str,
        config: Optional[SubCoordinatorConfig] = None,
        vulndocs_root: Optional[Path] = None,
    ):
        """Initialize SubCoordinator.

        Args:
            protocol_pack: Protocol context pack
            target_scope: List of contract files to analyze
            vuln_classes: List of vulnerability classes to process
            pool_id: Pool ID for bead association
            config: Optional configuration (uses defaults if None)
            vulndocs_root: Optional path to vulndocs root (default: ./vulndocs)
        """
        self.protocol_pack = protocol_pack
        self.target_scope = target_scope
        self.vuln_classes = vuln_classes
        self.pool_id = pool_id
        self.config = config or SubCoordinatorConfig()
        if vulndocs_root is not None:
            self.vulndocs_root = vulndocs_root
        else:
            from alphaswarm_sol.vulndocs.resolution import vulndocs_read_path_as_path
            self.vulndocs_root = vulndocs_read_path_as_path()

        # Initialize shared components
        self._extractor = VulndocContextExtractor(vulndocs_root=self.vulndocs_root)
        self._merger = ContextMerger(extractor=self._extractor)
        self._verifier = ContextVerifier()
        self._bead_factory = ContextBeadFactory()

        # Track created beads
        self._beads: List[ContextMergeBead] = []
        self._errors: Dict[str, List[str]] = {}

    async def run(self) -> SubCoordinatorResult:
        """Run parallel context-merge agents for all vuln classes.

        Returns:
            SubCoordinatorResult with beads and errors
        """
        total_classes = len(self.vuln_classes)
        if total_classes == 0:
            return SubCoordinatorResult(
                success=True,
                beads_created=[],
                failed_classes=[],
                errors={},
                total_classes=0,
                successful_classes=0,
            )

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.config.max_parallel)

        # Create tasks for all vuln classes
        tasks = [
            self._run_context_merge(vuln_class, semaphore)
            for vuln_class in self.vuln_classes
        ]

        # Run all tasks in parallel with exception handling
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_classes = 0
        failed_classes: List[str] = []

        for vuln_class, result in zip(self.vuln_classes, results):
            if isinstance(result, Exception):
                # Task raised an exception
                self._errors[vuln_class] = [str(result)]
                failed_classes.append(vuln_class)
            elif isinstance(result, ContextMergeResult):
                if result.success and result.bead:
                    self._beads.append(result.bead)
                    successful_classes += 1
                else:
                    self._errors[vuln_class] = result.errors
                    failed_classes.append(vuln_class)
            else:
                # Unexpected result type
                self._errors[vuln_class] = [f"Unexpected result type: {type(result)}"]
                failed_classes.append(vuln_class)

        return SubCoordinatorResult(
            success=len(failed_classes) == 0,
            beads_created=self._beads,
            failed_classes=failed_classes,
            errors=self._errors,
            total_classes=total_classes,
            successful_classes=successful_classes,
        )

    async def _run_context_merge(
        self,
        vuln_class: str,
        semaphore: asyncio.Semaphore,
    ) -> ContextMergeResult:
        """Run context-merge for a single vuln class.

        Args:
            vuln_class: Vulnerability class to process
            semaphore: Semaphore for concurrency control

        Returns:
            ContextMergeResult for this vuln class
        """
        async with semaphore:
            # Create agent for this vuln class
            agent = ContextMergeAgent(
                merger=self._merger,
                verifier=self._verifier,
                bead_factory=self._bead_factory,
                config=self.config.context_merge_config,
            )

            # Run with timeout
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        agent.execute,
                        vuln_class=vuln_class,
                        protocol_pack=self.protocol_pack,
                        target_scope=self.target_scope,
                        pool_id=self.pool_id,
                    ),
                    timeout=self.config.timeout_per_class_seconds,
                )
                return result

            except asyncio.TimeoutError:
                return ContextMergeResult(
                    success=False,
                    bead=None,
                    vuln_class=vuln_class,
                    attempts=0,
                    errors=[
                        f"Timeout after {self.config.timeout_per_class_seconds}s"
                    ],
                    final_quality_score=0.0,
                )

    def get_pending_beads(self) -> List[ContextMergeBead]:
        """Get all pending context-merge beads.

        Returns:
            List of beads with status PENDING
        """
        from alphaswarm_sol.beads.context_merge import ContextBeadStatus

        return [
            bead
            for bead in self._beads
            if bead.status == ContextBeadStatus.PENDING
        ]

    def get_beads_by_status(self, status: str) -> List[ContextMergeBead]:
        """Get beads filtered by status.

        Args:
            status: Status to filter by (pending, in_progress, complete, failed)

        Returns:
            List of beads with matching status
        """
        from alphaswarm_sol.beads.context_merge import ContextBeadStatus

        try:
            status_enum = ContextBeadStatus(status)
            return [bead for bead in self._beads if bead.status == status_enum]
        except ValueError:
            return []
