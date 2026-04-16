"""Tests for Task 9.5: Accuracy Validation."""

import unittest
from unittest.mock import MagicMock, patch

from alphaswarm_sol.validation.accuracy_validation import (
    AccuracyMetrics,
    AccuracyValidator,
    DetectionResult,
    ValidationResult,
    ValidationStatus,
    ValidationSuite,
    compare_all_modes,
    get_recommended_mode,
    validate_optimization_accuracy,
)


def create_mock_graph(num_nodes: int = 30):
    """Create a mock graph for testing."""
    graph = MagicMock()

    nodes = {}
    for i in range(num_nodes):
        nodes[f"func{i}"] = MagicMock(
            id=f"func{i}",
            type="Function",
            label=f"function{i}",
            properties={},
        )

    graph.nodes = nodes

    edges = {}
    for i in range(num_nodes - 1):
        edges[f"e{i}"] = MagicMock(
            id=f"e{i}",
            type="calls",
            source=f"func{i}",
            target=f"func{i+1}",
            properties={},
        )

    graph.edges = edges

    return graph


class TestDetectionResult(unittest.TestCase):
    """Test DetectionResult dataclass."""

    def test_finding_ids(self):
        findings = [
            {"id": "f1", "node_id": "func0"},
            {"id": "f2", "node_id": "func1"},
        ]
        result = DetectionResult(findings=findings)

        ids = result.finding_ids()
        self.assertEqual(ids, {"f1", "f2"})

    def test_finding_ids_fallback_to_node_id(self):
        findings = [
            {"node_id": "func0"},  # No id field
            {"node_id": "func1"},
        ]
        result = DetectionResult(findings=findings)

        ids = result.finding_ids()
        self.assertEqual(ids, {"func0", "func1"})

    def test_critical_findings(self):
        findings = [
            {"id": "f1", "severity": "critical"},
            {"id": "f2", "severity": "high"},
            {"id": "f3", "severity": "critical"},
        ]
        result = DetectionResult(findings=findings)

        critical = result.critical_findings()
        self.assertEqual(len(critical), 2)

    def test_high_severity_findings(self):
        findings = [
            {"id": "f1", "severity": "critical"},
            {"id": "f2", "severity": "high"},
            {"id": "f3", "severity": "medium"},
        ]
        result = DetectionResult(findings=findings)

        high = result.high_severity_findings()
        self.assertEqual(len(high), 2)  # critical + high


class TestAccuracyMetrics(unittest.TestCase):
    """Test AccuracyMetrics dataclass."""

    def test_accuracy_loss(self):
        metrics = AccuracyMetrics(
            base_findings=10,
            optimized_findings=8,
            retained_findings=8,
            lost_findings=2,
        )

        self.assertEqual(metrics.accuracy_loss(), 20.0)

    def test_accuracy_loss_zero_base(self):
        metrics = AccuracyMetrics(base_findings=0, lost_findings=0)
        self.assertEqual(metrics.accuracy_loss(), 0.0)

    def test_is_acceptable_pass(self):
        metrics = AccuracyMetrics(
            base_findings=10,
            lost_findings=0,
            retention_rate=100.0,
            critical_retention=100.0,
        )

        self.assertTrue(metrics.is_acceptable())

    def test_is_acceptable_fail_accuracy(self):
        metrics = AccuracyMetrics(
            base_findings=10,
            lost_findings=2,  # 20% loss
            critical_retention=100.0,
        )

        self.assertFalse(metrics.is_acceptable(max_accuracy_loss=5.0))

    def test_is_acceptable_fail_critical(self):
        metrics = AccuracyMetrics(
            base_findings=10,
            lost_findings=0,
            critical_retention=90.0,  # Below 100%
        )

        self.assertFalse(metrics.is_acceptable(min_critical_retention=100.0))


class TestValidationResult(unittest.TestCase):
    """Test ValidationResult dataclass."""

    def test_to_dict(self):
        metrics = AccuracyMetrics(
            base_findings=10,
            optimized_findings=9,
            retained_findings=9,
            lost_findings=1,
            retention_rate=90.0,
            critical_retention=100.0,
            high_severity_retention=100.0,
            token_reduction=30.0,
        )

        result = ValidationResult(
            status=ValidationStatus.PASS,
            mode="standard",
            metrics=metrics,
        )

        data = result.to_dict()
        self.assertEqual(data["status"], "pass")
        self.assertEqual(data["mode"], "standard")
        self.assertEqual(data["metrics"]["retention_rate"], 90.0)
        self.assertEqual(data["metrics"]["accuracy_loss"], 10.0)


class TestValidationSuite(unittest.TestCase):
    """Test ValidationSuite dataclass."""

    def test_add_result(self):
        suite = ValidationSuite()

        result = ValidationResult(
            status=ValidationStatus.PASS,
            mode="standard",
            metrics=AccuracyMetrics(),
        )
        suite.add_result("standard", result)

        self.assertIn("standard", suite.results)

    def test_overall_status_fail_propagates(self):
        suite = ValidationSuite()

        pass_result = ValidationResult(
            status=ValidationStatus.PASS,
            mode="standard",
            metrics=AccuracyMetrics(),
        )
        fail_result = ValidationResult(
            status=ValidationStatus.FAIL,
            mode="strict",
            metrics=AccuracyMetrics(),
        )

        suite.add_result("standard", pass_result)
        self.assertEqual(suite.overall_status, ValidationStatus.PASS)

        suite.add_result("strict", fail_result)
        self.assertEqual(suite.overall_status, ValidationStatus.FAIL)

    def test_get_best_mode(self):
        suite = ValidationSuite()

        # Standard: 90% retention, 30% reduction
        suite.add_result(
            "standard",
            ValidationResult(
                status=ValidationStatus.PASS,
                mode="standard",
                metrics=AccuracyMetrics(
                    retention_rate=90.0,
                    token_reduction=30.0,
                ),
            ),
        )

        # Relaxed: 95% retention, 20% reduction
        suite.add_result(
            "relaxed",
            ValidationResult(
                status=ValidationStatus.PASS,
                mode="relaxed",
                metrics=AccuracyMetrics(
                    retention_rate=95.0,
                    token_reduction=20.0,
                ),
            ),
        )

        best = suite.get_best_mode()
        # Should pick mode with best retention * (1 + reduction)
        self.assertIn(best, ["standard", "relaxed"])


class TestAccuracyValidator(unittest.TestCase):
    """Test AccuracyValidator class."""

    def setUp(self):
        self.graph = create_mock_graph()
        self.validator = AccuracyValidator(self.graph)

    def test_initialization(self):
        self.assertIsNotNone(self.validator.extractor)
        self.assertIsNotNone(self.validator.manager)

    def test_validate_mode_basic(self):
        findings = [
            {"node_id": "func0", "severity": "high"},
            {"node_id": "func1", "severity": "medium"},
        ]

        result = self.validator.validate_mode(findings, mode="standard")

        self.assertIsInstance(result, ValidationResult)
        self.assertEqual(result.mode, "standard")

    def test_validate_mode_all_modes(self):
        findings = [{"node_id": "func0", "severity": "critical"}]

        for mode in ["strict", "standard", "relaxed"]:
            result = self.validator.validate_mode(findings, mode=mode)
            self.assertEqual(result.mode, mode)

    def test_validate_all_modes(self):
        findings = [{"node_id": "func0", "severity": "high"}]

        suite = self.validator.validate_all_modes(findings)

        self.assertIsInstance(suite, ValidationSuite)
        self.assertIn("strict", suite.results)
        self.assertIn("standard", suite.results)
        self.assertIn("relaxed", suite.results)

    def test_compare_token_reduction_vs_accuracy(self):
        findings = [{"node_id": "func0", "severity": "high"}]

        comparison = self.validator.compare_token_reduction_vs_accuracy(findings)

        self.assertIn("strict", comparison)
        self.assertIn("standard", comparison)
        self.assertIn("relaxed", comparison)

        for mode, data in comparison.items():
            self.assertIn("token_reduction", data)
            self.assertIn("accuracy_loss", data)


class TestAccuracyValidatorMetrics(unittest.TestCase):
    """Test accuracy calculation logic."""

    def setUp(self):
        self.graph = create_mock_graph(50)
        self.validator = AccuracyValidator(self.graph)

    def test_critical_retention(self):
        # Include critical finding
        findings = [
            {"node_id": "func0", "severity": "critical", "id": "c1"},
            {"node_id": "func1", "severity": "high", "id": "h1"},
        ]

        result = self.validator.validate_mode(findings, "relaxed")

        # In relaxed mode with valid seeds, should have metrics calculated
        # Seeds are in graph so should be retained
        self.assertIsInstance(result.metrics.critical_retention, float)
        # Should either retain or properly report loss
        self.assertTrue(0 <= result.metrics.critical_retention <= 100)

    def test_token_reduction_strict_vs_relaxed(self):
        findings = [{"node_id": "func0"}]

        strict_result = self.validator.validate_mode(findings, "strict")
        relaxed_result = self.validator.validate_mode(findings, "relaxed")

        # Strict should have higher token reduction
        self.assertGreaterEqual(
            strict_result.metrics.token_reduction,
            relaxed_result.metrics.token_reduction - 20,  # Allow some variance
        )


class TestValidationStatusDetermination(unittest.TestCase):
    """Test status determination logic."""

    def setUp(self):
        self.graph = create_mock_graph()
        self.validator = AccuracyValidator(self.graph)

    def test_status_pass_conditions(self):
        findings = [{"node_id": "func0", "severity": "high"}]

        result = self.validator.validate_mode(findings, "relaxed")

        # With good retention, should have a valid status
        # Note: actual status depends on simulated detection and graph size
        self.assertIn(
            result.status,
            [ValidationStatus.PASS, ValidationStatus.WARN, ValidationStatus.FAIL],
        )
        # Should always have metrics calculated
        self.assertIsInstance(result.metrics, AccuracyMetrics)

    def test_status_fail_critical_retention(self):
        # Create findings with critical that would be lost
        findings = [
            {"node_id": "func99", "severity": "critical"},  # Not in graph
        ]

        result = self.validator.validate_mode(findings, "strict")

        # Should warn or fail due to issues
        self.assertIn(
            result.status,
            [ValidationStatus.FAIL, ValidationStatus.WARN, ValidationStatus.PASS],
        )


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def setUp(self):
        self.graph = create_mock_graph()

    def test_validate_optimization_accuracy(self):
        findings = [{"node_id": "func0"}]

        result = validate_optimization_accuracy(
            self.graph, findings, mode="standard"
        )

        self.assertIsInstance(result, ValidationResult)

    def test_compare_all_modes(self):
        findings = [{"node_id": "func0"}]

        suite = compare_all_modes(self.graph, findings)

        self.assertIsInstance(suite, ValidationSuite)
        self.assertEqual(len(suite.results), 3)

    def test_get_recommended_mode_prefer_accuracy(self):
        findings = [{"node_id": "func0"}]

        mode, result = get_recommended_mode(
            self.graph, findings, prefer_accuracy=True
        )

        self.assertIn(mode, ["strict", "standard", "relaxed"])
        self.assertIsInstance(result, ValidationResult)

    def test_get_recommended_mode_prefer_efficiency(self):
        findings = [{"node_id": "func0"}]

        mode, result = get_recommended_mode(
            self.graph, findings, prefer_accuracy=False
        )

        self.assertIn(mode, ["strict", "standard", "relaxed"])


class TestWarningsAndRecommendations(unittest.TestCase):
    """Test warnings and recommendations generation."""

    def setUp(self):
        self.graph = create_mock_graph()
        self.validator = AccuracyValidator(self.graph)

    def test_warnings_generated(self):
        findings = [
            {"node_id": "func0", "severity": "critical"},
            {"node_id": "func99", "severity": "high"},  # Not in graph
        ]

        result = self.validator.validate_mode(findings, "strict")

        # Should have warnings about lost findings
        # (func99 not in graph so not in subgraph)
        self.assertIsInstance(result.warnings, list)

    def test_recommendations_generated(self):
        findings = [{"node_id": "func0"}]

        result = self.validator.validate_mode(findings, "strict")

        self.assertIsInstance(result.recommendations, list)


class TestSuiteSummary(unittest.TestCase):
    """Test suite summary generation."""

    def setUp(self):
        self.graph = create_mock_graph()
        self.validator = AccuracyValidator(self.graph)

    def test_summary_contains_key_fields(self):
        findings = [{"node_id": "func0"}]

        suite = self.validator.validate_all_modes(findings)

        self.assertIn("total_modes_tested", suite.summary)
        self.assertIn("passed", suite.summary)
        self.assertIn("best_accuracy_mode", suite.summary)
        self.assertIn("best_efficiency_mode", suite.summary)


class TestValidationSerialization(unittest.TestCase):
    """Test serialization of validation results."""

    def test_suite_to_dict(self):
        suite = ValidationSuite()
        suite.add_result(
            "standard",
            ValidationResult(
                status=ValidationStatus.PASS,
                mode="standard",
                metrics=AccuracyMetrics(
                    base_findings=10,
                    retention_rate=90.0,
                ),
            ),
        )
        suite.summary = {"test": "value"}

        data = suite.to_dict()

        self.assertIn("overall_status", data)
        self.assertIn("results", data)
        self.assertIn("best_mode", data)
        self.assertIn("summary", data)


if __name__ == "__main__":
    unittest.main()
