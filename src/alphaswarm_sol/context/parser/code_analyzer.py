"""VKG-based code analyzer for protocol context extraction.

This module extracts protocol context directly from VKG KnowledgeGraph analysis.
It complements doc-based parsing by deriving roles, assumptions, and invariants
from actual code patterns.

Per 03-CONTEXT.md: "Active inference of unstated assumptions"
- 'uses oracle' -> infers 'assumes oracle honest'
- 'calls external' -> infers 'assumes external contract behaves correctly'

The analyzer provides:
- Role extraction from access control patterns
- Critical function identification from VKG properties
- Assumption inference from semantic operations
- Off-chain input detection from oracle/external reads
- Value flow extraction from transfer patterns

Usage:
    from alphaswarm_sol.context.parser import CodeAnalyzer
    from alphaswarm_sol.kg.schema import KnowledgeGraph

    graph = build_kg("contracts/")
    analyzer = CodeAnalyzer(graph)
    result = analyzer.analyze()

    # Access extracted context
    print(f"Roles: {[r.name for r in result.roles]}")
    print(f"Critical functions: {result.critical_functions}")
    print(f"Assumptions: {[a.description for a in result.inferred_assumptions]}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from ..types import (
    Assumption,
    Confidence,
    Invariant,
    OffchainInput,
    Role,
    ValueFlow,
)

if TYPE_CHECKING:
    from alphaswarm_sol.kg.schema import KnowledgeGraph, Node


# =============================================================================
# Operation-to-Assumption Mapping
# =============================================================================

# Per 03-CONTEXT.md: Map VKG semantic operations to inferred assumptions
# These are assumptions the protocol implicitly makes when using certain operations


def _create_operation_assumptions() -> Dict[str, List[Assumption]]:
    """Create the operation-to-assumption mapping.

    Returns a dictionary mapping VKG semantic operations to lists of
    Assumption objects that should be inferred when that operation is detected.
    """
    return {
        "READS_ORACLE": [
            Assumption(
                description="Oracle provides accurate and timely price data",
                category="price",
                affects_functions=[],  # Will be populated per-function
                confidence=Confidence.INFERRED,
                source="code:oracle_read",
                tags=["oracle", "price", "external"],
            ),
            Assumption(
                description="Oracle cannot be manipulated within a single transaction",
                category="price",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:oracle_read",
                tags=["oracle", "manipulation", "flash-loan"],
            ),
        ],
        "READS_EXTERNAL_VALUE": [
            Assumption(
                description="External data source returns valid and expected values",
                category="trust",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:external_read",
                tags=["external", "data", "trust"],
            ),
        ],
        "CALLS_UNTRUSTED": [
            Assumption(
                description="External call target behaves according to expected interface",
                category="trust",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:untrusted_call",
                tags=["external", "trust", "interface"],
            ),
            Assumption(
                description="External call does not perform unexpected reentrancy",
                category="trust",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:untrusted_call",
                tags=["external", "reentrancy", "callback"],
            ),
        ],
        "CALLS_EXTERNAL": [
            Assumption(
                description="External contract call completes successfully or reverts cleanly",
                category="trust",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:external_call",
                tags=["external", "call", "revert"],
            ),
        ],
        "USES_TIMESTAMP": [
            Assumption(
                description="Block timestamps are within acceptable deviation for time-sensitive logic",
                category="time",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:timestamp_use",
                tags=["time", "timestamp", "block"],
            ),
            Assumption(
                description="Miners/validators cannot manipulate timestamp significantly",
                category="time",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:timestamp_use",
                tags=["time", "manipulation", "miner"],
            ),
        ],
        "USES_BLOCK_DATA": [
            Assumption(
                description="Block data (number, hash) is sufficiently unpredictable for intended use",
                category="randomness",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:block_data",
                tags=["block", "randomness", "predictability"],
            ),
        ],
        "LOOPS_OVER_ARRAY": [
            Assumption(
                description="Array sizes are bounded to prevent gas exhaustion",
                category="economic",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:array_loop",
                tags=["array", "gas", "dos"],
            ),
        ],
        "TRANSFERS_VALUE_OUT": [
            Assumption(
                description="Receiving address can accept ETH/tokens without reverting",
                category="trust",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:value_transfer",
                tags=["transfer", "receive", "revert"],
            ),
        ],
        "PERFORMS_DIVISION": [
            Assumption(
                description="Division denominators are non-zero",
                category="economic",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:division",
                tags=["division", "zero", "arithmetic"],
            ),
            Assumption(
                description="Precision loss from division is acceptable for intended use",
                category="economic",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:division",
                tags=["division", "precision", "rounding"],
            ),
        ],
        "PERFORMS_MULTIPLICATION": [
            Assumption(
                description="Multiplication does not overflow for expected input ranges",
                category="economic",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:multiplication",
                tags=["multiplication", "overflow", "arithmetic"],
            ),
        ],
        "MODIFIES_CRITICAL_STATE": [
            Assumption(
                description="Critical state modifications are authorized and intended",
                category="access",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:critical_state",
                tags=["state", "critical", "access"],
            ),
        ],
        "INITIALIZES_STATE": [
            Assumption(
                description="Initialization can only occur once (not re-initializable)",
                category="access",
                affects_functions=[],
                confidence=Confidence.INFERRED,
                source="code:initializer",
                tags=["initialize", "once", "upgrade"],
            ),
        ],
    }


OPERATION_ASSUMPTIONS = _create_operation_assumptions()


# =============================================================================
# Role Capability Mapping
# =============================================================================

# Maps modifier names to (role_name, [capabilities])
ROLE_CAPABILITIES: Dict[str, tuple[str, List[str]]] = {
    "onlyowner": ("owner", ["ownership", "admin"]),
    "onlyadmin": ("admin", ["administration", "configure"]),
    "onlyminter": ("minter", ["mint"]),
    "onlyburner": ("burner", ["burn"]),
    "onlypauser": ("pauser", ["pause", "unpause"]),
    "onlyupgrader": ("upgrader", ["upgrade"]),
    "onlygovernance": ("governance", ["govern", "propose", "execute"]),
    "onlygov": ("governance", ["govern", "propose"]),
    "onlyoperator": ("operator", ["operate", "execute"]),
    "onlyguardian": ("guardian", ["emergency", "pause"]),
    "onlykeeper": ("keeper", ["maintain", "liquidate"]),
    "onlyliquidator": ("liquidator", ["liquidate"]),
    "onlyoracle": ("oracle", ["update_price", "report"]),
    "onlyrelayer": ("relayer", ["relay", "forward"]),
    "auth": ("authorized", ["call_protected"]),
    "requiresauth": ("authorized", ["call_protected"]),
    "restricted": ("restricted", ["restricted_access"]),
}

# Trust assumptions for different role types
ROLE_TRUST_ASSUMPTIONS: Dict[str, List[str]] = {
    "owner": [
        "Owner is trusted to act in protocol's best interest",
        "Owner key is securely managed (multisig, timelock, etc.)",
    ],
    "admin": [
        "Admin is trusted to configure protocol parameters correctly",
        "Admin will not set malicious configurations",
    ],
    "governance": [
        "Governance process prevents malicious proposals",
        "Token holders vote in protocol's best interest",
    ],
    "guardian": [
        "Guardian only uses emergency powers in actual emergencies",
        "Guardian cannot extract user funds",
    ],
    "keeper": [
        "Keeper will perform maintenance operations in timely manner",
        "Keeper incentives align with protocol health",
    ],
    "liquidator": [
        "Liquidations will occur promptly when positions are unhealthy",
        "Liquidation incentives are sufficient to attract liquidators",
    ],
    "minter": [
        "Minter will not inflate supply maliciously",
        "Minting is controlled by protocol rules",
    ],
    "pauser": [
        "Pauser will only pause in emergency situations",
        "Pause functionality is temporary and reversible",
    ],
    "upgrader": [
        "Upgrader will not deploy malicious implementation",
        "Upgrades go through proper review/timelock",
    ],
}


# =============================================================================
# Analysis Result
# =============================================================================


@dataclass
class AnalysisResult:
    """Result of code-based context extraction.

    Contains all context elements extracted from VKG analysis.

    Attributes:
        roles: Extracted protocol roles with capabilities
        critical_functions: List of critical function identifiers
        inferred_assumptions: Assumptions inferred from code patterns
        inferred_invariants: Potential invariants detected from code
        offchain_inputs: Detected off-chain dependencies
        value_flows: Economic value movement patterns
        warnings: Issues or uncertainties found during analysis
    """
    roles: List[Role] = field(default_factory=list)
    critical_functions: List[str] = field(default_factory=list)
    inferred_assumptions: List[Assumption] = field(default_factory=list)
    inferred_invariants: List[Invariant] = field(default_factory=list)
    offchain_inputs: List[OffchainInput] = field(default_factory=list)
    value_flows: List[ValueFlow] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "roles": [r.to_dict() for r in self.roles],
            "critical_functions": self.critical_functions,
            "inferred_assumptions": [a.to_dict() for a in self.inferred_assumptions],
            "inferred_invariants": [i.to_dict() for i in self.inferred_invariants],
            "offchain_inputs": [o.to_dict() for o in self.offchain_inputs],
            "value_flows": [v.to_dict() for v in self.value_flows],
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisResult":
        """Create AnalysisResult from dictionary."""
        return cls(
            roles=[Role.from_dict(r) for r in data.get("roles", [])],
            critical_functions=list(data.get("critical_functions", [])),
            inferred_assumptions=[Assumption.from_dict(a) for a in data.get("inferred_assumptions", [])],
            inferred_invariants=[Invariant.from_dict(i) for i in data.get("inferred_invariants", [])],
            offchain_inputs=[OffchainInput.from_dict(o) for o in data.get("offchain_inputs", [])],
            value_flows=[ValueFlow.from_dict(v) for v in data.get("value_flows", [])],
            warnings=list(data.get("warnings", [])),
        )

    def merge(self, other: "AnalysisResult") -> "AnalysisResult":
        """Merge another AnalysisResult into this one.

        Useful for combining results from multiple analysis passes.
        """
        # Merge roles by name, combining capabilities
        role_map: Dict[str, Role] = {r.name: r for r in self.roles}
        for role in other.roles:
            if role.name in role_map:
                existing = role_map[role.name]
                # Merge capabilities
                combined_caps = list(set(existing.capabilities + role.capabilities))
                # Merge trust assumptions
                combined_trust = list(set(existing.trust_assumptions + role.trust_assumptions))
                role_map[role.name] = Role(
                    name=role.name,
                    capabilities=combined_caps,
                    trust_assumptions=combined_trust,
                    confidence=min(existing.confidence, role.confidence),
                    description=existing.description or role.description,
                )
            else:
                role_map[role.name] = role

        # Merge critical functions (dedupe)
        combined_critical = list(set(self.critical_functions + other.critical_functions))

        # Merge assumptions (dedupe by description)
        seen_assumptions: Set[str] = {a.description for a in self.inferred_assumptions}
        combined_assumptions = list(self.inferred_assumptions)
        for assumption in other.inferred_assumptions:
            if assumption.description not in seen_assumptions:
                combined_assumptions.append(assumption)
                seen_assumptions.add(assumption.description)

        # Merge invariants (dedupe by natural_language)
        seen_invariants: Set[str] = {i.natural_language for i in self.inferred_invariants}
        combined_invariants = list(self.inferred_invariants)
        for invariant in other.inferred_invariants:
            if invariant.natural_language not in seen_invariants:
                combined_invariants.append(invariant)
                seen_invariants.add(invariant.natural_language)

        # Merge offchain inputs (dedupe by name)
        seen_inputs: Set[str] = {o.name for o in self.offchain_inputs}
        combined_inputs = list(self.offchain_inputs)
        for inp in other.offchain_inputs:
            if inp.name not in seen_inputs:
                combined_inputs.append(inp)
                seen_inputs.add(inp.name)

        # Merge value flows (dedupe by name)
        seen_flows: Set[str] = {v.name for v in self.value_flows}
        combined_flows = list(self.value_flows)
        for flow in other.value_flows:
            if flow.name not in seen_flows:
                combined_flows.append(flow)
                seen_flows.add(flow.name)

        # Merge warnings (dedupe)
        combined_warnings = list(set(self.warnings + other.warnings))

        return AnalysisResult(
            roles=list(role_map.values()),
            critical_functions=combined_critical,
            inferred_assumptions=combined_assumptions,
            inferred_invariants=combined_invariants,
            offchain_inputs=combined_inputs,
            value_flows=combined_flows,
            warnings=combined_warnings,
        )


# =============================================================================
# Code Analyzer
# =============================================================================


class CodeAnalyzer:
    """Extract protocol context from VKG analysis.

    Analyzes KnowledgeGraph to extract:
    - Roles from access control patterns (MODIFIES_OWNER, MODIFIES_ROLES, etc.)
    - Critical functions from semantic operations
    - Inferred assumptions from code patterns
    - Off-chain dependencies from oracle/external reads
    - Value flows from transfer patterns

    Usage:
        from alphaswarm_sol.kg.schema import KnowledgeGraph
        from alphaswarm_sol.context.parser import CodeAnalyzer

        graph = build_kg("contracts/")
        analyzer = CodeAnalyzer(graph)
        result = analyzer.analyze()

        for role in result.roles:
            print(f"{role.name}: {role.capabilities}")
    """

    def __init__(self, graph: "KnowledgeGraph") -> None:
        """Initialize the analyzer with a KnowledgeGraph.

        Args:
            graph: VKG KnowledgeGraph to analyze
        """
        self.graph = graph
        self._function_nodes: Optional[List["Node"]] = None
        self._contract_nodes: Optional[List["Node"]] = None

    @property
    def function_nodes(self) -> List["Node"]:
        """Get all function nodes from the graph."""
        if self._function_nodes is None:
            self._function_nodes = [
                node for node in self.graph.nodes.values()
                if node.type == "function"
            ]
        return self._function_nodes

    @property
    def contract_nodes(self) -> List["Node"]:
        """Get all contract nodes from the graph."""
        if self._contract_nodes is None:
            self._contract_nodes = [
                node for node in self.graph.nodes.values()
                if node.type == "contract"
            ]
        return self._contract_nodes

    def analyze(self) -> AnalysisResult:
        """Run full code analysis.

        Returns:
            AnalysisResult containing all extracted context
        """
        result = AnalysisResult()

        # Extract roles from access control patterns
        result.roles = self.extract_roles()

        # Identify critical functions
        result.critical_functions = self.extract_critical_functions()

        # Infer assumptions from code patterns
        result.inferred_assumptions = self.infer_assumptions()

        # Infer potential invariants
        result.inferred_invariants = self.infer_invariants()

        # Extract off-chain inputs
        result.offchain_inputs = self.extract_offchain_inputs()

        # Extract value flows
        result.value_flows = self.extract_value_flows()

        return result

    def extract_roles(self) -> List[Role]:
        """Extract roles from access control patterns.

        Looks for:
        - Functions with MODIFIES_OWNER -> infer 'owner' role
        - Functions with MODIFIES_ROLES -> infer role system
        - Functions with CHECKS_PERMISSION -> infer protected capabilities
        - onlyOwner/onlyAdmin modifiers -> role names

        Returns:
            List of extracted Role objects
        """
        roles: Dict[str, Role] = {}

        for node in self.function_nodes:
            props = node.properties
            func_name = props.get("name", node.label)

            # Check for modifier-based roles
            modifiers = props.get("modifiers", [])
            if isinstance(modifiers, str):
                modifiers = [modifiers]

            for mod in modifiers:
                mod_lower = mod.lower().replace("_", "")
                if mod_lower in ROLE_CAPABILITIES:
                    role_name, capabilities = ROLE_CAPABILITIES[mod_lower]
                    if role_name not in roles:
                        trust = ROLE_TRUST_ASSUMPTIONS.get(role_name, [])
                        roles[role_name] = Role(
                            name=role_name,
                            capabilities=list(capabilities),
                            trust_assumptions=list(trust),
                            confidence=Confidence.INFERRED,
                            source=f"code:modifier:{mod}",
                        )
                    else:
                        # Add new capabilities from this function
                        for cap in capabilities:
                            if cap not in roles[role_name].capabilities:
                                roles[role_name].capabilities.append(cap)

            # Check for ownership modification patterns
            if props.get("modifies_owner"):
                if "owner" not in roles:
                    roles["owner"] = Role(
                        name="owner",
                        capabilities=["transfer_ownership", "set_owner"],
                        trust_assumptions=ROLE_TRUST_ASSUMPTIONS.get("owner", []),
                        confidence=Confidence.INFERRED,
                        source="code:modifies_owner",
                    )
                # Add the function's capability
                cap = f"call_{func_name}"
                if cap not in roles["owner"].capabilities:
                    roles["owner"].capabilities.append(cap)

            # Check for role modification patterns
            if props.get("modifies_roles"):
                if "admin" not in roles:
                    roles["admin"] = Role(
                        name="admin",
                        capabilities=["manage_roles", "grant_role", "revoke_role"],
                        trust_assumptions=ROLE_TRUST_ASSUMPTIONS.get("admin", []),
                        confidence=Confidence.INFERRED,
                        source="code:modifies_roles",
                    )

            # Check for access gate patterns (has_access_gate)
            if props.get("has_access_gate") and not props.get("visibility") == "public":
                # This is a protected function
                # Try to infer which role can call it
                pass  # Already handled by modifier detection above

        return list(roles.values())

    def extract_critical_functions(self) -> List[str]:
        """Identify critical functions from VKG properties.

        Critical if any of:
        - MODIFIES_CRITICAL_STATE = true
        - TRANSFERS_VALUE_OUT = true
        - MODIFIES_OWNER = true
        - has upgrade capability (proxy patterns)
        - writes_privileged_state = true

        Returns:
            List of critical function identifiers (contract.function format)
        """
        critical: List[str] = []

        for node in self.function_nodes:
            props = node.properties
            is_critical = False

            # Check critical state modification
            if props.get("modifies_critical_state"):
                is_critical = True

            # Check value transfers
            if props.get("transfers_value_out"):
                is_critical = True

            # Check ownership modification
            if props.get("modifies_owner"):
                is_critical = True

            # Check role modification
            if props.get("modifies_roles"):
                is_critical = True

            # Check privileged state writes
            if props.get("writes_privileged_state"):
                is_critical = True

            # Check for initializer/upgrade patterns
            func_name = props.get("name", node.label).lower()
            if any(kw in func_name for kw in ["initialize", "upgrade", "implementation"]):
                is_critical = True

            # Check semantic operations
            semantic_ops = props.get("semantic_operations", [])
            if isinstance(semantic_ops, str):
                semantic_ops = [semantic_ops]
            critical_ops = {
                "MODIFIES_CRITICAL_STATE",
                "MODIFIES_OWNER",
                "MODIFIES_ROLES",
                "TRANSFERS_VALUE_OUT",
                "INITIALIZES_STATE",
            }
            if any(op in critical_ops for op in semantic_ops):
                is_critical = True

            if is_critical:
                # Format as contract.function
                contract_name = props.get("contract_name", "")
                func_name = props.get("name", node.label)
                if contract_name:
                    critical.append(f"{contract_name}.{func_name}")
                else:
                    critical.append(func_name)

        return list(set(critical))  # Dedupe

    def infer_assumptions(self) -> List[Assumption]:
        """Infer assumptions from code patterns.

        Per 03-CONTEXT.md: 'uses oracle' -> infers 'assumes oracle honest'

        Patterns:
        - READS_ORACLE -> assumes oracle is honest, price is accurate
        - CALLS_EXTERNAL to known addresses -> assumes external contract is safe
        - USES_TIMESTAMP -> assumes timestamps are accurate enough
        - unbounded loops -> assumes array sizes are bounded
        - delegatecall -> assumes implementation is trusted

        Returns:
            List of inferred Assumption objects
        """
        assumptions: Dict[str, Assumption] = {}  # Key by description for dedup

        for node in self.function_nodes:
            func_assumptions = self._get_assumptions_for_function(node)
            for assumption in func_assumptions:
                key = assumption.description
                if key not in assumptions:
                    assumptions[key] = assumption
                else:
                    # Merge affects_functions
                    existing = assumptions[key]
                    for func in assumption.affects_functions:
                        if func not in existing.affects_functions:
                            existing.affects_functions.append(func)

        return list(assumptions.values())

    def _get_assumptions_for_function(self, node: "Node") -> List[Assumption]:
        """Get assumptions for a specific function node.

        Args:
            node: Function node from the graph

        Returns:
            List of Assumption objects for this function
        """
        assumptions: List[Assumption] = []
        props = node.properties
        func_name = props.get("name", node.label)
        contract_name = props.get("contract_name", "")
        full_name = f"{contract_name}.{func_name}" if contract_name else func_name

        # Get semantic operations from properties
        semantic_ops = props.get("semantic_operations", [])
        if isinstance(semantic_ops, str):
            semantic_ops = [semantic_ops]

        # Map operations to assumptions
        for op in semantic_ops:
            op_upper = op.upper()
            if op_upper in OPERATION_ASSUMPTIONS:
                for template in OPERATION_ASSUMPTIONS[op_upper]:
                    # Create a copy with the function attached
                    assumption = Assumption(
                        description=template.description,
                        category=template.category,
                        affects_functions=[full_name],
                        confidence=Confidence.INFERRED,
                        source=template.source,
                        tags=list(template.tags),
                    )
                    assumptions.append(assumption)

        # Check for additional patterns not in semantic_operations
        # Delegatecall pattern
        if props.get("uses_delegatecall"):
            assumptions.append(Assumption(
                description="Delegatecall target implementation is trusted and non-malicious",
                category="trust",
                affects_functions=[full_name],
                confidence=Confidence.INFERRED,
                source="code:delegatecall",
                tags=["delegatecall", "proxy", "trust"],
            ))

        # Unchecked low-level calls
        if props.get("low_level_calls") and not props.get("checks_return_value"):
            assumptions.append(Assumption(
                description="Low-level call failures are acceptable or handled elsewhere",
                category="trust",
                affects_functions=[full_name],
                confidence=Confidence.INFERRED,
                source="code:unchecked_call",
                tags=["low-level", "call", "return"],
            ))

        # Reentrancy without guard
        if (props.get("calls_external") and
            props.get("writes_state_after_call") and
            not props.get("has_reentrancy_guard")):
            assumptions.append(Assumption(
                description="External call recipient will not perform reentrant calls",
                category="trust",
                affects_functions=[full_name],
                confidence=Confidence.INFERRED,
                source="code:no_reentrancy_guard",
                tags=["reentrancy", "external", "callback"],
            ))

        return assumptions

    def infer_invariants(self) -> List[Invariant]:
        """Infer potential invariants from code.

        Look for:
        - Balance tracking patterns -> sum invariants
        - Supply tracking -> totalSupply <= maxSupply
        - Access control patterns -> ownership invariants

        Returns:
            List of inferred Invariant objects
        """
        invariants: List[Invariant] = []

        # Look for supply-related state variables
        has_total_supply = False
        has_max_supply = False
        has_balance_mapping = False

        for node in self.graph.nodes.values():
            if node.type == "state_variable":
                name_lower = node.label.lower()
                if "totalsupply" in name_lower or "total_supply" in name_lower:
                    has_total_supply = True
                if "maxsupply" in name_lower or "max_supply" in name_lower or "cap" in name_lower:
                    has_max_supply = True
                if "balance" in name_lower:
                    has_balance_mapping = True

        # Infer supply invariants
        if has_total_supply and has_max_supply:
            invariants.append(Invariant(
                formal={"what": "totalSupply", "must": "lte", "value": "maxSupply"},
                natural_language="Total token supply must never exceed the maximum supply cap",
                confidence=Confidence.INFERRED,
                source="code:supply_tracking",
                category="supply",
                critical=True,
            ))

        if has_total_supply:
            invariants.append(Invariant(
                formal={"what": "totalSupply", "must": "eq", "value": "sum(balances)"},
                natural_language="Total supply equals the sum of all individual balances",
                confidence=Confidence.INFERRED,
                source="code:supply_tracking",
                category="supply",
                critical=True,
            ))

        if has_balance_mapping:
            invariants.append(Invariant(
                formal={"what": "balance[user]", "must": "gte", "value": "0"},
                natural_language="User balances are always non-negative",
                confidence=Confidence.INFERRED,
                source="code:balance_tracking",
                category="balance",
                critical=True,
            ))

        # Check for ownership patterns
        has_owner = any(
            "owner" in node.label.lower()
            for node in self.graph.nodes.values()
            if node.type == "state_variable"
        )
        if has_owner:
            invariants.append(Invariant(
                formal={"what": "owner", "must": "neq", "value": "address(0)"},
                natural_language="Contract always has a valid owner (not zero address)",
                confidence=Confidence.INFERRED,
                source="code:ownership",
                category="access",
                critical=False,  # Not always critical
            ))

        return invariants

    def extract_offchain_inputs(self) -> List[OffchainInput]:
        """Extract off-chain dependencies.

        Detect:
        - Oracle reads (Chainlink, custom oracles)
        - External contract calls that may be off-chain controlled
        - Admin functions that require off-chain action

        Returns:
            List of OffchainInput objects
        """
        inputs: Dict[str, OffchainInput] = {}  # Key by name for dedup

        for node in self.function_nodes:
            props = node.properties
            func_name = props.get("name", node.label)
            contract_name = props.get("contract_name", "")
            full_name = f"{contract_name}.{func_name}" if contract_name else func_name
            semantic_ops = props.get("semantic_operations", [])
            if isinstance(semantic_ops, str):
                semantic_ops = [semantic_ops]

            # Check for oracle reads
            if "READS_ORACLE" in semantic_ops or props.get("reads_oracle"):
                key = "price_oracle"
                if key not in inputs:
                    inputs[key] = OffchainInput(
                        name="Price Oracle",
                        input_type="oracle",
                        description="External price feed for asset valuations",
                        trust_assumptions=[
                            "Oracle provides timely price updates",
                            "Oracle data is resistant to manipulation",
                            "Oracle has sufficient decentralization",
                        ],
                        affects_functions=[full_name],
                        confidence=Confidence.INFERRED,
                    )
                else:
                    if full_name not in inputs[key].affects_functions:
                        inputs[key].affects_functions.append(full_name)

            # Check for external value reads
            if "READS_EXTERNAL_VALUE" in semantic_ops or props.get("reads_external_value"):
                key = "external_data"
                if key not in inputs:
                    inputs[key] = OffchainInput(
                        name="External Data Source",
                        input_type="oracle",
                        description="External contract providing data used in calculations",
                        trust_assumptions=[
                            "External source returns valid data",
                            "External source is available when needed",
                        ],
                        affects_functions=[full_name],
                        confidence=Confidence.INFERRED,
                    )
                else:
                    if full_name not in inputs[key].affects_functions:
                        inputs[key].affects_functions.append(full_name)

            # Check for admin-gated functions
            if props.get("has_access_gate"):
                modifiers = props.get("modifiers", [])
                if isinstance(modifiers, str):
                    modifiers = [modifiers]

                for mod in modifiers:
                    mod_lower = mod.lower()
                    if "owner" in mod_lower or "admin" in mod_lower or "gov" in mod_lower:
                        key = "admin_actions"
                        if key not in inputs:
                            inputs[key] = OffchainInput(
                                name="Admin Actions",
                                input_type="admin",
                                description="Administrative functions requiring off-chain execution",
                                trust_assumptions=[
                                    "Admin keys are securely managed",
                                    "Admin actions go through proper review process",
                                ],
                                affects_functions=[full_name],
                                confidence=Confidence.INFERRED,
                            )
                        else:
                            if full_name not in inputs[key].affects_functions:
                                inputs[key].affects_functions.append(full_name)
                        break

        return list(inputs.values())

    def extract_value_flows(self) -> List[ValueFlow]:
        """Extract economic value flows.

        Analyze transfer patterns to understand:
        - Who can send value
        - Who receives value
        - Under what conditions

        Returns:
            List of ValueFlow objects
        """
        flows: Dict[str, ValueFlow] = {}  # Key by name for dedup

        for node in self.function_nodes:
            props = node.properties
            func_name = props.get("name", node.label)
            contract_name = props.get("contract_name", "")
            semantic_ops = props.get("semantic_operations", [])
            if isinstance(semantic_ops, str):
                semantic_ops = [semantic_ops]

            # Check for value transfer out
            if "TRANSFERS_VALUE_OUT" in semantic_ops or props.get("transfers_value_out"):
                # Determine from/to based on context
                has_access_gate = props.get("has_access_gate", False)
                is_payable = props.get("is_payable", False)

                # Withdrawal pattern: user calls to get their funds
                if "withdraw" in func_name.lower():
                    key = "user_withdrawal"
                    if key not in flows:
                        flows[key] = ValueFlow(
                            name="user_withdrawal",
                            from_role="protocol",
                            to_role="user",
                            asset="ETH/tokens",
                            conditions=["user has balance", "not paused"],
                            confidence=Confidence.INFERRED,
                            description=f"Users withdraw funds via {func_name}",
                        )

                # Admin transfer pattern
                elif has_access_gate:
                    key = "admin_transfer"
                    if key not in flows:
                        flows[key] = ValueFlow(
                            name="admin_transfer",
                            from_role="protocol",
                            to_role="admin",
                            asset="ETH/tokens",
                            conditions=["admin authorized", "emergency or fee collection"],
                            confidence=Confidence.INFERRED,
                            description=f"Admin-gated value transfer via {func_name}",
                        )

                # Generic external transfer
                else:
                    key = f"transfer_{func_name}"
                    if key not in flows:
                        flows[key] = ValueFlow(
                            name=f"transfer_{func_name}",
                            from_role="protocol",
                            to_role="external",
                            asset="ETH/tokens",
                            conditions=["function conditions met"],
                            confidence=Confidence.INFERRED,
                            description=f"Value transfer via {func_name}",
                        )

            # Check for value receipt
            if "RECEIVES_VALUE_IN" in semantic_ops or props.get("is_payable"):
                if "deposit" in func_name.lower():
                    key = "user_deposit"
                    if key not in flows:
                        flows[key] = ValueFlow(
                            name="user_deposit",
                            from_role="user",
                            to_role="protocol",
                            asset="ETH/tokens",
                            conditions=["msg.value > 0", "not paused"],
                            confidence=Confidence.INFERRED,
                            description=f"Users deposit funds via {func_name}",
                        )
                else:
                    key = f"receive_{func_name}"
                    if key not in flows:
                        flows[key] = ValueFlow(
                            name=f"receive_{func_name}",
                            from_role="external",
                            to_role="protocol",
                            asset="ETH",
                            conditions=["payable function"],
                            confidence=Confidence.INFERRED,
                            description=f"Value received via {func_name}",
                        )

        return list(flows.values())
