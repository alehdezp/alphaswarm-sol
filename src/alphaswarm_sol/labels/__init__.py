"""Semantic Labeling for VKG.

This module provides LLM-driven semantic labeling for functions,
enabling detection of policy mismatches and invariant violations.

Labels are organized as category.subcategory (e.g., "access_control.owner_only")
and support confidence levels (HIGH, MEDIUM, LOW) for LLM-assigned labels.

Key Components:
- LabelCategory: Top-level categories (access_control, state_mutation, etc.)
- LabelDefinition: Label definitions with examples and negations
- CORE_TAXONOMY: ~20 pre-defined labels covering key security behaviors
- FunctionLabel: Label attached to a function with confidence and source
- LabelSet: Collection of labels for a single function
- LabelOverlay: Graph-level label storage (separate from core properties)
- LLMLabeler: Microagent for LLM-based labeling with tool calling
- LabelValidator: Validation and quality scoring for label sets
- LabelFilter: Context-filtered label retrieval
- LabelEvaluator: Evaluation harness for measuring label quality

CLI Usage:
    # Build graph with labeling
    uv run alphaswarm build-kg ./contracts --with-labels

    # Label an existing graph
    uv run alphaswarm label .vrs/graphs/graph.json

    # Export labels
    uv run alphaswarm label-export labels.json labels.yaml -f yaml

Python Usage:
    from alphaswarm_sol.labels import LLMLabeler, LabelingConfig, LabelOverlay

    # Create labeler
    labeler = LLMLabeler(provider)

    # Label functions
    result = await labeler.label_functions(graph, function_ids)

    # Get overlay
    overlay = labeler.get_overlay()

    # Query labels
    labels = overlay.get_labels("function_id")

    # Export/Import
    overlay.export_json(Path("labels.json"))
    loaded = LabelOverlay.from_json(Path("labels.json"))
"""

from .taxonomy import (
    LabelCategory,
    LabelDefinition,
    CORE_TAXONOMY,
    get_label_by_id,
    get_labels_by_category,
    is_valid_label,
    get_negation,
    get_all_label_ids,
)
from .schema import (
    LabelConfidence,
    LabelSource,
    FunctionLabel,
    LabelSet,
)
from .overlay import (
    LabelOverlay,
)
from .validator import (
    ValidationStatus,
    ValidationResult,
    LabelSetValidation,
    ConfidenceDistribution,
    QualityScore,
    PrecisionEstimate,
    LabelValidator,
    validate_labels,
)
from .labeler import (
    LabelingConfig,
    LabelingResult,
    BatchLabelingResult,
    LLMLabeler,
)
from .tools import (
    build_label_tools,
    LABELING_TOOL_CHOICE,
    parse_label_from_tool_call,
    validate_tool_response,
    extract_labels_from_tool_calls,
)
from .filter import (
    CONTEXT_TO_CATEGORIES,
    FilteredLabels,
    LabelFilter,
    get_relevant_categories,
    filter_labels_for_context,
)
from .evaluation import (
    PrecisionMetrics,
    DetectionMetrics,
    TokenMetrics,
    EvaluationReport,
    LabelEvaluator,
    run_evaluation,
    compare_overlays,
)

__all__ = [
    # Taxonomy
    "LabelCategory",
    "LabelDefinition",
    "CORE_TAXONOMY",
    "get_label_by_id",
    "get_labels_by_category",
    "is_valid_label",
    "get_negation",
    "get_all_label_ids",
    # Schema
    "LabelConfidence",
    "LabelSource",
    "FunctionLabel",
    "LabelSet",
    # Overlay
    "LabelOverlay",
    # Validator
    "ValidationStatus",
    "ValidationResult",
    "LabelSetValidation",
    "ConfidenceDistribution",
    "QualityScore",
    "PrecisionEstimate",
    "LabelValidator",
    "validate_labels",
    # Labeler
    "LabelingConfig",
    "LabelingResult",
    "BatchLabelingResult",
    "LLMLabeler",
    # Tools
    "build_label_tools",
    "LABELING_TOOL_CHOICE",
    "parse_label_from_tool_call",
    "validate_tool_response",
    "extract_labels_from_tool_calls",
    # Filter
    "CONTEXT_TO_CATEGORIES",
    "FilteredLabels",
    "LabelFilter",
    "get_relevant_categories",
    "filter_labels_for_context",
    # Evaluation
    "PrecisionMetrics",
    "DetectionMetrics",
    "TokenMetrics",
    "EvaluationReport",
    "LabelEvaluator",
    "run_evaluation",
    "compare_overlays",
]
