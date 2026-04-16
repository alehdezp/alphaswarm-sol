"""
Phase 4: Cross-Project Transfer

Enables learning from similar projects and transferring
vulnerability patterns across codebases.
"""

from alphaswarm_sol.transfer.project_profiler import (
    ProjectProfile,
    ProjectProfiler,
    ProjectDatabase,
)

from alphaswarm_sol.transfer.vulnerability_transfer import (
    ValidationStatus,
    TransferredFinding,
    TransferResult,
    VulnerabilityTransferEngine,
)

from alphaswarm_sol.transfer.ecosystem_learning import (
    ExploitRecord,
    PatternEffectiveness,
    EcosystemStats,
    EcosystemLearner,
)

__all__ = [
    # Project profiling
    "ProjectProfile",
    "ProjectProfiler",
    "ProjectDatabase",
    # Vulnerability transfer
    "ValidationStatus",
    "TransferredFinding",
    "TransferResult",
    "VulnerabilityTransferEngine",
    # Ecosystem learning
    "ExploitRecord",
    "PatternEffectiveness",
    "EcosystemStats",
    "EcosystemLearner",
]
