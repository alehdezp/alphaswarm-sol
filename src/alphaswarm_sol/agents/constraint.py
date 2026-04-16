"""Phase 9: Constraint Agent (Z3).

The Constraint Agent uses Z3 SMT solver to verify constraints and check
for vulnerability conditions that can be satisfied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from enum import Enum

try:
    from z3 import (
        Solver,
        Int,
        Bool,
        And,
        Or,
        Not,
        Implies,
        sat,
        unsat,
        unknown,
    )
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False

from alphaswarm_sol.agents.base import (
    VerificationAgent,
    AgentResult,
    AgentEvidence,
    EvidenceType,
)

if TYPE_CHECKING:
    from alphaswarm_sol.kg.subgraph import SubGraph, SubGraphNode


class ConstraintType(str, Enum):
    """Types of constraints extracted from code."""
    ACCESS_CONTROL = "access_control"
    BALANCE_CHECK = "balance_check"
    REENTRANCY_GUARD = "reentrancy_guard"
    OVERFLOW_CHECK = "overflow_check"
    STATE_INVARIANT = "state_invariant"
    VALUE_CONSTRAINT = "value_constraint"


class VulnerabilityConditionType(str, Enum):
    """Types of vulnerability conditions to check."""
    REENTRANCY_POSSIBLE = "reentrancy_possible"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    BALANCE_MANIPULATION = "balance_manipulation"
    OVERFLOW_EXPLOITABLE = "overflow_exploitable"
    INVARIANT_VIOLATION = "invariant_violation"


@dataclass
class Constraint:
    """A constraint extracted from code.

    Represents a condition that must hold (e.g., access check, balance check).
    """
    id: str
    type: ConstraintType
    description: str
    source_node: str
    # Z3 representation will be built dynamically
    variables: Dict[str, str] = field(default_factory=dict)  # var_name -> type
    expression: str = ""  # Simplified expression string

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "source_node": self.source_node,
            "variables": self.variables,
            "expression": self.expression,
        }


@dataclass
class VulnerabilityCondition:
    """A vulnerability condition to check with Z3.

    Represents a condition that, if satisfiable, indicates a vulnerability.
    """
    id: str
    type: VulnerabilityConditionType
    description: str
    severity: str = "medium"
    # Conditions that make vulnerability exploitable
    preconditions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "severity": self.severity,
            "preconditions": self.preconditions,
        }


@dataclass
class ConstraintViolation:
    """A detected constraint violation."""
    condition: VulnerabilityCondition
    satisfied: bool
    model: Optional[Dict[str, Any]] = None
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition": self.condition.to_dict(),
            "satisfied": self.satisfied,
            "model": self.model,
            "confidence": self.confidence,
        }


# Predefined vulnerability conditions
VULNERABILITY_CONDITIONS = [
    VulnerabilityCondition(
        id="reentrancy-exploitable",
        type=VulnerabilityConditionType.REENTRANCY_POSSIBLE,
        description="Reentrancy is possible: external call before state update",
        severity="critical",
        preconditions=["external_call", "not_reentrancy_guard", "state_write_after"],
    ),
    VulnerabilityCondition(
        id="unauthorized-privilege",
        type=VulnerabilityConditionType.UNAUTHORIZED_ACCESS,
        description="Privileged operation without access control",
        severity="high",
        preconditions=["writes_privileged", "not_access_gate"],
    ),
    VulnerabilityCondition(
        id="balance-drain",
        type=VulnerabilityConditionType.BALANCE_MANIPULATION,
        description="User can drain balance beyond their allowance",
        severity="critical",
        preconditions=["transfers_value", "not_balance_check"],
    ),
]


class ConstraintAgent(VerificationAgent):
    """Constraint Agent for Z3-based vulnerability verification.

    This agent extracts constraints from the subgraph and uses Z3 to
    check if vulnerability conditions can be satisfied.

    Note: Requires z3-solver package. If not available, falls back to
    heuristic-based analysis.
    """

    def __init__(
        self,
        vulnerability_conditions: Optional[List[VulnerabilityCondition]] = None,
    ):
        """Initialize the Constraint Agent.

        Args:
            vulnerability_conditions: Custom conditions to check. Uses defaults if None.
        """
        self.vulnerability_conditions = (
            vulnerability_conditions
            if vulnerability_conditions is not None
            else VULNERABILITY_CONDITIONS
        )

    @property
    def agent_name(self) -> str:
        return "constraint"

    def confidence(self) -> float:
        return 0.95 if Z3_AVAILABLE else 0.70

    def analyze(self, subgraph: "SubGraph", query: str = "") -> AgentResult:
        """Analyze the subgraph using constraint solving.

        Args:
            subgraph: SubGraph to analyze
            query: Optional query context

        Returns:
            AgentResult with constraint violations as findings
        """
        if not subgraph.nodes:
            return self._create_empty_result()

        # Extract constraints from nodes
        constraints = self._extract_constraints(subgraph)

        # Check vulnerability conditions
        violations = []
        for condition in self.vulnerability_conditions:
            violation = self._check_condition(condition, constraints, subgraph)
            if violation and violation.satisfied:
                violations.append(violation)

        # Create evidence
        evidence = []
        for violation in violations:
            evidence.append(AgentEvidence(
                type=EvidenceType.CONSTRAINT,
                data=violation.to_dict(),
                description=violation.condition.description,
                confidence=violation.confidence,
                source_nodes=self._get_related_nodes(violation, constraints),
            ))

        # Compute overall confidence
        if violations:
            overall_confidence = 0.95 if Z3_AVAILABLE else 0.80
        else:
            overall_confidence = self.confidence() * 0.6

        return AgentResult(
            agent=self.agent_name,
            matched=bool(violations),
            findings=[v.to_dict() for v in violations],
            confidence=overall_confidence,
            evidence=evidence,
            metadata={
                "z3_available": Z3_AVAILABLE,
                "constraints_extracted": len(constraints),
                "conditions_checked": len(self.vulnerability_conditions),
                "violations_found": len(violations),
            },
        )

    def _extract_constraints(self, subgraph: "SubGraph") -> List[Constraint]:
        """Extract constraints from subgraph nodes."""
        constraints = []

        for node_id, node in subgraph.nodes.items():
            if node.type != "Function":
                continue

            props = node.properties

            # Access control constraint
            if props.get("has_access_gate"):
                constraints.append(Constraint(
                    id=f"ac:{node_id}",
                    type=ConstraintType.ACCESS_CONTROL,
                    description="Access control check present",
                    source_node=node_id,
                    expression="caller == owner || has_role(caller)",
                ))

            # Reentrancy guard constraint
            if props.get("has_reentrancy_guard"):
                constraints.append(Constraint(
                    id=f"rg:{node_id}",
                    type=ConstraintType.REENTRANCY_GUARD,
                    description="Reentrancy guard present",
                    source_node=node_id,
                    expression="!locked",
                ))

            # Balance check constraint
            if props.get("checks_balance_before_transfer"):
                constraints.append(Constraint(
                    id=f"bc:{node_id}",
                    type=ConstraintType.BALANCE_CHECK,
                    description="Balance check before transfer",
                    source_node=node_id,
                    expression="balance[user] >= amount",
                ))

        return constraints

    def _check_condition(
        self,
        condition: VulnerabilityCondition,
        constraints: List[Constraint],
        subgraph: "SubGraph",
    ) -> Optional[ConstraintViolation]:
        """Check if a vulnerability condition can be satisfied.

        Uses Z3 if available, otherwise falls back to heuristics.
        """
        if Z3_AVAILABLE:
            return self._check_with_z3(condition, constraints, subgraph)
        else:
            return self._check_with_heuristics(condition, constraints, subgraph)

    def _check_with_z3(
        self,
        condition: VulnerabilityCondition,
        constraints: List[Constraint],
        subgraph: "SubGraph",
    ) -> Optional[ConstraintViolation]:
        """Check condition using Z3 SMT solver.

        Checks each function individually for the vulnerability condition.
        """
        # Check each function for the vulnerability
        for node_id, node in subgraph.nodes.items():
            if node.type != "Function":
                continue

            props = node.properties

            # Collect facts for this specific function
            facts = {
                "external_call": bool(props.get("has_external_calls") or props.get("has_low_level_calls")),
                "reentrancy_guard": bool(props.get("has_reentrancy_guard")),
                "state_write_after": bool(props.get("state_write_after_external_call")),
                "access_gate": bool(props.get("has_access_gate")),
                "writes_privileged": bool(props.get("writes_privileged_state")),
                "transfers_value": "TRANSFERS_VALUE_OUT" in props.get("semantic_ops", []),
                "balance_check": bool(props.get("checks_balance_before_transfer")),
            }

            # Use Z3 to formally verify the conditions
            solver = Solver()

            # Create symbolic variables
            has_external_call = Bool("has_external_call")
            has_reentrancy_guard = Bool("has_reentrancy_guard")
            has_state_write_after = Bool("has_state_write_after")
            has_access_gate = Bool("has_access_gate")
            writes_privileged = Bool("writes_privileged")
            transfers_value = Bool("transfers_value")
            has_balance_check = Bool("has_balance_check")

            # Add facts as constraints (set variables to their actual values)
            solver.add(has_external_call == facts["external_call"])
            solver.add(has_reentrancy_guard == facts["reentrancy_guard"])
            solver.add(has_state_write_after == facts["state_write_after"])
            solver.add(has_access_gate == facts["access_gate"])
            solver.add(writes_privileged == facts["writes_privileged"])
            solver.add(transfers_value == facts["transfers_value"])
            solver.add(has_balance_check == facts["balance_check"])

            # Build vulnerability condition
            vuln_condition = None
            if condition.type == VulnerabilityConditionType.REENTRANCY_POSSIBLE:
                vuln_condition = And(
                    has_external_call,
                    Not(has_reentrancy_guard),
                    has_state_write_after,
                )
            elif condition.type == VulnerabilityConditionType.UNAUTHORIZED_ACCESS:
                vuln_condition = And(
                    writes_privileged,
                    Not(has_access_gate),
                )
            elif condition.type == VulnerabilityConditionType.BALANCE_MANIPULATION:
                vuln_condition = And(
                    transfers_value,
                    Not(has_balance_check),
                )

            if vuln_condition is None:
                continue

            # Check if vulnerability condition is satisfiable given the facts
            solver.push()
            solver.add(vuln_condition)
            result = solver.check()
            solver.pop()

            if result == sat:
                facts["vulnerable_function"] = node_id
                return ConstraintViolation(
                    condition=condition,
                    satisfied=True,
                    model=facts,
                    confidence=0.95,
                )

        return None

    def _check_with_heuristics(
        self,
        condition: VulnerabilityCondition,
        constraints: List[Constraint],
        subgraph: "SubGraph",
    ) -> Optional[ConstraintViolation]:
        """Check condition using heuristic analysis (fallback when Z3 unavailable).

        Checks each function individually for the vulnerability condition.
        """
        # Check each function for the vulnerability
        for node_id, node in subgraph.nodes.items():
            if node.type != "Function":
                continue

            props = node.properties

            # Collect facts for this specific function
            facts = {
                "external_call": bool(props.get("has_external_calls") or props.get("has_low_level_calls")),
                "reentrancy_guard": bool(props.get("has_reentrancy_guard")),
                "state_write_after": bool(props.get("state_write_after_external_call")),
                "access_gate": bool(props.get("has_access_gate")),
                "writes_privileged": bool(props.get("writes_privileged_state")),
                "transfers_value": "TRANSFERS_VALUE_OUT" in props.get("semantic_ops", []),
                "balance_check": bool(props.get("checks_balance_before_transfer")),
            }

            # Check conditions
            satisfied = False
            if condition.type == VulnerabilityConditionType.REENTRANCY_POSSIBLE:
                satisfied = (
                    facts["external_call"]
                    and not facts["reentrancy_guard"]
                    and facts["state_write_after"]
                )
            elif condition.type == VulnerabilityConditionType.UNAUTHORIZED_ACCESS:
                satisfied = facts["writes_privileged"] and not facts["access_gate"]
            elif condition.type == VulnerabilityConditionType.BALANCE_MANIPULATION:
                satisfied = facts["transfers_value"] and not facts["balance_check"]

            if satisfied:
                facts["vulnerable_function"] = node_id
                return ConstraintViolation(
                    condition=condition,
                    satisfied=True,
                    model=facts,
                    confidence=0.75,  # Lower confidence without Z3
                )

        return None

    def _get_related_nodes(
        self,
        violation: ConstraintViolation,
        constraints: List[Constraint],
    ) -> List[str]:
        """Get node IDs related to a violation."""
        return [c.source_node for c in constraints]
