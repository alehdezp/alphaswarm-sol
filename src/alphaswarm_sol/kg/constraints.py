"""Phase 11: Constraint-Based Verification.

This module provides constraint extraction and Z3-based verification
for detecting logic bugs and checking vulnerability reachability.

Key features:
- Constraint extraction from Slither CFG nodes
- Z3 model building from constraints and state variables
- Vulnerability reachability checking
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set, Union
from enum import Enum
import re

# Optional Z3 import
try:
    from z3 import (
        Int, Bool, BitVec, Solver,
        And, Or, Not, Implies,
        sat, unsat, unknown,
        IntVal, BoolVal,
    )
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False
    # Stubs for type hints
    Solver = Any
    Int = Any
    Bool = Any
    BitVec = Any


class ConstraintType(str, Enum):
    """Types of constraints extracted from code."""
    BRANCH = "branch"           # if/else conditions
    REQUIRE = "require"         # require() statements
    ASSERT = "assert"           # assert() statements
    LOOP_BOUND = "loop_bound"   # loop conditions
    MODIFIER = "modifier"       # modifier conditions
    ARITHMETIC = "arithmetic"   # arithmetic constraints


@dataclass
class SourceLocation:
    """Source code location for a constraint."""
    file: str = ""
    line_start: int = 0
    line_end: int = 0
    column_start: int = 0
    column_end: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "column_start": self.column_start,
            "column_end": self.column_end,
        }


@dataclass
class Constraint:
    """Represents a constraint extracted from code.

    Attributes:
        type: Type of constraint (branch, require, assert, etc.)
        expression: String representation of the constraint expression
        variables: Set of variable names referenced
        location: Source code location
        negated: Whether this constraint is negated (else branch)
    """
    type: ConstraintType
    expression: str
    variables: Set[str] = field(default_factory=set)
    location: Optional[SourceLocation] = None
    negated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "expression": self.expression,
            "variables": list(self.variables),
            "location": self.location.to_dict() if self.location else None,
            "negated": self.negated,
        }


@dataclass
class StateVariable:
    """Represents a state variable for Z3 modeling.

    Attributes:
        name: Variable name
        var_type: Solidity type (uint256, bool, address, etc.)
        is_mapping: Whether it's a mapping type
        initial_value: Optional initial value
    """
    name: str
    var_type: str
    is_mapping: bool = False
    initial_value: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "var_type": self.var_type,
            "is_mapping": self.is_mapping,
            "initial_value": self.initial_value,
        }


@dataclass
class PathCondition:
    """Represents path conditions for a specific execution path.

    Attributes:
        path_id: Unique identifier for the path
        constraints: List of constraints along the path
        reachable: Whether the path is satisfiable
        model: Z3 model if satisfiable
    """
    path_id: str
    constraints: List[Constraint] = field(default_factory=list)
    reachable: Optional[bool] = None
    model: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "constraints": [c.to_dict() for c in self.constraints],
            "reachable": self.reachable,
            "model": self.model,
        }


def extract_variables(expression: str) -> Set[str]:
    """Extract variable names from an expression string.

    Args:
        expression: Expression string (e.g., "x > 0 && y < 10")

    Returns:
        Set of variable names found
    """
    # Simple regex to find variable-like identifiers
    # Excludes common Solidity keywords and functions
    keywords = {
        "true", "false", "msg", "sender", "value", "block", "timestamp",
        "now", "this", "require", "assert", "revert", "if", "else",
        "while", "for", "return", "address", "uint256", "int256", "bool",
        "bytes32", "bytes", "string", "mapping", "struct", "enum",
    }

    # Find all identifiers
    pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
    matches = re.findall(pattern, expression)

    # Filter out keywords and add remaining
    variables = {m for m in matches if m.lower() not in keywords}
    return variables


def extract_constraints_from_node(
    node: Any,
    node_type: str = "",
) -> List[Constraint]:
    """Extract constraints from a Slither CFG node.

    Args:
        node: Slither Node object
        node_type: Override for node type detection

    Returns:
        List of constraints extracted from the node
    """
    constraints: List[Constraint] = []

    # Get node type
    if hasattr(node, "type"):
        node_type = str(node.type.name) if hasattr(node.type, "name") else str(node.type)

    # Get source mapping for location
    location = None
    if hasattr(node, "source_mapping"):
        sm = node.source_mapping
        location = SourceLocation(
            file=getattr(sm, "filename_short", "") or "",
            line_start=getattr(sm, "lines", [0])[0] if hasattr(sm, "lines") and sm.lines else 0,
            line_end=getattr(sm, "lines", [0])[-1] if hasattr(sm, "lines") and sm.lines else 0,
        )

    # Handle IF nodes
    if "IF" in node_type:
        if hasattr(node, "expression"):
            expr_str = str(node.expression) if node.expression else ""
            if expr_str:
                variables = extract_variables(expr_str)
                constraints.append(Constraint(
                    type=ConstraintType.BRANCH,
                    expression=expr_str,
                    variables=variables,
                    location=location,
                    negated=False,
                ))

    # Handle EXPRESSION nodes that might contain require/assert
    if "EXPRESSION" in node_type or not node_type:
        if hasattr(node, "expression"):
            expr_str = str(node.expression) if node.expression else ""

            # Check for require
            if "require" in expr_str.lower():
                # Extract the condition inside require()
                match = re.search(r'require\s*\(\s*(.+?)(?:,|$|\))', expr_str)
                if match:
                    condition = match.group(1).strip()
                    variables = extract_variables(condition)
                    constraints.append(Constraint(
                        type=ConstraintType.REQUIRE,
                        expression=condition,
                        variables=variables,
                        location=location,
                    ))

            # Check for assert
            if "assert" in expr_str.lower():
                match = re.search(r'assert\s*\(\s*(.+?)\)', expr_str)
                if match:
                    condition = match.group(1).strip()
                    variables = extract_variables(condition)
                    constraints.append(Constraint(
                        type=ConstraintType.ASSERT,
                        expression=condition,
                        variables=variables,
                        location=location,
                    ))

    # Handle loop conditions
    if "BEGIN_LOOP" in node_type or "WHILE" in node_type or "FOR" in node_type:
        if hasattr(node, "expression"):
            expr_str = str(node.expression) if node.expression else ""
            if expr_str:
                variables = extract_variables(expr_str)
                constraints.append(Constraint(
                    type=ConstraintType.LOOP_BOUND,
                    expression=expr_str,
                    variables=variables,
                    location=location,
                ))

    return constraints


def extract_constraints(function: Any) -> List[Constraint]:
    """Extract all constraints from a Slither function.

    Args:
        function: Slither Function object

    Returns:
        List of constraints extracted from the function
    """
    constraints: List[Constraint] = []

    # Check if function has CFG nodes
    if not hasattr(function, "nodes"):
        return constraints

    for node in function.nodes:
        node_constraints = extract_constraints_from_node(node)
        constraints.extend(node_constraints)

    return constraints


def extract_state_variables(contract: Any) -> List[StateVariable]:
    """Extract state variables from a Slither contract.

    Args:
        contract: Slither Contract object

    Returns:
        List of StateVariable objects
    """
    state_vars: List[StateVariable] = []

    if not hasattr(contract, "state_variables"):
        return state_vars

    for var in contract.state_variables:
        var_type = str(var.type) if hasattr(var, "type") else "unknown"
        is_mapping = "mapping" in var_type.lower()

        state_vars.append(StateVariable(
            name=var.name,
            var_type=var_type,
            is_mapping=is_mapping,
        ))

    return state_vars


class Z3ModelBuilder:
    """Builds Z3 models from constraints and state variables.

    This class creates Z3 variables and constraints for symbolic verification.
    """

    def __init__(self):
        """Initialize the model builder."""
        if not Z3_AVAILABLE:
            raise RuntimeError("Z3 is not available. Install with: pip install z3-solver")

        self.solver = Solver()
        self.z3_vars: Dict[str, Any] = {}
        self._constraints_added: List[Constraint] = []

    def add_state_variable(self, var: StateVariable) -> Any:
        """Add a state variable to the Z3 model.

        Args:
            var: StateVariable to add

        Returns:
            Z3 variable created
        """
        if var.name in self.z3_vars:
            return self.z3_vars[var.name]

        # Map Solidity types to Z3 types
        var_type = var.var_type.lower()

        if "uint" in var_type or "int" in var_type:
            z3_var = Int(var.name)
            # Add non-negative constraint for uint
            if "uint" in var_type:
                self.solver.add(z3_var >= 0)
            self.z3_vars[var.name] = z3_var

        elif "bool" in var_type:
            z3_var = Bool(var.name)
            self.z3_vars[var.name] = z3_var

        elif "address" in var_type:
            # Addresses are 160-bit values
            z3_var = BitVec(var.name, 160)
            self.z3_vars[var.name] = z3_var

        elif "bytes32" in var_type:
            z3_var = BitVec(var.name, 256)
            self.z3_vars[var.name] = z3_var

        else:
            # Default to Int for unknown types
            z3_var = Int(var.name)
            self.z3_vars[var.name] = z3_var

        return z3_var

    def add_constraint(self, constraint: Constraint) -> bool:
        """Add a constraint to the Z3 solver.

        Args:
            constraint: Constraint to add

        Returns:
            True if constraint was added successfully
        """
        try:
            z3_expr = self._parse_expression(constraint.expression)
            if z3_expr is not None:
                if constraint.negated:
                    z3_expr = Not(z3_expr)
                self.solver.add(z3_expr)
                self._constraints_added.append(constraint)
                return True
        except Exception:
            pass  # Skip unparseable constraints
        return False

    def _parse_expression(self, expr: str) -> Optional[Any]:
        """Parse a string expression to Z3.

        This is a simplified parser for common patterns.

        Args:
            expr: Expression string

        Returns:
            Z3 expression or None if unparseable
        """
        if not Z3_AVAILABLE:
            return None

        expr = expr.strip()

        # Handle boolean literals
        if expr.lower() == "true":
            return BoolVal(True)
        if expr.lower() == "false":
            return BoolVal(False)

        # Handle simple comparisons
        patterns = [
            (r'(\w+)\s*==\s*(\w+)', lambda m: self._get_var(m.group(1)) == self._get_var(m.group(2))),
            (r'(\w+)\s*!=\s*(\w+)', lambda m: self._get_var(m.group(1)) != self._get_var(m.group(2))),
            (r'(\w+)\s*>=\s*(\w+)', lambda m: self._get_var(m.group(1)) >= self._get_var(m.group(2))),
            (r'(\w+)\s*<=\s*(\w+)', lambda m: self._get_var(m.group(1)) <= self._get_var(m.group(2))),
            (r'(\w+)\s*>\s*(\w+)', lambda m: self._get_var(m.group(1)) > self._get_var(m.group(2))),
            (r'(\w+)\s*<\s*(\w+)', lambda m: self._get_var(m.group(1)) < self._get_var(m.group(2))),
        ]

        for pattern, builder in patterns:
            match = re.fullmatch(pattern, expr)
            if match:
                try:
                    return builder(match)
                except Exception:
                    pass

        # Handle logical operations
        if "&&" in expr:
            parts = expr.split("&&")
            sub_exprs = [self._parse_expression(p.strip()) for p in parts]
            sub_exprs = [e for e in sub_exprs if e is not None]
            if sub_exprs:
                return And(*sub_exprs)

        if "||" in expr:
            parts = expr.split("||")
            sub_exprs = [self._parse_expression(p.strip()) for p in parts]
            sub_exprs = [e for e in sub_exprs if e is not None]
            if sub_exprs:
                return Or(*sub_exprs)

        if expr.startswith("!"):
            inner = self._parse_expression(expr[1:].strip())
            if inner is not None:
                return Not(inner)

        return None

    def _get_var(self, name: str) -> Any:
        """Get or create a Z3 variable.

        Args:
            name: Variable name or literal

        Returns:
            Z3 variable or value
        """
        # Check if it's a number
        try:
            return IntVal(int(name))
        except ValueError:
            pass

        # Check if it's an existing variable
        if name in self.z3_vars:
            return self.z3_vars[name]

        # Create new Int variable
        z3_var = Int(name)
        self.z3_vars[name] = z3_var
        return z3_var

    def check_satisfiability(self) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Check if the current constraints are satisfiable.

        Returns:
            Tuple of (result, model) where result is "sat", "unsat", or "unknown"
        """
        result = self.solver.check()

        if result == sat:
            model = self.solver.model()
            model_dict = {}
            for var_name, z3_var in self.z3_vars.items():
                try:
                    val = model.eval(z3_var, model_completion=True)
                    model_dict[var_name] = str(val)
                except Exception:
                    model_dict[var_name] = "?"
            return "sat", model_dict

        elif result == unsat:
            return "unsat", None

        else:
            return "unknown", None

    def push(self) -> None:
        """Push solver state."""
        self.solver.push()

    def pop(self) -> None:
        """Pop solver state."""
        self.solver.pop()

    def reset(self) -> None:
        """Reset the solver and variables."""
        self.solver = Solver()
        self.z3_vars.clear()
        self._constraints_added.clear()


def build_z3_model(
    constraints: List[Constraint],
    state_vars: List[StateVariable],
) -> Tuple[Optional[Z3ModelBuilder], Dict[str, Any]]:
    """Build a Z3 model from constraints and state variables.

    Args:
        constraints: List of constraints
        state_vars: List of state variables

    Returns:
        Tuple of (builder, z3_vars dict) or (None, {}) if Z3 unavailable
    """
    if not Z3_AVAILABLE:
        return None, {}

    builder = Z3ModelBuilder()

    # Add state variables
    for var in state_vars:
        builder.add_state_variable(var)

    # Add constraints
    for constraint in constraints:
        builder.add_constraint(constraint)

    return builder, builder.z3_vars


def check_vulnerability_reachable(
    builder: Z3ModelBuilder,
    vuln_condition: str,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check if a vulnerability condition is reachable.

    Args:
        builder: Z3ModelBuilder with current path constraints
        vuln_condition: String representation of vulnerability condition

    Returns:
        Tuple of (is_reachable, model) where model contains values if reachable
    """
    if not Z3_AVAILABLE or builder is None:
        return False, None

    # Save state
    builder.push()

    try:
        # Parse and add vulnerability condition
        vuln_expr = builder._parse_expression(vuln_condition)
        if vuln_expr is not None:
            builder.solver.add(vuln_expr)

        # Check satisfiability
        result, model = builder.check_satisfiability()

        if result == "sat":
            return True, model
        return False, None

    finally:
        # Restore state
        builder.pop()


@dataclass
class VulnerabilityCheck:
    """Result of a vulnerability reachability check.

    Attributes:
        vuln_type: Type of vulnerability checked
        condition: The condition that was checked
        is_reachable: Whether the vulnerability is reachable
        model: Counter-example if reachable
        confidence: Confidence in the result
    """
    vuln_type: str
    condition: str
    is_reachable: bool
    model: Optional[Dict[str, Any]] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vuln_type": self.vuln_type,
            "condition": self.condition,
            "is_reachable": self.is_reachable,
            "model": self.model,
            "confidence": self.confidence,
        }


class ConstraintVerifier:
    """High-level constraint-based verification.

    Combines constraint extraction and Z3 verification to check
    for various vulnerability conditions.
    """

    # Common vulnerability conditions
    VULN_CONDITIONS = {
        "integer_overflow": "result > MAX_UINT256",
        "integer_underflow": "result < 0",
        "division_by_zero": "divisor == 0",
        "unauthorized_access": "msg_sender != owner",
        "reentrancy_state": "balance > 0 && external_call_made",
        "array_out_of_bounds": "index >= array_length",
    }

    def __init__(self):
        """Initialize the verifier."""
        self.builder: Optional[Z3ModelBuilder] = None
        self.constraints: List[Constraint] = []
        self.state_vars: List[StateVariable] = []

    def load_function(self, function: Any) -> int:
        """Load constraints from a function.

        Args:
            function: Slither Function object

        Returns:
            Number of constraints extracted
        """
        self.constraints = extract_constraints(function)

        # Get contract's state variables
        if hasattr(function, "contract"):
            self.state_vars = extract_state_variables(function.contract)

        return len(self.constraints)

    def build_model(self) -> bool:
        """Build Z3 model from loaded constraints.

        Returns:
            True if model was built successfully
        """
        if not Z3_AVAILABLE:
            return False

        self.builder, _ = build_z3_model(self.constraints, self.state_vars)
        return self.builder is not None

    def check_vulnerability(
        self,
        vuln_type: str,
        custom_condition: Optional[str] = None,
    ) -> VulnerabilityCheck:
        """Check if a vulnerability type is reachable.

        Args:
            vuln_type: Type of vulnerability (from VULN_CONDITIONS keys)
            custom_condition: Optional custom condition string

        Returns:
            VulnerabilityCheck result
        """
        condition = custom_condition or self.VULN_CONDITIONS.get(vuln_type, "false")

        if not Z3_AVAILABLE or self.builder is None:
            return VulnerabilityCheck(
                vuln_type=vuln_type,
                condition=condition,
                is_reachable=False,
                confidence=0.0,  # Low confidence without Z3
            )

        is_reachable, model = check_vulnerability_reachable(self.builder, condition)

        return VulnerabilityCheck(
            vuln_type=vuln_type,
            condition=condition,
            is_reachable=is_reachable,
            model=model,
            confidence=1.0 if is_reachable else 0.9,
        )

    def check_all_vulnerabilities(self) -> List[VulnerabilityCheck]:
        """Check all known vulnerability conditions.

        Returns:
            List of VulnerabilityCheck results
        """
        results = []
        for vuln_type in self.VULN_CONDITIONS:
            result = self.check_vulnerability(vuln_type)
            results.append(result)
        return results


__all__ = [
    "ConstraintType",
    "SourceLocation",
    "Constraint",
    "StateVariable",
    "PathCondition",
    "extract_variables",
    "extract_constraints_from_node",
    "extract_constraints",
    "extract_state_variables",
    "Z3ModelBuilder",
    "build_z3_model",
    "check_vulnerability_reachable",
    "VulnerabilityCheck",
    "ConstraintVerifier",
    "Z3_AVAILABLE",
]
