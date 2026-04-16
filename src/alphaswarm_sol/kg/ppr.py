"""Personalized PageRank for VKG security graph traversal.

Task 9.1: PPR adapted for vulnerability detection.

This module implements PPR based on R9.1 research with:
- Seeds are vulnerability-related nodes
- Edge weights reflect security relevance
- Result is relevance score per node for context extraction

Key features:
- Correct out-degree normalization (fixes original bug)
- Security-aware edge weighting
- Configurable teleport probability for context modes
- Convergence detection
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from alphaswarm_sol.kg.ppr_weights import (
    calculate_edge_weight,
    create_analysis_weights,
    normalize_weights,
)


@dataclass
class PPRConfig:
    """PPR algorithm configuration.

    Based on R9.1 research: ppr-parameters.md

    Attributes:
        alpha: Teleport probability (higher = stays closer to seeds)
        max_iter: Maximum iterations before stopping
        epsilon: Convergence threshold
        min_score: Minimum score to include node in results
    """

    alpha: float = 0.15
    max_iter: int = 50
    epsilon: float = 1e-4
    min_score: float = 1e-6

    @classmethod
    def strict(cls) -> "PPRConfig":
        """High teleport - stays close to seeds (STRICT context mode)."""
        return cls(alpha=0.25, max_iter=30, epsilon=1e-3)

    @classmethod
    def standard(cls) -> "PPRConfig":
        """Balanced exploration (STANDARD context mode - default)."""
        return cls(alpha=0.15, max_iter=50, epsilon=1e-4)

    @classmethod
    def relaxed(cls) -> "PPRConfig":
        """Wide exploration (RELAXED context mode)."""
        return cls(alpha=0.10, max_iter=100, epsilon=1e-5)


@dataclass
class PPRResult:
    """Result of PPR computation.

    Attributes:
        scores: Node ID to relevance score mapping
        iterations: Number of iterations to converge
        converged: Whether algorithm converged within max_iter
        seeds: List of seed nodes used
        config: Configuration used
    """

    scores: Dict[str, float]
    iterations: int
    converged: bool
    seeds: List[str]
    config: PPRConfig

    def get_top_nodes(self, k: int = 10) -> List[Tuple[str, float]]:
        """Get top k nodes by score.

        Args:
            k: Number of top nodes to return

        Returns:
            List of (node_id, score) tuples, sorted descending
        """
        sorted_nodes = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_nodes[:k]

    def get_nodes_above_threshold(self, threshold: float) -> List[str]:
        """Get nodes with score above threshold.

        Args:
            threshold: Minimum score threshold

        Returns:
            List of node IDs above threshold
        """
        return [node for node, score in self.scores.items() if score >= threshold]

    def get_relative_threshold_nodes(self, factor: float = 0.05) -> List[str]:
        """Get nodes with score >= factor * max_score.

        Args:
            factor: Fraction of max score

        Returns:
            List of node IDs above relative threshold
        """
        if not self.scores:
            return []
        max_score = max(self.scores.values())
        threshold = factor * max_score
        return self.get_nodes_above_threshold(threshold)


class VKGPPR:
    """Personalized PageRank for VKG graphs.

    Usage:
        ppr = VKGPPR(graph)
        result = ppr.run(seeds=["withdraw", "balances"])

        # Get top relevant nodes
        top_nodes = result.get_top_nodes(k=10)

        # Get nodes above threshold
        relevant = result.get_relative_threshold_nodes(factor=0.05)
    """

    def __init__(
        self,
        graph: Union[Dict[str, Any], "KnowledgeGraph", "SubGraph"],
        analysis_type: str | None = None,
    ):
        """Initialize with VKG graph.

        Args:
            graph: VKG graph (dict, KnowledgeGraph, or SubGraph)
            analysis_type: Optional analysis type for tuned weights
        """
        self.graph = graph
        self.analysis_type = analysis_type

        # Extract graph components
        self.nodes = self._extract_nodes()
        self.edges = self._extract_edges()

        # Build adjacency structures
        self.in_edges = self._build_in_edges()
        self.out_edges = self._build_out_edges()

        # Calculate and normalize edge weights
        self.edge_weights = self._calculate_weights()

    def _extract_nodes(self) -> Set[str]:
        """Extract all node IDs from graph."""
        nodes = set()

        if isinstance(self.graph, dict):
            # Dict format: {nodes: [...], edges: [...]}
            node_list = self.graph.get("nodes", [])
            if isinstance(node_list, dict):
                nodes.update(node_list.keys())
            else:
                for node in node_list:
                    if isinstance(node, dict):
                        nodes.add(node.get("id", node.get("name", str(node))))
                    else:
                        nodes.add(str(node))
        else:
            # Object with .nodes attribute
            if hasattr(self.graph, "nodes"):
                if isinstance(self.graph.nodes, dict):
                    nodes.update(self.graph.nodes.keys())
                else:
                    for node in self.graph.nodes:
                        nodes.add(getattr(node, "id", str(node)))

        return nodes

    def _extract_edges(self) -> List[Dict[str, Any]]:
        """Extract all edges from graph as dictionaries."""
        edges = []

        if isinstance(self.graph, dict):
            edge_list = self.graph.get("edges", [])
            if isinstance(edge_list, dict):
                for edge_id, edge in edge_list.items():
                    if isinstance(edge, dict):
                        edge = edge.copy()
                        edge["id"] = edge_id
                        edges.append(edge)
                    else:
                        edges.append({
                            "id": edge_id,
                            "source": getattr(edge, "source", ""),
                            "target": getattr(edge, "target", ""),
                            "type": getattr(edge, "type", "uses"),
                        })
            else:
                edges.extend(edge_list)
        else:
            if hasattr(self.graph, "edges"):
                if isinstance(self.graph.edges, dict):
                    for edge_id, edge in self.graph.edges.items():
                        edges.append({
                            "id": edge_id,
                            "source": getattr(edge, "source", ""),
                            "target": getattr(edge, "target", ""),
                            "type": getattr(edge, "type", "uses"),
                            "properties": getattr(edge, "properties", {}),
                        })
                else:
                    for edge in self.graph.edges:
                        edges.append({
                            "source": getattr(edge, "source", ""),
                            "target": getattr(edge, "target", ""),
                            "type": getattr(edge, "type", "uses"),
                        })

        return edges

    def _build_in_edges(self) -> Dict[str, List[Dict]]:
        """Build mapping of node -> incoming edges."""
        in_edges: Dict[str, List[Dict]] = {n: [] for n in self.nodes}

        for edge in self.edges:
            target = edge.get("target", edge.get("to"))
            if target in in_edges:
                in_edges[target].append(edge)

        return in_edges

    def _build_out_edges(self) -> Dict[str, List[Dict]]:
        """Build mapping of node -> outgoing edges."""
        out_edges: Dict[str, List[Dict]] = {n: [] for n in self.nodes}

        for edge in self.edges:
            source = edge.get("source", edge.get("from"))
            if source in out_edges:
                out_edges[source].append(edge)

        return out_edges

    def _calculate_weights(self) -> Dict[str, float]:
        """Calculate and normalize edge weights."""
        # Get base weights (possibly tuned for analysis type)
        base_weights = None
        if self.analysis_type:
            base_weights = create_analysis_weights(self.analysis_type)

        # Calculate raw weights
        raw_weights = {}
        for edge in self.edges:
            edge_id = edge.get("id")
            if edge_id is None:
                source = edge.get("source", edge.get("from", ""))
                target = edge.get("target", edge.get("to", ""))
                edge_id = f"{source}->{target}"

            # Merge edge properties for weight calculation
            edge_data = edge.copy()
            if "properties" in edge:
                edge_data.update(edge["properties"])

            raw_weights[edge_id] = calculate_edge_weight(edge_data, base_weights)

        # Normalize per source node
        return normalize_weights(raw_weights, self.out_edges)

    def run(
        self,
        seeds: List[str],
        config: Optional[PPRConfig] = None,
    ) -> PPRResult:
        """Run Personalized PageRank from seed nodes.

        Args:
            seeds: List of seed node IDs
            config: PPR configuration (default: standard)

        Returns:
            PPRResult with scores and metadata
        """
        if config is None:
            config = PPRConfig.standard()

        # Filter seeds to valid nodes
        valid_seeds = [s for s in seeds if s in self.nodes]

        # Handle edge case: no valid seeds
        if not valid_seeds:
            if not self.nodes:
                return PPRResult(
                    scores={},
                    iterations=0,
                    converged=True,
                    seeds=[],
                    config=config,
                )
            # No valid seeds - return uniform distribution
            uniform_score = 1.0 / len(self.nodes)
            return PPRResult(
                scores={n: uniform_score for n in self.nodes},
                iterations=0,
                converged=True,
                seeds=[],
                config=config,
            )

        # Initialize scores uniformly
        scores = {n: 1.0 / len(self.nodes) for n in self.nodes}

        # Iterate until convergence
        converged = False
        iterations = 0

        for iteration in range(config.max_iter):
            new_scores = self._iterate(scores, valid_seeds, config.alpha)
            iterations = iteration + 1

            # Check convergence
            if self._converged(scores, new_scores, config.epsilon):
                converged = True
                scores = new_scores
                break

            scores = new_scores

        # Filter out very small scores
        filtered_scores = {
            n: s for n, s in scores.items() if s >= config.min_score
        }

        return PPRResult(
            scores=filtered_scores,
            iterations=iterations,
            converged=converged,
            seeds=valid_seeds,
            config=config,
        )

    def _iterate(
        self,
        scores: Dict[str, float],
        seeds: List[str],
        alpha: float,
    ) -> Dict[str, float]:
        """Perform one PPR iteration.

        PPR formula:
        PPR(v) = alpha * p(v) + (1-alpha) * [walk(v) + dangling_contrib(v)]

        Where:
        - p(v) = 1/|seeds| if v in seeds, else 0 (personalization)
        - walk(v) = sum of probability flowing into v from neighbors
        - dangling_contrib = probability from dangling nodes, redistributed to seeds
        """
        new_scores: Dict[str, float] = {}
        seed_set = set(seeds)
        num_seeds = len(seeds)

        # Calculate dangling node contribution
        # Dangling nodes (no outgoing edges) redistribute to personalization vector (seeds)
        dangling_sum = sum(
            scores[n] for n in self.nodes if not self.out_edges[n]
        )

        for node in self.nodes:
            # Teleport component: direct teleport to seeds
            if node in seed_set:
                teleport = alpha / num_seeds
                # Dangling contribution also goes to seeds (personalization)
                dangling_contrib = (1 - alpha) * dangling_sum / num_seeds
            else:
                teleport = 0.0
                dangling_contrib = 0.0

            # Walk component: probability flow from predecessors
            walk = 0.0
            for edge in self.in_edges[node]:
                source = edge.get("source", edge.get("from"))
                edge_id = edge.get("id")
                if edge_id is None:
                    edge_id = f"{source}->{node}"

                weight = self.edge_weights.get(edge_id, 0.0)
                walk += scores.get(source, 0.0) * weight

            new_scores[node] = teleport + (1 - alpha) * walk + dangling_contrib

        return new_scores

    def _converged(
        self,
        old: Dict[str, float],
        new: Dict[str, float],
        epsilon: float,
    ) -> bool:
        """Check if scores have converged."""
        max_diff = 0.0
        for n in self.nodes:
            diff = abs(new.get(n, 0) - old.get(n, 0))
            if diff > max_diff:
                max_diff = diff

        return max_diff < epsilon


def run_ppr(
    graph: Union[Dict[str, Any], "KnowledgeGraph", "SubGraph"],
    seeds: List[str],
    config: Optional[PPRConfig] = None,
    analysis_type: str | None = None,
) -> PPRResult:
    """Convenience function to run PPR on a graph.

    Args:
        graph: VKG graph (dict, KnowledgeGraph, or SubGraph)
        seeds: Seed node IDs
        config: PPR configuration
        analysis_type: Optional analysis type for tuned weights

    Returns:
        PPRResult with scores and metadata
    """
    ppr = VKGPPR(graph, analysis_type=analysis_type)
    return ppr.run(seeds, config)


def get_relevant_nodes_ppr(
    graph: Union[Dict[str, Any], "KnowledgeGraph", "SubGraph"],
    seeds: List[str],
    context_mode: str = "standard",
    max_nodes: int | None = None,
) -> List[str]:
    """Get relevant nodes using PPR with context mode.

    Args:
        graph: VKG graph
        seeds: Seed node IDs
        context_mode: "strict", "standard", or "relaxed"
        max_nodes: Maximum nodes to return

    Returns:
        List of relevant node IDs, sorted by score
    """
    config_map = {
        "strict": PPRConfig.strict(),
        "standard": PPRConfig.standard(),
        "relaxed": PPRConfig.relaxed(),
    }
    config = config_map.get(context_mode, PPRConfig.standard())

    result = run_ppr(graph, seeds, config)

    # Get top nodes
    top = result.get_top_nodes(k=max_nodes or len(result.scores))
    return [node_id for node_id, score in top]
