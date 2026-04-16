"""
Timeout Handling Utilities

Provides context managers and decorators for timeout enforcement.

Usage:
    # Context manager (Unix only)
    with timeout(30, "Analysis took too long"):
        slow_operation()

    # Decorator
    @with_timeout(30)
    def slow_function():
        ...

    # Cross-platform manager
    manager = TimeoutManager()
    result = manager.run_with_timeout(func, args, timeout_seconds=30)
"""

import signal
import functools
import threading
from typing import Callable, TypeVar, Any, Optional, Tuple
from contextlib import contextmanager
import platform

T = TypeVar("T")


class TimeoutError(Exception):
    """Raised when an operation times out."""

    def __init__(self, message: str = "Operation timed out", seconds: int = 0):
        super().__init__(message)
        self.seconds = seconds


@contextmanager
def timeout(seconds: int, message: str = "Operation timed out"):
    """
    Context manager for timeout enforcement.

    Note: Only works on Unix systems (uses SIGALRM).
    For Windows compatibility, use TimeoutManager.

    Usage:
        with timeout(30, "Analysis took too long"):
            slow_operation()

    Args:
        seconds: Timeout in seconds
        message: Error message if timeout occurs

    Raises:
        TimeoutError: If the operation times out
        NotImplementedError: On Windows
    """
    if platform.system() == "Windows":
        raise NotImplementedError(
            "Signal-based timeout not available on Windows. "
            "Use TimeoutManager instead."
        )

    def handler(signum, frame):
        raise TimeoutError(message, seconds)

    # Set up signal handler
    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Restore previous handler
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def with_timeout(seconds: int, message: Optional[str] = None):
    """
    Decorator for timeout enforcement.

    Note: Only works on Unix systems. For Windows, use TimeoutManager.

    Usage:
        @with_timeout(30)
        def slow_function():
            ...

    Args:
        seconds: Timeout in seconds
        message: Custom timeout message (default includes function name)

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            error_message = message or f"{func.__name__} timed out after {seconds}s"
            with timeout(seconds, error_message):
                return func(*args, **kwargs)

        return wrapper

    return decorator


class TimeoutManager:
    """
    Cross-platform timeout manager using threading.

    Works on both Unix and Windows systems.

    Usage:
        manager = TimeoutManager(default_timeout=60)
        result = manager.run_with_timeout(
            func,
            args=(arg1, arg2),
            timeout_seconds=30
        )
    """

    def __init__(self, default_timeout: int = 60):
        """
        Initialize timeout manager.

        Args:
            default_timeout: Default timeout in seconds
        """
        self.default_timeout = default_timeout

    def run_with_timeout(
        self,
        func: Callable[..., T],
        args: Tuple = (),
        kwargs: Optional[dict] = None,
        timeout_seconds: Optional[int] = None,
    ) -> T:
        """
        Run function with timeout using threading.

        Args:
            func: Function to run
            args: Positional arguments
            kwargs: Keyword arguments
            timeout_seconds: Timeout in seconds (default: default_timeout)

        Returns:
            Function result

        Raises:
            TimeoutError: If function doesn't complete in time
            Exception: Re-raised if function raises
        """
        kwargs = kwargs or {}
        timeout_seconds = timeout_seconds or self.default_timeout

        result_container = {"value": None, "exception": None}

        def target():
            try:
                result_container["value"] = func(*args, **kwargs)
            except Exception as e:
                result_container["exception"] = e

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout_seconds)

        if thread.is_alive():
            # Thread still running = timeout
            # Note: We can't forcefully kill the thread in Python
            # The thread will continue running in the background
            raise TimeoutError(
                f"Operation timed out after {timeout_seconds}s",
                timeout_seconds,
            )

        if result_container["exception"]:
            raise result_container["exception"]

        return result_container["value"]

    def run_async_with_timeout(
        self,
        func: Callable[..., T],
        args: Tuple = (),
        kwargs: Optional[dict] = None,
        timeout_seconds: Optional[int] = None,
        callback: Optional[Callable[[T], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
    ) -> threading.Thread:
        """
        Run function asynchronously with timeout.

        Returns immediately with a thread handle. Results are delivered
        via callbacks.

        Args:
            func: Function to run
            args: Positional arguments
            kwargs: Keyword arguments
            timeout_seconds: Timeout in seconds
            callback: Called with result on success
            error_callback: Called with exception on failure

        Returns:
            Thread handle (can be used for joining)
        """
        kwargs = kwargs or {}
        timeout_seconds = timeout_seconds or self.default_timeout

        def wrapper():
            try:
                result = self.run_with_timeout(
                    func,
                    args=args,
                    kwargs=kwargs,
                    timeout_seconds=timeout_seconds,
                )
                if callback:
                    callback(result)
            except Exception as e:
                if error_callback:
                    error_callback(e)

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        return thread


class TimeoutContext:
    """
    Reusable timeout context for multiple operations.

    Usage:
        ctx = TimeoutContext(30)

        # Each call has its own timeout
        result1 = ctx.run(func1)
        result2 = ctx.run(func2)
    """

    def __init__(self, default_timeout: int = 60):
        """
        Initialize timeout context.

        Args:
            default_timeout: Default timeout in seconds
        """
        self._manager = TimeoutManager(default_timeout)
        self.stats = {
            "total_calls": 0,
            "timeouts": 0,
            "errors": 0,
            "successes": 0,
        }

    def run(
        self,
        func: Callable[..., T],
        *args,
        timeout_seconds: Optional[int] = None,
        **kwargs,
    ) -> T:
        """
        Run function with timeout tracking.

        Args:
            func: Function to run
            *args: Positional arguments
            timeout_seconds: Override timeout
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            TimeoutError: On timeout
            Exception: On function error
        """
        self.stats["total_calls"] += 1

        try:
            result = self._manager.run_with_timeout(
                func,
                args=args,
                kwargs=kwargs,
                timeout_seconds=timeout_seconds,
            )
            self.stats["successes"] += 1
            return result

        except TimeoutError:
            self.stats["timeouts"] += 1
            raise

        except Exception:
            self.stats["errors"] += 1
            raise

    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "total_calls": 0,
            "timeouts": 0,
            "errors": 0,
            "successes": 0,
        }


# Convenience function
def run_with_timeout(
    func: Callable[..., T],
    timeout_seconds: int = 60,
    *args,
    **kwargs,
) -> T:
    """
    Run a function with timeout.

    Args:
        func: Function to run
        timeout_seconds: Timeout in seconds
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Function result

    Raises:
        TimeoutError: On timeout
    """
    manager = TimeoutManager()
    return manager.run_with_timeout(
        func,
        args=args,
        kwargs=kwargs,
        timeout_seconds=timeout_seconds,
    )
