"""Chaos testing harness for multi-agent resilience validation.

This module provides systematic fault injection for testing agent system resilience:
- Configurable fault types (API errors, timeouts, malformed responses, delays)
- Component-targeted experiments (llm, tool, agent, handoff)
- MTTR tracking and recovery measurement
- Pre-built templates for common scenarios

Design Principles:
1. Configurable fault injection rates (0-100%)
2. Component-scoped targeting for isolation
3. Decorator-based integration for minimal code changes
4. Comprehensive result aggregation

Example:
    from alphaswarm_sol.reliability.chaos import ChaosTestHarness, CHAOS_TEMPLATES

    # Create harness with pre-built template
    harness = ChaosTestHarness(enabled=True)
    harness.add_experiment(CHAOS_TEMPLATES["api_timeout_20pct"])

    # Use with decorator
    @with_chaos_testing("llm")
    def call_llm(prompt: str, chaos_harness=None):
        return {"response": "ok"}

    # Run with chaos
    result = call_llm("test", chaos_harness=harness)
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class FaultType(Enum):
    """Types of faults to inject."""

    API_TIMEOUT = "api_timeout"
    API_ERROR = "api_error"
    MALFORMED_RESPONSE = "malformed_response"
    AGENT_FAILURE = "agent_failure"
    COMMUNICATION_DELAY = "communication_delay"
    COST_SPIKE = "cost_spike"
    SCHEMA_VIOLATION = "schema_violation"
    RATE_LIMIT = "rate_limit"


@dataclass
class ChaosExperiment:
    """Chaos experiment definition.

    Attributes:
        name: Unique experiment identifier
        fault_type: Type of fault to inject
        injection_rate: Percentage of calls to inject (0.0 to 1.0)
        fault_params: Parameters for fault injection
        target_component: Which component to target ("llm", "tool", "agent", "handoff")
        expected_degradation: Expected performance degradation metrics
    """

    name: str
    fault_type: FaultType
    injection_rate: float  # 0.0 to 1.0 (percentage of calls)
    fault_params: Dict[str, Any]
    target_component: str  # "llm", "tool", "agent", "handoff"
    expected_degradation: Dict[str, float] = field(default_factory=dict)

    def _replace(self, **kwargs) -> "ChaosExperiment":
        """Create a copy with some fields replaced (for templates)."""
        params = {
            "name": self.name,
            "fault_type": self.fault_type,
            "injection_rate": self.injection_rate,
            "fault_params": self.fault_params.copy(),
            "target_component": self.target_component,
            "expected_degradation": self.expected_degradation.copy(),
        }
        params.update(kwargs)
        return ChaosExperiment(**params)


@dataclass
class ChaosResult:
    """Result of chaos experiment.

    Attributes:
        experiment_name: Name of experiment (or "aggregate")
        faults_injected: Number of faults injected
        total_calls: Total calls made
        success_rate: Percentage of successful calls
        mean_latency: Mean latency in seconds
        p95_latency: 95th percentile latency in seconds
        mttr: Mean time to recovery in seconds
        metrics: Additional metrics
    """

    experiment_name: str
    faults_injected: int
    total_calls: int
    success_rate: float
    mean_latency: float
    p95_latency: float
    mttr: float  # Mean time to recovery
    metrics: Dict[str, Any]


class APIError(Exception):
    """API error for chaos testing."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(Exception):
    """Rate limit error for chaos testing."""

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class AgentFailureError(Exception):
    """Agent failure error for chaos testing."""

    pass


class ChaosTestHarness:
    """Chaos testing harness for multi-agent orchestration.

    Provides systematic fault injection with configurable rates and targeting.
    Tracks recovery times and aggregates results.

    Example:
        harness = ChaosTestHarness(enabled=True, seed=42)
        harness.add_experiment(ChaosExperiment(
            name="api_errors",
            fault_type=FaultType.API_ERROR,
            injection_rate=0.20,
            fault_params={"status_code": 500},
            target_component="llm"
        ))

        # Check if fault should be injected
        experiment = harness.should_inject_fault("llm")
        if experiment:
            harness.inject_fault(experiment, {"function": "call_llm"})
    """

    def __init__(self, enabled: bool = False, seed: Optional[int] = None):
        """Initialize chaos harness.

        Args:
            enabled: Whether chaos testing is enabled
            seed: Random seed for reproducible fault injection
        """
        self.enabled = enabled
        self.active_experiments: List[ChaosExperiment] = []
        self._random = random.Random(seed)
        self._fault_counts: Dict[str, int] = {}
        self._call_counts: Dict[str, int] = {}
        self._recovery_times: List[float] = []

    def add_experiment(self, experiment: ChaosExperiment) -> None:
        """Add chaos experiment.

        Args:
            experiment: Experiment to add
        """
        self.active_experiments.append(experiment)
        logger.info(
            "Chaos experiment added",
            extra={
                "experiment": experiment.name,
                "fault_type": experiment.fault_type.value,
                "injection_rate": experiment.injection_rate,
                "target": experiment.target_component,
            },
        )

    def remove_experiment(self, name: str) -> None:
        """Remove chaos experiment by name.

        Args:
            name: Experiment name to remove
        """
        self.active_experiments = [
            e for e in self.active_experiments if e.name != name
        ]

    def clear_experiments(self) -> None:
        """Remove all experiments."""
        self.active_experiments = []

    def should_inject_fault(self, component: str) -> Optional[ChaosExperiment]:
        """Determine if fault should be injected for this call.

        Args:
            component: Component being called ("llm", "tool", etc.)

        Returns:
            ChaosExperiment if fault should be injected, None otherwise
        """
        if not self.enabled:
            return None

        self._call_counts[component] = self._call_counts.get(component, 0) + 1

        for experiment in self.active_experiments:
            if experiment.target_component == component:
                if self._random.random() < experiment.injection_rate:
                    self._fault_counts[experiment.name] = (
                        self._fault_counts.get(experiment.name, 0) + 1
                    )
                    return experiment
        return None

    def inject_fault(
        self,
        experiment: ChaosExperiment,
        context: Dict[str, Any],
    ) -> Any:
        """Inject fault based on experiment type.

        Args:
            experiment: Experiment defining the fault
            context: Context about the call

        Returns:
            Malformed response for non-exception faults, None for delay-only

        Raises:
            Various exceptions based on fault type
        """
        logger.warning(
            "Chaos fault injected",
            extra={
                "experiment": experiment.name,
                "fault_type": experiment.fault_type.value,
                "context": context,
            },
        )

        fault_type = experiment.fault_type
        params = experiment.fault_params

        if fault_type == FaultType.API_TIMEOUT:
            delay = params.get("delay_seconds", 30)
            time.sleep(delay)
            raise TimeoutError(f"API timeout after {delay}s (chaos)")

        elif fault_type == FaultType.API_ERROR:
            status_code = params.get("status_code", 500)
            raise APIError(f"API error {status_code} (chaos)", status_code=status_code)

        elif fault_type == FaultType.MALFORMED_RESPONSE:
            corruption = params.get("corruption_type", "json_syntax")
            if corruption == "json_syntax":
                return {"error": "malformed", "data": None, "_chaos": True}
            elif corruption == "missing_fields":
                return {"partial": True, "_chaos": True}

        elif fault_type == FaultType.COMMUNICATION_DELAY:
            delay = params.get("delay_seconds", 5)
            time.sleep(delay)
            return None  # Allow call to continue after delay

        elif fault_type == FaultType.SCHEMA_VIOLATION:
            return {"unexpected_field": "chaos", "missing_required": True, "_chaos": True}

        elif fault_type == FaultType.COST_SPIKE:
            multiplier = params.get("cost_multiplier", 10.0)
            return {"_cost_multiplier": multiplier, "_chaos": True}

        elif fault_type == FaultType.RATE_LIMIT:
            retry_after = params.get("retry_after", 60)
            raise RateLimitError(f"Rate limited, retry after {retry_after}s (chaos)", retry_after=retry_after)

        elif fault_type == FaultType.AGENT_FAILURE:
            raise AgentFailureError("Agent crashed mid-execution (chaos)")

    def record_recovery(self, recovery_time: float) -> None:
        """Record time to recover from a fault.

        Args:
            recovery_time: Time in seconds to recover
        """
        self._recovery_times.append(recovery_time)

    def get_results(self, component: Optional[str] = None) -> ChaosResult:
        """Get aggregated chaos test results.

        Args:
            component: Optional component to filter by

        Returns:
            ChaosResult with aggregated metrics
        """
        if component:
            total = self._call_counts.get(component, 0)
            faults = sum(
                self._fault_counts.get(e.name, 0)
                for e in self.active_experiments
                if e.target_component == component
            )
        else:
            total = sum(self._call_counts.values())
            faults = sum(self._fault_counts.values())

        success_rate = (total - faults) / total if total > 0 else 1.0
        mttr = (
            sum(self._recovery_times) / len(self._recovery_times)
            if self._recovery_times
            else 0.0
        )

        return ChaosResult(
            experiment_name="aggregate" if not component else component,
            faults_injected=faults,
            total_calls=total,
            success_rate=success_rate,
            mean_latency=0.0,  # Calculated by caller
            p95_latency=0.0,
            mttr=mttr,
            metrics={
                "fault_counts": dict(self._fault_counts),
                "call_counts": dict(self._call_counts),
            },
        )


def with_chaos_testing(component: str):
    """Decorator for chaos testing.

    Args:
        component: Component name ("llm", "tool", "agent", "handoff")

    Returns:
        Decorator that injects faults when chaos_harness kwarg is provided

    Example:
        @with_chaos_testing("llm")
        def call_llm(prompt: str, chaos_harness=None):
            return llm.complete(prompt)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            harness: Optional[ChaosTestHarness] = kwargs.get("chaos_harness")

            if harness:
                experiment = harness.should_inject_fault(component)
                if experiment:
                    context = {
                        "function": func.__name__,
                        "component": component,
                    }
                    result = harness.inject_fault(experiment, context)
                    if result is not None:
                        # Fault returns a value (malformed response, etc.)
                        return result
                    # Fault was delay-only, continue execution

            return func(*args, **kwargs)
        return wrapper
    return decorator


# Pre-built experiment templates
CHAOS_TEMPLATES = {
    "api_timeout_20pct": ChaosExperiment(
        name="api_timeout_20pct",
        fault_type=FaultType.API_TIMEOUT,
        injection_rate=0.20,
        fault_params={"delay_seconds": 10},
        target_component="llm",
        expected_degradation={"success_rate": 0.75, "mttr": 60.0},
    ),
    "malformed_response_10pct": ChaosExperiment(
        name="malformed_response_10pct",
        fault_type=FaultType.MALFORMED_RESPONSE,
        injection_rate=0.10,
        fault_params={"corruption_type": "json_syntax"},
        target_component="llm",
        expected_degradation={"success_rate": 0.85},
    ),
    "handoff_delay_15pct": ChaosExperiment(
        name="handoff_delay_15pct",
        fault_type=FaultType.COMMUNICATION_DELAY,
        injection_rate=0.15,
        fault_params={"delay_seconds": 5},
        target_component="handoff",
        expected_degradation={"p95_latency": 360.0},
    ),
    "tool_rate_limit_5pct": ChaosExperiment(
        name="tool_rate_limit_5pct",
        fault_type=FaultType.RATE_LIMIT,
        injection_rate=0.05,
        fault_params={"retry_after": 30},
        target_component="tool",
        expected_degradation={"success_rate": 0.90},
    ),
}


__all__ = [
    "FaultType",
    "ChaosExperiment",
    "ChaosResult",
    "APIError",
    "RateLimitError",
    "AgentFailureError",
    "ChaosTestHarness",
    "with_chaos_testing",
    "CHAOS_TEMPLATES",
]
