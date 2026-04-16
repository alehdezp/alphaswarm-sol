"""Execute query plans over a knowledge graph."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from alphaswarm_sol.kg.schema import Edge, KnowledgeGraph, Node
from alphaswarm_sol.kg.graph_hash import extract_build_hash
from alphaswarm_sol.kg.subgraph import OmissionLedger
from alphaswarm_sol.queries.patterns import (
    Condition,
    EdgeRequirement,
    PathRequirement,
    PathStep,
    PatternDefinition,
    PatternEngine,
    get_patterns,
)
from alphaswarm_sol.queries.results_v2 import PatternResultPackager, ResultsV2
from alphaswarm_sol.semgrep import run_semgrep
from alphaswarm_sol.queries.planner import QueryPlan
from alphaswarm_sol.queries.label_functions import (
    LABEL_FUNCTIONS,
    set_label_context,
    clear_label_context,
)

if TYPE_CHECKING:
    from alphaswarm_sol.labels.overlay import LabelOverlay
    from alphaswarm_sol.cache.graph_queries import GraphQueryCache


class QueryExecutor:
    """Execute a query plan against a knowledge graph.

    Supports semantic label queries when a label overlay is provided.
    Optionally caches query results using GraphQueryCache.

    Example:
        executor = QueryExecutor()
        executor.set_label_overlay(label_overlay, "reentrancy")
        result = executor.execute(graph, plan)
        executor.clear_label_overlay()

    Or use execute_with_labels() for automatic context management:
        result = executor.execute_with_labels(graph, plan, overlay, "reentrancy")

    With caching:
        from alphaswarm_sol.cache import GraphQueryCache
        cache = GraphQueryCache(ttl_seconds=300)
        executor = QueryExecutor(cache=cache)
        result = executor.execute(graph, plan, pool_id="pool-001")
    """

    def __init__(
        self,
        pattern_dir: Path | None = None,
        semgrep_rules_dir: Path | None = None,
        output_mode: str = "legacy",
        contract_strict: bool = True,
        cache: Optional["GraphQueryCache"] = None,
    ) -> None:
        self.pattern_dir = pattern_dir
        self.semgrep_rules_dir = semgrep_rules_dir or Path("examples/semgrep-smart-contracts/solidity")
        self._label_overlay: Optional["LabelOverlay"] = None
        self._label_context: Optional[str] = None
        self.output_mode = output_mode
        self.contract_strict = contract_strict
        self._cache = cache

    def set_label_overlay(
        self,
        overlay: "LabelOverlay",
        context: Optional[str] = None,
    ) -> None:
        """Set label overlay for label-based queries.

        This enables label functions like has_label(), label_confidence(),
        etc. to work in VQL queries.

        Args:
            overlay: Label overlay to query
            context: Optional analysis context for filtering (e.g., 'reentrancy')
        """
        set_label_context(overlay, context)
        self._label_overlay = overlay
        self._label_context = context

    def clear_label_overlay(self) -> None:
        """Clear label overlay after query.

        Should be called after query execution to clean up label context.
        """
        clear_label_context()
        self._label_overlay = None
        self._label_context = None

    @property
    def has_label_overlay(self) -> bool:
        """Check if a label overlay is currently set."""
        return self._label_overlay is not None

    @property
    def label_functions(self) -> dict[str, Any]:
        """Get available label functions for VQL queries."""
        return LABEL_FUNCTIONS

    def execute_with_labels(
        self,
        graph: KnowledgeGraph,
        plan: QueryPlan,
        label_overlay: "LabelOverlay",
        label_context: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute query with label overlay context.

        Automatically manages label context lifecycle.

        Args:
            graph: Knowledge graph to query
            plan: Query plan to execute
            label_overlay: Label overlay for label functions
            label_context: Optional analysis context for filtering

        Returns:
            Query result dictionary
        """
        self.set_label_overlay(label_overlay, label_context)
        try:
            return self.execute(graph, plan)
        finally:
            self.clear_label_overlay()

    def execute(
        self,
        graph: KnowledgeGraph,
        plan: QueryPlan,
        *,
        query_source: Optional[str] = None,
        pool_id: Optional[str] = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Execute a query plan against a knowledge graph.

        Args:
            graph: Knowledge graph to query
            plan: Query plan to execute
            query_source: Optional source identifier for results
            pool_id: Optional pool ID for cache scoping
            use_cache: Whether to use cache (default True)

        Returns:
            Query result dictionary
        """
        # Try cache first
        if use_cache and self._cache is not None and self._cache.is_enabled:
            cached_result = self._try_cache_get(graph, plan, pool_id)
            if cached_result is not None:
                return cached_result

        # Execute query
        result = self._execute_uncached(graph, plan, query_source=query_source)

        # Store in cache
        if use_cache and self._cache is not None and self._cache.is_enabled:
            self._try_cache_put(graph, plan, result, pool_id)

        return result

    def _try_cache_get(
        self,
        graph: KnowledgeGraph,
        plan: QueryPlan,
        pool_id: Optional[str],
    ) -> Optional[dict[str, Any]]:
        """Try to get result from cache."""
        if self._cache is None:
            return None

        graph_hash = self._get_build_hash(graph)
        query_text = self._compute_query_text(plan)
        overlay_hash = self._compute_overlay_hash()

        return self._cache.get(graph_hash, query_text, overlay_hash, pool_id)

    def _try_cache_put(
        self,
        graph: KnowledgeGraph,
        plan: QueryPlan,
        result: dict[str, Any],
        pool_id: Optional[str],
    ) -> None:
        """Try to store result in cache."""
        if self._cache is None:
            return

        graph_hash = self._get_build_hash(graph)
        query_text = self._compute_query_text(plan)
        overlay_hash = self._compute_overlay_hash()

        self._cache.put(graph_hash, query_text, result, overlay_hash, pool_id)

    def _compute_query_text(self, plan: QueryPlan) -> str:
        """Compute deterministic query text for cache key."""
        # Create a stable representation of the query plan
        parts = [plan.kind]
        if plan.node_types:
            parts.append(f"types:{','.join(sorted(plan.node_types))}")
        if plan.patterns:
            parts.append(f"patterns:{','.join(sorted(plan.patterns))}")
        if plan.lens:
            parts.append(f"lens:{','.join(sorted(plan.lens))}")
        if plan.properties:
            props = sorted(f"{k}={v}" for k, v in plan.properties.items())
            parts.append(f"props:{','.join(props)}")
        if plan.match:
            # Include match conditions in cache key
            match_repr = hashlib.md5(str(plan.match).encode()).hexdigest()[:8]
            parts.append(f"match:{match_repr}")
        parts.append(f"limit:{plan.limit}")
        return "|".join(parts)

    def _compute_overlay_hash(self) -> Optional[str]:
        """Compute hash of current overlay if set."""
        if self._label_overlay is None:
            return None
        # Use overlay's identity hash if available
        overlay_id = id(self._label_overlay)
        context_part = self._label_context or ""
        combined = f"{overlay_id}:{context_part}"
        return hashlib.md5(combined.encode()).hexdigest()[:12]

    def _execute_uncached(
        self,
        graph: KnowledgeGraph,
        plan: QueryPlan,
        *,
        query_source: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute query without cache."""
        if plan.kind == "fetch" and plan.node_ids:
            nodes = [graph.nodes[node_id] for node_id in plan.node_ids if node_id in graph.nodes]
            return self._package_result(
                nodes=nodes,
                edges=[],
                plan=plan,
                graph=graph,
                query_source=query_source,
            )
        if plan.kind == "flow" and plan.flow:
            nodes = self._filter_flow(graph, plan)
            return self._package_result(
                nodes=nodes,
                edges=[],
                plan=plan,
                graph=graph,
                query_source=query_source,
            )
        if plan.kind == "logic":
            return self._run_logic_query(graph, plan, query_source=query_source)
        if plan.kind == "edges":
            edges = self._filter_edges(graph, plan)
            return self._package_result(
                edges=edges,
                nodes=[],
                plan=plan,
                graph=graph,
                query_source=query_source,
            )
        if plan.kind in {"pattern", "lens"}:
            patterns = get_patterns(self.pattern_dir)
            findings = PatternEngine().run(
                graph,
                patterns,
                lens=plan.lens,
                pattern_ids=plan.patterns,
                severity=plan.severity,
                limit=plan.limit,
                explain=plan.explain_mode,
            )
            nodes = []
            if not plan.compact_mode:
                node_ids = {finding["node_id"] for finding in findings}
                nodes = [graph.nodes[node_id] for node_id in node_ids if node_id in graph.nodes]
            return self._package_result(
                edges=[],
                nodes=nodes,
                plan=plan,
                findings=findings,
                graph=graph,
                query_source=query_source,
            )
        if plan.kind == "semgrep":
            target = graph.metadata.get("target") or graph.metadata.get("root") or "."
            findings = run_semgrep(Path(target), self.semgrep_rules_dir, rule_ids=plan.patterns)
            return self._package_result(
                edges=[],
                nodes=[],
                plan=plan,
                findings=findings,
                graph=graph,
                query_source=query_source,
            )
        nodes = self._filter_nodes(graph, plan)
        return self._package_result(
            edges=[],
            nodes=nodes,
            plan=plan,
            graph=graph,
            query_source=query_source,
        )

    def _filter_nodes(self, graph: KnowledgeGraph, plan: QueryPlan) -> list[Node]:
        nodes: list[Node] = []
        for node in graph.nodes.values():
            if not self._match_node(node, plan.node_types, plan.properties):
                continue
            nodes.append(node)
            if len(nodes) >= plan.limit:
                break
        return nodes

    def _filter_edges(self, graph: KnowledgeGraph, plan: QueryPlan) -> list[Edge]:
        edges: list[Edge] = []
        for edge in graph.edges.values():
            if plan.edge_types and edge.type not in plan.edge_types:
                continue
            edges.append(edge)
            if len(edges) >= plan.limit:
                break
        return edges

    def _filter_flow(self, graph: KnowledgeGraph, plan: QueryPlan) -> list[Node]:
        nodes: list[Node] = []
        flow = plan.flow
        if flow is None:
            return nodes

        for node in graph.nodes.values():
            if plan.node_types and node.type not in plan.node_types:
                continue
            if not plan.node_types and node.type != "Function":
                continue
            if not self._match_node(node, plan.node_types, plan.properties):
                continue
            if not self._match_flow(graph, node, flow):
                continue
            nodes.append(node)
            if len(nodes) >= plan.limit:
                break
        return nodes

    def _run_logic_query(
        self,
        graph: KnowledgeGraph,
        plan: QueryPlan,
        *,
        query_source: Optional[str] = None,
    ) -> dict[str, Any]:
        pattern = self._build_ad_hoc_pattern(plan)
        findings = PatternEngine().run(
            graph,
            [pattern],
            limit=plan.limit,
            explain=plan.explain_mode,
        )
        nodes = []
        if not plan.compact_mode:
            node_ids = {finding["node_id"] for finding in findings}
            nodes = [graph.nodes[node_id] for node_id in node_ids if node_id in graph.nodes]
        return self._package_result(
            nodes=nodes,
            edges=[],
            plan=plan,
            findings=findings,
            graph=graph,
            query_source=query_source,
        )

    def _build_ad_hoc_pattern(self, plan: QueryPlan) -> PatternDefinition:
        scope = plan.node_types[0] if plan.node_types else "Function"
        match_all = []
        match_any = []
        match_none = []
        if plan.match:
            match_all = [Condition(c.property, c.op, c.value) for c in plan.match.all]
            match_any = [Condition(c.property, c.op, c.value) for c in plan.match.any]
            match_none = [Condition(c.property, c.op, c.value) for c in plan.match.none]
        edge_reqs = [
            EdgeRequirement(e.type, e.direction, e.target_type) for e in plan.edges_spec
        ]
        path_reqs = []
        for path in plan.paths_spec:
            steps = [PathStep(s.edge_type, s.direction, s.target_type) for s in path.steps]
            path_reqs.append(
                PathRequirement(
                    steps=steps,
                    edge_type=path.edge_type,
                    direction=path.direction,
                    max_depth=path.max_depth,
                    target_type=path.target_type,
                )
            )
        return PatternDefinition(
            id="ad-hoc",
            name="Ad Hoc Query",
            description=plan.match.model_dump() if plan.match else "ad hoc query",
            scope=scope,
            lens=[],
            severity="info",
            match_all=match_all,
            match_any=match_any,
            match_none=match_none,
            edges=edge_reqs,
            paths=path_reqs,
        )

    def _match_flow(self, graph: KnowledgeGraph, fn_node: Node, flow) -> bool:
        input_nodes = self._input_nodes_for_function(graph, fn_node)
        if flow.from_kinds:
            input_nodes = [n for n in input_nodes if n.properties.get("kind") in flow.from_kinds]
        if flow.exclude_sources:
            input_nodes = [n for n in input_nodes if n.label not in flow.exclude_sources]
        if not input_nodes:
            return False
        for input_node in input_nodes:
            if self._input_taints_target(graph, input_node, flow):
                return True
        return False

    def _input_nodes_for_function(self, graph: KnowledgeGraph, fn_node: Node) -> list[Node]:
        inputs: list[Node] = []
        for edge in graph.edges.values():
            if edge.type != "FUNCTION_HAS_INPUT":
                continue
            if edge.source != fn_node.id:
                continue
            target = graph.nodes.get(edge.target)
            if target and target.type == "Input":
                inputs.append(target)
        return inputs

    def _input_taints_target(self, graph: KnowledgeGraph, input_node: Node, flow) -> bool:
        for edge in graph.edges.values():
            if edge.type != flow.edge_type:
                continue
            if edge.source != input_node.id:
                continue
            target = graph.nodes.get(edge.target)
            if not target:
                continue
            if flow.target_type and target.type != flow.target_type:
                continue
            return True
        return False

    def _nodes_from_edges(self, graph: KnowledgeGraph, edges: list[Edge]) -> list[Node]:
        nodes: dict[str, Node] = {}
        for edge in edges:
            if edge.source in graph.nodes:
                nodes[edge.source] = graph.nodes[edge.source]
            if edge.target in graph.nodes:
                nodes[edge.target] = graph.nodes[edge.target]
        return list(nodes.values())

    def _match_node(self, node: Node, node_types: list[str], properties: dict[str, Any]) -> bool:
        if node_types and node.type not in node_types:
            return False
        for key, value in properties.items():
            node_value = node.properties.get(key)
            if isinstance(value, str):
                if node_value is None or str(node_value).lower() != value.lower():
                    return False
            else:
                if node_value != value:
                    return False
        return True

    def _package_result(
        self,
        *,
        nodes: list[Node],
        edges: list[Edge],
        plan: QueryPlan,
        findings: list[dict[str, Any]] | None = None,
        graph: Optional[KnowledgeGraph] = None,
        query_source: Optional[str] = None,
    ) -> dict[str, Any]:
        if self.output_mode == "v2":
            return self._package_result_v2(
                nodes=nodes,
                edges=edges,
                plan=plan,
                findings=findings or [],
                graph=graph,
                query_source=query_source,
            )
        return self._package_result_legacy(
            nodes=nodes,
            edges=edges,
            plan=plan,
            findings=findings or [],
        )

    def _package_result_legacy(
        self,
        *,
        nodes: list[Node],
        edges: list[Edge],
        plan: QueryPlan,
        findings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if plan.compact_mode:
            node_payload = [self._serialize_node_compact(node) for node in nodes]
            edge_payload = [self._serialize_edge_compact(edge) for edge in edges]
        else:
            node_payload = [self._serialize_node(node, plan.include_evidence) for node in nodes]
            edge_payload = [self._serialize_edge(edge, plan.include_evidence) for edge in edges]
        return {
            "summary": {
                "nodes": len(nodes),
                "edges": len(edges),
                "findings": len(findings),
                "limit": plan.limit,
                "compact_mode": plan.compact_mode,
                "evidence_mode": plan.evidence_mode,
                "explain_mode": plan.explain_mode,
            },
            "nodes": node_payload,
            "edges": edge_payload,
            "findings": findings,
        }

    def _package_result_v2(
        self,
        *,
        nodes: list[Node],
        edges: list[Edge],
        plan: QueryPlan,
        findings: list[dict[str, Any]],
        graph: Optional[KnowledgeGraph],
        query_source: Optional[str],
    ) -> dict[str, Any]:
        if plan.compact_mode:
            node_payload = [self._serialize_node_compact(node) for node in nodes]
            edge_payload = [self._serialize_edge_compact(edge) for edge in edges]
        else:
            node_payload = [self._serialize_node(node, plan.include_evidence) for node in nodes]
            edge_payload = [self._serialize_edge(edge, plan.include_evidence) for edge in edges]

        build_hash = self._get_build_hash(graph)
        nodes_count = self._count_nodes(graph, nodes)
        edges_count = self._count_edges(graph, edges)
        query_id = self._derive_query_id(plan)
        query_src = query_source or self._derive_query_source(plan)
        query_kind = self._map_query_kind(plan)
        omissions = self._extract_global_omissions(graph)

        if plan.kind in {"pattern", "lens", "logic", "semgrep"}:
            packager = PatternResultPackager(
                build_hash=build_hash,
                strict=self.contract_strict,
            )
            result = packager.package(
                findings=findings,
                query_id=query_id,
                query_source=query_src,
                nodes_count=nodes_count,
                edges_count=edges_count,
                global_omissions=omissions,
            )
            output = result.to_dict()
        else:
            output = ResultsV2(
                build_hash=build_hash,
                query_kind=query_kind,
                query_id=query_id,
                query_source=query_src,
                findings=[],
                omissions=omissions,
                nodes_count=nodes_count,
                edges_count=edges_count,
            ).to_dict()

        output["nodes"] = node_payload
        output["edges"] = edge_payload
        output["findings_raw"] = findings
        return output

    def _get_build_hash(self, graph: Optional[KnowledgeGraph]) -> str:
        if graph is None:
            return "000000000000"
        build_hash = extract_build_hash(graph, compute_if_missing=True)
        return build_hash or "000000000000"

    def _count_nodes(self, graph: Optional[KnowledgeGraph], nodes: list[Node]) -> int:
        if graph is None:
            return len(nodes)
        if hasattr(graph, "nodes"):
            try:
                return len(graph.nodes)
            except TypeError:
                pass
        if isinstance(graph, dict):
            return len(graph.get("nodes", []))
        return len(nodes)

    def _count_edges(self, graph: Optional[KnowledgeGraph], edges: list[Edge]) -> int:
        if graph is None:
            return len(edges)
        if hasattr(graph, "edges"):
            try:
                return len(graph.edges)
            except TypeError:
                pass
        if isinstance(graph, dict):
            return len(graph.get("edges", []))
        return len(edges)

    def _extract_global_omissions(self, graph: Optional[KnowledgeGraph]) -> OmissionLedger:
        if graph is None:
            return OmissionLedger(coverage_score=1.0)
        if hasattr(graph, "omissions") and getattr(graph, "omissions") is not None:
            return getattr(graph, "omissions")
        if isinstance(graph, dict):
            omissions = graph.get("omissions")
            if isinstance(omissions, dict):
                try:
                    return OmissionLedger.from_dict(omissions)
                except Exception:
                    pass
        return OmissionLedger(coverage_score=1.0)

    def _map_query_kind(self, plan: QueryPlan) -> str:
        if plan.kind in {"pattern", "lens", "semgrep"}:
            return "pattern"
        if plan.kind == "nodes":
            return "fetch"
        return plan.kind

    def _derive_query_id(self, plan: QueryPlan) -> str:
        if plan.patterns:
            return ",".join(plan.patterns)
        if plan.lens:
            return ",".join(plan.lens)
        if plan.node_types:
            return ",".join(plan.node_types)
        return plan.kind

    def _derive_query_source(self, plan: QueryPlan) -> str:
        if plan.patterns:
            return f"pattern:{','.join(plan.patterns)}"
        if plan.lens:
            return f"lens:{','.join(plan.lens)}"
        if plan.node_types:
            return f"nodes:{','.join(plan.node_types)}"
        if plan.edge_types:
            return f"edges:{','.join(plan.edge_types)}"
        return plan.kind

    def _serialize_node(self, node: Node, include_evidence: bool) -> dict[str, Any]:
        data = node.to_dict()
        if include_evidence is False:
            data["evidence"] = []
        return data

    def _serialize_node_compact(self, node: Node) -> dict[str, Any]:
        return {"id": node.id, "type": node.type, "label": node.label}

    def _serialize_edge(self, edge: Edge, include_evidence: bool) -> dict[str, Any]:
        data = edge.to_dict()
        if not include_evidence:
            data["evidence"] = []
        return data

    def _serialize_edge_compact(self, edge: Edge) -> dict[str, Any]:
        return {"id": edge.id, "type": edge.type, "source": edge.source, "target": edge.target}
