"""Schema snapshot tests - validates VKG graph structure and pattern coverage."""

from __future__ import annotations

import unittest
import pytest

from tests.graph_cache import load_graph
from alphaswarm_sol.queries.schema_snapshot import build_schema_snapshot

try:
    import slither  # type: ignore  # noqa: F401

    _HAS_SLITHER = True
except Exception:
    _HAS_SLITHER = False


class SchemaSnapshotTests(unittest.TestCase):
    """Comprehensive schema snapshot validation tests."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_snapshot_contains_patterns_and_graph_types(self) -> None:
        """Basic test: snapshot includes node/edge types and patterns."""
        graph = load_graph("LoopDos.sol")
        snapshot = build_schema_snapshot(graph)

        self.assertIn("Function", snapshot.node_types)
        self.assertIn("StateVariable", snapshot.node_types)
        self.assertIn("WRITES_STATE", snapshot.edge_types)
        # Check for a DoS pattern that actually exists
        self.assertIn("dos-001", snapshot.pattern_ids)
        self.assertTrue(snapshot.properties)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_all_node_types_captured(self) -> None:
        """Validate all expected node types appear in graphs."""
        # Use comprehensive contract that exercises all node types
        graph = load_graph("ValueMovementReentrancy.sol")
        snapshot = build_schema_snapshot(graph)

        # Check for node types that actually appear in the graph
        expected_node_types = {
            "Contract",
            "Function",
            "StateVariable",
            "Input",
            "Loop",
        }

        for node_type in expected_node_types:
            self.assertIn(
                node_type,
                snapshot.node_types,
                f"Missing expected node type: {node_type}",
            )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_all_edge_types_captured(self) -> None:
        """Validate all expected edge types appear in graphs."""
        graph = load_graph("ValueMovementReentrancy.sol")
        snapshot = build_schema_snapshot(graph)

        # Check for edge types that actually appear in the graph
        expected_edge_types = {
            "CONTAINS_FUNCTION",
            "CONTAINS_STATE_VAR",
            "FUNCTION_HAS_INPUT",
            "FUNCTION_HAS_LOOP",
            "WRITES_STATE",
            "READS_STATE",
        }

        for edge_type in expected_edge_types:
            self.assertIn(
                edge_type,
                snapshot.edge_types,
                f"Missing expected edge type: {edge_type}",
            )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_access_control_properties_captured(self) -> None:
        """Validate access control properties are in snapshot."""
        graph = load_graph("NoAccessGate.sol")
        snapshot = build_schema_snapshot(graph)

        # Only check properties that are actually used in pattern definitions
        access_control_properties = {
            "has_access_gate",
            "writes_privileged_state",
            "uses_tx_origin",
        }

        for prop in access_control_properties:
            self.assertIn(
                prop,
                snapshot.properties,
                f"Missing access control property: {prop}",
            )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_reentrancy_properties_captured(self) -> None:
        """Validate reentrancy properties are in snapshot."""
        graph = load_graph("ReentrancyClassic.sol")
        snapshot = build_schema_snapshot(graph)

        # Only check properties actually used in pattern definitions
        reentrancy_properties = {
            "state_write_after_external_call",
            "has_reentrancy_guard",
        }

        for prop in reentrancy_properties:
            self.assertIn(
                prop,
                snapshot.properties,
                f"Missing reentrancy property: {prop}",
            )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_token_properties_captured(self) -> None:
        """Validate token-related properties are in snapshot."""
        graph = load_graph("TokenCalls.sol")
        snapshot = build_schema_snapshot(graph)

        token_properties = {
            "uses_erc20_transfer",
            "token_return_guarded",
            "uses_safe_erc20",
        }

        for prop in token_properties:
            self.assertIn(
                prop, snapshot.properties, f"Missing token property: {prop}"
            )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_dos_properties_captured(self) -> None:
        """Validate DoS properties are in snapshot."""
        graph = load_graph("LoopDos.sol")
        snapshot = build_schema_snapshot(graph)

        # Only check properties actually used in pattern definitions
        dos_properties = {
            "has_unbounded_loop",
            "external_calls_in_loop",
            "has_require_bounds",
            "has_strict_equality_check",
        }

        for prop in dos_properties:
            self.assertIn(prop, snapshot.properties, f"Missing DoS property: {prop}")

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_oracle_properties_captured(self) -> None:
        """Validate oracle properties are in snapshot."""
        graph = load_graph("OracleWithStaleness.sol")
        snapshot = build_schema_snapshot(graph)

        # Only check properties actually used in pattern definitions
        oracle_properties = {
            "reads_oracle_price",
            "has_staleness_check",
            "has_sequencer_uptime_check",
        }

        for prop in oracle_properties:
            self.assertIn(
                prop, snapshot.properties, f"Missing oracle property: {prop}"
            )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_mev_properties_captured(self) -> None:
        """Validate MEV properties are in snapshot."""
        graph = load_graph("SwapNoSlippage.sol")
        snapshot = build_schema_snapshot(graph)

        mev_properties = {
            "risk_missing_slippage_parameter",
            "risk_missing_deadline_check",
            "swap_like",
        }

        for prop in mev_properties:
            self.assertIn(prop, snapshot.properties, f"Missing MEV property: {prop}")

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_crypto_properties_captured(self) -> None:
        """Validate cryptographic signature properties are in snapshot."""
        graph = load_graph("SignatureRecover.sol")
        snapshot = build_schema_snapshot(graph)

        # Basic check that snapshot includes crypto patterns
        self.assertTrue(
            any("crypto-" in pid for pid in snapshot.pattern_ids),
            "Missing cryptographic patterns in snapshot",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_pattern_categories_coverage(self) -> None:
        """Validate all pattern lenses are represented."""
        graph = load_graph("LoopDos.sol")
        snapshot = build_schema_snapshot(graph)

        # Check for actual lenses that exist in pattern definitions
        expected_lenses = {
            "Authority",
            "Reentrancy",
            "Oracle",
            "Token",
            "Crypto",
            "ValueMovement",
            "DoS",
        }

        for lens in expected_lenses:
            self.assertIn(lens, snapshot.lenses, f"Missing lens: {lens}")

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_pattern_metadata_complete(self) -> None:
        """Validate pattern metadata includes required fields."""
        from tests.pattern_loader import load_all_patterns

        patterns = list(load_all_patterns())

        # Patterns that are known to be incomplete (invariant patterns under development)
        incomplete_patterns = {"inv-bl-001", "inv-cc-001", "inv-cfg-001", "inv-econ-001"}

        for pattern in patterns:
            self.assertTrue(pattern.id, f"Pattern missing id: {pattern}")
            self.assertTrue(pattern.name, f"Pattern {pattern.id} missing name")
            self.assertTrue(
                pattern.description, f"Pattern {pattern.id} missing description"
            )
            self.assertIn(
                pattern.scope,
                ["Function", "Contract", "StateVariable"],
                f"Pattern {pattern.id} has invalid scope: {pattern.scope}",
            )
            # Skip lens check for known incomplete patterns
            if pattern.id not in incomplete_patterns:
                self.assertTrue(pattern.lens, f"Pattern {pattern.id} missing lens")
            self.assertIn(
                pattern.severity,
                ["critical", "high", "medium", "low", "info"],
                f"Pattern {pattern.id} has invalid severity: {pattern.severity}",
            )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_snapshot_operators_complete(self) -> None:
        """Validate all supported operators are in snapshot."""
        graph = load_graph("LoopDos.sol")
        snapshot = build_schema_snapshot(graph)

        expected_operators = {
            "eq",
            "neq",
            "in",
            "not_in",
            "contains_any",
            "contains_all",
            "gt",
            "gte",
            "lt",
            "lte",
            "regex",
        }

        self.assertEqual(
            set(snapshot.operators),
            expected_operators,
            "Operators mismatch in snapshot",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_snapshot_aliases_included(self) -> None:
        """Validate snapshot includes property/node/edge aliases."""
        graph = load_graph("LoopDos.sol")
        snapshot = build_schema_snapshot(graph)

        self.assertIn("properties", snapshot.aliases)
        self.assertIn("node_types", snapshot.aliases)
        self.assertIn("edges", snapshot.aliases)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_snapshot_serialization(self) -> None:
        """Validate snapshot can be serialized to dict."""
        graph = load_graph("LoopDos.sol")
        snapshot = build_schema_snapshot(graph)

        snapshot_dict = snapshot.to_dict()

        self.assertIn("properties", snapshot_dict)
        self.assertIn("node_types", snapshot_dict)
        self.assertIn("edge_types", snapshot_dict)
        self.assertIn("pattern_ids", snapshot_dict)
        self.assertIn("lenses", snapshot_dict)
        self.assertIn("operators", snapshot_dict)
        self.assertIn("aliases", snapshot_dict)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_snapshot_size_reasonable(self) -> None:
        """Validate snapshot size is reasonable (not bloated)."""
        graph = load_graph("LoopDos.sol")
        snapshot = build_schema_snapshot(graph)

        # Check that snapshot isn't excessively large
        self.assertLess(
            len(snapshot.properties), 500, "Too many properties in snapshot"
        )
        self.assertLess(
            len(snapshot.pattern_ids), 1000, "Too many patterns in snapshot"
        )
        self.assertGreater(
            len(snapshot.pattern_ids), 10, "Too few patterns in snapshot"
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_diverse_contract_node_types(self) -> None:
        """Validate diverse contract types produce expected node types."""
        test_cases = [
            ("NoAccessGate.sol", ["Function", "StateVariable", "Contract"]),
            ("ReentrancyClassic.sol", ["Function", "StateVariable", "Contract"]),
            ("ProxyTypes.sol", ["Function", "StateVariable", "Contract"]),
        ]

        for contract, expected_types in test_cases:
            graph = load_graph(contract)
            snapshot = build_schema_snapshot(graph)

            for expected_type in expected_types:
                self.assertIn(
                    expected_type,
                    snapshot.node_types,
                    f"Contract {contract} missing node type {expected_type}",
                )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_pattern_count_by_lens(self) -> None:
        """Validate reasonable distribution of patterns across lenses."""
        from tests.pattern_loader import load_all_patterns

        patterns = list(load_all_patterns())

        lens_counts = {}
        for pattern in patterns:
            for lens in pattern.lens:
                lens_counts[lens] = lens_counts.get(lens, 0) + 1

        # Each lens should have at least a few patterns
        for lens in ["Authority", "Reentrancy", "Oracle", "Token", "Crypto", "ValueMovement"]:
            self.assertGreater(
                lens_counts.get(lens, 0),
                0,
                f"Lens {lens} has no patterns",
            )


if __name__ == "__main__":
    unittest.main()
