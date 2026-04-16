"""Adapter Capability Matrix and Feature Detection.

Defines capability enums and matrices for runtime adapter selection based
on required features. Enables detection of tool execution, memory persistence,
trace propagation, and evidence preservation capabilities.

Key Features:
- AdapterCapability enum for feature detection
- CapabilityMatrix for adapter comparison
- ADAPTER_CAPABILITIES constant for all supported frameworks
- Evidence requirement validation

Usage:
    from alphaswarm_sol.adapters.capability import (
        AdapterCapability,
        get_capability_matrix,
        check_evidence_requirements,
    )

    # Check if adapter supports guardrails
    matrix = get_capability_matrix("agents-sdk")
    if matrix.supports(AdapterCapability.GUARDRAILS):
        print("Guardrails supported")

    # Check evidence preservation warnings
    warnings = check_evidence_requirements("autogen")
    if warnings:
        print(f"Evidence warnings: {warnings}")

Phase: 07.1.4-01 Adapter Interface Foundation
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Set


class AdapterCapability(str, Enum):
    """Adapter capability enumeration for feature detection.

    Capabilities fall into four categories:
    1. Tool Execution: Can execute and convert tools/functions
    2. Memory Management: Shared, thread-local, or persistent memory
    3. Trace Propagation: OpenTelemetry or custom trace formats
    4. VRS Features: Evidence preservation, guardrails, cost tracking
    """

    # Tool Execution
    TOOL_EXECUTION = "tool_execution"  # Can execute tools/functions
    TOOL_CONVERSION = "tool_conversion"  # Can convert between tool formats

    # Memory Management
    MEMORY_SHARED = "memory_shared"  # Shared memory across agents
    MEMORY_THREAD = "memory_thread"  # Thread-local memory
    MEMORY_PERSISTENT = "memory_persistent"  # Persistent checkpointing

    # Trace Propagation
    TRACE_PROPAGATION = "trace_propagation"  # Can propagate trace context
    TRACE_EXPORT_OTEL = "trace_export_otel"  # OpenTelemetry trace export
    TRACE_EXPORT_CUSTOM = "trace_export_custom"  # Custom trace format export

    # Handoff Support
    HANDOFF_SYNC = "handoff_sync"  # Synchronous agent handoffs
    HANDOFF_ASYNC = "handoff_async"  # Asynchronous agent handoffs

    # VRS Features
    GUARDRAILS = "guardrails"  # Input/output guardrails
    COST_TRACKING = "cost_tracking"  # Token/cost usage tracking
    BEAD_REPLAY = "bead_replay"  # Can replay bead state for resumption
    GRAPH_FIRST = "graph_first"  # Enforces BSKG query requirements


@dataclass
class CapabilityMatrix:
    """Capability matrix for adapter feature detection.

    Provides methods to check single or multiple capabilities and
    identify missing features for requirements validation.

    Attributes:
        adapter_name: Name of the adapter
        capabilities: Set of supported AdapterCapability enums

    Example:
        matrix = CapabilityMatrix("agents-sdk", {
            AdapterCapability.TOOL_EXECUTION,
            AdapterCapability.GUARDRAILS,
        })

        if matrix.supports(AdapterCapability.GUARDRAILS):
            print("Guardrails available")

        missing = matrix.missing_for({AdapterCapability.BEAD_REPLAY})
        if missing:
            print(f"Missing: {missing}")
    """

    adapter_name: str
    capabilities: Set[AdapterCapability]

    def supports(self, cap: AdapterCapability) -> bool:
        """Check if adapter supports a capability.

        Args:
            cap: AdapterCapability to check

        Returns:
            True if capability is supported
        """
        return cap in self.capabilities

    def supports_all(self, caps: Set[AdapterCapability]) -> bool:
        """Check if adapter supports all given capabilities.

        Args:
            caps: Set of capabilities to check

        Returns:
            True if all capabilities are supported
        """
        return caps.issubset(self.capabilities)

    def supports_any(self, caps: Set[AdapterCapability]) -> bool:
        """Check if adapter supports any of the given capabilities.

        Args:
            caps: Set of capabilities to check

        Returns:
            True if at least one capability is supported
        """
        return bool(caps.intersection(self.capabilities))

    def missing_for(self, required: Set[AdapterCapability]) -> Set[AdapterCapability]:
        """Identify missing capabilities for requirements.

        Args:
            required: Set of required capabilities

        Returns:
            Set of capabilities that are required but not supported
        """
        return required - self.capabilities

    def to_dict(self) -> Dict[str, bool]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary mapping capability names to boolean support status
        """
        return {cap.value: cap in self.capabilities for cap in AdapterCapability}


# Adapter Capability Matrix Definitions
# Maps adapter names to their supported capabilities

ADAPTER_CAPABILITIES: Dict[str, CapabilityMatrix] = {
    "agents-sdk": CapabilityMatrix(
        "agents-sdk",
        {
            AdapterCapability.TOOL_EXECUTION,
            AdapterCapability.TOOL_CONVERSION,
            AdapterCapability.TRACE_PROPAGATION,
            AdapterCapability.HANDOFF_SYNC,
            AdapterCapability.GUARDRAILS,
            AdapterCapability.COST_TRACKING,
        },
    ),
    "langgraph": CapabilityMatrix(
        "langgraph",
        {
            AdapterCapability.TOOL_EXECUTION,
            AdapterCapability.MEMORY_PERSISTENT,
            AdapterCapability.TRACE_PROPAGATION,
            AdapterCapability.TRACE_EXPORT_OTEL,
            AdapterCapability.HANDOFF_ASYNC,
            AdapterCapability.BEAD_REPLAY,
        },
    ),
    "autogen": CapabilityMatrix(
        "autogen",
        {
            AdapterCapability.TOOL_EXECUTION,
            AdapterCapability.MEMORY_THREAD,
            AdapterCapability.HANDOFF_SYNC,
            AdapterCapability.HANDOFF_ASYNC,
        },
    ),
    "crewai": CapabilityMatrix(
        "crewai",
        {
            AdapterCapability.TOOL_EXECUTION,
            AdapterCapability.MEMORY_SHARED,
            AdapterCapability.HANDOFF_SYNC,
        },
    ),
    "beads-gastown": CapabilityMatrix(
        "beads-gastown",
        {
            AdapterCapability.MEMORY_PERSISTENT,
            AdapterCapability.BEAD_REPLAY,
            AdapterCapability.GRAPH_FIRST,
        },
    ),
    "claude-code": CapabilityMatrix(
        "claude-code",
        {
            AdapterCapability.TOOL_EXECUTION,
            AdapterCapability.GRAPH_FIRST,
        },
    ),
    "codex-mcp": CapabilityMatrix(
        "codex-mcp",
        {
            AdapterCapability.TOOL_EXECUTION,
            AdapterCapability.TOOL_CONVERSION,
        },
    ),
}


def get_capability_matrix(adapter_name: str) -> CapabilityMatrix:
    """Get capability matrix for an adapter.

    Args:
        adapter_name: Name of the adapter (e.g., "agents-sdk", "langgraph")

    Returns:
        CapabilityMatrix for the adapter

    Raises:
        KeyError: If adapter name is not recognized

    Example:
        matrix = get_capability_matrix("agents-sdk")
        print(f"Tool execution: {matrix.supports(AdapterCapability.TOOL_EXECUTION)}")
    """
    if adapter_name not in ADAPTER_CAPABILITIES:
        available = ", ".join(ADAPTER_CAPABILITIES.keys())
        raise KeyError(
            f"Unknown adapter '{adapter_name}'. Available: {available}"
        )
    return ADAPTER_CAPABILITIES[adapter_name]


def check_evidence_requirements(adapter_name: str) -> List[str]:
    """Check adapter for evidence preservation requirements.

    Returns warnings if adapter lacks capabilities critical for
    evidence-first VRS workflows (BEAD_REPLAY, GRAPH_FIRST).

    Args:
        adapter_name: Name of the adapter to check

    Returns:
        List of warning messages (empty if all requirements met)

    Example:
        warnings = check_evidence_requirements("autogen")
        if warnings:
            for warning in warnings:
                print(f"Warning: {warning}")
    """
    try:
        matrix = get_capability_matrix(adapter_name)
    except KeyError as e:
        return [str(e)]

    warnings = []

    # Check for BEAD_REPLAY capability
    if not matrix.supports(AdapterCapability.BEAD_REPLAY):
        warnings.append(
            f"Adapter '{adapter_name}' lacks BEAD_REPLAY capability. "
            "Evidence state may not be resumable after interruption."
        )

    # Check for GRAPH_FIRST capability
    if not matrix.supports(AdapterCapability.GRAPH_FIRST):
        warnings.append(
            f"Adapter '{adapter_name}' lacks GRAPH_FIRST capability. "
            "BSKG query requirements may not be enforced during investigation."
        )

    # Check for TRACE_PROPAGATION (important for observability)
    if not matrix.supports(AdapterCapability.TRACE_PROPAGATION):
        warnings.append(
            f"Adapter '{adapter_name}' lacks TRACE_PROPAGATION capability. "
            "Distributed tracing across handoffs will not be available."
        )

    return warnings
