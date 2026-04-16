"""AgentSpawner - Parallel agent orchestration for autonomous testing.

Spawns multiple Claude Code agents in parallel for:
- Model comparison benchmarks
- Parallel vulnerability analysis
- Stress testing with multiple scenarios

Uses subprocess pools (ThreadPoolExecutor) for concurrent execution.

Example:
    >>> spawner = AgentSpawner(runner, max_workers=4)
    >>> tasks = [
    ...     AgentTask(task_id="opus", prompt="Analyze for reentrancy", model="claude-opus-4"),
    ...     AgentTask(task_id="sonnet", prompt="Analyze for reentrancy", model="claude-sonnet-4"),
    ... ]
    >>> results = spawner.run_parallel(tasks)
    >>> for result in results:
    ...     print(f"{result.task_id}: {result.duration_ms}ms")
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable

from alphaswarm_sol.testing.harness.runner import ClaudeCodeRunner, ClaudeCodeResult

logger = logging.getLogger(__name__)


@dataclass
class AgentTask:
    """A task for an agent to execute.

    Attributes:
        task_id: Unique identifier for the task (e.g., "reentrancy-opus")
        prompt: The analysis prompt to send
        allowed_tools: Tools to pre-approve for this task
        json_schema: Optional JSON schema for structured output
        model: Model to use (e.g., "claude-opus-4", "claude-sonnet-4")
        timeout_seconds: Timeout for this task (default: 300)
        system_prompt: Optional custom system prompt
        metadata: Optional metadata to track with results

    Example:
        >>> task = AgentTask(
        ...     task_id="reentrancy-opus",
        ...     prompt="Analyze contracts/Vault.sol for reentrancy",
        ...     allowed_tools=["Bash(uv run alphaswarm*)", "Read"],
        ...     model="claude-opus-4",
        ...     timeout_seconds=300
        ... )
    """

    task_id: str
    prompt: str
    allowed_tools: list[str] = field(default_factory=list)
    json_schema: dict[str, Any] | None = None
    model: str | None = None
    timeout_seconds: int = 300
    system_prompt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result from an agent task.

    Attributes:
        task_id: Task identifier matching the AgentTask
        result: ClaudeCodeResult if successful, None if error
        error: Exception if task failed, None if successful
        duration_ms: Total execution time in milliseconds
        metadata: Metadata from the original task

    Example:
        >>> if result.error:
        ...     print(f"Task {result.task_id} failed: {result.error}")
        ... else:
        ...     print(f"Task {result.task_id} took {result.duration_ms}ms")
    """

    task_id: str
    result: ClaudeCodeResult | None
    error: Exception | None
    duration_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if task completed successfully."""
        return self.error is None and self.result is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "result": self.result.to_dict() if self.result else None,
            "error": str(self.error) if self.error else None,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "success": self.success,
        }


# Type alias for progress callback
ProgressCallback = Callable[[str, int, int], None]


class AgentSpawner:
    """Spawn multiple agents in parallel for autonomous testing.

    Uses ThreadPoolExecutor for concurrent subprocess execution.
    Each agent runs in its own subprocess via ClaudeCodeRunner.

    Example:
        >>> runner = ClaudeCodeRunner(project_root=Path("."))
        >>> spawner = AgentSpawner(runner, max_workers=4)
        >>>
        >>> tasks = [
        ...     AgentTask(task_id="opus", prompt="Analyze", model="claude-opus-4"),
        ...     AgentTask(task_id="sonnet", prompt="Analyze", model="claude-sonnet-4"),
        ... ]
        >>>
        >>> results = spawner.run_parallel(tasks)
        >>> for r in results:
        ...     print(f"{r.task_id}: {r.duration_ms}ms, success={r.success}")

    Attributes:
        runner: ClaudeCodeRunner instance for executing tasks
        max_workers: Maximum concurrent agents (default: 4)
    """

    def __init__(
        self,
        runner: ClaudeCodeRunner,
        max_workers: int = 4,
    ):
        """Initialize AgentSpawner.

        Args:
            runner: ClaudeCodeRunner for executing tasks
            max_workers: Maximum concurrent agents
        """
        self.runner = runner
        self.max_workers = max_workers

    def run_parallel(
        self,
        tasks: list[AgentTask],
        progress_callback: ProgressCallback | None = None,
    ) -> list[AgentResult]:
        """Run multiple agent tasks in parallel.

        Args:
            tasks: List of AgentTask to execute
            progress_callback: Optional callback(task_id, completed, total)

        Returns:
            List of AgentResult in same order as input tasks
        """
        if not tasks:
            return []

        results: dict[str, AgentResult] = {}
        completed = 0

        logger.info(f"Starting {len(tasks)} tasks with {self.max_workers} workers")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(self._run_task, task): task for task in tasks
            }

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                except Exception as e:
                    # Unexpected executor error
                    logger.error(f"Executor error for {task.task_id}: {e}")
                    result = AgentResult(
                        task_id=task.task_id,
                        result=None,
                        error=e,
                        duration_ms=0,
                        metadata=task.metadata,
                    )

                results[task.task_id] = result
                completed += 1

                if progress_callback:
                    progress_callback(task.task_id, completed, len(tasks))

                logger.info(
                    f"Task {task.task_id} complete ({completed}/{len(tasks)}): "
                    f"{'success' if result.success else 'failed'}"
                )

        # Return in original order
        return [results[task.task_id] for task in tasks]

    def _run_task(self, task: AgentTask) -> AgentResult:
        """Execute a single agent task.

        Args:
            task: AgentTask to execute

        Returns:
            AgentResult with result or error
        """
        start = time.monotonic()

        try:
            result = self.runner.run_analysis(
                prompt=task.prompt,
                allowed_tools=task.allowed_tools,
                json_schema=task.json_schema,
                model=task.model,
                timeout_seconds=task.timeout_seconds,
                system_prompt=task.system_prompt,
            )
            error = None
        except Exception as e:
            result = None
            error = e
            logger.error(f"Task {task.task_id} failed: {e}")

        duration_ms = int((time.monotonic() - start) * 1000)

        return AgentResult(
            task_id=task.task_id,
            result=result,
            error=error,
            duration_ms=duration_ms,
            metadata=task.metadata,
        )

    def run_model_comparison(
        self,
        prompt: str,
        allowed_tools: list[str],
        models: list[str],
        json_schema: dict[str, Any] | None = None,
        timeout_seconds: int = 300,
    ) -> dict[str, AgentResult]:
        """Run same prompt against multiple models for comparison.

        Args:
            prompt: Analysis prompt to run
            allowed_tools: Tools to pre-approve
            models: List of model IDs to compare
            json_schema: Output schema
            timeout_seconds: Timeout per model

        Returns:
            Dict mapping model ID to AgentResult

        Example:
            >>> results = spawner.run_model_comparison(
            ...     prompt="Analyze for vulnerabilities",
            ...     allowed_tools=["Read", "Glob"],
            ...     models=["claude-opus-4", "claude-sonnet-4", "claude-haiku-4"]
            ... )
            >>> for model, result in results.items():
            ...     print(f"{model}: {result.duration_ms}ms")
        """
        tasks = [
            AgentTask(
                task_id=model,
                prompt=prompt,
                allowed_tools=allowed_tools,
                json_schema=json_schema,
                model=model,
                timeout_seconds=timeout_seconds,
                metadata={"comparison_type": "model", "model": model},
            )
            for model in models
        ]

        results = self.run_parallel(tasks)
        return {task.task_id: result for task, result in zip(tasks, results)}

    def run_contract_batch(
        self,
        contracts: list[str],
        prompt_template: str,
        allowed_tools: list[str],
        json_schema: dict[str, Any] | None = None,
        model: str | None = None,
        timeout_seconds: int = 300,
    ) -> dict[str, AgentResult]:
        """Run analysis on multiple contracts in parallel.

        Args:
            contracts: List of contract paths
            prompt_template: Template with {contract_path} placeholder
            allowed_tools: Tools to pre-approve
            json_schema: Output schema
            model: Model to use
            timeout_seconds: Timeout per contract

        Returns:
            Dict mapping contract path to AgentResult

        Example:
            >>> results = spawner.run_contract_batch(
            ...     contracts=["Vault.sol", "Token.sol", "Oracle.sol"],
            ...     prompt_template="Analyze {contract_path} for security issues",
            ...     allowed_tools=["Bash(uv run alphaswarm*)", "Read"]
            ... )
        """
        tasks = [
            AgentTask(
                task_id=contract,
                prompt=prompt_template.format(contract_path=contract),
                allowed_tools=allowed_tools,
                json_schema=json_schema,
                model=model,
                timeout_seconds=timeout_seconds,
                metadata={"contract_path": contract},
            )
            for contract in contracts
        ]

        results = self.run_parallel(tasks)
        return {task.task_id: result for task, result in zip(tasks, results)}

    def run_vuln_class_sweep(
        self,
        contract_path: str,
        vuln_classes: list[str],
        allowed_tools: list[str],
        json_schema: dict[str, Any] | None = None,
        model: str | None = None,
        timeout_seconds: int = 300,
    ) -> dict[str, AgentResult]:
        """Run focused analysis for each vulnerability class in parallel.

        Args:
            contract_path: Contract to analyze
            vuln_classes: List of vulnerability classes to check
            allowed_tools: Tools to pre-approve
            json_schema: Output schema
            model: Model to use
            timeout_seconds: Timeout per class

        Returns:
            Dict mapping vuln class to AgentResult

        Example:
            >>> results = spawner.run_vuln_class_sweep(
            ...     contract_path="Vault.sol",
            ...     vuln_classes=["reentrancy", "access-control", "oracle-manipulation"],
            ...     allowed_tools=["Bash(uv run alphaswarm*)", "Read"]
            ... )
        """
        tasks = [
            AgentTask(
                task_id=vuln_class,
                prompt=f"Analyze {contract_path} for {vuln_class} vulnerabilities. "
                f"Focus specifically on {vuln_class} patterns and use VKG queries.",
                allowed_tools=allowed_tools,
                json_schema=json_schema,
                model=model,
                timeout_seconds=timeout_seconds,
                metadata={"vuln_class": vuln_class, "contract_path": contract_path},
            )
            for vuln_class in vuln_classes
        ]

        results = self.run_parallel(tasks)
        return {task.task_id: result for task, result in zip(tasks, results)}

    def get_aggregate_stats(self, results: list[AgentResult]) -> dict[str, Any]:
        """Calculate aggregate statistics from results.

        Args:
            results: List of AgentResult

        Returns:
            Dict with aggregate statistics
        """
        if not results:
            return {
                "total_tasks": 0,
                "successful": 0,
                "failed": 0,
                "total_duration_ms": 0,
                "avg_duration_ms": 0,
            }

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        durations = [r.duration_ms for r in results]
        total_duration = sum(durations)
        avg_duration = total_duration // len(results) if results else 0

        total_cost = sum(
            r.result.cost_usd for r in successful if r.result and r.result.cost_usd
        )

        return {
            "total_tasks": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) if results else 0,
            "total_duration_ms": total_duration,
            "avg_duration_ms": avg_duration,
            "min_duration_ms": min(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "total_cost_usd": total_cost,
            "failed_task_ids": [r.task_id for r in failed],
        }
