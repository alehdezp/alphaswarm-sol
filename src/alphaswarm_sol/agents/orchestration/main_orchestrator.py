"""MainOrchestrator - top-level orchestration for context-merge -> vuln-discovery.

Per 05.5-CONTEXT.md:
- Uses Opus 4.5 (complex coordination decisions)
- Delegates ALL work to subagents - never performs tasks directly
- Flow: sub-coordinator (context-merge) -> vuln-discovery agents
- Sub-coordinator ends after beads created, main orchestrator spawns vuln-discovery

Per 05.10-09 (Creative Discovery Integration):
- Optional Tier-B creative discovery stage between context-merge and vuln-discovery
- Creative loop includes: near-miss mining, pattern mutation, counterfactual probes
- All creative outputs remain Tier-B with strict evidence gates
- Budget-checked before execution

Usage:
    from alphaswarm_sol.agents.orchestration import (
        MainOrchestrator,
        OrchestrationConfig,
        OrchestrationResult,
    )
    from alphaswarm_sol.context.schema import ProtocolContextPack

    # Configure orchestrator
    config = OrchestrationConfig(
        max_parallel_discovery=5,
        timeout_per_discovery_seconds=600,
        enable_creative_discovery=True,  # Optional Tier-B stage
        creative_discovery_budget=1500,
    )

    # Create orchestrator
    orchestrator = MainOrchestrator(
        protocol_pack=protocol_pack,
        target_scope=["contracts/"],
        vuln_classes=["reentrancy/classic", "access-control/missing-auth"],
        pool_id="audit-2026-01",
        config=config,
    )

    # Run full flow
    result = await orchestrator.run()
    print(f"Findings: {result.total_findings}")

    # Or run discovery only (skip context-merge)
    result = await orchestrator.run_discovery_only(["CTX-abc123"])
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from alphaswarm_sol.agents.context.bead_factory import ContextBeadFactory
from alphaswarm_sol.agents.orchestration.finding_factory import FindingBeadFactory
from alphaswarm_sol.agents.orchestration.sub_coordinator import (
    SubCoordinator,
    SubCoordinatorConfig,
)
from alphaswarm_sol.agents.orchestration.vuln_discovery_agent import (
    VulnDiscoveryAgent,
    VulnDiscoveryConfig,
    VulnDiscoveryResult,
)
from alphaswarm_sol.agents.runtime.base import AgentRole
from alphaswarm_sol.beads.context_merge import ContextMergeBead
from alphaswarm_sol.orchestration.creative import (
    CreativeDiscoveryLoop,
    CreativeDiscoveryConfig,
    CreativeDiscoveryResult,
)

if TYPE_CHECKING:
    from alphaswarm_sol.beads.schema import VulnerabilityBead
    from alphaswarm_sol.context.schema import ProtocolContextPack

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationConfig:
    """Configuration for main orchestrator.

    Attributes:
        max_parallel_discovery: Max vuln-discovery agents to run in parallel
        timeout_per_discovery_seconds: Timeout for each discovery agent
        sub_coordinator_config: Configuration for SubCoordinator
        vuln_discovery_config: Configuration for VulnDiscoveryAgent
        enable_creative_discovery: Whether to run optional Tier-B creative discovery
        creative_discovery_budget: Token budget for creative discovery stage
        creative_discovery_config: Configuration for CreativeDiscoveryLoop
    """

    max_parallel_discovery: int = 5
    timeout_per_discovery_seconds: int = 600
    sub_coordinator_config: SubCoordinatorConfig = field(
        default_factory=SubCoordinatorConfig
    )
    vuln_discovery_config: VulnDiscoveryConfig = field(
        default_factory=VulnDiscoveryConfig
    )
    # Creative discovery settings (05.10-09)
    enable_creative_discovery: bool = False  # Disabled by default
    creative_discovery_budget: int = 1500  # Token budget for creative loop
    creative_discovery_config: CreativeDiscoveryConfig = field(
        default_factory=CreativeDiscoveryConfig
    )


@dataclass
class OrchestrationResult:
    """Result of main orchestration.

    Attributes:
        success: Whether orchestration completed without critical failures
        phase: Last phase reached (context_merge, vuln_discovery, complete)
        context_beads_created: Number of context beads successfully created
        context_beads_failed: Number of context beads that failed
        findings_created: Total number of finding beads created
        discovery_completed: Number of discoveries that succeeded
        discovery_failed: Number of discoveries that failed
        findings: List of finding beads created
        errors: Dict mapping phase name to list of error messages
        creative_discovery_result: Optional creative discovery results (Tier-B)
    """

    success: bool
    phase: str  # "context_merge", "creative_discovery", "vuln_discovery", "complete"

    # Context-merge phase results
    context_beads_created: int
    context_beads_failed: int

    # Vuln-discovery phase results
    findings_created: int
    discovery_completed: int
    discovery_failed: int

    # Details
    findings: List[VulnerabilityBead]
    errors: Dict[str, List[str]]

    # Creative discovery results (05.10-09)
    creative_discovery_result: Optional[CreativeDiscoveryResult] = None

    @property
    def total_findings(self) -> int:
        """Get total number of findings.

        Returns:
            Number of findings created
        """
        return len(self.findings)

    @property
    def creative_hypotheses_count(self) -> int:
        """Get count of creative discovery hypotheses (Tier-B).

        Returns:
            Number of creative hypotheses generated
        """
        if self.creative_discovery_result:
            return len(self.creative_discovery_result.hypotheses)
        return 0


class MainOrchestrator:
    """Top-level orchestrator for context-merge and vuln-discovery flow.

    Per 05.5-CONTEXT.md decisions:
    - Orchestrator delegates ALL work to subagents
    - Sub-coordinator handles parallel context-merge
    - Main orchestrator spawns vuln-discovery from context beads
    - Model: Opus 4.5 (complex coordination decisions)

    Flow:
    1. Receive protocol pack + vuln classes to test
    2. Delegate to SubCoordinator for parallel context-merge
    3. Collect context-merge beads from sub-coordinator
    4. Spawn VulnDiscoveryAgents for each context bead
    5. Collect findings from all discovery agents
    6. Return aggregated results

    Attributes:
        MODEL: Claude model to use for this orchestrator
        ROLE: Agent role for tracking
        protocol_pack: Protocol context pack with economic/security context
        target_scope: List of contract files in scope
        vuln_classes: List of vulnerability classes to test
        pool_id: Pool ID for organizing beads
        config: OrchestrationConfig instance
        graph_path: Optional path to pre-built knowledge graph
        context_bead_factory: Factory for loading/saving context beads
        finding_factory: Factory for creating finding beads

    Usage:
        orchestrator = MainOrchestrator(
            protocol_pack=protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=["reentrancy/classic", "access-control/missing-auth"],
            pool_id="audit-2026-01",
        )
        result = await orchestrator.run()
    """

    # Model assignment per 05.5-CONTEXT.md
    MODEL = "claude-opus-4-5"
    ROLE = AgentRole.SUPERVISOR

    def __init__(
        self,
        protocol_pack: ProtocolContextPack,
        target_scope: List[str],
        vuln_classes: List[str],
        pool_id: Optional[str] = None,
        config: Optional[OrchestrationConfig] = None,
        graph_path: Optional[Path] = None,
        beads_dir: Optional[Path] = None,
    ):
        """Initialize MainOrchestrator.

        Args:
            protocol_pack: Protocol context pack with economic/security context
            target_scope: List of contract files in scope
            vuln_classes: List of vulnerability classes to test
            pool_id: Pool ID for organizing beads
            config: Optional configuration (uses defaults if None)
            graph_path: Optional path to pre-built knowledge graph
            beads_dir: Optional base directory for beads storage
        """
        self.protocol_pack = protocol_pack
        self.target_scope = target_scope
        self.vuln_classes = vuln_classes
        self.pool_id = pool_id
        self.config = config or OrchestrationConfig()
        self.graph_path = graph_path

        # Initialize factories
        self.context_bead_factory = ContextBeadFactory(
            beads_dir=beads_dir or Path(".vrs/beads")
        )
        self.finding_factory = FindingBeadFactory(
            beads_dir=beads_dir or Path(".vrs/beads")
        )

    async def run(self) -> OrchestrationResult:
        """Run full orchestration: context-merge -> vuln-discovery.

        Executes the complete orchestration flow:
        1. Delegate to SubCoordinator for parallel context-merge
        2. Spawn VulnDiscoveryAgents for each context bead
        3. Collect and aggregate all findings

        Returns:
            OrchestrationResult with all findings and errors
        """
        logger.info(f"Starting orchestration for {len(self.vuln_classes)} vuln classes")
        errors: Dict[str, List[str]] = {}
        all_findings: List[VulnerabilityBead] = []

        # Phase 1: Context-merge via sub-coordinator
        logger.info("Phase 1: Delegating to sub-coordinator for context-merge")
        sub_coordinator = SubCoordinator(
            protocol_pack=self.protocol_pack,
            target_scope=self.target_scope,
            vuln_classes=self.vuln_classes,
            pool_id=self.pool_id,
            config=self.config.sub_coordinator_config,
        )

        context_result = await sub_coordinator.run()

        if context_result.errors:
            errors["context_merge"] = []
            for vuln_class, class_errors in context_result.errors.items():
                errors["context_merge"].extend(
                    [f"{vuln_class}: {e}" for e in class_errors]
                )

        if not context_result.beads_created:
            logger.error("No context-merge beads created, aborting")
            return OrchestrationResult(
                success=False,
                phase="context_merge",
                context_beads_created=0,
                context_beads_failed=context_result.total_classes,
                findings_created=0,
                discovery_completed=0,
                discovery_failed=0,
                findings=[],
                errors=errors,
            )

        logger.info(f"Context-merge complete: {len(context_result.beads_created)} beads")

        # Phase 2: Vuln-discovery for each context bead
        logger.info("Phase 2: Spawning vuln-discovery agents")
        discovery_results = await self._run_vuln_discovery(context_result.beads_created)

        discovery_completed = 0
        discovery_failed = 0

        for context_bead_id, result in discovery_results.items():
            if result.success:
                discovery_completed += 1
                all_findings.extend(result.findings)
            else:
                discovery_failed += 1
                if "vuln_discovery" not in errors:
                    errors["vuln_discovery"] = []
                errors["vuln_discovery"].extend(
                    [f"{context_bead_id}: {e}" for e in result.errors]
                )

        logger.info(
            f"Orchestration complete: {len(all_findings)} findings "
            f"from {discovery_completed} discoveries"
        )

        return OrchestrationResult(
            success=discovery_failed == 0 and context_result.successful_classes > 0,
            phase="complete",
            context_beads_created=len(context_result.beads_created),
            context_beads_failed=len(context_result.failed_classes),
            findings_created=len(all_findings),
            discovery_completed=discovery_completed,
            discovery_failed=discovery_failed,
            findings=all_findings,
            errors=errors,
        )

    async def _run_vuln_discovery(
        self,
        context_beads: List[ContextMergeBead],
    ) -> Dict[str, VulnDiscoveryResult]:
        """Run vuln-discovery for all context beads in parallel.

        Uses a semaphore to limit concurrent discovery agents per
        config.max_parallel_discovery.

        Args:
            context_beads: List of verified context-merge beads

        Returns:
            Dict mapping context_bead_id to VulnDiscoveryResult
        """
        semaphore = asyncio.Semaphore(self.config.max_parallel_discovery)

        async def run_single(bead: ContextMergeBead) -> tuple[str, VulnDiscoveryResult]:
            async with semaphore:
                logger.info(f"Starting vuln-discovery for {bead.id}")

                # Configure discovery agent
                discovery_config = VulnDiscoveryConfig(
                    max_findings_per_context=self.config.vuln_discovery_config.max_findings_per_context,
                    min_confidence_to_report=self.config.vuln_discovery_config.min_confidence_to_report,
                    graph_path=self.graph_path,
                )

                agent = VulnDiscoveryAgent(
                    finding_factory=self.finding_factory,
                    config=discovery_config,
                )

                # Run in thread pool with timeout
                try:
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, agent.execute, bead, None),
                        timeout=self.config.timeout_per_discovery_seconds,
                    )
                    return bead.id, result

                except asyncio.TimeoutError:
                    return bead.id, VulnDiscoveryResult(
                        success=False,
                        context_bead_id=bead.id,
                        findings=[],
                        findings_count=0,
                        errors=[
                            f"Timeout after {self.config.timeout_per_discovery_seconds}s"
                        ],
                        vql_queries_executed=[],
                    )

        tasks = [run_single(bead) for bead in context_beads]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        discovery_results: Dict[str, VulnDiscoveryResult] = {}
        for i, result in enumerate(results):
            bead_id = context_beads[i].id
            if isinstance(result, Exception):
                discovery_results[bead_id] = VulnDiscoveryResult(
                    success=False,
                    context_bead_id=bead_id,
                    findings=[],
                    findings_count=0,
                    errors=[str(result)],
                    vql_queries_executed=[],
                )
            else:
                discovery_results[result[0]] = result[1]

        return discovery_results

    async def run_discovery_only(
        self,
        context_bead_ids: Optional[List[str]] = None,
    ) -> OrchestrationResult:
        """Run only vuln-discovery phase (skip context-merge).

        Useful when context beads already exist from a previous run.

        Args:
            context_bead_ids: Specific bead IDs to process, or None for all pending

        Returns:
            OrchestrationResult with findings
        """
        # Load existing context beads
        if context_bead_ids:
            beads = []
            for bead_id in context_bead_ids:
                try:
                    bead = self.context_bead_factory.load_bead(bead_id, self.pool_id)
                    beads.append(bead)
                except FileNotFoundError:
                    logger.warning(f"Bead not found: {bead_id}")
        else:
            beads = self.context_bead_factory.list_pending_beads(self.pool_id)

        if not beads:
            return OrchestrationResult(
                success=True,
                phase="complete",
                context_beads_created=0,
                context_beads_failed=0,
                findings_created=0,
                discovery_completed=0,
                discovery_failed=0,
                findings=[],
                errors={},
            )

        discovery_results = await self._run_vuln_discovery(beads)

        all_findings: List[VulnerabilityBead] = []
        discovery_completed = 0
        discovery_failed = 0
        errors: Dict[str, List[str]] = {}

        for bead_id, result in discovery_results.items():
            if result.success:
                discovery_completed += 1
                all_findings.extend(result.findings)
            else:
                discovery_failed += 1
                if "vuln_discovery" not in errors:
                    errors["vuln_discovery"] = []
                errors["vuln_discovery"].extend(result.errors)

        return OrchestrationResult(
            success=discovery_failed == 0,
            phase="complete",
            context_beads_created=len(beads),
            context_beads_failed=0,
            findings_created=len(all_findings),
            discovery_completed=discovery_completed,
            discovery_failed=discovery_failed,
            findings=all_findings,
            errors=errors,
        )

    def run_creative_discovery(
        self,
        nodes: Dict[str, Dict],
        pattern_required_ops: Dict[str, List[str]],
        pattern_orderings: Optional[Dict[str, List[tuple]]] = None,
        pcp_counterfactuals: Optional[List[Dict]] = None,
        pcp_anti_signals: Optional[List[Dict]] = None,
        guarded_nodes: Optional[Dict[str, List[str]]] = None,
    ) -> Optional[CreativeDiscoveryResult]:
        """Run optional Tier-B creative discovery stage.

        Per 05.10-09:
        - Creative loop outputs remain Tier-B
        - Near-miss, mutation, counterfactual probes are deterministic
        - All outputs marked unknown unless evidenced
        - Budget-checked before execution

        This method is called between context-merge and vuln-discovery
        when enable_creative_discovery is True.

        Args:
            nodes: Graph nodes as dict (node_id -> node data)
            pattern_required_ops: Pattern ID -> required operations
            pattern_orderings: Pattern ID -> ordering constraints
            pcp_counterfactuals: PCP counterfactuals for probing
            pcp_anti_signals: PCP anti-signals
            guarded_nodes: Node ID -> guard types present

        Returns:
            CreativeDiscoveryResult or None if disabled
        """
        if not self.config.enable_creative_discovery:
            logger.debug("Creative discovery disabled, skipping")
            return None

        # Budget check before execution
        budget = self.config.creative_discovery_budget
        if budget <= 0:
            logger.warning("Creative discovery budget exhausted, skipping")
            return None

        logger.info(f"Running creative discovery with budget {budget}")

        # Initialize creative discovery loop
        creative_loop = CreativeDiscoveryLoop(
            config=self.config.creative_discovery_config
        )

        # Run creative discovery
        result = creative_loop.discover(
            nodes=nodes,
            pattern_required_ops=pattern_required_ops,
            pattern_orderings=pattern_orderings or {},
            pcp_counterfactuals=pcp_counterfactuals,
            pcp_anti_signals=pcp_anti_signals,
            guarded_nodes=guarded_nodes,
            budget_remaining=budget,
        )

        logger.info(
            f"Creative discovery complete: "
            f"{len(result.near_misses)} near-misses, "
            f"{len(result.mutations)} mutations, "
            f"{len(result.counterfactuals)} counterfactuals, "
            f"{len(result.hypotheses)} hypotheses"
        )

        return result
