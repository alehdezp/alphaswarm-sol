"""Coverage score determinism tests.

Tests ensure coverage scores are deterministic and reproducible:
- Same graph + same query = same coverage score
- Rebuild graph from same source = same coverage score
- Build hash is stable for same source
- Evidence IDs are stable across builds
- Coverage formula matches documented specification

Reference:
- docs/reference/graph-interface-v2.md (coverage formula)
- 05.9-CONTEXT.md (coverage_score = captured_nodes_weight / relevant_nodes_weight)
"""

from __future__ import annotations

from pathlib import Path
from typing import Set

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "tests" / "contracts"


class TestCoverageScoreDeterminism:
    """Coverage scores must be deterministic for identical inputs."""

    def test_coverage_score_deterministic_same_extraction(self, sample_graph, subgraph_extractor):
        """Same graph + same seeds = same coverage score across extractions."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        # Get focal nodes
        focal_nodes = []
        for node_id, node in sample_graph.nodes.items():
            if node.type == "Function":
                focal_nodes.append(node_id)
                break

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        # Extract multiple times
        scores = []
        for _ in range(5):
            subgraph = subgraph_extractor.extract_for_analysis(
                focal_nodes=focal_nodes,
                max_nodes=20,
                max_hops=2,
                slice_mode=SliceMode.STANDARD,
            )
            scores.append(subgraph.omissions.coverage_score)

        # All scores must be identical
        assert all(s == scores[0] for s in scores), f"Coverage scores not deterministic: {scores}"

    def test_coverage_score_deterministic_ppr_extraction(self, sample_graph, ppr_extractor):
        """PPR extraction produces deterministic coverage scores."""
        from alphaswarm_sol.kg.ppr_subgraph import PPRExtractionConfig

        # Get seed nodes
        seeds = []
        for node_id, node in sample_graph.nodes.items():
            if node.type == "Function":
                seeds.append(node_id)
                if len(seeds) >= 2:
                    break

        if not seeds:
            pytest.skip("No functions in test graph")

        # Configure PPR extraction
        config = PPRExtractionConfig.standard()
        config.max_nodes = 20

        # Extract multiple times
        scores = []
        for _ in range(5):
            result = ppr_extractor.extract_from_seeds(seeds, config=config)
            scores.append(result.subgraph.omissions.coverage_score)

        # All scores must be identical
        assert all(s == scores[0] for s in scores), f"PPR coverage scores not deterministic: {scores}"

    def test_coverage_score_rebuild_deterministic(self, sample_contract_path):
        """Rebuilding graph from same source produces same coverage score."""
        from alphaswarm_sol.kg.builder import VKGBuilder
        from alphaswarm_sol.kg.subgraph import SubgraphExtractor, SliceMode

        builder = VKGBuilder(ROOT)

        # Build graph twice
        graph1 = builder.build(sample_contract_path)
        graph2 = builder.build(sample_contract_path)

        # Get common focal node (by label since IDs might differ)
        focal_label = None
        for node in graph1.nodes.values():
            if node.type == "Function":
                focal_label = node.label
                break

        if not focal_label:
            pytest.skip("No functions in test graph")

        # Find nodes by label in each graph
        focal1 = [nid for nid, n in graph1.nodes.items() if n.label == focal_label]
        focal2 = [nid for nid, n in graph2.nodes.items() if n.label == focal_label]

        if not focal1 or not focal2:
            pytest.skip("Could not find matching focal nodes")

        # Extract from each
        ext1 = SubgraphExtractor(graph1)
        ext2 = SubgraphExtractor(graph2)

        sg1 = ext1.extract_for_analysis(focal_nodes=focal1[:1], max_nodes=20, slice_mode=SliceMode.STANDARD)
        sg2 = ext2.extract_for_analysis(focal_nodes=focal2[:1], max_nodes=20, slice_mode=SliceMode.STANDARD)

        # Coverage scores should be identical for same structure
        assert sg1.omissions.coverage_score == sg2.omissions.coverage_score, (
            f"Coverage scores differ across rebuilds: {sg1.omissions.coverage_score} vs {sg2.omissions.coverage_score}"
        )


class TestBuildHashStability:
    """Build hash must be stable for identical source."""

    def test_build_hash_deterministic(self, sample_contract_path):
        """Build hash is deterministic for same source content."""
        from alphaswarm_sol.llm.interface_contract import generate_build_hash

        # Read source
        source_content = sample_contract_path.read_text()

        # Generate hash multiple times
        hashes = [generate_build_hash(source_content) for _ in range(5)]

        # All must be identical
        assert all(h == hashes[0] for h in hashes), f"Build hashes not deterministic: {hashes}"

    def test_build_hash_format(self, sample_contract_path):
        """Build hash follows expected format (12 hex chars)."""
        from alphaswarm_sol.llm.interface_contract import generate_build_hash

        source_content = sample_contract_path.read_text()
        build_hash = generate_build_hash(source_content)

        # Must be 12 chars
        assert len(build_hash) == 12, f"Build hash length wrong: {len(build_hash)}"

        # Must be hex
        try:
            int(build_hash, 16)
        except ValueError:
            pytest.fail(f"Build hash not hex: {build_hash}")

    def test_build_hash_changes_with_source(self, sample_contract_path, sample_safe_contract_path):
        """Different sources produce different build hashes."""
        from alphaswarm_sol.llm.interface_contract import generate_build_hash

        source1 = sample_contract_path.read_text()
        source2 = sample_safe_contract_path.read_text()

        hash1 = generate_build_hash(source1)
        hash2 = generate_build_hash(source2)

        assert hash1 != hash2, "Different sources should produce different hashes"


class TestEvidenceIDStability:
    """Evidence IDs must be stable across identical builds."""

    def test_evidence_ids_deterministic(self):
        """Evidence IDs are deterministic for same inputs."""
        from alphaswarm_sol.llm.interface_contract import generate_evidence_id

        build_hash = "abcdef123456"
        node_id = "func_withdraw"
        line = 42
        column = 10

        # Generate multiple times
        ids = [generate_evidence_id(build_hash, node_id, line, column) for _ in range(5)]

        # All must be identical
        assert all(id == ids[0] for id in ids), f"Evidence IDs not deterministic: {ids}"

    def test_evidence_ids_different_for_different_locations(self):
        """Evidence IDs differ for different source locations."""
        from alphaswarm_sol.llm.interface_contract import generate_evidence_id

        build_hash = "abcdef123456"
        node_id = "func_withdraw"

        id1 = generate_evidence_id(build_hash, node_id, line=42)
        id2 = generate_evidence_id(build_hash, node_id, line=43)
        id3 = generate_evidence_id(build_hash, "func_deposit", line=42)

        assert id1 != id2, "Different lines should produce different IDs"
        assert id1 != id3, "Different nodes should produce different IDs"

    def test_evidence_ids_stable_across_builds(self, sample_contract_path):
        """Evidence IDs are stable when build hash matches."""
        from alphaswarm_sol.llm.interface_contract import generate_build_hash, generate_evidence_id

        source = sample_contract_path.read_text()

        # Simulate two builds
        build_hash1 = generate_build_hash(source)
        build_hash2 = generate_build_hash(source)

        # Same source = same build hash
        assert build_hash1 == build_hash2

        # Same build hash + same location = same evidence ID
        node_id = "func_test"
        line = 10

        id1 = generate_evidence_id(build_hash1, node_id, line)
        id2 = generate_evidence_id(build_hash2, node_id, line)

        assert id1 == id2, "Evidence IDs should be stable across identical builds"

    def test_evidence_id_format(self):
        """Evidence ID follows expected format (EVD-xxxxxxxx)."""
        from alphaswarm_sol.llm.interface_contract import generate_evidence_id

        build_hash = "abcdef123456"
        evidence_id = generate_evidence_id(build_hash, "node_1", 1)

        # Must start with EVD-
        assert evidence_id.startswith("EVD-"), f"Evidence ID format wrong: {evidence_id}"

        # Must have 8 hex chars after prefix
        suffix = evidence_id[4:]
        assert len(suffix) == 8, f"Evidence ID suffix length wrong: {suffix}"

        try:
            int(suffix, 16)
        except ValueError:
            pytest.fail(f"Evidence ID suffix not hex: {suffix}")


class TestCoverageFormulaCompliance:
    """Coverage formula matches documented specification."""

    def test_coverage_formula_matches_spec(self, sample_graph, subgraph_extractor):
        """Coverage = captured_weight / relevant_weight per v2 contract."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        # Get all function nodes as focal
        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        # Extract small subgraph to force pruning
        subgraph = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes[:1],
            max_nodes=5,  # Small budget to force pruning
            max_hops=1,
            slice_mode=SliceMode.STANDARD,
        )

        # Get the tracked relevant nodes (set during extraction)
        relevant_nodes = subgraph.omissions._relevant_nodes
        captured_nodes = set(subgraph.nodes.keys())

        # Manual coverage calculation per spec
        if relevant_nodes:
            captured_count = len(captured_nodes & relevant_nodes)
            relevant_count = len(relevant_nodes)
            expected_coverage = captured_count / relevant_count if relevant_count > 0 else 1.0
        else:
            expected_coverage = 1.0

        actual_coverage = subgraph.omissions.coverage_score

        # Allow small floating point tolerance
        assert abs(actual_coverage - expected_coverage) < 0.01, (
            f"Coverage formula mismatch: expected {expected_coverage:.4f}, got {actual_coverage:.4f}"
        )

    def test_coverage_score_bounds(self, sample_graph, subgraph_extractor):
        """Coverage score is always in [0.0, 1.0] range."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        # Test various configurations
        configs = [
            {"max_nodes": 5, "max_hops": 1},
            {"max_nodes": 50, "max_hops": 2},
            {"max_nodes": 100, "max_hops": 3},
        ]

        for config in configs:
            subgraph = subgraph_extractor.extract_for_analysis(
                focal_nodes=focal_nodes,
                slice_mode=SliceMode.STANDARD,
                **config,
            )
            score = subgraph.omissions.coverage_score

            assert 0.0 <= score <= 1.0, (
                f"Coverage score out of bounds: {score} for config {config}"
            )

    def test_full_coverage_when_no_pruning(self, sample_graph, subgraph_extractor):
        """Coverage is 1.0 when no nodes are pruned."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        # Use very large budget to avoid pruning
        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        subgraph = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=1000,  # Large budget
            max_hops=10,  # Deep traversal
            slice_mode=SliceMode.STANDARD,
        )

        # If no nodes were pruned, coverage should be 1.0
        if not subgraph.omissions.omitted_nodes and not subgraph.omissions.cut_set:
            assert subgraph.omissions.coverage_score == 1.0, (
                f"Coverage should be 1.0 when no pruning: {subgraph.omissions.coverage_score}"
            )

    def test_coverage_decreases_with_more_pruning(self, sample_graph, subgraph_extractor):
        """More aggressive pruning results in lower coverage."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        # Extract with different budgets
        large = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=100,
            max_hops=3,
            slice_mode=SliceMode.STANDARD,
        )

        small = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=5,
            max_hops=1,
            slice_mode=SliceMode.STANDARD,
        )

        # Smaller budget should have lower or equal coverage
        assert small.omissions.coverage_score <= large.omissions.coverage_score, (
            f"Small budget coverage ({small.omissions.coverage_score}) should be <= "
            f"large budget coverage ({large.omissions.coverage_score})"
        )


class TestOmissionLedgerComputation:
    """OmissionLedger.compute_coverage_score works correctly."""

    def test_omission_ledger_compute_empty_relevant(self):
        """Empty relevant nodes = full coverage."""
        from alphaswarm_sol.kg.subgraph import OmissionLedger

        ledger = OmissionLedger()
        score = ledger.compute_coverage_score(
            captured_nodes={"a", "b", "c"},
            relevant_nodes=set(),  # No relevant nodes
        )

        assert score == 1.0, "Empty relevant nodes should give 1.0 coverage"

    def test_omission_ledger_compute_full_capture(self):
        """Capturing all relevant nodes = full coverage."""
        from alphaswarm_sol.kg.subgraph import OmissionLedger

        ledger = OmissionLedger()
        relevant = {"a", "b", "c"}
        score = ledger.compute_coverage_score(
            captured_nodes={"a", "b", "c", "d"},  # Superset of relevant
            relevant_nodes=relevant,
        )

        assert score == 1.0, "Capturing all relevant should give 1.0 coverage"

    def test_omission_ledger_compute_partial_capture(self):
        """Partial capture gives proportional coverage."""
        from alphaswarm_sol.kg.subgraph import OmissionLedger

        ledger = OmissionLedger()
        score = ledger.compute_coverage_score(
            captured_nodes={"a", "b"},  # 2 of 4 relevant
            relevant_nodes={"a", "b", "c", "d"},
        )

        assert score == 0.5, f"Expected 0.5 coverage, got {score}"

    def test_omission_ledger_compute_no_overlap(self):
        """No overlap = zero coverage."""
        from alphaswarm_sol.kg.subgraph import OmissionLedger

        ledger = OmissionLedger()
        score = ledger.compute_coverage_score(
            captured_nodes={"x", "y", "z"},  # No overlap
            relevant_nodes={"a", "b", "c"},
        )

        assert score == 0.0, f"Expected 0.0 coverage, got {score}"

    def test_omission_ledger_tracks_internal_sets(self):
        """OmissionLedger tracks captured and relevant sets internally."""
        from alphaswarm_sol.kg.subgraph import OmissionLedger

        ledger = OmissionLedger()
        captured = {"a", "b"}
        relevant = {"a", "b", "c", "d"}

        ledger.compute_coverage_score(captured, relevant)

        assert ledger._captured_nodes == captured
        assert ledger._relevant_nodes == relevant
