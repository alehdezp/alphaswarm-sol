"""Trace2Inv-style invariant patterns for mining from transaction traces.

Per 05.11-CONTEXT.md: Invariant patterns enable automated discovery of
protocol invariants from execution traces. Each pattern type represents
a class of invariants that can be mined from observed transaction behavior.

Pattern Types (Trace2Inv-inspired):
- MappingUpperBound: balance[user] <= totalSupply
- MappingLowerBound: balance[user] >= 0
- CallValueUpperBound: msg.value <= maxDeposit
- StateTransitionConstraint: state can only go A->B->C
- VariableRelation: reserveA * reserveB >= k (AMM)
- SumInvariant: sum(balances) == totalSupply
- MonotonicProperty: counter only increases

Usage:
    from alphaswarm_sol.economics.invariants.patterns import (
        InvariantPattern,
        MappingUpperBound,
        SumInvariant,
        VariableRelation,
    )

    pattern = MappingUpperBound(
        mapping_name="balances",
        bound_expression="totalSupply",
        confidence=0.95
    )

    # Check if trace satisfies pattern
    satisfied = pattern.check_trace(trace_data)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class InvariantPatternType(Enum):
    """Types of invariant patterns that can be mined from traces.

    Per 05.11-CONTEXT.md: Trace2Inv-style pattern types for automated
    invariant discovery.
    """

    MAPPING_UPPER_BOUND = "mapping_upper_bound"  # balance[user] <= totalSupply
    MAPPING_LOWER_BOUND = "mapping_lower_bound"  # balance[user] >= 0
    CALL_VALUE_UPPER_BOUND = "call_value_upper_bound"  # msg.value <= maxDeposit
    STATE_TRANSITION = "state_transition"  # state can only go A->B->C
    VARIABLE_RELATION = "variable_relation"  # reserveA * reserveB >= k
    SUM_INVARIANT = "sum_invariant"  # sum(balances) == totalSupply
    MONOTONIC_PROPERTY = "monotonic_property"  # counter only increases
    RATIO_BOUND = "ratio_bound"  # ratio <= maxRatio
    DIFFERENCE_BOUND = "difference_bound"  # diff <= maxDiff
    EQUALITY = "equality"  # a == b always


@dataclass
class InvariantPattern(ABC):
    """Base class for invariant patterns.

    Per 05.11-CONTEXT.md: Patterns describe invariant structures that can be
    mined from transaction traces. Each pattern type has specific extraction
    and validation logic.

    Attributes:
        pattern_type: Type of invariant pattern
        name: Human-readable name
        description: Pattern description
        base_confidence: Default confidence for this pattern type
    """

    pattern_type: InvariantPatternType
    name: str
    description: str = ""
    base_confidence: float = 0.7

    @abstractmethod
    def check_trace(self, trace: Dict[str, Any]) -> bool:
        """Check if a trace satisfies this pattern.

        Args:
            trace: Execution trace with state snapshots

        Returns:
            True if pattern is satisfied
        """

    @abstractmethod
    def extract_expression(self) -> str:
        """Extract formal expression for this pattern.

        Returns:
            String expression (e.g., "balance[user] <= totalSupply")
        """

    @abstractmethod
    def to_require_condition(self) -> str:
        """Convert pattern to Solidity require() condition.

        Returns:
            Solidity expression for require()
        """

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern_type": self.pattern_type.value,
            "name": self.name,
            "description": self.description,
            "base_confidence": self.base_confidence,
            "expression": self.extract_expression(),
        }


@dataclass
class MappingUpperBound(InvariantPattern):
    """Mapping upper bound pattern: mapping[key] <= bound.

    Per 05.11-CONTEXT.md: Commonly found in ERC20 tokens where
    balance[user] <= totalSupply must hold.

    Attributes:
        mapping_name: Name of the mapping (e.g., "balances")
        bound_expression: Upper bound expression (e.g., "totalSupply")
        key_type: Type of mapping key (e.g., "address")
    """

    mapping_name: str = ""
    bound_expression: str = ""
    key_type: str = "address"
    pattern_type: InvariantPatternType = field(
        default=InvariantPatternType.MAPPING_UPPER_BOUND, init=False
    )
    name: str = field(default="Mapping Upper Bound", init=False)

    def __post_init__(self) -> None:
        """Set description based on mapping and bound."""
        self.description = f"{self.mapping_name}[{self.key_type}] <= {self.bound_expression}"

    def check_trace(self, trace: Dict[str, Any]) -> bool:
        """Check if all mapping values are bounded in trace."""
        state = trace.get("state", {})
        mapping_values = state.get(self.mapping_name, {})
        bound_value = state.get(self.bound_expression, float("inf"))

        if isinstance(bound_value, str):
            bound_value = int(bound_value, 16) if bound_value.startswith("0x") else int(bound_value)

        for key, value in mapping_values.items():
            if isinstance(value, str):
                value = int(value, 16) if value.startswith("0x") else int(value)
            if value > bound_value:
                return False
        return True

    def extract_expression(self) -> str:
        """Extract formal expression."""
        return f"forall({self.key_type} k) {self.mapping_name}[k] <= {self.bound_expression}"

    def to_require_condition(self) -> str:
        """Convert to require condition."""
        return f"{self.mapping_name}[key] <= {self.bound_expression}"


@dataclass
class MappingLowerBound(InvariantPattern):
    """Mapping lower bound pattern: mapping[key] >= bound.

    Per 05.11-CONTEXT.md: Ensures non-negative values in mappings,
    commonly balance[user] >= 0.

    Attributes:
        mapping_name: Name of the mapping
        bound_value: Lower bound value (usually 0)
        key_type: Type of mapping key
    """

    mapping_name: str = ""
    bound_value: int = 0
    key_type: str = "address"
    pattern_type: InvariantPatternType = field(
        default=InvariantPatternType.MAPPING_LOWER_BOUND, init=False
    )
    name: str = field(default="Mapping Lower Bound", init=False)

    def __post_init__(self) -> None:
        """Set description based on mapping and bound."""
        self.description = f"{self.mapping_name}[{self.key_type}] >= {self.bound_value}"

    def check_trace(self, trace: Dict[str, Any]) -> bool:
        """Check if all mapping values are above bound in trace."""
        state = trace.get("state", {})
        mapping_values = state.get(self.mapping_name, {})

        for key, value in mapping_values.items():
            if isinstance(value, str):
                value = int(value, 16) if value.startswith("0x") else int(value)
            if value < self.bound_value:
                return False
        return True

    def extract_expression(self) -> str:
        """Extract formal expression."""
        return f"forall({self.key_type} k) {self.mapping_name}[k] >= {self.bound_value}"

    def to_require_condition(self) -> str:
        """Convert to require condition."""
        return f"{self.mapping_name}[key] >= {self.bound_value}"


@dataclass
class CallValueUpperBound(InvariantPattern):
    """Call value upper bound pattern: msg.value <= maxDeposit.

    Per 05.11-CONTEXT.md: Constrains ETH sent in transactions to
    prevent flash loan attacks or deposit manipulation.

    Attributes:
        bound_variable: Variable representing the bound (e.g., "maxDeposit")
        function_selector: Optional function selector to apply to
    """

    bound_variable: str = ""
    function_selector: Optional[str] = None
    pattern_type: InvariantPatternType = field(
        default=InvariantPatternType.CALL_VALUE_UPPER_BOUND, init=False
    )
    name: str = field(default="Call Value Upper Bound", init=False)

    def __post_init__(self) -> None:
        """Set description based on bound."""
        self.description = f"msg.value <= {self.bound_variable}"

    def check_trace(self, trace: Dict[str, Any]) -> bool:
        """Check if call value is within bounds."""
        call_value = trace.get("value", 0)
        state = trace.get("state", {})
        bound_value = state.get(self.bound_variable, float("inf"))

        if isinstance(call_value, str):
            call_value = int(call_value, 16) if call_value.startswith("0x") else int(call_value)
        if isinstance(bound_value, str):
            bound_value = int(bound_value, 16) if bound_value.startswith("0x") else int(bound_value)

        return call_value <= bound_value

    def extract_expression(self) -> str:
        """Extract formal expression."""
        return f"msg.value <= {self.bound_variable}"

    def to_require_condition(self) -> str:
        """Convert to require condition."""
        return f"msg.value <= {self.bound_variable}"


@dataclass
class StateTransitionConstraint(InvariantPattern):
    """State transition pattern: state can only follow valid transitions.

    Per 05.11-CONTEXT.md: Defines valid state machine transitions,
    e.g., state can only go A->B->C, not A->C directly.

    Attributes:
        state_variable: Name of the state variable
        valid_transitions: Dict mapping from_state -> [allowed_to_states]
        state_names: Optional mapping of state values to names
    """

    state_variable: str = ""
    valid_transitions: Dict[str, List[str]] = field(default_factory=dict)
    state_names: Dict[str, str] = field(default_factory=dict)
    pattern_type: InvariantPatternType = field(
        default=InvariantPatternType.STATE_TRANSITION, init=False
    )
    name: str = field(default="State Transition Constraint", init=False)

    def __post_init__(self) -> None:
        """Set description based on transitions."""
        if self.valid_transitions:
            transitions = ", ".join(
                f"{k}->{v}" for k, vs in self.valid_transitions.items() for v in vs
            )
            self.description = f"{self.state_variable} transitions: {transitions}"
        else:
            self.description = f"Valid transitions for {self.state_variable}"

    def check_trace(self, trace: Dict[str, Any]) -> bool:
        """Check if state transition in trace is valid."""
        pre_state = trace.get("pre_state", {})
        post_state = trace.get("post_state", trace.get("state", {}))

        old_state = str(pre_state.get(self.state_variable, ""))
        new_state = str(post_state.get(self.state_variable, ""))

        # If no transition, valid
        if old_state == new_state or not old_state:
            return True

        # Check if transition is valid
        allowed = self.valid_transitions.get(old_state, [])
        return new_state in allowed

    def extract_expression(self) -> str:
        """Extract formal expression."""
        transitions = " || ".join(
            f"({self.state_variable} == {k} => {self.state_variable}' in [{', '.join(v)}])"
            for k, v in self.valid_transitions.items()
        )
        return transitions or f"validTransition({self.state_variable})"

    def to_require_condition(self) -> str:
        """Convert to require condition."""
        # Generate require for a specific transition
        return f"validStateTransition({self.state_variable}, _newState)"


@dataclass
class VariableRelation(InvariantPattern):
    """Variable relation pattern: expr1 OP expr2.

    Per 05.11-CONTEXT.md: Captures relationships between variables,
    e.g., reserveA * reserveB >= k (constant product AMM).

    Attributes:
        left_expression: Left side of relation (e.g., "reserveA * reserveB")
        operator: Comparison operator (>=, <=, ==, !=)
        right_expression: Right side (e.g., "k")
    """

    left_expression: str = ""
    operator: str = ">="
    right_expression: str = ""
    pattern_type: InvariantPatternType = field(
        default=InvariantPatternType.VARIABLE_RELATION, init=False
    )
    name: str = field(default="Variable Relation", init=False)

    def __post_init__(self) -> None:
        """Set description based on relation."""
        self.description = f"{self.left_expression} {self.operator} {self.right_expression}"

    def check_trace(self, trace: Dict[str, Any]) -> bool:
        """Check if relation holds in trace state."""
        state = trace.get("state", {})

        # Simple evaluation - extract variable values
        try:
            left_val = self._evaluate_expression(self.left_expression, state)
            right_val = self._evaluate_expression(self.right_expression, state)

            if self.operator == ">=":
                return left_val >= right_val
            elif self.operator == "<=":
                return left_val <= right_val
            elif self.operator == "==":
                return left_val == right_val
            elif self.operator == "!=":
                return left_val != right_val
            elif self.operator == ">":
                return left_val > right_val
            elif self.operator == "<":
                return left_val < right_val
        except (KeyError, ValueError, TypeError):
            return True  # Can't evaluate, assume valid

        return True

    def _evaluate_expression(self, expr: str, state: Dict[str, Any]) -> int:
        """Evaluate simple expression against state."""
        # Handle multiplication
        if "*" in expr:
            parts = expr.split("*")
            result = 1
            for part in parts:
                val = state.get(part.strip(), 1)
                if isinstance(val, str):
                    val = int(val, 16) if val.startswith("0x") else int(val)
                result *= val
            return result

        # Handle addition
        if "+" in expr:
            parts = expr.split("+")
            result = 0
            for part in parts:
                val = state.get(part.strip(), 0)
                if isinstance(val, str):
                    val = int(val, 16) if val.startswith("0x") else int(val)
                result += val
            return result

        # Single variable or constant
        if expr.isdigit():
            return int(expr)
        val = state.get(expr.strip(), 0)
        if isinstance(val, str):
            val = int(val, 16) if val.startswith("0x") else int(val)
        return val

    def extract_expression(self) -> str:
        """Extract formal expression."""
        return f"{self.left_expression} {self.operator} {self.right_expression}"

    def to_require_condition(self) -> str:
        """Convert to require condition."""
        return f"{self.left_expression} {self.operator} {self.right_expression}"


@dataclass
class SumInvariant(InvariantPattern):
    """Sum invariant pattern: sum(values) == total.

    Per 05.11-CONTEXT.md: Conservation invariant common in ERC20 tokens
    where sum(balances) == totalSupply.

    Attributes:
        mapping_name: Name of mapping to sum (e.g., "balances")
        total_variable: Variable that should equal the sum (e.g., "totalSupply")
    """

    mapping_name: str = ""
    total_variable: str = ""
    pattern_type: InvariantPatternType = field(
        default=InvariantPatternType.SUM_INVARIANT, init=False
    )
    name: str = field(default="Sum Invariant", init=False)

    def __post_init__(self) -> None:
        """Set description based on mapping and total."""
        self.description = f"sum({self.mapping_name}) == {self.total_variable}"
        self.base_confidence = 0.85  # High confidence for conservation laws

    def check_trace(self, trace: Dict[str, Any]) -> bool:
        """Check if sum equals total in trace state."""
        state = trace.get("state", {})
        mapping_values = state.get(self.mapping_name, {})
        total = state.get(self.total_variable, 0)

        if isinstance(total, str):
            total = int(total, 16) if total.startswith("0x") else int(total)

        sum_values = 0
        for value in mapping_values.values():
            if isinstance(value, str):
                value = int(value, 16) if value.startswith("0x") else int(value)
            sum_values += value

        return sum_values == total

    def extract_expression(self) -> str:
        """Extract formal expression."""
        return f"sum({self.mapping_name}) == {self.total_variable}"

    def to_require_condition(self) -> str:
        """Convert to require condition."""
        # Sum invariants typically need a helper function
        return f"_sumOf{self.mapping_name.capitalize()}() == {self.total_variable}"


@dataclass
class MonotonicProperty(InvariantPattern):
    """Monotonic property pattern: variable only increases/decreases.

    Per 05.11-CONTEXT.md: Ensures variables like nonces, timestamps,
    or counters only change in one direction.

    Attributes:
        variable_name: Name of the variable
        direction: "increasing" or "decreasing"
        strict: Whether equality is allowed (non-strict) or not (strict)
    """

    variable_name: str = ""
    direction: str = "increasing"  # "increasing" or "decreasing"
    strict: bool = False  # If True, no equality allowed
    pattern_type: InvariantPatternType = field(
        default=InvariantPatternType.MONOTONIC_PROPERTY, init=False
    )
    name: str = field(default="Monotonic Property", init=False)

    def __post_init__(self) -> None:
        """Set description based on variable and direction."""
        op = ">" if self.strict else ">=" if self.direction == "increasing" else "<" if self.strict else "<="
        self.description = f"{self.variable_name}' {op} {self.variable_name}"
        self.base_confidence = 0.8

    def check_trace(self, trace: Dict[str, Any]) -> bool:
        """Check if variable maintains monotonicity."""
        pre_state = trace.get("pre_state", {})
        post_state = trace.get("post_state", trace.get("state", {}))

        old_val = pre_state.get(self.variable_name)
        new_val = post_state.get(self.variable_name)

        if old_val is None or new_val is None:
            return True  # Can't check, assume valid

        if isinstance(old_val, str):
            old_val = int(old_val, 16) if old_val.startswith("0x") else int(old_val)
        if isinstance(new_val, str):
            new_val = int(new_val, 16) if new_val.startswith("0x") else int(new_val)

        if self.direction == "increasing":
            return new_val > old_val if self.strict else new_val >= old_val
        else:
            return new_val < old_val if self.strict else new_val <= old_val

    def extract_expression(self) -> str:
        """Extract formal expression."""
        op = ">" if self.strict else ">=" if self.direction == "increasing" else "<" if self.strict else "<="
        return f"{self.variable_name}' {op} {self.variable_name}"

    def to_require_condition(self) -> str:
        """Convert to require condition."""
        op = ">" if self.strict else ">=" if self.direction == "increasing" else "<" if self.strict else "<="
        return f"_new{self.variable_name.capitalize()} {op} {self.variable_name}"


@dataclass
class RatioBound(InvariantPattern):
    """Ratio bound pattern: numerator / denominator <= maxRatio.

    Per 05.11-CONTEXT.md: Constrains ratios such as collateral ratios,
    fee percentages, or utilization rates.

    Attributes:
        numerator: Numerator variable
        denominator: Denominator variable
        max_ratio: Maximum allowed ratio (as a decimal, e.g., 0.8 for 80%)
        min_ratio: Minimum allowed ratio (optional)
    """

    numerator: str = ""
    denominator: str = ""
    max_ratio: float = 1.0
    min_ratio: float = 0.0
    pattern_type: InvariantPatternType = field(
        default=InvariantPatternType.RATIO_BOUND, init=False
    )
    name: str = field(default="Ratio Bound", init=False)

    def __post_init__(self) -> None:
        """Set description based on ratio bounds."""
        self.description = f"{self.min_ratio} <= {self.numerator}/{self.denominator} <= {self.max_ratio}"

    def check_trace(self, trace: Dict[str, Any]) -> bool:
        """Check if ratio is within bounds."""
        state = trace.get("state", {})
        num = state.get(self.numerator, 0)
        denom = state.get(self.denominator, 1)

        if isinstance(num, str):
            num = int(num, 16) if num.startswith("0x") else int(num)
        if isinstance(denom, str):
            denom = int(denom, 16) if denom.startswith("0x") else int(denom)

        if denom == 0:
            return True  # Avoid division by zero, assume valid

        ratio = num / denom
        return self.min_ratio <= ratio <= self.max_ratio

    def extract_expression(self) -> str:
        """Extract formal expression."""
        return f"{self.min_ratio} <= {self.numerator}/{self.denominator} <= {self.max_ratio}"

    def to_require_condition(self) -> str:
        """Convert to require condition."""
        # Multiply to avoid division: min * denom <= num <= max * denom
        return (
            f"{self.numerator} * 1e18 / {self.denominator} >= {int(self.min_ratio * 1e18)} && "
            f"{self.numerator} * 1e18 / {self.denominator} <= {int(self.max_ratio * 1e18)}"
        )


@dataclass
class DifferenceBound(InvariantPattern):
    """Difference bound pattern: |a - b| <= maxDiff.

    Per 05.11-CONTEXT.md: Constrains the difference between two values,
    useful for slippage protection or price bounds.

    Attributes:
        variable_a: First variable
        variable_b: Second variable
        max_difference: Maximum allowed difference
        relative: Whether difference is relative (percentage) or absolute
    """

    variable_a: str = ""
    variable_b: str = ""
    max_difference: int = 0
    relative: bool = False  # If True, max_difference is a percentage
    pattern_type: InvariantPatternType = field(
        default=InvariantPatternType.DIFFERENCE_BOUND, init=False
    )
    name: str = field(default="Difference Bound", init=False)

    def __post_init__(self) -> None:
        """Set description based on difference bound."""
        if self.relative:
            self.description = f"|{self.variable_a} - {self.variable_b}| <= {self.max_difference}% of {self.variable_a}"
        else:
            self.description = f"|{self.variable_a} - {self.variable_b}| <= {self.max_difference}"

    def check_trace(self, trace: Dict[str, Any]) -> bool:
        """Check if difference is within bounds."""
        state = trace.get("state", {})
        val_a = state.get(self.variable_a, 0)
        val_b = state.get(self.variable_b, 0)

        if isinstance(val_a, str):
            val_a = int(val_a, 16) if val_a.startswith("0x") else int(val_a)
        if isinstance(val_b, str):
            val_b = int(val_b, 16) if val_b.startswith("0x") else int(val_b)

        diff = abs(val_a - val_b)

        if self.relative:
            if val_a == 0:
                return diff == 0
            return (diff / val_a) * 100 <= self.max_difference
        else:
            return diff <= self.max_difference

    def extract_expression(self) -> str:
        """Extract formal expression."""
        if self.relative:
            return f"|{self.variable_a} - {self.variable_b}| <= {self.max_difference}% * {self.variable_a}"
        return f"|{self.variable_a} - {self.variable_b}| <= {self.max_difference}"

    def to_require_condition(self) -> str:
        """Convert to require condition."""
        if self.relative:
            return (
                f"({self.variable_a} >= {self.variable_b} ? "
                f"{self.variable_a} - {self.variable_b} : "
                f"{self.variable_b} - {self.variable_a}) * 100 <= "
                f"{self.variable_a} * {self.max_difference}"
            )
        return (
            f"({self.variable_a} >= {self.variable_b} ? "
            f"{self.variable_a} - {self.variable_b} : "
            f"{self.variable_b} - {self.variable_a}) <= {self.max_difference}"
        )


# Pattern templates for common invariant types
COMMON_PATTERNS: List[InvariantPattern] = [
    MappingUpperBound(
        mapping_name="balances",
        bound_expression="totalSupply",
        base_confidence=0.9,
    ),
    MappingLowerBound(
        mapping_name="balances",
        bound_value=0,
        base_confidence=0.95,
    ),
    SumInvariant(
        mapping_name="balances",
        total_variable="totalSupply",
        base_confidence=0.85,
    ),
    MonotonicProperty(
        variable_name="nonce",
        direction="increasing",
        strict=True,
        base_confidence=0.9,
    ),
    MonotonicProperty(
        variable_name="totalSupply",
        direction="increasing",
        strict=False,
        base_confidence=0.6,  # May decrease with burns
    ),
]


def get_pattern_for_type(pattern_type: InvariantPatternType) -> type:
    """Get pattern class for a pattern type.

    Args:
        pattern_type: InvariantPatternType enum

    Returns:
        Pattern class
    """
    type_map = {
        InvariantPatternType.MAPPING_UPPER_BOUND: MappingUpperBound,
        InvariantPatternType.MAPPING_LOWER_BOUND: MappingLowerBound,
        InvariantPatternType.CALL_VALUE_UPPER_BOUND: CallValueUpperBound,
        InvariantPatternType.STATE_TRANSITION: StateTransitionConstraint,
        InvariantPatternType.VARIABLE_RELATION: VariableRelation,
        InvariantPatternType.SUM_INVARIANT: SumInvariant,
        InvariantPatternType.MONOTONIC_PROPERTY: MonotonicProperty,
        InvariantPatternType.RATIO_BOUND: RatioBound,
        InvariantPatternType.DIFFERENCE_BOUND: DifferenceBound,
    }
    return type_map.get(pattern_type, InvariantPattern)


# Export all pattern types
__all__ = [
    "InvariantPatternType",
    "InvariantPattern",
    "MappingUpperBound",
    "MappingLowerBound",
    "CallValueUpperBound",
    "StateTransitionConstraint",
    "VariableRelation",
    "SumInvariant",
    "MonotonicProperty",
    "RatioBound",
    "DifferenceBound",
    "COMMON_PATTERNS",
    "get_pattern_for_type",
]
