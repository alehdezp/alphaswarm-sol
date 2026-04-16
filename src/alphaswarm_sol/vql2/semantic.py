"""VQL 2.0 Semantic Analyzer - Validation, type checking, and fuzzy matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from alphaswarm_sol.vql2.ast import (
    ASTNode,
    ASTVisitor,
    BinaryOp,
    DescribeQuery,
    ExistsExpression,
    FindQuery,
    FlowQuery,
    Identifier,
    MatchQuery,
    NodePattern,
    PatternQuery,
    QueryNode,
    WhereClause,
)


@dataclass
class SemanticError:
    """Semantic error with suggestions."""

    message: str
    node: ASTNode | None = None
    hint: str | None = None
    suggestions: list[str] = field(default_factory=list)
    auto_fix: str | None = None
    confidence: float = 0.0

    @property
    def line(self) -> int:
        return self.node.line if self.node else 0

    @property
    def column(self) -> int:
        return self.node.column if self.node else 0


@dataclass
class SemanticWarning:
    """Semantic warning."""

    message: str
    node: ASTNode | None = None
    hint: str | None = None


class VKGSchema:
    """VKG schema definition."""

    # Type aliases for user-friendly query syntax (lowercase/plural -> canonical)
    TYPE_ALIASES = {
        "functions": "Function",
        "function": "Function",
        "funcs": "Function",
        "func": "Function",
        "contracts": "Contract",
        "contract": "Contract",
        "statevariables": "StateVariable",
        "statevariable": "StateVariable",
        "state_variables": "StateVariable",
        "events": "Event",
        "event": "Event",
        "inputs": "Input",
        "input": "Input",
        "loops": "Loop",
        "loop": "Loop",
        "invariants": "Invariant",
        "invariant": "Invariant",
        "modifiers": "Modifier",
        "modifier": "Modifier",
        "nodes": "Function",  # Default for generic 'nodes'
        "edges": "_EDGE_QUERY",  # Marker for edge queries
        "patterns": "_PATTERN_QUERY",  # Marker for pattern queries
    }

    # Default schema based on True VKG
    DEFAULT_NODE_TYPES = [
        "Function",
        "Contract",
        "StateVariable",
        "Event",
        "Input",
        "Loop",
        "Invariant",
        "ExternalCallSite",
        "SignatureUse",
        "Modifier",
    ]

    DEFAULT_EDGE_TYPES = [
        "CONTAINS_FUNCTION",
        "CONTAINS_STATE",
        "CONTAINS_EVENT",
        "CONTAINS_MODIFIER",
        "FUNCTION_HAS_INPUT",
        "FUNCTION_HAS_LOOP",
        "INPUT_TAINTS_STATE",
        "FUNCTION_INPUT_TAINTS_STATE",
        "FUNCTION_TOUCHES_INVARIANT",
        "INVARIANT_TARGETS_CONTRACT",
        "INVARIANT_TARGETS_FUNCTION",
        "INVARIANT_TARGETS_STATE",
        "USES_MODIFIER",
        "READS_STATE",
        "WRITES_STATE",
        "CALLS_INTERNAL",
        "CALLS_EXTERNAL",
        "FUNCTION_HAS_CALLSITE",
        "CALLSITE_TARGETS",
        "CALLSITE_MOVES_VALUE",
        "FUNCTION_USES_SIGNATURE",
        "INHERITS",
    ]

    DEFAULT_PROPERTIES = {
        "Function": [
            "visibility",
            "mutability",
            "writes_state",
            "reads_state",
            "has_access_gate",
            "access_gate_logic",
            "writes_privileged_state",
            "has_auth_pattern",
            "uses_tx_origin",
            "has_access_control",
            "state_write_after_external_call",
            "state_write_before_external_call",
            "has_reentrancy_guard",
            "uses_delegatecall",
            "uses_call",
            "has_external_calls",
            "low_level_calls",
            "risk_missing_slippage_parameter",
            "risk_missing_deadline_check",
            "swap_like",
            "performs_swap_or_trade",
            "performs_swap",
            "interacts_with_amm",
            "affects_price",
            "reads_oracle_price",
            "has_staleness_check",
            "has_sequencer_uptime_check",
            "oracle_freshness_ok",
            "uses_erc20_transfer",
            "token_return_guarded",
            "uses_safe_erc20",
            "has_unbounded_loop",
            "has_require_bounds",
            "external_calls_in_loop",
            "has_unbounded_deletion",
            "uses_transfer",
            "uses_send",
            "has_strict_equality_check",
            "state_mutability",
            "touches_invariant",
            "has_invariant_check",
            "touches_invariant_unchecked",
            "is_constructor",
            "is_fallback",
            "is_receive",
            "is_upgrade_function",
            "is_initializer_function",
            "has_only_proxy_modifier",
            "is_view",
            "is_pure",
            "payable",
            "uses_msg_sender",
            "uses_block_timestamp",
            "uses_block_number",
            "uses_block_hash",
            "uses_block_prevrandao",
            "uses_chainid",
            "uses_ecrecover",
            "has_minimum_output_parameter",
            "has_minimum_output",
            "contract_is_upgradeable",
            "contract_is_uups_proxy",
            "contract_is_beacon_proxy",
            "contract_is_diamond_proxy",
            "contract_is_implementation_contract",
            "call_target_validated",
            "has_unchecked_block",
            "unchecked_contains_arithmetic",
            "unchecked_operand_from_user",
            "unchecked_affects_balance",
            "has_arithmetic",
            "has_division",
            "has_multiplication",
            "division_before_multiplication",
            "in_financial_context",
            "has_explicit_cast",
            "cast_is_narrowing",
            "has_bounds_check_before_cast",
            "has_signed_to_unsigned_cast",
            "has_signed_check",
            "has_address_to_uint_cast",
            "divisor_validated_nonzero",
            "has_rounding_ops",
            "large_number_multiplication",
            "price_amount_multiplication",
            "percentage_calculation",
            "percentage_bounds_check",
            "basis_points_calculation",
            "ratio_calculation",
            "fee_calculation",
            "fee_accumulation",
            "timestamp_arithmetic",
            "uses_token_decimals",
            "decimal_scaling_usage",
            "uses_safemath",
            "uses_muldiv_or_safemath",
            "loop_counter_small_type",
            "pre_08_arithmetic",
            "division_precision_risk",
            "fee_precision_risk",
            "basis_points_precision_risk",
            "ratio_calculation_risk",
            "price_amount_overflow_risk",
            "percentage_overflow_risk",
            "token_decimal_mismatch",
            "unchecked_arithmetic_risk",
            "division_by_zero_risk",
            "signed_unsigned_cast_risk",
            "narrowing_cast_risk",
            "multiplication_overflow_risk",
            "fee_accumulation_overflow_risk",
            "writes_share_state",
            "writes_collateral_state",
            "writes_pool_state",
            "modifies_state_machine_variable",
            "state_variable_is_state_machine",
            "modifies_state_variable",
            "validates_current_state",
            "enforces_valid_transition",
            "allows_invalid_transition",
            "state_cleanup_missing",
            "state_race_condition",
            "accounting_update_missing",
            "double_counting_risk",
            "rounding_accumulation_risk",
            "emits_event",
            "event_param_mismatch",
            "override_missing_super",
            "selfdestruct_target_user_controlled",
            "extcodesize_in_constructor",
            "share_inflation_risk",
            "missing_return_value_check",
            "missing_amount_bounds",
            "modifies_balance_state",
            "maintains_balance_invariant",
        ],
        "Contract": [
            "is_proxy",
            "is_upgradeable",
            "is_uups_proxy",
            "is_beacon_proxy",
            "is_diamond_proxy",
            "is_implementation_contract",
            "initializers_disabled",
            "has_selfdestruct",
            "storage_layout_changed",
            "new_variables_not_at_end",
            "inherited_storage_conflict",
            "diamond_storage_isolation",
            "semgrep_like_rules",
            "state_var_count",
            "uses_libdiamond",
            "contract_has_beacon_state",
            "contract_has_diamond_cut",
            "is_abstract",
            "is_interface",
            "is_library",
            "has_inherited_contracts",
            "has_diamond_inheritance",
            "shadows_parent_variable",
            "compiler_version_lt_08",
            "uses_safemath",
            "has_uninitialized_storage",
            "has_uninitialized_boolean",
        ],
        "StateVariable": [
            "security_tags",
            "is_constant",
            "is_immutable",
            "visibility",
        ],
        "Loop": [
            "has_unbounded_loop",
            "has_require_bounds",
            "external_calls_in_loop",
            "has_unbounded_deletion",
        ],
        "Input": [
            "kind",  # parameter, env
            "attacker_controlled",
        ],
        "ExternalCallSite": [
            "transfers_value",
            "call_type",
        ],
    }

    def __init__(
        self,
        node_types: list[str] | None = None,
        edge_types: list[str] | None = None,
        properties: dict[str, list[str]] | None = None,
    ):
        self.node_types = node_types or self.DEFAULT_NODE_TYPES
        self.edge_types = edge_types or self.DEFAULT_EDGE_TYPES
        self.properties = properties or self.DEFAULT_PROPERTIES

    @classmethod
    def default(cls) -> VKGSchema:
        """Get default VKG schema."""
        return cls()

    @classmethod
    def from_graph(cls, graph) -> VKGSchema:
        """Extract schema from a knowledge graph."""
        # Extract unique node types
        node_types = list(set(node.type for node in graph.nodes.values()))

        # Extract unique edge types
        edge_types = list(set(edge.type for edge in graph.edges.values()))

        # Extract properties by node type
        properties: dict[str, set[str]] = {}
        for node in graph.nodes.values():
            if node.type not in properties:
                properties[node.type] = set()
            properties[node.type].update(node.properties.keys())

        # Convert sets to sorted lists
        properties_dict = {k: sorted(v) for k, v in properties.items()}

        return cls(node_types, edge_types, properties_dict)

    def normalize_type(self, type_name: str) -> str:
        """Normalize type name using aliases."""
        return self.TYPE_ALIASES.get(type_name.lower(), type_name)

    def has_node_type(self, node_type: str) -> bool:
        """Check if node type exists (including aliases)."""
        normalized = self.normalize_type(node_type)
        if normalized.startswith("_"):
            # Special markers like _EDGE_QUERY, _PATTERN_QUERY
            return True
        return normalized in self.node_types

    def has_edge_type(self, edge_type: str) -> bool:
        """Check if edge type exists."""
        return edge_type in self.edge_types

    def has_property(self, node_type: str, property_name: str) -> bool:
        """Check if property exists for node type."""
        if node_type not in self.properties:
            return False
        return property_name in self.properties[node_type]

    def get_properties(self, node_type: str) -> list[str]:
        """Get all properties for a node type."""
        return self.properties.get(node_type, [])

    def fuzzy_match_node_type(self, query: str, threshold: int = 2) -> str | None:
        """Find closest matching node type using Levenshtein distance."""
        return self._fuzzy_match(query, self.node_types, threshold)

    def fuzzy_match_edge_type(self, query: str, threshold: int = 2) -> str | None:
        """Find closest matching edge type."""
        return self._fuzzy_match(query, self.edge_types, threshold)

    def fuzzy_match_property(self, node_type: str, query: str, threshold: int = 2) -> str | None:
        """Find closest matching property for a node type."""
        properties = self.get_properties(node_type)
        return self._fuzzy_match(query, properties, threshold)

    def _fuzzy_match(self, query: str, candidates: list[str], threshold: int) -> str | None:
        """Fuzzy match using Levenshtein distance."""
        query_lower = query.lower()
        best_match = None
        best_distance = threshold + 1

        for candidate in candidates:
            distance = self._levenshtein_distance(query_lower, candidate.lower())
            if distance < best_distance:
                best_distance = distance
                best_match = candidate

        return best_match if best_distance <= threshold else None

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return VKGSchema._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # j+1 instead of j since previous_row and current_row are one character longer than s2
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]


class SemanticAnalyzer(ASTVisitor):
    """Semantic analyzer for VQL 2.0."""

    def __init__(self, schema: VKGSchema | None = None, pattern_dir: Path | None = None):
        self.schema = schema or VKGSchema.default()
        self.pattern_dir = pattern_dir
        self.errors: list[SemanticError] = []
        self.warnings: list[SemanticWarning] = []
        self.symbol_table: dict[str, Any] = {}  # For WITH clause variables
        self.current_node_type: str | None = None  # Track current context

    def analyze(self, ast: QueryNode) -> None:
        """Analyze AST and collect errors/warnings."""
        self.errors.clear()
        self.warnings.clear()
        self.symbol_table.clear()
        ast.accept(self)

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    # ========================================
    # Visitor Methods
    # ========================================

    def visit_describe_query(self, node: DescribeQuery) -> None:
        """Validate DESCRIBE query."""
        if node.target == "PROPERTIES" and node.for_type:
            # Validate node type
            if not self.schema.has_node_type(node.for_type):
                suggestion = self.schema.fuzzy_match_node_type(node.for_type)
                self.errors.append(
                    SemanticError(
                        message=f"Unknown node type '{node.for_type}'",
                        node=node,
                        hint=f"Did you mean '{suggestion}'?" if suggestion else "Use DESCRIBE TYPES to see available types",
                        suggestions=[suggestion] if suggestion else [],
                        auto_fix=f"DESCRIBE PROPERTIES FOR {suggestion}" if suggestion else None,
                        confidence=0.95 if suggestion else 0.0,
                    )
                )

    def visit_find_query(self, node: FindQuery) -> None:
        """Validate FIND query."""
        # Process WITH clauses first
        for with_clause in node.with_clauses:
            self.symbol_table[with_clause.name] = with_clause
            if with_clause.subquery:
                with_clause.subquery.accept(self)

        # Validate target types
        for target_type in node.target_types:
            if not self.schema.has_node_type(target_type) and not self.schema.has_edge_type(target_type):
                # Try fuzzy matching
                node_suggestion = self.schema.fuzzy_match_node_type(target_type)
                edge_suggestion = self.schema.fuzzy_match_edge_type(target_type)

                suggestion = node_suggestion or edge_suggestion
                self.errors.append(
                    SemanticError(
                        message=f"Unknown type '{target_type}'",
                        node=node,
                        hint=f"Did you mean '{suggestion}'?" if suggestion else "Use DESCRIBE TYPES to see available types",
                        suggestions=[suggestion] if suggestion else [],
                        confidence=0.95 if suggestion else 0.0,
                    )
                )
            else:
                # Set current context for property validation (use normalized type)
                if self.schema.has_node_type(target_type):
                    self.current_node_type = self.schema.normalize_type(target_type)

        # Validate WHERE clause
        if node.where_clause:
            node.where_clause.accept(self)

        # Validate RETURN clause
        if node.return_clause:
            for item in node.return_clause.items:
                if item.expression:
                    item.expression.accept(self)

    def visit_match_query(self, node: MatchQuery) -> None:
        """Validate MATCH query."""
        # Process WITH clauses
        for with_clause in node.with_clauses:
            self.symbol_table[with_clause.name] = with_clause
            if with_clause.subquery:
                with_clause.subquery.accept(self)

        # Validate patterns
        for pattern in node.patterns:
            self._validate_pattern_sequence(pattern)

        # Validate optional patterns
        for pattern in node.optional_patterns:
            self._validate_pattern_sequence(pattern)

        # Validate WHERE clause
        if node.where_clause:
            node.where_clause.accept(self)

        # Validate RETURN clause
        if node.return_clause:
            for item in node.return_clause.items:
                if item.expression:
                    item.expression.accept(self)

    def _validate_pattern_sequence(self, pattern) -> None:
        """Validate pattern sequence."""
        # Validate start node
        if pattern.start_node:
            self._validate_node_pattern(pattern.start_node)

        # Validate segments (relationship + node pairs)
        for rel, node in pattern.segments:
            self._validate_relationship_pattern(rel)
            self._validate_node_pattern(node)

    def _validate_node_pattern(self, node: NodePattern) -> None:
        """Validate node pattern."""
        if node.node_type and not self.schema.has_node_type(node.node_type):
            suggestion = self.schema.fuzzy_match_node_type(node.node_type)
            self.errors.append(
                SemanticError(
                    message=f"Unknown node type '{node.node_type}'",
                    node=node,
                    hint=f"Did you mean '{suggestion}'?" if suggestion else None,
                    suggestions=[suggestion] if suggestion else [],
                    confidence=0.95 if suggestion else 0.0,
                )
            )

        # Validate IN cte_name
        if node.in_cte and node.in_cte not in self.symbol_table:
            self.errors.append(
                SemanticError(
                    message=f"Unknown CTE '{node.in_cte}'",
                    node=node,
                    hint="CTE must be defined in WITH clause before use",
                )
            )

    def _validate_relationship_pattern(self, rel) -> None:
        """Validate relationship pattern."""
        if rel.edge_type and not self.schema.has_edge_type(rel.edge_type):
            suggestion = self.schema.fuzzy_match_edge_type(rel.edge_type)
            self.errors.append(
                SemanticError(
                    message=f"Unknown edge type '{rel.edge_type}'",
                    node=rel,
                    hint=f"Did you mean '{suggestion}'?" if suggestion else None,
                    suggestions=[suggestion] if suggestion else [],
                    confidence=0.95 if suggestion else 0.0,
                )
            )

    def visit_flow_query(self, node: FlowQuery) -> None:
        """Validate FLOW query."""
        # Process WITH clauses
        for with_clause in node.with_clauses:
            self.symbol_table[with_clause.name] = with_clause

        # Validate source and sink patterns
        if node.source and node.source.pattern:
            self._validate_node_pattern(node.source.pattern)
        if node.sink and node.sink.pattern:
            self._validate_node_pattern(node.sink.pattern)
        if node.through and node.through.pattern:
            self._validate_node_pattern(node.through.pattern)

        # Validate WHERE clause
        if node.where_clause:
            node.where_clause.accept(self)

    def visit_pattern_query(self, node: PatternQuery) -> None:
        """Validate PATTERN query."""
        # TODO: Validate pattern IDs against pattern store
        # For now, just accept any pattern ID
        pass

    def visit_identifier(self, node: Identifier) -> None:
        """Validate identifier (property reference)."""
        if self.current_node_type:
            # Check if property exists for current node type
            if not self.schema.has_property(self.current_node_type, node.name):
                suggestion = self.schema.fuzzy_match_property(self.current_node_type, node.name)
                available_props = self.schema.get_properties(self.current_node_type)

                self.errors.append(
                    SemanticError(
                        message=f"Unknown property '{node.name}' for type '{self.current_node_type}'",
                        node=node,
                        hint=f"Did you mean '{suggestion}'?" if suggestion else f"Available properties: {', '.join(available_props[:5])}...",
                        suggestions=[suggestion] if suggestion else [],
                        auto_fix=suggestion,
                        confidence=0.95 if suggestion else 0.0,
                    )
                )

    def visit_binary_op(self, node: BinaryOp) -> None:
        """Validate binary operation."""
        # Validate left and right operands
        if node.left:
            node.left.accept(self)
        if node.right:
            node.right.accept(self)

        # Check for contradictory conditions
        if node.operator == "AND":
            self._check_contradictory_conditions(node)

    def _check_contradictory_conditions(self, node: BinaryOp) -> None:
        """Check for contradictory conditions like 'x = a AND x = b'."""
        # Simplified check - can be expanded
        if isinstance(node.left, BinaryOp) and isinstance(node.right, BinaryOp):
            if (
                node.left.operator in ("EQ", "=")
                and node.right.operator in ("EQ", "=")
                and isinstance(node.left.left, Identifier)
                and isinstance(node.right.left, Identifier)
                and node.left.left.name == node.right.left.name
            ):
                self.warnings.append(
                    SemanticWarning(
                        message=f"Contradictory conditions: {node.left.left.name} cannot equal two different values",
                        node=node,
                        hint="This will always return empty results. Use OR if you want either condition.",
                    )
                )

    def visit_where_clause(self, node: WhereClause) -> None:
        """Validate WHERE clause by visiting its condition."""
        if node.condition:
            node.condition.accept(self)

    def visit_exists_expression(self, node: ExistsExpression) -> None:
        """Validate EXISTS expression."""
        if node.subquery:
            node.subquery.accept(self)

    def get_error_report(self) -> str:
        """Generate formatted error report."""
        if not self.errors and not self.warnings:
            return "No errors or warnings"

        report = []

        if self.errors:
            report.append(f"Errors ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                report.append(f"\n{i}. Line {error.line}, column {error.column}: {error.message}")
                if error.hint:
                    report.append(f"   Hint: {error.hint}")
                if error.suggestions:
                    report.append(f"   Suggestions: {', '.join(error.suggestions)}")
                if error.auto_fix:
                    report.append(f"   Auto-fix: {error.auto_fix}")

        if self.warnings:
            report.append(f"\n\nWarnings ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                report.append(f"\n{i}. {warning.message}")
                if warning.hint:
                    report.append(f"   Hint: {warning.hint}")

        return "\n".join(report)
