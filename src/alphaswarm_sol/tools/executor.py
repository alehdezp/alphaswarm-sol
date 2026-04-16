"""
Parallel Tool Executor

Executes static analysis tools based on coordinator strategies.
Runs tools in parallel groups, handles timeouts, and provides
comprehensive error recovery.

Per PHILOSOPHY.md Pillar 6: tool execution uses haiku-4.5 tier for
efficient tool running while coordination uses sonnet-4.5.

Usage:
    executor = ToolExecutor()
    results = executor.execute_strategy(strategy, project_path)
    for result in results:
        if result.success:
            print(f"{result.tool}: {len(result.findings)} findings")
        else:
            print(f"{result.tool}: {result.error}")
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, ClassVar, Dict, List, Optional

import structlog

from alphaswarm_sol.tools.adapters.sarif import VKGFinding
from alphaswarm_sol.tools.config import ToolConfig, get_optimal_config
from alphaswarm_sol.tools.coordinator import ToolStrategy
from alphaswarm_sol.tools.registry import ModelTier
from alphaswarm_sol.tools.runner import ToolRunner, ToolResult

logger = structlog.get_logger(__name__)


@dataclass
class ExecutionResult:
    """Result of executing a single tool.

    Captures the outcome including findings, timing, errors, and
    whether results came from cache or were partial.

    Attributes:
        tool: Name of the tool that was executed
        success: Whether the tool completed without fatal errors
        findings: List of VKG findings extracted from tool output
        execution_time: Time in seconds for execution
        error: Error message if execution failed
        from_cache: Whether results came from cache
        partial: Whether results are incomplete (e.g., timeout)
        raw_output: Raw tool output (truncated for large outputs)
        metadata: Additional execution metadata
    """

    tool: str
    success: bool
    findings: List[VKGFinding]
    execution_time: float
    error: Optional[str] = None
    from_cache: bool = False
    partial: bool = False
    raw_output: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool": self.tool,
            "success": self.success,
            "findings_count": len(self.findings),
            "execution_time": self.execution_time,
            "error": self.error,
            "from_cache": self.from_cache,
            "partial": self.partial,
            "metadata": self.metadata,
        }

    @property
    def ok(self) -> bool:
        """Alias for success."""
        return self.success

    @property
    def finding_count(self) -> int:
        """Number of findings."""
        return len(self.findings)


# Type alias for tool adapter functions
ToolAdapterFunc = Callable[[Path, ToolConfig], List[VKGFinding]]


class ToolExecutor:
    """Executes static analysis tools with parallel support.

    Runs tools based on coordinator strategies, handling:
    - Parallel execution within groups
    - Per-tool timeouts
    - Error recovery with hints
    - Result caching integration

    Model tier: haiku-4.5 for tool execution.

    Example:
        executor = ToolExecutor()

        # Execute a full strategy
        results = executor.execute_strategy(strategy, Path("./contracts"))

        # Or execute a single tool
        result = executor.execute_tool("slither", config, Path("./contracts"))
    """

    # Model tier for tool execution
    MODEL_TIER: ClassVar[str] = ModelTier.RUNNING

    # Maximum output size to store (10MB)
    MAX_OUTPUT_SIZE: ClassVar[int] = 10 * 1024 * 1024

    # Retry configuration
    DEFAULT_MAX_RETRIES: ClassVar[int] = 1
    RETRY_DELAY: ClassVar[float] = 2.0

    # Retryable error patterns
    RETRYABLE_ERRORS: ClassVar[List[str]] = [
        "timeout",
        "timed out",
        "connection refused",
        "resource temporarily unavailable",
        "too many open files",
        "try again",
    ]

    def __init__(
        self,
        runner: Optional[ToolRunner] = None,
        cache: Optional[Any] = None,  # ToolResultCache when implemented
        max_workers: int = 4,
    ):
        """Initialize executor.

        Args:
            runner: Tool runner for subprocess execution.
                   Creates default if not provided.
            cache: Optional result cache for incremental analysis.
            max_workers: Maximum parallel workers per group.
        """
        self.runner = runner or ToolRunner()
        self.cache = cache
        self.max_workers = max_workers
        self._adapters: Dict[str, ToolAdapterFunc] = {}
        self._register_adapters()

    def execute_strategy(
        self,
        strategy: ToolStrategy,
        project_path: Path,
        use_cache: bool = True,
    ) -> List[ExecutionResult]:
        """Execute a full tool strategy.

        Runs tools in parallel groups as specified by the strategy.
        Groups run sequentially, tools within groups run in parallel.

        Args:
            strategy: Tool execution strategy from coordinator.
            project_path: Path to the project to analyze.
            use_cache: Whether to use cached results when available.

        Returns:
            List of ExecutionResult for all tools.
        """
        logger.info(
            "executing_strategy",
            tools=strategy.tools_to_run,
            groups=len(strategy.parallel_groups),
            project=str(project_path),
        )

        start_time = time.monotonic()
        all_results: List[ExecutionResult] = []

        for group_idx, group in enumerate(strategy.parallel_groups):
            # Filter to tools we're actually running
            tools_in_group = [t for t in group if t in strategy.tools_to_run]
            if not tools_in_group:
                continue

            logger.debug(
                "executing_group",
                group=group_idx + 1,
                tools=tools_in_group,
            )

            # Run group in parallel
            group_results = self.execute_parallel_group(
                tools_in_group,
                strategy.tool_configs,
                project_path,
                use_cache=use_cache,
            )
            all_results.extend(group_results)

        total_time = time.monotonic() - start_time
        success_count = sum(1 for r in all_results if r.success)
        finding_count = sum(r.finding_count for r in all_results)

        logger.info(
            "strategy_complete",
            total_time=f"{total_time:.2f}s",
            tools_run=len(all_results),
            successful=success_count,
            findings=finding_count,
        )

        return all_results

    def execute_parallel_group(
        self,
        tools: List[str],
        configs: Dict[str, ToolConfig],
        project_path: Path,
        use_cache: bool = True,
    ) -> List[ExecutionResult]:
        """Execute a group of tools in parallel.

        Args:
            tools: List of tool names to run.
            configs: Configuration per tool.
            project_path: Path to analyze.
            use_cache: Whether to check cache first.

        Returns:
            List of ExecutionResult for all tools in group.
        """
        results: List[ExecutionResult] = []
        workers = min(len(tools), self.max_workers)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures: Dict[Future[ExecutionResult], str] = {}

            for tool in tools:
                config = configs.get(tool) or get_optimal_config(tool)
                future = executor.submit(
                    self._execute_with_cache,
                    tool,
                    config,
                    project_path,
                    use_cache,
                )
                futures[future] = tool

            for future in as_completed(futures):
                tool = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    # Tool failure is never fatal
                    logger.warning(
                        "tool_execution_failed",
                        tool=tool,
                        error=str(e),
                    )
                    results.append(
                        ExecutionResult(
                            tool=tool,
                            success=False,
                            findings=[],
                            execution_time=0,
                            error=f"Execution error: {e}",
                            from_cache=False,
                            partial=False,
                            metadata={"exception": type(e).__name__},
                        )
                    )

        return results

    def execute_tool(
        self,
        tool: str,
        config: Optional[ToolConfig],
        project_path: Path,
        retry: bool = True,
    ) -> ExecutionResult:
        """Execute a single tool.

        Args:
            tool: Tool name to execute.
            config: Tool configuration. Uses defaults if None.
            project_path: Path to analyze.
            retry: Whether to retry on transient failures.

        Returns:
            ExecutionResult with findings or error.
        """
        if config is None:
            config = get_optimal_config(tool)

        logger.debug(
            "executing_tool",
            tool=tool,
            timeout=config.timeout,
            project=str(project_path),
        )

        start_time = time.monotonic()

        # Check if we have an adapter for this tool
        adapter = self._adapters.get(tool)

        if adapter:
            # Use typed adapter
            result = self._execute_with_adapter(
                tool, adapter, config, project_path, retry
            )
        else:
            # Fall back to generic CLI execution
            result = self._execute_cli(tool, config, project_path, retry)

        execution_time = time.monotonic() - start_time
        result.execution_time = execution_time

        if result.success:
            logger.info(
                "tool_complete",
                tool=tool,
                findings=result.finding_count,
                time=f"{execution_time:.2f}s",
            )
        else:
            logger.warning(
                "tool_failed",
                tool=tool,
                error=result.error,
                partial=result.partial,
            )

        return result

    def _execute_with_cache(
        self,
        tool: str,
        config: ToolConfig,
        project_path: Path,
        use_cache: bool,
    ) -> ExecutionResult:
        """Execute tool with cache check.

        Args:
            tool: Tool to execute.
            config: Tool configuration.
            project_path: Path to analyze.
            use_cache: Whether to check cache.

        Returns:
            ExecutionResult (from cache or fresh execution).
        """
        # Check cache if enabled and available
        if use_cache and self.cache is not None:
            cached = self.cache.get(tool, project_path, config)
            if cached:
                logger.debug("cache_hit", tool=tool)
                return ExecutionResult(
                    tool=tool,
                    success=True,
                    findings=cached.findings,
                    execution_time=cached.execution_time,
                    from_cache=True,
                    partial=False,
                    metadata={"cached_at": str(cached.cached_at)},
                )

        # Execute fresh
        result = self.execute_tool(tool, config, project_path, retry=True)

        # Cache successful results
        if result.success and self.cache is not None:
            self.cache.put(
                tool,
                project_path,
                config,
                result.findings,
                result.execution_time,
            )

        return result

    def _execute_with_adapter(
        self,
        tool: str,
        adapter: ToolAdapterFunc,
        config: ToolConfig,
        project_path: Path,
        retry: bool,
    ) -> ExecutionResult:
        """Execute tool using typed adapter.

        Args:
            tool: Tool name.
            adapter: Adapter function.
            config: Tool configuration.
            project_path: Path to analyze.
            retry: Whether to retry on failure.

        Returns:
            ExecutionResult.
        """
        max_attempts = self.DEFAULT_MAX_RETRIES + 1 if retry else 1
        last_error: Optional[str] = None

        for attempt in range(max_attempts):
            try:
                findings = adapter(project_path, config)
                return ExecutionResult(
                    tool=tool,
                    success=True,
                    findings=findings,
                    execution_time=0,  # Set by caller
                    from_cache=False,
                    partial=False,
                )
            except Exception as e:
                last_error = str(e)
                if attempt < max_attempts - 1 and self._is_retryable(last_error):
                    logger.debug(
                        "retrying_tool",
                        tool=tool,
                        attempt=attempt + 1,
                        error=last_error,
                    )
                    time.sleep(self.RETRY_DELAY * (attempt + 1))

        return ExecutionResult(
            tool=tool,
            success=False,
            findings=[],
            execution_time=0,
            error=last_error,
            from_cache=False,
            partial=False,
            metadata={"adapter": True, "retried": retry},
        )

    def _execute_cli(
        self,
        tool: str,
        config: ToolConfig,
        project_path: Path,
        retry: bool,
    ) -> ExecutionResult:
        """Execute tool via CLI.

        Generic fallback for tools without typed adapters.

        Args:
            tool: Tool name (must be in PATH).
            config: Tool configuration.
            project_path: Path to analyze.
            retry: Whether to retry on failure.

        Returns:
            ExecutionResult.
        """
        # Build command based on tool
        command = self._build_command(tool, config, project_path)

        if not command:
            return ExecutionResult(
                tool=tool,
                success=False,
                findings=[],
                execution_time=0,
                error=f"Unknown tool: {tool}",
                from_cache=False,
                partial=False,
            )

        # Run with retry if enabled
        if retry:
            result = self.runner.run_with_retry(
                command,
                timeout=config.timeout,
                cwd=project_path,
            )
        else:
            result = self.runner.run(
                command,
                timeout=config.timeout,
                cwd=project_path,
            )

        # Parse output to findings
        findings = self._parse_output(tool, result.output) if result.output else []

        return ExecutionResult(
            tool=tool,
            success=result.success,
            findings=findings,
            execution_time=result.runtime_ms / 1000.0,
            error=result.error,
            from_cache=False,
            partial=result.partial,
            raw_output=self._truncate_output(result.output),
            metadata={
                "exit_code": result.exit_code,
                "recovery": result.recovery,
            },
        )

    def _build_command(
        self,
        tool: str,
        config: ToolConfig,
        project_path: Path,
    ) -> List[str]:
        """Build CLI command for a tool.

        Args:
            tool: Tool name.
            config: Tool configuration.
            project_path: Path to analyze.

        Returns:
            Command list or empty list if unknown.
        """
        # Basic commands for known tools
        commands: Dict[str, List[str]] = {
            "slither": ["slither", "--json", "-", str(project_path)],
            "aderyn": ["aderyn", str(project_path), "--output", "json"],
            "mythril": ["myth", "analyze", "--json", str(project_path)],
            "semgrep": [
                "semgrep",
                "scan",
                "--json",
                str(project_path),
            ],
            "echidna": ["echidna", str(project_path)],
            "foundry": ["forge", "test", "--json"],
            "halmos": ["halmos", "--root", str(project_path)],
            "medusa": ["medusa", "fuzz", "--config", str(project_path / "medusa.json")],
        }

        base_command = commands.get(tool)
        if not base_command:
            return []

        # Add extra args from config
        if config.extra_args:
            base_command.extend(config.extra_args)

        return base_command

    def _parse_output(self, tool: str, output: str) -> List[VKGFinding]:
        """Parse tool output to VKG findings.

        Uses tool-specific adapters when available.

        Args:
            tool: Tool name.
            output: Raw tool output.

        Returns:
            List of VKGFinding.
        """
        # Import adapters lazily to avoid circular imports
        try:
            if tool == "slither":
                from alphaswarm_sol.tools.adapters.slither_adapter import slither_to_vkg_findings
                return slither_to_vkg_findings(output)
            elif tool == "aderyn":
                from alphaswarm_sol.tools.adapters.aderyn_adapter import aderyn_to_vkg_findings
                return aderyn_to_vkg_findings(output)
            elif tool == "mythril":
                from alphaswarm_sol.tools.adapters.mythril_adapter import mythril_to_vkg_findings
                return mythril_to_vkg_findings(output)
        except Exception as e:
            logger.warning(
                "output_parse_failed",
                tool=tool,
                error=str(e),
            )

        return []

    def _register_adapters(self) -> None:
        """Register tool adapters for typed execution."""
        # Adapters will be registered here as they're implemented
        # For now, rely on CLI fallback
        pass

    def _is_retryable(self, error: str) -> bool:
        """Check if an error is transient and worth retrying.

        Args:
            error: Error message.

        Returns:
            True if should retry.
        """
        if not error:
            return False

        error_lower = error.lower()
        return any(pattern in error_lower for pattern in self.RETRYABLE_ERRORS)

    def _truncate_output(self, output: Optional[str]) -> Optional[str]:
        """Truncate large output for storage.

        Args:
            output: Raw output.

        Returns:
            Truncated output or None.
        """
        if not output:
            return None

        if len(output) > self.MAX_OUTPUT_SIZE:
            return output[: self.MAX_OUTPUT_SIZE] + "\n... (truncated)"

        return output


# Convenience functions


def execute_tool(
    tool: str,
    project_path: Path,
    config: Optional[ToolConfig] = None,
) -> ExecutionResult:
    """Execute a single tool using default executor.

    Args:
        tool: Tool name.
        project_path: Path to analyze.
        config: Optional tool config.

    Returns:
        ExecutionResult.
    """
    return ToolExecutor().execute_tool(tool, config, project_path)


def execute_strategy(
    strategy: ToolStrategy,
    project_path: Path,
) -> List[ExecutionResult]:
    """Execute a strategy using default executor.

    Args:
        strategy: Tool strategy.
        project_path: Path to analyze.

    Returns:
        List of ExecutionResult.
    """
    return ToolExecutor().execute_strategy(strategy, project_path)


__all__ = [
    "ExecutionResult",
    "ToolExecutor",
    "execute_tool",
    "execute_strategy",
]
