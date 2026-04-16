"""Labeling prompts for LLM-based semantic labeling.

This module provides the system and user prompts for the LLM labeler microagent.
The prompts guide the LLM to apply semantic labels to Solidity functions based
on code behavior analysis.

Key Components:
- LABELING_SYSTEM_PROMPT: System prompt explaining labeling task and guidelines
- LABELING_USER_PROMPT_TEMPLATE: User prompt template with function context
- build_labeling_prompt(): Helper to build prompts with context
- format_function_context(): Format a single function's context
- CONTEXT_TO_LABEL_CATEGORIES: Maps analysis contexts to relevant label categories
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


LABELING_SYSTEM_PROMPT = """You are a smart contract security analyst specializing in semantic labeling.

Your task is to analyze Solidity functions and apply semantic labels that describe:
1. **Intent**: What the function is meant to do (e.g., transfers_ownership, enforces_timelock)
2. **Constraints**: What must be true for the function (e.g., only_owner_can_call, balance_never_negative)

## Label Categories

- **access_control**: Authorization and permission checks
- **state_mutation**: State modification patterns
- **external_interaction**: External calls and oracle usage
- **value_handling**: ETH/token transfers and fees
- **invariants**: Balance checks, supply constraints
- **temporal**: Timelocks, deadlines

## Guidelines

1. Apply labels based on CODE BEHAVIOR, not comments or names
2. Use HIGH confidence for clear patterns (explicit modifiers, obvious checks)
3. Use MEDIUM confidence for inferred patterns (implicit checks, context-dependent)
4. Use LOW confidence with reasoning for uncertain patterns
5. Apply negation labels (e.g., no_access_check) when protection is MISSING
6. A function can have multiple labels from different categories

## Response Format

Use the apply_labels_batch tool to apply all labels for the functions provided.
For each label, specify:
- function_id: The function identifier
- label: The semantic label from the taxonomy
- confidence: high, medium, or low
- reasoning: Required only for low confidence labels
"""


LABELING_USER_PROMPT_TEMPLATE = """Analyze the following function(s) and apply semantic labels.

## Functions to Analyze

{functions_context}

## Available Labels

{available_labels}

## Instructions

1. Analyze each function's behavior (ignore names, focus on code)
2. Apply relevant labels from the taxonomy
3. Include negation labels for missing protections
4. Use the apply_labels_batch tool to submit all labels

Apply labels now."""


def build_labeling_prompt(
    functions_context: str,
    label_subset: Optional[List[str]] = None,
) -> str:
    """Build the labeling prompt with function context.

    Constructs a complete user prompt by formatting the template with
    the provided function context and available labels from the taxonomy.

    Args:
        functions_context: Formatted context for functions to label
        label_subset: Optional list of label IDs to restrict available labels.
                     If None, all labels from CORE_TAXONOMY are available.

    Returns:
        Formatted user prompt ready for LLM consumption

    Example:
        >>> context = format_function_context("Vault.withdraw", "function withdraw()...", {})
        >>> prompt = build_labeling_prompt(context)
        >>> print(prompt[:100])
        Analyze the following function(s) and apply semantic labels...
    """
    from alphaswarm_sol.labels.taxonomy import CORE_TAXONOMY

    if label_subset:
        labels = [label for label in CORE_TAXONOMY if label.id in label_subset]
    else:
        labels = CORE_TAXONOMY

    available_labels = "\n".join(
        f"- {label.id}: {label.description}" for label in labels
    )

    return LABELING_USER_PROMPT_TEMPLATE.format(
        functions_context=functions_context,
        available_labels=available_labels,
    )


def format_function_context(
    function_id: str,
    source: str,
    properties: Dict[str, Any],
    callers: Optional[List[str]] = None,
    callees: Optional[List[str]] = None,
) -> str:
    """Format a single function's context for the prompt.

    Creates a structured representation of a function including its source code,
    key security-relevant properties, and call relationships.

    Args:
        function_id: The function identifier (e.g., "Vault.withdraw")
        source: Source code or signature of the function
        properties: Dictionary of function properties from the knowledge graph
        callers: Optional list of function IDs that call this function
        callees: Optional list of function IDs this function calls

    Returns:
        Formatted markdown context for inclusion in the labeling prompt

    Example:
        >>> context = format_function_context(
        ...     "Vault.withdraw",
        ...     "function withdraw(uint256 amount) external { ... }",
        ...     {"visibility": "external", "writes_state": True},
        ...     callers=["Router.executeWithdraw"],
        ...     callees=["Token.transfer"]
        ... )
        >>> "### Function: Vault.withdraw" in context
        True
    """
    context = f"### Function: {function_id}\n\n"
    context += f"```solidity\n{source}\n```\n\n"

    # Add key properties that are relevant for labeling
    key_props = [
        "visibility",
        "modifiers",
        "writes_state",
        "calls_external",
        "is_payable",
        "state_mutability",
        "has_require",
        "has_access_gate",
    ]
    prop_lines = []
    for key in key_props:
        if key in properties:
            value = properties[key]
            # Format list values nicely
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value) if value else "none"
            prop_lines.append(f"- {key}: {value}")

    if prop_lines:
        context += "**Properties:**\n" + "\n".join(prop_lines) + "\n\n"

    if callers:
        # Limit displayed callers to prevent prompt bloat
        displayed_callers = callers[:5]
        more = f" (+{len(callers) - 5} more)" if len(callers) > 5 else ""
        context += f"**Called by:** {', '.join(displayed_callers)}{more}\n"

    if callees:
        # Limit displayed callees to prevent prompt bloat
        displayed_callees = callees[:5]
        more = f" (+{len(callees) - 5} more)" if len(callees) > 5 else ""
        context += f"**Calls:** {', '.join(displayed_callees)}{more}\n"

    return context


# Context filtering prompts for scoped labeling
CONTEXT_TO_LABEL_CATEGORIES: Dict[str, Optional[List[str]]] = {
    "reentrancy": ["state_mutation", "external_interaction", "value_handling"],
    "access_control": ["access_control"],
    "oracle": ["external_interaction", "invariants"],
    "value_transfer": ["value_handling", "invariants"],
    "temporal": ["temporal"],
    "general": None,  # All categories
}


def get_relevant_label_categories(analysis_context: str) -> Optional[List[str]]:
    """Get label categories relevant to an analysis context.

    Maps analysis contexts (like "reentrancy" or "access_control") to the
    label categories that are most relevant for that type of analysis.

    Args:
        analysis_context: The analysis context (e.g., "reentrancy", "access_control")

    Returns:
        List of relevant category names, or None for all categories

    Example:
        >>> get_relevant_label_categories("reentrancy")
        ['state_mutation', 'external_interaction', 'value_handling']
        >>> get_relevant_label_categories("general") is None
        True
    """
    return CONTEXT_TO_LABEL_CATEGORIES.get(analysis_context.lower())


def get_labels_for_context(analysis_context: str) -> Optional[List[str]]:
    """Get label IDs relevant to an analysis context.

    Similar to get_relevant_label_categories but returns actual label IDs
    instead of category names.

    Args:
        analysis_context: The analysis context (e.g., "reentrancy")

    Returns:
        List of label IDs, or None for all labels

    Example:
        >>> labels = get_labels_for_context("access_control")
        >>> "access_control.owner_only" in labels
        True
    """
    from alphaswarm_sol.labels.taxonomy import CORE_TAXONOMY

    categories = get_relevant_label_categories(analysis_context)
    if categories is None:
        return None

    return [
        label.id
        for label in CORE_TAXONOMY
        if label.category.value in categories
    ]


def estimate_prompt_tokens(functions_context: str, label_subset: Optional[List[str]] = None) -> int:
    """Estimate the number of tokens in the labeling prompt.

    Provides a rough estimate using the 4 characters = 1 token heuristic.
    This is useful for budget checking before making API calls.

    Args:
        functions_context: Formatted function context
        label_subset: Optional subset of labels to include

    Returns:
        Estimated token count

    Example:
        >>> estimate_prompt_tokens("function foo() {}")
        50  # Approximate, depends on taxonomy size
    """
    prompt = build_labeling_prompt(functions_context, label_subset)
    # Rough estimate: 4 characters per token (varies by tokenizer)
    return (len(prompt) + len(LABELING_SYSTEM_PROMPT)) // 4


__all__ = [
    "LABELING_SYSTEM_PROMPT",
    "LABELING_USER_PROMPT_TEMPLATE",
    "build_labeling_prompt",
    "format_function_context",
    "CONTEXT_TO_LABEL_CATEGORIES",
    "get_relevant_label_categories",
    "get_labels_for_context",
    "estimate_prompt_tokens",
]
