"""Tests for state versioning (Task 10.4)."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from alphaswarm_sol.state.versioning import (
    GraphVersion,
    VersionGenerator,
    VersionStore,
)
from alphaswarm_sol.state.staleness import (
    StalenessResult,
    StalenessChecker,
    StalenessSeverity,
    format_staleness_warning,
    check_finding_staleness,
    summarize_staleness,
)


class TestGraphVersion(unittest.TestCase):
    """Test GraphVersion dataclass."""

    def test_creation(self):
        """Can create GraphVersion."""
        version = GraphVersion(
            version_id="v1-abc12345",
            fingerprint="sha256hash",
            code_hash="codehash",
            created_at=datetime.now(),
        )

        self.assertEqual(version.version_id, "v1-abc12345")
        self.assertEqual(version.fingerprint, "sha256hash")

    def test_to_dict(self):
        """Version can be serialized to dict."""
        version = GraphVersion(
            version_id="v1-abc12345",
            fingerprint="fp123",
            code_hash="ch123",
            created_at=datetime(2026, 1, 8, 12, 0, 0),
            source_files=["a.sol", "b.sol"],
            slither_version="0.10.0",
            vkg_version="3.5.0",
        )

        data = version.to_dict()

        self.assertEqual(data["version_id"], "v1-abc12345")
        self.assertEqual(data["fingerprint"], "fp123")
        self.assertEqual(data["source_files"], ["a.sol", "b.sol"])
        self.assertIn("2026-01-08", data["created_at"])

    def test_from_dict(self):
        """Version can be deserialized from dict."""
        data = {
            "version_id": "v1-abc12345",
            "fingerprint": "fp123",
            "code_hash": "ch123",
            "created_at": "2026-01-08T12:00:00",
            "source_files": ["a.sol"],
            "slither_version": "0.10.0",
        }

        version = GraphVersion.from_dict(data)

        self.assertEqual(version.version_id, "v1-abc12345")
        self.assertEqual(version.fingerprint, "fp123")
        self.assertEqual(version.source_files, ["a.sol"])

    def test_roundtrip(self):
        """Version survives dict roundtrip."""
        original = GraphVersion(
            version_id="v1-abc12345",
            fingerprint="hash1",
            code_hash="hash2",
            created_at=datetime.now(),
            source_files=["a.sol", "b.sol"],
            slither_version="0.10.0",
        )

        data = original.to_dict()
        restored = GraphVersion.from_dict(data)

        self.assertEqual(restored.version_id, original.version_id)
        self.assertEqual(restored.fingerprint, original.fingerprint)
        self.assertEqual(restored.code_hash, original.code_hash)
        self.assertEqual(restored.source_files, original.source_files)

    def test_equality_by_fingerprint(self):
        """Versions are equal if fingerprints match."""
        v1 = GraphVersion(
            version_id="v1-abc",
            fingerprint="same_hash",
            code_hash="ch1",
            created_at=datetime.now(),
        )
        v2 = GraphVersion(
            version_id="v2-def",  # Different ID
            fingerprint="same_hash",  # Same fingerprint
            code_hash="ch2",
            created_at=datetime.now(),
        )

        self.assertEqual(v1, v2)

    def test_inequality_different_fingerprint(self):
        """Versions with different fingerprints are not equal."""
        v1 = GraphVersion(
            version_id="v1-abc",
            fingerprint="hash1",
            code_hash="ch1",
            created_at=datetime.now(),
        )
        v2 = GraphVersion(
            version_id="v1-abc",  # Same ID
            fingerprint="hash2",  # Different fingerprint
            code_hash="ch1",
            created_at=datetime.now(),
        )

        self.assertNotEqual(v1, v2)

    def test_short_id(self):
        """short_id property works."""
        version = GraphVersion(
            version_id="v1-abc12345",
            fingerprint="fp",
            code_hash="ch",
            created_at=datetime.now(),
        )

        self.assertEqual(version.short_id, "v1-abc12345")


class TestVersionGenerator(unittest.TestCase):
    """Test VersionGenerator class."""

    def setUp(self):
        self.generator = VersionGenerator()

    def test_generates_version(self):
        """Generator creates version for graph."""
        graph = {"nodes": [1, 2, 3], "edges": [(1, 2)]}

        version = self.generator.generate(graph, [])

        self.assertIsInstance(version, GraphVersion)
        self.assertTrue(version.version_id.startswith("v"))
        self.assertEqual(len(version.fingerprint), 64)  # SHA256

    def test_generates_unique_ids(self):
        """Generator creates unique version IDs."""
        v1 = self.generator.generate({}, [])
        v2 = self.generator.generate({}, [])

        self.assertNotEqual(v1.version_id, v2.version_id)

    def test_same_graph_same_fingerprint(self):
        """Same graph produces same fingerprint."""
        graph = {"nodes": [1, 2, 3], "edges": [(1, 2)]}

        v1 = self.generator.generate(graph, [])
        v2 = self.generator.generate(graph, [])

        self.assertEqual(v1.fingerprint, v2.fingerprint)

    def test_different_graph_different_fingerprint(self):
        """Different graphs have different fingerprints."""
        v1 = self.generator.generate({"nodes": [1]}, [])
        v2 = self.generator.generate({"nodes": [2]}, [])

        self.assertNotEqual(v1.fingerprint, v2.fingerprint)

    def test_version_id_format(self):
        """Version ID has expected format."""
        version = self.generator.generate({}, [])

        # Format: vN-XXXXXXXX
        parts = version.version_id.split("-")
        self.assertEqual(len(parts), 2)
        self.assertTrue(parts[0].startswith("v"))
        self.assertEqual(len(parts[1]), 8)  # 8-char fingerprint prefix

    def test_source_files_included(self):
        """Source files are stored in version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sol_file = Path(tmpdir) / "test.sol"
            sol_file.write_text("contract Test {}")

            version = self.generator.generate({}, [sol_file])

            self.assertEqual(len(version.source_files), 1)
            self.assertIn("test.sol", version.source_files[0])

    def test_code_hash_changes_with_files(self):
        """Code hash changes when file contents change."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sol_file = Path(tmpdir) / "test.sol"

            sol_file.write_text("contract V1 {}")
            v1 = self.generator.generate({}, [sol_file])

            sol_file.write_text("contract V2 {}")
            v2 = self.generator.generate({}, [sol_file])

            self.assertNotEqual(v1.code_hash, v2.code_hash)

    def test_handles_graph_with_to_dict(self):
        """Generator handles objects with to_dict method."""
        mock_graph = MagicMock()
        mock_graph.to_dict.return_value = {"nodes": [1], "edges": []}

        version = self.generator.generate(mock_graph, [])

        self.assertIsInstance(version, GraphVersion)
        mock_graph.to_dict.assert_called()

    def test_handles_graph_with_nodes_edges(self):
        """Generator handles objects with nodes/edges attributes."""
        mock_graph = MagicMock()
        mock_graph.nodes = {"n1": MagicMock()}
        mock_graph.nodes["n1"].to_dict.return_value = {"id": "n1"}
        mock_graph.edges = {}
        del mock_graph.to_dict

        version = self.generator.generate(mock_graph, [])

        self.assertIsInstance(version, GraphVersion)

    def test_reset_counter(self):
        """Can reset version counter."""
        self.generator.generate({}, [])
        self.generator.generate({}, [])

        self.generator.reset_counter()
        version = self.generator.generate({}, [])

        self.assertTrue(version.version_id.startswith("v1-"))


class TestVersionStore(unittest.TestCase):
    """Test VersionStore persistence."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = VersionStore(Path(self.tmpdir))
        self.generator = VersionGenerator()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_creates_file(self):
        """Saving version creates file."""
        version = self.generator.generate({"test": True}, [])
        path = self.store.save(version)

        self.assertTrue(path.exists())
        self.assertIn(version.version_id, path.name)

    def test_save_and_load(self):
        """Versions can be saved and loaded."""
        version = self.generator.generate({"nodes": [1, 2]}, [])
        self.store.save(version)

        loaded = self.store.load(version.version_id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.version_id, version.version_id)
        self.assertEqual(loaded.fingerprint, version.fingerprint)

    def test_load_nonexistent(self):
        """Loading nonexistent version returns None."""
        result = self.store.load("v999-nonexistent")
        self.assertIsNone(result)

    def test_get_current(self):
        """Current version is tracked."""
        v1 = self.generator.generate({"v": 1}, [])
        self.store.save(v1)

        v2 = self.generator.generate({"v": 2}, [])
        self.store.save(v2)

        current = self.store.get_current()

        self.assertIsNotNone(current)
        self.assertEqual(current.version_id, v2.version_id)

    def test_set_current(self):
        """Can set current version."""
        v1 = self.generator.generate({"v": 1}, [])
        self.store.save(v1)

        v2 = self.generator.generate({"v": 2}, [])
        self.store.save(v2)

        # Set v1 as current
        self.store.set_current(v1.version_id)
        current = self.store.get_current()

        self.assertEqual(current.version_id, v1.version_id)

    def test_list_versions(self):
        """Can list all versions."""
        v1 = self.generator.generate({"v": 1}, [])
        self.store.save(v1)

        v2 = self.generator.generate({"v": 2}, [])
        self.store.save(v2)

        versions = self.store.list_versions()

        self.assertEqual(len(versions), 2)
        # Should be sorted newest first
        self.assertEqual(versions[0].version_id, v2.version_id)

    def test_delete_version(self):
        """Can delete version."""
        v1 = self.generator.generate({"v": 1}, [])
        self.store.save(v1)

        v2 = self.generator.generate({"v": 2}, [])
        self.store.save(v2)

        # Delete v1
        result = self.store.delete(v1.version_id)

        self.assertTrue(result)
        self.assertIsNone(self.store.load(v1.version_id))
        self.assertIsNotNone(self.store.load(v2.version_id))

    def test_cannot_delete_current(self):
        """Cannot delete current version."""
        version = self.generator.generate({}, [])
        self.store.save(version)

        result = self.store.delete(version.version_id)

        self.assertFalse(result)
        self.assertIsNotNone(self.store.load(version.version_id))

    def test_prune_keeps_recent(self):
        """Prune keeps most recent versions."""
        for i in range(5):
            v = self.generator.generate({"v": i}, [])
            self.store.save(v)

        deleted = self.store.prune(keep_count=2)

        # 5 versions, keep 2 = delete 3 (current is always kept)
        self.assertEqual(deleted, 3)
        self.assertEqual(len(self.store.list_versions()), 2)


class TestStalenessResult(unittest.TestCase):
    """Test StalenessResult dataclass."""

    def test_not_stale_severity_ok(self):
        """Not stale has OK severity."""
        result = StalenessResult(stale=False)
        self.assertEqual(result.severity, StalenessSeverity.OK)

    def test_code_changed_severity_critical(self):
        """Code changed has CRITICAL severity."""
        result = StalenessResult(stale=True, code_changed=True)
        self.assertEqual(result.severity, StalenessSeverity.CRITICAL)

    def test_old_severity_warning(self):
        """Old findings have WARNING severity."""
        result = StalenessResult(stale=True, age=timedelta(days=10))
        self.assertEqual(result.severity, StalenessSeverity.WARNING)

    def test_version_mismatch_severity_info(self):
        """Simple version mismatch has INFO severity."""
        result = StalenessResult(stale=True)
        self.assertEqual(result.severity, StalenessSeverity.INFO)

    def test_to_dict(self):
        """Result can be serialized."""
        result = StalenessResult(
            stale=True,
            finding_version="v1-old",
            current_version="v2-new",
            age=timedelta(hours=5),
            code_changed=False,
            recommendation="Refresh findings",
        )

        data = result.to_dict()

        self.assertTrue(data["stale"])
        self.assertEqual(data["finding_version"], "v1-old")
        self.assertEqual(data["severity"], "info")
        self.assertIn("age_human", data)


class TestStalenessChecker(unittest.TestCase):
    """Test StalenessChecker class."""

    def setUp(self):
        self.current_version = GraphVersion(
            version_id="v2-current",
            fingerprint="fp_current",
            code_hash="ch_current",
            created_at=datetime.now(),
        )
        self.checker = StalenessChecker(self.current_version)

    def test_same_version_not_stale(self):
        """Same version is not stale."""
        result = self.checker.check("v2-current")

        self.assertFalse(result.stale)
        self.assertEqual(result.severity, StalenessSeverity.OK)

    def test_different_version_is_stale(self):
        """Different version is stale."""
        result = self.checker.check("v1-old")

        self.assertTrue(result.stale)
        self.assertEqual(result.finding_version, "v1-old")
        self.assertEqual(result.current_version, "v2-current")

    def test_no_version_is_stale(self):
        """Missing version is considered stale."""
        result = self.checker.check(None)

        self.assertTrue(result.stale)
        self.assertIn("no version", result.recommendation.lower())

    def test_code_changed_detection(self):
        """Code change is detected."""
        result = self.checker.check("v1-old", "ch_old")

        self.assertTrue(result.stale)
        self.assertTrue(result.code_changed)
        self.assertEqual(result.severity, StalenessSeverity.CRITICAL)

    def test_code_unchanged_detection(self):
        """Code unchanged is detected."""
        result = self.checker.check("v1-old", "ch_current")

        self.assertTrue(result.stale)
        self.assertFalse(result.code_changed)

    def test_check_all(self):
        """Can check multiple findings."""
        findings = [
            {"graph_version": "v2-current"},  # Fresh
            {"graph_version": "v1-old"},  # Stale
            {"graph_version": None},  # No version
        ]

        results = self.checker.check_all(findings)

        self.assertEqual(len(results), 3)
        self.assertFalse(results[0].stale)
        self.assertTrue(results[1].stale)
        self.assertTrue(results[2].stale)

    def test_get_summary(self):
        """Can get staleness summary."""
        findings = [
            {"graph_version": "v2-current"},
            {"graph_version": "v1-old"},
            {"graph_version": "v1-old", "code_hash": "old_hash"},
        ]

        summary = self.checker.get_summary(findings)

        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["fresh"], 1)
        self.assertEqual(summary["stale"], 2)
        self.assertEqual(summary["code_changed"], 1)


class TestFormatStalenessWarning(unittest.TestCase):
    """Test warning formatting."""

    def test_no_warning_when_fresh(self):
        """No warning for fresh findings."""
        result = StalenessResult(stale=False)
        warning = format_staleness_warning(result)
        self.assertEqual(warning, "")

    def test_warning_includes_versions(self):
        """Warning shows version info."""
        result = StalenessResult(
            stale=True,
            finding_version="v1-old",
            current_version="v2-new",
        )
        warning = format_staleness_warning(result)

        self.assertIn("v1-old", warning)
        self.assertIn("v2-new", warning)

    def test_critical_warning_for_code_change(self):
        """Critical severity for code change."""
        result = StalenessResult(stale=True, code_changed=True)
        warning = format_staleness_warning(result)

        self.assertIn("CRITICAL", warning)

    def test_warning_includes_recommendation(self):
        """Warning includes recommendation."""
        result = StalenessResult(
            stale=True,
            recommendation="Run vkg refresh",
        )
        warning = format_staleness_warning(result)

        self.assertIn("vkg refresh", warning)

    def test_verbose_includes_details(self):
        """Verbose mode includes details."""
        result = StalenessResult(
            stale=True,
            details={"reason": "test_reason"},
        )
        warning = format_staleness_warning(result, verbose=True)

        self.assertIn("test_reason", warning)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def setUp(self):
        self.current_version = GraphVersion(
            version_id="v2-current",
            fingerprint="fp",
            code_hash="ch",
            created_at=datetime.now(),
        )

    def test_check_finding_staleness_dict(self):
        """check_finding_staleness works with dict."""
        finding = {"graph_version": "v1-old", "code_hash": "old_hash"}

        result = check_finding_staleness(finding, self.current_version)

        self.assertTrue(result.stale)

    def test_check_finding_staleness_object(self):
        """check_finding_staleness works with object."""
        finding = MagicMock()
        finding.graph_version = "v2-current"
        finding.code_hash = "ch"
        finding.created_at = None

        result = check_finding_staleness(finding, self.current_version)

        self.assertFalse(result.stale)

    def test_summarize_staleness(self):
        """summarize_staleness creates readable summary."""
        findings = [
            {"graph_version": "v2-current"},
            {"graph_version": "v1-old"},
        ]

        summary = summarize_staleness(findings, self.current_version)

        self.assertIn("Total findings: 2", summary)
        self.assertIn("Fresh: 1", summary)
        self.assertIn("Stale: 1", summary)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_empty_findings_list(self):
        """Handles empty findings list."""
        version = GraphVersion(
            version_id="v1",
            fingerprint="fp",
            code_hash="ch",
            created_at=datetime.now(),
        )
        checker = StalenessChecker(version)

        results = checker.check_all([])
        summary = checker.get_summary([])

        self.assertEqual(len(results), 0)
        self.assertEqual(summary["total"], 0)

    def test_generator_handles_empty_graph(self):
        """Generator handles empty graph."""
        gen = VersionGenerator()
        version = gen.generate({}, [])

        self.assertIsInstance(version, GraphVersion)
        self.assertEqual(len(version.fingerprint), 64)

    def test_generator_handles_string_graph(self):
        """Generator handles string representation."""
        gen = VersionGenerator()
        version = gen.generate("some string", [])

        self.assertIsInstance(version, GraphVersion)

    def test_store_handles_corrupted_file(self):
        """Store handles corrupted version file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VersionStore(Path(tmpdir))

            # Create corrupted file
            bad_file = store.versions_dir / "v1-bad.json"
            bad_file.write_text("not valid json")

            versions = store.list_versions()
            # Should not crash, just skip bad file
            self.assertEqual(len(versions), 0)


if __name__ == "__main__":
    unittest.main()
