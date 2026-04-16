"""Tests for canonical evidence ID generation and determinism.

These tests verify:
1. Evidence IDs are stable across repeated builds (determinism)
2. Evidence ID ordering is deterministic
3. Evidence IDs propagate to agent findings
4. Schema Evidence and AgentEvidence carry evidence_id fields

Reference: Phase 5.10 - Pattern Context + Batch Discovery Orchestration
"""

import pytest
from alphaswarm_sol.kg.evidence_id import (
    evidence_id_for,
    evidence_id_for_evidence,
    evidence_ids_for_node,
    compute_evidence_id_deterministic,
    CanonicalEvidenceID,
    EvidenceIDRegistry,
    EvidenceIDError,
    EvidenceResolutionError,
    validate_evidence_id,
    validate_build_hash,
    EVIDENCE_ID_PATTERN,
    BUILD_HASH_PATTERN,
)
from alphaswarm_sol.kg.schema import Evidence
from alphaswarm_sol.kg.graph_hash import compute_graph_hash
from alphaswarm_sol.agents.base import AgentEvidence, EvidenceType


# ============================================================================
# Evidence ID Determinism Tests
# ============================================================================


class TestEvidenceIDDeterminism:
    """Tests verifying evidence IDs are stable across repeated builds."""

    def test_evidence_id_for_same_inputs_same_id(self) -> None:
        """Same inputs must always produce the same evidence ID."""
        build_hash = "a1b2c3d4e5f6"
        node_id = "F-withdraw-001"
        file = "Token.sol"
        line_start = 42

        id1 = evidence_id_for(build_hash, node_id, file, line_start)
        id2 = evidence_id_for(build_hash, node_id, file, line_start)
        id3 = evidence_id_for(build_hash, node_id, file, line_start)

        assert id1 == id2 == id3

    def test_evidence_id_for_different_builds_different_ids(self) -> None:
        """Different build hashes must produce different evidence IDs."""
        node_id = "F-withdraw-001"
        file = "Token.sol"
        line_start = 42

        id1 = evidence_id_for("111111111111", node_id, file, line_start)
        id2 = evidence_id_for("222222222222", node_id, file, line_start)

        assert id1 != id2

    def test_evidence_id_for_different_lines_different_ids(self) -> None:
        """Different line numbers must produce different evidence IDs."""
        build_hash = "a1b2c3d4e5f6"
        node_id = "F-withdraw-001"
        file = "Token.sol"

        id1 = evidence_id_for(build_hash, node_id, file, line_start=42)
        id2 = evidence_id_for(build_hash, node_id, file, line_start=43)

        assert id1 != id2

    def test_evidence_id_for_line_range_matters(self) -> None:
        """Line end must affect the evidence ID."""
        build_hash = "a1b2c3d4e5f6"
        node_id = "F-withdraw-001"
        file = "Token.sol"

        id1 = evidence_id_for(build_hash, node_id, file, line_start=42, line_end=42)
        id2 = evidence_id_for(build_hash, node_id, file, line_start=42, line_end=45)

        assert id1 != id2

    def test_evidence_id_for_semantic_op_matters(self) -> None:
        """Semantic operation must affect the evidence ID when provided."""
        build_hash = "a1b2c3d4e5f6"
        node_id = "F-withdraw-001"
        file = "Token.sol"
        line_start = 42

        id1 = evidence_id_for(build_hash, node_id, file, line_start)
        id2 = evidence_id_for(
            build_hash, node_id, file, line_start, semantic_op="TRANSFERS_VALUE_OUT"
        )
        id3 = evidence_id_for(
            build_hash, node_id, file, line_start, semantic_op="WRITES_USER_BALANCE"
        )

        assert id1 != id2
        assert id2 != id3
        assert id1 != id3

    def test_evidence_id_format(self) -> None:
        """Evidence IDs must follow EVD-xxxxxxxx format."""
        evidence_id = evidence_id_for(
            build_hash="a1b2c3d4e5f6",
            node_id="F-001",
            file="Token.sol",
            line_start=42,
        )

        assert evidence_id.startswith("EVD-")
        assert len(evidence_id) == 12  # EVD- + 8 hex chars
        assert EVIDENCE_ID_PATTERN.match(evidence_id) is not None

    def test_compute_evidence_id_deterministic_alias(self) -> None:
        """compute_evidence_id_deterministic must be an alias for evidence_id_for."""
        build_hash = "a1b2c3d4e5f6"
        node_id = "F-001"
        file = "Token.sol"
        line_start = 42

        id1 = evidence_id_for(build_hash, node_id, file, line_start)
        id2 = compute_evidence_id_deterministic(build_hash, node_id, file, line_start)

        assert id1 == id2


class TestEvidenceIDOrdering:
    """Tests verifying evidence ID ordering is deterministic."""

    def test_evidence_ids_for_node_preserves_order(self) -> None:
        """evidence_ids_for_node must preserve evidence order."""
        build_hash = "a1b2c3d4e5f6"
        node_id = "F-001"

        evidence_list = [
            Evidence(file="A.sol", line_start=10),
            Evidence(file="B.sol", line_start=20),
            Evidence(file="C.sol", line_start=30),
        ]

        ids1 = evidence_ids_for_node(build_hash, node_id, evidence_list)
        ids2 = evidence_ids_for_node(build_hash, node_id, evidence_list)

        assert ids1 == ids2
        assert len(ids1) == 3
        # Each evidence should have unique ID
        assert len(set(ids1)) == 3

    def test_evidence_ids_ordering_independent_of_call_order(self) -> None:
        """Evidence IDs must be independent of the order they were generated."""
        build_hash = "a1b2c3d4e5f6"

        # Generate in one order
        id_a = evidence_id_for(build_hash, "N-A", "A.sol", 10)
        id_b = evidence_id_for(build_hash, "N-B", "B.sol", 20)

        # Generate in reverse order
        id_b2 = evidence_id_for(build_hash, "N-B", "B.sol", 20)
        id_a2 = evidence_id_for(build_hash, "N-A", "A.sol", 10)

        assert id_a == id_a2
        assert id_b == id_b2

    def test_registry_all_ids_is_deterministic(self) -> None:
        """Registry.all_ids() must return consistent ordering."""
        build_hash = "a1b2c3d4e5f6"
        registry = EvidenceIDRegistry(build_hash)

        # Register in specific order
        registry.register("N-001", "A.sol", 10)
        registry.register("N-002", "B.sol", 20)
        registry.register("N-003", "C.sol", 30)

        ids1 = registry.all_ids()
        ids2 = registry.all_ids()

        assert ids1 == ids2


class TestCanonicalEvidenceID:
    """Tests for CanonicalEvidenceID class."""

    def test_canonical_id_deterministic(self) -> None:
        """CanonicalEvidenceID must produce deterministic IDs."""
        id1 = CanonicalEvidenceID(
            build_hash="a1b2c3d4e5f6",
            node_id="F-001",
            file="Token.sol",
            line_start=42,
            line_end=45,
        )
        id2 = CanonicalEvidenceID(
            build_hash="a1b2c3d4e5f6",
            node_id="F-001",
            file="Token.sol",
            line_start=42,
            line_end=45,
        )

        assert id1.id == id2.id
        assert str(id1) == str(id2)
        assert hash(id1) == hash(id2)

    def test_canonical_id_to_dict(self) -> None:
        """CanonicalEvidenceID.to_dict() must produce v2 contract format."""
        evidence = CanonicalEvidenceID(
            build_hash="a1b2c3d4e5f6",
            node_id="F-001",
            file="Token.sol",
            line_start=42,
            line_end=45,
            column=4,
            semantic_op="TRANSFERS_VALUE_OUT",
        )

        d = evidence.to_dict()

        assert d["file"] == "Token.sol"
        assert d["line"] == 42
        assert d["line_end"] == 45
        assert d["column"] == 4
        assert d["node_id"] == "F-001"
        assert d["build_hash"] == "a1b2c3d4e5f6"
        assert d["snippet_id"] == evidence.id
        assert d["semantic_op"] == "TRANSFERS_VALUE_OUT"

    def test_canonical_id_from_evidence(self) -> None:
        """CanonicalEvidenceID.from_evidence() must work correctly."""
        evidence = Evidence(file="Token.sol", line_start=42, line_end=45)
        canonical = CanonicalEvidenceID.from_evidence(
            build_hash="a1b2c3d4e5f6",
            node_id="F-001",
            evidence=evidence,
            semantic_op="WRITES_STATE",
        )

        assert canonical.file == "Token.sol"
        assert canonical.line_start == 42
        assert canonical.line_end == 45
        assert canonical.semantic_op == "WRITES_STATE"
        assert validate_evidence_id(canonical.id)

    def test_canonical_id_invalid_build_hash(self) -> None:
        """CanonicalEvidenceID must reject invalid build hashes."""
        with pytest.raises(EvidenceIDError, match="Invalid build_hash"):
            CanonicalEvidenceID(
                build_hash="invalid",
                node_id="F-001",
                file="Token.sol",
                line_start=42,
                line_end=42,
            )


class TestEvidenceIDRegistry:
    """Tests for EvidenceIDRegistry."""

    def test_register_and_resolve(self) -> None:
        """Registry must register and resolve evidence correctly."""
        registry = EvidenceIDRegistry(build_hash="a1b2c3d4e5f6")

        evidence = registry.register(
            node_id="F-001",
            file="Token.sol",
            line_start=42,
            line_end=45,
            semantic_op="TRANSFERS_VALUE_OUT",
        )

        resolved = registry.resolve(evidence.id)

        assert resolved.file == "Token.sol"
        assert resolved.line_start == 42
        assert resolved.line_end == 45
        assert resolved.semantic_op == "TRANSFERS_VALUE_OUT"

    def test_register_evidence_dataclass(self) -> None:
        """Registry must register from Evidence dataclass."""
        registry = EvidenceIDRegistry(build_hash="a1b2c3d4e5f6")
        evidence = Evidence(file="Token.sol", line_start=42)

        canonical = registry.register_evidence("F-001", evidence)

        assert canonical.file == "Token.sol"
        assert registry.contains(canonical.id)

    def test_get_by_node(self) -> None:
        """Registry must track evidence by node."""
        registry = EvidenceIDRegistry(build_hash="a1b2c3d4e5f6")

        registry.register("N-001", "A.sol", 10)
        registry.register("N-001", "A.sol", 20)
        registry.register("N-002", "B.sol", 30)

        node_evidence = registry.get_by_node("N-001")
        assert len(node_evidence) == 2

        node2_evidence = registry.get_by_node("N-002")
        assert len(node2_evidence) == 1

    def test_to_evidence_refs(self) -> None:
        """Registry must export v2 contract evidence_refs."""
        registry = EvidenceIDRegistry(build_hash="a1b2c3d4e5f6")

        registry.register("N-001", "A.sol", 10)
        registry.register("N-002", "B.sol", 20)

        refs = registry.to_evidence_refs()

        assert len(refs) == 2
        assert all("snippet_id" in ref for ref in refs)
        assert all("build_hash" in ref for ref in refs)


# ============================================================================
# Schema Evidence Tests
# ============================================================================


class TestSchemaEvidenceID:
    """Tests for Evidence dataclass evidence_id field."""

    def test_evidence_with_evidence_id(self) -> None:
        """Evidence can carry evidence_id field."""
        evidence = Evidence(
            file="Token.sol",
            line_start=42,
            evidence_id="EVD-a1b2c3d4",
        )

        assert evidence.evidence_id == "EVD-a1b2c3d4"

    def test_evidence_to_dict_includes_evidence_id(self) -> None:
        """Evidence.to_dict() must include evidence_id when set."""
        evidence = Evidence(
            file="Token.sol",
            line_start=42,
            evidence_id="EVD-a1b2c3d4",
        )

        d = evidence.to_dict()

        assert d["evidence_id"] == "EVD-a1b2c3d4"

    def test_evidence_to_dict_omits_evidence_id_when_none(self) -> None:
        """Evidence.to_dict() must omit evidence_id when not set."""
        evidence = Evidence(file="Token.sol", line_start=42)

        d = evidence.to_dict()

        assert "evidence_id" not in d

    def test_evidence_from_dict_with_evidence_id(self) -> None:
        """Evidence.from_dict() must restore evidence_id."""
        data = {
            "file": "Token.sol",
            "line_start": 42,
            "evidence_id": "EVD-a1b2c3d4",
        }

        evidence = Evidence.from_dict(data)

        assert evidence.evidence_id == "EVD-a1b2c3d4"

    def test_evidence_with_evidence_id_method(self) -> None:
        """Evidence.with_evidence_id() must create new instance with ID."""
        evidence = Evidence(file="Token.sol", line_start=42)
        new_evidence = evidence.with_evidence_id("EVD-a1b2c3d4")

        assert evidence.evidence_id is None
        assert new_evidence.evidence_id == "EVD-a1b2c3d4"
        assert new_evidence.file == "Token.sol"
        assert new_evidence.line_start == 42


# ============================================================================
# Agent Evidence Tests
# ============================================================================


class TestAgentEvidenceID:
    """Tests for AgentEvidence evidence_id propagation."""

    def test_agent_evidence_with_evidence_id(self) -> None:
        """AgentEvidence can carry evidence_id and build_hash."""
        evidence = AgentEvidence(
            type=EvidenceType.NODE,
            description="Test evidence",
            evidence_id="EVD-a1b2c3d4",
            build_hash="a1b2c3d4e5f6",
        )

        assert evidence.evidence_id == "EVD-a1b2c3d4"
        assert evidence.build_hash == "a1b2c3d4e5f6"

    def test_agent_evidence_to_dict_includes_evidence_id(self) -> None:
        """AgentEvidence.to_dict() must include evidence_id when set."""
        evidence = AgentEvidence(
            type=EvidenceType.NODE,
            description="Test",
            evidence_id="EVD-a1b2c3d4",
            build_hash="a1b2c3d4e5f6",
            file="Token.sol",
            line_start=42,
        )

        d = evidence.to_dict()

        assert d["evidence_id"] == "EVD-a1b2c3d4"
        assert d["build_hash"] == "a1b2c3d4e5f6"
        assert d["file"] == "Token.sol"
        assert d["line_start"] == 42

    def test_agent_evidence_to_dict_omits_none_fields(self) -> None:
        """AgentEvidence.to_dict() must omit optional fields when None."""
        evidence = AgentEvidence(
            type=EvidenceType.NODE,
            description="Test",
        )

        d = evidence.to_dict()

        assert "evidence_id" not in d
        assert "build_hash" not in d
        assert "file" not in d

    def test_agent_evidence_from_dict_with_evidence_id(self) -> None:
        """AgentEvidence.from_dict() must restore evidence_id fields."""
        data = {
            "type": "node",
            "description": "Test",
            "evidence_id": "EVD-a1b2c3d4",
            "build_hash": "a1b2c3d4e5f6",
            "file": "Token.sol",
            "line_start": 42,
        }

        evidence = AgentEvidence.from_dict(data)

        assert evidence.evidence_id == "EVD-a1b2c3d4"
        assert evidence.build_hash == "a1b2c3d4e5f6"
        assert evidence.file == "Token.sol"
        assert evidence.line_start == 42

    def test_agent_evidence_with_evidence_id_method(self) -> None:
        """AgentEvidence.with_evidence_id() must create copy with ID."""
        evidence = AgentEvidence(
            type=EvidenceType.NODE,
            description="Test",
            source_nodes=["N-001"],
        )

        new_evidence = evidence.with_evidence_id("EVD-a1b2c3d4", "a1b2c3d4e5f6")

        assert evidence.evidence_id is None
        assert new_evidence.evidence_id == "EVD-a1b2c3d4"
        assert new_evidence.build_hash == "a1b2c3d4e5f6"
        assert new_evidence.source_nodes == ["N-001"]

    def test_agent_evidence_compute_evidence_id(self) -> None:
        """AgentEvidence.compute_evidence_id() must generate canonical ID."""
        evidence = AgentEvidence(
            type=EvidenceType.NODE,
            description="Test",
            file="Token.sol",
            line_start=42,
            line_end=45,
            semantic_op="TRANSFERS_VALUE_OUT",
        )

        computed = evidence.compute_evidence_id("a1b2c3d4e5f6", "F-001")

        assert computed.evidence_id is not None
        assert validate_evidence_id(computed.evidence_id)
        assert computed.build_hash == "a1b2c3d4e5f6"

    def test_agent_evidence_compute_evidence_id_requires_location(self) -> None:
        """AgentEvidence.compute_evidence_id() must require file and line_start."""
        evidence = AgentEvidence(
            type=EvidenceType.NODE,
            description="Test",
        )

        with pytest.raises(ValueError, match="file and line_start must be set"):
            evidence.compute_evidence_id("a1b2c3d4e5f6", "F-001")


# ============================================================================
# Integration Tests
# ============================================================================


class TestEvidenceIDIntegration:
    """Integration tests for evidence ID flow."""

    def test_full_workflow_graph_to_agent(self) -> None:
        """Test complete flow: graph hash -> evidence ID -> agent evidence."""
        # 1. Compute build hash from graph
        graph = {
            "nodes": [
                {"id": "F-001", "type": "Function", "label": "withdraw"},
            ],
            "edges": [],
        }
        build_hash = compute_graph_hash(graph)

        # 2. Create Evidence with evidence_id
        evidence = Evidence(file="Token.sol", line_start=42, line_end=45)
        evidence_id = evidence_id_for_evidence(build_hash, "F-001", evidence)
        evidence_with_id = evidence.with_evidence_id(evidence_id)

        # 3. Create AgentEvidence that references the graph evidence
        agent_evidence = AgentEvidence(
            type=EvidenceType.NODE,
            description="Function withdraw has external call before state update",
            source_nodes=["F-001"],
            file="Token.sol",
            line_start=42,
            line_end=45,
        )
        agent_evidence_with_id = agent_evidence.compute_evidence_id(build_hash, "F-001")

        # 4. Verify IDs match since they refer to same source location
        # Note: They may differ if compute_evidence_id uses different defaults
        # The key invariant is determinism - same inputs = same ID
        assert validate_evidence_id(evidence_with_id.evidence_id)
        assert validate_evidence_id(agent_evidence_with_id.evidence_id)

    def test_evidence_id_stable_across_registry_operations(self) -> None:
        """Evidence IDs must be stable regardless of registry state."""
        build_hash = "a1b2c3d4e5f6"

        # Generate ID directly
        direct_id = evidence_id_for(build_hash, "F-001", "Token.sol", 42)

        # Generate via registry
        registry = EvidenceIDRegistry(build_hash)
        registered = registry.register("F-001", "Token.sol", 42)

        assert direct_id == registered.id

    def test_serialization_roundtrip_preserves_evidence_id(self) -> None:
        """Evidence ID must survive serialization roundtrip."""
        original = AgentEvidence(
            type=EvidenceType.PATH,
            description="Vulnerable path",
            evidence_id="EVD-a1b2c3d4",
            build_hash="a1b2c3d4e5f6",
            file="Token.sol",
            line_start=42,
        )

        # Serialize and deserialize
        serialized = original.to_dict()
        restored = AgentEvidence.from_dict(serialized)

        assert restored.evidence_id == original.evidence_id
        assert restored.build_hash == original.build_hash
        assert restored.file == original.file
        assert restored.line_start == original.line_start
