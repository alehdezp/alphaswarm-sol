"""Tests for SubCoordinator and ContextMergeAgent.

Tests cover:
- ContextMergeAgent quality loop (merge -> verify -> retry)
- ContextMergeAgent error handling (schema errors, max retries, bead creation failure)
- SubCoordinator parallel execution
- SubCoordinator concurrency control
- SubCoordinator timeout handling
- SubCoordinator partial failure handling
"""

from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import asyncio

import pytest

from alphaswarm_sol.agents.context import (
    ContextBundle,
    ContextMerger,
    ContextVerifier,
    RiskProfile,
    RiskCategory,
)
from alphaswarm_sol.agents.context.bead_factory import ContextBeadFactory
from alphaswarm_sol.agents.context.merger import MergeResult
from alphaswarm_sol.agents.context.verifier import VerificationResult, VerificationError
from alphaswarm_sol.agents.orchestration import (
    ContextMergeAgent,
    ContextMergeConfig,
    ContextMergeResult,
    SubCoordinator,
    SubCoordinatorConfig,
    SubCoordinatorResult,
)
from alphaswarm_sol.beads.context_merge import ContextMergeBead, ContextBeadStatus
from alphaswarm_sol.context.schema import ProtocolContextPack


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_protocol_pack():
    """Create a minimal protocol context pack for testing."""
    return ProtocolContextPack(
        protocol_name="TestProtocol",
        protocol_type="lending",
        roles=[],
        assumptions=[],
        invariants=[],
        offchain_inputs=[],
    )


@pytest.fixture
def sample_bundle():
    """Create a valid context bundle for testing."""
    return ContextBundle(
        vulnerability_class="reentrancy/classic",
        reasoning_template="1. Check CEI\n2. Guards\n3. State\n4. Calls\n5. Callbacks",
        semantic_triggers=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        vql_queries=["FIND functions WHERE has_external_call"],
        graph_patterns=["R:bal->X:out->W:bal"],
        risk_profile=RiskProfile(
            oracle_risks=RiskCategory(present=False, notes="No oracles"),
            liquidity_risks=RiskCategory(present=False, notes="No flash loans"),
            access_risks=RiskCategory(present=True, notes="External calls present", confidence="certain"),
            upgrade_risks=RiskCategory(present=False, notes="Not upgradeable"),
        ),
        protocol_name="TestProtocol",
        target_scope=["contracts/Vault.sol"],
        token_estimate=500,
    )


@pytest.fixture
def mock_merger(sample_bundle):
    """Create a mock merger that returns successful results."""
    merger = Mock(spec=ContextMerger)
    merger.merge.return_value = MergeResult(
        success=True,
        bundle=sample_bundle,
        errors=[],
        warnings=[],
        token_count=500,
        trimmed=False,
        sources_used=["vulndocs/reentrancy/classic"],
    )
    return merger


@pytest.fixture
def mock_verifier():
    """Create a mock verifier that returns successful results."""
    verifier = Mock(spec=ContextVerifier)
    verifier.verify.return_value = VerificationResult(
        valid=True,
        errors=[],
        warnings=[],
        quality_score=0.95,
        feedback_for_retry=None,
    )
    return verifier


@pytest.fixture
def mock_bead_factory(sample_bundle):
    """Create a mock bead factory that returns beads."""
    factory = Mock(spec=ContextBeadFactory)
    bead = ContextMergeBead(
        id="CTX-test123",
        vulnerability_class="reentrancy/classic",
        protocol_name="TestProtocol",
        context_bundle=sample_bundle,
        target_scope=["contracts/Vault.sol"],
        verification_score=0.95,
        pool_id="test-pool",
    )
    factory.create_from_verified_merge.return_value = bead
    factory.save_bead.return_value = None
    return factory


# =============================================================================
# ContextMergeAgent Tests
# =============================================================================


def test_context_merge_agent_execute_success(
    mock_merger, mock_verifier, mock_bead_factory, sample_protocol_pack
):
    """Test happy path: merge, verify, create bead."""
    agent = ContextMergeAgent(
        merger=mock_merger,
        verifier=mock_verifier,
        bead_factory=mock_bead_factory,
    )

    result = agent.execute(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
        pool_id="test-pool",
    )

    # Assert success
    assert result.success
    assert result.bead is not None
    assert result.bead.id == "CTX-test123"
    assert result.attempts == 1
    assert result.final_quality_score == 0.95
    assert len(result.errors) == 0

    # Verify calls
    mock_merger.merge.assert_called_once()
    mock_verifier.verify.assert_called_once()
    mock_bead_factory.create_from_verified_merge.assert_called_once()
    mock_bead_factory.save_bead.assert_called_once()


def test_context_merge_agent_retry_on_verification_fail(
    mock_merger, mock_verifier, mock_bead_factory, sample_protocol_pack, sample_bundle
):
    """Test retries with feedback on verification failure."""
    # First attempt: verification fails
    # Second attempt: verification succeeds
    mock_verifier.verify.side_effect = [
        VerificationResult(
            valid=False,
            errors=[
                VerificationError(
                    field="reasoning_template",
                    error_type="too_short",
                    message="Reasoning too short",
                    severity="error",
                )
            ],
            warnings=[],
            quality_score=0.5,
            feedback_for_retry="Add more reasoning steps",
        ),
        VerificationResult(
            valid=True,
            errors=[],
            warnings=[],
            quality_score=0.95,
            feedback_for_retry=None,
        ),
    ]

    agent = ContextMergeAgent(
        merger=mock_merger,
        verifier=mock_verifier,
        bead_factory=mock_bead_factory,
    )

    result = agent.execute(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
    )

    # Assert success after retry
    assert result.success
    assert result.attempts == 2
    assert result.final_quality_score == 0.95

    # Verify retry with feedback
    assert mock_merger.merge.call_count == 2
    assert mock_verifier.verify.call_count == 2


def test_context_merge_agent_abort_on_schema_error(
    mock_merger, mock_verifier, mock_bead_factory, sample_protocol_pack
):
    """Test immediate abort on schema errors (missing vulndoc)."""
    # Merge returns schema error
    mock_merger.merge.return_value = MergeResult(
        success=False,
        bundle=None,
        errors=["Vulndoc not found: reentrancy/classic"],
        warnings=[],
        token_count=0,
        trimmed=False,
        sources_used=[],
    )

    config = ContextMergeConfig(abort_on_schema_error=True)
    agent = ContextMergeAgent(
        merger=mock_merger,
        verifier=mock_verifier,
        bead_factory=mock_bead_factory,
        config=config,
    )

    result = agent.execute(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
    )

    # Assert failure
    assert not result.success
    assert result.bead is None
    assert result.attempts == 1
    assert "not found" in result.errors[0].lower()

    # Verify no verification or bead creation attempted
    mock_verifier.verify.assert_not_called()
    mock_bead_factory.create_from_verified_merge.assert_not_called()


def test_context_merge_agent_max_retries_exhausted(
    mock_merger, mock_verifier, mock_bead_factory, sample_protocol_pack
):
    """Test failure after max retries exhausted."""
    # All attempts fail verification
    mock_verifier.verify.return_value = VerificationResult(
        valid=False,
        errors=[
            VerificationError(
                field="semantic_triggers",
                error_type="missing",
                message="No semantic triggers",
                severity="error",
            )
        ],
        warnings=[],
        quality_score=0.3,
        feedback_for_retry="Add semantic triggers",
    )

    config = ContextMergeConfig(max_retries=3, retry_on_quality_error=True)
    agent = ContextMergeAgent(
        merger=mock_merger,
        verifier=mock_verifier,
        bead_factory=mock_bead_factory,
        config=config,
    )

    result = agent.execute(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
    )

    # Assert failure
    assert not result.success
    assert result.bead is None
    assert result.attempts == 3
    assert result.final_quality_score == 0.3
    assert len(result.errors) > 0

    # Verify max retries reached
    assert mock_merger.merge.call_count == 3
    assert mock_verifier.verify.call_count == 3


def test_context_merge_agent_bead_creation_failure(
    mock_merger, mock_verifier, mock_bead_factory, sample_protocol_pack
):
    """Test handling of bead factory errors."""
    # Bead factory raises exception
    mock_bead_factory.create_from_verified_merge.side_effect = ValueError(
        "Invalid bundle format"
    )

    agent = ContextMergeAgent(
        merger=mock_merger,
        verifier=mock_verifier,
        bead_factory=mock_bead_factory,
    )

    result = agent.execute(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
    )

    # Assert failure
    assert not result.success
    assert result.bead is None
    assert "Bead creation failed" in result.errors[0]
    assert result.final_quality_score == 0.95  # Verification passed


def test_context_merge_agent_no_retry_on_quality_error_disabled(
    mock_merger, mock_verifier, mock_bead_factory, sample_protocol_pack
):
    """Test no retries when retry_on_quality_error is False."""
    # Verification fails
    mock_verifier.verify.return_value = VerificationResult(
        valid=False,
        errors=[
            VerificationError(
                field="reasoning_template",
                error_type="too_short",
                message="Reasoning too short",
                severity="error",
            )
        ],
        warnings=[],
        quality_score=0.5,
        feedback_for_retry="Add more reasoning",
    )

    config = ContextMergeConfig(retry_on_quality_error=False)
    agent = ContextMergeAgent(
        merger=mock_merger,
        verifier=mock_verifier,
        bead_factory=mock_bead_factory,
        config=config,
    )

    result = agent.execute(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
    )

    # Assert failure without retry
    assert not result.success
    assert result.attempts == 1

    # Verify no retries
    mock_merger.merge.assert_called_once()
    mock_verifier.verify.assert_called_once()


# =============================================================================
# SubCoordinator Tests
# =============================================================================


@pytest.mark.asyncio
async def test_sub_coordinator_single_vuln_class(
    mock_merger, mock_verifier, mock_bead_factory, sample_protocol_pack
):
    """Test single vuln class succeeds."""
    coordinator = SubCoordinator(
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
        vuln_classes=["reentrancy/classic"],
        pool_id="test-pool",
    )

    # Replace internal components with mocks
    coordinator._merger = mock_merger
    coordinator._verifier = mock_verifier
    coordinator._bead_factory = mock_bead_factory

    result = await coordinator.run()

    # Assert success
    assert result.success
    assert result.total_classes == 1
    assert result.successful_classes == 1
    assert len(result.beads_created) == 1
    assert len(result.failed_classes) == 0
    assert result.beads_created[0].id == "CTX-test123"


@pytest.mark.asyncio
async def test_sub_coordinator_multiple_parallel(
    mock_merger, mock_verifier, mock_bead_factory, sample_protocol_pack, sample_bundle
):
    """Test multiple classes run in parallel."""
    # Create multiple beads
    beads = [
        ContextMergeBead(
            id=f"CTX-test{i}",
            vulnerability_class=f"class-{i}",
            protocol_name="TestProtocol",
            context_bundle=sample_bundle,
            target_scope=["contracts/Vault.sol"],
            verification_score=0.95,
            pool_id="test-pool",
        )
        for i in range(5)
    ]
    mock_bead_factory.create_from_verified_merge.side_effect = beads

    coordinator = SubCoordinator(
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
        vuln_classes=[f"class-{i}" for i in range(5)],
        pool_id="test-pool",
        config=SubCoordinatorConfig(max_parallel=3),
    )

    coordinator._merger = mock_merger
    coordinator._verifier = mock_verifier
    coordinator._bead_factory = mock_bead_factory

    result = await coordinator.run()

    # Assert all succeeded
    assert result.success
    assert result.total_classes == 5
    assert result.successful_classes == 5
    assert len(result.beads_created) == 5
    assert len(result.failed_classes) == 0


@pytest.mark.asyncio
async def test_sub_coordinator_partial_failure(
    mock_merger, mock_verifier, mock_bead_factory, sample_protocol_pack, sample_bundle
):
    """Test some classes fail, others succeed."""
    # First two succeed, third fails
    merge_results = [
        MergeResult(
            success=True,
            bundle=sample_bundle,
            errors=[],
            warnings=[],
            token_count=500,
            trimmed=False,
            sources_used=["vulndocs"],
        ),
        MergeResult(
            success=True,
            bundle=sample_bundle,
            errors=[],
            warnings=[],
            token_count=500,
            trimmed=False,
            sources_used=["vulndocs"],
        ),
        MergeResult(
            success=False,
            bundle=None,
            errors=["Vulndoc not found"],
            warnings=[],
            token_count=0,
            trimmed=False,
            sources_used=[],
        ),
    ]
    mock_merger.merge.side_effect = merge_results

    beads = [
        ContextMergeBead(
            id=f"CTX-test{i}",
            vulnerability_class=f"class-{i}",
            protocol_name="TestProtocol",
            context_bundle=sample_bundle,
            target_scope=["contracts/Vault.sol"],
            verification_score=0.95,
            pool_id="test-pool",
        )
        for i in range(2)
    ]
    mock_bead_factory.create_from_verified_merge.side_effect = beads

    coordinator = SubCoordinator(
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
        vuln_classes=["class-0", "class-1", "class-2"],
        pool_id="test-pool",
    )

    coordinator._merger = mock_merger
    coordinator._verifier = mock_verifier
    coordinator._bead_factory = mock_bead_factory

    result = await coordinator.run()

    # Assert partial success
    assert not result.success  # Overall failure due to one class failing
    assert result.total_classes == 3
    assert result.successful_classes == 2
    assert len(result.beads_created) == 2
    assert len(result.failed_classes) == 1
    assert "class-2" in result.failed_classes
    assert "class-2" in result.errors


@pytest.mark.asyncio
async def test_sub_coordinator_all_fail(
    mock_merger, mock_verifier, mock_bead_factory, sample_protocol_pack
):
    """Test all classes fail."""
    # All merges fail
    mock_merger.merge.return_value = MergeResult(
        success=False,
        bundle=None,
        errors=["Merge failed"],
        warnings=[],
        token_count=0,
        trimmed=False,
        sources_used=[],
    )

    coordinator = SubCoordinator(
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
        vuln_classes=["class-0", "class-1", "class-2"],
        pool_id="test-pool",
    )

    coordinator._merger = mock_merger
    coordinator._verifier = mock_verifier
    coordinator._bead_factory = mock_bead_factory

    result = await coordinator.run()

    # Assert all failed
    assert not result.success
    assert result.total_classes == 3
    assert result.successful_classes == 0
    assert len(result.beads_created) == 0
    assert len(result.failed_classes) == 3
    assert len(result.errors) == 3


@pytest.mark.asyncio
async def test_sub_coordinator_respects_max_parallel(sample_protocol_pack):
    """Test concurrency limit is honored."""
    # Track concurrent executions
    concurrent_count = 0
    max_concurrent = 0

    async def track_concurrency(*args, **kwargs):
        nonlocal concurrent_count, max_concurrent
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        await asyncio.sleep(0.1)  # Simulate work
        concurrent_count -= 1

        # Return a result
        return ContextMergeResult(
            success=True,
            bead=Mock(spec=ContextMergeBead),
            vuln_class="test",
            attempts=1,
            errors=[],
            final_quality_score=0.95,
        )

    coordinator = SubCoordinator(
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
        vuln_classes=[f"class-{i}" for i in range(10)],
        pool_id="test-pool",
        config=SubCoordinatorConfig(max_parallel=3),
    )

    # Patch the agent execution
    with patch.object(
        ContextMergeAgent, "execute", side_effect=track_concurrency
    ):
        await coordinator.run()

    # Assert max concurrent executions <= max_parallel
    assert max_concurrent <= 3


@pytest.mark.asyncio
async def test_sub_coordinator_timeout_per_class(
    sample_protocol_pack, sample_bundle
):
    """Test timeout per class prevents runaway tasks."""
    import time

    # Create merger that hangs (synchronous sleep, not async)
    def slow_merge(*args, **kwargs):
        time.sleep(10)  # Longer than timeout
        return MergeResult(
            success=True,
            bundle=sample_bundle,
            errors=[],
            warnings=[],
            token_count=500,
            trimmed=False,
            sources_used=[],
        )

    mock_slow_merger = Mock(spec=ContextMerger)
    mock_slow_merger.merge.side_effect = slow_merge

    coordinator = SubCoordinator(
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
        vuln_classes=["slow-class"],
        pool_id="test-pool",
        config=SubCoordinatorConfig(timeout_per_class_seconds=1),
    )

    # Mock components with slow merger
    coordinator._merger = mock_slow_merger
    coordinator._verifier = Mock(spec=ContextVerifier)
    coordinator._bead_factory = Mock(spec=ContextBeadFactory)

    result = await coordinator.run()

    # Assert timeout failure
    assert not result.success
    assert result.total_classes == 1
    assert result.successful_classes == 0
    assert len(result.failed_classes) == 1
    assert "Timeout" in result.errors["slow-class"][0]


@pytest.mark.asyncio
async def test_sub_coordinator_empty_vuln_classes(sample_protocol_pack):
    """Test handling of empty vuln_classes list."""
    coordinator = SubCoordinator(
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
        vuln_classes=[],
        pool_id="test-pool",
    )

    result = await coordinator.run()

    # Assert success with no classes
    assert result.success
    assert result.total_classes == 0
    assert result.successful_classes == 0
    assert len(result.beads_created) == 0
    assert len(result.failed_classes) == 0


@pytest.mark.asyncio
async def test_sub_coordinator_get_pending_beads(
    mock_merger, mock_verifier, mock_bead_factory, sample_protocol_pack
):
    """Test get_pending_beads returns only pending beads."""
    coordinator = SubCoordinator(
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
        vuln_classes=["class-0", "class-1"],
        pool_id="test-pool",
    )

    coordinator._merger = mock_merger
    coordinator._verifier = mock_verifier
    coordinator._bead_factory = mock_bead_factory

    await coordinator.run()

    # Get pending beads
    pending = coordinator.get_pending_beads()

    # All should be pending initially
    assert len(pending) == 2
    assert all(bead.status == ContextBeadStatus.PENDING for bead in pending)


@pytest.mark.asyncio
async def test_sub_coordinator_get_beads_by_status(
    mock_merger, mock_verifier, mock_bead_factory, sample_protocol_pack
):
    """Test get_beads_by_status filters correctly."""
    coordinator = SubCoordinator(
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Vault.sol"],
        vuln_classes=["class-0"],
        pool_id="test-pool",
    )

    coordinator._merger = mock_merger
    coordinator._verifier = mock_verifier
    coordinator._bead_factory = mock_bead_factory

    await coordinator.run()

    # Test filtering by status
    pending = coordinator.get_beads_by_status("pending")
    assert len(pending) == 1

    # Test invalid status
    invalid = coordinator.get_beads_by_status("invalid-status")
    assert len(invalid) == 0
