"""Tests for VulnerabilityBead schema.

Task 6.1: Comprehensive tests for the bead schema.
"""

import json
import pytest
from datetime import datetime

from alphaswarm_sol.beads import (
    VulnerabilityBead,
    TestContext,
    PatternContext,
    InvestigationGuide,
    CodeSnippet,
    InvestigationStep,
    ExploitReference,
    Severity,
    BeadStatus,
    Verdict,
    VerdictType,
)


@pytest.fixture
def sample_vulnerable_code():
    """Sample vulnerable code snippet."""
    return CodeSnippet(
        source="""function withdraw(uint amount) external {
    msg.sender.call{value: amount}("");
    balances[msg.sender] -= amount;
}""",
        file_path="/contracts/Vault.sol",
        start_line=45,
        end_line=48,
        function_name="withdraw",
        contract_name="Vault",
    )


@pytest.fixture
def sample_pattern_context():
    """Sample pattern context."""
    return PatternContext(
        pattern_name="Classic Reentrancy",
        pattern_description="Detects external calls before state updates",
        why_flagged="External call on line 46 occurs before balance update on line 47",
        matched_properties=["state_write_after_external_call"],
        evidence_lines=[46, 47],
    )


@pytest.fixture
def sample_investigation_guide():
    """Sample investigation guide."""
    return InvestigationGuide(
        steps=[
            InvestigationStep(
                step_number=1,
                action="Identify the external call",
                look_for="call{value:}(), transfer(), send()",
                evidence_needed="Line number and target address",
                red_flag="User-controlled recipient",
                safe_if="Recipient is trusted contract",
            ),
            InvestigationStep(
                step_number=2,
                action="Check state update order",
                look_for="State variable modifications",
                evidence_needed="State update after external call",
            ),
            InvestigationStep(
                step_number=3,
                action="Look for reentrancy guards",
                look_for="nonReentrant modifier, ReentrancyGuard",
                evidence_needed="Presence or absence of guard",
                safe_if="nonReentrant modifier present",
            ),
        ],
        questions_to_answer=[
            "Is the external call target user-controlled?",
            "Is state modified after the external call?",
            "Is there a reentrancy guard present?",
            "Can an attacker profit from recursive calls?",
        ],
        common_false_positives=[
            "nonReentrant modifier present",
            "Target is a trusted contract",
            "No state changes after call",
            "Function is internal/private",
        ],
        key_indicators=[
            "External call before state update",
            "User-controlled call target",
            "Valuable state being modified",
        ],
        safe_patterns=[
            "Checks-Effects-Interactions (CEI) pattern",
            "nonReentrant modifier from OpenZeppelin",
            "Pull over push pattern",
        ],
    )


@pytest.fixture
def sample_test_context():
    """Sample test context."""
    return TestContext(
        scaffold_code="""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

contract AttackTest is Test {
    Vault vault;
    Attacker attacker;

    function setUp() public {
        vault = new Vault();
        attacker = new Attacker(address(vault));
        vm.deal(address(vault), 10 ether);
    }

    function testReentrancy() public {
        uint256 initialBalance = address(attacker).balance;
        attacker.attack{value: 1 ether}();
        assertGt(address(attacker).balance, initialBalance + 1 ether);
    }
}""",
        attack_scenario="""1. Attacker deposits 1 ETH
2. Attacker calls withdraw(1 ether)
3. In fallback, attacker calls withdraw again before balance update
4. Repeat until vault is drained
5. Attacker extracts more than deposited""",
        setup_requirements=[
            "Attacker contract with receive/fallback function",
            "Initial deposit to vault",
            "Sufficient vault balance",
        ],
        expected_outcome="Attacker extracts more ETH than their balance allows",
    )


@pytest.fixture
def sample_exploit():
    """Sample exploit reference."""
    return ExploitReference(
        id="the-dao-2016",
        name="The DAO Hack",
        date="2016-06-17",
        loss="$60M",
        pattern_id="vm-001",
        vulnerable_code="function splitDAO(...) { ... }",
        exploit_summary="Recursive call in splitDAO before balance update",
        fix="Use nonReentrant modifier or CEI pattern",
        source_url="https://hackingdistributed.com/2016/06/18/analysis-of-the-dao-exploit/",
    )


@pytest.fixture
def sample_bead(
    sample_vulnerable_code,
    sample_pattern_context,
    sample_investigation_guide,
    sample_test_context,
    sample_exploit,
):
    """Create a complete sample bead for testing."""
    return VulnerabilityBead(
        id="VKG-001",
        vulnerability_class="reentrancy",
        pattern_id="vm-001",
        severity=Severity.CRITICAL,
        confidence=0.95,
        vulnerable_code=sample_vulnerable_code,
        related_code=[],
        full_contract=None,
        inheritance_chain=["Ownable"],
        pattern_context=sample_pattern_context,
        investigation_guide=sample_investigation_guide,
        test_context=sample_test_context,
        similar_exploits=[sample_exploit],
        fix_recommendations=["Use CEI pattern", "Add nonReentrant modifier"],
    )


class TestTestContext:
    """Tests for TestContext dataclass."""

    def test_basic_creation(self):
        """Test basic TestContext creation."""
        ctx = TestContext(
            scaffold_code="// test code",
            attack_scenario="1. Attack step",
            setup_requirements=["req1", "req2"],
            expected_outcome="Exploit succeeds",
        )
        assert ctx.scaffold_code == "// test code"
        assert ctx.attack_scenario == "1. Attack step"
        assert len(ctx.setup_requirements) == 2
        assert ctx.expected_outcome == "Exploit succeeds"

    def test_to_dict(self):
        """Test to_dict serialization."""
        ctx = TestContext(
            scaffold_code="code",
            attack_scenario="scenario",
            setup_requirements=["req"],
            expected_outcome="outcome",
        )
        data = ctx.to_dict()
        assert data["scaffold_code"] == "code"
        assert data["setup_requirements"] == ["req"]

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "scaffold_code": "code",
            "attack_scenario": "scenario",
            "setup_requirements": ["req"],
            "expected_outcome": "outcome",
        }
        ctx = TestContext.from_dict(data)
        assert ctx.scaffold_code == "code"
        assert ctx.setup_requirements == ["req"]

    def test_round_trip(self):
        """Test serialization round-trip."""
        original = TestContext(
            scaffold_code="// code",
            attack_scenario="attack",
            setup_requirements=["a", "b"],
            expected_outcome="result",
        )
        data = original.to_dict()
        restored = TestContext.from_dict(data)
        assert restored.scaffold_code == original.scaffold_code
        assert restored.setup_requirements == original.setup_requirements


class TestPatternContext:
    """Tests for PatternContext dataclass."""

    def test_basic_creation(self):
        """Test basic PatternContext creation."""
        ctx = PatternContext(
            pattern_name="Classic Reentrancy",
            pattern_description="Detects external calls before state updates",
            why_flagged="External call before state update",
            matched_properties=["prop1", "prop2"],
            evidence_lines=[46, 47],
        )
        assert ctx.pattern_name == "Classic Reentrancy"
        assert len(ctx.matched_properties) == 2
        assert ctx.evidence_lines == [46, 47]

    def test_to_dict(self):
        """Test to_dict serialization."""
        ctx = PatternContext(
            pattern_name="Test",
            pattern_description="Desc",
            why_flagged="Reason",
            matched_properties=["prop"],
            evidence_lines=[1, 2, 3],
        )
        data = ctx.to_dict()
        assert data["pattern_name"] == "Test"
        assert data["evidence_lines"] == [1, 2, 3]

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "pattern_name": "Test",
            "pattern_description": "Desc",
            "why_flagged": "Reason",
            "matched_properties": ["prop"],
            "evidence_lines": [1, 2],
        }
        ctx = PatternContext.from_dict(data)
        assert ctx.pattern_name == "Test"
        assert ctx.evidence_lines == [1, 2]

    def test_round_trip(self):
        """Test serialization round-trip."""
        original = PatternContext(
            pattern_name="Pattern",
            pattern_description="Description",
            why_flagged="Because",
            matched_properties=["a", "b"],
            evidence_lines=[10, 20],
        )
        data = original.to_dict()
        restored = PatternContext.from_dict(data)
        assert restored.pattern_name == original.pattern_name
        assert restored.evidence_lines == original.evidence_lines


class TestInvestigationGuide:
    """Tests for InvestigationGuide dataclass."""

    def test_basic_creation(self):
        """Test basic InvestigationGuide creation."""
        guide = InvestigationGuide(
            steps=[
                InvestigationStep(
                    step_number=1,
                    action="Check",
                    look_for="Something",
                    evidence_needed="Found",
                )
            ],
            questions_to_answer=["Question?"],
            common_false_positives=["FP pattern"],
            key_indicators=["Indicator"],
            safe_patterns=["Safe pattern"],
        )
        assert len(guide.steps) == 1
        assert guide.questions_to_answer == ["Question?"]

    def test_to_dict(self):
        """Test to_dict serialization."""
        guide = InvestigationGuide(
            steps=[
                InvestigationStep(
                    step_number=1,
                    action="Action",
                    look_for="Look",
                    evidence_needed="Evidence",
                )
            ],
            questions_to_answer=["Q1"],
            common_false_positives=["FP1"],
            key_indicators=["KI1"],
            safe_patterns=["SP1"],
        )
        data = guide.to_dict()
        assert len(data["steps"]) == 1
        assert data["steps"][0]["action"] == "Action"
        assert data["questions_to_answer"] == ["Q1"]

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "steps": [
                {
                    "step_number": 1,
                    "action": "Action",
                    "look_for": "Look",
                    "evidence_needed": "Evidence",
                }
            ],
            "questions_to_answer": ["Q1"],
            "common_false_positives": ["FP1"],
            "key_indicators": ["KI1"],
            "safe_patterns": ["SP1"],
        }
        guide = InvestigationGuide.from_dict(data)
        assert len(guide.steps) == 1
        assert guide.steps[0].action == "Action"

    def test_round_trip(self):
        """Test serialization round-trip."""
        original = InvestigationGuide(
            steps=[
                InvestigationStep(
                    step_number=1,
                    action="Action",
                    look_for="Look",
                    evidence_needed="Evidence",
                    red_flag="Red",
                    safe_if="Safe",
                )
            ],
            questions_to_answer=["Q1", "Q2"],
            common_false_positives=["FP1"],
            key_indicators=["KI1"],
            safe_patterns=["SP1"],
        )
        data = original.to_dict()
        restored = InvestigationGuide.from_dict(data)
        assert len(restored.steps) == len(original.steps)
        assert restored.steps[0].red_flag == original.steps[0].red_flag


class TestVulnerabilityBead:
    """Tests for VulnerabilityBead dataclass."""

    def test_basic_creation(self, sample_bead):
        """Test basic bead creation."""
        assert sample_bead.id == "VKG-001"
        assert sample_bead.vulnerability_class == "reentrancy"
        assert sample_bead.severity == Severity.CRITICAL
        assert sample_bead.confidence == 0.95
        assert sample_bead.status == BeadStatus.PENDING

    def test_confidence_validation(self, sample_bead):
        """Test confidence must be in valid range."""
        # Valid values work
        bead_data = sample_bead.to_dict()
        bead_data["confidence"] = 0.5
        bead_data["context_hash"] = ""  # Reset hash for recalculation
        VulnerabilityBead.from_dict(bead_data)

        # Invalid values raise
        with pytest.raises(ValueError):
            bead_data["confidence"] = 1.5
            VulnerabilityBead.from_dict(bead_data)

    def test_context_hash_calculated(self, sample_bead):
        """Test context hash is calculated on creation."""
        assert sample_bead.context_hash != ""
        assert len(sample_bead.context_hash) == 16

    def test_context_hash_changes_with_code(self, sample_bead):
        """Test context hash changes when code changes."""
        hash1 = sample_bead.context_hash

        # Create new bead with different code
        modified_code = CodeSnippet(
            source="DIFFERENT CODE",
            file_path="/contracts/Vault.sol",
            start_line=45,
            end_line=48,
            function_name="withdraw",
            contract_name="Vault",
        )

        bead2 = VulnerabilityBead(
            id=sample_bead.id,
            vulnerability_class=sample_bead.vulnerability_class,
            pattern_id=sample_bead.pattern_id,
            severity=sample_bead.severity,
            confidence=sample_bead.confidence,
            vulnerable_code=modified_code,
            related_code=[],
            full_contract=None,
            inheritance_chain=sample_bead.inheritance_chain,
            pattern_context=sample_bead.pattern_context,
            investigation_guide=sample_bead.investigation_guide,
            test_context=sample_bead.test_context,
            similar_exploits=[],
            fix_recommendations=sample_bead.fix_recommendations,
        )

        assert bead2.context_hash != hash1

    def test_to_json(self, sample_bead):
        """Test JSON serialization."""
        json_str = sample_bead.to_json()
        data = json.loads(json_str)
        assert data["id"] == "VKG-001"
        assert data["severity"] == "critical"
        assert data["status"] == "pending"

    def test_from_json(self, sample_bead):
        """Test JSON deserialization."""
        json_str = sample_bead.to_json()
        restored = VulnerabilityBead.from_json(json_str)
        assert restored.id == sample_bead.id
        assert restored.severity == sample_bead.severity

    def test_round_trip_serialization(self, sample_bead):
        """Test full round-trip serialization."""
        data = sample_bead.to_dict()
        restored = VulnerabilityBead.from_dict(data)

        assert restored.id == sample_bead.id
        assert restored.vulnerability_class == sample_bead.vulnerability_class
        assert restored.severity == sample_bead.severity
        assert restored.confidence == sample_bead.confidence
        assert restored.vulnerable_code.source == sample_bead.vulnerable_code.source
        assert restored.pattern_context.pattern_name == sample_bead.pattern_context.pattern_name
        assert len(restored.investigation_guide.steps) == len(sample_bead.investigation_guide.steps)

    def test_is_complete(self, sample_bead):
        """Test is_complete validation."""
        assert sample_bead.is_complete() is True

    def test_is_complete_fails_on_missing_id(
        self,
        sample_pattern_context,
        sample_investigation_guide,
        sample_test_context,
    ):
        """Test is_complete fails when ID is missing."""
        incomplete = VulnerabilityBead(
            id="",  # Empty ID
            vulnerability_class="test",
            pattern_id="test",
            severity=Severity.LOW,
            confidence=0.5,
            vulnerable_code=CodeSnippet("code", "/path", 1, 1),
            related_code=[],
            full_contract=None,
            inheritance_chain=[],
            pattern_context=sample_pattern_context,
            investigation_guide=sample_investigation_guide,
            test_context=sample_test_context,
            similar_exploits=[],
            fix_recommendations=[],
        )
        assert incomplete.is_complete() is False

    def test_is_complete_fails_on_empty_steps(
        self,
        sample_vulnerable_code,
        sample_pattern_context,
        sample_test_context,
    ):
        """Test is_complete fails when investigation steps are empty."""
        empty_guide = InvestigationGuide(
            steps=[],
            questions_to_answer=["Q"],
            common_false_positives=[],
            key_indicators=[],
            safe_patterns=[],
        )
        incomplete = VulnerabilityBead(
            id="VKG-001",
            vulnerability_class="test",
            pattern_id="test",
            severity=Severity.LOW,
            confidence=0.5,
            vulnerable_code=sample_vulnerable_code,
            related_code=[],
            full_contract=None,
            inheritance_chain=[],
            pattern_context=sample_pattern_context,
            investigation_guide=empty_guide,
            test_context=sample_test_context,
            similar_exploits=[],
            fix_recommendations=[],
        )
        assert incomplete.is_complete() is False

    def test_add_note(self, sample_bead):
        """Test adding investigation notes."""
        sample_bead.add_note("Found reentrancy guard in parent")
        assert len(sample_bead.notes) == 1
        assert "Found reentrancy guard" in sample_bead.notes[0]
        assert "[" in sample_bead.notes[0]  # Has timestamp

    def test_add_multiple_notes(self, sample_bead):
        """Test adding multiple notes."""
        sample_bead.add_note("Note 1")
        sample_bead.add_note("Note 2")
        assert len(sample_bead.notes) == 2

    def test_set_verdict_true_positive(self, sample_bead):
        """Test setting true positive verdict."""
        verdict = Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="Confirmed via PoC",
            confidence=0.99,
            evidence=["External call before state update"],
        )
        sample_bead.set_verdict(verdict)

        assert sample_bead.verdict == verdict
        assert sample_bead.status == BeadStatus.CONFIRMED

    def test_set_verdict_false_positive(self, sample_bead):
        """Test setting false positive verdict."""
        verdict = Verdict(
            type=VerdictType.FALSE_POSITIVE,
            reason="Has reentrancy guard",
            confidence=0.95,
            evidence=["nonReentrant modifier present"],
        )
        sample_bead.set_verdict(verdict)

        assert sample_bead.verdict == verdict
        assert sample_bead.status == BeadStatus.REJECTED

    def test_set_verdict_inconclusive(self, sample_bead):
        """Test setting inconclusive verdict."""
        verdict = Verdict(
            type=VerdictType.INCONCLUSIVE,
            reason="Need more context",
            confidence=0.5,
            evidence=[],
        )
        sample_bead.set_verdict(verdict)

        assert sample_bead.status == BeadStatus.NEEDS_INFO

    def test_get_llm_prompt(self, sample_bead):
        """Test LLM prompt generation."""
        prompt = sample_bead.get_llm_prompt()

        # Check all major sections are present
        assert "VKG-001" in prompt
        assert "reentrancy" in prompt
        assert "critical" in prompt
        assert "95%" in prompt
        assert "Why Flagged" in prompt
        assert "Vulnerable Code" in prompt
        assert "Investigation Steps" in prompt
        assert "Step 1" in prompt
        assert "Step 2" in prompt
        assert "Questions to Answer" in prompt
        assert "Common False Positives" in prompt
        assert "Safe Patterns" in prompt
        assert "The DAO Hack" in prompt
        assert "Your Task" in prompt
        assert "TRUE POSITIVE" in prompt
        assert "FALSE POSITIVE" in prompt

    def test_get_llm_prompt_with_related_code(self, sample_bead):
        """Test LLM prompt includes related code."""
        related = CodeSnippet(
            source="modifier nonReentrant() { ... }",
            file_path="/contracts/Guard.sol",
            start_line=10,
            end_line=15,
            function_name="nonReentrant",
            contract_name="ReentrancyGuard",
        )
        sample_bead.related_code = [related]

        prompt = sample_bead.get_llm_prompt()
        assert "Related Code" in prompt
        assert "nonReentrant" in prompt

    def test_get_compact_summary(self, sample_bead):
        """Test compact summary generation."""
        summary = sample_bead.get_compact_summary()
        assert "VKG-001" in summary
        assert "critical" in summary
        assert "reentrancy" in summary
        assert "Vault.withdraw()" in summary
        assert "PENDING" in summary

    def test_is_resolved_property(self, sample_bead):
        """Test is_resolved property."""
        assert sample_bead.is_resolved is False

        sample_bead.set_verdict(Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="Test",
            confidence=0.9,
            evidence=[],
        ))
        assert sample_bead.is_resolved is True

    def test_is_true_positive_property(self, sample_bead):
        """Test is_true_positive property."""
        assert sample_bead.is_true_positive is False

        sample_bead.set_verdict(Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="Test",
            confidence=0.9,
            evidence=[],
        ))
        assert sample_bead.is_true_positive is True

    def test_is_false_positive_property(self, sample_bead):
        """Test is_false_positive property."""
        assert sample_bead.is_false_positive is False

        sample_bead.set_verdict(Verdict(
            type=VerdictType.FALSE_POSITIVE,
            reason="Test",
            confidence=0.9,
            evidence=[],
        ))
        assert sample_bead.is_false_positive is True


class TestBeadWithExploits:
    """Tests for beads with exploit references."""

    def test_bead_with_multiple_exploits(
        self,
        sample_vulnerable_code,
        sample_pattern_context,
        sample_investigation_guide,
        sample_test_context,
    ):
        """Test bead with multiple exploit references."""
        exploits = [
            ExploitReference(
                id="dao-2016",
                name="The DAO",
                date="2016-06-17",
                loss="$60M",
                pattern_id="vm-001",
                vulnerable_code="code1",
                exploit_summary="summary1",
                fix="fix1",
                source_url="url1",
            ),
            ExploitReference(
                id="cream-2021",
                name="Cream Finance",
                date="2021-10-27",
                loss="$130M",
                pattern_id="vm-001",
                vulnerable_code="code2",
                exploit_summary="summary2",
                fix="fix2",
                source_url="url2",
            ),
        ]

        bead = VulnerabilityBead(
            id="VKG-002",
            vulnerability_class="reentrancy",
            pattern_id="vm-001",
            severity=Severity.CRITICAL,
            confidence=0.9,
            vulnerable_code=sample_vulnerable_code,
            related_code=[],
            full_contract=None,
            inheritance_chain=[],
            pattern_context=sample_pattern_context,
            investigation_guide=sample_investigation_guide,
            test_context=sample_test_context,
            similar_exploits=exploits,
            fix_recommendations=["Fix 1", "Fix 2"],
        )

        prompt = bead.get_llm_prompt()
        assert "The DAO" in prompt
        assert "Cream Finance" in prompt
        assert "$60M" in prompt
        assert "$130M" in prompt


class TestBeadSerialization:
    """Tests for bead serialization edge cases."""

    def test_serialize_with_verdict(self, sample_bead):
        """Test serialization with verdict."""
        sample_bead.set_verdict(Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="Test",
            confidence=0.9,
            evidence=["evidence1"],
        ))

        data = sample_bead.to_dict()
        assert data["verdict"] is not None
        assert data["verdict"]["type"] == "true_positive"

        restored = VulnerabilityBead.from_dict(data)
        assert restored.verdict is not None
        assert restored.verdict.type == VerdictType.TRUE_POSITIVE

    def test_serialize_without_verdict(self, sample_bead):
        """Test serialization without verdict."""
        data = sample_bead.to_dict()
        assert data["verdict"] is None

        restored = VulnerabilityBead.from_dict(data)
        assert restored.verdict is None

    def test_serialize_with_full_contract(self, sample_bead):
        """Test serialization with full contract source."""
        sample_bead.full_contract = "// Full contract\ncontract Vault { ... }"
        data = sample_bead.to_dict()
        assert data["full_contract"] == "// Full contract\ncontract Vault { ... }"

        restored = VulnerabilityBead.from_dict(data)
        assert restored.full_contract == sample_bead.full_contract

    def test_serialize_timestamps(self, sample_bead):
        """Test timestamp serialization."""
        data = sample_bead.to_dict()
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)

        # Should be ISO format
        datetime.fromisoformat(data["created_at"])
        datetime.fromisoformat(data["updated_at"])


class TestModuleImports:
    """Tests for module-level imports."""

    def test_import_from_package(self):
        """Test imports work from package level."""
        from alphaswarm_sol.beads import (
            VulnerabilityBead,
            TestContext,
            PatternContext,
            InvestigationGuide,
        )

        # Should not raise
        assert VulnerabilityBead is not None
        assert TestContext is not None
        assert PatternContext is not None
        assert InvestigationGuide is not None

    def test_import_from_schema_module(self):
        """Test imports work from schema module."""
        from alphaswarm_sol.beads.schema import (
            VulnerabilityBead,
            TestContext,
            PatternContext,
            InvestigationGuide,
        )

        assert VulnerabilityBead is not None
