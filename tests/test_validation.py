"""Phase 21: Validation & Benchmarking Tests.

Tests for benchmarks, metrics calculation, and tool comparison.
"""

import unittest
from typing import Any, Dict, List

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node, Edge
from alphaswarm_sol.validation.benchmarks import (
    ExploitType,
    ExploitBenchmark,
    BenchmarkResult,
    BenchmarkSuite,
    KNOWN_EXPLOITS,
    run_benchmarks,
)
from alphaswarm_sol.validation.metrics import (
    ConfusionMatrix,
    DetectionMetrics,
    MetricsCalculator,
    calculate_metrics,
)
from alphaswarm_sol.validation.comparison import (
    Tool,
    ToolCapability,
    ComparisonResult,
    ToolComparisonSummary,
    ToolComparison,
    TOOL_CAPABILITIES,
    compare_tools,
)


class TestExploitType(unittest.TestCase):
    """Tests for ExploitType enum."""

    def test_types_defined(self):
        """All exploit types are defined."""
        self.assertEqual(ExploitType.REENTRANCY.value, "reentrancy")
        self.assertEqual(ExploitType.ACCESS_CONTROL.value, "access_control")
        self.assertEqual(ExploitType.ORACLE_MANIPULATION.value, "oracle_manipulation")
        self.assertEqual(ExploitType.FLASH_LOAN.value, "flash_loan")


class TestExploitBenchmark(unittest.TestCase):
    """Tests for ExploitBenchmark dataclass."""

    def test_benchmark_creation(self):
        """ExploitBenchmark can be created."""
        benchmark = ExploitBenchmark(
            id="test-001",
            name="Test Exploit",
            exploit_type=ExploitType.REENTRANCY,
            description="Test description",
            expected_findings=["reentrancy"],
        )

        self.assertEqual(benchmark.id, "test-001")
        self.assertEqual(benchmark.exploit_type, ExploitType.REENTRANCY)

    def test_to_dict(self):
        """ExploitBenchmark serializes correctly."""
        benchmark = ExploitBenchmark(
            id="test",
            name="Test",
            exploit_type=ExploitType.ACCESS_CONTROL,
            funds_lost=1_000_000,
        )

        d = benchmark.to_dict()
        self.assertEqual(d["id"], "test")
        self.assertEqual(d["exploit_type"], "access_control")
        self.assertEqual(d["funds_lost"], 1_000_000)


class TestBenchmarkResult(unittest.TestCase):
    """Tests for BenchmarkResult dataclass."""

    def test_result_creation(self):
        """BenchmarkResult can be created."""
        result = BenchmarkResult(
            benchmark_id="test-001",
            detected=True,
            findings_matched=["reentrancy"],
            findings_missed=[],
        )

        self.assertTrue(result.detected)
        self.assertEqual(result.recall, 1.0)

    def test_precision_calculation(self):
        """BenchmarkResult calculates precision."""
        result = BenchmarkResult(
            benchmark_id="test",
            detected=True,
            findings_matched=["a", "b"],
            false_positives=["c"],
        )

        self.assertAlmostEqual(result.precision, 2/3)

    def test_recall_calculation(self):
        """BenchmarkResult calculates recall."""
        result = BenchmarkResult(
            benchmark_id="test",
            detected=True,
            findings_matched=["a"],
            findings_missed=["b", "c"],
        )

        self.assertAlmostEqual(result.recall, 1/3)


class TestKnownExploits(unittest.TestCase):
    """Tests for known exploit benchmarks."""

    def test_dao_exploit(self):
        """DAO exploit benchmark is defined."""
        dao = next(e for e in KNOWN_EXPLOITS if e.id == "dao-2016")
        self.assertEqual(dao.exploit_type, ExploitType.REENTRANCY)
        self.assertIn("reentrancy", dao.expected_findings)

    def test_cream_exploit(self):
        """Cream Finance exploit benchmark is defined."""
        cream = next(e for e in KNOWN_EXPLOITS if e.id == "cream-2021")
        self.assertEqual(cream.exploit_type, ExploitType.FLASH_LOAN)

    def test_parity_exploit(self):
        """Parity wallet exploit benchmark is defined."""
        parity = next(e for e in KNOWN_EXPLOITS if e.id == "parity-2017")
        self.assertEqual(parity.exploit_type, ExploitType.ACCESS_CONTROL)


class TestBenchmarkSuite(unittest.TestCase):
    """Tests for BenchmarkSuite class."""

    def _create_vulnerable_graph(self) -> KnowledgeGraph:
        """Create a graph with vulnerabilities."""
        return KnowledgeGraph(
            nodes={
                "func1": Node(
                    id="func1",
                    label="withdraw",
                    type="Function",
                    properties={
                        "contract_name": "Vault",
                        "state_write_after_external_call": True,
                        "has_reentrancy_guard": False,
                        "transfers_value_out": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

    def test_run_benchmarks(self):
        """BenchmarkSuite runs benchmarks."""
        graph = self._create_vulnerable_graph()
        suite = BenchmarkSuite()

        results = suite.run(graph)

        self.assertGreater(len(results), 0)

    def test_detects_reentrancy(self):
        """BenchmarkSuite detects reentrancy pattern."""
        graph = self._create_vulnerable_graph()

        # Run just the DAO benchmark
        dao_benchmark = next(e for e in KNOWN_EXPLOITS if e.id == "dao-2016")
        suite = BenchmarkSuite([dao_benchmark])

        results = suite.run(graph)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].detected)
        self.assertIn("reentrancy", results[0].findings_matched)

    def test_get_summary(self):
        """BenchmarkSuite generates summary."""
        graph = self._create_vulnerable_graph()
        suite = BenchmarkSuite()

        results = suite.run(graph)
        summary = suite.get_summary(results)

        self.assertIn("total_benchmarks", summary)
        self.assertIn("precision", summary)
        self.assertIn("recall", summary)


class TestRunBenchmarks(unittest.TestCase):
    """Tests for run_benchmarks function."""

    def test_run_benchmarks(self):
        """run_benchmarks convenience function works."""
        graph = KnowledgeGraph(
            nodes={
                "func1": Node(
                    id="func1",
                    label="test",
                    type="Function",
                    properties={
                        "state_write_after_external_call": True,
                        "has_reentrancy_guard": False,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        result = run_benchmarks(graph)

        self.assertIn("results", result)
        self.assertIn("summary", result)


class TestConfusionMatrix(unittest.TestCase):
    """Tests for ConfusionMatrix dataclass."""

    def test_matrix_creation(self):
        """ConfusionMatrix can be created."""
        matrix = ConfusionMatrix(
            true_positives=10,
            false_positives=2,
            true_negatives=80,
            false_negatives=8,
        )

        self.assertEqual(matrix.total, 100)

    def test_precision(self):
        """ConfusionMatrix calculates precision."""
        matrix = ConfusionMatrix(true_positives=8, false_positives=2)
        self.assertAlmostEqual(matrix.precision, 0.8)

    def test_recall(self):
        """ConfusionMatrix calculates recall."""
        matrix = ConfusionMatrix(true_positives=8, false_negatives=2)
        self.assertAlmostEqual(matrix.recall, 0.8)

    def test_f1_score(self):
        """ConfusionMatrix calculates F1 score."""
        matrix = ConfusionMatrix(
            true_positives=8,
            false_positives=2,
            false_negatives=2,
        )
        # Precision = 0.8, Recall = 0.8, F1 = 0.8
        self.assertAlmostEqual(matrix.f1_score, 0.8)

    def test_accuracy(self):
        """ConfusionMatrix calculates accuracy."""
        matrix = ConfusionMatrix(
            true_positives=8,
            false_positives=2,
            true_negatives=80,
            false_negatives=10,
        )
        self.assertAlmostEqual(matrix.accuracy, 0.88)

    def test_add_prediction(self):
        """ConfusionMatrix adds predictions correctly."""
        matrix = ConfusionMatrix()

        matrix.add_prediction(True, True)   # TP
        matrix.add_prediction(True, False)  # FP
        matrix.add_prediction(False, True)  # FN
        matrix.add_prediction(False, False) # TN

        self.assertEqual(matrix.true_positives, 1)
        self.assertEqual(matrix.false_positives, 1)
        self.assertEqual(matrix.true_negatives, 1)
        self.assertEqual(matrix.false_negatives, 1)

    def test_false_positive_rate(self):
        """ConfusionMatrix calculates FPR."""
        matrix = ConfusionMatrix(false_positives=5, true_negatives=95)
        self.assertAlmostEqual(matrix.false_positive_rate, 0.05)


class TestDetectionMetrics(unittest.TestCase):
    """Tests for DetectionMetrics dataclass."""

    def test_metrics_creation(self):
        """DetectionMetrics can be created."""
        metrics = DetectionMetrics()
        self.assertEqual(metrics.overall.total, 0)

    def test_add_result(self):
        """DetectionMetrics adds results."""
        metrics = DetectionMetrics()

        metrics.add_result(True, True, category="reentrancy", severity="critical")
        metrics.add_result(False, False, category="access", severity="high")

        self.assertEqual(metrics.overall.total, 2)
        self.assertIn("reentrancy", metrics.by_category)
        self.assertIn("critical", metrics.by_severity)

    def test_to_report(self):
        """DetectionMetrics generates report."""
        metrics = DetectionMetrics()
        metrics.add_result(True, True, category="test")

        report = metrics.to_report()

        self.assertIn("Detection Metrics Report", report)
        self.assertIn("Precision", report)
        self.assertIn("Recall", report)


class TestMetricsCalculator(unittest.TestCase):
    """Tests for MetricsCalculator class."""

    def test_add_sample(self):
        """MetricsCalculator adds samples."""
        calc = MetricsCalculator()

        calc.add_sample(
            predicted_vulns=["reentrancy", "access"],
            actual_vulns=["reentrancy"],
        )

        metrics = calc.get_metrics()
        self.assertGreater(metrics.overall.total, 0)

    def test_binary_result(self):
        """MetricsCalculator handles binary results."""
        calc = MetricsCalculator()

        calc.add_binary_result(True, True, category="test")
        calc.add_binary_result(True, False, category="test")

        metrics = calc.get_metrics()
        self.assertEqual(metrics.overall.true_positives, 1)
        self.assertEqual(metrics.overall.false_positives, 1)

    def test_meets_targets(self):
        """MetricsCalculator checks targets."""
        calc = MetricsCalculator()

        # Add perfect results
        for _ in range(10):
            calc.add_binary_result(True, True)

        targets = calc.meets_targets()

        self.assertTrue(targets["precision_met"])
        self.assertTrue(targets["recall_met"])

    def test_reset(self):
        """MetricsCalculator resets correctly."""
        calc = MetricsCalculator()
        calc.add_binary_result(True, True)
        calc.reset()

        metrics = calc.get_metrics()
        self.assertEqual(metrics.overall.total, 0)


class TestCalculateMetrics(unittest.TestCase):
    """Tests for calculate_metrics function."""

    def test_calculate_metrics(self):
        """calculate_metrics convenience function works."""
        predictions = [
            {"id": "1", "vulnerabilities": ["reentrancy"]},
            {"id": "2", "vulnerabilities": ["access"]},
        ]
        ground_truth = [
            {"id": "1", "vulnerabilities": ["reentrancy"]},
            {"id": "2", "vulnerabilities": []},
        ]

        metrics = calculate_metrics(predictions, ground_truth)

        self.assertGreater(metrics.overall.total, 0)


class TestTool(unittest.TestCase):
    """Tests for Tool enum."""

    def test_tools_defined(self):
        """All tools are defined."""
        self.assertEqual(Tool.VKG.value, "vkg")
        self.assertEqual(Tool.SLITHER.value, "slither")
        self.assertEqual(Tool.MYTHRIL.value, "mythril")


class TestToolCapability(unittest.TestCase):
    """Tests for ToolCapability dataclass."""

    def test_capability_creation(self):
        """ToolCapability can be created."""
        cap = ToolCapability(
            tool=Tool.VKG,
            vulnerability_types=["reentrancy", "access"],
            analysis_depth="semantic graph",
        )

        self.assertEqual(cap.tool, Tool.VKG)
        self.assertEqual(len(cap.vulnerability_types), 2)


class TestToolCapabilities(unittest.TestCase):
    """Tests for known tool capabilities."""

    def test_vkg_capabilities(self):
        """VKG capabilities are defined."""
        cap = TOOL_CAPABILITIES[Tool.VKG]
        self.assertIn("reentrancy", cap.vulnerability_types)
        self.assertLess(cap.false_positive_rate, 0.1)

    def test_slither_capabilities(self):
        """Slither capabilities are defined."""
        cap = TOOL_CAPABILITIES[Tool.SLITHER]
        self.assertIn("reentrancy", cap.vulnerability_types)

    def test_mythril_capabilities(self):
        """Mythril capabilities are defined."""
        cap = TOOL_CAPABILITIES[Tool.MYTHRIL]
        self.assertEqual(cap.analysis_depth, "symbolic execution")


class TestToolComparison(unittest.TestCase):
    """Tests for ToolComparison class."""

    def test_add_result(self):
        """ToolComparison adds results."""
        comp = ToolComparison([Tool.VKG, Tool.SLITHER])

        comp.add_result(
            vulnerability="reentrancy",
            tool_results={Tool.VKG: True, Tool.SLITHER: True},
            ground_truth=True,
        )

        summary = comp.get_summary()
        self.assertEqual(len(summary.results), 1)

    def test_get_summary(self):
        """ToolComparison generates summary."""
        comp = ToolComparison([Tool.VKG, Tool.SLITHER])

        comp.add_result("vuln1", {Tool.VKG: True, Tool.SLITHER: False}, True)
        comp.add_result("vuln2", {Tool.VKG: True, Tool.SLITHER: True}, True)

        summary = comp.get_summary()

        # VKG detected both, Slither detected one
        self.assertEqual(summary.recall_by_tool[Tool.VKG], 1.0)
        self.assertEqual(summary.recall_by_tool[Tool.SLITHER], 0.5)

    def test_markdown_table(self):
        """ToolComparison generates markdown table."""
        comp = ToolComparison([Tool.VKG])
        comp.add_result("test", {Tool.VKG: True}, True)

        summary = comp.get_summary()
        table = summary.to_markdown_table()

        self.assertIn("| Tool |", table)
        self.assertIn("| vkg |", table)

    def test_get_tool_capabilities(self):
        """ToolComparison retrieves tool capabilities."""
        comp = ToolComparison()
        cap = comp.get_tool_capabilities(Tool.VKG)

        self.assertIsNotNone(cap)
        self.assertEqual(cap.tool, Tool.VKG)


class TestCompareTools(unittest.TestCase):
    """Tests for compare_tools function."""

    def test_compare_tools(self):
        """compare_tools convenience function works."""
        results = [
            {
                "vulnerability": "reentrancy",
                "tool_results": {"vkg": True, "slither": True},
                "ground_truth": True,
            },
            {
                "vulnerability": "access",
                "tool_results": {"vkg": True, "slither": False},
                "ground_truth": True,
            },
        ]

        summary = compare_tools(results, [Tool.VKG, Tool.SLITHER])

        self.assertEqual(summary.precision_by_tool[Tool.VKG], 1.0)
        self.assertEqual(summary.recall_by_tool[Tool.VKG], 1.0)


if __name__ == "__main__":
    unittest.main()
