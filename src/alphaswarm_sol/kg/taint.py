"""Taint/dataflow modeling for attacker-controlled input.

This module implements taint analysis for Solidity smart contracts following
the canonical rules defined in docs/reference/TAINT_RULES.md.

Key concepts:
- TaintSource: Origin of tainted data (user input, external return, etc.)
- TaintSink: Operations where tainted data creates security risk
- TaintSanitizer: Operations that reduce or eliminate taint
- TaintAvailability: Confidence in taint analysis results
- TaintResult: Complete taint analysis result with path and availability

See TAINT_RULES.md for:
- Aliasing strategy (Direct-then-Aliased)
- Source/sink severity matrix
- Availability calibration criteria
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog

try:
    from slither.analyses.data_dependency.data_dependency import is_dependent
except Exception:  # pragma: no cover - optional dependency
    is_dependent = None


LOGGER = structlog.get_logger()


# =============================================================================
# Taint Source Types
# =============================================================================


class TaintSource(Enum):
    """Source of tainted data, ranked by risk level.

    See TAINT_RULES.md for detailed source definitions and risk levels.
    """

    # CRITICAL risk
    CALL_TARGET_CONTROL = "call_target_control"  # User controls call destination

    # HIGH risk
    EXTERNAL_RETURN = "external_return"  # Return from external call
    USER_INPUT = "user_input"  # Function parameters
    ORACLE = "oracle"  # External price feeds

    # MEDIUM risk
    ENVIRONMENT = "environment"  # msg.sender, msg.value, block.*

    # LOW risk
    STORAGE_ALIASED = "storage_aliased"  # Tainted storage read


# Risk levels for source types
TAINT_SOURCE_RISK: dict[TaintSource, str] = {
    TaintSource.CALL_TARGET_CONTROL: "CRITICAL",
    TaintSource.EXTERNAL_RETURN: "HIGH",
    TaintSource.USER_INPUT: "HIGH",
    TaintSource.ORACLE: "HIGH",
    TaintSource.ENVIRONMENT: "MEDIUM",
    TaintSource.STORAGE_ALIASED: "LOW",
}


# =============================================================================
# Taint Sink Types
# =============================================================================


class TaintSink(Enum):
    """Operations where tainted data creates security risk.

    See TAINT_RULES.md for sink severity matrix.
    """

    # CRITICAL severity
    CALL_TARGET = "call_target"  # TAINTED_ADDR.call()
    EXTERNAL_CALL_VALUE = "external_call_value"  # .call{value: TAINTED}()

    # HIGH severity
    STORAGE_WRITE = "storage_write"  # balances[x] = TAINTED

    # MEDIUM severity
    ARITHMETIC = "arithmetic"  # a + TAINTED (overflow risk)

    # LOW severity
    COMPARISON = "comparison"  # if (TAINTED > x)


# Severity levels for sink types
TAINT_SINK_SEVERITY: dict[TaintSink, str] = {
    TaintSink.CALL_TARGET: "CRITICAL",
    TaintSink.EXTERNAL_CALL_VALUE: "CRITICAL",
    TaintSink.STORAGE_WRITE: "HIGH",
    TaintSink.ARITHMETIC: "MEDIUM",
    TaintSink.COMPARISON: "LOW",
}


# =============================================================================
# Taint Sanitizer Types
# =============================================================================


class TaintSanitizer(Enum):
    """Operations that reduce or eliminate taint.

    See TAINT_RULES.md for sanitizer effects and application rules.
    """

    BOUNDS_CHECK = "bounds_check"  # require(x < MAX)
    OWNERSHIP_CHECK = "ownership_check"  # require(msg.sender == owner)
    SAFE_MATH = "safe_math"  # x.add(y)
    TYPE_CAST = "type_cast"  # uint8(x)
    WHITELIST_CHECK = "whitelist_check"  # require(allowed[addr])
    ZERO_CHECK = "zero_check"  # require(addr != address(0))


# Which sinks each sanitizer affects
SANITIZER_AFFECTS: dict[TaintSanitizer, list[TaintSink]] = {
    TaintSanitizer.BOUNDS_CHECK: [TaintSink.ARITHMETIC],
    TaintSanitizer.OWNERSHIP_CHECK: [],  # Context validation only
    TaintSanitizer.SAFE_MATH: [TaintSink.ARITHMETIC],
    TaintSanitizer.TYPE_CAST: [TaintSink.ARITHMETIC],
    TaintSanitizer.WHITELIST_CHECK: [TaintSink.CALL_TARGET],
    TaintSanitizer.ZERO_CHECK: [],  # Weak sanitizer
}


# =============================================================================
# Taint Availability
# =============================================================================


@dataclass
class TaintAvailability:
    """Availability and confidence of taint analysis.

    See TAINT_RULES.md for availability calibration criteria.

    Attributes:
        available: Is taint analysis available? If False, result is UNKNOWN.
        confidence: Confidence in result (0.0-1.0). See calibration thresholds.
        reason: Explanation when unavailable or low confidence.
    """

    available: bool
    confidence: float
    reason: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate confidence bounds."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")

    @classmethod
    def full(cls) -> TaintAvailability:
        """Full availability with complete confidence."""
        return cls(available=True, confidence=1.0, reason=None)

    @classmethod
    def aliased(cls) -> TaintAvailability:
        """Reduced confidence due to storage aliasing."""
        return cls(
            available=True,
            confidence=0.7,
            reason="storage aliasing reduces confidence",
        )

    @classmethod
    def external_call(cls) -> TaintAvailability:
        """Reduced confidence due to external call in path."""
        return cls(
            available=True,
            confidence=0.5,
            reason="external call effects unknown",
        )

    @classmethod
    def delegatecall(cls) -> TaintAvailability:
        """Unavailable due to delegatecall."""
        return cls(
            available=False,
            confidence=0.0,
            reason="delegatecall to external contract - storage effects unknown",
        )

    @classmethod
    def inline_assembly(cls) -> TaintAvailability:
        """Unavailable due to inline assembly."""
        return cls(
            available=False,
            confidence=0.0,
            reason="inline assembly - opaque to static analysis",
        )

    @classmethod
    def dynamic_loop(cls) -> TaintAvailability:
        """Reduced confidence due to dynamic loop bound."""
        return cls(
            available=True,
            confidence=0.6,
            reason="loop with dynamic bound - iteration-dependent taint",
        )

    @classmethod
    def recursive(cls) -> TaintAvailability:
        """Reduced confidence due to recursion."""
        return cls(
            available=True,
            confidence=0.5,
            reason="recursive call - depth unknown",
        )

    @classmethod
    def try_catch(cls) -> TaintAvailability:
        """Reduced confidence due to try/catch with external call."""
        return cls(
            available=True,
            confidence=0.4,
            reason="try/catch with external - exception path uncertainty",
        )

    @classmethod
    def unavailable(cls, reason: str) -> TaintAvailability:
        """Generic unavailable result."""
        return cls(available=False, confidence=0.0, reason=reason)

    def is_high_confidence(self) -> bool:
        """Confidence >= 0.9 (use result directly)."""
        return self.available and self.confidence >= 0.9

    def is_medium_confidence(self) -> bool:
        """Confidence 0.7-0.89 (use with caution)."""
        return self.available and 0.7 <= self.confidence < 0.9

    def is_low_confidence(self) -> bool:
        """Confidence 0.5-0.69 (require manual review)."""
        return self.available and 0.5 <= self.confidence < 0.7

    def is_insufficient(self) -> bool:
        """Confidence < 0.5 or unavailable (treat as UNKNOWN)."""
        return not self.available or self.confidence < 0.5


# =============================================================================
# Taint Result
# =============================================================================


@dataclass
class TaintResult:
    """Complete taint analysis result.

    Attributes:
        is_tainted: Whether value is tainted.
        sources: List of taint sources that contribute.
        path: Taint propagation path (variable names).
        availability: Confidence in this result.
        sanitizers_applied: Sanitizers applied along the path.
        sink: Target sink if analyzing sink reachability.
    """

    is_tainted: bool
    sources: list[TaintSource] = field(default_factory=list)
    path: list[str] = field(default_factory=list)
    availability: TaintAvailability = field(default_factory=TaintAvailability.full)
    sanitizers_applied: list[TaintSanitizer] = field(default_factory=list)
    sink: Optional[TaintSink] = None

    @property
    def is_unknown(self) -> bool:
        """True if taint analysis is unavailable.

        IMPORTANT: When is_unknown is True, the result should NOT be
        interpreted as "not tainted". Treat as potentially tainted.
        """
        return not self.availability.available

    @property
    def is_safe(self) -> bool:
        """True only if analysis is available AND value is not tainted.

        Use this for conservative safety checks.
        """
        return self.availability.available and not self.is_tainted

    @property
    def risk_level(self) -> str:
        """Highest risk level among sources."""
        if not self.sources:
            return "NONE"
        risk_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        source_risks = [TAINT_SOURCE_RISK.get(s, "LOW") for s in self.sources]
        for risk in risk_order:
            if risk in source_risks:
                return risk
        return "LOW"

    @classmethod
    def safe(cls) -> TaintResult:
        """Create a safe (not tainted, available) result."""
        return cls(
            is_tainted=False,
            sources=[],
            path=[],
            availability=TaintAvailability.full(),
            sanitizers_applied=[],
        )

    @classmethod
    def unknown(cls, reason: str) -> TaintResult:
        """Create an unknown (unavailable) result.

        Use this when taint analysis cannot be performed.
        The result is NOT safe - it is unknown.
        """
        return cls(
            is_tainted=False,  # Unknown, not safe
            sources=[],
            path=[],
            availability=TaintAvailability.unavailable(reason),
            sanitizers_applied=[],
        )

    @classmethod
    def tainted(
        cls,
        sources: list[TaintSource],
        path: Optional[list[str]] = None,
        availability: Optional[TaintAvailability] = None,
        sanitizers: Optional[list[TaintSanitizer]] = None,
        sink: Optional[TaintSink] = None,
    ) -> TaintResult:
        """Create a tainted result with given sources."""
        return cls(
            is_tainted=True,
            sources=sources,
            path=path or [],
            availability=availability or TaintAvailability.full(),
            sanitizers_applied=sanitizers or [],
            sink=sink,
        )


# =============================================================================
# Taint Analyzer
# =============================================================================


class TaintAnalyzer:
    """Analyzer for taint propagation in Solidity functions.

    Implements the taint rules defined in TAINT_RULES.md.
    Uses Slither's data dependency analysis when available.
    """

    def __init__(self, contract: Any) -> None:
        """Initialize analyzer for a contract.

        Args:
            contract: Slither contract object.
        """
        self.contract = contract
        self._storage_taint: dict[str, TaintResult] = {}
        self._has_delegatecall = False
        self._has_inline_assembly = False

    def analyze_function(self, fn: Any) -> dict[str, TaintResult]:
        """Analyze taint for all variables in a function.

        Args:
            fn: Slither function object.

        Returns:
            Dict mapping variable names to their TaintResult.
        """
        results: dict[str, TaintResult] = {}

        # Check for delegatecall/assembly that affect availability
        self._check_availability_blockers(fn)

        # If delegatecall present, mark all as unknown
        if self._has_delegatecall:
            for var in getattr(fn, "variables", []) or []:
                name = _variable_name(var)
                results[name] = TaintResult.unknown(
                    "delegatecall present - storage effects unknown"
                )
            return results

        # Extract input sources
        inputs = extract_inputs(fn)
        special = extract_special_sources(fn)
        all_sources = inputs + special

        # Analyze each variable
        for var in getattr(fn, "variables", []) or []:
            name = _variable_name(var)
            results[name] = self._analyze_variable(fn, var, all_sources)

        return results

    def analyze_variable(
        self,
        fn: Any,
        var: Any,
        sink: Optional[TaintSink] = None,
    ) -> TaintResult:
        """Analyze taint for a specific variable.

        Args:
            fn: Slither function object.
            var: Variable to analyze.
            sink: Optional sink to check reachability to.

        Returns:
            TaintResult for the variable.
        """
        self._check_availability_blockers(fn)

        if self._has_delegatecall:
            return TaintResult.unknown(
                "delegatecall present - storage effects unknown"
            )

        if self._has_inline_assembly:
            return TaintResult.unknown("inline assembly - opaque to analysis")

        inputs = extract_inputs(fn)
        special = extract_special_sources(fn)
        all_sources = inputs + special

        result = self._analyze_variable(fn, var, all_sources)
        if sink is not None:
            result.sink = sink
        return result

    def _check_availability_blockers(self, fn: Any) -> None:
        """Check for delegatecall/assembly that block analysis."""
        # Check for delegatecall
        external_calls = getattr(fn, "high_level_calls", []) or []
        for call_info in external_calls:
            # call_info is typically (contract, function) tuple
            call_fn = call_info[1] if isinstance(call_info, tuple) else call_info
            call_name = getattr(call_fn, "name", str(call_fn))
            if "delegatecall" in str(call_name).lower():
                self._has_delegatecall = True

        low_level_calls = getattr(fn, "low_level_calls", []) or []
        for call_info in low_level_calls:
            call_type = call_info[1] if isinstance(call_info, tuple) else str(call_info)
            if "delegatecall" in str(call_type).lower():
                self._has_delegatecall = True

        # Check for inline assembly
        if getattr(fn, "contains_assembly", False):
            self._has_inline_assembly = True

    def _analyze_variable(
        self,
        fn: Any,
        var: Any,
        sources: list[InputSource],
    ) -> TaintResult:
        """Analyze taint for a variable given sources."""
        if is_dependent is None:
            return TaintResult.unknown("slither data dependency not available")

        name = _variable_name(var)
        taint_sources: list[TaintSource] = []
        path: list[str] = []

        # Check dependency on each source
        for source in sources:
            if source.var is None:
                continue
            try:
                dependent = _safe_is_dependent(var, source.var, self.contract)
            except Exception:
                LOGGER.debug(
                    "taint_check_failed",
                    var=name,
                    source=source.name,
                )
                continue

            if dependent:
                taint_type = self._classify_source(source)
                taint_sources.append(taint_type)
                path.append(f"{source.name} -> {name}")

        # Check if variable reads from tainted storage
        storage_taint = self._check_storage_alias(fn, var)
        if storage_taint:
            taint_sources.append(TaintSource.STORAGE_ALIASED)
            path.extend(storage_taint.path)
            # Use aliased availability (lower confidence)
            if taint_sources:
                return TaintResult.tainted(
                    sources=taint_sources,
                    path=path,
                    availability=TaintAvailability.aliased(),
                )

        if taint_sources:
            return TaintResult.tainted(sources=taint_sources, path=path)
        else:
            return TaintResult.safe()

    def _classify_source(self, source: InputSource) -> TaintSource:
        """Classify an InputSource into a TaintSource type."""
        if source.kind == "parameter":
            return TaintSource.USER_INPUT
        elif source.kind == "env":
            return TaintSource.ENVIRONMENT
        elif source.kind == "external_return":
            return TaintSource.EXTERNAL_RETURN
        elif source.kind == "oracle":
            return TaintSource.ORACLE
        elif source.kind == "call_target":
            return TaintSource.CALL_TARGET_CONTROL
        else:
            return TaintSource.USER_INPUT  # Default to user input

    def _check_storage_alias(self, fn: Any, var: Any) -> Optional[TaintResult]:
        """Check if variable reads from tainted storage."""
        name = _variable_name(var)

        # Check if this reads from storage we've marked as tainted
        if name in self._storage_taint:
            return self._storage_taint[name]

        # Check if variable is a storage read
        state_vars_read = getattr(fn, "state_variables_read", []) or []
        for state_var in state_vars_read:
            state_name = _variable_name(state_var)
            if state_name in self._storage_taint:
                return self._storage_taint[state_name]

        return None

    def mark_storage_tainted(
        self,
        slot_name: str,
        sources: list[TaintSource],
        path: Optional[list[str]] = None,
    ) -> None:
        """Mark a storage slot as tainted.

        Used when tainted value is written to storage.
        """
        self._storage_taint[slot_name] = TaintResult.tainted(
            sources=sources,
            path=path or [f"storage:{slot_name}"],
            availability=TaintAvailability.aliased(),
        )

    def clear_storage_taint(self, slot_name: str) -> None:
        """Clear taint from a storage slot."""
        self._storage_taint.pop(slot_name, None)

    def get_storage_taint(self) -> dict[str, TaintResult]:
        """Get all tainted storage slots."""
        return dict(self._storage_taint)


# =============================================================================
# Legacy API (backward compatibility)
# =============================================================================


@dataclass
class InputSource:
    """Represents an input source to a function."""

    name: str
    kind: str
    var: Any | None = None


def extract_inputs(fn: Any) -> list[InputSource]:
    """Extract parameter inputs from a function."""
    sources: list[InputSource] = []
    parameters = getattr(fn, "parameters", []) or []
    for idx, param in enumerate(parameters):
        name = getattr(param, "name", None) or f"arg{idx}"
        sources.append(InputSource(name=name, kind="parameter", var=param))
    return sources


def extract_special_sources(fn: Any) -> list[InputSource]:
    """Extract environment sources (msg.sender, etc.) from a function."""
    sources: list[InputSource] = []
    variables = getattr(fn, "variables_read", []) or []
    for var in variables:
        name = _variable_name(var)
        if name in {"msg.sender", "tx.origin", "msg.value"}:
            sources.append(InputSource(name=name, kind="env", var=var))
    return sources


def extract_external_return_sources(fn: Any) -> list[InputSource]:
    """Extract external call return value sources."""
    sources: list[InputSource] = []
    external_calls = getattr(fn, "external_calls_as_expressions", []) or []
    for idx, call in enumerate(external_calls):
        call_str = str(call)
        sources.append(
            InputSource(
                name=f"external_return_{idx}",
                kind="external_return",
                var=call,
            )
        )
    return sources


def extract_oracle_sources(fn: Any) -> list[InputSource]:
    """Extract oracle data sources (Chainlink, etc.)."""
    sources: list[InputSource] = []
    # Check for known oracle patterns
    oracle_patterns = [
        "latestAnswer",
        "latestRoundData",
        "getPrice",
        "getRate",
        "consult",  # Uniswap TWAP
    ]
    external_calls = getattr(fn, "external_calls_as_expressions", []) or []
    for idx, call in enumerate(external_calls):
        call_str = str(call)
        for pattern in oracle_patterns:
            if pattern in call_str:
                sources.append(
                    InputSource(
                        name=f"oracle_{idx}",
                        kind="oracle",
                        var=call,
                    )
                )
                break
    return sources


def compute_dataflow(
    contract: Any,
    inputs: list[InputSource],
    state_vars_written: list[Any],
) -> tuple[list[tuple[InputSource, Any]], bool]:
    """Compute dataflow edges from inputs to state variables.

    Legacy API - consider using TaintAnalyzer for new code.
    """
    if is_dependent is None:
        return [], False
    edges: list[tuple[InputSource, Any]] = []
    for state_var in state_vars_written:
        for source in inputs:
            if source.var is None:
                continue
            try:
                dependent = _safe_is_dependent(state_var, source.var, contract)
            except Exception:  # pragma: no cover - defensive on slither API changes
                LOGGER.debug(
                    "dataflow_check_failed",
                    source=source.name,
                    state_var=str(state_var),
                )
                dependent = False
            if dependent:
                edges.append((source, state_var))
    return edges, True


def _safe_is_dependent(state_var: Any, source_var: Any, contract: Any) -> bool:
    """Safely check dependency with fallback for Slither API changes."""
    try:
        return bool(is_dependent(state_var, source_var, contract))
    except TypeError:
        return bool(is_dependent(state_var, source_var))


def _variable_name(var: Any) -> str:
    """Extract variable name safely."""
    name = getattr(var, "name", None)
    if name:
        return name
    return str(var)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core types
    "TaintSource",
    "TaintSink",
    "TaintSanitizer",
    "TaintAvailability",
    "TaintResult",
    # Analyzer
    "TaintAnalyzer",
    # Risk/severity mappings
    "TAINT_SOURCE_RISK",
    "TAINT_SINK_SEVERITY",
    "SANITIZER_AFFECTS",
    # Legacy API
    "InputSource",
    "extract_inputs",
    "extract_special_sources",
    "extract_external_return_sources",
    "extract_oracle_sources",
    "compute_dataflow",
]
