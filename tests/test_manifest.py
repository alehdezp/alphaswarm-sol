"""
Tests for Build Manifest Module

Validates:
1. Manifest creation with correct structure
2. File hash computation
3. Graph hash computation
4. Manifest verification
5. Manifest comparison
"""

import json
import tempfile
import unittest
from pathlib import Path


class ManifestCreationTests(unittest.TestCase):
    """Tests for manifest creation."""

    def test_import_manifest_module(self):
        """Manifest module can be imported."""
        from alphaswarm_sol.kg.manifest import create_build_manifest
        self.assertIsNotNone(create_build_manifest)

    def test_compute_file_hash(self):
        """File hash computation works."""
        from alphaswarm_sol.kg.manifest import compute_file_hash

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sol", delete=False) as f:
            f.write("contract Test {}")
            temp_path = Path(f.name)

        try:
            hash1 = compute_file_hash(temp_path)
            hash2 = compute_file_hash(temp_path)

            self.assertEqual(len(hash1), 64)  # SHA-256 hex length
            self.assertEqual(hash1, hash2)  # Deterministic
        finally:
            temp_path.unlink()

    def test_compute_content_hash(self):
        """Content hash computation works."""
        from alphaswarm_sol.kg.manifest import compute_content_hash

        hash1 = compute_content_hash("test content")
        hash2 = compute_content_hash("test content")
        hash3 = compute_content_hash("different content")

        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)

    def test_create_manifest_structure(self):
        """Created manifest has correct structure."""
        from alphaswarm_sol.kg.manifest import create_build_manifest

        graph_data = {
            "graph": {
                "nodes": [{"id": "1", "type": "Function"}],
                "edges": []
            },
            "metadata": {"solc_version_selected": "0.8.20"}
        }

        manifest = create_build_manifest(
            source_files=[],
            graph_data=graph_data,
            output_path=Path("/tmp/graph.json"),
        )

        # Check required fields
        self.assertIn("manifest_version", manifest)
        self.assertIn("vkg_version", manifest)
        self.assertIn("build_timestamp", manifest)
        self.assertIn("environment", manifest)
        self.assertIn("inputs", manifest)
        self.assertIn("outputs", manifest)
        self.assertIn("verification", manifest)

        # Check outputs
        self.assertEqual(manifest["outputs"]["node_count"], 1)
        self.assertEqual(manifest["outputs"]["edge_count"], 0)
        self.assertIn("graph_hash", manifest["outputs"])

    def test_manifest_includes_source_hashes(self):
        """Manifest includes hashes for source files."""
        from alphaswarm_sol.kg.manifest import create_build_manifest

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sol", delete=False) as f:
            f.write("// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\ncontract Test {}")
            temp_path = Path(f.name)

        try:
            graph_data = {"graph": {"nodes": [], "edges": []}}

            manifest = create_build_manifest(
                source_files=[temp_path],
                graph_data=graph_data,
                output_path=Path("/tmp/graph.json"),
            )

            self.assertEqual(manifest["inputs"]["source_count"], 1)
            self.assertEqual(len(manifest["inputs"]["source_files"]), 1)
            self.assertIn("hash", manifest["inputs"]["source_files"][0])
        finally:
            temp_path.unlink()

    def test_manifest_environment_info(self):
        """Manifest includes environment info."""
        from alphaswarm_sol.kg.manifest import get_environment_info

        env = get_environment_info()

        self.assertIn("python_version", env)
        self.assertIn("platform", env)
        self.assertIn("machine", env)
        self.assertIn("hostname_hash", env)


class ManifestVerificationTests(unittest.TestCase):
    """Tests for manifest verification."""

    def test_verify_matching_manifest(self):
        """Verification passes for matching manifest."""
        from alphaswarm_sol.kg.manifest import create_build_manifest, save_manifest, verify_manifest

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            graph_data = {
                "graph": {
                    "nodes": [{"id": "1", "type": "Function"}],
                    "edges": []
                }
            }

            # Create and save manifest
            manifest = create_build_manifest(
                source_files=[],
                graph_data=graph_data,
                output_path=output_dir / "graph.json",
            )
            save_manifest(manifest, output_dir)

            # Save graph
            graph_path = output_dir / "graph.json"
            with open(graph_path, "w") as f:
                json.dump(graph_data, f)

            # Verify
            result = verify_manifest(
                output_dir / "build_manifest.json",
                graph_path
            )

            self.assertTrue(result["valid"])
            self.assertTrue(result["hash_match"])

    def test_verify_mismatched_manifest(self):
        """Verification fails for mismatched manifest."""
        from alphaswarm_sol.kg.manifest import create_build_manifest, save_manifest, verify_manifest

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            graph_data = {
                "graph": {
                    "nodes": [{"id": "1", "type": "Function"}],
                    "edges": []
                }
            }

            # Create and save manifest
            manifest = create_build_manifest(
                source_files=[],
                graph_data=graph_data,
                output_path=output_dir / "graph.json",
            )
            save_manifest(manifest, output_dir)

            # Save different graph
            modified_graph = {
                "graph": {
                    "nodes": [{"id": "1", "type": "Function"}, {"id": "2", "type": "Contract"}],
                    "edges": []
                }
            }
            graph_path = output_dir / "graph.json"
            with open(graph_path, "w") as f:
                json.dump(modified_graph, f)

            # Verify
            result = verify_manifest(
                output_dir / "build_manifest.json",
                graph_path
            )

            self.assertFalse(result["valid"])
            self.assertFalse(result["hash_match"])


class ManifestComparisonTests(unittest.TestCase):
    """Tests for manifest comparison."""

    def test_compare_identical_manifests(self):
        """Comparison of identical manifests shows no differences."""
        from alphaswarm_sol.kg.manifest import create_build_manifest, save_manifest, compare_manifests

        with tempfile.TemporaryDirectory() as tmpdir:
            graph_data = {"graph": {"nodes": [], "edges": []}}

            manifest = create_build_manifest(
                source_files=[],
                graph_data=graph_data,
                output_path=Path("/tmp/graph.json"),
            )

            path1 = Path(tmpdir) / "manifest1.json"
            path2 = Path(tmpdir) / "manifest2.json"

            with open(path1, "w") as f:
                json.dump(manifest, f)
            with open(path2, "w") as f:
                json.dump(manifest, f)

            result = compare_manifests(path1, path2)

            self.assertTrue(result["identical"])
            self.assertEqual(len(result["differences"]), 0)

    def test_compare_different_manifests(self):
        """Comparison of different manifests shows differences."""
        from alphaswarm_sol.kg.manifest import create_build_manifest, compare_manifests

        with tempfile.TemporaryDirectory() as tmpdir:
            graph_data1 = {"graph": {"nodes": [{"id": "1"}], "edges": []}}
            graph_data2 = {"graph": {"nodes": [{"id": "1"}, {"id": "2"}], "edges": []}}

            manifest1 = create_build_manifest([], graph_data1, Path("/tmp/g1.json"))
            manifest2 = create_build_manifest([], graph_data2, Path("/tmp/g2.json"))

            path1 = Path(tmpdir) / "manifest1.json"
            path2 = Path(tmpdir) / "manifest2.json"

            with open(path1, "w") as f:
                json.dump(manifest1, f)
            with open(path2, "w") as f:
                json.dump(manifest2, f)

            result = compare_manifests(path1, path2)

            self.assertFalse(result["identical"])
            self.assertGreater(len(result["differences"]), 0)


class ManifestDeterminismTests(unittest.TestCase):
    """Tests for manifest determinism."""

    def test_same_input_same_hash(self):
        """Same input produces same graph hash."""
        from alphaswarm_sol.kg.manifest import create_build_manifest

        graph_data = {
            "graph": {
                "nodes": [
                    {"id": "1", "type": "Function", "label": "test"}
                ],
                "edges": []
            }
        }

        manifests = [
            create_build_manifest([], graph_data, Path("/tmp/g.json"))
            for _ in range(5)
        ]

        hashes = [m["outputs"]["graph_hash"] for m in manifests]
        self.assertEqual(len(set(hashes)), 1, "All hashes should be identical")


if __name__ == "__main__":
    unittest.main()
