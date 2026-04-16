"""VKG Builder Package.

This package provides modular knowledge graph construction from Solidity code.

Public API:
    - VKGBuilder: Main builder class for knowledge graph construction
    - BuildContext: Dependency injection context for builder modules
    - build_graph: Convenience function for one-shot graph builds
    - build_graph_with_context: Build graph with access to diagnostics

Processor Classes (modular extraction from legacy builder):
    - ContractProcessor: Contract-level analysis and node creation
    - StateVarProcessor: State variable analysis and node creation
    - ProxyResolver: Proxy pattern detection and resolution
    - CallTracker: Call tracking with confidence scoring
    - CompletenessReporter: Build completeness reporting

Convenience Functions:
    - process_contract: Process a contract and create its node
    - process_inheritance: Process contract inheritance edges
    - process_state_variables: Process state variables for a contract
    - resolve_proxy: Resolve proxy pattern for a contract
    - track_calls: Track all calls from a function
    - generate_report: Generate completeness report

Report Classes:
    - CompletenessReport: Complete build report with metrics
    - CoverageMetrics: Coverage tracking for contracts/functions
    - ConfidenceBreakdown: Edge confidence distribution

Type Exports:
    - CallConfidence: Literal type for call resolution confidence
    - CallType: Literal type for call type
    - TargetResolution: Literal type for target resolution method
    - ProxyType: Literal type for proxy pattern detection
    - ProxyPattern: Enum for proxy patterns
    - UnresolvedTarget: Dataclass for tracking unresolved call targets
    - CallTarget: Dataclass for resolved call targets
    - CallInfo: Dataclass for call site information
    - CallbackPattern: Dataclass for detected callback patterns
    - ProxyInfo: Dataclass for proxy pattern information
    - ContractProperties: Dataclass for computed contract properties
    - StateVarProperties: Dataclass for computed state variable properties
    - SlitherContract: Protocol for Slither contract abstraction
    - SlitherFunction: Protocol for Slither function abstraction
    - SlitherStateVariable: Protocol for Slither state variable abstraction
    - EIP1967_IMPLEMENTATION_SLOT: EIP-1967 storage slot constant
    - EIP1967_ADMIN_SLOT: EIP-1967 storage slot constant
    - EIP1967_BEACON_SLOT: EIP-1967 storage slot constant
"""
from __future__ import annotations

# Import core components from the new modular structure
from alphaswarm_sol.kg.builder.core import (
    VKGBuilder,
    build_graph,
    build_graph_with_context,
)
from alphaswarm_sol.kg.builder.context import BuildContext
from alphaswarm_sol.kg.builder.types import (
    CallbackPattern,
    CallConfidence,
    CallInfo,
    CallTarget,
    CallType,
    EIP1967_ADMIN_SLOT,
    EIP1967_BEACON_SLOT,
    EIP1967_IMPLEMENTATION_SLOT,
    ProxyInfo,
    ProxyPattern,
    ProxyType,
    SlitherContract,
    SlitherFunction,
    SlitherStateVariable,
    TargetResolution,
    UnresolvedTarget,
)

# Import processor classes from modular extraction
from alphaswarm_sol.kg.builder.contracts import (
    ContractProcessor,
    ContractProperties,
    process_contract,
    process_inheritance,
)
from alphaswarm_sol.kg.builder.state_vars import (
    StateVarProcessor,
    StateVarProperties,
    process_state_variables,
    classify_state_variables,
    get_privileged_state_vars,
)
from alphaswarm_sol.kg.builder.proxy import (
    ProxyResolver,
    resolve_proxy,
    is_proxy_contract,
    get_proxy_pattern,
)
from alphaswarm_sol.kg.builder.calls import (
    CallTracker,
    track_calls,
    get_external_call_contracts,
    CALLBACK_PATTERNS,
)
from alphaswarm_sol.kg.builder.completeness import (
    CompletenessReporter,
    CompletenessReport,
    CoverageMetrics,
    ConfidenceBreakdown,
    generate_report,
    write_report,
)

__all__ = [
    # Core builder classes and functions
    "VKGBuilder",
    "BuildContext",
    "build_graph",
    "build_graph_with_context",
    # Processor classes
    "ContractProcessor",
    "StateVarProcessor",
    "ProxyResolver",
    "CallTracker",
    "CompletenessReporter",
    # Convenience functions
    "process_contract",
    "process_inheritance",
    "process_state_variables",
    "classify_state_variables",
    "get_privileged_state_vars",
    "resolve_proxy",
    "is_proxy_contract",
    "get_proxy_pattern",
    "track_calls",
    "get_external_call_contracts",
    "generate_report",
    "write_report",
    # Report classes
    "CompletenessReport",
    "CoverageMetrics",
    "ConfidenceBreakdown",
    # Type literals and enums
    "CallConfidence",
    "CallType",
    "TargetResolution",
    "ProxyType",
    "ProxyPattern",
    # Dataclasses for build tracking
    "UnresolvedTarget",
    "CallTarget",
    "CallInfo",
    "CallbackPattern",
    "ProxyInfo",
    "ContractProperties",
    "StateVarProperties",
    # Protocol types for Slither abstraction
    "SlitherContract",
    "SlitherFunction",
    "SlitherStateVariable",
    # EIP-1967 constants
    "EIP1967_IMPLEMENTATION_SLOT",
    "EIP1967_ADMIN_SLOT",
    "EIP1967_BEACON_SLOT",
    # Callback patterns constant
    "CALLBACK_PATTERNS",
]
