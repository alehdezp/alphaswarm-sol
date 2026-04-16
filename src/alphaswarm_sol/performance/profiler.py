"""Phase 19: Build Pipeline Profiler.

This module provides profiling functionality for the VKG build pipeline,
identifying performance bottlenecks and generating optimization reports.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar
from functools import wraps


class BuildPhase(str, Enum):
    """Phases of the build pipeline."""
    SLITHER_PARSE = "slither_parse"
    NODE_CREATION = "node_creation"
    EDGE_CREATION = "edge_creation"
    PROPERTY_DETECTION = "property_detection"
    SEMANTIC_OPS = "semantic_ops"
    HEURISTICS = "heuristics"
    GRAPH_EXPORT = "graph_export"


@dataclass
class TimingEntry:
    """Timing information for a profiled operation.

    Attributes:
        name: Operation name
        phase: Build phase
        start_time: Start timestamp
        end_time: End timestamp
        duration_ms: Duration in milliseconds
        count: Number of items processed
        metadata: Additional context
    """
    name: str
    phase: BuildPhase
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "phase": self.phase.value,
            "duration_ms": round(self.duration_ms, 2),
            "count": self.count,
            "metadata": self.metadata,
        }


@dataclass
class ProfileResult:
    """Result of profiling a build.

    Attributes:
        total_time_ms: Total build time in milliseconds
        phase_times: Time per phase
        bottlenecks: Identified bottlenecks
        recommendations: Optimization recommendations
        timings: Detailed timing entries
    """
    total_time_ms: float = 0.0
    phase_times: Dict[str, float] = field(default_factory=dict)
    bottlenecks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timings: List[TimingEntry] = field(default_factory=list)

    @property
    def slowest_phase(self) -> Optional[str]:
        """Get the slowest phase."""
        if not self.phase_times:
            return None
        return max(self.phase_times, key=self.phase_times.get)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_time_ms": round(self.total_time_ms, 2),
            "phase_times": {k: round(v, 2) for k, v in self.phase_times.items()},
            "bottlenecks": self.bottlenecks,
            "recommendations": self.recommendations,
            "timings": [t.to_dict() for t in self.timings],
        }

    def to_report(self) -> str:
        """Generate human-readable report."""
        lines = ["=== Build Profile Report ===", ""]

        # Total time
        lines.append(f"Total Time: {self.total_time_ms:.2f}ms")
        lines.append("")

        # Phase breakdown
        lines.append("Phase Breakdown:")
        sorted_phases = sorted(
            self.phase_times.items(),
            key=lambda x: x[1],
            reverse=True
        )
        for phase, time_ms in sorted_phases:
            pct = (time_ms / self.total_time_ms * 100) if self.total_time_ms > 0 else 0
            lines.append(f"  {phase}: {time_ms:.2f}ms ({pct:.1f}%)")
        lines.append("")

        # Bottlenecks
        if self.bottlenecks:
            lines.append("Bottlenecks:")
            for bottleneck in self.bottlenecks:
                lines.append(f"  - {bottleneck}")
            lines.append("")

        # Recommendations
        if self.recommendations:
            lines.append("Recommendations:")
            for rec in self.recommendations:
                lines.append(f"  - {rec}")

        return "\n".join(lines)


class BuildProfiler:
    """Profiles the VKG build pipeline.

    Tracks timing information for each phase and identifies bottlenecks.
    """

    # Thresholds for bottleneck detection (ms)
    BOTTLENECK_THRESHOLDS = {
        BuildPhase.SLITHER_PARSE: 5000,       # 5s for slither
        BuildPhase.NODE_CREATION: 100,        # 100ms for nodes
        BuildPhase.EDGE_CREATION: 100,        # 100ms for edges
        BuildPhase.PROPERTY_DETECTION: 500,   # 500ms for properties
        BuildPhase.SEMANTIC_OPS: 200,         # 200ms for semantic ops
        BuildPhase.HEURISTICS: 100,           # 100ms for heuristics
        BuildPhase.GRAPH_EXPORT: 50,          # 50ms for export
    }

    def __init__(self):
        """Initialize profiler."""
        self._timings: List[TimingEntry] = []
        self._active_entries: Dict[str, TimingEntry] = {}
        self._start_time: float = 0.0

    def start_build(self) -> None:
        """Start profiling a build."""
        self._timings = []
        self._active_entries = {}
        self._start_time = time.perf_counter()

    def start_phase(
        self,
        name: str,
        phase: BuildPhase,
        count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Start timing a phase.

        Args:
            name: Operation name
            phase: Build phase
            count: Number of items being processed
            metadata: Additional context
        """
        entry = TimingEntry(
            name=name,
            phase=phase,
            start_time=time.perf_counter(),
            count=count,
            metadata=metadata or {},
        )
        self._active_entries[name] = entry

    def end_phase(self, name: str) -> Optional[TimingEntry]:
        """End timing a phase.

        Args:
            name: Operation name

        Returns:
            Completed timing entry
        """
        entry = self._active_entries.pop(name, None)
        if entry:
            entry.end_time = time.perf_counter()
            entry.duration_ms = (entry.end_time - entry.start_time) * 1000
            self._timings.append(entry)
            return entry
        return None

    def record(
        self,
        name: str,
        phase: BuildPhase,
        duration_ms: float,
        count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TimingEntry:
        """Record a timing directly.

        Args:
            name: Operation name
            phase: Build phase
            duration_ms: Duration in milliseconds
            count: Number of items processed
            metadata: Additional context

        Returns:
            Recorded timing entry
        """
        entry = TimingEntry(
            name=name,
            phase=phase,
            duration_ms=duration_ms,
            count=count,
            metadata=metadata or {},
        )
        self._timings.append(entry)
        return entry

    def get_result(self) -> ProfileResult:
        """Get profiling result.

        Returns:
            ProfileResult with analysis
        """
        total_time = (time.perf_counter() - self._start_time) * 1000

        # Aggregate phase times
        phase_times: Dict[str, float] = {}
        for entry in self._timings:
            phase = entry.phase.value
            phase_times[phase] = phase_times.get(phase, 0.0) + entry.duration_ms

        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks()

        # Generate recommendations
        recommendations = self._generate_recommendations(bottlenecks)

        return ProfileResult(
            total_time_ms=total_time,
            phase_times=phase_times,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            timings=self._timings,
        )

    def _identify_bottlenecks(self) -> List[str]:
        """Identify performance bottlenecks."""
        bottlenecks: List[str] = []

        # Check phase thresholds
        phase_totals: Dict[BuildPhase, float] = {}
        for entry in self._timings:
            phase_totals[entry.phase] = (
                phase_totals.get(entry.phase, 0.0) + entry.duration_ms
            )

        for phase, total_ms in phase_totals.items():
            threshold = self.BOTTLENECK_THRESHOLDS.get(phase, 100)
            if total_ms > threshold:
                bottlenecks.append(
                    f"{phase.value}: {total_ms:.2f}ms (threshold: {threshold}ms)"
                )

        # Check for slow individual operations
        for entry in self._timings:
            if entry.count > 0 and entry.duration_ms > 0:
                per_item = entry.duration_ms / entry.count
                if per_item > 10:  # > 10ms per item
                    bottlenecks.append(
                        f"{entry.name}: {per_item:.2f}ms/item ({entry.count} items)"
                    )

        return bottlenecks

    def _generate_recommendations(self, bottlenecks: List[str]) -> List[str]:
        """Generate optimization recommendations."""
        recommendations: List[str] = []

        for bottleneck in bottlenecks:
            if "slither_parse" in bottleneck:
                recommendations.append(
                    "Consider caching Slither output for unchanged contracts"
                )
            elif "property_detection" in bottleneck:
                recommendations.append(
                    "Enable parallel property detection for large contracts"
                )
            elif "semantic_ops" in bottleneck:
                recommendations.append(
                    "Consider lazy evaluation of semantic operations"
                )
            elif "ms/item" in bottleneck:
                recommendations.append(
                    "Consider batching small operations for better throughput"
                )

        if not recommendations and bottlenecks:
            recommendations.append(
                "Review bottleneck phases for optimization opportunities"
            )

        return recommendations


# Type variable for decorated functions
F = TypeVar('F', bound=Callable[..., Any])


def timed(phase: BuildPhase, name: Optional[str] = None) -> Callable[[F], F]:
    """Decorator to time a function.

    Args:
        phase: Build phase this function belongs to
        name: Operation name (defaults to function name)

    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            op_name = name or func.__name__
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = (time.perf_counter() - start) * 1000
                # Store timing in function attribute for retrieval
                if not hasattr(wrapper, '_timings'):
                    wrapper._timings = []  # type: ignore
                wrapper._timings.append({  # type: ignore
                    'name': op_name,
                    'phase': phase,
                    'duration_ms': duration,
                })
        return wrapper  # type: ignore
    return decorator


def profile_build(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to profile an entire build function.

    Wraps the function and returns (result, profile_result) tuple.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        profiler = BuildProfiler()
        profiler.start_build()

        # Inject profiler into kwargs if function accepts it
        if 'profiler' in func.__code__.co_varnames:
            kwargs['profiler'] = profiler

        result = func(*args, **kwargs)

        profile_result = profiler.get_result()
        return result, profile_result

    return wrapper


__all__ = [
    "BuildPhase",
    "TimingEntry",
    "ProfileResult",
    "BuildProfiler",
    "timed",
    "profile_build",
]
