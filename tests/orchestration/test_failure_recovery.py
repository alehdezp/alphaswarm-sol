"""Tests for failure taxonomy and recovery playbooks (Phase 07.1.1-06).

Tests:
1. FailureClassifier correctly maps exceptions to FailureType
2. RecoveryPlaybook enforces max attempts and provides deterministic actions
3. ExecutionLoop records failure metadata when recovery fails
4. Rules enforce failure metadata on FAILED pools
"""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from alphaswarm_sol.orchestration.failures import (
    FailureType,
    FailureSeverity,
    RecoveryAction,
    FailureMetadata,
    RecoveryPlaybookEntry,
    FailureClassifier,
    RecoveryPlaybook,
    classify_failure,
    get_recovery_action,
)
from alphaswarm_sol.orchestration.rules import (
    OrchestrationRules,
    RuleSeverity,
)
from alphaswarm_sol.orchestration.schemas import (
    Pool,
    PoolStatus,
    Scope,
)
from alphaswarm_sol.orchestration.loop import (
    ExecutionLoop,
    LoopConfig,
    LoopPhase,
    PhaseResult,
)
from alphaswarm_sol.orchestration.pool import PoolManager
from alphaswarm_sol.orchestration.router import RouteAction


class TestFailureClassifier:
    """Tests for FailureClassifier exception mapping."""

    def test_classify_timeout_error(self):
        """TimeoutError should classify as TIMEOUT."""
        classifier = FailureClassifier()
        failure = classifier.classify(TimeoutError("operation timed out"))

        assert failure.failure_type == FailureType.TIMEOUT
        assert failure.severity == FailureSeverity.TRANSIENT

    def test_classify_value_error(self):
        """ValueError should classify as VALIDATION."""
        classifier = FailureClassifier()
        failure = classifier.classify(ValueError("invalid input"))

        assert failure.failure_type == FailureType.VALIDATION
        assert failure.severity == FailureSeverity.DEGRADED

    def test_classify_key_error(self):
        """KeyError should classify as STATE_CORRUPTION."""
        classifier = FailureClassifier()
        failure = classifier.classify(KeyError("missing_key"))

        assert failure.failure_type == FailureType.STATE_CORRUPTION
        assert failure.severity == FailureSeverity.CRITICAL

    def test_classify_memory_error(self):
        """MemoryError should classify as BACKPRESSURE."""
        classifier = FailureClassifier()
        failure = classifier.classify(MemoryError("out of memory"))

        assert failure.failure_type == FailureType.BACKPRESSURE
        assert failure.severity == FailureSeverity.TRANSIENT

    def test_classify_unknown_exception(self):
        """Unknown exception should classify as UNKNOWN."""
        classifier = FailureClassifier()
        failure = classifier.classify(Exception("something went wrong"))

        assert failure.failure_type == FailureType.UNKNOWN
        assert failure.severity == FailureSeverity.DEGRADED

    def test_classify_by_message_keywords(self):
        """Exception message keywords should affect classification."""
        classifier = FailureClassifier()

        # Rate limit in message -> AGENT_FAILURE
        failure = classifier.classify(Exception("rate limit exceeded"))
        assert failure.failure_type == FailureType.AGENT_FAILURE

        # Slither in message -> TOOL_FAILURE
        failure = classifier.classify(Exception("slither failed to run"))
        assert failure.failure_type == FailureType.TOOL_FAILURE

        # Compile in message -> TOOL_FAILURE
        failure = classifier.classify(Exception("compilation failed"))
        assert failure.failure_type == FailureType.TOOL_FAILURE

    def test_classify_by_context(self):
        """Context indicators should affect classification."""
        classifier = FailureClassifier()

        # Tool context -> TOOL_FAILURE
        failure = classifier.classify(
            Exception("unknown error"),
            context={"tool": "slither"},
        )
        assert failure.failure_type == FailureType.TOOL_FAILURE

        # Agent context -> AGENT_FAILURE
        failure = classifier.classify(
            Exception("unknown error"),
            context={"agent": "attacker"},
        )
        assert failure.failure_type == FailureType.AGENT_FAILURE

    def test_classify_includes_context(self):
        """Classified failure should include provided context."""
        classifier = FailureClassifier()
        failure = classifier.classify(
            Exception("test"),
            context={"pool_id": "test-pool", "bead_id": "bead-001"},
        )

        assert failure.context["pool_id"] == "test-pool"
        assert failure.context["bead_id"] == "bead-001"

    def test_classify_includes_attempt(self):
        """Classified failure should include attempt number."""
        classifier = FailureClassifier()
        failure = classifier.classify(Exception("test"), attempt=3)

        assert failure.attempt == 3

    def test_failure_metadata_serialization(self):
        """FailureMetadata should serialize and deserialize correctly."""
        failure = FailureMetadata(
            failure_type=FailureType.TIMEOUT,
            severity=FailureSeverity.TRANSIENT,
            message="Test failure",
            exception_type="TimeoutError",
            exception_message="timed out",
            context={"pool_id": "test"},
            attempt=2,
            recovery_action=RecoveryAction.RETRY,
        )

        data = failure.to_dict()
        restored = FailureMetadata.from_dict(data)

        assert restored.failure_type == failure.failure_type
        assert restored.severity == failure.severity
        assert restored.message == failure.message
        assert restored.attempt == failure.attempt
        assert restored.recovery_action == failure.recovery_action


class TestRecoveryPlaybook:
    """Tests for RecoveryPlaybook action mapping."""

    def test_playbook_default_entries(self):
        """Playbook should have default entries for all failure types."""
        playbook = RecoveryPlaybook()

        for failure_type in FailureType:
            entry = playbook.get_entry(failure_type)
            assert entry is not None
            assert isinstance(entry, RecoveryPlaybookEntry)

    def test_playbook_tool_failure_retry(self):
        """TOOL_FAILURE should default to RETRY."""
        playbook = RecoveryPlaybook()
        action = playbook.get_action(FailureType.TOOL_FAILURE, attempt=1)

        assert action == RecoveryAction.RETRY

    def test_playbook_state_corruption_abort(self):
        """STATE_CORRUPTION should default to ABORT."""
        playbook = RecoveryPlaybook()
        action = playbook.get_action(FailureType.STATE_CORRUPTION, attempt=1)

        assert action == RecoveryAction.ABORT

    def test_playbook_backpressure_pause(self):
        """BACKPRESSURE should default to PAUSE."""
        playbook = RecoveryPlaybook()
        action = playbook.get_action(FailureType.BACKPRESSURE, attempt=1)

        assert action == RecoveryAction.PAUSE

    def test_playbook_validation_quarantine(self):
        """VALIDATION should use QUARANTINE action (non-RETRY action)."""
        playbook = RecoveryPlaybook()
        entry = playbook.get_entry(FailureType.VALIDATION)

        # Validate the entry is configured for quarantine
        assert entry.action == RecoveryAction.QUARANTINE
        # Non-RETRY actions return the action directly
        action = playbook.get_action(FailureType.VALIDATION, attempt=1)
        assert action == RecoveryAction.QUARANTINE

    def test_playbook_max_attempts_escalation(self):
        """Exceeding max_attempts should escalate to escalation_action."""
        playbook = RecoveryPlaybook()

        # TOOL_FAILURE: max 3 attempts, escalates to SKIP
        action1 = playbook.get_action(FailureType.TOOL_FAILURE, attempt=1)
        action2 = playbook.get_action(FailureType.TOOL_FAILURE, attempt=2)
        action3 = playbook.get_action(FailureType.TOOL_FAILURE, attempt=3)
        action4 = playbook.get_action(FailureType.TOOL_FAILURE, attempt=4)

        assert action1 == RecoveryAction.RETRY
        assert action2 == RecoveryAction.RETRY
        assert action3 == RecoveryAction.SKIP  # Escalated at attempt 3
        assert action4 == RecoveryAction.SKIP

    def test_playbook_backoff_delay(self):
        """Backoff delay should increase with attempts."""
        entry = RecoveryPlaybookEntry(
            action=RecoveryAction.RETRY,
            backoff_seconds=1.0,
            backoff_multiplier=2.0,
            max_backoff_seconds=10.0,
        )

        delay1 = entry.get_backoff_delay(1)
        delay2 = entry.get_backoff_delay(2)
        delay3 = entry.get_backoff_delay(3)

        assert delay1 == 1.0
        assert delay2 == 2.0
        assert delay3 == 4.0

    def test_playbook_backoff_capped(self):
        """Backoff delay should be capped at max_backoff_seconds."""
        entry = RecoveryPlaybookEntry(
            action=RecoveryAction.RETRY,
            backoff_seconds=1.0,
            backoff_multiplier=10.0,
            max_backoff_seconds=5.0,
        )

        delay = entry.get_backoff_delay(10)
        assert delay == 5.0

    def test_playbook_should_retry(self):
        """should_retry should return False when max_attempts exceeded."""
        entry = RecoveryPlaybookEntry(
            action=RecoveryAction.RETRY,
            max_attempts=3,
        )

        assert entry.should_retry(1) is True
        assert entry.should_retry(2) is True
        assert entry.should_retry(3) is False
        assert entry.should_retry(4) is False

    def test_playbook_custom_entries(self):
        """Custom entries should override defaults."""
        custom_entry = RecoveryPlaybookEntry(
            action=RecoveryAction.SKIP,
            max_attempts=5,  # Higher max so attempt 1 doesn't escalate
        )
        playbook = RecoveryPlaybook(custom_entries={
            FailureType.TIMEOUT: custom_entry,
        })

        action = playbook.get_action(FailureType.TIMEOUT, attempt=1)
        assert action == RecoveryAction.SKIP

    def test_playbook_deterministic(self):
        """Playbook actions should be deterministic for same inputs."""
        playbook = RecoveryPlaybook()

        # Same inputs should always produce same outputs
        for _ in range(10):
            action = playbook.get_action(FailureType.TOOL_FAILURE, attempt=2)
            assert action == RecoveryAction.RETRY


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_classify_failure(self):
        """classify_failure should use default classifier."""
        failure = classify_failure(TimeoutError("test"))
        assert failure.failure_type == FailureType.TIMEOUT

    def test_get_recovery_action(self):
        """get_recovery_action should use default playbook."""
        action = get_recovery_action(FailureType.BACKPRESSURE)
        assert action == RecoveryAction.PAUSE


class TestRulesFailureMetadata:
    """Tests for orchestration rules around failure metadata."""

    def test_failed_pool_requires_failure_type(self):
        """FAILED pool should have failure_type in metadata."""
        rules = OrchestrationRules()
        pool = Pool(
            id="test-pool",
            scope=Scope(files=["test.sol"]),
            status=PoolStatus.FAILED,
            metadata={"failure_reason": "test failure"},
        )

        violations = rules.check_pool_rules(pool)

        # Should have violation for missing failure_type
        type_violations = [v for v in violations if v.rule_id == "P-04a"]
        assert len(type_violations) == 1
        assert type_violations[0].severity == RuleSeverity.WARNING

    def test_failed_pool_with_full_metadata_passes(self):
        """FAILED pool with all failure metadata should pass rules."""
        rules = OrchestrationRules()
        pool = Pool(
            id="test-pool",
            scope=Scope(files=["test.sol"]),
            status=PoolStatus.FAILED,
            metadata={
                "failure_reason": "test failure",
                "failure_type": "timeout",
                "failure_details": {"severity": "transient"},
            },
        )

        violations = rules.check_pool_rules(pool)

        # Should not have failure-related violations
        failure_violations = [v for v in violations if v.rule_id.startswith("P-04")]
        assert len(failure_violations) == 0


class TestLoopFailureRecovery:
    """Tests for ExecutionLoop failure recovery integration."""

    @pytest.fixture
    def temp_pool_dir(self):
        """Create temporary directory for pool storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_pool_dir):
        """Create PoolManager with temp storage."""
        return PoolManager(temp_pool_dir)

    @pytest.fixture
    def loop(self, manager):
        """Create ExecutionLoop with recovery enabled."""
        config = LoopConfig(
            use_queue=False,
            enable_recovery=True,
            max_recovery_attempts=3,
            max_iterations=10,
        )
        return ExecutionLoop(manager, config)

    def test_loop_classifies_handler_failure(self, loop, manager):
        """Loop should classify handler failures."""
        # Create pool
        pool = manager.create_pool(scope=Scope(files=["test.sol"]))

        # Register failing handler
        call_count = 0

        def failing_handler(pool, beads):
            nonlocal call_count
            call_count += 1
            raise TimeoutError("handler timed out")

        loop.register_handler(RouteAction.BUILD_GRAPH, failing_handler)

        # Run should eventually fail after max attempts
        result = loop.run(pool.id)

        # Should have attempted recovery
        assert call_count > 1  # Retried at least once

        # Pool should have failure metadata
        updated_pool = manager.get_pool(pool.id)
        assert "last_failure" in updated_pool.metadata
        assert updated_pool.metadata["last_failure"]["failure_type"] == "timeout"

    def test_loop_persists_failure_history(self, loop, manager):
        """Loop should persist failure history."""
        pool = manager.create_pool(scope=Scope(files=["test.sol"]))

        attempts = []

        def failing_handler(pool, beads):
            attempts.append(1)
            raise ValueError("validation failed")

        loop.register_handler(RouteAction.BUILD_GRAPH, failing_handler)

        # Run loop
        result = loop.run(pool.id)

        # Check failure history
        updated_pool = manager.get_pool(pool.id)
        assert "failure_history" in updated_pool.metadata
        assert len(updated_pool.metadata["failure_history"]) > 0

    def test_loop_recovery_disabled(self, manager):
        """Loop with recovery disabled should fail immediately."""
        config = LoopConfig(
            use_queue=False,
            enable_recovery=False,
        )
        loop = ExecutionLoop(manager, config)
        pool = manager.create_pool(scope=Scope(files=["test.sol"]))

        call_count = 0

        def failing_handler(pool, beads):
            nonlocal call_count
            call_count += 1
            raise Exception("test error")

        loop.register_handler(RouteAction.BUILD_GRAPH, failing_handler)

        result = loop.run(pool.id)

        assert call_count == 1  # No retry
        assert result.success is False

    def test_loop_state_corruption_aborts(self, loop, manager):
        """STATE_CORRUPTION failures should abort immediately."""
        pool = manager.create_pool(scope=Scope(files=["test.sol"]))

        def corrupt_handler(pool, beads):
            raise KeyError("missing state key")

        loop.register_handler(RouteAction.BUILD_GRAPH, corrupt_handler)

        result = loop.run(pool.id)

        # Should have aborted
        assert result.success is False
        assert "failure" in result.artifacts

        # Pool should be failed
        updated_pool = manager.get_pool(pool.id)
        assert updated_pool.status == PoolStatus.FAILED
        assert updated_pool.metadata.get("failure_type") == "state_corruption"

    def test_loop_backpressure_pauses(self, loop, manager):
        """BACKPRESSURE failures should pause the pool."""
        pool = manager.create_pool(scope=Scope(files=["test.sol"]))

        def memory_handler(pool, beads):
            raise MemoryError("out of memory")

        loop.register_handler(RouteAction.BUILD_GRAPH, memory_handler)

        result = loop.run(pool.id)

        # Should have paused with checkpoint
        assert result.checkpoint is True
        assert "failure" in result.artifacts

        # Pool should be paused
        updated_pool = manager.get_pool(pool.id)
        assert updated_pool.status == PoolStatus.PAUSED

    def test_loop_clears_attempts_on_success(self, loop, manager):
        """Successful execution should clear recovery attempts."""
        pool = manager.create_pool(scope=Scope(files=["test.sol"]))

        fail_first = True

        def sometimes_failing_handler(pool, beads):
            nonlocal fail_first
            if fail_first:
                fail_first = False
                raise TimeoutError("first attempt fails")
            return PhaseResult(success=True, phase=LoopPhase.INTAKE, message="ok")

        loop.register_handler(RouteAction.BUILD_GRAPH, sometimes_failing_handler)

        # Register wait handler for next phase
        loop.register_handler(RouteAction.WAIT, lambda p, b: PhaseResult(
            success=True, phase=LoopPhase.INTAKE, message="waiting"
        ))

        # Run should succeed after retry
        result = loop.run(pool.id)

        # Recovery attempts should be cleared
        assert pool.id not in loop._recovery_attempts


class TestFailureMetadataAudit:
    """Tests for failure metadata persistence for audits."""

    def test_failure_metadata_has_all_fields(self):
        """FailureMetadata should include all audit-required fields."""
        classifier = FailureClassifier(include_traceback=True)

        try:
            raise ValueError("test error")
        except ValueError as e:
            failure = classifier.classify(e, context={"pool_id": "test"})

        data = failure.to_dict()

        # Required audit fields
        assert "failure_type" in data
        assert "severity" in data
        assert "message" in data
        assert "exception_type" in data
        assert "exception_message" in data
        assert "timestamp" in data
        assert "context" in data
        assert "attempt" in data

        # Should have traceback when enabled
        assert "traceback" in data
        assert len(data["traceback"]) > 0

    def test_failure_metadata_timestamp_format(self):
        """Timestamp should be ISO 8601 format."""
        failure = FailureMetadata(
            failure_type=FailureType.UNKNOWN,
            severity=FailureSeverity.DEGRADED,
            message="test",
        )

        # Should parse as ISO 8601
        from datetime import datetime
        datetime.fromisoformat(failure.timestamp)  # Should not raise
