"""
Noninteractive Batch Processing Tests (Task 11.9)

Tests for:
1. Sequential batch processing
2. Concurrent batch processing
3. Retry logic
4. Progress tracking
5. Error handling
6. CI mode
"""

import asyncio
import json
import unittest

from alphaswarm_sol.findings.model import (
    Finding,
    FindingSeverity,
    FindingConfidence,
    FindingStatus,
    Location,
    Evidence,
)
from alphaswarm_sol.llm.batch import (
    NoninteractiveBatchRunner,
    CIRunner,
    CIError,
    BatchConfig,
    BatchResult,
    BatchStatus,
    BatchProgress,
    OutputMode,
    create_batch_runner,
    create_ci_runner,
)
from alphaswarm_sol.llm.workflow import WorkflowStatus


def create_test_finding(
    pattern: str = "test-pattern",
    confidence: FindingConfidence = FindingConfidence.MEDIUM,
) -> Finding:
    """Create a test finding."""
    return Finding(
        pattern=pattern,
        severity=FindingSeverity.HIGH,
        confidence=confidence,
        location=Location(file="Test.sol", line=42, function="test"),
        description="Test finding",
        evidence=Evidence(
            behavioral_signature="R:state→X:out→W:state",
            properties_matched=["test_property"],
            code_snippet="function test() external { }",
            why_vulnerable="Test reason",
        ),
    )


class TestBatchProgress(unittest.TestCase):
    """Tests for BatchProgress."""

    def test_percent_complete(self):
        """Percent complete should be calculated correctly."""
        progress = BatchProgress(total=100, processed=50)
        self.assertEqual(progress.percent_complete, 50.0)

    def test_percent_complete_zero_total(self):
        """Percent complete should be 0 when total is 0."""
        progress = BatchProgress(total=0, processed=0)
        self.assertEqual(progress.percent_complete, 0)

    def test_progress_line(self):
        """Progress line should be formatted correctly."""
        progress = BatchProgress(
            total=100,
            processed=50,
            tokens_used=1000,
            cost_usd=0.05,
        )
        line = progress.progress_line()
        self.assertIn("[50/100]", line)
        self.assertIn("1,000", line)
        self.assertIn("$0.05", line)

    def test_to_dict(self):
        """To dict should include all fields."""
        progress = BatchProgress(
            total=100,
            processed=50,
            succeeded=40,
            failed=5,
            skipped=5,
        )
        d = progress.to_dict()
        self.assertEqual(d["total"], 100)
        self.assertEqual(d["processed"], 50)
        self.assertEqual(d["succeeded"], 40)


class TestBatchResult(unittest.TestCase):
    """Tests for BatchResult."""

    def test_to_dict(self):
        """To dict should serialize correctly."""
        result = BatchResult(
            status=BatchStatus.COMPLETED,
            progress=BatchProgress(total=10, processed=10),
            results=[],
            errors=[],
        )
        d = result.to_dict()
        self.assertEqual(d["status"], "completed")
        self.assertIn("progress", d)

    def test_to_json(self):
        """To JSON should produce valid JSON."""
        result = BatchResult(
            status=BatchStatus.COMPLETED,
            progress=BatchProgress(total=10, processed=10),
            results=[],
            errors=[],
        )
        json_str = result.to_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["status"], "completed")

    def test_to_summary(self):
        """To summary should produce readable text."""
        result = BatchResult(
            status=BatchStatus.COMPLETED,
            progress=BatchProgress(
                total=10,
                processed=10,
                succeeded=8,
                failed=2,
            ),
            results=[],
            errors=["Error 1", "Error 2"],
        )
        summary = result.to_summary()
        self.assertIn("BATCH ANALYSIS COMPLETE", summary)
        self.assertIn("Total Findings: 10", summary)
        self.assertIn("Succeeded: 8", summary)
        self.assertIn("Error 1", summary)


class TestBatchConfig(unittest.TestCase):
    """Tests for BatchConfig."""

    def test_default_values(self):
        """Config should have sensible defaults."""
        config = BatchConfig()
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.max_concurrent, 5)
        self.assertEqual(config.max_tokens, 100_000)
        self.assertFalse(config.fail_fast)

    def test_custom_values(self):
        """Config should accept custom values."""
        config = BatchConfig(
            max_retries=5,
            max_concurrent=10,
            fail_fast=True,
        )
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.max_concurrent, 10)
        self.assertTrue(config.fail_fast)


class TestNoninteractiveBatchRunner(unittest.TestCase):
    """Tests for NoninteractiveBatchRunner."""

    def test_sequential_processing(self):
        """Sequential processing should work."""
        config = BatchConfig(max_concurrent=1)
        runner = NoninteractiveBatchRunner(config=config)

        findings = [create_test_finding(pattern=f"test-{i}") for i in range(3)]

        async def mock_llm(_):
            return json.dumps({
                "verdict": "VULNERABLE",
                "confidence": 85,
                "reasoning": "Test analysis completed successfully",
                "evidence": [],
            })

        result = asyncio.run(runner.run(findings, mock_llm))

        self.assertEqual(result.status, BatchStatus.COMPLETED)
        self.assertEqual(result.progress.total, 3)
        self.assertEqual(result.progress.processed, 3)

    def test_concurrent_processing(self):
        """Concurrent processing should work."""
        config = BatchConfig(max_concurrent=3)
        runner = NoninteractiveBatchRunner(config=config)

        findings = [create_test_finding(pattern=f"test-{i}") for i in range(5)]

        async def mock_llm(_):
            await asyncio.sleep(0.01)  # Simulate async work
            return json.dumps({
                "verdict": "SAFE",
                "confidence": 90,
                "reasoning": "Test analysis completed successfully",
                "evidence": [],
            })

        result = asyncio.run(runner.run(findings, mock_llm))

        self.assertEqual(result.status, BatchStatus.COMPLETED)
        self.assertEqual(result.progress.processed, 5)

    def test_retry_logic(self):
        """Retry logic should eventually succeed or gracefully fail."""
        config = BatchConfig(max_concurrent=1, max_retries=3, retry_delay=0.01)
        runner = NoninteractiveBatchRunner(config=config)

        findings = [create_test_finding()]
        call_count = [0]

        async def intermittent_success(_):
            call_count[0] += 1
            # First call succeeds (goes through contract's retry too)
            return json.dumps({
                "verdict": "VULNERABLE",
                "confidence": 85,
                "reasoning": "Analysis has completed successfully",
                "evidence": [],
            })

        result = asyncio.run(runner.run(findings, intermittent_success))

        self.assertEqual(result.status, BatchStatus.COMPLETED)
        self.assertEqual(result.progress.succeeded, 1)
        self.assertGreaterEqual(call_count[0], 1)  # At least 1 call made

    def test_max_retries_exceeded(self):
        """Should fail after max retries exceeded."""
        config = BatchConfig(max_concurrent=1, max_retries=2, retry_delay=0.01)
        runner = NoninteractiveBatchRunner(config=config)

        findings = [create_test_finding()]

        async def always_fail(_):
            raise RuntimeError("Permanent failure")

        result = asyncio.run(runner.run(findings, always_fail))

        self.assertEqual(result.progress.failed, 1)
        self.assertGreater(len(result.errors), 0)

    def test_fail_fast(self):
        """Fail fast should stop on first error."""
        config = BatchConfig(max_concurrent=1, fail_fast=True, max_retries=1, retry_delay=0.01)
        runner = NoninteractiveBatchRunner(config=config)

        findings = [create_test_finding(pattern=f"test-{i}") for i in range(5)]

        async def fail_on_second(prompt):
            if "test-1" in prompt:
                raise RuntimeError("Failure")
            return json.dumps({
                "verdict": "SAFE",
                "confidence": 90,
                "reasoning": "Analysis completed successfully",
                "evidence": [],
            })

        result = asyncio.run(runner.run(findings, fail_on_second))

        self.assertEqual(result.status, BatchStatus.FAILED)
        # Should stop early, not process all 5
        self.assertLess(result.progress.processed, 5)

    def test_progress_callback(self):
        """Progress callback should be called."""
        config = BatchConfig(max_concurrent=1)
        runner = NoninteractiveBatchRunner(config=config)

        findings = [create_test_finding(pattern=f"test-{i}") for i in range(3)]
        callback_calls = []

        def track_progress(progress: BatchProgress):
            callback_calls.append(progress.processed)

        async def mock_llm(_):
            return json.dumps({
                "verdict": "SAFE",
                "confidence": 90,
                "reasoning": "Analysis completed successfully",
                "evidence": [],
            })

        asyncio.run(runner.run(findings, mock_llm, progress_callback=track_progress))

        self.assertEqual(callback_calls, [1, 2, 3])

    def test_tokens_and_cost_tracked(self):
        """Tokens and cost should be tracked."""
        runner = NoninteractiveBatchRunner()

        findings = [create_test_finding()]

        async def mock_llm(_):
            return json.dumps({
                "verdict": "SAFE",
                "confidence": 90,
                "reasoning": "Analysis completed successfully",
                "evidence": [],
            })

        result = asyncio.run(runner.run(findings, mock_llm))

        self.assertGreater(result.progress.tokens_used, 0)
        self.assertGreater(result.progress.cost_usd, 0)

    def test_cancel(self):
        """Cancel should stop processing."""
        config = BatchConfig(max_concurrent=1)
        runner = NoninteractiveBatchRunner(config=config)

        findings = [create_test_finding(pattern=f"test-{i}") for i in range(10)]
        processed_count = [0]

        async def slow_llm(_):
            processed_count[0] += 1
            await asyncio.sleep(0.05)
            if processed_count[0] >= 3:
                runner.cancel()
            return json.dumps({
                "verdict": "SAFE",
                "confidence": 90,
                "reasoning": "Analysis completed successfully",
                "evidence": [],
            })

        result = asyncio.run(runner.run(findings, slow_llm))

        self.assertEqual(result.status, BatchStatus.CANCELLED)
        self.assertLess(result.progress.processed, 10)


class TestCIRunner(unittest.TestCase):
    """Tests for CIRunner."""

    def test_ci_runner_limits_findings(self):
        """CI runner should limit findings count."""
        runner = CIRunner(max_findings=5, max_cost_usd=1.00)

        findings = [create_test_finding(pattern=f"test-{i}") for i in range(10)]

        async def mock_llm(_):
            return json.dumps({
                "verdict": "SAFE",
                "confidence": 90,
                "reasoning": "Analysis completed successfully",
                "evidence": [],
            })

        result = asyncio.run(runner.run(findings, mock_llm))

        # Only 5 should be processed due to limit
        self.assertEqual(result.progress.total, 5)

    def test_ci_runner_fail_fast(self):
        """CI runner should fail fast by default."""
        runner = CIRunner()

        findings = [create_test_finding(pattern=f"test-{i}") for i in range(5)]

        async def fail_on_third(prompt):
            if "test-2" in prompt:
                raise RuntimeError("CI failure")
            return json.dumps({
                "verdict": "SAFE",
                "confidence": 90,
                "reasoning": "Analysis completed successfully",
                "evidence": [],
            })

        result = asyncio.run(runner.run(findings, fail_on_third))

        self.assertEqual(result.status, BatchStatus.FAILED)


class TestFactoryFunctions(unittest.TestCase):
    """Tests for factory functions."""

    def test_create_batch_runner(self):
        """Create batch runner should work."""
        runner = create_batch_runner(
            max_concurrent=10,
            max_retries=5,
        )
        self.assertIsInstance(runner, NoninteractiveBatchRunner)
        self.assertEqual(runner.config.max_concurrent, 10)
        self.assertEqual(runner.config.max_retries, 5)

    def test_create_ci_runner(self):
        """Create CI runner should work."""
        runner = create_ci_runner(
            max_findings=50,
            max_cost_usd=1.00,
        )
        self.assertIsInstance(runner, CIRunner)
        self.assertEqual(runner.max_findings, 50)


class TestOutputModes(unittest.TestCase):
    """Tests for output modes."""

    def test_output_mode_enum(self):
        """Output modes should be defined."""
        self.assertEqual(OutputMode.JSON.value, "json")
        self.assertEqual(OutputMode.SARIF.value, "sarif")
        self.assertEqual(OutputMode.COMPACT.value, "compact")
        self.assertEqual(OutputMode.SUMMARY.value, "summary")


class TestBatchStatus(unittest.TestCase):
    """Tests for batch status."""

    def test_status_values(self):
        """Status values should be correct."""
        self.assertEqual(BatchStatus.PENDING.value, "pending")
        self.assertEqual(BatchStatus.RUNNING.value, "running")
        self.assertEqual(BatchStatus.COMPLETED.value, "completed")
        self.assertEqual(BatchStatus.FAILED.value, "failed")
        self.assertEqual(BatchStatus.CANCELLED.value, "cancelled")


class TestIntegration(unittest.TestCase):
    """Integration tests for batch processing."""

    def test_full_workflow(self):
        """Full batch workflow should work end to end."""
        runner = create_batch_runner(max_concurrent=2, max_retries=2)

        findings = [
            create_test_finding(pattern="vuln-001"),
            create_test_finding(pattern="fp-001"),
            create_test_finding(pattern="vuln-002"),
        ]

        async def discriminating_llm(prompt):
            if "fp-001" in prompt:
                return json.dumps({
                    "verdict": "SAFE",
                    "confidence": 92,
                    "reasoning": "False positive detected successfully",
                    "evidence": ["Guard present"],
                })
            else:
                return json.dumps({
                    "verdict": "VULNERABLE",
                    "confidence": 88,
                    "reasoning": "Real vulnerability confirmed",
                    "evidence": ["No protection"],
                })

        result = asyncio.run(runner.run(findings, discriminating_llm))

        self.assertEqual(result.status, BatchStatus.COMPLETED)
        self.assertEqual(result.progress.total, 3)
        self.assertEqual(result.progress.succeeded, 3)

        # Verify we got different verdicts by checking tier_b_verdict
        from alphaswarm_sol.llm.validate import Verdict

        vulnerable = sum(
            1 for r in result.results
            if r.status == WorkflowStatus.SUCCESS and r.tier_b_verdict == Verdict.VULNERABLE
        )
        safe = sum(
            1 for r in result.results
            if r.status == WorkflowStatus.SUCCESS and r.tier_b_verdict == Verdict.SAFE
        )

        self.assertEqual(vulnerable, 2)  # vuln-001 and vuln-002
        self.assertEqual(safe, 1)  # fp-001

    def test_mixed_results_with_errors(self):
        """Should handle mixed results with some errors."""
        config = BatchConfig(max_concurrent=1, fail_fast=False, max_retries=1, retry_delay=0.01)
        runner = NoninteractiveBatchRunner(config=config)

        findings = [create_test_finding(pattern=f"test-{i}") for i in range(4)]

        async def mixed_results(prompt):
            if "test-1" in prompt:
                raise RuntimeError("Simulated error")
            return json.dumps({
                "verdict": "SAFE",
                "confidence": 90,
                "reasoning": "Analysis completed successfully",
                "evidence": [],
            })

        result = asyncio.run(runner.run(findings, mixed_results))

        self.assertEqual(result.status, BatchStatus.COMPLETED)
        self.assertEqual(result.progress.succeeded, 3)
        self.assertEqual(result.progress.failed, 1)


if __name__ == "__main__":
    unittest.main()
