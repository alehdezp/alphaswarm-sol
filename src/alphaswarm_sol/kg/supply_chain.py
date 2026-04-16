"""Phase 15: Supply-Chain Layer.

This module provides functionality for analyzing external dependencies
in smart contracts, including trust assessment and impact analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node, Edge


class TrustLevel(str, Enum):
    """Trust levels for external dependencies."""
    TRUSTED = "trusted"           # Known safe contracts (e.g., verified Chainlink)
    SEMI_TRUSTED = "semi-trusted" # Partially verified or constrained
    UNTRUSTED = "untrusted"       # Unknown or user-controlled


class DependencyType(str, Enum):
    """Types of external dependencies."""
    ORACLE = "oracle"             # Price feeds, data providers
    TOKEN = "token"               # ERC20, ERC721, etc.
    DEX = "dex"                   # DEX routers, pools
    LENDING = "lending"           # Lending protocols
    BRIDGE = "bridge"             # Cross-chain bridges
    GOVERNANCE = "governance"     # Governance contracts
    EXTERNAL_CALL = "external_call"  # Generic external call
    CALLBACK = "callback"         # Callbacks from external contracts


# Known trusted interfaces and implementations
KNOWN_TRUSTED_INTERFACES: Dict[str, List[str]] = {
    "AggregatorV3Interface": ["Chainlink price feeds"],
    "IERC20": ["Standard token interface"],
    "IUniswapV2Router02": ["Uniswap V2 router"],
    "IUniswapV3Pool": ["Uniswap V3 pool"],
    "IERC721": ["Standard NFT interface"],
    "IERC1155": ["Multi-token standard"],
}

# Interfaces with callback risk
CALLBACK_RISK_INTERFACES = {
    "IERC721Receiver",
    "IERC1155Receiver",
    "IFlashLoanRecipient",
    "IUniswapV3FlashCallback",
    "IUniswapV2Callee",
    "IFlashLoanSimpleReceiver",
}


@dataclass
class ExternalDependency:
    """External dependency on another contract or interface.

    Attributes:
        id: Unique identifier
        interface: Interface name or type being called
        target_address: Target address (if known/constant)
        known_implementations: List of known implementations
        trust_level: Trust level assessment
        dependency_type: Type of dependency
        callback_risk: Whether dependency can call back
        state_assumptions: State assumptions made about the external contract
        compromise_impact: Potential impact if dependency is compromised
        call_sites: Function nodes that call this dependency
        evidence: Evidence for the analysis
    """
    id: str
    interface: str
    target_address: Optional[str] = None
    known_implementations: List[str] = field(default_factory=list)
    trust_level: TrustLevel = TrustLevel.UNTRUSTED
    dependency_type: DependencyType = DependencyType.EXTERNAL_CALL
    callback_risk: bool = False
    state_assumptions: List[str] = field(default_factory=list)
    compromise_impact: List[str] = field(default_factory=list)
    call_sites: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "interface": self.interface,
            "target_address": self.target_address,
            "known_implementations": self.known_implementations,
            "trust_level": self.trust_level.value,
            "dependency_type": self.dependency_type.value,
            "callback_risk": self.callback_risk,
            "state_assumptions": self.state_assumptions,
            "compromise_impact": self.compromise_impact,
            "call_sites": self.call_sites,
            "evidence": self.evidence,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ExternalDependency":
        """Create from dictionary."""
        return ExternalDependency(
            id=data.get("id", ""),
            interface=data.get("interface", ""),
            target_address=data.get("target_address"),
            known_implementations=data.get("known_implementations", []),
            trust_level=TrustLevel(data.get("trust_level", "untrusted")),
            dependency_type=DependencyType(data.get("dependency_type", "external_call")),
            callback_risk=data.get("callback_risk", False),
            state_assumptions=data.get("state_assumptions", []),
            compromise_impact=data.get("compromise_impact", []),
            call_sites=data.get("call_sites", []),
            evidence=data.get("evidence", []),
        )


@dataclass
class DependencyAnalysis:
    """Analysis results for a contract's external dependencies.

    Attributes:
        contract_id: ID of the analyzed contract
        dependencies: List of external dependencies
        total_dependencies: Total count
        untrusted_count: Count of untrusted dependencies
        callback_risk_count: Count of dependencies with callback risk
        high_impact_count: Count of dependencies with high compromise impact
    """
    contract_id: str
    dependencies: List[ExternalDependency] = field(default_factory=list)

    @property
    def total_dependencies(self) -> int:
        return len(self.dependencies)

    @property
    def untrusted_count(self) -> int:
        return sum(1 for d in self.dependencies if d.trust_level == TrustLevel.UNTRUSTED)

    @property
    def callback_risk_count(self) -> int:
        return sum(1 for d in self.dependencies if d.callback_risk)

    @property
    def high_impact_count(self) -> int:
        return sum(1 for d in self.dependencies if len(d.compromise_impact) >= 2)

    def get_by_type(self, dep_type: DependencyType) -> List[ExternalDependency]:
        """Get dependencies by type."""
        return [d for d in self.dependencies if d.dependency_type == dep_type]

    def get_untrusted(self) -> List[ExternalDependency]:
        """Get untrusted dependencies."""
        return [d for d in self.dependencies if d.trust_level == TrustLevel.UNTRUSTED]

    def get_with_callback_risk(self) -> List[ExternalDependency]:
        """Get dependencies with callback risk."""
        return [d for d in self.dependencies if d.callback_risk]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "contract_id": self.contract_id,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "total_dependencies": self.total_dependencies,
            "untrusted_count": self.untrusted_count,
            "callback_risk_count": self.callback_risk_count,
            "high_impact_count": self.high_impact_count,
        }


class DependencyAnalyzer:
    """Analyzes external dependencies in a knowledge graph.

    Extracts and assesses external contract dependencies from function nodes.
    """

    def __init__(self, graph: KnowledgeGraph):
        """Initialize analyzer with knowledge graph.

        Args:
            graph: Knowledge graph to analyze
        """
        self.graph = graph

    def analyze_contract(self, contract_id: str) -> DependencyAnalysis:
        """Analyze dependencies for a specific contract.

        Args:
            contract_id: ID of the contract node

        Returns:
            DependencyAnalysis with all found dependencies
        """
        dependencies: List[ExternalDependency] = []
        seen_interfaces: Set[str] = set()

        # Get contract label if it's a contract node
        contract_label = None
        contract_node = self.graph.nodes.get(contract_id)
        if contract_node and contract_node.type == "Contract":
            contract_label = contract_node.label

        # Find all function nodes in the contract
        for node in self.graph.nodes.values():
            if node.type != "Function":
                continue

            # Check if function is in this contract
            contract_name = node.properties.get("contract_name", "")
            # Match by contract_id, contract_name, or contract_label
            if contract_id not in (node.id, contract_name) and contract_name != contract_label:
                continue

            # Extract dependencies from this function
            func_deps = self._extract_function_dependencies(node)
            for dep in func_deps:
                if dep.interface not in seen_interfaces:
                    dependencies.append(dep)
                    seen_interfaces.add(dep.interface)
                else:
                    # Add call site to existing dependency
                    for existing in dependencies:
                        if existing.interface == dep.interface:
                            existing.call_sites.extend(dep.call_sites)
                            break

        return DependencyAnalysis(
            contract_id=contract_id,
            dependencies=dependencies,
        )

    def analyze_all_contracts(self) -> Dict[str, DependencyAnalysis]:
        """Analyze dependencies for all contracts in graph.

        Returns:
            Dict mapping contract ID to DependencyAnalysis
        """
        results: Dict[str, DependencyAnalysis] = {}
        contract_ids: Set[str] = set()

        # Find all contract nodes
        for node in self.graph.nodes.values():
            if node.type == "Contract":
                contract_ids.add(node.id)

        for contract_id in contract_ids:
            results[contract_id] = self.analyze_contract(contract_id)

        return results

    def _extract_function_dependencies(self, func_node: Node) -> List[ExternalDependency]:
        """Extract dependencies from a function node.

        Args:
            func_node: Function node to analyze

        Returns:
            List of dependencies found in the function
        """
        dependencies: List[ExternalDependency] = []

        # Check for external calls
        external_calls = func_node.properties.get("external_calls", []) or []
        calls_external = func_node.properties.get("calls_external", False)
        uses_delegatecall = func_node.properties.get("uses_delegatecall", False)

        # Check for oracle reads
        reads_oracle = func_node.properties.get("reads_oracle_price", False)
        if reads_oracle:
            dep = ExternalDependency(
                id=f"{func_node.id}_oracle",
                interface="AggregatorV3Interface",
                known_implementations=["Chainlink price feeds"],
                trust_level=TrustLevel.SEMI_TRUSTED,
                dependency_type=DependencyType.ORACLE,
                callback_risk=False,
                state_assumptions=["Price is not stale", "Oracle is not manipulated"],
                compromise_impact=["Incorrect pricing", "Arbitrage opportunities"],
                call_sites=[func_node.id],
                evidence=["reads_oracle_price=True"],
            )
            dependencies.append(dep)

        # Check for token transfers
        uses_erc20 = func_node.properties.get("uses_erc20_transfer", False)
        if uses_erc20:
            dep = ExternalDependency(
                id=f"{func_node.id}_token",
                interface="IERC20",
                known_implementations=["Standard ERC20"],
                trust_level=TrustLevel.SEMI_TRUSTED,
                dependency_type=DependencyType.TOKEN,
                callback_risk=False,  # Standard ERC20 has no callbacks
                state_assumptions=["Token follows ERC20 standard"],
                compromise_impact=["Token theft", "Approval manipulation"],
                call_sites=[func_node.id],
                evidence=["uses_erc20_transfer=True"],
            )
            dependencies.append(dep)

        # Check for swap-like functions (DEX dependency)
        swap_like = func_node.properties.get("swap_like", False)
        if swap_like:
            dep = ExternalDependency(
                id=f"{func_node.id}_dex",
                interface="IDEXRouter",
                known_implementations=["Uniswap", "SushiSwap"],
                trust_level=TrustLevel.SEMI_TRUSTED,
                dependency_type=DependencyType.DEX,
                callback_risk=True,  # DEX swaps can have callbacks
                state_assumptions=["DEX liquidity is sufficient", "Slippage is acceptable"],
                compromise_impact=["Sandwich attacks", "Front-running", "MEV extraction"],
                call_sites=[func_node.id],
                evidence=["swap_like=True"],
            )
            dependencies.append(dep)

        # Check for delegatecall (high risk)
        if uses_delegatecall:
            dep = ExternalDependency(
                id=f"{func_node.id}_delegatecall",
                interface="IImplementation",
                known_implementations=[],
                trust_level=TrustLevel.UNTRUSTED,
                dependency_type=DependencyType.EXTERNAL_CALL,
                callback_risk=True,
                state_assumptions=["Implementation is not malicious"],
                compromise_impact=["Full contract takeover", "Storage corruption", "Funds theft"],
                call_sites=[func_node.id],
                evidence=["uses_delegatecall=True"],
            )
            dependencies.append(dep)

        # Check for generic external calls
        if calls_external and not reads_oracle and not uses_erc20 and not swap_like:
            dep = ExternalDependency(
                id=f"{func_node.id}_external",
                interface="IExternal",
                known_implementations=[],
                trust_level=self._assess_trust_level(func_node),
                dependency_type=DependencyType.EXTERNAL_CALL,
                callback_risk=self._can_callback(func_node),
                state_assumptions=["External contract behaves correctly"],
                compromise_impact=["Unexpected behavior", "Reentrancy"],
                call_sites=[func_node.id],
                evidence=["calls_external=True"],
            )
            dependencies.append(dep)

        # Check for flash loan receivers
        is_flashloan = "flash" in func_node.label.lower()
        if is_flashloan:
            dep = ExternalDependency(
                id=f"{func_node.id}_flashloan",
                interface="IFlashLoanReceiver",
                known_implementations=["Aave", "dYdX"],
                trust_level=TrustLevel.SEMI_TRUSTED,
                dependency_type=DependencyType.CALLBACK,
                callback_risk=True,
                state_assumptions=["Loan will be repaid"],
                compromise_impact=["Flash loan attacks", "Arbitrage exploitation"],
                call_sites=[func_node.id],
                evidence=["flash loan pattern detected"],
            )
            dependencies.append(dep)

        return dependencies

    def _assess_trust_level(self, func_node: Node) -> TrustLevel:
        """Assess trust level based on function properties.

        Args:
            func_node: Function node to assess

        Returns:
            Assessed trust level
        """
        # Check for access control
        has_access_gate = func_node.properties.get("has_access_gate", False)
        calls_untrusted = func_node.properties.get("calls_untrusted", False)

        if calls_untrusted:
            return TrustLevel.UNTRUSTED
        elif has_access_gate:
            return TrustLevel.SEMI_TRUSTED
        else:
            return TrustLevel.UNTRUSTED

    def _can_callback(self, func_node: Node) -> bool:
        """Check if function can receive callbacks.

        Args:
            func_node: Function node to check

        Returns:
            True if callbacks are possible
        """
        # Check for reentrancy indicators
        has_guard = func_node.properties.get("has_reentrancy_guard", False)
        state_after_call = func_node.properties.get("state_write_after_external_call", False)
        transfers_value = func_node.properties.get("transfers_value_out", False)

        # If no guard and transfers value, callbacks are possible
        if not has_guard and (state_after_call or transfers_value):
            return True

        return False


def analyze_external_dependencies(
    graph: KnowledgeGraph,
    contract_id: Optional[str] = None,
) -> DependencyAnalysis:
    """Analyze external dependencies in a knowledge graph.

    Convenience function for quick dependency analysis.

    Args:
        graph: Knowledge graph to analyze
        contract_id: Optional specific contract to analyze

    Returns:
        DependencyAnalysis results
    """
    analyzer = DependencyAnalyzer(graph)

    if contract_id:
        return analyzer.analyze_contract(contract_id)

    # Analyze all contracts and merge results
    all_results = analyzer.analyze_all_contracts()
    merged_deps: List[ExternalDependency] = []
    seen: Set[str] = set()

    for analysis in all_results.values():
        for dep in analysis.dependencies:
            if dep.id not in seen:
                merged_deps.append(dep)
                seen.add(dep.id)

    return DependencyAnalysis(
        contract_id="all",
        dependencies=merged_deps,
    )


def add_dependency_nodes_to_graph(
    graph: KnowledgeGraph,
    analysis: DependencyAnalysis,
) -> None:
    """Add ExternalDependency nodes and edges to graph.

    Args:
        graph: Knowledge graph to update
        analysis: Dependency analysis results
    """
    for dep in analysis.dependencies:
        # Create dependency node
        node = Node(
            id=f"dep_{dep.id}",
            label=dep.interface,
            type="ExternalDependency",
            properties={
                "interface": dep.interface,
                "target_address": dep.target_address,
                "trust_level": dep.trust_level.value,
                "dependency_type": dep.dependency_type.value,
                "callback_risk": dep.callback_risk,
                "state_assumptions": dep.state_assumptions,
                "compromise_impact": dep.compromise_impact,
                "known_implementations": dep.known_implementations,
            },
        )
        graph.nodes[node.id] = node

        # Create edges from call sites
        for call_site in dep.call_sites:
            edge = Edge(
                id=f"depends_{call_site}_{dep.id}",
                source=call_site,
                target=node.id,
                type="DEPENDS_ON",
                properties={
                    "trust_level": dep.trust_level.value,
                    "callback_risk": dep.callback_risk,
                },
            )
            graph.edges[edge.id] = edge


__all__ = [
    "TrustLevel",
    "DependencyType",
    "ExternalDependency",
    "DependencyAnalysis",
    "DependencyAnalyzer",
    "analyze_external_dependencies",
    "add_dependency_nodes_to_graph",
    "KNOWN_TRUSTED_INTERFACES",
    "CALLBACK_RISK_INTERFACES",
]
