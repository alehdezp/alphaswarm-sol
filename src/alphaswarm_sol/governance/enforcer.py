"""Runtime policy enforcement with decorator pattern.

This module provides the PolicyEnforcer class which validates operations against
governance policies. It integrates with:
- AuditLogger: Logs all violations to audit trail
- CostLedger: Looks up current pool costs
- Validators: Performs policy checks

PolicyEnforcer provides:
- check_input_policy: Validate before operation (cost, tool access, model)
- check_output_policy: Validate after operation (evidence integrity)
- handle_violation: Log and potentially raise error based on action

The enforce_policy decorator wraps handler functions for transparent enforcement.

Usage:
    from alphaswarm_sol.governance import PolicyEnforcer, enforce_policy

    # As a class
    enforcer = PolicyEnforcer(
        policies_path=Path("configs/governance_policies.yaml"),
        cost_ledger=ledger,
        audit_logger=logger
    )

    violation = enforcer.check_input_policy(
        pool_id="pool-123",
        agent_type="vrs-attacker",
        tool_name="slither",
        model="claude-3-5-sonnet",
        requested_cost=0.05
    )

    # As a decorator
    @enforce_policy(enforcer)
    def handle_investigation(pool_id, bead_id, agent_type, ...):
        # Handler logic here
        pass
"""

from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..metrics.cost_ledger import CostLedger
from ..observability.audit import AuditLogger
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
from .validators import (
    validate_cost_budget,
    validate_evidence_integrity,
    validate_model_usage,
    validate_tool_access,
)

logger = logging.getLogger(__name__)


class PolicyEnforcer:
    """Runtime policy enforcement for multi-agent orchestration.

    Validates operations against governance policies, logs violations,
    and blocks/alerts based on policy configuration.

    Attributes:
        policies_path: Path to governance_policies.yaml
        cost_ledger: Cost tracking for budget checks
        audit_logger: Audit logger for violation recording
        policies: Loaded policy configurations
    """

    def __init__(
        self,
        policies_path: Path,
        cost_ledger: Optional[CostLedger] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """Initialize policy enforcer.

        Args:
            policies_path: Path to governance_policies.yaml
            cost_ledger: Optional cost ledger for budget checks
            audit_logger: Optional audit logger for violation recording
        """
        self.policies_path = policies_path
        self.cost_ledger = cost_ledger
        self.audit_logger = audit_logger or AuditLogger()

        # Load policies
        config = load_policies(policies_path)
        self.policies = config["policies"]

        logger.info(
            "PolicyEnforcer initialized",
            policies_path=str(policies_path),
            cost_enabled=self.policies["cost_budget"].enabled,
            tool_access_enabled=self.policies["tool_access"].enabled,
            evidence_enabled=self.policies["evidence_integrity"].enabled,
            model_usage_enabled=self.policies["model_usage"].enabled,
        )

    def check_input_policy(
        self,
        pool_id: str,
        agent_type: str,
        tool_name: Optional[str] = None,
        model: Optional[str] = None,
        requested_cost: Optional[float] = None,
        trace_id: Optional[str] = None,
    ) -> Optional[PolicyViolation]:
        """Validate input policy before operation execution.

        Checks:
        - Cost budget (if cost_ledger provided and requested_cost specified)
        - Tool access (if tool_name specified)
        - Model usage (if model specified)

        Args:
            pool_id: Pool identifier
            agent_type: Agent type performing operation
            tool_name: Optional tool being accessed
            model: Optional model being used
            requested_cost: Optional estimated cost for operation
            trace_id: Optional trace correlation ID

        Returns:
            PolicyViolation if any check fails, None otherwise

        Raises:
            PolicyViolationError: If violation action is BLOCK
        """
        violations = []

        # Check cost budget
        if (
            requested_cost is not None
            and self.cost_ledger is not None
            and self.policies["cost_budget"].enabled
        ):
            current_cost = self.cost_ledger.total_cost
            violation = validate_cost_budget(
                current_cost=current_cost,
                requested_cost=requested_cost,
                policy=self.policies["cost_budget"],
                pool_id=pool_id,
            )
            if violation:
                violations.append(violation)

        # Check tool access
        if tool_name is not None and self.policies["tool_access"].enabled:
            violation = validate_tool_access(
                tool_name=tool_name,
                agent_type=agent_type,
                policy=self.policies["tool_access"],
            )
            if violation:
                violations.append(violation)

        # Check model usage
        if model is not None and self.policies["model_usage"].enabled:
            violation = validate_model_usage(
                model=model,
                agent_type=agent_type,
                policy=self.policies["model_usage"],
            )
            if violation:
                violations.append(violation)

        # Handle violations (log and potentially raise)
        for violation in violations:
            self.handle_violation(
                violation=violation,
                pool_id=pool_id,
                actor=agent_type,
                trace_id=trace_id,
            )

        # Return first blocking violation if any
        for violation in violations:
            if violation.action == PolicyAction.BLOCK:
                return violation

        # Return first alert violation if any
        for violation in violations:
            if violation.action == PolicyAction.ALERT:
                return violation

        return None

    def check_output_policy(
        self,
        bead_id: str,
        pool_id: str,
        agent_type: str,
        evidence_refs: List[str],
        confidence_from: Optional[str] = None,
        confidence_to: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Optional[PolicyViolation]:
        """Validate output policy after operation execution.

        Checks:
        - Evidence integrity (for confidence upgrades)

        Args:
            bead_id: Bead identifier
            pool_id: Pool identifier
            agent_type: Agent type that produced output
            evidence_refs: List of evidence IDs
            confidence_from: Previous confidence level (None if new verdict)
            confidence_to: New confidence level
            trace_id: Optional trace correlation ID

        Returns:
            PolicyViolation if check fails, None otherwise

        Raises:
            PolicyViolationError: If violation action is BLOCK
        """
        if confidence_to is None:
            return None

        violation = validate_evidence_integrity(
            evidence_refs=evidence_refs,
            confidence_from=confidence_from,
            confidence_to=confidence_to,
            policy=self.policies["evidence_integrity"],
            bead_id=bead_id,
        )

        if violation:
            self.handle_violation(
                violation=violation,
                pool_id=pool_id,
                actor=agent_type,
                trace_id=trace_id,
            )
            return violation

        return None

    def handle_violation(
        self,
        violation: PolicyViolation,
        pool_id: str,
        actor: str,
        trace_id: Optional[str] = None,
    ) -> None:
        """Handle policy violation (log and potentially raise).

        Args:
            violation: PolicyViolation details
            pool_id: Pool identifier for context
            actor: Agent/system that caused violation
            trace_id: Optional trace correlation ID

        Raises:
            PolicyViolationError: If violation.action is BLOCK
        """
        # Log to audit trail
        self.audit_logger.log_policy_violation(
            pool_id=pool_id,
            policy_id=violation.policy_id,
            violation_type=violation.violation_type,
            actor=actor,
            severity=violation.severity,
            suggested_action=violation.action.value,
            details=violation.details,
            trace_id=trace_id,
        )

        # Log to application logger
        log_level = {
            "critical": logging.CRITICAL,
            "high": logging.ERROR,
            "medium": logging.WARNING,
            "low": logging.INFO,
        }.get(violation.severity, logging.WARNING)

        logger.log(
            log_level,
            f"Policy violation: {violation.message}",
            extra={
                "policy_id": violation.policy_id,
                "violation_type": violation.violation_type,
                "action": violation.action.value,
                "pool_id": pool_id,
                "actor": actor,
            },
        )

        # Raise error if action is BLOCK
        if violation.action == PolicyAction.BLOCK:
            raise PolicyViolationError(
                message=violation.message,
                policy_id=violation.policy_id,
                violation_type=violation.violation_type,
                details=violation.details,
            )


def enforce_policy(enforcer: PolicyEnforcer) -> Callable:
    """Decorator for transparent policy enforcement on handler functions.

    Wraps handler functions to check input/output policies automatically.
    Handler functions should accept keyword arguments matching policy check parameters.

    Usage:
        @enforce_policy(enforcer)
        def handle_investigation(
            pool_id: str,
            bead_id: str,
            agent_type: str,
            tool_name: str = None,
            model: str = None,
            ...
        ):
            # Handler logic
            return result

    Args:
        enforcer: PolicyEnforcer instance

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract policy-relevant parameters
            pool_id = kwargs.get("pool_id")
            agent_type = kwargs.get("agent_type")
            tool_name = kwargs.get("tool_name")
            model = kwargs.get("model")
            requested_cost = kwargs.get("requested_cost")
            trace_id = kwargs.get("trace_id")

            # Check input policy
            if pool_id and agent_type:
                enforcer.check_input_policy(
                    pool_id=pool_id,
                    agent_type=agent_type,
                    tool_name=tool_name,
                    model=model,
                    requested_cost=requested_cost,
                    trace_id=trace_id,
                )

            # Execute function
            result = func(*args, **kwargs)

            # Check output policy (if result contains evidence)
            if pool_id and agent_type and isinstance(result, dict):
                bead_id = kwargs.get("bead_id") or result.get("bead_id")
                evidence_refs = result.get("evidence_refs", [])
                confidence_from = result.get("confidence_from")
                confidence_to = result.get("confidence_to")

                if bead_id and confidence_to:
                    enforcer.check_output_policy(
                        bead_id=bead_id,
                        pool_id=pool_id,
                        agent_type=agent_type,
                        evidence_refs=evidence_refs,
                        confidence_from=confidence_from,
                        confidence_to=confidence_to,
                        trace_id=trace_id,
                    )

            return result

        return wrapper

    return decorator
