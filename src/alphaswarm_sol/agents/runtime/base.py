"""Agent Runtime Base Classes.

This module defines the core abstractions for multi-SDK agent execution:
- AgentRole: Enumeration of agent roles in the verification pipeline
- AgentConfig: Configuration for agent execution
- AgentResponse: Standardized response from agent execution
- AgentRuntime: Abstract base class for SDK-specific implementations

The runtime abstraction enables:
- Multi-SDK parallel execution (Anthropic, OpenAI)
- Role-based model routing (Opus for attacker, Sonnet for defender)
- Unified response format with token/cache tracking
- Context-fresh agent spawning per PHILOSOPHY.md

Usage:
    from alphaswarm_sol.agents.runtime import (
        AgentRuntime, AgentConfig, AgentResponse, AgentRole
    )

    config = AgentConfig(
        role=AgentRole.ATTACKER,
        system_prompt="You are a security expert...",
        tools=[],
    )
    response = await runtime.execute(config, messages)
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentRole(str, Enum):
    """Agent roles in the multi-agent verification pipeline.

    Per PHILOSOPHY.md Pillar 4 and 05.2-CONTEXT.md, different roles
    are assigned to different models for optimal cost/quality tradeoff.

    Roles:
        ATTACKER: Constructs exploit paths, requires deep reasoning (Opus/o3)
        DEFENDER: Detects guards and mitigations, needs speed (Sonnet/gpt-4.1)
        VERIFIER: Cross-checks evidence, requires accuracy (Opus/o3)
        TEST_BUILDER: Generates exploit tests, code generation (Sonnet/gpt-4.1)
        SUPERVISOR: Orchestrates multi-agent workflows (Sonnet/gpt-4.1)
        INTEGRATOR: Merges verdicts, summarizes (Sonnet/gpt-4.1)
    """
    ATTACKER = "attacker"
    DEFENDER = "defender"
    VERIFIER = "verifier"
    TEST_BUILDER = "test_builder"
    SUPERVISOR = "supervisor"
    INTEGRATOR = "integrator"


@dataclass
class AgentRetryConfig:
    """Configuration for agent retry with exponential backoff.

    Phase 07.1.1-02: Bounded retry configuration for agent execution.

    Attributes:
        max_retries: Maximum retry attempts (0 = no retries)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        jitter: Random jitter fraction (0-1)
        retryable_errors: Error patterns indicating transient failures
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: float = 0.25
    retryable_errors: tuple = (
        "timeout",
        "rate_limit",
        "overloaded",
        "503",
        "429",
        "connection",
        "temporary",
    )

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        import random
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        if self.jitter > 0:
            delay += delay * self.jitter * random.random()
        return delay

    def is_retryable(self, error: str) -> bool:
        """Check if error is transient and worth retrying."""
        error_lower = error.lower()
        return any(pattern in error_lower for pattern in self.retryable_errors)


@dataclass
class AgentConfig:
    """Configuration for agent execution.

    Attributes:
        role: The agent's role determining model selection
        system_prompt: System prompt defining agent behavior
        tools: Tool definitions in SDK-agnostic format
        max_tokens: Maximum tokens for response
        temperature: Sampling temperature (lower = more deterministic)
        timeout_seconds: Timeout for agent execution
        idempotency_key: Optional key for idempotent execution (Phase 07.1.1-02)
        retry_config: Optional retry configuration (Phase 07.1.1-02)
        workdir: Optional working directory for isolated execution (Phase 07.1.1-05)
        metadata: Additional metadata for tracking/debugging

    The same AgentConfig works across SDKs - runtime implementations
    convert tools to SDK-specific format as needed.

    Phase 07.3.1.9: workdir enables workspace isolation - when set,
    the runtime should execute the agent in that directory (uses jj workspaces).
    """
    role: AgentRole
    system_prompt: str
    tools: List[Dict[str, Any]] = field(default_factory=list)
    max_tokens: int = 8192
    temperature: float = 0.1
    timeout_seconds: int = 300
    idempotency_key: Optional[str] = None
    retry_config: Optional[AgentRetryConfig] = None
    workdir: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "role": self.role.value,
            "system_prompt": self.system_prompt,
            "tools": self.tools,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout_seconds": self.timeout_seconds,
            "idempotency_key": self.idempotency_key,
            "workdir": self.workdir,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        """Create from dictionary."""
        return cls(
            role=AgentRole(data["role"]),
            system_prompt=data["system_prompt"],
            tools=data.get("tools", []),
            max_tokens=data.get("max_tokens", 8192),
            temperature=data.get("temperature", 0.1),
            timeout_seconds=data.get("timeout_seconds", 300),
            idempotency_key=data.get("idempotency_key"),
            workdir=data.get("workdir"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AgentResponse:
    """Standardized response from agent execution.

    Attributes:
        content: Text content of the response
        tool_calls: List of tool invocations
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated
        cache_read_tokens: Tokens read from cache (Anthropic prompt caching)
        cache_write_tokens: Tokens written to cache
        model: Model identifier used for this response
        latency_ms: Time taken for the response in milliseconds
        cost_usd: Estimated cost in USD
        metadata: Additional response metadata

    This unified format allows comparison across SDKs and
    aggregation of token usage for cost tracking.
    """
    content: str
    tool_calls: List[Dict[str, Any]]
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    model: str = ""
    latency_ms: int = 0
    cost_usd: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "tool_calls": self.tool_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentResponse":
        """Create from dictionary."""
        return cls(
            content=data.get("content", ""),
            tool_calls=data.get("tool_calls", []),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cache_read_tokens=data.get("cache_read_tokens", 0),
            cache_write_tokens=data.get("cache_write_tokens", 0),
            model=data.get("model", ""),
            latency_ms=data.get("latency_ms", 0),
            cost_usd=data.get("cost_usd", 0.0),
            metadata=data.get("metadata", {}),
        )

    @property
    def total_tokens(self) -> int:
        """Total tokens used (input + output)."""
        return self.input_tokens + self.output_tokens

    @property
    def cache_hit_ratio(self) -> float:
        """Ratio of cached reads to total input tokens."""
        if self.input_tokens == 0:
            return 0.0
        return self.cache_read_tokens / self.input_tokens


class UsageTracker:
    """Track token usage and costs across multiple requests.

    Aggregates usage statistics for cost monitoring and reporting.
    """

    def __init__(self):
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_cache_read_tokens: int = 0
        self.total_cache_write_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.request_count: int = 0
        self._model_usage: Dict[str, Dict[str, Any]] = {}

    def track(self, response: AgentResponse) -> None:
        """Track usage from a response."""
        self.total_input_tokens += response.input_tokens
        self.total_output_tokens += response.output_tokens
        self.total_cache_read_tokens += response.cache_read_tokens
        self.total_cache_write_tokens += response.cache_write_tokens
        self.total_cost_usd += response.cost_usd
        self.request_count += 1

        # Per-model tracking
        if response.model:
            if response.model not in self._model_usage:
                self._model_usage[response.model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "count": 0,
                }
            self._model_usage[response.model]["input_tokens"] += response.input_tokens
            self._model_usage[response.model]["output_tokens"] += response.output_tokens
            self._model_usage[response.model]["cost_usd"] += response.cost_usd
            self._model_usage[response.model]["count"] += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get usage summary."""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cache_read_tokens": self.total_cache_read_tokens,
            "total_cache_write_tokens": self.total_cache_write_tokens,
            "total_cost_usd": self.total_cost_usd,
            "request_count": self.request_count,
            "by_model": self._model_usage,
            "cache_savings_ratio": (
                self.total_cache_read_tokens / self.total_input_tokens
                if self.total_input_tokens > 0
                else 0.0
            ),
        }

    def reset(self) -> None:
        """Reset all counters."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cache_read_tokens = 0
        self.total_cache_write_tokens = 0
        self.total_cost_usd = 0.0
        self.request_count = 0
        self._model_usage = {}


class AgentRuntime(ABC):
    """Abstract base class for agent runtime implementations.

    The AgentRuntime provides a unified interface for executing agents
    across different SDKs (Anthropic, OpenAI Agents SDK). Each implementation
    handles SDK-specific details while exposing a consistent API.

    Per PHILOSOPHY.md and 05.2-CONTEXT.md:
    - Role-based model routing: get_model_for_role() maps roles to optimal models
    - Context-fresh spawning: spawn_agent() creates isolated agent instances
    - Unified response format: AgentResponse works across SDKs
    - Cost tracking: UsageTracker aggregates token usage

    Subclasses must implement:
    - execute(): Run agent with messages
    - spawn_agent(): Create context-fresh agent for a single task
    - get_model_for_role(): Return model name for a given role
    """

    @abstractmethod
    async def execute(
        self,
        config: AgentConfig,
        messages: List[Dict[str, Any]],
    ) -> AgentResponse:
        """Execute an agent with the given configuration and messages.

        Args:
            config: Agent configuration (role, system prompt, tools)
            messages: Conversation messages in OpenAI format
                      [{"role": "user", "content": "..."}, ...]

        Returns:
            AgentResponse with content, tool calls, and usage metrics

        Raises:
            RuntimeError: On permanent errors (auth, bad request)
            TimeoutError: When execution exceeds timeout
        """
        pass

    @abstractmethod
    async def spawn_agent(
        self,
        config: AgentConfig,
        task: str,
    ) -> AgentResponse:
        """Spawn a context-fresh agent for a single task.

        Creates a new agent instance with clean context - no memory
        from previous invocations. Per PHILOSOPHY.md preference for
        isolated agent execution.

        Args:
            config: Agent configuration (role, system prompt, tools)
            task: The task description for the agent

        Returns:
            AgentResponse with the agent's response

        Raises:
            RuntimeError: On permanent errors
            TimeoutError: When execution exceeds timeout
        """
        pass

    @abstractmethod
    def get_model_for_role(self, role: AgentRole) -> str:
        """Get the model name to use for a given role.

        Per 05.2-CONTEXT.md role-to-model mapping:
        - Attacker/Verifier: Opus (deep reasoning)
        - Defender/Test Builder: Sonnet (fast, code generation)
        - Supervisor/Integrator: Sonnet (orchestration)

        Args:
            role: The agent role

        Returns:
            Model identifier string (e.g., "claude-opus-4-20250514")
        """
        pass

    @abstractmethod
    def get_usage(self) -> Dict[str, Any]:
        """Get aggregated usage statistics.

        Returns:
            Dictionary with token counts, costs, and per-model breakdown
        """
        pass

    async def spawn_idempotent(
        self,
        config: AgentConfig,
        task: str,
        pool_path: "Path",
    ) -> AgentResponse:
        """Spawn agent with idempotency and retry support.

        Phase 07.1.1-02: Idempotent agent execution with bounded retry.

        If the idempotency key has a cached result, returns it without
        re-executing. Otherwise reserves the key, executes with retries,
        and records the result.

        Args:
            config: Agent configuration with idempotency_key set
            task: The task description for the agent
            pool_path: Path to pool directory for idempotency storage

        Returns:
            AgentResponse from cache or fresh execution

        Raises:
            ValueError: If idempotency_key not set in config
            RuntimeError: If key reservation fails
        """
        from pathlib import Path as PathClass
        from alphaswarm_sol.orchestration.idempotency import IdempotencyStore

        if not config.idempotency_key:
            raise ValueError("idempotency_key must be set in config for idempotent spawn")

        pool_path = PathClass(pool_path)
        store = IdempotencyStore(pool_path)
        key = config.idempotency_key
        retry_config = config.retry_config or AgentRetryConfig()

        # Check for cached result
        existing = store.get(key)
        if existing and existing.is_complete and existing.result is not None:
            cached = existing.result
            if isinstance(cached, dict):
                return AgentResponse.from_dict(cached)
            return cached

        # Reserve key
        if not store.reserve(key, metadata={"role": config.role.value, "task": task[:100]}):
            existing = store.get(key)
            if existing and existing.is_complete and existing.result is not None:
                cached = existing.result
                if isinstance(cached, dict):
                    return AgentResponse.from_dict(cached)
                return cached
            raise RuntimeError(f"Failed to reserve idempotency key {key}")

        # Execute with bounded retries
        import asyncio
        last_error: Optional[Exception] = None
        attempt = 0

        while attempt <= retry_config.max_retries:
            try:
                response = await self.spawn_agent(config, task)
                store.record_success(key, response.to_dict())
                return response

            except Exception as e:
                last_error = e
                error_str = str(e)

                # Check if retryable
                if not retry_config.is_retryable(error_str):
                    store.record_failure(key, error_str, permanent=True)
                    raise

                # Check if retries exhausted
                if attempt >= retry_config.max_retries:
                    store.record_failure(key, error_str, permanent=True)
                    raise

                # Record transient failure
                store.record_failure(key, error_str, permanent=False)

                # Delay with jitter
                delay = retry_config.calculate_delay(attempt)
                await asyncio.sleep(delay)
                attempt += 1

                # Re-reserve
                store.reserve(key)

        if last_error:
            raise last_error
        raise RuntimeError(f"Unexpected state in spawn_idempotent for key {key}")
