"""
Tools Module

Provides isolated tool execution with timeout, error handling, and recovery.
Includes tool registry for discovery, configuration management, coordination,
and parallel execution.
"""

from alphaswarm_sol.tools.config import (
    ConfigManager,
    ToolConfig,
    get_optimal_config,
    load_tool_config,
    merge_configs,
    save_project_config,
)
from alphaswarm_sol.tools.coordinator import (
    ProjectAnalysis,
    ToolCoordinator,
    ToolStrategy,
    analyze_project,
    create_strategy,
)
from alphaswarm_sol.tools.executor import (
    ExecutionResult,
    ToolExecutor,
    execute_strategy,
    execute_tool,
)
from alphaswarm_sol.tools.registry import (
    ModelTier,
    ToolHealth,
    ToolInfo,
    ToolRegistry,
    ToolTier,
    check_all_tools,
    get_available_tools,
    validate_tool_setup,
)
from alphaswarm_sol.tools.runner import (
    ToolResult,
    ToolRunner,
    run_tool_safely,
)
from alphaswarm_sol.tools.timeout import (
    TimeoutError,
    TimeoutManager,
    timeout,
    with_timeout,
)
from alphaswarm_sol.tools.hooks import (
    HookPriority,
    LocalToolHook,
    ToolHook,
    ToolRunRequest,
    ToolRunResult,
    ToolRunStatus,
    get_tool_hook,
    run_tool,
    run_tools_parallel,
    set_tool_hook,
)


__all__ = [
    # Registry
    "ToolRegistry",
    "ToolInfo",
    "ToolHealth",
    "ToolTier",
    "ModelTier",
    "check_all_tools",
    "get_available_tools",
    "validate_tool_setup",
    # Config
    "ToolConfig",
    "ConfigManager",
    "load_tool_config",
    "get_optimal_config",
    "merge_configs",
    "save_project_config",
    # Coordinator
    "ProjectAnalysis",
    "ToolStrategy",
    "ToolCoordinator",
    "analyze_project",
    "create_strategy",
    # Executor
    "ExecutionResult",
    "ToolExecutor",
    "execute_tool",
    "execute_strategy",
    # Runner
    "ToolResult",
    "ToolRunner",
    "run_tool_safely",
    # Timeout
    "TimeoutError",
    "TimeoutManager",
    "timeout",
    "with_timeout",
    # Hooks (Phase 5.2 SDK)
    "HookPriority",
    "ToolRunStatus",
    "ToolRunRequest",
    "ToolRunResult",
    "ToolHook",
    "LocalToolHook",
    "get_tool_hook",
    "set_tool_hook",
    "run_tool",
    "run_tools_parallel",
]
