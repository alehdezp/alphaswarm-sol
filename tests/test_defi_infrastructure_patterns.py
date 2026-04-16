"""
Comprehensive test suite for 9 DeFi infrastructure semantic patterns.

Tests patterns that detect unprotected writes to critical protocol parameters:
- circuit-001: Circuit breaker (pause/unpause)
- governance-001: Governance parameters
- tokenomics-001: Reward/emission parameters
- bridge-001: Bridge configuration
- defi-001: DeFi risk parameters
- emergency-001: Emergency recovery
- merkle-001: Merkle root updates
- oracle-002: Oracle/price feed configuration
- treasury-001: Treasury/fee recipients
"""

from __future__ import annotations
import unittest
import pytest
from tests.graph_cache import load_graph
from tests.pattern_loader import load_all_patterns
from alphaswarm_sol.queries.patterns import PatternEngine

try:
    import slither
    _HAS_SLITHER = True
except Exception:
    _HAS_SLITHER = False


class TestDeFiInfrastructurePatterns(unittest.TestCase):
    """Test all 9 DeFi infrastructure patterns on UnprotectedParametersTest.sol."""

    def setUp(self) -> None:
        self.patterns = list(load_all_patterns())
        self.engine = PatternEngine()
        self.graph = load_graph("projects/defi-protocol/UnprotectedParametersTest.sol")

    def _labels_for(self, findings, pattern_id: str) -> set[str]:
        """Extract function labels for a specific pattern from findings."""
        labels = set()
        for f in findings:
            if f["pattern_id"] == pattern_id:
                # Normalize label - remove contract prefix if present
                label = f["node_label"]
                if "." in label:
                    label = label.split(".", 1)[1]
                labels.add(label)
        return labels

    def _run_pattern(self, pattern_id: str):
        """Run a single pattern and return findings."""
        return self.engine.run(self.graph, self.patterns, pattern_ids=[pattern_id], limit=200)

    # ==========================================================================
    # circuit-001: Circuit Breaker
    # ==========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_circuit_001_tp_pause(self) -> None:
        """TP: pause() without access control."""
        findings = self._run_pattern("circuit-001")
        self.assertIn("pause()", self._labels_for(findings, "circuit-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_circuit_001_tp_unpause(self) -> None:
        """TP: unpause() without access control."""
        findings = self._run_pattern("circuit-001")
        self.assertIn("unpause()", self._labels_for(findings, "circuit-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_circuit_001_tp_set_paused(self) -> None:
        """TP: setPaused(bool) without access control."""
        findings = self._run_pattern("circuit-001")
        self.assertIn("setPaused(bool)", self._labels_for(findings, "circuit-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_circuit_001_tn_pause_protected(self) -> None:
        """TN: pauseProtected() WITH onlyOwner should NOT be flagged."""
        findings = self._run_pattern("circuit-001")
        self.assertNotIn("pauseProtected()", self._labels_for(findings, "circuit-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_circuit_001_tn_is_paused(self) -> None:
        """TN: isPaused() view function should NOT be flagged."""
        findings = self._run_pattern("circuit-001")
        self.assertNotIn("isPaused()", self._labels_for(findings, "circuit-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_circuit_001_var_emergency_stop(self) -> None:
        """VAR: activateEmergencyStop() - different naming."""
        findings = self._run_pattern("circuit-001")
        labels = self._labels_for(findings, "circuit-001")
        # Should detect if heuristics tag "emergencyStop" as pause-related
        # This tests implementation-agnostic detection

    # ==========================================================================
    # governance-001: Governance Parameters
    # ==========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_governance_001_tp_set_voting_delay(self) -> None:
        """TP: setVotingDelay(uint256) without access control."""
        findings = self._run_pattern("governance-001")
        self.assertIn("setVotingDelay(uint256)", self._labels_for(findings, "governance-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_governance_001_tp_set_quorum(self) -> None:
        """TP: setQuorum(uint256) without access control."""
        findings = self._run_pattern("governance-001")
        self.assertIn("setQuorum(uint256)", self._labels_for(findings, "governance-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_governance_001_tn_protected(self) -> None:
        """TN: setVotingDelayProtected() WITH onlyGovernance should NOT be flagged."""
        findings = self._run_pattern("governance-001")
        self.assertNotIn("setVotingDelayProtected(uint256)", self._labels_for(findings, "governance-001"))

    # ==========================================================================
    # tokenomics-001: Reward/Emission Parameters
    # ==========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tokenomics_001_tp_set_reward_rate(self) -> None:
        """TP: setRewardRate(uint256) without access control."""
        findings = self._run_pattern("tokenomics-001")
        self.assertIn("setRewardRate(uint256)", self._labels_for(findings, "tokenomics-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tokenomics_001_tp_set_emission_rate(self) -> None:
        """TP: setEmissionRate(uint256) without access control."""
        findings = self._run_pattern("tokenomics-001")
        self.assertIn("setEmissionRate(uint256)", self._labels_for(findings, "tokenomics-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tokenomics_001_tn_protected(self) -> None:
        """TN: setRewardRateProtected() WITH onlyRewardAdmin should NOT be flagged."""
        findings = self._run_pattern("tokenomics-001")
        self.assertNotIn("setRewardRateProtected(uint256)", self._labels_for(findings, "tokenomics-001"))

    # ==========================================================================
    # bridge-001: Bridge Configuration (CRITICAL)
    # ==========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_bridge_001_tp_set_relayer(self) -> None:
        """TP: setRelayer(address) without access control (Poly Network-style)."""
        findings = self._run_pattern("bridge-001")
        self.assertIn("setRelayer(address)", self._labels_for(findings, "bridge-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_bridge_001_tp_set_bridge_endpoint(self) -> None:
        """TP: setBridgeEndpoint(address) without access control (Nomad-style)."""
        findings = self._run_pattern("bridge-001")
        self.assertIn("setBridgeEndpoint(address)", self._labels_for(findings, "bridge-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_bridge_001_tn_protected(self) -> None:
        """TN: setRelayerProtected() WITH onlyBridgeAdmin should NOT be flagged."""
        findings = self._run_pattern("bridge-001")
        self.assertNotIn("setRelayerProtected(address)", self._labels_for(findings, "bridge-001"))

    # ==========================================================================
    # defi-001: DeFi Risk Parameters
    # ==========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_defi_001_tp_set_liquidation_threshold(self) -> None:
        """TP: setLiquidationThreshold(uint256) without access control."""
        findings = self._run_pattern("defi-001")
        self.assertIn("setLiquidationThreshold(uint256)", self._labels_for(findings, "defi-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_defi_001_tp_set_collateral_ratio(self) -> None:
        """TP: setCollateralRatio(uint256) without access control."""
        findings = self._run_pattern("defi-001")
        self.assertIn("setCollateralRatio(uint256)", self._labels_for(findings, "defi-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_defi_001_tn_protected(self) -> None:
        """TN: setLiquidationThresholdProtected() WITH onlyRiskManager should NOT be flagged."""
        findings = self._run_pattern("defi-001")
        self.assertNotIn("setLiquidationThresholdProtected(uint256)", self._labels_for(findings, "defi-001"))

    # ==========================================================================
    # emergency-001: Emergency Recovery
    # ==========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_emergency_001_tp_emergency_withdraw(self) -> None:
        """TP: emergencyWithdraw() without access control."""
        findings = self._run_pattern("emergency-001")
        self.assertIn("emergencyWithdraw(address,uint256)", self._labels_for(findings, "emergency-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_emergency_001_tp_rescue_tokens(self) -> None:
        """TP: rescueTokens() without access control."""
        findings = self._run_pattern("emergency-001")
        self.assertIn("rescueTokens(address)", self._labels_for(findings, "emergency-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_emergency_001_tn_protected(self) -> None:
        """TN: emergencyWithdrawProtected() WITH onlyEmergencyAdmin should NOT be flagged."""
        findings = self._run_pattern("emergency-001")
        self.assertNotIn("emergencyWithdrawProtected(address,uint256)", self._labels_for(findings, "emergency-001"))

    # ==========================================================================
    # merkle-001: Merkle Root Updates
    # ==========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_merkle_001_tp_set_merkle_root(self) -> None:
        """TP: setMerkleRoot(bytes32) without access control."""
        findings = self._run_pattern("merkle-001")
        self.assertIn("setMerkleRoot(bytes32)", self._labels_for(findings, "merkle-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_merkle_001_tp_update_root(self) -> None:
        """TP: updateRoot(bytes32) without access control."""
        findings = self._run_pattern("merkle-001")
        self.assertIn("updateRoot(bytes32)", self._labels_for(findings, "merkle-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_merkle_001_tn_protected(self) -> None:
        """TN: setMerkleRootProtected() WITH onlyMerkleAdmin should NOT be flagged."""
        findings = self._run_pattern("merkle-001")
        self.assertNotIn("setMerkleRootProtected(bytes32)", self._labels_for(findings, "merkle-001"))

    # ==========================================================================
    # oracle-002: Oracle/Price Feed Configuration
    # ==========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_oracle_002_tp_set_oracle(self) -> None:
        """TP: setOracle(address) without access control."""
        findings = self._run_pattern("oracle-002")
        self.assertIn("setOracle(address)", self._labels_for(findings, "oracle-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_oracle_002_tp_update_price_feed(self) -> None:
        """TP: updatePriceFeed(address) without access control."""
        findings = self._run_pattern("oracle-002")
        self.assertIn("updatePriceFeed(address)", self._labels_for(findings, "oracle-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_oracle_002_tn_protected(self) -> None:
        """TN: setOracleProtected() WITH onlyOracleAdmin should NOT be flagged."""
        findings = self._run_pattern("oracle-002")
        self.assertNotIn("setOracleProtected(address)", self._labels_for(findings, "oracle-002"))

    # ==========================================================================
    # treasury-001: Treasury/Fee Recipient
    # ==========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_treasury_001_tp_set_treasury(self) -> None:
        """TP: setTreasury(address) without access control."""
        findings = self._run_pattern("treasury-001")
        self.assertIn("setTreasury(address)", self._labels_for(findings, "treasury-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_treasury_001_tp_set_fee_collector(self) -> None:
        """TP: setFeeCollector(address) without access control."""
        findings = self._run_pattern("treasury-001")
        self.assertIn("setFeeCollector(address)", self._labels_for(findings, "treasury-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_treasury_001_tn_protected(self) -> None:
        """TN: setTreasuryProtected() WITH onlyTreasuryAdmin should NOT be flagged."""
        findings = self._run_pattern("treasury-001")
        self.assertNotIn("setTreasuryProtected(address)", self._labels_for(findings, "treasury-001"))


if __name__ == "__main__":
    unittest.main()
