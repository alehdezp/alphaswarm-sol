# [P3-T2] Causal Reasoning Engine

**Phase**: 3 - Iterative + Causal
**Task ID**: P3-T2
**Status**: NOT_STARTED
**Priority**: HIGH
**Estimated Effort**: 4-5 days
**Actual Effort**: -

---

## Executive Summary

Implement causal reasoning that explains **WHY vulnerabilities exist** and **WHAT would fix them**. This goes beyond pattern matching to build actual causal graphs from operation dependencies, identify root causes, find intervention points, and generate counterfactuals.

**Research Basis**: ContractLLM (PACIS 2025) achieved 61.5-point improvement in line-level reasoning through causal analysis. Graph-R1 (NeurIPS 2024) showed causal graphs dramatically improve reasoning accuracy.

**Why This Matters**: Security auditors need to understand causality, not just correlation. "This external call causes a reentrancy risk because the state update depends on it" is more actionable than "pattern matched reentrancy".

---

## Dependencies

### Required Before Starting
- [ ] [P3-T1] Iterative Query Engine - Provides multi-round context
- [ ] [P0-T3] Cross-Graph Linker - Provides cross-graph edges

### Blocks These Tasks
- [P3-T3] Counterfactual Generator - Uses causal graphs
- [P3-T4] Attack Path Synthesis - Uses causal ordering

---

## Objectives

### Primary Objectives
1. Build causal graphs from operation dependencies (data flow + control flow)
2. Identify root causes of vulnerabilities using graph traversal
3. Find intervention points (where fixes should be applied)
4. Generate causal explanation chains for findings
5. Compute causal contribution scores

### Stretch Goals
1. Integrate with LLM for natural language causal explanations
2. Compute counterfactual impact ("removing X would prevent Y")
3. Support multi-function causal paths (cross-function causality)

---

## Success Criteria

### Must Have (Definition of Done)
- [ ] `CausalNode` and `CausalEdge` dataclasses
- [ ] `CausalGraph` construction from BSKG behavioral signatures
- [ ] `RootCause` identification for reentrancy, access control, oracle patterns
- [ ] `InterventionPoint` suggestions for each root cause
- [ ] `generate_explanation()` produces human-readable output
- [ ] 95%+ test coverage on new code
- [ ] Documentation in docs/reference/causal-engine.md

### Should Have
- [ ] Multi-function causal path analysis
- [ ] Causal contribution scoring (how much each factor contributes)
- [ ] LLM-enhanced natural language explanations

### Nice to Have
- [ ] Interactive causal graph visualization export
- [ ] Causal impact simulation

---

## Technical Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CAUSAL REASONING ENGINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INPUT                                                                       │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐    │
│  │   Function Node    │  │   Vulnerability    │  │   Cross-Graph      │    │
│  │   (VKG)            │  │   Candidate        │  │   Context          │    │
│  └─────────┬──────────┘  └─────────┬──────────┘  └─────────┬──────────┘    │
│            │                       │                       │                │
│            └───────────────────────┼───────────────────────┘                │
│                                    │                                        │
│  CAUSAL GRAPH CONSTRUCTION         ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │   1. Extract Operations from Behavioral Signature                    │   │
│  │      "R:bal→X:out→W:bal" → [READ_BAL, EXT_CALL, WRITE_BAL]          │   │
│  │                                                                       │   │
│  │   2. Build Data Flow Dependencies                                    │   │
│  │      READ_BAL ──data──► EXT_CALL (uses balance)                     │   │
│  │      READ_BAL ──data──► WRITE_BAL (uses balance)                    │   │
│  │                                                                       │   │
│  │   3. Build Control Flow Dependencies                                 │   │
│  │      CHECK ──control──► EXT_CALL (guarded by check)                 │   │
│  │      EXT_CALL ──sequence──► WRITE_BAL (happens after)               │   │
│  │                                                                       │   │
│  │   4. Add External Influence Edges                                    │   │
│  │      EXT_CALL ──influence──► WRITE_BAL (can affect outcome)         │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ROOT CAUSE ANALYSIS               ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │   Backward Traversal from Vulnerability Node                         │   │
│  │                                                                       │   │
│  │   VULNERABILITY: state_write_after_external_call                     │   │
│  │          │                                                            │   │
│  │          ▼                                                            │   │
│  │   DIRECT CAUSE: EXT_CALL happens before WRITE_BAL                    │   │
│  │          │                                                            │   │
│  │          ▼                                                            │   │
│  │   ROOT CAUSE: Missing reentrancy guard + Wrong operation order       │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  INTERVENTION POINTS               ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │   Option 1: Add reentrancy guard (blocks external influence)         │   │
│  │   Option 2: Reorder operations (WRITE_BAL before EXT_CALL)           │   │
│  │   Option 3: Use pull pattern (remove direct transfer)                │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  OUTPUT                            ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  CausalAnalysis                                                     │    │
│  │    ├── causal_graph: CausalGraph                                   │    │
│  │    ├── root_causes: List[RootCause]                                │    │
│  │    ├── intervention_points: List[InterventionPoint]                │    │
│  │    └── explanation: str                                            │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### New Files
- `src/true_vkg/reasoning/__init__.py` - Package init
- `src/true_vkg/reasoning/causal.py` - Main causal engine
- `src/true_vkg/reasoning/causal_graph.py` - Graph data structures
- `src/true_vkg/reasoning/root_cause.py` - Root cause analysis
- `src/true_vkg/reasoning/intervention.py` - Intervention point finder
- `tests/test_3.5/test_causal_engine.py` - Tests

### Key Data Structures

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum


class CausalRelationType(Enum):
    """Types of causal relationships."""
    DATA_FLOW = "data_flow"           # X provides data used by Y
    CONTROL_FLOW = "control_flow"     # X controls whether Y executes
    SEQUENCE = "sequence"              # X happens before Y (temporal)
    EXTERNAL_INFLUENCE = "external"    # X can affect Y through external means
    STATE_DEPENDENCY = "state_dep"     # Y depends on state modified by X


@dataclass
class CausalNode:
    """
    Node in causal graph representing an operation or condition.

    Maps to BSKG semantic operations and code locations.
    """
    id: str
    operation: str  # Semantic operation (e.g., "TRANSFERS_VALUE_OUT")
    description: str  # Human-readable description

    # Code location
    line_start: int
    line_end: int
    code_snippet: Optional[str] = None

    # Causal properties
    is_controllable: bool = False  # Can attacker control this?
    is_observable: bool = False    # Can attacker observe this?
    is_root_candidate: bool = False  # Could be a root cause?

    # Graph connectivity
    causes: List[str] = field(default_factory=list)  # Nodes that cause this
    effects: List[str] = field(default_factory=list)  # Nodes this causes

    # Importance scoring
    centrality_score: float = 0.0  # How central in causal chain


@dataclass
class CausalEdge:
    """Edge representing a causal relationship."""
    source_id: str
    target_id: str
    relation_type: CausalRelationType

    # Strength of causal relationship
    strength: float  # 0.0 to 1.0

    # Evidence for this causal link
    evidence: List[str] = field(default_factory=list)

    # Can this edge be broken (intervention point)?
    is_breakable: bool = False
    break_methods: List[str] = field(default_factory=list)


@dataclass
class CausalGraph:
    """
    Directed acyclic graph of causal relationships.

    Built from BSKG behavioral signatures and enriched with
    data flow and control flow information.
    """
    id: str
    focal_node_id: str  # The function being analyzed
    vulnerability_id: Optional[str]  # The vulnerability this explains

    nodes: Dict[str, CausalNode] = field(default_factory=dict)
    edges: List[CausalEdge] = field(default_factory=list)

    # Precomputed paths
    root_to_vuln_paths: List[List[str]] = field(default_factory=list)

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
    cause_type: str  # "ordering_violation", "missing_guard", "wrong_assumption"
    severity: str  # "critical", "high", "medium", "low"

    # Causal path
    causal_path: List[str]  # Path from root to vulnerability manifestation
    contributing_factors: List[str]  # Other factors that enable this

    # Intervention
    intervention: str  # What would fix this
    intervention_confidence: float  # How confident we are this would fix it
    alternative_interventions: List[str] = field(default_factory=list)

    # Evidence
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0

    # Links
    related_cwes: List[str] = field(default_factory=list)
    related_patterns: List[str] = field(default_factory=list)


@dataclass
class InterventionPoint:
    """A point where intervention would break the causal chain."""
    id: str
    node_id: str  # The causal node where to intervene
    edge_id: Optional[str]  # The edge being broken (if applicable)

    # What to do
    intervention_type: str  # "add_guard", "reorder", "add_check", "remove"
    description: str
    code_suggestion: Optional[str]  # Suggested code change

    # Impact
    blocks_causes: List[str]  # Which root causes this would block
    impact_score: float  # How effective (0.0 to 1.0)

    # Trade-offs
    side_effects: List[str]  # Potential negative impacts
    complexity: str  # "trivial", "moderate", "complex"


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


class CausalReasoningEngine:
    """
    Builds causal graphs and identifies root causes.

    The engine works by:
    1. Extracting operations from behavioral signatures
    2. Building causal edges from data/control flow
    3. Identifying root causes via backward traversal
    4. Finding intervention points that break causal chains
    """

    def __init__(self, code_kg: "KnowledgeGraph", llm_client=None):
        self.code_kg = code_kg
        self.llm = llm_client  # Optional for enhanced explanations

        # Root cause templates for common vulnerability patterns
        self._root_cause_templates = self._load_root_cause_templates()

    def analyze(
        self,
        fn_node: "Node",
        vulnerability: Optional["VulnerabilityCandidate"] = None,
    ) -> CausalAnalysis:
        """
        Perform causal analysis on a function.

        Args:
            fn_node: The function node from VKG
            vulnerability: Optional vulnerability candidate providing context

        Returns:
            CausalAnalysis with graph, root causes, and interventions
        """
        import time
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
        vulnerability: Optional["VulnerabilityCandidate"] = None,
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
            vulnerability_id=vulnerability.id if vulnerability else None,
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

    def _extract_operations(self, fn_node: "Node") -> List["OperationInfo"]:
        """Extract operations from behavioral signature."""
        sig = fn_node.properties.get("behavioral_signature", "")
        semantic_ops = fn_node.properties.get("semantic_operations", [])

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
            "A:div": ("PERFORMS_DIVISION", "Division operation"),
            "V:in": ("VALIDATES_INPUT", "Input validation"),
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
        # If a balance read flows to an external call and a write,
        # add data flow edges

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

    def _add_sequence_edges(self, graph: CausalGraph, operations: List["OperationInfo"]) -> None:
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
        vulnerability: Optional["VulnerabilityCandidate"],
    ) -> List[RootCause]:
        """
        Identify root causes by backward traversal from vulnerability.

        Uses pattern-specific templates and general causal analysis.
        """
        root_causes = []

        # Pattern-specific root cause detection
        if vulnerability:
            for pattern in vulnerability.attack_patterns:
                if "reentrancy" in pattern.id.lower():
                    root_causes.extend(
                        self._identify_reentrancy_root_causes(graph, fn_node)
                    )
                elif "access" in pattern.id.lower():
                    root_causes.extend(
                        self._identify_access_control_root_causes(graph, fn_node)
                    )
                elif "oracle" in pattern.id.lower():
                    root_causes.extend(
                        self._identify_oracle_root_causes(graph, fn_node)
                    )
                elif "first_depositor" in pattern.id.lower():
                    root_causes.extend(
                        self._identify_first_depositor_root_causes(graph, fn_node)
                    )

        # General root cause detection (backward traversal)
        if not root_causes:
            root_causes = self._general_root_cause_analysis(graph)

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
        if not fn_node.properties.get("has_reentrancy_guard"):
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

    def _identify_first_depositor_root_causes(
        self,
        graph: CausalGraph,
        fn_node: "Node",
    ) -> List[RootCause]:
        """Identify root causes specific to first depositor attack."""
        root_causes = []

        if fn_node.properties.get("uses_share_calculation"):
            root_causes.append(RootCause(
                id=f"rc_first_depositor_{fn_node.id}",
                description="Share calculation vulnerable to inflation attack",
                cause_type="economic_vulnerability",
                severity="high",
                causal_path=[fn_node.id],
                contributing_factors=[
                    "Division by total supply/assets",
                    "No minimum deposit amount",
                    "No virtual offset",
                ],
                intervention="Add virtual offset to share calculation",
                intervention_confidence=0.85,
                alternative_interventions=[
                    "Require minimum first deposit",
                    "Use dead shares pattern",
                    "Initialize with non-zero shares",
                ],
                evidence=[
                    "Share calculation with division detected",
                    "Vulnerable to share inflation",
                ],
                confidence=0.8,
                related_cwes=["CWE-682", "CWE-190"],
                related_patterns=["first_depositor_attack"],
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

        # Interventions section
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

    def _is_controllable(self, op: "OperationInfo") -> bool:
        """Check if operation can be influenced by attacker."""
        return op.operation in [
            "TRANSFERS_VALUE_OUT",
            "CALLS_EXTERNAL",
            "VALIDATES_INPUT",
        ]

    def _is_observable(self, op: "OperationInfo") -> bool:
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


@dataclass
class OperationInfo:
    """Information about an operation."""
    operation: str
    description: str
    line: int
    index: int
```

---

## Implementation Plan

### Phase 1: Data Structures (1 day)
- [ ] Create `src/true_vkg/reasoning/__init__.py`
- [ ] Implement `CausalNode`, `CausalEdge` dataclasses
- [ ] Implement `CausalGraph` with traversal methods
- [ ] Implement `RootCause`, `InterventionPoint` dataclasses
- [ ] Write unit tests for data structures
- **Checkpoint**: Can create and traverse causal graphs

### Phase 2: Causal Graph Construction (1.5 days)
- [ ] Implement `_extract_operations()` from behavioral signature
- [ ] Implement `_add_data_flow_edges()`
- [ ] Implement `_add_control_flow_edges()`
- [ ] Implement `_add_sequence_edges()`
- [ ] Implement `_add_external_influence_edges()`
- [ ] Write tests for each edge type
- **Checkpoint**: Can build complete causal graphs

### Phase 3: Root Cause Analysis (1.5 days)
- [ ] Implement `_identify_reentrancy_root_causes()`
- [ ] Implement `_identify_access_control_root_causes()`
- [ ] Implement `_identify_oracle_root_causes()`
- [ ] Implement `_identify_first_depositor_root_causes()`
- [ ] Implement `_general_root_cause_analysis()` fallback
- [ ] Write tests for each root cause type
- **Checkpoint**: Can identify root causes for common patterns

### Phase 4: Interventions & Explanations (1 day)
- [ ] Implement `_find_intervention_points()`
- [ ] Implement `generate_explanation()`
- [ ] Add code suggestion generation
- [ ] Integration tests with real VKG
- [ ] Performance benchmarks
- **Checkpoint**: Full causal analysis working

---

## Validation Tests

### Unit Tests

```python
# tests/test_3.5/test_causal_engine.py

import pytest
from true_vkg.reasoning.causal import (
    CausalReasoningEngine,
    CausalGraph,
    CausalNode,
    CausalEdge,
    RootCause,
    CausalRelationType,
)


class TestCausalGraphConstruction:
    """Test causal graph building."""

    def test_extract_operations_from_signature(self):
        """Test extracting operations from behavioral signature."""
        engine = CausalReasoningEngine(mock_kg)

        mock_fn = MockFunctionNode(
            behavioral_signature="R:bal→X:out→W:bal",
        )

        ops = engine._extract_operations(mock_fn)

        assert len(ops) == 3
        assert ops[0].operation == "READS_USER_BALANCE"
        assert ops[1].operation == "TRANSFERS_VALUE_OUT"
        assert ops[2].operation == "WRITES_USER_BALANCE"

    def test_build_causal_graph(self):
        """Test building complete causal graph."""
        engine = CausalReasoningEngine(mock_kg)

        mock_fn = MockFunctionNode(
            id="fn_withdraw",
            behavioral_signature="R:bal→X:out→W:bal",
            properties={
                "has_reentrancy_guard": False,
                "state_write_after_external_call": True,
            }
        )

        graph = engine.build_causal_graph(mock_fn, None)

        assert len(graph.nodes) == 3
        assert len(graph.edges) > 0

        # Should have sequence edges
        sequence_edges = [e for e in graph.edges if e.relation_type == CausalRelationType.SEQUENCE]
        assert len(sequence_edges) == 2

        # Should have external influence edge
        influence_edges = [e for e in graph.edges if e.relation_type == CausalRelationType.EXTERNAL_INFLUENCE]
        assert len(influence_edges) > 0

    def test_graph_traversal(self):
        """Test graph traversal methods."""
        graph = CausalGraph(id="test", focal_node_id="fn")

        # Add nodes
        for i in range(4):
            graph.add_node(CausalNode(
                id=f"n{i}",
                operation=f"OP_{i}",
                description=f"Op {i}",
                line_start=i,
                line_end=i,
            ))

        # n0 → n1 → n2
        #      ↘ n3
        graph.add_edge(CausalEdge(source_id="n0", target_id="n1", relation_type=CausalRelationType.SEQUENCE, strength=1.0))
        graph.add_edge(CausalEdge(source_id="n1", target_id="n2", relation_type=CausalRelationType.SEQUENCE, strength=1.0))
        graph.add_edge(CausalEdge(source_id="n1", target_id="n3", relation_type=CausalRelationType.SEQUENCE, strength=1.0))

        # Test ancestors
        ancestors = graph.get_ancestors("n2")
        assert "n0" in ancestors
        assert "n1" in ancestors

        # Test descendants
        descendants = graph.get_descendants("n0")
        assert "n1" in descendants
        assert "n2" in descendants
        assert "n3" in descendants

        # Test path finding
        paths = graph.find_paths("n0", "n2")
        assert len(paths) == 1
        assert paths[0] == ["n0", "n1", "n2"]


class TestRootCauseIdentification:
    """Test root cause detection."""

    @pytest.fixture
    def engine(self):
        return CausalReasoningEngine(mock_kg)

    def test_identify_reentrancy_root_cause(self, engine):
        """Test detection of reentrancy root cause."""
        mock_fn = MockFunctionNode(
            id="fn_withdraw_vuln",
            behavioral_signature="R:bal→X:out→W:bal",
            properties={
                "has_reentrancy_guard": False,
                "state_write_after_external_call": True,
            }
        )

        mock_vuln = MockVulnerability(
            attack_patterns=[MockPattern(id="reentrancy_classic")]
        )

        analysis = engine.analyze(mock_fn, mock_vuln)

        assert len(analysis.root_causes) > 0
        ordering_causes = [rc for rc in analysis.root_causes if rc.cause_type == "ordering_violation"]
        assert len(ordering_causes) > 0

        # Should have intervention
        assert len(analysis.intervention_points) > 0

    def test_identify_missing_guard_root_cause(self, engine):
        """Test detection of missing guard."""
        mock_fn = MockFunctionNode(
            id="fn_withdraw_no_guard",
            behavioral_signature="R:bal→X:out→W:bal",
            properties={
                "has_reentrancy_guard": False,
            }
        )

        mock_vuln = MockVulnerability(
            attack_patterns=[MockPattern(id="reentrancy_classic")]
        )

        analysis = engine.analyze(mock_fn, mock_vuln)

        guard_causes = [rc for rc in analysis.root_causes if rc.cause_type == "missing_guard"]
        assert len(guard_causes) > 0
        assert "nonReentrant" in guard_causes[0].intervention

    def test_identify_access_control_root_cause(self, engine):
        """Test detection of missing access control."""
        mock_fn = MockFunctionNode(
            id="fn_set_owner",
            behavioral_signature="M:own",
            properties={
                "has_access_gate": False,
                "writes_privileged_state": True,
                "modifies_owner": True,
            }
        )

        mock_vuln = MockVulnerability(
            attack_patterns=[MockPattern(id="missing_access_control")]
        )

        analysis = engine.analyze(mock_fn, mock_vuln)

        access_causes = [rc for rc in analysis.root_causes if "access" in rc.id]
        assert len(access_causes) > 0
        assert "onlyOwner" in access_causes[0].intervention or "access" in access_causes[0].intervention.lower()

    def test_no_root_cause_for_safe_code(self, engine):
        """Test that safe code has no critical root causes."""
        mock_fn = MockFunctionNode(
            id="fn_withdraw_safe",
            behavioral_signature="R:bal→W:bal→X:out",  # Correct CEI order
            properties={
                "has_reentrancy_guard": True,
            }
        )

        analysis = engine.analyze(mock_fn, None)

        # Should have no ordering violations
        ordering_causes = [rc for rc in analysis.root_causes if rc.cause_type == "ordering_violation"]
        assert len(ordering_causes) == 0


class TestExplanationGeneration:
    """Test human-readable explanation generation."""

    def test_generate_explanation(self):
        """Test explanation generation."""
        engine = CausalReasoningEngine(mock_kg)

        mock_fn = MockFunctionNode(
            id="fn_vuln",
            behavioral_signature="R:bal→X:out→W:bal",
            properties={
                "has_reentrancy_guard": False,
                "state_write_after_external_call": True,
            }
        )

        mock_vuln = MockVulnerability(
            attack_patterns=[MockPattern(id="reentrancy_classic")]
        )

        analysis = engine.analyze(mock_fn, mock_vuln)

        # Should have explanation
        assert analysis.explanation is not None
        assert len(analysis.explanation) > 100

        # Explanation should contain key elements
        assert "Root Cause" in analysis.explanation
        assert "Fix" in analysis.explanation or "Intervention" in analysis.explanation
        assert "CEI" in analysis.explanation or "external call" in analysis.explanation.lower()


class TestIntegrationWithRealVKG:
    """Integration tests with real BSKG nodes."""

    def test_with_real_vulnerable_contract(self):
        """Test causal analysis on real vulnerable contract."""
        from tests.graph_cache import load_graph

        graph = load_graph("TokenVault")
        engine = CausalReasoningEngine(graph)

        # Find withdraw functions
        withdraw_fns = [n for n in graph.nodes.values()
                       if n.type == "Function" and "withdraw" in n.label.lower()]

        for fn in withdraw_fns:
            analysis = engine.analyze(fn, None)

            # Should produce analysis
            assert analysis is not None
            assert analysis.causal_graph is not None

            # Should have reasonable timing
            assert analysis.analysis_time_ms < 1000  # Under 1 second


### Performance Tests

```python
def test_causal_analysis_performance():
    """Test that causal analysis is fast enough."""
    import time

    engine = CausalReasoningEngine(mock_kg)

    # Create varied mock functions
    functions = []
    for i in range(50):
        sig = random.choice([
            "R:bal→X:out→W:bal",
            "C:perm→W:bal→X:out",
            "R:orc→A:div→X:out",
            "V:in→M:own",
        ])
        functions.append(MockFunctionNode(
            id=f"fn_{i}",
            behavioral_signature=sig,
        ))

    start = time.time()
    for fn in functions:
        engine.analyze(fn, None)
    elapsed = time.time() - start

    # Should complete 50 analyses in < 5 seconds (100ms each)
    assert elapsed < 5.0, f"Too slow: {elapsed:.2f}s for 50 analyses"
```

### The Ultimate Test

```python
def test_ultimate_causal_explanation():
    """
    Ultimate test: Causal engine should explain WHY reentrancy works
    and WHAT would fix it.

    This proves the engine enables actionable vulnerability understanding.
    """
    engine = CausalReasoningEngine(mock_kg)

    # The DAO-style vulnerable function
    dao_fn = MockFunctionNode(
        id="fn_withdraw_dao",
        behavioral_signature="R:bal→V:in→X:out→W:bal",
        properties={
            "visibility": "public",
            "has_reentrancy_guard": False,
            "state_write_after_external_call": True,
            "transfers_eth": True,
        }
    )

    dao_vuln = MockVulnerability(
        id="vuln_reentrancy",
        attack_patterns=[MockPattern(id="reentrancy_classic")],
    )

    analysis = engine.analyze(dao_fn, dao_vuln)

    # 1. Should identify ordering as root cause
    ordering_causes = [rc for rc in analysis.root_causes if rc.cause_type == "ordering_violation"]
    assert len(ordering_causes) > 0, "Should identify ordering violation"

    # 2. Should explain the causal path
    rc = ordering_causes[0]
    assert len(rc.causal_path) >= 2, "Should have causal path"
    assert "external" in rc.description.lower() or "call" in rc.description.lower()

    # 3. Should provide fix recommendation
    assert "CEI" in rc.intervention or "before" in rc.intervention

    # 4. Should link to CWE
    assert any("841" in cwe for cwe in rc.related_cwes)

    # 5. Should have interventions
    assert len(analysis.intervention_points) > 0

    # 6. Should generate readable explanation
    assert "Root Cause" in analysis.explanation
    assert len(analysis.explanation) > 200

    print("SUCCESS: Causal engine explains reentrancy")
    print(f"Root Cause: {rc.description}")
    print(f"Fix: {rc.intervention}")
    print(f"Confidence: {rc.confidence:.0%}")
```

---

## Metrics & Measurement

### Before Implementation (Baseline)
| Metric | Value | How Measured |
|--------|-------|--------------|
| Root cause explanations | 0 | Manual count |
| Fix recommendations | 0 | Manual count |
| Causal path analysis | N/A | Not available |

### After Implementation (Results)
| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| Root cause accuracy | 85%+ | - | - |
| Fix recommendation relevance | 80%+ | - | - |
| Analysis time per function | <200ms | - | - |
| Explanation clarity (manual review) | Good | - | - |

---

## Risk Assessment

### Technical Risks
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Causal graph too complex | MEDIUM | MEDIUM | Limit depth, prune unrelated edges |
| Root cause templates incomplete | HIGH | MEDIUM | Start with common patterns, expand |
| False causal attribution | HIGH | MEDIUM | Validate with known vulnerabilities |

### Dependency Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| BSKG behavioral signatures incomplete | HIGH | Work with builder team to enhance |
| Iterative engine not ready | MEDIUM | Can test standalone first |

---

## Critical Self-Analysis

### What Could Go Wrong
1. **Causal attribution incorrect**: Identifies wrong root cause → misleading fixes
   - Detection: Validate on known vulnerabilities with documented root causes
   - Mitigation: Use conservative attribution, require multiple evidence

2. **Too many root causes**: Every factor listed → not actionable
   - Detection: Output review shows excessive causes
   - Mitigation: Rank by contribution, show top 3

3. **Fix recommendations wrong**: Could introduce new bugs
   - Detection: Manual review of fix suggestions
   - Mitigation: Provide multiple options, mark confidence

### Assumptions Being Made
1. **Behavioral signatures capture causality**: Operations in signature reflect actual causal structure
   - Validation: Compare with CFG analysis

2. **Common patterns cover most cases**: Template-based detection sufficient
   - Validation: Measure coverage on diverse vulnerabilities

### Questions to Answer During Implementation
1. How to handle multi-function causal chains?
2. Should causal strength be learned or hand-tuned?
3. How to present uncertainty in causal claims?

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
| 2026-01-03 | Enhanced with full detail | Claude |
