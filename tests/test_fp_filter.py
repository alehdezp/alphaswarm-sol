"""
False Positive Filtering Tests (Task 11.4)

Tests for:
1. FP detection and filtering
2. True positive preservation
3. Metrics tracking
4. Pattern-specific behavior
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
from alphaswarm_sol.llm.fp_filter import (
    FPFilter,
    FPFilterResult,
    FPFilterDecision,
    FPFilterMetrics,
    create_fp_filter,
    calculate_fp_reduction,
    HIGH_FP_PATTERNS,
    NEVER_DISMISS_PATTERNS,
)
from alphaswarm_sol.llm.validate import Verdict


def create_test_finding(
    pattern: str = "reentrancy-001",
    confidence: FindingConfidence = FindingConfidence.MEDIUM,
    has_evidence: bool = True,
) -> Finding:
    """Create a test finding."""
    evidence = Evidence()
    if has_evidence:
        evidence = Evidence(
            behavioral_signature="R:bal→X:out→W:bal",
            properties_matched=["state_write_after_external_call"],
            code_snippet="function withdraw() external { }",
            why_vulnerable="External call before state update",
        )

    return Finding(
        pattern=pattern,
        severity=FindingSeverity.HIGH,
        confidence=confidence,
        location=Location(file="Test.sol", line=42, function="withdraw"),
        description="Potential reentrancy vulnerability",
        evidence=evidence,
    )


class TestFPFilterDecision(unittest.TestCase):
    """Tests for FP filter decisions."""

    def setUp(self):
        self.fp_filter = FPFilter()

    def test_safe_high_confidence_is_fp(self):
        """High confidence SAFE verdict should be confirmed FP."""
        finding = create_test_finding()

        async def mock_llm(_):
            return json.dumps({
                "verdict": "SAFE",
                "confidence": 95,
                "reasoning": "Function has reentrancy guard at line 40.",
                "evidence": ["modifier nonReentrant"],
            })

        result = asyncio.run(self.fp_filter.analyze_finding(finding, mock_llm))

        self.assertEqual(result.decision, FPFilterDecision.CONFIRMED_FP)
        self.assertEqual(result.confidence_after, 95)

    def test_safe_low_confidence_needs_review(self):
        """Low confidence SAFE verdict should need review."""
        fp_filter = FPFilter(min_confidence_for_fp=80)
        finding = create_test_finding()

        async def mock_llm(_):
            return json.dumps({
                "verdict": "SAFE",
                "confidence": 60,  # Below threshold
                "reasoning": "Possibly safe but uncertain.",
                "evidence": [],
            })

        result = asyncio.run(fp_filter.analyze_finding(finding, mock_llm))

        self.assertEqual(result.decision, FPFilterDecision.NEEDS_REVIEW)

    def test_vulnerable_is_confirmed(self):
        """VULNERABLE verdict should be confirmed vuln."""
        finding = create_test_finding()

        async def mock_llm(_):
            return json.dumps({
                "verdict": "VULNERABLE",
                "confidence": 90,
                "reasoning": "Classic reentrancy pattern detected.",
                "evidence": ["external call at line 42"],
            })

        result = asyncio.run(self.fp_filter.analyze_finding(finding, mock_llm))

        self.assertEqual(result.decision, FPFilterDecision.CONFIRMED_VULN)

    def test_uncertain_needs_review(self):
        """UNCERTAIN verdict should need review."""
        finding = create_test_finding()

        async def mock_llm(_):
            return json.dumps({
                "verdict": "UNCERTAIN",
                "confidence": 50,
                "reasoning": "Need more context to determine.",
                "evidence": [],
            })

        result = asyncio.run(self.fp_filter.analyze_finding(finding, mock_llm))

        self.assertEqual(result.decision, FPFilterDecision.NEEDS_REVIEW)


class TestProtectedPatterns(unittest.TestCase):
    """Tests for pattern protection."""

    def test_access_control_never_dismissed(self):
        """Access control patterns should never be auto-dismissed."""
        fp_filter = FPFilter()
        finding = create_test_finding(pattern="access-control-missing")

        async def mock_llm(_):
            raise AssertionError("Should not call LLM for protected pattern")

        result = asyncio.run(fp_filter.analyze_finding(finding, mock_llm))

        self.assertEqual(result.decision, FPFilterDecision.NEEDS_REVIEW)
        self.assertIn("requires human review", result.reasoning)

    def test_privilege_escalation_protected(self):
        """Privilege escalation patterns should be protected."""
        fp_filter = FPFilter()
        finding = create_test_finding(pattern="privilege-escalation-001")

        async def mock_llm(_):
            raise AssertionError("Should not call LLM")

        result = asyncio.run(fp_filter.analyze_finding(finding, mock_llm))

        self.assertEqual(result.decision, FPFilterDecision.NEEDS_REVIEW)

    def test_custom_protected_patterns(self):
        """Custom protected patterns should work."""
        fp_filter = FPFilter(never_dismiss_patterns={"custom-critical"})
        finding = create_test_finding(pattern="custom-critical-001")

        async def mock_llm(_):
            raise AssertionError("Should not call LLM")

        result = asyncio.run(fp_filter.analyze_finding(finding, mock_llm))

        self.assertEqual(result.decision, FPFilterDecision.NEEDS_REVIEW)


class TestFPMetrics(unittest.TestCase):
    """Tests for FP metrics tracking."""

    def test_metrics_tracked(self):
        """Metrics should be tracked correctly."""
        fp_filter = FPFilter()
        findings = [
            create_test_finding(pattern="test-001"),
            create_test_finding(pattern="test-002"),
        ]

        async def mock_llm(_):
            return json.dumps({
                "verdict": "SAFE",
                "confidence": 90,
                "reasoning": "Safe code pattern.",
                "evidence": [],
            })

        asyncio.run(fp_filter.filter_batch(findings, mock_llm))

        metrics = fp_filter.get_metrics()
        self.assertEqual(metrics.total_findings, 2)
        self.assertEqual(metrics.analyzed, 2)
        self.assertEqual(metrics.confirmed_fp, 2)

    def test_fp_reduction_rate(self):
        """FP reduction rate should be calculated."""
        fp_filter = FPFilter()
        findings = [
            create_test_finding(pattern="reentrancy-001", confidence=FindingConfidence.LOW),
            create_test_finding(pattern="reentrancy-002", confidence=FindingConfidence.LOW),
            create_test_finding(pattern="test-003"),
        ]

        async def mock_llm(_):
            return json.dumps({
                "verdict": "SAFE",
                "confidence": 95,
                "reasoning": "False positive confirmed.",
                "evidence": [],
            })

        results, metrics = asyncio.run(fp_filter.filter_batch(findings, mock_llm))

        metrics_dict = metrics.to_dict()
        self.assertIn("fp_reduction_rate", metrics_dict)
        self.assertIn("fp_identification_rate", metrics_dict)

    def test_true_positive_preservation(self):
        """True positives should be preserved."""
        fp_filter = FPFilter()
        findings = [create_test_finding()]

        async def mock_llm(_):
            return json.dumps({
                "verdict": "VULNERABLE",
                "confidence": 95,
                "reasoning": "Real vulnerability detected.",
                "evidence": ["exploitation possible"],
            })

        results, metrics = asyncio.run(fp_filter.filter_batch(findings, mock_llm))

        self.assertEqual(metrics.true_positives_preserved, 1)
        self.assertEqual(metrics.confirmed_vuln, 1)

    def test_reset_metrics(self):
        """Metrics should be resettable."""
        fp_filter = FPFilter()
        fp_filter._metrics.total_findings = 100
        fp_filter._metrics.confirmed_fp = 50

        fp_filter.reset_metrics()

        metrics = fp_filter.get_metrics()
        self.assertEqual(metrics.total_findings, 0)
        self.assertEqual(metrics.confirmed_fp, 0)


class TestApplyResults(unittest.TestCase):
    """Tests for applying FP results to findings."""

    def test_apply_confirmed_fp(self):
        """Confirmed FP should update finding status."""
        fp_filter = FPFilter()
        finding = create_test_finding()

        result = FPFilterResult(
            finding_id=finding.id,
            decision=FPFilterDecision.CONFIRMED_FP,
            original_status=FindingStatus.PENDING,
            confidence_before=0.6,
            confidence_after=95,
            reasoning="False positive - has guard",
        )

        fp_filter.apply_results([finding], [result])

        self.assertEqual(finding.status, FindingStatus.FALSE_POSITIVE)
        self.assertEqual(finding.tier, FindingTier.TIER_B)

    def test_apply_confirmed_vuln(self):
        """Confirmed vuln should update finding status."""
        fp_filter = FPFilter()
        finding = create_test_finding()

        result = FPFilterResult(
            finding_id=finding.id,
            decision=FPFilterDecision.CONFIRMED_VULN,
            original_status=FindingStatus.PENDING,
            confidence_before=0.6,
            confidence_after=90,
            reasoning="Vulnerability confirmed",
        )

        fp_filter.apply_results([finding], [result])

        self.assertEqual(finding.status, FindingStatus.CONFIRMED)
        self.assertEqual(finding.tier, FindingTier.TIER_B)
        self.assertEqual(finding.confidence, FindingConfidence.HIGH)

    def test_apply_needs_review(self):
        """Needs review should escalate finding."""
        fp_filter = FPFilter()
        finding = create_test_finding()

        result = FPFilterResult(
            finding_id=finding.id,
            decision=FPFilterDecision.NEEDS_REVIEW,
            original_status=FindingStatus.PENDING,
            confidence_before=0.6,
            reasoning="Uncertain",
        )

        fp_filter.apply_results([finding], [result])

        self.assertEqual(finding.status, FindingStatus.ESCALATED)


class TestBatchFiltering(unittest.TestCase):
    """Tests for batch filtering."""

    def test_batch_filter_mixed_results(self):
        """Batch filtering should handle mixed results."""
        fp_filter = FPFilter()
        findings = [
            create_test_finding(pattern="test-001"),
            create_test_finding(pattern="test-002"),
            create_test_finding(pattern="test-003"),
        ]

        call_count = [0]

        async def mock_llm(_):
            call_count[0] += 1
            if call_count[0] == 1:
                return json.dumps({
                    "verdict": "SAFE",
                    "confidence": 95,
                    "reasoning": "FP detected.",
                    "evidence": [],
                })
            elif call_count[0] == 2:
                return json.dumps({
                    "verdict": "VULNERABLE",
                    "confidence": 90,
                    "reasoning": "Real vuln.",
                    "evidence": [],
                })
            else:
                return json.dumps({
                    "verdict": "UNCERTAIN",
                    "confidence": 50,
                    "reasoning": "Need review.",
                    "evidence": [],
                })

        results, metrics = asyncio.run(fp_filter.filter_batch(findings, mock_llm))

        self.assertEqual(len(results), 3)
        self.assertEqual(metrics.confirmed_fp, 1)
        self.assertEqual(metrics.confirmed_vuln, 1)
        self.assertEqual(metrics.needs_review, 1)


class TestHighFPPatterns(unittest.TestCase):
    """Tests for high FP pattern handling."""

    def test_high_fp_patterns_defined(self):
        """High FP patterns should be defined."""
        self.assertIn("reentrancy", HIGH_FP_PATTERNS)
        self.assertIn("unchecked-return", HIGH_FP_PATTERNS)
        self.assertIn("timestamp-dependency", HIGH_FP_PATTERNS)

    def test_never_dismiss_patterns_defined(self):
        """Never dismiss patterns should be defined."""
        self.assertIn("access-control", NEVER_DISMISS_PATTERNS)
        self.assertIn("privilege-escalation", NEVER_DISMISS_PATTERNS)
        self.assertIn("owner-manipulation", NEVER_DISMISS_PATTERNS)
        self.assertIn("fund-drain", NEVER_DISMISS_PATTERNS)


class TestFPFilterFactory(unittest.TestCase):
    """Tests for create_fp_filter factory."""

    def test_creates_filter(self):
        """Factory should create filter."""
        fp_filter = create_fp_filter()
        self.assertIsInstance(fp_filter, FPFilter)

    def test_custom_confidence_threshold(self):
        """Factory should accept custom confidence threshold."""
        fp_filter = create_fp_filter(min_confidence_for_fp=90)
        self.assertEqual(fp_filter.min_confidence_for_fp, 90)


class TestCalculateFPReduction(unittest.TestCase):
    """Tests for FP reduction calculation."""

    def test_positive_reduction(self):
        """Should calculate positive reduction."""
        reduction = calculate_fp_reduction(100, 70)
        self.assertEqual(reduction, 30.0)

    def test_full_reduction(self):
        """Should handle full reduction."""
        reduction = calculate_fp_reduction(50, 0)
        self.assertEqual(reduction, 100.0)

    def test_no_reduction(self):
        """Should handle no reduction."""
        reduction = calculate_fp_reduction(50, 50)
        self.assertEqual(reduction, 0.0)

    def test_zero_before(self):
        """Should handle zero before count."""
        reduction = calculate_fp_reduction(0, 10)
        self.assertEqual(reduction, 0.0)


class TestFPFilterResultSerialization(unittest.TestCase):
    """Tests for result serialization."""

    def test_result_to_dict(self):
        """Result should serialize correctly."""
        result = FPFilterResult(
            finding_id="f-001",
            decision=FPFilterDecision.CONFIRMED_FP,
            original_status=FindingStatus.PENDING,
            confidence_before=0.6,
            confidence_after=95,
            reasoning="False positive detected",
            evidence=["line 42: nonReentrant modifier"],
            tokens_used=500,
            cost_usd=0.01,
        )

        d = result.to_dict()
        self.assertEqual(d["finding_id"], "f-001")
        self.assertEqual(d["decision"], "confirmed_fp")
        self.assertEqual(d["confidence_after"], 95)

    def test_metrics_to_dict(self):
        """Metrics should serialize correctly."""
        metrics = FPFilterMetrics(
            total_findings=100,
            analyzed=80,
            confirmed_fp=30,
            confirmed_vuln=40,
            needs_review=10,
            fp_before_count=50,
            fp_after_count=30,
            true_positives_preserved=40,
        )

        d = metrics.to_dict()
        self.assertEqual(d["total_findings"], 100)
        self.assertEqual(d["fp_reduction_rate"], 40.0)
        self.assertEqual(d["true_positives_preserved"], 40)


class TestFPFilterIntegration(unittest.TestCase):
    """Integration tests for FP filter."""

    def test_full_workflow(self):
        """Full FP filtering workflow should work."""
        fp_filter = create_fp_filter()
        findings = [
            create_test_finding(pattern="safe-pattern-001"),
            create_test_finding(pattern="vuln-pattern-002"),
        ]

        call_count = [0]

        async def mock_llm(prompt):
            call_count[0] += 1
            # First call returns SAFE, second returns VULNERABLE
            if call_count[0] == 1:
                return json.dumps({
                    "verdict": "SAFE",
                    "confidence": 92,
                    "reasoning": "Has nonReentrant modifier.",
                    "evidence": ["modifier present"],
                })
            return json.dumps({
                "verdict": "VULNERABLE",
                "confidence": 88,
                "reasoning": "Real vulnerability.",
                "evidence": ["no guard"],
            })

        results, metrics = asyncio.run(fp_filter.filter_batch(findings, mock_llm))
        fp_filter.apply_results(findings, results)

        # First finding should be FP
        self.assertEqual(findings[0].status, FindingStatus.FALSE_POSITIVE)
        # Second should be confirmed
        self.assertEqual(findings[1].status, FindingStatus.CONFIRMED)

        # Metrics should reflect
        self.assertEqual(metrics.confirmed_fp, 1)
        self.assertEqual(metrics.confirmed_vuln, 1)


class TestErrorHandling(unittest.TestCase):
    """Tests for error handling."""

    def test_llm_error_handled(self):
        """LLM errors should be handled gracefully."""
        fp_filter = FPFilter()
        finding = create_test_finding(pattern="test-error")

        async def mock_llm_error(_):
            raise RuntimeError("API error")

        result = asyncio.run(fp_filter.analyze_finding(finding, mock_llm_error))

        self.assertEqual(result.decision, FPFilterDecision.ERROR)


if __name__ == "__main__":
    unittest.main()
