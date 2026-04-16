"""Tool definitions for LLM labeling via Claude's tool calling.

This module provides JSON Schema-based tool definitions for structured
label application. These tools enable Claude to apply semantic labels
with guaranteed schema compliance via tool calling.

Usage:
    from alphaswarm_sol.labels.tools import build_label_tools, LABELING_TOOL_CHOICE

    # Get tools for API call
    tools = build_label_tools()

    # Use with forced tool choice for batch labeling
    response = await provider.generate_with_tools(
        prompt="...",
        tools=tools,
        tool_choice=LABELING_TOOL_CHOICE,
    )
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from .taxonomy import CORE_TAXONOMY
from .schema import FunctionLabel, LabelConfidence, LabelSource


def get_label_enum() -> List[str]:
    """Get all valid label IDs for tool schema.

    Returns:
        List of label IDs from CORE_TAXONOMY
    """
    return [label.id for label in CORE_TAXONOMY]


# Base tool definitions (enum populated at runtime)
_APPLY_LABEL_TOOL_BASE: Dict[str, Any] = {
    "name": "apply_label",
    "description": "Apply a semantic label to a function based on code analysis. "
    "Use this when analyzing a single function.",
    "input_schema": {
        "type": "object",
        "properties": {
            "function_id": {
                "type": "string",
                "description": "The ID of the function to label (format: contract.function)",
            },
            "label": {
                "type": "string",
                "enum": [],  # Populated from CORE_TAXONOMY
                "description": "The semantic label to apply (category.subcategory format)",
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "Confidence level: high (>= 0.8), medium (>= 0.5), low (< 0.5)",
            },
            "reasoning": {
                "type": "string",
                "description": "Required if confidence is low - explain the uncertainty",
            },
        },
        "required": ["function_id", "label", "confidence"],
    },
}

_APPLY_LABELS_BATCH_TOOL_BASE: Dict[str, Any] = {
    "name": "apply_labels_batch",
    "description": "Apply multiple semantic labels to functions in a single call. "
    "Use this when labeling multiple functions or applying multiple labels.",
    "input_schema": {
        "type": "object",
        "properties": {
            "labels": {
                "type": "array",
                "description": "Array of label assignments",
                "items": {
                    "type": "object",
                    "properties": {
                        "function_id": {
                            "type": "string",
                            "description": "The ID of the function to label",
                        },
                        "label": {
                            "type": "string",
                            "enum": [],  # Populated from CORE_TAXONOMY
                            "description": "The semantic label to apply",
                        },
                        "confidence": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": "Confidence level of the assignment",
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Required if confidence is low",
                        },
                    },
                    "required": ["function_id", "label", "confidence"],
                },
            },
        },
        "required": ["labels"],
    },
}


def build_label_tools() -> List[Dict[str, Any]]:
    """Build tool definitions with current taxonomy labels.

    Creates copies of the base tool definitions with the enum
    fields populated from CORE_TAXONOMY.

    Returns:
        List of tool definitions ready for API use
    """
    label_enum = get_label_enum()

    # Create apply_label tool
    apply_label = copy.deepcopy(_APPLY_LABEL_TOOL_BASE)
    apply_label["input_schema"]["properties"]["label"]["enum"] = label_enum

    # Create apply_labels_batch tool
    apply_batch = copy.deepcopy(_APPLY_LABELS_BATCH_TOOL_BASE)
    apply_batch["input_schema"]["properties"]["labels"]["items"]["properties"][
        "label"
    ]["enum"] = label_enum

    return [apply_label, apply_batch]


# Tool choice to force batch labeling
LABELING_TOOL_CHOICE: Dict[str, str] = {
    "type": "tool",
    "name": "apply_labels_batch",
}


def validate_tool_response(tool_name: str, response: Dict[str, Any]) -> bool:
    """Validate a tool response against its schema.

    Args:
        tool_name: Name of the tool ("apply_label" or "apply_labels_batch")
        response: Tool response to validate

    Returns:
        True if response is valid, False otherwise
    """
    if tool_name == "apply_label":
        required = ["function_id", "label", "confidence"]
        if not all(k in response for k in required):
            return False
        if response["confidence"] not in ["high", "medium", "low"]:
            return False
        label_ids = get_label_enum()
        if response["label"] not in label_ids:
            return False
        return True

    elif tool_name == "apply_labels_batch":
        if "labels" not in response:
            return False
        if not isinstance(response["labels"], list):
            return False
        label_ids = get_label_enum()
        for item in response["labels"]:
            required = ["function_id", "label", "confidence"]
            if not all(k in item for k in required):
                return False
            if item["confidence"] not in ["high", "medium", "low"]:
                return False
            if item["label"] not in label_ids:
                return False
        return True

    return False


def parse_label_from_tool_call(tool_call: Dict[str, Any]) -> Optional[FunctionLabel]:
    """Parse a FunctionLabel from a single label tool call response.

    Args:
        tool_call: Tool call input containing label data

    Returns:
        FunctionLabel if valid, None otherwise
    """
    try:
        return FunctionLabel(
            label_id=tool_call["label"],
            confidence=LabelConfidence(tool_call["confidence"]),
            source=LabelSource.LLM,
            reasoning=tool_call.get("reasoning"),
        )
    except (KeyError, ValueError):
        return None


def parse_labels_from_batch_response(
    tool_input: Dict[str, Any]
) -> List[tuple[str, FunctionLabel]]:
    """Parse FunctionLabels from a batch tool call response.

    Args:
        tool_input: Tool call input containing labels array

    Returns:
        List of (function_id, FunctionLabel) tuples
    """
    results = []
    labels = tool_input.get("labels", [])

    for item in labels:
        try:
            label = FunctionLabel(
                label_id=item["label"],
                confidence=LabelConfidence(item["confidence"]),
                source=LabelSource.LLM,
                reasoning=item.get("reasoning"),
            )
            results.append((item["function_id"], label))
        except (KeyError, ValueError):
            continue

    return results


def extract_labels_from_tool_calls(
    tool_calls: List[Dict[str, Any]]
) -> List[tuple[str, FunctionLabel]]:
    """Extract all labels from a list of tool calls.

    Args:
        tool_calls: List of tool calls from LLM response

    Returns:
        List of (function_id, FunctionLabel) tuples
    """
    results = []

    for tool_call in tool_calls:
        name = tool_call.get("name", "")
        tool_input = tool_call.get("input", {})

        if name == "apply_label":
            function_id = tool_input.get("function_id", "")
            label = parse_label_from_tool_call(tool_input)
            if label and function_id:
                results.append((function_id, label))

        elif name == "apply_labels_batch":
            results.extend(parse_labels_from_batch_response(tool_input))

    return results


__all__ = [
    "get_label_enum",
    "build_label_tools",
    "LABELING_TOOL_CHOICE",
    "validate_tool_response",
    "parse_label_from_tool_call",
    "parse_labels_from_batch_response",
    "extract_labels_from_tool_calls",
]
