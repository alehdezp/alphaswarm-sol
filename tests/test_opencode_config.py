"""Tests for OpenCode configuration generator.

These tests validate that the OpenCode config generator produces valid
JSON configurations that OpenCode can discover and use.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from alphaswarm_sol.cli import app
from alphaswarm_sol.templates.opencode import (
    OpenCodeConfig,
    VKG_TOOLS,
    generate_opencode_config,
    get_tool_descriptions,
    write_opencode_config,
)

runner = CliRunner()


class TestOpenCodeConfig(unittest.TestCase):
    """Tests for OpenCodeConfig dataclass."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = OpenCodeConfig(project_path=Path("/test/project"))

        self.assertEqual(config.project_path, Path("/test/project"))
        self.assertEqual(config.vkg_command, ["uv", "run", "alphaswarm", "mcp-serve"])
        self.assertEqual(config.log_level, "INFO")
        self.assertEqual(config.timeout, 30000)
        self.assertTrue(config.enabled)
        self.assertEqual(config.additional_mcp, {})
        self.assertEqual(config.instructions_files, [".vrs/AGENTS.md"])

    def test_config_to_dict(self):
        """Test configuration serialization to dictionary."""
        config = OpenCodeConfig(project_path=Path("/test/project"))
        d = config.to_dict()

        # Check schema
        self.assertEqual(d["$schema"], "https://opencode.ai/config.json")

        # Check MCP section
        self.assertIn("mcp", d)
        self.assertIn("vkg", d["mcp"])
        self.assertEqual(d["mcp"]["vkg"]["type"], "local")
        self.assertEqual(d["mcp"]["vkg"]["command"], ["uv", "run", "alphaswarm", "mcp-serve"])
        self.assertTrue(d["mcp"]["vkg"]["enabled"])

        # Check tools enabled
        self.assertIn("tools", d)
        self.assertTrue(d["tools"]["vkg_*"])

        # Check permissions exist
        self.assertIn("permission", d)

    def test_config_to_json(self):
        """Test JSON serialization."""
        config = OpenCodeConfig(project_path=Path("/test/project"))
        json_str = config.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, dict)
        self.assertIn("mcp", parsed)

    def test_config_custom_command(self):
        """Test custom VKG command."""
        config = OpenCodeConfig(
            project_path=Path("/test/project"),
            vkg_command=["python", "-m", "alphaswarm_sol", "mcp-serve"],
        )
        d = config.to_dict()

        self.assertEqual(
            d["mcp"]["vkg"]["command"],
            ["python", "-m", "alphaswarm_sol", "mcp-serve"],
        )

    def test_config_additional_mcp(self):
        """Test adding additional MCP servers."""
        config = OpenCodeConfig(
            project_path=Path("/test/project"),
            additional_mcp={
                "github": {
                    "type": "remote",
                    "url": "https://github-mcp.example.com",
                }
            },
        )
        d = config.to_dict()

        self.assertIn("github", d["mcp"])
        self.assertEqual(d["mcp"]["github"]["type"], "remote")

    def test_config_custom_commands(self):
        """Test custom slash commands."""
        config = OpenCodeConfig(
            project_path=Path("/test/project"),
            custom_commands={
                "quick-check": {
                    "template": "Run a quick security check",
                    "description": "Fast security scan",
                }
            },
        )
        d = config.to_dict()

        self.assertIn("command", d)
        self.assertIn("quick-check", d["command"])
        self.assertIn("audit", d["command"])  # Default command should still exist


class TestGenerateOpencodeConfig(unittest.TestCase):
    """Tests for generate_opencode_config function."""

    def test_generates_valid_json(self):
        """Test that generated config is valid JSON."""
        config = generate_opencode_config(Path("/test/project"))

        # Should serialize without error
        json_str = json.dumps(config)
        parsed = json.loads(json_str)

        self.assertEqual(parsed, config)

    def test_has_expected_structure(self):
        """Test config has expected top-level keys."""
        config = generate_opencode_config(Path("/test/project"))

        expected_keys = ["$schema", "mcp", "tools", "permission", "command"]
        for key in expected_keys:
            self.assertIn(key, config, f"Missing key: {key}")

    def test_mcp_section_structure(self):
        """Test MCP section has correct structure."""
        config = generate_opencode_config(Path("/test/project"))

        mcp = config["mcp"]
        self.assertIn("vkg", mcp)

        vkg = mcp["vkg"]
        self.assertEqual(vkg["type"], "local")
        self.assertIn("command", vkg)
        self.assertIn("environment", vkg)
        self.assertIn("enabled", vkg)
        self.assertIn("timeout", vkg)

    def test_environment_variables(self):
        """Test environment variables are set correctly."""
        config = generate_opencode_config(
            Path("/test/project"),
            log_level="DEBUG",
        )

        env = config["mcp"]["vkg"]["environment"]
        self.assertEqual(env["VKG_PROJECT"], "/test/project")
        self.assertEqual(env["VKG_LOG_LEVEL"], "DEBUG")

    def test_tool_permissions(self):
        """Test tool permissions are set correctly."""
        config = generate_opencode_config(Path("/test/project"))

        permissions = config["permission"]

        # Check all tools have permissions
        for tool_name in VKG_TOOLS:
            perm_key = f"vkg_{tool_name}"
            self.assertIn(perm_key, permissions, f"Missing permission for: {tool_name}")

        # findings_update should require confirmation
        self.assertEqual(permissions["vkg_findings_update"], "ask")

        # Most tools should be allowed
        self.assertEqual(permissions["vkg_build_kg"], "allow")
        self.assertEqual(permissions["vkg_analyze"], "allow")
        self.assertEqual(permissions["vkg_query"], "allow")

    def test_string_path_input(self):
        """Test that string paths are accepted."""
        config = generate_opencode_config("/test/project")

        self.assertEqual(config["mcp"]["vkg"]["environment"]["VKG_PROJECT"], "/test/project")

    def test_instructions_included(self):
        """Test instructions files are included."""
        config = generate_opencode_config(Path("/test/project"))

        self.assertIn("instructions", config)
        self.assertIn(".vrs/AGENTS.md", config["instructions"])

    def test_custom_instructions(self):
        """Test custom instructions files."""
        config = generate_opencode_config(
            Path("/test/project"),
            instructions_files=["CLAUDE.md", ".vrs/AGENTS.md"],
        )

        self.assertEqual(config["instructions"], ["CLAUDE.md", ".vrs/AGENTS.md"])


class TestWriteOpencodeConfig(unittest.TestCase):
    """Tests for write_opencode_config function."""

    def test_writes_to_default_location(self):
        """Test writing to default location (project/opencode.json)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            output_path = write_opencode_config(project_path)

            expected_path = project_path / "opencode.json"
            self.assertEqual(output_path, expected_path)
            self.assertTrue(expected_path.exists())

            # Validate content
            content = expected_path.read_text()
            config = json.loads(content)
            self.assertIn("mcp", config)

    def test_writes_to_custom_location(self):
        """Test writing to custom location."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            custom_output = project_path / "configs" / "opencode.json"
            custom_output.parent.mkdir(parents=True, exist_ok=True)

            output_path = write_opencode_config(
                project_path,
                output_path=custom_output,
            )

            self.assertEqual(output_path, custom_output)
            self.assertTrue(custom_output.exists())

    def test_raises_on_existing_file(self):
        """Test raises FileExistsError when file exists and overwrite=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            existing = project_path / "opencode.json"
            existing.write_text("{}")

            with self.assertRaises(FileExistsError):
                write_opencode_config(project_path)

    def test_overwrites_when_requested(self):
        """Test overwrites existing file when overwrite=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            existing = project_path / "opencode.json"
            existing.write_text('{"old": "config"}')

            output_path = write_opencode_config(project_path, overwrite=True)

            content = output_path.read_text()
            config = json.loads(content)
            self.assertIn("mcp", config)
            self.assertNotIn("old", config)

    def test_string_paths_accepted(self):
        """Test that string paths work for both arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = write_opencode_config(
                tmpdir,  # string path
                output_path=f"{tmpdir}/custom.json",  # string path
            )

            self.assertTrue(output_path.exists())


class TestVKGTools(unittest.TestCase):
    """Tests for VKG_TOOLS definitions."""

    def test_all_tools_have_descriptions(self):
        """Test all tools have descriptions."""
        for name, info in VKG_TOOLS.items():
            self.assertIn("description", info, f"Tool {name} missing description")
            self.assertIsInstance(info["description"], str)
            self.assertGreater(len(info["description"]), 10)

    def test_all_tools_have_permissions(self):
        """Test all tools have valid permissions."""
        valid_permissions = {"allow", "ask", "deny"}

        for name, info in VKG_TOOLS.items():
            self.assertIn("permission", info, f"Tool {name} missing permission")
            self.assertIn(
                info["permission"],
                valid_permissions,
                f"Tool {name} has invalid permission: {info['permission']}",
            )

    def test_expected_tools_present(self):
        """Test expected tools are defined."""
        expected_tools = [
            "build_kg",
            "analyze",
            "query",
            "findings_list",
            "findings_next",
            "findings_show",
            "findings_update",
            "report",
            "patterns_list",
        ]

        for tool in expected_tools:
            self.assertIn(tool, VKG_TOOLS, f"Expected tool missing: {tool}")

    def test_findings_update_requires_confirmation(self):
        """Test findings_update requires user confirmation."""
        self.assertEqual(VKG_TOOLS["findings_update"]["permission"], "ask")


class TestGetToolDescriptions(unittest.TestCase):
    """Tests for get_tool_descriptions function."""

    def test_returns_dict(self):
        """Test returns dictionary of tool descriptions."""
        descriptions = get_tool_descriptions()

        self.assertIsInstance(descriptions, dict)
        self.assertGreater(len(descriptions), 0)

    def test_all_tools_included(self):
        """Test all tools have descriptions."""
        descriptions = get_tool_descriptions()

        for tool in VKG_TOOLS:
            self.assertIn(tool, descriptions)

    def test_descriptions_are_strings(self):
        """Test all descriptions are strings."""
        descriptions = get_tool_descriptions()

        for name, desc in descriptions.items():
            self.assertIsInstance(desc, str, f"Description for {name} is not string")


class TestConfigSchemaCompliance(unittest.TestCase):
    """Tests for OpenCode schema compliance."""

    def test_schema_url_correct(self):
        """Test schema URL matches OpenCode's schema."""
        config = generate_opencode_config(Path("/test"))

        self.assertEqual(config["$schema"], "https://opencode.ai/config.json")

    def test_mcp_type_is_local(self):
        """Test MCP type is 'local' for stdio transport."""
        config = generate_opencode_config(Path("/test"))

        self.assertEqual(config["mcp"]["vkg"]["type"], "local")

    def test_command_is_array(self):
        """Test command is an array of strings."""
        config = generate_opencode_config(Path("/test"))

        command = config["mcp"]["vkg"]["command"]
        self.assertIsInstance(command, list)
        for item in command:
            self.assertIsInstance(item, str)

    def test_environment_is_dict(self):
        """Test environment is a dictionary."""
        config = generate_opencode_config(Path("/test"))

        env = config["mcp"]["vkg"]["environment"]
        self.assertIsInstance(env, dict)

    def test_timeout_is_integer(self):
        """Test timeout is an integer in milliseconds."""
        config = generate_opencode_config(Path("/test"))

        timeout = config["mcp"]["vkg"]["timeout"]
        self.assertIsInstance(timeout, int)
        self.assertGreater(timeout, 0)

    def test_enabled_is_boolean(self):
        """Test enabled is a boolean."""
        config = generate_opencode_config(Path("/test"))

        enabled = config["mcp"]["vkg"]["enabled"]
        self.assertIsInstance(enabled, bool)


class TestInitCliCommand(unittest.TestCase):
    """Tests for 'vkg init' CLI command."""

    def setUp(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_vkg_directory(self):
        """Test init creates .vrs directory."""
        result = runner.invoke(app, ["init", self.temp_dir])

        self.assertEqual(result.exit_code, 0)
        self.assertTrue((self.project_path / ".vrs").exists())
        self.assertTrue((self.project_path / ".vrs" / "graphs").exists())

    def test_init_with_opencode_flag(self):
        """Test init with --opencode creates opencode.json."""
        result = runner.invoke(app, ["init", self.temp_dir, "--opencode"])

        self.assertEqual(result.exit_code, 0)
        self.assertTrue((self.project_path / "opencode.json").exists())

        # Verify content
        content = (self.project_path / "opencode.json").read_text()
        config = json.loads(content)
        self.assertIn("mcp", config)
        self.assertIn("vkg", config["mcp"])

    def test_init_opencode_without_overwrite_fails(self):
        """Test init --opencode fails if opencode.json exists."""
        # Create existing file
        (self.project_path / "opencode.json").write_text("{}")

        result = runner.invoke(app, ["init", self.temp_dir, "--opencode"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("already exists", result.output)

    def test_init_opencode_with_overwrite_succeeds(self):
        """Test init --opencode --overwrite replaces existing file."""
        # Create existing file
        (self.project_path / "opencode.json").write_text('{"old": true}')

        result = runner.invoke(
            app, ["init", self.temp_dir, "--opencode", "--overwrite"]
        )

        self.assertEqual(result.exit_code, 0)

        # Verify new content
        content = (self.project_path / "opencode.json").read_text()
        config = json.loads(content)
        self.assertIn("mcp", config)
        self.assertNotIn("old", config)

    def test_init_nonexistent_path_fails(self):
        """Test init fails for nonexistent path."""
        result = runner.invoke(app, ["init", "/nonexistent/path/12345"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("not found", result.output)

    def test_init_output_shows_tools(self):
        """Test init --opencode output mentions available tools."""
        result = runner.invoke(app, ["init", self.temp_dir, "--opencode"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("vkg_build_kg", result.output)
        self.assertIn("vkg_analyze", result.output)
        self.assertIn("vkg_query", result.output)

    def test_init_shows_next_steps(self):
        """Test init shows next steps."""
        result = runner.invoke(app, ["init", self.temp_dir])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("build-kg", result.output)


if __name__ == "__main__":
    unittest.main()
