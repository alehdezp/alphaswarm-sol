"""
Tests for P2-T2: Attacker Agent

Tests attack construction, strategy selection, and exploitability scoring.
"""

import pytest
from unittest.mock import Mock, MagicMock

from alphaswarm_sol.agents.attacker import (
    AttackCategory,
    AttackFeasibility,
    EconomicImpact,
    AttackPrerequisite,
    AttackStep,
    EconomicAnalysis,
    AttackConstruction,
    ExploitabilityFactors,
    AttackerAgent,
    AttackerResult,
)


# Test Fixtures


@pytest.fixture
def attacker_agent():
    """Create attacker agent without LLM."""
    return AttackerAgent(use_llm=False)


@pytest.fixture
def reentrancy_context():
    """Context for reentrancy vulnerability."""
    context = Mock()
    context.focal_nodes = ["fn_withdraw"]
    context.patterns = []

    # Create mock subgraph with reentrancy properties
    node = Mock()
    node.id = "fn_withdraw"
    node.properties = {
        "visibility": "external",
        "makes_external_call": True,
        "writes_state": True,
        "state_write_after_external_call": True,
        "has_reentrancy_guard": False,
    }

    context.subgraph = Mock()
    context.subgraph.nodes = {"fn_withdraw": node}

    return context


@pytest.fixture
def access_control_context():
    """Context for access control vulnerability."""
    context = Mock()
    context.focal_nodes = ["fn_setOwner"]
    context.patterns = []

    # Create mock subgraph with access control issues
    node = Mock()
    node.id = "fn_setOwner"
    node.properties = {
        "visibility": "public",
        "writes_privileged_state": True,
        "has_access_gate": False,
    }

    context.subgraph = Mock()
    context.subgraph.nodes = {"fn_setOwner": node}

    return context


@pytest.fixture
def safe_context():
    """Context for safe function."""
    context = Mock()
    context.focal_nodes = ["fn_safe"]
    context.patterns = []

    # Create mock subgraph with safe properties
    node = Mock()
    node.id = "fn_safe"
    node.properties = {
        "visibility": "external",
        "has_access_gate": True,
        "has_reentrancy_guard": True,
    }

    context.subgraph = Mock()
    context.subgraph.nodes = {"fn_safe": node}

    return context


# Enum Tests


class TestEnums:
    """Test enum definitions."""

    def test_attack_categories(self):
        """Test attack category enum."""
        assert AttackCategory.STATE_MANIPULATION
        assert AttackCategory.ACCESS_BYPASS
        assert AttackCategory.ECONOMIC
        assert AttackCategory.DATA_INTEGRITY
        assert AttackCategory.DENIAL_OF_SERVICE
        assert AttackCategory.CRYPTOGRAPHIC

    def test_attack_feasibility(self):
        """Test attack feasibility enum."""
        assert AttackFeasibility.TRIVIAL
        assert AttackFeasibility.LOW
        assert AttackFeasibility.MEDIUM
        assert AttackFeasibility.HIGH

    def test_economic_impact(self):
        """Test economic impact enum."""
        assert EconomicImpact.NEGLIGIBLE
        assert EconomicImpact.LOW
        assert EconomicImpact.MEDIUM
        assert EconomicImpact.HIGH
        assert EconomicImpact.CRITICAL


# Dataclass Tests


class TestDataclasses:
    """Test dataclass functionality."""

    def test_attack_prerequisite_creation(self):
        """Test creating attack prerequisite."""
        prereq = AttackPrerequisite(
            condition="Function is public",
            satisfied=True,
            evidence=["fn_1"],
        )

        assert prereq.condition == "Function is public"
        assert prereq.satisfied is True
        assert prereq.evidence == ["fn_1"]

    def test_attack_step_creation(self):
        """Test creating attack step."""
        step = AttackStep(
            step_number=1,
            action="Call withdraw",
            effect="Reentrancy triggered",
            code_location="fn_withdraw",
        )

        assert step.step_number == 1
        assert step.action == "Call withdraw"
        assert step.effect == "Reentrancy triggered"
        assert step.code_location == "fn_withdraw"

    def test_economic_analysis_creation(self):
        """Test creating economic analysis."""
        econ = EconomicAnalysis(
            potential_gain=100.0,
            capital_required=10.0,
            impact_level=EconomicImpact.HIGH,
        )

        assert econ.potential_gain == 100.0
        assert econ.capital_required == 10.0
        assert econ.impact_level == EconomicImpact.HIGH

    def test_attack_construction_creation(self):
        """Test creating attack construction."""
        attack = AttackConstruction(
            category=AttackCategory.STATE_MANIPULATION,
            target_nodes=["fn_1"],
            preconditions=[],
            attack_steps=[],
            postconditions=["State corrupted"],
            exploitability_score=0.8,
            feasibility=AttackFeasibility.TRIVIAL,
            economic_analysis=EconomicAnalysis(),
        )

        assert attack.category == AttackCategory.STATE_MANIPULATION
        assert attack.target_nodes == ["fn_1"]
        assert attack.exploitability_score == 0.8
        assert attack.feasibility == AttackFeasibility.TRIVIAL


# ExploitabilityFactors Tests


class TestExploitabilityFactors:
    """Test exploitability scoring."""

    def test_calculate_score_all_max(self):
        """Test score with all factors at maximum."""
        factors = ExploitabilityFactors(
            technical_feasibility=1.0,
            guard_absence=1.0,
            pattern_match_strength=1.0,
            economic_viability=1.0,
            historical_precedent=1.0,
        )

        score = factors.calculate_score()
        assert score == 1.0

    def test_calculate_score_all_min(self):
        """Test score with all factors at minimum."""
        factors = ExploitabilityFactors(
            technical_feasibility=0.0,
            guard_absence=0.0,
            pattern_match_strength=0.0,
            economic_viability=0.0,
            historical_precedent=0.0,
        )

        score = factors.calculate_score()
        assert score == 0.0

    def test_calculate_score_weighted(self):
        """Test weighted scoring formula."""
        factors = ExploitabilityFactors(
            technical_feasibility=1.0,  # 30%
            guard_absence=0.0,  # 25%
            pattern_match_strength=0.0,  # 20%
            economic_viability=0.0,  # 15%
            historical_precedent=0.0,  # 10%
        )

        score = factors.calculate_score()
        assert score == 0.30  # Only technical feasibility contributes

    def test_calculate_score_bounds(self):
        """Test score is clamped to [0, 1]."""
        factors = ExploitabilityFactors(
            technical_feasibility=2.0,  # Over max
            guard_absence=-1.0,  # Under min
        )

        score = factors.calculate_score()
        assert 0.0 <= score <= 1.0


# AttackerAgent Tests


class TestAttackerAgent:
    """Test attacker agent functionality."""

    def test_agent_creation(self):
        """Test creating attacker agent."""
        agent = AttackerAgent(use_llm=False)

        assert agent.use_llm is False
        assert agent.adversarial_kg is None

    def test_agent_creation_with_kg(self):
        """Test creating agent with adversarial KG."""
        mock_kg = Mock()
        agent = AttackerAgent(adversarial_kg=mock_kg, use_llm=False)

        assert agent.adversarial_kg == mock_kg

    def test_analyze_returns_result(self, attacker_agent, reentrancy_context):
        """Test analyze returns AttackerResult."""
        result = attacker_agent.analyze(reentrancy_context)

        assert isinstance(result, AttackerResult)
        assert hasattr(result, "matched")
        assert hasattr(result, "confidence")

    def test_analyze_reentrancy_detection(self, attacker_agent, reentrancy_context):
        """Test detecting reentrancy vulnerability."""
        result = attacker_agent.analyze(reentrancy_context)

        assert result.matched is True
        assert result.confidence > 0.5
        assert result.attack is not None
        assert result.attack.category == AttackCategory.STATE_MANIPULATION

    def test_analyze_access_control_detection(
        self, attacker_agent, access_control_context
    ):
        """Test detecting access control vulnerability."""
        result = attacker_agent.analyze(access_control_context)

        assert result.matched is True
        assert result.confidence > 0.5
        assert result.attack is not None
        assert result.attack.category == AttackCategory.ACCESS_BYPASS

    def test_analyze_safe_function(self, attacker_agent, safe_context):
        """Test analyzing safe function."""
        result = attacker_agent.analyze(safe_context)

        # Should either not match or have low confidence
        if result.matched:
            assert result.confidence < 0.5
        else:
            assert result.confidence == 0.0

    def test_analyze_error_handling(self, attacker_agent):
        """Test error handling in analyze."""
        # Create context that will cause error
        bad_context = Mock()
        bad_context.focal_nodes = None  # Will cause error

        result = attacker_agent.analyze(bad_context)

        assert result.matched is False
        assert "error" in result.metadata


# Strategy Selection Tests


class TestStrategySelection:
    """Test attack strategy selection."""

    def test_select_strategy_from_pattern(self, attacker_agent):
        """Test strategy selection from pattern."""
        context = Mock()
        context.focal_nodes = ["fn_1"]

        # Add reentrancy pattern
        pattern = Mock()
        pattern.id = "reentrancy-classic"
        context.patterns = [pattern]
        context.subgraph = Mock()
        context.subgraph.nodes = {}

        strategy = attacker_agent._select_strategy(context)

        assert strategy == AttackCategory.STATE_MANIPULATION

    def test_select_strategy_from_properties(self, attacker_agent, reentrancy_context):
        """Test strategy selection from node properties."""
        reentrancy_context.patterns = []  # No patterns

        strategy = attacker_agent._select_strategy(reentrancy_context)

        assert strategy == AttackCategory.STATE_MANIPULATION

    def test_select_strategy_access_control(
        self, attacker_agent, access_control_context
    ):
        """Test selecting access bypass strategy."""
        access_control_context.patterns = []

        strategy = attacker_agent._select_strategy(access_control_context)

        assert strategy == AttackCategory.ACCESS_BYPASS

    def test_select_strategy_default(self, attacker_agent):
        """Test default strategy selection."""
        context = Mock()
        context.focal_nodes = []
        context.patterns = []
        context.subgraph = Mock()
        context.subgraph.nodes = {}

        strategy = attacker_agent._select_strategy(context)

        # Should default to state manipulation
        assert strategy == AttackCategory.STATE_MANIPULATION


# Attack Construction Tests


class TestAttackConstruction:
    """Test attack construction methods."""

    def test_construct_reentrancy_attack(self, attacker_agent, reentrancy_context):
        """Test constructing reentrancy attack."""
        attack = attacker_agent._construct_state_manipulation(reentrancy_context)

        assert attack is not None
        assert attack.category == AttackCategory.STATE_MANIPULATION
        assert len(attack.preconditions) > 0
        assert len(attack.attack_steps) > 0
        assert attack.exploitability_score > 0.0

    def test_construct_access_bypass_attack(
        self, attacker_agent, access_control_context
    ):
        """Test constructing access bypass attack."""
        attack = attacker_agent._construct_access_bypass(access_control_context)

        assert attack is not None
        assert attack.category == AttackCategory.ACCESS_BYPASS
        assert len(attack.preconditions) > 0
        assert len(attack.attack_steps) > 0

    def test_attack_has_preconditions(self, attacker_agent, reentrancy_context):
        """Test attack includes preconditions."""
        attack = attacker_agent._construct_state_manipulation(reentrancy_context)

        assert attack is not None
        assert len(attack.preconditions) > 0
        for prereq in attack.preconditions:
            assert isinstance(prereq, AttackPrerequisite)
            assert prereq.satisfied is True

    def test_attack_has_steps(self, attacker_agent, reentrancy_context):
        """Test attack includes steps."""
        attack = attacker_agent._construct_state_manipulation(reentrancy_context)

        assert attack is not None
        assert len(attack.attack_steps) > 0
        for step in attack.attack_steps:
            assert isinstance(step, AttackStep)
            assert step.step_number > 0

    def test_attack_has_exploitability_score(
        self, attacker_agent, reentrancy_context
    ):
        """Test attack has exploitability score."""
        attack = attacker_agent._construct_state_manipulation(reentrancy_context)

        assert attack is not None
        assert 0.0 <= attack.exploitability_score <= 1.0

    def test_attack_with_guards_has_blocking_factors(self, attacker_agent):
        """Test attack with guards includes blocking factors."""
        context = Mock()
        context.focal_nodes = ["fn_1"]
        context.patterns = []

        node = Mock()
        node.id = "fn_1"
        node.properties = {
            "makes_external_call": True,
            "writes_state": True,
            "state_write_after_external_call": True,
            "has_reentrancy_guard": True,  # Guard present
        }

        context.subgraph = Mock()
        context.subgraph.nodes = {"fn_1": node}

        attack = attacker_agent._construct_state_manipulation(context)

        assert attack is not None
        assert len(attack.blocking_factors) > 0
        assert any("guard" in factor.lower() for factor in attack.blocking_factors)


# Integration Tests


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_end_to_end_reentrancy_detection(
        self, attacker_agent, reentrancy_context
    ):
        """Test end-to-end reentrancy detection."""
        result = attacker_agent.analyze(reentrancy_context)

        assert result.matched is True
        assert result.attack is not None
        assert result.attack.category == AttackCategory.STATE_MANIPULATION
        assert result.attack.exploitability_score > 0.5
        assert len(result.attack.preconditions) >= 2  # External call + state write
        assert len(result.attack.attack_steps) >= 2  # Call + reenter
        assert result.confidence == result.attack.exploitability_score

    def test_end_to_end_access_control_detection(
        self, attacker_agent, access_control_context
    ):
        """Test end-to-end access control detection."""
        result = attacker_agent.analyze(access_control_context)

        assert result.matched is True
        assert result.attack is not None
        assert result.attack.category == AttackCategory.ACCESS_BYPASS
        assert result.attack.exploitability_score > 0.5
        assert result.attack.feasibility in [
            AttackFeasibility.TRIVIAL,
            AttackFeasibility.LOW,
        ]

    def test_metadata_includes_strategy(self, attacker_agent, reentrancy_context):
        """Test result metadata includes strategy."""
        result = attacker_agent.analyze(reentrancy_context)

        assert "strategy" in result.metadata
        assert result.metadata["strategy"] == AttackCategory.STATE_MANIPULATION.value

    def test_metadata_includes_feasibility(self, attacker_agent, reentrancy_context):
        """Test result metadata includes feasibility."""
        result = attacker_agent.analyze(reentrancy_context)

        assert "feasibility" in result.metadata

    def test_historical_exploits_included(self, attacker_agent, reentrancy_context):
        """Test historical exploits are included."""
        result = attacker_agent.analyze(reentrancy_context)

        assert result.attack is not None
        assert len(result.attack.historical_exploits) > 0


# Success Criteria Tests


class TestSuccessCriteria:
    """Validate P2-T2 success criteria."""

    def test_attack_construction_implemented(self, attacker_agent):
        """Attack construction should be implemented."""
        # Verify all attack categories can be constructed
        context = Mock()
        context.focal_nodes = ["fn_1"]
        context.patterns = []
        context.subgraph = Mock()
        context.subgraph.nodes = {}

        for category in [
            AttackCategory.STATE_MANIPULATION,
            AttackCategory.ACCESS_BYPASS,
            AttackCategory.ECONOMIC,
            AttackCategory.DENIAL_OF_SERVICE,
        ]:
            attack = attacker_agent._construct_attack(context, category)
            # May return None if not applicable, but method should work
            assert attack is None or isinstance(attack, AttackConstruction)

    def test_exploitability_scoring_working(self):
        """Exploitability scoring should work."""
        factors = ExploitabilityFactors(
            technical_feasibility=0.8,
            guard_absence=0.7,
            pattern_match_strength=0.9,
            economic_viability=0.6,
            historical_precedent=0.5,
        )

        score = factors.calculate_score()

        # Should be weighted average
        expected = 0.8 * 0.30 + 0.7 * 0.25 + 0.9 * 0.20 + 0.6 * 0.15 + 0.5 * 0.10
        assert abs(score - expected) < 0.01

    def test_strategy_selection_working(self, attacker_agent):
        """Strategy selection should work for all patterns."""
        context = Mock()
        context.focal_nodes = ["fn_1"]
        context.subgraph = Mock()
        context.subgraph.nodes = {}

        # Test pattern-based selection
        patterns = [
            ("reentrancy-classic", AttackCategory.STATE_MANIPULATION),
            ("access-control-missing", AttackCategory.ACCESS_BYPASS),
            ("oracle-manipulation", AttackCategory.ECONOMIC),
            ("dos-unbounded-loop", AttackCategory.DENIAL_OF_SERVICE),
        ]

        for pattern_id, expected_category in patterns:
            pattern = Mock()
            pattern.id = pattern_id
            context.patterns = [pattern]

            strategy = attacker_agent._select_strategy(context)
            assert strategy == expected_category

    def test_attack_steps_generated(self, attacker_agent, reentrancy_context):
        """Attack steps should be generated."""
        result = attacker_agent.analyze(reentrancy_context)

        assert result.attack is not None
        assert len(result.attack.attack_steps) > 0

        # Validate step structure
        for step in result.attack.attack_steps:
            assert step.step_number > 0
            assert step.action
            assert step.effect
