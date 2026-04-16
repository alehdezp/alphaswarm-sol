"""Tests for idempotency and retry/backoff functionality.

Phase 07.1.1-02: Production Orchestration Hardening

These tests validate:
- Idempotency key generation is deterministic
- Same key returns cached result without re-execution
- Retry attempts stop at max_retries
- Backoff delay values stay within configured bounds
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from alphaswarm_sol.orchestration.idempotency import (
    IdempotencyRecord,
    IdempotencyStatus,
    IdempotencyStore,
    RetryConfig,
    idempotent_execute,
)
from alphaswarm_sol.orchestration.handlers import (
    hash_payload,
    make_idempotency_key,
)
from alphaswarm_sol.tools.runner import (
    IdempotentRetryConfig,
    ToolResult,
    ToolRunner,
)


class TestIdempotencyKeyGeneration:
    """Test deterministic key generation."""

    def test_make_key_deterministic(self):
        """Same inputs always produce same key."""
        key1 = IdempotencyStore.make_key(
            pool_id="pool-1",
            bead_id="bead-1",
            action="tool",
            payload_hash="abc123",
        )
        key2 = IdempotencyStore.make_key(
            pool_id="pool-1",
            bead_id="bead-1",
            action="tool",
            payload_hash="abc123",
        )
        assert key1 == key2
        assert len(key1) == 16  # SHA256 prefix

    def test_make_key_different_inputs(self):
        """Different inputs produce different keys."""
        key1 = IdempotencyStore.make_key("pool-1", "bead-1", "tool", "abc")
        key2 = IdempotencyStore.make_key("pool-2", "bead-1", "tool", "abc")
        key3 = IdempotencyStore.make_key("pool-1", "bead-2", "tool", "abc")
        key4 = IdempotencyStore.make_key("pool-1", "bead-1", "agent", "abc")
        key5 = IdempotencyStore.make_key("pool-1", "bead-1", "tool", "def")

        keys = {key1, key2, key3, key4, key5}
        assert len(keys) == 5  # All unique

    def test_handler_make_key_consistency(self):
        """Handler make_idempotency_key matches store make_key."""
        store_key = IdempotencyStore.make_key("pool", "bead", "action", "hash")
        handler_key = make_idempotency_key("pool", "bead", "action", "hash")
        assert store_key == handler_key

    def test_hash_payload_deterministic(self):
        """Payload hashing is deterministic."""
        payload = {"a": 1, "b": [2, 3], "c": {"d": 4}}
        hash1 = hash_payload(payload)
        hash2 = hash_payload(payload)
        assert hash1 == hash2

    def test_hash_payload_order_independent(self):
        """Payload hash is independent of dict key order."""
        payload1 = {"a": 1, "b": 2}
        payload2 = {"b": 2, "a": 1}
        assert hash_payload(payload1) == hash_payload(payload2)


class TestIdempotencyStore:
    """Test IdempotencyStore persistence and caching."""

    def test_store_reserve_and_success(self, tmp_path):
        """Reserve key and record success."""
        store = IdempotencyStore(tmp_path / "pool-test")
        key = store.make_key("pool", "bead", "action", "hash")

        # Reserve should succeed
        assert store.reserve(key)

        # Double reserve should fail (already reserved)
        assert not store.reserve(key)

        # Record success
        store.record_success(key, {"result": 42})

        # Get cached result
        record = store.get(key)
        assert record is not None
        assert record.is_complete
        assert record.result == {"result": 42}

    def test_store_cached_result_no_reexecute(self, tmp_path):
        """Cached result prevents re-execution."""
        store = IdempotencyStore(tmp_path / "pool-test")
        key = store.make_key("pool", "bead", "action", "hash")

        # First execution
        store.reserve(key)
        store.record_success(key, "first_result")

        # Second attempt should not allow reserve
        assert not store.reserve(key)

        # Result should be cached
        record = store.get(key)
        assert record.result == "first_result"

    def test_store_persistence_across_restart(self, tmp_path):
        """Store persists across restarts."""
        pool_path = tmp_path / "pool-test"
        key = IdempotencyStore.make_key("pool", "bead", "action", "hash")

        # First instance
        store1 = IdempotencyStore(pool_path)
        store1.reserve(key)
        store1.record_success(key, {"value": 123})

        # New instance (simulating restart)
        store2 = IdempotencyStore(pool_path)
        record = store2.get(key)

        assert record is not None
        assert record.is_complete
        assert record.result == {"value": 123}

    def test_store_failure_is_retryable(self, tmp_path):
        """Failed (non-permanent) records allow retry."""
        store = IdempotencyStore(tmp_path / "pool-test")
        key = store.make_key("pool", "bead", "action", "hash")

        store.reserve(key)
        store.record_failure(key, "transient error", permanent=False)

        record = store.get(key)
        assert record.is_retryable
        assert not record.is_complete

        # Can re-reserve after transient failure
        assert store.reserve(key)

    def test_store_permanent_failure_not_retryable(self, tmp_path):
        """Permanent failures cannot be retried."""
        store = IdempotencyStore(tmp_path / "pool-test")
        key = store.make_key("pool", "bead", "action", "hash")

        store.reserve(key)
        store.record_failure(key, "permanent error", permanent=True)

        record = store.get(key)
        assert record.is_complete  # Permanent failure = complete
        assert not store.reserve(key)  # Cannot re-reserve

    def test_store_stats(self, tmp_path):
        """Store statistics are accurate."""
        store = IdempotencyStore(tmp_path / "pool-test")

        # Create various records
        for i in range(3):
            key = store.make_key("pool", f"bead-{i}", "action", "hash")
            store.reserve(key)
            store.record_success(key, i)

        key_fail = store.make_key("pool", "bead-fail", "action", "hash")
        store.reserve(key_fail)
        store.record_failure(key_fail, "error", permanent=False)

        stats = store.get_stats()
        assert stats["total"] == 4
        assert stats["success"] == 3
        assert stats["failure"] == 1


class TestRetryConfig:
    """Test retry configuration and backoff calculation."""

    def test_calculate_delay_exponential(self):
        """Delay follows exponential backoff."""
        config = RetryConfig(base_delay=1.0, max_delay=60.0, jitter=0.0)

        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 4.0
        assert config.calculate_delay(3) == 8.0

    def test_calculate_delay_bounded(self):
        """Delay is bounded by max_delay."""
        config = RetryConfig(base_delay=1.0, max_delay=10.0, jitter=0.0)

        assert config.calculate_delay(10) == 10.0  # Capped at max
        assert config.calculate_delay(20) == 10.0

    def test_calculate_delay_with_jitter(self):
        """Jitter adds randomness within bounds."""
        config = RetryConfig(base_delay=1.0, max_delay=60.0, jitter=0.25)

        delays = [config.calculate_delay(0) for _ in range(100)]

        # All delays should be >= base and <= base * (1 + jitter)
        assert all(1.0 <= d <= 1.25 for d in delays)

        # Should have variance (not all same)
        assert len(set(delays)) > 1

    def test_is_retryable_error(self):
        """Retryable error detection works."""
        config = RetryConfig()

        assert config.is_retryable_error("Connection timeout occurred")
        assert config.is_retryable_error("Rate limit exceeded")
        assert config.is_retryable_error("Service temporarily unavailable")
        assert config.is_retryable_error("Error 503 from server")
        assert config.is_retryable_error("HTTP 429 Too Many Requests")

        assert not config.is_retryable_error("Invalid API key")
        assert not config.is_retryable_error("Permission denied")
        assert not config.is_retryable_error("Syntax error in input")


class TestIdempotentExecute:
    """Test the idempotent_execute helper."""

    def test_returns_cached_result(self, tmp_path):
        """Returns cached result without re-execution."""
        store = IdempotencyStore(tmp_path / "pool")
        key = store.make_key("pool", "bead", "action", "hash")

        # Pre-populate cache
        store.reserve(key)
        store.record_success(key, "cached_value")

        # Mock function that should NOT be called
        mock_func = MagicMock(return_value="new_value")

        result = idempotent_execute(store, key, mock_func)

        assert result == "cached_value"
        mock_func.assert_not_called()

    def test_executes_and_caches(self, tmp_path):
        """Executes function and caches result."""
        store = IdempotencyStore(tmp_path / "pool")
        key = store.make_key("pool", "bead", "action", "hash")

        mock_func = MagicMock(return_value="new_value")

        result = idempotent_execute(store, key, mock_func)

        assert result == "new_value"
        mock_func.assert_called_once()

        # Verify cached
        record = store.get(key)
        assert record.result == "new_value"

    def test_retries_on_transient_failure(self, tmp_path):
        """Retries on transient errors up to max."""
        store = IdempotencyStore(tmp_path / "pool")
        key = store.make_key("pool", "bead", "action", "hash")

        attempt_count = 0

        def flaky_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise RuntimeError("timeout occurred")
            return "success_on_third"

        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=0.0)
        result = idempotent_execute(store, key, flaky_func, config)

        assert result == "success_on_third"
        assert attempt_count == 3

    def test_stops_at_max_retries(self, tmp_path):
        """Stops retrying after max_retries."""
        store = IdempotencyStore(tmp_path / "pool")
        key = store.make_key("pool", "bead", "action", "hash")

        attempt_count = 0

        def always_fails():
            nonlocal attempt_count
            attempt_count += 1
            raise RuntimeError("timeout occurred")

        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=0.0)

        with pytest.raises(RuntimeError, match="timeout"):
            idempotent_execute(store, key, always_fails, config)

        assert attempt_count == 3  # 1 initial + 2 retries

    def test_no_retry_on_permanent_error(self, tmp_path):
        """Does not retry on non-retryable errors."""
        store = IdempotencyStore(tmp_path / "pool")
        key = store.make_key("pool", "bead", "action", "hash")

        attempt_count = 0

        def permission_error():
            nonlocal attempt_count
            attempt_count += 1
            raise RuntimeError("Permission denied")

        config = RetryConfig(max_retries=3, base_delay=0.01)

        with pytest.raises(RuntimeError, match="Permission"):
            idempotent_execute(store, key, permission_error, config)

        assert attempt_count == 1  # No retries for permanent errors


class TestToolRunnerIdempotent:
    """Test ToolRunner idempotent execution."""

    def test_run_idempotent_returns_cached(self, tmp_path):
        """Returns cached ToolResult without re-execution."""
        pool_path = tmp_path / "pool"
        store = IdempotencyStore(pool_path)
        key = "test_key_123"

        # Pre-populate cache with a successful result
        store.reserve(key)
        store.record_success(key, {
            "success": True,
            "output": "cached output",
            "error": None,
            "exit_code": 0,
            "runtime_ms": 100,
            "recovery": None,
            "partial": False,
            "metadata": {"cached": True},
        })

        runner = ToolRunner(timeout=1)

        # This should NOT actually run the command
        result = runner.run_idempotent(
            command=["echo", "hello"],
            idempotency_key=key,
            pool_path=pool_path,
        )

        assert result.success
        assert result.output == "cached output"
        assert result.metadata.get("cached") is True

    def test_run_idempotent_executes_and_caches(self, tmp_path):
        """Executes command and caches result."""
        pool_path = tmp_path / "pool"
        runner = ToolRunner(timeout=5)
        key = "test_fresh_key"

        result = runner.run_idempotent(
            command=["echo", "hello world"],
            idempotency_key=key,
            pool_path=pool_path,
        )

        assert result.success
        assert "hello world" in result.output

        # Verify cached
        store = IdempotencyStore(pool_path)
        record = store.get(key)
        assert record is not None
        assert record.is_complete

    def test_run_idempotent_bounded_backoff(self, tmp_path):
        """Backoff delays stay within configured bounds."""
        config = IdempotentRetryConfig(
            max_retries=3,
            base_delay=0.1,
            max_delay=1.0,
            jitter=0.0,
        )

        delays = []
        for attempt in range(4):
            delay = config.calculate_delay(attempt)
            delays.append(delay)

        # Check exponential progression
        assert delays[0] == pytest.approx(0.1)
        assert delays[1] == pytest.approx(0.2)
        assert delays[2] == pytest.approx(0.4)
        assert delays[3] == pytest.approx(0.8)

        # All within bounds
        assert all(d <= config.max_delay for d in delays)


class TestIdempotencyIntegration:
    """Integration tests for full idempotency workflow."""

    def test_handler_key_with_store(self, tmp_path):
        """Handler-generated keys work with store."""
        pool_path = tmp_path / "pool"
        store = IdempotencyStore(pool_path)

        # Generate key using handler helper
        payload = {"tool": "slither", "target": "/path/to/contract.sol"}
        payload_hash = hash_payload(payload)
        key = make_idempotency_key(
            pool_id="audit-001",
            bead_id="VKG-042",
            action="tool:slither",
            payload_hash=payload_hash,
        )

        # Use with store
        assert store.reserve(key)
        store.record_success(key, {"findings": 5})

        # Verify retrieval
        record = store.get(key)
        assert record.result == {"findings": 5}

    def test_concurrent_reserve_protection(self, tmp_path):
        """Only one process can reserve a key."""
        pool_path = tmp_path / "pool"

        # Simulate two "processes" with separate store instances
        store1 = IdempotencyStore(pool_path)
        store2 = IdempotencyStore(pool_path)

        key = store1.make_key("pool", "bead", "action", "hash")

        # First reserve succeeds
        assert store1.reserve(key)

        # Reload store2 to see the new record
        store2 = IdempotencyStore(pool_path)

        # Second reserve fails (key is reserved)
        assert not store2.reserve(key)
