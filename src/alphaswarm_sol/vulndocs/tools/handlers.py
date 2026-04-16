"""Tool handlers for VulnDocs LLM integration.

Executes tools and returns structured responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from alphaswarm_sol.vulndocs.knowledge_doc import VulnKnowledgeDoc
from alphaswarm_sol.vulndocs.storage.knowledge_store import KnowledgeStore, StorageConfig
from alphaswarm_sol.vulndocs.storage.index_builder import IndexBuilder
from alphaswarm_sol.vulndocs.storage.retrieval import (
    KnowledgeRetriever,
    RetrievalConfig,
    RetrievalDepth,
    RetrievalQuery,
)
from alphaswarm_sol.vulndocs.tools.definitions import AVAILABLE_TOOLS, get_tool_schema
from alphaswarm_sol.vulndocs.tools.formatters import (
    OutputFormat,
    FormatterConfig,
    format_output,
    estimate_tokens,
)


class ToolError(Exception):
    """Error during tool execution."""

    def __init__(self, message: str, tool_name: str = "", details: str = ""):
        super().__init__(message)
        self.message = message
        self.tool_name = tool_name
        self.details = details


@dataclass
class ToolResponse:
    """Response from a tool execution."""

    success: bool
    tool_name: str
    content: str  # Formatted content
    raw_data: Any = None  # Unformatted data
    token_estimate: int = 0
    format_used: str = "toon"
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if not self.token_estimate and self.content:
            self.token_estimate = estimate_tokens(self.content)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "tool_name": self.tool_name,
            "content": self.content,
            "token_estimate": self.token_estimate,
            "format_used": self.format_used,
            "metadata": self.metadata,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class ToolHandler:
    """Handles tool execution for VulnDocs.

    Example:
        handler = ToolHandler()
        response = handler.execute(
            "get_vulnerability_knowledge",
            {"category": "reentrancy", "subcategory": "classic"}
        )
    """

    def __init__(
        self,
        store: Optional[KnowledgeStore] = None,
        retriever: Optional[KnowledgeRetriever] = None,
        default_format: OutputFormat = OutputFormat.TOON,
    ):
        """Initialize tool handler.

        Args:
            store: Knowledge store (creates default if not provided)
            retriever: Knowledge retriever (creates default if not provided)
            default_format: Default output format
        """
        self.store = store or KnowledgeStore()
        self.retriever = retriever or KnowledgeRetriever(self.store)
        self.default_format = default_format

    def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        output_format: Optional[OutputFormat] = None,
    ) -> ToolResponse:
        """Execute a tool with given parameters.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            output_format: Optional output format override

        Returns:
            ToolResponse with formatted content
        """
        if tool_name not in AVAILABLE_TOOLS:
            return ToolResponse(
                success=False,
                tool_name=tool_name,
                content="",
                error=f"Unknown tool: {tool_name}. Available tools: {list(AVAILABLE_TOOLS.keys())}",
            )

        format_to_use = output_format or self.default_format

        try:
            # Route to appropriate handler
            if tool_name == "get_vulnerability_knowledge":
                return self._handle_get_knowledge(parameters, format_to_use)
            elif tool_name == "search_vulnerability_knowledge":
                return self._handle_search(parameters, format_to_use)
            elif tool_name == "get_knowledge_for_finding":
                return self._handle_get_for_finding(parameters, format_to_use)
            elif tool_name == "list_vulnerability_categories":
                return self._handle_list_categories(parameters, format_to_use)
            elif tool_name == "get_pattern_knowledge":
                return self._handle_get_pattern_knowledge(parameters, format_to_use)
            elif tool_name == "get_navigation_context":
                return self._handle_get_navigation(parameters, format_to_use)
            else:
                return ToolResponse(
                    success=False,
                    tool_name=tool_name,
                    content="",
                    error=f"Handler not implemented for tool: {tool_name}",
                )
        except Exception as e:
            return ToolResponse(
                success=False,
                tool_name=tool_name,
                content="",
                error=f"Tool execution error: {str(e)}",
            )

    def _handle_get_knowledge(
        self,
        params: Dict[str, Any],
        format: OutputFormat,
    ) -> ToolResponse:
        """Handle get_vulnerability_knowledge tool."""
        category = params.get("category", "")
        subcategory = params.get("subcategory")
        depth_str = params.get("depth", "standard")
        max_tokens = params.get("max_tokens", 2000)

        if not category:
            return ToolResponse(
                success=False,
                tool_name="get_vulnerability_knowledge",
                content="",
                error="Missing required parameter: category",
            )

        # Map depth string to enum
        depth_map = {
            "minimal": RetrievalDepth.MINIMAL,
            "standard": RetrievalDepth.STANDARD,
            "full": RetrievalDepth.FULL,
            "compact": RetrievalDepth.COMPACT,
        }
        depth = depth_map.get(depth_str, RetrievalDepth.STANDARD)

        # Execute retrieval
        result = self.retriever.get_by_category(
            category=category,
            subcategory=subcategory,
            depth=depth,
            max_results=10,
        )

        if not result.documents:
            return ToolResponse(
                success=True,
                tool_name="get_vulnerability_knowledge",
                content=f"No knowledge found for category: {category}" + (
                    f"/{subcategory}" if subcategory else ""
                ),
                format_used=format.value,
                metadata={
                    "category": category,
                    "subcategory": subcategory,
                    "result_count": 0,
                },
            )

        # Format output
        config = FormatterConfig(max_tokens=max_tokens)
        content = format_output(result.documents, format, config)

        return ToolResponse(
            success=True,
            tool_name="get_vulnerability_knowledge",
            content=content,
            raw_data=result.documents,
            format_used=format.value,
            metadata={
                "category": category,
                "subcategory": subcategory,
                "result_count": len(result.documents),
                "truncated": result.truncated,
            },
        )

    def _handle_search(
        self,
        params: Dict[str, Any],
        format: OutputFormat,
    ) -> ToolResponse:
        """Handle search_vulnerability_knowledge tool."""
        query = params.get("query", "")
        max_results = params.get("max_results", 5)
        severity_filter = params.get("severity_filter")
        depth_str = params.get("depth", "minimal")

        if not query:
            return ToolResponse(
                success=False,
                tool_name="search_vulnerability_knowledge",
                content="",
                error="Missing required parameter: query",
            )

        depth_map = {
            "minimal": RetrievalDepth.MINIMAL,
            "standard": RetrievalDepth.STANDARD,
            "full": RetrievalDepth.FULL,
            "compact": RetrievalDepth.COMPACT,
        }
        depth = depth_map.get(depth_str, RetrievalDepth.MINIMAL)

        # Execute search
        result = self.retriever.search(
            keywords=query,
            max_results=max_results,
            depth=depth,
            severity_filter=severity_filter,
        )

        if not result.documents:
            return ToolResponse(
                success=True,
                tool_name="search_vulnerability_knowledge",
                content=f"No results found for query: {query}",
                format_used=format.value,
                metadata={"query": query, "result_count": 0},
            )

        # Format output
        content = format_output(result.documents, format)

        return ToolResponse(
            success=True,
            tool_name="search_vulnerability_knowledge",
            content=content,
            raw_data=result.documents,
            format_used=format.value,
            metadata={
                "query": query,
                "result_count": len(result.documents),
                "truncated": result.truncated,
            },
        )

    def _handle_get_for_finding(
        self,
        params: Dict[str, Any],
        format: OutputFormat,
    ) -> ToolResponse:
        """Handle get_knowledge_for_finding tool."""
        finding = params.get("finding", {})
        include_examples = params.get("include_examples", True)
        max_tokens = params.get("max_tokens", 1500)

        if not finding:
            return ToolResponse(
                success=False,
                tool_name="get_knowledge_for_finding",
                content="",
                error="Missing required parameter: finding",
            )

        # Get context for finding
        config = FormatterConfig(
            max_tokens=max_tokens,
            include_examples=include_examples,
        )

        context = self.retriever.get_context_for_finding(
            finding=finding,
            depth=RetrievalDepth.STANDARD,
            max_tokens=max_tokens,
        )

        return ToolResponse(
            success=True,
            tool_name="get_knowledge_for_finding",
            content=context,
            format_used=format.value,
            metadata={
                "finding_category": finding.get("category", "unknown"),
                "include_examples": include_examples,
            },
        )

    def _handle_list_categories(
        self,
        params: Dict[str, Any],
        format: OutputFormat,
    ) -> ToolResponse:
        """Handle list_vulnerability_categories tool."""
        include_stats = params.get("include_stats", True)
        category_filter = params.get("category_filter")

        index = self.retriever.index

        if category_filter:
            # Show subcategories for specific category
            subcategories = self.retriever.list_subcategories(category_filter)
            if not subcategories:
                return ToolResponse(
                    success=True,
                    tool_name="list_vulnerability_categories",
                    content=f"No subcategories found for: {category_filter}",
                    format_used=format.value,
                )

            lines = [f"# {category_filter.title()} Subcategories", ""]
            for subcat in subcategories:
                doc_ids = index.get_by_subcategory(category_filter, subcat)
                if include_stats:
                    lines.append(f"- {subcat} ({len(doc_ids)} docs)")
                else:
                    lines.append(f"- {subcat}")

            return ToolResponse(
                success=True,
                tool_name="list_vulnerability_categories",
                content="\n".join(lines),
                format_used="markdown",
                metadata={
                    "category": category_filter,
                    "subcategory_count": len(subcategories),
                },
            )

        # Show all categories
        categories = self.retriever.list_categories()

        if not categories:
            return ToolResponse(
                success=True,
                tool_name="list_vulnerability_categories",
                content="No categories found in knowledge base.",
                format_used=format.value,
            )

        lines = ["# Vulnerability Categories", ""]
        for cat in sorted(categories):
            cat_summary = index.get_category(cat)
            if cat_summary and include_stats:
                lines.append(
                    f"## {cat_summary.display_name} ({cat})"
                )
                lines.append(f"- {cat_summary.document_count} documents")
                lines.append(f"- Subcategories: {', '.join(cat_summary.subcategories[:5])}")
                if len(cat_summary.subcategories) > 5:
                    lines.append(f"  ... and {len(cat_summary.subcategories) - 5} more")
                lines.append("")
            else:
                lines.append(f"- {cat}")

        return ToolResponse(
            success=True,
            tool_name="list_vulnerability_categories",
            content="\n".join(lines),
            format_used="markdown",
            metadata={
                "category_count": len(categories),
                "total_documents": index.total_documents,
            },
        )

    def _handle_get_pattern_knowledge(
        self,
        params: Dict[str, Any],
        format: OutputFormat,
    ) -> ToolResponse:
        """Handle get_pattern_knowledge tool."""
        pattern_ids = params.get("pattern_ids", [])
        include_detection_guide = params.get("include_detection_guide", True)

        if not pattern_ids:
            return ToolResponse(
                success=False,
                tool_name="get_pattern_knowledge",
                content="",
                error="Missing required parameter: pattern_ids",
            )

        # Get documents linked to patterns
        result = self.retriever.get_by_pattern(
            pattern_ids=pattern_ids,
            depth=RetrievalDepth.STANDARD if include_detection_guide else RetrievalDepth.MINIMAL,
        )

        if not result.documents:
            return ToolResponse(
                success=True,
                tool_name="get_pattern_knowledge",
                content=f"No knowledge found for patterns: {', '.join(pattern_ids)}",
                format_used=format.value,
                metadata={"pattern_ids": pattern_ids, "result_count": 0},
            )

        content = format_output(result.documents, format)

        return ToolResponse(
            success=True,
            tool_name="get_pattern_knowledge",
            content=content,
            raw_data=result.documents,
            format_used=format.value,
            metadata={
                "pattern_ids": pattern_ids,
                "result_count": len(result.documents),
            },
        )

    def _handle_get_navigation(
        self,
        params: Dict[str, Any],
        format: OutputFormat,
    ) -> ToolResponse:
        """Handle get_navigation_context tool."""
        max_tokens = params.get("max_tokens", 1000)

        context = self.retriever.get_navigation_context(max_tokens=max_tokens)

        return ToolResponse(
            success=True,
            tool_name="get_navigation_context",
            content=context,
            format_used="markdown",
            metadata={"max_tokens": max_tokens},
        )

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(AVAILABLE_TOOLS.keys())

    def get_tool_help(self, tool_name: str) -> Optional[str]:
        """Get help text for a tool."""
        tool = AVAILABLE_TOOLS.get(tool_name)
        if not tool:
            return None

        lines = [
            f"# {tool_name}",
            "",
            tool.description,
            "",
            "## Parameters",
            "",
        ]

        for param in tool.parameters:
            req = "(required)" if param.required else "(optional)"
            lines.append(f"- **{param.name}** [{param.type}] {req}")
            lines.append(f"  {param.description}")
            if param.enum:
                lines.append(f"  Options: {', '.join(param.enum)}")
            if param.default is not None:
                lines.append(f"  Default: {param.default}")

        if tool.examples:
            lines.extend(["", "## Examples", ""])
            for ex in tool.examples:
                lines.append(f"- {ex.get('description', '')}")
                lines.append(f"  Input: {ex.get('input', {})}")

        return "\n".join(lines)


# =============================================================================
# Convenience Functions
# =============================================================================

_default_handler: Optional[ToolHandler] = None


def get_handler() -> ToolHandler:
    """Get or create default tool handler."""
    global _default_handler
    if _default_handler is None:
        _default_handler = ToolHandler()
    return _default_handler


def set_handler(handler: ToolHandler) -> None:
    """Set the default tool handler."""
    global _default_handler
    _default_handler = handler


def execute_tool(
    tool_name: str,
    parameters: Dict[str, Any],
    output_format: Optional[OutputFormat] = None,
) -> ToolResponse:
    """Execute a tool using the default handler.

    Args:
        tool_name: Name of the tool
        parameters: Tool parameters
        output_format: Optional output format override

    Returns:
        ToolResponse
    """
    handler = get_handler()
    return handler.execute(tool_name, parameters, output_format)


def get_tool_list() -> List[str]:
    """Get list of available tools."""
    return list(AVAILABLE_TOOLS.keys())


def get_help(tool_name: str) -> Optional[str]:
    """Get help for a tool."""
    handler = get_handler()
    return handler.get_tool_help(tool_name)
