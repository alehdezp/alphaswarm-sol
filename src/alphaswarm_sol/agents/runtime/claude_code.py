"""Claude Code CLI Runtime Implementation.

This module provides ClaudeCodeRuntime - the runtime for subscription-based
orchestration and critical analysis via Claude Code CLI.

Per 05.3-CONTEXT.md:
- Subscription-based ($20-100/month) for quality-critical tasks
- Claude Code CLI uses --print for non-interactive mode
- Session management via --resume flag
- Role-based model selection (Opus for ATTACKER/VERIFIER, Sonnet for others)

Usage:
    from alphaswarm_sol.agents.runtime.claude_code import ClaudeCodeRuntime, ClaudeCodeConfig

    config = ClaudeCodeConfig()
    runtime = ClaudeCodeRuntime(config)

    response = await runtime.execute(
        AgentConfig(role=AgentRole.ATTACKER, system_prompt="..."),
        messages=[{"role": "user", "content": "Construct exploit..."}],
    )
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import AgentConfig, AgentResponse, AgentRole, AgentRuntime, UsageTracker

logger = logging.getLogger(__name__)


# Session directory default location
DEFAULT_SESSION_DIR = Path.home() / ".claude-code-sessions"


@dataclass
class ClaudeCodeConfig:
    """Configuration for Claude Code runtime.

    Attributes:
        model: Default model for general roles (sonnet)
        opus_model: Model for critical roles (ATTACKER, VERIFIER)
        timeout_seconds: Timeout for subprocess calls (longer for complex analysis)
        max_tokens: Maximum tokens for response
        session_dir: Directory for session persistence
        working_dir: Working directory for subprocess
        max_retries: Maximum retry attempts
        print_mode: Use --print for non-interactive mode (default True)
    """
    model: str = "claude-sonnet-4-20250514"
    opus_model: str = "claude-opus-4-20250514"
    timeout_seconds: int = 300
    max_tokens: int = 8192
    session_dir: Optional[Path] = None
    working_dir: Optional[Path] = None
    max_retries: int = 2
    print_mode: bool = True

    def __post_init__(self):
        """Initialize session directory if not set."""
        if self.session_dir is None:
            self.session_dir = DEFAULT_SESSION_DIR


# Role to model mapping per 05.2-CONTEXT.md
# ATTACKER, VERIFIER -> Opus (deep reasoning, accuracy)
# DEFENDER, TEST_BUILDER, SUPERVISOR, INTEGRATOR -> Sonnet (fast)
CRITICAL_ROLES = {AgentRole.ATTACKER, AgentRole.VERIFIER}


class ClaudeCodeRuntime(AgentRuntime):
    """Claude Code CLI runtime for subscription-based orchestration.

    Executes agents via Claude Code CLI subprocess calls, providing:
    - Role-based model selection (Opus for critical roles)
    - Session management with --resume flag
    - Non-interactive mode with --print flag
    - Cost tracking as subscription-based (cost_usd = 0.0)

    Per 05.3-CONTEXT.md:
    - Used for critical analysis where quality is paramount
    - ATTACKER: deep reasoning for exploit construction
    - VERIFIER: accuracy for cross-checking
    - Others: fast execution with Sonnet
    """

    def __init__(
        self,
        config: Optional[ClaudeCodeConfig] = None,
        working_dir: Optional[Path] = None,
    ):
        """Initialize Claude Code runtime.

        Args:
            config: Runtime configuration
            working_dir: Working directory (overrides config)
        """
        self.config = config or ClaudeCodeConfig()
        self.working_dir = working_dir or self.config.working_dir or Path.cwd()
        self._usage_tracker = UsageTracker()

        # Ensure session directory exists
        if self.config.session_dir:
            self.config.session_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_file(self, session_id: str) -> Path:
        """Get path to session file for persistence.

        Args:
            session_id: Unique session identifier

        Returns:
            Path to session file
        """
        # Sanitize session ID for filesystem
        safe_id = hashlib.sha256(session_id.encode()).hexdigest()[:16]
        session_dir = self.config.session_dir or DEFAULT_SESSION_DIR
        return session_dir / f"session_{safe_id}.json"

    def _build_command(
        self,
        prompt: str,
        model: str,
        session_id: Optional[str] = None,
        output_format: str = "json",
    ) -> List[str]:
        """Build subprocess command for Claude Code CLI.

        Args:
            prompt: Full prompt string
            model: Model identifier (claude-sonnet-4 or claude-opus-4)
            session_id: Optional session ID for --resume
            output_format: Output format (default json)

        Returns:
            Command list for subprocess

        Notes:
            - Uses --print for non-interactive mode
            - Uses --output-format json for structured output
            - Uses --model to select opus vs sonnet
            - Uses --resume for session continuation
        """
        cmd = ["claude"]

        # Non-interactive mode
        if self.config.print_mode:
            cmd.append("--print")

        # Add prompt
        cmd.extend(["-p", prompt])

        # Output format
        cmd.extend(["--output-format", output_format])

        # Model selection
        cmd.extend(["--model", model])

        # Session continuation
        if session_id:
            cmd.extend(["--resume", session_id])

        return cmd

    async def _run_subprocess(
        self,
        cmd: List[str],
        timeout: int,
    ) -> Dict[str, Any]:
        """Execute subprocess and return parsed JSON result.

        Args:
            cmd: Command list
            timeout: Timeout in seconds

        Returns:
            Parsed JSON response

        Raises:
            TimeoutError: On timeout
            RuntimeError: On execution error
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else f"Exit code: {process.returncode}"

                # Check for subscription limit errors
                if any(x in error_msg.lower() for x in [
                    "rate limit", "quota exceeded", "subscription",
                    "limit reached", "too many requests"
                ]):
                    raise RuntimeError(f"Subscription limit error: {error_msg}")

                # Check for auth errors - fail fast
                if any(x in error_msg.lower() for x in [
                    "not authenticated", "authentication", "not logged in",
                    "unauthorized", "401", "403"
                ]):
                    raise RuntimeError(f"Authentication error: {error_msg}")

                # Check for session not found - handle gracefully
                if "session not found" in error_msg.lower():
                    logger.warning(f"Session not found, will create new session")
                    # Return empty result to trigger retry without session
                    return {"content": "", "session_not_found": True}

                # Other errors
                raise RuntimeError(f"Claude Code CLI error: {error_msg}")

            # Parse output
            output = stdout.decode().strip()
            if not output:
                return {"content": "", "usage": {}}

            try:
                return json.loads(output)
            except json.JSONDecodeError:
                # If not JSON, treat as plain text response
                return {"content": output, "usage": {}}

        except asyncio.TimeoutError:
            raise TimeoutError(f"Claude Code CLI timed out after {timeout}s")

    def _parse_response(
        self,
        result: Dict[str, Any],
        model: str,
        latency_ms: int,
    ) -> AgentResponse:
        """Parse subprocess result into AgentResponse.

        Args:
            result: Raw result from subprocess
            model: Model identifier used
            latency_ms: Latency in milliseconds

        Returns:
            Standardized AgentResponse

        Note:
            cost_usd = 0.0 for subscription-based pricing
        """
        # Extract content - handle various response formats
        content = result.get("content", result.get("message", result.get("result", "")))
        if isinstance(content, dict):
            content = content.get("content", content.get("text", str(content)))

        # Claude Code may return tool results differently
        if "tool_outputs" in result:
            tool_outputs = result.get("tool_outputs", [])
            if tool_outputs and isinstance(tool_outputs[-1], dict):
                content = tool_outputs[-1].get("output", content)

        # Extract usage info - Claude Code may not always provide this
        usage = result.get("usage", {})
        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))

        # Extract tool calls if present
        tool_calls = result.get("tool_calls", result.get("tool_use", []))

        return AgentResponse(
            content=str(content),
            tool_calls=tool_calls if isinstance(tool_calls, list) else [],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=usage.get("cache_read_tokens", 0),
            cache_write_tokens=usage.get("cache_write_tokens", 0),
            model=model,
            latency_ms=latency_ms,
            cost_usd=0.0,  # Subscription-based pricing
            metadata={"raw_result": result},
        )

    def get_model_for_role(self, role: AgentRole) -> str:
        """Get model for a given role.

        Per 05.2-CONTEXT.md role-to-model mapping:
        - ATTACKER: claude-opus-4 (deep reasoning for exploit construction)
        - VERIFIER: claude-opus-4 (accuracy for cross-checking)
        - DEFENDER: claude-sonnet-4 (fast guard detection)
        - TEST_BUILDER: claude-sonnet-4 (code generation)
        - SUPERVISOR: claude-sonnet-4 (orchestration)
        - INTEGRATOR: claude-sonnet-4 (summarization)

        Args:
            role: Agent role

        Returns:
            Model identifier (opus or sonnet)
        """
        if role in CRITICAL_ROLES:
            return self.config.opus_model
        return self.config.model

    def _build_prompt(
        self,
        config: AgentConfig,
        messages: List[Dict[str, Any]],
    ) -> str:
        """Build prompt string from config and messages.

        Args:
            config: Agent configuration with system prompt
            messages: List of messages in OpenAI format

        Returns:
            Combined prompt string
        """
        parts = []

        # Add system prompt
        if config.system_prompt:
            parts.append(f"<system>\n{config.system_prompt}\n</system>\n")

        # Add messages
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                parts.append(f"<system>\n{content}\n</system>\n")
            elif role == "assistant":
                parts.append(f"<assistant>\n{content}\n</assistant>\n")
            else:  # user
                parts.append(f"<user>\n{content}\n</user>\n")

        return "\n".join(parts)

    async def execute(
        self,
        config: AgentConfig,
        messages: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> AgentResponse:
        """Execute agent with configuration and messages.

        Args:
            config: Agent configuration
            messages: Conversation messages
            session_id: Optional session ID for continuation

        Returns:
            AgentResponse with content and usage

        Raises:
            RuntimeError: On permanent errors (auth, subscription limit)
            TimeoutError: On timeout
        """
        model = self.get_model_for_role(config.role)
        prompt = self._build_prompt(config, messages)
        cmd = self._build_command(prompt, model, session_id)

        start_time = time.monotonic()
        retries = 0

        while retries <= self.config.max_retries:
            try:
                result = await self._run_subprocess(cmd, self.config.timeout_seconds)

                # Handle session not found - retry without session
                if result.get("session_not_found") and session_id:
                    logger.info("Session not found, retrying without session")
                    cmd = self._build_command(prompt, model, None)
                    result = await self._run_subprocess(cmd, self.config.timeout_seconds)

                latency_ms = int((time.monotonic() - start_time) * 1000)
                response = self._parse_response(result, model, latency_ms)

                # Track usage
                self._usage_tracker.track(response)

                return response

            except RuntimeError as e:
                error_str = str(e)
                # Auth and subscription errors - don't retry
                if "Authentication error" in error_str or "Subscription limit" in error_str:
                    raise

                retries += 1
                if retries > self.config.max_retries:
                    raise

                # Exponential backoff
                await asyncio.sleep(2 ** retries)

            except TimeoutError:
                retries += 1
                if retries > self.config.max_retries:
                    raise

                await asyncio.sleep(2 ** retries)

        # Should not reach here
        raise RuntimeError("Execution failed after all retries")

    async def spawn_agent(
        self,
        config: AgentConfig,
        task: str,
    ) -> AgentResponse:
        """Spawn a context-fresh agent for a single task.

        Creates a new agent with no session - fully context-fresh
        per PHILOSOPHY.md preference for isolated execution.

        Args:
            config: Agent configuration
            task: Task description

        Returns:
            AgentResponse from the spawned agent
        """
        messages = [{"role": "user", "content": task}]
        # No session_id - context-fresh spawn
        return await self.execute(config, messages, session_id=None)

    async def execute_with_session(
        self,
        config: AgentConfig,
        messages: List[Dict[str, Any]],
        session_id: str,
    ) -> AgentResponse:
        """Execute with session continuation.

        For multi-turn conversations, use this method to continue
        an existing session.

        Args:
            config: Agent configuration
            messages: Conversation messages (typically just the latest)
            session_id: Session ID to continue

        Returns:
            AgentResponse with session context
        """
        return await self.execute(config, messages, session_id=session_id)

    def get_usage(self) -> Dict[str, Any]:
        """Get aggregated usage statistics.

        Returns:
            Dictionary with:
            - total_tokens: Sum of input + output tokens
            - total_cost: Always 0.0 (subscription)
            - request_count: Number of requests made
            - by_model: Breakdown by model
        """
        summary = self._usage_tracker.get_summary()
        return {
            "total_tokens": summary["total_input_tokens"] + summary["total_output_tokens"],
            "total_cost": 0.0,  # Subscription-based
            "request_count": summary["request_count"],
            "by_model": {
                model: {
                    "tokens": data["input_tokens"] + data["output_tokens"],
                    "cost": 0.0,  # Subscription-based
                    "requests": data["count"],
                }
                for model, data in summary["by_model"].items()
            },
        }

    def reset_usage(self) -> None:
        """Reset usage tracking."""
        self._usage_tracker.reset()


__all__ = [
    "ClaudeCodeRuntime",
    "ClaudeCodeConfig",
    "CRITICAL_ROLES",
    "DEFAULT_SESSION_DIR",
]
