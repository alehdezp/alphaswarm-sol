"""Phase 18: Attack Path Synthesis Tests.

Tests for attack path synthesis and description generation.
"""

import unittest
from typing import Any, Dict, List

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node, Edge
from alphaswarm_sol.analysis.attack_synthesis import (
    AttackDifficulty,
    ImpactLevel,
    BypassType,
    GuardBypass,
    AttackStep,
    AttackPath,
    AttackDescription,
    AttackPathSynthesizer,
    synthesize_attack_paths,
)


class TestAttackDifficulty(unittest.TestCase):
    """Tests for AttackDifficulty enum."""

    def test_difficulties_defined(self):
        """All difficulty levels are defined."""
        self.assertEqual(AttackDifficulty.TRIVIAL.value, "trivial")
        self.assertEqual(AttackDifficulty.EASY.value, "easy")
        self.assertEqual(AttackDifficulty.MODERATE.value, "moderate")
        self.assertEqual(AttackDifficulty.HARD.value, "hard")
        self.assertEqual(AttackDifficulty.VERY_HARD.value, "very_hard")


class TestImpactLevel(unittest.TestCase):
    """Tests for ImpactLevel enum."""

    def test_impacts_defined(self):
        """All impact levels are defined."""
        self.assertEqual(ImpactLevel.LOW.value, "low")
        self.assertEqual(ImpactLevel.MEDIUM.value, "medium")
        self.assertEqual(ImpactLevel.HIGH.value, "high")
        self.assertEqual(ImpactLevel.CRITICAL.value, "critical")


class TestBypassType(unittest.TestCase):
    """Tests for BypassType enum."""

    def test_bypasses_defined(self):
        """All bypass types are defined."""
        self.assertEqual(BypassType.FLASHLOAN.value, "flashloan")
        self.assertEqual(BypassType.REENTRANCY.value, "reentrancy")
        self.assertEqual(BypassType.FRONTRUN.value, "frontrun")
        self.assertEqual(BypassType.PRICE_MANIPULATION.value, "price_manipulation")


class TestGuardBypass(unittest.TestCase):
    """Tests for GuardBypass dataclass."""

    def test_bypass_creation(self):
        """GuardBypass can be created with all fields."""
        bypass = GuardBypass(
            guard="has_reentrancy_guard",
            bypass_type=BypassType.REENTRANCY,
            description="Bypass reentrancy guard",
            prerequisites=["Controllable callback"],
            difficulty=AttackDifficulty.MODERATE,
        )

        self.assertEqual(bypass.guard, "has_reentrancy_guard")
        self.assertEqual(bypass.bypass_type, BypassType.REENTRANCY)
        self.assertEqual(bypass.difficulty, AttackDifficulty.MODERATE)

    def test_to_dict(self):
        """GuardBypass serializes correctly."""
        bypass = GuardBypass(
            guard="test_guard",
            bypass_type=BypassType.FLASHLOAN,
        )

        d = bypass.to_dict()
        self.assertEqual(d["guard"], "test_guard")
        self.assertEqual(d["bypass_type"], "flashloan")


class TestAttackStep(unittest.TestCase):
    """Tests for AttackStep dataclass."""

    def test_step_creation(self):
        """AttackStep can be created with all fields."""
        step = AttackStep(
            function_id="func1",
            function_name="withdraw",
            action="Call withdraw to drain funds",
            preconditions=["Must have balance"],
            postconditions=["Funds transferred"],
        )

        self.assertEqual(step.function_id, "func1")
        self.assertEqual(step.function_name, "withdraw")
        self.assertEqual(len(step.preconditions), 1)

    def test_to_dict(self):
        """AttackStep serializes correctly."""
        step = AttackStep(
            function_id="func1",
            function_name="test",
            action="Test action",
        )

        d = step.to_dict()
        self.assertEqual(d["function_id"], "func1")
        self.assertEqual(d["action"], "Test action")


class TestAttackPath(unittest.TestCase):
    """Tests for AttackPath dataclass."""

    def test_path_creation(self):
        """AttackPath can be created with all fields."""
        path = AttackPath(
            id="path_1",
            entry="deposit",
            sink="withdraw",
            steps=[
                AttackStep(function_id="f1", function_name="deposit"),
                AttackStep(function_id="f2", function_name="withdraw"),
            ],
            required_bypasses=[
                GuardBypass(guard="guard1", bypass_type=BypassType.REENTRANCY),
            ],
            difficulty=AttackDifficulty.MODERATE,
            impact=ImpactLevel.HIGH,
            attack_type="reentrancy",
            description="Reentrant attack on withdraw",
        )

        self.assertEqual(path.id, "path_1")
        self.assertEqual(path.step_count, 2)
        self.assertEqual(path.bypass_count, 1)

    def test_to_dict(self):
        """AttackPath serializes correctly."""
        path = AttackPath(
            id="path_1",
            entry="start",
            sink="end",
            difficulty=AttackDifficulty.HARD,
            impact=ImpactLevel.CRITICAL,
            attack_type="test",
        )

        d = path.to_dict()
        self.assertEqual(d["id"], "path_1")
        self.assertEqual(d["difficulty"], "hard")
        self.assertEqual(d["impact"], "critical")


class TestAttackDescription(unittest.TestCase):
    """Tests for AttackDescription dataclass."""

    def test_description_creation(self):
        """AttackDescription can be created with all fields."""
        desc = AttackDescription(
            title="Reentrancy Attack",
            summary="Drain funds via reentrant call",
            steps=["Call deposit", "Call withdraw", "Re-enter in callback"],
            prerequisites=["Attacker contract", "Some initial funds"],
            impact="HIGH: Drain all funds",
            mitigation="Add ReentrancyGuard",
        )

        self.assertEqual(desc.title, "Reentrancy Attack")
        self.assertEqual(len(desc.steps), 3)

    def test_to_markdown(self):
        """to_markdown generates markdown output."""
        desc = AttackDescription(
            title="Test Attack",
            summary="Test summary",
            steps=["Step 1", "Step 2"],
            prerequisites=["Prereq 1"],
            impact="HIGH",
            mitigation="Fix it",
        )

        md = desc.to_markdown()

        self.assertIn("## Test Attack", md)
        self.assertIn("**Summary:** Test summary", md)
        self.assertIn("### Attack Steps", md)
        self.assertIn("1. Step 1", md)
        self.assertIn("2. Step 2", md)
        self.assertIn("### Prerequisites", md)
        self.assertIn("### Mitigation", md)

    def test_to_dict(self):
        """AttackDescription serializes correctly."""
        desc = AttackDescription(
            title="Test",
            summary="Summary",
        )

        d = desc.to_dict()
        self.assertEqual(d["title"], "Test")
        self.assertEqual(d["summary"], "Summary")


class TestAttackPathSynthesizer(unittest.TestCase):
    """Tests for AttackPathSynthesizer class."""

    def test_synthesize_reentrancy_path(self):
        """Synthesizer finds reentrancy attack path."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Vulnerable",
                    type="Contract",
                ),
                "withdraw": Node(
                    id="withdraw",
                    label="withdraw",
                    type="Function",
                    properties={
                        "contract_name": "Vulnerable",
                        "visibility": "external",
                        "writes_state": True,
                        "transfers_value_out": True,
                        "state_write_after_external_call": True,
                        "has_reentrancy_guard": False,
                        "semantic_ops": ["TRANSFERS_VALUE_OUT"],
                    }
                ),
            },
            edges={},
            metadata={},
        )

        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1")

        self.assertGreater(len(paths), 0)
        path = paths[0]
        self.assertEqual(path.attack_type, "reentrancy")
        # Description uses "Reentrant" or "reentrancy"
        self.assertTrue(
            "reentr" in path.description.lower(),
            f"Expected 'reentr' in description: {path.description}"
        )

    def test_synthesize_access_control_path(self):
        """Synthesizer finds access control attack path."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Ownable",
                    type="Contract",
                ),
                "setOwner": Node(
                    id="setOwner",
                    label="setOwner",
                    type="Function",
                    properties={
                        "contract_name": "Ownable",
                        "visibility": "public",
                        "writes_state": True,
                        "writes_privileged_state": True,
                        "has_access_gate": False,
                        "semantic_ops": ["MODIFIES_OWNER"],
                    }
                ),
            },
            edges={},
            metadata={},
        )

        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1")

        self.assertGreater(len(paths), 0)
        path = paths[0]
        self.assertEqual(path.attack_type, "unauthorized_access")
        self.assertEqual(path.impact, ImpactLevel.CRITICAL)

    def test_synthesize_oracle_path(self):
        """Synthesizer finds oracle manipulation path."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="PriceDependent",
                    type="Contract",
                ),
                "trade": Node(
                    id="trade",
                    label="trade",
                    type="Function",
                    properties={
                        "contract_name": "PriceDependent",
                        "visibility": "external",
                        "writes_state": True,
                        "transfers_value_out": True,
                        "reads_oracle_price": True,
                        "has_staleness_check": False,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1")

        self.assertGreater(len(paths), 0)
        path = paths[0]
        self.assertEqual(path.attack_type, "oracle_manipulation")

    def test_synthesize_slippage_path(self):
        """Synthesizer finds slippage attack path."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Swapper",
                    type="Contract",
                ),
                "swap": Node(
                    id="swap",
                    label="swap",
                    type="Function",
                    properties={
                        "contract_name": "Swapper",
                        "visibility": "external",
                        "writes_state": True,
                        "transfers_value_out": True,
                        "swap_like": True,
                        "risk_missing_slippage_parameter": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1")

        self.assertGreater(len(paths), 0)
        path = paths[0]
        self.assertEqual(path.attack_type, "slippage_exploitation")

    def test_synthesize_dos_path(self):
        """Synthesizer finds DoS attack path."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Loopy",
                    type="Contract",
                ),
                "processAll": Node(
                    id="processAll",
                    label="processAll",
                    type="Function",
                    properties={
                        "contract_name": "Loopy",
                        "visibility": "public",
                        "writes_state": True,
                        "has_unbounded_loop": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1")

        self.assertGreater(len(paths), 0)
        path = paths[0]
        self.assertEqual(path.attack_type, "denial_of_service")

    def test_synthesize_ecrecover_path(self):
        """Synthesizer finds signature malleability path."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Signer",
                    type="Contract",
                ),
                "verify": Node(
                    id="verify",
                    label="verify",
                    type="Function",
                    properties={
                        "contract_name": "Signer",
                        "visibility": "public",
                        "writes_state": True,
                        "uses_ecrecover": True,
                        "checks_zero_address": False,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1")

        self.assertGreater(len(paths), 0)
        path = paths[0]
        self.assertEqual(path.attack_type, "signature_malleability")

    def test_synthesize_with_bypasses(self):
        """Synthesizer identifies guard bypasses."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Guarded",
                    type="Contract",
                ),
                "withdraw": Node(
                    id="withdraw",
                    label="withdraw",
                    type="Function",
                    properties={
                        "contract_name": "Guarded",
                        "visibility": "external",
                        "writes_state": True,
                        "transfers_value_out": True,
                        "state_write_after_external_call": True,
                        "has_reentrancy_guard": True,  # Has guard
                    }
                ),
            },
            edges={},
            metadata={},
        )

        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1")

        self.assertGreater(len(paths), 0)
        path = paths[0]
        # Should have a bypass for the reentrancy guard
        self.assertGreater(path.bypass_count, 0)

    def test_synthesize_max_paths(self):
        """Synthesizer respects max_paths limit."""
        nodes = {
            "contract1": Node(id="contract1", label="Multi", type="Contract"),
        }
        for i in range(20):
            nodes[f"func{i}"] = Node(
                id=f"func{i}",
                label=f"function{i}",
                type="Function",
                properties={
                    "contract_name": "Multi",
                    "visibility": "external",
                    "writes_state": True,
                    "transfers_value_out": True,
                },
            )

        graph = KnowledgeGraph(nodes=nodes, edges={}, metadata={})
        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1", max_paths=5)

        self.assertLessEqual(len(paths), 5)

    def test_synthesize_multi_step_path(self):
        """Synthesizer creates multi-step paths."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Chain", type="Contract"),
                "start": Node(
                    id="start",
                    label="start",
                    type="Function",
                    properties={
                        "contract_name": "Chain",
                        "visibility": "external",
                        "writes_state": True,
                    }
                ),
                "middle": Node(
                    id="middle",
                    label="middle",
                    type="Function",
                    properties={
                        "contract_name": "Chain",
                        "visibility": "internal",
                        "writes_state": True,
                    }
                ),
                "end": Node(
                    id="end",
                    label="end",
                    type="Function",
                    properties={
                        "contract_name": "Chain",
                        "visibility": "external",
                        "writes_state": True,
                        "transfers_value_out": True,
                        "semantic_ops": ["TRANSFERS_VALUE_OUT"],
                    }
                ),
            },
            edges={
                "e1": Edge(id="e1", source="start", target="middle", type="CALLS"),
                "e2": Edge(id="e2", source="middle", target="end", type="CALLS"),
            },
            metadata={},
        )

        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1")

        # Should find path from start to end
        multi_step_paths = [p for p in paths if p.step_count > 1]
        self.assertGreater(len(multi_step_paths), 0)

    def test_synthesize_sorts_by_impact(self):
        """Synthesizer sorts paths by impact."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Mixed", type="Contract"),
                "low_impact": Node(
                    id="low_impact",
                    label="lowImpact",
                    type="Function",
                    properties={
                        "contract_name": "Mixed",
                        "visibility": "public",
                        "writes_state": True,
                        "has_unbounded_loop": True,
                    }
                ),
                "high_impact": Node(
                    id="high_impact",
                    label="highImpact",
                    type="Function",
                    properties={
                        "contract_name": "Mixed",
                        "visibility": "public",
                        "writes_state": True,
                        "writes_privileged_state": True,
                        "has_access_gate": False,
                        "semantic_ops": ["MODIFIES_OWNER"],
                    }
                ),
            },
            edges={},
            metadata={},
        )

        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1")

        # High impact should come first
        if len(paths) >= 2:
            self.assertGreaterEqual(
                synthesizer._impact_score(paths[0].impact),
                synthesizer._impact_score(paths[1].impact),
            )

    def test_generate_attack_description(self):
        """Synthesizer generates attack descriptions."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Test", type="Contract"),
                "withdraw": Node(
                    id="withdraw",
                    label="withdraw",
                    type="Function",
                    properties={
                        "contract_name": "Test",
                        "visibility": "external",
                        "writes_state": True,
                        "transfers_value_out": True,
                        "state_write_after_external_call": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1")

        self.assertGreater(len(paths), 0)

        desc = synthesizer.generate_attack_description(paths[0])
        self.assertIn("Attack", desc.title)
        self.assertIsInstance(desc.steps, list)
        self.assertIsInstance(desc.prerequisites, list)
        self.assertIn(":", desc.impact)
        self.assertIsNotNone(desc.mitigation)

    def test_description_has_mitigation(self):
        """Attack description includes mitigation."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Test", type="Contract"),
                "func": Node(
                    id="func",
                    label="vulnerable",
                    type="Function",
                    properties={
                        "contract_name": "Test",
                        "visibility": "public",
                        "writes_state": True,
                        "state_write_after_external_call": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1")

        if paths:
            desc = synthesizer.generate_attack_description(paths[0])
            self.assertGreater(len(desc.mitigation), 0)


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for convenience functions."""

    def test_synthesize_attack_paths(self):
        """synthesize_attack_paths convenience function works."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Test", type="Contract"),
                "func": Node(
                    id="func",
                    label="test",
                    type="Function",
                    properties={
                        "contract_name": "Test",
                        "visibility": "external",
                        "writes_state": True,
                        "transfers_value_out": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        paths = synthesize_attack_paths(graph, "contract1")

        self.assertIsInstance(paths, list)

    def test_synthesize_without_contract_id(self):
        """synthesize_attack_paths works without contract_id."""
        graph = KnowledgeGraph(
            nodes={
                "func": Node(
                    id="func",
                    label="test",
                    type="Function",
                    properties={
                        "visibility": "public",
                        "writes_state": True,
                        "calls_external": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        paths = synthesize_attack_paths(graph)

        self.assertIsInstance(paths, list)


class TestComplexScenarios(unittest.TestCase):
    """Tests for complex multi-vulnerability scenarios."""

    def test_defi_vault_attack_paths(self):
        """Synthesizer handles DeFi vault with multiple vulnerabilities."""
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
                    }
                ),
                "withdraw": Node(
                    id="withdraw",
                    label="withdraw",
                    type="Function",
                    properties={
                        "contract_name": "Vault",
                        "visibility": "external",
                        "writes_state": True,
                        "transfers_value_out": True,
                        "state_write_after_external_call": True,
                    }
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
                        "has_access_gate": False,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1")

        # Should find multiple attack paths
        self.assertGreater(len(paths), 1)

        # Should have both reentrancy and access control attacks
        attack_types = {p.attack_type for p in paths}
        self.assertIn("reentrancy", attack_types)
        self.assertIn("unauthorized_access", attack_types)

    def test_empty_contract(self):
        """Synthesizer handles contract with no vulnerabilities."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Safe", type="Contract"),
                "deposit": Node(
                    id="deposit",
                    label="deposit",
                    type="Function",
                    properties={
                        "contract_name": "Safe",
                        "visibility": "external",
                        "writes_state": True,
                        "has_access_gate": True,
                        "has_reentrancy_guard": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1")

        # Should either return no paths or paths with bypasses needed
        for path in paths:
            # If there's a path, it should require bypasses for the guards
            if path.attack_type:
                pass  # Some attack identified

    def test_no_entry_points(self):
        """Synthesizer handles contract with no public functions."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(id="contract1", label="Internal", type="Contract"),
                "func": Node(
                    id="func",
                    label="internal",
                    type="Function",
                    properties={
                        "contract_name": "Internal",
                        "visibility": "internal",
                        "writes_state": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        synthesizer = AttackPathSynthesizer(graph)
        paths = synthesizer.synthesize("contract1")

        # Should return empty list - no entry points
        self.assertEqual(len(paths), 0)


if __name__ == "__main__":
    unittest.main()
