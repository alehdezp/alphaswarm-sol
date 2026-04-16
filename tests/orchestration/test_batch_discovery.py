"""
Batch Discovery Orchestration v2 Tests (05.10-07)

Tests for:
1. Cache key changes on PCP version change
2. Adaptive batching groups by cost
3. Fork-then-rank selects deterministically
4. BatchManifest contains required fields
5. Cache versioning with graph hash + PCP version + budget policy
"""

import json
import unittest
from datetime import datetime

from alphaswarm_sol.agents.context.types import BudgetPolicy, BudgetPass
from alphaswarm_sol.orchestration.batch import (
    BatchDiscoveryOrchestrator,
    BatchManifest,
    AdaptiveBatcher,
    ForkThenRank,
    CacheKey,
    AdaptiveBatch,
    PatternCostEstimate,
    ForkResult,
    RankedResult,
    BatchPriority,
    RankingMethod,
    DEFAULT_COST_WEIGHTS,
)
from alphaswarm_sol.orchestration.schemas import (
    DiversityPolicy,
    DiversityPath,
    DiversityPathType,
    ScoutHypothesis,
    ScoutStatus,
    ContradictionReport,
    ContradictionStatus,
    UnknownItem,
    UnknownReason,
    Counterargument,
    CounterargumentType,
    CounterargumentStrength,
)


class TestCacheKeyVersioning(unittest.TestCase):
    """Tests for cache key versioning."""

    def test_cache_key_changes_on_pcp_version(self):
        """Cache key should change when PCP version changes."""
        orchestrator = BatchDiscoveryOrchestrator()
        graph_data = '{"nodes": {}, "edges": []}'

        key_v1 = orchestrator.compute_cache_key(graph_data, "v1.0")
        key_v2 = orchestrator.compute_cache_key(graph_data, "v2.0")

        # Keys should be different due to PCP version
        self.assertNotEqual(key_v1.to_string(), key_v2.to_string())

        # Graph hash should be the same
        self.assertEqual(key_v1.graph_hash, key_v2.graph_hash)

        # PCP version should differ
        self.assertEqual(key_v1.pcp_version, "v1.0")
        self.assertEqual(key_v2.pcp_version, "v2.0")

    def test_cache_key_changes_on_graph_change(self):
        """Cache key should change when graph changes."""
        orchestrator = BatchDiscoveryOrchestrator()

        graph_data_1 = '{"nodes": {"fn1": {}}, "edges": []}'
        graph_data_2 = '{"nodes": {"fn1": {}, "fn2": {}}, "edges": []}'

        key_1 = orchestrator.compute_cache_key(graph_data_1, "v2.0")
        key_2 = orchestrator.compute_cache_key(graph_data_2, "v2.0")

        # Keys should be different due to graph change
        self.assertNotEqual(key_1.to_string(), key_2.to_string())
        self.assertNotEqual(key_1.graph_hash, key_2.graph_hash)

    def test_cache_key_changes_on_budget_policy(self):
        """Cache key should change when budget policy changes."""
        budget_1 = BudgetPolicy(cheap_pass_tokens=2000, hard_limit=4000)
        budget_2 = BudgetPolicy(cheap_pass_tokens=4000, hard_limit=8000)

        orchestrator_1 = BatchDiscoveryOrchestrator(budget_policy=budget_1)
        orchestrator_2 = BatchDiscoveryOrchestrator(budget_policy=budget_2)

        graph_data = '{"nodes": {}, "edges": []}'

        key_1 = orchestrator_1.compute_cache_key(graph_data, "v2.0")
        key_2 = orchestrator_2.compute_cache_key(graph_data, "v2.0")

        # Budget hash should differ
        self.assertNotEqual(key_1.budget_policy_hash, key_2.budget_policy_hash)
        self.assertNotEqual(key_1.to_string(), key_2.to_string())

    def test_cache_key_includes_slice_hash(self):
        """Cache key should include slice hash when provided."""
        key_1 = CacheKey.compute(
            graph_data="graph",
            pcp_version="v2.0",
            budget_policy=BudgetPolicy.default(),
            slice_data=None,
        )

        key_2 = CacheKey.compute(
            graph_data="graph",
            pcp_version="v2.0",
            budget_policy=BudgetPolicy.default(),
            slice_data="slice-1",
        )

        # Without slice, no slice hash
        self.assertEqual(key_1.slice_hash, "")

        # With slice, has slice hash
        self.assertNotEqual(key_2.slice_hash, "")

    def test_cache_key_serialization(self):
        """Cache key should serialize and deserialize correctly."""
        key = CacheKey(
            graph_hash="abc123def456",
            pcp_version="v2.0",
            budget_policy_hash="xyz789",
            slice_hash="slice001",
        )

        data = key.to_dict()
        restored = CacheKey.from_dict(data)

        self.assertEqual(key.graph_hash, restored.graph_hash)
        self.assertEqual(key.pcp_version, restored.pcp_version)
        self.assertEqual(key.budget_policy_hash, restored.budget_policy_hash)
        self.assertEqual(key.slice_hash, restored.slice_hash)


class TestAdaptiveBatching(unittest.TestCase):
    """Tests for adaptive batching by cost/complexity."""

    def test_adaptive_batching_groups_by_cost(self):
        """Adaptive batching should group patterns by cost."""
        batcher = AdaptiveBatcher(max_batch_tokens=3000, max_batch_size=5)

        # Create estimates with varying costs
        estimates = [
            PatternCostEstimate("pattern-1", 500, 1.0, 500, tier="A"),
            PatternCostEstimate("pattern-2", 500, 1.0, 500, tier="A"),
            PatternCostEstimate("pattern-3", 500, 2.5, 1250, tier="B"),
            PatternCostEstimate("pattern-4", 500, 2.5, 1250, tier="B"),
            PatternCostEstimate("pattern-5", 500, 3.5, 1750, tier="C"),
        ]

        batches = batcher.create_batches(estimates)

        # Should create multiple batches due to token limits
        self.assertGreater(len(batches), 1)

        # First batch should have Tier A patterns (cheaper, higher priority)
        first_batch_patterns = batches[0].patterns
        self.assertIn("pattern-1", first_batch_patterns)
        self.assertIn("pattern-2", first_batch_patterns)

    def test_adaptive_batching_respects_token_limit(self):
        """Batches should not exceed token limit."""
        batcher = AdaptiveBatcher(max_batch_tokens=2000, max_batch_size=10)

        # Each pattern costs 1000 tokens
        estimates = [
            PatternCostEstimate(f"pattern-{i}", 500, 2.0, 1000, tier="B")
            for i in range(5)
        ]

        batches = batcher.create_batches(estimates)

        # Each batch should have at most 2 patterns (2000 tokens max)
        for batch in batches:
            self.assertLessEqual(batch.total_estimated_tokens, 2000)
            self.assertLessEqual(len(batch.patterns), 2)

    def test_adaptive_batching_respects_size_limit(self):
        """Batches should not exceed max patterns."""
        batcher = AdaptiveBatcher(max_batch_tokens=100000, max_batch_size=3)

        estimates = [
            PatternCostEstimate(f"pattern-{i}", 100, 1.0, 100, tier="A")
            for i in range(10)
        ]

        batches = batcher.create_batches(estimates)

        # Each batch should have at most 3 patterns
        for batch in batches:
            self.assertLessEqual(len(batch.patterns), 3)

    def test_cost_estimation_by_tier(self):
        """Cost estimation should vary by tier."""
        batcher = AdaptiveBatcher()

        tier_a = batcher.estimate_pattern_cost("p1", tier="A", base_tokens=500)
        tier_b = batcher.estimate_pattern_cost("p2", tier="B", base_tokens=500)
        tier_c = batcher.estimate_pattern_cost("p3", tier="C", base_tokens=500)

        # Tier A should be cheapest
        self.assertLess(tier_a.estimated_tokens, tier_b.estimated_tokens)
        # Tier B should be cheaper than C
        self.assertLess(tier_b.estimated_tokens, tier_c.estimated_tokens)

    def test_cost_estimation_with_multipliers(self):
        """Cost estimation should apply multipliers."""
        batcher = AdaptiveBatcher()

        simple = batcher.estimate_pattern_cost("p1", tier="B", base_tokens=500)
        multi_hop = batcher.estimate_pattern_cost(
            "p2", tier="B", has_multi_hop=True, base_tokens=500
        )
        cross_contract = batcher.estimate_pattern_cost(
            "p3", tier="B", has_cross_contract=True, base_tokens=500
        )
        both = batcher.estimate_pattern_cost(
            "p4", tier="B", has_multi_hop=True, has_cross_contract=True, base_tokens=500
        )

        # Multi-hop should cost more than simple
        self.assertGreater(multi_hop.estimated_tokens, simple.estimated_tokens)
        # Cross-contract should cost more than simple
        self.assertGreater(cross_contract.estimated_tokens, simple.estimated_tokens)
        # Both should cost most
        self.assertGreater(both.estimated_tokens, multi_hop.estimated_tokens)
        self.assertGreater(both.estimated_tokens, cross_contract.estimated_tokens)

    def test_risk_weighting_affects_batch_order(self):
        """Risk weighting should affect batch priority/order."""
        batcher = AdaptiveBatcher(max_batch_tokens=10000, max_batch_size=2)

        # Same tier, different risk weights
        estimates = [
            PatternCostEstimate("low-risk", 500, 2.5, 1250, tier="B"),
            PatternCostEstimate("high-risk", 500, 2.5, 1250, tier="B"),
        ]

        # With high risk weight on one pattern
        risk_weights = {"high-risk": 0.95, "low-risk": 0.3}

        batches = batcher.create_batches(estimates, risk_weights)

        # High-risk should come first within same tier
        if batches:
            first_batch = batches[0]
            # High risk pattern should be in first position
            self.assertEqual(first_batch.patterns[0], "high-risk")


class TestForkThenRank(unittest.TestCase):
    """Tests for fork-then-rank orchestration."""

    def _create_fork_result(
        self,
        scout_id: str,
        status: ScoutStatus,
        confidence: float,
        evidence_count: int = 1,
    ) -> ForkResult:
        """Create a test fork result."""
        hypothesis = ScoutHypothesis(
            pattern_id="test-pattern",
            status=status,
            evidence_refs=[f"EVD-{i}" for i in range(evidence_count)],
            unknowns=[],  # Required field - empty list for tests
            confidence=confidence,
        )
        path = DiversityPath(
            path_type=DiversityPathType.OPERATION_FIRST,
            focus="semantic operations",
        )
        return ForkResult(
            scout_id=scout_id,
            diversity_path=path,
            hypothesis=hypothesis,
        )

    def test_fork_then_rank_majority_vote(self):
        """Fork-then-rank should select by majority vote."""
        ranker = ForkThenRank(ranking_method=RankingMethod.MAJORITY_VOTE)

        # 2 CANDIDATE, 1 NOT_MATCHED
        results = [
            self._create_fork_result("scout-1", ScoutStatus.CANDIDATE, 0.65),
            self._create_fork_result("scout-2", ScoutStatus.CANDIDATE, 0.60),
            self._create_fork_result("scout-3", ScoutStatus.NOT_MATCHED, 0.55),
        ]

        ranked = ranker.rank_results("test-pattern", results)

        # Winner should be CANDIDATE (majority)
        self.assertEqual(ranked.winner.status, ScoutStatus.CANDIDATE)
        self.assertEqual(ranked.vote_count, 2)
        self.assertEqual(ranked.total_scouts, 3)

    def test_fork_then_rank_confidence_weighted(self):
        """Fork-then-rank should weight by confidence."""
        ranker = ForkThenRank(ranking_method=RankingMethod.CONFIDENCE_WEIGHTED)

        results = [
            self._create_fork_result("scout-1", ScoutStatus.CANDIDATE, 0.70, evidence_count=3),
            self._create_fork_result("scout-2", ScoutStatus.CANDIDATE, 0.55, evidence_count=1),
            self._create_fork_result("scout-3", ScoutStatus.NOT_MATCHED, 0.40, evidence_count=1),
        ]

        ranked = ranker.rank_results("test-pattern", results)

        # Winner should be scout-1 (highest confidence + evidence)
        self.assertEqual(ranked.winner.confidence, 0.70)

    def test_fork_then_rank_deterministic(self):
        """Fork-then-rank should produce deterministic results."""
        ranker = ForkThenRank(ranking_method=RankingMethod.HYBRID)

        results = [
            self._create_fork_result("scout-1", ScoutStatus.CANDIDATE, 0.60),
            self._create_fork_result("scout-2", ScoutStatus.CANDIDATE, 0.70),
            self._create_fork_result("scout-3", ScoutStatus.CANDIDATE, 0.55),
        ]

        # Run multiple times
        outcomes = []
        for _ in range(5):
            ranked = ranker.rank_results("test-pattern", results)
            outcomes.append(ranked.winner.confidence)

        # All outcomes should be identical
        self.assertEqual(len(set(outcomes)), 1)

    def test_fork_then_rank_contradiction_veto(self):
        """Contradiction can veto if confidence > threshold."""
        ranker = ForkThenRank(veto_threshold=0.7)

        results = [
            self._create_fork_result("scout-1", ScoutStatus.CANDIDATE, 0.65),
            self._create_fork_result("scout-2", ScoutStatus.CANDIDATE, 0.60),
        ]

        # Contradiction with high confidence (above veto threshold of 0.7)
        contradiction = ContradictionReport(
            finding_id="FND-001",
            status=ContradictionStatus.REFUTED,
            counterarguments=[],  # Empty counterarguments for test
            confidence=0.85,  # ContradictionReport can have higher confidence
        )

        ranked = ranker.rank_results("test-pattern", results, contradiction)

        self.assertTrue(ranked.vetoed)
        self.assertIn("0.85", ranked.veto_reason)

    def test_fork_then_rank_no_veto_low_confidence(self):
        """Contradiction should not veto if confidence < threshold."""
        ranker = ForkThenRank(veto_threshold=0.7)

        results = [
            self._create_fork_result("scout-1", ScoutStatus.CANDIDATE, 0.65),
        ]

        # Contradiction with low confidence
        contradiction = ContradictionReport(
            finding_id="FND-002",
            status=ContradictionStatus.REFUTED,
            counterarguments=[],  # Empty counterarguments for test
            confidence=0.5,
        )

        ranked = ranker.rank_results("test-pattern", results, contradiction)

        self.assertFalse(ranked.vetoed)

    def test_fork_then_rank_empty_results(self):
        """Should handle empty results gracefully."""
        ranker = ForkThenRank()

        ranked = ranker.rank_results("test-pattern", [])

        self.assertEqual(ranked.winner.status, ScoutStatus.UNKNOWN)
        self.assertEqual(ranked.vote_count, 0)
        self.assertEqual(ranked.total_scouts, 0)


class TestBatchManifest(unittest.TestCase):
    """Tests for BatchManifest structure."""

    def test_manifest_contains_required_fields(self):
        """Manifest should contain all required fields."""
        cache_key = CacheKey(
            graph_hash="abc123",
            pcp_version="v2.0",
            budget_policy_hash="def456",
        )

        batches = [
            AdaptiveBatch(
                batch_id="batch-001",
                priority=BatchPriority.HIGH,
                patterns=["pattern-1", "pattern-2"],
                cost_estimates=[
                    PatternCostEstimate("pattern-1", 500, 1.0, 500),
                    PatternCostEstimate("pattern-2", 500, 1.0, 500),
                ],
            )
        ]

        manifest = BatchManifest(
            manifest_id="manifest-001",
            cache_key=cache_key,
            batches=batches,
            evidence_ids=["EVD-001", "EVD-002"],
            slice_hashes=["hash-001", "hash-002"],
            protocol_context_included=True,
        )

        # Check required fields per plan
        data = manifest.to_dict()

        self.assertIn("cache_key", data)
        self.assertIn("evidence_ids", data)
        self.assertIn("slice_hashes", data)
        self.assertIn("protocol_context_included", data)
        self.assertIn("batches", data)

        # Cache key should have all components
        self.assertIn("graph_hash", data["cache_key"])
        self.assertIn("pcp_version", data["cache_key"])
        self.assertIn("budget_policy_hash", data["cache_key"])

    def test_manifest_protocol_context_flag(self):
        """Manifest should track protocol context inclusion."""
        cache_key = CacheKey("hash", "v2.0", "budget")

        manifest_with = BatchManifest(
            manifest_id="m1",
            cache_key=cache_key,
            batches=[],
            evidence_ids=[],
            slice_hashes=[],
            protocol_context_included=True,
        )

        manifest_without = BatchManifest(
            manifest_id="m2",
            cache_key=cache_key,
            batches=[],
            evidence_ids=[],
            slice_hashes=[],
            protocol_context_included=False,
        )

        self.assertTrue(manifest_with.protocol_context_included)
        self.assertFalse(manifest_without.protocol_context_included)

    def test_manifest_serialization(self):
        """Manifest should serialize to JSON-compatible dict."""
        cache_key = CacheKey("abc", "v2.0", "def")
        budget = BudgetPolicy.default()
        diversity = DiversityPolicy.default()

        manifest = BatchManifest(
            manifest_id="test-manifest",
            cache_key=cache_key,
            batches=[],
            evidence_ids=["EVD-001"],
            slice_hashes=["slice-001"],
            protocol_context_included=True,
            budget_policy=budget,
            diversity_policy=diversity,
            metadata={"source": "test"},
        )

        data = manifest.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(data, default=str)
        self.assertIsInstance(json_str, str)

        # Should contain all fields
        parsed = json.loads(json_str)
        self.assertEqual(parsed["manifest_id"], "test-manifest")
        self.assertEqual(parsed["evidence_ids"], ["EVD-001"])
        self.assertTrue(parsed["protocol_context_included"])


class TestBatchDiscoveryOrchestrator(unittest.TestCase):
    """Integration tests for BatchDiscoveryOrchestrator."""

    def test_orchestrator_creates_adaptive_batches(self):
        """Orchestrator should create adaptive batches from estimates."""
        orchestrator = BatchDiscoveryOrchestrator()

        estimates = [
            orchestrator.estimate_pattern_cost("p1", tier="A"),
            orchestrator.estimate_pattern_cost("p2", tier="B"),
            orchestrator.estimate_pattern_cost("p3", tier="C"),
        ]

        batches = orchestrator.create_adaptive_batches(estimates)

        self.assertGreater(len(batches), 0)
        self.assertIsInstance(batches[0], AdaptiveBatch)

    def test_orchestrator_creates_manifest(self):
        """Orchestrator should create complete manifest."""
        orchestrator = BatchDiscoveryOrchestrator()

        estimates = [
            orchestrator.estimate_pattern_cost("p1", tier="B"),
        ]
        batches = orchestrator.create_adaptive_batches(estimates)

        manifest = orchestrator.create_manifest(
            graph_data='{"test": true}',
            pcp_version="v2.0",
            batches=batches,
            evidence_ids=["EVD-001"],
            protocol_context_included=True,
        )

        self.assertIsInstance(manifest, BatchManifest)
        self.assertIn("EVD-001", manifest.evidence_ids)
        self.assertTrue(manifest.protocol_context_included)

    def test_orchestrator_caching(self):
        """Orchestrator should support caching."""
        orchestrator = BatchDiscoveryOrchestrator()

        key = orchestrator.compute_cache_key('{"test": true}', "v2.0")

        # Initially no cache
        self.assertIsNone(orchestrator.get_cached(key))

        # Set cache
        orchestrator.set_cached(key, {"result": "test"})

        # Retrieve cache
        cached = orchestrator.get_cached(key)
        self.assertEqual(cached, {"result": "test"})

        # Clear cache
        orchestrator.clear_cache()
        self.assertIsNone(orchestrator.get_cached(key))

    def test_orchestrator_fork_then_rank(self):
        """Orchestrator should run fork-then-rank."""
        orchestrator = BatchDiscoveryOrchestrator(ranking_method=RankingMethod.HYBRID)

        hypothesis = ScoutHypothesis(
            pattern_id="test",
            status=ScoutStatus.CANDIDATE,
            evidence_refs=["EVD-001"],
            unknowns=[],  # Required field
            confidence=0.65,
        )
        path = DiversityPath(path_type=DiversityPathType.OPERATION_FIRST, focus="semantic operations")

        results = [ForkResult("scout-1", path, hypothesis)]

        ranked = orchestrator.fork_then_rank("test-pattern", results)

        self.assertEqual(ranked.winner.status, ScoutStatus.CANDIDATE)
        self.assertEqual(len(orchestrator.get_results()), 1)


class TestDefaultCostWeights(unittest.TestCase):
    """Tests for default cost weights."""

    def test_default_weights_exist(self):
        """Default cost weights should be defined."""
        self.assertIn("tier_a", DEFAULT_COST_WEIGHTS)
        self.assertIn("tier_b", DEFAULT_COST_WEIGHTS)
        self.assertIn("tier_c", DEFAULT_COST_WEIGHTS)
        self.assertIn("multi_hop", DEFAULT_COST_WEIGHTS)
        self.assertIn("cross_contract", DEFAULT_COST_WEIGHTS)

    def test_tier_a_cheapest(self):
        """Tier A should have lowest cost multiplier."""
        self.assertLess(
            DEFAULT_COST_WEIGHTS["tier_a"],
            DEFAULT_COST_WEIGHTS["tier_b"],
        )
        self.assertLess(
            DEFAULT_COST_WEIGHTS["tier_b"],
            DEFAULT_COST_WEIGHTS["tier_c"],
        )


if __name__ == "__main__":
    unittest.main()
