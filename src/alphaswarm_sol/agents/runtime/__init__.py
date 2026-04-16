"""Agent Runtime Package.

Multi-SDK agent execution with cost-optimized model routing.

This package provides:
- AgentRuntime: Abstract base class for SDK implementations
- OpenCodeRuntime: Multi-model access via OpenRouter (cost-optimized, default)
- ClaudeCodeRuntime: Claude Code CLI (subscription, critical analysis)
- CodexCLIRuntime: Codex CLI (subscription, reviews/alternative perspectives)
- AnthropicRuntime: Direct Anthropic API (legacy, expensive)
- OpenAIAgentsRuntime: Direct OpenAI API (legacy, expensive)

Cost Comparison (per 1M tokens, typical task):
+----------------+-------------+------------------+-------------------+
| Runtime        | Input Cost  | Output Cost      | Notes             |
+----------------+-------------+------------------+-------------------+
| OpenCode       | $0.00-0.50  | $0.00-3.00       | Free/cheap models |
| Claude Code    | $0 (sub)    | $0 (sub)         | $20-100/month     |
| Codex          | $0 (sub)    | $0 (sub)         | ChatGPT Plus $20  |
| Anthropic API  | $3-15       | $15-75           | Direct API        |
| OpenAI API     | $2.5-10     | $10-40           | Direct API        |
+----------------+-------------+------------------+-------------------+

Usage:
    from alphaswarm_sol.agents.runtime import (
        # Factory (recommended)
        create_runtime,
        RuntimeType,
        # Task types for model routing
        TaskType,
        # Base classes
        AgentRuntime,
        AgentConfig,
        AgentResponse,
        AgentRole,
        UsageTracker,
        # Configuration
        RuntimeConfig,
        # Implementations
        OpenCodeRuntime, OpenCodeConfig,
        ClaudeCodeRuntime, ClaudeCodeConfig,
        CodexCLIRuntime, CodexCLIConfig,
        AnthropicRuntime,  # Legacy
        OpenAIAgentsRuntime,  # Legacy
    )

    # Recommended: Use factory with default (OpenCode)
    runtime = create_runtime()  # Defaults to OpenCode

    # Specify runtime type
    runtime = create_runtime("claude_code")  # Critical analysis
    runtime = create_runtime(RuntimeType.CODEX)  # Reviews

    # Legacy API runtimes (emit deprecation warning)
    runtime = create_runtime("anthropic")  # Warning: expensive

    # Execute agent
    agent_config = AgentConfig(
        role=AgentRole.ATTACKER,
        system_prompt="You are a security expert...",
    )
    response = await runtime.execute(
        agent_config,
        messages=[{"role": "user", "content": "Analyze..."}],
        task_type=TaskType.REASONING,  # OpenCode: model selection
    )
"""

from .base import (
    AgentRole,
    AgentConfig,
    AgentResponse,
    AgentRuntime,
    UsageTracker,
)

from .config import (
    ROLE_MODEL_MAP,
    MODEL_PRICING,
    RuntimeConfig,
    calculate_cost,
)

# New runtimes (Plans 05.3-01, 05.3-02, 05.3-03)
from .opencode import OpenCodeRuntime, OpenCodeConfig
from .claude_code import ClaudeCodeRuntime, ClaudeCodeConfig
from .codex_cli import CodexCLIRuntime, CodexCLIConfig

# Legacy runtimes (still supported with deprecation warning via factory)
from .anthropic import AnthropicRuntime
from .openai_agents import OpenAIAgentsRuntime

# Factory and types (Plan 05.3-04)
from .factory import (
    RuntimeType,
    create_runtime,
    get_available_runtimes,
    is_runtime_available,
)

# Task types for model routing
from .types import (
    TaskType,
    MODEL_PRICING as OPENCODE_MODEL_PRICING,
    MODEL_CONTEXT_LIMITS,
    DEFAULT_MODELS,
    calculate_model_cost,
    get_context_limit,
    is_free_model,
)

# Task router (Plan 05.3-05)
from .router import (
    RoutingPolicy,
    TaskRouter,
    route_to_runtime,
    LARGE_CONTEXT_THRESHOLD,
    HEAVY_CONTEXT_THRESHOLD,
)


# Backward compatibility: old create_runtime signature
# Preserved for existing code using RuntimeConfig(preferred_sdk="...")
def _legacy_create_runtime(config: RuntimeConfig | None = None) -> AgentRuntime:
    """Legacy factory function.

    DEPRECATED: Use create_runtime(sdk=...) instead.

    This function is kept for backward compatibility with code using:
        create_runtime(RuntimeConfig(preferred_sdk="anthropic"))

    Args:
        config: Runtime configuration with preferred_sdk field.

    Returns:
        AgentRuntime instance
    """
    import warnings

    if config is None:
        # No config = use new default (OpenCode)
        return create_runtime()

    # Map old preferred_sdk to new RuntimeType
    sdk_map = {
        "anthropic": RuntimeType.ANTHROPIC,
        "openai": RuntimeType.OPENAI,
    }

    sdk_type = sdk_map.get(config.preferred_sdk)
    if sdk_type:
        warnings.warn(
            f"create_runtime(RuntimeConfig(preferred_sdk='{config.preferred_sdk}')) is deprecated. "
            f"Use create_runtime(sdk='{sdk_type.value}') instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return create_runtime(sdk=sdk_type, config=config)

    # Unknown preferred_sdk - try as runtime type
    return create_runtime(sdk=config.preferred_sdk, config=config)


__all__ = [
    # Base classes
    "AgentRole",
    "AgentConfig",
    "AgentResponse",
    "AgentRuntime",
    "UsageTracker",
    # Configuration
    "ROLE_MODEL_MAP",
    "MODEL_PRICING",
    "RuntimeConfig",
    "calculate_cost",
    # New runtimes (cost-optimized)
    "OpenCodeRuntime",
    "OpenCodeConfig",
    "ClaudeCodeRuntime",
    "ClaudeCodeConfig",
    "CodexCLIRuntime",
    "CodexCLIConfig",
    # Legacy runtimes (API-based, expensive)
    "AnthropicRuntime",
    "OpenAIAgentsRuntime",
    # Factory (recommended entry point)
    "RuntimeType",
    "create_runtime",
    "get_available_runtimes",
    "is_runtime_available",
    # Task types for model routing
    "TaskType",
    "OPENCODE_MODEL_PRICING",
    "MODEL_CONTEXT_LIMITS",
    "DEFAULT_MODELS",
    "calculate_model_cost",
    "get_context_limit",
    "is_free_model",
    # Task router (intelligent routing)
    "RoutingPolicy",
    "TaskRouter",
    "route_to_runtime",
    "LARGE_CONTEXT_THRESHOLD",
    "HEAVY_CONTEXT_THRESHOLD",
]
