"""Tool definitions for VulnDocs LLM integration.

JSON Schema definitions for tools that LLM agents can invoke.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


@dataclass
class ToolParameter:
    """A parameter for a tool."""

    name: str
    type: str  # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Optional[Any] = None
    items: Optional[Dict[str, Any]] = None  # For array types

    def to_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format."""
        schema: Dict[str, Any] = {
            "type": self.type,
            "description": self.description,
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        if self.items:
            schema["items"] = self.items
        return schema


@dataclass
class ToolDefinition:
    """Definition of a tool for LLM invocation."""

    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: str = ""
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format for LLM tool use."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_schema()
            if param.required:
                required.append(param.name)

        schema = {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

        return schema

    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convert to Anthropic tool format."""
        return self.to_schema()

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function format."""
        schema = self.to_schema()
        return {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["input_schema"],
            },
        }


# =============================================================================
# Tool Definitions
# =============================================================================

GET_VULNERABILITY_KNOWLEDGE = ToolDefinition(
    name="get_vulnerability_knowledge",
    description="""Retrieve vulnerability knowledge documentation for a specific category and subcategory.

Returns structured knowledge about vulnerability classes including:
- Detection signals (what graph properties indicate this vulnerability)
- Attack vectors and exploitation steps
- Mitigation strategies and safe patterns
- Real-world exploit examples

Use this tool when you need detailed knowledge about a specific type of vulnerability
to understand how to detect, exploit, or fix it.""",
    parameters=[
        ToolParameter(
            name="category",
            type="string",
            description="Vulnerability category (e.g., 'reentrancy', 'access-control', 'oracle')",
            required=True,
        ),
        ToolParameter(
            name="subcategory",
            type="string",
            description="Specific subcategory (e.g., 'classic', 'cross-function', 'read-only')",
            required=False,
        ),
        ToolParameter(
            name="depth",
            type="string",
            description="How much detail to include",
            required=False,
            enum=["minimal", "standard", "full", "compact"],
            default="standard",
        ),
        ToolParameter(
            name="max_tokens",
            type="integer",
            description="Maximum tokens in response (for context budget management)",
            required=False,
            default=2000,
        ),
    ],
    returns="Structured vulnerability knowledge with detection, exploitation, and mitigation sections",
    examples=[
        {
            "description": "Get classic reentrancy knowledge",
            "input": {"category": "reentrancy", "subcategory": "classic"},
            "output_summary": "Returns detection signals, CEI pattern fix, The DAO exploit reference",
        },
        {
            "description": "Get all access control knowledge",
            "input": {"category": "access-control", "depth": "compact"},
            "output_summary": "Returns compact summaries of all access control subcategories",
        },
    ],
)

SEARCH_VULNERABILITY_KNOWLEDGE = ToolDefinition(
    name="search_vulnerability_knowledge",
    description="""Search vulnerability knowledge by keywords, patterns, or properties.

Use this when you're not sure which category to look in, or when searching
for knowledge related to specific:
- Graph signals (e.g., 'state_write_after_external_call')
- Attack techniques (e.g., 'flash loan', 'sandwich')
- Code patterns (e.g., 'callback', 'delegatecall')

Returns matching knowledge documents ranked by relevance.""",
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="Search query - keywords, signals, or patterns to find",
            required=True,
        ),
        ToolParameter(
            name="max_results",
            type="integer",
            description="Maximum number of results to return",
            required=False,
            default=5,
        ),
        ToolParameter(
            name="severity_filter",
            type="string",
            description="Filter by severity level",
            required=False,
            enum=["critical", "high", "medium", "low", "info"],
        ),
        ToolParameter(
            name="depth",
            type="string",
            description="How much detail per result",
            required=False,
            enum=["minimal", "standard", "full", "compact"],
            default="minimal",
        ),
    ],
    returns="List of matching vulnerability knowledge documents with relevance scores",
    examples=[
        {
            "description": "Search for flash loan vulnerabilities",
            "input": {"query": "flash loan manipulation"},
            "output_summary": "Returns oracle manipulation, price slippage, and flash loan attack docs",
        },
        {
            "description": "Search for critical vulnerabilities only",
            "input": {"query": "fund drain", "severity_filter": "critical"},
            "output_summary": "Returns critical severity vulnerabilities that could drain funds",
        },
    ],
)

GET_KNOWLEDGE_FOR_FINDING = ToolDefinition(
    name="get_knowledge_for_finding",
    description="""Get relevant vulnerability knowledge context for a specific VKG finding.

Use this when you have a finding from VKG analysis and need background knowledge
to understand, verify, or explain it. The tool automatically matches the finding's
signals and category to relevant knowledge.

Returns:
- Knowledge directly related to the finding's vulnerability type
- Detection guidance specific to the observed signals
- Mitigation recommendations tailored to the finding""",
    parameters=[
        ToolParameter(
            name="finding",
            type="object",
            description="The VKG finding object containing category, signals, location, etc.",
            required=True,
        ),
        ToolParameter(
            name="include_examples",
            type="boolean",
            description="Whether to include code examples and real exploits",
            required=False,
            default=True,
        ),
        ToolParameter(
            name="max_tokens",
            type="integer",
            description="Maximum tokens for the response",
            required=False,
            default=1500,
        ),
    ],
    returns="Contextual knowledge specific to the finding for investigation",
    examples=[
        {
            "description": "Get context for a reentrancy finding",
            "input": {
                "finding": {
                    "category": "reentrancy",
                    "signals": ["state_write_after_external_call"],
                    "location": "Vault.sol:withdraw:142",
                }
            },
            "output_summary": "Returns reentrancy knowledge focused on state-after-call pattern",
        },
    ],
)

LIST_VULNERABILITY_CATEGORIES = ToolDefinition(
    name="list_vulnerability_categories",
    description="""List all available vulnerability categories and their subcategories.

Use this to discover what knowledge is available and navigate to specific areas.
Returns a hierarchical tree of categories with document counts and coverage info.

Useful for:
- Understanding the scope of vulnerability knowledge
- Finding the right category for a specific issue
- Checking coverage gaps""",
    parameters=[
        ToolParameter(
            name="include_stats",
            type="boolean",
            description="Include document counts and coverage statistics",
            required=False,
            default=True,
        ),
        ToolParameter(
            name="category_filter",
            type="string",
            description="Filter to show only subcategories of a specific category",
            required=False,
        ),
    ],
    returns="Hierarchical list of categories with subcategories and statistics",
    examples=[
        {
            "description": "List all categories",
            "input": {"include_stats": True},
            "output_summary": "Returns tree of 15 categories with 80+ subcategories",
        },
        {
            "description": "List only reentrancy subcategories",
            "input": {"category_filter": "reentrancy"},
            "output_summary": "Returns classic, cross-function, read-only, etc. subcategories",
        },
    ],
)

GET_PATTERN_KNOWLEDGE = ToolDefinition(
    name="get_pattern_knowledge",
    description="""Get vulnerability knowledge linked to specific VKG patterns.

Each VKG pattern (e.g., 'reentrancy-001', 'access-control-weak') may have
associated knowledge documentation. Use this to understand:
- What the pattern detects
- Why it's a vulnerability
- How to verify findings from this pattern
- How to fix issues caught by this pattern

Pattern linkage types:
- exact_match: Pattern directly detects this vulnerability
- partial_match: Pattern covers subset of variants
- requires_llm: Detection requires Tier B LLM reasoning
- composite: Multiple patterns needed together""",
    parameters=[
        ToolParameter(
            name="pattern_ids",
            type="array",
            description="List of pattern IDs to get knowledge for",
            required=True,
            items={"type": "string"},
        ),
        ToolParameter(
            name="include_detection_guide",
            type="boolean",
            description="Include step-by-step detection guidance",
            required=False,
            default=True,
        ),
    ],
    returns="Knowledge documents linked to the specified patterns",
    examples=[
        {
            "description": "Get knowledge for reentrancy pattern",
            "input": {"pattern_ids": ["reentrancy-001"]},
            "output_summary": "Returns classic reentrancy knowledge with CEI pattern fix",
        },
    ],
)

GET_NAVIGATION_CONTEXT = ToolDefinition(
    name="get_navigation_context",
    description="""Get a navigation summary of the vulnerability knowledge base.

Returns a high-level overview suitable for LLM context, showing:
- Available categories and their sizes
- How to navigate to specific knowledge
- Search capabilities

Use this at the start of an investigation to understand what knowledge
is available and how to access it.""",
    parameters=[
        ToolParameter(
            name="max_tokens",
            type="integer",
            description="Maximum tokens for the navigation context",
            required=False,
            default=1000,
        ),
    ],
    returns="Navigation guide for the vulnerability knowledge base",
    examples=[
        {
            "description": "Get navigation context",
            "input": {"max_tokens": 500},
            "output_summary": "Returns compact overview of categories and how to query them",
        },
    ],
)


# =============================================================================
# Tool Registry
# =============================================================================

AVAILABLE_TOOLS: Dict[str, ToolDefinition] = {
    "get_vulnerability_knowledge": GET_VULNERABILITY_KNOWLEDGE,
    "search_vulnerability_knowledge": SEARCH_VULNERABILITY_KNOWLEDGE,
    "get_knowledge_for_finding": GET_KNOWLEDGE_FOR_FINDING,
    "list_vulnerability_categories": LIST_VULNERABILITY_CATEGORIES,
    "get_pattern_knowledge": GET_PATTERN_KNOWLEDGE,
    "get_navigation_context": GET_NAVIGATION_CONTEXT,
}


def get_tool_definitions(
    format: str = "anthropic",
) -> List[Dict[str, Any]]:
    """Get all tool definitions in specified format.

    Args:
        format: Output format - "anthropic", "openai", or "schema"

    Returns:
        List of tool definitions
    """
    definitions = []
    for tool in AVAILABLE_TOOLS.values():
        if format == "anthropic":
            definitions.append(tool.to_anthropic_format())
        elif format == "openai":
            definitions.append(tool.to_openai_format())
        else:
            definitions.append(tool.to_schema())
    return definitions


def get_tool_schema(tool_name: str) -> Optional[Dict[str, Any]]:
    """Get schema for a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Tool schema or None if not found
    """
    tool = AVAILABLE_TOOLS.get(tool_name)
    if tool:
        return tool.to_schema()
    return None


def get_tool_names() -> List[str]:
    """Get list of all available tool names."""
    return list(AVAILABLE_TOOLS.keys())


def get_tool_description(tool_name: str) -> Optional[str]:
    """Get description for a specific tool."""
    tool = AVAILABLE_TOOLS.get(tool_name)
    if tool:
        return tool.description
    return None
