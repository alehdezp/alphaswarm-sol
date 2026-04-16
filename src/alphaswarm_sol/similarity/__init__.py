"""
Semantic Code Similarity Engine

Novel Solution 9: Find semantically similar code across contracts
even when syntactically different.

Key capabilities:
- Operation-based fingerprinting (what code does, not how it looks)
- CFG-based structural similarity
- Behavioral signature matching
- Vulnerability pattern correlation
"""

from .fingerprint import (
    SemanticFingerprint,
    FingerprintType,
    OperationSequence,
    FingerprintGenerator,
    FingerprintConfig,
)

from .similarity import (
    SimilarityScore,
    SimilarityType,
    SimilarityCalculator,
    SimilarityConfig,
    SimilarityResult,
)

from .index import (
    ContractIndex,
    IndexEntry,
    IndexConfig,
    SearchResult,
    SearchConfig,
)

from .matcher import (
    PatternMatcher,
    MatchResult,
    MatchType,
    CloneDetector,
    CloneType,
    Clone,
)

from .engine import (
    SimilarityEngine,
    EngineConfig,
    AnalysisResult,
    SimilarContract,
    VulnerabilityCorrelation,
)

__all__ = [
    # Fingerprint
    "SemanticFingerprint",
    "FingerprintType",
    "OperationSequence",
    "FingerprintGenerator",
    "FingerprintConfig",
    # Similarity
    "SimilarityScore",
    "SimilarityType",
    "SimilarityCalculator",
    "SimilarityConfig",
    "SimilarityResult",
    # Index
    "ContractIndex",
    "IndexEntry",
    "IndexConfig",
    "SearchResult",
    "SearchConfig",
    # Matcher
    "PatternMatcher",
    "MatchResult",
    "MatchType",
    "CloneDetector",
    "CloneType",
    "Clone",
    # Engine
    "SimilarityEngine",
    "EngineConfig",
    "AnalysisResult",
    "SimilarContract",
    "VulnerabilityCorrelation",
]
