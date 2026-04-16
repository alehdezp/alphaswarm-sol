"""
Intent Validation Module

Cross-validates LLM-inferred intents against VKG properties to detect
hallucinations and ensure intent accuracy. This is critical for trusting
intent-based vulnerability analysis.
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Optional

from alphaswarm_sol.kg.schema import Node
from alphaswarm_sol.intent.schema import FunctionIntent, BusinessPurpose, TrustLevel


@dataclass
class ValidationResult:
    """Result of intent validation against VKG properties."""

    is_valid: bool
    confidence_adjustment: float  # Multiplier for original confidence (0.0 - 1.0)
    issues: List[str]  # List of validation issues found
    recommendation: str  # "accept", "review", "reject"


# Intent Validation Rules
# Maps business purposes to expected/forbidden semantic operations
INTENT_VALIDATION_RULES: Dict[BusinessPurpose, Dict[str, any]] = {
    # Value Movement Operations
    BusinessPurpose.WITHDRAWAL: {
        "required_ops": ["TRANSFERS_VALUE_OUT"],
        "expected_ops": ["READS_USER_BALANCE", "WRITES_USER_BALANCE"],
        "forbidden_ops": [],
        "expected_trust": [TrustLevel.DEPOSITOR_ONLY, TrustLevel.PERMISSIONLESS],
    },
    BusinessPurpose.DEPOSIT: {
        "required_ops": ["RECEIVES_VALUE_IN"],
        "expected_ops": ["WRITES_USER_BALANCE"],
        "forbidden_ops": ["TRANSFERS_VALUE_OUT"],
        "expected_trust": [TrustLevel.PERMISSIONLESS, TrustLevel.DEPOSITOR_ONLY],
    },
    BusinessPurpose.TRANSFER: {
        "required_ops": ["WRITES_USER_BALANCE"],
        "expected_ops": ["READS_USER_BALANCE"],
        "forbidden_ops": [],
        "expected_trust": [TrustLevel.DEPOSITOR_ONLY, TrustLevel.PERMISSIONLESS],
    },
    BusinessPurpose.CLAIM_REWARDS: {
        "required_ops": ["TRANSFERS_VALUE_OUT"],
        "expected_ops": ["READS_USER_BALANCE", "WRITES_USER_BALANCE"],
        "forbidden_ops": [],
        "expected_trust": [TrustLevel.DEPOSITOR_ONLY, TrustLevel.PERMISSIONLESS],
    },
    # Trading Operations
    BusinessPurpose.SWAP: {
        "required_ops": [],
        "expected_ops": ["CALLS_EXTERNAL", "WRITES_USER_BALANCE"],
        "forbidden_ops": [],
        "expected_trust": [TrustLevel.PERMISSIONLESS],
    },
    BusinessPurpose.LIQUIDATE: {
        "required_ops": [],
        "expected_ops": ["CALLS_EXTERNAL", "WRITES_USER_BALANCE"],
        "forbidden_ops": [],
        "expected_trust": [TrustLevel.PERMISSIONLESS],
    },
    # Read-Only Operations
    BusinessPurpose.VIEW_ONLY: {
        "required_ops": [],
        "expected_ops": [],
        "forbidden_ops": [
            "TRANSFERS_VALUE_OUT",
            "WRITES_USER_BALANCE",
            "MODIFIES_CRITICAL_STATE",
            "MODIFIES_OWNER",
            "MODIFIES_ROLES",
        ],
        "expected_trust": [TrustLevel.PERMISSIONLESS],
    },
    # Administrative Operations
    BusinessPurpose.SET_PARAMETER: {
        "required_ops": ["MODIFIES_CRITICAL_STATE"],
        "expected_ops": [],
        "forbidden_ops": [],
        "expected_trust": [
            TrustLevel.OWNER_ONLY,
            TrustLevel.ROLE_RESTRICTED,
        ],
    },
    BusinessPurpose.TRANSFER_OWNERSHIP: {
        "required_ops": ["MODIFIES_OWNER"],
        "expected_ops": [],
        "forbidden_ops": [],
        "expected_trust": [TrustLevel.OWNER_ONLY],
    },
    BusinessPurpose.GRANT_ROLE: {
        "required_ops": ["MODIFIES_ROLES"],
        "expected_ops": [],
        "forbidden_ops": [],
        "expected_trust": [
            TrustLevel.OWNER_ONLY,
            TrustLevel.ROLE_RESTRICTED,
        ],
    },
    BusinessPurpose.REVOKE_ROLE: {
        "required_ops": ["MODIFIES_ROLES"],
        "expected_ops": [],
        "forbidden_ops": [],
        "expected_trust": [
            TrustLevel.OWNER_ONLY,
            TrustLevel.ROLE_RESTRICTED,
        ],
    },
    BusinessPurpose.PAUSE: {
        "required_ops": ["MODIFIES_CRITICAL_STATE"],
        "expected_ops": [],
        "forbidden_ops": [],
        "expected_trust": [
            TrustLevel.OWNER_ONLY,
            TrustLevel.ROLE_RESTRICTED,
        ],
    },
    BusinessPurpose.UNPAUSE: {
        "required_ops": ["MODIFIES_CRITICAL_STATE"],
        "expected_ops": [],
        "forbidden_ops": [],
        "expected_trust": [
            TrustLevel.OWNER_ONLY,
            TrustLevel.ROLE_RESTRICTED,
        ],
    },
    # Initialization (CONSTRUCTOR is the closest match in the enum)
    BusinessPurpose.CONSTRUCTOR: {
        "required_ops": ["INITIALIZES_STATE"],
        "expected_ops": ["MODIFIES_CRITICAL_STATE"],
        "forbidden_ops": [],
        "expected_trust": [TrustLevel.OWNER_ONLY],
    },
    # Oracle Operations
    BusinessPurpose.UPDATE_PRICE: {
        "required_ops": [],
        "expected_ops": ["READS_ORACLE", "MODIFIES_CRITICAL_STATE"],
        "forbidden_ops": [],
        "expected_trust": [
            TrustLevel.PERMISSIONLESS,
            TrustLevel.ROLE_RESTRICTED,
        ],
    },
    BusinessPurpose.SYNC_RESERVES: {
        "required_ops": [],
        "expected_ops": ["MODIFIES_CRITICAL_STATE"],
        "forbidden_ops": [],
        "expected_trust": [TrustLevel.PERMISSIONLESS],
    },
}


class IntentValidator:
    """
    Validates LLM-inferred intents against VKG properties.

    Detects hallucinations by cross-checking intent claims against
    actual semantic operations detected in the function.
    """

    def __init__(self):
        """Initialize validator."""
        pass

    def validate(
        self, fn_node: Node, intent: FunctionIntent
    ) -> ValidationResult:
        """
        Validate intent against function properties.

        Args:
            fn_node: Function node with VKG properties
            intent: LLM-inferred intent to validate

        Returns:
            ValidationResult with issues and confidence adjustment
        """
        issues = []
        score = 1.0

        # Get actual operations from VKG
        actual_ops = set(fn_node.properties.get("semantic_ops", []))

        # Get validation rules for this business purpose
        rules = INTENT_VALIDATION_RULES.get(intent.business_purpose)

        if rules is None:
            # No validation rules for this purpose (uncommon purposes)
            return ValidationResult(
                is_valid=True,
                confidence_adjustment=0.9,  # Slight penalty for uncommon purpose
                issues=[f"No validation rules for {intent.business_purpose.value}"],
                recommendation="review",
            )

        # Check required operations
        required = set(rules.get("required_ops", []))
        if required:
            missing = required - actual_ops
            if missing:
                issues.append(
                    f"Missing required operations for {intent.business_purpose.value}: "
                    f"{', '.join(missing)}"
                )
                score -= 0.3

        # Check forbidden operations
        forbidden = set(rules.get("forbidden_ops", []))
        if forbidden:
            present = forbidden & actual_ops
            if present:
                issues.append(
                    f"Has forbidden operations for {intent.business_purpose.value}: "
                    f"{', '.join(present)}"
                )
                score -= 0.4

        # Check expected operations (soft check - warning only)
        expected = set(rules.get("expected_ops", []))
        if expected:
            missing_expected = expected - actual_ops
            if missing_expected and len(missing_expected) == len(expected):
                # All expected operations missing - likely wrong classification
                issues.append(
                    f"Missing all expected operations for {intent.business_purpose.value}: "
                    f"{', '.join(missing_expected)}"
                )
                score -= 0.2

        # Check trust level consistency
        expected_trust = rules.get("expected_trust", [])
        if expected_trust and intent.expected_trust_level not in expected_trust:
            issues.append(
                f"Unexpected trust level '{intent.expected_trust_level.value}' "
                f"for {intent.business_purpose.value}. "
                f"Expected: {', '.join(t.value for t in expected_trust)}"
            )
            score -= 0.2

        # Ensure score is in valid range
        score = max(0.0, min(1.0, score))

        # Determine recommendation
        if score >= 0.8:
            recommendation = "accept"
        elif score >= 0.5:
            recommendation = "review"
        else:
            recommendation = "reject"

        return ValidationResult(
            is_valid=len(issues) == 0,
            confidence_adjustment=score,
            issues=issues,
            recommendation=recommendation,
        )

    def validate_batch(
        self, validations: List[tuple[Node, FunctionIntent]]
    ) -> List[ValidationResult]:
        """
        Validate multiple intents in batch.

        Args:
            validations: List of (fn_node, intent) tuples

        Returns:
            List of ValidationResults
        """
        return [self.validate(fn_node, intent) for fn_node, intent in validations]

    def compute_adjusted_confidence(
        self, intent: FunctionIntent, validation: ValidationResult
    ) -> float:
        """
        Compute adjusted confidence after validation.

        Args:
            intent: Original intent
            validation: Validation result

        Returns:
            Adjusted confidence score (0.0 - 1.0)
        """
        adjusted = intent.purpose_confidence * validation.confidence_adjustment
        return max(0.0, min(1.0, adjusted))

    def get_high_confidence_intents(
        self,
        validations: List[tuple[FunctionIntent, ValidationResult]],
        threshold: float = 0.7,
    ) -> List[FunctionIntent]:
        """
        Filter to high-confidence validated intents.

        Args:
            validations: List of (intent, validation_result) tuples
            threshold: Minimum adjusted confidence

        Returns:
            List of high-confidence intents
        """
        high_confidence = []

        for intent, validation in validations:
            adjusted_confidence = self.compute_adjusted_confidence(intent, validation)
            if adjusted_confidence >= threshold:
                high_confidence.append(intent)

        return high_confidence
