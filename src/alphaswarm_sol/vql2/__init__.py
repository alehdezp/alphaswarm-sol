"""VQL 2.0 - Enhanced query language for Vulnerability Knowledge Graphs.

This module provides a powerful, LLM-friendly query language with:
- SQL-like syntax with graph pattern matching
- Advanced dataflow analysis
- Comprehensive error recovery
- Schema introspection
- Query composition and subqueries
"""

from alphaswarm_sol.vql2.lexer import Lexer, Token, TokenType
from alphaswarm_sol.vql2.parser import Parser, ParseError
from alphaswarm_sol.vql2.ast import QueryNode, ASTNodeType
from alphaswarm_sol.vql2.semantic import SemanticAnalyzer, SemanticError
from alphaswarm_sol.vql2.executor import VQL2Executor
from alphaswarm_sol.vql2.guidance import LLMGuidanceSystem

__all__ = [
    "Lexer",
    "Token",
    "TokenType",
    "Parser",
    "ParseError",
    "QueryNode",
    "ASTNodeType",
    "SemanticAnalyzer",
    "SemanticError",
    "VQL2Executor",
    "LLMGuidanceSystem",
    "parse_vql2",
    "execute_vql2",
]


def parse_vql2(query: str) -> QueryNode:
    """Parse a VQL 2.0 query string into an AST.

    Args:
        query: VQL 2.0 query string

    Returns:
        QueryNode representing the parsed query

    Raises:
        ParseError: If the query cannot be parsed
        SemanticError: If the query has semantic errors
    """
    lexer = Lexer(query)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast)
    return ast


def execute_vql2(query: str, graph, **options):
    """Parse and execute a VQL 2.0 query.

    Args:
        query: VQL 2.0 query string
        graph: KnowledgeGraph instance
        **options: Execution options (compact_mode, explain_mode, etc.)

    Returns:
        Query results dict

    Raises:
        ParseError: If the query cannot be parsed
        SemanticError: If the query has semantic errors
    """
    ast = parse_vql2(query)
    executor = VQL2Executor(graph, **options)
    return executor.execute(ast)
