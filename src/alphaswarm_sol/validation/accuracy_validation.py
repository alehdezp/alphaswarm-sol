"""Accuracy Validation for Context Optimization.

Task 9.5: Validate that PPR-based context optimization preserves detection accuracy.

This module validates:
1. Detection rate comparison (full graph vs optimized)
2. Critical vulnerability retention
3. Token reduction vs accuracy trade-off
4. Context mode comparison

Success criteria from Phase 9 TRACKER:
- Accuracy Preservation: < 5% loss
- Critical Vuln Retention: 100% (95% minimum)
- Token Reduction: >= 25% (35% target)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from alphaswarm_sol.llm.context_modes import (
    ContextMode,
    ContextModeConfig,
    ContextModeManager,
)
from alphaswarm_sol.kg.ppr_subgraph import PPRSubgraphExtractor


class ValidationStatus(Enum):
    """Validation result status."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


@dataclass
class DetectionResult:
    """Result of running detection on a graph or subgraph."""

    findings: List[Dict[str, Any]] = field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0
    token_estimate: int = 0
    context_mode: Optional[str] = None

    def finding_ids(self) -> Set[str]:
        """Get set of finding IDs."""
        return {f.get("id", f.get("node_id", "")) for f in self.findings}

    def critical_findings(self) -> List[Dict[str, Any]]:
        """Get critical severity findings."""
        return [
            f for f in self.findings
            if f.get("severity", "").lower() == "critical"
        ]

    def high_severity_findings(self) -> List[Dict[str, Any]]:
        """Get high+ severity findings (critical + high)."""
        return [
            f for f in self.findings
            if f.get("severity", "").lower() in ["critical", "high"]
        ]


@dataclass
class AccuracyMetrics:
    """Accuracy metrics comparing two detection results.

    Attributes:
        base_findings: Number of findings in base (full graph)
        optimized_findings: Number of findings in optimized version
        retained_findings: Findings present in both
        lost_findings: Findings only in base
        extra_findings: Findings only in optimized (possible false positives)
        retention_rate: % of base findings retained
        critical_retention: % of critical findings retained
        high_severity_retention: % of high+ severity retained
    """

    base_findings: int = 0
    optimized_findings: int = 0
    retained_findings: int = 0
    lost_findings: int = 0
    extra_findings: int = 0
    retention_rate: float = 0.0
    critical_retention: float = 0.0
    high_severity_retention: float = 0.0
    token_reduction: float = 0.0

    def accuracy_loss(self) -> float:
        """Calculate accuracy loss percentage."""
        if self.base_findings == 0:
            return 0.0
        return (self.lost_findings / self.base_findings) * 100

    def is_acceptable(
        self,
        max_accuracy_loss: float = 5.0,
        min_critical_retention: float = 100.0,
    ) -> bool:
        """Check if metrics meet acceptance criteria."""
        if self.accuracy_loss() > max_accuracy_loss:
            return False
        if self.critical_retention < min_critical_retention:
            return False
        return True


@dataclass
class ValidationResult:
    """Result of accuracy validation."""

    status: ValidationStatus
    mode: str
    metrics: AccuracyMetrics
    details: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "mode": self.mode,
            "metrics": {
                "base_findings": self.metrics.base_findings,
                "optimized_findings": self.metrics.optimized_findings,
                "retained_findings": self.metrics.retained_findings,
                "lost_findings": self.metrics.lost_findings,
                "retention_rate": self.metrics.retention_rate,
                "critical_retention": self.metrics.critical_retention,
                "high_severity_retention": self.metrics.high_severity_retention,
                "token_reduction": self.metrics.token_reduction,
                "accuracy_loss": self.metrics.accuracy_loss(),
            },
            "details": self.details,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
        }


@dataclass
class ValidationSuite:
    """Complete validation suite results."""

    results: Dict[str, ValidationResult] = field(default_factory=dict)
    overall_status: ValidationStatus = ValidationStatus.PASS
    summary: Dict[str, Any] = field(default_factory=dict)

    def add_result(self, mode: str, result: ValidationResult) -> None:
        """Add validation result for a mode."""
        self.results[mode] = result

        # Update overall status
        if result.status == ValidationStatus.FAIL:
            self.overall_status = ValidationStatus.FAIL
        elif result.status == ValidationStatus.WARN and self.overall_status == ValidationStatus.PASS:
            self.overall_status = ValidationStatus.WARN

    def get_best_mode(self) -> Optional[str]:
        """Get mode with best accuracy/efficiency trade-off."""
        best_mode = None
        best_score = -1

        for mode, result in self.results.items():
            if result.status == ValidationStatus.PASS:
                # Score = retention_rate * (1 + token_reduction)
                score = result.metrics.retention_rate * (1 + result.metrics.token_reduction / 100)
                if score > best_score:
                    best_score = score
                    best_mode = mode

        return best_mode

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_status": self.overall_status.value,
            "results": {m: r.to_dict() for m, r in self.results.items()},
            "best_mode": self.get_best_mode(),
            "summary": self.summary,
        }


class AccuracyValidator:
    """Validate PPR context optimization accuracy.

    Usage:
        validator = AccuracyValidator(graph)

        # Validate with test findings
        result = validator.validate_mode(test_findings, mode="standard")

        # Compare all modes
        suite = validator.validate_all_modes(test_findings)
    """

    def __init__(
        self,
        graph: Any,
        pattern_engine: Optional[Any] = None,
    ):
        """Initialize validator.

        Args:
            graph: Knowledge graph
            pattern_engine: Optional pattern engine for detection
        """
        self.graph = graph
        self.pattern_engine = pattern_engine
        self.extractor = PPRSubgraphExtractor(graph)
        self.manager = ContextModeManager()

    def validate_mode(
        self,
        base_findings: List[Dict[str, Any]],
        mode: str = "standard",
        detection_func: Optional[callable] = None,
    ) -> ValidationResult:
        """Validate detection accuracy for a context mode.

        Args:
            base_findings: Findings from full graph (ground truth)
            mode: Context mode to validate
            detection_func: Optional function to run detection on subgraph

        Returns:
            ValidationResult with metrics
        """
        config = self.manager.get_config(mode)

        # Create base result from full graph findings
        base_result = self._create_base_result(base_findings)

        # Extract optimized subgraph
        seeds = [f.get("node_id", f.get("function_id", "")) for f in base_findings]
        seeds = [s for s in seeds if s]

        extraction_result = self.manager.extract_context(
            self.graph,
            seeds,
            mode,
            base_findings,
        )

        # Create optimized result
        if detection_func:
            # Run detection on subgraph
            optimized_findings = detection_func(
                extraction_result,
                base_findings,
            )
            optimized_result = DetectionResult(
                findings=optimized_findings,
                node_count=extraction_result.nodes_extracted,
                edge_count=extraction_result.edges_extracted,
                token_estimate=extraction_result.tokens_estimated,
                context_mode=mode,
            )
        else:
            # Simulate: findings in subgraph = findings whose nodes are in subgraph
            optimized_findings = self._simulate_detection(
                base_findings,
                extraction_result,
            )
            optimized_result = DetectionResult(
                findings=optimized_findings,
                node_count=extraction_result.nodes_extracted,
                edge_count=extraction_result.edges_extracted,
                token_estimate=extraction_result.tokens_estimated,
                context_mode=mode,
            )

        # Calculate metrics
        metrics = self._calculate_metrics(base_result, optimized_result)

        # Determine status
        status = self._determine_status(metrics, config)

        # Build result
        result = ValidationResult(
            status=status,
            mode=mode,
            metrics=metrics,
            details={
                "config": config.to_dict(),
                "extraction_stats": extraction_result.to_dict(),
            },
        )

        # Add warnings and recommendations
        self._add_warnings_and_recommendations(result, metrics, config)

        return result

    def validate_all_modes(
        self,
        base_findings: List[Dict[str, Any]],
        detection_func: Optional[callable] = None,
    ) -> ValidationSuite:
        """Validate all context modes.

        Args:
            base_findings: Findings from full graph
            detection_func: Optional detection function

        Returns:
            ValidationSuite with all results
        """
        suite = ValidationSuite()

        for mode in ContextMode:
            result = self.validate_mode(base_findings, mode.value, detection_func)
            suite.add_result(mode.value, result)

        # Build summary
        suite.summary = self._build_summary(suite)

        return suite

    def compare_token_reduction_vs_accuracy(
        self,
        base_findings: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, float]]:
        """Compare token reduction vs accuracy for all modes.

        Args:
            base_findings: Findings from full graph

        Returns:
            Dict mapping mode to {token_reduction, accuracy_loss}
        """
        comparison = {}

        for mode in ContextMode:
            result = self.validate_mode(base_findings, mode.value)
            comparison[mode.value] = {
                "token_reduction": result.metrics.token_reduction,
                "accuracy_loss": result.metrics.accuracy_loss(),
                "retention_rate": result.metrics.retention_rate,
                "critical_retention": result.metrics.critical_retention,
            }

        return comparison

    def _create_base_result(
        self,
        findings: List[Dict[str, Any]],
    ) -> DetectionResult:
        """Create base detection result from full graph findings."""
        node_count = len(self.extractor._node_ids)

        # Estimate tokens for full graph
        token_estimate = node_count * 50  # Rough estimate

        return DetectionResult(
            findings=findings,
            node_count=node_count,
            edge_count=len(self.graph.edges) if hasattr(self.graph, "edges") else 0,
            token_estimate=token_estimate,
            context_mode="full",
        )

    def _simulate_detection(
        self,
        base_findings: List[Dict[str, Any]],
        extraction_result: Any,
    ) -> List[Dict[str, Any]]:
        """Simulate detection by checking if finding nodes are in subgraph.

        This is a simplified simulation - in practice, actual detection
        should be run on the subgraph.
        """
        # Get nodes in extracted subgraph
        # We need to access the subgraph from the extraction result
        subgraph_nodes = set()
        if hasattr(extraction_result, "subgraph"):
            subgraph_nodes = set(extraction_result.subgraph.nodes.keys())

        retained = []
        for finding in base_findings:
            node_id = finding.get("node_id", finding.get("function_id", ""))
            if node_id in subgraph_nodes:
                retained.append(finding)

        return retained

    def _calculate_metrics(
        self,
        base: DetectionResult,
        optimized: DetectionResult,
    ) -> AccuracyMetrics:
        """Calculate accuracy metrics between base and optimized."""
        base_ids = base.finding_ids()
        optimized_ids = optimized.finding_ids()

        retained = base_ids & optimized_ids
        lost = base_ids - optimized_ids
        extra = optimized_ids - base_ids

        # Critical retention
        base_critical = {f.get("id", f.get("node_id", "")) for f in base.critical_findings()}
        optimized_critical = {f.get("id", f.get("node_id", "")) for f in optimized.critical_findings()}
        critical_retained = base_critical & optimized_critical

        critical_retention = 100.0
        if base_critical:
            critical_retention = (len(critical_retained) / len(base_critical)) * 100

        # High severity retention
        base_high = {f.get("id", f.get("node_id", "")) for f in base.high_severity_findings()}
        optimized_high = {f.get("id", f.get("node_id", "")) for f in optimized.high_severity_findings()}
        high_retained = base_high & optimized_high

        high_retention = 100.0
        if base_high:
            high_retention = (len(high_retained) / len(base_high)) * 100

        # Token reduction
        token_reduction = 0.0
        if base.token_estimate > 0:
            token_reduction = ((base.token_estimate - optimized.token_estimate) / base.token_estimate) * 100

        # Retention rate
        retention_rate = 100.0
        if len(base_ids) > 0:
            retention_rate = (len(retained) / len(base_ids)) * 100

        return AccuracyMetrics(
            base_findings=len(base_ids),
            optimized_findings=len(optimized_ids),
            retained_findings=len(retained),
            lost_findings=len(lost),
            extra_findings=len(extra),
            retention_rate=retention_rate,
            critical_retention=critical_retention,
            high_severity_retention=high_retention,
            token_reduction=token_reduction,
        )

    def _determine_status(
        self,
        metrics: AccuracyMetrics,
        config: ContextModeConfig,
    ) -> ValidationStatus:
        """Determine validation status from metrics."""
        # FAIL if critical retention < 95%
        if metrics.critical_retention < 95.0:
            return ValidationStatus.FAIL

        # FAIL if accuracy loss > 10%
        if metrics.accuracy_loss() > 10.0:
            return ValidationStatus.FAIL

        # WARN if accuracy loss > 5%
        if metrics.accuracy_loss() > 5.0:
            return ValidationStatus.WARN

        # WARN if token reduction < 25% (not efficient enough)
        if metrics.token_reduction < 25.0:
            return ValidationStatus.WARN

        return ValidationStatus.PASS

    def _add_warnings_and_recommendations(
        self,
        result: ValidationResult,
        metrics: AccuracyMetrics,
        config: ContextModeConfig,
    ) -> None:
        """Add warnings and recommendations to result."""
        # Warnings
        if metrics.lost_findings > 0:
            result.warnings.append(
                f"{metrics.lost_findings} findings lost in {config.mode.value} mode"
            )

        if metrics.critical_retention < 100.0:
            result.warnings.append(
                f"Critical vulnerability retention: {metrics.critical_retention:.1f}%"
            )

        if metrics.token_reduction < 20.0:
            result.warnings.append(
                f"Low token reduction: {metrics.token_reduction:.1f}%"
            )

        # Recommendations
        if metrics.accuracy_loss() > 5.0 and config.mode != ContextMode.RELAXED:
            result.recommendations.append(
                "Consider using RELAXED mode for higher accuracy"
            )

        if metrics.token_reduction > 50.0 and config.mode != ContextMode.STRICT:
            result.recommendations.append(
                "High token reduction achieved - STRICT mode may suffice"
            )

        if metrics.extra_findings > 0:
            result.recommendations.append(
                f"{metrics.extra_findings} additional findings detected - "
                "may indicate improved coverage or false positives"
            )

    def _build_summary(self, suite: ValidationSuite) -> Dict[str, Any]:
        """Build summary for validation suite."""
        summary = {
            "total_modes_tested": len(suite.results),
            "passed": sum(1 for r in suite.results.values() if r.status == ValidationStatus.PASS),
            "failed": sum(1 for r in suite.results.values() if r.status == ValidationStatus.FAIL),
            "warnings": sum(1 for r in suite.results.values() if r.status == ValidationStatus.WARN),
        }

        # Find best accuracy
        best_accuracy_mode = None
        best_retention = 0.0
        for mode, result in suite.results.items():
            if result.metrics.retention_rate > best_retention:
                best_retention = result.metrics.retention_rate
                best_accuracy_mode = mode

        summary["best_accuracy_mode"] = best_accuracy_mode
        summary["best_retention_rate"] = best_retention

        # Find best efficiency
        best_efficiency_mode = None
        best_reduction = 0.0
        for mode, result in suite.results.items():
            if result.status == ValidationStatus.PASS:
                if result.metrics.token_reduction > best_reduction:
                    best_reduction = result.metrics.token_reduction
                    best_efficiency_mode = mode

        summary["best_efficiency_mode"] = best_efficiency_mode
        summary["best_token_reduction"] = best_reduction

        return summary


def validate_optimization_accuracy(
    graph: Any,
    findings: List[Dict[str, Any]],
    mode: str = "standard",
) -> ValidationResult:
    """Convenience function to validate optimization accuracy.

    Args:
        graph: Knowledge graph
        findings: Ground truth findings from full graph
        mode: Context mode to validate

    Returns:
        ValidationResult
    """
    validator = AccuracyValidator(graph)
    return validator.validate_mode(findings, mode)


def compare_all_modes(
    graph: Any,
    findings: List[Dict[str, Any]],
) -> ValidationSuite:
    """Compare accuracy across all context modes.

    Args:
        graph: Knowledge graph
        findings: Ground truth findings

    Returns:
        ValidationSuite with all results
    """
    validator = AccuracyValidator(graph)
    return validator.validate_all_modes(findings)


def get_recommended_mode(
    graph: Any,
    findings: List[Dict[str, Any]],
    prefer_accuracy: bool = True,
) -> Tuple[str, ValidationResult]:
    """Get recommended mode based on validation.

    Args:
        graph: Knowledge graph
        findings: Ground truth findings
        prefer_accuracy: Whether to prefer accuracy over efficiency

    Returns:
        Tuple of (mode_name, validation_result)
    """
    suite = compare_all_modes(graph, findings)

    if prefer_accuracy:
        # Return mode with best retention that passes
        best_mode = None
        best_retention = 0.0
        for mode, result in suite.results.items():
            if result.status != ValidationStatus.FAIL:
                if result.metrics.retention_rate > best_retention:
                    best_retention = result.metrics.retention_rate
                    best_mode = mode
    else:
        # Return mode with best token reduction that passes
        best_mode = suite.get_best_mode()

    if best_mode is None:
        # Fall back to relaxed (highest accuracy)
        best_mode = "relaxed"

    return best_mode, suite.results[best_mode]
