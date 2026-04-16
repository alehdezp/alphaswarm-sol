"""Phase 17: Semantic Scaffolding Tests.

Tests for token-efficient semantic scaffold generation.
"""

import unittest
from typing import Any, Dict, List

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node, Edge
from alphaswarm_sol.kg.scaffold import (
    ScaffoldFormat,
    FunctionSummary,
    RiskMatrixEntry,
    SemanticScaffold,
    ScaffoldGenerator,
    generate_semantic_scaffold,
    compress_for_llm,
)


class TestScaffoldFormat(unittest.TestCase):
    """Tests for ScaffoldFormat enum."""

    def test_formats_defined(self):
        """All scaffold formats are defined."""
        self.assertEqual(ScaffoldFormat.COMPACT.value, "compact")
        self.assertEqual(ScaffoldFormat.STRUCTURED.value, "structured")
        self.assertEqual(ScaffoldFormat.YAML_LIKE.value, "yaml_like")


class TestFunctionSummary(unittest.TestCase):
    """Tests for FunctionSummary dataclass."""

    def test_summary_creation(self):
        """FunctionSummary can be created with all fields."""
        summary = FunctionSummary(
            name="withdraw",
            role="CriticalState",
            visibility="external",
            guards=["onlyOwner", "reentrancy"],
            operations=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            mutations=["state", "privileged"],
            externals=["external_call", "token"],
            risk_factors=["reentrancy", "access_control"],
            signature="R:bal->X:out->W:bal",
        )

        self.assertEqual(summary.name, "withdraw")
        self.assertEqual(summary.role, "CriticalState")
        self.assertEqual(len(summary.guards), 2)
        self.assertEqual(len(summary.risk_factors), 2)

    def test_to_compact(self):
        """to_compact generates minimal representation."""
        summary = FunctionSummary(
            name="withdraw",
            role="Critical",
            guards=["access"],
            operations=["TRANSFERS_VALUE_OUT"],
            risk_factors=["reentrancy"],
        )

        compact = summary.to_compact()

        self.assertIn("fn:withdraw", compact)
        self.assertIn("role:Critical", compact)
        self.assertIn("guards:access", compact)
        self.assertIn("ops:TRANSFERS_VALUE_OUT", compact)
        self.assertIn("risk:reentrancy", compact)

    def test_to_compact_minimal(self):
        """to_compact handles minimal data."""
        summary = FunctionSummary(name="simple")
        compact = summary.to_compact()

        self.assertIn("fn:simple", compact)
        self.assertNotIn("role:", compact)  # Empty role not included
        self.assertNotIn("guards:", compact)  # Empty guards not included

    def test_to_structured(self):
        """to_structured generates readable output."""
        summary = FunctionSummary(
            name="deposit",
            role="Guardian",
            guards=["onlyOwner"],
            operations=["WRITES_STATE"],
            mutations=["balance"],
            externals=["token"],
            risk_factors=["access_control"],
        )

        structured = summary.to_structured()

        self.assertIn("FUNCTION: deposit", structured)
        self.assertIn("Role: Guardian", structured)
        self.assertIn("Guards: onlyOwner", structured)
        self.assertIn("Ops: WRITES_STATE", structured)
        self.assertIn("Mutates: balance", structured)
        self.assertIn("Externals: token", structured)
        self.assertIn("Risks: access_control", structured)

    def test_compact_token_efficiency(self):
        """Compact format is token-efficient (under ~50 tokens)."""
        summary = FunctionSummary(
            name="withdraw",
            role="Critical",
            guards=["access", "reentrancy"],
            operations=["TRANSFERS_VALUE_OUT", "WRITES_STATE"],
            risk_factors=["reentrancy", "dos"],
        )

        compact = summary.to_compact()
        # Rough estimate: ~4 chars per token
        estimated_tokens = len(compact) // 4

        # Should be under 50 tokens for typical function
        self.assertLess(estimated_tokens, 50)


class TestRiskMatrixEntry(unittest.TestCase):
    """Tests for RiskMatrixEntry dataclass."""

    def test_entry_creation(self):
        """RiskMatrixEntry can be created."""
        entry = RiskMatrixEntry(
            category="reentrancy",
            severity=9,
            functions=["withdraw", "transfer"],
            evidence=["state_write_after_external_call"],
        )

        self.assertEqual(entry.category, "reentrancy")
        self.assertEqual(entry.severity, 9)
        self.assertEqual(len(entry.functions), 2)


class TestSemanticScaffold(unittest.TestCase):
    """Tests for SemanticScaffold dataclass."""

    def test_scaffold_creation(self):
        """SemanticScaffold can be created with all fields."""
        scaffold = SemanticScaffold(
            contract_name="Vault",
            functions=[
                FunctionSummary(name="deposit", risk_factors=["access"]),
                FunctionSummary(name="withdraw", risk_factors=["reentrancy"]),
            ],
            risk_matrix=[
                RiskMatrixEntry(category="reentrancy", severity=9, functions=["withdraw"], evidence=[]),
            ],
            attack_surface=["withdraw: reentrancy"],
            dependencies=["external_call", "token"],
            token_estimate=50,
        )

        self.assertEqual(scaffold.contract_name, "Vault")
        self.assertEqual(len(scaffold.functions), 2)
        self.assertEqual(len(scaffold.risk_matrix), 1)

    def test_to_string_compact(self):
        """to_string generates compact format."""
        scaffold = SemanticScaffold(
            contract_name="Test",
            functions=[
                FunctionSummary(name="func1", role="Critical", risk_factors=["risk1"]),
            ],
            risk_matrix=[
                RiskMatrixEntry(category="risk1", severity=8, functions=["func1"], evidence=[]),
            ],
            attack_surface=["func1: risk1"],
        )

        output = scaffold.to_string(ScaffoldFormat.COMPACT)

        self.assertIn("CONTRACT: Test", output)
        self.assertIn("fn:func1", output)
        self.assertIn("RISKS:", output)
        self.assertIn("SURFACE:", output)

    def test_to_string_structured(self):
        """to_string generates structured format."""
        scaffold = SemanticScaffold(
            contract_name="Test",
            functions=[
                FunctionSummary(name="func1", role="Guardian", guards=["access"]),
            ],
            risk_matrix=[
                RiskMatrixEntry(category="access", severity=7, functions=["func1"], evidence=[]),
            ],
            attack_surface=["func1: access"],
        )

        output = scaffold.to_string(ScaffoldFormat.STRUCTURED)

        self.assertIn("═══ Test ═══", output)
        self.assertIn("FUNCTION: func1", output)
        self.assertIn("RISK MATRIX:", output)
        self.assertIn("[7/10] access", output)
        self.assertIn("ATTACK SURFACE:", output)

    def test_to_string_yaml_like(self):
        """to_string generates YAML-like format."""
        scaffold = SemanticScaffold(
            contract_name="Test",
            functions=[
                FunctionSummary(name="func1", role="Critical", guards=["auth"], operations=["WRITE"]),
            ],
            risk_matrix=[
                RiskMatrixEntry(category="access", severity=6, functions=[], evidence=[]),
            ],
        )

        output = scaffold.to_string(ScaffoldFormat.YAML_LIKE)

        self.assertIn("contract: Test", output)
        self.assertIn("functions:", output)
        self.assertIn("- name: func1", output)
        self.assertIn("role: Critical", output)
        self.assertIn("guards: [auth]", output)
        self.assertIn("risks:", output)
        self.assertIn("category: access", output)


class TestScaffoldGenerator(unittest.TestCase):
    """Tests for ScaffoldGenerator class."""

    def test_generate_basic_scaffold(self):
        """Generator creates scaffold from graph."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="SimpleVault",
                    type="Contract",
                ),
                "func1": Node(
                    id="func1",
                    label="deposit",
                    type="Function",
                    properties={
                        "contract_name": "SimpleVault",
                        "visibility": "public",
                        "writes_state": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        self.assertEqual(scaffold.contract_name, "SimpleVault")
        self.assertEqual(len(scaffold.functions), 1)
        self.assertEqual(scaffold.functions[0].name, "deposit")

    def test_generate_with_risk_factors(self):
        """Generator detects risk factors."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Vulnerable",
                    type="Contract",
                ),
                "func1": Node(
                    id="func1",
                    label="withdraw",
                    type="Function",
                    properties={
                        "contract_name": "Vulnerable",
                        "visibility": "external",
                        "writes_state": True,
                        "state_write_after_external_call": True,
                        "has_reentrancy_guard": False,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        self.assertEqual(len(scaffold.functions), 1)
        self.assertIn("reentrancy", scaffold.functions[0].risk_factors)
        self.assertEqual(len(scaffold.risk_matrix), 1)
        self.assertEqual(scaffold.risk_matrix[0].category, "reentrancy")
        self.assertEqual(scaffold.risk_matrix[0].severity, 9)

    def test_generate_with_access_control_risk(self):
        """Generator detects access control risks."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Ownable",
                    type="Contract",
                ),
                "func1": Node(
                    id="func1",
                    label="setOwner",
                    type="Function",
                    properties={
                        "contract_name": "Ownable",
                        "visibility": "public",
                        "writes_state": True,
                        "writes_privileged_state": True,
                        "has_access_gate": False,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        self.assertIn("access_control", scaffold.functions[0].risk_factors)

    def test_generate_with_oracle_risk(self):
        """Generator detects oracle stale price risks."""
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
                        "visibility": "public",
                        "reads_oracle_price": True,
                        "has_staleness_check": False,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        self.assertIn("stale_price", scaffold.functions[0].risk_factors)

    def test_generate_with_dos_risk(self):
        """Generator detects DoS risks."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Loopy",
                    type="Contract",
                ),
                "func1": Node(
                    id="func1",
                    label="processAll",
                    type="Function",
                    properties={
                        "contract_name": "Loopy",
                        "visibility": "public",
                        "writes_state": True,
                        "has_unbounded_loop": True,
                        "external_calls_in_loop": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        self.assertIn("dos", scaffold.functions[0].risk_factors)
        self.assertIn("dos_external", scaffold.functions[0].risk_factors)

    def test_generate_with_guards(self):
        """Generator extracts guards from function."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Guarded",
                    type="Contract",
                ),
                "func1": Node(
                    id="func1",
                    label="restricted",
                    type="Function",
                    properties={
                        "contract_name": "Guarded",
                        "visibility": "public",
                        "writes_state": True,
                        "has_access_gate": True,
                        "has_reentrancy_guard": True,
                        "modifiers": ["onlyOwner", "nonReentrant"],
                    }
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        guards = scaffold.functions[0].guards
        self.assertIn("access", guards)
        self.assertIn("reentrancy", guards)

    def test_generate_with_externals(self):
        """Generator extracts external dependencies."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="DeFi",
                    type="Contract",
                ),
                "func1": Node(
                    id="func1",
                    label="swap",
                    type="Function",
                    properties={
                        "contract_name": "DeFi",
                        "visibility": "external",
                        "writes_state": True,
                        "calls_external": True,
                        "reads_oracle_price": True,
                        "uses_erc20_transfer": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        externals = scaffold.functions[0].externals
        self.assertIn("external_call", externals)
        self.assertIn("oracle", externals)
        self.assertIn("token", externals)

    def test_generate_max_functions(self):
        """Generator respects max_functions limit."""
        nodes = {
            "contract1": Node(id="contract1", label="Multi", type="Contract"),
        }
        for i in range(20):
            nodes[f"func{i}"] = Node(
                id=f"func{i}",
                label=f"function{i}",
                type="Function",
                properties={"contract_name": "Multi", "writes_state": True},
            )

        graph = KnowledgeGraph(nodes=nodes, edges={}, metadata={})
        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1", max_functions=5)

        self.assertEqual(len(scaffold.functions), 5)

    def test_generate_sorts_by_risk(self):
        """Generator sorts functions by risk factors."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Mixed", type="Contract"),
                "func1": Node(
                    id="func1",
                    label="safe",
                    type="Function",
                    properties={"contract_name": "Mixed", "writes_state": True},
                ),
                "func2": Node(
                    id="func2",
                    label="risky",
                    type="Function",
                    properties={
                        "contract_name": "Mixed",
                        "writes_state": True,
                        "state_write_after_external_call": True,
                        "writes_privileged_state": True,
                        "has_access_gate": False,
                    },
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        # Risky function should come first
        self.assertEqual(scaffold.functions[0].name, "risky")

    def test_generate_attack_surface(self):
        """Generator identifies attack surface."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Surface", type="Contract"),
                "func1": Node(
                    id="func1",
                    label="publicRisky",
                    type="Function",
                    properties={
                        "contract_name": "Surface",
                        "visibility": "public",
                        "writes_state": True,
                        "has_unbounded_loop": True,
                    },
                ),
                "func2": Node(
                    id="func2",
                    label="internalRisky",
                    type="Function",
                    properties={
                        "contract_name": "Surface",
                        "visibility": "internal",
                        "writes_state": True,
                        "has_unbounded_loop": True,
                    },
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        # Only public function should be in attack surface
        self.assertEqual(len(scaffold.attack_surface), 1)
        self.assertIn("publicRisky", scaffold.attack_surface[0])

    def test_generate_token_estimate(self):
        """Generator estimates token count."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Test", type="Contract"),
                "func1": Node(
                    id="func1",
                    label="test",
                    type="Function",
                    properties={"contract_name": "Test", "writes_state": True},
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        self.assertGreater(scaffold.token_estimate, 0)

    def test_generate_slippage_risk(self):
        """Generator detects slippage risks."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Swap", type="Contract"),
                "func1": Node(
                    id="func1",
                    label="swap",
                    type="Function",
                    properties={
                        "contract_name": "Swap",
                        "visibility": "external",
                        "writes_state": True,
                        "swap_like": True,
                        "risk_missing_slippage_parameter": True,
                    },
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        self.assertIn("slippage", scaffold.functions[0].risk_factors)

    def test_generate_ecrecover_risk(self):
        """Generator detects ecrecover zero address risks."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Sig", type="Contract"),
                "func1": Node(
                    id="func1",
                    label="verify",
                    type="Function",
                    properties={
                        "contract_name": "Sig",
                        "visibility": "public",
                        "writes_state": True,
                        "uses_ecrecover": True,
                        "checks_zero_address": False,
                    },
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        self.assertIn("ecrecover_zero", scaffold.functions[0].risk_factors)


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for convenience functions."""

    def test_generate_semantic_scaffold(self):
        """generate_semantic_scaffold convenience function works."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Test", type="Contract"),
                "func1": Node(
                    id="func1",
                    label="test",
                    type="Function",
                    properties={"contract_name": "Test", "writes_state": True},
                ),
            },
            edges={},
            metadata={},
        )

        output = generate_semantic_scaffold(graph, "contract1")

        self.assertIsInstance(output, str)
        self.assertIn("CONTRACT: Test", output)

    def test_generate_semantic_scaffold_formats(self):
        """generate_semantic_scaffold supports all formats."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Test", type="Contract"),
                "func1": Node(
                    id="func1",
                    label="test",
                    type="Function",
                    properties={"contract_name": "Test", "writes_state": True},
                ),
            },
            edges={},
            metadata={},
        )

        compact = generate_semantic_scaffold(graph, "contract1", ScaffoldFormat.COMPACT)
        structured = generate_semantic_scaffold(graph, "contract1", ScaffoldFormat.STRUCTURED)
        yaml_like = generate_semantic_scaffold(graph, "contract1", ScaffoldFormat.YAML_LIKE)

        self.assertIn("CONTRACT:", compact)
        self.assertIn("═══", structured)
        self.assertIn("contract:", yaml_like)


class TestCompressForLLM(unittest.TestCase):
    """Tests for compress_for_llm function."""

    def test_compress_within_limit(self):
        """compress_for_llm returns as-is when within limit."""
        scaffold = SemanticScaffold(
            contract_name="Small",
            functions=[FunctionSummary(name="f1")],
            token_estimate=10,
        )

        compressed = compress_for_llm(scaffold, max_tokens=100)

        self.assertIn("CONTRACT: Small", compressed)
        self.assertNotIn("truncated", compressed)

    def test_compress_exceeds_limit(self):
        """compress_for_llm truncates when exceeding limit."""
        scaffold = SemanticScaffold(
            contract_name="Large",
            functions=[
                FunctionSummary(
                    name=f"function{i}",
                    role="Critical",
                    guards=["guard1", "guard2"],
                    operations=["OP1", "OP2", "OP3"],
                    risk_factors=["risk1", "risk2"],
                )
                for i in range(20)
            ],
            risk_matrix=[
                RiskMatrixEntry(category="risk1", severity=9, functions=[], evidence=[]),
            ],
            token_estimate=500,
        )

        compressed = compress_for_llm(scaffold, max_tokens=50)

        self.assertIn("truncated", compressed)

    def test_compress_preserves_key_info(self):
        """compress_for_llm preserves contract name even when truncating."""
        scaffold = SemanticScaffold(
            contract_name="Important",
            functions=[
                FunctionSummary(name=f"func{i}", risk_factors=["r1", "r2"])
                for i in range(100)
            ],
            token_estimate=1000,
        )

        compressed = compress_for_llm(scaffold, max_tokens=20)

        self.assertIn("CONTRACT: Important", compressed)


class TestTokenEfficiency(unittest.TestCase):
    """Tests for token efficiency requirements."""

    def test_compact_vs_raw_ratio(self):
        """Compact format is significantly smaller than raw representation."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="DeFiVault", type="Contract"),
                "func1": Node(
                    id="func1",
                    label="deposit",
                    type="Function",
                    properties={
                        "contract_name": "DeFiVault",
                        "visibility": "external",
                        "writes_state": True,
                        "uses_erc20_transfer": True,
                        "has_access_gate": False,
                        "semantic_ops": ["WRITES_USER_BALANCE", "TRANSFERS_VALUE_IN"],
                    },
                ),
                "func2": Node(
                    id="func2",
                    label="withdraw",
                    type="Function",
                    properties={
                        "contract_name": "DeFiVault",
                        "visibility": "external",
                        "writes_state": True,
                        "state_write_after_external_call": True,
                        "calls_external": True,
                        "semantic_ops": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                    },
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")
        compact = scaffold.to_string(ScaffoldFormat.COMPACT)

        # Raw representation would be much larger
        raw_size = sum(len(str(n.properties)) for n in graph.nodes.values() if n.type == "Function")
        compact_size = len(compact)

        # Compact should be significantly smaller (target: ~10x reduction)
        # At minimum should be smaller
        self.assertLess(compact_size, raw_size)

    def test_single_function_under_100_tokens(self):
        """Single function scaffold is under 100 tokens."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Simple", type="Contract"),
                "func1": Node(
                    id="func1",
                    label="process",
                    type="Function",
                    properties={
                        "contract_name": "Simple",
                        "visibility": "public",
                        "writes_state": True,
                        "has_access_gate": True,
                        "has_reentrancy_guard": True,
                        "semantic_role": "Guardian",
                        "modifiers": ["onlyOwner", "nonReentrant"],
                        "semantic_ops": ["CHECKS_PERMISSION", "WRITES_STATE"],
                    },
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        # Token estimate should be under 100
        self.assertLess(scaffold.token_estimate, 100)


class TestComplexScenarios(unittest.TestCase):
    """Tests for complex multi-function scenarios."""

    def test_defi_vault_scaffold(self):
        """Scaffold handles typical DeFi vault contract."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Vault", type="Contract"),
                "deposit": Node(
                    id="deposit",
                    label="deposit",
                    type="Function",
                    properties={
                        "contract_name": "Vault",
                        "visibility": "external",
                        "writes_state": True,
                        "uses_erc20_transfer": True,
                        "semantic_ops": ["TRANSFERS_VALUE_IN", "WRITES_USER_BALANCE"],
                    },
                ),
                "withdraw": Node(
                    id="withdraw",
                    label="withdraw",
                    type="Function",
                    properties={
                        "contract_name": "Vault",
                        "visibility": "external",
                        "writes_state": True,
                        "state_write_after_external_call": True,
                        "uses_erc20_transfer": True,
                        "semantic_ops": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                    },
                ),
                "setFee": Node(
                    id="setFee",
                    label="setFee",
                    type="Function",
                    properties={
                        "contract_name": "Vault",
                        "visibility": "public",
                        "writes_state": True,
                        "writes_privileged_state": True,
                        "has_access_gate": True,
                        "modifiers": ["onlyOwner"],
                    },
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        # Should have 3 functions
        self.assertEqual(len(scaffold.functions), 3)

        # withdraw should have reentrancy risk
        withdraw_func = next(f for f in scaffold.functions if f.name == "withdraw")
        self.assertIn("reentrancy", withdraw_func.risk_factors)

        # Risk matrix should include reentrancy
        risk_categories = {r.category for r in scaffold.risk_matrix}
        self.assertIn("reentrancy", risk_categories)

    def test_multi_contract_filter(self):
        """Scaffold filters to specific contract."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="A", type="Contract"),
                "contract2": Node(id="contract2", label="B", type="Contract"),
                "funcA": Node(
                    id="funcA",
                    label="funcA",
                    type="Function",
                    properties={"contract_name": "A", "writes_state": True},
                ),
                "funcB": Node(
                    id="funcB",
                    label="funcB",
                    type="Function",
                    properties={"contract_name": "B", "writes_state": True},
                ),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        # Should only have funcA
        self.assertEqual(len(scaffold.functions), 1)
        self.assertEqual(scaffold.functions[0].name, "funcA")

    def test_empty_contract(self):
        """Scaffold handles contract with no functions."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Empty", type="Contract"),
            },
            edges={},
            metadata={},
        )

        generator = ScaffoldGenerator(graph)
        scaffold = generator.generate("contract1")

        self.assertEqual(scaffold.contract_name, "Empty")
        self.assertEqual(len(scaffold.functions), 0)
        self.assertEqual(len(scaffold.risk_matrix), 0)


if __name__ == "__main__":
    unittest.main()
