"""Evaluation Runner — orchestrates the full evaluation pipeline.

Pipeline: contract -> session validity -> observations -> GVS -> reasoning -> result -> persist.

Ties together:
- Session validity checks (SYN-02)
- Observation parsing (3.1c-03)
- Graph Value Scoring (3.1c-04)
- Reasoning evaluation (3.1c-07)
- Baseline management with three-condition AND gate (P15-IMP-38)
- Mode-aware dimension filtering (IMP-25)
- Result persistence (EvaluationStoreProtocol)
- Post-run anomaly detection (IMP-26)
- Improvement queue threshold (IMP-01)

Zero imports from alphaswarm_sol.shipping — standalone on fixtures.

CONTRACT_VERSION: 08.2
CONSUMERS: [3.1c-09, 3.1c-10, 3.1c-11, 3.1c-12]
"""

from __future__ import annotations

import fcntl
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alphaswarm_sol.testing.evaluation.models import (
    EvaluationInput,
    EvaluationResult,
    PipelineHealth,
    RunMode,
    ScoreCard,
    SessionValidityManifest,
)
from tests.workflow_harness.graders.graph_value_scorer import GraphValueScorer
from tests.workflow_harness.graders.reasoning_evaluator import ReasoningEvaluator
from tests.workflow_harness.lib.debrief_protocol import run_debrief

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mode Capability Matrix (IMP-06) — dimensions unavailable per mode
# ---------------------------------------------------------------------------

# Dimensions that are UNAVAILABLE in specific run modes
MODE_UNAVAILABLE_DIMENSIONS: dict[RunMode, set[str]] = {
    RunMode.SIMULATED: {
        "debrief_layer_1",
        "debrief_layer_2",
        "hook_based_gvs",
        "interactive_followup",
        "message_flow_scoring",
        "session_end_hook",
        "precompact_hook",
        "async_hook_completion",
        "delegate_mode_enforcement",
        "parallel_execution",
    },
    RunMode.HEADLESS: {
        "debrief_layer_1",
        "interactive_followup",
        "message_flow_scoring",
    },
    RunMode.INTERACTIVE: {
        "parallel_execution",
    },
}

# Tier-to-mode defaults (IMP-14)
TIER_MODE_DEFAULTS: dict[str, RunMode] = {
    "core": RunMode.INTERACTIVE,
    "important_investigation": RunMode.INTERACTIVE,
    "important_tool": RunMode.HEADLESS,
    "important_support": RunMode.HEADLESS,
    "standard": RunMode.HEADLESS,
}

# Per-scenario timeouts (seconds)
SCENARIO_TIMEOUTS: dict[str, int] = {
    "standard": 300,
    "deep": 600,
    "deep_with_debate": 900,
}

# Execution profiles (P15-IMP-19)
EXECUTION_PROFILES: dict[str, dict[str, Any]] = {
    "interactive_investigation": {
        "run_gvs": True,
        "run_reasoning": True,
        "debrief": True,
        "depth": "deep",
    },
    "headless_tool": {
        "run_gvs": False,
        "run_reasoning": True,
        "debrief": False,
        "depth": "standard",
    },
    "headless_standard": {
        "run_gvs": False,
        "run_reasoning": True,
        "debrief": False,
        "depth": "standard",
    },
}

# Improvement queue constants (IMP-01)
IMPROVEMENT_QUEUE_SCORE_THRESHOLD = 30
IMPROVEMENT_QUEUE_COUNT_THRESHOLD = 3

# Anomaly detection constants (IMP-26)
ANOMALY_DETECTION_MIN_RUNS = 5


# ---------------------------------------------------------------------------
# Contract difficulty sorting (R7 — score-then-sort)
# ---------------------------------------------------------------------------


def sort_contracts_by_difficulty(
    contracts: list[dict[str, Any]],
    history: dict[str, list[float]],
) -> list[dict[str, Any]]:
    """Sort contracts by ascending average score (hardest first).

    Unknown contracts (no history) go first to prioritize exploration.
    Gracefully degrades to no-op when no history exists.

    Args:
        contracts: List of scenario dicts with at least 'workflow_id' key.
        history: Mapping of workflow_id -> list of past overall scores.

    Returns:
        Sorted copy of contracts list (original unchanged).
    """
    def sort_key(contract: dict[str, Any]) -> tuple[int, float]:
        scores = history.get(contract.get("workflow_id", ""), [])
        if not scores:
            return (0, 0.0)  # Unknown = highest priority (explore)
        return (1, sum(scores) / len(scores))

    return sorted(contracts, key=sort_key)


# ---------------------------------------------------------------------------
# JSON File Store (v1 implementation of EvaluationStoreProtocol)
# ---------------------------------------------------------------------------


class JSONFileStore:
    """Simple JSON file-based evaluation result store.

    Implements EvaluationStoreProtocol. Stores results as individual
    JSON files and maintains per-workflow JSONL history.
    """

    def __init__(self, base_dir: Path):
        self._base_dir = base_dir
        self._results_dir = base_dir / "results"
        self._history_dir = base_dir / "history"
        self._results_dir.mkdir(parents=True, exist_ok=True)
        self._history_dir.mkdir(parents=True, exist_ok=True)

    def store_result(self, result: EvaluationResult) -> None:
        """Persist an evaluation result as JSON."""
        path = self._results_dir / f"{result.result_id}.json"
        path.write_text(result.model_dump_json(indent=2))

    def get_result(self, result_id: str) -> EvaluationResult | None:
        """Retrieve a result by ID."""
        path = self._results_dir / f"{result_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return EvaluationResult.model_validate(data)

    def list_results(
        self, workflow_id: str | None = None, limit: int = 100
    ) -> list[EvaluationResult]:
        """List results, optionally filtered by workflow."""
        results = []
        for path in sorted(self._results_dir.glob("*.json"), reverse=True):
            if len(results) >= limit:
                break
            data = json.loads(path.read_text())
            result = EvaluationResult.model_validate(data)
            if workflow_id is None or result.workflow_id == workflow_id:
                results.append(result)
        return results

    def get_latest(self, workflow_id: str) -> EvaluationResult | None:
        """Get the most recent result for a workflow."""
        results = self.list_results(workflow_id=workflow_id, limit=1)
        return results[0] if results else None

    def append_history(self, workflow_id: str, result: EvaluationResult) -> None:
        """Append to per-workflow JSONL history."""
        path = self._history_dir / f"{workflow_id}.jsonl"
        with open(path, "a") as f:
            f.write(result.model_dump_json() + "\n")


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

PIPELINE_STAGES = [
    "check_session_validity",
    "load_scenario",
    "collect_output",
    "parse_observations",
    "run_gvs",
    "run_reasoning_evaluator",
    "apply_mode_filtering",
    "store_result",
    "integrity_check",
    "run_debrief",
]


# ---------------------------------------------------------------------------
# Intelligence signal extraction (3.1c.3 support)
# ---------------------------------------------------------------------------


def _extract_intelligence_signals(debrief: Any) -> dict[str, Any]:
    """Extract intelligence-targeted signals from debrief for 3.1c.3 modules.

    Looks for answers to the 3 intelligence questions:
    1. Most informative graph query
    2. Unhelpful query + what to change
    3. Information needed but unavailable from graph

    These feed coverage_radar and query_coach in 3.1c.3.
    """
    signals: dict[str, Any] = {}
    questions = debrief.questions if hasattr(debrief, "questions") else []
    answers = debrief.answers if hasattr(debrief, "answers") else []

    # Map known intelligence questions to signal keys
    INTELLIGENCE_KEYWORDS = {
        "most informative": "most_informative_query",
        "unhelpful results": "unhelpful_query_feedback",
        "could not get from the graph": "missing_information",
    }

    for i, question in enumerate(questions):
        if i >= len(answers):
            break
        q_lower = question.lower()
        for keyword, signal_key in INTELLIGENCE_KEYWORDS.items():
            if keyword in q_lower:
                signals[signal_key] = answers[i]
                break

    return signals


# ---------------------------------------------------------------------------
# EvaluationRunner
# ---------------------------------------------------------------------------


class EvaluationRunner:
    """Run the full evaluation pipeline for a scenario.

    Pipeline: contract -> session validity -> observations -> GVS ->
    reasoning evaluation -> mode-aware filtering -> result -> persist.

    Usage:
        runner = EvaluationRunner(store=JSONFileStore(base_dir))
        result = runner.run(session_id, contract)

    Configuration:
        max_parallel_headless: Maximum parallel headless sessions (default 1,
            increment to 3 after isolation test passes). P15-IMP-17.
    """

    def __init__(
        self,
        store: Any | None = None,
        contracts_dir: Path | None = None,
        obs_dir: Path | None = None,
        debrief_dir: Path | None = None,
        run_mode: RunMode = RunMode.SIMULATED,
        baseline_manager: Any | None = None,
        max_parallel_headless: int = 1,
        progress_dir: Path | None = None,
        session_recorder: Any | None = None,
        ground_truth_dir: Path | None = None,
    ):
        self._store = store
        self._contracts_dir = contracts_dir
        self._obs_dir = obs_dir
        self._debrief_dir = debrief_dir
        self._run_mode = run_mode
        self._baseline_manager = baseline_manager
        self._max_parallel_headless = max_parallel_headless
        self._progress_dir = progress_dir
        self._session_recorder = session_recorder
        self._ground_truth_dir = ground_truth_dir

    # -----------------------------------------------------------------------
    # Session validity (SYN-02)
    # -----------------------------------------------------------------------

    def _check_session_validity(
        self,
        session_id: str,
        obs_dir: Path | None,
        debrief_dir: Path | None,
    ) -> SessionValidityManifest:
        """Check if a session's data is valid for evaluation.

        Checks:
        1. Observation JSONL exists and is non-empty
        2. Session was not interrupted (has stop event)
        3. Debrief data exists (when debrief_dir provided)
        4. Data is not stale

        Returns:
            SessionValidityManifest with valid=True or valid=False with reasons.
        """
        reasons: list[str] = []

        # Check 1: Observation data exists
        if obs_dir is None or not obs_dir.exists():
            reasons.append("observation_directory_missing")
            return SessionValidityManifest(
                session_id=session_id, valid=False, reasons=reasons
            )

        # Find JSONL files
        jsonl_files = list(obs_dir.glob("*.jsonl"))
        if not jsonl_files:
            reasons.append("no_jsonl_files_found")
            return SessionValidityManifest(
                session_id=session_id, valid=False, reasons=reasons
            )

        # Check 2: Session not interrupted — look for stop event
        has_stop_event = False
        for jf in jsonl_files:
            try:
                content = jf.read_text().strip()
                if not content:
                    continue
                for line in content.split("\n"):
                    try:
                        record = json.loads(line)
                        # Check for agent_stop subtype or stop event
                        if record.get("subtype") == "agent_stop":
                            has_stop_event = True
                            break
                    except json.JSONDecodeError:
                        continue
            except OSError:
                continue
            if has_stop_event:
                break

        # Check for explicit interrupted status
        status_file = obs_dir / "status.json"
        if status_file.exists():
            try:
                status = json.loads(status_file.read_text())
                if status.get("status") == "interrupted":
                    reasons.append("session_interrupted")
                    return SessionValidityManifest(
                        session_id=session_id, valid=False, reasons=reasons
                    )
            except (json.JSONDecodeError, OSError):
                pass

        if not has_stop_event:
            reasons.append("session_interrupted_no_stop_event")
            return SessionValidityManifest(
                session_id=session_id, valid=False, reasons=reasons
            )

        # Check 3: Data staleness — explicit marker or file mtime
        staleness_marker = obs_dir / "staleness_marker.json"
        if staleness_marker.exists():
            try:
                marker = json.loads(staleness_marker.read_text())
                if marker.get("stale", False):
                    reasons.append("session_data_stale")
                    return SessionValidityManifest(
                        session_id=session_id, valid=False, reasons=reasons
                    )
            except (json.JSONDecodeError, OSError):
                pass

        import os

        now = time.time()
        max_staleness = 86400  # 24 hours
        all_stale = True
        for jf in jsonl_files:
            try:
                mtime = os.path.getmtime(jf)
                if (now - mtime) <= max_staleness:
                    all_stale = False
                    break
            except OSError:
                continue

        if all_stale and jsonl_files:
            reasons.append("session_data_stale")
            return SessionValidityManifest(
                session_id=session_id, valid=False, reasons=reasons
            )

        # Check 4: Debrief data exists when dir provided
        if debrief_dir is not None:
            debrief_files = list(debrief_dir.glob("*.json"))
            if not debrief_files:
                reasons.append("debrief_data_missing")
                return SessionValidityManifest(
                    session_id=session_id, valid=False, reasons=reasons
                )

        return SessionValidityManifest(
            session_id=session_id,
            valid=True,
            reasons=["all_checks_passed"],
        )

    # -----------------------------------------------------------------------
    # Mode-aware dimension filtering (IMP-25)
    # -----------------------------------------------------------------------

    def _apply_mode_filtering(
        self, score_card: ScoreCard, run_mode: RunMode
    ) -> ScoreCard:
        """Set applicable=False for dimensions unavailable in this run mode.

        Post-scoring pass: dimensions already scored are marked inapplicable
        if the run mode doesn't support them. effective_score() excludes these.
        """
        unavailable = MODE_UNAVAILABLE_DIMENSIONS.get(run_mode, set())
        if not unavailable:
            return score_card

        for dim in score_card.dimensions:
            if dim.dimension in unavailable:
                dim.applicable = False

        for ps in score_card.plugin_scores:
            if ps.plugin_name in unavailable:
                ps.applicable = False

        return score_card

    # -----------------------------------------------------------------------
    # Post-run anomaly detection (IMP-26)
    # -----------------------------------------------------------------------

    def _detect_anomalies(
        self, result: EvaluationResult, run_count: int
    ) -> list[str]:
        """Detect ceiling/floor/zero-variance anomalies after scoring.

        Only activates after ANOMALY_DETECTION_MIN_RUNS Core-tier runs.
        Full healing stays in Plan 12.
        """
        warnings: list[str] = []
        if run_count < ANOMALY_DETECTION_MIN_RUNS:
            return warnings

        dimensions = result.score_card.dimensions
        applicable = [d for d in dimensions if d.applicable]

        if not applicable:
            return warnings

        scores = [d.score for d in applicable]

        # Ceiling: all scores at 100
        if all(s == 100 for s in scores):
            warnings.append(
                "ANOMALY: ceiling_detected — all applicable dimensions scored 100"
            )

        # Floor: all scores at 0
        if all(s == 0 for s in scores):
            warnings.append(
                "ANOMALY: floor_detected — all applicable dimensions scored 0"
            )

        # Zero variance: all scores identical (but not 0 or 100)
        if len(set(scores)) == 1 and scores[0] not in (0, 100):
            warnings.append(
                f"ANOMALY: zero_variance — all applicable dimensions scored {scores[0]}"
            )

        return warnings

    # -----------------------------------------------------------------------
    # Improvement queue (IMP-01)
    # -----------------------------------------------------------------------

    def _check_improvement_queue(
        self, result: EvaluationResult
    ) -> None:
        """After Core-tier run, flag HIGH_PRIORITY if too many low-score hints."""
        # Count dimensions with score below threshold as proxy for improvement needs
        low_dims = [
            d for d in result.score_card.dimensions
            if d.applicable and d.score < IMPROVEMENT_QUEUE_SCORE_THRESHOLD
        ]

        if len(low_dims) > IMPROVEMENT_QUEUE_COUNT_THRESHOLD:
            if self._progress_dir is not None:
                progress_path = self._progress_dir / "progress.json"
                progress_data: dict[str, Any] = {}
                if progress_path.exists():
                    try:
                        progress_data = json.loads(progress_path.read_text())
                    except (json.JSONDecodeError, OSError):
                        pass
                progress_data["HIGH_PRIORITY"] = True
                progress_data["high_priority_reason"] = (
                    f"{len(low_dims)} dimensions scored below "
                    f"{IMPROVEMENT_QUEUE_SCORE_THRESHOLD}"
                )
                self._progress_dir.mkdir(parents=True, exist_ok=True)
                progress_path.write_text(json.dumps(progress_data, indent=2))

    # -----------------------------------------------------------------------
    # Fail-fast on unconsumed config (DC-4)
    # -----------------------------------------------------------------------

    @staticmethod
    def _check_unconsumed_config(
        contract: dict[str, Any], consumed_keys: set[str]
    ) -> None:
        """Raise if contract has unexpected top-level config fields."""
        known_keys = {
            "workflow_id", "category", "grader_type", "rule_refs",
            "reasoning_dimensions", "capability_checks", "evidence_requirements",
            "metadata", "evaluation_config", "hooks", "status",
            "coverage_axes", "ground_truth_rubric", "active_dimensions",
            "tier", "dimension_registry",
        }
        all_valid = known_keys | consumed_keys
        unexpected = set(contract.keys()) - all_valid
        if unexpected:
            raise ValueError(
                f"Unconsumed config fields in contract: {unexpected}. "
                f"Add to known_keys or consumed_keys if intentional."
            )

    # -----------------------------------------------------------------------
    # Main pipeline
    # -----------------------------------------------------------------------

    def run(
        self,
        scenario_name: str,
        workflow_id: str,
        collected_output: Any,
        debrief_agent_name: str | None = None,
        debrief_agent_type: str | None = None,
        transcript_path: Path | None = None,
        trial_number: int = 1,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
        contract: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """Execute the full evaluation pipeline.

        Args:
            scenario_name: Name of the scenario being evaluated.
            workflow_id: Which workflow/contract to evaluate against.
            collected_output: CollectedOutput or EvaluationInput.
            debrief_agent_name: Agent to debrief (optional).
            debrief_agent_type: Agent's role (optional).
            transcript_path: Path to agent transcript (optional).
            trial_number: Which trial this is.
            metadata: Additional metadata.
            session_id: Session ID for validity checking.
            contract: Evaluation contract dict (optional, loaded from disk if absent).

        Returns:
            EvaluationResult with full pipeline output.
        """
        start_time = time.time()
        started_at = datetime.now(timezone.utc).isoformat()
        health = PipelineHealth(expected_records=len(PIPELINE_STAGES))
        stages_completed: list[str] = []
        stage_durations: dict[str, float] = {}
        obs_summary = None

        # Session correlation ID — enables cross-observation grouping
        correlation_id = str(uuid.uuid4())

        # Resolve effective obs/debrief dirs (session-scoped subdirectories)
        effective_obs_dir = self._obs_dir
        effective_debrief_dir = self._debrief_dir
        if session_id and self._obs_dir:
            session_subdir = self._obs_dir / session_id
            if session_subdir.exists():
                effective_obs_dir = session_subdir

        # Stage 1: Session validity check (SYN-02)
        t0 = time.monotonic()
        manifest = None
        if session_id and effective_obs_dir:
            manifest = self._check_session_validity(
                session_id, effective_obs_dir, effective_debrief_dir
            )
            stages_completed.append("check_session_validity")

            if not manifest.valid:
                # Early return — invalid sessions skip scoring entirely
                stage_durations["check_session_validity"] = time.monotonic() - t0
                elapsed_ms = (time.time() - start_time) * 1000.0
                health.parsed_records = len(stages_completed)
                health.stages_completed = stages_completed
                health.stage_durations = stage_durations
                return EvaluationResult(
                    scenario_name=scenario_name,
                    workflow_id=workflow_id,
                    run_mode=self._run_mode,
                    score_card=ScoreCard(
                        workflow_id=workflow_id,
                        overall_score=0,
                        passed=False,
                        failure_narrative=None,
                    ),
                    pipeline_health=health,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    run_duration_ms=elapsed_ms,
                    trial_number=trial_number,
                    metadata=dict(metadata or {}, **{
                        "validity_reasons": manifest.reasons,
                        "session_correlation_id": correlation_id,
                        "pipeline_timing": stage_durations,
                    }),
                    baseline_update_status="rejected",
                    status="invalid_session",
                    graph_value_score=None,
                    reasoning_assessment=None,
                    evaluation_complete=False,
                )
        else:
            stages_completed.append("check_session_validity")
        stage_durations["check_session_validity"] = time.monotonic() - t0

        # Initialize before try so they're always bound
        run_gvs = True
        run_reasoning = True
        gvs_result: Any = None
        plugins_executed: list[str] = []
        debrief = None

        try:
            # Stage 2: Load evaluator
            t0 = time.monotonic()
            evaluator = ReasoningEvaluator(
                workflow_id, contracts_dir=self._contracts_dir
            )
            stages_completed.append("load_scenario")
            stage_durations["load_scenario"] = time.monotonic() - t0

            # Load contract for config checks
            if contract is None:
                try:
                    from alphaswarm_sol.testing.evaluation.contract_loader import (
                        load_contract,
                    )
                    loaded = load_contract(
                        workflow_id, contracts_dir=self._contracts_dir
                    )
                    contract = loaded if isinstance(loaded, dict) else {}
                except Exception:
                    contract = {}

            eval_config = contract.get("evaluation_config", {})
            run_gvs = eval_config.get("run_gvs", True)
            run_reasoning = eval_config.get("run_reasoning", True)

            # Stage 3: Bridge to EvaluationInput
            t0 = time.monotonic()
            self._bridge_input(collected_output)
            stages_completed.append("collect_output")
            stage_durations["collect_output"] = time.monotonic() - t0

            # Stage 4: Parse observations (if available)
            t0 = time.monotonic()
            if effective_obs_dir and effective_obs_dir.exists():
                try:
                    from tests.workflow_harness.lib.observation_parser import (
                        ObservationParser,
                    )

                    parser = ObservationParser(
                        effective_obs_dir, session_id=session_id
                    )
                    obs_summary = parser.parse()

                    # SYN-01: Data quality warning (do NOT auto-reject)
                    if (
                        obs_summary.data_quality
                        and getattr(obs_summary.data_quality, "degraded", False)
                    ):
                        logger.warning(
                            "Data quality degraded for session %s", session_id
                        )
                except Exception:
                    health.errors += 1
            stages_completed.append("parse_observations")
            stage_durations["parse_observations"] = time.monotonic() - t0

            # Stage 5: Run GVS if contract says run_gvs: true
            t0 = time.monotonic()
            if run_gvs:
                try:
                    gvs = GraphValueScorer()
                    context: dict[str, Any] = {}
                    if obs_summary is not None:
                        context["obs_summary"] = obs_summary
                    if contract:
                        context["contract"] = contract
                    gvs_result = gvs.score(collected_output, context=context)
                except Exception:
                    health.errors += 1
            stages_completed.append("run_gvs")
            stage_durations["run_gvs"] = time.monotonic() - t0

            # Stage 6: Run reasoning evaluator if contract says run_reasoning: true
            # Wire ground_truth_rubric from contract (P15-IMP-33)
            t0 = time.monotonic()
            eval_context: dict[str, Any] = {}
            if contract and "ground_truth_rubric" in contract:
                eval_context["ground_truth_rubric"] = contract[
                    "ground_truth_rubric"
                ]

            debrief = None
            if debrief_agent_name and debrief_agent_type:
                debrief = run_debrief(
                    agent_name=debrief_agent_name,
                    agent_type=debrief_agent_type,
                    obs_dir=effective_obs_dir,
                    transcript_path=transcript_path,
                    simulated=self._run_mode == RunMode.SIMULATED,
                )

            if run_reasoning:
                score_card = evaluator.evaluate(
                    collected_output,
                    debrief=debrief,
                    obs_dir=effective_obs_dir,
                    obs_summary=obs_summary,
                    context=eval_context if eval_context else None,
                )
            else:
                score_card = ScoreCard(
                    workflow_id=workflow_id,
                    overall_score=0,
                    passed=False,
                    failure_narrative=None,
                )

            # Merge GVS plugin score into scorecard
            if gvs_result is not None:
                score_card.plugin_scores.append(gvs_result)

            plugins_executed = [ps.plugin_name for ps in score_card.plugin_scores]
            stages_completed.append("run_reasoning_evaluator")
            stage_durations["run_reasoning_evaluator"] = time.monotonic() - t0

            # Stage 7: Mode-aware dimension filtering (IMP-25)
            t0 = time.monotonic()
            score_card = self._apply_mode_filtering(score_card, self._run_mode)
            stages_completed.append("apply_mode_filtering")
            stage_durations["apply_mode_filtering"] = time.monotonic() - t0

        except FileNotFoundError:
            plugins_executed = []
            gvs_result = None
            run_reasoning = False
            score_card = ScoreCard(
                workflow_id=workflow_id,
                overall_score=0,
                passed=False,
                failure_narrative=None,
            )
            health.errors += 1

        elapsed_ms = (time.time() - start_time) * 1000.0

        # Build result
        health.parsed_records = len(stages_completed)
        health.stages_completed = stages_completed

        # Merge obs_summary stats into metadata if available
        result_metadata = dict(metadata or {})
        if obs_summary is not None:
            result_metadata["obs_summary"] = {
                "total_records": getattr(obs_summary, "total_records", 0),
                "tool_count": getattr(obs_summary, "tool_count", 0),
                "bskg_query_count": getattr(obs_summary, "bskg_query_count", 0),
            }

        # Data quality warning
        data_quality_warning = ""
        if (
            obs_summary is not None
            and obs_summary.data_quality
            and getattr(obs_summary.data_quality, "degraded", False)
        ):
            data_quality_warning = (
                "Observation data quality degraded — results may be unreliable"
            )

        status = "completed" if "run_reasoning_evaluator" in stages_completed else "failed"

        # Extract top-level GVS score from plugin scores
        top_level_gvs: float | None = None
        if gvs_result is not None:
            top_level_gvs = getattr(gvs_result, "score", None)

        # Extract reasoning assessment from score_card
        # The score_card produced by ReasoningEvaluator contains dimension scores
        reasoning_assess: Any | None = None
        if run_reasoning and score_card.dimensions:
            reasoning_assess = {
                "dimensions": {
                    d.dimension: d.score for d in score_card.dimensions if d.applicable
                },
                "overall_score": score_card.overall_score,
                "passed": score_card.passed,
            }

        eval_complete = status == "completed"

        result = EvaluationResult(
            scenario_name=scenario_name,
            workflow_id=workflow_id,
            run_mode=self._run_mode,
            score_card=score_card,
            pipeline_health=health,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
            run_duration_ms=elapsed_ms,
            trial_number=trial_number,
            metadata=result_metadata,
            plugins_executed=plugins_executed,
            data_quality_warning=data_quality_warning,
            status=status,
            graph_value_score=top_level_gvs,
            reasoning_assessment=reasoning_assess,
            evaluation_complete=eval_complete,
        )

        # Inject session correlation ID into result metadata
        result.metadata["session_correlation_id"] = correlation_id

        # Stage 8: Store result
        t0 = time.monotonic()
        if self._store is not None:
            try:
                self._store.store_result(result)
                self._store.append_history(workflow_id, result)
                stages_completed.append("store_result")
                health.parsed_records = len(stages_completed)
                health.stages_completed = stages_completed
            except Exception:
                health.errors += 1
        else:
            stages_completed.append("store_result")
            health.parsed_records = len(stages_completed)
            health.stages_completed = stages_completed
        stage_durations["store_result"] = time.monotonic() - t0

        # Stage 8.5: Integrity validation (D-5: auto-run after every session)
        t0 = time.monotonic()
        if effective_obs_dir and effective_obs_dir.exists():
            try:
                from alphaswarm_sol.testing.evaluation.agent_execution_validator import (
                    validate_batch,
                )

                batch_id_val = session_id or "unknown"
                integrity_report = validate_batch(
                    observation_dir=effective_obs_dir,
                    batch_id=batch_id_val,
                    ground_truth_dir=self._ground_truth_dir,
                )

                # Record integrity result in metadata
                warning_count = sum(
                    1 for v in integrity_report.violations
                    if v.severity == "warning"
                )
                critical_count = sum(
                    1 for v in integrity_report.violations
                    if v.severity == "critical"
                )
                result.metadata["integrity_check"] = {
                    "verdict": integrity_report.verdict,
                    "total_files": integrity_report.total_files,
                    "files_checked": integrity_report.files_checked,
                    "critical_violations": critical_count,
                    "warning_violations": warning_count,
                    "summary": integrity_report.summary,
                }

                # DEGRADED escalation: 3+ warnings -> FAIL (prevents dead zone)
                effective_verdict = integrity_report.verdict
                if effective_verdict == "DEGRADED" and warning_count >= 3:
                    effective_verdict = "FAIL"
                    result.metadata["integrity_check"]["escalated"] = True
                    result.metadata["integrity_check"]["escalation_reason"] = (
                        f"DEGRADED with {warning_count} warnings (>= 3) escalated to FAIL"
                    )
                    logger.warning(
                        "Integrity DEGRADED escalated to FAIL: %d warnings for session %s",
                        warning_count, session_id,
                    )

                # Auto-REJECT on FAIL verdict (original or escalated)
                if effective_verdict == "FAIL":
                    result.baseline_update_status = "rejected"

                    # Score tainting: mark result as polluted
                    result.metadata["tainted"] = True
                    result.metadata["taint_reason"] = (
                        f"integrity_check_failed: {integrity_report.summary}"
                    )

                    # Write rejection artifact
                    rejection_path = effective_obs_dir / "rejection.json"
                    rejection_path.write_text(
                        integrity_report.model_dump_json(indent=2)
                    )
                    result.metadata["integrity_rejection"] = {
                        "report_path": str(rejection_path),
                        "critical_count": critical_count,
                    }
                    logger.error(
                        "Integrity check FAILED for session %s: %s",
                        session_id, integrity_report.summary,
                    )

                stages_completed.append("integrity_check")
                health.parsed_records = len(stages_completed)
                health.stages_completed = stages_completed

            except Exception as e:
                logger.warning("Integrity check failed to run: %s", e)
                health.errors += 1
        stage_durations["integrity_check"] = time.monotonic() - t0

        # Stage 9: Debrief artifact persistence
        t0 = time.monotonic()
        if status == "completed" and debrief is not None:
            try:
                debrief_artifact = {
                    "agent_name": debrief.agent_name,
                    "layer_used": debrief.layer_used,
                    "answers": debrief.answers,
                    "confidence": debrief.confidence,
                    "questions_asked": debrief.questions,
                }

                # Intelligence-targeted signals (3.1c.3 needs)
                intelligence_signals = _extract_intelligence_signals(debrief)
                if intelligence_signals:
                    debrief_artifact["intelligence_signals"] = intelligence_signals

                # Persist to obs dir
                if effective_obs_dir:
                    debrief_path = effective_obs_dir / "debrief.json"
                    debrief_path.write_text(
                        json.dumps(debrief_artifact, indent=2)
                    )
                    result.metadata["debrief"] = {
                        "layer_used": debrief.layer_used,
                        "confidence": debrief.confidence,
                        "artifact_path": str(debrief_path),
                        "answer_count": len(debrief.answers),
                    }

                # Also persist to debrief_dir if configured
                if self._debrief_dir:
                    self._debrief_dir.mkdir(parents=True, exist_ok=True)
                    named_path = self._debrief_dir / f"{session_id or scenario_name}_debrief.json"
                    named_path.write_text(
                        json.dumps(debrief_artifact, indent=2)
                    )

                stages_completed.append("run_debrief")
                health.parsed_records = len(stages_completed)
                health.stages_completed = stages_completed

            except Exception as e:
                logger.warning("Debrief persistence failed: %s", e)
                health.errors += 1
        stage_durations["run_debrief"] = time.monotonic() - t0

        # Post-pipeline: Observation enrichment
        if effective_obs_dir and effective_obs_dir.exists():
            try:
                enrichment = {
                    "pipeline_timing": stage_durations,
                    "session_correlation_id": correlation_id,
                    "stages_completed": list(stages_completed),
                    "total_duration_s": sum(stage_durations.values()),
                }

                # Add integrity summary if available
                if "integrity_check" in result.metadata:
                    enrichment["integrity_verdict"] = result.metadata["integrity_check"]["verdict"]
                if result.metadata.get("tainted"):
                    enrichment["tainted"] = True

                enrichment_path = effective_obs_dir / "_enrichment.json"
                enrichment_path.write_text(json.dumps(enrichment, indent=2))

            except Exception as e:
                logger.warning("Observation enrichment failed: %s", e)

        # Record final timing in result metadata and health
        result.metadata["pipeline_timing"] = stage_durations
        health.stage_durations = stage_durations

        # Three-condition AND gate for baseline updates (P15-IMP-38)
        effective_score = score_card.effective_score()
        session_valid = manifest.valid if manifest is not None else True
        if self._baseline_manager is not None:
            if (
                session_valid
                and status == "completed"
                and effective_score is not None
                and not result.metadata.get("tainted")
            ):
                try:
                    if hasattr(self._baseline_manager, "_baseline_dir"):
                        lock_path = (
                            self._baseline_manager._baseline_dir / ".lock"
                        )
                        lock_path.parent.mkdir(parents=True, exist_ok=True)
                        lock_file = None
                        try:
                            lock_file = open(lock_path, "w")
                            fcntl.flock(lock_file, fcntl.LOCK_EX)
                            self._baseline_manager.update_baseline(
                                workflow_id, result
                            )
                        finally:
                            if lock_file is not None:
                                try:
                                    fcntl.flock(lock_file, fcntl.LOCK_UN)
                                    lock_file.close()
                                except Exception:
                                    pass
                    else:
                        self._baseline_manager.update_baseline(
                            workflow_id, result
                        )
                    result.baseline_update_status = "updated"
                except Exception:
                    health.errors += 1
                    result.baseline_update_status = "rejected"
            else:
                result.baseline_update_status = "rejected"

        # Post-run anomaly detection (IMP-26)
        run_count = 0
        if self._store is not None:
            try:
                history = self._store.list_results(
                    workflow_id=workflow_id, limit=ANOMALY_DETECTION_MIN_RUNS + 1
                )
                run_count = len(history)
            except Exception:
                pass
        anomaly_warnings = self._detect_anomalies(result, run_count)
        if anomaly_warnings:
            result.metadata["anomaly_warnings"] = anomaly_warnings
            logger.warning("Anomalies detected: %s", anomaly_warnings)

        # Improvement queue check (IMP-01)
        self._check_improvement_queue(result)

        # Session recording (additive — does not affect pipeline results)
        if self._session_recorder is not None and transcript_path is not None:
            try:
                from alphaswarm_sol.testing.evaluation.session_recorder import (
                    SessionMetadata as RecorderMetadata,
                )
                from alphaswarm_sol.testing.evaluation.transcript_session_extractor import (
                    TranscriptSessionExtractor,
                )

                extractor = TranscriptSessionExtractor(transcript_path)
                parsed_data = extractor.extract()
                # Map pipeline status to recorder verdict (PASS/DEGRADED/FAIL)
                if (
                    status == "completed"
                    and effective_score is not None
                    and effective_score >= 70
                ):
                    rec_verdict = "PASS"
                elif (
                    status == "completed"
                    and effective_score is not None
                    and effective_score >= 40
                ):
                    rec_verdict = "DEGRADED"
                else:
                    rec_verdict = "FAIL"

                rec_meta = RecorderMetadata(
                    teammate_name=metadata.get("teammate_name", "") if metadata else "",
                    agent_type=metadata.get("agent_type", "") if metadata else "",
                    contract=scenario_name,
                    workflow_id=workflow_id,
                    verdict=rec_verdict,
                    overall_score=effective_score,
                )
                recorded_id = self._session_recorder.record_session(
                    transcript_path=transcript_path,
                    metadata=rec_meta,
                    parsed_data=parsed_data,
                )
                result.metadata["recorded_session_id"] = recorded_id
            except Exception:
                logger.warning("Session recording failed", exc_info=True)

        return result

    def _bridge_input(self, collected_output: Any) -> EvaluationInput | None:
        """Bridge CollectedOutput to EvaluationInput if needed."""
        if isinstance(collected_output, EvaluationInput):
            return collected_output

        # Try to bridge from CollectedOutput dataclass
        if hasattr(collected_output, "tool_sequence"):
            try:
                return EvaluationInput.from_collected_output(
                    collected_output, self._run_mode
                )
            except Exception:
                return None

        return None

    def _load_score_history(self) -> dict[str, list[float]]:
        """Load per-workflow score history from the store.

        Returns:
            Mapping of workflow_id -> list of overall scores.
        """
        history: dict[str, list[float]] = {}
        if self._store is None:
            return history
        try:
            all_results = self._store.list_results(limit=500)
            for r in all_results:
                wid = r.workflow_id
                score = r.score_card.effective_score()
                if score is not None:
                    history.setdefault(wid, []).append(score)
        except Exception:
            logger.debug("Could not load score history for sorting", exc_info=True)
        return history

    def run_batch(
        self,
        scenarios: list[dict[str, Any]],
    ) -> list[EvaluationResult]:
        """Run multiple scenarios.

        Scenarios are sorted by difficulty (hardest first) using score
        history when available. On first run with no history, order is
        preserved (no-op sort).

        Args:
            scenarios: List of dicts with keys:
                scenario_name, workflow_id, collected_output,
                and optional debrief_*, trial_number, metadata.

        Returns:
            List of EvaluationResults.
        """
        # Sort by difficulty — hardest (lowest avg score) first
        history = self._load_score_history()
        sorted_scenarios = sort_contracts_by_difficulty(scenarios, history)

        results = []
        for spec in sorted_scenarios:
            result = self.run(
                scenario_name=spec["scenario_name"],
                workflow_id=spec["workflow_id"],
                collected_output=spec["collected_output"],
                debrief_agent_name=spec.get("debrief_agent_name"),
                debrief_agent_type=spec.get("debrief_agent_type"),
                transcript_path=spec.get("transcript_path"),
                trial_number=spec.get("trial_number", 1),
                metadata=spec.get("metadata"),
                session_id=spec.get("session_id"),
                contract=spec.get("contract"),
            )
            results.append(result)
        return results
