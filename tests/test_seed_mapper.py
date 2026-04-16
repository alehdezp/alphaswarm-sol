"""Tests for Task 9.2: Query-to-Seed Mapping."""

import unittest
from unittest.mock import MagicMock, patch

from alphaswarm_sol.kg.seed_mapper import (
    SeedMapper,
    SeedMapping,
    SeedNode,
    SeedType,
    extract_seeds_for_ppr,
    map_query_to_ppr_result,
)


def create_mock_graph():
    """Create a mock graph for testing."""
    graph = MagicMock()

    # Create nodes
    nodes = {
        "withdraw": MagicMock(
            id="withdraw",
            type="Function",
            label="withdraw",
            properties={
                "name": "withdraw",
                "visibility": "public",
                "writes_state": True,
                "has_external_calls": True,
                "has_value_transfer": True,
            },
        ),
        "deposit": MagicMock(
            id="deposit",
            type="Function",
            label="deposit",
            properties={
                "name": "deposit",
                "visibility": "public",
                "writes_state": True,
                "has_external_calls": False,
            },
        ),
        "balances": MagicMock(
            id="balances",
            type="StateVariable",
            label="balances",
            properties={"security_tags": ["user_balance"]},
        ),
        "owner": MagicMock(
            id="owner",
            type="StateVariable",
            label="owner",
            properties={"security_tags": ["privileged"]},
        ),
        "transfer": MagicMock(
            id="transfer",
            type="Function",
            label="transfer",
            properties={
                "name": "transfer",
                "visibility": "public",
                "writes_state": True,
            },
        ),
        "onlyOwner": MagicMock(
            id="onlyOwner",
            type="Modifier",
            label="onlyOwner",
            properties={},
        ),
    }
    graph.nodes = nodes

    # Create edges
    edges = {
        "e1": MagicMock(
            id="e1",
            type="writes_state",
            source="withdraw",
            target="balances",
        ),
        "e2": MagicMock(
            id="e2",
            type="writes_state",
            source="deposit",
            target="balances",
        ),
        "e3": MagicMock(
            id="e3",
            type="calls",
            source="transfer",
            target="withdraw",
        ),
        "e4": MagicMock(
            id="e4",
            type="reads_state",
            source="withdraw",
            target="owner",
        ),
    }
    graph.edges = edges

    return graph


class TestSeedNode(unittest.TestCase):
    """Test SeedNode dataclass."""

    def test_create_primary_seed(self):
        seed = SeedNode(
            id="withdraw",
            seed_type=SeedType.PRIMARY,
            source="finding",
            weight=1.5,
        )
        self.assertEqual(seed.id, "withdraw")
        self.assertEqual(seed.seed_type, SeedType.PRIMARY)
        self.assertEqual(seed.source, "finding")
        self.assertEqual(seed.weight, 1.5)

    def test_create_secondary_seed(self):
        seed = SeedNode(
            id="balances",
            seed_type=SeedType.SECONDARY,
            source="state_of:withdraw",
            weight=0.8,
        )
        self.assertEqual(seed.seed_type, SeedType.SECONDARY)

    def test_seed_equality(self):
        seed1 = SeedNode(id="func1")
        seed2 = SeedNode(id="func1", weight=2.0)
        seed3 = SeedNode(id="func2")

        self.assertEqual(seed1, seed2)  # Same ID = equal
        self.assertNotEqual(seed1, seed3)

    def test_seed_hashable(self):
        seeds = {SeedNode(id="func1"), SeedNode(id="func2")}
        self.assertEqual(len(seeds), 2)

        # Duplicate should not increase size
        seeds.add(SeedNode(id="func1", weight=5.0))
        self.assertEqual(len(seeds), 2)


class TestSeedMapping(unittest.TestCase):
    """Test SeedMapping dataclass."""

    def test_empty_mapping(self):
        mapping = SeedMapping()
        self.assertTrue(mapping.is_empty())
        self.assertEqual(mapping.all_seed_ids(), [])

    def test_all_seed_ids(self):
        mapping = SeedMapping(
            primary_seeds=[SeedNode(id="a"), SeedNode(id="b")],
            secondary_seeds=[SeedNode(id="c"), SeedNode(id="a")],  # Duplicate
            contextual_seeds=[SeedNode(id="d")],
        )

        ids = mapping.all_seed_ids()
        self.assertEqual(ids, ["a", "b", "c", "d"])  # No duplicates, priority order

    def test_primary_seed_ids(self):
        mapping = SeedMapping(
            primary_seeds=[SeedNode(id="a"), SeedNode(id="b")],
            secondary_seeds=[SeedNode(id="c")],
        )
        self.assertEqual(mapping.primary_seed_ids(), ["a", "b"])

    def test_weighted_seeds(self):
        mapping = SeedMapping(
            primary_seeds=[SeedNode(id="a", weight=1.0)],
            secondary_seeds=[SeedNode(id="b", weight=1.0)],
            contextual_seeds=[SeedNode(id="c", weight=1.0)],
        )

        weights = mapping.weighted_seeds()
        self.assertEqual(weights["a"], 1.0)  # Primary full weight
        self.assertAlmostEqual(weights["b"], 0.7)  # Secondary 70%
        self.assertAlmostEqual(weights["c"], 0.4)  # Contextual 40%

    def test_weighted_seeds_no_override(self):
        """Higher priority seeds keep their weight."""
        mapping = SeedMapping(
            primary_seeds=[SeedNode(id="a", weight=1.0)],
            secondary_seeds=[SeedNode(id="a", weight=2.0)],  # Same ID
        )

        weights = mapping.weighted_seeds()
        self.assertEqual(weights["a"], 1.0)  # Primary weight preserved


class TestSeedMapper(unittest.TestCase):
    """Test SeedMapper class."""

    def setUp(self):
        self.graph = create_mock_graph()
        self.mapper = SeedMapper(self.graph)

    def test_initialization(self):
        self.assertIn("withdraw", self.mapper._node_ids)
        self.assertIn("deposit", self.mapper._node_ids)
        self.assertIn("balances", self.mapper._node_ids)
        self.assertIn("withdraw", self.mapper._function_nodes)

    def test_adjacency_building(self):
        self.assertIn("balances", self.mapper._adjacency.get("withdraw", set()))
        self.assertIn("withdraw", self.mapper._adjacency.get("balances", set()))

    def test_from_findings_basic(self):
        findings = [
            {"node_id": "withdraw", "severity": "critical"},
            {"node_id": "deposit", "severity": "medium"},
        ]

        mapping = self.mapper.from_findings(findings, expand_context=False)

        self.assertEqual(len(mapping.primary_seeds), 2)
        self.assertIn("withdraw", mapping.primary_seed_ids())
        self.assertIn("deposit", mapping.primary_seed_ids())
        self.assertEqual(mapping.query_type, "findings")

    def test_from_findings_with_expansion(self):
        findings = [{"node_id": "withdraw"}]

        mapping = self.mapper.from_findings(findings, expand_context=True)

        # Should have primary + secondary seeds
        self.assertGreater(len(mapping.secondary_seeds), 0)
        # balances is a state variable neighbor
        secondary_ids = [s.id for s in mapping.secondary_seeds]
        self.assertIn("balances", secondary_ids)

    def test_from_findings_severity_weight(self):
        findings = [
            {"node_id": "withdraw", "severity": "critical"},
            {"node_id": "deposit", "severity": "low"},
        ]

        mapping = self.mapper.from_findings(findings, expand_context=False)

        withdraw_seed = next(s for s in mapping.primary_seeds if s.id == "withdraw")
        deposit_seed = next(s for s in mapping.primary_seeds if s.id == "deposit")

        self.assertGreater(withdraw_seed.weight, deposit_seed.weight)

    def test_from_findings_invalid_node(self):
        findings = [
            {"node_id": "withdraw"},
            {"node_id": "nonexistent"},
        ]

        mapping = self.mapper.from_findings(findings, expand_context=False)

        self.assertEqual(len(mapping.primary_seeds), 1)
        self.assertEqual(mapping.primary_seeds[0].id, "withdraw")

    def test_from_node_ids(self):
        mapping = self.mapper.from_node_ids(
            ["withdraw", "deposit", "invalid"],
            source="test",
            expand_context=False,
        )

        self.assertEqual(len(mapping.primary_seeds), 2)
        self.assertEqual(len(mapping.warnings), 1)
        self.assertIn("invalid", mapping.warnings[0])

    def test_from_function_names(self):
        mapping = self.mapper.from_function_names(
            ["withdraw", "deposit", "nonexistent"],
            expand_context=False,
        )

        primary_ids = mapping.primary_seed_ids()
        self.assertIn("withdraw", primary_ids)
        self.assertIn("deposit", primary_ids)
        self.assertEqual(len(mapping.warnings), 1)  # nonexistent warning

    def test_from_function_names_case_insensitive(self):
        mapping = self.mapper.from_function_names(
            ["WITHDRAW", "Deposit"],
            expand_context=False,
        )

        primary_ids = mapping.primary_seed_ids()
        self.assertIn("withdraw", primary_ids)
        self.assertIn("deposit", primary_ids)

    def test_from_pattern_results(self):
        results = [
            {"node_id": "withdraw", "severity": "high", "score": 0.9},
            {"node_id": "deposit", "score": 0.5},
        ]

        mapping = self.mapper.from_pattern_results(
            results,
            pattern_id="reentrancy-001",
            expand_context=False,
        )

        self.assertEqual(len(mapping.primary_seeds), 2)
        self.assertEqual(mapping.query_type, "pattern")

        withdraw_seed = next(s for s in mapping.primary_seeds if s.id == "withdraw")
        self.assertIn("reentrancy-001", withdraw_seed.source)

    def test_from_pattern_results_weight(self):
        results = [
            {"node_id": "withdraw", "severity": "critical", "score": 1.5},
            {"node_id": "deposit", "severity": "info", "score": 0.5},
        ]

        mapping = self.mapper.from_pattern_results(results, expand_context=False)

        withdraw_seed = next(s for s in mapping.primary_seeds if s.id == "withdraw")
        deposit_seed = next(s for s in mapping.primary_seeds if s.id == "deposit")

        self.assertGreater(withdraw_seed.weight, deposit_seed.weight)

    def test_secondary_seed_caller_detection(self):
        """Test that callers are added as secondary seeds."""
        findings = [{"node_id": "withdraw"}]

        mapping = self.mapper.from_findings(findings, expand_context=True)

        secondary_ids = [s.id for s in mapping.secondary_seeds]
        # transfer calls withdraw
        self.assertIn("transfer", secondary_ids)


class TestSeedMapperIntent(unittest.TestCase):
    """Test SeedMapper with Intent objects."""

    def setUp(self):
        self.graph = create_mock_graph()
        self.mapper = SeedMapper(self.graph)

    def test_from_intent_with_node_ids(self):
        intent = MagicMock()
        intent.query_kind = "fetch"
        intent.raw_text = "get nodes"
        intent.node_ids = ["withdraw", "deposit"]
        intent.properties = {}
        intent.node_types = []

        mapping = self.mapper.from_intent(intent, expand_context=False)

        self.assertEqual(len(mapping.primary_seeds), 2)
        self.assertEqual(mapping.query_type, "fetch")

    def test_from_intent_with_properties(self):
        intent = MagicMock()
        intent.query_kind = "nodes"
        intent.raw_text = "functions with external calls"
        intent.node_ids = []
        intent.properties = {"has_external_calls": True}
        intent.node_types = []

        mapping = self.mapper.from_intent(intent, expand_context=False)

        # withdraw has has_external_calls=True
        primary_ids = mapping.primary_seed_ids()
        self.assertIn("withdraw", primary_ids)

    def test_from_intent_with_node_types(self):
        intent = MagicMock()
        intent.query_kind = "nodes"
        intent.raw_text = "all state variables"
        intent.node_ids = []
        intent.properties = {}
        intent.node_types = ["StateVariable"]

        mapping = self.mapper.from_intent(intent, expand_context=False)

        primary_ids = mapping.primary_seed_ids()
        self.assertIn("balances", primary_ids)
        self.assertIn("owner", primary_ids)


class TestSeedMapperEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_empty_graph(self):
        graph = MagicMock()
        graph.nodes = {}
        graph.edges = {}

        mapper = SeedMapper(graph)
        mapping = mapper.from_findings([{"node_id": "test"}])

        self.assertTrue(mapping.is_empty())

    def test_graph_without_nodes_attr(self):
        graph = MagicMock(spec=[])  # No attributes

        mapper = SeedMapper(graph)
        self.assertEqual(len(mapper._node_ids), 0)

    def test_dict_graph_format(self):
        """Test with dict-based graph (non-object nodes)."""
        graph = MagicMock()
        graph.nodes = {
            "func1": {
                "id": "func1",
                "type": "Function",
                "label": "func1",
                "properties": {"name": "func1"},
            },
        }
        graph.edges = {}

        mapper = SeedMapper(graph)
        self.assertIn("func1", mapper._node_ids)
        self.assertIn("func1", mapper._function_nodes)

    def test_duplicate_findings(self):
        graph = create_mock_graph()
        mapper = SeedMapper(graph)

        findings = [
            {"node_id": "withdraw"},
            {"node_id": "withdraw"},  # Duplicate
            {"node_id": "deposit"},
        ]

        mapping = mapper.from_findings(findings, expand_context=False)

        # Should deduplicate
        self.assertEqual(len(mapping.primary_seeds), 2)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def setUp(self):
        self.graph = create_mock_graph()

    def test_extract_seeds_for_ppr_findings(self):
        findings = [{"node_id": "withdraw"}, {"node_id": "deposit"}]

        seeds = extract_seeds_for_ppr(self.graph, findings, source_type="findings")

        self.assertIn("withdraw", seeds)
        self.assertIn("deposit", seeds)

    def test_extract_seeds_for_ppr_pattern(self):
        results = {"matches": [{"node_id": "withdraw"}]}

        seeds = extract_seeds_for_ppr(self.graph, results, source_type="pattern")

        self.assertIn("withdraw", seeds)

    def test_extract_seeds_for_ppr_nodes(self):
        nodes = {"nodes": [{"id": "withdraw"}, {"id": "deposit"}]}

        seeds = extract_seeds_for_ppr(self.graph, nodes, source_type="nodes")

        self.assertIn("withdraw", seeds)
        self.assertIn("deposit", seeds)

    def test_extract_seeds_invalid_type(self):
        seeds = extract_seeds_for_ppr(self.graph, [], source_type="invalid")
        self.assertEqual(seeds, [])

    @patch("alphaswarm_sol.kg.seed_mapper.run_ppr")
    def test_map_query_to_ppr_result(self, mock_run_ppr):
        mock_run_ppr.return_value = MagicMock(
            scores={"withdraw": 0.5, "deposit": 0.3},
            iterations=10,
            converged=True,
        )

        findings = [{"node_id": "withdraw"}]
        mapping, ppr_result = map_query_to_ppr_result(
            self.graph,
            findings,
            source_type="findings",
            context_mode="standard",
        )

        self.assertIn("withdraw", mapping.primary_seed_ids())
        mock_run_ppr.assert_called_once()
        self.assertTrue(ppr_result.converged)

    @patch("alphaswarm_sol.kg.seed_mapper.run_ppr")
    def test_map_query_to_ppr_result_strict(self, mock_run_ppr):
        mock_run_ppr.return_value = MagicMock()

        map_query_to_ppr_result(
            self.graph,
            [{"node_id": "withdraw"}],
            source_type="findings",
            context_mode="strict",
        )

        # Check that strict config was passed
        call_args = mock_run_ppr.call_args
        config = call_args[0][2]  # Third positional arg
        self.assertEqual(config.alpha, 0.25)  # Strict alpha


class TestSeedExpansion(unittest.TestCase):
    """Test secondary seed expansion logic."""

    def setUp(self):
        self.graph = create_mock_graph()
        self.mapper = SeedMapper(self.graph)

    def test_state_variable_expansion(self):
        """State variables should be added as secondary seeds."""
        mapping = self.mapper.from_node_ids(
            ["withdraw"],
            expand_context=True,
        )

        secondary_ids = [s.id for s in mapping.secondary_seeds]
        # balances is connected to withdraw
        self.assertIn("balances", secondary_ids)

    def test_expansion_limited(self):
        """Expansion should be limited to avoid explosion."""
        # Create a graph with many connections
        graph = MagicMock()
        graph.nodes = {
            f"func{i}": MagicMock(
                id=f"func{i}",
                type="Function",
                label=f"func{i}",
                properties={"name": f"func{i}"},
            )
            for i in range(100)
        }
        graph.edges = {
            f"e{i}": MagicMock(
                type="calls",
                source="func0",
                target=f"func{i}",
            )
            for i in range(1, 100)
        }

        mapper = SeedMapper(graph)
        mapping = mapper.from_node_ids(["func0"], expand_context=True)

        # Should not explode with too many secondary seeds
        # Primary + secondary should be bounded
        total = len(mapping.primary_seeds) + len(mapping.secondary_seeds)
        self.assertLess(total, 50)


class TestFindingWeight(unittest.TestCase):
    """Test weight calculation for findings."""

    def setUp(self):
        self.graph = create_mock_graph()
        self.mapper = SeedMapper(self.graph)

    def test_critical_severity_weight(self):
        findings = [{"node_id": "withdraw", "severity": "critical"}]
        mapping = self.mapper.from_findings(findings, expand_context=False)

        weight = mapping.primary_seeds[0].weight
        self.assertGreater(weight, 1.0)  # Critical gets boost

    def test_confidence_weight(self):
        findings = [
            {"node_id": "withdraw", "confidence": 0.5},
            {"node_id": "deposit", "confidence": 1.5},
        ]
        mapping = self.mapper.from_findings(findings, expand_context=False)

        withdraw_weight = next(s.weight for s in mapping.primary_seeds if s.id == "withdraw")
        deposit_weight = next(s.weight for s in mapping.primary_seeds if s.id == "deposit")

        self.assertLess(withdraw_weight, deposit_weight)


class TestPatternWeight(unittest.TestCase):
    """Test weight calculation for pattern results."""

    def setUp(self):
        self.graph = create_mock_graph()
        self.mapper = SeedMapper(self.graph)

    def test_high_score_weight(self):
        results = [
            {"node_id": "withdraw", "score": 2.0},
            {"node_id": "deposit", "score": 0.5},
        ]
        mapping = self.mapper.from_pattern_results(results, expand_context=False)

        withdraw_weight = next(s.weight for s in mapping.primary_seeds if s.id == "withdraw")
        deposit_weight = next(s.weight for s in mapping.primary_seeds if s.id == "deposit")

        self.assertGreater(withdraw_weight, deposit_weight)


if __name__ == "__main__":
    unittest.main()
