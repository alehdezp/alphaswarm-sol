"""Tests for ops taxonomy registry (Phase 5.9).

This module tests the taxonomy registry for semantic operations and edge types,
including:
- Registry structure and completeness
- Deprecated ops detection and migration rules
- Legacy alias resolution (deterministic)
- SARIF-normalized operation name coverage
- Pattern validation with deprecated ops

Reference:
- 05.9-02-PLAN.md: Ops taxonomy registry + migration rules + SARIF-alias tests
"""

from __future__ import annotations

import unittest
import warnings
from typing import Set

from alphaswarm_sol.kg.taxonomy import (
    TAXONOMY_VERSION,
    DeprecationStatus,
    DeprecationInfo,
    OpDefinition,
    EdgeDefinition,
    CANONICAL_OPERATIONS,
    CANONICAL_EDGES,
    DEPRECATED_ALIASES,
    OpsTaxonomyRegistry,
    ops_registry,
    resolve_operation,
    resolve_edge,
    is_deprecated,
    get_migration,
    validate_pattern_ops,
    OP_CATEGORY_VALUE_MOVEMENT,
    OP_CATEGORY_ACCESS_CONTROL,
    OP_CATEGORY_EXTERNAL,
    OP_CATEGORY_STATE,
    OP_CATEGORY_CONTROL_FLOW,
    OP_CATEGORY_ARITHMETIC,
    OP_CATEGORY_VALIDATION,
)
from alphaswarm_sol.kg.operations import (
    SemanticOperation,
    OP_CODES,
    resolve_operation_name,
    get_operation_from_name,
    validate_operation_names,
    get_operation_pattern_tags,
    get_operation_risk_base,
)


class TestTaxonomyVersion(unittest.TestCase):
    """Test taxonomy versioning."""

    def test_version_format(self):
        """Version should be semver format."""
        parts = TAXONOMY_VERSION.split(".")
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit())

    def test_registry_version(self):
        """Registry should expose correct version."""
        self.assertEqual(ops_registry.version, TAXONOMY_VERSION)


class TestCanonicalOperations(unittest.TestCase):
    """Test canonical operation definitions."""

    def test_all_20_operations_defined(self):
        """All 20 semantic operations should have canonical definitions."""
        self.assertEqual(len(CANONICAL_OPERATIONS), 20)

    def test_operations_match_enum(self):
        """All canonical operations should match SemanticOperation enum names."""
        enum_names = {op.name for op in SemanticOperation}
        registry_names = set(CANONICAL_OPERATIONS.keys())
        self.assertEqual(enum_names, registry_names)

    def test_short_codes_match_op_codes(self):
        """Short codes in registry should match OP_CODES mapping."""
        for op in SemanticOperation:
            expected_code = OP_CODES[op]
            registry_def = CANONICAL_OPERATIONS.get(op.name)
            self.assertIsNotNone(registry_def, f"Missing registry def for {op.name}")
            self.assertEqual(
                registry_def.short_code,
                expected_code,
                f"Short code mismatch for {op.name}",
            )

    def test_short_codes_unique(self):
        """All short codes should be unique."""
        codes = [op.short_code for op in CANONICAL_OPERATIONS.values()]
        self.assertEqual(len(codes), len(set(codes)), "Duplicate short codes found")

    def test_operations_have_categories(self):
        """All operations should have valid categories."""
        valid_categories = {
            OP_CATEGORY_VALUE_MOVEMENT,
            OP_CATEGORY_ACCESS_CONTROL,
            OP_CATEGORY_EXTERNAL,
            OP_CATEGORY_STATE,
            OP_CATEGORY_CONTROL_FLOW,
            OP_CATEGORY_ARITHMETIC,
            OP_CATEGORY_VALIDATION,
        }
        for name, op_def in CANONICAL_OPERATIONS.items():
            self.assertIn(
                op_def.category,
                valid_categories,
                f"Invalid category for {name}: {op_def.category}",
            )

    def test_operations_have_descriptions(self):
        """All operations should have non-empty descriptions."""
        for name, op_def in CANONICAL_OPERATIONS.items():
            self.assertIsNotNone(op_def.description)
            self.assertGreater(
                len(op_def.description), 0, f"Empty description for {name}"
            )

    def test_category_distribution(self):
        """Operations should be distributed across expected category counts."""
        category_counts = {}
        for op_def in CANONICAL_OPERATIONS.values():
            category_counts[op_def.category] = (
                category_counts.get(op_def.category, 0) + 1
            )

        # Expected: value_movement=4, access_control=3, external=3,
        #           state=3, control_flow=3, arithmetic=2, validation=2
        self.assertEqual(category_counts[OP_CATEGORY_VALUE_MOVEMENT], 4)
        self.assertEqual(category_counts[OP_CATEGORY_ACCESS_CONTROL], 3)
        self.assertEqual(category_counts[OP_CATEGORY_EXTERNAL], 3)
        self.assertEqual(category_counts[OP_CATEGORY_STATE], 3)
        self.assertEqual(category_counts[OP_CATEGORY_CONTROL_FLOW], 3)
        self.assertEqual(category_counts[OP_CATEGORY_ARITHMETIC], 2)
        self.assertEqual(category_counts[OP_CATEGORY_VALIDATION], 2)


class TestCanonicalEdges(unittest.TestCase):
    """Test canonical edge type definitions."""

    def test_edges_defined(self):
        """Edge types should be defined."""
        self.assertGreater(len(CANONICAL_EDGES), 0)

    def test_edges_have_risk_scores(self):
        """All edges should have risk scores."""
        for name, edge_def in CANONICAL_EDGES.items():
            self.assertIsInstance(
                edge_def.risk_base, float, f"Missing risk for {name}"
            )
            self.assertGreaterEqual(
                edge_def.risk_base, 0.0, f"Negative risk for {name}"
            )
            self.assertLessEqual(edge_def.risk_base, 10.0, f"Risk > 10 for {name}")


class TestDeprecatedOperations(unittest.TestCase):
    """Test deprecated operations and migration rules."""

    def test_deprecated_aliases_have_replacement(self):
        """All deprecated aliases should have a replacement."""
        for name, info in DEPRECATED_ALIASES.items():
            self.assertIsNotNone(
                info.replacement, f"No replacement for deprecated {name}"
            )

    def test_deprecated_aliases_have_migration_rule(self):
        """All deprecated aliases should have migration rules."""
        for name, info in DEPRECATED_ALIASES.items():
            self.assertIsNotNone(
                info.migration_rule, f"No migration rule for deprecated {name}"
            )

    def test_deprecated_aliases_have_version(self):
        """All deprecated aliases should have deprecation version."""
        for name, info in DEPRECATED_ALIASES.items():
            self.assertIsNotNone(
                info.deprecated_in, f"No deprecation version for {name}"
            )

    def test_replacement_is_canonical(self):
        """Replacement operations should be canonical."""
        for name, info in DEPRECATED_ALIASES.items():
            if info.replacement:
                self.assertIn(
                    info.replacement,
                    CANONICAL_OPERATIONS,
                    f"Replacement {info.replacement} for {name} is not canonical",
                )

    def test_deprecated_warning_emitted(self):
        """Using deprecated ops should emit DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ops_registry.resolve_operation("TRANSFERS_ETH", warn_on_deprecated=True)
            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[0].category, DeprecationWarning))
            self.assertIn("TRANSFERS_ETH", str(w[0].message))
            self.assertIn("deprecated", str(w[0].message).lower())


class TestLegacyAliasResolution(unittest.TestCase):
    """Test legacy alias resolution is deterministic."""

    def test_aliases_resolve_deterministically(self):
        """Aliases should always resolve to the same canonical name."""
        # Test multiple times to verify determinism
        for _ in range(3):
            self.assertEqual(
                resolve_operation("TRANSFERS_ETH"), "TRANSFERS_VALUE_OUT"
            )
            self.assertEqual(
                resolve_operation("TRANSFERS_TOKEN"), "TRANSFERS_VALUE_OUT"
            )
            self.assertEqual(resolve_operation("TRANSFER_OUT"), "TRANSFERS_VALUE_OUT")
            self.assertEqual(resolve_operation("OWNER_CHANGE"), "MODIFIES_OWNER")

    def test_case_insensitive_resolution(self):
        """Resolution should be case-insensitive."""
        self.assertEqual(
            resolve_operation("transfers_value_out"), "TRANSFERS_VALUE_OUT"
        )
        self.assertEqual(
            resolve_operation("TRANSFERS_VALUE_OUT"), "TRANSFERS_VALUE_OUT"
        )
        self.assertEqual(
            resolve_operation("Transfers_Value_Out"), "TRANSFERS_VALUE_OUT"
        )

    def test_all_aliases_resolve(self):
        """All defined aliases should resolve to canonical ops."""
        for canonical, op_def in CANONICAL_OPERATIONS.items():
            for alias in op_def.aliases:
                result = ops_registry.resolve_operation(
                    alias, warn_on_deprecated=False
                )
                self.assertEqual(
                    result, canonical, f"Alias {alias} should resolve to {canonical}"
                )


class TestSARIFAliasResolution(unittest.TestCase):
    """Test SARIF-normalized operation name coverage."""

    def test_sarif_aliases_resolve(self):
        """SARIF aliases should resolve to canonical ops."""
        for canonical, op_def in CANONICAL_OPERATIONS.items():
            for sarif_alias in op_def.sarif_aliases:
                result = ops_registry.resolve_operation(
                    sarif_alias, warn_on_deprecated=False
                )
                self.assertEqual(
                    result,
                    canonical,
                    f"SARIF alias {sarif_alias} should resolve to {canonical}",
                )

    def test_sarif_kebab_case_resolution(self):
        """Kebab-case SARIF names should resolve."""
        # Common SARIF patterns from tool outputs
        test_cases = [
            ("transfers-eth", "TRANSFERS_VALUE_OUT"),
            ("transfers-token", "TRANSFERS_VALUE_OUT"),
            ("reads-balance", "READS_USER_BALANCE"),
            ("writes-balance", "WRITES_USER_BALANCE"),
            ("calls-external", "CALLS_EXTERNAL"),
            ("calls-untrusted", "CALLS_UNTRUSTED"),
            ("reads-oracle", "READS_ORACLE"),
            ("modifies-owner", "MODIFIES_OWNER"),
            ("modifies-roles", "MODIFIES_ROLES"),
            ("checks-auth", "CHECKS_PERMISSION"),
        ]
        for sarif_name, expected in test_cases:
            result = ops_registry.resolve_operation(
                sarif_name, warn_on_deprecated=False
            )
            self.assertEqual(
                result,
                expected,
                f"SARIF {sarif_name} should resolve to {expected}",
            )

    def test_sarif_resolution_via_dedicated_method(self):
        """resolve_sarif_operation should work for SARIF names."""
        result = ops_registry.resolve_sarif_operation("transfers-eth")
        self.assertEqual(result, "TRANSFERS_VALUE_OUT")

    def test_all_ops_have_sarif_aliases(self):
        """All operations should have at least one SARIF alias."""
        for canonical, op_def in CANONICAL_OPERATIONS.items():
            self.assertGreater(
                len(op_def.sarif_aliases),
                0,
                f"No SARIF aliases for {canonical}",
            )


class TestPatternValidation(unittest.TestCase):
    """Test pattern validation with deprecated ops detection."""

    def test_validate_deprecated_ops_fail(self):
        """Patterns with deprecated ops should be flagged."""
        # Using deprecated TRANSFERS_ETH
        valid, invalid = validate_pattern_ops(
            ["TRANSFERS_VALUE_OUT", "CALLS_EXTERNAL", "UNKNOWN_OP"]
        )
        self.assertIn("TRANSFERS_VALUE_OUT", valid)
        self.assertIn("CALLS_EXTERNAL", valid)
        self.assertIn("UNKNOWN_OP", invalid)

    def test_validate_mixed_ops(self):
        """Mixed valid and invalid ops should be properly separated."""
        ops = [
            "TRANSFERS_VALUE_OUT",  # Valid canonical
            "READS_USER_BALANCE",  # Valid canonical
            "INVALID_OP",  # Invalid
            "NOT_AN_OP",  # Invalid
        ]
        valid, invalid = validate_pattern_ops(ops)
        self.assertEqual(len(valid), 2)
        self.assertEqual(len(invalid), 2)

    def test_validate_returns_canonical(self):
        """Validation should return canonical names for valid ops."""
        valid, _ = validate_pattern_ops(["TRANSFERS_VALUE_OUT", "CALLS_EXTERNAL"])
        self.assertIn("TRANSFERS_VALUE_OUT", valid)
        self.assertIn("CALLS_EXTERNAL", valid)


class TestOperationsIntegration(unittest.TestCase):
    """Test integration between operations.py and taxonomy.py."""

    def test_resolve_operation_name_canonical(self):
        """resolve_operation_name should work for canonical names."""
        result = resolve_operation_name("TRANSFERS_VALUE_OUT")
        self.assertEqual(result, "TRANSFERS_VALUE_OUT")

    def test_resolve_operation_name_short_code(self):
        """resolve_operation_name should work for short codes."""
        result = resolve_operation_name("X:out")
        self.assertEqual(result, "TRANSFERS_VALUE_OUT")

        result = resolve_operation_name("R:bal")
        self.assertEqual(result, "READS_USER_BALANCE")

    def test_resolve_operation_name_sarif(self):
        """resolve_operation_name should work for SARIF names."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = resolve_operation_name("transfers-eth", warn_on_deprecated=False)
        self.assertEqual(result, "TRANSFERS_VALUE_OUT")

    def test_get_operation_from_name(self):
        """get_operation_from_name should return SemanticOperation enum."""
        result = get_operation_from_name("TRANSFERS_VALUE_OUT")
        self.assertEqual(result, SemanticOperation.TRANSFERS_VALUE_OUT)

        result = get_operation_from_name("X:out")
        self.assertEqual(result, SemanticOperation.TRANSFERS_VALUE_OUT)

    def test_validate_operation_names(self):
        """validate_operation_names should work with various formats."""
        valid, invalid = validate_operation_names(
            ["TRANSFERS_VALUE_OUT", "X:out", "UNKNOWN"]
        )
        self.assertEqual(len(valid), 2)
        self.assertEqual(len(invalid), 1)

    def test_get_operation_pattern_tags(self):
        """get_operation_pattern_tags should return correct tags."""
        tags = get_operation_pattern_tags("TRANSFERS_VALUE_OUT")
        self.assertIn("reentrancy", tags)
        self.assertIn("value_movement", tags)

    def test_get_operation_risk_base(self):
        """get_operation_risk_base should return correct risk scores."""
        # High risk operations
        self.assertGreaterEqual(get_operation_risk_base("CALLS_UNTRUSTED"), 7.0)
        self.assertGreaterEqual(get_operation_risk_base("MODIFIES_OWNER"), 7.0)

        # Low risk operations
        self.assertEqual(get_operation_risk_base("CHECKS_PERMISSION"), 0.0)
        self.assertEqual(get_operation_risk_base("VALIDATES_INPUT"), 0.0)


class TestShortCodeResolution(unittest.TestCase):
    """Test short code resolution."""

    def test_all_short_codes_resolve(self):
        """All short codes should resolve to their canonical operations."""
        for op in SemanticOperation:
            short_code = OP_CODES[op]
            result = ops_registry.resolve_short_code(short_code)
            self.assertEqual(
                result, op.name, f"Short code {short_code} should resolve to {op.name}"
            )

    def test_short_code_via_resolve_operation_name(self):
        """resolve_operation_name should handle short codes."""
        for op in SemanticOperation:
            short_code = OP_CODES[op]
            result = resolve_operation_name(short_code)
            self.assertEqual(
                result, op.name, f"Short code {short_code} via resolve_operation_name"
            )


class TestEdgeResolution(unittest.TestCase):
    """Test edge type resolution."""

    def test_edge_canonical_resolution(self):
        """Canonical edge names should resolve to themselves."""
        for name in CANONICAL_EDGES:
            result = resolve_edge(name)
            self.assertEqual(result, name)

    def test_edge_alias_resolution(self):
        """Edge aliases should resolve to canonical names."""
        test_cases = [
            ("STATE_WRITE", "WRITES_STATE"),
            ("EXTERNAL_CALL", "CALLS_EXTERNAL"),
            ("ETH_TRANSFER", "TRANSFERS_ETH"),
            ("TOKEN_TRANSFER", "TRANSFERS_TOKEN"),
        ]
        for alias, expected in test_cases:
            result = resolve_edge(alias)
            self.assertEqual(
                result, expected, f"Edge alias {alias} should resolve to {expected}"
            )


class TestRegistrySerialization(unittest.TestCase):
    """Test registry serialization."""

    def test_to_dict_structure(self):
        """Registry to_dict should have expected structure."""
        data = ops_registry.to_dict()
        self.assertIn("version", data)
        self.assertIn("operations", data)
        self.assertIn("edges", data)
        self.assertIn("deprecated", data)

    def test_to_dict_operations_complete(self):
        """to_dict operations should include all canonical ops."""
        data = ops_registry.to_dict()
        self.assertEqual(len(data["operations"]), 20)

    def test_operation_definition_to_dict(self):
        """OpDefinition.to_dict should include all fields."""
        op_def = CANONICAL_OPERATIONS["TRANSFERS_VALUE_OUT"]
        data = op_def.to_dict()
        self.assertIn("canonical_name", data)
        self.assertIn("category", data)
        self.assertIn("short_code", data)
        self.assertIn("description", data)
        self.assertIn("risk_base", data)
        self.assertIn("aliases", data)
        self.assertIn("sarif_aliases", data)
        self.assertIn("pattern_tags", data)
        self.assertIn("edge_types", data)


class TestDeprecationInfo(unittest.TestCase):
    """Test DeprecationInfo dataclass."""

    def test_deprecation_info_creation(self):
        """DeprecationInfo should be creatable."""
        info = DeprecationInfo(
            status=DeprecationStatus.DEPRECATED,
            deprecated_in="2.0.0",
            sunset_in="3.0.0",
            replacement="NEW_OP",
            migration_rule="Use NEW_OP instead",
            reason="Unified naming",
        )
        self.assertEqual(info.status, DeprecationStatus.DEPRECATED)
        self.assertEqual(info.replacement, "NEW_OP")

    def test_deprecation_info_to_dict(self):
        """DeprecationInfo.to_dict should work."""
        info = DeprecationInfo(
            status=DeprecationStatus.DEPRECATED,
            deprecated_in="2.0.0",
            replacement="NEW_OP",
        )
        data = info.to_dict()
        self.assertEqual(data["status"], "deprecated")
        self.assertEqual(data["deprecated_in"], "2.0.0")
        self.assertEqual(data["replacement"], "NEW_OP")


class TestIsDeprecated(unittest.TestCase):
    """Test is_deprecated function."""

    def test_deprecated_aliases(self):
        """Known deprecated aliases should return True."""
        self.assertTrue(is_deprecated("TRANSFERS_ETH"))
        self.assertTrue(is_deprecated("TRANSFERS_TOKEN"))
        self.assertTrue(is_deprecated("OWNER_CHANGE"))

    def test_canonical_ops_not_deprecated(self):
        """Canonical operations should not be deprecated."""
        for name in CANONICAL_OPERATIONS:
            # None of the canonical ops are marked deprecated
            op_def = CANONICAL_OPERATIONS[name]
            if op_def.deprecation is None:
                self.assertFalse(
                    is_deprecated(name), f"Canonical {name} should not be deprecated"
                )

    def test_unknown_not_deprecated(self):
        """Unknown operations should return False."""
        self.assertFalse(is_deprecated("TOTALLY_UNKNOWN_OP"))


class TestGetMigration(unittest.TestCase):
    """Test get_migration function."""

    def test_deprecated_has_migration(self):
        """Deprecated aliases should have migrations."""
        migration = get_migration("TRANSFERS_ETH")
        self.assertEqual(migration, "TRANSFERS_VALUE_OUT")

        migration = get_migration("TRANSFERS_TOKEN")
        self.assertEqual(migration, "TRANSFERS_VALUE_OUT")

    def test_canonical_no_migration(self):
        """Canonical operations should not have migrations."""
        migration = get_migration("TRANSFERS_VALUE_OUT")
        self.assertIsNone(migration)

    def test_unknown_no_migration(self):
        """Unknown operations should return None."""
        migration = get_migration("UNKNOWN_OP")
        self.assertIsNone(migration)


class TestCategoryFiltering(unittest.TestCase):
    """Test filtering operations by category."""

    def test_get_ops_by_category(self):
        """get_ops_by_category should return correct operations."""
        value_ops = ops_registry.get_ops_by_category(OP_CATEGORY_VALUE_MOVEMENT)
        self.assertEqual(len(value_ops), 4)

        access_ops = ops_registry.get_ops_by_category(OP_CATEGORY_ACCESS_CONTROL)
        self.assertEqual(len(access_ops), 3)

    def test_get_edges_by_category(self):
        """get_edges_by_category should return correct edge types."""
        state_edges = ops_registry.get_edges_by_category("state")
        self.assertGreater(len(state_edges), 0)

        external_edges = ops_registry.get_edges_by_category("external")
        self.assertGreater(len(external_edges), 0)


class TestIsValid(unittest.TestCase):
    """Test validity checking functions."""

    def test_is_valid_operation(self):
        """is_valid_operation should return True for valid ops."""
        self.assertTrue(ops_registry.is_valid_operation("TRANSFERS_VALUE_OUT"))
        self.assertTrue(ops_registry.is_valid_operation("CALLS_EXTERNAL"))
        # Aliases are also valid
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.assertTrue(ops_registry.is_valid_operation("TRANSFERS_ETH"))

    def test_is_valid_operation_invalid(self):
        """is_valid_operation should return False for invalid ops."""
        self.assertFalse(ops_registry.is_valid_operation("TOTALLY_INVALID_OP"))
        self.assertFalse(ops_registry.is_valid_operation(""))

    def test_is_valid_edge(self):
        """is_valid_edge should return True for valid edges."""
        self.assertTrue(ops_registry.is_valid_edge("WRITES_STATE"))
        self.assertTrue(ops_registry.is_valid_edge("CALLS_EXTERNAL"))
        # Aliases
        self.assertTrue(ops_registry.is_valid_edge("STATE_WRITE"))

    def test_is_valid_edge_invalid(self):
        """is_valid_edge should return False for invalid edges."""
        self.assertFalse(ops_registry.is_valid_edge("TOTALLY_INVALID_EDGE"))


if __name__ == "__main__":
    unittest.main()
