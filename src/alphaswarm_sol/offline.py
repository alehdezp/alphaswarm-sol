"""
Offline Mode Support

Tier A (graph building and pattern matching) works fully offline.
Tier B (LLM analysis) requires network.

Usage:
    VKG_OFFLINE=1 vkg build-kg ...  # Works
    VKG_OFFLINE=1 vkg analyze --tier-b  # Fails gracefully

Integration with Tier System:
    - Offline mode forces CORE tier only
    - Online mode uses AvailabilityChecker to determine effective tier
"""

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.core.tiers import Tier


def is_offline_mode() -> bool:
    """Check if VKG is running in offline mode."""
    return os.environ.get("VKG_OFFLINE", "").lower() in ("1", "true", "yes")


def require_network(operation: str) -> None:
    """
    Raise error if network is required but offline mode is enabled.

    Args:
        operation: Name of the operation requiring network (for error message)

    Raises:
        RuntimeError: If offline mode is enabled
    """
    if is_offline_mode():
        raise RuntimeError(
            f"Operation '{operation}' requires network access, "
            f"but VKG_OFFLINE is set. Unset VKG_OFFLINE to use this feature."
        )


def offline_capable(func):
    """
    Decorator marking a function as offline-capable.

    This is documentation - the function works without network.
    """
    func._offline_capable = True
    return func


def requires_network(func):
    """
    Decorator marking a function as requiring network.

    Will raise error if called in offline mode.
    """
    def wrapper(*args, **kwargs):
        require_network(func.__name__)
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper._requires_network = True
    return wrapper


# Tier capabilities
TIER_A_CAPABILITIES = [
    "build-kg",
    "query",
    "lens-report",
    "pattern matching",
    "graph fingerprinting",
]

TIER_B_CAPABILITIES = [
    "LLM analysis",
    "intent annotation",
    "false positive filtering",
    "natural language queries",
]


def get_current_tier() -> "Tier":
    """
    Get current operation tier based on mode and availability.

    In offline mode, forces CORE tier.
    In online mode, uses AvailabilityChecker to determine effective tier.

    Returns:
        Tier: The current effective operation tier
    """
    from alphaswarm_sol.core.tiers import Tier
    from alphaswarm_sol.core.availability import AvailabilityChecker

    if is_offline_mode():
        return Tier.CORE  # Offline = core only

    checker = AvailabilityChecker()
    try:
        return checker.get_effective_tier(raise_on_critical=False)
    except RuntimeError:
        return Tier.CORE


def can_use_tier_b() -> bool:
    """
    Check if Tier B (LLM) functionality is available.

    Returns:
        True if Tier B is available (not offline and LLM configured)
    """
    if is_offline_mode():
        return False

    from alphaswarm_sol.core.availability import AvailabilityChecker

    checker = AvailabilityChecker()
    return checker.check_dependency("llm_provider")
