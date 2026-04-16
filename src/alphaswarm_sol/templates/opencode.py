"""OpenCode configuration generator for VKG integration.

This module generates opencode.json configuration files that enable VKG
to be discovered and used as an MCP (Model Context Protocol) server by
OpenCode, an open-source AI coding agent.

OpenCode discovers VKG tools via the MCP server, which exposes:
- build_kg: Build knowledge graph from Solidity contracts
- analyze: Run vulnerability analysis on built graph
- query: Query the knowledge graph using NL or VQL2
- findings_list/next/show/update: Manage findings workflow
- report: Generate audit reports
- patterns_list: List available vulnerability patterns

Reference: https://opencode.ai/docs/mcp-servers/
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Tool definitions with clear descriptions for LLM discovery
VKG_TOOLS = {
    "build_kg": {
        "description": "Build knowledge graph from Solidity contracts. "
        "Extracts 50+ security properties per function.",
        "permission": "allow",
    },
    "analyze": {
        "description": "Run vulnerability analysis using pattern matching. "
        "Detects reentrancy, access control, oracle, MEV, and other issues.",
        "permission": "allow",
    },
    "query": {
        "description": "Query the knowledge graph using natural language or VQL2. "
        "Find functions by properties, operations, or vulnerability patterns.",
        "permission": "allow",
    },
    "findings_list": {
        "description": "List all detected findings with severity and status filters.",
        "permission": "allow",
    },
    "findings_next": {
        "description": "Get the next highest-priority finding to investigate. "
        "Priority is based on severity, confidence, and age.",
        "permission": "allow",
    },
    "findings_show": {
        "description": "Show full details for a specific finding including "
        "evidence, code snippets, and verification steps.",
        "permission": "allow",
    },
    "findings_update": {
        "description": "Update the status of a finding after investigation "
        "(investigating, confirmed, rejected, fixed).",
        "permission": "ask",  # Requires confirmation since it modifies state
    },
    "report": {
        "description": "Generate audit report in SARIF, JSON, or Markdown format.",
        "permission": "allow",
    },
    "patterns_list": {
        "description": "List available vulnerability patterns by lens category.",
        "permission": "allow",
    },
}


@dataclass
class OpenCodeConfig:
    """OpenCode configuration for VKG integration.

    Attributes:
        project_path: Path to the project root
        vkg_command: Command to start VKG MCP server
        log_level: VKG log level (DEBUG, INFO, WARNING, ERROR)
        timeout: MCP server startup timeout in milliseconds
        enabled: Whether VKG integration is enabled
        additional_mcp: Additional MCP servers to include
        instructions_files: Files to include in OpenCode instructions
        custom_commands: Custom slash commands for OpenCode
    """

    project_path: Path
    vkg_command: list[str] = field(
        default_factory=lambda: ["uv", "run", "alphaswarm", "mcp-serve"]
    )
    log_level: str = "INFO"
    timeout: int = 30000
    enabled: bool = True
    additional_mcp: dict[str, Any] = field(default_factory=dict)
    instructions_files: list[str] = field(
        default_factory=lambda: [".vrs/AGENTS.md"]
    )
    custom_commands: dict[str, dict[str, str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Generate the full opencode.json configuration dictionary."""
        config: dict[str, Any] = {
            "$schema": "https://opencode.ai/config.json",
            # MCP Server Configuration
            "mcp": {
                "vkg": {
                    "type": "local",
                    "command": self.vkg_command,
                    "environment": {
                        "VKG_PROJECT": str(self.project_path),
                        "VKG_LOG_LEVEL": self.log_level,
                    },
                    "enabled": self.enabled,
                    "timeout": self.timeout,
                }
            },
            # Enable VKG tools (wildcard)
            "tools": {"vkg_*": True},
            # Tool permissions
            "permission": {
                f"vkg_{name}": info["permission"]
                for name, info in VKG_TOOLS.items()
            },
        }

        # Add instructions files if any exist
        if self.instructions_files:
            config["instructions"] = self.instructions_files

        # Add custom commands
        default_commands = {
            "audit": {
                "template": "Run a complete security audit on this Solidity project",
                "description": "Start VKG vulnerability audit",
            },
            "vkg-analyze": {
                "template": "Analyze the current contracts for vulnerabilities using VKG",
                "description": "Quick VKG analysis",
            },
        }
        all_commands = {**default_commands, **self.custom_commands}
        if all_commands:
            config["command"] = all_commands

        # Add additional MCP servers
        if self.additional_mcp:
            config["mcp"].update(self.additional_mcp)

        return config

    def to_json(self, indent: int = 2) -> str:
        """Serialize configuration to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


def generate_opencode_config(
    project_path: Path | str,
    vkg_command: list[str] | None = None,
    log_level: str = "INFO",
    timeout: int = 30000,
    enabled: bool = True,
    additional_mcp: dict[str, Any] | None = None,
    instructions_files: list[str] | None = None,
    custom_commands: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Generate opencode.json configuration for VKG integration.

    This function creates a configuration dictionary that can be written
    to opencode.json in a project root. The configuration:

    1. Points to VKG as an MCP server (stdio transport)
    2. Exposes key VKG commands: build, analyze, query, findings, report
    3. Includes clear tool descriptions for LLM discovery
    4. Sets appropriate permissions for each tool

    Args:
        project_path: Path to the project root
        vkg_command: Custom command for VKG MCP server.
            Defaults to ["uv", "run", "alphaswarm", "mcp-serve"]
        log_level: VKG log level (DEBUG, INFO, WARNING, ERROR)
        timeout: MCP server startup timeout in milliseconds
        enabled: Whether VKG integration is enabled
        additional_mcp: Additional MCP servers to include
        instructions_files: Files to include in OpenCode instructions.
            Defaults to [".vrs/AGENTS.md"]
        custom_commands: Custom slash commands for OpenCode

    Returns:
        Complete opencode.json configuration dictionary

    Example:
        >>> config = generate_opencode_config(Path("/path/to/project"))
        >>> config["mcp"]["vkg"]["type"]
        'local'
        >>> config["permission"]["vkg_build_kg"]
        'allow'
    """
    if isinstance(project_path, str):
        project_path = Path(project_path)

    config_obj = OpenCodeConfig(
        project_path=project_path,
        vkg_command=vkg_command or ["uv", "run", "alphaswarm", "mcp-serve"],
        log_level=log_level,
        timeout=timeout,
        enabled=enabled,
        additional_mcp=additional_mcp or {},
        instructions_files=instructions_files or [".vrs/AGENTS.md"],
        custom_commands=custom_commands or {},
    )

    return config_obj.to_dict()


def write_opencode_config(
    project_path: Path | str,
    output_path: Path | str | None = None,
    overwrite: bool = False,
    **kwargs: Any,
) -> Path:
    """Write opencode.json to project.

    Args:
        project_path: Path to the project root
        output_path: Custom output path. Defaults to project_path/opencode.json
        overwrite: Whether to overwrite existing config file
        **kwargs: Additional arguments for generate_opencode_config

    Returns:
        Path to written config file

    Raises:
        FileExistsError: If output_path exists and overwrite is False
    """
    if isinstance(project_path, str):
        project_path = Path(project_path)

    if output_path is None:
        output_path = project_path / "opencode.json"
    elif isinstance(output_path, str):
        output_path = Path(output_path)

    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Config file already exists: {output_path}. "
            "Use overwrite=True to replace."
        )

    config = generate_opencode_config(project_path, **kwargs)
    output_path.write_text(json.dumps(config, indent=2) + "\n")

    return output_path


def get_tool_descriptions() -> dict[str, str]:
    """Get tool descriptions for documentation or display.

    Returns:
        Dictionary mapping tool names to descriptions
    """
    return {name: info["description"] for name, info in VKG_TOOLS.items()}
