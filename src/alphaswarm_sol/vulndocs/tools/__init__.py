"""LLM Tool Interface for VulnDocs knowledge retrieval.

Task 18.19: Tool definitions and handlers for LLM agent integration.

Key Components:
- Tool Definitions: JSON Schema definitions for LLM tool use
- Tool Handlers: Execute tools and return structured responses
- Output Formatters: TOON, JSON, and Markdown output formats

Design Principles:
1. Token Efficiency: Default to compact TOON format (30-50% reduction)
2. Structured Output: JSON schemas for all responses
3. Discoverability: Self-documenting tools with examples
4. Composability: Tools work together naturally for complex queries

Usage:
    from alphaswarm_sol.vulndocs.tools import (
        VulnDocsTools,
        get_tool_definitions,
        execute_tool,
    )

    # Get tool definitions for LLM
    tools = get_tool_definitions()

    # Execute a tool
    result = execute_tool(
        "get_vulnerability_knowledge",
        {"category": "reentrancy", "subcategory": "classic"}
    )
"""

from alphaswarm_sol.vulndocs.tools.definitions import (
    ToolDefinition,
    get_tool_definitions,
    get_tool_schema,
    AVAILABLE_TOOLS,
)
from alphaswarm_sol.vulndocs.tools.handlers import (
    ToolHandler,
    ToolResponse,
    ToolError,
    execute_tool,
)
from alphaswarm_sol.vulndocs.tools.formatters import (
    OutputFormat,
    OutputFormatter,
    TOONFormatter,
    format_output,
)

__all__ = [
    # Definitions
    "ToolDefinition",
    "get_tool_definitions",
    "get_tool_schema",
    "AVAILABLE_TOOLS",
    # Handlers
    "ToolHandler",
    "ToolResponse",
    "ToolError",
    "execute_tool",
    # Formatters
    "OutputFormat",
    "OutputFormatter",
    "TOONFormatter",
    "format_output",
]
