"""Runtime Factory for Multi-SDK Support.

This module provides a unified factory function for creating the appropriate
agent runtime based on configuration. Supports:

- OpenCode SDK (default): Multi-model access via OpenRouter, cost-optimized
- Claude Code CLI: Subscription-based, for critical analysis
- Codex CLI: Subscription-based, for reviews and alternative perspectives
- Anthropic API: Direct API access (legacy, expensive)
- OpenAI API: Direct API access (legacy, expensive)

Per 05.3-CONTEXT.md:
- Default to OpenCode SDK for 75-95% cost reduction
- Legacy API runtimes emit deprecation warnings
- Auto mode defaults to OpenCode

Usage:
    from alphaswarm_sol.agents.runtime.factory import create_runtime, RuntimeType

    # Create default runtime (OpenCode)
    runtime = create_runtime()

    # Create specific runtime
    runtime = create_runtime(sdk="claude_code")

    # Using enum
    runtime = create_runtime(sdk=RuntimeType.CODEX)
"""

from __future__ import annotations

import logging
import shutil
import warnings
from enum import Enum
from typing import Any, List, Optional, Union

from .base import AgentRuntime

logger = logging.getLogger(__name__)


class RuntimeType(str, Enum):
    """Runtime type enumeration for SDK selection.

    Values:
        OPENCODE: OpenCode SDK with multi-model support (default, cost-optimized)
        CLAUDE_CODE: Claude Code CLI (subscription, for critical analysis)
        CODEX: Codex CLI (subscription, for reviews/discussion)
        ANTHROPIC: Anthropic API (expensive, legacy - emits deprecation warning)
        OPENAI: OpenAI API (expensive, legacy - emits deprecation warning)
        AUTO: Smart routing - defaults to opencode

    Note:
        String values allow direct string comparison and serialization.
    """
    OPENCODE = "opencode"
    CLAUDE_CODE = "claude_code"
    CODEX = "codex"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    AUTO = "auto"


# CLI executables for availability checking
_CLI_EXECUTABLES = {
    RuntimeType.OPENCODE: "opencode",
    RuntimeType.CLAUDE_CODE: "claude",
    RuntimeType.CODEX: "codex",
}


def is_runtime_available(sdk: Union[str, RuntimeType]) -> bool:
    """Check if a runtime is available on the system.

    For CLI-based runtimes (opencode, claude_code, codex), checks if the
    CLI executable is installed. For API-based runtimes (anthropic, openai),
    checks if the SDK package is installed.

    Args:
        sdk: Runtime type to check

    Returns:
        True if runtime is available, False otherwise

    Example:
        >>> is_runtime_available("opencode")
        True
        >>> is_runtime_available(RuntimeType.CLAUDE_CODE)
        False  # If not installed
    """
    # Normalize to RuntimeType
    if isinstance(sdk, str):
        try:
            sdk = RuntimeType(sdk.lower())
        except ValueError:
            return False

    # Check CLI-based runtimes
    if sdk in _CLI_EXECUTABLES:
        executable = _CLI_EXECUTABLES[sdk]
        return shutil.which(executable) is not None

    # Check API-based runtimes
    if sdk == RuntimeType.ANTHROPIC:
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False

    if sdk == RuntimeType.OPENAI:
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            return False

    # AUTO - check if any runtime is available
    if sdk == RuntimeType.AUTO:
        return any(
            is_runtime_available(rt)
            for rt in [RuntimeType.OPENCODE, RuntimeType.CLAUDE_CODE, RuntimeType.CODEX]
        )

    return False


def get_available_runtimes() -> List[str]:
    """Get list of available runtime types.

    Checks all known runtimes and returns those that are available
    on the current system.

    Returns:
        List of available runtime type names

    Example:
        >>> get_available_runtimes()
        ['opencode', 'anthropic']
    """
    available = []
    for rt in RuntimeType:
        if rt == RuntimeType.AUTO:
            continue  # Skip AUTO, it's a meta-type
        if is_runtime_available(rt):
            available.append(rt.value)
    return available


def create_runtime(
    sdk: Union[str, RuntimeType] = "auto",
    config: Any = None,
    **kwargs: Any,
) -> AgentRuntime:
    """Create appropriate runtime based on configuration.

    Factory function that creates the appropriate runtime based on the
    sdk parameter. Defaults to OpenCode for cost optimization.

    Args:
        sdk: Runtime type - "opencode", "claude_code", "codex",
             "anthropic", "openai", or "auto"
        config: Runtime-specific configuration object. Type depends on sdk:
            - opencode: OpenCodeConfig
            - claude_code: ClaudeCodeConfig
            - codex: CodexCLIConfig
            - anthropic: RuntimeConfig
            - openai: RuntimeConfig
        **kwargs: Additional arguments passed to runtime constructor

    Returns:
        AgentRuntime instance

    Raises:
        ValueError: If sdk is not recognized
        RuntimeError: If the requested runtime is not available

    SDK Selection:
        - "opencode": OpenCode SDK with multi-model support (default, cost-optimized)
        - "claude_code": Claude Code CLI (subscription, for critical analysis)
        - "codex": Codex CLI (subscription, for reviews/discussion)
        - "anthropic": Anthropic API (expensive, legacy - emits deprecation warning)
        - "openai": OpenAI API (expensive, legacy - emits deprecation warning)
        - "auto": Smart routing - defaults to opencode

    Example:
        # Default - OpenCode
        runtime = create_runtime()

        # Specific runtime
        runtime = create_runtime("claude_code")

        # With configuration
        from alphaswarm_sol.agents.runtime.opencode import OpenCodeConfig
        config = OpenCodeConfig(default_model="deepseek/deepseek-v3.2")
        runtime = create_runtime("opencode", config=config)

        # Legacy API (with deprecation warning)
        runtime = create_runtime("anthropic")  # Warning emitted
    """
    # Normalize sdk to RuntimeType
    if isinstance(sdk, str):
        try:
            sdk_type = RuntimeType(sdk.lower())
        except ValueError:
            raise ValueError(
                f"Unknown SDK: {sdk}. Must be one of: "
                f"{', '.join(rt.value for rt in RuntimeType)}"
            )
    else:
        sdk_type = sdk

    # Handle AUTO - default to OpenCode
    if sdk_type == RuntimeType.AUTO:
        sdk_type = RuntimeType.OPENCODE
        logger.debug("Auto-selecting OpenCode runtime (cost-optimized default)")

    # Create appropriate runtime with lazy imports
    if sdk_type == RuntimeType.OPENCODE:
        from .opencode import OpenCodeRuntime, OpenCodeConfig

        if config is None:
            config = OpenCodeConfig()
        elif not isinstance(config, OpenCodeConfig):
            logger.warning(
                f"Config type mismatch: expected OpenCodeConfig, got {type(config).__name__}. "
                "Using default OpenCodeConfig."
            )
            config = OpenCodeConfig()
        return OpenCodeRuntime(config, **kwargs)

    elif sdk_type == RuntimeType.CLAUDE_CODE:
        from .claude_code import ClaudeCodeRuntime, ClaudeCodeConfig

        if config is None:
            config = ClaudeCodeConfig()
        elif not isinstance(config, ClaudeCodeConfig):
            logger.warning(
                f"Config type mismatch: expected ClaudeCodeConfig, got {type(config).__name__}. "
                "Using default ClaudeCodeConfig."
            )
            config = ClaudeCodeConfig()
        return ClaudeCodeRuntime(config, **kwargs)

    elif sdk_type == RuntimeType.CODEX:
        from .codex_cli import CodexCLIRuntime, CodexCLIConfig

        if config is None:
            config = CodexCLIConfig()
        elif not isinstance(config, CodexCLIConfig):
            logger.warning(
                f"Config type mismatch: expected CodexCLIConfig, got {type(config).__name__}. "
                "Using default CodexCLIConfig."
            )
            config = CodexCLIConfig()
        return CodexCLIRuntime(config, **kwargs)

    elif sdk_type == RuntimeType.ANTHROPIC:
        # Emit deprecation warning for legacy API
        warnings.warn(
            "Anthropic API runtime is expensive and deprecated in favor of CLI-based runtimes. "
            "Consider using 'opencode' (75-95% cost reduction) or 'claude_code' (subscription). "
            "This warning will become an error in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
        from .anthropic import AnthropicRuntime
        from .config import RuntimeConfig

        if config is None:
            config = RuntimeConfig(preferred_sdk="anthropic")
        elif not isinstance(config, RuntimeConfig):
            logger.warning(
                f"Config type mismatch: expected RuntimeConfig, got {type(config).__name__}. "
                "Using default RuntimeConfig."
            )
            config = RuntimeConfig(preferred_sdk="anthropic")
        return AnthropicRuntime(config, **kwargs)

    elif sdk_type == RuntimeType.OPENAI:
        # Emit deprecation warning for legacy API
        warnings.warn(
            "OpenAI API runtime is expensive and deprecated in favor of CLI-based runtimes. "
            "Consider using 'opencode' (75-95% cost reduction) or 'codex' (subscription). "
            "This warning will become an error in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
        from .openai_agents import OpenAIAgentsRuntime
        from .config import RuntimeConfig

        if config is None:
            config = RuntimeConfig(preferred_sdk="openai")
        elif not isinstance(config, RuntimeConfig):
            logger.warning(
                f"Config type mismatch: expected RuntimeConfig, got {type(config).__name__}. "
                "Using default RuntimeConfig."
            )
            config = RuntimeConfig(preferred_sdk="openai")
        return OpenAIAgentsRuntime(config, **kwargs)

    # Should not reach here due to enum validation, but just in case
    raise ValueError(f"Unknown SDK type: {sdk_type}")


__all__ = [
    "RuntimeType",
    "create_runtime",
    "get_available_runtimes",
    "is_runtime_available",
]
