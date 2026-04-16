"""Infrastructure Agents Package.

This package provides infrastructure agents for the multi-agent SDK integration:
- SupervisorAgent: Monitors queues, detects stuck work, escalates failures (05.2-03)
- IntegratorAgent: Merges verdicts from multiple agents (05.2-04)

Per 05.2-CONTEXT.md:
- Supervisor logs issues without auto-intervention
- Integrator dedupes overlaps, merges evidence, finalizes verdicts
- Let pool complete with what it can
- All escalations require human review

Usage:
    from alphaswarm_sol.agents.infrastructure import (
        # Supervisor
        SupervisorAgent,
        SupervisorConfig,
        SupervisorReport,
        StuckWorkReport,
        # Integrator
        IntegratorAgent,
        IntegratorConfig,
        MergedVerdict,
        AgentVerdict,
        # Prompts
        SUPERVISOR_SYSTEM_PROMPT,
        INTEGRATOR_SYSTEM_PROMPT,
    )

    # Create supervisor
    supervisor = SupervisorAgent(
        pool_manager=manager,
        inboxes={
            AgentRole.ATTACKER: attacker_inbox,
            AgentRole.DEFENDER: defender_inbox,
        },
        config=SupervisorConfig(stuck_threshold_minutes=15),
    )

    # Run check
    report = supervisor.check_pool("pool-123")
    if report.has_issues:
        print(report.summary())

    # Create integrator
    integrator = IntegratorAgent()
    result = integrator.integrate(bead, verdicts)
"""

from .prompts import (
    SUPERVISOR_SYSTEM_PROMPT,
    INTEGRATOR_SYSTEM_PROMPT,
)

from .supervisor import (
    SupervisorAgent,
    SupervisorConfig,
    SupervisorReport,
    StuckWorkReport,
)

from .integrator import (
    IntegratorAgent,
    IntegratorConfig,
    MergedVerdict,
    AgentVerdict,
)


__all__ = [
    # Supervisor
    "SupervisorAgent",
    "SupervisorConfig",
    "SupervisorReport",
    "StuckWorkReport",
    # Integrator
    "IntegratorAgent",
    "IntegratorConfig",
    "MergedVerdict",
    "AgentVerdict",
    # Prompts
    "SUPERVISOR_SYSTEM_PROMPT",
    "INTEGRATOR_SYSTEM_PROMPT",
]
