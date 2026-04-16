"""Intelligence module: Evaluation contract self-healing.

v1 Implementation (Plan 12): Detects ceiling/floor/zero-variance anomalies
from BaselineManager's score windows.

DC-2 enforcement: No imports from kg or vulndocs subpackages.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from alphaswarm_sol.testing.evaluation.models import EvaluationStoreProtocol

logger = logging.getLogger(__name__)

# Minimum results before anomaly detection activates
MIN_RESULTS_FOR_ACTIVATION = 10

# Score window size for anomaly detection
WINDOW_SIZE = 20


def is_active(store: EvaluationStoreProtocol) -> bool:
    """Check whether contract_healer has enough data to activate.

    Requires at least MIN_RESULTS_FOR_ACTIVATION results.
    """
    try:
        results = store.list_results(limit=MIN_RESULTS_FOR_ACTIVATION + 1)
        return len(results) >= MIN_RESULTS_FOR_ACTIVATION
    except Exception:
        return False


def detect_anomalies(
    store: EvaluationStoreProtocol,
    workflow_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Detect ceiling, floor, and zero-variance anomalies in score windows.

    Anomaly types:
    - CEILING: All scores in window are >= 95 (evaluation too easy)
    - FLOOR: All scores in window are <= 10 (evaluation too hard or broken)
    - ZERO_VARIANCE: Standard deviation of window scores is 0 (degenerate)

    Args:
        store: Evaluation store with historical data.
        workflow_ids: Optional filter. If None, check all workflows.

    Returns:
        List of anomaly dicts with keys:
        - workflow_id, anomaly_type, scores, recommendation
    """
    anomalies: list[dict[str, Any]] = []

    results = store.list_results(limit=500)
    if not results:
        return anomalies

    # Group by workflow
    by_workflow: dict[str, list[int]] = {}
    for r in results:
        if r.score_card and (workflow_ids is None or r.score_card.workflow_id in workflow_ids):
            wid = r.score_card.workflow_id
            by_workflow.setdefault(wid, []).append(r.score_card.overall_score)

    for wid, scores in by_workflow.items():
        window = scores[-WINDOW_SIZE:]
        if len(window) < 3:
            continue

        # Ceiling: all scores >= 95
        if all(s >= 95 for s in window):
            anomalies.append({
                "workflow_id": wid,
                "anomaly_type": "CEILING",
                "scores": window,
                "recommendation": (
                    "Evaluation contract may be too easy. Consider: "
                    "(1) harder test contracts, (2) stricter rubric, "
                    "(3) verify evaluator isn't anchoring high."
                ),
            })

        # Floor: all scores <= 10
        elif all(s <= 10 for s in window):
            anomalies.append({
                "workflow_id": wid,
                "anomaly_type": "FLOOR",
                "scores": window,
                "recommendation": (
                    "Evaluation contract may be broken or too hard. Consider: "
                    "(1) verify capability contract isn't impossible, "
                    "(2) check for infrastructure failures, "
                    "(3) verify test contract is valid Solidity."
                ),
            })

        # Zero variance
        elif len(set(window)) == 1:
            anomalies.append({
                "workflow_id": wid,
                "anomaly_type": "ZERO_VARIANCE",
                "scores": window,
                "recommendation": (
                    "All scores identical — degenerate evaluation. Consider: "
                    "(1) verify evaluator temperature is non-zero, "
                    "(2) check for deterministic anchoring, "
                    "(3) verify transcript variation exists."
                ),
            })

    return anomalies
