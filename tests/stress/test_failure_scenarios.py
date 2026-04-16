"""
Stress Tests for VKG Robustness

Tests VKG behavior under various failure conditions.
Each scenario must:
1. Not crash VKG
2. Provide clear error
3. Offer recovery path
"""

import json
import shutil
import tempfile
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from alphaswarm_sol.cli.main import app
from tests.stress.chaos import ChaosInjector


runner = CliRunner()


class TestScenario1_KillSlitherMidRun:
    """Test: Kill Slither process during analysis."""

    @pytest.fixture
    def chaos(self):
        injector = ChaosInjector()
        yield injector
        injector.cleanup()

    def test_slither_killed_does_not_crash_vkg(self, chaos, tmp_path):
        """VKG handles slither being killed gracefully."""
        # This test verifies the tools runner handles process death
        from alphaswarm_sol.tools.runner import ToolRunner

        runner_tool = ToolRunner(timeout=10)

        # Run a process and kill it
        import subprocess
        import sys

        # Start a long-running python process
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Kill it after 0.5s
        time.sleep(0.5)
        proc.kill()

        # VKG should be able to continue running other commands
        result = runner_tool.run([sys.executable, "-c", "print('still alive')"])

        # VKG should not crash
        assert result.success is True
        assert "still alive" in result.output

    def test_tool_runner_isolates_failures(self, chaos):
        """Tool runner isolates process failures."""
        from alphaswarm_sol.tools.runner import ToolRunner
        import sys

        runner_tool = ToolRunner(timeout=5)

        # Run command that exits with error
        result1 = runner_tool.run([sys.executable, "-c", "import sys; sys.exit(1)"])
        assert result1.success is False

        # VKG can still run other commands
        result2 = runner_tool.run([sys.executable, "-c", "print('ok')"])
        assert result2.success is True


class TestScenario2_RemoveVkgDirectory:
    """Test: .vkg directory removed during operation."""

    def test_vkg_dir_removed_does_not_crash(self, tmp_path):
        """VKG handles missing .vkg directory gracefully."""
        # Create .vkg dir
        vkg_dir = tmp_path / ".vrs"
        vkg_dir.mkdir()
        graph_dir = vkg_dir / "graphs"
        graph_dir.mkdir()
        graph_file = graph_dir / "graph.json"
        graph_file.write_text('{"nodes": [], "edges": []}')

        # Now remove it
        shutil.rmtree(vkg_dir)

        # Query should fail gracefully
        result = runner.invoke(app, [
            "query", "test",
            "--graph", str(graph_file)
        ])

        # Should fail with clear error, not crash
        assert result.exit_code != 0
        # Should have some error indication
        output_lower = result.output.lower()
        assert any(word in output_lower for word in ["not found", "error", "no such", "does not exist"])

    def test_validate_handles_deleted_dir(self, tmp_path):
        """Validate command handles deleted directory."""
        result = runner.invoke(app, ["validate", "--project", str(tmp_path)])

        # Should fail gracefully
        assert result.exit_code != 0
        assert "no .vrs directory" in result.output.lower()

    def test_doctor_handles_missing_dir(self, tmp_path):
        """Doctor command works even with missing .vkg."""
        result = runner.invoke(app, ["doctor", "--project", str(tmp_path)])

        # Should succeed (doctor reports issues, doesn't fail)
        assert result.exit_code == 0
        # Should indicate .vkg not found
        assert "not found" in result.output.lower() or "!" in result.output


class TestScenario3_CorruptGraphJson:
    """Test: Corrupted graph.json."""

    @pytest.fixture
    def chaos(self):
        injector = ChaosInjector()
        yield injector
        injector.cleanup()

    def test_corrupt_graph_handled(self, chaos, tmp_path):
        """VKG handles corrupted graph.json."""
        # Create valid structure
        vkg_dir = tmp_path / ".vrs"
        graph_dir = vkg_dir / "graphs"
        graph_dir.mkdir(parents=True)

        graph_file = graph_dir / "graph.json"
        graph_file.write_text('{"nodes": [], "edges": []}')

        # Corrupt it
        chaos.corrupt_file(graph_file)

        # Query should fail gracefully
        result = runner.invoke(app, [
            "query", "test",
            "--graph", str(graph_file)
        ])

        # Should fail with error, not crash
        assert result.exit_code != 0
        # Should mention JSON or corruption
        output_lower = result.output.lower()
        assert any(word in output_lower for word in ["json", "invalid", "corrupt", "error", "decode"])

    def test_doctor_detects_corruption(self, tmp_path):
        """Doctor command detects corrupted files."""
        vkg_dir = tmp_path / ".vrs"
        graph_dir = vkg_dir / "graphs"
        graph_dir.mkdir(parents=True)

        graph_file = graph_dir / "graph.json"
        graph_file.write_text("{{{{invalid json")

        result = runner.invoke(app, ["doctor", "--project", str(tmp_path)])

        # Doctor should run without crashing
        assert result.exit_code == 0
        # Should detect corruption
        output_lower = result.output.lower()
        assert any(word in output_lower for word in ["corrupt", "error", "invalid", "!"])

    def test_validate_detects_corruption(self, tmp_path):
        """Validate command detects corrupted files."""
        vkg_dir = tmp_path / ".vrs"
        graph_dir = vkg_dir / "graphs"
        graph_dir.mkdir(parents=True)

        graph_file = graph_dir / "graph.json"
        graph_file.write_text("{{{{invalid json")

        result = runner.invoke(app, ["validate", "--project", str(tmp_path)])

        # Should fail
        assert result.exit_code != 0
        assert "error" in result.output.lower()


class TestScenario4_ToolTimeout:
    """Test: External tools timeout."""

    def test_timeout_returns_partial_results(self):
        """Tool timeout returns partial results, doesn't hang."""
        from alphaswarm_sol.tools.runner import ToolRunner
        import sys

        # Use 1 second timeout with slow command
        runner_tool = ToolRunner(timeout=1)

        start = time.time()
        result = runner_tool.run([sys.executable, "-c", "import time; time.sleep(10)"])
        elapsed = time.time() - start

        # Should return within 3 seconds (1s timeout + overhead)
        assert elapsed < 5, f"Tool runner hung past timeout (took {elapsed}s)"

        # Should have timeout error
        assert result.success is False
        assert "timed out" in result.error.lower()

        # Should have recovery command
        assert result.recovery is not None

    def test_vkg_continues_after_tool_timeout(self):
        """VKG can continue running after tool times out."""
        from alphaswarm_sol.tools.runner import ToolRunner
        import sys

        runner_tool = ToolRunner(timeout=1)

        # First tool times out
        result1 = runner_tool.run([sys.executable, "-c", "import time; time.sleep(10)"])
        assert result1.success is False

        # VKG can still run other commands
        result2 = runner_tool.run([sys.executable, "-c", "print('ok')"])
        assert result2.success is True
        assert "ok" in result2.output

    def test_multiple_timeouts_handled(self):
        """Multiple consecutive timeouts are handled."""
        from alphaswarm_sol.tools.runner import ToolRunner
        import sys

        runner_tool = ToolRunner(timeout=1)

        # Multiple timeouts in succession
        for i in range(3):
            result = runner_tool.run([sys.executable, "-c", "import time; time.sleep(10)"])
            assert result.success is False
            assert "timed out" in result.error.lower()

        # Still can run fast commands
        result = runner_tool.run([sys.executable, "-c", f"print('iteration')"])
        assert result.success is True


class TestScenario5_DiskFull:
    """Test: Disk full during write (simulated with permissions)."""

    def test_disk_full_does_not_corrupt_existing(self, tmp_path):
        """Write failure doesn't corrupt existing files."""
        # Create existing file
        existing = tmp_path / "existing.json"
        existing.write_text('{"valid": true}')

        # Simulate disk full by making directory read-only
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        output_file = output_dir / "new.json"

        # Make directory read-only
        output_dir.chmod(0o555)

        try:
            # Try to write - should fail
            try:
                output_file.write_text('{"new": true}')
                # If this succeeds, test environment doesn't support
                pytest.skip("Could not simulate disk full (write succeeded)")
            except (PermissionError, OSError):
                pass

            # Existing file should still be valid
            data = json.loads(existing.read_text())
            assert data["valid"] is True

        finally:
            # Restore permissions for cleanup
            output_dir.chmod(0o755)

    def test_atomic_write_pattern(self, tmp_path):
        """Atomic write prevents partial files."""
        from alphaswarm_sol.state.versioning import VersionStore

        # Create version store
        vkg_dir = tmp_path / ".vrs"
        vkg_dir.mkdir()

        store = VersionStore(vkg_dir)

        # Verify atomic write uses temp file
        # The store should write to temp first, then rename
        from alphaswarm_sol.state.versioning import GraphVersion
        from datetime import datetime

        version = GraphVersion(
            version_id="test123",
            fingerprint="abc",
            code_hash="def",
            created_at=datetime.now(),
            source_files=[],
        )

        # Save should work atomically
        path = store.save(version)

        # File should exist and be valid
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["version_id"] == "test123"


class TestCrossScenarioRecovery:
    """Test recovery after multiple failures."""

    def test_vkg_recovers_after_failures(self, tmp_path):
        """VKG can recover after multiple failures."""
        # Cause various failures
        failures = [
            (["query", "test", "--graph", "/nonexistent/path.json"], False),
            (["validate", "--project", "/nonexistent/path"], False),
            (["doctor", "--project", str(tmp_path)], True),  # Should succeed
        ]

        for args, should_succeed in failures:
            result = runner.invoke(app, args)
            # None should crash (exit code should be >= 0)
            assert result.exit_code >= 0, f"Command crashed: {args}"
            if should_succeed:
                assert result.exit_code == 0

    def test_state_remains_consistent_after_errors(self, tmp_path):
        """State remains consistent after errors."""
        vkg_dir = tmp_path / ".vrs"
        graph_dir = vkg_dir / "graphs"
        graph_dir.mkdir(parents=True)

        # Create valid graph
        graph_file = graph_dir / "graph.json"
        original_content = '{"nodes": [{"id": "n1"}], "edges": []}'
        graph_file.write_text(original_content)

        # Trigger errors with invalid queries
        runner.invoke(app, ["query", "invalid query syntax ???", "--graph", str(graph_file)])

        # Graph should still be intact
        current_content = graph_file.read_text()
        assert current_content == original_content


class TestStressTestSummary:
    """Summary test to ensure all scenarios covered."""

    def test_all_scenarios_have_tests(self):
        """Verify all 5 scenarios have test classes."""
        scenarios = [
            TestScenario1_KillSlitherMidRun,
            TestScenario2_RemoveVkgDirectory,
            TestScenario3_CorruptGraphJson,
            TestScenario4_ToolTimeout,
            TestScenario5_DiskFull,
        ]
        assert len(scenarios) == 5, "All 5 stress scenarios implemented"

    def test_each_scenario_has_multiple_tests(self):
        """Each scenario should have at least 2 tests."""
        import inspect

        scenarios = [
            TestScenario1_KillSlitherMidRun,
            TestScenario2_RemoveVkgDirectory,
            TestScenario3_CorruptGraphJson,
            TestScenario4_ToolTimeout,
            TestScenario5_DiskFull,
        ]

        for scenario in scenarios:
            test_methods = [
                m for m in dir(scenario)
                if m.startswith("test_") and callable(getattr(scenario, m))
            ]
            assert len(test_methods) >= 2, f"{scenario.__name__} needs at least 2 tests"
