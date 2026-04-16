"""
Intent Integration with VKG Builder

Provides intent annotation capabilities for VKG graphs without modifying
the core builder. Uses composition pattern for clean integration.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node
from alphaswarm_sol.intent.annotator import IntentAnnotator
from alphaswarm_sol.intent.schema import FunctionIntent


class IntentEnrichedGraph:
    """
    Wrapper that adds intent annotation capabilities to existing KnowledgeGraph.

    Uses lazy evaluation - intents are computed on-demand and cached.
    """

    def __init__(
        self,
        graph: KnowledgeGraph,
        annotator: IntentAnnotator,
        source_map: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize intent-enriched graph.

        Args:
            graph: Base knowledge graph
            annotator: Intent annotator
            source_map: Optional mapping of function IDs to source code
        """
        self.graph = graph
        self.annotator = annotator
        self.source_map = source_map or {}

    def get_intent(self, fn_node: Node) -> Optional[FunctionIntent]:
        """
        Get or compute intent for a function node.

        Args:
            fn_node: Function node

        Returns:
            FunctionIntent if available, None otherwise
        """
        # Check if already annotated
        if "intent" in fn_node.properties:
            return FunctionIntent.from_dict(fn_node.properties["intent"])

        # Annotate on-demand
        if fn_node.type == "Function":
            intent = self._annotate_function(fn_node)
            if intent:
                # Cache in node properties
                fn_node.properties["intent"] = intent.to_dict()
                fn_node.properties["business_purpose"] = intent.business_purpose.value
                fn_node.properties["trust_level"] = intent.expected_trust_level.value
                fn_node.properties["purpose_confidence"] = intent.purpose_confidence
                return intent

        return None

    def annotate_all_functions(self, batch_size: int = 10) -> int:
        """
        Annotate all function nodes in the graph.

        Args:
            batch_size: Number of functions to annotate per batch

        Returns:
            Number of functions annotated
        """
        functions = [n for n in self.graph.nodes.values() if n.type == "Function"]

        annotated_count = 0
        batch = []

        for fn_node in functions:
            # Skip if already annotated
            if "intent" in fn_node.properties:
                continue

            # Add to batch
            code_context = self._get_function_code(fn_node)
            contract_context = self._get_contract_context(fn_node)

            if code_context:
                batch.append((fn_node, code_context, contract_context))

            # Process batch when full
            if len(batch) >= batch_size:
                self._process_batch(batch)
                annotated_count += len(batch)
                batch = []

        # Process remaining
        if batch:
            self._process_batch(batch)
            annotated_count += len(batch)

        return annotated_count

    def get_functions_by_purpose(self, business_purpose: str) -> List[Node]:
        """
        Get all functions with a specific business purpose.

        Args:
            business_purpose: Business purpose value

        Returns:
            List of function nodes
        """
        results = []
        for node in self.graph.nodes.values():
            if node.type == "Function":
                if node.properties.get("business_purpose") == business_purpose:
                    results.append(node)
                elif "intent" not in node.properties:
                    # Lazily annotate and check
                    intent = self.get_intent(node)
                    if intent and intent.business_purpose.value == business_purpose:
                        results.append(node)
        return results

    def get_high_risk_functions(self, threshold: float = 0.7) -> List[Node]:
        """
        Get all high-risk functions based on intent analysis.

        Args:
            threshold: Risk threshold

        Returns:
            List of high-risk function nodes
        """
        results = []
        for node in self.graph.nodes.values():
            if node.type == "Function":
                intent = self.get_intent(node)
                if intent and intent.is_high_risk(threshold):
                    results.append(node)
        return results

    def get_authorization_mismatches(self) -> List[tuple[Node, str]]:
        """
        Find functions where actual access != expected access.

        Returns:
            List of (node, mismatch_description) tuples
        """
        mismatches = []

        for node in self.graph.nodes.values():
            if node.type != "Function":
                continue

            intent = self.get_intent(node)
            if not intent:
                continue

            # Check if function has authorization requirements
            if intent.has_authorization_requirements():
                # Check if function has access gate
                has_gate = node.properties.get("has_access_gate", False)

                if not has_gate:
                    mismatch = (
                        f"Expected {intent.expected_trust_level.value} access, "
                        f"but no access gate detected"
                    )
                    mismatches.append((node, mismatch))

        return mismatches

    def _annotate_function(self, fn_node: Node) -> Optional[FunctionIntent]:
        """
        Annotate a single function.

        Args:
            fn_node: Function node

        Returns:
            FunctionIntent or None
        """
        code_context = self._get_function_code(fn_node)
        if not code_context:
            return None

        contract_context = self._get_contract_context(fn_node)

        intent = self.annotator.annotate_function(
            fn_node,
            code_context,
            contract_context,
        )

        return intent

    def _process_batch(self, batch: List[tuple[Node, str, Optional[str]]]) -> None:
        """
        Process a batch of functions.

        Args:
            batch: List of (fn_node, code_context, contract_context) tuples
        """
        # Use batch annotation
        intents = self.annotator.annotate_batch(batch)

        # Cache results
        for (fn_node, _, _), intent in zip(batch, intents):
            fn_node.properties["intent"] = intent.to_dict()
            fn_node.properties["business_purpose"] = intent.business_purpose.value
            fn_node.properties["trust_level"] = intent.expected_trust_level.value
            fn_node.properties["purpose_confidence"] = intent.purpose_confidence

    def _get_function_code(self, fn_node: Node) -> Optional[str]:
        """
        Get source code for function.

        Args:
            fn_node: Function node

        Returns:
            Source code string or None
        """
        # Try source_map first
        if fn_node.id in self.source_map:
            return self.source_map[fn_node.id]

        # Try node properties
        if "source_code" in fn_node.properties:
            return fn_node.properties["source_code"]

        # Try to construct from evidence
        for evidence in fn_node.evidence:
            if hasattr(evidence, "code_snippet"):
                return evidence.code_snippet

        return None

    def _get_contract_context(self, fn_node: Node) -> Optional[str]:
        """
        Get contract context for function.

        Args:
            fn_node: Function node

        Returns:
            Contract context string or None
        """
        # Find contract node
        contract_node = None
        for edge in self.graph.edges.values():
            if edge.target == fn_node.id and edge.type == "DEFINES":
                contract_node = self.graph.nodes.get(edge.source)
                break

        if not contract_node:
            return None

        # Build context string
        context_parts = [f"Contract: {contract_node.label}"]

        # Add inheritance if available
        if "inherits" in contract_node.properties:
            inherits = contract_node.properties["inherits"]
            if inherits:
                context_parts.append(f"Inherits: {', '.join(inherits)}")

        # Add function count
        function_count = sum(
            1
            for e in self.graph.edges.values()
            if e.source == contract_node.id and e.type == "DEFINES"
        )
        context_parts.append(f"Functions: {function_count}")

        return "\n".join(context_parts)


def enrich_graph_with_intent(
    graph: KnowledgeGraph,
    annotator: IntentAnnotator,
    annotate_now: bool = False,
    source_map: Optional[Dict[str, str]] = None,
) -> IntentEnrichedGraph:
    """
    Factory function to create intent-enriched graph.

    Args:
        graph: Base knowledge graph
        annotator: Intent annotator
        annotate_now: If True, annotate all functions immediately
        source_map: Optional source code mapping

    Returns:
        IntentEnrichedGraph
    """
    enriched = IntentEnrichedGraph(graph, annotator, source_map)

    if annotate_now:
        enriched.annotate_all_functions()

    return enriched
