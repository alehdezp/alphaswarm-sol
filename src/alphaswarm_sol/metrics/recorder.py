"""High-level recorder for metric events.

Task 8.2a: Singleton recorder for convenient event recording.

Usage:
    from alphaswarm_sol.metrics.recorder import recorder

    # Record detection outcome
    recorder.detection(
        contract_id="test.sol",
        pattern_id="vm-001",
        function_name="withdraw",
        line_number=42,
        expected=True,
        detected=True
    )

    # Record timing
    recorder.timing(
        operation="scan",
        contract_id="test.sol",
        duration_seconds=2.5
    )
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .event_store import EventStore


class MetricsRecorder:
    """Singleton recorder for metric events.

    Provides a convenient API for recording events from anywhere in the codebase.
    Uses a singleton pattern to ensure all events go to the same store.
    """

    _instance: MetricsRecorder | None = None

    def __init__(self, storage_path: Path | str | None = None):
        """Initialize recorder.

        Args:
            storage_path: Override default storage path (for testing)
        """
        if storage_path is None:
            # Import here to avoid circular imports
            from ..config import METRICS_CONFIG

            storage_path = Path(METRICS_CONFIG.get("storage_path", ".vrs/metrics"))

        self.storage_path = Path(storage_path)
        self.store = EventStore(self.storage_path / "events")

    @classmethod
    def get_instance(cls, storage_path: Path | str | None = None) -> MetricsRecorder:
        """Get or create singleton instance.

        Args:
            storage_path: Override storage path (only used on first call)

        Returns:
            MetricsRecorder singleton instance
        """
        if cls._instance is None:
            cls._instance = cls(storage_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        cls._instance = None

    def detection(
        self,
        contract_id: str,
        pattern_id: str,
        function_name: str,
        line_number: int,
        expected: bool,
        detected: bool,
    ) -> str:
        """Record detection event.

        Args:
            contract_id: Contract identifier
            pattern_id: Pattern ID (e.g., "vm-001")
            function_name: Function where detection occurred
            line_number: Line number in source
            expected: Whether this was expected (from MANIFEST)
            detected: Whether AlphaSwarm detected it

        Returns:
            Event ID
        """
        return self.store.record_detection(
            contract_id=contract_id,
            pattern_id=pattern_id,
            function_name=function_name,
            line_number=line_number,
            expected=expected,
            detected=detected,
        )

    def timing(
        self,
        operation: str,
        contract_id: str,
        duration_seconds: float,
    ) -> str:
        """Record timing event.

        Args:
            operation: Operation type ("scan", "build_graph", "query")
            contract_id: Contract identifier
            duration_seconds: Duration in seconds

        Returns:
            Event ID
        """
        return self.store.record_timing(
            operation=operation,
            contract_id=contract_id,
            duration_seconds=duration_seconds,
        )

    def scaffold(
        self,
        finding_id: str,
        pattern_id: str,
        compiled: bool,
        error_message: str | None = None,
    ) -> str:
        """Record scaffold event.

        Args:
            finding_id: Finding identifier
            pattern_id: Pattern ID
            compiled: Whether scaffold compiled
            error_message: Error if compilation failed

        Returns:
            Event ID
        """
        return self.store.record_scaffold(
            finding_id=finding_id,
            pattern_id=pattern_id,
            compiled=compiled,
            error_message=error_message,
        )

    def verdict(
        self,
        finding_id: str,
        pattern_id: str,
        verdict: str,
        auto_resolved: bool,
        tokens_used: int,
    ) -> str:
        """Record verdict event.

        Args:
            finding_id: Finding identifier
            pattern_id: Pattern ID
            verdict: Verdict ("confirmed", "rejected", "uncertain")
            auto_resolved: Whether resolved without human escalation
            tokens_used: Number of tokens used

        Returns:
            Event ID
        """
        return self.store.record_verdict(
            finding_id=finding_id,
            pattern_id=pattern_id,
            verdict=verdict,
            auto_resolved=auto_resolved,
            tokens_used=tokens_used,
        )


def get_recorder(storage_path: Path | str | None = None) -> MetricsRecorder:
    """Get the global metrics recorder instance.

    Args:
        storage_path: Override storage path (only used on first call)

    Returns:
        MetricsRecorder singleton instance
    """
    return MetricsRecorder.get_instance(storage_path)


# Note: We don't create a global `recorder` instance at module level
# to avoid issues with circular imports. Instead, call get_recorder().
