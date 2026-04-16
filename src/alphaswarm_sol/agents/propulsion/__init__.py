"""Propulsion System for Autonomous Agent Execution.

This package provides the propulsion engine and coordinator for autonomous
agent work-pulling and multi-agent pool processing.

Per PHILOSOPHY.md:
- Agents pull work from their hooks (inboxes)
- Context-fresh: new agent instance per bead
- Work state persists so agents can resume

Per 05.2-CONTEXT.md:
- Hybrid work claiming: orchestrator assigns, agents can pull more
- Configurable agents per role
- Verifier assigned only when BOTH attacker AND defender complete

Components:
    PropulsionEngine: Autonomous work-pulling engine for single role
    PropulsionConfig: Configuration for propulsion engine
    WorkResult: Result of processing one work item
    AgentCoordinator: Multi-agent coordination for pool processing
    CoordinatorConfig: Configuration for coordinator
    CoordinatorStatus: Status enum for coordinator
    CoordinatorReport: Report from coordinator execution

Usage:
    from alphaswarm_sol.agents.propulsion import (
        PropulsionEngine, PropulsionConfig, WorkResult,
        AgentCoordinator, CoordinatorConfig, CoordinatorStatus, CoordinatorReport,
    )

    # Single-role engine
    engine = PropulsionEngine(runtime, inboxes, PropulsionConfig())
    results = await engine.run(timeout=300)

    # Multi-agent coordinator
    coordinator = AgentCoordinator(runtime, CoordinatorConfig())
    coordinator.setup_for_pool(pool, beads)
    report = await coordinator.run(timeout=600)
"""

from .engine import (
    PropulsionConfig,
    WorkResult,
    CostSummary,
    PropulsionEngine,
)

from .coordinator import (
    CoordinatorStatus,
    CoordinatorConfig,
    CoordinatorReport,
    CostBreakdown,
    AgentCoordinator,
    ROLE_TO_TASK_TYPE,
)


__all__ = [
    # Engine
    "PropulsionConfig",
    "WorkResult",
    "CostSummary",
    "PropulsionEngine",
    # Coordinator
    "CoordinatorStatus",
    "CoordinatorConfig",
    "CoordinatorReport",
    "CostBreakdown",
    "AgentCoordinator",
    "ROLE_TO_TASK_TYPE",
]
