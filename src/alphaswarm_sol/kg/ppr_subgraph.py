"""PPR-Enhanced Subgraph Extraction for VKG.

Task 9.6: Integrate PPR with subgraph extraction for context optimization.

This module combines:
- PPR algorithm for graph-based relevance scoring
- Seed mapping for query-to-seeds translation
- Graph slicing for category-aware property filtering

The result is a highly optimized subgraph for LLM consumption.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from alphaswarm_sol.kg.ppr import PPRConfig, PPRResult, VKGPPR, run_ppr
from alphaswarm_sol.kg.seed_mapper import SeedMapper, SeedMapping
from alphaswarm_sol.kg.subgraph import (
    CutSetReason,
    OmissionLedger,
    SliceMode,
    SubGraph,
    SubGraphEdge,
    SubGraphNode,
    SubgraphExtractor,
)


@dataclass
class PPRExtractionConfig:
    """Configuration for PPR-based subgraph extraction.

    Attributes:
        context_mode: PPR context mode ("strict", "standard", "relaxed")
        max_nodes: Maximum nodes in extracted subgraph
        min_relevance: Minimum PPR relevance to include
        relative_threshold: Include nodes with score >= factor * max_score
        include_edges: Whether to include edges in result
        expand_state_vars: Whether to ensure state variables are included
    """

    context_mode: str = "standard"
    max_nodes: int = 50
    min_relevance: float = 0.001
    relative_threshold: float = 0.05
    include_edges: bool = True
    expand_state_vars: bool = True

    @classmethod
    def strict(cls) -> "PPRExtractionConfig":
        """Strict config - focused subgraph, fewer nodes."""
        return cls(
            context_mode="strict",
            max_nodes=30,
            min_relevance=0.01,
            relative_threshold=0.1,
        )

    @classmethod
    def standard(cls) -> "PPRExtractionConfig":
        """Standard config - balanced focus and context."""
        return cls(
            context_mode="standard",
            max_nodes=50,
            min_relevance=0.001,
            relative_threshold=0.05,
        )

    @classmethod
    def relaxed(cls) -> "PPRExtractionConfig":
        """Relaxed config - wider context inclusion."""
        return cls(
            context_mode="relaxed",
            max_nodes=100,
            min_relevance=0.0001,
            relative_threshold=0.02,
        )


@dataclass
class PPRSubgraphResult:
    """Result of PPR-based subgraph extraction.

    Contains the extracted subgraph plus PPR metadata.
    """

    subgraph: SubGraph
    ppr_result: PPRResult
    seed_mapping: SeedMapping
    config: PPRExtractionConfig
    stats: Dict[str, Any] = field(default_factory=dict)

    def get_top_nodes(self, k: int = 10) -> List[Tuple[str, float]]:
        """Get top k nodes by PPR relevance."""
        return self.ppr_result.get_top_nodes(k)

    def get_token_estimate(self) -> int:
        """Estimate tokens for LLM consumption."""
        # Rough estimate: 50 tokens per node + 10 per edge
        return len(self.subgraph.nodes) * 50 + len(self.subgraph.edges) * 10


class PPRSubgraphExtractor:
    """Extract subgraphs using PPR for relevance scoring.

    Combines PPR-based relevance with query-aware seed selection
    for optimal LLM context extraction.

    Usage:
        extractor = PPRSubgraphExtractor(graph)

        # From findings
        result = extractor.extract_from_findings(findings)

        # From seeds
        result = extractor.extract_from_seeds(seed_ids)

        # Get LLM-optimized subgraph
        subgraph = result.subgraph
    """

    def __init__(self, graph: Any):
        """Initialize with a KnowledgeGraph.

        Args:
            graph: KnowledgeGraph instance
        """
        self.graph = graph
        self.seed_mapper = SeedMapper(graph)
        self._node_ids = self._get_node_ids()
        self._adjacency = self._build_adjacency()

    def _get_node_ids(self) -> Set[str]:
        """Get all node IDs from graph."""
        if hasattr(self.graph, "nodes"):
            if isinstance(self.graph.nodes, dict):
                return set(self.graph.nodes.keys())
            return {getattr(n, "id", str(n)) for n in self.graph.nodes}
        return set()

    def _build_adjacency(self) -> Dict[str, Set[str]]:
        """Build adjacency list from graph edges."""
        adj: Dict[str, Set[str]] = {}
        if hasattr(self.graph, "edges"):
            edges = self.graph.edges
            if isinstance(edges, dict):
                edges = edges.values()
            for edge in edges:
                source = getattr(edge, "source", "")
                target = getattr(edge, "target", "")
                if isinstance(edge, dict):
                    source = edge.get("source", "")
                    target = edge.get("target", "")
                adj.setdefault(source, set()).add(target)
                adj.setdefault(target, set()).add(source)
        return adj

    def extract_from_findings(
        self,
        findings: List[Dict[str, Any]],
        config: Optional[PPRExtractionConfig] = None,
    ) -> PPRSubgraphResult:
        """Extract subgraph based on vulnerability findings.

        Args:
            findings: List of finding dictionaries
            config: Extraction configuration

        Returns:
            PPRSubgraphResult with extracted subgraph
        """
        if config is None:
            config = PPRExtractionConfig.standard()

        # Map findings to seeds
        seed_mapping = self.seed_mapper.from_findings(findings)

        return self._extract_with_mapping(seed_mapping, config)

    def extract_from_seeds(
        self,
        seed_ids: List[str],
        config: Optional[PPRExtractionConfig] = None,
    ) -> PPRSubgraphResult:
        """Extract subgraph starting from explicit seed nodes.

        Args:
            seed_ids: List of seed node IDs
            config: Extraction configuration

        Returns:
            PPRSubgraphResult with extracted subgraph
        """
        if config is None:
            config = PPRExtractionConfig.standard()

        seed_mapping = self.seed_mapper.from_node_ids(seed_ids)

        return self._extract_with_mapping(seed_mapping, config)

    def extract_from_pattern(
        self,
        pattern_results: List[Dict[str, Any]],
        pattern_id: str = "",
        config: Optional[PPRExtractionConfig] = None,
    ) -> PPRSubgraphResult:
        """Extract subgraph based on pattern matching results.

        Args:
            pattern_results: Pattern match results
            pattern_id: Optional pattern ID
            config: Extraction configuration

        Returns:
            PPRSubgraphResult with extracted subgraph
        """
        if config is None:
            config = PPRExtractionConfig.standard()

        seed_mapping = self.seed_mapper.from_pattern_results(
            pattern_results, pattern_id
        )

        return self._extract_with_mapping(seed_mapping, config)

    def extract_from_function_names(
        self,
        function_names: List[str],
        config: Optional[PPRExtractionConfig] = None,
    ) -> PPRSubgraphResult:
        """Extract subgraph for named functions.

        Args:
            function_names: Function names to analyze
            config: Extraction configuration

        Returns:
            PPRSubgraphResult with extracted subgraph
        """
        if config is None:
            config = PPRExtractionConfig.standard()

        seed_mapping = self.seed_mapper.from_function_names(function_names)

        return self._extract_with_mapping(seed_mapping, config)

    def _extract_with_mapping(
        self,
        seed_mapping: SeedMapping,
        config: PPRExtractionConfig,
    ) -> PPRSubgraphResult:
        """Core extraction method using seed mapping.

        Args:
            seed_mapping: Pre-computed seed mapping
            config: Extraction configuration

        Returns:
            PPRSubgraphResult
        """
        # Get PPR config
        ppr_config = self._get_ppr_config(config.context_mode)

        # Get seeds for PPR
        seeds = seed_mapping.primary_seed_ids()
        if not seeds and seed_mapping.secondary_seeds:
            # Fall back to secondary seeds if no primary
            seeds = [s.id for s in seed_mapping.secondary_seeds]

        # Handle empty seeds
        if not seeds:
            return PPRSubgraphResult(
                subgraph=SubGraph(),
                ppr_result=PPRResult(
                    scores={},
                    iterations=0,
                    converged=True,
                    seeds=[],
                    config=ppr_config,
                ),
                seed_mapping=seed_mapping,
                config=config,
                stats={"error": "No valid seeds found"},
            )

        # Run PPR
        ppr_result = run_ppr(self.graph, seeds, ppr_config)

        # Extract subgraph based on PPR scores
        subgraph = self._build_subgraph(
            ppr_result,
            seeds,
            config,
        )

        # Compute stats
        stats = self._compute_stats(subgraph, ppr_result, config)

        return PPRSubgraphResult(
            subgraph=subgraph,
            ppr_result=ppr_result,
            seed_mapping=seed_mapping,
            config=config,
            stats=stats,
        )

    def _get_ppr_config(self, context_mode: str) -> PPRConfig:
        """Get PPR config for context mode."""
        config_map = {
            "strict": PPRConfig.strict(),
            "standard": PPRConfig.standard(),
            "relaxed": PPRConfig.relaxed(),
        }
        return config_map.get(context_mode, PPRConfig.standard())

    def _build_subgraph(
        self,
        ppr_result: PPRResult,
        seeds: List[str],
        config: PPRExtractionConfig,
    ) -> SubGraph:
        """Build subgraph from PPR results.

        Args:
            ppr_result: PPR computation result
            seeds: Original seed node IDs
            config: Extraction config

        Returns:
            SubGraph with relevant nodes and omission metadata
        """
        subgraph = SubGraph(
            focal_node_ids=seeds,
            analysis_type="ppr_extraction",
        )

        seed_set = set(seeds)

        # Get nodes to include based on PPR scores
        # These are the PPR-selected nodes (relevant_nodes in coverage formula)
        ppr_selected_nodes = self._select_nodes(ppr_result, config)

        # Always include seeds
        for seed_id in seeds:
            if seed_id not in ppr_selected_nodes:
                ppr_selected_nodes.append(seed_id)

        # Track relevant nodes for coverage calculation
        # relevant_nodes = PPR_selected ∪ query_matched ∪ dependency_closed
        # For PPR extraction, relevant_nodes = all PPR-selected nodes
        relevant_nodes_set = set(ppr_selected_nodes)
        subgraph.omissions._relevant_nodes = relevant_nodes_set.copy()

        # Track nodes that exceed max_nodes budget
        omitted_due_to_budget = []
        if len(ppr_selected_nodes) > config.max_nodes:
            omitted_due_to_budget = ppr_selected_nodes[config.max_nodes:]
            ppr_selected_nodes = ppr_selected_nodes[:config.max_nodes]

        # Add nodes to subgraph
        for node_id in ppr_selected_nodes:
            node = self._get_node(node_id)
            if node is None:
                continue

            ppr_score = ppr_result.scores.get(node_id, 0.0)
            is_focal = node_id in seed_set

            sg_node = self._create_subgraph_node(
                node, ppr_score, is_focal, seeds
            )
            subgraph.add_node(sg_node)

        # Record budget-exceeded omissions
        if omitted_due_to_budget:
            for node_id in omitted_due_to_budget:
                subgraph.omissions.add_omitted_node(node_id)
            subgraph.omissions.add_cut_set_entry(
                blocker=f"max_nodes:{config.max_nodes}",
                reason=CutSetReason.BUDGET_EXCEEDED,
                impact=f"Pruned {len(omitted_due_to_budget)} PPR-relevant nodes to fit budget",
            )

        # Expand to include state variables if configured
        if config.expand_state_vars:
            self._expand_state_variables(subgraph, seeds, config.max_nodes)

        # Add edges if configured
        if config.include_edges:
            self._add_edges(subgraph)

        # Compute coverage score
        captured_nodes = set(subgraph.nodes.keys())
        subgraph.omissions.compute_coverage_score(captured_nodes, relevant_nodes_set)

        return subgraph

    def _select_nodes(
        self,
        ppr_result: PPRResult,
        config: PPRExtractionConfig,
    ) -> List[str]:
        """Select nodes to include based on PPR scores.

        Combines:
        - Top-k by score
        - Relative threshold (factor * max_score)
        - Minimum relevance threshold
        """
        if not ppr_result.scores:
            return []

        max_score = max(ppr_result.scores.values())
        relative_cutoff = config.relative_threshold * max_score
        min_cutoff = max(config.min_relevance, relative_cutoff)

        # Filter by minimum cutoff
        candidates = [
            (node_id, score)
            for node_id, score in ppr_result.scores.items()
            if score >= min_cutoff
        ]

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)

        return [node_id for node_id, _ in candidates]

    def _get_node(self, node_id: str) -> Optional[Any]:
        """Get node from graph by ID."""
        if hasattr(self.graph, "nodes"):
            if isinstance(self.graph.nodes, dict):
                return self.graph.nodes.get(node_id)
        return None

    def _create_subgraph_node(
        self,
        node: Any,
        ppr_score: float,
        is_focal: bool,
        focal_nodes: List[str],
    ) -> SubGraphNode:
        """Create SubGraphNode from graph node with PPR score."""
        # Get node attributes
        node_id = getattr(node, "id", str(node))
        node_type = getattr(node, "type", "")
        label = getattr(node, "label", "")

        if isinstance(node, dict):
            node_id = node.get("id", str(node))
            node_type = node.get("type", "")
            label = node.get("label", "")

        # Get properties
        props = {}
        if hasattr(node, "properties"):
            props = dict(node.properties) if isinstance(node.properties, dict) else {}
        elif isinstance(node, dict):
            props = dict(node.get("properties", {}))

        # Add PPR score to properties
        props["ppr_score"] = ppr_score

        # Calculate distance from focal (approximate using PPR)
        # Higher PPR score = closer to seeds
        distance = self._estimate_distance(node_id, focal_nodes, ppr_score)

        # Map PPR score to relevance (0-10 scale)
        relevance = self._ppr_to_relevance(ppr_score, is_focal)

        return SubGraphNode(
            id=node_id,
            type=node_type,
            label=label,
            properties=props,
            relevance_score=relevance,
            distance_from_focal=distance,
            is_focal=is_focal,
        )

    def _estimate_distance(
        self,
        node_id: str,
        focal_nodes: List[str],
        ppr_score: float,
    ) -> int:
        """Estimate graph distance from PPR score."""
        if node_id in focal_nodes:
            return 0
        if ppr_score >= 0.1:
            return 1
        if ppr_score >= 0.01:
            return 2
        return 3

    def _ppr_to_relevance(self, ppr_score: float, is_focal: bool) -> float:
        """Convert PPR score to relevance (0-10 scale)."""
        if is_focal:
            return 10.0

        # Logarithmic scaling for PPR scores
        # PPR scores are often very small
        if ppr_score <= 0:
            return 0.0

        import math
        # Log scale: score 0.1 -> ~6, score 0.01 -> ~4, score 0.001 -> ~2
        log_score = math.log10(ppr_score * 1000) if ppr_score > 0 else 0
        relevance = max(0, min(10, log_score * 2))

        return relevance

    def _expand_state_variables(
        self,
        subgraph: SubGraph,
        focal_nodes: List[str],
        max_nodes: int,
    ) -> None:
        """Ensure state variables are included for focal functions."""
        if len(subgraph.nodes) >= max_nodes:
            return

        for focal_id in focal_nodes:
            node = self._get_node(focal_id)
            if node is None:
                continue

            props = getattr(node, "properties", {})
            if isinstance(node, dict):
                props = node.get("properties", {})

            # Get written state variables
            written = props.get("state_variables_written_names", [])
            read = props.get("state_variables_read_names", [])

            for var_name in written + read:
                if len(subgraph.nodes) >= max_nodes:
                    break

                # Find state variable node
                for nid, n in (self.graph.nodes.items() if isinstance(self.graph.nodes, dict) else []):
                    if nid in subgraph.nodes:
                        continue

                    n_type = getattr(n, "type", n.get("type", "") if isinstance(n, dict) else "")
                    n_label = getattr(n, "label", n.get("label", "") if isinstance(n, dict) else "")

                    if n_type == "StateVariable" and n_label == var_name:
                        sg_node = SubGraphNode(
                            id=nid,
                            type="StateVariable",
                            label=var_name,
                            properties={"related_to": focal_id},
                            relevance_score=7.0,  # High relevance for state
                            distance_from_focal=1,
                        )
                        subgraph.add_node(sg_node)
                        break

    def _add_edges(self, subgraph: SubGraph) -> None:
        """Add edges between nodes in subgraph."""
        node_ids = set(subgraph.nodes.keys())

        if not hasattr(self.graph, "edges"):
            return

        edges = self.graph.edges
        if isinstance(edges, dict):
            edges = edges.values()

        for edge in edges:
            source = getattr(edge, "source", "")
            target = getattr(edge, "target", "")
            edge_id = getattr(edge, "id", f"{source}->{target}")
            edge_type = getattr(edge, "type", "")

            if isinstance(edge, dict):
                source = edge.get("source", "")
                target = edge.get("target", "")
                edge_id = edge.get("id", f"{source}->{target}")
                edge_type = edge.get("type", "")

            if source in node_ids and target in node_ids:
                props = {}
                if hasattr(edge, "properties"):
                    props = dict(edge.properties) if isinstance(edge.properties, dict) else {}
                elif isinstance(edge, dict):
                    props = dict(edge.get("properties", {}))

                sg_edge = SubGraphEdge(
                    id=edge_id,
                    type=edge_type,
                    source=source,
                    target=target,
                    properties=props,
                )
                subgraph.add_edge(sg_edge)

    def _compute_stats(
        self,
        subgraph: SubGraph,
        ppr_result: PPRResult,
        config: PPRExtractionConfig,
    ) -> Dict[str, Any]:
        """Compute extraction statistics including omission metadata."""
        ppr_scores = list(ppr_result.scores.values())

        return {
            "total_graph_nodes": len(self._node_ids),
            "extracted_nodes": len(subgraph.nodes),
            "extracted_edges": len(subgraph.edges),
            "focal_nodes": len(subgraph.focal_node_ids),
            "ppr_iterations": ppr_result.iterations,
            "ppr_converged": ppr_result.converged,
            "avg_ppr_score": sum(ppr_scores) / len(ppr_scores) if ppr_scores else 0,
            "max_ppr_score": max(ppr_scores) if ppr_scores else 0,
            "reduction_ratio": 1 - (len(subgraph.nodes) / len(self._node_ids)) if self._node_ids else 0,
            "context_mode": config.context_mode,
            # v2 contract: omission metadata
            "coverage_score": subgraph.omissions.coverage_score,
            "omissions_present": subgraph.omissions.has_omissions(),
            "cut_set_count": len(subgraph.omissions.cut_set),
            "omitted_nodes_count": len(subgraph.omissions.omitted_nodes),
            "slice_mode": subgraph.omissions.slice_mode.value,
        }


def extract_ppr_subgraph(
    graph: Any,
    seeds: List[str],
    context_mode: str = "standard",
    max_nodes: int = 50,
) -> SubGraph:
    """Convenience function to extract PPR-based subgraph.

    Args:
        graph: KnowledgeGraph
        seeds: Seed node IDs
        context_mode: "strict", "standard", or "relaxed"
        max_nodes: Maximum nodes in result

    Returns:
        SubGraph with PPR-scored nodes
    """
    config_map = {
        "strict": PPRExtractionConfig.strict(),
        "standard": PPRExtractionConfig.standard(),
        "relaxed": PPRExtractionConfig.relaxed(),
    }
    config = config_map.get(context_mode, PPRExtractionConfig.standard())
    config.max_nodes = max_nodes

    extractor = PPRSubgraphExtractor(graph)
    result = extractor.extract_from_seeds(seeds, config)

    return result.subgraph


def extract_ppr_subgraph_for_findings(
    graph: Any,
    findings: List[Dict[str, Any]],
    context_mode: str = "standard",
    max_nodes: int = 50,
) -> PPRSubgraphResult:
    """Extract PPR-based subgraph for vulnerability findings.

    Args:
        graph: KnowledgeGraph
        findings: Vulnerability findings
        context_mode: "strict", "standard", or "relaxed"
        max_nodes: Maximum nodes in result

    Returns:
        PPRSubgraphResult with full metadata
    """
    config_map = {
        "strict": PPRExtractionConfig.strict(),
        "standard": PPRExtractionConfig.standard(),
        "relaxed": PPRExtractionConfig.relaxed(),
    }
    config = config_map.get(context_mode, PPRExtractionConfig.standard())
    config.max_nodes = max_nodes

    extractor = PPRSubgraphExtractor(graph)
    return extractor.extract_from_findings(findings, config)
