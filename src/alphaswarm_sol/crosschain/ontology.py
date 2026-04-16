"""
Universal Vulnerability Ontology (UVO)

Chain-agnostic representation of security vulnerabilities using abstract operations.
Enables cross-chain vulnerability transfer and detection.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from enum import Enum
import hashlib


class Chain(Enum):
    """Supported blockchain platforms."""
    EVM = "evm"           # Ethereum, Polygon, BSC, etc.
    SOLANA = "solana"     # Solana with Anchor framework
    MOVE = "move"         # Aptos, Sui (Move language)
    COSMOS = "cosmos"     # Cosmos SDK chains
    NEAR = "near"         # NEAR Protocol
    TON = "ton"           # TON blockchain
    CARDANO = "cardano"   # Cardano (Plutus)


class OperationType(Enum):
    """Abstract operation types (chain-agnostic)."""
    # Value operations
    READ_VALUE = "read_value"           # Read user balance/amount
    WRITE_VALUE = "write_value"         # Write user balance/amount
    TRANSFER_VALUE = "transfer_value"   # Transfer value to external
    MINT_VALUE = "mint_value"           # Create new value
    BURN_VALUE = "burn_value"           # Destroy value

    # State operations
    READ_STATE = "read_state"           # Read contract state
    WRITE_STATE = "write_state"         # Write contract state
    READ_GLOBAL = "read_global"         # Read global/shared state
    WRITE_GLOBAL = "write_global"       # Write global/shared state

    # External operations
    CALL_EXTERNAL = "call_external"     # Call external contract/program
    CALL_UNTRUSTED = "call_untrusted"   # Call potentially untrusted code
    READ_EXTERNAL = "read_external"     # Read from external source (oracle)

    # Access control
    CHECK_PERMISSION = "check_permission"   # Verify access rights
    MODIFY_PERMISSION = "modify_permission" # Change access rights
    CHECK_OWNER = "check_owner"             # Verify ownership
    MODIFY_OWNER = "modify_owner"           # Transfer ownership

    # Cryptographic
    VERIFY_SIGNATURE = "verify_signature"   # Signature verification
    HASH_DATA = "hash_data"                 # Hash computation

    # Control flow
    LOOP_BOUNDED = "loop_bounded"       # Bounded iteration
    LOOP_UNBOUNDED = "loop_unbounded"   # Unbounded iteration (DoS risk)

    # Token operations
    TOKEN_APPROVE = "token_approve"     # Approve token spending
    TOKEN_TRANSFER = "token_transfer"   # Transfer tokens
    TOKEN_CALLBACK = "token_callback"   # Token callback (ERC777, etc.)


class InvariantType(Enum):
    """Security invariants that can be violated."""
    CEI_PATTERN = "cei_pattern"                     # Checks-Effects-Interactions
    ACCESS_CONTROL = "access_control"               # Proper authorization
    REENTRANCY_GUARD = "reentrancy_guard"           # Protection against reentry
    ORACLE_FRESHNESS = "oracle_freshness"           # Staleness check
    ORACLE_MANIPULATION = "oracle_manipulation"     # Price manipulation
    INTEGER_OVERFLOW = "integer_overflow"           # Arithmetic bounds
    DOUBLE_SPENDING = "double_spending"             # Replay protection
    FRONT_RUNNING = "front_running"                 # MEV protection
    DENIAL_OF_SERVICE = "denial_of_service"         # Gas/compute limits
    SIGNATURE_REPLAY = "signature_replay"           # Nonce/chain protection
    INITIALIZATION = "initialization"               # Proper init guards
    UPGRADE_SAFETY = "upgrade_safety"               # Safe upgrade patterns


@dataclass
class AbstractOperation:
    """
    Chain-agnostic semantic operation.

    Describes WHAT is happening, not HOW it's implemented.
    """
    operation: OperationType
    target: str                         # What's being operated on (e.g., "balance", "oracle", "owner")
    timing: int                         # Order in execution sequence
    conditions: List[str] = field(default_factory=list)  # Guards/checks applied
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash((self.operation, self.target, self.timing))

    def __eq__(self, other):
        if not isinstance(other, AbstractOperation):
            return False
        return (
            self.operation == other.operation and
            self.target == other.target
        )

    def to_signature_element(self) -> str:
        """Convert to signature string element."""
        op_short = self.operation.value[:3].upper()
        target_short = self.target[:3] if self.target else ""
        return f"{op_short}:{target_short}"

    def matches(self, other: "AbstractOperation", strict: bool = False) -> bool:
        """Check if operations match."""
        if self.operation != other.operation:
            return False

        if strict:
            return self.target == other.target

        # Fuzzy target matching (balance ~ userBalance ~ accountBalance)
        if self.target == other.target:
            return True

        # Category-based matching
        value_targets = {"balance", "amount", "value", "funds", "lamports", "coins"}
        if self.target in value_targets and other.target in value_targets:
            return True

        return False


@dataclass
class AbstractVulnerabilitySignature:
    """
    Universal vulnerability pattern.

    Represents a vulnerability in chain-agnostic terms that can be
    translated to/from specific blockchain implementations.
    """
    vuln_id: str
    vuln_name: str
    vuln_category: str                                   # e.g., "reentrancy", "access_control"
    abstract_operations: List[AbstractOperation]
    invariant_violated: InvariantType
    severity: str                                        # critical, high, medium, low

    # Operation ordering constraints (if order matters)
    ordering_constraints: List[Dict[str, str]] = field(default_factory=list)

    # Chain-specific manifestations (populated by translators)
    chain_patterns: Dict[Chain, Dict] = field(default_factory=dict)

    # Metadata
    cwe_ids: List[str] = field(default_factory=list)     # CWE mappings
    real_exploits: List[str] = field(default_factory=list)  # Known exploits
    description: str = ""

    def get_signature_hash(self) -> str:
        """Get unique hash of the vulnerability signature."""
        sig_parts = [op.to_signature_element() for op in self.abstract_operations]
        sig_str = "->".join(sig_parts)
        return hashlib.sha256(sig_str.encode()).hexdigest()[:16]

    def get_behavioral_signature(self) -> str:
        """Get human-readable behavioral signature."""
        return "->".join(op.to_signature_element() for op in self.abstract_operations)

    def matches_signature(
        self,
        operations: List[AbstractOperation],
        check_ordering: bool = True
    ) -> bool:
        """
        Check if a list of operations matches this vulnerability signature.

        Args:
            operations: List of abstract operations to check
            check_ordering: Whether to verify operation ordering

        Returns:
            True if operations match the vulnerability pattern
        """
        # Must have at least the required operations
        required_ops = set((op.operation, op.target) for op in self.abstract_operations)
        actual_ops = set((op.operation, op.target) for op in operations)

        if not required_ops.issubset(actual_ops):
            return False

        if check_ordering and self.ordering_constraints:
            # Check ordering constraints
            op_timings = {
                (op.operation, op.target): op.timing
                for op in operations
            }

            for constraint in self.ordering_constraints:
                before_key = (
                    OperationType(constraint.get("before_op")),
                    constraint.get("before_target", "")
                )
                after_key = (
                    OperationType(constraint.get("after_op")),
                    constraint.get("after_target", "")
                )

                if before_key in op_timings and after_key in op_timings:
                    if op_timings[before_key] >= op_timings[after_key]:
                        return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "vuln_id": self.vuln_id,
            "vuln_name": self.vuln_name,
            "vuln_category": self.vuln_category,
            "invariant_violated": self.invariant_violated.value,
            "severity": self.severity,
            "behavioral_signature": self.get_behavioral_signature(),
            "signature_hash": self.get_signature_hash(),
            "operations": [
                {
                    "operation": op.operation.value,
                    "target": op.target,
                    "timing": op.timing,
                    "conditions": op.conditions,
                }
                for op in self.abstract_operations
            ],
            "ordering_constraints": self.ordering_constraints,
            "cwe_ids": self.cwe_ids,
            "description": self.description,
        }


# Pre-defined universal vulnerability signatures
UNIVERSAL_SIGNATURES = {
    "reentrancy_classic": AbstractVulnerabilitySignature(
        vuln_id="UVO-REEN-001",
        vuln_name="Classic Reentrancy",
        vuln_category="reentrancy",
        abstract_operations=[
            AbstractOperation(OperationType.READ_VALUE, "balance", 0),
            AbstractOperation(OperationType.TRANSFER_VALUE, "external", 1),
            AbstractOperation(OperationType.WRITE_VALUE, "balance", 2),
        ],
        ordering_constraints=[
            {"before_op": "transfer_value", "before_target": "external",
             "after_op": "write_value", "after_target": "balance"}
        ],
        invariant_violated=InvariantType.CEI_PATTERN,
        severity="critical",
        cwe_ids=["CWE-841"],
        real_exploits=["The DAO", "Cream Finance"],
        description="External call before state update allows reentrant calls",
    ),

    "access_control_missing": AbstractVulnerabilitySignature(
        vuln_id="UVO-AUTH-001",
        vuln_name="Missing Access Control",
        vuln_category="access_control",
        abstract_operations=[
            AbstractOperation(OperationType.WRITE_STATE, "privileged", 0),
        ],
        ordering_constraints=[],
        invariant_violated=InvariantType.ACCESS_CONTROL,
        severity="critical",
        cwe_ids=["CWE-284", "CWE-862"],
        real_exploits=["Parity Wallet", "Wormhole"],
        description="Privileged state modification without access control check",
    ),

    "oracle_staleness": AbstractVulnerabilitySignature(
        vuln_id="UVO-ORACLE-001",
        vuln_name="Oracle Staleness",
        vuln_category="oracle",
        abstract_operations=[
            AbstractOperation(OperationType.READ_EXTERNAL, "oracle_price", 0),
            AbstractOperation(OperationType.WRITE_VALUE, "calculation", 1),
        ],
        ordering_constraints=[],
        invariant_violated=InvariantType.ORACLE_FRESHNESS,
        severity="high",
        cwe_ids=["CWE-346"],
        real_exploits=["Harvest Finance", "Venus Protocol"],
        description="Oracle data used without freshness validation",
    ),

    "unbounded_loop": AbstractVulnerabilitySignature(
        vuln_id="UVO-DOS-001",
        vuln_name="Unbounded Loop DoS",
        vuln_category="denial_of_service",
        abstract_operations=[
            AbstractOperation(OperationType.LOOP_UNBOUNDED, "user_data", 0),
            AbstractOperation(OperationType.CALL_EXTERNAL, "iteration", 1),
        ],
        ordering_constraints=[],
        invariant_violated=InvariantType.DENIAL_OF_SERVICE,
        severity="medium",
        cwe_ids=["CWE-400", "CWE-770"],
        description="Unbounded loop with external calls can exhaust gas",
    ),

    "signature_replay": AbstractVulnerabilitySignature(
        vuln_id="UVO-SIG-001",
        vuln_name="Signature Replay",
        vuln_category="cryptographic",
        abstract_operations=[
            AbstractOperation(OperationType.VERIFY_SIGNATURE, "user", 0),
            AbstractOperation(OperationType.WRITE_STATE, "action", 1),
        ],
        ordering_constraints=[],
        invariant_violated=InvariantType.SIGNATURE_REPLAY,
        severity="high",
        cwe_ids=["CWE-294"],
        real_exploits=["Wintermute"],
        description="Signature can be replayed without nonce or chain protection",
    ),

    "initialization_missing": AbstractVulnerabilitySignature(
        vuln_id="UVO-INIT-001",
        vuln_name="Missing Initialization Guard",
        vuln_category="initialization",
        abstract_operations=[
            AbstractOperation(OperationType.MODIFY_OWNER, "owner", 0),
        ],
        ordering_constraints=[],
        invariant_violated=InvariantType.INITIALIZATION,
        severity="critical",
        cwe_ids=["CWE-908"],
        real_exploits=["Nomad Bridge"],
        description="Initializer can be called multiple times or by unauthorized caller",
    ),
}


def get_signature_by_category(category: str) -> List[AbstractVulnerabilitySignature]:
    """Get all vulnerability signatures for a category."""
    return [
        sig for sig in UNIVERSAL_SIGNATURES.values()
        if sig.vuln_category == category
    ]


def get_signature_by_invariant(invariant: InvariantType) -> List[AbstractVulnerabilitySignature]:
    """Get all vulnerability signatures violating an invariant."""
    return [
        sig for sig in UNIVERSAL_SIGNATURES.values()
        if sig.invariant_violated == invariant
    ]
