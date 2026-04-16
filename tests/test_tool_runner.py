"""Tests for Isolated Tool Execution (Task 10.3).

Tests the ToolRunner, ToolResult, and timeout utilities for graceful
tool failure handling without crashing VKG.
"""

import os
import sys
import time
import platform
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import threading

from alphaswarm_sol.tools.runner import (
    ToolResult,
    ToolRunner,
    ToolExecutionError,
    run_tool_safely,
    run_slither,
    run_aderyn,
)
from alphaswarm_sol.tools.timeout import (
    TimeoutError,
    TimeoutManager,
    TimeoutContext,
    timeout,
    with_timeout,
    run_with_timeout,
)


class TestToolResult(unittest.TestCase):
    """Test ToolResult dataclass."""

    def test_success_result(self):
        """Successful result has correct properties."""
        result = ToolResult(
            success=True,
            output="test output",
            exit_code=0,
            runtime_ms=100,
        )

        self.assertTrue(result.success)
        self.assertTrue(result.ok)  # Alias
        self.assertEqual(result.output, "test output")
        self.assertEqual(result.exit_code, 0)
        self.assertIsNone(result.error)
        self.assertIsNone(result.recovery)
        self.assertFalse(result.partial)

    def test_failure_result(self):
        """Failed result has error information."""
        result = ToolResult(
            success=False,
            error="Command failed",
            exit_code=1,
            recovery="Check input syntax",
        )

        self.assertFalse(result.success)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Command failed")
        self.assertEqual(result.recovery, "Check input syntax")

    def test_partial_result(self):
        """Partial result indicates incomplete output."""
        result = ToolResult(
            success=False,
            output="partial...",
            error="Timeout",
            partial=True,
        )

        self.assertTrue(result.partial)
        self.assertIsNotNone(result.output)

    def test_to_dict(self):
        """ToolResult can be serialized."""
        result = ToolResult(
            success=True,
            output="test",
            exit_code=0,
            runtime_ms=50,
            metadata={"key": "value"},
        )

        data = result.to_dict()

        self.assertEqual(data["success"], True)
        self.assertEqual(data["output"], "test")
        self.assertEqual(data["exit_code"], 0)
        self.assertEqual(data["runtime_ms"], 50)
        self.assertEqual(data["metadata"]["key"], "value")

    def test_raise_for_status_success(self):
        """raise_for_status does nothing on success."""
        result = ToolResult(success=True, output="ok")
        # Should not raise
        result.raise_for_status()

    def test_raise_for_status_failure(self):
        """raise_for_status raises on failure."""
        result = ToolResult(success=False, error="Failed")

        with self.assertRaises(ToolExecutionError) as ctx:
            result.raise_for_status()

        self.assertIn("Failed", str(ctx.exception))
        self.assertEqual(ctx.exception.result, result)


class TestToolRunner(unittest.TestCase):
    """Test ToolRunner class."""

    def setUp(self):
        self.runner = ToolRunner(timeout=30)

    def test_run_echo_command(self):
        """Run simple echo command."""
        result = self.runner.run(["echo", "hello"])

        self.assertTrue(result.success)
        self.assertIn("hello", result.output)
        self.assertEqual(result.exit_code, 0)
        self.assertGreater(result.runtime_ms, 0)

    def test_run_python_version(self):
        """Run python --version."""
        result = self.runner.run([sys.executable, "--version"])

        self.assertTrue(result.success)
        self.assertIn("Python", result.output or result.error or "")
        self.assertEqual(result.exit_code, 0)

    def test_run_command_with_args(self):
        """Run command with arguments."""
        result = self.runner.run([sys.executable, "-c", "print('test')"])

        self.assertTrue(result.success)
        self.assertIn("test", result.output)

    def test_run_empty_command(self):
        """Empty command returns error."""
        result = self.runner.run([])

        self.assertFalse(result.success)
        self.assertIn("Empty command", result.error)

    def test_run_nonexistent_command(self):
        """Nonexistent command returns not found error."""
        result = self.runner.run(["nonexistent_tool_xyz123"])

        self.assertFalse(result.success)
        self.assertIn("not found", result.error.lower())
        self.assertTrue(result.metadata.get("not_found"))

    def test_run_failing_command(self):
        """Failing command returns error."""
        result = self.runner.run([sys.executable, "-c", "import sys; sys.exit(1)"])

        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, 1)

    def test_run_with_cwd(self):
        """Run command in specific directory."""
        result = self.runner.run(
            [sys.executable, "-c", "import os; print(os.getcwd())"],
            cwd=Path("/tmp"),
        )

        self.assertTrue(result.success)
        # On macOS, /tmp may resolve to /private/tmp
        self.assertTrue("/tmp" in result.output or "/private/tmp" in result.output)

    def test_run_with_env(self):
        """Run command with custom environment."""
        result = self.runner.run(
            [sys.executable, "-c", "import os; print(os.environ.get('TEST_VAR'))"],
            env={"TEST_VAR": "custom_value"},
        )

        self.assertTrue(result.success)
        self.assertIn("custom_value", result.output)

    def test_run_with_timeout(self):
        """Command exceeding timeout returns timeout error."""
        runner = ToolRunner(timeout=1)

        result = runner.run([sys.executable, "-c", "import time; time.sleep(10)"])

        self.assertFalse(result.success)
        self.assertIn("timed out", result.error.lower())
        self.assertTrue(result.metadata.get("timeout"))

    def test_timeout_includes_recovery_hint(self):
        """Timeout result includes recovery hint."""
        runner = ToolRunner(timeout=1)

        result = runner.run([sys.executable, "-c", "import time; time.sleep(10)"])

        self.assertIsNotNone(result.recovery)
        self.assertIn("timeout", result.recovery.lower())

    def test_run_captures_stderr(self):
        """Captures stderr on failure."""
        result = self.runner.run(
            [sys.executable, "-c", "import sys; sys.stderr.write('error msg')"]
        )

        # Even though exit code is 0, stderr should be in error for non-zero exits
        # This command has exit code 0, so we test differently
        result2 = self.runner.run(
            [sys.executable, "-c", "import sys; sys.stderr.write('error msg'); sys.exit(1)"]
        )

        self.assertFalse(result2.success)
        self.assertIn("error msg", result2.error)

    def test_output_truncation(self):
        """Large output is truncated."""
        runner = ToolRunner(timeout=30)
        # Temporarily reduce max output for testing
        original_max = runner.MAX_OUTPUT_SIZE
        runner.MAX_OUTPUT_SIZE = 100

        result = runner.run(
            [sys.executable, "-c", "print('x' * 1000)"]
        )

        runner.MAX_OUTPUT_SIZE = original_max

        self.assertTrue(result.success)
        self.assertLessEqual(len(result.output), 120)  # 100 + truncation message
        self.assertIn("truncated", result.output)

    def test_metadata_includes_command(self):
        """Result metadata includes command name."""
        result = self.runner.run(["echo", "test"])

        self.assertIn("command", result.metadata)
        self.assertEqual(result.metadata["command"], "echo")


class TestToolRunnerRecoveryHints(unittest.TestCase):
    """Test recovery hint generation."""

    def setUp(self):
        self.runner = ToolRunner()

    def test_slither_not_found_hint(self):
        """Slither not found gives install hint."""
        result = self.runner.run(["slither_nonexistent"])

        self.assertFalse(result.success)
        # Should have some recovery hint
        self.assertIsNotNone(result.recovery)

    def test_recovery_hint_from_stderr(self):
        """Recovery hint derived from stderr patterns."""
        # This tests the _get_recovery_hint method indirectly
        runner = ToolRunner()

        # Test permission denied pattern
        hint = runner._get_recovery_hint("test", 1, "permission denied for file")
        self.assertIn("permission", hint.lower())

        # Test syntax error pattern
        hint = runner._get_recovery_hint("test", 1, "syntax error at line 5")
        self.assertIn("syntax", hint.lower())


class TestToolRunnerRetry(unittest.TestCase):
    """Test retry functionality."""

    def test_retry_on_success(self):
        """Successful command doesn't retry."""
        runner = ToolRunner(max_retries=3, retry_delay=0.01)

        with patch.object(runner, 'run') as mock_run:
            mock_run.return_value = ToolResult(success=True, output="ok")

            result = runner.run_with_retry(["echo", "test"])

            self.assertTrue(result.success)
            mock_run.assert_called_once()

    def test_retry_on_transient_failure(self):
        """Transient failures are retried."""
        runner = ToolRunner(max_retries=2, retry_delay=0.01)

        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return ToolResult(success=False, error="connection timeout")
            return ToolResult(success=True, output="ok")

        with patch.object(runner, 'run', side_effect=mock_run):
            result = runner.run_with_retry(["test"])

            self.assertTrue(result.success)
            self.assertEqual(call_count, 2)

    def test_no_retry_on_permanent_failure(self):
        """Permanent failures are not retried."""
        runner = ToolRunner(max_retries=3, retry_delay=0.01)

        with patch.object(runner, 'run') as mock_run:
            mock_run.return_value = ToolResult(
                success=False,
                error="Syntax error in file",
            )

            result = runner.run_with_retry(["test"])

            self.assertFalse(result.success)
            mock_run.assert_called_once()  # No retries

    def test_max_retries_respected(self):
        """Retries stop at max_retries."""
        runner = ToolRunner(max_retries=2, retry_delay=0.01)

        with patch.object(runner, 'run') as mock_run:
            mock_run.return_value = ToolResult(
                success=False,
                error="connection timeout",  # Retryable
            )

            result = runner.run_with_retry(["test"])

            self.assertFalse(result.success)
            self.assertEqual(mock_run.call_count, 3)  # Initial + 2 retries


class TestToolRunnerIsolation(unittest.TestCase):
    """Test that tool failures don't crash VKG."""

    def setUp(self):
        self.runner = ToolRunner(timeout=5)

    def test_crash_isolation(self):
        """Crashing tool doesn't crash Python."""
        # Run a command that would crash/segfault
        result = self.runner.run(
            [sys.executable, "-c", "import os; os._exit(139)"]  # Simulate crash
        )

        # Should complete without raising exception
        self.assertFalse(result.success)
        # We should still be running

    def test_multiple_failures_isolated(self):
        """Multiple failing tools are handled independently."""
        results = []

        for _ in range(5):
            result = self.runner.run(["nonexistent_tool"])
            results.append(result)

        # All should fail gracefully
        self.assertEqual(len(results), 5)
        for r in results:
            self.assertFalse(r.success)

    def test_exception_in_tool_isolated(self):
        """Python exception in subprocess doesn't propagate."""
        result = self.runner.run(
            [sys.executable, "-c", "raise RuntimeError('test error')"]
        )

        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, 1)


class TestTimeoutContextManager(unittest.TestCase):
    """Test timeout context manager."""

    @unittest.skipIf(platform.system() == "Windows", "Signal-based timeout not available on Windows")
    def test_timeout_not_exceeded(self):
        """Code completing in time doesn't raise."""
        with timeout(5, "Test timeout"):
            time.sleep(0.1)
        # Should complete without exception

    @unittest.skipIf(platform.system() == "Windows", "Signal-based timeout not available on Windows")
    def test_timeout_exceeded(self):
        """Code exceeding timeout raises TimeoutError."""
        with self.assertRaises(TimeoutError) as ctx:
            with timeout(1, "Operation timed out"):
                time.sleep(10)

        self.assertIn("timed out", str(ctx.exception).lower())

    def test_timeout_on_windows_raises(self):
        """Timeout context manager raises NotImplementedError on Windows."""
        if platform.system() == "Windows":
            with self.assertRaises(NotImplementedError):
                with timeout(5, "Test"):
                    pass


class TestWithTimeoutDecorator(unittest.TestCase):
    """Test with_timeout decorator."""

    @unittest.skipIf(platform.system() == "Windows", "Signal-based timeout not available on Windows")
    def test_decorated_function_completes(self):
        """Decorated function completing in time returns result."""
        @with_timeout(5)
        def quick_func():
            return "done"

        result = quick_func()
        self.assertEqual(result, "done")

    @unittest.skipIf(platform.system() == "Windows", "Signal-based timeout not available on Windows")
    def test_decorated_function_timeout(self):
        """Decorated function exceeding timeout raises."""
        @with_timeout(1)
        def slow_func():
            time.sleep(10)
            return "done"

        with self.assertRaises(TimeoutError):
            slow_func()


class TestTimeoutManager(unittest.TestCase):
    """Test TimeoutManager for cross-platform timeout."""

    def test_run_completes_in_time(self):
        """Function completing in time returns result."""
        manager = TimeoutManager(default_timeout=5)

        def quick_func(x, y):
            return x + y

        result = manager.run_with_timeout(quick_func, args=(1, 2))
        self.assertEqual(result, 3)

    def test_run_exceeds_timeout(self):
        """Function exceeding timeout raises TimeoutError."""
        manager = TimeoutManager(default_timeout=1)

        def slow_func():
            time.sleep(10)
            return "done"

        with self.assertRaises(TimeoutError):
            manager.run_with_timeout(slow_func)

    def test_run_with_kwargs(self):
        """Function receives kwargs correctly."""
        manager = TimeoutManager()

        def func_with_kwargs(a, b=10):
            return a * b

        result = manager.run_with_timeout(
            func_with_kwargs,
            args=(5,),
            kwargs={"b": 3},
            timeout_seconds=5,
        )
        self.assertEqual(result, 15)

    def test_exception_in_function_propagates(self):
        """Exception in function is re-raised."""
        manager = TimeoutManager()

        def failing_func():
            raise ValueError("test error")

        with self.assertRaises(ValueError) as ctx:
            manager.run_with_timeout(failing_func, timeout_seconds=5)

        self.assertEqual(str(ctx.exception), "test error")

    def test_async_with_timeout_callback(self):
        """Async execution calls callback on success."""
        manager = TimeoutManager()
        results = []

        def success_callback(result):
            results.append(result)

        def quick_func():
            return "async done"

        thread = manager.run_async_with_timeout(
            quick_func,
            timeout_seconds=5,
            callback=success_callback,
        )

        thread.join(timeout=2)

        self.assertEqual(results, ["async done"])

    def test_async_with_timeout_error_callback(self):
        """Async execution calls error_callback on failure."""
        manager = TimeoutManager()
        errors = []

        def error_callback(e):
            errors.append(e)

        def failing_func():
            raise RuntimeError("async error")

        thread = manager.run_async_with_timeout(
            failing_func,
            timeout_seconds=5,
            error_callback=error_callback,
        )

        thread.join(timeout=2)

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], RuntimeError)


class TestTimeoutContext(unittest.TestCase):
    """Test TimeoutContext for reusable timeout operations."""

    def test_run_tracks_stats(self):
        """TimeoutContext tracks execution statistics."""
        ctx = TimeoutContext(default_timeout=5)

        def quick_func():
            return "ok"

        ctx.run(quick_func)
        ctx.run(quick_func)

        self.assertEqual(ctx.stats["total_calls"], 2)
        self.assertEqual(ctx.stats["successes"], 2)
        self.assertEqual(ctx.stats["timeouts"], 0)
        self.assertEqual(ctx.stats["errors"], 0)

    def test_run_tracks_timeouts(self):
        """TimeoutContext counts timeouts."""
        ctx = TimeoutContext(default_timeout=1)

        def slow_func():
            time.sleep(10)

        try:
            ctx.run(slow_func)
        except TimeoutError:
            pass

        self.assertEqual(ctx.stats["timeouts"], 1)
        self.assertEqual(ctx.stats["successes"], 0)

    def test_run_tracks_errors(self):
        """TimeoutContext counts errors."""
        ctx = TimeoutContext()

        def failing_func():
            raise ValueError("test")

        try:
            ctx.run(failing_func, timeout_seconds=5)
        except ValueError:
            pass

        self.assertEqual(ctx.stats["errors"], 1)
        self.assertEqual(ctx.stats["successes"], 0)

    def test_reset_stats(self):
        """reset_stats clears all counters."""
        ctx = TimeoutContext()
        ctx.stats["total_calls"] = 10
        ctx.stats["successes"] = 5

        ctx.reset_stats()

        self.assertEqual(ctx.stats["total_calls"], 0)
        self.assertEqual(ctx.stats["successes"], 0)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def test_run_tool_safely(self):
        """run_tool_safely wraps ToolRunner."""
        result = run_tool_safely(["echo", "test"])

        self.assertTrue(result.success)
        self.assertIn("test", result.output)

    def test_run_tool_safely_with_timeout(self):
        """run_tool_safely respects timeout."""
        result = run_tool_safely(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            timeout=1,
        )

        self.assertFalse(result.success)
        self.assertIn("timed out", result.error.lower())

    def test_run_with_timeout_function(self):
        """run_with_timeout convenience function works."""
        def quick():
            return 42

        result = run_with_timeout(quick, timeout_seconds=5)
        self.assertEqual(result, 42)


class TestSlitherRunner(unittest.TestCase):
    """Test Slither-specific runner."""

    @patch('alphaswarm_sol.tools.runner.ToolRunner.run')
    def test_run_slither_basic(self, mock_run):
        """run_slither builds correct command."""
        mock_run.return_value = ToolResult(success=True, output="{}")

        run_slither(Path("/test/contract.sol"))

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("slither", args)
        self.assertIn("--json", args)
        self.assertIn("/test/contract.sol", args)

    @patch('alphaswarm_sol.tools.runner.ToolRunner.run')
    def test_run_slither_with_extra_args(self, mock_run):
        """run_slither passes extra arguments."""
        mock_run.return_value = ToolResult(success=True, output="{}")

        run_slither(Path("/test.sol"), extra_args=["--exclude-informational"])

        args = mock_run.call_args[0][0]
        self.assertIn("--exclude-informational", args)


class TestAderynRunner(unittest.TestCase):
    """Test Aderyn-specific runner."""

    @patch('alphaswarm_sol.tools.runner.ToolRunner.run')
    def test_run_aderyn_basic(self, mock_run):
        """run_aderyn builds correct command."""
        mock_run.return_value = ToolResult(success=True, output="{}")

        run_aderyn(Path("/test/contract.sol"))

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("aderyn", args)
        self.assertIn("/test/contract.sol", args)


class TestTimeoutErrorClass(unittest.TestCase):
    """Test TimeoutError exception class."""

    def test_timeout_error_message(self):
        """TimeoutError has correct message."""
        err = TimeoutError("Test timeout", 30)

        self.assertEqual(str(err), "Test timeout")
        self.assertEqual(err.seconds, 30)

    def test_timeout_error_default_seconds(self):
        """TimeoutError defaults seconds to 0."""
        err = TimeoutError("Test")

        self.assertEqual(err.seconds, 0)


class TestToolExecutionError(unittest.TestCase):
    """Test ToolExecutionError exception class."""

    def test_execution_error_includes_result(self):
        """ToolExecutionError includes the ToolResult."""
        result = ToolResult(success=False, error="test error")
        err = ToolExecutionError("Tool failed", result)

        self.assertIn("Tool failed", str(err))
        self.assertEqual(err.result, result)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and unusual inputs."""

    def setUp(self):
        self.runner = ToolRunner(timeout=5)

    def test_command_with_special_characters(self):
        """Commands with special characters work."""
        result = self.runner.run(
            [sys.executable, "-c", "print('hello world!')"]
        )

        self.assertTrue(result.success)
        self.assertIn("hello world!", result.output)

    def test_command_with_unicode(self):
        """Commands with unicode work."""
        result = self.runner.run(
            [sys.executable, "-c", "print('hello \u4e16\u754c')"]
        )

        self.assertTrue(result.success)

    def test_very_short_timeout(self):
        """Very short timeout still works."""
        runner = ToolRunner(timeout=1)
        result = runner.run(["echo", "quick"])

        # Should succeed for quick command
        self.assertTrue(result.success)

    def test_command_produces_no_output(self):
        """Command with no output handled correctly."""
        result = self.runner.run([sys.executable, "-c", "pass"])

        self.assertTrue(result.success)
        self.assertEqual(result.output, "")

    def test_concurrent_tool_runs(self):
        """Multiple concurrent tool runs don't interfere."""
        runner = ToolRunner(timeout=10)
        results = []
        errors = []

        def run_tool(idx):
            try:
                result = runner.run(
                    [sys.executable, "-c", f"print({idx})"]
                )
                results.append((idx, result))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run_tool, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 5)
        for idx, result in results:
            self.assertTrue(result.success)
            self.assertIn(str(idx), result.output)


if __name__ == "__main__":
    unittest.main()
