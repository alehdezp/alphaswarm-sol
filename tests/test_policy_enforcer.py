"""Tests for governance policy enforcement.

Tests PolicyEnforcer class and validators:
- Cost budget hard/soft limits
- Tool access role restrictions
- Evidence integrity requirements
- Model usage tier restrictions
- enforce_policy decorator integration
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from alphaswarm_sol.governance import (
    PolicyAction,
    PolicyEnforcer,
    PolicyViolation,
    PolicyViolationError,
    enforce_policy,
)
from alphaswarm_sol.governance.policies import (
    CostPolicy,
    EvidencePolicy,
    ModelUsagePolicy,
    ToolAccessPolicy,
)
from alphaswarm_sol.governance.validators import (
    validate_cost_budget,
    validate_evidence_integrity,
    validate_model_usage,
    validate_tool_access,
)
from alphaswarm_sol.metrics.cost_ledger import CostLedger, PoolBudget
from alphaswarm_sol.observability.audit import AuditLogger


@pytest.fixture
def test_policies_path(tmp_path: Path) -> Path:
    """Create temporary test policy configuration."""
    config_path = tmp_path / "test_policies.yaml"
    config_path.write_text(
        """
metadata:
  version: "1.0"
  description: "Test policies"

policies:
  cost_budget:
    hard_limit_usd: 10.0
    soft_limit_usd: 8.0
    enabled: true
    block_on_exceed: true

  tool_access:
    enabled: true
    role_restrictions:
      vrs-attacker:
        - slither
        - mythril
      vrs-defender:
        - slither
        - aderyn
    forbidden_tools:
      - shell_exec

  evidence_integrity:
    enabled: true
    require_evidence_refs: true
    min_evidence_count: 1

  model_usage:
    enabled: true
    tier_restrictions:
      vrs-attacker:
        - opus
        - sonnet
      cost-governor:
        - haiku
    allowed_models: []
"""
    )
    return config_path


@pytest.fixture
def mock_cost_ledger():
    """Create mock cost ledger."""
    ledger = MagicMock(spec=CostLedger)
    ledger.total_cost = 5.0  # Current cost
    return ledger


@pytest.fixture
def mock_audit_logger():
    """Create mock audit logger."""
    return MagicMock(spec=AuditLogger)


# --- Cost Budget Validator Tests ---


def test_validate_cost_budget_hard_limit():
    """Test cost budget hard limit violation."""
    policy = CostPolicy(hard_limit_usd=10.0, soft_limit_usd=8.0, block_on_exceed=True)

    violation = validate_cost_budget(
        current_cost=9.0,
        requested_cost=2.0,  # Would total 11.0 > 10.0
        policy=policy,
        pool_id="pool-123",
    )

    assert violation is not None
    assert violation.policy_id == "cost_budget.hard_limit"
    assert violation.violation_type == "budget_exceeded"
    assert violation.severity == "critical"
    assert violation.action == PolicyAction.BLOCK
    assert "11.00" in violation.message
    assert violation.details["total_cost_usd"] == 11.0


def test_validate_cost_budget_soft_limit():
    """Test cost budget soft limit warning."""
    policy = CostPolicy(hard_limit_usd=10.0, soft_limit_usd=8.0)

    violation = validate_cost_budget(
        current_cost=7.0,
        requested_cost=1.5,  # Would total 8.5 > 8.0 soft, < 10.0 hard
        policy=policy,
        pool_id="pool-123",
    )

    assert violation is not None
    assert violation.policy_id == "cost_budget.soft_limit"
    assert violation.violation_type == "budget_warning"
    assert violation.severity == "medium"
    assert violation.action == PolicyAction.ALERT
    assert "approaching" in violation.message.lower()


def test_validate_cost_budget_within_limits():
    """Test cost budget within limits (no violation)."""
    policy = CostPolicy(hard_limit_usd=10.0, soft_limit_usd=8.0)

    violation = validate_cost_budget(
        current_cost=5.0,
        requested_cost=1.0,  # Would total 6.0 < 8.0 soft
        policy=policy,
        pool_id="pool-123",
    )

    assert violation is None


def test_validate_cost_budget_disabled():
    """Test cost budget validation disabled."""
    policy = CostPolicy(hard_limit_usd=10.0, enabled=False)

    violation = validate_cost_budget(
        current_cost=100.0,
        requested_cost=100.0,  # Way over limit, but disabled
        policy=policy,
        pool_id="pool-123",
    )

    assert violation is None


# --- Tool Access Validator Tests ---


def test_validate_tool_access_forbidden():
    """Test forbidden tool access."""
    policy = ToolAccessPolicy(
        forbidden_tools=["shell_exec"],
        role_restrictions={},
    )

    violation = validate_tool_access(
        tool_name="shell_exec",
        agent_type="vrs-attacker",
        policy=policy,
    )

    assert violation is not None
    assert violation.policy_id == "tool_access.forbidden"
    assert violation.violation_type == "forbidden_tool"
    assert violation.severity == "critical"
    assert violation.action == PolicyAction.BLOCK


def test_validate_tool_access_role_restriction():
    """Test role-based tool restriction."""
    policy = ToolAccessPolicy(
        role_restrictions={
            "vrs-attacker": ["slither", "mythril"],
            "vrs-defender": ["slither", "aderyn"],
        }
    )

    # Attacker trying to use aderyn (only allowed for defender)
    violation = validate_tool_access(
        tool_name="aderyn",
        agent_type="vrs-attacker",
        policy=policy,
    )

    assert violation is not None
    assert violation.policy_id == "tool_access.role_restriction"
    assert violation.violation_type == "unauthorized_tool"
    assert violation.severity == "high"
    assert violation.action == PolicyAction.BLOCK
    assert "aderyn" in violation.message


def test_validate_tool_access_allowed():
    """Test allowed tool access."""
    policy = ToolAccessPolicy(
        role_restrictions={
            "vrs-attacker": ["slither", "mythril"],
        }
    )

    violation = validate_tool_access(
        tool_name="slither",
        agent_type="vrs-attacker",
        policy=policy,
    )

    assert violation is None


def test_validate_tool_access_no_restrictions():
    """Test tool access with no restrictions for agent type."""
    policy = ToolAccessPolicy(
        role_restrictions={
            "vrs-attacker": ["slither"],
        }
    )

    # Different agent type with no restrictions
    violation = validate_tool_access(
        tool_name="any_tool",
        agent_type="vrs-verifier",
        policy=policy,
    )

    assert violation is None


# --- Evidence Integrity Validator Tests ---


def test_validate_evidence_integrity_missing():
    """Test evidence integrity violation for missing evidence refs."""
    policy = EvidencePolicy(require_evidence_refs=True, min_evidence_count=1)

    violation = validate_evidence_integrity(
        evidence_refs=[],  # No evidence
        confidence_from="POSSIBLE",
        confidence_to="LIKELY",
        policy=policy,
        bead_id="VKG-042",
    )

    assert violation is not None
    assert violation.policy_id == "evidence_integrity.missing_evidence"
    assert violation.violation_type == "insufficient_evidence"
    assert violation.severity == "high"
    assert violation.action == PolicyAction.BLOCK


def test_validate_evidence_integrity_sufficient():
    """Test evidence integrity with sufficient evidence."""
    policy = EvidencePolicy(require_evidence_refs=True, min_evidence_count=1)

    violation = validate_evidence_integrity(
        evidence_refs=["ev-001", "ev-002"],
        confidence_from="POSSIBLE",
        confidence_to="LIKELY",
        policy=policy,
        bead_id="VKG-042",
    )

    assert violation is None


def test_validate_evidence_integrity_initial_verdict():
    """Test evidence integrity not enforced for initial verdicts."""
    policy = EvidencePolicy(require_evidence_refs=True, min_evidence_count=1)

    # Initial verdict (confidence_from=None) doesn't require evidence
    violation = validate_evidence_integrity(
        evidence_refs=[],
        confidence_from=None,  # Initial verdict
        confidence_to="POSSIBLE",
        policy=policy,
        bead_id="VKG-042",
    )

    assert violation is None


# --- Model Usage Validator Tests ---


def test_validate_model_usage_tier_restriction():
    """Test model tier restriction violation."""
    policy = ModelUsagePolicy(
        tier_restrictions={
            "cost-governor": ["haiku"],  # Only haiku allowed
        }
    )

    # cost-governor trying to use sonnet
    violation = validate_model_usage(
        model="claude-3-5-sonnet",
        agent_type="cost-governor",
        policy=policy,
    )

    assert violation is not None
    assert violation.policy_id == "model_usage.tier_restriction"
    assert violation.violation_type == "unauthorized_tier"
    assert violation.details["model_tier"] == "sonnet"


def test_validate_model_usage_allowed_tier():
    """Test allowed model tier."""
    policy = ModelUsagePolicy(
        tier_restrictions={
            "vrs-attacker": ["opus", "sonnet"],
        }
    )

    violation = validate_model_usage(
        model="claude-3-5-sonnet",
        agent_type="vrs-attacker",
        policy=policy,
    )

    assert violation is None


def test_validate_model_usage_explicit_allowed():
    """Test explicit allowed models list."""
    policy = ModelUsagePolicy(
        allowed_models=["claude-3-5-sonnet", "claude-3-haiku"],
    )

    # Allowed model
    violation = validate_model_usage(
        model="claude-3-5-sonnet",
        agent_type="any-agent",
        policy=policy,
    )
    assert violation is None

    # Not allowed model
    violation = validate_model_usage(
        model="gpt-4o",
        agent_type="any-agent",
        policy=policy,
    )
    assert violation is not None
    assert violation.policy_id == "model_usage.not_allowed"


# --- PolicyEnforcer Integration Tests ---


def test_enforcer_check_input_policy_cost_violation(
    test_policies_path, mock_cost_ledger, mock_audit_logger
):
    """Test PolicyEnforcer input check with cost violation."""
    enforcer = PolicyEnforcer(
        policies_path=test_policies_path,
        cost_ledger=mock_cost_ledger,
        audit_logger=mock_audit_logger,
    )

    # Mock ledger has 9.0, requesting 2.0 -> 11.0 > 10.0 hard limit
    mock_cost_ledger.total_cost = 9.0

    with pytest.raises(PolicyViolationError) as exc_info:
        enforcer.check_input_policy(
            pool_id="pool-123",
            agent_type="vrs-attacker",
            requested_cost=2.0,
        )

    assert "exceed hard limit" in str(exc_info.value)
    mock_audit_logger.log_policy_violation.assert_called_once()


def test_enforcer_check_input_policy_tool_violation(
    test_policies_path, mock_cost_ledger, mock_audit_logger
):
    """Test PolicyEnforcer input check with tool access violation."""
    enforcer = PolicyEnforcer(
        policies_path=test_policies_path,
        cost_ledger=mock_cost_ledger,
        audit_logger=mock_audit_logger,
    )

    with pytest.raises(PolicyViolationError) as exc_info:
        enforcer.check_input_policy(
            pool_id="pool-123",
            agent_type="vrs-attacker",
            tool_name="shell_exec",  # Forbidden tool
        )

    assert "forbidden" in str(exc_info.value).lower()
    mock_audit_logger.log_policy_violation.assert_called_once()


def test_enforcer_check_output_policy_evidence_violation(
    test_policies_path, mock_cost_ledger, mock_audit_logger
):
    """Test PolicyEnforcer output check with evidence violation."""
    enforcer = PolicyEnforcer(
        policies_path=test_policies_path,
        cost_ledger=mock_cost_ledger,
        audit_logger=mock_audit_logger,
    )

    with pytest.raises(PolicyViolationError) as exc_info:
        enforcer.check_output_policy(
            bead_id="VKG-042",
            pool_id="pool-123",
            agent_type="vrs-attacker",
            evidence_refs=[],  # No evidence
            confidence_from="POSSIBLE",
            confidence_to="LIKELY",
        )

    assert "evidence" in str(exc_info.value).lower()
    mock_audit_logger.log_policy_violation.assert_called_once()


def test_enforcer_check_input_policy_soft_limit_alert(
    test_policies_path, mock_cost_ledger, mock_audit_logger
):
    """Test PolicyEnforcer soft limit logs alert but continues."""
    enforcer = PolicyEnforcer(
        policies_path=test_policies_path,
        cost_ledger=mock_cost_ledger,
        audit_logger=mock_audit_logger,
    )

    # Mock ledger has 7.0, requesting 1.5 -> 8.5 > 8.0 soft, < 10.0 hard
    mock_cost_ledger.total_cost = 7.0

    # Should NOT raise, just log
    violation = enforcer.check_input_policy(
        pool_id="pool-123",
        agent_type="vrs-attacker",
        requested_cost=1.5,
    )

    assert violation is not None
    assert violation.action == PolicyAction.ALERT
    mock_audit_logger.log_policy_violation.assert_called_once()


# --- Decorator Tests ---


def test_enforce_policy_decorator(test_policies_path, mock_cost_ledger, mock_audit_logger):
    """Test enforce_policy decorator applies checks."""
    enforcer = PolicyEnforcer(
        policies_path=test_policies_path,
        cost_ledger=mock_cost_ledger,
        audit_logger=mock_audit_logger,
    )

    @enforce_policy(enforcer)
    def test_handler(pool_id: str, agent_type: str, tool_name: str = None):
        return {"status": "success"}

    # Should work for allowed tool
    result = test_handler(
        pool_id="pool-123",
        agent_type="vrs-attacker",
        tool_name="slither",
    )
    assert result["status"] == "success"

    # Should raise for forbidden tool
    with pytest.raises(PolicyViolationError):
        test_handler(
            pool_id="pool-123",
            agent_type="vrs-attacker",
            tool_name="shell_exec",
        )


def test_enforce_policy_decorator_output_check(
    test_policies_path, mock_cost_ledger, mock_audit_logger
):
    """Test enforce_policy decorator checks output."""
    enforcer = PolicyEnforcer(
        policies_path=test_policies_path,
        cost_ledger=mock_cost_ledger,
        audit_logger=mock_audit_logger,
    )

    @enforce_policy(enforcer)
    def test_handler(pool_id: str, bead_id: str, agent_type: str):
        # Return result with confidence upgrade but no evidence
        return {
            "bead_id": bead_id,
            "confidence_from": "POSSIBLE",
            "confidence_to": "LIKELY",
            "evidence_refs": [],  # No evidence - should violate
        }

    # Should raise for missing evidence
    with pytest.raises(PolicyViolationError):
        test_handler(
            pool_id="pool-123",
            bead_id="VKG-042",
            agent_type="vrs-attacker",
        )
