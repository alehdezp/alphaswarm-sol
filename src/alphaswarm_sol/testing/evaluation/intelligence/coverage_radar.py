"""Intelligence module: 4-axis coverage heat map.

v1 Implementation (Plan 12): Identifies under-evaluated workflows and
dimensions using coverage_axes from Plan 06.

DC-2 enforcement: No imports from kg or vulndocs subpackages.

Coverage Axes (4):
1. Workflow Coverage: % of workflows that have been evaluated
2. Dimension Coverage: % of reasoning dimensions scored per workflow
3. Tier Coverage: Distribution of evaluations across Core/Important/Standard
4. Contract Coverage: % of corpus contracts used in evaluations
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from alphaswarm_sol.testing.evaluation.models import EvaluationStoreProtocol

logger = logging.getLogger(__name__)

# Minimum results before coverage analysis activates
MIN_RESULTS_FOR_ACTIVATION = 5

# Expected dimensions for full coverage
EXPECTED_DIMENSIONS = [
    "hypothesis_formation",
    "query_formulation",
    "result_interpretation",
    "evidence_integration",
    "contradiction_handling",
    "conclusion_synthesis",
    "self_critique",
]


def is_active(store: EvaluationStoreProtocol) -> bool:
    """Check whether coverage_radar has enough data to activate.

    Requires at least MIN_RESULTS_FOR_ACTIVATION results.
    """
    try:
        results = store.list_results(limit=MIN_RESULTS_FOR_ACTIVATION + 1)
        return len(results) >= MIN_RESULTS_FOR_ACTIVATION
    except Exception:
        return False


class CoverageHeatMap:
    """4-axis coverage analysis for evaluation completeness."""

    def __init__(
        self,
        all_workflow_ids: list[str],
        all_contract_ids: list[str],
        tier_distribution: dict[str, list[str]],
    ) -> None:
        """Initialize with expected universe of workflows and contracts.

        Args:
            all_workflow_ids: All known workflow IDs (51 total).
            all_contract_ids: All corpus contract IDs.
            tier_distribution: Dict mapping tier -> list of workflow_ids.
        """
        self._all_workflows = set(all_workflow_ids)
        self._all_contracts = set(all_contract_ids)
        self._tier_distribution = tier_distribution

    def compute(
        self, store: EvaluationStoreProtocol
    ) -> dict[str, Any]:
        """Compute 4-axis coverage heat map.

        Returns:
            Dict with:
            - workflow_coverage: float (0-1)
            - dimension_coverage: float (0-1)
            - tier_coverage: dict per tier
            - contract_coverage: float (0-1)
            - gaps: list of identified coverage gaps
        """
        results = store.list_results(limit=1000)
        if not results:
            return {
                "workflow_coverage": 0.0,
                "dimension_coverage": 0.0,
                "tier_coverage": {},
                "contract_coverage": 0.0,
                "gaps": ["No evaluation results found"],
            }

        # Axis 1: Workflow Coverage
        evaluated_workflows = set()
        for r in results:
            if r.score_card:
                evaluated_workflows.add(r.score_card.workflow_id)
        workflow_coverage = (
            len(evaluated_workflows & self._all_workflows) / len(self._all_workflows)
            if self._all_workflows
            else 0.0
        )

        # Axis 2: Dimension Coverage
        dimension_hits: dict[str, int] = {d: 0 for d in EXPECTED_DIMENSIONS}
        scored_workflows = 0
        for r in results:
            if r.score_card and r.score_card.dimensions:
                scored_workflows += 1
                for dim in r.score_card.dimensions:
                    if dim.dimension in dimension_hits:
                        dimension_hits[dim.dimension] += 1
        dimension_coverage = (
            sum(1 for v in dimension_hits.values() if v > 0) / len(EXPECTED_DIMENSIONS)
            if EXPECTED_DIMENSIONS
            else 0.0
        )

        # Axis 3: Tier Coverage
        tier_coverage: dict[str, dict[str, Any]] = {}
        for tier, workflows in self._tier_distribution.items():
            tier_evaluated = evaluated_workflows & set(workflows)
            tier_coverage[tier] = {
                "total": len(workflows),
                "evaluated": len(tier_evaluated),
                "coverage": len(tier_evaluated) / len(workflows) if workflows else 0.0,
                "missing": sorted(set(workflows) - tier_evaluated),
            }

        # Axis 4: Contract Coverage
        evaluated_contracts: set[str] = set()
        for r in results:
            if hasattr(r, "metadata") and r.metadata:
                contract_id = r.metadata.get("contract_id")
                if contract_id:
                    evaluated_contracts.add(contract_id)
        contract_coverage = (
            len(evaluated_contracts & self._all_contracts) / len(self._all_contracts)
            if self._all_contracts
            else 0.0
        )

        # Identify gaps
        gaps: list[str] = []
        missing_workflows = self._all_workflows - evaluated_workflows
        if missing_workflows:
            gaps.append(
                f"Unevaluated workflows ({len(missing_workflows)}): "
                f"{sorted(list(missing_workflows)[:5])}"
            )
        zero_dims = [d for d, v in dimension_hits.items() if v == 0]
        if zero_dims:
            gaps.append(f"Unscored dimensions: {zero_dims}")
        for tier, info in tier_coverage.items():
            if info["coverage"] < 0.5:
                gaps.append(f"Tier '{tier}' under-evaluated: {info['coverage']:.0%}")

        return {
            "workflow_coverage": round(workflow_coverage, 3),
            "dimension_coverage": round(dimension_coverage, 3),
            "tier_coverage": tier_coverage,
            "contract_coverage": round(contract_coverage, 3),
            "gaps": gaps,
            "evaluated_workflows_count": len(evaluated_workflows),
            "total_workflows_count": len(self._all_workflows),
            "dimension_hits": dimension_hits,
        }
