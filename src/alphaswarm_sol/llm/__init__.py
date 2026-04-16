"""Phase 12 + VKG 3.5: LLM Integration.

This module provides LLM-enhanced analysis capabilities for the VKG.

Key features:
- Annotation schema for LLM-generated insights
- Step-back prompting for context-aware analysis
- RAG integration with pattern library
- Annotation caching for efficiency
- Multi-provider abstraction with automatic fallback (VKG 3.5 P0-T0)
- Cost tracking and budget enforcement
- Context optimization with hierarchical triage (VKG 3.5 P0-T0c)
- Semantic compression for token efficiency
"""

from alphaswarm_sol.llm.annotations import (
    LLMAnnotation,
    AnnotationType,
    AnnotationSource,
    create_annotation,
    merge_annotations,
)
from alphaswarm_sol.llm.prompts import (
    StepBackPrompt,
    AnalysisPrompt,
    PromptBuilder,
    generate_analysis_prompt,
    generate_step_back_prompt,
)
from alphaswarm_sol.llm.cache import (
    AnnotationCache,
    CacheEntry,
    get_cache,
    clear_cache,
)
from alphaswarm_sol.llm.rag import (
    PatternRAG,
    RAGResult,
    retrieve_similar_patterns,
)

# VKG 3.5 P0-T0: LLM Provider Abstraction
from alphaswarm_sol.llm.client import LLMClient, UsageStats
from alphaswarm_sol.llm.config import LLMConfig, Provider, ProviderConfig, PROVIDER_CONFIGS
from alphaswarm_sol.llm.providers import LLMProvider, LLMResponse
from alphaswarm_sol.llm.research import ResearchClient, ResearchResults, SearchResult

# VKG 3.5 P0-T0c: Context Optimization
from alphaswarm_sol.llm.triage import TriageClassifier, TriageLevel, TriageResult
from alphaswarm_sol.llm.compressor import SemanticCompressor, CompressionTier, CompressedContext
from alphaswarm_sol.llm.slicer import ContextSlicer, ContextSlice
from alphaswarm_sol.llm.optimizer import ContextOptimizer, OptimizedContext
from alphaswarm_sol.llm.templates import (
    get_template,
    get_system_prompt,
    TEMPLATES,
    SYSTEM_PROMPTS,
)

# VKG 3.5 P0-T0d: Efficiency Metrics & Feedback
from alphaswarm_sol.llm.telemetry import (
    TelemetryCollector,
    AnalysisEvent,
    SessionMetrics,
    Verdict,
    get_collector,
)
from alphaswarm_sol.llm.metrics import (
    MetricsAnalyzer,
    DriftDetector,
    FeedbackLoop,
    DriftAlert,
    MetricsTrend,
)

# VKG 4.0 Phase 9: Context Policy
from alphaswarm_sol.llm.context import Context, ContextItem, Finding, ExternalCall
from alphaswarm_sol.llm.context_policy import (
    ContextPolicy,
    ContextPolicyLevel,
    ContextAuditEntry,
    require_explicit_relaxed,
    get_policy,
    validate_context_for_llm,
)

# VKG 4.0 Phase 9.4: Unified Context Modes
from alphaswarm_sol.llm.context_modes import (
    ContextMode,
    ContextModeConfig,
    ContextModeManager,
    ContextExtractionResult,
    get_context_config,
    extract_context_for_findings,
)

# VKG 4.0 Phase 11.7: LLM Safety Guardrails
from alphaswarm_sol.llm.sanitize import (
    CodeSanitizer,
    InjectionRisk,
    SanitizationResult,
    sanitize_for_llm,
    check_injection_risk,
    strip_comments,
)
from alphaswarm_sol.llm.validate import (
    OutputValidator,
    ValidationResult,
    ValidationError,
    LLMVerdict,
    Verdict as LLMVerdictType,  # Alias to avoid conflict with telemetry.Verdict
    validate_llm_output,
    is_valid_verdict,
    extract_json_from_response,
    VERDICT_SCHEMA,
)

# VKG 4.0 Phase 11.8: Prompt Contract
from alphaswarm_sol.llm.contract import (
    PromptContract,
    PromptInput,
    PromptType,
    ContractAuditEntry,
    ContractViolation,
    get_prompt_template,
    build_standard_prompt,
    create_contract,
    PROMPT_TEMPLATES,
)

# VKG 4.0 Phase 11.11: Rate Limiting & Cost Caps
from alphaswarm_sol.llm.limits import (
    LLMLimits,
    LimitType,
    LimitExceededError,
    UsageReport,
    RateLimiter,
    create_rate_limiter,
    check_budget,
    get_usage_summary,
)

# VKG 4.0 Phase 11.3: Tier B Analysis Workflow
from alphaswarm_sol.llm.confidence import (
    ConfidenceEvaluator,
    ConfidenceResult,
    ConfidenceAction,
    ConfidenceThresholds,
    evaluate_confidence,
    needs_tier_b_analysis,
)
from alphaswarm_sol.llm.workflow import (
    TierBWorkflow,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStats,
    create_tier_b_workflow,
)

# VKG 4.0 Phase 11.4: False Positive Filtering
from alphaswarm_sol.llm.fp_filter import (
    FPFilter,
    FPFilterResult,
    FPFilterDecision,
    FPFilterMetrics,
    create_fp_filter,
    calculate_fp_reduction,
)

# VKG 4.0 Phase 11.9: Noninteractive Batch Mode
from alphaswarm_sol.llm.batch import (
    NoninteractiveBatchRunner,
    CIRunner,
    CIError,
    BatchConfig,
    BatchResult,
    BatchStatus,
    BatchProgress,
    OutputMode,
    create_batch_runner,
    create_ci_runner,
)

# VKG 4.0 Phase 11.12: Multi-Tier Model Support
from alphaswarm_sol.llm.tiers import (
    TierRouter,
    TierBContext,
    ModelTier,
    ModelTierConfig,
    AnalysisType,
    Complexity,
    TierStats,
    create_tier_router,
    estimate_batch_tiers,
)

# VKG 4.0 Phase 12.8: LLM Subagent Orchestration
from alphaswarm_sol.llm.subagents import (
    LLMSubagentManager,
    SubagentTask,
    SubagentResult,
    TaskType,
    TOONEncoder,
    TASK_TIER_DEFAULTS,
    create_subagent_manager,
    create_task,
    estimate_batch_cost,
)

# Phase 5.9: Deterministic Evidence IDs
from alphaswarm_sol.llm.evidence_ids import (
    EvidenceID,
    EvidenceIDError,
    EvidenceRegistry,
    EvidenceResolutionError,
    SourceSpan,
    ClauseEvidence,
    ClauseMatrixBuilder,
    generate_evidence_id,
    validate_evidence_id,
    validate_build_hash as validate_evidence_build_hash,
    parse_evidence_id,
    build_evidence_ref,
    build_evidence_refs_from_nodes,
    EVIDENCE_ID_PATTERN,
    BUILD_HASH_PATTERN as EVIDENCE_BUILD_HASH_PATTERN,
)

__all__ = [
    # Annotations
    "LLMAnnotation",
    "AnnotationType",
    "AnnotationSource",
    "create_annotation",
    "merge_annotations",
    # Prompts
    "StepBackPrompt",
    "AnalysisPrompt",
    "PromptBuilder",
    "generate_analysis_prompt",
    "generate_step_back_prompt",
    # Cache
    "AnnotationCache",
    "CacheEntry",
    "get_cache",
    "clear_cache",
    # RAG
    "PatternRAG",
    "RAGResult",
    "retrieve_similar_patterns",
    # VKG 3.5: Provider Abstraction
    "LLMClient",
    "UsageStats",
    "LLMConfig",
    "Provider",
    "ProviderConfig",
    "PROVIDER_CONFIGS",
    "LLMProvider",
    "LLMResponse",
    "ResearchClient",
    "ResearchResults",
    "SearchResult",
    # VKG 3.5: Context Optimization
    "TriageClassifier",
    "TriageLevel",
    "TriageResult",
    "SemanticCompressor",
    "CompressionTier",
    "CompressedContext",
    "ContextSlicer",
    "ContextSlice",
    "ContextOptimizer",
    "OptimizedContext",
    "get_template",
    "get_system_prompt",
    "TEMPLATES",
    "SYSTEM_PROMPTS",
    # VKG 3.5: Efficiency Metrics & Feedback
    "TelemetryCollector",
    "AnalysisEvent",
    "SessionMetrics",
    "Verdict",
    "get_collector",
    "MetricsAnalyzer",
    "DriftDetector",
    "FeedbackLoop",
    "DriftAlert",
    "MetricsTrend",
    # VKG 4.0 Phase 9: Context Policy
    "Context",
    "ContextItem",
    "Finding",
    "ExternalCall",
    "ContextPolicy",
    "ContextPolicyLevel",
    "ContextAuditEntry",
    "require_explicit_relaxed",
    "get_policy",
    "validate_context_for_llm",
    # VKG 4.0 Phase 9.4: Unified Context Modes
    "ContextMode",
    "ContextModeConfig",
    "ContextModeManager",
    "ContextExtractionResult",
    "get_context_config",
    "extract_context_for_findings",
    # VKG 4.0 Phase 11.7: LLM Safety Guardrails
    "CodeSanitizer",
    "InjectionRisk",
    "SanitizationResult",
    "sanitize_for_llm",
    "check_injection_risk",
    "strip_comments",
    "OutputValidator",
    "ValidationResult",
    "ValidationError",
    "LLMVerdict",
    "LLMVerdictType",
    "validate_llm_output",
    "is_valid_verdict",
    "extract_json_from_response",
    "VERDICT_SCHEMA",
    # VKG 4.0 Phase 11.8: Prompt Contract
    "PromptContract",
    "PromptInput",
    "PromptType",
    "ContractAuditEntry",
    "ContractViolation",
    "get_prompt_template",
    "build_standard_prompt",
    "create_contract",
    "PROMPT_TEMPLATES",
    # VKG 4.0 Phase 11.11: Rate Limiting & Cost Caps
    "LLMLimits",
    "LimitType",
    "LimitExceededError",
    "UsageReport",
    "RateLimiter",
    "create_rate_limiter",
    "check_budget",
    "get_usage_summary",
    # VKG 4.0 Phase 11.3: Tier B Analysis Workflow
    "ConfidenceEvaluator",
    "ConfidenceResult",
    "ConfidenceAction",
    "ConfidenceThresholds",
    "evaluate_confidence",
    "needs_tier_b_analysis",
    "TierBWorkflow",
    "WorkflowResult",
    "WorkflowStatus",
    "WorkflowStats",
    "create_tier_b_workflow",
    # VKG 4.0 Phase 11.4: False Positive Filtering
    "FPFilter",
    "FPFilterResult",
    "FPFilterDecision",
    "FPFilterMetrics",
    "create_fp_filter",
    "calculate_fp_reduction",
    # VKG 4.0 Phase 11.9: Noninteractive Batch Mode
    "NoninteractiveBatchRunner",
    "CIRunner",
    "CIError",
    "BatchConfig",
    "BatchResult",
    "BatchStatus",
    "BatchProgress",
    "OutputMode",
    "create_batch_runner",
    "create_ci_runner",
    # VKG 4.0 Phase 11.12: Multi-Tier Model Support
    "TierRouter",
    "TierBContext",
    "ModelTier",
    "ModelTierConfig",
    "AnalysisType",
    "Complexity",
    "TierStats",
    "create_tier_router",
    "estimate_batch_tiers",
    # VKG 4.0 Phase 12.8: LLM Subagent Orchestration
    "LLMSubagentManager",
    "SubagentTask",
    "SubagentResult",
    "TaskType",
    "TOONEncoder",
    "TASK_TIER_DEFAULTS",
    "create_subagent_manager",
    "create_task",
    "estimate_batch_cost",
    # Phase 5.9: Deterministic Evidence IDs
    "EvidenceID",
    "EvidenceIDError",
    "EvidenceRegistry",
    "EvidenceResolutionError",
    "SourceSpan",
    "ClauseEvidence",
    "ClauseMatrixBuilder",
    "generate_evidence_id",
    "validate_evidence_id",
    "validate_evidence_build_hash",
    "parse_evidence_id",
    "build_evidence_ref",
    "build_evidence_refs_from_nodes",
    "EVIDENCE_ID_PATTERN",
    "EVIDENCE_BUILD_HASH_PATTERN",
]
