"""Deterministic planner from intent to executable query plan."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from alphaswarm_sol.queries.intent import EdgeSpec, FlowSpec, Intent, MatchSpec, PathSpec


@dataclass
class QueryPlan:
    """Normalized plan for query execution."""

    kind: str
    node_types: list[str] = field(default_factory=list)
    edge_types: list[str] = field(default_factory=list)
    node_ids: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    flow: FlowSpec | None = None
    match: MatchSpec | None = None
    edges_spec: list[EdgeSpec] = field(default_factory=list)
    paths_spec: list[PathSpec] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    lens: list[str] = field(default_factory=list)
    severity: list[str] = field(default_factory=list)
    limit: int = 50
    compact_mode: bool = False
    evidence_mode: str = "full"
    explain_mode: bool = False
    include_evidence: bool = True


class QueryPlanner:
    """Planner that converts intent to a deterministic plan."""

    def build(self, intent: Intent) -> QueryPlan:
        return QueryPlan(
            kind=intent.query_kind,
            node_types=intent.node_types,
            edge_types=intent.edge_types,
            node_ids=intent.node_ids,
            properties=intent.properties,
            flow=intent.flow,
            match=intent.match,
            edges_spec=intent.edges,
            paths_spec=intent.paths,
            patterns=intent.patterns,
            lens=intent.lens,
            severity=intent.severity,
            limit=intent.limit,
            compact_mode=intent.compact_mode,
            evidence_mode=intent.evidence_mode,
            explain_mode=intent.explain_mode,
            include_evidence=intent.include_evidence,
        )
