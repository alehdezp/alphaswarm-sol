"""Tests for confidence elevation via tests (SDK-14) and PoC narratives (SDK-15).

Tests the confidence elevation system that elevates to CONFIRMED when
exploit tests pass, and the PoC narrative generator for attacker claims.

Per 05.2-CONTEXT.md:
- Pass = confirmed (passing exploit test elevates confidence to "confirmed")
- No human review needed if test demonstrates the vulnerability
- tests_run stored in work_state for debate protocol
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from alphaswarm_sol.agents.confidence import (
    ConfidenceElevator,
    ElevationResult,
    PoCNarrativeGenerator,
    ExploitNarrative,
)
from alphaswarm_sol.agents.roles import GeneratedTest, ForgeTestResult, ForgeBuildResult
from alphaswarm_sol.orchestration.schemas import VerdictConfidence
from alphaswarm_sol.beads.types import Severity


@pytest.fixture
def mock_bead():
    """Create a mock VulnerabilityBead for testing."""
    bead = MagicMock()
    bead.id = "VKG-001"
    bead.vulnerability_class = "reentrancy"
    bead.severity = Severity.CRITICAL
    bead.verdict = None
    bead.human_flag = True
    bead.work_state = None
    bead.notes = []
    bead.add_note = MagicMock()
    bead.pattern_context.why_flagged = "External call before state update"
    bead.pattern_context.pattern_name = "Classic Reentrancy"
    bead.vulnerable_code.source = "function withdraw() { msg.sender.call{value: balances[msg.sender]}(''); balances[msg.sender] = 0; }"
    bead.vulnerable_code.contract_name = "Vault"
    bead.test_context.attack_scenario = "1. Deploy attacker contract\n2. Call withdraw\n3. Re-enter in fallback"
    bead.test_context.setup_requirements = ["Attacker contract with fallback"]
    bead.fix_recommendations = ["Use reentrancy guard", "Follow CEI pattern"]
    return bead


@pytest.fixture
def passing_test():
    """Create a GeneratedTest with passing results."""
    return GeneratedTest(
        bead_id="VKG-001",
        test_code="contract ExploitTest { function test_reentrancy_exploit() public { /* reentrancy attack */ } }",
        test_file="test/Exploit.t.sol",
        expected_outcome="Drain funds via reentrancy",
        compile_result=ForgeBuildResult(success=True),
        test_results=[ForgeTestResult("test_reentrancy_exploit", passed=True)],
    )


@pytest.fixture
def failing_test():
    """Create a GeneratedTest with failing results (revert)."""
    return GeneratedTest(
        bead_id="VKG-001",
        test_code="contract ExploitTest { function test_exploit() { /* exploit */ } }",
        test_file="test/Exploit.t.sol",
        expected_outcome="Drain funds",
        compile_result=ForgeBuildResult(success=True),
        test_results=[
            ForgeTestResult(
                "test_exploit", passed=False, failure_reason="revert: ReentrancyGuard: reentrant call"
            )
        ],
    )


@pytest.fixture
def compile_failure_test():
    """Create a GeneratedTest that failed to compile."""
    return GeneratedTest(
        bead_id="VKG-001",
        test_code="invalid solidity code {{{",
        test_file="test/Exploit.t.sol",
        expected_outcome="",
        compile_result=ForgeBuildResult(success=False, errors=["Error: Parse error"]),
        test_results=[],
    )


class TestConfidenceElevator:
    """Tests for ConfidenceElevator."""

    def test_elevate_on_passing_test(self, mock_bead, passing_test):
        """Passing test should elevate to CONFIRMED."""
        elevator = ConfidenceElevator()
        result = elevator.elevate_on_test(
            mock_bead,
            VerdictConfidence.LIKELY,
            passing_test,
        )

        assert result.elevated
        assert result.new_confidence == VerdictConfidence.CONFIRMED
        assert "passed" in result.reason.lower()
        assert result.tests_run == ["test_reentrancy_exploit"]

    def test_no_elevation_on_failing_test(self, mock_bead, failing_test):
        """Failing test with revert should downgrade to UNCERTAIN."""
        elevator = ConfidenceElevator()
        result = elevator.elevate_on_test(
            mock_bead,
            VerdictConfidence.LIKELY,
            failing_test,
        )

        assert not result.elevated
        assert result.new_confidence == VerdictConfidence.UNCERTAIN  # Downgraded due to revert
        assert "revert" in result.reason.lower()

    def test_no_elevation_on_compile_failure(self, mock_bead, compile_failure_test):
        """Compile failure should be inconclusive (no change)."""
        elevator = ConfidenceElevator()
        result = elevator.elevate_on_test(
            mock_bead,
            VerdictConfidence.LIKELY,
            compile_failure_test,
        )

        assert not result.elevated
        assert result.new_confidence == VerdictConfidence.LIKELY  # Unchanged
        assert "compile" in result.reason.lower()

    def test_apply_elevation_clears_human_flag(self, mock_bead, passing_test):
        """Confirmed via test should clear human_flag."""
        elevator = ConfidenceElevator()
        result = elevator.elevate_on_test(mock_bead, VerdictConfidence.LIKELY, passing_test)

        updated_bead = elevator.apply_elevation(mock_bead, result)

        assert not updated_bead.human_flag
        assert updated_bead.verdict is not None
        mock_bead.add_note.assert_called()

    def test_tests_run_stored(self, mock_bead, passing_test):
        """tests_run should be stored in work_state."""
        elevator = ConfidenceElevator()
        result = elevator.elevate_on_test(mock_bead, VerdictConfidence.LIKELY, passing_test)

        updated_bead = elevator.apply_elevation(mock_bead, result)

        assert "tests_run" in updated_bead.work_state
        assert "test_reentrancy_exploit" in updated_bead.work_state["tests_run"]

    def test_apply_elevation_non_elevated(self, mock_bead, compile_failure_test):
        """Non-elevated result should add failure note."""
        elevator = ConfidenceElevator()
        result = elevator.elevate_on_test(mock_bead, VerdictConfidence.LIKELY, compile_failure_test)

        updated_bead = elevator.apply_elevation(mock_bead, result)

        # Should have called add_note with failure reason
        mock_bead.add_note.assert_called()
        assert "failed" in mock_bead.add_note.call_args[0][0].lower()

    def test_validate_evidence_chain(self, mock_bead, passing_test):
        """Should validate test relates to bead."""
        elevator = ConfidenceElevator()
        assert elevator.validate_evidence_chain(mock_bead, passing_test)

    def test_validate_rejects_mismatched_bead(self, mock_bead, passing_test):
        """Should reject test for different bead."""
        passing_test.bead_id = "VKG-999"
        elevator = ConfidenceElevator()
        assert not elevator.validate_evidence_chain(mock_bead, passing_test)

    def test_validate_rejects_compile_failure(self, mock_bead, compile_failure_test):
        """Should reject test that failed to compile."""
        elevator = ConfidenceElevator()
        assert not elevator.validate_evidence_chain(mock_bead, compile_failure_test)

    def test_elevation_result_to_dict(self, mock_bead, passing_test):
        """ElevationResult should serialize to dict."""
        elevator = ConfidenceElevator()
        result = elevator.elevate_on_test(mock_bead, VerdictConfidence.LIKELY, passing_test)

        result_dict = result.to_dict()

        assert result_dict["bead_id"] == "VKG-001"
        assert result_dict["original_confidence"] == "likely"
        assert result_dict["new_confidence"] == "confirmed"
        assert result_dict["elevated"] is True

    def test_multiple_test_results(self, mock_bead):
        """Should handle multiple test results."""
        test = GeneratedTest(
            bead_id="VKG-001",
            test_code="contract Tests { function test_a() {} function test_b() {} }",
            test_file="test/Tests.t.sol",
            expected_outcome="Both pass",
            compile_result=ForgeBuildResult(success=True),
            test_results=[
                ForgeTestResult("test_a", passed=True),
                ForgeTestResult("test_b", passed=False, failure_reason="assertion failed"),
            ],
        )

        elevator = ConfidenceElevator()
        result = elevator.elevate_on_test(mock_bead, VerdictConfidence.LIKELY, test)

        # Any passing test should elevate
        assert result.elevated
        assert result.new_confidence == VerdictConfidence.CONFIRMED
        assert len(result.tests_run) == 2


class TestPoCNarrativeGenerator:
    """Tests for PoCNarrativeGenerator."""

    @pytest.mark.asyncio
    async def test_generate_narrative(self, mock_bead, passing_test):
        """Should generate narrative from bead via LLM."""
        mock_runtime = MagicMock()
        mock_runtime.spawn_agent = AsyncMock(
            return_value=MagicMock(
                content='{"title": "Reentrancy in Vault", "vulnerability_summary": "CEI violation", "attack_steps": ["1. Deploy attacker", "2. Call withdraw"], "prerequisites": ["Ether"], "economic_impact": "High - drain all funds", "mitigation": "Use nonReentrant"}'
            )
        )

        generator = PoCNarrativeGenerator(mock_runtime)
        narrative = await generator.generate_narrative(mock_bead, passing_test)

        assert narrative.bead_id == "VKG-001"
        assert "Reentrancy" in narrative.title
        assert narrative.poc_reference == "test/Exploit.t.sol"
        assert len(narrative.attack_steps) == 2

    @pytest.mark.asyncio
    async def test_generate_narrative_no_test(self, mock_bead):
        """Should generate narrative without test result."""
        mock_runtime = MagicMock()
        mock_runtime.spawn_agent = AsyncMock(
            return_value=MagicMock(
                content='{"title": "Reentrancy Exploit", "vulnerability_summary": "...", "attack_steps": ["step"], "prerequisites": [], "economic_impact": "Medium", "mitigation": "..."}'
            )
        )

        generator = PoCNarrativeGenerator(mock_runtime)
        narrative = await generator.generate_narrative(mock_bead)

        assert narrative.bead_id == "VKG-001"
        assert narrative.poc_reference is None

    @pytest.mark.asyncio
    async def test_generate_narrative_parse_failure(self, mock_bead):
        """Should handle JSON parse failure gracefully."""
        mock_runtime = MagicMock()
        mock_runtime.spawn_agent = AsyncMock(
            return_value=MagicMock(content="This is not valid JSON at all")
        )

        generator = PoCNarrativeGenerator(mock_runtime)
        narrative = await generator.generate_narrative(mock_bead)

        # Should fallback to bead data
        assert narrative.bead_id == "VKG-001"
        assert "reentrancy" in narrative.title.lower() or "Exploit" in narrative.title

    def test_from_bead_directly(self, mock_bead):
        """Should create narrative without LLM."""
        generator = PoCNarrativeGenerator.__new__(PoCNarrativeGenerator)
        narrative = generator.from_bead_directly(mock_bead)

        assert narrative.bead_id == "VKG-001"
        assert "Vault" in narrative.title
        assert len(narrative.attack_steps) > 0
        assert "Attacker contract" in narrative.prerequisites[0]
        assert "reentrancy guard" in narrative.mitigation.lower()

    def test_narrative_to_markdown(self):
        """Should render as markdown."""
        narrative = ExploitNarrative(
            bead_id="VKG-001",
            title="Reentrancy in Vault.withdraw()",
            vulnerability_summary="External call before state update allows reentrancy",
            attack_steps=["Deploy attacker contract", "Call withdraw", "Re-enter in fallback"],
            prerequisites=["Attacker contract with receive()"],
            economic_impact="High - can drain all funds",
            poc_reference="test/Exploit.t.sol",
            mitigation="Use nonReentrant modifier",
        )

        md = narrative.to_markdown()

        assert "# Reentrancy in Vault.withdraw()" in md
        assert "1. Deploy attacker contract" in md
        assert "- Attacker contract with receive()" in md
        assert "See: test/Exploit.t.sol" in md

    def test_narrative_to_dict(self):
        """Should serialize to dict."""
        narrative = ExploitNarrative(
            bead_id="VKG-001",
            title="Test Exploit",
            vulnerability_summary="Summary",
            attack_steps=["Step 1"],
            prerequisites=["Prereq 1"],
            economic_impact="High",
            poc_reference="test.sol",
            mitigation="Fix it",
        )

        data = narrative.to_dict()

        assert data["bead_id"] == "VKG-001"
        assert data["title"] == "Test Exploit"
        assert data["attack_steps"] == ["Step 1"]

    def test_narrative_no_poc(self):
        """Should handle missing PoC reference."""
        narrative = ExploitNarrative(
            bead_id="VKG-001",
            title="Exploit",
            vulnerability_summary="...",
            attack_steps=[],
            prerequisites=[],
            economic_impact="",
            poc_reference=None,
            mitigation="",
        )

        md = narrative.to_markdown()
        assert "No PoC available" in md


class TestElevationIntegration:
    """Integration tests for elevation workflow."""

    def test_full_elevation_workflow(self, mock_bead, passing_test):
        """Test complete workflow: test pass -> elevation -> bead update."""
        elevator = ConfidenceElevator()

        # 1. Validate evidence chain
        assert elevator.validate_evidence_chain(mock_bead, passing_test)

        # 2. Elevate on test
        result = elevator.elevate_on_test(
            mock_bead,
            VerdictConfidence.UNCERTAIN,  # Start at low confidence
            passing_test,
        )

        # 3. Apply elevation
        updated_bead = elevator.apply_elevation(mock_bead, result)

        # Verify outcomes
        assert result.elevated
        assert result.original_confidence == VerdictConfidence.UNCERTAIN
        assert result.new_confidence == VerdictConfidence.CONFIRMED
        assert not updated_bead.human_flag
        assert updated_bead.work_state["tests_run"] == ["test_reentrancy_exploit"]

    def test_failed_test_workflow(self, mock_bead, failing_test):
        """Test workflow when test fails with revert."""
        elevator = ConfidenceElevator()

        result = elevator.elevate_on_test(
            mock_bead,
            VerdictConfidence.LIKELY,
            failing_test,
        )

        updated_bead = elevator.apply_elevation(mock_bead, result)

        # Verify no elevation
        assert not result.elevated
        assert result.new_confidence == VerdictConfidence.UNCERTAIN
        # Human flag should NOT be cleared
        assert updated_bead.human_flag  # Still True
