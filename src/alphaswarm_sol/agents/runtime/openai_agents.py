"""OpenAI Agents SDK Runtime Implementation.

This module provides the OpenAI Agents SDK implementation of AgentRuntime with:
- Role-based model selection (o3 for deep reasoning, gpt-4.1 for fast tasks)
- Tool conversion from Anthropic format to OpenAI format
- Retry with exponential backoff for transient errors
- Cost and token tracking

Per 05.2-CONTEXT.md:
- OpenAI automatic caching for prompts >1024 tokens
- Organization-scoped cache sharing
- Full parity with Anthropic runtime for same AgentConfig

Usage:
    from alphaswarm_sol.agents.runtime import OpenAIAgentsRuntime, RuntimeConfig

    config = RuntimeConfig(preferred_sdk="openai")
    runtime = OpenAIAgentsRuntime(config)

    response = await runtime.execute(agent_config, messages)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional, Awaitable

from agents import Agent, Runner, FunctionTool, RunConfig, Usage
from agents.exceptions import AgentsException, MaxTurnsExceeded, UserError
from openai import AuthenticationError, RateLimitError, APIConnectionError, APIError

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


class OpenAIAgentsRuntime(AgentRuntime):
    """OpenAI Agents SDK implementation of AgentRuntime.

    Features:
    - Agent-based execution with Runner.run()
    - Role-based model selection from ROLE_MODEL_MAP
    - Tool conversion from Anthropic format
    - Retry with exponential backoff for rate limits
    - Token tracking via Usage dataclass

    Per 05.2-CONTEXT.md:
    - Accept differences between SDKs
    - Per-SDK tool definitions
    - Same AgentConfig/AgentResponse interface
    """

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        api_key: Optional[str] = None,
    ):
        """Initialize OpenAI Agents runtime.

        Args:
            config: Runtime configuration
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.config = config or RuntimeConfig(preferred_sdk="openai")
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._usage_tracker = UsageTracker()

        # Set default API key for agents SDK
        if self._api_key:
            from agents import set_default_openai_key
            set_default_openai_key(self._api_key)

    async def execute(
        self,
        config: AgentConfig,
        messages: List[Dict[str, Any]],
    ) -> AgentResponse:
        """Execute agent using OpenAI Agents SDK Runner.

        Creates an Agent with the configuration and runs it with
        the provided messages. Converts tool definitions from
        Anthropic format to OpenAI format.

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

        # Convert tools to OpenAI Agents SDK format
        tools = self._convert_tools(config.tools) if config.tools else []

        # Create agent
        agent = Agent(
            name=f"vkg-{config.role.value}",
            instructions=config.system_prompt,
            model=model,
            tools=tools,
        )

        # Prepare input from messages
        input_text = self._extract_input_from_messages(messages)

        # Create run config
        run_config = RunConfig(
            max_turns=10,
        )

        # Execute with retry
        result, usage = await self._execute_with_retry(
            agent=agent,
            input_text=input_text,
            run_config=run_config,
            timeout=config.timeout_seconds,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Parse response
        agent_response = self._parse_result(result, usage, model, latency_ms)

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

        Creates a new agent instance with clean context.
        Per PHILOSOPHY.md design goal for isolated execution.

        Args:
            config: Agent configuration
            task: Task description

        Returns:
            AgentResponse with agent's response
        """
        messages = [{"role": "user", "content": task}]
        return await self.execute(config, messages)

    def get_model_for_role(self, role: AgentRole) -> str:
        """Get OpenAI model for role.

        Args:
            role: Agent role

        Returns:
            OpenAI model identifier
        """
        # Check custom override first
        if role in self.config.custom_model_map:
            return self.config.custom_model_map[role]
        return ROLE_MODEL_MAP[role]["openai"]

    def get_usage(self) -> Dict[str, Any]:
        """Get aggregated usage statistics."""
        return self._usage_tracker.get_summary()

    def _convert_tools(
        self,
        tools: List[Dict[str, Any]],
    ) -> List[FunctionTool]:
        """Convert tools from Anthropic format to OpenAI Agents SDK format.

        Anthropic format:
        {
            "name": "get_weather",
            "description": "Get weather for a location",
            "input_schema": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }

        OpenAI Agents SDK uses FunctionTool with params_json_schema.

        Args:
            tools: Tool definitions in Anthropic format

        Returns:
            List of FunctionTool objects
        """
        converted: List[FunctionTool] = []

        for tool in tools:
            name = tool.get("name", "")
            description = tool.get("description", "")

            # Get schema - Anthropic uses "input_schema", OpenAI uses "parameters"
            schema = tool.get("input_schema") or tool.get("parameters", {})

            # Create a placeholder invoke function
            # Real invocations are handled by the runtime
            async def placeholder_invoke(ctx: Any, args: str) -> Any:
                import json
                return {"result": f"Tool {name} called with: {json.loads(args)}"}

            func_tool = FunctionTool(
                name=name,
                description=description,
                params_json_schema=schema,
                on_invoke_tool=placeholder_invoke,
                strict_json_schema=False,  # Allow flexible schemas
            )
            converted.append(func_tool)

        return converted

    def _extract_input_from_messages(
        self,
        messages: List[Dict[str, Any]],
    ) -> str:
        """Extract input text from messages.

        Combines user messages into a single input string.
        The OpenAI Agents SDK expects a string or list of items.

        Args:
            messages: Conversation messages

        Returns:
            Combined input text
        """
        user_messages = []
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    user_messages.append(content)
                elif isinstance(content, list):
                    # Handle content blocks
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            user_messages.append(block.get("text", ""))
                        elif isinstance(block, str):
                            user_messages.append(block)

        return "\n\n".join(user_messages)

    async def _execute_with_retry(
        self,
        agent: Agent,
        input_text: str,
        run_config: RunConfig,
        timeout: int,
    ) -> tuple[Any, Usage]:
        """Execute with retry for transient errors.

        Per 05.2-CONTEXT.md hybrid retry strategy.

        Args:
            agent: Configured Agent
            input_text: Input for the agent
            run_config: Run configuration
            timeout: Timeout in seconds

        Returns:
            Tuple of (RunResult, Usage)

        Raises:
            RuntimeError: On permanent errors
            TimeoutError: When timeout exceeded
        """
        last_error: Optional[Exception] = None
        total_usage = Usage(input_tokens=0, output_tokens=0, requests=0)

        for attempt in range(self.config.max_retries + 1):
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    Runner.run(
                        agent,
                        input_text,
                        run_config=run_config,
                    ),
                    timeout=timeout,
                )

                # Aggregate usage from raw responses
                for response in result.raw_responses:
                    if hasattr(response, "usage") and response.usage:
                        usage = response.usage
                        total_usage.input_tokens += getattr(usage, "input_tokens", 0) or 0
                        total_usage.output_tokens += getattr(usage, "output_tokens", 0) or 0
                        total_usage.requests += 1

                return result, total_usage

            except AuthenticationError as e:
                # Permanent error - fail fast
                logger.error(f"Authentication error: {e}")
                raise RuntimeError(f"OpenAI authentication failed: {e}") from e

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

            except MaxTurnsExceeded as e:
                # Agent exceeded max turns - not retriable
                logger.warning(f"Agent exceeded max turns: {e}")
                raise RuntimeError(f"Agent exceeded maximum turns") from e

            except UserError as e:
                # User error - not retriable
                logger.error(f"User error: {e}")
                raise RuntimeError(f"Agent user error: {e}") from e

            except AgentsException as e:
                # Generic agent error - check if retriable
                last_error = e
                if attempt < self.config.max_retries:
                    backoff = self.config.retry_backoff_base ** attempt
                    logger.warning(
                        f"Agent error (attempt {attempt + 1}), "
                        f"retrying in {backoff}s: {e}"
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(f"Max retries exceeded: {e}")

            except APIError as e:
                # API error - check status
                if hasattr(e, "status_code") and e.status_code and e.status_code >= 500:
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
                    raise RuntimeError(f"OpenAI API error: {e}") from e

        # All retries exhausted
        raise RuntimeError(f"Max retries exceeded: {last_error}") from last_error

    def _parse_result(
        self,
        result: Any,
        usage: Usage,
        model: str,
        latency_ms: int,
    ) -> AgentResponse:
        """Parse RunResult to AgentResponse.

        Extracts content, tool calls, and usage metrics.

        Args:
            result: RunResult from Runner.run()
            usage: Aggregated Usage
            model: Model identifier
            latency_ms: Response latency

        Returns:
            Standardized AgentResponse
        """
        # Extract final output content
        content = ""
        if result.final_output:
            if isinstance(result.final_output, str):
                content = result.final_output
            elif hasattr(result.final_output, "text"):
                content = result.final_output.text
            else:
                content = str(result.final_output)

        # Extract tool calls from new_items
        tool_calls: List[Dict[str, Any]] = []
        for item in result.new_items:
            if hasattr(item, "type") and item.type == "tool_call":
                tool_calls.append({
                    "id": getattr(item, "id", ""),
                    "name": getattr(item, "name", ""),
                    "input": getattr(item, "arguments", {}),
                })

        # Calculate cost
        cost_usd = calculate_cost(
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )

        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=0,  # OpenAI caching is automatic, not tracked
            cache_write_tokens=0,
            model=model,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            metadata={
                "requests": usage.requests,
                "total_tokens": usage.total_tokens,
            },
        )
