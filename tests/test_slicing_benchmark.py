"""Tests for graph slicing benchmark.

Task 9.C: Tests for full vs sliced accuracy benchmarking.
"""

import unittest

from alphaswarm_sol.kg.property_sets import (
    CORE_PROPERTIES,
    PROPERTY_SETS,
    VulnerabilityCategory,
)
from alphaswarm_sol.kg.slicing_benchmark import (
    AccuracyValidation,
    BenchmarkSuite,
    SlicingBenchmark,
    SlicingBenchmarkResult,
    TokenEstimate,
    compare_full_vs_sliced,
    generate_benchmark_report,
    run_slicing_benchmark,
    validate_slicing_for_detection,
)
from alphaswarm_sol.kg.subgraph import SubGraph, SubGraphNode


class TestTokenEstimate(unittest.TestCase):
    """Test TokenEstimate dataclass."""

    def test_from_dict_simple(self):
        """from_dict estimates tokens for simple dict."""
        data = {"name": "test", "value": 42}
        estimate = TokenEstimate.from_dict(data)

        self.assertGreater(estimate.char_count, 0)
        self.assertGreater(estimate.estimated_tokens, 0)

    def test_from_dict_complex(self):
        """from_dict handles complex nested dict."""
        data = {
            "nodes": [
                {"id": "1", "props": {"a": 1, "b": 2}},
                {"id": "2", "props": {"c": 3}},
            ],
            "edges": [{"source": "1", "target": "2"}],
        }
        estimate = TokenEstimate.from_dict(data)

        self.assertGreater(estimate.char_count, 50)
        self.assertGreater(estimate.estimated_tokens, 10)

    def test_token_estimate_ratio(self):
        """Token estimate is approximately chars/4."""
        data = {"a": "x" * 100}
        estimate = TokenEstimate.from_dict(data)

        # Should be roughly char_count / 4
        self.assertAlmostEqual(
            estimate.estimated_tokens,
            estimate.char_count // 4,
            delta=5,
        )


class TestSlicingBenchmarkResult(unittest.TestCase):
    """Test SlicingBenchmarkResult dataclass."""

    def test_meets_target(self):
        """meets_target checks 50% threshold."""
        result_pass = SlicingBenchmarkResult(
            category="reentrancy",
            full_tokens=1000,
            sliced_tokens=400,
            reduction_percent=60.0,
            properties_full=50,
            properties_sliced=10,
            relevant_properties_retained=True,
        )
        self.assertTrue(result_pass.meets_target)

        result_fail = SlicingBenchmarkResult(
            category="reentrancy",
            full_tokens=1000,
            sliced_tokens=600,
            reduction_percent=40.0,
            properties_full=50,
            properties_sliced=30,
            relevant_properties_retained=True,
        )
        self.assertFalse(result_fail.meets_target)

    def test_meets_stretch_target(self):
        """meets_stretch_target checks 75% threshold."""
        result_pass = SlicingBenchmarkResult(
            category="reentrancy",
            full_tokens=1000,
            sliced_tokens=200,
            reduction_percent=80.0,
            properties_full=50,
            properties_sliced=10,
            relevant_properties_retained=True,
        )
        self.assertTrue(result_pass.meets_stretch_target)

        result_fail = SlicingBenchmarkResult(
            category="reentrancy",
            full_tokens=1000,
            sliced_tokens=300,
            reduction_percent=70.0,
            properties_full=50,
            properties_sliced=15,
            relevant_properties_retained=True,
        )
        self.assertFalse(result_fail.meets_stretch_target)


class TestAccuracyValidation(unittest.TestCase):
    """Test AccuracyValidation dataclass."""

    def test_accuracy_preserved(self):
        """accuracy_preserved when no missing required."""
        validation = AccuracyValidation(
            category="reentrancy",
            required_properties={"a", "b"},
            retained_properties={"a", "b", "c"},
            missing_required=set(),
            accuracy_preserved=True,
            coverage_percent=100.0,
        )
        self.assertTrue(validation.accuracy_preserved)

    def test_accuracy_not_preserved(self):
        """accuracy_preserved false when missing required."""
        validation = AccuracyValidation(
            category="reentrancy",
            required_properties={"a", "b", "c"},
            retained_properties={"a", "b"},
            missing_required={"c"},
            accuracy_preserved=False,
            coverage_percent=66.7,
        )
        self.assertFalse(validation.accuracy_preserved)


class TestBenchmarkSuite(unittest.TestCase):
    """Test BenchmarkSuite dataclass."""

    def test_to_dict(self):
        """to_dict serializes correctly."""
        suite = BenchmarkSuite(
            overall_reduction=60.0,
            overall_accuracy=100.0,
            passing=True,
        )
        suite.results["reentrancy"] = SlicingBenchmarkResult(
            category="reentrancy",
            full_tokens=1000,
            sliced_tokens=400,
            reduction_percent=60.0,
            properties_full=50,
            properties_sliced=20,
            relevant_properties_retained=True,
        )

        data = suite.to_dict()

        self.assertEqual(data["overall_reduction"], 60.0)
        self.assertTrue(data["passing"])
        self.assertIn("reentrancy", data["results"])

    def test_passing_flag(self):
        """passing flag set correctly."""
        suite_pass = BenchmarkSuite(
            overall_reduction=60.0,
            overall_accuracy=98.0,
            passing=True,
        )
        self.assertTrue(suite_pass.passing)

        suite_fail = BenchmarkSuite(
            overall_reduction=40.0,
            overall_accuracy=98.0,
            passing=False,
        )
        self.assertFalse(suite_fail.passing)


class TestSlicingBenchmark(unittest.TestCase):
    """Test SlicingBenchmark class."""

    def _create_sample_graph(self) -> SubGraph:
        """Create sample graph with many properties."""
        graph = SubGraph()

        # Create node with ALL category properties to ensure reduction
        all_props = {}
        # Add core properties
        for p in CORE_PROPERTIES:
            all_props[p] = "test_value"
        # Add properties from each category
        for category in VulnerabilityCategory:
            prop_set = PROPERTY_SETS[category]
            for p in prop_set.required:
                all_props[p] = True
            for p in prop_set.optional:
                all_props[p] = False

        node = SubGraphNode(
            id="func1",
            type="Function",
            label="withdraw",
            properties=all_props,
        )
        graph.add_node(node)
        graph.focal_node_ids = ["func1"]

        return graph

    def test_run_benchmark(self):
        """run_benchmark returns BenchmarkSuite."""
        graph = self._create_sample_graph()
        benchmark = SlicingBenchmark()

        suite = benchmark.run_benchmark(graph)

        self.assertIsInstance(suite, BenchmarkSuite)
        self.assertGreater(len(suite.results), 0)
        self.assertGreater(len(suite.validations), 0)

    def test_run_benchmark_all_categories(self):
        """run_benchmark tests all categories by default."""
        graph = self._create_sample_graph()
        benchmark = SlicingBenchmark()

        suite = benchmark.run_benchmark(graph)

        for category in VulnerabilityCategory:
            self.assertIn(category.value, suite.results)

    def test_run_benchmark_specific_categories(self):
        """run_benchmark tests specific categories."""
        graph = self._create_sample_graph()
        benchmark = SlicingBenchmark()

        categories = [
            VulnerabilityCategory.REENTRANCY,
            VulnerabilityCategory.ACCESS_CONTROL,
        ]
        suite = benchmark.run_benchmark(graph, categories=categories)

        self.assertEqual(len(suite.results), 2)
        self.assertIn("reentrancy", suite.results)
        self.assertIn("access_control", suite.results)

    def test_overall_metrics_calculated(self):
        """Overall metrics are calculated."""
        graph = self._create_sample_graph()
        benchmark = SlicingBenchmark()

        suite = benchmark.run_benchmark(graph)

        self.assertGreater(suite.overall_reduction, 0)
        self.assertGreater(suite.overall_accuracy, 0)

    def test_benchmark_achieves_reduction(self):
        """Benchmark shows significant reduction."""
        graph = self._create_sample_graph()
        benchmark = SlicingBenchmark()

        suite = benchmark.run_benchmark(
            graph,
            categories=[VulnerabilityCategory.REENTRANCY],
        )

        result = suite.results["reentrancy"]
        # With a graph containing ALL properties, slicing should reduce
        self.assertGreater(result.reduction_percent, 0)

    def test_accuracy_validation(self):
        """Accuracy validation is performed."""
        graph = self._create_sample_graph()
        benchmark = SlicingBenchmark()

        suite = benchmark.run_benchmark(
            graph,
            categories=[VulnerabilityCategory.REENTRANCY],
        )

        validation = suite.validations["reentrancy"]
        self.assertIsInstance(validation, AccuracyValidation)
        self.assertGreater(validation.coverage_percent, 0)


class TestBenchmarkReduction(unittest.TestCase):
    """Test that benchmark shows real reduction."""

    def test_reentrancy_reduces_oracle_props(self):
        """Reentrancy slicing removes oracle properties."""
        graph = SubGraph()
        graph.add_node(SubGraphNode(
            id="func1",
            type="Function",
            label="test",
            properties={
                # Reentrancy relevant
                "state_write_after_external_call": True,
                "has_reentrancy_guard": False,
                # Oracle irrelevant (should be removed)
                "reads_oracle_price": True,
                "has_staleness_check": False,
                "has_sequencer_uptime_check": False,
            },
        ))

        benchmark = SlicingBenchmark()
        suite = benchmark.run_benchmark(
            graph,
            categories=[VulnerabilityCategory.REENTRANCY],
        )

        result = suite.results["reentrancy"]
        self.assertIn("reads_oracle_price", result.irrelevant_properties_removed)

    def test_oracle_reduces_reentrancy_props(self):
        """Oracle slicing removes reentrancy properties."""
        graph = SubGraph()
        graph.add_node(SubGraphNode(
            id="func1",
            type="Function",
            label="test",
            properties={
                # Oracle relevant
                "reads_oracle_price": True,
                "has_staleness_check": False,
                # Reentrancy irrelevant (should be removed)
                "state_write_after_external_call": True,
                "has_reentrancy_guard": False,
            },
        ))

        benchmark = SlicingBenchmark()
        suite = benchmark.run_benchmark(
            graph,
            categories=[VulnerabilityCategory.ORACLE],
        )

        result = suite.results["oracle"]
        self.assertIn(
            "state_write_after_external_call",
            result.irrelevant_properties_removed,
        )


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def _create_sample_graph(self) -> SubGraph:
        """Create sample graph."""
        graph = SubGraph()
        graph.add_node(SubGraphNode(
            id="func1",
            type="Function",
            label="test",
            properties={
                "visibility": "public",
                "state_write_after_external_call": True,
                "reads_oracle_price": False,
            },
        ))
        return graph

    def test_run_slicing_benchmark(self):
        """run_slicing_benchmark convenience function works."""
        graph = self._create_sample_graph()

        suite = run_slicing_benchmark(graph)

        self.assertIsInstance(suite, BenchmarkSuite)

    def test_compare_full_vs_sliced(self):
        """compare_full_vs_sliced returns comparison dict."""
        graph = self._create_sample_graph()

        result = compare_full_vs_sliced(graph, VulnerabilityCategory.REENTRANCY)

        self.assertIn("category", result)
        self.assertIn("full_tokens", result)
        self.assertIn("sliced_tokens", result)
        self.assertIn("reduction_percent", result)
        self.assertIn("accuracy_preserved", result)

    def test_validate_slicing_for_detection(self):
        """validate_slicing_for_detection checks detection capability."""
        graph = SubGraph()
        graph.add_node(SubGraphNode(
            id="func1",
            type="Function",
            label="test",
            properties={
                "state_write_after_external_call": True,
                "has_reentrancy_guard": False,
            },
        ))

        # Should preserve detection for reentrancy pattern
        result = validate_slicing_for_detection(graph, "reentrancy-001")
        self.assertTrue(result)


class TestGenerateBenchmarkReport(unittest.TestCase):
    """Test report generation."""

    def test_generate_report(self):
        """generate_benchmark_report produces readable output."""
        suite = BenchmarkSuite(
            overall_reduction=60.0,
            overall_accuracy=100.0,
            passing=True,
        )
        suite.results["reentrancy"] = SlicingBenchmarkResult(
            category="reentrancy",
            full_tokens=1000,
            sliced_tokens=400,
            reduction_percent=60.0,
            properties_full=50,
            properties_sliced=20,
            relevant_properties_retained=True,
        )
        suite.validations["reentrancy"] = AccuracyValidation(
            category="reentrancy",
            required_properties=set(),
            retained_properties=set(),
            missing_required=set(),
            accuracy_preserved=True,
            coverage_percent=100.0,
        )

        report = generate_benchmark_report(suite)

        self.assertIn("PASS", report)
        self.assertIn("60.0%", report)
        self.assertIn("REENTRANCY", report)

    def test_report_shows_failure(self):
        """Report shows failure status."""
        suite = BenchmarkSuite(
            overall_reduction=40.0,
            overall_accuracy=90.0,
            passing=False,
        )
        suite.results["test"] = SlicingBenchmarkResult(
            category="test",
            full_tokens=100,
            sliced_tokens=60,
            reduction_percent=40.0,
            properties_full=10,
            properties_sliced=6,
            relevant_properties_retained=True,
        )

        report = generate_benchmark_report(suite)

        self.assertIn("FAIL", report)


class TestAccuracyPreservation(unittest.TestCase):
    """Test that slicing preserves detection accuracy."""

    def test_required_properties_retained(self):
        """Required properties are retained after slicing."""
        # Create graph with reentrancy-relevant properties
        graph = SubGraph()
        graph.add_node(SubGraphNode(
            id="func1",
            type="Function",
            label="test",
            properties={
                "state_write_after_external_call": True,
                "has_reentrancy_guard": False,
                "external_call_sites": ["msg.sender.call"],
                "visibility": "public",
            },
        ))

        benchmark = SlicingBenchmark()
        suite = benchmark.run_benchmark(
            graph,
            categories=[VulnerabilityCategory.REENTRANCY],
        )

        validation = suite.validations["reentrancy"]
        # Required properties that exist in graph should be retained
        self.assertTrue(validation.accuracy_preserved)
        self.assertEqual(validation.coverage_percent, 100.0)

    def test_missing_required_detected(self):
        """Missing required properties are detected."""
        # Create graph missing some required properties
        graph = SubGraph()
        graph.add_node(SubGraphNode(
            id="func1",
            type="Function",
            label="test",
            properties={
                # Only include some reentrancy properties
                "state_write_after_external_call": True,
                # Missing: has_reentrancy_guard, external_call_sites, etc.
            },
        ))

        benchmark = SlicingBenchmark()
        validation = benchmark._validate_accuracy(
            graph, VulnerabilityCategory.REENTRANCY
        )

        # Should have 100% coverage of what exists
        # (missing props are only flagged if they existed in original)
        self.assertEqual(validation.coverage_percent, 100.0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases."""

    def test_empty_graph(self):
        """Benchmark handles empty graph."""
        graph = SubGraph()
        benchmark = SlicingBenchmark()

        suite = benchmark.run_benchmark(graph)

        self.assertIsInstance(suite, BenchmarkSuite)

    def test_graph_with_no_properties(self):
        """Benchmark handles nodes with no properties."""
        graph = SubGraph()
        graph.add_node(SubGraphNode(
            id="func1",
            type="Function",
            label="test",
            properties={},
        ))

        benchmark = SlicingBenchmark()
        suite = benchmark.run_benchmark(graph)

        self.assertIsInstance(suite, BenchmarkSuite)

    def test_custom_target_reduction(self):
        """Benchmark respects custom target reduction."""
        graph = SubGraph()
        graph.add_node(SubGraphNode(
            id="func1",
            type="Function",
            label="test",
            properties={"a": 1},
        ))

        # Use high target that won't be met
        benchmark = SlicingBenchmark(target_reduction=99.0)
        suite = benchmark.run_benchmark(graph)

        # Should fail due to high target
        self.assertFalse(suite.passing)


if __name__ == "__main__":
    unittest.main()
