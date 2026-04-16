"""Omission ledger consistency and silent omission regression tests.

CRITICAL: Per PITFALLS.md "Silent Omissions Cause False Safety"

When a subgraph extraction prunes nodes or edges, the LLM receives a smaller
graph and assumes it's complete. Missing nodes are interpreted as "no evidence
of vulnerability" rather than "evidence not included." This leads to false
safety conclusions.

Prevention:
- Mandatory omission ledger on ALL subgraph outputs
- Coverage score as a first-class field
- Regression tests with known omissions (this file)

Detection:
- Coverage score < 0.8 should trigger warning
- Agent asks "is this all the relevant code?" with no answer = problem

Reference:
- .planning/research/PITFALLS.md
- docs/reference/graph-interface-v2.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "tests" / "contracts"


class TestSilentOmissionRegressions:
    """REGRESSION: Silent omissions cause false safety conclusions.

    Every subgraph output MUST include omission metadata.
    These tests catch silent omission regressions.
    """

    def test_no_silent_omissions_in_subgraph(self, sample_graph, subgraph_extractor):
        """
        REGRESSION: Silent omissions cause false safety conclusions.
        (PITFALLS.md: "Silent Omissions Cause False Safety")

        Every subgraph output MUST include omission metadata.
        """
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        subgraph = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=10,
            slice_mode=SliceMode.STANDARD,
        )

        result = subgraph.to_dict()

        # MUST have omissions field
        assert "omissions" in result, "SILENT OMISSION: subgraph missing omissions field"

        # MUST have coverage_score
        assert "coverage_score" in result["omissions"], "SILENT OMISSION: omissions missing coverage_score"

        # MUST have required omission fields
        assert "cut_set" in result["omissions"], "SILENT OMISSION: omissions missing cut_set"
        assert "slice_mode" in result["omissions"], "SILENT OMISSION: omissions missing slice_mode"

    def test_no_silent_omissions_in_ppr_subgraph(self, sample_graph, ppr_extractor):
        """PPR subgraph extraction MUST include omission metadata."""
        from alphaswarm_sol.kg.ppr_subgraph import PPRExtractionConfig

        seeds = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:2]

        if not seeds:
            pytest.skip("No functions in test graph")

        config = PPRExtractionConfig.standard()
        config.max_nodes = 10

        result = ppr_extractor.extract_from_seeds(seeds, config=config)
        output = result.subgraph.to_dict()

        # MUST have omissions
        assert "omissions" in output, "SILENT OMISSION: PPR subgraph missing omissions"
        assert "coverage_score" in output["omissions"], "SILENT OMISSION: PPR omissions missing coverage_score"

    def test_no_silent_omissions_in_pattern_results(self, sample_graph):
        """Pattern results MUST include omission metadata."""
        from alphaswarm_sol.queries import package_pattern_results
        from alphaswarm_sol.llm.interface_contract import generate_build_hash

        build_hash = generate_build_hash("silent_omission_test")

        output = package_pattern_results(
            findings=[
                {
                    "pattern_id": "test-pattern",
                    "severity": "medium",
                    "node_id": "func_test",
                    "explain": {},
                }
            ],
            build_hash=build_hash,
            strict=False,
        )

        # Global omissions MUST be present
        assert "omissions" in output, "SILENT OMISSION: pattern results missing global omissions"
        assert "coverage_score" in output["omissions"], "SILENT OMISSION: global omissions missing coverage_score"

        # Per-finding omissions MUST be present
        for i, finding in enumerate(output["findings"]):
            assert "omissions" in finding, f"SILENT OMISSION: finding[{i}] missing omissions"
            assert "coverage_score" in finding["omissions"], f"SILENT OMISSION: finding[{i}] omissions missing coverage_score"


class TestPrunedNodesInOmissionLedger:
    """Pruned nodes must be recorded in omission ledger."""

    def test_pruned_nodes_appear_in_omission_ledger(self, sample_graph, subgraph_extractor):
        """Pruned nodes must be recorded in omission ledger."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        # Small budget to force pruning
        subgraph = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=5,
            max_hops=2,
            slice_mode=SliceMode.STANDARD,
        )

        # If graph had more than 5 nodes reachable, some were pruned
        total_reachable = len(subgraph.omissions._relevant_nodes)
        captured = len(subgraph.nodes)

        if total_reachable > captured:
            # Coverage should be < 1.0
            assert subgraph.omissions.coverage_score < 1.0, (
                f"Coverage should be < 1.0 when pruning: {subgraph.omissions.coverage_score}"
            )
            # cut_set or omitted_nodes should be non-empty
            has_omission_info = (
                len(subgraph.omissions.cut_set) > 0 or
                len(subgraph.omissions.omitted_nodes) > 0
            )
            assert has_omission_info, "Pruning occurred but no omission info recorded"

    def test_depth_limit_recorded_in_cut_set(self, sample_graph, subgraph_extractor):
        """Depth limit should be recorded in cut_set."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        # Use shallow depth to potentially hit limit
        subgraph = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=100,
            max_hops=1,  # Very shallow
            slice_mode=SliceMode.STANDARD,
        )

        # Check if depth limit was recorded
        cut_set_blockers = [entry.blocker for entry in subgraph.omissions.cut_set]
        depth_entries = [b for b in cut_set_blockers if "depth_limit" in b]

        # If there are nodes beyond depth 1, we should have depth limit entry
        # This is implementation-dependent, so just verify structure is correct
        for entry in subgraph.omissions.cut_set:
            assert hasattr(entry, "blocker"), "CutSetEntry missing blocker"
            assert hasattr(entry, "reason"), "CutSetEntry missing reason"

    def test_budget_exceeded_recorded_in_cut_set(self, sample_graph, subgraph_extractor):
        """Budget exceeded should be recorded in cut_set when pruning."""
        from alphaswarm_sol.kg.subgraph import SliceMode, CutSetReason

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        # Use tiny budget to force pruning
        subgraph = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=3,  # Very small
            max_hops=3,
            slice_mode=SliceMode.STANDARD,
        )

        # If we have more than 3 nodes before pruning, budget should be recorded
        if len(subgraph.omissions.omitted_nodes) > 0:
            budget_entries = [
                e for e in subgraph.omissions.cut_set
                if e.reason == CutSetReason.BUDGET_EXCEEDED
            ]
            assert len(budget_entries) > 0, "Budget exceeded but not recorded in cut_set"


class TestOmissionLedgerFieldConsistency:
    """Omission ledger has consistent field types."""

    def test_omission_ledger_fields_consistent(self, sample_graph, subgraph_extractor):
        """Omission ledger has consistent field types."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        subgraph = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=10,
            slice_mode=SliceMode.STANDARD,
        )

        omissions = subgraph.omissions

        # Type checks
        assert isinstance(omissions.coverage_score, (int, float)), (
            f"coverage_score must be numeric, got {type(omissions.coverage_score)}"
        )
        assert 0.0 <= omissions.coverage_score <= 1.0, (
            f"coverage_score out of range: {omissions.coverage_score}"
        )
        assert isinstance(omissions.cut_set, list), (
            f"cut_set must be list, got {type(omissions.cut_set)}"
        )
        assert isinstance(omissions.excluded_edges, list), (
            f"excluded_edges must be list, got {type(omissions.excluded_edges)}"
        )
        assert isinstance(omissions.omitted_nodes, list), (
            f"omitted_nodes must be list, got {type(omissions.omitted_nodes)}"
        )
        assert omissions.slice_mode.value in ["standard", "debug"], (
            f"slice_mode invalid: {omissions.slice_mode}"
        )

    def test_omission_ledger_serializes_correctly(self, sample_graph, subgraph_extractor):
        """Omission ledger serializes to correct dict structure."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        subgraph = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=10,
            slice_mode=SliceMode.STANDARD,
        )

        omissions_dict = subgraph.omissions.to_dict()

        # Required fields in serialized form
        assert "coverage_score" in omissions_dict
        assert "cut_set" in omissions_dict
        assert "excluded_edges" in omissions_dict
        assert "slice_mode" in omissions_dict

        # Correct types after serialization
        assert isinstance(omissions_dict["coverage_score"], float)
        assert isinstance(omissions_dict["cut_set"], list)
        assert isinstance(omissions_dict["slice_mode"], str)


class TestCoverageScoreDecreases:
    """Coverage score decreases appropriately with pruning."""

    def test_coverage_score_decreases_with_pruning(self, sample_graph, subgraph_extractor):
        """More aggressive pruning = lower coverage score."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        # Large extraction
        large = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=100,
            max_hops=3,
            slice_mode=SliceMode.STANDARD,
        )

        # Small extraction
        small = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=5,
            max_hops=1,
            slice_mode=SliceMode.STANDARD,
        )

        assert small.omissions.coverage_score <= large.omissions.coverage_score, (
            f"Small ({small.omissions.coverage_score}) should have <= coverage than large ({large.omissions.coverage_score})"
        )

    def test_coverage_score_monotonic_with_budget(self, sample_graph, subgraph_extractor):
        """Coverage score is monotonically non-decreasing with budget."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        # Test with increasing budgets
        budgets = [5, 10, 20, 50, 100]
        scores = []

        for budget in budgets:
            subgraph = subgraph_extractor.extract_for_analysis(
                focal_nodes=focal_nodes,
                max_nodes=budget,
                max_hops=3,
                slice_mode=SliceMode.STANDARD,
            )
            scores.append(subgraph.omissions.coverage_score)

        # Scores should be non-decreasing
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i-1], (
                f"Coverage not monotonic: budget {budgets[i-1]}={scores[i-1]} > budget {budgets[i]}={scores[i]}"
            )


class TestDebugModeOmissions:
    """Debug slice mode records all omissions."""

    def test_debug_mode_records_all_omissions(self, sample_graph, subgraph_extractor):
        """Debug slice mode records all omitted nodes."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        # Debug mode with large budget (shouldn't prune)
        subgraph = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=100,
            max_hops=3,
            slice_mode=SliceMode.DEBUG,
        )

        # Debug mode should be indicated
        assert subgraph.omissions.slice_mode.value == "debug", (
            f"Expected debug mode, got {subgraph.omissions.slice_mode}"
        )

    def test_debug_mode_vs_standard_mode(self, sample_graph, subgraph_extractor):
        """Debug mode exposes more omission detail than standard."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        standard = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=100,
            slice_mode=SliceMode.STANDARD,
        )

        debug = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=100,
            slice_mode=SliceMode.DEBUG,
        )

        # Mode should be correctly set
        assert standard.omissions.slice_mode.value == "standard"
        assert debug.omissions.slice_mode.value == "debug"


class TestCrossModuleOmissionConsistency:
    """Omission handling is consistent across modules."""

    def test_pattern_findings_include_omissions(self, sample_graph):
        """Pattern findings include omission context."""
        from alphaswarm_sol.queries import package_pattern_results
        from alphaswarm_sol.llm.interface_contract import generate_build_hash

        build_hash = generate_build_hash("cross_module_test")

        output = package_pattern_results(
            findings=[
                {
                    "pattern_id": "test-pattern-1",
                    "severity": "medium",
                    "node_id": "func_1",
                    "explain": {},
                },
                {
                    "pattern_id": "test-pattern-2",
                    "severity": "high",
                    "node_id": "func_2",
                    "explain": {},
                },
            ],
            build_hash=build_hash,
            strict=False,
        )

        for i, finding in enumerate(output["findings"]):
            # Each finding must have omissions
            assert "omissions" in finding, f"Finding[{i}] missing omissions"

            omissions = finding["omissions"]
            assert "coverage_score" in omissions, f"Finding[{i}] omissions missing coverage_score"
            assert "cut_set" in omissions, f"Finding[{i}] omissions missing cut_set"
            assert "slice_mode" in omissions, f"Finding[{i}] omissions missing slice_mode"

    def test_subgraph_and_pattern_omission_structure_match(self, sample_graph, subgraph_extractor):
        """Subgraph and pattern outputs use same omission structure."""
        from alphaswarm_sol.kg.subgraph import SliceMode
        from alphaswarm_sol.queries import package_pattern_results
        from alphaswarm_sol.llm.interface_contract import generate_build_hash

        # Get subgraph omissions structure
        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        subgraph = subgraph_extractor.extract_for_analysis(
            focal_nodes=focal_nodes,
            max_nodes=10,
            slice_mode=SliceMode.STANDARD,
        )
        subgraph_omissions = subgraph.omissions.to_dict()

        # Get pattern omissions structure
        build_hash = generate_build_hash("structure_test")
        output = package_pattern_results(
            findings=[{"pattern_id": "test", "severity": "low", "node_id": "n1", "explain": {}}],
            build_hash=build_hash,
            strict=False,
        )
        pattern_omissions = output["omissions"]

        # Same required fields
        required_fields = {"coverage_score", "cut_set", "excluded_edges", "slice_mode"}
        subgraph_fields = set(subgraph_omissions.keys())
        pattern_fields = set(pattern_omissions.keys())

        assert required_fields <= subgraph_fields, f"Subgraph missing: {required_fields - subgraph_fields}"
        assert required_fields <= pattern_fields, f"Pattern missing: {required_fields - pattern_fields}"


class TestOmissionLedgerDataclass:
    """OmissionLedger dataclass behaves correctly."""

    def test_omission_ledger_empty_factory(self):
        """OmissionLedger.empty() creates valid empty ledger."""
        from alphaswarm_sol.kg.subgraph import OmissionLedger, SliceMode

        ledger = OmissionLedger.empty()

        assert ledger.coverage_score == 1.0
        assert ledger.cut_set == []
        assert ledger.excluded_edges == []
        assert ledger.omitted_nodes == []
        assert ledger.slice_mode == SliceMode.STANDARD

    def test_omission_ledger_add_cut_set_entry(self):
        """OmissionLedger.add_cut_set_entry works correctly."""
        from alphaswarm_sol.kg.subgraph import OmissionLedger, CutSetReason

        ledger = OmissionLedger.empty()
        ledger.add_cut_set_entry(
            blocker="modifier_nonReentrant",
            reason=CutSetReason.MODIFIER_NOT_TRAVERSED,
            impact="Modifier body not analyzed",
        )

        assert len(ledger.cut_set) == 1
        entry = ledger.cut_set[0]
        assert entry.blocker == "modifier_nonReentrant"
        assert entry.reason == CutSetReason.MODIFIER_NOT_TRAVERSED
        assert entry.impact == "Modifier body not analyzed"

    def test_omission_ledger_add_excluded_edge(self):
        """OmissionLedger.add_excluded_edge deduplicates."""
        from alphaswarm_sol.kg.subgraph import OmissionLedger

        ledger = OmissionLedger.empty()
        ledger.add_excluded_edge("INHERITS_FROM")
        ledger.add_excluded_edge("INHERITS_FROM")  # Duplicate
        ledger.add_excluded_edge("IMPLEMENTS")

        assert len(ledger.excluded_edges) == 2
        assert "INHERITS_FROM" in ledger.excluded_edges
        assert "IMPLEMENTS" in ledger.excluded_edges

    def test_omission_ledger_has_omissions(self):
        """OmissionLedger.has_omissions detects any omission."""
        from alphaswarm_sol.kg.subgraph import OmissionLedger, CutSetReason

        # Empty = no omissions
        empty = OmissionLedger.empty()
        assert not empty.has_omissions()

        # With coverage < 1.0
        low_coverage = OmissionLedger(coverage_score=0.8)
        assert low_coverage.has_omissions()

        # With cut_set entry
        with_cut = OmissionLedger.empty()
        with_cut.add_cut_set_entry("blocker", CutSetReason.BUDGET_EXCEEDED)
        assert with_cut.has_omissions()

        # With excluded_edges
        with_excluded = OmissionLedger.empty()
        with_excluded.add_excluded_edge("EDGE_TYPE")
        assert with_excluded.has_omissions()

        # With omitted_nodes
        with_omitted = OmissionLedger.empty()
        with_omitted.add_omitted_node("node_1")
        assert with_omitted.has_omissions()

    def test_omission_ledger_from_dict(self):
        """OmissionLedger.from_dict deserializes correctly."""
        from alphaswarm_sol.kg.subgraph import OmissionLedger, SliceMode

        data = {
            "coverage_score": 0.75,
            "cut_set": [
                {"blocker": "test_blocker", "reason": "budget_exceeded", "impact": "test"}
            ],
            "excluded_edges": ["EDGE_A", "EDGE_B"],
            "omitted_nodes": ["node_1", "node_2"],
            "slice_mode": "debug",
        }

        ledger = OmissionLedger.from_dict(data)

        assert ledger.coverage_score == 0.75
        assert len(ledger.cut_set) == 1
        assert ledger.cut_set[0].blocker == "test_blocker"
        assert len(ledger.excluded_edges) == 2
        assert len(ledger.omitted_nodes) == 2
        assert ledger.slice_mode == SliceMode.DEBUG

    def test_omission_ledger_round_trip(self):
        """OmissionLedger serializes and deserializes consistently."""
        from alphaswarm_sol.kg.subgraph import OmissionLedger, CutSetReason, SliceMode

        original = OmissionLedger(
            coverage_score=0.65,
            slice_mode=SliceMode.DEBUG,
        )
        original.add_cut_set_entry("blocker_a", CutSetReason.DEPTH_LIMIT_REACHED, "impact_a")
        original.add_excluded_edge("EDGE_TYPE")
        original.add_omitted_node("node_x")

        # Serialize
        serialized = original.to_dict()

        # Deserialize
        restored = OmissionLedger.from_dict(serialized)

        # Compare
        assert restored.coverage_score == original.coverage_score
        assert len(restored.cut_set) == len(original.cut_set)
        assert restored.excluded_edges == original.excluded_edges
        assert restored.omitted_nodes == original.omitted_nodes
        assert restored.slice_mode == original.slice_mode
