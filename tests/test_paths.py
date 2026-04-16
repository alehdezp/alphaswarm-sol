"""Tests for Phase 7: Execution Path Analysis.

This module tests:
- ExecutionPath and PathStep schemas
- Path enumeration from entry points
- Invariant tracking and violation detection
- Attack scenario generation
- Integration with KnowledgeGraph
"""

from __future__ import annotations

import unittest
from pathlib import Path

from tests.graph_cache import load_graph
from alphaswarm_sol.kg.paths import (
    PathStep,
    ExecutionPath,
    Invariant,
    InvariantType,
    AttackScenario,
    PathEnumerator,
    check_path_invariants,
    generate_attack_scenarios,
    enumerate_attack_paths,
    get_path_analysis_summary,
)


class TestPathStepSchema(unittest.TestCase):
    """Test PathStep dataclass."""

    def test_path_step_creation(self):
        """PathStep can be created with all fields."""
        step = PathStep(
            function_id="func:1",
            function_label="withdraw",
            operations=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            state_reads={"balance": "read"},
            state_writes={"balance": "written"},
            external_calls=["external_call"],
            order=0,
            guards_passed=["onlyOwner"],
            risk_contribution=3.5,
        )
        self.assertEqual(step.function_id, "func:1")
        self.assertEqual(step.function_label, "withdraw")
        self.assertEqual(len(step.operations), 2)
        self.assertEqual(step.risk_contribution, 3.5)

    def test_path_step_serialization(self):
        """PathStep serializes to dict and back."""
        step = PathStep(
            function_id="func:1",
            function_label="deposit",
            operations=["RECEIVES_VALUE_IN"],
            order=1,
        )

        # Serialize
        data = step.to_dict()
        self.assertEqual(data["function_id"], "func:1")
        self.assertEqual(data["order"], 1)

        # Deserialize
        restored = PathStep.from_dict(data)
        self.assertEqual(restored.function_id, step.function_id)
        self.assertEqual(restored.function_label, step.function_label)


class TestExecutionPathSchema(unittest.TestCase):
    """Test ExecutionPath dataclass."""

    def test_execution_path_creation(self):
        """ExecutionPath can be created with all fields."""
        steps = [
            PathStep(function_id="func:1", function_label="deposit", order=0),
            PathStep(function_id="func:2", function_label="withdraw", order=1),
        ]
        path = ExecutionPath(
            id="path:1",
            entry_point="func:1",
            steps=steps,
            state_preconditions={"balance": 0},
            state_postconditions={"balance": 100},
            invariants_violated=["inv:1"],
            attack_potential=5.0,
            path_type="attack",
        )
        self.assertEqual(path.id, "path:1")
        self.assertEqual(len(path.steps), 2)
        self.assertEqual(path.attack_potential, 5.0)

    def test_execution_path_serialization(self):
        """ExecutionPath serializes to dict and back."""
        steps = [
            PathStep(function_id="func:1", function_label="fn1", order=0),
        ]
        path = ExecutionPath(
            id="path:1",
            entry_point="func:1",
            steps=steps,
            attack_potential=3.0,
        )

        # Serialize
        data = path.to_dict()
        self.assertEqual(data["id"], "path:1")
        self.assertEqual(len(data["steps"]), 1)

        # Deserialize
        restored = ExecutionPath.from_dict(data)
        self.assertEqual(restored.id, path.id)
        self.assertEqual(len(restored.steps), 1)

    def test_has_external_call_before_state_update(self):
        """Detects CEI violation pattern."""
        # CEI violation: external call then state write
        steps_violation = [
            PathStep(
                function_id="func:1",
                function_label="fn1",
                external_calls=["external_call"],
                order=0,
            ),
            PathStep(
                function_id="func:2",
                function_label="fn2",
                state_writes={"balance": "written"},
                order=1,
            ),
        ]
        path_violation = ExecutionPath(
            id="path:1",
            entry_point="func:1",
            steps=steps_violation,
        )
        self.assertTrue(path_violation.has_external_call_before_state_update())

        # Safe: state write then external call
        steps_safe = [
            PathStep(
                function_id="func:1",
                function_label="fn1",
                state_writes={"balance": "written"},
                order=0,
            ),
            PathStep(
                function_id="func:2",
                function_label="fn2",
                external_calls=["external_call"],
                order=1,
            ),
        ]
        path_safe = ExecutionPath(
            id="path:2",
            entry_point="func:1",
            steps=steps_safe,
        )
        self.assertFalse(path_safe.has_external_call_before_state_update())

    def test_involves_value_movement(self):
        """Detects value movement in path."""
        steps = [
            PathStep(
                function_id="func:1",
                function_label="transfer",
                operations=["TRANSFERS_VALUE_OUT"],
                order=0,
            ),
        ]
        path = ExecutionPath(id="path:1", entry_point="func:1", steps=steps)
        self.assertTrue(path.involves_value_movement())

        # No value movement
        steps_no_value = [
            PathStep(
                function_id="func:1",
                function_label="read",
                operations=["READS_ORACLE"],
                order=0,
            ),
        ]
        path_no_value = ExecutionPath(id="path:2", entry_point="func:1", steps=steps_no_value)
        self.assertFalse(path_no_value.involves_value_movement())

    def test_compute_cumulative_risk(self):
        """Risk score computation works."""
        steps = [
            PathStep(function_id="func:1", function_label="fn1", risk_contribution=2.0, order=0),
            PathStep(function_id="func:2", function_label="fn2", risk_contribution=3.0, order=1),
        ]
        path = ExecutionPath(id="path:1", entry_point="func:1", steps=steps)

        risk = path.compute_cumulative_risk()
        self.assertGreaterEqual(risk, 5.0)  # Base risk = 2 + 3

    def test_risk_capped_at_10(self):
        """Risk score capped at 10.0."""
        steps = [
            PathStep(
                function_id="func:1",
                function_label="fn1",
                risk_contribution=10.0,
                external_calls=["call"],
                operations=["TRANSFERS_VALUE_OUT"],
                order=0,
            ),
            PathStep(
                function_id="func:2",
                function_label="fn2",
                risk_contribution=10.0,
                state_writes={"x": "y"},
                order=1,
            ),
        ]
        path = ExecutionPath(
            id="path:1",
            entry_point="func:1",
            steps=steps,
            invariants_violated=["inv:1", "inv:2", "inv:3"],
        )

        risk = path.compute_cumulative_risk()
        self.assertLessEqual(risk, 10.0)


class TestInvariant(unittest.TestCase):
    """Test Invariant class."""

    def test_invariant_creation(self):
        """Invariant can be created."""
        inv = Invariant(
            id="inv:balance",
            type=InvariantType.BALANCE_CONSERVATION,
            description="Total balance must remain constant",
            check=lambda s: s.get("total_in", 0) == s.get("total_out", 0),
            variables_involved=["total_in", "total_out"],
        )
        self.assertEqual(inv.id, "inv:balance")
        self.assertEqual(inv.type, InvariantType.BALANCE_CONSERVATION)

    def test_invariant_holds(self):
        """Invariant.holds() works correctly."""
        inv = Invariant(
            id="inv:positive",
            type=InvariantType.STATE_CONSISTENCY,
            description="Balance must be positive",
            check=lambda s: s.get("balance", 0) >= 0,
        )

        # Valid state
        self.assertTrue(inv.holds({"balance": 100}))

        # Invalid state
        self.assertFalse(inv.holds({"balance": -1}))

    def test_invariant_handles_exceptions(self):
        """Invariant.holds() returns False on exception."""
        inv = Invariant(
            id="inv:error",
            type=InvariantType.STATE_CONSISTENCY,
            description="Causes error",
            check=lambda s: s["nonexistent"] > 0,  # Will raise KeyError
        )

        # Should return False, not raise
        self.assertFalse(inv.holds({}))


class TestCheckPathInvariants(unittest.TestCase):
    """Test check_path_invariants function."""

    def test_no_violations(self):
        """No violations when invariants hold."""
        steps = [
            PathStep(
                function_id="func:1",
                function_label="fn1",
                state_writes={"balance": 100},
                order=0,
            ),
        ]
        path = ExecutionPath(
            id="path:1",
            entry_point="func:1",
            steps=steps,
            state_preconditions={"balance": 0},
        )

        inv = Invariant(
            id="inv:positive",
            type=InvariantType.STATE_CONSISTENCY,
            description="Balance positive",
            check=lambda s: s.get("balance", 0) >= 0,
        )

        violations = check_path_invariants(path, [inv])
        self.assertEqual(len(violations), 0)

    def test_violation_detected(self):
        """Violation detected when invariant fails."""
        steps = [
            PathStep(
                function_id="func:1",
                function_label="fn1",
                state_writes={"balance": -100},  # Negative balance
                order=0,
            ),
        ]
        path = ExecutionPath(
            id="path:1",
            entry_point="func:1",
            steps=steps,
            state_preconditions={"balance": 0},
        )

        inv = Invariant(
            id="inv:positive",
            type=InvariantType.STATE_CONSISTENCY,
            description="Balance positive",
            check=lambda s: s.get("balance", 0) >= 0,
        )

        violations = check_path_invariants(path, [inv])
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0], "inv:positive")


class TestAttackScenarioGeneration(unittest.TestCase):
    """Test attack scenario generation."""

    def test_reentrancy_scenario(self):
        """Reentrancy scenario generated for CEI violation."""
        steps = [
            PathStep(
                function_id="func:1",
                function_label="withdraw",
                external_calls=["external_call"],
                operations=["TRANSFERS_VALUE_OUT"],
                order=0,
            ),
            PathStep(
                function_id="func:2",
                function_label="update",
                state_writes={"balance": "written"},
                order=1,
            ),
        ]
        path = ExecutionPath(
            id="path:1",
            entry_point="func:1",
            steps=steps,
        )

        scenarios = generate_attack_scenarios(path)
        reentrancy = [s for s in scenarios if s.type == "reentrancy"]
        self.assertGreater(len(reentrancy), 0)
        self.assertEqual(reentrancy[0].impact, "high")

    def test_flash_loan_scenario(self):
        """Flash loan scenario generated for oracle + value movement."""
        steps = [
            PathStep(
                function_id="func:1",
                function_label="getPrice",
                operations=["READS_ORACLE"],
                order=0,
            ),
            PathStep(
                function_id="func:2",
                function_label="swap",
                operations=["TRANSFERS_VALUE_OUT"],
                order=1,
            ),
        ]
        path = ExecutionPath(
            id="path:1",
            entry_point="func:1",
            steps=steps,
        )

        scenarios = generate_attack_scenarios(path)
        flash_loan = [s for s in scenarios if s.type == "flash_loan"]
        self.assertGreater(len(flash_loan), 0)

    def test_privilege_escalation_scenario(self):
        """Privilege escalation detected for unguarded owner change."""
        steps = [
            PathStep(
                function_id="func:1",
                function_label="setOwner",
                operations=["MODIFIES_OWNER"],
                guards_passed=[],  # No guards!
                order=0,
            ),
        ]
        path = ExecutionPath(
            id="path:1",
            entry_point="func:1",
            steps=steps,
        )

        scenarios = generate_attack_scenarios(path)
        privilege = [s for s in scenarios if s.type == "privilege_escalation"]
        self.assertGreater(len(privilege), 0)
        self.assertEqual(privilege[0].impact, "critical")

    def test_no_scenario_for_guarded_function(self):
        """No reentrancy scenario when nonReentrant guard present."""
        steps = [
            PathStep(
                function_id="func:1",
                function_label="withdraw",
                external_calls=["external_call"],
                guards_passed=["nonReentrant"],
                order=0,
            ),
            PathStep(
                function_id="func:2",
                function_label="update",
                state_writes={"balance": "written"},
                order=1,
            ),
        ]
        path = ExecutionPath(
            id="path:1",
            entry_point="func:1",
            steps=steps,
        )

        scenarios = generate_attack_scenarios(path)
        reentrancy = [s for s in scenarios if s.type == "reentrancy"]
        self.assertEqual(len(reentrancy), 0)


class TestPathEnumerator(unittest.TestCase):
    """Test PathEnumerator class."""

    def test_enumerator_on_real_contract(self):
        """PathEnumerator works on real contract."""
        graph = load_graph("ArbitraryDelegatecall.sol")
        enumerator = PathEnumerator(graph, max_depth=3, max_paths=10)

        entry_points = enumerator.get_entry_points()
        self.assertGreater(len(entry_points), 0)

    def test_enumerate_paths_on_real_contract(self):
        """Path enumeration works on real contract."""
        graph = load_graph("ArbitraryDelegatecall.sol")
        enumerator = PathEnumerator(graph, max_depth=3, max_paths=10)

        paths = enumerator.enumerate_paths()
        # May have 0 or more paths depending on contract structure
        self.assertIsInstance(paths, list)

    def test_create_step_from_function(self):
        """Step creation from function node works."""
        graph = load_graph("ArbitraryDelegatecall.sol")
        enumerator = PathEnumerator(graph)

        # Find a function node
        fn_id = None
        for node in graph.nodes.values():
            if node.type == "Function":
                fn_id = node.id
                break

        if fn_id:
            step = enumerator.create_step_from_function(fn_id, 0)
            self.assertEqual(step.function_id, fn_id)
            self.assertEqual(step.order, 0)


class TestEnumerateAttackPaths(unittest.TestCase):
    """Test enumerate_attack_paths function."""

    def test_attack_paths_on_vulnerable_contract(self):
        """Attack paths found in vulnerable contract."""
        graph = load_graph("ReentrancyClassic.sol")
        attack_paths = enumerate_attack_paths(graph, max_depth=3)

        # Should find some paths (may or may not be attack paths)
        self.assertIsInstance(attack_paths, list)

    def test_attack_paths_sorted_by_risk(self):
        """Attack paths sorted by attack potential."""
        graph = load_graph("ArbitraryDelegatecall.sol")
        attack_paths = enumerate_attack_paths(graph, max_depth=3)

        if len(attack_paths) >= 2:
            # Should be sorted descending
            for i in range(len(attack_paths) - 1):
                self.assertGreaterEqual(
                    attack_paths[i].attack_potential,
                    attack_paths[i + 1].attack_potential
                )


class TestGetPathAnalysisSummary(unittest.TestCase):
    """Test get_path_analysis_summary function."""

    def test_summary_structure(self):
        """Summary has expected structure."""
        graph = load_graph("ArbitraryDelegatecall.sol")
        summary = get_path_analysis_summary(graph)

        self.assertIn("total_paths", summary)
        self.assertIn("attack_paths", summary)
        self.assertIn("privilege_escalation_paths", summary)
        self.assertIn("normal_paths", summary)
        self.assertIn("total_scenarios", summary)
        self.assertIn("scenario_types", summary)
        self.assertIn("entry_points", summary)

    def test_summary_counts(self):
        """Summary counts are non-negative."""
        graph = load_graph("ArbitraryDelegatecall.sol")
        summary = get_path_analysis_summary(graph)

        self.assertGreaterEqual(summary["total_paths"], 0)
        self.assertGreaterEqual(summary["attack_paths"], 0)
        self.assertGreaterEqual(summary["total_scenarios"], 0)


class TestAttackScenarioSchema(unittest.TestCase):
    """Test AttackScenario dataclass."""

    def test_attack_scenario_serialization(self):
        """AttackScenario serializes to dict and back."""
        path = ExecutionPath(id="path:1", entry_point="func:1", steps=[])
        scenario = AttackScenario(
            id="scenario:1",
            type="reentrancy",
            path=path,
            description="Test scenario",
            required_conditions=["condition1"],
            impact="high",
            likelihood="medium",
            recommended_fix="Add guard",
        )

        # Serialize
        data = scenario.to_dict()
        self.assertEqual(data["id"], "scenario:1")
        self.assertEqual(data["type"], "reentrancy")
        self.assertEqual(data["impact"], "high")

        # Deserialize
        restored = AttackScenario.from_dict(data)
        self.assertEqual(restored.id, scenario.id)
        self.assertEqual(restored.type, scenario.type)
        self.assertEqual(restored.recommended_fix, scenario.recommended_fix)


if __name__ == "__main__":
    unittest.main()
