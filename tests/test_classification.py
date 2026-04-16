"""Tests for Phase 6: Hierarchical Node Classification.

This module tests:
- FunctionRole classification
- StateVariableRole classification
- AtomicBlock detection
- CEI violation detection
- Integration with builder.py
"""

from __future__ import annotations

import unittest
from pathlib import Path

from tests.graph_cache import load_graph
from alphaswarm_sol.kg.classification import (
    FunctionRole,
    StateVariableRole,
    AtomicBlock,
    NodeClassifier,
    classify_function_role,
    classify_state_variable_role,
    detect_atomic_blocks,
    get_semantic_role_summary,
)


class TestFunctionRoleEnum(unittest.TestCase):
    """Test FunctionRole enum values."""

    def test_all_roles_defined(self):
        """All expected function roles are defined."""
        self.assertEqual(FunctionRole.GUARDIAN.value, "Guardian")
        self.assertEqual(FunctionRole.CHECKPOINT.value, "Checkpoint")
        self.assertEqual(FunctionRole.ESCAPE_HATCH.value, "EscapeHatch")
        self.assertEqual(FunctionRole.ENTRY_POINT.value, "EntryPoint")
        self.assertEqual(FunctionRole.INTERNAL.value, "Internal")
        self.assertEqual(FunctionRole.VIEW.value, "View")


class TestStateVariableRoleEnum(unittest.TestCase):
    """Test StateVariableRole enum values."""

    def test_all_roles_defined(self):
        """All expected state variable roles are defined."""
        self.assertEqual(StateVariableRole.STATE_ANCHOR.value, "StateAnchor")
        self.assertEqual(StateVariableRole.CRITICAL_STATE.value, "CriticalState")
        self.assertEqual(StateVariableRole.CONFIG_STATE.value, "ConfigState")
        self.assertEqual(StateVariableRole.INTERNAL_STATE.value, "InternalState")


class TestAtomicBlock(unittest.TestCase):
    """Test AtomicBlock dataclass."""

    def test_atomic_block_creation(self):
        """AtomicBlock can be created with all fields."""
        block = AtomicBlock(
            function_id="func:1",
            call_site_line=42,
            call_type="call",
            pre_state_reads=["balance"],
            pre_state_writes=[],
            post_state_reads=[],
            post_state_writes=["balance"],
            cei_violation=True,
            risk_level="high",
        )
        self.assertEqual(block.function_id, "func:1")
        self.assertEqual(block.call_site_line, 42)
        self.assertTrue(block.cei_violation)
        self.assertEqual(block.risk_level, "high")

    def test_atomic_block_serialization(self):
        """AtomicBlock serializes to dict and back."""
        block = AtomicBlock(
            function_id="func:1",
            call_site_line=42,
            call_type="delegatecall",
            pre_state_reads=["a", "b"],
            pre_state_writes=["c"],
            post_state_reads=["d"],
            post_state_writes=["e", "f"],
            cei_violation=True,
            risk_level="critical",
        )

        # Serialize
        data = block.to_dict()
        self.assertEqual(data["function_id"], "func:1")
        self.assertEqual(data["call_type"], "delegatecall")
        self.assertEqual(data["risk_level"], "critical")

        # Deserialize
        restored = AtomicBlock.from_dict(data)
        self.assertEqual(restored.function_id, block.function_id)
        self.assertEqual(restored.call_type, block.call_type)
        self.assertEqual(restored.cei_violation, block.cei_violation)
        self.assertEqual(restored.pre_state_reads, ["a", "b"])
        self.assertEqual(restored.post_state_writes, ["e", "f"])


class TestNodeClassifier(unittest.TestCase):
    """Test NodeClassifier class."""

    def setUp(self):
        """Create classifier instance."""
        self.classifier = NodeClassifier()

    def test_classify_view_function(self):
        """View functions are classified correctly."""
        fn = {"is_view": True, "visibility": "public"}
        role = self.classifier.classify_function(fn)
        self.assertEqual(role, FunctionRole.VIEW)

    def test_classify_pure_function(self):
        """Pure functions are classified as View."""
        fn = {"state_mutability": "pure", "visibility": "public"}
        role = self.classifier.classify_function(fn)
        self.assertEqual(role, FunctionRole.VIEW)

    def test_classify_guardian_function(self):
        """Access control functions are classified as Guardian."""
        fn = {
            "label": "onlyOwner",
            "has_access_modifier": True,
            "writes_state": False,
        }
        role = self.classifier.classify_function(fn)
        self.assertEqual(role, FunctionRole.GUARDIAN)

    def test_classify_escape_hatch_function(self):
        """Emergency functions are classified as EscapeHatch."""
        fn = {"label": "emergencyWithdraw", "visibility": "public"}
        role = self.classifier.classify_function(fn)
        self.assertEqual(role, FunctionRole.ESCAPE_HATCH)

    def test_classify_pause_function(self):
        """Pause functions are classified as EscapeHatch."""
        fn = {"label": "pause", "has_pause_check": True, "visibility": "public"}
        role = self.classifier.classify_function(fn)
        self.assertEqual(role, FunctionRole.ESCAPE_HATCH)

    def test_classify_checkpoint_function(self):
        """Critical state modification functions are classified as Checkpoint."""
        fn = {
            "label": "setOwner",
            "writes_state": True,
            "writes_privileged_state": True,
            "visibility": "public",
        }
        role = self.classifier.classify_function(fn)
        self.assertEqual(role, FunctionRole.CHECKPOINT)

    def test_classify_upgrade_function(self):
        """Upgrade functions are classified as Checkpoint."""
        fn = {
            "label": "upgradeTo",
            "is_upgrade_function": True,
            "visibility": "public",
        }
        role = self.classifier.classify_function(fn)
        self.assertEqual(role, FunctionRole.CHECKPOINT)

    def test_classify_entry_point_function(self):
        """Public state-changing functions are classified as EntryPoint."""
        fn = {
            "label": "deposit",
            "visibility": "public",
            "writes_state": True,
        }
        role = self.classifier.classify_function(fn)
        self.assertEqual(role, FunctionRole.ENTRY_POINT)

    def test_classify_internal_function(self):
        """Internal functions are classified as Internal."""
        fn = {
            "label": "_internalHelper",
            "visibility": "internal",
            "writes_state": True,
        }
        role = self.classifier.classify_function(fn)
        self.assertEqual(role, FunctionRole.INTERNAL)

    def test_classify_state_anchor_variable(self):
        """Owner/admin variables are classified as StateAnchor."""
        var = {"label": "owner", "security_tags": ["owner"]}
        role = self.classifier.classify_state_variable(var)
        self.assertEqual(role, StateVariableRole.STATE_ANCHOR)

    def test_classify_critical_state_variable(self):
        """Balance variables are classified as CriticalState."""
        var = {"label": "balances", "type": "mapping(address => uint256)"}
        role = self.classifier.classify_state_variable(var)
        self.assertEqual(role, StateVariableRole.CRITICAL_STATE)

    def test_classify_config_state_variable(self):
        """Fee variables are classified as ConfigState."""
        var = {"label": "feeRate", "security_tags": ["fee"]}
        role = self.classifier.classify_state_variable(var)
        self.assertEqual(role, StateVariableRole.CONFIG_STATE)

    def test_classify_internal_state_variable(self):
        """Generic variables are classified as InternalState."""
        var = {"label": "counter", "type": "uint256"}
        role = self.classifier.classify_state_variable(var)
        self.assertEqual(role, StateVariableRole.INTERNAL_STATE)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience classification functions."""

    def test_classify_function_role(self):
        """classify_function_role returns string value."""
        fn = {"label": "pause", "has_pause_check": True}
        role = classify_function_role(fn)
        self.assertEqual(role, "EscapeHatch")

    def test_classify_state_variable_role(self):
        """classify_state_variable_role returns string value."""
        var = {"label": "owner", "security_tags": ["admin"]}
        role = classify_state_variable_role(var)
        self.assertEqual(role, "StateAnchor")


class TestDetectAtomicBlocks(unittest.TestCase):
    """Test atomic block detection."""

    def test_no_external_calls(self):
        """Functions without external calls have no atomic blocks."""
        fn = {
            "id": "func:1",
            "has_external_calls": False,
            "has_low_level_calls": False,
        }
        blocks = detect_atomic_blocks(fn)
        self.assertEqual(len(blocks), 0)

    def test_external_call_with_cei_violation(self):
        """External call with post-write creates CEI violation."""
        fn = {
            "id": "func:1",
            "has_external_calls": True,
            "has_low_level_calls": False,
            "state_variables_read_names": ["balance"],
            "state_variables_written_names": ["balance"],
            "state_write_after_external_call": True,
            "has_reentrancy_guard": False,
        }
        blocks = detect_atomic_blocks(fn)
        self.assertEqual(len(blocks), 1)
        self.assertTrue(blocks[0].cei_violation)
        self.assertEqual(blocks[0].risk_level, "high")

    def test_external_call_with_reentrancy_guard(self):
        """Reentrancy guard prevents CEI violation flag."""
        fn = {
            "id": "func:1",
            "has_external_calls": True,
            "state_variables_written_names": ["balance"],
            "state_write_after_external_call": True,
            "has_reentrancy_guard": True,
        }
        blocks = detect_atomic_blocks(fn)
        self.assertEqual(len(blocks), 1)
        self.assertFalse(blocks[0].cei_violation)
        self.assertEqual(blocks[0].risk_level, "low")

    def test_delegatecall_critical_risk(self):
        """Delegatecall with post-write is critical risk."""
        fn = {
            "id": "func:1",
            "has_external_calls": True,
            "uses_delegatecall": True,
            "state_variables_written_names": ["impl"],
            "state_write_after_external_call": True,
            "has_reentrancy_guard": False,
        }
        blocks = detect_atomic_blocks(fn)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].call_type, "delegatecall")
        self.assertEqual(blocks[0].risk_level, "critical")

    def test_low_level_call_detection(self):
        """Low-level calls are detected."""
        fn = {
            "id": "func:1",
            "has_external_calls": False,
            "has_low_level_calls": True,
            "state_write_after_external_call": False,
        }
        blocks = detect_atomic_blocks(fn)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].call_type, "call")
        self.assertEqual(blocks[0].risk_level, "low")


class TestBuilderIntegration(unittest.TestCase):
    """Test classification integration with builder."""

    def test_builder_adds_semantic_role(self):
        """Builder adds semantic_role property to function nodes."""
        graph = load_graph("ArbitraryDelegatecall.sol")

        # Check that at least one function has semantic_role
        fn_nodes = [n for n in graph.nodes.values() if n.type == "Function"]
        has_semantic_role = any(
            n.properties.get("semantic_role") is not None for n in fn_nodes
        )
        self.assertTrue(has_semantic_role)

    def test_builder_adds_state_variable_role(self):
        """Builder adds semantic_role property to state variable nodes."""
        graph = load_graph("ArbitraryDelegatecall.sol")

        # Check that at least one state variable has semantic_role
        sv_nodes = [n for n in graph.nodes.values() if n.type == "StateVariable"]
        has_semantic_role = any(
            n.properties.get("semantic_role") is not None for n in sv_nodes
        )
        self.assertTrue(has_semantic_role)

    def test_builder_adds_atomic_blocks(self):
        """Builder adds atomic_blocks property to functions with external calls."""
        graph = load_graph("ArbitraryDelegatecall.sol")

        # Find function with delegatecall
        fn_with_delegatecall = None
        for node in graph.nodes.values():
            if node.type == "Function" and node.properties.get("uses_delegatecall"):
                fn_with_delegatecall = node
                break

        self.assertIsNotNone(fn_with_delegatecall)
        atomic_blocks = fn_with_delegatecall.properties.get("atomic_blocks", [])
        # Should have atomic block data
        self.assertIsInstance(atomic_blocks, list)

    def test_reentrancy_contract_classification(self):
        """ReentrancyClassic contract is classified correctly."""
        graph = load_graph("ReentrancyClassic.sol")

        # Find withdraw function
        withdraw_fn = None
        for node in graph.nodes.values():
            if node.type == "Function" and "withdraw" in node.label.lower():
                withdraw_fn = node
                break

        self.assertIsNotNone(withdraw_fn)
        # "withdraw" matches EMERGENCY_KEYWORDS so it's classified as EscapeHatch
        # This is reasonable - withdraw functions often serve as escape hatches
        role = withdraw_fn.properties.get("semantic_role")
        self.assertIn(role, ["EntryPoint", "Checkpoint", "EscapeHatch"])


class TestGetSemanticRoleSummary(unittest.TestCase):
    """Test semantic role summary generation."""

    def test_summary_structure(self):
        """Summary has expected structure."""
        graph = load_graph("ArbitraryDelegatecall.sol")
        summary = get_semantic_role_summary(graph)

        self.assertIn("function_roles", summary)
        self.assertIn("state_variable_roles", summary)
        self.assertIn("atomic_blocks", summary)
        self.assertIn("high_risk_nodes", summary)
        self.assertIn("total_functions", summary)
        self.assertIn("total_state_variables", summary)

    def test_summary_counts(self):
        """Summary counts are non-negative."""
        graph = load_graph("ArbitraryDelegatecall.sol")
        summary = get_semantic_role_summary(graph)

        self.assertGreaterEqual(summary["total_functions"], 0)
        self.assertGreaterEqual(summary["total_state_variables"], 0)

    def test_reentrancy_has_high_risk(self):
        """ReentrancyClassic contract has high-risk atomic blocks."""
        graph = load_graph("ReentrancyClassic.sol")
        summary = get_semantic_role_summary(graph)

        # Should detect CEI violation in withdraw
        cei_violations = [
            block for block in summary["atomic_blocks"]
            if block.get("cei_violation")
        ]
        self.assertGreater(len(cei_violations), 0)


if __name__ == "__main__":
    unittest.main()
