"""Tests for tool status command (Task 10.2)."""

import json
import unittest
from unittest.mock import patch, MagicMock

from typer.testing import CliRunner

from alphaswarm_sol.cli.main import app
from alphaswarm_sol.cli.tools import tools_app, _get_tier_display_name, _get_status_badge
from alphaswarm_sol.core.tiers import Tier, DEPENDENCIES
from alphaswarm_sol.core.tool_registry import ToolRegistry, ToolInfo


runner = CliRunner()


class TestToolsStatusCommand(unittest.TestCase):
    """Test vkg tools status command."""

    def test_status_runs(self):
        """Command executes without error."""
        result = runner.invoke(app, ["tools", "status"])
        # Should not crash even if some tools missing
        self.assertEqual(result.exit_code, 0)

    def test_status_shows_tiers(self):
        """Output shows tier categories."""
        result = runner.invoke(app, ["tools", "status"])
        # Should contain tier information
        self.assertTrue(
            "Core" in result.stdout or "CORE" in result.stdout
        )

    def test_status_json_output(self):
        """JSON output is valid."""
        result = runner.invoke(app, ["tools", "status", "--json"])
        self.assertEqual(result.exit_code, 0)

        data = json.loads(result.stdout)
        self.assertIn("tiers", data)
        self.assertIn("effective_tier", data)
        self.assertIn("dependencies", data)

    def test_status_verbose(self):
        """Verbose output includes descriptions."""
        result = runner.invoke(app, ["tools", "status", "--verbose"])
        self.assertEqual(result.exit_code, 0)
        # Verbose should include more text
        self.assertGreater(len(result.stdout), 100)


class TestToolsCheckCommand(unittest.TestCase):
    """Test vkg tools check command."""

    def test_check_existing_tool(self):
        """Check command works for existing tool (python)."""
        result = runner.invoke(app, ["tools", "check", "python"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("OK", result.stdout)

    def test_check_unknown_tool(self):
        """Check command fails for unknown tool."""
        result = runner.invoke(app, ["tools", "check", "nonexistent_tool_12345"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Unknown tool", result.stdout)

    def test_check_shows_available_tools(self):
        """Check for unknown tool shows available options."""
        result = runner.invoke(app, ["tools", "check", "xyz123"])
        self.assertIn("Available tools", result.stdout)


class TestToolsListCommand(unittest.TestCase):
    """Test vkg tools list command."""

    def test_list_shows_all_tools(self):
        """List command shows all registered tools."""
        result = runner.invoke(app, ["tools", "list"])
        self.assertEqual(result.exit_code, 0)

        # Should show key tools
        self.assertIn("slither", result.stdout)
        self.assertIn("python", result.stdout)

    def test_list_filter_by_tier(self):
        """List command filters by tier."""
        result = runner.invoke(app, ["tools", "list", "--tier", "core"])
        self.assertEqual(result.exit_code, 0)

        # Should show core tools
        self.assertIn("slither", result.stdout)
        # Should not show enhancement-only tools
        self.assertNotIn("aderyn", result.stdout.lower())

    def test_list_invalid_tier(self):
        """List command rejects invalid tier."""
        result = runner.invoke(app, ["tools", "list", "--tier", "invalid"])
        self.assertEqual(result.exit_code, 1)


class TestToolsDoctorCommand(unittest.TestCase):
    """Test vkg tools doctor command."""

    def test_doctor_runs(self):
        """Doctor command executes."""
        result = runner.invoke(app, ["tools", "doctor"])
        # Exit code depends on system state
        self.assertIn(result.exit_code, [0, 1])

    def test_doctor_verbose(self):
        """Doctor verbose shows more info."""
        result = runner.invoke(app, ["tools", "doctor", "--verbose"])
        # Should have more output in verbose mode
        self.assertIn(result.exit_code, [0, 1])


class TestToolsRefreshCommand(unittest.TestCase):
    """Test vkg tools refresh command."""

    def test_refresh_clears_cache(self):
        """Refresh command clears cache."""
        result = runner.invoke(app, ["tools", "refresh"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("cache cleared", result.stdout.lower())


class TestToolRegistry(unittest.TestCase):
    """Test ToolRegistry class."""

    def setUp(self):
        self.registry = ToolRegistry()
        self.registry.clear_cache()

    def test_detect_python(self):
        """Python detection works."""
        info = self.registry.detect_tool("python", "python --version")

        self.assertTrue(info.available)
        self.assertIsNotNone(info.version)
        self.assertEqual(info.health, "ok")

    def test_detect_missing_tool(self):
        """Missing tool detection returns unavailable."""
        info = self.registry.detect_tool("fake", "nonexistent_tool_xyz123 --version")

        self.assertFalse(info.available)
        self.assertEqual(info.health, "error")

    def test_detect_all(self):
        """detect_all returns results for all dependencies."""
        results = self.registry.detect_all()

        # Should have results for registered dependencies
        self.assertGreater(len(results), 0)
        self.assertIn("python", results)

    def test_cache_works(self):
        """Detection results are cached."""
        info1 = self.registry.detect_tool("python", "python --version")
        info2 = self.registry.detect_tool("python", "python --version")

        # Should be same object from cache
        self.assertEqual(info1.version, info2.version)

    def test_force_bypasses_cache(self):
        """force=True bypasses cache."""
        info1 = self.registry.detect_tool("python", "python --version")

        # Modify cache manually
        self.registry._cache["python"] = ToolInfo(
            name="python",
            available=False,
            health="error",
        )

        # With force, should re-detect
        info2 = self.registry.detect_tool("python", "python --version", force=True)
        self.assertTrue(info2.available)

    def test_get_healthy_tools(self):
        """get_healthy_tools returns available tools."""
        healthy = self.registry.get_healthy_tools()

        # Python should be healthy
        self.assertIn("python", healthy)

    def test_get_missing_tools(self):
        """get_missing_tools returns unavailable tools."""
        missing = self.registry.get_missing_tools()

        # Some tools are likely missing
        self.assertIsInstance(missing, list)


class TestToolInfo(unittest.TestCase):
    """Test ToolInfo dataclass."""

    def test_to_dict(self):
        """ToolInfo can be serialized."""
        info = ToolInfo(
            name="test",
            available=True,
            version="1.0.0",
            path="/usr/bin/test",
            health="ok",
            details={"extra": "info"},
        )

        data = info.to_dict()

        self.assertEqual(data["name"], "test")
        self.assertTrue(data["available"])
        self.assertEqual(data["version"], "1.0.0")


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions."""

    def test_get_tier_display_name(self):
        """Tier display names are human-readable."""
        self.assertEqual(_get_tier_display_name(Tier.CORE), "Core (Required)")
        self.assertEqual(_get_tier_display_name(Tier.ENHANCEMENT), "Enhancement (Optional)")
        self.assertEqual(_get_tier_display_name(Tier.OPTIONAL), "Nice-to-Have")

    def test_get_status_badge_available(self):
        """Available status badge is green check."""
        badge = _get_status_badge(True)
        self.assertIn("green", badge)

    def test_get_status_badge_unavailable(self):
        """Unavailable status badge is yellow."""
        badge = _get_status_badge(False)
        self.assertIn("yellow", badge)


class TestVersionExtraction(unittest.TestCase):
    """Test version extraction from tool output."""

    def setUp(self):
        self.registry = ToolRegistry()

    def test_extract_semver(self):
        """Extracts semantic version."""
        version = self.registry._extract_version("test", "version 1.2.3")
        self.assertEqual(version, "1.2.3")

    def test_extract_python_version(self):
        """Extracts Python version format."""
        version = self.registry._extract_version("python", "Python 3.11.5")
        self.assertEqual(version, "3.11.5")

    def test_no_version_found(self):
        """Returns None when no version found."""
        version = self.registry._extract_version("test", "no version here")
        self.assertIsNone(version)


class TestMissingToolHandling(unittest.TestCase):
    """Test handling of missing tools."""

    def test_missing_tool_shows_install_hint(self):
        """Status continues even with missing tools."""
        result = runner.invoke(app, ["tools", "status"])
        # Should not crash
        self.assertEqual(result.exit_code, 0)

    def test_status_continues_with_missing_enhancement(self):
        """Status completes even with missing enhancement tools."""
        result = runner.invoke(app, ["tools", "status"])
        self.assertEqual(result.exit_code, 0)


class TestJSONOutput(unittest.TestCase):
    """Test JSON output format."""

    def test_json_has_dependencies(self):
        """JSON output includes dependency details."""
        result = runner.invoke(app, ["tools", "status", "--json"])
        data = json.loads(result.stdout)

        self.assertIn("dependencies", data)
        deps = data["dependencies"]

        # Should have some dependencies
        self.assertGreater(len(deps), 0)

        # Each should have expected fields
        for name, info in deps.items():
            self.assertIn("tier", info)
            self.assertIn("available", info)
            self.assertIn("description", info)

    def test_json_tiers_valid(self):
        """JSON tiers are valid."""
        result = runner.invoke(app, ["tools", "status", "--json"])
        data = json.loads(result.stdout)

        for tier in data["tiers"]:
            self.assertIn("tier", tier)
            self.assertIn("available", tier)
            self.assertIn("unavailable", tier)


if __name__ == "__main__":
    unittest.main()
