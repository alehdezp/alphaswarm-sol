"""
Intent Annotation Package

Captures LLM-inferred business intent and security assumptions.
This is THE KEY COMPONENT for semantic vulnerability detection.
"""

from .schema import (
    BusinessPurpose,
    TrustLevel,
    TrustAssumption,
    InferredInvariant,
    FunctionIntent,
)
from .annotator import (
    IntentAnnotator,
    IntentCache,
)
from .integration import (
    IntentEnrichedGraph,
    enrich_graph_with_intent,
)
from .validation import (
    IntentValidator,
    ValidationResult,
    INTENT_VALIDATION_RULES,
)

__all__ = [
    "BusinessPurpose",
    "TrustLevel",
    "TrustAssumption",
    "InferredInvariant",
    "FunctionIntent",
    "IntentAnnotator",
    "IntentCache",
    "IntentEnrichedGraph",
    "enrich_graph_with_intent",
    "IntentValidator",
    "ValidationResult",
    "INTENT_VALIDATION_RULES",
]
