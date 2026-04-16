"""Policy validation functions for runtime enforcement.

This module provides validation functions that check inputs/outputs against
governance policies. Each validator returns a PolicyViolation if the check fails,
or None if validation passes.

Validators:
- validate_cost_budget: Check pool spend against cost limits
- validate_tool_access: Check tool usage against role restrictions
- validate_evidence_integrity: Check confidence upgrades have evidence refs
- validate_model_usage: Check model selection against tier restrictions

Usage:
    from alphaswarm_sol.governance.validators import validate_cost_budget
    from alphaswarm_sol.governance.policies import CostPolicy, PolicyAction

    policy = CostPolicy(hard_limit_usd=10.0, soft_limit_usd=8.0)
    violation = validate_cost_budget(
        current_cost=9.5,
        requested_cost=1.0,
        policy=policy,
        pool_id="pool-123"
    )
    if violation:
        print(f"Violation: {violation.message}")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .policies import (
    CostPolicy,
    EvidencePolicy,
    ModelUsagePolicy,
    PolicyAction,
    PolicyViolation,
    ToolAccessPolicy,
)


def validate_cost_budget(
    current_cost: float,
    requested_cost: float,
    policy: CostPolicy,
    pool_id: str,
) -> Optional[PolicyViolation]:
    """Validate cost budget compliance.

    Args:
        current_cost: Current pool spend in USD
        requested_cost: Additional cost being requested in USD
        policy: Cost policy configuration
        pool_id: Pool identifier for context

    Returns:
        PolicyViolation if budget exceeded, None otherwise
    """
    if not policy.enabled:
        return None

    total_cost = current_cost + requested_cost

    # Check hard limit
    if total_cost > policy.hard_limit_usd:
        return PolicyViolation(
            policy_id="cost_budget.hard_limit",
            violation_type="budget_exceeded",
            severity="critical" if policy.block_on_exceed else "high",
            action=PolicyAction.BLOCK if policy.block_on_exceed else PolicyAction.ALERT,
            message=f"Pool {pool_id} would exceed hard limit: ${total_cost:.2f} > ${policy.hard_limit_usd:.2f}",
            details={
                "current_cost_usd": current_cost,
                "requested_cost_usd": requested_cost,
                "total_cost_usd": total_cost,
                "hard_limit_usd": policy.hard_limit_usd,
                "pool_id": pool_id,
            },
        )

    # Check soft limit
    if total_cost > policy.soft_limit_usd:
        return PolicyViolation(
            policy_id="cost_budget.soft_limit",
            violation_type="budget_warning",
            severity="medium",
            action=PolicyAction.ALERT,
            message=f"Pool {pool_id} approaching hard limit: ${total_cost:.2f} > ${policy.soft_limit_usd:.2f} (soft limit)",
            details={
                "current_cost_usd": current_cost,
                "requested_cost_usd": requested_cost,
                "total_cost_usd": total_cost,
                "soft_limit_usd": policy.soft_limit_usd,
                "hard_limit_usd": policy.hard_limit_usd,
                "pool_id": pool_id,
            },
        )

    return None


def validate_tool_access(
    tool_name: str,
    agent_type: str,
    policy: ToolAccessPolicy,
) -> Optional[PolicyViolation]:
    """Validate tool access against role restrictions.

    Args:
        tool_name: Name of tool being accessed
        agent_type: Agent type requesting access (e.g., "vrs-attacker")
        policy: Tool access policy configuration

    Returns:
        PolicyViolation if access denied, None otherwise
    """
    if not policy.enabled:
        return None

    # Check forbidden tools list
    if tool_name in policy.forbidden_tools:
        return PolicyViolation(
            policy_id="tool_access.forbidden",
            violation_type="forbidden_tool",
            severity="critical",
            action=PolicyAction.BLOCK,
            message=f"Tool '{tool_name}' is forbidden for all agents",
            details={
                "tool_name": tool_name,
                "agent_type": agent_type,
                "forbidden_tools": policy.forbidden_tools,
            },
        )

    # Check role restrictions if defined for this agent
    if agent_type in policy.role_restrictions:
        allowed_tools = policy.role_restrictions[agent_type]
        if tool_name not in allowed_tools:
            return PolicyViolation(
                policy_id="tool_access.role_restriction",
                violation_type="unauthorized_tool",
                severity="high",
                action=PolicyAction.BLOCK,
                message=f"Agent '{agent_type}' not authorized to use tool '{tool_name}'",
                details={
                    "tool_name": tool_name,
                    "agent_type": agent_type,
                    "allowed_tools": allowed_tools,
                },
            )

    return None


def validate_evidence_integrity(
    evidence_refs: List[str],
    confidence_from: Optional[str],
    confidence_to: str,
    policy: EvidencePolicy,
    bead_id: str,
) -> Optional[PolicyViolation]:
    """Validate evidence integrity for confidence upgrades.

    Args:
        evidence_refs: List of evidence IDs
        confidence_from: Previous confidence level (None if new verdict)
        confidence_to: New confidence level
        policy: Evidence policy configuration
        bead_id: Bead identifier for context

    Returns:
        PolicyViolation if evidence requirements not met, None otherwise
    """
    if not policy.enabled:
        return None

    # Only enforce for confidence upgrades, not initial verdicts
    if confidence_from is None:
        return None

    if not policy.require_evidence_refs:
        return None

    # Check if evidence refs provided
    if not evidence_refs or len(evidence_refs) < policy.min_evidence_count:
        return PolicyViolation(
            policy_id="evidence_integrity.missing_evidence",
            violation_type="insufficient_evidence",
            severity="high",
            action=PolicyAction.BLOCK,
            message=f"Confidence upgrade for {bead_id} requires at least {policy.min_evidence_count} evidence ref(s)",
            details={
                "bead_id": bead_id,
                "confidence_from": confidence_from,
                "confidence_to": confidence_to,
                "evidence_refs": evidence_refs,
                "evidence_count": len(evidence_refs),
                "min_required": policy.min_evidence_count,
            },
        )

    return None


def validate_model_usage(
    model: str,
    agent_type: str,
    policy: ModelUsagePolicy,
) -> Optional[PolicyViolation]:
    """Validate model usage against tier restrictions.

    Args:
        model: Model being requested (e.g., "claude-3-5-sonnet")
        agent_type: Agent type requesting model
        policy: Model usage policy configuration

    Returns:
        PolicyViolation if model not allowed, None otherwise
    """
    if not policy.enabled:
        return None

    # If allowed_models specified, use that (override tier restrictions)
    if policy.allowed_models:
        if model not in policy.allowed_models:
            return PolicyViolation(
                policy_id="model_usage.not_allowed",
                violation_type="unauthorized_model",
                severity="high",
                action=PolicyAction.BLOCK,
                message=f"Model '{model}' not in allowed models list",
                details={
                    "model": model,
                    "agent_type": agent_type,
                    "allowed_models": policy.allowed_models,
                },
            )
        return None

    # Check tier restrictions
    if agent_type not in policy.tier_restrictions:
        # No restrictions for this agent type - allow
        return None

    allowed_tiers = policy.tier_restrictions[agent_type]

    # Map model to tier
    model_tier = _get_model_tier(model)
    if model_tier not in allowed_tiers:
        return PolicyViolation(
            policy_id="model_usage.tier_restriction",
            violation_type="unauthorized_tier",
            severity="medium",
            action=PolicyAction.BLOCK,
            message=f"Agent '{agent_type}' not authorized for tier '{model_tier}' (model: {model})",
            details={
                "model": model,
                "model_tier": model_tier,
                "agent_type": agent_type,
                "allowed_tiers": allowed_tiers,
            },
        )

    return None


def _get_model_tier(model: str) -> str:
    """Map model name to tier.

    Args:
        model: Model name (e.g., "claude-3-5-sonnet", "gpt-4o")

    Returns:
        Tier string ("opus", "sonnet", "haiku", "unknown")
    """
    model_lower = model.lower()

    # Claude tiers
    if "opus" in model_lower:
        return "opus"
    if "sonnet" in model_lower:
        return "sonnet"
    if "haiku" in model_lower:
        return "haiku"

    # GPT tiers (map to Claude equivalents)
    if "o1" in model_lower or "gpt-4o" in model_lower:
        return "opus"  # High-tier reasoning
    if "gpt-4o-mini" in model_lower:
        return "haiku"  # Low-tier fast

    # Gemini tiers
    if "gemini-1.5-pro" in model_lower:
        return "sonnet"  # Mid-tier
    if "gemini-1.5-flash" in model_lower:
        return "haiku"  # Low-tier fast

    return "unknown"
