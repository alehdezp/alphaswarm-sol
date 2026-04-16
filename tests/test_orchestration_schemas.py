"""Comprehensive tests for orchestration schemas.

Tests cover:
- TestSchemas: Pool creation, status transitions, verdict confidence levels
- TestYAMLSerialization: Pool to YAML, roundtrip preservation
- TestPoolStorage: Save/load, list by status
- TestPoolManager: Create from scope, add bead, record verdict
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from alphaswarm_sol.orchestration.schemas import (
    Pool,
    PoolStatus,
    Scope,
    Verdict,
    VerdictConfidence,
    EvidenceItem,
    EvidencePacket,
    DebateClaim,
    DebateRecord,
)
from alphaswarm_sol.orchestration.pool import PoolStorage, PoolManager


class TestPoolStatus:
    """Tests for PoolStatus enum."""

    def test_all_statuses_exist(self):
        """All expected statuses should exist."""
        expected = [
            "intake", "context", "beads", "execute",
            "verify", "integrate", "complete", "failed", "paused"
        ]
        for status in expected:
            assert PoolStatus(status) is not None

    def test_from_string_case_insensitive(self):
        """from_string should handle different cases."""
        assert PoolStatus.from_string("INTAKE") == PoolStatus.INTAKE
        assert PoolStatus.from_string("intake") == PoolStatus.INTAKE
        assert PoolStatus.from_string("Intake") == PoolStatus.INTAKE
        assert PoolStatus.from_string("  execute  ") == PoolStatus.EXECUTE

    def test_is_terminal(self):
        """Terminal statuses should be identified correctly."""
        assert PoolStatus.COMPLETE.is_terminal()
        assert PoolStatus.FAILED.is_terminal()
        assert not PoolStatus.INTAKE.is_terminal()
        assert not PoolStatus.VERIFY.is_terminal()
        assert not PoolStatus.PAUSED.is_terminal()

    def test_is_active(self):
        """Active statuses should be identified correctly."""
        assert PoolStatus.INTAKE.is_active()
        assert PoolStatus.EXECUTE.is_active()
        assert not PoolStatus.COMPLETE.is_active()
        assert not PoolStatus.FAILED.is_active()
        assert not PoolStatus.PAUSED.is_active()

    def test_next_phase(self):
        """next_phase should return correct next status."""
        assert PoolStatus.INTAKE.next_phase() == PoolStatus.CONTEXT
        assert PoolStatus.CONTEXT.next_phase() == PoolStatus.BEADS
        assert PoolStatus.BEADS.next_phase() == PoolStatus.EXECUTE
        assert PoolStatus.EXECUTE.next_phase() == PoolStatus.VERIFY
        assert PoolStatus.VERIFY.next_phase() == PoolStatus.INTEGRATE
        assert PoolStatus.INTEGRATE.next_phase() == PoolStatus.COMPLETE
        assert PoolStatus.COMPLETE.next_phase() is None
        # Non-lifecycle statuses
        assert PoolStatus.FAILED.next_phase() is None
        assert PoolStatus.PAUSED.next_phase() is None


class TestVerdictConfidence:
    """Tests for VerdictConfidence enum."""

    def test_all_levels_exist(self):
        """All confidence levels should exist."""
        expected = ["confirmed", "likely", "uncertain", "rejected"]
        for level in expected:
            assert VerdictConfidence(level) is not None

    def test_from_string_case_insensitive(self):
        """from_string should handle different cases."""
        assert VerdictConfidence.from_string("CONFIRMED") == VerdictConfidence.CONFIRMED
        assert VerdictConfidence.from_string("likely") == VerdictConfidence.LIKELY
        assert VerdictConfidence.from_string("  Uncertain  ") == VerdictConfidence.UNCERTAIN

    def test_is_positive(self):
        """Positive confidences should be identified correctly."""
        assert VerdictConfidence.CONFIRMED.is_positive()
        assert VerdictConfidence.LIKELY.is_positive()
        assert not VerdictConfidence.UNCERTAIN.is_positive()
        assert not VerdictConfidence.REJECTED.is_positive()

    def test_requires_human_review(self):
        """All verdicts should require human review per PHILOSOPHY.md."""
        for confidence in VerdictConfidence:
            assert confidence.requires_human_review()


class TestScope:
    """Tests for Scope dataclass."""

    def test_creation_minimal(self):
        """Scope should be creatable with just files."""
        scope = Scope(files=["contracts/Vault.sol"])
        assert scope.files == ["contracts/Vault.sol"]
        assert scope.contracts == []
        assert scope.focus_areas == []

    def test_creation_full(self):
        """Scope should support all fields."""
        scope = Scope(
            files=["contracts/Vault.sol", "contracts/Token.sol"],
            contracts=["Vault", "VaultFactory"],
            focus_areas=["reentrancy", "access-control"],
            exclude_patterns=["**/test/**", "**/mock/**"],
            metadata={"initiated_by": "/vkg:audit"}
        )
        assert len(scope.files) == 2
        assert len(scope.contracts) == 2
        assert "reentrancy" in scope.focus_areas
        assert "**/test/**" in scope.exclude_patterns
        assert scope.metadata["initiated_by"] == "/vkg:audit"

    def test_to_dict_from_dict_roundtrip(self):
        """Scope should survive dict roundtrip."""
        original = Scope(
            files=["contracts/Vault.sol"],
            contracts=["Vault"],
            focus_areas=["reentrancy"],
            metadata={"key": "value"}
        )
        data = original.to_dict()
        restored = Scope.from_dict(data)
        assert restored.files == original.files
        assert restored.contracts == original.contracts
        assert restored.focus_areas == original.focus_areas
        assert restored.metadata == original.metadata

    def test_yaml_serialization(self):
        """Scope should serialize to valid YAML."""
        scope = Scope(
            files=["contracts/Vault.sol"],
            contracts=["Vault"],
            focus_areas=["reentrancy"]
        )
        yaml_str = scope.to_yaml()
        assert "contracts/Vault.sol" in yaml_str
        # Verify it's valid YAML
        data = yaml.safe_load(yaml_str)
        assert data["files"] == ["contracts/Vault.sol"]

    def test_yaml_roundtrip(self):
        """Scope should survive YAML roundtrip."""
        original = Scope(
            files=["contracts/Vault.sol"],
            contracts=["Vault"],
            metadata={"key": "value"}
        )
        yaml_str = original.to_yaml()
        restored = Scope.from_yaml(yaml_str)
        assert restored.files == original.files
        assert restored.contracts == original.contracts

    def test_matches_file(self):
        """matches_file should correctly check scope membership."""
        scope = Scope(
            files=["contracts/Vault.sol", "lib/"],
            exclude_patterns=["**/test/**"]
        )
        assert scope.matches_file("contracts/Vault.sol")
        assert scope.matches_file("lib/Token.sol")
        assert not scope.matches_file("other/File.sol")


class TestEvidenceItem:
    """Tests for EvidenceItem dataclass."""

    def test_creation(self):
        """EvidenceItem should be creatable with required fields."""
        item = EvidenceItem(
            type="behavioral_signature",
            value="R:bal->X:out->W:bal",
            location="contracts/Vault.sol:142"
        )
        assert item.type == "behavioral_signature"
        assert item.confidence == 1.0  # Default
        assert item.source == "vkg"  # Default

    def test_confidence_validation(self):
        """EvidenceItem should reject invalid confidence."""
        with pytest.raises(ValueError):
            EvidenceItem(
                type="test",
                value="test",
                location="test",
                confidence=1.5  # Invalid
            )
        with pytest.raises(ValueError):
            EvidenceItem(
                type="test",
                value="test",
                location="test",
                confidence=-0.1  # Invalid
            )

    def test_to_dict_from_dict_roundtrip(self):
        """EvidenceItem should survive dict roundtrip."""
        original = EvidenceItem(
            type="pattern_match",
            value="CEI violation",
            location="Vault.sol:50",
            confidence=0.95,
            source="attacker"
        )
        data = original.to_dict()
        restored = EvidenceItem.from_dict(data)
        assert restored.type == original.type
        assert restored.value == original.value
        assert restored.location == original.location
        assert restored.confidence == original.confidence
        assert restored.source == original.source


class TestEvidencePacket:
    """Tests for EvidencePacket dataclass."""

    def test_creation_empty(self):
        """EvidencePacket should be creatable with just finding_id."""
        packet = EvidencePacket(finding_id="VKG-042")
        assert packet.finding_id == "VKG-042"
        assert packet.items == []

    def test_add_item(self):
        """add_item should add evidence to the packet."""
        packet = EvidencePacket(finding_id="VKG-042")
        item = EvidenceItem(type="test", value="value", location="loc")
        packet.add_item(item)
        assert len(packet.items) == 1
        assert packet.items[0] == item

    def test_get_by_type(self):
        """get_by_type should filter items correctly."""
        packet = EvidencePacket(
            finding_id="VKG-042",
            items=[
                EvidenceItem(type="signature", value="v1", location="l1"),
                EvidenceItem(type="pattern", value="v2", location="l2"),
                EvidenceItem(type="signature", value="v3", location="l3"),
            ]
        )
        signatures = packet.get_by_type("signature")
        assert len(signatures) == 2

    def test_get_by_source(self):
        """get_by_source should filter items correctly."""
        packet = EvidencePacket(
            finding_id="VKG-042",
            items=[
                EvidenceItem(type="t1", value="v1", location="l1", source="vkg"),
                EvidenceItem(type="t2", value="v2", location="l2", source="attacker"),
                EvidenceItem(type="t3", value="v3", location="l3", source="vkg"),
            ]
        )
        vkg_items = packet.get_by_source("vkg")
        assert len(vkg_items) == 2

    def test_average_confidence(self):
        """average_confidence should calculate correctly."""
        packet = EvidencePacket(
            finding_id="VKG-042",
            items=[
                EvidenceItem(type="t1", value="v1", location="l1", confidence=0.8),
                EvidenceItem(type="t2", value="v2", location="l2", confidence=1.0),
            ]
        )
        assert packet.average_confidence == 0.9

    def test_average_confidence_empty(self):
        """average_confidence should return 0 for empty packet."""
        packet = EvidencePacket(finding_id="VKG-042")
        assert packet.average_confidence == 0.0

    def test_locations(self):
        """locations should return unique locations."""
        packet = EvidencePacket(
            finding_id="VKG-042",
            items=[
                EvidenceItem(type="t1", value="v1", location="loc1"),
                EvidenceItem(type="t2", value="v2", location="loc2"),
                EvidenceItem(type="t3", value="v3", location="loc1"),  # Duplicate
            ]
        )
        locs = packet.locations
        assert len(locs) == 2
        assert "loc1" in locs
        assert "loc2" in locs

    def test_yaml_roundtrip(self):
        """EvidencePacket should survive YAML roundtrip."""
        original = EvidencePacket(
            finding_id="VKG-042",
            items=[
                EvidenceItem(type="sig", value="R:bal", location="Vault.sol:142"),
            ],
            summary="Reentrancy detected"
        )
        yaml_str = original.to_yaml()
        restored = EvidencePacket.from_yaml(yaml_str)
        assert restored.finding_id == original.finding_id
        assert len(restored.items) == 1
        assert restored.summary == original.summary


class TestDebateClaim:
    """Tests for DebateClaim dataclass."""

    def test_creation(self):
        """DebateClaim should be creatable with required fields."""
        claim = DebateClaim(
            role="attacker",
            claim="This is exploitable",
            evidence=[
                EvidenceItem(type="sig", value="CEI", location="Vault.sol:50")
            ],
            reasoning="External call before state update"
        )
        assert claim.role == "attacker"
        assert claim.claim == "This is exploitable"
        assert len(claim.evidence) == 1

    def test_to_dict_from_dict_roundtrip(self):
        """DebateClaim should survive dict roundtrip."""
        original = DebateClaim(
            role="defender",
            claim="This is safe",
            evidence=[
                EvidenceItem(type="guard", value="nonReentrant", location="Vault.sol:40")
            ],
            reasoning="Reentrancy guard present"
        )
        data = original.to_dict()
        restored = DebateClaim.from_dict(data)
        assert restored.role == original.role
        assert restored.claim == original.claim
        assert restored.reasoning == original.reasoning
        assert len(restored.evidence) == len(original.evidence)


class TestDebateRecord:
    """Tests for DebateRecord dataclass."""

    def test_creation_empty(self):
        """DebateRecord should be creatable with just finding_id."""
        record = DebateRecord(finding_id="VKG-042")
        assert record.finding_id == "VKG-042"
        assert record.attacker_claim is None
        assert record.defender_claim is None
        assert record.rebuttals == []
        assert not record.is_complete

    def test_add_rebuttal(self):
        """add_rebuttal should add to rebuttals list."""
        record = DebateRecord(finding_id="VKG-042")
        rebuttal = DebateClaim(
            role="attacker",
            claim="Counter-argument",
            evidence=[],
            reasoning="Because..."
        )
        record.add_rebuttal(rebuttal)
        assert len(record.rebuttals) == 1

    def test_complete(self):
        """complete should mark record as complete."""
        record = DebateRecord(finding_id="VKG-042")
        assert not record.is_complete
        record.complete("Summary of debate", "Dissenting view")
        assert record.is_complete
        assert record.verifier_summary == "Summary of debate"
        assert record.dissenting_opinion == "Dissenting view"
        assert record.completed_at is not None

    def test_has_claims(self):
        """has_claims should check for both claims."""
        record = DebateRecord(finding_id="VKG-042")
        assert not record.has_claims

        record.attacker_claim = DebateClaim(
            role="attacker", claim="c", evidence=[], reasoning="r"
        )
        assert not record.has_claims

        record.defender_claim = DebateClaim(
            role="defender", claim="c", evidence=[], reasoning="r"
        )
        assert record.has_claims

    def test_yaml_roundtrip(self):
        """DebateRecord should survive YAML roundtrip."""
        original = DebateRecord(
            finding_id="VKG-042",
            attacker_claim=DebateClaim(
                role="attacker",
                claim="Exploitable",
                evidence=[EvidenceItem(type="t", value="v", location="l")],
                reasoning="Because"
            ),
            defender_claim=DebateClaim(
                role="defender",
                claim="Safe",
                evidence=[],
                reasoning="Guard present"
            ),
        )
        original.complete("Verifier says likely", "Defender notes edge case")

        yaml_str = original.to_yaml()
        restored = DebateRecord.from_yaml(yaml_str)
        assert restored.finding_id == original.finding_id
        assert restored.attacker_claim is not None
        assert restored.defender_claim is not None
        assert restored.is_complete
        assert restored.verifier_summary == original.verifier_summary


class TestVerdict:
    """Tests for Verdict dataclass."""

    def test_creation_minimal(self):
        """Verdict should be creatable with minimal fields."""
        verdict = Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="CEI violation detected"
        )
        assert verdict.finding_id == "VKG-042"
        assert verdict.confidence == VerdictConfidence.LIKELY
        assert verdict.is_vulnerable
        assert verdict.human_flag  # Always True

    def test_human_flag_always_true(self):
        """human_flag should always be True per PHILOSOPHY.md."""
        verdict = Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.REJECTED,
            is_vulnerable=False,
            rationale="False positive",
            human_flag=False  # Try to set False
        )
        assert verdict.human_flag  # Should still be True

    def test_confirmed_requires_evidence(self):
        """CONFIRMED verdict should require evidence."""
        with pytest.raises(ValueError):
            Verdict(
                finding_id="VKG-042",
                confidence=VerdictConfidence.CONFIRMED,
                is_vulnerable=True,
                rationale="Confirmed",
                evidence_packet=None  # No evidence
            )

    def test_confirmed_with_evidence_ok(self):
        """CONFIRMED verdict with evidence should be OK."""
        evidence = EvidencePacket(
            finding_id="VKG-042",
            items=[EvidenceItem(type="test", value="v", location="l")]
        )
        verdict = Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.CONFIRMED,
            is_vulnerable=True,
            rationale="Test passed",
            evidence_packet=evidence
        )
        assert verdict.confidence == VerdictConfidence.CONFIRMED

    def test_requires_action(self):
        """requires_action should identify actionable verdicts."""
        vulnerable_likely = Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="r"
        )
        assert vulnerable_likely.requires_action

        safe_rejected = Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.REJECTED,
            is_vulnerable=False,
            rationale="r"
        )
        assert not safe_rejected.requires_action

        uncertain = Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.UNCERTAIN,
            is_vulnerable=True,
            rationale="r"
        )
        assert not uncertain.requires_action

    def test_summary(self):
        """summary should provide one-line summary."""
        verdict = Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="r"
        )
        assert "VKG-042" in verdict.summary
        assert "VULNERABLE" in verdict.summary
        assert "likely" in verdict.summary

    def test_yaml_roundtrip(self):
        """Verdict should survive YAML roundtrip."""
        evidence = EvidencePacket(
            finding_id="VKG-042",
            items=[EvidenceItem(type="sig", value="v", location="l")]
        )
        original = Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.CONFIRMED,
            is_vulnerable=True,
            rationale="Test passed",
            evidence_packet=evidence,
            created_by="vkg-verifier"
        )
        yaml_str = original.to_yaml()
        restored = Verdict.from_yaml(yaml_str)
        assert restored.finding_id == original.finding_id
        assert restored.confidence == original.confidence
        assert restored.is_vulnerable == original.is_vulnerable
        assert restored.created_by == original.created_by
        assert len(restored.evidence_packet.items) == 1


class TestPool:
    """Tests for Pool dataclass."""

    def test_creation_minimal(self):
        """Pool should be creatable with scope."""
        scope = Scope(files=["contracts/Vault.sol"])
        pool = Pool(id="test-pool", scope=scope)
        assert pool.id == "test-pool"
        assert pool.status == PoolStatus.INTAKE
        assert pool.bead_ids == []
        assert pool.verdicts == {}

    def test_id_auto_generation(self):
        """Pool should auto-generate ID if not provided."""
        scope = Scope(files=["contracts/Vault.sol"])
        pool = Pool(id="", scope=scope)
        assert pool.id.startswith("pool-")
        assert len(pool.id) > 5

    def test_add_bead(self):
        """add_bead should add unique beads."""
        scope = Scope(files=["contracts/Vault.sol"])
        pool = Pool(id="test-pool", scope=scope)
        pool.add_bead("VKG-042")
        pool.add_bead("VKG-043")
        pool.add_bead("VKG-042")  # Duplicate
        assert pool.bead_ids == ["VKG-042", "VKG-043"]

    def test_remove_bead(self):
        """remove_bead should remove existing beads."""
        scope = Scope(files=["contracts/Vault.sol"])
        pool = Pool(id="test-pool", scope=scope, bead_ids=["VKG-042", "VKG-043"])
        assert pool.remove_bead("VKG-042")
        assert pool.bead_ids == ["VKG-043"]
        assert not pool.remove_bead("VKG-999")  # Not found

    def test_record_verdict(self):
        """record_verdict should store verdict."""
        scope = Scope(files=["contracts/Vault.sol"])
        pool = Pool(id="test-pool", scope=scope)
        verdict = Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="r"
        )
        pool.record_verdict(verdict)
        assert "VKG-042" in pool.verdicts
        assert pool.verdicts["VKG-042"] == verdict

    def test_get_verdict(self):
        """get_verdict should return verdict or None."""
        scope = Scope(files=["contracts/Vault.sol"])
        pool = Pool(id="test-pool", scope=scope)
        verdict = Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="r"
        )
        pool.record_verdict(verdict)
        assert pool.get_verdict("VKG-042") == verdict
        assert pool.get_verdict("VKG-999") is None

    def test_advance_phase(self):
        """advance_phase should move through lifecycle."""
        scope = Scope(files=["contracts/Vault.sol"])
        pool = Pool(id="test-pool", scope=scope)
        assert pool.status == PoolStatus.INTAKE

        assert pool.advance_phase()
        assert pool.status == PoolStatus.CONTEXT
        assert "intake" in pool.phases_complete

        assert pool.advance_phase()
        assert pool.status == PoolStatus.BEADS

        # Advance to complete
        while pool.advance_phase():
            pass
        assert pool.status == PoolStatus.COMPLETE
        assert not pool.advance_phase()  # Can't advance past complete

    def test_fail(self):
        """fail should mark pool as failed."""
        scope = Scope(files=["contracts/Vault.sol"])
        pool = Pool(id="test-pool", scope=scope)
        pool.fail("Something went wrong")
        assert pool.status == PoolStatus.FAILED
        assert pool.metadata["failure_reason"] == "Something went wrong"

    def test_pause_resume(self):
        """pause and resume should work correctly."""
        scope = Scope(files=["contracts/Vault.sol"])
        pool = Pool(id="test-pool", scope=scope)
        pool.advance_phase()  # CONTEXT
        pool.advance_phase()  # BEADS

        pool.pause("Waiting for human input")
        assert pool.status == PoolStatus.PAUSED
        assert pool.metadata["pause_reason"] == "Waiting for human input"

        pool.resume()
        assert pool.status == PoolStatus.EXECUTE  # Next after BEADS
        assert "pause_reason" not in pool.metadata

    def test_pending_completed_beads(self):
        """pending_beads and completed_beads should work correctly."""
        scope = Scope(files=["contracts/Vault.sol"])
        pool = Pool(
            id="test-pool",
            scope=scope,
            bead_ids=["VKG-042", "VKG-043", "VKG-044"]
        )
        verdict = Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="r"
        )
        pool.record_verdict(verdict)

        assert pool.pending_beads == ["VKG-043", "VKG-044"]
        assert pool.completed_beads == ["VKG-042"]

    def test_vulnerable_confirmed_counts(self):
        """vulnerable_count and confirmed_count should work correctly."""
        scope = Scope(files=["contracts/Vault.sol"])
        pool = Pool(id="test-pool", scope=scope)

        # Add verdicts
        evidence = EvidencePacket(
            finding_id="VKG-042",
            items=[EvidenceItem(type="t", value="v", location="l")]
        )
        pool.record_verdict(Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.CONFIRMED,
            is_vulnerable=True,
            rationale="r",
            evidence_packet=evidence
        ))
        pool.record_verdict(Verdict(
            finding_id="VKG-043",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="r"
        ))
        pool.record_verdict(Verdict(
            finding_id="VKG-044",
            confidence=VerdictConfidence.REJECTED,
            is_vulnerable=False,
            rationale="r"
        ))

        assert pool.vulnerable_count == 2
        assert pool.confirmed_count == 1

    def test_yaml_roundtrip(self):
        """Pool should survive YAML roundtrip."""
        scope = Scope(
            files=["contracts/Vault.sol"],
            contracts=["Vault"],
            focus_areas=["reentrancy"]
        )
        original = Pool(
            id="test-pool",
            scope=scope,
            bead_ids=["VKG-042", "VKG-043"],
            initiated_by="/vkg:audit",
            metadata={"key": "value"}
        )
        original.advance_phase()
        original.record_verdict(Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="r"
        ))

        yaml_str = original.to_yaml()
        restored = Pool.from_yaml(yaml_str)

        assert restored.id == original.id
        assert restored.scope.files == original.scope.files
        assert restored.bead_ids == original.bead_ids
        assert restored.status == original.status
        assert restored.initiated_by == original.initiated_by
        assert "VKG-042" in restored.verdicts


class TestPoolStorage:
    """Tests for PoolStorage class."""

    def test_save_and_load(self):
        """save_pool and get_pool should work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PoolStorage(Path(tmpdir))
            scope = Scope(files=["contracts/Vault.sol"])
            pool = Pool(id="test-pool", scope=scope)
            pool.add_bead("VKG-042")

            path = storage.save_pool(pool)
            assert path.exists()
            assert path.name == "test-pool.yaml"

            loaded = storage.get_pool("test-pool")
            assert loaded is not None
            assert loaded.id == "test-pool"
            assert loaded.bead_ids == ["VKG-042"]

    def test_get_pool_not_found(self):
        """get_pool should return None for missing pool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PoolStorage(Path(tmpdir))
            assert storage.get_pool("nonexistent") is None

    def test_list_pools(self):
        """list_pools should return all pools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PoolStorage(Path(tmpdir))
            scope = Scope(files=["f1.sol"])

            pool1 = Pool(id="pool-1", scope=scope)
            pool2 = Pool(id="pool-2", scope=scope)
            storage.save_pool(pool1)
            storage.save_pool(pool2)

            pools = storage.list_pools()
            assert len(pools) == 2
            ids = [p.id for p in pools]
            assert "pool-1" in ids
            assert "pool-2" in ids

    def test_list_pools_by_status(self):
        """list_pools_by_status should filter correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PoolStorage(Path(tmpdir))
            scope = Scope(files=["f1.sol"])

            pool1 = Pool(id="pool-1", scope=scope)
            pool2 = Pool(id="pool-2", scope=scope)
            pool2.advance_phase()  # CONTEXT
            pool3 = Pool(id="pool-3", scope=scope)
            pool3.fail("error")

            storage.save_pool(pool1)
            storage.save_pool(pool2)
            storage.save_pool(pool3)

            intake_pools = storage.list_pools_by_status(PoolStatus.INTAKE)
            assert len(intake_pools) == 1
            assert intake_pools[0].id == "pool-1"

            failed_pools = storage.list_pools_by_status(PoolStatus.FAILED)
            assert len(failed_pools) == 1
            assert failed_pools[0].id == "pool-3"

    def test_list_active_pools(self):
        """list_active_pools should return only active pools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PoolStorage(Path(tmpdir))
            scope = Scope(files=["f1.sol"])

            pool1 = Pool(id="pool-1", scope=scope)  # INTAKE - active
            pool2 = Pool(id="pool-2", scope=scope)
            pool2.fail("error")  # FAILED - not active
            pool3 = Pool(id="pool-3", scope=scope)
            pool3.pause("waiting")  # PAUSED - not active

            storage.save_pool(pool1)
            storage.save_pool(pool2)
            storage.save_pool(pool3)

            active = storage.list_active_pools()
            assert len(active) == 1
            assert active[0].id == "pool-1"

    def test_delete_pool(self):
        """delete_pool should remove pool file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PoolStorage(Path(tmpdir))
            scope = Scope(files=["f1.sol"])
            pool = Pool(id="test-pool", scope=scope)
            storage.save_pool(pool)

            assert storage.exists("test-pool")
            assert storage.delete_pool("test-pool")
            assert not storage.exists("test-pool")
            assert not storage.delete_pool("test-pool")  # Already deleted

    def test_clear(self):
        """clear should remove all pools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PoolStorage(Path(tmpdir))
            scope = Scope(files=["f1.sol"])

            storage.save_pool(Pool(id="pool-1", scope=scope))
            storage.save_pool(Pool(id="pool-2", scope=scope))
            assert storage.count() == 2

            deleted = storage.clear()
            assert deleted == 2
            assert storage.count() == 0

    def test_get_summary(self):
        """get_summary should return aggregate statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = PoolStorage(Path(tmpdir))
            scope = Scope(files=["f1.sol"])

            pool1 = Pool(id="pool-1", scope=scope, bead_ids=["b1", "b2"])
            pool1.record_verdict(Verdict(
                finding_id="b1",
                confidence=VerdictConfidence.LIKELY,
                is_vulnerable=True,
                rationale="r"
            ))
            pool2 = Pool(id="pool-2", scope=scope, bead_ids=["b3"])
            pool2.advance_phase()

            storage.save_pool(pool1)
            storage.save_pool(pool2)

            summary = storage.get_summary()
            assert summary["total_pools"] == 2
            assert summary["by_status"]["intake"] == 1
            assert summary["by_status"]["context"] == 1
            assert summary["total_beads"] == 3
            assert summary["total_verdicts"] == 1
            assert summary["vulnerable_count"] == 1


class TestPoolManager:
    """Tests for PoolManager class."""

    def test_create_pool(self):
        """create_pool should create and persist pool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["contracts/Vault.sol"])

            pool = manager.create_pool(
                scope=scope,
                pool_id="my-pool",
                initiated_by="/vkg:audit",
                metadata={"key": "value"}
            )

            assert pool.id == "my-pool"
            assert pool.initiated_by == "/vkg:audit"

            # Verify persisted
            loaded = manager.get_pool("my-pool")
            assert loaded is not None
            assert loaded.id == "my-pool"

    def test_create_pool_auto_id(self):
        """create_pool should auto-generate ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["contracts/Vault.sol"])

            pool = manager.create_pool(scope=scope)
            assert pool.id.startswith("pool-")

    def test_add_bead(self):
        """add_bead should add bead to pool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["f1.sol"])
            pool = manager.create_pool(scope=scope, pool_id="my-pool")

            assert manager.add_bead("my-pool", "VKG-042")
            assert not manager.add_bead("nonexistent", "VKG-042")

            loaded = manager.get_pool("my-pool")
            assert "VKG-042" in loaded.bead_ids

    def test_add_beads(self):
        """add_beads should add multiple beads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["f1.sol"])
            pool = manager.create_pool(scope=scope, pool_id="my-pool")

            assert manager.add_beads("my-pool", ["VKG-042", "VKG-043", "VKG-044"])

            loaded = manager.get_pool("my-pool")
            assert len(loaded.bead_ids) == 3

    def test_remove_bead(self):
        """remove_bead should remove bead from pool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["f1.sol"])
            pool = manager.create_pool(scope=scope, pool_id="my-pool")
            manager.add_beads("my-pool", ["VKG-042", "VKG-043"])

            assert manager.remove_bead("my-pool", "VKG-042")

            loaded = manager.get_pool("my-pool")
            assert loaded.bead_ids == ["VKG-043"]

    def test_record_verdict(self):
        """record_verdict should record verdict in pool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["f1.sol"])
            pool = manager.create_pool(scope=scope, pool_id="my-pool")

            verdict = Verdict(
                finding_id="VKG-042",
                confidence=VerdictConfidence.LIKELY,
                is_vulnerable=True,
                rationale="r"
            )
            assert manager.record_verdict("my-pool", verdict)

            loaded = manager.get_pool("my-pool")
            assert "VKG-042" in loaded.verdicts

    def test_advance_phase(self):
        """advance_phase should advance pool status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["f1.sol"])
            manager.create_pool(scope=scope, pool_id="my-pool")

            status = manager.advance_phase("my-pool")
            assert status == PoolStatus.CONTEXT

            loaded = manager.get_pool("my-pool")
            assert loaded.status == PoolStatus.CONTEXT

    def test_set_status(self):
        """set_status should set pool status directly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["f1.sol"])
            manager.create_pool(scope=scope, pool_id="my-pool")

            assert manager.set_status("my-pool", PoolStatus.EXECUTE)

            loaded = manager.get_pool("my-pool")
            assert loaded.status == PoolStatus.EXECUTE

    def test_fail_pool(self):
        """fail_pool should mark pool as failed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["f1.sol"])
            manager.create_pool(scope=scope, pool_id="my-pool")

            assert manager.fail_pool("my-pool", "Something went wrong")

            loaded = manager.get_pool("my-pool")
            assert loaded.status == PoolStatus.FAILED

    def test_pause_resume_pool(self):
        """pause_pool and resume_pool should work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["f1.sol"])
            manager.create_pool(scope=scope, pool_id="my-pool")
            manager.advance_phase("my-pool")  # CONTEXT

            assert manager.pause_pool("my-pool", "Waiting")

            loaded = manager.get_pool("my-pool")
            assert loaded.status == PoolStatus.PAUSED

            assert manager.resume_pool("my-pool")

            loaded = manager.get_pool("my-pool")
            assert loaded.status == PoolStatus.BEADS  # Next after CONTEXT

    def test_get_pending_beads(self):
        """get_pending_beads should return beads without verdicts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["f1.sol"])
            manager.create_pool(scope=scope, pool_id="my-pool")
            manager.add_beads("my-pool", ["VKG-042", "VKG-043", "VKG-044"])

            verdict = Verdict(
                finding_id="VKG-042",
                confidence=VerdictConfidence.LIKELY,
                is_vulnerable=True,
                rationale="r"
            )
            manager.record_verdict("my-pool", verdict)

            pending = manager.get_pending_beads("my-pool")
            assert pending == ["VKG-043", "VKG-044"]

    def test_get_pools_by_status(self):
        """get_pools_by_status should filter pools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["f1.sol"])

            manager.create_pool(scope=scope, pool_id="pool-1")
            manager.create_pool(scope=scope, pool_id="pool-2")
            manager.advance_phase("pool-2")

            intake_pools = manager.get_pools_by_status(PoolStatus.INTAKE)
            assert len(intake_pools) == 1
            assert intake_pools[0].id == "pool-1"

    def test_get_active_pools(self):
        """get_active_pools should return active pools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["f1.sol"])

            manager.create_pool(scope=scope, pool_id="pool-1")
            manager.create_pool(scope=scope, pool_id="pool-2")
            manager.fail_pool("pool-2", "error")

            active = manager.get_active_pools()
            assert len(active) == 1
            assert active[0].id == "pool-1"

    def test_delete_pool(self):
        """delete_pool should remove pool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["f1.sol"])
            manager.create_pool(scope=scope, pool_id="my-pool")

            assert manager.delete_pool("my-pool")
            assert manager.get_pool("my-pool") is None

    def test_update_pool(self):
        """update_pool should apply custom update function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PoolManager(Path(tmpdir))
            scope = Scope(files=["f1.sol"])
            manager.create_pool(scope=scope, pool_id="my-pool")

            def add_metadata(pool: Pool) -> None:
                pool.metadata["custom"] = "value"

            assert manager.update_pool("my-pool", add_metadata)

            loaded = manager.get_pool("my-pool")
            assert loaded.metadata["custom"] == "value"


class TestYAMLSerialization:
    """Tests focused on YAML serialization for human readability."""

    def test_pool_yaml_human_readable(self):
        """Pool YAML should be human-readable."""
        scope = Scope(
            files=["contracts/Vault.sol"],
            contracts=["Vault"],
            focus_areas=["reentrancy", "access-control"]
        )
        pool = Pool(
            id="audit-wave-erc4626",
            scope=scope,
            bead_ids=["VKG-042", "VKG-043"],
            initiated_by="/vkg:audit"
        )

        yaml_str = pool.to_yaml()

        # Check human-readable format
        assert "id: audit-wave-erc4626" in yaml_str
        assert "status: intake" in yaml_str
        assert "- contracts/Vault.sol" in yaml_str
        assert "- VKG-042" in yaml_str

        # Verify it's valid YAML
        data = yaml.safe_load(yaml_str)
        assert data["id"] == "audit-wave-erc4626"

    def test_verdict_yaml_human_readable(self):
        """Verdict YAML should be human-readable."""
        evidence = EvidencePacket(
            finding_id="VKG-042",
            items=[
                EvidenceItem(
                    type="behavioral_signature",
                    value="R:bal->X:out->W:bal",
                    location="contracts/Vault.sol:142"
                )
            ],
            summary="Reentrancy pattern detected"
        )
        verdict = Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="External call before state update, no guard present",
            evidence_packet=evidence
        )

        yaml_str = verdict.to_yaml()

        # Check human-readable format
        assert "finding_id: VKG-042" in yaml_str
        assert "confidence: likely" in yaml_str
        assert "is_vulnerable: true" in yaml_str
        assert "R:bal->X:out->W:bal" in yaml_str

    def test_debate_record_yaml_human_readable(self):
        """DebateRecord YAML should be human-readable."""
        record = DebateRecord(
            finding_id="VKG-042",
            attacker_claim=DebateClaim(
                role="attacker",
                claim="This is exploitable via reentrancy",
                evidence=[
                    EvidenceItem(
                        type="signature",
                        value="External call at L142 before balance update at L145",
                        location="Vault.sol:142"
                    )
                ],
                reasoning="The CEI pattern is violated"
            ),
            defender_claim=DebateClaim(
                role="defender",
                claim="This is protected by reentrancy guard",
                evidence=[
                    EvidenceItem(
                        type="guard",
                        value="nonReentrant modifier present",
                        location="Vault.sol:140"
                    )
                ],
                reasoning="The modifier prevents reentry"
            )
        )
        record.complete(
            "Attacker's claim is stronger - guard is on wrong function",
            "Defender notes the guard exists but on deposit(), not withdraw()"
        )

        yaml_str = record.to_yaml()

        # Check human-readable format
        assert "attacker_claim:" in yaml_str
        assert "defender_claim:" in yaml_str
        assert "verifier_summary:" in yaml_str
        assert "dissenting_opinion:" in yaml_str

    def test_complex_pool_roundtrip(self):
        """Complex pool with verdicts should survive roundtrip."""
        scope = Scope(
            files=["contracts/Vault.sol", "contracts/Token.sol"],
            contracts=["Vault", "VaultFactory"],
            focus_areas=["reentrancy"],
            exclude_patterns=["**/test/**"],
            metadata={"initiated_by": "/vkg:audit", "priority": "high"}
        )

        evidence = EvidencePacket(
            finding_id="VKG-042",
            items=[
                EvidenceItem(
                    type="behavioral_signature",
                    value="R:bal->X:out->W:bal",
                    location="Vault.sol:142",
                    confidence=0.95,
                    source="vkg"
                )
            ],
            summary="Reentrancy pattern"
        )

        debate = DebateRecord(finding_id="VKG-042")
        debate.attacker_claim = DebateClaim(
            role="attacker",
            claim="Exploitable",
            evidence=[EvidenceItem(type="t", value="v", location="l")],
            reasoning="Because"
        )
        debate.complete("Likely vulnerable", "")

        verdict = Verdict(
            finding_id="VKG-042",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="CEI violation",
            evidence_packet=evidence,
            debate=debate,
            created_by="vkg-verifier"
        )

        original = Pool(
            id="complex-pool",
            scope=scope,
            bead_ids=["VKG-042", "VKG-043", "VKG-044"],
            initiated_by="/vkg:audit",
            metadata={"wave": 1}
        )
        original.advance_phase()
        original.advance_phase()
        original.record_verdict(verdict)

        # Roundtrip
        yaml_str = original.to_yaml()
        restored = Pool.from_yaml(yaml_str)

        # Verify all data preserved
        assert restored.id == original.id
        assert restored.scope.files == original.scope.files
        assert restored.scope.metadata == original.scope.metadata
        assert restored.bead_ids == original.bead_ids
        assert restored.status == original.status
        assert len(restored.phases_complete) == len(original.phases_complete)
        assert "VKG-042" in restored.verdicts
        assert restored.verdicts["VKG-042"].debate is not None
        assert restored.verdicts["VKG-042"].debate.is_complete


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
