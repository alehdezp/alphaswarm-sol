"""Shared type definitions for the VKG builder package.

This module provides Protocol interfaces for Slither abstractions and
Literal types for confidence levels and proxy patterns, enabling
type-safe builder modules with minimal coupling to Slither internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Protocol, runtime_checkable


# -----------------------------------------------------------------------------
# Confidence and Proxy Types
# -----------------------------------------------------------------------------

CallConfidence = Literal["HIGH", "MEDIUM", "LOW"]
"""Confidence level for call target resolution.

- HIGH: Direct, unambiguous call (e.g., contract.method())
- MEDIUM: Resolvable through state analysis (e.g., stored interface)
- LOW: Dynamic or unresolvable (e.g., delegatecall to user input)
"""

ProxyType = Literal[
    "transparent",
    "uups",
    "diamond",
    "beacon",
    "minimal",
    "unknown",
    "none",
]
"""Detected proxy pattern type (string literal).

- transparent: OpenZeppelin TransparentUpgradeableProxy
- uups: Universal Upgradeable Proxy Standard (EIP-1822)
- diamond: EIP-2535 Diamond/Multi-facet proxy
- beacon: Beacon proxy pattern
- minimal: EIP-1167 minimal proxy/clone
- unknown: Detected as proxy but pattern unclear
- none: Not a proxy contract
"""


class ProxyPattern(Enum):
    """Supported proxy patterns (enum version).

    Provides pattern-matching and comparison capabilities for
    proxy detection and resolution logic.
    """

    TRANSPARENT = "transparent"  # EIP-1967 Transparent
    UUPS = "uups"  # Universal Upgradeable Proxy Standard
    DIAMOND = "diamond"  # EIP-2535 Diamond
    BEACON = "beacon"  # Beacon Proxy
    MINIMAL = "minimal"  # EIP-1167 Minimal Proxy (clone)
    UNKNOWN = "unknown"  # Detected as proxy but pattern unclear
    NONE = "none"  # Not a proxy


# EIP-1967 storage slots (pre-computed keccak256 hashes)
# See: https://eips.ethereum.org/EIPS/eip-1967
EIP1967_IMPLEMENTATION_SLOT = (
    "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
)
"""keccak256('eip1967.proxy.implementation') - 1"""

EIP1967_ADMIN_SLOT = (
    "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
)
"""keccak256('eip1967.proxy.admin') - 1"""

EIP1967_BEACON_SLOT = (
    "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
)
"""keccak256('eip1967.proxy.beacon') - 1"""


# -----------------------------------------------------------------------------
# Slither Protocol Abstractions
# -----------------------------------------------------------------------------

@runtime_checkable
class SlitherExpression(Protocol):
    """Abstract interface for Slither expression nodes."""

    @property
    def type(self) -> Any:
        """Expression type."""
        ...


@runtime_checkable
class SlitherStateVariable(Protocol):
    """Abstract interface for Slither state variable objects.

    Provides type-safe access to state variable properties without
    tight coupling to Slither's internal implementation.
    """

    @property
    def name(self) -> str:
        """Variable name."""
        ...

    @property
    def type(self) -> Any:
        """Variable type (Slither Type object)."""
        ...

    @property
    def visibility(self) -> str:
        """Visibility: public, private, internal."""
        ...

    @property
    def is_constant(self) -> bool:
        """Whether variable is declared constant."""
        ...

    @property
    def is_immutable(self) -> bool:
        """Whether variable is declared immutable."""
        ...

    @property
    def expression(self) -> SlitherExpression | None:
        """Initial value expression, if any."""
        ...


@runtime_checkable
class SlitherFunction(Protocol):
    """Abstract interface for Slither function objects.

    Provides type-safe access to function properties without
    tight coupling to Slither's internal implementation.
    """

    @property
    def name(self) -> str:
        """Function name."""
        ...

    @property
    def full_name(self) -> str:
        """Full function name including parameter types."""
        ...

    @property
    def signature_str(self) -> str:
        """Function signature as string."""
        ...

    @property
    def canonical_name(self) -> str:
        """Canonical name including contract."""
        ...

    @property
    def visibility(self) -> str:
        """Visibility: public, external, internal, private."""
        ...

    @property
    def is_constructor(self) -> bool:
        """Whether this is a constructor."""
        ...

    @property
    def is_fallback(self) -> bool:
        """Whether this is a fallback function."""
        ...

    @property
    def is_receive(self) -> bool:
        """Whether this is a receive function."""
        ...

    @property
    def view(self) -> bool:
        """Whether function is view."""
        ...

    @property
    def pure(self) -> bool:
        """Whether function is pure."""
        ...

    @property
    def payable(self) -> bool:
        """Whether function is payable."""
        ...

    @property
    def modifiers(self) -> list[Any]:
        """List of modifier calls."""
        ...

    @property
    def parameters(self) -> list[Any]:
        """List of function parameters."""
        ...

    @property
    def returns(self) -> list[Any]:
        """List of return variables."""
        ...

    @property
    def state_variables_read(self) -> list[Any]:
        """State variables read by this function."""
        ...

    @property
    def state_variables_written(self) -> list[Any]:
        """State variables written by this function."""
        ...

    @property
    def internal_calls(self) -> list[Any]:
        """Internal function calls made."""
        ...

    @property
    def external_calls_as_expressions(self) -> list[Any]:
        """External call expressions."""
        ...

    @property
    def high_level_calls(self) -> list[Any]:
        """High-level external calls (contract, function) pairs."""
        ...

    @property
    def low_level_calls(self) -> list[Any]:
        """Low-level calls (call, delegatecall, staticcall)."""
        ...


@runtime_checkable
class SlitherContract(Protocol):
    """Abstract interface for Slither contract objects.

    Provides type-safe access to contract properties without
    tight coupling to Slither's internal implementation.
    """

    @property
    def name(self) -> str:
        """Contract name."""
        ...

    @property
    def id(self) -> int:
        """Unique contract ID."""
        ...

    @property
    def is_interface(self) -> bool:
        """Whether this is an interface."""
        ...

    @property
    def is_library(self) -> bool:
        """Whether this is a library."""
        ...

    @property
    def is_abstract(self) -> bool:
        """Whether this is abstract."""
        ...

    @property
    def inheritance(self) -> list[Any]:
        """List of inherited contracts."""
        ...

    @property
    def state_variables(self) -> list[Any]:
        """List of state variables."""
        ...

    @property
    def state_variables_declared(self) -> list[Any]:
        """State variables declared in this contract (not inherited)."""
        ...

    @property
    def functions(self) -> list[Any]:
        """List of functions."""
        ...

    @property
    def functions_declared(self) -> list[Any]:
        """Functions declared in this contract (not inherited)."""
        ...

    @property
    def modifiers(self) -> list[Any]:
        """List of modifiers."""
        ...

    @property
    def events(self) -> list[Any]:
        """List of events."""
        ...

    @property
    def source_mapping(self) -> Any:
        """Source code mapping information."""
        ...


# -----------------------------------------------------------------------------
# Builder Internal Types
# -----------------------------------------------------------------------------

@dataclass
class UnresolvedTarget:
    """Tracks an unresolved call target for completeness reporting.

    Used to document where the builder could not determine the exact
    target of an external call, enabling detection gap analysis.
    """

    source_function: str
    """Fully qualified name of the calling function."""

    call_type: str
    """Type of call: 'high_level', 'low_level', 'delegatecall', 'library'."""

    target_expression: str
    """String representation of the unresolved target expression."""

    reason: str
    """Why resolution failed: 'dynamic', 'interface_only', 'unknown_type', etc."""

    confidence: CallConfidence = "LOW"
    """Confidence in any partial resolution."""

    file: str | None = None
    """Source file path."""

    line: int | None = None
    """Line number of the call."""

    context: dict[str, Any] = field(default_factory=dict)
    """Additional context for debugging/analysis."""

    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}" if self.file and self.line else "unknown"
        return f"[{self.call_type}] {self.source_function} -> {self.target_expression} ({self.reason}) at {loc}"


@dataclass
class CallTarget:
    """Resolved call target with confidence information.

    Represents a successfully resolved external call target,
    including confidence level and evidence for the resolution.
    """

    contract_name: str
    """Name of the target contract."""

    function_name: str | None
    """Name of the target function, if known."""

    function_signature: str | None
    """Full function signature, if known."""

    confidence: CallConfidence
    """Confidence level of the resolution."""

    is_interface: bool = False
    """Whether the target is an interface (implementation unknown)."""

    possible_implementations: list[str] = field(default_factory=list)
    """List of possible concrete implementations if interface."""

    evidence: str | None = None
    """How the target was resolved (for debugging)."""


@dataclass
class ProxyInfo:
    """Proxy detection and resolution result.

    Captures comprehensive proxy detection results including pattern type,
    implementation resolution, Diamond facets, and admin mechanisms.
    Best-effort resolution with confidence scoring.
    """

    is_proxy: bool
    """Whether the contract is detected as a proxy."""

    pattern: ProxyPattern
    """Detected proxy pattern type."""

    confidence: CallConfidence
    """Confidence in the detection/resolution."""

    # Implementation info
    implementation_slot: str | None = None
    """Storage slot for implementation address (EIP-1967)."""

    implementation_contract: str | None = None
    """Name of the implementation contract if resolved."""

    implementation_address: str | None = None
    """Address of implementation if known at analysis time."""

    # Diamond-specific (EIP-2535)
    facets: list[str] = field(default_factory=list)
    """List of Diamond facet contract names."""

    facet_selectors: dict[str, list[str]] = field(default_factory=dict)
    """Mapping of facet name to list of function selectors."""

    # Beacon-specific
    beacon_contract: str | None = None
    """Name of the Beacon contract (for beacon proxies)."""

    beacon_address: str | None = None
    """Address of beacon if known at analysis time."""

    # Admin info
    admin_slot: str | None = None
    """Storage slot for admin address (EIP-1967)."""

    admin_contract: str | None = None
    """Name of the admin/ProxyAdmin contract."""

    # Upgrade mechanism
    upgrade_function: str | None = None
    """Name of the upgrade function."""

    initializer_function: str | None = None
    """Name of the initializer function."""

    is_initialized: bool | None = None
    """Whether the proxy has been initialized."""

    # Resolution metadata
    resolution_notes: list[str] = field(default_factory=list)
    """Notes about resolution process and findings."""

    unresolved_reason: str | None = None
    """If resolution incomplete, why it couldn't be resolved."""

    evidence: list[str] = field(default_factory=list)
    """Evidence used to detect this proxy pattern."""

    # Legacy compatibility
    @property
    def proxy_type(self) -> ProxyType:
        """Legacy accessor for proxy type as string literal."""
        return self.pattern.value  # type: ignore[return-value]


# -----------------------------------------------------------------------------
# Call Tracking Types
# -----------------------------------------------------------------------------

CallType = Literal["internal", "external", "delegatecall", "staticcall", "library"]
"""Type of call being made.

- internal: Call to a function within the same contract
- external: High-level external call (contract.function())
- delegatecall: Low-level delegatecall (code runs in caller's context)
- staticcall: Read-only external call
- library: Library function call
"""

TargetResolution = Literal["direct", "inferred", "interface", "unresolved"]
"""How the call target was resolved.

- direct: Explicit target (e.g., specificContract.function())
- inferred: Resolved through state variable type analysis
- interface: Target is an interface, implementation unknown
- unresolved: Could not determine target
"""


@dataclass
class CallInfo:
    """Information about a call site.

    Captures detailed information about a single call including the type,
    target resolution, confidence level, and source location.
    """

    call_type: CallType
    """Type of call (internal, external, delegatecall, etc.)."""

    target_contract: str | None
    """Name of the target contract, if resolved."""

    target_function: str | None
    """Name of the target function, if resolved."""

    confidence: CallConfidence
    """Confidence level in target resolution."""

    resolution: TargetResolution
    """How the target was resolved."""

    # Source location
    file_path: str | None = None
    """Source file containing the call."""

    line_number: int | None = None
    """Line number of the call."""

    # Callback detection
    is_callback_source: bool = False
    """Whether this call triggers a callback to the caller."""

    potential_callbacks: list[str] = field(default_factory=list)
    """List of callback function names that may be invoked."""

    # Call metadata
    data_expression: str | None = None
    """String representation of call data/arguments."""

    gas_specified: bool = False
    """Whether gas was explicitly specified."""

    value_sent: bool = False
    """Whether value (ETH) is sent with the call."""

    def __str__(self) -> str:
        target = f"{self.target_contract}.{self.target_function}" if self.target_contract else self.target_function
        loc = f"{self.file_path}:{self.line_number}" if self.file_path and self.line_number else "?"
        return f"[{self.call_type}:{self.confidence}] -> {target or 'unresolved'} @ {loc}"


@dataclass
class CallbackPattern:
    """Detected callback pattern.

    Represents a detected callback relationship where an external call
    is expected to call back into the calling contract.
    """

    source_function: str
    """Function that initiates the external call."""

    callback_interface: str
    """Interface or contract containing the callback."""

    callback_function: str
    """Name of the callback function."""

    pattern_type: str
    """Type of callback pattern: 'flash_loan', 'erc777', 'erc721', 'uniswap', 'custom'."""

    confidence: CallConfidence
    """Confidence in the callback detection."""

    def __str__(self) -> str:
        return f"[{self.pattern_type}] {self.source_function} -> {self.callback_interface}.{self.callback_function}"
