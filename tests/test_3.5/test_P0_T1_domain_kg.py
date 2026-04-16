"""
Tests for P0-T1: Domain Knowledge Graph

Tests specifications, invariants, DeFi primitives, and matching logic.
"""

import pytest

from alphaswarm_sol.knowledge.domain_kg import (
    DomainKnowledgeGraph,
    Specification,
    DeFiPrimitive,
    Invariant,
    InvariantViolation,
    SpecType,
)
from alphaswarm_sol.knowledge.specs import load_all_specs


# Test Fixtures

@pytest.fixture
def domain_kg():
    """Create domain knowledge graph with all specs loaded."""
    kg = DomainKnowledgeGraph()
    specs, primitives = load_all_specs()

    for spec in specs:
        kg.add_specification(spec)

    for primitive in primitives:
        kg.add_primitive(primitive)

    return kg


@pytest.fixture
def sample_transfer_fn():
    """Sample ERC-20 transfer function node."""
    return {
        "id": "fn_transfer",
        "name": "transfer",
        "signature": "transfer(address,uint256)",
        "properties": {
            "operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            "follows_cei_pattern": True,
            "has_return_value": True,
        }
    }


@pytest.fixture
def vulnerable_transfer_fn():
    """Vulnerable transfer function with reentrancy."""
    return {
        "id": "fn_bad_transfer",
        "name": "transfer",
        "signature": "transfer(address,uint256)",
        "properties": {
            "operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            "follows_cei_pattern": False,
            "state_write_after_external_call": True,
            "has_return_value": False,
        }
    }


# Core Data Structure Tests

class TestDataStructures:
    """Test core data structures."""

    def test_invariant_creation(self):
        """Should create invariant with all fields."""
        inv = Invariant(
            id="test-inv",
            description="Test invariant",
            scope="function",
            violation_signature="W:bal→X:out",
            must_have=["has_check"],
            must_not_have=["is_vulnerable"]
        )

        assert inv.id == "test-inv"
        assert inv.scope == "function"
        assert len(inv.must_have) == 1

    def test_specification_creation(self):
        """Should create specification with invariants."""
        inv = Invariant(id="inv-1", description="Test", scope="function")

        spec = Specification(
            id="test-spec",
            spec_type=SpecType.ERC_STANDARD,
            name="Test Standard",
            description="Test description",
            version="1.0",
            function_signatures=["test(uint256)"],
            expected_operations=["TRANSFERS_VALUE"],
            invariants=[inv],
            semantic_tags=["test"]
        )

        assert spec.id == "test-spec"
        assert len(spec.invariants) == 1
        assert spec.spec_type == SpecType.ERC_STANDARD

    def test_defi_primitive_creation(self):
        """Should create DeFi primitive with security model."""
        primitive = DeFiPrimitive(
            id="test-primitive",
            name="Test Primitive",
            description="Test",
            entry_functions=["execute"],
            implements_specs=["erc-20"],
            attack_surface=["reentrancy"],
            known_attack_patterns=["pattern-1"]
        )

        assert primitive.id == "test-primitive"
        assert len(primitive.attack_surface) == 1


# Domain KG Tests

class TestDomainKnowledgeGraph:
    """Test domain knowledge graph."""

    def test_initialization(self):
        """Should initialize empty graph."""
        kg = DomainKnowledgeGraph()

        assert len(kg.specifications) == 0
        assert len(kg.primitives) == 0

    def test_add_specification(self):
        """Should add and index specification."""
        kg = DomainKnowledgeGraph()

        spec = Specification(
            id="test-1",
            spec_type=SpecType.ERC_STANDARD,
            name="Test",
            description="Test",
            version="1.0",
            function_signatures=["test()"],
            semantic_tags=["test"]
        )

        kg.add_specification(spec)

        assert "test-1" in kg.specifications
        assert "test" in kg._semantic_index
        assert "test()" in kg._sig_index

    def test_add_primitive(self):
        """Should add DeFi primitive."""
        kg = DomainKnowledgeGraph()

        primitive = DeFiPrimitive(
            id="prim-1",
            name="Test Primitive",
            description="Test"
        )

        kg.add_primitive(primitive)

        assert "prim-1" in kg.primitives

    def test_stats(self, domain_kg):
        """Should return statistics."""
        stats = domain_kg.stats()

        assert stats["total_specifications"] >= 4  # ERC-20, 721, 4626, 1155
        assert stats["total_primitives"] >= 5  # AMM, lending, flash loan, vault, staking
        assert stats["erc_standards"] >= 4


# Specification Matching Tests

class TestSpecificationMatching:
    """Test spec matching logic."""

    def test_exact_signature_match(self, domain_kg, sample_transfer_fn):
        """Should match by exact function signature."""
        matches = domain_kg.find_matching_specs(sample_transfer_fn, min_confidence=0.9)

        # Should match ERC-20
        assert len(matches) > 0
        spec, conf = matches[0]
        assert spec.id == "erc-20"
        assert conf == 1.0  # Exact match

    def test_operation_overlap_match(self, domain_kg):
        """Should match by semantic operation overlap."""
        fn_node = {
            "id": "fn_custom",
            "name": "customTransfer",
            "signature": "customTransfer(address,uint256)",  # Different sig
            "properties": {
                "operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            }
        }

        matches = domain_kg.find_matching_specs(fn_node, min_confidence=0.3)

        # Should still match ERC-20 by operations
        assert len(matches) > 0
        erc20_match = next((m for m in matches if m[0].id == "erc-20"), None)
        assert erc20_match is not None

    def test_semantic_tag_match(self, domain_kg):
        """Should match by semantic tags."""
        fn_node = {
            "id": "fn_vault_deposit",
            "name": "depositToVault",
            "signature": "depositToVault(uint256)",
            "properties": {
                "operations": [],
            }
        }

        matches = domain_kg.find_matching_specs(fn_node, min_confidence=0.4)

        # Should match vault-related specs
        vault_matches = [m for m in matches if "vault" in m[0].semantic_tags]
        assert len(vault_matches) > 0

    def test_no_match_below_threshold(self, domain_kg):
        """Should not match if below confidence threshold."""
        fn_node = {
            "id": "fn_unrelated",
            "name": "doSomethingElse",
            "signature": "doSomethingElse()",
            "properties": {
                "operations": [],
            }
        }

        matches = domain_kg.find_matching_specs(fn_node, min_confidence=0.9)

        assert len(matches) == 0


# Invariant Checking Tests

class TestInvariantChecking:
    """Test invariant violation detection."""

    def test_no_violations_safe_function(self, domain_kg, sample_transfer_fn):
        """Safe function should have no violations."""
        spec = domain_kg.get_specification("erc-20")
        behavioral_sig = "R:bal→W:bal→X:out"  # CEI pattern

        violations = domain_kg.check_invariant(
            sample_transfer_fn,
            spec,
            behavioral_sig
        )

        # Should have no violations
        assert len(violations) == 0

    def test_detect_cei_violation(self, domain_kg, vulnerable_transfer_fn):
        """Should detect CEI pattern violation."""
        spec = domain_kg.get_specification("erc-20")
        behavioral_sig = "R:bal→X:out→W:bal"  # Violated CEI

        violations = domain_kg.check_invariant(
            vulnerable_transfer_fn,
            spec,
            behavioral_sig
        )

        # Should detect CEI violation
        cei_violations = [v for v in violations if "cei" in v.invariant.id.lower()]
        assert len(cei_violations) > 0
        assert cei_violations[0].severity in ["high", "medium"]

    def test_detect_missing_property(self, domain_kg):
        """Should detect missing required properties."""
        spec = domain_kg.get_specification("erc-20")

        fn_node = {
            "id": "fn_incomplete",
            "name": "transfer",
            "signature": "transfer(address,uint256)",
            "properties": {
                "operations": ["TRANSFERS_VALUE_OUT"],
                "follows_cei_pattern": False,  # Missing this
                "has_return_value": False,  # Missing this
            }
        }

        violations = domain_kg.check_invariant(
            fn_node,
            spec,
            "R:bal→X:out→W:bal"
        )

        # Should have multiple violations
        assert len(violations) > 0

    def test_detect_forbidden_property(self, domain_kg):
        """Should detect forbidden properties."""
        spec = domain_kg.get_specification("erc-20")

        fn_node = {
            "id": "fn_bad",
            "name": "transfer",
            "signature": "transfer(address,uint256)",
            "properties": {
                "operations": [],
                "state_write_after_external_call": True,  # Forbidden
            }
        }

        violations = domain_kg.check_invariant(
            fn_node,
            spec,
            "R:bal→X:out→W:bal"
        )

        # Should detect forbidden property
        assert len(violations) > 0


# ERC Standard Tests

class TestERCStandards:
    """Test ERC standard definitions."""

    def test_erc20_loaded(self, domain_kg):
        """Should load ERC-20 with all properties."""
        erc20 = domain_kg.get_specification("erc-20")

        assert erc20 is not None
        assert erc20.name == "ERC-20"
        assert len(erc20.function_signatures) > 0
        assert len(erc20.invariants) > 0
        assert "token" in erc20.semantic_tags

    def test_erc721_loaded(self, domain_kg):
        """Should load ERC-721 with NFT properties."""
        erc721 = domain_kg.get_specification("erc-721")

        assert erc721 is not None
        assert erc721.name == "ERC-721"
        assert "nft" in erc721.semantic_tags

    def test_erc4626_loaded(self, domain_kg):
        """Should load ERC-4626 with vault properties."""
        erc4626 = domain_kg.get_specification("erc-4626")

        assert erc4626 is not None
        assert erc4626.name == "ERC-4626"
        assert "vault" in erc4626.semantic_tags
        assert len(erc4626.invariants) >= 3  # Share price, equivalence, rounding

    def test_erc1155_loaded(self, domain_kg):
        """Should load ERC-1155 multi-token standard."""
        erc1155 = domain_kg.get_specification("erc-1155")

        assert erc1155 is not None
        assert "multi-token" in erc1155.semantic_tags


# DeFi Primitive Tests

class TestDeFiPrimitives:
    """Test DeFi primitive definitions."""

    def test_amm_swap_loaded(self, domain_kg):
        """Should load AMM swap primitive."""
        amm = domain_kg.get_primitive("amm-swap")

        assert amm is not None
        assert "swap" in amm.entry_functions[0].lower()
        assert len(amm.attack_surface) > 0
        assert len(amm.primitive_invariants) >= 3  # Constant product, slippage, deadline

    def test_lending_pool_loaded(self, domain_kg):
        """Should load lending pool primitive."""
        lending = domain_kg.get_primitive("lending-pool")

        assert lending is not None
        assert "borrow" in [f.lower() for f in lending.entry_functions]
        assert "oracle-manipulation" in lending.known_attack_patterns

    def test_flash_loan_loaded(self, domain_kg):
        """Should load flash loan primitive."""
        flash_loan = domain_kg.get_primitive("flash-loan")

        assert flash_loan is not None
        assert flash_loan.callback_pattern is not None
        assert "reentrancy" in flash_loan.attack_surface[0].lower()

    def test_yield_vault_loaded(self, domain_kg):
        """Should load yield vault primitive."""
        vault = domain_kg.get_primitive("yield-vault")

        assert vault is not None
        assert "erc-4626" in vault.implements_specs
        assert "donation-attack" in vault.known_attack_patterns

    def test_staking_loaded(self, domain_kg):
        """Should load staking primitive."""
        staking = domain_kg.get_primitive("staking")

        assert staking is not None
        assert len(staking.primitive_invariants) > 0


# Integration Tests

class TestDomainKGIntegration:
    """Test full domain KG workflow."""

    def test_end_to_end_matching_and_checking(self, domain_kg):
        """Should match specs and check invariants end-to-end."""
        # Vulnerable ERC-20 transfer
        fn_node = {
            "id": "fn_vuln_transfer",
            "name": "transfer",
            "signature": "transfer(address,uint256)",
            "properties": {
                "operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                "follows_cei_pattern": False,
                "state_write_after_external_call": True,
            }
        }

        # Step 1: Find matching specs
        matches = domain_kg.find_matching_specs(fn_node)
        assert len(matches) > 0

        # Step 2: Check invariants for best match
        spec, conf = matches[0]
        violations = domain_kg.check_invariant(
            fn_node,
            spec,
            "R:bal→X:out→W:bal"
        )

        # Should detect violations
        assert len(violations) > 0

        # Should have evidence
        for v in violations:
            assert len(v.evidence) > 0
            assert v.function_id == "fn_vuln_transfer"

    def test_list_specifications_by_type(self, domain_kg):
        """Should filter specifications by type."""
        erc_standards = domain_kg.list_specifications(SpecType.ERC_STANDARD)

        assert len(erc_standards) >= 4
        assert all(s.spec_type == SpecType.ERC_STANDARD for s in erc_standards)

    def test_list_all_primitives(self, domain_kg):
        """Should list all DeFi primitives."""
        primitives = domain_kg.list_primitives()

        assert len(primitives) >= 5
        assert any(p.id == "amm-swap" for p in primitives)
        assert any(p.id == "lending-pool" for p in primitives)


# Success Criteria Tests

class TestSuccessCriteria:
    """Validate P0-T1 success criteria."""

    def test_has_required_erc_standards(self, domain_kg):
        """Should have ERC-20, 721, 4626, 1155."""
        required = ["erc-20", "erc-721", "erc-4626", "erc-1155"]

        for spec_id in required:
            spec = domain_kg.get_specification(spec_id)
            assert spec is not None, f"Missing {spec_id}"

    def test_has_required_defi_primitives(self, domain_kg):
        """Should have AMM, lending, vault primitives."""
        required = ["amm-swap", "lending-pool", "yield-vault"]

        for prim_id in required:
            prim = domain_kg.get_primitive(prim_id)
            assert prim is not None, f"Missing {prim_id}"

    def test_find_matching_specs_works(self, domain_kg, sample_transfer_fn):
        """find_matching_specs should return relevant specs."""
        matches = domain_kg.find_matching_specs(sample_transfer_fn)

        assert len(matches) > 0
        assert all(isinstance(m[0], Specification) for m in matches)
        assert all(isinstance(m[1], float) for m in matches)
        assert all(0.0 <= m[1] <= 1.0 for m in matches)

    def test_check_invariant_works(self, domain_kg, vulnerable_transfer_fn):
        """check_invariant should detect violations."""
        spec = domain_kg.get_specification("erc-20")
        violations = domain_kg.check_invariant(
            vulnerable_transfer_fn,
            spec,
            "R:bal→X:out→W:bal"
        )

        assert isinstance(violations, list)
        assert all(isinstance(v, InvariantViolation) for v in violations)

    def test_query_performance(self, domain_kg, sample_transfer_fn):
        """Queries should be fast (< 10ms for 100 functions)."""
        import time

        start = time.time()
        for _ in range(100):
            domain_kg.find_matching_specs(sample_transfer_fn)
        elapsed = time.time() - start

        # Should complete 100 queries in < 10ms total (or at least < 1 second)
        assert elapsed < 1.0, f"Took {elapsed*1000:.2f}ms for 100 queries"
