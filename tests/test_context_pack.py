"""Integration tests for Protocol Context Pack.

Tests the full workflow of the Protocol Context Pack system:
- Schema serialization/deserialization
- Storage save/load operations
- Code analysis extraction
- Builder orchestration
- Evidence and bead integration
- CLI commands (via programmatic invocation)

Per 03-CONTEXT.md:
- "LLM-generated, not human-authored"
- "Confidence levels on each field"
- "Accepted risks auto-filtered from findings"
- "Each bead inherits relevant context pack sections"
"""

import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict

import pytest

from alphaswarm_sol.context import (
    # Schema and types
    ProtocolContextPack,
    ContextPackStorage,
    ContextPackBuilder,
    BuildConfig,
    Confidence,
    Role,
    Assumption,
    Invariant,
    OffchainInput,
    ValueFlow,
    AcceptedRisk,
    # Integrations
    EvidenceContextExtension,
    EvidenceContextProvider,
    BeadContext,
    BeadContextProvider,
)
from alphaswarm_sol.context.parser import CodeAnalyzer, AnalysisResult


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_role() -> Role:
    """Create a sample role for testing."""
    return Role(
        name="admin",
        capabilities=["pause", "upgrade", "set_fees"],
        trust_assumptions=["Admin is trusted multisig", "Admin will not rug users"],
        confidence=Confidence.CERTAIN,
        description="Protocol administrator",
        addresses=["0x1234..."],
    )


@pytest.fixture
def sample_assumption() -> Assumption:
    """Create a sample assumption for testing."""
    return Assumption(
        description="Oracle prices are accurate within 1%",
        category="price",
        affects_functions=["swap", "liquidate", "borrow"],
        confidence=Confidence.INFERRED,
        source="whitepaper",
        tags=["oracle", "price"],
    )


@pytest.fixture
def sample_invariant() -> Invariant:
    """Create a sample invariant for testing."""
    return Invariant(
        formal={"what": "totalSupply", "must": "lte", "value": "maxSupply"},
        natural_language="Total supply must never exceed max supply",
        confidence=Confidence.CERTAIN,
        source="ERC20 specification",
        category="supply",
        critical=True,
    )


@pytest.fixture
def sample_offchain_input() -> OffchainInput:
    """Create a sample off-chain input for testing."""
    return OffchainInput(
        name="Chainlink ETH/USD",
        input_type="oracle",
        description="Price feed for ETH/USD",
        trust_assumptions=["Oracle nodes are decentralized"],
        affects_functions=["liquidate", "borrow"],
        confidence=Confidence.CERTAIN,
        endpoints=["0xABCD..."],
    )


@pytest.fixture
def sample_value_flow() -> ValueFlow:
    """Create a sample value flow for testing."""
    return ValueFlow(
        name="liquidation_reward",
        from_role="protocol",
        to_role="liquidator",
        asset="ETH",
        conditions=["health_factor < 1", "debt > 0"],
        confidence=Confidence.INFERRED,
        description="Liquidator receives bonus for liquidating unhealthy positions",
    )


@pytest.fixture
def sample_accepted_risk() -> AcceptedRisk:
    """Create a sample accepted risk for testing."""
    return AcceptedRisk(
        description="Admin can pause all transfers",
        reason="Emergency circuit breaker by design",
        affects_functions=["transfer", "transferFrom"],
        documented_in="audit_report_v1.pdf",
        severity="medium",
        patterns=["access-control-001"],
    )


@pytest.fixture
def sample_pack(
    sample_role, sample_assumption, sample_invariant, sample_offchain_input,
    sample_value_flow, sample_accepted_risk
) -> ProtocolContextPack:
    """Create a fully populated sample context pack."""
    return ProtocolContextPack(
        protocol_name="TestProtocol",
        protocol_type="lending",
        version="1.0",
        schema_version="1.0",
        auto_generated=True,
        reviewed=False,
        roles=[sample_role],
        assumptions=[sample_assumption],
        invariants=[sample_invariant],
        offchain_inputs=[sample_offchain_input],
        value_flows=[sample_value_flow],
        accepted_risks=[sample_accepted_risk],
        critical_functions=["liquidate", "borrow", "repay"],
        tokenomics_summary="Security-focused lending protocol",
        security_model={"type": "permissioned", "admin_multisig": True},
        governance={"voting_threshold": "50%", "timelock": "48h"},
    )


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for storage tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Test ProtocolContextPack Schema
# =============================================================================


class TestContextPackSchema:
    """Test ProtocolContextPack schema."""

    def test_create_minimal_pack(self):
        """Create context pack with minimal fields."""
        pack = ProtocolContextPack(protocol_name="TestProtocol")

        assert pack.protocol_name == "TestProtocol"
        assert pack.version == "1.0"
        assert pack.auto_generated is True
        assert pack.reviewed is False
        assert len(pack.roles) == 0
        assert len(pack.assumptions) == 0

    def test_create_full_pack(self, sample_pack):
        """Create context pack with all fields."""
        pack = sample_pack

        assert pack.protocol_name == "TestProtocol"
        assert pack.protocol_type == "lending"
        assert len(pack.roles) == 1
        assert len(pack.assumptions) == 1
        assert len(pack.invariants) == 1
        assert len(pack.offchain_inputs) == 1
        assert len(pack.value_flows) == 1
        assert len(pack.accepted_risks) == 1
        assert len(pack.critical_functions) == 3

    def test_to_dict_from_dict_roundtrip(self, sample_pack):
        """Test serialization roundtrip preserves data."""
        pack = sample_pack

        # Serialize to dict
        data = pack.to_dict()

        # Verify dict has expected structure
        assert data["protocol_name"] == "TestProtocol"
        assert data["protocol_type"] == "lending"
        assert len(data["roles"]) == 1
        assert len(data["assumptions"]) == 1

        # Deserialize from dict
        restored = ProtocolContextPack.from_dict(data)

        # Verify restored pack matches original
        assert restored.protocol_name == pack.protocol_name
        assert restored.protocol_type == pack.protocol_type
        assert len(restored.roles) == len(pack.roles)
        assert restored.roles[0].name == pack.roles[0].name
        assert len(restored.assumptions) == len(pack.assumptions)
        assert restored.assumptions[0].description == pack.assumptions[0].description

    def test_get_section(self, sample_pack):
        """Test targeted section retrieval."""
        pack = sample_pack

        # Get roles section
        roles_section = pack.get_section("roles")
        assert roles_section is not None
        assert "roles" in roles_section
        assert len(roles_section["roles"]) == 1

        # Get assumptions section
        assumptions_section = pack.get_section("assumptions")
        assert assumptions_section is not None
        assert "assumptions" in assumptions_section

        # Get metadata section
        metadata = pack.get_section("metadata")
        assert metadata is not None
        assert metadata["protocol_name"] == "TestProtocol"

        # Invalid section returns None
        invalid = pack.get_section("invalid_section")
        assert invalid is None

    def test_token_estimate(self, sample_pack):
        """Test token estimation for context budgeting."""
        pack = sample_pack

        tokens = pack.token_estimate()

        # Should be a positive number
        assert tokens > 0
        # Rough estimate: 4 chars per token, sample pack should be 200-2000 tokens
        assert tokens < 10000  # Sanity check

    def test_get_relevant_assumptions(self, sample_pack):
        """Test getting assumptions for specific functions."""
        pack = sample_pack

        # Function that should have relevant assumptions
        relevant = pack.get_relevant_assumptions("liquidate")
        assert len(relevant) == 1
        assert relevant[0].description == "Oracle prices are accurate within 1%"

        # Function not in any assumption
        not_relevant = pack.get_relevant_assumptions("unknown_function")
        assert len(not_relevant) == 0

    def test_is_accepted_risk(self, sample_pack):
        """Test accepted risk checking."""
        pack = sample_pack

        # Matching description
        assert pack.is_accepted_risk(
            description="Admin can pause all transfers",
            function_name="transfer"
        ) is True

        # Non-matching
        assert pack.is_accepted_risk(
            description="Random vulnerability",
            function_name="unknown"
        ) is False

    def test_is_critical_function(self, sample_pack):
        """Test critical function checking."""
        pack = sample_pack

        assert pack.is_critical_function("liquidate") is True
        assert pack.is_critical_function("borrow") is True
        assert pack.is_critical_function("unknown") is False

    def test_confidence_summary(self, sample_pack):
        """Test confidence level summary."""
        pack = sample_pack

        summary = pack.confidence_summary()

        assert "roles" in summary
        assert "assumptions" in summary
        assert "invariants" in summary

        # Check our sample data
        assert summary["roles"]["certain"] == 1
        assert summary["assumptions"]["inferred"] == 1
        assert summary["invariants"]["certain"] == 1

    def test_merge_packs(self, sample_pack, sample_role, sample_assumption):
        """Test merging two context packs."""
        pack1 = sample_pack

        # Create a second pack with different data
        new_role = Role(
            name="keeper",
            capabilities=["execute", "relay"],
            trust_assumptions=["Keeper is automated"],
            confidence=Confidence.INFERRED,
        )
        new_assumption = Assumption(
            description="Network latency is acceptable",
            category="time",
            affects_functions=["execute"],
            confidence=Confidence.CERTAIN,
            source="docs",
        )
        pack2 = ProtocolContextPack(
            protocol_name="",
            roles=[new_role],
            assumptions=[new_assumption],
        )

        merged = pack1.merge(pack2)

        # Should have combined roles and assumptions
        assert len(merged.roles) == 2
        role_names = [r.name for r in merged.roles]
        assert "admin" in role_names
        assert "keeper" in role_names

        assert len(merged.assumptions) == 2


# =============================================================================
# Test ContextPackStorage
# =============================================================================


class TestContextPackStorage:
    """Test ContextPackStorage operations."""

    def test_save_and_load(self, sample_pack, temp_storage_dir):
        """Test save and load roundtrip."""
        storage = ContextPackStorage(temp_storage_dir)

        # Save
        saved_path = storage.save(sample_pack, "test_protocol")
        assert saved_path.exists()

        # Load
        loaded = storage.load("test_protocol")
        assert loaded is not None
        assert loaded.protocol_name == sample_pack.protocol_name
        assert len(loaded.roles) == len(sample_pack.roles)

    def test_list_packs(self, sample_pack, temp_storage_dir):
        """Test listing stored packs."""
        storage = ContextPackStorage(temp_storage_dir)

        # Initially empty
        assert len(storage.list_packs()) == 0

        # Save a pack
        storage.save(sample_pack, "protocol_a")

        # Now has one
        packs = storage.list_packs()
        assert len(packs) == 1
        assert "protocol_a" in packs

        # Save another
        sample_pack.protocol_name = "Protocol B"
        storage.save(sample_pack, "protocol_b")

        packs = storage.list_packs()
        assert len(packs) == 2

    def test_exists_and_delete(self, sample_pack, temp_storage_dir):
        """Test exists and delete operations."""
        storage = ContextPackStorage(temp_storage_dir)

        # Doesn't exist yet
        assert storage.exists("test_protocol") is False

        # Save
        storage.save(sample_pack, "test_protocol")
        assert storage.exists("test_protocol") is True

        # Delete
        result = storage.delete("test_protocol")
        assert result is True
        assert storage.exists("test_protocol") is False

        # Delete non-existent
        result = storage.delete("non_existent")
        assert result is False

    def test_load_section(self, sample_pack, temp_storage_dir):
        """Test loading individual sections."""
        storage = ContextPackStorage(temp_storage_dir)
        storage.save(sample_pack, "test_protocol")

        # Load roles section
        roles = storage.load_section("test_protocol", "roles")
        assert roles is not None
        assert "roles" in roles

        # Load assumptions section
        assumptions = storage.load_section("test_protocol", "assumptions")
        assert assumptions is not None
        assert "assumptions" in assumptions

    def test_update_section(self, sample_pack, temp_storage_dir):
        """Test updating individual sections."""
        storage = ContextPackStorage(temp_storage_dir)
        storage.save(sample_pack, "test_protocol")

        # Update roles section
        new_roles_data = {
            "roles": [
                {
                    "name": "new_admin",
                    "capabilities": ["admin"],
                    "trust_assumptions": [],
                    "confidence": "certain",
                    "description": "",
                    "addresses": [],
                }
            ]
        }

        result = storage.update_section("test_protocol", "roles", new_roles_data)
        assert result is True

        # Reload and verify
        loaded = storage.load("test_protocol")
        assert len(loaded.roles) == 1
        assert loaded.roles[0].name == "new_admin"

    def test_get_summary(self, sample_pack, temp_storage_dir):
        """Test getting storage summary."""
        storage = ContextPackStorage(temp_storage_dir)

        # Save multiple packs
        storage.save(sample_pack, "protocol_a")
        sample_pack.protocol_name = "Protocol B"
        sample_pack.reviewed = True
        storage.save(sample_pack, "protocol_b")

        summary = storage.get_summary()

        assert summary["total"] == 2
        assert len(summary["packs"]) == 2

        # Check pack details
        pack_names = [p["name"] for p in summary["packs"]]
        assert "protocol_a" in pack_names
        assert "protocol_b" in pack_names


# =============================================================================
# Test CodeAnalyzer
# =============================================================================


class TestCodeAnalyzer:
    """Test CodeAnalyzer extraction."""

    def test_operation_assumption_mapping(self):
        """Test operation to assumption mapping exists."""
        from alphaswarm_sol.context.parser import OPERATION_ASSUMPTIONS

        # Should have mappings for key operations
        assert "READS_ORACLE" in OPERATION_ASSUMPTIONS
        assert "CALLS_UNTRUSTED" in OPERATION_ASSUMPTIONS
        assert "READS_EXTERNAL_VALUE" in OPERATION_ASSUMPTIONS

        # Each mapping should be a list of Assumption objects
        oracle_assumptions = OPERATION_ASSUMPTIONS["READS_ORACLE"]
        assert len(oracle_assumptions) > 0
        assert isinstance(oracle_assumptions[0], Assumption)

    def test_role_capability_mapping(self):
        """Test role capability detection mapping exists."""
        from alphaswarm_sol.context.parser import ROLE_CAPABILITIES

        # Should have mappings for common modifiers
        assert any("owner" in key.lower() for key in ROLE_CAPABILITIES.keys())
        assert any("admin" in key.lower() for key in ROLE_CAPABILITIES.keys())

        # Each mapping is a tuple: (role_name, [capabilities])
        for modifier, mapping in ROLE_CAPABILITIES.items():
            assert isinstance(mapping, tuple)
            assert len(mapping) == 2
            role_name, capabilities = mapping
            assert isinstance(role_name, str)
            assert isinstance(capabilities, list)


# =============================================================================
# Test Evidence Integration
# =============================================================================


class TestEvidenceIntegration:
    """Test evidence packet integration."""

    def test_evidence_context_provider(self, sample_pack):
        """Test getting context for findings."""
        provider = EvidenceContextProvider(sample_pack)

        # Get context using the existing API
        ext = provider.get_context_for_finding(
            function_name="liquidate",
            vulnerability_class="reentrancy",
            semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )

        # Should return EvidenceContextExtension
        assert isinstance(ext, EvidenceContextExtension)
        # Should have relevant assumptions (liquidate is in our sample)
        assert len(ext.relevant_assumptions) > 0 or len(ext.protocol_context) > 0

    def test_accepted_risk_check(self, sample_pack):
        """Test accepted risk filtering."""
        provider = EvidenceContextProvider(sample_pack)

        # Finding that matches accepted risk
        is_accepted, reason = provider.check_accepted_risk(
            finding_description="Admin can pause all transfers",
            function_name="transfer",
        )

        assert is_accepted is True
        assert len(reason) > 0

        # Finding that doesn't match
        is_accepted, reason = provider.check_accepted_risk(
            finding_description="Reentrancy vulnerability",
            function_name="withdraw",
        )

        assert is_accepted is False

    def test_evidence_context_extension_to_dict(self, sample_pack):
        """Test EvidenceContextExtension serialization."""
        ext = EvidenceContextExtension(
            protocol_context=["Lending protocol with flash loans"],
            relevant_assumptions=["Oracle provides accurate prices"],
            violated_assumptions=["Oracle cannot be manipulated"],
            offchain_dependencies=["Chainlink ETH/USD"],
            business_impact="User funds at risk due to price manipulation",
            is_accepted_risk=False,
        )

        data = ext.to_dict()

        assert "protocol_context" in data
        assert "assumptions" in data  # relevant_assumptions mapped to assumptions
        assert "violated_assumptions" in data
        assert "offchain_inputs" in data  # offchain_dependencies mapped to offchain_inputs
        assert "business_impact" in data

    def test_check_violated_assumptions(self, sample_pack):
        """Test checking for violated assumptions."""
        provider = EvidenceContextProvider(sample_pack)

        # Check for violations with oracle-related operations
        violated = provider.check_violated_assumptions(
            finding_description="Oracle price manipulation vulnerability",
            semantic_ops=["READS_ORACLE"],
        )

        # Should find the oracle-related assumption as potentially violated
        assert len(violated) > 0


# =============================================================================
# Test Bead Integration
# =============================================================================


class TestBeadIntegration:
    """Test bead context inheritance."""

    def test_bead_context_provider(self, sample_pack):
        """Test getting context for beads."""
        provider = BeadContextProvider(sample_pack)

        # Get context using the existing API
        ctx = provider.get_context_for_bead(
            vulnerability_class="reentrancy",
            function_name="liquidate",
            semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            max_tokens=2000,
        )

        assert isinstance(ctx, BeadContext)
        # Should have protocol info
        assert ctx.protocol_name == "TestProtocol"
        assert ctx.protocol_type == "lending"

    def test_bead_context_to_prompt_section(self, sample_pack):
        """Test bead context LLM formatting."""
        provider = BeadContextProvider(sample_pack)

        ctx = provider.get_context_for_bead(
            vulnerability_class="oracle-manipulation",
            function_name="liquidate",
            semantic_ops=["READS_ORACLE"],
        )

        prompt = ctx.to_prompt_section()

        assert isinstance(prompt, str)
        assert "Protocol Context" in prompt
        assert "TestProtocol" in prompt

    def test_bead_context_to_dict(self, sample_pack):
        """Test bead context serialization."""
        provider = BeadContextProvider(sample_pack)

        ctx = provider.get_context_for_bead(
            vulnerability_class="access-control",
            function_name="transfer",
            semantic_ops=["CHECKS_PERMISSION"],
        )

        ctx_dict = ctx.to_dict()

        assert "protocol_name" in ctx_dict
        assert "protocol_type" in ctx_dict
        assert "relevant_roles" in ctx_dict
        assert "relevant_assumptions" in ctx_dict
        assert "relevant_invariants" in ctx_dict
        assert "offchain_dependencies" in ctx_dict

    def test_bead_context_has_context(self, sample_pack):
        """Test BeadContext.has_context() method."""
        ctx = BeadContext(
            protocol_name="TestProtocol",
            protocol_type="lending",
        )
        assert ctx.has_context() is True

        empty_ctx = BeadContext()
        assert empty_ctx.has_context() is False


# =============================================================================
# Test Context Pack Builder
# =============================================================================


class TestContextPackBuilder:
    """Test ContextPackBuilder."""

    def test_build_minimal(self, temp_storage_dir):
        """Test building context pack with minimal input."""
        from alphaswarm_sol.kg.schema import KnowledgeGraph

        # Create minimal graph
        graph = KnowledgeGraph()

        builder = ContextPackBuilder(
            graph=graph,
            project_path=temp_storage_dir,
            config=BuildConfig(
                protocol_name="MinimalProtocol",
                include_code_analysis=True,
                include_doc_parsing=False,
            ),
        )

        result = asyncio.run(builder.build())

        # Should succeed even with empty graph
        assert result.pack is not None
        assert result.pack.protocol_name == "MinimalProtocol"
        assert result.build_time >= 0

    def test_build_config_to_dict(self):
        """Test BuildConfig serialization."""
        config = BuildConfig(
            protocol_name="TestProtocol",
            protocol_type="lending",
            include_code_analysis=True,
            include_doc_parsing=True,
            additional_doc_sources=["https://docs.example.com"],
        )

        data = config.to_dict()

        assert data["protocol_name"] == "TestProtocol"
        assert data["protocol_type"] == "lending"
        assert data["include_code_analysis"] is True
        assert len(data["additional_doc_sources"]) == 1

    def test_build_result_properties(self, temp_storage_dir):
        """Test BuildResult properties."""
        from alphaswarm_sol.kg.schema import KnowledgeGraph

        graph = KnowledgeGraph()

        builder = ContextPackBuilder(
            graph=graph,
            project_path=temp_storage_dir,
            config=BuildConfig(protocol_name="Test"),
        )

        result = asyncio.run(builder.build())

        # Test properties
        assert hasattr(result, "has_conflicts")
        assert result.has_conflicts is False

        # Test to_dict
        data = result.to_dict()
        assert "pack" in data
        assert "warnings" in data
        assert "build_time" in data


# =============================================================================
# Test Foundation Types
# =============================================================================


class TestFoundationTypes:
    """Test foundation type behaviors."""

    def test_confidence_ordering(self):
        """Test confidence level comparison."""
        assert Confidence.UNKNOWN < Confidence.INFERRED
        assert Confidence.INFERRED < Confidence.CERTAIN

    def test_confidence_from_string(self):
        """Test confidence parsing from strings."""
        assert Confidence.from_string("certain") == Confidence.CERTAIN
        assert Confidence.from_string("INFERRED") == Confidence.INFERRED
        assert Confidence.from_string("unknown") == Confidence.UNKNOWN

        # Test aliases
        assert Confidence.from_string("high") == Confidence.CERTAIN
        assert Confidence.from_string("medium") == Confidence.INFERRED
        assert Confidence.from_string("low") == Confidence.UNKNOWN

    def test_role_has_capability(self, sample_role):
        """Test role capability checking."""
        assert sample_role.has_capability("pause") is True
        assert sample_role.has_capability("PAUSE") is True  # Case insensitive
        assert sample_role.has_capability("mint") is False

    def test_assumption_affects_function(self, sample_assumption):
        """Test assumption function relevance."""
        assert sample_assumption.affects_function("swap") is True
        assert sample_assumption.affects_function("liquidate") is True
        assert sample_assumption.affects_function("unknown") is False

    def test_invariant_categories(self, sample_invariant):
        """Test invariant category checks."""
        assert sample_invariant.is_supply_invariant() is True
        assert sample_invariant.is_balance_invariant() is False

    def test_offchain_input_is_oracle(self, sample_offchain_input):
        """Test off-chain input type checking."""
        assert sample_offchain_input.is_oracle() is True

    def test_value_flow_involves_role(self, sample_value_flow):
        """Test value flow role checking."""
        assert sample_value_flow.involves_role("protocol") is True
        assert sample_value_flow.involves_role("liquidator") is True
        assert sample_value_flow.involves_role("random") is False

    def test_accepted_risk_matches_pattern(self, sample_accepted_risk):
        """Test accepted risk pattern matching."""
        assert sample_accepted_risk.matches_pattern("access-control-001") is True
        assert sample_accepted_risk.matches_pattern("reentrancy-001") is False


# =============================================================================
# Test CLI Integration (Programmatic)
# =============================================================================


class TestCLIIntegration:
    """Test CLI commands via programmatic invocation."""

    def test_context_app_exists(self):
        """Test that context CLI app is importable."""
        from alphaswarm_sol.cli.context import context_app

        assert context_app is not None
        # Check commands exist
        command_names = [c.name for c in context_app.registered_commands]
        assert "generate" in command_names
        assert "show" in command_names
        assert "update" in command_names
        assert "list" in command_names
        assert "delete" in command_names
        assert "export" in command_names

    def test_context_app_registered(self):
        """Test that context CLI is registered in main app."""
        from alphaswarm_sol.cli.main import app

        group_names = [g.name for g in app.registered_groups]
        assert "context" in group_names


# =============================================================================
# Integration Tests
# =============================================================================


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    def test_full_context_pack_workflow(self, sample_pack, temp_storage_dir):
        """Test complete workflow from creation to retrieval."""
        # 1. Create storage
        storage = ContextPackStorage(temp_storage_dir)

        # 2. Save context pack
        storage.save(sample_pack, "full_test")

        # 3. Load and verify
        loaded = storage.load("full_test")
        assert loaded is not None
        assert loaded.protocol_name == sample_pack.protocol_name

        # 4. Create providers
        evidence_provider = EvidenceContextProvider(loaded)
        bead_provider = BeadContextProvider(loaded)

        # 5. Test evidence context
        finding_ctx = evidence_provider.get_context_for_finding(
            function_name="liquidate",
            vulnerability_class="reentrancy",
            semantic_ops=["TRANSFERS_VALUE_OUT"],
        )
        assert finding_ctx is not None

        # 6. Test bead context
        bead_ctx = bead_provider.get_context_for_bead(
            vulnerability_class="oracle-manipulation",
            function_name="liquidate",
            semantic_ops=["READS_ORACLE"],
        )
        assert bead_ctx is not None

        # 7. Test section retrieval
        roles_section = storage.load_section("full_test", "roles")
        assert roles_section is not None

        # 8. Test summary
        summary = storage.get_summary()
        assert summary["total"] == 1

        # 9. Delete and verify
        storage.delete("full_test")
        assert storage.exists("full_test") is False

    def test_incremental_update_preserves_human_edits(self, temp_storage_dir):
        """Test that incremental updates preserve human-verified content."""
        from alphaswarm_sol.kg.schema import KnowledgeGraph

        # Create initial pack with CERTAIN confidence (simulating human review)
        initial_assumption = Assumption(
            description="Human-verified critical assumption",
            category="trust",
            affects_functions=["critical_function"],
            confidence=Confidence.CERTAIN,
            source="human_audit",
        )

        initial_pack = ProtocolContextPack(
            protocol_name="UpdateTest",
            reviewed=True,
            assumptions=[initial_assumption],
        )

        storage = ContextPackStorage(temp_storage_dir)
        storage.save(initial_pack, "update_test")

        # Create builder for update
        graph = KnowledgeGraph()
        builder = ContextPackBuilder(
            graph=graph,
            project_path=temp_storage_dir,
            config=BuildConfig(protocol_name="UpdateTest"),
        )

        # Load and update (async method)
        loaded = storage.load("update_test")
        result = asyncio.run(builder.update(loaded, changed_files=["some.sol"]))

        # Human-verified assumption should be preserved
        preserved = [
            a for a in result.pack.assumptions
            if a.confidence == Confidence.CERTAIN and "Human-verified" in a.description
        ]
        assert len(preserved) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
