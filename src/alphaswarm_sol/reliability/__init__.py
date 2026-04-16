"""SLO tracking and incident response for AlphaSwarm orchestration.

This module provides reliability monitoring and incident management:
- SLO (Service Level Objective) tracking with automated measurement
- Incident detection from SLO violations
- Playbook-driven automated response
- Chaos testing for resilience validation

Key Components:
- SLO: Service Level Objective definitions (targets, thresholds, measurement)
- SLOTracker: Automated measurement and violation detection
- IncidentDetector: Create and manage incidents from violations
- PlaybookExecutor: Execute automated response playbooks
- ChaosTestHarness: Systematic fault injection for resilience testing

Usage:
    from alphaswarm_sol.reliability import SLOTracker, load_slos
    from pathlib import Path

    # Load SLOs from config
    slos = load_slos(Path("configs/slo_definitions.yaml"))
    tracker = SLOTracker(slos)

    # Measure SLOs
    measurement = tracker.measure_slo(
        slo_id="pool_success_rate",
        pool_id="audit-pool-001"
    )

    # Check for violations
    violation = tracker.check_slo("pool_success_rate", measurement)
    if violation:
        print(f"SLO violated: {violation.message}")
"""

from .slo import (
    SLOStatus,
    SLO,
    SLOViolation,
    SLOMeasurement,
    SLOTracker,
    load_slos,
)
from .incidents import (
    IncidentSeverity,
    IncidentStatus,
    Incident,
    IncidentDetector,
)
from .playbooks import (
    StepAction,
    PlaybookStep,
    PlaybookResult,
    Playbook,
    PlaybookExecutor,
    load_playbooks,
)
from .chaos import (
    FaultType,
    ChaosExperiment,
    ChaosResult,
    APIError,
    RateLimitError,
    AgentFailureError,
    ChaosTestHarness,
    with_chaos_testing,
    CHAOS_TEMPLATES,
)

__all__ = [
    # SLO tracking
    "SLOStatus",
    "SLO",
    "SLOViolation",
    "SLOMeasurement",
    "SLOTracker",
    "load_slos",
    # Incident management
    "IncidentSeverity",
    "IncidentStatus",
    "Incident",
    "IncidentDetector",
    # Playbook execution
    "StepAction",
    "PlaybookStep",
    "PlaybookResult",
    "Playbook",
    "PlaybookExecutor",
    "load_playbooks",
    # Chaos testing
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
