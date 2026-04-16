"""DeFi protocol dependency graph for CPCRM.

Per 05.11-10: Build a protocol dependency graph that models DeFi ecosystem
interactions with centrality analysis and critical path detection.

Key Features:
- ProtocolNode: Protocol metadata (TVL, category, chains, governance)
- DependencyEdge: Dependency relationships with criticality and cascade impact
- ProtocolDependencyGraph: Graph with centrality computation and cycle detection
- Seed data for major DeFi protocols

Usage:
    from alphaswarm_sol.economics.composability.protocol_graph import (
        ProtocolNode,
        ProtocolCategory,
        DependencyEdge,
        DependencyType,
        ProtocolDependencyGraph,
    )

    # Create graph and add protocols
    graph = ProtocolDependencyGraph()
    graph.add_protocol(ProtocolNode(
        protocol_id="aave-v3",
        tvl=Decimal("10_000_000_000"),
        category=ProtocolCategory.LENDING,
        chains=["ethereum", "arbitrum"],
    ))

    # Add dependency
    graph.add_dependency(DependencyEdge(
        source="aave-v3",
        target="chainlink",
        dependency_type=DependencyType.ORACLE,
        criticality=9.0,
    ))

    # Compute centrality
    centrality = graph.compute_centrality()
    print(f"Chainlink centrality: {centrality['chainlink']:.2f}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.context.passports import ContractPassport


class ProtocolCategory(Enum):
    """Categories of DeFi protocols.

    Used to classify protocols by their primary function in the ecosystem.
    """

    LENDING = "lending"  # Lending/borrowing (Aave, Compound)
    DEX = "dex"  # Decentralized exchanges (Uniswap, Curve)
    ORACLE = "oracle"  # Price oracles (Chainlink, Pyth)
    BRIDGE = "bridge"  # Cross-chain bridges (Wormhole, LayerZero)
    DERIVATIVE = "derivative"  # Derivatives/perps (dYdX, GMX)
    STAKING = "staking"  # Liquid staking (Lido, Rocket Pool)
    YIELD = "yield"  # Yield aggregators (Yearn, Convex)
    GOVERNANCE = "governance"  # DAO governance (MakerDAO, Curve DAO)
    STABLECOIN = "stablecoin"  # Stablecoin issuers (MakerDAO, Frax)
    OTHER = "other"


class GovernanceType(Enum):
    """Types of protocol governance."""

    TIMELOCK = "timelock"  # Timelock-controlled
    MULTISIG = "multisig"  # Multisig-controlled
    DAO = "dao"  # DAO governance (token voting)
    EOA = "eoa"  # Single EOA (high risk)
    IMMUTABLE = "immutable"  # No admin (immutable)


@dataclass
class GovernanceInfo:
    """Governance configuration for a protocol.

    Attributes:
        governance_type: Type of governance
        timelock_seconds: Timelock delay (if applicable)
        multisig_threshold: Required signatures (if multisig)
        total_signers: Total multisig signers (if multisig)
        governance_token: Governance token address (if DAO)
        quorum_percentage: Required quorum for votes (if DAO)
    """

    governance_type: GovernanceType
    timelock_seconds: int = 0
    multisig_threshold: int = 0
    total_signers: int = 0
    governance_token: str = ""
    quorum_percentage: float = 0.0

    @property
    def has_timelock(self) -> bool:
        """Whether protocol has a timelock."""
        return self.timelock_seconds > 0 or self.governance_type == GovernanceType.TIMELOCK

    @property
    def is_centralized(self) -> bool:
        """Whether governance is centralized (EOA or single signer)."""
        if self.governance_type == GovernanceType.EOA:
            return True
        if self.governance_type == GovernanceType.MULTISIG and self.multisig_threshold <= 1:
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "governance_type": self.governance_type.value,
            "timelock_seconds": self.timelock_seconds,
            "multisig_threshold": self.multisig_threshold,
            "total_signers": self.total_signers,
            "governance_token": self.governance_token,
            "quorum_percentage": self.quorum_percentage,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GovernanceInfo":
        """Create GovernanceInfo from dictionary."""
        gov_type = data.get("governance_type", "timelock")
        if isinstance(gov_type, str):
            gov_type = GovernanceType(gov_type)

        return cls(
            governance_type=gov_type,
            timelock_seconds=int(data.get("timelock_seconds", 0)),
            multisig_threshold=int(data.get("multisig_threshold", 0)),
            total_signers=int(data.get("total_signers", 0)),
            governance_token=str(data.get("governance_token", "")),
            quorum_percentage=float(data.get("quorum_percentage", 0.0)),
        )


@dataclass
class ProtocolNode:
    """A DeFi protocol node in the dependency graph.

    Per 05.11-10: Represents a protocol with its TVL, category, chains,
    and governance information.

    Attributes:
        protocol_id: Unique identifier (e.g., "aave-v3", "compound-v3")
        tvl: Total value locked in USD
        category: Protocol category (LENDING, DEX, ORACLE, etc.)
        chains: List of deployed chains
        governance: Governance configuration
        description: Human-readable description
        website: Protocol website URL
        contracts: List of main contract addresses
    """

    protocol_id: str
    tvl: Decimal = Decimal("0")
    category: ProtocolCategory = ProtocolCategory.OTHER
    chains: List[str] = field(default_factory=list)
    governance: GovernanceInfo = field(default_factory=lambda: GovernanceInfo(GovernanceType.TIMELOCK))
    description: str = ""
    website: str = ""
    contracts: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate and normalize protocol node."""
        if not self.protocol_id:
            raise ValueError("protocol_id is required")
        self.protocol_id = self.protocol_id.lower()
        if self.tvl < 0:
            raise ValueError(f"tvl must be non-negative, got {self.tvl}")

    @property
    def is_high_tvl(self) -> bool:
        """Whether this protocol has high TVL (>= $100M)."""
        return self.tvl >= Decimal("100_000_000")

    @property
    def is_infrastructure(self) -> bool:
        """Whether this is core infrastructure (oracle/bridge)."""
        return self.category in (ProtocolCategory.ORACLE, ProtocolCategory.BRIDGE)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "protocol_id": self.protocol_id,
            "tvl": str(self.tvl),
            "category": self.category.value,
            "chains": self.chains,
            "governance": self.governance.to_dict(),
            "description": self.description,
            "website": self.website,
            "contracts": self.contracts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProtocolNode":
        """Create ProtocolNode from dictionary."""
        category = data.get("category", "other")
        if isinstance(category, str):
            category = ProtocolCategory(category)

        return cls(
            protocol_id=str(data.get("protocol_id", "")),
            tvl=Decimal(str(data.get("tvl", "0"))),
            category=category,
            chains=list(data.get("chains", [])),
            governance=GovernanceInfo.from_dict(data.get("governance", {})),
            description=str(data.get("description", "")),
            website=str(data.get("website", "")),
            contracts=list(data.get("contracts", [])),
        )


class DependencyType(Enum):
    """Types of protocol dependencies.

    Per 05.11-10: Categorize how protocols depend on each other.
    """

    ORACLE = "oracle"  # Price oracle dependency
    LIQUIDITY = "liquidity"  # Liquidity dependency (pools, DEXs)
    COLLATERAL = "collateral"  # Collateral asset dependency
    GOVERNANCE = "governance"  # Governance dependency
    BRIDGE = "bridge"  # Cross-chain bridge dependency


@dataclass
class DependencyEdge:
    """A dependency edge between protocols.

    Per 05.11-10: Represents a dependency relationship with criticality
    and cascade impact estimation.

    Attributes:
        source: Dependent protocol ID (the one that depends on target)
        target: Dependency protocol ID (the one being depended upon)
        dependency_type: Type of dependency (ORACLE, LIQUIDITY, etc.)
        criticality: Criticality score 1-10 (10 = critical)
        failure_propagation_time: Time for failure to propagate
        tvl_at_risk: TVL at risk if dependency fails
        description: Human-readable description
        affected_functions: Functions affected by this dependency
    """

    source: str
    target: str
    dependency_type: DependencyType
    criticality: float = 5.0
    failure_propagation_time: timedelta = field(default_factory=lambda: timedelta(hours=1))
    tvl_at_risk: Decimal = Decimal("0")
    description: str = ""
    affected_functions: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate and normalize dependency edge."""
        self.source = self.source.lower()
        self.target = self.target.lower()

        if not 1.0 <= self.criticality <= 10.0:
            raise ValueError(f"criticality must be 1-10, got {self.criticality}")

        if self.source == self.target:
            raise ValueError("source and target cannot be the same")

    @property
    def is_critical(self) -> bool:
        """Whether this dependency is critical (>= 8)."""
        return self.criticality >= 8.0

    @property
    def is_oracle_dependency(self) -> bool:
        """Whether this is an oracle dependency."""
        return self.dependency_type == DependencyType.ORACLE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "source": self.source,
            "target": self.target,
            "dependency_type": self.dependency_type.value,
            "criticality": self.criticality,
            "failure_propagation_time_seconds": int(self.failure_propagation_time.total_seconds()),
            "tvl_at_risk": str(self.tvl_at_risk),
            "description": self.description,
            "affected_functions": self.affected_functions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DependencyEdge":
        """Create DependencyEdge from dictionary."""
        dep_type = data.get("dependency_type", "oracle")
        if isinstance(dep_type, str):
            dep_type = DependencyType(dep_type)

        return cls(
            source=str(data.get("source", "")),
            target=str(data.get("target", "")),
            dependency_type=dep_type,
            criticality=float(data.get("criticality", 5.0)),
            failure_propagation_time=timedelta(
                seconds=int(data.get("failure_propagation_time_seconds", 3600))
            ),
            tvl_at_risk=Decimal(str(data.get("tvl_at_risk", "0"))),
            description=str(data.get("description", "")),
            affected_functions=list(data.get("affected_functions", [])),
        )


@dataclass
class CriticalPath:
    """A critical failure path through the dependency graph.

    Attributes:
        path: Ordered list of protocol IDs in the path
        total_criticality: Sum of edge criticalities along path
        total_tvl_at_risk: Total TVL at risk along the path
        bottleneck: Protocol with highest centrality in path
    """

    path: List[str]
    total_criticality: float = 0.0
    total_tvl_at_risk: Decimal = Decimal("0")
    bottleneck: str = ""

    @property
    def length(self) -> int:
        """Path length (number of protocols)."""
        return len(self.path)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "path": self.path,
            "total_criticality": self.total_criticality,
            "total_tvl_at_risk": str(self.total_tvl_at_risk),
            "bottleneck": self.bottleneck,
        }


@dataclass
class Cycle:
    """A circular dependency in the graph.

    Attributes:
        protocols: Protocols involved in the cycle
        description: Human-readable description of the cycle
    """

    protocols: List[str]
    description: str = ""

    @property
    def length(self) -> int:
        """Cycle length."""
        return len(self.protocols)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "protocols": self.protocols,
            "length": self.length,
            "description": self.description,
        }


class ProtocolDependencyGraph:
    """DeFi protocol dependency graph.

    Per 05.11-10: Models the DeFi ecosystem as a directed graph where nodes
    are protocols and edges are dependencies. Provides centrality analysis,
    critical path detection, and cycle detection.

    Usage:
        graph = ProtocolDependencyGraph()

        # Add protocols
        graph.add_protocol(ProtocolNode("aave-v3", tvl=Decimal("10B")))
        graph.add_protocol(ProtocolNode("chainlink", tvl=Decimal("0")))

        # Add dependency
        graph.add_dependency(DependencyEdge(
            source="aave-v3",
            target="chainlink",
            dependency_type=DependencyType.ORACLE,
            criticality=9.0
        ))

        # Analyze
        centrality = graph.compute_centrality()
        paths = graph.find_critical_paths()
    """

    # Seed data for major DeFi protocols
    SEED_PROTOCOLS: Dict[str, Dict[str, Any]] = {
        "chainlink": {
            "category": "oracle",
            "tvl": "0",
            "chains": ["ethereum", "arbitrum", "optimism", "polygon", "avalanche", "bsc"],
            "description": "Decentralized oracle network providing price feeds",
        },
        "aave-v3": {
            "category": "lending",
            "tvl": "12000000000",
            "chains": ["ethereum", "arbitrum", "optimism", "polygon", "avalanche"],
            "description": "Decentralized non-custodial liquidity protocol",
        },
        "compound-v3": {
            "category": "lending",
            "tvl": "2500000000",
            "chains": ["ethereum", "arbitrum", "polygon", "base"],
            "description": "Compound III money market protocol",
        },
        "uniswap-v3": {
            "category": "dex",
            "tvl": "5000000000",
            "chains": ["ethereum", "arbitrum", "optimism", "polygon", "base"],
            "description": "Concentrated liquidity DEX",
        },
        "curve": {
            "category": "dex",
            "tvl": "2000000000",
            "chains": ["ethereum", "arbitrum", "polygon"],
            "description": "Stablecoin-focused AMM",
        },
        "lido": {
            "category": "staking",
            "tvl": "30000000000",
            "chains": ["ethereum", "polygon"],
            "description": "Liquid staking protocol for Ethereum",
        },
        "makerdao": {
            "category": "stablecoin",
            "tvl": "8000000000",
            "chains": ["ethereum"],
            "description": "Decentralized stablecoin (DAI) issuer",
        },
        "synthetix": {
            "category": "derivative",
            "tvl": "500000000",
            "chains": ["ethereum", "optimism"],
            "description": "Synthetic assets protocol",
        },
        "wormhole": {
            "category": "bridge",
            "tvl": "1000000000",
            "chains": ["ethereum", "solana", "arbitrum", "avalanche"],
            "description": "Cross-chain messaging and bridging protocol",
        },
        "layerzero": {
            "category": "bridge",
            "tvl": "500000000",
            "chains": ["ethereum", "arbitrum", "optimism", "polygon", "avalanche", "bsc"],
            "description": "Omnichain interoperability protocol",
        },
    }

    # Seed dependency data
    SEED_DEPENDENCIES: List[Dict[str, Any]] = [
        # Oracle dependencies on Chainlink
        {"source": "aave-v3", "target": "chainlink", "dependency_type": "oracle", "criticality": 9.0},
        {"source": "compound-v3", "target": "chainlink", "dependency_type": "oracle", "criticality": 9.0},
        {"source": "makerdao", "target": "chainlink", "dependency_type": "oracle", "criticality": 8.0},
        {"source": "synthetix", "target": "chainlink", "dependency_type": "oracle", "criticality": 9.0},
        # Liquidity dependencies
        {"source": "aave-v3", "target": "uniswap-v3", "dependency_type": "liquidity", "criticality": 6.0},
        {"source": "compound-v3", "target": "uniswap-v3", "dependency_type": "liquidity", "criticality": 6.0},
        # Collateral dependencies on stETH (Lido)
        {"source": "aave-v3", "target": "lido", "dependency_type": "collateral", "criticality": 8.0},
        {"source": "makerdao", "target": "lido", "dependency_type": "collateral", "criticality": 7.0},
        # Curve dependencies
        {"source": "curve", "target": "chainlink", "dependency_type": "oracle", "criticality": 7.0},
        # Cross-protocol liquidity
        {"source": "synthetix", "target": "curve", "dependency_type": "liquidity", "criticality": 7.0},
    ]

    def __init__(self) -> None:
        """Initialize empty protocol dependency graph."""
        self._protocols: Dict[str, ProtocolNode] = {}
        self._dependencies: List[DependencyEdge] = []
        # Adjacency lists for efficient traversal
        self._outgoing: Dict[str, List[DependencyEdge]] = {}  # source -> edges
        self._incoming: Dict[str, List[DependencyEdge]] = {}  # target -> edges

    def add_protocol(self, node: ProtocolNode) -> None:
        """Add a protocol to the graph.

        Args:
            node: ProtocolNode to add
        """
        self._protocols[node.protocol_id] = node
        if node.protocol_id not in self._outgoing:
            self._outgoing[node.protocol_id] = []
        if node.protocol_id not in self._incoming:
            self._incoming[node.protocol_id] = []

    def add_dependency(self, edge: DependencyEdge) -> None:
        """Add a dependency edge to the graph.

        Args:
            edge: DependencyEdge to add

        Raises:
            ValueError: If source or target protocol not in graph
        """
        # Auto-add protocols if not present
        if edge.source not in self._protocols:
            self.add_protocol(ProtocolNode(protocol_id=edge.source))
        if edge.target not in self._protocols:
            self.add_protocol(ProtocolNode(protocol_id=edge.target))

        self._dependencies.append(edge)
        self._outgoing[edge.source].append(edge)
        self._incoming[edge.target].append(edge)

    def get_protocol(self, protocol_id: str) -> Optional[ProtocolNode]:
        """Get a protocol by ID.

        Args:
            protocol_id: Protocol identifier

        Returns:
            ProtocolNode if found, None otherwise
        """
        return self._protocols.get(protocol_id.lower())

    def get_dependencies(self, protocol_id: str) -> List[DependencyEdge]:
        """Get dependencies OF a protocol (what it depends on).

        Args:
            protocol_id: Protocol identifier

        Returns:
            List of dependency edges where protocol is the source
        """
        return self._outgoing.get(protocol_id.lower(), [])

    def get_dependents(self, protocol_id: str) -> List[DependencyEdge]:
        """Get protocols that depend ON this protocol.

        Args:
            protocol_id: Protocol identifier

        Returns:
            List of dependency edges where protocol is the target
        """
        return self._incoming.get(protocol_id.lower(), [])

    def compute_centrality(self) -> Dict[str, float]:
        """Compute eigenvector centrality for all protocols.

        Uses power iteration to approximate eigenvector centrality.
        Higher centrality = more important in the network.

        Returns:
            Dict mapping protocol_id to centrality score (0-1)
        """
        protocols = list(self._protocols.keys())
        n = len(protocols)

        if n == 0:
            return {}

        if n == 1:
            return {protocols[0]: 1.0}

        # Build adjacency matrix (for undirected version)
        idx = {p: i for i, p in enumerate(protocols)}
        adj = [[0.0] * n for _ in range(n)]

        for edge in self._dependencies:
            i, j = idx[edge.source], idx[edge.target]
            # Weight by criticality
            weight = edge.criticality / 10.0
            adj[i][j] += weight
            adj[j][i] += weight  # Undirected for centrality

        # Power iteration for eigenvector centrality
        scores = [1.0 / n] * n
        for _ in range(100):  # Max iterations
            new_scores = [0.0] * n
            for i in range(n):
                for j in range(n):
                    new_scores[i] += adj[i][j] * scores[j]

            # Normalize
            norm = sum(s * s for s in new_scores) ** 0.5
            if norm > 0:
                new_scores = [s / norm for s in new_scores]

            # Check convergence
            diff = sum(abs(new_scores[i] - scores[i]) for i in range(n))
            scores = new_scores
            if diff < 1e-6:
                break

        # Normalize to 0-1 range
        max_score = max(scores) if scores else 1.0
        if max_score > 0:
            scores = [s / max_score for s in scores]

        return {protocols[i]: scores[i] for i in range(n)}

    def find_critical_paths(self, min_criticality: float = 7.0) -> List[CriticalPath]:
        """Find high-impact failure chains.

        Identifies paths through the graph where cumulative criticality
        exceeds a threshold, indicating potential cascade failure paths.

        Args:
            min_criticality: Minimum edge criticality to include

        Returns:
            List of CriticalPath objects sorted by total criticality
        """
        paths: List[CriticalPath] = []
        centrality = self.compute_centrality()

        # Start from each protocol and find paths
        for start in self._protocols:
            for path in self._find_paths_from(start, min_criticality):
                if len(path) >= 2:
                    # Calculate path metrics
                    total_crit = 0.0
                    total_tvl = Decimal("0")

                    for i in range(len(path) - 1):
                        edges = [e for e in self._outgoing.get(path[i], [])
                                 if e.target == path[i + 1] and e.criticality >= min_criticality]
                        if edges:
                            total_crit += edges[0].criticality
                            total_tvl += edges[0].tvl_at_risk

                    # Find bottleneck (highest centrality in path)
                    bottleneck = max(path, key=lambda p: centrality.get(p, 0))

                    paths.append(CriticalPath(
                        path=path,
                        total_criticality=total_crit,
                        total_tvl_at_risk=total_tvl,
                        bottleneck=bottleneck,
                    ))

        # Sort by criticality descending
        paths.sort(key=lambda p: p.total_criticality, reverse=True)
        return paths[:20]  # Return top 20 paths

    def _find_paths_from(
        self,
        start: str,
        min_criticality: float,
        max_depth: int = 5,
    ) -> List[List[str]]:
        """Find all paths from a starting protocol.

        Args:
            start: Starting protocol ID
            min_criticality: Minimum edge criticality
            max_depth: Maximum path length

        Returns:
            List of paths (each path is a list of protocol IDs)
        """
        paths: List[List[str]] = []

        def dfs(current: str, path: List[str], visited: Set[str]) -> None:
            if len(path) > max_depth:
                return

            edges = [e for e in self._outgoing.get(current, [])
                     if e.criticality >= min_criticality and e.target not in visited]

            if not edges and len(path) > 1:
                paths.append(path.copy())
                return

            for edge in edges:
                path.append(edge.target)
                visited.add(edge.target)
                dfs(edge.target, path, visited)
                path.pop()
                visited.remove(edge.target)

            if len(path) > 1:
                paths.append(path.copy())

        dfs(start, [start], {start})
        return paths

    def detect_circular_dependencies(self) -> List[Cycle]:
        """Detect circular dependencies in the graph.

        Uses DFS-based cycle detection.

        Returns:
            List of Cycle objects
        """
        cycles: List[Cycle] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for edge in self._outgoing.get(node, []):
                target = edge.target
                if target not in visited:
                    dfs(target)
                elif target in rec_stack:
                    # Found cycle
                    cycle_start = path.index(target)
                    cycle_path = path[cycle_start:] + [target]
                    cycles.append(Cycle(
                        protocols=cycle_path,
                        description=f"Circular dependency: {' -> '.join(cycle_path)}",
                    ))

            path.pop()
            rec_stack.remove(node)

        for protocol in self._protocols:
            if protocol not in visited:
                dfs(protocol)

        return cycles

    def build_from_passports(self, passports: List["ContractPassport"]) -> "ProtocolDependencyGraph":
        """Build graph from contract passports.

        Per 05.11-10: Extract cross-protocol dependencies from passports
        and build the dependency graph.

        Args:
            passports: List of ContractPassport objects

        Returns:
            Self for chaining
        """
        for passport in passports:
            # Extract protocol ID from contract
            protocol_id = passport.contract_id.lower().split(".")[0]

            # Add protocol if not exists
            if protocol_id not in self._protocols:
                self.add_protocol(ProtocolNode(
                    protocol_id=protocol_id,
                    category=ProtocolCategory.OTHER,
                    description=passport.economic_purpose,
                ))

            # Add dependencies from passport
            for dep in passport.cross_protocol_dependencies:
                dep_type_map = {
                    "oracle": DependencyType.ORACLE,
                    "liquidity": DependencyType.LIQUIDITY,
                    "collateral": DependencyType.COLLATERAL,
                    "governance": DependencyType.GOVERNANCE,
                    "bridge": DependencyType.BRIDGE,
                }

                dep_type = dep_type_map.get(
                    dep.dependency_type.value,
                    DependencyType.LIQUIDITY,
                )

                self.add_dependency(DependencyEdge(
                    source=protocol_id,
                    target=dep.protocol_id.lower(),
                    dependency_type=dep_type,
                    criticality=float(dep.criticality),
                    description=dep.description,
                    affected_functions=dep.affected_functions,
                ))

        return self

    def load_seed_data(self) -> "ProtocolDependencyGraph":
        """Load seed data for major DeFi protocols.

        Per 05.11-10: Provides seed data for 10+ major protocols
        including Chainlink, Aave, Compound, Uniswap, Curve, Lido, etc.

        Returns:
            Self for chaining
        """
        # Add seed protocols
        for protocol_id, data in self.SEED_PROTOCOLS.items():
            category = data.get("category", "other")
            if isinstance(category, str):
                category = ProtocolCategory(category)

            self.add_protocol(ProtocolNode(
                protocol_id=protocol_id,
                tvl=Decimal(data.get("tvl", "0")),
                category=category,
                chains=data.get("chains", []),
                description=data.get("description", ""),
            ))

        # Add seed dependencies
        for dep_data in self.SEED_DEPENDENCIES:
            dep_type = dep_data.get("dependency_type", "liquidity")
            if isinstance(dep_type, str):
                dep_type = DependencyType(dep_type)

            self.add_dependency(DependencyEdge(
                source=dep_data["source"],
                target=dep_data["target"],
                dependency_type=dep_type,
                criticality=dep_data.get("criticality", 5.0),
            ))

        return self

    @property
    def protocol_count(self) -> int:
        """Number of protocols in the graph."""
        return len(self._protocols)

    @property
    def dependency_count(self) -> int:
        """Number of dependencies in the graph."""
        return len(self._dependencies)

    @property
    def protocols(self) -> List[ProtocolNode]:
        """List of all protocols."""
        return list(self._protocols.values())

    @property
    def dependencies(self) -> List[DependencyEdge]:
        """List of all dependencies."""
        return self._dependencies.copy()

    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary for serialization."""
        return {
            "protocols": {pid: p.to_dict() for pid, p in self._protocols.items()},
            "dependencies": [d.to_dict() for d in self._dependencies],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProtocolDependencyGraph":
        """Create ProtocolDependencyGraph from dictionary."""
        graph = cls()

        for protocol_data in data.get("protocols", {}).values():
            graph.add_protocol(ProtocolNode.from_dict(protocol_data))

        for dep_data in data.get("dependencies", []):
            graph.add_dependency(DependencyEdge.from_dict(dep_data))

        return graph


# =============================================================================
# Module Exports
# =============================================================================


__all__ = [
    "ProtocolCategory",
    "GovernanceType",
    "GovernanceInfo",
    "ProtocolNode",
    "DependencyType",
    "DependencyEdge",
    "CriticalPath",
    "Cycle",
    "ProtocolDependencyGraph",
]
