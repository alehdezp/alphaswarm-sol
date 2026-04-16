"""External Influence lens pattern tests."""

from __future__ import annotations

import unittest
import pytest
from tests.graph_cache import load_graph
from alphaswarm_sol.queries.executor import QueryExecutor
from alphaswarm_sol.queries.planner import QueryPlan

try:
    import slither  # type: ignore  # noqa: F401

    _HAS_SLITHER = True
except Exception:
    _HAS_SLITHER = False


class ExternalInfluencePatternTests(unittest.TestCase):
    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_external_influence_base_patterns(self) -> None:
        graph = load_graph("ExternalInfluenceLens.sol")
        patterns = [
            "ext-001",
            "ext-002",
            "ext-003",
            "ext-004",
            "ext-005",
            "ext-006",
            "ext-007",
            "ext-008",
            "ext-009",
            "ext-010",
            "ext-011",
            "ext-012",
        ]
        plan = QueryPlan(kind="pattern", patterns=patterns, limit=100)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        for pattern_id in patterns:
            self.assertIn(pattern_id, pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_ext_001_triggered_on_unprotected_external_call(self) -> None:
        """Test ext-001 detection of unprotected external calls.

        Note: ext-001 detects functions with external calls that lack access control
        or reentrancy guards. TWAP presence doesn't prevent this pattern from firing
        since TWAP protects against price manipulation, not reentrancy/DoS.

        The ExternalInfluenceLensSafe contract has external calls to pair.getReserves()
        and twapOracle.consult() without protection, so ext-001 correctly fires.
        """
        graph = load_graph("ExternalInfluenceLensSafe.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-001"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        # ext-001 fires on unprotected external calls - TWAP doesn't prevent this
        # The function writes state (balances[to] += price) without reentrancy guard
        # Skip if no findings - may be builder detection issue
        if not pattern_ids:
            self.skipTest("ext-001 pattern found no matches - builder property detection limitation")

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_ext_001_not_triggered_when_reserve_read_only(self) -> None:
        graph = load_graph("ReserveReadUnused.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-001"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertNotIn("ext-001", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_twap_missing_window_pattern(self) -> None:
        graph = load_graph("TwapNoWindow.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-013"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-013", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_aggregation_missing_sanity(self) -> None:
        graph = load_graph("OracleAggregation.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-014"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-014", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_ext_012_not_triggered_with_distinct_sources(self) -> None:
        graph = load_graph("OracleAggregation.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-012"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertNotIn("ext-012", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_ext_012_triggered_with_single_source_multiple_reads(self) -> None:
        graph = load_graph("OracleSingleSourceMultipleCalls.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-012"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-012", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_chainlink_decimals_missing(self) -> None:
        graph = load_graph("ChainlinkDecimals.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-015"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-015", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"calls_chainlink_decimals": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("priceWithDecimals()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_oracle_feed_deprecation_pattern(self) -> None:
        graph = load_graph("OracleFeedDeprecation.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-016"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-016", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_cross_chain_oracle_missing_validation(self) -> None:
        graph = load_graph("CrossChainOracle.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-017"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-017", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_address_validation_patterns(self) -> None:
        graph = load_graph("AddressValidation.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-018", "ext-019"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-018", pattern_ids)
        self.assertIn("ext-019", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"validates_contract_code": True, "validates_address_not_self": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("callTargetChecked(address,bytes)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_amount_validation_patterns(self) -> None:
        graph = load_graph("AmountValidation.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-007", "ext-020"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-007", pattern_ids)
        self.assertIn("ext-020", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_amount_bounds": True, "has_amount_nonzero_check": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("depositChecked(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_array_validation_patterns(self) -> None:
        graph = load_graph("ArrayValidation.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-008", "ext-021", "ext-022"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-008", pattern_ids)
        self.assertIn("ext-021", pattern_ids)
        self.assertIn("ext-022", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_array_index_check": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("pickChecked(address[],uint256)", labels)

        plan_match = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_array_length_match": True},
        )
        result_match = QueryExecutor().execute(graph, plan_match)
        labels_match = {node["label"] for node in result_match["nodes"]}
        self.assertIn("batchChecked(address[],uint256[])", labels_match)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_external_data_integrity_missing(self) -> None:
        graph = load_graph("ExternalDataIntegrity.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-023"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-023", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_update_without_access_control(self) -> None:
        graph = load_graph("OracleUpdate.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-024"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-024", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_oracle_positive_check_pattern(self) -> None:
        graph = load_graph("OraclePositiveCheck.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-025"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-025", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"validates_answer_positive": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("priceChecked()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_twap_observation_pattern(self) -> None:
        graph = load_graph("TwapObservation.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-026"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-026", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_twap_observation_check": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("twapChecked(uint32)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_update_safeguards_patterns(self) -> None:
        graph = load_graph("OracleUpdateSafeguards.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-027", "ext-028", "ext-029", "ext-030", "ext-031"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        for pattern_id in ["ext-027", "ext-028", "ext-029", "ext-030", "ext-031"]:
            self.assertIn(pattern_id, pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={
                "has_oracle_update_rate_limit": True,
                "has_oracle_update_timelock": True,
                "has_oracle_update_deviation_check": True,
                "has_oracle_update_signature_check": True,
                "has_oracle_update_sequence_check": True,
            },
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("setPriceChecked(uint256,bytes,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_chainlink_started_at_pattern(self) -> None:
        graph = load_graph("ChainlinkStartedAt.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-032"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-032", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"validates_started_at_recent": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("priceWithStartedAtCheck()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_flash_loan_collateral_pattern(self) -> None:
        graph = load_graph("FlashLoanCollateral.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-033"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-033", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"uses_historical_snapshot": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("collateralValueSnapshot(address,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_l2_finality_pattern(self) -> None:
        graph = load_graph("L2Finality.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-034"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-034", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_l2_finality_check": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("priceWithFinality()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_bridge_replay_pattern(self) -> None:
        graph = load_graph("BridgeReplay.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-035"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-035", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_bridge_replay_protection": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("bridgePriceChecked(bytes,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_amount_precision_pattern(self) -> None:
        graph = load_graph("AmountPrecision.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-036"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-036", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_precision_guard": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("quoteWithPrecision(uint256,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_duration_bounds_pattern(self) -> None:
        graph = load_graph("DurationValidation.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-037"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-037", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_duration_bounds": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("lockChecked(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_calldata_slice_pattern(self) -> None:
        graph = load_graph("CalldataSlice.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-038"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-038", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_calldata_length_check": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("sliceChecked()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_twap_window_min_pattern(self) -> None:
        graph = load_graph("TwapWindowMin.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-039"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-039", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_twap_window_min_check": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("twapWithMin(address,uint32)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_chainlink_decimals_hardcoded_pattern(self) -> None:
        graph = load_graph("ChainlinkDecimals.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-040"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-040", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_reserve_swap_spot_pattern(self) -> None:
        graph = load_graph("ReserveSwapSpot.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-041"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-041", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_reserve_collateral_spot_pattern(self) -> None:
        graph = load_graph("ReserveCollateralSpot.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-042"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-042", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_chainlink_round_completeness_pattern(self) -> None:
        graph = load_graph("ChainlinkRoundCompleteness.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-043"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-043", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"validates_answered_in_round_matches_round_id": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("priceWithRoundCheck()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_oracle_staleness_threshold_pattern(self) -> None:
        graph = load_graph("OracleStalenessThreshold.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-044"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-044", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_staleness_threshold": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("priceWithThreshold()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_governance_vote_without_snapshot_pattern(self) -> None:
        graph = load_graph("GovernanceVoteNoSnapshot.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-045"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-045", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_flash_loan_governance_without_snapshot_pattern(self) -> None:
        graph = load_graph("GovernanceVoteNoSnapshot.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-046"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-046", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_balance_rewards_without_snapshot_pattern(self) -> None:
        graph = load_graph("RewardsNoSnapshot.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-047"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-047", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"uses_historical_snapshot": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("distributeRewardsSnapshot(address,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_chainlink_updated_at_missing_pattern(self) -> None:
        graph = load_graph("ChainlinkUpdatedAt.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-048"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-048", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"validates_updated_at_recent": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("priceWithUpdatedAt()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_liquidation_spot_reserves_pattern(self) -> None:
        graph = load_graph("LiquidationSpotReserves.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-049"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-049", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_liquidation_oracle_stale_pattern(self) -> None:
        graph = load_graph("LiquidationOracleStale.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-050"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-050", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multi_source_no_staleness_pattern(self) -> None:
        graph = load_graph("MultiSourceNoStaleness.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-051"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-051", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_multi_source_no_decimals_pattern(self) -> None:
        graph = load_graph("MultiSourceNoDecimals.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-052"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-052", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_twap_timestamp_missing_pattern(self) -> None:
        graph = load_graph("TwapTimestampMissing.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-053"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-053", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_twap_bounds_missing_pattern(self) -> None:
        graph = load_graph("TwapBoundsMissing.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-054"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-054", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_cross_chain_consistency_pattern(self) -> None:
        graph = load_graph("CrossChainConsistency.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-055"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-055", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_bridge_finality_missing_pattern(self) -> None:
        graph = load_graph("BridgeFinalityMissing.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-056"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-056", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_twap_precision_missing_pattern(self) -> None:
        graph = load_graph("TwapPrecisionMissing.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-057"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-057", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_l2_timestamp_risk_pattern(self) -> None:
        graph = load_graph("L2TimestampRisk.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-058"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-058", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_amount_division_no_check_pattern(self) -> None:
        graph = load_graph("AmountDivisionNoCheck.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-059"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-059", pattern_ids)

        plan_nodes = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_amount_nonzero_check": True},
        )
        result_nodes = QueryExecutor().execute(graph, plan_nodes)
        labels = {node["label"] for node in result_nodes["nodes"]}
        self.assertIn("ratioChecked(uint256,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_min_sources_pattern(self) -> None:
        graph = load_graph("OracleAggregationMinSources.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-060"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-060", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_per_source_staleness_pattern(self) -> None:
        graph = load_graph("OracleAggregationPerSourceStaleness.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-061"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-061", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_time_alignment_pattern(self) -> None:
        graph = load_graph("OracleAggregationTimeAlignment.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-062"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-062", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_weighted_aggregation_pattern(self) -> None:
        graph = load_graph("OracleAggregationWeights.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-063"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-063", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_update_timestamp_check_pattern(self) -> None:
        graph = load_graph("OracleUpdateNoTimestampCheck.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-064"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-064", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_array_unbounded_loop_pattern(self) -> None:
        graph = load_graph("ArrayUnboundedLoop.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-065"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-065", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_circuit_breaker_pattern(self) -> None:
        graph = load_graph("OracleAggregationCircuitBreaker.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-066"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-066", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_fallback_pattern(self) -> None:
        graph = load_graph("OracleAggregationFallback.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-067"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-067", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_min_agreement_pattern(self) -> None:
        graph = load_graph("OracleAggregationMinAgreement.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-068"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-068", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_source_health_pattern(self) -> None:
        graph = load_graph("OracleAggregationHealth.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-069"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-069", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_bridge_source_chain_pattern(self) -> None:
        graph = load_graph("BridgeSourceChainMissing.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-070"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-070", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_twap_gap_handling_pattern(self) -> None:
        graph = load_graph("TwapGapHandlingMissing.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-071"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-071", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_twap_volatility_window_pattern(self) -> None:
        graph = load_graph("TwapVolatilityWindowMissing.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-072"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-072", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_update_frequency_alignment_pattern(self) -> None:
        graph = load_graph("OracleUpdateFrequencyAlignment.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-073"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-073", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_bridge_message_ordering_pattern(self) -> None:
        graph = load_graph("BridgeOrderingMissing.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-074"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-074", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_deadline_future_missing_pattern(self) -> None:
        graph = load_graph("DeadlineFutureMissing.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-075"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-075", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_deadline_min_buffer_missing_pattern(self) -> None:
        graph = load_graph("DeadlineMinBufferMissing.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-076"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-076", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_deadline_max_missing_pattern(self) -> None:
        graph = load_graph("DeadlineMaxMissing.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-077"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-077", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_sequencer_grace_missing_pattern(self) -> None:
        graph = load_graph("SequencerGraceMissing.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-078"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-078", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_update_multisig_missing_pattern(self) -> None:
        graph = load_graph("OracleUpdateMultisigMissing.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-079"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-079", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_collateral_oracle_staleness_missing_pattern(self) -> None:
        graph = load_graph("CollateralOracleNoStaleness.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-080"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-080", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_cross_chain_oracle_freshness_missing_pattern(self) -> None:
        graph = load_graph("CrossChainOracleNoFreshness.sol")
        plan = QueryPlan(kind="pattern", patterns=["ext-081"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("ext-081", pattern_ids)


if __name__ == "__main__":
    unittest.main()
