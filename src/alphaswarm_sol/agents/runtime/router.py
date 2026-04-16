"""Multi-Model Task Router for Intelligent Runtime Selection.

This module provides intelligent task routing to the most appropriate runtime
based on task type, agent role, and quality requirements. It implements the
cost-optimization strategy from 05.3-CONTEXT.md:

- Critical analysis (Attacker, Verifier) -> Claude Code CLI
- Reviews/discussion -> Codex CLI (different perspective)
- Verification/summarization -> OpenCode (free models)
- Code generation -> OpenCode (GLM-4.7)
- Deep reasoning -> OpenCode (DeepSeek V3.2)
- Large context (>200K) -> OpenCode (Gemini 3 Flash)
- Default -> OpenCode (cost-optimized)

Usage:
    from alphaswarm_sol.agents.runtime.router import (
        route_to_runtime,
        TaskRouter,
        RoutingPolicy,
    )
    from alphaswarm_sol.agents.runtime.base import AgentRole
    from alphaswarm_sol.agents.runtime.types import TaskType

    # Simple usage
    runtime = route_to_runtime(
        AgentRole.ATTACKER,
        TaskType.CRITICAL,
        accuracy_critical=True,
    )

    # Advanced usage with policy
    router = TaskRouter()
    policy = RoutingPolicy(
        task_type=TaskType.REASONING,
        role=AgentRole.VERIFIER,
        accuracy_critical=True,
        context_size=150_000,
    )
    runtime = router.route(policy)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from .base import AgentRole, AgentRuntime
from .types import (
    TaskType,
    MODEL_CONTEXT_LIMITS,
    get_context_limit,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Context Size Thresholds
# =============================================================================

# Context size thresholds for model selection
LARGE_CONTEXT_THRESHOLD = 200_000  # >200K tokens -> use large context model
HEAVY_CONTEXT_THRESHOLD = 500_000  # >500K tokens -> use heavy model (Gemini 3 Flash)


# =============================================================================
# Routing Policy
# =============================================================================

@dataclass
class RoutingPolicy:
    """Policy for task routing decisions.

    Attributes:
        task_type: The type of task being performed (ANALYZE, VERIFY, CODE, etc.)
        role: The agent role, if applicable (ATTACKER, DEFENDER, VERIFIER, etc.)
        accuracy_critical: Whether high accuracy is required (routes to premium runtimes)
        latency_sensitive: Whether low latency is important (routes to faster models)
        context_size: Estimated context size in tokens (affects model selection)
        preferred_runtime: Optional override for runtime selection
        metadata: Additional routing metadata for logging

    Examples:
        # Critical analysis requiring accuracy
        policy = RoutingPolicy(
            task_type=TaskType.CRITICAL,
            role=AgentRole.ATTACKER,
            accuracy_critical=True,
        )

        # Large context summarization
        policy = RoutingPolicy(
            task_type=TaskType.SUMMARIZE,
            context_size=300_000,  # 300K tokens
        )
    """

    task_type: TaskType
    role: Optional[AgentRole] = None
    accuracy_critical: bool = False
    latency_sensitive: bool = False
    context_size: int = 0
    preferred_runtime: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary for logging."""
        return {
            "task_type": self.task_type.value,
            "role": self.role.value if self.role else None,
            "accuracy_critical": self.accuracy_critical,
            "latency_sensitive": self.latency_sensitive,
            "context_size": self.context_size,
            "preferred_runtime": self.preferred_runtime,
            "metadata": self.metadata,
        }


# =============================================================================
# Task Router
# =============================================================================

class TaskRouter:
    """Multi-model task router for intelligent runtime selection.

    Routes tasks to the most appropriate runtime based on task type, agent role,
    and quality requirements. Implements the cost-optimization strategy from
    05.3-CONTEXT.md.

    Routing Rules:
        1. Critical analysis (Attacker, Verifier) + accuracy_critical -> Claude Code CLI
        2. Reviews/discussion (REVIEW task type) -> Codex CLI (different perspective)
        3. Verification/summarization -> OpenCode (free models)
        4. Code generation -> OpenCode (GLM-4.7)
        5. Reasoning tasks -> OpenCode (DeepSeek V3.2)
        6. Large context (>200K) -> OpenCode (Gemini 3 Flash)
        7. Default -> OpenCode (cost-optimized)

    Fallback Chain:
        OpenCode free models -> OpenCode paid models -> Claude Code CLI

    Usage:
        router = TaskRouter()
        policy = RoutingPolicy(
            task_type=TaskType.CRITICAL,
            role=AgentRole.ATTACKER,
            accuracy_critical=True,
        )
        runtime = router.route(policy)

    Attributes:
        rankings_store: Path to rankings YAML file for model selection
        _rankings: Cached rankings data
        _route_count: Counter for routing decisions
    """

    def __init__(self, rankings_store: Optional[Path] = None):
        """Initialize task router.

        Args:
            rankings_store: Path to rankings YAML file. If None, uses default
                          location at .vrs/rankings/rankings.yaml
        """
        self.rankings_store = rankings_store
        self._rankings: Optional[Dict[str, Any]] = None
        self._route_count: Dict[str, int] = {
            "opencode": 0,
            "claude_code": 0,
            "codex": 0,
        }

    def _load_rankings(self) -> Dict[str, Any]:
        """Load rankings from YAML file.

        Returns:
            Dictionary of rankings by task type. Empty dict if file not found.
        """
        if self._rankings is not None:
            return self._rankings

        if self.rankings_store and self.rankings_store.exists():
            try:
                import yaml
                with open(self.rankings_store) as f:
                    self._rankings = yaml.safe_load(f) or {}
                logger.debug(f"Loaded rankings from {self.rankings_store}")
            except Exception as e:
                logger.warning(f"Failed to load rankings: {e}")
                self._rankings = {}
        else:
            self._rankings = {}

        return self._rankings

    def route(self, policy: RoutingPolicy) -> AgentRuntime:
        """Route task to appropriate runtime.

        Per 05.3-CONTEXT.md routing strategy:
        1. Critical analysis (Attacker, Verifier) + accuracy_critical -> Claude Code CLI
        2. Reviews/discussion -> Codex CLI (different perspective)
        3. Verification/summarization -> OpenCode (free models)
        4. Code generation -> OpenCode (GLM-4.7 subscription)
        5. Reasoning tasks -> OpenCode (DeepSeek V3.2)
        6. Large context (>200K) -> OpenCode (Gemini 3 Flash)
        7. Default -> OpenCode (cost-optimized)

        Args:
            policy: Routing policy with task type, role, and requirements

        Returns:
            AgentRuntime instance for the selected runtime

        Raises:
            ValueError: If policy has invalid values
        """
        from .factory import create_runtime, RuntimeType
        from .opencode import OpenCodeConfig

        # Check for explicit preferred runtime override
        if policy.preferred_runtime:
            logger.info(f"Using preferred runtime: {policy.preferred_runtime}")
            self._track_route(policy.preferred_runtime)
            return create_runtime(sdk=policy.preferred_runtime)

        # Determine runtime based on routing rules
        runtime_type, model_hint = self._determine_runtime(policy)

        # Log routing decision
        self._log_routing_decision(policy, runtime_type, model_hint)

        # Track routing statistics
        self._track_route(runtime_type.value)

        # Create and return runtime
        if runtime_type == RuntimeType.OPENCODE:
            # For OpenCode, configure model based on task
            config = OpenCodeConfig(default_model=model_hint)
            return create_runtime(sdk=runtime_type, config=config)
        else:
            return create_runtime(sdk=runtime_type)

    def _determine_runtime(
        self, policy: RoutingPolicy
    ) -> tuple["RuntimeType", str]:
        """Determine the best runtime and model for a policy.

        Args:
            policy: Routing policy

        Returns:
            Tuple of (RuntimeType, model_hint)
        """
        from .factory import RuntimeType
        from .types import DEFAULT_MODELS

        task_type = policy.task_type
        role = policy.role

        # Rule 1: Critical analysis with accuracy requirement -> Claude Code
        if policy.accuracy_critical and role in (AgentRole.ATTACKER, AgentRole.VERIFIER):
            logger.debug(
                f"Routing to Claude Code: accuracy_critical + {role.value} role"
            )
            return RuntimeType.CLAUDE_CODE, "claude"

        # Rule 2: Critical task type -> Claude Code
        if task_type == TaskType.CRITICAL:
            logger.debug("Routing to Claude Code: CRITICAL task type")
            return RuntimeType.CLAUDE_CODE, "claude"

        # Rule 3: Review task type -> Codex CLI (different perspective)
        if task_type == TaskType.REVIEW:
            logger.debug("Routing to Codex CLI: REVIEW task type")
            return RuntimeType.CODEX, "codex"

        # All remaining tasks go to OpenCode with appropriate model selection
        # Rule 4: Large context handling
        if policy.context_size >= HEAVY_CONTEXT_THRESHOLD:
            logger.debug(
                f"Routing to OpenCode (Gemini 3 Flash): large context {policy.context_size} tokens"
            )
            return RuntimeType.OPENCODE, "google/gemini-3-flash-preview"

        if policy.context_size >= LARGE_CONTEXT_THRESHOLD:
            logger.debug(
                f"Routing to OpenCode (Gemini 3 Flash): context {policy.context_size} tokens"
            )
            return RuntimeType.OPENCODE, "google/gemini-3-flash-preview"

        # Rule 5: Use DEFAULT_MODELS mapping for task type
        model = DEFAULT_MODELS.get(task_type, "google/gemini-3-flash-preview")

        # Handle special model values
        if model in ("claude", "codex"):
            # These are CLI-based, but we're in OpenCode path
            # This shouldn't happen based on task type, fall back to Flash
            model = "google/gemini-3-flash-preview"

        logger.debug(f"Routing to OpenCode ({model}): {task_type.value} task type")
        return RuntimeType.OPENCODE, model

    def _log_routing_decision(
        self,
        policy: RoutingPolicy,
        runtime_type: "RuntimeType",
        model_hint: str,
    ) -> None:
        """Log routing decision for debugging and optimization.

        Args:
            policy: The routing policy
            runtime_type: Selected runtime type
            model_hint: Selected model for OpenCode, or runtime name for CLI
        """
        logger.info(
            f"Routed task: type={policy.task_type.value}, "
            f"role={policy.role.value if policy.role else 'None'}, "
            f"accuracy_critical={policy.accuracy_critical}, "
            f"context_size={policy.context_size} -> "
            f"{runtime_type.value} ({model_hint})"
        )

    def _track_route(self, runtime_name: str) -> None:
        """Track routing statistics.

        Args:
            runtime_name: Name of the runtime routed to
        """
        if runtime_name in self._route_count:
            self._route_count[runtime_name] += 1
        else:
            self._route_count[runtime_name] = 1

    def get_route_statistics(self) -> Dict[str, int]:
        """Get routing statistics.

        Returns:
            Dictionary of runtime names to route counts
        """
        return self._route_count.copy()

    def get_recommended_runtime(
        self,
        task_type: TaskType,
        role: Optional[AgentRole] = None,
    ) -> str:
        """Get recommended runtime name for logging/debugging.

        A lighter-weight method that returns just the runtime name without
        creating the actual runtime instance.

        Args:
            task_type: The task type
            role: Optional agent role

        Returns:
            Runtime type name (e.g., "opencode", "claude_code", "codex")
        """
        policy = RoutingPolicy(task_type=task_type, role=role)
        runtime_type, _ = self._determine_runtime(policy)
        return runtime_type.value

    def reset_statistics(self) -> None:
        """Reset routing statistics."""
        self._route_count = {
            "opencode": 0,
            "claude_code": 0,
            "codex": 0,
        }


# =============================================================================
# Convenience Function
# =============================================================================

def route_to_runtime(
    role: AgentRole,
    task_type: TaskType = TaskType.ANALYZE,
    accuracy_critical: bool = False,
    latency_sensitive: bool = False,
    context_size: int = 0,
    preferred_runtime: Optional[str] = None,
) -> AgentRuntime:
    """Route task to appropriate runtime.

    Convenience function that creates a TaskRouter and routes based on
    the provided parameters. For more control, use TaskRouter directly.

    Per 05.3-CONTEXT.md routing rules:
    1. Critical analysis (Attacker, Verifier) + accuracy_critical -> Claude Code CLI
    2. Reviews/discussion -> Codex CLI (different perspective)
    3. Verification/summarization -> OpenCode (free models)
    4. Code generation -> OpenCode (GLM-4.7)
    5. Reasoning tasks -> OpenCode (DeepSeek V3.2)
    6. Large context (>200K) -> OpenCode (Gemini 3 Flash)
    7. Default -> OpenCode (cost-optimized)

    Args:
        role: Agent role (ATTACKER, DEFENDER, VERIFIER, etc.)
        task_type: Type of task (ANALYZE, VERIFY, CODE, etc.). Defaults to ANALYZE.
        accuracy_critical: Whether high accuracy is required. Routes to Claude Code
                         for critical roles (Attacker, Verifier).
        latency_sensitive: Whether low latency is important.
        context_size: Estimated context size in tokens. Large contexts (>200K)
                     route to models with large context windows.
        preferred_runtime: Optional override for runtime selection.

    Returns:
        AgentRuntime instance for the selected runtime

    Examples:
        # Critical analysis - routes to Claude Code
        runtime = route_to_runtime(
            AgentRole.ATTACKER,
            TaskType.CRITICAL,
            accuracy_critical=True,
        )

        # Verification - routes to OpenCode with free model
        runtime = route_to_runtime(
            AgentRole.VERIFIER,
            TaskType.VERIFY,
        )

        # Code generation - routes to OpenCode with GLM-4.7
        runtime = route_to_runtime(
            AgentRole.TEST_BUILDER,
            TaskType.CODE,
        )

        # Large context - routes to OpenCode with Gemini 3 Flash
        runtime = route_to_runtime(
            AgentRole.INTEGRATOR,
            TaskType.SUMMARIZE,
            context_size=300_000,  # 300K tokens
        )
    """
    router = TaskRouter()
    policy = RoutingPolicy(
        task_type=task_type,
        role=role,
        accuracy_critical=accuracy_critical,
        latency_sensitive=latency_sensitive,
        context_size=context_size,
        preferred_runtime=preferred_runtime,
    )
    return router.route(policy)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "RoutingPolicy",
    "TaskRouter",
    "route_to_runtime",
    "LARGE_CONTEXT_THRESHOLD",
    "HEAVY_CONTEXT_THRESHOLD",
]
