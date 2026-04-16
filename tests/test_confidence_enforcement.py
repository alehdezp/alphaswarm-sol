"""Tests for confidence enforcement rules (ORCH-09, ORCH-10).

Tests cover:
- TestConfidenceEnforcement: Core validation and enforcement
- TestMissingContextBucketing: ORCH-10 uncertain bucketing
- TestDebateHumanFlag: Debate disagreement triggers human flag
- TestTestElevation: Test-based confidence elevation
- TestOrchestrationRules: Pool and verdict rules
"""

import pytest
from datetime import datetime

from alphaswarm_sol.orchestration.schemas import (
    DebateClaim,
    DebateRecord,
    EvidenceItem,
    EvidencePacket,
    Pool,
    PoolStatus,
    Scope,
    Verdict,
    VerdictConfidence,
)
from alphaswarm_sol.orchestration.confidence import (
    ConfidenceEnforcer,
    ValidationError,
    ValidationErrorType,
    ValidationResult,
    enforce_confidence,
    validate_confidence,
)
from alphaswarm_sol.orchestration.rules import (
    BatchingPolicy,
    DEFAULT_BATCHING,
    OrchestrationRules,
    RuleSeverity,
    RuleType,
    RuleViolation,
)


class TestConfidenceEnforcement:
    """Tests for core confidence enforcement."""

    def test_confirmed_without_test_downgraded(self):
        """CONFIRMED verdict without test should be downgraded to LIKELY."""
        # Create CONFIRMED verdict without test evidence
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.CONFIRMED,
            is_vulnerable=True,
            rationale="Some vulnerability",
            evidence_packet=EvidencePacket(
                finding_id="VKG-001",
                items=[
                    EvidenceItem(
                        type="code_pattern",
                        value="pattern match",
                        location="file.sol:10",
                        confidence=0.7,
                    )
                ],
            ),
        )

        enforcer = ConfidenceEnforcer()
        result = enforcer.validate(verdict)

        # Should have validation error
        assert not result.is_valid
        assert any(
            e.type == ValidationErrorType.MISSING_EVIDENCE
            for e in result.errors
        )

        # Enforcement should downgrade to LIKELY
        corrected = enforcer.enforce(verdict)
        assert corrected.confidence == VerdictConfidence.LIKELY

    def test_confirmed_with_test_passes(self):
        """CONFIRMED verdict with test evidence should pass validation."""
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.CONFIRMED,
            is_vulnerable=True,
            rationale="Exploit verified by test",
            evidence_packet=EvidencePacket(
                finding_id="VKG-001",
                items=[
                    EvidenceItem(
                        type="test_pass",
                        value="exploit test passed",
                        location="test_suite",
                        confidence=1.0,
                    )
                ],
            ),
        )

        enforcer = ConfidenceEnforcer()
        result = enforcer.validate(verdict)

        # Should pass
        assert result.is_valid
        assert len(result.errors) == 0

    def test_confirmed_with_strong_evidence_passes(self):
        """CONFIRMED with multiple high-confidence evidence items should pass."""
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.CONFIRMED,
            is_vulnerable=True,
            rationale="Strong multi-source evidence",
            evidence_packet=EvidencePacket(
                finding_id="VKG-001",
                items=[
                    EvidenceItem(
                        type="behavioral_signature",
                        value="R:bal->X:out->W:bal",
                        location="Vault.sol:142",
                        confidence=0.95,
                    ),
                    EvidenceItem(
                        type="code_pattern",
                        value="external call before state",
                        location="Vault.sol:143",
                        confidence=0.9,
                    ),
                ],
            ),
        )

        enforcer = ConfidenceEnforcer()
        result = enforcer.validate(verdict)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_likely_without_evidence_downgraded(self):
        """LIKELY verdict without evidence should be downgraded to UNCERTAIN."""
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="No evidence available",
            evidence_packet=None,
        )

        enforcer = ConfidenceEnforcer()
        result = enforcer.validate(verdict)

        # Should have validation error
        assert not result.is_valid
        assert any(
            e.type == ValidationErrorType.INSUFFICIENT_EVIDENCE
            for e in result.errors
        )

        # Enforcement should downgrade
        corrected = enforcer.enforce(verdict)
        assert corrected.confidence == VerdictConfidence.UNCERTAIN

    def test_likely_with_evidence_passes(self):
        """LIKELY verdict with evidence should pass validation."""
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="Pattern match found",
            evidence_packet=EvidencePacket(
                finding_id="VKG-001",
                items=[
                    EvidenceItem(
                        type="behavioral_signature",
                        value="pattern",
                        location="file.sol:10",
                    )
                ],
            ),
        )

        enforcer = ConfidenceEnforcer()
        result = enforcer.validate(verdict)

        assert result.is_valid

    def test_uncertain_always_passes(self):
        """UNCERTAIN verdict should always pass validation."""
        # Without evidence
        verdict1 = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.UNCERTAIN,
            is_vulnerable=True,
            rationale="Needs more analysis",
        )

        enforcer = ConfidenceEnforcer()
        result = enforcer.validate(verdict1)
        assert result.is_valid

        # With evidence
        verdict2 = Verdict(
            finding_id="VKG-002",
            confidence=VerdictConfidence.UNCERTAIN,
            is_vulnerable=True,
            rationale="Some evidence but inconclusive",
            evidence_packet=EvidencePacket(
                finding_id="VKG-002",
                items=[EvidenceItem(type="potential", value="maybe", location="file.sol:1")],
            ),
        )
        result2 = enforcer.validate(verdict2)
        assert result2.is_valid

    def test_rejected_always_passes(self):
        """REJECTED verdict should always pass validation."""
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.REJECTED,
            is_vulnerable=False,
            rationale="False positive confirmed",
        )

        enforcer = ConfidenceEnforcer()
        result = enforcer.validate(verdict)
        assert result.is_valid


class TestMissingContextBucketing:
    """Tests for ORCH-10: Missing context defaults to uncertain bucket."""

    def test_bucket_uncertain_creates_uncertain_verdict(self):
        """bucket_uncertain should create UNCERTAIN verdict."""
        enforcer = ConfidenceEnforcer()
        verdict = enforcer.bucket_uncertain(
            finding_id="VKG-001",
            reason="missing_context",
        )

        assert verdict.confidence == VerdictConfidence.UNCERTAIN
        assert verdict.is_vulnerable  # Assume vulnerable for safety
        assert verdict.human_flag
        assert "missing_context" in verdict.rationale

    def test_bucket_uncertain_with_evidence(self):
        """bucket_uncertain should preserve existing evidence."""
        evidence = EvidencePacket(
            finding_id="VKG-001",
            items=[
                EvidenceItem(
                    type="partial_match",
                    value="some pattern",
                    location="file.sol:5",
                )
            ],
        )

        enforcer = ConfidenceEnforcer()
        verdict = enforcer.bucket_uncertain(
            finding_id="VKG-001",
            reason="conflicting_evidence",
            evidence_packet=evidence,
        )

        assert verdict.confidence == VerdictConfidence.UNCERTAIN
        assert verdict.evidence_packet is not None
        assert len(verdict.evidence_packet.items) == 1

    def test_bucket_uncertain_custom_reasons(self):
        """bucket_uncertain should accept various reasons."""
        enforcer = ConfidenceEnforcer()

        reasons = [
            "missing_context",
            "conflicting_evidence",
            "incomplete_analysis",
            "timeout",
        ]

        for reason in reasons:
            verdict = enforcer.bucket_uncertain(
                finding_id=f"VKG-{reasons.index(reason)}",
                reason=reason,
            )
            assert verdict.confidence == VerdictConfidence.UNCERTAIN
            assert reason in verdict.rationale


class TestDebateHumanFlag:
    """Tests for debate disagreement triggering human flag."""

    def test_debate_disagreement_triggers_warning(self):
        """Debate with disagreement should trigger warning."""
        debate = DebateRecord(
            finding_id="VKG-001",
            attacker_claim=DebateClaim(
                role="attacker",
                claim="This is vulnerable to reentrancy",
                evidence=[],
                reasoning="External call before state update",
            ),
            defender_claim=DebateClaim(
                role="defender",
                claim="This is safe, guard present",
                evidence=[],
                reasoning="nonReentrant modifier applied",
            ),
            dissenting_opinion="Defender disagrees with final verdict",
        )
        debate.complete("Attacker's analysis prevails", "Defender notes guard may be present")

        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="Attacker evidence stronger",
            evidence_packet=EvidencePacket(
                finding_id="VKG-001",
                items=[EvidenceItem(type="sig", value="R:bal->X:out", location="f.sol:1")],
            ),
            debate=debate,
        )

        enforcer = ConfidenceEnforcer()
        result = enforcer.validate(verdict)

        # Should have warning about dissenting opinion
        assert result.has_warnings
        assert any("dissenting" in w.lower() for w in result.warnings)

    def test_debate_always_requires_human(self):
        """check_debate_requires_human should always return True."""
        enforcer = ConfidenceEnforcer()

        debate = DebateRecord(finding_id="VKG-001")
        assert enforcer.check_debate_requires_human(debate)

        # Even complete debate
        debate.complete("Summary")
        assert enforcer.check_debate_requires_human(debate)

    def test_human_flag_always_true(self):
        """human_flag must always be True after enforcement."""
        # Create verdict with human_flag somehow False (shouldn't happen but test)
        verdict_dict = {
            "finding_id": "VKG-001",
            "confidence": "uncertain",
            "is_vulnerable": True,
            "rationale": "Test",
            "human_flag": False,  # This violates rules
        }

        # The Verdict class enforces human_flag=True in __post_init__
        verdict = Verdict.from_dict(verdict_dict)
        assert verdict.human_flag  # Should be True regardless of input


class TestTestElevation:
    """Tests for test-based confidence elevation."""

    def test_elevate_on_test_pass_to_confirmed(self):
        """Test pass should elevate to CONFIRMED."""
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="Pattern match",
            evidence_packet=EvidencePacket(
                finding_id="VKG-001",
                items=[EvidenceItem(type="pattern", value="match", location="f.sol:1")],
            ),
        )

        enforcer = ConfidenceEnforcer()
        elevated = enforcer.elevate_on_test(verdict, test_passed=True)

        assert elevated.confidence == VerdictConfidence.CONFIRMED
        # Should have test evidence added
        assert elevated.evidence_packet is not None
        # Original evidence should be preserved, and test_pass may be added
        # if no test_pass evidence exists in original
        assert len(elevated.evidence_packet.items) >= 1

    def test_elevate_on_test_pass_with_custom_evidence(self):
        """Test pass with custom evidence should use that evidence."""
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="Pattern match",
        )

        test_evidence = EvidenceItem(
            type="poc_verified",
            value="Exploit POC executed successfully, drained 100 ETH",
            location="test/Exploit.t.sol:42",
            confidence=1.0,
            source="foundry",
        )

        enforcer = ConfidenceEnforcer()
        elevated = enforcer.elevate_on_test(
            verdict, test_passed=True, test_evidence=test_evidence
        )

        assert elevated.confidence == VerdictConfidence.CONFIRMED
        assert elevated.evidence_packet is not None
        assert any(i.type == "poc_verified" for i in elevated.evidence_packet.items)

    def test_elevate_on_test_fail_to_rejected(self):
        """Test failure should downgrade positive verdict to REJECTED."""
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="False positive suspected",
            evidence_packet=EvidencePacket(
                finding_id="VKG-001",
                items=[EvidenceItem(type="pattern", value="match", location="f.sol:1")],
            ),
        )

        enforcer = ConfidenceEnforcer()
        downgraded = enforcer.elevate_on_test(verdict, test_passed=False)

        assert downgraded.confidence == VerdictConfidence.REJECTED
        assert not downgraded.is_vulnerable
        assert "downgraded" in downgraded.rationale.lower()

    def test_elevate_uncertain_to_confirmed(self):
        """UNCERTAIN verdict can be elevated to CONFIRMED on test pass."""
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.UNCERTAIN,
            is_vulnerable=True,
            rationale="Needs verification",
        )

        enforcer = ConfidenceEnforcer()
        elevated = enforcer.elevate_on_test(verdict, test_passed=True)

        assert elevated.confidence == VerdictConfidence.CONFIRMED


class TestOrchestrationRules:
    """Tests for OrchestrationRules class."""

    def test_verdict_rules_human_flag(self):
        """Verdict must have human_flag=True."""
        rules = OrchestrationRules()

        # Valid verdict
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.UNCERTAIN,
            is_vulnerable=True,
            rationale="Test",
        )
        violations = rules.check_verdict_rules(verdict)
        # human_flag is always True (enforced by Verdict class)
        assert not any(v.rule_id == "V-01" for v in violations)

    def test_verdict_rules_confirmed_requires_evidence(self):
        """CONFIRMED verdict requires evidence per rules.

        Note: Verdict class already enforces this in __post_init__, so we
        test that OrchestrationRules provides an alternative validation layer.
        The Verdict class enforcement is primary; OrchestrationRules is for
        validating verdicts loaded from external sources that may be invalid.

        Since we can't create an invalid Verdict directly, we test the
        complementary scenario: LIKELY without evidence also triggers rule V-04.
        """
        rules = OrchestrationRules(require_evidence_for_likely=True)

        # Test that LIKELY without evidence triggers the rule
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="Test",
            evidence_packet=None,
        )
        violations = rules.check_verdict_rules(verdict)

        # V-04 is for LIKELY without evidence
        assert any(v.rule_id == "V-04" for v in violations)
        assert any(v.severity == RuleSeverity.ERROR for v in violations)

    def test_verdict_rules_likely_requires_evidence(self):
        """LIKELY verdict requires evidence per rules."""
        rules = OrchestrationRules(require_evidence_for_likely=True)

        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="Test",
            evidence_packet=None,
        )
        violations = rules.check_verdict_rules(verdict)

        assert any(v.rule_id == "V-04" for v in violations)

    def test_verdict_rules_positive_requires_rationale(self):
        """Positive verdict requires rationale."""
        rules = OrchestrationRules()

        # Create evidence so it's not downgraded
        evidence = EvidencePacket(
            finding_id="VKG-001",
            items=[EvidenceItem(type="test_pass", value="pass", location="test")],
        )

        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.CONFIRMED,
            is_vulnerable=True,
            rationale="",  # Empty rationale
            evidence_packet=evidence,
        )
        violations = rules.check_verdict_rules(verdict)

        assert any(v.rule_id == "V-05" for v in violations)

    def test_pool_rules_requires_scope(self):
        """Pool must have scope files."""
        rules = OrchestrationRules()

        pool = Pool(
            id="test-pool",
            scope=Scope(files=[]),  # Empty scope
        )
        violations = rules.check_pool_rules(pool)

        assert any(v.rule_id == "P-01" for v in violations)

    def test_pool_rules_execute_requires_beads(self):
        """EXECUTE phase requires beads."""
        rules = OrchestrationRules(min_beads_for_execute=1)

        pool = Pool(
            id="test-pool",
            scope=Scope(files=["file.sol"]),
            status=PoolStatus.EXECUTE,
            bead_ids=[],  # No beads
        )
        violations = rules.check_pool_rules(pool)

        assert any(v.rule_id == "P-02" for v in violations)

    def test_can_advance_phase_from_intake(self):
        """Should be able to advance from INTAKE."""
        rules = OrchestrationRules()

        pool = Pool(
            id="test-pool",
            scope=Scope(files=["file.sol"]),
            status=PoolStatus.INTAKE,
        )

        can_advance, reason = rules.can_advance_phase(pool)
        assert can_advance
        assert reason == ""

    def test_cannot_advance_from_terminal(self):
        """Should not advance from terminal status."""
        rules = OrchestrationRules()

        pool = Pool(
            id="test-pool",
            scope=Scope(files=["file.sol"]),
            status=PoolStatus.COMPLETE,
        )

        can_advance, reason = rules.can_advance_phase(pool)
        assert not can_advance
        assert "terminal" in reason.lower()

    def test_cannot_advance_from_paused(self):
        """Should not advance from PAUSED status."""
        rules = OrchestrationRules()

        pool = Pool(
            id="test-pool",
            scope=Scope(files=["file.sol"]),
            status=PoolStatus.PAUSED,
        )

        can_advance, reason = rules.can_advance_phase(pool)
        assert not can_advance
        assert "paused" in reason.lower()

    def test_cannot_advance_beads_without_beads(self):
        """Should not advance from BEADS without beads."""
        rules = OrchestrationRules(min_beads_for_execute=1)

        pool = Pool(
            id="test-pool",
            scope=Scope(files=["file.sol"]),
            status=PoolStatus.BEADS,
            bead_ids=[],
        )

        can_advance, reason = rules.can_advance_phase(pool)
        assert not can_advance
        assert "bead" in reason.lower()


class TestBatchingPolicy:
    """Tests for BatchingPolicy."""

    def test_default_batching_order(self):
        """Default batching should be attacker -> defender -> verifier."""
        policy = DEFAULT_BATCHING

        batches = policy.get_batch_order()
        assert len(batches) == 3
        assert "attacker" in batches[0]
        assert "defender" in batches[1]
        assert "verifier" in batches[2]

    def test_get_role_batch(self):
        """Should correctly identify which batch a role belongs to."""
        policy = DEFAULT_BATCHING

        assert policy.get_role_batch("attacker") == 1
        assert policy.get_role_batch("defender") == 2
        assert policy.get_role_batch("verifier") == 3
        assert policy.get_role_batch("unknown") == 0

    def test_custom_batching_policy(self):
        """Custom batching policy should work."""
        policy = BatchingPolicy(
            first_batch=["explorer", "attacker"],
            second_batch=["defender"],
            third_batch=["verifier", "arbiter"],
            max_parallel=5,
        )

        assert policy.get_role_batch("explorer") == 1
        assert policy.get_role_batch("attacker") == 1
        assert policy.get_role_batch("arbiter") == 3
        assert policy.max_parallel == 5

    def test_batching_policy_serialization(self):
        """BatchingPolicy should serialize and deserialize correctly."""
        policy = BatchingPolicy(
            first_batch=["a", "b"],
            second_batch=["c"],
            third_batch=["d"],
            parallel_within_batch=False,
            max_parallel=2,
            timeout_seconds=600,
        )

        data = policy.to_dict()
        restored = BatchingPolicy.from_dict(data)

        assert restored.first_batch == ["a", "b"]
        assert restored.second_batch == ["c"]
        assert restored.third_batch == ["d"]
        assert not restored.parallel_within_batch
        assert restored.max_parallel == 2
        assert restored.timeout_seconds == 600


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_add_error_invalidates(self):
        """Adding error should set is_valid to False."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid

        result.add_error(
            ValidationError(
                type=ValidationErrorType.MISSING_EVIDENCE,
                message="Test error",
            )
        )

        assert not result.is_valid
        assert result.error_count == 1

    def test_add_warning_preserves_validity(self):
        """Adding warning should not affect is_valid."""
        result = ValidationResult(is_valid=True)
        result.add_warning("Test warning")

        assert result.is_valid
        assert result.has_warnings

    def test_serialization(self):
        """ValidationResult should serialize correctly."""
        result = ValidationResult(is_valid=False)
        result.add_error(
            ValidationError(
                type=ValidationErrorType.MISSING_EVIDENCE,
                message="No evidence",
                field="evidence_packet",
            )
        )
        result.add_warning("Check this")

        data = result.to_dict()
        assert not data["is_valid"]
        assert len(data["errors"]) == 1
        assert len(data["warnings"]) == 1
        assert data["errors"][0]["type"] == "missing_evidence"


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_enforce_confidence_function(self):
        """enforce_confidence function should work.

        Note: Verdict class enforces CONFIRMED requires evidence in __post_init__,
        so we test with CONFIRMED + weak evidence (not test pass) which should
        be downgraded to LIKELY.
        """
        # Create CONFIRMED with weak evidence (not test_pass) - should be downgraded
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.CONFIRMED,
            is_vulnerable=True,
            rationale="Test",
            evidence_packet=EvidencePacket(
                finding_id="VKG-001",
                items=[
                    EvidenceItem(
                        type="code_pattern",  # Not test_pass, weak evidence
                        value="pattern",
                        location="f.sol:1",
                        confidence=0.5,  # Low confidence
                    )
                ],
            ),
        )

        corrected = enforce_confidence(verdict)
        # With only one weak evidence item, should be downgraded
        assert corrected.confidence == VerdictConfidence.LIKELY

    def test_validate_confidence_function(self):
        """validate_confidence function should work."""
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.UNCERTAIN,
            is_vulnerable=True,
            rationale="Test",
        )

        result = validate_confidence(verdict)
        assert result.is_valid
