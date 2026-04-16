"""Incident response playbook execution.

This module provides automated incident response through YAML-defined playbooks:
- Define playbooks with ordered response steps
- Execute steps with action handlers (query, alert, log)
- Track execution results and failures
- Support for conditional execution

Design Principles:
1. Playbooks are YAML-defined, not hardcoded
2. Steps execute in order with success/failure tracking
3. Actions are extensible through handler registry
4. All execution is logged for audit trail

Example:
    from alphaswarm_sol.reliability.playbooks import PlaybookExecutor, load_playbooks
    from pathlib import Path

    # Load playbooks
    playbooks = load_playbooks(Path("configs/incident_playbooks.yaml"))
    executor = PlaybookExecutor()

    # Execute playbook
    result = executor.execute(
        playbook=playbooks["pool_success_rate_degradation"],
        context={"pool_id": "audit-pool-001", "success_rate": 85.0}
    )

    print(f"Execution status: {result.success}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class StepAction(str, Enum):
    """Available playbook step actions."""

    QUERY = "query"  # Query data from store
    ALERT = "alert"  # Send alert/notification
    LOG = "log"  # Log information
    ESCALATE = "escalate"  # Escalate to higher severity
    RETRY = "retry"  # Retry failed operation


@dataclass
class PlaybookStep:
    """A single step in an incident response playbook.

    Attributes:
        id: Step identifier
        name: Step name
        action: Action to execute
        params: Parameters for the action
        condition: Optional condition for execution
    """

    id: str
    name: str
    action: StepAction
    params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "action": self.action.value,
            "params": self.params,
            "condition": self.condition,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlaybookStep":
        """Create from dictionary."""
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            action=StepAction(data["action"]),
            params=dict(data.get("params", {})),
            condition=data.get("condition"),
        )


@dataclass
class PlaybookResult:
    """Result of playbook execution.

    Attributes:
        playbook_id: Which playbook was executed
        success: Whether execution succeeded
        steps_executed: Number of steps executed
        steps_failed: Number of steps that failed
        execution_time_ms: Execution time in milliseconds
        step_results: Results for each step
        error: Error message if execution failed
        timestamp: When execution occurred
    """

    playbook_id: str
    success: bool
    steps_executed: int
    steps_failed: int
    execution_time_ms: float
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "playbook_id": self.playbook_id,
            "success": self.success,
            "steps_executed": self.steps_executed,
            "steps_failed": self.steps_failed,
            "execution_time_ms": self.execution_time_ms,
            "step_results": self.step_results,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Playbook:
    """Incident response playbook.

    Attributes:
        id: Playbook identifier
        name: Playbook name
        description: What this playbook does
        trigger_slo: Which SLO violation triggers this playbook
        steps: Ordered list of response steps
    """

    id: str
    name: str
    description: str
    trigger_slo: str
    steps: List[PlaybookStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger_slo": self.trigger_slo,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Playbook":
        """Create from dictionary."""
        steps = [PlaybookStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            description=str(data["description"]),
            trigger_slo=str(data["trigger_slo"]),
            steps=steps,
        )


class PlaybookExecutor:
    """Execute incident response playbooks.

    Executes playbook steps in order, handles action dispatch, and tracks results.
    Supports extensible action handlers through registration.

    Example:
        executor = PlaybookExecutor()

        # Execute playbook
        result = executor.execute(playbook, context={"pool_id": "pool-001"})

        if not result.success:
            print(f"Playbook failed: {result.error}")
    """

    def __init__(self):
        """Initialize playbook executor."""
        self._action_handlers: Dict[StepAction, Callable] = {
            StepAction.QUERY: self._handle_query,
            StepAction.ALERT: self._handle_alert,
            StepAction.LOG: self._handle_log,
            StepAction.ESCALATE: self._handle_escalate,
            StepAction.RETRY: self._handle_retry,
        }

    def execute(
        self, playbook: Playbook, context: Optional[Dict[str, Any]] = None
    ) -> PlaybookResult:
        """Execute a playbook.

        Args:
            playbook: Playbook to execute
            context: Optional execution context (pool_id, incident_id, etc.)

        Returns:
            PlaybookResult with execution details
        """
        start_time = datetime.now()
        context = context or {}

        logger.info(
            f"Executing playbook {playbook.id} ({playbook.name}) with context: {context}"
        )

        step_results = []
        steps_executed = 0
        steps_failed = 0

        for step in playbook.steps:
            # Check condition if present
            if step.condition and not self._evaluate_condition(step.condition, context):
                logger.debug(f"Skipping step {step.id} - condition not met")
                step_results.append(
                    {
                        "step_id": step.id,
                        "name": step.name,
                        "action": step.action.value,
                        "status": "skipped",
                        "reason": "condition not met",
                    }
                )
                continue

            # Execute step
            try:
                handler = self._action_handlers.get(step.action)
                if handler is None:
                    raise ValueError(f"No handler for action: {step.action}")

                result = handler(step, context)
                steps_executed += 1

                step_results.append(
                    {
                        "step_id": step.id,
                        "name": step.name,
                        "action": step.action.value,
                        "status": "success",
                        "result": result,
                    }
                )

                logger.debug(f"Step {step.id} completed: {result}")

            except Exception as e:
                steps_failed += 1
                error_msg = str(e)

                # Handle both StepAction enum and string action
                action_value = step.action.value if hasattr(step.action, 'value') else str(step.action)

                step_results.append(
                    {
                        "step_id": step.id,
                        "name": step.name,
                        "action": action_value,
                        "status": "failed",
                        "error": error_msg,
                    }
                )

                logger.error(f"Step {step.id} failed: {error_msg}")

                # Stop execution on failure
                break

        # Calculate execution time
        end_time = datetime.now()
        execution_time_ms = (end_time - start_time).total_seconds() * 1000

        success = steps_failed == 0
        error = None if success else f"{steps_failed} step(s) failed"

        result = PlaybookResult(
            playbook_id=playbook.id,
            success=success,
            steps_executed=steps_executed,
            steps_failed=steps_failed,
            execution_time_ms=execution_time_ms,
            step_results=step_results,
            error=error,
            timestamp=start_time,
        )

        logger.info(
            f"Playbook {playbook.id} execution completed: "
            f"success={success}, steps={steps_executed}/{len(playbook.steps)}, "
            f"time={execution_time_ms:.1f}ms"
        )

        return result

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate condition string against context.

        Args:
            condition: Condition expression (e.g., "success_rate < 90")
            context: Context values

        Returns:
            True if condition met, False otherwise
        """
        # Simple expression evaluation (placeholder)
        # In production, would use safer expression evaluator
        try:
            # Replace variable references with context values
            for key, value in context.items():
                condition = condition.replace(key, str(value))

            # Evaluate expression
            return bool(eval(condition))
        except Exception as e:
            logger.warning(f"Failed to evaluate condition '{condition}': {e}")
            return False

    def _handle_query(self, step: PlaybookStep, context: Dict[str, Any]) -> str:
        """Handle query action.

        Args:
            step: Playbook step
            context: Execution context

        Returns:
            Query result description
        """
        query_type = step.params.get("query_type", "unknown")
        target = step.params.get("target", "unknown")

        logger.info(f"Querying {query_type} from {target}")

        # Placeholder - would actually query data stores
        return f"Queried {query_type} from {target}"

    def _handle_alert(self, step: PlaybookStep, context: Dict[str, Any]) -> str:
        """Handle alert action.

        Args:
            step: Playbook step
            context: Execution context

        Returns:
            Alert result description
        """
        message = step.params.get("message", "Alert")
        channel = step.params.get("channel", "log")

        logger.warning(f"ALERT [{channel}]: {message}")

        # Placeholder - would send actual alerts
        return f"Alert sent to {channel}: {message}"

    def _handle_log(self, step: PlaybookStep, context: Dict[str, Any]) -> str:
        """Handle log action.

        Args:
            step: Playbook step
            context: Execution context

        Returns:
            Log result description
        """
        message = step.params.get("message", "")
        level = step.params.get("level", "info")

        log_func = getattr(logger, level, logger.info)
        log_func(f"Playbook log: {message}")

        return f"Logged at {level}: {message}"

    def _handle_escalate(self, step: PlaybookStep, context: Dict[str, Any]) -> str:
        """Handle escalate action.

        Args:
            step: Playbook step
            context: Execution context

        Returns:
            Escalation result description
        """
        to = step.params.get("to", "oncall")
        reason = step.params.get("reason", "SLO violation")

        logger.warning(f"Escalating to {to}: {reason}")

        # Placeholder - would trigger actual escalation
        return f"Escalated to {to}"

    def _handle_retry(self, step: PlaybookStep, context: Dict[str, Any]) -> str:
        """Handle retry action.

        Args:
            step: Playbook step
            context: Execution context

        Returns:
            Retry result description
        """
        operation = step.params.get("operation", "unknown")
        max_attempts = step.params.get("max_attempts", 3)

        logger.info(f"Retrying {operation} (max {max_attempts} attempts)")

        # Placeholder - would trigger actual retry logic
        return f"Retry scheduled for {operation}"


def load_playbooks(config_path: Path) -> Dict[str, Playbook]:
    """Load playbook definitions from YAML configuration.

    Args:
        config_path: Path to incident_playbooks.yaml

    Returns:
        Dictionary mapping playbook_id to Playbook

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Playbook config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "playbooks" not in data:
        raise ValueError("Invalid playbook config: must have 'playbooks' key")

    playbooks = {}
    for playbook_data in data["playbooks"]:
        playbook = Playbook.from_dict(playbook_data)
        playbooks[playbook.id] = playbook

    logger.info(f"Loaded {len(playbooks)} playbook definitions from {config_path}")
    return playbooks


__all__ = [
    "StepAction",
    "PlaybookStep",
    "PlaybookResult",
    "Playbook",
    "PlaybookExecutor",
    "load_playbooks",
]
