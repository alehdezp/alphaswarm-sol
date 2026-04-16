"""
Test Metrics for AlphaSwarm Test Forge.

Dataclasses for tracking test accuracy, model comparison, and GA gate validation.

GA Gates (per context doc):
- Precision >= 85%
- Recall (Critical) >= 95%
- Recall (High) >= 85%

Phase 7.2 Tier C Stability Gates:
- Stability >= 85%
- Shadow mode consensus >= 70%

Phase 7.2 Innovation Metrics (I4, I5, I6):
- Evidence debt tracking (blocks promotion when >25% weak evidence)
- Economic context TTL decay (30-day TTL, decays to unknown)
- Plausibility scoring (priority only, never hides findings)

Note: recall_medium and recall_low are tracked but NOT gated for GA.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.testing.quality import (
        EvidenceDebtTracker,
        PlausibilityScorer,
        ContextTTLManager,
    )


@dataclass
class CategoryMetrics:
    """Metrics for a specific vulnerability category.

    Tracks precision, recall, and confusion matrix counts
    for a single vulnerability category (e.g., reentrancy, oracle).

    Example:
        >>> reentrancy_metrics = CategoryMetrics(
        ...     precision=0.92, recall=0.88, f1_score=0.90,
        ...     tp=44, fp=4, fn=6
        ... )
    """

    precision: float
    recall: float
    f1_score: float
    tp: int  # True positives
    fp: int  # False positives
    fn: int  # False negatives

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CategoryMetrics":
        """Create from dictionary."""
        return cls(
            precision=data["precision"],
            recall=data["recall"],
            f1_score=data["f1_score"],
            tp=data["tp"],
            fp=data["fp"],
            fn=data["fn"],
        )


@dataclass
class SegmentMetrics:
    """Metrics for a corpus segment.

    Tracks accuracy for each corpus segment:
    - recent-audits: Post-2025 audit findings
    - mutations: Auto-generated variants
    - adversarial: Hand-crafted challenges
    - safe: Known safe contracts (for FP testing)

    Example:
        >>> audits_metrics = SegmentMetrics(
        ...     precision=0.87, recall=0.91,
        ...     contracts_tested=25,
        ...     findings_correct=45, findings_incorrect=7
        ... )
    """

    precision: float
    recall: float
    contracts_tested: int
    findings_correct: int
    findings_incorrect: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "precision": self.precision,
            "recall": self.recall,
            "contracts_tested": self.contracts_tested,
            "findings_correct": self.findings_correct,
            "findings_incorrect": self.findings_incorrect,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SegmentMetrics":
        """Create from dictionary."""
        return cls(
            precision=data["precision"],
            recall=data["recall"],
            contracts_tested=data["contracts_tested"],
            findings_correct=data["findings_correct"],
            findings_incorrect=data["findings_incorrect"],
        )


@dataclass
class TestMetrics:
    """Complete test metrics for a run.

    Captures all accuracy, performance, and cost data from a test run.
    Used for:
    - GA gate validation (meets_ga_gates)
    - Model comparison
    - Regression detection
    - Cost tracking

    GA Gates (checked by meets_ga_gates):
    - Precision >= 0.85 (85%)
    - Recall (Critical) >= 0.95 (95%)
    - Recall (High) >= 0.85 (85%)

    NOT gated (targets only):
    - Recall (Medium): Target 70%
    - Recall (Low): Target 70%

    Example:
        >>> metrics = TestMetrics(
        ...     precision=0.90, recall=0.88, f1_score=0.89,
        ...     recall_critical=0.98, recall_high=0.90,
        ...     recall_medium=0.75, recall_low=0.72,
        ...     execution_time_ms=5000, contracts_tested=50, patterns_tested=20
        ... )
        >>> metrics.meets_ga_gates()
        True
    """

    # Core accuracy
    precision: float
    recall: float
    f1_score: float

    # Severity-weighted recall
    recall_critical: float
    recall_high: float
    recall_medium: float
    recall_low: float

    # Performance
    execution_time_ms: int
    contracts_tested: int
    patterns_tested: int

    # Breakdown by category and segment
    by_category: Dict[str, CategoryMetrics] = field(default_factory=dict)
    by_segment: Dict[str, SegmentMetrics] = field(default_factory=dict)

    # Cost tracking (informational, not gated)
    tokens_used: int = 0
    cost_usd: float = 0.0

    # Model comparison
    model_used: str = ""
    vs_opus_accuracy: Optional[float] = None  # Percentage of Opus accuracy achieved

    # Phase 7.2 Innovation metrics (I4, I5, I6)
    innovation_metrics: Optional["InnovationMetrics"] = None

    def meets_ga_gates(self) -> bool:
        """Check if metrics meet GA quality gates.

        GA Gates (per context doc):
        - Precision >= 85%
        - Recall (Critical) >= 95%
        - Recall (High) >= 85%

        Note: recall_medium and recall_low are tracked targets,
        NOT gates. They do NOT affect this method's result.

        Returns:
            True if all GA gates pass, False otherwise
        """
        return (
            self.precision >= 0.85
            and self.recall_critical >= 0.95
            and self.recall_high >= 0.85
        )

    def get_gate_failures(self) -> Dict[str, Dict[str, float]]:
        """Get details on which GA gates failed.

        Returns:
            Dictionary mapping failed gate names to actual/required values.
            Empty dict if all gates pass.
        """
        failures: Dict[str, Dict[str, float]] = {}

        if self.precision < 0.85:
            failures["precision"] = {"actual": self.precision, "required": 0.85}
        if self.recall_critical < 0.95:
            failures["recall_critical"] = {"actual": self.recall_critical, "required": 0.95}
        if self.recall_high < 0.85:
            failures["recall_high"] = {"actual": self.recall_high, "required": 0.85}

        return failures

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization.

        Returns:
            Dictionary representation with nested structures serialized
        """
        result = {
            # Core accuracy
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            # Severity-weighted recall
            "recall_critical": self.recall_critical,
            "recall_high": self.recall_high,
            "recall_medium": self.recall_medium,
            "recall_low": self.recall_low,
            # Performance
            "execution_time_ms": self.execution_time_ms,
            "contracts_tested": self.contracts_tested,
            "patterns_tested": self.patterns_tested,
            # Breakdowns
            "by_category": {k: v.to_dict() for k, v in self.by_category.items()},
            "by_segment": {k: v.to_dict() for k, v in self.by_segment.items()},
            # Cost
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            # Model info
            "model_used": self.model_used,
            "vs_opus_accuracy": self.vs_opus_accuracy,
        }
        # Phase 7.2 innovation metrics
        if self.innovation_metrics is not None:
            result["innovation_metrics"] = self.innovation_metrics.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestMetrics":
        """Create TestMetrics from dictionary.

        Args:
            data: Dictionary with metrics data

        Returns:
            TestMetrics instance
        """
        by_category = {
            k: CategoryMetrics.from_dict(v)
            for k, v in data.get("by_category", {}).items()
        }
        by_segment = {
            k: SegmentMetrics.from_dict(v)
            for k, v in data.get("by_segment", {}).items()
        }

        # Handle innovation metrics
        innovation_metrics = None
        if "innovation_metrics" in data:
            innovation_metrics = InnovationMetrics.from_dict(data["innovation_metrics"])

        return cls(
            precision=data["precision"],
            recall=data["recall"],
            f1_score=data["f1_score"],
            recall_critical=data["recall_critical"],
            recall_high=data["recall_high"],
            recall_medium=data["recall_medium"],
            recall_low=data["recall_low"],
            execution_time_ms=data["execution_time_ms"],
            contracts_tested=data["contracts_tested"],
            patterns_tested=data["patterns_tested"],
            by_category=by_category,
            by_segment=by_segment,
            tokens_used=data.get("tokens_used", 0),
            cost_usd=data.get("cost_usd", 0.0),
            model_used=data.get("model_used", ""),
            vs_opus_accuracy=data.get("vs_opus_accuracy"),
            innovation_metrics=innovation_metrics,
        )

    def format_summary(self) -> str:
        """Format metrics as human-readable summary.

        Returns:
            Multi-line summary string
        """
        ga_status = "PASS" if self.meets_ga_gates() else "FAIL"
        failures = self.get_gate_failures()

        lines = [
            f"Test Metrics Summary (GA: {ga_status})",
            "-" * 40,
            f"Precision:       {self.precision:.1%}",
            f"Recall:          {self.recall:.1%}",
            f"F1 Score:        {self.f1_score:.1%}",
            "",
            "Severity Recall:",
            f"  Critical:      {self.recall_critical:.1%} {'(REQUIRED >= 95%)' if 'recall_critical' in failures else ''}",
            f"  High:          {self.recall_high:.1%} {'(REQUIRED >= 85%)' if 'recall_high' in failures else ''}",
            f"  Medium:        {self.recall_medium:.1%} (target: 70%)",
            f"  Low:           {self.recall_low:.1%} (target: 70%)",
            "",
            f"Contracts tested: {self.contracts_tested}",
            f"Patterns tested:  {self.patterns_tested}",
            f"Execution time:   {self.execution_time_ms}ms",
        ]

        if self.cost_usd > 0:
            lines.extend([
                "",
                f"Tokens used:     {self.tokens_used:,}",
                f"Cost:            ${self.cost_usd:.4f}",
            ])

        if self.model_used:
            lines.append(f"Model:           {self.model_used}")
            if self.vs_opus_accuracy is not None:
                lines.append(f"vs Opus:         {self.vs_opus_accuracy:.1%}")

        # Include innovation metrics if available
        if self.innovation_metrics is not None and self.innovation_metrics.has_innovation_data():
            lines.extend([
                "",
                self.innovation_metrics.format_summary(),
            ])

        return "\n".join(lines)


@dataclass
class TierCStabilityMetrics:
    """Metrics for Phase 7.2 Tier C stability testing.

    Tracks stability scores across multiple runs (N=50) and shadow mode
    consensus between dual labelers.

    Phase 7.2 Gates:
    - Stability >= 0.85 (85% consistent findings)
    - Shadow mode consensus >= 0.70 (70% label overlap)

    Example:
        >>> metrics = TierCStabilityMetrics(
        ...     overall_stability=0.92,
        ...     patterns_passed=18, patterns_failed=2,
        ...     shadow_mode_consensus=0.78
        ... )
        >>> metrics.meets_stability_gates()
        True
    """

    # Overall stability
    overall_stability: float
    patterns_passed: int
    patterns_failed: int
    total_patterns: int = 0

    # Shadow mode metrics
    shadow_mode_enabled: bool = False
    shadow_mode_consensus: float = 1.0
    shadow_disagreements: List[str] = field(default_factory=list)

    # Per-pattern breakdown
    pattern_scores: Dict[str, float] = field(default_factory=dict)

    # Performance
    stability_runs_per_pattern: int = 50
    execution_time_ms: int = 0

    # Thresholds (for reference)
    stability_threshold: float = 0.85
    shadow_mode_threshold: float = 0.70

    def __post_init__(self):
        """Set total_patterns if not provided."""
        if self.total_patterns == 0:
            self.total_patterns = self.patterns_passed + self.patterns_failed

    def meets_stability_gates(self) -> bool:
        """Check if metrics meet Phase 7.2 stability gates.

        Gates:
        - Overall stability >= 0.85 (85%)
        - If shadow mode enabled: consensus >= 0.70 (70%)

        Returns:
            True if all stability gates pass, False otherwise
        """
        stability_passed = self.overall_stability >= self.stability_threshold

        if self.shadow_mode_enabled:
            shadow_passed = self.shadow_mode_consensus >= self.shadow_mode_threshold
            return stability_passed and shadow_passed

        return stability_passed

    def get_stability_failures(self) -> Dict[str, Dict[str, float]]:
        """Get details on which stability gates failed.

        Returns:
            Dictionary mapping failed gate names to actual/required values.
            Empty dict if all gates pass.
        """
        failures: Dict[str, Dict[str, float]] = {}

        if self.overall_stability < self.stability_threshold:
            failures["overall_stability"] = {
                "actual": self.overall_stability,
                "required": self.stability_threshold,
            }

        if self.shadow_mode_enabled and self.shadow_mode_consensus < self.shadow_mode_threshold:
            failures["shadow_mode_consensus"] = {
                "actual": self.shadow_mode_consensus,
                "required": self.shadow_mode_threshold,
            }

        return failures

    def get_unstable_patterns(self) -> List[str]:
        """Get list of patterns that failed stability threshold.

        Returns:
            List of pattern IDs with stability < threshold
        """
        return [
            pid for pid, score in self.pattern_scores.items()
            if score < self.stability_threshold
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization.

        Returns:
            Dictionary representation
        """
        return {
            "overall_stability": self.overall_stability,
            "patterns_passed": self.patterns_passed,
            "patterns_failed": self.patterns_failed,
            "total_patterns": self.total_patterns,
            "shadow_mode_enabled": self.shadow_mode_enabled,
            "shadow_mode_consensus": self.shadow_mode_consensus,
            "shadow_disagreements": self.shadow_disagreements,
            "pattern_scores": self.pattern_scores,
            "stability_runs_per_pattern": self.stability_runs_per_pattern,
            "execution_time_ms": self.execution_time_ms,
            "stability_threshold": self.stability_threshold,
            "shadow_mode_threshold": self.shadow_mode_threshold,
            "gates_passed": self.meets_stability_gates(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TierCStabilityMetrics":
        """Create TierCStabilityMetrics from dictionary.

        Args:
            data: Dictionary with metrics data

        Returns:
            TierCStabilityMetrics instance
        """
        return cls(
            overall_stability=data["overall_stability"],
            patterns_passed=data["patterns_passed"],
            patterns_failed=data["patterns_failed"],
            total_patterns=data.get("total_patterns", 0),
            shadow_mode_enabled=data.get("shadow_mode_enabled", False),
            shadow_mode_consensus=data.get("shadow_mode_consensus", 1.0),
            shadow_disagreements=data.get("shadow_disagreements", []),
            pattern_scores=data.get("pattern_scores", {}),
            stability_runs_per_pattern=data.get("stability_runs_per_pattern", 50),
            execution_time_ms=data.get("execution_time_ms", 0),
            stability_threshold=data.get("stability_threshold", 0.85),
            shadow_mode_threshold=data.get("shadow_mode_threshold", 0.70),
        )

    @classmethod
    def from_stability_report(cls, report: Any) -> "TierCStabilityMetrics":
        """Create from TierCStabilityReport.

        Args:
            report: TierCStabilityReport instance

        Returns:
            TierCStabilityMetrics instance
        """
        pattern_scores = {
            r.pattern_id: r.stability_score
            for r in report.pattern_results
        }

        shadow_disagreements = []
        if report.shadow_mode_results:
            for sr in report.shadow_mode_results:
                if not sr.consensus_reached:
                    shadow_disagreements.extend(sr.notes)

        return cls(
            overall_stability=report.overall_stability,
            patterns_passed=report.patterns_passed,
            patterns_failed=report.patterns_failed,
            total_patterns=report.total_patterns,
            shadow_mode_enabled=report.shadow_mode_enabled,
            shadow_mode_consensus=report.shadow_mode_consensus_rate,
            shadow_disagreements=shadow_disagreements,
            pattern_scores=pattern_scores,
            stability_runs_per_pattern=report.config.get("stability_runs", 50),
            execution_time_ms=report.execution_time_ms,
            stability_threshold=report.config.get("stability_threshold", 0.85),
            shadow_mode_threshold=report.config.get("shadow_mode_threshold", 0.70),
        )

    def format_summary(self) -> str:
        """Format metrics as human-readable summary.

        Returns:
            Multi-line summary string
        """
        status = "PASS" if self.meets_stability_gates() else "FAIL"
        failures = self.get_stability_failures()

        lines = [
            f"Tier C Stability Metrics (Status: {status})",
            "-" * 40,
            f"Overall Stability: {self.overall_stability:.1%} "
            f"{'(REQUIRED >= 85%)' if 'overall_stability' in failures else ''}",
            f"Patterns Passed:   {self.patterns_passed}/{self.total_patterns}",
            f"Patterns Failed:   {self.patterns_failed}",
            "",
        ]

        if self.shadow_mode_enabled:
            lines.extend([
                "Shadow Mode:",
                f"  Consensus:     {self.shadow_mode_consensus:.1%} "
                f"{'(REQUIRED >= 70%)' if 'shadow_mode_consensus' in failures else ''}",
                f"  Disagreements: {len(self.shadow_disagreements)}",
                "",
            ])

        lines.extend([
            f"Runs per pattern: {self.stability_runs_per_pattern}",
            f"Execution time:   {self.execution_time_ms}ms",
        ])

        unstable = self.get_unstable_patterns()
        if unstable:
            lines.extend([
                "",
                f"Unstable patterns ({len(unstable)}):",
            ])
            for pid in unstable[:5]:
                score = self.pattern_scores.get(pid, 0)
                lines.append(f"  - {pid}: {score:.1%}")
            if len(unstable) > 5:
                lines.append(f"  ... and {len(unstable) - 5} more")

        return "\n".join(lines)


# =============================================================================
# Phase 7.2 Innovation Metrics (I4, I5, I6)
# =============================================================================

@dataclass
class InnovationMetrics:
    """Phase 7.2 Innovation metrics summary.

    Combines evidence debt (I4), context TTL (I5), and plausibility (I6)
    metrics for inclusion in test run summaries.

    Key principles:
    - Evidence debt blocks pattern PROMOTION, not findings
    - TTL decay sets status to "unknown", NEVER "safe"
    - Plausibility scores PRIORITIZE, never suppress
    """

    # Evidence Debt (I4)
    evidence_debt_enabled: bool = False
    patterns_with_debt: int = 0
    blocked_patterns: List[str] = field(default_factory=list)
    overall_weak_evidence_ratio: float = 0.0
    evidence_debt_threshold: float = 0.25

    # Context TTL (I5)
    context_ttl_enabled: bool = False
    total_context_fields: int = 0
    active_context_fields: int = 0
    expired_context_fields: int = 0
    decay_events: int = 0
    ttl_days: int = 30

    # Plausibility (I6)
    plausibility_enabled: bool = False
    total_scored_findings: int = 0
    avg_plausibility_score: float = 0.0
    by_priority_tier: Dict[str, int] = field(default_factory=dict)

    def has_innovation_data(self) -> bool:
        """Check if any innovation metrics are populated."""
        return (
            self.evidence_debt_enabled or
            self.context_ttl_enabled or
            self.plausibility_enabled
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "evidence_debt": {
                "enabled": self.evidence_debt_enabled,
                "patterns_with_debt": self.patterns_with_debt,
                "blocked_patterns": self.blocked_patterns,
                "overall_weak_evidence_ratio": round(self.overall_weak_evidence_ratio, 3),
                "threshold": self.evidence_debt_threshold,
            },
            "context_ttl": {
                "enabled": self.context_ttl_enabled,
                "total_fields": self.total_context_fields,
                "active_fields": self.active_context_fields,
                "expired_fields": self.expired_context_fields,
                "decay_events": self.decay_events,
                "ttl_days": self.ttl_days,
            },
            "plausibility": {
                "enabled": self.plausibility_enabled,
                "total_scored": self.total_scored_findings,
                "avg_score": round(self.avg_plausibility_score, 3),
                "by_priority_tier": self.by_priority_tier,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InnovationMetrics":
        """Create from dictionary."""
        debt = data.get("evidence_debt", {})
        ttl = data.get("context_ttl", {})
        plaus = data.get("plausibility", {})

        return cls(
            evidence_debt_enabled=debt.get("enabled", False),
            patterns_with_debt=debt.get("patterns_with_debt", 0),
            blocked_patterns=debt.get("blocked_patterns", []),
            overall_weak_evidence_ratio=debt.get("overall_weak_evidence_ratio", 0.0),
            evidence_debt_threshold=debt.get("threshold", 0.25),
            context_ttl_enabled=ttl.get("enabled", False),
            total_context_fields=ttl.get("total_fields", 0),
            active_context_fields=ttl.get("active_fields", 0),
            expired_context_fields=ttl.get("expired_fields", 0),
            decay_events=ttl.get("decay_events", 0),
            ttl_days=ttl.get("ttl_days", 30),
            plausibility_enabled=plaus.get("enabled", False),
            total_scored_findings=plaus.get("total_scored", 0),
            avg_plausibility_score=plaus.get("avg_score", 0.0),
            by_priority_tier=plaus.get("by_priority_tier", {}),
        )

    @classmethod
    def from_trackers(
        cls,
        evidence_tracker: Optional["EvidenceDebtTracker"] = None,
        ttl_manager: Optional["ContextTTLManager"] = None,
        plausibility_scorer: Optional["PlausibilityScorer"] = None,
    ) -> "InnovationMetrics":
        """Create metrics from tracker instances.

        Args:
            evidence_tracker: Optional EvidenceDebtTracker
            ttl_manager: Optional ContextTTLManager
            plausibility_scorer: Optional PlausibilityScorer

        Returns:
            InnovationMetrics populated from trackers
        """
        metrics = cls()

        if evidence_tracker is not None:
            summary = evidence_tracker.get_summary()
            metrics.evidence_debt_enabled = True
            metrics.patterns_with_debt = summary.get("patterns_with_debt", 0)
            metrics.blocked_patterns = summary.get("blocked_patterns", [])
            metrics.overall_weak_evidence_ratio = summary.get("overall_weak_ratio", 0.0)
            metrics.evidence_debt_threshold = evidence_tracker.DEBT_THRESHOLD

        if ttl_manager is not None:
            summary = ttl_manager.get_summary()
            metrics.context_ttl_enabled = True
            metrics.total_context_fields = summary.get("total_fields", 0)
            metrics.active_context_fields = summary.get("active_fields", 0)
            metrics.expired_context_fields = summary.get("expired_fields", 0)
            metrics.decay_events = summary.get("decay_events", 0)
            metrics.ttl_days = ttl_manager.DEFAULT_TTL_DAYS

        if plausibility_scorer is not None:
            summary = plausibility_scorer.get_summary()
            metrics.plausibility_enabled = True
            metrics.total_scored_findings = summary.get("total_scored", 0)
            metrics.avg_plausibility_score = summary.get("avg_score", 0.0)
            metrics.by_priority_tier = summary.get("by_priority_tier", {})

        return metrics

    def format_summary(self) -> str:
        """Format innovation metrics as human-readable summary.

        Returns:
            Multi-line summary string
        """
        if not self.has_innovation_data():
            return "Innovation Metrics: Not enabled"

        lines = [
            "Phase 7.2 Innovation Metrics",
            "-" * 40,
        ]

        if self.evidence_debt_enabled:
            debt_status = "BLOCKED" if self.blocked_patterns else "OK"
            lines.extend([
                "",
                f"Evidence Debt (I4): {debt_status}",
                f"  Patterns with debt: {self.patterns_with_debt}",
                f"  Weak evidence ratio: {self.overall_weak_evidence_ratio:.1%}",
                f"  Threshold: {self.evidence_debt_threshold:.0%}",
            ])
            if self.blocked_patterns:
                lines.append(f"  Blocked patterns: {', '.join(self.blocked_patterns[:5])}")
                if len(self.blocked_patterns) > 5:
                    lines.append(f"    ... and {len(self.blocked_patterns) - 5} more")

        if self.context_ttl_enabled:
            ttl_status = "STALE" if self.expired_context_fields > 0 else "FRESH"
            lines.extend([
                "",
                f"Context TTL (I5): {ttl_status}",
                f"  Active fields: {self.active_context_fields}/{self.total_context_fields}",
                f"  Expired fields: {self.expired_context_fields}",
                f"  Decay events: {self.decay_events}",
                f"  TTL: {self.ttl_days} days",
            ])

        if self.plausibility_enabled:
            lines.extend([
                "",
                f"Plausibility (I6): PRIORITIZATION ONLY",
                f"  Scored findings: {self.total_scored_findings}",
                f"  Avg score: {self.avg_plausibility_score:.1%}",
            ])
            if self.by_priority_tier:
                tiers = ", ".join(f"{t}:{c}" for t, c in sorted(self.by_priority_tier.items()))
                lines.append(f"  By tier: {tiers}")

        return "\n".join(lines)
