"""Arithmetic + Logic/State lens coverage tests."""

from __future__ import annotations

import unittest
import pytest
from tests.graph_cache import load_graph
from tests.pattern_loader import load_all_patterns
from alphaswarm_sol.queries.patterns import PatternEngine

try:
    import slither  # type: ignore  # noqa: F401

    _HAS_SLITHER = True
except Exception:
    _HAS_SLITHER = False


class ArithmeticLensTests(unittest.TestCase):
    def setUp(self) -> None:
        self.patterns = list(load_all_patterns())
        self.engine = PatternEngine()

    def _labels_for(self, findings, pattern_id: str) -> set[str]:
        return {finding["node_label"] for finding in findings if finding["pattern_id"] == pattern_id}

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_arithmetic_patterns(self) -> None:
        graph = load_graph("ArithmeticLens.sol")
        pattern_ids = [
            "arith-001",
            "arith-002",
            "arith-003",
            "arith-004",
            "arith-005",
            "arith-006",
            "arith-007",
            "arith-008",
            "arith-009",
            "arith-010",
            "arith-012",
            "arith-013",
            "arith-014",
            "arith-015",
            "arith-016",
            "arith-017",
            "arith-018",
            "arith-019",
            "arith-020",
            "arith-021",
            "arith-022",
            "arith-023",
        ]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=400)

        self.assertIn("uncheckedAdd(uint256)", self._labels_for(findings, "arith-001"))
        self.assertIn("divisionBeforeMul(uint256,uint256)", self._labels_for(findings, "arith-002"))
        self.assertIn("narrowingCast(uint256)", self._labels_for(findings, "arith-003"))
        self.assertIn("divideBy(uint256,uint256)", self._labels_for(findings, "arith-004"))
        self.assertIn("deposit(uint256)", self._labels_for(findings, "arith-005"))
        self.assertIn("feeCalc(uint256,uint256)", self._labels_for(findings, "arith-006"))
        self.assertIn("decimalMismatch(uint256,uint8)", self._labels_for(findings, "arith-007"))
        self.assertIn("largeMul(uint256)", self._labels_for(findings, "arith-008"))
        self.assertIn("roundingExploit(uint256)", self._labels_for(findings, "arith-009"))
        self.assertIn("percentageCalc(uint256,uint256)", self._labels_for(findings, "arith-010"))
        self.assertIn("loopSmallCounter(uint8)", self._labels_for(findings, "arith-012"))
        self.assertIn("truncationInFees(uint256,uint256)", self._labels_for(findings, "arith-013"))
        self.assertIn("signedToUnsigned(int256)", self._labels_for(findings, "arith-014"))
        self.assertIn("addressToUint(address)", self._labels_for(findings, "arith-015"))
        self.assertIn("lossCalc(uint256,uint256)", self._labels_for(findings, "arith-016"))
        self.assertIn("priceAmount(uint256,uint256)", self._labels_for(findings, "arith-017"))
        self.assertIn("basisPoints(uint256,uint256)", self._labels_for(findings, "arith-018"))
        self.assertIn("ratioCalc(uint256,uint256)", self._labels_for(findings, "arith-019"))
        self.assertIn("accumulateFees(uint256[])", self._labels_for(findings, "arith-020"))
        self.assertIn("timeMath(uint256)", self._labels_for(findings, "arith-021"))
        self.assertIn("durationCalc(uint256)", self._labels_for(findings, "arith-022"))
        self.assertIn("decimalIssue(uint256,uint8)", self._labels_for(findings, "arith-023"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_pre_08_arithmetic(self) -> None:
        graph = load_graph("ArithmeticLensPre08.sol")
        findings = self.engine.run(graph, self.patterns, pattern_ids=["arith-011"], limit=50)
        self.assertIn("pre08Add(uint256,uint256)", self._labels_for(findings, "arith-011"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_arithmetic_safe(self) -> None:
        graph = load_graph("ArithmeticLensSafe.sol")
        pattern_ids = [
            "arith-001",
            "arith-002",
            "arith-003",
            "arith-004",
            "arith-005",
            "arith-006",
            "arith-007",
            "arith-008",
            "arith-009",
            "arith-010",
            "arith-012",
            "arith-013",
            "arith-014",
            "arith-015",
            "arith-016",
            "arith-017",
            "arith-018",
            "arith-019",
            "arith-020",
            "arith-021",
            "arith-022",
            "arith-023",
        ]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=400)
        self.assertNotIn("checkedAdd(uint256)", self._labels_for(findings, "arith-001"))
        self.assertNotIn("mulBeforeDiv(uint256,uint256)", self._labels_for(findings, "arith-002"))
        self.assertNotIn("narrowingCastSafe(uint256)", self._labels_for(findings, "arith-003"))
        self.assertNotIn("divideBySafe(uint256,uint256)", self._labels_for(findings, "arith-004"))
        self.assertNotIn("depositSafe(uint256)", self._labels_for(findings, "arith-005"))
        self.assertNotIn("feePrecisionSafe(uint256,uint256)", self._labels_for(findings, "arith-006"))
        self.assertNotIn("decimalMismatchSafe(uint256,uint8)", self._labels_for(findings, "arith-007"))
        self.assertNotIn("largeMulSafe(uint256)", self._labels_for(findings, "arith-008"))
        self.assertNotIn("roundingSafe(uint256)", self._labels_for(findings, "arith-009"))
        self.assertNotIn("percentageCalcSafe(uint256,uint256)", self._labels_for(findings, "arith-010"))
        self.assertNotIn("loopLargeCounter(uint256)", self._labels_for(findings, "arith-012"))
        self.assertNotIn("feeWithPrecision(uint256,uint256)", self._labels_for(findings, "arith-013"))
        self.assertNotIn("signedToUnsignedSafe(int256)", self._labels_for(findings, "arith-014"))
        self.assertNotIn("checkedAdd(uint256)", self._labels_for(findings, "arith-015"))
        self.assertNotIn("precisionLossSafe(uint256,uint256)", self._labels_for(findings, "arith-016"))
        self.assertNotIn("priceAmountSafe(uint256,uint256)", self._labels_for(findings, "arith-017"))
        self.assertNotIn("basisPointsSafe(uint256,uint256)", self._labels_for(findings, "arith-018"))
        self.assertNotIn("ratioSafe(uint256,uint256)", self._labels_for(findings, "arith-019"))
        self.assertNotIn("accumulateSafely(uint256[])", self._labels_for(findings, "arith-020"))
        self.assertNotIn("timeCheck(uint256)", self._labels_for(findings, "arith-021"))
        self.assertNotIn("durationCalcSafe(uint256)", self._labels_for(findings, "arith-022"))
        self.assertNotIn("decimalScalingSafe(uint256,uint8)", self._labels_for(findings, "arith-023"))


class LogicStateLensTests(unittest.TestCase):
    def setUp(self) -> None:
        self.patterns = list(load_all_patterns())
        self.engine = PatternEngine()

    def _labels_for(self, findings, pattern_id: str) -> set[str]:
        return {finding["node_label"] for finding in findings if finding["pattern_id"] == pattern_id}

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_logic_state_patterns(self) -> None:
        graph = load_graph("LogicStateLens.sol")
        pattern_ids = [f"logic-{i:03d}" for i in range(1, 27)]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=400)

        self.assertIn("setStateNoCheck(LogicStateLens.Status)", self._labels_for(findings, "logic-001"))
        self.assertIn("updateBalance(address,uint256)", self._labels_for(findings, "logic-002"))
        self.assertIn("withdraw(uint256)", self._labels_for(findings, "logic-003"))
        self.assertIn("doubleCount(address,uint256)", self._labels_for(findings, "logic-004"))
        self.assertIn("LogicStateLens", self._labels_for(findings, "logic-005"))
        self.assertIn("kill(address)", self._labels_for(findings, "logic-006"))
        self.assertIn("constructor()", self._labels_for(findings, "logic-007"))
        self.assertIn("LogicStateLens", self._labels_for(findings, "logic-008"))
        self.assertIn("updateValue(address,uint256)", self._labels_for(findings, "logic-009"))
        self.assertIn("finishState()", self._labels_for(findings, "logic-010"))
        self.assertIn("externalCallNoGuard(address)", self._labels_for(findings, "logic-011"))
        self.assertIn("updateCollateral(uint256)", self._labels_for(findings, "logic-012"))
        self.assertIn("updatePool(uint256)", self._labels_for(findings, "logic-013"))
        self.assertIn("unsafeTransfer(address,address,uint256)", self._labels_for(findings, "logic-014"))
        self.assertIn("updateAmount(uint256)", self._labels_for(findings, "logic-015"))
        self.assertIn("orderedExternalCall(address)", self._labels_for(findings, "logic-016"))
        self.assertIn("conditionalGate()", self._labels_for(findings, "logic-017"))
        self.assertIn("protocolCall(address)", self._labels_for(findings, "logic-018"))
        self.assertIn("transferEth(address)", self._labels_for(findings, "logic-019"))
        self.assertIn("roundingLoop(uint256,uint256)", self._labels_for(findings, "logic-020"))
        self.assertIn("updateState(uint256)", self._labels_for(findings, "logic-021"))
        self.assertIn("DiamondDerived", self._labels_for(findings, "logic-022"))
        self.assertIn("kill(address)", self._labels_for(findings, "logic-023"))
        self.assertIn("transferTo(address)", self._labels_for(findings, "logic-024"))
        self.assertIn("LogicStateLens", self._labels_for(findings, "logic-025"))
        self.assertIn("emitWrong(uint256)", self._labels_for(findings, "logic-026"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_logic_state_safe(self) -> None:
        graph = load_graph("LogicStateLensSafe.sol")
        pattern_ids = [f"logic-{i:03d}" for i in range(1, 27)]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=400)
        self.assertNotIn("setStateChecked(uint8)", self._labels_for(findings, "logic-001"))
        self.assertNotIn("updateBalanceSafe(address,uint256)", self._labels_for(findings, "logic-002"))
        self.assertNotIn("withdrawSafe(uint256)", self._labels_for(findings, "logic-003"))
        self.assertNotIn("singleCount(address,uint256)", self._labels_for(findings, "logic-004"))
        self.assertNotIn("LogicStateLensSafe", self._labels_for(findings, "logic-005"))
        self.assertNotIn("guardedExternalCall(address)", self._labels_for(findings, "logic-011"))
        self.assertNotIn("updateAmountSafe(uint256)", self._labels_for(findings, "logic-015"))
        self.assertNotIn("protocolCallSafe(address)", self._labels_for(findings, "logic-018"))
        self.assertNotIn("emitCorrect(uint256)", self._labels_for(findings, "logic-026"))


if __name__ == "__main__":
    unittest.main()
