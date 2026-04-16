"""Codex CLI Runtime Implementation.

This module provides CodexCLIRuntime - the runtime for alternative perspective
reviews and double-checks via Codex CLI (ChatGPT Plus subscription).

Per 05.3-CONTEXT.md:
- Subscription-based ($20/month ChatGPT Plus) for review tasks
- Codex CLI uses `codex exec` for non-interactive mode
- Provides GPT-4 perspective for double-checking Claude's conclusions
- Reduces correlated errors by using different model family

Use Cases:
- Review: Alternative perspective on findings
- Double-check: Verify Claude's conclusions with GPT-4
- Discussion: Interactive review (future)

Usage:
    from alphaswarm_sol.agents.runtime.codex_cli import CodexCLIRuntime, CodexCLIConfig

    config = CodexCLIConfig()
    runtime = CodexCLIRuntime(config)

    response = await runtime.execute(
        AgentConfig(role=AgentRole.VERIFIER, system_prompt="..."),
        messages=[{"role": "user", "content": "Review this finding..."}],
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import AgentConfig, AgentResponse, AgentRole, AgentRuntime, UsageTracker

logger = logging.getLogger(__name__)


@dataclass
class CodexCLIConfig:
    """Configuration for Codex CLI runtime.

    Attributes:
        model: Default model for Codex CLI (gpt-4o)
        timeout_seconds: Timeout for subprocess calls
        max_tokens: Maximum tokens for response
        working_dir: Working directory for subprocess
        max_retries: Maximum retry attempts
        context_files: Default context files to include
        approval_mode: Approval mode for codex exec (full-auto, suggest, auto-edit)
    """
    model: str = "gpt-4o"
    timeout_seconds: int = 180
    max_tokens: int = 4096
    working_dir: Optional[Path] = None
    max_retries: int = 2
    context_files: List[str] = field(default_factory=list)
    approval_mode: str = "full-auto"

    def __post_init__(self):
        """Validate configuration."""
        valid_modes = {"full-auto", "suggest", "auto-edit"}
        if self.approval_mode not in valid_modes:
            raise ValueError(f"approval_mode must be one of {valid_modes}")


class CodexCLIRuntime(AgentRuntime):
    """Codex CLI runtime for review and alternative perspective tasks.

    Executes agents via Codex CLI subprocess calls, providing:
    - GPT-4 family perspective for diversity (reduces correlated errors)
    - Non-interactive mode with `codex exec --json`
    - Context file support with --context flag
    - Cost tracking as subscription-based (cost_usd = 0.0)

    Per 05.3-CONTEXT.md:
    - Used for reviews and double-checking Claude's conclusions
    - ChatGPT Plus subscription ($20/month)
    - Primary use: getting alternative perspective on findings

    CLI Command Format:
        codex exec "prompt" --json [--context file.sol] [--approval-mode full-auto]
    """

    def __init__(
        self,
        config: Optional[CodexCLIConfig] = None,
        working_dir: Optional[Path] = None,
    ):
        """Initialize Codex CLI runtime.

        Args:
            config: Runtime configuration
            working_dir: Working directory (overrides config)
        """
        self.config = config or CodexCLIConfig()
        self.default_working_dir = working_dir or self.config.working_dir or Path.cwd()
        self._usage_tracker = UsageTracker()

    def _get_working_dir(self, agent_config: Optional[AgentConfig] = None) -> Path:
        """Get the working directory for execution.

        Phase 07.3.1.9: Respects AgentConfig.workdir for workspace isolation.

        Args:
            agent_config: Optional agent config with workdir

        Returns:
            Working directory path
        """
        if agent_config and agent_config.workdir:
            return Path(agent_config.workdir)
        return self.default_working_dir

    def _build_command(
        self,
        prompt: str,
        context_files: Optional[List[str]] = None,
        approval_mode: Optional[str] = None,
    ) -> List[str]:
        """Build subprocess command for Codex CLI.

        Args:
            prompt: Full prompt string
            context_files: Optional list of context file paths
            approval_mode: Approval mode (full-auto, suggest, auto-edit)

        Returns:
            Command list for subprocess

        Notes:
            - Uses `codex exec` for non-interactive scripted execution
            - Uses --json for structured JSON output
            - Uses --context for adding file context
            - Uses --approval-mode for execution mode
        """
        cmd = ["codex", "exec"]

        # Add prompt
        cmd.append(prompt)

        # JSON output format
        cmd.append("--json")

        # Add context files
        files = context_files or self.config.context_files
        for ctx_file in files:
            cmd.extend(["--context", ctx_file])

        # Approval mode
        mode = approval_mode or self.config.approval_mode
        cmd.extend(["--approval-mode", mode])

        return cmd

    async def _run_subprocess(
        self,
        cmd: List[str],
        timeout: int,
        working_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Execute subprocess and return parsed JSON result.

        Args:
            cmd: Command list
            timeout: Timeout in seconds
            working_dir: Optional working directory (Phase 07.1.1-05)

        Returns:
            Parsed JSON response

        Raises:
            TimeoutError: On timeout
            RuntimeError: On execution error
        """
        cwd = str(working_dir) if working_dir else str(self.default_working_dir)
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
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
                    "limit reached", "too many requests", "usage limit"
                ]):
                    raise RuntimeError(f"Subscription limit error: {error_msg}")

                # Check for auth errors - fail fast
                if any(x in error_msg.lower() for x in [
                    "not authenticated", "authentication", "not logged in",
                    "unauthorized", "401", "403", "api key", "invalid key"
                ]):
                    raise RuntimeError(f"Authentication error: {error_msg}")

                # Check for model not available
                if any(x in error_msg.lower() for x in [
                    "model not found", "model unavailable", "invalid model"
                ]):
                    raise RuntimeError(f"Model error: {error_msg}")

                # Command not found (Codex not installed)
                if any(x in error_msg.lower() for x in [
                    "command not found", "not found", "not recognized"
                ]) or process.returncode == 127:
                    raise RuntimeError(
                        "Codex CLI not installed. Install via npm: npm install -g @openai/codex"
                    )

                # Other errors
                raise RuntimeError(f"Codex CLI error: {error_msg}")

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
            raise TimeoutError(f"Codex CLI timed out after {timeout}s")

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

        # Codex may return response in different keys
        if not content and "output" in result:
            content = result["output"]
        if not content and "response" in result:
            content = result["response"]

        # Extract usage info - Codex may not always provide this
        usage = result.get("usage", {})
        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))

        # Extract tool calls if present
        tool_calls = result.get("tool_calls", result.get("function_calls", []))

        return AgentResponse(
            content=str(content),
            tool_calls=tool_calls if isinstance(tool_calls, list) else [],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=0,  # Codex doesn't have prompt caching
            cache_write_tokens=0,
            model=model,
            latency_ms=latency_ms,
            cost_usd=0.0,  # Subscription-based pricing
            metadata={"raw_result": result, "runtime": "codex_cli"},
        )

    def get_model_for_role(self, role: Optional[AgentRole]) -> str:
        """Get model for a given role.

        For Codex CLI, all roles use the configured model (gpt-4o by default).
        Codex is primarily used for reviews/alternative perspectives, not
        role-based model routing.

        Args:
            role: Agent role (ignored, always returns config.model)

        Returns:
            Model identifier (always config.model)
        """
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
        context_files: Optional[List[str]] = None,
    ) -> AgentResponse:
        """Execute agent with configuration and messages.

        Args:
            config: Agent configuration
            messages: Conversation messages
            context_files: Optional context files to include

        Returns:
            AgentResponse with content and usage

        Raises:
            RuntimeError: On permanent errors (auth, subscription limit)
            TimeoutError: On timeout
        """
        model = self.get_model_for_role(config.role)
        prompt = self._build_prompt(config, messages)
        cmd = self._build_command(prompt, context_files)

        # Get working directory (respects workdir for workspace isolation)
        working_dir = self._get_working_dir(config)

        start_time = time.monotonic()
        retries = 0

        while retries <= self.config.max_retries:
            try:
                result = await self._run_subprocess(
                    cmd, self.config.timeout_seconds, working_dir
                )

                latency_ms = int((time.monotonic() - start_time) * 1000)
                response = self._parse_response(result, model, latency_ms)

                # Track usage
                self._usage_tracker.track(response)

                return response

            except RuntimeError as e:
                error_str = str(e)
                # Auth, subscription, and model errors - don't retry
                if any(x in error_str for x in [
                    "Authentication error",
                    "Subscription limit",
                    "Model error",
                    "not installed"
                ]):
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
        return await self.execute(config, messages)

    async def review(
        self,
        finding: str,
        context: Optional[str] = None,
        context_files: Optional[List[str]] = None,
    ) -> AgentResponse:
        """Review a finding with alternative perspective.

        Specialized method for review tasks - primary use case for Codex CLI.

        Args:
            finding: The finding or conclusion to review
            context: Optional additional context
            context_files: Optional context files

        Returns:
            AgentResponse with review perspective
        """
        system_prompt = """You are a senior security researcher reviewing findings.
Your role is to provide an alternative perspective and identify any issues:
- Evaluate the evidence supporting the finding
- Consider alternative explanations
- Identify any gaps in the analysis
- Suggest additional investigation if needed

Be thorough but concise. Focus on whether the conclusion is well-supported."""

        content = f"Please review this finding:\n\n{finding}"
        if context:
            content += f"\n\nAdditional context:\n{context}"

        config = AgentConfig(
            role=AgentRole.VERIFIER,  # Review role
            system_prompt=system_prompt,
            max_tokens=self.config.max_tokens,
            temperature=0.1,
        )
        messages = [{"role": "user", "content": content}]

        return await self.execute(config, messages, context_files)

    async def double_check(
        self,
        conclusion: str,
        evidence: str,
        context_files: Optional[List[str]] = None,
    ) -> AgentResponse:
        """Double-check a conclusion with alternative model.

        Uses GPT-4 to verify Claude's conclusions - reduces correlated errors.

        Args:
            conclusion: The conclusion to verify
            evidence: Supporting evidence
            context_files: Optional context files

        Returns:
            AgentResponse with verification result
        """
        system_prompt = """You are verifying a security analysis conclusion.
Examine the evidence and determine if it supports the conclusion.

Respond with:
1. CONFIRMED if evidence strongly supports the conclusion
2. DISPUTED if evidence contradicts or doesn't support the conclusion
3. UNCERTAIN if more evidence is needed

Explain your reasoning briefly."""

        content = f"""Conclusion to verify:
{conclusion}

Supporting evidence:
{evidence}

Does the evidence support this conclusion?"""

        config = AgentConfig(
            role=AgentRole.VERIFIER,
            system_prompt=system_prompt,
            max_tokens=1024,
            temperature=0.0,  # Deterministic for verification
        )
        messages = [{"role": "user", "content": content}]

        return await self.execute(config, messages, context_files)

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
    "CodexCLIRuntime",
    "CodexCLIConfig",
]
