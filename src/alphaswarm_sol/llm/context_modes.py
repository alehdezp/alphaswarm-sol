"""Unified Context Modes for VKG.

Task 9.4: Unified context mode configuration across all components.

This module provides a single configuration point for context optimization:
- PPR parameters
- Subgraph extraction settings
- Graph slicing depth
- Token budgets
- Property filtering

Context Modes:
- STRICT: Minimum context, focused on immediate vulnerability
- STANDARD: Balanced context with 1-hop dependencies (DEFAULT)
- RELAXED: Wide context for complex analysis
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from alphaswarm_sol.kg.ppr import PPRConfig
from alphaswarm_sol.kg.ppr_subgraph import PPRExtractionConfig


class ContextMode(Enum):
    """Context mode levels.

    STRICT: Minimum context, focused analysis
    STANDARD: Balanced context (DEFAULT)
    RELAXED: Wide context for complex cases
    """

    STRICT = "strict"
    STANDARD = "standard"
    RELAXED = "relaxed"

    @classmethod
    def from_string(cls, value: str) -> "ContextMode":
        """Parse context mode from string."""
        try:
            return cls(value.lower())
        except ValueError:
            valid = [m.value for m in cls]
            raise ValueError(f"Invalid context mode: {value}. Valid: {valid}")


@dataclass
class ContextModeConfig:
    """Unified configuration for a context mode.

    Contains all settings for PPR, extraction, slicing, and serialization
    for a specific context mode.

    Attributes:
        mode: The context mode
        ppr_alpha: PPR teleport probability
        ppr_max_iter: Maximum PPR iterations
        ppr_epsilon: PPR convergence threshold
        max_nodes: Maximum nodes in extracted subgraph
        max_hops: Maximum hops from focal nodes
        min_relevance: Minimum relevance to include
        relative_threshold: Include nodes with score >= factor * max
        max_tokens: Target token budget for serialization
        include_edges: Whether to include edges
        expand_state_vars: Whether to ensure state vars included
        property_depth: How many related properties to include (0=core only)
    """

    mode: ContextMode
    ppr_alpha: float = 0.15
    ppr_max_iter: int = 50
    ppr_epsilon: float = 1e-4
    max_nodes: int = 50
    max_hops: int = 2
    min_relevance: float = 0.001
    relative_threshold: float = 0.05
    max_tokens: int = 4000
    include_edges: bool = True
    expand_state_vars: bool = True
    property_depth: int = 1

    @classmethod
    def strict(cls) -> "ContextModeConfig":
        """Create STRICT mode config.

        Characteristics:
        - High PPR alpha (stays close to seeds)
        - Fewer iterations (faster)
        - Smaller subgraph (30 nodes)
        - Higher relevance threshold
        - Smaller token budget
        """
        return cls(
            mode=ContextMode.STRICT,
            ppr_alpha=0.25,
            ppr_max_iter=30,
            ppr_epsilon=1e-3,
            max_nodes=30,
            max_hops=1,
            min_relevance=0.01,
            relative_threshold=0.1,
            max_tokens=2000,
            include_edges=True,
            expand_state_vars=True,
            property_depth=0,
        )

    @classmethod
    def standard(cls) -> "ContextModeConfig":
        """Create STANDARD mode config (DEFAULT).

        Characteristics:
        - Balanced PPR alpha
        - Moderate subgraph size (50 nodes)
        - 1-hop dependencies included
        - Standard token budget
        """
        return cls(
            mode=ContextMode.STANDARD,
            ppr_alpha=0.15,
            ppr_max_iter=50,
            ppr_epsilon=1e-4,
            max_nodes=50,
            max_hops=2,
            min_relevance=0.001,
            relative_threshold=0.05,
            max_tokens=4000,
            include_edges=True,
            expand_state_vars=True,
            property_depth=1,
        )

    @classmethod
    def relaxed(cls) -> "ContextModeConfig":
        """Create RELAXED mode config.

        Characteristics:
        - Low PPR alpha (wide exploration)
        - More iterations (thorough)
        - Large subgraph (100 nodes)
        - Lower relevance threshold
        - Higher token budget
        """
        return cls(
            mode=ContextMode.RELAXED,
            ppr_alpha=0.10,
            ppr_max_iter=100,
            ppr_epsilon=1e-5,
            max_nodes=100,
            max_hops=3,
            min_relevance=0.0001,
            relative_threshold=0.02,
            max_tokens=8000,
            include_edges=True,
            expand_state_vars=True,
            property_depth=2,
        )

    @classmethod
    def from_mode(cls, mode: ContextMode | str) -> "ContextModeConfig":
        """Create config from mode enum or string."""
        if isinstance(mode, str):
            mode = ContextMode.from_string(mode)

        config_map = {
            ContextMode.STRICT: cls.strict,
            ContextMode.STANDARD: cls.standard,
            ContextMode.RELAXED: cls.relaxed,
        }
        return config_map[mode]()

    def to_ppr_config(self) -> PPRConfig:
        """Convert to PPR configuration."""
        return PPRConfig(
            alpha=self.ppr_alpha,
            max_iter=self.ppr_max_iter,
            epsilon=self.ppr_epsilon,
        )

    def to_extraction_config(self) -> PPRExtractionConfig:
        """Convert to PPR extraction configuration."""
        return PPRExtractionConfig(
            context_mode=self.mode.value,
            max_nodes=self.max_nodes,
            min_relevance=self.min_relevance,
            relative_threshold=self.relative_threshold,
            include_edges=self.include_edges,
            expand_state_vars=self.expand_state_vars,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mode": self.mode.value,
            "ppr_alpha": self.ppr_alpha,
            "ppr_max_iter": self.ppr_max_iter,
            "ppr_epsilon": self.ppr_epsilon,
            "max_nodes": self.max_nodes,
            "max_hops": self.max_hops,
            "min_relevance": self.min_relevance,
            "relative_threshold": self.relative_threshold,
            "max_tokens": self.max_tokens,
            "include_edges": self.include_edges,
            "expand_state_vars": self.expand_state_vars,
            "property_depth": self.property_depth,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextModeConfig":
        """Create from dictionary."""
        return cls(
            mode=ContextMode(data.get("mode", "standard")),
            ppr_alpha=data.get("ppr_alpha", 0.15),
            ppr_max_iter=data.get("ppr_max_iter", 50),
            ppr_epsilon=data.get("ppr_epsilon", 1e-4),
            max_nodes=data.get("max_nodes", 50),
            max_hops=data.get("max_hops", 2),
            min_relevance=data.get("min_relevance", 0.001),
            relative_threshold=data.get("relative_threshold", 0.05),
            max_tokens=data.get("max_tokens", 4000),
            include_edges=data.get("include_edges", True),
            expand_state_vars=data.get("expand_state_vars", True),
            property_depth=data.get("property_depth", 1),
        )


@dataclass
class ContextExtractionResult:
    """Result of context extraction with a specific mode."""

    mode_config: ContextModeConfig
    nodes_extracted: int = 0
    edges_extracted: int = 0
    tokens_estimated: int = 0
    reduction_ratio: float = 0.0
    ppr_converged: bool = False
    ppr_iterations: int = 0
    warnings: List[str] = field(default_factory=list)

    def is_within_budget(self) -> bool:
        """Check if extraction is within token budget."""
        return self.tokens_estimated <= self.mode_config.max_tokens

    def needs_stricter_mode(self) -> bool:
        """Check if stricter mode should be used."""
        return self.tokens_estimated > self.mode_config.max_tokens * 1.2

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mode": self.mode_config.mode.value,
            "nodes_extracted": self.nodes_extracted,
            "edges_extracted": self.edges_extracted,
            "tokens_estimated": self.tokens_estimated,
            "reduction_ratio": self.reduction_ratio,
            "ppr_converged": self.ppr_converged,
            "ppr_iterations": self.ppr_iterations,
            "within_budget": self.is_within_budget(),
            "warnings": self.warnings,
        }


class ContextModeManager:
    """Manage context extraction across different modes.

    Provides a unified interface for extracting context with automatic
    mode selection and fallback handling.

    Usage:
        manager = ContextModeManager()

        # Extract with specific mode
        result = manager.extract_context(graph, seeds, mode="standard")

        # Extract with automatic fallback if over budget
        result = manager.extract_with_fallback(graph, seeds)
    """

    def __init__(
        self,
        default_mode: ContextMode | str = ContextMode.STANDARD,
        enable_fallback: bool = True,
    ):
        """Initialize context mode manager.

        Args:
            default_mode: Default context mode
            enable_fallback: Whether to fall back to stricter mode if over budget
        """
        if isinstance(default_mode, str):
            default_mode = ContextMode.from_string(default_mode)

        self.default_mode = default_mode
        self.enable_fallback = enable_fallback

    def get_config(self, mode: ContextMode | str | None = None) -> ContextModeConfig:
        """Get config for a mode (or default).

        Args:
            mode: Mode to get config for (None = default)

        Returns:
            ContextModeConfig for the mode
        """
        if mode is None:
            mode = self.default_mode
        elif isinstance(mode, str):
            mode = ContextMode.from_string(mode)

        return ContextModeConfig.from_mode(mode)

    def extract_context(
        self,
        graph: Any,
        seeds: List[str],
        mode: ContextMode | str | None = None,
        findings: Optional[List[Dict[str, Any]]] = None,
    ) -> ContextExtractionResult:
        """Extract context using PPR-based extraction.

        Args:
            graph: Knowledge graph
            seeds: Seed node IDs
            mode: Context mode (None = default)
            findings: Optional findings for seed mapping

        Returns:
            ContextExtractionResult with extraction stats
        """
        from alphaswarm_sol.kg.ppr_subgraph import PPRSubgraphExtractor

        config = self.get_config(mode)

        extractor = PPRSubgraphExtractor(graph)

        if findings:
            result = extractor.extract_from_findings(
                findings,
                config.to_extraction_config(),
            )
        else:
            result = extractor.extract_from_seeds(
                seeds,
                config.to_extraction_config(),
            )

        # Calculate token estimate
        tokens = result.get_token_estimate()

        # Calculate reduction ratio
        total_nodes = len(extractor._node_ids)
        reduction = 1 - (len(result.subgraph.nodes) / total_nodes) if total_nodes else 0

        return ContextExtractionResult(
            mode_config=config,
            nodes_extracted=len(result.subgraph.nodes),
            edges_extracted=len(result.subgraph.edges),
            tokens_estimated=tokens,
            reduction_ratio=reduction,
            ppr_converged=result.ppr_result.converged,
            ppr_iterations=result.ppr_result.iterations,
        )

    def extract_with_fallback(
        self,
        graph: Any,
        seeds: List[str],
        starting_mode: ContextMode | str | None = None,
        findings: Optional[List[Dict[str, Any]]] = None,
    ) -> ContextExtractionResult:
        """Extract context with automatic fallback to stricter mode.

        If extraction exceeds token budget, automatically retries
        with a stricter mode.

        Args:
            graph: Knowledge graph
            seeds: Seed node IDs
            starting_mode: Mode to start with (None = default)
            findings: Optional findings

        Returns:
            ContextExtractionResult (possibly with stricter mode)
        """
        if starting_mode is None:
            starting_mode = self.default_mode
        elif isinstance(starting_mode, str):
            starting_mode = ContextMode.from_string(starting_mode)

        # Try modes from starting to strict
        mode_order = [ContextMode.RELAXED, ContextMode.STANDARD, ContextMode.STRICT]
        start_idx = mode_order.index(starting_mode)

        for mode in mode_order[start_idx:]:
            result = self.extract_context(graph, seeds, mode, findings)

            if result.is_within_budget() or mode == ContextMode.STRICT:
                if mode != starting_mode:
                    result.warnings.append(
                        f"Fell back from {starting_mode.value} to {mode.value} "
                        f"to meet token budget"
                    )
                return result

        # Should not reach here, but return last result
        return result

    def compare_modes(
        self,
        graph: Any,
        seeds: List[str],
    ) -> Dict[str, ContextExtractionResult]:
        """Compare extraction results across all modes.

        Args:
            graph: Knowledge graph
            seeds: Seed node IDs

        Returns:
            Dict mapping mode name to result
        """
        results = {}
        for mode in ContextMode:
            results[mode.value] = self.extract_context(graph, seeds, mode)
        return results

    @staticmethod
    def get_recommended_mode(
        graph_size: int,
        finding_severity: str = "medium",
    ) -> ContextMode:
        """Get recommended mode based on graph size and severity.

        Args:
            graph_size: Number of nodes in graph
            finding_severity: Severity of finding

        Returns:
            Recommended ContextMode
        """
        # For critical findings, use wider context
        if finding_severity.lower() in ["critical", "high"]:
            if graph_size < 100:
                return ContextMode.RELAXED
            return ContextMode.STANDARD

        # For smaller graphs, can afford relaxed
        if graph_size < 50:
            return ContextMode.RELAXED

        # For larger graphs, use stricter modes
        if graph_size > 500:
            return ContextMode.STRICT

        return ContextMode.STANDARD


def get_context_config(mode: str = "standard") -> ContextModeConfig:
    """Get context configuration for a mode.

    Args:
        mode: Mode name ("strict", "standard", "relaxed")

    Returns:
        ContextModeConfig instance
    """
    return ContextModeConfig.from_mode(mode)


def extract_context_for_findings(
    graph: Any,
    findings: List[Dict[str, Any]],
    mode: str = "standard",
) -> ContextExtractionResult:
    """Extract optimized context for findings.

    Convenience function for common use case.

    Args:
        graph: Knowledge graph
        findings: Vulnerability findings
        mode: Context mode

    Returns:
        ContextExtractionResult
    """
    manager = ContextModeManager(default_mode=mode)
    seeds = [f.get("node_id", f.get("function_id", "")) for f in findings]
    seeds = [s for s in seeds if s]

    return manager.extract_context(graph, seeds, mode, findings)
