"""Tests for VulnDocs tools module.

Task 18.19: Comprehensive tests for LLM tool interface.
"""

import json
import shutil
import tempfile
import unittest
from typing import List

from alphaswarm_sol.vulndocs.knowledge_doc import (
    DetectionSection,
    DocMetadata,
    ExamplesSection,
    ExploitationSection,
    MitigationSection,
    PatternLinkage,
    PatternLinkageType,
    RealExploitRef,
    Severity,
    VulnKnowledgeDoc,
)
from alphaswarm_sol.vulndocs.storage.knowledge_store import KnowledgeStore, StorageConfig
from alphaswarm_sol.vulndocs.tools.definitions import (
    AVAILABLE_TOOLS,
    ToolDefinition,
    ToolParameter,
    get_tool_definitions,
    get_tool_names,
    get_tool_schema,
)
from alphaswarm_sol.vulndocs.tools.formatters import (
    CompactFormatter,
    FormatterConfig,
    JSONFormatter,
    MarkdownFormatter,
    OutputFormat,
    TOONFormatter,
    format_for_llm,
    format_output,
    get_formatter,
)
from alphaswarm_sol.vulndocs.tools.handlers import (
    ToolError,
    ToolHandler,
    ToolResponse,
    execute_tool,
    get_help,
    get_tool_list,
)


def create_test_document(
    doc_id: str = "reentrancy/classic/test-doc",
    name: str = "Test Vulnerability",
    category: str = "reentrancy",
    subcategory: str = "classic",
    severity: Severity = Severity.HIGH,
    keywords: List[str] = None,
    pattern_ids: List[str] = None,
) -> VulnKnowledgeDoc:
    """Create a test document with default values."""
    return VulnKnowledgeDoc(
        id=doc_id,
        name=name,
        category=category,
        subcategory=subcategory,
        severity=severity,
        one_liner="Test vulnerability for external call patterns",
        tldr="This tests state updates after external calls.",
        detection=DetectionSection(
            graph_signals=["state_write_after_external_call", "no_reentrancy_guard"],
            vulnerable_sequence="R:bal -> X:out -> W:bal",
            safe_sequence="R:bal -> W:bal -> X:out",
            indicators=["External call before state update"],
            checklist=["Check call ordering", "Verify guard presence"],
        ),
        exploitation=ExploitationSection(
            attack_vector="Callback exploitation during external call",
            prerequisites=["External call to attacker-controlled contract"],
            attack_steps=["Deploy attacker", "Call target function", "Re-enter"],
            potential_impact="Complete fund drain",
            monetary_risk="critical",
        ),
        mitigation=MitigationSection(
            primary_fix="Use CEI pattern (Checks-Effects-Interactions)",
            alternative_fixes=["Add reentrancy guard", "Use pull pattern"],
            safe_pattern="CEI",
            how_to_verify=["Test with attacker contract", "Static analysis"],
        ),
        examples=ExamplesSection(
            vulnerable_code="function withdraw() { msg.sender.call{value: bal}(''); bal = 0; }",
            vulnerable_code_explanation="External call before balance update",
            fixed_code="function withdraw() { uint b = bal; bal = 0; msg.sender.call{value: b}(''); }",
            fixed_code_explanation="Balance updated before external call",
            real_exploits=[
                RealExploitRef(
                    name="The DAO Hack",
                    date="2016-06-17",
                    loss="$60M",
                    protocol="The DAO",
                    brief="Classic reentrancy exploit",
                )
            ],
        ),
        pattern_linkage=PatternLinkage(
            linkage_type=PatternLinkageType.EXACT_MATCH,
            pattern_ids=pattern_ids or ["reentrancy-001"],
            coverage_pct=0.95,
        ),
        metadata=DocMetadata(
            sources=["https://example.com/vuln"],
            source_authority=0.9,
            keywords=keywords or ["reentrancy", "external-call", "state-update"],
            completeness_score=0.85,
            confidence_score=0.9,
        ),
    )


class TestToolParameter(unittest.TestCase):
    """Tests for ToolParameter."""

    def test_to_schema_basic(self):
        """Test basic schema generation."""
        param = ToolParameter(
            name="category",
            type="string",
            description="Vulnerability category",
            required=True,
        )

        schema = param.to_schema()

        self.assertEqual(schema["type"], "string")
        self.assertEqual(schema["description"], "Vulnerability category")
        self.assertNotIn("enum", schema)
        self.assertNotIn("default", schema)

    def test_to_schema_with_enum(self):
        """Test schema with enum values."""
        param = ToolParameter(
            name="depth",
            type="string",
            description="Detail level",
            required=False,
            enum=["minimal", "standard", "full"],
            default="standard",
        )

        schema = param.to_schema()

        self.assertEqual(schema["enum"], ["minimal", "standard", "full"])
        self.assertEqual(schema["default"], "standard")

    def test_to_schema_with_items(self):
        """Test schema for array type with items."""
        param = ToolParameter(
            name="pattern_ids",
            type="array",
            description="List of pattern IDs",
            required=True,
            items={"type": "string"},
        )

        schema = param.to_schema()

        self.assertEqual(schema["type"], "array")
        self.assertEqual(schema["items"], {"type": "string"})


class TestToolDefinition(unittest.TestCase):
    """Tests for ToolDefinition."""

    def test_to_schema(self):
        """Test schema generation."""
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters=[
                ToolParameter("param1", "string", "First param", required=True),
                ToolParameter("param2", "integer", "Second param", required=False),
            ],
        )

        schema = tool.to_schema()

        self.assertEqual(schema["name"], "test_tool")
        self.assertEqual(schema["description"], "A test tool")
        self.assertIn("input_schema", schema)
        self.assertEqual(schema["input_schema"]["type"], "object")
        self.assertIn("param1", schema["input_schema"]["properties"])
        self.assertEqual(schema["input_schema"]["required"], ["param1"])

    def test_to_anthropic_format(self):
        """Test Anthropic tool format."""
        tool = ToolDefinition(
            name="test_tool",
            description="Test",
            parameters=[],
        )

        anthropic_format = tool.to_anthropic_format()

        self.assertEqual(anthropic_format["name"], "test_tool")

    def test_to_openai_format(self):
        """Test OpenAI function format."""
        tool = ToolDefinition(
            name="test_tool",
            description="Test",
            parameters=[],
        )

        openai_format = tool.to_openai_format()

        self.assertEqual(openai_format["type"], "function")
        self.assertEqual(openai_format["function"]["name"], "test_tool")


class TestToolDefinitions(unittest.TestCase):
    """Tests for tool definitions."""

    def test_all_tools_defined(self):
        """Test that all expected tools are defined."""
        expected_tools = [
            "get_vulnerability_knowledge",
            "search_vulnerability_knowledge",
            "get_knowledge_for_finding",
            "list_vulnerability_categories",
            "get_pattern_knowledge",
            "get_navigation_context",
        ]

        for tool_name in expected_tools:
            self.assertIn(tool_name, AVAILABLE_TOOLS)

    def test_get_tool_definitions_anthropic(self):
        """Test getting all definitions in Anthropic format."""
        definitions = get_tool_definitions(format="anthropic")

        self.assertIsInstance(definitions, list)
        self.assertGreater(len(definitions), 0)
        self.assertIn("name", definitions[0])
        self.assertIn("description", definitions[0])

    def test_get_tool_definitions_openai(self):
        """Test getting all definitions in OpenAI format."""
        definitions = get_tool_definitions(format="openai")

        self.assertIsInstance(definitions, list)
        self.assertGreater(len(definitions), 0)
        self.assertEqual(definitions[0]["type"], "function")

    def test_get_tool_schema(self):
        """Test getting schema for specific tool."""
        schema = get_tool_schema("get_vulnerability_knowledge")

        self.assertIsNotNone(schema)
        self.assertEqual(schema["name"], "get_vulnerability_knowledge")

    def test_get_tool_schema_not_found(self):
        """Test getting schema for non-existent tool."""
        schema = get_tool_schema("nonexistent_tool")
        self.assertIsNone(schema)

    def test_get_tool_names(self):
        """Test getting list of tool names."""
        names = get_tool_names()

        self.assertIsInstance(names, list)
        self.assertIn("get_vulnerability_knowledge", names)


class TestTOONFormatter(unittest.TestCase):
    """Tests for TOON (Token-Optimized Output Notation) formatter."""

    def test_format_document(self):
        """Test formatting a single document."""
        doc = create_test_document()
        formatter = TOONFormatter()

        output = formatter.format_document(doc)

        # Check header format
        self.assertIn("REENTRANCY/classic", output)
        self.assertIn("SEV:", output)

        # Check detection signals abbreviated
        self.assertIn("detect:", output)

        # Check fix included
        self.assertIn("fix:", output)
        self.assertIn("CEI", output)

    def test_format_document_includes_exploits(self):
        """Test that real exploits are included by default."""
        doc = create_test_document()
        formatter = TOONFormatter()

        output = formatter.format_document(doc)

        self.assertIn("DAO", output)
        self.assertIn("$60M", output)

    def test_format_document_without_examples(self):
        """Test formatting without examples."""
        doc = create_test_document()
        config = FormatterConfig(include_examples=False)
        formatter = TOONFormatter(config)

        output = formatter.format_document(doc)

        self.assertNotIn("refs:", output)

    def test_severity_symbols(self):
        """Test severity symbol conversion."""
        formatter = TOONFormatter()

        # Test all severity levels
        self.assertIn("★★★", formatter._severity_symbol("critical"))
        self.assertIn("★★", formatter._severity_symbol("high"))
        self.assertIn("★", formatter._severity_symbol("medium"))
        self.assertIn("○", formatter._severity_symbol("low"))
        self.assertIn("·", formatter._severity_symbol("info"))

    def test_format_documents_respects_token_limit(self):
        """Test that multiple documents respect token limit."""
        docs = [create_test_document(f"reentrancy/classic/doc{i}") for i in range(10)]
        config = FormatterConfig(max_tokens=500)
        formatter = TOONFormatter(config)

        output = formatter.format_documents(docs)

        # Should indicate more documents available
        token_estimate = formatter.estimate_tokens(output)
        self.assertLessEqual(token_estimate, 600)  # Some buffer for truncation message


class TestJSONFormatter(unittest.TestCase):
    """Tests for JSON formatter."""

    def test_format_document(self):
        """Test formatting document to JSON."""
        doc = create_test_document()
        formatter = JSONFormatter()

        output = formatter.format_document(doc)

        # Should be valid JSON
        data = json.loads(output)
        self.assertEqual(data["id"], doc.id)
        self.assertEqual(data["name"], doc.name)

    def test_format_documents(self):
        """Test formatting multiple documents."""
        docs = [create_test_document(f"reentrancy/classic/doc{i}") for i in range(3)]
        formatter = JSONFormatter()

        output = formatter.format_documents(docs)

        data = json.loads(output)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 3)


class TestMarkdownFormatter(unittest.TestCase):
    """Tests for Markdown formatter."""

    def test_format_document(self):
        """Test formatting document to Markdown."""
        doc = create_test_document()
        formatter = MarkdownFormatter()

        output = formatter.format_document(doc)

        # Check markdown structure
        self.assertIn("# Test Vulnerability", output)
        self.assertIn("## Detection", output)
        self.assertIn("## Mitigation", output)


class TestCompactFormatter(unittest.TestCase):
    """Tests for Compact formatter."""

    def test_format_document_is_shorter(self):
        """Test that compact format is shorter than full."""
        doc = create_test_document()
        compact_formatter = CompactFormatter()
        markdown_formatter = MarkdownFormatter()

        compact_output = compact_formatter.format_document(doc)
        markdown_output = markdown_formatter.format_document(doc)

        self.assertLess(len(compact_output), len(markdown_output))


class TestFormatOutput(unittest.TestCase):
    """Tests for format_output function."""

    def test_format_output_toon(self):
        """Test formatting with TOON."""
        doc = create_test_document()

        output = format_output(doc, OutputFormat.TOON)

        self.assertIn("REENTRANCY", output)

    def test_format_output_json(self):
        """Test formatting with JSON."""
        doc = create_test_document()

        output = format_output(doc, OutputFormat.JSON)

        data = json.loads(output)
        self.assertIn("id", data)

    def test_format_output_string_format(self):
        """Test formatting with string format name."""
        doc = create_test_document()

        output = format_output(doc, "toon")

        self.assertIn("REENTRANCY", output)

    def test_format_for_llm(self):
        """Test format_for_llm convenience function."""
        doc = create_test_document()

        output = format_for_llm(doc, max_tokens=1000)

        self.assertIsInstance(output, str)
        self.assertGreater(len(output), 0)


class TestToolResponse(unittest.TestCase):
    """Tests for ToolResponse."""

    def test_response_creation(self):
        """Test creating a tool response."""
        response = ToolResponse(
            success=True,
            tool_name="test_tool",
            content="Test content",
        )

        self.assertTrue(response.success)
        self.assertEqual(response.tool_name, "test_tool")
        self.assertGreater(response.token_estimate, 0)
        self.assertIsNotNone(response.timestamp)

    def test_response_to_dict(self):
        """Test serializing response."""
        response = ToolResponse(
            success=True,
            tool_name="test_tool",
            content="Test content",
            metadata={"key": "value"},
        )

        data = response.to_dict()

        self.assertEqual(data["success"], True)
        self.assertEqual(data["tool_name"], "test_tool")
        self.assertIn("metadata", data)


class TestToolHandler(unittest.TestCase):
    """Tests for ToolHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = StorageConfig(base_path=self.temp_dir)
        self.store = KnowledgeStore(self.config)
        self.handler = ToolHandler(store=self.store)

        # Add some test documents
        doc1 = create_test_document(
            "reentrancy/classic/doc1",
            name="Classic Reentrancy",
            keywords=["reentrancy", "callback"],
            pattern_ids=["reentrancy-001"],
        )
        doc2 = create_test_document(
            "reentrancy/cross-function/doc1",
            name="Cross-Function Reentrancy",
            subcategory="cross-function",
            keywords=["reentrancy", "cross-function"],
            pattern_ids=["reentrancy-002"],
        )
        doc3 = create_test_document(
            "access-control/missing-modifier/doc1",
            name="Missing Access Control",
            category="access-control",
            subcategory="missing-modifier",
            severity=Severity.CRITICAL,
            keywords=["access", "modifier"],
            pattern_ids=["access-001"],
        )

        self.store.save(doc1)
        self.store.save(doc2)
        self.store.save(doc3)

        # Rebuild retriever with fresh index
        from alphaswarm_sol.vulndocs.storage.retrieval import KnowledgeRetriever
        self.handler.retriever = KnowledgeRetriever(self.store)

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_execute_unknown_tool(self):
        """Test executing unknown tool."""
        response = self.handler.execute("unknown_tool", {})

        self.assertFalse(response.success)
        self.assertIn("Unknown tool", response.error)

    def test_get_vulnerability_knowledge(self):
        """Test get_vulnerability_knowledge tool."""
        response = self.handler.execute(
            "get_vulnerability_knowledge",
            {"category": "reentrancy"},
        )

        self.assertTrue(response.success)
        self.assertIn("reentrancy", response.content.lower())
        self.assertEqual(response.metadata["category"], "reentrancy")

    def test_get_vulnerability_knowledge_with_subcategory(self):
        """Test get_vulnerability_knowledge with subcategory."""
        response = self.handler.execute(
            "get_vulnerability_knowledge",
            {"category": "reentrancy", "subcategory": "classic"},
        )

        self.assertTrue(response.success)
        self.assertEqual(response.metadata["subcategory"], "classic")

    def test_get_vulnerability_knowledge_missing_category(self):
        """Test get_vulnerability_knowledge without category."""
        response = self.handler.execute(
            "get_vulnerability_knowledge",
            {},
        )

        self.assertFalse(response.success)
        self.assertIn("Missing required parameter", response.error)

    def test_search_vulnerability_knowledge(self):
        """Test search_vulnerability_knowledge tool."""
        response = self.handler.execute(
            "search_vulnerability_knowledge",
            {"query": "reentrancy callback"},
        )

        self.assertTrue(response.success)

    def test_search_vulnerability_knowledge_with_severity(self):
        """Test search with severity filter."""
        response = self.handler.execute(
            "search_vulnerability_knowledge",
            {"query": "access", "severity_filter": "critical"},
        )

        self.assertTrue(response.success)

    def test_search_missing_query(self):
        """Test search without query."""
        response = self.handler.execute(
            "search_vulnerability_knowledge",
            {},
        )

        self.assertFalse(response.success)
        self.assertIn("Missing required parameter", response.error)

    def test_get_knowledge_for_finding(self):
        """Test get_knowledge_for_finding tool."""
        response = self.handler.execute(
            "get_knowledge_for_finding",
            {
                "finding": {
                    "category": "reentrancy",
                    "signals": ["state_write_after_external_call"],
                }
            },
        )

        self.assertTrue(response.success)

    def test_get_knowledge_for_finding_missing_finding(self):
        """Test get_knowledge_for_finding without finding."""
        response = self.handler.execute(
            "get_knowledge_for_finding",
            {},
        )

        self.assertFalse(response.success)

    def test_list_vulnerability_categories(self):
        """Test list_vulnerability_categories tool."""
        response = self.handler.execute(
            "list_vulnerability_categories",
            {"include_stats": True},
        )

        self.assertTrue(response.success)
        self.assertIn("reentrancy", response.content.lower())
        self.assertIn("access-control", response.content.lower())

    def test_list_vulnerability_categories_filtered(self):
        """Test list_vulnerability_categories with filter."""
        response = self.handler.execute(
            "list_vulnerability_categories",
            {"category_filter": "reentrancy"},
        )

        self.assertTrue(response.success)
        self.assertIn("classic", response.content.lower())

    def test_get_pattern_knowledge(self):
        """Test get_pattern_knowledge tool."""
        response = self.handler.execute(
            "get_pattern_knowledge",
            {"pattern_ids": ["reentrancy-001"]},
        )

        self.assertTrue(response.success)

    def test_get_pattern_knowledge_missing_ids(self):
        """Test get_pattern_knowledge without pattern_ids."""
        response = self.handler.execute(
            "get_pattern_knowledge",
            {},
        )

        self.assertFalse(response.success)

    def test_get_navigation_context(self):
        """Test get_navigation_context tool."""
        response = self.handler.execute(
            "get_navigation_context",
            {"max_tokens": 500},
        )

        self.assertTrue(response.success)
        self.assertIn("Categories", response.content)

    def test_get_available_tools(self):
        """Test getting available tools."""
        tools = self.handler.get_available_tools()

        self.assertIn("get_vulnerability_knowledge", tools)
        self.assertIn("search_vulnerability_knowledge", tools)

    def test_get_tool_help(self):
        """Test getting tool help."""
        help_text = self.handler.get_tool_help("get_vulnerability_knowledge")

        self.assertIsNotNone(help_text)
        self.assertIn("get_vulnerability_knowledge", help_text)
        self.assertIn("Parameters", help_text)

    def test_get_tool_help_unknown(self):
        """Test getting help for unknown tool."""
        help_text = self.handler.get_tool_help("unknown_tool")
        self.assertIsNone(help_text)


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for convenience functions."""

    def setUp(self):
        """Set up with a handler."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = StorageConfig(base_path=self.temp_dir)
        self.store = KnowledgeStore(self.config)

        from alphaswarm_sol.vulndocs.tools.handlers import set_handler
        set_handler(ToolHandler(store=self.store))

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_execute_tool(self):
        """Test execute_tool convenience function."""
        response = execute_tool(
            "list_vulnerability_categories",
            {},
        )

        self.assertTrue(response.success)

    def test_get_tool_list(self):
        """Test get_tool_list convenience function."""
        tools = get_tool_list()

        self.assertIn("get_vulnerability_knowledge", tools)

    def test_get_help(self):
        """Test get_help convenience function."""
        help_text = get_help("search_vulnerability_knowledge")

        self.assertIsNotNone(help_text)


class TestOutputFormatIntegration(unittest.TestCase):
    """Integration tests for output format selection."""

    def setUp(self):
        """Set up with test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = StorageConfig(base_path=self.temp_dir)
        self.store = KnowledgeStore(self.config)

        doc = create_test_document()
        self.store.save(doc)

        from alphaswarm_sol.vulndocs.storage.retrieval import KnowledgeRetriever
        self.handler = ToolHandler(
            store=self.store,
            retriever=KnowledgeRetriever(self.store),
        )

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_output_format_toon(self):
        """Test TOON output format."""
        response = self.handler.execute(
            "get_vulnerability_knowledge",
            {"category": "reentrancy"},
            output_format=OutputFormat.TOON,
        )

        self.assertEqual(response.format_used, "toon")
        self.assertIn("▸", response.content)  # TOON header symbol

    def test_output_format_json(self):
        """Test JSON output format."""
        response = self.handler.execute(
            "get_vulnerability_knowledge",
            {"category": "reentrancy"},
            output_format=OutputFormat.JSON,
        )

        self.assertEqual(response.format_used, "json")
        # Should be valid JSON
        data = json.loads(response.content)
        self.assertIsInstance(data, list)

    def test_output_format_markdown(self):
        """Test Markdown output format."""
        response = self.handler.execute(
            "get_vulnerability_knowledge",
            {"category": "reentrancy"},
            output_format=OutputFormat.MARKDOWN,
        )

        self.assertEqual(response.format_used, "markdown")
        self.assertIn("#", response.content)  # Markdown header


if __name__ == "__main__":
    unittest.main()
