"""
Invariant Types and Data Structures

Defines the core types for formal invariant synthesis.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from enum import Enum
from datetime import datetime


class InvariantType(Enum):
    """Categories of invariants."""
    # Balance invariants
    BALANCE_CONSERVATION = "balance_conservation"  # sum(balances) == totalSupply
    BALANCE_NON_NEGATIVE = "balance_non_negative"  # balance >= 0
    BALANCE_BOUNDED = "balance_bounded"            # balance <= maxBalance

    # Ownership invariants
    SINGLE_OWNER = "single_owner"                  # exactly one owner
    OWNER_NON_ZERO = "owner_non_zero"              # owner != address(0)
    ROLE_CONSISTENCY = "role_consistency"          # role assignments consistent

    # State machine invariants
    STATE_VALID = "state_valid"                    # state in valid set
    STATE_TRANSITION = "state_transition"          # valid transitions only
    STATE_FINAL = "state_final"                    # final states irreversible

    # Temporal invariants
    MONOTONIC_INCREASE = "monotonic_increase"      # value only increases
    MONOTONIC_DECREASE = "monotonic_decrease"      # value only decreases
    TIMESTAMP_ORDERED = "timestamp_ordered"        # timestamps increase

    # Access control invariants
    PERMISSION_REQUIRED = "permission_required"    # action requires permission
    ADMIN_PRIVILEGED = "admin_privileged"          # admin-only functions
    SELF_ONLY = "self_only"                        # msg.sender == this

    # Mathematical invariants
    SUM_PRESERVED = "sum_preserved"                # sum of values constant
    RATIO_MAINTAINED = "ratio_maintained"          # ratio between values
    BOUNDS_RESPECTED = "bounds_respected"          # min <= x <= max

    # Reentrancy invariants
    LOCK_HELD = "lock_held"                        # lock during execution
    NO_CALLBACK = "no_callback"                    # no external calls

    # Custom
    CUSTOM = "custom"


class InvariantStrength(Enum):
    """How strong/reliable the invariant is."""
    PROVEN = "proven"           # Formally verified
    LIKELY = "likely"           # High confidence from analysis
    CANDIDATE = "candidate"     # Needs verification
    VIOLATED = "violated"       # Known to be broken


@dataclass
class Invariant:
    """A formal property that must always hold."""
    invariant_id: str
    invariant_type: InvariantType
    name: str
    description: str

    # Formal specification
    predicate: str              # Logical formula (e.g., "balance[addr] >= 0")
    variables: List[str]        # Variables involved
    quantifiers: Dict[str, str] = field(default_factory=dict)  # forall/exists

    # Scope
    contract: Optional[str] = None
    functions: List[str] = field(default_factory=list)  # Functions where it applies

    # Verification status
    strength: InvariantStrength = InvariantStrength.CANDIDATE
    confidence: float = 0.5     # 0.0 to 1.0
    proof_method: Optional[str] = None  # How it was verified

    # Metadata
    discovered_at: datetime = field(default_factory=datetime.now)
    discovered_by: str = ""     # Mining technique that found it
    tags: Set[str] = field(default_factory=set)

    def is_verified(self) -> bool:
        """Check if invariant is formally verified."""
        return self.strength == InvariantStrength.PROVEN

    def is_violated(self) -> bool:
        """Check if invariant is known to be violated."""
        return self.strength == InvariantStrength.VIOLATED

    def to_solidity_assert(self) -> str:
        """Convert to Solidity assertion."""
        return f'assert({self.predicate}); // {self.name}'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "type": self.invariant_type.value,
            "name": self.name,
            "predicate": self.predicate,
            "strength": self.strength.value,
            "confidence": round(self.confidence, 3),
            "contract": self.contract,
            "functions": self.functions,
        }


@dataclass
class InvariantViolation:
    """A detected invariant violation."""
    violation_id: str
    invariant: Invariant
    function: str
    description: str

    # Counter-example
    counter_example: Optional[Dict[str, Any]] = None
    trace: List[str] = field(default_factory=list)

    # Impact
    severity: str = "medium"    # critical, high, medium, low
    exploitable: bool = False

    # Fix suggestion
    fix_suggestion: Optional[str] = None

    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "invariant": self.invariant.name,
            "function": self.function,
            "description": self.description,
            "severity": self.severity,
            "exploitable": self.exploitable,
            "has_counter_example": self.counter_example is not None,
        }


@dataclass
class VerificationResult:
    """Result of invariant verification."""
    invariant_id: str
    verified: bool
    method: str                 # z3, symbolic, testing, etc.

    # If verified
    proof_time_ms: int = 0

    # If violated
    violation: Optional[InvariantViolation] = None

    # Metadata
    attempts: int = 1
    confidence: float = 0.0  # Set based on verification result

    def __post_init__(self):
        """Set confidence based on verification result if not explicitly set."""
        if self.confidence == 0.0 and self.verified:
            self.confidence = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "verified": self.verified,
            "method": self.method,
            "proof_time_ms": self.proof_time_ms,
            "confidence": round(self.confidence, 3),
        }
