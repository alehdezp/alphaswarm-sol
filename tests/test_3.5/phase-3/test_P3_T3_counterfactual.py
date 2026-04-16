"""
Tests for P3-T3: Counterfactual Generator

Validates counterfactual scenario generation, intervention ranking,
and fix recommendation.
"""

import pytest
from unittest.mock import Mock
from alphaswarm_sol.reasoning.counterfactual import (
    CounterfactualGenerator,
    Counterfactual,
    CounterfactualSet,
    InterventionType,
)
from alphaswarm_sol.reasoning.causal import (
    CausalAnalysis,
    CausalGraph,
    RootCause,
    InterventionPoint,
)


# Mock fixtures
@pytest.fixture
def generator():
    """Create counterfactual generator."""
    return CounterfactualGenerator()


def create_mock_root_cause(
    cause_id: str,
    cause_type: str,
    intervention: str,
    confidence: float = 0.9,
    alternatives: list = None,
):
    """Helper to create mock root cause."""
    return RootCause(
        id=cause_id,
        description=f"Test root cause: {cause_type}",
        cause_type=cause_type,
        severity="critical",
        causal_path=["op_1", "op_2"],
        intervention=intervention,
        intervention_confidence=confidence,
        confidence=0.85,
        alternative_interventions=alternatives or [],
    )


def create_mock_intervention_point(
    ip_id: str,
    intervention_type: str,
    description: str,
    impact: float = 0.9,
):
    """Helper to create mock intervention point."""
    return InterventionPoint(
        id=ip_id,
        node_id="test_node",
        intervention_type=intervention_type,
        description=description,
        impact_score=impact,
        complexity="trivial",
        blocks_causes=["rc_1"],
        side_effects=[],
        code_suggestion="// Test code",
    )


def create_mock_causal_analysis(root_causes: list, interventions: list):
    """Helper to create mock causal analysis."""
    graph = CausalGraph(
        id="test_graph",
        focal_node_id="fn_test",
        vulnerability_id="vuln_1",
    )

    return CausalAnalysis(
        causal_graph=graph,
        root_causes=root_causes,
        intervention_points=interventions,
        explanation="Test explanation",
        analysis_time_ms=100.0,
        confidence=0.85,
    )


# ============================================================================
# PART 1: Enum and Dataclass Tests
# ============================================================================

class TestEnumsAndDataclasses:
    """Test enum values and dataclass creation."""

    def test_intervention_type_enum(self):
        """Test InterventionType enum values."""
        assert InterventionType.REMOVE_NODE.value == "remove_node"
        assert InterventionType.REORDER_OPERATIONS.value == "reorder_operations"
        assert InterventionType.ADD_GUARD.value == "add_guard"
        assert InterventionType.ADD_VALIDATION.value == "add_validation"
        assert InterventionType.BREAK_EDGE.value == "break_edge"
        assert InterventionType.CHANGE_PROPERTY.value == "change_property"

    def test_counterfactual_creation(self):
        """Test Counterfactual dataclass creation."""
        cf = Counterfactual(
            id="cf_1",
            scenario_name="Test Scenario",
            original_description="Original state",
            original_vulnerability="critical",
            intervention_type=InterventionType.ADD_GUARD,
            intervention_description="Add guard",
            intervention_target="fn_test",
            blocks_vulnerability=True,
            expected_outcome="Vulnerability prevented",
            confidence=0.9,
            causal_path_broken=["path1"],
            affected_nodes=["node1"],
        )

        assert cf.id == "cf_1"
        assert cf.blocks_vulnerability is True
        assert cf.confidence == 0.9
        assert cf.code_diff is None
        assert cf.side_effects == []

    def test_counterfactual_set_creation(self):
        """Test CounterfactualSet dataclass creation."""
        cf_set = CounterfactualSet(
            vulnerability_id="vuln_1",
            function_id="fn_test",
        )

        assert cf_set.vulnerability_id == "vuln_1"
        assert cf_set.total_scenarios == 0
        assert cf_set.counterfactuals == []


# ============================================================================
# PART 2: Root Cause Counterfactual Generation
# ============================================================================

class TestRootCauseCounterfactuals:
    """Test generating counterfactuals from root causes."""

    def test_generate_for_ordering_violation(self, generator):
        """Test counterfactual for ordering violation."""
        root_cause = create_mock_root_cause(
            "rc_1",
            "ordering_violation",
            "Move state update before external call (CEI pattern)",
        )

        scenarios = generator._generate_for_root_cause(root_cause, Mock())

        # Should generate reorder scenario
        assert len(scenarios) >= 1
        reorder = scenarios[0]
        assert reorder.intervention_type == InterventionType.REORDER_OPERATIONS
        assert reorder.blocks_vulnerability is True
        assert "CEI" in reorder.scenario_name or "Reorder" in reorder.scenario_name

    def test_generate_for_missing_guard(self, generator):
        """Test counterfactual for missing guard."""
        root_cause = create_mock_root_cause(
            "rc_2",
            "missing_guard",
            "Add nonReentrant modifier",
        )

        scenarios = generator._generate_for_root_cause(root_cause, Mock())

        # Should generate guard scenario
        assert len(scenarios) >= 1
        guard = scenarios[0]
        assert guard.intervention_type == InterventionType.ADD_GUARD
        assert guard.blocks_vulnerability is True
        assert "Guard" in guard.scenario_name

    def test_generate_for_missing_validation(self, generator):
        """Test counterfactual for missing validation."""
        root_cause = create_mock_root_cause(
            "rc_3",
            "missing_validation",
            "Add staleness check on oracle response",
        )

        scenarios = generator._generate_for_root_cause(root_cause, Mock())

        # Should generate validation scenario
        assert len(scenarios) >= 1
        validate = scenarios[0]
        assert validate.intervention_type == InterventionType.ADD_VALIDATION
        assert validate.blocks_vulnerability is True
        assert "Validation" in validate.scenario_name or "Check" in validate.scenario_name

    def test_generate_with_alternatives(self, generator):
        """Test generating alternative counterfactuals."""
        root_cause = create_mock_root_cause(
            "rc_4",
            "ordering_violation",
            "Move state update before external call",
            alternatives=[
                "Add nonReentrant modifier",
                "Use pull payment pattern",
            ]
        )

        scenarios = generator._generate_for_root_cause(root_cause, Mock())

        # Should generate main + 2 alternatives = 3 scenarios
        assert len(scenarios) == 3

        # Check alternatives have slightly lower confidence
        main = scenarios[0]
        alt1 = scenarios[1]
        assert alt1.confidence < main.confidence


# ============================================================================
# PART 3: Intervention Point Counterfactuals
# ============================================================================

class TestInterventionPointCounterfactuals:
    """Test generating counterfactuals from intervention points."""

    def test_generate_from_reorder_intervention(self, generator):
        """Test counterfactual from reorder intervention point."""
        ip = create_mock_intervention_point(
            "ip_1",
            "reorder",
            "Reorder operations to follow CEI pattern",
        )

        cf = generator._generate_from_intervention_point(ip, Mock())

        assert cf.intervention_type == InterventionType.REORDER_OPERATIONS
        assert cf.blocks_vulnerability is True
        assert cf.confidence == 0.9

    def test_generate_from_guard_intervention(self, generator):
        """Test counterfactual from add_guard intervention point."""
        ip = create_mock_intervention_point(
            "ip_2",
            "add_guard",
            "Add protective modifier",
        )

        cf = generator._generate_from_intervention_point(ip, Mock())

        assert cf.intervention_type == InterventionType.ADD_GUARD
        assert cf.code_diff == "// Test code"

    def test_generate_from_validation_intervention(self, generator):
        """Test counterfactual from add_check intervention point."""
        ip = create_mock_intervention_point(
            "ip_3",
            "add_check",
            "Add validation check",
        )

        cf = generator._generate_from_intervention_point(ip, Mock())

        assert cf.intervention_type == InterventionType.ADD_VALIDATION


# ============================================================================
# PART 4: Code Diff Generation
# ============================================================================

class TestCodeDiffGeneration:
    """Test code diff generation for different scenarios."""

    def test_reorder_diff_generation(self, generator):
        """Test diff generation for reordering."""
        root_cause = create_mock_root_cause(
            "rc_1",
            "ordering_violation",
            "Move state update before external call",
        )

        diff = generator._generate_reorder_diff(root_cause)

        assert "```diff" in diff
        assert "balances[msg.sender]" in diff
        assert "call{value:" in diff
        assert "-" in diff  # Has removals
        assert "+" in diff  # Has additions

    def test_guard_diff_reentrancy(self, generator):
        """Test diff generation for nonReentrant guard."""
        root_cause = create_mock_root_cause(
            "rc_2",
            "missing_guard",
            "Add nonReentrant modifier",
        )

        diff = generator._generate_guard_diff(root_cause)

        assert "```diff" in diff
        assert "nonReentrant" in diff

    def test_guard_diff_access_control(self, generator):
        """Test diff generation for access control guard."""
        root_cause = create_mock_root_cause(
            "rc_3",
            "missing_guard",
            "Add onlyOwner modifier",
        )

        diff = generator._generate_guard_diff(root_cause)

        assert "```diff" in diff
        assert "onlyOwner" in diff

    def test_validation_diff_staleness(self, generator):
        """Test diff generation for staleness validation."""
        root_cause = RootCause(
            id="rc_4",
            description="Oracle price used without staleness check",
            cause_type="missing_validation",
            severity="high",
            causal_path=["op_1"],
            intervention="Add staleness check",
            intervention_confidence=0.9,
            confidence=0.85,
        )

        diff = generator._generate_validation_diff(root_cause)

        assert "```diff" in diff
        assert "staleness" in diff.lower() or "updatedAt" in diff


# ============================================================================
# PART 5: Complete Counterfactual Generation
# ============================================================================

class TestCompleteGeneration:
    """Test end-to-end counterfactual generation."""

    def test_generate_from_single_root_cause(self, generator):
        """Test generating counterfactuals from single root cause."""
        root_cause = create_mock_root_cause(
            "rc_1",
            "ordering_violation",
            "Reorder operations",
        )
        analysis = create_mock_causal_analysis([root_cause], [])

        cf_set = generator.generate(analysis)

        assert cf_set.vulnerability_id == "vuln_1"
        assert cf_set.function_id == "fn_test"
        assert len(cf_set.counterfactuals) >= 1
        assert cf_set.total_scenarios >= 1

    def test_generate_from_multiple_root_causes(self, generator):
        """Test generating from multiple root causes."""
        root_causes = [
            create_mock_root_cause("rc_1", "ordering_violation", "Reorder"),
            create_mock_root_cause("rc_2", "missing_guard", "Add guard"),
        ]
        analysis = create_mock_causal_analysis(root_causes, [])

        cf_set = generator.generate(analysis)

        # Should have scenarios for both root causes
        assert len(cf_set.counterfactuals) >= 2

    def test_generate_with_interventions(self, generator):
        """Test generating from intervention points."""
        root_cause = create_mock_root_cause("rc_1", "ordering_violation", "Reorder")
        intervention = create_mock_intervention_point("ip_1", "reorder", "Reorder ops")

        analysis = create_mock_causal_analysis([root_cause], [intervention])

        cf_set = generator.generate(analysis)

        # Should have scenarios from both root cause and intervention
        assert len(cf_set.counterfactuals) >= 2

    def test_scenarios_that_block_metric(self, generator):
        """Test that scenarios_that_block metric is calculated."""
        root_cause = create_mock_root_cause("rc_1", "ordering_violation", "Reorder")
        analysis = create_mock_causal_analysis([root_cause], [])

        cf_set = generator.generate(analysis)

        # All generated scenarios should block vulnerability
        assert cf_set.scenarios_that_block == cf_set.total_scenarios
        assert cf_set.scenarios_that_block > 0


# ============================================================================
# PART 6: Scenario Ranking
# ============================================================================

class TestScenarioRanking:
    """Test selecting best counterfactual scenario."""

    def test_select_best_trivial_over_complex(self, generator):
        """Test that trivial fix is preferred over complex."""
        scenarios = [
            Counterfactual(
                id="cf_complex",
                scenario_name="Complex",
                original_description="Test",
                original_vulnerability="critical",
                intervention_type=InterventionType.REORDER_OPERATIONS,
                intervention_description="Complex refactor",
                intervention_target="fn",
                blocks_vulnerability=True,
                expected_outcome="Fixed",
                confidence=0.9,
                causal_path_broken=[],
                affected_nodes=[],
                fix_complexity="complex",
            ),
            Counterfactual(
                id="cf_trivial",
                scenario_name="Trivial",
                original_description="Test",
                original_vulnerability="critical",
                intervention_type=InterventionType.ADD_GUARD,
                intervention_description="Add modifier",
                intervention_target="fn",
                blocks_vulnerability=True,
                expected_outcome="Fixed",
                confidence=0.9,
                causal_path_broken=[],
                affected_nodes=[],
                fix_complexity="trivial",
            ),
        ]

        best = generator._select_best_scenario(scenarios)
        assert best == "cf_trivial"

    def test_select_best_higher_confidence(self, generator):
        """Test that higher confidence is preferred."""
        scenarios = [
            Counterfactual(
                id="cf_low",
                scenario_name="Low confidence",
                original_description="Test",
                original_vulnerability="critical",
                intervention_type=InterventionType.ADD_GUARD,
                intervention_description="Fix",
                intervention_target="fn",
                blocks_vulnerability=True,
                expected_outcome="Fixed",
                confidence=0.7,
                causal_path_broken=[],
                affected_nodes=[],
                fix_complexity="trivial",
            ),
            Counterfactual(
                id="cf_high",
                scenario_name="High confidence",
                original_description="Test",
                original_vulnerability="critical",
                intervention_type=InterventionType.ADD_GUARD,
                intervention_description="Fix",
                intervention_target="fn",
                blocks_vulnerability=True,
                expected_outcome="Fixed",
                confidence=0.95,
                causal_path_broken=[],
                affected_nodes=[],
                fix_complexity="trivial",
            ),
        ]

        best = generator._select_best_scenario(scenarios)
        assert best == "cf_high"

    def test_select_best_fewer_side_effects(self, generator):
        """Test that fewer side effects is preferred."""
        scenarios = [
            Counterfactual(
                id="cf_many_effects",
                scenario_name="Many effects",
                original_description="Test",
                original_vulnerability="critical",
                intervention_type=InterventionType.REORDER_OPERATIONS,
                intervention_description="Fix",
                intervention_target="fn",
                blocks_vulnerability=True,
                expected_outcome="Fixed",
                confidence=0.9,
                causal_path_broken=[],
                affected_nodes=[],
                fix_complexity="trivial",
                side_effects=["Effect 1", "Effect 2", "Effect 3"],
            ),
            Counterfactual(
                id="cf_no_effects",
                scenario_name="No effects",
                original_description="Test",
                original_vulnerability="critical",
                intervention_type=InterventionType.ADD_GUARD,
                intervention_description="Fix",
                intervention_target="fn",
                blocks_vulnerability=True,
                expected_outcome="Fixed",
                confidence=0.9,
                causal_path_broken=[],
                affected_nodes=[],
                fix_complexity="trivial",
                side_effects=[],
            ),
        ]

        best = generator._select_best_scenario(scenarios)
        assert best == "cf_no_effects"

    def test_select_only_blocking_scenarios(self, generator):
        """Test that only blocking scenarios are considered."""
        scenarios = [
            Counterfactual(
                id="cf_nonblocking",
                scenario_name="Non-blocking",
                original_description="Test",
                original_vulnerability="critical",
                intervention_type=InterventionType.CHANGE_PROPERTY,
                intervention_description="Doesn't fix",
                intervention_target="fn",
                blocks_vulnerability=False,  # Doesn't block
                expected_outcome="Not fixed",
                confidence=0.95,
                causal_path_broken=[],
                affected_nodes=[],
                fix_complexity="trivial",
            ),
            Counterfactual(
                id="cf_blocking",
                scenario_name="Blocking",
                original_description="Test",
                original_vulnerability="critical",
                intervention_type=InterventionType.ADD_GUARD,
                intervention_description="Fixes",
                intervention_target="fn",
                blocks_vulnerability=True,  # Blocks
                expected_outcome="Fixed",
                confidence=0.8,
                causal_path_broken=[],
                affected_nodes=[],
                fix_complexity="trivial",
            ),
        ]

        best = generator._select_best_scenario(scenarios)
        assert best == "cf_blocking"


# ============================================================================
# PART 7: Explanation and Reporting
# ============================================================================

class TestExplanationAndReporting:
    """Test generating human-readable explanations."""

    def test_explain_counterfactual(self, generator):
        """Test generating explanation for counterfactual."""
        cf = Counterfactual(
            id="cf_1",
            scenario_name="Test Scenario",
            original_description="External call before state update",
            original_vulnerability="critical",
            intervention_type=InterventionType.REORDER_OPERATIONS,
            intervention_description="Reorder to CEI pattern",
            intervention_target="fn_withdraw",
            blocks_vulnerability=True,
            expected_outcome="Vulnerability prevented",
            confidence=0.95,
            causal_path_broken=["ext_call", "state_write"],
            affected_nodes=["op_1", "op_2"],
            code_diff="```diff\n- old\n+ new\n```",
            fix_complexity="moderate",
        )

        explanation = generator.explain_counterfactual(cf)

        assert "Test Scenario" in explanation
        assert "Original Situation" in explanation
        assert "Counterfactual Intervention" in explanation
        assert "Expected Outcome" in explanation
        assert "reorder_operations" in explanation
        assert "95%" in explanation
        assert "moderate" in explanation

    def test_generate_report(self, generator):
        """Test generating comprehensive report."""
        cf1 = Counterfactual(
            id="cf_1",
            scenario_name="Scenario 1",
            original_description="Test",
            original_vulnerability="critical",
            intervention_type=InterventionType.ADD_GUARD,
            intervention_description="Add guard",
            intervention_target="fn",
            blocks_vulnerability=True,
            expected_outcome="Fixed",
            confidence=0.9,
            causal_path_broken=[],
            affected_nodes=[],
            fix_complexity="trivial",
        )

        cf_set = CounterfactualSet(
            vulnerability_id="vuln_1",
            function_id="fn_test",
            counterfactuals=[cf1],
            total_scenarios=1,
            scenarios_that_block=1,
            recommended_scenario="cf_1",
        )

        report = generator.generate_report(cf_set)

        assert "Counterfactual Analysis Report" in report
        assert "fn_test" in report
        assert "vuln_1" in report
        assert "Recommended Fix" in report
        assert "Scenario 1" in report


# ============================================================================
# PART 8: Intervention Type Inference
# ============================================================================

class TestInterventionTypeInference:
    """Test inferring intervention types from text."""

    def test_infer_reorder(self, generator):
        """Test inferring reorder intervention."""
        assert generator._infer_intervention_type("Move state update before call") == InterventionType.REORDER_OPERATIONS
        assert generator._infer_intervention_type("Reorder operations") == InterventionType.REORDER_OPERATIONS

    def test_infer_guard(self, generator):
        """Test inferring guard intervention."""
        assert generator._infer_intervention_type("Add nonReentrant modifier") == InterventionType.ADD_GUARD
        assert generator._infer_intervention_type("Use guard pattern") == InterventionType.ADD_GUARD

    def test_infer_validation(self, generator):
        """Test inferring validation intervention."""
        assert generator._infer_intervention_type("Add staleness check") == InterventionType.ADD_VALIDATION
        assert generator._infer_intervention_type("Validate input") == InterventionType.ADD_VALIDATION
        assert generator._infer_intervention_type("Require positive amount") == InterventionType.ADD_VALIDATION

    def test_infer_remove(self, generator):
        """Test inferring remove intervention."""
        assert generator._infer_intervention_type("Remove dangerous operation") == InterventionType.REMOVE_NODE
        assert generator._infer_intervention_type("Delete this function") == InterventionType.REMOVE_NODE


# ============================================================================
# PART 9: Integration Tests
# ============================================================================

class TestIntegration:
    """Test integration with causal engine."""

    def test_full_pipeline_reentrancy(self, generator):
        """Test full pipeline for reentrancy vulnerability."""
        # Create realistic reentrancy scenario
        root_cause = RootCause(
            id="rc_reentrancy",
            description="External call before state update violates CEI pattern",
            cause_type="ordering_violation",
            severity="critical",
            causal_path=["fn_withdraw_op_1", "fn_withdraw_op_2"],
            intervention="Move state update before external call (CEI pattern)",
            intervention_confidence=0.95,
            confidence=0.9,
            alternative_interventions=[
                "Add nonReentrant modifier",
                "Use pull payment pattern",
            ],
            related_cwes=["CWE-841"],
        )

        intervention = InterventionPoint(
            id="ip_reorder",
            node_id="fn_withdraw_op_1",
            intervention_type="reorder",
            description="Reorder operations to follow CEI pattern",
            impact_score=0.95,
            complexity="moderate",
            code_suggestion="// Reorder code",
        )

        analysis = create_mock_causal_analysis([root_cause], [intervention])

        # Generate counterfactuals
        cf_set = generator.generate(analysis)

        # Should have multiple scenarios
        assert cf_set.total_scenarios >= 3  # Main + intervention + 2 alternatives

        # Should have recommended fix
        assert cf_set.recommended_scenario is not None

        # Generate report
        report = generator.generate_report(cf_set)
        assert "reentrancy" in report.lower() or "CEI" in report

    def test_full_pipeline_access_control(self, generator):
        """Test full pipeline for access control vulnerability."""
        root_cause = RootCause(
            id="rc_access",
            description="Privileged function lacks access control",
            cause_type="missing_guard",
            severity="critical",
            causal_path=["fn_setOwner"],
            intervention="Add onlyOwner modifier",
            intervention_confidence=0.95,
            confidence=0.9,
            alternative_interventions=["Use AccessControl"],
            related_cwes=["CWE-862"],
        )

        analysis = create_mock_causal_analysis([root_cause], [])

        cf_set = generator.generate(analysis)

        # Should generate guard scenario
        assert any(cf.intervention_type == InterventionType.ADD_GUARD
                   for cf in cf_set.counterfactuals)


# ============================================================================
# PART 10: Success Criteria Tests
# ============================================================================

class TestSuccessCriteria:
    """Test that all success criteria from spec are met."""

    def test_counterfactual_generation_working(self, generator):
        """Verify counterfactual generation works."""
        root_cause = create_mock_root_cause("rc_1", "ordering_violation", "Reorder")
        analysis = create_mock_causal_analysis([root_cause], [])

        cf_set = generator.generate(analysis)

        assert cf_set is not None
        assert len(cf_set.counterfactuals) > 0

    def test_fix_diffs_generated(self, generator):
        """Verify fix diffs are generated."""
        root_cause = create_mock_root_cause("rc_1", "ordering_violation", "Reorder")
        analysis = create_mock_causal_analysis([root_cause], [])

        cf_set = generator.generate(analysis)

        # At least one scenario should have a code diff
        assert any(cf.code_diff is not None for cf in cf_set.counterfactuals)

    def test_integration_with_causal_engine(self, generator):
        """Verify integration with causal engine works."""
        # Create full causal analysis
        root_cause = create_mock_root_cause("rc_1", "ordering_violation", "Reorder")
        intervention = create_mock_intervention_point("ip_1", "reorder", "Reorder")

        analysis = create_mock_causal_analysis([root_cause], [intervention])

        # Should accept causal analysis and generate counterfactuals
        cf_set = generator.generate(analysis)

        assert cf_set.vulnerability_id == analysis.causal_graph.vulnerability_id
        assert cf_set.function_id == analysis.causal_graph.focal_node_id
