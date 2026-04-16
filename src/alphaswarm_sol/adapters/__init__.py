"""Orchestrator Adapters for External Framework Interoperability.

This module provides adapter interfaces for running AlphaSwarm VRS workflows
across external orchestration frameworks (Agents SDK, LangGraph, AutoGen, CrewAI).

Core Abstractions:
- OrchestratorAdapter: Abstract base class for framework adapters
- AdapterConfig: Adapter configuration with capabilities
- HandoffContext: Context for agent handoffs with evidence preservation
- TraceContext: Distributed tracing context for observability
- AdapterCapability: Feature detection for adapter capabilities

Design Principles:
1. Evidence Preservation: Ensure VulnerabilityBead evidence contracts survive framework boundaries
2. Trace Continuity: Propagate trace context across handoffs for observability
3. Capability Detection: Feature matrix for runtime adapter selection
4. Framework Agnostic: Unified interface regardless of orchestration framework

Usage:
    from alphaswarm_sol.adapters import (
        OrchestratorAdapter,
        AdapterConfig,
        HandoffContext,
        TraceContext,
        AdapterCapability,
    )

    # Check adapter capabilities
    from alphaswarm_sol.adapters.capability import get_capability_matrix

    matrix = get_capability_matrix("agents-sdk")
    if matrix.supports(AdapterCapability.GUARDRAILS):
        # Use guardrails feature
        pass

Phase: 07.1.4 Interop & Orchestrator Adapters
"""

from .base import (
    AdapterConfig,
    HandoffContext,
    HandoffResult,
    OrchestratorAdapter,
    TraceContext,
)
from .capability import (
    AdapterCapability,
    CapabilityMatrix,
    check_evidence_requirements,
    get_capability_matrix,
    ADAPTER_CAPABILITIES,
)

# Adapter implementations
from .agents_sdk import AgentsSdkAdapter, AgentsSdkConfig
from .beads_gastown import BeadsGasTownAdapter, BeadsGasTownConfig
from .claude_code import ClaudeCodeAdapter, ClaudeCodeConfig
from .codex_mcp import CodexMcpAdapter, CodexMcpConfig

# Conditional imports for adapters (optional dependencies)
try:
    from .langgraph import LangGraphAdapter, LangGraphConfig

    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    LangGraphAdapter = None  # type: ignore
    LangGraphConfig = None  # type: ignore

try:
    from .autogen import AutoGenAdapter, AutoGenConfig

    HAS_AUTOGEN = True
except ImportError:
    HAS_AUTOGEN = False
    AutoGenAdapter = None  # type: ignore
    AutoGenConfig = None  # type: ignore

try:
    from .crewai import CrewAIAdapter, CrewAIConfig

    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False
    CrewAIAdapter = None  # type: ignore
    CrewAIConfig = None  # type: ignore

# Registry
from .registry import (
    AdapterRegistry,
    find_adapters_with_capabilities,
    get_adapter,
    list_adapters,
    register_adapter,
)

__all__ = [
    # Base classes
    "OrchestratorAdapter",
    "AdapterConfig",
    "HandoffContext",
    "HandoffResult",
    "TraceContext",
    # Capability detection
    "AdapterCapability",
    "CapabilityMatrix",
    "get_capability_matrix",
    "check_evidence_requirements",
    "ADAPTER_CAPABILITIES",
    # Adapter implementations
    "AgentsSdkAdapter",
    "AgentsSdkConfig",
    "BeadsGasTownAdapter",
    "BeadsGasTownConfig",
    "ClaudeCodeAdapter",
    "ClaudeCodeConfig",
    "CodexMcpAdapter",
    "CodexMcpConfig",
    # Adapters (if available)
    "LangGraphAdapter",
    "LangGraphConfig",
    "AutoGenAdapter",
    "AutoGenConfig",
    "CrewAIAdapter",
    "CrewAIConfig",
    # Registry
    "AdapterRegistry",
    "get_adapter",
    "register_adapter",
    "list_adapters",
    "find_adapters_with_capabilities",
]
