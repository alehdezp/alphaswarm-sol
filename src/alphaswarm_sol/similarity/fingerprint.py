"""
Semantic Fingerprinting

Generate semantic fingerprints from code that capture
what the code does, not how it's written.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any, Tuple
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)


class FingerprintType(Enum):
    """Types of semantic fingerprints."""
    OPERATION_SEQUENCE = "operation_sequence"  # Sequence of operations
    BEHAVIORAL_SIGNATURE = "behavioral_signature"  # What function does
    CFG_STRUCTURE = "cfg_structure"  # Control flow graph shape
    DATA_FLOW = "data_flow"  # How data flows through function
    STATE_TRANSITIONS = "state_transitions"  # State variable changes
    CALL_GRAPH = "call_graph"  # External call patterns
    ACCESS_PATTERN = "access_pattern"  # Permission checks
    VALUE_FLOW = "value_flow"  # Value transfer patterns


@dataclass
class OperationSequence:
    """Sequence of semantic operations in a function."""
    operations: List[str]  # e.g., ["READS_BALANCE", "TRANSFERS_OUT", "WRITES_BALANCE"]
    guards: List[str] = field(default_factory=list)  # Guards/checks applied
    loops: int = 0  # Number of loops
    branches: int = 0  # Number of branches

    def to_hash(self) -> str:
        """Generate hash of operation sequence."""
        content = f"{','.join(self.operations)}|{','.join(self.guards)}|{self.loops}|{self.branches}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def similarity(self, other: "OperationSequence") -> float:
        """Calculate similarity to another sequence."""
        if not self.operations and not other.operations:
            return 1.0
        if not self.operations or not other.operations:
            return 0.0

        # Longest common subsequence
        lcs_len = self._lcs_length(self.operations, other.operations)
        max_len = max(len(self.operations), len(other.operations))

        return lcs_len / max_len if max_len > 0 else 0.0

    def _lcs_length(self, seq1: List[str], seq2: List[str]) -> int:
        """Calculate longest common subsequence length."""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])

        return dp[m][n]


@dataclass
class SemanticFingerprint:
    """Semantic fingerprint of a function or contract."""
    fingerprint_id: str
    fingerprint_type: FingerprintType
    source_name: str  # Function or contract name
    contract_name: Optional[str] = None

    # Core fingerprint data
    hash_value: str = ""
    operations: List[str] = field(default_factory=list)
    features: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    complexity: int = 0
    num_operations: int = 0
    num_external_calls: int = 0
    num_state_writes: int = 0
    num_guards: int = 0

    def to_vector(self) -> List[float]:
        """Convert to numeric vector for similarity calculation."""
        # Create feature vector
        vector = [
            float(self.complexity),
            float(self.num_operations),
            float(self.num_external_calls),
            float(self.num_state_writes),
            float(self.num_guards),
        ]

        # Add operation presence flags
        common_ops = [
            "READS_USER_BALANCE", "WRITES_USER_BALANCE", "TRANSFERS_VALUE_OUT",
            "CHECKS_PERMISSION", "MODIFIES_OWNER", "CALLS_EXTERNAL",
            "READS_ORACLE", "MODIFIES_CRITICAL_STATE", "EMITS_EVENT",
        ]
        for op in common_ops:
            vector.append(1.0 if op in self.operations else 0.0)

        return vector

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fingerprint_id": self.fingerprint_id,
            "type": self.fingerprint_type.value,
            "source": self.source_name,
            "contract": self.contract_name,
            "hash": self.hash_value,
            "operations": self.operations,
            "complexity": self.complexity,
            "num_operations": self.num_operations,
        }


@dataclass
class FingerprintConfig:
    """Configuration for fingerprint generation."""
    include_operations: bool = True
    include_cfg: bool = True
    include_data_flow: bool = True
    include_guards: bool = True

    # Normalization
    normalize_names: bool = True  # Ignore variable/function names
    normalize_types: bool = False  # Map similar types together
    normalize_constants: bool = True  # Ignore specific constant values

    # Granularity
    per_function: bool = True
    per_contract: bool = True


class FingerprintGenerator:
    """Generate semantic fingerprints from code or KG data."""

    def __init__(self, config: Optional[FingerprintConfig] = None):
        self.config = config or FingerprintConfig()
        self._fingerprint_counter = 0

    def _generate_id(self) -> str:
        """Generate unique fingerprint ID."""
        self._fingerprint_counter += 1
        return f"FP-{self._fingerprint_counter:06d}"

    def generate_from_function(
        self,
        function_name: str,
        operations: List[str],
        properties: Dict[str, Any],
        contract_name: Optional[str] = None,
    ) -> SemanticFingerprint:
        """Generate fingerprint from function data."""
        # Calculate hash from operations
        op_sequence = OperationSequence(
            operations=operations,
            guards=self._extract_guards(properties),
            loops=properties.get("loop_count", 0),
            branches=properties.get("branch_count", 0),
        )

        # Count various metrics
        num_external = sum(1 for op in operations if "CALLS" in op or "EXTERNAL" in op)
        num_writes = sum(1 for op in operations if "WRITES" in op or "MODIFIES" in op)
        num_guards = len(op_sequence.guards)

        return SemanticFingerprint(
            fingerprint_id=self._generate_id(),
            fingerprint_type=FingerprintType.OPERATION_SEQUENCE,
            source_name=function_name,
            contract_name=contract_name,
            hash_value=op_sequence.to_hash(),
            operations=operations.copy(),
            features={
                "operation_sequence": op_sequence,
                "visibility": properties.get("visibility", "internal"),
                "modifiers": properties.get("modifiers", []),
            },
            complexity=len(operations) + op_sequence.loops * 2 + op_sequence.branches,
            num_operations=len(operations),
            num_external_calls=num_external,
            num_state_writes=num_writes,
            num_guards=num_guards,
        )

    def _extract_guards(self, properties: Dict[str, Any]) -> List[str]:
        """Extract guard/check information from properties."""
        guards = []

        if properties.get("has_access_gate"):
            guards.append("ACCESS_GATE")
        if properties.get("has_reentrancy_guard"):
            guards.append("REENTRANCY_GUARD")
        if properties.get("has_zero_check"):
            guards.append("ZERO_CHECK")
        if properties.get("has_bounds_check"):
            guards.append("BOUNDS_CHECK")
        if properties.get("has_staleness_check"):
            guards.append("STALENESS_CHECK")

        return guards

    def generate_from_kg(
        self,
        kg_data: Dict[str, Any],
        contract_name: str,
    ) -> List[SemanticFingerprint]:
        """Generate fingerprints from knowledge graph data."""
        fingerprints = []

        functions = kg_data.get("functions", [])
        for func in functions:
            func_name = func.get("name", "unknown")
            operations = func.get("operations", [])
            properties = func.get("properties", {})

            fp = self.generate_from_function(
                function_name=func_name,
                operations=operations,
                properties=properties,
                contract_name=contract_name,
            )
            fingerprints.append(fp)

        # Generate contract-level fingerprint
        if self.config.per_contract:
            all_ops = []
            total_complexity = 0

            for func in functions:
                all_ops.extend(func.get("operations", []))
                total_complexity += len(func.get("operations", []))

            contract_fp = SemanticFingerprint(
                fingerprint_id=self._generate_id(),
                fingerprint_type=FingerprintType.BEHAVIORAL_SIGNATURE,
                source_name=contract_name,
                contract_name=contract_name,
                hash_value=hashlib.sha256(",".join(sorted(set(all_ops))).encode()).hexdigest()[:16],
                operations=list(set(all_ops)),
                features={
                    "num_functions": len(functions),
                    "unique_operations": len(set(all_ops)),
                },
                complexity=total_complexity,
                num_operations=len(all_ops),
                num_external_calls=sum(1 for op in all_ops if "CALLS" in op),
                num_state_writes=sum(1 for op in all_ops if "WRITES" in op),
                num_guards=sum(1 for f in functions if f.get("properties", {}).get("has_access_gate")),
            )
            fingerprints.append(contract_fp)

        return fingerprints

    def generate_behavioral_signature(
        self,
        operations: List[str],
        name: str = "unknown",
    ) -> str:
        """Generate behavioral signature string (e.g., R:bal→X:out→W:bal)."""
        sig_parts = []

        for op in operations:
            if "READS" in op and "BALANCE" in op:
                sig_parts.append("R:bal")
            elif "WRITES" in op and "BALANCE" in op:
                sig_parts.append("W:bal")
            elif "TRANSFERS" in op and "OUT" in op:
                sig_parts.append("X:out")
            elif "TRANSFERS" in op and "IN" in op:
                sig_parts.append("X:in")
            elif "CHECKS" in op and "PERMISSION" in op:
                sig_parts.append("C:perm")
            elif "MODIFIES" in op and "OWNER" in op:
                sig_parts.append("M:own")
            elif "CALLS" in op and "EXTERNAL" in op:
                sig_parts.append("X:call")
            elif "READS" in op and "ORACLE" in op:
                sig_parts.append("R:orc")
            elif "EMITS" in op:
                sig_parts.append("E:evt")

        return "→".join(sig_parts) if sig_parts else "∅"

    def compare_fingerprints(
        self,
        fp1: SemanticFingerprint,
        fp2: SemanticFingerprint,
    ) -> float:
        """Compare two fingerprints for similarity (0.0-1.0)."""
        # Quick hash check
        if fp1.hash_value == fp2.hash_value:
            return 1.0

        # Vector similarity (cosine)
        v1 = fp1.to_vector()
        v2 = fp2.to_vector()

        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        cosine_sim = dot_product / (norm1 * norm2)

        # Operation sequence similarity
        if "operation_sequence" in fp1.features and "operation_sequence" in fp2.features:
            seq_sim = fp1.features["operation_sequence"].similarity(fp2.features["operation_sequence"])
            # Combine: 60% sequence, 40% vector
            return 0.6 * seq_sim + 0.4 * cosine_sim

        return cosine_sim
