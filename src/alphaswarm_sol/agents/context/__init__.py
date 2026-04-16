"""Agent context extraction and merging.

This package provides context extraction from vulndocs and protocol packs,
merging them into unified context bundles for agent spawning, and verification
of context quality.

Key components:
- VulndocContextExtractor: Extract context from vulndocs + protocol pack
- ContextMerger: Merge multiple context sources
- ContextVerifier: Validate merged context quality
- ContextBundle: Unified context for agent spawning
"""

from alphaswarm_sol.agents.context.types import (
    BudgetPass,
    BudgetPolicy,
    BudgetValidation,
    ContextBundle,
    ContextDelta,
    ContextGating,
    ContextSection,
    RiskCategory,
    RiskProfile,
)
from alphaswarm_sol.agents.context.extractor import VulndocContextExtractor
from alphaswarm_sol.agents.context.merger import ContextMerger, MergeResult
from alphaswarm_sol.agents.context.verifier import (
    ContextVerifier,
    VerificationError,
    VerificationResult,
)
from alphaswarm_sol.agents.context.bead_factory import ContextBeadFactory

__all__ = [
    "BudgetPass",
    "BudgetPolicy",
    "BudgetValidation",
    "ContextBundle",
    "ContextDelta",
    "ContextGating",
    "ContextSection",
    "RiskCategory",
    "RiskProfile",
    "VulndocContextExtractor",
    "ContextMerger",
    "MergeResult",
    "ContextVerifier",
    "VerificationError",
    "VerificationResult",
    "ContextBeadFactory",
]
