"""Hook interfaces for Phase 5.2 SDK integration.

These interfaces define how tool skills will interact with the SDK's
hook system. Implementing now ensures Phase 5.1 work is SDK-ready.

The actual hook implementation (queues, routing, propulsion) will be
built in Phase 5.2. This module defines the contracts.

Usage:
    # Simple invocation
    from alphaswarm_sol.tools.hooks import run_tool, HookPriority
    result = await run_tool("slither", Path("./contracts"))

    # Full control
    from alphaswarm_sol.tools.hooks import get_tool_hook, ToolRunRequest
    hook = get_tool_hook()
    request = ToolRunRequest(tool="mythril", project_path=Path("./contracts"))
    request_id = await hook.submit(request)
    result = await hook.get_result(request_id)
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from alphaswarm_sol.tools.adapters.sarif import VKGFinding

logger = structlog.get_logger(__name__)


class HookPriority(str, Enum):
    """Priority levels for hook queue.

    Higher priority requests are processed first.
    """

    CRITICAL = "critical"  # Security-critical, process immediately
    HIGH = "high"  # Important findings, prioritize
    NORMAL = "normal"  # Standard priority (default)
    LOW = "low"  # Background analysis
    BACKGROUND = "background"  # Run when idle


class ToolRunStatus(str, Enum):
    """Status of a tool run request."""

    PENDING = "pending"  # Queued, waiting to start
    RUNNING = "running"  # Currently executing
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"  # Execution error
    TIMEOUT = "timeout"  # Exceeded timeout
    CACHED = "cached"  # Result from cache
    CANCELLED = "cancelled"  # User cancelled


@dataclass
class ToolRunRequest:
    """Request to run a tool via hook system.

    This is what an agent submits to the hook queue.

    Attributes:
        tool: Name of the tool to run (slither, mythril, etc.)
        project_path: Path to the project to analyze
        config: Optional tool-specific configuration
        priority: Queue priority for processing order
        timeout: Maximum execution time in seconds
        use_cache: Whether to check/use cached results
        request_id: Unique identifier (auto-generated if not provided)
        requester: Agent ID that submitted the request
        created_at: Timestamp when request was created
    """

    tool: str
    project_path: Path
    config: Optional[Dict[str, Any]] = None
    priority: HookPriority = HookPriority.NORMAL
    timeout: int = 300
    use_cache: bool = True
    request_id: str = ""
    requester: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Generate request ID if not provided."""
        if not self.request_id:
            self.request_id = f"tool-{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for transmission."""
        return {
            "request_id": self.request_id,
            "tool": self.tool,
            "project_path": str(self.project_path),
            "config": self.config,
            "priority": self.priority.value,
            "timeout": self.timeout,
            "use_cache": self.use_cache,
            "requester": self.requester,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ToolRunResult:
    """Result from a tool run via hook system.

    This is what the hook returns to the requesting agent.

    Attributes:
        request_id: Links to original request
        tool: Tool that was executed
        status: Final execution status
        findings: List of VKG findings extracted from tool output
        execution_time: Time in seconds for execution
        error: Error message if execution failed
        from_cache: Whether results came from cache
        partial: Whether results are incomplete (e.g., timeout)
        completed_at: Timestamp when execution completed
    """

    request_id: str
    tool: str
    status: ToolRunStatus
    findings: List[Any] = field(default_factory=list)  # List[VKGFinding]
    execution_time: float = 0.0
    error: Optional[str] = None
    from_cache: bool = False
    partial: bool = False
    completed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for hook transmission."""
        return {
            "request_id": self.request_id,
            "tool": self.tool,
            "status": self.status.value,
            "findings_count": len(self.findings),
            "execution_time": self.execution_time,
            "error": self.error,
            "from_cache": self.from_cache,
            "partial": self.partial,
            "completed_at": self.completed_at.isoformat(),
        }

    @property
    def success(self) -> bool:
        """Check if tool completed successfully."""
        return self.status in (ToolRunStatus.COMPLETED, ToolRunStatus.CACHED)

    @property
    def finding_count(self) -> int:
        """Number of findings."""
        return len(self.findings)


class ToolHook(ABC):
    """Abstract base for tool hook implementations.

    Phase 5.2 will implement concrete versions:
    - LocalToolHook: Direct execution (current, Phase 5.1)
    - QueuedToolHook: Via message queue (Phase 5.2)
    - DistributedToolHook: Across workers (Phase 5.2+)

    Example:
        hook = get_tool_hook()
        request = ToolRunRequest(tool="slither", project_path=Path("./contracts"))

        # Submit request
        request_id = await hook.submit(request)

        # Wait for result
        result = await hook.get_result(request_id, timeout=120)

        # Or check status without blocking
        status = await hook.get_status(request_id)
        if status == ToolRunStatus.RUNNING:
            print("Still running...")
    """

    @abstractmethod
    async def submit(self, request: ToolRunRequest) -> str:
        """Submit a tool run request.

        Args:
            request: Tool run request with tool name, path, config.

        Returns:
            request_id for tracking the request.
        """
        pass

    @abstractmethod
    async def get_result(
        self,
        request_id: str,
        timeout: Optional[float] = None,
    ) -> ToolRunResult:
        """Wait for and retrieve result.

        Blocks until the tool completes or timeout is reached.

        Args:
            request_id: ID from submit().
            timeout: Max wait time in seconds. None = wait forever.

        Returns:
            ToolRunResult when available.

        Raises:
            TimeoutError: If timeout exceeded before completion.
            ValueError: If request_id is unknown.
        """
        pass

    @abstractmethod
    async def get_status(self, request_id: str) -> ToolRunStatus:
        """Check status without blocking.

        Args:
            request_id: ID from submit().

        Returns:
            Current status of the request.
        """
        pass

    @abstractmethod
    async def cancel(self, request_id: str) -> bool:
        """Cancel a pending or running request.

        Args:
            request_id: ID from submit().

        Returns:
            True if cancelled, False if already completed or unknown.
        """
        pass


class LocalToolHook(ToolHook):
    """Direct execution hook for Phase 5.1 compatibility.

    Runs tools directly without queueing. Provides same interface
    as future queued implementations for seamless migration.

    This is the default hook until Phase 5.2 SDK is implemented.

    Example:
        hook = LocalToolHook()

        # Submit and wait
        request = ToolRunRequest(tool="slither", project_path=Path("./contracts"))
        request_id = await hook.submit(request)
        result = await hook.get_result(request_id)

        # Check findings
        if result.success:
            for finding in result.findings:
                print(finding.title)
    """

    def __init__(self) -> None:
        """Initialize local hook with result storage."""
        self._results: Dict[str, ToolRunResult] = {}
        self._pending: Dict[str, asyncio.Task[ToolRunResult]] = {}
        self._requests: Dict[str, ToolRunRequest] = {}

    async def submit(self, request: ToolRunRequest) -> str:
        """Execute tool directly, store result.

        Starts execution immediately in a background task.

        Args:
            request: Tool run request.

        Returns:
            request_id for tracking.
        """
        request_id = request.request_id
        self._requests[request_id] = request

        logger.debug(
            "local_hook_submit",
            request_id=request_id,
            tool=request.tool,
            project_path=str(request.project_path),
        )

        # Create task for async execution
        task = asyncio.create_task(self._run_tool(request))
        self._pending[request_id] = task

        return request_id

    async def get_result(
        self,
        request_id: str,
        timeout: Optional[float] = None,
    ) -> ToolRunResult:
        """Wait for task completion.

        Args:
            request_id: ID from submit().
            timeout: Max wait time in seconds.

        Returns:
            ToolRunResult when available.

        Raises:
            TimeoutError: If timeout exceeded.
            ValueError: If request_id unknown.
        """
        # Check if already completed
        if request_id in self._results:
            return self._results[request_id]

        # Check if pending
        if request_id not in self._pending:
            raise ValueError(f"Unknown request: {request_id}")

        task = self._pending[request_id]

        try:
            result = await asyncio.wait_for(task, timeout=timeout)
            self._results[request_id] = result
            del self._pending[request_id]
            return result

        except asyncio.TimeoutError:
            logger.warning(
                "hook_result_timeout",
                request_id=request_id,
                timeout=timeout,
            )
            # Return timeout result but don't cancel task
            return ToolRunResult(
                request_id=request_id,
                tool=self._requests.get(request_id, ToolRunRequest("", Path("."))).tool,
                status=ToolRunStatus.TIMEOUT,
                error=f"Timed out waiting for result after {timeout}s",
            )

    async def get_status(self, request_id: str) -> ToolRunStatus:
        """Check if task is done.

        Args:
            request_id: ID from submit().

        Returns:
            Current status.
        """
        if request_id in self._results:
            return self._results[request_id].status

        if request_id in self._pending:
            task = self._pending[request_id]
            if task.done():
                # Task finished but result not yet retrieved
                try:
                    result = task.result()
                    return result.status
                except Exception:
                    return ToolRunStatus.FAILED
            return ToolRunStatus.RUNNING

        return ToolRunStatus.PENDING

    async def cancel(self, request_id: str) -> bool:
        """Cancel pending task.

        Args:
            request_id: ID from submit().

        Returns:
            True if cancelled.
        """
        if request_id in self._pending:
            task = self._pending[request_id]
            task.cancel()
            del self._pending[request_id]

            # Store cancellation result
            self._results[request_id] = ToolRunResult(
                request_id=request_id,
                tool=self._requests.get(request_id, ToolRunRequest("", Path("."))).tool,
                status=ToolRunStatus.CANCELLED,
                error="Cancelled by user",
            )

            logger.debug("hook_cancelled", request_id=request_id)
            return True

        return False

    async def _run_tool(self, request: ToolRunRequest) -> ToolRunResult:
        """Execute tool and create result.

        Runs synchronous ToolExecutor in thread pool.

        Args:
            request: Tool run request.

        Returns:
            ToolRunResult with findings or error.
        """
        from alphaswarm_sol.tools.config import get_optimal_config
        from alphaswarm_sol.tools.executor import ToolExecutor

        request_id = request.request_id
        start_time = datetime.now()

        logger.debug(
            "local_hook_running",
            request_id=request_id,
            tool=request.tool,
        )

        try:
            # Run in thread pool since ToolExecutor is sync
            loop = asyncio.get_event_loop()
            executor = ToolExecutor()
            config = request.config or get_optimal_config(request.tool)

            # Convert dict config to ToolConfig if needed
            if isinstance(config, dict):
                from alphaswarm_sol.tools.config import ToolConfig

                config = ToolConfig(name=request.tool, **config)

            result = await loop.run_in_executor(
                None,
                lambda: executor.execute_tool(
                    request.tool,
                    config,
                    request.project_path,
                    retry=True,
                ),
            )

            return ToolRunResult(
                request_id=request_id,
                tool=request.tool,
                status=ToolRunStatus.COMPLETED if result.success else ToolRunStatus.FAILED,
                findings=result.findings,
                execution_time=result.execution_time,
                error=result.error,
                from_cache=result.from_cache,
                partial=result.partial,
            )

        except asyncio.CancelledError:
            return ToolRunResult(
                request_id=request_id,
                tool=request.tool,
                status=ToolRunStatus.CANCELLED,
                error="Execution cancelled",
            )

        except Exception as e:
            logger.exception(
                "local_hook_error",
                request_id=request_id,
                tool=request.tool,
                error=str(e),
            )
            return ToolRunResult(
                request_id=request_id,
                tool=request.tool,
                status=ToolRunStatus.FAILED,
                error=str(e),
            )


# Global hook instance (singleton pattern)
_tool_hook: Optional[ToolHook] = None


def get_tool_hook() -> ToolHook:
    """Get the configured tool hook.

    Returns LocalToolHook for Phase 5.1.
    Phase 5.2 SDK will configure appropriate hook based on deployment.

    Returns:
        ToolHook instance (singleton).
    """
    global _tool_hook
    if _tool_hook is None:
        _tool_hook = LocalToolHook()
    return _tool_hook


def set_tool_hook(hook: ToolHook) -> None:
    """Set the tool hook instance.

    Used by Phase 5.2 SDK to configure appropriate hook.

    Args:
        hook: ToolHook implementation to use.
    """
    global _tool_hook
    _tool_hook = hook


async def run_tool(
    tool: str,
    project_path: Path,
    config: Optional[Dict[str, Any]] = None,
    priority: HookPriority = HookPriority.NORMAL,
    timeout: Optional[float] = None,
) -> ToolRunResult:
    """Convenience function to run a tool via hook.

    Submits request and waits for result.

    Args:
        tool: Tool name (slither, mythril, etc.)
        project_path: Path to project to analyze
        config: Optional tool-specific configuration
        priority: Queue priority
        timeout: Max wait time in seconds

    Returns:
        ToolRunResult with findings or error.

    Example:
        result = await run_tool("slither", Path("./contracts"))
        if result.success:
            for finding in result.findings:
                print(finding.title)
    """
    hook = get_tool_hook()
    request = ToolRunRequest(
        tool=tool,
        project_path=project_path,
        config=config,
        priority=priority,
    )
    request_id = await hook.submit(request)
    return await hook.get_result(request_id, timeout=timeout)


async def run_tools_parallel(
    tools: List[str],
    project_path: Path,
    config: Optional[Dict[str, Dict[str, Any]]] = None,
    priority: HookPriority = HookPriority.NORMAL,
) -> Dict[str, ToolRunResult]:
    """Run multiple tools in parallel via hooks.

    Submits all requests then waits for all results.

    Args:
        tools: List of tool names
        project_path: Path to project to analyze
        config: Optional per-tool configuration {tool_name: config}
        priority: Queue priority for all requests

    Returns:
        Dict mapping tool name to result.

    Example:
        results = await run_tools_parallel(
            ["slither", "aderyn"],
            Path("./contracts"),
        )
        for tool, result in results.items():
            print(f"{tool}: {result.finding_count} findings")
    """
    hook = get_tool_hook()
    config = config or {}

    # Submit all requests
    requests: Dict[str, str] = {}  # tool -> request_id
    for tool in tools:
        request = ToolRunRequest(
            tool=tool,
            project_path=project_path,
            config=config.get(tool),
            priority=priority,
        )
        request_id = await hook.submit(request)
        requests[tool] = request_id

    # Wait for all results
    results: Dict[str, ToolRunResult] = {}
    for tool, request_id in requests.items():
        results[tool] = await hook.get_result(request_id)

    return results


__all__ = [
    # Enums
    "HookPriority",
    "ToolRunStatus",
    # Data classes
    "ToolRunRequest",
    "ToolRunResult",
    # Abstract base
    "ToolHook",
    # Implementation
    "LocalToolHook",
    # Functions
    "get_tool_hook",
    "set_tool_hook",
    "run_tool",
    "run_tools_parallel",
]
