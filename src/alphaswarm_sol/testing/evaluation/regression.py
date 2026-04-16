"""Regression detection and baseline management for evaluation pipeline.

Plan 12 Part 1: Establishes baseline from REAL evaluation data (Plans 09-11),
provides tier-weighted regression detection, and anti-fabrication checks.

DC-2 enforcement: No imports from kg or vulndocs subpackages.

Key types:
- BaselineEntry: Single workflow baseline record with scores and metadata
- BaselineManager: Loads/saves/queries baseline data, detects regressions
- AntiFabricationResult: Result of anti-fabrication checks on a session
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from alphaswarm_sol.testing.evaluation.models import BaselineKey

logger = logging.getLogger(__name__)

# Tier-weighted regression thresholds (locked decision)
REGRESSION_THRESHOLDS: dict[str, int] = {
    "core": 10,       # >10pt drop = REJECT
    "important": 15,  # >15pt drop = REJECT
    "standard": 25,   # >25pt drop = REJECT
}


class BaselineEntry(BaseModel):
    """Single workflow baseline record.

    Derived from REAL evaluation data (Plans 09-11).
    Anti-fabrication checks must pass before entry is accepted.
    """

    key: BaselineKey = Field(description="Composite lookup key")
    tier: Literal["core", "important", "standard"] = Field(
        description="Workflow tier for regression threshold selection"
    )
    overall_score: float = Field(
        ge=0, le=100, description="Baseline overall score"
    )
    dimension_scores: dict[str, int] = Field(
        default_factory=dict,
        description="Per-dimension scores (reasoning_dimensions from progress.json)",
    )
    source_plan: str = Field(
        description="Plan that produced this baseline entry (e.g., '3.1c-09')"
    )
    source_workflow_id: str = Field(
        description="Original workflow_id from progress.json"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When this baseline entry was recorded",
    )
    data_quality_warning: str | None = Field(
        default=None,
        description="If set, this entry is excluded from variance computation",
    )
    scoring_denominator_version: str = Field(
        default="v1",
        description="Must match current version for baseline to be valid",
    )

    model_config = {"extra": "forbid"}


class AntiFabricationResult(BaseModel):
    """Result of anti-fabrication checks on evaluation data.

    Six mandatory triggers — all must pass for data to be accepted.
    """

    passed: bool = Field(description="Whether all checks passed")
    triggers_fired: list[str] = Field(
        default_factory=list,
        description="Names of triggered anti-fabrication checks",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Per-trigger details",
    )

    model_config = {"extra": "forbid"}


class RegressionResult(BaseModel):
    """Result of regression check for a single workflow."""

    workflow_id: str
    tier: str
    threshold: int
    current_score: float
    baseline_score: float
    delta: float = Field(description="current - baseline (negative = regression)")
    verdict: Literal["PASS", "REJECT", "NO_BASELINE"] = Field(
        description="REJECT if |delta| > threshold and delta < 0"
    )

    model_config = {"extra": "forbid"}


class BaselineManager:
    """Manages evaluation baselines and regression detection.

    Reads/writes baseline data from .vrs/evaluations/baseline_data/.
    Provides tier-weighted regression detection.
    """

    def __init__(self, baseline_dir: Path | None = None) -> None:
        self._baseline_dir = baseline_dir or Path(
            ".vrs/evaluations/baseline_data"
        )
        self._entries: dict[str, BaselineEntry] = {}
        self._loaded = False

    def load(self) -> None:
        """Load baseline entries from disk."""
        self._entries.clear()
        if not self._baseline_dir.exists():
            logger.warning("Baseline directory does not exist: %s", self._baseline_dir)
            self._loaded = True
            return

        for path in sorted(self._baseline_dir.glob("*.json")):
            if path.name.startswith("_"):
                continue
            try:
                data = json.loads(path.read_text())
                entry = BaselineEntry.model_validate(data)
                self._entries[entry.key.workflow_id] = entry
            except Exception:
                logger.exception("Failed to load baseline entry: %s", path)

        self._loaded = True
        logger.info("Loaded %d baseline entries", len(self._entries))

    def save_entry(self, entry: BaselineEntry) -> Path:
        """Save a single baseline entry to disk.

        Returns:
            Path to the written file.
        """
        self._baseline_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{entry.key.workflow_id}.json"
        path = self._baseline_dir / filename
        path.write_text(entry.model_dump_json(indent=2))
        self._entries[entry.key.workflow_id] = entry
        return path

    def get_entry(self, workflow_id: str) -> BaselineEntry | None:
        """Get baseline entry for a workflow."""
        if not self._loaded:
            self.load()
        return self._entries.get(workflow_id)

    def all_entries(self) -> list[BaselineEntry]:
        """Get all baseline entries."""
        if not self._loaded:
            self.load()
        return list(self._entries.values())

    def check_regression(
        self, workflow_id: str, current_score: float
    ) -> RegressionResult:
        """Check if current score represents a regression from baseline.

        Uses tier-weighted thresholds:
        - Core: >10pt drop = REJECT
        - Important: >15pt drop = REJECT
        - Standard: >25pt drop = REJECT
        """
        entry = self.get_entry(workflow_id)
        if entry is None:
            return RegressionResult(
                workflow_id=workflow_id,
                tier="unknown",
                threshold=0,
                current_score=current_score,
                baseline_score=0,
                delta=0,
                verdict="NO_BASELINE",
            )

        threshold = REGRESSION_THRESHOLDS.get(entry.tier, 25)
        delta = current_score - entry.overall_score
        verdict: Literal["PASS", "REJECT", "NO_BASELINE"] = (
            "REJECT" if delta < 0 and abs(delta) > threshold else "PASS"
        )

        return RegressionResult(
            workflow_id=workflow_id,
            tier=entry.tier,
            threshold=threshold,
            current_score=current_score,
            baseline_score=entry.overall_score,
            delta=delta,
            verdict=verdict,
        )

    def check_all_regressions(
        self, current_scores: dict[str, float]
    ) -> list[RegressionResult]:
        """Check regressions for all workflows with current scores."""
        results = []
        for workflow_id, score in current_scores.items():
            results.append(self.check_regression(workflow_id, score))
        return results

    @property
    def entry_count(self) -> int:
        """Number of loaded baseline entries."""
        if not self._loaded:
            self.load()
        return len(self._entries)


def run_anti_fabrication_checks(
    entries: list[dict[str, Any]],
) -> AntiFabricationResult:
    """Run 6 mandatory anti-fabrication triggers on evaluation data.

    Triggers:
    1. NOT 100% pass rate across all capability checks
    2. NOT identical outputs across multiple runs of same workflow
    3. NOT scores at exactly 100 for all dimensions
    4. NOT duration < 5s for any evaluation session
    5. NOT identical reasoning_score across all Core agents
    6. NOT all fidelity_scores identical in orchestrator evaluations

    Args:
        entries: List of evaluation data dicts from progress.json

    Returns:
        AntiFabricationResult with pass/fail and trigger details.
    """
    triggers: list[str] = []
    details: dict[str, Any] = {}

    # Trigger 1: 100% pass rate
    pass_rates = [e.get("capability_check") == "passed" for e in entries if e.get("capability_check")]
    if pass_rates and all(pass_rates) and len(pass_rates) > 10:
        triggers.append("uniform_pass_rate")
        details["uniform_pass_rate"] = {
            "total": len(pass_rates),
            "all_passed": True,
            "note": "100% pass rate across >10 entries is suspicious",
        }

    # Trigger 2: Identical outputs
    outputs = [
        json.dumps(e.get("reasoning_dimensions", {}), sort_keys=True)
        for e in entries
        if e.get("reasoning_dimensions")
    ]
    if len(outputs) > 1 and len(set(outputs)) == 1:
        triggers.append("identical_outputs")
        details["identical_outputs"] = {
            "unique_outputs": 1,
            "total_outputs": len(outputs),
        }

    # Trigger 3: All scores at 100
    for entry in entries:
        dims = entry.get("reasoning_dimensions", {})
        if dims and all(v == 100 for v in dims.values()):
            triggers.append("ceiling_scores")
            details["ceiling_scores"] = {
                "workflow_id": entry.get("workflow_id"),
                "all_100": True,
            }
            break

    # Trigger 4: Duration < 5s (if duration info available)
    for entry in entries:
        started = entry.get("started_at")
        completed = entry.get("completed_at")
        if started and completed:
            try:
                start_dt = datetime.fromisoformat(started)
                end_dt = datetime.fromisoformat(completed)
                duration = (end_dt - start_dt).total_seconds()
                if duration < 5:
                    triggers.append("suspicious_duration")
                    details["suspicious_duration"] = {
                        "workflow_id": entry.get("workflow_id"),
                        "duration_seconds": duration,
                    }
                    break
            except (ValueError, TypeError):
                pass

    # Trigger 5: Identical reasoning scores across Core agents
    core_scores = [
        e.get("reasoning_score")
        for e in entries
        if e.get("tier") == "core" and e.get("reasoning_score") is not None
    ]
    if len(core_scores) > 1 and len(set(core_scores)) == 1:
        triggers.append("identical_core_scores")
        details["identical_core_scores"] = {
            "score": core_scores[0],
            "count": len(core_scores),
        }

    # Trigger 6: Identical fidelity scores in orchestrator evaluations
    fidelity_scores = [
        e.get("evidence_fidelity", {}).get("fidelity_score")
        for e in entries
        if e.get("evidence_fidelity", {}).get("fidelity_score") is not None
    ]
    if len(fidelity_scores) > 2 and len(set(fidelity_scores)) == 1:
        triggers.append("identical_fidelity")
        details["identical_fidelity"] = {
            "score": fidelity_scores[0],
            "count": len(fidelity_scores),
        }

    return AntiFabricationResult(
        passed=len(triggers) == 0,
        triggers_fired=triggers,
        details=details,
    )


# ---------------------------------------------------------------------------
# Adaptive Disagreement Threshold (R6 — EWMA tracker)
# ---------------------------------------------------------------------------

# Minimum observations before EWMA activates
EWMA_MIN_OBSERVATIONS = 25
# EWMA smoothing factor (lower = more smoothing)
EWMA_LAMBDA = 0.25
# Multiplier for standard deviation band
EWMA_K = 2.0
# Fallback fixed threshold when insufficient data
EWMA_FALLBACK_THRESHOLD = 15


class AdaptiveDisagreementTracker:
    """Track evaluator disagreements and compute adaptive thresholds via EWMA.

    Uses Exponentially Weighted Moving Average to replace the fixed 15-point
    disagreement threshold with a data-driven one. Falls back to fixed
    threshold until EWMA_MIN_OBSERVATIONS are collected.

    State is persisted to a JSON file for cross-session continuity.
    """

    def __init__(self, state_path: Path | None = None) -> None:
        self._state_path = state_path or Path(
            ".vrs/evaluations/disagreement_tracker.json"
        )
        self._observations: list[float] = []
        self._ewma: float | None = None
        self._ewma_variance: float | None = None
        self._loaded = False

    def load(self) -> None:
        """Load persisted state from disk."""
        self._observations = []
        self._ewma = None
        self._ewma_variance = None

        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text())
                self._observations = data.get("observations", [])
                self._ewma = data.get("ewma")
                self._ewma_variance = data.get("ewma_variance")
            except (json.JSONDecodeError, OSError):
                logger.warning("Could not load disagreement tracker state")

        self._loaded = True

    def save(self) -> None:
        """Persist current state to disk."""
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "observations": self._observations,
            "ewma": self._ewma,
            "ewma_variance": self._ewma_variance,
            "observation_count": len(self._observations),
        }
        self._state_path.write_text(json.dumps(data, indent=2))

    def record(self, disagreement: float) -> None:
        """Record a new evaluator disagreement observation.

        Updates EWMA and variance incrementally.

        Args:
            disagreement: Absolute point difference between dual evaluators.
        """
        if not self._loaded:
            self.load()

        self._observations.append(disagreement)

        # Update EWMA incrementally
        if self._ewma is None:
            self._ewma = disagreement
            self._ewma_variance = 0.0
        else:
            prev_ewma = self._ewma
            self._ewma = EWMA_LAMBDA * disagreement + (1 - EWMA_LAMBDA) * prev_ewma
            # Incremental variance: EWMA of squared deviations
            deviation_sq = (disagreement - prev_ewma) ** 2
            self._ewma_variance = (
                EWMA_LAMBDA * deviation_sq
                + (1 - EWMA_LAMBDA) * (self._ewma_variance or 0.0)
            )

    @property
    def threshold(self) -> float:
        """Current adaptive threshold.

        Returns EWMA + k * std_dev when enough data exists,
        otherwise the fixed fallback threshold.
        """
        if not self._loaded:
            self.load()

        if len(self._observations) < EWMA_MIN_OBSERVATIONS:
            return float(EWMA_FALLBACK_THRESHOLD)

        if self._ewma is None or self._ewma_variance is None:
            return float(EWMA_FALLBACK_THRESHOLD)

        std_dev = self._ewma_variance ** 0.5
        return self._ewma + EWMA_K * std_dev

    @property
    def observation_count(self) -> int:
        """Number of recorded observations."""
        if not self._loaded:
            self.load()
        return len(self._observations)

    @property
    def is_adaptive(self) -> bool:
        """Whether EWMA is active (enough observations)."""
        return self.observation_count >= EWMA_MIN_OBSERVATIONS
