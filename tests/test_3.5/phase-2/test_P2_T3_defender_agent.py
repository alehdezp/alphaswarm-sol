"""
Tests for P2-T3: Defender Agent

Tests guard detection, spec compliance, and rebuttal generation.
"""

import pytest
from unittest.mock import Mock

from alphaswarm_sol.agents.defender import (
    DefenseType,
    RebuttalStrategy,
    GuardInfo,
    Rebuttal,
    DefenseArgument,
    DefenderAgent,
    DefenderResult,
)
from alphaswarm_sol.agents.attacker import (
    AttackCategory,
    AttackConstruction,
    AttackPrerequisite,
    AttackStep,
    AttackerResult,
)


# Test Fixtures


@pytest.fixture
def defender_agent():
    """Create defender agent without LLM."""
    return DefenderAgent(use_llm=False)


@pytest.fixture
def guarded_context():
    """Context for function with reentrancy guard."""
    context = Mock()
    context.focal_nodes = ["fn_withdraw"]
    context.specs = []
    context.upstream_results = []

    node = Mock()
    node.id = "fn_withdraw"
    node.label = "withdraw"
    node.properties = {
        "has_reentrancy_guard": True,
        "has_access_gate": True,
        "modifiers": ["nonReentrant", "onlyOwner"],
    }

    context.subgraph = Mock()
    context.subgraph.nodes = {"fn_withdraw": node}

    return context


@pytest.fixture
def cei_context():
    """Context for function following CEI pattern."""
    context = Mock()
    context.focal_nodes = ["fn_safe"]
    context.specs = []
    context.upstream_results = []

    node = Mock()
    node.id = "fn_safe"
    node.label = "safeSend"
    node.properties = {
        "behavioral_signature": "R:bal→W:bal→X:out",  # CEI pattern
        "has_reentrancy_guard": False,
    }

    context.subgraph = Mock()
    context.subgraph.nodes = {"fn_safe": node}

    return context


@pytest.fixture
def vulnerable_context():
    """Context for vulnerable function."""
    context = Mock()
    context.focal_nodes = ["fn_vulnerable"]
    context.specs = []
    context.upstream_results = []

    node = Mock()
    node.id = "fn_vulnerable"
    node.label = "vulnerable"
    node.properties = {
        "has_reentrancy_guard": False,
        "has_access_gate": False,
        "behavioral_signature": "R:bal→X:out→W:bal",  # Vulnerable
    }

    context.subgraph = Mock()
    context.subgraph.nodes = {"fn_vulnerable": node}

    return context


@pytest.fixture
def attack_on_guarded():
    """Attacker result claiming reentrancy on guarded function."""
    attack = AttackConstruction(
        category=AttackCategory.STATE_MANIPULATION,
        target_nodes=["fn_withdraw"],
        preconditions=[
            AttackPrerequisite(
                condition="Function makes external call",
                satisfied=True,
                evidence=["fn_withdraw"],
            ),
            AttackPrerequisite(
                condition="No reentrancy guard",
                satisfied=False,  # Actually false!
                evidence=[],
            ),
        ],
        attack_steps=[
            AttackStep(
                step_number=1,
                action="Call function",
                effect="External call made",
            )
        ],
        postconditions=["Funds drained"],
        exploitability_score=0.8,
        feasibility=Mock(),
        economic_analysis=Mock(),
    )
    attack.id = "attack_reentrancy_001"

    return AttackerResult(
        matched=True,
        confidence=0.8,
        attack=attack,
    )


# Enum Tests


class TestEnums:
    """Test enum definitions."""

    def test_defense_types(self):
        """Test defense type enum."""
        assert DefenseType.GUARD_PRESENT
        assert DefenseType.INVARIANT_PRESERVED
        assert DefenseType.SPEC_COMPLIANT
        assert DefenseType.PRECONDITION_UNSATISFIABLE
        assert DefenseType.CEI_PATTERN
        assert DefenseType.SAFE_LIBRARY

    def test_rebuttal_strategies(self):
        """Test rebuttal strategy enum."""
        assert RebuttalStrategy.GUARD_BLOCKS
        assert RebuttalStrategy.PRECONDITION_FALSE
        assert RebuttalStrategy.INVARIANT_MAINTAINED
        assert RebuttalStrategy.SPEC_REQUIRES_SAFETY
        assert RebuttalStrategy.EXECUTION_ORDER


# Dataclass Tests


class TestDataclasses:
    """Test dataclass functionality."""

    def test_guard_info_creation(self):
        """Test creating guard info."""
        guard = GuardInfo(
            guard_type="reentrancy_guard",
            name="nonReentrant",
            strength=0.95,
            evidence=["Modifier present"],
            blocks_attacks=["reentrancy_classic"],
        )

        assert guard.guard_type == "reentrancy_guard"
        assert guard.name == "nonReentrant"
        assert guard.strength == 0.95

    def test_rebuttal_creation(self):
        """Test creating rebuttal."""
        rebuttal = Rebuttal(
            attack_id="attack_001",
            attack_description="Reentrancy",
            strategy=RebuttalStrategy.GUARD_BLOCKS,
            claim="Blocked by guard",
            evidence=["nonReentrant"],
            strength=0.95,
        )

        assert rebuttal.attack_id == "attack_001"
        assert rebuttal.strategy == RebuttalStrategy.GUARD_BLOCKS

    def test_defense_argument_creation(self):
        """Test creating defense argument."""
        defense = DefenseArgument(
            id="defense_001",
            claim="Function is protected",
            defense_type=DefenseType.GUARD_PRESENT,
            strength=0.95,
        )

        assert defense.id == "defense_001"
        assert defense.defense_type == DefenseType.GUARD_PRESENT
        assert defense.strength == 0.95


# DefenderAgent Tests


class TestDefenderAgent:
    """Test defender agent functionality."""

    def test_agent_creation(self):
        """Test creating defender agent."""
        agent = DefenderAgent(use_llm=False)

        assert agent.use_llm is False
        assert agent.domain_kg is None

    def test_agent_creation_with_kg(self):
        """Test creating agent with domain KG."""
        mock_kg = Mock()
        agent = DefenderAgent(domain_kg=mock_kg, use_llm=False)

        assert agent.domain_kg == mock_kg

    def test_analyze_returns_result(self, defender_agent, guarded_context):
        """Test analyze returns DefenderResult."""
        result = defender_agent.analyze(guarded_context)

        assert isinstance(result, DefenderResult)
        assert hasattr(result, "matched")
        assert hasattr(result, "confidence")
        assert hasattr(result, "defenses")

    def test_analyze_detects_reentrancy_guard(self, defender_agent, guarded_context):
        """Test detecting reentrancy guard."""
        result = defender_agent.analyze(guarded_context)

        assert result.matched is True
        guard_defenses = [
            d for d in result.defenses if d.defense_type == DefenseType.GUARD_PRESENT
        ]
        assert len(guard_defenses) > 0

        # Check for reentrancy guard specifically
        reentrancy_guards = [
            d
            for d in guard_defenses
            if any(g.guard_type == "reentrancy_guard" for g in d.guards_identified)
        ]
        assert len(reentrancy_guards) > 0
        assert reentrancy_guards[0].strength >= 0.9

    def test_analyze_detects_access_control(self, defender_agent, guarded_context):
        """Test detecting access control."""
        result = defender_agent.analyze(guarded_context)

        guard_defenses = [
            d for d in result.defenses if d.defense_type == DefenseType.GUARD_PRESENT
        ]

        # Check for access control guard
        access_guards = [
            d
            for d in guard_defenses
            if any(
                g.guard_type in ["only_owner", "role_based"]
                for g in d.guards_identified
            )
        ]
        assert len(access_guards) > 0

    def test_analyze_detects_cei_pattern(self, defender_agent, cei_context):
        """Test detecting CEI pattern."""
        result = defender_agent.analyze(cei_context)

        cei_defenses = [
            d for d in result.defenses if d.defense_type == DefenseType.CEI_PATTERN
        ]
        assert len(cei_defenses) > 0
        assert cei_defenses[0].strength >= 0.7

    def test_analyze_vulnerable_has_low_confidence(
        self, defender_agent, vulnerable_context
    ):
        """Test vulnerable function has low defense confidence."""
        result = defender_agent.analyze(vulnerable_context)

        # Should have few or no defenses
        if result.matched:
            assert result.confidence < 0.5
        else:
            assert result.confidence == 0.0

    def test_analyze_error_handling(self, defender_agent):
        """Test error handling in analyze."""
        bad_context = Mock()
        bad_context.focal_nodes = None  # Will cause error

        result = defender_agent.analyze(bad_context)

        assert result.matched is False
        assert "error" in result.metadata


# Guard Analysis Tests


class TestGuardAnalysis:
    """Test guard detection methods."""

    def test_guard_strengths_defined(self):
        """Test guard strengths are defined."""
        agent = DefenderAgent()

        assert "reentrancy_guard" in agent.GUARD_STRENGTHS
        assert agent.GUARD_STRENGTHS["reentrancy_guard"] == 0.95
        assert agent.GUARD_STRENGTHS["only_owner"] == 0.85
        assert agent.GUARD_STRENGTHS["cei_pattern"] == 0.80

    def test_guard_protections_defined(self):
        """Test guard protections mapping."""
        agent = DefenderAgent()

        assert "reentrancy_guard" in agent.GUARD_PROTECTIONS
        assert "reentrancy_classic" in agent.GUARD_PROTECTIONS["reentrancy_guard"]
        assert "unauthorized_access" in agent.GUARD_PROTECTIONS["only_owner"]

    def test_follows_cei_pattern_true(self, defender_agent):
        """Test CEI pattern detection - positive case."""
        node = Mock()
        node.properties = {"behavioral_signature": "R:bal→W:bal→X:out"}

        assert defender_agent._follows_cei_pattern(node) is True

    def test_follows_cei_pattern_false(self, defender_agent):
        """Test CEI pattern detection - negative case."""
        node = Mock()
        node.properties = {"behavioral_signature": "R:bal→X:out→W:bal"}

        assert defender_agent._follows_cei_pattern(node) is False

    def test_follows_cei_pattern_no_signature(self, defender_agent):
        """Test CEI pattern with no signature."""
        node = Mock()
        node.properties = {}

        assert defender_agent._follows_cei_pattern(node) is False

    def test_uses_pull_pattern(self, defender_agent):
        """Test pull payment pattern detection."""
        node = Mock()
        node.label = "withdraw"
        node.properties = {"reads_user_balance": True}

        assert defender_agent._uses_pull_pattern(node) is True

    def test_uses_pull_pattern_negative(self, defender_agent):
        """Test pull pattern - negative case."""
        node = Mock()
        node.label = "deposit"
        node.properties = {}

        assert defender_agent._uses_pull_pattern(node) is False


# Rebuttal Generation Tests


class TestRebuttalGeneration:
    """Test rebuttal generation methods."""

    def test_generate_rebuttals_with_attacker_result(
        self, defender_agent, attack_on_guarded, guarded_context
    ):
        """Test generating rebuttals to attacker claims."""
        guarded_context.upstream_results = [attack_on_guarded]

        result = defender_agent.analyze(guarded_context)

        rebuttals = [d for d in result.defenses if d.rebuts_attack]
        assert len(rebuttals) > 0

    def test_rebuttal_identifies_blocking_guards(
        self, defender_agent, attack_on_guarded, guarded_context
    ):
        """Test rebuttal identifies blocking guards."""
        guarded_context.upstream_results = [attack_on_guarded]

        result = defender_agent.analyze(guarded_context)

        rebuttals = [d for d in result.defenses if d.rebuts_attack]
        if rebuttals:
            assert len(rebuttals[0].guards_identified) > 0

    def test_rebuttal_has_high_strength(
        self, defender_agent, attack_on_guarded, guarded_context
    ):
        """Test rebuttal on protected function has high strength."""
        guarded_context.upstream_results = [attack_on_guarded]

        result = defender_agent.analyze(guarded_context)

        rebuttals = [d for d in result.defenses if d.rebuts_attack]
        if rebuttals:
            assert rebuttals[0].strength > 0.7

    def test_find_unsatisfiable_preconditions(self, defender_agent):
        """Test finding unsatisfiable preconditions."""
        node = Mock()
        node.properties = {"has_reentrancy_guard": True}

        attack = Mock()
        attack.preconditions = [
            Mock(condition="No reentrancy guard"),
            Mock(condition="Function is public"),
        ]

        unsatisfiable = defender_agent._find_unsatisfiable_preconditions(node, attack)

        assert len(unsatisfiable) > 0
        assert "No reentrancy guard" in unsatisfiable[0]

    def test_find_blocking_guards(self, defender_agent):
        """Test finding blocking guards."""
        node = Mock()
        node.properties = {"has_reentrancy_guard": True}

        attack = Mock()
        attack.category = AttackCategory.STATE_MANIPULATION

        blocking = defender_agent._find_blocking_guards(node, attack)

        assert len(blocking) > 0
        assert blocking[0].guard_type == "reentrancy_guard"

    def test_has_guard_checks(self, defender_agent):
        """Test has_guard method for different guard types."""
        node = Mock()
        node.properties = {
            "has_reentrancy_guard": True,
            "has_access_gate": True,
            "uses_safe_erc20": False,
        }

        assert defender_agent._has_guard(node, "reentrancy_guard") is True
        assert defender_agent._has_guard(node, "only_owner") is True
        assert defender_agent._has_guard(node, "safe_erc20") is False


# Integration Tests


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_end_to_end_protected_function(self, defender_agent, guarded_context):
        """Test end-to-end analysis of protected function."""
        result = defender_agent.analyze(guarded_context)

        assert result.matched is True
        assert result.confidence > 0.8
        assert len(result.defenses) >= 2  # Reentrancy + access control
        assert result.metadata["guard_count"] >= 2

    def test_end_to_end_with_attacker_rebuttal(
        self, defender_agent, attack_on_guarded, guarded_context
    ):
        """Test end-to-end with attacker result."""
        guarded_context.upstream_results = [attack_on_guarded]

        result = defender_agent.analyze(guarded_context)

        assert result.matched is True
        assert result.metadata["rebuttal_count"] > 0

        # Should have both guards and rebuttals
        guards = [
            d for d in result.defenses if d.defense_type == DefenseType.GUARD_PRESENT
        ]
        rebuttals = [d for d in result.defenses if d.rebuts_attack]

        assert len(guards) > 0
        assert len(rebuttals) > 0

    def test_confidence_calculation_rebuttals(
        self, defender_agent, attack_on_guarded, guarded_context
    ):
        """Test confidence calculation with rebuttals."""
        guarded_context.upstream_results = [attack_on_guarded]

        result = defender_agent.analyze(guarded_context)

        # Confidence should be weighted: 60% rebuttals, 40% defenses
        assert 0.0 <= result.confidence <= 1.0

    def test_summary_generation(self, defender_agent, guarded_context):
        """Test summary generation."""
        result = defender_agent.analyze(guarded_context)

        assert "Defense Summary" in result.summary
        assert "Guards" in result.summary or len(result.defenses) == 0

    def test_multiple_focal_nodes(self, defender_agent):
        """Test analyzing multiple focal nodes."""
        context = Mock()
        context.focal_nodes = ["fn_1", "fn_2"]
        context.specs = []
        context.upstream_results = []

        node1 = Mock()
        node1.id = "fn_1"
        node1.properties = {"has_reentrancy_guard": True}

        node2 = Mock()
        node2.id = "fn_2"
        node2.properties = {"has_access_gate": True}

        context.subgraph = Mock()
        context.subgraph.nodes = {"fn_1": node1, "fn_2": node2}

        result = defender_agent.analyze(context)

        assert result.matched is True
        # Should have defenses for both nodes
        assert len(result.defenses) >= 2


# Success Criteria Tests


class TestSuccessCriteria:
    """Validate P2-T3 success criteria."""

    def test_guard_detection_implemented(self, defender_agent, guarded_context):
        """Guard detection should be implemented."""
        result = defender_agent.analyze(guarded_context)

        guard_types = set()
        for defense in result.defenses:
            if defense.defense_type == DefenseType.GUARD_PRESENT:
                for guard in defense.guards_identified:
                    guard_types.add(guard.guard_type)

        # Should detect multiple guard types
        assert len(guard_types) >= 2

    def test_defense_strength_quantified(self, defender_agent, guarded_context):
        """Defense strength should be quantified 0.0-1.0."""
        result = defender_agent.analyze(guarded_context)

        for defense in result.defenses:
            assert 0.0 <= defense.strength <= 1.0

        assert 0.0 <= result.confidence <= 1.0

    def test_rebuttal_generation_working(
        self, defender_agent, attack_on_guarded, guarded_context
    ):
        """Rebuttal generation should work."""
        guarded_context.upstream_results = [attack_on_guarded]

        result = defender_agent.analyze(guarded_context)

        rebuttals = [d for d in result.defenses if d.rebuts_attack]
        assert len(rebuttals) > 0

        # Rebuttal should have strategy
        assert rebuttals[0].rebuttal is not None
        assert isinstance(rebuttals[0].rebuttal.strategy, RebuttalStrategy)

    def test_cei_pattern_detection_working(self, defender_agent, cei_context):
        """CEI pattern detection should work."""
        result = defender_agent.analyze(cei_context)

        cei_defenses = [
            d for d in result.defenses if d.defense_type == DefenseType.CEI_PATTERN
        ]
        assert len(cei_defenses) > 0

    def test_evidence_included(self, defender_agent, guarded_context):
        """All defenses should include evidence."""
        result = defender_agent.analyze(guarded_context)

        for defense in result.defenses:
            # Should have some form of evidence
            has_evidence = (
                len(defense.evidence) > 0
                or len(defense.guards_identified) > 0
                or len(defense.spec_references) > 0
            )
            assert has_evidence

    def test_strength_reasoning_included(self, defender_agent, guarded_context):
        """All defenses should include strength reasoning."""
        result = defender_agent.analyze(guarded_context)

        for defense in result.defenses:
            assert defense.strength_reasoning != ""
            assert len(defense.strength_factors) > 0
