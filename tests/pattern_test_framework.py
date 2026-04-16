"""
Pattern Test Framework

A comprehensive testing framework for VKG patterns with precision/recall tracking.
Part of Phase 4: Testing Infrastructure

This module provides:
- PatternTestSpec: Specification for pattern testing with expected matches
- PatternTestCase: Base class for pattern tests
- Precision/Recall calculation utilities
- Test report generation
"""

from __future__ import annotations

import json
import unittest
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from tests.graph_cache import load_graph
from tests.pattern_loader import load_all_patterns
from alphaswarm_sol.queries.patterns import PatternEngine


class PatternStatus(Enum):
    """Pattern quality status based on metrics."""
    DRAFT = "draft"        # precision < 70%, recall < 50%
    READY = "ready"        # precision >= 70%, recall >= 50%, variation >= 60%
    EXCELLENT = "excellent"  # precision >= 90%, recall >= 85%, variation >= 85%


@dataclass
class PatternTestSpec:
    """
    Specification for testing a vulnerability pattern.

    Attributes:
        pattern_id: The pattern identifier to test
        must_match: List of "Contract.function" that pattern MUST detect (true positives)
        must_not_match: List of "Contract.function" that pattern must NOT detect (true negatives)
        edge_cases: Optional list of edge case functions to test
        max_fp_rate: Maximum acceptable false positive rate (default 0.05 = 5%)
        description: Optional description of what this test validates
    """
    pattern_id: str
    must_match: List[str] = field(default_factory=list)
    must_not_match: List[str] = field(default_factory=list)
    edge_cases: List[str] = field(default_factory=list)
    max_fp_rate: float = 0.05
    description: str = ""


@dataclass
class PatternTestResult:
    """Result of running a pattern test."""
    pattern_id: str
    spec: PatternTestSpec

    # Counts
    true_positives: List[str] = field(default_factory=list)
    false_negatives: List[str] = field(default_factory=list)
    true_negatives: List[str] = field(default_factory=list)
    false_positives: List[str] = field(default_factory=list)

    # Metrics
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    fp_rate: float = 0.0

    # Status
    passed: bool = False
    status: PatternStatus = PatternStatus.DRAFT
    errors: List[str] = field(default_factory=list)

    def calculate_metrics(self) -> None:
        """Calculate precision, recall, F1, and FP rate."""
        tp = len(self.true_positives)
        fn = len(self.false_negatives)
        tn = len(self.true_negatives)
        fp = len(self.false_positives)

        # Precision = TP / (TP + FP)
        if tp + fp > 0:
            self.precision = tp / (tp + fp)
        else:
            self.precision = 1.0  # No predictions = no false positives

        # Recall = TP / (TP + FN)
        if tp + fn > 0:
            self.recall = tp / (tp + fn)
        else:
            self.recall = 1.0  # No expected matches = trivially complete

        # F1 = 2 * (precision * recall) / (precision + recall)
        if self.precision + self.recall > 0:
            self.f1_score = 2 * (self.precision * self.recall) / (self.precision + self.recall)
        else:
            self.f1_score = 0.0

        # FP Rate = FP / (FP + TN)
        if fp + tn > 0:
            self.fp_rate = fp / (fp + tn)
        else:
            self.fp_rate = 0.0

        # Determine status based on metrics
        self._determine_status()

    def _determine_status(self) -> None:
        """Determine pattern status based on metrics."""
        # Calculate variation score (how well it distinguishes TP from TN)
        total_expected = len(self.spec.must_match) + len(self.spec.must_not_match)
        if total_expected > 0:
            correct = len(self.true_positives) + len(self.true_negatives)
            variation = correct / total_expected
        else:
            variation = 0.0

        if self.precision >= 0.90 and self.recall >= 0.85 and variation >= 0.85:
            self.status = PatternStatus.EXCELLENT
        elif self.precision >= 0.70 and self.recall >= 0.50 and variation >= 0.60:
            self.status = PatternStatus.READY
        else:
            self.status = PatternStatus.DRAFT

        # Test passes if FP rate is within threshold and no errors
        self.passed = (
            self.fp_rate <= self.spec.max_fp_rate
            and len(self.errors) == 0
            and self.recall > 0  # Must detect at least something expected
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pattern_id": self.pattern_id,
            "true_positives": self.true_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "false_positives": self.false_positives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "fp_rate": round(self.fp_rate, 4),
            "passed": self.passed,
            "status": self.status.value,
            "errors": self.errors,
        }


class PatternTestRunner:
    """
    Runs pattern tests and collects results.

    Usage:
        runner = PatternTestRunner()
        result = runner.run_spec(spec)
        print(f"Precision: {result.precision:.1%}")
    """

    def __init__(self, patterns_dir: str = "vulndocs"):
        self.patterns = list(load_all_patterns())
        self.engine = PatternEngine()
        self._graph_cache: Dict[str, Any] = {}

    def _get_graph(self, contract_path: str) -> Any:
        """Get graph with caching."""
        if contract_path not in self._graph_cache:
            self._graph_cache[contract_path] = load_graph(contract_path)
        return self._graph_cache[contract_path]

    def _parse_function_ref(self, ref: str) -> Tuple[str, str]:
        """
        Parse "Contract.function" or "path/Contract.sol:function" reference.

        Returns:
            Tuple of (contract_path, function_name)
        """
        if ":" in ref:
            # Format: path/Contract.sol:function
            contract_path, func_name = ref.rsplit(":", 1)
        elif "." in ref and not ref.endswith(".sol"):
            # Format: Contract.function (assume .sol extension)
            parts = ref.split(".", 1)
            contract_path = parts[0] + ".sol"
            func_name = parts[1]
        else:
            raise ValueError(f"Invalid function reference: {ref}")

        return contract_path, func_name

    def _get_matching_labels(self, graph: Any, pattern_id: str) -> Set[str]:
        """Get labels of functions matched by pattern."""
        try:
            findings = self.engine.run(graph, self.patterns, pattern_ids=[pattern_id], limit=500)
            return {f["node_label"] for f in findings if f["pattern_id"] == pattern_id}
        except Exception as e:
            return set()

    def _function_matches(self, matching_labels: Set[str], func_name: str) -> bool:
        """Check if function name is in matching labels."""
        # Handle both "func" and "func(args)" formats
        for label in matching_labels:
            if label.startswith(func_name + "(") or label == func_name:
                return True
        return False

    def run_spec(self, spec: PatternTestSpec) -> PatternTestResult:
        """Run a single pattern test specification."""
        result = PatternTestResult(pattern_id=spec.pattern_id, spec=spec)

        # Group functions by contract for efficiency
        contract_funcs: Dict[str, Tuple[List[str], List[str]]] = {}

        for ref in spec.must_match:
            try:
                contract_path, func_name = self._parse_function_ref(ref)
                if contract_path not in contract_funcs:
                    contract_funcs[contract_path] = ([], [])
                contract_funcs[contract_path][0].append(func_name)
            except ValueError as e:
                result.errors.append(str(e))

        for ref in spec.must_not_match:
            try:
                contract_path, func_name = self._parse_function_ref(ref)
                if contract_path not in contract_funcs:
                    contract_funcs[contract_path] = ([], [])
                contract_funcs[contract_path][1].append(func_name)
            except ValueError as e:
                result.errors.append(str(e))

        # Run pattern on each contract
        for contract_path, (expected_match, expected_not_match) in contract_funcs.items():
            try:
                graph = self._get_graph(contract_path)
                matching_labels = self._get_matching_labels(graph, spec.pattern_id)

                # Check expected matches
                for func_name in expected_match:
                    func_ref = f"{contract_path}:{func_name}"
                    if self._function_matches(matching_labels, func_name):
                        result.true_positives.append(func_ref)
                    else:
                        result.false_negatives.append(func_ref)

                # Check expected non-matches
                for func_name in expected_not_match:
                    func_ref = f"{contract_path}:{func_name}"
                    if self._function_matches(matching_labels, func_name):
                        result.false_positives.append(func_ref)
                    else:
                        result.true_negatives.append(func_ref)

            except Exception as e:
                result.errors.append(f"Error loading {contract_path}: {str(e)}")

        result.calculate_metrics()
        return result

    def run_specs(self, specs: List[PatternTestSpec]) -> List[PatternTestResult]:
        """Run multiple pattern test specifications."""
        return [self.run_spec(spec) for spec in specs]


class PatternTestCase(unittest.TestCase):
    """
    Base class for pattern test cases.

    Subclass this to create pattern-specific tests:

        class ReentrancyPatternTests(PatternTestCase):
            def setUp(self):
                super().setUp()
                self.specs = [
                    PatternTestSpec(
                        pattern_id="reentrancy-basic",
                        must_match=["ReentrancyClassic.withdraw"],
                        must_not_match=["ReentrancyCEI.withdraw"],
                    ),
                ]

            def test_reentrancy_patterns(self):
                self.run_pattern_tests(self.specs)
    """

    @classmethod
    def setUpClass(cls):
        """Load patterns once for all tests."""
        cls.runner = PatternTestRunner()

    def run_pattern_tests(
        self,
        specs: List[PatternTestSpec],
        require_all_pass: bool = True
    ) -> List[PatternTestResult]:
        """
        Run pattern tests and assert results.

        Args:
            specs: List of PatternTestSpec to test
            require_all_pass: If True, fail if any spec doesn't pass

        Returns:
            List of PatternTestResult
        """
        results = self.runner.run_specs(specs)

        # Print results
        print(f"\n=== Pattern Test Results ===")
        for result in results:
            status_icon = "✅" if result.passed else "❌"
            print(f"\n{status_icon} {result.pattern_id}")
            print(f"    Precision: {result.precision:.1%}")
            print(f"    Recall: {result.recall:.1%}")
            print(f"    F1 Score: {result.f1_score:.3f}")
            print(f"    FP Rate: {result.fp_rate:.1%}")
            print(f"    Status: {result.status.value}")

            if result.false_negatives:
                print(f"    Missed (FN): {result.false_negatives}")
            if result.false_positives:
                print(f"    Over-matched (FP): {result.false_positives}")
            if result.errors:
                print(f"    Errors: {result.errors}")

        if require_all_pass:
            for result in results:
                self.assertTrue(
                    result.passed,
                    f"Pattern {result.pattern_id} failed: "
                    f"precision={result.precision:.1%}, "
                    f"recall={result.recall:.1%}, "
                    f"fp_rate={result.fp_rate:.1%}"
                )

        return results

    def assert_pattern_matches(
        self,
        pattern_id: str,
        contract: str,
        function: str,
        should_match: bool = True
    ) -> None:
        """Assert that a pattern matches (or doesn't match) a specific function."""
        graph = self.runner._get_graph(contract)
        matching_labels = self.runner._get_matching_labels(graph, pattern_id)
        matches = self.runner._function_matches(matching_labels, function)

        if should_match:
            self.assertTrue(
                matches,
                f"Pattern {pattern_id} should match {contract}:{function}"
            )
        else:
            self.assertFalse(
                matches,
                f"Pattern {pattern_id} should NOT match {contract}:{function}"
            )


def generate_precision_report(
    results: List[PatternTestResult],
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a comprehensive precision report.

    Args:
        results: List of PatternTestResult from test runs
        output_path: Optional path to save JSON report

    Returns:
        Report dictionary with aggregate metrics
    """
    report = {
        "summary": {
            "total_patterns": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "by_status": {
                "draft": sum(1 for r in results if r.status == PatternStatus.DRAFT),
                "ready": sum(1 for r in results if r.status == PatternStatus.READY),
                "excellent": sum(1 for r in results if r.status == PatternStatus.EXCELLENT),
            },
        },
        "aggregate_metrics": {},
        "patterns": [r.to_dict() for r in results],
    }

    # Calculate aggregate metrics
    if results:
        total_tp = sum(len(r.true_positives) for r in results)
        total_fn = sum(len(r.false_negatives) for r in results)
        total_tn = sum(len(r.true_negatives) for r in results)
        total_fp = sum(len(r.false_positives) for r in results)

        if total_tp + total_fp > 0:
            report["aggregate_metrics"]["precision"] = total_tp / (total_tp + total_fp)
        if total_tp + total_fn > 0:
            report["aggregate_metrics"]["recall"] = total_tp / (total_tp + total_fn)
        if total_fp + total_tn > 0:
            report["aggregate_metrics"]["fp_rate"] = total_fp / (total_fp + total_tn)

        report["aggregate_metrics"]["avg_precision"] = sum(r.precision for r in results) / len(results)
        report["aggregate_metrics"]["avg_recall"] = sum(r.recall for r in results) / len(results)
        report["aggregate_metrics"]["avg_f1"] = sum(r.f1_score for r in results) / len(results)

    if output_path:
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

    return report


# Convenience function for quick pattern testing
def test_pattern(
    pattern_id: str,
    must_match: List[str],
    must_not_match: List[str],
    max_fp_rate: float = 0.05,
) -> PatternTestResult:
    """
    Quick pattern test utility.

    Example:
        result = test_pattern(
            "reentrancy-basic",
            must_match=["ReentrancyClassic.withdraw"],
            must_not_match=["ReentrancyCEI.withdraw"],
        )
        print(f"Precision: {result.precision:.1%}")
    """
    spec = PatternTestSpec(
        pattern_id=pattern_id,
        must_match=must_match,
        must_not_match=must_not_match,
        max_fp_rate=max_fp_rate,
    )
    runner = PatternTestRunner()
    return runner.run_spec(spec)


if __name__ == "__main__":
    # Example usage
    specs = [
        PatternTestSpec(
            pattern_id="reentrancy-basic",
            must_match=[
                "ReentrancyClassic.withdraw",
            ],
            must_not_match=[
                "ReentrancyCEI.withdrawSafe",
                "ReentrancyWithGuard.withdraw",
            ],
            description="Basic reentrancy detection",
        ),
    ]

    runner = PatternTestRunner()
    results = runner.run_specs(specs)

    for result in results:
        print(f"\n{result.pattern_id}:")
        print(f"  Precision: {result.precision:.1%}")
        print(f"  Recall: {result.recall:.1%}")
        print(f"  Status: {result.status.value}")
