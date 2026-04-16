"""Component tests for ContextMergeAgent.

These tests validate the context-merge agent in isolation
with mocked dependencies for deterministic behavior.

Tests cover:
- Quality loop execution (merge -> verify -> retry)
- Bead creation on successful verification
- Error handling (schema errors, quality errors)
- Max retry enforcement
- Configuration options
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from unittest.mock import MagicMock, Mock

import pytest

from alphaswarm_sol.agents.context.types import ContextBundle, RiskProfile, RiskCategory
from alphaswarm_sol.agents.context.verifier import VerificationResult, VerificationError
from alphaswarm_sol.agents.context.merger import MergeResult
from alphaswarm_sol.agents.orchestration.context_merge_agent import (
    ContextMergeAgent,
    ContextMergeConfig,
    ContextMergeResult,
)


class TestContextMergeAgentComponent:
    """Component tests for ContextMergeAgent."""

    @pytest.fixture
    def mock_merger(self):
        """Create mock merger for testing."""
        merger = MagicMock()
        return merger

    @pytest.fixture
    def mock_verifier(self):
        """Create mock verifier for testing."""
        verifier = MagicMock()
        return verifier

    @pytest.fixture
    def mock_bead_factory(self):
        """Create mock bead factory for testing."""
        factory = MagicMock()
        # Default behavior: create and save bead successfully
        mock_bead = MagicMock()
        mock_bead.id = "CTX-test-123"
        factory.create_from_verified_merge.return_value = mock_bead
        return factory

    @pytest.fixture
    def sample_protocol_pack(self):
        """Create mock protocol pack for testing."""
        pack = MagicMock()
        pack.protocol_name = "TestProtocol"
        return pack

    @pytest.fixture
    def sample_bundle(self):
        """Create sample context bundle for testing."""
        return ContextBundle(
            vulnerability_class="reentrancy/classic",
            reasoning_template="1. Check CEI pattern\n2. Look for guards\n3. Verify state updates\n4. Analyze callbacks\n5. Review external calls",
            semantic_triggers=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            vql_queries=["FIND functions WHERE has_external_call"],
            graph_patterns=["R:bal->X:out->W:bal"],
            risk_profile=RiskProfile(
                access_risks=RiskCategory(present=True, confidence="certain"),
                timing_risks=RiskCategory(present=True, confidence="inferred"),
            ),
            protocol_name="TestProtocol",
            target_scope=["contracts/Test.sol"],
            token_estimate=2000,
        )

    @pytest.fixture
    def successful_merge_result(self, sample_bundle):
        """Create successful merge result."""
        return MergeResult(
            success=True,
            bundle=sample_bundle,
            errors=[],
            warnings=[],
            token_count=2000,
            trimmed=False,
            sources_used=["vulndoc", "protocol_pack"],
        )

    @pytest.fixture
    def successful_verification_result(self):
        """Create successful verification result."""
        return VerificationResult(
            valid=True,
            errors=[],
            warnings=[],
            quality_score=0.95,
            feedback_for_retry=None,
        )

    def test_execute_success_single_attempt(
        self,
        mock_merger,
        mock_verifier,
        mock_bead_factory,
        sample_protocol_pack,
        successful_merge_result,
        successful_verification_result,
    ):
        """Test successful execution on first attempt."""
        mock_merger.merge.return_value = successful_merge_result
        mock_verifier.verify.return_value = successful_verification_result

        agent = ContextMergeAgent(
            merger=mock_merger,
            verifier=mock_verifier,
            bead_factory=mock_bead_factory,
        )

        result = agent.execute(
            vuln_class="reentrancy/classic",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/Test.sol"],
            pool_id="POOL-001",
        )

        assert result.success is True
        assert result.bead is not None
        assert result.attempts == 1
        assert result.final_quality_score == 0.95
        assert len(result.errors) == 0
        mock_merger.merge.assert_called_once()
        mock_verifier.verify.assert_called_once()
        mock_bead_factory.create_from_verified_merge.assert_called_once()
        mock_bead_factory.save_bead.assert_called_once()

    def test_execute_retry_on_quality_failure(
        self,
        mock_merger,
        mock_verifier,
        mock_bead_factory,
        sample_protocol_pack,
        sample_bundle,
    ):
        """Test retry loop when verification fails with quality error."""
        # First merge succeeds but verification fails
        first_merge = MergeResult(
            success=True,
            bundle=sample_bundle,
            errors=[],
            warnings=[],
            token_count=2000,
            trimmed=False,
            sources_used=["vulndoc"],
        )

        # Second merge also succeeds
        second_merge = MergeResult(
            success=True,
            bundle=sample_bundle,
            errors=[],
            warnings=[],
            token_count=2000,
            trimmed=False,
            sources_used=["vulndoc"],
        )

        mock_merger.merge.side_effect = [first_merge, second_merge]

        # First verification fails, second succeeds
        failed_verification = VerificationResult(
            valid=False,
            errors=[VerificationError(
                field="reasoning_template",
                error_type="too_short",
                message="Template too short",
                severity="error",
            )],
            warnings=[],
            quality_score=0.60,
            feedback_for_retry="Please expand reasoning template",
        )
        successful_verification = VerificationResult(
            valid=True,
            errors=[],
            warnings=[],
            quality_score=0.90,
            feedback_for_retry=None,
        )
        mock_verifier.verify.side_effect = [failed_verification, successful_verification]

        agent = ContextMergeAgent(
            merger=mock_merger,
            verifier=mock_verifier,
            bead_factory=mock_bead_factory,
        )

        result = agent.execute(
            vuln_class="reentrancy/classic",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/Test.sol"],
        )

        assert result.success is True
        assert result.attempts == 2
        assert mock_merger.merge.call_count == 2
        assert mock_verifier.verify.call_count == 2

    def test_execute_max_retries_exhausted(
        self,
        mock_merger,
        mock_verifier,
        mock_bead_factory,
        sample_protocol_pack,
        sample_bundle,
    ):
        """Test failure when max retries exhausted."""
        # All merges succeed but verifications fail
        merge_result = MergeResult(
            success=True,
            bundle=sample_bundle,
            errors=[],
            warnings=[],
            token_count=2000,
            trimmed=False,
            sources_used=["vulndoc"],
        )
        mock_merger.merge.return_value = merge_result

        failed_verification = VerificationResult(
            valid=False,
            errors=[VerificationError(
                field="reasoning_template",
                error_type="too_short",
                message="Template too short",
                severity="error",
            )],
            warnings=[],
            quality_score=0.50,
            feedback_for_retry="Please expand template",
        )
        mock_verifier.verify.return_value = failed_verification

        config = ContextMergeConfig(max_retries=3)
        agent = ContextMergeAgent(
            merger=mock_merger,
            verifier=mock_verifier,
            bead_factory=mock_bead_factory,
            config=config,
        )

        result = agent.execute(
            vuln_class="reentrancy/classic",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/Test.sol"],
        )

        assert result.success is False
        assert result.bead is None
        assert result.attempts == 3
        assert result.final_quality_score == 0.50
        mock_bead_factory.create_from_verified_merge.assert_not_called()

    def test_execute_abort_on_schema_error(
        self,
        mock_merger,
        mock_verifier,
        mock_bead_factory,
        sample_protocol_pack,
    ):
        """Test immediate abort on schema error (missing vulndoc)."""
        merge_result = MergeResult(
            success=False,
            bundle=None,
            errors=["VulnDoc not found: nonexistent/vuln"],
            warnings=[],
            token_count=0,
            trimmed=False,
            sources_used=[],
        )
        mock_merger.merge.return_value = merge_result

        config = ContextMergeConfig(abort_on_schema_error=True)
        agent = ContextMergeAgent(
            merger=mock_merger,
            verifier=mock_verifier,
            bead_factory=mock_bead_factory,
            config=config,
        )

        result = agent.execute(
            vuln_class="nonexistent/vuln",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/Test.sol"],
        )

        assert result.success is False
        assert result.bead is None
        assert result.attempts == 1  # No retries for schema errors
        assert "not found" in result.errors[0].lower()
        mock_verifier.verify.assert_not_called()

    def test_config_disable_retry_on_quality(
        self,
        mock_merger,
        mock_verifier,
        mock_bead_factory,
        sample_protocol_pack,
        sample_bundle,
    ):
        """Test config option to disable retry on quality errors."""
        merge_result = MergeResult(
            success=True,
            bundle=sample_bundle,
            errors=[],
            warnings=[],
            token_count=2000,
            trimmed=False,
            sources_used=["vulndoc"],
        )
        mock_merger.merge.return_value = merge_result

        failed_verification = VerificationResult(
            valid=False,
            errors=[VerificationError(
                field="reasoning_template",
                error_type="too_short",
                message="Template too short",
                severity="error",
            )],
            warnings=[],
            quality_score=0.50,
            feedback_for_retry="Expand template",
        )
        mock_verifier.verify.return_value = failed_verification

        config = ContextMergeConfig(
            max_retries=3,
            retry_on_quality_error=False,  # Disable retry
        )
        agent = ContextMergeAgent(
            merger=mock_merger,
            verifier=mock_verifier,
            bead_factory=mock_bead_factory,
            config=config,
        )

        result = agent.execute(
            vuln_class="reentrancy/classic",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/Test.sol"],
        )

        assert result.success is False
        assert result.attempts == 1  # No retry due to config
        mock_merger.merge.assert_called_once()

    def test_agent_does_not_have_direct_llm_client(
        self,
        mock_merger,
        mock_verifier,
        mock_bead_factory,
    ):
        """Test that agent delegates to components, no direct LLM access."""
        agent = ContextMergeAgent(
            merger=mock_merger,
            verifier=mock_verifier,
            bead_factory=mock_bead_factory,
        )

        # Agent should not have direct LLM client
        assert not hasattr(agent, "_llm_client")
        assert not hasattr(agent, "anthropic_client")
        assert not hasattr(agent, "runtime")

        # Agent delegates to components
        assert hasattr(agent, "merger")
        assert hasattr(agent, "verifier")
        assert hasattr(agent, "bead_factory")

    def test_execute_passes_vuln_class_to_merger(
        self,
        mock_merger,
        mock_verifier,
        mock_bead_factory,
        sample_protocol_pack,
        successful_merge_result,
        successful_verification_result,
    ):
        """Test that vuln_class is passed correctly to merger."""
        mock_merger.merge.return_value = successful_merge_result
        mock_verifier.verify.return_value = successful_verification_result

        agent = ContextMergeAgent(
            merger=mock_merger,
            verifier=mock_verifier,
            bead_factory=mock_bead_factory,
        )

        agent.execute(
            vuln_class="oracle/price-manipulation",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/Oracle.sol"],
        )

        # Verify vuln_class was passed to merger
        call_args = mock_merger.merge.call_args
        assert call_args.kwargs.get("vuln_class") == "oracle/price-manipulation" or \
               call_args.args[0] == "oracle/price-manipulation"

    def test_execute_handles_bead_creation_failure(
        self,
        mock_merger,
        mock_verifier,
        mock_bead_factory,
        sample_protocol_pack,
        successful_merge_result,
        successful_verification_result,
    ):
        """Test handling when bead creation fails."""
        mock_merger.merge.return_value = successful_merge_result
        mock_verifier.verify.return_value = successful_verification_result
        mock_bead_factory.create_from_verified_merge.side_effect = Exception(
            "Failed to create bead"
        )

        agent = ContextMergeAgent(
            merger=mock_merger,
            verifier=mock_verifier,
            bead_factory=mock_bead_factory,
        )

        result = agent.execute(
            vuln_class="reentrancy/classic",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/Test.sol"],
        )

        assert result.success is False
        assert result.bead is None
        assert any("Bead creation failed" in err for err in result.errors)

    def test_execute_empty_target_scope(
        self,
        mock_merger,
        mock_verifier,
        mock_bead_factory,
        sample_protocol_pack,
        successful_merge_result,
        successful_verification_result,
    ):
        """Test execution with empty target scope."""
        mock_merger.merge.return_value = successful_merge_result
        mock_verifier.verify.return_value = successful_verification_result

        agent = ContextMergeAgent(
            merger=mock_merger,
            verifier=mock_verifier,
            bead_factory=mock_bead_factory,
        )

        result = agent.execute(
            vuln_class="reentrancy/classic",
            protocol_pack=sample_protocol_pack,
            target_scope=[],  # Empty scope
        )

        # Should still work - merger handles validation
        assert mock_merger.merge.called

    def test_result_includes_vuln_class(
        self,
        mock_merger,
        mock_verifier,
        mock_bead_factory,
        sample_protocol_pack,
        successful_merge_result,
        successful_verification_result,
    ):
        """Test that result includes vuln_class for tracking."""
        mock_merger.merge.return_value = successful_merge_result
        mock_verifier.verify.return_value = successful_verification_result

        agent = ContextMergeAgent(
            merger=mock_merger,
            verifier=mock_verifier,
            bead_factory=mock_bead_factory,
        )

        result = agent.execute(
            vuln_class="reentrancy/cross-function",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/Test.sol"],
        )

        assert result.vuln_class == "reentrancy/cross-function"
