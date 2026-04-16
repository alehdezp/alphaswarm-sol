"""Tests for operation sequencing (Phase 2).

This module tests the sequencing functionality that enables pattern
detection based on operation ordering.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from tests.graph_cache import load_graph
from alphaswarm_sol.kg.sequencing import (
    OrderedOperation,
    extract_operation_sequence,
    get_ordering_pairs,
    has_ordering,
    detect_vulnerable_reentrancy_pattern,
    detect_cei_pattern,
    compute_signature_from_fn,
    SemanticOperation,
    OperationOccurrence,
    compute_behavioral_signature,
    compute_ordering_pairs,
)


class TestOrderedOperation(unittest.TestCase):
    """Test the OrderedOperation dataclass."""

    def test_creation(self):
        """OrderedOperation can be created with all fields."""
        op = OrderedOperation(
            operation="TRANSFERS_VALUE_OUT",
            cfg_order=0,
            node_id=1,
            line_number=10,
            detail="ETH via transfer",
        )
        self.assertEqual(op.operation, "TRANSFERS_VALUE_OUT")
        self.assertEqual(op.cfg_order, 0)
        self.assertEqual(op.node_id, 1)
        self.assertEqual(op.line_number, 10)
        self.assertEqual(op.detail, "ETH via transfer")

    def test_optional_detail(self):
        """OrderedOperation detail is optional."""
        op = OrderedOperation(
            operation="CALLS_EXTERNAL",
            cfg_order=1,
            node_id=2,
            line_number=15,
        )
        self.assertIsNone(op.detail)


class TestOrderingPairsComputation(unittest.TestCase):
    """Test compute_ordering_pairs function."""

    def test_empty_list(self):
        """Empty operations produce no pairs."""
        pairs = compute_ordering_pairs([])
        self.assertEqual(pairs, [])

    def test_single_operation(self):
        """Single operation produces no pairs."""
        ops = [
            OperationOccurrence(
                operation=SemanticOperation.CALLS_EXTERNAL,
                cfg_order=0,
                line_number=10,
            )
        ]
        pairs = compute_ordering_pairs(ops)
        self.assertEqual(pairs, [])

    def test_two_operations(self):
        """Two operations produce one pair."""
        ops = [
            OperationOccurrence(
                operation=SemanticOperation.CALLS_EXTERNAL,
                cfg_order=0,
                line_number=10,
            ),
            OperationOccurrence(
                operation=SemanticOperation.WRITES_USER_BALANCE,
                cfg_order=1,
                line_number=15,
            ),
        ]
        pairs = compute_ordering_pairs(ops)
        self.assertEqual(len(pairs), 1)
        self.assertIn(("CALLS_EXTERNAL", "WRITES_USER_BALANCE"), pairs)

    def test_vulnerable_pattern_pairs(self):
        """Vulnerable reentrancy pattern produces correct pairs."""
        ops = [
            OperationOccurrence(
                operation=SemanticOperation.READS_USER_BALANCE,
                cfg_order=0,
                line_number=10,
            ),
            OperationOccurrence(
                operation=SemanticOperation.TRANSFERS_VALUE_OUT,
                cfg_order=1,
                line_number=12,
            ),
            OperationOccurrence(
                operation=SemanticOperation.WRITES_USER_BALANCE,
                cfg_order=2,
                line_number=15,
            ),
        ]
        pairs = compute_ordering_pairs(ops)
        # Should have 3 pairs: (R, X), (R, W), (X, W)
        self.assertEqual(len(pairs), 3)
        # Critical vulnerable pattern: external before write
        self.assertIn(("TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"), pairs)

    def test_order_is_preserved(self):
        """Operations are sorted by CFG order for pair computation."""
        # Input out of order
        ops = [
            OperationOccurrence(
                operation=SemanticOperation.WRITES_USER_BALANCE,
                cfg_order=2,
                line_number=15,
            ),
            OperationOccurrence(
                operation=SemanticOperation.READS_USER_BALANCE,
                cfg_order=0,
                line_number=10,
            ),
            OperationOccurrence(
                operation=SemanticOperation.TRANSFERS_VALUE_OUT,
                cfg_order=1,
                line_number=12,
            ),
        ]
        pairs = compute_ordering_pairs(ops)
        # Should still produce correct ordering pairs
        self.assertIn(("READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"), pairs)
        self.assertIn(("READS_USER_BALANCE", "WRITES_USER_BALANCE"), pairs)
        self.assertIn(("TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"), pairs)
        # Should NOT have reverse ordering
        self.assertNotIn(("WRITES_USER_BALANCE", "READS_USER_BALANCE"), pairs)


class TestOpOrderingInGraph(unittest.TestCase):
    """Test op_ordering property in graph nodes."""

    @classmethod
    def setUpClass(cls):
        """Load the test contract graph once for all tests."""
        cls.graph = load_graph("OperationsTest.sol")

    def _get_function_props(self, func_name: str) -> dict:
        """Get properties for a function by signature match."""
        for node in self.graph.nodes.values():
            if node.type == "Function" and func_name in node.label:
                return node.properties
        self.fail(f"Function {func_name} not found in graph")

    def test_all_functions_have_op_ordering(self):
        """All functions should have op_ordering property."""
        for node in self.graph.nodes.values():
            if node.type == "Function":
                self.assertIn("op_ordering", node.properties)
                self.assertIsInstance(node.properties["op_ordering"], list)

    def test_op_ordering_contains_tuples(self):
        """op_ordering should contain tuples of operation names."""
        props = self._get_function_props("withdrawVulnerable")
        ordering = props["op_ordering"]
        for pair in ordering:
            self.assertIsInstance(pair, (list, tuple))
            self.assertEqual(len(pair), 2)
            self.assertIsInstance(pair[0], str)
            self.assertIsInstance(pair[1], str)

    def test_vulnerable_withdrawal_has_external_before_write(self):
        """Vulnerable withdrawal should have external call before balance write."""
        props = self._get_function_props("withdrawVulnerable")
        ordering = props["op_ordering"]
        # Convert to tuples for comparison
        ordering_tuples = [tuple(p) for p in ordering]
        # Should have TRANSFERS_VALUE_OUT before WRITES_USER_BALANCE
        self.assertIn(
            ("TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"),
            ordering_tuples,
            "Vulnerable pattern: TRANSFERS_VALUE_OUT should come before WRITES_USER_BALANCE"
        )

    def test_cei_withdrawal_has_write_before_external(self):
        """CEI withdrawal should have balance write before external call."""
        props = self._get_function_props("withdrawCEI")
        ordering = props["op_ordering"]
        # Convert to tuples for comparison
        ordering_tuples = [tuple(p) for p in ordering]
        # Should have WRITES_USER_BALANCE before TRANSFERS_VALUE_OUT
        self.assertIn(
            ("WRITES_USER_BALANCE", "TRANSFERS_VALUE_OUT"),
            ordering_tuples,
            "CEI pattern: WRITES_USER_BALANCE should come before TRANSFERS_VALUE_OUT"
        )

    def test_empty_function_has_empty_ordering(self):
        """Functions with no operations should have empty ordering."""
        # Constructor or simple getter should have minimal/empty ordering
        for node in self.graph.nodes.values():
            if node.type == "Function":
                ordering = node.properties.get("op_ordering", [])
                # Empty ordering is a valid case
                if not node.properties.get("semantic_ops"):
                    self.assertEqual(ordering, [])


class TestSequenceOrderPatternMatching(unittest.TestCase):
    """Test that sequence_order pattern matching works with op_ordering."""

    @classmethod
    def setUpClass(cls):
        """Load the test contract graph."""
        cls.graph = load_graph("OperationsTest.sol")

    def _get_function_props(self, func_name: str) -> dict:
        """Get properties for a function by signature match."""
        for node in self.graph.nodes.values():
            if node.type == "Function" and func_name in node.label:
                return node.properties
        self.fail(f"Function {func_name} not found in graph")

    def _matches_sequence_order(
        self, func_name: str, before: str, after: str
    ) -> bool:
        """Check if sequence_order condition matches for a function."""
        props = self._get_function_props(func_name)
        ordering = props.get("op_ordering", [])
        return any(
            tuple(p) == (before, after) for p in ordering
        )

    def test_vulnerable_matches_external_before_write(self):
        """Vulnerable function matches external before write pattern."""
        result = self._matches_sequence_order(
            "withdrawVulnerable",
            "TRANSFERS_VALUE_OUT",
            "WRITES_USER_BALANCE"
        )
        self.assertTrue(result)

    def test_cei_does_not_match_external_before_write(self):
        """CEI function does NOT match external before write pattern."""
        result = self._matches_sequence_order(
            "withdrawCEI",
            "TRANSFERS_VALUE_OUT",
            "WRITES_USER_BALANCE"
        )
        self.assertFalse(result)

    def test_cei_matches_write_before_external(self):
        """CEI function matches write before external pattern."""
        result = self._matches_sequence_order(
            "withdrawCEI",
            "WRITES_USER_BALANCE",
            "TRANSFERS_VALUE_OUT"
        )
        self.assertTrue(result)


class TestBehavioralSignatureVsOrdering(unittest.TestCase):
    """Test relationship between behavioral signature and ordering pairs."""

    def test_signature_reflects_ordering(self):
        """Behavioral signature order should match ordering pairs."""
        ops = [
            OperationOccurrence(
                operation=SemanticOperation.READS_USER_BALANCE,
                cfg_order=0,
                line_number=10,
            ),
            OperationOccurrence(
                operation=SemanticOperation.TRANSFERS_VALUE_OUT,
                cfg_order=1,
                line_number=12,
            ),
            OperationOccurrence(
                operation=SemanticOperation.WRITES_USER_BALANCE,
                cfg_order=2,
                line_number=15,
            ),
        ]
        sig = compute_behavioral_signature(ops)
        pairs = compute_ordering_pairs(ops)

        # Signature should be R:bal→X:out→W:bal
        self.assertIn("R:bal", sig)
        self.assertIn("X:out", sig)
        self.assertIn("W:bal", sig)

        # Pairs should reflect the same ordering
        self.assertIn(("READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"), pairs)
        self.assertIn(("TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"), pairs)


class TestReentrancyVulnerabilityTestContracts(unittest.TestCase):
    """Test sequencing on reentrancy vulnerability test contracts."""

    @classmethod
    def setUpClass(cls):
        """Load ValueMovementReentrancy contract."""
        cls.graph = load_graph("ValueMovementReentrancy.sol")

    def _get_function_props(self, func_name: str) -> dict:
        """Get properties for a function by signature match."""
        for node in self.graph.nodes.values():
            if node.type == "Function" and func_name in node.label:
                return node.properties
        self.fail(f"Function {func_name} not found in graph")

    def test_vulnerable_functions_have_op_ordering(self):
        """Vulnerable reentrancy functions should have op_ordering."""
        for node in self.graph.nodes.values():
            if node.type == "Function":
                props = node.properties
                self.assertIn("op_ordering", props)

    def test_behavioral_signatures_present(self):
        """All functions should have behavioral signatures."""
        for node in self.graph.nodes.values():
            if node.type == "Function":
                props = node.properties
                self.assertIn("behavioral_signature", props)
                # Signature can be empty for trivial functions
                self.assertIsInstance(props["behavioral_signature"], str)


if __name__ == "__main__":
    unittest.main()
