"""
Benchmark Results

Stores and analyzes benchmark run results.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ChallengeResult:
    """Result for a single challenge."""
    challenge_id: str
    status: str  # detected, not-detected, error, skipped
    expected_detections: int = 0
    actual_detections: int = 0
    patterns_matched: list[str] = field(default_factory=list)
    patterns_missed: list[str] = field(default_factory=list)
    false_positives: list[str] = field(default_factory=list)
    error_message: str | None = None
    execution_time_ms: float = 0.0

    @property
    def is_detected(self) -> bool:
        """Whether vulnerability was detected."""
        return self.status == "detected"

    @property
    def recall(self) -> float:
        """Recall for this challenge."""
        if self.expected_detections == 0:
            return 1.0
        return self.actual_detections / self.expected_detections

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "challenge_id": self.challenge_id,
            "status": self.status,
            "expected_detections": self.expected_detections,
            "actual_detections": self.actual_detections,
            "patterns_matched": self.patterns_matched,
            "patterns_missed": self.patterns_missed,
            "false_positives": self.false_positives,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "recall": self.recall,
        }


@dataclass
class BenchmarkResults:
    """Results from a benchmark run."""
    suite_name: str
    suite_version: str
    run_timestamp: str = ""
    challenge_results: list[ChallengeResult] = field(default_factory=list)
    vkg_version: str = ""
    total_time_ms: float = 0.0

    def __post_init__(self):
        if not self.run_timestamp:
            self.run_timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def total_challenges(self) -> int:
        """Total number of challenges."""
        return len(self.challenge_results)

    @property
    def detected_count(self) -> int:
        """Number of detected challenges."""
        return sum(1 for r in self.challenge_results if r.is_detected)

    @property
    def skipped_count(self) -> int:
        """Number of skipped challenges."""
        return sum(1 for r in self.challenge_results if r.status == "skipped")

    @property
    def error_count(self) -> int:
        """Number of challenges with errors."""
        return sum(1 for r in self.challenge_results if r.status == "error")

    @property
    def detection_rate(self) -> float:
        """Overall detection rate."""
        evaluable = self.total_challenges - self.skipped_count
        if evaluable == 0:
            return 0.0
        return self.detected_count / evaluable

    @property
    def average_recall(self) -> float:
        """Average recall across all challenges."""
        recalls = [r.recall for r in self.challenge_results if r.status != "skipped"]
        if not recalls:
            return 0.0
        return sum(recalls) / len(recalls)

    @property
    def total_false_positives(self) -> int:
        """Total false positives across all challenges."""
        return sum(len(r.false_positives) for r in self.challenge_results)

    def add_result(self, result: ChallengeResult) -> None:
        """Add a challenge result."""
        self.challenge_results.append(result)

    def get_result(self, challenge_id: str) -> ChallengeResult | None:
        """Get result for a specific challenge."""
        for r in self.challenge_results:
            if r.challenge_id == challenge_id:
                return r
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "suite_name": self.suite_name,
            "suite_version": self.suite_version,
            "run_timestamp": self.run_timestamp,
            "vkg_version": self.vkg_version,
            "total_time_ms": self.total_time_ms,
            "summary": {
                "total_challenges": self.total_challenges,
                "detected": self.detected_count,
                "skipped": self.skipped_count,
                "errors": self.error_count,
                "detection_rate": round(self.detection_rate, 3),
                "average_recall": round(self.average_recall, 3),
                "total_false_positives": self.total_false_positives,
            },
            "challenge_results": [r.to_dict() for r in self.challenge_results],
        }

    def save(self, output_path: Path) -> None:
        """Save results to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, input_path: Path) -> "BenchmarkResults":
        """Load results from JSON file."""
        with open(input_path) as f:
            data = json.load(f)

        results = cls(
            suite_name=data["suite_name"],
            suite_version=data["suite_version"],
            run_timestamp=data.get("run_timestamp", ""),
            vkg_version=data.get("vkg_version", ""),
            total_time_ms=data.get("total_time_ms", 0.0),
        )

        for cr in data.get("challenge_results", []):
            results.add_result(ChallengeResult(
                challenge_id=cr["challenge_id"],
                status=cr["status"],
                expected_detections=cr.get("expected_detections", 0),
                actual_detections=cr.get("actual_detections", 0),
                patterns_matched=cr.get("patterns_matched", []),
                patterns_missed=cr.get("patterns_missed", []),
                false_positives=cr.get("false_positives", []),
                error_message=cr.get("error_message"),
                execution_time_ms=cr.get("execution_time_ms", 0.0),
            ))

        return results


def compare_results(current: BenchmarkResults, baseline: BenchmarkResults) -> dict[str, Any]:
    """Compare two benchmark results."""
    comparison = {
        "current_rate": current.detection_rate,
        "baseline_rate": baseline.detection_rate,
        "rate_delta": current.detection_rate - baseline.detection_rate,
        "improved": [],
        "regressed": [],
        "unchanged": [],
    }

    for cr in current.challenge_results:
        br = baseline.get_result(cr.challenge_id)
        if br is None:
            comparison["improved"].append(cr.challenge_id)
        elif cr.is_detected and not br.is_detected:
            comparison["improved"].append(cr.challenge_id)
        elif not cr.is_detected and br.is_detected:
            comparison["regressed"].append(cr.challenge_id)
        else:
            comparison["unchanged"].append(cr.challenge_id)

    comparison["has_regression"] = len(comparison["regressed"]) > 0
    return comparison
