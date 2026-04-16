"""Query-to-Seed Mapping for PPR-based context extraction.

Task 9.2: Map queries, findings, and patterns to PPR seed nodes.

This module bridges the gap between user queries and PPR/subgraph extraction by:
1. Extracting relevant node IDs from query results
2. Determining seed nodes for vulnerability-focused PPR
3. Providing context-mode-aware seed expansion

Key Concepts:
- Seeds: Starting nodes for PPR (vulnerability-related nodes)
- Primary seeds: Direct query matches (highest weight)
- Secondary seeds: Related nodes (state variables, callers, etc.)
- Seed expansion: Adding contextually important neighbors
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from alphaswarm_sol.kg.ppr import PPRConfig, PPRResult, VKGPPR, run_ppr


class SeedType(Enum):
    """Types of seed nodes for PPR."""
    PRIMARY = "primary"      # Direct query match
    SECONDARY = "secondary"  # Related node (state, caller)
    CONTEXTUAL = "contextual"  # Expanded for context


@dataclass
class SeedNode:
    """A seed node for PPR with metadata."""
    id: str
    seed_type: SeedType = SeedType.PRIMARY
    source: str = ""  # Where this seed came from
    weight: float = 1.0  # Initial weight for PPR

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SeedNode):
            return self.id == other.id
        return False


@dataclass
class SeedMapping:
    """Result of seed extraction from a query.

    Contains categorized seeds for PPR initialization and
    metadata about the extraction process.
    """
    primary_seeds: List[SeedNode] = field(default_factory=list)
    secondary_seeds: List[SeedNode] = field(default_factory=list)
    contextual_seeds: List[SeedNode] = field(default_factory=list)
    query_type: str = ""
    source_query: str = ""
    warnings: List[str] = field(default_factory=list)

    def all_seed_ids(self) -> List[str]:
        """Get all seed IDs in priority order."""
        seen = set()
        result = []
        for seed in self.primary_seeds + self.secondary_seeds + self.contextual_seeds:
            if seed.id not in seen:
                seen.add(seed.id)
                result.append(seed.id)
        return result

    def primary_seed_ids(self) -> List[str]:
        """Get only primary (highest priority) seed IDs."""
        return [s.id for s in self.primary_seeds]

    def weighted_seeds(self) -> Dict[str, float]:
        """Get seed ID to weight mapping."""
        weights = {}
        # Primary seeds get full weight
        for seed in self.primary_seeds:
            weights[seed.id] = seed.weight
        # Secondary seeds get reduced weight
        for seed in self.secondary_seeds:
            if seed.id not in weights:
                weights[seed.id] = seed.weight * 0.7
        # Contextual seeds get further reduced weight
        for seed in self.contextual_seeds:
            if seed.id not in weights:
                weights[seed.id] = seed.weight * 0.4
        return weights

    def is_empty(self) -> bool:
        """Check if no seeds were found."""
        return (
            len(self.primary_seeds) == 0 and
            len(self.secondary_seeds) == 0 and
            len(self.contextual_seeds) == 0
        )


class SeedMapper:
    """Maps queries, findings, and patterns to PPR seed nodes.

    Usage:
        mapper = SeedMapper(graph)

        # From findings
        seeds = mapper.from_findings(findings)

        # From query intent
        seeds = mapper.from_intent(intent)

        # From pattern results
        seeds = mapper.from_pattern_results(results)

        # Get seeds for PPR
        ppr_seeds = seeds.all_seed_ids()
    """

    def __init__(self, graph: Any):
        """Initialize with a KnowledgeGraph.

        Args:
            graph: KnowledgeGraph instance
        """
        self.graph = graph
        self._node_ids = self._extract_node_ids()
        self._function_nodes = self._get_function_nodes()
        self._adjacency = self._build_adjacency()

    def _extract_node_ids(self) -> Set[str]:
        """Extract all node IDs from graph."""
        if hasattr(self.graph, "nodes"):
            if isinstance(self.graph.nodes, dict):
                return set(self.graph.nodes.keys())
            return {getattr(n, "id", str(n)) for n in self.graph.nodes}
        return set()

    def _get_function_nodes(self) -> Dict[str, Any]:
        """Get all function nodes from graph."""
        functions = {}
        if hasattr(self.graph, "nodes") and isinstance(self.graph.nodes, dict):
            for node_id, node in self.graph.nodes.items():
                node_type = getattr(node, "type", node.get("type", "") if isinstance(node, dict) else "")
                if node_type == "Function":
                    functions[node_id] = node
        return functions

    def _build_adjacency(self) -> Dict[str, Set[str]]:
        """Build adjacency list from graph edges."""
        adj: Dict[str, Set[str]] = {}
        if hasattr(self.graph, "edges"):
            edges = self.graph.edges
            if isinstance(edges, dict):
                edges = edges.values()
            for edge in edges:
                source = getattr(edge, "source", edge.get("source", "") if isinstance(edge, dict) else "")
                target = getattr(edge, "target", edge.get("target", "") if isinstance(edge, dict) else "")
                adj.setdefault(source, set()).add(target)
                adj.setdefault(target, set()).add(source)
        return adj

    def from_findings(
        self,
        findings: List[Dict[str, Any]],
        expand_context: bool = True,
    ) -> SeedMapping:
        """Extract seeds from vulnerability findings.

        Args:
            findings: List of finding dictionaries with node_id
            expand_context: Whether to add secondary seeds for context

        Returns:
            SeedMapping with extracted seeds
        """
        mapping = SeedMapping(
            query_type="findings",
            source_query=f"{len(findings)} findings",
        )

        seen_ids: Set[str] = set()

        # Extract primary seeds from findings
        for finding in findings:
            node_id = finding.get("node_id", finding.get("function_id", ""))
            if node_id and node_id in self._node_ids and node_id not in seen_ids:
                seed = SeedNode(
                    id=node_id,
                    seed_type=SeedType.PRIMARY,
                    source="finding",
                    weight=self._get_finding_weight(finding),
                )
                mapping.primary_seeds.append(seed)
                seen_ids.add(node_id)

        # Expand to secondary seeds
        if expand_context:
            self._expand_secondary_seeds(mapping, seen_ids)

        return mapping

    def from_intent(
        self,
        intent: Any,
        expand_context: bool = True,
    ) -> SeedMapping:
        """Extract seeds from query intent.

        Args:
            intent: Intent object from query parsing
            expand_context: Whether to add secondary seeds

        Returns:
            SeedMapping with extracted seeds
        """
        mapping = SeedMapping(
            query_type=getattr(intent, "query_kind", "unknown"),
            source_query=getattr(intent, "raw_text", str(intent)),
        )

        seen_ids: Set[str] = set()

        # Direct node_ids from fetch queries
        if hasattr(intent, "node_ids") and intent.node_ids:
            for node_id in intent.node_ids:
                if node_id in self._node_ids and node_id not in seen_ids:
                    mapping.primary_seeds.append(SeedNode(
                        id=node_id,
                        seed_type=SeedType.PRIMARY,
                        source="fetch",
                    ))
                    seen_ids.add(node_id)

        # For pattern/lens queries, we'll get seeds from execution results
        # For now, extract function-relevant seeds from properties
        if hasattr(intent, "properties") and intent.properties:
            self._seeds_from_properties(intent.properties, mapping, seen_ids)

        # Node type filtering
        if hasattr(intent, "node_types") and intent.node_types:
            self._seeds_from_node_types(intent.node_types, mapping, seen_ids)

        # Expand to secondary seeds
        if expand_context:
            self._expand_secondary_seeds(mapping, seen_ids)

        return mapping

    def from_pattern_results(
        self,
        results: List[Dict[str, Any]],
        pattern_id: str = "",
        expand_context: bool = True,
    ) -> SeedMapping:
        """Extract seeds from pattern matching results.

        Args:
            results: Pattern match results
            pattern_id: Pattern ID for source tracking
            expand_context: Whether to add secondary seeds

        Returns:
            SeedMapping with extracted seeds
        """
        mapping = SeedMapping(
            query_type="pattern",
            source_query=pattern_id or "pattern",
        )

        seen_ids: Set[str] = set()

        for result in results:
            node_id = result.get("node_id", result.get("function_id", ""))
            if node_id and node_id in self._node_ids and node_id not in seen_ids:
                seed = SeedNode(
                    id=node_id,
                    seed_type=SeedType.PRIMARY,
                    source=f"pattern:{pattern_id}" if pattern_id else "pattern",
                    weight=self._get_pattern_weight(result),
                )
                mapping.primary_seeds.append(seed)
                seen_ids.add(node_id)

        if expand_context:
            self._expand_secondary_seeds(mapping, seen_ids)

        return mapping

    def from_node_ids(
        self,
        node_ids: List[str],
        source: str = "manual",
        expand_context: bool = True,
    ) -> SeedMapping:
        """Create seed mapping from explicit node IDs.

        Args:
            node_ids: List of node IDs
            source: Source of the node IDs
            expand_context: Whether to add secondary seeds

        Returns:
            SeedMapping with extracted seeds
        """
        mapping = SeedMapping(
            query_type="explicit",
            source_query=f"{len(node_ids)} node IDs",
        )

        seen_ids: Set[str] = set()

        for node_id in node_ids:
            if node_id in self._node_ids and node_id not in seen_ids:
                mapping.primary_seeds.append(SeedNode(
                    id=node_id,
                    seed_type=SeedType.PRIMARY,
                    source=source,
                ))
                seen_ids.add(node_id)
            elif node_id not in self._node_ids:
                mapping.warnings.append(f"Node '{node_id}' not found in graph")

        if expand_context:
            self._expand_secondary_seeds(mapping, seen_ids)

        return mapping

    def from_function_names(
        self,
        function_names: List[str],
        expand_context: bool = True,
    ) -> SeedMapping:
        """Create seed mapping from function names.

        Args:
            function_names: List of function names to find
            expand_context: Whether to add secondary seeds

        Returns:
            SeedMapping with matched function seeds
        """
        mapping = SeedMapping(
            query_type="function_name",
            source_query=f"functions: {', '.join(function_names)}",
        )

        seen_ids: Set[str] = set()
        name_lower = {n.lower() for n in function_names}

        for func_id, func in self._function_nodes.items():
            if func_id in seen_ids:
                continue

            # Check node label/name
            label = ""
            if hasattr(func, "label"):
                label = func.label
            elif isinstance(func, dict):
                label = func.get("label", func.get("name", ""))

            # Also check properties
            if hasattr(func, "properties"):
                props = func.properties if isinstance(func.properties, dict) else {}
            elif isinstance(func, dict):
                props = func.get("properties", {})
            else:
                props = {}

            func_name = props.get("name", label)

            if func_name.lower() in name_lower or label.lower() in name_lower:
                mapping.primary_seeds.append(SeedNode(
                    id=func_id,
                    seed_type=SeedType.PRIMARY,
                    source="function_name",
                ))
                seen_ids.add(func_id)

        # Warn about unmatched names
        matched_names = set()
        for seed in mapping.primary_seeds:
            func = self._function_nodes.get(seed.id)
            if func:
                props = getattr(func, "properties", {}) if hasattr(func, "properties") else func.get("properties", {})
                label = getattr(func, "label", "") if hasattr(func, "label") else func.get("label", "")
                name = props.get("name", label)
                matched_names.add(name.lower())

        for fn in function_names:
            if fn.lower() not in matched_names:
                mapping.warnings.append(f"Function '{fn}' not found in graph")

        if expand_context:
            self._expand_secondary_seeds(mapping, seen_ids)

        return mapping

    def _seeds_from_properties(
        self,
        properties: Dict[str, Any],
        mapping: SeedMapping,
        seen_ids: Set[str],
    ) -> None:
        """Add seeds based on property filters."""
        # High-risk property indicators
        risk_properties = {
            "writes_state", "has_external_calls", "uses_delegatecall",
            "has_value_transfer", "reads_user_balance", "writes_user_balance",
        }

        filter_props = set(properties.keys())

        # If filtering by risky properties, add functions with those properties
        if filter_props & risk_properties:
            for func_id, func in self._function_nodes.items():
                if func_id in seen_ids:
                    continue

                props = getattr(func, "properties", {})
                if isinstance(func, dict):
                    props = func.get("properties", {})

                # Check if function has any of the risk properties set to true
                for prop in filter_props & risk_properties:
                    if props.get(prop):
                        mapping.primary_seeds.append(SeedNode(
                            id=func_id,
                            seed_type=SeedType.PRIMARY,
                            source=f"property:{prop}",
                        ))
                        seen_ids.add(func_id)
                        break

    def _seeds_from_node_types(
        self,
        node_types: List[str],
        mapping: SeedMapping,
        seen_ids: Set[str],
        max_per_type: int = 20,
    ) -> None:
        """Add seeds based on node types."""
        if not hasattr(self.graph, "nodes") or not isinstance(self.graph.nodes, dict):
            return

        type_set = set(node_types)
        counts: Dict[str, int] = {t: 0 for t in type_set}

        for node_id, node in self.graph.nodes.items():
            if node_id in seen_ids:
                continue

            node_type = getattr(node, "type", "")
            if isinstance(node, dict):
                node_type = node.get("type", "")

            if node_type in type_set and counts[node_type] < max_per_type:
                mapping.primary_seeds.append(SeedNode(
                    id=node_id,
                    seed_type=SeedType.PRIMARY,
                    source=f"type:{node_type}",
                ))
                seen_ids.add(node_id)
                counts[node_type] += 1

    def _expand_secondary_seeds(
        self,
        mapping: SeedMapping,
        seen_ids: Set[str],
    ) -> None:
        """Expand to secondary seeds (state variables, callers, etc.)."""
        if not mapping.primary_seeds:
            return

        # For each primary seed, find related nodes
        for primary in mapping.primary_seeds[:10]:  # Limit expansion
            neighbors = self._adjacency.get(primary.id, set())

            for neighbor_id in neighbors:
                if neighbor_id in seen_ids:
                    continue

                # Get neighbor node
                if not hasattr(self.graph, "nodes"):
                    continue
                node = self.graph.nodes.get(neighbor_id)
                if not node:
                    continue

                node_type = getattr(node, "type", "")
                if isinstance(node, dict):
                    node_type = node.get("type", "")

                # Add state variables as secondary seeds
                if node_type == "StateVariable":
                    mapping.secondary_seeds.append(SeedNode(
                        id=neighbor_id,
                        seed_type=SeedType.SECONDARY,
                        source=f"state_of:{primary.id}",
                        weight=0.8,
                    ))
                    seen_ids.add(neighbor_id)

                # Add callers as secondary seeds
                elif node_type == "Function" and self._is_caller(neighbor_id, primary.id):
                    mapping.secondary_seeds.append(SeedNode(
                        id=neighbor_id,
                        seed_type=SeedType.SECONDARY,
                        source=f"calls:{primary.id}",
                        weight=0.7,
                    ))
                    seen_ids.add(neighbor_id)

    def _is_caller(self, caller_id: str, callee_id: str) -> bool:
        """Check if caller_id calls callee_id."""
        if not hasattr(self.graph, "edges"):
            return False

        edges = self.graph.edges
        if isinstance(edges, dict):
            edges = edges.values()

        for edge in edges:
            source = getattr(edge, "source", "")
            target = getattr(edge, "target", "")
            edge_type = getattr(edge, "type", "")
            if isinstance(edge, dict):
                source = edge.get("source", "")
                target = edge.get("target", "")
                edge_type = edge.get("type", "")

            if source == caller_id and target == callee_id and "call" in edge_type.lower():
                return True

        return False

    def _get_finding_weight(self, finding: Dict[str, Any]) -> float:
        """Calculate weight for a finding seed."""
        weight = 1.0

        # Severity adjustment
        severity = finding.get("severity", "").lower()
        severity_weights = {
            "critical": 1.5,
            "high": 1.3,
            "medium": 1.0,
            "low": 0.8,
            "info": 0.5,
        }
        weight *= severity_weights.get(severity, 1.0)

        # Confidence adjustment
        confidence = finding.get("confidence", 1.0)
        if isinstance(confidence, (int, float)):
            weight *= min(max(confidence, 0.5), 1.5)

        return weight

    def _get_pattern_weight(self, result: Dict[str, Any]) -> float:
        """Calculate weight for a pattern result seed."""
        weight = 1.0

        # Pattern severity
        severity = result.get("severity", "").lower()
        if severity == "critical":
            weight = 1.5
        elif severity == "high":
            weight = 1.3

        # Match score
        score = result.get("score", result.get("match_score", 1.0))
        if isinstance(score, (int, float)):
            weight *= max(score, 0.5)

        return weight


def extract_seeds_for_ppr(
    graph: Any,
    query_result: Union[Dict[str, Any], List[Dict[str, Any]]],
    source_type: str = "findings",
) -> List[str]:
    """Convenience function to extract PPR seeds from query results.

    Args:
        graph: KnowledgeGraph
        query_result: Query result (findings, pattern results, etc.)
        source_type: Type of source ("findings", "pattern", "nodes")

    Returns:
        List of seed node IDs for PPR
    """
    mapper = SeedMapper(graph)

    if source_type == "findings":
        if isinstance(query_result, dict):
            findings = query_result.get("findings", [])
        else:
            findings = query_result
        mapping = mapper.from_findings(findings)

    elif source_type == "pattern":
        if isinstance(query_result, dict):
            results = query_result.get("matches", query_result.get("results", []))
        else:
            results = query_result
        mapping = mapper.from_pattern_results(results)

    elif source_type == "nodes":
        if isinstance(query_result, dict):
            nodes = query_result.get("nodes", [])
            node_ids = [n.get("id", n) if isinstance(n, dict) else getattr(n, "id", str(n)) for n in nodes]
        else:
            node_ids = [r.get("node_id", r) if isinstance(r, dict) else r for r in query_result]
        mapping = mapper.from_node_ids(node_ids)

    else:
        return []

    return mapping.all_seed_ids()


def map_query_to_ppr_result(
    graph: Any,
    query_result: Union[Dict[str, Any], List[Dict[str, Any]]],
    source_type: str = "findings",
    context_mode: str = "standard",
    max_nodes: Optional[int] = None,
) -> Tuple[SeedMapping, PPRResult]:
    """Map query results to seeds and run PPR.

    Args:
        graph: KnowledgeGraph
        query_result: Query result
        source_type: Type of source
        context_mode: PPR context mode ("strict", "standard", "relaxed")
        max_nodes: Maximum relevant nodes to return

    Returns:
        Tuple of (SeedMapping, PPRResult)
    """
    mapper = SeedMapper(graph)

    # Get seed mapping
    if source_type == "findings":
        findings = query_result if isinstance(query_result, list) else query_result.get("findings", [])
        mapping = mapper.from_findings(findings)
    elif source_type == "pattern":
        results = query_result if isinstance(query_result, list) else query_result.get("matches", [])
        mapping = mapper.from_pattern_results(results)
    else:
        node_ids = query_result if isinstance(query_result, list) else query_result.get("node_ids", [])
        mapping = mapper.from_node_ids(node_ids)

    # Get PPR config
    config_map = {
        "strict": PPRConfig.strict(),
        "standard": PPRConfig.standard(),
        "relaxed": PPRConfig.relaxed(),
    }
    config = config_map.get(context_mode, PPRConfig.standard())

    # Run PPR
    seeds = mapping.primary_seed_ids()
    ppr_result = run_ppr(graph, seeds, config)

    return mapping, ppr_result
