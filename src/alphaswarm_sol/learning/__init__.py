"""Conservative learning module for VKG 4.0.

This module provides:
- Bootstrap data generation from benchmark results
- Confidence bounds based on empirical data
- Time-based learning decay
- Learning event tracking
- A/B testing infrastructure
- Rollback capabilities

Key Design Decisions:
1. Learning is OFF by default - must be explicitly enabled
2. Confidence bounds prevent death spirals (min 0.15, max 0.98)
3. 30-day half-life ensures fresh lessons matter more
4. Bayesian calibration handles small samples gracefully
"""

from __future__ import annotations

from alphaswarm_sol.learning.types import (
    PatternBaseline,
    ConfidenceBounds,
    LearningEvent,
    EventType,
    SimilarityKey,
    SimilarityTier,
)
from alphaswarm_sol.learning.bootstrap import (
    BootstrapGenerator,
    generate_bootstrap_data,
    load_manifest,
)
from alphaswarm_sol.learning.bounds import (
    BoundsManager,
    calculate_bounds,
    wilson_score_interval,
)
from alphaswarm_sol.learning.similarity import (
    SimilarityEngine,
    extract_guards,
)
from alphaswarm_sol.learning.decay import (
    DecayConfig,
    DecayCalculator,
    get_decay_calculator,
    apply_decay,
    is_relevant,
    time_weighted_confidence,
)
from alphaswarm_sol.learning.events import (
    EventContext,
    EnrichedEvent,
    EventStore,
    generate_event_id,
    default_adjustment,
    create_event_from_finding,
)
from alphaswarm_sol.learning.fp_recorder import (
    FPPattern,
    FPWarning,
    FalsePositiveRecorder,
)
from alphaswarm_sol.learning.labels import (
    ROLE_LABELS,
    RELATIONSHIP_LABELS,
    ALL_LABELS,
    is_valid_label,
    label_categories,
    label_relevant_to_category,
)
from alphaswarm_sol.learning.overlay import (
    AssertionKind,
    LearningAssertion,
    LearningOverlayStore,
    format_overlay_context,
)
from alphaswarm_sol.learning.post_bead import (
    LearningConfig,
    FindingStub,
    PostBeadLearner,
    build_finding_stub,
    build_finding_dict,
    load_learning_config,
)
from alphaswarm_sol.learning.ab_testing import (
    Variant,
    ABTestConfig,
    ABTestResult,
    PatternABTest,
    ABTestManager,
)
from alphaswarm_sol.learning.rollback import (
    LearningSnapshot,
    VersionManager,
    DegradationAlert,
    AutoRollback,
    rollback_pattern,
    rollback_to_baseline,
)

__all__ = [
    # Types
    "PatternBaseline",
    "ConfidenceBounds",
    "LearningEvent",
    "EventType",
    "SimilarityKey",
    "SimilarityTier",
    # Bootstrap
    "BootstrapGenerator",
    "generate_bootstrap_data",
    "load_manifest",
    # Bounds
    "BoundsManager",
    "calculate_bounds",
    "wilson_score_interval",
    # Similarity
    "SimilarityEngine",
    "extract_guards",
    # Decay
    "DecayConfig",
    "DecayCalculator",
    "get_decay_calculator",
    "apply_decay",
    "is_relevant",
    "time_weighted_confidence",
    # Events
    "EventContext",
    "EnrichedEvent",
    "EventStore",
    "generate_event_id",
    "default_adjustment",
    "create_event_from_finding",
    # FP Recorder
    "FPPattern",
    "FPWarning",
    "FalsePositiveRecorder",
    # Labels
    "ROLE_LABELS",
    "RELATIONSHIP_LABELS",
    "ALL_LABELS",
    "is_valid_label",
    "label_categories",
    "label_relevant_to_category",
    # Overlay
    "AssertionKind",
    "LearningAssertion",
    "LearningOverlayStore",
    "format_overlay_context",
    # Post-bead learning
    "LearningConfig",
    "FindingStub",
    "PostBeadLearner",
    "build_finding_stub",
    "build_finding_dict",
    "load_learning_config",
    # A/B Testing
    "Variant",
    "ABTestConfig",
    "ABTestResult",
    "PatternABTest",
    "ABTestManager",
    # Rollback
    "LearningSnapshot",
    "VersionManager",
    "DegradationAlert",
    "AutoRollback",
    "rollback_pattern",
    "rollback_to_baseline",
]
