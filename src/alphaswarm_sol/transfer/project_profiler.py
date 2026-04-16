"""
Phase 4: Project Profiler

Creates project profiles for cross-project similarity matching and
vulnerability transfer learning.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, TYPE_CHECKING
from pathlib import Path
import math

if TYPE_CHECKING:
    from alphaswarm_sol.kg.schema import KnowledgeGraph, Node


@dataclass
class ProjectProfile:
    """
    Embedding of a Solidity project for similarity matching.

    Captures architecture patterns, DeFi primitives, and operation
    distributions to enable finding "similar projects" for transfer learning.
    """
    project_id: str
    name: str

    # Architecture patterns
    is_upgradeable: bool
    proxy_pattern: Optional[str] = None  # "transparent", "uups", "beacon", None
    uses_oracles: bool = False
    uses_governance: bool = False
    uses_multisig: bool = False
    uses_timelock: bool = False

    # DeFi classification
    protocol_type: str = "utility"  # "dex", "lending", "vault", "nft", "oracle_consumer", "utility"
    primitives_used: List[str] = field(default_factory=list)  # ["amm", "flash_loan", "staking"]

    # Aggregate stats
    num_contracts: int = 0
    num_functions: int = 0
    num_state_variables: int = 0
    operation_histogram: Dict[str, int] = field(default_factory=dict)  # Semantic ops distribution

    # Complexity metrics
    avg_function_complexity: float = 0.0
    max_function_complexity: int = 0

    # Security profile
    has_access_control: bool = False
    has_reentrancy_guards: bool = False
    has_pause_mechanism: bool = False

    # Known vulnerabilities (for audited projects)
    known_vulns: List[str] = field(default_factory=list)
    audit_reports: List[str] = field(default_factory=list)

    # Vector embedding for similarity (normalized operation histogram)
    embedding: Optional[List[float]] = None

    def similarity_to(self, other: "ProjectProfile") -> float:
        """
        Calculate cosine similarity between this and another project.

        Returns:
            Float between 0.0 (completely different) and 1.0 (identical)
        """
        if not self.embedding or not other.embedding:
            return 0.0

        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(self.embedding, other.embedding))
        mag_a = math.sqrt(sum(a * a for a in self.embedding))
        mag_b = math.sqrt(sum(b * b for b in other.embedding))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot_product / (mag_a * mag_b)


class ProjectProfiler:
    """
    Creates project profiles for similarity matching.

    Analyzes a KnowledgeGraph to extract:
    - Architecture patterns (proxy, upgradeable, oracle usage)
    - Protocol type (DEX, lending, vault, etc.)
    - DeFi primitives (AMM, flash loans, staking)
    - Operation distribution embedding
    """

    # Known DeFi primitives and their operation signatures
    PRIMITIVE_SIGNATURES = {
        "amm": {"READS_USER_BALANCE", "WRITES_USER_BALANCE", "TRANSFERS_VALUE_OUT"},
        "flash_loan": {"CALLS_EXTERNAL", "TRANSFERS_VALUE_OUT", "CHECKS_PERMISSION"},
        "staking": {"WRITES_USER_BALANCE", "READS_EXTERNAL_VALUE", "MODIFIES_CRITICAL_STATE"},
        "vault": {"WRITES_USER_BALANCE", "TRANSFERS_VALUE_OUT", "CHECKS_PERMISSION"},
        "oracle_integration": {"READS_ORACLE", "READS_EXTERNAL_VALUE"},
        "governance": {"MODIFIES_ROLES", "CHECKS_PERMISSION", "MODIFIES_OWNER"},
        "timelock": {"CHECKS_PERMISSION", "MODIFIES_CRITICAL_STATE"},
        "liquidity_pool": {"WRITES_USER_BALANCE", "READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"},
        "yield_farming": {"READS_EXTERNAL_VALUE", "WRITES_USER_BALANCE", "MODIFIES_CRITICAL_STATE"},
        "token_bridge": {"CALLS_EXTERNAL", "TRANSFERS_VALUE_OUT", "MODIFIES_CRITICAL_STATE"},
    }

    def __init__(self):
        # Operation vocabulary for embedding (all possible semantic operations)
        self.operation_vocab = [
            # Value operations
            "TRANSFERS_VALUE_OUT",
            "READS_USER_BALANCE",
            "WRITES_USER_BALANCE",
            "READS_CONTRACT_BALANCE",
            # Access operations
            "CHECKS_PERMISSION",
            "MODIFIES_OWNER",
            "MODIFIES_ROLES",
            # External operations
            "CALLS_EXTERNAL",
            "CALLS_UNTRUSTED",
            "READS_EXTERNAL_VALUE",
            # State operations
            "MODIFIES_CRITICAL_STATE",
            "READS_ORACLE",
            # Control flow
            "HAS_LOOPS",
            "HAS_DELEGATECALL",
        ]

    def profile(self, code_kg: "KnowledgeGraph") -> ProjectProfile:
        """
        Create comprehensive profile from code KG.

        Args:
            code_kg: KnowledgeGraph of the project

        Returns:
            ProjectProfile with all characteristics extracted
        """
        # Collect nodes by type
        contracts = [n for n in code_kg.nodes.values() if n.type == "Contract"]
        functions = [n for n in code_kg.nodes.values() if n.type == "Function"]
        state_vars = [n for n in code_kg.nodes.values() if n.type == "StateVariable"]

        # Count operations across all functions
        op_histogram = self._build_operation_histogram(functions)

        # Detect architecture patterns
        is_upgradeable = any(c.properties.get("is_upgradeable", False) for c in contracts)
        proxy_pattern = self._detect_proxy_pattern(contracts)
        uses_oracles = op_histogram.get("READS_ORACLE", 0) > 0
        uses_governance = op_histogram.get("MODIFIES_ROLES", 0) > 0

        # Detect protocol type
        protocol_type = self._classify_protocol(op_histogram, contracts, functions)

        # Detect primitives
        primitives = self._detect_primitives(op_histogram)

        # Calculate complexity
        complexities = [f.properties.get("cyclomatic_complexity", 1) for f in functions]
        avg_complexity = sum(complexities) / len(complexities) if complexities else 0.0
        max_complexity = max(complexities) if complexities else 0

        # Security features
        has_access = any(f.properties.get("has_access_gate", False) for f in functions)
        has_reentrancy = any(f.properties.get("has_reentrancy_guard", False) for f in functions)
        has_pause = any("pause" in f.label.lower() for f in functions)

        # Generate embedding
        embedding = self._generate_embedding(op_histogram)

        profile = ProjectProfile(
            project_id=code_kg.metadata.get("target", "unknown"),
            name=Path(code_kg.metadata.get("target", "unknown")).stem,
            is_upgradeable=is_upgradeable,
            proxy_pattern=proxy_pattern,
            uses_oracles=uses_oracles,
            uses_governance=uses_governance,
            uses_multisig=self._detect_multisig(functions),
            uses_timelock=self._detect_timelock(functions),
            protocol_type=protocol_type,
            primitives_used=primitives,
            num_contracts=len(contracts),
            num_functions=len(functions),
            num_state_variables=len(state_vars),
            operation_histogram=op_histogram,
            avg_function_complexity=avg_complexity,
            max_function_complexity=max_complexity,
            has_access_control=has_access,
            has_reentrancy_guards=has_reentrancy,
            has_pause_mechanism=has_pause,
            embedding=embedding,
        )

        return profile

    def _build_operation_histogram(self, functions: List["Node"]) -> Dict[str, int]:
        """Count semantic operations across all functions."""
        histogram = {}

        for fn in functions:
            ops = fn.properties.get("semantic_operations", [])
            for op in ops:
                histogram[op] = histogram.get(op, 0) + 1

        return histogram

    def _detect_proxy_pattern(self, contracts: List["Node"]) -> Optional[str]:
        """Detect proxy pattern type."""
        for contract in contracts:
            proxy_type = contract.properties.get("proxy_type")
            if proxy_type:
                return proxy_type
        return None

    def _classify_protocol(
        self,
        histogram: Dict[str, int],
        contracts: List["Node"],
        functions: List["Node"],
    ) -> str:
        """
        Classify protocol type from operation distribution.

        Uses heuristics based on:
        - Operation patterns
        - Contract/function naming
        - Operation ratios
        """
        # Check for lending patterns first (most specific)
        has_borrow = any("borrow" in f.label.lower() for f in functions)
        has_lend = any("lend" in f.label.lower() or "supply" in f.label.lower() for f in functions)

        if has_borrow or has_lend:
            # Confirmed lending protocol
            return "lending"

        # Check for oracle-heavy protocols
        reads_oracle = histogram.get("READS_ORACLE", 0)
        value_transfers = histogram.get("TRANSFERS_VALUE_OUT", 0)
        reads_external = histogram.get("READS_EXTERNAL_VALUE", 0)

        if reads_oracle > 5:
            if value_transfers > 10:
                return "lending"
            return "oracle_consumer"

        # High external reads also suggest lending
        if reads_external > 10 and value_transfers > 5:
            return "lending"

        # Check for DEX patterns (swap-like + balance operations)
        balance_writes = histogram.get("WRITES_USER_BALANCE", 0)

        if balance_writes > 5 and value_transfers > 5:
            # Check for swap-like functions
            has_swap = any("swap" in f.label.lower() for f in functions)
            has_pool = any("pool" in c.label.lower() or "pair" in c.label.lower() for c in contracts)

            if has_swap or has_pool:
                return "dex"

            # Vault pattern (deposit/withdraw focused)
            has_deposit = any("deposit" in f.label.lower() for f in functions)
            has_withdraw = any("withdraw" in f.label.lower() for f in functions)

            if has_deposit and has_withdraw:
                return "vault"

        # NFT protocols
        has_nft_ops = any("erc721" in c.label.lower() or "nft" in c.label.lower() for c in contracts)
        if has_nft_ops:
            return "nft"

        return "utility"

    def _detect_primitives(self, histogram: Dict[str, int]) -> List[str]:
        """
        Detect DeFi primitives from operation histogram.

        Matches operation patterns against known primitive signatures.
        """
        detected = []

        # Convert histogram to set of operations that appear
        present_ops = set(op for op, count in histogram.items() if count > 0)

        for primitive, signature in self.PRIMITIVE_SIGNATURES.items():
            # Check if primitive signature is subset of present operations
            if signature.issubset(present_ops):
                detected.append(primitive)

        return detected

    def _detect_multisig(self, functions: List["Node"]) -> bool:
        """Detect if project uses multisig pattern."""
        # Look for signature-related functions
        multisig_indicators = ["confirm", "signature", "signer", "threshold", "quorum", "approval"]

        for fn in functions:
            fn_name = fn.label.lower()
            # Look for multisig indicators with access control
            for indicator in multisig_indicators:
                if indicator in fn_name:
                    # If it has access control, likely multisig
                    if fn.properties.get("has_access_gate", False):
                        return True

        return False

    def _detect_timelock(self, functions: List["Node"]) -> bool:
        """Detect if project uses timelock pattern."""
        timelock_indicators = ["timelock", "delay", "queue", "execute_after", "eta"]

        for fn in functions:
            fn_name = fn.label.lower()
            if any(indicator in fn_name for indicator in timelock_indicators):
                return True

        return False

    def _generate_embedding(self, histogram: Dict[str, int]) -> List[float]:
        """
        Generate normalized embedding vector from operation histogram.

        Uses fixed vocabulary of semantic operations to create
        consistent-dimensional embeddings for similarity comparison.

        Returns:
            Normalized vector of operation frequencies
        """
        # Build vector from vocabulary
        vector = []
        for op in self.operation_vocab:
            vector.append(histogram.get(op, 0))

        # Normalize (L2 normalization)
        magnitude = math.sqrt(sum(x * x for x in vector))
        if magnitude > 0:
            vector = [x / magnitude for x in vector]

        return vector


class ProjectDatabase:
    """
    Database of known project profiles for similarity search.

    Stores profiles of audited projects with known vulnerabilities
    for transfer learning.
    """

    def __init__(self):
        self.profiles: Dict[str, ProjectProfile] = {}

    def add_profile(self, profile: ProjectProfile):
        """Add project profile to database."""
        self.profiles[profile.project_id] = profile

    def find_similar(
        self,
        query_profile: ProjectProfile,
        top_k: int = 5,
        min_similarity: float = 0.5,
    ) -> List[tuple[ProjectProfile, float]]:
        """
        Find most similar projects to query.

        Args:
            query_profile: Profile to match against
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of (profile, similarity_score) tuples, sorted by similarity
        """
        similarities = []

        for profile in self.profiles.values():
            if profile.project_id == query_profile.project_id:
                continue

            similarity = query_profile.similarity_to(profile)

            if similarity >= min_similarity:
                similarities.append((profile, similarity))

        # Sort by similarity (descending) and take top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def get_by_protocol_type(self, protocol_type: str) -> List[ProjectProfile]:
        """Get all projects of a specific protocol type."""
        return [
            p for p in self.profiles.values()
            if p.protocol_type == protocol_type
        ]

    def get_by_primitive(self, primitive: str) -> List[ProjectProfile]:
        """Get all projects using a specific DeFi primitive."""
        return [
            p for p in self.profiles.values()
            if primitive in p.primitives_used
        ]
