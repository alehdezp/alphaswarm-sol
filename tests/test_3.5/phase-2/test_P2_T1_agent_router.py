"""
Tests for P2-T1: Agent Router (GLM-Style)

Tests the agent routing with selective context sharing.
"""

import pytest
from typing import List
from unittest.mock import Mock, MagicMock

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node, Edge, Evidence
from alphaswarm_sol.routing import (
    AgentType,
    AgentContext,
    ContextSlicer,
    AgentRouter,
    ChainedResult,
)


# Test Fixtures


@pytest.fixture
def simple_kg():
    """Create simple test knowledge graph."""
    kg = KnowledgeGraph()

    # Contract node
    contract = Node(
        id="contract_1",
        label="TestContract",
        type="Contract",
        properties={},
        evidence=[],
    )
    kg.nodes[contract.id] = contract

    # Function nodes
    fn1 = Node(
        id="fn_1",
        label="withdraw",
        type="Function",
        properties={
            "visibility": "external",
            "has_access_gate": False,
            "semantic_ops": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        },
        evidence=[],
    )
    kg.nodes[fn1.id] = fn1

    fn2 = Node(
        id="fn_2",
        label="deposit",
        type="Function",
        properties={
            "visibility": "external",
            "semantic_ops": ["RECEIVES_VALUE_IN", "WRITES_USER_BALANCE"],
        },
        evidence=[],
    )
    kg.nodes[fn2.id] = fn2

    # Edges
    edge1 = Edge(
        id=f"{contract.id}_DEFINES_{fn1.id}",
        type="DEFINES",
        source=contract.id,
        target=fn1.id,
        evidence=[],
    )
    kg.edges[edge1.id] = edge1

    edge2 = Edge(
        id=f"{contract.id}_DEFINES_{fn2.id}",
        type="DEFINES",
        source=contract.id,
        target=fn2.id,
        evidence=[],
    )
    kg.edges[edge2.id] = edge2

    return kg


@pytest.fixture
def context_slicer(simple_kg):
    """Create context slicer."""
    return ContextSlicer(simple_kg)


@pytest.fixture
def agent_router(simple_kg):
    """Create agent router."""
    return AgentRouter(simple_kg)


# AgentType Tests


class TestAgentType:
    """Test AgentType enum."""

    def test_agent_types_exist(self):
        """Test that all agent types are defined."""
        assert AgentType.CLASSIFIER
        assert AgentType.ATTACKER
        assert AgentType.DEFENDER
        assert AgentType.VERIFIER

    def test_agent_type_values(self):
        """Test agent type values."""
        assert AgentType.CLASSIFIER.value == "classifier"
        assert AgentType.ATTACKER.value == "attacker"
        assert AgentType.DEFENDER.value == "defender"
        assert AgentType.VERIFIER.value == "verifier"


# AgentContext Tests


class TestAgentContext:
    """Test AgentContext functionality."""

    def test_context_creation(self):
        """Test creating agent context."""
        ctx = AgentContext(
            agent_type=AgentType.CLASSIFIER,
            focal_nodes=["fn_1"],
            subgraph=Mock(),
        )

        assert ctx.agent_type == AgentType.CLASSIFIER
        assert ctx.focal_nodes == ["fn_1"]
        assert len(ctx.specs) == 0
        assert len(ctx.patterns) == 0
        assert len(ctx.intents) == 0

    def test_token_estimation(self):
        """Test token estimation."""
        ctx = AgentContext(
            agent_type=AgentType.CLASSIFIER,
            focal_nodes=["fn_1", "fn_2"],
            subgraph=Mock(),
            specs=[Mock(), Mock()],  # 2 specs
            patterns=[Mock()],  # 1 pattern
        )

        tokens = ctx.estimate_tokens()

        # Should have base + focal nodes + specs + patterns
        assert tokens > 100  # At least base tokens
        assert tokens > 200  # Should include specs (2 * 100)

    def test_attacker_context_includes_patterns(self):
        """Test attacker context includes patterns."""
        ctx = AgentContext(
            agent_type=AgentType.ATTACKER,
            focal_nodes=["fn_1"],
            subgraph=Mock(),
            patterns=[Mock(id="reentrancy")],
        )

        assert len(ctx.patterns) == 1
        assert ctx.patterns[0].id == "reentrancy"

    def test_defender_context_includes_specs(self):
        """Test defender context includes specs."""
        ctx = AgentContext(
            agent_type=AgentType.DEFENDER,
            focal_nodes=["fn_1"],
            subgraph=Mock(),
            specs=[Mock(id="erc20_transfer")],
        )

        assert len(ctx.specs) == 1
        assert ctx.specs[0].id == "erc20_transfer"


# ContextSlicer Tests


class TestContextSlicer:
    """Test ContextSlicer functionality."""

    def test_slicer_creation(self, simple_kg):
        """Test creating context slicer."""
        slicer = ContextSlicer(simple_kg)

        assert slicer.code_kg == simple_kg
        assert slicer.domain_kg is None
        assert slicer.adversarial_kg is None

    def test_slice_for_classifier(self, context_slicer):
        """Test slicing for classifier agent."""
        ctx = context_slicer.slice_for_agent(
            AgentType.CLASSIFIER,
            focal_nodes=["fn_1"],
        )

        assert ctx.agent_type == AgentType.CLASSIFIER
        assert ctx.focal_nodes == ["fn_1"]
        assert len(ctx.specs) == 0  # Classifier doesn't need specs
        assert len(ctx.patterns) == 0  # Classifier doesn't need patterns
        assert len(ctx.intents) == 0  # Classifier doesn't need intents

    def test_slice_for_attacker(self, context_slicer):
        """Test slicing for attacker agent."""
        ctx = context_slicer.slice_for_agent(
            AgentType.ATTACKER,
            focal_nodes=["fn_1"],
        )

        assert ctx.agent_type == AgentType.ATTACKER
        assert ctx.focal_nodes == ["fn_1"]
        # Attacker gets richer context

    def test_slice_for_defender(self, context_slicer):
        """Test slicing for defender agent."""
        ctx = context_slicer.slice_for_agent(
            AgentType.DEFENDER,
            focal_nodes=["fn_1"],
        )

        assert ctx.agent_type == AgentType.DEFENDER
        assert ctx.focal_nodes == ["fn_1"]
        # Defender doesn't need patterns
        assert len(ctx.patterns) == 0

    def test_slice_for_verifier(self, context_slicer):
        """Test slicing for verifier agent."""
        ctx = context_slicer.slice_for_agent(
            AgentType.VERIFIER,
            focal_nodes=["fn_1"],
        )

        assert ctx.agent_type == AgentType.VERIFIER
        assert ctx.focal_nodes == ["fn_1"]

    def test_invalid_agent_type_raises(self, context_slicer):
        """Test invalid agent type raises error."""
        with pytest.raises(ValueError, match="Unknown agent type"):
            # Create invalid enum-like object
            class InvalidType:
                value = "invalid"

            context_slicer.slice_for_agent(
                InvalidType(),  # type: ignore
                focal_nodes=["fn_1"],
            )

    def test_token_reduction_vs_baseline(self, context_slicer):
        """Test that slicing reduces tokens vs full context."""
        focal_nodes = ["fn_1", "fn_2"]

        # Create contexts for all agents
        classifier_ctx = context_slicer.slice_for_agent(
            AgentType.CLASSIFIER, focal_nodes
        )
        attacker_ctx = context_slicer.slice_for_agent(
            AgentType.ATTACKER, focal_nodes
        )

        # Sliced tokens
        total_sliced = (
            classifier_ctx.estimate_tokens() + attacker_ctx.estimate_tokens()
        )

        # Baseline (full context per agent)
        baseline_per_agent = len(focal_nodes) * 2000
        baseline_total = baseline_per_agent * 2

        # Should have significant reduction
        reduction = 1 - (total_sliced / baseline_total)
        assert reduction > 0.5  # At least 50% reduction


# AgentRouter Tests


class TestAgentRouter:
    """Test AgentRouter functionality."""

    def test_router_creation(self, simple_kg):
        """Test creating agent router."""
        router = AgentRouter(simple_kg)

        assert router.code_kg == simple_kg
        assert isinstance(router.slicer, ContextSlicer)
        assert len(router.agents) == 0  # No agents registered yet

    def test_register_agent(self, agent_router):
        """Test registering agents."""
        mock_agent = Mock()
        agent_router.register_agent(AgentType.CLASSIFIER, mock_agent)

        assert AgentType.CLASSIFIER in agent_router.agents
        assert agent_router.agents[AgentType.CLASSIFIER] == mock_agent

    def test_route_single_agent(self, agent_router):
        """Test routing to single agent."""
        # Create mock agent
        mock_agent = Mock()
        mock_result = Mock(matched=True, confidence=0.9)
        mock_agent.analyze = Mock(return_value=mock_result)

        agent_router.register_agent(AgentType.CLASSIFIER, mock_agent)

        # Route
        results = agent_router.route(
            focal_nodes=["fn_1"],
            agent_types=[AgentType.CLASSIFIER],
            parallel=False,
        )

        assert AgentType.CLASSIFIER in results
        assert results[AgentType.CLASSIFIER] == mock_result
        mock_agent.analyze.assert_called_once()

    def test_route_multiple_agents(self, agent_router):
        """Test routing to multiple agents."""
        # Create mock agents
        classifier = Mock()
        classifier.analyze = Mock(return_value=Mock(matched=True))

        attacker = Mock()
        attacker.analyze = Mock(return_value=Mock(matched=True))

        agent_router.register_agent(AgentType.CLASSIFIER, classifier)
        agent_router.register_agent(AgentType.ATTACKER, attacker)

        # Route
        results = agent_router.route(
            focal_nodes=["fn_1"],
            parallel=False,
        )

        assert len(results) == 2
        assert AgentType.CLASSIFIER in results
        assert AgentType.ATTACKER in results

    def test_route_parallel_execution(self, agent_router):
        """Test parallel agent execution."""
        # Create mock agents
        classifier = Mock()
        classifier.analyze = Mock(return_value=Mock(matched=True))

        attacker = Mock()
        attacker.analyze = Mock(return_value=Mock(matched=True))

        agent_router.register_agent(AgentType.CLASSIFIER, classifier)
        agent_router.register_agent(AgentType.ATTACKER, attacker)

        # Route with parallel=True
        results = agent_router.route(
            focal_nodes=["fn_1"],
            parallel=True,
        )

        assert len(results) == 2
        # Both agents should have been called
        classifier.analyze.assert_called_once()
        attacker.analyze.assert_called_once()

    def test_route_agent_failure_handling(self, agent_router):
        """Test handling agent failures."""
        # Create failing agent
        failing_agent = Mock()
        failing_agent.analyze = Mock(side_effect=Exception("Agent failed"))

        agent_router.register_agent(AgentType.CLASSIFIER, failing_agent)

        # Route
        results = agent_router.route(
            focal_nodes=["fn_1"],
            agent_types=[AgentType.CLASSIFIER],
            parallel=False,
        )

        # Should have result with error
        assert AgentType.CLASSIFIER in results
        result = results[AgentType.CLASSIFIER]
        assert result.matched is False
        assert "error" in result.metadata


# Chained Routing Tests


class TestChainedRouting:
    """Test chained agent execution."""

    def test_route_with_chaining(self, agent_router):
        """Test routing with chaining."""
        # Create mock agents
        classifier = Mock()
        classifier.analyze = Mock(
            return_value=Mock(matched=True, confidence=0.8)
        )

        attacker = Mock()
        attacker.analyze = Mock(
            return_value=Mock(matched=True, confidence=0.9)
        )

        defender = Mock()
        defender.analyze = Mock(
            return_value=Mock(matched=False, confidence=0.7)
        )

        agent_router.register_agent(AgentType.CLASSIFIER, classifier)
        agent_router.register_agent(AgentType.ATTACKER, attacker)
        agent_router.register_agent(AgentType.DEFENDER, defender)

        # Route with chaining
        result = agent_router.route_with_chaining(focal_nodes=["fn_1"])

        assert isinstance(result, ChainedResult)
        assert len(result.stages) == 3
        assert AgentType.CLASSIFIER in result.stages
        assert AgentType.ATTACKER in result.stages
        assert AgentType.DEFENDER in result.stages

    def test_chained_result_final_verdict(self):
        """Test ChainedResult final verdict."""
        # All matched
        result1 = ChainedResult(
            stages={
                AgentType.CLASSIFIER: Mock(matched=True),
                AgentType.ATTACKER: Mock(matched=True),
                AgentType.DEFENDER: Mock(matched=True),
            },
            focal_nodes=["fn_1"],
        )
        assert result1.get_final_verdict() is True

        # One didn't match
        result2 = ChainedResult(
            stages={
                AgentType.CLASSIFIER: Mock(matched=True),
                AgentType.ATTACKER: Mock(matched=False),
            },
            focal_nodes=["fn_1"],
        )
        assert result2.get_final_verdict() is False


# Success Criteria Tests


class TestSuccessCriteria:
    """Validate P2-T1 success criteria."""

    def test_context_slicing_implemented(self, context_slicer):
        """Context slicing should be implemented for all agent types."""
        agent_types = [
            AgentType.CLASSIFIER,
            AgentType.ATTACKER,
            AgentType.DEFENDER,
            AgentType.VERIFIER,
        ]

        for agent_type in agent_types:
            ctx = context_slicer.slice_for_agent(agent_type, ["fn_1"])
            assert ctx.agent_type == agent_type
            assert ctx.focal_nodes == ["fn_1"]

    def test_token_reduction_target(self, context_slicer):
        """Token reduction should be >= 80%."""
        focal_nodes = ["fn_1", "fn_2"]

        # Create contexts
        contexts = {
            agent_type: context_slicer.slice_for_agent(agent_type, focal_nodes)
            for agent_type in [
                AgentType.CLASSIFIER,
                AgentType.ATTACKER,
                AgentType.DEFENDER,
                AgentType.VERIFIER,
            ]
        }

        # Measure tokens
        total_sliced = sum(c.estimate_tokens() for c in contexts.values())
        baseline = len(focal_nodes) * 2000 * 4  # 4 agents

        reduction = 1 - (total_sliced / baseline)
        assert reduction >= 0.80, f"Token reduction {reduction:.1%} below 80%"

    def test_parallel_execution_working(self, agent_router):
        """Parallel execution should work."""
        # Register multiple agents
        for agent_type in [AgentType.CLASSIFIER, AgentType.ATTACKER]:
            agent = Mock()
            agent.analyze = Mock(return_value=Mock(matched=True))
            agent_router.register_agent(agent_type, agent)

        # Run parallel
        results = agent_router.route(
            focal_nodes=["fn_1"],
            parallel=True,
        )

        assert len(results) == 2

    def test_result_chaining_working(self, agent_router):
        """Result chaining should work."""
        # Register agents
        classifier = Mock()
        classifier.analyze = Mock(return_value=Mock(matched=True))

        attacker = Mock()
        attacker.analyze = Mock(return_value=Mock(matched=True))

        agent_router.register_agent(AgentType.CLASSIFIER, classifier)
        agent_router.register_agent(AgentType.ATTACKER, attacker)

        # Chain
        result = agent_router.route_with_chaining(focal_nodes=["fn_1"])

        assert isinstance(result, ChainedResult)
        assert len(result.stages) == 2
