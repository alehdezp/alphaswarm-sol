"""Shared Pydantic vocabulary for the 3.1c evaluation pipeline.

All models that cross plan boundaries live here. Internal-only models
for specific plans (e.g., GVS internals) live in their own modules.

Design constraints:
- DC-1: RunMode classification — gate phase exits on non-simulated runs
- DC-2: No imports from kg or vulndocs subpackages
- DC-3: EvaluationPlugin protocol for pluggable scoring dimensions
- DC-5: TranscriptParser stays in tests/ — bridge via EvaluationInput

Field Stability Tiers (3.1e Plan 04):
- Track A (17 fields): VALIDITY_CLAIM — implement as specified
- Track B (7 fields): PROVISIONAL — tagged [pending-real-transcript-validation]
- Track C (11 fields): STRUCTURAL_PROXY — heuristic_ prefix where applicable

CONTRACT_VERSION: 02.0
CONSUMERS: [3.1c-02, 3.1c-03, 3.1c-04, 3.1c-05, 3.1c-06, 3.1c-07, 3.1c-08, 3.1c-12]
"""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# RunMode (DC-1)
# ---------------------------------------------------------------------------


class RunMode(str, Enum):
    """Execution mode for an evaluation run.

    Phase gates require ``headless`` or ``interactive`` — ``simulated``
    runs can never satisfy exit criteria.
    """

    SIMULATED = "simulated"
    HEADLESS = "headless"
    INTERACTIVE = "interactive"


# ---------------------------------------------------------------------------
# Reasoning Move Taxonomy (7-move decomposition)
# ---------------------------------------------------------------------------


class ReasoningMove(str, Enum):
    """The 7-move taxonomy for reasoning decomposition.

    Each move represents a distinct reasoning capability that can be
    scored independently by the dual-Opus evaluator (3.1c-07).
    """

    HYPOTHESIS_FORMATION = "hypothesis_formation"
    QUERY_FORMULATION = "query_formulation"
    RESULT_INTERPRETATION = "result_interpretation"
    EVIDENCE_INTEGRATION = "evidence_integration"
    CONTRADICTION_HANDLING = "contradiction_handling"
    CONCLUSION_SYNTHESIS = "conclusion_synthesis"
    SELF_CRITIQUE = "self_critique"


# ---------------------------------------------------------------------------
# Observation Records (hooks -> parser contract, Issue #2)
# ---------------------------------------------------------------------------


class ObservationRecord(BaseModel):
    """Single JSONL line written by observation hooks.

    Shared contract between 3.1c-02 (hooks that write) and 3.1c-03
    (parser that reads).  Every observation hook MUST produce records
    matching this schema.
    """

    timestamp: str = Field(description="ISO 8601 timestamp of the observation")
    session_id: str = Field(description="Claude Code session identifier")
    event_type: str = Field(
        description="Hook event that produced this record "
        "(e.g., 'tool_use', 'tool_result', 'bskg_query', 'message', "
        "'session_start', 'agent_stop')"
    )
    hook_name: str = Field(description="Name of the hook script that produced this")
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific payload. Structure varies by event_type.",
    )

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Plugin Scores (DC-3)
# ---------------------------------------------------------------------------


class PluginScore(BaseModel):
    """Standard score envelope returned by any EvaluationPlugin.

    Score is 0-100 integer. Plugins may attach arbitrary details.
    """

    plugin_name: str = Field(description="Name of the plugin that produced this score")
    score: int = Field(ge=0, le=100, description="Overall score (0=worst, 100=best)")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Plugin-specific scoring breakdown",
    )
    explanation: str = Field(
        default="", description="Human-readable explanation of the score"
    )
    applicable: bool = Field(
        default=True,
        description="Whether this plugin was applicable to the workflow. "
        "Non-applicable plugins are excluded from effective_score().",
    )


class GraphValueScore(PluginScore):
    """BSKG-specific extension of PluginScore.

    Carries graph-utilization metrics alongside the standard score.
    Produced by the GraphValueScorer plugin (3.1c-04).
    """

    query_coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of expected query types issued",
    )
    citation_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of query results cited in conclusions",
    )
    graph_first_compliant: bool = Field(
        default=False,
        description="Whether BSKG queries preceded conclusions",
    )
    graph_first_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Graduated graph-first score: proportion of Read calls "
        "preceded by at least one BSKG query. Binary graph_first_compliant "
        "preserved for enforcement. Graduated score fed to Plan 07 evaluator "
        "as context (P13-ADV-3-02).",
    )
    dimensions: list["DimensionScore"] = Field(
        default_factory=list,
        description="Per-dimension breakdown including applicable=False for "
        "unimplemented dimensions (DEFAULT-30 fix)",
    )


# ---------------------------------------------------------------------------
# EvaluationPlugin Protocol (DC-3)
# ---------------------------------------------------------------------------


@runtime_checkable
class EvaluationPlugin(Protocol):
    """Protocol for pluggable evaluation dimensions.

    Any class implementing ``name``, ``score()``, and ``explain()``
    can be registered as a scoring plugin.  This enables future
    projects to add custom dimensions without modifying core code.

    DC-3 fix: ``score()`` accepts an optional ``context`` kwarg to
    pass evaluation metadata (e.g., contract info, run parameters).
    """

    @property
    def name(self) -> str: ...

    def score(
        self,
        collected_output: Any,
        context: dict[str, Any] | None = None,
    ) -> PluginScore:
        """Score a collected output.

        Args:
            collected_output: A CollectedOutput instance (typed as Any
                to avoid importing from tests/).
            context: Optional evaluation context metadata. Plugins that
                need contract info, run mode, etc. receive it here.

        Returns:
            PluginScore with the plugin's assessment.
        """
        ...

    def explain(self, plugin_score: PluginScore) -> str:
        """Produce a human-readable explanation of a score.

        Args:
            plugin_score: The score to explain.

        Returns:
            Explanation string.
        """
        ...


# ---------------------------------------------------------------------------
# Dimension & ScoreCard
# ---------------------------------------------------------------------------


class DimensionScore(BaseModel):
    """Per-dimension score with evidence and explanation.

    A ScoreCard contains multiple DimensionScores, one per evaluated
    aspect (e.g., "graph_utilization", "evidence_quality", "reasoning_depth").

    The ``scoring_method`` field tags how this score was produced:
    - ``"heuristic"``: keyword/activity-based scoring — STRUCTURAL_PROXY role only
      (anti-fabrication, zero-query detection). MUST NOT contribute to evaluation
      scores per P17-IMP-01 heuristic scoring demotion.
    - ``"llm"``: LLM-as-judge via ``claude -p --json-schema`` (reliable)

    Heuristic-scored dimensions on Core workflows MUST NOT be used for
    regression baselines — they invert quality signal (P3-IMP-12, P3-IMP-17).
    """

    dimension: str = Field(description="Dimension name")
    score: int = Field(ge=0, le=100, description="Score for this dimension")
    weight: float = Field(
        default=1.0, ge=0.0, description="Weight in overall aggregation"
    )
    scoring_method: Literal["heuristic", "llm"] = Field(
        default="heuristic",
        description="How this score was produced. Heuristic scores are quarantined for Core tier baselines.",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence items supporting this score",
    )
    explanation: str = Field(default="", description="Why this score was given")
    applicable: bool = Field(
        default=True,
        description="Whether this dimension applies to this workflow. "
        "Non-applicable dimensions are excluded from effective_score().",
    )
    # Track B: [pending-real-transcript-validation]
    # behavioral_signature is PROVISIONAL — requires real transcript data
    behavioral_signature: str = Field(
        default="",
        description="Behavioral signature for construct disambiguation. "
        "PROVISIONAL: [pending-real-transcript-validation]",
    )

    @classmethod
    def disambiguation_check(
        cls,
        registry: list[DimensionScore],
        overlap_threshold: float = 0.5,
    ) -> None:
        """Check that no two dimensions in the registry have overlapping signatures.

        Raises ``ConstructAmbiguityError`` if any pair of dimensions has
        behavioral_signature overlap exceeding the threshold. Plan 06 Task 1
        must call this on each registered dimension before finalizing.

        Args:
            registry: All registered dimension instances.
            overlap_threshold: Maximum allowed signature similarity (0.0-1.0).

        Raises:
            ConstructAmbiguityError: If overlapping signatures found.
        """
        signatures = [
            (d.dimension, set(d.behavioral_signature.lower().split()))
            for d in registry
            if d.behavioral_signature
        ]
        for i, (name_a, sig_a) in enumerate(signatures):
            for name_b, sig_b in signatures[i + 1 :]:
                if not sig_a or not sig_b:
                    continue
                overlap = len(sig_a & sig_b) / min(len(sig_a), len(sig_b))
                if overlap > overlap_threshold:
                    raise ConstructAmbiguityError(
                        f"Dimensions '{name_a}' and '{name_b}' have "
                        f"behavioral_signature overlap {overlap:.2f} "
                        f"exceeding threshold {overlap_threshold:.2f}"
                    )


class ConstructAmbiguityError(ValueError):
    """Raised when two evaluation dimensions have overlapping behavioral signatures.

    Plan 06 Task 1 calls ``DimensionScore.disambiguation_check()`` on all
    registered dimensions. This error blocks registry finalization.
    """


class FailureNarrative(BaseModel):
    """Self-describing failure narrative for metaprompting.

    Every low score produces a paired description enabling targeted
    prompt improvements.
    """

    what_happened: str = Field(
        description="Factual description of what the agent did"
    )
    what_should_have_happened: str = Field(
        description="Expected behavior that would have scored higher"
    )
    root_dimensions: list[str] = Field(
        default_factory=list,
        description="Which dimensions drove this failure",
    )


class ScoreCard(BaseModel):
    """Aggregated evaluation scores with pass/fail determination.

    Produced by the ReasoningEvaluator (3.1c-07) from capability checks,
    plugin scores, and LLM reasoning assessment.
    """

    workflow_id: str = Field(description="Workflow being evaluated")
    dimensions: list[DimensionScore] = Field(
        default_factory=list, description="Per-dimension scores"
    )
    plugin_scores: list[PluginScore] = Field(
        default_factory=list, description="Scores from registered plugins"
    )
    overall_score: int = Field(
        ge=0, le=100, description="Weighted aggregate score"
    )
    passed: bool = Field(description="Whether the workflow passed evaluation")
    pass_threshold: int = Field(
        default=60, ge=0, le=100, description="Score needed to pass"
    )
    failure_narrative: FailureNarrative | None = Field(
        default=None,
        description="Narrative explaining failures (None if passed)",
    )
    capability_gating_failed: bool = Field(
        default=False,
        description="True if a gating capability check failed. "
        "Regression detection skips comparison for these runs.",
    )

    def dimension_by_name(self, name: str) -> DimensionScore | None:
        """Look up a dimension by name."""
        for d in self.dimensions:
            if d.dimension == name:
                return d
        return None

    @property
    def has_heuristic_scores(self) -> bool:
        """Whether any dimension was scored by heuristic (not LLM)."""
        return any(d.scoring_method == "heuristic" for d in self.dimensions)

    def effective_score(self) -> int | None:
        """Weighted average score of applicable dimensions only.

        Returns:
            Weighted score (0-100) or None if no dimensions are applicable.
        """
        applicable = [d for d in self.dimensions if d.applicable]
        if not applicable:
            return None
        total_weight = sum(d.weight for d in applicable)
        if total_weight == 0:
            return None
        weighted_sum = sum(d.score * d.weight for d in applicable)
        return round(weighted_sum / total_weight)


# ---------------------------------------------------------------------------
# Core Assessment Models
# ---------------------------------------------------------------------------


class MoveAssessment(BaseModel):
    """Assessment of a single reasoning move within a transcript.

    Track A: VALIDITY_CLAIM — all fields observed in 3.1e experiments.
    """

    move: ReasoningMove = Field(description="Which reasoning move this assesses")
    score: int = Field(ge=0, le=100, description="Score for this move (0-100)")
    evidence: list[str] = Field(
        default_factory=list,
        description="Transcript excerpts supporting this score",
    )
    explanation: str = Field(default="", description="Evaluator's rationale")
    # Track C: STRUCTURAL_PROXY — heuristic activity indicator
    heuristic_activity_detected: bool = Field(
        default=False,
        description="Whether heuristic detected activity for this move. "
        "STRUCTURAL_PROXY: [structural-proxy] — gate signal only, not quality.",
    )


class ReasoningAssessment(BaseModel):
    """Complete 7-move reasoning decomposition assessment.

    Produced by the dual-Opus evaluator (3.1c-07). Each of the 7 reasoning
    moves is scored independently, enabling targeted improvement via
    metaprompting on the weakest moves.

    Track A: VALIDITY_CLAIM — core assessment structure.
    """

    session_id: str = Field(description="Evaluated session identifier")
    workflow_id: str = Field(description="Workflow that was evaluated")
    evaluator_id: str = Field(
        default="",
        description="Which evaluator instance produced this (A or B for dual-evaluator)",
    )
    moves: list[MoveAssessment] = Field(
        default_factory=list,
        description="Per-move assessments (up to 7)",
    )
    overall_reasoning_score: int = Field(
        ge=0, le=100,
        description="Aggregate reasoning quality score",
    )
    # Track B: [pending-real-transcript-validation]
    transcript_quality: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Quality/completeness of the transcript used. "
        "PROVISIONAL: [pending-real-transcript-validation]",
    )
    assessment_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When this assessment was produced",
    )
    # Track C: STRUCTURAL_PROXY — heuristic reasoning depth
    heuristic_reasoning_depth: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Heuristic-scored reasoning depth. "
        "STRUCTURAL_PROXY: [structural-proxy] — gate signal only, not quality.",
    )
    # Track B: [pending-real-transcript-validation]
    llm_reasoning_depth: int = Field(
        default=0,
        ge=0,
        le=100,
        description="LLM-scored reasoning depth. "
        "PROVISIONAL: [pending-real-transcript-validation]",
    )


class EvaluatorDisagreement(BaseModel):
    """Records disagreement between dual evaluators (A and B).

    When evaluators disagree by more than 10 points on any dimension,
    a structured debate exchange is triggered. Unresolved disputes use
    the lower score with unreliable=True. 3.1c-07 uses this for the
    blind-then-debate protocol.
    """

    dimension: str = Field(description="Dimension with disagreement")
    a_score: int = Field(ge=0, le=100, description="Evaluator A's score")
    b_score: int = Field(ge=0, le=100, description="Evaluator B's score")
    b_score_pre_exposure: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Evaluator B's score before seeing A's reasoning (for anchoring detection). "
        "None if debate not conducted.",
    )
    b_justification: str = Field(
        default="",
        description="Evaluator B's rebuttal/justification after seeing A's explanation",
    )
    resolved_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Final resolved score after debate. None if unresolved.",
    )
    debate_completed: bool = Field(
        default=False,
        description="Whether the evaluators conducted a reconciliation debate",
    )
    resolved_by: Literal["consensus", "a_wins", "b_wins", "escalated", "unresolved"] = Field(
        default="unresolved",
        description="How the disagreement was resolved. "
        "'escalated' uses lower score with unreliable=True.",
    )
    unreliable: bool = Field(
        default=False,
        description="True when dispute was escalated (unresolved) — lower score used",
    )
    delta: int = Field(
        default=0,
        ge=0,
        description="Absolute score difference |A - B|",
    )

    @model_validator(mode="after")
    def _compute_delta(self) -> EvaluatorDisagreement:
        self.delta = abs(self.a_score - self.b_score)
        return self


class ImprovementHint(BaseModel):
    """Actionable hint for improving a specific evaluation dimension.

    Produced by the evaluator when a dimension scores below threshold.
    Feeds into the metaprompting improvement loop (Plan 12).
    """

    dimension: str = Field(description="Dimension this hint targets")
    calibration_status: Literal["calibrated", "uncalibrated", "provisional"] = Field(
        default="uncalibrated",
        description="Whether this hint's basis has been calibrated",
    )
    hypothesis: str = Field(
        default="",
        description="What the evaluator thinks would improve the score",
    )
    kill_criterion: str = Field(
        default="",
        description="Condition under which this hint should be abandoned. "
        "Used by ExperimentLedgerEntry to decide when to stop iterating.",
    )
    priority: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Priority ranking (0=lowest, 10=highest)",
    )


class MetaEvaluationResult(BaseModel):
    """Result of the dual-evaluator meta-evaluation protocol.

    Wraps the two independent assessments plus disagreement analysis.
    """

    evaluator_a: ReasoningAssessment = Field(
        description="First evaluator's assessment"
    )
    evaluator_b: ReasoningAssessment = Field(
        description="Second evaluator's assessment"
    )
    disagreements: list[EvaluatorDisagreement] = Field(
        default_factory=list,
        description="Dimensions where evaluators disagreed significantly",
    )
    is_reliable: bool = Field(
        default=True,
        description="False if any disagreement exceeds 15 points and remains unresolved",
    )
    merged_score: int = Field(
        ge=0, le=100,
        description="Final merged reasoning score after disagreement resolution",
    )


# ---------------------------------------------------------------------------
# Calibration (split: inputs vs outputs, P12 requirement)
# ---------------------------------------------------------------------------


class CalibrationConfig(BaseModel):
    """Calibration inputs — what parameters were used for this calibration run.

    Split from CalibrationResult (outputs) so Plan 12 can verify evaluator
    constants match across calibration runs.
    """

    evaluator_model: str = Field(description="Model used for evaluation (e.g., 'opus')")
    effort_level: Literal["minimal", "standard", "thorough"] = Field(
        default="standard",
        description="How much evaluation effort was applied",
    )
    debate_enabled: bool = Field(
        default=False,
        description="Whether dual-evaluator debate was active",
    )
    evaluator_prompt_hash: str = Field(
        default="",
        description="SHA256 of the evaluator prompt template. "
        "Caller computes externally and passes in.",
    )
    status: Literal["pending", "running", "completed", "failed"] = Field(
        default="pending",
        description="Current calibration status",
    )
    temperature_controllable: bool = Field(
        default=False,
        description="Whether the evaluator model supports temperature control",
    )


class CalibrationResult(BaseModel):
    """Calibration outputs — what was measured.

    Track A: VALIDITY_CLAIM — spearman_rho is from observed data.
    """

    spearman_rho: float = Field(
        ge=-1.0, le=1.0,
        description="Spearman rank correlation between evaluator scores and ground truth",
    )
    spearman_rho_ci: tuple[float, float] = Field(
        default=(-1.0, 1.0),
        description="95% confidence interval for spearman_rho (low, high)",
    )
    # Track B: [pending-real-transcript-validation]
    partial_rho_tp_only: float | None = Field(
        default=None,
        description="Spearman rho computed on true-positive subset only. "
        "PROVISIONAL: [pending-real-transcript-validation]",
    )
    anchor_diagnosis: str = Field(
        default="",
        description="Diagnosis of evaluator anchoring behavior",
    )
    consistency_class: Literal["stable", "recommended", "unstable"] = Field(
        default="stable",
        description="Classification of evaluator consistency across runs",
    )
    anchor_phase: Literal["none", "early", "late", "persistent"] = Field(
        default="none",
        description="Where in evaluation the anchoring effect occurs",
    )


# ---------------------------------------------------------------------------
# Per-workflow reasoning weight profiles (R9 — simplified)
# ---------------------------------------------------------------------------

# Default weight multipliers for reasoning move types.
# Each key maps a move type to a multiplier applied during overall score
# aggregation. Default 1.0 preserves current behavior. Contracts can
# override via an optional `reasoning_weights` YAML field.
DEFAULT_REASONING_WEIGHTS: dict[str, float] = {
    "HYPOTHESIS_FORMATION": 1.0,
    "QUERY_FORMULATION": 1.0,
    "RESULT_INTERPRETATION": 1.0,
    "EVIDENCE_INTEGRATION": 1.0,
    "CONTRADICTION_HANDLING": 1.0,
    "CONCLUSION_SYNTHESIS": 1.0,
    "SELF_CRITIQUE": 1.0,
}


# ---------------------------------------------------------------------------
# EvaluatorConstants (P11-SYN-02, P14-IMP-06)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class EvaluatorConstants:
    """Frozen configuration constants for the reasoning evaluator.

    Single source of truth for evaluator config. The caller computes
    ``prompt_template_hash`` externally (SHA256 of the prompt template text)
    and passes it in via ``current()``. This class MUST NOT import from
    the evaluator module (P14-IMP-06 / DC-2 enforcement).
    """

    prompt_template_hash: str
    scoring_scale_min: int = 0
    scoring_scale_max: int = 100
    disagreement_threshold: int = 15
    min_moves_for_assessment: int = 3
    max_token_budget: int = 6000
    evaluator_model: str = "opus"

    @classmethod
    def current(cls, prompt_template_hash: str) -> EvaluatorConstants:
        """Factory returning current evaluator constants.

        Args:
            prompt_template_hash: SHA256 hex digest of the evaluator prompt
                template. Caller is responsible for computing this externally.

        Returns:
            Frozen EvaluatorConstants instance.
        """
        return cls(prompt_template_hash=prompt_template_hash)


# ---------------------------------------------------------------------------
# Infrastructure Failure Types
# ---------------------------------------------------------------------------

# Using Literal instead of Enum for Pydantic serialization compatibility
InfrastructureFailureType = Literal[
    "hook_timeout",
    "hook_crash",
    "parser_error",
    "store_write_failure",
    "store_read_failure",
    "evaluator_timeout",
    "evaluator_crash",
    "plugin_crash",
    "session_invalid",
    "transcript_missing",
    "transcript_truncated",
    "sandbox_failure",
]


class FailureSignal(BaseModel):
    """A failure signal observed during pipeline execution.

    Track A: VALIDITY_CLAIM — failure types observed in 3.1e experiments.
    """

    signal_type: InfrastructureFailureType = Field(  # type: ignore[valid-type]
        description="Category of infrastructure failure"
    )
    detail: str = Field(
        default="",
        description="Human-readable detail about the failure",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When the failure was observed",
    )
    recoverable: bool = Field(
        default=True,
        description="Whether the pipeline can continue after this failure",
    )


# ---------------------------------------------------------------------------
# Agent Failure Modes (R5 — failure routing)
# ---------------------------------------------------------------------------


class FailureMode(str, Enum):
    """Classification of agent evaluation failures.

    Routes failures to the right remediation path. Infrastructure failures
    (FailureSignal) are pipeline-level; FailureMode classifies agent-level
    behavioral failures observed during evaluation.

    Post-batch only: populated after evaluation data exists.
    """

    POLICY_REFUSAL = "policy_refusal"
    """Agent refused the task due to safety/policy concerns."""

    TASK_RESIGNATION = "task_resignation"
    """Agent gave up or declared it could not complete the task."""

    SCAFFOLD_NONCOMPLIANCE = "scaffold_noncompliance"
    """Agent ignored tool restrictions or imported forbidden modules."""

    FABRICATION = "fabrication"
    """Agent fabricated results without using required tools."""

    FALSE_COMPLETION = "false_completion"
    """Agent claimed completion but did not achieve the objective."""


def classify_failure(
    violations: list[dict[str, Any]],
    transcript_text: str = "",
) -> FailureMode | None:
    """Classify an agent evaluation failure into a FailureMode.

    Uses signals from agent_execution_validator.py checks and
    transcript text patterns. Returns None if no failure detected.

    Args:
        violations: List of violation dicts from agent_execution_validator,
            each with at least 'check_id' and 'severity' keys.
        transcript_text: Raw transcript text for pattern matching.

    Returns:
        The most likely FailureMode, or None if no failure pattern matched.
    """
    if not violations and not transcript_text:
        return None

    violation_ids = {v.get("check_id", "") for v in violations}

    # Priority-ordered classification (most specific first)

    # 1. Policy refusal — agent refused the task
    refusal_patterns = ["cannot assist", "i'm unable to", "policy", "i cannot help"]
    if any(p in transcript_text.lower() for p in refusal_patterns):
        return FailureMode.POLICY_REFUSAL

    # 2. Scaffold noncompliance — used forbidden tools/imports
    scaffold_checks = {"python_import_bypass", "blocked_tool_usage", "raw_python_execution"}
    if violation_ids & scaffold_checks:
        return FailureMode.SCAFFOLD_NONCOMPLIANCE

    # 3. Fabrication — produced results without tool usage
    fabrication_checks = {"no_cli_tool_calls", "zero_graph_queries"}
    if violation_ids & fabrication_checks:
        return FailureMode.FABRICATION

    # 4. Task resignation — agent gave up
    resignation_patterns = ["i cannot complete", "unable to finish", "giving up", "cannot proceed"]
    if any(p in transcript_text.lower() for p in resignation_patterns):
        return FailureMode.TASK_RESIGNATION

    # 5. False completion — claimed done but violations present
    if violations:
        return FailureMode.FALSE_COMPLETION

    return None


class SessionValidityManifest(BaseModel):
    """Validity assessment for a single evaluation session.

    Track A: VALIDITY_CLAIM — session validity checks are deterministic.
    """

    session_id: str = Field(description="Claude Code session identifier")
    valid: bool = Field(description="Whether the session data is usable")
    reasons: list[str] = Field(
        default_factory=list,
        description="Reasons for validity/invalidity",
    )
    checked_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When validity was assessed",
    )


class ObservationDataQuality(BaseModel):
    """Quality assessment of observation data from hooks.

    Track A: VALIDITY_CLAIM — data quality metrics are deterministic.
    """

    serialize_errors: int = Field(
        default=0,
        ge=0,
        description="Number of records that failed serialization",
    )
    cross_session_records_dropped: int = Field(
        default=0,
        ge=0,
        description="Records dropped because session_id mismatched",
    )
    stale_files_excluded: int = Field(
        default=0,
        ge=0,
        description="Observation files excluded due to staleness",
    )
    degraded: bool = Field(
        default=False,
        description="Whether data quality is degraded enough to affect reliability",
    )


# Infrastructure failure type to signal mapping
INFRA_TO_SIGNAL: dict[str, str] = {
    "hook_timeout": "observation_gap",
    "hook_crash": "observation_gap",
    "parser_error": "data_quality_degraded",
    "store_write_failure": "persistence_failure",
    "store_read_failure": "persistence_failure",
    "evaluator_timeout": "evaluation_incomplete",
    "evaluator_crash": "evaluation_incomplete",
    "plugin_crash": "scoring_incomplete",
    "session_invalid": "session_rejected",
    "transcript_missing": "observation_gap",
    "transcript_truncated": "data_quality_degraded",
    "sandbox_failure": "environment_failure",
}


# ---------------------------------------------------------------------------
# Detection + Ground Truth
# ---------------------------------------------------------------------------


class DetectionSummary(BaseModel):
    """Summary of detection results for corpus evaluation runs.

    Track A: VALIDITY_CLAIM — tp/fp/fn counts from 3.1e Plan 01 baseline.
    This is an OUTCOME metric (P14-SYN-01) — used for corpus runs only,
    never as a process-evaluation input for reasoning dimensions.
    """

    tp: int = Field(default=0, ge=0, description="True positives")
    fp: int = Field(default=0, ge=0, description="False positives")
    fn: int = Field(default=0, ge=0, description="False negatives")

    @property
    def precision(self) -> float:
        """Precision = TP / (TP + FP). Returns 1.0 if no predictions."""
        total = self.tp + self.fp
        return self.tp / total if total > 0 else 1.0

    @property
    def recall(self) -> float:
        """Recall = TP / (TP + FN). Returns 1.0 if no ground truth."""
        total = self.tp + self.fn
        return self.tp / total if total > 0 else 1.0

    @property
    def f1(self) -> float:
        """F1 = 2 * precision * recall / (precision + recall)."""
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


class NormalizedFinding(BaseModel):
    """A normalized vulnerability finding for ground truth comparison.

    Tier classification follows VulnDocs pattern tiers.
    """

    finding_id: str = Field(description="Unique finding identifier")
    tier: Literal["A", "B", "C", "uncatalogued"] = Field(
        description="VulnDocs pattern tier"
    )
    category: str = Field(default="", description="Vulnerability category")
    function_name: str = Field(default="", description="Affected function")
    description: str = Field(default="", description="Finding description")
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Finding confidence"
    )


class GroundTruthEntry(BaseModel):
    """A single ground truth vulnerability entry.

    Track A: VALIDITY_CLAIM — ground truth is human-authored.
    """

    entry_id: str = Field(description="Unique ground truth identifier")
    contract_name: str = Field(description="Contract this applies to")
    vulnerability_type: str = Field(description="Type of vulnerability")
    function_name: str = Field(default="", description="Affected function")
    severity: Literal["critical", "high", "medium", "low", "informational"] = Field(
        default="medium",
        description="Severity classification (plain string, not vulndocs type — DC-2)",
    )
    description: str = Field(default="", description="Description of the vulnerability")


class GroundTruthComparison(BaseModel):
    """Result of comparing agent findings against ground truth."""

    ground_truths: list[GroundTruthEntry] = Field(
        default_factory=list,
        description="Expected vulnerabilities",
    )
    findings: list[NormalizedFinding] = Field(
        default_factory=list,
        description="Agent's normalized findings",
    )
    matched: list[tuple[str, str]] = Field(
        default_factory=list,
        description="Pairs of (ground_truth_id, finding_id) that matched",
    )
    detection_summary: DetectionSummary = Field(
        default_factory=DetectionSummary,
        description="TP/FP/FN summary from the comparison",
    )


# ---------------------------------------------------------------------------
# Progress + Reporting
# ---------------------------------------------------------------------------


class WorkflowStatus(BaseModel):
    """Status of a single workflow within an evaluation run."""

    workflow_id: str = Field(description="Workflow identifier")
    status: Literal["pending", "running", "completed", "failed", "skipped"] = Field(
        default="pending",
        description="Current status",
    )
    started_at: str | None = Field(default=None, description="Start timestamp")
    completed_at: str | None = Field(default=None, description="Completion timestamp")
    error: str | None = Field(default=None, description="Error message if failed")


class EvaluationProgress(BaseModel):
    """Progress tracking for a suite evaluation run.

    Track A: VALIDITY_CLAIM — deterministic pipeline state.
    """

    total_workflows: int = Field(default=0, ge=0, description="Total workflows to evaluate")
    completed: int = Field(default=0, ge=0, description="Workflows completed")
    failed: int = Field(default=0, ge=0, description="Workflows that failed")
    skipped: int = Field(default=0, ge=0, description="Workflows skipped")
    per_workflow_status: list[WorkflowStatus] = Field(
        default_factory=list,
        description="Status for each workflow",
    )
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When the evaluation suite started",
    )

    @property
    def remaining(self) -> int:
        """Workflows not yet completed, failed, or skipped."""
        return max(0, self.total_workflows - self.completed - self.failed - self.skipped)

    @property
    def is_complete(self) -> bool:
        """Whether all workflows have been processed."""
        return self.remaining == 0 and self.total_workflows > 0


class FailureRecommendation(str, Enum):
    """Recommended action after a failure."""

    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"
    INVESTIGATE = "investigate"
    ESCALATE = "escalate"


class FailureReport(BaseModel):
    """Structured report of a failure during evaluation."""

    failure_type: str = Field(description="Category of failure")
    detail: str = Field(default="", description="Detailed failure description")
    workflow_id: str = Field(default="", description="Which workflow failed")
    recommendation: FailureRecommendation = Field(
        default=FailureRecommendation.INVESTIGATE,
        description="Recommended action",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When the failure occurred",
    )


class SuiteExitReport(BaseModel):
    """Final report from a complete evaluation suite run.

    Consumed by the /vrs-test-suite skill (3.1c-09) and persisted
    to .vrs/evaluations/.
    """

    suite_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique suite run identifier",
    )
    progress: EvaluationProgress = Field(
        description="Final progress state"
    )
    results: list[EvaluationResult] = Field(
        default_factory=list,
        description="Per-workflow evaluation results",
    )
    failures: list[FailureReport] = Field(
        default_factory=list,
        description="Failures encountered during the run",
    )
    overall_passed: bool = Field(
        default=False,
        description="Whether the suite as a whole passed",
    )
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Suite start timestamp",
    )
    completed_at: str = Field(
        default="",
        description="Suite completion timestamp",
    )
    run_mode: RunMode = Field(
        default=RunMode.SIMULATED,
        description="Execution mode for this suite run",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Suite-level metadata",
    )


class ExperimentLedgerEntry(BaseModel):
    """Entry in the experiment ledger for tracking improvement iterations.

    Round-trip serializable via model_dump_json() / model_validate_json().
    """

    entry_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique ledger entry identifier",
    )
    dimension: str = Field(description="Dimension being improved")
    hypothesis: str = Field(description="What improvement was attempted")
    decision: Literal["continue", "abandon", "promote", "demote"] = Field(
        description="Decision after this iteration"
    )
    abandon_reason: str = Field(
        default="",
        description="Why the experiment was abandoned (empty if not abandoned)",
    )
    kill_criterion: str = Field(
        default="",
        description="Condition that triggered abandonment",
    )
    iteration: int = Field(default=1, ge=1, description="Iteration number")
    score_before: int = Field(
        default=0, ge=0, le=100, description="Score before this iteration"
    )
    score_after: int = Field(
        default=0, ge=0, le=100, description="Score after this iteration"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When this entry was created",
    )


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------


class BaselineKey(BaseModel):
    """Composite key for baseline lookup.

    Uniquely identifies a baseline configuration for regression comparison.
    """

    workflow_id: str = Field(description="Workflow this baseline applies to")
    run_mode: RunMode = Field(description="Execution mode")
    debate_enabled: bool = Field(default=False, description="Whether debate was active")
    effort_level: Literal["minimal", "standard", "thorough"] = Field(
        default="standard",
        description="Evaluation effort level",
    )
    scoring_denominator_version: str = Field(
        default="v1",
        description="Version of the scoring denominator formula. "
        "Changes when dimensions are added/removed.",
    )


# ---------------------------------------------------------------------------
# EvaluationConfig (self-evaluation guard, 3.1e deferred Item 4)
# ---------------------------------------------------------------------------


class EvaluationConfig(BaseModel):
    """Configuration for an evaluation run.

    Contains the self-evaluation guard (3.1e deferred Item 4): prevents
    the evaluator from scoring its own session.
    """

    evaluator_session_id: str = Field(
        default="",
        description="Session ID of the evaluator (the agent doing the scoring)",
    )
    evaluated_session_id: str = Field(
        default="",
        description="Session ID of the agent being evaluated",
    )
    self_evaluation_guard: bool = Field(
        default=True,
        description="When True, reject evaluation where evaluator_session_id == evaluated_session_id",
    )
    run_mode: RunMode = Field(default=RunMode.SIMULATED, description="Execution mode")
    debate_enabled: bool = Field(default=False, description="Enable dual-evaluator debate")
    effort_level: Literal["minimal", "standard", "thorough"] = Field(
        default="standard",
        description="How much evaluation effort to apply",
    )

    @model_validator(mode="after")
    def _check_self_evaluation(self) -> EvaluationConfig:
        if (
            self.self_evaluation_guard
            and self.evaluator_session_id
            and self.evaluated_session_id
            and self.evaluator_session_id == self.evaluated_session_id
        ):
            raise ValueError(
                f"Self-evaluation rejected: evaluator_session_id "
                f"({self.evaluator_session_id}) matches evaluated_session_id. "
                f"Set self_evaluation_guard=False to override."
            )
        return self


# ---------------------------------------------------------------------------
# Pipeline Health
# ---------------------------------------------------------------------------


class PipelineHealth(BaseModel):
    """Health metrics for a single evaluation pipeline run.

    Runs with health < 60% are flagged as unreliable and excluded
    from baseline calculations.
    """

    parsed_records: int = Field(default=0, description="Records successfully parsed")
    expected_records: int = Field(default=0, description="Records expected")
    errors: int = Field(default=0, description="Parse/processing errors")
    stages_completed: list[str] = Field(
        default_factory=list, description="Pipeline stages that completed"
    )
    stage_durations: dict[str, float] = Field(
        default_factory=dict,
        description="Wall-clock duration in seconds for each pipeline stage",
    )

    @property
    def health_pct(self) -> float:
        """Health percentage (0.0-1.0)."""
        if self.expected_records == 0:
            return 1.0 if self.errors == 0 else 0.0
        return max(0.0, (self.parsed_records - self.errors) / self.expected_records)

    @property
    def is_reliable(self) -> bool:
        """Whether this run's data is reliable enough for baseline."""
        return self.health_pct >= 0.6


# ---------------------------------------------------------------------------
# EvaluationResult (updated with new fields)
# ---------------------------------------------------------------------------


class EvaluationResult(BaseModel):
    """Complete result of evaluating one scenario run.

    Wraps a ScoreCard with execution metadata, timestamps, and
    pipeline health.  Persisted to .vrs/evaluation/results/.
    """

    result_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique result identifier",
    )
    scenario_name: str = Field(description="Scenario that was executed")
    workflow_id: str = Field(description="Workflow that was evaluated")
    run_mode: RunMode = Field(description="Execution mode used")
    score_card: ScoreCard = Field(description="Evaluation scores")
    pipeline_health: PipelineHealth = Field(
        default_factory=PipelineHealth,
        description="Pipeline health metrics",
    )
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 start timestamp",
    )
    completed_at: str = Field(
        default="",
        description="ISO 8601 completion timestamp (empty if not completed)",
    )
    run_duration_ms: float = Field(
        default=0.0, description="Total evaluation duration in milliseconds"
    )
    trial_number: int = Field(
        default=1, ge=1, description="Which trial this is (for multi-trial runs)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata (model, version, etc.)",
    )
    plugins_executed: list[str] = Field(
        default_factory=list,
        description="Names of evaluation plugins that were executed",
    )

    # --- New fields (3.1c-01) ---
    improvement_hints: list[ImprovementHint] = Field(
        default_factory=list,
        description="Actionable hints for improving weak dimensions",
    )
    evaluator_disagreements: list[EvaluatorDisagreement] = Field(
        default_factory=list,
        description="Disagreements between dual evaluators (if debate was active)",
    )
    detection_summary: DetectionSummary | None = Field(
        default=None,
        description="Detection TP/FP/FN summary (corpus runs only — outcome metric)",
    )
    failure_signals: list[FailureSignal] = Field(
        default_factory=list,
        description="Infrastructure failure signals observed during this run",
    )
    infrastructure_failure_type: InfrastructureFailureType | None = Field(  # type: ignore[valid-type]
        default=None,
        description="Primary infrastructure failure type, if any",
    )
    scoring_cost_usd: float = Field(
        default=0.0,
        ge=0.0,
        description="Cost of LLM scoring calls in USD",
    )
    baseline_update_status: Literal["none", "pending", "updated", "rejected"] = Field(
        default="none",
        description="Whether this result triggered a baseline update",
    )
    data_quality_warning: str = Field(
        default="",
        description="Warning about observation data quality issues",
    )

    # --- Cross-Plan Dependency fields (3.1c-08 -> 3.1c-09/10/11/12) ---
    status: str = Field(
        default="completed",
        description="Pipeline outcome status: 'completed', 'invalid_session', 'failed'",
    )
    graph_value_score: float | None = Field(
        default=None,
        description="Top-level GVS score from GraphValueScorer (None if GVS not run)",
    )
    reasoning_assessment: Any | None = Field(
        default=None,
        description="Top-level reasoning assessment from ReasoningEvaluator (None if not run)",
    )
    evaluation_complete: bool = Field(
        default=False,
        description="Whether all pipeline stages completed successfully",
    )

    @property
    def is_reliable(self) -> bool:
        """Whether this result is reliable enough for baseline comparison."""
        return self.pipeline_health.is_reliable


# ---------------------------------------------------------------------------
# EvaluationStoreProtocol (Issue #1 -- abstract persistence)
# ---------------------------------------------------------------------------


@runtime_checkable
class EvaluationStoreProtocol(Protocol):
    """Abstract persistence interface for evaluation results.

    Implementations may use JSON files (v1), SQLite, or any other backend.
    The runner (3.1c-08) depends only on this protocol.
    """

    def store_result(self, result: EvaluationResult) -> None:
        """Persist an evaluation result."""
        ...

    def get_result(self, result_id: str) -> EvaluationResult | None:
        """Retrieve a result by ID."""
        ...

    def list_results(
        self, workflow_id: str | None = None, limit: int = 100
    ) -> list[EvaluationResult]:
        """List results, optionally filtered by workflow."""
        ...

    def get_latest(self, workflow_id: str) -> EvaluationResult | None:
        """Get the most recent result for a workflow."""
        ...

    def append_history(self, workflow_id: str, result: EvaluationResult) -> None:
        """Append to per-workflow history (append-only JSONL)."""
        ...


# ---------------------------------------------------------------------------
# Debrief Response (updated with compacted + delivery_status)
# ---------------------------------------------------------------------------


class DebriefResponse(BaseModel):
    """Structured self-assessment from an agent debrief.

    Produced by the DebriefProtocol (3.1c-05) when an agent answers
    debrief questions after completing a task.
    """

    agent_name: str = Field(description="Agent that was debriefed")
    agent_type: str = Field(description="Agent role (attacker, defender, etc.)")
    layer_used: str = Field(
        description="Which debrief layer succeeded "
        "(send_message, hook_gate, transcript_analysis)"
    )
    questions: list[str] = Field(description="Questions that were asked")
    answers: list[str] = Field(description="Agent's answers (parallel to questions)")
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How confident the debrief data is (0=fallback, 1=direct)",
    )
    raw_response: str = Field(
        default="", description="Raw text response before parsing"
    )
    duration_ms: float = Field(
        default=0.0, description="Time taken for debrief in milliseconds"
    )
    # P11-IMP-04: compacted flag
    compacted: bool = Field(
        default=False,
        description="Whether this debrief response was compacted to save tokens",
    )
    # P15-IMP-21: delivery status
    delivery_status: Literal["delivered", "phantom", "not_attempted"] = Field(
        default="not_attempted",
        description="Whether the debrief was actually delivered to the agent",
    )


# ---------------------------------------------------------------------------
# EvaluationInput -- Bridge from 3.1b dataclasses (Issue #3)
# ---------------------------------------------------------------------------


class EvaluationInput(BaseModel):
    """Bridge between 3.1b's CollectedOutput (dataclass) and 3.1c's Pydantic pipeline.

    Use ``from_collected_output()`` to convert. Extracts serializable data
    and drops non-serializable fields (TranscriptParser, EventStream).
    """

    scenario_name: str
    run_id: str
    tool_sequence: list[str] = Field(default_factory=list)
    bskg_queries: list[dict[str, Any]] = Field(default_factory=list)
    duration_ms: float = 0.0
    cost_usd: float = 0.0
    failure_notes: str = ""
    response_text: str = ""
    structured_output: dict[str, Any] | None = None
    agent_count: int = Field(
        default=0, description="Number of agents in team (0 = single-agent run)"
    )
    run_mode: RunMode = Field(default=RunMode.SIMULATED)

    @classmethod
    def from_collected_output(
        cls,
        co: Any,
        run_mode: RunMode = RunMode.SIMULATED,
    ) -> EvaluationInput:
        """Bridge a 3.1b CollectedOutput into a Pydantic EvaluationInput.

        Args:
            co: A CollectedOutput instance (from output_collector.py).
                Typed as Any to avoid importing from tests/.
            run_mode: The execution mode for this run.

        Returns:
            EvaluationInput with serializable data extracted.
        """
        # Extract BSKG queries as dicts for serialization
        bskg_dicts = []
        for q in getattr(co, "bskg_queries", []):
            if hasattr(q, "__dict__"):
                bskg_dicts.append(
                    {
                        k: v
                        for k, v in q.__dict__.items()
                        if not k.startswith("_")
                    }
                )
            elif isinstance(q, dict):
                bskg_dicts.append(q)

        agent_count = 0
        team_obs = getattr(co, "team_observation", None)
        if team_obs is not None:
            agent_count = len(getattr(team_obs, "agents", {}))

        return cls(
            scenario_name=getattr(co, "scenario_name", ""),
            run_id=getattr(co, "run_id", ""),
            tool_sequence=list(getattr(co, "tool_sequence", [])),
            bskg_queries=bskg_dicts,
            duration_ms=getattr(co, "duration_ms", 0.0),
            cost_usd=getattr(co, "cost_usd", 0.0),
            failure_notes=getattr(co, "failure_notes", ""),
            response_text=getattr(co, "response_text", ""),
            structured_output=getattr(co, "structured_output", None),
            agent_count=agent_count,
            run_mode=run_mode,
        )


# ---------------------------------------------------------------------------
# Forward reference resolution
# ---------------------------------------------------------------------------

# GraphValueScore references DimensionScore which is defined after it.
# With `from __future__ import annotations`, Pydantic v2 needs model_rebuild().
GraphValueScore.model_rebuild()
