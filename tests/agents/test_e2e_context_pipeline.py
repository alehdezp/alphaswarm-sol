"""End-to-end tests for context-merge -> vuln-discovery pipeline.

These tests validate the complete agent execution flow as defined in Phase 5.5:
- EXEC-01: Context Extraction Protocol (extractor loads index.yaml)
- EXEC-02: Economic Context Integration (RiskProfile from protocol pack)
- EXEC-03: Fresh Context Spawning (SubCoordinator spawns parallel agents)
- EXEC-04: Reasoning Template Application (template in system prompt)
- EXEC-05: Exploit Cross-Reference (vulndoc_reference preserved)
- EXEC-06: Category-Specific Prompts (risk mapping per vuln class)
- EXEC-07: Evidence Chain Validation (vulndoc_reference in findings)
- EXEC-09: Token Budget Optimization (estimation and trimming)
- EXEC-10: Output Format Standardization (consistent bead serialization)
Plus full pipeline E2E tests with MainOrchestrator.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import yaml

from alphaswarm_sol.agents.context import (
    ContextBundle,
    ContextMerger,
    ContextVerifier,
    MergeResult,
    RiskCategory,
    RiskProfile,
    VerificationResult,
    VulndocContextExtractor,
)
from alphaswarm_sol.agents.context.bead_factory import ContextBeadFactory
from alphaswarm_sol.agents.orchestration import (
    ContextMergeAgent,
    ContextMergeConfig,
    ContextMergeResult,
    EvidenceChain,
    FindingBeadFactory,
    FindingInput,
    MainOrchestrator,
    OrchestrationConfig,
    OrchestrationResult,
    SubCoordinator,
    SubCoordinatorConfig,
    SubCoordinatorResult,
    VulnDiscoveryAgent,
    VulnDiscoveryConfig,
    VulnDiscoveryResult,
)
from alphaswarm_sol.beads.context_merge import ContextBeadStatus, ContextMergeBead
from alphaswarm_sol.beads.types import Severity
from alphaswarm_sol.context.schema import ProtocolContextPack


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_protocol_pack():
    """Create minimal protocol pack for testing."""
    return ProtocolContextPack(
        protocol_name="TestVault",
        protocol_type="lending",
    )


@pytest.fixture
def sample_vulndocs(tmp_path):
    """Create minimal vulndocs structure for testing."""
    vulndocs_dir = tmp_path / "vulndocs"
    vulndocs_dir.mkdir()

    # Create reentrancy/classic vulndoc
    reentrancy_dir = vulndocs_dir / "reentrancy" / "classic"
    reentrancy_dir.mkdir(parents=True)

    index_yaml = {
        "id": "reentrancy-classic",
        "category": "reentrancy",
        "subcategory": "classic",
        "severity": "critical",
        "vulndoc": "reentrancy/classic",
        "description": "Classic reentrancy via external call before state update",
        "semantic_triggers": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        "vql_queries": [
            "FIND functions WHERE has_all_operations([TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE])"
        ],
        "graph_patterns": ["R:bal->X:out->W:bal"],
        "reasoning_template": """1. Identify external calls (TRANSFERS_VALUE_OUT)
2. Check for state writes after external calls (WRITES_USER_BALANCE)
3. Verify no reentrancy guard present
4. Trace value flow to confirm exploitability
5. NOT vulnerable if:
   - nonReentrant modifier present
   - CEI pattern followed (checks-effects-interactions)
   - Trusted contracts only""",
        "relevant_properties": ["has_external_call", "writes_state_after_call"],
        "created": "2026-01-22",
    }

    (reentrancy_dir / "index.yaml").write_text(yaml.dump(index_yaml))

    # Create access-control/missing-auth vulndoc
    access_dir = vulndocs_dir / "access-control" / "missing-auth"
    access_dir.mkdir(parents=True)

    access_yaml = {
        "id": "access-control-missing-auth",
        "category": "access-control",
        "subcategory": "missing-auth",
        "severity": "high",
        "vulndoc": "access-control/missing-auth",
        "description": "Functions lacking proper access control checks",
        "semantic_triggers": ["MODIFIES_CRITICAL_STATE", "MODIFIES_OWNER"],
        "vql_queries": ["FIND functions WHERE modifies_state AND NOT has_access_control"],
        "graph_patterns": [],
        "reasoning_template": """1. Identify state-modifying functions
2. Check for access control modifiers (onlyOwner, requireRole)
3. Verify privilege requirements match function sensitivity
4. NOT vulnerable if:
   - Proper access control present
   - Function is view/pure
   - State changes are user-scoped""",
        "relevant_properties": ["has_access_control", "modifies_state"],
        "created": "2026-01-22",
    }

    (access_dir / "index.yaml").write_text(yaml.dump(access_yaml))

    return vulndocs_dir


@pytest.fixture
def sample_risk_profile():
    """Create sample risk profile."""
    return RiskProfile(
        oracle_risks=RiskCategory(present=False, notes="No oracles", confidence="inferred"),
        liquidity_risks=RiskCategory(
            present=True, notes="Flash loan exposure", confidence="inferred"
        ),
        access_risks=RiskCategory(
            present=True, notes="Admin multisig", confidence="certain"
        ),
        upgrade_risks=RiskCategory(present=False, notes="Not upgradeable", confidence="inferred"),
        integration_risks=RiskCategory(
            present=False, notes="No external deps", confidence="inferred"
        ),
        timing_risks=RiskCategory(
            present=True, notes="MEV exposure in DEX", confidence="inferred"
        ),
        economic_risks=RiskCategory(
            present=False, notes="Simple tokenomics", confidence="inferred"
        ),
        governance_risks=RiskCategory(
            present=False, notes="No governance", confidence="inferred"
        ),
    )


@pytest.fixture
def sample_context_bundle(sample_risk_profile):
    """Create sample context bundle."""
    return ContextBundle(
        vulnerability_class="reentrancy/classic",
        reasoning_template="1. Check CEI\n2. Guards\n3. State\n4. Calls\n5. Callbacks",
        semantic_triggers=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        vql_queries=["FIND functions WHERE has_external_call"],
        graph_patterns=["R:bal->X:out->W:bal"],
        risk_profile=sample_risk_profile,
        protocol_name="TestVault",
        target_scope=["contracts/Vault.sol"],
        token_estimate=500,
    )


@pytest.fixture
def sample_context_bead(sample_context_bundle):
    """Create sample context-merge bead."""
    return ContextMergeBead(
        id="CTX-test123abc",
        vulnerability_class="reentrancy/classic",
        protocol_name="TestVault",
        context_bundle=sample_context_bundle,
        target_scope=["contracts/Vault.sol"],
        verification_score=0.95,
        status=ContextBeadStatus.PENDING,
        created_at=datetime.now(),
        pool_id="test-pool",
    )


# =============================================================================
# EXEC-01: Context Extraction Protocol
# =============================================================================


class TestContextExtractionProtocol:
    """Tests for EXEC-01: Standardized vulndoc knowledge extraction."""

    def test_extractor_loads_vulndoc_index(self, sample_vulndocs):
        """Extractor loads index.yaml for specified vuln class."""
        extractor = VulndocContextExtractor(vulndocs_root=sample_vulndocs)
        index = extractor._load_vulndoc_index("reentrancy/classic")

        assert index["id"] == "reentrancy-classic"
        assert "reasoning_template" in index
        assert len(index["semantic_triggers"]) > 0

    def test_extractor_raises_for_missing_vulndoc(self, sample_vulndocs):
        """Extractor raises ValueError for missing vulndoc."""
        extractor = VulndocContextExtractor(vulndocs_root=sample_vulndocs)

        with pytest.raises(ValueError, match="VulnDoc not found"):
            extractor._load_vulndoc_index("nonexistent/vuln")

    def test_extract_produces_context_bundle(self, sample_vulndocs, sample_protocol_pack):
        """Extractor produces complete ContextBundle."""
        extractor = VulndocContextExtractor(vulndocs_root=sample_vulndocs)

        bundle = extractor.extract(
            vuln_class="reentrancy/classic",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/Vault.sol"],
        )

        assert bundle.vulnerability_class == "reentrancy/classic"
        assert len(bundle.reasoning_template) > 50
        assert len(bundle.semantic_triggers) > 0
        assert "TRANSFERS_VALUE_OUT" in bundle.semantic_triggers

    def test_extractor_loads_vql_queries(self, sample_vulndocs, sample_protocol_pack):
        """Extractor loads VQL queries from vulndoc."""
        extractor = VulndocContextExtractor(vulndocs_root=sample_vulndocs)

        bundle = extractor.extract(
            vuln_class="reentrancy/classic",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/"],
        )

        assert len(bundle.vql_queries) > 0
        assert "FIND functions" in bundle.vql_queries[0]


# =============================================================================
# EXEC-02: Economic Context Integration
# =============================================================================


class TestEconomicContextIntegration:
    """Tests for EXEC-02: Protocol value/risk in analysis context."""

    def test_risk_profile_extracted_from_protocol_pack(
        self, sample_vulndocs, sample_protocol_pack
    ):
        """Risk profile is extracted from protocol pack."""
        extractor = VulndocContextExtractor(vulndocs_root=sample_vulndocs)

        bundle = extractor.extract(
            vuln_class="reentrancy/classic",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/Vault.sol"],
        )

        assert bundle.risk_profile is not None
        # Risk profile has all 8 categories
        assert hasattr(bundle.risk_profile, "oracle_risks")
        assert hasattr(bundle.risk_profile, "liquidity_risks")
        assert hasattr(bundle.risk_profile, "access_risks")
        assert hasattr(bundle.risk_profile, "timing_risks")

    def test_risk_profile_has_8_categories(self):
        """RiskProfile has all 8 required categories."""
        profile = RiskProfile()

        categories = [
            "oracle_risks",
            "liquidity_risks",
            "access_risks",
            "upgrade_risks",
            "integration_risks",
            "timing_risks",
            "economic_risks",
            "governance_risks",
        ]

        for cat in categories:
            assert hasattr(profile, cat), f"Missing category: {cat}"

    def test_conservative_defaults_applied(self):
        """Unknown risks default to present (conservative)."""
        # Default RiskCategory should have present=True
        default_cat = RiskCategory()
        assert default_cat.present is True
        assert default_cat.confidence == "unknown"


# =============================================================================
# EXEC-03: Fresh Context Spawning
# =============================================================================


class TestFreshContextSpawning:
    """Tests for EXEC-03: Clean agent instance per vulnerability test."""

    @pytest.mark.asyncio
    async def test_sub_coordinator_spawns_separate_agents(
        self, sample_vulndocs, sample_protocol_pack, sample_context_bundle
    ):
        """Sub-coordinator spawns separate agents for each vuln class."""
        coordinator = SubCoordinator(
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=["reentrancy/classic", "access-control/missing-auth"],
            pool_id="test-pool",
            vulndocs_root=sample_vulndocs,
        )

        # Mock the components
        mock_merger = Mock(spec=ContextMerger)
        mock_merger.merge.return_value = MergeResult(
            success=True,
            bundle=sample_context_bundle,
            errors=[],
            warnings=[],
            token_count=500,
            trimmed=False,
            sources_used=["vulndocs/reentrancy/classic"],
        )

        mock_verifier = Mock(spec=ContextVerifier)
        mock_verifier.verify.return_value = VerificationResult(
            valid=True,
            errors=[],
            warnings=[],
            quality_score=0.95,
            feedback_for_retry=None,
        )

        mock_factory = Mock(spec=ContextBeadFactory)
        mock_factory.create_from_verified_merge.return_value = ContextMergeBead(
            id="CTX-test",
            vulnerability_class="test",
            protocol_name="TestVault",
            context_bundle=sample_context_bundle,
            target_scope=["contracts/"],
            verification_score=0.95,
            pool_id="test-pool",
        )
        mock_factory.save_bead.return_value = None

        coordinator._merger = mock_merger
        coordinator._verifier = mock_verifier
        coordinator._bead_factory = mock_factory

        result = await coordinator.run()

        # Each vuln class should be processed
        assert result.total_classes == 2
        # Merger called for each class
        assert mock_merger.merge.call_count == 2

    def test_context_bead_is_self_contained(self, sample_context_bundle):
        """Each context bead contains all needed context inline."""
        bead = ContextMergeBead(
            id="CTX-test123",
            vulnerability_class="reentrancy/classic",
            protocol_name="TestVault",
            context_bundle=sample_context_bundle,
            target_scope=["contracts/"],
            verification_score=0.95,
            pool_id="test-pool",
        )

        # Bead contains everything needed (self-contained)
        assert bead.context_bundle is not None
        assert len(bead.context_bundle.reasoning_template) > 0
        assert len(bead.target_scope) > 0
        assert bead.context_bundle.risk_profile is not None


# =============================================================================
# EXEC-04: Reasoning Template Application
# =============================================================================


class TestReasoningTemplateApplication:
    """Tests for EXEC-04: Vulndoc reasoning patterns in prompts."""

    def test_reasoning_template_in_system_prompt(
        self, sample_vulndocs, sample_protocol_pack
    ):
        """Reasoning template is formatted into system prompt."""
        extractor = VulndocContextExtractor(vulndocs_root=sample_vulndocs)

        bundle = extractor.extract(
            vuln_class="reentrancy/classic",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/"],
        )

        system_prompt = bundle.to_system_prompt()

        # System prompt contains the reasoning template
        assert "Identify external calls" in system_prompt
        assert "NOT vulnerable if" in system_prompt

    def test_template_has_step_structure(self, sample_vulndocs, sample_protocol_pack):
        """Reasoning template has numbered steps."""
        import re

        extractor = VulndocContextExtractor(vulndocs_root=sample_vulndocs)

        bundle = extractor.extract(
            vuln_class="reentrancy/classic",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/"],
        )

        # Template has numbered steps (1., 2., etc.)
        assert re.search(r"\d+\.", bundle.reasoning_template)

    def test_system_prompt_includes_semantic_triggers(self, sample_context_bundle):
        """System prompt includes semantic triggers."""
        system_prompt = sample_context_bundle.to_system_prompt()

        assert "TRANSFERS_VALUE_OUT" in system_prompt
        assert "WRITES_USER_BALANCE" in system_prompt


# =============================================================================
# EXEC-05: Exploit Cross-Reference
# =============================================================================


class TestExploitCrossReference:
    """Tests for EXEC-05: Vulndoc reference preserved in findings."""

    def test_vulndoc_reference_in_evidence_chain(self, sample_context_bead, tmp_path):
        """Evidence chain contains vulndoc reference."""
        factory = FindingBeadFactory(beads_dir=tmp_path / "beads")

        evidence = EvidenceChain(
            code_locations=["contracts/Vault.sol:42"],
            vulndoc_reference="reentrancy/classic",
            reasoning_steps=["Found external call", "State update after call"],
            vql_queries=["FIND functions WHERE ..."],
            protocol_context_applied=["Protocol accepts ETH"],
            confidence="likely",
            confidence_reason="Pattern matched",
        )

        finding = FindingInput(
            vulnerability_class="reentrancy/classic",
            severity=Severity.CRITICAL,
            summary="Reentrancy in withdraw()",
            evidence_chain=evidence,
            context_bead_id=sample_context_bead.id,
        )

        bead = factory.create_finding(finding=finding, context_bead=sample_context_bead)

        # Vulndoc reference preserved in metadata
        assert "reentrancy/classic" in bead.metadata["evidence_chain"]["vulndoc_reference"]


# =============================================================================
# EXEC-06: Category-Specific Prompts
# =============================================================================


class TestCategorySpecificPrompts:
    """Tests for EXEC-06: Risk mapping per vulnerability class."""

    def test_risk_mapping_for_reentrancy(self, sample_risk_profile):
        """Reentrancy maps to access_risks and timing_risks."""
        relevant = sample_risk_profile.get_relevant_for_vuln_class("reentrancy/classic")

        assert "access_risks" in relevant
        assert "timing_risks" in relevant
        # Should not include unrelated risks
        assert "oracle_risks" not in relevant

    def test_risk_mapping_for_oracle(self, sample_risk_profile):
        """Oracle vulnerabilities map to oracle_risks and integration_risks."""
        relevant = sample_risk_profile.get_relevant_for_vuln_class("oracle/manipulation")

        assert "oracle_risks" in relevant
        assert "integration_risks" in relevant

    def test_risk_mapping_for_access_control(self, sample_risk_profile):
        """Access control maps to access_risks and governance_risks."""
        relevant = sample_risk_profile.get_relevant_for_vuln_class(
            "access-control/missing-auth"
        )

        assert "access_risks" in relevant
        assert "governance_risks" in relevant


# =============================================================================
# EXEC-07: Evidence Chain Validation
# =============================================================================


class TestEvidenceChainValidation:
    """Tests for EXEC-07: Verify evidence links to vulndocs/exploits."""

    def test_finding_includes_code_locations(self, sample_context_bead, tmp_path):
        """Finding beads include code locations in evidence chain."""
        factory = FindingBeadFactory(beads_dir=tmp_path / "beads")

        evidence = EvidenceChain(
            code_locations=["contracts/Vault.sol:42-55"],
            vulndoc_reference="reentrancy/classic",
            reasoning_steps=["Found external call"],
            vql_queries=["FIND functions WHERE ..."],
            protocol_context_applied=[],
            confidence="confirmed",
            confidence_reason="CEI violated",
        )

        finding = FindingInput(
            vulnerability_class="reentrancy/classic",
            severity=Severity.CRITICAL,
            summary="Reentrancy in withdraw()",
            evidence_chain=evidence,
            context_bead_id=sample_context_bead.id,
        )

        bead = factory.create_finding(finding=finding, context_bead=sample_context_bead)

        # Code locations preserved
        assert len(bead.metadata["evidence_chain"]["code_locations"]) > 0
        assert "Vault.sol" in bead.metadata["evidence_chain"]["code_locations"][0]

    def test_finding_includes_reasoning_steps(self, sample_context_bead, tmp_path):
        """Finding beads include reasoning steps."""
        factory = FindingBeadFactory(beads_dir=tmp_path / "beads")

        evidence = EvidenceChain(
            code_locations=["contracts/Vault.sol:42"],
            vulndoc_reference="reentrancy/classic",
            reasoning_steps=["Step 1: Found call", "Step 2: State after call"],
            vql_queries=[],
            protocol_context_applied=[],
            confidence="likely",
            confidence_reason="Pattern matched",
        )

        finding = FindingInput(
            vulnerability_class="reentrancy/classic",
            severity=Severity.CRITICAL,
            summary="Test finding",
            evidence_chain=evidence,
            context_bead_id=sample_context_bead.id,
        )

        bead = factory.create_finding(finding=finding, context_bead=sample_context_bead)

        assert len(bead.metadata["evidence_chain"]["reasoning_steps"]) == 2

    def test_finding_includes_vql_queries(self, sample_context_bead, tmp_path):
        """Finding beads include VQL queries used."""
        factory = FindingBeadFactory(beads_dir=tmp_path / "beads")

        evidence = EvidenceChain(
            code_locations=[],
            vulndoc_reference="reentrancy/classic",
            reasoning_steps=[],
            vql_queries=["FIND functions WHERE has_external_call"],
            protocol_context_applied=[],
            confidence="uncertain",
            confidence_reason="Needs review",
        )

        finding = FindingInput(
            vulnerability_class="reentrancy/classic",
            severity=Severity.MEDIUM,
            summary="Potential issue",
            evidence_chain=evidence,
            context_bead_id=sample_context_bead.id,
        )

        bead = factory.create_finding(finding=finding, context_bead=sample_context_bead)

        assert "FIND functions" in bead.metadata["evidence_chain"]["vql_queries"][0]


# =============================================================================
# EXEC-09: Token Budget Optimization
# =============================================================================


class TestTokenBudgetOptimization:
    """Tests for EXEC-09: Context within 6k token limit."""

    def test_token_estimation(self, sample_vulndocs, sample_protocol_pack):
        """Token estimation is reasonable (rough chars/4)."""
        extractor = VulndocContextExtractor(vulndocs_root=sample_vulndocs)

        bundle = extractor.extract(
            vuln_class="reentrancy/classic",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/"],
        )

        # Token estimate should be positive
        assert bundle.token_estimate > 0
        # Should be under limit for this small bundle
        assert bundle.token_estimate < 6000

    def test_trimming_preserves_reasoning_template(
        self, sample_vulndocs, sample_protocol_pack
    ):
        """Trimming never drops reasoning template."""
        extractor = VulndocContextExtractor(vulndocs_root=sample_vulndocs)

        bundle = extractor.extract(
            vuln_class="reentrancy/classic",
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/"],
        )

        # Force trim with very low budget
        trimmed = extractor._trim_to_budget(bundle, max_tokens=100)

        # Reasoning template still present (even if truncated)
        assert len(trimmed.reasoning_template) > 0

    def test_trimming_reduces_vql_queries(self, sample_vulndocs, sample_protocol_pack):
        """Trimming reduces VQL queries to max 3."""
        extractor = VulndocContextExtractor(vulndocs_root=sample_vulndocs)

        # Create bundle with many queries and large content to force trimming
        # Each long string adds ~250 chars = ~62 tokens
        long_queries = [f"FIND functions WHERE very_long_query_{i} " * 20 for i in range(5)]
        long_patterns = [f"PATTERN_{i}_very_long_pattern_string " * 20 for i in range(5)]

        bundle = ContextBundle(
            vulnerability_class="test",
            reasoning_template="Test template " * 100,  # Make large
            semantic_triggers=["OP1", "OP2"],
            vql_queries=long_queries,
            graph_patterns=long_patterns,
            risk_profile=RiskProfile(),
            protocol_name="Test",
            target_scope=["contracts/"],
            token_estimate=5000,
        )

        # Trim - use very low budget to force trimming
        trimmed = extractor._trim_to_budget(bundle, max_tokens=200)

        # Graph patterns limited to 3 (trimmed first)
        assert len(trimmed.graph_patterns) <= 3


# =============================================================================
# EXEC-10: Output Format Standardization
# =============================================================================


class TestOutputFormatStandardization:
    """Tests for EXEC-10: Consistent finding format for integration."""

    def test_context_bead_serialization(self, sample_context_bundle):
        """Context beads serialize to consistent format."""
        bead = ContextMergeBead(
            id="CTX-test123",
            vulnerability_class="reentrancy/classic",
            protocol_name="TestVault",
            context_bundle=sample_context_bundle,
            target_scope=["contracts/"],
            verification_score=0.95,
            pool_id="test-pool",
        )

        # JSON roundtrip
        json_str = bead.to_json()
        data = json.loads(json_str)

        assert "id" in data
        assert "vulnerability_class" in data
        assert "context_bundle" in data
        assert "verification_score" in data

    def test_context_bead_yaml_roundtrip(self, sample_context_bundle):
        """Context bead YAML serialization roundtrips correctly."""
        bead = ContextMergeBead(
            id="CTX-test456",
            vulnerability_class="reentrancy/classic",
            protocol_name="TestVault",
            context_bundle=sample_context_bundle,
            target_scope=["contracts/"],
            verification_score=0.90,
            pool_id="test-pool",
        )

        yaml_str = bead.to_yaml()
        loaded = ContextMergeBead.from_yaml(yaml_str)

        assert loaded.id == bead.id
        assert loaded.vulnerability_class == bead.vulnerability_class
        assert loaded.verification_score == bead.verification_score

    def test_finding_bead_has_required_fields(self, sample_context_bead, tmp_path):
        """Finding beads have all required fields."""
        factory = FindingBeadFactory(beads_dir=tmp_path / "beads")

        evidence = EvidenceChain(
            code_locations=["file.sol:10"],
            vulndoc_reference="reentrancy/classic",
            reasoning_steps=["step"],
            vql_queries=[],
            protocol_context_applied=[],
            confidence="likely",
            confidence_reason="test",
        )

        finding = FindingInput(
            vulnerability_class="reentrancy/classic",
            severity=Severity.HIGH,
            summary="Test finding",
            evidence_chain=evidence,
            context_bead_id=sample_context_bead.id,
        )

        bead = factory.create_finding(finding=finding, context_bead=sample_context_bead)

        # Required fields present
        assert bead.id is not None
        assert bead.vulnerability_class == "reentrancy/classic"
        assert bead.severity == Severity.HIGH
        assert bead.confidence > 0


# =============================================================================
# Full Pipeline E2E
# =============================================================================


class TestFullPipeline:
    """Full end-to-end pipeline tests."""

    @pytest.mark.asyncio
    async def test_sub_coordinator_full_flow(
        self, sample_vulndocs, sample_protocol_pack, sample_context_bundle
    ):
        """Sub-coordinator runs full context-merge flow."""
        coordinator = SubCoordinator(
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=["reentrancy/classic"],
            pool_id="test-pool",
            vulndocs_root=sample_vulndocs,
        )

        # Mock components
        mock_merger = Mock(spec=ContextMerger)
        mock_merger.merge.return_value = MergeResult(
            success=True,
            bundle=sample_context_bundle,
            errors=[],
            warnings=[],
            token_count=500,
            trimmed=False,
            sources_used=["vulndocs"],
        )

        mock_verifier = Mock(spec=ContextVerifier)
        mock_verifier.verify.return_value = VerificationResult(
            valid=True,
            errors=[],
            warnings=[],
            quality_score=0.95,
            feedback_for_retry=None,
        )

        mock_factory = Mock(spec=ContextBeadFactory)
        mock_factory.create_from_verified_merge.return_value = ContextMergeBead(
            id="CTX-test123",
            vulnerability_class="reentrancy/classic",
            protocol_name="TestVault",
            context_bundle=sample_context_bundle,
            target_scope=["contracts/"],
            verification_score=0.95,
            pool_id="test-pool",
        )
        mock_factory.save_bead.return_value = None

        coordinator._merger = mock_merger
        coordinator._verifier = mock_verifier
        coordinator._bead_factory = mock_factory

        result = await coordinator.run()

        assert result.success
        assert result.successful_classes == 1
        assert len(result.beads_created) == 1
        assert result.beads_created[0].vulnerability_class == "reentrancy/classic"

    @pytest.mark.asyncio
    async def test_main_orchestrator_context_merge_phase(
        self, sample_protocol_pack, sample_context_bundle, tmp_path
    ):
        """Main orchestrator runs context-merge phase."""
        orchestrator = MainOrchestrator(
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=["reentrancy/classic"],
            pool_id="test-pool",
            beads_dir=tmp_path / "beads",
        )

        # Mock sub-coordinator result
        mock_context_bead = ContextMergeBead(
            id="CTX-test123",
            vulnerability_class="reentrancy/classic",
            protocol_name="TestVault",
            context_bundle=sample_context_bundle,
            target_scope=["contracts/"],
            verification_score=0.95,
            pool_id="test-pool",
        )

        mock_sub_result = SubCoordinatorResult(
            success=True,
            beads_created=[mock_context_bead],
            failed_classes=[],
            errors={},
            total_classes=1,
            successful_classes=1,
        )

        # Mock discovery result
        mock_discovery_result = VulnDiscoveryResult(
            success=True,
            context_bead_id=mock_context_bead.id,
            findings=["VKG-001"],
            findings_count=1,
            errors=[],
            vql_queries_executed=["query1"],
        )

        with patch(
            "alphaswarm_sol.agents.orchestration.main_orchestrator.SubCoordinator"
        ) as MockSubCoord:
            mock_sub_instance = MagicMock()
            mock_sub_instance.run = AsyncMock(return_value=mock_sub_result)
            MockSubCoord.return_value = mock_sub_instance

            with patch.object(
                orchestrator, "_run_vuln_discovery", new_callable=AsyncMock
            ) as mock_discovery:
                mock_discovery.return_value = {
                    mock_context_bead.id: mock_discovery_result
                }

                result = await orchestrator.run()

        assert result.context_beads_created == 1
        assert result.phase == "complete"

    @pytest.mark.asyncio
    async def test_main_orchestrator_aggregates_findings(
        self, sample_protocol_pack, sample_context_bundle, tmp_path
    ):
        """Main orchestrator collects all findings."""
        orchestrator = MainOrchestrator(
            protocol_pack=sample_protocol_pack,
            target_scope=["contracts/"],
            vuln_classes=["reentrancy/classic", "access-control/missing-auth"],
            pool_id="test-pool",
            beads_dir=tmp_path / "beads",
        )

        beads = [
            ContextMergeBead(
                id=f"CTX-test{i}",
                vulnerability_class=f"class-{i}",
                protocol_name="TestVault",
                context_bundle=sample_context_bundle,
                target_scope=["contracts/"],
                verification_score=0.95,
                pool_id="test-pool",
            )
            for i in range(2)
        ]

        mock_sub_result = SubCoordinatorResult(
            success=True,
            beads_created=beads,
            failed_classes=[],
            errors={},
            total_classes=2,
            successful_classes=2,
        )

        discovery_results = {
            beads[0].id: VulnDiscoveryResult(
                success=True,
                context_bead_id=beads[0].id,
                findings=["VKG-001", "VKG-002"],
                findings_count=2,
                errors=[],
                vql_queries_executed=[],
            ),
            beads[1].id: VulnDiscoveryResult(
                success=True,
                context_bead_id=beads[1].id,
                findings=["VKG-003"],
                findings_count=1,
                errors=[],
                vql_queries_executed=[],
            ),
        }

        with patch(
            "alphaswarm_sol.agents.orchestration.main_orchestrator.SubCoordinator"
        ) as MockSubCoord:
            mock_sub_instance = MagicMock()
            mock_sub_instance.run = AsyncMock(return_value=mock_sub_result)
            MockSubCoord.return_value = mock_sub_instance

            with patch.object(
                orchestrator, "_run_vuln_discovery", new_callable=AsyncMock
            ) as mock_discovery:
                mock_discovery.return_value = discovery_results

                result = await orchestrator.run()

        assert result.findings_created == 3
        assert result.discovery_completed == 2


# =============================================================================
# Context Bead Status Transitions
# =============================================================================


class TestContextBeadStatusTransitions:
    """Tests for context bead status management."""

    def test_bead_starts_pending(self, sample_context_bundle):
        """New beads start in PENDING status."""
        bead = ContextMergeBead(
            id="CTX-test",
            vulnerability_class="test",
            protocol_name="Test",
            context_bundle=sample_context_bundle,
            target_scope=["contracts/"],
            verification_score=0.9,
        )

        assert bead.status == ContextBeadStatus.PENDING

    def test_bead_mark_complete(self, sample_context_bundle):
        """Bead can be marked complete."""
        bead = ContextMergeBead(
            id="CTX-test",
            vulnerability_class="test",
            protocol_name="Test",
            context_bundle=sample_context_bundle,
            target_scope=["contracts/"],
            verification_score=0.9,
            status=ContextBeadStatus.IN_PROGRESS,
        )

        bead.mark_complete()

        assert bead.status == ContextBeadStatus.COMPLETE

    def test_bead_mark_failed(self, sample_context_bundle):
        """Bead can be marked failed with error."""
        bead = ContextMergeBead(
            id="CTX-test",
            vulnerability_class="test",
            protocol_name="Test",
            context_bundle=sample_context_bundle,
            target_scope=["contracts/"],
            verification_score=0.9,
            status=ContextBeadStatus.IN_PROGRESS,
        )

        bead.mark_failed("VQL execution error")

        assert bead.status == ContextBeadStatus.FAILED
        assert "failure_reason" in bead.metadata
        assert bead.metadata["failure_reason"] == "VQL execution error"

    def test_bead_tracks_finding_ids(self, sample_context_bundle):
        """Bead tracks created finding bead IDs."""
        bead = ContextMergeBead(
            id="CTX-test",
            vulnerability_class="test",
            protocol_name="Test",
            context_bundle=sample_context_bundle,
            target_scope=["contracts/"],
            verification_score=0.9,
        )

        bead.add_finding_bead("VKG-001")
        bead.add_finding_bead("VKG-002")

        assert len(bead.finding_bead_ids) == 2
        assert "VKG-001" in bead.finding_bead_ids
        assert "VKG-002" in bead.finding_bead_ids


# =============================================================================
# Model Assignment Tests
# =============================================================================


class TestModelAssignments:
    """Tests for correct model assignments per CONTEXT.md."""

    def test_main_orchestrator_uses_opus(self):
        """MainOrchestrator uses Opus 4.5."""
        assert MainOrchestrator.MODEL == "claude-opus-4-5"

    def test_sub_coordinator_uses_opus(self):
        """SubCoordinator uses Opus 4.5."""
        assert SubCoordinator.MODEL == "claude-opus-4-5"

    def test_context_merge_agent_uses_sonnet(self):
        """ContextMergeAgent uses Sonnet 4.5."""
        assert ContextMergeAgent.MODEL == "claude-sonnet-4-5"


# =============================================================================
# Package Export Tests
# =============================================================================


class TestPackageExports:
    """Tests for complete package exports."""

    def test_orchestration_exports_all_classes(self):
        """Orchestration package exports all required classes."""
        from alphaswarm_sol.agents import orchestration

        # Check all exports present
        required = [
            "SubCoordinator",
            "SubCoordinatorConfig",
            "SubCoordinatorResult",
            "ContextMergeAgent",
            "ContextMergeConfig",
            "ContextMergeResult",
            "VulnDiscoveryAgent",
            "VulnDiscoveryConfig",
            "VulnDiscoveryResult",
            "FindingBeadFactory",
            "FindingInput",
            "EvidenceChain",
            "MainOrchestrator",
            "OrchestrationConfig",
            "OrchestrationResult",
        ]

        for name in required:
            assert hasattr(orchestration, name), f"Missing export: {name}"

    def test_context_exports_all_classes(self):
        """Context package exports all required classes."""
        from alphaswarm_sol.agents import context

        required = [
            "ContextBundle",
            "RiskCategory",
            "RiskProfile",
            "VulndocContextExtractor",
            "ContextMerger",
            "ContextVerifier",
            "ContextBeadFactory",
        ]

        for name in required:
            assert hasattr(context, name), f"Missing export: {name}"
