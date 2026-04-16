"""Tests for model tier routing and escalation.

Tests the TierRoutingPolicy and its integration with subagents and routers.
"""

import pytest
from alphaswarm_sol.llm.routing_policy import (
    TierRoutingPolicy,
    RoutingDecision,
    EscalationReason,
    EscalationThresholds,
    TASK_DEFAULT_TIERS,
    create_routing_policy,
    route_task,
)
from alphaswarm_sol.llm.tiers import (
    ModelTier,
    ModelTierConfig,
    PolicyAwareTierRouter,
    create_policy_aware_router,
)


class TestTierRoutingPolicy:
    """Tests for TierRoutingPolicy."""

    def test_policy_has_tier_properties(self):
        """Policy exposes validator, specialist, and expert tiers."""
        policy = TierRoutingPolicy()

        assert policy.validator_tier == ModelTier.CHEAP
        assert policy.specialist_tier == ModelTier.STANDARD
        assert policy.expert_tier == ModelTier.PREMIUM

    def test_default_tier_for_simple_tasks(self):
        """Simple tasks default to CHEAP tier."""
        policy = TierRoutingPolicy()

        for task_type in ["evidence_extraction", "pattern_validation", "code_parsing"]:
            decision = policy.route(task_type=task_type)
            assert decision.tier == ModelTier.CHEAP, f"{task_type} should use CHEAP tier"

    def test_default_tier_for_standard_tasks(self):
        """Standard analysis tasks default to STANDARD tier."""
        policy = TierRoutingPolicy()

        for task_type in ["tier_b_verification", "context_analysis", "fp_filtering"]:
            decision = policy.route(task_type=task_type)
            assert decision.tier == ModelTier.STANDARD, f"{task_type} should use STANDARD tier"

    def test_default_tier_for_complex_tasks(self):
        """Complex reasoning tasks default to PREMIUM tier."""
        policy = TierRoutingPolicy()

        for task_type in ["exploit_synthesis", "business_logic_analysis", "attack_path_generation"]:
            decision = policy.route(task_type=task_type)
            assert decision.tier == ModelTier.PREMIUM, f"{task_type} should use PREMIUM tier"

    def test_escalation_on_high_risk(self):
        """High risk score triggers escalation to higher tier."""
        policy = TierRoutingPolicy()

        # CHEAP task with high risk should escalate to STANDARD
        decision = policy.route(
            task_type="pattern_validation",
            risk_score=0.6,
        )
        assert decision.tier == ModelTier.STANDARD
        assert decision.was_escalated
        assert EscalationReason.HIGH_RISK in decision.escalation_reasons

        # CHEAP task with very high risk should escalate to PREMIUM
        decision = policy.route(
            task_type="pattern_validation",
            risk_score=0.9,
        )
        assert decision.tier == ModelTier.PREMIUM
        assert decision.was_escalated

    def test_escalation_on_low_evidence(self):
        """Low evidence completeness triggers escalation."""
        policy = TierRoutingPolicy()

        # CHEAP task with low evidence should escalate to STANDARD
        decision = policy.route(
            task_type="pattern_validation",
            evidence_completeness=0.2,
        )
        assert decision.tier == ModelTier.STANDARD
        assert decision.was_escalated
        assert EscalationReason.LOW_EVIDENCE in decision.escalation_reasons

    def test_escalation_on_critical_severity(self):
        """Critical severity triggers escalation."""
        policy = TierRoutingPolicy()

        decision = policy.route(
            task_type="pattern_validation",
            severity="critical",
        )
        assert decision.tier == ModelTier.STANDARD
        assert decision.was_escalated
        assert EscalationReason.CRITICAL_SEVERITY in decision.escalation_reasons

    def test_escalation_on_complex_pattern(self):
        """Complex pattern types trigger escalation to PREMIUM."""
        policy = TierRoutingPolicy()

        complex_patterns = [
            "business-logic-vuln",
            "cross-contract-call",
            "flash-loan-attack",
            "governance-manipulation",
        ]

        for pattern in complex_patterns:
            decision = policy.route(
                task_type="tier_b_verification",
                pattern_type=pattern,
            )
            assert decision.tier == ModelTier.PREMIUM, f"{pattern} should escalate to PREMIUM"
            assert EscalationReason.COMPLEX_PATTERN in decision.escalation_reasons

    def test_budget_downgrade_to_standard(self):
        """Low budget downgrades PREMIUM to STANDARD."""
        policy = TierRoutingPolicy()

        decision = policy.route(
            task_type="exploit_synthesis",  # Normally PREMIUM
            budget_remaining=1.5,  # Below low threshold (2.0)
        )
        assert decision.tier == ModelTier.STANDARD
        assert decision.was_downgraded
        assert EscalationReason.BUDGET_LIMITED in decision.escalation_reasons

    def test_budget_downgrade_to_cheap(self):
        """Critical budget forces CHEAP tier."""
        policy = TierRoutingPolicy()

        decision = policy.route(
            task_type="exploit_synthesis",  # Normally PREMIUM
            budget_remaining=0.3,  # Below critical threshold (0.5)
        )
        assert decision.tier == ModelTier.CHEAP
        assert decision.was_downgraded
        assert EscalationReason.BUDGET_LIMITED in decision.escalation_reasons

    def test_no_budget_constraint(self):
        """Unlimited budget doesn't affect tier selection."""
        policy = TierRoutingPolicy()

        # No budget_remaining means unlimited
        decision = policy.route(
            task_type="exploit_synthesis",
            budget_remaining=None,
        )
        assert decision.tier == ModelTier.PREMIUM
        assert not decision.was_downgraded

    def test_routing_decision_has_metadata(self):
        """Routing decision includes complete metadata."""
        policy = TierRoutingPolicy()

        decision = policy.route(
            task_type="tier_b_verification",
            risk_score=0.7,
            evidence_completeness=0.5,
            budget_remaining=5.0,
            severity="high",
            pattern_type="reentrancy",
            pool_id="pool-123",
            workflow_id="workflow-456",
        )

        assert decision.rationale
        assert decision.estimated_cost_usd > 0
        assert decision.original_tier is not None
        assert decision.metadata["task_type"] == "tier_b_verification"
        assert decision.metadata["risk_score"] == 0.7
        assert decision.metadata["evidence_completeness"] == 0.5
        assert decision.metadata["pool_id"] == "pool-123"
        assert decision.metadata["workflow_id"] == "workflow-456"

    def test_routing_decision_to_dict(self):
        """Routing decision serializes to dictionary."""
        policy = TierRoutingPolicy()

        decision = policy.route(task_type="pattern_validation")
        data = decision.to_dict()

        assert "tier" in data
        assert "rationale" in data
        assert "escalation_reasons" in data
        assert "estimated_cost_usd" in data
        assert "timestamp" in data

    def test_custom_thresholds(self):
        """Custom thresholds affect routing behavior."""
        # Very sensitive thresholds
        thresholds = EscalationThresholds(
            risk_score_standard=0.3,
            risk_score_premium=0.5,
            evidence_completeness_low=0.5,
        )
        policy = TierRoutingPolicy(thresholds=thresholds)

        # Low risk should now escalate
        decision = policy.route(
            task_type="pattern_validation",
            risk_score=0.4,
        )
        assert decision.tier == ModelTier.STANDARD

    def test_escalation_path(self):
        """Get escalation path from a tier."""
        policy = TierRoutingPolicy()

        assert policy.get_escalation_path(ModelTier.CHEAP) == [
            ModelTier.STANDARD,
            ModelTier.PREMIUM,
        ]
        assert policy.get_escalation_path(ModelTier.STANDARD) == [ModelTier.PREMIUM]
        assert policy.get_escalation_path(ModelTier.PREMIUM) == []


class TestPolicyAwareTierRouter:
    """Tests for PolicyAwareTierRouter."""

    def test_router_uses_policy(self):
        """Router uses policy for tier selection."""
        router = PolicyAwareTierRouter()

        decision = router.route_with_policy(
            task_type="tier_b_verification",
            risk_score=0.5,
        )

        assert decision.tier in [ModelTier.CHEAP, ModelTier.STANDARD, ModelTier.PREMIUM]
        assert decision.rationale

    def test_router_with_custom_policy(self):
        """Router accepts custom policy."""
        policy = TierRoutingPolicy(
            thresholds=EscalationThresholds(risk_score_standard=0.2)
        )
        router = PolicyAwareTierRouter(policy=policy)

        decision = router.route_with_policy(
            task_type="pattern_validation",
            risk_score=0.3,  # Should escalate with custom threshold
        )
        assert decision.tier == ModelTier.STANDARD

    def test_factory_function(self):
        """Factory function creates configured router."""
        router = create_policy_aware_router()

        assert router is not None
        assert router.policy is not None


class TestRoutingConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_routing_policy(self):
        """Create policy with custom thresholds."""
        policy = create_routing_policy(
            risk_threshold=0.4,
            evidence_threshold=0.4,
            budget_threshold=3.0,
        )

        assert policy.thresholds.risk_score_standard == 0.4
        assert policy.thresholds.evidence_completeness_low == 0.4
        assert policy.thresholds.budget_low_threshold_usd == 3.0

    def test_route_task_convenience(self):
        """Route single task with convenience function."""
        decision = route_task(
            task_type="pattern_validation",
            risk_score=0.2,
            evidence_completeness=0.8,
        )

        assert decision.tier == ModelTier.CHEAP
        assert not decision.was_escalated


class TestTaskDefaultTiers:
    """Tests for task type default tiers."""

    def test_all_task_types_have_defaults(self):
        """Verify key task types have default tiers."""
        # CHEAP tier tasks
        assert TASK_DEFAULT_TIERS.get("evidence_extraction") == ModelTier.CHEAP
        assert TASK_DEFAULT_TIERS.get("pattern_validation") == ModelTier.CHEAP

        # STANDARD tier tasks
        assert TASK_DEFAULT_TIERS.get("tier_b_verification") == ModelTier.STANDARD
        assert TASK_DEFAULT_TIERS.get("context_analysis") == ModelTier.STANDARD

        # PREMIUM tier tasks
        assert TASK_DEFAULT_TIERS.get("exploit_synthesis") == ModelTier.PREMIUM
        assert TASK_DEFAULT_TIERS.get("business_logic_analysis") == ModelTier.PREMIUM


class TestEscalationThresholds:
    """Tests for EscalationThresholds."""

    def test_default_thresholds(self):
        """Default thresholds have sensible values."""
        thresholds = EscalationThresholds()

        assert 0 < thresholds.risk_score_standard < thresholds.risk_score_premium <= 1.0
        assert 0 < thresholds.evidence_completeness_low < thresholds.evidence_completeness_high <= 1.0
        assert 0 < thresholds.budget_critical_threshold_usd < thresholds.budget_low_threshold_usd

    def test_thresholds_to_dict(self):
        """Thresholds serialize to dictionary."""
        thresholds = EscalationThresholds()
        data = thresholds.to_dict()

        assert "risk_score_standard" in data
        assert "risk_score_premium" in data
        assert "evidence_completeness_low" in data
        assert "budget_low_threshold_usd" in data


class TestValidatorFirstBehavior:
    """Tests verifying validator-first approach."""

    def test_cheap_tier_is_default_for_unknown_tasks(self):
        """Unknown task types default to CHEAP (validator) tier."""
        policy = TierRoutingPolicy()

        decision = policy.route(task_type="unknown_task_type")
        assert decision.tier == ModelTier.CHEAP

    def test_escalation_only_when_needed(self):
        """Escalation only happens when conditions warrant it."""
        policy = TierRoutingPolicy()

        # Standard task with good evidence and low risk should stay STANDARD
        decision = policy.route(
            task_type="tier_b_verification",
            risk_score=0.3,
            evidence_completeness=0.9,
        )
        assert decision.tier == ModelTier.STANDARD
        assert not decision.was_escalated

    def test_multiple_escalation_reasons_combine(self):
        """Multiple escalation conditions combine correctly."""
        policy = TierRoutingPolicy()

        decision = policy.route(
            task_type="pattern_validation",  # Default CHEAP
            risk_score=0.9,  # HIGH_RISK -> escalate
            evidence_completeness=0.1,  # LOW_EVIDENCE -> escalate
            severity="critical",  # CRITICAL_SEVERITY -> escalate
        )

        assert decision.tier == ModelTier.PREMIUM
        assert decision.was_escalated
        # Should have HIGH_RISK as primary reason (risk_score >= 0.8 -> PREMIUM)
        assert EscalationReason.HIGH_RISK in decision.escalation_reasons


class TestRoutingIntegration:
    """Integration tests for routing with subagents."""

    @pytest.mark.asyncio
    async def test_subagent_manager_uses_policy(self):
        """LLMSubagentManager uses routing policy."""
        from alphaswarm_sol.llm.subagents import (
            LLMSubagentManager,
            SubagentTask,
            TaskType,
        )

        manager = LLMSubagentManager(budget_usd=10.0)

        task = SubagentTask(
            type=TaskType.TIER_B_VERIFICATION,
            prompt="Test prompt",
            context={},
            risk_score=0.7,
            evidence_completeness=0.4,
        )

        result = await manager.dispatch(task)

        # Result should have routing metadata
        assert result.routing_decision is not None
        assert result.tier_rationale
        assert result.escalation_reasons

    @pytest.mark.asyncio
    async def test_subagent_budget_tracking(self):
        """LLMSubagentManager tracks budget correctly."""
        from alphaswarm_sol.llm.subagents import (
            LLMSubagentManager,
            SubagentTask,
            TaskType,
        )

        initial_budget = 10.0
        manager = LLMSubagentManager(budget_usd=initial_budget)

        assert manager.budget_remaining == initial_budget

        task = SubagentTask(
            type=TaskType.PATTERN_VALIDATION,
            prompt="Test prompt",
            context={},
        )

        await manager.dispatch(task)

        # Budget should be reduced (mock execution costs $0.001)
        assert manager.budget_remaining is not None
        # Note: The mock returns 0.001 cost which gets tracked
