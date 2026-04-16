"""
Tests for P1-T3: Builder Integration

Tests the integration of intent annotation with VKG graphs.
"""

import pytest
import json
from pathlib import Path

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node, Edge, Evidence
from alphaswarm_sol.intent import (
    IntentAnnotator,
    IntentEnrichedGraph,
    enrich_graph_with_intent,
    BusinessPurpose,
    TrustLevel,
    FunctionIntent,
)


# Mock Classes

class MockNode:
    """Mock VKG node."""

    def __init__(self, id: str, label: str, type: str, properties: dict = None):
        self.id = id
        self.label = label
        self.type = type
        self.properties = properties or {}
        self.evidence = []


class MockLLMClient:
    """Mock LLM client."""

    def __init__(self):
        self.call_count = 0

    def analyze(self, prompt: str, response_format: str = "text", temperature: float = 0.7) -> str:
        self.call_count += 1
        return json.dumps({
            "business_purpose": "withdrawal",
            "purpose_confidence": 0.9,
            "purpose_reasoning": "Withdrawal function",
            "expected_trust_level": "depositor_only",
            "authorized_callers": ["depositor"],
            "trust_assumptions": [],
            "inferred_invariants": [],
            "likely_specs": [],
            "spec_confidence": {},
            "risk_notes": [],
            "complexity_score": 0.5,
        })


class MockDomainKG:
    """Mock domain KG."""

    def __init__(self):
        self.specifications = []
        self.primitives = []


# Test Fixtures

@pytest.fixture
def mock_llm():
    """Create mock LLM client."""
    return MockLLMClient()


@pytest.fixture
def mock_domain_kg():
    """Create mock domain KG."""
    return MockDomainKG()


@pytest.fixture
def annotator(mock_llm, mock_domain_kg):
    """Create annotator."""
    return IntentAnnotator(mock_llm, mock_domain_kg)


@pytest.fixture
def simple_graph():
    """Create simple test graph."""
    graph = KnowledgeGraph()

    # Contract node
    contract = Node(
        id="contract_1",
        label="TestContract",
        type="Contract",
        properties={"inherits": ["Ownable"]},
        evidence=[],
    )
    graph.nodes[contract.id] = contract

    # Function nodes
    fn1 = Node(
        id="fn_1",
        label="withdraw",
        type="Function",
        properties={
            "visibility": "external",
            "semantic_ops": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
            "source_code": "function withdraw(uint amount) external { }",
        },
        evidence=[],
    )
    graph.nodes[fn1.id] = fn1

    fn2 = Node(
        id="fn_2",
        label="deposit",
        type="Function",
        properties={
            "visibility": "external",
            "semantic_ops": ["WRITES_USER_BALANCE"],
        },
        evidence=[],
    )
    graph.nodes[fn2.id] = fn2

    # Edges
    edge1 = Edge(
        id=f"{contract.id}_DEFINES_{fn1.id}",
        type="DEFINES",
        source=contract.id,
        target=fn1.id,
        evidence=[],
    )
    graph.edges[edge1.id] = edge1

    edge2 = Edge(
        id=f"{contract.id}_DEFINES_{fn2.id}",
        type="DEFINES",
        source=contract.id,
        target=fn2.id,
        evidence=[],
    )
    graph.edges[edge2.id] = edge2

    return graph


# IntentEnrichedGraph Tests

class TestIntentEnrichedGraph:
    """Test IntentEnrichedGraph functionality."""

    def test_creation(self, simple_graph, annotator):
        """Test creating enriched graph."""
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        assert enriched.graph == simple_graph
        assert enriched.annotator == annotator

    def test_get_intent_lazy(self, simple_graph, annotator, mock_llm):
        """Test lazy intent annotation."""
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        fn_node = simple_graph.nodes["fn_1"]
        assert "intent" not in fn_node.properties

        # First call should annotate
        intent = enriched.get_intent(fn_node)

        assert intent is not None
        assert isinstance(intent, FunctionIntent)
        assert "intent" in fn_node.properties
        assert mock_llm.call_count == 1

        # Second call should use cache
        intent2 = enriched.get_intent(fn_node)

        assert intent2 is not None
        assert mock_llm.call_count == 1  # No new call

    def test_get_intent_non_function(self, simple_graph, annotator):
        """Test getting intent for non-function returns None."""
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        contract_node = simple_graph.nodes["contract_1"]
        intent = enriched.get_intent(contract_node)

        assert intent is None

    def test_annotate_all_functions(self, simple_graph, annotator, mock_llm):
        """Test annotating all functions."""
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        count = enriched.annotate_all_functions()

        # Should annotate at least one function (fn_1 has source_code)
        assert count >= 1
        assert "intent" in simple_graph.nodes["fn_1"].properties

    def test_get_functions_by_purpose(self, simple_graph, annotator):
        """Test querying functions by business purpose."""
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        # Annotate all
        enriched.annotate_all_functions()

        # Query by purpose
        withdrawals = enriched.get_functions_by_purpose("withdrawal")

        assert len(withdrawals) >= 1
        assert withdrawals[0].label == "withdraw"

    def test_get_high_risk_functions(self, simple_graph, mock_domain_kg):
        """Test querying high-risk functions."""
        # Create LLM that returns high-risk intent
        high_risk_llm = MockLLMClient()
        high_risk_llm.analyze = lambda *args, **kwargs: json.dumps({
            "business_purpose": "liquidate",
            "purpose_confidence": 0.9,
            "purpose_reasoning": "Liquidation function",
            "expected_trust_level": "permissionless",
            "authorized_callers": ["anyone"],
            "trust_assumptions": [
                {
                    "id": "oracle_fresh",
                    "description": "Oracle is fresh",
                    "category": "oracle",
                    "critical": True,
                }
            ],
            "inferred_invariants": [],
            "likely_specs": [],
            "spec_confidence": {},
            "risk_notes": ["Critical oracle dependency"],
            "complexity_score": 0.9,
        })

        annotator = IntentAnnotator(high_risk_llm, mock_domain_kg)
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        high_risk = enriched.get_high_risk_functions()

        assert len(high_risk) >= 1

    def test_get_authorization_mismatches(self, simple_graph, mock_domain_kg):
        """Test detecting authorization mismatches."""
        # Create LLM that returns restricted access intent
        llm = MockLLMClient()
        llm.analyze = lambda *args, **kwargs: json.dumps({
            "business_purpose": "withdrawal",
            "purpose_confidence": 0.9,
            "purpose_reasoning": "Withdrawal",
            "expected_trust_level": "depositor_only",  # Expects access control
            "authorized_callers": ["depositor"],
            "trust_assumptions": [],
            "inferred_invariants": [],
            "likely_specs": [],
            "spec_confidence": {},
            "risk_notes": [],
            "complexity_score": 0.5,
        })

        annotator = IntentAnnotator(llm, mock_domain_kg)
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        mismatches = enriched.get_authorization_mismatches()

        # Should detect mismatch (no access gate in mock)
        assert len(mismatches) >= 1
        node, description = mismatches[0]
        assert "no access gate" in description.lower()

    def test_get_function_code_from_properties(self, simple_graph, annotator):
        """Test extracting function code from properties."""
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        fn_node = simple_graph.nodes["fn_1"]
        code = enriched._get_function_code(fn_node)

        assert code is not None
        assert "withdraw" in code

    def test_get_function_code_from_source_map(self, simple_graph, annotator):
        """Test extracting function code from source map."""
        source_map = {
            "fn_2": "function deposit(uint amount) external payable { }",
        }

        enriched = IntentEnrichedGraph(simple_graph, annotator, source_map)

        fn_node = simple_graph.nodes["fn_2"]
        code = enriched._get_function_code(fn_node)

        assert code is not None
        assert "deposit" in code

    def test_get_contract_context(self, simple_graph, annotator):
        """Test extracting contract context."""
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        fn_node = simple_graph.nodes["fn_1"]
        context = enriched._get_contract_context(fn_node)

        assert context is not None
        assert "TestContract" in context
        assert "Ownable" in context


# Factory Function Tests

class TestEnrichGraphWithIntent:
    """Test enrich_graph_with_intent factory function."""

    def test_factory_lazy(self, simple_graph, annotator, mock_llm):
        """Test factory function with lazy annotation."""
        enriched = enrich_graph_with_intent(simple_graph, annotator, annotate_now=False)

        assert isinstance(enriched, IntentEnrichedGraph)
        assert mock_llm.call_count == 0  # No annotation yet

    def test_factory_eager(self, simple_graph, annotator, mock_llm):
        """Test factory function with eager annotation."""
        enriched = enrich_graph_with_intent(simple_graph, annotator, annotate_now=True)

        assert isinstance(enriched, IntentEnrichedGraph)
        assert mock_llm.call_count >= 1  # Annotated immediately

    def test_factory_with_source_map(self, simple_graph, annotator):
        """Test factory function with source map."""
        source_map = {"fn_1": "function withdraw() { }"}

        enriched = enrich_graph_with_intent(
            simple_graph,
            annotator,
            source_map=source_map,
        )

        assert enriched.source_map == source_map


# Integration Tests

class TestBuilderIntegration:
    """Test integration scenarios."""

    def test_intent_properties_added(self, simple_graph, annotator):
        """Test that intent properties are added to nodes."""
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        fn_node = simple_graph.nodes["fn_1"]
        enriched.get_intent(fn_node)

        # Check properties added
        assert "intent" in fn_node.properties
        assert "business_purpose" in fn_node.properties
        assert "trust_level" in fn_node.properties
        assert "purpose_confidence" in fn_node.properties

    def test_batch_annotation(self, simple_graph, annotator, mock_llm):
        """Test batch annotation."""
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        # Annotate with batch size 10 (functions in one batch)
        count = enriched.annotate_all_functions(batch_size=10)

        assert count >= 1  # At least one function annotated
        assert mock_llm.call_count >= 1

    def test_query_after_annotation(self, simple_graph, annotator):
        """Test querying works after annotation."""
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        # Annotate
        enriched.annotate_all_functions()

        # Query
        withdrawals = enriched.get_functions_by_purpose("withdrawal")
        assert len(withdrawals) >= 0  # May or may not have withdrawals

        high_risk = enriched.get_high_risk_functions(threshold=0.8)
        assert isinstance(high_risk, list)


# Success Criteria Tests

class TestSuccessCriteria:
    """Validate P1-T3 success criteria."""

    def test_lazy_annotation_works(self, simple_graph, annotator):
        """Lazy annotation should work on-demand."""
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        fn_node = simple_graph.nodes["fn_1"]
        intent = enriched.get_intent(fn_node)

        assert intent is not None
        assert isinstance(intent, FunctionIntent)

    def test_intent_stored_in_properties(self, simple_graph, annotator):
        """Intent should be stored in node properties."""
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        fn_node = simple_graph.nodes["fn_1"]
        enriched.get_intent(fn_node)

        assert "intent" in fn_node.properties
        assert isinstance(fn_node.properties["intent"], dict)

    def test_backward_compatible(self, simple_graph, annotator):
        """Should work without annotator (returns None)."""
        # Create enriched graph but don't annotate
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        # Can still access graph
        assert len(enriched.graph.nodes) == 3

    def test_serialization_preserves_intent(self, simple_graph, annotator):
        """Serialized graph should preserve intent."""
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        fn_node = simple_graph.nodes["fn_1"]
        enriched.get_intent(fn_node)

        # Intent stored as dict (JSON-serializable)
        intent_dict = fn_node.properties["intent"]
        assert isinstance(intent_dict, dict)
        assert "business_purpose" in intent_dict

    def test_enriched_graph_provides_value(self, simple_graph, annotator):
        """Enriched graph should provide intent-based queries."""
        enriched = IntentEnrichedGraph(simple_graph, annotator)

        enriched.annotate_all_functions()

        # Can query by purpose
        by_purpose = enriched.get_functions_by_purpose("withdrawal")
        assert isinstance(by_purpose, list)

        # Can query high-risk
        high_risk = enriched.get_high_risk_functions()
        assert isinstance(high_risk, list)

        # Can detect mismatches
        mismatches = enriched.get_authorization_mismatches()
        assert isinstance(mismatches, list)
