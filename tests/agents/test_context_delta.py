"""Tests for ContextDelta and delta packing in verify pass.

Phase 5.10-06: Context delta tests.

Tests:
- ContextDelta computation between scout and verifier slices
- Delta includes only added nodes/edges
- Evidence IDs are deterministically sorted
- DeltaPacker budget enforcement
- Delta is never trimmed to drop PCP fields
"""

import pytest
from alphaswarm_sol.agents.context.types import (
    BudgetPolicy,
    ContextDelta,
)
from alphaswarm_sol.agents.context.merger import (
    DeltaMergeResult,
    DeltaPacker,
)


# =============================================================================
# ContextDelta Tests
# =============================================================================


def test_context_delta_defaults():
    """Test ContextDelta default values."""
    delta = ContextDelta()

    assert delta.added_node_ids == []
    assert delta.added_edge_ids == []
    assert delta.removed_node_ids == []
    assert delta.evidence_ids == []
    assert delta.property_changes == {}
    assert delta.scout_coverage == 0.0
    assert delta.delta_tokens == 0


def test_context_delta_is_empty():
    """Test ContextDelta.is_empty() check."""
    empty_delta = ContextDelta()
    assert empty_delta.is_empty() is True

    delta_with_nodes = ContextDelta(added_node_ids=["F-test"])
    assert delta_with_nodes.is_empty() is False

    delta_with_evidence = ContextDelta(evidence_ids=["E-001"])
    assert delta_with_evidence.is_empty() is False


def test_context_delta_node_count():
    """Test ContextDelta.node_count() calculation."""
    delta = ContextDelta(
        added_node_ids=["F-1", "F-2", "F-3"],
        removed_node_ids=["F-old"],
    )

    assert delta.node_count() == 4  # 3 added + 1 removed


def test_context_delta_compute():
    """Test ContextDelta.compute() creates proper delta."""
    scout_nodes = {"F-1", "F-2", "F-3"}
    scout_edges = {"E-1", "E-2"}
    verifier_nodes = {"F-1", "F-2", "F-3", "F-4", "F-5"}
    verifier_edges = {"E-1", "E-2", "E-3"}
    evidence_ids = ["EV-001", "EV-003", "EV-002"]  # Unsorted

    delta = ContextDelta.compute(
        scout_node_ids=scout_nodes,
        scout_edge_ids=scout_edges,
        verifier_node_ids=verifier_nodes,
        verifier_edge_ids=verifier_edges,
        evidence_ids=evidence_ids,
        scout_coverage=0.75,
    )

    # Should only include added nodes/edges
    assert set(delta.added_node_ids) == {"F-4", "F-5"}
    assert set(delta.added_edge_ids) == {"E-3"}
    assert delta.removed_node_ids == []  # No removals

    # Evidence IDs should be sorted
    assert delta.evidence_ids == ["EV-001", "EV-002", "EV-003"]

    # Coverage from scout pass
    assert delta.scout_coverage == 0.75

    # Token estimate should be positive
    assert delta.delta_tokens > 0


def test_context_delta_compute_with_removals():
    """Test delta computation when verifier has fewer nodes than scout."""
    scout_nodes = {"F-1", "F-2", "F-3", "F-old"}
    scout_edges = {"E-1", "E-2"}
    verifier_nodes = {"F-1", "F-2", "F-3"}  # F-old removed
    verifier_edges = {"E-1", "E-2", "E-3"}

    delta = ContextDelta.compute(
        scout_node_ids=scout_nodes,
        scout_edge_ids=scout_edges,
        verifier_node_ids=verifier_nodes,
        verifier_edge_ids=verifier_edges,
    )

    # Should track removals
    assert delta.removed_node_ids == ["F-old"]
    assert delta.added_node_ids == []


def test_context_delta_deterministic_ordering():
    """Test that delta output is deterministically ordered."""
    scout = {"C", "A", "B"}
    verifier = {"C", "A", "B", "E", "D", "F"}

    delta1 = ContextDelta.compute(scout, set(), verifier, set())
    delta2 = ContextDelta.compute(scout, set(), verifier, set())

    # Both should produce same order
    assert delta1.added_node_ids == delta2.added_node_ids
    assert delta1.added_node_ids == ["D", "E", "F"]  # Sorted


def test_context_delta_serialization():
    """Test ContextDelta to_dict/from_dict roundtrip."""
    delta = ContextDelta(
        added_node_ids=["F-new1", "F-new2"],
        added_edge_ids=["E-new"],
        removed_node_ids=["F-old"],
        evidence_ids=["EV-001", "EV-002"],
        property_changes={"prop1": "changed"},
        scout_coverage=0.8,
        delta_tokens=250,
    )

    data = delta.to_dict()

    # Should be deterministically sorted
    assert data["added_node_ids"] == ["F-new1", "F-new2"]
    assert data["evidence_ids"] == ["EV-001", "EV-002"]
    assert data["scout_coverage"] == 0.8

    restored = ContextDelta.from_dict(data)
    assert restored.added_node_ids == delta.added_node_ids
    assert restored.evidence_ids == delta.evidence_ids
    assert restored.scout_coverage == delta.scout_coverage


# =============================================================================
# DeltaPacker Tests
# =============================================================================


def test_delta_packer_defaults():
    """Test DeltaPacker initialization with defaults."""
    packer = DeltaPacker()

    assert packer.budget_policy is not None
    assert packer.budget_policy.verify_pass_tokens == 3000


def test_delta_packer_compute_delta():
    """Test DeltaPacker.compute_delta() wrapper."""
    packer = DeltaPacker()

    delta = packer.compute_delta(
        scout_nodes={"F-1", "F-2"},
        scout_edges={"E-1"},
        verifier_nodes={"F-1", "F-2", "F-3"},
        verifier_edges={"E-1", "E-2"},
        evidence_ids=["EV-001"],
        scout_coverage=0.7,
    )

    assert "F-3" in delta.added_node_ids
    assert "E-2" in delta.added_edge_ids
    assert delta.scout_coverage == 0.7


def test_delta_packer_pack_for_verify():
    """Test packing delta for verify pass."""
    packer = DeltaPacker()

    delta = ContextDelta(
        added_node_ids=["F-1", "F-2"],
        added_edge_ids=["E-1"],
        evidence_ids=["EV-001", "EV-002"],
        scout_coverage=0.75,
        delta_tokens=350,
    )

    packed = packer.pack_for_verify(delta)

    assert packed["type"] == "context_delta"
    assert packed["scout_coverage"] == 0.75
    assert packed["added_nodes"] == ["F-1", "F-2"]
    assert packed["added_edges"] == ["E-1"]
    assert packed["evidence_ids"] == ["EV-001", "EV-002"]


def test_delta_packer_excludes_removed_by_default():
    """Test that removed nodes are excluded by default."""
    packer = DeltaPacker()

    delta = ContextDelta(
        added_node_ids=["F-new"],
        removed_node_ids=["F-old"],
    )

    packed = packer.pack_for_verify(delta)
    assert "removed_nodes" not in packed

    # But can be included explicitly
    packed_with_removed = packer.pack_for_verify(delta, include_removed=True)
    assert "removed_nodes" in packed_with_removed
    assert packed_with_removed["removed_nodes"] == ["F-old"]


def test_delta_packer_trims_to_budget():
    """Test that packer trims delta when over budget."""
    packer = DeltaPacker(BudgetPolicy(verify_pass_tokens=500))

    # Create delta with many nodes that will exceed budget
    delta = ContextDelta(
        added_node_ids=[f"F-{i}" for i in range(50)],  # Many nodes
        added_edge_ids=[f"E-{i}" for i in range(10)],
        evidence_ids=["EV-001"],  # Evidence never trimmed
        delta_tokens=5500,  # Over budget
    )

    packed = packer.pack_for_verify(delta, budget=500)

    # Evidence should always be preserved
    assert "evidence_ids" in packed
    assert "EV-001" in packed["evidence_ids"]

    # Nodes should be reduced
    if "added_nodes" in packed:
        assert len(packed["added_nodes"]) < 50


def test_delta_packer_evidence_never_trimmed():
    """Test that evidence IDs are never trimmed even with tight budget."""
    packer = DeltaPacker()

    delta = ContextDelta(
        added_node_ids=[f"F-{i}" for i in range(100)],
        evidence_ids=[f"EV-{i:03d}" for i in range(10)],
        delta_tokens=10000,
    )

    # Very tight budget
    packed = packer.pack_for_verify(delta, budget=100)

    # All evidence should be preserved
    assert len(packed["evidence_ids"]) == 10


def test_delta_packer_should_use_delta():
    """Test should_use_delta decision logic."""
    packer = DeltaPacker()

    # Delta much smaller than scout - use delta
    assert packer.should_use_delta(scout_tokens=2000, delta_tokens=500) is True

    # Delta similar to scout - don't use delta (< 30% reduction)
    assert packer.should_use_delta(scout_tokens=2000, delta_tokens=1500) is False

    # Edge case: zero scout tokens
    assert packer.should_use_delta(scout_tokens=0, delta_tokens=100) is False


def test_delta_packer_property_changes():
    """Test that property changes are included when present."""
    packer = DeltaPacker()

    delta = ContextDelta(
        added_node_ids=["F-1"],
        property_changes={"semantic_ops": ["ADDED_OP"]},
    )

    packed = packer.pack_for_verify(delta)

    assert "property_changes" in packed
    assert packed["property_changes"]["semantic_ops"] == ["ADDED_OP"]


# =============================================================================
# DeltaMergeResult Tests
# =============================================================================


def test_delta_merge_result_creation():
    """Test DeltaMergeResult creation and defaults."""
    result = DeltaMergeResult(
        success=True,
        delta=ContextDelta(added_node_ids=["F-1"]),
        packed={"type": "context_delta"},
        scout_bundle=None,
        evidence_ids=["EV-001"],
        within_budget=True,
    )

    assert result.success is True
    assert result.delta is not None
    assert result.evidence_ids == ["EV-001"]
    assert result.errors == []


def test_delta_merge_result_serialization():
    """Test DeltaMergeResult to_dict."""
    delta = ContextDelta(
        added_node_ids=["F-1"],
        evidence_ids=["EV-001"],
    )

    result = DeltaMergeResult(
        success=True,
        delta=delta,
        packed={"type": "context_delta", "evidence_ids": ["EV-001"]},
        scout_bundle=None,
        evidence_ids=["EV-001"],
        within_budget=True,
    )

    data = result.to_dict()

    assert data["success"] is True
    assert data["within_budget"] is True
    assert data["evidence_ids"] == ["EV-001"]
    assert "delta" in data
    assert "packed" in data


# =============================================================================
# Integration: Delta with Budget Policy
# =============================================================================


def test_delta_respects_verify_pass_budget():
    """Test that delta packing respects verify pass budget from policy."""
    policy = BudgetPolicy(verify_pass_tokens=1000)
    packer = DeltaPacker(policy)

    delta = ContextDelta(
        added_node_ids=[f"F-{i}" for i in range(20)],
        evidence_ids=["EV-001"],
        delta_tokens=2500,
    )

    # Default budget should come from policy
    packed = packer.pack_for_verify(delta)

    # Should have been trimmed to fit ~1000 tokens
    if "added_nodes" in packed:
        # 20 nodes * 100 tokens = 2000, should be reduced
        assert len(packed["added_nodes"]) < 20


def test_delta_includes_only_new_evidence():
    """Test that delta only includes new evidence not in scout."""
    scout_nodes = {"F-1", "F-2"}
    verifier_nodes = {"F-1", "F-2", "F-3", "F-4"}

    delta = ContextDelta.compute(
        scout_node_ids=scout_nodes,
        scout_edge_ids=set(),
        verifier_node_ids=verifier_nodes,
        verifier_edge_ids=set(),
        evidence_ids=["EV-new-1", "EV-new-2"],  # Only new evidence
        scout_coverage=0.6,
    )

    # Only new nodes should be in delta
    assert "F-1" not in delta.added_node_ids
    assert "F-2" not in delta.added_node_ids
    assert "F-3" in delta.added_node_ids
    assert "F-4" in delta.added_node_ids
