"""
Tests for Graph Fingerprinting Module

Validates that:
1. Fingerprints are stable across multiple runs
2. Different graphs produce different fingerprints
3. Fingerprint comparison works correctly
"""

import unittest
import json


class FingerprintTests(unittest.TestCase):
    """Tests for fingerprinting functionality."""

    def test_import_fingerprint_module(self):
        """Fingerprint module can be imported."""
        from alphaswarm_sol.kg.fingerprint import fingerprint_graph
        self.assertIsNotNone(fingerprint_graph)

    def test_fingerprint_empty_graph(self):
        """Fingerprint works on empty graph."""
        from alphaswarm_sol.kg.fingerprint import fingerprint_graph

        empty_graph = {"graph": {"nodes": [], "edges": []}}
        fp = fingerprint_graph(empty_graph)

        self.assertIn("full_hash", fp)
        self.assertEqual(fp["node_count"], 0)
        self.assertEqual(fp["edge_count"], 0)

    def test_fingerprint_simple_graph(self):
        """Fingerprint works on simple graph."""
        from alphaswarm_sol.kg.fingerprint import fingerprint_graph

        simple_graph = {
            "graph": {
                "nodes": [
                    {
                        "id": "func:1",
                        "type": "Function",
                        "label": "withdraw(uint256)",
                        "properties": {
                            "visibility": "external",
                            "has_access_gate": False,
                            "state_write_after_external_call": True,
                        }
                    }
                ],
                "edges": []
            }
        }
        fp = fingerprint_graph(simple_graph)

        self.assertIn("full_hash", fp)
        self.assertEqual(fp["node_count"], 1)
        self.assertEqual(fp["version"], "1.0")

    def test_fingerprint_stability(self):
        """Same graph produces same fingerprint."""
        from alphaswarm_sol.kg.fingerprint import fingerprint_graph

        graph = {
            "graph": {
                "nodes": [
                    {
                        "id": "func:1",
                        "type": "Function",
                        "label": "transfer(address,uint256)",
                        "properties": {
                            "visibility": "external",
                            "has_access_gate": True,
                            "uses_erc20_transfer": True,
                        }
                    },
                    {
                        "id": "func:2",
                        "type": "Function",
                        "label": "withdraw()",
                        "properties": {
                            "visibility": "public",
                            "is_value_transfer": True,
                        }
                    }
                ],
                "edges": [
                    {"source": "func:1", "target": "func:2", "type": "calls"}
                ]
            }
        }

        fp1 = fingerprint_graph(graph)
        fp2 = fingerprint_graph(graph)

        self.assertEqual(fp1["full_hash"], fp2["full_hash"])

    def test_fingerprint_different_graphs(self):
        """Different graphs produce different fingerprints."""
        from alphaswarm_sol.kg.fingerprint import fingerprint_graph

        graph1 = {
            "graph": {
                "nodes": [
                    {"id": "1", "type": "Function", "label": "a", "properties": {"visibility": "public"}}
                ],
                "edges": []
            }
        }
        graph2 = {
            "graph": {
                "nodes": [
                    {"id": "1", "type": "Function", "label": "b", "properties": {"visibility": "external"}}
                ],
                "edges": []
            }
        }

        fp1 = fingerprint_graph(graph1)
        fp2 = fingerprint_graph(graph2)

        self.assertNotEqual(fp1["full_hash"], fp2["full_hash"])

    def test_compare_identical_fingerprints(self):
        """Compare returns identical=True for same fingerprint."""
        from alphaswarm_sol.kg.fingerprint import fingerprint_graph, compare_fingerprints

        graph = {
            "graph": {
                "nodes": [
                    {"id": "1", "type": "Function", "label": "test", "properties": {}}
                ],
                "edges": []
            }
        }

        fp = fingerprint_graph(graph)
        comparison = compare_fingerprints(fp, fp)

        self.assertTrue(comparison["identical"])
        self.assertEqual(comparison["node_count_diff"], 0)

    def test_compare_different_fingerprints(self):
        """Compare correctly identifies differences."""
        from alphaswarm_sol.kg.fingerprint import fingerprint_graph, compare_fingerprints

        graph1 = {
            "graph": {
                "nodes": [
                    {"id": "1", "type": "Function", "label": "a", "properties": {"has_access_gate": True}}
                ],
                "edges": []
            }
        }
        graph2 = {
            "graph": {
                "nodes": [
                    {"id": "1", "type": "Function", "label": "a", "properties": {"has_access_gate": True}},
                    {"id": "2", "type": "Function", "label": "b", "properties": {}}
                ],
                "edges": []
            }
        }

        fp1 = fingerprint_graph(graph1)
        fp2 = fingerprint_graph(graph2)
        comparison = compare_fingerprints(fp1, fp2)

        self.assertFalse(comparison["identical"])
        self.assertEqual(comparison["node_count_diff"], 1)

    def test_verify_determinism(self):
        """Verify determinism function works."""
        from alphaswarm_sol.kg.fingerprint import verify_determinism

        graph = {
            "graph": {
                "nodes": [
                    {"id": "1", "type": "Function", "label": "test", "properties": {"visibility": "public"}}
                ],
                "edges": []
            }
        }

        result = verify_determinism(graph, runs=5)
        self.assertTrue(result)

    def test_semantic_summary(self):
        """Fingerprint includes semantic property summary."""
        from alphaswarm_sol.kg.fingerprint import fingerprint_graph

        graph = {
            "graph": {
                "nodes": [
                    {
                        "id": "1",
                        "type": "Function",
                        "label": "vulnerable",
                        "properties": {
                            "has_access_gate": False,
                            "state_write_after_external_call": True,
                        }
                    },
                    {
                        "id": "2",
                        "type": "Function",
                        "label": "safe",
                        "properties": {
                            "has_access_gate": True,
                            "has_reentrancy_guard": True,
                        }
                    }
                ],
                "edges": []
            }
        }

        fp = fingerprint_graph(graph)
        summary = fp["semantic_summary"]

        self.assertEqual(summary["has_access_gate"], 1)
        self.assertEqual(summary["has_reentrancy_guard"], 1)
        self.assertEqual(summary["state_write_after_external_call"], 1)

    def test_node_type_counts(self):
        """Fingerprint includes node type counts."""
        from alphaswarm_sol.kg.fingerprint import fingerprint_graph

        graph = {
            "graph": {
                "nodes": [
                    {"id": "1", "type": "Function", "label": "f1", "properties": {}},
                    {"id": "2", "type": "Function", "label": "f2", "properties": {}},
                    {"id": "3", "type": "Contract", "label": "C", "properties": {}},
                ],
                "edges": []
            }
        }

        fp = fingerprint_graph(graph)
        counts = fp["node_type_counts"]

        self.assertEqual(counts["Function"], 2)
        self.assertEqual(counts["Contract"], 1)


if __name__ == "__main__":
    unittest.main()
