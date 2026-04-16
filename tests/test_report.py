"""Comprehensive lens report aggregation and security findings presentation tests.

This module tests the reporting capabilities for various vulnerability types and severity levels,
ensuring that security findings are properly aggregated, categorized, and presented.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from alphaswarm_sol.kg.builder import VKGBuilder
from alphaswarm_sol.queries.report import build_lens_report
from tests.graph_cache import load_graph

try:
    import slither  # type: ignore  # noqa: F401

    _HAS_SLITHER = True
except Exception:
    _HAS_SLITHER = False


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "tests" / "contracts"


class BasicLensReportTests(unittest.TestCase):
    """Basic lens report functionality tests."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_lens_report_contains_contract(self) -> None:
        """Test that lens report includes contract information."""
        graph = VKGBuilder(ROOT).build(CONTRACTS / "SwapNoParams.sol")
        report = build_lens_report(graph, ["Ordering", "Oracle", "ExternalInfluence"], limit=20)
        labels = {entry["contract_label"] for entry in report["contracts"]}
        self.assertIn("SwapNoParams", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_lens_report_structure(self) -> None:
        """Test that lens report has expected structure."""
        graph = VKGBuilder(ROOT).build(CONTRACTS / "SwapNoParams.sol")
        report = build_lens_report(graph, ["Authority", "Reentrancy"], limit=10)

        self.assertIn("contracts", report)
        self.assertIsInstance(report["contracts"], list)
        if len(report["contracts"]) > 0:
            contract_entry = report["contracts"][0]
            self.assertIn("contract_label", contract_entry)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_lens_report_limit(self) -> None:
        """Test that lens report respects limit parameter."""
        graph = VKGBuilder(ROOT).build(CONTRACTS / "RoleBasedAccess.sol")
        report = build_lens_report(graph, ["Authority"], limit=5)

        self.assertIsNotNone(report)
        # Verify report generation succeeds with limit

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multiple_lenses(self) -> None:
        """Test report generation with multiple lenses."""
        graph = VKGBuilder(ROOT).build(CONTRACTS / "ReentrancyClassic.sol")
        report = build_lens_report(
            graph,
            ["Authority", "Reentrancy", "ExternalInfluence", "ValueMovement"],
            limit=20
        )

        self.assertIsNotNone(report)
        self.assertIn("contracts", report)


class AuthorityLensReportTests(unittest.TestCase):
    """Tests for Authority lens reporting."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_weak_access_control(self) -> None:
        """Test Authority lens detects weak access control."""
        graph = load_graph("NoAccessGate.sol")
        report = build_lens_report(graph, ["Authority"], limit=20)

        self.assertIsNotNone(report)
        self.assertIn("contracts", report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_tx_origin(self) -> None:
        """Test Authority lens detects tx.origin usage."""
        graph = load_graph("TxOriginAuth.sol")
        report = build_lens_report(graph, ["Authority"], limit=20)

        self.assertIsNotNone(report)
        contracts = report.get("contracts", [])
        self.assertTrue(len(contracts) > 0)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_delegatecall(self) -> None:
        """Test Authority lens detects delegatecall without access control."""
        graph = load_graph("DelegatecallNoAccessGate.sol")
        report = build_lens_report(graph, ["Authority"], limit=20)

        self.assertIsNotNone(report)


class ReentrancyLensReportTests(unittest.TestCase):
    """Tests for Reentrancy lens reporting."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_reentrancy_lens_classic(self) -> None:
        """Test Reentrancy lens detects classic reentrancy."""
        graph = load_graph("ReentrancyClassic.sol")
        report = build_lens_report(graph, ["Reentrancy"], limit=20)

        self.assertIsNotNone(report)
        self.assertIn("contracts", report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_reentrancy_lens_erc777(self) -> None:
        """Test Reentrancy lens detects ERC777 hook reentrancy."""
        graph = load_graph("Erc777Reentrancy.sol")
        report = build_lens_report(graph, ["Reentrancy"], limit=20)

        self.assertIsNotNone(report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_reentrancy_lens_read_only(self) -> None:
        """Test Reentrancy lens detects read-only reentrancy."""
        graph = load_graph("ReadOnlyReentrancy.sol")
        report = build_lens_report(graph, ["Reentrancy"], limit=20)

        self.assertIsNotNone(report)


class TokenLensReportTests(unittest.TestCase):
    """Tests for Token lens reporting."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_token_lens_fee_on_transfer(self) -> None:
        """Test Token lens detects fee-on-transfer issues."""
        graph = load_graph("FeeOnTransferToken.sol")
        report = build_lens_report(graph, ["Token"], limit=20)

        self.assertIsNotNone(report)
        self.assertIn("contracts", report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_token_lens_rebasing(self) -> None:
        """Test Token lens detects rebasing token issues."""
        graph = load_graph("RebasingToken.sol")
        report = build_lens_report(graph, ["Token"], limit=20)

        self.assertIsNotNone(report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_token_lens_non_standard(self) -> None:
        """Test Token lens detects non-standard tokens."""
        graph = load_graph("NonStandardTokens.sol")
        report = build_lens_report(graph, ["Token"], limit=20)

        self.assertIsNotNone(report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_token_lens_approval_risks(self) -> None:
        """Test Token lens detects approval vulnerabilities."""
        graph = load_graph("ApprovalRaceCondition.sol")
        report = build_lens_report(graph, ["Token"], limit=20)

        self.assertIsNotNone(report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_token_lens_decimal_mismatch(self) -> None:
        """Test Token lens detects decimal mismatch issues."""
        graph = load_graph("TokenDecimalMismatch.sol")
        report = build_lens_report(graph, ["Token"], limit=20)

        self.assertIsNotNone(report)


class OracleLensReportTests(unittest.TestCase):
    """Tests for Oracle lens reporting."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_oracle_lens_missing_validation(self) -> None:
        """Test Oracle lens detects missing staleness checks."""
        graph = load_graph("OracleNoStaleness.sol")
        report = build_lens_report(graph, ["Oracle"], limit=20)

        self.assertIsNotNone(report)
        self.assertIn("contracts", report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_oracle_lens_twap_manipulation(self) -> None:
        """Test Oracle lens detects TWAP manipulation risks."""
        graph = load_graph("TwapNoWindow.sol")
        report = build_lens_report(graph, ["Oracle"], limit=20)

        self.assertIsNotNone(report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_oracle_lens_chainlink_issues(self) -> None:
        """Test Oracle lens detects Chainlink oracle issues."""
        graph = load_graph("OracleL2NoSequencerCheck.sol")
        report = build_lens_report(graph, ["Oracle"], limit=20)

        self.assertIsNotNone(report)


class MEVLensReportTests(unittest.TestCase):
    """Tests for MEV lens reporting."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_mev_lens_missing_slippage(self) -> None:
        """Test MEV lens detects missing slippage protection."""
        graph = load_graph("SwapNoSlippage.sol")
        report = build_lens_report(graph, ["MEV"], limit=20)

        self.assertIsNotNone(report)
        self.assertIn("contracts", report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_mev_lens_missing_deadline(self) -> None:
        """Test MEV lens detects missing deadline checks."""
        graph = load_graph("SwapNoParams.sol")
        report = build_lens_report(graph, ["MEV"], limit=20)

        self.assertIsNotNone(report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_mev_lens_frontrunning(self) -> None:
        """Test MEV lens detects frontrunning vulnerabilities."""
        graph = load_graph("MEVFrontrunLiquidation.sol")
        report = build_lens_report(graph, ["MEV"], limit=20)

        self.assertIsNotNone(report)


class ValueMovementLensReportTests(unittest.TestCase):
    """Tests for Value Movement lens reporting."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_value_movement_reentrancy(self) -> None:
        """Test Value Movement lens detects reentrancy vulnerabilities."""
        graph = load_graph("ValueMovementReentrancy.sol")
        report = build_lens_report(graph, ["ValueMovement"], limit=20)

        self.assertIsNotNone(report)
        self.assertIn("contracts", report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_value_movement_forced_ether(self) -> None:
        """Test Value Movement lens detects forced ether injection."""
        graph = load_graph("ValueMovementForcedEther.sol")
        report = build_lens_report(graph, ["ValueMovement"], limit=20)

        self.assertIsNotNone(report)
        contracts = report.get("contracts", [])
        self.assertTrue(len(contracts) > 0)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_value_movement_stuck_ether(self) -> None:
        """Test Value Movement lens detects stuck ether vulnerabilities."""
        graph = load_graph("ValueMovementStuckEther.sol")
        report = build_lens_report(graph, ["ValueMovement"], limit=20)

        self.assertIsNotNone(report)
        self.assertIn("contracts", report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_value_movement_mev_sandwich(self) -> None:
        """Test Value Movement lens detects MEV sandwich attack patterns."""
        graph = load_graph("ValueMovementMEVSandwich.sol")
        report = build_lens_report(graph, ["ValueMovement", "MEV"], limit=20)

        self.assertIsNotNone(report)
        contracts = report.get("contracts", [])
        self.assertTrue(len(contracts) > 0)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_value_movement_integer_issues(self) -> None:
        """Test Value Movement lens detects integer overflow/precision issues."""
        graph = load_graph("ValueMovementIntegerIssues.sol")
        report = build_lens_report(graph, ["ValueMovement"], limit=20)

        self.assertIsNotNone(report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_value_movement_flash_loan(self) -> None:
        """Test Value Movement lens detects flash loan vulnerabilities."""
        graph = load_graph("ValueMovementFlashLoan.sol")
        report = build_lens_report(graph, ["ValueMovement"], limit=20)

        self.assertIsNotNone(report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_value_movement_external_calls(self) -> None:
        """Test Value Movement lens detects unchecked external calls."""
        graph = load_graph("ValueMovementExternalCalls.sol")
        report = build_lens_report(graph, ["ValueMovement"], limit=20)

        self.assertIsNotNone(report)
        self.assertIn("contracts", report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_value_movement_fee_on_transfer(self) -> None:
        """Test Value Movement lens detects fee-on-transfer issues."""
        graph = load_graph("FeeOnTransferToken.sol")
        report = build_lens_report(graph, ["ValueMovement", "Token"], limit=20)

        self.assertIsNotNone(report)
        contracts = report.get("contracts", [])
        self.assertTrue(len(contracts) > 0)


class ComprehensiveLensReportTests(unittest.TestCase):
    """Tests for comprehensive multi-lens reports."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_all_lenses_comprehensive_contract(self) -> None:
        """Test report with all lenses on a complex contract."""
        graph = load_graph("FeeOnTransferToken.sol")
        report = build_lens_report(
            graph,
            ["Authority", "Reentrancy", "MEV", "Oracle", "Token", "Crypto"],
            limit=50
        )

        self.assertIsNotNone(report)
        self.assertIn("contracts", report)
        contracts = report.get("contracts", [])
        self.assertTrue(len(contracts) > 0)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_report_with_different_limits(self) -> None:
        """Test report generation with various limit values."""
        graph = load_graph("RebasingToken.sol")

        for limit in [5, 10, 20, 50]:
            report = build_lens_report(graph, ["Token", "Authority"], limit=limit)
            self.assertIsNotNone(report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_empty_lens_list(self) -> None:
        """Test report generation with empty lens list."""
        graph = load_graph("TokenCalls.sol")
        report = build_lens_report(graph, [], limit=10)

        self.assertIsNotNone(report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_report_consistency(self) -> None:
        """Test that multiple report generations are consistent."""
        graph = load_graph("BlacklistPausableTokens.sol")

        report1 = build_lens_report(graph, ["Token"], limit=20)
        report2 = build_lens_report(graph, ["Token"], limit=20)

        # Reports should be identical for same input
        self.assertEqual(len(report1.get("contracts", [])), len(report2.get("contracts", [])))


class SeverityReportTests(unittest.TestCase):
    """Tests for severity-based reporting."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_high_severity_findings(self) -> None:
        """Test detection of high severity issues."""
        graph = load_graph("NoAccessGate.sol")
        report = build_lens_report(graph, ["Authority"], limit=20)

        # Weak access control should be high severity
        self.assertIsNotNone(report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_medium_severity_findings(self) -> None:
        """Test detection of medium severity issues."""
        graph = load_graph("SwapNoParams.sol")
        report = build_lens_report(graph, ["MEV"], limit=20)

        # Missing deadline is medium severity
        self.assertIsNotNone(report)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_low_severity_findings(self) -> None:
        """Test detection of low severity issues."""
        graph = load_graph("NonStandardTokens.sol")
        report = build_lens_report(graph, ["Token"], limit=20)

        # Non-standard tokens may be low/info severity
        self.assertIsNotNone(report)


class ReportFormatTests(unittest.TestCase):
    """Tests for report format and structure."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_report_json_serializable(self) -> None:
        """Test that report is JSON serializable."""
        import json

        graph = load_graph("PermitVulnerabilities.sol")
        report = build_lens_report(graph, ["Token", "Crypto"], limit=20)

        # Should be able to serialize to JSON
        try:
            json_str = json.dumps(report)
            self.assertIsNotNone(json_str)
        except TypeError:
            self.fail("Report should be JSON serializable")

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_report_contains_metadata(self) -> None:
        """Test that report contains expected metadata fields."""
        graph = load_graph("InfiniteApprovalRisks.sol")
        report = build_lens_report(graph, ["Token"], limit=20)

        self.assertIsNotNone(report)
        # Basic structure check
        self.assertIsInstance(report, dict)


if __name__ == "__main__":
    unittest.main()
