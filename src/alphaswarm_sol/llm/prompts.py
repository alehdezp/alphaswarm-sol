"""Phase 12: LLM Prompts and Step-Back Prompting.

This module provides prompt generation for LLM-enhanced analysis,
including step-back prompting for deeper understanding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class PromptStyle(str, Enum):
    """Styles of prompts."""
    STEP_BACK = "step_back"
    DIRECT = "direct"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    FEW_SHOT = "few_shot"


@dataclass
class StepBackPrompt:
    """Step-back prompt for deeper analysis.

    Step-back prompting asks the LLM to first understand high-level concepts
    before analyzing specific code patterns.

    Attributes:
        context: High-level context question
        specific: Specific analysis question
        background: Background information
        examples: Optional examples for few-shot learning
    """
    context: str
    specific: str
    background: str = ""
    examples: List[Dict[str, str]] = field(default_factory=list)

    def to_messages(self) -> List[Dict[str, str]]:
        """Convert to message format for LLM API."""
        messages = []

        # System message with background
        if self.background:
            messages.append({
                "role": "system",
                "content": self.background,
            })

        # Add examples if provided
        for example in self.examples:
            messages.append({
                "role": "user",
                "content": example.get("question", ""),
            })
            messages.append({
                "role": "assistant",
                "content": example.get("answer", ""),
            })

        # Step-back question (context)
        messages.append({
            "role": "user",
            "content": f"Step back and consider: {self.context}",
        })

        # Specific question
        messages.append({
            "role": "user",
            "content": f"Now, specifically: {self.specific}",
        })

        return messages

    def to_single_prompt(self) -> str:
        """Convert to single prompt string."""
        parts = []

        if self.background:
            parts.append(f"Background:\n{self.background}\n")

        parts.append(f"First, step back and consider: {self.context}\n")
        parts.append(f"Then, specifically analyze: {self.specific}")

        return "\n".join(parts)


@dataclass
class AnalysisPrompt:
    """Prompt for code analysis.

    Attributes:
        code: Code to analyze
        function_name: Name of function being analyzed
        properties: Security properties from the graph
        context: Additional context
        query: Specific analysis query
        output_format: Expected output format
    """
    code: str
    function_name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    context: str = ""
    query: str = ""
    output_format: str = "json"

    def to_prompt(self) -> str:
        """Generate analysis prompt."""
        parts = []

        # Header
        parts.append(f"Analyze the following Solidity function: `{self.function_name}`\n")

        # Code
        parts.append("```solidity")
        parts.append(self.code)
        parts.append("```\n")

        # Properties from graph analysis
        if self.properties:
            parts.append("Known security properties:")
            for key, value in self.properties.items():
                parts.append(f"  - {key}: {value}")
            parts.append("")

        # Context
        if self.context:
            parts.append(f"Context: {self.context}\n")

        # Query
        if self.query:
            parts.append(f"Question: {self.query}\n")
        else:
            parts.append("Identify potential security vulnerabilities and provide:\n")
            parts.append("1. Risk assessment (severity and likelihood)")
            parts.append("2. Developer intent analysis")
            parts.append("3. Potential attack vectors")
            parts.append("4. Remediation suggestions\n")

        # Output format
        if self.output_format == "json":
            parts.append("Respond in JSON format with keys: risk_level, intent, vulnerabilities, recommendations")

        return "\n".join(parts)


class PromptBuilder:
    """Builder for constructing complex prompts.

    Provides a fluent interface for building prompts with various components.
    """

    def __init__(self):
        """Initialize builder."""
        self._system: str = ""
        self._context: List[str] = []
        self._code: Optional[str] = None
        self._function_name: str = ""
        self._properties: Dict[str, Any] = {}
        self._query: str = ""
        self._examples: List[Dict[str, str]] = []
        self._style: PromptStyle = PromptStyle.DIRECT

    def system(self, content: str) -> "PromptBuilder":
        """Set system message."""
        self._system = content
        return self

    def add_context(self, context: str) -> "PromptBuilder":
        """Add context information."""
        self._context.append(context)
        return self

    def code(self, code: str, function_name: str = "") -> "PromptBuilder":
        """Add code to analyze."""
        self._code = code
        self._function_name = function_name
        return self

    def properties(self, props: Dict[str, Any]) -> "PromptBuilder":
        """Add known properties."""
        self._properties.update(props)
        return self

    def query(self, query: str) -> "PromptBuilder":
        """Set the analysis query."""
        self._query = query
        return self

    def add_example(self, question: str, answer: str) -> "PromptBuilder":
        """Add few-shot example."""
        self._examples.append({"question": question, "answer": answer})
        return self

    def style(self, style: PromptStyle) -> "PromptBuilder":
        """Set prompt style."""
        self._style = style
        return self

    def build(self) -> str:
        """Build the final prompt."""
        parts = []

        # System/background
        if self._system:
            parts.append(f"System: {self._system}\n")

        # Context
        if self._context:
            parts.append("Context:")
            for ctx in self._context:
                parts.append(f"  - {ctx}")
            parts.append("")

        # Examples for few-shot
        if self._examples and self._style == PromptStyle.FEW_SHOT:
            parts.append("Examples:")
            for ex in self._examples:
                parts.append(f"Q: {ex['question']}")
                parts.append(f"A: {ex['answer']}")
            parts.append("")

        # Code
        if self._code:
            parts.append(f"Function: `{self._function_name}`")
            parts.append("```solidity")
            parts.append(self._code)
            parts.append("```\n")

        # Properties
        if self._properties:
            parts.append("Security properties:")
            for k, v in self._properties.items():
                parts.append(f"  - {k}: {v}")
            parts.append("")

        # Step-back for that style
        if self._style == PromptStyle.STEP_BACK:
            parts.append("Step 1: First, consider what this function is trying to accomplish.")
            parts.append("Step 2: Identify the security model and assumptions.")
            parts.append("Step 3: Now analyze for vulnerabilities.\n")

        # Chain of thought
        if self._style == PromptStyle.CHAIN_OF_THOUGHT:
            parts.append("Think through this step by step:\n")

        # Query
        if self._query:
            parts.append(f"Question: {self._query}")
        else:
            parts.append("Analyze this code for security vulnerabilities.")

        return "\n".join(parts)

    def build_messages(self) -> List[Dict[str, str]]:
        """Build as message list for chat API."""
        messages = []

        if self._system:
            messages.append({"role": "system", "content": self._system})

        # Combine rest into user message
        user_content = self.build()
        if self._system:
            # Remove system part from user content
            user_content = user_content.replace(f"System: {self._system}\n\n", "")

        messages.append({"role": "user", "content": user_content})

        return messages


def generate_analysis_prompt(
    code: str,
    function_name: str,
    properties: Optional[Dict[str, Any]] = None,
    context: str = "",
    query: str = "",
) -> str:
    """Generate an analysis prompt for a function.

    Args:
        code: Function code
        function_name: Name of the function
        properties: Known security properties
        context: Additional context
        query: Specific query

    Returns:
        Generated prompt string
    """
    prompt = AnalysisPrompt(
        code=code,
        function_name=function_name,
        properties=properties or {},
        context=context,
        query=query,
    )
    return prompt.to_prompt()


def generate_step_back_prompt(
    function_summary: str,
    vulnerability_type: str,
    code_snippet: str = "",
) -> StepBackPrompt:
    """Generate a step-back prompt for vulnerability analysis.

    Args:
        function_summary: Summary of the function
        vulnerability_type: Type of potential vulnerability
        code_snippet: Optional code snippet

    Returns:
        StepBackPrompt instance
    """
    context_question = (
        f"What are the general principles of {vulnerability_type} vulnerabilities "
        f"in Solidity smart contracts? What conditions must exist for this type "
        f"of vulnerability to be exploitable?"
    )

    specific_question = (
        f"Given this function: {function_summary}\n"
        f"Is it vulnerable to {vulnerability_type}? "
        f"If so, describe the attack vector and provide remediation."
    )

    background = (
        "You are a smart contract security expert. You analyze Solidity code "
        "for vulnerabilities. You understand common attack patterns including "
        "reentrancy, access control issues, oracle manipulation, and more."
    )

    # Add example for few-shot
    examples = [
        {
            "question": "Is a function that transfers ETH before updating state reentrancy-vulnerable?",
            "answer": (
                "Yes, this violates the Checks-Effects-Interactions pattern. "
                "An attacker can re-enter the function during the ETH transfer "
                "callback before the state is updated, allowing multiple withdrawals. "
                "Fix: Update state before external calls or use ReentrancyGuard."
            ),
        }
    ]

    return StepBackPrompt(
        context=context_question,
        specific=specific_question,
        background=background,
        examples=examples,
    )


# Pre-defined prompt templates
VULNERABILITY_ANALYSIS_TEMPLATE = """
You are analyzing a Solidity smart contract function for security vulnerabilities.

Function: {function_name}
```solidity
{code}
```

Known properties from static analysis:
{properties}

Analyze this function for the following vulnerability types:
1. Reentrancy (external calls before state updates)
2. Access control (missing or weak authentication)
3. Integer overflow/underflow (unsafe arithmetic)
4. Oracle manipulation (stale or manipulated price feeds)
5. Front-running (transaction ordering attacks)

For each potential vulnerability found, provide:
- Severity (Critical/High/Medium/Low/Info)
- Confidence (High/Medium/Low)
- Description of the issue
- Attack scenario
- Recommended fix

Respond in JSON format.
"""

FALSE_POSITIVE_ANALYSIS_TEMPLATE = """
A static analyzer has flagged a potential vulnerability in this code:

Function: {function_name}
```solidity
{code}
```

Flagged issue: {issue_description}

Analyze whether this is a true vulnerability or a false positive.
Consider:
1. The actual execution context
2. Any implicit protections in the code
3. Whether the flagged pattern is actually exploitable

Provide your assessment:
- Is this a true positive or false positive?
- Confidence level
- Reasoning
"""


__all__ = [
    "PromptStyle",
    "StepBackPrompt",
    "AnalysisPrompt",
    "PromptBuilder",
    "generate_analysis_prompt",
    "generate_step_back_prompt",
    "VULNERABILITY_ANALYSIS_TEMPLATE",
    "FALSE_POSITIVE_ANALYSIS_TEMPLATE",
]
