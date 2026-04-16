"""
Result Aggregation

Combines results from multiple analysis sources, handling partial failures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SourceResult:
    """Result from a single analysis source."""

    source: str
    complete: bool
    findings: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    runtime_ms: int = 0
    retry_command: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "complete": self.complete,
            "finding_count": len(self.findings),
            "error": self.error,
            "runtime_ms": self.runtime_ms,
            "retry_command": self.retry_command,
            "metadata": self.metadata,
        }

    @property
    def ok(self) -> bool:
        """Alias for complete."""
        return self.complete

    @property
    def failed(self) -> bool:
        """True if this result represents a failure."""
        return not self.complete


@dataclass
class AggregatedResults:
    """Combined results from multiple sources."""

    sources: List[SourceResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def total_findings(self) -> int:
        """Total number of findings from all sources."""
        return sum(len(s.findings) for s in self.sources)

    @property
    def complete(self) -> bool:
        """True if all sources completed successfully."""
        return len(self.sources) > 0 and all(s.complete for s in self.sources)

    @property
    def incomplete_sources(self) -> List[str]:
        """List of sources that failed."""
        return [s.source for s in self.sources if not s.complete]

    @property
    def successful_sources(self) -> List[str]:
        """List of sources that completed successfully."""
        return [s.source for s in self.sources if s.complete]

    @property
    def partial(self) -> bool:
        """True if some but not all sources completed."""
        return len(self.sources) > 0 and not self.complete and len(self.successful_sources) > 0

    @property
    def total_sources(self) -> int:
        """Total number of sources."""
        return len(self.sources)

    @property
    def success_rate(self) -> float:
        """Percentage of sources that completed (0.0 to 1.0)."""
        if len(self.sources) == 0:
            return 0.0
        return len(self.successful_sources) / len(self.sources)

    def add_result(self, result: SourceResult) -> None:
        """Add a source result."""
        self.sources.append(result)

    def get_source(self, name: str) -> Optional[SourceResult]:
        """Get result for a specific source."""
        for s in self.sources:
            if s.source == name:
                return s
        return None

    def get_all_findings(self) -> List[Dict[str, Any]]:
        """Get all findings from all sources with source annotation."""
        findings = []
        for source in self.sources:
            for finding in source.findings:
                # Create a copy with source annotation
                annotated = dict(finding)
                annotated["_source"] = source.source
                findings.append(annotated)
        return findings

    def get_errors(self) -> List[Dict[str, str]]:
        """Get all errors from failed sources."""
        return [
            {"source": s.source, "error": s.error}
            for s in self.sources
            if not s.complete and s.error
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_findings": self.total_findings,
            "complete": self.complete,
            "partial": self.partial,
            "success_rate": self.success_rate,
            "incomplete_sources": self.incomplete_sources,
            "successful_sources": self.successful_sources,
            "sources": [s.to_dict() for s in self.sources],
            "timestamp": self.timestamp.isoformat(),
        }


class ResultAggregator:
    """Aggregates results from multiple analysis sources."""

    def __init__(self):
        self.results = AggregatedResults()

    def add_success(
        self,
        source: str,
        findings: List[Dict[str, Any]],
        runtime_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add successful result."""
        self.results.add_result(
            SourceResult(
                source=source,
                complete=True,
                findings=findings,
                runtime_ms=runtime_ms,
                metadata=metadata or {},
            )
        )

    def add_failure(
        self,
        source: str,
        error: str,
        partial_findings: Optional[List[Dict[str, Any]]] = None,
        retry_command: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add failed result."""
        self.results.add_result(
            SourceResult(
                source=source,
                complete=False,
                findings=partial_findings or [],
                error=error,
                retry_command=retry_command or f"vkg tools run {source}",
                metadata=metadata or {},
            )
        )

    def add_timeout(
        self,
        source: str,
        timeout_seconds: int,
        partial_findings: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add timeout result."""
        self.results.add_result(
            SourceResult(
                source=source,
                complete=False,
                findings=partial_findings or [],
                error=f"Timed out after {timeout_seconds}s",
                retry_command=f"vkg tools run {source} --timeout {timeout_seconds * 2}",
                metadata=metadata or {},
            )
        )

    def add_skipped(
        self,
        source: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add skipped source (tool not available)."""
        self.results.add_result(
            SourceResult(
                source=source,
                complete=False,
                findings=[],
                error=f"Skipped: {reason}",
                retry_command=None,  # Can't retry skipped tools
                metadata=metadata or {},
            )
        )

    def add_from_tool_result(self, source: str, tool_result: Any) -> None:
        """Add result from a ToolResult object.

        Expects tool_result to have: success, output, error, runtime_ms attributes.
        """
        if tool_result.success:
            # Try to parse findings from output
            findings = []
            if hasattr(tool_result, "findings"):
                findings = tool_result.findings
            elif tool_result.output:
                # Try JSON parse
                import json
                try:
                    data = json.loads(tool_result.output)
                    if isinstance(data, list):
                        findings = data
                    elif isinstance(data, dict) and "findings" in data:
                        findings = data["findings"]
                except json.JSONDecodeError:
                    pass

            self.add_success(
                source=source,
                findings=findings,
                runtime_ms=getattr(tool_result, "runtime_ms", 0),
            )
        else:
            if "timed out" in (tool_result.error or "").lower():
                self.add_timeout(source, 60)  # Default timeout
            else:
                self.add_failure(
                    source=source,
                    error=tool_result.error or "Unknown error",
                    retry_command=getattr(tool_result, "recovery", None),
                )

    def get_results(self) -> AggregatedResults:
        """Get aggregated results."""
        return self.results

    def reset(self) -> None:
        """Reset the aggregator."""
        self.results = AggregatedResults()
