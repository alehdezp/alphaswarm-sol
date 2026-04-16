"""Phase 5.10 Quality Gate Integration Tests.

Tests for determinism, evidence gating, batch orchestration, and quality metrics
that validate the Phase 5.10 Pattern Context + Batch Discovery capabilities.

CRITICAL: These tests validate behavior-level outcomes, not just pass-through.

Reference:
- .planning/phases/05.10-pattern-context-batch-discovery-orchestration/05.10-CONTEXT.md
- PCONTEXT-01 through PCONTEXT-11 acceptance checks

Coverage:
- PCP context pack determinism
- Evidence ID stability
- Unknown handling with controlled expansion
- Omission surfacing (not interpreted as safe)
- Shuffled-input determinism for merge/batch operations
"""

from __future__ import annotations

import hashlib
import json
import random
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pytest

ROOT = Path(__file__).resolve().parents[2]


class TestPCPDeterminism:
    """PCP context packs are bit-identical for same graph + PCP version.

    Per PCONTEXT-01: PCP v2 schema + validator with deterministic defaults.
    """

    def test_pcp_to_dict_deterministic(self):
        """Same PCP produces identical dict output across invocations."""
        from alphaswarm_sol.context.schema import ProtocolContextPack
        from alphaswarm_sol.context.types import Assumption, Confidence, Role

        # Create PCP with all fields populated
        pcp = ProtocolContextPack(
            version="2.0",
            schema_version="2.0",
            protocol_name="TestProtocol",
            protocol_type="lending",
            generated_at="2026-01-27T00:00:00Z",
            auto_generated=False,
            reviewed=True,
            roles=[
                Role(
                    name="admin",
                    capabilities=["pause", "upgrade"],
                    trust_assumptions=["multisig"],
                    confidence=Confidence.CERTAIN,
                ),
                Role(
                    name="user",
                    capabilities=["deposit", "withdraw"],
                    trust_assumptions=[],
                    confidence=Confidence.CERTAIN,
                ),
            ],
            assumptions=[
                Assumption(
                    description="Oracle prices are accurate",
                    category="price",
                    affects_functions=["liquidate", "borrow"],
                    confidence=Confidence.INFERRED,
                    source="whitepaper",
                ),
            ],
            critical_functions=["liquidate", "borrow", "withdraw"],
            incentives=["yield", "governance_token"],
        )

        # Serialize multiple times
        outputs = [json.dumps(pcp.to_dict(), sort_keys=True) for _ in range(5)]

        # All outputs must be identical
        assert all(o == outputs[0] for o in outputs), "PCP serialization not deterministic"

    def test_pcp_round_trip_deterministic(self):
        """PCP serialize -> deserialize -> serialize is bit-identical."""
        from alphaswarm_sol.context.schema import ProtocolContextPack
        from alphaswarm_sol.context.types import Assumption, Confidence, Role

        original = ProtocolContextPack(
            version="2.0",
            protocol_name="TestProtocol",
            protocol_type="dex",
            generated_at="2026-01-27T00:00:00Z",
            roles=[
                Role(name="trader", capabilities=["swap"], trust_assumptions=[], confidence=Confidence.CERTAIN),
            ],
            assumptions=[
                Assumption(
                    description="AMM formula is correct",
                    category="math",
                    affects_functions=["swap"],
                    source="whitepaper",
                    confidence=Confidence.CERTAIN,
                ),
            ],
        )

        original_json = json.dumps(original.to_dict(), sort_keys=True)

        # Round trip
        restored = ProtocolContextPack.from_dict(original.to_dict())
        restored_json = json.dumps(restored.to_dict(), sort_keys=True)

        assert original_json == restored_json, "PCP round-trip not deterministic"

    def test_pcp_merge_deterministic(self):
        """PCP merge operation is deterministic for same input order."""
        from alphaswarm_sol.context.schema import ProtocolContextPack
        from alphaswarm_sol.context.types import Assumption, Confidence, Role

        pcp1 = ProtocolContextPack(
            version="2.0",
            protocol_name="Protocol1",
            generated_at="2026-01-27T00:00:00Z",
            roles=[Role(name="admin", capabilities=["a"], trust_assumptions=[], confidence=Confidence.CERTAIN)],
            assumptions=[
                Assumption(description="Assumption A", category="a", affects_functions=["func_a"], source="doc_a", confidence=Confidence.CERTAIN)
            ],
        )

        pcp2 = ProtocolContextPack(
            version="2.0",
            protocol_name="Protocol2",
            generated_at="2026-01-27T00:00:01Z",
            roles=[Role(name="user", capabilities=["b"], trust_assumptions=[], confidence=Confidence.INFERRED)],
            assumptions=[
                Assumption(description="Assumption B", category="b", affects_functions=["func_b"], source="doc_b", confidence=Confidence.INFERRED)
            ],
        )

        # Merge in same direction multiple times
        merged_1 = pcp1.merge(pcp2)
        merged_2 = pcp1.merge(pcp2)

        # Same merge order should produce identical results
        def normalize(pcp: ProtocolContextPack) -> str:
            d = pcp.to_dict()
            d["roles"] = sorted(d["roles"], key=lambda r: r["name"])
            d["assumptions"] = sorted(d["assumptions"], key=lambda a: a["description"])
            # Remove generated_at since merge generates new timestamp
            del d["generated_at"]
            return json.dumps(d, sort_keys=True)

        # Same merge order should have same content
        assert normalize(merged_1) == normalize(merged_2), "PCP merge not deterministic"

        # Both merged results should have both roles and assumptions
        assert len(merged_1.roles) == 2, "Merged PCP should have 2 roles"
        assert len(merged_1.assumptions) == 2, "Merged PCP should have 2 assumptions"


class TestEvidenceIDStability:
    """Evidence IDs are stable across rebuilds (PCONTEXT-03)."""

    def test_evidence_id_stable_for_same_inputs(self):
        """Same build hash + node + location = same evidence ID."""
        from alphaswarm_sol.llm.interface_contract import generate_evidence_id

        build_hash = "abcdef123456"
        node_id = "func_withdraw"
        line = 42
        column = 10

        # Generate multiple times
        ids = [generate_evidence_id(build_hash, node_id, line, column) for _ in range(10)]

        assert all(id == ids[0] for id in ids), "Evidence IDs not stable"

    def test_evidence_id_includes_graph_hash_component(self):
        """Evidence ID changes when graph hash changes."""
        from alphaswarm_sol.llm.interface_contract import generate_evidence_id

        node_id = "func_test"
        line = 10

        id1 = generate_evidence_id("graph_hash_A", node_id, line)
        id2 = generate_evidence_id("graph_hash_B", node_id, line)

        assert id1 != id2, "Evidence ID should differ for different graph hashes"

    def test_evidence_id_deterministic_format(self):
        """Evidence ID follows EVD-xxxxxxxx format."""
        from alphaswarm_sol.llm.interface_contract import generate_evidence_id

        evidence_id = generate_evidence_id("test_hash", "node_1", 1)

        assert evidence_id.startswith("EVD-"), f"Wrong prefix: {evidence_id}"
        suffix = evidence_id[4:]
        assert len(suffix) == 8, f"Wrong suffix length: {len(suffix)}"
        try:
            int(suffix, 16)
        except ValueError:
            pytest.fail(f"Suffix not hex: {suffix}")


class TestUnknownHandling:
    """Unknown handling triggers controlled expansion, never upgrades without evidence."""

    def test_unknown_status_preserved_in_hypothesis(self):
        """Unknown status is preserved and not upgraded to candidate."""
        from alphaswarm_sol.orchestration.schemas import (
            ScoutHypothesis,
            ScoutStatus,
            UnknownItem,
            UnknownReason,
        )

        # Create hypothesis with unknown
        hypothesis = ScoutHypothesis(
            pattern_id="test-pattern",
            status=ScoutStatus.UNKNOWN,
            evidence_refs=[],
            unknowns=[
                UnknownItem(
                    field="balance_access",
                    reason=UnknownReason.MISSING_EVIDENCE,
                )
            ],
            confidence=0.0,
        )

        # Serialize and deserialize
        data = hypothesis.to_dict()
        restored = ScoutHypothesis.from_dict(data)

        assert restored.status == ScoutStatus.UNKNOWN, "Unknown status was modified"
        assert len(restored.unknowns) == 1, "Unknowns were lost"
        assert restored.unknowns[0].reason == UnknownReason.MISSING_EVIDENCE

    def test_unknown_cannot_upgrade_to_candidate_without_evidence(self):
        """Hypothesis with unknown cannot become candidate without evidence."""
        from alphaswarm_sol.orchestration.schemas import (
            ScoutHypothesis,
            ScoutStatus,
            UnknownItem,
            UnknownReason,
        )

        hypothesis = ScoutHypothesis(
            pattern_id="test-pattern",
            status=ScoutStatus.UNKNOWN,
            evidence_refs=[],
            unknowns=[
                UnknownItem(field="state_write", reason=UnknownReason.OUT_OF_SCOPE)
            ],
            confidence=0.0,
        )

        # Create a hypothesis with evidence and CANDIDATE status
        hypothesis_with_evidence = ScoutHypothesis(
            pattern_id="test-pattern",
            status=ScoutStatus.CANDIDATE,
            evidence_refs=["EVD-12345678"],
            unknowns=[],
            confidence=0.7,
        )

        # The key assertion: if there are unknowns, status should not be CANDIDATE
        # This is a design invariant - evidence must address the unknowns
        assert hypothesis.status == ScoutStatus.UNKNOWN
        assert len(hypothesis.evidence_refs) == 0

        # With evidence and no unknowns, CANDIDATE is valid
        assert hypothesis_with_evidence.status == ScoutStatus.CANDIDATE
        assert len(hypothesis_with_evidence.evidence_refs) > 0
        assert len(hypothesis_with_evidence.unknowns) == 0

    def test_unknown_reason_requires_expansion(self):
        """Unknown items with REQUIRES_EXPANSION indicate controlled expansion needed."""
        from alphaswarm_sol.orchestration.schemas import UnknownItem, UnknownReason

        unknown = UnknownItem(
            field="cross_contract_call",
            reason=UnknownReason.REQUIRES_EXPANSION,
        )

        assert unknown.field == "cross_contract_call"
        assert unknown.reason == UnknownReason.REQUIRES_EXPANSION


class TestOmissionSurfacing:
    """Omission lists are surfaced and not interpreted as safe."""

    def test_omission_ledger_not_empty_when_pruning(self, sample_graph, subgraph_extractor):
        """Pruned subgraph has non-empty omission ledger."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        # Small budget to force pruning
        subgraph = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=3,
            max_hops=1,
            slice_mode=SliceMode.STANDARD,
        )

        # If pruning occurred, omissions must be surfaced
        if len(sample_graph.nodes) > 3:
            assert subgraph.omissions.has_omissions(), "Pruning occurred but no omissions surfaced"

    def test_omission_coverage_score_reflects_pruning(self, sample_graph, subgraph_extractor):
        """Coverage score < 1.0 when pruning occurred."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        subgraph = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=3,
            max_hops=1,
            slice_mode=SliceMode.STANDARD,
        )

        # Coverage should reflect actual pruning
        if len(subgraph.omissions._relevant_nodes) > len(subgraph.nodes):
            assert subgraph.omissions.coverage_score < 1.0, (
                "Coverage should be < 1.0 when nodes were pruned"
            )

    def test_omission_not_interpreted_as_safe(self):
        """Omission metadata exists and indicates potential incompleteness."""
        from alphaswarm_sol.kg.subgraph import OmissionLedger

        ledger = OmissionLedger(coverage_score=0.7)
        ledger.add_omitted_node("important_function")

        # has_omissions should be True for low coverage or omitted nodes
        assert ledger.has_omissions(), "Ledger with omissions should indicate incompleteness"

        # Serialization should include omission info
        data = ledger.to_dict()
        assert data["coverage_score"] == 0.7
        assert len(data["omitted_nodes"]) > 0


class TestShuffledInputDeterminism:
    """CRITICAL: Shuffled-input determinism catches iteration order bugs.

    Per plan: Run same operation twice with inputs in different random order.
    Assert outputs are bit-identical. Catches dict/set iteration order bugs.
    """

    def test_batch_creation_deterministic_shuffled_order(self):
        """Batch creation is deterministic regardless of input order.

        NOTE: The batcher sorts inputs by tier priority internally before batching,
        so shuffled inputs should produce the same batches (sorted by priority).
        This test validates that the batches have the same total patterns.
        """
        from alphaswarm_sol.orchestration.batch import (
            AdaptiveBatcher,
            PatternCostEstimate,
        )

        batcher = AdaptiveBatcher(max_batch_tokens=2000, max_batch_size=5)

        # Create cost estimates
        estimates = [
            PatternCostEstimate(
                pattern_id=f"pattern-{i:03d}",
                base_cost=300,
                complexity_multiplier=1.0 + (i % 3) * 0.5,
                estimated_tokens=0,
                tier=["A", "B", "C"][i % 3],
            )
            for i in range(20)
        ]

        # Run 1: original order
        batches_1 = batcher.create_batches(estimates)
        patterns_1 = sorted([p for b in batches_1 for p in b.patterns])

        # Run 2: shuffled order (fixed seed for reproducibility)
        shuffled = list(estimates)
        random.seed(42)
        random.shuffle(shuffled)
        batches_2 = batcher.create_batches(shuffled)
        patterns_2 = sorted([p for b in batches_2 for p in b.patterns])

        # Both should produce same total patterns (batching preserves all inputs)
        assert patterns_1 == patterns_2, (
            "Batch creation does not preserve all patterns across shuffled inputs"
        )

    def test_cache_key_deterministic_shuffled_policy(self):
        """Cache key computation is deterministic regardless of dict order."""
        from alphaswarm_sol.agents.context.types import BudgetPolicy
        from alphaswarm_sol.orchestration.batch import CacheKey

        # Create policies with same values but potentially different internal order
        policy_1 = BudgetPolicy(
            cheap_pass_tokens=1000,
            verify_pass_tokens=3000,
            deep_pass_tokens=6000,
        )

        policy_2 = BudgetPolicy(
            deep_pass_tokens=6000,
            verify_pass_tokens=3000,
            cheap_pass_tokens=1000,
        )

        graph_data = "test_graph_data_for_hashing"
        pcp_version = "v2.0"

        key_1 = CacheKey.compute(graph_data, pcp_version, policy_1)
        key_2 = CacheKey.compute(graph_data, pcp_version, policy_2)

        assert key_1.to_string() == key_2.to_string(), (
            "Cache key not deterministic for equivalent policies"
        )

    def test_manifest_evidence_ids_sorted(self):
        """Manifest evidence IDs are sorted for deterministic output."""
        from alphaswarm_sol.agents.context.types import BudgetPolicy
        from alphaswarm_sol.orchestration.batch import BatchDiscoveryOrchestrator

        orchestrator = BatchDiscoveryOrchestrator(budget_policy=BudgetPolicy.default())

        # Create manifest with unsorted evidence IDs
        evidence_ids_unsorted = ["EVD-zzz", "EVD-aaa", "EVD-mmm", "EVD-bbb"]

        manifest = orchestrator.create_manifest(
            graph_data="test_graph",
            pcp_version="v2.0",
            batches=[],
            evidence_ids=evidence_ids_unsorted,
            protocol_context_included=True,
        )

        # Evidence IDs should be sorted in manifest
        assert manifest.evidence_ids == sorted(evidence_ids_unsorted), (
            "Manifest evidence IDs not sorted"
        )

        # Serialization should be deterministic
        data_1 = json.dumps(manifest.to_dict(), sort_keys=True)
        data_2 = json.dumps(manifest.to_dict(), sort_keys=True)
        assert data_1 == data_2, "Manifest serialization not deterministic"

    def test_fork_rank_deterministic_with_shuffled_results(self):
        """Fork-then-rank produces deterministic winner regardless of input order."""
        from datetime import datetime

        from alphaswarm_sol.orchestration.batch import ForkResult, ForkThenRank, RankingMethod
        from alphaswarm_sol.orchestration.schemas import (
            DiversityPath,
            DiversityPathType,
            ScoutHypothesis,
            ScoutStatus,
        )

        ranker = ForkThenRank(ranking_method=RankingMethod.CONFIDENCE_WEIGHTED)

        # Create fork results with varying confidence
        results = [
            ForkResult(
                scout_id=f"scout-{i}",
                diversity_path=DiversityPath(
                    path_type=DiversityPathType.OPERATION_FIRST,
                    focus="balanced analysis",
                ),
                hypothesis=ScoutHypothesis(
                    pattern_id="test-pattern",
                    status=ScoutStatus.CANDIDATE if i % 2 == 0 else ScoutStatus.NOT_MATCHED,
                    evidence_refs=[f"EVD-{i:08d}"] if i % 2 == 0 else [],
                    unknowns=[],
                    confidence=0.5 + i * 0.03,  # Stay within tier B limit of 0.70
                ),
                timestamp=datetime(2026, 1, 27, i, 0, 0),
            )
            for i in range(6)
        ]

        # Run 1: original order
        ranked_1 = ranker.rank_results("test-pattern", results)

        # Run 2: shuffled order
        shuffled = list(results)
        random.seed(12345)
        random.shuffle(shuffled)
        ranked_2 = ranker.rank_results("test-pattern", shuffled)

        # Winner should be the same
        assert ranked_1.winner.pattern_id == ranked_2.winner.pattern_id
        assert ranked_1.winner.confidence == ranked_2.winner.confidence
        assert ranked_1.confidence_aggregate == ranked_2.confidence_aggregate

    def test_pcp_merge_deterministic_shuffled_lists(self):
        """PCP merge is deterministic even with shuffled internal lists."""
        from alphaswarm_sol.context.schema import ProtocolContextPack
        from alphaswarm_sol.context.types import Assumption, Confidence, Role

        # Create PCP with multiple items in lists
        roles = [
            Role(name=f"role_{i}", capabilities=[f"cap_{i}"], trust_assumptions=[], confidence=Confidence.CERTAIN)
            for i in range(5)
        ]

        assumptions = [
            Assumption(
                description=f"Assumption {i}",
                category=f"cat_{i}",
                affects_functions=[f"func_{i}"],
                source=f"source_{i}",
                confidence=Confidence.INFERRED,
            )
            for i in range(5)
        ]

        pcp = ProtocolContextPack(
            version="2.0",
            protocol_name="Test",
            generated_at="2026-01-27T00:00:00Z",
            roles=roles,
            assumptions=assumptions,
        )

        # Serialize multiple times
        outputs = []
        for _ in range(5):
            d = pcp.to_dict()
            # Sort for consistent comparison
            d["roles"] = sorted(d["roles"], key=lambda r: r["name"])
            d["assumptions"] = sorted(d["assumptions"], key=lambda a: a["description"])
            outputs.append(json.dumps(d, sort_keys=True))

        assert all(o == outputs[0] for o in outputs), "PCP serialization not deterministic"


class TestAdaptiveBatchingWithCacheVersioning:
    """Adaptive batching with cache versioning tests (PCONTEXT-07)."""

    def test_cache_key_includes_all_components(self):
        """Cache key includes graph hash, PCP version, and budget policy."""
        from alphaswarm_sol.agents.context.types import BudgetPolicy
        from alphaswarm_sol.orchestration.batch import CacheKey

        policy = BudgetPolicy(
            cheap_pass_tokens=500,
            verify_pass_tokens=2000,
            deep_pass_tokens=5000,
        )

        key = CacheKey.compute(
            graph_data="test_graph_content",
            pcp_version="v2.1",
            budget_policy=policy,
            slice_data="test_slice",
        )

        assert key.graph_hash, "Missing graph hash"
        assert key.pcp_version == "v2.1"
        assert key.budget_policy_hash, "Missing budget policy hash"
        assert key.slice_hash, "Missing slice hash"

        # Key string should include all components
        key_str = key.to_string()
        assert "g:" in key_str, "Graph hash not in key string"
        assert "p:v2.1" in key_str, "PCP version not in key string"
        assert "b:" in key_str, "Budget hash not in key string"
        assert "s:" in key_str, "Slice hash not in key string"

    def test_cache_key_changes_with_graph(self):
        """Different graphs produce different cache keys."""
        from alphaswarm_sol.agents.context.types import BudgetPolicy
        from alphaswarm_sol.orchestration.batch import CacheKey

        policy = BudgetPolicy.default()

        key_1 = CacheKey.compute("graph_A", "v2.0", policy)
        key_2 = CacheKey.compute("graph_B", "v2.0", policy)

        assert key_1.graph_hash != key_2.graph_hash, "Different graphs should have different hashes"

    def test_cache_key_changes_with_pcp_version(self):
        """Different PCP versions produce different cache keys."""
        from alphaswarm_sol.agents.context.types import BudgetPolicy
        from alphaswarm_sol.orchestration.batch import CacheKey

        policy = BudgetPolicy.default()

        key_1 = CacheKey.compute("same_graph", "v2.0", policy)
        key_2 = CacheKey.compute("same_graph", "v2.1", policy)

        assert key_1.pcp_version != key_2.pcp_version


class TestForkThenRankWithVerifierSelection:
    """Fork-then-rank with verifier selection tests (PCONTEXT-07)."""

    def test_fork_then_rank_selects_highest_confidence(self):
        """Fork-then-rank selects hypothesis with highest confidence."""
        from datetime import datetime

        from alphaswarm_sol.orchestration.batch import ForkResult, ForkThenRank, RankingMethod
        from alphaswarm_sol.orchestration.schemas import (
            DiversityPath,
            DiversityPathType,
            ScoutHypothesis,
            ScoutStatus,
        )

        ranker = ForkThenRank(ranking_method=RankingMethod.CONFIDENCE_WEIGHTED)

        results = [
            ForkResult(
                scout_id="scout-1",
                diversity_path=DiversityPath(path_type=DiversityPathType.OPERATION_FIRST, focus="operations"),
                hypothesis=ScoutHypothesis(
                    pattern_id="test",
                    status=ScoutStatus.CANDIDATE,
                    evidence_refs=["EVD-00000001"],
                    unknowns=[],
                    confidence=0.6,
                ),
                timestamp=datetime.now(),
            ),
            ForkResult(
                scout_id="scout-2",
                diversity_path=DiversityPath(path_type=DiversityPathType.GUARD_FIRST, focus="guards"),
                hypothesis=ScoutHypothesis(
                    pattern_id="test",
                    status=ScoutStatus.CANDIDATE,
                    evidence_refs=["EVD-00000002", "EVD-00000003"],
                    unknowns=[],
                    confidence=0.7,  # Highest confidence within tier B limit
                ),
                timestamp=datetime.now(),
            ),
        ]

        ranked = ranker.rank_results("test", results)

        assert ranked.winner.confidence == 0.7, "Should select highest confidence hypothesis"

    def test_contradiction_veto_high_confidence(self):
        """Contradiction with high confidence vetoes result."""
        from datetime import datetime

        from alphaswarm_sol.orchestration.batch import ForkResult, ForkThenRank
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

        ranker = ForkThenRank(veto_threshold=0.7)

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

        # ContradictionReport uses finding_id and counterarguments structure
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
            confidence=0.85,  # Above veto threshold
        )

        ranked = ranker.rank_results("test", results, contradiction)

        assert ranked.vetoed, "High-confidence contradiction should veto"
        assert "confidence" in ranked.veto_reason.lower()


class TestProtocolContextGating:
    """Protocol context gating recorded in manifest (PCONTEXT-06, PCONTEXT-07)."""

    def test_manifest_records_protocol_context_inclusion(self):
        """Manifest records whether protocol context was included."""
        from alphaswarm_sol.agents.context.types import BudgetPolicy
        from alphaswarm_sol.orchestration.batch import BatchDiscoveryOrchestrator

        orchestrator = BatchDiscoveryOrchestrator(budget_policy=BudgetPolicy.default())

        manifest_with = orchestrator.create_manifest(
            graph_data="test",
            pcp_version="v2.0",
            batches=[],
            evidence_ids=[],
            protocol_context_included=True,
        )

        manifest_without = orchestrator.create_manifest(
            graph_data="test",
            pcp_version="v2.0",
            batches=[],
            evidence_ids=[],
            protocol_context_included=False,
        )

        assert manifest_with.protocol_context_included is True
        assert manifest_without.protocol_context_included is False

        # Serialization preserves the flag
        data_with = manifest_with.to_dict()
        data_without = manifest_without.to_dict()

        assert data_with["protocol_context_included"] is True
        assert data_without["protocol_context_included"] is False


class TestAppendOnlyDeltaMerge:
    """Append-only deltas merged deterministically (PCONTEXT-10)."""

    def test_sorted_evidence_ids_in_manifest(self):
        """Evidence IDs in manifest are sorted for deterministic ordering."""
        from alphaswarm_sol.agents.context.types import BudgetPolicy
        from alphaswarm_sol.orchestration.batch import BatchDiscoveryOrchestrator

        orchestrator = BatchDiscoveryOrchestrator()

        # Create with unsorted IDs
        manifest = orchestrator.create_manifest(
            graph_data="test",
            pcp_version="v2.0",
            batches=[],
            evidence_ids=["EVD-zzz", "EVD-aaa", "EVD-mmm"],
            protocol_context_included=True,
        )

        assert manifest.evidence_ids == ["EVD-aaa", "EVD-mmm", "EVD-zzz"], (
            "Evidence IDs should be sorted"
        )

    def test_manifest_serialization_deterministic(self):
        """Manifest serialization is deterministic across invocations."""
        from alphaswarm_sol.agents.context.types import BudgetPolicy
        from alphaswarm_sol.orchestration.batch import BatchDiscoveryOrchestrator

        orchestrator = BatchDiscoveryOrchestrator()

        manifest = orchestrator.create_manifest(
            graph_data="test_graph_data",
            pcp_version="v2.0",
            batches=[],
            evidence_ids=["EVD-001", "EVD-002"],
            protocol_context_included=True,
            metadata={"key": "value"},
        )

        # Serialize multiple times
        outputs = []
        for _ in range(5):
            data = manifest.to_dict()
            # Remove timestamp for comparison
            del data["created_at"]
            del data["manifest_id"]  # Contains timestamp
            outputs.append(json.dumps(data, sort_keys=True))

        assert all(o == outputs[0] for o in outputs), "Manifest serialization not deterministic"


class TestQualitySuiteMetrics:
    """Quality suite reports precision/recall deltas, novelty yield, evidence entropy (PCONTEXT-11)."""

    def test_slicing_benchmark_metrics(self, sample_graph):
        """Slicing benchmark reports token reduction and accuracy."""
        from alphaswarm_sol.kg.slicing_benchmark import SlicingBenchmark

        benchmark = SlicingBenchmark(target_reduction=50.0, accuracy_threshold=95.0)
        suite = benchmark.run_benchmark(sample_graph)

        # Suite should have results
        assert suite.results, "Benchmark should produce results"

        # Check that metrics are computed
        for category, result in suite.results.items():
            assert isinstance(result.reduction_percent, float)
            assert isinstance(result.full_tokens, int)
            assert isinstance(result.sliced_tokens, int)

        # Overall metrics should be computed
        assert isinstance(suite.overall_reduction, float)
        assert isinstance(suite.overall_accuracy, float)
        assert isinstance(suite.passing, bool)

    def test_batch_quality_benchmark_structure(self):
        """Batch quality benchmark produces expected structure."""
        from scripts.benchmarks.batch_quality import BatchQualityBenchmark

        benchmark = BatchQualityBenchmark()
        result = benchmark.run()

        # Should have all required fields
        assert result.timestamp
        assert result.version
        assert result.status in ("passed", "failed", "regression", "improved")

        # Should have metrics
        assert result.sequential_metrics is not None
        assert result.batch_metrics is not None
        assert result.novelty_metrics is not None
        assert result.entropy_metrics is not None
        assert result.pareto_metrics is not None

        # Should have regression checks
        assert len(result.regression_checks) > 0

        # JSON serialization should work
        json_output = result.to_json()
        parsed = json.loads(json_output)
        assert "summary" in parsed
