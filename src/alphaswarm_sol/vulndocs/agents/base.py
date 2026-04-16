"""Base Agent Classes for Multi-Model Pipeline.

Task 18.2: Base infrastructure for Haiku workers and Opus orchestrators.

The agent system uses:
- Haiku: Fast, cheap workers for bulk processing (crawling, summarization)
- Opus: Intelligent orchestrators for decision making (merging, conflict resolution)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

logger = logging.getLogger(__name__)


class AgentModel(Enum):
    """Model types for agents."""

    HAIKU = "haiku"
    # Fast, cheap - use for bulk processing
    # Good for: crawling, summarization, extraction, classification

    OPUS = "opus"
    # Intelligent, expensive - use for decision making
    # Good for: merging, conflict resolution, quality assessment, linking

    SONNET = "sonnet"
    # Balanced - use for medium complexity tasks
    # Good for: validation, moderate reasoning

    @classmethod
    def from_string(cls, value: str) -> "AgentModel":
        """Parse model from string."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.HAIKU  # Default to cheapest


class AgentStatus(Enum):
    """Status of an agent task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    model: AgentModel = AgentModel.HAIKU
    max_retries: int = 3
    timeout_seconds: int = 60
    temperature: float = 0.1
    max_tokens: int = 4096

    # Parallelism settings
    max_concurrent: int = 10
    batch_size: int = 5

    # Rate limiting
    rate_limit_per_minute: int = 60
    delay_between_calls: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "model": self.model.value,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "max_concurrent": self.max_concurrent,
            "batch_size": self.batch_size,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "delay_between_calls": self.delay_between_calls,
        }

    @classmethod
    def for_haiku_worker(cls) -> "AgentConfig":
        """Get default config for Haiku workers."""
        return cls(
            model=AgentModel.HAIKU,
            max_concurrent=50,
            batch_size=10,
            temperature=0.0,
            max_tokens=2048,
        )

    @classmethod
    def for_opus_orchestrator(cls) -> "AgentConfig":
        """Get default config for Opus orchestrators."""
        return cls(
            model=AgentModel.OPUS,
            max_concurrent=15,
            batch_size=3,
            temperature=0.1,
            max_tokens=8192,
        )


T = TypeVar("T")


@dataclass
class AgentResult(Generic[T]):
    """Result of an agent task."""

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    status: AgentStatus = AgentStatus.COMPLETED

    # Metrics
    processing_time_ms: int = 0
    tokens_used: int = 0
    retries: int = 0

    # Tracking
    task_id: str = ""
    timestamp: str = ""

    def __post_init__(self):
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if not self.task_id:
            self.task_id = hashlib.md5(
                f"{self.timestamp}{id(self)}".encode()
            ).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "data": self.data if isinstance(self.data, dict) else str(self.data),
            "error": self.error,
            "status": self.status.value,
            "processing_time_ms": self.processing_time_ms,
            "tokens_used": self.tokens_used,
            "retries": self.retries,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def success_result(cls, data: T, **kwargs) -> "AgentResult[T]":
        """Create a successful result."""
        return cls(success=True, data=data, status=AgentStatus.COMPLETED, **kwargs)

    @classmethod
    def failure_result(cls, error: str, **kwargs) -> "AgentResult[T]":
        """Create a failure result."""
        return cls(success=False, error=error, status=AgentStatus.FAILED, **kwargs)


@dataclass
class TaskProgress:
    """Progress tracking for agent tasks."""

    total: int = 0
    completed: int = 0
    failed: int = 0
    in_progress: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def progress_pct(self) -> float:
        """Get progress percentage."""
        if self.total == 0:
            return 0.0
        return (self.completed + self.failed) / self.total * 100

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.utcnow()
        return (end - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "in_progress": self.in_progress,
            "progress_pct": self.progress_pct,
            "elapsed_seconds": self.elapsed_seconds,
        }


class BaseAgent(ABC):
    """Base class for all agents in the multi-model pipeline.

    Agents are the building blocks of the knowledge processing pipeline.
    They handle specific tasks like crawling, summarization, or merging.
    """

    def __init__(
        self,
        name: str,
        config: Optional[AgentConfig] = None,
    ):
        """Initialize the agent.

        Args:
            name: Agent identifier
            config: Agent configuration
        """
        self.name = name
        self.config = config or AgentConfig()
        self.progress = TaskProgress()
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._callbacks: List[Callable[[TaskProgress], None]] = []

    @property
    def model(self) -> AgentModel:
        """Get the model this agent uses."""
        return self.config.model

    @property
    def is_haiku(self) -> bool:
        """Check if this is a Haiku agent."""
        return self.config.model == AgentModel.HAIKU

    @property
    def is_opus(self) -> bool:
        """Check if this is an Opus agent."""
        return self.config.model == AgentModel.OPUS

    def add_progress_callback(self, callback: Callable[[TaskProgress], None]) -> None:
        """Add a callback for progress updates.

        Args:
            callback: Function to call with progress updates
        """
        self._callbacks.append(callback)

    def _notify_progress(self) -> None:
        """Notify all callbacks of progress update."""
        for callback in self._callbacks:
            try:
                callback(self.progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    async def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create the concurrency semaphore."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        return self._semaphore

    @abstractmethod
    async def process(self, input_data: Any) -> AgentResult:
        """Process input data.

        Args:
            input_data: Data to process

        Returns:
            Processing result
        """
        pass

    async def process_batch(self, items: List[Any]) -> List[AgentResult]:
        """Process multiple items in parallel.

        Args:
            items: List of items to process

        Returns:
            List of results
        """
        self.progress = TaskProgress(
            total=len(items),
            start_time=datetime.utcnow(),
        )
        self._notify_progress()

        semaphore = await self._get_semaphore()
        results = []

        async def process_with_semaphore(item: Any) -> AgentResult:
            async with semaphore:
                self.progress.in_progress += 1
                self._notify_progress()

                try:
                    result = await self.process(item)
                    if result.success:
                        self.progress.completed += 1
                    else:
                        self.progress.failed += 1
                except Exception as e:
                    result = AgentResult.failure_result(str(e))
                    self.progress.failed += 1
                finally:
                    self.progress.in_progress -= 1
                    self._notify_progress()

                # Rate limiting
                if self.config.delay_between_calls > 0:
                    await asyncio.sleep(self.config.delay_between_calls)

                return result

        tasks = [process_with_semaphore(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failure results
        processed_results = []
        for r in results:
            if isinstance(r, Exception):
                processed_results.append(AgentResult.failure_result(str(r)))
            else:
                processed_results.append(r)

        self.progress.end_time = datetime.utcnow()
        self._notify_progress()

        return processed_results

    def get_prompt_template(self, template_name: str) -> str:
        """Get a prompt template for this agent.

        Args:
            template_name: Name of the template

        Returns:
            Template string

        Subclasses should override to provide custom templates.
        """
        return ""

    def log(self, message: str, level: str = "info") -> None:
        """Log a message with agent context.

        Args:
            message: Message to log
            level: Log level (debug, info, warning, error)
        """
        log_fn = getattr(logger, level, logger.info)
        log_fn(f"[{self.name}] {message}")


@dataclass
class SubagentTask:
    """A task to be executed by a subagent."""

    task_id: str
    agent_name: str
    input_data: Any
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.PENDING
    result: Optional[AgentResult] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result.to_dict() if self.result else None,
        }


class SubagentCoordinator:
    """Coordinates multiple subagents for parallel processing.

    Used by CategoryAgents to spawn SubcategoryWorkers.
    """

    def __init__(self, max_concurrent: int = 10):
        """Initialize the coordinator.

        Args:
            max_concurrent: Maximum concurrent subagents
        """
        self.max_concurrent = max_concurrent
        self.agents: Dict[str, BaseAgent] = {}
        self.tasks: Dict[str, SubagentTask] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a subagent.

        Args:
            agent: Agent to register
        """
        self.agents[agent.name] = agent

    def add_task(self, task: SubagentTask) -> None:
        """Add a task to the queue.

        Args:
            task: Task to add
        """
        self.tasks[task.task_id] = task

    async def execute_all(self) -> Dict[str, AgentResult]:
        """Execute all pending tasks.

        Returns:
            Dictionary of task_id -> result
        """
        results: Dict[str, AgentResult] = {}

        # Sort by priority (higher first) and dependency order
        sorted_tasks = sorted(
            self.tasks.values(),
            key=lambda t: (-t.priority, len(t.dependencies)),
        )

        async def execute_task(task: SubagentTask) -> None:
            # Wait for dependencies
            for dep_id in task.dependencies:
                while dep_id not in results:
                    await asyncio.sleep(0.1)

            async with self._semaphore:
                task.status = AgentStatus.RUNNING
                agent = self.agents.get(task.agent_name)

                if agent is None:
                    task.result = AgentResult.failure_result(
                        f"Agent {task.agent_name} not found"
                    )
                else:
                    try:
                        task.result = await agent.process(task.input_data)
                    except Exception as e:
                        task.result = AgentResult.failure_result(str(e))

                task.status = (
                    AgentStatus.COMPLETED if task.result.success else AgentStatus.FAILED
                )
                results[task.task_id] = task.result

        await asyncio.gather(*[execute_task(t) for t in sorted_tasks])
        return results

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress across all tasks.

        Returns:
            Progress summary
        """
        statuses = [t.status for t in self.tasks.values()]
        return {
            "total": len(statuses),
            "pending": statuses.count(AgentStatus.PENDING),
            "running": statuses.count(AgentStatus.RUNNING),
            "completed": statuses.count(AgentStatus.COMPLETED),
            "failed": statuses.count(AgentStatus.FAILED),
        }
