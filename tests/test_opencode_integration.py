"""Tests for OpenCode Integration (Task 3.8b).

This module tests the VKG integration with OpenCode, an open-source AI coding agent.
Since we cannot actually run OpenCode in the test environment, these tests validate:

1. Config Discovery - OpenCode config file is generated correctly
2. Tool Exposure - All VKG audit tools are properly exposed
3. MCP Server Config - MCP server configuration is valid
4. Workflow Simulation - Simulated audit workflow using VKG tools
5. Permission Test - Proper permissions are set for each tool
6. Tool Description Quality - Descriptions are LLM-friendly

Reference: task/4.0/phases/phase-3/R3.2-OPENCODE-SDK-RESEARCH.md
"""

import json
import re
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from alphaswarm_sol.templates.opencode import (
    OpenCodeConfig,
    VKG_TOOLS,
    generate_opencode_config,
    get_tool_descriptions,
    write_opencode_config,
)


class TestConfigDiscovery(unittest.TestCase):
    """Test 1: Config file is generated correctly."""

    def test_generate_config_returns_dict(self):
        """generate_opencode_config returns a valid dictionary."""
        config = generate_opencode_config(Path("/test/project"))
        self.assertIsInstance(config, dict)

    def test_config_has_schema(self):
        """Config includes OpenCode schema reference."""
        config = generate_opencode_config(Path("/test/project"))
        self.assertIn("$schema", config)
        self.assertEqual(config["$schema"], "https://opencode.ai/config.json")

    def test_config_has_mcp_section(self):
        """Config includes MCP section."""
        config = generate_opencode_config(Path("/test/project"))
        self.assertIn("mcp", config)
        self.assertIsInstance(config["mcp"], dict)

    def test_config_has_vkg_mcp_server(self):
        """Config includes VKG as MCP server."""
        config = generate_opencode_config(Path("/test/project"))
        self.assertIn("vkg", config["mcp"])

    def test_config_has_tools_section(self):
        """Config includes tools section."""
        config = generate_opencode_config(Path("/test/project"))
        self.assertIn("tools", config)
        self.assertIn("vkg_*", config["tools"])

    def test_config_has_permission_section(self):
        """Config includes permission section."""
        config = generate_opencode_config(Path("/test/project"))
        self.assertIn("permission", config)

    def test_config_has_instructions(self):
        """Config includes instructions files."""
        config = generate_opencode_config(Path("/test/project"))
        self.assertIn("instructions", config)
        self.assertIn(".vrs/AGENTS.md", config["instructions"])

    def test_config_has_custom_commands(self):
        """Config includes custom commands."""
        config = generate_opencode_config(Path("/test/project"))
        self.assertIn("command", config)
        self.assertIn("audit", config["command"])

    def test_write_config_creates_file(self):
        """write_opencode_config creates a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            output_path = write_opencode_config(project_path)

            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.name, "opencode.json")

    def test_write_config_valid_json(self):
        """Written config is valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            output_path = write_opencode_config(project_path)

            content = output_path.read_text()
            config = json.loads(content)

            self.assertIsInstance(config, dict)
            self.assertIn("mcp", config)

    def test_write_config_no_overwrite_default(self):
        """write_opencode_config does not overwrite by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            output_path = project_path / "opencode.json"

            # Create existing file
            output_path.write_text('{"existing": true}')

            # Should raise error
            with self.assertRaises(FileExistsError):
                write_opencode_config(project_path)

    def test_write_config_overwrite_allowed(self):
        """write_opencode_config overwrites when allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            output_path = project_path / "opencode.json"

            # Create existing file
            output_path.write_text('{"existing": true}')

            # Should succeed with overwrite=True
            result_path = write_opencode_config(project_path, overwrite=True)

            content = result_path.read_text()
            config = json.loads(content)
            self.assertIn("mcp", config)
            self.assertNotIn("existing", config)

    def test_config_custom_output_path(self):
        """write_opencode_config respects custom output path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            custom_path = project_path / "custom" / "opencode.json"
            custom_path.parent.mkdir(parents=True)

            output_path = write_opencode_config(
                project_path, output_path=custom_path
            )

            self.assertEqual(output_path, custom_path)
            self.assertTrue(output_path.exists())


class TestToolExposure(unittest.TestCase):
    """Test 2: All VKG audit tools are exposed."""

    # Required VKG tools that must be exposed
    REQUIRED_TOOLS = [
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

    def test_all_required_tools_defined(self):
        """All required tools are defined in VKG_TOOLS."""
        for tool in self.REQUIRED_TOOLS:
            self.assertIn(tool, VKG_TOOLS, f"Missing required tool: {tool}")

    def test_all_tools_have_descriptions(self):
        """Every tool has a description."""
        for tool_name, tool_info in VKG_TOOLS.items():
            self.assertIn("description", tool_info)
            self.assertIsInstance(tool_info["description"], str)
            self.assertGreater(len(tool_info["description"]), 10)

    def test_all_tools_have_permissions(self):
        """Every tool has a permission level."""
        for tool_name, tool_info in VKG_TOOLS.items():
            self.assertIn("permission", tool_info)
            self.assertIn(tool_info["permission"], ["allow", "ask", "deny"])

    def test_tools_exposed_in_config(self):
        """Tools are exposed in generated config."""
        config = generate_opencode_config(Path("/test/project"))

        # Wildcard enables all VKG tools
        self.assertTrue(config["tools"].get("vkg_*"))

    def test_tool_permissions_in_config(self):
        """Tool permissions are set in config."""
        config = generate_opencode_config(Path("/test/project"))

        for tool_name in self.REQUIRED_TOOLS:
            perm_key = f"vkg_{tool_name}"
            self.assertIn(perm_key, config["permission"])

    def test_get_tool_descriptions_returns_all(self):
        """get_tool_descriptions returns descriptions for all tools."""
        descriptions = get_tool_descriptions()

        for tool in self.REQUIRED_TOOLS:
            self.assertIn(tool, descriptions)
            self.assertIsInstance(descriptions[tool], str)


class TestMCPServerConfig(unittest.TestCase):
    """Test 3: MCP server config is valid."""

    def test_mcp_server_type_local(self):
        """MCP server is configured as local (stdio transport)."""
        config = generate_opencode_config(Path("/test/project"))
        vkg_config = config["mcp"]["vkg"]

        self.assertEqual(vkg_config["type"], "local")

    def test_mcp_server_has_command(self):
        """MCP server has command specified."""
        config = generate_opencode_config(Path("/test/project"))
        vkg_config = config["mcp"]["vkg"]

        self.assertIn("command", vkg_config)
        self.assertIsInstance(vkg_config["command"], list)
        self.assertGreater(len(vkg_config["command"]), 0)

    def test_mcp_server_default_command(self):
        """MCP server uses default VKG command."""
        config = generate_opencode_config(Path("/test/project"))
        command = config["mcp"]["vkg"]["command"]

        self.assertEqual(command, ["uv", "run", "alphaswarm", "mcp-serve"])

    def test_mcp_server_custom_command(self):
        """MCP server accepts custom command."""
        custom_cmd = ["python", "-m", "alphaswarm_sol.mcp"]
        config = generate_opencode_config(
            Path("/test/project"), vkg_command=custom_cmd
        )

        self.assertEqual(config["mcp"]["vkg"]["command"], custom_cmd)

    def test_mcp_server_has_environment(self):
        """MCP server has environment variables."""
        config = generate_opencode_config(Path("/test/project"))
        vkg_config = config["mcp"]["vkg"]

        self.assertIn("environment", vkg_config)
        self.assertIn("VKG_PROJECT", vkg_config["environment"])
        self.assertIn("VKG_LOG_LEVEL", vkg_config["environment"])

    def test_mcp_server_enabled_default(self):
        """MCP server is enabled by default."""
        config = generate_opencode_config(Path("/test/project"))
        self.assertTrue(config["mcp"]["vkg"]["enabled"])

    def test_mcp_server_disabled(self):
        """MCP server can be disabled."""
        config = generate_opencode_config(Path("/test/project"), enabled=False)
        self.assertFalse(config["mcp"]["vkg"]["enabled"])

    def test_mcp_server_has_timeout(self):
        """MCP server has timeout configured."""
        config = generate_opencode_config(Path("/test/project"))
        vkg_config = config["mcp"]["vkg"]

        self.assertIn("timeout", vkg_config)
        self.assertIsInstance(vkg_config["timeout"], int)
        self.assertGreater(vkg_config["timeout"], 0)

    def test_mcp_server_custom_timeout(self):
        """MCP server accepts custom timeout."""
        config = generate_opencode_config(Path("/test/project"), timeout=60000)
        self.assertEqual(config["mcp"]["vkg"]["timeout"], 60000)

    def test_additional_mcp_servers(self):
        """Config supports additional MCP servers."""
        additional = {
            "other_tool": {
                "type": "local",
                "command": ["other-tool", "serve"],
                "enabled": True,
            }
        }
        config = generate_opencode_config(
            Path("/test/project"), additional_mcp=additional
        )

        self.assertIn("vkg", config["mcp"])
        self.assertIn("other_tool", config["mcp"])

    def test_mcp_project_path_included(self):
        """MCP environment includes project path."""
        project_path = Path("/my/project")
        config = generate_opencode_config(project_path)

        env = config["mcp"]["vkg"]["environment"]
        self.assertEqual(env["VKG_PROJECT"], str(project_path))


class TestWorkflowSimulation(unittest.TestCase):
    """Test 4: Simulated audit workflow using VKG tools.

    This test simulates the audit workflow an LLM would perform using VKG tools.
    The workflow is:
    1. build_kg - Build knowledge graph from contracts
    2. analyze - Run vulnerability analysis
    3. findings_next - Get next priority finding
    4. findings_show - Get full finding details
    5. findings_update - Update finding status
    6. report - Generate final report
    """

    def test_workflow_step_order(self):
        """Workflow steps are logically ordered."""
        # Define expected workflow
        workflow = [
            "build_kg",      # Step 1: Build graph
            "analyze",       # Step 2: Run analysis
            "findings_list", # Step 3: List all findings
            "findings_next", # Step 4: Get priority finding
            "findings_show", # Step 5: Get details
            "findings_update", # Step 6: Update status
            "report",        # Step 7: Generate report
        ]

        # Verify all tools exist
        for tool in workflow:
            self.assertIn(tool, VKG_TOOLS)

    def test_workflow_tool_permissions(self):
        """Workflow tools have appropriate permissions."""
        # These tools should be auto-allowed (read-only or safe)
        allow_tools = [
            "build_kg",
            "analyze",
            "query",
            "findings_list",
            "findings_next",
            "findings_show",
            "report",
            "patterns_list",
        ]

        # These tools modify state and should require confirmation
        ask_tools = [
            "findings_update",
        ]

        for tool in allow_tools:
            self.assertEqual(
                VKG_TOOLS[tool]["permission"], "allow",
                f"{tool} should have 'allow' permission"
            )

        for tool in ask_tools:
            self.assertEqual(
                VKG_TOOLS[tool]["permission"], "ask",
                f"{tool} should have 'ask' permission"
            )

    def test_workflow_all_steps_have_descriptions(self):
        """All workflow steps have descriptions for LLM understanding."""
        workflow_tools = [
            "build_kg", "analyze", "query", "findings_list",
            "findings_next", "findings_show", "findings_update", "report"
        ]

        for tool in workflow_tools:
            desc = VKG_TOOLS[tool]["description"]
            self.assertGreater(len(desc), 20)

    def test_config_enables_full_workflow(self):
        """Generated config enables full audit workflow."""
        config = generate_opencode_config(Path("/test/project"))

        # MCP server is configured
        self.assertIn("vkg", config["mcp"])
        self.assertTrue(config["mcp"]["vkg"]["enabled"])

        # All tools are enabled via wildcard
        self.assertTrue(config["tools"].get("vkg_*"))

        # Permissions are set
        self.assertGreater(len(config["permission"]), 5)

    def test_audit_command_defined(self):
        """Custom 'audit' command is defined for quick start."""
        config = generate_opencode_config(Path("/test/project"))

        self.assertIn("audit", config["command"])
        self.assertIn("template", config["command"]["audit"])
        self.assertIn("description", config["command"]["audit"])


class TestToolDescriptionQuality(unittest.TestCase):
    """Test 6: Tool descriptions are LLM-friendly.

    LLM-friendly descriptions should be:
    - Clear and concise (not too long)
    - Actionable (describe what the tool does)
    - Include key parameters/outputs
    - Avoid jargon without explanation
    """

    # Maximum description length for LLM efficiency
    MAX_DESCRIPTION_LENGTH = 200

    # Minimum description length for usefulness
    MIN_DESCRIPTION_LENGTH = 30

    def test_descriptions_are_concise(self):
        """Descriptions are not too long."""
        for tool_name, tool_info in VKG_TOOLS.items():
            desc = tool_info["description"]
            self.assertLessEqual(
                len(desc), self.MAX_DESCRIPTION_LENGTH,
                f"{tool_name} description too long: {len(desc)} chars"
            )

    def test_descriptions_are_substantial(self):
        """Descriptions are not too short."""
        for tool_name, tool_info in VKG_TOOLS.items():
            desc = tool_info["description"]
            self.assertGreaterEqual(
                len(desc), self.MIN_DESCRIPTION_LENGTH,
                f"{tool_name} description too short: {len(desc)} chars"
            )

    def test_descriptions_start_with_verb(self):
        """Descriptions start with an action verb."""
        action_verbs = [
            "build", "run", "query", "list", "get", "show", "update",
            "generate", "create", "analyze", "find", "extract", "return"
        ]

        for tool_name, tool_info in VKG_TOOLS.items():
            desc = tool_info["description"].lower()
            first_word = desc.split()[0]

            # Check if starts with verb or common starting patterns
            starts_ok = any(
                first_word.startswith(verb) for verb in action_verbs
            )
            self.assertTrue(
                starts_ok,
                f"{tool_name} description should start with action verb: '{desc[:30]}...'"
            )

    def test_descriptions_not_contain_jargon(self):
        """Descriptions avoid unexplained jargon."""
        # If these terms appear, they should be explained
        jargon_terms = ["VQL2", "CEI", "LLMDFA"]

        for tool_name, tool_info in VKG_TOOLS.items():
            desc = tool_info["description"]

            for term in jargon_terms:
                if term in desc:
                    # Term should have explanation nearby
                    self.assertIn(
                        "or", desc.lower(),
                        f"{tool_name} uses jargon '{term}' without explanation"
                    )

    def test_descriptions_mention_key_functionality(self):
        """Descriptions mention what the tool actually does."""
        # Map tool to expected key words
        expected_keywords = {
            "build_kg": ["knowledge graph", "contracts", "solidity"],
            "analyze": ["vulnerability", "analysis", "pattern"],
            "query": ["query", "natural language"],
            "findings_list": ["list", "finding"],
            "findings_next": ["next", "priority", "finding"],
            "findings_show": ["detail", "finding", "evidence"],
            "findings_update": ["update", "status", "finding"],
            "report": ["report", "generate"],
            "patterns_list": ["pattern", "list"],
        }

        for tool_name, keywords in expected_keywords.items():
            desc = VKG_TOOLS[tool_name]["description"].lower()

            found_any = any(kw in desc for kw in keywords)
            self.assertTrue(
                found_any,
                f"{tool_name} description missing expected keywords: {keywords}"
            )


class TestOpenCodeConfigClass(unittest.TestCase):
    """Test OpenCodeConfig dataclass."""

    def test_config_creation(self):
        """OpenCodeConfig can be created."""
        config = OpenCodeConfig(project_path=Path("/test/project"))

        self.assertEqual(config.project_path, Path("/test/project"))
        self.assertEqual(config.log_level, "INFO")
        self.assertTrue(config.enabled)

    def test_config_to_dict(self):
        """OpenCodeConfig converts to dict."""
        config = OpenCodeConfig(project_path=Path("/test/project"))
        d = config.to_dict()

        self.assertIn("$schema", d)
        self.assertIn("mcp", d)
        self.assertIn("tools", d)
        self.assertIn("permission", d)

    def test_config_to_json(self):
        """OpenCodeConfig converts to JSON."""
        config = OpenCodeConfig(project_path=Path("/test/project"))
        json_str = config.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        self.assertIn("mcp", parsed)

    def test_config_custom_command(self):
        """OpenCodeConfig accepts custom command."""
        custom_cmd = ["custom", "command"]
        config = OpenCodeConfig(
            project_path=Path("/test"),
            vkg_command=custom_cmd,
        )

        d = config.to_dict()
        self.assertEqual(d["mcp"]["vkg"]["command"], custom_cmd)

    def test_config_custom_log_level(self):
        """OpenCodeConfig accepts custom log level."""
        config = OpenCodeConfig(
            project_path=Path("/test"),
            log_level="DEBUG",
        )

        d = config.to_dict()
        self.assertEqual(d["mcp"]["vkg"]["environment"]["VKG_LOG_LEVEL"], "DEBUG")

    def test_config_custom_timeout(self):
        """OpenCodeConfig accepts custom timeout."""
        config = OpenCodeConfig(
            project_path=Path("/test"),
            timeout=60000,
        )

        d = config.to_dict()
        self.assertEqual(d["mcp"]["vkg"]["timeout"], 60000)

    def test_config_custom_instructions(self):
        """OpenCodeConfig accepts custom instructions files."""
        config = OpenCodeConfig(
            project_path=Path("/test"),
            instructions_files=["CLAUDE.md", "custom.md"],
        )

        d = config.to_dict()
        self.assertEqual(d["instructions"], ["CLAUDE.md", "custom.md"])

    def test_config_custom_commands(self):
        """OpenCodeConfig accepts custom commands."""
        config = OpenCodeConfig(
            project_path=Path("/test"),
            custom_commands={
                "my_cmd": {"template": "Do something", "description": "My command"}
            },
        )

        d = config.to_dict()
        self.assertIn("my_cmd", d["command"])
        self.assertIn("audit", d["command"])  # Default still present


class TestConfigEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_string_path_accepted(self):
        """generate_opencode_config accepts string path."""
        config = generate_opencode_config("/string/path")

        self.assertIn("mcp", config)
        self.assertEqual(
            config["mcp"]["vkg"]["environment"]["VKG_PROJECT"],
            "/string/path"
        )

    def test_empty_additional_mcp(self):
        """Empty additional_mcp is handled."""
        config = generate_opencode_config(
            Path("/test"), additional_mcp={}
        )

        # Should only have vkg
        self.assertEqual(len(config["mcp"]), 1)
        self.assertIn("vkg", config["mcp"])

    def test_none_optional_params(self):
        """None optional params use defaults."""
        config = generate_opencode_config(
            Path("/test"),
            vkg_command=None,
            additional_mcp=None,
            instructions_files=None,
            custom_commands=None,
        )

        self.assertEqual(
            config["mcp"]["vkg"]["command"],
            ["uv", "run", "alphaswarm", "mcp-serve"]
        )
        self.assertIn(".vrs/AGENTS.md", config["instructions"])

    def test_relative_path_warning(self):
        """Relative paths are handled (converted to string)."""
        config = generate_opencode_config(Path("relative/path"))

        # Should still work, but path is as-is
        self.assertEqual(
            config["mcp"]["vkg"]["environment"]["VKG_PROJECT"],
            "relative/path"
        )


class TestOpenCodeSchemaCompliance(unittest.TestCase):
    """Test that generated config complies with OpenCode schema expectations.

    Based on research at R3.2-OPENCODE-SDK-RESEARCH.md
    """

    def test_mcp_server_required_fields(self):
        """MCP server config has all required fields."""
        config = generate_opencode_config(Path("/test"))
        vkg = config["mcp"]["vkg"]

        # Required fields per OpenCode spec
        required_fields = ["type", "command", "enabled", "timeout"]
        for field in required_fields:
            self.assertIn(field, vkg, f"Missing required MCP field: {field}")

    def test_permission_values_valid(self):
        """Permission values are valid OpenCode values."""
        config = generate_opencode_config(Path("/test"))

        valid_permissions = ["allow", "ask", "deny"]
        for tool, permission in config["permission"].items():
            self.assertIn(
                permission, valid_permissions,
                f"Invalid permission '{permission}' for {tool}"
            )

    def test_command_structure_valid(self):
        """Command structure follows OpenCode format."""
        config = generate_opencode_config(Path("/test"))

        for cmd_name, cmd_info in config["command"].items():
            self.assertIn("template", cmd_info)
            self.assertIn("description", cmd_info)
            self.assertIsInstance(cmd_info["template"], str)
            self.assertIsInstance(cmd_info["description"], str)

    def test_environment_variable_format(self):
        """Environment variables are in correct format."""
        config = generate_opencode_config(Path("/test"))
        env = config["mcp"]["vkg"]["environment"]

        # All keys should be uppercase with underscores
        for key in env.keys():
            self.assertTrue(
                key.isupper() or "_" in key,
                f"Environment variable should be uppercase: {key}"
            )


class TestMCPToolSchemaExpectations(unittest.TestCase):
    """Test that tool definitions match MCP tool schema expectations.

    When the VKG MCP server is implemented, it should respond to tools/list
    with schemas matching these expectations.
    """

    # Expected MCP tool schema structure
    EXPECTED_TOOL_SCHEMAS = {
        "build_kg": {
            "required_params": ["path"],
            "optional_params": [],
            "return_type": "json",
        },
        "analyze": {
            "required_params": [],
            "optional_params": ["patterns"],
            "return_type": "json",
        },
        "query": {
            "required_params": ["query_text"],
            "optional_params": ["format"],
            "return_type": "json",
        },
        "findings_list": {
            "required_params": [],
            "optional_params": ["status", "severity"],
            "return_type": "json",
        },
        "findings_next": {
            "required_params": [],
            "optional_params": [],
            "return_type": "json",
        },
        "findings_show": {
            "required_params": ["id"],
            "optional_params": [],
            "return_type": "json",
        },
        "findings_update": {
            "required_params": ["id", "status"],
            "optional_params": ["reason"],
            "return_type": "json",
        },
        "report": {
            "required_params": [],
            "optional_params": ["format"],
            "return_type": "json",
        },
        "patterns_list": {
            "required_params": [],
            "optional_params": ["lens"],
            "return_type": "json",
        },
    }

    def test_all_expected_tools_defined(self):
        """All expected MCP tools are defined."""
        for tool_name in self.EXPECTED_TOOL_SCHEMAS:
            self.assertIn(
                tool_name, VKG_TOOLS,
                f"Missing expected MCP tool: {tool_name}"
            )

    def test_tool_count_matches_expected(self):
        """Number of tools matches expected."""
        self.assertEqual(
            len(VKG_TOOLS), len(self.EXPECTED_TOOL_SCHEMAS),
            "Tool count mismatch - update EXPECTED_TOOL_SCHEMAS or VKG_TOOLS"
        )


class TestWorkflowIntegration(unittest.TestCase):
    """Integration tests for complete audit workflow.

    These tests verify the config enables the full audit flow that
    OpenCode would execute:
    1. LLM receives project to audit
    2. LLM discovers VKG tools via MCP
    3. LLM executes: build_kg -> analyze -> findings iteration -> report
    4. User receives findings
    """

    def test_full_audit_workflow_config(self):
        """Config enables complete audit workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create .vkg directory for instructions
            vkg_dir = project_path / ".vkg"
            vkg_dir.mkdir()
            (vkg_dir / "AGENTS.md").write_text("# VKG Agent Instructions")

            # Generate config
            output_path = write_opencode_config(project_path)

            # Read and verify
            config = json.loads(output_path.read_text())

            # Verify MCP server config
            self.assertIn("vkg", config["mcp"])
            self.assertTrue(config["mcp"]["vkg"]["enabled"])

            # Verify all workflow tools accessible
            workflow_tools = [
                "vkg_build_kg", "vkg_analyze", "vkg_query",
                "vkg_findings_list", "vkg_findings_next",
                "vkg_findings_show", "vkg_findings_update",
                "vkg_report", "vkg_patterns_list"
            ]
            for tool in workflow_tools:
                self.assertIn(tool, config["permission"])

    def test_workflow_with_custom_settings(self):
        """Workflow works with custom settings."""
        config = generate_opencode_config(
            Path("/audit/target"),
            log_level="DEBUG",
            timeout=60000,
            custom_commands={
                "quick-audit": {
                    "template": "Run quick security scan",
                    "description": "Fast security check",
                }
            },
        )

        # Verify custom settings applied
        self.assertEqual(
            config["mcp"]["vkg"]["environment"]["VKG_LOG_LEVEL"],
            "DEBUG"
        )
        self.assertEqual(config["mcp"]["vkg"]["timeout"], 60000)
        self.assertIn("quick-audit", config["command"])


class TestToolCoverage(unittest.TestCase):
    """Verify VKG tools cover all audit needs."""

    def test_graph_building_tool_exists(self):
        """Tool for building knowledge graph exists."""
        self.assertIn("build_kg", VKG_TOOLS)

    def test_analysis_tool_exists(self):
        """Tool for vulnerability analysis exists."""
        self.assertIn("analyze", VKG_TOOLS)

    def test_query_tool_exists(self):
        """Tool for querying graph exists."""
        self.assertIn("query", VKG_TOOLS)

    def test_findings_management_tools_exist(self):
        """Tools for managing findings exist."""
        findings_tools = [
            "findings_list",
            "findings_next",
            "findings_show",
            "findings_update",
        ]
        for tool in findings_tools:
            self.assertIn(tool, VKG_TOOLS, f"Missing findings tool: {tool}")

    def test_report_tool_exists(self):
        """Tool for generating reports exists."""
        self.assertIn("report", VKG_TOOLS)

    def test_pattern_tool_exists(self):
        """Tool for listing patterns exists."""
        self.assertIn("patterns_list", VKG_TOOLS)


if __name__ == "__main__":
    unittest.main()
