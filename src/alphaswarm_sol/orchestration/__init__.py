"""Orchestration Module for VKG.

This module provides:

1. Tool Orchestration (Phase 5):
   - Run multiple analysis tools (VKG, Slither, Aderyn)
   - Deduplicate and merge findings
   - Generate combined reports

2. Pool Orchestration (Phase 4):
   - Canonical artifact schemas (Pool, Verdict, Scope, EvidencePacket)
   - Pool management and storage
   - Batch processing for audit waves

Philosophy:
- VKG is not a replacement for existing tools - it's an orchestrator
- Combine findings from multiple sources for comprehensive coverage
- Deduplicate intelligently (same location + similar category = merge)
- Flag disagreements for human review
- All verdicts require human review (per PHILOSOPHY.md)

Tool Orchestration Usage:
    from alphaswarm_sol.orchestration import ToolRunner, deduplicate_findings, generate_report

    runner = ToolRunner(Path("./my-project"))
    results = runner.run_all()

    all_findings = []
    for r in results:
        all_findings.extend(r.findings)

    deduped = deduplicate_findings(all_findings)
    report = generate_report("./my-project", results, deduped)

Pool Orchestration Usage:
    from alphaswarm_sol.orchestration import (
        Pool, PoolStatus, Scope, Verdict, VerdictConfidence,
        EvidencePacket, EvidenceItem, PoolManager, PoolStorage
    )

    # Create a scope and pool
    scope = Scope(files=["contracts/Vault.sol"])
    pool = Pool(id="audit-wave-001", scope=scope)
    pool.add_bead("VKG-042")

    # Store pools
    storage = PoolStorage(Path(".vrs/pools"))
    storage.save_pool(pool)
"""

from alphaswarm_sol.orchestration.runner import (
    ToolStatus,
    ToolResult,
    ToolRunner,
)
from alphaswarm_sol.orchestration.dedup import (
    DeduplicatedFinding,
    deduplicate_findings,
    merge_findings,
    get_disagreements,
    get_unique_to_tool,
    CATEGORY_ALIASES,
)
from alphaswarm_sol.orchestration.output import (
    OrchestratorReport,
    generate_report,
    format_report,
    format_markdown_report,
)
from alphaswarm_sol.orchestration.schemas import (
    PoolStatus,
    VerdictConfidence,
    Scope,
    EvidenceItem,
    EvidencePacket,
    DebateClaim,
    DebateRecord,
    Verdict,
    Pool,
)
from alphaswarm_sol.orchestration.pool import (
    PoolStorage,
    PoolManager,
)
from alphaswarm_sol.orchestration.confidence import (
    ValidationErrorType,
    ValidationError,
    ValidationResult,
    ConfidenceEnforcer,
    enforce_confidence,
    validate_confidence,
)
from alphaswarm_sol.orchestration.rules import (
    RuleType,
    RuleSeverity,
    RuleViolation,
    BatchingPolicy,
    DEFAULT_BATCHING,
    OrchestrationRules,
)
from alphaswarm_sol.orchestration.router import (
    RouteAction,
    RouteDecision,
    Router,
    route_pool,
)
from alphaswarm_sol.orchestration.loop import (
    LoopPhase,
    PhaseResult,
    LoopConfig,
    ExecutionLoop,
)
from alphaswarm_sol.orchestration.queue import (
    WorkItemStatus,
    WorkItem,
    QueueLimits,
    QueueSnapshot,
    BackpressureError,
    WorkQueue,
)
from alphaswarm_sol.orchestration.debate import (
    DebatePhase,
    DebateRound,
    DebateConfig,
    DebateResult,
    DebateOrchestrator,
    run_debate,
)
from alphaswarm_sol.orchestration.handlers import (
    HandlerConfig,
    BaseHandler,
    BuildGraphHandler,
    LoadContextHandler,
    DetectPatternsHandler,
    CreateBeadsHandler,
    SpawnAttackersHandler,
    SpawnDefendersHandler,
    SpawnVerifiersHandler,
    RunDebateHandler,
    CollectVerdictsHandler,
    GenerateReportHandler,
    FlagForHumanHandler,
    CompleteHandler,
    WaitHandler,
    create_default_handlers,
    make_idempotency_key,
    hash_payload,
)
from alphaswarm_sol.orchestration.idempotency import (
    IdempotencyStatus,
    IdempotencyRecord,
    RetryConfig,
    IdempotencyStore,
    idempotent_execute,
)
from alphaswarm_sol.orchestration.replay import (
    PoolEvent,
    PoolEventStore,
    StateMismatch,
    ReplayResult,
    ReplayEngine,
)
from alphaswarm_sol.orchestration.dismissal import (
    DismissalCategory,
    DismissalReason,
    DismissalLog,
    BatchDismissal,
    dismiss_beads,
)
from alphaswarm_sol.orchestration.cross_verify import (
    VerificationResult,
    CrossModelVerifier,
    get_diverse_verifier,
    create_mock_verifier,
)
from alphaswarm_sol.orchestration.batch import (
    BatchPriority,
    RankingMethod,
    PatternCostEstimate,
    AdaptiveBatch,
    CacheKey,
    ForkResult,
    RankedResult,
    BatchManifest,
    AdaptiveBatcher,
    ForkThenRank,
    BatchDiscoveryOrchestrator,
    DEFAULT_COST_WEIGHTS,
)
from alphaswarm_sol.orchestration.creative import (
    NearMissType,
    MutationType,
    CounterfactualType,
    ShadowPatternStatus,
    NearMissResult,
    MutationResult,
    CounterfactualProbe,
    AnomalyMotif,
    ShadowPattern,
    CreativeDiscoveryConfig,
    CreativeDiscoveryResult,
    NearMissMiner,
    PatternMutator,
    CounterfactualProber,
    AnomalyDetector,
    ShadowPatternGenerator,
    CreativeDiscoveryLoop,
    TIER_B_MAX_CONFIDENCE,
)
from alphaswarm_sol.orchestration.failures import (
    FailureType,
    FailureSeverity,
    RecoveryAction,
    FailureMetadata,
    RecoveryPlaybookEntry,
    FailureClassifier,
    RecoveryPlaybook,
    classify_failure,
    get_recovery_action,
)
from alphaswarm_sol.orchestration.workspace import (
    WorkspaceMetadata,
    WorkspaceError,
    WorkspaceManager,
    DEFAULT_WORKSPACE_ROOT,
    # Backward compatibility aliases
    WorktreeMetadata,
    WorktreeError,
    WorktreeManager,
    DEFAULT_WORKTREE_ROOT,
)

__all__ = [
    # Runner
    "ToolStatus",
    "ToolResult",
    "ToolRunner",
    # Deduplication
    "DeduplicatedFinding",
    "deduplicate_findings",
    "merge_findings",
    "get_disagreements",
    "get_unique_to_tool",
    "CATEGORY_ALIASES",
    # Output
    "OrchestratorReport",
    "generate_report",
    "format_report",
    "format_markdown_report",
    # Schemas (Phase 4)
    "PoolStatus",
    "VerdictConfidence",
    "Scope",
    "EvidenceItem",
    "EvidencePacket",
    "DebateClaim",
    "DebateRecord",
    "Verdict",
    "Pool",
    # Pool Management (Phase 4)
    "PoolStorage",
    "PoolManager",
    # Confidence Enforcement (ORCH-09, ORCH-10)
    "ValidationErrorType",
    "ValidationError",
    "ValidationResult",
    "ConfidenceEnforcer",
    "enforce_confidence",
    "validate_confidence",
    # Orchestration Rules
    "RuleType",
    "RuleSeverity",
    "RuleViolation",
    "BatchingPolicy",
    "DEFAULT_BATCHING",
    "OrchestrationRules",
    # Router (ORCH-01)
    "RouteAction",
    "RouteDecision",
    "Router",
    "route_pool",
    # Execution Loop (ORCH-07)
    "LoopPhase",
    "PhaseResult",
    "LoopConfig",
    "ExecutionLoop",
    # Debate Protocol (04-05)
    "DebatePhase",
    "DebateRound",
    "DebateConfig",
    "DebateResult",
    "DebateOrchestrator",
    "run_debate",
    # Phase Handlers (04-05)
    "HandlerConfig",
    "BaseHandler",
    "BuildGraphHandler",
    "LoadContextHandler",
    "DetectPatternsHandler",
    "CreateBeadsHandler",
    "SpawnAttackersHandler",
    "SpawnDefendersHandler",
    "SpawnVerifiersHandler",
    "RunDebateHandler",
    "CollectVerdictsHandler",
    "GenerateReportHandler",
    "FlagForHumanHandler",
    "CompleteHandler",
    "WaitHandler",
    "create_default_handlers",
    # Batch Dismissal (Phase 5.1)
    "DismissalCategory",
    "DismissalReason",
    "DismissalLog",
    "BatchDismissal",
    "dismiss_beads",
    # Cross-Model Verification (Phase 5.1)
    "VerificationResult",
    "CrossModelVerifier",
    "get_diverse_verifier",
    "create_mock_verifier",
    # Batch Discovery Orchestration v2 (Phase 5.10)
    "BatchPriority",
    "RankingMethod",
    "PatternCostEstimate",
    "AdaptiveBatch",
    "CacheKey",
    "ForkResult",
    "RankedResult",
    "BatchManifest",
    "AdaptiveBatcher",
    "ForkThenRank",
    "BatchDiscoveryOrchestrator",
    "DEFAULT_COST_WEIGHTS",
    # Creative Discovery (Phase 5.10-09)
    "NearMissType",
    "MutationType",
    "CounterfactualType",
    "ShadowPatternStatus",
    "NearMissResult",
    "MutationResult",
    "CounterfactualProbe",
    "AnomalyMotif",
    "ShadowPattern",
    "CreativeDiscoveryConfig",
    "CreativeDiscoveryResult",
    "NearMissMiner",
    "PatternMutator",
    "CounterfactualProber",
    "AnomalyDetector",
    "ShadowPatternGenerator",
    "CreativeDiscoveryLoop",
    "TIER_B_MAX_CONFIDENCE",
    # Idempotency (Phase 07.1.1-02)
    "IdempotencyStatus",
    "IdempotencyRecord",
    "RetryConfig",
    "IdempotencyStore",
    "idempotent_execute",
    "make_idempotency_key",
    "hash_payload",
    # Work Queue (Phase 07.1.1-03)
    "WorkItemStatus",
    "WorkItem",
    "QueueLimits",
    "QueueSnapshot",
    "BackpressureError",
    "WorkQueue",
    # Replay Engine (Phase 07.1.1-04)
    "PoolEvent",
    "PoolEventStore",
    "StateMismatch",
    "ReplayResult",
    "ReplayEngine",
    # Failure Recovery (Phase 07.1.1-06)
    "FailureType",
    "FailureSeverity",
    "RecoveryAction",
    "FailureMetadata",
    "RecoveryPlaybookEntry",
    "FailureClassifier",
    "RecoveryPlaybook",
    "classify_failure",
    "get_recovery_action",
    # Workspace Isolation (Phase 07.3.1.9 - Jujutsu-based)
    "WorkspaceMetadata",
    "WorkspaceError",
    "WorkspaceManager",
    "DEFAULT_WORKSPACE_ROOT",
    # Backward compatibility (Phase 07.1.1-05 aliases)
    "WorktreeMetadata",
    "WorktreeError",
    "WorktreeManager",
    "DEFAULT_WORKTREE_ROOT",
]
