"""
P2-T4: LLMDFA Verifier Agent

Grounds LLM claims in formal verification using Z3 SMT solver.
Uses LLM to synthesize constraints from attacker/defender arguments,
then executes Z3 to prove or disprove path feasibility.

Research Basis: LLMDFA (NeurIPS 2024) - LLM + SMT hybrid achieves high
accuracy by using LLM as code synthesizer, not reasoning engine.

Phase 5.9 Integration:
    This verifier works with the Phase 5.9 LLM graph interface skills:

    Evidence Validation:
        - /vrs-evidence-audit validates evidence IDs are deterministic and complete
        - Evidence must pass audit before being used in verification
        - Build hash verification ensures reproducible evidence

    Ordering Verification:
        - /vrs-ordering-proof provides dominance-based path ordering
        - ORDERING constraints (line 47) should align with ordering-proof output
        - Path-qualified ordering enables cross-function attack chain verification

    Contract Compliance:
        - /vrs-graph-contract-validate ensures Graph Interface Contract v2 compliance
        - Verifier inputs (function_code, attack, defense) must pass contract validation
        - Required evidence policy: all findings must have valid evidence packets

    See: src/alphaswarm_sol/shipping/README.md for skill catalog.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
import logging
import re
import tempfile
import os

logger = logging.getLogger(__name__)

# Try to import z3
try:
    import z3
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False
    z3 = None


class VerificationStatus(Enum):
    """Result status of verification."""
    SAT = "sat"              # Path is feasible, attack works
    UNSAT = "unsat"          # Path is blocked, attack fails
    UNKNOWN = "unknown"      # Z3 timeout or complexity limit
    ERROR = "error"          # Invalid script or Z3 failure


class ConstraintType(Enum):
    """Types of path constraints."""
    REQUIRE = "require"           # Explicit require statement
    IF_CONDITION = "if_condition" # Condition from if statement
    LOOP_BOUND = "loop_bound"     # Loop iteration constraint
    IMPLICIT = "implicit"         # Inferred from semantics
    ORDERING = "ordering"         # Temporal ordering constraint
    ASSERT = "assert"             # Explicit assert statement


@dataclass
class PathConstraint:
    """A single constraint on the execution path."""
    id: str
    constraint_type: ConstraintType
    solidity_expr: str          # Original Solidity expression
    z3_expr: Optional[str]      # Z3 SMT-LIB representation
    source_location: str        # File:line
    is_negatable: bool = True   # Can this constraint be negated in alternative paths?
    variables: List[str] = field(default_factory=list)  # Variables involved

    def __str__(self) -> str:
        return f"{self.constraint_type.value}: {self.solidity_expr}"


@dataclass
class ConstraintSet:
    """Collection of constraints for a path."""
    constraints: List[PathConstraint] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)  # var_name -> z3_type

    def add(self, constraint: PathConstraint) -> None:
        self.constraints.append(constraint)
        for var in constraint.variables:
            if var not in self.variables:
                self.variables[var] = "Int"  # Default type

    def to_smt_lib(self) -> str:
        """Convert to SMT-LIB2 format."""
        lines = []

        # Declare variables
        for var, vtype in self.variables.items():
            lines.append(f"(declare-const {var} {vtype})")

        # Add assertions
        for c in self.constraints:
            if c.z3_expr:
                lines.append(f"(assert {c.z3_expr})")

        # Check satisfiability
        lines.append("(check-sat)")
        lines.append("(get-model)")

        return "\n".join(lines)


@dataclass
class WitnessValues:
    """Satisfying assignment from Z3 (counterexample for defender, exploit params for attacker)."""
    assignments: Dict[str, Any] = field(default_factory=dict)
    attack_parameters: Dict[str, Any] = field(default_factory=dict)

    def get(self, var: str) -> Any:
        return self.assignments.get(var)

    def describe(self) -> str:
        """Human-readable description of the witness."""
        lines = ["Attack parameters:"]
        for var, val in self.attack_parameters.items():
            lines.append(f"  {var} = {val}")
        return "\n".join(lines)


@dataclass
class UnsatCore:
    """Minimal set of conflicting constraints."""
    core_constraints: List[PathConstraint] = field(default_factory=list)
    conflict_reason: str = ""

    def describe(self) -> str:
        """Human-readable description of why path is blocked."""
        lines = ["Path blocked by:"]
        for c in self.core_constraints:
            lines.append(f"  - {c.solidity_expr}")
        lines.append(f"\nReason: {self.conflict_reason}")
        return "\n".join(lines)


@dataclass
class VerificationResult:
    """Complete result of formal verification.

    Evidence Contract (Phase 5.9):
        - All evidence fields must pass /vrs-evidence-audit validation
        - witness.assignments must have deterministic IDs
        - unsat_core.core_constraints must reference valid constraint IDs
        - to_dict() output should comply with Graph Interface Contract v2
    """
    # Core result
    status: VerificationStatus
    is_proven: bool  # True = Z3 gave definitive answer (SAT/UNSAT)

    # Path feasibility
    path_feasible: bool  # True if attack path works

    # Evidence
    witness: Optional[WitnessValues] = None  # If SAT
    unsat_core: Optional[UnsatCore] = None   # If UNSAT

    # Debugging
    z3_script: str = ""
    z3_output: str = ""
    reasoning: str = ""
    constraints_checked: int = 0

    # Timing
    synthesis_time_ms: int = 0
    solving_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "is_proven": self.is_proven,
            "path_feasible": self.path_feasible,
            "witness": self.witness.assignments if self.witness else None,
            "reasoning": self.reasoning,
            "solving_time_ms": self.solving_time_ms,
        }


class LLMDFAVerifier:
    """
    LLMDFA-style verifier using LLM + Z3.

    Key insight from NeurIPS 2024 paper:
    - LLM synthesizes constraints (good at understanding code)
    - Z3 verifies constraints (guaranteed correct reasoning)

    This grounds LLM claims in formal proof, preventing hallucination.

    Phase 5.9 Skills Integration:
        For complete verification, combine with:
        - /vrs-ordering-proof: Validates ORDERING constraints via dominance analysis
        - /vrs-evidence-audit: Validates evidence packets before verdict synthesis
        - /vrs-taint-extend: Provides taint source/sink for constraint extraction

        Verification Policy:
        - All attack evidence must pass evidence-audit before formal verification
        - Ordering claims must be confirmed by ordering-proof skill
        - Defense claims require contract validation via graph-contract-validate
    """

    # Configuration
    DEFAULT_TIMEOUT_SECONDS = 30
    MAX_SYNTHESIS_RETRIES = 3
    USE_BITVECTORS = False  # Use Int for simplicity, BitVec for precision

    # Common patterns for constraint extraction
    REQUIRE_PATTERN = re.compile(r'require\s*\(([^;]+?)\s*(?:,\s*"[^"]*")?\s*\)', re.DOTALL)
    IF_PATTERN = re.compile(r'if\s*\(([^)]+)\)')
    ASSERT_PATTERN = re.compile(r'assert\s*\(([^)]+)\)')

    # Solidity operators to Z3 operators
    OPERATOR_MAP = {
        ">=": ">=",
        "<=": "<=",
        ">": ">",
        "<": "<",
        "==": "=",
        "!=": "distinct",
        "&&": "and",
        "||": "or",
        "!": "not",
        "+": "+",
        "-": "-",
        "*": "*",
        "/": "div",
        "%": "mod",
    }

    def __init__(self, llm_client: Optional[Any] = None, timeout_seconds: int = None):
        """
        Initialize verifier.

        Args:
            llm_client: Optional LLM client for constraint synthesis
            timeout_seconds: Z3 timeout in seconds
        """
        self.llm = llm_client
        self.timeout = timeout_seconds or self.DEFAULT_TIMEOUT_SECONDS
        self._z3_available = self._check_z3_available()

    def _check_z3_available(self) -> bool:
        """Check if Z3 is available."""
        if not Z3_AVAILABLE:
            return False
        try:
            z3.Solver()
            return True
        except Exception:
            return False

    @property
    def z3_available(self) -> bool:
        """Public accessor for Z3 availability."""
        return self._z3_available

    def verify_attack_path(
        self,
        attack: Any,
        function_code: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> VerificationResult:
        """
        Verify if an attack path is feasible.

        Args:
            attack: The attack construction from AttackerAgent
            function_code: Source code of the function
            context: Additional context (state variables, etc.)

        Returns:
            VerificationResult with formal proof or UNKNOWN
        """
        import time

        if not self._z3_available:
            return VerificationResult(
                status=VerificationStatus.UNKNOWN,
                is_proven=False,
                path_feasible=False,
                reasoning="Z3 solver not available, cannot verify formally",
            )

        # Step 1: Extract constraints from attack + code
        start_synthesis = time.time()
        constraints = self._extract_constraints(attack, function_code, context)

        # Step 2: Synthesize Z3 script
        z3_script, synthesis_ok = self._synthesize_z3_with_retry(constraints, attack)
        synthesis_time = int((time.time() - start_synthesis) * 1000)

        if not synthesis_ok:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                is_proven=False,
                path_feasible=False,
                z3_script=z3_script,
                reasoning="Failed to synthesize valid Z3 script after retries",
                synthesis_time_ms=synthesis_time,
            )

        # Step 3: Execute Z3
        start_solve = time.time()
        z3_result = self._execute_z3(z3_script)
        solve_time = int((time.time() - start_solve) * 1000)

        # Step 4: Interpret result
        result = self._interpret_result(z3_result, z3_script, constraints)
        result.synthesis_time_ms = synthesis_time
        result.solving_time_ms = solve_time
        result.constraints_checked = len(constraints.constraints)

        return result

    def verify_defense_claim(
        self,
        defense: Any,
        attack: Any,
        function_code: str,
    ) -> VerificationResult:
        """
        Verify if a defense claim blocks an attack.

        The defense claims certain guards prevent the attack.
        We check if adding guard constraints makes the attack path UNSAT.
        """
        # Extract base constraints
        constraints = self._extract_constraints(attack, function_code, {})

        # Add defense constraints (guards that should block)
        if hasattr(defense, "guards_identified"):
            for guard in defense.guards_identified:
                guard_name = guard.guard_type if hasattr(guard, "guard_type") else str(guard)
                guard_constraint = self._guard_to_constraint(guard_name, defense)
                if guard_constraint:
                    constraints.add(guard_constraint)

        # Now check if attack is still feasible with guards
        z3_script, ok = self._synthesize_z3_with_retry(constraints, attack)
        if not ok:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                is_proven=False,
                path_feasible=True,  # Assume attack works if we can't verify
                reasoning="Failed to synthesize Z3 script for defense verification",
            )

        z3_result = self._execute_z3(z3_script)
        result = self._interpret_result(z3_result, z3_script, constraints)

        # If UNSAT, defense is valid (guards block attack)
        if result.status == VerificationStatus.UNSAT:
            result.reasoning = f"Defense verified: guards block attack path. {result.reasoning}"

        return result

    def verify_constraints_satisfiable(
        self,
        constraints: List[str],
        variable_types: Optional[Dict[str, str]] = None,
    ) -> VerificationResult:
        """
        Directly verify if a set of constraints is satisfiable.

        Args:
            constraints: List of Solidity-style constraint expressions
            variable_types: Optional mapping of variable names to Z3 types

        Returns:
            VerificationResult with SAT/UNSAT status
        """
        constraint_set = ConstraintSet()

        if variable_types:
            constraint_set.variables = variable_types.copy()

        for i, expr in enumerate(constraints):
            pc = PathConstraint(
                id=f"c_{i}",
                constraint_type=ConstraintType.REQUIRE,
                solidity_expr=expr,
                z3_expr=self._solidity_to_z3(expr),
                source_location="direct",
                variables=self._extract_variables(expr),
            )
            constraint_set.add(pc)

        # Synthesize and execute
        z3_script = self._build_z3_script(constraint_set)
        z3_result = self._execute_z3(z3_script)
        return self._interpret_result(z3_result, z3_script, constraint_set)

    def _extract_constraints(
        self,
        attack: Any,
        code: str,
        context: Optional[Dict[str, Any]],
    ) -> ConstraintSet:
        """Extract path constraints from attack and code."""
        constraints = ConstraintSet()

        # Extract from code using regex patterns
        self._extract_require_constraints(code, constraints)
        self._extract_if_constraints(code, constraints)

        # Extract from attack preconditions
        if hasattr(attack, "preconditions"):
            for i, precond in enumerate(attack.preconditions):
                if hasattr(precond, "condition"):
                    expr = precond.condition
                else:
                    expr = str(precond)

                pc = PathConstraint(
                    id=f"pre_{i}",
                    constraint_type=ConstraintType.IMPLICIT,
                    solidity_expr=expr,
                    z3_expr=self._solidity_to_z3(expr),
                    source_location="precondition",
                    variables=self._extract_variables(expr),
                )
                constraints.add(pc)

        # If we have LLM, use it for better extraction
        if self.llm is not None and hasattr(attack, "attack_steps"):
            try:
                llm_constraints = self._llm_extract_constraints(attack, code)
                for c in llm_constraints.constraints:
                    constraints.add(c)
            except Exception as e:
                logger.debug(f"LLM constraint extraction failed: {e}")

        return constraints

    def _extract_require_constraints(self, code: str, constraints: ConstraintSet) -> None:
        """Extract constraints from require statements."""
        for i, match in enumerate(self.REQUIRE_PATTERN.finditer(code)):
            expr = match.group(1).strip()
            # Clean up the expression
            expr = re.sub(r'\s+', ' ', expr)

            pc = PathConstraint(
                id=f"req_{i}",
                constraint_type=ConstraintType.REQUIRE,
                solidity_expr=expr,
                z3_expr=self._solidity_to_z3(expr),
                source_location="require",
                variables=self._extract_variables(expr),
            )
            constraints.add(pc)

    def _extract_if_constraints(self, code: str, constraints: ConstraintSet) -> None:
        """Extract constraints from if conditions."""
        for i, match in enumerate(self.IF_PATTERN.finditer(code)):
            expr = match.group(1).strip()

            pc = PathConstraint(
                id=f"if_{i}",
                constraint_type=ConstraintType.IF_CONDITION,
                solidity_expr=expr,
                z3_expr=self._solidity_to_z3(expr),
                source_location="if_condition",
                variables=self._extract_variables(expr),
                is_negatable=True,
            )
            constraints.add(pc)

    def _extract_variables(self, expr: str) -> List[str]:
        """Extract variable names from expression."""
        # Simple heuristic: find identifiers
        identifiers = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', expr)
        # Filter out keywords and common functions
        keywords = {
            'require', 'if', 'else', 'true', 'false', 'msg', 'sender',
            'address', 'uint256', 'int256', 'bool', 'bytes', 'string',
            'public', 'private', 'internal', 'external', 'view', 'pure',
            'returns', 'return', 'for', 'while', 'do', 'break', 'continue',
        }
        return list(set(v for v in identifiers if v.lower() not in keywords))

    def _solidity_to_z3(self, expr: str) -> Optional[str]:
        """Convert Solidity expression to Z3 SMT-LIB format."""
        if not expr:
            return None

        try:
            # Simple translation for common patterns
            z3_expr = expr

            # Handle comparison operators
            z3_expr = re.sub(r'(\w+)\s*>=\s*(\w+)', r'(>= \1 \2)', z3_expr)
            z3_expr = re.sub(r'(\w+)\s*<=\s*(\w+)', r'(<= \1 \2)', z3_expr)
            z3_expr = re.sub(r'(\w+)\s*>\s*(\w+)', r'(> \1 \2)', z3_expr)
            z3_expr = re.sub(r'(\w+)\s*<\s*(\w+)', r'(< \1 \2)', z3_expr)
            z3_expr = re.sub(r'(\w+)\s*==\s*(\w+)', r'(= \1 \2)', z3_expr)
            z3_expr = re.sub(r'(\w+)\s*!=\s*(\w+)', r'(distinct \1 \2)', z3_expr)

            # Handle arithmetic
            z3_expr = re.sub(r'(\w+)\s*\+\s*(\w+)', r'(+ \1 \2)', z3_expr)
            z3_expr = re.sub(r'(\w+)\s*-\s*(\w+)', r'(- \1 \2)', z3_expr)
            z3_expr = re.sub(r'(\w+)\s*\*\s*(\w+)', r'(* \1 \2)', z3_expr)

            # Handle boolean operators
            z3_expr = re.sub(r'(\([^)]+\))\s*&&\s*(\([^)]+\))', r'(and \1 \2)', z3_expr)
            z3_expr = re.sub(r'(\([^)]+\))\s*\|\|\s*(\([^)]+\))', r'(or \1 \2)', z3_expr)

            # Handle mapping access like balances[addr]
            z3_expr = re.sub(r'(\w+)\[(\w+)\]', r'(select \1 \2)', z3_expr)

            # If it doesn't look like valid S-expr, wrap it
            if not z3_expr.startswith('('):
                # Handle simple booleans
                if z3_expr.lower() == 'true':
                    return 'true'
                elif z3_expr.lower() == 'false':
                    return 'false'

            return z3_expr

        except Exception as e:
            logger.debug(f"Failed to convert expression: {expr}, error: {e}")
            return None

    def _llm_extract_constraints(self, attack: Any, code: str) -> ConstraintSet:
        """Use LLM to extract constraints."""
        prompt = f"""Extract all constraints that must be satisfied for this attack to succeed.

## Attack Description
{getattr(attack, 'category', 'Unknown')}

## Attack Steps
{self._format_attack_steps(attack)}

## Function Code
```solidity
{code}
```

## Task
List each constraint that must be TRUE for the attack to execute.

For each constraint, provide:
1. The Solidity expression (as written in code)
2. The constraint type (require/if/implicit)
3. Variables involved

Format as JSON array:
```json
[
  {{
    "solidity_expr": "balances[msg.sender] >= amount",
    "type": "require",
    "variables": ["balances", "msg_sender", "amount"],
    "location": "line 5"
  }}
]
```
"""
        response = self.llm.analyze(prompt, response_format="json")
        return self._parse_constraint_response(response)

    def _format_attack_steps(self, attack: Any) -> str:
        """Format attack steps for prompt."""
        if not hasattr(attack, "attack_steps"):
            return "No attack steps available"

        lines = []
        for step in attack.attack_steps:
            if hasattr(step, "action"):
                lines.append(f"- {step.action}")
            elif hasattr(step, "description"):
                lines.append(f"- {step.description}")
            else:
                lines.append(f"- {step}")
        return "\n".join(lines)

    def _parse_constraint_response(self, response: str) -> ConstraintSet:
        """Parse LLM response into ConstraintSet."""
        import json

        constraints = ConstraintSet()

        try:
            # Extract JSON from response
            json_match = re.search(r'\[[\s\S]*\]', response)
            if not json_match:
                return constraints

            data = json.loads(json_match.group())

            for i, item in enumerate(data):
                constraint = PathConstraint(
                    id=f"llm_{i}",
                    constraint_type=ConstraintType(item.get("type", "require")),
                    solidity_expr=item["solidity_expr"],
                    z3_expr=self._solidity_to_z3(item["solidity_expr"]),
                    source_location=item.get("location", "llm_extracted"),
                    variables=item.get("variables", []),
                )
                constraints.add(constraint)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug(f"Failed to parse LLM response: {e}")

        return constraints

    def _synthesize_z3_with_retry(
        self,
        constraints: ConstraintSet,
        attack: Any,
    ) -> Tuple[str, bool]:
        """Synthesize Z3 script with retry on failure."""
        last_script = ""
        last_error = ""

        for attempt in range(self.MAX_SYNTHESIS_RETRIES):
            # First try direct synthesis (no LLM needed for simple cases)
            if attempt == 0:
                script = self._build_z3_script(constraints)
            elif self.llm is not None:
                # Use LLM for retry
                prompt = self._build_synthesis_prompt(constraints, attack, last_error)
                response = self.llm.analyze(prompt)
                script = self._extract_smt_code(response)
            else:
                # No LLM, can't retry differently
                break

            last_script = script

            # Validate syntax
            is_valid, error = self._validate_z3_syntax(script)
            if is_valid:
                return script, True

            last_error = error

        return last_script, False

    def _build_z3_script(self, constraints: ConstraintSet) -> str:
        """Build Z3 script from constraints."""
        lines = []

        # Declare variables
        for var, vtype in constraints.variables.items():
            # Sanitize variable name
            safe_var = re.sub(r'[^a-zA-Z0-9_]', '_', var)
            lines.append(f"(declare-const {safe_var} {vtype})")

        # Add non-negative constraints for uint-like variables
        for var in constraints.variables:
            safe_var = re.sub(r'[^a-zA-Z0-9_]', '_', var)
            lines.append(f"(assert (>= {safe_var} 0))")

        # Add assertions from constraints
        for c in constraints.constraints:
            if c.z3_expr:
                # Sanitize variable names in expression
                z3_expr = c.z3_expr
                for var in c.variables:
                    safe_var = re.sub(r'[^a-zA-Z0-9_]', '_', var)
                    z3_expr = re.sub(rf'\b{re.escape(var)}\b', safe_var, z3_expr)
                lines.append(f"(assert {z3_expr})")

        # Check satisfiability
        lines.append("(check-sat)")
        lines.append("(get-model)")

        return "\n".join(lines)

    def _build_synthesis_prompt(
        self,
        constraints: ConstraintSet,
        attack: Any,
        previous_error: str = "",
    ) -> str:
        """Build prompt for Z3 synthesis."""
        error_section = ""
        if previous_error:
            error_section = f"""
## Previous Attempt Failed
Error: {previous_error}
Please fix the issue and try again.
"""

        constraint_desc = "\n".join(
            f"- {c.solidity_expr}  [{c.constraint_type.value}]"
            for c in constraints.constraints
        )

        var_desc = "\n".join(
            f"- {var}: {vtype}"
            for var, vtype in constraints.variables.items()
        )

        return f"""Generate a Z3 SMT-LIB2 script to check if these constraints are satisfiable.

## Constraints to Check
{constraint_desc}

## Variables and Types
{var_desc}

{error_section}

## Requirements
1. Use SMT-LIB2 syntax
2. Declare all variables with (declare-const name type)
3. Use Int for uint256 (simplified), Bool for bool
4. Add (assert ...) for each constraint
5. End with (check-sat) and (get-model)

Output ONLY valid SMT-LIB2 code, no explanations:
"""

    def _extract_smt_code(self, response: str) -> str:
        """Extract SMT-LIB code from LLM response."""
        # Look for code block
        code_match = re.search(r'```(?:smt2?|lisp)?\n([\s\S]*?)```', response)
        if code_match:
            return code_match.group(1).strip()

        # If no code block, assume entire response is code
        lines = []
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('(') or line.startswith(';'):
                lines.append(line)
        return '\n'.join(lines)

    def _validate_z3_syntax(self, script: str) -> Tuple[bool, str]:
        """Validate Z3 script syntax."""
        if not self._z3_available:
            return False, "Z3 not available"

        try:
            # Write to temp file and parse
            with tempfile.NamedTemporaryFile(mode='w', suffix='.smt2', delete=False) as f:
                f.write(script)
                f.flush()
                temp_path = f.name

            try:
                z3.parse_smt2_file(temp_path)
                return True, ""
            except z3.Z3Exception as e:
                return False, str(e)
            finally:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

        except Exception as e:
            return False, str(e)

    def _execute_z3(self, script: str) -> Dict[str, Any]:
        """Execute Z3 solver on script."""
        if not self._z3_available:
            return {"status": "error", "error": "Z3 not available"}

        try:
            # Use z3 Python API for better integration
            solver = z3.Solver()
            solver.set("timeout", self.timeout * 1000)  # Z3 uses milliseconds

            # Parse and add assertions
            with tempfile.NamedTemporaryFile(mode='w', suffix='.smt2', delete=False) as f:
                f.write(script)
                f.flush()
                temp_path = f.name

            try:
                assertions = z3.parse_smt2_file(temp_path)
                solver.add(assertions)
            except z3.Z3Exception as e:
                return {"status": "error", "error": str(e)}
            finally:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

            # Check satisfiability
            result = solver.check()

            if result == z3.sat:
                model = solver.model()
                model_dict = {}
                for d in model.decls():
                    model_dict[d.name()] = str(model[d])
                return {
                    "status": "sat",
                    "model": model_dict,
                }
            elif result == z3.unsat:
                return {
                    "status": "unsat",
                    "core": [],
                }
            else:
                return {"status": "unknown", "reason": "timeout or complexity"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _interpret_result(
        self,
        z3_result: Dict[str, Any],
        z3_script: str,
        constraints: ConstraintSet,
    ) -> VerificationResult:
        """Interpret Z3 result into VerificationResult."""
        status_map = {
            "sat": VerificationStatus.SAT,
            "unsat": VerificationStatus.UNSAT,
            "unknown": VerificationStatus.UNKNOWN,
            "error": VerificationStatus.ERROR,
        }

        status = status_map.get(z3_result.get("status", "error"), VerificationStatus.ERROR)

        if status == VerificationStatus.SAT:
            # Attack path is feasible
            witness = WitnessValues(
                assignments=z3_result.get("model", {}),
                attack_parameters=self._extract_attack_params(z3_result.get("model", {})),
            )
            return VerificationResult(
                status=status,
                is_proven=True,
                path_feasible=True,
                witness=witness,
                z3_script=z3_script,
                z3_output=str(z3_result),
                reasoning="Z3 found satisfying assignment - attack path is feasible",
            )

        elif status == VerificationStatus.UNSAT:
            # Attack path is blocked
            unsat_core = UnsatCore(
                core_constraints=[],
                conflict_reason="Constraints are mutually unsatisfiable",
            )
            return VerificationResult(
                status=status,
                is_proven=True,
                path_feasible=False,
                unsat_core=unsat_core,
                z3_script=z3_script,
                z3_output=str(z3_result),
                reasoning="Z3 proved UNSAT - attack path is blocked by constraints",
            )

        elif status == VerificationStatus.UNKNOWN:
            return VerificationResult(
                status=status,
                is_proven=False,
                path_feasible=False,  # Conservative: assume blocked until proven
                z3_script=z3_script,
                z3_output=str(z3_result),
                reasoning=f"Z3 returned unknown: {z3_result.get('reason', 'timeout')}",
            )

        else:  # ERROR
            return VerificationResult(
                status=status,
                is_proven=False,
                path_feasible=False,
                z3_script=z3_script,
                z3_output=str(z3_result),
                reasoning=f"Z3 error: {z3_result.get('error', 'unknown error')}",
            )

    def _extract_attack_params(self, model: Dict[str, str]) -> Dict[str, Any]:
        """Extract attack parameters from Z3 model."""
        # Identify which variables are attacker-controlled
        attack_vars = {"amount", "value", "data", "to", "recipient"}
        params = {}
        for var, val in model.items():
            if any(av in var.lower() for av in attack_vars):
                params[var] = val
        return params

    def _guard_to_constraint(
        self,
        guard: str,
        defense: Any,
    ) -> Optional[PathConstraint]:
        """Convert guard name to constraint."""
        guard_lower = guard.lower()

        if "reentrancy" in guard_lower:
            return PathConstraint(
                id="guard_reentrancy",
                constraint_type=ConstraintType.IMPLICIT,
                solidity_expr="reentrancy_locked == false",
                z3_expr="(= reentrancy_locked false)",
                source_location="guard",
                variables=["reentrancy_locked"],
            )
        elif "owner" in guard_lower:
            return PathConstraint(
                id="guard_owner",
                constraint_type=ConstraintType.REQUIRE,
                solidity_expr="msg.sender == owner",
                z3_expr="(= caller owner)",
                source_location="modifier",
                variables=["caller", "owner"],
            )
        elif "cei" in guard_lower:
            return PathConstraint(
                id="guard_cei",
                constraint_type=ConstraintType.ORDERING,
                solidity_expr="state_write_time < external_call_time",
                z3_expr="(< state_write external_call)",
                source_location="pattern",
                variables=["state_write", "external_call"],
            )

        return None

    def batch_verify(
        self,
        attacks: List[Any],
        function_codes: Dict[str, str],
    ) -> List[VerificationResult]:
        """Verify multiple attacks efficiently."""
        results = []
        for attack in attacks:
            target = getattr(attack, "target_function", None) or ""
            if hasattr(attack, "target_nodes") and attack.target_nodes:
                target = attack.target_nodes[0]
            code = function_codes.get(target, "")
            result = self.verify_attack_path(attack, code)
            results.append(result)
        return results


# Convenience function
def verify_path_feasibility(
    constraints: List[str],
    variable_types: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> VerificationResult:
    """
    Quick verification of path constraints.

    Args:
        constraints: List of Solidity-style constraint expressions
        variable_types: Optional variable type mapping
        timeout: Z3 timeout in seconds

    Returns:
        VerificationResult with SAT/UNSAT status
    """
    verifier = LLMDFAVerifier(timeout_seconds=timeout)
    return verifier.verify_constraints_satisfiable(constraints, variable_types)
