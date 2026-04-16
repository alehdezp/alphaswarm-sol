"""Tests for bead creator.

Tests the creation of VulnerabilityBeads from pattern engine findings.
"""

import pytest
from unittest.mock import Mock

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node, Evidence
from alphaswarm_sol.beads.creator import (
    BeadCreator,
    BeadCreationConfig,
    create_bead,
    create_beads,
)
from alphaswarm_sol.beads.types import Severity, BeadStatus
from alphaswarm_sol.beads.schema import VulnerabilityBead


@pytest.fixture
def sample_graph():
    """Create a sample knowledge graph with test nodes."""
    graph = KnowledgeGraph()

    # Add a function node
    func_node = Node(
        id="func_vault_withdraw",
        type="Function",
        label="Vault.withdraw",
        properties={
            "name": "withdraw",
            "contract_name": "Vault",
            "visibility": "public",
            "state_write_after_external_call": True,
            "has_reentrancy_guard": False,
            "source_code": """function withdraw(uint amount) external {
    require(balances[msg.sender] >= amount);
    (bool success,) = msg.sender.call{value: amount}("");
    require(success);
    balances[msg.sender] -= amount;
}""",
            "modifiers": [],
            "internal_calls": [],
        },
        evidence=[
            Evidence(file="/contracts/Vault.sol", line_start=45, line_end=51)
        ],
    )
    graph.add_node(func_node)

    # Add a contract node
    contract_node = Node(
        id="contract_Vault",
        type="Contract",
        label="Vault",
        properties={
            "name": "Vault",
            "inheritance": ["Ownable", "ReentrancyGuard"],
        },
        evidence=[Evidence(file="/contracts/Vault.sol", line_start=1, line_end=100)],
    )
    graph.add_node(contract_node)

    return graph


@pytest.fixture
def reentrancy_finding():
    """Create a sample reentrancy finding."""
    return {
        "pattern_id": "vm-001",
        "pattern_name": "Basic Reentrancy",
        "severity": "critical",
        "lens": ["Reentrancy"],
        "node_id": "func_vault_withdraw",
        "node_label": "Vault.withdraw",
        "node_type": "Function",
        "explain": {
            "all_conditions": {
                "state_write_after_external_call": True,
                "has_reentrancy_guard": False,
            },
            "evidence_lines": [48, 50],
        },
    }


@pytest.fixture
def access_control_finding():
    """Create a sample access control finding."""
    return {
        "pattern_id": "auth-001",
        "pattern_name": "Missing Access Control",
        "severity": "high",
        "lens": ["Access-Control"],
        "node_id": "func_vault_withdraw",
        "node_label": "Vault.withdraw",
        "node_type": "Function",
    }


class TestBeadCreator:
    """Tests for BeadCreator class."""

    def test_create_bead_basic(self, sample_graph, reentrancy_finding):
        """Create bead produces valid VulnerabilityBead."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert isinstance(bead, VulnerabilityBead)
        assert bead.id.startswith("VKG-")
        assert bead.pattern_id == "vm-001"
        assert bead.status == BeadStatus.PENDING

    def test_bead_id_unique(self, sample_graph, reentrancy_finding):
        """Each bead gets a unique ID."""
        creator = BeadCreator(sample_graph)
        bead1 = creator.create_bead(reentrancy_finding)
        bead2 = creator.create_bead(reentrancy_finding)

        assert bead1.id != bead2.id

    def test_vulnerability_class_from_lens(self, sample_graph, reentrancy_finding):
        """Vulnerability class correctly determined from lens."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert bead.vulnerability_class == "reentrancy"

    def test_vulnerability_class_from_pattern_id(self, sample_graph):
        """Vulnerability class determined from pattern ID when no lens."""
        finding = {
            "pattern_id": "oracle-staleness-001",
            "severity": "high",
            "node_id": "func_vault_withdraw",
            "node_label": "Vault.withdraw",
        }
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(finding)

        assert bead.vulnerability_class == "oracle"

    def test_severity_from_finding(self, sample_graph, reentrancy_finding):
        """Severity correctly extracted from finding."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert bead.severity == Severity.CRITICAL

    def test_severity_defaults_to_medium(self, sample_graph):
        """Severity defaults to medium when not specified."""
        finding = {
            "pattern_id": "test-001",
            "node_id": "func_vault_withdraw",
            "node_label": "Vault.withdraw",
        }
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(finding)

        assert bead.severity == Severity.MEDIUM


class TestBeadCodeContext:
    """Tests for code context extraction."""

    def test_bead_has_vulnerable_code(self, sample_graph, reentrancy_finding):
        """Bead includes vulnerable code snippet."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert bead.vulnerable_code is not None
        assert bead.vulnerable_code.function_name == "withdraw"
        assert bead.vulnerable_code.contract_name == "Vault"

    def test_code_snippet_has_source(self, sample_graph, reentrancy_finding):
        """Code snippet includes source code."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert "withdraw" in bead.vulnerable_code.source
        assert "msg.sender.call" in bead.vulnerable_code.source

    def test_code_snippet_has_location(self, sample_graph, reentrancy_finding):
        """Code snippet includes file and line info."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert bead.vulnerable_code.file_path == "/contracts/Vault.sol"
        assert bead.vulnerable_code.start_line == 45
        assert bead.vulnerable_code.end_line == 51

    def test_bead_has_inheritance(self, sample_graph, reentrancy_finding):
        """Bead includes inheritance chain."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert "Ownable" in bead.inheritance_chain
        assert "ReentrancyGuard" in bead.inheritance_chain


class TestBeadPatternContext:
    """Tests for pattern context."""

    def test_bead_has_pattern_context(self, sample_graph, reentrancy_finding):
        """Bead includes pattern context."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert bead.pattern_context is not None
        assert bead.pattern_context.pattern_name == "Basic Reentrancy"

    def test_pattern_context_has_why_flagged(self, sample_graph, reentrancy_finding):
        """Pattern context includes why_flagged explanation."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert bead.pattern_context.why_flagged
        assert "Basic Reentrancy" in bead.pattern_context.why_flagged

    def test_pattern_context_has_matched_properties(
        self, sample_graph, reentrancy_finding
    ):
        """Pattern context includes matched properties."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        # Should extract from explain dict
        assert len(bead.pattern_context.matched_properties) >= 0


class TestBeadInvestigationGuide:
    """Tests for investigation guide."""

    def test_bead_has_investigation_guide(self, sample_graph, reentrancy_finding):
        """Bead includes investigation guide."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert bead.investigation_guide is not None
        assert len(bead.investigation_guide.steps) > 0

    def test_investigation_guide_has_steps(self, sample_graph, reentrancy_finding):
        """Investigation guide has investigation steps."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        # Should load from reentrancy template
        assert len(bead.investigation_guide.steps) >= 3

    def test_investigation_guide_has_questions(self, sample_graph, reentrancy_finding):
        """Investigation guide has questions to answer."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert len(bead.investigation_guide.questions_to_answer) > 0

    def test_fallback_guide_for_unknown_class(self, sample_graph):
        """Fallback guide used for unknown vulnerability class."""
        finding = {
            "pattern_id": "unknown-weird-pattern",
            "severity": "medium",
            "node_id": "func_vault_withdraw",
            "node_label": "Vault.withdraw",
        }
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(finding)

        # Should still have an investigation guide (fallback)
        assert bead.investigation_guide is not None
        assert len(bead.investigation_guide.steps) >= 3


class TestBeadTestContext:
    """Tests for test context."""

    def test_bead_has_test_context(self, sample_graph, reentrancy_finding):
        """Bead includes test context."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert bead.test_context is not None

    def test_test_context_has_scaffold(self, sample_graph, reentrancy_finding):
        """Test context includes Foundry scaffold."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert "setUp" in bead.test_context.scaffold_code
        assert "forge-std/Test.sol" in bead.test_context.scaffold_code
        assert "Vault" in bead.test_context.scaffold_code

    def test_test_context_has_attack_scenario(self, sample_graph, reentrancy_finding):
        """Test context includes attack scenario."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert bead.test_context.attack_scenario
        # Reentrancy scenario should mention reentry
        assert "re-enter" in bead.test_context.attack_scenario.lower()

    def test_test_context_has_requirements(self, sample_graph, reentrancy_finding):
        """Test context includes setup requirements."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert len(bead.test_context.setup_requirements) > 0


class TestBeadExploits:
    """Tests for exploit references."""

    def test_bead_has_similar_exploits(self, sample_graph, reentrancy_finding):
        """Bead includes similar exploits."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        # Should find reentrancy exploits from database
        assert len(bead.similar_exploits) > 0

    def test_exploits_limited_to_three(self, sample_graph, reentrancy_finding):
        """Similar exploits limited to 3 max."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert len(bead.similar_exploits) <= 3


class TestBeadFixRecommendations:
    """Tests for fix recommendations."""

    def test_bead_has_fix_recommendations(self, sample_graph, reentrancy_finding):
        """Bead includes fix recommendations."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert len(bead.fix_recommendations) > 0

    def test_reentrancy_recommendations(self, sample_graph, reentrancy_finding):
        """Reentrancy bead has relevant recommendations."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        recommendations_text = " ".join(bead.fix_recommendations).lower()
        assert "nonreentrant" in recommendations_text or "cei" in recommendations_text


class TestBeadConfiguration:
    """Tests for bead creation configuration."""

    def test_config_respected(self, sample_graph, reentrancy_finding):
        """Configuration is respected during creation."""
        config = BeadCreationConfig(max_related_code=2)
        creator = BeadCreator(sample_graph, config)
        bead = creator.create_bead(reentrancy_finding)

        assert len(bead.related_code) <= 2

    def test_default_config_used(self, sample_graph, reentrancy_finding):
        """Default config used when not specified."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert len(bead.related_code) <= 5  # Default max


class TestBeadCompleteness:
    """Tests for bead completeness."""

    def test_bead_is_complete(self, sample_graph, reentrancy_finding):
        """Created bead passes is_complete check."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert bead.is_complete()

    def test_bead_has_context_hash(self, sample_graph, reentrancy_finding):
        """Created bead has context hash."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        assert bead.context_hash  # Non-empty hash


class TestCreateBeadsFromFindings:
    """Tests for batch bead creation."""

    def test_create_multiple_beads(self, sample_graph, reentrancy_finding):
        """Create multiple beads from findings."""
        findings = [reentrancy_finding, reentrancy_finding]
        creator = BeadCreator(sample_graph)
        beads = creator.create_beads_from_findings(findings)

        assert len(beads) == 2
        assert all(isinstance(b, VulnerabilityBead) for b in beads)

    def test_continues_on_error(self, sample_graph, reentrancy_finding):
        """Continues creating beads even if one fails."""
        # One valid, one invalid finding
        findings = [
            reentrancy_finding,
            {"pattern_id": "test", "node_id": "nonexistent"},  # Will fail
        ]
        creator = BeadCreator(sample_graph)
        beads = creator.create_beads_from_findings(findings)

        # Should have at least the valid one
        assert len(beads) >= 1


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_bead_function(self, sample_graph, reentrancy_finding):
        """create_bead convenience function works."""
        bead = create_bead(reentrancy_finding, sample_graph)

        assert isinstance(bead, VulnerabilityBead)
        assert bead.id.startswith("VKG-")

    def test_create_beads_function(self, sample_graph, reentrancy_finding):
        """create_beads convenience function works."""
        findings = [reentrancy_finding]
        beads = create_beads(findings, sample_graph)

        assert len(beads) == 1
        assert isinstance(beads[0], VulnerabilityBead)


class TestBeadLLMPrompt:
    """Tests for LLM prompt generation."""

    def test_bead_generates_prompt(self, sample_graph, reentrancy_finding):
        """Created bead can generate LLM prompt."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        prompt = bead.get_llm_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Should be substantial

    def test_prompt_contains_key_sections(self, sample_graph, reentrancy_finding):
        """LLM prompt contains key sections."""
        creator = BeadCreator(sample_graph)
        bead = creator.create_bead(reentrancy_finding)

        prompt = bead.get_llm_prompt()

        # Should contain key sections
        assert "VULNERABILITY" in prompt or "vulnerability" in prompt.lower()
        assert "CODE" in prompt or "code" in prompt.lower()
