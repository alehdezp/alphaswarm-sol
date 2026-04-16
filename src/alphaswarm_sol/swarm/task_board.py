"""
Task Board for Agent Swarm

A shared task queue that agents use to coordinate work.
Implements priority-based task distribution and claiming.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from enum import Enum
from datetime import datetime
import heapq
import threading
import logging

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0    # Must be done immediately
    HIGH = 1        # Important, do soon
    MEDIUM = 2      # Normal priority
    LOW = 3         # Can wait
    BACKGROUND = 4  # Do when nothing else


class TaskStatus(Enum):
    """Task status."""
    PENDING = "pending"           # Waiting to be claimed
    CLAIMED = "claimed"           # Agent is working on it
    IN_PROGRESS = "in_progress"   # Actively being processed
    COMPLETED = "completed"       # Successfully done
    FAILED = "failed"             # Failed, may need retry
    BLOCKED = "blocked"           # Waiting for dependencies
    CANCELLED = "cancelled"       # No longer needed


class TaskType(Enum):
    """Types of tasks agents can perform."""
    SCAN_FUNCTION = "scan_function"             # Initial scan of a function
    ANALYZE_FINDING = "analyze_finding"         # Deep analysis of potential vuln
    VERIFY_HYPOTHESIS = "verify_hypothesis"     # Verify a hypothesis
    BUILD_EXPLOIT = "build_exploit"             # Create PoC exploit
    GENERATE_FIX = "generate_fix"               # Generate fix recommendation
    CROSS_REFERENCE = "cross_reference"         # Check related functions
    PATTERN_MATCH = "pattern_match"             # Match against known patterns
    WRITE_REPORT = "write_report"               # Generate report section
    CONSENSUS_CHECK = "consensus_check"         # Build consensus on finding


@dataclass
class TaskResult:
    """Result of task execution."""
    task_id: str
    success: bool
    result_type: str  # finding, hypothesis, evidence, report, etc.
    result_data: Any
    agent_id: str
    execution_time_ms: int = 0
    error_message: Optional[str] = None
    follow_up_tasks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "result_type": self.result_type,
            "agent_id": self.agent_id,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "follow_up_tasks": self.follow_up_tasks,
        }


@dataclass
class SwarmTask:
    """A task for the swarm to execute."""
    task_id: str
    task_type: TaskType
    priority: TaskPriority
    description: str
    target: str  # Function name, finding ID, etc.

    # Task details
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: Set[str] = field(default_factory=set)

    # State
    status: TaskStatus = TaskStatus.PENDING
    claimed_by: Optional[str] = None
    result: Optional[TaskResult] = None

    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    claimed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: int = 300  # 5 minute default timeout

    # Retry tracking
    retry_count: int = 0
    max_retries: int = 3

    def __lt__(self, other: "SwarmTask") -> bool:
        """For priority queue ordering."""
        return self.priority.value < other.priority.value

    def is_claimable(self) -> bool:
        """Check if task can be claimed."""
        return self.status == TaskStatus.PENDING

    def is_timed_out(self) -> bool:
        """Check if task has timed out."""
        if self.claimed_at and self.status in [TaskStatus.CLAIMED, TaskStatus.IN_PROGRESS]:
            elapsed = (datetime.now() - self.claimed_at).total_seconds()
            return elapsed > self.timeout_seconds
        return False

    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.retry_count < self.max_retries

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "priority": self.priority.name,
            "description": self.description,
            "target": self.target,
            "status": self.status.value,
            "claimed_by": self.claimed_by,
            "retry_count": self.retry_count,
            "dependencies": len(self.depends_on),
        }


class TaskBoard:
    """
    Shared task board for agent coordination.

    Implements:
    - Priority-based task queue
    - Task claiming with timeouts
    - Dependency tracking
    - Result storage
    """

    def __init__(self):
        self._tasks: Dict[str, SwarmTask] = {}
        self._priority_queue: List[SwarmTask] = []
        self._completed_tasks: Dict[str, SwarmTask] = {}
        self._lock = threading.Lock()
        self._task_counter = 0

    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        self._task_counter += 1
        return f"TASK-{self._task_counter:06d}"

    def create_task(
        self,
        task_type: TaskType,
        target: str,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        parameters: Optional[Dict[str, Any]] = None,
        required_capabilities: Optional[Set[str]] = None,
        depends_on: Optional[List[str]] = None,
        timeout_seconds: int = 300
    ) -> SwarmTask:
        """Create and add a new task."""
        with self._lock:
            task = SwarmTask(
                task_id=self._generate_task_id(),
                task_type=task_type,
                priority=priority,
                description=description,
                target=target,
                parameters=parameters or {},
                required_capabilities=required_capabilities or set(),
                depends_on=depends_on or [],
                timeout_seconds=timeout_seconds,
            )

            # Check dependencies
            if depends_on:
                for dep_id in depends_on:
                    if dep_id in self._tasks:
                        self._tasks[dep_id].blocks.append(task.task_id)
                # If has unmet dependencies, mark as blocked
                if not self._dependencies_met(task):
                    task.status = TaskStatus.BLOCKED

            self._tasks[task.task_id] = task

            # Only add to queue if not blocked
            if task.status == TaskStatus.PENDING:
                heapq.heappush(self._priority_queue, task)

            logger.debug(f"Created task: {task.task_id} - {task.description}")
            return task

    def claim_task(
        self,
        agent_id: str,
        capabilities: Optional[Set[str]] = None
    ) -> Optional[SwarmTask]:
        """Claim the highest priority available task."""
        with self._lock:
            # First, check for timed out tasks and release them
            self._release_timed_out_tasks()

            # Find suitable task
            candidates = []
            for task in self._priority_queue:
                if not task.is_claimable():
                    continue
                if task.required_capabilities and capabilities:
                    if not task.required_capabilities.issubset(capabilities):
                        continue
                candidates.append(task)

            if not candidates:
                return None

            # Get highest priority candidate
            candidates.sort(key=lambda t: t.priority.value)
            task = candidates[0]

            # Claim it
            task.status = TaskStatus.CLAIMED
            task.claimed_by = agent_id
            task.claimed_at = datetime.now()

            # Remove from priority queue
            self._priority_queue = [t for t in self._priority_queue if t.task_id != task.task_id]
            heapq.heapify(self._priority_queue)

            logger.debug(f"Agent {agent_id} claimed task: {task.task_id}")
            return task

    def start_task(self, task_id: str, agent_id: str) -> bool:
        """Mark task as in progress."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.claimed_by != agent_id:
                return False

            task.status = TaskStatus.IN_PROGRESS
            return True

    def complete_task(
        self,
        task_id: str,
        agent_id: str,
        result: TaskResult
    ) -> bool:
        """Complete a task with result."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.claimed_by != agent_id:
                return False

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result

            # Move to completed
            self._completed_tasks[task_id] = task

            # Unblock dependent tasks
            self._unblock_dependent_tasks(task_id)

            logger.debug(f"Task completed: {task_id} by {agent_id}")
            return True

    def fail_task(
        self,
        task_id: str,
        agent_id: str,
        error_message: str
    ) -> bool:
        """Mark task as failed."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.claimed_by != agent_id:
                return False

            task.retry_count += 1

            if task.can_retry():
                # Reset for retry
                task.status = TaskStatus.PENDING
                task.claimed_by = None
                task.claimed_at = None
                heapq.heappush(self._priority_queue, task)
                logger.debug(f"Task {task_id} failed, queued for retry {task.retry_count}")
            else:
                task.status = TaskStatus.FAILED
                task.result = TaskResult(
                    task_id=task_id,
                    success=False,
                    result_type="error",
                    result_data=None,
                    agent_id=agent_id,
                    error_message=error_message,
                )
                logger.warning(f"Task {task_id} failed permanently: {error_message}")

            return True

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            task.status = TaskStatus.CANCELLED

            # Remove from queue
            self._priority_queue = [t for t in self._priority_queue if t.task_id != task_id]
            heapq.heapify(self._priority_queue)

            return True

    def release_task(self, task_id: str) -> bool:
        """Release a claimed task back to the queue."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            if task.status in [TaskStatus.CLAIMED, TaskStatus.IN_PROGRESS]:
                task.status = TaskStatus.PENDING
                task.claimed_by = None
                task.claimed_at = None
                heapq.heappush(self._priority_queue, task)
                return True

            return False

    def _release_timed_out_tasks(self):
        """Release tasks that have timed out."""
        for task in self._tasks.values():
            if task.is_timed_out():
                logger.warning(f"Task {task.task_id} timed out, releasing")
                task.status = TaskStatus.PENDING
                task.claimed_by = None
                task.claimed_at = None
                task.retry_count += 1
                if task.can_retry():
                    heapq.heappush(self._priority_queue, task)
                else:
                    task.status = TaskStatus.FAILED

    def _dependencies_met(self, task: SwarmTask) -> bool:
        """Check if all task dependencies are met."""
        for dep_id in task.depends_on:
            dep_task = self._tasks.get(dep_id) or self._completed_tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    def _unblock_dependent_tasks(self, completed_task_id: str):
        """Unblock tasks that depended on the completed task."""
        for task in self._tasks.values():
            if task.status == TaskStatus.BLOCKED:
                if completed_task_id in task.depends_on:
                    if self._dependencies_met(task):
                        task.status = TaskStatus.PENDING
                        heapq.heappush(self._priority_queue, task)
                        logger.debug(f"Unblocked task: {task.task_id}")

    # === Query Methods ===

    def get_task(self, task_id: str) -> Optional[SwarmTask]:
        """Get task by ID."""
        return self._tasks.get(task_id) or self._completed_tasks.get(task_id)

    def get_pending_tasks(self) -> List[SwarmTask]:
        """Get all pending tasks."""
        return [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]

    def get_tasks_by_type(self, task_type: TaskType) -> List[SwarmTask]:
        """Get tasks by type."""
        return [t for t in self._tasks.values() if t.task_type == task_type]

    def get_tasks_for_target(self, target: str) -> List[SwarmTask]:
        """Get all tasks for a specific target."""
        return [t for t in self._tasks.values() if t.target == target]

    def get_agent_tasks(self, agent_id: str) -> List[SwarmTask]:
        """Get tasks claimed by an agent."""
        return [t for t in self._tasks.values() if t.claimed_by == agent_id]

    def get_completed_results(self) -> List[TaskResult]:
        """Get all completed task results."""
        return [t.result for t in self._completed_tasks.values() if t.result]

    # === Statistics ===

    def get_statistics(self) -> Dict[str, Any]:
        """Get board statistics."""
        status_counts = {}
        type_counts = {}
        priority_counts = {}

        for task in list(self._tasks.values()) + list(self._completed_tasks.values()):
            # Status
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

            # Type
            t_type = task.task_type.value
            type_counts[t_type] = type_counts.get(t_type, 0) + 1

            # Priority
            prio = task.priority.name
            priority_counts[prio] = priority_counts.get(prio, 0) + 1

        return {
            "total_tasks": len(self._tasks) + len(self._completed_tasks),
            "pending": len(self.get_pending_tasks()),
            "queue_size": len(self._priority_queue),
            "completed": len(self._completed_tasks),
            "by_status": status_counts,
            "by_type": type_counts,
            "by_priority": priority_counts,
        }

    def get_queue_summary(self) -> str:
        """Get human-readable queue summary."""
        stats = self.get_statistics()
        lines = [
            "=== Task Board Summary ===",
            f"Total tasks: {stats['total_tasks']}",
            f"Queue size: {stats['queue_size']}",
            f"Completed: {stats['completed']}",
            "",
            "By Status:",
        ]

        for status, count in sorted(stats['by_status'].items()):
            lines.append(f"  - {status}: {count}")

        return "\n".join(lines)

    def clear(self):
        """Clear all tasks."""
        with self._lock:
            self._tasks.clear()
            self._priority_queue.clear()
            self._completed_tasks.clear()
            self._task_counter = 0
