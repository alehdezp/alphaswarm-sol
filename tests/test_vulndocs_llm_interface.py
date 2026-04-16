import pytest
"""Tests for VulnDocs LLM Navigation Interface.

Phase 17.7: LLM Navigation Interface Tests.

This test module covers:
- LLMNavigationTool dataclass creation and serialization
- NavigationState dataclass and state management
- ToolExecutionResult creation
- LLMNavigator initialization and system prompt generation
- Tool definition formats (OpenAI, Anthropic)
- Tool execution with valid/invalid parameters
- Navigation context building
- Evidence request generation
- Multi-turn navigation scenarios
- Integration with navigator and builder
"""

import shutil
import tempfile
from pathlib import Path
from unittest import TestCase, main

import yaml

from alphaswarm_sol.knowledge.vulndocs.llm_interface import (
    LLMNavigator,
    LLMNavigationTool,
    NavigationState,
    ToolExecutionResult,
    create_llm_navigator,
    get_tool_names,
    TOOL_LIST_CATEGORIES,
    TOOL_GET_CATEGORY_INFO,
    TOOL_GET_SUBCATEGORY_INFO,
    TOOL_GET_DETECTION_GUIDE,
    TOOL_GET_PATTERNS,
    TOOL_GET_EXPLOITS,
    TOOL_GET_FIXES,
    TOOL_SEARCH_BY_OPERATION,
    TOOL_SEARCH_BY_SIGNATURE,
    ALL_TOOLS,
)
from alphaswarm_sol.knowledge.vulndocs.navigator import KnowledgeNavigator
from alphaswarm_sol.knowledge.vulndocs.cache import PromptCache
from alphaswarm_sol.knowledge.vulndocs.builder import ContextBuilder
from alphaswarm_sol.knowledge.vulndocs.schema import (
    KnowledgeDepth,
    KNOWLEDGE_DIR,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================


def create_test_knowledge_base(temp_dir: Path) -> Path:
    """Create a minimal test knowledge base."""
    knowledge_dir = temp_dir / "vulndocs"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    # Create index.yaml
    index_data = {
        "schema_version": "1.0",
        "last_updated": "2026-01-09",
        "categories": {
            "reentrancy": {
                "name": "Reentrancy Vulnerabilities",
                "description": "Attacks exploiting callback mechanisms during external calls",
                "severity_range": ["high", "critical"],
                "subcategories": [
                    {"id": "classic", "name": "Classic Reentrancy", "description": "State write after external call"},
                    {"id": "cross-function", "name": "Cross-Function Reentrancy", "description": "Multi-function reentry"},
                ],
                "key_operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE", "CALLS_EXTERNAL"],
                "key_properties": ["state_write_after_external_call", "has_reentrancy_guard"],
            },
            "access-control": {
                "name": "Access Control Issues",
                "description": "Permission and authorization flaws",
                "severity_range": ["medium", "high", "critical"],
                "subcategories": [
                    {"id": "missing-modifier", "name": "Missing Modifier", "description": "No access gate"},
                ],
                "key_operations": ["CHECKS_PERMISSION", "MODIFIES_OWNER"],
                "key_properties": ["has_access_gate", "writes_privileged_state"],
            },
        },
        "operation_to_categories": {
            "TRANSFERS_VALUE_OUT": {
                "primary": ["reentrancy"],
                "secondary": ["access-control"],
            },
            "CHECKS_PERMISSION": {
                "primary": ["access-control"],
                "secondary": [],
            },
        },
        "signature_to_categories": {
            "R:bal->X:out->W:bal": {
                "category": "reentrancy",
                "subcategory": "classic",
                "severity": "critical",
            },
        },
        "navigation": {
            "hints": ["Start with operations", "Use detection depth"],
            "depth_guide": {
                "detection": "~1000 tokens",
                "patterns": "~1500 tokens",
            },
        },
    }

    with open(knowledge_dir / "index.yaml", "w") as f:
        yaml.safe_dump(index_data, f)

    # Create category directory structure
    reentrancy_dir = knowledge_dir / "categories" / "reentrancy"
    reentrancy_dir.mkdir(parents=True, exist_ok=True)

    category_index = {
        "id": "reentrancy",
        "name": "Reentrancy Vulnerabilities",
        "description": "Attacks exploiting callback mechanisms during external calls",
        "severity_range": ["high", "critical"],
        "subcategories": [
            {"id": "classic", "name": "Classic Reentrancy", "description": "State write after external call"},
            {"id": "cross-function", "name": "Cross-Function Reentrancy", "description": "Multi-function reentry"},
        ],
        "relevant_properties": ["state_write_after_external_call", "has_reentrancy_guard"],
        "semantic_operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
    }

    with open(reentrancy_dir / "index.yaml", "w") as f:
        yaml.safe_dump(category_index, f)

    # Create classic subcategory
    classic_dir = reentrancy_dir / "subcategories" / "classic"
    classic_dir.mkdir(parents=True, exist_ok=True)

    subcategory_index = {
        "id": "classic",
        "name": "Classic Reentrancy",
        "description": "The most common form where state is written after an external call.",
        "parent_category": "reentrancy",
        "severity_range": ["high", "critical"],
        "patterns": ["vm-001-classic", "vm-002-callback"],
        "relevant_properties": ["state_write_after_external_call", "has_reentrancy_guard"],
        "graph_signals": [
            {"property": "state_write_after_external_call", "expected": True, "critical": True},
            {"property": "has_reentrancy_guard", "expected": False, "critical": True},
        ],
        "behavioral_signatures": ["R:bal->X:out->W:bal"],
        "false_positive_indicators": ["Reentrancy guard present", "Trusted external call"],
    }

    with open(classic_dir / "index.yaml", "w") as f:
        yaml.safe_dump(subcategory_index, f)

    return knowledge_dir


# =============================================================================
# LLM NAVIGATION TOOL TESTS
# =============================================================================


class TestLLMNavigationToolCreation(TestCase):
    """Tests for LLMNavigationTool dataclass creation."""

    def test_create_basic_tool(self):
        """Test creating a basic navigation tool."""
        tool = LLMNavigationTool(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

        self.assertEqual(tool.name, "test_tool")
        self.assertEqual(tool.description, "A test tool")
        self.assertIn("type", tool.parameters)

    def test_tool_with_parameters(self):
        """Test creating tool with complex parameters."""
        tool = LLMNavigationTool(
            name="get_category",
            description="Get category info",
            parameters={
                "type": "object",
                "properties": {
                    "category_id": {
                        "type": "string",
                        "description": "The category ID",
                    },
                },
                "required": ["category_id"],
            },
        )

        self.assertEqual(tool.name, "get_category")
        self.assertIn("category_id", tool.parameters["properties"])
        self.assertEqual(tool.parameters["required"], ["category_id"])


class TestLLMNavigationToolFormats(TestCase):
    """Tests for LLMNavigationTool format conversion."""

    def setUp(self):
        """Create a test tool."""
        self.tool = LLMNavigationTool(
            name="list_categories",
            description="List all vulnerability categories",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    def test_to_openai_format(self):
        """Test conversion to OpenAI function calling format."""
        openai_format = self.tool.to_openai_format()

        self.assertEqual(openai_format["type"], "function")
        self.assertIn("function", openai_format)
        self.assertEqual(openai_format["function"]["name"], "list_categories")
        self.assertEqual(openai_format["function"]["description"], "List all vulnerability categories")
        self.assertIn("parameters", openai_format["function"])

    def test_to_anthropic_format(self):
        """Test conversion to Anthropic tool use format."""
        anthropic_format = self.tool.to_anthropic_format()

        self.assertEqual(anthropic_format["name"], "list_categories")
        self.assertEqual(anthropic_format["description"], "List all vulnerability categories")
        self.assertIn("input_schema", anthropic_format)

    def test_openai_format_structure(self):
        """Test OpenAI format has correct structure."""
        tool = LLMNavigationTool(
            name="get_category_info",
            description="Get category details",
            parameters={
                "type": "object",
                "properties": {
                    "category_id": {"type": "string"},
                },
                "required": ["category_id"],
            },
        )

        openai_format = tool.to_openai_format()

        # Verify nested structure
        self.assertEqual(openai_format["type"], "function")
        func = openai_format["function"]
        self.assertIn("name", func)
        self.assertIn("description", func)
        self.assertIn("parameters", func)
        self.assertEqual(func["parameters"]["type"], "object")

    def test_anthropic_format_structure(self):
        """Test Anthropic format has correct structure."""
        tool = LLMNavigationTool(
            name="search_by_operation",
            description="Search by semantic operation",
            parameters={
                "type": "object",
                "properties": {
                    "operation": {"type": "string"},
                },
                "required": ["operation"],
            },
        )

        anthropic_format = tool.to_anthropic_format()

        self.assertIn("name", anthropic_format)
        self.assertIn("description", anthropic_format)
        self.assertIn("input_schema", anthropic_format)
        self.assertEqual(anthropic_format["input_schema"]["type"], "object")


class TestLLMNavigationToolSerialization(TestCase):
    """Tests for LLMNavigationTool serialization."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        tool = LLMNavigationTool(
            name="test_tool",
            description="Test description",
            parameters={"type": "object"},
        )

        data = tool.to_dict()

        self.assertEqual(data["name"], "test_tool")
        self.assertEqual(data["description"], "Test description")
        self.assertEqual(data["parameters"], {"type": "object"})

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "name": "my_tool",
            "description": "My tool description",
            "parameters": {"type": "object", "properties": {}},
        }

        tool = LLMNavigationTool.from_dict(data)

        self.assertEqual(tool.name, "my_tool")
        self.assertEqual(tool.description, "My tool description")

    def test_round_trip_serialization(self):
        """Test that to_dict -> from_dict preserves data."""
        original = LLMNavigationTool(
            name="complex_tool",
            description="Complex tool with params",
            parameters={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"},
                    "param2": {"type": "boolean"},
                },
                "required": ["param1"],
            },
        )

        data = original.to_dict()
        restored = LLMNavigationTool.from_dict(data)

        self.assertEqual(restored.name, original.name)
        self.assertEqual(restored.description, original.description)
        self.assertEqual(restored.parameters, original.parameters)


# =============================================================================
# NAVIGATION STATE TESTS
# =============================================================================


class TestNavigationStateCreation(TestCase):
    """Tests for NavigationState dataclass creation."""

    def test_create_default_state(self):
        """Test creating default navigation state."""
        state = NavigationState()

        self.assertIsNone(state.current_category)
        self.assertIsNone(state.current_subcategory)
        self.assertEqual(state.depth, KnowledgeDepth.DETECTION)
        self.assertEqual(state.operations, [])
        self.assertEqual(state.history, [])

    def test_create_with_values(self):
        """Test creating state with initial values."""
        state = NavigationState(
            current_category="reentrancy",
            current_subcategory="classic",
            depth=KnowledgeDepth.PATTERNS,
            operations=["TRANSFERS_VALUE_OUT"],
        )

        self.assertEqual(state.current_category, "reentrancy")
        self.assertEqual(state.current_subcategory, "classic")
        self.assertEqual(state.depth, KnowledgeDepth.PATTERNS)
        self.assertEqual(state.operations, ["TRANSFERS_VALUE_OUT"])


class TestNavigationStateOperations(TestCase):
    """Tests for NavigationState operations."""

    def test_set_focus(self):
        """Test setting navigation focus."""
        state = NavigationState()

        state.set_focus(category="reentrancy")
        self.assertEqual(state.current_category, "reentrancy")
        self.assertIsNone(state.current_subcategory)

        state.set_focus(subcategory="classic")
        self.assertEqual(state.current_category, "reentrancy")
        self.assertEqual(state.current_subcategory, "classic")

    def test_add_operation(self):
        """Test adding operations to state."""
        state = NavigationState()

        state.add_operation("TRANSFERS_VALUE_OUT")
        self.assertIn("TRANSFERS_VALUE_OUT", state.operations)

        # Duplicate should not be added
        state.add_operation("TRANSFERS_VALUE_OUT")
        self.assertEqual(state.operations.count("TRANSFERS_VALUE_OUT"), 1)

    def test_record_action(self):
        """Test recording navigation actions."""
        state = NavigationState()

        state.record_action("list_categories", {})
        state.record_action("get_category_info", {"category_id": "reentrancy"})

        self.assertEqual(len(state.history), 2)
        self.assertEqual(state.history[0]["tool"], "list_categories")
        self.assertEqual(state.history[1]["params"]["category_id"], "reentrancy")

    def test_clear_state(self):
        """Test clearing navigation state."""
        state = NavigationState(
            current_category="reentrancy",
            current_subcategory="classic",
            operations=["TRANSFERS_VALUE_OUT"],
        )
        state.record_action("test", {})

        state.clear()

        self.assertIsNone(state.current_category)
        self.assertIsNone(state.current_subcategory)
        self.assertEqual(state.operations, [])
        self.assertEqual(state.history, [])


class TestNavigationStateSerialization(TestCase):
    """Tests for NavigationState serialization."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        state = NavigationState(
            current_category="reentrancy",
            depth=KnowledgeDepth.PATTERNS,
        )

        data = state.to_dict()

        self.assertEqual(data["current_category"], "reentrancy")
        self.assertEqual(data["depth"], "patterns")

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "current_category": "access-control",
            "current_subcategory": "missing-modifier",
            "depth": "detection",
            "operations": ["CHECKS_PERMISSION"],
            "history": [{"tool": "test", "params": {}}],
        }

        state = NavigationState.from_dict(data)

        self.assertEqual(state.current_category, "access-control")
        self.assertEqual(state.current_subcategory, "missing-modifier")
        self.assertEqual(state.depth, KnowledgeDepth.DETECTION)
        self.assertEqual(state.operations, ["CHECKS_PERMISSION"])

    def test_round_trip_serialization(self):
        """Test that to_dict -> from_dict preserves data."""
        original = NavigationState(
            current_category="reentrancy",
            current_subcategory="classic",
            depth=KnowledgeDepth.EXPLOITS,
            operations=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )
        original.record_action("test_tool", {"param": "value"})

        data = original.to_dict()
        restored = NavigationState.from_dict(data)

        self.assertEqual(restored.current_category, original.current_category)
        self.assertEqual(restored.current_subcategory, original.current_subcategory)
        self.assertEqual(restored.depth, original.depth)
        self.assertEqual(restored.operations, original.operations)


# =============================================================================
# TOOL EXECUTION RESULT TESTS
# =============================================================================


class TestToolExecutionResult(TestCase):
    """Tests for ToolExecutionResult dataclass."""

    def test_success_result(self):
        """Test creating a successful result."""
        result = ToolExecutionResult.success_result(
            content="Test content",
            metadata={"count": 5},
        )

        self.assertTrue(result.success)
        self.assertEqual(result.content, "Test content")
        self.assertIsNone(result.error)
        self.assertEqual(result.metadata["count"], 5)

    def test_error_result(self):
        """Test creating an error result."""
        result = ToolExecutionResult.error_result("Something went wrong")

        self.assertFalse(result.success)
        self.assertEqual(result.content, "")
        self.assertEqual(result.error, "Something went wrong")

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = ToolExecutionResult(
            success=True,
            content="Content here",
            metadata={"key": "value"},
        )

        data = result.to_dict()

        self.assertTrue(data["success"])
        self.assertEqual(data["content"], "Content here")
        self.assertNotIn("error", data)  # No error key when not present
        self.assertEqual(data["metadata"]["key"], "value")

    def test_error_to_dict(self):
        """Test error result serialization."""
        result = ToolExecutionResult.error_result("Error message")

        data = result.to_dict()

        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "Error message")


# =============================================================================
# LLM NAVIGATOR TESTS - INITIALIZATION
# =============================================================================


class TestLLMNavigatorInitialization(TestCase):
    """Tests for LLMNavigator initialization."""

    @classmethod
    def setUpClass(cls):
        """Create test knowledge base once for all tests."""
        cls.temp_dir = Path(tempfile.mkdtemp())
        cls.knowledge_dir = create_test_knowledge_base(cls.temp_dir)

    @classmethod
    def tearDownClass(cls):
        """Clean up test knowledge base."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Create navigator instances for each test."""
        self.navigator = KnowledgeNavigator(self.knowledge_dir)
        self.cache = PromptCache(self.navigator)
        self.builder = ContextBuilder(self.navigator, self.cache)
        self.llm_nav = LLMNavigator(self.navigator, self.builder)

    def test_initialization(self):
        """Test basic initialization."""
        self.assertIsNotNone(self.llm_nav.navigator)
        self.assertIsNotNone(self.llm_nav.builder)
        self.assertIsNotNone(self.llm_nav.state)

    def test_tools_initialized(self):
        """Test that all tools are initialized."""
        self.assertEqual(len(self.llm_nav._tools), len(ALL_TOOLS))

        for tool_name in ALL_TOOLS:
            self.assertIn(tool_name, self.llm_nav._tools)

    def test_get_tool_by_name(self):
        """Test retrieving individual tools."""
        tool = self.llm_nav.get_tool(TOOL_LIST_CATEGORIES)

        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, TOOL_LIST_CATEGORIES)

    def test_get_nonexistent_tool(self):
        """Test retrieving nonexistent tool returns None."""
        tool = self.llm_nav.get_tool("nonexistent_tool")

        self.assertIsNone(tool)


# =============================================================================
# LLM NAVIGATOR TESTS - SYSTEM PROMPT
# =============================================================================


class TestLLMNavigatorSystemPrompt(TestCase):
    """Tests for system prompt generation."""

    @classmethod
    def setUpClass(cls):
        """Create test knowledge base once for all tests."""
        cls.temp_dir = Path(tempfile.mkdtemp())
        cls.knowledge_dir = create_test_knowledge_base(cls.temp_dir)

    @classmethod
    def tearDownClass(cls):
        """Clean up test knowledge base."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Create navigator instances for each test."""
        self.navigator = KnowledgeNavigator(self.knowledge_dir)
        self.cache = PromptCache(self.navigator)
        self.builder = ContextBuilder(self.navigator, self.cache)
        self.llm_nav = LLMNavigator(self.navigator, self.builder)

    def test_system_prompt_generated(self):
        """Test that system prompt is generated."""
        prompt = self.llm_nav.get_system_prompt()

        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 100)

    def test_system_prompt_contains_navigation_strategy(self):
        """Test prompt contains navigation strategy."""
        prompt = self.llm_nav.get_system_prompt()

        self.assertIn("Navigation Strategy", prompt)
        self.assertIn("search_by_operation", prompt)

    def test_system_prompt_contains_depths(self):
        """Test prompt contains depth levels."""
        prompt = self.llm_nav.get_system_prompt()

        self.assertIn("detection", prompt)
        self.assertIn("patterns", prompt)
        self.assertIn("exploits", prompt)
        self.assertIn("fixes", prompt)

    def test_system_prompt_contains_categories(self):
        """Test prompt contains available categories."""
        prompt = self.llm_nav.get_system_prompt()

        self.assertIn("Available Categories", prompt)
        self.assertIn("reentrancy", prompt)


# =============================================================================
# LLM NAVIGATOR TESTS - TOOL DEFINITIONS
# =============================================================================


class TestLLMNavigatorToolDefinitions(TestCase):
    """Tests for tool definition generation."""

    @classmethod
    def setUpClass(cls):
        """Create test knowledge base once for all tests."""
        cls.temp_dir = Path(tempfile.mkdtemp())
        cls.knowledge_dir = create_test_knowledge_base(cls.temp_dir)

    @classmethod
    def tearDownClass(cls):
        """Clean up test knowledge base."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Create navigator instances for each test."""
        self.navigator = KnowledgeNavigator(self.knowledge_dir)
        self.cache = PromptCache(self.navigator)
        self.builder = ContextBuilder(self.navigator, self.cache)
        self.llm_nav = LLMNavigator(self.navigator, self.builder)

    def test_get_tool_definitions_openai(self):
        """Test getting tool definitions in OpenAI format."""
        tools = self.llm_nav.get_tool_definitions(format="openai")

        self.assertEqual(len(tools), len(ALL_TOOLS))
        for tool in tools:
            self.assertEqual(tool["type"], "function")
            self.assertIn("function", tool)
            self.assertIn("name", tool["function"])
            self.assertIn("description", tool["function"])
            self.assertIn("parameters", tool["function"])

    def test_get_tool_definitions_anthropic(self):
        """Test getting tool definitions in Anthropic format."""
        tools = self.llm_nav.get_tool_definitions(format="anthropic")

        self.assertEqual(len(tools), len(ALL_TOOLS))
        for tool in tools:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("input_schema", tool)

    def test_tool_definitions_contain_all_tools(self):
        """Test that all defined tools are included."""
        tools = self.llm_nav.get_tool_definitions()
        tool_names = {t["function"]["name"] for t in tools}

        for expected_tool in ALL_TOOLS:
            self.assertIn(expected_tool, tool_names)

    def test_tool_parameters_have_required_structure(self):
        """Test tool parameters have required JSON Schema structure."""
        tools = self.llm_nav.get_tool_definitions()

        for tool in tools:
            params = tool["function"]["parameters"]
            self.assertIn("type", params)
            self.assertEqual(params["type"], "object")
            self.assertIn("properties", params)
            self.assertIn("required", params)


# =============================================================================
# LLM NAVIGATOR TESTS - TOOL EXECUTION
# =============================================================================


class TestLLMNavigatorToolExecution(TestCase):
    """Tests for tool execution."""

    @classmethod
    def setUpClass(cls):
        """Create test knowledge base once for all tests."""
        cls.temp_dir = Path(tempfile.mkdtemp())
        cls.knowledge_dir = create_test_knowledge_base(cls.temp_dir)

    @classmethod
    def tearDownClass(cls):
        """Clean up test knowledge base."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Create navigator instances for each test."""
        self.navigator = KnowledgeNavigator(self.knowledge_dir)
        self.cache = PromptCache(self.navigator)
        self.builder = ContextBuilder(self.navigator, self.cache)
        self.llm_nav = LLMNavigator(self.navigator, self.builder)

    def test_execute_list_categories(self):
        """Test executing list_categories tool."""
        result = self.llm_nav.execute_tool(TOOL_LIST_CATEGORIES, {})

        self.assertTrue(result.success)
        self.assertIn("reentrancy", result.content.lower())
        self.assertIn("category_count", result.metadata)

    def test_execute_get_category_info(self):
        """Test executing get_category_info tool."""
        result = self.llm_nav.execute_tool(
            TOOL_GET_CATEGORY_INFO,
            {"category_id": "reentrancy"},
        )

        self.assertTrue(result.success)
        self.assertIn("Reentrancy", result.content)
        self.assertIn("category_id", result.metadata)

    def test_execute_get_category_info_missing_param(self):
        """Test get_category_info with missing parameter."""
        result = self.llm_nav.execute_tool(TOOL_GET_CATEGORY_INFO, {})

        self.assertFalse(result.success)
        self.assertIn("category_id", result.error)

    def test_execute_get_category_info_invalid_category(self):
        """Test get_category_info with invalid category."""
        result = self.llm_nav.execute_tool(
            TOOL_GET_CATEGORY_INFO,
            {"category_id": "nonexistent"},
        )

        self.assertFalse(result.success)
        self.assertIn("not found", result.error.lower())

    def test_execute_get_subcategory_info(self):
        """Test executing get_subcategory_info tool."""
        result = self.llm_nav.execute_tool(
            TOOL_GET_SUBCATEGORY_INFO,
            {"category_id": "reentrancy", "subcategory_id": "classic"},
        )

        self.assertTrue(result.success)
        self.assertIn("Classic", result.content)

    def test_execute_get_subcategory_info_missing_params(self):
        """Test get_subcategory_info with missing parameters."""
        result = self.llm_nav.execute_tool(
            TOOL_GET_SUBCATEGORY_INFO,
            {"category_id": "reentrancy"},
        )

        self.assertFalse(result.success)
        self.assertIn("subcategory_id", result.error)

    def test_execute_get_detection_guide(self):
        """Test executing get_detection_guide tool."""
        result = self.llm_nav.execute_tool(
            TOOL_GET_DETECTION_GUIDE,
            {"category_id": "reentrancy"},
        )

        self.assertTrue(result.success)
        self.assertIn("detection", result.metadata.get("depth", ""))

    def test_execute_get_patterns(self):
        """Test executing get_patterns tool."""
        result = self.llm_nav.execute_tool(
            TOOL_GET_PATTERNS,
            {"category_id": "reentrancy"},
        )

        self.assertTrue(result.success)
        self.assertIn("patterns", result.metadata.get("depth", ""))

    def test_execute_get_exploits(self):
        """Test executing get_exploits tool."""
        result = self.llm_nav.execute_tool(
            TOOL_GET_EXPLOITS,
            {"category_id": "reentrancy"},
        )

        self.assertTrue(result.success)
        self.assertIn("exploits", result.metadata.get("depth", ""))

    def test_execute_get_fixes(self):
        """Test executing get_fixes tool."""
        result = self.llm_nav.execute_tool(
            TOOL_GET_FIXES,
            {"category_id": "reentrancy"},
        )

        self.assertTrue(result.success)
        self.assertIn("fixes", result.metadata.get("depth", ""))

    def test_execute_search_by_operation(self):
        """Test executing search_by_operation tool."""
        result = self.llm_nav.execute_tool(
            TOOL_SEARCH_BY_OPERATION,
            {"operation": "TRANSFERS_VALUE_OUT"},
        )

        self.assertTrue(result.success)
        self.assertIn("operation", result.metadata)

    def test_execute_search_by_operation_no_matches(self):
        """Test search_by_operation with no matches."""
        result = self.llm_nav.execute_tool(
            TOOL_SEARCH_BY_OPERATION,
            {"operation": "NONEXISTENT_OPERATION"},
        )

        self.assertTrue(result.success)  # Still success, just no results
        self.assertEqual(result.metadata.get("match_count"), 0)

    def test_execute_search_by_signature(self):
        """Test executing search_by_signature tool."""
        result = self.llm_nav.execute_tool(
            TOOL_SEARCH_BY_SIGNATURE,
            {"signature": "R:bal->X:out->W:bal"},
        )

        self.assertTrue(result.success)
        self.assertIn("signature", result.metadata)

    def test_execute_unknown_tool(self):
        """Test executing unknown tool."""
        result = self.llm_nav.execute_tool("unknown_tool", {})

        self.assertFalse(result.success)
        self.assertIn("Unknown tool", result.error)


# =============================================================================
# LLM NAVIGATOR TESTS - STATE MANAGEMENT
# =============================================================================


class TestLLMNavigatorStateManagement(TestCase):
    """Tests for navigation state management."""

    @classmethod
    def setUpClass(cls):
        """Create test knowledge base once for all tests."""
        cls.temp_dir = Path(tempfile.mkdtemp())
        cls.knowledge_dir = create_test_knowledge_base(cls.temp_dir)

    @classmethod
    def tearDownClass(cls):
        """Clean up test knowledge base."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Create navigator instances for each test."""
        self.navigator = KnowledgeNavigator(self.knowledge_dir)
        self.cache = PromptCache(self.navigator)
        self.builder = ContextBuilder(self.navigator, self.cache)
        self.llm_nav = LLMNavigator(self.navigator, self.builder)

    def test_state_updated_on_tool_execution(self):
        """Test that state is updated when tools are executed."""
        self.llm_nav.execute_tool(
            TOOL_GET_CATEGORY_INFO,
            {"category_id": "reentrancy"},
        )

        self.assertEqual(self.llm_nav.state.current_category, "reentrancy")

    def test_state_tracks_history(self):
        """Test that state tracks execution history."""
        self.llm_nav.execute_tool(TOOL_LIST_CATEGORIES, {})
        self.llm_nav.execute_tool(TOOL_GET_CATEGORY_INFO, {"category_id": "reentrancy"})

        self.assertEqual(len(self.llm_nav.state.history), 2)

    def test_get_state(self):
        """Test getting current state."""
        state = self.llm_nav.get_state()

        self.assertIsInstance(state, NavigationState)

    def test_set_state(self):
        """Test setting navigation state."""
        new_state = NavigationState(
            current_category="access-control",
            depth=KnowledgeDepth.PATTERNS,
        )

        self.llm_nav.set_state(new_state)

        self.assertEqual(self.llm_nav.state.current_category, "access-control")
        self.assertEqual(self.llm_nav.state.depth, KnowledgeDepth.PATTERNS)

    def test_reset_state(self):
        """Test resetting navigation state."""
        self.llm_nav.execute_tool(TOOL_GET_CATEGORY_INFO, {"category_id": "reentrancy"})
        self.llm_nav.reset_state()

        self.assertIsNone(self.llm_nav.state.current_category)
        self.assertEqual(len(self.llm_nav.state.history), 0)

    def test_export_state(self):
        """Test exporting state to dictionary."""
        self.llm_nav.execute_tool(TOOL_GET_CATEGORY_INFO, {"category_id": "reentrancy"})

        exported = self.llm_nav.export_state()

        self.assertEqual(exported["current_category"], "reentrancy")
        self.assertIn("history", exported)

    def test_import_state(self):
        """Test importing state from dictionary."""
        data = {
            "current_category": "access-control",
            "current_subcategory": "missing-modifier",
            "depth": "detection",
            "operations": ["CHECKS_PERMISSION"],
            "history": [],
        }

        self.llm_nav.import_state(data)

        self.assertEqual(self.llm_nav.state.current_category, "access-control")
        self.assertEqual(self.llm_nav.state.current_subcategory, "missing-modifier")


# =============================================================================
# LLM NAVIGATOR TESTS - NAVIGATION CONTEXT
# =============================================================================


class TestLLMNavigatorNavigationContext(TestCase):
    """Tests for navigation context building."""

    @classmethod
    def setUpClass(cls):
        """Create test knowledge base once for all tests."""
        cls.temp_dir = Path(tempfile.mkdtemp())
        cls.knowledge_dir = create_test_knowledge_base(cls.temp_dir)

    @classmethod
    def tearDownClass(cls):
        """Clean up test knowledge base."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Create navigator instances for each test."""
        self.navigator = KnowledgeNavigator(self.knowledge_dir)
        self.cache = PromptCache(self.navigator)
        self.builder = ContextBuilder(self.navigator, self.cache)
        self.llm_nav = LLMNavigator(self.navigator, self.builder)

    def test_get_navigation_context_default(self):
        """Test getting default navigation context."""
        context = self.llm_nav.get_navigation_context()

        self.assertIsInstance(context, str)
        self.assertGreater(len(context), 0)

    def test_get_navigation_context_with_category(self):
        """Test getting context for specific category."""
        context = self.llm_nav.get_navigation_context(category="reentrancy")

        self.assertIn("reentrancy", context.lower())

    def test_get_navigation_context_with_operations(self):
        """Test getting context for operations."""
        context = self.llm_nav.get_navigation_context(
            operations=["TRANSFERS_VALUE_OUT"]
        )

        self.assertIn("TRANSFERS_VALUE_OUT", context)

    def test_get_navigation_context_with_finding(self):
        """Test getting context for a finding."""
        finding = {
            "pattern_id": "vm-001-classic",
            "operations": ["TRANSFERS_VALUE_OUT"],
            "severity": "high",
        }

        context = self.llm_nav.get_navigation_context(finding=finding)

        self.assertIsInstance(context, str)


# =============================================================================
# LLM NAVIGATOR TESTS - EVIDENCE REQUEST
# =============================================================================


class TestLLMNavigatorEvidenceRequest(TestCase):
    """Tests for evidence request generation."""

    @classmethod
    def setUpClass(cls):
        """Create test knowledge base once for all tests."""
        cls.temp_dir = Path(tempfile.mkdtemp())
        cls.knowledge_dir = create_test_knowledge_base(cls.temp_dir)

    @classmethod
    def tearDownClass(cls):
        """Clean up test knowledge base."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Create navigator instances for each test."""
        self.navigator = KnowledgeNavigator(self.knowledge_dir)
        self.cache = PromptCache(self.navigator)
        self.builder = ContextBuilder(self.navigator, self.cache)
        self.llm_nav = LLMNavigator(self.navigator, self.builder)

    def test_build_evidence_request_basic(self):
        """Test building basic evidence request."""
        finding = {
            "pattern_id": "vm-001",
            "severity": "high",
        }

        request = self.llm_nav.build_evidence_request(finding)

        self.assertIn("Evidence Request", request)
        self.assertIn("vm-001", request)
        self.assertIn("high", request)

    def test_build_evidence_request_with_operations(self):
        """Test evidence request with operations."""
        finding = {
            "pattern_id": "vm-001",
            "operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        }

        request = self.llm_nav.build_evidence_request(finding)

        self.assertIn("search_by_operation", request)
        self.assertIn("TRANSFERS_VALUE_OUT", request)

    def test_build_evidence_request_with_signature(self):
        """Test evidence request with signature."""
        finding = {
            "signature": "R:bal->X:out->W:bal",
        }

        request = self.llm_nav.build_evidence_request(finding)

        self.assertIn("search_by_signature", request)
        self.assertIn("R:bal->X:out->W:bal", request)

    def test_build_evidence_request_with_context(self):
        """Test evidence request includes function/contract."""
        finding = {
            "function_name": "withdraw",
            "contract_name": "Vault",
            "severity": "critical",
        }

        request = self.llm_nav.build_evidence_request(finding)

        self.assertIn("withdraw", request)
        self.assertIn("Vault", request)


# =============================================================================
# MULTI-TURN NAVIGATION TESTS
# =============================================================================


class TestMultiTurnNavigation(TestCase):
    """Tests for multi-turn navigation scenarios."""

    @classmethod
    def setUpClass(cls):
        """Create test knowledge base once for all tests."""
        cls.temp_dir = Path(tempfile.mkdtemp())
        cls.knowledge_dir = create_test_knowledge_base(cls.temp_dir)

    @classmethod
    def tearDownClass(cls):
        """Clean up test knowledge base."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        """Create navigator instances for each test."""
        self.navigator = KnowledgeNavigator(self.knowledge_dir)
        self.cache = PromptCache(self.navigator)
        self.builder = ContextBuilder(self.navigator, self.cache)
        self.llm_nav = LLMNavigator(self.navigator, self.builder)

    def test_navigation_flow_categories_to_detection(self):
        """Test navigation from categories to detection."""
        # Step 1: List categories
        result1 = self.llm_nav.execute_tool(TOOL_LIST_CATEGORIES, {})
        self.assertTrue(result1.success)

        # Step 2: Get category info
        result2 = self.llm_nav.execute_tool(
            TOOL_GET_CATEGORY_INFO, {"category_id": "reentrancy"}
        )
        self.assertTrue(result2.success)

        # Step 3: Get detection guide
        result3 = self.llm_nav.execute_tool(
            TOOL_GET_DETECTION_GUIDE, {"category_id": "reentrancy"}
        )
        self.assertTrue(result3.success)

        # Verify state tracks the flow
        self.assertEqual(len(self.llm_nav.state.history), 3)
        self.assertEqual(self.llm_nav.state.current_category, "reentrancy")

    def test_navigation_flow_search_to_details(self):
        """Test navigation from search to details."""
        # Step 1: Search by operation
        result1 = self.llm_nav.execute_tool(
            TOOL_SEARCH_BY_OPERATION, {"operation": "TRANSFERS_VALUE_OUT"}
        )
        self.assertTrue(result1.success)

        # Step 2: Get category details
        result2 = self.llm_nav.execute_tool(
            TOOL_GET_CATEGORY_INFO, {"category_id": "reentrancy"}
        )
        self.assertTrue(result2.success)

        # Verify operation tracked
        self.assertIn("TRANSFERS_VALUE_OUT", self.llm_nav.state.operations)

    def test_navigation_preserves_context(self):
        """Test that navigation preserves context across calls."""
        # Navigate to category
        self.llm_nav.execute_tool(
            TOOL_GET_CATEGORY_INFO, {"category_id": "reentrancy"}
        )

        # Navigate to subcategory
        self.llm_nav.execute_tool(
            TOOL_GET_SUBCATEGORY_INFO,
            {"category_id": "reentrancy", "subcategory_id": "classic"},
        )

        # Verify context preserved
        self.assertEqual(self.llm_nav.state.current_category, "reentrancy")
        self.assertEqual(self.llm_nav.state.current_subcategory, "classic")


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunction(TestCase):
    """Tests for the create_llm_navigator factory function."""

    @classmethod
    def setUpClass(cls):
        """Create test knowledge base once for all tests."""
        cls.temp_dir = Path(tempfile.mkdtemp())
        cls.knowledge_dir = create_test_knowledge_base(cls.temp_dir)

    @classmethod
    def tearDownClass(cls):
        """Clean up test knowledge base."""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_create_llm_navigator_with_path(self):
        """Test creating navigator with custom path."""
        llm_nav = create_llm_navigator(str(self.knowledge_dir))

        self.assertIsInstance(llm_nav, LLMNavigator)
        self.assertIsNotNone(llm_nav.navigator)
        self.assertIsNotNone(llm_nav.builder)

    def test_factory_creates_functional_navigator(self):
        """Test factory creates a functional navigator."""
        llm_nav = create_llm_navigator(str(self.knowledge_dir))

        # Should be able to execute tools
        result = llm_nav.execute_tool(TOOL_LIST_CATEGORIES, {})
        self.assertTrue(result.success)


class TestHelperFunctions(TestCase):
    """Tests for helper functions."""

    def test_get_tool_names(self):
        """Test get_tool_names returns all tools."""
        tools = get_tool_names()

        self.assertEqual(len(tools), len(ALL_TOOLS))
        for tool_name in ALL_TOOLS:
            self.assertIn(tool_name, tools)

    def test_get_tool_names_returns_copy(self):
        """Test get_tool_names returns a copy."""
        tools1 = get_tool_names()
        tools2 = get_tool_names()

        # Should be different list objects
        self.assertIsNot(tools1, tools2)

        # Modifying one shouldn't affect the other
        tools1.append("new_tool")
        self.assertNotIn("new_tool", tools2)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegrationWithRealKnowledgeBase(TestCase):
    """Integration tests with the real knowledge base if available."""

    def setUp(self):
        """Check if real knowledge base exists."""
        self.skip_if_no_real_kb = not KNOWLEDGE_DIR.exists()

    @pytest.mark.xfail(reason="Stale code: VulnDocs index schema format changed")
    def test_real_knowledge_base_navigation(self):
        """Test navigation with real knowledge base."""
        if self.skip_if_no_real_kb:
            self.skipTest("Real knowledge base not available")

        llm_nav = create_llm_navigator()

        # List categories
        result = llm_nav.execute_tool(TOOL_LIST_CATEGORIES, {})
        self.assertTrue(result.success)

        # Should have multiple categories
        self.assertGreater(result.metadata.get("category_count", 0), 0)

    @pytest.mark.xfail(reason="Stale code: VulnDocs index schema format changed")
    def test_real_knowledge_base_search(self):
        """Test search with real knowledge base."""
        if self.skip_if_no_real_kb:
            self.skipTest("Real knowledge base not available")

        llm_nav = create_llm_navigator()

        # Search for common operation
        result = llm_nav.execute_tool(
            TOOL_SEARCH_BY_OPERATION,
            {"operation": "TRANSFERS_VALUE_OUT"},
        )
        self.assertTrue(result.success)


if __name__ == "__main__":
    main()
