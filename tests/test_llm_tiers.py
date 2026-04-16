"""
Multi-Tier Model Support Tests (Task 11.12)

Tests for:
1. Complexity estimation
2. Analysis type determination
3. Tier routing
4. Context generation
5. Batch processing
"""

import unittest

from alphaswarm_sol.findings.model import (
    Finding,
    FindingSeverity,
    FindingConfidence,
    Location,
    Evidence,
)
from alphaswarm_sol.llm.tiers import (
    TierRouter,
    TierBContext,
    ModelTier,
    ModelTierConfig,
    AnalysisType,
    Complexity,
    TierStats,
    create_tier_router,
    estimate_batch_tiers,
)


def create_test_finding(
    pattern: str = "test-001",
    severity: FindingSeverity = FindingSeverity.MEDIUM,
    confidence: FindingConfidence = FindingConfidence.MEDIUM,
    behavioral_signature: str = "",
) -> Finding:
    """Create a test finding."""
    evidence = Evidence(
        behavioral_signature=behavioral_signature,
        properties_matched=["test_property"],
        code_snippet="function test() external { }",
        why_vulnerable="Test reason",
    )

    return Finding(
        pattern=pattern,
        severity=severity,
        confidence=confidence,
        location=Location(file="Test.sol", line=42, function="test"),
        description="Test finding",
        evidence=evidence,
    )


class TestComplexityEstimation(unittest.TestCase):
    """Tests for complexity estimation."""

    def test_high_complexity_business_logic(self):
        """Business logic patterns should be high complexity."""
        router = TierRouter()
        finding = create_test_finding(pattern="business-logic-001")

        complexity = router.estimate_complexity(finding)

        self.assertEqual(complexity, Complexity.HIGH)

    def test_high_complexity_reentrancy(self):
        """Reentrancy patterns should be high complexity."""
        router = TierRouter()
        finding = create_test_finding(pattern="reentrancy-classic")

        complexity = router.estimate_complexity(finding)

        self.assertEqual(complexity, Complexity.HIGH)

    def test_low_complexity_unchecked_return(self):
        """Unchecked return patterns should be low complexity."""
        router = TierRouter()
        finding = create_test_finding(pattern="unchecked-return-001")

        complexity = router.estimate_complexity(finding)

        self.assertEqual(complexity, Complexity.LOW)

    def test_high_complexity_critical_severity(self):
        """Critical severity should increase complexity."""
        router = TierRouter()
        finding = create_test_finding(
            pattern="unknown-pattern",
            severity=FindingSeverity.CRITICAL,
        )

        complexity = router.estimate_complexity(finding)

        self.assertEqual(complexity, Complexity.HIGH)

    def test_high_complexity_long_behavioral(self):
        """Long behavioral signatures indicate complex patterns."""
        router = TierRouter()
        finding = create_test_finding(
            pattern="unknown-pattern",
            behavioral_signature="R:bal→X:out→W:bal→X:in→R:state",
        )

        complexity = router.estimate_complexity(finding)

        self.assertEqual(complexity, Complexity.HIGH)

    def test_medium_complexity_default(self):
        """Default unknown patterns should be medium complexity."""
        router = TierRouter()
        finding = create_test_finding(pattern="unknown-pattern")

        complexity = router.estimate_complexity(finding)

        self.assertEqual(complexity, Complexity.MEDIUM)


class TestAnalysisTypeDetermination(unittest.TestCase):
    """Tests for analysis type determination."""

    def test_business_logic_type(self):
        """Business logic patterns need business logic analysis."""
        router = TierRouter()
        finding = create_test_finding(pattern="business-logic-flow")

        analysis_type = router.determine_analysis_type(finding)

        self.assertEqual(analysis_type, AnalysisType.BUSINESS_LOGIC)

    def test_cross_contract_type(self):
        """Flash loan patterns need cross-contract analysis."""
        router = TierRouter()
        finding = create_test_finding(pattern="flash-loan-attack")

        analysis_type = router.determine_analysis_type(finding)

        self.assertEqual(analysis_type, AnalysisType.CROSS_CONTRACT)

    def test_cross_function_type(self):
        """Reentrancy patterns need cross-function analysis."""
        router = TierRouter()
        finding = create_test_finding(pattern="reentrancy-classic")

        analysis_type = router.determine_analysis_type(finding)

        self.assertEqual(analysis_type, AnalysisType.CROSS_FUNCTION)

    def test_context_aware_type(self):
        """Patterns with behavioral signatures need context-aware analysis."""
        router = TierRouter()
        finding = create_test_finding(
            pattern="unknown-pattern",
            behavioral_signature="R:bal→W:bal",
        )

        analysis_type = router.determine_analysis_type(finding)

        self.assertEqual(analysis_type, AnalysisType.CONTEXT_AWARE)

    def test_simple_check_type(self):
        """Simple patterns need simple checks."""
        router = TierRouter()
        finding = create_test_finding(
            pattern="magic-number-001",
            behavioral_signature="",
        )

        analysis_type = router.determine_analysis_type(finding)

        self.assertEqual(analysis_type, AnalysisType.SIMPLE_CHECK)


class TestTierSuggestion(unittest.TestCase):
    """Tests for tier suggestion."""

    def test_premium_for_business_logic(self):
        """Business logic analysis should suggest premium tier."""
        router = TierRouter()

        tier = router.suggest_tier(Complexity.HIGH, AnalysisType.BUSINESS_LOGIC)

        self.assertEqual(tier, ModelTier.PREMIUM)

    def test_premium_for_cross_contract(self):
        """Cross-contract analysis should suggest premium tier."""
        router = TierRouter()

        tier = router.suggest_tier(Complexity.MEDIUM, AnalysisType.CROSS_CONTRACT)

        self.assertEqual(tier, ModelTier.PREMIUM)

    def test_standard_for_cross_function(self):
        """Cross-function analysis should suggest standard tier."""
        router = TierRouter()

        tier = router.suggest_tier(Complexity.MEDIUM, AnalysisType.CROSS_FUNCTION)

        self.assertEqual(tier, ModelTier.STANDARD)

    def test_cheap_for_simple_low_complexity(self):
        """Simple low-complexity checks should suggest cheap tier."""
        router = TierRouter()

        tier = router.suggest_tier(Complexity.LOW, AnalysisType.SIMPLE_CHECK)

        self.assertEqual(tier, ModelTier.CHEAP)

    def test_standard_default(self):
        """Default case should suggest standard tier."""
        router = TierRouter()

        tier = router.suggest_tier(Complexity.MEDIUM, AnalysisType.CONTEXT_AWARE)

        self.assertEqual(tier, ModelTier.STANDARD)


class TestTierBContext(unittest.TestCase):
    """Tests for TierBContext."""

    def test_create_context(self):
        """Context should be created with all fields."""
        router = TierRouter()
        finding = create_test_finding(
            pattern="reentrancy-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
        )

        context = router.create_context(finding)

        self.assertIsInstance(context, TierBContext)
        self.assertEqual(context.pattern, "reentrancy-001")
        self.assertEqual(context.severity, "high")
        self.assertEqual(context.tier_a_verdict, "match")  # HIGH confidence
        self.assertIn(context.complexity, list(Complexity))
        self.assertIn(context.suggested_tier, list(ModelTier))

    def test_context_to_dict(self):
        """Context should serialize to dict."""
        router = TierRouter()
        finding = create_test_finding()

        context = router.create_context(finding)
        d = context.to_dict()

        self.assertIn("finding_id", d)
        self.assertIn("complexity", d)
        self.assertIn("suggested_tier", d)
        self.assertIn("analysis_type", d)

    def test_context_to_json(self):
        """Context should serialize to JSON."""
        router = TierRouter()
        finding = create_test_finding()

        context = router.create_context(finding)
        json_str = context.to_json()

        import json
        parsed = json.loads(json_str)
        self.assertIn("finding_id", parsed)

    def test_tier_a_verdict_mapping(self):
        """Tier A verdict should map from confidence."""
        router = TierRouter()

        # HIGH confidence -> match
        finding_high = create_test_finding(confidence=FindingConfidence.HIGH)
        context_high = router.create_context(finding_high)
        self.assertEqual(context_high.tier_a_verdict, "match")

        # MEDIUM confidence -> possible
        finding_med = create_test_finding(confidence=FindingConfidence.MEDIUM)
        context_med = router.create_context(finding_med)
        self.assertEqual(context_med.tier_a_verdict, "possible")

        # LOW confidence -> unlikely
        finding_low = create_test_finding(confidence=FindingConfidence.LOW)
        context_low = router.create_context(finding_low)
        self.assertEqual(context_low.tier_a_verdict, "unlikely")

    def test_urgency_mapping(self):
        """Urgency should map from severity."""
        router = TierRouter()

        # CRITICAL severity -> high urgency
        finding_crit = create_test_finding(severity=FindingSeverity.CRITICAL)
        context_crit = router.create_context(finding_crit)
        self.assertEqual(context_crit.urgency, "high")

        # LOW severity -> normal urgency
        finding_low = create_test_finding(severity=FindingSeverity.LOW)
        context_low = router.create_context(finding_low)
        self.assertEqual(context_low.urgency, "normal")


class TestTokenEstimation(unittest.TestCase):
    """Tests for token estimation."""

    def test_base_tokens(self):
        """Should have base token count."""
        router = TierRouter()
        finding = create_test_finding()

        tokens = router.estimate_tokens(finding)

        self.assertGreater(tokens, 100)

    def test_context_increases_tokens(self):
        """Adding context should increase token estimate."""
        router = TierRouter()
        finding = create_test_finding()

        tokens_no_context = router.estimate_tokens(finding, "")
        tokens_with_context = router.estimate_tokens(
            finding,
            "function withdraw() external { msg.sender.call{value: amount}(''); }"
        )

        self.assertGreater(tokens_with_context, tokens_no_context)

    def test_token_cap(self):
        """Tokens should be capped at maximum."""
        router = TierRouter()
        finding = create_test_finding()

        # Very long context
        long_context = "function test() external { " + "x = 1; " * 10000 + "}"
        tokens = router.estimate_tokens(finding, long_context)

        self.assertLessEqual(tokens, 4000)


class TestBatchProcessing(unittest.TestCase):
    """Tests for batch context creation."""

    def test_batch_create_contexts(self):
        """Should create contexts for all findings."""
        router = TierRouter()
        findings = [
            create_test_finding(pattern="reentrancy-001"),
            create_test_finding(pattern="unchecked-return-001"),
            create_test_finding(pattern="business-logic-001"),
        ]

        contexts = router.batch_create_contexts(findings)

        self.assertEqual(len(contexts), 3)
        self.assertTrue(all(isinstance(c, TierBContext) for c in contexts))

    def test_estimate_batch_tiers(self):
        """Should estimate tier distribution."""
        findings = [
            create_test_finding(pattern="unchecked-return-001"),  # Cheap
            create_test_finding(pattern="test-001"),  # Standard
            create_test_finding(pattern="business-logic-001"),  # Premium
        ]

        stats = estimate_batch_tiers(findings)

        self.assertGreater(stats.cheap_count + stats.standard_count + stats.premium_count, 0)

    def test_tier_stats_to_dict(self):
        """TierStats should serialize to dict."""
        stats = TierStats(
            cheap_count=5,
            standard_count=10,
            premium_count=2,
            total_estimated_tokens=5000,
            total_estimated_cost=0.05,
        )

        d = stats.to_dict()

        self.assertIn("tier_distribution", d)
        self.assertIn("tier_percentages", d)
        self.assertEqual(d["tier_distribution"]["cheap"], 5)


class TestModelTierConfig(unittest.TestCase):
    """Tests for ModelTierConfig."""

    def test_default_config(self):
        """Default config should have sensible values."""
        config = ModelTierConfig()

        self.assertIn(ModelTier.CHEAP, config.tier_models)
        self.assertIn(ModelTier.STANDARD, config.tier_models)
        self.assertIn(ModelTier.PREMIUM, config.tier_models)

        self.assertGreater(len(config.low_complexity_patterns), 0)
        self.assertGreater(len(config.high_complexity_patterns), 0)

    def test_custom_config(self):
        """Custom config should override defaults."""
        config = ModelTierConfig(
            low_complexity_patterns=["custom-pattern"],
            tier_cost_weights={
                ModelTier.CHEAP: 0.05,
                ModelTier.STANDARD: 0.5,
                ModelTier.PREMIUM: 5.0,
            },
        )

        self.assertEqual(config.low_complexity_patterns, ["custom-pattern"])
        self.assertEqual(config.tier_cost_weights[ModelTier.CHEAP], 0.05)


class TestFactoryFunctions(unittest.TestCase):
    """Tests for factory functions."""

    def test_create_tier_router(self):
        """Factory should create router."""
        router = create_tier_router()

        self.assertIsInstance(router, TierRouter)

    def test_create_tier_router_with_config(self):
        """Factory should accept config."""
        config = ModelTierConfig(
            low_complexity_patterns=["my-pattern"],
        )

        router = create_tier_router(config)

        self.assertEqual(router.config.low_complexity_patterns, ["my-pattern"])


class TestIntegration(unittest.TestCase):
    """Integration tests for tier routing."""

    def test_full_routing_flow(self):
        """Full routing flow should work end to end."""
        router = create_tier_router()

        findings = [
            create_test_finding(
                pattern="reentrancy-classic",
                severity=FindingSeverity.CRITICAL,
                confidence=FindingConfidence.HIGH,
            ),
            create_test_finding(
                pattern="unchecked-return",
                severity=FindingSeverity.LOW,
                confidence=FindingConfidence.LOW,
            ),
            create_test_finding(
                pattern="business-logic-vuln",
                severity=FindingSeverity.HIGH,
                confidence=FindingConfidence.MEDIUM,
            ),
        ]

        contexts = router.batch_create_contexts(findings)

        # Reentrancy should be high complexity, standard/premium tier
        self.assertEqual(contexts[0].complexity, Complexity.HIGH)
        self.assertIn(contexts[0].suggested_tier, [ModelTier.STANDARD, ModelTier.PREMIUM])

        # Unchecked return should be low complexity, cheap tier
        self.assertEqual(contexts[1].complexity, Complexity.LOW)
        self.assertEqual(contexts[1].suggested_tier, ModelTier.CHEAP)

        # Business logic should be high complexity, premium tier
        self.assertEqual(contexts[2].complexity, Complexity.HIGH)
        self.assertEqual(contexts[2].suggested_tier, ModelTier.PREMIUM)

    def test_tier_stats_calculation(self):
        """Tier stats should be calculated correctly."""
        findings = [
            create_test_finding(pattern="unchecked-return"),
            create_test_finding(pattern="unchecked-return"),
            create_test_finding(pattern="standard-pattern"),
            create_test_finding(pattern="business-logic"),
        ]

        stats = estimate_batch_tiers(findings)

        # Should have mix of tiers
        self.assertGreater(stats.cheap_count, 0)
        self.assertGreater(stats.total_estimated_tokens, 0)


if __name__ == "__main__":
    unittest.main()
