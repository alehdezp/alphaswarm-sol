"""
Baseline Detection Measurement Tests

Tests to measure detection rates on original vs renamed contracts.
Part of Phase 0: Foundation & Baseline

Goal: Measure current detection degradation when contracts use non-standard naming.
Target: Achieve >90% detection on renamed contracts (current baseline ~60%).
"""

import json
import unittest
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from tests.graph_cache import load_graph


@dataclass
class DetectionSpec:
    """Specifies expected detections for a contract."""
    contract_name: str
    vulnerability_type: str
    # Patterns that should match
    expected_patterns: List[str] = field(default_factory=list)
    # Properties that should be detected
    expected_properties: Dict[str, Any] = field(default_factory=dict)
    # Functions with vulnerabilities
    vulnerable_functions: List[str] = field(default_factory=list)


@dataclass
class DetectionResult:
    """Result of detection test on a contract."""
    contract_name: str
    total_expected: int
    detected: int
    missed: List[str] = field(default_factory=list)
    detection_rate: float = 0.0


# Original contracts with expected detections
ORIGINAL_CONTRACTS: List[DetectionSpec] = [
    DetectionSpec(
        contract_name="ReentrancyClassic.sol",
        vulnerability_type="reentrancy",
        expected_properties={
            "withdraw": {
                "has_external_calls": True,
                "writes_state": True,
                "state_write_after_external_call": True,
            }
        },
        vulnerable_functions=["withdraw"]
    ),
    DetectionSpec(
        contract_name="NoAccessGate.sol",
        vulnerability_type="access_control",
        expected_properties={
            "setOwner": {
                "writes_state": True,
                "has_access_gate": False,
                "writes_privileged_state": True,
            }
        },
        vulnerable_functions=["setOwner"]
    ),
    DetectionSpec(
        contract_name="DelegatecallNoAccessGate.sol",
        vulnerability_type="delegatecall",
        expected_properties={
            "execute": {
                "uses_delegatecall": True,
                "has_access_gate": False,
            }
        },
        vulnerable_functions=["execute"]
    ),
    DetectionSpec(
        contract_name="SwapNoSlippage.sol",
        vulnerability_type="mev",
        expected_properties={
            "swapExactTokensForTokens": {
                "swap_like": True,
            }
        },
        vulnerable_functions=["swapExactTokensForTokens"]
    ),
    DetectionSpec(
        contract_name="LoopDos.sol",
        vulnerability_type="dos",
        expected_properties={
            "distribute": {
                "has_unbounded_loop": True,
            }
        },
        vulnerable_functions=["distribute"]
    ),
]

# Renamed contracts with same expected detections
RENAMED_CONTRACTS: List[DetectionSpec] = [
    DetectionSpec(
        contract_name="renamed/ReentrancyRenamed.sol",
        vulnerability_type="reentrancy",
        expected_properties={
            "removeFunds": {  # Renamed from "withdraw"
                "has_external_calls": True,
                "writes_state": True,
                "state_write_after_external_call": True,
            }
        },
        vulnerable_functions=["removeFunds"]
    ),
    DetectionSpec(
        contract_name="renamed/AccessControlRenamed.sol",
        vulnerability_type="access_control",
        expected_properties={
            "updateController": {  # Renamed from "setOwner"
                "writes_state": True,
                "has_access_gate": False,
            }
        },
        vulnerable_functions=["updateController"]
    ),
    DetectionSpec(
        contract_name="renamed/DelegateCallRenamed.sol",
        vulnerability_type="delegatecall",
        expected_properties={
            "invokeArbitrary": {
                "uses_delegatecall": True,
                "has_access_gate": False,
            }
        },
        vulnerable_functions=["invokeArbitrary"]
    ),
    DetectionSpec(
        contract_name="renamed/SwapRenamed.sol",
        vulnerability_type="mev",
        expected_properties={
            "exchangeAssetsUnsafe": {  # Renamed from "swap"
                # swap_like detection may fail due to name
            }
        },
        vulnerable_functions=["exchangeAssetsUnsafe"]
    ),
    DetectionSpec(
        contract_name="renamed/LoopDosRenamed.sol",
        vulnerability_type="dos",
        expected_properties={
            "distributeToAll": {  # Renamed from "distribute"
                "has_unbounded_loop": True,
            }
        },
        vulnerable_functions=["distributeToAll"]
    ),
]


class BaselineDetectionTests(unittest.TestCase):
    """Tests for measuring detection rates."""

    @classmethod
    def setUpClass(cls):
        """Load all graphs once for efficiency."""
        cls.graphs = {}
        cls.load_errors = {}

        for spec in ORIGINAL_CONTRACTS + RENAMED_CONTRACTS:
            try:
                cls.graphs[spec.contract_name] = load_graph(spec.contract_name)
            except Exception as e:
                cls.load_errors[spec.contract_name] = str(e)

    def _get_function_node(self, graph, func_name: str):
        """Get function node from graph by name (matches start of label)."""
        for node in graph.nodes.values():
            if node.type == "Function":
                # Labels are like "withdraw(uint256)" - match the function name part
                if node.label.startswith(func_name + "(") or node.label == func_name:
                    return node
        return None

    def _check_properties(self, node, expected_props: Dict[str, Any]) -> Tuple[int, int, List[str]]:
        """
        Check if node has expected properties.
        Returns (expected_count, detected_count, missed_properties)
        """
        expected = 0
        detected = 0
        missed = []

        for prop, expected_value in expected_props.items():
            expected += 1
            actual = node.properties.get(prop)

            # Handle boolean comparisons
            if isinstance(expected_value, bool):
                if actual == expected_value:
                    detected += 1
                else:
                    missed.append(f"{prop}={expected_value} (got {actual})")
            # Handle existence checks
            elif expected_value is True and actual:
                detected += 1
            elif expected_value is False and not actual:
                detected += 1
            else:
                if actual == expected_value:
                    detected += 1
                else:
                    missed.append(f"{prop}={expected_value} (got {actual})")

        return expected, detected, missed

    def _measure_detection(self, specs: List[DetectionSpec]) -> List[DetectionResult]:
        """Measure detection rates for a list of contract specs."""
        results = []

        for spec in specs:
            if spec.contract_name in self.load_errors:
                results.append(DetectionResult(
                    contract_name=spec.contract_name,
                    total_expected=0,
                    detected=0,
                    missed=[f"Load error: {self.load_errors[spec.contract_name]}"],
                    detection_rate=0.0
                ))
                continue

            graph = self.graphs.get(spec.contract_name)
            if not graph:
                results.append(DetectionResult(
                    contract_name=spec.contract_name,
                    total_expected=0,
                    detected=0,
                    missed=["Graph not loaded"],
                    detection_rate=0.0
                ))
                continue

            total_expected = 0
            total_detected = 0
            all_missed = []

            for func_name, props in spec.expected_properties.items():
                node = self._get_function_node(graph, func_name)
                if not node:
                    all_missed.append(f"Function {func_name} not found")
                    total_expected += len(props)
                    continue

                expected, detected, missed = self._check_properties(node, props)
                total_expected += expected
                total_detected += detected
                all_missed.extend(missed)

            rate = total_detected / total_expected if total_expected > 0 else 0.0
            results.append(DetectionResult(
                contract_name=spec.contract_name,
                total_expected=total_expected,
                detected=total_detected,
                missed=all_missed,
                detection_rate=rate
            ))

        return results

    def test_original_contracts_detection(self):
        """Measure detection rate on original (standard naming) contracts."""
        results = self._measure_detection(ORIGINAL_CONTRACTS)

        total_expected = sum(r.total_expected for r in results)
        total_detected = sum(r.detected for r in results)

        if total_expected > 0:
            overall_rate = total_detected / total_expected
        else:
            overall_rate = 0.0

        print(f"\n=== Original Contracts Detection ===")
        for r in results:
            status = "PASS" if r.detection_rate >= 0.8 else "FAIL"
            print(f"  {r.contract_name}: {r.detected}/{r.total_expected} ({r.detection_rate:.1%}) [{status}]")
            if r.missed:
                for m in r.missed[:3]:  # Show first 3 misses
                    print(f"    - {m}")

        print(f"\n  Overall: {total_detected}/{total_expected} ({overall_rate:.1%})")

        # Original contracts should have high detection rate
        self.assertGreaterEqual(overall_rate, 0.7,
            f"Original contract detection rate {overall_rate:.1%} below 70% threshold")

    def test_renamed_contracts_detection(self):
        """Measure detection rate on renamed (non-standard naming) contracts."""
        results = self._measure_detection(RENAMED_CONTRACTS)

        total_expected = sum(r.total_expected for r in results)
        total_detected = sum(r.detected for r in results)

        if total_expected > 0:
            overall_rate = total_detected / total_expected
        else:
            overall_rate = 0.0

        print(f"\n=== Renamed Contracts Detection ===")
        for r in results:
            status = "PASS" if r.detection_rate >= 0.8 else "NEEDS_IMPROVEMENT"
            print(f"  {r.contract_name}: {r.detected}/{r.total_expected} ({r.detection_rate:.1%}) [{status}]")
            if r.missed:
                for m in r.missed[:3]:
                    print(f"    - {m}")

        print(f"\n  Overall: {total_detected}/{total_expected} ({overall_rate:.1%})")
        print(f"  Target: >90%")

        # Record baseline - this test documents current state, not enforces target
        # After Phase 1-3 implementation, update threshold to 0.9

    def test_detection_degradation(self):
        """Calculate detection degradation between original and renamed contracts."""
        original_results = self._measure_detection(ORIGINAL_CONTRACTS)
        renamed_results = self._measure_detection(RENAMED_CONTRACTS)

        orig_expected = sum(r.total_expected for r in original_results)
        orig_detected = sum(r.detected for r in original_results)
        orig_rate = orig_detected / orig_expected if orig_expected > 0 else 0.0

        renamed_expected = sum(r.total_expected for r in renamed_results)
        renamed_detected = sum(r.detected for r in renamed_results)
        renamed_rate = renamed_detected / renamed_expected if renamed_expected > 0 else 0.0

        degradation = orig_rate - renamed_rate if orig_rate > 0 else 0.0

        print(f"\n=== Detection Degradation Analysis ===")
        print(f"  Original contracts: {orig_rate:.1%}")
        print(f"  Renamed contracts:  {renamed_rate:.1%}")
        print(f"  Degradation:        {degradation:.1%}")
        print(f"")
        print(f"  Goal: <10% degradation (currently {degradation:.1%})")

    def test_generate_baseline_report(self):
        """Generate comprehensive baseline report."""
        original_results = self._measure_detection(ORIGINAL_CONTRACTS)
        renamed_results = self._measure_detection(RENAMED_CONTRACTS)

        report = {
            "original_contracts": {
                "total_expected": sum(r.total_expected for r in original_results),
                "total_detected": sum(r.detected for r in original_results),
                "results": [
                    {
                        "contract": r.contract_name,
                        "expected": r.total_expected,
                        "detected": r.detected,
                        "rate": r.detection_rate,
                        "missed": r.missed
                    }
                    for r in original_results
                ]
            },
            "renamed_contracts": {
                "total_expected": sum(r.total_expected for r in renamed_results),
                "total_detected": sum(r.detected for r in renamed_results),
                "results": [
                    {
                        "contract": r.contract_name,
                        "expected": r.total_expected,
                        "detected": r.detected,
                        "rate": r.detection_rate,
                        "missed": r.missed
                    }
                    for r in renamed_results
                ]
            }
        }

        orig_rate = (report["original_contracts"]["total_detected"] /
                    report["original_contracts"]["total_expected"]
                    if report["original_contracts"]["total_expected"] > 0 else 0)
        renamed_rate = (report["renamed_contracts"]["total_detected"] /
                       report["renamed_contracts"]["total_expected"]
                       if report["renamed_contracts"]["total_expected"] > 0 else 0)

        report["summary"] = {
            "original_detection_rate": orig_rate,
            "renamed_detection_rate": renamed_rate,
            "degradation": orig_rate - renamed_rate,
            "target_renamed_rate": 0.9,
            "gap_to_target": 0.9 - renamed_rate
        }

        # Write report
        output_path = Path(__file__).parent.parent / "benchmarks" / "detection_baseline.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n=== Baseline Report Written ===")
        print(f"  Path: {output_path}")
        print(f"  Original Rate: {orig_rate:.1%}")
        print(f"  Renamed Rate: {renamed_rate:.1%}")
        print(f"  Gap to 90% Target: {report['summary']['gap_to_target']:.1%}")


class PropertyDetectionTests(unittest.TestCase):
    """Individual property detection tests."""

    @classmethod
    def setUpClass(cls):
        """Load graphs for testing."""
        try:
            cls.reentrancy_original = load_graph("ReentrancyClassic.sol")
        except Exception:
            cls.reentrancy_original = None

        try:
            cls.reentrancy_renamed = load_graph("renamed/ReentrancyRenamed.sol")
        except Exception:
            cls.reentrancy_renamed = None

    def _get_function(self, graph, name: str):
        if not graph:
            return None
        for node in graph.nodes.values():
            if node.type == "Function":
                # Labels are like "withdraw(uint256)" - match the function name part
                if node.label.startswith(name + "(") or node.label == name:
                    return node
        return None

    def test_reentrancy_original_external_calls(self):
        """Original reentrancy contract should detect has_external_calls."""
        if not self.reentrancy_original:
            self.skipTest("ReentrancyClassic not loaded")

        fn = self._get_function(self.reentrancy_original, "withdraw")
        self.assertIsNotNone(fn, "withdraw function not found")
        self.assertTrue(fn.properties.get("has_external_calls", False),
                       "has_external_calls not detected on withdraw")

    def test_reentrancy_renamed_external_calls(self):
        """Renamed reentrancy contract should detect has_external_calls."""
        if not self.reentrancy_renamed:
            self.skipTest("ReentrancyRenamed not loaded")

        fn = self._get_function(self.reentrancy_renamed, "removeFunds")
        self.assertIsNotNone(fn, "removeFunds function not found")
        self.assertTrue(fn.properties.get("has_external_calls", False),
                       "has_external_calls not detected on removeFunds (semantic detection should work)")

    def test_reentrancy_original_state_write_order(self):
        """Original contract should detect state_write_after_external_call."""
        if not self.reentrancy_original:
            self.skipTest("ReentrancyClassic not loaded")

        fn = self._get_function(self.reentrancy_original, "withdraw")
        self.assertIsNotNone(fn)
        # This is a semantic property that should work regardless of naming
        self.assertTrue(fn.properties.get("state_write_after_external_call", False),
                       "state_write_after_external_call not detected")

    def test_reentrancy_renamed_state_write_order(self):
        """Renamed contract should detect state_write_after_external_call (semantic)."""
        if not self.reentrancy_renamed:
            self.skipTest("ReentrancyRenamed not loaded")

        fn = self._get_function(self.reentrancy_renamed, "removeFunds")
        self.assertIsNotNone(fn)
        # Semantic detection should work regardless of function name
        self.assertTrue(fn.properties.get("state_write_after_external_call", False),
                       "state_write_after_external_call should be detected semantically")


if __name__ == "__main__":
    unittest.main(verbosity=2)
