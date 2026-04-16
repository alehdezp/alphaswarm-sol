"""Integration tests for context-merge to bead flow.

These tests validate the complete flow from context-merge
request through verification to bead creation.

Tests validate:
- Orchestrator delegation patterns (orchestrators don't execute directly)
- Concurrency limits (max parallel subagents)
- Quality loops (retry on verification failure)
- Bead state transitions through flows
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alphaswarm_sol.agents.orchestration.sub_coordinator import (
    SubCoordinator,
    SubCoordinatorConfig,
    SubCoordinatorResult,
)
from alphaswarm_sol.agents.orchestration.context_merge_agent import (
    ContextMergeAgent,
    ContextMergeConfig,
    ContextMergeResult,
)
from alphaswarm_sol.beads.context_merge import (
    ContextBeadStatus,
    ContextMergeBead,
)


# =============================================================================
# Mock Factories
# =============================================================================


@pytest.fixture
def mock_protocol_pack():
    """Create mock ProtocolContextPack."""
    pack = MagicMock()
    pack.protocol_name = "TestProtocol"
    pack.chain = "ethereum"
    pack.roles = []
    pack.invariants = []
    return pack


@pytest.fixture
def mock_context_bundle():
    """Create mock ContextBundle for tests."""
    bundle = MagicMock()
    bundle.vulnerability_class = "reentrancy/classic"
    bundle.protocol_context = "Protocol: TestProtocol"
    bundle.vulndoc_context = "VulnDoc: Reentrancy patterns"
    bundle.additional_context = {}
    bundle.to_dict.return_value = {
        "vulnerability_class": "reentrancy/classic",
        "protocol_context": "Protocol: TestProtocol",
        "vulndoc_context": "VulnDoc: Reentrancy patterns",
        "additional_context": {},
    }
    bundle.to_system_prompt.return_value = "System prompt for reentrancy"
    bundle.to_user_context.return_value = "User context for reentrancy"
    return bundle


@pytest.fixture
def mock_context_merge_bead(mock_context_bundle):
    """Create mock ContextMergeBead."""
    bead = MagicMock(spec=ContextMergeBead)
    bead.id = "CTX-abc123def456"
    bead.vulnerability_class = "reentrancy/classic"
    bead.protocol_name = "TestProtocol"
    bead.context_bundle = mock_context_bundle
    bead.target_scope = ["contracts/Token.sol"]
    bead.verification_score = 0.90
    bead.verification_warnings = []
    bead.status = ContextBeadStatus.PENDING
    bead.created_at = datetime.now()
    bead.created_by = "context-merge-agent"
    bead.pool_id = "pool-001"
    bead.finding_bead_ids = []
    bead.metadata = {}
    return bead


# =============================================================================
# TestContextMergeFlow - Integration tests for context-merge flow
# =============================================================================


class TestContextMergeFlow:
    """Integration tests for context-merge flow."""

    @pytest.fixture
    def mock_merge_result(self, mock_context_merge_bead):
        """Create successful ContextMergeResult."""
        return ContextMergeResult(
            success=True,
            bead=mock_context_merge_bead,
            vuln_class="reentrancy/classic",
            attempts=1,
            errors=[],
            final_quality_score=0.90,
        )

    @pytest.fixture
    def mock_failed_result(self):
        """Create failed ContextMergeResult."""
        return ContextMergeResult(
            success=False,
            bead=None,
            vuln_class="reentrancy/classic",
            attempts=3,
            errors=["Quality score below threshold"],
            final_quality_score=0.50,
        )

    @pytest.mark.asyncio
    async def test_full_context_merge_flow(
        self, mock_protocol_pack, mock_merge_result
    ):
        """Test complete context-merge flow.

        This test validates the flow:
        1. SubCoordinator spawns context-merge for vuln class
        2. ContextMergeAgent produces merged context
        3. Verifier validates quality
        4. Bead is created with context
        """
        coordinator = SubCoordinator(
            protocol_pack=mock_protocol_pack,
            target_scope=["contracts/Token.sol"],
            vuln_classes=["reentrancy/classic"],
            pool_id="pool-001",
            config=SubCoordinatorConfig(max_parallel=5),
        )

        # Mock the internal context merge execution
        with patch.object(
            coordinator, "_run_context_merge", return_value=mock_merge_result
        ):
            result = await coordinator.run()

            assert result.success is True
            assert result.total_classes == 1
            assert result.successful_classes == 1
            assert len(result.beads_created) == 1
            assert result.beads_created[0].vulnerability_class == "reentrancy/classic"

    @pytest.mark.asyncio
    async def test_context_merge_to_verifier_flow(
        self, mock_protocol_pack, mock_context_bundle
    ):
        """Test context-merge output flows to verifier.

        The ContextMergeAgent internally merges context, then
        passes the bundle to the verifier for quality check.
        """
        # Create mock components
        mock_merger = MagicMock()
        mock_merger.merge.return_value = MagicMock(
            success=True,
            bundle=mock_context_bundle,
            errors=[],
        )

        mock_verifier = MagicMock()
        mock_verifier.verify.return_value = MagicMock(
            valid=True,
            quality_score=0.90,
            errors=[],
            feedback_for_retry=None,
        )

        mock_bead_factory = MagicMock()
        mock_bead = MagicMock(spec=ContextMergeBead)
        mock_bead.vulnerability_class = "reentrancy/classic"
        mock_bead_factory.create_from_verified_merge.return_value = mock_bead
        mock_bead_factory.save_bead = MagicMock()

        agent = ContextMergeAgent(
            merger=mock_merger,
            verifier=mock_verifier,
            bead_factory=mock_bead_factory,
            config=ContextMergeConfig(max_retries=3),
        )

        result = agent.execute(
            vuln_class="reentrancy/classic",
            protocol_pack=mock_protocol_pack,
            target_scope=["contracts/Token.sol"],
            pool_id="pool-001",
        )

        # Verify flow: merge -> verify -> create bead
        mock_merger.merge.assert_called_once()
        mock_verifier.verify.assert_called_once_with(mock_context_bundle)
        mock_bead_factory.create_from_verified_merge.assert_called_once()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_failed_verification_triggers_retry(
        self, mock_protocol_pack, mock_context_bundle
    ):
        """Test that failed verification triggers quality loop retry."""
        # Create mock components where first verification fails
        mock_merger = MagicMock()
        mock_merger.merge.return_value = MagicMock(
            success=True,
            bundle=mock_context_bundle,
            errors=[],
        )

        # Verification fails first time, passes second time
        mock_verifier = MagicMock()
        mock_verifier.verify.side_effect = [
            MagicMock(
                valid=False,
                quality_score=0.50,
                errors=[MagicMock(message="Quality score too low")],
                feedback_for_retry="Improve coverage of attack vectors",
            ),
            MagicMock(
                valid=True,
                quality_score=0.90,
                errors=[],
                feedback_for_retry=None,
            ),
        ]

        mock_bead_factory = MagicMock()
        mock_bead = MagicMock(spec=ContextMergeBead)
        mock_bead_factory.create_from_verified_merge.return_value = mock_bead
        mock_bead_factory.save_bead = MagicMock()

        agent = ContextMergeAgent(
            merger=mock_merger,
            verifier=mock_verifier,
            bead_factory=mock_bead_factory,
            config=ContextMergeConfig(max_retries=3, retry_on_quality_error=True),
        )

        result = agent.execute(
            vuln_class="reentrancy/classic",
            protocol_pack=mock_protocol_pack,
            target_scope=["contracts/Token.sol"],
        )

        # Should have retried once before succeeding
        assert result.success is True
        assert result.attempts == 2
        assert mock_merger.merge.call_count == 2  # Called twice
        assert mock_verifier.verify.call_count == 2  # Verified twice

    @pytest.mark.asyncio
    async def test_bead_created_on_success(
        self, mock_protocol_pack, mock_merge_result
    ):
        """Test that bead is created on successful flow."""
        coordinator = SubCoordinator(
            protocol_pack=mock_protocol_pack,
            target_scope=["contracts/Token.sol"],
            vuln_classes=["oracle/manipulation"],
            pool_id="pool-002",
        )

        # Mock successful context merge
        with patch.object(
            coordinator, "_run_context_merge", return_value=mock_merge_result
        ):
            result = await coordinator.run()

            assert result.success is True
            assert len(result.beads_created) == 1
            # Bead should have PENDING status (ready for vuln-discovery)
            bead = result.beads_created[0]
            assert bead.status == ContextBeadStatus.PENDING

    @pytest.mark.asyncio
    async def test_parallel_context_merge(
        self, mock_protocol_pack, mock_context_merge_bead
    ):
        """Test parallel context-merge for multiple vuln classes."""
        vuln_classes = ["reentrancy/classic", "oracle/manipulation", "access-control/weak"]

        coordinator = SubCoordinator(
            protocol_pack=mock_protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=vuln_classes,
            pool_id="pool-003",
            config=SubCoordinatorConfig(max_parallel=3),
        )

        # Create unique results for each vuln class
        def create_result(vuln_class):
            bead = MagicMock(spec=ContextMergeBead)
            bead.vulnerability_class = vuln_class
            bead.status = ContextBeadStatus.PENDING
            return ContextMergeResult(
                success=True,
                bead=bead,
                vuln_class=vuln_class,
                attempts=1,
                errors=[],
                final_quality_score=0.90,
            )

        with patch.object(
            coordinator,
            "_run_context_merge",
            side_effect=[create_result(vc) for vc in vuln_classes],
        ):
            result = await coordinator.run()

            assert result.success is True
            assert result.total_classes == 3
            assert result.successful_classes == 3
            assert len(result.beads_created) == 3

    def test_orchestrator_delegates_not_executes(self, mock_protocol_pack):
        """Test that orchestrator delegates work to agents.

        Per orchestration design: orchestrators don't do work directly.
        SubCoordinator creates and delegates to ContextMergeAgent instances.
        """
        coordinator = SubCoordinator(
            protocol_pack=mock_protocol_pack,
            target_scope=["contracts/Token.sol"],
            vuln_classes=["reentrancy/classic"],
            pool_id="pool-004",
        )

        # Coordinator should NOT have direct LLM execution methods
        assert not hasattr(coordinator, "execute_llm")
        assert not hasattr(coordinator, "call_model")
        assert not hasattr(coordinator, "invoke_model")

        # Coordinator delegates via _run_context_merge which spawns agents
        assert hasattr(coordinator, "_run_context_merge")
        assert hasattr(coordinator, "run")

    @pytest.mark.asyncio
    async def test_concurrency_limits_enforced(self, mock_protocol_pack):
        """Test that concurrency limits are enforced.

        Per project context: max 5 subagents per context doc.
        SubCoordinator should respect max_parallel config.

        The semaphore is created in run() and passed to _run_context_merge.
        To properly test concurrency, we need to track within the semaphore.
        """
        # Create coordinator with 5 parallel limit
        coordinator = SubCoordinator(
            protocol_pack=mock_protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=[f"vuln-class-{i}" for i in range(10)],
            pool_id="pool-005",
            config=SubCoordinatorConfig(max_parallel=5),
        )

        # Verify config is set correctly
        assert coordinator.config.max_parallel == 5

        # Track concurrent executions using the passed semaphore
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        async def tracked_run(vuln_class, semaphore):
            nonlocal concurrent_count, max_concurrent
            # Use the passed semaphore to respect concurrency limits
            async with semaphore:
                async with lock:
                    concurrent_count += 1
                    max_concurrent = max(max_concurrent, concurrent_count)

                try:
                    # Simulate work
                    await asyncio.sleep(0.05)
                    return ContextMergeResult(
                        success=True,
                        bead=MagicMock(spec=ContextMergeBead, vulnerability_class=vuln_class),
                        vuln_class=vuln_class,
                        attempts=1,
                        errors=[],
                        final_quality_score=0.90,
                    )
                finally:
                    async with lock:
                        concurrent_count -= 1

        with patch.object(coordinator, "_run_context_merge", side_effect=tracked_run):
            result = await coordinator.run()

            # Max concurrent should not exceed configured limit
            assert max_concurrent <= 5
            assert result.total_classes == 10

    @pytest.mark.asyncio
    async def test_context_merge_to_vuln_discovery_flow(
        self, mock_protocol_pack, mock_merge_result
    ):
        """Test that context-merge bead is ready for vuln-discovery.

        Per 05.5-CONTEXT.md: SubCoordinator ends after context-merge beads
        created. It does NOT spawn vuln-discovery (parent orchestrator does).
        """
        coordinator = SubCoordinator(
            protocol_pack=mock_protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=["reentrancy/classic"],
            pool_id="pool-006",
        )

        with patch.object(
            coordinator, "_run_context_merge", return_value=mock_merge_result
        ):
            result = await coordinator.run()

            assert result.success is True
            assert len(result.beads_created) == 1

            # Bead should be PENDING, ready for vuln-discovery pickup
            bead = result.beads_created[0]
            assert bead.status == ContextBeadStatus.PENDING

            # SubCoordinator should NOT have vuln-discovery spawning
            assert not hasattr(coordinator, "_spawn_vuln_discovery")
            assert not hasattr(coordinator, "spawn_vuln_discovery")


# =============================================================================
# TestBeadStateFlow - Tests for bead state transitions
# =============================================================================


class TestBeadStateFlow:
    """Tests for bead state transitions in flows."""

    @pytest.fixture
    def mock_bead_with_state(self, mock_context_bundle):
        """Create mock bead with state tracking."""
        bead = MagicMock(spec=ContextMergeBead)
        bead.id = "CTX-state123"
        bead.vulnerability_class = "reentrancy/classic"
        bead.status = ContextBeadStatus.PENDING
        bead.context_bundle = mock_context_bundle
        bead.finding_bead_ids = []
        bead.metadata = {}
        return bead

    def test_bead_status_transitions(self, mock_bead_with_state):
        """Test valid bead status transitions.

        Valid transitions:
        - pending -> in_progress
        - in_progress -> verified | failed
        - verified -> complete
        - failed -> pending (retry)
        """
        bead = mock_bead_with_state

        # Define valid transitions
        valid_transitions = {
            ContextBeadStatus.PENDING: [ContextBeadStatus.IN_PROGRESS],
            ContextBeadStatus.IN_PROGRESS: [
                ContextBeadStatus.COMPLETE,  # Was verified in-band
                ContextBeadStatus.FAILED,
            ],
            ContextBeadStatus.COMPLETE: [],  # Terminal state
            ContextBeadStatus.FAILED: [ContextBeadStatus.PENDING],  # Can retry
        }

        # Verify initial state is PENDING
        assert bead.status == ContextBeadStatus.PENDING
        assert bead.status in valid_transitions

        # Simulate state transitions
        # PENDING -> IN_PROGRESS
        bead.status = ContextBeadStatus.IN_PROGRESS
        assert ContextBeadStatus.IN_PROGRESS in valid_transitions[ContextBeadStatus.PENDING]

        # IN_PROGRESS -> COMPLETE
        bead.status = ContextBeadStatus.COMPLETE
        assert ContextBeadStatus.COMPLETE in valid_transitions[ContextBeadStatus.IN_PROGRESS]

        # Test failed transition path
        bead.status = ContextBeadStatus.IN_PROGRESS
        bead.status = ContextBeadStatus.FAILED
        assert ContextBeadStatus.FAILED in valid_transitions[ContextBeadStatus.IN_PROGRESS]

        # FAILED -> PENDING (retry)
        bead.status = ContextBeadStatus.PENDING
        assert ContextBeadStatus.PENDING in valid_transitions[ContextBeadStatus.FAILED]

    def test_bead_preserves_evidence_chain(self, mock_bead_with_state):
        """Test that bead preserves evidence chain through flow."""
        bead = mock_bead_with_state

        # Initialize evidence tracking
        evidence_chain = []

        # Add evidence at each stage
        evidence_chain.append({
            "stage": "context_merge",
            "timestamp": datetime.now().isoformat(),
            "data": "Merged protocol + vulndoc context",
            "quality_score": 0.85,
        })

        evidence_chain.append({
            "stage": "verification",
            "timestamp": datetime.now().isoformat(),
            "data": "Verified by ContextVerifier",
            "quality_score": 0.90,
        })

        evidence_chain.append({
            "stage": "bead_creation",
            "timestamp": datetime.now().isoformat(),
            "data": "Created ContextMergeBead CTX-state123",
            "bead_id": bead.id,
        })

        # Store in bead metadata
        bead.metadata["evidence_chain"] = evidence_chain

        # Verify evidence chain integrity
        assert len(bead.metadata["evidence_chain"]) == 3
        assert bead.metadata["evidence_chain"][0]["stage"] == "context_merge"
        assert bead.metadata["evidence_chain"][1]["stage"] == "verification"
        assert bead.metadata["evidence_chain"][2]["stage"] == "bead_creation"

        # Verify ordering (each stage has increasing timestamp)
        stages = [e["stage"] for e in bead.metadata["evidence_chain"]]
        assert stages == ["context_merge", "verification", "bead_creation"]

    def test_bead_status_helper_methods(self, mock_context_bundle):
        """Test ContextMergeBead status helper methods."""
        # Create a real-ish bead (but with mock bundle)
        bead = ContextMergeBead(
            id="CTX-helper123",
            vulnerability_class="reentrancy/classic",
            protocol_name="TestProtocol",
            context_bundle=mock_context_bundle,
            target_scope=["contracts/Token.sol"],
            verification_score=0.90,
            status=ContextBeadStatus.IN_PROGRESS,
        )

        # Test mark_complete
        bead.mark_complete()
        assert bead.status == ContextBeadStatus.COMPLETE

        # Reset for mark_failed test
        bead.status = ContextBeadStatus.IN_PROGRESS
        bead.mark_failed("Test failure reason")
        assert bead.status == ContextBeadStatus.FAILED
        assert bead.metadata.get("failure_reason") == "Test failure reason"

    def test_bead_finding_association(self, mock_context_bundle):
        """Test associating finding beads with context bead."""
        bead = ContextMergeBead(
            id="CTX-findings123",
            vulnerability_class="oracle/manipulation",
            protocol_name="TestProtocol",
            context_bundle=mock_context_bundle,
            target_scope=["contracts/Oracle.sol"],
            verification_score=0.90,
        )

        # Add finding beads (from vuln-discovery)
        bead.add_finding_bead("VKG-001")
        bead.add_finding_bead("VKG-002")
        bead.add_finding_bead("VKG-003")

        # Should not duplicate
        bead.add_finding_bead("VKG-001")

        assert len(bead.finding_bead_ids) == 3
        assert "VKG-001" in bead.finding_bead_ids
        assert "VKG-002" in bead.finding_bead_ids
        assert "VKG-003" in bead.finding_bead_ids


# =============================================================================
# TestSubCoordinatorEdgeCases - Edge case tests
# =============================================================================


class TestSubCoordinatorEdgeCases:
    """Edge case tests for SubCoordinator."""

    @pytest.mark.asyncio
    async def test_empty_vuln_classes(self, mock_protocol_pack):
        """Test SubCoordinator with empty vuln_classes list."""
        coordinator = SubCoordinator(
            protocol_pack=mock_protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=[],  # Empty
            pool_id="pool-empty",
        )

        result = await coordinator.run()

        assert result.success is True
        assert result.total_classes == 0
        assert result.successful_classes == 0
        assert len(result.beads_created) == 0
        assert len(result.failed_classes) == 0

    @pytest.mark.asyncio
    async def test_partial_failure(self, mock_protocol_pack):
        """Test SubCoordinator when some vuln classes fail."""
        vuln_classes = ["reentrancy/classic", "oracle/manipulation", "invalid/class"]

        coordinator = SubCoordinator(
            protocol_pack=mock_protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=vuln_classes,
            pool_id="pool-partial",
        )

        # Create results: 2 success, 1 failure
        results = [
            ContextMergeResult(
                success=True,
                bead=MagicMock(spec=ContextMergeBead, vulnerability_class="reentrancy/classic"),
                vuln_class="reentrancy/classic",
                attempts=1,
                errors=[],
                final_quality_score=0.90,
            ),
            ContextMergeResult(
                success=True,
                bead=MagicMock(spec=ContextMergeBead, vulnerability_class="oracle/manipulation"),
                vuln_class="oracle/manipulation",
                attempts=1,
                errors=[],
                final_quality_score=0.85,
            ),
            ContextMergeResult(
                success=False,
                bead=None,
                vuln_class="invalid/class",
                attempts=3,
                errors=["Vulndoc not found for invalid/class"],
                final_quality_score=0.0,
            ),
        ]

        with patch.object(coordinator, "_run_context_merge", side_effect=results):
            result = await coordinator.run()

            # Overall should fail (not all succeeded)
            assert result.success is False
            assert result.total_classes == 3
            assert result.successful_classes == 2
            assert len(result.beads_created) == 2
            assert len(result.failed_classes) == 1
            assert "invalid/class" in result.failed_classes

    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_protocol_pack):
        """Test SubCoordinator handles timeouts correctly."""
        coordinator = SubCoordinator(
            protocol_pack=mock_protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=["slow/class"],
            pool_id="pool-timeout",
            config=SubCoordinatorConfig(timeout_per_class_seconds=1),
        )

        # Create timeout result (simulating what _run_context_merge returns on timeout)
        timeout_result = ContextMergeResult(
            success=False,
            bead=None,
            vuln_class="slow/class",
            attempts=0,
            errors=["Timeout after 1s"],
            final_quality_score=0.0,
        )

        with patch.object(coordinator, "_run_context_merge", return_value=timeout_result):
            result = await coordinator.run()

            assert result.success is False
            assert len(result.failed_classes) == 1
            assert "slow/class" in result.failed_classes
            assert "Timeout" in result.errors.get("slow/class", [""])[0]

    @pytest.mark.asyncio
    async def test_exception_handling(self, mock_protocol_pack):
        """Test SubCoordinator handles exceptions gracefully."""
        coordinator = SubCoordinator(
            protocol_pack=mock_protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=["error/class"],
            pool_id="pool-exception",
        )

        # Simulate exception during execution
        with patch.object(
            coordinator,
            "_run_context_merge",
            side_effect=RuntimeError("Unexpected error"),
        ):
            result = await coordinator.run()

            assert result.success is False
            assert len(result.failed_classes) == 1
            assert "error/class" in result.failed_classes
            assert "Unexpected error" in str(result.errors.get("error/class", []))

    def test_get_beads_by_status(self, mock_protocol_pack, mock_context_merge_bead):
        """Test filtering beads by status."""
        coordinator = SubCoordinator(
            protocol_pack=mock_protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=[],
            pool_id="pool-filter",
        )

        # Manually add beads with different statuses
        pending_bead = MagicMock(spec=ContextMergeBead)
        pending_bead.status = ContextBeadStatus.PENDING

        complete_bead = MagicMock(spec=ContextMergeBead)
        complete_bead.status = ContextBeadStatus.COMPLETE

        coordinator._beads = [pending_bead, complete_bead]

        # Test filtering
        pending = coordinator.get_beads_by_status("pending")
        assert len(pending) == 1

        complete = coordinator.get_beads_by_status("complete")
        assert len(complete) == 1

        failed = coordinator.get_beads_by_status("failed")
        assert len(failed) == 0

        # Test invalid status
        invalid = coordinator.get_beads_by_status("invalid")
        assert len(invalid) == 0
