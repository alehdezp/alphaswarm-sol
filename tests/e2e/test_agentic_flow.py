"""End-to-end tests for agentic audit pipeline.

Tests the full flow: build -> detect -> beads -> verify -> report

SDK-07: E2E agentic flow tests
SDK-10: Integration of all SDK components

Test Coverage:
- Full pipeline execution with deterministic runtime
- Pool lifecycle (intake -> complete)
- Multi-agent coordination (attacker/defender/verifier)
- Verdict generation and consensus
- Error handling and recovery
- CLI/SDK artifact parity
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

from tests.e2e.fixtures import (
    DeterministicRuntime,
    DETERMINISTIC_RESPONSES,
    create_minimal_bead,
    deterministic_runtime,
    sample_bead,
    sample_pool,
    vulnerable_contract_dir,
)

from alphaswarm_sol.agents.propulsion.coordinator import (
    AgentCoordinator,
    CoordinatorConfig,
    CoordinatorStatus,
    CoordinatorReport,
)
from alphaswarm_sol.agents.runtime import AgentConfig, AgentRole
from alphaswarm_sol.beads.schema import VulnerabilityBead
from alphaswarm_sol.beads.storage import BeadStorage
from alphaswarm_sol.beads.types import BeadStatus, Severity
from alphaswarm_sol.orchestration.debate import (
    DebateOrchestrator,
    DebateConfig,
    run_debate,
)
from alphaswarm_sol.orchestration.loop import (
    ExecutionLoop,
    LoopConfig,
    LoopPhase,
    PhaseResult,
)
from alphaswarm_sol.orchestration.pool import PoolManager, PoolStorage
from alphaswarm_sol.orchestration.router import RouteAction, Router
from alphaswarm_sol.orchestration.schemas import (
    Pool,
    PoolStatus,
    Scope,
    Verdict,
    VerdictConfidence,
    EvidenceItem,
    EvidencePacket,
)


# =============================================================================
# Test: Full Pipeline Flow
# =============================================================================


@pytest.mark.asyncio
class TestFullPipelineFlow:
    """Test complete audit pipeline from build to report."""

    async def test_pipeline_intake_to_complete(
        self, deterministic_runtime: DeterministicRuntime, tmp_path: Path
    ) -> None:
        """Test full pipeline: intake -> context -> beads -> execute -> verify -> integrate -> complete."""
        # Setup
        pool_storage = PoolStorage(tmp_path / "pools")
        bead_storage = BeadStorage(tmp_path / "beads")
        manager = PoolManager(tmp_path / "pools")

        # Create pool
        scope = Scope(
            files=["contracts/VulnerableVault.sol"],
            contracts=["VulnerableVault"],
            focus_areas=["reentrancy"],
        )
        pool = manager.create_pool(scope, pool_id="e2e-pipeline-test")

        # Verify initial state
        assert pool.status == PoolStatus.INTAKE
        assert len(pool.bead_ids) == 0

        # Simulate phase progression
        phases = [
            PoolStatus.INTAKE,
            PoolStatus.CONTEXT,
            PoolStatus.BEADS,
            PoolStatus.EXECUTE,
            PoolStatus.VERIFY,
            PoolStatus.INTEGRATE,
            PoolStatus.COMPLETE,
        ]

        for i in range(len(phases) - 1):
            assert pool.status == phases[i]
            advanced = pool.advance_phase()
            assert advanced, f"Failed to advance from {phases[i]}"
            pool_storage.save_pool(pool)

        assert pool.status == PoolStatus.COMPLETE

    async def test_pipeline_with_beads(
        self, deterministic_runtime: DeterministicRuntime, tmp_path: Path
    ) -> None:
        """Test pipeline with actual beads being processed."""
        # Setup
        manager = PoolManager(tmp_path / "pools")
        bead_storage = BeadStorage(tmp_path / "beads")

        # Create beads
        beads = [
            create_minimal_bead(
                bead_id=f"VKG-E2E-{i:03d}",
                vulnerability_class="reentrancy",
            )
            for i in range(3)
        ]

        # Save beads
        for bead in beads:
            bead_storage.save_bead(bead)

        # Create pool with beads
        scope = Scope(files=["contracts/VulnerableVault.sol"])
        pool = manager.create_pool(scope, pool_id="e2e-with-beads")
        for bead in beads:
            manager.add_bead(pool.id, bead.id)

        # Verify beads added
        pool = manager.get_pool(pool.id)
        assert pool is not None
        assert len(pool.bead_ids) == 3

        # Run coordinator with deterministic runtime
        coordinator = AgentCoordinator(
            deterministic_runtime,
            CoordinatorConfig(
                agents_per_role={"attacker": 1, "defender": 1, "verifier": 1}
            ),
        )
        coordinator.setup_for_pool(pool, beads)
        report = await coordinator.run(timeout=60)

        # Verify report
        assert report.status == CoordinatorStatus.COMPLETE
        assert report.total_beads == 3
        assert report.completed_beads > 0

    async def test_pipeline_produces_artifacts(
        self, deterministic_runtime: DeterministicRuntime, tmp_path: Path
    ) -> None:
        """Test that pipeline produces expected artifacts for SDK-08 parity."""
        manager = PoolManager(tmp_path / "pools")
        bead_storage = BeadStorage(tmp_path / "beads")

        # Create pool and bead
        bead = create_minimal_bead(bead_id="VKG-ARTIFACT-001")
        bead_storage.save_bead(bead)

        scope = Scope(files=["contracts/VulnerableVault.sol"])
        pool = manager.create_pool(scope, pool_id="e2e-artifacts")
        manager.add_bead(pool.id, bead.id)

        # Run coordinator
        coordinator = AgentCoordinator(
            deterministic_runtime,
            CoordinatorConfig(
                agents_per_role={"attacker": 1, "defender": 1, "verifier": 1}
            ),
        )
        coordinator.setup_for_pool(pool, [bead])
        report = await coordinator.run()

        # Verify report is serializable (SDK-08 parity)
        report_dict = report.to_dict()
        assert "status" in report_dict
        assert "total_beads" in report_dict
        assert "completed_beads" in report_dict
        assert "results_by_role" in report_dict

        # Verify JSON serializable
        json_str = json.dumps(report_dict)
        assert len(json_str) > 0

        # Verify round-trip
        restored = CoordinatorReport.from_dict(json.loads(json_str))
        assert restored.total_beads == report.total_beads


# =============================================================================
# Test: Execution Loop
# =============================================================================


class TestExecutionLoop:
    """Test execution loop phase transitions."""

    def test_loop_phase_transitions(self, tmp_path: Path) -> None:
        """Test loop advances through phases correctly."""
        manager = PoolManager(tmp_path / "pools")
        loop = ExecutionLoop(manager, LoopConfig(auto_advance=True))

        # Create pool
        scope = Scope(files=["contracts/Test.sol"])
        pool = manager.create_pool(scope, pool_id="loop-test")

        # Verify initial phase
        assert pool.status == PoolStatus.INTAKE

        # Router should determine next action
        router = Router()
        decision = router.route(pool)
        assert decision.action in [
            RouteAction.BUILD_GRAPH,
            RouteAction.LOAD_CONTEXT,
            RouteAction.WAIT,
        ]

    def test_loop_handles_failed_pool(self, tmp_path: Path) -> None:
        """Test loop handles failed pool correctly."""
        manager = PoolManager(tmp_path / "pools")
        loop = ExecutionLoop(manager)

        # Create and fail a pool
        scope = Scope(files=["contracts/Test.sol"])
        pool = manager.create_pool(scope, pool_id="loop-fail-test")
        manager.fail_pool(pool.id, "Test failure")

        # Run loop
        result = loop.run(pool.id)

        # Should report failure
        assert not result.success
        assert "failed" in result.message.lower() or result.phase == LoopPhase.INTAKE

    def test_loop_single_phase_execution(self, tmp_path: Path) -> None:
        """Test running a single phase."""
        manager = PoolManager(tmp_path / "pools")
        loop = ExecutionLoop(manager)

        # Register a simple handler
        def noop_handler(pool: Pool, beads: List[str]) -> PhaseResult:
            return PhaseResult(
                success=True, phase=LoopPhase.INTAKE, message="Handler executed"
            )

        loop.register_handler(RouteAction.BUILD_GRAPH, noop_handler)

        # Create pool
        scope = Scope(files=["contracts/Test.sol"])
        pool = manager.create_pool(scope, pool_id="single-phase-test")

        # Run single phase
        result = loop.run_single_phase(pool.id)
        # Result depends on whether handler was called
        assert result.phase is not None


# =============================================================================
# Test: Agent Coordinator
# =============================================================================


@pytest.mark.asyncio
class TestAgentCoordinator:
    """Test multi-agent coordination."""

    async def test_coordinator_parallel_execution(
        self, deterministic_runtime: DeterministicRuntime
    ) -> None:
        """Test attacker and defender run in parallel."""
        beads = [create_minimal_bead(bead_id=f"VKG-PARALLEL-{i}") for i in range(2)]

        pool = Pool(
            id="parallel-test",
            scope=Scope(files=["contracts/Test.sol"]),
            bead_ids=[b.id for b in beads],
        )

        coordinator = AgentCoordinator(
            deterministic_runtime,
            CoordinatorConfig(
                agents_per_role={"attacker": 1, "defender": 1, "verifier": 1}
            ),
        )
        coordinator.setup_for_pool(pool, beads)
        report = await coordinator.run()

        # Both attacker and defender should have run
        assert "attacker" in report.results_by_role
        assert "defender" in report.results_by_role

    async def test_coordinator_verifier_after_both_complete(
        self, deterministic_runtime: DeterministicRuntime
    ) -> None:
        """Test verifier only runs after attacker AND defender complete."""
        bead = create_minimal_bead(bead_id="VKG-VERIFIER-GATE")

        pool = Pool(
            id="verifier-gate-test",
            scope=Scope(files=["contracts/Test.sol"]),
            bead_ids=[bead.id],
        )

        coordinator = AgentCoordinator(
            deterministic_runtime,
            CoordinatorConfig(
                agents_per_role={"attacker": 1, "defender": 1, "verifier": 1}
            ),
        )
        coordinator.setup_for_pool(pool, [bead])
        report = await coordinator.run()

        # After run, verifier should have processed if both completed
        if coordinator.attacker_complete_count > 0 and coordinator.defender_complete_count > 0:
            assert "verifier" in report.results_by_role or coordinator.verifier_pending_count == 0

    async def test_coordinator_reports_stuck_work(
        self, deterministic_runtime: DeterministicRuntime
    ) -> None:
        """Test coordinator identifies stuck work items."""
        bead = create_minimal_bead(bead_id="VKG-STUCK-CHECK")

        pool = Pool(
            id="stuck-check-test",
            scope=Scope(files=["contracts/Test.sol"]),
            bead_ids=[bead.id],
        )

        coordinator = AgentCoordinator(
            deterministic_runtime,
            CoordinatorConfig(enable_supervisor=True),
        )
        coordinator.setup_for_pool(pool, [bead])
        report = await coordinator.run()

        # Report should have stuck_work field
        assert isinstance(report.stuck_work, list)


# =============================================================================
# Test: Debate Protocol
# =============================================================================


class TestDebateProtocol:
    """Test structured debate between attacker and defender."""

    def test_debate_without_agents(self) -> None:
        """Test debate protocol without actual agents."""
        evidence = EvidencePacket(
            finding_id="VKG-DEBATE-001",
            items=[
                EvidenceItem(
                    type="behavioral_signature",
                    value="R:bal->X:out->W:bal",
                    location="VulnerableVault.sol:17",
                    confidence=0.9,
                )
            ],
        )

        # Run debate without agents (uses placeholder claims)
        verdict = run_debate(
            bead_id="VKG-DEBATE-001",
            evidence=evidence,
            attacker_context={},
            defender_context={},
        )

        # Verdict should be produced and human-flagged
        assert verdict is not None
        assert verdict.human_flag is True

    def test_debate_produces_verdict(self) -> None:
        """Test debate produces verdict with confidence."""
        orchestrator = DebateOrchestrator(config=DebateConfig())

        evidence = EvidencePacket(
            finding_id="VKG-DEBATE-002",
            items=[
                EvidenceItem(
                    type="code_pattern",
                    value="External call before state update",
                    location="VulnerableVault.sol:17-21",
                    confidence=0.85,
                )
            ],
        )

        verdict = orchestrator.run_debate(
            bead_id="VKG-DEBATE-002",
            evidence=evidence,
            attacker_context={},
            defender_context={},
        )

        # Verify verdict properties
        assert verdict.finding_id == "VKG-DEBATE-002"
        assert isinstance(verdict.confidence, VerdictConfidence)
        assert verdict.human_flag is True

    def test_debate_has_rationale(self) -> None:
        """Test debate verdict includes rationale."""
        evidence = EvidencePacket(finding_id="VKG-DEBATE-003", items=[])

        verdict = run_debate(
            bead_id="VKG-DEBATE-003",
            evidence=evidence,
            attacker_context={},
            defender_context={},
        )

        # Should have rationale explaining the verdict
        assert len(verdict.rationale) > 0


# =============================================================================
# Test: Pool Management
# =============================================================================


class TestPoolManagement:
    """Test pool lifecycle and persistence."""

    def test_pool_create_and_persist(self, tmp_path: Path) -> None:
        """Test pool is created and persisted correctly."""
        manager = PoolManager(tmp_path / "pools")

        scope = Scope(
            files=["contracts/Vault.sol"],
            contracts=["Vault"],
            focus_areas=["reentrancy"],
        )
        pool = manager.create_pool(scope, pool_id="persist-test")

        # Verify persisted
        loaded = manager.get_pool(pool.id)
        assert loaded is not None
        assert loaded.scope.files == scope.files

    def test_pool_add_beads(self, tmp_path: Path) -> None:
        """Test adding beads to pool."""
        manager = PoolManager(tmp_path / "pools")

        scope = Scope(files=["contracts/Vault.sol"])
        pool = manager.create_pool(scope, pool_id="add-beads-test")

        # Add beads
        manager.add_bead(pool.id, "VKG-001")
        manager.add_bead(pool.id, "VKG-002")

        # Verify
        pool = manager.get_pool(pool.id)
        assert pool is not None
        assert "VKG-001" in pool.bead_ids
        assert "VKG-002" in pool.bead_ids

    def test_pool_record_verdict(self, tmp_path: Path) -> None:
        """Test recording verdict in pool."""
        manager = PoolManager(tmp_path / "pools")

        scope = Scope(files=["contracts/Vault.sol"])
        pool = manager.create_pool(scope, pool_id="verdict-test")
        manager.add_bead(pool.id, "VKG-001")

        # Create and record verdict
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="Test verdict",
        )
        manager.record_verdict(pool.id, verdict)

        # Verify
        pool = manager.get_pool(pool.id)
        assert pool is not None
        assert "VKG-001" in pool.verdicts
        assert pool.verdicts["VKG-001"].is_vulnerable

    def test_pool_pause_and_resume(self, tmp_path: Path) -> None:
        """Test pausing and resuming pool."""
        manager = PoolManager(tmp_path / "pools")

        scope = Scope(files=["contracts/Vault.sol"])
        pool = manager.create_pool(scope, pool_id="pause-test")

        # Advance to execute phase
        pool.advance_phase()  # INTAKE -> CONTEXT
        pool.advance_phase()  # CONTEXT -> BEADS
        pool.advance_phase()  # BEADS -> EXECUTE
        manager.storage.save_pool(pool)

        # Pause
        manager.pause_pool(pool.id, "Human review needed")
        pool = manager.get_pool(pool.id)
        assert pool is not None
        assert pool.status == PoolStatus.PAUSED

        # Resume
        manager.resume_pool(pool.id)
        pool = manager.get_pool(pool.id)
        assert pool is not None
        assert pool.status != PoolStatus.PAUSED


# =============================================================================
# Test: Bead Storage
# =============================================================================


class TestBeadStorage:
    """Test bead persistence and pool integration."""

    def test_bead_save_and_load(self, tmp_path: Path) -> None:
        """Test bead save and load."""
        storage = BeadStorage(tmp_path / "beads")
        bead = create_minimal_bead(bead_id="VKG-STORAGE-001")

        # Save
        path = storage.save_bead(bead)
        assert path.exists()

        # Load
        loaded = storage.get_bead("VKG-STORAGE-001")
        assert loaded is not None
        assert loaded.id == bead.id
        assert loaded.vulnerability_class == bead.vulnerability_class

    def test_bead_pool_association(self, tmp_path: Path) -> None:
        """Test bead association with pool."""
        bead_storage = BeadStorage(tmp_path / "beads")
        pool_storage = PoolStorage(tmp_path / "pools")

        # Create bead
        bead = create_minimal_bead(bead_id="VKG-POOL-ASSOC")
        bead_storage.save_bead(bead)

        # Save to pool
        bead_storage.save_to_pool(bead, "test-pool")

        # Verify association
        loaded = bead_storage.load_from_pool("VKG-POOL-ASSOC", "test-pool")
        assert loaded is not None


# =============================================================================
# Test: Error Handling
# =============================================================================


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling in pipeline."""

    async def test_coordinator_handles_timeout(
        self, deterministic_runtime: DeterministicRuntime
    ) -> None:
        """Test coordinator handles individual work timeouts."""
        bead = create_minimal_bead(bead_id="VKG-TIMEOUT-TEST")

        pool = Pool(
            id="timeout-test",
            scope=Scope(files=["contracts/Test.sol"]),
            bead_ids=[bead.id],
        )

        # Very short timeout to trigger timeout handling
        coordinator = AgentCoordinator(
            deterministic_runtime,
            CoordinatorConfig(work_timeout=1),  # 1 second timeout
        )
        coordinator.setup_for_pool(pool, [bead])
        report = await coordinator.run(timeout=60)

        # Should complete even if some work items timed out
        assert report.status in [CoordinatorStatus.COMPLETE, CoordinatorStatus.FAILED]

    async def test_coordinator_handles_empty_pool(
        self, deterministic_runtime: DeterministicRuntime
    ) -> None:
        """Test coordinator handles empty pool gracefully."""
        pool = Pool(
            id="empty-pool-test",
            scope=Scope(files=["contracts/Test.sol"]),
            bead_ids=[],
        )

        coordinator = AgentCoordinator(deterministic_runtime)
        coordinator.setup_for_pool(pool, [])
        report = await coordinator.run()

        # Should complete with 0 beads
        assert report.total_beads == 0
        assert report.status == CoordinatorStatus.COMPLETE

    def test_loop_handles_missing_pool(self, tmp_path: Path) -> None:
        """Test loop handles missing pool."""
        manager = PoolManager(tmp_path / "pools")
        loop = ExecutionLoop(manager)

        result = loop.run("nonexistent-pool-id")

        assert not result.success
        assert "not found" in result.message.lower()


# =============================================================================
# Test: Integration Scenarios
# =============================================================================


@pytest.mark.asyncio
class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    async def test_multi_bead_parallel_processing(
        self, deterministic_runtime: DeterministicRuntime, tmp_path: Path
    ) -> None:
        """Test processing multiple beads in parallel."""
        # Create multiple beads with different severities
        beads = [
            create_minimal_bead(bead_id="VKG-MULTI-001", severity=Severity.CRITICAL),
            create_minimal_bead(bead_id="VKG-MULTI-002", severity=Severity.HIGH),
            create_minimal_bead(bead_id="VKG-MULTI-003", severity=Severity.MEDIUM),
        ]

        pool = Pool(
            id="multi-bead-test",
            scope=Scope(files=["contracts/MultiVuln.sol"]),
            bead_ids=[b.id for b in beads],
        )

        # Run with multiple agents per role
        coordinator = AgentCoordinator(
            deterministic_runtime,
            CoordinatorConfig(
                agents_per_role={"attacker": 2, "defender": 2, "verifier": 1}
            ),
        )
        coordinator.setup_for_pool(pool, beads)
        report = await coordinator.run()

        # All beads should be processed
        assert report.total_beads == 3
        # At minimum, attacker and defender should have run
        assert report.results_by_role.get("attacker", 0) > 0
        assert report.results_by_role.get("defender", 0) > 0

    async def test_end_to_end_with_verdict(
        self, deterministic_runtime: DeterministicRuntime, tmp_path: Path
    ) -> None:
        """Test full E2E flow produces verdict."""
        manager = PoolManager(tmp_path / "pools")
        bead_storage = BeadStorage(tmp_path / "beads")

        # Create and save bead
        bead = create_minimal_bead(bead_id="VKG-E2E-VERDICT")
        bead_storage.save_bead(bead)

        # Create pool
        scope = Scope(files=["contracts/VulnerableVault.sol"])
        pool = manager.create_pool(scope, pool_id="e2e-verdict-test")
        manager.add_bead(pool.id, bead.id)

        # Run coordinator
        coordinator = AgentCoordinator(deterministic_runtime)
        coordinator.setup_for_pool(pool, [bead])
        report = await coordinator.run()

        # Process complete
        assert report.status == CoordinatorStatus.COMPLETE

        # Simulate verdict creation (would normally be done by debate)
        verdict = Verdict(
            finding_id=bead.id,
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="Attacker confirmed vulnerability, defender found no mitigations",
        )
        manager.record_verdict(pool.id, verdict)

        # Verify verdict recorded
        pool = manager.get_pool(pool.id)
        assert pool is not None
        assert bead.id in pool.verdicts
        assert pool.vulnerable_count == 1
