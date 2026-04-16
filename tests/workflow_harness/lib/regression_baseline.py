"""Regression Baseline — track and compare evaluation scores over time.

Implements the improvement loop for 3.1c-12:
- Capture baseline scores per workflow
- Compare new runs against baseline
- Detect regressions (score drops > threshold)
- Track improvement trends

CONTRACT_VERSION: 12.1
CONSUMERS: [3.1c-08 (Runner), CI pipeline]
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from alphaswarm_sol.testing.evaluation.models import EvaluationResult


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_REGRESSION_THRESHOLD = 5  # Points of score drop that triggers alert
DEFAULT_BASELINE_DIR = Path(".vrs/evaluation/baselines")

# Tier-to-threshold mapping (P2-IMP-07: BaselineManager needs tier awareness)
TIER_THRESHOLDS: dict[str, int] = {
    "core": 10,
    "important": 15,
    "standard": 25,
}

# Core workflow prefixes — heuristic scores are quarantined for these
CORE_WORKFLOW_PREFIXES = (
    "agent-vrs-attacker",
    "agent-vrs-defender",
    "agent-vrs-verifier",
    "agent-vrs-secure-reviewer",
    "skill-vrs-audit",
    "skill-vrs-verify",
    "skill-vrs-investigate",
    "skill-vrs-debate",
    "orchestrator-full-audit",
    "orchestrator-debate",
)


# ---------------------------------------------------------------------------
# Baseline data structures
# ---------------------------------------------------------------------------


@dataclass
class BaselineEntry:
    """A single workflow's baseline score."""

    workflow_id: str
    score: int
    trial_count: int = 1
    scores: list[int] = field(default_factory=list)
    last_updated: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def avg_score(self) -> float:
        return sum(self.scores) / len(self.scores) if self.scores else float(self.score)

    @property
    def min_score(self) -> int:
        return min(self.scores) if self.scores else self.score

    @property
    def max_score(self) -> int:
        return max(self.scores) if self.scores else self.score


@dataclass
class RegressionReport:
    """Result of comparing a new run against baseline."""

    workflow_id: str
    baseline_score: int
    new_score: int
    delta: int
    is_regression: bool
    threshold: int
    message: str


@dataclass
class ImprovementSummary:
    """Summary of improvements across multiple workflows."""

    total_workflows: int = 0
    improved: int = 0
    regressed: int = 0
    stable: int = 0
    reports: list[RegressionReport] = field(default_factory=list)

    @property
    def regression_rate(self) -> float:
        return self.regressed / max(self.total_workflows, 1)


# ---------------------------------------------------------------------------
# Baseline Manager
# ---------------------------------------------------------------------------


class BaselineManager:
    """Manage regression baselines for evaluation scores.

    Usage:
        mgr = BaselineManager(baseline_dir)
        mgr.update_baseline("skill-vrs-audit", result)
        report = mgr.check_regression("skill-vrs-audit", new_result)
    """

    def __init__(
        self,
        baseline_dir: Path | None = None,
        regression_threshold: int = DEFAULT_REGRESSION_THRESHOLD,
    ):
        self._baseline_dir = baseline_dir or DEFAULT_BASELINE_DIR
        self._baseline_dir.mkdir(parents=True, exist_ok=True)
        self._threshold = regression_threshold

    def get_baseline(self, workflow_id: str) -> BaselineEntry | None:
        """Get current baseline for a workflow."""
        path = self._baseline_dir / f"{workflow_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return BaselineEntry(**data)

    def _is_core_workflow(self, workflow_id: str) -> bool:
        """Check if a workflow is in the Core tier."""
        return any(workflow_id.startswith(prefix) for prefix in CORE_WORKFLOW_PREFIXES)

    def update_baseline(
        self,
        workflow_id: str,
        result: EvaluationResult,
    ) -> BaselineEntry:
        """Update baseline with a new evaluation result.

        Only updates if the result is reliable (pipeline health >= 60%).
        Rejects heuristic-scored Core results — they invert quality signal.
        Rejects capability-gating-failed results from baseline seeding.
        """
        # P3-IMP-05: Never seed baseline from capability gate failures
        if result.score_card.capability_gating_failed:
            existing = self.get_baseline(workflow_id)
            if existing:
                return existing
            # No baseline + gate failure = skip entirely (don't seed poison)
            return BaselineEntry(workflow_id=workflow_id, score=0)

        # P3-IMP-12/17: Quarantine heuristic scores for Core workflows
        if self._is_core_workflow(workflow_id) and result.score_card.has_heuristic_scores:
            existing = self.get_baseline(workflow_id)
            if existing:
                return existing
            # Don't seed Core baselines from heuristic data
            return BaselineEntry(workflow_id=workflow_id, score=0)

        if not result.is_reliable:
            existing = self.get_baseline(workflow_id)
            if existing:
                return existing
            # P3-IMP-05: Don't seed baselines from unreliable first runs either
            return BaselineEntry(workflow_id=workflow_id, score=0)

        existing = self.get_baseline(workflow_id)
        new_score = result.score_card.overall_score

        if existing:
            scores = existing.scores + [new_score]
            entry = BaselineEntry(
                workflow_id=workflow_id,
                score=new_score,
                trial_count=existing.trial_count + 1,
                scores=scores[-20:],  # Keep last 20 scores
                last_updated=result.completed_at or result.started_at,
                metadata=result.metadata,
            )
        else:
            entry = BaselineEntry(
                workflow_id=workflow_id,
                score=new_score,
                trial_count=1,
                scores=[new_score],
                last_updated=result.completed_at or result.started_at,
                metadata=result.metadata,
            )

        self._save_baseline(entry)
        return entry

    def check_regression(
        self,
        workflow_id: str,
        result: EvaluationResult,
    ) -> RegressionReport:
        """Check if a new result represents a regression.

        Returns:
            RegressionReport with regression status.
        """
        baseline = self.get_baseline(workflow_id)
        new_score = result.score_card.overall_score

        # P3-IMP-05: Skip regression comparison for capability gate failures
        if result.score_card.capability_gating_failed:
            return RegressionReport(
                workflow_id=workflow_id,
                baseline_score=baseline.score if baseline else 0,
                new_score=new_score,
                delta=0,
                is_regression=False,
                threshold=self._threshold,
                message=f"SKIP: {workflow_id} — capability gate failure, not comparable",
            )

        if baseline is None:
            return RegressionReport(
                workflow_id=workflow_id,
                baseline_score=0,
                new_score=new_score,
                delta=new_score,
                is_regression=False,
                threshold=self._threshold,
                message="No baseline — this is the first run",
            )

        delta = int(new_score - baseline.avg_score)
        is_regression = delta < -self._threshold

        if is_regression:
            msg = (
                f"REGRESSION: {workflow_id} dropped {abs(delta):.0f} points "
                f"({baseline.avg_score:.0f} avg → {new_score}, threshold: {self._threshold})"
            )
        elif delta > 0:
            msg = f"IMPROVED: {workflow_id} gained {delta:.0f} points ({baseline.avg_score:.0f} avg → {new_score})"
        else:
            msg = f"STABLE: {workflow_id} at {new_score} ({baseline.avg_score:.0f} avg baseline)"

        return RegressionReport(
            workflow_id=workflow_id,
            baseline_score=int(baseline.avg_score),
            new_score=new_score,
            delta=delta,
            is_regression=is_regression,
            threshold=self._threshold,
            message=msg,
        )

    def check_batch(
        self,
        results: list[EvaluationResult],
    ) -> ImprovementSummary:
        """Check regression for multiple results.

        Returns:
            ImprovementSummary across all workflows.
        """
        summary = ImprovementSummary(total_workflows=len(results))

        for result in results:
            report = self.check_regression(result.workflow_id, result)
            summary.reports.append(report)

            if report.is_regression:
                summary.regressed += 1
            elif report.delta > 0:
                summary.improved += 1
            else:
                summary.stable += 1

        return summary

    def list_baselines(self) -> list[BaselineEntry]:
        """List all stored baselines."""
        entries = []
        for path in sorted(self._baseline_dir.glob("*.json")):
            data = json.loads(path.read_text())
            entries.append(BaselineEntry(**data))
        return entries

    def _save_baseline(self, entry: BaselineEntry) -> None:
        """Persist a baseline entry."""
        path = self._baseline_dir / f"{entry.workflow_id}.json"
        data = {
            "workflow_id": entry.workflow_id,
            "score": entry.score,
            "trial_count": entry.trial_count,
            "scores": entry.scores,
            "last_updated": entry.last_updated,
            "metadata": entry.metadata,
        }
        path.write_text(json.dumps(data, indent=2))
