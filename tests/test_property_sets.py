"""Tests for property sets per vulnerability category.

Task 9.A: Tests for category-relevant property definitions.
"""

import unittest

from alphaswarm_sol.kg.property_sets import (
    CORE_PROPERTIES,
    PROPERTY_SETS,
    PropertySet,
    VulnerabilityCategory,
    get_all_categories,
    get_category_from_pattern_id,
    get_property_set,
    get_relevant_properties,
    is_property_relevant,
)


class TestPropertySet(unittest.TestCase):
    """Test PropertySet dataclass."""

    def test_create_property_set(self):
        """PropertySet can be created."""
        ps = PropertySet(
            required=frozenset({"prop1", "prop2"}),
            optional=frozenset({"prop3"}),
        )
        self.assertIn("prop1", ps.required)
        self.assertIn("prop3", ps.optional)

    def test_all_properties(self):
        """all_properties returns required + optional."""
        ps = PropertySet(
            required=frozenset({"prop1"}),
            optional=frozenset({"prop2"}),
        )
        all_props = ps.all_properties()
        self.assertIn("prop1", all_props)
        self.assertIn("prop2", all_props)

    def test_is_relevant_required(self):
        """Required properties are relevant."""
        ps = PropertySet(required=frozenset({"prop1"}))
        self.assertTrue(ps.is_relevant("prop1"))

    def test_is_relevant_optional(self):
        """Optional properties are relevant."""
        ps = PropertySet(
            required=frozenset(),
            optional=frozenset({"prop1"}),
        )
        self.assertTrue(ps.is_relevant("prop1"))

    def test_is_relevant_excluded(self):
        """Excluded properties are not relevant."""
        ps = PropertySet(
            required=frozenset({"prop1"}),
            exclusions=frozenset({"prop2"}),
        )
        self.assertFalse(ps.is_relevant("prop2"))

    def test_is_relevant_unknown(self):
        """Unknown properties are not relevant."""
        ps = PropertySet(required=frozenset({"prop1"}))
        self.assertFalse(ps.is_relevant("unknown"))


class TestVulnerabilityCategory(unittest.TestCase):
    """Test VulnerabilityCategory enum."""

    def test_all_categories_defined(self):
        """All expected categories are defined."""
        expected = [
            "reentrancy",
            "access_control",
            "dos",
            "oracle",
            "mev",
            "token",
            "crypto",
            "upgrade",
            "governance",
            "general",
        ]
        for cat in expected:
            self.assertIsNotNone(VulnerabilityCategory(cat))

    def test_category_values(self):
        """Category values are correct."""
        self.assertEqual(VulnerabilityCategory.REENTRANCY.value, "reentrancy")
        self.assertEqual(VulnerabilityCategory.ACCESS_CONTROL.value, "access_control")


class TestPropertySets(unittest.TestCase):
    """Test PROPERTY_SETS definitions."""

    def test_all_categories_have_sets(self):
        """All categories have property sets defined."""
        for category in VulnerabilityCategory:
            self.assertIn(category, PROPERTY_SETS)

    def test_reentrancy_properties(self):
        """Reentrancy has expected properties."""
        ps = PROPERTY_SETS[VulnerabilityCategory.REENTRANCY]
        self.assertIn("state_write_after_external_call", ps.required)
        self.assertIn("has_reentrancy_guard", ps.required)
        self.assertIn("has_external_calls", ps.required)

    def test_access_control_properties(self):
        """Access control has expected properties."""
        ps = PROPERTY_SETS[VulnerabilityCategory.ACCESS_CONTROL]
        self.assertIn("has_access_gate", ps.required)
        self.assertIn("writes_privileged_state", ps.required)
        self.assertIn("uses_tx_origin", ps.required)

    def test_dos_properties(self):
        """DoS has expected properties."""
        ps = PROPERTY_SETS[VulnerabilityCategory.DOS]
        self.assertIn("has_unbounded_loop", ps.required)
        self.assertIn("external_calls_in_loop", ps.required)

    def test_oracle_properties(self):
        """Oracle has expected properties."""
        ps = PROPERTY_SETS[VulnerabilityCategory.ORACLE]
        self.assertIn("reads_oracle_price", ps.required)
        self.assertIn("has_staleness_check", ps.required)

    def test_mev_properties(self):
        """MEV has expected properties."""
        ps = PROPERTY_SETS[VulnerabilityCategory.MEV]
        self.assertIn("swap_like", ps.required)
        self.assertIn("risk_missing_slippage_parameter", ps.required)

    def test_token_properties(self):
        """Token has expected properties."""
        ps = PROPERTY_SETS[VulnerabilityCategory.TOKEN]
        self.assertIn("uses_erc20_transfer", ps.required)
        self.assertIn("token_return_guarded", ps.required)

    def test_crypto_properties(self):
        """Crypto has expected properties."""
        ps = PROPERTY_SETS[VulnerabilityCategory.CRYPTO]
        self.assertIn("uses_ecrecover", ps.required)
        self.assertIn("checks_zero_address", ps.required)

    def test_upgrade_properties(self):
        """Upgrade has expected properties."""
        ps = PROPERTY_SETS[VulnerabilityCategory.UPGRADE]
        self.assertIn("is_proxy_like", ps.required)
        self.assertIn("uses_delegatecall", ps.required)

    def test_governance_properties(self):
        """Governance has expected properties."""
        ps = PROPERTY_SETS[VulnerabilityCategory.GOVERNANCE]
        self.assertIn("governance_vote_without_snapshot", ps.required)

    def test_general_uses_core(self):
        """General category uses core properties."""
        ps = PROPERTY_SETS[VulnerabilityCategory.GENERAL]
        self.assertEqual(ps.required, CORE_PROPERTIES)

    def test_exclusions_defined(self):
        """Some categories have exclusions."""
        ps_reentrancy = PROPERTY_SETS[VulnerabilityCategory.REENTRANCY]
        self.assertIn("reads_oracle_price", ps_reentrancy.exclusions)

        ps_oracle = PROPERTY_SETS[VulnerabilityCategory.ORACLE]
        self.assertIn("state_write_after_external_call", ps_oracle.exclusions)


class TestCoreProperties(unittest.TestCase):
    """Test CORE_PROPERTIES."""

    def test_core_properties_defined(self):
        """Core properties are defined."""
        self.assertIn("name", CORE_PROPERTIES)
        self.assertIn("visibility", CORE_PROPERTIES)
        self.assertIn("modifiers", CORE_PROPERTIES)
        self.assertIn("has_external_calls", CORE_PROPERTIES)

    def test_core_properties_frozen(self):
        """Core properties is a frozenset."""
        self.assertIsInstance(CORE_PROPERTIES, frozenset)


class TestGetPropertySet(unittest.TestCase):
    """Test get_property_set function."""

    def test_get_by_enum(self):
        """Can get property set by enum."""
        ps = get_property_set(VulnerabilityCategory.REENTRANCY)
        self.assertIn("state_write_after_external_call", ps.required)

    def test_get_by_string(self):
        """Can get property set by string."""
        ps = get_property_set("reentrancy")
        self.assertIn("state_write_after_external_call", ps.required)

    def test_get_by_string_case_insensitive(self):
        """String lookup is case insensitive."""
        ps = get_property_set("REENTRANCY")
        self.assertIn("state_write_after_external_call", ps.required)

    def test_unknown_returns_general(self):
        """Unknown category returns general set."""
        ps = get_property_set("unknown_category")
        self.assertEqual(ps.required, CORE_PROPERTIES)


class TestGetRelevantProperties(unittest.TestCase):
    """Test get_relevant_properties function."""

    def test_includes_core(self):
        """Always includes core properties."""
        props = get_relevant_properties("reentrancy")
        for core in CORE_PROPERTIES:
            self.assertIn(core, props)

    def test_includes_category_specific(self):
        """Includes category-specific properties."""
        props = get_relevant_properties("reentrancy")
        self.assertIn("state_write_after_external_call", props)
        self.assertIn("has_reentrancy_guard", props)


class TestIsPropertyRelevant(unittest.TestCase):
    """Test is_property_relevant function."""

    def test_core_always_relevant(self):
        """Core properties are always relevant."""
        self.assertTrue(is_property_relevant("visibility", "reentrancy"))
        self.assertTrue(is_property_relevant("visibility", "oracle"))

    def test_category_property_relevant(self):
        """Category-specific properties are relevant."""
        self.assertTrue(
            is_property_relevant("state_write_after_external_call", "reentrancy")
        )
        self.assertTrue(is_property_relevant("reads_oracle_price", "oracle"))

    def test_irrelevant_property(self):
        """Irrelevant properties return False."""
        # Oracle property not relevant for reentrancy
        self.assertFalse(is_property_relevant("has_staleness_check", "reentrancy"))


class TestGetAllCategories(unittest.TestCase):
    """Test get_all_categories function."""

    def test_returns_all(self):
        """Returns all categories."""
        categories = get_all_categories()
        self.assertIn(VulnerabilityCategory.REENTRANCY, categories)
        self.assertIn(VulnerabilityCategory.ACCESS_CONTROL, categories)
        self.assertIn(VulnerabilityCategory.GENERAL, categories)

    def test_count_matches(self):
        """Count matches PROPERTY_SETS."""
        categories = get_all_categories()
        self.assertEqual(len(categories), len(PROPERTY_SETS))


class TestGetCategoryFromPatternId(unittest.TestCase):
    """Test get_category_from_pattern_id function."""

    def test_reentrancy_patterns(self):
        """Recognizes reentrancy patterns."""
        self.assertEqual(
            get_category_from_pattern_id("reentrancy-001"),
            VulnerabilityCategory.REENTRANCY,
        )
        self.assertEqual(
            get_category_from_pattern_id("reentrancy-classic"),
            VulnerabilityCategory.REENTRANCY,
        )

    def test_access_control_patterns(self):
        """Recognizes access control patterns."""
        self.assertEqual(
            get_category_from_pattern_id("auth-001"),
            VulnerabilityCategory.ACCESS_CONTROL,
        )
        self.assertEqual(
            get_category_from_pattern_id("access-control"),
            VulnerabilityCategory.ACCESS_CONTROL,
        )
        self.assertEqual(
            get_category_from_pattern_id("vm-001"),
            VulnerabilityCategory.ACCESS_CONTROL,
        )

    def test_dos_patterns(self):
        """Recognizes DoS patterns."""
        self.assertEqual(
            get_category_from_pattern_id("dos-001"), VulnerabilityCategory.DOS
        )
        self.assertEqual(
            get_category_from_pattern_id("gas-griefing"), VulnerabilityCategory.DOS
        )

    def test_oracle_patterns(self):
        """Recognizes oracle patterns."""
        self.assertEqual(
            get_category_from_pattern_id("oracle-001"), VulnerabilityCategory.ORACLE
        )
        self.assertEqual(
            get_category_from_pattern_id("price-manipulation"),
            VulnerabilityCategory.ORACLE,
        )

    def test_mev_patterns(self):
        """Recognizes MEV patterns."""
        self.assertEqual(
            get_category_from_pattern_id("mev-001"), VulnerabilityCategory.MEV
        )
        self.assertEqual(
            get_category_from_pattern_id("swap-no-slippage"), VulnerabilityCategory.MEV
        )

    def test_token_patterns(self):
        """Recognizes token patterns."""
        self.assertEqual(
            get_category_from_pattern_id("token-001"), VulnerabilityCategory.TOKEN
        )
        self.assertEqual(
            get_category_from_pattern_id("erc20-transfer"), VulnerabilityCategory.TOKEN
        )

    def test_crypto_patterns(self):
        """Recognizes crypto patterns."""
        self.assertEqual(
            get_category_from_pattern_id("crypto-001"), VulnerabilityCategory.CRYPTO
        )
        self.assertEqual(
            get_category_from_pattern_id("signature-malleability"),
            VulnerabilityCategory.CRYPTO,
        )

    def test_upgrade_patterns(self):
        """Recognizes upgrade patterns."""
        self.assertEqual(
            get_category_from_pattern_id("upgrade-001"), VulnerabilityCategory.UPGRADE
        )
        self.assertEqual(
            get_category_from_pattern_id("proxy-storage-gap"),
            VulnerabilityCategory.UPGRADE,
        )

    def test_governance_patterns(self):
        """Recognizes governance patterns."""
        self.assertEqual(
            get_category_from_pattern_id("gov-001"), VulnerabilityCategory.GOVERNANCE
        )
        self.assertEqual(
            get_category_from_pattern_id("vote-manipulation"),
            VulnerabilityCategory.GOVERNANCE,
        )

    def test_unknown_returns_general(self):
        """Unknown patterns return GENERAL."""
        self.assertEqual(
            get_category_from_pattern_id("unknown-pattern"),
            VulnerabilityCategory.GENERAL,
        )


if __name__ == "__main__":
    unittest.main()
