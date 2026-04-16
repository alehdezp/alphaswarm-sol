"""Test suite for VQL 2.0 implementation."""

import unittest
from pathlib import Path

from alphaswarm_sol.vql2.lexer import Lexer, TokenType
from alphaswarm_sol.vql2.parser import Parser
from alphaswarm_sol.vql2.semantic import SemanticAnalyzer, VKGSchema
from alphaswarm_sol.vql2.guidance import LLMGuidanceSystem
from alphaswarm_sol.vql2.ast import FindQuery, MatchQuery, DescribeQuery, FlowQuery, PatternQuery


class TestVQL2Lexer(unittest.TestCase):
    """Test VQL 2.0 lexer."""

    def test_simple_find_query(self):
        """Test tokenizing a simple FIND query."""
        query = "FIND functions WHERE visibility = 'public'"
        lexer = Lexer(query)
        tokens = lexer.tokenize()

        self.assertEqual(tokens[0].type, TokenType.FIND)
        # "functions" is a keyword, not identifier
        self.assertEqual(tokens[1].type, TokenType.FUNCTIONS)
        self.assertEqual(tokens[2].type, TokenType.WHERE)
        self.assertEqual(tokens[3].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[3].value, "visibility")
        self.assertEqual(tokens[4].type, TokenType.EQ)
        self.assertEqual(tokens[5].type, TokenType.STRING)
        self.assertEqual(tokens[5].value, "public")

    def test_complex_query_with_operators(self):
        """Test tokenizing complex query with various operators."""
        query = "FIND functions WHERE visibility IN ['public', 'external'] AND writes_state"
        lexer = Lexer(query)
        tokens = lexer.tokenize()

        # Verify key tokens
        token_types = [t.type for t in tokens]
        self.assertIn(TokenType.FIND, token_types)
        self.assertIn(TokenType.WHERE, token_types)
        self.assertIn(TokenType.IN, token_types)
        self.assertIn(TokenType.AND, token_types)
        self.assertIn(TokenType.LBRACKET, token_types)
        self.assertIn(TokenType.RBRACKET, token_types)

    def test_match_pattern(self):
        """Test tokenizing MATCH pattern."""
        query = "MATCH (f:Function)-[:WRITES_STATE]->(s:StateVariable)"
        lexer = Lexer(query)
        tokens = lexer.tokenize()

        token_types = [t.type for t in tokens]
        self.assertIn(TokenType.MATCH, token_types)
        self.assertIn(TokenType.LPAREN, token_types)
        self.assertIn(TokenType.COLON, token_types)
        self.assertIn(TokenType.DASH, token_types)
        self.assertIn(TokenType.LBRACKET, token_types)
        self.assertIn(TokenType.ARROW_RIGHT, token_types)


class TestVQL2Parser(unittest.TestCase):
    """Test VQL 2.0 parser."""

    def test_parse_describe_types(self):
        """Test parsing DESCRIBE TYPES query."""
        query = "DESCRIBE TYPES"
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        self.assertIsInstance(ast, DescribeQuery)
        self.assertEqual(ast.target, "TYPES")

    def test_parse_describe_properties(self):
        """Test parsing DESCRIBE PROPERTIES FOR query."""
        query = "DESCRIBE PROPERTIES FOR Function"
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        self.assertIsInstance(ast, DescribeQuery)
        self.assertEqual(ast.target, "PROPERTIES")
        self.assertEqual(ast.for_type, "Function")

    def test_parse_simple_find(self):
        """Test parsing simple FIND query."""
        query = "FIND functions WHERE visibility = 'public'"
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        self.assertIsInstance(ast, FindQuery)
        self.assertEqual(ast.target_types, ["functions"])
        self.assertIsNotNone(ast.where_clause)

    def test_parse_find_with_return(self):
        """Test parsing FIND with RETURN clause."""
        query = "FIND functions WHERE writes_state RETURN id, label LIMIT 10"
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        self.assertIsInstance(ast, FindQuery)
        self.assertIsNotNone(ast.return_clause)
        self.assertEqual(len(ast.return_clause.items), 2)
        self.assertIsNotNone(ast.limit)
        self.assertEqual(ast.limit.value, 10)

    def test_parse_match_pattern(self):
        """Test parsing MATCH query."""
        query = "MATCH (f:Function)-[:WRITES_STATE]->(s:StateVariable) WHERE f.visibility = 'public' RETURN f.label"
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        self.assertIsInstance(ast, MatchQuery)
        self.assertEqual(len(ast.patterns), 1)
        self.assertIsNotNone(ast.patterns[0].start_node)
        self.assertIsNotNone(ast.where_clause)
        self.assertIsNotNone(ast.return_clause)

    def test_parse_flow_query(self):
        """Test parsing FLOW query."""
        query = "FLOW FROM (i:Input) TO (s:StateVariable) RETURN PATHS"
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        self.assertIsInstance(ast, FlowQuery)
        self.assertIsNotNone(ast.source)
        self.assertIsNotNone(ast.sink)
        self.assertIsNotNone(ast.return_clause)

    def test_parse_pattern_query(self):
        """Test parsing PATTERN query."""
        query = "PATTERN weak-access-control LENS Authority SEVERITY high"
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        self.assertIsInstance(ast, PatternQuery)
        self.assertEqual(ast.pattern_ids, ["weak-access-control"])
        self.assertEqual(ast.lens, ["Authority"])
        self.assertEqual(ast.severity, ["high"])


class TestVQL2Semantic(unittest.TestCase):
    """Test VQL 2.0 semantic analyzer."""

    def setUp(self):
        """Set up test schema."""
        self.schema = VKGSchema.default()
        self.analyzer = SemanticAnalyzer(self.schema)

    def test_valid_query(self):
        """Test validation of valid query."""
        query = "FIND functions WHERE visibility = 'public'"
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        self.analyzer.analyze(ast)
        self.assertFalse(self.analyzer.has_errors())

    def test_unknown_node_type(self):
        """Test detection of unknown node type."""
        query = "FIND blahblah WHERE visibility = 'public'"  # Wrong type
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        self.analyzer.analyze(ast)
        self.assertTrue(self.analyzer.has_errors())
        self.assertIn("Unknown type", self.analyzer.errors[0].message)

    def test_fuzzy_matching_property(self):
        """Test fuzzy matching for misspelled property."""
        query = "FIND functions WHERE visability = 'public'"  # Typo
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        self.analyzer.analyze(ast)
        self.assertTrue(self.analyzer.has_errors())
        error = self.analyzer.errors[0]
        self.assertIn("visibility", error.suggestions[0] if error.suggestions else "")

    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation."""
        distance = VKGSchema._levenshtein_distance("visibility", "visability")
        self.assertEqual(distance, 1)  # One character swap

        distance2 = VKGSchema._levenshtein_distance("function", "funct")
        self.assertEqual(distance2, 3)  # Three deletions


class TestLLMGuidance(unittest.TestCase):
    """Test LLM Guidance System."""

    def setUp(self):
        """Set up guidance system."""
        self.guidance = LLMGuidanceSystem()

    def test_schema_discovery(self):
        """Test schema discovery protocol."""
        response = self.guidance.discover_schema()

        self.assertIn("capabilities", response)
        self.assertIn("node_types", response["capabilities"])
        self.assertIn("query_types", response["capabilities"])
        self.assertIn("Function", response["capabilities"]["node_types"])
        self.assertIn("FIND", response["capabilities"]["query_types"])

    def test_autocomplete_keyword(self):
        """Test autocomplete for keywords."""
        response = self.guidance.autocomplete({"query": "FI", "cursor_position": 2})

        self.assertIn("suggestions", response)
        suggestions = response["suggestions"]
        self.assertTrue(any(s["text"] == "FIND" for s in suggestions))

    def test_autocomplete_property(self):
        """Test autocomplete for properties."""
        response = self.guidance.autocomplete(
            {"query": "FIND functions WHERE visi", "cursor_position": 28}
        )

        self.assertIn("suggestions", response)
        # Should suggest visibility
        self.assertTrue(
            any("visibility" in s["text"] for s in response["suggestions"])
        )

    def test_validate_correct_query(self):
        """Test validation of correct query."""
        response = self.guidance.validate(
            {"query": "FIND functions WHERE visibility = 'public'"}
        )

        self.assertTrue(response["valid"])
        self.assertNotIn("errors", response)

    def test_validate_incorrect_query(self):
        """Test validation of incorrect query."""
        response = self.guidance.validate(
            {"query": "FIND funcs WHERE visability = public"}  # Multiple errors
        )

        self.assertFalse(response["valid"])
        self.assertIn("errors", response)
        self.assertTrue(len(response["errors"]) > 0)

    def test_example_generation(self):
        """Test example query generation."""
        response = self.guidance.generate_examples(
            {"use_case": "find_vulnerable_functions", "complexity": "simple"}
        )

        self.assertIn("examples", response)
        self.assertTrue(len(response["examples"]) > 0)
        self.assertEqual(response["examples"][0]["complexity"], "simple")


class TestIntegration(unittest.TestCase):
    """Integration tests for full VQL 2.0 pipeline."""

    def test_end_to_end_find_query(self):
        """Test complete pipeline: lex → parse → validate."""
        query = "FIND functions WHERE visibility IN ['public', 'external'] AND writes_state LIMIT 20"

        # Tokenize
        lexer = Lexer(query)
        tokens = lexer.tokenize()
        self.assertTrue(len(tokens) > 0)

        # Parse
        parser = Parser(tokens)
        ast = parser.parse()
        self.assertIsInstance(ast, FindQuery)

        # Validate
        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)
        self.assertFalse(analyzer.has_errors())

    def test_error_recovery(self):
        """Test error recovery and suggestions."""
        query = "FIND funcs WHERE visability = public"  # Multiple errors

        lexer = Lexer(query)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        # Should have errors
        self.assertTrue(analyzer.has_errors())

        # Should have suggestions
        for error in analyzer.errors:
            if "Unknown type" in error.message:
                self.assertTrue(len(error.suggestions) > 0)


if __name__ == "__main__":
    unittest.main()
