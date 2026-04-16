"""
Tests for P3-T2: Causal Reasoning Engine

Validates causal graph construction, root cause identification,
and intervention point generation.
"""

import pytest
from unittest.mock import Mock
from alphaswarm_sol.reasoning.causal import (
    CausalReasoningEngine,
    CausalGraph,
    CausalNode,
    CausalEdge,
    RootCause,
    InterventionPoint,
    CausalAnalysis,
    CausalRelationType,
    OperationInfo,
)


# Mock fixtures
@pytest.fixture
def mock_kg():
    """Create mock knowledge graph."""
    kg = Mock()
    return kg


@pytest.fixture
def engine(mock_kg):
    """Create causal reasoning engine."""
    return CausalReasoningEngine(mock_kg)


def create_mock_function(fn_id: str, signature: str, properties: dict):
    """Helper to create mock function node."""
    fn = Mock()
    fn.id = fn_id
    fn.properties = {
        "behavioral_signature": signature,
        **properties
    }
    return fn


# ============================================================================
# PART 1: Enum and Dataclass Tests
# ============================================================================

class TestEnumsAndDataclasses:
    """Test enum values and dataclass creation."""

    def test_causal_relation_types(self):
        """Test CausalRelationType enum values."""
        assert CausalRelationType.DATA_FLOW.value == "data_flow"
        assert CausalRelationType.CONTROL_FLOW.value == "control_flow"
        assert CausalRelationType.SEQUENCE.value == "sequence"
        assert CausalRelationType.EXTERNAL_INFLUENCE.value == "external"
        assert CausalRelationType.STATE_DEPENDENCY.value == "state_dep"

    def test_causal_node_creation(self):
        """Test CausalNode dataclass creation."""
        node = CausalNode(
            id="n1",
            operation="READS_USER_BALANCE",
            description="Read balance",
            line_start=10,
            line_end=10,
            is_controllable=False,
            is_observable=True,
        )

        assert node.id == "n1"
        assert node.operation == "READS_USER_BALANCE"
        assert node.is_observable is True
        assert node.centrality_score == 0.0
        assert node.causes == []
        assert node.effects == []

    def test_causal_edge_creation(self):
        """Test CausalEdge dataclass creation."""
        edge = CausalEdge(
            source_id="n1",
            target_id="n2",
            relation_type=CausalRelationType.DATA_FLOW,
            strength=0.9,
            is_breakable=False,
        )

        assert edge.source_id == "n1"
        assert edge.target_id == "n2"
        assert edge.strength == 0.9
        assert edge.evidence == []
        assert edge.break_methods == []

    def test_root_cause_creation(self):
        """Test RootCause dataclass creation."""
        rc = RootCause(
            id="rc1",
            description="External call before state update",
            cause_type="ordering_violation",
            severity="critical",
            causal_path=["n1", "n2"],
            intervention="Reorder operations",
            intervention_confidence=0.95,
            confidence=0.9,
        )

        assert rc.id == "rc1"
        assert rc.cause_type == "ordering_violation"
        assert rc.severity == "critical"
        assert rc.causal_path == ["n1", "n2"]
        assert rc.confidence == 0.9

    def test_intervention_point_creation(self):
        """Test InterventionPoint dataclass creation."""
        ip = InterventionPoint(
            id="ip1",
            node_id="n1",
            intervention_type="reorder",
            description="Reorder operations",
            impact_score=0.95,
            complexity="moderate",
        )

        assert ip.id == "ip1"
        assert ip.intervention_type == "reorder"
        assert ip.impact_score == 0.95
        assert ip.side_effects == []


# ============================================================================
# PART 2: Causal Graph Construction
# ============================================================================

class TestCausalGraphConstruction:
    """Test causal graph building and manipulation."""

    def test_empty_causal_graph(self):
        """Test creating empty causal graph."""
        graph = CausalGraph(
            id="cg_test",
            focal_node_id="fn_test",
            vulnerability_id="vuln_1",
        )

        assert graph.id == "cg_test"
        assert graph.focal_node_id == "fn_test"
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_add_nodes_to_graph(self):
        """Test adding nodes to causal graph."""
        graph = CausalGraph(id="test", focal_node_id="fn")

        node1 = CausalNode(
            id="n1",
            operation="READS_USER_BALANCE",
            description="Read balance",
            line_start=10,
            line_end=10,
        )
        node2 = CausalNode(
            id="n2",
            operation="WRITES_USER_BALANCE",
            description="Write balance",
            line_start=20,
            line_end=20,
        )

        graph.add_node(node1)
        graph.add_node(node2)

        assert len(graph.nodes) == 2
        assert "n1" in graph.nodes
        assert "n2" in graph.nodes

    def test_add_edges_updates_connectivity(self):
        """Test that adding edges updates node connectivity."""
        graph = CausalGraph(id="test", focal_node_id="fn")

        # Add nodes
        for i in range(3):
            graph.add_node(CausalNode(
                id=f"n{i}",
                operation=f"OP_{i}",
                description=f"Op {i}",
                line_start=i,
                line_end=i,
            ))

        # Add edge n0 -> n1
        graph.add_edge(CausalEdge(
            source_id="n0",
            target_id="n1",
            relation_type=CausalRelationType.SEQUENCE,
            strength=1.0,
        ))

        # Check connectivity
        assert "n1" in graph.nodes["n0"].effects
        assert "n0" in graph.nodes["n1"].causes

    def test_graph_get_ancestors(self):
        """Test getting all ancestors of a node."""
        graph = CausalGraph(id="test", focal_node_id="fn")

        # Add nodes
        for i in range(4):
            graph.add_node(CausalNode(
                id=f"n{i}",
                operation=f"OP_{i}",
                description=f"Op {i}",
                line_start=i,
                line_end=i,
            ))

        # n0 → n1 → n2
        graph.add_edge(CausalEdge(source_id="n0", target_id="n1", relation_type=CausalRelationType.SEQUENCE, strength=1.0))
        graph.add_edge(CausalEdge(source_id="n1", target_id="n2", relation_type=CausalRelationType.SEQUENCE, strength=1.0))

        ancestors = graph.get_ancestors("n2")
        assert "n0" in ancestors
        assert "n1" in ancestors
        assert len(ancestors) == 2

    def test_graph_get_descendants(self):
        """Test getting all descendants of a node."""
        graph = CausalGraph(id="test", focal_node_id="fn")

        # Add nodes
        for i in range(4):
            graph.add_node(CausalNode(
                id=f"n{i}",
                operation=f"OP_{i}",
                description=f"Op {i}",
                line_start=i,
                line_end=i,
            ))

        # n0 → n1
        #      ↓
        #     n2
        graph.add_edge(CausalEdge(source_id="n0", target_id="n1", relation_type=CausalRelationType.SEQUENCE, strength=1.0))
        graph.add_edge(CausalEdge(source_id="n1", target_id="n2", relation_type=CausalRelationType.SEQUENCE, strength=1.0))

        descendants = graph.get_descendants("n0")
        assert "n1" in descendants
        assert "n2" in descendants

    def test_graph_find_paths(self):
        """Test finding all causal paths between nodes."""
        graph = CausalGraph(id="test", focal_node_id="fn")

        # Add nodes
        for i in range(4):
            graph.add_node(CausalNode(
                id=f"n{i}",
                operation=f"OP_{i}",
                description=f"Op {i}",
                line_start=i,
                line_end=i,
            ))

        # n0 → n1 → n2
        graph.add_edge(CausalEdge(source_id="n0", target_id="n1", relation_type=CausalRelationType.SEQUENCE, strength=1.0))
        graph.add_edge(CausalEdge(source_id="n1", target_id="n2", relation_type=CausalRelationType.SEQUENCE, strength=1.0))

        paths = graph.find_paths("n0", "n2")
        assert len(paths) == 1
        assert paths[0] == ["n0", "n1", "n2"]

    def test_graph_find_multiple_paths(self):
        """Test finding multiple paths in diamond graph."""
        graph = CausalGraph(id="test", focal_node_id="fn")

        # Add nodes
        for i in range(4):
            graph.add_node(CausalNode(
                id=f"n{i}",
                operation=f"OP_{i}",
                description=f"Op {i}",
                line_start=i,
                line_end=i,
            ))

        # Diamond: n0 → n1 → n3
        #          n0 → n2 → n3
        graph.add_edge(CausalEdge(source_id="n0", target_id="n1", relation_type=CausalRelationType.SEQUENCE, strength=1.0))
        graph.add_edge(CausalEdge(source_id="n0", target_id="n2", relation_type=CausalRelationType.SEQUENCE, strength=1.0))
        graph.add_edge(CausalEdge(source_id="n1", target_id="n3", relation_type=CausalRelationType.SEQUENCE, strength=1.0))
        graph.add_edge(CausalEdge(source_id="n2", target_id="n3", relation_type=CausalRelationType.SEQUENCE, strength=1.0))

        paths = graph.find_paths("n0", "n3")
        assert len(paths) == 2


# ============================================================================
# PART 3: Operation Extraction
# ============================================================================

class TestOperationExtraction:
    """Test extracting operations from behavioral signatures."""

    def test_extract_operations_reentrancy_signature(self, engine):
        """Test extracting operations from reentrancy signature."""
        fn = create_mock_function(
            "fn_withdraw",
            "R:bal→X:out→W:bal",
            {}
        )

        ops = engine._extract_operations(fn)

        assert len(ops) == 3
        assert ops[0].operation == "READS_USER_BALANCE"
        assert ops[1].operation == "TRANSFERS_VALUE_OUT"
        assert ops[2].operation == "WRITES_USER_BALANCE"

    def test_extract_operations_access_control_signature(self, engine):
        """Test extracting operations from access control signature."""
        fn = create_mock_function(
            "fn_set_owner",
            "C:perm→M:own",
            {}
        )

        ops = engine._extract_operations(fn)

        assert len(ops) == 2
        assert ops[0].operation == "CHECKS_PERMISSION"
        assert ops[1].operation == "MODIFIES_OWNER"

    def test_extract_operations_oracle_signature(self, engine):
        """Test extracting operations from oracle signature."""
        fn = create_mock_function(
            "fn_calculate",
            "R:orc→A:div",
            {}
        )

        ops = engine._extract_operations(fn)

        assert len(ops) == 2
        assert ops[0].operation == "READS_ORACLE"
        assert ops[1].operation == "PERFORMS_DIVISION"

    def test_extract_operations_empty_signature(self, engine):
        """Test extracting from empty signature."""
        fn = create_mock_function(
            "fn_empty",
            "",
            {}
        )

        ops = engine._extract_operations(fn)
        assert len(ops) == 0


# ============================================================================
# PART 4: Edge Building
# ============================================================================

class TestEdgeBuilding:
    """Test building different types of causal edges."""

    def test_build_causal_graph_creates_nodes(self, engine):
        """Test that build_causal_graph creates nodes from signature."""
        fn = create_mock_function(
            "fn_withdraw",
            "R:bal→X:out→W:bal",
            {}
        )

        graph = engine.build_causal_graph(fn, None)

        assert len(graph.nodes) == 3
        assert graph.focal_node_id == "fn_withdraw"

    def test_sequence_edges_created(self, engine):
        """Test that sequence edges are created."""
        fn = create_mock_function(
            "fn_withdraw",
            "R:bal→X:out→W:bal",
            {}
        )

        graph = engine.build_causal_graph(fn, None)

        sequence_edges = [e for e in graph.edges if e.relation_type == CausalRelationType.SEQUENCE]
        assert len(sequence_edges) == 2  # 3 ops → 2 sequence edges

    def test_external_influence_edges_for_reentrancy(self, engine):
        """Test external influence edges for reentrancy pattern."""
        fn = create_mock_function(
            "fn_withdraw_vuln",
            "R:bal→X:out→W:bal",
            {}
        )

        graph = engine.build_causal_graph(fn, None)

        # Should have external influence edge from X:out to W:bal
        influence_edges = [e for e in graph.edges if e.relation_type == CausalRelationType.EXTERNAL_INFLUENCE]
        assert len(influence_edges) > 0

    def test_data_flow_edges_for_balance_operations(self, engine):
        """Test data flow edges from balance read."""
        fn = create_mock_function(
            "fn_withdraw",
            "R:bal→X:out→W:bal",
            {}
        )

        graph = engine.build_causal_graph(fn, None)

        # Should have data flow edges from R:bal to both X:out and W:bal
        data_flow_edges = [e for e in graph.edges if e.relation_type == CausalRelationType.DATA_FLOW]
        assert len(data_flow_edges) > 0

    def test_control_flow_edges_for_permission_check(self, engine):
        """Test control flow edges from permission check."""
        fn = create_mock_function(
            "fn_protected",
            "C:perm→M:own",
            {}
        )

        graph = engine.build_causal_graph(fn, None)

        # Should have control flow edge from C:perm to M:own
        control_edges = [e for e in graph.edges if e.relation_type == CausalRelationType.CONTROL_FLOW]
        assert len(control_edges) > 0


# ============================================================================
# PART 5: Root Cause Identification
# ============================================================================

class TestRootCauseIdentification:
    """Test identifying root causes for different vulnerability patterns."""

    def test_identify_reentrancy_ordering_violation(self, engine):
        """Test identifying reentrancy ordering violation."""
        fn = create_mock_function(
            "fn_withdraw_vuln",
            "R:bal→X:out→W:bal",
            {
                "has_reentrancy_guard": False,
                "state_write_after_external_call": True,
            }
        )

        graph = engine.build_causal_graph(fn, None)
        root_causes = engine._identify_reentrancy_root_causes(graph, fn)

        # Should find ordering violation
        ordering_violations = [rc for rc in root_causes if rc.cause_type == "ordering_violation"]
        assert len(ordering_violations) > 0
        assert "CEI" in ordering_violations[0].intervention

    def test_identify_missing_reentrancy_guard(self, engine):
        """Test identifying missing reentrancy guard."""
        fn = create_mock_function(
            "fn_withdraw_no_guard",
            "R:bal→X:out→W:bal",
            {
                "has_reentrancy_guard": False,
            }
        )

        graph = engine.build_causal_graph(fn, None)
        root_causes = engine._identify_reentrancy_root_causes(graph, fn)

        # Should find missing guard
        missing_guard = [rc for rc in root_causes if rc.cause_type == "missing_guard"]
        assert len(missing_guard) > 0
        assert "nonReentrant" in missing_guard[0].intervention

    def test_identify_access_control_root_cause(self, engine):
        """Test identifying missing access control."""
        fn = create_mock_function(
            "fn_set_owner",
            "M:own",
            {
                "has_access_gate": False,
                "writes_privileged_state": True,
                "modifies_owner": True,
            }
        )

        graph = engine.build_causal_graph(fn, None)
        root_causes = engine._identify_access_control_root_causes(graph, fn)

        assert len(root_causes) > 0
        rc = root_causes[0]
        assert rc.cause_type == "missing_guard"
        assert "access" in rc.intervention.lower() or "onlyOwner" in rc.intervention

    def test_identify_oracle_staleness_root_cause(self, engine):
        """Test identifying oracle staleness root cause."""
        fn = create_mock_function(
            "fn_get_price",
            "R:orc→A:div",
            {
                "reads_oracle_price": True,
                "has_staleness_check": False,
            }
        )

        graph = engine.build_causal_graph(fn, None)
        root_causes = engine._identify_oracle_root_causes(graph, fn)

        assert len(root_causes) > 0
        rc = root_causes[0]
        assert rc.cause_type == "missing_validation"
        assert "staleness" in rc.description.lower()

    def test_no_root_cause_for_safe_reentrancy_pattern(self, engine):
        """Test that safe CEI pattern has no ordering violations."""
        fn = create_mock_function(
            "fn_withdraw_safe",
            "R:bal→W:bal→X:out",  # Correct CEI order
            {
                "has_reentrancy_guard": True,
            }
        )

        graph = engine.build_causal_graph(fn, None)
        root_causes = engine._identify_reentrancy_root_causes(graph, fn)

        # Should have no ordering violations (external call is after state write)
        ordering_violations = [rc for rc in root_causes if rc.cause_type == "ordering_violation"]
        assert len(ordering_violations) == 0

    def test_no_root_cause_for_protected_function(self, engine):
        """Test that protected function has no access control issues."""
        fn = create_mock_function(
            "fn_set_owner_protected",
            "C:perm→M:own",
            {
                "has_access_gate": True,
                "writes_privileged_state": True,
            }
        )

        graph = engine.build_causal_graph(fn, None)
        root_causes = engine._identify_access_control_root_causes(graph, fn)

        # Should have no missing guard issues
        assert len(root_causes) == 0


# ============================================================================
# PART 6: Intervention Points
# ============================================================================

class TestInterventionPoints:
    """Test finding intervention points."""

    def test_intervention_for_ordering_violation(self, engine):
        """Test intervention suggestion for ordering violation."""
        rc = RootCause(
            id="rc1",
            description="Ordering violation",
            cause_type="ordering_violation",
            severity="critical",
            causal_path=["n1", "n2"],
            intervention="Reorder",
            intervention_confidence=0.95,
        )

        graph = CausalGraph(id="test", focal_node_id="fn")
        interventions = engine._find_intervention_points(graph, [rc])

        assert len(interventions) > 0
        assert interventions[0].intervention_type == "reorder"
        assert interventions[0].impact_score == 0.95

    def test_intervention_for_missing_guard(self, engine):
        """Test intervention suggestion for missing guard."""
        rc = RootCause(
            id="rc1",
            description="Missing guard",
            cause_type="missing_guard",
            severity="high",
            causal_path=["n1"],
            intervention="Add guard",
            intervention_confidence=0.9,
        )

        graph = CausalGraph(id="test", focal_node_id="fn")
        interventions = engine._find_intervention_points(graph, [rc])

        assert len(interventions) > 0
        assert interventions[0].intervention_type == "add_guard"
        assert "nonReentrant" in interventions[0].code_suggestion

    def test_intervention_for_missing_validation(self, engine):
        """Test intervention suggestion for missing validation."""
        rc = RootCause(
            id="rc1",
            description="Missing validation",
            cause_type="missing_validation",
            severity="high",
            causal_path=["n1"],
            intervention="Add check",
            intervention_confidence=0.85,
        )

        graph = CausalGraph(id="test", focal_node_id="fn")
        interventions = engine._find_intervention_points(graph, [rc])

        assert len(interventions) > 0
        assert interventions[0].intervention_type == "add_check"


# ============================================================================
# PART 7: Explanation Generation
# ============================================================================

class TestExplanationGeneration:
    """Test human-readable explanation generation."""

    def test_generate_explanation_with_root_causes(self, engine):
        """Test generating explanation with root causes."""
        rc = RootCause(
            id="rc1",
            description="External call before state update",
            cause_type="ordering_violation",
            severity="critical",
            causal_path=["op_1", "op_2"],
            intervention="Reorder operations",
            intervention_confidence=0.95,
            confidence=0.9,
            contributing_factors=["No guard", "Wrong order"],
            evidence=["Call at line 10", "Write at line 15"],
            related_cwes=["CWE-841"],
        )

        ip = InterventionPoint(
            id="ip1",
            node_id="op_1",
            intervention_type="reorder",
            description="Reorder to CEI",
            impact_score=0.95,
            complexity="moderate",
            code_suggestion="// Example fix",
        )

        graph = CausalGraph(id="test", focal_node_id="fn")
        explanation = engine.generate_explanation(graph, [rc], [ip])

        assert "Root Cause" in explanation
        assert "ordering_violation" in explanation
        assert "critical" in explanation
        assert "CWE-841" in explanation
        assert "Fix" in explanation
        assert "reorder" in explanation

    def test_generate_explanation_no_root_causes(self, engine):
        """Test generating explanation when no root causes found."""
        graph = CausalGraph(id="test", focal_node_id="fn")
        explanation = engine.generate_explanation(graph, [], [])

        assert "Root Cause" in explanation
        assert "secure" in explanation.lower() or "No root causes" in explanation


# ============================================================================
# PART 8: Complete Analysis
# ============================================================================

class TestCompleteAnalysis:
    """Test end-to-end causal analysis."""

    def test_analyze_vulnerable_reentrancy(self, engine):
        """Test complete analysis of vulnerable reentrancy pattern."""
        fn = create_mock_function(
            "fn_withdraw_vuln",
            "R:bal→X:out→W:bal",
            {
                "has_reentrancy_guard": False,
                "state_write_after_external_call": True,
            }
        )

        analysis = engine.analyze(fn, None)

        # Should have causal graph
        assert analysis.causal_graph is not None
        assert len(analysis.causal_graph.nodes) == 3

        # Should have root causes
        assert len(analysis.root_causes) > 0

        # Should have interventions
        assert len(analysis.intervention_points) > 0

        # Should have explanation
        assert len(analysis.explanation) > 100

        # Should have reasonable confidence
        assert analysis.confidence > 0.5

        # Should complete quickly
        assert analysis.analysis_time_ms < 1000

    def test_analyze_safe_reentrancy(self, engine):
        """Test analysis of safe reentrancy pattern (CEI)."""
        fn = create_mock_function(
            "fn_withdraw_safe",
            "R:bal→W:bal→X:out",
            {
                "has_reentrancy_guard": True,
            }
        )

        analysis = engine.analyze(fn, None)

        # Should have causal graph
        assert analysis.causal_graph is not None

        # Should have no or fewer root causes
        ordering_violations = [rc for rc in analysis.root_causes if rc.cause_type == "ordering_violation"]
        assert len(ordering_violations) == 0

    def test_analyze_vulnerable_access_control(self, engine):
        """Test analysis of missing access control."""
        fn = create_mock_function(
            "fn_set_owner",
            "M:own",
            {
                "has_access_gate": False,
                "writes_privileged_state": True,
                "modifies_owner": True,
            }
        )

        analysis = engine.analyze(fn, None)

        # Should identify access control issue
        access_issues = [rc for rc in analysis.root_causes if "access" in rc.id]
        assert len(access_issues) > 0

        # Should suggest access control fix
        assert any("access" in ip.description.lower() or "guard" in ip.intervention_type
                   for ip in analysis.intervention_points)

    def test_analyze_with_vulnerability_context(self, engine):
        """Test analysis with vulnerability context."""
        fn = create_mock_function(
            "fn_withdraw",
            "R:bal→X:out→W:bal",
            {
                "has_reentrancy_guard": False,
            }
        )

        vuln = {
            "id": "vuln_1",
            "attack_patterns": [
                {"id": "reentrancy_classic"}
            ]
        }

        analysis = engine.analyze(fn, vuln)

        # Should use vulnerability context
        assert analysis.causal_graph.vulnerability_id == "vuln_1"

        # Should identify reentrancy-specific root causes
        assert any("reentrancy" in rc.related_patterns or "reentrancy" in rc.id
                   for rc in analysis.root_causes if rc.related_patterns)


# ============================================================================
# PART 9: Helper Methods
# ============================================================================

class TestHelperMethods:
    """Test helper methods."""

    def test_is_controllable(self, engine):
        """Test controllability detection."""
        op_controllable = OperationInfo(
            operation="TRANSFERS_VALUE_OUT",
            description="Transfer",
            line=10,
            index=0,
        )
        assert engine._is_controllable(op_controllable) is True

        op_not_controllable = OperationInfo(
            operation="READS_USER_BALANCE",
            description="Read",
            line=10,
            index=0,
        )
        assert engine._is_controllable(op_not_controllable) is False

    def test_is_observable(self, engine):
        """Test observability detection."""
        op_observable = OperationInfo(
            operation="READS_USER_BALANCE",
            description="Read",
            line=10,
            index=0,
        )
        assert engine._is_observable(op_observable) is True

        op_not_observable = OperationInfo(
            operation="TRANSFERS_VALUE_OUT",
            description="Transfer",
            line=10,
            index=0,
        )
        assert engine._is_observable(op_not_observable) is False

    def test_compute_confidence(self, engine):
        """Test confidence computation."""
        root_causes = [
            RootCause(
                id="rc1",
                description="Test",
                cause_type="test",
                severity="high",
                causal_path=[],
                intervention="Fix",
                intervention_confidence=0.9,
                confidence=0.8,
            ),
            RootCause(
                id="rc2",
                description="Test",
                cause_type="test",
                severity="high",
                causal_path=[],
                intervention="Fix",
                intervention_confidence=0.9,
                confidence=0.9,
            ),
        ]

        confidence = engine._compute_confidence(root_causes)
        assert abs(confidence - 0.85) < 0.001  # Average of 0.8 and 0.9 (within tolerance)

    def test_compute_confidence_empty(self, engine):
        """Test confidence computation with no root causes."""
        confidence = engine._compute_confidence([])
        assert confidence == 0.0

    def test_compute_centrality(self, engine):
        """Test centrality score computation."""
        graph = CausalGraph(id="test", focal_node_id="fn")

        # Add nodes
        for i in range(3):
            graph.add_node(CausalNode(
                id=f"n{i}",
                operation=f"OP_{i}",
                description=f"Op {i}",
                line_start=i,
                line_end=i,
            ))

        # n0 → n1 → n2
        graph.add_edge(CausalEdge(source_id="n0", target_id="n1", relation_type=CausalRelationType.SEQUENCE, strength=1.0))
        graph.add_edge(CausalEdge(source_id="n1", target_id="n2", relation_type=CausalRelationType.SEQUENCE, strength=1.0))

        engine._compute_centrality(graph)

        # Middle node should have highest centrality
        assert graph.nodes["n1"].centrality_score > 0


# ============================================================================
# PART 10: Success Criteria Tests
# ============================================================================

class TestSuccessCriteria:
    """Test that all success criteria from spec are met."""

    def test_causal_node_and_edge_dataclasses_exist(self):
        """Verify CausalNode and CausalEdge exist."""
        node = CausalNode(
            id="n1",
            operation="TEST",
            description="Test",
            line_start=1,
            line_end=1,
        )
        assert node is not None

        edge = CausalEdge(
            source_id="n1",
            target_id="n2",
            relation_type=CausalRelationType.DATA_FLOW,
            strength=0.9,
        )
        assert edge is not None

    def test_causal_graph_construction_from_vkg(self, engine):
        """Verify causal graph can be built from VKG behavioral signature."""
        fn = create_mock_function(
            "fn_test",
            "R:bal→X:out→W:bal",
            {}
        )

        graph = engine.build_causal_graph(fn, None)

        assert graph is not None
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

    def test_root_cause_identification_for_patterns(self, engine):
        """Verify root cause identification works for common patterns."""
        # Reentrancy
        fn_reentrancy = create_mock_function(
            "fn_reentrancy",
            "R:bal→X:out→W:bal",
            {"has_reentrancy_guard": False}
        )
        analysis = engine.analyze(fn_reentrancy, None)
        assert len(analysis.root_causes) > 0

        # Access control
        fn_access = create_mock_function(
            "fn_access",
            "M:own",
            {"has_access_gate": False, "writes_privileged_state": True}
        )
        analysis = engine.analyze(fn_access, None)
        assert len(analysis.root_causes) > 0

        # Oracle
        fn_oracle = create_mock_function(
            "fn_oracle",
            "R:orc",
            {"reads_oracle_price": True, "has_staleness_check": False}
        )
        analysis = engine.analyze(fn_oracle, None)
        assert len(analysis.root_causes) > 0

    def test_intervention_point_suggestions(self, engine):
        """Verify intervention points are suggested for each root cause."""
        fn = create_mock_function(
            "fn_vuln",
            "R:bal→X:out→W:bal",
            {"has_reentrancy_guard": False}
        )

        analysis = engine.analyze(fn, None)

        # Should have intervention points
        assert len(analysis.intervention_points) > 0

        # Each intervention should have required fields
        for ip in analysis.intervention_points:
            assert ip.intervention_type is not None
            assert ip.description is not None
            assert 0 <= ip.impact_score <= 1.0

    def test_generate_explanation_produces_readable_output(self, engine):
        """Verify generate_explanation produces human-readable output."""
        fn = create_mock_function(
            "fn_vuln",
            "R:bal→X:out→W:bal",
            {"has_reentrancy_guard": False}
        )

        analysis = engine.analyze(fn, None)

        # Should have explanation
        assert analysis.explanation is not None
        assert len(analysis.explanation) > 50

        # Should contain key sections
        assert "Root Cause" in analysis.explanation or "secure" in analysis.explanation.lower()


# ============================================================================
# PART 11: Ultimate Test
# ============================================================================

class TestUltimateCausalExplanation:
    """
    The ultimate test: Causal engine should explain WHY reentrancy works
    and WHAT would fix it.

    This proves the engine enables actionable vulnerability understanding.
    """

    def test_ultimate_causal_explanation(self, engine):
        """Test complete causal explanation for DAO-style reentrancy."""
        # The DAO-style vulnerable function
        dao_fn = create_mock_function(
            "fn_withdraw_dao",
            "R:bal→V:in→X:out→W:bal",
            {
                "visibility": "public",
                "has_reentrancy_guard": False,
                "state_write_after_external_call": True,
                "transfers_eth": True,
            }
        )

        analysis = engine.analyze(dao_fn, None)

        # 1. Should identify ordering as root cause
        ordering_causes = [rc for rc in analysis.root_causes if rc.cause_type == "ordering_violation"]
        assert len(ordering_causes) > 0, "Should identify ordering violation"

        # 2. Should explain the causal path
        rc = ordering_causes[0]
        assert len(rc.causal_path) >= 2, "Should have causal path"
        assert "external" in rc.description.lower() or "call" in rc.description.lower()

        # 3. Should provide fix recommendation
        assert "CEI" in rc.intervention or "before" in rc.intervention

        # 4. Should link to CWE
        assert any("841" in cwe for cwe in rc.related_cwes)

        # 5. Should have interventions
        assert len(analysis.intervention_points) > 0

        # 6. Should generate readable explanation
        assert "Root Cause" in analysis.explanation or len(analysis.root_causes) > 0
        assert len(analysis.explanation) > 200

        print("SUCCESS: Causal engine explains reentrancy")
        print(f"Root Cause: {rc.description}")
        print(f"Fix: {rc.intervention}")
        print(f"Confidence: {rc.confidence:.0%}")
