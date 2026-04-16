"""Tests for beads CLI commands."""

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner

from alphaswarm_sol.cli.beads import beads_app
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
    ExploitReference,
)


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary bead storage."""
    storage_path = tmp_path / "beads"
    storage_path.mkdir(parents=True)
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


@pytest.fixture
def storage_with_beads(temp_storage, sample_bead):
    """Storage populated with sample beads."""
    # Add the sample bead
    temp_storage.save_bead(sample_bead)

    # Add a high severity bead
    high_bead = VulnerabilityBead(
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
    temp_storage.save_bead(high_bead)

    # Add a confirmed bead
    confirmed_bead = VulnerabilityBead(
        id="VKG-0003-ghi789",
        vulnerability_class="reentrancy",
        pattern_id="vm-001",
        severity=Severity.MEDIUM,
        confidence=0.75,
        status=BeadStatus.CONFIRMED,
        vulnerable_code=CodeSnippet(
            source="function claim() { token.transfer(msg.sender, amount); claimed = true; }",
            file_path="/contracts/Airdrop.sol",
            start_line=30,
            end_line=33,
            function_name="claim",
            contract_name="Airdrop",
        ),
        pattern_context=PatternContext(
            pattern_name="Basic Reentrancy",
            pattern_description="Detects external calls before state updates",
            why_flagged="Token transfer before state update",
            matched_properties=["state_write_after_external_call"],
            evidence_lines=[30, 31],
        ),
        investigation_guide=InvestigationGuide(
            steps=[
                InvestigationStep(
                    step_number=1,
                    action="Check CEI pattern",
                    look_for="State update before transfer",
                    evidence_needed="Transfer found before state update",
                    red_flag="Transfer before update",
                    safe_if="CEI pattern followed",
                ),
            ],
            questions_to_answer=["Is CEI pattern followed?"],
            common_false_positives=[],
            key_indicators=["Transfer before state change"],
            safe_patterns=["CEI pattern"],
        ),
        test_context=TestContext(
            scaffold_code="// Test scaffold",
            attack_scenario="Re-enter to claim multiple times",
            setup_requirements=["Deploy Airdrop"],
            expected_outcome="Attacker claims multiple times",
        ),
        related_code=[],
        full_contract=None,
        similar_exploits=[],
        fix_recommendations=["Apply CEI pattern"],
        inheritance_chain=[],
        context_hash="ghi789",
    )
    temp_storage.save_bead(confirmed_bead)

    return temp_storage


class TestBeadsListCommand:
    """Tests for the beads list command."""

    def test_list_empty(self, runner, temp_storage, monkeypatch):
        """List with no beads."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: temp_storage
        )

        result = runner.invoke(beads_app, ["list"])
        assert result.exit_code == 0
        assert "No beads found" in result.output

    def test_list_with_beads(self, runner, storage_with_beads, monkeypatch):
        """List shows all beads."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["list"])
        assert result.exit_code == 0
        assert "VKG-0001" in result.output
        assert "VKG-0002" in result.output
        assert "VKG-0003" in result.output
        assert "Total: 3 beads" in result.output

    def test_list_filter_by_status(self, runner, storage_with_beads, monkeypatch):
        """List filtered by status."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["list", "--status", "pending"])
        assert result.exit_code == 0
        assert "VKG-0001" in result.output
        assert "VKG-0002" in result.output
        assert "VKG-0003" not in result.output  # Confirmed, not pending
        assert "Total: 2 beads" in result.output

    def test_list_filter_by_severity(self, runner, storage_with_beads, monkeypatch):
        """List filtered by severity."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["list", "--severity", "critical"])
        assert result.exit_code == 0
        assert "VKG-0001" in result.output
        assert "VKG-0002" not in result.output  # High, not critical
        assert "Total: 1 beads" in result.output

    def test_list_filter_by_class(self, runner, storage_with_beads, monkeypatch):
        """List filtered by vulnerability class."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["list", "--class", "reentrancy"])
        assert result.exit_code == 0
        assert "VKG-0001" in result.output
        assert "VKG-0003" in result.output
        assert "VKG-0002" not in result.output  # access_control
        assert "Total: 2 beads" in result.output

    def test_list_json_format(self, runner, storage_with_beads, monkeypatch):
        """List in JSON format."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 3

    def test_list_compact_format(self, runner, storage_with_beads, monkeypatch):
        """List in compact format."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["list", "--format", "compact"])
        assert result.exit_code == 0
        assert "|" in result.output  # Compact uses pipe separator

    def test_list_invalid_status(self, runner, storage_with_beads, monkeypatch):
        """List with invalid status."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["list", "--status", "invalid"])
        assert result.exit_code == 1
        assert "Invalid status" in result.output


class TestBeadsShowCommand:
    """Tests for the beads show command."""

    def test_show_bead(self, runner, storage_with_beads, monkeypatch):
        """Show displays bead details."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["show", "VKG-0001-abc123"])
        assert result.exit_code == 0
        assert "VKG-0001-abc123" in result.output
        assert "reentrancy" in result.output
        assert "CRITICAL" in result.output
        assert "withdraw" in result.output

    def test_show_not_found(self, runner, storage_with_beads, monkeypatch):
        """Show non-existent bead."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["show", "VKG-XXXX"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_show_json_format(self, runner, storage_with_beads, monkeypatch):
        """Show in JSON format."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["show", "VKG-0001-abc123", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "VKG-0001-abc123"

    def test_show_llm_format(self, runner, storage_with_beads, monkeypatch):
        """Show in LLM prompt format."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["show", "VKG-0001-abc123", "--format", "llm"])
        assert result.exit_code == 0
        # LLM prompt should have investigation content
        assert "VULNERABILITY" in result.output.upper() or "vulnerability" in result.output.lower()


class TestBeadsNextCommand:
    """Tests for the beads next command."""

    def test_next_gets_critical_first(self, runner, storage_with_beads, monkeypatch):
        """Next returns critical severity first."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["next"])
        assert result.exit_code == 0
        assert "VKG-0001" in result.output  # Critical severity
        assert "investigating" in result.output.lower()

    def test_next_no_pending(self, runner, temp_storage, sample_bead, monkeypatch):
        """Next with no pending beads."""
        # Mark bead as confirmed
        sample_bead.status = BeadStatus.CONFIRMED
        temp_storage.save_bead(sample_bead)

        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: temp_storage
        )

        result = runner.invoke(beads_app, ["next"])
        assert result.exit_code == 0
        assert "No pending beads" in result.output

    def test_next_with_severity_filter(self, runner, storage_with_beads, monkeypatch):
        """Next with minimum severity filter."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["next", "--severity", "critical"])
        assert result.exit_code == 0
        assert "VKG-0001" in result.output  # Only critical matches


class TestBeadsVerdictCommand:
    """Tests for the beads verdict command."""

    def test_verdict_confirmed(self, runner, storage_with_beads, monkeypatch):
        """Set confirmed verdict."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(
            beads_app,
            ["verdict", "VKG-0001-abc123", "--confirmed", "--reason", "Exploit confirmed"],
        )
        assert result.exit_code == 0
        assert "confirmed" in result.output.lower()

        # Verify bead was updated
        bead = storage_with_beads.get_bead("VKG-0001-abc123")
        assert bead.status == BeadStatus.CONFIRMED

    def test_verdict_rejected(self, runner, storage_with_beads, monkeypatch):
        """Set rejected verdict."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(
            beads_app,
            ["verdict", "VKG-0001-abc123", "--rejected", "--reason", "Has nonReentrant"],
        )
        assert result.exit_code == 0
        assert "rejected" in result.output.lower()

        # Verify bead was updated
        bead = storage_with_beads.get_bead("VKG-0001-abc123")
        assert bead.status == BeadStatus.REJECTED

    def test_verdict_inconclusive(self, runner, storage_with_beads, monkeypatch):
        """Set inconclusive verdict."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(
            beads_app,
            ["verdict", "VKG-0001-abc123", "--inconclusive", "--reason", "Need more context"],
        )
        assert result.exit_code == 0
        assert "inconclusive" in result.output.lower()

    def test_verdict_requires_type(self, runner, storage_with_beads, monkeypatch):
        """Verdict must specify type."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(
            beads_app,
            ["verdict", "VKG-0001-abc123", "--reason", "test"],
        )
        assert result.exit_code == 1
        assert "Must specify" in result.output

    def test_verdict_not_found(self, runner, storage_with_beads, monkeypatch):
        """Verdict on non-existent bead."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(
            beads_app,
            ["verdict", "VKG-XXXX", "--confirmed", "--reason", "test"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_verdict_multiple_types_error(self, runner, storage_with_beads, monkeypatch):
        """Cannot specify multiple verdict types."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(
            beads_app,
            ["verdict", "VKG-0001-abc123", "--confirmed", "--rejected", "--reason", "test"],
        )
        assert result.exit_code == 1
        assert "only specify one" in result.output.lower()


class TestBeadsNoteCommand:
    """Tests for the beads note command."""

    def test_add_note(self, runner, storage_with_beads, monkeypatch):
        """Add note to bead."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(
            beads_app,
            ["note", "VKG-0001-abc123", "Checked modifiers, none found"],
        )
        assert result.exit_code == 0
        assert "Note added" in result.output

        # Verify note was added
        bead = storage_with_beads.get_bead("VKG-0001-abc123")
        assert "Checked modifiers" in bead.notes[0]

    def test_note_not_found(self, runner, storage_with_beads, monkeypatch):
        """Add note to non-existent bead."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["note", "VKG-XXXX", "test note"])
        assert result.exit_code == 1
        assert "not found" in result.output


class TestBeadsContextCommand:
    """Tests for the beads context command."""

    def test_context_empty(self, runner, temp_storage, monkeypatch):
        """Context with no beads."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: temp_storage
        )

        result = runner.invoke(beads_app, ["context"])
        assert result.exit_code == 0
        assert "No beads in session" in result.output

    def test_context_summary(self, runner, storage_with_beads, monkeypatch):
        """Context shows summary."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["context"])
        assert result.exit_code == 0
        assert "SESSION CONTEXT" in result.output
        assert "Total Beads: 3" in result.output

    def test_context_json_format(self, runner, storage_with_beads, monkeypatch):
        """Context in JSON format."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["context", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total"] == 3
        assert "by_status" in data


class TestBeadsSummaryCommand:
    """Tests for the beads summary command."""

    def test_summary_empty(self, runner, temp_storage, monkeypatch):
        """Summary with no beads."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: temp_storage
        )

        result = runner.invoke(beads_app, ["summary"])
        assert result.exit_code == 0
        assert "Total: 0 beads" in result.output

    def test_summary_with_beads(self, runner, storage_with_beads, monkeypatch):
        """Summary shows statistics."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["summary"])
        assert result.exit_code == 0
        assert "BEADS SUMMARY" in result.output
        assert "By Status" in result.output
        assert "By Severity" in result.output
        assert "By Vulnerability Class" in result.output


class TestBeadsClearCommand:
    """Tests for the beads clear command."""

    def test_clear_empty(self, runner, temp_storage, monkeypatch):
        """Clear with no beads."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: temp_storage
        )

        result = runner.invoke(beads_app, ["clear"])
        assert result.exit_code == 0
        assert "No beads to clear" in result.output

    def test_clear_with_force(self, runner, storage_with_beads, monkeypatch):
        """Clear with force flag."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        result = runner.invoke(beads_app, ["clear", "--force"])
        assert result.exit_code == 0
        assert "Cleared 3 beads" in result.output

        # Verify beads are gone
        assert storage_with_beads.count() == 0

    def test_clear_with_confirmation(self, runner, storage_with_beads, monkeypatch):
        """Clear with confirmation prompt."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        # Confirm yes
        result = runner.invoke(beads_app, ["clear"], input="y\n")
        assert result.exit_code == 0
        assert "Cleared 3 beads" in result.output

    def test_clear_cancelled(self, runner, storage_with_beads, monkeypatch):
        """Clear cancelled by user."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: storage_with_beads
        )

        # Cancel
        result = runner.invoke(beads_app, ["clear"], input="n\n")
        assert result.exit_code == 0
        assert "Cancelled" in result.output

        # Verify beads still exist
        assert storage_with_beads.count() == 3


class TestBeadsStorage:
    """Tests for bead storage operations via CLI."""

    def test_beads_persist(self, runner, temp_storage, sample_bead, monkeypatch):
        """Beads persist between CLI invocations."""
        monkeypatch.setattr(
            "alphaswarm_sol.cli.beads._get_storage", lambda vkg_dir=None: temp_storage
        )

        # Save bead
        temp_storage.save_bead(sample_bead)

        # Verify via CLI
        result = runner.invoke(beads_app, ["list"])
        assert result.exit_code == 0
        assert "VKG-0001" in result.output

        # Update via CLI
        result = runner.invoke(
            beads_app,
            ["verdict", "VKG-0001-abc123", "--confirmed", "--reason", "Verified"],
        )
        assert result.exit_code == 0

        # Verify persistence
        result = runner.invoke(beads_app, ["list", "--status", "confirmed"])
        assert result.exit_code == 0
        assert "VKG-0001" in result.output
