"""Anthropic Runtime Implementation.

This module provides the Anthropic SDK implementation of AgentRuntime with:
- Prompt caching for cost reduction (90% on cached reads)
- Role-based model selection (Opus for deep reasoning, Sonnet for fast tasks)
- Retry with exponential backoff for transient errors
- Cost and token tracking

Per TOKEN-EFFICIENCY-RESEARCH.md:
- Cache VulnDocs, tool definitions, contract source (stable prefix)
- Dynamic suffix: bead context, agent role, investigation state
- Cache breakeven: ~3 requests with same prefix

Usage:
    from alphaswarm_sol.agents.runtime import AnthropicRuntime, RuntimeConfig

    config = RuntimeConfig(enable_prompt_caching=True)
    runtime = AnthropicRuntime(config)

    response = await runtime.execute(agent_config, messages)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

import anthropic
from anthropic import APIError, APIConnectionError, RateLimitError, AuthenticationError

from .base import (
    AgentConfig,
    AgentResponse,
    AgentRole,
    AgentRuntime,
    UsageTracker,
)
from .config import (
    ROLE_MODEL_MAP,
    RuntimeConfig,
    calculate_cost,
)


logger = logging.getLogger(__name__)


class AnthropicRuntime(AgentRuntime):
    """Anthropic SDK implementation of AgentRuntime.

    Features:
    - Prompt caching with cache_control markers
    - Role-based model selection from ROLE_MODEL_MAP
    - Retry with exponential backoff for rate limits
    - Comprehensive token and cost tracking
    - Tool calling support

    Per 05.2-CONTEXT.md error handling:
    - Retry transient errors (rate limits, timeouts) with backoff
    - Fail fast on permanent errors (auth, bad request)
    """

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        api_key: Optional[str] = None,
    ):
        """Initialize Anthropic runtime.

        Args:
            config: Runtime configuration
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.config = config or RuntimeConfig(preferred_sdk="anthropic")
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
        )
        self._usage_tracker = UsageTracker()

    async def execute(
        self,
        config: AgentConfig,
        messages: List[Dict[str, Any]],
    ) -> AgentResponse:
        """Execute agent with prompt caching.

        Per TOKEN-EFFICIENCY-RESEARCH.md, applies cache_control to
        stable prefix (system prompt) for 90% cost reduction on
        subsequent requests.

        Args:
            config: Agent configuration
            messages: Conversation messages

        Returns:
            AgentResponse with content and usage metrics

        Raises:
            RuntimeError: On permanent errors (auth, bad request)
            TimeoutError: When execution exceeds timeout
        """
        model = self.get_model_for_role(config.role)
        start_time = time.perf_counter()

        # Build system prompt with cache control
        system_content = self._build_cached_system(config.system_prompt)

        # Build tools with cache control if provided
        tools = self._build_cached_tools(config.tools) if config.tools else None

        # Execute with retry
        response = await self._execute_with_retry(
            model=model,
            system=system_content,
            messages=messages,
            tools=tools,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            timeout=config.timeout_seconds,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Parse response
        agent_response = self._parse_response(response, model, latency_ms)

        # Track usage
        if self.config.enable_cost_tracking:
            self._usage_tracker.track(agent_response)

        return agent_response

    async def spawn_agent(
        self,
        config: AgentConfig,
        task: str,
    ) -> AgentResponse:
        """Spawn context-fresh agent for single task.

        Creates a new conversation with just the task - no prior context.
        Per PHILOSOPHY.md preference for isolated agent execution.

        Args:
            config: Agent configuration
            task: Task description

        Returns:
            AgentResponse with agent's response
        """
        messages = [{"role": "user", "content": task}]
        return await self.execute(config, messages)

    def get_model_for_role(self, role: AgentRole) -> str:
        """Get Anthropic model for role.

        Args:
            role: Agent role

        Returns:
            Anthropic model identifier
        """
        # Check custom override first
        if role in self.config.custom_model_map:
            return self.config.custom_model_map[role]
        return ROLE_MODEL_MAP[role]["anthropic"]

    def get_usage(self) -> Dict[str, Any]:
        """Get aggregated usage statistics."""
        return self._usage_tracker.get_summary()

    def _build_cached_system(self, system_prompt: str) -> List[Dict[str, Any]]:
        """Build system content with cache control.

        Per Anthropic docs, cache_control marks content for caching.
        Content before the marker is cached, content after is dynamic.

        Args:
            system_prompt: System prompt text

        Returns:
            List of content blocks with cache control
        """
        if not self.config.enable_prompt_caching:
            return [{"type": "text", "text": system_prompt}]

        return [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    def _build_cached_tools(
        self,
        tools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build tools with cache control on last tool.

        Per Anthropic docs, cache breakpoint should be at end of
        stable prefix. Tools are stable, so cache at end.

        Args:
            tools: Tool definitions

        Returns:
            Tools with cache control on last item
        """
        if not tools or not self.config.enable_prompt_caching:
            return tools

        # Copy tools, add cache_control to last one
        cached_tools = [dict(tool) for tool in tools]
        cached_tools[-1]["cache_control"] = {"type": "ephemeral"}
        return cached_tools

    async def _execute_with_retry(
        self,
        model: str,
        system: List[Dict[str, Any]],
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        max_tokens: int,
        temperature: float,
        timeout: int,
    ) -> anthropic.types.Message:
        """Execute with retry for transient errors.

        Per 05.2-CONTEXT.md hybrid retry strategy:
        - Retry: rate limits, connection errors, timeouts
        - Fail fast: auth errors, bad requests

        Args:
            model: Model identifier
            system: System content blocks
            messages: Conversation messages
            tools: Tool definitions
            max_tokens: Maximum output tokens
            temperature: Sampling temperature
            timeout: Timeout in seconds

        Returns:
            Anthropic Message response

        Raises:
            RuntimeError: On permanent errors
            TimeoutError: When timeout exceeded
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                # Build request kwargs
                kwargs: Dict[str, Any] = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system,
                    "messages": messages,
                }

                if tools:
                    kwargs["tools"] = tools

                # Execute with timeout
                response = await asyncio.wait_for(
                    self.client.messages.create(**kwargs),
                    timeout=timeout,
                )
                return response

            except AuthenticationError as e:
                # Permanent error - fail fast
                logger.error(f"Authentication error: {e}")
                raise RuntimeError(f"Anthropic authentication failed: {e}") from e

            except (RateLimitError, APIConnectionError) as e:
                # Transient error - retry with backoff
                last_error = e
                if attempt < self.config.max_retries:
                    backoff = self.config.retry_backoff_base ** attempt
                    logger.warning(
                        f"Transient error (attempt {attempt + 1}), "
                        f"retrying in {backoff}s: {e}"
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(f"Max retries exceeded: {e}")

            except asyncio.TimeoutError as e:
                # Timeout - retry or fail
                last_error = e
                if attempt < self.config.max_retries:
                    logger.warning(
                        f"Timeout (attempt {attempt + 1}), retrying..."
                    )
                else:
                    raise TimeoutError(
                        f"Execution timed out after {timeout}s"
                    ) from e

            except APIError as e:
                # Other API errors - check if transient
                if e.status_code and e.status_code >= 500:
                    # Server error - retry
                    last_error = e
                    if attempt < self.config.max_retries:
                        backoff = self.config.retry_backoff_base ** attempt
                        logger.warning(
                            f"Server error (attempt {attempt + 1}), "
                            f"retrying in {backoff}s: {e}"
                        )
                        await asyncio.sleep(backoff)
                else:
                    # Client error - fail fast
                    logger.error(f"API error: {e}")
                    raise RuntimeError(f"Anthropic API error: {e}") from e

        # All retries exhausted
        raise RuntimeError(f"Max retries exceeded: {last_error}") from last_error

    def _parse_response(
        self,
        response: anthropic.types.Message,
        model: str,
        latency_ms: int,
    ) -> AgentResponse:
        """Parse Anthropic response to AgentResponse.

        Extracts content, tool calls, and usage metrics.

        Args:
            response: Anthropic Message response
            model: Model identifier
            latency_ms: Response latency

        Returns:
            Standardized AgentResponse
        """
        # Extract content and tool calls
        content = ""
        tool_calls: List[Dict[str, Any]] = []

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        # Extract token usage
        usage = response.usage
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens

        # Cache tokens (if available)
        cache_read_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_write_tokens = getattr(usage, "cache_creation_input_tokens", 0) or 0

        # Calculate cost
        cost_usd = calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
        )

        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
            model=model,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            metadata={
                "stop_reason": response.stop_reason,
                "model": response.model,
            },
        )
