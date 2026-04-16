"""
Isolated Tool Runner

Runs external tools with timeout, isolation, and error recovery.
Tool failures NEVER crash VKG - they return structured ToolResult objects.

Features (Phase 07.1.1-02):
- Idempotent execution with key-based caching
- Bounded exponential backoff with jitter
- On-disk persistence for retry across restarts

Usage:
    runner = ToolRunner(timeout=60)
    result = runner.run(["slither", "contract.sol"])
    if not result.success:
        print(f"Error: {result.error}")
        print(f"Recovery: {result.recovery}")

    # Idempotent execution with caching
    result = runner.run_idempotent(
        command=["slither", "contract.sol"],
        idempotency_key="abc123",
        pool_path=Path(".vrs/pools/my-pool"),
    )
"""

import subprocess
import time
import os
import logging
import random
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """
    Result of running an external tool.

    Attributes:
        success: Whether the tool completed successfully
        output: stdout from the tool (may be truncated)
        error: Error message if failed
        exit_code: Process exit code (-1 if not applicable)
        runtime_ms: How long the tool ran in milliseconds
        recovery: Suggested recovery action if failed
        partial: True if we got partial results (e.g., from timeout)
        metadata: Additional metadata about the run
    """

    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    exit_code: int = -1
    runtime_ms: int = 0
    recovery: Optional[str] = None
    partial: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "runtime_ms": self.runtime_ms,
            "recovery": self.recovery,
            "partial": self.partial,
            "metadata": self.metadata,
        }

    @property
    def ok(self) -> bool:
        """Alias for success."""
        return self.success

    def raise_for_status(self) -> None:
        """Raise exception if not successful."""
        if not self.success:
            raise ToolExecutionError(
                f"Tool failed: {self.error}",
                result=self,
            )


class ToolExecutionError(Exception):
    """Raised when raise_for_status is called on a failed result."""

    def __init__(self, message: str, result: ToolResult):
        super().__init__(message)
        self.result = result


@dataclass
class IdempotentRetryConfig:
    """Configuration for idempotent retry with exponential backoff.

    Attributes:
        max_retries: Maximum retry attempts (0 = no retries)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        jitter: Random jitter fraction (0-1) to prevent thundering herd
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: float = 0.25

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt with jitter.

        Args:
            attempt: Zero-indexed attempt number

        Returns:
            Delay in seconds with bounded exponential backoff and jitter
        """
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        if self.jitter > 0:
            delay += delay * self.jitter * random.random()
        return delay


class ToolRunner:
    """
    Runs external tools with isolation and comprehensive error handling.

    Features:
    - Timeout enforcement
    - Output truncation for large outputs
    - Recovery hints for common errors
    - Retry support for transient failures
    - Idempotent execution with on-disk caching (Phase 07.1.1-02)
    - Logging of all tool invocations
    """

    DEFAULT_TIMEOUT = 60  # seconds
    MAX_OUTPUT_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_ERROR_SIZE = 10000  # chars

    # Known recovery hints by tool and exit code
    RECOVERY_HINTS = {
        "slither": {
            1: "Check Solidity syntax or run: slither --help",
            127: "Slither not found. Install: pip install slither-analyzer",
            -9: "Slither was killed (timeout or OOM). Try smaller files.",
        },
        "aderyn": {
            1: "Check contract path or run: aderyn --help",
            127: "Aderyn not found. Install: cargo install aderyn",
        },
        "forge": {
            1: "Check Foundry project setup or run: forge --help",
            127: "Foundry not found. Install: curl -L https://foundry.paradigm.xyz | bash",
        },
        "medusa": {
            1: "Check Medusa configuration or run: medusa --help",
            127: "Medusa not found. See https://github.com/crytic/medusa",
        },
        "solc": {
            1: "Solidity compilation failed. Check syntax.",
            127: "solc not found. Install: pip install solc-select",
        },
    }

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = 0,
        retry_delay: float = 1.0,
    ):
        """
        Initialize tool runner.

        Args:
            timeout: Default timeout in seconds
            max_retries: Number of retries for transient failures
            retry_delay: Base delay between retries (exponential backoff)
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def run(
        self,
        command: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        capture_stderr: bool = True,
    ) -> ToolResult:
        """
        Run a command with isolation.

        Args:
            command: Command and arguments as list
            cwd: Working directory
            env: Environment variables (merged with current env)
            timeout: Override default timeout
            capture_stderr: Whether to capture stderr

        Returns:
            ToolResult with success status and output/error
        """
        if not command:
            return ToolResult(
                success=False,
                error="Empty command",
            )

        effective_timeout = timeout or self.timeout
        start_time = time.monotonic()
        tool_name = Path(command[0]).name

        # Merge environment
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        logger.debug(
            f"Running tool: {tool_name}",
            extra={
                "command": " ".join(command),
                "cwd": str(cwd) if cwd else None,
                "timeout": effective_timeout,
            },
        )

        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                env=full_env,
                capture_output=True,
                timeout=effective_timeout,
                text=True,
            )

            runtime_ms = int((time.monotonic() - start_time) * 1000)

            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    output=self._truncate_output(result.stdout),
                    exit_code=0,
                    runtime_ms=runtime_ms,
                    metadata={"command": command[0]},
                )
            else:
                stderr = result.stderr[:self.MAX_ERROR_SIZE] if result.stderr else None
                return ToolResult(
                    success=False,
                    output=self._truncate_output(result.stdout) if result.stdout else None,
                    error=stderr or f"Command failed with exit code {result.returncode}",
                    exit_code=result.returncode,
                    runtime_ms=runtime_ms,
                    recovery=self._get_recovery_hint(tool_name, result.returncode, stderr),
                    metadata={"command": command[0]},
                )

        except subprocess.TimeoutExpired as e:
            runtime_ms = int((time.monotonic() - start_time) * 1000)
            partial_output = None
            if e.stdout:
                if isinstance(e.stdout, bytes):
                    partial_output = e.stdout.decode("utf-8", errors="replace")[:1000]
                else:
                    partial_output = e.stdout[:1000]

            return ToolResult(
                success=False,
                output=partial_output,
                error=f"Command timed out after {effective_timeout}s",
                runtime_ms=runtime_ms,
                recovery=f"Try increasing timeout: --timeout {effective_timeout * 2}",
                partial=bool(partial_output),
                metadata={"command": command[0], "timeout": True},
            )

        except FileNotFoundError:
            return ToolResult(
                success=False,
                error=f"Command not found: {command[0]}",
                recovery=self._get_install_hint(tool_name),
                metadata={"command": command[0], "not_found": True},
            )

        except PermissionError:
            return ToolResult(
                success=False,
                error=f"Permission denied: {command[0]}",
                recovery=f"Check file permissions or run: chmod +x {command[0]}",
                metadata={"command": command[0]},
            )

        except MemoryError:
            runtime_ms = int((time.monotonic() - start_time) * 1000)
            return ToolResult(
                success=False,
                error="Out of memory",
                runtime_ms=runtime_ms,
                recovery="Try reducing input size or increasing system memory",
                metadata={"command": command[0], "oom": True},
            )

        except OSError as e:
            return ToolResult(
                success=False,
                error=f"OS error: {e}",
                recovery="Check system resources and permissions",
                metadata={"command": command[0]},
            )

        except Exception as e:
            logger.exception(f"Unexpected error running {tool_name}")
            return ToolResult(
                success=False,
                error=f"Unexpected error: {type(e).__name__}: {str(e)[:200]}",
                recovery="Check logs for details: vkg tools doctor --verbose",
                metadata={"command": command[0], "exception": type(e).__name__},
            )

    def run_with_retry(
        self,
        command: List[str],
        max_retries: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Run command with retries on transient failures.

        Args:
            command: Command to run
            max_retries: Override default max_retries
            **kwargs: Arguments passed to run()

        Returns:
            ToolResult from successful run or last failure
        """
        retries = max_retries if max_retries is not None else self.max_retries
        last_result = None

        for attempt in range(retries + 1):
            result = self.run(command, **kwargs)

            if result.success:
                return result

            last_result = result

            # Check if error is retryable
            if not self._is_retryable(result):
                return result

            if attempt < retries:
                delay = self.retry_delay * (2 ** attempt)
                logger.info(
                    f"Retry {attempt + 1}/{retries} for {command[0]} "
                    f"after {delay}s delay"
                )
                time.sleep(delay)

        return last_result or ToolResult(
            success=False,
            error="All retries failed",
        )

    def run_idempotent(
        self,
        command: List[str],
        idempotency_key: str,
        pool_path: Path,
        retry_config: Optional[IdempotentRetryConfig] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Run command with idempotency and bounded retry/backoff.

        If the idempotency key has a cached successful result, returns it
        without re-executing. Otherwise reserves the key, executes with
        retries, and records the result.

        Args:
            command: Command and arguments as list
            idempotency_key: Unique key for this operation
            pool_path: Path to pool directory for idempotency storage
            retry_config: Retry configuration (default: 3 retries, exp backoff)
            **kwargs: Arguments passed to run()

        Returns:
            ToolResult from cache or fresh execution
        """
        from alphaswarm_sol.orchestration.idempotency import IdempotencyStore

        config = retry_config or IdempotentRetryConfig()
        store = IdempotencyStore(pool_path)

        # Check for cached result
        existing = store.get(idempotency_key)
        if existing and existing.is_complete and existing.result is not None:
            logger.debug(f"Returning cached tool result for key {idempotency_key}")
            cached_result = existing.result
            if isinstance(cached_result, dict):
                return ToolResult(
                    success=cached_result.get("success", False),
                    output=cached_result.get("output"),
                    error=cached_result.get("error"),
                    exit_code=cached_result.get("exit_code", -1),
                    runtime_ms=cached_result.get("runtime_ms", 0),
                    recovery=cached_result.get("recovery"),
                    partial=cached_result.get("partial", False),
                    metadata=cached_result.get("metadata", {"cached": True}),
                )
            return cached_result

        # Reserve key
        if not store.reserve(idempotency_key, metadata={"command": command[0]}):
            # Check if completed while we were trying to reserve
            existing = store.get(idempotency_key)
            if existing and existing.is_complete and existing.result is not None:
                cached_result = existing.result
                if isinstance(cached_result, dict):
                    return ToolResult(
                        success=cached_result.get("success", False),
                        output=cached_result.get("output"),
                        error=cached_result.get("error"),
                        exit_code=cached_result.get("exit_code", -1),
                        runtime_ms=cached_result.get("runtime_ms", 0),
                        recovery=cached_result.get("recovery"),
                        partial=cached_result.get("partial", False),
                        metadata=cached_result.get("metadata", {"cached": True}),
                    )
            # Key reserved by another process - fail fast
            return ToolResult(
                success=False,
                error=f"Idempotency key {idempotency_key} already reserved",
                metadata={"command": command[0], "idempotency_conflict": True},
            )

        # Execute with bounded retries
        last_result: Optional[ToolResult] = None
        attempt = 0

        while attempt <= config.max_retries:
            result = self.run(command, **kwargs)

            if result.success:
                # Record success and return
                store.record_success(idempotency_key, result.to_dict())
                return result

            last_result = result

            # Check if retryable
            if not self._is_retryable(result):
                store.record_failure(idempotency_key, result.error or "Unknown error", permanent=True)
                return result

            # Check if retries exhausted
            if attempt >= config.max_retries:
                store.record_failure(idempotency_key, result.error or "All retries failed", permanent=True)
                return result

            # Record transient failure
            store.record_failure(idempotency_key, result.error or "Transient failure", permanent=False)

            # Calculate delay with jitter
            delay = config.calculate_delay(attempt)
            logger.info(
                f"Retry {attempt + 1}/{config.max_retries} for {command[0]} "
                f"after {delay:.2f}s delay (key: {idempotency_key})"
            )
            time.sleep(delay)
            attempt += 1

            # Re-reserve for next attempt
            store.reserve(idempotency_key)

        # All retries exhausted
        if last_result:
            store.record_failure(idempotency_key, last_result.error or "All retries failed", permanent=True)
            return last_result

        return ToolResult(
            success=False,
            error="All retries failed",
            metadata={"command": command[0], "idempotency_key": idempotency_key},
        )

    def _truncate_output(self, output: str) -> str:
        """Truncate output if too large."""
        if not output:
            return ""
        if len(output) > self.MAX_OUTPUT_SIZE:
            return output[: self.MAX_OUTPUT_SIZE] + "\n... (truncated)"
        return output

    def _is_retryable(self, result: ToolResult) -> bool:
        """Check if error is transient and worth retrying."""
        if not result.error:
            return False

        retryable_patterns = [
            "timed out",
            "timeout",
            "connection",
            "temporary",
            "try again",
            "resource temporarily unavailable",
            "too many open files",
        ]

        error_lower = result.error.lower()
        return any(p in error_lower for p in retryable_patterns)

    def _get_recovery_hint(
        self,
        tool: str,
        exit_code: int,
        stderr: Optional[str],
    ) -> str:
        """Generate recovery hint based on error."""
        # Check tool-specific hints
        tool_hints = self.RECOVERY_HINTS.get(tool, {})
        hint = tool_hints.get(exit_code)

        if hint:
            return hint

        # Check stderr for common patterns
        if stderr:
            stderr_lower = stderr.lower()

            if "not found" in stderr_lower:
                return self._get_install_hint(tool)

            if "permission denied" in stderr_lower:
                return f"Check file permissions or run: chmod +x $(which {tool})"

            if "out of memory" in stderr_lower or "memory" in stderr_lower:
                return "Try reducing input size or increasing system memory"

            if "syntax error" in stderr_lower:
                return "Check input syntax"

        return f"Check {tool} logs or run: {tool} --help"

    def _get_install_hint(self, tool: str) -> str:
        """Get installation hint for tool."""
        try:
            from alphaswarm_sol.core.tiers import DEPENDENCIES

            dep = DEPENDENCIES.get(tool)
            if dep and dep.install_hint:
                return dep.install_hint
        except ImportError:
            pass

        return f"Install {tool} and ensure it's in PATH"


# Convenience functions


def run_tool_safely(
    command: List[str],
    timeout: int = 60,
    **kwargs,
) -> ToolResult:
    """
    Run a tool with default safety settings.

    Args:
        command: Command and arguments
        timeout: Timeout in seconds
        **kwargs: Additional arguments for ToolRunner.run

    Returns:
        ToolResult
    """
    runner = ToolRunner(timeout=timeout)
    return runner.run(command, **kwargs)


def run_slither(
    target: Path,
    timeout: int = 120,
    extra_args: Optional[List[str]] = None,
) -> ToolResult:
    """
    Run Slither with safe defaults.

    Args:
        target: Target file or directory
        timeout: Timeout in seconds
        extra_args: Additional Slither arguments

    Returns:
        ToolResult
    """
    command = ["slither", "--json", "-", str(target)]
    if extra_args:
        command.extend(extra_args)

    runner = ToolRunner(timeout=timeout)
    return runner.run(command)


def run_aderyn(
    target: Path,
    timeout: int = 60,
    extra_args: Optional[List[str]] = None,
) -> ToolResult:
    """
    Run Aderyn with safe defaults.

    Args:
        target: Target file or directory
        timeout: Timeout in seconds
        extra_args: Additional Aderyn arguments

    Returns:
        ToolResult
    """
    command = ["aderyn", str(target)]
    if extra_args:
        command.extend(extra_args)

    runner = ToolRunner(timeout=timeout)
    return runner.run(command)
