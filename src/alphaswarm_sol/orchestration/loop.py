"""Fixed execution loop for orchestration (ORCH-07).

Loop sequence:
  Intake -> Context -> Beads -> Execute -> Verify -> Integrate -> Complete

Each phase:
1. Check if ready
2. Execute phase work via handler
3. Persist state
4. Advance to next phase

The loop is deterministic - handlers are injected, loop just orchestrates.
No domain logic lives in the loop itself.

Phase 07.1.1-03: Work Queue Integration
    The execution loop now integrates with WorkQueue for:
    - Enqueuing route decisions instead of immediate execution
    - Respecting max_in_flight concurrency limits
    - Applying backpressure when queue is full (pausing pool)
    - Queue-driven work dispatch for predictable resource usage

Usage:
    from alphaswarm_sol.orchestration.loop import ExecutionLoop, LoopPhase, LoopConfig
    from alphaswarm_sol.orchestration.queue import QueueLimits

    manager = PoolManager(Path(".vrs/pools"))

    # With queue integration (default)
    limits = QueueLimits(max_in_flight=10, max_queue_depth=100)
    loop = ExecutionLoop(manager, queue_limits=limits)

    # Register handlers for each action
    loop.register_handler(RouteAction.BUILD_GRAPH, build_graph_handler)
    loop.register_handler(RouteAction.DETECT_PATTERNS, detect_patterns_handler)
    # ... register other handlers

    # Run until completion or checkpoint
    result = loop.run(pool_id)

    # Or run single phase for testing
    result = loop.run_single_phase(pool_id)

    # Resume from checkpoint
    result = loop.resume(pool_id)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .pool import PoolManager
from .router import RouteAction, RouteDecision, Router
from .schemas import Pool, PoolStatus
from .queue import WorkQueue, WorkItem, QueueLimits, BackpressureError
from .failures import (
    FailureClassifier,
    RecoveryPlaybook,
    FailureMetadata,
    FailureType,
    RecoveryAction,
)

logger = logging.getLogger(__name__)


class LoopPhase(Enum):
    """Execution loop phases matching pool status.

    These phases mirror PoolStatus but are specific to the loop's
    perspective of what phase is being executed.

    Usage:
        if result.phase == LoopPhase.EXECUTE:
            print("Loop is in execute phase")
    """

    INTAKE = "intake"
    CONTEXT = "context"
    BEADS = "beads"
    EXECUTE = "execute"
    VERIFY = "verify"
    INTEGRATE = "integrate"
    COMPLETE = "complete"


@dataclass
class PhaseResult:
    """Result of executing a phase.

    Attributes:
        success: Whether the phase completed successfully
        phase: Which phase this result is for
        next_phase: Next phase to execute (if success)
        message: Human-readable status message
        artifacts: Any artifacts produced by the phase
        checkpoint: True if loop should pause for human interaction

    Usage:
        result = PhaseResult(
            success=True,
            phase=LoopPhase.EXECUTE,
            message="Spawned 3 attacker agents",
            artifacts={"agent_ids": ["att-001", "att-002", "att-003"]}
        )
    """

    success: bool
    phase: LoopPhase
    next_phase: Optional[LoopPhase] = None
    message: str = ""
    artifacts: Dict[str, Any] = field(default_factory=dict)
    checkpoint: bool = False  # True if should pause for human


@dataclass
class LoopConfig:
    """Configuration for execution loop.

    Attributes:
        auto_advance: Automatically advance phases when ready
        pause_on_human_flag: Pause when human review is needed
        max_iterations: Safety limit to prevent infinite loops
        verbose: Enable verbose logging
        use_queue: Enable work queue for concurrency control (Phase 07.1.1-03)
        queue_limits: Limits for work queue (if use_queue=True)
        enable_recovery: Enable failure recovery (Phase 07.1.1-06)
        max_recovery_attempts: Maximum recovery attempts before failing pool

    Usage:
        config = LoopConfig(
            auto_advance=True,
            pause_on_human_flag=True,
            max_iterations=50,
            use_queue=True,
            queue_limits=QueueLimits(max_in_flight=10),
            enable_recovery=True,
        )
    """

    auto_advance: bool = True  # Automatically advance phases
    pause_on_human_flag: bool = True  # Pause when human review needed
    max_iterations: int = 100  # Safety limit
    verbose: bool = False
    use_queue: bool = True  # Enable work queue for concurrency control
    queue_limits: Optional[QueueLimits] = None  # Queue limits configuration
    enable_recovery: bool = True  # Enable failure recovery (Phase 07.1.1-06)
    max_recovery_attempts: int = 5  # Maximum recovery attempts before failing pool


# Type alias for handler functions
PhaseHandler = Callable[[Pool, List[str]], PhaseResult]


class ExecutionLoop:
    """Fixed execution loop that drives audit workflow.

    The loop:
    1. Gets current pool state
    2. Routes to appropriate action
    3. Executes action via handler
    4. Persists state
    5. Advances phase if ready
    6. Repeats until complete or checkpoint

    Handlers are injected - loop doesn't contain domain logic.
    This makes the loop testable and the domain logic swappable.

    Example:
        manager = PoolManager(Path(".vrs/pools"))
        loop = ExecutionLoop(manager)

        # Register handlers
        def build_graph_handler(pool, beads):
            # Build VKG graph
            return PhaseResult(success=True, phase=LoopPhase.INTAKE)

        loop.register_handler(RouteAction.BUILD_GRAPH, build_graph_handler)

        # Run loop
        result = loop.run(pool.id)
    """

    # Phase order for advancement - this is the fixed sequence
    PHASE_ORDER: List[LoopPhase] = [
        LoopPhase.INTAKE,
        LoopPhase.CONTEXT,
        LoopPhase.BEADS,
        LoopPhase.EXECUTE,
        LoopPhase.VERIFY,
        LoopPhase.INTEGRATE,
        LoopPhase.COMPLETE,
    ]

    def __init__(
        self,
        manager: PoolManager,
        config: Optional[LoopConfig] = None,
        queue_limits: Optional[QueueLimits] = None,
    ):
        """Initialize execution loop.

        Args:
            manager: Pool manager for persistence
            config: Loop configuration (uses defaults if not provided)
            queue_limits: Queue limits (shorthand for config.queue_limits)
        """
        self.manager = manager
        self.config = config or LoopConfig()
        self.router = Router()
        self._handlers: Dict[RouteAction, PhaseHandler] = {}

        # Phase 07.1.1-03: Work queue support
        # Use queue_limits from parameter or config
        if queue_limits:
            self.config.queue_limits = queue_limits
        elif self.config.queue_limits is None:
            self.config.queue_limits = QueueLimits()

        # Queue instances are created per-pool (see _get_queue)
        self._queues: Dict[str, WorkQueue] = {}

        # Phase 07.1.1-06: Failure recovery
        self._classifier = FailureClassifier()
        self._playbook = RecoveryPlaybook()
        self._recovery_attempts: Dict[str, int] = {}  # pool_id -> attempt count

    def register_handler(self, action: RouteAction, handler: PhaseHandler) -> None:
        """Register handler for routing action.

        Handlers are callables: (pool, beads) -> PhaseResult

        Args:
            action: RouteAction to handle
            handler: Callable that handles this action
        """
        self._handlers[action] = handler

    def _get_queue(self, pool_id: str) -> WorkQueue:
        """Get or create work queue for a pool.

        Phase 07.1.1-03: Work queues are per-pool to enable pool-level
        concurrency limits and backpressure.

        Args:
            pool_id: Pool identifier

        Returns:
            WorkQueue instance for the pool
        """
        if pool_id not in self._queues:
            pool_path = self.manager.storage.path / pool_id
            self._queues[pool_id] = WorkQueue(pool_path, self.config.queue_limits)
        return self._queues[pool_id]

    def enqueue(
        self,
        pool_id: str,
        decision: RouteDecision,
        payload_hash: str = "",
    ) -> bool:
        """Enqueue a routing decision for processing.

        Phase 07.1.1-03: Instead of immediate execution, enqueue work items
        to respect concurrency limits.

        Args:
            pool_id: Pool identifier
            decision: Route decision to enqueue
            payload_hash: Optional hash for deduplication

        Returns:
            True if enqueued, False if duplicate or backpressure

        Note:
            On BackpressureError, the pool is paused with reason=backpressure
        """
        if not self.config.use_queue:
            return False

        queue = self._get_queue(pool_id)

        # Create work items for each target bead (or one pool-level item)
        if decision.target_beads:
            for bead_id in decision.target_beads:
                item = WorkItem(
                    pool_id=pool_id,
                    bead_id=bead_id,
                    action=decision.action.value,
                    payload_hash=payload_hash,
                    metadata={"reason": decision.reason},
                )
                try:
                    queue.enqueue(item)
                except BackpressureError:
                    self._apply_backpressure(pool_id)
                    return False
        else:
            # Pool-level action (no specific beads)
            item = WorkItem(
                pool_id=pool_id,
                bead_id="*",
                action=decision.action.value,
                payload_hash=payload_hash,
                metadata={"reason": decision.reason},
            )
            try:
                queue.enqueue(item)
            except BackpressureError:
                self._apply_backpressure(pool_id)
                return False

        return True

    def _apply_backpressure(self, pool_id: str) -> None:
        """Apply backpressure by pausing the pool.

        Phase 07.1.1-03: When queue is full, pause pool with metadata
        indicating backpressure as the reason.

        Args:
            pool_id: Pool to pause
        """
        pool = self.manager.get_pool(pool_id)
        if pool and pool.status != PoolStatus.PAUSED:
            # Pause first (this updates metadata)
            self.manager.pause_pool(pool_id, reason="backpressure")

            # Add backpressure metadata after pause
            pool = self.manager.get_pool(pool_id)  # Reload
            if pool:
                queue = self._get_queue(pool_id)
                pool.metadata["backpressure"] = True
                pool.metadata["queue_snapshot"] = queue.snapshot()
                self.manager.storage.save_pool(pool)

                logger.warning(
                    f"Backpressure applied to pool {pool_id}, "
                    f"queue snapshot: {pool.metadata['queue_snapshot']}"
                )

    def _apply_recovery(
        self,
        pool_id: str,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[PhaseResult]:
        """Apply failure recovery using classifier and playbook.

        Phase 07.1.1-06: Classify failure, apply recovery action,
        and persist failure metadata.

        Args:
            pool_id: Pool experiencing failure
            exception: The exception that occurred
            context: Additional context (action, beads, etc.)

        Returns:
            PhaseResult if recovery requires stopping (pause/abort/skip)
            None if recovery says retry (caller should continue loop)
        """
        if not self.config.enable_recovery:
            # Recovery disabled, fail immediately
            logger.error(f"Handler error (recovery disabled): {exception}")
            pool = self.manager.get_pool(pool_id)
            return PhaseResult(
                success=False,
                phase=self._status_to_phase(pool.status) if pool else LoopPhase.INTAKE,
                message=f"Handler error: {exception}",
            )

        # Track recovery attempts
        attempt = self._recovery_attempts.get(pool_id, 0) + 1
        self._recovery_attempts[pool_id] = attempt

        # Classify the failure
        ctx = {"pool_id": pool_id, **(context or {})}
        failure = self._classifier.classify(exception, context=ctx, attempt=attempt)

        # Get recovery action
        action = self._playbook.get_action(failure.failure_type, attempt)
        failure.recovery_action = action

        # Persist failure metadata
        self._persist_failure_metadata(pool_id, failure)

        logger.info(
            f"Recovery: {action.value} for {failure.failure_type.value} "
            f"(pool={pool_id}, attempt={attempt})"
        )

        pool = self.manager.get_pool(pool_id)

        # Apply recovery action
        if action == RecoveryAction.RETRY:
            # Check if we've exceeded max attempts
            if attempt >= self.config.max_recovery_attempts:
                logger.error(
                    f"Max recovery attempts ({self.config.max_recovery_attempts}) "
                    f"exceeded for pool {pool_id}"
                )
                self._fail_pool(pool_id, failure)
                return PhaseResult(
                    success=False,
                    phase=self._status_to_phase(pool.status) if pool else LoopPhase.INTAKE,
                    message=f"Max recovery attempts exceeded: {failure.message}",
                    artifacts={"failure": failure.to_dict()},
                )
            # Apply backoff
            entry = self._playbook.get_entry(failure.failure_type)
            delay = entry.get_backoff_delay(attempt)
            logger.debug(f"Applying backoff delay: {delay}s")
            import time
            time.sleep(delay)
            return None  # Signal caller to continue/retry

        elif action == RecoveryAction.PAUSE:
            self.manager.pause_pool(pool_id, reason=f"failure_recovery: {failure.failure_type.value}")
            return PhaseResult(
                success=True,
                phase=self._status_to_phase(pool.status) if pool else LoopPhase.INTAKE,
                message=f"Pool paused for recovery: {failure.message}",
                checkpoint=True,
                artifacts={"failure": failure.to_dict()},
            )

        elif action == RecoveryAction.SKIP:
            logger.warning(f"Skipping failed operation: {failure.message}")
            return None  # Signal caller to continue (skip this item)

        elif action == RecoveryAction.ABORT:
            self._fail_pool(pool_id, failure)
            return PhaseResult(
                success=False,
                phase=self._status_to_phase(pool.status) if pool else LoopPhase.INTAKE,
                message=f"Pool aborted: {failure.message}",
                artifacts={"failure": failure.to_dict()},
            )

        elif action == RecoveryAction.QUARANTINE:
            # Quarantine the failing item and continue
            self._quarantine_failure(pool_id, failure)
            return None  # Continue with other work

        elif action == RecoveryAction.FALLBACK:
            # Fallback not implemented yet - treat as skip
            logger.warning(f"Fallback not implemented, skipping: {failure.message}")
            return None

        # Unknown action - fail safe
        logger.error(f"Unknown recovery action: {action}")
        return PhaseResult(
            success=False,
            phase=self._status_to_phase(pool.status) if pool else LoopPhase.INTAKE,
            message=f"Unknown recovery action: {action.value}",
        )

    def _persist_failure_metadata(self, pool_id: str, failure: FailureMetadata) -> None:
        """Persist failure metadata to pool.

        Args:
            pool_id: Pool to update
            failure: Failure metadata to persist
        """
        pool = self.manager.get_pool(pool_id)
        if not pool:
            return

        # Initialize failure history if needed
        if "failure_history" not in pool.metadata:
            pool.metadata["failure_history"] = []

        # Append to history (keep last 20 failures)
        pool.metadata["failure_history"].append(failure.to_dict())
        pool.metadata["failure_history"] = pool.metadata["failure_history"][-20:]

        # Update current failure info
        pool.metadata["last_failure"] = failure.to_dict()
        pool.metadata["failure_count"] = len(pool.metadata["failure_history"])

        self.manager.storage.save_pool(pool)

    def _fail_pool(self, pool_id: str, failure: FailureMetadata) -> None:
        """Mark pool as failed with failure reason.

        Args:
            pool_id: Pool to fail
            failure: Failure that caused the abort
        """
        pool = self.manager.get_pool(pool_id)
        if not pool:
            return

        # Set failure metadata before calling fail() which will save
        pool.metadata["failure_reason"] = failure.message
        pool.metadata["failure_type"] = failure.failure_type.value
        pool.metadata["failure_details"] = failure.to_dict()

        # Manually fail and save (instead of using manager.fail_pool which reloads)
        pool.fail(failure.message)
        self.manager.storage.save_pool(pool)

        self._recovery_attempts.pop(pool_id, None)

    def _quarantine_failure(self, pool_id: str, failure: FailureMetadata) -> None:
        """Quarantine a failing item for later review.

        Args:
            pool_id: Pool containing the failure
            failure: Failure metadata to quarantine
        """
        pool = self.manager.get_pool(pool_id)
        if not pool:
            return

        # Initialize quarantine list if needed
        if "quarantined_failures" not in pool.metadata:
            pool.metadata["quarantined_failures"] = []

        # Add to quarantine
        quarantine_entry = {
            **failure.to_dict(),
            "quarantined_at": failure.timestamp,
            "status": "pending_review",
        }
        pool.metadata["quarantined_failures"].append(quarantine_entry)
        self.manager.storage.save_pool(pool)

        logger.info(f"Quarantined failure for pool {pool_id}: {failure.failure_type.value}")

    def _process_queue(self, pool_id: str) -> List[PhaseResult]:
        """Process reserved items from the queue.

        Phase 07.1.1-03: Reserve items respecting max_in_flight, execute
        handlers, and ack/nack based on results.

        Args:
            pool_id: Pool to process work for

        Returns:
            List of PhaseResults from executed handlers
        """
        if not self.config.use_queue:
            return []

        queue = self._get_queue(pool_id)
        pool = self.manager.get_pool(pool_id)
        if not pool:
            return []

        results = []

        # Reserve items up to available capacity
        reserved = queue.reserve()
        if not reserved:
            return results

        logger.debug(f"Processing {len(reserved)} reserved items for pool {pool_id}")

        for item in reserved:
            action = RouteAction(item.action)
            handler = self._handlers.get(action)

            if handler is None:
                logger.warning(f"No handler for queued action: {item.action}")
                queue.nack(item.item_id, retry=False, error="No handler registered")
                continue

            try:
                # Build target beads list
                target_beads = [item.bead_id] if item.bead_id != "*" else []

                # Execute handler
                result = handler(pool, target_beads)
                results.append(result)

                # Ack on success
                queue.ack(item.item_id)

            except Exception as e:
                # Phase 07.1.1-06: Apply failure recovery for queue items
                if self.config.enable_recovery:
                    recovery_result = self._apply_recovery(
                        pool_id=pool_id,
                        exception=e,
                        context={
                            "action": item.action,
                            "bead_id": item.bead_id,
                            "item_id": item.item_id,
                        },
                    )
                    if recovery_result:
                        # Recovery requires stopping (pause/abort)
                        queue.nack(item.item_id, retry=False, error=str(e))
                        results.append(recovery_result)
                        break  # Stop processing queue
                    else:
                        # Recovery says retry or skip - nack with retry
                        queue.nack(item.item_id, retry=True, error=str(e))
                else:
                    logger.error(f"Handler error for {item.item_id}: {e}")
                    queue.nack(item.item_id, retry=True, error=str(e))

        return results

    def get_queue_snapshot(self, pool_id: str) -> Dict[str, Any]:
        """Get queue snapshot for a pool.

        Phase 07.1.1-03: Returns current queue state including counts,
        capacity status, and backpressure indicator.

        Args:
            pool_id: Pool identifier

        Returns:
            Queue snapshot dictionary
        """
        if not self.config.use_queue:
            return {"use_queue": False}

        queue = self._get_queue(pool_id)
        return queue.snapshot()

    def run(self, pool_id: str) -> PhaseResult:
        """Run loop until checkpoint or completion.

        Iterates through phases, executing handlers and advancing
        until either:
        - Pool reaches COMPLETE status
        - A handler returns checkpoint=True
        - An error occurs
        - Max iterations reached

        Phase 07.1.1-03: When use_queue=True, route decisions are enqueued
        and work is processed via the queue, respecting concurrency limits.
        Backpressure pauses the pool when queue is full.

        Args:
            pool_id: ID of pool to process

        Returns:
            PhaseResult indicating where we stopped and why
        """
        iterations = 0

        while iterations < self.config.max_iterations:
            iterations += 1

            # Load current state
            pool = self.manager.get_pool(pool_id)
            if pool is None:
                return PhaseResult(
                    success=False,
                    phase=LoopPhase.INTAKE,
                    message=f"Pool not found: {pool_id}",
                )

            # Check if complete
            if pool.status == PoolStatus.COMPLETE:
                return PhaseResult(
                    success=True,
                    phase=LoopPhase.COMPLETE,
                    message="Audit complete",
                )

            # Check if failed
            if pool.status == PoolStatus.FAILED:
                return PhaseResult(
                    success=False,
                    phase=self._status_to_phase(pool.status),
                    message=f"Pool failed: {pool.metadata.get('failure_reason', 'unknown')}",
                )

            # Phase 07.1.1-03: Check for backpressure-paused state
            if pool.status == PoolStatus.PAUSED:
                if pool.metadata.get("backpressure"):
                    # Try to resume if queue has capacity
                    queue = self._get_queue(pool_id)
                    snap = queue.snapshot()
                    if not snap["backpressure"] and not snap["at_capacity"]:
                        # Clear backpressure and resume
                        pool.metadata["backpressure"] = False
                        self.manager.resume_pool(pool_id)
                        logger.info(f"Backpressure cleared, resuming pool {pool_id}")
                        continue
                    else:
                        # Still under backpressure
                        return PhaseResult(
                            success=True,
                            phase=self._status_to_phase(pool.status),
                            message="Pool paused due to backpressure",
                            checkpoint=True,
                            artifacts={"queue_snapshot": snap, "backpressure": True},
                        )

            # Get routing decision
            decision = self.router.route(pool)

            if self.config.verbose:
                logger.info(
                    f"Loop iteration {iterations}: {decision.action.value} - {decision.reason}"
                )

            # Handle human flag checkpoint
            if decision.action == RouteAction.FLAG_FOR_HUMAN:
                if self.config.pause_on_human_flag:
                    return PhaseResult(
                        success=True,
                        phase=self._status_to_phase(pool.status),
                        message="Human review required",
                        checkpoint=True,
                        artifacts={"beads_for_review": decision.target_beads},
                    )

            # Handle wait (nothing to do, may need to advance)
            if decision.action == RouteAction.WAIT:
                # Phase 07.1.1-03: Process any pending queue items before advancing
                if self.config.use_queue:
                    queue_results = self._process_queue(pool_id)
                    for qr in queue_results:
                        if qr.checkpoint:
                            return qr

                if self.config.auto_advance:
                    advanced = self._try_advance_phase(pool)
                    if advanced:
                        continue
                    else:
                        return PhaseResult(
                            success=True,
                            phase=self._status_to_phase(pool.status),
                            message="Phase complete, waiting for advance",
                        )
                return PhaseResult(
                    success=True,
                    phase=self._status_to_phase(pool.status),
                    message=decision.reason,
                )

            # Handle complete
            if decision.action == RouteAction.COMPLETE:
                return PhaseResult(
                    success=True,
                    phase=LoopPhase.COMPLETE,
                    message="Audit complete",
                )

            # Phase 07.1.1-03: Queue-based execution
            if self.config.use_queue:
                # Enqueue the decision
                from .handlers import hash_payload
                payload_hash = hash_payload({
                    "action": decision.action.value,
                    "beads": decision.target_beads,
                })
                enqueued = self.enqueue(pool_id, decision, payload_hash)

                if not enqueued:
                    # Backpressure applied, return paused status
                    pool = self.manager.get_pool(pool_id)  # Reload after pause
                    return PhaseResult(
                        success=True,
                        phase=self._status_to_phase(pool.status) if pool else LoopPhase.INTAKE,
                        message="Pool paused due to backpressure",
                        checkpoint=True,
                        artifacts={
                            "backpressure": True,
                            "queue_snapshot": self.get_queue_snapshot(pool_id),
                        },
                    )

                # Process queue items
                queue_results = self._process_queue(pool_id)
                for qr in queue_results:
                    if qr.checkpoint:
                        return qr

                continue

            # Direct execution (use_queue=False or fallback)
            handler = self._handlers.get(decision.action)
            if handler is None:
                logger.warning(f"No handler for action: {decision.action}")
                return PhaseResult(
                    success=False,
                    phase=self._status_to_phase(pool.status),
                    message=f"No handler registered for {decision.action.value}",
                )

            try:
                result = handler(pool, decision.target_beads)
                # Clear recovery attempts on success
                self._recovery_attempts.pop(pool_id, None)
                if result.checkpoint:
                    return result
            except Exception as e:
                # Phase 07.1.1-06: Apply failure recovery
                recovery_result = self._apply_recovery(
                    pool_id=pool_id,
                    exception=e,
                    context={
                        "action": decision.action.value,
                        "target_beads": decision.target_beads,
                    },
                )
                if recovery_result:
                    return recovery_result
                # Recovery says continue (retry)
                continue

        # Safety limit reached
        return PhaseResult(
            success=False,
            phase=self._status_to_phase(pool.status) if pool else LoopPhase.INTAKE,
            message=f"Max iterations ({self.config.max_iterations}) reached",
        )

    def run_single_phase(self, pool_id: str) -> PhaseResult:
        """Run one phase only, then return.

        Useful for step-by-step execution or testing.

        Args:
            pool_id: ID of pool to process

        Returns:
            PhaseResult for single phase execution
        """
        pool = self.manager.get_pool(pool_id)
        if pool is None:
            return PhaseResult(
                success=False,
                phase=LoopPhase.INTAKE,
                message=f"Pool not found: {pool_id}",
            )

        decision = self.router.route(pool)
        handler = self._handlers.get(decision.action)

        if handler is None:
            return PhaseResult(
                success=False,
                phase=self._status_to_phase(pool.status),
                message=f"No handler for {decision.action.value}",
            )

        return handler(pool, decision.target_beads)

    def resume(self, pool_id: str) -> PhaseResult:
        """Resume loop from last checkpoint.

        Loads pool state and continues from current phase.
        Use this after human review or manual intervention.

        Args:
            pool_id: ID of pool to resume

        Returns:
            PhaseResult indicating where we stopped
        """
        pool = self.manager.get_pool(pool_id)
        if pool is None:
            return PhaseResult(
                success=False,
                phase=LoopPhase.INTAKE,
                message=f"Pool not found: {pool_id}",
            )

        # If paused, resume first
        if pool.status == PoolStatus.PAUSED:
            self.manager.resume_pool(pool_id)

        logger.info(f"Resuming pool {pool_id} from {pool.status.value}")
        return self.run(pool_id)

    def _try_advance_phase(self, pool: Pool) -> bool:
        """Try to advance pool to next phase.

        Checks if current phase is complete, then advances.
        Persists state before returning.

        Args:
            pool: Pool to advance

        Returns:
            True if advanced, False if not ready
        """
        current_idx = self._get_phase_index(pool.status)
        if current_idx is None or current_idx >= len(self.PHASE_ORDER) - 1:
            return False

        # Check if current phase is truly complete
        if not self._phase_complete(pool):
            return False

        # Advance via manager (persists automatically)
        new_status = self.manager.advance_phase(pool.id)

        if new_status:
            logger.info(f"Advanced pool {pool.id} to {new_status.value}")
            return True

        return False

    def _phase_complete(self, pool: Pool) -> bool:
        """Check if current phase is complete.

        Uses router to determine completion - if router returns WAIT,
        the current phase has nothing more to do.

        Args:
            pool: Pool to check

        Returns:
            True if phase is complete
        """
        decision = self.router.route(pool)
        return decision.action == RouteAction.WAIT

    def _get_phase_index(self, status: PoolStatus) -> Optional[int]:
        """Get index of status in phase order.

        Args:
            status: Pool status

        Returns:
            Index in PHASE_ORDER or None if not found
        """
        phase = self._status_to_phase(status)
        try:
            return self.PHASE_ORDER.index(phase)
        except ValueError:
            return None

    def _status_to_phase(self, status: PoolStatus) -> LoopPhase:
        """Convert pool status to loop phase.

        Args:
            status: Pool status

        Returns:
            Corresponding LoopPhase
        """
        mapping = {
            PoolStatus.INTAKE: LoopPhase.INTAKE,
            PoolStatus.CONTEXT: LoopPhase.CONTEXT,
            PoolStatus.BEADS: LoopPhase.BEADS,
            PoolStatus.EXECUTE: LoopPhase.EXECUTE,
            PoolStatus.VERIFY: LoopPhase.VERIFY,
            PoolStatus.INTEGRATE: LoopPhase.INTEGRATE,
            PoolStatus.COMPLETE: LoopPhase.COMPLETE,
            # Terminal states map to their last active phase
            PoolStatus.FAILED: LoopPhase.INTAKE,
            PoolStatus.PAUSED: LoopPhase.INTAKE,
        }
        return mapping.get(status, LoopPhase.INTAKE)

    def _phase_to_status(self, phase: LoopPhase) -> PoolStatus:
        """Convert loop phase to pool status.

        Args:
            phase: Loop phase

        Returns:
            Corresponding PoolStatus
        """
        mapping = {
            LoopPhase.INTAKE: PoolStatus.INTAKE,
            LoopPhase.CONTEXT: PoolStatus.CONTEXT,
            LoopPhase.BEADS: PoolStatus.BEADS,
            LoopPhase.EXECUTE: PoolStatus.EXECUTE,
            LoopPhase.VERIFY: PoolStatus.VERIFY,
            LoopPhase.INTEGRATE: PoolStatus.INTEGRATE,
            LoopPhase.COMPLETE: PoolStatus.COMPLETE,
        }
        return mapping.get(phase, PoolStatus.INTAKE)


# Export for module (includes re-exports from queue for convenience)
__all__ = [
    "LoopPhase",
    "PhaseResult",
    "LoopConfig",
    "ExecutionLoop",
    "PhaseHandler",
    # Re-exports from queue module (Phase 07.1.1-03)
    "WorkQueue",
    "WorkItem",
    "QueueLimits",
    "BackpressureError",
    # Re-exports from failures module (Phase 07.1.1-06)
    "FailureClassifier",
    "RecoveryPlaybook",
    "FailureMetadata",
    "FailureType",
    "RecoveryAction",
]
