"""VQL 2.0 Executor - Execute validated AST against knowledge graph."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alphaswarm_sol.kg.schema import Edge, KnowledgeGraph, Node
from alphaswarm_sol.queries.patterns import PatternEngine, get_patterns
from alphaswarm_sol.vql2.ast import (
    ASTVisitor,
    BinaryOp,
    DescribeQuery,
    ExistsExpression,
    FindQuery,
    FlowQuery,
    FunctionCall,
    Identifier,
    Literal,
    MatchQuery,
    NodePattern,
    PathExpression,
    PatternQuery,
    QueryNode,
    Subquery,
    UnaryOp,
)
from alphaswarm_sol.vql2.semantic import VKGSchema


class VQL2Executor(ASTVisitor):
    """Execute VQL 2.0 queries against a knowledge graph."""

    def __init__(
        self,
        graph: KnowledgeGraph,
        pattern_dir: Path | None = None,
        **options,
    ):
        self.graph = graph
        self.pattern_dir = pattern_dir
        self.options = options
        self.schema = VKGSchema.from_graph(graph)
        self.symbol_table: dict[str, Any] = {}  # CTE results

    def execute(self, ast: QueryNode) -> dict[str, Any]:
        """Execute AST and return results."""
        return ast.accept(self)

    # ========================================
    # Query Execution
    # ========================================

    def visit_describe_query(self, node: DescribeQuery) -> dict[str, Any]:
        """Execute DESCRIBE query."""
        if node.target == "TYPES":
            return {
                "result_type": "schema",
                "node_types": sorted(self.schema.node_types),
                "edge_types": sorted(self.schema.edge_types),
            }
        elif node.target == "PROPERTIES":
            if node.for_type:
                return {
                    "result_type": "schema",
                    "node_type": node.for_type,
                    "properties": sorted(self.schema.get_properties(node.for_type)),
                }
            else:
                return {
                    "result_type": "schema",
                    "properties_by_type": {k: sorted(v) for k, v in self.schema.properties.items()},
                }
        elif node.target == "EDGES":
            return {
                "result_type": "schema",
                "edge_types": sorted(self.schema.edge_types),
            }
        elif node.target == "PATTERNS":
            patterns = get_patterns(self.pattern_dir)
            return {
                "result_type": "schema",
                "patterns": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "description": p.description,
                        "severity": p.severity,
                        "lens": p.lens,
                    }
                    for p in patterns
                ],
            }
        elif node.target == "LENSES":
            patterns = get_patterns(self.pattern_dir)
            lenses = set()
            for p in patterns:
                lenses.update(p.lens)
            return {
                "result_type": "schema",
                "lenses": sorted(lenses),
            }
        elif node.target == "SCHEMA":
            return {
                "result_type": "schema",
                "node_types": sorted(self.schema.node_types),
                "edge_types": sorted(self.schema.edge_types),
                "properties_by_type": {k: sorted(v) for k, v in self.schema.properties.items()},
            }

        return {"result_type": "error", "message": f"Unknown DESCRIBE target: {node.target}"}

    def visit_find_query(self, node: FindQuery) -> dict[str, Any]:
        """Execute FIND query."""
        # Execute WITH clauses (CTEs)
        for with_clause in node.with_clauses:
            if with_clause.subquery:
                result = with_clause.subquery.accept(self)
                self.symbol_table[with_clause.name] = result

        # Get nodes of target types
        nodes = []
        for node_id, graph_node in self.graph.nodes.items():
            if node.target_types and graph_node.type not in node.target_types:
                continue
            nodes.append(graph_node)

        # Apply WHERE filter
        if node.where_clause:
            nodes = [n for n in nodes if self._evaluate_condition(node.where_clause.condition, n)]

        # Apply GROUP BY
        if node.group_by:
            nodes = self._apply_group_by(nodes, node.group_by)

        # Apply HAVING
        if node.having:
            nodes = [n for n in nodes if self._evaluate_condition(node.having.condition, n)]

        # Apply ORDER BY
        if node.order_by:
            nodes = self._apply_order_by(nodes, node.order_by)

        # Apply LIMIT/OFFSET
        if node.offset:
            nodes = nodes[node.offset.value :]
        if node.limit:
            nodes = nodes[: node.limit.value]

        # Project results (RETURN clause)
        if node.return_clause:
            return self._project_results(nodes, node.return_clause, node.options)

        return self._format_results(nodes, node.options)

    def visit_match_query(self, node: MatchQuery) -> dict[str, Any]:
        """Execute MATCH query."""
        # Execute WITH clauses
        for with_clause in node.with_clauses:
            if with_clause.subquery:
                result = with_clause.subquery.accept(self)
                self.symbol_table[with_clause.name] = result

        # Execute pattern matching
        matches = []
        for pattern in node.patterns:
            pattern_matches = self._match_pattern(pattern)
            matches.extend(pattern_matches)

        # Convert to nodes (extract unique nodes from matches)
        nodes = []
        node_ids = set()
        for match in matches:
            for var_name, graph_node in match.items():
                if graph_node.id not in node_ids:
                    nodes.append(graph_node)
                    node_ids.add(graph_node.id)

        # Apply WHERE filter
        if node.where_clause:
            nodes = [n for n in nodes if self._evaluate_condition(node.where_clause.condition, n)]

        # Apply modifiers
        if node.offset:
            nodes = nodes[node.offset.value :]
        if node.limit:
            nodes = nodes[: node.limit.value]

        # Project results
        if node.return_clause:
            return self._project_results(nodes, node.return_clause, node.options)

        return self._format_results(nodes, node.options)

    def _match_pattern(self, pattern) -> list[dict[str, Node]]:
        """Match a pattern sequence against the graph."""
        matches = []

        # Start with nodes matching the start pattern
        start_nodes = self._match_node_pattern(pattern.start_node)

        for start_node in start_nodes:
            # Initialize match with start node
            match = {}
            if pattern.start_node.variable:
                match[pattern.start_node.variable] = start_node

            # Try to match the rest of the pattern
            if self._match_segments(start_node, pattern.segments, match):
                matches.append(match)

        return matches

    def _match_node_pattern(self, node_pattern: NodePattern) -> list[Node]:
        """Find nodes matching a node pattern."""
        nodes = []

        # Check if referring to CTE
        if node_pattern.in_cte:
            cte_result = self.symbol_table.get(node_pattern.in_cte)
            if cte_result and "nodes" in cte_result:
                return cte_result["nodes"]
            return []

        # Match by type and properties
        for graph_node in self.graph.nodes.values():
            if node_pattern.node_type and graph_node.type != node_pattern.node_type:
                continue

            # Check properties
            if node_pattern.properties:
                match = True
                for key, value in node_pattern.properties.items():
                    if graph_node.properties.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            nodes.append(graph_node)

        return nodes

    def _match_segments(self, current_node: Node, segments: list, match: dict[str, Node]) -> bool:
        """Recursively match pattern segments."""
        if not segments:
            return True  # All segments matched

        rel_pattern, node_pattern = segments[0]
        remaining_segments = segments[1:]

        # Find edges from current node matching the relationship pattern
        for edge in self.graph.edges.values():
            # Check direction and source
            if rel_pattern.direction == "out" and edge.source != current_node.id:
                continue
            if rel_pattern.direction == "in" and edge.target != current_node.id:
                continue

            # Check edge type
            if rel_pattern.edge_type and edge.type != rel_pattern.edge_type:
                continue

            # Get target node
            target_id = edge.target if rel_pattern.direction == "out" else edge.source
            target_node = self.graph.nodes.get(target_id)
            if not target_node:
                continue

            # Check if target node matches node pattern
            if node_pattern.node_type and target_node.type != node_pattern.node_type:
                continue

            # Check properties
            if node_pattern.properties:
                props_match = True
                for key, value in node_pattern.properties.items():
                    if target_node.properties.get(key) != value:
                        props_match = False
                        break
                if not props_match:
                    continue

            # Add to match
            if node_pattern.variable:
                match[node_pattern.variable] = target_node

            # Try to match remaining segments
            if self._match_segments(target_node, remaining_segments, match):
                return True

        return False

    def visit_flow_query(self, node: FlowQuery) -> dict[str, Any]:
        """Execute FLOW query (dataflow analysis)."""
        # Simplified implementation - full dataflow analysis would be more complex
        paths = []

        if node.source and node.source.pattern:
            source_nodes = self._match_node_pattern(node.source.pattern)
        else:
            source_nodes = []

        if node.sink and node.sink.pattern:
            sink_nodes = self._match_node_pattern(node.sink.pattern)
        elif node.sink and node.sink.is_any:
            sink_nodes = list(self.graph.nodes.values())
        else:
            sink_nodes = []

        # Find paths from sources to sinks
        for source in source_nodes:
            for sink in sink_nodes:
                if self._has_dataflow_path(source, sink):
                    paths.append({"source": source, "sink": sink})

        # Format based on RETURN clause
        if node.return_clause and node.return_clause.special_return:
            special = node.return_clause.special_return
            if special == "SOURCES":
                return {
                    "result_type": "flow",
                    "sources": [{"id": p["source"].id, "label": p["source"].label} for p in paths],
                }
            elif special == "SINKS":
                return {
                    "result_type": "flow",
                    "sinks": [{"id": p["sink"].id, "label": p["sink"].label} for p in paths],
                }
            elif special == "PATHS":
                return {
                    "result_type": "flow",
                    "paths": [
                        {
                            "source": {"id": p["source"].id, "label": p["source"].label},
                            "sink": {"id": p["sink"].id, "label": p["sink"].label},
                        }
                        for p in paths
                    ],
                }

        return {
            "result_type": "flow",
            "paths": paths,
        }

    def _has_dataflow_path(self, source: Node, sink: Node) -> bool:
        """Check if there's a dataflow path from source to sink."""
        # Simplified: Check for INPUT_TAINTS_STATE or FUNCTION_INPUT_TAINTS_STATE edges
        for edge in self.graph.edges.values():
            if edge.type in ("INPUT_TAINTS_STATE", "FUNCTION_INPUT_TAINTS_STATE"):
                if edge.source == source.id and edge.target == sink.id:
                    return True
        return False

    def visit_pattern_query(self, node: PatternQuery) -> dict[str, Any]:
        """Execute PATTERN query."""
        patterns = get_patterns(self.pattern_dir)

        # Filter patterns
        filtered_patterns = []
        for pattern in patterns:
            if node.pattern_ids and pattern.id not in node.pattern_ids:
                continue
            if node.lens and not any(lens in pattern.lens for lens in node.lens):
                continue
            if node.severity and pattern.severity not in node.severity:
                continue
            filtered_patterns.append(pattern)

        # Run pattern engine
        limit = node.limit.value if node.limit else 50
        findings = PatternEngine().run(
            self.graph,
            filtered_patterns,
            limit=limit,
            explain=node.options.get("explain_mode", False),
        )

        return {
            "result_type": "findings",
            "findings": findings,
            "summary": {
                "total": len(findings),
                "patterns_matched": len(set(f["pattern_id"] for f in findings)),
            },
        }

    # ========================================
    # Expression Evaluation
    # ========================================

    def _evaluate_condition(self, expr, node: Node) -> bool:
        """Evaluate condition expression against a node."""
        if isinstance(expr, BinaryOp):
            return self._evaluate_binary_op(expr, node)
        elif isinstance(expr, UnaryOp):
            return self._evaluate_unary_op(expr, node)
        elif isinstance(expr, Identifier):
            # Boolean property check
            return bool(node.properties.get(expr.name, False))
        elif isinstance(expr, Literal):
            return bool(expr.value)
        elif isinstance(expr, ExistsExpression):
            return self._evaluate_exists(expr, node)

        return False

    def _evaluate_binary_op(self, expr: BinaryOp, node: Node) -> bool:
        """Evaluate binary operation."""
        if expr.operator == "AND":
            left = self._evaluate_condition(expr.left, node)
            right = self._evaluate_condition(expr.right, node)
            return left and right
        elif expr.operator == "OR":
            left = self._evaluate_condition(expr.left, node)
            right = self._evaluate_condition(expr.right, node)
            return left or right
        elif expr.operator in ("EQ", "="):
            left_val = self._evaluate_expression(expr.left, node)
            right_val = self._evaluate_expression(expr.right, node)
            return left_val == right_val
        elif expr.operator in ("NEQ", "!="):
            left_val = self._evaluate_expression(expr.left, node)
            right_val = self._evaluate_expression(expr.right, node)
            return left_val != right_val
        elif expr.operator in ("GT", ">"):
            left_val = self._evaluate_expression(expr.left, node)
            right_val = self._evaluate_expression(expr.right, node)
            return left_val > right_val
        elif expr.operator in ("LT", "<"):
            left_val = self._evaluate_expression(expr.left, node)
            right_val = self._evaluate_expression(expr.right, node)
            return left_val < right_val
        elif expr.operator == "IN":
            left_val = self._evaluate_expression(expr.left, node)
            right_val = self._evaluate_expression(expr.right, node)
            return left_val in right_val if isinstance(right_val, (list, tuple)) else False
        elif expr.operator == "CONTAINS":
            left_val = self._evaluate_expression(expr.left, node)
            right_val = self._evaluate_expression(expr.right, node)
            return right_val in left_val if isinstance(left_val, (list, tuple)) else False
        elif expr.operator == "CONTAINS_ANY":
            left_val = self._evaluate_expression(expr.left, node)
            right_val = self._evaluate_expression(expr.right, node)
            if isinstance(left_val, (list, tuple)) and isinstance(right_val, (list, tuple)):
                return any(item in left_val for item in right_val)
            return False

        return False

    def _evaluate_unary_op(self, expr: UnaryOp, node: Node) -> bool:
        """Evaluate unary operation."""
        if expr.operator == "NOT":
            return not self._evaluate_condition(expr.operand, node)
        return False

    def _evaluate_exists(self, expr: ExistsExpression, node: Node) -> bool:
        """Evaluate EXISTS expression."""
        # Simplified: Execute subquery and check if it returns any results
        if expr.subquery:
            result = expr.subquery.accept(self)
            has_results = bool(result.get("nodes") or result.get("findings"))
            return not has_results if expr.negated else has_results
        return False

    def _evaluate_expression(self, expr, node: Node) -> Any:
        """Evaluate expression and return value."""
        if isinstance(expr, Identifier):
            return node.properties.get(expr.name)
        elif isinstance(expr, Literal):
            return expr.value
        elif isinstance(expr, PathExpression):
            # Nested property access
            value = self._evaluate_expression(expr.base, node)
            for part in expr.path:
                if isinstance(part, str):
                    value = value.get(part) if isinstance(value, dict) else None
                else:
                    # Index access
                    idx = self._evaluate_expression(part, node)
                    value = value[idx] if isinstance(value, (list, tuple)) and isinstance(idx, int) else None
            return value
        elif isinstance(expr, BinaryOp):
            # Could be comparison or arithmetic
            return self._evaluate_condition(expr, node)

        return None

    # ========================================
    # Result Formatting
    # ========================================

    def _project_results(self, nodes: list[Node], return_clause, options: dict) -> dict[str, Any]:
        """Project results based on RETURN clause."""
        if return_clause.return_all:
            return self._format_results(nodes, options)

        # Project specific fields
        results = []
        for node in nodes:
            item = {}
            for return_item in return_clause.items:
                field_value = self._evaluate_expression(return_item.expression, node)
                field_name = return_item.alias or (
                    return_item.expression.name if isinstance(return_item.expression, Identifier) else "value"
                )
                item[field_name] = field_value
            results.append(item)

        return {
            "result_type": "projected",
            "results": results,
            "summary": {"count": len(results)},
        }

    def _format_results(self, nodes: list[Node], options: dict) -> dict[str, Any]:
        """Format node results."""
        compact = options.get("compact_mode", False)
        include_evidence = options.get("include_evidence", True)

        if compact:
            return {
                "result_type": "nodes",
                "nodes": [{"id": n.id, "type": n.type, "label": n.label} for n in nodes],
                "summary": {"count": len(nodes)},
            }

        node_data = []
        for node in nodes:
            data = node.to_dict()
            if not include_evidence:
                data["evidence"] = []
            node_data.append(data)

        return {
            "result_type": "nodes",
            "nodes": node_data,
            "summary": {"count": len(nodes)},
        }

    def _apply_group_by(self, nodes: list[Node], group_by) -> list[Node]:
        """Apply GROUP BY (simplified - returns first node per group)."""
        # TODO: Full implementation with aggregations
        return nodes

    def _apply_order_by(self, nodes: list[Node], order_by) -> list[Node]:
        """Apply ORDER BY."""
        # Simplified implementation
        if not order_by.items:
            return nodes

        # Sort by first order item
        order_item = order_by.items[0]
        reverse = order_item.direction == "DESC"

        def sort_key(node: Node):
            value = self._evaluate_expression(order_item.expression, node)
            return value if value is not None else ""

        return sorted(nodes, key=sort_key, reverse=reverse)
