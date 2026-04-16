"""
Core VKG System Components

Provides dependency management, availability checking, and graceful degradation.
"""

from alphaswarm_sol.core.tiers import (
    Tier,
    Dependency,
    DEPENDENCIES,
    get_available_tiers,
    get_degradation_message,
    get_tier_dependencies,
)
from alphaswarm_sol.core.availability import (
    AvailabilityChecker,
    AvailabilityReport,
    check_all_dependencies,
    get_effective_tier,
)
from alphaswarm_sol.core.tool_registry import (
    ToolInfo,
    ToolRegistry,
    detect_tool,
    detect_all_tools,
)


__all__ = [
    # Tiers
    "Tier",
    "Dependency",
    "DEPENDENCIES",
    "get_available_tiers",
    "get_degradation_message",
    "get_tier_dependencies",
    # Availability
    "AvailabilityChecker",
    "AvailabilityReport",
    "check_all_dependencies",
    "get_effective_tier",
    # Tool Registry
    "ToolInfo",
    "ToolRegistry",
    "detect_tool",
    "detect_all_tools",
]
