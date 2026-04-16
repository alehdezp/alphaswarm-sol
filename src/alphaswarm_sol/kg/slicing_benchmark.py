"""Benchmark for graph slicing accuracy and token reduction.

Task 9.C: Benchmark full vs sliced graph accuracy.

This module provides tools to measure:
- Token reduction from slicing
- Detection accuracy preservation
- Category-specific slicing impact
- Hallucination risk reduction

Success Metrics (from GRAPH_DENSITY_INVESTIGATION.md):
- Token Reduction: >= 50% (target 75%)
- Accuracy Preservation: < 5% loss
- Hallucination Reduction: >= 50%
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union

from alphaswarm_sol.kg.property_sets import (
    CORE_PROPERTIES,
    PROPERTY_SETS,
    VulnerabilityCategory,
    get_property_set,
)
from alphaswarm_sol.kg.slicer import GraphSlicer, SlicedGraph, calculate_slicing_impact
from alphaswarm_sol.kg.subgraph import SubGraph, SubGraphNode


@dataclass
class TokenEstimate:
    """Estimated token count for graph content."""

    char_count: int = 0
    word_count: int = 0
    estimated_tokens: int = 0  # ~4 chars per token
    json_size: int = 0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TokenEstimate":
        """Estimate tokens from a dictionary."""
        json_str = json.dumps(data, separators=(",", ":"))
        char_count = len(json_str)
        word_count = len(json_str.split())

        return TokenEstimate(
            char_count=char_count,
            word_count=word_count,
            estimated_tokens=char_count // 4,  # Rough estimate
            json_size=char_count,
        )


@dataclass
class SlicingBenchmarkResult:
    """Result of a slicing benchmark comparison."""

    category: str
    full_tokens: int
    sliced_tokens: int
    reduction_percent: float
    properties_full: int
    properties_sliced: int
    relevant_properties_retained: bool
    irrelevant_properties_removed: List[str] = field(default_factory=list)

    @property
    def meets_target(self) -> bool:
        """Check if reduction meets 50% target."""
        return self.reduction_percent >= 50.0

    @property
    def meets_stretch_target(self) -> bool:
        """Check if reduction meets 75% stretch target."""
        return self.reduction_percent >= 75.0


@dataclass
class AccuracyValidation:
    """Validation that slicing preserves detection capability."""

    category: str
    required_properties: Set[str]
    retained_properties: Set[str]
    missing_required: Set[str]
    accuracy_preserved: bool
    coverage_percent: float


@dataclass
class BenchmarkSuite:
    """Complete benchmark suite results."""

    results: Dict[str, SlicingBenchmarkResult] = field(default_factory=dict)
    validations: Dict[str, AccuracyValidation] = field(default_factory=dict)
    overall_reduction: float = 0.0
    overall_accuracy: float = 0.0
    passing: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "results": {
                k: {
                    "category": v.category,
                    "full_tokens": v.full_tokens,
                    "sliced_tokens": v.sliced_tokens,
                    "reduction_percent": v.reduction_percent,
                    "meets_target": v.meets_target,
                }
                for k, v in self.results.items()
            },
            "validations": {
                k: {
                    "category": v.category,
                    "accuracy_preserved": v.accuracy_preserved,
                    "coverage_percent": v.coverage_percent,
                    "missing_required": list(v.missing_required),
                }
                for k, v in self.validations.items()
            },
            "overall_reduction": self.overall_reduction,
            "overall_accuracy": self.overall_accuracy,
            "passing": self.passing,
        }


class SlicingBenchmark:
    """Benchmark tool for graph slicing evaluation.

    Usage:
        benchmark = SlicingBenchmark()

        # Run on a sample graph
        results = benchmark.run_benchmark(sample_graph)

        # Check if targets are met
        assert results.passing

        # Get detailed results
        for category, result in results.results.items():
            print(f"{category}: {result.reduction_percent:.1f}% reduction")
    """

    def __init__(
        self,
        target_reduction: float = 50.0,
        accuracy_threshold: float = 95.0,
    ):
        """Initialize benchmark.

        Args:
            target_reduction: Target reduction percentage (default 50%)
            accuracy_threshold: Required accuracy preservation (default 95%)
        """
        self.target_reduction = target_reduction
        self.accuracy_threshold = accuracy_threshold
        self.slicer = GraphSlicer()

    def run_benchmark(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        categories: Optional[List[VulnerabilityCategory]] = None,
    ) -> BenchmarkSuite:
        """Run benchmark on a graph for specified categories.

        Args:
            graph: Graph to benchmark
            categories: Categories to test (default: all)

        Returns:
            BenchmarkSuite with results
        """
        if categories is None:
            categories = list(VulnerabilityCategory)

        suite = BenchmarkSuite()

        # Run benchmark for each category
        for category in categories:
            result = self._benchmark_category(graph, category)
            suite.results[category.value] = result

            validation = self._validate_accuracy(graph, category)
            suite.validations[category.value] = validation

        # Calculate overall metrics
        if suite.results:
            suite.overall_reduction = sum(
                r.reduction_percent for r in suite.results.values()
            ) / len(suite.results)

            suite.overall_accuracy = sum(
                v.coverage_percent for v in suite.validations.values()
            ) / len(suite.validations)

        # Check if passing
        suite.passing = (
            suite.overall_reduction >= self.target_reduction
            and suite.overall_accuracy >= self.accuracy_threshold
        )

        return suite

    def _benchmark_category(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        category: VulnerabilityCategory,
    ) -> SlicingBenchmarkResult:
        """Benchmark slicing for a specific category.

        Args:
            graph: Graph to benchmark
            category: Category to slice for

        Returns:
            SlicingBenchmarkResult
        """
        # Calculate full graph size
        full_estimate = self._estimate_tokens(graph)

        # Slice the graph
        sliced = self.slicer.slice_for_category(graph, category)

        # Calculate sliced graph size
        sliced_estimate = self._estimate_tokens_sliced(sliced)

        # Calculate reduction
        if full_estimate.estimated_tokens > 0:
            reduction = (
                (full_estimate.estimated_tokens - sliced_estimate.estimated_tokens)
                / full_estimate.estimated_tokens
                * 100
            )
        else:
            reduction = 0.0

        # Find irrelevant properties that were removed
        prop_set = get_property_set(category)
        relevant = set(prop_set.all_properties()) | set(CORE_PROPERTIES)

        all_props = self._get_all_properties(graph)
        irrelevant_removed = [p for p in all_props if p not in relevant]

        return SlicingBenchmarkResult(
            category=category.value,
            full_tokens=full_estimate.estimated_tokens,
            sliced_tokens=sliced_estimate.estimated_tokens,
            reduction_percent=reduction,
            properties_full=sliced.stats.original_property_count,
            properties_sliced=sliced.stats.sliced_property_count,
            relevant_properties_retained=True,  # Validated separately
            irrelevant_properties_removed=irrelevant_removed,
        )

    def _validate_accuracy(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        category: VulnerabilityCategory,
    ) -> AccuracyValidation:
        """Validate that slicing preserves required properties.

        Args:
            graph: Graph to validate
            category: Category to validate for

        Returns:
            AccuracyValidation
        """
        # Get required properties for this category
        prop_set = get_property_set(category)
        required = set(prop_set.required)

        # Slice the graph
        sliced = self.slicer.slice_for_category(graph, category)

        # Check which properties are retained
        retained: Set[str] = set()
        nodes = sliced.nodes.values() if hasattr(sliced, "nodes") else []
        for node in nodes:
            retained.update(node.properties.keys())

        # Find missing required properties
        # Only count as missing if the property existed in original graph
        original_props = self._get_all_properties(graph)
        relevant_required = required & original_props
        missing = relevant_required - retained

        # Calculate coverage
        if relevant_required:
            coverage = (
                len(relevant_required - missing) / len(relevant_required) * 100
            )
        else:
            coverage = 100.0

        return AccuracyValidation(
            category=category.value,
            required_properties=required,
            retained_properties=retained,
            missing_required=missing,
            accuracy_preserved=len(missing) == 0,
            coverage_percent=coverage,
        )

    def _estimate_tokens(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
    ) -> TokenEstimate:
        """Estimate tokens for a full graph."""
        data = self._graph_to_dict(graph)
        return TokenEstimate.from_dict(data)

    def _estimate_tokens_sliced(
        self,
        sliced: SlicedGraph,
    ) -> TokenEstimate:
        """Estimate tokens for a sliced graph."""
        data = sliced.to_dict()
        return TokenEstimate.from_dict(data)

    def _graph_to_dict(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
    ) -> Dict[str, Any]:
        """Convert graph to dictionary for token estimation."""
        if hasattr(graph, "to_dict"):
            return graph.to_dict()

        # Manual conversion for KnowledgeGraph
        nodes = {}
        if hasattr(graph, "nodes"):
            for node_id, node in graph.nodes.items():
                if hasattr(node, "to_dict"):
                    nodes[node_id] = node.to_dict()
                else:
                    nodes[node_id] = {
                        "id": getattr(node, "id", str(node_id)),
                        "type": getattr(node, "type", "unknown"),
                        "properties": getattr(node, "properties", {}),
                    }

        return {"nodes": nodes}

    def _get_all_properties(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
    ) -> Set[str]:
        """Get all property names from a graph."""
        props: Set[str] = set()
        nodes = graph.nodes.values() if hasattr(graph, "nodes") else []
        for node in nodes:
            if hasattr(node, "properties"):
                props.update(node.properties.keys())
        return props


def run_slicing_benchmark(
    graph: Union[SubGraph, "KnowledgeGraph"],
    target_reduction: float = 50.0,
) -> BenchmarkSuite:
    """Convenience function to run slicing benchmark.

    Args:
        graph: Graph to benchmark
        target_reduction: Target reduction percentage

    Returns:
        BenchmarkSuite with results
    """
    benchmark = SlicingBenchmark(target_reduction=target_reduction)
    return benchmark.run_benchmark(graph)


def compare_full_vs_sliced(
    graph: Union[SubGraph, "KnowledgeGraph"],
    category: VulnerabilityCategory,
) -> Dict[str, Any]:
    """Compare full vs sliced graph for a category.

    Args:
        graph: Graph to compare
        category: Category to slice for

    Returns:
        Comparison dictionary with metrics
    """
    benchmark = SlicingBenchmark()
    result = benchmark._benchmark_category(graph, category)
    validation = benchmark._validate_accuracy(graph, category)

    return {
        "category": category.value,
        "full_tokens": result.full_tokens,
        "sliced_tokens": result.sliced_tokens,
        "reduction_percent": result.reduction_percent,
        "accuracy_preserved": validation.accuracy_preserved,
        "coverage_percent": validation.coverage_percent,
        "meets_target": result.meets_target,
        "irrelevant_removed": len(result.irrelevant_properties_removed),
    }


def generate_benchmark_report(
    suite: BenchmarkSuite,
) -> str:
    """Generate a human-readable benchmark report.

    Args:
        suite: BenchmarkSuite with results

    Returns:
        Formatted report string
    """
    lines = [
        "=" * 60,
        "GRAPH SLICING BENCHMARK REPORT",
        "=" * 60,
        "",
        f"Overall Status: {'PASS' if suite.passing else 'FAIL'}",
        f"Average Reduction: {suite.overall_reduction:.1f}%",
        f"Average Accuracy: {suite.overall_accuracy:.1f}%",
        "",
        "-" * 60,
        "CATEGORY RESULTS",
        "-" * 60,
    ]

    for category, result in suite.results.items():
        status = "PASS" if result.meets_target else "FAIL"
        lines.append(f"\n{category.upper()}:")
        lines.append(f"  Reduction: {result.reduction_percent:.1f}% [{status}]")
        lines.append(f"  Full tokens: {result.full_tokens}")
        lines.append(f"  Sliced tokens: {result.sliced_tokens}")
        lines.append(
            f"  Properties: {result.properties_sliced}/{result.properties_full}"
        )

        if category in suite.validations:
            validation = suite.validations[category]
            lines.append(
                f"  Accuracy: {validation.coverage_percent:.1f}% "
                f"({'preserved' if validation.accuracy_preserved else 'LOSS'})"
            )
            if validation.missing_required:
                lines.append(f"  Missing: {validation.missing_required}")

    lines.extend([
        "",
        "-" * 60,
        "TARGETS",
        "-" * 60,
        "Token Reduction: >= 50% (target), >= 75% (stretch)",
        "Accuracy: >= 95% property coverage",
        "",
        "=" * 60,
    ])

    return "\n".join(lines)


def validate_slicing_for_detection(
    graph: Union[SubGraph, "KnowledgeGraph"],
    finding_pattern_id: str,
) -> bool:
    """Validate that slicing preserves detection capability for a finding.

    This simulates checking if a pattern would still match after slicing.

    Args:
        graph: Graph containing the finding
        finding_pattern_id: Pattern ID that detected the finding

    Returns:
        True if detection would be preserved
    """
    from alphaswarm_sol.kg.property_sets import get_category_from_pattern_id

    # Get category from pattern
    category = get_category_from_pattern_id(finding_pattern_id)

    # Get required properties for this category
    prop_set = get_property_set(category)
    required = set(prop_set.required)

    # Slice the graph
    slicer = GraphSlicer()
    sliced = slicer.slice_for_category(graph, category)

    # Check if required properties are present
    for node in sliced.nodes.values():
        # At least one node should have the detection-critical properties
        if required & set(node.properties.keys()):
            return True

    return False
