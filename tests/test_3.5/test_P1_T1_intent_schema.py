"""
Tests for P1-T1: Intent Schema

Tests the data structures for capturing LLM-inferred business intent.
"""

import pytest
from datetime import datetime

from alphaswarm_sol.intent import (
    BusinessPurpose,
    TrustLevel,
    TrustAssumption,
    InferredInvariant,
    FunctionIntent,
)
from alphaswarm_sol.intent.schema import (
    get_all_business_purposes,
    get_all_trust_levels,
    categorize_business_purpose,
)


# Test Fixtures

@pytest.fixture
def sample_trust_assumption():
    """Create sample trust assumption."""
    return TrustAssumption(
        id="oracle_fresh",
        description="Oracle price is fresh (< 1 hour old)",
        category="oracle",
        critical=True,
        validation_check="block.timestamp - lastUpdate < 3600",
    )


@pytest.fixture
def sample_inferred_invariant():
    """Create sample inferred invariant."""
    return InferredInvariant(
        id="balance_decrease",
        description="Caller's balance decreases by withdrawn amount",
        scope="function",
        formal="balances[msg.sender]_post == balances[msg.sender]_pre - amount",
        related_spec="erc4626_withdraw",
    )


@pytest.fixture
def sample_function_intent():
    """Create sample function intent."""
    return FunctionIntent(
        business_purpose=BusinessPurpose.WITHDRAWAL,
        purpose_confidence=0.9,
        purpose_reasoning="Function transfers ETH to caller based on balance mapping",
        expected_trust_level=TrustLevel.DEPOSITOR_ONLY,
        authorized_callers=["depositor"],
        trust_assumptions=[
            TrustAssumption(
                id="balance_accurate",
                description="Balance mapping is accurate",
                category="state",
                critical=True,
            )
        ],
        inferred_invariants=[
            InferredInvariant(
                id="balance_decrease",
                description="Caller balance decreases by amount",
                scope="function",
            )
        ],
        likely_specs=["erc4626"],
        spec_confidence={"erc4626": 0.85},
        risk_notes=["External call before state update - potential reentrancy"],
        complexity_score=0.7,
    )


# Enum Tests

class TestBusinessPurpose:
    """Test BusinessPurpose enum."""

    def test_all_values_accessible(self):
        """All business purposes should be accessible."""
        assert BusinessPurpose.WITHDRAWAL
        assert BusinessPurpose.DEPOSIT
        assert BusinessPurpose.SWAP
        assert BusinessPurpose.VOTE
        assert BusinessPurpose.LIQUIDATE
        assert BusinessPurpose.UNKNOWN

    def test_value_movement_purposes(self):
        """Test value movement purposes."""
        value_movement = [
            BusinessPurpose.WITHDRAWAL,
            BusinessPurpose.DEPOSIT,
            BusinessPurpose.TRANSFER,
            BusinessPurpose.CLAIM_REWARDS,
            BusinessPurpose.MINT,
            BusinessPurpose.BURN,
        ]

        for purpose in value_movement:
            category = categorize_business_purpose(purpose)
            assert category == "value_movement"

    def test_trading_purposes(self):
        """Test trading purposes."""
        trading = [
            BusinessPurpose.SWAP,
            BusinessPurpose.ADD_LIQUIDITY,
            BusinessPurpose.REMOVE_LIQUIDITY,
        ]

        for purpose in trading:
            category = categorize_business_purpose(purpose)
            assert category == "trading"

    def test_governance_purposes(self):
        """Test governance purposes."""
        governance = [
            BusinessPurpose.VOTE,
            BusinessPurpose.PROPOSE,
            BusinessPurpose.EXECUTE_PROPOSAL,
            BusinessPurpose.DELEGATE,
        ]

        for purpose in governance:
            category = categorize_business_purpose(purpose)
            assert category == "governance"

    def test_get_all_purposes(self):
        """Test getting all business purposes."""
        all_purposes = get_all_business_purposes()
        assert len(all_purposes) >= 30  # Should have 30+ purposes
        assert BusinessPurpose.WITHDRAWAL in all_purposes


class TestTrustLevel:
    """Test TrustLevel enum."""

    def test_all_values_accessible(self):
        """All trust levels should be accessible."""
        assert TrustLevel.PERMISSIONLESS
        assert TrustLevel.DEPOSITOR_ONLY
        assert TrustLevel.ROLE_RESTRICTED
        assert TrustLevel.OWNER_ONLY
        assert TrustLevel.INTERNAL_ONLY

    def test_get_all_trust_levels(self):
        """Test getting all trust levels."""
        all_levels = get_all_trust_levels()
        assert len(all_levels) == 7
        assert TrustLevel.PERMISSIONLESS in all_levels


# TrustAssumption Tests

class TestTrustAssumption:
    """Test TrustAssumption dataclass."""

    def test_creation(self, sample_trust_assumption):
        """Test creating trust assumption."""
        assert sample_trust_assumption.id == "oracle_fresh"
        assert sample_trust_assumption.critical is True
        assert sample_trust_assumption.category == "oracle"

    def test_serialization(self, sample_trust_assumption):
        """Test trust assumption serialization."""
        data = sample_trust_assumption.to_dict()

        assert data["id"] == "oracle_fresh"
        assert data["critical"] is True
        assert "validation_check" in data

    def test_deserialization(self, sample_trust_assumption):
        """Test trust assumption deserialization."""
        data = sample_trust_assumption.to_dict()
        restored = TrustAssumption.from_dict(data)

        assert restored.id == sample_trust_assumption.id
        assert restored.critical == sample_trust_assumption.critical
        assert restored.validation_check == sample_trust_assumption.validation_check


# InferredInvariant Tests

class TestInferredInvariant:
    """Test InferredInvariant dataclass."""

    def test_creation(self, sample_inferred_invariant):
        """Test creating inferred invariant."""
        assert sample_inferred_invariant.id == "balance_decrease"
        assert sample_inferred_invariant.scope == "function"
        assert sample_inferred_invariant.related_spec == "erc4626_withdraw"

    def test_serialization(self, sample_inferred_invariant):
        """Test invariant serialization."""
        data = sample_inferred_invariant.to_dict()

        assert data["id"] == "balance_decrease"
        assert data["scope"] == "function"
        assert "formal" in data

    def test_deserialization(self, sample_inferred_invariant):
        """Test invariant deserialization."""
        data = sample_inferred_invariant.to_dict()
        restored = InferredInvariant.from_dict(data)

        assert restored.id == sample_inferred_invariant.id
        assert restored.scope == sample_inferred_invariant.scope
        assert restored.formal == sample_inferred_invariant.formal


# FunctionIntent Tests

class TestFunctionIntent:
    """Test FunctionIntent dataclass."""

    def test_creation(self, sample_function_intent):
        """Test creating function intent."""
        assert sample_function_intent.business_purpose == BusinessPurpose.WITHDRAWAL
        assert sample_function_intent.purpose_confidence == 0.9
        assert sample_function_intent.expected_trust_level == TrustLevel.DEPOSITOR_ONLY
        assert len(sample_function_intent.trust_assumptions) == 1
        assert len(sample_function_intent.inferred_invariants) == 1

    def test_serialization(self, sample_function_intent):
        """Test function intent serialization."""
        data = sample_function_intent.to_dict()

        # Enums converted to values
        assert data["business_purpose"] == "withdrawal"
        assert data["expected_trust_level"] == "depositor_only"

        # Nested objects preserved
        assert len(data["trust_assumptions"]) == 1
        assert len(data["inferred_invariants"]) == 1
        assert data["complexity_score"] == 0.7

    def test_deserialization(self, sample_function_intent):
        """Test function intent deserialization."""
        data = sample_function_intent.to_dict()
        restored = FunctionIntent.from_dict(data)

        # Enums restored correctly
        assert isinstance(restored.business_purpose, BusinessPurpose)
        assert isinstance(restored.expected_trust_level, TrustLevel)

        # Values preserved
        assert restored.business_purpose == sample_function_intent.business_purpose
        assert restored.purpose_confidence == sample_function_intent.purpose_confidence
        assert len(restored.trust_assumptions) == 1
        assert len(restored.inferred_invariants) == 1

    def test_round_trip_serialization(self, sample_function_intent):
        """Test complete round-trip preserves all data."""
        data = sample_function_intent.to_dict()
        restored = FunctionIntent.from_dict(data)
        data2 = restored.to_dict()

        # Should be identical
        assert data == data2

    def test_is_high_risk(self):
        """Test high-risk detection."""
        # High complexity score
        high_complexity = FunctionIntent(
            business_purpose=BusinessPurpose.LIQUIDATE,
            purpose_confidence=0.8,
            purpose_reasoning="Liquidation function",
            expected_trust_level=TrustLevel.PERMISSIONLESS,
            complexity_score=0.9,
        )
        assert high_complexity.is_high_risk()

        # Many risk notes
        many_risks = FunctionIntent(
            business_purpose=BusinessPurpose.WITHDRAWAL,
            purpose_confidence=0.8,
            purpose_reasoning="Withdrawal",
            expected_trust_level=TrustLevel.DEPOSITOR_ONLY,
            risk_notes=["Risk 1", "Risk 2", "Risk 3"],
            complexity_score=0.3,
        )
        assert many_risks.is_high_risk()

        # Critical assumption
        critical_assumption = FunctionIntent(
            business_purpose=BusinessPurpose.SWAP,
            purpose_confidence=0.8,
            purpose_reasoning="Swap function",
            expected_trust_level=TrustLevel.PERMISSIONLESS,
            trust_assumptions=[
                TrustAssumption(
                    id="oracle",
                    description="Oracle is accurate",
                    category="oracle",
                    critical=True,
                )
            ],
            complexity_score=0.3,
        )
        assert critical_assumption.is_high_risk()

        # Low risk
        low_risk = FunctionIntent(
            business_purpose=BusinessPurpose.VIEW_ONLY,
            purpose_confidence=0.95,
            purpose_reasoning="View function",
            expected_trust_level=TrustLevel.PERMISSIONLESS,
            complexity_score=0.1,
        )
        assert not low_risk.is_high_risk()

    def test_has_authorization_requirements(self):
        """Test authorization requirement detection."""
        # Permissionless
        permissionless = FunctionIntent(
            business_purpose=BusinessPurpose.VIEW_ONLY,
            purpose_confidence=0.9,
            purpose_reasoning="View",
            expected_trust_level=TrustLevel.PERMISSIONLESS,
        )
        assert not permissionless.has_authorization_requirements()

        # Restricted
        restricted = FunctionIntent(
            business_purpose=BusinessPurpose.WITHDRAWAL,
            purpose_confidence=0.9,
            purpose_reasoning="Withdrawal",
            expected_trust_level=TrustLevel.DEPOSITOR_ONLY,
        )
        assert restricted.has_authorization_requirements()

    def test_get_critical_assumptions(self, sample_function_intent):
        """Test getting critical assumptions."""
        critical = sample_function_intent.get_critical_assumptions()
        assert len(critical) == 1
        assert critical[0].id == "balance_accurate"

    def test_string_representation(self, sample_function_intent):
        """Test string representation."""
        s = str(sample_function_intent)
        assert "withdrawal" in s
        assert "depositor_only" in s
        assert "0.90" in s


# Integration Tests

class TestIntentIntegration:
    """Test intent schema integration scenarios."""

    def test_withdrawal_intent_complete(self):
        """Test complete withdrawal intent."""
        intent = FunctionIntent(
            business_purpose=BusinessPurpose.WITHDRAWAL,
            purpose_confidence=0.92,
            purpose_reasoning="Function named 'withdraw', transfers ETH to msg.sender based on balance",
            expected_trust_level=TrustLevel.DEPOSITOR_ONLY,
            authorized_callers=["depositor", "balance_holder"],
            trust_assumptions=[
                TrustAssumption(
                    id="balance_accurate",
                    description="Balance mapping accurately reflects deposited amounts",
                    category="state",
                    critical=True,
                ),
                TrustAssumption(
                    id="no_reentrancy",
                    description="External call won't reenter",
                    category="external_contract",
                    critical=True,
                    validation_check="has_reentrancy_guard",
                ),
            ],
            inferred_invariants=[
                InferredInvariant(
                    id="balance_decrease",
                    description="Caller's balance decreases by withdrawn amount",
                    scope="function",
                    formal="balances[msg.sender]_post == balances[msg.sender]_pre - amount",
                    related_spec="erc4626_withdraw",
                ),
                InferredInvariant(
                    id="eth_transferred",
                    description="ETH transferred equals withdrawn amount",
                    scope="function",
                    formal="msg.sender.balance_post == msg.sender.balance_pre + amount",
                ),
            ],
            likely_specs=["erc4626_withdraw", "erc20_transfer"],
            spec_confidence={"erc4626_withdraw": 0.85, "erc20_transfer": 0.60},
            risk_notes=[
                "External call before state update - reentrancy risk",
                "No access control check visible",
            ],
            complexity_score=0.65,
            inferred_at=datetime.now().isoformat(),
        )

        # Validate structure
        assert intent.business_purpose == BusinessPurpose.WITHDRAWAL
        assert len(intent.trust_assumptions) == 2
        assert len(intent.inferred_invariants) == 2
        assert intent.is_high_risk()
        assert intent.has_authorization_requirements()

        # Critical assumptions
        critical = intent.get_critical_assumptions()
        assert len(critical) == 2

        # Serialization works
        data = intent.to_dict()
        restored = FunctionIntent.from_dict(data)
        assert restored.business_purpose == intent.business_purpose

    def test_admin_function_intent(self):
        """Test admin function intent."""
        intent = FunctionIntent(
            business_purpose=BusinessPurpose.SET_PARAMETER,
            purpose_confidence=0.88,
            purpose_reasoning="Function sets protocol fee parameter",
            expected_trust_level=TrustLevel.OWNER_ONLY,
            authorized_callers=["owner"],
            trust_assumptions=[
                TrustAssumption(
                    id="caller_is_owner",
                    description="Only owner can modify parameters",
                    category="caller",
                    critical=True,
                    validation_check="msg.sender == owner",
                )
            ],
            inferred_invariants=[
                InferredInvariant(
                    id="param_in_range",
                    description="Parameter value is within safe range",
                    scope="function",
                    formal="newFee >= MIN_FEE && newFee <= MAX_FEE",
                )
            ],
            likely_specs=["ownable_pattern"],
            spec_confidence={"ownable_pattern": 0.90},
            risk_notes=["Critical parameter - needs access control"],
            complexity_score=0.45,
        )

        assert intent.business_purpose == BusinessPurpose.SET_PARAMETER
        assert intent.expected_trust_level == TrustLevel.OWNER_ONLY
        assert intent.has_authorization_requirements()


# Success Criteria Tests

class TestSuccessCriteria:
    """Validate P1-T1 success criteria."""

    def test_all_dataclasses_defined(self):
        """All required dataclasses should be defined."""
        # Can import all classes
        from alphaswarm_sol.intent import (
            BusinessPurpose,
            TrustLevel,
            TrustAssumption,
            InferredInvariant,
            FunctionIntent,
        )

        assert BusinessPurpose is not None
        assert TrustLevel is not None
        assert TrustAssumption is not None
        assert InferredInvariant is not None
        assert FunctionIntent is not None

    def test_business_purpose_coverage(self):
        """Business purpose taxonomy should cover 90%+ of DeFi."""
        purposes = get_all_business_purposes()

        # Should have comprehensive coverage
        assert len(purposes) >= 30

        # Key categories covered
        categories = set(categorize_business_purpose(p) for p in purposes)
        assert "value_movement" in categories
        assert "trading" in categories
        assert "governance" in categories
        assert "administration" in categories
        assert "lending_borrowing" in categories

    def test_trust_level_completeness(self):
        """Trust level taxonomy should be complete."""
        levels = get_all_trust_levels()

        # Should cover all access patterns
        assert TrustLevel.PERMISSIONLESS in levels
        assert TrustLevel.OWNER_ONLY in levels
        assert TrustLevel.ROLE_RESTRICTED in levels
        assert TrustLevel.INTERNAL_ONLY in levels

    def test_serialization_support(self):
        """All structures should support serialization."""
        # Trust assumption
        ta = TrustAssumption(
            id="test", description="Test", category="test", critical=False
        )
        assert ta.to_dict() is not None
        assert TrustAssumption.from_dict(ta.to_dict()) is not None

        # Inferred invariant
        inv = InferredInvariant(id="test", description="Test", scope="function")
        assert inv.to_dict() is not None
        assert InferredInvariant.from_dict(inv.to_dict()) is not None

        # Function intent
        intent = FunctionIntent(
            business_purpose=BusinessPurpose.UNKNOWN,
            purpose_confidence=0.5,
            purpose_reasoning="Test",
            expected_trust_level=TrustLevel.PERMISSIONLESS,
        )
        assert intent.to_dict() is not None
        assert FunctionIntent.from_dict(intent.to_dict()) is not None
