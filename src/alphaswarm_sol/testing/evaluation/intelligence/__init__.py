"""Tier 2 — Evaluation Intelligence layer.

Adaptive modules that activate incrementally as evaluation run data
accumulates. Tier 1 (Engine) plans 01-12 MUST NOT depend on intelligence
modules being active.

DC-2 enforcement: No imports from kg or vulndocs subpackages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.testing.evaluation.models import EvaluationStoreProtocol

from alphaswarm_sol.testing.evaluation.intelligence.tier_manager import (
    is_active as _tier_manager_active,
)
from alphaswarm_sol.testing.evaluation.intelligence.contract_healer import (
    is_active as _contract_healer_active,
)
from alphaswarm_sol.testing.evaluation.intelligence.coverage_radar import (
    is_active as _coverage_radar_active,
)

_MODULES = {
    "tier_manager": _tier_manager_active,
    "contract_healer": _contract_healer_active,
    "coverage_radar": _coverage_radar_active,
}


def get_active_modules(store: EvaluationStoreProtocol) -> list[str]:
    """Return names of intelligence modules that have enough data to activate.

    Args:
        store: Evaluation store to check for accumulated run data.

    Returns:
        List of module names that are currently active.
    """
    return [name for name, check_fn in _MODULES.items() if check_fn(store)]
