"""Phase 21: Tool Comparison.

This module provides functionality for comparing VKG detection
capabilities against other security tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Tool(str, Enum):
    """Security analysis tools."""
    VKG = "vkg"
    SLITHER = "slither"
    MYTHRIL = "mythril"
    SEMGREP = "semgrep"
    SECURIFY = "securify"
    MANTICORE = "manticore"


@dataclass
class ToolCapability:
    """Capability of a security tool.

    Attributes:
        tool: Tool name
        vulnerability_types: Types of vulnerabilities detected
        analysis_depth: Depth of analysis (static, symbolic, etc.)
        average_time_sec: Average analysis time
        false_positive_rate: Known FP rate
        strengths: Tool strengths
        weaknesses: Tool weaknesses
    """
    tool: Tool
    vulnerability_types: List[str] = field(default_factory=list)
    analysis_depth: str = "static"
    average_time_sec: float = 0.0
    false_positive_rate: float = 0.0
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool": self.tool.value,
            "vulnerability_types": self.vulnerability_types,
            "analysis_depth": self.analysis_depth,
            "average_time_sec": self.average_time_sec,
            "false_positive_rate": self.false_positive_rate,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
        }


# Known tool capabilities
TOOL_CAPABILITIES: Dict[Tool, ToolCapability] = {
    Tool.VKG: ToolCapability(
        tool=Tool.VKG,
        vulnerability_types=[
            "reentrancy", "access_control", "oracle_manipulation",
            "dos", "arithmetic", "slippage", "signature",
        ],
        analysis_depth="semantic graph",
        average_time_sec=2.0,
        false_positive_rate=0.05,
        strengths=[
            "Semantic operation detection",
            "Name-agnostic detection",
            "Fast incremental builds",
            "Pattern-based extensibility",
        ],
        weaknesses=[
            "Requires Slither backend",
            "Limited cross-contract analysis",
        ],
    ),
    Tool.SLITHER: ToolCapability(
        tool=Tool.SLITHER,
        vulnerability_types=[
            "reentrancy", "uninitialized_storage", "arbitrary_send",
            "suicidal", "low_level_calls",
        ],
        analysis_depth="static AST",
        average_time_sec=5.0,
        false_positive_rate=0.15,
        strengths=[
            "Fast analysis",
            "Good coverage",
            "Active development",
        ],
        weaknesses=[
            "Name-dependent detection",
            "Higher FP rate",
        ],
    ),
    Tool.MYTHRIL: ToolCapability(
        tool=Tool.MYTHRIL,
        vulnerability_types=[
            "reentrancy", "integer_overflow", "tx_origin",
            "delegatecall", "ether_theft",
        ],
        analysis_depth="symbolic execution",
        average_time_sec=60.0,
        false_positive_rate=0.10,
        strengths=[
            "Deep symbolic analysis",
            "Path exploration",
            "Low FP on findings",
        ],
        weaknesses=[
            "Slow analysis",
            "Path explosion on complex contracts",
        ],
    ),
    Tool.SEMGREP: ToolCapability(
        tool=Tool.SEMGREP,
        vulnerability_types=[
            "access_control", "deprecated_functions", "tx_origin",
        ],
        analysis_depth="pattern matching",
        average_time_sec=1.0,
        false_positive_rate=0.20,
        strengths=[
            "Very fast",
            "Custom rules",
            "CI/CD friendly",
        ],
        weaknesses=[
            "Limited semantic analysis",
            "Pattern-dependent",
        ],
    ),
}


@dataclass
class ComparisonResult:
    """Result of comparing tools.

    Attributes:
        vulnerability: Vulnerability tested
        tool_results: Results per tool (True = detected)
        ground_truth: Whether vulnerability actually exists
        notes: Additional notes
    """
    vulnerability: str
    tool_results: Dict[Tool, bool] = field(default_factory=dict)
    ground_truth: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "vulnerability": self.vulnerability,
            "tool_results": {t.value: v for t, v in self.tool_results.items()},
            "ground_truth": self.ground_truth,
            "notes": self.notes,
        }


@dataclass
class ToolComparisonSummary:
    """Summary of tool comparison.

    Attributes:
        tools: Tools compared
        results: Comparison results
        precision_by_tool: Precision per tool
        recall_by_tool: Recall per tool
        f1_by_tool: F1 score per tool
    """
    tools: List[Tool] = field(default_factory=list)
    results: List[ComparisonResult] = field(default_factory=list)
    precision_by_tool: Dict[Tool, float] = field(default_factory=dict)
    recall_by_tool: Dict[Tool, float] = field(default_factory=dict)
    f1_by_tool: Dict[Tool, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tools": [t.value for t in self.tools],
            "results": [r.to_dict() for r in self.results],
            "precision_by_tool": {t.value: v for t, v in self.precision_by_tool.items()},
            "recall_by_tool": {t.value: v for t, v in self.recall_by_tool.items()},
            "f1_by_tool": {t.value: v for t, v in self.f1_by_tool.items()},
        }

    def to_markdown_table(self) -> str:
        """Generate markdown comparison table."""
        lines = ["| Tool | Precision | Recall | F1 Score |", "|------|-----------|--------|----------|"]

        for tool in self.tools:
            p = self.precision_by_tool.get(tool, 0)
            r = self.recall_by_tool.get(tool, 0)
            f1 = self.f1_by_tool.get(tool, 0)
            lines.append(f"| {tool.value} | {p:.1%} | {r:.1%} | {f1:.1%} |")

        return "\n".join(lines)


class ToolComparison:
    """Compares VKG against other security tools.

    Tracks detection results across tools and calculates
    comparative metrics.
    """

    def __init__(self, tools: Optional[List[Tool]] = None):
        """Initialize comparison.

        Args:
            tools: Tools to compare (default: all known tools)
        """
        self.tools = tools or list(Tool)
        self._results: List[ComparisonResult] = []

    def add_result(
        self,
        vulnerability: str,
        tool_results: Dict[Tool, bool],
        ground_truth: bool,
        notes: str = "",
    ) -> None:
        """Add a comparison result.

        Args:
            vulnerability: Vulnerability type
            tool_results: Detection result per tool
            ground_truth: Whether vulnerability actually exists
            notes: Additional notes
        """
        self._results.append(ComparisonResult(
            vulnerability=vulnerability,
            tool_results=tool_results,
            ground_truth=ground_truth,
            notes=notes,
        ))

    def get_summary(self) -> ToolComparisonSummary:
        """Get comparison summary.

        Returns:
            ToolComparisonSummary
        """
        summary = ToolComparisonSummary(
            tools=self.tools,
            results=self._results,
        )

        # Calculate metrics per tool
        for tool in self.tools:
            tp = 0
            fp = 0
            fn = 0

            for result in self._results:
                predicted = result.tool_results.get(tool, False)
                actual = result.ground_truth

                if predicted and actual:
                    tp += 1
                elif predicted and not actual:
                    fp += 1
                elif not predicted and actual:
                    fn += 1

            # Calculate metrics
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            summary.precision_by_tool[tool] = precision
            summary.recall_by_tool[tool] = recall
            summary.f1_by_tool[tool] = f1

        return summary

    def get_tool_capabilities(self, tool: Tool) -> Optional[ToolCapability]:
        """Get known capabilities for a tool.

        Args:
            tool: Tool to look up

        Returns:
            ToolCapability or None
        """
        return TOOL_CAPABILITIES.get(tool)


def compare_tools(
    results: List[Dict[str, Any]],
    tools: Optional[List[Tool]] = None,
) -> ToolComparisonSummary:
    """Compare tools based on results.

    Convenience function for quick comparison.

    Args:
        results: List of comparison results with keys:
            - vulnerability: str
            - tool_results: Dict[str, bool] (tool name -> detected)
            - ground_truth: bool
        tools: Tools to compare

    Returns:
        ToolComparisonSummary
    """
    comparison = ToolComparison(tools)

    for result in results:
        tool_results = {
            Tool(name): detected
            for name, detected in result.get("tool_results", {}).items()
            if name in [t.value for t in Tool]
        }

        comparison.add_result(
            vulnerability=result.get("vulnerability", ""),
            tool_results=tool_results,
            ground_truth=result.get("ground_truth", False),
            notes=result.get("notes", ""),
        )

    return comparison.get_summary()


__all__ = [
    "Tool",
    "ToolCapability",
    "ComparisonResult",
    "ToolComparisonSummary",
    "ToolComparison",
    "TOOL_CAPABILITIES",
    "compare_tools",
]
