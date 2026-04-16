"""Runtime Configuration and Role-to-Model Mapping.

This module provides:
- Role-to-model mapping for different SDKs
- Model pricing for cost calculation
- Runtime configuration options

Per 05.2-CONTEXT.md and TOKEN-EFFICIENCY-RESEARCH.md:
- Attacker/Verifier: Opus (deep reasoning required)
- Defender: Sonnet (fast guard detection)
- Test Builder: Sonnet (code generation strength)
- Supervisor/Integrator: Sonnet (orchestration)

Usage:
    from alphaswarm_sol.agents.runtime.config import ROLE_MODEL_MAP, RuntimeConfig

    model = ROLE_MODEL_MAP[AgentRole.ATTACKER]["anthropic"]
    # Returns: "claude-opus-4-20250514"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .base import AgentRole


# Role-to-model mapping per 05.2-CONTEXT.md
# Maps each role to the optimal model for that task
ROLE_MODEL_MAP: Dict[AgentRole, Dict[str, str]] = {
    # Attacker: Deep exploit reasoning - needs Opus/o3
    AgentRole.ATTACKER: {
        "anthropic": "claude-opus-4-20250514",
        "openai": "o3",
    },
    # Defender: Fast guard detection - Sonnet/gpt-4.1 sufficient
    AgentRole.DEFENDER: {
        "anthropic": "claude-sonnet-4-20250514",
        "openai": "gpt-4.1",
    },
    # Verifier: Critical accuracy for evidence cross-check
    AgentRole.VERIFIER: {
        "anthropic": "claude-opus-4-20250514",
        "openai": "o3",
    },
    # Test Builder: Code generation strength
    AgentRole.TEST_BUILDER: {
        "anthropic": "claude-sonnet-4-20250514",
        "openai": "gpt-4.1",
    },
    # Supervisor: Orchestration, balanced cost/quality
    AgentRole.SUPERVISOR: {
        "anthropic": "claude-sonnet-4-20250514",
        "openai": "gpt-4.1",
    },
    # Integrator: Merging verdicts, summarization
    AgentRole.INTEGRATOR: {
        "anthropic": "claude-sonnet-4-20250514",
        "openai": "gpt-4.1",
    },
}


# Model pricing per million tokens (as of January 2026)
# Used for cost estimation and tracking
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # Anthropic models
    "claude-opus-4-20250514": {
        "input": 15.0,
        "output": 75.0,
        "cache_read": 1.5,  # 90% discount on cache reads
        "cache_write": 18.75,  # 25% premium on cache writes
    },
    "claude-sonnet-4-20250514": {
        "input": 3.0,
        "output": 15.0,
        "cache_read": 0.3,
        "cache_write": 3.75,
    },
    "claude-haiku-4-20250514": {
        "input": 0.25,
        "output": 1.25,
        "cache_read": 0.025,
        "cache_write": 0.3125,
    },
    # OpenAI models
    "o3": {
        "input": 10.0,
        "output": 40.0,
        "cache_read": 2.5,
        "cache_write": 10.0,
    },
    "gpt-4.1": {
        "input": 2.5,
        "output": 10.0,
        "cache_read": 1.25,
        "cache_write": 2.5,
    },
    "gpt-4o": {
        "input": 2.5,
        "output": 10.0,
        "cache_read": 1.25,
        "cache_write": 2.5,
    },
}


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    """Calculate cost in USD for token usage.

    Args:
        model: Model identifier
        input_tokens: Number of input tokens (non-cached)
        output_tokens: Number of output tokens
        cache_read_tokens: Tokens read from cache
        cache_write_tokens: Tokens written to cache

    Returns:
        Cost in USD
    """
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        # Fall back to rough estimate if model not found
        return (input_tokens * 5.0 + output_tokens * 15.0) / 1_000_000

    # Calculate each component
    input_cost = (input_tokens - cache_read_tokens) * pricing["input"] / 1_000_000
    output_cost = output_tokens * pricing["output"] / 1_000_000
    cache_read_cost = cache_read_tokens * pricing["cache_read"] / 1_000_000
    cache_write_cost = cache_write_tokens * pricing.get("cache_write", pricing["input"] * 1.25) / 1_000_000

    return input_cost + output_cost + cache_read_cost + cache_write_cost


@dataclass
class RuntimeConfig:
    """Configuration for agent runtime behavior.

    Attributes:
        preferred_sdk: Which SDK to use by default ("anthropic" or "openai")
        enable_prompt_caching: Enable prompt caching for Anthropic
        enable_cost_tracking: Track token costs
        max_retries: Maximum retries for transient errors
        retry_backoff_base: Base for exponential backoff (seconds)
        timeout_seconds: Default timeout for agent execution
        log_level: Logging level for runtime operations
        custom_model_map: Override default role-to-model mapping

    Example:
        config = RuntimeConfig(
            preferred_sdk="anthropic",
            enable_prompt_caching=True,
            max_retries=3,
        )
        runtime = AnthropicRuntime(config)
    """
    preferred_sdk: str = "anthropic"
    enable_prompt_caching: bool = True
    enable_cost_tracking: bool = True
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    timeout_seconds: int = 300
    log_level: str = "INFO"
    custom_model_map: Dict[AgentRole, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration."""
        if self.preferred_sdk not in ("anthropic", "openai"):
            raise ValueError(f"Invalid SDK: {self.preferred_sdk}. Must be 'anthropic' or 'openai'")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.retry_backoff_base <= 0:
            raise ValueError("retry_backoff_base must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    def get_model_for_role(self, role: AgentRole) -> str:
        """Get model for role, respecting custom overrides.

        Args:
            role: Agent role

        Returns:
            Model identifier
        """
        # Check for custom override first
        if role in self.custom_model_map:
            return self.custom_model_map[role]

        # Use default mapping for preferred SDK
        return ROLE_MODEL_MAP[role][self.preferred_sdk]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "preferred_sdk": self.preferred_sdk,
            "enable_prompt_caching": self.enable_prompt_caching,
            "enable_cost_tracking": self.enable_cost_tracking,
            "max_retries": self.max_retries,
            "retry_backoff_base": self.retry_backoff_base,
            "timeout_seconds": self.timeout_seconds,
            "log_level": self.log_level,
            "custom_model_map": {
                role.value: model for role, model in self.custom_model_map.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeConfig":
        """Create from dictionary."""
        custom_map = {}
        if "custom_model_map" in data:
            custom_map = {
                AgentRole(role): model
                for role, model in data["custom_model_map"].items()
            }

        return cls(
            preferred_sdk=data.get("preferred_sdk", "anthropic"),
            enable_prompt_caching=data.get("enable_prompt_caching", True),
            enable_cost_tracking=data.get("enable_cost_tracking", True),
            max_retries=data.get("max_retries", 3),
            retry_backoff_base=data.get("retry_backoff_base", 2.0),
            timeout_seconds=data.get("timeout_seconds", 300),
            log_level=data.get("log_level", "INFO"),
            custom_model_map=custom_map,
        )
