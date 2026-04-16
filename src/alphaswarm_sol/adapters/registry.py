"""Adapter Registry for Unified Adapter Management.

Provides centralized registry for adapter discovery, creation, and
capability-based selection. Enables feature-based adapter selection
across all orchestration frameworks.

Key Features:
- Centralized adapter class registration
- Instance caching for performance
- Capability-based adapter discovery
- Capability comparison matrix
- Validation against adapter requirements

Design:
- Registry singleton pattern
- Lazy instance creation with caching
- Capability matrix for comparison
- Auto-registration of built-in adapters

Usage:
    from alphaswarm_sol.adapters import get_adapter, AdapterRegistry
    from alphaswarm_sol.adapters.capability import AdapterCapability

    # Get adapter by name
    adapter = get_adapter("agents-sdk", config)

    # Find adapters with required capabilities
    registry = AdapterRegistry()
    adapters = registry.find_adapter_for_capabilities({
        AdapterCapability.BEAD_REPLAY,
        AdapterCapability.GRAPH_FIRST,
    })

    # Compare capabilities across adapters
    comparison = registry.get_capability_comparison()

Phase: 07.1.4-05 Beads/Gas Town and Claude Code Adapters
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Type

from .base import AdapterConfig, OrchestratorAdapter
from .capability import AdapterCapability

# Import all adapter classes
from .agents_sdk import AgentsSdkAdapter
from .beads_gastown import BeadsGasTownAdapter
from .claude_code import ClaudeCodeAdapter
from .codex_mcp import CodexMcpAdapter

# Conditional imports
try:
    from .langgraph import LangGraphAdapter

    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    LangGraphAdapter = None  # type: ignore

try:
    from .autogen import AutoGenAdapter

    HAS_AUTOGEN = True
except ImportError:
    HAS_AUTOGEN = False
    AutoGenAdapter = None  # type: ignore

try:
    from .crewai import CrewAIAdapter

    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False
    CrewAIAdapter = None  # type: ignore


class AdapterRegistry:
    """Registry for orchestrator adapter management.

    Provides centralized adapter registration, discovery, and capability-based
    selection. Maintains both adapter classes and instance cache.

    Attributes:
        _adapters: Mapping of adapter name to adapter class
        _instances: Cache of adapter instances by name
    """

    def __init__(self):
        """Initialize empty registry."""
        self._adapters: Dict[str, Type[OrchestratorAdapter]] = {}
        self._instances: Dict[str, OrchestratorAdapter] = {}

    def register(self, name: str, adapter_class: Type[OrchestratorAdapter]) -> None:
        """Register adapter class by name.

        Args:
            name: Adapter identifier (e.g., "agents-sdk")
            adapter_class: OrchestratorAdapter subclass

        Raises:
            TypeError: If adapter_class is not OrchestratorAdapter subclass
        """
        if not issubclass(adapter_class, OrchestratorAdapter):
            raise TypeError(
                f"Adapter class must be subclass of OrchestratorAdapter, "
                f"got {adapter_class}"
            )

        self._adapters[name] = adapter_class

    def get(
        self, name: str, config: Optional[AdapterConfig] = None
    ) -> OrchestratorAdapter:
        """Get adapter instance by name.

        Returns cached instance if available, otherwise creates new instance.

        Args:
            name: Adapter identifier
            config: Optional adapter configuration (required for new instances)

        Returns:
            OrchestratorAdapter instance

        Raises:
            KeyError: If adapter name is not registered
            ValueError: If config is required but not provided
        """
        if name not in self._adapters:
            available = ", ".join(self.list_adapters())
            raise KeyError(
                f"Unknown adapter '{name}'. Available adapters: {available}"
            )

        # Return cached instance if available
        if name in self._instances:
            return self._instances[name]

        # Create new instance
        if config is None:
            raise ValueError(
                f"Configuration required to create new '{name}' adapter instance"
            )

        adapter_class = self._adapters[name]
        instance = adapter_class(config)

        # Cache instance
        self._instances[name] = instance

        return instance

    def list_adapters(self) -> List[str]:
        """List all registered adapter names.

        Returns:
            List of adapter identifiers
        """
        return sorted(self._adapters.keys())

    def get_capability_comparison(self) -> Dict[str, Dict[str, bool]]:
        """Generate capability comparison matrix for all adapters.

        Returns:
            Nested dict mapping adapter name -> capability name -> bool

        Example:
            {
                "agents-sdk": {
                    "tool_execution": True,
                    "guardrails": True,
                    "bead_replay": False,
                    ...
                },
                "langgraph": {
                    "tool_execution": True,
                    "memory_persistent": True,
                    ...
                },
                ...
            }
        """
        from .capability import ADAPTER_CAPABILITIES

        comparison = {}

        for adapter_name in self.list_adapters():
            # Get capabilities from capability matrix
            if adapter_name in ADAPTER_CAPABILITIES:
                matrix = ADAPTER_CAPABILITIES[adapter_name]
                comparison[adapter_name] = matrix.to_dict()
            else:
                # No capability matrix defined
                comparison[adapter_name] = {
                    cap.value: False for cap in AdapterCapability
                }

        return comparison

    def find_adapter_for_capabilities(
        self, required: Set[AdapterCapability]
    ) -> List[str]:
        """Find adapters supporting all required capabilities.

        Args:
            required: Set of required AdapterCapability enums

        Returns:
            List of adapter names supporting all required capabilities

        Example:
            required = {AdapterCapability.BEAD_REPLAY, AdapterCapability.GRAPH_FIRST}
            adapters = registry.find_adapter_for_capabilities(required)
            # Returns: ["beads-gastown"]
        """
        from .capability import ADAPTER_CAPABILITIES

        matching = []

        for adapter_name in self.list_adapters():
            if adapter_name in ADAPTER_CAPABILITIES:
                matrix = ADAPTER_CAPABILITIES[adapter_name]
                if matrix.supports_all(required):
                    matching.append(adapter_name)

        return matching

    def clear_cache(self) -> None:
        """Clear instance cache.

        Forces new instances to be created on next get() call.
        Useful for testing or when configuration changes.
        """
        self._instances.clear()


# Module-level singleton registry
_registry = AdapterRegistry()


def get_adapter(
    name: str, config: Optional[AdapterConfig] = None
) -> OrchestratorAdapter:
    """Get adapter instance by name.

    Convenience function for accessing the global registry.

    Args:
        name: Adapter identifier (e.g., "agents-sdk")
        config: Optional adapter configuration

    Returns:
        OrchestratorAdapter instance

    Raises:
        KeyError: If adapter name is not registered
        ValueError: If config is required but not provided

    Example:
        from alphaswarm_sol.adapters import get_adapter
        from alphaswarm_sol.adapters.agents_sdk import AgentsSdkConfig

        config = AgentsSdkConfig(api_key="...")
        adapter = get_adapter("agents-sdk", config)
    """
    return _registry.get(name, config)


def register_adapter(name: str, adapter_class: Type[OrchestratorAdapter]) -> None:
    """Register adapter class in global registry.

    Args:
        name: Adapter identifier
        adapter_class: OrchestratorAdapter subclass

    Example:
        from alphaswarm_sol.adapters import register_adapter
        from my_package import MyCustomAdapter

        register_adapter("my-adapter", MyCustomAdapter)
    """
    _registry.register(name, adapter_class)


def list_adapters() -> List[str]:
    """List all registered adapter names.

    Returns:
        List of adapter identifiers
    """
    return _registry.list_adapters()


def find_adapters_with_capabilities(
    required: Set[AdapterCapability],
) -> List[str]:
    """Find adapters supporting required capabilities.

    Args:
        required: Set of required capabilities

    Returns:
        List of adapter names
    """
    return _registry.find_adapter_for_capabilities(required)


# Auto-register all built-in adapters
register_adapter("agents-sdk", AgentsSdkAdapter)
register_adapter("codex-mcp", CodexMcpAdapter)
register_adapter("beads-gastown", BeadsGasTownAdapter)
register_adapter("claude-code", ClaudeCodeAdapter)

# Register optional adapters if available
if HAS_LANGGRAPH:
    register_adapter("langgraph", LangGraphAdapter)

if HAS_AUTOGEN:
    register_adapter("autogen", AutoGenAdapter)

if HAS_CREWAI:
    register_adapter("crewai", CrewAIAdapter)
