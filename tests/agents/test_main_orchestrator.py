"""Tests for MainOrchestrator.

Tests the full orchestration flow: context-merge -> vuln-discovery.

Per 05.5-07 plan requirements:
- test_run_full_flow_success - Happy path
- test_run_context_merge_failure - Aborts if no beads
- test_run_partial_discovery_failure - Completes with some failures
- test_run_respects_parallel_limit - max_parallel_discovery honored
- test_run_aggregates_findings - All findings collected
- test_run_aggregates_errors - Errors organized by phase
- test_run_discovery_only - Skips context-merge
- test_run_discovery_only_specific_beads - Filters by bead ID
- test_full_pipeline_end_to_end - Protocol pack -> Findings
- test_bead_status_transitions - Context beads marked complete/failed
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alphaswarm_sol.agents.context.types import ContextBundle
from alphaswarm_sol.agents.orchestration.main_orchestrator import (
    MainOrchestrator,
    OrchestrationConfig,
    OrchestrationResult,
)
from alphaswarm_sol.agents.orchestration.sub_coordinator import (
    SubCoordinatorConfig,
    SubCoordinatorResult,
)
from alphaswarm_sol.agents.orchestration.vuln_discovery_agent import (
    VulnDiscoveryConfig,
    VulnDiscoveryResult,
)
from alphaswarm_sol.beads.context_merge import ContextMergeBead, ContextBeadStatus
from alphaswarm_sol.context.schema import ProtocolContextPack


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def protocol_pack() -> ProtocolContextPack:
    """Create a test protocol context pack."""
    return ProtocolContextPack(
        protocol_name="TestProtocol",
        protocol_type="lending",
    )


@pytest.fixture
def mock_risk_profile():
    """Create a mock risk profile."""
    from alphaswarm_sol.agents.context.types import RiskCategory, RiskProfile

    return RiskProfile(
        oracle_risks=RiskCategory(present=False),
        liquidity_risks=RiskCategory(present=False),
        access_risks=RiskCategory(present=True, notes="Admin multisig"),
        upgrade_risks=RiskCategory(present=False),
        integration_risks=RiskCategory(present=False),
        timing_risks=RiskCategory(present=True, notes="Potential reentrancy"),
        economic_risks=RiskCategory(present=False),
        governance_risks=RiskCategory(present=False),
    )


@pytest.fixture
def mock_context_bundle(mock_risk_profile) -> ContextBundle:
    """Create a mock context bundle."""
    return ContextBundle(
        vulnerability_class="reentrancy/classic",
        reasoning_template="1. Check CEI pattern\n2. Look for external calls\n3. Verify state updates",
        semantic_triggers=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        vql_queries=["FIND functions WHERE writes_state"],
        graph_patterns=["R:bal->X:out->W:bal"],
        risk_profile=mock_risk_profile,
        protocol_name="TestProtocol",
        target_scope=["contracts/Vault.sol"],
        token_estimate=3500,
    )


@pytest.fixture
def mock_context_bead(mock_context_bundle: ContextBundle) -> ContextMergeBead:
    """Create a mock context-merge bead."""
    return ContextMergeBead(
        id="CTX-test123",
        vulnerability_class="reentrancy/classic",
        protocol_name="TestProtocol",
        context_bundle=mock_context_bundle,
        target_scope=["contracts/Vault.sol"],
        verification_score=0.9,
        status=ContextBeadStatus.PENDING,
        created_at=datetime.now(),
        pool_id="test-pool",
    )


@pytest.fixture
def mock_context_bead_2(mock_context_bundle: ContextBundle) -> ContextMergeBead:
    """Create a second mock context-merge bead."""
    return ContextMergeBead(
        id="CTX-test456",
        vulnerability_class="access-control/missing-auth",
        protocol_name="TestProtocol",
        context_bundle=mock_context_bundle,
        target_scope=["contracts/Admin.sol"],
        verification_score=0.85,
        status=ContextBeadStatus.PENDING,
        created_at=datetime.now(),
        pool_id="test-pool",
    )


@pytest.fixture
def orchestrator(protocol_pack: ProtocolContextPack, tmp_path: Path) -> MainOrchestrator:
    """Create test orchestrator."""
    config = OrchestrationConfig(
        max_parallel_discovery=2,
        timeout_per_discovery_seconds=10,
    )
    return MainOrchestrator(
        protocol_pack=protocol_pack,
        target_scope=["contracts/"],
        vuln_classes=["reentrancy/classic", "access-control/missing-auth"],
        pool_id="test-pool",
        config=config,
        beads_dir=tmp_path / "beads",
    )


# =============================================================================
# Basic Initialization Tests
# =============================================================================


class TestMainOrchestratorInit:
    """Test MainOrchestrator initialization."""

    def test_init_with_defaults(self, protocol_pack: ProtocolContextPack):
        """Test initialization with default config."""
        orchestrator = MainOrchestrator(
            protocol_pack=protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=["reentrancy/classic"],
        )

        assert orchestrator.protocol_pack == protocol_pack
        assert orchestrator.target_scope == ["contracts/"]
        assert orchestrator.vuln_classes == ["reentrancy/classic"]
        assert orchestrator.config is not None
        assert orchestrator.config.max_parallel_discovery == 5  # default

    def test_init_with_custom_config(self, protocol_pack: ProtocolContextPack):
        """Test initialization with custom config."""
        config = OrchestrationConfig(
            max_parallel_discovery=10,
            timeout_per_discovery_seconds=300,
        )
        orchestrator = MainOrchestrator(
            protocol_pack=protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=["reentrancy/classic"],
            config=config,
        )

        assert orchestrator.config.max_parallel_discovery == 10
        assert orchestrator.config.timeout_per_discovery_seconds == 300

    def test_model_and_role_assigned(self, orchestrator: MainOrchestrator):
        """Test MODEL and ROLE class attributes."""
        assert orchestrator.MODEL == "claude-opus-4-5"
        from alphaswarm_sol.agents.runtime.base import AgentRole
        assert orchestrator.ROLE == AgentRole.SUPERVISOR


# =============================================================================
# Full Flow Tests
# =============================================================================


class TestMainOrchestratorRun:
    """Test MainOrchestrator.run() method."""

    @pytest.mark.asyncio
    async def test_run_full_flow_success(
        self,
        orchestrator: MainOrchestrator,
        mock_context_bead: ContextMergeBead,
        mock_context_bead_2: ContextMergeBead,
    ):
        """Test successful full flow execution."""
        # Mock SubCoordinator.run
        mock_sub_result = SubCoordinatorResult(
            success=True,
            beads_created=[mock_context_bead, mock_context_bead_2],
            failed_classes=[],
            errors={},
            total_classes=2,
            successful_classes=2,
        )

        # Mock VulnDiscoveryAgent results
        mock_discovery_result_1 = VulnDiscoveryResult(
            success=True,
            context_bead_id=mock_context_bead.id,
            findings=["VKG-001"],
            findings_count=1,
            errors=[],
            vql_queries_executed=["query1"],
        )
        mock_discovery_result_2 = VulnDiscoveryResult(
            success=True,
            context_bead_id=mock_context_bead_2.id,
            findings=["VKG-002"],
            findings_count=1,
            errors=[],
            vql_queries_executed=["query2"],
        )

        with patch.object(
            orchestrator, "_run_vuln_discovery", new_callable=AsyncMock
        ) as mock_discovery:
            mock_discovery.return_value = {
                mock_context_bead.id: mock_discovery_result_1,
                mock_context_bead_2.id: mock_discovery_result_2,
            }

            with patch(
                "alphaswarm_sol.agents.orchestration.main_orchestrator.SubCoordinator"
            ) as MockSubCoord:
                mock_sub_instance = MagicMock()
                mock_sub_instance.run = AsyncMock(return_value=mock_sub_result)
                MockSubCoord.return_value = mock_sub_instance

                result = await orchestrator.run()

        assert result.success is True
        assert result.phase == "complete"
        assert result.context_beads_created == 2
        assert result.context_beads_failed == 0
        assert result.discovery_completed == 2
        assert result.discovery_failed == 0
        assert result.findings_created == 2

    @pytest.mark.asyncio
    async def test_run_context_merge_failure(
        self,
        orchestrator: MainOrchestrator,
    ):
        """Test abort when no context beads created."""
        # Mock SubCoordinator.run with no beads created
        mock_sub_result = SubCoordinatorResult(
            success=False,
            beads_created=[],
            failed_classes=["reentrancy/classic", "access-control/missing-auth"],
            errors={
                "reentrancy/classic": ["Vulndoc not found"],
                "access-control/missing-auth": ["Merge failed"],
            },
            total_classes=2,
            successful_classes=0,
        )

        with patch(
            "alphaswarm_sol.agents.orchestration.main_orchestrator.SubCoordinator"
        ) as MockSubCoord:
            mock_sub_instance = MagicMock()
            mock_sub_instance.run = AsyncMock(return_value=mock_sub_result)
            MockSubCoord.return_value = mock_sub_instance

            result = await orchestrator.run()

        assert result.success is False
        assert result.phase == "context_merge"
        assert result.context_beads_created == 0
        assert result.context_beads_failed == 2
        assert "context_merge" in result.errors
        assert len(result.errors["context_merge"]) == 2

    @pytest.mark.asyncio
    async def test_run_partial_discovery_failure(
        self,
        orchestrator: MainOrchestrator,
        mock_context_bead: ContextMergeBead,
        mock_context_bead_2: ContextMergeBead,
    ):
        """Test completion with some discovery failures."""
        mock_sub_result = SubCoordinatorResult(
            success=True,
            beads_created=[mock_context_bead, mock_context_bead_2],
            failed_classes=[],
            errors={},
            total_classes=2,
            successful_classes=2,
        )

        # One success, one failure
        mock_discovery_result_1 = VulnDiscoveryResult(
            success=True,
            context_bead_id=mock_context_bead.id,
            findings=["VKG-001"],
            findings_count=1,
            errors=[],
            vql_queries_executed=["query1"],
        )
        mock_discovery_result_2 = VulnDiscoveryResult(
            success=False,
            context_bead_id=mock_context_bead_2.id,
            findings=[],
            findings_count=0,
            errors=["VQL execution failed"],
            vql_queries_executed=[],
        )

        with patch.object(
            orchestrator, "_run_vuln_discovery", new_callable=AsyncMock
        ) as mock_discovery:
            mock_discovery.return_value = {
                mock_context_bead.id: mock_discovery_result_1,
                mock_context_bead_2.id: mock_discovery_result_2,
            }

            with patch(
                "alphaswarm_sol.agents.orchestration.main_orchestrator.SubCoordinator"
            ) as MockSubCoord:
                mock_sub_instance = MagicMock()
                mock_sub_instance.run = AsyncMock(return_value=mock_sub_result)
                MockSubCoord.return_value = mock_sub_instance

                result = await orchestrator.run()

        # Should not be success due to discovery failure
        assert result.success is False
        assert result.phase == "complete"
        assert result.discovery_completed == 1
        assert result.discovery_failed == 1
        assert result.findings_created == 1
        assert "vuln_discovery" in result.errors


class TestVulnDiscoveryExecution:
    """Test _run_vuln_discovery method."""

    @pytest.fixture
    def parallel_test_bundle(self, mock_risk_profile):
        """Create a context bundle for parallel tests."""
        return ContextBundle(
            vulnerability_class="reentrancy/classic",
            reasoning_template="Test reasoning",
            semantic_triggers=["TRANSFERS_VALUE_OUT"],
            vql_queries=["FIND functions"],
            graph_patterns=[],
            risk_profile=mock_risk_profile,
            protocol_name="TestProtocol",
            target_scope=["contracts/"],
            token_estimate=1000,
        )

    @pytest.mark.asyncio
    async def test_run_respects_parallel_limit(
        self,
        protocol_pack: ProtocolContextPack,
        parallel_test_bundle: ContextBundle,
        tmp_path: Path,
    ):
        """Test that max_parallel_discovery is honored."""
        # Create 5 context beads
        beads = []
        for i in range(5):
            bead = ContextMergeBead(
                id=f"CTX-test{i:03d}",
                vulnerability_class="reentrancy/classic",
                protocol_name="TestProtocol",
                context_bundle=parallel_test_bundle,
                target_scope=["contracts/"],
                verification_score=0.9,
                status=ContextBeadStatus.PENDING,
                created_at=datetime.now(),
                pool_id="test-pool",
            )
            beads.append(bead)

        # Set max_parallel to 2
        config = OrchestrationConfig(max_parallel_discovery=2)
        orchestrator = MainOrchestrator(
            protocol_pack=protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=[],
            pool_id="test-pool",
            config=config,
            beads_dir=tmp_path / "beads",
        )

        # Track concurrent executions using threading lock for thread safety
        import threading
        import time

        concurrent_count = 0
        max_concurrent = 0
        lock = threading.Lock()

        def mock_execute(*args):
            nonlocal concurrent_count, max_concurrent
            with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
            time.sleep(0.05)  # Simulate work (sync sleep since execute is sync)
            with lock:
                concurrent_count -= 1
            return VulnDiscoveryResult(
                success=True,
                context_bead_id=args[0].id if args else "unknown",
                findings=[],
                findings_count=0,
                errors=[],
                vql_queries_executed=[],
            )

        with patch(
            "alphaswarm_sol.agents.orchestration.main_orchestrator.VulnDiscoveryAgent"
        ) as MockAgent:
            mock_agent = MagicMock()
            mock_agent.execute = mock_execute
            MockAgent.return_value = mock_agent

            results = await orchestrator._run_vuln_discovery(beads)

        # Verify parallel limit was respected
        assert max_concurrent <= 2
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_run_aggregates_findings(
        self,
        orchestrator: MainOrchestrator,
        mock_context_bead: ContextMergeBead,
        mock_context_bead_2: ContextMergeBead,
    ):
        """Test that all findings are collected."""
        mock_sub_result = SubCoordinatorResult(
            success=True,
            beads_created=[mock_context_bead, mock_context_bead_2],
            failed_classes=[],
            errors={},
            total_classes=2,
            successful_classes=2,
        )

        # Multiple findings per discovery
        mock_discovery_result_1 = VulnDiscoveryResult(
            success=True,
            context_bead_id=mock_context_bead.id,
            findings=["VKG-001", "VKG-002", "VKG-003"],
            findings_count=3,
            errors=[],
            vql_queries_executed=[],
        )
        mock_discovery_result_2 = VulnDiscoveryResult(
            success=True,
            context_bead_id=mock_context_bead_2.id,
            findings=["VKG-004", "VKG-005"],
            findings_count=2,
            errors=[],
            vql_queries_executed=[],
        )

        with patch.object(
            orchestrator, "_run_vuln_discovery", new_callable=AsyncMock
        ) as mock_discovery:
            mock_discovery.return_value = {
                mock_context_bead.id: mock_discovery_result_1,
                mock_context_bead_2.id: mock_discovery_result_2,
            }

            with patch(
                "alphaswarm_sol.agents.orchestration.main_orchestrator.SubCoordinator"
            ) as MockSubCoord:
                mock_sub_instance = MagicMock()
                mock_sub_instance.run = AsyncMock(return_value=mock_sub_result)
                MockSubCoord.return_value = mock_sub_instance

                result = await orchestrator.run()

        assert result.findings_created == 5
        assert result.total_findings == 5

    @pytest.mark.asyncio
    async def test_run_aggregates_errors(
        self,
        orchestrator: MainOrchestrator,
        mock_context_bead: ContextMergeBead,
    ):
        """Test that errors are organized by phase."""
        # Context merge with some errors
        mock_sub_result = SubCoordinatorResult(
            success=True,
            beads_created=[mock_context_bead],
            failed_classes=["access-control/missing-auth"],
            errors={"access-control/missing-auth": ["Vulndoc missing"]},
            total_classes=2,
            successful_classes=1,
        )

        # Discovery failure
        mock_discovery_result = VulnDiscoveryResult(
            success=False,
            context_bead_id=mock_context_bead.id,
            findings=[],
            findings_count=0,
            errors=["VQL parse error", "Graph not found"],
            vql_queries_executed=[],
        )

        with patch.object(
            orchestrator, "_run_vuln_discovery", new_callable=AsyncMock
        ) as mock_discovery:
            mock_discovery.return_value = {
                mock_context_bead.id: mock_discovery_result,
            }

            with patch(
                "alphaswarm_sol.agents.orchestration.main_orchestrator.SubCoordinator"
            ) as MockSubCoord:
                mock_sub_instance = MagicMock()
                mock_sub_instance.run = AsyncMock(return_value=mock_sub_result)
                MockSubCoord.return_value = mock_sub_instance

                result = await orchestrator.run()

        # Check errors organized by phase
        assert "context_merge" in result.errors
        assert "vuln_discovery" in result.errors
        assert any("Vulndoc missing" in e for e in result.errors["context_merge"])
        assert any("VQL parse error" in e for e in result.errors["vuln_discovery"])


# =============================================================================
# Discovery Only Tests
# =============================================================================


class TestDiscoveryOnly:
    """Test run_discovery_only method."""

    @pytest.mark.asyncio
    async def test_run_discovery_only(
        self,
        orchestrator: MainOrchestrator,
        mock_context_bead: ContextMergeBead,
        mock_context_bead_2: ContextMergeBead,
    ):
        """Test skipping context-merge phase."""
        # Mock loading beads
        with patch.object(
            orchestrator.context_bead_factory,
            "list_pending_beads",
            return_value=[mock_context_bead, mock_context_bead_2],
        ):
            mock_discovery_result_1 = VulnDiscoveryResult(
                success=True,
                context_bead_id=mock_context_bead.id,
                findings=["VKG-001"],
                findings_count=1,
                errors=[],
                vql_queries_executed=["query1"],
            )
            mock_discovery_result_2 = VulnDiscoveryResult(
                success=True,
                context_bead_id=mock_context_bead_2.id,
                findings=["VKG-002"],
                findings_count=1,
                errors=[],
                vql_queries_executed=["query2"],
            )

            with patch.object(
                orchestrator, "_run_vuln_discovery", new_callable=AsyncMock
            ) as mock_discovery:
                mock_discovery.return_value = {
                    mock_context_bead.id: mock_discovery_result_1,
                    mock_context_bead_2.id: mock_discovery_result_2,
                }

                result = await orchestrator.run_discovery_only()

        assert result.success is True
        assert result.phase == "complete"
        assert result.context_beads_created == 2  # Loaded, not created
        assert result.discovery_completed == 2
        assert result.findings_created == 2

    @pytest.mark.asyncio
    async def test_run_discovery_only_specific_beads(
        self,
        orchestrator: MainOrchestrator,
        mock_context_bead: ContextMergeBead,
    ):
        """Test filtering by specific bead IDs."""
        # Mock loading specific beads
        with patch.object(
            orchestrator.context_bead_factory,
            "load_bead",
            return_value=mock_context_bead,
        ):
            mock_discovery_result = VulnDiscoveryResult(
                success=True,
                context_bead_id=mock_context_bead.id,
                findings=["VKG-001"],
                findings_count=1,
                errors=[],
                vql_queries_executed=["query1"],
            )

            with patch.object(
                orchestrator, "_run_vuln_discovery", new_callable=AsyncMock
            ) as mock_discovery:
                mock_discovery.return_value = {
                    mock_context_bead.id: mock_discovery_result,
                }

                result = await orchestrator.run_discovery_only(
                    context_bead_ids=["CTX-test123"]
                )

        assert result.success is True
        assert result.context_beads_created == 1
        assert result.discovery_completed == 1

    @pytest.mark.asyncio
    async def test_run_discovery_only_no_beads(
        self,
        orchestrator: MainOrchestrator,
    ):
        """Test when no beads are found."""
        with patch.object(
            orchestrator.context_bead_factory,
            "list_pending_beads",
            return_value=[],
        ):
            result = await orchestrator.run_discovery_only()

        assert result.success is True
        assert result.phase == "complete"
        assert result.context_beads_created == 0
        assert result.discovery_completed == 0
        assert result.findings == []


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_discovery_timeout(
        self,
        protocol_pack: ProtocolContextPack,
        mock_context_bead: ContextMergeBead,
        tmp_path: Path,
    ):
        """Test handling of discovery timeout."""
        import time

        config = OrchestrationConfig(
            max_parallel_discovery=1,
            timeout_per_discovery_seconds=1,  # Short timeout
        )
        orchestrator = MainOrchestrator(
            protocol_pack=protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=[],
            pool_id="test-pool",
            config=config,
            beads_dir=tmp_path / "beads",
        )

        # Mock slow synchronous execution that will timeout
        # Note: run_in_executor runs sync functions, so use time.sleep not asyncio.sleep
        def slow_execute(*args):
            time.sleep(10)  # Longer than timeout
            return VulnDiscoveryResult(
                success=True,
                context_bead_id="test",
                findings=[],
                findings_count=0,
                errors=[],
                vql_queries_executed=[],
            )

        with patch(
            "alphaswarm_sol.agents.orchestration.main_orchestrator.VulnDiscoveryAgent"
        ) as MockAgent:
            mock_agent = MagicMock()
            mock_agent.execute = slow_execute
            MockAgent.return_value = mock_agent

            results = await orchestrator._run_vuln_discovery([mock_context_bead])

        assert mock_context_bead.id in results
        assert results[mock_context_bead.id].success is False
        assert "Timeout" in results[mock_context_bead.id].errors[0]

    @pytest.mark.asyncio
    async def test_discovery_exception(
        self,
        orchestrator: MainOrchestrator,
        mock_context_bead: ContextMergeBead,
    ):
        """Test handling of discovery exceptions."""

        def raise_exception(*args):
            raise RuntimeError("Unexpected error")

        with patch(
            "alphaswarm_sol.agents.orchestration.main_orchestrator.VulnDiscoveryAgent"
        ) as MockAgent:
            mock_agent = MagicMock()
            mock_agent.execute = raise_exception
            MockAgent.return_value = mock_agent

            results = await orchestrator._run_vuln_discovery([mock_context_bead])

        assert mock_context_bead.id in results
        assert results[mock_context_bead.id].success is False
        assert "Unexpected error" in results[mock_context_bead.id].errors[0]


class TestOrchestrationResult:
    """Test OrchestrationResult dataclass."""

    def test_total_findings_property(self):
        """Test total_findings property calculation."""
        result = OrchestrationResult(
            success=True,
            phase="complete",
            context_beads_created=2,
            context_beads_failed=0,
            findings_created=5,
            discovery_completed=2,
            discovery_failed=0,
            findings=["f1", "f2", "f3", "f4", "f5"],
            errors={},
        )

        assert result.total_findings == 5

    def test_empty_result(self):
        """Test empty orchestration result."""
        result = OrchestrationResult(
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

        assert result.total_findings == 0
        assert result.success is True


class TestOrchestrationConfig:
    """Test OrchestrationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = OrchestrationConfig()

        assert config.max_parallel_discovery == 5
        assert config.timeout_per_discovery_seconds == 600
        assert config.sub_coordinator_config is not None
        assert config.vuln_discovery_config is not None

    def test_nested_config(self):
        """Test nested configuration."""
        sub_config = SubCoordinatorConfig(max_parallel=3)
        vuln_config = VulnDiscoveryConfig(max_findings_per_context=5)

        config = OrchestrationConfig(
            max_parallel_discovery=10,
            sub_coordinator_config=sub_config,
            vuln_discovery_config=vuln_config,
        )

        assert config.sub_coordinator_config.max_parallel == 3
        assert config.vuln_discovery_config.max_findings_per_context == 5
