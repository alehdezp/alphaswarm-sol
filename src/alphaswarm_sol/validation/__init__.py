"""Validation and benchmarking module for True VKG.

Provides benchmarks against real exploits, metrics calculation,
and real-world validation against audit reports.
"""

from alphaswarm_sol.validation.benchmarks import (
    ExploitBenchmark,
    BenchmarkResult,
    BenchmarkSuite,
    run_benchmarks,
)
from alphaswarm_sol.validation.metrics import (
    ConfusionMatrix,
    DetectionMetrics,
    MetricsCalculator,
    calculate_metrics,
)
from alphaswarm_sol.validation.comparison import (
    ToolComparison,
    ComparisonResult,
    compare_tools,
)
from alphaswarm_sol.validation.ground_truth import (
    VulnerabilityCategory,
    Severity,
    AuditFinding,
    ProjectGroundTruth,
    VKGFinding,
    MatchResult,
    ValidationResult,
    FindingMatcher,
    normalize_category,
    is_category_match,
    format_validation_report,
)

# Phase 9.5: Accuracy Validation
from alphaswarm_sol.validation.accuracy_validation import (
    AccuracyMetrics,
    AccuracyValidator,
    DetectionResult,
    ValidationResult as AccuracyValidationResult,
    ValidationStatus,
    ValidationSuite,
    compare_all_modes,
    get_recommended_mode,
    validate_optimization_accuracy,
)

__all__ = [
    # Benchmarks
    "ExploitBenchmark",
    "BenchmarkResult",
    "BenchmarkSuite",
    "run_benchmarks",
    # Metrics
    "ConfusionMatrix",
    "DetectionMetrics",
    "MetricsCalculator",
    "calculate_metrics",
    # Comparison
    "ToolComparison",
    "ComparisonResult",
    "compare_tools",
    # Ground Truth (Phase 5)
    "VulnerabilityCategory",
    "Severity",
    "AuditFinding",
    "ProjectGroundTruth",
    "VKGFinding",
    "MatchResult",
    "ValidationResult",
    "FindingMatcher",
    "normalize_category",
    "is_category_match",
    "format_validation_report",
    # Phase 9.5: Accuracy Validation
    "AccuracyMetrics",
    "AccuracyValidator",
    "DetectionResult",
    "AccuracyValidationResult",
    "ValidationStatus",
    "ValidationSuite",
    "compare_all_modes",
    "get_recommended_mode",
    "validate_optimization_accuracy",
]
