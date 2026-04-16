"""PCP (Protocol Context Pack) Determinism Tests.

Validates that Protocol Context Packs are bit-identical for same graph + PCP version.
This is critical for cache correctness and reproducibility.

Per PCONTEXT-01, PCONTEXT-03:
- PCP v2 schema with deterministic defaults
- Evidence IDs stable across rebuilds
- Witness extraction deterministic

Reference:
- .planning/phases/05.10-pattern-context-batch-discovery-orchestration/05.10-CONTEXT.md
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any, Dict, List

import pytest

ROOT = Path(__file__).resolve().parents[2]


class TestPCPSchemaV2Determinism:
    """PCP v2 schema produces deterministic output."""

    def test_empty_pcp_serialization_deterministic(self):
        """Empty PCP serializes identically each time."""
        from alphaswarm_sol.context.schema import ProtocolContextPack

        pcp = ProtocolContextPack()

        outputs = [json.dumps(pcp.to_dict(), sort_keys=True) for _ in range(10)]
        assert all(o == outputs[0] for o in outputs), "Empty PCP not deterministic"

    def test_pcp_with_all_fields_deterministic(self):
        """PCP with all fields populated serializes identically."""
        from alphaswarm_sol.context.schema import ProtocolContextPack
        from alphaswarm_sol.context.types import (
            AcceptedRisk,
            Assumption,
            CausalEdge,
            CausalEdgeType,
            Confidence,
            Invariant,
            OffchainInput,
            Role,
            ValueFlow,
        )

        pcp = ProtocolContextPack(
            version="2.0",
            schema_version="2.0",
            protocol_name="FullTestProtocol",
            protocol_type="lending",
            generated_at="2026-01-27T00:00:00Z",
            auto_generated=False,
            reviewed=True,
            roles=[
                Role(
                    name="admin",
                    capabilities=["pause", "upgrade", "setFee"],
                    trust_assumptions=["multisig_3of5"],
                    confidence=Confidence.CERTAIN,
                ),
                Role(
                    name="user",
                    capabilities=["deposit", "withdraw", "borrow"],
                    trust_assumptions=[],
                    confidence=Confidence.CERTAIN,
                ),
                Role(
                    name="liquidator",
                    capabilities=["liquidate"],
                    trust_assumptions=["MEV_protected"],
                    confidence=Confidence.INFERRED,
                ),
            ],
            value_flows=[
                ValueFlow(
                    name="deposit_flow",
                    from_role="user",
                    to_role="protocol",
                    asset="ETH",
                    conditions=["deposit > 0"],
                    confidence=Confidence.CERTAIN,
                ),
                ValueFlow(
                    name="interest_flow",
                    from_role="borrower",
                    to_role="lender",
                    asset="interest_token",
                    conditions=["interest > 0"],
                    confidence=Confidence.INFERRED,
                ),
            ],
            incentives=["yield", "governance_token", "liquidation_bonus"],
            tokenomics_summary="Native token used for governance and fee discounts",
            assumptions=[
                Assumption(
                    description="Oracle prices are accurate within 1%",
                    category="price",
                    affects_functions=["liquidate", "borrow", "healthFactor"],
                    confidence=Confidence.INFERRED,
                    source="whitepaper_v2",
                ),
                Assumption(
                    description="Chainlink heartbeat is 1 hour",
                    category="oracle",
                    affects_functions=["getPrice"],
                    confidence=Confidence.CERTAIN,
                    source="chainlink_docs",
                ),
            ],
            invariants=[
                Invariant(
                    natural_language="Total deposits >= total borrows",
                    formal={"what": "deposits", "must": "gte", "value": "borrows"},
                    category="balance",
                    critical=True,
                    confidence=Confidence.CERTAIN,
                    source="whitepaper",
                ),
                Invariant(
                    natural_language="Health factor >= 1 for all positions",
                    formal={"what": "health_factor", "must": "gte", "value": 1},
                    category="solvency",
                    critical=True,
                    confidence=Confidence.CERTAIN,
                    source="whitepaper",
                ),
            ],
            offchain_inputs=[
                OffchainInput(
                    name="chainlink_oracle",
                    input_type="oracle",
                    description="Chainlink price oracle for ETH/USD",
                    affects_functions=["getPrice", "liquidate"],
                    trust_assumptions=["Chainlink nodes are decentralized"],
                    confidence=Confidence.CERTAIN,
                ),
            ],
            security_model={
                "access_control": "role_based",
                "upgrade_mechanism": "timelock_24h",
                "pause_mechanism": "admin_only",
            },
            critical_functions=["liquidate", "borrow", "withdraw", "setFee"],
            accepted_risks=[
                AcceptedRisk(
                    description="Flashloan attacks on low-liquidity pools",
                    reason="Accepted for capital efficiency",
                    affects_functions=["flashloan"],
                    documented_in="audit_v1",
                    patterns=["flashloan-manipulation"],
                ),
            ],
            governance={
                "voting_mechanism": "token_weighted",
                "proposal_threshold": "1%",
                "quorum": "10%",
            },
            sources=[
                {"tier": 1, "name": "whitepaper_v2", "url": "https://example.com/wp"},
                {"tier": 2, "name": "audit_report", "url": "https://example.com/audit"},
            ],
            deployment={
                "chain": "ethereum",
                "address": "0x1234567890abcdef",
                "block_deployed": 12345678,
            },
            notes="Test protocol for determinism validation",
            causal_edges=[
                CausalEdge(
                    source_node="oracle_stale",
                    target_node="bad_liquidation",
                    edge_type=CausalEdgeType.ENABLES,
                    probability=0.8,
                    evidence_refs=["EVD-001"],
                ),
            ],
        )

        # Serialize multiple times
        outputs = []
        for _ in range(10):
            data = pcp.to_dict()
            outputs.append(json.dumps(data, sort_keys=True))

        assert all(o == outputs[0] for o in outputs), "Full PCP not deterministic"

    def test_pcp_hash_stable(self):
        """PCP content hash is stable across serializations."""
        from alphaswarm_sol.context.schema import ProtocolContextPack
        from alphaswarm_sol.context.types import Assumption, Confidence, Role

        pcp = ProtocolContextPack(
            version="2.0",
            protocol_name="HashTestProtocol",
            generated_at="2026-01-27T00:00:00Z",
            roles=[Role(name="test", capabilities=["a"], trust_assumptions=[], confidence=Confidence.CERTAIN)],
            assumptions=[
                Assumption(description="Test assumption", category="test", affects_functions=["func"], source="doc", confidence=Confidence.CERTAIN)
            ],
        )

        # Compute hash multiple times
        hashes = []
        for _ in range(10):
            content = json.dumps(pcp.to_dict(), sort_keys=True)
            h = hashlib.sha256(content.encode()).hexdigest()
            hashes.append(h)

        assert all(h == hashes[0] for h in hashes), "PCP content hash not stable"

    def test_pcp_from_dict_preserves_order(self):
        """PCP.from_dict preserves field ordering for deterministic output."""
        from alphaswarm_sol.context.schema import ProtocolContextPack
        from alphaswarm_sol.context.types import Assumption, Confidence, Role

        original = ProtocolContextPack(
            version="2.0",
            protocol_name="OrderTest",
            generated_at="2026-01-27T00:00:00Z",
            roles=[
                Role(name="a", capabilities=["1"], trust_assumptions=[], confidence=Confidence.CERTAIN),
                Role(name="b", capabilities=["2"], trust_assumptions=[], confidence=Confidence.INFERRED),
                Role(name="c", capabilities=["3"], trust_assumptions=[], confidence=Confidence.UNKNOWN),
            ],
            assumptions=[
                Assumption(description="First", category="a", affects_functions=["f1"], source="d1", confidence=Confidence.CERTAIN),
                Assumption(description="Second", category="b", affects_functions=["f2"], source="d2", confidence=Confidence.INFERRED),
            ],
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = ProtocolContextPack.from_dict(data)

        # Order should be preserved
        original_roles = [r.name for r in original.roles]
        restored_roles = [r.name for r in restored.roles]
        assert original_roles == restored_roles, "Role order not preserved"

        original_assumptions = [a.description for a in original.assumptions]
        restored_assumptions = [a.description for a in restored.assumptions]
        assert original_assumptions == restored_assumptions, "Assumption order not preserved"


class TestWitnessExtractionDeterminism:
    """Witness and negative witness extraction is deterministic (PCONTEXT-03)."""

    def test_causal_edge_serialization_deterministic(self):
        """Causal edges serialize deterministically."""
        from alphaswarm_sol.context.types import CausalEdge, CausalEdgeType

        edge = CausalEdge(
            source_node="vuln_source",
            target_node="exploit_target",
            edge_type=CausalEdgeType.CAUSES,
            probability=0.75,
            evidence_refs=["EVD-001", "EVD-002"],
            description="Source enables target exploitation",
        )

        outputs = [json.dumps(edge.to_dict(), sort_keys=True) for _ in range(10)]
        assert all(o == outputs[0] for o in outputs), "CausalEdge not deterministic"

    def test_causal_edges_list_deterministic(self):
        """List of causal edges serializes deterministically."""
        from alphaswarm_sol.context.types import CausalEdge, CausalEdgeType

        edges = [
            CausalEdge(
                source_node=f"node_{i}",
                target_node=f"target_{i}",
                edge_type=CausalEdgeType.ENABLES if i % 2 == 0 else CausalEdgeType.BLOCKS,
                probability=0.5 + i * 0.1,
                evidence_refs=[f"EVD-{i:03d}"],
            )
            for i in range(5)
        ]

        outputs = []
        for _ in range(10):
            data = [e.to_dict() for e in edges]
            outputs.append(json.dumps(data, sort_keys=True))

        assert all(o == outputs[0] for o in outputs), "CausalEdge list not deterministic"


class TestGraphHashDeterminism:
    """Graph hash computation is deterministic."""

    def test_graph_hash_stable(self, sample_graph):
        """Graph hash is stable across computations."""
        from alphaswarm_sol.kg.graph_hash import compute_graph_hash

        hashes = [compute_graph_hash(sample_graph) for _ in range(10)]
        assert all(h == hashes[0] for h in hashes), "Graph hash not stable"

    def test_graph_hash_changes_with_content(self, sample_graph, sample_safe_graph):
        """Different graphs produce different hashes."""
        from alphaswarm_sol.kg.graph_hash import compute_graph_hash

        hash_1 = compute_graph_hash(sample_graph)
        hash_2 = compute_graph_hash(sample_safe_graph)

        assert hash_1 != hash_2, "Different graphs should have different hashes"


class TestEvidenceIDsGraphHashInclusion:
    """Evidence IDs include graph hash for stability (PCONTEXT-03)."""

    def test_evidence_id_changes_with_graph_hash(self):
        """Evidence ID changes when graph hash changes."""
        from alphaswarm_sol.llm.interface_contract import generate_evidence_id

        node_id = "func_test"
        line = 42

        id_1 = generate_evidence_id("graph_hash_A", node_id, line)
        id_2 = generate_evidence_id("graph_hash_B", node_id, line)

        assert id_1 != id_2, "Evidence ID should change with graph hash"

    def test_evidence_id_stable_for_same_graph(self):
        """Evidence ID stable for same graph hash."""
        from alphaswarm_sol.llm.interface_contract import generate_evidence_id

        graph_hash = "stable_hash_12345"
        node_id = "func_test"
        line = 42

        ids = [generate_evidence_id(graph_hash, node_id, line) for _ in range(10)]
        assert all(id == ids[0] for id in ids), "Evidence ID not stable for same graph"


class TestSliceHashDeterminism:
    """Graph slice hashes are deterministic."""

    def test_subgraph_hash_stable(self, sample_graph, subgraph_extractor):
        """Subgraph extraction produces stable hash."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        hashes = []
        for _ in range(5):
            subgraph = subgraph_extractor.extract_for_analysis(
                focal_nodes=focal_nodes,
                max_nodes=10,
                slice_mode=SliceMode.STANDARD,
            )
            data = subgraph.to_dict()
            h = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
            hashes.append(h)

        assert all(h == hashes[0] for h in hashes), "Subgraph hash not stable"

    def test_omission_ledger_hash_stable(self, sample_graph, subgraph_extractor):
        """Omission ledger produces stable hash."""
        from alphaswarm_sol.kg.subgraph import SliceMode

        focal_nodes = [nid for nid, n in sample_graph.nodes.items() if n.type == "Function"][:1]

        if not focal_nodes:
            pytest.skip("No functions in test graph")

        hashes = []
        for _ in range(5):
            subgraph = subgraph_extractor.extract_for_analysis(
                focal_nodes=focal_nodes,
                max_nodes=5,
                max_hops=1,
                slice_mode=SliceMode.STANDARD,
            )
            data = subgraph.omissions.to_dict()
            h = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
            hashes.append(h)

        assert all(h == hashes[0] for h in hashes), "Omission ledger hash not stable"


class TestConfidenceEnumDeterminism:
    """Confidence enum serialization is deterministic."""

    def test_confidence_to_string_deterministic(self):
        """Confidence enum serializes to same string."""
        from alphaswarm_sol.context.types import Confidence

        outputs = []
        for _ in range(10):
            data = {
                "certain": Confidence.CERTAIN.value,
                "inferred": Confidence.INFERRED.value,
                "unknown": Confidence.UNKNOWN.value,
            }
            outputs.append(json.dumps(data, sort_keys=True))

        assert all(o == outputs[0] for o in outputs), "Confidence enum not deterministic"

    def test_confidence_comparison_stable(self):
        """Confidence comparison is stable."""
        from alphaswarm_sol.context.types import Confidence

        # These comparisons should always work the same way
        results = []
        for _ in range(10):
            r = {
                "certain_gt_inferred": Confidence.CERTAIN > Confidence.INFERRED,
                "inferred_gt_unknown": Confidence.INFERRED > Confidence.UNKNOWN,
                "certain_gt_unknown": Confidence.CERTAIN > Confidence.UNKNOWN,
            }
            results.append(json.dumps(r, sort_keys=True))

        assert all(r == results[0] for r in results), "Confidence comparison not stable"


class TestDeterministicDefaults:
    """PCP v2 schema has deterministic defaults (PCONTEXT-01)."""

    def test_empty_lists_default(self):
        """Empty lists are default, not None."""
        from alphaswarm_sol.context.schema import ProtocolContextPack

        pcp = ProtocolContextPack()

        assert pcp.roles == []
        assert pcp.assumptions == []
        assert pcp.invariants == []
        assert pcp.offchain_inputs == []
        assert pcp.value_flows == []
        assert pcp.accepted_risks == []
        assert pcp.sources == []
        assert pcp.causal_edges == []

    def test_default_version_fields(self):
        """Version fields have deterministic defaults."""
        from alphaswarm_sol.context.schema import ProtocolContextPack

        pcp = ProtocolContextPack()

        assert pcp.version == "1.0"
        assert pcp.schema_version == "1.1"

    def test_default_auto_generated_flags(self):
        """Auto-generated and reviewed flags have deterministic defaults."""
        from alphaswarm_sol.context.schema import ProtocolContextPack

        pcp = ProtocolContextPack()

        assert pcp.auto_generated is True
        assert pcp.reviewed is False
