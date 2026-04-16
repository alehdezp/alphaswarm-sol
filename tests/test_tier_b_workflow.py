"""
Tier B Analysis Workflow Tests (Task 11.3)

Tests for:
1. Confidence evaluation and routing
2. Auto-confirm high confidence
3. Auto-dismiss low confidence
4. Middle-range Tier B analysis
5. Workflow statistics
"""

import asyncio
import json
import unittest

from alphaswarm_sol.findings.model import (
    Finding,
    FindingSeverity,
    FindingConfidence,
    FindingStatus,
    FindingTier,
    Location,
    Evidence,
)
from alphaswarm_sol.llm.confidence import (
    ConfidenceEvaluator,
    ConfidenceResult,
    ConfidenceAction,
    ConfidenceThresholds,
    evaluate_confidence,
    needs_tier_b_analysis,
    CONFIDENCE_TO_NUMERIC,
)
from alphaswarm_sol.llm.workflow import (
    TierBWorkflow,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStats,
    create_tier_b_workflow,
)
from alphaswarm_sol.llm.validate import Verdict


def create_test_finding(
    pattern: str = "test-pattern",
    confidence: FindingConfidence = FindingConfidence.MEDIUM,
    has_evidence: bool = True,
) -> Finding:
    """Create a test finding."""
    evidence = Evidence()
    if has_evidence:
        evidence = Evidence(
            behavioral_signature="R:bal→X:out→W:bal",
            properties_matched=["state_write_after_external_call"],
            code_snippet="function withdraw() external {}",
            why_vulnerable="External call before state update",
            attack_scenario=["1. Call withdraw", "2. Re-enter"],
        )

    return Finding(
        pattern=pattern,
        severity=FindingSeverity.HIGH,
        confidence=confidence,
        location=Location(file="Test.sol", line=42, function="withdraw"),
        description="Test vulnerability",
        evidence=evidence,
    )


class TestConfidenceEvaluator(unittest.TestCase):
    """Tests for ConfidenceEvaluator."""

    def setUp(self):
        self.evaluator = ConfidenceEvaluator()

    def test_high_confidence_auto_confirms(self):
        """High confidence findings should auto-confirm."""
        finding = create_test_finding(confidence=FindingConfidence.HIGH)
        result = self.evaluator.evaluate(finding)

        self.assertEqual(result.action, ConfidenceAction.AUTO_CONFIRM)
        self.assertTrue(result.skip_tier_b)
        self.assertGreaterEqual(result.numeric_confidence, 0.9)

    def test_low_confidence_auto_dismisses(self):
        """Low confidence findings without evidence should auto-dismiss."""
        finding = create_test_finding(
            confidence=FindingConfidence.LOW,
            has_evidence=False,
        )
        result = self.evaluator.evaluate(finding)

        self.assertEqual(result.action, ConfidenceAction.AUTO_DISMISS)
        self.assertTrue(result.skip_tier_b)
        self.assertLessEqual(result.numeric_confidence, 0.3)

    def test_medium_confidence_goes_to_tier_b(self):
        """Medium confidence findings should go to Tier B."""
        finding = create_test_finding(confidence=FindingConfidence.MEDIUM)
        result = self.evaluator.evaluate(finding)

        self.assertEqual(result.action, ConfidenceAction.ANALYZE)
        self.assertFalse(result.skip_tier_b)

    def test_evidence_boosts_confidence(self):
        """Evidence should boost confidence score."""
        finding_with = create_test_finding(
            confidence=FindingConfidence.MEDIUM,
            has_evidence=True,
        )
        finding_without = create_test_finding(
            confidence=FindingConfidence.MEDIUM,
            has_evidence=False,
        )

        result_with = self.evaluator.evaluate(finding_with)
        result_without = self.evaluator.evaluate(finding_without)

        self.assertGreater(
            result_with.numeric_confidence,
            result_without.numeric_confidence,
        )

    def test_always_analyze_patterns(self):
        """Certain patterns should always go to Tier B."""
        finding = create_test_finding(
            pattern="business-logic-001",
            confidence=FindingConfidence.HIGH,
        )
        result = self.evaluator.evaluate(finding)

        self.assertEqual(result.action, ConfidenceAction.ANALYZE)
        self.assertFalse(result.skip_tier_b)
        self.assertIn("always requires Tier B", result.reason)

    def test_access_control_always_analyzed(self):
        """Access control patterns should always be analyzed."""
        finding = create_test_finding(
            pattern="access-control-missing",
            confidence=FindingConfidence.HIGH,
        )
        result = self.evaluator.evaluate(finding)

        self.assertEqual(result.action, ConfidenceAction.ANALYZE)

    def test_custom_thresholds(self):
        """Custom thresholds should be respected."""
        thresholds = ConfidenceThresholds(
            auto_confirm_threshold=0.99,  # Very high threshold
            auto_dismiss_threshold=0.2,
        )
        evaluator = ConfidenceEvaluator(thresholds)

        # High confidence without evidence (0.85 base - evidence penalties < 0.99)
        finding = create_test_finding(confidence=FindingConfidence.HIGH, has_evidence=False)
        result = evaluator.evaluate(finding)

        # Should go to Tier B because without evidence, confidence is below 0.99 threshold
        self.assertEqual(result.action, ConfidenceAction.ANALYZE)


class TestConfidenceConvenienceFunctions(unittest.TestCase):
    """Tests for convenience functions."""

    def test_evaluate_confidence(self):
        """evaluate_confidence should work correctly."""
        finding = create_test_finding(confidence=FindingConfidence.MEDIUM)
        result = evaluate_confidence(finding)

        self.assertIsInstance(result, ConfidenceResult)
        self.assertIsInstance(result.action, ConfidenceAction)

    def test_needs_tier_b_analysis(self):
        """needs_tier_b_analysis should return correct boolean."""
        high_conf = create_test_finding(confidence=FindingConfidence.HIGH)
        medium_conf = create_test_finding(confidence=FindingConfidence.MEDIUM)

        self.assertFalse(needs_tier_b_analysis(high_conf))
        self.assertTrue(needs_tier_b_analysis(medium_conf))


class TestConfidenceBatchEvaluate(unittest.TestCase):
    """Tests for batch evaluation."""

    def test_batch_evaluate(self):
        """Batch evaluation should return stats."""
        evaluator = ConfidenceEvaluator()
        findings = [
            create_test_finding(confidence=FindingConfidence.HIGH),
            create_test_finding(confidence=FindingConfidence.MEDIUM),
            create_test_finding(confidence=FindingConfidence.LOW, has_evidence=False),
        ]

        result = evaluator.batch_evaluate(findings)

        self.assertEqual(result["stats"]["total"], 3)
        self.assertIn("auto_confirm", result["stats"])
        self.assertIn("tier_b_required", result["stats"])


class TestTierBWorkflow(unittest.TestCase):
    """Tests for TierBWorkflow."""

    def setUp(self):
        self.workflow = TierBWorkflow(strict_mode=False)

    def test_auto_confirm_skips_llm(self):
        """High confidence should skip LLM call."""
        finding = create_test_finding(confidence=FindingConfidence.HIGH)

        async def mock_llm(_):
            raise AssertionError("LLM should not be called")

        result = asyncio.run(self.workflow.analyze_finding(finding, mock_llm))

        self.assertEqual(result.status, WorkflowStatus.SKIPPED_HIGH_CONFIDENCE)
        self.assertIsNone(result.tier_b_verdict)

    def test_auto_dismiss_skips_llm(self):
        """Low confidence should skip LLM call."""
        finding = create_test_finding(
            confidence=FindingConfidence.LOW,
            has_evidence=False,
        )

        async def mock_llm(_):
            raise AssertionError("LLM should not be called")

        result = asyncio.run(self.workflow.analyze_finding(finding, mock_llm))

        self.assertEqual(result.status, WorkflowStatus.SKIPPED_LOW_CONFIDENCE)

    def test_medium_confidence_calls_llm(self):
        """Medium confidence should call LLM."""
        finding = create_test_finding(confidence=FindingConfidence.MEDIUM)

        llm_called = [False]

        async def mock_llm(_):
            llm_called[0] = True
            return json.dumps({
                "verdict": "VULNERABLE",
                "confidence": 85,
                "reasoning": "Classic reentrancy pattern detected.",
                "evidence": ["line 42: external call before state update"],
            })

        result = asyncio.run(self.workflow.analyze_finding(finding, mock_llm))

        self.assertTrue(llm_called[0])
        self.assertEqual(result.status, WorkflowStatus.SUCCESS)
        self.assertEqual(result.tier_b_verdict, Verdict.VULNERABLE)
        self.assertEqual(result.tier_b_confidence, 85)

    def test_llm_safe_verdict(self):
        """LLM returning SAFE should be captured."""
        finding = create_test_finding(confidence=FindingConfidence.MEDIUM)

        async def mock_llm(_):
            return json.dumps({
                "verdict": "SAFE",
                "confidence": 90,
                "reasoning": "Function has proper reentrancy guard.",
                "evidence": ["line 40: nonReentrant modifier"],
            })

        result = asyncio.run(self.workflow.analyze_finding(finding, mock_llm))

        self.assertEqual(result.tier_b_verdict, Verdict.SAFE)
        self.assertEqual(result.tier_b_confidence, 90)
        self.assertIn("reentrancy guard", result.tier_b_reasoning)

    def test_llm_uncertain_verdict(self):
        """LLM returning UNCERTAIN should be captured."""
        finding = create_test_finding(confidence=FindingConfidence.MEDIUM)

        async def mock_llm(_):
            return json.dumps({
                "verdict": "UNCERTAIN",
                "confidence": 50,
                "reasoning": "Need more context about the caller.",
                "evidence": ["line 42: external call"],
            })

        result = asyncio.run(self.workflow.analyze_finding(finding, mock_llm))

        self.assertEqual(result.tier_b_verdict, Verdict.UNCERTAIN)

    def test_llm_error_handled(self):
        """LLM errors should be handled gracefully."""
        finding = create_test_finding(confidence=FindingConfidence.MEDIUM)

        async def mock_llm_error(_):
            raise RuntimeError("API connection failed")

        result = asyncio.run(self.workflow.analyze_finding(finding, mock_llm_error))

        # Contract catches exception and retries, returning validation error after exhausting retries
        self.assertIn(result.status, [WorkflowStatus.LLM_ERROR, WorkflowStatus.VALIDATION_ERROR])

    def test_invalid_response_handled(self):
        """Invalid LLM responses should be handled."""
        finding = create_test_finding(confidence=FindingConfidence.MEDIUM)

        async def mock_llm_invalid(_):
            return "not valid json"

        result = asyncio.run(self.workflow.analyze_finding(finding, mock_llm_invalid))

        # Should get ERROR verdict or validation error status
        self.assertIn(result.status, [
            WorkflowStatus.VALIDATION_ERROR,
            WorkflowStatus.SUCCESS,
        ])
        if result.status == WorkflowStatus.SUCCESS:
            self.assertEqual(result.tier_b_verdict, Verdict.ERROR)


class TestWorkflowBatch(unittest.TestCase):
    """Tests for batch workflow processing."""

    def test_batch_analyze(self):
        """Batch analysis should process all findings."""
        workflow = TierBWorkflow(strict_mode=False)

        findings = [
            create_test_finding(confidence=FindingConfidence.HIGH),
            create_test_finding(confidence=FindingConfidence.MEDIUM),
            create_test_finding(confidence=FindingConfidence.LOW, has_evidence=False),
        ]

        async def mock_llm(_):
            return json.dumps({
                "verdict": "VULNERABLE",
                "confidence": 80,
                "reasoning": "Vulnerability confirmed.",
                "evidence": ["evidence"],
            })

        results, stats = asyncio.run(workflow.analyze_batch(findings, mock_llm))

        self.assertEqual(len(results), 3)
        self.assertEqual(stats.total_findings, 3)
        self.assertEqual(stats.skipped_high_confidence, 1)
        self.assertEqual(stats.skipped_low_confidence, 1)
        self.assertEqual(stats.tier_b_analyzed, 1)

    def test_batch_stats(self):
        """Batch stats should be calculated correctly."""
        workflow = TierBWorkflow(strict_mode=False)

        findings = [
            create_test_finding(confidence=FindingConfidence.MEDIUM),
            create_test_finding(confidence=FindingConfidence.MEDIUM),
        ]

        call_count = [0]

        async def mock_llm(_):
            call_count[0] += 1
            if call_count[0] == 1:
                return json.dumps({
                    "verdict": "VULNERABLE",
                    "confidence": 85,
                    "reasoning": "Vulnerable code pattern.",
                    "evidence": ["evidence"],
                })
            else:
                return json.dumps({
                    "verdict": "SAFE",
                    "confidence": 90,
                    "reasoning": "Code is safe.",
                    "evidence": [],
                })

        results, stats = asyncio.run(workflow.analyze_batch(findings, mock_llm))

        self.assertEqual(stats.tier_b_analyzed, 2)
        self.assertEqual(stats.confirmed_vulnerable, 1)
        self.assertEqual(stats.confirmed_safe, 1)


class TestWorkflowUpdateFinding(unittest.TestCase):
    """Tests for finding update from workflow result."""

    def test_update_from_vulnerable(self):
        """VULNERABLE verdict should confirm finding."""
        workflow = TierBWorkflow()
        finding = create_test_finding()

        result = WorkflowResult(
            finding_id=finding.id,
            status=WorkflowStatus.SUCCESS,
            original_confidence=0.6,
            tier_b_verdict=Verdict.VULNERABLE,
            tier_b_confidence=90,
            tier_b_reasoning="Confirmed vulnerable.",
        )

        workflow.update_finding_from_result(finding, result)

        self.assertEqual(finding.status, FindingStatus.CONFIRMED)
        self.assertEqual(finding.tier, FindingTier.TIER_B)
        self.assertEqual(finding.confidence, FindingConfidence.HIGH)

    def test_update_from_safe(self):
        """SAFE verdict should mark as false positive."""
        workflow = TierBWorkflow()
        finding = create_test_finding()

        result = WorkflowResult(
            finding_id=finding.id,
            status=WorkflowStatus.SUCCESS,
            original_confidence=0.6,
            tier_b_verdict=Verdict.SAFE,
            tier_b_confidence=95,
            tier_b_reasoning="False positive, has guard.",
        )

        workflow.update_finding_from_result(finding, result)

        self.assertEqual(finding.status, FindingStatus.FALSE_POSITIVE)
        self.assertEqual(finding.tier, FindingTier.TIER_B)
        self.assertIn("False positive", finding.status_reason)

    def test_update_from_uncertain(self):
        """UNCERTAIN verdict should escalate."""
        workflow = TierBWorkflow()
        finding = create_test_finding()

        result = WorkflowResult(
            finding_id=finding.id,
            status=WorkflowStatus.SUCCESS,
            original_confidence=0.6,
            tier_b_verdict=Verdict.UNCERTAIN,
            tier_b_confidence=50,
            tier_b_reasoning="Need more context.",
        )

        workflow.update_finding_from_result(finding, result)

        self.assertEqual(finding.status, FindingStatus.ESCALATED)
        self.assertIn("human review", finding.status_reason)

    def test_update_from_auto_dismiss(self):
        """Auto-dismiss should mark as false positive."""
        workflow = TierBWorkflow()
        finding = create_test_finding()

        result = WorkflowResult(
            finding_id=finding.id,
            status=WorkflowStatus.SKIPPED_LOW_CONFIDENCE,
            original_confidence=0.2,
        )

        workflow.update_finding_from_result(finding, result)

        self.assertEqual(finding.status, FindingStatus.FALSE_POSITIVE)
        self.assertIn("Auto-dismissed", finding.status_reason)


class TestWorkflowFactory(unittest.TestCase):
    """Tests for create_tier_b_workflow factory."""

    def test_creates_workflow(self):
        """Factory should create workflow."""
        workflow = create_tier_b_workflow()
        self.assertIsInstance(workflow, TierBWorkflow)

    def test_custom_thresholds(self):
        """Factory should accept custom thresholds."""
        workflow = create_tier_b_workflow(
            auto_confirm_threshold=0.95,
            auto_dismiss_threshold=0.2,
        )

        self.assertEqual(
            workflow.confidence_evaluator.thresholds.auto_confirm_threshold,
            0.95,
        )

    def test_custom_limits(self):
        """Factory should accept custom limits."""
        workflow = create_tier_b_workflow(
            max_tokens=50_000,
            max_cost=2.00,
        )

        self.assertEqual(
            workflow.rate_limiter.limits.max_tokens_per_run,
            50_000,
        )


class TestConfidenceThresholds(unittest.TestCase):
    """Tests for ConfidenceThresholds dataclass."""

    def test_default_values(self):
        """Default values should be sensible."""
        thresholds = ConfidenceThresholds()

        self.assertEqual(thresholds.auto_confirm_threshold, 0.9)
        self.assertEqual(thresholds.auto_dismiss_threshold, 0.3)
        self.assertTrue(thresholds.require_evidence_for_confirm)

    def test_always_analyze_patterns_default(self):
        """Default always-analyze patterns should exist."""
        thresholds = ConfidenceThresholds()

        self.assertIn("business-logic", thresholds.always_analyze_patterns)
        self.assertIn("access-control", thresholds.always_analyze_patterns)


class TestWorkflowUsageReport(unittest.TestCase):
    """Tests for usage tracking."""

    def test_usage_report(self):
        """Usage report should be available."""
        workflow = TierBWorkflow()

        report = workflow.get_usage_report()

        self.assertIn("tokens_used", report)
        self.assertIn("cost_usd", report)
        self.assertIn("requests_made", report)


class TestWorkflowIntegration(unittest.TestCase):
    """Integration tests for full workflow."""

    def test_full_workflow_vulnerable(self):
        """Full workflow for vulnerable finding."""
        workflow = create_tier_b_workflow()
        finding = create_test_finding(confidence=FindingConfidence.MEDIUM)

        async def mock_llm(_):
            return json.dumps({
                "verdict": "VULNERABLE",
                "confidence": 95,
                "reasoning": "Reentrancy vulnerability confirmed. External call at line 42 occurs before state update at line 45.",
                "evidence": [
                    "line 42: payable(msg.sender).transfer(amount)",
                    "line 45: balances[msg.sender] = 0",
                ],
            })

        result = asyncio.run(workflow.analyze_finding(finding, mock_llm))
        workflow.update_finding_from_result(finding, result)

        self.assertEqual(result.status, WorkflowStatus.SUCCESS)
        self.assertEqual(result.tier_b_verdict, Verdict.VULNERABLE)
        self.assertEqual(finding.status, FindingStatus.CONFIRMED)
        self.assertEqual(finding.tier, FindingTier.TIER_B)

    def test_full_workflow_false_positive(self):
        """Full workflow for false positive."""
        workflow = create_tier_b_workflow()
        finding = create_test_finding(confidence=FindingConfidence.MEDIUM)

        async def mock_llm(_):
            return json.dumps({
                "verdict": "SAFE",
                "confidence": 92,
                "reasoning": "Function has nonReentrant modifier at line 40 which prevents reentrancy.",
                "evidence": [
                    "line 40: modifier nonReentrant",
                    "line 42: function withdraw() external nonReentrant",
                ],
            })

        result = asyncio.run(workflow.analyze_finding(finding, mock_llm))
        workflow.update_finding_from_result(finding, result)

        self.assertEqual(result.status, WorkflowStatus.SUCCESS)
        self.assertEqual(result.tier_b_verdict, Verdict.SAFE)
        self.assertEqual(finding.status, FindingStatus.FALSE_POSITIVE)


if __name__ == "__main__":
    unittest.main()
