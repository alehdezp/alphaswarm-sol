"""Phase 15: Supply-Chain Layer Tests.

Tests for external dependency analysis in smart contracts.
"""

import unittest
from dataclasses import dataclass, field
from typing import Any, Dict, List

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node, Edge
from alphaswarm_sol.kg.supply_chain import (
    TrustLevel,
    DependencyType,
    ExternalDependency,
    DependencyAnalysis,
    DependencyAnalyzer,
    analyze_external_dependencies,
    add_dependency_nodes_to_graph,
    KNOWN_TRUSTED_INTERFACES,
    CALLBACK_RISK_INTERFACES,
)


class TestTrustLevel(unittest.TestCase):
    """Tests for TrustLevel enum."""

    def test_trust_levels_defined(self):
        """All trust levels are defined."""
        self.assertEqual(TrustLevel.TRUSTED.value, "trusted")
        self.assertEqual(TrustLevel.SEMI_TRUSTED.value, "semi-trusted")
        self.assertEqual(TrustLevel.UNTRUSTED.value, "untrusted")


class TestDependencyType(unittest.TestCase):
    """Tests for DependencyType enum."""

    def test_dependency_types_defined(self):
        """All dependency types are defined."""
        self.assertEqual(DependencyType.ORACLE.value, "oracle")
        self.assertEqual(DependencyType.TOKEN.value, "token")
        self.assertEqual(DependencyType.DEX.value, "dex")
        self.assertEqual(DependencyType.CALLBACK.value, "callback")


class TestExternalDependency(unittest.TestCase):
    """Tests for ExternalDependency dataclass."""

    def test_dependency_creation(self):
        """ExternalDependency can be created with all fields."""
        dep = ExternalDependency(
            id="test_dep",
            interface="IERC20",
            target_address="0x1234",
            known_implementations=["Standard ERC20"],
            trust_level=TrustLevel.SEMI_TRUSTED,
            dependency_type=DependencyType.TOKEN,
            callback_risk=False,
            state_assumptions=["Token follows standard"],
            compromise_impact=["Token theft"],
            call_sites=["func1", "func2"],
            evidence=["uses_erc20_transfer=True"],
        )

        self.assertEqual(dep.id, "test_dep")
        self.assertEqual(dep.interface, "IERC20")
        self.assertEqual(dep.trust_level, TrustLevel.SEMI_TRUSTED)
        self.assertFalse(dep.callback_risk)

    def test_to_dict(self):
        """ExternalDependency serializes correctly."""
        dep = ExternalDependency(
            id="test_dep",
            interface="AggregatorV3Interface",
            trust_level=TrustLevel.TRUSTED,
            dependency_type=DependencyType.ORACLE,
            callback_risk=False,
        )

        d = dep.to_dict()
        self.assertEqual(d["id"], "test_dep")
        self.assertEqual(d["interface"], "AggregatorV3Interface")
        self.assertEqual(d["trust_level"], "trusted")
        self.assertEqual(d["dependency_type"], "oracle")

    def test_from_dict(self):
        """ExternalDependency deserializes correctly."""
        d = {
            "id": "test_dep",
            "interface": "IDEXRouter",
            "trust_level": "semi-trusted",
            "dependency_type": "dex",
            "callback_risk": True,
            "state_assumptions": ["Liquidity exists"],
            "compromise_impact": ["Sandwich attack"],
        }

        dep = ExternalDependency.from_dict(d)
        self.assertEqual(dep.id, "test_dep")
        self.assertEqual(dep.interface, "IDEXRouter")
        self.assertEqual(dep.trust_level, TrustLevel.SEMI_TRUSTED)
        self.assertEqual(dep.dependency_type, DependencyType.DEX)
        self.assertTrue(dep.callback_risk)


class TestDependencyAnalysis(unittest.TestCase):
    """Tests for DependencyAnalysis dataclass."""

    def test_analysis_counts(self):
        """DependencyAnalysis computes counts correctly."""
        deps = [
            ExternalDependency(
                id="dep1",
                interface="IERC20",
                trust_level=TrustLevel.SEMI_TRUSTED,
                callback_risk=False,
            ),
            ExternalDependency(
                id="dep2",
                interface="IExternal",
                trust_level=TrustLevel.UNTRUSTED,
                callback_risk=True,
                compromise_impact=["Impact1", "Impact2"],
            ),
            ExternalDependency(
                id="dep3",
                interface="IAnother",
                trust_level=TrustLevel.UNTRUSTED,
                callback_risk=False,
            ),
        ]

        analysis = DependencyAnalysis(
            contract_id="test_contract",
            dependencies=deps,
        )

        self.assertEqual(analysis.total_dependencies, 3)
        self.assertEqual(analysis.untrusted_count, 2)
        self.assertEqual(analysis.callback_risk_count, 1)
        self.assertEqual(analysis.high_impact_count, 1)

    def test_get_by_type(self):
        """get_by_type filters correctly."""
        deps = [
            ExternalDependency(id="dep1", interface="I1", dependency_type=DependencyType.ORACLE),
            ExternalDependency(id="dep2", interface="I2", dependency_type=DependencyType.TOKEN),
            ExternalDependency(id="dep3", interface="I3", dependency_type=DependencyType.ORACLE),
        ]

        analysis = DependencyAnalysis(contract_id="test", dependencies=deps)
        oracles = analysis.get_by_type(DependencyType.ORACLE)

        self.assertEqual(len(oracles), 2)

    def test_get_untrusted(self):
        """get_untrusted returns only untrusted deps."""
        deps = [
            ExternalDependency(id="dep1", interface="I1", trust_level=TrustLevel.TRUSTED),
            ExternalDependency(id="dep2", interface="I2", trust_level=TrustLevel.UNTRUSTED),
        ]

        analysis = DependencyAnalysis(contract_id="test", dependencies=deps)
        untrusted = analysis.get_untrusted()

        self.assertEqual(len(untrusted), 1)
        self.assertEqual(untrusted[0].id, "dep2")


class TestDependencyAnalyzer(unittest.TestCase):
    """Tests for DependencyAnalyzer class."""

    def test_analyze_oracle_dependency(self):
        """Analyzer detects oracle dependencies."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="PriceConsumer",
                    type="Contract",
                ),
                "func1": Node(
                    id="func1",
                    label="getPrice",
                    type="Function",
                    properties={
                        "contract_name": "PriceConsumer",
                        "reads_oracle_price": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        analyzer = DependencyAnalyzer(graph)
        analysis = analyzer.analyze_contract("contract1")

        self.assertEqual(len(analysis.dependencies), 1)
        dep = analysis.dependencies[0]
        self.assertEqual(dep.dependency_type, DependencyType.ORACLE)
        self.assertEqual(dep.interface, "AggregatorV3Interface")
        self.assertIn("Price is not stale", dep.state_assumptions)

    def test_analyze_token_dependency(self):
        """Analyzer detects token dependencies."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="TokenVault",
                    type="Contract",
                ),
                "func1": Node(
                    id="func1",
                    label="deposit",
                    type="Function",
                    properties={
                        "contract_name": "TokenVault",
                        "uses_erc20_transfer": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        analyzer = DependencyAnalyzer(graph)
        analysis = analyzer.analyze_contract("contract1")

        self.assertEqual(len(analysis.dependencies), 1)
        dep = analysis.dependencies[0]
        self.assertEqual(dep.dependency_type, DependencyType.TOKEN)
        self.assertEqual(dep.interface, "IERC20")

    def test_analyze_dex_dependency(self):
        """Analyzer detects DEX dependencies."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Swapper",
                    type="Contract",
                ),
                "func1": Node(
                    id="func1",
                    label="swapTokens",
                    type="Function",
                    properties={
                        "contract_name": "Swapper",
                        "swap_like": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        analyzer = DependencyAnalyzer(graph)
        analysis = analyzer.analyze_contract("contract1")

        self.assertEqual(len(analysis.dependencies), 1)
        dep = analysis.dependencies[0]
        self.assertEqual(dep.dependency_type, DependencyType.DEX)
        self.assertTrue(dep.callback_risk)  # DEX swaps can callback

    def test_analyze_delegatecall_dependency(self):
        """Analyzer detects high-risk delegatecall dependencies."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Proxy",
                    type="Contract",
                ),
                "func1": Node(
                    id="func1",
                    label="fallback",
                    type="Function",
                    properties={
                        "contract_name": "Proxy",
                        "uses_delegatecall": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        analyzer = DependencyAnalyzer(graph)
        analysis = analyzer.analyze_contract("contract1")

        self.assertEqual(len(analysis.dependencies), 1)
        dep = analysis.dependencies[0]
        self.assertEqual(dep.trust_level, TrustLevel.UNTRUSTED)
        self.assertTrue(dep.callback_risk)
        self.assertIn("Full contract takeover", dep.compromise_impact)

    def test_analyze_multiple_dependencies(self):
        """Analyzer handles multiple dependencies in one contract."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="DeFiVault",
                    type="Contract",
                ),
                "func1": Node(
                    id="func1",
                    label="deposit",
                    type="Function",
                    properties={
                        "contract_name": "DeFiVault",
                        "uses_erc20_transfer": True,
                    }
                ),
                "func2": Node(
                    id="func2",
                    label="swap",
                    type="Function",
                    properties={
                        "contract_name": "DeFiVault",
                        "swap_like": True,
                    }
                ),
                "func3": Node(
                    id="func3",
                    label="getPrice",
                    type="Function",
                    properties={
                        "contract_name": "DeFiVault",
                        "reads_oracle_price": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        analyzer = DependencyAnalyzer(graph)
        analysis = analyzer.analyze_contract("contract1")

        self.assertEqual(len(analysis.dependencies), 3)
        dep_types = {d.dependency_type for d in analysis.dependencies}
        self.assertIn(DependencyType.TOKEN, dep_types)
        self.assertIn(DependencyType.DEX, dep_types)
        self.assertIn(DependencyType.ORACLE, dep_types)

    def test_analyze_all_contracts(self):
        """Analyzer can analyze all contracts in graph."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="A", type="Contract"),
                "contract2": Node(id="contract2", label="B", type="Contract"),
                "func1": Node(
                    id="func1",
                    label="f1",
                    type="Function",
                    properties={"contract_name": "A", "reads_oracle_price": True}
                ),
                "func2": Node(
                    id="func2",
                    label="f2",
                    type="Function",
                    properties={"contract_name": "B", "swap_like": True}
                ),
            },
            edges={},
            metadata={},
        )

        analyzer = DependencyAnalyzer(graph)
        results = analyzer.analyze_all_contracts()

        self.assertEqual(len(results), 2)
        self.assertIn("contract1", results)
        self.assertIn("contract2", results)

    def test_callback_risk_detection(self):
        """Analyzer detects callback risk from function properties."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="A", type="Contract"),
                "func1": Node(
                    id="func1",
                    label="withdraw",
                    type="Function",
                    properties={
                        "contract_name": "A",
                        "calls_external": True,
                        "has_reentrancy_guard": False,
                        "state_write_after_external_call": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        analyzer = DependencyAnalyzer(graph)
        analysis = analyzer.analyze_contract("contract1")

        self.assertEqual(len(analysis.dependencies), 1)
        self.assertTrue(analysis.dependencies[0].callback_risk)


class TestAddDependencyNodesToGraph(unittest.TestCase):
    """Tests for add_dependency_nodes_to_graph function."""

    def test_adds_dependency_nodes(self):
        """Function adds ExternalDependency nodes to graph."""
        graph = KnowledgeGraph(
            nodes={
                "func1": Node(id="func1", label="test", type="Function"),
            },
            edges={},
            metadata={},
        )

        analysis = DependencyAnalysis(
            contract_id="test",
            dependencies=[
                ExternalDependency(
                    id="oracle_dep",
                    interface="AggregatorV3Interface",
                    trust_level=TrustLevel.SEMI_TRUSTED,
                    dependency_type=DependencyType.ORACLE,
                    call_sites=["func1"],
                ),
            ],
        )

        add_dependency_nodes_to_graph(graph, analysis)

        # Check node added
        self.assertIn("dep_oracle_dep", graph.nodes)
        dep_node = graph.nodes["dep_oracle_dep"]
        self.assertEqual(dep_node.type, "ExternalDependency")
        self.assertEqual(dep_node.properties["interface"], "AggregatorV3Interface")
        self.assertEqual(dep_node.properties["trust_level"], "semi-trusted")

        # Check edge added
        self.assertEqual(len(graph.edges), 1)
        edge = list(graph.edges.values())[0]
        self.assertEqual(edge.source, "func1")
        self.assertEqual(edge.target, "dep_oracle_dep")
        self.assertEqual(edge.type, "DEPENDS_ON")


class TestAnalyzeExternalDependencies(unittest.TestCase):
    """Tests for convenience function."""

    def test_convenience_function(self):
        """analyze_external_dependencies works correctly."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Test", type="Contract"),
                "func1": Node(
                    id="func1",
                    label="test",
                    type="Function",
                    properties={
                        "contract_name": "Test",
                        "reads_oracle_price": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        analysis = analyze_external_dependencies(graph, "contract1")

        self.assertEqual(analysis.contract_id, "contract1")
        self.assertEqual(len(analysis.dependencies), 1)

    def test_analyze_all(self):
        """analyze_external_dependencies without contract_id analyzes all."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="A", type="Contract"),
                "func1": Node(
                    id="func1",
                    label="f1",
                    type="Function",
                    properties={"contract_name": "A", "swap_like": True}
                ),
            },
            edges={},
            metadata={},
        )

        analysis = analyze_external_dependencies(graph)

        self.assertEqual(analysis.contract_id, "all")
        self.assertGreater(len(analysis.dependencies), 0)


class TestKnownInterfaces(unittest.TestCase):
    """Tests for known interface data."""

    def test_known_trusted_interfaces(self):
        """Known trusted interfaces are defined."""
        self.assertIn("AggregatorV3Interface", KNOWN_TRUSTED_INTERFACES)
        self.assertIn("IERC20", KNOWN_TRUSTED_INTERFACES)
        self.assertIn("IUniswapV2Router02", KNOWN_TRUSTED_INTERFACES)

    def test_callback_risk_interfaces(self):
        """Callback risk interfaces are defined."""
        self.assertIn("IERC721Receiver", CALLBACK_RISK_INTERFACES)
        self.assertIn("IFlashLoanRecipient", CALLBACK_RISK_INTERFACES)


if __name__ == "__main__":
    unittest.main()
