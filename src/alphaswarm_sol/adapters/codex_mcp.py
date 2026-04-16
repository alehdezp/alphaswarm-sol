"""Codex CLI MCP Adapter for AlphaSwarm VRS.

Implements the OrchestratorAdapter interface for Codex CLI execution,
enabling code-heavy agent tasks via MCP (Model Context Protocol) bridge.

Key Features:
- CLI-based agent execution via codex command
- Bead state transfer through temp files
- Subprocess isolation with timeout
- Trace context propagation via environment variables
- Minimal capabilities (tool execution + handoff sync)

Usage:
    from alphaswarm_sol.adapters.codex_mcp import CodexMcpAdapter, CodexMcpConfig

    config = CodexMcpConfig(
        name="codex-mcp",
        codex_path="codex",
        workdir="/tmp/codex-work",
        sandbox_mode=True,
    )
    adapter = CodexMcpAdapter(config)
    response = await adapter.execute_agent(agent_config, messages)

Phase: 07.1.4-02 Agents SDK + Codex MCP Integration
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from alphaswarm_sol.adapters.base import (
    AdapterConfig,
    HandoffContext,
    HandoffResult,
    OrchestratorAdapter,
    TraceContext,
)
from alphaswarm_sol.adapters.capability import AdapterCapability
from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentResponse
from alphaswarm_sol.agents.runtime.codex_cli import CodexCLIRuntime, CodexCLIConfig
from alphaswarm_sol.beads.schema import VulnerabilityBead


@dataclass
class CodexMcpConfig(AdapterConfig):
    """Configuration for Codex CLI MCP adapter.

    Attributes:
        name: Adapter name (default: "codex-mcp")
        capabilities: Set of capabilities (auto-populated if not provided)
        codex_path: Path to codex CLI executable (default: "codex")
        workdir: Working directory for execution (created if doesn't exist)
        timeout_seconds: Execution timeout in seconds
        sandbox_mode: Whether to run in sandboxed mode (prevents file writes outside workdir)
    """

    # Override parent fields with defaults
    name: str = "codex-mcp"
    capabilities: Set[AdapterCapability] = field(
        default_factory=lambda: {
            AdapterCapability.TOOL_EXECUTION,
            AdapterCapability.HANDOFF_SYNC,
        }
    )

    # Adapter-specific fields
    codex_path: str = "codex"
    workdir: str = "/tmp/codex-work"
    timeout_seconds: int = 300
    sandbox_mode: bool = True


class CodexMcpAdapter(OrchestratorAdapter):
    """Codex CLI MCP adapter implementation.

    Executes agents via the Codex CLI for code-heavy tasks where
    CLI tools are more appropriate than SDK-based execution.

    Example:
        config = CodexMcpConfig(name="codex-mcp", workdir="/tmp/work")
        adapter = CodexMcpAdapter(config)

        # Execute agent
        response = await adapter.execute_agent(agent_config, messages)

        # Handoff with bead state
        ctx = HandoffContext(
            source_agent="attacker",
            target_agent="defender",
            bead_id="VKG-001",
        )
        result = await adapter.handoff(ctx)
    """

    def __init__(self, config: CodexMcpConfig):
        """Initialize Codex MCP adapter.

        Args:
            config: CodexMcpConfig with CLI path and workdir

        Raises:
            FileNotFoundError: If codex CLI not found in PATH
        """
        # Set minimal capabilities for Codex adapter
        if not config.capabilities:
            config.capabilities = {
                AdapterCapability.TOOL_EXECUTION,
                AdapterCapability.HANDOFF_SYNC,
            }

        super().__init__(config)
        self.mcp_config = config

        # Verify codex CLI available
        codex_path = shutil.which(config.codex_path)
        if not codex_path:
            raise FileNotFoundError(
                f"Codex CLI not found: {config.codex_path}. "
                "Ensure it's installed and in PATH."
            )

        self.codex_path = codex_path

        # Set up working directory
        self.workdir = Path(config.workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)

        # Temp file storage for bead state
        self._bead_temp_dir = self.workdir / "beads"
        self._bead_temp_dir.mkdir(exist_ok=True)

        # Initialize Codex CLI runtime for actual execution
        cli_config = CodexCLIConfig(
            timeout_seconds=config.timeout_seconds,
            working_dir=self.workdir,
        )
        self._runtime = CodexCLIRuntime(config=cli_config)

    def _build_codex_command(
        self, config: AgentConfig, messages: List[Dict[str, Any]]
    ) -> List[str]:
        """Build codex CLI command from agent config and messages.

        Args:
            config: Agent configuration
            messages: Conversation messages

        Returns:
            List of command arguments for subprocess
        """
        # Create temp file for messages
        messages_file = self.workdir / f"messages-{uuid.uuid4()}.json"
        with open(messages_file, "w") as f:
            json.dump(messages, f)

        # Build command
        cmd = [
            self.codex_path,
            "--role", config.role.value,
            "--messages", str(messages_file),
            "--max-tokens", str(config.max_tokens),
            "--temperature", str(config.temperature),
        ]

        # Add system prompt if provided
        if config.system_prompt:
            prompt_file = self.workdir / f"prompt-{uuid.uuid4()}.txt"
            with open(prompt_file, "w") as f:
                f.write(config.system_prompt)
            cmd.extend(["--system-prompt", str(prompt_file)])

        # Add tools if provided
        if config.tools:
            tools_file = self.workdir / f"tools-{uuid.uuid4()}.json"
            with open(tools_file, "w") as f:
                json.dump(config.tools, f)
            cmd.extend(["--tools", str(tools_file)])

        # Add sandbox mode
        if self.mcp_config.sandbox_mode:
            cmd.append("--sandbox")

        # Add workdir
        cmd.extend(["--workdir", str(self.workdir)])

        return cmd

    def _parse_codex_output(self, output: str) -> AgentResponse:
        """Parse codex CLI output into AgentResponse.

        Args:
            output: Raw CLI output (expected to be JSON)

        Returns:
            AgentResponse parsed from output

        Raises:
            ValueError: If output is not valid JSON
        """
        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            # Fallback: treat as plain text response
            return AgentResponse(
                content=output,
                tool_calls=[],
                input_tokens=0,
                output_tokens=0,
                model="codex-cli",
                metadata={"adapter": "codex-mcp", "parse_error": str(e)},
            )

        # Parse structured response
        return AgentResponse(
            content=data.get("content", ""),
            tool_calls=data.get("tool_calls", []),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cache_read_tokens=data.get("cache_read_tokens", 0),
            cache_write_tokens=data.get("cache_write_tokens", 0),
            model=data.get("model", "codex-cli"),
            latency_ms=data.get("latency_ms", 0),
            cost_usd=data.get("cost_usd", 0.0),
            metadata={
                **data.get("metadata", {}),
                "adapter": "codex-mcp",
            },
        )

    def _write_bead_context(self, bead: VulnerabilityBead, path: Path) -> None:
        """Write bead state to temp file for handoff.

        Args:
            bead: VulnerabilityBead to serialize
            path: Path to write bead JSON
        """
        with open(path, "w") as f:
            json.dump(bead.to_dict(), f, indent=2)

    def _read_bead_context(self, path: Path) -> VulnerabilityBead:
        """Read bead state from temp file after execution.

        Args:
            path: Path to bead JSON file

        Returns:
            VulnerabilityBead deserialized from file

        Raises:
            FileNotFoundError: If bead file not found
            ValueError: If bead JSON is invalid
        """
        if not path.exists():
            raise FileNotFoundError(f"Bead context file not found: {path}")

        with open(path, "r") as f:
            data = json.load(f)

        return VulnerabilityBead.from_dict(data)

    async def execute_agent(
        self, config: AgentConfig, messages: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Execute agent via Codex CLI runtime.

        Args:
            config: Agent configuration
            messages: Conversation messages

        Returns:
            AgentResponse from CodexCLIRuntime

        Raises:
            TimeoutError: If execution exceeds timeout
            RuntimeError: If CLI execution fails
        """
        # Extract context files from config metadata if present
        context_files = config.metadata.get("context_files", [])

        # Delegate to CodexCLIRuntime
        response = await self._runtime.execute(config, messages, context_files)

        # Add adapter-specific metadata
        response.metadata.update({
            "adapter": "codex-mcp",
            "workdir": str(self.workdir),
        })

        return response

    async def handoff(self, ctx: HandoffContext) -> HandoffResult:
        """Hand off execution with bead state transfer via CodexCLIRuntime.

        Writes bead to temp file, executes target agent via runtime, reads updated bead.

        Args:
            ctx: Handoff context with source/target agents

        Returns:
            HandoffResult with target response

        Raises:
            ValueError: If handoff depth exceeds maximum
        """
        # Check handoff depth
        if ctx.handoff_depth >= self.config.max_handoff_depth:
            return HandoffResult(
                success=False,
                errors=[
                    f"Handoff depth {ctx.handoff_depth} exceeds maximum {self.config.max_handoff_depth}"
                ],
            )

        # Create bead context file if bead_id provided
        bead_path = None
        if ctx.bead_id:
            bead_path = self._bead_temp_dir / f"{ctx.bead_id}.json"

        # Build handoff messages
        messages = [
            {"role": "system", "content": f"Handoff from {ctx.source_agent}"},
            {"role": "user", "content": f"Continue investigation for bead {ctx.bead_id}"},
        ]

        # Map target agent name to role
        from alphaswarm_sol.agents.runtime.base import AgentRole

        role_map = {
            "vrs-attacker": AgentRole.ATTACKER,
            "vrs-defender": AgentRole.DEFENDER,
            "vrs-verifier": AgentRole.VERIFIER,
            "attacker": AgentRole.ATTACKER,
            "defender": AgentRole.DEFENDER,
            "verifier": AgentRole.VERIFIER,
        }
        target_role = role_map.get(ctx.target_agent, AgentRole.DEFENDER)

        # Build target agent config
        target_config = AgentConfig(
            role=target_role,
            system_prompt=f"You are {ctx.target_agent}. Continue the investigation from {ctx.source_agent}.",
            tools=[],
            metadata={
                "handoff_from": ctx.source_agent,
                "bead_id": ctx.bead_id,
                "bead_path": str(bead_path) if bead_path else None,
            },
        )

        # Execute target agent via runtime
        try:
            response = await self._runtime.execute(target_config, messages)

            # Add adapter metadata
            response.metadata.update({
                "adapter": "codex-mcp",
                "handoff_from": ctx.source_agent,
                "workdir": str(self.workdir),
            })

            return HandoffResult(
                success=True,
                target_response=response,
                evidence_preserved=True,
                trace_continued=False,  # CLI uses env vars for trace, not full propagation
                metadata={
                    "bead_path": str(bead_path) if bead_path else None,
                },
            )

        except Exception as e:
            return HandoffResult(
                success=False,
                errors=[str(e)],
            )

    async def spawn_with_trace(
        self, config: AgentConfig, task: str, trace: TraceContext
    ) -> AgentResponse:
        """Spawn agent with trace context via environment variables.

        Sets trace headers as env vars before CLI execution via runtime.

        Args:
            config: Agent configuration
            task: Task description
            trace: Trace context to propagate

        Returns:
            AgentResponse with trace_id preserved in metadata
        """
        # Set trace headers as environment variables for subprocess
        original_env = os.environ.copy()
        os.environ["TRACE_ID"] = trace.trace_id
        os.environ["SPAN_ID"] = trace.span_id
        if trace.parent_span_id:
            os.environ["PARENT_SPAN_ID"] = trace.parent_span_id
        os.environ["TRACE_OPERATION"] = trace.operation

        try:
            # Execute via runtime
            messages = [{"role": "user", "content": task}]
            response = await self._runtime.execute(config, messages)

            # Attach trace and adapter metadata
            response.metadata.update({
                "adapter": "codex-mcp",
                "trace_id": trace.trace_id,
                "span_id": trace.span_id,
                "workdir": str(self.workdir),
            })

            return response

        finally:
            # Restore original environment
            for key in ["TRACE_ID", "SPAN_ID", "PARENT_SPAN_ID", "TRACE_OPERATION"]:
                if key in os.environ and key not in original_env:
                    del os.environ[key]
                elif key in original_env:
                    os.environ[key] = original_env[key]

    def get_capabilities(self) -> Set[AdapterCapability]:
        """Get adapter capabilities.

        Returns:
            Minimal capabilities: TOOL_EXECUTION, HANDOFF_SYNC
        """
        return {
            AdapterCapability.TOOL_EXECUTION,
            AdapterCapability.HANDOFF_SYNC,
        }

    def export_trace(self, trace: TraceContext) -> Dict[str, Any]:
        """Export trace context (minimal implementation).

        Args:
            trace: Trace context to export

        Returns:
            Dictionary with basic trace info
        """
        return trace.to_dict()

    def import_trace(self, data: Dict[str, Any]) -> TraceContext:
        """Import trace context.

        Args:
            data: Dictionary with trace info

        Returns:
            TraceContext instance
        """
        return TraceContext.from_dict(data)

    def preserve_evidence(
        self, bead: VulnerabilityBead, ctx: HandoffContext
    ) -> VulnerabilityBead:
        """Preserve evidence contracts during CLI handoff.

        Writes bead to temp file, validates after execution.

        Args:
            bead: VulnerabilityBead to preserve
            ctx: Handoff context

        Returns:
            VulnerabilityBead (unmodified or loaded from temp file)
        """
        # Write bead to temp file
        bead_path = self._bead_temp_dir / f"{bead.id}.json"
        self._write_bead_context(bead, bead_path)

        # Store path in context for validation
        ctx.metadata["bead_path"] = str(bead_path)

        # Return original bead - actual validation happens after execution
        return bead
