"""Trajectory evaluation for agent quality assessment."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class StepType(Enum):
    """Types of steps in an agent trajectory."""

    REASONING = "reasoning"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    DECISION = "decision"
    ERROR = "error"
    RECOVERY = "recovery"
    CHECKPOINT = "checkpoint"


@dataclass
class TrajectoryStep:
    """A single step in an agent trajectory."""

    step_number: int
    step_type: StepType
    timestamp: datetime
    content: str
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    duration_ms: int = 0
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Trajectory:
    """Complete trajectory of an agent execution."""

    agent_id: str
    agent_type: str
    task_description: str
    start_time: datetime
    end_time: datetime | None = None
    steps: list[TrajectoryStep] = field(default_factory=list)
    final_result: Any = None
    success: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_duration_ms(self) -> int:
        """Total execution duration in milliseconds."""
        if not self.end_time:
            return 0
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() * 1000)

    @property
    def tool_call_count(self) -> int:
        return sum(1 for s in self.steps if s.step_type == StepType.TOOL_CALL)

    @property
    def error_count(self) -> int:
        return sum(1 for s in self.steps if s.step_type == StepType.ERROR)

    @property
    def recovery_count(self) -> int:
        return sum(1 for s in self.steps if s.step_type == StepType.RECOVERY)


@dataclass
class TrajectoryMetrics:
    """Metrics derived from trajectory evaluation."""

    # Efficiency metrics
    step_efficiency: float  # Ratio of productive steps to total
    tool_efficiency: float  # Ratio of successful tool calls
    time_efficiency: float  # Actual vs expected duration

    # Quality metrics
    tool_appropriateness: float  # Right tools for the task
    reasoning_coherence: float  # Logical flow score
    error_recovery_rate: float  # Recovery success rate

    # Problem metrics
    dead_end_ratio: float  # Unproductive exploration
    redundancy_ratio: float  # Repeated actions

    # Overall
    overall_score: float

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "step_efficiency": self.step_efficiency,
            "tool_efficiency": self.tool_efficiency,
            "time_efficiency": self.time_efficiency,
            "tool_appropriateness": self.tool_appropriateness,
            "reasoning_coherence": self.reasoning_coherence,
            "error_recovery_rate": self.error_recovery_rate,
            "dead_end_ratio": self.dead_end_ratio,
            "redundancy_ratio": self.redundancy_ratio,
            "overall_score": self.overall_score,
        }


class TrajectoryEvaluator:
    """
    Evaluates agent trajectories for quality assessment.

    Goes beyond final answers to analyze HOW agents reach conclusions.
    Based on research from arXiv 2510.02837.
    """

    def __init__(
        self,
        expected_tools: list[str] | None = None,
        expected_duration_ms: int | None = None,
        optimal_step_count: int | None = None,
    ):
        self.expected_tools = expected_tools or []
        self.expected_duration_ms = expected_duration_ms
        self.optimal_step_count = optimal_step_count

    def evaluate(self, trajectory: Trajectory) -> TrajectoryMetrics:
        """Evaluate a trajectory and return metrics."""
        return TrajectoryMetrics(
            step_efficiency=self._calculate_step_efficiency(trajectory),
            tool_efficiency=self._calculate_tool_efficiency(trajectory),
            time_efficiency=self._calculate_time_efficiency(trajectory),
            tool_appropriateness=self._calculate_tool_appropriateness(trajectory),
            reasoning_coherence=self._calculate_reasoning_coherence(trajectory),
            error_recovery_rate=self._calculate_error_recovery_rate(trajectory),
            dead_end_ratio=self._calculate_dead_end_ratio(trajectory),
            redundancy_ratio=self._calculate_redundancy_ratio(trajectory),
            overall_score=self._calculate_overall_score(trajectory),
        )

    def _calculate_step_efficiency(self, trajectory: Trajectory) -> float:
        """Calculate ratio of productive steps to total steps."""
        if not trajectory.steps:
            return 0.0

        productive_types = {
            StepType.TOOL_CALL,
            StepType.DECISION,
            StepType.CHECKPOINT,
            StepType.RECOVERY,
        }

        productive = sum(
            1
            for s in trajectory.steps
            if s.step_type in productive_types and s.success
        )

        return productive / len(trajectory.steps)

    def _calculate_tool_efficiency(self, trajectory: Trajectory) -> float:
        """Calculate ratio of successful tool calls."""
        tool_calls = [s for s in trajectory.steps if s.step_type == StepType.TOOL_CALL]
        if not tool_calls:
            return 1.0

        successful = sum(1 for s in tool_calls if s.success)
        return successful / len(tool_calls)

    def _calculate_time_efficiency(self, trajectory: Trajectory) -> float:
        """Calculate time efficiency vs expected duration."""
        if not self.expected_duration_ms or not trajectory.total_duration_ms:
            return 1.0

        # Score decreases if took longer than expected
        ratio = self.expected_duration_ms / trajectory.total_duration_ms
        return min(ratio, 1.0)

    def _calculate_tool_appropriateness(self, trajectory: Trajectory) -> float:
        """Calculate how appropriate tool choices were."""
        if not self.expected_tools:
            return 1.0

        used_tools = {
            s.tool_name
            for s in trajectory.steps
            if s.step_type == StepType.TOOL_CALL and s.tool_name
        }

        expected_set = set(self.expected_tools)

        # Penalize missing expected tools and using unexpected tools
        missing = len(expected_set - used_tools)
        extra = len(used_tools - expected_set)

        total_expected = len(expected_set)
        if total_expected == 0:
            return 1.0

        score = max(0, total_expected - missing - (extra * 0.5)) / total_expected
        return score

    def _calculate_reasoning_coherence(self, trajectory: Trajectory) -> float:
        """Calculate logical coherence of reasoning steps."""
        reasoning_steps = [
            s for s in trajectory.steps if s.step_type == StepType.REASONING
        ]

        if len(reasoning_steps) < 2:
            return 1.0

        # Simple heuristic: check for logical progression
        # (In a real implementation, could use LLM to evaluate)
        coherent_count = 0
        for i in range(1, len(reasoning_steps)):
            prev = reasoning_steps[i - 1].content.lower()
            curr = reasoning_steps[i].content.lower()

            # Check for logical connectors or references
            connectors = ["therefore", "because", "since", "thus", "next", "then"]
            if any(c in curr for c in connectors):
                coherent_count += 1

        return (
            coherent_count / (len(reasoning_steps) - 1)
            if len(reasoning_steps) > 1
            else 1.0
        )

    def _calculate_error_recovery_rate(self, trajectory: Trajectory) -> float:
        """Calculate rate of successful error recovery."""
        errors = sum(1 for s in trajectory.steps if s.step_type == StepType.ERROR)
        recoveries = sum(1 for s in trajectory.steps if s.step_type == StepType.RECOVERY)

        if errors == 0:
            return 1.0

        return min(recoveries / errors, 1.0)

    def _calculate_dead_end_ratio(self, trajectory: Trajectory) -> float:
        """Calculate ratio of dead-end explorations."""
        if not trajectory.steps:
            return 0.0

        # Detect dead ends: errors without recovery, or abandoned paths
        dead_ends = 0
        for i, step in enumerate(trajectory.steps):
            if step.step_type == StepType.ERROR:
                # Check if next step is not a recovery
                if i + 1 < len(trajectory.steps):
                    next_step = trajectory.steps[i + 1]
                    if next_step.step_type != StepType.RECOVERY:
                        dead_ends += 1
                else:
                    dead_ends += 1

        return dead_ends / len(trajectory.steps)

    def _calculate_redundancy_ratio(self, trajectory: Trajectory) -> float:
        """Calculate ratio of redundant/repeated actions."""
        if not trajectory.steps:
            return 0.0

        tool_calls = [
            (s.tool_name, str(s.tool_args))
            for s in trajectory.steps
            if s.step_type == StepType.TOOL_CALL
        ]

        if len(tool_calls) < 2:
            return 0.0

        unique_calls = len(set(tool_calls))
        redundant = len(tool_calls) - unique_calls

        return redundant / len(tool_calls)

    def _calculate_overall_score(self, trajectory: Trajectory) -> float:
        """Calculate weighted overall score."""
        weights = {
            "step_efficiency": 0.15,
            "tool_efficiency": 0.15,
            "time_efficiency": 0.10,
            "tool_appropriateness": 0.15,
            "reasoning_coherence": 0.15,
            "error_recovery_rate": 0.15,
            "dead_end_ratio": 0.075,  # Negative impact
            "redundancy_ratio": 0.075,  # Negative impact
        }

        scores = {
            "step_efficiency": self._calculate_step_efficiency(trajectory),
            "tool_efficiency": self._calculate_tool_efficiency(trajectory),
            "time_efficiency": self._calculate_time_efficiency(trajectory),
            "tool_appropriateness": self._calculate_tool_appropriateness(trajectory),
            "reasoning_coherence": self._calculate_reasoning_coherence(trajectory),
            "error_recovery_rate": self._calculate_error_recovery_rate(trajectory),
            "dead_end_ratio": 1.0 - self._calculate_dead_end_ratio(trajectory),
            "redundancy_ratio": 1.0 - self._calculate_redundancy_ratio(trajectory),
        }

        return sum(scores[k] * weights[k] for k in weights)
