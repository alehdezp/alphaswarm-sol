"""Confidence enforcement rules for the orchestration layer (ORCH-09, ORCH-10).

This module implements confidence enforcement to ensure verdict quality:
- ORCH-09: No likely/confirmed verdict without evidence
- ORCH-10: Missing context defaults to uncertain bucket

Rules:
1. CONFIRMED requires test pass OR multi-agent consensus with strong evidence
2. LIKELY requires evidence + agent analysis
3. UNCERTAIN is the default for missing context
4. Debate disagreement always sets human_flag=True

Per PHILOSOPHY.md, all verdicts require human review.

Usage:
    from alphaswarm_sol.orchestration.confidence import ConfidenceEnforcer, enforce_confidence

    # Validate a verdict
    enforcer = ConfidenceEnforcer()
    result = enforcer.validate(verdict)
    if not result.is_valid:
        print(f"Validation errors: {result.errors}")

    # Enforce rules (auto-correct verdict)
    corrected = enforcer.enforce(verdict)

    # Elevate on test pass
    elevated = enforcer.elevate_on_test(verdict, test_passed=True)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .schemas import (
    DebateRecord,
    EvidenceItem,
    EvidencePacket,
    Verdict,
    VerdictConfidence,
)


class ValidationErrorType(Enum):
    """Types of validation errors."""

    MISSING_EVIDENCE = "missing_evidence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    MISSING_RATIONALE = "missing_rationale"
    DEBATE_INCOMPLETE = "debate_incomplete"
    DEBATE_DISAGREEMENT = "debate_disagreement"
    CONFIDENCE_TOO_HIGH = "confidence_too_high"
    INVALID_ELEVATION = "invalid_elevation"


@dataclass
class ValidationError:
    """Single validation error with details.

    Attributes:
        type: Type of validation error
        message: Human-readable error message
        field: Field that failed validation
        current_value: Current value that caused the error
        suggested_value: Suggested correction (if applicable)
    """

    type: ValidationErrorType
    message: str
    field: str = ""
    current_value: Any = None
    suggested_value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type.value,
            "message": self.message,
            "field": self.field,
            "current_value": str(self.current_value) if self.current_value else None,
            "suggested_value": str(self.suggested_value) if self.suggested_value else None,
        }


@dataclass
class ValidationResult:
    """Result of verdict validation.

    Attributes:
        is_valid: Whether the verdict passes all rules
        errors: List of validation errors
        warnings: List of validation warnings (non-blocking)
        enforced_changes: Changes made during enforcement
        validated_at: When validation occurred
    """

    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    enforced_changes: List[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.now)

    def add_error(self, error: ValidationError) -> None:
        """Add a validation error."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a validation warning."""
        self.warnings.append(warning)

    def add_change(self, change: str) -> None:
        """Record an enforced change."""
        self.enforced_changes.append(change)

    @property
    def error_count(self) -> int:
        """Get count of errors."""
        return len(self.errors)

    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return len(self.warnings) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "enforced_changes": self.enforced_changes,
            "validated_at": self.validated_at.isoformat(),
        }


class ConfidenceEnforcer:
    """Enforces confidence rules for verdicts.

    Implements ORCH-09 and ORCH-10 from the orchestration layer:
    - ORCH-09: No likely/confirmed verdict without evidence
    - ORCH-10: Missing context defaults to uncertain bucket

    Rules:
    1. CONFIRMED requires:
       - Test passes OR
       - Multi-agent consensus with strong evidence (avg confidence >= 0.8)
    2. LIKELY requires:
       - At least one evidence item
       - Non-empty rationale
    3. UNCERTAIN is default for:
       - Missing evidence
       - Missing context
       - Conflicting evidence
    4. Debate outcomes always set human_flag=True

    Example:
        enforcer = ConfidenceEnforcer()

        # Validate without modification
        result = enforcer.validate(verdict)
        if not result.is_valid:
            for error in result.errors:
                print(f"Error: {error.message}")

        # Enforce rules (auto-correct)
        corrected = enforcer.enforce(verdict)

        # Elevate after test pass
        elevated = enforcer.elevate_on_test(verdict, test_passed=True)
    """

    # Minimum evidence items for LIKELY verdict
    MIN_EVIDENCE_FOR_LIKELY = 1

    # Minimum average confidence for CONFIRMED without test
    MIN_CONFIDENCE_FOR_CONFIRMED = 0.8

    # Minimum evidence items for CONFIRMED without test
    MIN_EVIDENCE_FOR_CONFIRMED = 2

    def __init__(
        self,
        min_evidence_for_likely: int = 1,
        min_confidence_for_confirmed: float = 0.8,
        min_evidence_for_confirmed: int = 2,
    ):
        """Initialize enforcer with configurable thresholds.

        Args:
            min_evidence_for_likely: Minimum evidence items for LIKELY
            min_confidence_for_confirmed: Minimum avg confidence for CONFIRMED
            min_evidence_for_confirmed: Minimum evidence items for CONFIRMED
        """
        self.min_evidence_for_likely = min_evidence_for_likely
        self.min_confidence_for_confirmed = min_confidence_for_confirmed
        self.min_evidence_for_confirmed = min_evidence_for_confirmed

    def validate(self, verdict: Verdict) -> ValidationResult:
        """Validate a verdict against confidence rules.

        Checks all rules without modifying the verdict.

        Args:
            verdict: Verdict to validate

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(is_valid=True)

        # Rule: human_flag must always be True
        if not verdict.human_flag:
            result.add_error(
                ValidationError(
                    type=ValidationErrorType.CONFIDENCE_TOO_HIGH,
                    message="Human flag must always be True per PHILOSOPHY.md",
                    field="human_flag",
                    current_value=verdict.human_flag,
                    suggested_value=True,
                )
            )

        # Rule: Rationale must be non-empty for positive verdicts
        if verdict.is_vulnerable and verdict.confidence.is_positive():
            if not verdict.rationale or not verdict.rationale.strip():
                result.add_error(
                    ValidationError(
                        type=ValidationErrorType.MISSING_RATIONALE,
                        message="Positive verdict requires non-empty rationale",
                        field="rationale",
                        current_value=verdict.rationale,
                    )
                )

        # Rule: CONFIRMED requires evidence
        if verdict.confidence == VerdictConfidence.CONFIRMED and verdict.is_vulnerable:
            if not self._has_sufficient_evidence_for_confirmed(verdict):
                result.add_error(
                    ValidationError(
                        type=ValidationErrorType.MISSING_EVIDENCE,
                        message="CONFIRMED verdict requires test pass or strong evidence",
                        field="confidence",
                        current_value=verdict.confidence.value,
                        suggested_value=VerdictConfidence.LIKELY.value,
                    )
                )

        # Rule: LIKELY requires at least minimal evidence
        if verdict.confidence == VerdictConfidence.LIKELY and verdict.is_vulnerable:
            if not self._has_sufficient_evidence_for_likely(verdict):
                result.add_error(
                    ValidationError(
                        type=ValidationErrorType.INSUFFICIENT_EVIDENCE,
                        message=f"LIKELY verdict requires at least {self.min_evidence_for_likely} evidence item(s)",
                        field="confidence",
                        current_value=verdict.confidence.value,
                        suggested_value=VerdictConfidence.UNCERTAIN.value,
                    )
                )

        # Rule: Debate disagreement requires human flag
        if verdict.debate:
            self._validate_debate(verdict.debate, result)

        return result

    def _has_sufficient_evidence_for_confirmed(self, verdict: Verdict) -> bool:
        """Check if verdict has sufficient evidence for CONFIRMED.

        CONFIRMED requires either:
        1. Test passes (indicated by metadata or specific evidence type)
        2. Strong evidence (multiple items with high avg confidence)
        """
        # Check for test pass evidence
        if verdict.evidence_packet:
            for item in verdict.evidence_packet.items:
                if item.type in ("test_pass", "exploit_test", "poc_verified"):
                    return True

        # Check for strong evidence
        if verdict.evidence_packet and verdict.evidence_packet.items:
            if len(verdict.evidence_packet.items) >= self.min_evidence_for_confirmed:
                if verdict.evidence_packet.average_confidence >= self.min_confidence_for_confirmed:
                    return True

        return False

    def _has_sufficient_evidence_for_likely(self, verdict: Verdict) -> bool:
        """Check if verdict has sufficient evidence for LIKELY."""
        if not verdict.evidence_packet:
            return False
        return len(verdict.evidence_packet.items) >= self.min_evidence_for_likely

    def _validate_debate(self, debate: DebateRecord, result: ValidationResult) -> None:
        """Validate debate record constraints."""
        # Check if debate is complete
        if not debate.is_complete:
            result.add_warning("Debate is not complete, verdict may change")

        # Check for disagreement (attacker and defender have opposing claims)
        if debate.attacker_claim and debate.defender_claim:
            attacker_vulnerable = "vulnerable" in debate.attacker_claim.claim.lower()
            defender_safe = "safe" in debate.defender_claim.claim.lower() or "not vulnerable" in debate.defender_claim.claim.lower()

            if attacker_vulnerable and defender_safe:
                result.add_warning("Debate has disagreement - human review required")

        # Check for dissenting opinion
        if debate.dissenting_opinion:
            result.add_warning(f"Debate has dissenting opinion: {debate.dissenting_opinion[:100]}...")

    def enforce(self, verdict: Verdict) -> Verdict:
        """Enforce confidence rules on a verdict.

        Creates a corrected copy of the verdict that passes validation.
        Does not modify the original verdict.

        Args:
            verdict: Verdict to enforce rules on

        Returns:
            Corrected Verdict that passes validation
        """
        # Start with validation to know what needs fixing
        validation = self.validate(verdict)

        if validation.is_valid:
            return verdict

        # Create a mutable copy via dict
        verdict_dict = verdict.to_dict()

        # Always ensure human_flag is True
        verdict_dict["human_flag"] = True

        # Downgrade confidence if evidence is insufficient
        current_confidence = VerdictConfidence.from_string(verdict_dict["confidence"])

        if current_confidence == VerdictConfidence.CONFIRMED and verdict.is_vulnerable:
            if not self._has_sufficient_evidence_for_confirmed(verdict):
                verdict_dict["confidence"] = VerdictConfidence.LIKELY.value

        if current_confidence == VerdictConfidence.LIKELY and verdict.is_vulnerable:
            if not self._has_sufficient_evidence_for_likely(verdict):
                verdict_dict["confidence"] = VerdictConfidence.UNCERTAIN.value

        # Create new verdict from corrected dict
        return Verdict.from_dict(verdict_dict)

    def bucket_uncertain(
        self,
        finding_id: str,
        reason: str = "missing_context",
        evidence_packet: Optional[EvidencePacket] = None,
    ) -> Verdict:
        """Create an UNCERTAIN verdict for missing context (ORCH-10).

        Use when context is insufficient to make a determination.

        Args:
            finding_id: ID of the finding
            reason: Why context is missing
            evidence_packet: Optional existing evidence

        Returns:
            UNCERTAIN verdict with human_flag=True
        """
        return Verdict(
            finding_id=finding_id,
            confidence=VerdictConfidence.UNCERTAIN,
            is_vulnerable=True,  # Uncertain = assume vulnerable for safety
            rationale=f"Bucketed as uncertain due to: {reason}",
            evidence_packet=evidence_packet,
            human_flag=True,
            created_by="confidence_enforcer",
        )

    def elevate_on_test(
        self,
        verdict: Verdict,
        test_passed: bool,
        test_evidence: Optional[EvidenceItem] = None,
    ) -> Verdict:
        """Elevate verdict confidence based on test result.

        If test passes (exploit verified), can elevate to CONFIRMED.
        If test fails, can downgrade to REJECTED.

        Args:
            verdict: Original verdict
            test_passed: Whether the exploit test passed
            test_evidence: Optional evidence item describing the test

        Returns:
            Updated verdict with new confidence level
        """
        verdict_dict = verdict.to_dict()

        if test_passed:
            # Elevate to CONFIRMED
            verdict_dict["confidence"] = VerdictConfidence.CONFIRMED.value

            # Add test evidence if provided
            if test_evidence:
                if verdict_dict.get("evidence_packet"):
                    # Parse existing evidence packet and add new item
                    evidence = EvidencePacket.from_dict(verdict_dict["evidence_packet"])
                    evidence.add_item(test_evidence)
                    verdict_dict["evidence_packet"] = evidence.to_dict()
                else:
                    # Create new evidence packet with test item
                    evidence = EvidencePacket(
                        finding_id=verdict.finding_id,
                        items=[test_evidence],
                    )
                    verdict_dict["evidence_packet"] = evidence.to_dict()
            elif not verdict_dict.get("evidence_packet"):
                # Create minimal test evidence
                evidence = EvidencePacket(
                    finding_id=verdict.finding_id,
                    items=[
                        EvidenceItem(
                            type="test_pass",
                            value="Exploit test passed",
                            location="test_suite",
                            confidence=1.0,
                            source="test_runner",
                        )
                    ],
                )
                verdict_dict["evidence_packet"] = evidence.to_dict()

        else:
            # Test failed - downgrade to REJECTED if it was positive
            if verdict.is_vulnerable and verdict.confidence.is_positive():
                verdict_dict["confidence"] = VerdictConfidence.REJECTED.value
                verdict_dict["is_vulnerable"] = False

                # Update rationale
                original_rationale = verdict_dict.get("rationale", "")
                verdict_dict["rationale"] = f"Test failed, downgraded from {verdict.confidence.value}. Original: {original_rationale}"

        return Verdict.from_dict(verdict_dict)

    def check_debate_requires_human(self, debate: DebateRecord) -> bool:
        """Check if debate outcome requires human flag.

        Per rules, debate outcomes always require human review.

        Args:
            debate: Debate record to check

        Returns:
            True (always, per design)
        """
        # Per PHILOSOPHY.md and ORCH requirements, all debate outcomes
        # require human review
        return True

    def get_required_evidence_types(
        self,
        target_confidence: VerdictConfidence,
    ) -> List[str]:
        """Get evidence types required for a confidence level.

        Args:
            target_confidence: Desired confidence level

        Returns:
            List of evidence type strings that satisfy requirements
        """
        if target_confidence == VerdictConfidence.CONFIRMED:
            return [
                "test_pass",
                "exploit_test",
                "poc_verified",
                "behavioral_signature",
                "code_pattern",
            ]
        elif target_confidence == VerdictConfidence.LIKELY:
            return [
                "behavioral_signature",
                "code_pattern",
                "guard_missing",
                "agent_analysis",
            ]
        elif target_confidence == VerdictConfidence.UNCERTAIN:
            return [
                "potential_issue",
                "needs_review",
                "incomplete_analysis",
            ]
        else:  # REJECTED
            return [
                "false_positive",
                "guard_present",
                "safe_pattern",
            ]


def enforce_confidence(verdict: Verdict) -> Verdict:
    """Convenience function to enforce confidence rules on a verdict.

    Args:
        verdict: Verdict to enforce rules on

    Returns:
        Corrected Verdict that passes validation
    """
    enforcer = ConfidenceEnforcer()
    return enforcer.enforce(verdict)


def validate_confidence(verdict: Verdict) -> ValidationResult:
    """Convenience function to validate a verdict.

    Args:
        verdict: Verdict to validate

    Returns:
        ValidationResult with errors and warnings
    """
    enforcer = ConfidenceEnforcer()
    return enforcer.validate(verdict)


# Export for module
__all__ = [
    "ValidationErrorType",
    "ValidationError",
    "ValidationResult",
    "ConfidenceEnforcer",
    "enforce_confidence",
    "validate_confidence",
]
