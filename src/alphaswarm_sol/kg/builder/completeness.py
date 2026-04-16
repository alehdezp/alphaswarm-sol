"""Completeness reporting for VKG builder.

This module provides comprehensive build reporting with:
- Coverage metrics (contracts, functions, state variables)
- Confidence breakdown (HIGH/MEDIUM/LOW)
- Unresolved items tracking
- Graph fingerprint for determinism verification
- YAML export for human-readable reports

Usage:
    from alphaswarm_sol.kg.builder.completeness import (
        CompletenessReporter,
        generate_report,
        CompletenessReport,
    )

    reporter = CompletenessReporter(ctx)
    report = reporter.generate()
    print(report.to_yaml())
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from alphaswarm_sol.kg.schema import KnowledgeGraph
from alphaswarm_sol.kg.fingerprint import graph_fingerprint

# Type checking imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.kg.builder.context import BuildContext
    from alphaswarm_sol.kg.builder.types import UnresolvedTarget


__all__ = [
    "CoverageMetrics",
    "ConfidenceBreakdown",
    "CompletenessReport",
    "CompletenessReporter",
    "generate_report",
    "write_report",
]


# -----------------------------------------------------------------------------
# Metrics Dataclasses
# -----------------------------------------------------------------------------


@dataclass
class CoverageMetrics:
    """Coverage metrics for the build.

    Tracks how many entities were discovered and processed,
    enabling gap analysis for incomplete builds.
    """

    contracts_total: int = 0
    """Total number of contracts discovered."""

    contracts_processed: int = 0
    """Number of contracts successfully processed."""

    functions_total: int = 0
    """Total number of functions discovered."""

    functions_processed: int = 0
    """Number of functions successfully processed."""

    state_vars_total: int = 0
    """Total number of state variables discovered."""

    state_vars_processed: int = 0
    """Number of state variables successfully processed."""

    @property
    def contract_coverage(self) -> float:
        """Percentage of contracts processed (0.0 to 1.0)."""
        if self.contracts_total == 0:
            return 1.0
        return self.contracts_processed / self.contracts_total

    @property
    def function_coverage(self) -> float:
        """Percentage of functions processed (0.0 to 1.0)."""
        if self.functions_total == 0:
            return 1.0
        return self.functions_processed / self.functions_total

    @property
    def state_var_coverage(self) -> float:
        """Percentage of state variables processed (0.0 to 1.0)."""
        if self.state_vars_total == 0:
            return 1.0
        return self.state_vars_processed / self.state_vars_total


@dataclass
class ConfidenceBreakdown:
    """Confidence breakdown for edges.

    Tracks how many edges were created with each confidence level,
    enabling quality assessment of call target resolution.
    """

    high_confidence: int = 0
    """Number of edges with HIGH confidence."""

    medium_confidence: int = 0
    """Number of edges with MEDIUM confidence."""

    low_confidence: int = 0
    """Number of edges with LOW confidence."""

    @property
    def total(self) -> int:
        """Total number of edges across all confidence levels."""
        return self.high_confidence + self.medium_confidence + self.low_confidence

    @property
    def high_percentage(self) -> float:
        """Percentage of edges with HIGH confidence."""
        if self.total == 0:
            return 100.0
        return (self.high_confidence / self.total) * 100

    @property
    def medium_percentage(self) -> float:
        """Percentage of edges with MEDIUM confidence."""
        if self.total == 0:
            return 0.0
        return (self.medium_confidence / self.total) * 100

    @property
    def low_percentage(self) -> float:
        """Percentage of edges with LOW confidence."""
        if self.total == 0:
            return 0.0
        return (self.low_confidence / self.total) * 100


# -----------------------------------------------------------------------------
# Completeness Report
# -----------------------------------------------------------------------------


@dataclass
class CompletenessReport:
    """Complete build report with all metrics.

    Provides a comprehensive snapshot of the build including:
    - Build metadata (time, schema version, fingerprint)
    - Graph statistics (nodes, edges)
    - Coverage metrics
    - Confidence breakdown
    - Unresolved items
    - Warnings
    """

    # Build info
    build_time: str = ""
    """ISO timestamp of when the report was generated."""

    schema_version: str = "2.0"
    """Schema version used for ID generation."""

    graph_fingerprint: str = ""
    """Deterministic fingerprint of the graph content."""

    # Graph stats
    node_count: int = 0
    """Total number of nodes in the graph."""

    edge_count: int = 0
    """Total number of edges in the graph."""

    rich_edge_count: int = 0
    """Total number of rich edges with intelligence metadata."""

    # Coverage
    coverage: CoverageMetrics = field(default_factory=CoverageMetrics)
    """Coverage metrics for contracts, functions, state variables."""

    # Confidence
    confidence: ConfidenceBreakdown = field(default_factory=ConfidenceBreakdown)
    """Confidence breakdown for edges."""

    # Unresolved items
    unresolved_call_targets: list[dict[str, Any]] = field(default_factory=list)
    """List of call targets that could not be resolved."""

    unresolved_proxy_implementations: list[dict[str, Any]] = field(default_factory=list)
    """List of proxy implementations that could not be resolved."""

    # Warnings
    warnings: list[str] = field(default_factory=list)
    """Non-fatal warnings encountered during build."""

    # Determinism check
    determinism_verified: bool = False
    """Whether the graph fingerprint was verified as deterministic."""

    def to_yaml(self) -> str:
        """Serialize report to YAML format.

        Returns:
            Human-readable YAML representation of the report.
        """
        data = {
            "build_info": {
                "build_time": self.build_time,
                "schema_version": self.schema_version,
                "graph_fingerprint": self.graph_fingerprint,
                "determinism_verified": self.determinism_verified,
            },
            "graph_stats": {
                "nodes": self.node_count,
                "edges": self.edge_count,
                "rich_edges": self.rich_edge_count,
            },
            "coverage": {
                "contracts": {
                    "total": self.coverage.contracts_total,
                    "processed": self.coverage.contracts_processed,
                    "percentage": round(self.coverage.contract_coverage * 100, 1),
                },
                "functions": {
                    "total": self.coverage.functions_total,
                    "processed": self.coverage.functions_processed,
                    "percentage": round(self.coverage.function_coverage * 100, 1),
                },
                "state_variables": {
                    "total": self.coverage.state_vars_total,
                    "processed": self.coverage.state_vars_processed,
                    "percentage": round(self.coverage.state_var_coverage * 100, 1),
                },
            },
            "confidence_breakdown": {
                "high": self.confidence.high_confidence,
                "medium": self.confidence.medium_confidence,
                "low": self.confidence.low_confidence,
                "high_percentage": round(self.confidence.high_percentage, 1),
            },
            "unresolved": {
                "call_targets": self.unresolved_call_targets,
                "call_target_count": len(self.unresolved_call_targets),
                "proxy_implementations": self.unresolved_proxy_implementations,
                "proxy_implementation_count": len(self.unresolved_proxy_implementations),
            },
            "warnings": self.warnings,
            "warning_count": len(self.warnings),
        }
        return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary.

        Returns:
            Dictionary representation of the report.
        """
        return yaml.safe_load(self.to_yaml())

    def is_complete(self, min_coverage: float = 0.95) -> bool:
        """Check if the build meets completeness criteria.

        Args:
            min_coverage: Minimum coverage percentage (default 95%)

        Returns:
            True if all coverage metrics meet the minimum.
        """
        return (
            self.coverage.contract_coverage >= min_coverage
            and self.coverage.function_coverage >= min_coverage
            and self.coverage.state_var_coverage >= min_coverage
        )

    def quality_score(self) -> float:
        """Calculate overall quality score (0.0 to 1.0).

        Considers coverage and confidence metrics.

        Returns:
            Quality score as float between 0.0 and 1.0.
        """
        # Weight coverage more heavily
        coverage_score = (
            self.coverage.contract_coverage * 0.3
            + self.coverage.function_coverage * 0.5
            + self.coverage.state_var_coverage * 0.2
        )

        # Confidence score based on high confidence percentage
        confidence_score = self.confidence.high_percentage / 100.0

        # Penalize unresolved items
        unresolved_penalty = min(
            0.2, (len(self.unresolved_call_targets) * 0.01)
        )

        return max(0.0, (coverage_score * 0.6 + confidence_score * 0.4) - unresolved_penalty)


# -----------------------------------------------------------------------------
# Completeness Reporter
# -----------------------------------------------------------------------------


class CompletenessReporter:
    """Generate completeness reports from build context.

    Analyzes the build context and graph to produce comprehensive
    reports on build quality, coverage, and confidence.
    """

    def __init__(self, ctx: "BuildContext") -> None:
        """Initialize reporter with build context.

        Args:
            ctx: BuildContext with graph and unresolved items.
        """
        self.ctx = ctx

    def generate(self, graph: KnowledgeGraph | None = None) -> CompletenessReport:
        """Generate completeness report.

        Args:
            graph: KnowledgeGraph (uses ctx.graph if not provided)

        Returns:
            CompletenessReport with all metrics.
        """
        if graph is None:
            graph = self.ctx.graph

        report = CompletenessReport(
            build_time=datetime.now(timezone.utc).isoformat(),
            schema_version=getattr(self.ctx, "schema_version", "2.0"),
            graph_fingerprint=graph_fingerprint(graph),
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
            rich_edge_count=len(graph.rich_edges) if hasattr(graph, "rich_edges") else 0,
        )

        # Compute coverage
        report.coverage = self._compute_coverage(graph)

        # Compute confidence breakdown
        report.confidence = self._compute_confidence(graph)

        # Collect unresolved items
        report.unresolved_call_targets = [
            self._unresolved_to_dict(u) for u in self.ctx.unresolved_targets
        ]

        # Collect warnings
        report.warnings = list(self.ctx.warnings)

        # Verify determinism
        report.determinism_verified = self._verify_determinism(graph)

        return report

    def _compute_coverage(self, graph: KnowledgeGraph) -> CoverageMetrics:
        """Compute coverage metrics from graph.

        Args:
            graph: KnowledgeGraph to analyze.

        Returns:
            CoverageMetrics with counts and percentages.
        """
        metrics = CoverageMetrics()

        for node in graph.nodes.values():
            node_type = node.type.lower()
            if node_type == "contract":
                metrics.contracts_total += 1
                metrics.contracts_processed += 1
            elif node_type == "function":
                metrics.functions_total += 1
                metrics.functions_processed += 1
            elif node_type in ("state_variable", "state_var"):
                metrics.state_vars_total += 1
                metrics.state_vars_processed += 1

        return metrics

    def _compute_confidence(self, graph: KnowledgeGraph) -> ConfidenceBreakdown:
        """Compute confidence breakdown from edges.

        Args:
            graph: KnowledgeGraph to analyze.

        Returns:
            ConfidenceBreakdown with counts and percentages.
        """
        breakdown = ConfidenceBreakdown()

        for edge in graph.edges.values():
            confidence = edge.properties.get("confidence", "HIGH")
            if isinstance(confidence, str):
                confidence = confidence.upper()
            if confidence == "HIGH":
                breakdown.high_confidence += 1
            elif confidence == "MEDIUM":
                breakdown.medium_confidence += 1
            else:
                breakdown.low_confidence += 1

        return breakdown

    def _unresolved_to_dict(self, target: "UnresolvedTarget") -> dict[str, Any]:
        """Convert UnresolvedTarget to dict for report.

        Args:
            target: UnresolvedTarget to convert.

        Returns:
            Dictionary representation for YAML export.
        """
        result: dict[str, Any] = {
            "source_function": target.source_function,
            "call_type": target.call_type,
            "target_expression": target.target_expression,
            "reason": target.reason,
            "confidence": target.confidence,
        }

        # Add optional location info
        if target.file and target.line:
            result["location"] = f"{target.file}:{target.line}"
        elif target.file:
            result["location"] = target.file

        return result

    def _verify_determinism(self, graph: KnowledgeGraph) -> bool:
        """Verify graph fingerprint is deterministic.

        Computes fingerprint twice and compares.

        Args:
            graph: KnowledgeGraph to verify.

        Returns:
            True if fingerprints match (deterministic).
        """
        fp1 = graph_fingerprint(graph)
        fp2 = graph_fingerprint(graph)
        return fp1 == fp2


# -----------------------------------------------------------------------------
# Convenience Functions
# -----------------------------------------------------------------------------


def generate_report(
    ctx: "BuildContext",
    graph: KnowledgeGraph | None = None,
) -> CompletenessReport:
    """Convenience function to generate report.

    Args:
        ctx: BuildContext with graph and unresolved items.
        graph: Optional KnowledgeGraph (uses ctx.graph if not provided).

    Returns:
        CompletenessReport with all metrics.
    """
    reporter = CompletenessReporter(ctx)
    return reporter.generate(graph)


def write_report(report: CompletenessReport, output_path: Path) -> None:
    """Write report to YAML file.

    Args:
        report: CompletenessReport to write.
        output_path: Path to output YAML file.
    """
    output_path.write_text(report.to_yaml())
