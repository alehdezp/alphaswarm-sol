"""Batch Quality Metrics Tests (05.10-11)

Tests for batch discovery quality metrics per PCONTEXT-11:
1. Precision/recall deltas for batch vs sequential
2. Novelty yield measurement
3. Evidence entropy calculation
4. Quality regression detection

These tests ensure batch discovery improves results without regression.
"""

from __future__ import annotations

import json
import math
import unittest
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums and Constants
# =============================================================================


class DiscoveryMode(str, Enum):
    """Discovery execution mode."""

    SEQUENTIAL = "sequential"
    BATCH = "batch"


class QualityLevel(str, Enum):
    """Quality assessment level."""

    EXCELLENT = "excellent"  # P/R >= 0.90
    GOOD = "good"           # P/R >= 0.75
    ACCEPTABLE = "acceptable"  # P/R >= 0.60
    POOR = "poor"           # P/R < 0.60


# Thresholds for quality metrics
PRECISION_REGRESSION_THRESHOLD = 0.05  # Max allowed precision drop
RECALL_REGRESSION_THRESHOLD = 0.05     # Max allowed recall drop
NOVELTY_MIN_THRESHOLD = 0.10           # Min novelty yield required
ENTROPY_MIN_THRESHOLD = 0.30           # Min evidence entropy required


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class DiscoveryFinding:
    """A single discovery finding with metadata."""

    finding_id: str
    pattern_id: str
    confidence: float
    evidence_refs: List[str]
    is_true_positive: bool = True
    discovery_mode: DiscoveryMode = DiscoveryMode.SEQUENTIAL
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "finding_id": self.finding_id,
            "pattern_id": self.pattern_id,
            "confidence": self.confidence,
            "evidence_refs": self.evidence_refs,
            "is_true_positive": self.is_true_positive,
            "discovery_mode": self.discovery_mode.value,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class QualityMetrics:
    """Quality metrics for a discovery run."""

    precision: float
    recall: float
    f1_score: float
    true_positives: int
    false_positives: int
    false_negatives: int
    total_findings: int
    mode: DiscoveryMode

    @classmethod
    def compute(
        cls,
        findings: List[DiscoveryFinding],
        ground_truth_positives: int,
        mode: DiscoveryMode,
    ) -> "QualityMetrics":
        """Compute metrics from findings and ground truth.

        Args:
            findings: List of discovery findings
            ground_truth_positives: Number of actual vulnerabilities
            mode: Discovery mode used

        Returns:
            QualityMetrics with computed values
        """
        tp = sum(1 for f in findings if f.is_true_positive)
        fp = len(findings) - tp
        fn = max(0, ground_truth_positives - tp)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / ground_truth_positives if ground_truth_positives > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return cls(
            precision=precision,
            recall=recall,
            f1_score=f1,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            total_findings=len(findings),
            mode=mode,
        )

    def quality_level(self) -> QualityLevel:
        """Determine quality level based on metrics."""
        avg_pr = (self.precision + self.recall) / 2
        if avg_pr >= 0.90:
            return QualityLevel.EXCELLENT
        elif avg_pr >= 0.75:
            return QualityLevel.GOOD
        elif avg_pr >= 0.60:
            return QualityLevel.ACCEPTABLE
        return QualityLevel.POOR

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "total_findings": self.total_findings,
            "mode": self.mode.value,
            "quality_level": self.quality_level().value,
        }


@dataclass
class QualityDelta:
    """Delta between batch and sequential quality metrics."""

    precision_delta: float  # Batch - Sequential
    recall_delta: float
    f1_delta: float
    batch_metrics: QualityMetrics
    sequential_metrics: QualityMetrics

    @classmethod
    def compute(
        cls,
        batch_metrics: QualityMetrics,
        sequential_metrics: QualityMetrics,
    ) -> "QualityDelta":
        """Compute delta between batch and sequential metrics."""
        return cls(
            precision_delta=batch_metrics.precision - sequential_metrics.precision,
            recall_delta=batch_metrics.recall - sequential_metrics.recall,
            f1_delta=batch_metrics.f1_score - sequential_metrics.f1_score,
            batch_metrics=batch_metrics,
            sequential_metrics=sequential_metrics,
        )

    def has_precision_regression(self) -> bool:
        """Check if batch has precision regression beyond threshold."""
        return self.precision_delta < -PRECISION_REGRESSION_THRESHOLD

    def has_recall_regression(self) -> bool:
        """Check if batch has recall regression beyond threshold."""
        return self.recall_delta < -RECALL_REGRESSION_THRESHOLD

    def has_any_regression(self) -> bool:
        """Check if batch has any significant regression."""
        return self.has_precision_regression() or self.has_recall_regression()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "precision_delta": round(self.precision_delta, 4),
            "recall_delta": round(self.recall_delta, 4),
            "f1_delta": round(self.f1_delta, 4),
            "has_regression": self.has_any_regression(),
            "batch_metrics": self.batch_metrics.to_dict(),
            "sequential_metrics": self.sequential_metrics.to_dict(),
        }


@dataclass
class NoveltyMetrics:
    """Novelty yield metrics for batch discovery."""

    unique_patterns_found: int
    total_patterns_checked: int
    novel_evidence_refs: int
    total_evidence_refs: int
    novelty_yield: float  # Novel findings / Total findings
    evidence_novelty: float  # Novel evidence / Total evidence

    @classmethod
    def compute(
        cls,
        batch_findings: List[DiscoveryFinding],
        prior_findings: Optional[List[DiscoveryFinding]] = None,
        total_patterns: int = 100,
    ) -> "NoveltyMetrics":
        """Compute novelty metrics.

        Args:
            batch_findings: Findings from batch discovery
            prior_findings: Optional prior findings to compare against
            total_patterns: Total patterns checked

        Returns:
            NoveltyMetrics
        """
        prior_findings = prior_findings or []

        # Patterns found
        prior_patterns = {f.pattern_id for f in prior_findings}
        batch_patterns = {f.pattern_id for f in batch_findings}
        novel_patterns = batch_patterns - prior_patterns

        # Evidence refs found
        prior_evidence = set()
        for f in prior_findings:
            prior_evidence.update(f.evidence_refs)

        batch_evidence = set()
        for f in batch_findings:
            batch_evidence.update(f.evidence_refs)

        novel_evidence = batch_evidence - prior_evidence

        # Compute yields
        novelty_yield = len(novel_patterns) / len(batch_patterns) if batch_patterns else 0.0
        evidence_novelty = len(novel_evidence) / len(batch_evidence) if batch_evidence else 0.0

        return cls(
            unique_patterns_found=len(batch_patterns),
            total_patterns_checked=total_patterns,
            novel_evidence_refs=len(novel_evidence),
            total_evidence_refs=len(batch_evidence),
            novelty_yield=novelty_yield,
            evidence_novelty=evidence_novelty,
        )

    def meets_threshold(self) -> bool:
        """Check if novelty meets minimum threshold."""
        return self.novelty_yield >= NOVELTY_MIN_THRESHOLD

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "unique_patterns_found": self.unique_patterns_found,
            "total_patterns_checked": self.total_patterns_checked,
            "novel_evidence_refs": self.novel_evidence_refs,
            "total_evidence_refs": self.total_evidence_refs,
            "novelty_yield": round(self.novelty_yield, 4),
            "evidence_novelty": round(self.evidence_novelty, 4),
            "meets_threshold": self.meets_threshold(),
        }


@dataclass
class EntropyMetrics:
    """Evidence entropy metrics for discovery diversity."""

    evidence_entropy: float  # Shannon entropy of evidence distribution
    pattern_entropy: float   # Shannon entropy of pattern distribution
    normalized_entropy: float  # Entropy / Max possible entropy
    evidence_counts: Dict[str, int]

    @classmethod
    def compute(cls, findings: List[DiscoveryFinding]) -> "EntropyMetrics":
        """Compute entropy metrics from findings.

        Higher entropy = more diverse evidence/patterns used.
        Lower entropy = findings rely on same evidence repeatedly.

        Args:
            findings: List of discovery findings

        Returns:
            EntropyMetrics
        """
        if not findings:
            return cls(
                evidence_entropy=0.0,
                pattern_entropy=0.0,
                normalized_entropy=0.0,
                evidence_counts={},
            )

        # Count evidence refs
        evidence_counts: Counter[str] = Counter()
        for f in findings:
            for ref in f.evidence_refs:
                evidence_counts[ref] += 1

        # Count patterns
        pattern_counts: Counter[str] = Counter()
        for f in findings:
            pattern_counts[f.pattern_id] += 1

        # Compute Shannon entropy for evidence
        total_evidence = sum(evidence_counts.values())
        if total_evidence > 0:
            evidence_entropy = -sum(
                (c / total_evidence) * math.log2(c / total_evidence)
                for c in evidence_counts.values()
                if c > 0
            )
        else:
            evidence_entropy = 0.0

        # Compute Shannon entropy for patterns
        total_patterns = sum(pattern_counts.values())
        if total_patterns > 0:
            pattern_entropy = -sum(
                (c / total_patterns) * math.log2(c / total_patterns)
                for c in pattern_counts.values()
                if c > 0
            )
        else:
            pattern_entropy = 0.0

        # Normalize (max entropy = log2(n) where n is number of unique items)
        n_evidence = len(evidence_counts)
        max_evidence_entropy = math.log2(n_evidence) if n_evidence > 1 else 1.0
        normalized = evidence_entropy / max_evidence_entropy if max_evidence_entropy > 0 else 0.0

        return cls(
            evidence_entropy=evidence_entropy,
            pattern_entropy=pattern_entropy,
            normalized_entropy=normalized,
            evidence_counts=dict(evidence_counts),
        )

    def meets_threshold(self) -> bool:
        """Check if entropy meets minimum threshold."""
        return self.normalized_entropy >= ENTROPY_MIN_THRESHOLD

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "evidence_entropy": round(self.evidence_entropy, 4),
            "pattern_entropy": round(self.pattern_entropy, 4),
            "normalized_entropy": round(self.normalized_entropy, 4),
            "meets_threshold": self.meets_threshold(),
            "evidence_counts": self.evidence_counts,
        }


@dataclass
class BatchQualitySuite:
    """Complete batch quality metrics suite."""

    quality_delta: QualityDelta
    novelty_metrics: NoveltyMetrics
    entropy_metrics: EntropyMetrics

    def passes_regression_check(self) -> bool:
        """Check if batch passes all regression checks."""
        return (
            not self.quality_delta.has_any_regression()
            and self.novelty_metrics.meets_threshold()
            and self.entropy_metrics.meets_threshold()
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "passes_regression_check": self.passes_regression_check(),
            "quality_delta": self.quality_delta.to_dict(),
            "novelty_metrics": self.novelty_metrics.to_dict(),
            "entropy_metrics": self.entropy_metrics.to_dict(),
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


# =============================================================================
# Test Cases
# =============================================================================


class TestQualityMetrics(unittest.TestCase):
    """Tests for QualityMetrics computation."""

    def test_perfect_precision_recall(self):
        """Perfect P/R should be 1.0."""
        findings = [
            DiscoveryFinding(f"F-{i}", f"P-{i}", 0.9, [f"EVD-{i}"], is_true_positive=True)
            for i in range(10)
        ]

        metrics = QualityMetrics.compute(findings, ground_truth_positives=10, mode=DiscoveryMode.BATCH)

        self.assertEqual(metrics.precision, 1.0)
        self.assertEqual(metrics.recall, 1.0)
        self.assertEqual(metrics.f1_score, 1.0)
        self.assertEqual(metrics.quality_level(), QualityLevel.EXCELLENT)

    def test_precision_with_false_positives(self):
        """Precision should account for FPs."""
        findings = [
            DiscoveryFinding("F-1", "P-1", 0.9, ["EVD-1"], is_true_positive=True),
            DiscoveryFinding("F-2", "P-2", 0.8, ["EVD-2"], is_true_positive=True),
            DiscoveryFinding("F-3", "P-3", 0.7, ["EVD-3"], is_true_positive=False),  # FP
            DiscoveryFinding("F-4", "P-4", 0.6, ["EVD-4"], is_true_positive=False),  # FP
        ]

        metrics = QualityMetrics.compute(findings, ground_truth_positives=2, mode=DiscoveryMode.BATCH)

        self.assertEqual(metrics.true_positives, 2)
        self.assertEqual(metrics.false_positives, 2)
        self.assertEqual(metrics.precision, 0.5)
        self.assertEqual(metrics.recall, 1.0)

    def test_recall_with_false_negatives(self):
        """Recall should account for FNs."""
        findings = [
            DiscoveryFinding("F-1", "P-1", 0.9, ["EVD-1"], is_true_positive=True),
            DiscoveryFinding("F-2", "P-2", 0.8, ["EVD-2"], is_true_positive=True),
        ]

        # Ground truth has 4 positives, we only found 2
        metrics = QualityMetrics.compute(findings, ground_truth_positives=4, mode=DiscoveryMode.BATCH)

        self.assertEqual(metrics.recall, 0.5)
        self.assertEqual(metrics.false_negatives, 2)

    def test_f1_score_calculation(self):
        """F1 should be harmonic mean of P and R."""
        findings = [
            DiscoveryFinding("F-1", "P-1", 0.9, ["EVD-1"], is_true_positive=True),
            DiscoveryFinding("F-2", "P-2", 0.8, ["EVD-2"], is_true_positive=False),
        ]

        # P = 0.5, R = 0.5 (1 TP out of 2 ground truth)
        metrics = QualityMetrics.compute(findings, ground_truth_positives=2, mode=DiscoveryMode.BATCH)

        expected_f1 = 2 * 0.5 * 0.5 / (0.5 + 0.5)  # = 0.5
        self.assertEqual(metrics.f1_score, expected_f1)

    def test_empty_findings(self):
        """Empty findings should result in zero metrics."""
        metrics = QualityMetrics.compute([], ground_truth_positives=10, mode=DiscoveryMode.BATCH)

        self.assertEqual(metrics.precision, 0.0)
        self.assertEqual(metrics.recall, 0.0)
        self.assertEqual(metrics.f1_score, 0.0)
        self.assertEqual(metrics.quality_level(), QualityLevel.POOR)

    def test_quality_level_thresholds(self):
        """Quality levels should match thresholds."""
        # EXCELLENT: P/R avg >= 0.90
        excellent = QualityMetrics(0.92, 0.90, 0.91, 9, 1, 1, 10, DiscoveryMode.BATCH)
        self.assertEqual(excellent.quality_level(), QualityLevel.EXCELLENT)

        # GOOD: P/R avg >= 0.75
        good = QualityMetrics(0.80, 0.75, 0.77, 8, 2, 2, 10, DiscoveryMode.BATCH)
        self.assertEqual(good.quality_level(), QualityLevel.GOOD)

        # ACCEPTABLE: P/R avg >= 0.60
        acceptable = QualityMetrics(0.65, 0.60, 0.62, 6, 4, 4, 10, DiscoveryMode.BATCH)
        self.assertEqual(acceptable.quality_level(), QualityLevel.ACCEPTABLE)

        # POOR: P/R avg < 0.60
        poor = QualityMetrics(0.40, 0.50, 0.44, 4, 6, 5, 10, DiscoveryMode.BATCH)
        self.assertEqual(poor.quality_level(), QualityLevel.POOR)


class TestQualityDelta(unittest.TestCase):
    """Tests for batch vs sequential quality deltas."""

    def test_positive_delta_no_regression(self):
        """Positive delta should indicate improvement."""
        seq = QualityMetrics(0.70, 0.65, 0.67, 7, 3, 3, 10, DiscoveryMode.SEQUENTIAL)
        batch = QualityMetrics(0.80, 0.75, 0.77, 8, 2, 2, 10, DiscoveryMode.BATCH)

        delta = QualityDelta.compute(batch, seq)

        self.assertAlmostEqual(delta.precision_delta, 0.10, places=4)
        self.assertAlmostEqual(delta.recall_delta, 0.10, places=4)
        self.assertFalse(delta.has_any_regression())

    def test_precision_regression_detected(self):
        """Precision regression beyond threshold should be detected."""
        seq = QualityMetrics(0.80, 0.75, 0.77, 8, 2, 2, 10, DiscoveryMode.SEQUENTIAL)
        batch = QualityMetrics(0.70, 0.80, 0.74, 7, 3, 2, 10, DiscoveryMode.BATCH)  # P dropped 0.10

        delta = QualityDelta.compute(batch, seq)

        self.assertAlmostEqual(delta.precision_delta, -0.10, places=4)
        self.assertTrue(delta.has_precision_regression())
        self.assertTrue(delta.has_any_regression())

    def test_recall_regression_detected(self):
        """Recall regression beyond threshold should be detected."""
        seq = QualityMetrics(0.75, 0.80, 0.77, 8, 2, 2, 10, DiscoveryMode.SEQUENTIAL)
        batch = QualityMetrics(0.80, 0.68, 0.73, 6, 1, 3, 7, DiscoveryMode.BATCH)  # R dropped 0.12

        delta = QualityDelta.compute(batch, seq)

        self.assertAlmostEqual(delta.recall_delta, -0.12, places=4)
        self.assertTrue(delta.has_recall_regression())
        self.assertTrue(delta.has_any_regression())

    def test_small_delta_no_regression(self):
        """Small negative delta within threshold should not be regression."""
        seq = QualityMetrics(0.80, 0.80, 0.80, 8, 2, 2, 10, DiscoveryMode.SEQUENTIAL)
        batch = QualityMetrics(0.78, 0.77, 0.775, 7, 2, 3, 9, DiscoveryMode.BATCH)  # Small drops

        delta = QualityDelta.compute(batch, seq)

        self.assertFalse(delta.has_precision_regression())  # -0.02 < threshold
        self.assertFalse(delta.has_recall_regression())     # -0.03 < threshold
        self.assertFalse(delta.has_any_regression())


class TestNoveltyMetrics(unittest.TestCase):
    """Tests for novelty yield metrics."""

    def test_full_novelty_no_prior(self):
        """Full novelty when no prior findings."""
        batch_findings = [
            DiscoveryFinding("F-1", "P-1", 0.9, ["EVD-1", "EVD-2"]),
            DiscoveryFinding("F-2", "P-2", 0.8, ["EVD-3"]),
        ]

        metrics = NoveltyMetrics.compute(batch_findings, prior_findings=None)

        self.assertEqual(metrics.unique_patterns_found, 2)
        self.assertEqual(metrics.novelty_yield, 1.0)
        self.assertEqual(metrics.novel_evidence_refs, 3)
        self.assertTrue(metrics.meets_threshold())

    def test_partial_novelty_with_prior(self):
        """Partial novelty when some patterns overlap with prior."""
        prior = [
            DiscoveryFinding("P-1", "pattern-a", 0.8, ["EVD-1"]),
        ]
        batch = [
            DiscoveryFinding("F-1", "pattern-a", 0.9, ["EVD-1"]),  # Same pattern
            DiscoveryFinding("F-2", "pattern-b", 0.8, ["EVD-2"]),  # Novel
            DiscoveryFinding("F-3", "pattern-c", 0.7, ["EVD-3"]),  # Novel
        ]

        metrics = NoveltyMetrics.compute(batch, prior_findings=prior)

        # 2 novel patterns out of 3 total
        self.assertEqual(metrics.unique_patterns_found, 3)
        self.assertAlmostEqual(metrics.novelty_yield, 2/3, places=4)

        # 2 novel evidence refs out of 3 total
        self.assertEqual(metrics.novel_evidence_refs, 2)
        self.assertTrue(metrics.meets_threshold())

    def test_zero_novelty(self):
        """Zero novelty when all patterns overlap."""
        prior = [
            DiscoveryFinding("P-1", "pattern-a", 0.8, ["EVD-1"]),
            DiscoveryFinding("P-2", "pattern-b", 0.7, ["EVD-2"]),
        ]
        batch = [
            DiscoveryFinding("F-1", "pattern-a", 0.9, ["EVD-1"]),
            DiscoveryFinding("F-2", "pattern-b", 0.85, ["EVD-2"]),
        ]

        metrics = NoveltyMetrics.compute(batch, prior_findings=prior)

        self.assertEqual(metrics.novelty_yield, 0.0)
        self.assertEqual(metrics.novel_evidence_refs, 0)
        self.assertFalse(metrics.meets_threshold())

    def test_empty_batch(self):
        """Empty batch should have zero novelty."""
        metrics = NoveltyMetrics.compute([])

        self.assertEqual(metrics.unique_patterns_found, 0)
        self.assertEqual(metrics.novelty_yield, 0.0)
        self.assertFalse(metrics.meets_threshold())


class TestEntropyMetrics(unittest.TestCase):
    """Tests for evidence entropy metrics."""

    def test_high_entropy_diverse_evidence(self):
        """High entropy when evidence is diverse."""
        # Each finding uses different evidence
        findings = [
            DiscoveryFinding(f"F-{i}", f"P-{i}", 0.9, [f"EVD-{i}"])
            for i in range(10)
        ]

        metrics = EntropyMetrics.compute(findings)

        # Should have high entropy (each evidence used once)
        self.assertGreater(metrics.evidence_entropy, 3.0)  # log2(10) = 3.32
        self.assertAlmostEqual(metrics.normalized_entropy, 1.0, places=2)
        self.assertTrue(metrics.meets_threshold())

    def test_low_entropy_repeated_evidence(self):
        """Low entropy when same evidence repeated."""
        # All findings use same evidence
        findings = [
            DiscoveryFinding(f"F-{i}", f"P-{i}", 0.9, ["EVD-SAME"])
            for i in range(10)
        ]

        metrics = EntropyMetrics.compute(findings)

        # Single evidence = zero entropy
        self.assertEqual(metrics.evidence_entropy, 0.0)
        self.assertEqual(metrics.normalized_entropy, 0.0)
        self.assertFalse(metrics.meets_threshold())

    def test_medium_entropy(self):
        """Medium entropy with some diversity."""
        findings = [
            DiscoveryFinding("F-1", "P-1", 0.9, ["EVD-A", "EVD-A"]),
            DiscoveryFinding("F-2", "P-2", 0.9, ["EVD-A", "EVD-B"]),
            DiscoveryFinding("F-3", "P-3", 0.9, ["EVD-B", "EVD-C"]),
            DiscoveryFinding("F-4", "P-4", 0.9, ["EVD-C", "EVD-C"]),
        ]

        metrics = EntropyMetrics.compute(findings)

        # EVD-A: 3, EVD-B: 2, EVD-C: 3 = some diversity
        self.assertGreater(metrics.evidence_entropy, 1.0)
        self.assertGreater(metrics.normalized_entropy, 0.3)
        self.assertTrue(metrics.meets_threshold())

    def test_empty_findings(self):
        """Empty findings should have zero entropy."""
        metrics = EntropyMetrics.compute([])

        self.assertEqual(metrics.evidence_entropy, 0.0)
        self.assertEqual(metrics.pattern_entropy, 0.0)
        self.assertEqual(metrics.normalized_entropy, 0.0)


class TestBatchQualitySuite(unittest.TestCase):
    """Tests for complete batch quality suite."""

    def _create_findings(
        self,
        count: int,
        tp_rate: float,
        mode: DiscoveryMode,
        pattern_prefix: str = "P",
    ) -> List[DiscoveryFinding]:
        """Create test findings.

        Args:
            count: Number of findings
            tp_rate: Fraction of true positives
            mode: Discovery mode
            pattern_prefix: Prefix for pattern IDs (use different prefixes for novelty)
        """
        findings = []
        tp_count = int(count * tp_rate)
        for i in range(count):
            findings.append(
                DiscoveryFinding(
                    finding_id=f"F-{mode.value}-{i}",
                    pattern_id=f"{pattern_prefix}-{i}",
                    confidence=0.8,
                    evidence_refs=[f"EVD-{mode.value}-{i}-A", f"EVD-{mode.value}-{i}-B"],
                    is_true_positive=i < tp_count,
                    discovery_mode=mode,
                )
            )
        return findings

    def test_suite_passes_all_checks(self):
        """Suite should pass when all metrics are good."""
        # Sequential: 70% precision/recall
        seq_findings = self._create_findings(10, 0.7, DiscoveryMode.SEQUENTIAL, pattern_prefix="SEQ")
        seq_metrics = QualityMetrics.compute(seq_findings, 10, DiscoveryMode.SEQUENTIAL)

        # Batch: 80% precision/recall (improvement) with DIFFERENT patterns
        batch_findings = self._create_findings(10, 0.8, DiscoveryMode.BATCH, pattern_prefix="BATCH")
        batch_metrics = QualityMetrics.compute(batch_findings, 10, DiscoveryMode.BATCH)

        # Compute suite
        quality_delta = QualityDelta.compute(batch_metrics, seq_metrics)
        # Novelty should be 100% since batch has completely different patterns
        novelty = NoveltyMetrics.compute(batch_findings, seq_findings)
        entropy = EntropyMetrics.compute(batch_findings)

        suite = BatchQualitySuite(quality_delta, novelty, entropy)

        self.assertTrue(suite.passes_regression_check())

    def test_suite_fails_on_regression(self):
        """Suite should fail when regression detected."""
        # Sequential: 80% precision/recall
        seq_findings = self._create_findings(10, 0.8, DiscoveryMode.SEQUENTIAL, pattern_prefix="SEQ")
        seq_metrics = QualityMetrics.compute(seq_findings, 10, DiscoveryMode.SEQUENTIAL)

        # Batch: 65% precision/recall (regression > 5%)
        batch_findings = self._create_findings(10, 0.65, DiscoveryMode.BATCH, pattern_prefix="BATCH")
        batch_metrics = QualityMetrics.compute(batch_findings, 10, DiscoveryMode.BATCH)

        quality_delta = QualityDelta.compute(batch_metrics, seq_metrics)
        novelty = NoveltyMetrics.compute(batch_findings)
        entropy = EntropyMetrics.compute(batch_findings)

        suite = BatchQualitySuite(quality_delta, novelty, entropy)

        self.assertFalse(suite.passes_regression_check())
        self.assertTrue(suite.quality_delta.has_any_regression())

    def test_suite_json_serialization(self):
        """Suite should serialize to valid JSON."""
        seq_findings = self._create_findings(5, 0.8, DiscoveryMode.SEQUENTIAL, pattern_prefix="SEQ")
        batch_findings = self._create_findings(5, 0.9, DiscoveryMode.BATCH, pattern_prefix="BATCH")

        seq_metrics = QualityMetrics.compute(seq_findings, 5, DiscoveryMode.SEQUENTIAL)
        batch_metrics = QualityMetrics.compute(batch_findings, 5, DiscoveryMode.BATCH)

        suite = BatchQualitySuite(
            quality_delta=QualityDelta.compute(batch_metrics, seq_metrics),
            novelty_metrics=NoveltyMetrics.compute(batch_findings),
            entropy_metrics=EntropyMetrics.compute(batch_findings),
        )

        # Should produce valid JSON
        json_str = suite.to_json()
        parsed = json.loads(json_str)

        self.assertIn("passes_regression_check", parsed)
        self.assertIn("quality_delta", parsed)
        self.assertIn("novelty_metrics", parsed)
        self.assertIn("entropy_metrics", parsed)


class TestRegressionThresholds(unittest.TestCase):
    """Tests for regression threshold constants."""

    def test_threshold_values(self):
        """Threshold constants should have sensible values."""
        self.assertEqual(PRECISION_REGRESSION_THRESHOLD, 0.05)
        self.assertEqual(RECALL_REGRESSION_THRESHOLD, 0.05)
        self.assertEqual(NOVELTY_MIN_THRESHOLD, 0.10)
        self.assertEqual(ENTROPY_MIN_THRESHOLD, 0.30)

    def test_thresholds_are_reasonable(self):
        """Thresholds should be between 0 and 1."""
        self.assertGreater(PRECISION_REGRESSION_THRESHOLD, 0)
        self.assertLess(PRECISION_REGRESSION_THRESHOLD, 1)

        self.assertGreater(NOVELTY_MIN_THRESHOLD, 0)
        self.assertLess(NOVELTY_MIN_THRESHOLD, 1)

        self.assertGreater(ENTROPY_MIN_THRESHOLD, 0)
        self.assertLess(ENTROPY_MIN_THRESHOLD, 1)


if __name__ == "__main__":
    unittest.main()
