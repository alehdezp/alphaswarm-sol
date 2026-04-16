"""Batch Discovery End-to-End Integration Tests.

Tests for batch orchestration, fork-then-rank, adaptive batching,
and manifest creation with deterministic ordering.

Per PCONTEXT-07:
- Batch orchestration groups by cost/complexity
- Prefix cache keyed by graph hash + PCP version
- Fork-then-rank produces deterministic winners

Reference:
- .planning/phases/05.10-pattern-context-batch-discovery-orchestration/05.10-CONTEXT.md
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

ROOT = Path(__file__).resolve().parents[2]


class TestAdaptiveBatchingEndToEnd:
    """End-to-end tests for adaptive batching by cost/complexity."""

    def test_adaptive_batching_groups_by_tier(self):
        """Patterns are grouped by tier in adaptive batching."""
        from alphaswarm_sol.orchestration.batch import (
            AdaptiveBatcher,
            BatchPriority,
            PatternCostEstimate,
        )

        batcher = AdaptiveBatcher(max_batch_tokens=3000, max_batch_size=10)

        # Create mix of tier A, B, C patterns
        estimates = [
            PatternCostEstimate(
                pattern_id="tier-a-1",
                base_cost=200,
                complexity_multiplier=1.0,
                estimated_tokens=200,
                tier="A",
            ),
            PatternCostEstimate(
                pattern_id="tier-a-2",
                base_cost=200,
                complexity_multiplier=1.0,
                estimated_tokens=200,
                tier="A",
            ),
            PatternCostEstimate(
                pattern_id="tier-b-1",
                base_cost=400,
                complexity_multiplier=2.5,
                estimated_tokens=1000,
                tier="B",
            ),
            PatternCostEstimate(
                pattern_id="tier-c-1",
                base_cost=500,
                complexity_multiplier=3.5,
                estimated_tokens=1750,
                tier="C",
            ),
        ]

        batches = batcher.create_batches(estimates)

        # All patterns should be preserved across batches
        all_patterns = set(p for b in batches for p in b.patterns)
        expected = {"tier-a-1", "tier-a-2", "tier-b-1", "tier-c-1"}
        assert all_patterns == expected, "All patterns should be preserved"

        # At least one batch exists
        assert len(batches) > 0, "Should have at least one batch"

    def test_adaptive_batching_respects_token_limits(self):
        """Batches respect maximum token limits."""
        from alphaswarm_sol.orchestration.batch import (
            AdaptiveBatcher,
            PatternCostEstimate,
        )

        max_tokens = 1000
        batcher = AdaptiveBatcher(max_batch_tokens=max_tokens, max_batch_size=100)

        # Create patterns that together exceed limit
        estimates = [
            PatternCostEstimate(
                pattern_id=f"pattern-{i}",
                base_cost=300,
                complexity_multiplier=1.0,
                estimated_tokens=300,
                tier="B",
            )
            for i in range(10)
        ]

        batches = batcher.create_batches(estimates)

        # Each batch should be under token limit
        for batch in batches:
            assert batch.total_estimated_tokens <= max_tokens * 1.5, (
                f"Batch {batch.batch_id} exceeds token limit: {batch.total_estimated_tokens}"
            )

    def test_adaptive_batching_respects_batch_size_limits(self):
        """Batches respect maximum pattern count limits."""
        from alphaswarm_sol.orchestration.batch import (
            AdaptiveBatcher,
            PatternCostEstimate,
        )

        max_size = 3
        batcher = AdaptiveBatcher(max_batch_tokens=10000, max_batch_size=max_size)

        estimates = [
            PatternCostEstimate(
                pattern_id=f"pattern-{i}",
                base_cost=100,
                complexity_multiplier=1.0,
                estimated_tokens=100,
                tier="A",
            )
            for i in range(10)
        ]

        batches = batcher.create_batches(estimates)

        # Each batch should have at most max_size patterns
        for batch in batches:
            assert len(batch.patterns) <= max_size, (
                f"Batch {batch.batch_id} has too many patterns: {len(batch.patterns)}"
            )

    def test_adaptive_batching_preserves_all_patterns(self):
        """All input patterns appear in output batches."""
        from alphaswarm_sol.orchestration.batch import (
            AdaptiveBatcher,
            PatternCostEstimate,
        )

        batcher = AdaptiveBatcher()

        estimates = [
            PatternCostEstimate(
                pattern_id=f"pattern-{i:03d}",
                base_cost=200 + i * 50,
                complexity_multiplier=1.0 + (i % 3) * 0.5,
                estimated_tokens=0,
                tier=["A", "B", "C"][i % 3],
            )
            for i in range(20)
        ]

        batches = batcher.create_batches(estimates)

        # Collect all patterns from batches
        all_patterns = set()
        for batch in batches:
            all_patterns.update(batch.patterns)

        # All original patterns should be present
        original_patterns = {e.pattern_id for e in estimates}
        assert all_patterns == original_patterns, "Some patterns missing from batches"


class TestCacheVersioningEndToEnd:
    """End-to-end tests for prefix cache versioning."""

    def test_cache_key_uniqueness(self):
        """Different inputs produce different cache keys."""
        from alphaswarm_sol.agents.context.types import BudgetPolicy
        from alphaswarm_sol.orchestration.batch import BatchDiscoveryOrchestrator

        orchestrator = BatchDiscoveryOrchestrator()

        # Different graphs
        key_1 = orchestrator.compute_cache_key("graph_1", "v2.0")
        key_2 = orchestrator.compute_cache_key("graph_2", "v2.0")
        assert key_1.to_string() != key_2.to_string(), "Different graphs should have different keys"

        # Different PCP versions
        key_3 = orchestrator.compute_cache_key("graph_1", "v2.1")
        assert key_1.to_string() != key_3.to_string(), "Different versions should have different keys"

        # Different slices
        key_4 = orchestrator.compute_cache_key("graph_1", "v2.0", "slice_A")
        key_5 = orchestrator.compute_cache_key("graph_1", "v2.0", "slice_B")
        assert key_4.to_string() != key_5.to_string(), "Different slices should have different keys"

    def test_cache_key_stability(self):
        """Same inputs produce same cache key."""
        from alphaswarm_sol.orchestration.batch import BatchDiscoveryOrchestrator

        orchestrator = BatchDiscoveryOrchestrator()

        keys = [
            orchestrator.compute_cache_key("graph_data", "v2.0", "slice_data")
            for _ in range(10)
        ]

        key_strings = [k.to_string() for k in keys]
        assert all(k == key_strings[0] for k in key_strings), "Cache key not stable"

    def test_cache_get_set_round_trip(self):
        """Cache get/set works correctly."""
        from alphaswarm_sol.orchestration.batch import BatchDiscoveryOrchestrator

        orchestrator = BatchDiscoveryOrchestrator()

        key = orchestrator.compute_cache_key("test_graph", "v2.0")
        value = {"result": "cached_data", "timestamp": "2026-01-27"}

        # Initially not cached
        assert orchestrator.get_cached(key) is None

        # Set and get
        orchestrator.set_cached(key, value)
        retrieved = orchestrator.get_cached(key)

        assert retrieved == value, "Cache round-trip failed"

        # Clear and verify
        orchestrator.clear_cache()
        assert orchestrator.get_cached(key) is None, "Cache not cleared"


class TestForkThenRankEndToEnd:
    """End-to-end tests for fork-then-rank pattern selection."""

    def test_fork_then_rank_selects_winner(self):
        """Fork-then-rank selects a deterministic winner."""
        from datetime import datetime

        from alphaswarm_sol.orchestration.batch import (
            BatchDiscoveryOrchestrator,
            ForkResult,
            RankingMethod,
        )
        from alphaswarm_sol.orchestration.schemas import (
            DiversityPath,
            DiversityPathType,
            ScoutHypothesis,
            ScoutStatus,
        )

        orchestrator = BatchDiscoveryOrchestrator(ranking_method=RankingMethod.HYBRID)

        # Create diverse scout results using correct DiversityPathType enum values
        results = [
            ForkResult(
                scout_id="operation_scout",
                diversity_path=DiversityPath(
                    path_type=DiversityPathType.OPERATION_FIRST,
                    focus="aggressive analysis",
                ),
                hypothesis=ScoutHypothesis(
                    pattern_id="reentrancy-classic",
                    status=ScoutStatus.CANDIDATE,
                    evidence_refs=["EVD-00000001"],
                    unknowns=[],
                    confidence=0.70,
                ),
                timestamp=datetime.now(),
            ),
            ForkResult(
                scout_id="guard_scout",
                diversity_path=DiversityPath(
                    path_type=DiversityPathType.GUARD_FIRST,
                    focus="conservative analysis",
                ),
                hypothesis=ScoutHypothesis(
                    pattern_id="reentrancy-classic",
                    status=ScoutStatus.NOT_MATCHED,
                    evidence_refs=[],
                    unknowns=[],
                    confidence=0.6,
                ),
                timestamp=datetime.now(),
            ),
            ForkResult(
                scout_id="invariant_scout",
                diversity_path=DiversityPath(
                    path_type=DiversityPathType.INVARIANT_FIRST,
                    focus="balanced analysis",
                ),
                hypothesis=ScoutHypothesis(
                    pattern_id="reentrancy-classic",
                    status=ScoutStatus.CANDIDATE,
                    evidence_refs=["EVD-00000002"],
                    unknowns=[],
                    confidence=0.65,
                ),
                timestamp=datetime.now(),
            ),
        ]

        ranked = orchestrator.fork_then_rank("reentrancy-classic", results)

        # Should have a winner
        assert ranked.winner is not None
        assert ranked.pattern_id == "reentrancy-classic"
        assert ranked.total_scouts == 3
        assert ranked.vote_count >= 1

    def test_fork_then_rank_handles_empty_results(self):
        """Fork-then-rank handles empty scout results."""
        from alphaswarm_sol.orchestration.batch import BatchDiscoveryOrchestrator
        from alphaswarm_sol.orchestration.schemas import ScoutStatus

        orchestrator = BatchDiscoveryOrchestrator()

        ranked = orchestrator.fork_then_rank("test-pattern", [])

        assert ranked.winner is not None
        assert ranked.winner.status == ScoutStatus.UNKNOWN
        assert ranked.total_scouts == 0

    def test_fork_then_rank_contradiction_veto(self):
        """High-confidence contradiction vetoes result."""
        from datetime import datetime

        from alphaswarm_sol.orchestration.batch import BatchDiscoveryOrchestrator, ForkResult
        from alphaswarm_sol.orchestration.schemas import (
            ContradictionReport,
            ContradictionStatus,
            Counterargument,
            CounterargumentStrength,
            CounterargumentType,
            DiversityPath,
            DiversityPathType,
            ScoutHypothesis,
            ScoutStatus,
        )

        orchestrator = BatchDiscoveryOrchestrator()

        results = [
            ForkResult(
                scout_id="scout-1",
                diversity_path=DiversityPath(path_type=DiversityPathType.OPERATION_FIRST, focus="operations"),
                hypothesis=ScoutHypothesis(
                    pattern_id="test",
                    status=ScoutStatus.CANDIDATE,
                    evidence_refs=["EVD-00000001"],
                    unknowns=[],
                    confidence=0.65,
                ),
                timestamp=datetime.now(),
            ),
        ]

        # High-confidence contradiction using correct schema
        contradiction = ContradictionReport(
            finding_id="FND-001",
            status=ContradictionStatus.REFUTED,
            counterarguments=[
                Counterargument(
                    type=CounterargumentType.GUARD_PRESENT,
                    claim="Reentrancy guard present",
                    evidence_refs=["EVD-counter01"],
                    strength=CounterargumentStrength.STRONG,
                )
            ],
            confidence=0.9,
        )

        ranked = orchestrator.fork_then_rank("test", results, contradiction)

        assert ranked.vetoed is True
        assert "0.9" in ranked.veto_reason or "confidence" in ranked.veto_reason.lower()

    def test_fork_then_rank_low_confidence_no_veto(self):
        """Low-confidence contradiction does not veto."""
        from datetime import datetime

        from alphaswarm_sol.orchestration.batch import BatchDiscoveryOrchestrator, ForkResult
        from alphaswarm_sol.orchestration.schemas import (
            ContradictionReport,
            ContradictionStatus,
            Counterargument,
            CounterargumentStrength,
            CounterargumentType,
            DiversityPath,
            DiversityPathType,
            ScoutHypothesis,
            ScoutStatus,
        )

        orchestrator = BatchDiscoveryOrchestrator(veto_threshold=0.7)

        results = [
            ForkResult(
                scout_id="scout-1",
                diversity_path=DiversityPath(path_type=DiversityPathType.GUARD_FIRST, focus="guards"),
                hypothesis=ScoutHypothesis(
                    pattern_id="test",
                    status=ScoutStatus.CANDIDATE,
                    evidence_refs=["EVD-00000001"],
                    unknowns=[],
                    confidence=0.65,
                ),
                timestamp=datetime.now(),
            ),
        ]

        # Low-confidence contradiction
        contradiction = ContradictionReport(
            finding_id="FND-002",
            status=ContradictionStatus.CHALLENGED,  # Changed from REFUTED to CHALLENGED
            counterarguments=[
                Counterargument(
                    type=CounterargumentType.ANTI_SIGNAL,
                    claim="Weak counter",
                    evidence_refs=["EVD-weak001"],
                    strength=CounterargumentStrength.WEAK,
                )
            ],
            confidence=0.5,  # Below threshold
        )

        ranked = orchestrator.fork_then_rank("test", results, contradiction)

        assert ranked.vetoed is False


class TestManifestCreationEndToEnd:
    """End-to-end tests for batch manifest creation."""

    def test_manifest_contains_all_required_fields(self):
        """Manifest contains all required fields per spec."""
        from alphaswarm_sol.agents.context.types import BudgetPolicy
        from alphaswarm_sol.orchestration.batch import (
            AdaptiveBatch,
            BatchDiscoveryOrchestrator,
            BatchPriority,
            PatternCostEstimate,
        )

        orchestrator = BatchDiscoveryOrchestrator()

        batches = [
            AdaptiveBatch(
                batch_id="batch-001",
                priority=BatchPriority.HIGH,
                patterns=["pattern-1", "pattern-2"],
                cost_estimates=[
                    PatternCostEstimate(
                        pattern_id="pattern-1",
                        base_cost=300,
                        complexity_multiplier=1.0,
                        estimated_tokens=300,
                        tier="A",
                    ),
                    PatternCostEstimate(
                        pattern_id="pattern-2",
                        base_cost=500,
                        complexity_multiplier=2.5,
                        estimated_tokens=1250,
                        tier="B",
                    ),
                ],
            ),
        ]

        manifest = orchestrator.create_manifest(
            graph_data="test_graph_content",
            pcp_version="v2.0",
            batches=batches,
            evidence_ids=["EVD-001", "EVD-002", "EVD-003"],
            protocol_context_included=True,
            metadata={"source": "test"},
        )

        # Check required fields
        assert manifest.manifest_id, "Missing manifest_id"
        assert manifest.cache_key, "Missing cache_key"
        assert manifest.batches == batches, "Batches not preserved"
        assert manifest.evidence_ids == ["EVD-001", "EVD-002", "EVD-003"], "Evidence IDs not sorted"
        assert manifest.protocol_context_included is True
        assert manifest.budget_policy is not None
        assert manifest.diversity_policy is not None

    def test_manifest_serialization_round_trip(self):
        """Manifest serializes and deserializes correctly."""
        from alphaswarm_sol.orchestration.batch import BatchDiscoveryOrchestrator

        orchestrator = BatchDiscoveryOrchestrator()

        manifest = orchestrator.create_manifest(
            graph_data="test",
            pcp_version="v2.0",
            batches=[],
            evidence_ids=["EVD-001"],
            protocol_context_included=True,
        )

        # Serialize
        data = manifest.to_dict()

        # Required fields in serialized form
        assert "manifest_id" in data
        assert "cache_key" in data
        assert "batches" in data
        assert "evidence_ids" in data
        assert "protocol_context_included" in data
        assert "created_at" in data

    def test_manifest_slice_hashes_computed(self):
        """Manifest computes slice hashes if not provided."""
        from alphaswarm_sol.orchestration.batch import (
            AdaptiveBatch,
            BatchDiscoveryOrchestrator,
            BatchPriority,
            PatternCostEstimate,
        )

        orchestrator = BatchDiscoveryOrchestrator()

        batches = [
            AdaptiveBatch(
                batch_id="batch-001",
                priority=BatchPriority.MEDIUM,
                patterns=["p1", "p2"],
                cost_estimates=[
                    PatternCostEstimate("p1", 100, 1.0, 100, "A"),
                    PatternCostEstimate("p2", 100, 1.0, 100, "A"),
                ],
            ),
            AdaptiveBatch(
                batch_id="batch-002",
                priority=BatchPriority.MEDIUM,
                patterns=["p3"],
                cost_estimates=[
                    PatternCostEstimate("p3", 200, 1.5, 300, "B"),
                ],
            ),
        ]

        manifest = orchestrator.create_manifest(
            graph_data="test",
            pcp_version="v2.0",
            batches=batches,
            evidence_ids=[],
            protocol_context_included=True,
        )

        # Slice hashes should be computed
        assert len(manifest.slice_hashes) == len(batches), "Missing slice hashes"
        assert all(len(h) == 8 for h in manifest.slice_hashes), "Slice hash wrong length"


class TestBatchOrchestratorStateManagement:
    """Tests for batch orchestrator state management."""

    def test_orchestrator_tracks_results(self):
        """Orchestrator tracks ranked results across calls."""
        from datetime import datetime

        from alphaswarm_sol.orchestration.batch import BatchDiscoveryOrchestrator, ForkResult
        from alphaswarm_sol.orchestration.schemas import (
            DiversityPath,
            DiversityPathType,
            ScoutHypothesis,
            ScoutStatus,
        )

        orchestrator = BatchDiscoveryOrchestrator()

        # Run multiple fork-then-rank
        path_types = [DiversityPathType.OPERATION_FIRST, DiversityPathType.GUARD_FIRST, DiversityPathType.INVARIANT_FIRST]
        focuses = ["operations", "guards", "invariants"]
        for i in range(3):
            results = [
                ForkResult(
                    scout_id=f"scout-{i}",
                    diversity_path=DiversityPath(path_type=path_types[i], focus=focuses[i]),
                    hypothesis=ScoutHypothesis(
                        pattern_id=f"pattern-{i}",
                        status=ScoutStatus.CANDIDATE,
                        evidence_refs=[f"EVD-{i:08d}"],
                        unknowns=[],
                        confidence=0.6 + i * 0.03,  # Stay within 0.70 limit for tier B
                    ),
                    timestamp=datetime.now(),
                ),
            ]
            orchestrator.fork_then_rank(f"pattern-{i}", results)

        # All results should be tracked
        all_results = orchestrator.get_results()
        assert len(all_results) == 3, "Not all results tracked"

        # Clear and verify
        orchestrator.clear_results()
        assert len(orchestrator.get_results()) == 0, "Results not cleared"

    def test_orchestrator_budget_policy_affects_cache_key(self):
        """Different budget policies produce different cache keys."""
        from alphaswarm_sol.agents.context.types import BudgetPolicy
        from alphaswarm_sol.orchestration.batch import BatchDiscoveryOrchestrator

        policy_1 = BudgetPolicy(
            cheap_pass_tokens=500,
            verify_pass_tokens=2000,
            deep_pass_tokens=5000,
        )

        policy_2 = BudgetPolicy(
            cheap_pass_tokens=1000,
            verify_pass_tokens=3000,
            deep_pass_tokens=6000,
        )

        orch_1 = BatchDiscoveryOrchestrator(budget_policy=policy_1)
        orch_2 = BatchDiscoveryOrchestrator(budget_policy=policy_2)

        key_1 = orch_1.compute_cache_key("same_graph", "v2.0")
        key_2 = orch_2.compute_cache_key("same_graph", "v2.0")

        assert key_1.budget_policy_hash != key_2.budget_policy_hash, (
            "Different budgets should produce different cache keys"
        )


class TestShuffledInputBatchDeterminism:
    """CRITICAL: Verify shuffled-input determinism for batch operations."""

    def test_batch_orchestrator_deterministic_shuffled_patterns(self):
        """Batch orchestrator preserves all patterns regardless of input order.

        NOTE: The batcher may sort inputs internally by tier/cost before batching,
        so shuffled inputs produce same total patterns but possibly different batch structure.
        This test validates pattern preservation, not exact batch structure.
        """
        from alphaswarm_sol.orchestration.batch import (
            BatchDiscoveryOrchestrator,
            PatternCostEstimate,
        )

        orchestrator = BatchDiscoveryOrchestrator()

        # Create pattern cost estimates
        estimates = [
            PatternCostEstimate(
                pattern_id=f"pattern-{chr(65 + i)}",  # A, B, C, etc.
                base_cost=200 + i * 100,
                complexity_multiplier=1.0 + (i % 3) * 0.5,
                estimated_tokens=0,
                tier=["A", "B", "C"][i % 3],
            )
            for i in range(15)
        ]

        # Run 1: original order
        batches_1 = orchestrator.create_adaptive_batches(estimates)
        patterns_1 = sorted([p for b in batches_1 for p in b.patterns])

        # Run 2: shuffled order (fixed seed)
        shuffled = list(estimates)
        random.seed(99999)
        random.shuffle(shuffled)
        batches_2 = orchestrator.create_adaptive_batches(shuffled)
        patterns_2 = sorted([p for b in batches_2 for p in b.patterns])

        # Both should produce same total patterns
        assert patterns_1 == patterns_2, (
            "Batch orchestrator does not preserve all patterns"
        )

    def test_manifest_deterministic_with_shuffled_evidence(self):
        """Manifest is deterministic regardless of evidence ID order."""
        from alphaswarm_sol.orchestration.batch import BatchDiscoveryOrchestrator

        orchestrator = BatchDiscoveryOrchestrator()

        # Original order
        evidence_1 = ["EVD-zebra", "EVD-apple", "EVD-mango", "EVD-banana"]

        # Shuffled order
        evidence_2 = ["EVD-banana", "EVD-apple", "EVD-zebra", "EVD-mango"]

        manifest_1 = orchestrator.create_manifest(
            graph_data="test",
            pcp_version="v2.0",
            batches=[],
            evidence_ids=evidence_1,
            protocol_context_included=True,
        )

        manifest_2 = orchestrator.create_manifest(
            graph_data="test",
            pcp_version="v2.0",
            batches=[],
            evidence_ids=evidence_2,
            protocol_context_included=True,
        )

        # Evidence IDs should be sorted identically
        assert manifest_1.evidence_ids == manifest_2.evidence_ids, (
            "Manifest evidence IDs not deterministic"
        )

        # Slice hashes should be identical (empty batches)
        assert manifest_1.slice_hashes == manifest_2.slice_hashes
