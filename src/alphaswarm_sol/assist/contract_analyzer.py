"""Contract analyzer for query suggestion.

Analyzes a knowledge graph to extract security-relevant characteristics
that inform which queries are likely to find vulnerabilities.
"""

from dataclasses import dataclass
from typing import List
from ..kg.schema import KnowledgeGraph


@dataclass
class ContractAnalysis:
    """Security-relevant characteristics extracted from a contract."""

    # Function counts
    total_functions: int
    external_functions: int
    public_functions: int
    internal_functions: int
    private_functions: int

    # State analysis
    total_state_vars: int
    privileged_state_vars: int  # owner, admin, implementation, etc.

    # Security features
    has_access_control: bool
    has_reentrancy_guards: bool
    has_pause_mechanism: bool
    has_upgrade_mechanism: bool

    # Call patterns
    has_external_calls: bool
    has_delegatecalls: bool
    has_low_level_calls: bool

    # DeFi patterns
    has_oracle_reads: bool
    has_swap_operations: bool
    has_token_transfers: bool

    # Loop patterns
    has_unbounded_loops: bool
    has_loops_with_external_calls: bool

    # Complexity
    complexity: str  # "low", "medium", "high"
    avg_cyclomatic_complexity: float


def analyze_contract(graph: KnowledgeGraph) -> ContractAnalysis:
    """Analyze contract to determine relevant query categories.

    Args:
        graph: Knowledge graph of the contract

    Returns:
        ContractAnalysis with security-relevant characteristics
    """
    # Filter nodes by type
    functions = [n for n in graph.nodes.values() if n.type == "Function"]
    state_vars = [n for n in graph.nodes.values() if n.type == "StateVariable"]
    loops = [n for n in graph.nodes.values() if n.type == "Loop"]

    # Count functions by visibility
    external = [f for f in functions if f.properties.get("visibility") == "external"]
    public = [f for f in functions if f.properties.get("visibility") == "public"]
    internal = [f for f in functions if f.properties.get("visibility") == "internal"]
    private = [f for f in functions if f.properties.get("visibility") == "private"]

    # Detect privileged state variables
    privileged_tags = ["owner", "admin", "role", "implementation", "governor", "timelock"]
    privileged = [
        v for v in state_vars
        if any(tag in v.properties.get("security_tags", [])
               for tag in privileged_tags)
    ]

    # Detect access control patterns
    has_access_control = any(
        f.properties.get("has_access_gate", False)
        for f in functions
    )

    # Detect reentrancy guards
    has_reentrancy_guards = any(
        f.properties.get("has_reentrancy_guard", False)
        for f in functions
    )

    # Detect pause mechanisms
    has_pause_mechanism = any(
        "paused" in v.properties.get("security_tags", [])
        for v in state_vars
    )

    # Detect upgrade patterns
    has_upgrade_mechanism = any(
        "implementation" in v.properties.get("security_tags", [])
        for v in state_vars
    )

    # Detect external calls
    has_external_calls = any(
        f.properties.get("has_external_calls", False)
        for f in functions
    )

    # Detect delegatecalls
    has_delegatecalls = any(
        f.properties.get("uses_delegatecall", False)
        for f in functions
    )

    # Detect low-level calls
    has_low_level_calls = any(
        len(f.properties.get("low_level_calls", [])) > 0
        for f in functions
    )

    # Detect oracle reads
    has_oracle_reads = any(
        f.properties.get("reads_oracle_price", False)
        for f in functions
    )

    # Detect swap operations
    has_swap_operations = any(
        f.properties.get("swap_like", False)
        for f in functions
    )

    # Detect token transfers
    has_token_transfers = any(
        f.properties.get("uses_erc20_transfer", False)
        for f in functions
    )

    # Detect unbounded loops
    has_unbounded_loops = any(
        loop.properties.get("has_unbounded_loop", False)
        for loop in loops
    )

    # Detect loops with external calls
    has_loops_with_external_calls = any(
        loop.properties.get("external_calls_in_loop", False)
        for loop in loops
    )

    # Calculate complexity
    total_funcs = len(functions)
    if total_funcs == 0:
        complexity = "empty"
        avg_complexity = 0.0
    elif total_funcs < 10:
        complexity = "low"
        avg_complexity = 1.0
    elif total_funcs < 30:
        complexity = "medium"
        avg_complexity = 2.0
    else:
        complexity = "high"
        avg_complexity = 3.0

    return ContractAnalysis(
        total_functions=total_funcs,
        external_functions=len(external),
        public_functions=len(public),
        internal_functions=len(internal),
        private_functions=len(private),
        total_state_vars=len(state_vars),
        privileged_state_vars=len(privileged),
        has_access_control=has_access_control,
        has_reentrancy_guards=has_reentrancy_guards,
        has_pause_mechanism=has_pause_mechanism,
        has_upgrade_mechanism=has_upgrade_mechanism,
        has_external_calls=has_external_calls,
        has_delegatecalls=has_delegatecalls,
        has_low_level_calls=has_low_level_calls,
        has_oracle_reads=has_oracle_reads,
        has_swap_operations=has_swap_operations,
        has_token_transfers=has_token_transfers,
        has_unbounded_loops=has_unbounded_loops,
        has_loops_with_external_calls=has_loops_with_external_calls,
        complexity=complexity,
        avg_cyclomatic_complexity=avg_complexity,
    )
