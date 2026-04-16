"""LLM Labeler microagent for semantic labeling.

Uses Claude with tool calling to apply semantic labels to functions.
The labeler prepares sliced subgraph context and uses tool calling for
structured output, storing labels in a LabelOverlay.

Key Components:
- LabelingConfig: Configuration for labeling (token budget, batch size)
- LabelingResult: Result of labeling a single function
- BatchLabelingResult: Result of batch labeling operations
- LLMLabeler: Main labeler class with label_function() and label_functions()

Usage:
    from alphaswarm_sol.labels.labeler import LLMLabeler, LabelingConfig
    from alphaswarm_sol.llm.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider(config)
    labeler = LLMLabeler(provider)
    result = await labeler.label_functions(graph, function_ids)
    overlay = labeler.get_overlay()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from alphaswarm_sol.labels.schema import FunctionLabel, LabelConfidence, LabelSource, LabelSet
from alphaswarm_sol.labels.overlay import LabelOverlay
from alphaswarm_sol.labels.tools import build_label_tools, LABELING_TOOL_CHOICE, parse_label_from_tool_call
from alphaswarm_sol.labels.prompts import LABELING_SYSTEM_PROMPT, build_labeling_prompt, format_function_context
from alphaswarm_sol.labels.taxonomy import is_valid_label
from alphaswarm_sol.kg.slicer import GraphSlicer, SlicedGraph

if TYPE_CHECKING:
    from alphaswarm_sol.kg.schema import KnowledgeGraph, Node
    from alphaswarm_sol.llm.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class LabelingConfig:
    """Configuration for labeling operations.

    Attributes:
        max_tokens_per_call: Maximum token budget per LLM call (~6k default)
        max_functions_per_batch: Functions per LLM call for efficiency
        min_confidence_threshold: Minimum confidence to accept labels
        include_negation_labels: Whether to apply negation labels
        temperature: LLM sampling temperature (low for consistency)
    """

    max_tokens_per_call: int = 6000  # Token budget
    max_functions_per_batch: int = 5  # Functions per LLM call
    min_confidence_threshold: LabelConfidence = LabelConfidence.LOW
    include_negation_labels: bool = True
    temperature: float = 0.1


@dataclass
class LabelingResult:
    """Result of labeling a single function.

    Attributes:
        function_id: ID of the labeled function
        labels_applied: List of labels applied to the function
        tokens_used: Tokens used for this labeling operation
        success: Whether labeling succeeded
        error: Error message if labeling failed
    """

    function_id: str
    labels_applied: List[FunctionLabel] = field(default_factory=list)
    tokens_used: int = 0
    success: bool = True
    error: Optional[str] = None


@dataclass
class BatchLabelingResult:
    """Result of batch labeling multiple functions.

    Attributes:
        results: Individual results per function
        total_tokens: Total tokens used across all batches
        total_cost_usd: Total cost in USD
        functions_labeled: Number of functions successfully labeled
        labels_applied: Total number of labels applied
    """

    results: List[LabelingResult] = field(default_factory=list)
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    functions_labeled: int = 0
    labels_applied: int = 0


class LLMLabeler:
    """LLM-based semantic labeler using tool calling.

    Uses Claude with tool calling to apply semantic labels to functions.
    Context is prepared from the knowledge graph with caller/callee information,
    and labels are stored in a LabelOverlay.

    The labeler enforces token budgets and supports batch processing to
    reduce API calls and costs.

    Usage:
        labeler = LLMLabeler(provider)
        result = await labeler.label_functions(graph, function_ids)
        overlay = labeler.get_overlay()

    Attributes:
        provider: LLM provider for API calls
        config: Labeling configuration
        overlay: Label storage overlay
        slicer: Graph slicer for context preparation
    """

    def __init__(
        self,
        provider: "LLMProvider",
        config: Optional[LabelingConfig] = None,
    ):
        """Initialize LLMLabeler.

        Args:
            provider: LLM provider (Anthropic, OpenAI, etc.)
            config: Optional labeling configuration
        """
        self.provider = provider
        self.config = config or LabelingConfig()
        self.overlay = LabelOverlay()
        self.slicer = GraphSlicer(include_core=True, strict_mode=False)
        self._tools = build_label_tools()
        self._total_tokens = 0
        self._total_cost = 0.0

    async def label_function(
        self,
        graph: "KnowledgeGraph",
        function_id: str,
        context_category: Optional[str] = None,
    ) -> LabelingResult:
        """Label a single function.

        Convenience method that delegates to label_functions() for a single
        function. Use label_functions() directly for better efficiency when
        labeling multiple functions.

        Args:
            graph: Knowledge graph containing the function
            function_id: ID of function to label
            context_category: Optional category to filter label scope

        Returns:
            LabelingResult with applied labels
        """
        batch_result = await self.label_functions(graph, [function_id], context_category)
        if batch_result.results:
            return batch_result.results[0]
        return LabelingResult(function_id, success=False, error="No results returned")

    async def label_functions(
        self,
        graph: "KnowledgeGraph",
        function_ids: List[str],
        context_category: Optional[str] = None,
    ) -> BatchLabelingResult:
        """Label multiple functions.

        Processes functions in batches to reduce API calls while staying
        within token budget. Labels are stored in the overlay automatically.

        Args:
            graph: Knowledge graph containing the functions
            function_ids: IDs of functions to label
            context_category: Optional category filter for scoped labeling

        Returns:
            BatchLabelingResult with all labeling results

        Example:
            result = await labeler.label_functions(graph, ["Vault.withdraw", "Vault.deposit"])
            print(f"Labeled {result.functions_labeled} functions with {result.labels_applied} labels")
        """
        batch_result = BatchLabelingResult()

        # Process in batches
        for i in range(0, len(function_ids), self.config.max_functions_per_batch):
            batch_ids = function_ids[i:i + self.config.max_functions_per_batch]
            results = await self._label_batch(graph, batch_ids, context_category)
            batch_result.results.extend(results)

        # Aggregate statistics
        batch_result.functions_labeled = sum(1 for r in batch_result.results if r.success)
        batch_result.labels_applied = sum(len(r.labels_applied) for r in batch_result.results)
        batch_result.total_tokens = self._total_tokens
        batch_result.total_cost_usd = self._total_cost

        return batch_result

    async def _label_batch(
        self,
        graph: "KnowledgeGraph",
        function_ids: List[str],
        context_category: Optional[str],
    ) -> List[LabelingResult]:
        """Label a batch of functions with a single LLM call.

        Internal method that prepares context for a batch of functions,
        makes the LLM call with tool calling, and parses the results.

        Args:
            graph: Knowledge graph
            function_ids: IDs of functions in this batch
            context_category: Optional category filter

        Returns:
            List of LabelingResult for each function
        """
        # Prepare context for each function
        functions_context = []
        valid_function_ids = []

        for func_id in function_ids:
            node = graph.nodes.get(func_id)
            if not node:
                logger.warning(f"Function {func_id} not found in graph")
                continue

            valid_function_ids.append(func_id)

            # Get function source and properties
            source = node.properties.get("source_code", node.properties.get("signature", ""))
            properties = node.properties

            # Get callers/callees from edges
            callers = self._get_callers(graph, func_id)
            callees = self._get_callees(graph, func_id)

            context = format_function_context(
                function_id=func_id,
                source=source,
                properties=properties,
                callers=callers,
                callees=callees,
            )
            functions_context.append(context)

        if not functions_context:
            return [LabelingResult(fid, success=False, error="Not found") for fid in function_ids]

        # Build prompt with optional label subset for scoped labeling
        label_subset = None
        if context_category:
            from alphaswarm_sol.labels.prompts import get_labels_for_context
            label_subset = get_labels_for_context(context_category)

        prompt = build_labeling_prompt("\n\n".join(functions_context), label_subset)

        # Estimate tokens (rough estimate: 4 chars = 1 token)
        estimated_tokens = (len(prompt) + len(LABELING_SYSTEM_PROMPT)) // 4
        if estimated_tokens > self.config.max_tokens_per_call:
            logger.warning(
                f"Estimated {estimated_tokens} tokens exceeds budget of "
                f"{self.config.max_tokens_per_call}, context may be truncated"
            )

        # Call LLM with tools
        try:
            response = await self.provider.generate_with_tools(
                prompt=prompt,
                tools=self._tools,
                tool_choice=LABELING_TOOL_CHOICE,
                system=LABELING_SYSTEM_PROMPT,
                max_tokens=2048,
                temperature=self.config.temperature,
            )

            self._total_tokens += response.input_tokens + response.output_tokens
            self._total_cost += response.cost_usd

            # Parse labels from tool calls and store in overlay
            results = self._parse_labeling_response(valid_function_ids, response)

            # Add results for functions not found in graph
            for fid in function_ids:
                if fid not in valid_function_ids:
                    results.append(LabelingResult(fid, success=False, error="Not found in graph"))

            return results

        except Exception as e:
            logger.error(f"Labeling failed: {e}")
            return [LabelingResult(fid, success=False, error=str(e)) for fid in function_ids]

    def _parse_labeling_response(
        self,
        function_ids: List[str],
        response: "LLMResponse",
    ) -> List[LabelingResult]:
        """Parse labels from LLM response and store in overlay.

        For each valid label parsed from tool calls, stores it via
        self.overlay.add_label(func_id, label) to persist in the overlay.

        Args:
            function_ids: Function IDs that were in this batch
            response: LLM response with tool calls

        Returns:
            List of LabelingResult for each function
        """
        results = {fid: LabelingResult(fid) for fid in function_ids}

        for tool_call in response.tool_calls:
            if tool_call["name"] == "apply_labels_batch":
                # Process batch labels
                for label_data in tool_call["input"].get("labels", []):
                    func_id = label_data.get("function_id")
                    if func_id not in results:
                        # Skip labels for functions not in this batch
                        logger.debug(f"Label for unknown function: {func_id}")
                        continue

                    label_id = label_data.get("label")
                    if not is_valid_label(label_id):
                        logger.warning(f"Invalid label ID from LLM: {label_id}")
                        continue

                    confidence = LabelConfidence(label_data.get("confidence", "medium"))
                    reasoning = label_data.get("reasoning")

                    label = FunctionLabel(
                        label_id=label_id,
                        confidence=confidence,
                        source=LabelSource.LLM,
                        reasoning=reasoning,
                    )

                    # Store parsed label in overlay via add_label
                    self.overlay.add_label(func_id, label)
                    results[func_id].labels_applied.append(label)

            elif tool_call["name"] == "apply_label":
                # Process single label
                label_data = tool_call["input"]
                func_id = label_data.get("function_id")
                if func_id not in results:
                    continue

                label = parse_label_from_tool_call(label_data)
                if label:
                    # Store parsed label in overlay via add_label
                    self.overlay.add_label(func_id, label)
                    results[func_id].labels_applied.append(label)

        # Mark results with tokens used
        tokens = response.input_tokens + response.output_tokens
        for result in results.values():
            result.tokens_used = tokens

        return list(results.values())

    def _get_callers(self, graph: "KnowledgeGraph", function_id: str) -> List[str]:
        """Get functions that call this function.

        Looks up edges in the graph where this function is the target
        of a CALLS or INTERNAL_CALL edge.

        Args:
            graph: Knowledge graph
            function_id: Function ID to find callers for

        Returns:
            List of caller function IDs (limited to 10)
        """
        callers = []
        for edge in graph.edges.values():
            if edge.target == function_id and edge.type in ("CALLS", "INTERNAL_CALL"):
                callers.append(edge.source)
        return callers[:10]  # Limit to prevent context bloat

    def _get_callees(self, graph: "KnowledgeGraph", function_id: str) -> List[str]:
        """Get functions this function calls.

        Looks up edges in the graph where this function is the source
        of a CALLS or INTERNAL_CALL edge.

        Args:
            graph: Knowledge graph
            function_id: Function ID to find callees for

        Returns:
            List of callee function IDs (limited to 10)
        """
        callees = []
        for edge in graph.edges.values():
            if edge.source == function_id and edge.type in ("CALLS", "INTERNAL_CALL"):
                callees.append(edge.target)
        return callees[:10]  # Limit to prevent context bloat

    def get_overlay(self) -> LabelOverlay:
        """Get the label overlay with all applied labels.

        Returns:
            LabelOverlay containing all labels applied during labeling
        """
        return self.overlay

    def set_overlay(self, overlay: LabelOverlay) -> None:
        """Set an existing overlay for incremental labeling.

        Useful when continuing a labeling session or merging results.

        Args:
            overlay: Existing LabelOverlay to use
        """
        self.overlay = overlay

    def get_statistics(self) -> Dict[str, Any]:
        """Get labeling statistics.

        Returns:
            Dictionary with:
                - total_tokens: Tokens used across all calls
                - total_cost_usd: Cost in USD
                - functions_labeled: Number of functions with labels
                - total_labels: Total labels applied
        """
        return {
            "total_tokens": self._total_tokens,
            "total_cost_usd": self._total_cost,
            "functions_labeled": len(self.overlay.labels),
            "total_labels": sum(len(ls.labels) for ls in self.overlay.labels.values()),
        }

    def reset_statistics(self) -> None:
        """Reset usage statistics.

        Useful when starting a new labeling session while keeping the overlay.
        """
        self._total_tokens = 0
        self._total_cost = 0.0


__all__ = [
    "LabelingConfig",
    "LabelingResult",
    "BatchLabelingResult",
    "LLMLabeler",
]
