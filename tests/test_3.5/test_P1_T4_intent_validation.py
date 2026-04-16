"""
Tests for P1-T4: Intent Validation

Tests the validation of LLM-inferred intents against VKG properties.
"""

import pytest
from typing import List

from alphaswarm_sol.kg.schema import Node, Evidence
from alphaswarm_sol.intent import (
    IntentValidator,
    ValidationResult,
    INTENT_VALIDATION_RULES,
    FunctionIntent,
    BusinessPurpose,
    TrustLevel,
    TrustAssumption,
    InferredInvariant,
)


# Test Fixtures


@pytest.fixture
def validator():
    """Create validator instance."""
    return IntentValidator()


@pytest.fixture
def withdrawal_intent():
    """Create withdrawal intent."""
    return FunctionIntent(
        business_purpose=BusinessPurpose.WITHDRAWAL,
        purpose_confidence=0.9,
        purpose_reasoning="Transfers value to user",
        expected_trust_level=TrustLevel.DEPOSITOR_ONLY,
        authorized_callers=["depositor"],
        trust_assumptions=[],
        inferred_invariants=[],
        likely_specs=[],
        spec_confidence={},
        risk_notes=[],
        complexity_score=0.5,
    )


@pytest.fixture
def view_only_intent():
    """Create view-only intent."""
    return FunctionIntent(
        business_purpose=BusinessPurpose.VIEW_ONLY,
        purpose_confidence=0.95,
        purpose_reasoning="Read-only function",
        expected_trust_level=TrustLevel.PERMISSIONLESS,
        authorized_callers=["anyone"],
        trust_assumptions=[],
        inferred_invariants=[],
        likely_specs=[],
        spec_confidence={},
        risk_notes=[],
        complexity_score=0.2,
    )


@pytest.fixture
def admin_config_intent():
    """Create admin config intent."""
    return FunctionIntent(
        business_purpose=BusinessPurpose.SET_PARAMETER,
        purpose_confidence=0.85,
        purpose_reasoning="Modifies critical state",
        expected_trust_level=TrustLevel.OWNER_ONLY,
        authorized_callers=["owner"],
        trust_assumptions=[],
        inferred_invariants=[],
        likely_specs=[],
        spec_confidence={},
        risk_notes=[],
        complexity_score=0.4,
    )


def create_function_node(
    fn_id: str,
    label: str,
    semantic_ops: List[str],
    **extra_properties,
) -> Node:
    """Helper to create function node with semantic operations."""
    properties = {
        "semantic_ops": semantic_ops,
        **extra_properties,
    }

    return Node(
        id=fn_id,
        label=label,
        type="Function",
        properties=properties,
        evidence=[],
    )


# Validation Rules Tests


class TestValidationRules:
    """Test validation rules structure."""

    def test_rules_exist_for_common_purposes(self):
        """Common business purposes should have validation rules."""
        common_purposes = [
            BusinessPurpose.WITHDRAWAL,
            BusinessPurpose.DEPOSIT,
            BusinessPurpose.VIEW_ONLY,
            BusinessPurpose.SET_PARAMETER,
            BusinessPurpose.SWAP,
            BusinessPurpose.LIQUIDATE,
        ]

        for purpose in common_purposes:
            assert purpose in INTENT_VALIDATION_RULES
            rules = INTENT_VALIDATION_RULES[purpose]
            assert "required_ops" in rules
            assert "expected_ops" in rules
            assert "forbidden_ops" in rules
            assert "expected_trust" in rules

    def test_view_only_has_strict_rules(self):
        """VIEW_ONLY should forbid state-changing operations."""
        rules = INTENT_VALIDATION_RULES[BusinessPurpose.VIEW_ONLY]

        assert "TRANSFERS_VALUE_OUT" in rules["forbidden_ops"]
        assert "WRITES_USER_BALANCE" in rules["forbidden_ops"]
        assert "MODIFIES_CRITICAL_STATE" in rules["forbidden_ops"]
        assert TrustLevel.PERMISSIONLESS in rules["expected_trust"]

    def test_withdrawal_requires_transfer(self):
        """WITHDRAWAL should require value transfer out."""
        rules = INTENT_VALIDATION_RULES[BusinessPurpose.WITHDRAWAL]

        assert "TRANSFERS_VALUE_OUT" in rules["required_ops"]

    def test_admin_requires_critical_state_change(self):
        """SET_PARAMETER should require critical state modification."""
        rules = INTENT_VALIDATION_RULES[BusinessPurpose.SET_PARAMETER]

        assert "MODIFIES_CRITICAL_STATE" in rules["required_ops"]


# IntentValidator Tests


class TestIntentValidator:
    """Test IntentValidator functionality."""

    def test_validator_creation(self, validator):
        """Test creating validator."""
        assert validator is not None
        assert isinstance(validator, IntentValidator)

    def test_valid_withdrawal(self, validator, withdrawal_intent):
        """Test validating correct withdrawal function."""
        fn_node = create_function_node(
            "fn_1",
            "withdraw",
            semantic_ops=[
                "TRANSFERS_VALUE_OUT",
                "READS_USER_BALANCE",
                "WRITES_USER_BALANCE",
            ],
        )

        result = validator.validate(fn_node, withdrawal_intent)

        assert result.is_valid
        assert result.confidence_adjustment == 1.0
        assert len(result.issues) == 0
        assert result.recommendation == "accept"

    def test_invalid_withdrawal_missing_transfer(self, validator, withdrawal_intent):
        """Test withdrawal without value transfer (hallucination)."""
        fn_node = create_function_node(
            "fn_1",
            "withdraw",
            semantic_ops=["READS_USER_BALANCE", "WRITES_USER_BALANCE"],
        )

        result = validator.validate(fn_node, withdrawal_intent)

        assert not result.is_valid
        assert result.confidence_adjustment < 1.0
        assert len(result.issues) > 0
        assert "Missing required operations" in result.issues[0]
        assert result.recommendation in ["review", "reject"]

    def test_valid_view_only(self, validator, view_only_intent):
        """Test validating correct view-only function."""
        fn_node = create_function_node(
            "fn_1",
            "getBalance",
            semantic_ops=["READS_USER_BALANCE"],
        )

        result = validator.validate(fn_node, view_only_intent)

        assert result.is_valid
        assert result.confidence_adjustment == 1.0
        assert len(result.issues) == 0
        assert result.recommendation == "accept"

    def test_invalid_view_only_has_transfer(self, validator, view_only_intent):
        """Test view-only with forbidden transfer (hallucination)."""
        fn_node = create_function_node(
            "fn_1",
            "getBalance",
            semantic_ops=["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
        )

        result = validator.validate(fn_node, view_only_intent)

        assert not result.is_valid
        assert result.confidence_adjustment < 1.0
        assert len(result.issues) > 0
        assert "forbidden operations" in result.issues[0].lower()
        assert result.recommendation in ["review", "reject"]

    def test_invalid_view_only_modifies_state(self, validator, view_only_intent):
        """Test view-only with state modification (hallucination)."""
        fn_node = create_function_node(
            "fn_1",
            "getBalance",
            semantic_ops=["READS_USER_BALANCE", "MODIFIES_CRITICAL_STATE"],
        )

        result = validator.validate(fn_node, view_only_intent)

        assert not result.is_valid
        assert result.confidence_adjustment < 1.0
        assert "MODIFIES_CRITICAL_STATE" in result.issues[0]

    def test_valid_admin_config(self, validator, admin_config_intent):
        """Test validating correct admin config function."""
        fn_node = create_function_node(
            "fn_1",
            "setFee",
            semantic_ops=["MODIFIES_CRITICAL_STATE"],
        )

        result = validator.validate(fn_node, admin_config_intent)

        assert result.is_valid
        assert result.confidence_adjustment == 1.0
        assert len(result.issues) == 0

    def test_invalid_admin_wrong_trust_level(self, validator):
        """Test admin function with wrong trust level."""
        # Create admin intent with wrong trust level
        intent = FunctionIntent(
            business_purpose=BusinessPurpose.SET_PARAMETER,
            purpose_confidence=0.85,
            purpose_reasoning="Admin function",
            expected_trust_level=TrustLevel.PERMISSIONLESS,  # Wrong!
            authorized_callers=["anyone"],
            trust_assumptions=[],
            inferred_invariants=[],
            likely_specs=[],
            spec_confidence={},
            risk_notes=[],
            complexity_score=0.4,
        )

        fn_node = create_function_node(
            "fn_1",
            "setFee",
            semantic_ops=["MODIFIES_CRITICAL_STATE"],
        )

        result = validator.validate(fn_node, intent)

        assert not result.is_valid
        assert result.confidence_adjustment < 1.0
        assert any("trust level" in issue.lower() for issue in result.issues)

    def test_uncommon_business_purpose(self, validator):
        """Test validation for uncommon business purpose without rules."""
        # Create intent for purpose not in validation rules
        intent = FunctionIntent(
            business_purpose=BusinessPurpose.UNKNOWN,
            purpose_confidence=0.8,
            purpose_reasoning="Custom function",
            expected_trust_level=TrustLevel.PERMISSIONLESS,
            authorized_callers=["anyone"],
            trust_assumptions=[],
            inferred_invariants=[],
            likely_specs=[],
            spec_confidence={},
            risk_notes=[],
            complexity_score=0.5,
        )

        fn_node = create_function_node("fn_1", "custom", semantic_ops=[])

        result = validator.validate(fn_node, intent)

        assert result.is_valid  # No rules = pass
        assert result.confidence_adjustment == 0.9  # Slight penalty
        assert result.recommendation == "review"


# Batch Validation Tests


class TestBatchValidation:
    """Test batch validation functionality."""

    def test_validate_batch(self, validator, withdrawal_intent, view_only_intent):
        """Test validating multiple intents at once."""
        fn1 = create_function_node(
            "fn_1",
            "withdraw",
            semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )
        fn2 = create_function_node(
            "fn_2",
            "getBalance",
            semantic_ops=["READS_USER_BALANCE"],
        )

        results = validator.validate_batch([
            (fn1, withdrawal_intent),
            (fn2, view_only_intent),
        ])

        assert len(results) == 2
        assert all(isinstance(r, ValidationResult) for r in results)

    def test_batch_with_mixed_validity(self, validator):
        """Test batch with both valid and invalid intents."""
        # Valid withdrawal
        fn1 = create_function_node(
            "fn_1",
            "withdraw",
            semantic_ops=["TRANSFERS_VALUE_OUT", "READS_USER_BALANCE", "WRITES_USER_BALANCE"],
        )
        intent1 = FunctionIntent(
            business_purpose=BusinessPurpose.WITHDRAWAL,
            purpose_confidence=0.9,
            purpose_reasoning="Withdrawal",
            expected_trust_level=TrustLevel.DEPOSITOR_ONLY,
            authorized_callers=["depositor"],
            trust_assumptions=[],
            inferred_invariants=[],
            likely_specs=[],
            spec_confidence={},
            risk_notes=[],
            complexity_score=0.5,
        )

        # Invalid view-only (has transfer)
        fn2 = create_function_node(
            "fn_2",
            "getBalance",
            semantic_ops=["TRANSFERS_VALUE_OUT"],  # Forbidden!
        )
        intent2 = FunctionIntent(
            business_purpose=BusinessPurpose.VIEW_ONLY,
            purpose_confidence=0.9,
            purpose_reasoning="View only",
            expected_trust_level=TrustLevel.PERMISSIONLESS,
            authorized_callers=["anyone"],
            trust_assumptions=[],
            inferred_invariants=[],
            likely_specs=[],
            spec_confidence={},
            risk_notes=[],
            complexity_score=0.2,
        )

        results = validator.validate_batch([
            (fn1, intent1),
            (fn2, intent2),
        ])

        assert results[0].is_valid
        assert not results[1].is_valid


# Confidence Adjustment Tests


class TestConfidenceAdjustment:
    """Test confidence adjustment functionality."""

    def test_compute_adjusted_confidence_valid(self, validator, withdrawal_intent):
        """Test adjusted confidence for valid intent."""
        fn_node = create_function_node(
            "fn_1",
            "withdraw",
            semantic_ops=["TRANSFERS_VALUE_OUT", "READS_USER_BALANCE", "WRITES_USER_BALANCE"],
        )

        result = validator.validate(fn_node, withdrawal_intent)
        adjusted = validator.compute_adjusted_confidence(withdrawal_intent, result)

        # Original: 0.9, adjustment: 1.0 → 0.9
        assert adjusted == pytest.approx(0.9)

    def test_compute_adjusted_confidence_invalid(self, validator, view_only_intent):
        """Test adjusted confidence for invalid intent."""
        fn_node = create_function_node(
            "fn_1",
            "getBalance",
            semantic_ops=["TRANSFERS_VALUE_OUT"],  # Forbidden
        )

        result = validator.validate(fn_node, view_only_intent)
        adjusted = validator.compute_adjusted_confidence(view_only_intent, result)

        # Should be significantly reduced
        assert adjusted < view_only_intent.purpose_confidence
        assert adjusted < 0.7

    def test_get_high_confidence_intents(self, validator):
        """Test filtering to high-confidence intents."""
        # High confidence valid intent
        intent1 = FunctionIntent(
            business_purpose=BusinessPurpose.WITHDRAWAL,
            purpose_confidence=0.9,
            purpose_reasoning="Withdrawal",
            expected_trust_level=TrustLevel.DEPOSITOR_ONLY,
            authorized_callers=["depositor"],
            trust_assumptions=[],
            inferred_invariants=[],
            likely_specs=[],
            spec_confidence={},
            risk_notes=[],
            complexity_score=0.5,
        )
        result1 = ValidationResult(
            is_valid=True,
            confidence_adjustment=1.0,
            issues=[],
            recommendation="accept",
        )

        # Low confidence invalid intent
        intent2 = FunctionIntent(
            business_purpose=BusinessPurpose.VIEW_ONLY,
            purpose_confidence=0.6,
            purpose_reasoning="View",
            expected_trust_level=TrustLevel.PERMISSIONLESS,
            authorized_callers=["anyone"],
            trust_assumptions=[],
            inferred_invariants=[],
            likely_specs=[],
            spec_confidence={},
            risk_notes=[],
            complexity_score=0.2,
        )
        result2 = ValidationResult(
            is_valid=False,
            confidence_adjustment=0.5,
            issues=["Issue"],
            recommendation="reject",
        )

        high_conf = validator.get_high_confidence_intents(
            [(intent1, result1), (intent2, result2)],
            threshold=0.7,
        )

        assert len(high_conf) == 1
        assert high_conf[0] == intent1


# Integration Tests


class TestValidationIntegration:
    """Test validation in realistic scenarios."""

    def test_deposit_function_validation(self, validator):
        """Test validating deposit function."""
        deposit_intent = FunctionIntent(
            business_purpose=BusinessPurpose.DEPOSIT,
            purpose_confidence=0.9,
            purpose_reasoning="Deposits ETH",
            expected_trust_level=TrustLevel.PERMISSIONLESS,
            authorized_callers=["anyone"],
            trust_assumptions=[],
            inferred_invariants=[],
            likely_specs=[],
            spec_confidence={},
            risk_notes=[],
            complexity_score=0.3,
        )

        fn_node = create_function_node(
            "fn_1",
            "deposit",
            semantic_ops=["RECEIVES_VALUE_IN", "WRITES_USER_BALANCE"],
        )

        result = validator.validate(fn_node, deposit_intent)

        assert result.is_valid
        assert result.recommendation == "accept"

    def test_swap_function_validation(self, validator):
        """Test validating swap function."""
        swap_intent = FunctionIntent(
            business_purpose=BusinessPurpose.SWAP,
            purpose_confidence=0.85,
            purpose_reasoning="Token swap",
            expected_trust_level=TrustLevel.PERMISSIONLESS,
            authorized_callers=["anyone"],
            trust_assumptions=[],
            inferred_invariants=[],
            likely_specs=[],
            spec_confidence={},
            risk_notes=[],
            complexity_score=0.7,
        )

        fn_node = create_function_node(
            "fn_1",
            "swap",
            semantic_ops=["CALLS_EXTERNAL", "WRITES_USER_BALANCE"],
        )

        result = validator.validate(fn_node, swap_intent)

        assert result.is_valid
        assert result.recommendation == "accept"

    def test_ownership_transfer_validation(self, validator):
        """Test validating ownership transfer."""
        transfer_intent = FunctionIntent(
            business_purpose=BusinessPurpose.TRANSFER_OWNERSHIP,
            purpose_confidence=0.95,
            purpose_reasoning="Transfers ownership",
            expected_trust_level=TrustLevel.OWNER_ONLY,
            authorized_callers=["owner"],
            trust_assumptions=[],
            inferred_invariants=[],
            likely_specs=[],
            spec_confidence={},
            risk_notes=[],
            complexity_score=0.3,
        )

        fn_node = create_function_node(
            "fn_1",
            "transferOwnership",
            semantic_ops=["MODIFIES_OWNER"],
        )

        result = validator.validate(fn_node, transfer_intent)

        assert result.is_valid
        assert result.recommendation == "accept"


# Edge Cases and Recommendation Tests


class TestRecommendations:
    """Test recommendation logic."""

    def test_accept_recommendation(self, validator, withdrawal_intent):
        """Test 'accept' recommendation for high confidence."""
        fn_node = create_function_node(
            "fn_1",
            "withdraw",
            semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )

        result = validator.validate(fn_node, withdrawal_intent)

        assert result.confidence_adjustment >= 0.8
        assert result.recommendation == "accept"

    def test_review_recommendation(self, validator):
        """Test 'review' recommendation for medium confidence."""
        intent = FunctionIntent(
            business_purpose=BusinessPurpose.WITHDRAWAL,
            purpose_confidence=0.9,
            purpose_reasoning="Withdrawal",
            expected_trust_level=TrustLevel.DEPOSITOR_ONLY,
            authorized_callers=["depositor"],
            trust_assumptions=[],
            inferred_invariants=[],
            likely_specs=[],
            spec_confidence={},
            risk_notes=[],
            complexity_score=0.5,
        )

        # Missing expected operation (not required, so partial penalty)
        fn_node = create_function_node(
            "fn_1",
            "withdraw",
            semantic_ops=["TRANSFERS_VALUE_OUT"],  # Missing balance ops
        )

        result = validator.validate(fn_node, intent)

        # Missing expected ops gets 0.2 penalty → 0.8 adjustment
        assert result.confidence_adjustment == 0.8
        assert result.recommendation == "accept"  # 0.8 is still >= 0.8

    def test_reject_recommendation(self, validator, view_only_intent):
        """Test 'reject' recommendation for low confidence."""
        fn_node = create_function_node(
            "fn_1",
            "getBalance",
            semantic_ops=[
                "TRANSFERS_VALUE_OUT",
                "MODIFIES_CRITICAL_STATE",
            ],  # Multiple violations
        )

        result = validator.validate(fn_node, view_only_intent)

        # Forbidden ops penalty is 0.4, so 1.0 - 0.4 = 0.6
        assert result.confidence_adjustment == 0.6
        assert result.recommendation == "review"  # 0.5 <= 0.6 < 0.8


# Success Criteria Tests


class TestSuccessCriteria:
    """Validate P1-T4 success criteria."""

    def test_validation_rules_for_all_purposes(self):
        """Validation rules should cover common business purposes."""
        common_purposes = [
            BusinessPurpose.WITHDRAWAL,
            BusinessPurpose.DEPOSIT,
            BusinessPurpose.VIEW_ONLY,
            BusinessPurpose.SET_PARAMETER,
            BusinessPurpose.SWAP,
            BusinessPurpose.LIQUIDATE,
            BusinessPurpose.TRANSFER_OWNERSHIP,
            BusinessPurpose.GRANT_ROLE,
            BusinessPurpose.CONSTRUCTOR,
        ]

        for purpose in common_purposes:
            assert purpose in INTENT_VALIDATION_RULES

    def test_catches_obvious_hallucinations(self, validator):
        """Should catch obvious hallucinations."""
        # View-only with value transfer = hallucination
        view_intent = FunctionIntent(
            business_purpose=BusinessPurpose.VIEW_ONLY,
            purpose_confidence=0.9,
            purpose_reasoning="View",
            expected_trust_level=TrustLevel.PERMISSIONLESS,
            authorized_callers=["anyone"],
            trust_assumptions=[],
            inferred_invariants=[],
            likely_specs=[],
            spec_confidence={},
            risk_notes=[],
            complexity_score=0.2,
        )

        fn_node = create_function_node(
            "fn_1",
            "getBalance",
            semantic_ops=["TRANSFERS_VALUE_OUT"],
        )

        result = validator.validate(fn_node, view_intent)

        assert not result.is_valid
        assert len(result.issues) > 0

    def test_provides_confidence_adjustment(self, validator, withdrawal_intent):
        """Should provide confidence adjustment."""
        fn_node = create_function_node(
            "fn_1",
            "withdraw",
            semantic_ops=["TRANSFERS_VALUE_OUT"],
        )

        result = validator.validate(fn_node, withdrawal_intent)

        assert isinstance(result.confidence_adjustment, float)
        assert 0.0 <= result.confidence_adjustment <= 1.0

    def test_flags_for_manual_review(self, validator):
        """Should flag low-confidence for manual review."""
        intent = FunctionIntent(
            business_purpose=BusinessPurpose.VIEW_ONLY,
            purpose_confidence=0.9,
            purpose_reasoning="View",
            expected_trust_level=TrustLevel.PERMISSIONLESS,
            authorized_callers=["anyone"],
            trust_assumptions=[],
            inferred_invariants=[],
            likely_specs=[],
            spec_confidence={},
            risk_notes=[],
            complexity_score=0.2,
        )

        fn_node = create_function_node(
            "fn_1",
            "getBalance",
            semantic_ops=["TRANSFERS_VALUE_OUT"],  # Wrong
        )

        result = validator.validate(fn_node, intent)

        assert result.recommendation in ["review", "reject"]
