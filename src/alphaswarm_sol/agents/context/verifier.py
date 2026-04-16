"""Context verifier for quality validation.

This module provides the ContextVerifier class that validates merged
context bundles for completeness and quality before bead creation.

Per 05.5-CONTEXT.md:
- IF FAIL: Report errors, back to merge
- IF PASS: Proceed to bead creation
- Max 3 retries on quality issues
- Abort immediately on schema errors
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from alphaswarm_sol.agents.context.types import ContextBundle, RiskProfile
from alphaswarm_sol.vulndocs.types import VALID_SEMANTIC_OPERATIONS


@dataclass
class VerificationError:
    """Specific verification error.

    Attributes:
        field: Which field failed validation
        error_type: Type of error (missing, invalid, too_short, malformed)
        message: Human-readable error message
        severity: Severity level (error = blocking, warning = quality)
    """

    field: str
    error_type: str
    message: str
    severity: str


@dataclass
class VerificationResult:
    """Result of context verification.

    Attributes:
        valid: Whether all errors resolved (may have warnings)
        errors: List of blocking errors
        warnings: List of quality warnings
        quality_score: Quality metric from 0.0 to 1.0
        feedback_for_retry: Formatted feedback for agent retry (None if valid)
    """

    valid: bool
    errors: List[VerificationError]
    warnings: List[VerificationError]
    quality_score: float
    feedback_for_retry: Optional[str]


class ContextVerifier:
    """Verifies context bundle completeness and quality.

    Per 05.5-CONTEXT.md:
    - IF FAIL: Report errors, back to merge
    - IF PASS: Proceed to bead creation
    - Max 3 retries on quality issues
    - Abort immediately on schema errors

    The verifier checks required fields, validates content quality,
    and generates actionable feedback for retry loops.

    Class Attributes:
        REQUIRED_FIELDS: List of required bundle fields
        MIN_REASONING_TEMPLATE_LENGTH: Minimum chars for reasoning template
        MIN_SEMANTIC_TRIGGERS: Minimum number of semantic triggers
    """

    REQUIRED_FIELDS = [
        "vulnerability_class",
        "reasoning_template",
        "semantic_triggers",
        "risk_profile",
        "target_scope",
    ]

    MIN_REASONING_TEMPLATE_LENGTH = 100
    MIN_SEMANTIC_TRIGGERS = 1

    def verify(self, bundle: ContextBundle) -> VerificationResult:
        """Verify context bundle completeness and quality.

        Args:
            bundle: Context bundle to verify

        Returns:
            VerificationResult with validation status and feedback
        """
        errors: List[VerificationError] = []
        warnings: List[VerificationError] = []

        # 1. Check required fields
        for field in self.REQUIRED_FIELDS:
            value = getattr(bundle, field, None)
            if value is None or (isinstance(value, (str, list)) and len(value) == 0):
                errors.append(
                    VerificationError(
                        field=field,
                        error_type="missing",
                        message=f"Required field '{field}' is missing or empty",
                        severity="error",
                    )
                )

        # 2. Check reasoning template quality
        if bundle.reasoning_template:
            if len(bundle.reasoning_template) < self.MIN_REASONING_TEMPLATE_LENGTH:
                errors.append(
                    VerificationError(
                        field="reasoning_template",
                        error_type="too_short",
                        message=f"Reasoning template must be at least {self.MIN_REASONING_TEMPLATE_LENGTH} chars",
                        severity="error",
                    )
                )
            if not self._has_step_structure(bundle.reasoning_template):
                warnings.append(
                    VerificationError(
                        field="reasoning_template",
                        error_type="malformed",
                        message="Reasoning template should have numbered steps (1., 2., etc.)",
                        severity="warning",
                    )
                )

        # 3. Check semantic triggers
        if bundle.semantic_triggers:
            if len(bundle.semantic_triggers) < self.MIN_SEMANTIC_TRIGGERS:
                errors.append(
                    VerificationError(
                        field="semantic_triggers",
                        error_type="too_short",
                        message=f"At least {self.MIN_SEMANTIC_TRIGGERS} semantic trigger required",
                        severity="error",
                    )
                )
            invalid_triggers = self._check_valid_operations(bundle.semantic_triggers)
            for trigger in invalid_triggers:
                warnings.append(
                    VerificationError(
                        field="semantic_triggers",
                        error_type="invalid",
                        message=f"Unknown semantic operation: {trigger}",
                        severity="warning",
                    )
                )

        # 4. Check risk profile completeness
        if bundle.risk_profile:
            unknown_count = self._count_unknown_risks(bundle.risk_profile)
            if unknown_count > 4:  # More than half unknown
                warnings.append(
                    VerificationError(
                        field="risk_profile",
                        error_type="incomplete",
                        message=f"{unknown_count}/8 risk categories are unknown",
                        severity="warning",
                    )
                )

        # Calculate quality score
        quality_score = self._calculate_quality_score(bundle, errors, warnings)

        # Build retry feedback if needed
        feedback = None
        if errors:
            feedback = self._format_retry_feedback(errors, warnings)

        return VerificationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            quality_score=quality_score,
            feedback_for_retry=feedback,
        )

    def _has_step_structure(self, template: str) -> bool:
        """Check if template has numbered steps.

        Args:
            template: Reasoning template to check

        Returns:
            True if template contains numbered steps
        """
        return bool(re.search(r"\d+\.", template))

    def _check_valid_operations(self, triggers: List[str]) -> List[str]:
        """Return list of invalid operations.

        Args:
            triggers: List of semantic operation names

        Returns:
            List of invalid operation names
        """
        return [t for t in triggers if t not in VALID_SEMANTIC_OPERATIONS]

    def _count_unknown_risks(self, profile: RiskProfile) -> int:
        """Count risk categories with unknown confidence.

        Args:
            profile: Risk profile to check

        Returns:
            Count of unknown risk categories
        """
        count = 0
        for field in [
            "oracle_risks",
            "liquidity_risks",
            "access_risks",
            "upgrade_risks",
            "integration_risks",
            "timing_risks",
            "economic_risks",
            "governance_risks",
        ]:
            if getattr(profile, field).confidence == "unknown":
                count += 1
        return count

    def _calculate_quality_score(
        self,
        bundle: ContextBundle,
        errors: List[VerificationError],
        warnings: List[VerificationError],
    ) -> float:
        """Calculate quality score 0.0-1.0.

        Args:
            bundle: Context bundle being scored
            errors: List of validation errors
            warnings: List of validation warnings

        Returns:
            Quality score from 0.0 to 1.0
        """
        score = 1.0
        score -= len(errors) * 0.25  # Each error = -0.25
        score -= len(warnings) * 0.05  # Each warning = -0.05
        return max(0.0, min(1.0, score))

    def _format_retry_feedback(
        self,
        errors: List[VerificationError],
        warnings: List[VerificationError],
    ) -> str:
        """Format feedback for context-merge agent retry.

        Args:
            errors: List of validation errors
            warnings: List of validation warnings

        Returns:
            Formatted feedback string
        """
        lines = ["Context verification failed. Please fix the following issues:\n"]
        lines.append("ERRORS (must fix):")
        for err in errors:
            lines.append(f"  - [{err.field}] {err.message}")

        if warnings:
            lines.append("\nWARNINGS (should fix):")
            for warn in warnings:
                lines.append(f"  - [{warn.field}] {warn.message}")

        return "\n".join(lines)
