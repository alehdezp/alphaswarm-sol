"""Tests for LLM verdict accuracy testing framework.

This module tests the accuracy testing infrastructure, NOT actual LLM accuracy.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from alphaswarm_sol.beads.accuracy_test import (
    AccuracyReport,
    BeadAccuracyTester,
    ExpectedVerdict,
    LLMVerdict,
    TestCase,
    TestResult,
    analyze_failures,
    create_test_case,
    load_test_cases,
)
from alphaswarm_sol.beads.schema import (
    InvestigationGuide,
    PatternContext,
    TestContext,
    VulnerabilityBead,
)
from alphaswarm_sol.beads.types import (
    BeadStatus,
    CodeSnippet,
    InvestigationStep,
    Severity,
    VerdictType,
)


def make_test_bead(
    bead_id: str = "test-001",
    vulnerability_class: str = "reentrancy",
    source: str = "function test() {}",
) -> VulnerabilityBead:
    """Create a minimal test bead for testing."""
    return VulnerabilityBead(
        id=bead_id,
        vulnerability_class=vulnerability_class,
        pattern_id="test-pattern",
        severity=Severity.HIGH,
        confidence=0.9,
        status=BeadStatus.PENDING,
        vulnerable_code=CodeSnippet(
            source=source,
            file_path="/test.sol",
            start_line=1,
            end_line=5,
            function_name="test",
            contract_name="Test",
        ),
        related_code=[],
        full_contract=None,
        inheritance_chain=[],
        pattern_context=PatternContext(
            pattern_name="Test Pattern",
            pattern_description="A test pattern",
            why_flagged="For testing",
            matched_properties=["test"],
            evidence_lines=[1, 2],
        ),
        investigation_guide=InvestigationGuide(
            steps=[
                InvestigationStep(
                    step_number=1,
                    action="Check something",
                    look_for="Something",
                    evidence_needed="Evidence",
                    red_flag="Red flag",
                    safe_if="Safe condition",
                )
            ],
            questions_to_answer=["Is it safe?"],
            common_false_positives=["Always"],
            key_indicators=["Test"],
            safe_patterns=["None"],
        ),
        test_context=TestContext(
            scaffold_code="// test",
            attack_scenario="Attack",
            setup_requirements=["Deploy"],
            expected_outcome="Success",
        ),
        similar_exploits=[],
        fix_recommendations=["Fix it"],
        notes=[],
        verdict=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        context_hash="testhash",
    )


class TestExpectedVerdict(unittest.TestCase):
    """Test ExpectedVerdict enum."""

    def test_true_positive_value(self) -> None:
        """TRUE_POSITIVE has correct value."""
        self.assertEqual(ExpectedVerdict.TRUE_POSITIVE.value, "true_positive")

    def test_false_positive_value(self) -> None:
        """FALSE_POSITIVE has correct value."""
        self.assertEqual(ExpectedVerdict.FALSE_POSITIVE.value, "false_positive")

    def test_from_string(self) -> None:
        """Can create from string."""
        self.assertEqual(ExpectedVerdict("true_positive"), ExpectedVerdict.TRUE_POSITIVE)
        self.assertEqual(ExpectedVerdict("false_positive"), ExpectedVerdict.FALSE_POSITIVE)


class TestTestCase(unittest.TestCase):
    """Test TestCase dataclass."""

    def test_create_test_case(self) -> None:
        """Can create a test case."""
        bead = make_test_bead()
        case = TestCase(
            bead=bead,
            expected=ExpectedVerdict.TRUE_POSITIVE,
            rationale="It's vulnerable",
            source="manual review",
            vulnerability_class="reentrancy",
        )
        self.assertEqual(case.expected, ExpectedVerdict.TRUE_POSITIVE)
        self.assertEqual(case.rationale, "It's vulnerable")
        self.assertEqual(case.vulnerability_class, "reentrancy")

    def test_default_vulnerability_class(self) -> None:
        """Vulnerability class defaults to empty string."""
        bead = make_test_bead()
        case = TestCase(
            bead=bead,
            expected=ExpectedVerdict.FALSE_POSITIVE,
            rationale="Safe",
            source="audit",
        )
        self.assertEqual(case.vulnerability_class, "")


class TestLLMVerdict(unittest.TestCase):
    """Test LLMVerdict dataclass."""

    def test_create_verdict(self) -> None:
        """Can create an LLM verdict."""
        verdict = LLMVerdict(
            verdict=VerdictType.TRUE_POSITIVE,
            confidence=0.95,
            reasoning="Clear vulnerability",
            raw_response='{"verdict": "true_positive"}',
        )
        self.assertEqual(verdict.verdict, VerdictType.TRUE_POSITIVE)
        self.assertEqual(verdict.confidence, 0.95)
        self.assertIn("vulnerability", verdict.reasoning)


class TestTestResult(unittest.TestCase):
    """Test TestResult dataclass."""

    def test_correct_result(self) -> None:
        """Can create a correct result."""
        bead = make_test_bead()
        case = TestCase(
            bead=bead,
            expected=ExpectedVerdict.TRUE_POSITIVE,
            rationale="Vulnerable",
            source="review",
        )
        verdict = LLMVerdict(
            verdict=VerdictType.TRUE_POSITIVE,
            confidence=0.9,
            reasoning="Yes",
            raw_response="{}",
        )
        result = TestResult(
            test_case=case,
            llm_verdicts=[verdict],
            final_verdict=VerdictType.TRUE_POSITIVE,
            is_correct=True,
        )
        self.assertTrue(result.is_correct)

    def test_incorrect_result(self) -> None:
        """Can create an incorrect result."""
        bead = make_test_bead()
        case = TestCase(
            bead=bead,
            expected=ExpectedVerdict.TRUE_POSITIVE,
            rationale="Vulnerable",
            source="review",
        )
        result = TestResult(
            test_case=case,
            llm_verdicts=[],
            final_verdict=VerdictType.FALSE_POSITIVE,
            is_correct=False,
        )
        self.assertFalse(result.is_correct)


class TestAccuracyReport(unittest.TestCase):
    """Test AccuracyReport dataclass."""

    def make_report(
        self, correct: int = 3, total: int = 4
    ) -> AccuracyReport:
        """Create a test report."""
        results = []
        for i in range(total):
            bead = make_test_bead(f"test-{i}")
            is_tp = i % 2 == 0
            case = TestCase(
                bead=bead,
                expected=ExpectedVerdict.TRUE_POSITIVE if is_tp else ExpectedVerdict.FALSE_POSITIVE,
                rationale="Test",
                source="test",
                vulnerability_class="reentrancy",
            )
            is_correct = i < correct
            results.append(
                TestResult(
                    test_case=case,
                    llm_verdicts=[
                        LLMVerdict(
                            verdict=VerdictType.TRUE_POSITIVE if is_tp else VerdictType.FALSE_POSITIVE,
                            confidence=0.9,
                            reasoning="Test",
                            raw_response="{}",
                        )
                    ],
                    final_verdict=VerdictType.TRUE_POSITIVE if (is_tp == is_correct) else VerdictType.FALSE_POSITIVE,
                    is_correct=is_correct,
                )
            )

        return AccuracyReport(
            timestamp=datetime.now(),
            model="test-model",
            total_cases=total,
            correct_cases=correct,
            accuracy=correct / total if total > 0 else 0,
            results=results,
            config={"runs_per_bead": 3},
        )

    def test_to_dict(self) -> None:
        """Can convert report to dict."""
        report = self.make_report()
        data = report.to_dict()

        self.assertEqual(data["model"], "test-model")
        self.assertEqual(data["total_cases"], 4)
        self.assertEqual(data["correct_cases"], 3)
        self.assertAlmostEqual(data["accuracy"], 0.75)
        self.assertEqual(len(data["results"]), 4)

    def test_to_dict_serializable(self) -> None:
        """Report dict is JSON serializable."""
        report = self.make_report()
        data = report.to_dict()

        # Should not raise
        json_str = json.dumps(data)
        self.assertIn("test-model", json_str)

    def test_summary(self) -> None:
        """Can generate summary."""
        report = self.make_report()
        summary = report.summary()

        self.assertIn("LLM Verdict Accuracy Report", summary)
        self.assertIn("test-model", summary)
        self.assertIn("75.0%", summary)

    def test_summary_no_failures(self) -> None:
        """Summary handles no failures."""
        report = self.make_report(correct=4, total=4)
        summary = report.summary()

        self.assertIn("100.0%", summary)
        self.assertIn("None!", summary)  # No failures

    def test_breakdown_by_class(self) -> None:
        """Can get breakdown by vulnerability class."""
        report = self.make_report()
        breakdown = report.breakdown_by_class()

        self.assertIn("reentrancy", breakdown)
        self.assertEqual(breakdown["reentrancy"]["total"], 4)

    def test_breakdown_empty_class(self) -> None:
        """Handles empty vulnerability class."""
        bead = make_test_bead()
        case = TestCase(
            bead=bead,
            expected=ExpectedVerdict.TRUE_POSITIVE,
            rationale="Test",
            source="test",
            vulnerability_class="",  # Empty
        )
        result = TestResult(
            test_case=case,
            llm_verdicts=[],
            final_verdict=VerdictType.TRUE_POSITIVE,
            is_correct=True,
        )
        report = AccuracyReport(
            timestamp=datetime.now(),
            model="test",
            total_cases=1,
            correct_cases=1,
            accuracy=1.0,
            results=[result],
            config={},
        )

        breakdown = report.breakdown_by_class()
        self.assertIn("unknown", breakdown)


class TestBeadAccuracyTester(unittest.TestCase):
    """Test BeadAccuracyTester class."""

    def test_init(self) -> None:
        """Can initialize tester."""
        client = MagicMock()
        tester = BeadAccuracyTester(
            llm_client=client,
            model="test-model",
            runs_per_bead=3,
            temperature=0.0,
        )
        self.assertEqual(tester.model, "test-model")
        self.assertEqual(tester.runs_per_bead, 3)
        self.assertEqual(tester.temperature, 0.0)

    def test_parse_response_valid_json(self) -> None:
        """Can parse valid JSON response."""
        client = MagicMock()
        tester = BeadAccuracyTester(client)

        response = json.dumps(
            {
                "verdict": "true_positive",
                "confidence": 0.95,
                "reasoning": "Clear vulnerability pattern",
            }
        )

        verdict = tester._parse_response(response)
        self.assertEqual(verdict.verdict, VerdictType.TRUE_POSITIVE)
        self.assertEqual(verdict.confidence, 0.95)
        self.assertIn("vulnerability", verdict.reasoning)

    def test_parse_response_false_positive(self) -> None:
        """Can parse false positive verdict."""
        client = MagicMock()
        tester = BeadAccuracyTester(client)

        response = json.dumps(
            {
                "verdict": "false_positive",
                "confidence": 0.8,
                "reasoning": "Has protection",
            }
        )

        verdict = tester._parse_response(response)
        self.assertEqual(verdict.verdict, VerdictType.FALSE_POSITIVE)

    def test_parse_response_with_surrounding_text(self) -> None:
        """Can extract JSON from text with surrounding content."""
        client = MagicMock()
        tester = BeadAccuracyTester(client)

        response = """Here is my analysis:
        {"verdict": "true_positive", "confidence": 0.9, "reasoning": "Test"}
        Thank you for asking."""

        verdict = tester._parse_response(response)
        self.assertEqual(verdict.verdict, VerdictType.TRUE_POSITIVE)

    def test_parse_response_invalid_verdict(self) -> None:
        """Handles invalid verdict string."""
        client = MagicMock()
        tester = BeadAccuracyTester(client)

        response = json.dumps(
            {
                "verdict": "maybe",  # Invalid
                "confidence": 0.5,
                "reasoning": "Unsure",
            }
        )

        verdict = tester._parse_response(response)
        self.assertEqual(verdict.verdict, VerdictType.INCONCLUSIVE)

    def test_parse_response_invalid_json(self) -> None:
        """Handles invalid JSON."""
        client = MagicMock()
        tester = BeadAccuracyTester(client)

        response = "This is not JSON at all"

        verdict = tester._parse_response(response)
        self.assertEqual(verdict.verdict, VerdictType.INCONCLUSIVE)
        self.assertIn("Parse error", verdict.reasoning)

    def test_parse_response_missing_fields(self) -> None:
        """Handles missing fields with defaults."""
        client = MagicMock()
        tester = BeadAccuracyTester(client)

        response = json.dumps({"verdict": "true_positive"})

        verdict = tester._parse_response(response)
        self.assertEqual(verdict.verdict, VerdictType.TRUE_POSITIVE)
        self.assertEqual(verdict.confidence, 0.5)  # Default
        self.assertEqual(verdict.reasoning, "")  # Default

    def test_vote_majority_true_positive(self) -> None:
        """Vote returns majority verdict."""
        client = MagicMock()
        tester = BeadAccuracyTester(client)

        verdicts = [
            LLMVerdict(VerdictType.TRUE_POSITIVE, 0.9, "Test", "{}"),
            LLMVerdict(VerdictType.TRUE_POSITIVE, 0.8, "Test", "{}"),
            LLMVerdict(VerdictType.FALSE_POSITIVE, 0.7, "Test", "{}"),
        ]

        result = tester._vote(verdicts)
        self.assertEqual(result, VerdictType.TRUE_POSITIVE)

    def test_vote_majority_false_positive(self) -> None:
        """Vote returns majority for false positive."""
        client = MagicMock()
        tester = BeadAccuracyTester(client)

        verdicts = [
            LLMVerdict(VerdictType.FALSE_POSITIVE, 0.9, "Test", "{}"),
            LLMVerdict(VerdictType.FALSE_POSITIVE, 0.8, "Test", "{}"),
            LLMVerdict(VerdictType.TRUE_POSITIVE, 0.7, "Test", "{}"),
        ]

        result = tester._vote(verdicts)
        self.assertEqual(result, VerdictType.FALSE_POSITIVE)

    def test_vote_ignores_inconclusive(self) -> None:
        """Vote ignores INCONCLUSIVE when others available."""
        client = MagicMock()
        tester = BeadAccuracyTester(client)

        verdicts = [
            LLMVerdict(VerdictType.INCONCLUSIVE, 0.0, "Error", "{}"),
            LLMVerdict(VerdictType.TRUE_POSITIVE, 0.8, "Test", "{}"),
            LLMVerdict(VerdictType.INCONCLUSIVE, 0.0, "Error", "{}"),
        ]

        result = tester._vote(verdicts)
        self.assertEqual(result, VerdictType.TRUE_POSITIVE)

    def test_vote_all_inconclusive(self) -> None:
        """Vote returns INCONCLUSIVE when all are inconclusive."""
        client = MagicMock()
        tester = BeadAccuracyTester(client)

        verdicts = [
            LLMVerdict(VerdictType.INCONCLUSIVE, 0.0, "Error", "{}"),
            LLMVerdict(VerdictType.INCONCLUSIVE, 0.0, "Error", "{}"),
        ]

        result = tester._vote(verdicts)
        self.assertEqual(result, VerdictType.INCONCLUSIVE)

    def test_vote_tie_breaker(self) -> None:
        """Vote handles ties (max returns first max)."""
        client = MagicMock()
        tester = BeadAccuracyTester(client)

        verdicts = [
            LLMVerdict(VerdictType.TRUE_POSITIVE, 0.9, "Test", "{}"),
            LLMVerdict(VerdictType.FALSE_POSITIVE, 0.9, "Test", "{}"),
        ]

        # Either is acceptable - just verify it returns one of them
        result = tester._vote(verdicts)
        self.assertIn(result, [VerdictType.TRUE_POSITIVE, VerdictType.FALSE_POSITIVE])


class TestBeadAccuracyTesterAsync(unittest.TestCase):
    """Test async methods of BeadAccuracyTester."""

    def test_get_llm_verdict_success(self) -> None:
        """Can get LLM verdict successfully."""
        client = MagicMock()
        client.analyze = AsyncMock(
            return_value='{"verdict": "true_positive", "confidence": 0.9, "reasoning": "Test"}'
        )

        tester = BeadAccuracyTester(client)
        bead = make_test_bead()

        verdict = asyncio.run(tester._get_llm_verdict(bead))

        self.assertEqual(verdict.verdict, VerdictType.TRUE_POSITIVE)
        client.analyze.assert_called_once()

    def test_get_llm_verdict_error(self) -> None:
        """Handles LLM client error."""
        client = MagicMock()
        client.analyze = AsyncMock(side_effect=Exception("API Error"))

        tester = BeadAccuracyTester(client)
        bead = make_test_bead()

        verdict = asyncio.run(tester._get_llm_verdict(bead))

        self.assertEqual(verdict.verdict, VerdictType.INCONCLUSIVE)
        self.assertIn("Error", verdict.reasoning)

    def test_run_accuracy_test(self) -> None:
        """Can run full accuracy test."""
        client = MagicMock()
        # Return true_positive for all calls
        client.analyze = AsyncMock(
            return_value='{"verdict": "true_positive", "confidence": 0.95, "reasoning": "Vulnerable"}'
        )

        tester = BeadAccuracyTester(client, runs_per_bead=2)

        bead = make_test_bead()
        cases = [
            TestCase(
                bead=bead,
                expected=ExpectedVerdict.TRUE_POSITIVE,
                rationale="Test",
                source="test",
            )
        ]

        report = asyncio.run(tester.run_accuracy_test(cases))

        self.assertEqual(report.total_cases, 1)
        self.assertEqual(report.correct_cases, 1)
        self.assertEqual(report.accuracy, 1.0)
        # 2 runs per bead
        self.assertEqual(client.analyze.call_count, 2)

    def test_run_accuracy_test_incorrect(self) -> None:
        """Reports incorrect predictions."""
        client = MagicMock()
        # Return false_positive but we expect true_positive
        client.analyze = AsyncMock(
            return_value='{"verdict": "false_positive", "confidence": 0.8, "reasoning": "Looks safe"}'
        )

        tester = BeadAccuracyTester(client, runs_per_bead=1)

        bead = make_test_bead()
        cases = [
            TestCase(
                bead=bead,
                expected=ExpectedVerdict.TRUE_POSITIVE,
                rationale="Should be TP",
                source="test",
            )
        ]

        report = asyncio.run(tester.run_accuracy_test(cases))

        self.assertEqual(report.total_cases, 1)
        self.assertEqual(report.correct_cases, 0)
        self.assertEqual(report.accuracy, 0.0)
        self.assertFalse(report.results[0].is_correct)

    def test_run_accuracy_test_sync(self) -> None:
        """Can use sync wrapper."""
        client = MagicMock()
        client.analyze = AsyncMock(
            return_value='{"verdict": "true_positive", "confidence": 0.9, "reasoning": "Test"}'
        )

        tester = BeadAccuracyTester(client, runs_per_bead=1)

        bead = make_test_bead()
        cases = [
            TestCase(
                bead=bead,
                expected=ExpectedVerdict.TRUE_POSITIVE,
                rationale="Test",
                source="test",
            )
        ]

        # Use sync wrapper
        report = tester.run_accuracy_test_sync(cases)

        self.assertEqual(report.total_cases, 1)


class TestLoadTestCases(unittest.TestCase):
    """Test load_test_cases function."""

    def test_load_test_cases(self) -> None:
        """Can load test cases from JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create bead file
            bead = make_test_bead("load-test-001")
            bead_path = tmppath / "test_bead.json"
            with open(bead_path, "w") as f:
                json.dump(bead.to_dict(), f)

            # Create ground truth file
            gt_data = {
                "cases": [
                    {
                        "bead_path": "test_bead.json",
                        "expected": "true_positive",
                        "rationale": "Test rationale",
                        "source": "test source",
                        "vulnerability_class": "reentrancy",
                    }
                ]
            }
            gt_path = tmppath / "ground_truth.json"
            with open(gt_path, "w") as f:
                json.dump(gt_data, f)

            # Load
            cases = load_test_cases(gt_path)

            self.assertEqual(len(cases), 1)
            self.assertEqual(cases[0].bead.id, "load-test-001")
            self.assertEqual(cases[0].expected, ExpectedVerdict.TRUE_POSITIVE)
            self.assertEqual(cases[0].rationale, "Test rationale")
            self.assertEqual(cases[0].vulnerability_class, "reentrancy")

    def test_load_test_cases_default_vulnerability_class(self) -> None:
        """Uses bead's vulnerability class if not specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            bead = make_test_bead("load-test-002", vulnerability_class="access_control")
            bead_path = tmppath / "test_bead.json"
            with open(bead_path, "w") as f:
                json.dump(bead.to_dict(), f)

            gt_data = {
                "cases": [
                    {
                        "bead_path": "test_bead.json",
                        "expected": "false_positive",
                        # No vulnerability_class specified
                    }
                ]
            }
            gt_path = tmppath / "ground_truth.json"
            with open(gt_path, "w") as f:
                json.dump(gt_data, f)

            cases = load_test_cases(gt_path)

            # Should use bead's class
            self.assertEqual(cases[0].vulnerability_class, "access_control")

    def test_load_multiple_cases(self) -> None:
        """Can load multiple test cases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create beads
            for i in range(3):
                bead = make_test_bead(f"multi-{i}")
                with open(tmppath / f"bead_{i}.json", "w") as f:
                    json.dump(bead.to_dict(), f)

            gt_data = {
                "cases": [
                    {"bead_path": "bead_0.json", "expected": "true_positive"},
                    {"bead_path": "bead_1.json", "expected": "false_positive"},
                    {"bead_path": "bead_2.json", "expected": "true_positive"},
                ]
            }
            with open(tmppath / "gt.json", "w") as f:
                json.dump(gt_data, f)

            cases = load_test_cases(tmppath / "gt.json")

            self.assertEqual(len(cases), 3)
            self.assertEqual(cases[1].expected, ExpectedVerdict.FALSE_POSITIVE)


class TestCreateTestCase(unittest.TestCase):
    """Test create_test_case helper."""

    def test_create_test_case_helper(self) -> None:
        """Can create test case with helper."""
        bead = make_test_bead(vulnerability_class="oracle")

        case = create_test_case(
            bead=bead,
            expected="true_positive",
            rationale="Missing price check",
            source="audit report",
        )

        self.assertEqual(case.expected, ExpectedVerdict.TRUE_POSITIVE)
        self.assertEqual(case.rationale, "Missing price check")
        self.assertEqual(case.source, "audit report")
        self.assertEqual(case.vulnerability_class, "oracle")  # From bead

    def test_create_test_case_false_positive(self) -> None:
        """Can create false positive test case."""
        bead = make_test_bead()

        case = create_test_case(
            bead=bead,
            expected="false_positive",
            rationale="Has proper guard",
        )

        self.assertEqual(case.expected, ExpectedVerdict.FALSE_POSITIVE)


class TestAnalyzeFailures(unittest.TestCase):
    """Test analyze_failures function."""

    def test_analyze_no_failures(self) -> None:
        """Handles no failures."""
        report = AccuracyReport(
            timestamp=datetime.now(),
            model="test",
            total_cases=2,
            correct_cases=2,
            accuracy=1.0,
            results=[
                TestResult(
                    test_case=TestCase(
                        bead=make_test_bead("ok-1"),
                        expected=ExpectedVerdict.TRUE_POSITIVE,
                        rationale="Test",
                        source="test",
                    ),
                    llm_verdicts=[],
                    final_verdict=VerdictType.TRUE_POSITIVE,
                    is_correct=True,
                ),
            ],
            config={},
        )

        analysis = analyze_failures(report)
        self.assertIn("No failures", analysis)

    def test_analyze_with_failures(self) -> None:
        """Analyzes failures correctly."""
        report = AccuracyReport(
            timestamp=datetime.now(),
            model="test",
            total_cases=2,
            correct_cases=1,
            accuracy=0.5,
            results=[
                TestResult(
                    test_case=TestCase(
                        bead=make_test_bead("fail-1"),
                        expected=ExpectedVerdict.TRUE_POSITIVE,
                        rationale="Should be vulnerable",
                        source="test",
                    ),
                    llm_verdicts=[
                        LLMVerdict(
                            verdict=VerdictType.FALSE_POSITIVE,
                            confidence=0.8,
                            reasoning="I think it's safe because of the guard",
                            raw_response="{}",
                        )
                    ],
                    final_verdict=VerdictType.FALSE_POSITIVE,
                    is_correct=False,  # Expected TP, got FP
                ),
            ],
            config={},
        )

        analysis = analyze_failures(report)

        self.assertIn("Failure Analysis", analysis)
        self.assertIn("fail-1", analysis)
        self.assertIn("true_positive", analysis)
        self.assertIn("false_positive", analysis)
        self.assertIn("Should be vulnerable", analysis)
        self.assertIn("safe because of the guard", analysis)

    def test_analyze_failure_types(self) -> None:
        """Categorizes failure types correctly."""
        bead1 = make_test_bead("missed-tp")
        bead2 = make_test_bead("false-fp")

        report = AccuracyReport(
            timestamp=datetime.now(),
            model="test",
            total_cases=2,
            correct_cases=0,
            accuracy=0.0,
            results=[
                TestResult(
                    test_case=TestCase(
                        bead=bead1,
                        expected=ExpectedVerdict.TRUE_POSITIVE,
                        rationale="Missed",
                        source="test",
                    ),
                    llm_verdicts=[],
                    final_verdict=VerdictType.FALSE_POSITIVE,
                    is_correct=False,
                ),
                TestResult(
                    test_case=TestCase(
                        bead=bead2,
                        expected=ExpectedVerdict.FALSE_POSITIVE,
                        rationale="Wrong",
                        source="test",
                    ),
                    llm_verdicts=[],
                    final_verdict=VerdictType.TRUE_POSITIVE,
                    is_correct=False,
                ),
            ],
            config={},
        )

        analysis = analyze_failures(report)

        self.assertIn("Missed TPs (should have confirmed): 1", analysis)
        self.assertIn("False FPs (wrongly rejected): 1", analysis)


class TestIntegrationWithFixtures(unittest.TestCase):
    """Test loading actual fixtures."""

    def test_load_ground_truth_fixtures(self) -> None:
        """Can load the ground truth fixtures we created."""
        fixture_path = Path(__file__).parent / "fixtures" / "bead_ground_truth.json"

        if not fixture_path.exists():
            self.skipTest("Ground truth fixtures not found")

        cases = load_test_cases(fixture_path)

        self.assertEqual(len(cases), 4)

        # Check expected verdicts
        expected_verdicts = {
            "VKG-GT-001": ExpectedVerdict.TRUE_POSITIVE,  # reentrancy-vulnerable
            "VKG-GT-002": ExpectedVerdict.FALSE_POSITIVE,  # reentrancy-guarded
            "VKG-GT-003": ExpectedVerdict.TRUE_POSITIVE,  # access-control-missing
            "VKG-GT-004": ExpectedVerdict.FALSE_POSITIVE,  # access-control-protected
        }

        for case in cases:
            if case.bead.id in expected_verdicts:
                self.assertEqual(
                    case.expected,
                    expected_verdicts[case.bead.id],
                    f"Wrong expected verdict for {case.bead.id}",
                )


if __name__ == "__main__":
    unittest.main()
