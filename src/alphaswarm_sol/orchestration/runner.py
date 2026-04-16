"""Tool Runner for Orchestrator Mode (Phase 5 Task 5.8).

Runs multiple analysis tools (VKG, Slither, Aderyn) and normalizes their output.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ToolStatus(str, Enum):
    """Status of a tool execution."""

    SUCCESS = "success"
    NOT_INSTALLED = "not_installed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class ToolResult:
    """Result from running an analysis tool."""

    tool: str
    status: ToolStatus
    findings: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool": self.tool,
            "status": self.status.value,
            "findings_count": len(self.findings),
            "error": self.error,
            "execution_time": self.execution_time,
        }


class ToolRunner:
    """Run analysis tools on a Solidity project.

    Supports VKG (always available), Slither, and Aderyn.
    Results are normalized to a common finding format.
    """

    SUPPORTED_TOOLS = ["vkg", "slither", "aderyn"]

    def __init__(self, project_path: Path):
        """Initialize runner with project path.

        Args:
            project_path: Path to Solidity project directory
        """
        self.project_path = Path(project_path).resolve()

    def check_tool_installed(self, tool: str) -> bool:
        """Check if a tool is installed and available.

        Args:
            tool: Tool name (vkg, slither, aderyn)

        Returns:
            True if tool is available
        """
        if tool == "vkg":
            return True  # Always available (this package)
        elif tool == "slither":
            return shutil.which("slither") is not None
        elif tool == "aderyn":
            return shutil.which("aderyn") is not None
        return False

    def get_available_tools(self) -> List[str]:
        """Get list of available tools.

        Returns:
            List of tool names that are installed
        """
        return [t for t in self.SUPPORTED_TOOLS if self.check_tool_installed(t)]

    def run_tool(self, tool: str) -> ToolResult:
        """Run a single analysis tool.

        Args:
            tool: Tool name to run

        Returns:
            ToolResult with status and findings
        """
        start = time.time()

        if tool not in self.SUPPORTED_TOOLS:
            return ToolResult(
                tool=tool,
                status=ToolStatus.ERROR,
                error=f"Unknown tool: {tool}. Supported: {self.SUPPORTED_TOOLS}",
            )

        if not self.check_tool_installed(tool):
            return ToolResult(
                tool=tool,
                status=ToolStatus.NOT_INSTALLED,
                error=f"{tool} not found in PATH",
            )

        try:
            if tool == "vkg":
                findings = self._run_vkg()
            elif tool == "slither":
                findings = self._run_slither()
            elif tool == "aderyn":
                findings = self._run_aderyn()
            else:
                # Should never reach here due to earlier check
                findings = []

            return ToolResult(
                tool=tool,
                status=ToolStatus.SUCCESS,
                findings=findings,
                execution_time=time.time() - start,
            )

        except Exception as e:
            return ToolResult(
                tool=tool,
                status=ToolStatus.ERROR,
                error=str(e),
                execution_time=time.time() - start,
            )

    def run_all(
        self, tools: Optional[List[str]] = None, skip_missing: bool = True
    ) -> List[ToolResult]:
        """Run multiple tools on the project.

        Args:
            tools: List of tools to run (default: all supported)
            skip_missing: If True, skip tools not installed. If False, return NOT_INSTALLED status.

        Returns:
            List of ToolResult for each tool
        """
        if tools is None:
            tools = self.SUPPORTED_TOOLS.copy()

        results = []
        for tool in tools:
            if skip_missing and not self.check_tool_installed(tool):
                results.append(
                    ToolResult(
                        tool=tool,
                        status=ToolStatus.SKIPPED,
                        error=f"{tool} not installed (skipped)",
                    )
                )
            else:
                results.append(self.run_tool(tool))

        return results

    def _run_vkg(self) -> List[Dict[str, Any]]:
        """Run VKG analysis.

        Returns:
            List of normalized findings
        """
        from alphaswarm_sol.kg.builder import VKGBuilder
        from alphaswarm_sol.queries.patterns import PatternEngine

        builder = VKGBuilder(self.project_path)
        graph = builder.build(self.project_path)

        # Run pattern matching
        engine = PatternEngine()
        matches = engine.run_all_patterns(graph)

        return [self._normalize_vkg_finding(m) for m in matches]

    def _run_slither(self) -> List[Dict[str, Any]]:
        """Run Slither analysis.

        Returns:
            List of normalized findings
        """
        result = subprocess.run(
            ["slither", ".", "--json", "-"],
            cwd=self.project_path,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        # Slither returns non-zero on findings, check stdout
        if not result.stdout:
            if result.returncode != 0:
                raise RuntimeError(f"Slither failed: {result.stderr}")
            return []

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse Slither output: {e}")

        detectors = output.get("results", {}).get("detectors", [])
        return [self._normalize_slither_finding(d) for d in detectors]

    def _run_aderyn(self) -> List[Dict[str, Any]]:
        """Run Aderyn analysis.

        Returns:
            List of normalized findings
        """
        # Aderyn outputs to stdout with --stdout flag
        result = subprocess.run(
            ["aderyn", ".", "--output", "json", "--stdout"],
            cwd=self.project_path,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0 and not result.stdout:
            raise RuntimeError(f"Aderyn failed: {result.stderr}")

        if not result.stdout:
            return []

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse Aderyn output: {e}")

        # Aderyn has high/medium/low issue lists
        findings = []
        for severity in ["high", "medium", "low"]:
            issues = output.get(f"{severity}_issues", {}).get("issues", [])
            for issue in issues:
                issue["_severity"] = severity
                findings.append(self._normalize_aderyn_finding(issue))

        return findings

    def _normalize_vkg_finding(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize VKG pattern match to common format.

        Args:
            match: Raw VKG pattern match

        Returns:
            Normalized finding dict
        """
        location = match.get("location", {})
        evidence = match.get("evidence", {})

        return {
            "source": "vkg",
            "id": match.get("pattern_id", match.get("id", "unknown")),
            "title": match.get("title", match.get("pattern_id", "")),
            "severity": match.get("severity", "medium"),
            "category": match.get("category", match.get("lens", "unknown")),
            "file": location.get("file", evidence.get("file", "")),
            "line": location.get("line", evidence.get("line", 0)),
            "function": location.get("function", evidence.get("function")),
            "confidence": match.get("confidence", 0.7),
            "raw": match,
        }

    def _normalize_slither_finding(self, detector: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Slither detector result to common format.

        Args:
            detector: Raw Slither detector result

        Returns:
            Normalized finding dict
        """
        elements = detector.get("elements", [])
        first = elements[0] if elements else {}
        source_mapping = first.get("source_mapping", {})

        # Get line number
        lines = source_mapping.get("lines", [])
        line = lines[0] if lines else 0

        # Map Slither confidence to numeric
        confidence_map = {"High": 0.9, "Medium": 0.7, "Low": 0.5, "Informational": 0.3}

        return {
            "source": "slither",
            "id": detector.get("check", "unknown"),
            "title": detector.get("description", "")[:200],
            "severity": detector.get("impact", "Low").lower(),
            "category": detector.get("check", "unknown"),
            "file": source_mapping.get("filename", ""),
            "line": line,
            "function": first.get("name"),
            "confidence": confidence_map.get(
                detector.get("confidence", "Low"), 0.5
            ),
            "raw": detector,
        }

    def _normalize_aderyn_finding(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Aderyn issue to common format.

        Args:
            issue: Raw Aderyn issue

        Returns:
            Normalized finding dict
        """
        instances = issue.get("instances", [])
        first_instance = instances[0] if instances else {}

        # Extract file/line from instance
        src = first_instance.get("src", "")
        file_path = ""
        line = 0

        if src:
            # Aderyn src format: "file.sol:line:col"
            parts = src.split(":")
            if parts:
                file_path = parts[0]
            if len(parts) > 1:
                try:
                    line = int(parts[1])
                except ValueError:
                    pass

        return {
            "source": "aderyn",
            "id": issue.get("detector_name", "unknown"),
            "title": issue.get("title", ""),
            "severity": issue.get("_severity", "medium"),
            "category": issue.get("detector_name", "unknown"),
            "file": file_path,
            "line": line,
            "function": first_instance.get("contract_path"),
            "confidence": 0.7,  # Aderyn doesn't provide confidence
            "raw": issue,
        }
