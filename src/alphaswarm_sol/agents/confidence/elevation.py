"""Confidence elevation via test results (SDK-14).

This module implements confidence elevation based on test results:
- Passing exploit test -> CONFIRMED confidence
- Test failure due to revert -> UNCERTAIN (possible mitigation)
- Compile failure -> Inconclusive (no elevation)

Per PHILOSOPHY.md and 05.2-CONTEXT.md:
- CONFIRMED: Verified by test (passing exploit test)
- No human review needed if test demonstrates the vulnerability
- tests_run field populated for debate protocol

Evidence chain required:
1. Bead identifies potential vulnerability
2. Test generated from bead evidence
3. Test compiles successfully
4. Test passes (demonstrates exploit)
5. -> Confidence = CONFIRMED

Usage:
    from alphaswarm_sol.agents.confidence import ConfidenceElevator, ElevationResult

    elevator = ConfidenceElevator()
    result = elevator.elevate_on_test(bead, current_confidence, test_result)

    if result.elevated:
        bead = elevator.apply_elevation(bead, result)
        print(f"Elevated to {result.new_confidence}")
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import logging

from alphaswarm_sol.agents.roles import GeneratedTest, ForgeTestResult
from alphaswarm_sol.beads.schema import VulnerabilityBead
from alphaswarm_sol.beads.types import Verdict, VerdictType
from alphaswarm_sol.orchestration.schemas import VerdictConfidence, EvidenceItem

logger = logging.getLogger(__name__)


@dataclass
class ElevationResult:
    """Result of confidence elevation attempt.

    Attributes:
        bead_id: ID of the bead being elevated
        original_confidence: Confidence level before elevation
        new_confidence: Confidence level after elevation attempt
        elevated: Whether elevation occurred
        reason: Human-readable explanation
        test_evidence: The test result used for elevation (optional)
        tests_run: List of test names that were executed
    """
    bead_id: str
    original_confidence: VerdictConfidence
    new_confidence: VerdictConfidence
    elevated: bool
    reason: str
    test_evidence: Optional[GeneratedTest] = None
    tests_run: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "bead_id": self.bead_id,
            "original_confidence": self.original_confidence.value,
            "new_confidence": self.new_confidence.value,
            "elevated": self.elevated,
            "reason": self.reason,
            "tests_run": self.tests_run,
        }


class ConfidenceElevator:
    """Elevates confidence based on test results.

    Per PHILOSOPHY.md and 05.2-CONTEXT.md:
    - CONFIRMED: Verified by test (passing exploit test)
    - No human review needed if test demonstrates the vulnerability

    Evidence chain required:
    1. Bead identifies potential vulnerability
    2. Test generated from bead evidence
    3. Test compiles successfully
    4. Test passes (demonstrates exploit)
    5. -> Confidence = CONFIRMED

    **Integration Point:**
    IntegratorAgent calls ConfidenceElevator.apply_elevation() after
    TestBuilderAgent completes test execution. The flow is:
    1. TestBuilderAgent generates and runs test -> GeneratedTest
    2. IntegratorAgent receives test result
    3. IntegratorAgent instantiates ConfidenceElevator
    4. IntegratorAgent calls elevator.elevate_on_test() to compute result
    5. IntegratorAgent calls elevator.apply_elevation() to update bead

    Example:
        # In IntegratorAgent after test execution
        elevator = ConfidenceElevator()
        result = elevator.elevate_on_test(
            bead,
            VerdictConfidence.LIKELY,
            test_result,
        )
        if result.elevated:
            updated_bead = elevator.apply_elevation(bead, result)
    """

    def elevate_on_test(
        self,
        bead: VulnerabilityBead,
        current_confidence: VerdictConfidence,
        test_result: GeneratedTest,
    ) -> ElevationResult:
        """Attempt to elevate confidence based on test result.

        Args:
            bead: The vulnerability bead
            current_confidence: Current confidence level
            test_result: Result from TestBuilderAgent

        Returns:
            ElevationResult with new confidence and reason
        """
        tests_run = [r.test_name for r in test_result.test_results]

        # Check if test demonstrates vulnerability
        if test_result.test_passed:
            # Passing exploit test = CONFIRMED
            logger.info(f"Bead {bead.id}: Elevated to CONFIRMED via passing test")
            return ElevationResult(
                bead_id=bead.id,
                original_confidence=current_confidence,
                new_confidence=VerdictConfidence.CONFIRMED,
                elevated=True,
                reason=f"Exploit test passed: {test_result.expected_outcome}",
                test_evidence=test_result,
                tests_run=tests_run,
            )

        # Test failed - check why
        if test_result.compile_result and not test_result.compile_result.success:
            # Couldn't compile - no elevation, but not disproof
            return ElevationResult(
                bead_id=bead.id,
                original_confidence=current_confidence,
                new_confidence=current_confidence,
                elevated=False,
                reason="Test failed to compile - inconclusive",
                test_evidence=test_result,
                tests_run=tests_run,
            )

        # Test compiled but failed - might indicate false positive
        failure_reasons = [
            r.failure_reason for r in test_result.test_results
            if r.failure_reason
        ]

        if any("revert" in (r or "").lower() for r in failure_reasons):
            # Reverted - potential mitigations in place
            return ElevationResult(
                bead_id=bead.id,
                original_confidence=current_confidence,
                new_confidence=VerdictConfidence.UNCERTAIN,
                elevated=False,
                reason=f"Exploit reverted - possible mitigation: {failure_reasons}",
                test_evidence=test_result,
                tests_run=tests_run,
            )

        # Other failure - inconclusive
        return ElevationResult(
            bead_id=bead.id,
            original_confidence=current_confidence,
            new_confidence=current_confidence,
            elevated=False,
            reason=f"Test failed: {failure_reasons}",
            test_evidence=test_result,
            tests_run=tests_run,
        )

    def apply_elevation(
        self,
        bead: VulnerabilityBead,
        elevation: ElevationResult,
    ) -> VulnerabilityBead:
        """Apply elevation result to bead.

        Updates bead with:
        - New verdict confidence
        - Test evidence in notes
        - tests_run for debate protocol

        **Called by IntegratorAgent** after test execution completes.

        Args:
            bead: The vulnerability bead to update
            elevation: The elevation result from elevate_on_test()

        Returns:
            Updated bead with new verdict and work_state
        """
        if elevation.elevated:
            # Update verdict to confirmed
            bead.verdict = Verdict(
                type=VerdictType.TRUE_POSITIVE,
                reason=elevation.reason,
                confidence=1.0,  # Full confidence from test
                evidence=[f"Test passed: {t}" for t in elevation.tests_run],
            )
            bead.add_note(f"Confidence elevated to CONFIRMED via test: {elevation.reason}")

            # Clear human flag - no review needed per 05.2-CONTEXT.md
            bead.human_flag = False

        else:
            bead.add_note(f"Test elevation failed: {elevation.reason}")

        # Store tests_run for debate protocol
        if bead.work_state is None:
            bead.work_state = {}
        bead.work_state["tests_run"] = elevation.tests_run

        return bead

    def validate_evidence_chain(
        self,
        bead: VulnerabilityBead,
        test_result: GeneratedTest,
    ) -> bool:
        """Validate evidence chain from bead to test.

        Required for elevation:
        1. Test was generated from this bead
        2. Test addresses the same vulnerability class
        3. Test compiled successfully
        4. Test assertions relate to bead's pattern

        Args:
            bead: The vulnerability bead
            test_result: The test result to validate

        Returns:
            True if evidence chain is valid
        """
        # Check bead ID match
        if test_result.bead_id != bead.id:
            logger.warning(f"Test bead_id mismatch: {test_result.bead_id} != {bead.id}")
            return False

        # Check compilation
        if not test_result.compile_result or not test_result.compile_result.success:
            return False

        # Check test code references vulnerability
        vuln_keywords = [
            bead.vulnerability_class.lower(),
            "exploit",
            "attack",
        ]
        test_lower = test_result.test_code.lower()
        if not any(kw in test_lower for kw in vuln_keywords):
            logger.warning("Test doesn't reference vulnerability class")
            return False

        return True


__all__ = [
    "ElevationResult",
    "ConfidenceElevator",
]
