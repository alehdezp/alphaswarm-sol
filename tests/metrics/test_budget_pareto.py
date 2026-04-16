"""Budget-Quality Pareto Tests (05.10-11)

Tests for budget-quality Pareto thresholds per PCONTEXT-11:
1. Pareto efficiency measurement
2. Budget-quality tradeoff analysis
3. Optimal budget selection
4. Pareto frontier computation

These tests ensure batch discovery achieves optimal budget-quality tradeoffs.
"""

from __future__ import annotations

import json
import math
import unittest
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# =============================================================================
# Pareto Constants
# =============================================================================


class BudgetTier(str, Enum):
    """Budget tier classification."""

    MINIMAL = "minimal"      # < 1000 tokens
    STANDARD = "standard"    # 1000-4000 tokens
    EXTENDED = "extended"    # 4000-8000 tokens
    COMPREHENSIVE = "comprehensive"  # > 8000 tokens


# Default Pareto thresholds (quality vs budget)
PARETO_QUALITY_FLOOR = 0.60  # Min F1 acceptable
PARETO_BUDGET_CEILING = 8000  # Max tokens acceptable
PARETO_EFFICIENCY_MIN = 0.5  # Min quality per 1000 tokens


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class BudgetPoint:
    """A single budget-quality data point."""

    budget_tokens: int
    quality_f1: float
    precision: float
    recall: float
    timestamp: str = ""
    pattern_count: int = 0
    mode: str = "batch"

    def efficiency(self) -> float:
        """Compute quality efficiency (F1 per 1000 tokens)."""
        if self.budget_tokens == 0:
            return 0.0
        return (self.quality_f1 * 1000) / self.budget_tokens

    def budget_tier(self) -> BudgetTier:
        """Classify budget tier."""
        if self.budget_tokens < 1000:
            return BudgetTier.MINIMAL
        elif self.budget_tokens < 4000:
            return BudgetTier.STANDARD
        elif self.budget_tokens < 8000:
            return BudgetTier.EXTENDED
        return BudgetTier.COMPREHENSIVE

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "budget_tokens": self.budget_tokens,
            "quality_f1": round(self.quality_f1, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "efficiency": round(self.efficiency(), 4),
            "budget_tier": self.budget_tier().value,
            "pattern_count": self.pattern_count,
            "mode": self.mode,
        }


@dataclass
class ParetoFrontier:
    """Pareto frontier of budget-quality tradeoffs."""

    frontier_points: List[BudgetPoint]
    dominated_points: List[BudgetPoint]
    optimal_point: Optional[BudgetPoint]

    @classmethod
    def compute(cls, points: List[BudgetPoint]) -> "ParetoFrontier":
        """Compute Pareto frontier from data points.

        A point is Pareto-optimal if no other point has both:
        - Higher quality (F1)
        - Lower budget (tokens)

        Args:
            points: List of budget-quality points

        Returns:
            ParetoFrontier with classified points
        """
        if not points:
            return cls(
                frontier_points=[],
                dominated_points=[],
                optimal_point=None,
            )

        frontier = []
        dominated = []

        for p in points:
            is_dominated = False
            for other in points:
                if other is p:
                    continue
                # Check if other dominates p (better quality AND lower budget)
                if other.quality_f1 >= p.quality_f1 and other.budget_tokens <= p.budget_tokens:
                    if other.quality_f1 > p.quality_f1 or other.budget_tokens < p.budget_tokens:
                        is_dominated = True
                        break

            if is_dominated:
                dominated.append(p)
            else:
                frontier.append(p)

        # Sort frontier by budget (ascending)
        frontier.sort(key=lambda x: x.budget_tokens)

        # Find optimal point: highest efficiency on frontier
        optimal = max(frontier, key=lambda x: x.efficiency()) if frontier else None

        return cls(
            frontier_points=frontier,
            dominated_points=dominated,
            optimal_point=optimal,
        )

    def meets_quality_floor(self) -> bool:
        """Check if frontier has points meeting quality floor."""
        return any(p.quality_f1 >= PARETO_QUALITY_FLOOR for p in self.frontier_points)

    def meets_budget_ceiling(self) -> bool:
        """Check if frontier has points within budget ceiling."""
        return any(p.budget_tokens <= PARETO_BUDGET_CEILING for p in self.frontier_points)

    def optimal_within_budget(self, max_budget: int) -> Optional[BudgetPoint]:
        """Find optimal point within a budget constraint.

        Args:
            max_budget: Maximum allowed tokens

        Returns:
            Best quality point within budget, or None
        """
        within_budget = [p for p in self.frontier_points if p.budget_tokens <= max_budget]
        if not within_budget:
            return None
        return max(within_budget, key=lambda x: x.quality_f1)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "frontier_points": [p.to_dict() for p in self.frontier_points],
            "dominated_points": [p.to_dict() for p in self.dominated_points],
            "optimal_point": self.optimal_point.to_dict() if self.optimal_point else None,
            "meets_quality_floor": self.meets_quality_floor(),
            "meets_budget_ceiling": self.meets_budget_ceiling(),
        }


@dataclass
class ParetoAnalysis:
    """Complete Pareto analysis for batch discovery."""

    frontier: ParetoFrontier
    efficiency_by_tier: Dict[str, float]
    recommended_tier: BudgetTier
    quality_budget_ratio: float  # Quality gained per token spent

    @classmethod
    def compute(cls, points: List[BudgetPoint]) -> "ParetoAnalysis":
        """Compute complete Pareto analysis.

        Args:
            points: Budget-quality data points

        Returns:
            ParetoAnalysis with recommendations
        """
        frontier = ParetoFrontier.compute(points)

        # Compute efficiency by tier
        tier_efficiencies: Dict[str, List[float]] = {
            BudgetTier.MINIMAL.value: [],
            BudgetTier.STANDARD.value: [],
            BudgetTier.EXTENDED.value: [],
            BudgetTier.COMPREHENSIVE.value: [],
        }

        for p in points:
            tier_efficiencies[p.budget_tier().value].append(p.efficiency())

        efficiency_by_tier = {
            tier: sum(effs) / len(effs) if effs else 0.0
            for tier, effs in tier_efficiencies.items()
        }

        # Find recommended tier (highest average efficiency)
        if efficiency_by_tier:
            recommended = max(efficiency_by_tier.keys(), key=lambda t: efficiency_by_tier[t])
            recommended_tier = BudgetTier(recommended)
        else:
            recommended_tier = BudgetTier.STANDARD

        # Compute overall quality-budget ratio
        if points:
            total_quality = sum(p.quality_f1 for p in points)
            total_budget = sum(p.budget_tokens for p in points)
            ratio = total_quality / total_budget * 1000 if total_budget > 0 else 0.0
        else:
            ratio = 0.0

        return cls(
            frontier=frontier,
            efficiency_by_tier=efficiency_by_tier,
            recommended_tier=recommended_tier,
            quality_budget_ratio=ratio,
        )

    def passes_pareto_check(self) -> bool:
        """Check if analysis passes Pareto quality checks."""
        return (
            self.frontier.meets_quality_floor()
            and self.frontier.meets_budget_ceiling()
            and self.quality_budget_ratio >= PARETO_EFFICIENCY_MIN
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "frontier": self.frontier.to_dict(),
            "efficiency_by_tier": {
                k: round(v, 4) for k, v in self.efficiency_by_tier.items()
            },
            "recommended_tier": self.recommended_tier.value,
            "quality_budget_ratio": round(self.quality_budget_ratio, 4),
            "passes_pareto_check": self.passes_pareto_check(),
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


# =============================================================================
# Test Cases
# =============================================================================


class TestBudgetPoint(unittest.TestCase):
    """Tests for BudgetPoint dataclass."""

    def test_efficiency_calculation(self):
        """Efficiency should be F1 per 1000 tokens."""
        point = BudgetPoint(
            budget_tokens=2000,
            quality_f1=0.8,
            precision=0.85,
            recall=0.75,
        )

        # 0.8 * 1000 / 2000 = 0.4
        self.assertEqual(point.efficiency(), 0.4)

    def test_zero_budget_efficiency(self):
        """Zero budget should return zero efficiency."""
        point = BudgetPoint(0, 0.8, 0.8, 0.8)
        self.assertEqual(point.efficiency(), 0.0)

    def test_budget_tier_minimal(self):
        """Budget < 1000 should be MINIMAL."""
        point = BudgetPoint(500, 0.5, 0.5, 0.5)
        self.assertEqual(point.budget_tier(), BudgetTier.MINIMAL)

    def test_budget_tier_standard(self):
        """Budget 1000-4000 should be STANDARD."""
        point = BudgetPoint(2000, 0.7, 0.7, 0.7)
        self.assertEqual(point.budget_tier(), BudgetTier.STANDARD)

    def test_budget_tier_extended(self):
        """Budget 4000-8000 should be EXTENDED."""
        point = BudgetPoint(6000, 0.85, 0.85, 0.85)
        self.assertEqual(point.budget_tier(), BudgetTier.EXTENDED)

    def test_budget_tier_comprehensive(self):
        """Budget > 8000 should be COMPREHENSIVE."""
        point = BudgetPoint(10000, 0.95, 0.95, 0.95)
        self.assertEqual(point.budget_tier(), BudgetTier.COMPREHENSIVE)

    def test_serialization(self):
        """Point should serialize correctly."""
        point = BudgetPoint(3000, 0.75, 0.80, 0.70, pattern_count=10)
        data = point.to_dict()

        self.assertEqual(data["budget_tokens"], 3000)
        self.assertEqual(data["quality_f1"], 0.75)
        self.assertIn("efficiency", data)
        self.assertIn("budget_tier", data)


class TestParetoFrontier(unittest.TestCase):
    """Tests for ParetoFrontier computation."""

    def test_empty_points(self):
        """Empty points should return empty frontier."""
        frontier = ParetoFrontier.compute([])

        self.assertEqual(len(frontier.frontier_points), 0)
        self.assertEqual(len(frontier.dominated_points), 0)
        self.assertIsNone(frontier.optimal_point)

    def test_single_point_on_frontier(self):
        """Single point should be on frontier."""
        points = [BudgetPoint(2000, 0.8, 0.8, 0.8)]
        frontier = ParetoFrontier.compute(points)

        self.assertEqual(len(frontier.frontier_points), 1)
        self.assertEqual(len(frontier.dominated_points), 0)

    def test_dominated_point_identification(self):
        """Dominated points should be correctly identified."""
        points = [
            BudgetPoint(2000, 0.9, 0.9, 0.9),  # On frontier (high quality)
            BudgetPoint(3000, 0.85, 0.85, 0.85),  # Dominated (worse on both)
            BudgetPoint(1500, 0.7, 0.7, 0.7),  # On frontier (lower budget)
        ]

        frontier = ParetoFrontier.compute(points)

        # Point 2 is dominated: lower quality AND higher budget than point 1
        self.assertEqual(len(frontier.frontier_points), 2)
        self.assertEqual(len(frontier.dominated_points), 1)
        self.assertEqual(frontier.dominated_points[0].budget_tokens, 3000)

    def test_frontier_sorted_by_budget(self):
        """Frontier should be sorted by budget ascending."""
        points = [
            BudgetPoint(5000, 0.95, 0.95, 0.95),
            BudgetPoint(1000, 0.6, 0.6, 0.6),
            BudgetPoint(3000, 0.85, 0.85, 0.85),
        ]

        frontier = ParetoFrontier.compute(points)

        budgets = [p.budget_tokens for p in frontier.frontier_points]
        self.assertEqual(budgets, sorted(budgets))

    def test_optimal_point_highest_efficiency(self):
        """Optimal point should have highest efficiency."""
        points = [
            BudgetPoint(1000, 0.6, 0.6, 0.6),   # efficiency = 0.6
            BudgetPoint(2000, 0.9, 0.9, 0.9),   # efficiency = 0.45
            BudgetPoint(3000, 0.95, 0.95, 0.95),  # efficiency = 0.317
        ]

        frontier = ParetoFrontier.compute(points)

        # First point has highest efficiency
        self.assertEqual(frontier.optimal_point.budget_tokens, 1000)

    def test_meets_quality_floor(self):
        """Should check if any point meets quality floor."""
        good_points = [BudgetPoint(2000, 0.7, 0.7, 0.7)]  # Above 0.6
        bad_points = [BudgetPoint(2000, 0.5, 0.5, 0.5)]   # Below 0.6

        good_frontier = ParetoFrontier.compute(good_points)
        bad_frontier = ParetoFrontier.compute(bad_points)

        self.assertTrue(good_frontier.meets_quality_floor())
        self.assertFalse(bad_frontier.meets_quality_floor())

    def test_meets_budget_ceiling(self):
        """Should check if any point within budget ceiling."""
        good_points = [BudgetPoint(6000, 0.8, 0.8, 0.8)]  # Under 8000
        bad_points = [BudgetPoint(10000, 0.9, 0.9, 0.9)]  # Over 8000

        good_frontier = ParetoFrontier.compute(good_points)
        bad_frontier = ParetoFrontier.compute(bad_points)

        self.assertTrue(good_frontier.meets_budget_ceiling())
        self.assertFalse(bad_frontier.meets_budget_ceiling())

    def test_optimal_within_budget(self):
        """Should find best point within budget constraint."""
        points = [
            BudgetPoint(1000, 0.5, 0.5, 0.5),
            BudgetPoint(2500, 0.75, 0.75, 0.75),
            BudgetPoint(5000, 0.9, 0.9, 0.9),
        ]

        frontier = ParetoFrontier.compute(points)

        # With budget 3000, best is the 2500-token point
        best = frontier.optimal_within_budget(3000)
        self.assertEqual(best.budget_tokens, 2500)
        self.assertEqual(best.quality_f1, 0.75)

        # With budget 1500, best is the 1000-token point
        best = frontier.optimal_within_budget(1500)
        self.assertEqual(best.budget_tokens, 1000)

        # With budget 500, no point available
        best = frontier.optimal_within_budget(500)
        self.assertIsNone(best)


class TestParetoAnalysis(unittest.TestCase):
    """Tests for complete Pareto analysis."""

    def test_efficiency_by_tier(self):
        """Should compute average efficiency per tier."""
        points = [
            BudgetPoint(500, 0.4, 0.4, 0.4),    # MINIMAL, eff=0.8
            BudgetPoint(800, 0.5, 0.5, 0.5),    # MINIMAL, eff=0.625
            BudgetPoint(2000, 0.7, 0.7, 0.7),   # STANDARD, eff=0.35
            BudgetPoint(3000, 0.75, 0.75, 0.75),  # STANDARD, eff=0.25
        ]

        analysis = ParetoAnalysis.compute(points)

        # MINIMAL average: (0.8 + 0.625) / 2 = 0.7125
        self.assertAlmostEqual(
            analysis.efficiency_by_tier[BudgetTier.MINIMAL.value],
            0.7125,
            places=2,
        )

        # STANDARD average: (0.35 + 0.25) / 2 = 0.30
        self.assertAlmostEqual(
            analysis.efficiency_by_tier[BudgetTier.STANDARD.value],
            0.30,
            places=2,
        )

    def test_recommended_tier(self):
        """Should recommend tier with highest efficiency."""
        points = [
            BudgetPoint(500, 0.5, 0.5, 0.5),    # MINIMAL, eff=1.0
            BudgetPoint(2000, 0.6, 0.6, 0.6),   # STANDARD, eff=0.3
            BudgetPoint(5000, 0.8, 0.8, 0.8),   # EXTENDED, eff=0.16
        ]

        analysis = ParetoAnalysis.compute(points)

        # MINIMAL has highest efficiency
        self.assertEqual(analysis.recommended_tier, BudgetTier.MINIMAL)

    def test_quality_budget_ratio(self):
        """Should compute overall quality-budget ratio."""
        points = [
            BudgetPoint(1000, 0.6, 0.6, 0.6),
            BudgetPoint(2000, 0.8, 0.8, 0.8),
        ]

        analysis = ParetoAnalysis.compute(points)

        # Total quality: 1.4, Total budget: 3000
        # Ratio: 1.4 / 3000 * 1000 = 0.467
        self.assertAlmostEqual(analysis.quality_budget_ratio, 0.467, places=2)

    def test_passes_pareto_check(self):
        """Should pass when meeting all criteria."""
        # Good points: meet quality floor, budget ceiling, efficiency
        # Points need high efficiency: F1 * 1000 / budget >= 0.5
        good_points = [
            BudgetPoint(1000, 0.7, 0.7, 0.7),   # High efficiency (0.7)
            BudgetPoint(1500, 0.85, 0.85, 0.85),  # High efficiency (0.57)
        ]

        good_analysis = ParetoAnalysis.compute(good_points)
        self.assertTrue(good_analysis.passes_pareto_check())

    def test_fails_pareto_check_low_quality(self):
        """Should fail when quality floor not met."""
        points = [BudgetPoint(2000, 0.4, 0.4, 0.4)]  # Below 0.6 floor

        analysis = ParetoAnalysis.compute(points)
        self.assertFalse(analysis.passes_pareto_check())

    def test_fails_pareto_check_high_budget(self):
        """Should fail when only over-budget points exist."""
        points = [BudgetPoint(10000, 0.9, 0.9, 0.9)]  # Above 8000 ceiling

        analysis = ParetoAnalysis.compute(points)
        self.assertFalse(analysis.passes_pareto_check())

    def test_json_serialization(self):
        """Analysis should serialize to valid JSON."""
        points = [
            BudgetPoint(2000, 0.7, 0.75, 0.65, pattern_count=5),
            BudgetPoint(4000, 0.85, 0.88, 0.82, pattern_count=10),
        ]

        analysis = ParetoAnalysis.compute(points)
        json_str = analysis.to_json()
        parsed = json.loads(json_str)

        self.assertIn("frontier", parsed)
        self.assertIn("efficiency_by_tier", parsed)
        self.assertIn("recommended_tier", parsed)
        self.assertIn("passes_pareto_check", parsed)


class TestParetoThresholds(unittest.TestCase):
    """Tests for Pareto threshold constants."""

    def test_threshold_values(self):
        """Thresholds should have sensible values."""
        self.assertEqual(PARETO_QUALITY_FLOOR, 0.60)
        self.assertEqual(PARETO_BUDGET_CEILING, 8000)
        self.assertEqual(PARETO_EFFICIENCY_MIN, 0.5)

    def test_thresholds_reasonable(self):
        """Thresholds should be in reasonable ranges."""
        # Quality floor between 0 and 1
        self.assertGreater(PARETO_QUALITY_FLOOR, 0)
        self.assertLess(PARETO_QUALITY_FLOOR, 1)

        # Budget ceiling positive
        self.assertGreater(PARETO_BUDGET_CEILING, 0)

        # Efficiency min positive
        self.assertGreater(PARETO_EFFICIENCY_MIN, 0)


class TestParetoIntegration(unittest.TestCase):
    """Integration tests for Pareto analysis."""

    def test_batch_discovery_pareto_analysis(self):
        """Simulate batch discovery Pareto analysis."""
        # Simulate results from different batch configurations
        batch_results = [
            BudgetPoint(1500, 0.55, 0.60, 0.50, pattern_count=5, mode="batch-minimal"),
            BudgetPoint(2500, 0.70, 0.75, 0.65, pattern_count=8, mode="batch-standard"),
            BudgetPoint(4000, 0.82, 0.85, 0.79, pattern_count=12, mode="batch-extended"),
            BudgetPoint(6000, 0.88, 0.90, 0.86, pattern_count=15, mode="batch-full"),
            BudgetPoint(8500, 0.92, 0.93, 0.91, pattern_count=18, mode="batch-comprehensive"),
        ]

        analysis = ParetoAnalysis.compute(batch_results)

        # Should have computed frontier
        self.assertGreater(len(analysis.frontier.frontier_points), 0)

        # Should have identified optimal
        self.assertIsNotNone(analysis.frontier.optimal_point)

        # Should meet quality and budget constraints
        self.assertTrue(analysis.frontier.meets_quality_floor())
        self.assertTrue(analysis.frontier.meets_budget_ceiling())

    def test_ci_ready_output(self):
        """Output should be CI-ready (valid JSON, required fields)."""
        points = [
            BudgetPoint(2000, 0.7, 0.75, 0.65),
            BudgetPoint(4000, 0.85, 0.88, 0.82),
        ]

        analysis = ParetoAnalysis.compute(points)
        output = analysis.to_dict()

        # Required fields for CI
        self.assertIn("passes_pareto_check", output)
        self.assertIn("frontier", output)
        self.assertIn("recommended_tier", output)
        self.assertIn("quality_budget_ratio", output)

        # Should be JSON serializable
        json.dumps(output)

    def test_budget_optimization_recommendation(self):
        """Should recommend optimal budget for target quality."""
        points = [
            BudgetPoint(1000, 0.5, 0.5, 0.5),
            BudgetPoint(2000, 0.7, 0.7, 0.7),
            BudgetPoint(3000, 0.8, 0.8, 0.8),
            BudgetPoint(4000, 0.85, 0.85, 0.85),
            BudgetPoint(6000, 0.9, 0.9, 0.9),
        ]

        analysis = ParetoAnalysis.compute(points)

        # For quality >= 0.7, minimum budget should be 2000
        optimal = analysis.frontier.optimal_within_budget(2000)
        self.assertIsNotNone(optimal)
        self.assertGreaterEqual(optimal.quality_f1, 0.7)


if __name__ == "__main__":
    unittest.main()
