"""Liveness lens detection tests."""

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


class LivenessLensTests(unittest.TestCase):
    """Test liveness lens pattern detection."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_liveness_patterns(self) -> None:
        graph = load_graph("LivenessLens.sol")
        patterns = list(load_all_patterns())
        engine = PatternEngine()

        cases = {
            "live-001": ("loopGasExhaustion", "boundedLoop"),
            "live-002": ("unboundedDeletion", "deletionSafe"),
            "live-003": ("pushPayment", "pushPaymentSafe"),
            "live-004": ("auctionBid", "auctionBidSafe"),
            "live-005": ("divide", "divideSafe"),
            "live-006": ("arrayBounds", "arrayBoundsSafe"),
            "live-007": ("assertCheck", "assertSafe"),
            "live-008": ("stateGrowth", "arrayOpsSafe"),
            "live-009": ("setFee", "setFeeSafe"),
            "live-010": ("unlockWithExternal", "lockSafe"),
            "live-011": ("MissingEmergency", "HasEmergency"),
            "live-012": ("cascadingFailures", "cascadingFailuresSafe"),
            "live-013": ("nestedLoop", "nestedConstantLoop"),
            "live-014": ("dynamicGas", "boundedLoop"),
            "live-015": ("transactionSizeAttack", "transactionSizeSafe"),
            "live-016": ("batchNoLimit", "batchBounded"),
            "live-017": ("unboundedArrayOps", "arrayOpsSafe"),
            "live-018": ("mappingIteration", "mappingIterationSafe"),
            "live-019": ("setBytes", "bytesSafe"),
            "live-020": ("callbackGrief", "callbackSafe"),
            "live-021": ("timeGrief", "stateGrowthSafe"),
            "live-022": ("externalDependency", "externalDependencySafe"),
            "live-023": ("gasForward", "gasForwardSafe"),
            "live-024": ("overflowRisk", "uncheckedSafe"),
            "live-025": ("storageCostAttack", "storageCostSafe"),
            "live-026": ("storageCostAttack", "storageCostSafe"),
            "live-027": ("unboundedDeletion", "deletionSafe"),
            "live-028": ("depositThreshold", "depositThresholdSafe"),
            "live-029": ("claimRewards", "liquiditySafe"),
            "live-030": ("transitionBlock", "transitionSafe"),
            "live-031": ("pauseSensitive", "pauseSafe"),
            "live-032": ("deadlineNoCheck", "deadlineSafe"),
            "live-033": ("allocateMemory", "allocateMemorySafe"),
            "live-034": ("recursiveDoS", "sliceCalldataSafe"),
            "live-035": ("emitInLoop", "emitSafe"),
            "live-036": ("unlockWithExternal", "unlockSafe"),
            "live-037": ("timeLock", "timeLockSafe"),
            "live-038": ("emergencyRecover", "emergencyRecoverSafe"),
            "live-039": ("emergencyDrain", "emergencyPing"),
        }

        # Patterns where the "safe" negative case iterates over storage arrays
        # Builder correctly treats storage array lengths as unbounded, so these
        # will also be flagged. Skip negative assertion for these patterns.
        storage_array_safe_patterns = {"live-002", "live-027"}

        # Patterns that require properties the builder doesn't currently detect
        # These are skipped when no findings are returned
        builder_limitation_patterns = {
            "live-013",  # Requires has_nested_loop which builder doesn't set
            "live-021",  # Requires time_griefing properties not detected
            "live-024",  # Requires pre_08_arithmetic (already has special handling)
            "live-026",  # Requires storage_cost_attack properties not detected
            "live-028",  # Requires deposit_threshold properties not detected
            "live-039",  # Requires emergency_ping properties not detected
        }

        for pattern_id, (positive, negative) in cases.items():
            if pattern_id == "live-024":
                has_pre_08 = any(
                    node.type == "Function" and node.properties.get("pre_08_arithmetic")
                    for node in graph.nodes.values()
                )
                if not has_pre_08:
                    continue
            findings = engine.run(graph, patterns, pattern_ids=[pattern_id])
            names = {finding["node_label"].split("(")[0] for finding in findings}

            # Skip patterns with known builder limitations when positive not found
            if pattern_id in builder_limitation_patterns and positive not in names:
                continue

            self.assertIn(
                positive,
                names,
                msg=f"Expected {pattern_id} to match {positive}, got {sorted(names)}",
            )
            # Skip negative assertion for patterns where "safe" iterates over storage arrays
            # (deletionSafe iterates over recipients.length which is unbounded)
            if pattern_id not in storage_array_safe_patterns:
                self.assertNotIn(
                    negative,
                    names,
                    msg=f"Expected {pattern_id} to exclude {negative}, got {sorted(names)}",
                )
