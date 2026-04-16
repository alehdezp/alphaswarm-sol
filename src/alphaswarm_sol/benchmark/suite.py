"""
Benchmark Suite Definition

Loads and manages benchmark suite configurations from YAML files.
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExpectedDetection:
    """Expected detection for a challenge."""
    pattern: str
    contract: str
    function: str
    property: str
    confidence: str = "high"


@dataclass
class Challenge:
    """A single benchmark challenge."""
    id: str
    name: str
    source_path: str
    vulnerability_type: str
    severity: str
    expected_detections: list[ExpectedDetection] = field(default_factory=list)
    expected_vulnerable_functions: list[str] = field(default_factory=list)
    expected_safe_functions: list[str] = field(default_factory=list)
    status: str = "pending"
    difficulty: int = 1
    category: str = ""

    @classmethod
    def from_yaml(cls, yaml_data: dict[str, Any], file_path: Path) -> "Challenge":
        """Load challenge from YAML data."""
        vuln = yaml_data.get("vulnerability", {})
        expected = yaml_data.get("expected_detections", [])
        funcs = yaml_data.get("expected_functions", {})

        detections = [
            ExpectedDetection(
                pattern=d.get("pattern", ""),
                contract=d.get("contract", ""),
                function=d.get("function", ""),
                property=d.get("property", ""),
                confidence=d.get("confidence", "high"),
            )
            for d in expected
        ]

        return cls(
            id=yaml_data.get("id", file_path.stem),
            name=yaml_data.get("name", file_path.stem),
            source_path=yaml_data.get("source_path", ""),
            vulnerability_type=vuln.get("type", "unknown"),
            severity=vuln.get("severity", "medium"),
            expected_detections=detections,
            expected_vulnerable_functions=funcs.get("vulnerable", []),
            expected_safe_functions=funcs.get("safe", []),
            status=yaml_data.get("status", "pending"),
            difficulty=yaml_data.get("difficulty", 1),
            category=yaml_data.get("category", ""),
        )


@dataclass
class BenchmarkSuite:
    """A collection of benchmark challenges."""
    name: str
    description: str
    version: str
    challenges: list[Challenge] = field(default_factory=list)
    targets: dict[str, float] = field(default_factory=dict)

    @classmethod
    def load(cls, suite_path: Path) -> "BenchmarkSuite":
        """Load benchmark suite from YAML file."""
        with open(suite_path) as f:
            data = yaml.safe_load(f)

        suite = cls(
            name=data.get("name", "unknown"),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            targets=data.get("targets", {"minimum": 0.7, "target": 0.8}),
        )

        # Load individual challenge files
        suite_dir = suite_path.parent
        for challenge_ref in data.get("challenges", []):
            challenge_file = suite_dir / challenge_ref["file"]
            if challenge_file.exists():
                with open(challenge_file) as f:
                    challenge_data = yaml.safe_load(f)
                challenge = Challenge.from_yaml(challenge_data, challenge_file)
                # Override status from suite.yaml if present
                if "status" in challenge_ref:
                    challenge.status = challenge_ref["status"]
                suite.challenges.append(challenge)

        return suite

    @property
    def detectable_count(self) -> int:
        """Count of challenges that should be detectable."""
        return sum(1 for c in self.challenges if c.status != "not-applicable")

    @property
    def detected_count(self) -> int:
        """Count of challenges that are detected."""
        return sum(1 for c in self.challenges if c.status == "detected")

    @property
    def detection_rate(self) -> float:
        """Current detection rate."""
        detectable = self.detectable_count
        if detectable == 0:
            return 0.0
        return self.detected_count / detectable

    def get_challenge(self, challenge_id: str) -> Challenge | None:
        """Get a challenge by ID."""
        for c in self.challenges:
            if c.id == challenge_id:
                return c
        return None


def load_suite(suite_name: str, benchmark_dir: Path | None = None) -> BenchmarkSuite:
    """Load a benchmark suite by name."""
    if benchmark_dir is None:
        # Default to project benchmarks directory
        benchmark_dir = Path(__file__).parent.parent.parent.parent / "benchmarks"

    suite_path = benchmark_dir / suite_name / "suite.yaml"
    if not suite_path.exists():
        raise FileNotFoundError(f"Benchmark suite not found: {suite_path}")

    return BenchmarkSuite.load(suite_path)
