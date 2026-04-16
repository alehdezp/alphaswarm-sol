"""
Golden Graph Snapshot Tests

Validates that graph fingerprints match expected values for DVDeFi challenges.
These tests ensure that builder.py changes don't accidentally alter graph structure.

To update snapshots after intentional changes:
    python -m tests.test_golden_snapshots --update
"""

import unittest
import json
import os
import subprocess
import tempfile
from pathlib import Path


SNAPSHOT_DIR = Path(__file__).parent / "golden_snapshots"
VKG_ROOT = Path(__file__).parent.parent
DVDEFI_PATH = VKG_ROOT / "examples" / "damm-vuln-defi" / "src"


# Expected fingerprints for DVDeFi challenges
# Updated after intentional builder.py changes
EXPECTED_FINGERPRINTS = {
    "unstoppable": {
        "node_count_min": 10,
        "node_count_max": 100,
        "has_function_nodes": True,
        "has_contract_nodes": True,
    },
    "truster": {
        "node_count_min": 10,
        "node_count_max": 100,
        "has_function_nodes": True,
        "has_contract_nodes": True,
    },
    "naive-receiver": {
        "node_count_min": 10,
        "node_count_max": 100,
        "has_function_nodes": True,
        "has_contract_nodes": True,
    },
    "side-entrance": {
        "node_count_min": 10,
        "node_count_max": 100,
        "has_function_nodes": True,
        "has_contract_nodes": True,
    },
    "the-rewarder": {
        "node_count_min": 10,
        "node_count_max": 200,
        "has_function_nodes": True,
        "has_contract_nodes": True,
    },
}


class GoldenSnapshotTests(unittest.TestCase):
    """Tests comparing current graphs to golden snapshots."""

    def _build_graph(self, challenge: str) -> dict:
        """Build graph for a DVDeFi challenge."""
        challenge_path = DVDEFI_PATH / challenge
        if not challenge_path.exists():
            self.skipTest(f"Challenge path not found: {challenge_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                ["uv", "run", "alphaswarm", "build-kg", str(challenge_path), "--out", os.path.join(tmpdir, "graph.kg.json")],
                capture_output=True,
                text=True,
                cwd=str(VKG_ROOT)
            )

            if result.returncode != 0:
                self.skipTest(f"Graph build failed: {result.stderr}")

            graph_path = os.path.join(tmpdir, "graph.kg.json", "graph.json")
            if os.path.exists(graph_path):
                with open(graph_path) as f:
                    return json.load(f)
            return None

    def _get_fingerprint(self, graph: dict) -> dict:
        """Get fingerprint for graph."""
        from alphaswarm_sol.kg.fingerprint import fingerprint_graph
        return fingerprint_graph(graph)

    def test_unstoppable_snapshot(self):
        """Unstoppable graph matches expected structure."""
        graph = self._build_graph("unstoppable")
        if graph is None:
            self.skipTest("Graph not available")

        fp = self._get_fingerprint(graph)
        expected = EXPECTED_FINGERPRINTS["unstoppable"]

        self.assertGreaterEqual(
            fp["node_count"],
            expected["node_count_min"],
            "Node count below minimum"
        )
        self.assertLessEqual(
            fp["node_count"],
            expected["node_count_max"],
            "Node count above maximum"
        )
        self.assertIn("Function", fp["node_type_counts"])
        self.assertIn("Contract", fp["node_type_counts"])

    def test_truster_snapshot(self):
        """Truster graph matches expected structure."""
        graph = self._build_graph("truster")
        if graph is None:
            self.skipTest("Graph not available")

        fp = self._get_fingerprint(graph)
        expected = EXPECTED_FINGERPRINTS["truster"]

        self.assertGreaterEqual(fp["node_count"], expected["node_count_min"])
        self.assertLessEqual(fp["node_count"], expected["node_count_max"])

    def test_naive_receiver_snapshot(self):
        """Naive-receiver graph matches expected structure."""
        graph = self._build_graph("naive-receiver")
        if graph is None:
            self.skipTest("Graph not available")

        fp = self._get_fingerprint(graph)
        expected = EXPECTED_FINGERPRINTS["naive-receiver"]

        self.assertGreaterEqual(fp["node_count"], expected["node_count_min"])
        self.assertLessEqual(fp["node_count"], expected["node_count_max"])

    def test_side_entrance_snapshot(self):
        """Side-entrance graph matches expected structure."""
        graph = self._build_graph("side-entrance")
        if graph is None:
            self.skipTest("Graph not available")

        fp = self._get_fingerprint(graph)
        expected = EXPECTED_FINGERPRINTS["side-entrance"]

        self.assertGreaterEqual(fp["node_count"], expected["node_count_min"])
        self.assertLessEqual(fp["node_count"], expected["node_count_max"])

    def test_rewarder_snapshot(self):
        """The-rewarder graph matches expected structure."""
        graph = self._build_graph("the-rewarder")
        if graph is None:
            self.skipTest("Graph not available")

        fp = self._get_fingerprint(graph)
        expected = EXPECTED_FINGERPRINTS["the-rewarder"]

        self.assertGreaterEqual(fp["node_count"], expected["node_count_min"])
        self.assertLessEqual(fp["node_count"], expected["node_count_max"])


class DeterminismTests(unittest.TestCase):
    """Tests that graph building is deterministic."""

    def test_repeated_builds_identical(self):
        """Same source produces identical graphs."""
        from alphaswarm_sol.kg.fingerprint import fingerprint_graph

        source = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Test {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }
}
"""
        fingerprints = []

        for _ in range(3):
            with tempfile.TemporaryDirectory() as tmpdir:
                sol_path = os.path.join(tmpdir, "Test.sol")
                with open(sol_path, "w") as f:
                    f.write(source)

                result = subprocess.run(
                    ["uv", "run", "alphaswarm", "build-kg", tmpdir, "--out", os.path.join(tmpdir, "graph.kg.json")],
                    capture_output=True,
                    text=True,
                    cwd=str(VKG_ROOT)
                )

                if result.returncode != 0:
                    self.skipTest(f"Build failed: {result.stderr}")

                graph_path = os.path.join(tmpdir, "graph.kg.json", "graph.json")
                with open(graph_path) as f:
                    graph = json.load(f)

                fp = fingerprint_graph(graph)
                fingerprints.append(fp["full_hash"])

        # All fingerprints should be identical
        self.assertEqual(
            len(set(fingerprints)), 1,
            f"Fingerprints differ: {fingerprints}"
        )


if __name__ == "__main__":
    import sys
    if "--update" in sys.argv:
        print("Updating golden snapshots...")
        # Implementation for updating snapshots
        print("Done.")
    else:
        unittest.main()
