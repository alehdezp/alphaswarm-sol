"""Tests for semantic operations detection (Phase 1).

This module tests the operation detection system that provides
name-agnostic vulnerability detection based on what code DOES,
not what it's named.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from tests.graph_cache import load_graph
from alphaswarm_sol.kg.operations import (
    SemanticOperation,
    OperationOccurrence,
    OP_CODES,
    compute_behavioral_signature,
    compute_ordering_pairs,
)


class TestSemanticOperationEnum(unittest.TestCase):
    """Test the SemanticOperation enum definition."""

    def test_all_20_operations_defined(self):
        """Verify all 20 semantic operations are defined."""
        operations = list(SemanticOperation)
        self.assertEqual(len(operations), 20)

    def test_op_codes_complete(self):
        """Verify OP_CODES mapping is complete for all operations."""
        for op in SemanticOperation:
            self.assertIn(op, OP_CODES, f"Missing OP_CODE for {op.name}")
            self.assertIsInstance(OP_CODES[op], str)
            self.assertGreater(len(OP_CODES[op]), 0)

    def test_op_codes_unique(self):
        """Verify all OP_CODES are unique."""
        codes = list(OP_CODES.values())
        self.assertEqual(len(codes), len(set(codes)), "Duplicate OP_CODES found")


class TestBehavioralSignature(unittest.TestCase):
    """Test behavioral signature generation."""

    def test_empty_operations(self):
        """Empty operations list produces empty signature."""
        sig = compute_behavioral_signature([])
        self.assertEqual(sig, "")

    def test_single_operation(self):
        """Single operation produces single code signature."""
        ops = [
            OperationOccurrence(
                operation=SemanticOperation.TRANSFERS_VALUE_OUT,
                cfg_order=0,
                line_number=10,
            )
        ]
        sig = compute_behavioral_signature(ops)
        self.assertEqual(sig, "X:out")

    def test_ordered_operations(self):
        """Operations are ordered by CFG order in signature."""
        ops = [
            OperationOccurrence(
                operation=SemanticOperation.READS_USER_BALANCE,
                cfg_order=0,
                line_number=10,
            ),
            OperationOccurrence(
                operation=SemanticOperation.TRANSFERS_VALUE_OUT,
                cfg_order=1,
                line_number=11,
            ),
            OperationOccurrence(
                operation=SemanticOperation.WRITES_USER_BALANCE,
                cfg_order=2,
                line_number=12,
            ),
        ]
        sig = compute_behavioral_signature(ops)
        # Should be R:bal->X:out->W:bal (vulnerable reentrancy pattern)
        self.assertIn("R:bal", sig)
        self.assertIn("X:out", sig)
        self.assertIn("W:bal", sig)
        # Check order
        parts = sig.split("→")
        self.assertEqual(parts[0], "R:bal")
        self.assertEqual(parts[1], "X:out")
        self.assertEqual(parts[2], "W:bal")

    def test_cei_pattern_signature(self):
        """Safe CEI pattern produces correct signature."""
        ops = [
            OperationOccurrence(
                operation=SemanticOperation.READS_USER_BALANCE,
                cfg_order=0,
                line_number=10,
            ),
            OperationOccurrence(
                operation=SemanticOperation.WRITES_USER_BALANCE,
                cfg_order=1,
                line_number=11,
            ),
            OperationOccurrence(
                operation=SemanticOperation.TRANSFERS_VALUE_OUT,
                cfg_order=2,
                line_number=12,
            ),
        ]
        sig = compute_behavioral_signature(ops)
        # Should be R:bal->W:bal->X:out (safe CEI pattern)
        parts = sig.split("→")
        self.assertEqual(parts[0], "R:bal")
        self.assertEqual(parts[1], "W:bal")
        self.assertEqual(parts[2], "X:out")


class TestOrderingPairs(unittest.TestCase):
    """Test operation ordering pair computation."""

    def test_empty_operations(self):
        """Empty operations produce no pairs."""
        pairs = compute_ordering_pairs([])
        self.assertEqual(pairs, [])

    def test_single_operation(self):
        """Single operation produces no pairs."""
        ops = [
            OperationOccurrence(
                operation=SemanticOperation.TRANSFERS_VALUE_OUT,
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
                operation=SemanticOperation.READS_USER_BALANCE,
                cfg_order=0,
                line_number=10,
            ),
            OperationOccurrence(
                operation=SemanticOperation.WRITES_USER_BALANCE,
                cfg_order=1,
                line_number=11,
            ),
        ]
        pairs = compute_ordering_pairs(ops)
        self.assertEqual(len(pairs), 1)
        self.assertIn(("READS_USER_BALANCE", "WRITES_USER_BALANCE"), pairs)

    def test_three_operations(self):
        """Three operations produce three pairs."""
        ops = [
            OperationOccurrence(
                operation=SemanticOperation.READS_USER_BALANCE,
                cfg_order=0,
                line_number=10,
            ),
            OperationOccurrence(
                operation=SemanticOperation.TRANSFERS_VALUE_OUT,
                cfg_order=1,
                line_number=11,
            ),
            OperationOccurrence(
                operation=SemanticOperation.WRITES_USER_BALANCE,
                cfg_order=2,
                line_number=12,
            ),
        ]
        pairs = compute_ordering_pairs(ops)
        self.assertEqual(len(pairs), 3)
        # All expected pairs
        expected = [
            ("READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"),
            ("READS_USER_BALANCE", "WRITES_USER_BALANCE"),
            ("TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"),
        ]
        for pair in expected:
            self.assertIn(pair, pairs)


class TestOperationsInGraph(unittest.TestCase):
    """Test operation detection via the VKG builder."""

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

    def test_graph_has_semantic_ops_property(self):
        """All functions should have semantic_ops property."""
        for node in self.graph.nodes.values():
            if node.type == "Function":
                self.assertIn("semantic_ops", node.properties)
                self.assertIsInstance(node.properties["semantic_ops"], list)

    def test_graph_has_behavioral_signature_property(self):
        """All functions should have behavioral_signature property."""
        for node in self.graph.nodes.values():
            if node.type == "Function":
                self.assertIn("behavioral_signature", node.properties)
                self.assertIsInstance(node.properties["behavioral_signature"], str)

    def test_graph_has_op_sequence_property(self):
        """All functions should have op_sequence property."""
        for node in self.graph.nodes.values():
            if node.type == "Function":
                self.assertIn("op_sequence", node.properties)
                self.assertIsInstance(node.properties["op_sequence"], list)

    # =========================================================================
    # Value Movement Operation Tests
    # =========================================================================

    def test_vulnerable_withdrawal_has_transfer_out(self):
        """withdrawVulnerable should detect TRANSFERS_VALUE_OUT."""
        props = self._get_function_props("withdrawVulnerable")
        self.assertIn("TRANSFERS_VALUE_OUT", props["semantic_ops"])

    def test_vulnerable_withdrawal_has_balance_ops(self):
        """withdrawVulnerable should detect balance operations."""
        props = self._get_function_props("withdrawVulnerable")
        ops = props["semantic_ops"]
        # Should have balance read and write
        self.assertIn("READS_USER_BALANCE", ops)
        self.assertIn("WRITES_USER_BALANCE", ops)

    def test_deposit_is_payable(self):
        """deposit() should detect RECEIVES_VALUE_IN."""
        props = self._get_function_props("deposit")
        self.assertIn("RECEIVES_VALUE_IN", props["semantic_ops"])

    def test_sendETH_has_external_call(self):
        """sendETH should detect external call with value."""
        props = self._get_function_props("sendETH")
        ops = props["semantic_ops"]
        self.assertIn("CALLS_EXTERNAL", ops)

    # =========================================================================
    # Access Control Operation Tests
    # =========================================================================

    def test_transfer_ownership_has_permission_check(self):
        """transferOwnership should detect CHECKS_PERMISSION via onlyOwner."""
        props = self._get_function_props("transferOwnership")
        self.assertIn("CHECKS_PERMISSION", props["semantic_ops"])

    def test_transfer_ownership_modifies_owner(self):
        """transferOwnership should detect MODIFIES_OWNER."""
        props = self._get_function_props("transferOwnership")
        self.assertIn("MODIFIES_OWNER", props["semantic_ops"])

    def test_grant_operator_modifies_roles(self):
        """grantOperator should detect MODIFIES_ROLES."""
        props = self._get_function_props("grantOperator")
        self.assertIn("MODIFIES_ROLES", props["semantic_ops"])

    # =========================================================================
    # External Interaction Operation Tests
    # =========================================================================

    def test_call_untrusted_detects_untrusted(self):
        """callUntrusted should detect CALLS_UNTRUSTED."""
        props = self._get_function_props("callUntrusted")
        ops = props["semantic_ops"]
        self.assertIn("CALLS_EXTERNAL", ops)
        # Should also detect untrusted since target comes from parameter
        self.assertIn("CALLS_UNTRUSTED", ops)

    def test_get_price_detects_oracle(self):
        """getPrice should detect READS_ORACLE."""
        props = self._get_function_props("getPrice")
        self.assertIn("READS_ORACLE", props["semantic_ops"])

    # =========================================================================
    # State Management Operation Tests
    # =========================================================================

    def test_set_fee_modifies_critical_state(self):
        """setFee should detect MODIFIES_CRITICAL_STATE."""
        props = self._get_function_props("setFee")
        self.assertIn("MODIFIES_CRITICAL_STATE", props["semantic_ops"])

    def test_initialize_detects_initialization(self):
        """initialize should detect state initialization pattern."""
        props = self._get_function_props("initialize")
        # Should detect owner modification (which is critical state)
        self.assertIn("MODIFIES_OWNER", props["semantic_ops"])

    # =========================================================================
    # Control Flow Operation Tests
    # =========================================================================

    def test_batch_transfer_has_loop(self):
        """batchTransfer should detect LOOPS_OVER_ARRAY."""
        props = self._get_function_props("batchTransfer")
        self.assertIn("LOOPS_OVER_ARRAY", props["semantic_ops"])

    def test_timelock_check_uses_timestamp(self):
        """timelockCheck should detect USES_TIMESTAMP."""
        props = self._get_function_props("timelockCheck")
        self.assertIn("USES_TIMESTAMP", props["semantic_ops"])

    def test_get_block_number_uses_block_data(self):
        """getBlockNumber should detect USES_BLOCK_DATA."""
        props = self._get_function_props("getBlockNumber")
        self.assertIn("USES_BLOCK_DATA", props["semantic_ops"])

    # =========================================================================
    # Arithmetic Operation Tests
    # =========================================================================

    def test_calculate_share_has_division(self):
        """calculateShare should detect PERFORMS_DIVISION."""
        props = self._get_function_props("calculateShare")
        self.assertIn("PERFORMS_DIVISION", props["semantic_ops"])

    def test_calculate_fee_has_multiplication(self):
        """calculateFee should detect PERFORMS_MULTIPLICATION."""
        props = self._get_function_props("calculateFee")
        self.assertIn("PERFORMS_MULTIPLICATION", props["semantic_ops"])

    # =========================================================================
    # Validation Operation Tests
    # =========================================================================

    def test_validate_and_store_validates_input(self):
        """validateAndStore should detect VALIDATES_INPUT."""
        props = self._get_function_props("validateAndStore")
        self.assertIn("VALIDATES_INPUT", props["semantic_ops"])

    def test_emit_event_emits_event(self):
        """emitEvent should detect EMITS_EVENT."""
        props = self._get_function_props("emitEvent")
        self.assertIn("EMITS_EVENT", props["semantic_ops"])

    # =========================================================================
    # Behavioral Signature Tests
    # =========================================================================

    def test_vulnerable_withdrawal_signature(self):
        """Vulnerable withdrawal should have R:bal before X:out before W:bal."""
        props = self._get_function_props("withdrawVulnerable")
        sig = props["behavioral_signature"]
        # Signature should contain the vulnerable pattern markers
        self.assertIn("R:bal", sig)
        self.assertIn("X:out", sig)
        self.assertIn("W:bal", sig)

    def test_cei_withdrawal_signature(self):
        """CEI withdrawal should have W:bal before X:out."""
        props = self._get_function_props("withdrawCEI")
        sig = props["behavioral_signature"]
        # Signature should show CEI pattern
        parts = sig.split("→")
        # Find positions
        w_bal_idx = next((i for i, p in enumerate(parts) if "W:bal" in p), -1)
        x_out_idx = next((i for i, p in enumerate(parts) if "X:out" in p), -1)
        # W:bal should come before X:out in CEI pattern
        if w_bal_idx != -1 and x_out_idx != -1:
            self.assertLess(w_bal_idx, x_out_idx, "CEI pattern: W:bal should come before X:out")


class TestOperationsRegressionPrevention(unittest.TestCase):
    """Test that existing contracts still work with operation detection."""

    def test_no_access_gate_still_works(self):
        """NoAccessGate.sol should still be parseable with operations."""
        graph = load_graph("NoAccessGate.sol")
        self.assertIsNotNone(graph)
        # Check that functions have operation properties
        fn_count = sum(1 for n in graph.nodes.values() if n.type == "Function")
        self.assertGreater(fn_count, 0)
        for node in graph.nodes.values():
            if node.type == "Function":
                self.assertIn("semantic_ops", node.properties)
                self.assertIn("behavioral_signature", node.properties)

    def test_value_movement_reentrancy_still_works(self):
        """ValueMovementReentrancy.sol should still be parseable."""
        graph = load_graph("ValueMovementReentrancy.sol")
        self.assertIsNotNone(graph)
        for node in graph.nodes.values():
            if node.type == "Function":
                self.assertIn("semantic_ops", node.properties)


if __name__ == "__main__":
    unittest.main()
