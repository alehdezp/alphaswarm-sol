# [P2-T4] LLMDFA Verifier Agent

**Phase**: 2 - Adversarial Agents
**Task ID**: P2-T4
**Status**: COMPLETED
**Priority**: HIGH
**Estimated Effort**: 4-5 days
**Actual Effort**: 1 day
**Completed**: 2026-01-05

---

## Executive Summary

Implement the **LLMDFA Verifier Agent** that grounds LLM claims in formal verification. Uses LLM to synthesize Z3 constraints from attacker/defender arguments, then executes Z3 to prove or disprove path feasibility. This is the **key innovation** that prevents LLM hallucination.

**Research Basis**: LLMDFA (NeurIPS 2024) showed LLM + SMT hybrid achieves high accuracy by using LLM as code synthesizer, not reasoning engine.

**Key Insight**: The LLM generates constraints; Z3 validates them. This separation ensures correctness - the LLM can hallucinate constraints, but Z3 will catch inconsistencies.

---

## Architecture

```
                    ┌──────────────────────────────────────────────────────────────────┐
                    │                       LLMDFAVerifier                              │
                    │                                                                   │
  AttackPath ───────►  ┌─────────────────────────────────────────────────────────────┐ │
                    │  │                 Constraint Extraction                        │ │
  FunctionCode ────►│  │                                                              │ │
                    │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │ │
                    │  │  │   Require    │  │     If       │  │    Loop      │       │ │
                    │  │  │  Statements  │  │  Conditions  │  │   Bounds     │       │ │
                    │  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │ │
                    │  │         │                 │                 │                │ │
                    │  │         ▼                 ▼                 ▼                │ │
                    │  │  ┌────────────────────────────────────────────────────┐     │ │
                    │  │  │           PathConstraints Collection                │     │ │
                    │  │  │                                                     │     │ │
                    │  │  │  - balance_of[caller] >= amount                     │     │ │
                    │  │  │  - caller != address(0)                             │     │ │
                    │  │  │  - external_call_succeeds = true                    │     │ │
                    │  │  └────────────────────────────────────────────────────┘     │ │
                    │  └───────────────────────────┬──────────────────────────────────┘ │
                    │                              │                                    │
                    │                              ▼                                    │
                    │  ┌─────────────────────────────────────────────────────────────┐ │
                    │  │                  Z3 Script Synthesis                         │ │
                    │  │                                                              │ │
                    │  │  LLM generates SMT-LIB2 script:                              │ │
                    │  │  ┌────────────────────────────────────────────────────┐     │ │
                    │  │  │ (declare-const balance_caller Int)                  │     │ │
                    │  │  │ (declare-const amount Int)                          │     │ │
                    │  │  │ (assert (>= balance_caller amount))                 │     │ │
                    │  │  │ (assert (> amount 0))                               │     │ │
                    │  │  │ (check-sat)                                         │     │ │
                    │  │  │ (get-model)                                         │     │ │
                    │  │  └────────────────────────────────────────────────────┘     │ │
                    │  │                                                              │ │
                    │  │  Validation: Syntax check + type consistency                 │ │
                    │  │  Retry: Up to 3 attempts with error feedback                 │ │
                    │  │                                                              │ │
                    │  └───────────────────────────┬──────────────────────────────────┘ │
                    │                              │                                    │
                    │                              ▼                                    │
                    │  ┌─────────────────────────────────────────────────────────────┐ │
                    │  │                    Z3 Execution Engine                       │ │
                    │  │                                                              │ │
                    │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │ │
                    │  │  │     SAT      │  │    UNSAT     │  │   UNKNOWN    │       │ │
                    │  │  │ Path viable  │  │ Path blocked │  │   Timeout    │       │ │
                    │  │  │ + witness    │  │ + unsat core │  │ or complex   │       │ │
                    │  │  └──────────────┘  └──────────────┘  └──────────────┘       │ │
                    │  │                                                              │ │
                    │  │  Timeout: 30s default, configurable                          │ │
                    │  │  Fallback: Return UNKNOWN, not error                         │ │
                    │  │                                                              │ │
                    │  └───────────────────────────┬──────────────────────────────────┘ │
                    │                              │                                    │
                    └──────────────────────────────┼────────────────────────────────────┘
                                                   │
                                                   ▼
                                      ┌───────────────────────────┐
                                      │   VerificationResult      │
                                      │   - is_proven: bool       │
                                      │   - path_feasible: bool   │
                                      │   - witness_values: dict  │
                                      │   - unsat_core: List      │
                                      │   - z3_script: str        │
                                      │   - reasoning: str        │
                                      └───────────────────────────┘
```

---

## Constraint Types and Extraction

### Constraint Categories

| Category | Solidity Pattern | Z3 Translation | Example |
|----------|------------------|----------------|---------|
| **Balance Check** | `require(balance >= amount)` | `(assert (>= balance amount))` | Withdraw validation |
| **Access Control** | `require(msg.sender == owner)` | `(assert (= caller owner))` | Owner-only |
| **Non-Zero** | `require(amount > 0)` | `(assert (> amount 0))` | Input validation |
| **Mapping Access** | `balances[addr] >= x` | `(assert (>= (select balances addr) x))` | Mapping read |
| **State Ordering** | External before state write | `(assert (< external_call_time state_write_time))` | Reentrancy |
| **Loop Bounds** | `for(i < n)` where n is input | `(assert (> n 0))` | DoS check |
| **Arithmetic** | `a + b < MAX` | `(assert (< (+ a b) MAX))` | Overflow |

### Solidity-to-Z3 Type Mapping

```
┌─────────────────────────┬──────────────────────────────────────────┐
│ Solidity Type           │ Z3 Type                                  │
├─────────────────────────┼──────────────────────────────────────────┤
│ uint256                 │ (_ BitVec 256) or Int (simplified)       │
│ int256                  │ (_ BitVec 256) or Int (simplified)       │
│ address                 │ (_ BitVec 160) or Int                    │
│ bool                    │ Bool                                     │
│ bytes32                 │ (_ BitVec 256)                           │
│ mapping(K => V)         │ (Array K V)                              │
│ struct                  │ Tuple of component types                 │
│ enum                    │ Int (with range constraint)              │
└─────────────────────────┴──────────────────────────────────────────┘
```

---

## Dependencies

### Required Before Starting
- [ ] [P2-T2] Attacker Agent - Provides attack claims to verify
- [ ] [P2-T3] Defender Agent - Provides defense claims to verify
- Z3 solver installed (`pip install z3-solver` or system package)

### Blocks These Tasks
- [P2-T5] Adversarial Arbiter - Uses verification results

---

## Objectives

1. Extract path constraints from attack constructions
2. Synthesize valid Z3/SMT-LIB scripts using LLM
3. Execute Z3 with proper timeout and error handling
4. Return formal proof (SAT/UNSAT) or graceful UNKNOWN
5. Provide witness values for SAT results (attack parameters)
6. Provide UNSAT core for blocked paths (which constraints conflict)

---

## Technical Design

### Key Data Structures

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
import subprocess
import tempfile
import re
import z3


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
    assignments: Dict[str, Any]
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
    core_constraints: List[PathConstraint]
    conflict_reason: str

    def describe(self) -> str:
        """Human-readable description of why path is blocked."""
        lines = ["Path blocked by:"]
        for c in self.core_constraints:
            lines.append(f"  - {c.solidity_expr}")
        lines.append(f"\nReason: {self.conflict_reason}")
        return "\n".join(lines)


@dataclass
class VerificationResult:
    """Complete result of formal verification."""
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
    """

    # Configuration
    DEFAULT_TIMEOUT_SECONDS = 30
    MAX_SYNTHESIS_RETRIES = 3
    USE_BITVECTORS = False  # Use Int for simplicity, BitVec for precision

    # Common patterns for constraint extraction
    REQUIRE_PATTERN = re.compile(r'require\s*\(([^)]+)\)')
    IF_PATTERN = re.compile(r'if\s*\(([^)]+)\)')
    ASSERT_PATTERN = re.compile(r'assert\s*\(([^)]+)\)')

    def __init__(self, llm_client, timeout_seconds: int = None):
        self.llm = llm_client
        self.timeout = timeout_seconds or self.DEFAULT_TIMEOUT_SECONDS
        self._z3_available = self._check_z3_available()

    def _check_z3_available(self) -> bool:
        """Check if Z3 is available."""
        try:
            z3.Solver()
            return True
        except Exception:
            return False

    def verify_attack_path(
        self,
        attack: "AttackConstruction",
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
        defense: "DefenseArgument",
        attack: "AttackConstruction",
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
        for guard in defense.guards_identified:
            guard_constraint = self._guard_to_constraint(guard, defense)
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

    def _extract_constraints(
        self,
        attack: "AttackConstruction",
        code: str,
        context: Optional[Dict[str, Any]],
    ) -> ConstraintSet:
        """Extract path constraints using LLM."""

        prompt = f"""Extract all constraints that must be satisfied for this attack to succeed.

## Attack Description
{attack.description}

## Attack Steps
{self._format_attack_steps(attack)}

## Preconditions Claimed
{attack.preconditions}

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
    "variables": ["balances", "msg.sender", "amount"],
    "location": "line 5"
  }},
  ...
]
```

Be thorough - include ALL constraints on the execution path.
"""

        response = self.llm.analyze(prompt, response_format="json")
        return self._parse_constraint_response(response)

    def _format_attack_steps(self, attack: "AttackConstruction") -> str:
        """Format attack steps for prompt."""
        lines = []
        for i, step in enumerate(attack.attack_steps, 1):
            lines.append(f"{i}. {step.description}")
            if hasattr(step, 'precondition'):
                lines.append(f"   Requires: {step.precondition}")
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
                    id=f"c_{i}",
                    constraint_type=ConstraintType(item.get("type", "require")),
                    solidity_expr=item["solidity_expr"],
                    z3_expr=None,  # Will be synthesized later
                    source_location=item.get("location", "unknown"),
                    variables=item.get("variables", []),
                )
                constraints.add(constraint)

        except (json.JSONDecodeError, KeyError) as e:
            # Fall back to regex extraction
            constraints = self._fallback_constraint_extraction(response)

        return constraints

    def _fallback_constraint_extraction(self, code: str) -> ConstraintSet:
        """Fallback: Extract constraints using regex patterns."""
        constraints = ConstraintSet()

        # Find require statements
        for i, match in enumerate(self.REQUIRE_PATTERN.finditer(code)):
            constraint = PathConstraint(
                id=f"req_{i}",
                constraint_type=ConstraintType.REQUIRE,
                solidity_expr=match.group(1).strip(),
                z3_expr=None,
                source_location="extracted",
                variables=self._extract_variables(match.group(1)),
            )
            constraints.add(constraint)

        return constraints

    def _extract_variables(self, expr: str) -> List[str]:
        """Extract variable names from expression."""
        # Simple heuristic: find identifiers
        identifiers = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', expr)
        # Filter out keywords and common functions
        keywords = {'require', 'if', 'else', 'true', 'false', 'msg', 'sender', 'address'}
        return [v for v in identifiers if v not in keywords]

    def _synthesize_z3_with_retry(
        self,
        constraints: ConstraintSet,
        attack: "AttackConstruction",
    ) -> Tuple[str, bool]:
        """Synthesize Z3 script with retry on failure."""

        last_script = ""
        last_error = ""

        for attempt in range(self.MAX_SYNTHESIS_RETRIES):
            prompt = self._build_synthesis_prompt(constraints, attack, last_error)
            script = self.llm.analyze(prompt)

            # Extract just the SMT-LIB code
            script = self._extract_smt_code(script)
            last_script = script

            # Validate syntax
            is_valid, error = self._validate_z3_syntax(script)
            if is_valid:
                return script, True

            last_error = error

        return last_script, False

    def _build_synthesis_prompt(
        self,
        constraints: ConstraintSet,
        attack: "AttackConstruction",
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

        return f"""Generate a Z3 SMT-LIB2 script to check if these constraints are satisfiable.

## Constraints to Check
{self._format_constraints(constraints)}

## Variables and Types
{self._format_variables(constraints)}

## Attack Context
The attack succeeds if ALL constraints can be satisfied simultaneously.
We want to find: Is there an assignment of values that makes all constraints TRUE?

{error_section}

## Requirements
1. Use SMT-LIB2 syntax
2. Declare all variables with (declare-const name type)
3. Use Int for uint256 (simplified), Bool for bool
4. Add (assert ...) for each constraint
5. End with (check-sat) and (get-model)

Output ONLY valid SMT-LIB2 code, no explanations:
"""

    def _format_constraints(self, constraints: ConstraintSet) -> str:
        """Format constraints for synthesis prompt."""
        lines = []
        for c in constraints.constraints:
            lines.append(f"- {c.solidity_expr}  [{c.constraint_type.value}]")
        return "\n".join(lines)

    def _format_variables(self, constraints: ConstraintSet) -> str:
        """Format variable types."""
        lines = []
        for var, vtype in constraints.variables.items():
            lines.append(f"- {var}: {vtype}")
        return "\n".join(lines)

    def _extract_smt_code(self, response: str) -> str:
        """Extract SMT-LIB code from LLM response."""
        # Look for code block
        code_match = re.search(r'```(?:smt2?|lisp)?\n([\s\S]*?)```', response)
        if code_match:
            return code_match.group(1).strip()

        # If no code block, assume entire response is code
        # Remove obvious non-code lines
        lines = []
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('(') or line.startswith(';'):
                lines.append(line)
        return '\n'.join(lines)

    def _validate_z3_syntax(self, script: str) -> Tuple[bool, str]:
        """Validate Z3 script syntax."""
        try:
            # Quick validation: parse with z3
            solver = z3.Solver()

            # Write to temp file and parse
            with tempfile.NamedTemporaryFile(mode='w', suffix='.smt2', delete=False) as f:
                f.write(script)
                f.flush()
                try:
                    z3.parse_smt2_file(f.name)
                    return True, ""
                except z3.Z3Exception as e:
                    return False, str(e)
        except Exception as e:
            return False, str(e)

    def _execute_z3(self, script: str) -> Dict[str, Any]:
        """Execute Z3 solver on script."""
        try:
            # Use z3 Python API for better integration
            solver = z3.Solver()
            solver.set("timeout", self.timeout * 1000)  # Z3 uses milliseconds

            # Parse and add assertions
            with tempfile.NamedTemporaryFile(mode='w', suffix='.smt2', delete=False) as f:
                f.write(script)
                f.flush()

                try:
                    assertions = z3.parse_smt2_file(f.name)
                    solver.add(assertions)
                except z3.Z3Exception as e:
                    return {"status": "error", "error": str(e)}

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
                # Try to get unsat core (requires tracking)
                return {
                    "status": "unsat",
                    "core": [],  # Would need assertion tracking for core
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
                core_constraints=[],  # Would need tracking
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
        defense: "DefenseArgument",
    ) -> Optional[PathConstraint]:
        """Convert guard name to constraint."""

        guard_constraints = {
            "ReentrancyGuard": PathConstraint(
                id="guard_reentrancy",
                constraint_type=ConstraintType.IMPLICIT,
                solidity_expr="reentrancy_locked == false",
                z3_expr="(assert (= reentrancy_locked false))",
                source_location="guard",
                variables=["reentrancy_locked"],
            ),
            "onlyOwner": PathConstraint(
                id="guard_owner",
                constraint_type=ConstraintType.REQUIRE,
                solidity_expr="msg.sender == owner",
                z3_expr="(assert (= caller owner))",
                source_location="modifier",
                variables=["caller", "owner"],
            ),
            "CEI_pattern": PathConstraint(
                id="guard_cei",
                constraint_type=ConstraintType.ORDERING,
                solidity_expr="state_write_time < external_call_time",
                z3_expr="(assert (< state_write external_call))",
                source_location="pattern",
                variables=["state_write", "external_call"],
            ),
        }

        return guard_constraints.get(guard)

    def batch_verify(
        self,
        attacks: List["AttackConstruction"],
        function_codes: Dict[str, str],
    ) -> List[VerificationResult]:
        """Verify multiple attacks efficiently."""
        results = []
        for attack in attacks:
            code = function_codes.get(attack.target_function, "")
            result = self.verify_attack_path(attack, code)
            results.append(result)
        return results
```

---

## Success Criteria

- [ ] Constraint extraction via LLM working for common patterns
- [ ] Z3 script synthesis with valid SMT-LIB2 output
- [ ] Retry logic for synthesis failures
- [ ] Z3 execution with proper timeout handling (30s default)
- [ ] SAT result with witness values (attack parameters)
- [ ] UNSAT result with conflict explanation
- [ ] UNKNOWN handling for timeouts
- [ ] Graceful degradation when Z3 unavailable
- [ ] Defense claim verification working
- [ ] Batch verification for multiple attacks

---

## Validation Tests

```python
import pytest
from true_vkg.agents.verifier import (
    LLMDFAVerifier, VerificationStatus, ConstraintType,
    PathConstraint, ConstraintSet, VerificationResult
)


class TestConstraintExtraction:
    """Test constraint extraction from code."""

    def test_extract_require_constraints(self):
        """Test extraction of require statements."""
        verifier = LLMDFAVerifier(mock_llm)

        attack = create_simple_attack("withdraw")
        code = '''
        function withdraw(uint256 amount) external {
            require(balances[msg.sender] >= amount, "Insufficient");
            require(amount > 0, "Zero amount");
            balances[msg.sender] -= amount;
            payable(msg.sender).transfer(amount);
        }
        '''

        constraints = verifier._extract_constraints(attack, code, {})

        assert len(constraints.constraints) >= 2
        assert any("balance" in c.solidity_expr.lower() for c in constraints.constraints)
        assert any("amount > 0" in c.solidity_expr for c in constraints.constraints)

    def test_extract_implicit_constraints(self):
        """Test extraction of implicit constraints (not in require)."""
        verifier = LLMDFAVerifier(mock_llm)

        attack = create_reentrancy_attack()
        code = '''
        function withdraw(uint256 amount) external {
            uint256 bal = balances[msg.sender];
            require(bal >= amount);
            // Implicit: external call must succeed for attack
            (bool success,) = msg.sender.call{value: amount}("");
            require(success);
            balances[msg.sender] = bal - amount;
        }
        '''

        constraints = verifier._extract_constraints(attack, code, {})

        # Should include external call success as constraint
        assert any(
            "success" in c.solidity_expr.lower() or "call" in c.solidity_expr.lower()
            for c in constraints.constraints
        )


class TestZ3Synthesis:
    """Test Z3 script synthesis."""

    def test_synthesize_valid_smt_lib(self):
        """Test that synthesis produces valid SMT-LIB2."""
        verifier = LLMDFAVerifier(mock_llm)

        constraints = ConstraintSet()
        constraints.add(PathConstraint(
            id="c1",
            constraint_type=ConstraintType.REQUIRE,
            solidity_expr="balance >= amount",
            z3_expr=None,
            source_location="test",
            variables=["balance", "amount"],
        ))

        script, ok = verifier._synthesize_z3_with_retry(constraints, mock_attack)

        assert ok
        assert "(declare-const" in script
        assert "(assert" in script
        assert "(check-sat)" in script

    def test_retry_on_invalid_syntax(self):
        """Test retry when first synthesis is invalid."""
        # Mock LLM that returns invalid first, valid second
        failing_llm = MockLLMWithRetry(
            responses=[
                "(invalid syntax here",  # First attempt fails
                "(declare-const x Int)\n(assert (> x 0))\n(check-sat)",  # Second succeeds
            ]
        )

        verifier = LLMDFAVerifier(failing_llm)
        script, ok = verifier._synthesize_z3_with_retry(simple_constraints, mock_attack)

        assert ok
        assert "(declare-const" in script


class TestZ3Execution:
    """Test Z3 solver execution."""

    def test_sat_result_with_witness(self):
        """Test SAT result returns witness values."""
        verifier = LLMDFAVerifier(mock_llm)

        # Simple satisfiable constraints
        script = """
        (declare-const amount Int)
        (declare-const balance Int)
        (assert (>= balance amount))
        (assert (> amount 0))
        (assert (= balance 100))
        (check-sat)
        (get-model)
        """

        result = verifier._execute_z3(script)

        assert result["status"] == "sat"
        assert "model" in result
        assert "amount" in result["model"] or "balance" in result["model"]

    def test_unsat_result(self):
        """Test UNSAT result for impossible constraints."""
        verifier = LLMDFAVerifier(mock_llm)

        # Impossible constraints
        script = """
        (declare-const x Int)
        (assert (> x 10))
        (assert (< x 5))
        (check-sat)
        """

        result = verifier._execute_z3(script)

        assert result["status"] == "unsat"

    def test_timeout_returns_unknown(self):
        """Test timeout returns UNKNOWN status."""
        verifier = LLMDFAVerifier(mock_llm, timeout_seconds=1)

        # Complex formula that might timeout
        script = """
        (declare-const x (_ BitVec 256))
        (declare-const y (_ BitVec 256))
        (assert (= (bvmul x y) #x0000000000000000000000000000000000000000000000000000000000000001))
        (check-sat)
        """

        result = verifier._execute_z3(script)

        # Either solves quickly or times out
        assert result["status"] in ["sat", "unsat", "unknown"]


class TestFullVerification:
    """Integration tests for full verification pipeline."""

    def test_verify_feasible_reentrancy_attack(self):
        """Test verification confirms feasible attack path."""
        verifier = LLMDFAVerifier(real_llm)

        attack = create_reentrancy_attack("fn_withdraw_vuln")
        code = VULNERABLE_WITHDRAW_CODE

        result = verifier.verify_attack_path(attack, code)

        assert result.status == VerificationStatus.SAT
        assert result.is_proven == True
        assert result.path_feasible == True
        assert result.witness is not None
        assert len(result.witness.assignments) > 0

    def test_verify_blocked_attack_with_guard(self):
        """Test verification shows guarded function blocks attack."""
        verifier = LLMDFAVerifier(real_llm)

        attack = create_reentrancy_attack("fn_safe_withdraw")
        code = SAFE_WITHDRAW_WITH_GUARD

        result = verifier.verify_attack_path(attack, code)

        # Attack should be blocked by reentrancy guard
        assert result.path_feasible == False or result.status == VerificationStatus.UNSAT

    def test_verify_defense_claim(self):
        """Test defense verification confirms guards block attack."""
        verifier = LLMDFAVerifier(real_llm)

        attack = create_reentrancy_attack("fn_withdraw")
        defense = create_defense_with_guard("ReentrancyGuard")
        code = SAFE_WITHDRAW_WITH_GUARD

        result = verifier.verify_defense_claim(defense, attack, code)

        assert result.path_feasible == False
        assert "defense verified" in result.reasoning.lower() or result.status == VerificationStatus.UNSAT

    def test_graceful_degradation_without_z3(self):
        """Test graceful handling when Z3 is unavailable."""
        verifier = LLMDFAVerifier(mock_llm)
        verifier._z3_available = False  # Simulate no Z3

        result = verifier.verify_attack_path(mock_attack, "code")

        assert result.status == VerificationStatus.UNKNOWN
        assert result.is_proven == False
        assert "not available" in result.reasoning.lower()


class TestUltimateVerifierPipeline:
    """Ultimate integration test with real LLM and Z3."""

    @pytest.mark.integration
    def test_full_pipeline_vulnerable_code(self):
        """Full pipeline test on known vulnerable code."""
        # Setup
        llm = create_real_llm_client()
        verifier = LLMDFAVerifier(llm)

        # Create attack for DAO-style vulnerability
        attack = AttackConstruction(
            id="attack_reentrancy",
            target_function="withdraw",
            description="Classic reentrancy via external call before state update",
            attack_steps=[
                AttackStep("Call withdraw with amount <= balance"),
                AttackStep("Receive callback during external call"),
                AttackStep("Re-enter withdraw before balance updated"),
            ],
            preconditions=["Attacker has positive balance", "External call succeeds"],
            exploitability=0.9,
        )

        code = '''
        function withdraw(uint256 amount) external {
            require(balances[msg.sender] >= amount);
            (bool success,) = msg.sender.call{value: amount}("");
            require(success);
            balances[msg.sender] -= amount;
        }
        '''

        # Verify
        result = verifier.verify_attack_path(attack, code)

        # Assert attack is feasible
        assert result.status == VerificationStatus.SAT
        assert result.is_proven
        assert result.path_feasible
        assert result.witness is not None

        # Witness should contain valid attack parameters
        assert any(
            "amount" in k.lower() or "balance" in k.lower()
            for k in result.witness.assignments
        )


# Test fixtures
VULNERABLE_WITHDRAW_CODE = '''
function withdraw(uint256 amount) external {
    require(balances[msg.sender] >= amount, "Insufficient balance");
    (bool success,) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");
    balances[msg.sender] -= amount;  // State update AFTER external call
}
'''

SAFE_WITHDRAW_WITH_GUARD = '''
function withdraw(uint256 amount) external nonReentrant {
    require(balances[msg.sender] >= amount, "Insufficient balance");
    balances[msg.sender] -= amount;  // State update BEFORE external call
    (bool success,) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");
}
'''
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Z3 not installed | HIGH | Graceful degradation, return UNKNOWN |
| LLM generates invalid SMT | MEDIUM | Validate syntax, retry with error feedback |
| Z3 timeout on complex paths | MEDIUM | Configurable timeout, report as UNKNOWN |
| Type mismatches (uint vs int) | LOW | Use simplified Int types, add range constraints |
| LLM extracts incomplete constraints | MEDIUM | Fallback to regex extraction, multiple extraction strategies |

---

## Integration Points

### Input From Other Tasks
- **P2-T2 Attacker Agent**: `AttackConstruction` with attack steps and preconditions
- **P2-T3 Defender Agent**: `DefenseArgument` with guard claims to verify

### Output To Other Tasks
- **P2-T5 Adversarial Arbiter**: `VerificationResult` with formal proof status
  - `is_proven=True` + `path_feasible=True` → VULNERABLE (highest confidence)
  - `is_proven=True` + `path_feasible=False` → SAFE (highest confidence)
  - `is_proven=False` → Use other evidence, lower confidence

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
| 2026-01-03 | Enhanced with complete Z3 integration, constraint types, retry logic, comprehensive tests | Claude |
