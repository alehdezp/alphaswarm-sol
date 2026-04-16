"""Intelligence module: Adaptive tier promotion/demotion.

v1 Implementation (Plan 12): Wraps BaselineManager thresholds.
Human approval required for demotion via `tier_demotion_proposals.yaml`.

DC-2 enforcement: No imports from kg or vulndocs subpackages.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from alphaswarm_sol.testing.evaluation.models import EvaluationStoreProtocol

logger = logging.getLogger(__name__)

# Minimum runs required before tier changes are considered
MIN_RUNS_FOR_ACTIVATION = 5

# Sustained low score threshold (below this for MIN_RUNS triggers promotion)
LOW_SCORE_THRESHOLD = 50

# Tier promotion direction: Standard -> Important -> Core
TIER_ORDER: list[str] = ["standard", "important", "core"]


def is_active(store: EvaluationStoreProtocol) -> bool:
    """Check whether tier_manager has enough data to activate.

    Requires at least MIN_RUNS_FOR_ACTIVATION results to have meaningful
    statistics for tier change proposals.
    """
    try:
        results = store.list_results(limit=MIN_RUNS_FOR_ACTIVATION + 1)
        return len(results) >= MIN_RUNS_FOR_ACTIVATION
    except Exception:
        return False


def propose_tier_changes(
    store: EvaluationStoreProtocol,
    current_tiers: dict[str, str],
) -> list[dict[str, Any]]:
    """Propose tier changes based on sustained score patterns.

    Promotion (auto): If a Standard/Important workflow scores < LOW_SCORE_THRESHOLD
    for MIN_RUNS consecutive runs, propose promoting it (more scrutiny needed).

    Demotion (human-only): If a Core/Important workflow consistently scores > 90,
    propose demoting it to free evaluation budget. Requires human approval.

    Args:
        store: Evaluation store with historical data.
        current_tiers: Dict mapping workflow_id -> tier name.

    Returns:
        List of proposals, each a dict with keys:
        - workflow_id, current_tier, proposed_tier, direction, reason, auto_approve
    """
    proposals: list[dict[str, Any]] = []

    for workflow_id, current_tier in current_tiers.items():
        results = store.list_results(workflow_id=workflow_id, limit=MIN_RUNS_FOR_ACTIVATION)
        if len(results) < MIN_RUNS_FOR_ACTIVATION:
            continue

        scores = [r.score_card.overall_score for r in results if r.score_card]
        if not scores:
            continue

        # Promotion check: sustained low scores -> needs more attention
        if all(s < LOW_SCORE_THRESHOLD for s in scores[-MIN_RUNS_FOR_ACTIVATION:]):
            tier_idx = TIER_ORDER.index(current_tier) if current_tier in TIER_ORDER else 0
            if tier_idx < len(TIER_ORDER) - 1:
                proposed = TIER_ORDER[tier_idx + 1]
                proposals.append({
                    "workflow_id": workflow_id,
                    "current_tier": current_tier,
                    "proposed_tier": proposed,
                    "direction": "promote",
                    "reason": (
                        f"Sustained scores below {LOW_SCORE_THRESHOLD} "
                        f"for {MIN_RUNS_FOR_ACTIVATION} consecutive runs "
                        f"(scores: {scores[-MIN_RUNS_FOR_ACTIVATION:]})"
                    ),
                    "auto_approve": True,
                })

        # Demotion check: consistently high scores -> reduce evaluation budget
        elif all(s > 90 for s in scores[-MIN_RUNS_FOR_ACTIVATION:]):
            tier_idx = TIER_ORDER.index(current_tier) if current_tier in TIER_ORDER else 0
            if tier_idx > 0:
                proposed = TIER_ORDER[tier_idx - 1]
                proposals.append({
                    "workflow_id": workflow_id,
                    "current_tier": current_tier,
                    "proposed_tier": proposed,
                    "direction": "demote",
                    "reason": (
                        f"Consistently above 90 for {MIN_RUNS_FOR_ACTIVATION} runs "
                        f"(scores: {scores[-MIN_RUNS_FOR_ACTIVATION:]}). "
                        "Requires human approval."
                    ),
                    "auto_approve": False,  # Human approval required for demotion
                })

    return proposals
