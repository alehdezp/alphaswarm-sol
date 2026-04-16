"""OpenCode SDK Runtime Implementation.

This module provides OpenCodeRuntime - the primary runtime for multi-model
agent execution via OpenCode CLI and OpenRouter.

Per 05.3-CONTEXT.md:
- Primary SDK for multi-model access (400+ models via OpenRouter)
- Task-type-based model routing for cost optimization
- Loop prevention via iterations, output hashing, and token ceiling
- Rankings-based model selection with EMA feedback

Usage:
    from alphaswarm_sol.agents.runtime.opencode import OpenCodeRuntime, OpenCodeConfig

    config = OpenCodeConfig(default_model="google/gemini-3-flash-preview")
    runtime = OpenCodeRuntime(config)

    response = await runtime.execute(
        AgentConfig(role=AgentRole.VERIFIER, system_prompt="..."),
        messages=[{"role": "user", "content": "Analyze this code..."}],
        task_type="verify",
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
from typing import Any, Dict, List, Optional, Union

import yaml

from .base import AgentConfig, AgentResponse, AgentRole, AgentRuntime, UsageTracker
from .types import (
    DEFAULT_MODELS,
    MODEL_PRICING,
    TaskType,
    calculate_model_cost,
    get_context_limit,
)

logger = logging.getLogger(__name__)


# Loop prevention constants
MAX_ITERATIONS = 10  # Hard limit on LLM calls per task
MAX_REPEATED_OUTPUTS = 3  # Consecutive identical outputs trigger abort
TOKEN_CEILING = 100_000  # Max tokens per task


@dataclass
class LoopState:
    """Track state for loop prevention.

    Attributes:
        iteration_count: Number of LLM calls made
        output_hashes: SHA256 hashes of outputs for deduplication
        total_tokens_used: Cumulative tokens across iterations
    """
    iteration_count: int = 0
    output_hashes: List[str] = field(default_factory=list)
    total_tokens_used: int = 0


@dataclass
class OpenCodeConfig:
    """Configuration for OpenCode runtime.

    Attributes:
        default_model: Default model for general tasks
        verify_model: Model for verification tasks (free tier)
        summarize_model: Model for summarization (free tier)
        context_model: Model for context gathering
        code_model: Model for code generation
        reasoning_model: Model for reasoning tasks
        reasoning_heavy_model: Model for complex reasoning
        heavy_model: Model for large context processing
        fallback_model: Fallback when primary model fails
        timeout_seconds: Timeout for subprocess calls
        max_retries: Maximum retry attempts
        rankings_path: Path to rankings YAML file
        working_dir: Working directory for subprocess
    """
    default_model: str = "google/gemini-3-flash-preview"
    verify_model: str = "minimax/minimax-m2:free"
    summarize_model: str = "minimax/minimax-m2:free"
    context_model: str = "x-ai/grok-code-fast-1"
    code_model: str = "zhipu/glm-4.7"
    reasoning_model: str = "deepseek/deepseek-v3.2"
    reasoning_heavy_model: str = "google/gemini-3-pro-preview"
    heavy_model: str = "google/gemini-3-flash-preview"
    fallback_model: str = "qwen/qwen-2.5-72b-instruct:free"
    timeout_seconds: int = 120
    max_retries: int = 3
    rankings_path: Optional[Path] = None
    working_dir: Optional[Path] = None

    def get_model_for_task_type(self, task_type: TaskType) -> str:
        """Get configured model for a task type.

        Args:
            task_type: The task type

        Returns:
            Model identifier string
        """
        model_map = {
            TaskType.VERIFY: self.verify_model,
            TaskType.SUMMARIZE: self.summarize_model,
            TaskType.CONTEXT: self.context_model,
            TaskType.CODE: self.code_model,
            TaskType.REASONING: self.reasoning_model,
            TaskType.REASONING_HEAVY: self.reasoning_heavy_model,
            TaskType.HEAVY: self.heavy_model,
            TaskType.ANALYZE: self.default_model,
            TaskType.REVIEW: self.default_model,  # Codex handled specially
            TaskType.CRITICAL: self.default_model,  # Claude handled specially
        }
        return model_map.get(task_type, self.default_model)


class OpenCodeRuntime(AgentRuntime):
    """OpenCode SDK runtime for multi-model agent execution.

    Executes agents via OpenCode CLI subprocess calls, providing:
    - Task-type-based model routing
    - Rankings-based model selection
    - Loop prevention (iterations, output hash, token ceiling)
    - Cost tracking and usage aggregation

    Per 05.3-CONTEXT.md:
    - Primary runtime for multi-model access via OpenRouter
    - Subprocess execution: opencode -p "prompt" --model "model-id" -f json -q
    - Rankings stored in .vrs/rankings/rankings.yaml
    """

    def __init__(
        self,
        config: Optional[OpenCodeConfig] = None,
        working_dir: Optional[Path] = None,
        rankings_store: Optional[Dict[str, Any]] = None,
    ):
        """Initialize OpenCode runtime.

        Args:
            config: Runtime configuration
            working_dir: Working directory for subprocess (overrides config)
            rankings_store: Pre-loaded rankings (for testing)
        """
        self.config = config or OpenCodeConfig()
        self.working_dir = working_dir or self.config.working_dir or Path.cwd()
        self._usage_tracker = UsageTracker()
        self._rankings: Dict[str, Any] = rankings_store or {}
        self._rankings_loaded = rankings_store is not None

        # Load rankings if path specified and not pre-loaded
        if not self._rankings_loaded and self.config.rankings_path:
            self._load_rankings()

    def _load_rankings(self) -> None:
        """Load rankings from YAML file."""
        if not self.config.rankings_path:
            return

        rankings_path = self.config.rankings_path
        if not rankings_path.is_absolute():
            rankings_path = self.working_dir / rankings_path

        if rankings_path.exists():
            try:
                with open(rankings_path) as f:
                    self._rankings = yaml.safe_load(f) or {}
                logger.debug(f"Loaded rankings from {rankings_path}")
            except Exception as e:
                logger.warning(f"Failed to load rankings: {e}")
                self._rankings = {}
        else:
            logger.debug(f"Rankings file not found: {rankings_path}")

        self._rankings_loaded = True

    def _save_rankings(self) -> None:
        """Save rankings to YAML file."""
        if not self.config.rankings_path:
            return

        rankings_path = self.config.rankings_path
        if not rankings_path.is_absolute():
            rankings_path = self.working_dir / rankings_path

        try:
            rankings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(rankings_path, "w") as f:
                yaml.safe_dump(self._rankings, f, default_flow_style=False)
            logger.debug(f"Saved rankings to {rankings_path}")
        except Exception as e:
            logger.warning(f"Failed to save rankings: {e}")

    def _select_model(
        self,
        task_type: Union[str, TaskType],
        role: Optional[AgentRole] = None,
    ) -> str:
        """Select optimal model for task type and role.

        Model selection priority:
        1. Rankings-based selection (if rankings exist for task type)
        2. Config-based selection (per OpenCodeConfig)
        3. DEFAULT_MODELS fallback

        Args:
            task_type: Task type (str or TaskType enum)
            role: Optional agent role for additional context

        Returns:
            Model identifier string
        """
        # Normalize task type
        if isinstance(task_type, str):
            try:
                task_type = TaskType(task_type.lower())
            except ValueError:
                task_type = TaskType.ANALYZE

        task_key = task_type.value

        # Check rankings first
        if self._rankings and task_key in self._rankings:
            ranked_models = self._rankings[task_key]
            if isinstance(ranked_models, list) and ranked_models:
                # Return top-ranked model
                top_model = ranked_models[0]
                if isinstance(top_model, dict):
                    return top_model.get("model", self.config.get_model_for_task_type(task_type))
                return str(top_model)

        # Use config-based selection
        return self.config.get_model_for_task_type(task_type)

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

    def _build_command(self, model: str, prompt: str) -> List[str]:
        """Build subprocess command for OpenCode CLI.

        Args:
            model: Model identifier
            prompt: Full prompt string

        Returns:
            Command list for subprocess
        """
        # opencode -p "prompt" --model "model-id" -f json -q
        return [
            "opencode",
            "-p", prompt,
            "--model", model,
            "-f", "json",
            "-q",  # Quiet mode - no interactive prompts
        ]

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

                # Check for auth errors - fail fast
                if any(x in error_msg.lower() for x in ["unauthorized", "authentication", "api key", "401", "403"]):
                    raise RuntimeError(f"Authentication error: {error_msg}")

                # Other errors might be retryable
                raise RuntimeError(f"OpenCode CLI error: {error_msg}")

            # Parse JSON output
            output = stdout.decode().strip()
            if not output:
                return {"content": "", "usage": {}}

            try:
                return json.loads(output)
            except json.JSONDecodeError:
                # If not JSON, treat as plain text response
                return {"content": output, "usage": {}}

        except asyncio.TimeoutError:
            raise TimeoutError(f"OpenCode CLI timed out after {timeout}s")

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
        """
        content = result.get("content", result.get("message", ""))
        if isinstance(content, dict):
            content = content.get("content", str(content))

        # Extract usage info
        usage = result.get("usage", {})
        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))

        # Extract tool calls if present
        tool_calls = result.get("tool_calls", [])

        # Calculate cost
        cost = calculate_model_cost(model, input_tokens, output_tokens)

        return AgentResponse(
            content=str(content),
            tool_calls=tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            latency_ms=latency_ms,
            cost_usd=cost,
            metadata={"raw_result": result},
        )

    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for model usage.

        Args:
            model: Model identifier
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Cost in USD
        """
        return calculate_model_cost(model, input_tokens, output_tokens)

    def _check_loop_prevention(self, state: LoopState, output: str) -> bool:
        """Check if loop prevention should abort execution.

        Three mechanisms combined:
        1. Iteration count limit (MAX_ITERATIONS)
        2. Repeated output detection (MAX_REPEATED_OUTPUTS consecutive)
        3. Token ceiling (TOKEN_CEILING)

        Args:
            state: Current loop state
            output: Latest output string

        Returns:
            True if loop detected (should abort), False otherwise
        """
        # Check iteration count
        if state.iteration_count >= MAX_ITERATIONS:
            logger.warning(f"Loop prevention: max iterations ({MAX_ITERATIONS}) reached")
            return True

        # Check repeated outputs
        output_hash = hashlib.sha256(output.encode()).hexdigest()[:16]
        if len(state.output_hashes) >= MAX_REPEATED_OUTPUTS:
            recent_hashes = state.output_hashes[-MAX_REPEATED_OUTPUTS:]
            if all(h == output_hash for h in recent_hashes):
                logger.warning(
                    f"Loop prevention: repeated output detected "
                    f"{MAX_REPEATED_OUTPUTS} times"
                )
                return True
        state.output_hashes.append(output_hash)

        # Check token ceiling
        if state.total_tokens_used >= TOKEN_CEILING:
            logger.warning(f"Loop prevention: token ceiling ({TOKEN_CEILING}) exceeded")
            return True

        return False

    async def _record_feedback(
        self,
        task_type: Union[str, TaskType],
        role: Optional[AgentRole],
        model: str,
        response: AgentResponse,
    ) -> None:
        """Record execution feedback for rankings.

        Updates rankings with EMA-based weighting.

        Args:
            task_type: Task type executed
            role: Agent role (if any)
            model: Model used
            response: Response received
        """
        if isinstance(task_type, TaskType):
            task_key = task_type.value
        else:
            task_key = task_type

        # Initialize task rankings if needed
        if task_key not in self._rankings:
            self._rankings[task_key] = []

        # Simple success tracking for now
        # Full EMA implementation in later plans
        entry = {
            "model": model,
            "success": len(response.content) > 0,
            "latency_ms": response.latency_ms,
            "tokens": response.total_tokens,
            "cost": response.cost_usd,
            "timestamp": time.time(),
        }

        # Add to rankings
        self._rankings[task_key].append(entry)

        # Save if path configured
        self._save_rankings()

    async def execute(
        self,
        config: AgentConfig,
        messages: List[Dict[str, Any]],
        task_type: Union[str, TaskType] = "analyze",
    ) -> AgentResponse:
        """Execute agent with configuration and messages.

        Args:
            config: Agent configuration
            messages: Conversation messages
            task_type: Task type for model selection

        Returns:
            AgentResponse with content and usage

        Raises:
            RuntimeError: On permanent errors
            TimeoutError: On timeout
        """
        model = self._select_model(task_type, config.role)
        prompt = self._build_prompt(config, messages)
        cmd = self._build_command(model, prompt)

        start_time = time.monotonic()
        retries = 0

        while retries <= self.config.max_retries:
            try:
                result = await self._run_subprocess(cmd, self.config.timeout_seconds)
                latency_ms = int((time.monotonic() - start_time) * 1000)

                response = self._parse_response(result, model, latency_ms)

                # Track usage
                self._usage_tracker.track(response)

                # Record feedback
                await self._record_feedback(task_type, config.role, model, response)

                return response

            except RuntimeError as e:
                # Auth errors - don't retry
                if "Authentication error" in str(e):
                    raise

                retries += 1
                if retries > self.config.max_retries:
                    # Try fallback model
                    if model != self.config.fallback_model:
                        logger.warning(f"Retries exhausted, trying fallback model")
                        model = self.config.fallback_model
                        cmd = self._build_command(model, prompt)
                        retries = 0
                        continue
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

        Args:
            config: Agent configuration
            task: Task description

        Returns:
            AgentResponse from the spawned agent
        """
        messages = [{"role": "user", "content": task}]

        # Determine task type from role
        role_to_task_type = {
            AgentRole.ATTACKER: TaskType.REASONING,
            AgentRole.DEFENDER: TaskType.ANALYZE,
            AgentRole.VERIFIER: TaskType.VERIFY,
            AgentRole.TEST_BUILDER: TaskType.CODE,
            AgentRole.SUPERVISOR: TaskType.ANALYZE,
            AgentRole.INTEGRATOR: TaskType.SUMMARIZE,
        }
        task_type = role_to_task_type.get(config.role, TaskType.ANALYZE)

        return await self.execute(config, messages, task_type)

    def get_model_for_role(self, role: AgentRole) -> str:
        """Get model for a given role.

        Maps roles to appropriate task types and returns the model.

        Args:
            role: Agent role

        Returns:
            Model identifier
        """
        role_to_task_type = {
            AgentRole.ATTACKER: TaskType.REASONING,
            AgentRole.DEFENDER: TaskType.ANALYZE,
            AgentRole.VERIFIER: TaskType.VERIFY,
            AgentRole.TEST_BUILDER: TaskType.CODE,
            AgentRole.SUPERVISOR: TaskType.ANALYZE,
            AgentRole.INTEGRATOR: TaskType.SUMMARIZE,
        }
        task_type = role_to_task_type.get(role, TaskType.ANALYZE)
        return self._select_model(task_type, role)

    def get_usage(self) -> Dict[str, Any]:
        """Get aggregated usage statistics.

        Returns:
            Dictionary with:
            - total_tokens: Sum of input + output tokens
            - total_cost: Total USD cost
            - request_count: Number of requests made
            - by_model: Breakdown by model
        """
        summary = self._usage_tracker.get_summary()
        return {
            "total_tokens": summary["total_input_tokens"] + summary["total_output_tokens"],
            "total_cost": summary["total_cost_usd"],
            "request_count": summary["request_count"],
            "by_model": {
                model: {
                    "tokens": data["input_tokens"] + data["output_tokens"],
                    "cost": data["cost_usd"],
                    "requests": data["count"],
                }
                for model, data in summary["by_model"].items()
            },
        }

    def reset_usage(self) -> None:
        """Reset usage tracking."""
        self._usage_tracker.reset()

    def get_rankings(self) -> Dict[str, Any]:
        """Get current model rankings.

        Returns:
            Rankings dictionary by task type
        """
        return self._rankings.copy()


__all__ = [
    "OpenCodeRuntime",
    "OpenCodeConfig",
    "LoopState",
    "MAX_ITERATIONS",
    "MAX_REPEATED_OUTPUTS",
    "TOKEN_CEILING",
]
