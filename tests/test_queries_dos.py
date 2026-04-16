"""Loop/DoS query tests."""

from __future__ import annotations

import unittest
from tests.graph_cache import load_graph
from tests.pattern_loader import load_all_patterns
from alphaswarm_sol.queries.patterns import PatternEngine

try:
    import slither  # type: ignore  # noqa: F401

    _HAS_SLITHER = True
except Exception:
    _HAS_SLITHER = False


class DosQueryTests(unittest.TestCase):
    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_loop_summary_flags(self) -> None:
        graph = load_graph("LoopDos.sol")
        fn_nodes = [node for node in graph.nodes.values() if node.type == "Function"]
        loop_nodes = [node for node in graph.nodes.values() if node.type == "Loop"]

        by_name = {node.label.split("(")[0]: node for node in fn_nodes}
        unbounded = by_name["unboundedLoop"]
        with_call = by_name["loopWithExternalCall"]
        delete_loop = by_name["unboundedDelete"]
        constant_loop = by_name["constantLoop"]
        bounded_delete = by_name["boundedDelete"]

        self.assertTrue(unbounded.properties.get("has_loops"))
        self.assertTrue(unbounded.properties.get("has_unbounded_loop"))
        self.assertIn("user_input", unbounded.properties.get("loop_bound_sources", []))

        self.assertTrue(with_call.properties.get("external_calls_in_loop"))
        # Note: storage_length is now correctly treated as unbounded by builder
        self.assertTrue(with_call.properties.get("has_unbounded_loop"))
        self.assertIn("storage_length", with_call.properties.get("loop_bound_sources", []))

        self.assertTrue(delete_loop.properties.get("has_delete_in_loop"))
        self.assertTrue(delete_loop.properties.get("has_unbounded_deletion"))

        self.assertTrue(constant_loop.properties.get("has_loops"))
        self.assertFalse(constant_loop.properties.get("has_unbounded_loop"))
        self.assertIn("constant", constant_loop.properties.get("loop_bound_sources", []))

        self.assertTrue(bounded_delete.properties.get("has_delete_in_loop"))
        # Note: storage_length is now correctly treated as unbounded by builder
        self.assertTrue(bounded_delete.properties.get("has_unbounded_loop"))
        self.assertTrue(bounded_delete.properties.get("has_unbounded_deletion"))
        self.assertIn("storage_length", bounded_delete.properties.get("loop_bound_sources", []))

        self.assertTrue(loop_nodes)
        self.assertTrue(any("user_input" in node.properties.get("bound_sources", []) for node in loop_nodes))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_dos_patterns_match(self) -> None:
        """Test DoS pattern detection.

        Note: Pattern IDs use semantic naming (dos-001, dos-002, dos-003).
        storage_length is now correctly treated as unbounded by builder.
        """
        graph = load_graph("LoopDos.sol")
        patterns = list(load_all_patterns())
        engine = PatternEngine()

        # Pattern dos-001 = unbounded loop
        findings = engine.run(graph, patterns, pattern_ids=["dos-001"])
        names = {finding["node_label"].split("(")[0] for finding in findings}
        self.assertIn("unboundedLoop", names)
        self.assertNotIn("constantLoop", names)
        # loopWithExternalCall uses storage_length which is now unbounded
        self.assertIn("loopWithExternalCall", names)

        # Pattern dos-002 = external call in loop
        findings = engine.run(graph, patterns, pattern_ids=["dos-002"])
        names = {finding["node_label"].split("(")[0] for finding in findings}
        self.assertIn("loopWithExternalCall", names)

        # Pattern dos-unbounded-deletion = unbounded deletion
        findings = engine.run(graph, patterns, pattern_ids=["dos-unbounded-deletion"])
        names = {finding["node_label"].split("(")[0] for finding in findings}
        self.assertIn("unboundedDelete", names)
        # boundedDelete uses storage_length which is now unbounded
        self.assertIn("boundedDelete", names)


if __name__ == "__main__":
    unittest.main()
