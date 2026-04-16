"""VulnDocs LLM Navigation Interface.

Phase 17.7: LLM Navigation Interface for VulnDocs.

This module provides the LLM-facing interface for navigating the VulnDocs
knowledge base. It enables LLMs to:

1. Navigate the knowledge hierarchy via tool calls
2. Retrieve targeted vulnerability knowledge
3. Build context based on findings and operations
4. Support multi-turn navigation with state tracking

Design Philosophy:
- Deterministic outputs (Tier A data only)
- No LLM reasoning in tool outputs - just knowledge retrieval
- Support prompt caching for efficiency
- Keep context minimal and targeted

Usage:
    from alphaswarm_sol.knowledge.vulndocs import KnowledgeNavigator
    from alphaswarm_sol.knowledge.vulndocs.builder import ContextBuilder
    from alphaswarm_sol.knowledge.vulndocs.cache import PromptCache
    from alphaswarm_sol.knowledge.vulndocs.llm_interface import LLMNavigator

    # Initialize
    navigator = KnowledgeNavigator()
    cache = PromptCache(navigator)
    builder = ContextBuilder(navigator, cache)
    llm_nav = LLMNavigator(navigator, builder)

    # Get system prompt for LLM
    system_prompt = llm_nav.get_system_prompt()

    # Get tool definitions (OpenAI/Anthropic compatible)
    tools = llm_nav.get_tool_definitions()

    # Execute a tool call
    result = llm_nav.execute_tool("list_categories", {})

    # Build navigation context
    context = llm_nav.get_navigation_context(category="reentrancy")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from alphaswarm_sol.knowledge.vulndocs.schema import (
    Category,
    KnowledgeDepth,
    Subcategory,
)

if TYPE_CHECKING:
    from alphaswarm_sol.knowledge.vulndocs.navigator import KnowledgeNavigator
    from alphaswarm_sol.knowledge.vulndocs.builder import ContextBuilder


# =============================================================================
# CONSTANTS
# =============================================================================

# Tool name constants
TOOL_LIST_CATEGORIES = "list_categories"
TOOL_GET_CATEGORY_INFO = "get_category_info"
TOOL_GET_SUBCATEGORY_INFO = "get_subcategory_info"
TOOL_GET_DETECTION_GUIDE = "get_detection_guide"
TOOL_GET_PATTERNS = "get_patterns"
TOOL_GET_EXPLOITS = "get_exploits"
TOOL_GET_FIXES = "get_fixes"
TOOL_SEARCH_BY_OPERATION = "search_by_operation"
TOOL_SEARCH_BY_SIGNATURE = "search_by_signature"

# All available tool names
ALL_TOOLS = [
    TOOL_LIST_CATEGORIES,
    TOOL_GET_CATEGORY_INFO,
    TOOL_GET_SUBCATEGORY_INFO,
    TOOL_GET_DETECTION_GUIDE,
    TOOL_GET_PATTERNS,
    TOOL_GET_EXPLOITS,
    TOOL_GET_FIXES,
    TOOL_SEARCH_BY_OPERATION,
    TOOL_SEARCH_BY_SIGNATURE,
]

# Navigation state keys
STATE_CURRENT_CATEGORY = "current_category"
STATE_CURRENT_SUBCATEGORY = "current_subcategory"
STATE_DEPTH = "depth"
STATE_OPERATIONS = "operations"
STATE_HISTORY = "history"


# =============================================================================
# DATACLASSES
# =============================================================================


@dataclass
class LLMNavigationTool:
    """Defines a tool that LLMs can use to navigate VulnDocs.

    Each tool represents a navigation action that returns deterministic
    knowledge from the VulnDocs knowledge base.

    Attributes:
        name: The unique tool name (used in function calls).
        description: Human-readable description of what the tool does.
        parameters: JSON Schema defining the tool's input parameters.
    """

    name: str
    description: str
    parameters: Dict[str, Any]

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format.

        Returns:
            Dictionary compatible with OpenAI's function calling API.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convert to Anthropic tool use format.

        Returns:
            Dictionary compatible with Anthropic's tool use API.
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of the tool definition.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMNavigationTool":
        """Deserialize from dictionary.

        Args:
            data: Dictionary containing tool definition.

        Returns:
            LLMNavigationTool instance.
        """
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
        )


@dataclass
class NavigationState:
    """Tracks multi-turn navigation state.

    Maintains context across multiple LLM interactions to enable
    coherent navigation through the knowledge hierarchy.

    Attributes:
        current_category: Currently focused category ID.
        current_subcategory: Currently focused subcategory ID.
        depth: Current knowledge depth level.
        operations: List of detected operations.
        history: List of navigation actions taken.
    """

    current_category: Optional[str] = None
    current_subcategory: Optional[str] = None
    depth: KnowledgeDepth = KnowledgeDepth.DETECTION
    operations: List[str] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            STATE_CURRENT_CATEGORY: self.current_category,
            STATE_CURRENT_SUBCATEGORY: self.current_subcategory,
            STATE_DEPTH: self.depth.value,
            STATE_OPERATIONS: self.operations,
            STATE_HISTORY: self.history,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NavigationState":
        """Deserialize from dictionary."""
        depth_value = data.get(STATE_DEPTH, "detection")
        depth = KnowledgeDepth.from_string(depth_value)

        return cls(
            current_category=data.get(STATE_CURRENT_CATEGORY),
            current_subcategory=data.get(STATE_CURRENT_SUBCATEGORY),
            depth=depth,
            operations=data.get(STATE_OPERATIONS, []),
            history=data.get(STATE_HISTORY, []),
        )

    def record_action(self, tool_name: str, params: Dict[str, Any]) -> None:
        """Record a navigation action to history."""
        self.history.append({
            "tool": tool_name,
            "params": params,
        })

    def set_focus(
        self,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
    ) -> None:
        """Set the current navigation focus."""
        if category is not None:
            self.current_category = category
        if subcategory is not None:
            self.current_subcategory = subcategory

    def add_operation(self, operation: str) -> None:
        """Add an operation to the tracked operations."""
        if operation not in self.operations:
            self.operations.append(operation)

    def clear(self) -> None:
        """Clear the navigation state."""
        self.current_category = None
        self.current_subcategory = None
        self.depth = KnowledgeDepth.DETECTION
        self.operations = []
        self.history = []


@dataclass
class ToolExecutionResult:
    """Result of executing a navigation tool.

    Attributes:
        success: Whether the tool execution succeeded.
        content: The retrieved knowledge content.
        error: Error message if execution failed.
        metadata: Additional metadata about the execution.
    """

    success: bool
    content: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result = {
            "success": self.success,
            "content": self.content,
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def success_result(
        cls,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ToolExecutionResult":
        """Create a successful result."""
        return cls(
            success=True,
            content=content,
            metadata=metadata or {},
        )

    @classmethod
    def error_result(cls, error: str) -> "ToolExecutionResult":
        """Create an error result."""
        return cls(
            success=False,
            content="",
            error=error,
        )


# =============================================================================
# LLM NAVIGATOR CLASS
# =============================================================================


class LLMNavigator:
    """Interface for LLM-driven navigation of VulnDocs.

    Provides a structured interface for LLMs to navigate the VulnDocs
    knowledge base using tool calls. All outputs are deterministic
    (Tier A data) with no LLM reasoning.

    Attributes:
        navigator: KnowledgeNavigator instance for knowledge retrieval.
        builder: ContextBuilder instance for context optimization.
        state: Current navigation state.
    """

    def __init__(
        self,
        navigator: "KnowledgeNavigator",
        builder: "ContextBuilder",
    ) -> None:
        """Initialize the LLM navigator.

        Args:
            navigator: KnowledgeNavigator instance for loading knowledge.
            builder: ContextBuilder instance for context optimization.
        """
        self.navigator = navigator
        self.builder = builder
        self.state = NavigationState()
        self._tools: Dict[str, LLMNavigationTool] = {}
        self._init_tools()

    # =========================================================================
    # SYSTEM PROMPT GENERATION
    # =========================================================================

    def get_system_prompt(self) -> str:
        """Generate system prompt teaching LLM how to navigate.

        Returns:
            System prompt string with navigation instructions.
        """
        lines = [
            "# VulnDocs Knowledge Navigation",
            "",
            "You have access to VulnDocs, a curated vulnerability knowledge base.",
            "Use the provided tools to retrieve specific vulnerability knowledge.",
            "",
            "## Navigation Strategy",
            "",
            "1. **Start with operations/signatures**: If you have detected semantic",
            "   operations or behavioral signatures, use `search_by_operation` or",
            "   `search_by_signature` to find relevant categories.",
            "",
            "2. **Explore categories**: Use `list_categories` to see available",
            "   vulnerability categories, then `get_category_info` for details.",
            "",
            "3. **Drill into subcategories**: Use `get_subcategory_info` to get",
            "   detailed information about specific vulnerability types.",
            "",
            "4. **Get targeted knowledge**: Use specialized tools:",
            "   - `get_detection_guide`: Graph signals, behavioral patterns",
            "   - `get_patterns`: Vulnerable and safe code examples",
            "   - `get_exploits`: Real-world exploit references",
            "   - `get_fixes`: Remediation recommendations",
            "",
            "## Available Knowledge Depths",
            "",
            "- `index`: Category/subcategory names only (~200 tokens)",
            "- `overview`: High-level descriptions (~500 tokens)",
            "- `detection`: Graph signals and behavioral patterns (~1000 tokens)",
            "- `patterns`: Vulnerable and safe code examples (~1500 tokens)",
            "- `exploits`: Real-world exploit references (~1000 tokens)",
            "- `fixes`: Remediation recommendations (~800 tokens)",
            "- `full`: All available content (~5000 tokens)",
            "",
            "## Key Principles",
            "",
            "- All tool outputs are **deterministic** and factual",
            "- Knowledge is organized by **behavioral patterns**, not function names",
            "- Each finding should link to specific **evidence** from the knowledge",
            "- Use **minimal context** - retrieve only what's needed",
            "",
        ]

        # Add category overview
        lines.append("## Available Categories")
        lines.append("")
        try:
            for cat_id in self.navigator.list_categories():
                try:
                    category = self.navigator.get_category(cat_id)
                    lines.append(f"- **{category.name}** (`{cat_id}`)")
                except (ValueError, FileNotFoundError):
                    lines.append(f"- `{cat_id}`")
        except (ValueError, FileNotFoundError):
            lines.append("- (Run `list_categories` to see available categories)")
        lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # TOOL DEFINITIONS
    # =========================================================================

    def _init_tools(self) -> None:
        """Initialize all navigation tool definitions."""
        self._tools = {
            TOOL_LIST_CATEGORIES: self._define_list_categories(),
            TOOL_GET_CATEGORY_INFO: self._define_get_category_info(),
            TOOL_GET_SUBCATEGORY_INFO: self._define_get_subcategory_info(),
            TOOL_GET_DETECTION_GUIDE: self._define_get_detection_guide(),
            TOOL_GET_PATTERNS: self._define_get_patterns(),
            TOOL_GET_EXPLOITS: self._define_get_exploits(),
            TOOL_GET_FIXES: self._define_get_fixes(),
            TOOL_SEARCH_BY_OPERATION: self._define_search_by_operation(),
            TOOL_SEARCH_BY_SIGNATURE: self._define_search_by_signature(),
        }

    def _define_list_categories(self) -> LLMNavigationTool:
        """Define the list_categories tool."""
        return LLMNavigationTool(
            name=TOOL_LIST_CATEGORIES,
            description="List all available vulnerability categories in VulnDocs. "
            "Returns category IDs, names, and brief descriptions.",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    def _define_get_category_info(self) -> LLMNavigationTool:
        """Define the get_category_info tool."""
        return LLMNavigationTool(
            name=TOOL_GET_CATEGORY_INFO,
            description="Get detailed information about a vulnerability category, "
            "including description, severity range, subcategories, "
            "relevant properties, and semantic operations.",
            parameters={
                "type": "object",
                "properties": {
                    "category_id": {
                        "type": "string",
                        "description": "The category ID (e.g., 'reentrancy', 'access-control')",
                    },
                },
                "required": ["category_id"],
            },
        )

    def _define_get_subcategory_info(self) -> LLMNavigationTool:
        """Define the get_subcategory_info tool."""
        return LLMNavigationTool(
            name=TOOL_GET_SUBCATEGORY_INFO,
            description="Get detailed information about a vulnerability subcategory, "
            "including description, severity range, patterns, and graph signals.",
            parameters={
                "type": "object",
                "properties": {
                    "category_id": {
                        "type": "string",
                        "description": "The parent category ID",
                    },
                    "subcategory_id": {
                        "type": "string",
                        "description": "The subcategory ID (e.g., 'classic', 'cross-function')",
                    },
                },
                "required": ["category_id", "subcategory_id"],
            },
        )

    def _define_get_detection_guide(self) -> LLMNavigationTool:
        """Define the get_detection_guide tool."""
        return LLMNavigationTool(
            name=TOOL_GET_DETECTION_GUIDE,
            description="Get detection guidance for a vulnerability type, "
            "including graph signals, behavioral signatures, operation sequences, "
            "and false positive indicators.",
            parameters={
                "type": "object",
                "properties": {
                    "category_id": {
                        "type": "string",
                        "description": "The category ID",
                    },
                    "subcategory_id": {
                        "type": "string",
                        "description": "The subcategory ID (optional, for more specific guidance)",
                    },
                },
                "required": ["category_id"],
            },
        )

    def _define_get_patterns(self) -> LLMNavigationTool:
        """Define the get_patterns tool."""
        return LLMNavigationTool(
            name=TOOL_GET_PATTERNS,
            description="Get known vulnerable and safe code patterns for a vulnerability type. "
            "Includes code examples and pattern identifiers.",
            parameters={
                "type": "object",
                "properties": {
                    "category_id": {
                        "type": "string",
                        "description": "The category ID",
                    },
                    "subcategory_id": {
                        "type": "string",
                        "description": "The subcategory ID (optional)",
                    },
                },
                "required": ["category_id"],
            },
        )

    def _define_get_exploits(self) -> LLMNavigationTool:
        """Define the get_exploits tool."""
        return LLMNavigationTool(
            name=TOOL_GET_EXPLOITS,
            description="Get real-world exploit examples for a vulnerability type. "
            "Includes protocol names, dates, losses, and attack descriptions.",
            parameters={
                "type": "object",
                "properties": {
                    "category_id": {
                        "type": "string",
                        "description": "The category ID",
                    },
                    "subcategory_id": {
                        "type": "string",
                        "description": "The subcategory ID (optional)",
                    },
                },
                "required": ["category_id"],
            },
        )

    def _define_get_fixes(self) -> LLMNavigationTool:
        """Define the get_fixes tool."""
        return LLMNavigationTool(
            name=TOOL_GET_FIXES,
            description="Get remediation recommendations for a vulnerability type. "
            "Includes fix descriptions, code examples, effectiveness, and complexity.",
            parameters={
                "type": "object",
                "properties": {
                    "category_id": {
                        "type": "string",
                        "description": "The category ID",
                    },
                    "subcategory_id": {
                        "type": "string",
                        "description": "The subcategory ID (optional)",
                    },
                },
                "required": ["category_id"],
            },
        )

    def _define_search_by_operation(self) -> LLMNavigationTool:
        """Define the search_by_operation tool."""
        return LLMNavigationTool(
            name=TOOL_SEARCH_BY_OPERATION,
            description="Search for vulnerability categories relevant to a semantic operation. "
            "Operations like TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE, etc.",
            parameters={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "The semantic operation (e.g., 'TRANSFERS_VALUE_OUT')",
                    },
                    "include_secondary": {
                        "type": "boolean",
                        "description": "Include secondary category matches (default: false)",
                    },
                },
                "required": ["operation"],
            },
        )

    def _define_search_by_signature(self) -> LLMNavigationTool:
        """Define the search_by_signature tool."""
        return LLMNavigationTool(
            name=TOOL_SEARCH_BY_SIGNATURE,
            description="Search for vulnerability categories matching a behavioral signature. "
            "Signatures like 'R:bal->X:out->W:bal' represent operation sequences.",
            parameters={
                "type": "object",
                "properties": {
                    "signature": {
                        "type": "string",
                        "description": "The behavioral signature (e.g., 'R:bal->X:out->W:bal')",
                    },
                },
                "required": ["signature"],
            },
        )

    def get_tool_definitions(
        self,
        format: str = "openai",
    ) -> List[Dict[str, Any]]:
        """Return tool definitions for function calling.

        Args:
            format: Output format - 'openai' or 'anthropic'.

        Returns:
            List of tool definitions in the specified format.
        """
        tools = []
        for tool in self._tools.values():
            if format == "anthropic":
                tools.append(tool.to_anthropic_format())
            else:
                tools.append(tool.to_openai_format())
        return tools

    def get_tool(self, tool_name: str) -> Optional[LLMNavigationTool]:
        """Get a specific tool definition by name.

        Args:
            tool_name: The tool name.

        Returns:
            LLMNavigationTool if found, None otherwise.
        """
        return self._tools.get(tool_name)

    # =========================================================================
    # TOOL EXECUTION
    # =========================================================================

    def execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> ToolExecutionResult:
        """Execute a navigation tool and return result.

        Args:
            tool_name: The tool name to execute.
            params: Parameters for the tool.

        Returns:
            ToolExecutionResult with success/failure and content.
        """
        # Validate tool name
        if tool_name not in self._tools:
            return ToolExecutionResult.error_result(
                f"Unknown tool: {tool_name}. Available tools: {', '.join(ALL_TOOLS)}"
            )

        # Record action in state
        self.state.record_action(tool_name, params)

        # Dispatch to appropriate handler
        handlers = {
            TOOL_LIST_CATEGORIES: self._exec_list_categories,
            TOOL_GET_CATEGORY_INFO: self._exec_get_category_info,
            TOOL_GET_SUBCATEGORY_INFO: self._exec_get_subcategory_info,
            TOOL_GET_DETECTION_GUIDE: self._exec_get_detection_guide,
            TOOL_GET_PATTERNS: self._exec_get_patterns,
            TOOL_GET_EXPLOITS: self._exec_get_exploits,
            TOOL_GET_FIXES: self._exec_get_fixes,
            TOOL_SEARCH_BY_OPERATION: self._exec_search_by_operation,
            TOOL_SEARCH_BY_SIGNATURE: self._exec_search_by_signature,
        }

        handler = handlers.get(tool_name)
        if handler is None:
            return ToolExecutionResult.error_result(f"No handler for tool: {tool_name}")

        try:
            return handler(params)
        except Exception as e:
            return ToolExecutionResult.error_result(f"Tool execution error: {str(e)}")

    def _exec_list_categories(
        self,
        params: Dict[str, Any],
    ) -> ToolExecutionResult:
        """Execute list_categories tool."""
        try:
            category_ids = self.navigator.list_categories()
        except (ValueError, FileNotFoundError):
            return ToolExecutionResult.error_result("Failed to load category list")

        lines = ["# Vulnerability Categories", ""]

        for cat_id in category_ids:
            try:
                category = self.navigator.get_category(cat_id)
                lines.append(f"## {category.name} (`{cat_id}`)")
                lines.append("")
                desc = category.description[:150] + "..." if len(category.description) > 150 else category.description
                lines.append(desc)
                lines.append("")
                lines.append(f"**Severity:** {', '.join(category.severity_range)}")
                lines.append(f"**Subcategories:** {len(category.subcategories)}")
                lines.append("")
            except (ValueError, FileNotFoundError):
                lines.append(f"## `{cat_id}` (details unavailable)")
                lines.append("")

        return ToolExecutionResult.success_result(
            content="\n".join(lines),
            metadata={"category_count": len(category_ids)},
        )

    def _exec_get_category_info(
        self,
        params: Dict[str, Any],
    ) -> ToolExecutionResult:
        """Execute get_category_info tool."""
        category_id = params.get("category_id", "")
        if not category_id:
            return ToolExecutionResult.error_result("Missing required parameter: category_id")

        try:
            category = self.navigator.get_category(category_id)
        except (ValueError, FileNotFoundError):
            return ToolExecutionResult.error_result(f"Category not found: {category_id}")

        # Update navigation state
        self.state.set_focus(category=category_id)

        # Build output
        lines = [
            f"# {category.name}",
            "",
            f"**ID:** `{category.id}`",
            f"**Severity Range:** {', '.join(category.severity_range)}",
            "",
            "## Description",
            "",
            category.description,
            "",
        ]

        # Subcategories
        if category.subcategories:
            lines.append("## Subcategories")
            lines.append("")
            for sub in category.subcategories:
                desc = f": {sub.description}" if sub.description else ""
                lines.append(f"- **{sub.name}** (`{sub.id}`){desc}")
            lines.append("")

        # Relevant properties
        if category.relevant_properties:
            lines.append("## Relevant Properties")
            lines.append("")
            for prop in category.relevant_properties:
                lines.append(f"- `{prop}`")
            lines.append("")

        # Semantic operations
        if category.semantic_operations:
            lines.append("## Semantic Operations")
            lines.append("")
            for op in category.semantic_operations:
                lines.append(f"- `{op}`")
            lines.append("")

        # Related CWEs
        if category.related_cwes:
            lines.append("## Related CWEs")
            lines.append("")
            lines.append(", ".join(category.related_cwes))
            lines.append("")

        return ToolExecutionResult.success_result(
            content="\n".join(lines),
            metadata={
                "category_id": category_id,
                "subcategory_count": len(category.subcategories),
            },
        )

    def _exec_get_subcategory_info(
        self,
        params: Dict[str, Any],
    ) -> ToolExecutionResult:
        """Execute get_subcategory_info tool."""
        category_id = params.get("category_id", "")
        subcategory_id = params.get("subcategory_id", "")

        if not category_id:
            return ToolExecutionResult.error_result("Missing required parameter: category_id")
        if not subcategory_id:
            return ToolExecutionResult.error_result("Missing required parameter: subcategory_id")

        try:
            subcategory = self.navigator.get_subcategory(category_id, subcategory_id)
        except (ValueError, FileNotFoundError):
            return ToolExecutionResult.error_result(
                f"Subcategory not found: {category_id}/{subcategory_id}"
            )

        # Update navigation state
        self.state.set_focus(category=category_id, subcategory=subcategory_id)

        # Build output
        lines = [
            f"# {subcategory.name}",
            "",
            f"**Category:** `{category_id}`",
            f"**ID:** `{subcategory.id}`",
            f"**Severity Range:** {', '.join(subcategory.severity_range)}",
            "",
            "## Description",
            "",
            subcategory.description,
            "",
        ]

        # Patterns
        if subcategory.patterns:
            lines.append("## Associated Patterns")
            lines.append("")
            for pattern in subcategory.patterns:
                lines.append(f"- `{pattern}`")
            lines.append("")

        # Relevant properties
        if subcategory.relevant_properties:
            lines.append("## Relevant Properties")
            lines.append("")
            for prop in subcategory.relevant_properties:
                lines.append(f"- `{prop}`")
            lines.append("")

        # Graph signals
        if subcategory.graph_signals:
            lines.append("## Graph Signals")
            lines.append("")
            lines.append("| Property | Expected | Critical |")
            lines.append("|----------|----------|----------|")
            for sig in subcategory.graph_signals:
                critical = "Yes" if sig.critical else "No"
                lines.append(f"| `{sig.property_name}` | {sig.expected} | {critical} |")
            lines.append("")

        # Behavioral signatures
        if subcategory.behavioral_signatures:
            lines.append("## Behavioral Signatures")
            lines.append("")
            for sig in subcategory.behavioral_signatures:
                lines.append(f"- `{sig}`")
            lines.append("")

        return ToolExecutionResult.success_result(
            content="\n".join(lines),
            metadata={
                "category_id": category_id,
                "subcategory_id": subcategory_id,
            },
        )

    def _exec_get_detection_guide(
        self,
        params: Dict[str, Any],
    ) -> ToolExecutionResult:
        """Execute get_detection_guide tool."""
        category_id = params.get("category_id", "")
        subcategory_id = params.get("subcategory_id")

        if not category_id:
            return ToolExecutionResult.error_result("Missing required parameter: category_id")

        try:
            content = self.navigator.get_context(
                category_id,
                subcategory_id,
                depth=KnowledgeDepth.DETECTION,
            )
        except (ValueError, FileNotFoundError) as e:
            return ToolExecutionResult.error_result(f"Failed to get detection guide: {str(e)}")

        # Update navigation state
        self.state.set_focus(category=category_id, subcategory=subcategory_id)
        self.state.depth = KnowledgeDepth.DETECTION

        return ToolExecutionResult.success_result(
            content=content,
            metadata={
                "category_id": category_id,
                "subcategory_id": subcategory_id,
                "depth": "detection",
            },
        )

    def _exec_get_patterns(
        self,
        params: Dict[str, Any],
    ) -> ToolExecutionResult:
        """Execute get_patterns tool."""
        category_id = params.get("category_id", "")
        subcategory_id = params.get("subcategory_id")

        if not category_id:
            return ToolExecutionResult.error_result("Missing required parameter: category_id")

        try:
            content = self.navigator.get_context(
                category_id,
                subcategory_id,
                depth=KnowledgeDepth.PATTERNS,
            )
        except (ValueError, FileNotFoundError) as e:
            return ToolExecutionResult.error_result(f"Failed to get patterns: {str(e)}")

        # Update navigation state
        self.state.set_focus(category=category_id, subcategory=subcategory_id)
        self.state.depth = KnowledgeDepth.PATTERNS

        return ToolExecutionResult.success_result(
            content=content,
            metadata={
                "category_id": category_id,
                "subcategory_id": subcategory_id,
                "depth": "patterns",
            },
        )

    def _exec_get_exploits(
        self,
        params: Dict[str, Any],
    ) -> ToolExecutionResult:
        """Execute get_exploits tool."""
        category_id = params.get("category_id", "")
        subcategory_id = params.get("subcategory_id")

        if not category_id:
            return ToolExecutionResult.error_result("Missing required parameter: category_id")

        try:
            content = self.navigator.get_context(
                category_id,
                subcategory_id,
                depth=KnowledgeDepth.EXPLOITS,
            )
        except (ValueError, FileNotFoundError) as e:
            return ToolExecutionResult.error_result(f"Failed to get exploits: {str(e)}")

        # Update navigation state
        self.state.set_focus(category=category_id, subcategory=subcategory_id)
        self.state.depth = KnowledgeDepth.EXPLOITS

        return ToolExecutionResult.success_result(
            content=content,
            metadata={
                "category_id": category_id,
                "subcategory_id": subcategory_id,
                "depth": "exploits",
            },
        )

    def _exec_get_fixes(
        self,
        params: Dict[str, Any],
    ) -> ToolExecutionResult:
        """Execute get_fixes tool."""
        category_id = params.get("category_id", "")
        subcategory_id = params.get("subcategory_id")

        if not category_id:
            return ToolExecutionResult.error_result("Missing required parameter: category_id")

        try:
            content = self.navigator.get_context(
                category_id,
                subcategory_id,
                depth=KnowledgeDepth.FIXES,
            )
        except (ValueError, FileNotFoundError) as e:
            return ToolExecutionResult.error_result(f"Failed to get fixes: {str(e)}")

        # Update navigation state
        self.state.set_focus(category=category_id, subcategory=subcategory_id)
        self.state.depth = KnowledgeDepth.FIXES

        return ToolExecutionResult.success_result(
            content=content,
            metadata={
                "category_id": category_id,
                "subcategory_id": subcategory_id,
                "depth": "fixes",
            },
        )

    def _exec_search_by_operation(
        self,
        params: Dict[str, Any],
    ) -> ToolExecutionResult:
        """Execute search_by_operation tool."""
        operation = params.get("operation", "")
        include_secondary = params.get("include_secondary", False)

        if not operation:
            return ToolExecutionResult.error_result("Missing required parameter: operation")

        # Track operation in state
        self.state.add_operation(operation)

        try:
            categories = self.navigator.search_by_operation(operation, include_secondary)
        except (ValueError, FileNotFoundError):
            categories = []

        if not categories:
            return ToolExecutionResult.success_result(
                content=f"No categories found for operation: `{operation}`",
                metadata={"operation": operation, "match_count": 0},
            )

        lines = [
            f"# Categories for Operation: `{operation}`",
            "",
            f"Found {len(categories)} matching categories:",
            "",
        ]

        for cat in categories:
            lines.append(f"## {cat.name} (`{cat.id}`)")
            lines.append("")
            desc = cat.description[:150] + "..." if len(cat.description) > 150 else cat.description
            lines.append(desc)
            lines.append("")
            lines.append(f"**Severity:** {', '.join(cat.severity_range)}")
            lines.append("")

        return ToolExecutionResult.success_result(
            content="\n".join(lines),
            metadata={
                "operation": operation,
                "match_count": len(categories),
                "category_ids": [c.id for c in categories],
            },
        )

    def _exec_search_by_signature(
        self,
        params: Dict[str, Any],
    ) -> ToolExecutionResult:
        """Execute search_by_signature tool."""
        signature = params.get("signature", "")

        if not signature:
            return ToolExecutionResult.error_result("Missing required parameter: signature")

        try:
            categories = self.navigator.search_by_signature(signature)
        except (ValueError, FileNotFoundError):
            categories = []

        if not categories:
            return ToolExecutionResult.success_result(
                content=f"No categories found for signature: `{signature}`",
                metadata={"signature": signature, "match_count": 0},
            )

        lines = [
            f"# Categories for Signature: `{signature}`",
            "",
            f"Found {len(categories)} matching categories:",
            "",
        ]

        for cat in categories:
            lines.append(f"## {cat.name} (`{cat.id}`)")
            lines.append("")
            desc = cat.description[:150] + "..." if len(cat.description) > 150 else cat.description
            lines.append(desc)
            lines.append("")

            # Show relevant subcategories
            lines.append("**Subcategories:**")
            for sub in cat.subcategories[:5]:
                lines.append(f"- `{sub.id}`: {sub.name}")
            if len(cat.subcategories) > 5:
                lines.append(f"- ... and {len(cat.subcategories) - 5} more")
            lines.append("")

        return ToolExecutionResult.success_result(
            content="\n".join(lines),
            metadata={
                "signature": signature,
                "match_count": len(categories),
                "category_ids": [c.id for c in categories],
            },
        )

    # =========================================================================
    # NAVIGATION CONTEXT
    # =========================================================================

    def get_navigation_context(
        self,
        category: Optional[str] = None,
        operations: Optional[List[str]] = None,
        finding: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Get navigation context based on current state.

        Builds a context string based on the provided parameters or
        the current navigation state.

        Args:
            category: Category ID to focus on.
            operations: List of semantic operations to search for.
            finding: Finding dictionary to build context for.

        Returns:
            Formatted context string for LLM consumption.
        """
        lines = []

        # If finding provided, use builder for optimized context
        if finding:
            ctx = self.builder.build_for_finding(finding)
            return ctx.content

        # If operations provided, search for relevant categories
        if operations:
            lines.append("# Relevant Knowledge for Detected Operations")
            lines.append("")

            all_categories = set()
            for op in operations:
                try:
                    cats = self.navigator.search_by_operation(op, include_secondary=False)
                    for cat in cats:
                        all_categories.add(cat.id)
                except (ValueError, FileNotFoundError):
                    pass

            if all_categories:
                lines.append(f"**Operations:** {', '.join(f'`{op}`' for op in operations)}")
                lines.append(f"**Relevant Categories:** {', '.join(f'`{c}`' for c in all_categories)}")
                lines.append("")

                for cat_id in list(all_categories)[:3]:
                    try:
                        content = self.navigator.get_context(cat_id, depth=KnowledgeDepth.OVERVIEW)
                        lines.append("---")
                        lines.append("")
                        lines.append(content)
                        lines.append("")
                    except (ValueError, FileNotFoundError):
                        pass

            return "\n".join(lines)

        # If category provided, get category context
        if category:
            try:
                content = self.navigator.get_context(category, depth=KnowledgeDepth.DETECTION)
                return content
            except (ValueError, FileNotFoundError):
                return f"Category not found: {category}"

        # Otherwise, return general navigation context
        return self.navigator.get_navigation_context()

    def build_evidence_request(self, finding: Dict[str, Any]) -> str:
        """Generate a request for additional evidence context.

        Given a finding, generates a request string that can be used
        to retrieve supporting evidence from VulnDocs.

        Args:
            finding: Dictionary containing finding information.

        Returns:
            Evidence request string.
        """
        lines = [
            "# Evidence Request",
            "",
        ]

        pattern_id = finding.get("pattern_id") or finding.get("pattern", "")
        operations = finding.get("operations", [])
        signature = finding.get("signature") or finding.get("behavioral_signature", "")
        severity = finding.get("severity", "medium")

        lines.append("## Finding Summary")
        lines.append("")

        if pattern_id:
            lines.append(f"**Pattern:** `{pattern_id}`")
        if severity:
            lines.append(f"**Severity:** {severity}")
        if finding.get("function_name"):
            lines.append(f"**Function:** `{finding['function_name']}`")
        if finding.get("contract_name"):
            lines.append(f"**Contract:** `{finding['contract_name']}`")
        lines.append("")

        # Evidence gathering recommendations
        lines.append("## Recommended Evidence Retrieval")
        lines.append("")

        if signature:
            lines.append(f"1. Search by signature: `search_by_signature(\"{signature}\")`")

        if operations:
            for op in operations[:3]:
                lines.append(f"2. Search by operation: `search_by_operation(\"{op}\")`")

        # Determine likely categories
        categories = set()
        if operations:
            for op in operations:
                try:
                    cats = self.navigator.search_by_operation(op)
                    for cat in cats:
                        categories.add(cat.id)
                except (ValueError, FileNotFoundError):
                    pass

        if categories:
            lines.append("")
            lines.append("## Suggested Deep Dives")
            lines.append("")
            for cat_id in list(categories)[:3]:
                lines.append(f"- `get_detection_guide(\"{cat_id}\")`")
                lines.append(f"- `get_exploits(\"{cat_id}\")`")

        return "\n".join(lines)

    # =========================================================================
    # STATE MANAGEMENT
    # =========================================================================

    def get_state(self) -> NavigationState:
        """Get the current navigation state.

        Returns:
            Current NavigationState.
        """
        return self.state

    def set_state(self, state: NavigationState) -> None:
        """Set the navigation state.

        Args:
            state: NavigationState to set.
        """
        self.state = state

    def reset_state(self) -> None:
        """Reset the navigation state to initial values."""
        self.state.clear()

    def export_state(self) -> Dict[str, Any]:
        """Export the navigation state as a dictionary.

        Returns:
            Dictionary representation of the state.
        """
        return self.state.to_dict()

    def import_state(self, data: Dict[str, Any]) -> None:
        """Import navigation state from a dictionary.

        Args:
            data: Dictionary containing state data.
        """
        self.state = NavigationState.from_dict(data)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def create_llm_navigator(
    base_path: Optional[str] = None,
) -> LLMNavigator:
    """Factory function to create an LLMNavigator with dependencies.

    Args:
        base_path: Optional path to knowledge base directory.

    Returns:
        Configured LLMNavigator instance.
    """
    from alphaswarm_sol.knowledge.vulndocs.navigator import KnowledgeNavigator
    from alphaswarm_sol.knowledge.vulndocs.cache import PromptCache
    from alphaswarm_sol.knowledge.vulndocs.builder import ContextBuilder
    from pathlib import Path

    if base_path:
        navigator = KnowledgeNavigator(Path(base_path))
    else:
        navigator = KnowledgeNavigator()

    cache = PromptCache(navigator)
    builder = ContextBuilder(navigator, cache)

    return LLMNavigator(navigator, builder)


def get_tool_names() -> List[str]:
    """Get list of all available tool names.

    Returns:
        List of tool name strings.
    """
    return ALL_TOOLS.copy()
