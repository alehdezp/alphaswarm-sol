"""
Tests for P3-T4: Attack Path Synthesis

Validates multi-step attack path synthesis, complexity estimation,
and PoC generation.
"""

import pytest
from unittest.mock import Mock
from alphaswarm_sol.reasoning.attack_synthesis import (
    AttackPathSynthesizer,
    AttackPath,
    AttackPathSet,
    AttackStep,
    AttackComplexity,
    AttackImpact,
)
from alphaswarm_sol.reasoning.iterative import (
    ReasoningResult,
    AttackChain,
    ReasoningRound,
)
from alphaswarm_sol.reasoning.causal import (
    CausalAnalysis,
    CausalGraph,
    RootCause,
)


# Mock fixtures
@pytest.fixture
def synthesizer():
    """Create attack path synthesizer."""
    return AttackPathSynthesizer()


def create_mock_attack_chain(
    chain_id: str,
    functions: list,
    entry: str,
    exit: str,
    feasibility: float = 0.8,
    impact: str = "high",
):
    """Helper to create mock attack chain."""
    return AttackChain(
        id=chain_id,
        functions=functions,
        entry_point=entry,
        exit_point=exit,
        pattern_ids=["test_pattern"],
        description="Test chain",
        feasibility=feasibility,
        impact=impact,
        preconditions=[],
        evidence=[],
        cross_graph_support=[],
    )


def create_mock_reasoning_result(chains: list, candidates: list):
    """Helper to create mock reasoning result."""
    return ReasoningResult(
        rounds=[],
        final_candidates=candidates,
        attack_chains=chains,
        all_cross_graph_findings=[],
        converged=True,
        convergence_round=2,
        convergence_reason="test",
        total_time_ms=100.0,
        total_nodes_explored=5,
        total_cross_graph_queries=0,
        single_pass_would_find=[],
        iterative_bonus_findings=[],
    )


# ============================================================================
# PART 1: Enum and Dataclass Tests
# ============================================================================

class TestEnumsAndDataclasses:
    """Test enum values and dataclass creation."""

    def test_attack_complexity_enum(self):
        """Test AttackComplexity enum values."""
        assert AttackComplexity.TRIVIAL.value == "trivial"
        assert AttackComplexity.LOW.value == "low"
        assert AttackComplexity.MEDIUM.value == "medium"
        assert AttackComplexity.HIGH.value == "high"
        assert AttackComplexity.VERY_HIGH.value == "very_high"

    def test_attack_impact_enum(self):
        """Test AttackImpact enum values."""
        assert AttackImpact.NEGLIGIBLE.value == "negligible"
        assert AttackImpact.LOW.value == "low"
        assert AttackImpact.MEDIUM.value == "medium"
        assert AttackImpact.HIGH.value == "high"
        assert AttackImpact.CRITICAL.value == "critical"

    def test_attack_step_creation(self):
        """Test AttackStep dataclass creation."""
        step = AttackStep(
            step_number=1,
            description="Call function",
            function_called="fn_test",
            transaction_type="exploit",
        )

        assert step.step_number == 1
        assert step.requires_setup is False
        assert step.preconditions == []

    def test_attack_path_creation(self):
        """Test AttackPath dataclass creation."""
        path = AttackPath(
            id="path_1",
            name="Test Attack",
            entry_point="fn_entry",
            steps=[],
            exit_point="fn_exit",
            complexity=AttackComplexity.LOW,
            estimated_impact=AttackImpact.HIGH,
            total_steps=2,
            feasibility_score=0.8,
        )

        assert path.id == "path_1"
        assert path.complexity == AttackComplexity.LOW
        assert path.feasibility_score == 0.8
        assert path.required_conditions == []

    def test_attack_path_set_creation(self):
        """Test AttackPathSet dataclass creation."""
        path_set = AttackPathSet(
            target_contract="TestContract",
        )

        assert path_set.target_contract == "TestContract"
        assert path_set.total_paths == 0
        assert path_set.all_paths == []


# ============================================================================
# PART 2: Attack Chain Synthesis
# ============================================================================

class TestAttackChainSynthesis:
    """Test synthesizing paths from attack chains."""

    def test_synthesize_from_single_chain(self, synthesizer):
        """Test synthesizing from single attack chain."""
        chain = create_mock_attack_chain(
            "chain_1",
            ["fn_entry", "fn_vulnerable"],
            "fn_entry",
            "fn_vulnerable",
        )
        reasoning = create_mock_reasoning_result([chain], [])

        path_set = synthesizer.synthesize(reasoning)

        assert path_set.total_paths == 1
        assert len(path_set.all_paths) == 1

        path = path_set.all_paths[0]
        assert path.entry_point == "fn_entry"
        assert path.exit_point == "fn_vulnerable"

    def test_synthesize_from_multi_step_chain(self, synthesizer):
        """Test synthesizing from multi-step chain."""
        chain = create_mock_attack_chain(
            "chain_1",
            ["fn_1", "fn_2", "fn_3", "fn_4"],
            "fn_1",
            "fn_4",
        )
        reasoning = create_mock_reasoning_result([chain], [])

        path_set = synthesizer.synthesize(reasoning)

        path = path_set.all_paths[0]
        assert path.total_steps == 4
        assert len(path.steps) == 4

    def test_synthesize_from_multiple_chains(self, synthesizer):
        """Test synthesizing from multiple chains."""
        chains = [
            create_mock_attack_chain("chain_1", ["fn_1", "fn_2"], "fn_1", "fn_2"),
            create_mock_attack_chain("chain_2", ["fn_3", "fn_4"], "fn_3", "fn_4"),
        ]
        reasoning = create_mock_reasoning_result(chains, [])

        path_set = synthesizer.synthesize(reasoning)

        assert path_set.total_paths == 2


# ============================================================================
# PART 3: Candidate Synthesis
# ============================================================================

class TestCandidateSynthesis:
    """Test synthesizing paths from candidates."""

    def test_synthesize_from_candidate_without_causal(self, synthesizer):
        """Test synthesizing from candidate without causal analysis."""
        reasoning = create_mock_reasoning_result([], ["fn_vulnerable"])

        path_set = synthesizer.synthesize(reasoning, None)

        assert path_set.total_paths == 1
        path = path_set.all_paths[0]
        assert path.entry_point == "fn_vulnerable"
        assert path.total_steps == 1

    def test_synthesize_from_candidate_with_causal(self, synthesizer):
        """Test synthesizing from candidate with causal analysis."""
        # Create causal analysis
        root_cause = RootCause(
            id="rc_1",
            description="Test root cause",
            cause_type="ordering_violation",
            severity="critical",
            causal_path=["op_1", "op_2"],
            intervention="Fix it",
            intervention_confidence=0.9,
            confidence=0.85,
        )

        graph = CausalGraph(
            id="cg_1",
            focal_node_id="fn_vulnerable",
        )

        causal = CausalAnalysis(
            causal_graph=graph,
            root_causes=[root_cause],
            intervention_points=[],
            explanation="Test",
            analysis_time_ms=100.0,
            confidence=0.85,
        )

        reasoning = create_mock_reasoning_result([], ["fn_vulnerable"])

        path_set = synthesizer.synthesize(reasoning, [causal])

        assert path_set.total_paths == 1
        path = path_set.all_paths[0]
        # Should have setup step + exploit step
        assert path.total_steps >= 1


# ============================================================================
# PART 4: Complexity Estimation
# ============================================================================

class TestComplexityEstimation:
    """Test attack complexity estimation."""

    def test_estimate_trivial_complexity(self, synthesizer):
        """Test estimating trivial complexity."""
        complexity = synthesizer._estimate_complexity(1, 0.95)
        assert complexity == AttackComplexity.TRIVIAL

    def test_estimate_low_complexity(self, synthesizer):
        """Test estimating low complexity."""
        complexity = synthesizer._estimate_complexity(2, 0.8)
        assert complexity == AttackComplexity.LOW

    def test_estimate_medium_complexity(self, synthesizer):
        """Test estimating medium complexity."""
        complexity = synthesizer._estimate_complexity(4, 0.6)
        assert complexity == AttackComplexity.MEDIUM

    def test_estimate_high_complexity(self, synthesizer):
        """Test estimating high complexity."""
        complexity = synthesizer._estimate_complexity(6, 0.4)
        assert complexity == AttackComplexity.HIGH

    def test_estimate_very_high_complexity(self, synthesizer):
        """Test estimating very high complexity."""
        complexity = synthesizer._estimate_complexity(10, 0.2)
        assert complexity == AttackComplexity.VERY_HIGH


# ============================================================================
# PART 5: Impact Estimation
# ============================================================================

class TestImpactEstimation:
    """Test attack impact estimation."""

    def test_estimate_critical_impact(self, synthesizer):
        """Test estimating critical impact."""
        impact = synthesizer._estimate_impact("critical")
        assert impact == AttackImpact.CRITICAL

    def test_estimate_high_impact(self, synthesizer):
        """Test estimating high impact."""
        impact = synthesizer._estimate_impact("high")
        assert impact == AttackImpact.HIGH

    def test_estimate_medium_impact(self, synthesizer):
        """Test estimating medium impact."""
        impact = synthesizer._estimate_impact("medium")
        assert impact == AttackImpact.MEDIUM

    def test_estimate_low_impact(self, synthesizer):
        """Test estimating low impact."""
        impact = synthesizer._estimate_impact("low")
        assert impact == AttackImpact.LOW

    def test_estimate_unknown_defaults_to_medium(self, synthesizer):
        """Test that unknown impact defaults to medium."""
        impact = synthesizer._estimate_impact("unknown")
        assert impact == AttackImpact.MEDIUM


# ============================================================================
# PART 6: PoC Generation
# ============================================================================

class TestPoCGeneration:
    """Test PoC code generation."""

    def test_generate_poc_single_step(self, synthesizer):
        """Test generating PoC for single step."""
        steps = [
            AttackStep(
                step_number=1,
                description="Call vulnerable function",
                function_called="fn_vulnerable",
                transaction_type="exploit",
                code_snippet="target.fn_vulnerable()",
            )
        ]

        poc = synthesizer._generate_poc_from_steps(steps)

        assert "Attack Proof of Concept" in poc
        assert "Step 1" in poc
        assert "target.fn_vulnerable()" in poc

    def test_generate_poc_multi_step(self, synthesizer):
        """Test generating PoC for multiple steps."""
        steps = [
            AttackStep(
                step_number=1,
                description="Setup",
                function_called="setup",
                transaction_type="setup",
                requires_setup=True,
                setup_description="Setup attack conditions",
                code_snippet="// Setup code",
            ),
            AttackStep(
                step_number=2,
                description="Exploit",
                function_called="exploit",
                transaction_type="exploit",
                code_snippet="target.exploit()",
            ),
        ]

        poc = synthesizer._generate_poc_from_steps(steps)

        assert "Step 1" in poc
        assert "Step 2" in poc
        assert "Setup attack conditions" in poc
        assert "target.exploit()" in poc


# ============================================================================
# PART 7: Path Organization
# ============================================================================

class TestPathOrganization:
    """Test organizing paths by severity."""

    def test_organize_by_severity(self, synthesizer):
        """Test organizing paths by impact severity."""
        paths = [
            AttackPath(
                id="path_1",
                name="Critical",
                entry_point="fn_1",
                steps=[],
                exit_point="fn_1",
                complexity=AttackComplexity.LOW,
                estimated_impact=AttackImpact.CRITICAL,
                total_steps=1,
                feasibility_score=0.8,
            ),
            AttackPath(
                id="path_2",
                name="Medium",
                entry_point="fn_2",
                steps=[],
                exit_point="fn_2",
                complexity=AttackComplexity.LOW,
                estimated_impact=AttackImpact.MEDIUM,
                total_steps=1,
                feasibility_score=0.8,
            ),
        ]

        organized = synthesizer._organize_by_severity(paths)

        assert len(organized["critical"]) == 1
        assert len(organized["medium"]) == 1
        assert len(organized["high"]) == 0

    def test_find_highest_impact(self, synthesizer):
        """Test finding highest impact path."""
        paths = [
            AttackPath(
                id="path_low",
                name="Low",
                entry_point="fn",
                steps=[],
                exit_point="fn",
                complexity=AttackComplexity.LOW,
                estimated_impact=AttackImpact.LOW,
                total_steps=1,
                feasibility_score=0.8,
            ),
            AttackPath(
                id="path_critical",
                name="Critical",
                entry_point="fn",
                steps=[],
                exit_point="fn",
                complexity=AttackComplexity.LOW,
                estimated_impact=AttackImpact.CRITICAL,
                total_steps=1,
                feasibility_score=0.8,
            ),
        ]

        highest = synthesizer._find_highest_impact(paths)
        assert highest == "path_critical"

    def test_find_easiest(self, synthesizer):
        """Test finding easiest path."""
        paths = [
            AttackPath(
                id="path_complex",
                name="Complex",
                entry_point="fn",
                steps=[],
                exit_point="fn",
                complexity=AttackComplexity.HIGH,
                estimated_impact=AttackImpact.HIGH,
                total_steps=1,
                feasibility_score=0.5,
            ),
            AttackPath(
                id="path_trivial",
                name="Trivial",
                entry_point="fn",
                steps=[],
                exit_point="fn",
                complexity=AttackComplexity.TRIVIAL,
                estimated_impact=AttackImpact.HIGH,
                total_steps=1,
                feasibility_score=0.9,
            ),
        ]

        easiest = synthesizer._find_easiest(paths)
        assert easiest == "path_trivial"


# ============================================================================
# PART 8: Reporting
# ============================================================================

class TestReporting:
    """Test report generation."""

    def test_generate_report(self, synthesizer):
        """Test generating attack path report."""
        path = AttackPath(
            id="path_1",
            name="Test Attack",
            entry_point="fn_entry",
            steps=[],
            exit_point="fn_exit",
            complexity=AttackComplexity.LOW,
            estimated_impact=AttackImpact.HIGH,
            total_steps=2,
            feasibility_score=0.8,
        )

        path_set = AttackPathSet(
            target_contract="TestContract",
            total_paths=1,
            all_paths=[path],
            highest_impact_path="path_1",
            easiest_path="path_1",
        )
        path_set.paths_by_severity = synthesizer._organize_by_severity([path])

        report = synthesizer.generate_report(path_set)

        assert "Attack Path Analysis Report" in report
        assert "TestContract" in report
        assert "Total Paths Found" in report
        assert "1" in report  # Check for the count
        assert "high" in report.lower()

    def test_explain_attack_path(self, synthesizer):
        """Test explaining individual attack path."""
        step = AttackStep(
            step_number=1,
            description="Exploit",
            function_called="fn_vulnerable",
            transaction_type="exploit",
            code_snippet="target.fn_vulnerable()",
        )

        path = AttackPath(
            id="path_1",
            name="Test Attack",
            entry_point="fn_entry",
            steps=[step],
            exit_point="fn_exit",
            complexity=AttackComplexity.LOW,
            estimated_impact=AttackImpact.HIGH,
            total_steps=1,
            feasibility_score=0.8,
        )

        explanation = synthesizer.explain_attack_path(path)

        assert "Attack Path: Test Attack" in explanation
        assert "Overview" in explanation
        assert "Attack Flow" in explanation
        assert "Step-by-Step Breakdown" in explanation
        assert "fn_vulnerable" in explanation


# ============================================================================
# PART 9: Step Type Inference
# ============================================================================

class TestStepTypeInference:
    """Test inferring step types."""

    def test_infer_first_step_is_setup(self, synthesizer):
        """Test that first step is inferred as setup."""
        chain = create_mock_attack_chain("chain", ["fn_1", "fn_2"], "fn_1", "fn_2")
        step_type = synthesizer._infer_step_type(0, 2, chain)
        assert step_type == "setup"

    def test_infer_last_step_is_exploit(self, synthesizer):
        """Test that last step is inferred as exploit."""
        chain = create_mock_attack_chain("chain", ["fn_1", "fn_2"], "fn_1", "fn_2")
        step_type = synthesizer._infer_step_type(1, 2, chain)
        assert step_type == "exploit"

    def test_infer_middle_step_is_intermediate(self, synthesizer):
        """Test that middle steps are intermediate."""
        chain = create_mock_attack_chain("chain", ["fn_1", "fn_2", "fn_3"], "fn_1", "fn_3")
        step_type = synthesizer._infer_step_type(1, 3, chain)
        assert step_type == "intermediate"


# ============================================================================
# PART 10: Integration Tests
# ============================================================================

class TestIntegration:
    """Test end-to-end attack path synthesis."""

    def test_full_synthesis_pipeline(self, synthesizer):
        """Test complete synthesis pipeline."""
        # Create realistic multi-step chain
        chain = create_mock_attack_chain(
            "reentrancy_chain",
            ["fn_deposit", "fn_withdraw", "fn_deposit"],  # Reentrancy pattern
            "fn_deposit",
            "fn_deposit",
            feasibility=0.85,
            impact="critical",
        )

        reasoning = create_mock_reasoning_result([chain], [])

        # Synthesize paths
        path_set = synthesizer.synthesize(reasoning)

        # Verify results
        assert path_set.total_paths == 1
        assert path_set.highest_impact_path is not None
        assert path_set.easiest_path is not None

        path = path_set.all_paths[0]
        assert path.complexity in [AttackComplexity.LOW, AttackComplexity.MEDIUM]
        assert path.estimated_impact == AttackImpact.CRITICAL
        assert path.total_steps == 3

        # Verify PoC generated
        assert path.poc_code is not None
        assert "Step" in path.poc_code

    def test_synthesis_with_both_chains_and_candidates(self, synthesizer):
        """Test synthesis with both chains and candidates."""
        chain = create_mock_attack_chain("chain_1", ["fn_1", "fn_2"], "fn_1", "fn_2")
        reasoning = create_mock_reasoning_result([chain], ["fn_3"])

        path_set = synthesizer.synthesize(reasoning, None)

        # Should synthesize from chain, not candidate (chains preferred)
        assert path_set.total_paths == 1


# ============================================================================
# PART 11: Success Criteria Tests
# ============================================================================

class TestSuccessCriteria:
    """Test that all success criteria from spec are met."""

    def test_multi_function_path_synthesis_working(self, synthesizer):
        """Verify multi-function path synthesis works."""
        chain = create_mock_attack_chain(
            "multi_step",
            ["fn_1", "fn_2", "fn_3", "fn_4"],
            "fn_1",
            "fn_4",
        )
        reasoning = create_mock_reasoning_result([chain], [])

        path_set = synthesizer.synthesize(reasoning)

        assert path_set.total_paths > 0
        path = path_set.all_paths[0]
        assert path.total_steps == 4

    def test_poc_generation_working(self, synthesizer):
        """Verify PoC generation works."""
        chain = create_mock_attack_chain("chain", ["fn_1", "fn_2"], "fn_1", "fn_2")
        reasoning = create_mock_reasoning_result([chain], [])

        path_set = synthesizer.synthesize(reasoning)

        path = path_set.all_paths[0]
        assert path.poc_code is not None
        assert len(path.poc_code) > 0
        assert "Attack Proof of Concept" in path.poc_code

    def test_integration_with_reasoning_engine(self, synthesizer):
        """Verify integration with reasoning engine works."""
        # Create reasoning result with attack chains
        chain = create_mock_attack_chain("chain", ["fn_1"], "fn_1", "fn_1")
        reasoning = create_mock_reasoning_result([chain], [])

        # Should accept reasoning result and synthesize paths
        path_set = synthesizer.synthesize(reasoning)

        assert path_set is not None
        assert isinstance(path_set, AttackPathSet)
