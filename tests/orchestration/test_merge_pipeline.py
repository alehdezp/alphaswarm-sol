"""Tests for merge pipeline v2 (Phase 5.10-10).

Tests:
- Deterministic delta ordering
- Idempotent merges across replay
- Conflict detection and quarantine
- Stable hash computation
"""

import pytest

from alphaswarm_sol.orchestration.schemas import (
    DeltaEntry,
    DeltaType,
    MergeBatch,
    MergeConflict,
    MergeResult,
    ConflictType,
)
from alphaswarm_sol.orchestration.dedup import (
    merge_batch_deltas,
    verify_merge_idempotency,
    compute_merged_output_hash,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_delta_finding() -> DeltaEntry:
    """Create a sample finding delta."""
    return DeltaEntry(
        delta_type=DeltaType.FINDING_ADD,
        target_id="FND-001",
        evidence_ids=["EVD-abc123", "EVD-def456"],
        source_batch="batch-001",
        payload={"severity": "high", "confidence": 0.85},
    )


@pytest.fixture
def sample_delta_evidence() -> DeltaEntry:
    """Create a sample evidence delta for a DIFFERENT target to avoid conflict."""
    return DeltaEntry(
        delta_type=DeltaType.EVIDENCE_ADD,
        target_id="FND-002",  # Different target to avoid conflict
        evidence_ids=["EVD-ghi789"],
        source_batch="batch-001",
        payload={"type": "behavioral_signature", "value": "R:bal->X:out->W:bal"},
    )


@pytest.fixture
def conflicting_delta() -> DeltaEntry:
    """Create a delta that conflicts with sample_delta_finding."""
    return DeltaEntry(
        delta_type=DeltaType.FINDING_ADD,
        target_id="FND-001",  # Same target
        evidence_ids=["EVD-xyz999"],  # Different evidence
        source_batch="batch-002",
        payload={"severity": "medium", "confidence": 0.45},  # Different confidence
    )


@pytest.fixture
def sample_batch(sample_delta_finding, sample_delta_evidence) -> MergeBatch:
    """Create a sample merge batch."""
    return MergeBatch(
        source="pattern_scout",
        deltas=[sample_delta_finding, sample_delta_evidence],
        graph_hash="abc123def456",
        pcp_version="2.0",
    )


# =============================================================================
# Delta Schema Tests
# =============================================================================


class TestDeltaEntry:
    """Tests for DeltaEntry schema."""

    def test_deterministic_delta_id(self, sample_delta_finding):
        """Delta ID should be deterministic for identical content."""
        delta1 = DeltaEntry(
            delta_type=DeltaType.FINDING_ADD,
            target_id="FND-001",
            evidence_ids=["EVD-abc123", "EVD-def456"],
            source_batch="batch-001",
            payload={"severity": "high", "confidence": 0.85},
        )
        delta2 = DeltaEntry(
            delta_type=DeltaType.FINDING_ADD,
            target_id="FND-001",
            evidence_ids=["EVD-abc123", "EVD-def456"],  # Same evidence
            source_batch="batch-002",  # Different batch doesn't affect ID
            payload={"severity": "high", "confidence": 0.85},
        )
        # Same content (excluding source_batch and timestamp) = same ID
        assert delta1.delta_id == delta2.delta_id

    def test_different_evidence_different_id(self):
        """Different evidence should produce different delta IDs."""
        delta1 = DeltaEntry(
            delta_type=DeltaType.FINDING_ADD,
            target_id="FND-001",
            evidence_ids=["EVD-abc123"],
            source_batch="batch-001",
            payload={"severity": "high"},
        )
        delta2 = DeltaEntry(
            delta_type=DeltaType.FINDING_ADD,
            target_id="FND-001",
            evidence_ids=["EVD-xyz999"],  # Different evidence
            source_batch="batch-001",
            payload={"severity": "high"},
        )
        assert delta1.delta_id != delta2.delta_id

    def test_ordering_key_priority(self):
        """Ordering key should prioritize by delta type."""
        finding = DeltaEntry(
            delta_type=DeltaType.FINDING_ADD,
            target_id="FND-001",
            evidence_ids=["EVD-001"],
            source_batch="batch-001",
            payload={},
        )
        evidence = DeltaEntry(
            delta_type=DeltaType.EVIDENCE_ADD,
            target_id="FND-001",
            evidence_ids=["EVD-002"],
            source_batch="batch-001",
            payload={},
        )
        verdict = DeltaEntry(
            delta_type=DeltaType.VERDICT_ADD,
            target_id="FND-001",
            evidence_ids=["EVD-003"],
            source_batch="batch-001",
            payload={},
        )

        # FINDING_ADD < EVIDENCE_ADD < VERDICT_ADD
        assert finding.ordering_key < evidence.ordering_key
        assert evidence.ordering_key < verdict.ordering_key

    def test_evidence_id_validation(self):
        """Invalid evidence IDs should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid evidence ID format"):
            DeltaEntry(
                delta_type=DeltaType.FINDING_ADD,
                target_id="FND-001",
                evidence_ids=["invalid-format"],  # Missing prefix
                source_batch="batch-001",
                payload={},
            )

    def test_valid_evidence_formats(self):
        """Various valid evidence ID formats should be accepted."""
        # All these should work
        delta = DeltaEntry(
            delta_type=DeltaType.FINDING_ADD,
            target_id="FND-001",
            evidence_ids=[
                "EVD-abc123",
                "node:func:withdraw",
                "edge:call:45",
                "fn:transfer:123",
            ],
            source_batch="batch-001",
            payload={},
        )
        assert len(delta.evidence_ids) == 4

    def test_to_dict_roundtrip(self, sample_delta_finding):
        """Delta should survive dict serialization roundtrip."""
        data = sample_delta_finding.to_dict()
        restored = DeltaEntry.from_dict(data)

        assert restored.delta_id == sample_delta_finding.delta_id
        assert restored.delta_type == sample_delta_finding.delta_type
        assert restored.target_id == sample_delta_finding.target_id
        assert restored.evidence_ids == sample_delta_finding.evidence_ids
        assert restored.payload == sample_delta_finding.payload


class TestMergeBatch:
    """Tests for MergeBatch schema."""

    def test_stable_hash_deterministic(self, sample_batch):
        """Stable hash should be deterministic for identical batches."""
        batch1 = MergeBatch(
            source="scout",
            deltas=sample_batch.deltas,
            graph_hash="abc123",
            pcp_version="2.0",
        )
        batch2 = MergeBatch(
            source="scout",
            deltas=sample_batch.deltas,
            graph_hash="abc123",
            pcp_version="2.0",
        )
        assert batch1.stable_hash == batch2.stable_hash

    def test_stable_hash_changes_with_graph(self, sample_delta_finding):
        """Stable hash should change when graph hash changes."""
        batch1 = MergeBatch(
            source="scout",
            deltas=[sample_delta_finding],
            graph_hash="abc123",
            pcp_version="2.0",
        )
        batch2 = MergeBatch(
            source="scout",
            deltas=[sample_delta_finding],
            graph_hash="xyz789",  # Different graph
            pcp_version="2.0",
        )
        assert batch1.stable_hash != batch2.stable_hash

    def test_add_delta_updates_hash(self, sample_batch, sample_delta_evidence):
        """Adding delta should update stable hash."""
        original_hash = sample_batch.stable_hash

        new_delta = DeltaEntry(
            delta_type=DeltaType.CONFIDENCE_CHANGE,
            target_id="FND-002",
            evidence_ids=["EVD-new123"],
            source_batch="batch-001",
            payload={"confidence": 0.9},
        )
        sample_batch.add_delta(new_delta)

        assert sample_batch.stable_hash != original_hash


# =============================================================================
# Merge Pipeline Tests
# =============================================================================


class TestMergeBatchDeltas:
    """Tests for merge_batch_deltas function."""

    def test_basic_merge(self, sample_batch):
        """Basic merge should combine deltas from batch."""
        result = merge_batch_deltas([sample_batch])

        assert result.idempotent
        assert len(result.merged_deltas) == 2
        assert len(result.conflicts) == 0
        assert result.output_hash

    def test_idempotent_replay(self, sample_batch):
        """Same merge should produce identical output."""
        result1 = merge_batch_deltas([sample_batch])
        result2 = merge_batch_deltas([sample_batch])

        assert result1.output_hash == result2.output_hash
        assert len(result1.merged_deltas) == len(result2.merged_deltas)
        assert result1.idempotent and result2.idempotent

    def test_order_independent_merge(self, sample_delta_finding, sample_delta_evidence):
        """Merge should be order-independent."""
        batch1 = MergeBatch(
            source="scout1",
            deltas=[sample_delta_finding],
            graph_hash="abc123",
        )
        batch2 = MergeBatch(
            source="scout2",
            deltas=[sample_delta_evidence],
            graph_hash="abc123",
        )

        result_ab = merge_batch_deltas([batch1, batch2])
        result_ba = merge_batch_deltas([batch2, batch1])

        # Same output regardless of batch order
        assert result_ab.output_hash == result_ba.output_hash

    def test_conflict_detection_evidence_mismatch(
        self, sample_delta_finding, conflicting_delta
    ):
        """Should detect conflict when evidence differs for same target."""
        batch1 = MergeBatch(
            source="scout1",
            deltas=[sample_delta_finding],
            graph_hash="abc123",
        )
        batch2 = MergeBatch(
            source="scout2",
            deltas=[conflicting_delta],
            graph_hash="abc123",
        )

        result = merge_batch_deltas([batch1, batch2])

        # Should have at least one conflict (evidence mismatch or confidence)
        assert len(result.conflicts) > 0
        assert result.conflicts[0].delta_a.target_id == "FND-001"
        assert result.conflicts[0].delta_b.target_id == "FND-001"

    def test_conflict_detection_confidence_conflict(self):
        """Should detect conflict when confidence differs significantly."""
        delta_high = DeltaEntry(
            delta_type=DeltaType.CONFIDENCE_CHANGE,
            target_id="FND-001",
            evidence_ids=["EVD-001", "EVD-002"],
            source_batch="batch-001",
            payload={"confidence": 0.95},
        )
        delta_low = DeltaEntry(
            delta_type=DeltaType.CONFIDENCE_CHANGE,
            target_id="FND-001",
            evidence_ids=["EVD-001", "EVD-002"],  # Same evidence
            source_batch="batch-002",
            payload={"confidence": 0.3},  # > 0.3 gap
        )

        batch1 = MergeBatch(source="scout1", deltas=[delta_high], graph_hash="abc123")
        batch2 = MergeBatch(source="scout2", deltas=[delta_low], graph_hash="abc123")

        result = merge_batch_deltas([batch1, batch2])

        confidence_conflicts = [
            c for c in result.conflicts
            if c.conflict_type.value == "confidence_conflict"
        ]
        assert len(confidence_conflicts) == 1

    def test_conflict_detection_verdict_divergence(self):
        """Should detect conflict when verdicts differ."""
        delta_vuln = DeltaEntry(
            delta_type=DeltaType.VERDICT_ADD,
            target_id="FND-001",
            evidence_ids=["EVD-001"],
            source_batch="batch-001",
            payload={"is_vulnerable": True},
        )
        delta_safe = DeltaEntry(
            delta_type=DeltaType.VERDICT_ADD,
            target_id="FND-001",
            evidence_ids=["EVD-001"],
            source_batch="batch-002",
            payload={"is_vulnerable": False},
        )

        batch1 = MergeBatch(source="attacker", deltas=[delta_vuln], graph_hash="abc123")
        batch2 = MergeBatch(source="defender", deltas=[delta_safe], graph_hash="abc123")

        result = merge_batch_deltas([batch1, batch2])

        payload_conflicts = [
            c for c in result.conflicts
            if c.conflict_type.value == "payload_divergence"
        ]
        assert len(payload_conflicts) == 1

    def test_duplicate_delta_deduplication(self, sample_delta_finding):
        """Identical deltas should be deduplicated."""
        # Same delta in two batches
        batch1 = MergeBatch(
            source="scout1",
            deltas=[sample_delta_finding],
            graph_hash="abc123",
        )
        batch2 = MergeBatch(
            source="scout2",
            deltas=[sample_delta_finding],  # Same delta
            graph_hash="abc123",
        )

        result = merge_batch_deltas([batch1, batch2])

        # Should only have one copy
        assert len(result.merged_deltas) == 1
        assert "idempotent" in " ".join(result.audit_trail).lower()

    def test_incremental_merge(self, sample_delta_finding, sample_delta_evidence):
        """Incremental merge should combine existing and new deltas."""
        existing = [sample_delta_finding]

        batch = MergeBatch(
            source="scout",
            deltas=[sample_delta_evidence],
            graph_hash="abc123",
        )

        result = merge_batch_deltas([batch], existing_deltas=existing)

        assert len(result.merged_deltas) == 2
        assert any(d.delta_type == DeltaType.FINDING_ADD for d in result.merged_deltas)
        assert any(d.delta_type == DeltaType.EVIDENCE_ADD for d in result.merged_deltas)

    def test_deterministic_ordering(self):
        """Merged deltas should be in deterministic order."""
        deltas = [
            DeltaEntry(
                delta_type=DeltaType.VERDICT_ADD,
                target_id="FND-001",
                evidence_ids=["EVD-001"],
                source_batch="batch",
                payload={},
            ),
            DeltaEntry(
                delta_type=DeltaType.FINDING_ADD,
                target_id="FND-002",
                evidence_ids=["EVD-002"],
                source_batch="batch",
                payload={},
            ),
            DeltaEntry(
                delta_type=DeltaType.EVIDENCE_ADD,
                target_id="FND-001",
                evidence_ids=["EVD-003"],
                source_batch="batch",
                payload={},
            ),
        ]

        batch = MergeBatch(source="scout", deltas=deltas, graph_hash="abc123")
        result = merge_batch_deltas([batch])

        # Order: FINDING_ADD < EVIDENCE_ADD < VERDICT_ADD
        assert result.merged_deltas[0].delta_type == DeltaType.FINDING_ADD
        assert result.merged_deltas[1].delta_type == DeltaType.EVIDENCE_ADD
        assert result.merged_deltas[2].delta_type == DeltaType.VERDICT_ADD

    def test_audit_trail(self, sample_batch):
        """Merge should produce audit trail."""
        result = merge_batch_deltas([sample_batch])

        assert len(result.audit_trail) > 0
        assert any("Processing batch" in entry for entry in result.audit_trail)
        assert any("Sorted" in entry for entry in result.audit_trail)


class TestVerifyMergeIdempotency:
    """Tests for verify_merge_idempotency function."""

    def test_same_batches_same_hash(self, sample_batch):
        """Verify idempotency with expected hash."""
        result = merge_batch_deltas([sample_batch])
        expected_hash = result.output_hash

        assert verify_merge_idempotency([sample_batch], expected_hash)

    def test_different_hash_fails(self, sample_batch):
        """Verify idempotency fails with wrong hash."""
        assert not verify_merge_idempotency([sample_batch], "wrong_hash")


class TestComputeMergedOutputHash:
    """Tests for compute_merged_output_hash function."""

    def test_deterministic_hash(self, sample_delta_finding, sample_delta_evidence):
        """Hash should be deterministic for same deltas."""
        deltas = [sample_delta_finding, sample_delta_evidence]

        hash1 = compute_merged_output_hash(deltas)
        hash2 = compute_merged_output_hash(deltas)

        assert hash1 == hash2

    def test_order_independent_hash(self, sample_delta_finding, sample_delta_evidence):
        """Hash should be order-independent (sorts by ordering_key)."""
        hash1 = compute_merged_output_hash([sample_delta_finding, sample_delta_evidence])
        hash2 = compute_merged_output_hash([sample_delta_evidence, sample_delta_finding])

        assert hash1 == hash2


# =============================================================================
# Conflict Quarantine Tests
# =============================================================================


class TestMergeConflict:
    """Tests for MergeConflict schema."""

    def test_conflict_id_deterministic(self, sample_delta_finding, conflicting_delta):
        """Conflict ID should be deterministic."""
        conflict1 = MergeConflict(
            conflict_type=ConflictType.EVIDENCE_MISMATCH,
            delta_a=sample_delta_finding,
            delta_b=conflicting_delta,
        )
        conflict2 = MergeConflict(
            conflict_type=ConflictType.EVIDENCE_MISMATCH,
            delta_a=sample_delta_finding,
            delta_b=conflicting_delta,
        )
        assert conflict1.conflict_id == conflict2.conflict_id

    def test_conflict_to_dict_roundtrip(self, sample_delta_finding, conflicting_delta):
        """Conflict should survive dict serialization roundtrip."""
        conflict = MergeConflict(
            conflict_type=ConflictType.EVIDENCE_MISMATCH,
            delta_a=sample_delta_finding,
            delta_b=conflicting_delta,
            description="Test conflict",
        )

        data = conflict.to_dict()
        restored = MergeConflict.from_dict(data)

        assert restored.conflict_id == conflict.conflict_id
        assert restored.conflict_type == conflict.conflict_type
        assert restored.description == conflict.description


class TestConflictQuarantineIntegration:
    """Integration tests for conflict quarantine flow."""

    def test_conflicts_preserved_for_audit(self):
        """Both deltas should be preserved in conflict for audit."""
        delta_a = DeltaEntry(
            delta_type=DeltaType.FINDING_ADD,
            target_id="FND-001",
            evidence_ids=["EVD-001"],
            source_batch="batch-001",
            payload={"is_vulnerable": True},
        )
        delta_b = DeltaEntry(
            delta_type=DeltaType.FINDING_ADD,
            target_id="FND-001",
            evidence_ids=["EVD-002"],  # Different evidence
            source_batch="batch-002",
            payload={"is_vulnerable": False},  # Different verdict
        )

        batch1 = MergeBatch(source="attacker", deltas=[delta_a], graph_hash="abc123")
        batch2 = MergeBatch(source="defender", deltas=[delta_b], graph_hash="abc123")

        result = merge_batch_deltas([batch1, batch2])

        assert len(result.conflicts) > 0

        # Verify both deltas preserved (order depends on ordering_key)
        conflict = result.conflicts[0]
        conflict_delta_ids = {conflict.delta_a.delta_id, conflict.delta_b.delta_id}
        expected_delta_ids = {delta_a.delta_id, delta_b.delta_id}
        assert conflict_delta_ids == expected_delta_ids

        # Serialization preserves deltas
        data = conflict.to_dict()
        assert "delta_a" in data
        assert "delta_b" in data
        # Check that both vulnerable states are captured
        vuln_values = {
            data["delta_a"]["payload"]["is_vulnerable"],
            data["delta_b"]["payload"]["is_vulnerable"],
        }
        assert vuln_values == {True, False}
