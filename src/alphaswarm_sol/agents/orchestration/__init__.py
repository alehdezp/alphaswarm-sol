"""Agent orchestration layer for vuln-discovery workflow.

This module provides:
- MainOrchestrator: Top-level orchestrator for context-merge -> vuln-discovery
- SubCoordinator: Orchestrate parallel context-merge agents
- ContextMergeAgent: Produce verified context bundles for single vuln class
- FindingBeadFactory: Create finding beads with evidence chains (Phase 05.5-06)
- VulnDiscoveryAgent: Convert context beads to findings via VQL (Phase 05.5-06)
"""

from .context_merge_agent import (
    ContextMergeAgent,
    ContextMergeConfig,
    ContextMergeResult,
)
from .sub_coordinator import (
    SubCoordinator,
    SubCoordinatorConfig,
    SubCoordinatorResult,
)
from .finding_factory import (
    FindingBeadFactory,
    FindingInput,
    EvidenceChain,
)
from .vuln_discovery_agent import (
    VulnDiscoveryAgent,
    VulnDiscoveryConfig,
    VulnDiscoveryResult,
)
from .main_orchestrator import (
    MainOrchestrator,
    OrchestrationConfig,
    OrchestrationResult,
)

__all__ = [
    # Main orchestrator (Phase 05.5-07)
    "MainOrchestrator",
    "OrchestrationConfig",
    "OrchestrationResult",
    # Context merge orchestration (Phase 05.5-05)
    "ContextMergeAgent",
    "ContextMergeConfig",
    "ContextMergeResult",
    "SubCoordinator",
    "SubCoordinatorConfig",
    "SubCoordinatorResult",
    # Finding discovery (Phase 05.5-06)
    "FindingBeadFactory",
    "FindingInput",
    "EvidenceChain",
    "VulnDiscoveryAgent",
    "VulnDiscoveryConfig",
    "VulnDiscoveryResult",
]
