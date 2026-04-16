"""LLM verdict accuracy testing for beads.

This module provides tools to validate that beads contain sufficient context
for LLMs to make accurate verdicts. The target is 80%+ accuracy using ONLY
bead content (no additional context).

Usage:
    from alphaswarm_sol.beads.accuracy_test import BeadAccuracyTester, load_test_cases
    from alphaswarm_sol.llm import LLMClient

    # Load test cases
    cases = load_test_cases(Path("tests/fixtures/bead_ground_truth.json"))

    # Initialize tester
    client = LLMClient()
    tester = BeadAccuracyTester(client, runs_per_bead=3)

    # Run test
    report = await tester.run_accuracy_test(cases)

    # Print summary
    print(report.summary())
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schema import VulnerabilityBead
from .types import VerdictType


class ExpectedVerdict(Enum):
    """Expected verdict for a test case."""

    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"


@dataclass
class TestCase:
    """A test case with bead and expected verdict.

    Attributes:
        bead: The vulnerability bead to test
        expected: Expected verdict (true_positive or false_positive)
        rationale: Why this is the expected verdict
        source: Where ground truth came from (e.g., "audit report", "manual review")
        vulnerability_class: Optional class for grouping results
    """

    bead: VulnerabilityBead
    expected: ExpectedVerdict
    rationale: str
    source: str
    vulnerability_class: str = ""


@dataclass
class LLMVerdict:
    """An LLM's verdict on a bead.

    Attributes:
        verdict: The verdict type
        confidence: Confidence score (0.0-1.0)
        reasoning: LLM's reasoning explanation
        raw_response: Full raw response from LLM
    """

    verdict: VerdictType
    confidence: float
    reasoning: str
    raw_response: str


@dataclass
class TestResult:
    """Result of testing one bead.

    Attributes:
        test_case: The original test case
        llm_verdicts: All LLM verdicts (multiple runs)
        final_verdict: Final verdict after voting
        is_correct: Whether the final verdict matches expected
        notes: Any additional notes
    """

    test_case: TestCase
    llm_verdicts: List[LLMVerdict]
    final_verdict: VerdictType
    is_correct: bool
    notes: str = ""


@dataclass
class AccuracyReport:
    """Full accuracy test report.

    Attributes:
        timestamp: When the test was run
        model: Model used for testing
        total_cases: Total number of test cases
        correct_cases: Number of correct predictions
        accuracy: Accuracy percentage
        results: Individual test results
        config: Test configuration
    """

    timestamp: datetime
    model: str
    total_cases: int
    correct_cases: int
    accuracy: float
    results: List[TestResult]
    config: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "model": self.model,
            "total_cases": self.total_cases,
            "correct_cases": self.correct_cases,
            "accuracy": self.accuracy,
            "results": [
                {
                    "bead_id": r.test_case.bead.id,
                    "expected": r.test_case.expected.value,
                    "predicted": r.final_verdict.value,
                    "is_correct": r.is_correct,
                    "verdicts": [
                        {"verdict": v.verdict.value, "confidence": v.confidence}
                        for v in r.llm_verdicts
                    ],
                }
                for r in self.results
            ],
            "config": self.config,
        }

    def summary(self) -> str:
        """Generate human-readable summary report."""
        lines = [
            "# LLM Verdict Accuracy Report",
            "",
            f"**Model:** {self.model}",
            f"**Date:** {self.timestamp.isoformat()}",
            "",
            "## Results",
            f"- Total Cases: {self.total_cases}",
            f"- Correct: {self.correct_cases}",
            f"- **Accuracy: {self.accuracy:.1%}**",
            "",
            "## Breakdown",
        ]

        # Breakdown by expected verdict
        tp_cases = [
            r for r in self.results if r.test_case.expected == ExpectedVerdict.TRUE_POSITIVE
        ]
        fp_cases = [
            r for r in self.results if r.test_case.expected == ExpectedVerdict.FALSE_POSITIVE
        ]

        tp_correct = sum(1 for r in tp_cases if r.is_correct)
        fp_correct = sum(1 for r in fp_cases if r.is_correct)

        if tp_cases:
            lines.append(
                f"- True Positives: {tp_correct}/{len(tp_cases)} correct "
                f"({tp_correct/len(tp_cases):.1%})"
            )
        else:
            lines.append("- True Positives: N/A")

        if fp_cases:
            lines.append(
                f"- False Positives: {fp_correct}/{len(fp_cases)} correct "
                f"({fp_correct/len(fp_cases):.1%})"
            )
        else:
            lines.append("- False Positives: N/A")

        lines.extend(["", "## Failures"])

        failures = [r for r in self.results if not r.is_correct]
        if failures:
            for failure in failures:
                lines.append(
                    f"- {failure.test_case.bead.id}: Expected {failure.test_case.expected.value}, "
                    f"Got {failure.final_verdict.value}"
                )
        else:
            lines.append("- None!")

        return "\n".join(lines)

    def breakdown_by_class(self) -> Dict[str, Dict[str, Any]]:
        """Get accuracy breakdown by vulnerability class."""
        by_class: Dict[str, List[TestResult]] = {}

        for r in self.results:
            vuln_class = r.test_case.vulnerability_class or "unknown"
            if vuln_class not in by_class:
                by_class[vuln_class] = []
            by_class[vuln_class].append(r)

        breakdown = {}
        for vuln_class, class_results in by_class.items():
            correct = sum(1 for r in class_results if r.is_correct)
            breakdown[vuln_class] = {
                "total": len(class_results),
                "correct": correct,
                "accuracy": correct / len(class_results) if class_results else 0.0,
            }

        return breakdown


class BeadAccuracyTester:
    """Test LLM verdict accuracy on beads.

    This tester runs each bead through the LLM multiple times and uses
    majority voting to determine the final verdict.

    Usage:
        from alphaswarm_sol.llm import LLMClient

        client = LLMClient()
        tester = BeadAccuracyTester(client)
        report = await tester.run_accuracy_test(test_cases)
    """

    VERDICT_PROMPT_SUFFIX = """

Based on the above information, provide your verdict in the following JSON format:
{
    "verdict": "true_positive" or "false_positive",
    "confidence": 0.0 to 1.0,
    "reasoning": "Your detailed reasoning"
}

A "true_positive" means this is a real vulnerability that should be fixed.
A "false_positive" means this is NOT a real vulnerability (safe code, pattern misidentification, or mitigated).

Consider:
1. Is the vulnerable pattern actually present in the code?
2. Are there any mitigations (guards, checks, access controls)?
3. Could this be exploited in practice?

Respond ONLY with the JSON, no additional text.
"""

    def __init__(
        self,
        llm_client: Any,  # LLMClient from alphaswarm_sol.llm
        model: str = "claude-3-opus",
        runs_per_bead: int = 3,
        temperature: float = 0.0,
    ):
        """Initialize the tester.

        Args:
            llm_client: The LLM client to use
            model: Model identifier (for documentation, actual model from client config)
            runs_per_bead: Number of times to run each bead (for voting)
            temperature: Temperature for LLM calls (0.0 for deterministic)
        """
        self.client = llm_client
        self.model = model
        self.runs_per_bead = runs_per_bead
        self.temperature = temperature

    async def run_accuracy_test(self, test_cases: List[TestCase]) -> AccuracyReport:
        """Run accuracy test on a set of test cases.

        Args:
            test_cases: List of beads with expected verdicts

        Returns:
            AccuracyReport with results
        """
        results = []

        for i, case in enumerate(test_cases):
            print(f"Testing {i+1}/{len(test_cases)}: {case.bead.id}")

            # Get multiple verdicts
            verdicts = []
            for _run in range(self.runs_per_bead):
                verdict = await self._get_llm_verdict(case.bead)
                verdicts.append(verdict)

            # Determine final verdict (majority vote)
            final_verdict = self._vote(verdicts)

            # Check correctness
            expected_verdict_type = (
                VerdictType.TRUE_POSITIVE
                if case.expected == ExpectedVerdict.TRUE_POSITIVE
                else VerdictType.FALSE_POSITIVE
            )
            is_correct = final_verdict == expected_verdict_type

            results.append(
                TestResult(
                    test_case=case,
                    llm_verdicts=verdicts,
                    final_verdict=final_verdict,
                    is_correct=is_correct,
                )
            )

        # Calculate accuracy
        correct = sum(1 for r in results if r.is_correct)
        accuracy = correct / len(results) if results else 0

        return AccuracyReport(
            timestamp=datetime.now(),
            model=self.model,
            total_cases=len(results),
            correct_cases=correct,
            accuracy=accuracy,
            results=results,
            config={
                "runs_per_bead": self.runs_per_bead,
                "temperature": self.temperature,
            },
        )

    def run_accuracy_test_sync(self, test_cases: List[TestCase]) -> AccuracyReport:
        """Synchronous wrapper for run_accuracy_test."""
        return asyncio.run(self.run_accuracy_test(test_cases))

    async def _get_llm_verdict(self, bead: VulnerabilityBead) -> LLMVerdict:
        """Get LLM verdict for a single bead."""
        # Build prompt
        prompt = bead.get_llm_prompt() + self.VERDICT_PROMPT_SUFFIX

        # Call LLM
        try:
            response = await self.client.analyze(
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=1000,
            )

            # Parse response
            return self._parse_response(response)
        except Exception as e:
            # Return inconclusive on error
            return LLMVerdict(
                verdict=VerdictType.INCONCLUSIVE,
                confidence=0.0,
                reasoning=f"Error: {e}",
                raw_response="",
            )

    def _parse_response(self, response: str) -> LLMVerdict:
        """Parse LLM response into a verdict."""
        try:
            # Try to extract JSON from response
            # Handle case where response might have extra text
            response = response.strip()

            # Find JSON in response
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)

                # Map verdict string to VerdictType
                verdict_str = data.get("verdict", "").lower()
                if verdict_str == "true_positive":
                    verdict = VerdictType.TRUE_POSITIVE
                elif verdict_str == "false_positive":
                    verdict = VerdictType.FALSE_POSITIVE
                else:
                    verdict = VerdictType.INCONCLUSIVE

                return LLMVerdict(
                    verdict=verdict,
                    confidence=float(data.get("confidence", 0.5)),
                    reasoning=str(data.get("reasoning", "")),
                    raw_response=response,
                )
            else:
                raise ValueError("No JSON found in response")

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Failed to parse - treat as inconclusive
            return LLMVerdict(
                verdict=VerdictType.INCONCLUSIVE,
                confidence=0.0,
                reasoning=f"Parse error: {e}",
                raw_response=response,
            )

    def _vote(self, verdicts: List[LLMVerdict]) -> VerdictType:
        """Majority vote from multiple verdicts."""
        votes: Dict[VerdictType, int] = {}
        for v in verdicts:
            if v.verdict not in votes:
                votes[v.verdict] = 0
            votes[v.verdict] += 1

        # Return most common (excluding INCONCLUSIVE if possible)
        valid_votes = {k: v for k, v in votes.items() if k != VerdictType.INCONCLUSIVE}
        if valid_votes:
            return max(valid_votes, key=lambda k: valid_votes[k])

        # All inconclusive
        return VerdictType.INCONCLUSIVE


def load_test_cases(path: Path) -> List[TestCase]:
    """Load test cases from JSON file.

    Expected format:
    {
        "cases": [
            {
                "bead_path": "path/to/bead.json",
                "expected": "true_positive" or "false_positive",
                "rationale": "Why this is expected",
                "source": "audit report / manual review / etc",
                "vulnerability_class": "reentrancy"  // optional
            }
        ]
    }
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cases = []
    base_dir = path.parent

    for item in data.get("cases", []):
        bead_path = base_dir / item["bead_path"]

        with open(bead_path, "r", encoding="utf-8") as f:
            bead_data = json.load(f)

        bead = VulnerabilityBead.from_dict(bead_data)

        cases.append(
            TestCase(
                bead=bead,
                expected=ExpectedVerdict(item["expected"]),
                rationale=item.get("rationale", ""),
                source=item.get("source", "unknown"),
                vulnerability_class=item.get("vulnerability_class", bead.vulnerability_class),
            )
        )

    return cases


def create_test_case(
    bead: VulnerabilityBead,
    expected: str,
    rationale: str,
    source: str = "manual review",
) -> TestCase:
    """Create a test case from a bead.

    Helper function for programmatic test case creation.

    Args:
        bead: The vulnerability bead
        expected: Expected verdict ("true_positive" or "false_positive")
        rationale: Why this is the expected verdict
        source: Ground truth source

    Returns:
        TestCase ready for testing
    """
    return TestCase(
        bead=bead,
        expected=ExpectedVerdict(expected),
        rationale=rationale,
        source=source,
        vulnerability_class=bead.vulnerability_class,
    )


def analyze_failures(report: AccuracyReport) -> str:
    """Analyze what went wrong for failed cases.

    Returns:
        Detailed failure analysis report
    """
    failures = [r for r in report.results if not r.is_correct]

    if not failures:
        return "No failures to analyze!"

    lines = [
        f"## Failure Analysis ({len(failures)} failures)",
        "",
    ]

    for failure in failures:
        lines.append(f"### {failure.test_case.bead.id}")
        lines.append(f"**Expected:** {failure.test_case.expected.value}")
        lines.append(f"**Got:** {failure.final_verdict.value}")
        lines.append(f"**Rationale:** {failure.test_case.rationale}")
        lines.append("")
        lines.append("**LLM Reasoning:**")

        for i, v in enumerate(failure.llm_verdicts):
            lines.append(f"  Run {i+1}: {v.verdict.value} ({v.confidence:.0%})")
            reasoning_preview = v.reasoning[:200] + "..." if len(v.reasoning) > 200 else v.reasoning
            lines.append(f"    {reasoning_preview}")

        lines.append("")

    # Categorize failures
    missed_tp = [f for f in failures if f.test_case.expected == ExpectedVerdict.TRUE_POSITIVE]
    false_fp = [f for f in failures if f.test_case.expected == ExpectedVerdict.FALSE_POSITIVE]

    lines.extend(
        [
            "## Failure Types",
            f"  Missed TPs (should have confirmed): {len(missed_tp)}",
            f"  False FPs (wrongly rejected): {len(false_fp)}",
        ]
    )

    return "\n".join(lines)


# Export for module
__all__ = [
    "ExpectedVerdict",
    "TestCase",
    "LLMVerdict",
    "TestResult",
    "AccuracyReport",
    "BeadAccuracyTester",
    "load_test_cases",
    "create_test_case",
    "analyze_failures",
]
