"""Query engine for the True VKG."""

from alphaswarm_sol.queries.errors import (
    EmptyPatternStoreError,
    PatternDirectoryNotFoundError,
    PatternLoadError,
)
from alphaswarm_sol.queries.executor import QueryExecutor
from alphaswarm_sol.queries.intent import Intent, parse_intent
from alphaswarm_sol.queries.planner import QueryPlan, QueryPlanner
from alphaswarm_sol.queries.patterns import PatternEngine, PatternStore, get_patterns
from alphaswarm_sol.queries.results_v2 import (
    ResultsV2,
    FindingV2,
    ClauseMatrix,
    ClauseResult,
    PatternResultPackager,
    package_pattern_results,
)
from alphaswarm_sol.queries.label_functions import (
    LABEL_FUNCTIONS,
    set_label_context,
    clear_label_context,
    has_label,
    missing_label,
    has_any_label,
    has_all_labels,
    label_confidence,
    labels_in_category,
    has_category,
    label_count,
    get_label_reasoning,
    get_available_functions,
)

__all__ = [
    # Core query types
    "Intent",
    "QueryPlan",
    "QueryPlanner",
    "QueryExecutor",
    "PatternEngine",
    "PatternStore",
    "get_patterns",
    "parse_intent",
    # Pattern loading exceptions
    "PatternLoadError",
    "PatternDirectoryNotFoundError",
    "EmptyPatternStoreError",
    # v2 Result packaging
    "ResultsV2",
    "FindingV2",
    "ClauseMatrix",
    "ClauseResult",
    "PatternResultPackager",
    "package_pattern_results",
    # Label query functions
    "LABEL_FUNCTIONS",
    "set_label_context",
    "clear_label_context",
    "has_label",
    "missing_label",
    "has_any_label",
    "has_all_labels",
    "label_confidence",
    "labels_in_category",
    "has_category",
    "label_count",
    "get_label_reasoning",
    "get_available_functions",
]
