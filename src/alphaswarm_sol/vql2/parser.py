"""VQL 2.0 Parser - Convert tokens to AST with error recovery."""

from __future__ import annotations

from typing import Any

from alphaswarm_sol.vql2.lexer import Token, TokenType
from alphaswarm_sol.vql2.ast import (
    ASTNode,
    ASTNodeType,
    BinaryOp,
    CaseExpression,
    DescribeQuery,
    ExistsExpression,
    Expression,
    FindQuery,
    FlowQuery,
    FlowSanitizer,
    FlowSink,
    FlowSource,
    FlowThrough,
    FunctionCall,
    GroupByClause,
    HavingClause,
    Identifier,
    LimitClause,
    Literal,
    MatchQuery,
    NodePattern,
    OffsetClause,
    OrderByClause,
    OrderByItem,
    PathExpression,
    PatternQuery,
    PatternSequence,
    QueryNode,
    RelationshipPattern,
    ReturnClause,
    ReturnItem,
    SetOperation,
    Subquery,
    UnaryOp,
    WhenClause,
    WhereClause,
    WithClause,
)


class ParseError(Exception):
    """Parse error with position and hint."""

    def __init__(
        self,
        message: str,
        token: Token | None = None,
        hint: str | None = None,
        suggestion: str | None = None,
    ):
        self.message = message
        self.token = token
        self.hint = hint
        self.suggestion = suggestion
        self.line = token.line if token else 0
        self.column = token.column if token else 0

        error_msg = f"Line {self.line}, column {self.column}: {message}"
        if hint:
            error_msg += f"\nHint: {hint}"
        if suggestion:
            error_msg += f"\nSuggestion: {suggestion}"

        super().__init__(error_msg)


class Parser:
    """Recursive descent parser for VQL 2.0."""

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errors: list[ParseError] = []

    def current(self) -> Token:
        """Get current token."""
        if self.pos >= len(self.tokens):
            return self.tokens[-1]  # EOF
        return self.tokens[self.pos]

    def peek(self, offset: int = 1) -> Token:
        """Peek ahead at token."""
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return self.tokens[-1]  # EOF
        return self.tokens[pos]

    def advance(self) -> Token:
        """Move to next token."""
        token = self.current()
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token

    def match(self, *types: TokenType) -> bool:
        """Check if current token matches any of the given types."""
        return self.current().type in types

    def consume(self, token_type: TokenType, error_msg: str | None = None) -> Token:
        """Consume a token of the given type or raise error."""
        if not self.match(token_type):
            if error_msg is None:
                error_msg = f"Expected {token_type.name}, got {self.current().type.name}"
            raise ParseError(error_msg, self.current())
        return self.advance()

    def synchronize(self) -> None:
        """Synchronize after error by advancing to next statement."""
        while not self.match(TokenType.EOF):
            # Synchronization points: major keywords
            if self.match(
                TokenType.FIND,
                TokenType.MATCH,
                TokenType.FLOW,
                TokenType.PATTERN,
                TokenType.DESCRIBE,
                TokenType.WHERE,
                TokenType.RETURN,
            ):
                return
            self.advance()

    # ========================================
    # Main Entry Point
    # ========================================

    def parse(self) -> QueryNode:
        """Parse a VQL 2.0 query."""
        try:
            if self.match(TokenType.DESCRIBE):
                return self.parse_describe()
            elif self.match(TokenType.FIND):
                return self.parse_find()
            elif self.match(TokenType.MATCH):
                return self.parse_match()
            elif self.match(TokenType.FLOW):
                return self.parse_flow()
            elif self.match(TokenType.PATTERN):
                return self.parse_pattern()
            else:
                raise ParseError(
                    "Expected query keyword (DESCRIBE, FIND, MATCH, FLOW, PATTERN)",
                    self.current(),
                    hint="Start your query with one of these keywords",
                )
        except ParseError as e:
            self.errors.append(e)
            self.synchronize()
            raise

    # ========================================
    # DESCRIBE Query
    # ========================================

    def parse_describe(self) -> DescribeQuery:
        """Parse DESCRIBE query."""
        token = self.consume(TokenType.DESCRIBE)
        query = DescribeQuery(
            node_type=ASTNodeType.DESCRIBE_QUERY,
            line=token.line,
            column=token.column,
        )

        if self.match(TokenType.TYPES):
            self.advance()
            query.target = "TYPES"
        elif self.match(TokenType.PROPERTIES):
            self.advance()
            query.target = "PROPERTIES"
            if self.match(TokenType.FOR):
                self.advance()
                type_token = self.consume(TokenType.IDENTIFIER, "Expected node type after FOR")
                query.for_type = type_token.value
        elif self.match(TokenType.EDGES):
            self.advance()
            query.target = "EDGES"
        elif self.match(TokenType.PATTERNS):
            self.advance()
            query.target = "PATTERNS"
        elif self.match(TokenType.LENSES):
            self.advance()
            query.target = "LENSES"
        elif self.match(TokenType.SCHEMA):
            self.advance()
            query.target = "SCHEMA"
        else:
            raise ParseError(
                "Expected TYPES, PROPERTIES, EDGES, PATTERNS, LENSES, or SCHEMA",
                self.current(),
                hint="Use 'DESCRIBE TYPES' to see available node types",
            )

        return query

    # ========================================
    # FIND Query
    # ========================================

    def parse_find(self) -> FindQuery:
        """Parse FIND query."""
        token = self.consume(TokenType.FIND)
        query = FindQuery(
            node_type=ASTNodeType.FIND_QUERY,
            line=token.line,
            column=token.column,
        )

        # WITH clause (optional)
        if self.match(TokenType.WITH):
            query.with_clauses = self.parse_with_clauses()

        # Target types
        query.target_types = self.parse_target_types()

        # WHERE clause (optional)
        if self.match(TokenType.WHERE):
            query.where_clause = self.parse_where()

        # RETURN clause (optional)
        if self.match(TokenType.RETURN):
            query.return_clause = self.parse_return()

        # Modifiers
        self.parse_modifiers(query)

        return query

    def parse_with_clauses(self) -> list[WithClause]:
        """Parse WITH clauses (CTEs)."""
        self.consume(TokenType.WITH)
        clauses = []

        while True:
            name_token = self.consume(TokenType.IDENTIFIER, "Expected CTE name")
            self.consume(TokenType.AS, "Expected AS after CTE name")
            self.consume(TokenType.LPAREN, "Expected '(' after AS")

            # Parse subquery
            subquery = self.parse()

            self.consume(TokenType.RPAREN, "Expected ')' after subquery")

            clauses.append(
                WithClause(
                    node_type=name_token.type,
                    name=name_token.value,
                    subquery=subquery,
                    line=name_token.line,
                    column=name_token.column,
                )
            )

            if not self.match(TokenType.COMMA):
                break
            self.advance()

        return clauses

    # Token types that can be used as target types in FIND/MATCH queries
    TARGET_TYPE_TOKENS = {
        TokenType.IDENTIFIER,
        TokenType.FUNCTIONS,
        TokenType.EDGES,
        TokenType.NODES,
        TokenType.PATTERNS,
    }

    def parse_target_types(self) -> list[str]:
        """Parse target node/edge types.

        Accepts both identifiers and certain keywords that double as type names
        (e.g., functions, edges, nodes, contracts).
        """
        types = []

        while True:
            if self.current().type in self.TARGET_TYPE_TOKENS:
                type_token = self.advance()
                # Use the value for identifiers, the type name for keywords
                if type_token.type == TokenType.IDENTIFIER:
                    types.append(type_token.value)
                else:
                    types.append(type_token.type.name.lower())
            else:
                raise ParseError(
                    "Expected node or edge type (e.g., functions, contracts, edges)",
                    self.current()
                )

            if not self.match(TokenType.COMMA):
                break
            self.advance()

        return types

    # ========================================
    # WHERE Clause
    # ========================================

    def parse_where(self) -> WhereClause:
        """Parse WHERE clause."""
        token = self.consume(TokenType.WHERE)
        condition = self.parse_condition()

        return WhereClause(
            node_type=ASTNodeType.WHERE_CLAUSE,
            condition=condition,
            line=token.line,
            column=token.column,
        )

    def parse_condition(self) -> Expression:
        """Parse condition expression with operator precedence."""
        return self.parse_or()

    def parse_or(self) -> Expression:
        """Parse OR expression."""
        left = self.parse_and()

        while self.match(TokenType.OR):
            op_token = self.advance()
            right = self.parse_and()
            left = BinaryOp(
                node_type=ASTNodeType.BINARY_OP,
                operator="OR",
                left=left,
                right=right,
                line=op_token.line,
                column=op_token.column,
            )

        return left

    def parse_and(self) -> Expression:
        """Parse AND expression."""
        left = self.parse_not()

        while self.match(TokenType.AND):
            op_token = self.advance()
            right = self.parse_not()
            left = BinaryOp(
                node_type=ASTNodeType.BINARY_OP,
                operator="AND",
                left=left,
                right=right,
                line=op_token.line,
                column=op_token.column,
            )

        return left

    def parse_not(self) -> Expression:
        """Parse NOT expression."""
        if self.match(TokenType.NOT):
            op_token = self.advance()

            # Check for NOT EXISTS
            if self.match(TokenType.EXISTS):
                return self.parse_exists(negated=True)

            # Check for NOT IN
            operand = self.parse_comparison()
            return UnaryOp(
                node_type=ASTNodeType.UNARY_OP,
                operator="NOT",
                operand=operand,
                line=op_token.line,
                column=op_token.column,
            )

        return self.parse_comparison()

    def parse_comparison(self) -> Expression:
        """Parse comparison expression."""
        left = self.parse_primary_expression()

        # Check for comparison operators
        if self.match(
            TokenType.EQ,
            TokenType.NEQ,
            TokenType.GT,
            TokenType.LT,
            TokenType.GTE,
            TokenType.LTE,
            TokenType.IN,
            TokenType.REGEX,
            TokenType.LIKE,
            TokenType.CONTAINS,
            TokenType.CONTAINS_ANY,
            TokenType.CONTAINS_ALL,
        ):
            op_token = self.advance()
            right = self.parse_primary_expression()

            return BinaryOp(
                node_type=ASTNodeType.BINARY_OP,
                operator=op_token.type.name,
                left=left,
                right=right,
                line=op_token.line,
                column=op_token.column,
            )

        # No operator - treat as boolean property
        return left

    def parse_primary_expression(self) -> Expression:
        """Parse primary expression."""
        # Parenthesized expression
        if self.match(TokenType.LPAREN):
            self.advance()

            # Check for subquery
            if self.match(TokenType.FIND, TokenType.MATCH, TokenType.FLOW, TokenType.PATTERN):
                subquery = self.parse()
                self.consume(TokenType.RPAREN)
                return Subquery(node_type=ASTNodeType.SUBQUERY, query=subquery)

            # Regular parenthesized expression
            expr = self.parse_condition()
            self.consume(TokenType.RPAREN)
            return expr

        # EXISTS
        if self.match(TokenType.EXISTS):
            return self.parse_exists()

        # CASE expression
        if self.match(TokenType.CASE):
            return self.parse_case()

        # Function call
        if self.match(TokenType.COUNT, TokenType.SUM, TokenType.AVG, TokenType.MAX, TokenType.MIN, TokenType.COLLECT):
            return self.parse_function_call()

        # Literal
        if self.match(TokenType.STRING, TokenType.INTEGER, TokenType.FLOAT, TokenType.BOOLEAN, TokenType.NULL):
            return self.parse_literal()

        # Array literal
        if self.match(TokenType.LBRACKET):
            return self.parse_array_literal()

        # Identifier or path expression
        if self.match(TokenType.IDENTIFIER):
            return self.parse_identifier_or_path()

        raise ParseError("Expected expression", self.current())

    def parse_exists(self, negated: bool = False) -> ExistsExpression:
        """Parse EXISTS expression."""
        token = self.consume(TokenType.EXISTS)
        self.consume(TokenType.LPAREN)
        subquery = self.parse()
        self.consume(TokenType.RPAREN)

        return ExistsExpression(
            node_type=token.type,
            subquery=subquery,
            negated=negated,
            line=token.line,
            column=token.column,
        )

    def parse_case(self) -> CaseExpression:
        """Parse CASE expression."""
        token = self.consume(TokenType.CASE)
        case_expr = CaseExpression(node_type=ASTNodeType.CASE_EXPRESSION, line=token.line, column=token.column)

        # Optional test expression
        if not self.match(TokenType.WHEN):
            case_expr.test_expression = self.parse_condition()

        # WHEN clauses
        while self.match(TokenType.WHEN):
            self.advance()
            condition = self.parse_condition()
            self.consume(TokenType.THEN)
            result = self.parse_primary_expression()

            case_expr.when_clauses.append(
                WhenClause(node_type=TokenType.WHEN, condition=condition, result=result)
            )

        # ELSE clause (optional)
        if self.match(TokenType.ELSE):
            self.advance()
            case_expr.else_expression = self.parse_primary_expression()

        self.consume(TokenType.END)
        return case_expr

    def parse_function_call(self) -> FunctionCall:
        """Parse function call."""
        name_token = self.advance()
        self.consume(TokenType.LPAREN)

        func = FunctionCall(
            node_type=ASTNodeType.FUNCTION_CALL,
            name=name_token.type.name,
            line=name_token.line,
            column=name_token.column,
        )

        # Parse arguments
        if not self.match(TokenType.RPAREN):
            while True:
                func.arguments.append(self.parse_condition())
                if not self.match(TokenType.COMMA):
                    break
                self.advance()

        self.consume(TokenType.RPAREN)
        return func

    def parse_literal(self) -> Literal:
        """Parse literal value."""
        token = self.advance()

        if token.type == TokenType.STRING:
            return Literal(
                node_type=ASTNodeType.LITERAL,
                value=token.value,
                literal_type="string",
                line=token.line,
                column=token.column,
            )
        elif token.type == TokenType.INTEGER:
            return Literal(
                node_type=ASTNodeType.LITERAL,
                value=token.value,
                literal_type="integer",
                line=token.line,
                column=token.column,
            )
        elif token.type == TokenType.FLOAT:
            return Literal(
                node_type=ASTNodeType.LITERAL,
                value=token.value,
                literal_type="float",
                line=token.line,
                column=token.column,
            )
        elif token.type == TokenType.BOOLEAN:
            return Literal(
                node_type=ASTNodeType.LITERAL,
                value=token.value,
                literal_type="boolean",
                line=token.line,
                column=token.column,
            )
        elif token.type == TokenType.NULL:
            return Literal(
                node_type=ASTNodeType.LITERAL,
                value=None,
                literal_type="null",
                line=token.line,
                column=token.column,
            )

        raise ParseError(f"Unexpected literal type: {token.type}", token)

    def parse_array_literal(self) -> Literal:
        """Parse array literal."""
        token = self.consume(TokenType.LBRACKET)
        values = []

        if not self.match(TokenType.RBRACKET):
            while True:
                lit = self.parse_literal()
                values.append(lit.value)
                if not self.match(TokenType.COMMA):
                    break
                self.advance()

        self.consume(TokenType.RBRACKET)

        return Literal(
            node_type=ASTNodeType.LITERAL,
            value=values,
            literal_type="array",
            line=token.line,
            column=token.column,
        )

    def parse_identifier_or_path(self) -> Expression:
        """Parse identifier or path expression."""
        token = self.advance()
        base = Identifier(node_type=ASTNodeType.IDENTIFIER, name=token.value, line=token.line, column=token.column)

        # Check for path expression (a.b.c or a[0])
        path_parts = []
        while self.match(TokenType.DOT, TokenType.LBRACKET):
            if self.match(TokenType.DOT):
                self.advance()
                name_token = self.consume(TokenType.IDENTIFIER)
                path_parts.append(name_token.value)
            elif self.match(TokenType.LBRACKET):
                self.advance()
                index_expr = self.parse_condition()
                self.consume(TokenType.RBRACKET)
                path_parts.append(index_expr)

        if path_parts:
            return PathExpression(
                node_type=ASTNodeType.PATH_EXPRESSION, base=base, path=path_parts, line=token.line, column=token.column
            )

        return base

    # ========================================
    # RETURN Clause
    # ========================================

    def parse_return(self) -> ReturnClause:
        """Parse RETURN clause."""
        token = self.consume(TokenType.RETURN)
        return_clause = ReturnClause(node_type=token.type, line=token.line, column=token.column)

        # Check for special returns (SOURCES, SINKS, PATHS, etc.)
        if self.match(TokenType.SOURCES, TokenType.SINKS, TokenType.PATHS, TokenType.TAINTED, TokenType.UNSAFE, TokenType.INFLUENCERS):
            special_token = self.advance()
            return_clause.special_return = special_token.type.name
            return return_clause

        # Check for RETURN *
        if self.match(TokenType.STAR):
            self.advance()
            return_clause.return_all = True
            return return_clause

        # Parse return items
        while True:
            expr = self.parse_condition()

            alias = None
            if self.match(TokenType.AS):
                self.advance()
                alias_token = self.consume(TokenType.IDENTIFIER)
                alias = alias_token.value

            return_clause.items.append(
                ReturnItem(node_type=TokenType.RETURN, expression=expr, alias=alias)
            )

            if not self.match(TokenType.COMMA):
                break
            self.advance()

        return return_clause

    # ========================================
    # MATCH Query
    # ========================================

    def parse_match(self) -> MatchQuery:
        """Parse MATCH query."""
        token = self.consume(TokenType.MATCH)
        query = MatchQuery(node_type=ASTNodeType.MATCH_QUERY, line=token.line, column=token.column)

        # WITH clause (optional)
        if self.match(TokenType.WITH):
            query.with_clauses = self.parse_with_clauses()

        # Parse patterns
        query.patterns = self.parse_pattern_list()

        # OPTIONAL MATCH patterns
        while self.match(TokenType.OPTIONAL):
            self.advance()
            self.consume(TokenType.MATCH)
            query.optional_patterns.extend(self.parse_pattern_list())

        # WHERE clause
        if self.match(TokenType.WHERE):
            query.where_clause = self.parse_where()

        # RETURN clause
        if self.match(TokenType.RETURN):
            query.return_clause = self.parse_return()

        # Modifiers
        self.parse_modifiers(query)

        return query

    def parse_pattern_list(self) -> list[PatternSequence]:
        """Parse comma-separated pattern list."""
        patterns = []

        while True:
            patterns.append(self.parse_pattern_sequence())
            if not self.match(TokenType.COMMA):
                break
            self.advance()

        return patterns

    def parse_pattern_sequence(self) -> PatternSequence:
        """Parse pattern sequence: (a)-[:REL]->(b)-[:REL2]->(c)."""
        pattern = PatternSequence(node_type=TokenType.MATCH)

        # Check for path variable: path = (...)
        if self.match(TokenType.IDENTIFIER) and self.peek().type == TokenType.EQ:
            path_token = self.advance()
            pattern.path_variable = path_token.value
            self.consume(TokenType.EQ)

        # Parse start node
        pattern.start_node = self.parse_node_pattern()

        # Parse relationship-node segments
        while self.match(TokenType.DASH):
            rel = self.parse_relationship_pattern()
            node = self.parse_node_pattern()
            pattern.segments.append((rel, node))

        return pattern

    def parse_node_pattern(self) -> NodePattern:
        """Parse node pattern: (variable:Type {props})."""
        token = self.consume(TokenType.LPAREN)
        node = NodePattern(node_type=token.type, line=token.line, column=token.column)

        # Variable name (optional) - check if we have var:Type or just var or just :Type
        if self.match(TokenType.IDENTIFIER):
            # Look ahead to determine if this is a variable binding
            if self.peek().type == TokenType.COLON:
                # Pattern: (var:Type) - consume variable, then type
                var_token = self.advance()
                node.variable = var_token.value
            elif self.peek().type == TokenType.IN:
                # Pattern: (var IN cte) - consume variable
                var_token = self.advance()
                node.variable = var_token.value
            elif self.peek().type in (TokenType.RPAREN, TokenType.LBRACE):
                # Pattern: (var) or (var {props}) - just variable, no type
                var_token = self.advance()
                node.variable = var_token.value

        # Type (optional) - :Type
        if self.match(TokenType.COLON):
            self.advance()
            type_token = self.consume(TokenType.IDENTIFIER, "Expected type name after ':'")
            node.node_type = type_token.value

        # IN cte_name (optional)
        if self.match(TokenType.IN):
            self.advance()
            cte_token = self.consume(TokenType.IDENTIFIER)
            node.in_cte = cte_token.value

        # Properties (optional)
        if self.match(TokenType.LBRACE):
            node.properties = self.parse_properties_literal()

        self.consume(TokenType.RPAREN)
        return node

    def parse_relationship_pattern(self) -> RelationshipPattern:
        """Parse relationship pattern: -[:TYPE*1..3]->."""
        self.consume(TokenType.DASH)

        rel = RelationshipPattern(node_type=TokenType.DASH)
        direction = "any"

        # [...]
        if self.match(TokenType.LBRACKET):
            self.advance()

            # Variable (optional)
            if self.match(TokenType.IDENTIFIER):
                var_token = self.advance()
                rel.variable = var_token.value

            # Type (optional)
            if self.match(TokenType.COLON):
                self.advance()
                type_token = self.consume(TokenType.IDENTIFIER)
                rel.edge_type = type_token.value

            # Variable length *min..max
            if self.match(TokenType.STAR):
                self.advance()
                if self.match(TokenType.INTEGER):
                    min_token = self.advance()
                    rel.min_length = min_token.value

                    if self.match(TokenType.DOTDOT):
                        self.advance()
                        max_token = self.consume(TokenType.INTEGER)
                        rel.max_length = max_token.value

            # Properties (optional)
            if self.match(TokenType.LBRACE):
                rel.properties = self.parse_properties_literal()

            self.consume(TokenType.RBRACKET)

        # Direction: handle both -> as single token and - > as two tokens
        if self.match(TokenType.ARROW_RIGHT):
            self.advance()
            direction = "out"
        elif self.match(TokenType.ARROW_LEFT):
            self.advance()
            direction = "in"
        elif self.match(TokenType.DASH):
            self.advance()
            if self.match(TokenType.GT):
                self.advance()
                direction = "out"
            elif self.match(TokenType.LT):
                direction = "in"
            # else: undirected (-)

        rel.direction = direction
        return rel

    def parse_properties_literal(self) -> dict[str, Any]:
        """Parse properties literal: {key: value, ...}."""
        self.consume(TokenType.LBRACE)
        props = {}

        if not self.match(TokenType.RBRACE):
            while True:
                key_token = self.consume(TokenType.IDENTIFIER)
                self.consume(TokenType.COLON)
                value_lit = self.parse_literal()
                props[key_token.value] = value_lit.value

                if not self.match(TokenType.COMMA):
                    break
                self.advance()

        self.consume(TokenType.RBRACE)
        return props

    # ========================================
    # FLOW Query
    # ========================================

    def parse_flow(self) -> FlowQuery:
        """Parse FLOW query."""
        token = self.consume(TokenType.FLOW)
        query = FlowQuery(node_type=ASTNodeType.FLOW_QUERY, line=token.line, column=token.column)

        # Direction (optional)
        if self.match(TokenType.FORWARD, TokenType.BACKWARD):
            dir_token = self.advance()
            query.direction = dir_token.type.name

        # FROM
        self.consume(TokenType.FROM, "Expected FROM in FLOW query")
        query.source = self.parse_flow_source()

        # TO
        self.consume(TokenType.TO, "Expected TO in FLOW query")
        query.sink = self.parse_flow_sink()

        # THROUGH (optional)
        if self.match(TokenType.THROUGH):
            self.advance()
            node_pattern = self.parse_node_pattern()
            query.through = FlowThrough(node_type=TokenType.THROUGH, pattern=node_pattern)

        # EXCLUDE SOURCES (optional)
        if self.match(TokenType.EXCLUDE):
            self.advance()
            self.consume(TokenType.SOURCES)
            array_lit = self.parse_array_literal()
            query.exclude_sources = array_lit.value

        # REQUIRE (optional)
        if self.match(TokenType.REQUIRE):
            self.advance()
            self.consume(TokenType.ALL)
            self.consume(TokenType.PATHS)
            # PASS (using PATHS as keyword)
            condition = self.parse_condition()
            query.sanitizer = FlowSanitizer(node_type=TokenType.REQUIRE, condition=condition, mode="ALL")

        # WHERE (optional)
        if self.match(TokenType.WHERE):
            query.where_clause = self.parse_where()

        # RETURN
        if self.match(TokenType.RETURN):
            query.return_clause = self.parse_return()

        # Modifiers
        self.parse_modifiers(query)

        return query

    def parse_flow_source(self) -> FlowSource:
        """Parse flow source."""
        if self.match(TokenType.LPAREN):
            # Could be node pattern or subquery
            self.advance()
            if self.match(TokenType.IDENTIFIER) and self.peek().type == TokenType.COLON:
                # Node pattern
                self.pos -= 1  # Back up
                node_pattern = self.parse_node_pattern()
                return FlowSource(node_type=TokenType.LPAREN, pattern=node_pattern)
            else:
                # Subquery
                self.pos -= 1  # Back up
                subquery = self.parse()
                self.consume(TokenType.RPAREN)
                return FlowSource(node_type=TokenType.LPAREN, subquery=subquery)

        raise ParseError("Expected flow source (node pattern or subquery)", self.current())

    def parse_flow_sink(self) -> FlowSink:
        """Parse flow sink."""
        if self.match(TokenType.ANY):
            token = self.advance()
            return FlowSink(node_type=token.type, is_any=True)

        if self.match(TokenType.LPAREN):
            # Could be node pattern or subquery
            self.advance()
            if self.match(TokenType.IDENTIFIER) and self.peek().type == TokenType.COLON:
                # Node pattern
                self.pos -= 1  # Back up
                node_pattern = self.parse_node_pattern()
                return FlowSink(node_type=TokenType.LPAREN, pattern=node_pattern)
            else:
                # Subquery
                self.pos -= 1  # Back up
                subquery = self.parse()
                self.consume(TokenType.RPAREN)
                return FlowSink(node_type=TokenType.LPAREN, subquery=subquery)

        raise ParseError("Expected flow sink (ANY, node pattern, or subquery)", self.current())

    # ========================================
    # PATTERN Query
    # ========================================

    def parse_pattern(self) -> PatternQuery:
        """Parse PATTERN query."""
        token = self.consume(TokenType.PATTERN)
        query = PatternQuery(node_type=ASTNodeType.PATTERN_QUERY, line=token.line, column=token.column)

        # Pattern IDs
        while True:
            id_token = self.consume(TokenType.IDENTIFIER, "Expected pattern ID")
            query.pattern_ids.append(id_token.value)
            if not self.match(TokenType.COMMA):
                break
            self.advance()

        # LENS (optional)
        if self.match(TokenType.LENS):
            self.advance()
            while True:
                lens_token = self.consume(TokenType.IDENTIFIER)
                query.lens.append(lens_token.value)
                if not self.match(TokenType.COMMA):
                    break
                self.advance()

        # SEVERITY (optional)
        if self.match(TokenType.SEVERITY):
            self.advance()
            while True:
                sev_token = self.consume(TokenType.IDENTIFIER)
                query.severity.append(sev_token.value)
                if not self.match(TokenType.COMMA):
                    break
                self.advance()

        # Modifiers
        self.parse_modifiers(query)

        return query

    # ========================================
    # Modifiers
    # ========================================

    def parse_modifiers(self, query: QueryNode) -> None:
        """Parse query modifiers (GROUP BY, HAVING, ORDER BY, LIMIT, OFFSET, options)."""
        # GROUP BY
        if self.match(TokenType.GROUP):
            self.advance()
            self.consume(TokenType.BY)
            query.group_by = GroupByClause(node_type=TokenType.GROUP)
            while True:
                expr = self.parse_condition()
                query.group_by.expressions.append(expr)
                if not self.match(TokenType.COMMA):
                    break
                self.advance()

        # HAVING
        if self.match(TokenType.HAVING):
            token = self.advance()
            condition = self.parse_condition()
            query.having = HavingClause(
                node_type=token.type, condition=condition, line=token.line, column=token.column
            )

        # ORDER BY
        if self.match(TokenType.ORDER):
            self.advance()
            self.consume(TokenType.BY)
            query.order_by = OrderByClause(node_type=TokenType.ORDER)
            while True:
                expr = self.parse_condition()
                direction = "ASC"
                if self.match(TokenType.ASC, TokenType.DESC):
                    dir_token = self.advance()
                    direction = dir_token.type.name
                query.order_by.items.append(
                    OrderByItem(node_type=TokenType.ORDER, expression=expr, direction=direction)
                )
                if not self.match(TokenType.COMMA):
                    break
                self.advance()

        # LIMIT
        if self.match(TokenType.LIMIT):
            token = self.advance()
            limit_token = self.consume(TokenType.INTEGER, "Expected integer after LIMIT")
            query.limit = LimitClause(
                node_type=token.type, value=limit_token.value, line=token.line, column=token.column
            )

        # OFFSET
        if self.match(TokenType.OFFSET):
            token = self.advance()
            offset_token = self.consume(TokenType.INTEGER, "Expected integer after OFFSET")
            query.offset = OffsetClause(
                node_type=token.type, value=offset_token.value, line=token.line, column=token.column
            )

        # Options (COMPACT, EXPLAIN, NO EVIDENCE, VERBOSE)
        while self.match(TokenType.COMPACT, TokenType.EXPLAIN, TokenType.NO, TokenType.VERBOSE):
            if self.match(TokenType.COMPACT):
                self.advance()
                query.options["compact_mode"] = True
            elif self.match(TokenType.EXPLAIN):
                self.advance()
                query.options["explain_mode"] = True
            elif self.match(TokenType.VERBOSE):
                self.advance()
                query.options["verbose_mode"] = True
            elif self.match(TokenType.NO):
                self.advance()
                self.consume(TokenType.EVIDENCE)
                query.options["include_evidence"] = False
