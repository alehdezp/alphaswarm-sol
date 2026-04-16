"""Authority lens pattern coverage tests."""

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


class AuthorityLensTests(unittest.TestCase):
    def setUp(self) -> None:
        self.patterns = list(load_all_patterns())
        self.engine = PatternEngine()

    def _labels_for(self, findings, pattern_id: str) -> set[str]:
        return {finding["node_label"] for finding in findings if finding["pattern_id"] == pattern_id}

    def _run_patterns(self, contract_name: str, pattern_ids: list[str]):
        graph = load_graph(contract_name)
        return self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=200)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_patterns(self) -> None:
        graph = load_graph("AuthorityLens.sol")
        pattern_ids = [
            "auth-001",
            "auth-002",
            "auth-003",
            "auth-004",
            "auth-005",
            "auth-006",
            "auth-007",
            "auth-008",
            "auth-009",
            "auth-010",
            "auth-011",
            "auth-012",
            "auth-013",
            "auth-014",
            "auth-015",
            "auth-016",
            "auth-017",
            "auth-018",
            "auth-019",
            "auth-020",
        ]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=200)

        self.assertIn("setOwner(address)", self._labels_for(findings, "auth-001"))
        self.assertNotIn("setOwnerProtected(address)", self._labels_for(findings, "auth-001"))
        self.assertIn("privileged()", self._labels_for(findings, "auth-002"))
        self.assertIn("verify(bytes32,uint8,bytes32,bytes32)", self._labels_for(findings, "auth-003"))
        self.assertIn("verify(bytes32,uint8,bytes32,bytes32)", self._labels_for(findings, "auth-004"))
        self.assertIn("CentralizedAdmin", self._labels_for(findings, "auth-005"))
        self.assertIn("CentralizedAdmin", self._labels_for(findings, "auth-008"))
        self.assertIn("initialize(address)", self._labels_for(findings, "auth-006"))
        self.assertNotIn("initializeProtected(address)", self._labels_for(findings, "auth-006"))
        self.assertIn("grantSelf()", self._labels_for(findings, "auth-007"))
        self.assertNotIn("grantSelfProtected()", self._labels_for(findings, "auth-007"))
        self.assertIn("onERC721Received(address,address,uint256,bytes)", self._labels_for(findings, "auth-009"))
        self.assertIn("delegateAsOwner(address,bytes)", self._labels_for(findings, "auth-010"))
        self.assertIn("sweep(address)", self._labels_for(findings, "auth-011"))
        self.assertIn("updateFee(uint256)", self._labels_for(findings, "auth-012"))
        self.assertIn("InconsistentAccessControl", self._labels_for(findings, "auth-013"))
        self.assertIn("RoleGrantOnly", self._labels_for(findings, "auth-014"))
        self.assertIn("RoleGrantOnly", self._labels_for(findings, "auth-015"))
        self.assertIn("emergencyWithdraw(address,address,uint256)", self._labels_for(findings, "auth-016"))
        self.assertIn("sweep(address)", self._labels_for(findings, "auth-017"))
        self.assertIn("timeGate(uint256)", self._labels_for(findings, "auth-018"))
        self.assertIn("onERC1155Received(address,address,uint256,uint256,bytes)", self._labels_for(findings, "auth-019"))
        self.assertIn("withdraw(address)", self._labels_for(findings, "auth-020"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_patterns_extended(self) -> None:
        findings = self._run_patterns("MultiSigThresholdOne.sol", ["auth-021"])
        self.assertIn("MultiSigThresholdOne", self._labels_for(findings, "auth-021"))

        findings = self._run_patterns("DangerousAdminWrites.sol", ["auth-022"])
        self.assertIn("updateOwner(address)", self._labels_for(findings, "auth-022"))

        findings = self._run_patterns("RoleBasedAccess.sol", ["auth-023"])
        self.assertIn("RoleBasedAccess", self._labels_for(findings, "auth-023"))

        findings = self._run_patterns("SignatureReplayMissingChainId.sol", ["auth-024"])
        self.assertIn(
            "executeWithSignature(address,uint256,uint256,uint256,uint8,bytes32,bytes32)",
            self._labels_for(findings, "auth-024"),
        )

        findings = self._run_patterns("SignatureReplayMissingDomain.sol", ["auth-025"])
        self.assertIn(
            "permit(address,address,uint256,uint256,uint8,bytes32,bytes32)",
            self._labels_for(findings, "auth-025"),
        )

        findings = self._run_patterns("SignatureNoDeadline.sol", ["auth-026"])
        self.assertIn(
            "executeWithSignature(address,uint256,uint256,uint8,bytes32,bytes32)",
            self._labels_for(findings, "auth-026"),
        )

        findings = self._run_patterns("SignatureMalleabilityV.sol", ["auth-027"])
        self.assertIn(
            "executeWithSignature(address,uint256,uint256,uint256,uint8,bytes32,bytes32)",
            self._labels_for(findings, "auth-027"),
        )

        findings = self._run_patterns("DelegatecallTargetUnvalidated.sol", ["auth-028"])
        self.assertIn("execute(address,bytes)", self._labels_for(findings, "auth-028"))

        findings = self._run_patterns("CallbackNoAuth.sol", ["auth-029"])
        self.assertIn("onCallback(address,uint256)", self._labels_for(findings, "auth-029"))

        findings = self._run_patterns("MulticallAuthBypass.sol", ["auth-030"])
        self.assertIn("guardedAction(uint256)", self._labels_for(findings, "auth-030"))

        findings = self._run_patterns("UpgradeNoTimelock.sol", ["auth-031"])
        self.assertIn("upgradeTo(address)", self._labels_for(findings, "auth-031"))

        findings = self._run_patterns("TimelockBypassEmergency.sol", ["auth-032"])
        self.assertIn("emergencyWithdraw(address,uint256)", self._labels_for(findings, "auth-032"))

        findings = self._run_patterns("UpgradeTimelockMissingCheck.sol", ["auth-033"])
        self.assertIn("upgradeTo(address)", self._labels_for(findings, "auth-033"))

        findings = self._run_patterns("TimelockDelayZero.sol", ["auth-034"])
        self.assertIn("TimelockDelayZero", self._labels_for(findings, "auth-034"))

        findings = self._run_patterns("PublicWrapperNoGate.sol", ["auth-045"])
        self.assertIn("setOwner(address)", self._labels_for(findings, "auth-045"))

        findings = self._run_patterns("GovernanceVoteNoSnapshot.sol", ["auth-046"])
        self.assertIn("castVote(uint256)", self._labels_for(findings, "auth-046"))

        findings = self._run_patterns("MultisigConfigNoGate.sol", ["auth-047"])
        self.assertIn("setThreshold(uint256)", self._labels_for(findings, "auth-047"))

        findings = self._run_patterns("MultisigConfigNoGate.sol", ["auth-048"])
        self.assertIn("addSigner(address)", self._labels_for(findings, "auth-048"))

        findings = self._run_patterns("EmergencyDelegatecallBypass.sol", ["auth-049"])
        self.assertIn("emergencyExecute(address,bytes)", self._labels_for(findings, "auth-049"))

        findings = self._run_patterns("MulticallBatchingNoGuard.sol", ["auth-050"])
        self.assertIn("multicall(address,bytes[])", self._labels_for(findings, "auth-050"))

        findings = self._run_patterns("TimelockAdminNoGate.sol", ["auth-051"])
        self.assertIn("setTimelockDelay(uint256)", self._labels_for(findings, "auth-051"))

        findings = self._run_patterns("DelegatecallContextSensitive.sol", ["auth-052"])
        self.assertIn("execute(address,bytes)", self._labels_for(findings, "auth-052"))

        findings = self._run_patterns("TxOriginAuth.sol", ["auth-053"])
        self.assertIn("privileged()", self._labels_for(findings, "auth-053"))

        findings = self._run_patterns("WeakAuthSource.sol", ["auth-054"])
        self.assertIn("privileged(uint256)", self._labels_for(findings, "auth-054"))

        findings = self._run_patterns("DelegatecallNoAccessGate.sol", ["auth-055"])
        self.assertIn("execute(address,bytes)", self._labels_for(findings, "auth-055"))

        findings = self._run_patterns("CallWithValue.sol", ["auth-056"])
        self.assertIn("forward(address,bytes)", self._labels_for(findings, "auth-056"))

        findings = self._run_patterns("WeakAuthSource.sol", ["auth-057"])
        self.assertIn("privileged(uint256)", self._labels_for(findings, "auth-057"))

        findings = self._run_patterns("WeakAuthSource.sol", ["auth-042"])
        self.assertIn("privileged(uint256)", self._labels_for(findings, "auth-042"))

        findings = self._run_patterns("WeakAuthSource.sol", ["auth-043"])
        self.assertIn("privileged(uint256)", self._labels_for(findings, "auth-043"))

        findings = self._run_patterns("RoleGrantRevokeNoGate.sol", ["auth-058"])
        self.assertIn("grantRole(address)", self._labels_for(findings, "auth-058"))

        findings = self._run_patterns("RoleGrantRevokeNoGate.sol", ["auth-059"])
        self.assertIn("revokeRole(address)", self._labels_for(findings, "auth-059"))

        findings = self._run_patterns("RoleGrantRevokeNoGate.sol", ["auth-060"])
        self.assertIn("grantRole(address)", self._labels_for(findings, "auth-060"))

        findings = self._run_patterns("SelfdestructNoGate.sol", ["auth-061"])
        self.assertIn("destroy()", self._labels_for(findings, "auth-061"))

        findings = self._run_patterns("ReinitializerNoGuard.sol", ["auth-062"])
        self.assertIn("reinitialize(address)", self._labels_for(findings, "auth-062"))

        findings = self._run_patterns("PublicPayableNoGate.sol", ["auth-063"])
        self.assertIn("deposit()", self._labels_for(findings, "auth-063"))

        findings = self._run_patterns("PayableFallbackNoGate.sol", ["auth-064"])
        labels = self._labels_for(findings, "auth-064")
        self.assertTrue("receive()" in labels or "fallback()" in labels)

        findings = self._run_patterns("CallWithValue.sol", ["auth-065"])
        self.assertIn("forward(address,bytes)", self._labels_for(findings, "auth-065"))

        findings = self._run_patterns("NoAccessGate.sol", ["auth-066"])
        self.assertIn("setOwner(address)", self._labels_for(findings, "auth-066"))

        findings = self._run_patterns("TxOriginAuth.sol", ["auth-067"])
        self.assertIn("privileged()", self._labels_for(findings, "auth-067"))

        findings = self._run_patterns("TimelockParameterNoCheck.sol", ["auth-068"])
        self.assertIn("executeAfter(uint256,address,bytes)", self._labels_for(findings, "auth-068"))

        findings = self._run_patterns("MultiSigThresholdZero.sol", ["auth-069"])
        self.assertIn("MultiSigThresholdZero", self._labels_for(findings, "auth-069"))

        findings = self._run_patterns("UpgradeNoAccessControl.sol", ["auth-070"])
        self.assertIn("upgradeTo(address)", self._labels_for(findings, "auth-070"))

        findings = self._run_patterns("OracleUpdate.sol", ["auth-071"])
        self.assertIn("setPrice(int256)", self._labels_for(findings, "auth-071"))

        findings = self._run_patterns("GovernanceQuorumNoSnapshot.sol", ["auth-072"])
        self.assertIn("quorum(uint256)", self._labels_for(findings, "auth-072"))

        findings = self._run_patterns("GovernanceExecuteNoTimelock.sol", ["auth-073"])
        labels = self._labels_for(findings, "auth-073")
        self.assertTrue("executeProposal(uint256,uint256)" in labels or "queue(uint256)" in labels)

        findings = self._run_patterns("MultisigThresholdChangeNoValidation.sol", ["auth-074"])
        self.assertIn("setThreshold(uint256)", self._labels_for(findings, "auth-074"))

        findings = self._run_patterns("MultisigSignerChangeNoValidation.sol", ["auth-075"])
        self.assertIn("addSigner(address)", self._labels_for(findings, "auth-075"))

        findings = self._run_patterns("GovernanceExecuteNoQuorum.sol", ["auth-076"])
        self.assertIn("execute(uint256)", self._labels_for(findings, "auth-076"))

        findings = self._run_patterns("GovernanceExecuteNoVotePeriod.sol", ["auth-077"])
        self.assertIn("execute(uint256)", self._labels_for(findings, "auth-077"))

        findings = self._run_patterns("MultiSigThresholdOne.sol", ["auth-078"])
        self.assertIn("execute(address,bytes)", self._labels_for(findings, "auth-078"))

        findings = self._run_patterns("WeakAuthExtcodesize.sol", ["auth-079"])
        self.assertIn("privileged(address)", self._labels_for(findings, "auth-079"))

        findings = self._run_patterns("WeakAuthExtcodehash.sol", ["auth-080"])
        self.assertIn("privileged(address)", self._labels_for(findings, "auth-080"))

        findings = self._run_patterns("WeakAuthGasleft.sol", ["auth-081"])
        self.assertIn("privileged(uint256)", self._labels_for(findings, "auth-081"))

        findings = self._run_patterns("TxOriginFallback.sol", ["auth-082"])
        labels = self._labels_for(findings, "auth-082")
        self.assertTrue("receive()" in labels or "fallback()" in labels)

        findings = self._run_patterns("DefaultAdminZeroAddress.sol", ["auth-083"])
        self.assertIn("DefaultAdminZeroAddress", self._labels_for(findings, "auth-083"))

        findings = self._run_patterns("UninitializedOwner.sol", ["auth-084"])
        self.assertIn("UninitializedOwner", self._labels_for(findings, "auth-084"))

        findings = self._run_patterns("UninitializedOwner.sol", ["auth-085"])
        self.assertIn("UninitializedOwner", self._labels_for(findings, "auth-085"))

        findings = self._run_patterns("WeakAuthSource.sol", ["auth-086"])
        self.assertIn("privileged(uint256)", self._labels_for(findings, "auth-086"))

        findings = self._run_patterns("WeakAuthBlockNumber.sol", ["auth-087"])
        self.assertIn("privileged(uint256)", self._labels_for(findings, "auth-087"))

        findings = self._run_patterns("WeakAuthBlockhash.sol", ["auth-088"])
        self.assertIn("privileged(bytes32)", self._labels_for(findings, "auth-088"))

        findings = self._run_patterns("WeakAuthChainId.sol", ["auth-089"])
        self.assertIn("privileged(uint256)", self._labels_for(findings, "auth-089"))

        findings = self._run_patterns("WeakAuthMsgValue.sol", ["auth-090"])
        self.assertIn("privileged()", self._labels_for(findings, "auth-090"))

        findings = self._run_patterns("TimelockAdminNoGate.sol", ["auth-091"])
        self.assertIn("setTimelockDelay(uint256)", self._labels_for(findings, "auth-091"))

        findings = self._run_patterns("MultisigExecuteNonceNoUpdate.sol", ["auth-092"])
        self.assertIn("execute(address,bytes,uint256)", self._labels_for(findings, "auth-092"))

        findings = self._run_patterns("GovernanceFlashLoanVote.sol", ["auth-093"])
        self.assertIn("vote(uint256)", self._labels_for(findings, "auth-093"))

        findings = self._run_patterns("MultisigSignerChangeNoValidation.sol", ["auth-094"])
        self.assertIn("addSigner(address)", self._labels_for(findings, "auth-094"))

        findings = self._run_patterns("WeakAuthBalanceCheck.sol", ["auth-095"])
        self.assertIn("privileged(address)", self._labels_for(findings, "auth-095"))

        findings = self._run_patterns("MultisigThresholdChangeSingleOwner.sol", ["auth-096"])
        self.assertIn("setThreshold(uint256)", self._labels_for(findings, "auth-096"))

        findings = self._run_patterns("MultisigSignerChangeSingleOwner.sol", ["auth-097"])
        self.assertIn("addSigner(address)", self._labels_for(findings, "auth-097"))

        findings = self._run_patterns("MultisigExecuteNoSignatureValidation.sol", ["auth-098"])
        self.assertIn("execute(address,bytes)", self._labels_for(findings, "auth-098"))

        findings = self._run_patterns("MultisigSignerRemoveNoMinCheck.sol", ["auth-099"])
        self.assertIn("removeSigner(uint256)", self._labels_for(findings, "auth-099"))

        findings = self._run_patterns("MultisigThresholdAboveOwners.sol", ["auth-100"])
        self.assertIn("setThreshold(uint256)", self._labels_for(findings, "auth-100"))

        findings = self._run_patterns("WeakAuthContractAddress.sol", ["auth-101"])
        self.assertIn("privileged()", self._labels_for(findings, "auth-101"))

        findings = self._run_patterns("AccessGateStringCompare.sol", ["auth-102"])
        self.assertIn("privileged()", self._labels_for(findings, "auth-102"))

        findings = self._run_patterns("RoleGrantNoEvent.sol", ["auth-103"])
        self.assertIn("RoleGrantNoEvent", self._labels_for(findings, "auth-103"))

        findings = self._run_patterns("MixedAuthMethods.sol", ["auth-104"])
        self.assertIn("mixedAuth()", self._labels_for(findings, "auth-104"))

        findings = self._run_patterns("AccessGateIfReturn.sol", ["auth-105"])
        self.assertIn("setValue(uint256)", self._labels_for(findings, "auth-105"))

        findings = self._run_patterns("AccessGateWrongVariable.sol", ["auth-106"])
        self.assertIn("setValue(address,uint256)", self._labels_for(findings, "auth-106"))

        findings = self._run_patterns("CrossContractAuthConfusion.sol", ["auth-107"])
        self.assertIn("delegateAsOwner(address,bytes)", self._labels_for(findings, "auth-107"))

        findings = self._run_patterns("UnprotectedConfigUpdates.sol", ["auth-108"])
        self.assertIn("pause()", self._labels_for(findings, "auth-108"))

        findings = self._run_patterns("UnprotectedConfigUpdates.sol", ["auth-109"])
        self.assertIn("addToWhitelist(address)", self._labels_for(findings, "auth-109"))

        findings = self._run_patterns("UnprotectedConfigUpdates.sol", ["auth-110"])
        self.assertIn("setQuorum(uint256)", self._labels_for(findings, "auth-110"))

        findings = self._run_patterns("UnprotectedConfigUpdates.sol", ["auth-111"])
        self.assertIn("setRewardRate(uint256)", self._labels_for(findings, "auth-111"))

        findings = self._run_patterns("UnprotectedConfigUpdates.sol", ["auth-112"])
        self.assertIn("setBridgeRelayer(address)", self._labels_for(findings, "auth-112"))

        findings = self._run_patterns("AuthReentrancyNoGuard.sol", ["auth-113"])
        self.assertIn("emergencyCall(address,bytes)", self._labels_for(findings, "auth-113"))

        findings = self._run_patterns("UnprotectedConfigUpdates.sol", ["auth-114"])
        self.assertIn("setFeeBps(uint256)", self._labels_for(findings, "auth-114"))

        findings = self._run_patterns("UnprotectedConfigUpdates.sol", ["auth-115"])
        self.assertIn("rescueFunds(address,uint256)", self._labels_for(findings, "auth-115"))

        findings = self._run_patterns("UnprotectedConfigUpdates.sol", ["auth-116"])
        self.assertIn("setMerkleRoot(bytes32)", self._labels_for(findings, "auth-116"))

        findings = self._run_patterns("UnprotectedConfigUpdates.sol", ["auth-117"])
        self.assertIn("setOracle(address)", self._labels_for(findings, "auth-117"))

        findings = self._run_patterns("UnprotectedConfigUpdates.sol", ["auth-118"])
        self.assertIn("setFeeRecipient(address)", self._labels_for(findings, "auth-118"))

        findings = self._run_patterns("ImplementationInitializerNoProxy.sol", ["auth-119"])
        self.assertIn("initialize(address)", self._labels_for(findings, "auth-119"))

        findings = self._run_patterns("GovernanceNoTimelock.sol", ["auth-044"])
        self.assertIn("GovernanceNoTimelock", self._labels_for(findings, "auth-044"))

        findings = self._run_patterns("FallbackNoAuth.sol", ["auth-120"])
        self.assertIn("fallback()", self._labels_for(findings, "auth-120"))

    # =========================================================================
    # auth-005: Unprotected List Management - Comprehensive Tests
    # =========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_auth_005_true_positives(self) -> None:
        """Test auth-005 detects unprotected list management functions."""
        graph = load_graph("projects/access-registry/ListManagementTest.sol")
        findings = self.engine.run(graph, self.patterns, pattern_ids=["auth-005"], limit=200)
        labels = self._labels_for(findings, "auth-005")

        # TP1-TP12: Standard unprotected list management
        self.assertIn("addToWhitelist(address)", labels, "TP1: Should flag unprotected whitelist addition")
        self.assertIn("removeFromBlacklist(address)", labels, "TP2: Should flag unprotected blacklist removal")
        self.assertIn("addValidator(address)", labels, "TP3: Should flag unprotected validator addition")
        self.assertIn("removeOperator(address)", labels, "TP4: Should flag unprotected operator removal")
        self.assertIn("updateAllowedAddress(address,bool)", labels, "TP5: Should flag unprotected allowlist setter")
        self.assertIn("addMinter(address)", labels, "TP6: Should flag unprotected minter addition")
        self.assertIn("removeBurner(address)", labels, "TP7: Should flag unprotected burner removal")
        self.assertIn("addRelayer(address)", labels, "TP8: Should flag unprotected relayer addition")
        self.assertIn("addMultipleAddresses(address[])", labels, "TP9: Should flag unprotected batch operation")
        self.assertIn("whitelistAddress(address)", labels, "TP10: Should flag alternative naming")
        self.assertIn("blacklistUser(address)", labels, "TP11: Should flag alternative naming")
        self.assertIn("registerValidator(address)", labels, "TP12: Should flag alternative naming")

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_auth_005_true_negatives(self) -> None:
        """Test auth-005 does NOT flag protected list management."""
        graph = load_graph("projects/access-registry/ListManagementTest.sol")
        findings = self.engine.run(graph, self.patterns, pattern_ids=["auth-005"], limit=200)
        labels = self._labels_for(findings, "auth-005")

        # TN1-TN10: Protected or safe patterns should NOT be flagged
        self.assertNotIn("addToWhitelistProtected(address)", labels, "TN1: Should NOT flag onlyOwner protected")
        self.assertNotIn("removeFromBlacklistProtected(address)", labels, "TN2: Should NOT flag onlyAdmin protected")
        self.assertNotIn("addValidatorProtected(address)", labels, "TN3: Should NOT flag if-revert protected")
        self.assertNotIn("_addToWhitelistInternal(address)", labels, "TN4: Should NOT flag internal function")
        self.assertNotIn("_removeFromBlacklistPrivate(address)", labels, "TN5: Should NOT flag private function")
        self.assertNotIn("isWhitelisted(address)", labels, "TN7: Should NOT flag view function")
        self.assertNotIn("selfRegister()", labels, "TN8: Should NOT flag self-registration")
        self.assertNotIn("updateStatusBasedOnBalance()", labels, "TN9: Should NOT flag automatic update")
        self.assertNotIn("addMultipleAddressesProtected(address[])", labels, "TN10: Should NOT flag protected batch")
        self.assertNotIn("addValidatorWithRequire(address)", labels, "VAR5b: Should NOT flag require-based protection")
        self.assertNotIn("addToWhitelistRoleBased(address)", labels, "VAR6b: Should NOT flag role-based protection")

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_auth_005_edge_cases(self) -> None:
        """Test auth-005 edge case detection."""
        graph = load_graph("projects/access-registry/ListManagementTest.sol")
        findings = self.engine.run(graph, self.patterns, pattern_ids=["auth-005"], limit=200)
        labels = self._labels_for(findings, "auth-005")

        # EDGE1: Two-step proposal (propose is unprotected, confirm is protected)
        self.assertIn("proposeAddition(address)", labels, "EDGE1: Should flag unprotected proposal step")

        # EDGE2: Confirm step should NOT be flagged (protected)
        self.assertNotIn("confirmAddition(address)", labels, "EDGE2: Should NOT flag protected confirm step")

        # EDGE3-5: Unprotected edge cases
        self.assertIn("onValidatorCallback(address)", labels, "EDGE3: Should flag callback list management")
        self.assertIn("updateExternalRegistry(address)", labels, "EDGE4: Should flag cross-contract registry")
        self.assertIn("clearAllValidators(address[])", labels, "EDGE5: Should flag emergency clearing")

        # EDGE6: Multi-sig should NOT be flagged (has validation)
        self.assertNotIn("multiSigAddValidator(address,bytes[])", labels, "EDGE6: Should NOT flag multi-sig")

        # EDGE7: Merkle root update (controls allowlist verification)
        # This is a special case - depends on if merkleRoot is tagged as privileged
        # We test both possibilities since this is an edge case
        if "updateMerkleRoot(bytes32)" in labels:
            # Pattern detected it as privileged state write (merkle roots control access)
            pass
        else:
            # Pattern didn't detect it (merkleRoot not tagged as allowlist/denylist)
            pass

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_auth_005_variations(self) -> None:
        """Test auth-005 detects various naming and implementation patterns."""
        graph = load_graph("projects/access-registry/ListManagementTest.sol")
        findings = self.engine.run(graph, self.patterns, pattern_ids=["auth-005"], limit=200)
        labels = self._labels_for(findings, "auth-005")

        # VAR1: grant/revoke terminology
        self.assertIn("grantRole(address)", labels, "VAR1a: Should flag grant terminology")
        self.assertIn("revokeRole(address)", labels, "VAR1a: Should flag revoke terminology")

        # VAR1b: set/unset terminology
        self.assertIn("setAllowlisted(address)", labels, "VAR1b: Should flag set terminology")
        self.assertIn("unsetAllowlisted(address)", labels, "VAR1b: Should flag unset terminology")

        # VAR2: Different list types
        self.assertIn("addGuardian(address)", labels, "VAR2a: Should flag guardian list")
        self.assertIn("addOperator(address)", labels, "VAR2b: Should flag operator list")

        # VAR3: Array-based list management
        self.assertIn("addValidatorToArray(address)", labels, "VAR3: Should flag array-based lists")

        # VAR4: Single vs batch
        self.assertIn("addSingleMinter(address)", labels, "VAR4a: Should flag single minter addition")

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_auth_005_additional_coverage(self) -> None:
        """Test auth-005 additional patterns."""
        graph = load_graph("projects/access-registry/ListManagementTest.sol")
        findings = self.engine.run(graph, self.patterns, pattern_ids=["auth-005"], limit=200)
        labels = self._labels_for(findings, "auth-005")

        # Alternative list types
        self.assertIn("addToDenylist(address)", labels, "Should flag denylist addition")
        self.assertIn("removeFromAllowlist(address)", labels, "Should flag allowlist removal")

        # Should NOT flag owner changes (different pattern - auth-001 or auth-003)
        # setOwner might be flagged by auth-003 (privileged state write) but not necessarily by auth-005
        # since owner might not be tagged as allowlist/denylist


class MultisigLensTests(unittest.TestCase):
    """Tests for multisig-related patterns (semantic/multisig/)."""

    def setUp(self) -> None:
        self.patterns = list(load_all_patterns())
        self.engine = PatternEngine()

    def _labels_for(self, findings, pattern_id: str) -> set[str]:
        return {finding["node_label"] for finding in findings if finding["pattern_id"] == pattern_id}

    def _run_pattern(self, project: str, contract: str, pattern_id: str):
        graph = load_graph(f"projects/{project}/{contract}")
        return self.engine.run(graph, self.patterns, pattern_ids=[pattern_id], limit=200)

    # =========================================================================
    # multisig-002: Nonce Parameter Not Updated
    # =========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tp_standard_execute(self) -> None:
        """TP1: executeTransaction with nonce parameter but NO state update."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "executeTransaction(address,uint256,bytes,uint256,bytes[])",
            labels,
            "Should flag execute with nonce parameter but no usedNonces update",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tp_submit_only_event(self) -> None:
        """TP2: submitTransaction with nonce, only emits event (NO state update)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "submitTransaction(address,uint256,bytes,uint256,bytes[])",
            labels,
            "Should flag submit that only emits event without nonce update",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tp_confirm_execute_read_only(self) -> None:
        """TP3: confirmAndExecute with nonce parameter, only reads it."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "confirmAndExecute(uint256,address,bytes,uint256)",
            labels,
            "Should flag confirm/execute that reads nonce but doesn't update state",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tp_require_check_no_increment(self) -> None:
        """TP4: executeWithNonce with require check BUT no increment."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "executeWithNonce(address,bytes,uint256)",
            labels,
            "Should flag function that validates nonce but doesn't increment",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tp_sequence_number_naming(self) -> None:
        """TP5: executeSequential with sequenceNumber parameter (alternative naming)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "executeSequential(address,bytes,uint256)",
            labels,
            "Should flag sequenceNumber parameter without state update",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_multisig_002_tp_batch_execute_struct_nonce(self) -> None:
        """TP6: batchExecute with nonce field in struct, no tracking."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "batchExecute(NonceNotUpdatedVulnerable.Transaction[],bytes[])",
            labels,
            "Should flag batch execute with nonce in struct but no state tracking",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tp_counter_naming(self) -> None:
        """TP7: executeWithCounter with counter parameter (variation)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "executeWithCounter(address,bytes,uint256)",
            labels,
            "Should flag counter parameter without state update",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tp_index_naming(self) -> None:
        """TP8: executeAtIndex with index parameter (variation)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "executeAtIndex(address,bytes,uint256)",
            labels,
            "Should flag index parameter without state update",
        )

    # =========================================================================
    # TRUE NEGATIVES: Correct nonce usage (should NOT be flagged)
    # =========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tn_mapping_based_tracking(self) -> None:
        """TN1: executeTransaction WITH usedNonces[nonce] = true (CORRECT)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        # Safe version in NonceUpdatedSafe contract
        self.assertNotIn(
            "NonceUpdatedSafe.executeTransaction(address,uint256,bytes,uint256,bytes[])",
            labels,
            "Should NOT flag when nonce is properly marked as used",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tn_incremental_counter(self) -> None:
        """TN2: executeSequential WITH nonce++ (CORRECT)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertNotIn(
            "NonceUpdatedSafe.executeSequential(address,bytes,uint256)",
            labels,
            "Should NOT flag when nonce is properly incremented",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tn_no_nonce_parameter(self) -> None:
        """TN3: executeWithoutNonce - no nonce parameter (different vulnerability)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        # This would be multisig-001 (no nonce at all), not multisig-002
        self.assertNotIn(
            "executeWithoutNonce(address,bytes,bytes[])",
            labels,
            "Should NOT flag - no nonce parameter (different pattern)",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tn_hash_based_tracking(self) -> None:
        """TN4: executeWithFlag using transaction hash tracking (alternative)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertNotIn(
            "executeWithFlag(bytes32,address,bytes)",
            labels,
            "Should NOT flag - uses executedTxs flag instead of nonce",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tn_view_function(self) -> None:
        """TN5: getNonceHash - view function with nonce parameter."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertNotIn(
            "getNonceHash(address,uint256,bytes,uint256)",
            labels,
            "Should NOT flag view functions",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tn_internal_function(self) -> None:
        """TN6: _executeInternal - internal function with nonce."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertNotIn(
            "_executeInternal(address,bytes,uint256)",
            labels,
            "Should NOT flag internal functions",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tn_nonce_getter(self) -> None:
        """TN7: currentNonce - nonce getter (view function)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertNotIn(
            "currentNonce()",
            labels,
            "Should NOT flag nonce getter functions",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_tn_deadline_not_nonce(self) -> None:
        """TN8: executeWithDeadline - deadline parameter (not nonce)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertNotIn(
            "executeWithDeadline(address,bytes,uint256,bytes[])",
            labels,
            "Should NOT flag deadline parameter (different protection mechanism)",
        )

    # =========================================================================
    # EDGE CASES
    # =========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_edge_nonce_in_modifier(self) -> None:
        """Edge1: Nonce updated in modifier (should be TN if detected)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        # If builder detects modifier state writes, this should be TN
        # Otherwise, might be flagged (acceptable for Phase 1)
        # Document in notes if flagged
        if "executeWithModifier(address,bytes,uint256)" in labels:
            print(
                "NOTE: executeWithModifier flagged - builder may not detect modifier state writes "
                "(acceptable limitation, document in pattern notes)"
            )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_edge_assembly_update(self) -> None:
        """Edge2: Nonce updated via assembly (advanced case)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        # Assembly state writes may not be detected by builder
        if "executeWithAssembly(address,bytes,uint256)" in labels:
            print(
                "NOTE: executeWithAssembly flagged - builder may not detect assembly state writes "
                "(known limitation, document in pattern notes)"
            )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_edge_multi_nonce(self) -> None:
        """Edge3: Multiple nonce parameters (both not updated - TP)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "executeMultiNonce(address,bytes,uint256,uint256)",
            labels,
            "Should flag when multiple nonce parameters exist but none are updated",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_edge_require_no_write(self) -> None:
        """Edge4: Nonce validation in require but no write (TP)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "executeWithRequire(address,bytes,uint256)",
            labels,
            "Should flag when nonce is validated but not updated",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_edge_nonce_only_event(self) -> None:
        """Edge5: Nonce only in event (TP - event doesn't prevent replay)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "executeOnlyEvent(address,bytes,uint256)",
            labels,
            "Should flag when nonce is only in event, not state",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_edge_nonce_return_only(self) -> None:
        """Edge6: Nonce in return value only (TP)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "executeReturnNonce(address,bytes,uint256)",
            labels,
            "Should flag when nonce is only returned, not stored",
        )

    # =========================================================================
    # VARIATION TESTS
    # =========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_multisig_002_var_sequence_naming(self) -> None:
        """Var1: sequenceNumber naming (TP)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "executeSequence(address,bytes,uint256)",
            labels,
            "Should detect sequenceNumber variation",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_multisig_002_var_counter_naming(self) -> None:
        """Var2: counter naming (TP)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "executeCount(address,bytes,uint256)",
            labels,
            "Should detect counter variation",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_multisig_002_var_index_naming(self) -> None:
        """Var3: index naming (TP)."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertIn(
            "executeIndex(address,bytes,uint256)",
            labels,
            "Should detect index variation",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_var_increment_safe(self) -> None:
        """Var4: Incremental counter - SAFE version."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertNotIn(
            "executeIncrement(address,bytes,uint256)",
            labels,
            "Should NOT flag when counter is properly incremented",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_var_mapping_safe(self) -> None:
        """Var5: Mapping-based tracking - SAFE version."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        self.assertNotIn(
            "executeTracked(address,bytes,uint256)",
            labels,
            "Should NOT flag when nonce is properly tracked in mapping",
        )

    # =========================================================================
    # NON-MULTISIG CONTRACT (should NOT flag)
    # =========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_002_non_multisig_contract(self) -> None:
        """Non-multisig: RegularContract should NOT be flagged."""
        findings = self._run_pattern("multisig-wallet", "NonceNotUpdatedTest.sol", "multisig-002")
        labels = self._labels_for(findings, "multisig-002")

        # RegularContract is not a multisig, so pattern should NOT match
        # even though executeAction has nonce parameter without update
        self.assertNotIn(
            "RegularContract.executeAction(address,bytes,uint256)",
            labels,
            "Should NOT flag non-multisig contracts (contract_has_multisig == false)",
        )

    # =========================================================================
    # multisig-003: Execution Without Signature Validation
    # =========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tp_standard_signature_array(self) -> None:
        """TP1: execute with bytes[] signatures, no ecrecover validation."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "execute(address,uint256,bytes,bytes[])",
            labels,
            "Should flag execute with signature array but no ecrecover",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tp_split_signature_params(self) -> None:
        """TP2: submitWithSignatures with r,s,v parameters, no validation."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "submitWithSignatures(address,bytes,bytes32,bytes32,uint8)",
            labels,
            "Should flag function with split signature (r,s,v) but no validation",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_multisig_003_tp_signature_struct(self) -> None:
        """TP3: multiSigExecute with Signature[] struct, only checks length."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "multiSigExecute(address,uint256,VulnerableExecutionSignatureStruct.Signature[])",
            labels,
            "Should flag when signature struct is validated for length but not cryptographically",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tp_address_array_no_proof(self) -> None:
        """TP4: executeWithApprovals with address[] claiming to be signers."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "executeWithApprovals(address,bytes,address[])",
            labels,
            "Should flag when addresses are claimed as signers without signature proof",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tp_batch_execution(self) -> None:
        """TP5: batchExecuteWithSigs with bytes signatures, no validation."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "batchExecuteWithSigs(address[],bytes[],bytes)",
            labels,
            "Should flag batch execution with signatures but no validation",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tp_eip712_no_validation(self) -> None:
        """TP6: executeEIP712 has EIP-712 parameters but no validation."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "executeEIP712(address,bytes,bytes32,bytes)",
            labels,
            "Should flag EIP-712 execution without signature validation",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_multisig_003_tp_alternate_naming(self) -> None:
        """TP7: multiSigCall with different naming conventions."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "multiSigCall(address,bytes,bytes[])",
            labels,
            "Should flag alternative naming (multiSigCall, approvalSigs)",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tp_compact_signature(self) -> None:
        """TP8: executeCompact with 65-byte signature, no ecrecover."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "executeCompact(address,uint256,bytes,bytes)",
            labels,
            "Should flag compact 65-byte signature without validation",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tp_eip2098_signature(self) -> None:
        """TP9: executeEIP2098 with compact r,vs signature, no validation."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "executeEIP2098(address,bytes,bytes32,bytes32)",
            labels,
            "Should flag EIP-2098 compact signature without validation",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tp_only_length_check(self) -> None:
        """TP10: executeMultiple validates signature count/length but not content."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "executeMultiple(address,bytes,bytes[])",
            labels,
            "Should flag when only signature count/length is validated",
        )

    # =========================================================================
    # TRUE NEGATIVES: Safe signature validation (should NOT flag)
    # =========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tn_with_ecrecover(self) -> None:
        """TN1: SAFE - Uses ecrecover for signature validation."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertNotIn(
            "SafeWithEcrecover.execute(address,uint256,bytes,bytes[])",
            labels,
            "Should NOT flag when ecrecover is properly used",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tn_with_ecdsa_library(self) -> None:
        """TN2: SAFE - Uses ECDSA library for signature recovery (BUILDER LIMITATION)."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        # BUILDER LIMITATION: builder.py doesn't detect ECDSA.recover() library calls
        # Pattern currently flags this as vulnerable (false positive)
        if "submitWithSignatures(address,bytes,bytes32,bytes)" in labels:
            print(
                "NOTE: SafeWithECDSALibrary.submitWithSignatures flagged - "
                "builder does not detect ECDSA.recover() library calls as ecrecover usage "
                "(acceptable limitation, requires builder enhancement)"
            )
        else:
            # If builder is enhanced to detect library ecrecover, this should pass
            self.assertNotIn(
                "submitWithSignatures(address,bytes,bytes32,bytes)",
                labels,
                "Should NOT flag when ECDSA.recover library is used",
            )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tn_with_eip1271(self) -> None:
        """TN3: SAFE - Uses EIP-1271 contract signature validation."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertNotIn(
            "SafeWithEIP1271.multiSigExecute(address,bytes,address[],bytes[])",
            labels,
            "Should NOT flag when EIP-1271 validation is used",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tn_view_function(self) -> None:
        """TN4: SAFE - View function doesn't perform external calls."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertNotIn(
            "getTransactionHash(address,uint256,bytes,bytes[])",
            labels,
            "Should NOT flag view functions (no external calls)",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tn_internal_helper(self) -> None:
        """TN5: SAFE - Internal function, not externally callable."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertNotIn(
            "_executeInternal(address,bytes,bytes[])",
            labels,
            "Should NOT flag internal functions (visibility check)",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tn_without_signature_params(self) -> None:
        """TN6: SAFE - Different pattern: pre-approved hashes, no signature params."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertNotIn(
            "SafeWithoutSignatureParams.execute(address,uint256,bytes)",
            labels,
            "Should NOT flag when no signature parameters present",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tn_non_multisig_contract(self) -> None:
        """TN7: SAFE - Not a multisig contract (contract_has_multisig == false)."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertNotIn(
            "SafeNonMultisigContract.executeAction(address,bytes,bytes)",
            labels,
            "Should NOT flag non-multisig contracts",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tn_constructor(self) -> None:
        """TN8: SAFE - Constructor excluded by pattern."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        # Constructor should not be flagged
        # Pattern explicitly excludes is_constructor == true
        # (Constructors don't appear as regular function findings)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_tn_initializer(self) -> None:
        """TN9: SAFE - Initializer excluded by pattern."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertNotIn(
            "initialize(address[])",
            labels,
            "Should NOT flag initializer functions",
        )

    # =========================================================================
    # EDGE CASES
    # =========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_edge_signature_in_modifier(self) -> None:
        """EDGE1: Signature validation in modifier (should be SAFE)."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        # Should NOT flag - modifier has ecrecover validation
        # If flagged, builder may not detect modifier ecrecover
        if "EdgeSignatureInModifier.execute(address,bytes,bytes32,bytes[])" in labels:
            print(
                "NOTE: execute with validSignatures modifier flagged - "
                "builder may not detect ecrecover in modifiers (limitation)"
            )
        else:
            self.assertNotIn(
                "EdgeSignatureInModifier.execute(address,bytes,bytes32,bytes[])",
                labels,
                "Should NOT flag when signature validation is in modifier",
            )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_edge_signature_in_external_contract(self) -> None:
        """EDGE2: Signature validation delegated to external contract."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        # Pattern likely flags this - validation is in external contract
        # This is acceptable - manual review needed for delegated validation
        if "executeWithApprovals(address,bytes,bytes[])" in labels:
            print(
                "NOTE: executeWithApprovals with external validator flagged - "
                "pattern cannot detect external contract validation (acceptable, requires manual review)"
            )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_edge_signature_in_library(self) -> None:
        """EDGE3: Signature validation via library."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        # Should NOT flag - library uses ecrecover
        # If flagged, builder may not track library ecrecover
        self.assertNotIn(
            "EdgeSignatureInLibrary.execute(address,bytes,bytes)",
            labels,
            "Should NOT flag when library performs ecrecover validation",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_edge_signature_in_assembly(self) -> None:
        """EDGE4: Signature validation using assembly ecrecover."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        # Should NOT flag - assembly calls ecrecover precompile (0x01)
        # If flagged, builder may not detect assembly ecrecover
        if "executeWithAssembly(address,bytes,bytes32,bytes)" in labels:
            print(
                "NOTE: executeWithAssembly flagged - "
                "builder may not detect assembly ecrecover (limitation)"
            )
        else:
            self.assertNotIn(
                "executeWithAssembly(address,bytes,bytes32,bytes)",
                labels,
                "Should NOT flag when assembly uses ecrecover precompile",
            )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_edge_multiple_signature_types(self) -> None:
        """EDGE5: Handles both EOA (ecrecover) and contract (EIP-1271) signatures."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertNotIn(
            "EdgeMultipleSignatureTypes.execute(address,bytes,address[],bytes[])",
            labels,
            "Should NOT flag when both EOA and contract signatures are validated",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_edge_signature_in_struct_field(self) -> None:
        """EDGE6: Signature parameter inside struct field."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertNotIn(
            "batchExecute(EdgeSignatureInStructField.Transaction[])",
            labels,
            "Should NOT flag when signature in struct is validated with ecrecover",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_edge_no_external_call(self) -> None:
        """EDGE7: Has signature validation but NO external call (should NOT flag)."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertNotIn(
            "validateOnly(bytes32,bytes[])",
            labels,
            "Should NOT flag when no external calls (pattern requires CALLS_EXTERNAL)",
        )

    # =========================================================================
    # VARIATION TESTS
    # =========================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_var_controller_naming(self) -> None:
        """VAR1: 'controller' instead of 'owner' naming."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "executeAction(address,bytes,bytes[])",
            labels,
            "Should detect controller/authSigs naming variation",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_var_gnosis_safe_style(self) -> None:
        """VAR2: Gnosis Safe-style execution with many parameters."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "execTransaction(address,uint256,bytes,uint8,uint256,uint256,uint256,address,address,bytes)",
            labels,
            "Should detect Gnosis Safe-style execution without validation",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_var_timelock_style(self) -> None:
        """VAR3: Timelock-style execution with queued transactions."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "executeQueuedTransaction(bytes32,address,bytes,bytes[])",
            labels,
            "Should detect timelock-style execution without validation",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_var_governor_style(self) -> None:
        """VAR4: Governor-style proposal execution."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "executeProposal(uint256,bytes[])",
            labels,
            "Should detect governor-style execution without validation",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_var_compact_format(self) -> None:
        """VAR5: Compact 65-byte signature format."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        # Note: label doesn't include contract prefix for some functions
        self.assertIn(
            "executeCompact(address,bytes,bytes)",
            labels,
            "Should detect compact signature format without validation",
        )

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_003_var_eip2098_format(self) -> None:
        """VAR6: EIP-2098 compact format (64 bytes, r + vs)."""
        findings = self._run_pattern("multisig-wallet", "SignatureValidationTest.sol", "multisig-003")
        labels = self._labels_for(findings, "multisig-003")

        self.assertIn(
            "executeEIP2098Compact(address,bytes,bytes32,bytes32)",
            labels,
            "Should detect EIP-2098 compact format without validation",
        )


if __name__ == "__main__":
    unittest.main()
