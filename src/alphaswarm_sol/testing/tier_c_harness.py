"""Tier C Stability + Shadow Mode Harness.

Provides stability testing for label-dependent (Tier C) patterns to detect
instability before GA validation. Implements:

1. Stability Testing: Run Tier C detection N=50 times per pattern and
   compute stability score. Patterns below 0.85 stability threshold fail.

2. Shadow Mode: Run dual labelers with different prompt slices and enforce
   70% label overlap consensus threshold.

Per Phase 7.2 CONTEXT.md:
- Tier C repeat runs: 50 runs per pattern (thorough)
- Stability threshold: >= 0.85 (85% consistent findings)
- Shadow mode consensus: >= 70% label overlap

Output: `.vrs/testing/tier_c_stability.yaml` report with per-pattern stability scores.
"""

from __future__ import annotations

import hashlib
import logging
import random
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from alphaswarm_sol.labels.overlay import LabelOverlay
from alphaswarm_sol.queries.tier_c import TierCMatcher, TierCMatch


logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_STABILITY_RUNS = 50
STABILITY_THRESHOLD = 0.85
SHADOW_MODE_CONSENSUS_THRESHOLD = 0.70
TIER_C_STABILITY_REPORT_PATH = Path(".vrs/testing/tier_c_stability.yaml")


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class PatternStabilityResult:
    """Stability result for a single pattern.

    Attributes:
        pattern_id: Pattern identifier
        stability_score: Stability score [0.0, 1.0]
        runs_total: Total number of runs
        runs_consistent: Number of consistent runs
        findings_variance: Variance in findings count across runs
        passed: Whether pattern meets stability threshold
        details: Per-run details for debugging
    """

    pattern_id: str
    stability_score: float
    runs_total: int
    runs_consistent: int
    findings_variance: float
    passed: bool
    details: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "stability_score": round(self.stability_score, 4),
            "runs_total": self.runs_total,
            "runs_consistent": self.runs_consistent,
            "findings_variance": round(self.findings_variance, 4),
            "passed": self.passed,
            "details": self.details[:5],  # Only keep first 5 for report
        }


@dataclass
class ShadowModeResult:
    """Result from shadow mode dual-labeler comparison.

    Attributes:
        pattern_id: Pattern identifier
        overlap_score: Label overlap score [0.0, 1.0]
        consensus_reached: Whether 70% consensus threshold met
        labeler_a_labels: Labels from labeler A
        labeler_b_labels: Labels from labeler B
        agreed_labels: Labels both labelers agreed on
        disagreed_labels: Labels with disagreement
        notes: Disagreement analysis notes
    """

    pattern_id: str
    overlap_score: float
    consensus_reached: bool
    labeler_a_labels: Set[str] = field(default_factory=set)
    labeler_b_labels: Set[str] = field(default_factory=set)
    agreed_labels: Set[str] = field(default_factory=set)
    disagreed_labels: Set[str] = field(default_factory=set)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "overlap_score": round(self.overlap_score, 4),
            "consensus_reached": self.consensus_reached,
            "labeler_a_count": len(self.labeler_a_labels),
            "labeler_b_count": len(self.labeler_b_labels),
            "agreed_count": len(self.agreed_labels),
            "disagreed_count": len(self.disagreed_labels),
            "agreed_labels": list(self.agreed_labels),
            "disagreed_labels": list(self.disagreed_labels),
            "notes": self.notes,
        }


@dataclass
class TierCStabilityReport:
    """Complete Tier C stability report.

    Attributes:
        timestamp: When report was generated
        total_patterns: Total patterns tested
        patterns_passed: Patterns meeting stability threshold
        patterns_failed: Patterns failing stability threshold
        overall_stability: Average stability across all patterns
        shadow_mode_enabled: Whether shadow mode was run
        shadow_mode_consensus_rate: Rate of consensus in shadow mode
        pattern_results: Per-pattern stability results
        shadow_mode_results: Per-pattern shadow mode results
        config: Configuration used for the run
    """

    timestamp: str
    total_patterns: int
    patterns_passed: int
    patterns_failed: int
    overall_stability: float
    shadow_mode_enabled: bool
    shadow_mode_consensus_rate: float
    pattern_results: List[PatternStabilityResult]
    shadow_mode_results: List[ShadowModeResult]
    config: Dict[str, Any]
    execution_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "metadata": {
                "timestamp": self.timestamp,
                "execution_time_ms": self.execution_time_ms,
            },
            "summary": {
                "total_patterns": self.total_patterns,
                "patterns_passed": self.patterns_passed,
                "patterns_failed": self.patterns_failed,
                "overall_stability": round(self.overall_stability, 4),
                "shadow_mode_enabled": self.shadow_mode_enabled,
                "shadow_mode_consensus_rate": round(self.shadow_mode_consensus_rate, 4),
            },
            "config": self.config,
            "pattern_results": [r.to_dict() for r in self.pattern_results],
            "shadow_mode_results": [r.to_dict() for r in self.shadow_mode_results],
        }

    def save(self, path: Optional[Path] = None) -> Path:
        """Save report to YAML file.

        Args:
            path: Custom path (defaults to .vrs/testing/tier_c_stability.yaml)

        Returns:
            Path where report was saved
        """
        output_path = path or TIER_C_STABILITY_REPORT_PATH
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            yaml.dump(
                self.to_dict(),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

        logger.info(f"Tier C stability report saved to {output_path}")
        return output_path


# =============================================================================
# Tier C Stability Harness
# =============================================================================


class TierCStabilityHarness:
    """Harness for testing Tier C pattern stability.

    Runs label-based detection multiple times per pattern and computes
    stability scores. Supports shadow mode with dual labelers.

    Example:
        >>> harness = TierCStabilityHarness(
        ...     overlay=label_overlay,
        ...     stability_runs=50,
        ...     stability_threshold=0.85,
        ... )
        >>> report = harness.run_stability_test(patterns, node_ids)
        >>> print(report.overall_stability)
    """

    def __init__(
        self,
        overlay: LabelOverlay,
        stability_runs: int = DEFAULT_STABILITY_RUNS,
        stability_threshold: float = STABILITY_THRESHOLD,
        shadow_mode_threshold: float = SHADOW_MODE_CONSENSUS_THRESHOLD,
        enable_shadow_mode: bool = True,
    ):
        """Initialize harness.

        Args:
            overlay: Primary label overlay for testing
            stability_runs: Number of runs per pattern (default: 50)
            stability_threshold: Minimum stability score to pass (default: 0.85)
            shadow_mode_threshold: Consensus threshold for shadow mode (default: 0.70)
            enable_shadow_mode: Whether to run shadow mode tests
        """
        self.overlay = overlay
        self.stability_runs = stability_runs
        self.stability_threshold = stability_threshold
        self.shadow_mode_threshold = shadow_mode_threshold
        self.enable_shadow_mode = enable_shadow_mode

        # Secondary overlay for shadow mode (simulates different labeler)
        self._shadow_overlay: Optional[LabelOverlay] = None

    def set_shadow_overlay(self, overlay: LabelOverlay) -> None:
        """Set secondary overlay for shadow mode comparison.

        Args:
            overlay: Secondary labeler's overlay
        """
        self._shadow_overlay = overlay

    def run_stability_test(
        self,
        patterns: List[Dict[str, Any]],
        node_ids: List[str],
        seed: Optional[int] = None,
    ) -> TierCStabilityReport:
        """Run stability test for multiple patterns.

        Args:
            patterns: List of Tier C pattern definitions (with tier_c_* conditions)
            node_ids: List of node IDs to test against
            seed: Random seed for reproducibility

        Returns:
            TierCStabilityReport with stability scores and shadow mode results
        """
        start_time = time.time()

        if seed is not None:
            random.seed(seed)

        pattern_results: List[PatternStabilityResult] = []
        shadow_results: List[ShadowModeResult] = []

        for pattern in patterns:
            pattern_id = pattern.get("id", "unknown")
            logger.info(f"Testing stability for pattern: {pattern_id}")

            # Run stability test
            stability_result = self._run_pattern_stability(pattern, node_ids)
            pattern_results.append(stability_result)

            # Run shadow mode if enabled and secondary overlay available
            if self.enable_shadow_mode and self._shadow_overlay is not None:
                shadow_result = self._run_shadow_mode(pattern, node_ids)
                shadow_results.append(shadow_result)

        # Calculate overall metrics
        total_patterns = len(pattern_results)
        patterns_passed = sum(1 for r in pattern_results if r.passed)
        patterns_failed = total_patterns - patterns_passed
        overall_stability = (
            statistics.mean(r.stability_score for r in pattern_results)
            if pattern_results
            else 0.0
        )

        shadow_consensus_rate = (
            sum(1 for r in shadow_results if r.consensus_reached) / len(shadow_results)
            if shadow_results
            else 1.0
        )

        execution_time_ms = int((time.time() - start_time) * 1000)

        report = TierCStabilityReport(
            timestamp=datetime.now().isoformat(),
            total_patterns=total_patterns,
            patterns_passed=patterns_passed,
            patterns_failed=patterns_failed,
            overall_stability=overall_stability,
            shadow_mode_enabled=self.enable_shadow_mode,
            shadow_mode_consensus_rate=shadow_consensus_rate,
            pattern_results=pattern_results,
            shadow_mode_results=shadow_results,
            config={
                "stability_runs": self.stability_runs,
                "stability_threshold": self.stability_threshold,
                "shadow_mode_threshold": self.shadow_mode_threshold,
                "shadow_mode_enabled": self.enable_shadow_mode,
            },
            execution_time_ms=execution_time_ms,
        )

        # Persist report to .vrs/testing/tier_c_stability.yaml
        report.save()

        return report

    def _run_pattern_stability(
        self,
        pattern: Dict[str, Any],
        node_ids: List[str],
    ) -> PatternStabilityResult:
        """Run stability test for a single pattern.

        Executes N runs and computes stability as consistency of results.

        Args:
            pattern: Pattern definition with tier_c_* conditions
            node_ids: Node IDs to test against

        Returns:
            PatternStabilityResult with stability metrics
        """
        pattern_id = pattern.get("id", "unknown")
        matcher = TierCMatcher(self.overlay)

        # Extract Tier C conditions from pattern
        tier_c_all = pattern.get("tier_c_all", [])
        tier_c_any = pattern.get("tier_c_any", [])
        tier_c_none = pattern.get("tier_c_none", [])

        run_results: List[Tuple[int, Set[str]]] = []

        for run_idx in range(self.stability_runs):
            # Simulate variation by shuffling node order
            shuffled_nodes = node_ids.copy()
            random.shuffle(shuffled_nodes)

            matched_nodes: Set[str] = set()

            for node_id in shuffled_nodes:
                result = self._match_tier_c(
                    matcher, node_id, tier_c_all, tier_c_any, tier_c_none
                )
                if result.matched:
                    matched_nodes.add(node_id)

            run_results.append((len(matched_nodes), matched_nodes))

        # Calculate stability score
        findings_counts = [r[0] for r in run_results]
        mode_count = max(set(findings_counts), key=findings_counts.count)

        runs_consistent = findings_counts.count(mode_count)
        stability_score = runs_consistent / self.stability_runs

        findings_variance = (
            statistics.variance(findings_counts) if len(findings_counts) > 1 else 0.0
        )

        # Build details for debugging
        details = [
            {
                "run": i + 1,
                "findings_count": count,
                "is_consistent": count == mode_count,
            }
            for i, (count, _) in enumerate(run_results[:10])  # Keep first 10 runs
        ]

        return PatternStabilityResult(
            pattern_id=pattern_id,
            stability_score=stability_score,
            runs_total=self.stability_runs,
            runs_consistent=runs_consistent,
            findings_variance=findings_variance,
            passed=stability_score >= self.stability_threshold,
            details=details,
        )

    def _run_shadow_mode(
        self,
        pattern: Dict[str, Any],
        node_ids: List[str],
    ) -> ShadowModeResult:
        """Run shadow mode comparison between two labelers.

        Compares labels from primary and secondary overlays and computes
        overlap score. Consensus requires >= 70% label overlap.

        Args:
            pattern: Pattern definition
            node_ids: Node IDs to compare labels for

        Returns:
            ShadowModeResult with consensus metrics
        """
        pattern_id = pattern.get("id", "unknown")

        if self._shadow_overlay is None:
            return ShadowModeResult(
                pattern_id=pattern_id,
                overlap_score=1.0,
                consensus_reached=True,
                notes=["Shadow overlay not configured"],
            )

        # Collect labels from both overlays for all nodes
        labeler_a_labels: Set[str] = set()
        labeler_b_labels: Set[str] = set()

        for node_id in node_ids:
            # Primary labeler (A)
            label_set_a = self.overlay.get_labels(node_id)
            for label in label_set_a.labels:
                labeler_a_labels.add(f"{node_id}:{label.label_id}")

            # Shadow labeler (B)
            label_set_b = self._shadow_overlay.get_labels(node_id)
            for label in label_set_b.labels:
                labeler_b_labels.add(f"{node_id}:{label.label_id}")

        # Calculate overlap
        agreed_labels = labeler_a_labels & labeler_b_labels
        all_labels = labeler_a_labels | labeler_b_labels

        overlap_score = len(agreed_labels) / len(all_labels) if all_labels else 1.0
        consensus_reached = overlap_score >= self.shadow_mode_threshold

        disagreed_labels = labeler_a_labels ^ labeler_b_labels

        notes: List[str] = []
        if not consensus_reached:
            notes.append(
                f"Consensus not reached: {overlap_score:.2%} < {self.shadow_mode_threshold:.0%}"
            )
            notes.append(f"Disagreed on {len(disagreed_labels)} label assignments")

        return ShadowModeResult(
            pattern_id=pattern_id,
            overlap_score=overlap_score,
            consensus_reached=consensus_reached,
            labeler_a_labels=labeler_a_labels,
            labeler_b_labels=labeler_b_labels,
            agreed_labels=agreed_labels,
            disagreed_labels=disagreed_labels,
            notes=notes,
        )

    def _match_tier_c(
        self,
        matcher: TierCMatcher,
        node_id: str,
        tier_c_all: List[Dict[str, Any]],
        tier_c_any: List[Dict[str, Any]],
        tier_c_none: List[Dict[str, Any]],
    ) -> TierCMatch:
        """Match Tier C conditions for a node.

        Args:
            matcher: TierCMatcher instance
            node_id: Node to match
            tier_c_all: All conditions must match
            tier_c_any: At least one must match
            tier_c_none: None must match

        Returns:
            TierCMatch result
        """
        from alphaswarm_sol.queries.tier_c import TierCCondition

        all_conds = [TierCCondition.from_dict(c) for c in tier_c_all] if tier_c_all else None
        any_conds = [TierCCondition.from_dict(c) for c in tier_c_any] if tier_c_any else None
        none_conds = [TierCCondition.from_dict(c) for c in tier_c_none] if tier_c_none else None

        return matcher.match(
            node_id,
            conditions_all=all_conds,
            conditions_any=any_conds,
            conditions_none=none_conds,
        )


# =============================================================================
# Utility Functions
# =============================================================================


def run_tier_c_stability(
    overlay: LabelOverlay,
    patterns: List[Dict[str, Any]],
    node_ids: List[str],
    shadow_overlay: Optional[LabelOverlay] = None,
    runs: int = DEFAULT_STABILITY_RUNS,
    threshold: float = STABILITY_THRESHOLD,
) -> TierCStabilityReport:
    """Convenience function to run Tier C stability testing.

    Args:
        overlay: Primary label overlay
        patterns: Tier C pattern definitions
        node_ids: Node IDs to test
        shadow_overlay: Optional secondary overlay for shadow mode
        runs: Number of runs per pattern
        threshold: Stability threshold

    Returns:
        TierCStabilityReport with results
    """
    harness = TierCStabilityHarness(
        overlay=overlay,
        stability_runs=runs,
        stability_threshold=threshold,
        enable_shadow_mode=shadow_overlay is not None,
    )

    if shadow_overlay is not None:
        harness.set_shadow_overlay(shadow_overlay)

    return harness.run_stability_test(patterns, node_ids)


def load_tier_c_stability_report(
    path: Optional[Path] = None,
) -> Optional[TierCStabilityReport]:
    """Load a saved Tier C stability report.

    Args:
        path: Path to report (defaults to .vrs/testing/tier_c_stability.yaml)

    Returns:
        TierCStabilityReport if found, None otherwise
    """
    report_path = path or TIER_C_STABILITY_REPORT_PATH

    if not report_path.exists():
        return None

    with open(report_path) as f:
        data = yaml.safe_load(f)

    if data is None:
        return None

    # Reconstruct pattern results
    pattern_results = [
        PatternStabilityResult(
            pattern_id=r["pattern_id"],
            stability_score=r["stability_score"],
            runs_total=r["runs_total"],
            runs_consistent=r["runs_consistent"],
            findings_variance=r["findings_variance"],
            passed=r["passed"],
            details=r.get("details", []),
        )
        for r in data.get("pattern_results", [])
    ]

    # Reconstruct shadow mode results
    shadow_results = [
        ShadowModeResult(
            pattern_id=r["pattern_id"],
            overlap_score=r["overlap_score"],
            consensus_reached=r["consensus_reached"],
            agreed_labels=set(r.get("agreed_labels", [])),
            disagreed_labels=set(r.get("disagreed_labels", [])),
            notes=r.get("notes", []),
        )
        for r in data.get("shadow_mode_results", [])
    ]

    summary = data.get("summary", {})
    metadata = data.get("metadata", {})

    return TierCStabilityReport(
        timestamp=metadata.get("timestamp", ""),
        total_patterns=summary.get("total_patterns", 0),
        patterns_passed=summary.get("patterns_passed", 0),
        patterns_failed=summary.get("patterns_failed", 0),
        overall_stability=summary.get("overall_stability", 0.0),
        shadow_mode_enabled=summary.get("shadow_mode_enabled", False),
        shadow_mode_consensus_rate=summary.get("shadow_mode_consensus_rate", 0.0),
        pattern_results=pattern_results,
        shadow_mode_results=shadow_results,
        config=data.get("config", {}),
        execution_time_ms=metadata.get("execution_time_ms", 0),
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Constants
    "DEFAULT_STABILITY_RUNS",
    "STABILITY_THRESHOLD",
    "SHADOW_MODE_CONSENSUS_THRESHOLD",
    "TIER_C_STABILITY_REPORT_PATH",
    # Data classes
    "PatternStabilityResult",
    "ShadowModeResult",
    "TierCStabilityReport",
    # Main harness
    "TierCStabilityHarness",
    # Utility functions
    "run_tier_c_stability",
    "load_tier_c_stability_report",
]
