"""VQL 2.0 Abstract Syntax Tree (AST) definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class ASTNodeType(Enum):
    """AST node types."""

    # Queries
    DESCRIBE_QUERY = auto()
    FIND_QUERY = auto()
    MATCH_QUERY = auto()
    FLOW_QUERY = auto()
    PATTERN_QUERY = auto()

    # Clauses
    WITH_CLAUSE = auto()
    WHERE_CLAUSE = auto()
    RETURN_CLAUSE = auto()
    GROUP_BY_CLAUSE = auto()
    HAVING_CLAUSE = auto()
    ORDER_BY_CLAUSE = auto()
    LIMIT_CLAUSE = auto()
    OFFSET_CLAUSE = auto()

    # Expressions
    IDENTIFIER = auto()
    LITERAL = auto()
    BINARY_OP = auto()
    UNARY_OP = auto()
    FUNCTION_CALL = auto()
    CASE_EXPRESSION = auto()
    PATH_EXPRESSION = auto()
    SUBQUERY = auto()

    # Patterns
    NODE_PATTERN = auto()
    RELATIONSHIP_PATTERN = auto()
    PATTERN_SEQUENCE = auto()

    # Flow
    FLOW_SOURCE = auto()
    FLOW_SINK = auto()
    FLOW_THROUGH = auto()
    FLOW_SANITIZER = auto()

    # Set operations
    UNION = auto()
    INTERSECT = auto()
    EXCEPT = auto()


@dataclass
class ASTNode:
    """Base AST node."""

    node_type: ASTNodeType
    line: int = 0
    column: int = 0

    def accept(self, visitor: ASTVisitor) -> Any:
        """Accept a visitor (Visitor pattern)."""
        method_name = f"visit_{self.node_type.name.lower()}"
        method = getattr(visitor, method_name, None)
        if method:
            return method(self)
        return visitor.visit_generic(self)


@dataclass
class QueryNode(ASTNode):
    """Base query node."""

    with_clauses: list[WithClause] = field(default_factory=list)
    where_clause: WhereClause | None = None
    return_clause: ReturnClause | None = None
    group_by: GroupByClause | None = None
    having: HavingClause | None = None
    order_by: OrderByClause | None = None
    limit: LimitClause | None = None
    offset: OffsetClause | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class DescribeQuery(QueryNode):
    """DESCRIBE query for schema introspection."""

    target: str = "TYPES"  # TYPES, PROPERTIES, EDGES, PATTERNS, LENSES, SCHEMA
    for_type: str | None = None  # For PROPERTIES FOR <type>


@dataclass
class FindQuery(QueryNode):
    """FIND query for simple node/edge searches."""

    target_types: list[str] = field(default_factory=list)  # Node or edge types
    is_edge_query: bool = False


@dataclass
class MatchQuery(QueryNode):
    """MATCH query for graph pattern matching."""

    patterns: list[PatternSequence] = field(default_factory=list)
    optional_patterns: list[PatternSequence] = field(default_factory=list)


@dataclass
class FlowQuery(QueryNode):
    """FLOW query for dataflow analysis."""

    direction: str = "FORWARD"  # FORWARD, BACKWARD
    source: FlowSource | None = None
    sink: FlowSink | None = None
    through: FlowThrough | None = None
    exclude_sources: list[str] = field(default_factory=list)
    sanitizer: FlowSanitizer | None = None


@dataclass
class PatternQuery(QueryNode):
    """PATTERN query for vulnerability pattern matching."""

    pattern_ids: list[str] = field(default_factory=list)
    lens: list[str] = field(default_factory=list)
    severity: list[str] = field(default_factory=list)


# Clauses

@dataclass
class WithClause(ASTNode):
    """WITH clause (CTE)."""

    name: str = ""
    subquery: QueryNode | None = None


@dataclass
class WhereClause(ASTNode):
    """WHERE clause."""

    condition: Expression | None = None


@dataclass
class ReturnClause(ASTNode):
    """RETURN clause."""

    items: list[ReturnItem] = field(default_factory=list)
    return_all: bool = False
    special_return: str | None = None  # SOURCES, SINKS, PATHS, etc.


@dataclass
class ReturnItem(ASTNode):
    """Single RETURN item."""

    expression: Expression | None = None
    alias: str | None = None


@dataclass
class GroupByClause(ASTNode):
    """GROUP BY clause."""

    expressions: list[Expression] = field(default_factory=list)


@dataclass
class HavingClause(ASTNode):
    """HAVING clause."""

    condition: Expression | None = None


@dataclass
class OrderByClause(ASTNode):
    """ORDER BY clause."""

    items: list[OrderByItem] = field(default_factory=list)


@dataclass
class OrderByItem(ASTNode):
    """Single ORDER BY item."""

    expression: Expression | None = None
    direction: str = "ASC"  # ASC or DESC


@dataclass
class LimitClause(ASTNode):
    """LIMIT clause."""

    value: int = 50


@dataclass
class OffsetClause(ASTNode):
    """OFFSET clause."""

    value: int = 0


# Expressions

@dataclass
class Expression(ASTNode):
    """Base expression."""

    pass


@dataclass
class Identifier(Expression):
    """Identifier expression."""

    name: str = ""


@dataclass
class Literal(Expression):
    """Literal value."""

    value: Any = None
    literal_type: str = "string"  # string, integer, float, boolean, null, array, object


@dataclass
class BinaryOp(Expression):
    """Binary operation."""

    operator: str = ""  # =, !=, >, <, >=, <=, AND, OR, IN, etc.
    left: Expression | None = None
    right: Expression | None = None


@dataclass
class UnaryOp(Expression):
    """Unary operation."""

    operator: str = ""  # NOT, -, etc.
    operand: Expression | None = None


@dataclass
class FunctionCall(Expression):
    """Function call."""

    name: str = ""
    arguments: list[Expression] = field(default_factory=list)


@dataclass
class CaseExpression(Expression):
    """CASE expression."""

    test_expression: Expression | None = None
    when_clauses: list[WhenClause] = field(default_factory=list)
    else_expression: Expression | None = None


@dataclass
class WhenClause(ASTNode):
    """WHEN clause in CASE expression."""

    condition: Expression | None = None
    result: Expression | None = None


@dataclass
class PathExpression(Expression):
    """Path expression for nested property access."""

    base: Expression | None = None
    path: list[str | Expression] = field(default_factory=list)  # ["property", 0, "nested"]


@dataclass
class Subquery(Expression):
    """Subquery expression."""

    query: QueryNode | None = None


@dataclass
class ExistsExpression(Expression):
    """EXISTS expression."""

    subquery: QueryNode | None = None
    negated: bool = False


# Patterns

@dataclass
class NodePattern(ASTNode):
    """Node pattern in MATCH."""

    variable: str | None = None
    node_type: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    in_cte: str | None = None  # For "IN cte_name"


@dataclass
class RelationshipPattern(ASTNode):
    """Relationship pattern in MATCH."""

    variable: str | None = None
    edge_type: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    direction: str = "out"  # out (->), in (<-), any (-)
    min_length: int | None = None
    max_length: int | None = None


@dataclass
class PatternSequence(ASTNode):
    """Sequence of node and relationship patterns."""

    path_variable: str | None = None  # For "path = (...)"
    start_node: NodePattern | None = None
    segments: list[tuple[RelationshipPattern, NodePattern]] = field(default_factory=list)


# Flow

@dataclass
class FlowSource(ASTNode):
    """Flow source specification."""

    pattern: NodePattern | None = None
    subquery: QueryNode | None = None


@dataclass
class FlowSink(ASTNode):
    """Flow sink specification."""

    pattern: NodePattern | None = None
    subquery: QueryNode | None = None
    is_any: bool = False


@dataclass
class FlowThrough(ASTNode):
    """Flow through specification."""

    pattern: NodePattern | None = None


@dataclass
class FlowSanitizer(ASTNode):
    """Flow sanitizer requirement."""

    condition: Expression | None = None
    mode: str = "ALL"  # ALL or ANY


# Set Operations

@dataclass
class SetOperation(QueryNode):
    """Set operation (UNION, INTERSECT, EXCEPT)."""

    operation: str = "UNION"  # UNION, INTERSECT, EXCEPT
    left: QueryNode | None = None
    right: QueryNode | None = None


# Visitor Pattern

class ASTVisitor:
    """Base visitor for AST traversal."""

    def visit_generic(self, node: ASTNode) -> Any:
        """Generic visit method."""
        pass

    def visit_describe_query(self, node: DescribeQuery) -> Any:
        pass

    def visit_find_query(self, node: FindQuery) -> Any:
        pass

    def visit_match_query(self, node: MatchQuery) -> Any:
        pass

    def visit_flow_query(self, node: FlowQuery) -> Any:
        pass

    def visit_pattern_query(self, node: PatternQuery) -> Any:
        pass

    def visit_identifier(self, node: Identifier) -> Any:
        pass

    def visit_literal(self, node: Literal) -> Any:
        pass

    def visit_binary_op(self, node: BinaryOp) -> Any:
        pass

    def visit_unary_op(self, node: UnaryOp) -> Any:
        pass

    def visit_function_call(self, node: FunctionCall) -> Any:
        pass


class ASTPrinter(ASTVisitor):
    """Pretty-print AST for debugging."""

    def __init__(self):
        self.indent = 0

    def print_node(self, node: ASTNode) -> str:
        """Print AST node recursively."""
        indent_str = "  " * self.indent
        node_name = node.__class__.__name__
        result = f"{indent_str}{node_name}\n"

        self.indent += 1
        for key, value in node.__dict__.items():
            if key in ("node_type", "line", "column"):
                continue
            if value is None:
                continue
            if isinstance(value, list) and len(value) == 0:
                continue

            if isinstance(value, ASTNode):
                result += f"{indent_str}  {key}:\n"
                result += self.print_node(value)
            elif isinstance(value, list):
                if all(isinstance(item, ASTNode) for item in value):
                    result += f"{indent_str}  {key}:\n"
                    for item in value:
                        result += self.print_node(item)
                else:
                    result += f"{indent_str}  {key}: {value}\n"
            else:
                result += f"{indent_str}  {key}: {value}\n"
        self.indent -= 1

        return result
