"""Tests for bead-pool integration (ORCH-04/08).

This module tests the integration between beads and pools:
- Pool association via pool_id field
- Pool-aware storage operations
- Work state persistence for agent resumption
- Human flagging for debate outcomes
"""

import json
import pytest
from datetime import datetime
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
    storage_path = tmp_path / ".vkg" / "beads"
    return BeadStorage(storage_path)


@pytest.fixture
def sample_bead():
    """Create a sample bead for testing."""
    return VulnerabilityBead(
        id="VKG-POOL-001",
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
        context_hash="pool001",
    )


class TestBeadPoolIntegration:
    """Test bead-pool integration features (ORCH-04)."""

    def test_bead_has_pool_id_field(self, sample_bead):
        """Bead schema includes pool_id field for association."""
        assert hasattr(sample_bead, "pool_id")
        assert sample_bead.pool_id is None  # Default is None

        sample_bead.pool_id = "audit-vault-2026-01-20"
        assert sample_bead.pool_id == "audit-vault-2026-01-20"

    def test_save_to_pool_creates_directory(self, temp_storage, sample_bead):
        """save_to_pool creates pool beads directory."""
        pool_id = "test-pool-001"

        saved_path = temp_storage.save_to_pool(sample_bead, pool_id)

        assert saved_path.exists()
        assert "pools" in str(saved_path)
        assert pool_id in str(saved_path)
        assert saved_path.suffix == ".yaml"

    def test_save_to_pool_updates_pool_id(self, temp_storage, sample_bead):
        """save_to_pool sets bead's pool_id."""
        pool_id = "test-pool-002"
        assert sample_bead.pool_id is None

        temp_storage.save_to_pool(sample_bead, pool_id)

        assert sample_bead.pool_id == pool_id

    def test_load_from_pool_returns_bead(self, temp_storage, sample_bead):
        """load_from_pool retrieves saved bead."""
        pool_id = "test-pool-003"

        # First save to main storage (for full data)
        temp_storage.save_bead(sample_bead)
        # Then save to pool
        temp_storage.save_to_pool(sample_bead, pool_id)

        loaded = temp_storage.load_from_pool(sample_bead.id, pool_id)

        assert loaded is not None
        assert loaded.id == sample_bead.id
        assert loaded.pool_id == pool_id
        assert loaded.vulnerability_class == "reentrancy"

    def test_load_from_pool_not_found(self, temp_storage):
        """load_from_pool returns None for missing bead."""
        result = temp_storage.load_from_pool("VKG-NONEXISTENT", "no-pool")
        assert result is None

    def test_list_pool_beads_returns_all_beads(self, temp_storage, sample_bead):
        """list_pool_beads returns all beads in pool."""
        pool_id = "test-pool-004"

        # Save first bead
        temp_storage.save_bead(sample_bead)
        temp_storage.save_to_pool(sample_bead, pool_id)

        # Save second bead
        bead2 = VulnerabilityBead(
            id="VKG-POOL-002",
            vulnerability_class="access_control",
            pattern_id="auth-001",
            severity=Severity.HIGH,
            confidence=0.85,
            status=BeadStatus.PENDING,
            vulnerable_code=CodeSnippet(
                source="function setOwner() public { owner = msg.sender; }",
                file_path="/contracts/Vault.sol",
                start_line=20,
                end_line=22,
                function_name="setOwner",
                contract_name="Vault",
            ),
            pattern_context=PatternContext(
                pattern_name="Missing Access Control",
                pattern_description="Detects public privileged functions",
                why_flagged="Public function modifies owner",
                matched_properties=["modifies_owner"],
                evidence_lines=[20],
            ),
            investigation_guide=InvestigationGuide(
                steps=[],
                questions_to_answer=["Who can call this?"],
                common_false_positives=[],
                key_indicators=[],
                safe_patterns=[],
            ),
            test_context=TestContext(
                scaffold_code="",
                attack_scenario="Anyone takes ownership",
                setup_requirements=[],
                expected_outcome="Attacker is owner",
            ),
            related_code=[],
            full_contract=None,
            similar_exploits=[],
            fix_recommendations=[],
            inheritance_chain=[],
            context_hash="pool002",
        )
        temp_storage.save_bead(bead2)
        temp_storage.save_to_pool(bead2, pool_id)

        beads = temp_storage.list_pool_beads(pool_id)

        assert len(beads) == 2
        ids = {b.id for b in beads}
        assert "VKG-POOL-001" in ids
        assert "VKG-POOL-002" in ids

    def test_list_pool_beads_empty_pool(self, temp_storage):
        """list_pool_beads returns empty list for nonexistent pool."""
        beads = temp_storage.list_pool_beads("nonexistent-pool")
        assert beads == []


class TestWorkStatePersistence:
    """Test work state persistence for agent resumption (ORCH-08)."""

    def test_bead_has_work_state_field(self, sample_bead):
        """Bead schema includes work_state field."""
        assert hasattr(sample_bead, "work_state")
        assert sample_bead.work_state is None

    def test_bead_has_last_agent_field(self, sample_bead):
        """Bead schema includes last_agent field."""
        assert hasattr(sample_bead, "last_agent")
        assert sample_bead.last_agent is None

    def test_bead_has_last_updated_field(self, sample_bead):
        """Bead schema includes last_updated field."""
        assert hasattr(sample_bead, "last_updated")
        assert sample_bead.last_updated is None

    def test_update_work_state_persists(self, temp_storage, sample_bead):
        """update_work_state saves state for resumption."""
        pool_id = "test-pool-005"

        # Save to main and pool storage
        temp_storage.save_bead(sample_bead)
        temp_storage.save_to_pool(sample_bead, pool_id)

        work_state = {
            "step": 2,
            "findings": ["Found external call at line 12"],
            "incomplete": True,
        }

        result = temp_storage.update_work_state(
            sample_bead.id, pool_id, work_state, "attacker-agent-001"
        )

        assert result is True

        # Verify persistence
        loaded = temp_storage.load_from_pool(sample_bead.id, pool_id)
        assert loaded.work_state == work_state
        assert loaded.last_agent == "attacker-agent-001"
        assert loaded.last_updated is not None

    def test_update_work_state_not_found(self, temp_storage):
        """update_work_state returns False for missing bead."""
        result = temp_storage.update_work_state(
            "VKG-NONEXISTENT", "no-pool", {}, "agent"
        )
        assert result is False

    def test_get_resumable_beads_returns_investigating(
        self, temp_storage, sample_bead
    ):
        """get_resumable_beads returns beads with work state."""
        pool_id = "test-pool-006"

        # Save with work state and INVESTIGATING status
        temp_storage.save_bead(sample_bead)
        sample_bead.status = BeadStatus.INVESTIGATING
        sample_bead.work_state = {"step": 1}
        temp_storage.save_to_pool(sample_bead, pool_id)

        resumable = temp_storage.get_resumable_beads(pool_id)

        assert len(resumable) == 1
        assert resumable[0].id == sample_bead.id

    def test_get_resumable_beads_excludes_completed(
        self, temp_storage, sample_bead
    ):
        """get_resumable_beads excludes CONFIRMED/REJECTED beads."""
        pool_id = "test-pool-007"

        # Save with work state but CONFIRMED status
        temp_storage.save_bead(sample_bead)
        sample_bead.status = BeadStatus.CONFIRMED
        sample_bead.work_state = {"step": 3}  # Has work state
        temp_storage.save_to_pool(sample_bead, pool_id)

        resumable = temp_storage.get_resumable_beads(pool_id)

        # Should be empty - CONFIRMED beads are not resumable
        assert len(resumable) == 0

    def test_get_resumable_beads_excludes_no_state(
        self, temp_storage, sample_bead
    ):
        """get_resumable_beads excludes beads without work_state."""
        pool_id = "test-pool-008"

        # Save without work state
        temp_storage.save_bead(sample_bead)
        sample_bead.status = BeadStatus.INVESTIGATING
        sample_bead.work_state = None  # No work state
        temp_storage.save_to_pool(sample_bead, pool_id)

        resumable = temp_storage.get_resumable_beads(pool_id)

        assert len(resumable) == 0


class TestHumanFlagging:
    """Test human flagging for debate outcomes (ORCH-08)."""

    def test_bead_status_has_flagged_for_human(self):
        """BeadStatus enum includes FLAGGED_FOR_HUMAN."""
        assert BeadStatus.FLAGGED_FOR_HUMAN.value == "flagged_for_human"

    def test_bead_has_human_flag_field(self, sample_bead):
        """Bead schema includes human_flag field."""
        assert hasattr(sample_bead, "human_flag")
        assert sample_bead.human_flag is False  # Default is False

    def test_human_flag_persists(self, temp_storage, sample_bead):
        """human_flag persists through serialization."""
        pool_id = "test-pool-009"

        sample_bead.human_flag = True
        temp_storage.save_bead(sample_bead)
        temp_storage.save_to_pool(sample_bead, pool_id)

        loaded = temp_storage.load_from_pool(sample_bead.id, pool_id)

        assert loaded.human_flag is True

    def test_list_flagged_for_human(self, temp_storage, sample_bead):
        """list_flagged_for_human returns flagged beads."""
        pool_id = "test-pool-010"

        # Save flagged bead
        temp_storage.save_bead(sample_bead)
        sample_bead.human_flag = True
        temp_storage.save_to_pool(sample_bead, pool_id)

        flagged = temp_storage.list_flagged_for_human(pool_id)

        assert len(flagged) == 1
        assert flagged[0].id == sample_bead.id

    def test_list_flagged_includes_status_flagged(
        self, temp_storage, sample_bead
    ):
        """list_flagged_for_human includes FLAGGED_FOR_HUMAN status."""
        pool_id = "test-pool-011"

        temp_storage.save_bead(sample_bead)
        sample_bead.status = BeadStatus.FLAGGED_FOR_HUMAN
        sample_bead.human_flag = False  # Status takes precedence
        temp_storage.save_to_pool(sample_bead, pool_id)

        flagged = temp_storage.list_flagged_for_human(pool_id)

        assert len(flagged) == 1

    def test_minimal_yaml_includes_human_flag(self, sample_bead):
        """to_minimal_yaml includes human_flag field."""
        sample_bead.human_flag = True

        yaml_str = sample_bead.to_minimal_yaml()

        assert "human_flag: true" in yaml_str


class TestDebateFields:
    """Test debate protocol fields (ORCH-06)."""

    def test_bead_has_debate_summary(self, sample_bead):
        """Bead schema includes debate_summary field."""
        assert hasattr(sample_bead, "debate_summary")
        assert sample_bead.debate_summary is None

    def test_bead_has_attacker_claim(self, sample_bead):
        """Bead schema includes attacker_claim field."""
        assert hasattr(sample_bead, "attacker_claim")
        assert sample_bead.attacker_claim is None

    def test_bead_has_defender_claim(self, sample_bead):
        """Bead schema includes defender_claim field."""
        assert hasattr(sample_bead, "defender_claim")
        assert sample_bead.defender_claim is None

    def test_bead_has_verifier_verdict(self, sample_bead):
        """Bead schema includes verifier_verdict field."""
        assert hasattr(sample_bead, "verifier_verdict")
        assert sample_bead.verifier_verdict is None

    def test_debate_fields_persist(self, temp_storage, sample_bead):
        """Debate fields persist through serialization."""
        sample_bead.debate_summary = "Attacker claims reentrancy, defender disputes"
        sample_bead.attacker_claim = "External call before balance update allows drain"
        sample_bead.defender_claim = "Rate limiting prevents full drain"
        sample_bead.verifier_verdict = "Attacker claim valid for partial drain"

        temp_storage.save_bead(sample_bead)
        loaded = temp_storage.get_bead(sample_bead.id)

        assert loaded.debate_summary == sample_bead.debate_summary
        assert loaded.attacker_claim == sample_bead.attacker_claim
        assert loaded.defender_claim == sample_bead.defender_claim
        assert loaded.verifier_verdict == sample_bead.verifier_verdict

    def test_minimal_yaml_includes_debate(self, sample_bead):
        """to_minimal_yaml includes debate fields when set."""
        sample_bead.debate_summary = "Test debate"
        sample_bead.attacker_claim = "Attack claim"
        sample_bead.defender_claim = "Defense claim"
        sample_bead.verifier_verdict = "Verdict"

        yaml_str = sample_bead.to_minimal_yaml()

        assert "debate:" in yaml_str
        assert "summary: Test debate" in yaml_str
        assert "attacker_claim: Attack claim" in yaml_str


class TestPoolsListing:
    """Test listing pools with beads."""

    def test_list_pools_with_beads_empty(self, temp_storage):
        """list_pools_with_beads returns empty when no pools."""
        pools = temp_storage.list_pools_with_beads()
        assert pools == []

    def test_list_pools_with_beads(self, temp_storage, sample_bead):
        """list_pools_with_beads finds pools with beads."""
        # Save to two pools
        temp_storage.save_bead(sample_bead)
        temp_storage.save_to_pool(sample_bead, "pool-a")

        bead2 = VulnerabilityBead(
            id="VKG-POOL-003",
            vulnerability_class="oracle",
            pattern_id="oracle-001",
            severity=Severity.HIGH,
            confidence=0.9,
            status=BeadStatus.PENDING,
            vulnerable_code=CodeSnippet(
                source="uint price = oracle.getPrice();",
                file_path="/contracts/Swap.sol",
                start_line=30,
                end_line=30,
                function_name="swap",
                contract_name="Swap",
            ),
            pattern_context=PatternContext(
                pattern_name="Oracle Manipulation",
                pattern_description="Detects oracle usage",
                why_flagged="Uses external oracle",
                matched_properties=[],
                evidence_lines=[],
            ),
            investigation_guide=InvestigationGuide(
                steps=[],
                questions_to_answer=[],
                common_false_positives=[],
                key_indicators=[],
                safe_patterns=[],
            ),
            test_context=TestContext(
                scaffold_code="",
                attack_scenario="",
                setup_requirements=[],
                expected_outcome="",
            ),
            related_code=[],
            full_contract=None,
            similar_exploits=[],
            fix_recommendations=[],
            inheritance_chain=[],
            context_hash="pool003",
        )
        temp_storage.save_bead(bead2)
        temp_storage.save_to_pool(bead2, "pool-b")

        pools = temp_storage.list_pools_with_beads()

        assert len(pools) == 2
        assert "pool-a" in pools
        assert "pool-b" in pools


class TestYAMLFormat:
    """Test YAML format for pool beads."""

    def test_save_to_pool_uses_yaml_by_default(self, temp_storage, sample_bead):
        """save_to_pool uses YAML format by default."""
        pool_id = "yaml-test-pool"

        saved_path = temp_storage.save_to_pool(sample_bead, pool_id)

        assert saved_path.suffix == ".yaml"
        content = saved_path.read_text()
        assert "id:" in content
        assert "vulnerability_class:" in content

    def test_save_to_pool_json_option(self, temp_storage, sample_bead):
        """save_to_pool can use JSON format."""
        pool_id = "json-test-pool"

        saved_path = temp_storage.save_to_pool(sample_bead, pool_id, use_yaml=False)

        assert saved_path.suffix == ".json"
        content = saved_path.read_text()
        data = json.loads(content)
        assert data["id"] == sample_bead.id

    def test_yaml_is_human_readable(self, sample_bead):
        """to_minimal_yaml produces readable output."""
        yaml_str = sample_bead.to_minimal_yaml()

        # Should have clear structure
        lines = yaml_str.split("\n")
        assert any("id:" in line for line in lines)
        assert any("severity:" in line for line in lines)
        assert any("location:" in line for line in lines)

        # Should not have complex serialization artifacts
        assert "!!" not in yaml_str  # No YAML tags


class TestBackwardCompatibility:
    """Test backward compatibility with existing beads."""

    def test_old_beads_load_without_pool_fields(self, temp_storage, tmp_path):
        """Old beads without pool fields still load correctly."""
        # Create old-format bead JSON (without pool fields)
        old_bead_data = {
            "id": "VKG-OLD-001",
            "vulnerability_class": "reentrancy",
            "pattern_id": "vm-001",
            "severity": "critical",
            "confidence": 0.9,
            "status": "pending",
            "vulnerable_code": {
                "source": "code",
                "file_path": "/test.sol",
                "start_line": 1,
                "end_line": 5,
            },
            "pattern_context": {
                "pattern_name": "Test",
                "pattern_description": "Test",
                "why_flagged": "Test",
                "matched_properties": [],
                "evidence_lines": [],
            },
            "investigation_guide": {
                "steps": [],
                "questions_to_answer": [],
                "common_false_positives": [],
                "key_indicators": [],
                "safe_patterns": [],
            },
            "test_context": {
                "scaffold_code": "",
                "attack_scenario": "",
                "setup_requirements": [],
                "expected_outcome": "",
            },
            "related_code": [],
            "similar_exploits": [],
            "fix_recommendations": [],
            "inheritance_chain": [],
            "notes": [],
            "created_at": "2026-01-20T00:00:00",
            "updated_at": "2026-01-20T00:00:00",
            "context_hash": "old",
            # Deliberately omitting pool_id, debate fields, etc.
        }

        # Save directly to storage
        bead_path = temp_storage.path / "VKG-OLD-001.json"
        with open(bead_path, "w") as f:
            json.dump(old_bead_data, f)

        # Load should work
        loaded = temp_storage.get_bead("VKG-OLD-001")

        assert loaded is not None
        assert loaded.id == "VKG-OLD-001"
        # New fields should have defaults
        assert loaded.pool_id is None
        assert loaded.human_flag is False
        assert loaded.debate_summary is None
        assert loaded.work_state is None
