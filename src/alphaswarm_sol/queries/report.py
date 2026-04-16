"""Lens report aggregation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alphaswarm_sol.kg.schema import KnowledgeGraph
from alphaswarm_sol.queries.patterns import PatternEngine, get_patterns


def build_lens_report(
    graph: KnowledgeGraph,
    lens: list[str],
    *,
    limit: int = 50,
    pattern_dir: Path | None = None,
) -> dict[str, Any]:
    patterns = get_patterns(pattern_dir)
    findings = PatternEngine().run(
        graph,
        patterns,
        lens=lens,
        limit=limit,
    )
    fn_to_contract = _function_contract_map(graph)
    contracts: dict[str, dict[str, Any]] = {}
    for finding in findings:
        node_id = finding.get("node_id")
        contract_id = fn_to_contract.get(node_id, "unknown")
        contract_node = graph.nodes.get(contract_id)
        contract_label = contract_node.label if contract_node else "unknown"
        entry = contracts.setdefault(
            contract_id,
            {
                "contract_id": contract_id,
                "contract_label": contract_label,
                "lens_counts": {name: 0 for name in lens},
                "findings": [],
            },
        )
        for lens_name in finding.get("lens", []):
            if lens_name in entry["lens_counts"]:
                entry["lens_counts"][lens_name] += 1
        entry["findings"].append(
            {
                "pattern_id": finding.get("pattern_id"),
                "severity": finding.get("severity"),
                "node_label": finding.get("node_label"),
                "lens": finding.get("lens"),
            }
        )
    return {
        "lens": lens,
        "contracts": sorted(contracts.values(), key=lambda item: item["contract_label"]),
        "findings": len(findings),
    }


def _function_contract_map(graph: KnowledgeGraph) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for edge in graph.edges.values():
        if edge.type != "CONTAINS_FUNCTION":
            continue
        mapping[edge.target] = edge.source
    return mapping
