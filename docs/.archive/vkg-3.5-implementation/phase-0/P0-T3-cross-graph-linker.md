# [P0-T3] Cross-Graph Linker

**Phase**: 0 - Knowledge Foundation
**Task ID**: P0-T3
**Status**: NOT_STARTED
**Priority**: CRITICAL
**Estimated Effort**: 4-5 days
**Actual Effort**: -

---

## Executive Summary

Build the Cross-Graph Linker that connects the three knowledge graphs (Domain, Code, Adversarial) with semantic relationships. This is **THE KEY INNOVATION** that enables true business logic detection: a function that is `SIMILAR_TO` an attack pattern AND `VIOLATES` a specification AND has no `MITIGATES` edge is high-confidence vulnerable.

**Why This Matters**: Individual knowledge graphs are useful but limited. The magic happens at the intersections - where code behavior deviates from specs AND matches exploit patterns.

---

## Dependencies

### Required Before Starting
- [ ] [P0-T1] Domain Knowledge Graph - Need specs to link against
- [ ] [P0-T2] Adversarial Knowledge Graph - Need patterns to link against

### Blocks These Tasks
- [P1-T2] LLM Intent Annotator - Uses links for context
- [P2-T1] Agent Router - Needs cross-graph context per agent
- [P2-T5] Adversarial Arbiter - Uses link analysis for verdicts
- [P3-T1] Iterative Query Engine - Traverses cross-graph links

---

## Objectives

### Primary Objectives
1. Define cross-graph edge types (IMPLEMENTS, VIOLATES, SIMILAR_TO, MITIGATES, ENABLES)
2. Implement linker that creates edges between all three KGs
3. Build query interface for vulnerability candidate detection
4. Enable composite queries ("functions that SIMILAR_TO pattern AND VIOLATES spec")
5. Create confidence scoring for cross-graph relationships

### Stretch Goals
1. Incremental link updates (don't rebuild all links on small changes)
2. Link explanation generation (why this edge exists)
3. Transitive relationship inference

---

## Success Criteria

### Must Have (Definition of Done)
- [ ] `CrossGraphEdge` dataclass with all relation types
- [ ] `CrossGraphLinker` class with link creation methods
- [ ] `VulnerabilityCandidate` dataclass for query results
- [ ] `link_function_to_specs()` creates IMPLEMENTS/VIOLATES edges
- [ ] `link_function_to_patterns()` creates SIMILAR_TO/MITIGATES edges
- [ ] `query_vulnerabilities()` returns high-confidence candidates
- [ ] Composite query support (AND/OR conditions on edge types)
- [ ] 95%+ test coverage
- [ ] Documentation in docs/reference/cross-graph-linker.md

### Should Have
- [ ] Link time < 100ms per function
- [ ] Confidence calibration validated empirically
- [ ] Link explanation strings for debugging

### Nice to Have
- [ ] Graph visualization export (for debugging)
- [ ] Incremental link updates
- [ ] Transitive closure computation

---

## Technical Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CROSS-GRAPH LINKER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌────────────────┐         ┌────────────────┐                            │
│    │   DOMAIN KG    │◄───────►│    CODE KG     │◄───────►│ ADVERSARIAL KG   │
│    │                │         │   (VKG)        │         │                  │
│    │  Specifications│  IMPL   │   Functions    │  SIM    │  Attack Patterns │
│    │  Invariants    │◄───────►│   Contracts    │◄───────►│  Exploits        │
│    │  DeFi Prims    │  VIOL   │   State Vars   │  MITIG  │  CWEs            │
│    └───────┬────────┘         └───────┬────────┘         └────────┬─────────┘
│            │                          │                           │          │
│            │         CROSS-GRAPH EDGES                            │          │
│            │                          │                           │          │
│            │    ┌─────────────────────┴───────────────────┐      │          │
│            │    │                                         │      │          │
│            │    │  code ──IMPLEMENTS──► spec              │      │          │
│            │    │  code ──VIOLATES────► spec              │      │          │
│            │    │  code ──SIMILAR_TO──► pattern           │      │          │
│            │    │  code ──MITIGATES───► pattern           │      │          │
│            │    │  pattern ─EXPLOITS──► spec              │      │          │
│            │    │                                         │      │          │
│            │    └─────────────────────────────────────────┘      │          │
│            │                                                      │          │
│            └──────────────────────────────────────────────────────┘          │
│                                                                              │
│    ┌────────────────────────────────────────────────────────────────────┐   │
│    │                      VULNERABILITY QUERY                            │   │
│    │                                                                     │   │
│    │   VulnerabilityCandidate = {                                       │   │
│    │     function: Node,                                                │   │
│    │     attack_pattern: AttackPattern,    // from SIMILAR_TO edges     │   │
│    │     violated_specs: [Specification],  // from VIOLATES edges       │   │
│    │     mitigations_present: false,       // from absence of MITIGATES │   │
│    │     confidence: 0.85,                 // composite score           │   │
│    │     evidence: [...],                  // supporting evidence       │   │
│    │   }                                                                │   │
│    │                                                                     │   │
│    └────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### New Files
- `src/true_vkg/knowledge/linker.py` - Main implementation
- `src/true_vkg/knowledge/queries.py` - Cross-graph query engine
- `tests/test_3.5/test_linker.py` - Tests

### Key Data Structures

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum


class CrossGraphRelation(Enum):
    """Types of relationships between knowledge graphs."""

    # Code ↔ Domain relations
    IMPLEMENTS = "implements"      # Code correctly implements spec
    VIOLATES = "violates"          # Code violates spec invariant

    # Code ↔ Adversarial relations
    SIMILAR_TO = "similar_to"      # Code matches attack pattern
    MITIGATES = "mitigates"        # Code has protection against pattern

    # Adversarial ↔ Domain relations
    EXPLOITS = "exploits"          # Attack pattern exploits spec weakness


@dataclass
class CrossGraphEdge:
    """
    Edge connecting nodes across different knowledge graphs.

    The power of BSKG 3.5 comes from reasoning over these edges.
    """
    id: str

    # Source and target across graphs
    source_graph: str  # "code", "domain", "adversarial"
    source_id: str
    target_graph: str
    target_id: str

    # Relationship
    relation: CrossGraphRelation

    # Confidence and evidence
    confidence: float  # 0.0 to 1.0
    evidence: List[str]  # Human-readable explanations

    # Metadata
    created_by: str  # Which linker method created this
    created_at: str  # ISO timestamp

    def inverse(self) -> "CrossGraphEdge":
        """Create inverse edge (target → source)."""
        inverse_relations = {
            CrossGraphRelation.IMPLEMENTS: CrossGraphRelation.IMPLEMENTS,  # Symmetric
            CrossGraphRelation.VIOLATES: CrossGraphRelation.VIOLATES,
            CrossGraphRelation.SIMILAR_TO: CrossGraphRelation.SIMILAR_TO,
            CrossGraphRelation.MITIGATES: CrossGraphRelation.MITIGATES,
            CrossGraphRelation.EXPLOITS: CrossGraphRelation.EXPLOITS,
        }
        return CrossGraphEdge(
            id=f"{self.id}_inverse",
            source_graph=self.target_graph,
            source_id=self.target_id,
            target_graph=self.source_graph,
            target_id=self.source_id,
            relation=inverse_relations[self.relation],
            confidence=self.confidence,
            evidence=self.evidence,
            created_by=self.created_by,
            created_at=self.created_at,
        )


@dataclass
class VulnerabilityCandidate:
    """
    Result of cross-graph vulnerability query.

    A candidate is HIGH CONFIDENCE when:
    - Has SIMILAR_TO edge to attack pattern
    - Has VIOLATES edge to specification
    - Does NOT have MITIGATES edge
    """
    function_id: str
    function_node: "Node"

    # From SIMILAR_TO edges
    attack_patterns: List["AttackPattern"]
    pattern_confidences: Dict[str, float]  # pattern_id -> confidence

    # From VIOLATES edges
    violated_specs: List["Specification"]
    violation_confidences: Dict[str, float]  # spec_id -> confidence

    # From MITIGATES edges (or absence thereof)
    mitigations_present: List[str]  # Pattern IDs that are mitigated
    unmitigated_patterns: List[str]  # Pattern IDs without mitigation

    # Composite scoring
    composite_confidence: float
    severity: str  # "critical", "high", "medium", "low"

    # Evidence chain
    evidence: List[str]

    def is_high_confidence(self, threshold: float = 0.7) -> bool:
        """Check if this is a high-confidence vulnerability."""
        return (
            self.composite_confidence >= threshold
            and len(self.unmitigated_patterns) > 0
            and len(self.violated_specs) > 0
        )


class CrossGraphLinker:
    """
    Links the three knowledge graphs together.

    This is WHERE THE MAGIC HAPPENS - connecting:
    - What the code DOES (code KG)
    - What it SHOULD do (domain KG)
    - How it might be BROKEN (adversarial KG)
    """

    def __init__(
        self,
        code_kg: "KnowledgeGraph",
        domain_kg: "DomainKnowledgeGraph",
        adversarial_kg: "AdversarialKnowledgeGraph",
    ):
        self.code_kg = code_kg
        self.domain_kg = domain_kg
        self.adversarial_kg = adversarial_kg

        self.edges: List[CrossGraphEdge] = []
        self._edge_index: Dict[str, List[CrossGraphEdge]] = {}  # node_id -> edges

    def link_all(self) -> int:
        """
        Create all cross-graph links.

        Returns number of edges created.
        """
        count = 0

        # Link each function to specs and patterns
        for node in self.code_kg.nodes.values():
            if node.type == "Function":
                count += self._link_function(node)

        # Link patterns to specs they exploit
        count += self._link_patterns_to_specs()

        return count

    def _link_function(self, fn_node: "Node") -> int:
        """Create links for a single function."""
        count = 0

        # Link to domain specs
        count += self._link_to_specs(fn_node)

        # Link to attack patterns
        count += self._link_to_patterns(fn_node)

        return count

    def _link_to_specs(self, fn_node: "Node") -> int:
        """Create IMPLEMENTS/VIOLATES edges to specifications."""
        count = 0

        # Find matching specs from domain KG
        matching_specs = self.domain_kg.find_matching_specs(fn_node)

        for spec, match_confidence in matching_specs:
            # Check if function implements or violates spec
            violations = self.domain_kg.check_invariant(
                fn_node,
                spec,
                fn_node.properties.get("behavioral_signature", ""),
            )

            if violations:
                # Create VIOLATES edge
                for violation in violations:
                    edge = CrossGraphEdge(
                        id=f"violates_{fn_node.id}_{spec.id}_{violation.id}",
                        source_graph="code",
                        source_id=fn_node.id,
                        target_graph="domain",
                        target_id=spec.id,
                        relation=CrossGraphRelation.VIOLATES,
                        confidence=match_confidence * violation.confidence,
                        evidence=[
                            f"Function matches {spec.name} (conf: {match_confidence:.2f})",
                            f"Violates invariant: {violation.description}",
                        ],
                        created_by="_link_to_specs",
                        created_at=datetime.now().isoformat(),
                    )
                    self._add_edge(edge)
                    count += 1
            else:
                # Create IMPLEMENTS edge
                edge = CrossGraphEdge(
                    id=f"implements_{fn_node.id}_{spec.id}",
                    source_graph="code",
                    source_id=fn_node.id,
                    target_graph="domain",
                    target_id=spec.id,
                    relation=CrossGraphRelation.IMPLEMENTS,
                    confidence=match_confidence,
                    evidence=[
                        f"Function matches {spec.name} signature/operations",
                        f"No invariant violations detected",
                    ],
                    created_by="_link_to_specs",
                    created_at=datetime.now().isoformat(),
                )
                self._add_edge(edge)
                count += 1

        return count

    def _link_to_patterns(self, fn_node: "Node") -> int:
        """Create SIMILAR_TO/MITIGATES edges to attack patterns."""
        count = 0

        # Find similar patterns from adversarial KG
        pattern_matches = self.adversarial_kg.find_similar_patterns(fn_node)

        for match in pattern_matches:
            if match.blocked_by:
                # Create MITIGATES edge (has protection)
                edge = CrossGraphEdge(
                    id=f"mitigates_{fn_node.id}_{match.pattern.id}",
                    source_graph="code",
                    source_id=fn_node.id,
                    target_graph="adversarial",
                    target_id=match.pattern.id,
                    relation=CrossGraphRelation.MITIGATES,
                    confidence=match.confidence,
                    evidence=[
                        f"Pattern {match.pattern.name} partially matches",
                        f"Blocked by: {', '.join(match.blocked_by)}",
                    ],
                    created_by="_link_to_patterns",
                    created_at=datetime.now().isoformat(),
                )
            else:
                # Create SIMILAR_TO edge (potentially vulnerable)
                edge = CrossGraphEdge(
                    id=f"similar_to_{fn_node.id}_{match.pattern.id}",
                    source_graph="code",
                    source_id=fn_node.id,
                    target_graph="adversarial",
                    target_id=match.pattern.id,
                    relation=CrossGraphRelation.SIMILAR_TO,
                    confidence=match.confidence,
                    evidence=[
                        f"Matches pattern: {match.pattern.name}",
                        f"Matched operations: {match.matched_operations}",
                        f"Signature match: {match.matched_signature}",
                    ],
                    created_by="_link_to_patterns",
                    created_at=datetime.now().isoformat(),
                )

            self._add_edge(edge)
            count += 1

        return count

    def query_vulnerabilities(
        self,
        function_id: Optional[str] = None,
        min_confidence: float = 0.5,
    ) -> List[VulnerabilityCandidate]:
        """
        Query for vulnerability candidates based on cross-graph analysis.

        A function is a vulnerability candidate if:
        1. It has SIMILAR_TO edges to attack patterns
        2. It has VIOLATES edges to specifications
        3. It does NOT have MITIGATES edges for those patterns
        """
        candidates = []

        # Get functions to analyze
        if function_id:
            functions = [self.code_kg.nodes[function_id]]
        else:
            functions = [n for n in self.code_kg.nodes.values() if n.type == "Function"]

        for fn_node in functions:
            candidate = self._build_candidate(fn_node, min_confidence)
            if candidate and candidate.composite_confidence >= min_confidence:
                candidates.append(candidate)

        return sorted(candidates, key=lambda c: c.composite_confidence, reverse=True)

    def _build_candidate(
        self,
        fn_node: "Node",
        min_confidence: float,
    ) -> Optional[VulnerabilityCandidate]:
        """Build vulnerability candidate from cross-graph edges."""

        # Get all edges for this function
        fn_edges = self._edge_index.get(fn_node.id, [])

        # Categorize edges
        similar_to_edges = [e for e in fn_edges if e.relation == CrossGraphRelation.SIMILAR_TO]
        violates_edges = [e for e in fn_edges if e.relation == CrossGraphRelation.VIOLATES]
        mitigates_edges = [e for e in fn_edges if e.relation == CrossGraphRelation.MITIGATES]

        # Need at least one vulnerability signal
        if not similar_to_edges and not violates_edges:
            return None

        # Build candidate
        attack_patterns = []
        pattern_confidences = {}
        mitigated_patterns = set()
        unmitigated_patterns = []

        for edge in similar_to_edges:
            pattern = self.adversarial_kg.patterns.get(edge.target_id)
            if pattern:
                attack_patterns.append(pattern)
                pattern_confidences[pattern.id] = edge.confidence

        for edge in mitigates_edges:
            mitigated_patterns.add(edge.target_id)

        for pattern in attack_patterns:
            if pattern.id not in mitigated_patterns:
                unmitigated_patterns.append(pattern.id)

        violated_specs = []
        violation_confidences = {}

        for edge in violates_edges:
            spec = self.domain_kg.specifications.get(edge.target_id)
            if spec:
                violated_specs.append(spec)
                violation_confidences[spec.id] = edge.confidence

        # Compute composite confidence
        # Higher when: multiple patterns match, specs violated, no mitigations
        composite = self._compute_composite_confidence(
            pattern_confidences,
            violation_confidences,
            len(mitigated_patterns),
            len(unmitigated_patterns),
        )

        # Build evidence chain
        evidence = []
        for edge in similar_to_edges + violates_edges:
            evidence.extend(edge.evidence)

        if composite >= min_confidence:
            return VulnerabilityCandidate(
                function_id=fn_node.id,
                function_node=fn_node,
                attack_patterns=attack_patterns,
                pattern_confidences=pattern_confidences,
                violated_specs=violated_specs,
                violation_confidences=violation_confidences,
                mitigations_present=list(mitigated_patterns),
                unmitigated_patterns=unmitigated_patterns,
                composite_confidence=composite,
                severity=self._compute_severity(composite, attack_patterns),
                evidence=evidence,
            )

        return None

    def _compute_composite_confidence(
        self,
        pattern_confs: Dict[str, float],
        violation_confs: Dict[str, float],
        num_mitigated: int,
        num_unmitigated: int,
    ) -> float:
        """
        Compute composite vulnerability confidence.

        Formula:
        - Base: max(pattern confidences) * 0.4 + max(violation confidences) * 0.4
        - Bonus: +0.2 if multiple patterns match
        - Bonus: +0.1 if multiple specs violated
        - Penalty: -0.3 * (mitigated / total patterns)
        """
        if not pattern_confs and not violation_confs:
            return 0.0

        base = 0.0
        if pattern_confs:
            base += max(pattern_confs.values()) * 0.4
        if violation_confs:
            base += max(violation_confs.values()) * 0.4

        # Multi-signal bonus
        if len(pattern_confs) > 1:
            base += 0.1
        if len(violation_confs) > 1:
            base += 0.1

        # Mitigation penalty
        total_patterns = num_mitigated + num_unmitigated
        if total_patterns > 0:
            mitigation_ratio = num_mitigated / total_patterns
            base -= 0.3 * mitigation_ratio

        return max(0.0, min(1.0, base))
```

---

## Implementation Plan

### Phase 1: Core Data Structures (1.5 days)
- [ ] Create `linker.py` with dataclasses
- [ ] Implement `CrossGraphEdge` with all relation types
- [ ] Implement `VulnerabilityCandidate`
- [ ] Create `CrossGraphLinker` shell
- [ ] Implement edge indexing
- [ ] Write unit tests for data structures
- **Checkpoint**: Can create and query edges

### Phase 2: Linking Logic (2 days)
- [ ] Implement `_link_to_specs()` for IMPLEMENTS/VIOLATES edges
- [ ] Implement `_link_to_patterns()` for SIMILAR_TO/MITIGATES edges
- [ ] Implement `_link_patterns_to_specs()` for EXPLOITS edges
- [ ] Implement `link_all()` orchestration
- [ ] Add confidence calculation for each edge type
- [ ] Write tests for linking logic
- **Checkpoint**: Can create all edge types

### Phase 3: Query Engine (1.5 days)
- [ ] Implement `_build_candidate()` from edge analysis
- [ ] Implement `_compute_composite_confidence()`
- [ ] Implement `query_vulnerabilities()` main method
- [ ] Add severity computation
- [ ] Add evidence chain building
- [ ] Implement composite queries (AND/OR)
- [ ] Performance optimization (lazy loading, caching)
- **Checkpoint**: Can query vulnerability candidates

---

## Validation Tests

### Unit Tests

```python
# tests/test_3.5/test_linker.py

import pytest
from true_vkg.knowledge.linker import (
    CrossGraphLinker,
    CrossGraphEdge,
    CrossGraphRelation,
    VulnerabilityCandidate,
)


class TestCrossGraphEdge:
    """Test CrossGraphEdge dataclass."""

    def test_edge_creation(self):
        """Test basic edge creation."""
        edge = CrossGraphEdge(
            id="test_edge",
            source_graph="code",
            source_id="fn_withdraw",
            target_graph="adversarial",
            target_id="reentrancy_classic",
            relation=CrossGraphRelation.SIMILAR_TO,
            confidence=0.85,
            evidence=["Pattern matches"],
            created_by="test",
            created_at="2026-01-02T00:00:00",
        )
        assert edge.relation == CrossGraphRelation.SIMILAR_TO
        assert edge.confidence == 0.85


class TestCrossGraphLinker:
    """Test CrossGraphLinker functionality."""

    @pytest.fixture
    def linker(self, code_kg, domain_kg, adversarial_kg):
        """Create linker with test knowledge graphs."""
        return CrossGraphLinker(code_kg, domain_kg, adversarial_kg)

    def test_link_vulnerable_function_to_pattern(self, linker):
        """Test linking vulnerable function to attack pattern."""
        # Add vulnerable function to code KG
        fn_node = MockFunctionNode(
            id="fn_withdraw",
            semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            behavioral_signature="X:out→W:bal",
            properties={"state_write_after_external_call": True},
        )
        linker.code_kg.add_node(fn_node)

        # Link
        linker.link_all()

        # Check edges
        edges = linker._edge_index.get("fn_withdraw", [])
        similar_to = [e for e in edges if e.relation == CrossGraphRelation.SIMILAR_TO]

        assert len(similar_to) > 0
        assert any("reentrancy" in e.target_id for e in similar_to)

    def test_link_protected_function_creates_mitigates(self, linker):
        """Test that protected functions get MITIGATES edges."""
        # Add protected function
        fn_node = MockFunctionNode(
            id="fn_safe_withdraw",
            semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            behavioral_signature="X:out→W:bal",
            properties={
                "state_write_after_external_call": True,
                "has_reentrancy_guard": True,  # Protected!
            },
        )
        linker.code_kg.add_node(fn_node)

        linker.link_all()

        edges = linker._edge_index.get("fn_safe_withdraw", [])
        mitigates = [e for e in edges if e.relation == CrossGraphRelation.MITIGATES]

        assert len(mitigates) > 0
        assert any("reentrancy" in e.target_id for e in mitigates)

    def test_link_function_to_spec_violation(self, linker):
        """Test VIOLATES edge creation."""
        # Add function that violates ERC-20 spec
        fn_node = MockFunctionNode(
            id="fn_transfer",
            semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            behavioral_signature="X:out→W:bal",  # CEI violation
            signature="transfer(address,uint256)",
        )
        linker.code_kg.add_node(fn_node)

        linker.link_all()

        edges = linker._edge_index.get("fn_transfer", [])
        violates = [e for e in edges if e.relation == CrossGraphRelation.VIOLATES]

        assert len(violates) > 0


class TestVulnerabilityQuery:
    """Test vulnerability candidate queries."""

    @pytest.fixture
    def linked_system(self, code_kg, domain_kg, adversarial_kg):
        """Create fully linked knowledge graph system."""
        linker = CrossGraphLinker(code_kg, domain_kg, adversarial_kg)
        linker.link_all()
        return linker

    def test_query_high_confidence_vulnerable(self, linked_system):
        """Test querying for high-confidence vulnerabilities."""
        candidates = linked_system.query_vulnerabilities(min_confidence=0.6)

        # Should find vulnerable functions
        assert len(candidates) > 0

        # High confidence candidates should have:
        for candidate in candidates:
            if candidate.is_high_confidence():
                # Unmitigated patterns
                assert len(candidate.unmitigated_patterns) > 0
                # Spec violations
                assert len(candidate.violated_specs) > 0

    def test_protected_functions_low_confidence(self, linked_system):
        """Test that protected functions have low confidence."""
        # Query for the protected function
        candidates = linked_system.query_vulnerabilities(
            function_id="fn_safe_withdraw",
            min_confidence=0.0,  # Get all
        )

        if candidates:
            # Should have low confidence due to mitigations
            assert candidates[0].composite_confidence < 0.5
            assert len(candidates[0].mitigations_present) > 0

    def test_composite_confidence_scoring(self, linked_system):
        """Test that composite confidence rewards multiple signals."""
        # Function with multiple vulnerability signals
        fn_multi = MockFunctionNode(
            id="fn_multi_vuln",
            semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE", "READS_ORACLE"],
            behavioral_signature="R:orc→X:out→W:bal",
            properties={
                "state_write_after_external_call": True,
                "reads_oracle_price": True,
                "has_staleness_check": False,
            },
        )
        linked_system.code_kg.add_node(fn_multi)
        linked_system._link_function(fn_multi)

        candidates = linked_system.query_vulnerabilities(function_id="fn_multi_vuln")

        if candidates:
            # Multiple patterns should boost confidence
            assert len(candidates[0].attack_patterns) > 1
            assert candidates[0].composite_confidence > 0.6
```

### The Ultimate Test

```python
def test_ultimate_cross_graph_detection():
    """
    Ultimate test: Cross-graph analysis detects DAO-style vulnerability
    by combining spec violation AND pattern match.

    This proves the cross-graph linker enables true semantic detection.
    """
    # Setup all three knowledge graphs
    code_kg = create_test_code_kg()
    domain_kg = DomainKnowledgeGraph()
    domain_kg.load_all()
    adversarial_kg = AdversarialKnowledgeGraph()
    adversarial_kg.load_all()

    # Add The DAO-style vulnerable function
    dao_vuln_fn = MockFunctionNode(
        id="fn_splitDAO",
        name="splitDAO",
        semantic_ops=[
            "READS_USER_BALANCE",
            "VALIDATES_INPUT",
            "TRANSFERS_VALUE_OUT",
            "WRITES_USER_BALANCE",
        ],
        behavioral_signature="R:bal→V:in→X:out→W:bal",
        signature="splitDAO(uint256,address)",
        properties={
            "visibility": "public",
            "state_write_after_external_call": True,
            "has_reentrancy_guard": False,
            "transfers_eth": True,
        },
    )
    code_kg.add_node(dao_vuln_fn)

    # Create linker and link
    linker = CrossGraphLinker(code_kg, domain_kg, adversarial_kg)
    linker.link_all()

    # Query for vulnerabilities
    candidates = linker.query_vulnerabilities(
        function_id="fn_splitDAO",
        min_confidence=0.5,
    )

    # MUST find this as high-confidence vulnerable
    assert len(candidates) == 1, "Should find exactly one candidate"

    candidate = candidates[0]

    # Must have SIMILAR_TO edges to reentrancy patterns
    assert len(candidate.attack_patterns) > 0
    reentrancy_patterns = [p for p in candidate.attack_patterns if "reentrancy" in p.id]
    assert len(reentrancy_patterns) > 0, "Must match reentrancy pattern"

    # Must have VIOLATES edges (CEI violation)
    assert len(candidate.violated_specs) > 0, "Must violate specifications"

    # Must NOT be mitigated
    assert len(candidate.unmitigated_patterns) > 0, "Must have unmitigated patterns"
    assert "reentrancy" in candidate.unmitigated_patterns[0]

    # High confidence
    assert candidate.is_high_confidence(threshold=0.7), \
        f"Should be high confidence, got {candidate.composite_confidence}"

    # Severity should be critical
    assert candidate.severity == "critical", \
        f"Reentrancy should be critical, got {candidate.severity}"

    print(f"SUCCESS: Detected DAO-style vulnerability with {candidate.composite_confidence:.2f} confidence")
    print(f"Patterns: {[p.name for p in candidate.attack_patterns]}")
    print(f"Violations: {[s.name for s in candidate.violated_specs]}")
    print(f"Evidence: {candidate.evidence[:3]}")
```

---

## Metrics & Measurement

### Before Implementation (Baseline)
| Metric | Value | How Measured |
|--------|-------|--------------|
| Cross-graph queries | N/A | Not available |
| Composite vulnerability detection | N/A | Not available |

### After Implementation (Results)
| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| Edge types implemented | 5 | - | - |
| Composite query support | Yes | - | - |
| Link time (100 functions) | <10s | - | - |
| Query time | <100ms | - | - |
| Detection precision boost | +20% vs single-graph | - | - |

---

## Critical Self-Analysis

### What Could Go Wrong
1. **Edge explosion**: Too many edges make queries slow
   - Mitigation: Confidence thresholds, lazy evaluation

2. **False correlations**: Spurious cross-graph connections
   - Mitigation: Require multiple evidence types

3. **Confidence miscalibration**: Composite scores don't reflect reality
   - Mitigation: Empirical calibration on known vulnerabilities

### Questions to Answer During Implementation
1. Should edges be bidirectional or unidirectional?
2. How to handle partial matches (some invariants violated, not all)?
3. Should confidence be calibrated per-pattern or globally?

---

## Improvement Opportunities

### Discovered During Planning
- [ ] Edge weight learning from feedback
- [ ] Graph embedding for similarity queries

### For Future Phases
- [ ] Transitive closure (A→B→C implies A→C relationship)
- [ ] Temporal edges (vulnerability introduced in commit X)

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-02 | Created | Claude |
