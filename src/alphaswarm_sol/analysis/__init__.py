"""Analysis result aggregation and partial result handling."""

from .results import (
    SourceResult,
    AggregatedResults,
    ResultAggregator,
)
from .partial import (
    format_partial_results,
    render_partial_results_rich,
    merge_partial_results,
    PartialResultHandler,
)

__all__ = [
    "SourceResult",
    "AggregatedResults",
    "ResultAggregator",
    "format_partial_results",
    "render_partial_results_rich",
    "merge_partial_results",
    "PartialResultHandler",
]
