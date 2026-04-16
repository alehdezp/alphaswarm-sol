"""Export a schema snapshot from patterns and a VKG graph."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from alphaswarm_sol.kg.schema import KnowledgeGraph
from alphaswarm_sol.queries.aliases import EDGE_ALIASES, NODE_TYPE_ALIASES, PROPERTY_ALIASES
from alphaswarm_sol.queries.patterns import PatternDefinition, get_patterns


@dataclass(frozen=True)
class SchemaSnapshot:
    properties: list[str]
    node_types: list[str]
    edge_types: list[str]
    pattern_ids: list[str]
    lenses: list[str]
    operators: list[str]
    aliases: dict[str, dict[str, str]]

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "properties": self.properties,
            "node_types": self.node_types,
            "edge_types": self.edge_types,
            "pattern_ids": self.pattern_ids,
            "lenses": self.lenses,
            "operators": self.operators,
            "aliases": self.aliases,
        }


def build_schema_snapshot(
    graph: KnowledgeGraph | None, *, pattern_dir: Path | None = None
) -> SchemaSnapshot:
    patterns = get_patterns(pattern_dir)
    properties = _pattern_properties(patterns)
    node_types = _graph_node_types(graph)
    edge_types = _graph_edge_types(graph)
    pattern_ids = sorted({pattern.id for pattern in patterns})
    lenses = sorted({lens for pattern in patterns for lens in pattern.lens})
    operators = sorted({"eq", "neq", "in", "not_in", "contains_any", "contains_all", "gt", "gte", "lt", "lte", "regex"})
    aliases = {
        "properties": PROPERTY_ALIASES,
        "node_types": NODE_TYPE_ALIASES,
        "edges": EDGE_ALIASES,
    }

    return SchemaSnapshot(
        properties=sorted(properties),
        node_types=node_types,
        edge_types=edge_types,
        pattern_ids=pattern_ids,
        lenses=lenses,
        operators=operators,
        aliases=aliases,
    )


def _pattern_properties(patterns: Iterable[PatternDefinition]) -> set[str]:
    props: set[str] = set()
    for pattern in patterns:
        for cond in pattern.match_all + pattern.match_any + pattern.match_none:
            if cond.property:
                props.add(cond.property)
    return props


def _graph_node_types(graph: KnowledgeGraph | None) -> list[str]:
    if graph is None:
        return []
    return sorted({node.type for node in graph.nodes.values()})


def _graph_edge_types(graph: KnowledgeGraph | None) -> list[str]:
    if graph is None:
        return []
    return sorted({edge.type for edge in graph.edges.values()})
