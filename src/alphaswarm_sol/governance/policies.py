"""Policy definitions and configuration loading.

This module defines governance policies for multi-agent orchestration:
- CostPolicy: Budget enforcement with hard/soft limits
- ToolAccessPolicy: Role-based tool restrictions
- EvidencePolicy: Evidence integrity requirements
- ModelUsagePolicy: Model tier restrictions per agent type

Design Principles:
1. Declarative: Policies defined in YAML, not code
2. Type-safe: Enum-based actions and dataclasses
3. Auditable: Violations produce structured logs
4. Flexible: Support both blocking and alerting modes

Usage:
    from alphaswarm_sol.governance.policies import load_policies

    policies = load_policies(Path("configs/governance_policies.yaml"))
    cost_policy = policies["policies"]["cost_budget"]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class PolicyAction(Enum):
    """Action to take when policy is triggered."""

    ALLOW = "allow"  # Allow operation to proceed
    BLOCK = "block"  # Block operation, raise error
    SANITIZE = "sanitize"  # Modify operation to comply
    ALERT = "alert"  # Log warning but allow


class PolicyViolationError(Exception):
    """Raised when a policy violation blocks execution."""

    def __init__(
        self,
        message: str,
        policy_id: str,
        violation_type: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.policy_id = policy_id
        self.violation_type = violation_type
        self.details = details or {}


@dataclass
class PolicyViolation:
    """Record of a policy violation.

    Attributes:
        policy_id: Identifier of violated policy
        violation_type: Type of violation
        severity: Severity level (info, warning, error, critical)
        action: Action taken (ALLOW, BLOCK, SANITIZE, ALERT)
        message: Human-readable violation description
        details: Additional context (e.g., current/limit values)
    """

    policy_id: str
    violation_type: str
    severity: str
    action: PolicyAction
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "policy_id": self.policy_id,
            "violation_type": self.violation_type,
            "severity": self.severity,
            "action": self.action.value,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class CostPolicy:
    """Cost budget policy configuration.

    Attributes:
        hard_limit_usd: Maximum spend allowed (blocks if exceeded)
        soft_limit_usd: Warning threshold (alerts if exceeded)
        enabled: Whether cost enforcement is active
        block_on_exceed: If True, raise error on hard limit; if False, warn only
    """

    hard_limit_usd: float = 10.0
    soft_limit_usd: float = 8.0
    enabled: bool = True
    block_on_exceed: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CostPolicy":
        """Create from dictionary."""
        return cls(
            hard_limit_usd=float(data.get("hard_limit_usd", 10.0)),
            soft_limit_usd=float(data.get("soft_limit_usd", 8.0)),
            enabled=bool(data.get("enabled", True)),
            block_on_exceed=bool(data.get("block_on_exceed", True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hard_limit_usd": self.hard_limit_usd,
            "soft_limit_usd": self.soft_limit_usd,
            "enabled": self.enabled,
            "block_on_exceed": self.block_on_exceed,
        }


@dataclass
class ToolAccessPolicy:
    """Tool access policy configuration.

    Attributes:
        role_restrictions: Mapping of agent types to allowed tools
        forbidden_tools: Tools that are forbidden for all agents
        enabled: Whether tool access enforcement is active
    """

    role_restrictions: Dict[str, List[str]] = field(default_factory=dict)
    forbidden_tools: List[str] = field(default_factory=list)
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolAccessPolicy":
        """Create from dictionary."""
        return cls(
            role_restrictions=data.get("role_restrictions", {}),
            forbidden_tools=data.get("forbidden_tools", []),
            enabled=bool(data.get("enabled", True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role_restrictions": self.role_restrictions,
            "forbidden_tools": self.forbidden_tools,
            "enabled": self.enabled,
        }


@dataclass
class EvidencePolicy:
    """Evidence integrity policy configuration.

    Attributes:
        require_evidence_refs: If True, block confidence upgrades without evidence
        min_evidence_count: Minimum number of evidence refs required
        enabled: Whether evidence integrity enforcement is active
    """

    require_evidence_refs: bool = True
    min_evidence_count: int = 1
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidencePolicy":
        """Create from dictionary."""
        return cls(
            require_evidence_refs=bool(data.get("require_evidence_refs", True)),
            min_evidence_count=int(data.get("min_evidence_count", 1)),
            enabled=bool(data.get("enabled", True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "require_evidence_refs": self.require_evidence_refs,
            "min_evidence_count": self.min_evidence_count,
            "enabled": self.enabled,
        }


@dataclass
class ModelUsagePolicy:
    """Model usage policy configuration.

    Attributes:
        tier_restrictions: Mapping of agent types to allowed model tiers
        allowed_models: Explicit list of allowed models (if specified)
        enabled: Whether model usage enforcement is active
    """

    tier_restrictions: Dict[str, List[str]] = field(default_factory=dict)
    allowed_models: List[str] = field(default_factory=list)
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelUsagePolicy":
        """Create from dictionary."""
        return cls(
            tier_restrictions=data.get("tier_restrictions", {}),
            allowed_models=data.get("allowed_models", []),
            enabled=bool(data.get("enabled", True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tier_restrictions": self.tier_restrictions,
            "allowed_models": self.allowed_models,
            "enabled": self.enabled,
        }


def load_policies(path: Path) -> Dict[str, Any]:
    """Load policies from YAML configuration.

    Args:
        path: Path to governance_policies.yaml

    Returns:
        Dictionary with parsed policy objects

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config is invalid YAML
    """
    if not path.exists():
        raise FileNotFoundError(f"Policy configuration not found: {path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    policies = data.get("policies", {})

    return {
        "policies": {
            "cost_budget": CostPolicy.from_dict(policies.get("cost_budget", {})),
            "tool_access": ToolAccessPolicy.from_dict(policies.get("tool_access", {})),
            "evidence_integrity": EvidencePolicy.from_dict(
                policies.get("evidence_integrity", {})
            ),
            "model_usage": ModelUsagePolicy.from_dict(policies.get("model_usage", {})),
        },
        "metadata": data.get("metadata", {}),
    }
