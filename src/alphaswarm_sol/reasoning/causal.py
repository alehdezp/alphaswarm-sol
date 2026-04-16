"""
Phase 3: Causal Reasoning Engine

Builds causal graphs from VKG behavioral signatures and identifies root causes
of vulnerabilities with fix recommendations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, TYPE_CHECKING
from enum import Enum
import time

if TYPE_CHECKING:
    from alphaswarm_sol.kg.schema import Node


class CausalRelationType(Enum):
    """Types of causal relationships."""
    DATA_FLOW = "data_flow"  # X provides data used by Y
    CONTROL_FLOW = "control_flow"  # X controls whether Y executes
    SEQUENCE = "sequence"  # X happens before Y (temporal)
    EXTERNAL_INFLUENCE = "external"  # X can affect Y through external means
    STATE_DEPENDENCY = "state_dep"  # Y depends on state modified by X


@dataclass
class CausalNode:
    """
    Node in causal graph representing an operation or condition.

    Maps to VKG semantic operations and code locations.
    """
    id: str
    operation: str  # Semantic operation (e.g., "TRANSFERS_VALUE_OUT")
    description: str  # Human-readable description

    # Code location
    line_start: int
    line_end: int

    # Causal properties
    is_controllable: bool = False  # Can attacker control this?
    is_observable: bool = False  # Can attacker observe this?
    is_root_candidate: bool = False  # Could be a root cause?

    # Graph connectivity (managed by CausalGraph)
    causes: List[str] = field(default_factory=list)  # Nodes that cause this
    effects: List[str] = field(default_factory=list)  # Nodes this causes

    # Importance scoring
    centrality_score: float = 0.0  # How central in causal chain

    code_snippet: Optional[str] = None


@dataclass
class CausalEdge:
    """Edge representing a causal relationship."""
    source_id: str
    target_id: str
    relation_type: CausalRelationType

    # Strength of causal relationship
    strength: float  # 0.0 to 1.0

    # Can this edge be broken (intervention point)?
    is_breakable: bool = False

    # Evidence for this causal link
    evidence: List[str] = field(default_factory=list)
    break_methods: List[str] = field(default_factory=list)


@dataclass
class CausalGraph:
    """
    Directed acyclic graph of causal relationships.

    Built from VKG behavioral signatures and enriched with
    data flow and control flow information.
    """
    id: str
    focal_node_id: str  # The function being analyzed

    nodes: Dict[str, CausalNode] = field(default_factory=dict)
    edges: List[CausalEdge] = field(default_factory=list)

    # Precomputed paths
    root_to_vuln_paths: List[List[str]] = field(default_factory=list)

    vulnerability_id: Optional[str] = None  # The vulnerability this explains

    def add_node(self, node: CausalNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: CausalEdge) -> None:
        """Add an edge and update node connectivity."""
        self.edges.append(edge)
        if edge.source_id in self.nodes:
            self.nodes[edge.source_id].effects.append(edge.target_id)
        if edge.target_id in self.nodes:
            self.nodes[edge.target_id].causes.append(edge.source_id)

    def get_ancestors(self, node_id: str) -> Set[str]:
        """Get all nodes that causally precede this node."""
        ancestors = set()
        queue = [node_id]
        while queue:
            current = queue.pop(0)
            if current in self.nodes:
                for cause in self.nodes[current].causes:
                    if cause not in ancestors:
                        ancestors.add(cause)
                        queue.append(cause)
        return ancestors

    def get_descendants(self, node_id: str) -> Set[str]:
        """Get all nodes causally affected by this node."""
        descendants = set()
        queue = [node_id]
        while queue:
            current = queue.pop(0)
            if current in self.nodes:
                for effect in self.nodes[current].effects:
                    if effect not in descendants:
                        descendants.add(effect)
                        queue.append(effect)
        return descendants

    def find_paths(self, source_id: str, target_id: str) -> List[List[str]]:
        """Find all causal paths from source to target."""
        paths = []

        def dfs(current: str, path: List[str], visited: Set[str]):
            if current == target_id:
                paths.append(path.copy())
                return
            if current not in self.nodes:
                return
            for effect in self.nodes[current].effects:
                if effect not in visited:
                    visited.add(effect)
                    path.append(effect)
                    dfs(effect, path, visited)
                    path.pop()
                    visited.remove(effect)

        dfs(source_id, [source_id], {source_id})
        return paths


@dataclass
class RootCause:
    """A root cause of a vulnerability with fix recommendation."""
    id: str
    description: str  # Human-readable description

    # Classification
    cause_type: str  # "ordering_violation", "missing_guard", "missing_validation"
    severity: str  # "critical", "high", "medium", "low"

    # Causal path
    causal_path: List[str]  # Path from root to vulnerability manifestation

    # Intervention
    intervention: str  # What would fix this
    intervention_confidence: float  # How confident we are this would fix it

    # Evidence
    confidence: float = 0.0

    contributing_factors: List[str] = field(default_factory=list)
    alternative_interventions: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    related_cwes: List[str] = field(default_factory=list)
    related_patterns: List[str] = field(default_factory=list)


@dataclass
class InterventionPoint:
    """A point where intervention would break the causal chain."""
    id: str
    node_id: str  # The causal node where to intervene

    # What to do
    intervention_type: str  # "add_guard", "reorder", "add_check", "remove"
    description: str

    # Impact
    impact_score: float  # How effective (0.0 to 1.0)

    # Trade-offs
    complexity: str  # "trivial", "moderate", "complex"

    edge_id: Optional[str] = None  # The edge being broken (if applicable)
    code_suggestion: Optional[str] = None  # Suggested code change
    blocks_causes: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)


@dataclass
class CausalAnalysis:
    """Complete causal analysis result."""
    causal_graph: CausalGraph
    root_causes: List[RootCause]
    intervention_points: List[InterventionPoint]
    explanation: str  # Human-readable explanation

    # Metadata
    analysis_time_ms: float
    confidence: float


@dataclass
class OperationInfo:
    """Information about an operation extracted from behavioral signature."""
    operation: str
    description: str
    line: int
    index: int


class CausalReasoningEngine:
    """
    Builds causal graphs and identifies root causes.

    The engine works by:
    1. Extracting operations from behavioral signatures
    2. Building causal edges from data/control flow
    3. Identifying root causes via backward traversal
    4. Finding intervention points that break causal chains
    """

    def __init__(self, code_kg: "Node", llm_client=None):
        self.code_kg = code_kg
        self.llm = llm_client  # Optional for enhanced explanations

        # Root cause templates for common vulnerability patterns
        self._root_cause_templates = self._load_root_cause_templates()

    def analyze(
        self,
        fn_node: "Node",
        vulnerability: Optional[Dict] = None,
    ) -> CausalAnalysis:
        """
        Perform causal analysis on a function.

        Args:
            fn_node: The function node from VKG
            vulnerability: Optional vulnerability candidate providing context

        Returns:
            CausalAnalysis with graph, root causes, and interventions
        """
        start = time.time()

        # Step 1: Build causal graph
        causal_graph = self.build_causal_graph(fn_node, vulnerability)

        # Step 2: Identify root causes
        root_causes = self._identify_root_causes(causal_graph, fn_node, vulnerability)

        # Step 3: Find intervention points
        interventions = self._find_intervention_points(causal_graph, root_causes)

        # Step 4: Generate explanation
        explanation = self.generate_explanation(causal_graph, root_causes, interventions)

        elapsed_ms = (time.time() - start) * 1000

        return CausalAnalysis(
            causal_graph=causal_graph,
            root_causes=root_causes,
            intervention_points=interventions,
            explanation=explanation,
            analysis_time_ms=elapsed_ms,
            confidence=self._compute_confidence(root_causes),
        )

    def build_causal_graph(
        self,
        fn_node: "Node",
        vulnerability: Optional[Dict] = None,
    ) -> CausalGraph:
        """
        Build causal graph from function's behavioral signature and properties.

        Extracts operations and builds causal edges based on:
        - Data flow dependencies
        - Control flow dependencies
        - Temporal ordering (sequence)
        - External influence paths
        """
        causal_graph = CausalGraph(
            id=f"cg_{fn_node.id}",
            focal_node_id=fn_node.id,
            vulnerability_id=vulnerability.get("id") if vulnerability else None,
        )

        # Extract operations from behavioral signature
        operations = self._extract_operations(fn_node)

        # Add operations as nodes
        for i, op in enumerate(operations):
            node = CausalNode(
                id=f"{fn_node.id}_op_{i}",
                operation=op.operation,
                description=op.description,
                line_start=op.line,
                line_end=op.line,
                is_controllable=self._is_controllable(op),
                is_observable=self._is_observable(op),
            )
            causal_graph.add_node(node)

        # Build edges
        self._add_data_flow_edges(causal_graph, fn_node)
        self._add_control_flow_edges(causal_graph, fn_node)
        self._add_sequence_edges(causal_graph, operations)
        self._add_external_influence_edges(causal_graph, fn_node)

        # Mark root candidates (nodes with no incoming causal edges)
        for node in causal_graph.nodes.values():
            if not node.causes:
                node.is_root_candidate = True

        # Compute centrality scores
        self._compute_centrality(causal_graph)

        return causal_graph

    def _extract_operations(self, fn_node: "Node") -> List[OperationInfo]:
        """Extract operations from behavioral signature."""
        sig = fn_node.properties.get("behavioral_signature", "")

        operations = []

        # Parse behavioral signature like "R:bal→X:out→W:bal"
        parts = sig.split("→") if sig else []

        op_map = {
            "R:bal": ("READS_USER_BALANCE", "Read user balance"),
            "W:bal": ("WRITES_USER_BALANCE", "Write user balance"),
            "X:out": ("TRANSFERS_VALUE_OUT", "External call/transfer"),
            "X:call": ("CALLS_EXTERNAL", "External function call"),
            "R:orc": ("READS_ORACLE", "Read oracle price"),
            "C:perm": ("CHECKS_PERMISSION", "Permission check"),
            "M:own": ("MODIFIES_OWNER", "Modify ownership"),
            "M:role": ("MODIFIES_ROLES", "Modify roles"),
            "A:div": ("PERFORMS_DIVISION", "Division operation"),
            "V:in": ("VALIDATES_INPUT", "Input validation"),
            "W:priv": ("WRITES_PRIVILEGED_STATE", "Write privileged state"),
        }

        for i, part in enumerate(parts):
            if part in op_map:
                op, desc = op_map[part]
                operations.append(OperationInfo(
                    operation=op,
                    description=desc,
                    line=0,  # Would get from actual analysis
                    index=i,
                ))

        return operations

    def _add_data_flow_edges(self, graph: CausalGraph, fn_node: "Node") -> None:
        """Add edges for data flow dependencies."""
        node_list = list(graph.nodes.values())

        for i, source in enumerate(node_list):
            for target in node_list[i+1:]:
                # Balance reads flow to operations that use balances
                if source.operation == "READS_USER_BALANCE":
                    if target.operation in ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"]:
                        graph.add_edge(CausalEdge(
                            source_id=source.id,
                            target_id=target.id,
                            relation_type=CausalRelationType.DATA_FLOW,
                            strength=0.9,
                            evidence=["Balance value flows to operation"],
                        ))

                # Oracle reads flow to calculations
                if source.operation == "READS_ORACLE":
                    if target.operation == "PERFORMS_DIVISION":
                        graph.add_edge(CausalEdge(
                            source_id=source.id,
                            target_id=target.id,
                            relation_type=CausalRelationType.DATA_FLOW,
                            strength=0.9,
                            evidence=["Oracle price flows to calculation"],
                        ))

    def _add_control_flow_edges(self, graph: CausalGraph, fn_node: "Node") -> None:
        """Add edges for control flow dependencies."""
        node_list = list(graph.nodes.values())

        for source in node_list:
            if source.operation == "CHECKS_PERMISSION":
                # Permission checks control subsequent operations
                for target in node_list:
                    if target.id != source.id:
                        graph.add_edge(CausalEdge(
                            source_id=source.id,
                            target_id=target.id,
                            relation_type=CausalRelationType.CONTROL_FLOW,
                            strength=0.8,
                            evidence=["Execution depends on permission check"],
                            is_breakable=True,
                            break_methods=["Access control"],
                        ))

    def _add_sequence_edges(self, graph: CausalGraph, operations: List[OperationInfo]) -> None:
        """Add edges for temporal sequence."""
        node_list = list(graph.nodes.values())

        for i in range(len(node_list) - 1):
            graph.add_edge(CausalEdge(
                source_id=node_list[i].id,
                target_id=node_list[i+1].id,
                relation_type=CausalRelationType.SEQUENCE,
                strength=1.0,
                evidence=["Temporal ordering in code"],
                is_breakable=True,
                break_methods=["Reorder operations"],
            ))

    def _add_external_influence_edges(self, graph: CausalGraph, fn_node: "Node") -> None:
        """Add edges for external influence (reentrancy paths)."""
        node_list = list(graph.nodes.values())

        # External calls can influence subsequent state operations
        for source in node_list:
            if source.operation in ["TRANSFERS_VALUE_OUT", "CALLS_EXTERNAL"]:
                for target in node_list:
                    if target.operation == "WRITES_USER_BALANCE":
                        # Check if target comes after source (sequence violation)
                        source_idx = list(graph.nodes.keys()).index(source.id)
                        target_idx = list(graph.nodes.keys()).index(target.id)

                        if source_idx < target_idx:
                            graph.add_edge(CausalEdge(
                                source_id=source.id,
                                target_id=target.id,
                                relation_type=CausalRelationType.EXTERNAL_INFLUENCE,
                                strength=0.95,
                                evidence=[
                                    "External call before state update",
                                    "Callback can re-enter",
                                ],
                                is_breakable=True,
                                break_methods=[
                                    "Add reentrancy guard",
                                    "Move state update before call",
                                    "Use pull pattern",
                                ],
                            ))

    def _identify_root_causes(
        self,
        graph: CausalGraph,
        fn_node: "Node",
        vulnerability: Optional[Dict],
    ) -> List[RootCause]:
        """
        Identify root causes by backward traversal from vulnerability.

        Uses pattern-specific templates and general causal analysis.
        """
        root_causes = []

        # Pattern-specific root cause detection
        if vulnerability and "attack_patterns" in vulnerability:
            for pattern in vulnerability["attack_patterns"]:
                pattern_id = pattern.get("id", "")
                if "reentrancy" in pattern_id.lower():
                    root_causes.extend(
                        self._identify_reentrancy_root_causes(graph, fn_node)
                    )
                elif "access" in pattern_id.lower():
                    root_causes.extend(
                        self._identify_access_control_root_causes(graph, fn_node)
                    )
                elif "oracle" in pattern_id.lower():
                    root_causes.extend(
                        self._identify_oracle_root_causes(graph, fn_node)
                    )
        else:
            # Try all pattern detectors
            root_causes.extend(self._identify_reentrancy_root_causes(graph, fn_node))
            root_causes.extend(self._identify_access_control_root_causes(graph, fn_node))
            root_causes.extend(self._identify_oracle_root_causes(graph, fn_node))

        return root_causes

    def _identify_reentrancy_root_causes(
        self,
        graph: CausalGraph,
        fn_node: "Node",
    ) -> List[RootCause]:
        """Identify root causes specific to reentrancy."""
        root_causes = []

        # Find external call and state write nodes
        external_calls = [n for n in graph.nodes.values()
                         if n.operation in ["TRANSFERS_VALUE_OUT", "CALLS_EXTERNAL"]]
        state_writes = [n for n in graph.nodes.values()
                       if n.operation == "WRITES_USER_BALANCE"]

        for ext_call in external_calls:
            for write in state_writes:
                # Check if external call comes before write (wrong order)
                ext_idx = list(graph.nodes.keys()).index(ext_call.id)
                write_idx = list(graph.nodes.keys()).index(write.id)

                if ext_idx < write_idx:
                    root_causes.append(RootCause(
                        id=f"rc_reentrancy_{ext_call.id}_{write.id}",
                        description="External call before state update violates CEI pattern",
                        cause_type="ordering_violation",
                        severity="critical",
                        causal_path=[ext_call.id, write.id],
                        contributing_factors=[
                            "No reentrancy guard",
                            "Uses callback-capable transfer",
                        ],
                        intervention="Move state update before external call (CEI pattern)",
                        intervention_confidence=0.95,
                        alternative_interventions=[
                            "Add nonReentrant modifier",
                            "Use pull payment pattern",
                            "Use transfer() instead of call{value:}() for simple transfers",
                        ],
                        evidence=[
                            f"External call at operation {ext_idx}",
                            f"State write at operation {write_idx}",
                            "Attacker callback can re-enter before state update",
                        ],
                        confidence=0.9,
                        related_cwes=["CWE-841", "CWE-696"],
                        related_patterns=["reentrancy_classic", "reentrancy_cross_function"],
                    ))

        # Check for missing reentrancy guard
        if not fn_node.properties.get("has_reentrancy_guard") and (external_calls and state_writes):
            root_causes.append(RootCause(
                id=f"rc_missing_guard_{fn_node.id}",
                description="Function lacks reentrancy protection",
                cause_type="missing_guard",
                severity="high",
                causal_path=[fn_node.id],
                contributing_factors=[
                    "Function has external calls",
                    "Function modifies state",
                ],
                intervention="Add nonReentrant modifier",
                intervention_confidence=0.9,
                alternative_interventions=[
                    "Implement custom reentrancy lock",
                    "Use OpenZeppelin ReentrancyGuard",
                ],
                evidence=[
                    "No nonReentrant modifier found",
                    "Function is externally callable",
                ],
                confidence=0.85,
                related_cwes=["CWE-841"],
                related_patterns=["reentrancy_classic"],
            ))

        return root_causes

    def _identify_access_control_root_causes(
        self,
        graph: CausalGraph,
        fn_node: "Node",
    ) -> List[RootCause]:
        """Identify root causes specific to access control."""
        root_causes = []

        if not fn_node.properties.get("has_access_gate"):
            # Check what privileged operations are performed
            privileged_ops = []
            if fn_node.properties.get("writes_privileged_state"):
                privileged_ops.append("writes privileged state")
            if fn_node.properties.get("modifies_owner"):
                privileged_ops.append("modifies ownership")
            if fn_node.properties.get("modifies_roles"):
                privileged_ops.append("modifies roles")

            if privileged_ops:
                root_causes.append(RootCause(
                    id=f"rc_access_{fn_node.id}",
                    description="Privileged function lacks access control",
                    cause_type="missing_guard",
                    severity="critical",
                    causal_path=[fn_node.id],
                    contributing_factors=privileged_ops,
                    intervention="Add onlyOwner or role-based access modifier",
                    intervention_confidence=0.95,
                    alternative_interventions=[
                        "Use OpenZeppelin Ownable",
                        "Use OpenZeppelin AccessControl",
                        "Implement custom access control",
                    ],
                    evidence=[
                        "No access control modifier found",
                        f"Function performs: {', '.join(privileged_ops)}",
                    ],
                    confidence=0.9,
                    related_cwes=["CWE-862", "CWE-863", "CWE-284"],
                    related_patterns=["unprotected_function", "missing_access_control"],
                ))

        return root_causes

    def _identify_oracle_root_causes(
        self,
        graph: CausalGraph,
        fn_node: "Node",
    ) -> List[RootCause]:
        """Identify root causes specific to oracle manipulation."""
        root_causes = []

        if fn_node.properties.get("reads_oracle_price"):
            if not fn_node.properties.get("has_staleness_check"):
                root_causes.append(RootCause(
                    id=f"rc_oracle_stale_{fn_node.id}",
                    description="Oracle price used without staleness check",
                    cause_type="missing_validation",
                    severity="high",
                    causal_path=[fn_node.id],
                    contributing_factors=[
                        "Reads oracle price",
                        "No roundId/timestamp validation",
                    ],
                    intervention="Add staleness check on oracle response",
                    intervention_confidence=0.9,
                    alternative_interventions=[
                        "Check updatedAt against threshold",
                        "Verify roundId is recent",
                        "Use TWAP instead of spot price",
                    ],
                    evidence=[
                        "Oracle price read detected",
                        "No staleness validation found",
                    ],
                    confidence=0.85,
                    related_cwes=["CWE-20", "CWE-682"],
                    related_patterns=["stale_oracle_data"],
                ))

        return root_causes

    def _find_intervention_points(
        self,
        graph: CausalGraph,
        root_causes: List[RootCause],
    ) -> List[InterventionPoint]:
        """
        Find points where intervention would break causal chains.

        For each root cause, identify the most effective intervention.
        """
        interventions = []

        for rc in root_causes:
            if rc.cause_type == "ordering_violation":
                # For ordering, intervention is reordering
                interventions.append(InterventionPoint(
                    id=f"int_reorder_{rc.id}",
                    node_id=rc.causal_path[0],
                    edge_id=None,
                    intervention_type="reorder",
                    description="Reorder operations to follow CEI pattern",
                    code_suggestion="// Move state update before external call\nbalances[msg.sender] = 0;\n(bool success,) = msg.sender.call{value: amount}(\"\");",
                    blocks_causes=[rc.id],
                    impact_score=0.95,
                    side_effects=[],
                    complexity="moderate",
                ))

            elif rc.cause_type == "missing_guard":
                interventions.append(InterventionPoint(
                    id=f"int_guard_{rc.id}",
                    node_id=rc.causal_path[0],
                    edge_id=None,
                    intervention_type="add_guard",
                    description="Add protective modifier",
                    code_suggestion="// Add modifier\nfunction withdraw() external nonReentrant {",
                    blocks_causes=[rc.id],
                    impact_score=0.9,
                    side_effects=["Gas overhead from guard"],
                    complexity="trivial",
                ))

            elif rc.cause_type == "missing_validation":
                interventions.append(InterventionPoint(
                    id=f"int_validate_{rc.id}",
                    node_id=rc.causal_path[0],
                    edge_id=None,
                    intervention_type="add_check",
                    description="Add validation check",
                    code_suggestion="require(updatedAt > block.timestamp - STALENESS_THRESHOLD, \"Stale price\");",
                    blocks_causes=[rc.id],
                    impact_score=0.85,
                    side_effects=["Reverts on stale data"],
                    complexity="trivial",
                ))

        return interventions

    def generate_explanation(
        self,
        graph: CausalGraph,
        root_causes: List[RootCause],
        interventions: List[InterventionPoint],
    ) -> str:
        """Generate human-readable causal explanation."""
        lines = ["# Causal Analysis Report\n"]

        # Root causes section
        if root_causes:
            lines.append("## Root Causes\n")
            for i, rc in enumerate(root_causes, 1):
                lines.append(f"### {i}. {rc.description}")
                lines.append(f"- **Type**: {rc.cause_type}")
                lines.append(f"- **Severity**: {rc.severity}")
                lines.append(f"- **Confidence**: {rc.confidence:.0%}")
                lines.append(f"- **Causal Path**: {' → '.join(rc.causal_path)}")
                lines.append(f"- **Contributing Factors**: {', '.join(rc.contributing_factors)}")
                lines.append(f"\n**Evidence**:")
                for ev in rc.evidence:
                    lines.append(f"  - {ev}")
                lines.append(f"\n**Related CWEs**: {', '.join(rc.related_cwes)}")
                lines.append("")
        else:
            lines.append("## Root Causes\n")
            lines.append("No root causes identified. Function appears secure.\n")

        # Interventions section
        if interventions:
            lines.append("\n## Recommended Fixes\n")
            for i, int_point in enumerate(interventions, 1):
                lines.append(f"### Fix {i}: {int_point.description}")
                lines.append(f"- **Type**: {int_point.intervention_type}")
                lines.append(f"- **Impact**: {int_point.impact_score:.0%} effective")
                lines.append(f"- **Complexity**: {int_point.complexity}")
                if int_point.code_suggestion:
                    lines.append(f"\n```solidity\n{int_point.code_suggestion}\n```")
                if int_point.side_effects:
                    lines.append(f"\n**Side Effects**: {', '.join(int_point.side_effects)}")
                lines.append("")

        return "\n".join(lines)

    def _compute_centrality(self, graph: CausalGraph) -> None:
        """Compute centrality scores for all nodes."""
        for node_id, node in graph.nodes.items():
            # Simple centrality: number of paths through node
            ancestors = graph.get_ancestors(node_id)
            descendants = graph.get_descendants(node_id)
            node.centrality_score = len(ancestors) * len(descendants) / max(len(graph.nodes), 1)

    def _compute_confidence(self, root_causes: List[RootCause]) -> float:
        """Compute overall analysis confidence."""
        if not root_causes:
            return 0.0
        return sum(rc.confidence for rc in root_causes) / len(root_causes)

    def _is_controllable(self, op: OperationInfo) -> bool:
        """Check if operation can be influenced by attacker."""
        return op.operation in [
            "TRANSFERS_VALUE_OUT",
            "CALLS_EXTERNAL",
            "VALIDATES_INPUT",
        ]

    def _is_observable(self, op: OperationInfo) -> bool:
        """Check if operation result is observable by attacker."""
        return op.operation in [
            "READS_USER_BALANCE",
            "READS_ORACLE",
        ]

    def _load_root_cause_templates(self) -> Dict:
        """Load templates for common root causes."""
        return {
            "reentrancy": {
                "pattern": ["EXTERNAL", "WRITE"],
                "cause": "ordering_violation",
            },
            "access_control": {
                "pattern": ["PRIVILEGED_WRITE"],
                "cause": "missing_guard",
            },
        }
