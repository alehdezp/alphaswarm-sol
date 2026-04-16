"""
Tests for Test Scaffold Tier System (Task 4.1)

Validates the tier definitions and their properties.
"""

import unittest

from alphaswarm_sol.testing.tiers import (
    TestTier,
    TierDefinition,
    TIER_DEFINITIONS,
    get_tier_definition,
    validate_tier_success_rate,
    format_tier_summary,
)


class TestTestTierEnum(unittest.TestCase):
    """Tests for TestTier enum."""

    def test_all_tiers_exist(self):
        """All three tiers are defined."""
        self.assertEqual(TestTier.TIER_1_TEMPLATE.value, 1)
        self.assertEqual(TestTier.TIER_2_SMART.value, 2)
        self.assertEqual(TestTier.TIER_3_COMPLETE.value, 3)

    def test_tier_count(self):
        """Exactly 3 tiers defined."""
        self.assertEqual(len(TestTier), 3)


class TestTierDefinition(unittest.TestCase):
    """Tests for TierDefinition dataclass."""

    def test_valid_definition(self):
        """Can create valid tier definition."""
        defn = TierDefinition(
            tier=TestTier.TIER_1_TEMPLATE,
            description="Test tier",
            success_rate_target=0.5,
            success_rate_minimum=0.3,
            provides=["item1", "item2"],
            does_not_provide=["item3"],
        )
        self.assertEqual(defn.tier, TestTier.TIER_1_TEMPLATE)
        self.assertEqual(defn.success_rate_target, 0.5)
        self.assertEqual(len(defn.provides), 2)

    def test_invalid_target_rate_above_1(self):
        """Reject success rate > 1.0."""
        with self.assertRaises(ValueError):
            TierDefinition(
                tier=TestTier.TIER_1_TEMPLATE,
                description="Test",
                success_rate_target=1.5,  # Invalid
                success_rate_minimum=0.3,
            )

    def test_invalid_target_rate_below_0(self):
        """Reject success rate < 0.0."""
        with self.assertRaises(ValueError):
            TierDefinition(
                tier=TestTier.TIER_1_TEMPLATE,
                description="Test",
                success_rate_target=-0.1,  # Invalid
                success_rate_minimum=0.3,
            )

    def test_minimum_cannot_exceed_target(self):
        """Minimum rate cannot be higher than target."""
        with self.assertRaises(ValueError):
            TierDefinition(
                tier=TestTier.TIER_1_TEMPLATE,
                description="Test",
                success_rate_target=0.3,
                success_rate_minimum=0.5,  # Invalid - higher than target
            )


class TestTierDefinitions(unittest.TestCase):
    """Tests for TIER_DEFINITIONS mapping."""

    def test_all_tiers_have_definitions(self):
        """All tiers have definitions in the registry."""
        for tier in TestTier:
            self.assertIn(tier, TIER_DEFINITIONS, f"Missing definition for {tier}")

    def test_tier1_always_succeeds(self):
        """Tier 1 must have 100% success target and minimum."""
        defn = TIER_DEFINITIONS[TestTier.TIER_1_TEMPLATE]
        self.assertEqual(defn.success_rate_target, 1.0)
        self.assertEqual(defn.success_rate_minimum, 1.0)

    def test_tier2_realistic_target(self):
        """Tier 2 target is realistic (not aspirational 60%)."""
        defn = TIER_DEFINITIONS[TestTier.TIER_2_SMART]
        # Original docs claimed 60%, but honest assessment is 30-40%
        self.assertLessEqual(defn.success_rate_target, 0.50)
        self.assertGreaterEqual(defn.success_rate_target, 0.30)

    def test_tier3_aspirational(self):
        """Tier 3 target is low (aspirational)."""
        defn = TIER_DEFINITIONS[TestTier.TIER_3_COMPLETE]
        self.assertLessEqual(defn.success_rate_target, 0.20)

    def test_all_tiers_have_provides(self):
        """All tiers list what they provide."""
        for tier, defn in TIER_DEFINITIONS.items():
            self.assertGreater(
                len(defn.provides), 0,
                f"{tier} should have 'provides' list"
            )

    def test_all_tiers_have_does_not_provide(self):
        """All tiers list what they don't provide."""
        for tier, defn in TIER_DEFINITIONS.items():
            self.assertGreater(
                len(defn.does_not_provide), 0,
                f"{tier} should have 'does_not_provide' list"
            )

    def test_tier_hierarchy(self):
        """Higher tiers should have lower success rates."""
        tier1 = TIER_DEFINITIONS[TestTier.TIER_1_TEMPLATE]
        tier2 = TIER_DEFINITIONS[TestTier.TIER_2_SMART]
        tier3 = TIER_DEFINITIONS[TestTier.TIER_3_COMPLETE]

        self.assertGreater(tier1.success_rate_target, tier2.success_rate_target)
        self.assertGreater(tier2.success_rate_target, tier3.success_rate_target)


class TestGetTierDefinition(unittest.TestCase):
    """Tests for get_tier_definition function."""

    def test_get_tier1(self):
        """Can get Tier 1 definition."""
        defn = get_tier_definition(TestTier.TIER_1_TEMPLATE)
        self.assertEqual(defn.tier, TestTier.TIER_1_TEMPLATE)

    def test_get_tier2(self):
        """Can get Tier 2 definition."""
        defn = get_tier_definition(TestTier.TIER_2_SMART)
        self.assertEqual(defn.tier, TestTier.TIER_2_SMART)

    def test_get_tier3(self):
        """Can get Tier 3 definition."""
        defn = get_tier_definition(TestTier.TIER_3_COMPLETE)
        self.assertEqual(defn.tier, TestTier.TIER_3_COMPLETE)


class TestValidateTierSuccessRate(unittest.TestCase):
    """Tests for validate_tier_success_rate function."""

    def test_tier1_accepts_100_percent(self):
        """Tier 1 accepts 100% success rate."""
        self.assertTrue(validate_tier_success_rate(TestTier.TIER_1_TEMPLATE, 1.0))

    def test_tier1_rejects_below_minimum(self):
        """Tier 1 rejects below 100%."""
        self.assertFalse(validate_tier_success_rate(TestTier.TIER_1_TEMPLATE, 0.99))

    def test_tier2_accepts_at_minimum(self):
        """Tier 2 accepts at minimum threshold."""
        defn = TIER_DEFINITIONS[TestTier.TIER_2_SMART]
        self.assertTrue(validate_tier_success_rate(TestTier.TIER_2_SMART, defn.success_rate_minimum))

    def test_tier2_rejects_below_minimum(self):
        """Tier 2 rejects below minimum threshold."""
        defn = TIER_DEFINITIONS[TestTier.TIER_2_SMART]
        self.assertFalse(validate_tier_success_rate(
            TestTier.TIER_2_SMART,
            defn.success_rate_minimum - 0.01
        ))

    def test_tier3_accepts_at_minimum(self):
        """Tier 3 accepts at minimum threshold."""
        defn = TIER_DEFINITIONS[TestTier.TIER_3_COMPLETE]
        self.assertTrue(validate_tier_success_rate(TestTier.TIER_3_COMPLETE, defn.success_rate_minimum))


class TestFormatTierSummary(unittest.TestCase):
    """Tests for format_tier_summary function."""

    def test_format_tier1(self):
        """Can format Tier 1 summary."""
        summary = format_tier_summary(TestTier.TIER_1_TEMPLATE)
        self.assertIn("TIER_1_TEMPLATE", summary)
        self.assertIn("100%", summary)
        self.assertIn("Provides:", summary)

    def test_format_tier2(self):
        """Can format Tier 2 summary."""
        summary = format_tier_summary(TestTier.TIER_2_SMART)
        self.assertIn("TIER_2_SMART", summary)
        self.assertIn("40%", summary)  # Target rate

    def test_format_contains_provides_and_not_provides(self):
        """Summary includes both provides and does_not_provide."""
        summary = format_tier_summary(TestTier.TIER_1_TEMPLATE)
        self.assertIn("Provides:", summary)
        self.assertIn("Does NOT provide:", summary)


class TestTierDescriptions(unittest.TestCase):
    """Tests for tier description content."""

    def test_tier1_mentions_todo(self):
        """Tier 1 description mentions TODO markers."""
        defn = TIER_DEFINITIONS[TestTier.TIER_1_TEMPLATE]
        self.assertIn("TODO", defn.description.upper())

    def test_tier2_mentions_import(self):
        """Tier 2 description mentions import resolution."""
        defn = TIER_DEFINITIONS[TestTier.TIER_2_SMART]
        self.assertIn("import", defn.description.lower())

    def test_tier1_provides_structure(self):
        """Tier 1 provides test file structure."""
        defn = TIER_DEFINITIONS[TestTier.TIER_1_TEMPLATE]
        provides_lower = " ".join(defn.provides).lower()
        self.assertIn("structure", provides_lower)

    def test_tier2_provides_pragma(self):
        """Tier 2 provides pragma matching."""
        defn = TIER_DEFINITIONS[TestTier.TIER_2_SMART]
        provides_lower = " ".join(defn.provides).lower()
        self.assertIn("pragma", provides_lower)


if __name__ == "__main__":
    unittest.main()
