"""Ranking Data Structures for Model Selection.

This module provides data classes for the model ranking system:
- TaskProfile: Defines task requirements for model selection
- ModelRanking: Tracks model performance per task type
- TaskFeedback: Captures execution feedback for ranking updates

Per 05.3-CONTEXT.md:
- Rankings update via EMA after each execution
- Rankings stored persistently in .vrs/rankings/rankings.yaml
- Selector uses rankings to choose best model per task type

Usage:
    from alphaswarm_sol.agents.ranking.schemas import (
        TaskProfile,
        ModelRanking,
        TaskFeedback,
    )

    # Define task profile for model selection
    profile = TaskProfile(
        task_type=TaskType.VERIFY,
        complexity="simple",
        context_size=5000,
        requires_tools=False,
    )

    # Create ranking entry
    ranking = ModelRanking(
        model_id="minimax/minimax-m2:free",
        task_type="verify",
        success_rate=0.95,
        average_latency_ms=1200,
        average_tokens=500,
        quality_score=0.88,
        cost_per_task=0.0,
        sample_count=25,
    )

    # Record feedback
    feedback = TaskFeedback(
        task_id="task-123",
        model_id="minimax/minimax-m2:free",
        task_type="verify",
        success=True,
        latency_ms=980,
        tokens_used=450,
        quality_score=0.9,
        cost_usd=0.0,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from alphaswarm_sol.agents.runtime.types import TaskType


# =============================================================================
# Complexity Levels
# =============================================================================

class Complexity:
    """Task complexity levels for model selection."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"

    @classmethod
    def values(cls) -> list[str]:
        """Get all valid complexity values."""
        return [cls.SIMPLE, cls.MODERATE, cls.COMPLEX]

    @classmethod
    def validate(cls, value: str) -> bool:
        """Check if a value is a valid complexity level."""
        return value in cls.values()


# =============================================================================
# Task Profile
# =============================================================================

@dataclass
class TaskProfile:
    """Profile defining task requirements for model selection.

    Used by ModelSelector to find the best model for a task based on
    requirements and constraints.

    Attributes:
        task_type: The type of task (VERIFY, CODE, REASONING, etc.)
        complexity: Task complexity level (simple, moderate, complex)
        context_size: Required context window size in tokens
        output_size: Expected output size in tokens
        requires_tools: Whether the task needs tool use capability
        latency_sensitive: Whether fast response is important
        accuracy_critical: Whether quality/accuracy matters most

    Examples:
        # Simple verification task
        profile = TaskProfile(
            task_type=TaskType.VERIFY,
            complexity="simple",
            context_size=2000,
            output_size=500,
            requires_tools=False,
            latency_sensitive=True,
            accuracy_critical=False,
        )

        # Complex reasoning task
        profile = TaskProfile(
            task_type=TaskType.REASONING_HEAVY,
            complexity="complex",
            context_size=50000,
            output_size=5000,
            requires_tools=True,
            latency_sensitive=False,
            accuracy_critical=True,
        )
    """

    task_type: TaskType
    complexity: str = Complexity.MODERATE
    context_size: int = 0
    output_size: int = 0
    requires_tools: bool = False
    latency_sensitive: bool = False
    accuracy_critical: bool = False

    def __post_init__(self):
        """Validate complexity value."""
        if not Complexity.validate(self.complexity):
            raise ValueError(
                f"Invalid complexity '{self.complexity}'. "
                f"Must be one of: {Complexity.values()}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for serialization.

        Returns:
            Dictionary representation of the profile
        """
        return {
            "task_type": self.task_type.value,
            "complexity": self.complexity,
            "context_size": self.context_size,
            "output_size": self.output_size,
            "requires_tools": self.requires_tools,
            "latency_sensitive": self.latency_sensitive,
            "accuracy_critical": self.accuracy_critical,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskProfile":
        """Create TaskProfile from dictionary.

        Args:
            data: Dictionary with profile data

        Returns:
            TaskProfile instance
        """
        task_type_str = data.get("task_type", "analyze")
        task_type = TaskType(task_type_str) if isinstance(task_type_str, str) else task_type_str

        return cls(
            task_type=task_type,
            complexity=data.get("complexity", Complexity.MODERATE),
            context_size=data.get("context_size", 0),
            output_size=data.get("output_size", 0),
            requires_tools=data.get("requires_tools", False),
            latency_sensitive=data.get("latency_sensitive", False),
            accuracy_critical=data.get("accuracy_critical", False),
        )


# =============================================================================
# Model Ranking
# =============================================================================

@dataclass
class ModelRanking:
    """Track model performance per task type.

    Rankings are updated via EMA (exponential moving average) after each
    execution, with recent feedback weighted more heavily.

    Attributes:
        model_id: Model identifier (e.g., "minimax/minimax-m2:free")
        task_type: Task type this ranking applies to (e.g., "verify")
        success_rate: Success rate 0.0-1.0 (EMA-weighted)
        average_latency_ms: Average latency in milliseconds (EMA-weighted)
        average_tokens: Average tokens used per task (EMA-weighted)
        quality_score: Quality score 0.0-1.0 (EMA-weighted)
        cost_per_task: Average cost in USD per task (EMA-weighted)
        sample_count: Number of executions in ranking history
        last_updated: Timestamp of last update

    Examples:
        # Create new ranking
        ranking = ModelRanking(
            model_id="deepseek/deepseek-v3.2",
            task_type="reasoning",
            success_rate=0.92,
            average_latency_ms=2500,
            average_tokens=3000,
            quality_score=0.85,
            cost_per_task=0.0012,
            sample_count=50,
        )

        # Convert to YAML-friendly dict
        data = ranking.to_dict()
    """

    model_id: str
    task_type: str
    success_rate: float = 0.0
    average_latency_ms: int = 0
    average_tokens: int = 0
    quality_score: float = 0.0
    cost_per_task: float = 0.0
    sample_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate ranking values."""
        if not 0.0 <= self.success_rate <= 1.0:
            raise ValueError(f"success_rate must be 0.0-1.0, got {self.success_rate}")
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError(f"quality_score must be 0.0-1.0, got {self.quality_score}")
        if self.average_latency_ms < 0:
            raise ValueError(f"average_latency_ms must be >= 0, got {self.average_latency_ms}")
        if self.average_tokens < 0:
            raise ValueError(f"average_tokens must be >= 0, got {self.average_tokens}")
        if self.cost_per_task < 0:
            raise ValueError(f"cost_per_task must be >= 0, got {self.cost_per_task}")
        if self.sample_count < 0:
            raise ValueError(f"sample_count must be >= 0, got {self.sample_count}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert ranking to dictionary for YAML serialization.

        Returns:
            Dictionary representation suitable for YAML storage
        """
        return {
            "model_id": self.model_id,
            "task_type": self.task_type,
            "success_rate": round(self.success_rate, 4),
            "average_latency_ms": self.average_latency_ms,
            "average_tokens": self.average_tokens,
            "quality_score": round(self.quality_score, 4),
            "cost_per_task": round(self.cost_per_task, 6),
            "sample_count": self.sample_count,
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelRanking":
        """Create ModelRanking from dictionary.

        Args:
            data: Dictionary with ranking data (from YAML)

        Returns:
            ModelRanking instance
        """
        last_updated = data.get("last_updated")
        if isinstance(last_updated, str):
            # Parse ISO format timestamp
            last_updated = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        elif last_updated is None:
            last_updated = datetime.utcnow()

        return cls(
            model_id=data["model_id"],
            task_type=data["task_type"],
            success_rate=float(data.get("success_rate", 0.0)),
            average_latency_ms=int(data.get("average_latency_ms", 0)),
            average_tokens=int(data.get("average_tokens", 0)),
            quality_score=float(data.get("quality_score", 0.0)),
            cost_per_task=float(data.get("cost_per_task", 0.0)),
            sample_count=int(data.get("sample_count", 0)),
            last_updated=last_updated,
        )

    def score(
        self,
        weight_quality: float = 0.4,
        weight_latency: float = 0.2,
        weight_cost: float = 0.3,
        weight_success: float = 0.1,
        max_latency_ms: int = 10000,
        max_cost: float = 0.01,
    ) -> float:
        """Calculate composite score for ranking comparison.

        Higher score = better model for the task.

        Args:
            weight_quality: Weight for quality score (0.0-1.0)
            weight_latency: Weight for latency (0.0-1.0)
            weight_cost: Weight for cost (0.0-1.0)
            weight_success: Weight for success rate (0.0-1.0)
            max_latency_ms: Maximum latency for normalization
            max_cost: Maximum cost for normalization

        Returns:
            Composite score 0.0-1.0 (higher is better)
        """
        # Normalize latency (lower is better, so invert)
        latency_score = 1.0 - min(self.average_latency_ms / max_latency_ms, 1.0)

        # Normalize cost (lower is better, so invert)
        cost_score = 1.0 - min(self.cost_per_task / max_cost, 1.0) if max_cost > 0 else 1.0

        # Composite score
        return (
            weight_quality * self.quality_score
            + weight_latency * latency_score
            + weight_cost * cost_score
            + weight_success * self.success_rate
        )


# =============================================================================
# Task Feedback
# =============================================================================

@dataclass
class TaskFeedback:
    """Feedback from task execution for ranking updates.

    Collected after each task execution to update model rankings via EMA.

    Attributes:
        task_id: Unique identifier for the task execution
        model_id: Model used for execution
        task_type: Type of task performed
        success: Whether the task completed successfully
        latency_ms: Execution latency in milliseconds
        tokens_used: Total tokens used (input + output)
        quality_score: Quality score 0.0-1.0 (from verification)
        cost_usd: Actual cost in USD
        timestamp: When the task was executed
        error_message: Error message if task failed

    Examples:
        # Successful execution
        feedback = TaskFeedback(
            task_id="verify-abc123",
            model_id="minimax/minimax-m2:free",
            task_type="verify",
            success=True,
            latency_ms=850,
            tokens_used=450,
            quality_score=0.92,
            cost_usd=0.0,
        )

        # Failed execution
        feedback = TaskFeedback(
            task_id="reason-xyz789",
            model_id="deepseek/deepseek-v3.2",
            task_type="reasoning",
            success=False,
            latency_ms=5000,
            tokens_used=0,
            quality_score=0.0,
            cost_usd=0.002,
            error_message="Context length exceeded",
        )
    """

    task_id: str
    model_id: str
    task_type: str
    success: bool
    latency_ms: int
    tokens_used: int
    quality_score: float
    cost_usd: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None

    def __post_init__(self):
        """Validate feedback values."""
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError(f"quality_score must be 0.0-1.0, got {self.quality_score}")
        if self.latency_ms < 0:
            raise ValueError(f"latency_ms must be >= 0, got {self.latency_ms}")
        if self.tokens_used < 0:
            raise ValueError(f"tokens_used must be >= 0, got {self.tokens_used}")
        if self.cost_usd < 0:
            raise ValueError(f"cost_usd must be >= 0, got {self.cost_usd}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert feedback to dictionary for storage/logging.

        Returns:
            Dictionary representation of the feedback
        """
        return {
            "task_id": self.task_id,
            "model_id": self.model_id,
            "task_type": self.task_type,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "tokens_used": self.tokens_used,
            "quality_score": round(self.quality_score, 4),
            "cost_usd": round(self.cost_usd, 6),
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskFeedback":
        """Create TaskFeedback from dictionary.

        Args:
            data: Dictionary with feedback data

        Returns:
            TaskFeedback instance
        """
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        elif timestamp is None:
            timestamp = datetime.utcnow()

        return cls(
            task_id=data["task_id"],
            model_id=data["model_id"],
            task_type=data["task_type"],
            success=data.get("success", False),
            latency_ms=int(data.get("latency_ms", 0)),
            tokens_used=int(data.get("tokens_used", 0)),
            quality_score=float(data.get("quality_score", 0.0)),
            cost_usd=float(data.get("cost_usd", 0.0)),
            timestamp=timestamp,
            error_message=data.get("error_message"),
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "Complexity",
    "TaskProfile",
    "ModelRanking",
    "TaskFeedback",
]
