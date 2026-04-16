"""
Collaborative Audit Network Module

Provides decentralized audit knowledge sharing with:
- Shared vulnerability database
- Auditor reputation system
- Consensus-based finding validation
- Bounty system for competitive audits
"""

from alphaswarm_sol.collab.findings import (
    AuditFinding,
    FindingStatus,
    FindingVote,
    FindingSubmission,
    FindingRegistry,
)

from alphaswarm_sol.collab.reputation import (
    AuditorProfile,
    ReputationSystem,
    ReputationAction,
    ReputationLevel,
)

from alphaswarm_sol.collab.consensus import (
    ConsensusResult,
    ConsensusValidator,
    ValidationRequest,
    ValidationVote,
)

from alphaswarm_sol.collab.network import (
    CollaborativeNetwork,
    NetworkConfig,
    NetworkStatistics,
)

from alphaswarm_sol.collab.bounty import (
    Bounty,
    BountyStatus,
    BountySubmission,
    BountyManager,
)

__all__ = [
    # Findings
    "AuditFinding",
    "FindingStatus",
    "FindingVote",
    "FindingSubmission",
    "FindingRegistry",
    # Reputation
    "AuditorProfile",
    "ReputationSystem",
    "ReputationAction",
    "ReputationLevel",
    # Consensus
    "ConsensusResult",
    "ConsensusValidator",
    "ValidationRequest",
    "ValidationVote",
    # Network
    "CollaborativeNetwork",
    "NetworkConfig",
    "NetworkStatistics",
    # Bounty
    "Bounty",
    "BountyStatus",
    "BountySubmission",
    "BountyManager",
]
