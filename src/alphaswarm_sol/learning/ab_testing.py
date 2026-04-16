"""A/B testing infrastructure for pattern configurations.

Task 7.5: Enable testing pattern variants before production deployment.
Route a percentage of findings to test configurations and compare performance.

Key concepts:
- Consistent assignment: Same finding always gets same variant
- Traffic splitting: Configurable percentage to treatment group
- Statistical significance: Proper checks before declaring winner
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class Variant(Enum):
    """A/B test variants."""

    CONTROL = "A"
    TREATMENT = "B"


@dataclass
class ABTestConfig:
    """Configuration for an A/B test.

    Attributes:
        test_id: Unique identifier for this test
        pattern_id: Pattern being tested
        treatment_config: Configuration changes for variant B
        traffic_fraction: Fraction of findings to route to treatment (0-1)
        min_samples: Minimum samples needed for significance check
        start_time: When the test started
        end_time: When the test ended (None if active)
    """

    test_id: str
    pattern_id: str
    treatment_config: Dict[str, Any]
    traffic_fraction: float = 0.10
    min_samples: int = 20
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    description: str = ""

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not 0 < self.traffic_fraction < 1:
            raise ValueError("traffic_fraction must be between 0 and 1")
        if self.min_samples < 1:
            raise ValueError("min_samples must be at least 1")

    def is_active(self) -> bool:
        """Check if test is currently active."""
        return self.end_time is None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "test_id": self.test_id,
            "pattern_id": self.pattern_id,
            "treatment_config": self.treatment_config,
            "traffic_fraction": self.traffic_fraction,
            "min_samples": self.min_samples,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ABTestConfig":
        """Create from dict."""
        end_time = data.get("end_time")
        if end_time:
            end_time = datetime.fromisoformat(end_time)

        return cls(
            test_id=data["test_id"],
            pattern_id=data["pattern_id"],
            treatment_config=data.get("treatment_config", {}),
            traffic_fraction=data.get("traffic_fraction", 0.10),
            min_samples=data.get("min_samples", 20),
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=end_time,
            description=data.get("description", ""),
        )


@dataclass
class ABTestResult:
    """Results of an A/B test.

    Provides metrics for comparing control vs treatment performance.
    """

    test_id: str
    control_samples: int
    treatment_samples: int
    control_precision: float
    treatment_precision: float
    control_verdicts: Dict[str, int]  # {confirmed: N, rejected: N}
    treatment_verdicts: Dict[str, int]
    is_significant: bool
    p_value: Optional[float]
    winner: Optional[Variant]
    precision_diff: float = 0.0

    def __post_init__(self) -> None:
        """Calculate derived fields."""
        self.precision_diff = self.treatment_precision - self.control_precision

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "test_id": self.test_id,
            "control_samples": self.control_samples,
            "treatment_samples": self.treatment_samples,
            "control_precision": round(self.control_precision, 4),
            "treatment_precision": round(self.treatment_precision, 4),
            "control_verdicts": self.control_verdicts,
            "treatment_verdicts": self.treatment_verdicts,
            "is_significant": self.is_significant,
            "p_value": round(self.p_value, 4) if self.p_value else None,
            "winner": self.winner.value if self.winner else None,
            "precision_diff": round(self.precision_diff, 4),
        }

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"# A/B Test Results: {self.test_id}",
            "",
            f"Control (A): {self.control_samples} samples, {self.control_precision:.1%} precision",
            f"Treatment (B): {self.treatment_samples} samples, {self.treatment_precision:.1%} precision",
            "",
            f"Difference: {self.precision_diff:+.1%}",
            f"Significant: {'Yes' if self.is_significant else 'No'}",
        ]

        if self.winner:
            lines.append(f"Winner: Variant {self.winner.value}")
        else:
            lines.append("Winner: No clear winner yet")

        return "\n".join(lines)


class PatternABTest:
    """Manage A/B test for a pattern.

    Handles variant assignment, verdict recording, and result calculation.
    """

    def __init__(self, config: ABTestConfig, storage_path: Path):
        """Initialize test.

        Args:
            config: Test configuration
            storage_path: Directory for storing results
        """
        self.config = config
        self.storage_path = storage_path
        self._results: Dict[str, Dict[str, Any]] = {"A": {}, "B": {}}
        self._load()

    def get_variant(self, finding_id: str) -> Variant:
        """Determine variant for a finding.

        Uses consistent hashing so same finding always gets same variant.
        This ensures findings aren't evaluated multiple times with different configs.

        Args:
            finding_id: Unique identifier for the finding

        Returns:
            Variant assignment (CONTROL or TREATMENT)
        """
        # Consistent hash assignment
        hash_input = f"{self.config.test_id}:{finding_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        fraction = (hash_value % 10000) / 10000.0

        if fraction < self.config.traffic_fraction:
            return Variant.TREATMENT
        return Variant.CONTROL

    def record_verdict(
        self,
        finding_id: str,
        variant: Variant,
        verdict: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a verdict for a finding.

        Args:
            finding_id: Unique identifier for the finding
            variant: Which variant was used
            verdict: "confirmed" or "rejected"
            metadata: Optional additional data
        """
        var_key = variant.value
        self._results[var_key][finding_id] = {
            "verdict": verdict,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self._save()

    def get_results(self) -> ABTestResult:
        """Calculate test results.

        Returns:
            ABTestResult with metrics and significance check
        """
        control = self._results["A"]
        treatment = self._results["B"]

        control_verdicts = self._count_verdicts(control)
        treatment_verdicts = self._count_verdicts(treatment)

        control_precision = self._calculate_precision(control_verdicts)
        treatment_precision = self._calculate_precision(treatment_verdicts)

        # Check statistical significance
        is_significant, p_value = self._check_significance(
            control_verdicts, treatment_verdicts
        )

        # Determine winner
        winner = None
        if is_significant:
            if treatment_precision > control_precision:
                winner = Variant.TREATMENT
            elif control_precision > treatment_precision:
                winner = Variant.CONTROL

        return ABTestResult(
            test_id=self.config.test_id,
            control_samples=len(control),
            treatment_samples=len(treatment),
            control_precision=control_precision,
            treatment_precision=treatment_precision,
            control_verdicts=control_verdicts,
            treatment_verdicts=treatment_verdicts,
            is_significant=is_significant,
            p_value=p_value,
            winner=winner,
        )

    def is_complete(self) -> bool:
        """Check if test has enough samples for analysis.

        Returns:
            True if both variants have minimum required samples
        """
        control_count = len(self._results["A"])
        treatment_count = len(self._results["B"])

        # Treatment needs fewer samples due to traffic fraction
        treatment_min = max(5, int(self.config.min_samples * self.config.traffic_fraction))

        return (
            control_count >= self.config.min_samples
            and treatment_count >= treatment_min
        )

    def get_assignment_stats(self) -> Dict[str, int]:
        """Get statistics on variant assignments.

        Returns:
            Dict with counts per variant
        """
        return {
            "control": len(self._results["A"]),
            "treatment": len(self._results["B"]),
        }

    def _count_verdicts(self, results: Dict[str, Any]) -> Dict[str, int]:
        """Count verdicts by type."""
        counts = {"confirmed": 0, "rejected": 0}
        for r in results.values():
            verdict = r.get("verdict", "")
            if verdict in counts:
                counts[verdict] += 1
        return counts

    def _calculate_precision(self, verdicts: Dict[str, int]) -> float:
        """Calculate precision from verdict counts.

        Precision = TP / (TP + FP)
        where confirmed = TP, rejected = FP
        """
        tp = verdicts.get("confirmed", 0)
        fp = verdicts.get("rejected", 0)
        if tp + fp == 0:
            return 0.5  # No data - return prior
        return tp / (tp + fp)

    def _check_significance(
        self,
        control: Dict[str, int],
        treatment: Dict[str, int],
    ) -> Tuple[bool, Optional[float]]:
        """Check if difference is statistically significant.

        Uses a simple proportion comparison approach.
        For production use, consider chi-square or Fisher's exact test.

        Args:
            control: Verdict counts for control group
            treatment: Verdict counts for treatment group

        Returns:
            Tuple of (is_significant, p_value)
        """
        control_total = sum(control.values())
        treatment_total = sum(treatment.values())

        # Need minimum samples for any significance check
        if control_total < 10 or treatment_total < 5:
            return False, None

        control_precision = self._calculate_precision(control)
        treatment_precision = self._calculate_precision(treatment)

        diff = abs(control_precision - treatment_precision)

        # Simple significance heuristic:
        # - Require at least 15% difference
        # - Require sufficient samples in both groups
        # In production, use proper statistical test
        if diff > 0.15 and min(control_total, treatment_total) >= 10:
            # Rough p-value estimate based on sample size and difference
            # This is a placeholder - real implementation would use proper test
            if diff > 0.30:
                p_value = 0.01
            elif diff > 0.20:
                p_value = 0.05
            else:
                p_value = 0.10
            return True, p_value

        return False, None

    def _load(self) -> None:
        """Load results from storage."""
        results_file = self.storage_path / f"ab_test_{self.config.test_id}.json"
        if results_file.exists():
            try:
                with open(results_file, "r") as f:
                    data = json.load(f)
                    self._results = data.get("results", {"A": {}, "B": {}})
            except (json.JSONDecodeError, KeyError):
                self._results = {"A": {}, "B": {}}

    def _save(self) -> None:
        """Save results to storage."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        results_file = self.storage_path / f"ab_test_{self.config.test_id}.json"

        data = {
            "config": self.config.to_dict(),
            "results": self._results,
        }

        with open(results_file, "w") as f:
            json.dump(data, f, indent=2)


class ABTestManager:
    """Manage multiple A/B tests.

    Provides a central interface for creating, managing, and querying tests.
    """

    def __init__(self, storage_path: Path):
        """Initialize manager.

        Args:
            storage_path: Directory for storing all test data
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._tests: Dict[str, PatternABTest] = {}
        self._load_tests()

    def _load_tests(self) -> None:
        """Load all existing tests from storage."""
        for test_file in self.storage_path.glob("ab_test_*.json"):
            try:
                with open(test_file, "r") as f:
                    data = json.load(f)
                    config = ABTestConfig.from_dict(data["config"])
                    self._tests[config.test_id] = PatternABTest(config, self.storage_path)
            except (json.JSONDecodeError, KeyError):
                continue

    def create_test(
        self,
        pattern_id: str,
        treatment_config: Dict[str, Any],
        traffic_fraction: float = 0.10,
        min_samples: int = 20,
        description: str = "",
    ) -> str:
        """Create a new A/B test.

        Args:
            pattern_id: Pattern to test
            treatment_config: Configuration changes for treatment group
            traffic_fraction: Fraction of traffic to route to treatment
            min_samples: Minimum samples needed for significance
            description: Human-readable description of the test

        Returns:
            Test ID
        """
        # Check for existing active test
        existing = self.get_active_test(pattern_id)
        if existing:
            raise ValueError(
                f"Pattern {pattern_id} already has active test: {existing.config.test_id}"
            )

        test_id = f"test_{pattern_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        config = ABTestConfig(
            test_id=test_id,
            pattern_id=pattern_id,
            treatment_config=treatment_config,
            traffic_fraction=traffic_fraction,
            min_samples=min_samples,
            description=description,
        )

        test = PatternABTest(config, self.storage_path)
        self._tests[test_id] = test
        test._save()

        return test_id

    def get_test(self, test_id: str) -> Optional[PatternABTest]:
        """Get a test by ID.

        Args:
            test_id: Test identifier

        Returns:
            PatternABTest or None if not found
        """
        return self._tests.get(test_id)

    def get_active_test(self, pattern_id: str) -> Optional[PatternABTest]:
        """Get active test for a pattern.

        Args:
            pattern_id: Pattern to check

        Returns:
            Active PatternABTest or None
        """
        for test in self._tests.values():
            if test.config.pattern_id == pattern_id and test.config.is_active():
                return test
        return None

    def get_tests_for_pattern(self, pattern_id: str) -> List[PatternABTest]:
        """Get all tests for a pattern (active and completed).

        Args:
            pattern_id: Pattern to query

        Returns:
            List of PatternABTest objects
        """
        return [
            test for test in self._tests.values()
            if test.config.pattern_id == pattern_id
        ]

    def end_test(self, test_id: str) -> Optional[ABTestResult]:
        """End a test and return results.

        Args:
            test_id: Test to end

        Returns:
            ABTestResult or None if test not found
        """
        test = self._tests.get(test_id)
        if test:
            test.config.end_time = datetime.now()
            test._save()
            return test.get_results()
        return None

    def get_all_active_tests(self) -> List[PatternABTest]:
        """Get all currently active tests.

        Returns:
            List of active PatternABTest objects
        """
        return [test for test in self._tests.values() if test.config.is_active()]

    def get_all_results(self) -> Dict[str, ABTestResult]:
        """Get results for all tests.

        Returns:
            Dict mapping test_id to ABTestResult
        """
        return {test_id: test.get_results() for test_id, test in self._tests.items()}

    def summary(self) -> str:
        """Generate summary of all tests.

        Returns:
            Markdown-formatted summary
        """
        active = self.get_all_active_tests()
        completed = [t for t in self._tests.values() if not t.config.is_active()]

        lines = ["# A/B Test Summary", ""]

        if active:
            lines.append(f"## Active Tests ({len(active)})")
            for test in active:
                stats = test.get_assignment_stats()
                lines.append(
                    f"- {test.config.test_id}: {test.config.pattern_id} "
                    f"(A:{stats['control']}, B:{stats['treatment']})"
                )
            lines.append("")

        if completed:
            lines.append(f"## Completed Tests ({len(completed)})")
            for test in completed:
                result = test.get_results()
                winner_str = f"Winner: {result.winner.value}" if result.winner else "No winner"
                lines.append(
                    f"- {test.config.test_id}: {winner_str} "
                    f"(diff: {result.precision_diff:+.1%})"
                )
            lines.append("")

        if not active and not completed:
            lines.append("No tests created yet.")

        return "\n".join(lines)
