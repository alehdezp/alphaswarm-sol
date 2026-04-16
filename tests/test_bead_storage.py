"""Tests for bead storage module."""

import json
import pytest
from pathlib import Path

from alphaswarm_sol.beads.storage import BeadStorage
from alphaswarm_sol.beads.schema import (
    VulnerabilityBead,
    CodeSnippet,
    PatternContext,
    InvestigationGuide,
    TestContext,
)
from alphaswarm_sol.beads.types import (
    Severity,
    BeadStatus,
    InvestigationStep,
)


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary bead storage."""
    storage_path = tmp_path / "beads"
    return BeadStorage(storage_path)


@pytest.fixture
def sample_bead():
    """Create a sample bead for testing."""
    return VulnerabilityBead(
        id="VKG-0001-abc123",
        vulnerability_class="reentrancy",
        pattern_id="vm-001",
        severity=Severity.CRITICAL,
        confidence=0.95,
        status=BeadStatus.PENDING,
        vulnerable_code=CodeSnippet(
            source="function withdraw() { msg.sender.call{value: amount}(''); balance = 0; }",
            file_path="/contracts/Vault.sol",
            start_line=10,
            end_line=15,
            function_name="withdraw",
            contract_name="Vault",
        ),
        pattern_context=PatternContext(
            pattern_name="Basic Reentrancy",
            pattern_description="Detects external calls before state updates",
            why_flagged="State write after external call",
            matched_properties=["state_write_after_external_call"],
            evidence_lines=[10, 11],
        ),
        investigation_guide=InvestigationGuide(
            steps=[
                InvestigationStep(
                    step_number=1,
                    action="Check for reentrancy guards",
                    look_for="nonReentrant modifier",
                    evidence_needed="No guard found on function",
                    red_flag="No guard found",
                    safe_if="Has nonReentrant modifier",
                ),
            ],
            questions_to_answer=["Is there a reentrancy guard?"],
            common_false_positives=["View functions"],
            key_indicators=["External call before state write"],
            safe_patterns=["CEI pattern"],
        ),
        test_context=TestContext(
            scaffold_code="// Test scaffold",
            attack_scenario="Attacker re-enters during withdrawal",
            setup_requirements=["Deploy Vault", "Fund with ETH"],
            expected_outcome="Attacker drains contract",
        ),
        related_code=[],
        full_contract=None,
        similar_exploits=[],
        fix_recommendations=["Use nonReentrant modifier"],
        inheritance_chain=["Ownable"],
        context_hash="abc123",
    )


class TestBeadStorageBasics:
    """Tests for basic storage operations."""

    def test_storage_creates_directory(self, tmp_path):
        """Storage creates directory if it doesn't exist."""
        storage_path = tmp_path / "new_dir" / "beads"
        assert not storage_path.exists()

        storage = BeadStorage(storage_path)

        assert storage_path.exists()
        assert storage.path == storage_path

    def test_save_bead(self, temp_storage, sample_bead):
        """Save bead to storage."""
        path = temp_storage.save_bead(sample_bead)

        assert path.exists()
        assert path.name == f"{sample_bead.id}.json"

    def test_get_bead(self, temp_storage, sample_bead):
        """Load bead by ID."""
        temp_storage.save_bead(sample_bead)

        loaded = temp_storage.get_bead(sample_bead.id)

        assert loaded is not None
        assert loaded.id == sample_bead.id
        assert loaded.vulnerability_class == sample_bead.vulnerability_class
        assert loaded.severity == sample_bead.severity

    def test_get_bead_not_found(self, temp_storage):
        """Get bead returns None if not found."""
        result = temp_storage.get_bead("VKG-XXXX")
        assert result is None

    def test_list_beads_empty(self, temp_storage):
        """List beads on empty storage returns empty list."""
        beads = temp_storage.list_beads()
        assert beads == []

    def test_list_beads(self, temp_storage, sample_bead):
        """List all beads in storage."""
        temp_storage.save_bead(sample_bead)

        # Add second bead
        second_bead = VulnerabilityBead(
            id="VKG-0002-def456",
            vulnerability_class="access_control",
            pattern_id="auth-001",
            severity=Severity.HIGH,
            confidence=0.85,
            status=BeadStatus.PENDING,
            vulnerable_code=CodeSnippet(
                source="function setOwner(address newOwner) public { owner = newOwner; }",
                file_path="/contracts/Vault.sol",
                start_line=20,
                end_line=22,
                function_name="setOwner",
                contract_name="Vault",
            ),
            pattern_context=PatternContext(
                pattern_name="Missing Access Control",
                pattern_description="Detects functions missing access control",
                why_flagged="Public function modifies privileged state",
                matched_properties=["writes_privileged_state"],
                evidence_lines=[20, 21],
            ),
            investigation_guide=InvestigationGuide(
                steps=[
                    InvestigationStep(
                        step_number=1,
                        action="Check access modifiers",
                        look_for="onlyOwner modifier",
                        evidence_needed="No access control modifier found",
                        red_flag="No access control",
                        safe_if="Has proper modifier",
                    ),
                ],
                questions_to_answer=["Who can call this function?"],
                common_false_positives=["Initializers"],
                key_indicators=["Missing modifier"],
                safe_patterns=["onlyOwner pattern"],
            ),
            test_context=TestContext(
                scaffold_code="// Test scaffold",
                attack_scenario="Anyone can take ownership",
                setup_requirements=["Deploy contract"],
                expected_outcome="Attacker becomes owner",
            ),
            related_code=[],
            full_contract=None,
            similar_exploits=[],
            fix_recommendations=["Add onlyOwner modifier"],
            inheritance_chain=[],
            context_hash="def456",
        )
        temp_storage.save_bead(second_bead)

        beads = temp_storage.list_beads()
        assert len(beads) == 2


class TestBeadStorageFilters:
    """Tests for filtered listing."""

    def test_list_beads_by_status(self, temp_storage, sample_bead):
        """List beads filtered by status."""
        temp_storage.save_bead(sample_bead)

        # Change status and save another
        sample_bead.id = "VKG-0002-xyz"
        sample_bead.status = BeadStatus.CONFIRMED
        sample_bead.context_hash = "xyz789"
        temp_storage.save_bead(sample_bead)

        pending = temp_storage.list_beads_by_status(BeadStatus.PENDING)
        confirmed = temp_storage.list_beads_by_status(BeadStatus.CONFIRMED)

        assert len(pending) == 1
        assert len(confirmed) == 1

    def test_list_beads_by_severity(self, temp_storage, sample_bead):
        """List beads filtered by severity."""
        temp_storage.save_bead(sample_bead)

        critical = temp_storage.list_beads_by_severity(Severity.CRITICAL)
        high = temp_storage.list_beads_by_severity(Severity.HIGH)

        assert len(critical) == 1
        assert len(high) == 0

    def test_list_beads_by_class(self, temp_storage, sample_bead):
        """List beads filtered by vulnerability class."""
        temp_storage.save_bead(sample_bead)

        reentrancy = temp_storage.list_beads_by_class("reentrancy")
        access = temp_storage.list_beads_by_class("access_control")

        assert len(reentrancy) == 1
        assert len(access) == 0


class TestBeadStorageDelete:
    """Tests for delete operations."""

    def test_delete_bead(self, temp_storage, sample_bead):
        """Delete a bead from storage."""
        temp_storage.save_bead(sample_bead)
        assert temp_storage.get_bead(sample_bead.id) is not None

        result = temp_storage.delete_bead(sample_bead.id)

        assert result is True
        assert temp_storage.get_bead(sample_bead.id) is None

    def test_delete_bead_not_found(self, temp_storage):
        """Delete returns False if bead not found."""
        result = temp_storage.delete_bead("VKG-XXXX")
        assert result is False

    def test_clear_storage(self, temp_storage, sample_bead):
        """Clear all beads from storage."""
        temp_storage.save_bead(sample_bead)
        sample_bead.id = "VKG-0002"
        sample_bead.context_hash = "xyz"
        temp_storage.save_bead(sample_bead)

        count = temp_storage.clear()

        assert count == 2
        assert temp_storage.count() == 0

    def test_clear_empty_storage(self, temp_storage):
        """Clear on empty storage returns 0."""
        count = temp_storage.clear()
        assert count == 0


class TestBeadStorageMetrics:
    """Tests for storage metrics and summary."""

    def test_count(self, temp_storage, sample_bead):
        """Count beads in storage."""
        assert temp_storage.count() == 0

        temp_storage.save_bead(sample_bead)
        assert temp_storage.count() == 1

    def test_exists(self, temp_storage, sample_bead):
        """Check if bead exists."""
        assert temp_storage.exists(sample_bead.id) is False

        temp_storage.save_bead(sample_bead)
        assert temp_storage.exists(sample_bead.id) is True

    def test_get_summary_empty(self, temp_storage):
        """Get summary on empty storage."""
        summary = temp_storage.get_summary()

        assert summary["total"] == 0
        assert summary["by_status"] == {}
        assert summary["by_severity"] == {}
        assert summary["by_class"] == {}

    def test_get_summary(self, temp_storage, sample_bead):
        """Get summary statistics."""
        temp_storage.save_bead(sample_bead)

        summary = temp_storage.get_summary()

        assert summary["total"] == 1
        assert summary["by_status"]["pending"] == 1
        assert summary["by_severity"]["critical"] == 1
        assert summary["by_class"]["reentrancy"] == 1


class TestBeadStoragePersistence:
    """Tests for persistence and round-trip serialization."""

    def test_bead_persists_all_fields(self, temp_storage, sample_bead):
        """All bead fields persist correctly."""
        temp_storage.save_bead(sample_bead)
        loaded = temp_storage.get_bead(sample_bead.id)

        # Identity
        assert loaded.id == sample_bead.id
        assert loaded.vulnerability_class == sample_bead.vulnerability_class
        assert loaded.pattern_id == sample_bead.pattern_id
        assert loaded.severity == sample_bead.severity
        assert loaded.confidence == sample_bead.confidence
        assert loaded.status == sample_bead.status

        # Code context
        assert loaded.vulnerable_code.source == sample_bead.vulnerable_code.source
        assert loaded.vulnerable_code.file_path == sample_bead.vulnerable_code.file_path
        assert loaded.vulnerable_code.function_name == sample_bead.vulnerable_code.function_name

        # Pattern context
        assert loaded.pattern_context.pattern_name == sample_bead.pattern_context.pattern_name
        assert loaded.pattern_context.why_flagged == sample_bead.pattern_context.why_flagged

        # Investigation guide
        assert len(loaded.investigation_guide.steps) == len(sample_bead.investigation_guide.steps)

        # Test context
        assert loaded.test_context.attack_scenario == sample_bead.test_context.attack_scenario

        # Recommendations
        assert loaded.fix_recommendations == sample_bead.fix_recommendations
        assert loaded.inheritance_chain == sample_bead.inheritance_chain

    def test_bead_update_persists(self, temp_storage, sample_bead):
        """Updates to bead persist correctly."""
        temp_storage.save_bead(sample_bead)

        # Load, modify, save
        bead = temp_storage.get_bead(sample_bead.id)
        bead.status = BeadStatus.INVESTIGATING
        bead.add_note("Investigation started")
        temp_storage.save_bead(bead)

        # Load again
        reloaded = temp_storage.get_bead(sample_bead.id)

        assert reloaded.status == BeadStatus.INVESTIGATING
        assert "Investigation started" in reloaded.notes[0]

    def test_corrupted_file_skipped(self, temp_storage, sample_bead):
        """Corrupted files are skipped during listing."""
        temp_storage.save_bead(sample_bead)

        # Create a corrupted file
        corrupt_path = temp_storage.path / "corrupt.json"
        corrupt_path.write_text("not valid json {{{")

        # Should still list valid beads
        beads = temp_storage.list_beads()
        assert len(beads) == 1
        assert beads[0].id == sample_bead.id


class TestBeadStorageEdgeCases:
    """Tests for edge cases."""

    def test_bead_with_special_characters_in_id(self, temp_storage, sample_bead):
        """Handle beads with special characters in ID."""
        # IDs should be safe for filenames, but test anyway
        sample_bead.id = "VKG-0001-abc_123"
        sample_bead.context_hash = "special"
        temp_storage.save_bead(sample_bead)

        loaded = temp_storage.get_bead(sample_bead.id)
        assert loaded is not None
        assert loaded.id == sample_bead.id

    def test_multiple_save_overwrites(self, temp_storage, sample_bead):
        """Multiple saves overwrite the same file."""
        temp_storage.save_bead(sample_bead)
        sample_bead.status = BeadStatus.CONFIRMED
        temp_storage.save_bead(sample_bead)

        # Should still be 1 bead
        assert temp_storage.count() == 1

        loaded = temp_storage.get_bead(sample_bead.id)
        assert loaded.status == BeadStatus.CONFIRMED
