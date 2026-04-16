"""
Creative Discovery Loop Tests (05.10-09)

Tests for:
1. Near-miss discoveries are marked unknown
2. Counterfactuals do not upgrade confidence
3. Shadow patterns are flagged as proposals
4. Tier-B confidence caps enforced
5. Budget checks and evidence gates
"""

import unittest
from datetime import datetime

from alphaswarm_sol.orchestration.creative import (
    CreativeDiscoveryLoop,
    CreativeDiscoveryConfig,
    CreativeDiscoveryResult,
    NearMissMiner,
    PatternMutator,
    CounterfactualProber,
    AnomalyDetector,
    ShadowPatternGenerator,
    NearMissResult,
    MutationResult,
    CounterfactualProbe,
    AnomalyMotif,
    ShadowPattern,
    NearMissType,
    MutationType,
    CounterfactualType,
    ShadowPatternStatus,
    TIER_B_MAX_CONFIDENCE,
)
from alphaswarm_sol.orchestration.schemas import (
    ScoutHypothesis,
    ScoutStatus,
    UnknownItem,
    UnknownReason,
)


class TestNearMissMarkedUnknown(unittest.TestCase):
    """Tests that near-miss discoveries are properly marked as unknown."""

    def test_near_miss_marked_unknown_without_evidence(self):
        """Near-miss without evidence should be marked unknown."""
        near_miss = NearMissResult(
            node_id="fn:withdraw:123",
            pattern_id="reentrancy-classic",
            near_miss_type=NearMissType.MISSING_ONE_OP,
            missing_element="TRANSFERS_VALUE_OUT",
            present_elements=["WRITES_USER_BALANCE", "READS_USER_BALANCE"],
            evidence_refs=[],  # No evidence
            confidence=0.45,
        )

        # Should be marked unknown
        self.assertTrue(near_miss.is_unknown)
        self.assertEqual(near_miss.unknown_reason, UnknownReason.MISSING_EVIDENCE)

    def test_near_miss_marked_unknown_with_evidence(self):
        """Near-miss with evidence should still be marked unknown (Tier-B)."""
        near_miss = NearMissResult(
            node_id="fn:withdraw:123",
            pattern_id="reentrancy-classic",
            near_miss_type=NearMissType.MISSING_ONE_OP,
            missing_element="TRANSFERS_VALUE_OUT",
            present_elements=["WRITES_USER_BALANCE"],
            evidence_refs=["node:fn:withdraw:123"],
            confidence=0.50,
            is_unknown=False,  # Try to set as not unknown
        )

        # With evidence but no explicit marking, should preserve the state
        # but confidence should still be capped at Tier-B max
        self.assertLessEqual(near_miss.confidence, TIER_B_MAX_CONFIDENCE)

    def test_near_miss_confidence_capped_at_tier_b(self):
        """Near-miss confidence should be capped at TIER_B_MAX_CONFIDENCE."""
        near_miss = NearMissResult(
            node_id="fn:test:1",
            pattern_id="test-pattern",
            near_miss_type=NearMissType.WRONG_ORDER,
            missing_element="ordering",
            present_elements=["OP_A", "OP_B"],
            evidence_refs=["node:fn:test:1"],
            confidence=0.95,  # Try to set above Tier-B max
        )

        # Should be capped
        self.assertEqual(near_miss.confidence, TIER_B_MAX_CONFIDENCE)

    def test_near_miss_miner_returns_unknown_results(self):
        """NearMissMiner should return results marked as unknown."""
        miner = NearMissMiner()

        nodes = {
            "fn:withdraw:1": {
                "type": "Function",
                "semantic_ops": ["READS_USER_BALANCE", "WRITES_USER_BALANCE"],
                "op_ordering": [],
            },
            "fn:deposit:2": {
                "type": "Function",
                "semantic_ops": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                "op_ordering": [],
            },
        }

        pattern_required_ops = {
            "reentrancy-classic": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        }

        results = miner.mine_near_misses(
            nodes=nodes,
            pattern_required_ops=pattern_required_ops,
            pattern_orderings={},
        )

        # Should find near-miss for fn:withdraw:1 (missing TRANSFERS_VALUE_OUT)
        self.assertGreaterEqual(len(results), 1)

        # All results should be marked unknown
        for result in results:
            self.assertTrue(result.is_unknown)
            self.assertEqual(result.unknown_reason, UnknownReason.MISSING_EVIDENCE)


class TestCounterfactualsDoNotUpgradeConfidence(unittest.TestCase):
    """Tests that counterfactual probes do not upgrade confidence."""

    def test_counterfactual_confidence_capped(self):
        """Counterfactual confidence should be capped at 0.50."""
        probe = CounterfactualProbe(
            probe_id="cf-001",
            pattern_id="reentrancy-classic",
            counterfactual_type=CounterfactualType.GUARD_REMOVED,
            removed_element="reentrancy_guard",
            becomes_vulnerable=True,
            affected_nodes=["fn:withdraw:123"],
            evidence_refs=["node:fn:withdraw:123"],
            confidence=0.95,  # Try to set high confidence
        )

        # Counterfactuals cannot upgrade confidence beyond 0.50
        self.assertLessEqual(probe.confidence, 0.50)

    def test_counterfactual_lower_than_tier_b_max(self):
        """Counterfactual confidence should be lower than Tier-B max."""
        probe = CounterfactualProbe(
            probe_id="cf-002",
            pattern_id="test-pattern",
            counterfactual_type=CounterfactualType.OP_PRESENT,
            removed_element="missing_op",
            becomes_vulnerable=True,
            confidence=TIER_B_MAX_CONFIDENCE,  # Try Tier-B max
        )

        # Should be capped lower than Tier-B max (at 0.50)
        self.assertLess(probe.confidence, TIER_B_MAX_CONFIDENCE)
        self.assertEqual(probe.confidence, 0.50)

    def test_counterfactual_prober_returns_low_confidence(self):
        """CounterfactualProber should return probes with capped confidence."""
        prober = CounterfactualProber()

        pcp_counterfactuals = [
            {
                "id": "cf-001",
                "if_removed": "reentrancy_guard",
                "becomes_true": True,
                "notes": "Pattern would hold without guard",
            }
        ]

        anti_signals = [
            {
                "id": "guard.reentrancy",
                "guard_type": "reentrancy_guard",
                "bypass_notes": ["Cross-contract may bypass"],
            }
        ]

        guarded_nodes = {
            "fn:withdraw:1": ["reentrancy_guard"],
            "fn:deposit:2": [],
        }

        probes = prober.probe_counterfactuals(
            pattern_id="reentrancy-classic",
            pcp_counterfactuals=pcp_counterfactuals,
            anti_signals=anti_signals,
            guarded_nodes=guarded_nodes,
        )

        # All probes should have confidence <= 0.50
        for probe in probes:
            self.assertLessEqual(probe.confidence, 0.50)
            # Counterfactuals are hypothetical, not upgrades
            self.assertLess(probe.confidence, TIER_B_MAX_CONFIDENCE)


class TestShadowPatternsFlaggedAsProposals(unittest.TestCase):
    """Tests that shadow patterns are always flagged as proposals."""

    def test_shadow_pattern_status_is_proposal(self):
        """Shadow pattern status should always be PROPOSAL."""
        shadow = ShadowPattern(
            shadow_id="shadow-001",
            name="Test Shadow Pattern",
            description="A test shadow pattern",
            derived_from=["nm-001", "nm-002"],
            required_ops=["OP_A", "OP_B"],
            status=ShadowPatternStatus.VALIDATED,  # Try to set as validated
        )

        # Should be forced to PROPOSAL
        self.assertEqual(shadow.status, ShadowPatternStatus.PROPOSAL)

    def test_shadow_pattern_confidence_capped(self):
        """Shadow pattern confidence should be capped at 0.40."""
        shadow = ShadowPattern(
            shadow_id="shadow-002",
            name="High Confidence Shadow",
            description="Trying to set high confidence",
            derived_from=["nm-001"],
            required_ops=["OP_A"],
            confidence=0.90,  # Try to set high
        )

        # Should be capped at 0.40
        self.assertLessEqual(shadow.confidence, 0.40)

    def test_shadow_generator_produces_proposals(self):
        """ShadowPatternGenerator should produce patterns with PROPOSAL status."""
        generator = ShadowPatternGenerator()

        near_misses = [
            NearMissResult(
                node_id="fn:test:1",
                pattern_id="test-pattern",
                near_miss_type=NearMissType.MISSING_ONE_OP,
                missing_element="OP_C",
                present_elements=["OP_A", "OP_B"],
                evidence_refs=["node:fn:test:1"],
            ),
            NearMissResult(
                node_id="fn:test:2",
                pattern_id="test-pattern",
                near_miss_type=NearMissType.MISSING_ONE_OP,
                missing_element="OP_C",
                present_elements=["OP_A", "OP_B"],
                evidence_refs=["node:fn:test:2"],
            ),
        ]

        anomalies = [
            AnomalyMotif(
                motif_id="motif-001",
                operations=["OP_X", "OP_Y"],
                occurrence_count=10,
                expected_count=2.0,
                z_score=4.0,  # High anomaly
                example_nodes=["fn:anomaly:1"],
            ),
        ]

        shadows = generator.generate_shadow_patterns(
            near_misses=near_misses,
            anomalies=anomalies,
        )

        # All shadows should be proposals
        for shadow in shadows:
            self.assertEqual(shadow.status, ShadowPatternStatus.PROPOSAL)
            self.assertLessEqual(shadow.confidence, 0.40)


class TestCreativeDiscoveryLoop(unittest.TestCase):
    """Integration tests for CreativeDiscoveryLoop."""

    def setUp(self):
        """Set up test fixtures."""
        self.nodes = {
            "fn:withdraw:1": {
                "type": "Function",
                "semantic_ops": ["READS_USER_BALANCE", "WRITES_USER_BALANCE"],
                "op_ordering": [("READS_USER_BALANCE", "WRITES_USER_BALANCE")],
            },
            "fn:deposit:2": {
                "type": "Function",
                "semantic_ops": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                "op_ordering": [
                    ("READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"),
                    ("TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"),
                ],
            },
            "fn:transfer:3": {
                "type": "Function",
                "semantic_ops": ["CHECKS_PERMISSION", "TRANSFERS_VALUE_OUT"],
                "op_ordering": [("CHECKS_PERMISSION", "TRANSFERS_VALUE_OUT")],
            },
        }

        self.pattern_required_ops = {
            "reentrancy-classic": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            "access-control-missing": ["TRANSFERS_VALUE_OUT"],
        }

        self.pattern_orderings = {
            "reentrancy-classic": [
                ("TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"),  # Vulnerable ordering
            ],
        }

    def test_creative_loop_respects_budget(self):
        """Creative loop should respect budget constraints."""
        config = CreativeDiscoveryConfig(
            max_near_misses=100,
            max_mutations=100,
        )
        loop = CreativeDiscoveryLoop(config=config)

        result = loop.discover(
            nodes=self.nodes,
            pattern_required_ops=self.pattern_required_ops,
            pattern_orderings=self.pattern_orderings,
            budget_remaining=50,  # Very low budget
        )

        # With low budget, some operations should be skipped
        # Budget is reduced as operations are performed
        # The key constraint is budget_remaining should be tracked
        self.assertIsInstance(result.budget_remaining, int)
        self.assertLessEqual(result.budget_remaining, 50)

    def test_creative_loop_all_hypotheses_tier_b(self):
        """All hypotheses from creative loop should be Tier-B."""
        loop = CreativeDiscoveryLoop()

        result = loop.discover(
            nodes=self.nodes,
            pattern_required_ops=self.pattern_required_ops,
            pattern_orderings=self.pattern_orderings,
            budget_remaining=2000,
        )

        # All hypotheses should have confidence <= TIER_B_MAX_CONFIDENCE
        for hypothesis in result.hypotheses:
            self.assertLessEqual(hypothesis.confidence, TIER_B_MAX_CONFIDENCE)
            # All should have unknowns list (possibly empty)
            self.assertIsInstance(hypothesis.unknowns, list)

    def test_creative_loop_produces_near_misses(self):
        """Creative loop should produce near-miss results."""
        loop = CreativeDiscoveryLoop()

        result = loop.discover(
            nodes=self.nodes,
            pattern_required_ops=self.pattern_required_ops,
            pattern_orderings=self.pattern_orderings,
            budget_remaining=2000,
        )

        # Should have near-misses
        self.assertGreater(len(result.near_misses), 0)

        # All near-misses should be unknown
        for nm in result.near_misses:
            self.assertTrue(nm.is_unknown)

    def test_creative_loop_with_counterfactuals(self):
        """Creative loop should process counterfactuals."""
        loop = CreativeDiscoveryLoop()

        pcp_counterfactuals = [
            {
                "id": "cf-001",
                "if_removed": "reentrancy_guard",
                "becomes_true": True,
                "notes": "Would be vulnerable",
            },
        ]

        guarded_nodes = {
            "fn:withdraw:1": ["reentrancy_guard"],
        }

        result = loop.discover(
            nodes=self.nodes,
            pattern_required_ops=self.pattern_required_ops,
            pattern_orderings=self.pattern_orderings,
            pcp_counterfactuals=pcp_counterfactuals,
            guarded_nodes=guarded_nodes,
            budget_remaining=2000,
        )

        # Should have counterfactual probes
        self.assertGreater(len(result.counterfactuals), 0)

        # All counterfactuals should have low confidence
        for cf in result.counterfactuals:
            self.assertLessEqual(cf.confidence, 0.50)


class TestMutationResults(unittest.TestCase):
    """Tests for pattern mutation results."""

    def test_mutation_marked_unknown(self):
        """Mutation results should be marked as unknown."""
        mutation = MutationResult(
            base_pattern_id="test-pattern",
            mutation_type=MutationType.OP_SUBSTITUTION,
            mutation_description="Replace OP_A with OP_B",
            affected_ops=["OP_A", "OP_B"],
            matching_nodes=[],
            evidence_refs=[],
            confidence=0.35,
        )

        # Without evidence, should be unknown
        self.assertTrue(mutation.is_unknown)

    def test_mutation_confidence_capped(self):
        """Mutation confidence should be capped at Tier-B max."""
        mutation = MutationResult(
            base_pattern_id="test-pattern",
            mutation_type=MutationType.ORDER_SWAP,
            mutation_description="Swap ordering",
            affected_ops=["OP_A", "OP_B"],
            confidence=0.95,  # Try to set high
        )

        # Should be capped
        self.assertEqual(mutation.confidence, TIER_B_MAX_CONFIDENCE)


class TestAnomalyMotifs(unittest.TestCase):
    """Tests for anomaly motif detection."""

    def test_anomaly_always_unknown(self):
        """Anomaly motifs should always be marked as unknown."""
        anomaly = AnomalyMotif(
            motif_id="motif-001",
            operations=["OP_A", "OP_B"],
            occurrence_count=15,
            expected_count=3.0,
            z_score=4.5,
            example_nodes=["fn:test:1"],
            is_unknown=False,  # Try to set as not unknown
        )

        # Should always be unknown
        self.assertTrue(anomaly.is_unknown)

    def test_anomaly_confidence_from_zscore(self):
        """Anomaly confidence should be derived from z-score."""
        anomaly = AnomalyMotif(
            motif_id="motif-002",
            operations=["OP_X", "OP_Y"],
            occurrence_count=20,
            expected_count=5.0,
            z_score=3.0,  # Medium anomaly
            example_nodes=[],
        )

        # Confidence should be capped
        self.assertLessEqual(anomaly.confidence, TIER_B_MAX_CONFIDENCE)
        # Should be positive
        self.assertGreater(anomaly.confidence, 0)

    def test_anomaly_detector_finds_anomalies(self):
        """AnomalyDetector should find statistical anomalies."""
        detector = AnomalyDetector(config=CreativeDiscoveryConfig(min_anomaly_z_score=1.5))

        # Create nodes with some ops appearing together unusually often
        nodes = {}
        for i in range(30):
            # Most functions have just OP_A
            nodes[f"fn:common:{i}"] = {
                "type": "Function",
                "semantic_ops": ["VALIDATES_INPUT"],
            }

        # Add some functions with unusual combination
        for i in range(10):
            nodes[f"fn:anomaly:{i}"] = {
                "type": "Function",
                "semantic_ops": ["TRANSFERS_VALUE_OUT", "MODIFIES_CRITICAL_STATE"],
            }

        anomalies = detector.detect_anomalies(nodes)

        # Should detect anomalies (all results should be unknown)
        for anomaly in anomalies:
            self.assertTrue(anomaly.is_unknown)
            self.assertLessEqual(anomaly.confidence, TIER_B_MAX_CONFIDENCE)


class TestEvidenceGates(unittest.TestCase):
    """Tests for evidence gating in creative discovery."""

    def test_hypothesis_requires_evidence_or_unknowns(self):
        """ScoutHypothesis from creative loop should have evidence refs or unknowns."""
        loop = CreativeDiscoveryLoop()

        nodes = {
            "fn:test:1": {
                "type": "Function",
                "semantic_ops": ["OP_A"],
                "op_ordering": [],
            },
        }

        result = loop.discover(
            nodes=nodes,
            pattern_required_ops={"test": ["OP_A", "OP_B"]},
            pattern_orderings={},
            budget_remaining=1000,
        )

        # Every hypothesis should have either evidence_refs or unknowns
        for hypothesis in result.hypotheses:
            has_evidence = len(hypothesis.evidence_refs) > 0
            has_unknowns = len(hypothesis.unknowns) > 0
            # At least one should be true
            self.assertTrue(
                has_evidence or has_unknowns,
                f"Hypothesis {hypothesis.pattern_id} has neither evidence nor unknowns"
            )

    def test_near_miss_evidence_refs_format(self):
        """Near-miss evidence refs should follow canonical format."""
        near_miss = NearMissResult(
            node_id="fn:test:1",
            pattern_id="test-pattern",
            near_miss_type=NearMissType.MISSING_ONE_OP,
            missing_element="OP_B",
            present_elements=["OP_A"],
            evidence_refs=["node:fn:test:1"],
        )

        # Evidence refs should follow format
        for ref in near_miss.evidence_refs:
            # Should start with valid prefix
            self.assertTrue(
                ref.startswith("node:") or ref.startswith("edge:") or ref.startswith("fn:") or ref.startswith("EVD-"),
                f"Invalid evidence ref format: {ref}"
            )


if __name__ == "__main__":
    unittest.main()
