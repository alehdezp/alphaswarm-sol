"""Tests for Phase 9: Multi-Agent Verification.

This module tests all agent components:
- Base class and dataclasses
- ExplorerAgent path tracing
- PatternAgent matching
- ConstraintAgent Z3 integration
- RiskAgent scenario assessment
- AgentConsensus verdict determination
"""

import unittest
from dataclasses import dataclass
from typing import Dict, List, Any

from alphaswarm_sol.agents.base import (
    VerificationAgent,
    AgentResult,
    AgentEvidence,
    EvidenceType,
)
from alphaswarm_sol.agents.explorer import ExplorerAgent, TracedPath
from alphaswarm_sol.agents.pattern import PatternAgent, VulnerabilityPattern, PatternMatch
from alphaswarm_sol.agents.constraint import (
    ConstraintAgent,
    Constraint,
    ConstraintType,
    VulnerabilityCondition,
    VulnerabilityConditionType,
    ConstraintViolation,
    Z3_AVAILABLE,
)
from alphaswarm_sol.agents.risk import (
    RiskAgent,
    AttackAssessment,
    ScenarioType,
    Likelihood,
    Impact,
)
from alphaswarm_sol.agents.consensus import (
    AgentConsensus,
    ConsensusResult,
    Verdict,
)
from alphaswarm_sol.kg.subgraph import SubGraph, SubGraphNode, SubGraphEdge


class TestAgentEvidence(unittest.TestCase):
    """Tests for AgentEvidence dataclass."""

    def test_evidence_creation(self):
        """Test basic evidence creation."""
        evidence = AgentEvidence(
            type=EvidenceType.PATH,
            data={"path": ["A", "B", "C"]},
            description="Path from A to C",
            confidence=0.9,
            source_nodes=["A", "B", "C"],
        )
        self.assertEqual(evidence.type, EvidenceType.PATH)
        self.assertEqual(evidence.confidence, 0.9)
        self.assertEqual(len(evidence.source_nodes), 3)

    def test_evidence_serialization(self):
        """Test evidence serialization to dict."""
        evidence = AgentEvidence(
            type=EvidenceType.PATTERN,
            data={"pattern": "reentrancy"},
            description="Reentrancy pattern matched",
            confidence=0.95,
        )
        d = evidence.to_dict()
        self.assertEqual(d["type"], "pattern")
        self.assertEqual(d["description"], "Reentrancy pattern matched")

    def test_evidence_deserialization(self):
        """Test evidence deserialization from dict."""
        data = {
            "type": "constraint",
            "data": {"solver": "z3"},
            "description": "Constraint violated",
            "confidence": 0.85,
            "source_nodes": ["node1"],
            "source_edges": ["edge1"],
        }
        evidence = AgentEvidence.from_dict(data)
        self.assertEqual(evidence.type, EvidenceType.CONSTRAINT)
        self.assertEqual(evidence.confidence, 0.85)

    def test_evidence_type_enum(self):
        """Test all evidence types."""
        types = [EvidenceType.PATH, EvidenceType.PATTERN,
                 EvidenceType.CONSTRAINT, EvidenceType.SCENARIO,
                 EvidenceType.NODE, EvidenceType.EDGE, EvidenceType.PROPERTY]
        self.assertEqual(len(types), 7)

    def test_unknown_evidence_type_fallback(self):
        """Test that unknown types fall back to PROPERTY."""
        data = {"type": "unknown_type", "data": {}}
        evidence = AgentEvidence.from_dict(data)
        self.assertEqual(evidence.type, EvidenceType.PROPERTY)


class TestAgentResult(unittest.TestCase):
    """Tests for AgentResult dataclass."""

    def test_result_creation(self):
        """Test basic result creation."""
        result = AgentResult(
            agent="test_agent",
            matched=True,
            findings=["finding1", "finding2"],
            confidence=0.9,
            evidence=[],
        )
        self.assertEqual(result.agent, "test_agent")
        self.assertTrue(result.matched)
        self.assertEqual(len(result.findings), 2)

    def test_result_serialization(self):
        """Test result serialization."""
        evidence = AgentEvidence(
            type=EvidenceType.NODE,
            data={"node": "test"},
            description="Test node",
        )
        result = AgentResult(
            agent="explorer",
            matched=True,
            findings=[{"type": "path"}],
            confidence=0.85,
            evidence=[evidence],
            metadata={"runtime": 0.5},
        )
        d = result.to_dict()
        self.assertEqual(d["agent"], "explorer")
        self.assertTrue(d["matched"])
        self.assertEqual(len(d["evidence"]), 1)

    def test_result_deserialization(self):
        """Test result deserialization."""
        data = {
            "agent": "pattern",
            "matched": False,
            "findings": [],
            "confidence": 0.5,
            "evidence": [],
            "metadata": {},
        }
        result = AgentResult.from_dict(data)
        self.assertEqual(result.agent, "pattern")
        self.assertFalse(result.matched)


class TestVerificationAgentBase(unittest.TestCase):
    """Tests for VerificationAgent base class."""

    def test_abstract_class(self):
        """Test that VerificationAgent is abstract."""
        with self.assertRaises(TypeError):
            VerificationAgent()  # type: ignore

    def test_concrete_agent_implementation(self):
        """Test implementing a concrete agent."""
        class TestAgent(VerificationAgent):
            @property
            def agent_name(self) -> str:
                return "test"

            def analyze(self, subgraph: SubGraph, query: str = "") -> AgentResult:
                return AgentResult(
                    agent=self.agent_name,
                    matched=True,
                    findings=["test_finding"],
                    confidence=0.9,
                )

            def confidence(self) -> float:
                return 0.85

        agent = TestAgent()
        self.assertEqual(agent.agent_name, "test")
        self.assertEqual(agent.confidence(), 0.85)

    def test_empty_result_helper(self):
        """Test _create_empty_result helper."""
        class TestAgent(VerificationAgent):
            @property
            def agent_name(self) -> str:
                return "test"

            def analyze(self, subgraph: SubGraph, query: str = "") -> AgentResult:
                return self._create_empty_result()

            def confidence(self) -> float:
                return 0.8

        agent = TestAgent()
        result = agent.analyze(SubGraph(), "")
        self.assertFalse(result.matched)
        self.assertEqual(result.confidence, 0.4)  # 0.8 * 0.5

    def test_error_result_helper(self):
        """Test _create_error_result helper."""
        class TestAgent(VerificationAgent):
            @property
            def agent_name(self) -> str:
                return "test"

            def analyze(self, subgraph: SubGraph, query: str = "") -> AgentResult:
                return self._create_error_result("test error")

            def confidence(self) -> float:
                return 0.8

        agent = TestAgent()
        result = agent.analyze(SubGraph(), "")
        self.assertFalse(result.matched)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.metadata.get("error"), "test error")


class TestSubGraphIntegration(unittest.TestCase):
    """Test agent integration with SubGraph."""

    def setUp(self):
        """Create a test subgraph."""
        self.subgraph = SubGraph()
        self.subgraph.nodes["contract::TestContract"] = SubGraphNode(
            id="contract::TestContract",
            type="Contract",
            label="TestContract",
            relevance_score=8.0,
            is_focal=True,
        )
        self.subgraph.nodes["function::withdraw"] = SubGraphNode(
            id="function::withdraw",
            type="Function",
            label="withdraw",
            properties={
                "visibility": "public",
                "state_write_after_external_call": True,
            },
            relevance_score=9.0,
        )
        self.subgraph.edges["e1"] = SubGraphEdge(
            id="e1",
            type="HAS_FUNCTION",
            source="contract::TestContract",
            target="function::withdraw",
        )
        self.subgraph.focal_node_ids = ["contract::TestContract"]

    def test_subgraph_has_nodes(self):
        """Test that subgraph has expected nodes."""
        self.assertEqual(len(self.subgraph.nodes), 2)
        self.assertIn("function::withdraw", self.subgraph.nodes)

    def test_subgraph_has_edges(self):
        """Test that subgraph has expected edges."""
        self.assertEqual(len(self.subgraph.edges), 1)

    def test_agent_can_access_subgraph(self):
        """Test that agent can access subgraph data."""
        class SimpleAgent(VerificationAgent):
            @property
            def agent_name(self) -> str:
                return "simple"

            def analyze(self, subgraph: SubGraph, query: str = "") -> AgentResult:
                findings = []
                for node_id, node in subgraph.nodes.items():
                    if node.type == "Function":
                        if node.properties.get("state_write_after_external_call"):
                            findings.append({"node": node_id, "issue": "reentrancy"})
                return AgentResult(
                    agent=self.agent_name,
                    matched=bool(findings),
                    findings=findings,
                    confidence=0.8 if findings else 0.5,
                )

            def confidence(self) -> float:
                return 0.85

        agent = SimpleAgent()
        result = agent.analyze(self.subgraph, "find reentrancy")
        self.assertTrue(result.matched)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.findings[0]["issue"], "reentrancy")


class TestExplorerAgent(unittest.TestCase):
    """Tests for ExplorerAgent."""

    def setUp(self):
        """Create test subgraph with callable paths."""
        self.subgraph = SubGraph()

        # Contract node
        self.subgraph.nodes["contract::TestContract"] = SubGraphNode(
            id="contract::TestContract",
            type="Contract",
            label="TestContract",
            relevance_score=8.0,
            is_focal=True,
        )

        # Public withdraw function with reentrancy risk
        self.subgraph.nodes["function::withdraw"] = SubGraphNode(
            id="function::withdraw",
            type="Function",
            label="withdraw",
            properties={
                "visibility": "public",
                "state_mutability": "nonpayable",
                "state_write_after_external_call": True,
                "has_external_calls": True,
                "writes_privileged_state": True,
                "semantic_ops": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            },
            relevance_score=9.0,
        )

        # Internal transfer function
        self.subgraph.nodes["function::_transfer"] = SubGraphNode(
            id="function::_transfer",
            type="Function",
            label="_transfer",
            properties={
                "visibility": "internal",
                "state_mutability": "nonpayable",
                "semantic_ops": ["WRITES_USER_BALANCE"],
            },
            relevance_score=7.0,
        )

        # Public deposit function (safe)
        self.subgraph.nodes["function::deposit"] = SubGraphNode(
            id="function::deposit",
            type="Function",
            label="deposit",
            properties={
                "visibility": "public",
                "state_mutability": "payable",
                "has_access_gate": False,
                "semantic_ops": ["RECEIVES_VALUE_IN"],
            },
            relevance_score=6.0,
        )

        # View function (should not be entry point)
        self.subgraph.nodes["function::getBalance"] = SubGraphNode(
            id="function::getBalance",
            type="Function",
            label="getBalance",
            properties={
                "visibility": "public",
                "state_mutability": "view",
            },
            relevance_score=3.0,
        )

        # Edges
        self.subgraph.edges["e1"] = SubGraphEdge(
            id="e1",
            type="HAS_FUNCTION",
            source="contract::TestContract",
            target="function::withdraw",
        )
        self.subgraph.edges["e2"] = SubGraphEdge(
            id="e2",
            type="CALLS",
            source="function::withdraw",
            target="function::_transfer",
        )
        self.subgraph.edges["e3"] = SubGraphEdge(
            id="e3",
            type="HAS_FUNCTION",
            source="contract::TestContract",
            target="function::deposit",
        )

        self.subgraph.focal_node_ids = ["contract::TestContract"]

    def test_agent_creation(self):
        """Test creating an explorer agent."""
        agent = ExplorerAgent()
        self.assertEqual(agent.agent_name, "explorer")
        self.assertEqual(agent.confidence(), 0.85)

    def test_find_entry_points(self):
        """Test finding entry points."""
        agent = ExplorerAgent()
        entry_points = agent._find_entry_points(self.subgraph)

        # Should find withdraw and deposit (public, not view)
        self.assertIn("function::withdraw", entry_points)
        self.assertIn("function::deposit", entry_points)
        # Should NOT find internal or view functions
        self.assertNotIn("function::_transfer", entry_points)
        self.assertNotIn("function::getBalance", entry_points)

    def test_trace_paths(self):
        """Test tracing paths from entry points."""
        agent = ExplorerAgent()
        paths = agent._trace_paths_from("function::withdraw", self.subgraph)

        # Should find path from withdraw -> _transfer
        self.assertGreater(len(paths), 0)

        # At least one path should include both functions
        has_full_path = any(
            "function::_transfer" in p.node_ids
            for p in paths
        )
        self.assertTrue(has_full_path)

    def test_critical_path_detection(self):
        """Test detection of critical paths."""
        agent = ExplorerAgent()
        result = agent.analyze(self.subgraph, "find reentrancy")

        # Should find critical paths
        self.assertTrue(result.matched)
        self.assertGreater(len(result.findings), 0)

        # Metadata should include counts
        self.assertIn("critical_paths_found", result.metadata)
        self.assertGreater(result.metadata["critical_paths_found"], 0)

    def test_path_touches_critical_state(self):
        """Test that paths with critical state access are flagged."""
        agent = ExplorerAgent()
        result = agent.analyze(self.subgraph, "")

        # Find path from withdraw
        withdraw_paths = [
            f for f in result.findings
            if "function::withdraw" in f.get("node_ids", [])
        ]
        self.assertGreater(len(withdraw_paths), 0)

        # Should be flagged as touching critical state
        path = withdraw_paths[0]
        self.assertTrue(path.get("touches_critical_state"))

    def test_path_with_value_transfer(self):
        """Test detection of value transfer in paths."""
        agent = ExplorerAgent()
        result = agent.analyze(self.subgraph, "")

        # Paths from withdraw should have value transfer
        for finding in result.findings:
            if "function::withdraw" in finding.get("node_ids", []):
                self.assertTrue(finding.get("has_value_transfer"))

    def test_empty_subgraph(self):
        """Test handling of empty subgraph."""
        agent = ExplorerAgent()
        empty_subgraph = SubGraph()
        result = agent.analyze(empty_subgraph, "")

        self.assertFalse(result.matched)
        self.assertEqual(len(result.findings), 0)

    def test_no_entry_points(self):
        """Test handling of subgraph with no entry points."""
        agent = ExplorerAgent()
        subgraph = SubGraph()
        subgraph.nodes["function::internal"] = SubGraphNode(
            id="function::internal",
            type="Function",
            label="internal",
            properties={"visibility": "internal"},
        )
        result = agent.analyze(subgraph, "")

        self.assertFalse(result.matched)

    def test_evidence_creation(self):
        """Test that evidence is created for critical paths."""
        agent = ExplorerAgent()
        result = agent.analyze(self.subgraph, "")

        self.assertGreater(len(result.evidence), 0)

        for ev in result.evidence:
            self.assertEqual(ev.type, EvidenceType.PATH)
            self.assertIn("path_id", ev.data)
            self.assertGreater(len(ev.source_nodes), 0)


class TestTracedPath(unittest.TestCase):
    """Tests for TracedPath dataclass."""

    def test_traced_path_creation(self):
        """Test creating a traced path."""
        path = TracedPath(
            path_id="path:1234",
            node_ids=["fn1", "fn2"],
            operations=["TRANSFERS_VALUE_OUT"],
            touches_critical_state=True,
            has_external_calls=True,
            has_value_transfer=True,
            risk_score=5.0,
            entry_point="fn1",
        )
        self.assertEqual(path.path_id, "path:1234")
        self.assertTrue(path.touches_critical_state)

    def test_traced_path_serialization(self):
        """Test serializing a traced path."""
        path = TracedPath(
            path_id="path:5678",
            node_ids=["fn1", "fn2", "fn3"],
            operations=["WRITES_USER_BALANCE"],
            risk_score=3.5,
            entry_point="fn1",
        )
        d = path.to_dict()
        self.assertEqual(d["path_id"], "path:5678")
        self.assertEqual(len(d["node_ids"]), 3)
        self.assertEqual(d["risk_score"], 3.5)


class TestPatternAgent(unittest.TestCase):
    """Tests for PatternAgent."""

    def setUp(self):
        """Create test subgraph with vulnerable functions."""
        self.subgraph = SubGraph()

        # Reentrancy vulnerable function
        self.subgraph.nodes["function::withdraw"] = SubGraphNode(
            id="function::withdraw",
            type="Function",
            label="withdraw",
            properties={
                "visibility": "public",
                "state_write_after_external_call": True,
                "has_reentrancy_guard": False,
                "has_external_calls": True,
                "semantic_ops": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            },
        )

        # Missing access control function
        self.subgraph.nodes["function::setOwner"] = SubGraphNode(
            id="function::setOwner",
            type="Function",
            label="setOwner",
            properties={
                "visibility": "public",
                "writes_privileged_state": True,
                "has_access_gate": False,
                "semantic_ops": ["MODIFIES_OWNER"],
            },
        )

        # Safe function (has access control)
        self.subgraph.nodes["function::protectedSet"] = SubGraphNode(
            id="function::protectedSet",
            type="Function",
            label="protectedSet",
            properties={
                "visibility": "public",
                "writes_privileged_state": True,
                "has_access_gate": True,
                "semantic_ops": ["MODIFIES_CRITICAL_STATE"],
            },
        )

        # Unsafe delegatecall
        self.subgraph.nodes["function::execute"] = SubGraphNode(
            id="function::execute",
            type="Function",
            label="execute",
            properties={
                "visibility": "external",
                "uses_delegatecall": True,
                "has_access_gate": False,
                "semantic_ops": ["CALLS_UNTRUSTED"],
            },
        )

    def test_agent_creation(self):
        """Test creating a pattern agent."""
        agent = PatternAgent()
        self.assertEqual(agent.agent_name, "pattern")
        self.assertEqual(agent.confidence(), 0.90)

    def test_builtin_patterns_exist(self):
        """Test that builtin patterns are loaded."""
        agent = PatternAgent()
        self.assertGreater(len(agent.patterns), 0)

    def test_reentrancy_detection(self):
        """Test detection of reentrancy pattern."""
        agent = PatternAgent()
        result = agent.analyze(self.subgraph, "")

        # Should detect reentrancy in withdraw
        reentrancy_matches = [
            f for f in result.findings
            if "reentrancy" in f.get("pattern_id", "").lower()
        ]
        self.assertGreater(len(reentrancy_matches), 0)

        # Should match the withdraw function
        node_ids = [m["matched_node_id"] for m in reentrancy_matches]
        self.assertIn("function::withdraw", node_ids)

    def test_missing_access_control_detection(self):
        """Test detection of missing access control."""
        agent = PatternAgent()
        result = agent.analyze(self.subgraph, "")

        # Should detect missing access control in setOwner
        access_matches = [
            f for f in result.findings
            if "access" in f.get("pattern_id", "").lower()
        ]
        self.assertGreater(len(access_matches), 0)

    def test_protected_function_not_matched(self):
        """Test that protected function is not matched."""
        agent = PatternAgent()
        result = agent.analyze(self.subgraph, "")

        # protectedSet should NOT be matched (has access gate)
        matched_nodes = [f.get("matched_node_id") for f in result.findings]
        self.assertNotIn("function::protectedSet", matched_nodes)

    def test_delegatecall_detection(self):
        """Test detection of unprotected delegatecall."""
        agent = PatternAgent()
        result = agent.analyze(self.subgraph, "")

        delegatecall_matches = [
            f for f in result.findings
            if "delegatecall" in f.get("pattern_id", "").lower()
        ]
        self.assertGreater(len(delegatecall_matches), 0)

    def test_custom_pattern(self):
        """Test adding and matching custom patterns."""
        custom_pattern = VulnerabilityPattern(
            id="custom-test",
            name="Custom Test Pattern",
            severity="low",
            match_all=[{"property": "uses_delegatecall", "value": True}],
        )

        agent = PatternAgent(patterns=[custom_pattern])
        result = agent.analyze(self.subgraph, "")

        # Should match execute function
        self.assertTrue(result.matched)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.findings[0]["pattern_id"], "custom-test")

    def test_empty_subgraph(self):
        """Test handling of empty subgraph."""
        agent = PatternAgent()
        empty_subgraph = SubGraph()
        result = agent.analyze(empty_subgraph, "")

        self.assertFalse(result.matched)
        self.assertEqual(len(result.findings), 0)

    def test_pattern_severity_ordering(self):
        """Test that results are ordered by severity."""
        agent = PatternAgent()
        result = agent.analyze(self.subgraph, "")

        if len(result.findings) >= 2:
            severities = [f.get("severity") for f in result.findings]
            severity_order = ["critical", "high", "medium", "low", "info"]

            # Check that severities are non-increasing
            for i in range(len(severities) - 1):
                idx_curr = severity_order.index(severities[i]) if severities[i] in severity_order else 2
                idx_next = severity_order.index(severities[i + 1]) if severities[i + 1] in severity_order else 2
                self.assertLessEqual(idx_curr, idx_next)

    def test_condition_operators(self):
        """Test various condition operators."""
        agent = PatternAgent()

        # Test "in" operator
        pattern_in = VulnerabilityPattern(
            id="test-in",
            name="Test In",
            match_all=[
                {"property": "visibility", "value": ["public", "external"], "op": "in"},
            ],
        )
        match = agent._match_pattern(
            pattern_in, self.subgraph.nodes["function::withdraw"]
        )
        self.assertIsNotNone(match)

        # Test "ne" operator
        pattern_ne = VulnerabilityPattern(
            id="test-ne",
            name="Test NE",
            match_all=[
                {"property": "visibility", "value": "private", "op": "ne"},
            ],
        )
        match = agent._match_pattern(
            pattern_ne, self.subgraph.nodes["function::withdraw"]
        )
        self.assertIsNotNone(match)

    def test_evidence_creation(self):
        """Test that evidence is created for matches."""
        agent = PatternAgent()
        result = agent.analyze(self.subgraph, "")

        self.assertGreater(len(result.evidence), 0)

        for ev in result.evidence:
            self.assertEqual(ev.type, EvidenceType.PATTERN)
            self.assertIn("pattern_id", ev.data)

    def test_metadata_contents(self):
        """Test metadata contains expected fields."""
        agent = PatternAgent()
        result = agent.analyze(self.subgraph, "")

        self.assertIn("patterns_evaluated", result.metadata)
        self.assertIn("nodes_evaluated", result.metadata)
        self.assertIn("matches_found", result.metadata)
        self.assertIn("severity_distribution", result.metadata)


class TestVulnerabilityPattern(unittest.TestCase):
    """Tests for VulnerabilityPattern dataclass."""

    def test_pattern_creation(self):
        """Test creating a vulnerability pattern."""
        pattern = VulnerabilityPattern(
            id="test-pattern",
            name="Test Pattern",
            severity="high",
            description="A test pattern",
            match_all=[{"property": "test", "value": True}],
        )
        self.assertEqual(pattern.id, "test-pattern")
        self.assertEqual(pattern.severity, "high")

    def test_pattern_serialization(self):
        """Test serializing a pattern."""
        pattern = VulnerabilityPattern(
            id="test-pattern",
            name="Test Pattern",
            ops_required=["TRANSFERS_VALUE_OUT"],
        )
        d = pattern.to_dict()
        self.assertEqual(d["id"], "test-pattern")
        self.assertIn("TRANSFERS_VALUE_OUT", d["ops_required"])


class TestPatternMatch(unittest.TestCase):
    """Tests for PatternMatch dataclass."""

    def test_pattern_match_creation(self):
        """Test creating a pattern match."""
        pattern = VulnerabilityPattern(id="p1", name="P1")
        match = PatternMatch(
            pattern=pattern,
            matched_node_id="fn::test",
            matched_node_label="test",
            severity="high",
            confidence=0.85,
        )
        self.assertEqual(match.matched_node_id, "fn::test")
        self.assertEqual(match.confidence, 0.85)

    def test_pattern_match_serialization(self):
        """Test serializing a pattern match."""
        pattern = VulnerabilityPattern(id="p1", name="P1")
        match = PatternMatch(
            pattern=pattern,
            matched_node_id="fn::test",
            matched_node_label="test",
            severity="medium",
        )
        d = match.to_dict()
        self.assertEqual(d["pattern_id"], "p1")
        self.assertEqual(d["severity"], "medium")


class TestConstraintAgent(unittest.TestCase):
    """Tests for ConstraintAgent."""

    def setUp(self):
        """Create test subgraph with various vulnerability patterns."""
        self.subgraph = SubGraph()

        # Reentrancy vulnerable function
        self.subgraph.nodes["function::withdraw"] = SubGraphNode(
            id="function::withdraw",
            type="Function",
            label="withdraw",
            properties={
                "visibility": "public",
                "has_external_calls": True,
                "has_reentrancy_guard": False,
                "state_write_after_external_call": True,
                "semantic_ops": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            },
        )

        # Missing access control
        self.subgraph.nodes["function::setOwner"] = SubGraphNode(
            id="function::setOwner",
            type="Function",
            label="setOwner",
            properties={
                "visibility": "public",
                "writes_privileged_state": True,
                "has_access_gate": False,
            },
        )

        # Safe function (protected)
        self.subgraph.nodes["function::protectedWithdraw"] = SubGraphNode(
            id="function::protectedWithdraw",
            type="Function",
            label="protectedWithdraw",
            properties={
                "visibility": "public",
                "has_external_calls": True,
                "has_reentrancy_guard": True,
                "has_access_gate": True,
                "checks_balance_before_transfer": True,
                "semantic_ops": ["TRANSFERS_VALUE_OUT"],
            },
        )

    def test_agent_creation(self):
        """Test creating a constraint agent."""
        agent = ConstraintAgent()
        self.assertEqual(agent.agent_name, "constraint")

    def test_z3_availability_reflected(self):
        """Test that Z3 availability is reflected in confidence."""
        agent = ConstraintAgent()
        if Z3_AVAILABLE:
            self.assertEqual(agent.confidence(), 0.95)
        else:
            self.assertEqual(agent.confidence(), 0.70)

    def test_reentrancy_detection(self):
        """Test detection of reentrancy vulnerability."""
        agent = ConstraintAgent()
        result = agent.analyze(self.subgraph, "")

        # Should detect reentrancy
        reentrancy_violations = [
            f for f in result.findings
            if "reentrancy" in f.get("condition", {}).get("id", "").lower()
        ]
        self.assertGreater(len(reentrancy_violations), 0)

    def test_unauthorized_access_detection(self):
        """Test detection of unauthorized access."""
        agent = ConstraintAgent()
        result = agent.analyze(self.subgraph, "")

        # Should detect unauthorized access
        access_violations = [
            f for f in result.findings
            if "unauthorized" in f.get("condition", {}).get("id", "").lower()
        ]
        self.assertGreater(len(access_violations), 0)

    def test_constraint_extraction(self):
        """Test constraint extraction from nodes."""
        agent = ConstraintAgent()
        constraints = agent._extract_constraints(self.subgraph)

        # Should extract constraints from protected function
        constraint_types = [c.type for c in constraints]
        # Protected function has access gate and reentrancy guard
        self.assertIn(ConstraintType.ACCESS_CONTROL, constraint_types)
        self.assertIn(ConstraintType.REENTRANCY_GUARD, constraint_types)

    def test_empty_subgraph(self):
        """Test handling of empty subgraph."""
        agent = ConstraintAgent()
        empty_subgraph = SubGraph()
        result = agent.analyze(empty_subgraph, "")

        self.assertFalse(result.matched)
        self.assertEqual(len(result.findings), 0)

    def test_no_vulnerabilities(self):
        """Test subgraph with no vulnerabilities."""
        agent = ConstraintAgent()
        safe_subgraph = SubGraph()
        safe_subgraph.nodes["function::safe"] = SubGraphNode(
            id="function::safe",
            type="Function",
            label="safe",
            properties={
                "visibility": "public",
                "has_access_gate": True,
                "has_reentrancy_guard": True,
            },
        )
        result = agent.analyze(safe_subgraph, "")

        # No violations should be found
        self.assertFalse(result.matched)

    def test_metadata_contents(self):
        """Test metadata contains expected fields."""
        agent = ConstraintAgent()
        result = agent.analyze(self.subgraph, "")

        self.assertIn("z3_available", result.metadata)
        self.assertIn("constraints_extracted", result.metadata)
        self.assertIn("conditions_checked", result.metadata)
        self.assertIn("violations_found", result.metadata)

    def test_evidence_creation(self):
        """Test that evidence is created for violations."""
        agent = ConstraintAgent()
        result = agent.analyze(self.subgraph, "")

        if result.matched:
            self.assertGreater(len(result.evidence), 0)
            for ev in result.evidence:
                self.assertEqual(ev.type, EvidenceType.CONSTRAINT)


class TestConstraint(unittest.TestCase):
    """Tests for Constraint dataclass."""

    def test_constraint_creation(self):
        """Test creating a constraint."""
        constraint = Constraint(
            id="test-constraint",
            type=ConstraintType.ACCESS_CONTROL,
            description="Test access control",
            source_node="function::test",
            expression="caller == owner",
        )
        self.assertEqual(constraint.id, "test-constraint")
        self.assertEqual(constraint.type, ConstraintType.ACCESS_CONTROL)

    def test_constraint_serialization(self):
        """Test serializing a constraint."""
        constraint = Constraint(
            id="test-constraint",
            type=ConstraintType.BALANCE_CHECK,
            description="Balance check",
            source_node="fn::test",
        )
        d = constraint.to_dict()
        self.assertEqual(d["type"], "balance_check")


class TestVulnerabilityCondition(unittest.TestCase):
    """Tests for VulnerabilityCondition dataclass."""

    def test_condition_creation(self):
        """Test creating a vulnerability condition."""
        condition = VulnerabilityCondition(
            id="test-condition",
            type=VulnerabilityConditionType.REENTRANCY_POSSIBLE,
            description="Test reentrancy",
            severity="critical",
        )
        self.assertEqual(condition.id, "test-condition")
        self.assertEqual(condition.severity, "critical")

    def test_condition_serialization(self):
        """Test serializing a condition."""
        condition = VulnerabilityCondition(
            id="test-condition",
            type=VulnerabilityConditionType.UNAUTHORIZED_ACCESS,
            description="Unauthorized access",
            preconditions=["no_auth"],
        )
        d = condition.to_dict()
        self.assertEqual(d["type"], "unauthorized_access")
        self.assertIn("no_auth", d["preconditions"])


class TestConstraintViolation(unittest.TestCase):
    """Tests for ConstraintViolation dataclass."""

    def test_violation_creation(self):
        """Test creating a constraint violation."""
        condition = VulnerabilityCondition(
            id="v1",
            type=VulnerabilityConditionType.BALANCE_MANIPULATION,
            description="Balance drain",
        )
        violation = ConstraintViolation(
            condition=condition,
            satisfied=True,
            confidence=0.9,
        )
        self.assertTrue(violation.satisfied)
        self.assertEqual(violation.confidence, 0.9)

    def test_violation_serialization(self):
        """Test serializing a violation."""
        condition = VulnerabilityCondition(
            id="v1",
            type=VulnerabilityConditionType.INVARIANT_VIOLATION,
            description="Invariant broken",
        )
        violation = ConstraintViolation(
            condition=condition,
            satisfied=True,
            model={"x": 5},
        )
        d = violation.to_dict()
        self.assertTrue(d["satisfied"])
        self.assertEqual(d["model"], {"x": 5})


class TestRiskAgent(unittest.TestCase):
    """Tests for RiskAgent."""

    def setUp(self):
        """Create test subgraph with various risk scenarios."""
        self.subgraph = SubGraph()

        # Reentrancy vulnerable function
        self.subgraph.nodes["function::withdraw"] = SubGraphNode(
            id="function::withdraw",
            type="Function",
            label="withdraw",
            properties={
                "visibility": "public",
                "has_external_calls": True,
                "has_reentrancy_guard": False,
                "state_write_after_external_call": True,
                "semantic_ops": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            },
        )

        # Privilege escalation vulnerable
        self.subgraph.nodes["function::setOwner"] = SubGraphNode(
            id="function::setOwner",
            type="Function",
            label="setOwner",
            properties={
                "visibility": "public",
                "writes_privileged_state": True,
                "has_access_gate": False,
            },
        )

        # Oracle manipulation vulnerable
        self.subgraph.nodes["function::swap"] = SubGraphNode(
            id="function::swap",
            type="Function",
            label="swap",
            properties={
                "visibility": "public",
                "reads_oracle_price": True,
                "has_staleness_check": False,
                "swap_like": True,
                "has_deadline_check": False,
            },
        )

        # DoS vulnerable
        self.subgraph.nodes["function::distribute"] = SubGraphNode(
            id="function::distribute",
            type="Function",
            label="distribute",
            properties={
                "visibility": "public",
                "has_unbounded_loop": True,
            },
        )

        # Safe function
        self.subgraph.nodes["function::safeTransfer"] = SubGraphNode(
            id="function::safeTransfer",
            type="Function",
            label="safeTransfer",
            properties={
                "visibility": "public",
                "has_access_gate": True,
                "has_reentrancy_guard": True,
                "checks_balance_before_transfer": True,
            },
        )

    def test_agent_creation(self):
        """Test creating a risk agent."""
        agent = RiskAgent()
        self.assertEqual(agent.agent_name, "risk")
        self.assertEqual(agent.confidence(), 0.80)

    def test_reentrancy_scenario_generation(self):
        """Test generation of reentrancy attack scenario."""
        agent = RiskAgent()
        result = agent.analyze(self.subgraph, "")

        # Should generate reentrancy scenario
        reentrancy_findings = [
            f for f in result.findings
            if f.get("scenario_type") == "reentrancy"
        ]
        self.assertGreater(len(reentrancy_findings), 0)

    def test_privilege_escalation_scenario(self):
        """Test generation of privilege escalation scenario."""
        agent = RiskAgent()
        result = agent.analyze(self.subgraph, "")

        # Should generate privilege escalation scenario
        priv_findings = [
            f for f in result.findings
            if f.get("scenario_type") == "privilege_escalation"
        ]
        self.assertGreater(len(priv_findings), 0)

    def test_oracle_manipulation_scenario(self):
        """Test generation of oracle manipulation scenario."""
        # Oracle scenarios have lower exploitability, use low threshold
        agent = RiskAgent(exploitability_threshold=1.0)
        result = agent.analyze(self.subgraph, "")

        # Should generate oracle manipulation scenario
        oracle_findings = [
            f for f in result.findings
            if f.get("scenario_type") == "oracle_manipulation"
        ]
        self.assertGreater(len(oracle_findings), 0)

    def test_dos_scenario(self):
        """Test generation of DoS scenario."""
        # DoS scenarios have lower exploitability, use low threshold
        agent = RiskAgent(exploitability_threshold=1.0)
        result = agent.analyze(self.subgraph, "")

        # Should generate DoS scenario
        dos_findings = [
            f for f in result.findings
            if f.get("scenario_type") == "denial_of_service"
        ]
        self.assertGreater(len(dos_findings), 0)

    def test_exploitability_scoring(self):
        """Test that exploitability scores are computed."""
        agent = RiskAgent()
        result = agent.analyze(self.subgraph, "")

        for finding in result.findings:
            self.assertIn("exploitability_score", finding)
            self.assertGreaterEqual(finding["exploitability_score"], 0.0)

    def test_attack_steps_included(self):
        """Test that attack steps are included in scenarios."""
        agent = RiskAgent()
        result = agent.analyze(self.subgraph, "")

        for finding in result.findings:
            self.assertIn("attack_steps", finding)
            self.assertGreater(len(finding["attack_steps"]), 0)

    def test_mitigation_included(self):
        """Test that mitigation is included in scenarios."""
        agent = RiskAgent()
        result = agent.analyze(self.subgraph, "")

        for finding in result.findings:
            self.assertIn("mitigation", finding)
            self.assertNotEqual(finding["mitigation"], "")

    def test_empty_subgraph(self):
        """Test handling of empty subgraph."""
        agent = RiskAgent()
        empty_subgraph = SubGraph()
        result = agent.analyze(empty_subgraph, "")

        self.assertFalse(result.matched)
        self.assertEqual(len(result.findings), 0)

    def test_safe_function_not_flagged(self):
        """Test that safe function doesn't generate high-risk scenarios."""
        agent = RiskAgent()
        safe_subgraph = SubGraph()
        safe_subgraph.nodes["function::safe"] = SubGraphNode(
            id="function::safe",
            type="Function",
            label="safe",
            properties={
                "visibility": "public",
                "has_access_gate": True,
                "has_reentrancy_guard": True,
            },
        )
        result = agent.analyze(safe_subgraph, "")

        # Should not find high-risk scenarios
        self.assertFalse(result.matched)

    def test_evidence_creation(self):
        """Test that evidence is created for high-risk scenarios."""
        agent = RiskAgent()
        result = agent.analyze(self.subgraph, "")

        if result.matched:
            self.assertGreater(len(result.evidence), 0)
            for ev in result.evidence:
                self.assertEqual(ev.type, EvidenceType.SCENARIO)

    def test_metadata_contents(self):
        """Test metadata contains expected fields."""
        agent = RiskAgent()
        result = agent.analyze(self.subgraph, "")

        self.assertIn("scenarios_generated", result.metadata)
        self.assertIn("high_risk_count", result.metadata)
        self.assertIn("max_exploitability", result.metadata)

    def test_custom_threshold(self):
        """Test custom exploitability threshold."""
        # Very high threshold - should find nothing
        agent = RiskAgent(exploitability_threshold=100.0)
        result = agent.analyze(self.subgraph, "")
        self.assertFalse(result.matched)

        # Very low threshold - should find more
        agent2 = RiskAgent(exploitability_threshold=0.1)
        result2 = agent2.analyze(self.subgraph, "")
        self.assertTrue(result2.matched)


class TestAttackAssessment(unittest.TestCase):
    """Tests for AttackAssessment dataclass."""

    def test_assessment_creation(self):
        """Test creating an attack assessment."""
        assessment = AttackAssessment(
            id="test-1",
            scenario_type=ScenarioType.REENTRANCY,
            description="Test reentrancy",
            likelihood=Likelihood.HIGH,
            impact=Impact.CRITICAL,
            exploitability_score=8.5,
        )
        self.assertEqual(assessment.id, "test-1")
        self.assertEqual(assessment.scenario_type, ScenarioType.REENTRANCY)
        self.assertEqual(assessment.exploitability_score, 8.5)

    def test_assessment_serialization(self):
        """Test serializing an assessment."""
        assessment = AttackAssessment(
            id="test-2",
            scenario_type=ScenarioType.FLASH_LOAN,
            description="Flash loan attack",
            affected_functions=["fn1", "fn2"],
            attack_steps=["Step 1", "Step 2"],
        )
        d = assessment.to_dict()
        self.assertEqual(d["scenario_type"], "flash_loan")
        self.assertEqual(len(d["affected_functions"]), 2)
        self.assertEqual(len(d["attack_steps"]), 2)


class TestScenarioEnums(unittest.TestCase):
    """Tests for scenario-related enums."""

    def test_scenario_types(self):
        """Test all scenario types exist."""
        types = [
            ScenarioType.REENTRANCY,
            ScenarioType.FLASH_LOAN,
            ScenarioType.PRIVILEGE_ESCALATION,
            ScenarioType.ORACLE_MANIPULATION,
            ScenarioType.FRONT_RUNNING,
            ScenarioType.VALUE_EXTRACTION,
            ScenarioType.ACCESS_CONTROL_BYPASS,
            ScenarioType.DENIAL_OF_SERVICE,
        ]
        self.assertEqual(len(types), 8)

    def test_likelihood_levels(self):
        """Test likelihood levels."""
        levels = [Likelihood.LOW, Likelihood.MEDIUM, Likelihood.HIGH]
        self.assertEqual(len(levels), 3)

    def test_impact_levels(self):
        """Test impact levels."""
        levels = [Impact.LOW, Impact.MEDIUM, Impact.HIGH, Impact.CRITICAL]
        self.assertEqual(len(levels), 4)


class TestAgentConsensus(unittest.TestCase):
    """Tests for AgentConsensus."""

    def setUp(self):
        """Create test subgraph with vulnerabilities."""
        self.subgraph = SubGraph()

        # Reentrancy vulnerable function
        self.subgraph.nodes["function::withdraw"] = SubGraphNode(
            id="function::withdraw",
            type="Function",
            label="withdraw",
            properties={
                "visibility": "public",
                "state_mutability": "nonpayable",
                "has_external_calls": True,
                "has_reentrancy_guard": False,
                "state_write_after_external_call": True,
                "writes_privileged_state": True,
                "has_access_gate": False,
                "semantic_ops": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            },
        )

        # Safe function
        self.subgraph.nodes["function::safe"] = SubGraphNode(
            id="function::safe",
            type="Function",
            label="safe",
            properties={
                "visibility": "public",
                "has_access_gate": True,
                "has_reentrancy_guard": True,
            },
        )

    def test_consensus_creation(self):
        """Test creating a consensus system."""
        agents = [ExplorerAgent(), PatternAgent()]
        consensus = AgentConsensus(agents)
        self.assertEqual(len(consensus.agents), 2)

    def test_consensus_all_agree(self):
        """Test consensus when all agents agree on vulnerability."""
        agents = [
            ExplorerAgent(),
            PatternAgent(),
            ConstraintAgent(),
            RiskAgent(exploitability_threshold=1.0),
        ]
        consensus = AgentConsensus(agents)
        result = consensus.verify(self.subgraph, "")

        # All agents should find something, expect HIGH_RISK
        self.assertEqual(result.agents_agreed, 4)
        self.assertEqual(result.total_agents, 4)
        self.assertEqual(result.verdict, Verdict.HIGH_RISK)

    def test_consensus_partial_agreement(self):
        """Test consensus with partial agreement."""
        # Create a custom agent that always returns no findings
        class NeverMatchAgent(VerificationAgent):
            @property
            def agent_name(self) -> str:
                return "never_match"

            def analyze(self, subgraph, query=""):
                return self._create_empty_result()

            def confidence(self) -> float:
                return 0.9

        agents = [ExplorerAgent(), PatternAgent(), NeverMatchAgent(), NeverMatchAgent()]
        consensus = AgentConsensus(agents)
        result = consensus.verify(self.subgraph, "")

        # 2/4 agents agree -> MEDIUM_RISK
        self.assertEqual(result.agents_agreed, 2)
        self.assertEqual(result.verdict, Verdict.MEDIUM_RISK)

    def test_consensus_single_agent_finding(self):
        """Test LOW_RISK when only one agent finds issues."""
        class AlwaysMatchAgent(VerificationAgent):
            @property
            def agent_name(self) -> str:
                return "always_match"

            def analyze(self, subgraph, query=""):
                return AgentResult(
                    agent=self.agent_name,
                    matched=True,
                    findings=["test"],
                    confidence=0.8,
                )

            def confidence(self) -> float:
                return 0.8

        class NeverMatchAgent(VerificationAgent):
            @property
            def agent_name(self) -> str:
                return "never_match"

            def analyze(self, subgraph, query=""):
                return self._create_empty_result()

            def confidence(self) -> float:
                return 0.9

        agents = [
            AlwaysMatchAgent(),
            NeverMatchAgent(),
            NeverMatchAgent(),
            NeverMatchAgent(),
        ]
        consensus = AgentConsensus(agents)
        result = consensus.verify(self.subgraph, "")

        # 1/4 agents agree -> LOW_RISK
        self.assertEqual(result.agents_agreed, 1)
        self.assertEqual(result.verdict, Verdict.LOW_RISK)

    def test_consensus_no_findings(self):
        """Test LIKELY_SAFE when no agents find issues."""
        safe_subgraph = SubGraph()
        safe_subgraph.nodes["function::safe"] = SubGraphNode(
            id="function::safe",
            type="Function",
            label="safe",
            properties={
                "visibility": "public",
                "has_access_gate": True,
                "has_reentrancy_guard": True,
            },
        )

        agents = [ExplorerAgent(), PatternAgent()]
        consensus = AgentConsensus(agents)
        result = consensus.verify(safe_subgraph, "")

        self.assertEqual(result.agents_agreed, 0)
        self.assertEqual(result.verdict, Verdict.LIKELY_SAFE)

    def test_evidence_merging(self):
        """Test that evidence is merged from all agents."""
        agents = [ExplorerAgent(), PatternAgent()]
        consensus = AgentConsensus(agents)
        result = consensus.verify(self.subgraph, "")

        # Should have evidence from multiple agents
        self.assertGreater(len(result.evidence), 0)

    def test_summary_generation(self):
        """Test that summary is generated."""
        agents = [ExplorerAgent(), PatternAgent()]
        consensus = AgentConsensus(agents)
        result = consensus.verify(self.subgraph, "")

        self.assertNotEqual(result.summary, "")
        self.assertIn(str(result.agents_agreed), result.summary)

    def test_add_remove_agent(self):
        """Test adding and removing agents."""
        consensus = AgentConsensus([ExplorerAgent()])
        self.assertEqual(len(consensus.agents), 1)

        consensus.add_agent(PatternAgent())
        self.assertEqual(len(consensus.agents), 2)

        removed = consensus.remove_agent("explorer")
        self.assertTrue(removed)
        self.assertEqual(len(consensus.agents), 1)

        # Try to remove non-existent agent
        removed = consensus.remove_agent("nonexistent")
        self.assertFalse(removed)

    def test_list_agents(self):
        """Test listing agent names."""
        agents = [ExplorerAgent(), PatternAgent(), ConstraintAgent()]
        consensus = AgentConsensus(agents)
        names = consensus.list_agents()

        self.assertIn("explorer", names)
        self.assertIn("pattern", names)
        self.assertIn("constraint", names)

    def test_custom_thresholds(self):
        """Test custom verdict thresholds."""
        class AlwaysMatchAgent(VerificationAgent):
            @property
            def agent_name(self) -> str:
                return "always_match"

            def analyze(self, subgraph, query=""):
                return AgentResult(agent=self.agent_name, matched=True, findings=["x"])

            def confidence(self) -> float:
                return 0.8

        class NeverMatchAgent(VerificationAgent):
            @property
            def agent_name(self) -> str:
                return "never_match"

            def analyze(self, subgraph, query=""):
                return self._create_empty_result()

            def confidence(self) -> float:
                return 0.9

        # With default thresholds, 50% agreement = MEDIUM_RISK
        agents = [AlwaysMatchAgent(), NeverMatchAgent()]
        consensus = AgentConsensus(agents)
        result = consensus.verify(self.subgraph, "")
        self.assertEqual(result.verdict, Verdict.MEDIUM_RISK)

        # With high threshold, 50% agreement = LOW_RISK
        consensus2 = AgentConsensus(
            agents, high_risk_threshold=0.9, medium_risk_threshold=0.7
        )
        result2 = consensus2.verify(self.subgraph, "")
        self.assertEqual(result2.verdict, Verdict.LOW_RISK)

    def test_empty_agents(self):
        """Test consensus with no agents."""
        consensus = AgentConsensus([])
        result = consensus.verify(self.subgraph, "")

        self.assertEqual(result.verdict, Verdict.LIKELY_SAFE)
        self.assertEqual(result.total_agents, 0)


class TestConsensusResult(unittest.TestCase):
    """Tests for ConsensusResult dataclass."""

    def test_result_creation(self):
        """Test creating a consensus result."""
        result = ConsensusResult(
            verdict=Verdict.HIGH_RISK,
            agents_agreed=3,
            total_agents=4,
            confidence=0.9,
            summary="High risk detected",
        )
        self.assertEqual(result.verdict, Verdict.HIGH_RISK)
        self.assertEqual(result.agents_agreed, 3)

    def test_result_serialization(self):
        """Test serializing a consensus result."""
        result = ConsensusResult(
            verdict=Verdict.MEDIUM_RISK,
            agents_agreed=2,
            total_agents=4,
            summary="Medium risk",
        )
        d = result.to_dict()
        self.assertEqual(d["verdict"], "MEDIUM_RISK")
        self.assertEqual(d["agents_agreed"], 2)

    def test_result_deserialization(self):
        """Test deserializing a consensus result."""
        data = {
            "verdict": "LOW_RISK",
            "agents_agreed": 1,
            "total_agents": 4,
            "agent_results": [],
            "evidence": [],
            "confidence": 0.5,
            "summary": "Low risk",
        }
        result = ConsensusResult.from_dict(data)
        self.assertEqual(result.verdict, Verdict.LOW_RISK)
        self.assertEqual(result.confidence, 0.5)


class TestVerdict(unittest.TestCase):
    """Tests for Verdict enum."""

    def test_verdict_values(self):
        """Test all verdict values exist."""
        verdicts = [
            Verdict.HIGH_RISK,
            Verdict.MEDIUM_RISK,
            Verdict.LOW_RISK,
            Verdict.LIKELY_SAFE,
        ]
        self.assertEqual(len(verdicts), 4)

    def test_verdict_string_values(self):
        """Test verdict string representations."""
        self.assertEqual(Verdict.HIGH_RISK.value, "HIGH_RISK")
        self.assertEqual(Verdict.LIKELY_SAFE.value, "LIKELY_SAFE")


if __name__ == "__main__":
    unittest.main()
