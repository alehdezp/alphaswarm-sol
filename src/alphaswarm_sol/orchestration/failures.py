"""Failure taxonomy and recovery playbooks for orchestration (Phase 07.1.1-06).

Provides:
- FailureType enum classifying all orchestration failure modes
- FailureSeverity enum for impact assessment
- RecoveryAction enum for playbook actions
- FailureClassifier mapping exceptions/context to failure types
- RecoveryPlaybook mapping failure types to recovery strategies
- FailureMetadata for persistence and audit

Usage:
    from alphaswarm_sol.orchestration.failures import (
        FailureClassifier,
        RecoveryPlaybook,
        FailureType,
        RecoveryAction,
    )

    classifier = FailureClassifier()
    playbook = RecoveryPlaybook()

    try:
        handler(pool, beads)
    except Exception as e:
        # Classify the failure
        failure = classifier.classify(e, context={"pool_id": pool.id})

        # Get recovery action
        action = playbook.get_action(failure.failure_type)

        # Apply recovery
        if action.action == RecoveryAction.RETRY:
            # Retry with backoff
            pass
        elif action.action == RecoveryAction.SKIP:
            # Skip this item
            pass
"""

from __future__ import annotations

import logging
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Standard taxonomy of orchestration failure types.

    Categories:
    - TOOL_FAILURE: External tool errors (Slither, Aderyn, etc.)
    - AGENT_FAILURE: LLM agent errors (timeouts, rate limits, bad responses)
    - TIMEOUT: Operation exceeded time limit
    - VALIDATION: Data validation failures (schema, constraints)
    - STATE_CORRUPTION: Inconsistent or corrupted state
    - BACKPRESSURE: Queue full, resource exhaustion
    - UNKNOWN: Unclassified failures
    """

    TOOL_FAILURE = "tool_failure"
    AGENT_FAILURE = "agent_failure"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    STATE_CORRUPTION = "state_corruption"
    BACKPRESSURE = "backpressure"
    UNKNOWN = "unknown"


class FailureSeverity(Enum):
    """Severity levels for failures.

    Levels:
    - TRANSIENT: Temporary issue, likely to resolve on retry
    - DEGRADED: Partial functionality available
    - CRITICAL: Operation cannot proceed
    - FATAL: Pool/system integrity at risk
    """

    TRANSIENT = "transient"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FATAL = "fatal"


class RecoveryAction(Enum):
    """Recovery actions for failure playbooks.

    Actions:
    - RETRY: Retry the operation (with backoff)
    - PAUSE: Pause pool for manual intervention
    - SKIP: Skip this item and continue
    - ABORT: Abort the pool entirely
    - FALLBACK: Use fallback strategy
    - QUARANTINE: Isolate the item for later review
    """

    RETRY = "retry"
    PAUSE = "pause"
    SKIP = "skip"
    ABORT = "abort"
    FALLBACK = "fallback"
    QUARANTINE = "quarantine"


@dataclass
class FailureMetadata:
    """Metadata for a classified failure.

    Attributes:
        failure_type: Classified failure type
        severity: Failure severity level
        message: Human-readable error message
        exception_type: Type name of the original exception
        exception_message: Original exception message
        traceback: Full traceback (optional, for debugging)
        timestamp: When the failure occurred
        context: Additional context (pool_id, bead_id, etc.)
        attempt: Current attempt number (for retries)
        recovery_action: Recommended recovery action
    """

    failure_type: FailureType
    severity: FailureSeverity
    message: str
    exception_type: str = ""
    exception_message: str = ""
    traceback: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    context: Dict[str, Any] = field(default_factory=dict)
    attempt: int = 1
    recovery_action: Optional[RecoveryAction] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "failure_type": self.failure_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "traceback": self.traceback,
            "timestamp": self.timestamp,
            "context": self.context,
            "attempt": self.attempt,
            "recovery_action": self.recovery_action.value if self.recovery_action else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FailureMetadata":
        """Create from dictionary."""
        recovery = data.get("recovery_action")
        return cls(
            failure_type=FailureType(data["failure_type"]),
            severity=FailureSeverity(data["severity"]),
            message=data.get("message", ""),
            exception_type=data.get("exception_type", ""),
            exception_message=data.get("exception_message", ""),
            traceback=data.get("traceback", ""),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
            context=data.get("context", {}),
            attempt=data.get("attempt", 1),
            recovery_action=RecoveryAction(recovery) if recovery else None,
        )


@dataclass
class RecoveryPlaybookEntry:
    """Entry in the recovery playbook.

    Attributes:
        action: Primary recovery action
        max_attempts: Maximum retry attempts before escalation
        backoff_seconds: Initial backoff delay for retries
        backoff_multiplier: Multiplier for exponential backoff
        max_backoff_seconds: Maximum backoff delay
        escalation_action: Action to take if max_attempts exceeded
        requires_human: Whether human intervention is needed
        notes: Additional guidance for the recovery
    """

    action: RecoveryAction
    max_attempts: int = 3
    backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 60.0
    escalation_action: RecoveryAction = RecoveryAction.PAUSE
    requires_human: bool = False
    notes: str = ""

    def get_backoff_delay(self, attempt: int) -> float:
        """Calculate backoff delay for given attempt number.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        if attempt <= 1:
            return self.backoff_seconds
        delay = self.backoff_seconds * (self.backoff_multiplier ** (attempt - 1))
        return min(delay, self.max_backoff_seconds)

    def should_retry(self, attempt: int) -> bool:
        """Check if retry is appropriate for given attempt.

        Args:
            attempt: Current attempt number

        Returns:
            True if should retry, False if should escalate
        """
        return self.action == RecoveryAction.RETRY and attempt < self.max_attempts

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action": self.action.value,
            "max_attempts": self.max_attempts,
            "backoff_seconds": self.backoff_seconds,
            "backoff_multiplier": self.backoff_multiplier,
            "max_backoff_seconds": self.max_backoff_seconds,
            "escalation_action": self.escalation_action.value,
            "requires_human": self.requires_human,
            "notes": self.notes,
        }


class FailureClassifier:
    """Classifies exceptions and context into failure types.

    The classifier uses exception type matching and context analysis
    to determine the appropriate FailureType and FailureSeverity.

    Example:
        classifier = FailureClassifier()

        try:
            result = run_tool(...)
        except Exception as e:
            failure = classifier.classify(e, context={"tool": "slither"})
            print(f"Failure type: {failure.failure_type.value}")
    """

    # Exception type to failure type mapping
    EXCEPTION_MAP: Dict[str, FailureType] = {
        # Timeout-related
        "TimeoutError": FailureType.TIMEOUT,
        "asyncio.TimeoutError": FailureType.TIMEOUT,
        "concurrent.futures.TimeoutError": FailureType.TIMEOUT,
        "httpx.TimeoutException": FailureType.TIMEOUT,
        "requests.exceptions.Timeout": FailureType.TIMEOUT,

        # Validation-related
        "ValueError": FailureType.VALIDATION,
        "TypeError": FailureType.VALIDATION,
        "pydantic.ValidationError": FailureType.VALIDATION,
        "jsonschema.ValidationError": FailureType.VALIDATION,

        # State corruption indicators
        "KeyError": FailureType.STATE_CORRUPTION,
        "AttributeError": FailureType.STATE_CORRUPTION,
        "IndexError": FailureType.STATE_CORRUPTION,

        # Backpressure indicators
        "MemoryError": FailureType.BACKPRESSURE,
        "OSError": FailureType.BACKPRESSURE,
        "ResourceWarning": FailureType.BACKPRESSURE,
    }

    # Keywords in exception messages to help classify
    MESSAGE_KEYWORDS: Dict[str, FailureType] = {
        "timeout": FailureType.TIMEOUT,
        "timed out": FailureType.TIMEOUT,
        "rate limit": FailureType.AGENT_FAILURE,
        "rate_limit": FailureType.AGENT_FAILURE,
        "quota": FailureType.AGENT_FAILURE,
        "api error": FailureType.AGENT_FAILURE,
        "api_error": FailureType.AGENT_FAILURE,
        "model": FailureType.AGENT_FAILURE,
        "llm": FailureType.AGENT_FAILURE,
        "anthropic": FailureType.AGENT_FAILURE,
        "openai": FailureType.AGENT_FAILURE,
        "slither": FailureType.TOOL_FAILURE,
        "aderyn": FailureType.TOOL_FAILURE,
        "mythril": FailureType.TOOL_FAILURE,
        "echidna": FailureType.TOOL_FAILURE,
        "foundry": FailureType.TOOL_FAILURE,
        "forge": FailureType.TOOL_FAILURE,
        "compilation": FailureType.TOOL_FAILURE,
        "compile": FailureType.TOOL_FAILURE,
        "solc": FailureType.TOOL_FAILURE,
        "backpressure": FailureType.BACKPRESSURE,
        "queue full": FailureType.BACKPRESSURE,
        "no space": FailureType.BACKPRESSURE,
        "disk full": FailureType.BACKPRESSURE,
        "memory": FailureType.BACKPRESSURE,
        "corrupt": FailureType.STATE_CORRUPTION,
        "inconsistent": FailureType.STATE_CORRUPTION,
        "mismatch": FailureType.STATE_CORRUPTION,
        "invalid state": FailureType.STATE_CORRUPTION,
    }

    # Context keys that indicate specific failure types
    CONTEXT_INDICATORS: Dict[str, FailureType] = {
        "tool": FailureType.TOOL_FAILURE,
        "tool_name": FailureType.TOOL_FAILURE,
        "agent": FailureType.AGENT_FAILURE,
        "agent_type": FailureType.AGENT_FAILURE,
        "model": FailureType.AGENT_FAILURE,
    }

    def __init__(
        self,
        include_traceback: bool = True,
        custom_mappings: Optional[Dict[str, FailureType]] = None,
    ):
        """Initialize classifier.

        Args:
            include_traceback: Whether to include full traceback in metadata
            custom_mappings: Additional exception type mappings
        """
        self.include_traceback = include_traceback
        self.exception_map = dict(self.EXCEPTION_MAP)
        if custom_mappings:
            self.exception_map.update(custom_mappings)

    def classify(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        attempt: int = 1,
    ) -> FailureMetadata:
        """Classify an exception into a failure metadata object.

        Args:
            exception: The exception to classify
            context: Additional context (pool_id, bead_id, action, etc.)
            attempt: Current attempt number

        Returns:
            FailureMetadata with classified type and severity
        """
        context = context or {}

        # Determine failure type
        failure_type = self._classify_type(exception, context)

        # Determine severity
        severity = self._classify_severity(exception, failure_type, context)

        # Build message
        message = self._build_message(exception, failure_type, context)

        # Get traceback
        tb = ""
        if self.include_traceback:
            tb = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))

        return FailureMetadata(
            failure_type=failure_type,
            severity=severity,
            message=message,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            traceback=tb,
            context=context,
            attempt=attempt,
        )

    def _classify_type(
        self,
        exception: Exception,
        context: Dict[str, Any],
    ) -> FailureType:
        """Classify the failure type from exception and context.

        Args:
            exception: The exception to classify
            context: Additional context

        Returns:
            Classified FailureType
        """
        exc_type_name = type(exception).__name__
        exc_module = type(exception).__module__
        full_type_name = f"{exc_module}.{exc_type_name}"

        # Check direct type mapping
        if exc_type_name in self.exception_map:
            return self.exception_map[exc_type_name]
        if full_type_name in self.exception_map:
            return self.exception_map[full_type_name]

        # Check context indicators
        for key, failure_type in self.CONTEXT_INDICATORS.items():
            if key in context:
                return failure_type

        # Check message keywords
        exc_message = str(exception).lower()
        for keyword, failure_type in self.MESSAGE_KEYWORDS.items():
            if keyword in exc_message:
                return failure_type

        # Check cause chain
        cause = exception.__cause__
        while cause:
            cause_type = type(cause).__name__
            if cause_type in self.exception_map:
                return self.exception_map[cause_type]
            cause = cause.__cause__

        return FailureType.UNKNOWN

    def _classify_severity(
        self,
        exception: Exception,
        failure_type: FailureType,
        context: Dict[str, Any],
    ) -> FailureSeverity:
        """Classify the severity of a failure.

        Args:
            exception: The exception
            failure_type: Already-classified failure type
            context: Additional context

        Returns:
            Classified FailureSeverity
        """
        # State corruption is always critical
        if failure_type == FailureType.STATE_CORRUPTION:
            return FailureSeverity.CRITICAL

        # Timeouts and backpressure are usually transient
        if failure_type in (FailureType.TIMEOUT, FailureType.BACKPRESSURE):
            return FailureSeverity.TRANSIENT

        # Tool failures depend on which tool
        if failure_type == FailureType.TOOL_FAILURE:
            # Compilation failures are critical
            if "compile" in str(exception).lower():
                return FailureSeverity.CRITICAL
            return FailureSeverity.DEGRADED

        # Agent failures - rate limits are transient, others degraded
        if failure_type == FailureType.AGENT_FAILURE:
            if "rate" in str(exception).lower():
                return FailureSeverity.TRANSIENT
            return FailureSeverity.DEGRADED

        # Validation errors are degraded
        if failure_type == FailureType.VALIDATION:
            return FailureSeverity.DEGRADED

        # Unknown defaults to degraded
        return FailureSeverity.DEGRADED

    def _build_message(
        self,
        exception: Exception,
        failure_type: FailureType,
        context: Dict[str, Any],
    ) -> str:
        """Build a human-readable message for the failure.

        Args:
            exception: The exception
            failure_type: Classified failure type
            context: Additional context

        Returns:
            Human-readable error message
        """
        exc_type = type(exception).__name__
        exc_msg = str(exception)[:200]  # Truncate long messages

        parts = [f"{failure_type.value.upper()}: {exc_type}"]

        if exc_msg:
            parts.append(f"- {exc_msg}")

        # Add relevant context
        if "pool_id" in context:
            parts.append(f"(pool: {context['pool_id']})")
        if "bead_id" in context:
            parts.append(f"(bead: {context['bead_id']})")
        if "action" in context:
            parts.append(f"(action: {context['action']})")

        return " ".join(parts)


class RecoveryPlaybook:
    """Maps failure types to recovery strategies.

    Provides deterministic, bounded recovery actions for each failure type.
    The playbook ensures:
    - Recovery actions are consistent for each failure type
    - Retry attempts are bounded
    - Escalation paths are clear

    Example:
        playbook = RecoveryPlaybook()

        entry = playbook.get_entry(FailureType.TIMEOUT)
        if entry.should_retry(attempt=2):
            delay = entry.get_backoff_delay(attempt=2)
            time.sleep(delay)
            # retry
    """

    # Default playbook entries for each failure type
    DEFAULT_ENTRIES: Dict[FailureType, RecoveryPlaybookEntry] = {
        FailureType.TOOL_FAILURE: RecoveryPlaybookEntry(
            action=RecoveryAction.RETRY,
            max_attempts=3,
            backoff_seconds=5.0,
            backoff_multiplier=2.0,
            escalation_action=RecoveryAction.SKIP,
            notes="Tool failures often resolve on retry. Skip if persistent.",
        ),
        FailureType.AGENT_FAILURE: RecoveryPlaybookEntry(
            action=RecoveryAction.RETRY,
            max_attempts=5,
            backoff_seconds=10.0,
            backoff_multiplier=2.0,
            max_backoff_seconds=120.0,
            escalation_action=RecoveryAction.PAUSE,
            notes="Agent failures may be rate limits. Longer backoff helps.",
        ),
        FailureType.TIMEOUT: RecoveryPlaybookEntry(
            action=RecoveryAction.RETRY,
            max_attempts=2,
            backoff_seconds=30.0,
            backoff_multiplier=1.5,
            escalation_action=RecoveryAction.SKIP,
            notes="Timeouts may indicate resource issues. Quick escalation.",
        ),
        FailureType.VALIDATION: RecoveryPlaybookEntry(
            action=RecoveryAction.QUARANTINE,
            max_attempts=1,
            escalation_action=RecoveryAction.SKIP,
            requires_human=True,
            notes="Validation errors need human review of the data.",
        ),
        FailureType.STATE_CORRUPTION: RecoveryPlaybookEntry(
            action=RecoveryAction.ABORT,
            max_attempts=1,
            escalation_action=RecoveryAction.ABORT,
            requires_human=True,
            notes="State corruption is fatal. Requires investigation.",
        ),
        FailureType.BACKPRESSURE: RecoveryPlaybookEntry(
            action=RecoveryAction.PAUSE,
            max_attempts=1,
            backoff_seconds=60.0,
            escalation_action=RecoveryAction.PAUSE,
            notes="Backpressure means system overloaded. Pause and wait.",
        ),
        FailureType.UNKNOWN: RecoveryPlaybookEntry(
            action=RecoveryAction.RETRY,
            max_attempts=2,
            backoff_seconds=5.0,
            escalation_action=RecoveryAction.QUARANTINE,
            requires_human=True,
            notes="Unknown failures need investigation after retry.",
        ),
    }

    def __init__(
        self,
        custom_entries: Optional[Dict[FailureType, RecoveryPlaybookEntry]] = None,
    ):
        """Initialize playbook.

        Args:
            custom_entries: Override default entries for specific failure types
        """
        self.entries = dict(self.DEFAULT_ENTRIES)
        if custom_entries:
            self.entries.update(custom_entries)

    def get_entry(self, failure_type: FailureType) -> RecoveryPlaybookEntry:
        """Get playbook entry for a failure type.

        Args:
            failure_type: The failure type

        Returns:
            RecoveryPlaybookEntry with recovery strategy
        """
        return self.entries.get(failure_type, self.entries[FailureType.UNKNOWN])

    def get_action(
        self,
        failure_type: FailureType,
        attempt: int = 1,
    ) -> RecoveryAction:
        """Get the recommended action for a failure.

        For RETRY actions:
        - Returns RETRY if attempt < max_attempts
        - Returns escalation_action if max_attempts exceeded

        For non-RETRY actions (SKIP, PAUSE, ABORT, QUARANTINE, FALLBACK):
        - Returns the action directly (no retry logic)

        Args:
            failure_type: The failure type
            attempt: Current attempt number

        Returns:
            RecoveryAction to take
        """
        entry = self.get_entry(failure_type)

        # Non-RETRY actions are immediate
        if entry.action != RecoveryAction.RETRY:
            return entry.action

        # RETRY action: check attempt count
        if attempt < entry.max_attempts:
            return RecoveryAction.RETRY
        return entry.escalation_action

    def apply_recovery(
        self,
        failure: FailureMetadata,
        on_retry: Optional[Callable[[], Any]] = None,
        on_pause: Optional[Callable[[], Any]] = None,
        on_skip: Optional[Callable[[], Any]] = None,
        on_abort: Optional[Callable[[], Any]] = None,
        on_quarantine: Optional[Callable[[], Any]] = None,
        on_fallback: Optional[Callable[[], Any]] = None,
    ) -> bool:
        """Apply recovery strategy for a failure.

        This is a convenience method that:
        1. Gets the appropriate action for the failure
        2. Applies backoff delay if retrying
        3. Calls the corresponding callback

        Args:
            failure: The failure metadata
            on_retry: Callback for retry action
            on_pause: Callback for pause action
            on_skip: Callback for skip action
            on_abort: Callback for abort action
            on_quarantine: Callback for quarantine action
            on_fallback: Callback for fallback action

        Returns:
            True if recovery was applied, False if no callback provided
        """
        entry = self.get_entry(failure.failure_type)
        action = self.get_action(failure.failure_type, failure.attempt)

        # Update failure metadata with action
        failure.recovery_action = action

        # Apply backoff for retries
        if action == RecoveryAction.RETRY:
            delay = entry.get_backoff_delay(failure.attempt)
            logger.info(
                f"Recovery: RETRY for {failure.failure_type.value} "
                f"(attempt {failure.attempt}, delay {delay}s)"
            )
            time.sleep(delay)
            if on_retry:
                on_retry()
                return True

        elif action == RecoveryAction.PAUSE:
            logger.warning(f"Recovery: PAUSE for {failure.failure_type.value}")
            if on_pause:
                on_pause()
                return True

        elif action == RecoveryAction.SKIP:
            logger.warning(f"Recovery: SKIP for {failure.failure_type.value}")
            if on_skip:
                on_skip()
                return True

        elif action == RecoveryAction.ABORT:
            logger.error(f"Recovery: ABORT for {failure.failure_type.value}")
            if on_abort:
                on_abort()
                return True

        elif action == RecoveryAction.QUARANTINE:
            logger.warning(f"Recovery: QUARANTINE for {failure.failure_type.value}")
            if on_quarantine:
                on_quarantine()
                return True

        elif action == RecoveryAction.FALLBACK:
            logger.info(f"Recovery: FALLBACK for {failure.failure_type.value}")
            if on_fallback:
                on_fallback()
                return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert playbook to dictionary for serialization."""
        return {
            failure_type.value: entry.to_dict()
            for failure_type, entry in self.entries.items()
        }


# Convenience functions

def classify_failure(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    attempt: int = 1,
) -> FailureMetadata:
    """Classify a failure using the default classifier.

    Args:
        exception: The exception to classify
        context: Additional context
        attempt: Current attempt number

    Returns:
        FailureMetadata
    """
    classifier = FailureClassifier()
    return classifier.classify(exception, context, attempt)


def get_recovery_action(
    failure_type: FailureType,
    attempt: int = 1,
) -> RecoveryAction:
    """Get recovery action using the default playbook.

    Args:
        failure_type: The failure type
        attempt: Current attempt number

    Returns:
        RecoveryAction
    """
    playbook = RecoveryPlaybook()
    return playbook.get_action(failure_type, attempt)


# Export for module
__all__ = [
    # Enums
    "FailureType",
    "FailureSeverity",
    "RecoveryAction",
    # Data classes
    "FailureMetadata",
    "RecoveryPlaybookEntry",
    # Classes
    "FailureClassifier",
    "RecoveryPlaybook",
    # Convenience functions
    "classify_failure",
    "get_recovery_action",
]
