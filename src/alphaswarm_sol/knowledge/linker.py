"""
Cross-Graph Linker

Connects the three knowledge graphs (Domain, Code, Adversarial) with semantic relationships.
This is THE KEY INNOVATION enabling business logic detection.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime


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

    The power of VKG 3.5 comes from reasoning over these edges.
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
    function_node: Any  # Node from code KG

    # From SIMILAR_TO edges
    attack_patterns: List[Any]  # AttackPattern instances
    pattern_confidences: Dict[str, float]  # pattern_id -> confidence

    # From VIOLATES edges
    violated_specs: List[Any]  # Specification instances
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
        code_kg: Any,  # KnowledgeGraph instance
        domain_kg: Any,  # DomainKnowledgeGraph instance
        adversarial_kg: Any,  # AdversarialKnowledgeGraph instance
    ):
        """
        Initialize cross-graph linker.

        Args:
            code_kg: Code knowledge graph (VKG instance)
            domain_kg: Domain knowledge graph
            adversarial_kg: Adversarial knowledge graph
        """
        self.code_kg = code_kg
        self.domain_kg = domain_kg
        self.adversarial_kg = adversarial_kg

        self.edges: List[CrossGraphEdge] = []
        self._edge_index: Dict[str, List[CrossGraphEdge]] = {}  # node_id -> edges

    def link_all(self) -> int:
        """
        Create all cross-graph links.

        Returns:
            Number of edges created
        """
        count = 0

        # Link each function to specs and patterns
        for node_id, node in self.code_kg.nodes.items():
            if node.type == "Function":
                count += self._link_function(node)

        # Link patterns to specs they exploit
        count += self._link_patterns_to_specs()

        return count

    def _link_function(self, fn_node: Any) -> int:
        """
        Create links for a single function.

        Args:
            fn_node: Function node from code KG

        Returns:
            Number of edges created
        """
        count = 0

        # Link to domain specs
        count += self._link_to_specs(fn_node)

        # Link to attack patterns
        count += self._link_to_patterns(fn_node)

        return count

    def _link_to_specs(self, fn_node: Any) -> int:
        """
        Create IMPLEMENTS/VIOLATES edges to specifications.

        Args:
            fn_node: Function node from code KG

        Returns:
            Number of edges created
        """
        count = 0

        # Convert node to dict for domain KG compatibility
        fn_dict = {
            "id": fn_node.id,
            "name": fn_node.name,
            "signature": fn_node.properties.get("signature", ""),
            "properties": fn_node.properties,
        }

        # Find matching specs from domain KG
        matching_specs = self.domain_kg.find_matching_specs(fn_dict)

        for spec, match_confidence in matching_specs:
            # Check if function implements or violates spec
            behavioral_sig = fn_node.properties.get("behavioral_signature", "")
            violations = self.domain_kg.check_invariant(fn_dict, spec, behavioral_sig)

            if violations:
                # Create VIOLATES edge for each violation
                for violation in violations:
                    edge = CrossGraphEdge(
                        id=f"violates_{fn_node.id}_{spec.id}_{violation.invariant.id}",
                        source_graph="code",
                        source_id=fn_node.id,
                        target_graph="domain",
                        target_id=spec.id,
                        relation=CrossGraphRelation.VIOLATES,
                        confidence=match_confidence * violation.confidence,
                        evidence=[
                            f"Function matches {spec.name} (confidence: {match_confidence:.2f})",
                            f"Violates invariant: {violation.invariant.description}",
                        ] + violation.evidence,
                        created_by="_link_to_specs",
                        created_at=datetime.now().isoformat(),
                    )
                    self._add_edge(edge)
                    count += 1
            else:
                # Create IMPLEMENTS edge (clean implementation)
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

    def _link_to_patterns(self, fn_node: Any) -> int:
        """
        Create SIMILAR_TO/MITIGATES edges to attack patterns.

        Args:
            fn_node: Function node from code KG

        Returns:
            Number of edges created
        """
        count = 0

        # Convert node to dict for adversarial KG compatibility
        fn_dict = {
            "id": fn_node.id,
            "name": fn_node.name,
            "properties": fn_node.properties,
        }

        # Find similar patterns from adversarial KG
        pattern_matches = self.adversarial_kg.find_similar_patterns(fn_dict)

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
                    ] + match.evidence,
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
                        f"Matched operations: {', '.join(match.matched_operations)}",
                        f"Signature match: {match.matched_signature}",
                    ] + match.evidence,
                    created_by="_link_to_patterns",
                    created_at=datetime.now().isoformat(),
                )

            self._add_edge(edge)
            count += 1

        return count

    def _link_patterns_to_specs(self) -> int:
        """
        Create EXPLOITS edges between attack patterns and specs.

        Returns:
            Number of edges created
        """
        count = 0

        # For each attack pattern, link to specs it exploits
        for pattern in self.adversarial_kg.patterns.values():
            # Match based on violated properties
            for spec in self.domain_kg.specifications.values():
                # Check if pattern's violated properties overlap with spec
                if set(pattern.violated_properties) & set(spec.semantic_tags):
                    edge = CrossGraphEdge(
                        id=f"exploits_{pattern.id}_{spec.id}",
                        source_graph="adversarial",
                        source_id=pattern.id,
                        target_graph="domain",
                        target_id=spec.id,
                        relation=CrossGraphRelation.EXPLOITS,
                        confidence=0.8,  # High confidence for known pattern-spec relationships
                        evidence=[
                            f"Pattern {pattern.name} exploits {spec.name}",
                            f"Violated properties: {', '.join(pattern.violated_properties)}",
                        ],
                        created_by="_link_patterns_to_specs",
                        created_at=datetime.now().isoformat(),
                    )
                    self._add_edge(edge)
                    count += 1

        return count

    def _add_edge(self, edge: CrossGraphEdge) -> None:
        """
        Add edge to graph and update index.

        Args:
            edge: CrossGraphEdge to add
        """
        self.edges.append(edge)

        # Index by source
        if edge.source_id not in self._edge_index:
            self._edge_index[edge.source_id] = []
        self._edge_index[edge.source_id].append(edge)

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

        Args:
            function_id: Optional specific function to analyze
            min_confidence: Minimum composite confidence threshold

        Returns:
            List of VulnerabilityCandidate sorted by confidence (descending)
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
        fn_node: Any,
        min_confidence: float,
    ) -> Optional[VulnerabilityCandidate]:
        """
        Build vulnerability candidate from cross-graph edges.

        Args:
            fn_node: Function node from code KG
            min_confidence: Minimum confidence threshold

        Returns:
            VulnerabilityCandidate if evidence exists, None otherwise
        """
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
        composite = self._compute_composite_confidence(
            pattern_confidences,
            violation_confidences,
            len(mitigated_patterns),
            len(unmitigated_patterns),
        )

        # Determine severity
        severity = self._compute_severity(attack_patterns, violated_specs, composite)

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
                severity=severity,
                evidence=evidence,
            )

        return None

    def _compute_composite_confidence(
        self,
        pattern_confidences: Dict[str, float],
        violation_confidences: Dict[str, float],
        num_mitigated: int,
        num_unmitigated: int,
    ) -> float:
        """
        Compute composite confidence score.

        Higher when:
        - Multiple patterns match
        - Specs violated
        - No mitigations present

        Args:
            pattern_confidences: Pattern match confidences
            violation_confidences: Spec violation confidences
            num_mitigated: Number of mitigated patterns
            num_unmitigated: Number of unmitigated patterns

        Returns:
            Composite confidence (0.0-1.0)
        """
        if not pattern_confidences and not violation_confidences:
            return 0.0

        score = 0.0

        # Pattern match contribution (40%)
        if pattern_confidences:
            avg_pattern_conf = sum(pattern_confidences.values()) / len(pattern_confidences)
            score += 0.4 * avg_pattern_conf

        # Spec violation contribution (40%)
        if violation_confidences:
            avg_violation_conf = sum(violation_confidences.values()) / len(violation_confidences)
            score += 0.4 * avg_violation_conf

        # Mitigation penalty/bonus (20%)
        if num_unmitigated > 0:
            # Has unmitigated patterns - bonus
            score += 0.2
        elif num_mitigated > 0:
            # Only mitigated patterns - penalty
            score -= 0.1

        return max(0.0, min(1.0, score))

    def _compute_severity(
        self,
        attack_patterns: List[Any],
        violated_specs: List[Any],
        confidence: float,
    ) -> str:
        """
        Compute severity based on patterns and violations.

        Args:
            attack_patterns: Matched attack patterns
            violated_specs: Violated specifications
            confidence: Composite confidence

        Returns:
            Severity string
        """
        # Check for critical patterns
        critical_patterns = [p for p in attack_patterns if p.severity.value == "critical"]

        if critical_patterns and confidence >= 0.8:
            return "critical"
        elif len(attack_patterns) > 1 and len(violated_specs) > 1:
            return "high"
        elif attack_patterns or violated_specs:
            return "medium"
        else:
            return "low"

    def get_edges_for_node(self, node_id: str) -> List[CrossGraphEdge]:
        """
        Get all edges connected to a node.

        Args:
            node_id: Node ID

        Returns:
            List of edges
        """
        return self._edge_index.get(node_id, [])

    def stats(self) -> Dict[str, Any]:
        """
        Get statistics about cross-graph links.

        Returns:
            Dict with statistics
        """
        relation_counts = {}
        for relation in CrossGraphRelation:
            relation_counts[relation.value] = sum(
                1 for e in self.edges if e.relation == relation
            )

        return {
            "total_edges": len(self.edges),
            "by_relation": relation_counts,
            "indexed_nodes": len(self._edge_index),
        }
