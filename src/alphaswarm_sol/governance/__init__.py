"""Governance and policy enforcement for AlphaSwarm orchestration.

This module provides runtime policy enforcement for multi-agent workflows,
including cost budgets, tool access restrictions, model usage policies, and
evidence integrity gates.

Public API:
    from alphaswarm_sol.governance import (
        PolicyEnforcer,
        enforce_policy,
        PolicyViolation,
        PolicyAction,
        load_policies,
    )
"""

from .enforcer import PolicyEnforcer, enforce_policy
from .policies import (
    CostPolicy,
    EvidencePolicy,
    ModelUsagePolicy,
    PolicyAction,
    PolicyViolation,
    PolicyViolationError,
    ToolAccessPolicy,
    load_policies,
)

__all__ = [
    # Core enforcement
    "PolicyEnforcer",
    "enforce_policy",
    # Policy definitions
    "PolicyAction",
    "PolicyViolation",
    "PolicyViolationError",
    "CostPolicy",
    "ToolAccessPolicy",
    "EvidencePolicy",
    "ModelUsagePolicy",
    # Utilities
    "load_policies",
]
