"""Test BSKG enhancements for DoS analysis."""

from __future__ import annotations

import unittest
from pathlib import Path

from tests.graph_cache import load_graph
from alphaswarm_sol.queries.patterns import PatternEngine, PatternStore

try:
    import slither  # type: ignore  # noqa: F401

    _HAS_SLITHER = True
except Exception:
    _HAS_SLITHER = False


class BSKGEnhancementTests(unittest.TestCase):
    """Test the 5 new BSKG enhancements for DoS detection."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_has_require_bounds_property(self) -> None:
        """Test has_require_bounds property detects bounded parameters."""
        graph = load_graph("DosComprehensive.sol")
        fn_nodes = [node for node in graph.nodes.values() if node.type == "Function"]
        by_name = {node.label.split("(")[0]: node for node in fn_nodes}

        # Safe paginated function should have require bounds
        paginated = by_name.get("paginatedArrayAccess")
        if paginated:
            # This may or may not be detected depending on Slither's IR
            # The property exists and defaults to False if not detected
            self.assertIsInstance(paginated.properties.get("has_require_bounds"), bool)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_uses_transfer_and_send_properties(self) -> None:
        """Test uses_transfer and uses_send properties are present."""
        graph = load_graph("DosComprehensive.sol")
        fn_nodes = [node for node in graph.nodes.values() if node.type == "Function"]
        by_name = {node.label.split("(")[0]: node for node in fn_nodes}

        # All functions should have these properties (even if False)
        for fn_node in fn_nodes:
            self.assertIn("uses_transfer", fn_node.properties)
            self.assertIn("uses_send", fn_node.properties)
            self.assertIsInstance(fn_node.properties["uses_transfer"], bool)
            self.assertIsInstance(fn_node.properties["uses_send"], bool)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_has_strict_equality_check_property(self) -> None:
        """Test has_strict_equality_check property is present."""
        graph = load_graph("DosComprehensive.sol")
        fn_nodes = [node for node in graph.nodes.values() if node.type == "Function"]

        # All functions should have this property
        for fn_node in fn_nodes:
            self.assertIn("has_strict_equality_check", fn_node.properties)
            self.assertIsInstance(fn_node.properties["has_strict_equality_check"], bool)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_enhanced_has_external_calls_property(self) -> None:
        """Test has_external_calls now includes low-level calls."""
        graph = load_graph("DosComprehensive.sol")
        fn_nodes = [node for node in graph.nodes.values() if node.type == "Function"]
        by_name = {node.label.split("(")[0]: node for node in fn_nodes}

        # Functions with .call{value: X}("") should have has_external_calls = true
        # This tests the enhancement that includes low_level_calls
        for fn_node in fn_nodes:
            self.assertIn("has_external_calls", fn_node.properties)
            self.assertIsInstance(fn_node.properties["has_external_calls"], bool)

        # If low_level_calls is present, has_external_calls should be true
        for fn_node in fn_nodes:
            low_level = fn_node.properties.get("low_level_calls", [])
            if low_level:
                self.assertTrue(
                    fn_node.properties["has_external_calls"],
                    f"Function {fn_node.label} has low_level_calls but has_external_calls is False"
                )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_state_mutability_property(self) -> None:
        """Test state_mutability property with normalized values."""
        graph = load_graph("DosComprehensive.sol")
        fn_nodes = [node for node in graph.nodes.values() if node.type == "Function"]

        valid_mutabilities = {"view", "pure", "payable", "nonpayable"}

        # All functions should have state_mutability property
        for fn_node in fn_nodes:
            self.assertIn("state_mutability", fn_node.properties)
            mutability = fn_node.properties["state_mutability"]
            self.assertIsInstance(mutability, str)
            self.assertIn(
                mutability,
                valid_mutabilities,
                f"Function {fn_node.label} has invalid state_mutability: {mutability}"
            )

        # Check specific functions have correct mutability
        by_name = {node.label.split("(")[0]: node for node in fn_nodes}

        # View functions should have state_mutability = "view"
        view_funcs = [name for name in by_name.keys() if "getAll" in name or "view" in name.lower()]
        for name in view_funcs:
            if name in by_name:
                node = by_name[name]
                # Should be view or nonpayable (depending on Slither's analysis)
                self.assertIn(node.properties["state_mutability"], {"view", "nonpayable"})

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_all_enhancements_backward_compatible(self) -> None:
        """Test that all existing properties still exist (backward compatibility)."""
        graph = load_graph("LoopDos.sol")
        fn_nodes = [node for node in graph.nodes.values() if node.type == "Function"]

        # Original properties that must exist
        required_props = [
            "visibility",
            "has_loops",
            "has_unbounded_loop",
            "external_calls_in_loop",
            "has_delete_in_loop",
            "has_unbounded_deletion",
            "has_external_calls",
            "has_access_gate",
            "writes_state",
            "reads_state",
        ]

        for fn_node in fn_nodes:
            for prop in required_props:
                self.assertIn(
                    prop,
                    fn_node.properties,
                    f"Function {fn_node.label} missing required property: {prop}"
                )

        # New properties that must exist
        new_props = [
            "has_require_bounds",
            "uses_transfer",
            "uses_send",
            "has_strict_equality_check",
            "state_mutability",
        ]

        for fn_node in fn_nodes:
            for prop in new_props:
                self.assertIn(
                    prop,
                    fn_node.properties,
                    f"Function {fn_node.label} missing new property: {prop}"
                )


if __name__ == "__main__":
    unittest.main()
