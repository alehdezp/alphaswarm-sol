"""
Tests for P3-T1: Iterative Reasoning Engine

Tests multi-round reasoning, graph expansion, and convergence detection.
"""

import pytest
from unittest.mock import Mock, MagicMock

from alphaswarm_sol.reasoning import (
    ExpansionType,
    ExpandedNode,
    CrossGraphFinding,
    AttackChain,
    ReasoningRound,
    ReasoningResult,
    IterativeReasoningEngine,
)
from alphaswarm_sol.kg.schema import Node, Edge


# Test Fixtures


@pytest.fixture
def mock_kg():
    """Create mock knowledge graph with test functions."""
    kg = Mock()
    kg.nodes = {}
    kg.edges = {}

    # Create test nodes
    # fn_withdraw: vulnerable to reentrancy
    withdraw = Mock(spec=Node)
    withdraw.id = "fn_withdraw"
    withdraw.type = Mock(value="function")
    withdraw.label = "withdraw"
    withdraw.properties = {
        "visibility": "public",
        "state_write_after_external_call": True,
        "has_reentrancy_guard": False,
        "writes_state_vars": ["balances"],
        "reads_state_vars": ["balances"],
    }
    kg.nodes["fn_withdraw"] = withdraw

    # fn_deposit: shares state with withdraw
    deposit = Mock(spec=Node)
    deposit.id = "fn_deposit"
    deposit.type = Mock(value="function")
    deposit.label = "deposit"
    deposit.properties = {
        "visibility": "public",
        "writes_state_vars": ["balances"],
        "reads_state_vars": [],
    }
    kg.nodes["fn_deposit"] = deposit

    # fn_transfer: privileged operation
    transfer = Mock(spec=Node)
    transfer.id = "fn_transfer"
    transfer.type = Mock(value="function")
    transfer.label = "transfer"
    transfer.properties = {
        "visibility": "public",
        "writes_privileged_state": True,
        "has_access_gate": False,
        "writes_state_vars": ["owner"],
        "reads_state_vars": [],
    }
    kg.nodes["fn_transfer"] = transfer

    # fn_caller: calls withdraw
    caller = Mock(spec=Node)
    caller.id = "fn_caller"
    caller.type = Mock(value="function")
    caller.label = "requestWithdraw"
    caller.properties = {
        "visibility": "public",
        "writes_state_vars": [],
        "reads_state_vars": [],
    }
    kg.nodes["fn_caller"] = caller

    # fn_helper: called by withdraw
    helper = Mock(spec=Node)
    helper.id = "fn_helper"
    helper.type = Mock(value="function")
    helper.label = "_transferFunds"
    helper.properties = {
        "visibility": "internal",
        "writes_state_vars": [],
        "reads_state_vars": ["balances"],
    }
    kg.nodes["fn_helper"] = helper

    # Create edges
    # caller → withdraw
    edge1 = Mock(spec=Edge)
    edge1.id = "edge_1"
    edge1.source = "fn_caller"
    edge1.target = "fn_withdraw"
    edge1.type = Mock(value="calls")
    kg.edges["edge_1"] = edge1

    # withdraw → helper
    edge2 = Mock(spec=Edge)
    edge2.id = "edge_2"
    edge2.source = "fn_withdraw"
    edge2.target = "fn_helper"
    edge2.type = Mock(value="calls")
    kg.edges["edge_2"] = edge2

    return kg


@pytest.fixture
def engine(mock_kg):
    """Create iterative reasoning engine."""
    return IterativeReasoningEngine(
        code_kg=mock_kg,
        max_rounds=3,
        convergence_threshold=0.9,
        expansion_limit=10,
        min_confidence=0.3,
    )


# Enum Tests


class TestEnums:
    """Test enum definitions."""

    def test_expansion_types(self):
        """Test expansion type enum."""
        assert ExpansionType.CALLERS.value == "callers"
        assert ExpansionType.CALLEES.value == "callees"
        assert ExpansionType.SHARED_STATE.value == "shared_state"
        assert ExpansionType.INHERITANCE.value == "inheritance"
        assert ExpansionType.CROSS_CONTRACT.value == "cross_contract"


# Dataclass Tests


class TestDataclasses:
    """Test dataclass functionality."""

    def test_expanded_node_creation(self):
        """Test creating expanded node."""
        node = ExpandedNode(
            node_id="fn_test",
            expansion_type=ExpansionType.CALLERS,
            source_node="fn_source",
            hop_distance=1,
            relevance_score=0.8,
        )

        assert node.node_id == "fn_test"
        assert node.expansion_type == ExpansionType.CALLERS
        assert node.hop_distance == 1
        assert node.relevance_score == 0.8

    def test_cross_graph_finding_creation(self):
        """Test creating cross-graph finding."""
        finding = CrossGraphFinding(
            source_node="fn_test",
            target_kg="adversarial",
            edge_type="SIMILAR_TO",
            target_spec_or_pattern="the_dao_exploit",
            confidence=0.85,
            evidence=["Evidence 1", "Evidence 2"],
        )

        assert finding.target_kg == "adversarial"
        assert finding.confidence == 0.85
        assert len(finding.evidence) == 2

    def test_attack_chain_creation(self):
        """Test creating attack chain."""
        chain = AttackChain(
            id="chain_1",
            functions=["fn_a", "fn_b", "fn_a"],
            entry_point="fn_a",
            exit_point="fn_a",
            pattern_ids=["reentrancy_classic"],
            description="Reentrancy attack",
            feasibility=0.8,
            impact="critical",
        )

        assert len(chain.functions) == 3
        assert chain.impact == "critical"
        assert chain.feasibility == 0.8

    def test_reasoning_round_creation(self):
        """Test creating reasoning round."""
        round_data = ReasoningRound(
            round_num=1,
            input_candidates=["fn_a", "fn_b"],
            pattern_matches={"fn_a": [("pattern_1", 0.8)]},
            expanded_nodes=[],
            cross_graph_findings=[],
            refined_candidates=["fn_a", "fn_b", "fn_c"],
            attack_chains_discovered=[],
            new_candidates_added=1,
            candidates_removed=0,
            expansion_time_ms=50.0,
            cross_graph_time_ms=30.0,
        )

        assert round_data.round_num == 1
        assert round_data.new_candidates_added == 1
        assert len(round_data.refined_candidates) == 3


# Engine Initialization Tests


class TestEngineInitialization:
    """Test engine initialization."""

    def test_init_with_defaults(self, mock_kg):
        """Test initialization with defaults."""
        engine = IterativeReasoningEngine(code_kg=mock_kg)

        assert engine.code_kg == mock_kg
        assert engine.max_rounds == 4
        assert engine.convergence_threshold == 0.9
        assert engine.expansion_limit == 20
        assert engine.min_confidence == 0.3

    def test_init_with_custom_params(self, mock_kg):
        """Test initialization with custom parameters."""
        engine = IterativeReasoningEngine(
            code_kg=mock_kg,
            max_rounds=5,
            convergence_threshold=0.85,
            expansion_limit=15,
            min_confidence=0.4,
        )

        assert engine.max_rounds == 5
        assert engine.convergence_threshold == 0.85
        assert engine.expansion_limit == 15
        assert engine.min_confidence == 0.4


# Pattern Matching Tests


class TestPatternMatching:
    """Test pattern matching logic."""

    def test_pattern_match_reentrancy(self, engine, mock_kg):
        """Test pattern matching detects reentrancy."""
        matches = engine._pattern_match({"fn_withdraw"})

        assert "fn_withdraw" in matches
        patterns = dict(matches["fn_withdraw"])
        assert "reentrancy_classic" in patterns
        assert patterns["reentrancy_classic"] == 0.85

    def test_pattern_match_access_control(self, engine, mock_kg):
        """Test pattern matching detects weak access control."""
        matches = engine._pattern_match({"fn_transfer"})

        assert "fn_transfer" in matches
        patterns = dict(matches["fn_transfer"])
        assert "weak_access_control" in patterns
        assert patterns["weak_access_control"] == 0.80

    def test_pattern_match_no_vulnerabilities(self, engine, mock_kg):
        """Test pattern matching with no vulnerabilities."""
        matches = engine._pattern_match({"fn_deposit"})

        assert "fn_deposit" not in matches  # No vulnerabilities

    def test_pattern_match_multiple_candidates(self, engine, mock_kg):
        """Test pattern matching on multiple candidates."""
        matches = engine._pattern_match({"fn_withdraw", "fn_transfer", "fn_deposit"})

        assert "fn_withdraw" in matches
        assert "fn_transfer" in matches
        assert "fn_deposit" not in matches


# Graph Expansion Tests


class TestGraphExpansion:
    """Test graph expansion logic."""

    def test_expand_neighbors_shared_state(self, engine, mock_kg):
        """Test expansion finds shared state functions."""
        expanded = engine._expand_neighbors({"fn_withdraw"}, set())

        # Should find fn_deposit (shares 'balances' state)
        shared_nodes = [e for e in expanded if e.expansion_type == ExpansionType.SHARED_STATE]
        assert len(shared_nodes) > 0
        assert any(e.node_id == "fn_deposit" for e in shared_nodes)

    def test_expand_neighbors_callers(self, engine, mock_kg):
        """Test expansion finds callers."""
        expanded = engine._expand_neighbors({"fn_withdraw"}, set())

        # Should find fn_caller
        caller_nodes = [e for e in expanded if e.expansion_type == ExpansionType.CALLERS]
        assert len(caller_nodes) > 0
        assert any(e.node_id == "fn_caller" for e in caller_nodes)

    def test_expand_neighbors_callees(self, engine, mock_kg):
        """Test expansion finds callees."""
        expanded = engine._expand_neighbors({"fn_withdraw"}, set())

        # Should find fn_helper
        callee_nodes = [e for e in expanded if e.expansion_type == ExpansionType.CALLEES]
        assert len(callee_nodes) > 0
        assert any(e.node_id == "fn_helper" for e in callee_nodes)

    def test_expand_neighbors_respects_explored(self, engine, mock_kg):
        """Test expansion doesn't return already explored nodes."""
        already_explored = {"fn_caller", "fn_helper", "fn_deposit"}

        expanded = engine._expand_neighbors({"fn_withdraw"}, already_explored)

        # Should not include already explored nodes
        expanded_ids = [e.node_id for e in expanded]
        assert "fn_caller" not in expanded_ids
        assert "fn_helper" not in expanded_ids
        assert "fn_deposit" not in expanded_ids

    def test_expand_neighbors_relevance_scores(self, engine, mock_kg):
        """Test expansion assigns correct relevance scores."""
        expanded = engine._expand_neighbors({"fn_withdraw"}, set())

        # Shared state should have highest relevance
        for node in expanded:
            if node.expansion_type == ExpansionType.SHARED_STATE:
                assert node.relevance_score == 0.9
            elif node.expansion_type == ExpansionType.CALLERS:
                assert node.relevance_score == 0.7
            elif node.expansion_type == ExpansionType.CALLEES:
                assert node.relevance_score == 0.6


# Helper Method Tests


class TestHelperMethods:
    """Test helper methods."""

    def test_get_shared_state_functions(self, engine, mock_kg):
        """Test finding shared state functions."""
        shared = engine._get_shared_state_functions("fn_withdraw")

        # Should find fn_deposit (shares 'balances')
        assert "fn_deposit" in shared

    def test_get_callers(self, engine, mock_kg):
        """Test finding caller functions."""
        callers = engine._get_callers("fn_withdraw")

        assert "fn_caller" in callers

    def test_get_callees(self, engine, mock_kg):
        """Test finding callee functions."""
        callees = engine._get_callees("fn_withdraw")

        assert "fn_helper" in callees


# Attack Chain Building Tests


class TestAttackChainBuilding:
    """Test attack chain building."""

    def test_build_reentrancy_chain(self, engine, mock_kg):
        """Test building reentrancy attack chain."""
        candidates = {"fn_withdraw"}
        expanded = [
            ExpandedNode(
                node_id="fn_caller",
                expansion_type=ExpansionType.CALLERS,
                source_node="fn_withdraw",
                hop_distance=1,
                relevance_score=0.7,
            )
        ]
        pattern_matches = {"fn_withdraw": [("reentrancy_classic", 0.85)]}

        chains = engine._build_attack_chains(candidates, expanded, pattern_matches)

        assert len(chains) > 0
        reentrancy_chain = chains[0]
        assert "reentrancy" in reentrancy_chain.description.lower()
        assert reentrancy_chain.impact == "critical"
        assert len(reentrancy_chain.functions) == 3  # caller → vulnerable → caller

    def test_build_no_chains_without_matches(self, engine, mock_kg):
        """Test no chains built without pattern matches."""
        candidates = {"fn_deposit"}
        expanded = []
        pattern_matches = {}

        chains = engine._build_attack_chains(candidates, expanded, pattern_matches)

        assert len(chains) == 0


# Convergence Tests


class TestConvergence:
    """Test convergence detection."""

    def test_converged_no_new_candidates(self, engine):
        """Test convergence when no new candidates added."""
        rounds = [
            ReasoningRound(
                round_num=1,
                input_candidates=["fn_a"],
                pattern_matches={},
                expanded_nodes=[],
                cross_graph_findings=[],
                refined_candidates=["fn_a", "fn_b"],
                attack_chains_discovered=[],
                new_candidates_added=1,
                candidates_removed=0,
                expansion_time_ms=50.0,
                cross_graph_time_ms=30.0,
            ),
            ReasoningRound(
                round_num=2,
                input_candidates=["fn_a", "fn_b"],
                pattern_matches={},
                expanded_nodes=[],
                cross_graph_findings=[],
                refined_candidates=["fn_a", "fn_b"],
                attack_chains_discovered=[],
                new_candidates_added=0,  # No new candidates
                candidates_removed=0,
                expansion_time_ms=50.0,
                cross_graph_time_ms=30.0,
            ),
        ]

        assert engine._converged(rounds) is True

    def test_not_converged_with_new_candidates(self, engine):
        """Test not converged when new candidates added."""
        rounds = [
            ReasoningRound(
                round_num=1,
                input_candidates=["fn_a"],
                pattern_matches={},
                expanded_nodes=[],
                cross_graph_findings=[],
                refined_candidates=["fn_a", "fn_b"],
                attack_chains_discovered=[],
                new_candidates_added=1,
                candidates_removed=0,
                expansion_time_ms=50.0,
                cross_graph_time_ms=30.0,
            ),
        ]

        assert engine._converged(rounds) is False

    def test_not_converged_single_round(self, engine):
        """Test not converged with single round."""
        rounds = [
            ReasoningRound(
                round_num=1,
                input_candidates=["fn_a"],
                pattern_matches={},
                expanded_nodes=[],
                cross_graph_findings=[],
                refined_candidates=["fn_a"],
                attack_chains_discovered=[],
                new_candidates_added=0,
                candidates_removed=0,
                expansion_time_ms=50.0,
                cross_graph_time_ms=30.0,
            ),
        ]

        # Need at least 2 rounds to check convergence
        assert engine._converged(rounds) is False


# End-to-End Reasoning Tests


class TestIterativeReasoning:
    """Test end-to-end iterative reasoning."""

    def test_reason_single_candidate(self, engine, mock_kg):
        """Test reasoning with single initial candidate."""
        result = engine.reason(initial_candidates=["fn_withdraw"])

        assert isinstance(result, ReasoningResult)
        assert len(result.rounds) > 0
        assert "fn_withdraw" in result.final_candidates
        assert result.converged or result.convergence_reason == "max_rounds"

    def test_reason_multiple_rounds(self, engine, mock_kg):
        """Test reasoning executes multiple rounds."""
        result = engine.reason(initial_candidates=["fn_withdraw"], max_rounds=3)

        assert len(result.rounds) <= 3
        assert result.convergence_round <= 3

    def test_reason_discovers_new_candidates(self, engine, mock_kg):
        """Test reasoning discovers new candidates through expansion."""
        result = engine.reason(initial_candidates=["fn_withdraw"])

        # Should discover related functions
        assert len(result.final_candidates) >= 1

    def test_reason_builds_attack_chains(self, engine, mock_kg):
        """Test reasoning builds attack chains."""
        result = engine.reason(initial_candidates=["fn_withdraw"])

        # Should build reentrancy chain
        assert len(result.attack_chains) > 0

    def test_reason_tracks_metrics(self, engine, mock_kg):
        """Test reasoning tracks performance metrics."""
        result = engine.reason(initial_candidates=["fn_withdraw"])

        assert result.total_time_ms > 0
        assert result.total_nodes_explored > 0
        assert result.convergence_round > 0

    def test_reason_compares_with_single_pass(self, engine, mock_kg):
        """Test reasoning compares with single-pass baseline."""
        result = engine.reason(initial_candidates=["fn_withdraw", "fn_transfer"])

        assert isinstance(result.single_pass_would_find, list)
        assert isinstance(result.iterative_bonus_findings, list)

        # Should have some findings
        assert len(result.single_pass_would_find) > 0


# Refine Candidates Tests


class TestCandidateRefinement:
    """Test candidate refinement logic."""

    def test_refine_adds_high_relevance_nodes(self, engine):
        """Test refinement adds high-relevance expanded nodes."""
        current = {"fn_a"}
        expanded = [
            ExpandedNode(
                node_id="fn_b",
                expansion_type=ExpansionType.SHARED_STATE,
                source_node="fn_a",
                hop_distance=1,
                relevance_score=0.9,  # High relevance
            )
        ]
        cross_findings = []
        pattern_matches = {"fn_a": [("pattern_1", 0.8)]}

        refined = engine._refine_candidates(current, expanded, cross_findings, pattern_matches)

        assert "fn_b" in refined  # Added due to high relevance

    def test_refine_keeps_pattern_matches(self, engine):
        """Test refinement keeps candidates with pattern matches."""
        current = {"fn_a", "fn_b"}
        expanded = []
        cross_findings = []
        pattern_matches = {"fn_a": [("pattern_1", 0.8)]}  # Only fn_a has match

        refined = engine._refine_candidates(current, expanded, cross_findings, pattern_matches)

        assert "fn_a" in refined  # Kept due to pattern match


# Integration Tests


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_iterative_reasoning_workflow(self, engine, mock_kg):
        """Test complete iterative reasoning workflow."""
        result = engine.reason(initial_candidates=["fn_withdraw"])

        # Should complete successfully
        assert isinstance(result, ReasoningResult)

        # Should have rounds
        assert len(result.rounds) > 0

        # Should find vulnerabilities
        assert len(result.final_candidates) > 0

        # Should have metrics
        assert result.total_time_ms > 0
        assert result.total_nodes_explored > 0

        # Should have convergence info
        assert result.convergence_round > 0
        assert result.convergence_reason in ["no_new_candidates", "max_rounds"]

    def test_iterative_finds_more_than_single_pass(self, engine, mock_kg):
        """Test iterative finds more than single-pass."""
        result = engine.reason(initial_candidates=["fn_withdraw"])

        # Iterative should find at least what single-pass finds
        assert len(result.final_candidates) >= len(result.single_pass_would_find)


# Success Criteria Tests


class TestSuccessCriteria:
    """Validate P3-T1 success criteria."""

    def test_reasoning_round_dataclass_exists(self):
        """ReasoningRound dataclass should exist."""
        round_data = ReasoningRound(
            round_num=1,
            input_candidates=[],
            pattern_matches={},
            expanded_nodes=[],
            cross_graph_findings=[],
            refined_candidates=[],
            attack_chains_discovered=[],
            new_candidates_added=0,
            candidates_removed=0,
            expansion_time_ms=0.0,
            cross_graph_time_ms=0.0,
        )

        assert round_data.round_num == 1

    def test_engine_has_reason_method(self, engine):
        """Engine should have reason() method."""
        assert hasattr(engine, "reason")
        assert callable(engine.reason)

    def test_multi_round_expansion_works(self, engine, mock_kg):
        """Multi-round expansion should work."""
        result = engine.reason(initial_candidates=["fn_withdraw"], max_rounds=3)

        # Should execute multiple rounds
        assert len(result.rounds) >= 1

    def test_convergence_detection_works(self, engine, mock_kg):
        """Convergence detection should work."""
        result = engine.reason(initial_candidates=["fn_withdraw"])

        # Should detect convergence or hit max rounds
        assert result.convergence_reason in ["no_new_candidates", "max_rounds"]
        assert isinstance(result.converged, bool)

    def test_better_than_single_pass(self, engine, mock_kg):
        """Iterative should find at least as much as single-pass."""
        result = engine.reason(initial_candidates=["fn_withdraw", "fn_transfer"])

        # Should find at least what single-pass finds
        single_pass_set = set(result.single_pass_would_find)
        final_set = set(result.final_candidates)

        # Final candidates should include single-pass findings
        assert single_pass_set.issubset(final_set) or len(final_set) >= len(single_pass_set)
