"""Claude Code CLI Adapter for Local Execution.

Provides local CLI-based execution using the claude command-line tool.
Supports worktree isolation for parallel agent execution with git-backed
state management.

Key Features:
- Local claude CLI execution
- Worktree isolation for parallel agents
- System prompt injection from agent configs
- GRAPH_FIRST enforcement via CLAUDE.md
- Environment variable trace propagation

Design:
- Executes claude CLI as subprocess
- Creates worktrees for isolated execution
- Writes bead context to worktree
- Parses CLI output as AgentResponse
- Cleans up worktrees after execution

Usage:
    from alphaswarm_sol.adapters import ClaudeCodeAdapter, ClaudeCodeConfig

    config = ClaudeCodeConfig(
        claude_path="claude",
        workdir=Path.cwd(),
        worktree_enabled=True,
    )

    adapter = ClaudeCodeAdapter(config)

    # Execute agent locally
    response = await adapter.execute_agent(agent_config, messages)

Phase: 07.1.4-05 Beads/Gas Town and Claude Code Adapters
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentResponse
from alphaswarm_sol.agents.runtime.claude_code import (
    ClaudeCodeRuntime,
    ClaudeCodeConfig as RuntimeClaudeCodeConfig,
)
from alphaswarm_sol.beads.schema import VulnerabilityBead

from .base import (
    AdapterConfig,
    HandoffContext,
    HandoffResult,
    OrchestratorAdapter,
    TraceContext,
)
from .capability import AdapterCapability, ADAPTER_CAPABILITIES

# Optional import for workspace manager (backward compatible with worktree)
try:
    from alphaswarm_sol.orchestration.workspace import WorkspaceManager as WorktreeManager

    HAS_WORKTREE = True
except ImportError:
    HAS_WORKTREE = False
    WorktreeManager = None  # type: ignore


@dataclass
class ClaudeCodeConfig(AdapterConfig):
    """Configuration for Claude Code CLI adapter.

    Extends AdapterConfig with CLI-specific settings.

    Attributes:
        claude_path: Path to claude CLI executable (default "claude")
        workdir: Working directory for execution
        worktree_enabled: Use worktrees for isolation (default True)
        timeout_seconds: Execution timeout in seconds (default 600)
        model: Claude model to use (default "claude-opus-4")
    """

    claude_path: str = "claude"
    workdir: Path = field(default_factory=Path.cwd)
    worktree_enabled: bool = True
    timeout_seconds: int = 600
    model: str = "claude-opus-4"

    def __init__(
        self,
        claude_path: str = "claude",
        workdir: Optional[Path] = None,
        worktree_enabled: bool = True,
        timeout_seconds: int = 600,
        model: str = "claude-opus-4",
        **kwargs,
    ):
        """Initialize config with CLI-specific settings."""
        # Claude Code enforces GRAPH_FIRST via CLAUDE.md
        capabilities = {
            AdapterCapability.TOOL_EXECUTION,
            AdapterCapability.GRAPH_FIRST,
        }

        super().__init__(
            name="claude-code",
            capabilities=capabilities,
            evidence_mode="bead",
            trace_propagation="context",  # Environment variables
            **kwargs,
        )

        self.claude_path = claude_path
        self.workdir = workdir or Path.cwd()
        self.worktree_enabled = worktree_enabled
        self.timeout_seconds = timeout_seconds
        self.model = model


class ClaudeCodeAdapter(OrchestratorAdapter):
    """Claude Code CLI adapter for local execution.

    Executes agents using the claude CLI with worktree isolation.
    """

    def __init__(self, config: ClaudeCodeConfig):
        """Initialize adapter with CLI configuration.

        Args:
            config: Claude Code configuration

        Raises:
            ValueError: If claude CLI is not available
        """
        super().__init__(config)
        self.config = config

        # Verify claude CLI is available
        if not self._check_claude_available():
            raise ValueError(
                f"Claude CLI not found at '{config.claude_path}'. "
                "Install from: https://www.anthropic.com/claude-code"
            )

        # Initialize Claude Code CLI runtime for agent execution
        runtime_config = RuntimeClaudeCodeConfig(
            timeout_seconds=config.timeout_seconds,
            working_dir=config.workdir,
        )
        self._runtime = ClaudeCodeRuntime(config=runtime_config)

        # Initialize worktree manager if enabled
        self.worktree_manager = None
        if config.worktree_enabled and HAS_WORKTREE:
            self.worktree_manager = WorktreeManager(root=config.workdir / ".vrs" / "worktrees")

    def _check_claude_available(self) -> bool:
        """Check if claude CLI is available.

        Returns:
            True if claude command exists
        """
        try:
            result = subprocess.run(
                [self.config.claude_path, "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    async def execute_agent(
        self, config: AgentConfig, messages: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Execute agent via Claude Code CLI runtime.

        Delegates to ClaudeCodeRuntime for actual CLI execution, which provides:
        - Role-based model selection (Opus for ATTACKER/VERIFIER, Sonnet for others)
        - Session management with --resume flag
        - Non-interactive mode with --print flag
        - Subscription-based cost tracking (cost_usd = 0.0)

        Args:
            config: Agent configuration with system prompt
            messages: Conversation messages

        Returns:
            AgentResponse with CLI output
        """
        # Delegate to ClaudeCodeRuntime for execution
        response = await self._runtime.execute(config, messages)

        # Add adapter-specific metadata
        response.metadata.update({
            "adapter": "claude-code",
            "worktree_enabled": self.config.worktree_enabled,
        })

        return response

    async def handoff(self, ctx: HandoffContext) -> HandoffResult:
        """Hand off execution to target agent.

        Writes bead context to worktree, executes target agent,
        reads updated bead, and cleans up.

        Args:
            ctx: Handoff context with source/target agents

        Returns:
            HandoffResult with target response
        """
        if not ctx.bead_id:
            return HandoffResult(
                success=False,
                errors=["No bead_id provided for handoff"],
            )

        # Create worktree if enabled
        if self.config.worktree_enabled and self.worktree_manager:
            worktree_path = self.worktree_manager.allocate(
                pool_id="handoff",
                agent_id=ctx.target_agent,
            )

            try:
                # Write bead context to worktree
                bead_file = worktree_path / ".vrs" / "bead_context.yaml"
                bead_file.parent.mkdir(parents=True, exist_ok=True)

                with open(bead_file, "w") as f:
                    yaml.dump(ctx.evidence_snapshot, f)

                # Execute target agent via runtime
                target_config = AgentConfig(
                    role=ctx.target_agent,
                    model="claude-sonnet-4",
                    prompt_template="",
                    tools=[],
                    metadata={"handoff_context": ctx.to_dict()},
                )
                target_response = await self._runtime.execute(target_config, [])

                return HandoffResult(
                    success=True,
                    target_response=target_response,
                    evidence_preserved=True,
                    trace_continued=True,
                    metadata={"worktree": str(worktree_path)},
                )

            finally:
                # Clean up worktree
                self.worktree_manager.release(
                    pool_id="handoff",
                    agent_id=ctx.target_agent,
                )
        else:
            # Execute without worktree isolation via runtime
            target_config = AgentConfig(
                role=ctx.target_agent,
                model="claude-sonnet-4",
                prompt_template="",
                tools=[],
                metadata={"handoff_context": ctx.to_dict()},
            )
            target_response = await self._runtime.execute(target_config, [])

            return HandoffResult(
                success=True,
                target_response=target_response,
                evidence_preserved=True,
                trace_continued=True,
            )

    async def spawn_with_trace(
        self, config: AgentConfig, task: str, trace: TraceContext
    ) -> AgentResponse:
        """Spawn agent with trace propagation via environment variables.

        Args:
            config: Agent configuration
            task: Task description
            trace: Trace context to propagate

        Returns:
            AgentResponse with trace preserved
        """
        # Set trace as environment variables
        env = os.environ.copy()
        env.update(
            {
                "VRS_TRACE_ID": trace.trace_id,
                "VRS_SPAN_ID": trace.span_id,
                "VRS_OPERATION": trace.operation,
            }
        )

        # Build command
        cmd = self._build_claude_command(config, task)

        # Execute with trace environment
        output = await self._execute_command(cmd, cwd=self.config.workdir, env=env)

        # Parse output and add trace metadata
        response = self._parse_claude_output(output)
        response.metadata["trace"] = trace.to_dict()

        return response

    def get_capabilities(self) -> Set[AdapterCapability]:
        """Get adapter capabilities.

        Returns:
            Set of capabilities (TOOL_EXECUTION, GRAPH_FIRST)
        """
        return self.config.capabilities

    def preserve_evidence(
        self, bead: VulnerabilityBead, ctx: HandoffContext
    ) -> VulnerabilityBead:
        """Preserve evidence by storing in worktree.

        Args:
            bead: VulnerabilityBead to preserve
            ctx: Handoff context

        Returns:
            VulnerabilityBead with evidence snapshot
        """
        # Call parent implementation for snapshot
        bead = super().preserve_evidence(bead, ctx)

        # Store bead in worktree if enabled
        if self.config.worktree_enabled:
            # Evidence is written to worktree during handoff
            pass

        return bead

    def export_trace(self, trace: TraceContext) -> Dict[str, Any]:
        """Export trace as environment variables.

        Args:
            trace: Trace context to export

        Returns:
            Dictionary with environment variable mappings
        """
        return {
            "VRS_TRACE_ID": trace.trace_id,
            "VRS_SPAN_ID": trace.span_id,
            "VRS_PARENT_SPAN_ID": trace.parent_span_id or "",
            "VRS_OPERATION": trace.operation,
            "VRS_TIMESTAMP": trace.timestamp,
        }

    def import_trace(self, data: Dict[str, Any]) -> TraceContext:
        """Import trace from environment variables.

        Args:
            data: Dictionary with environment variable values

        Returns:
            TraceContext reconstructed from environment
        """
        return TraceContext(
            trace_id=data.get("VRS_TRACE_ID", ""),
            span_id=data.get("VRS_SPAN_ID", ""),
            parent_span_id=data.get("VRS_PARENT_SPAN_ID") or None,
            operation=data.get("VRS_OPERATION", "unknown"),
            timestamp=data.get("VRS_TIMESTAMP", ""),
        )

    # CLI helper methods

    def _build_claude_command(self, config: AgentConfig, task: str) -> List[str]:
        """Build claude CLI command.

        Args:
            config: Agent configuration
            task: Task description

        Returns:
            List of command arguments
        """
        cmd = [self.config.claude_path]

        # Add model flag
        cmd.extend(["--model", self.config.model])

        # Add system prompt if provided
        if config.system_prompt:
            cmd.extend(["--system", config.system_prompt])

        # Add task
        cmd.append(task)

        return cmd

    def _build_task_from_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Build task from message list.

        Args:
            messages: Conversation messages

        Returns:
            Task string for CLI
        """
        # Extract last user message as task
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")

        return "Execute investigation"

    async def _execute_command(
        self,
        cmd: List[str],
        cwd: Path,
        env: Optional[Dict[str, str]] = None,
    ) -> str:
        """Execute command as subprocess.

        Args:
            cmd: Command and arguments
            cwd: Working directory
            env: Optional environment variables

        Returns:
            Command output (stdout)

        Raises:
            RuntimeError: If command fails
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                env=env or os.environ.copy(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout_seconds,
            )

            if process.returncode != 0:
                raise RuntimeError(
                    f"Command failed with exit code {process.returncode}: "
                    f"{stderr.decode()}"
                )

            return stdout.decode()

        except asyncio.TimeoutError:
            raise RuntimeError(f"Command timed out after {self.config.timeout_seconds}s")
        except Exception as e:
            raise RuntimeError(f"Command execution failed: {e}")

    def _parse_claude_output(self, output: str) -> AgentResponse:
        """Parse claude CLI output as AgentResponse.

        Args:
            output: CLI stdout

        Returns:
            AgentResponse with parsed content
        """
        # Try to parse as JSON first (structured output)
        try:
            data = json.loads(output)
            return AgentResponse(
                content=data.get("content", output),
                metadata=data.get("metadata", {}),
            )
        except json.JSONDecodeError:
            # Fall back to raw output
            return AgentResponse(
                content=output,
                metadata={"raw_output": True},
            )
