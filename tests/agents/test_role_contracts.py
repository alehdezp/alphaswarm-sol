"""Unit tests for role contracts in orchestration schemas.

Tests validate that role contracts enforce:
- Schema validation fails on missing fields
- Unknown handling is explicit (required even if empty)
- Evidence IDs are required and validated
- Diversity policy enforces distinct reasoning modes

These tests cover PCONTEXT-08 acceptance criteria.
"""

from __future__ import annotations

import pytest

from alphaswarm_sol.orchestration.schemas import (
    # Role contracts
    UnknownReason,
    UnknownItem,
    ScoutStatus,
    ScoutHypothesis,
    VerificationStatus,
    VerificationResult,
    ContradictionStatus,
    CounterargumentType,
    CounterargumentStrength,
    Counterargument,
    ResidualRisk,
    ContradictionReport,
    CompositionStatus,
    ComposedPattern,
    RejectedComposition,
    CompositionProposal,
    SynthesisStatus,
    ConflictType,
    ConflictResolution,
    ConfidenceBounds,
    SynthesizedCluster,
    SynthesisConflict,
    EvidenceStats,
    SynthesizedFinding,
    # Diversity policy
    DiversityPathType,
    AssignmentStrategy,
    DiversityPath,
    DiversityPolicy,
)


class TestUnknownHandling:
    """Test explicit unknown handling for role contracts."""

    def test_unknown_item_creation(self):
        """Test UnknownItem creation with valid data."""
        unknown = UnknownItem(
            field="external_call_target",
            reason=UnknownReason.MISSING_EVIDENCE
        )
        assert unknown.field == "external_call_target"
        assert unknown.reason == UnknownReason.MISSING_EVIDENCE

    def test_unknown_item_serialization(self):
        """Test UnknownItem serialization roundtrip."""
        unknown = UnknownItem(
            field="oracle_source",
            reason=UnknownReason.OUT_OF_SCOPE
        )
        data = unknown.to_dict()
        restored = UnknownItem.from_dict(data)
        assert restored.field == unknown.field
        assert restored.reason == unknown.reason

    def test_unknown_reason_from_string(self):
        """Test UnknownReason enum from string parsing."""
        assert UnknownReason.from_string("missing_evidence") == UnknownReason.MISSING_EVIDENCE
        assert UnknownReason.from_string("OUT_OF_SCOPE") == UnknownReason.OUT_OF_SCOPE
        assert UnknownReason.from_string("requires_expansion") == UnknownReason.REQUIRES_EXPANSION
        assert UnknownReason.from_string("conflicting_signals") == UnknownReason.CONFLICTING_SIGNALS


class TestScoutHypothesisRoleContract:
    """Test ScoutHypothesis role contract enforcement."""

    def test_valid_scout_hypothesis(self):
        """Test valid ScoutHypothesis creation."""
        hypothesis = ScoutHypothesis(
            pattern_id="reentrancy-classic",
            status=ScoutStatus.CANDIDATE,
            evidence_refs=["node:fn:withdraw:123"],
            unknowns=[UnknownItem(field="external_call_target", reason=UnknownReason.MISSING_EVIDENCE)],
            confidence=0.65
        )
        assert hypothesis.pattern_id == "reentrancy-classic"
        assert hypothesis.status == ScoutStatus.CANDIDATE
        assert len(hypothesis.evidence_refs) == 1
        assert len(hypothesis.unknowns) == 1

    def test_evidence_refs_required_format(self):
        """Test that evidence refs must match valid format."""
        with pytest.raises(ValueError, match="Invalid evidence ref format"):
            ScoutHypothesis(
                pattern_id="test",
                status=ScoutStatus.CANDIDATE,
                evidence_refs=["invalid-format"],  # Invalid: no prefix
                unknowns=[]
            )

    def test_evidence_refs_valid_formats(self):
        """Test all valid evidence ref formats."""
        valid_refs = [
            "node:fn:withdraw:123",
            "edge:call:456",
            "EVD-abc123",
            "fn:transfer:789"
        ]
        hypothesis = ScoutHypothesis(
            pattern_id="test",
            status=ScoutStatus.CANDIDATE,
            evidence_refs=valid_refs,
            unknowns=[]
        )
        assert hypothesis.evidence_refs == valid_refs

    def test_confidence_cap_at_070(self):
        """Test that scout confidence is capped at 0.70 for Tier B."""
        with pytest.raises(ValueError, match="Scout confidence must be <= 0.70"):
            ScoutHypothesis(
                pattern_id="test",
                status=ScoutStatus.CANDIDATE,
                evidence_refs=["node:fn:test:1"],
                unknowns=[],
                confidence=0.85  # Too high for Tier B
            )

    def test_unknowns_required_even_if_empty(self):
        """Test that unknowns field is required (explicit unknown handling)."""
        # Empty list is valid - explicit "no unknowns"
        hypothesis = ScoutHypothesis(
            pattern_id="test",
            status=ScoutStatus.NOT_MATCHED,
            evidence_refs=[],
            unknowns=[]
        )
        assert hypothesis.unknowns == []

    def test_serialization_roundtrip(self):
        """Test ScoutHypothesis serialization roundtrip."""
        hypothesis = ScoutHypothesis(
            pattern_id="weak-access-control",
            status=ScoutStatus.UNKNOWN,
            evidence_refs=["node:fn:admin:42"],
            unknowns=[UnknownItem(field="role_check", reason=UnknownReason.REQUIRES_EXPANSION)],
            confidence=0.45,
            notes="Needs deeper analysis"
        )
        data = hypothesis.to_dict()
        restored = ScoutHypothesis.from_dict(data)
        assert restored.pattern_id == hypothesis.pattern_id
        assert restored.status == hypothesis.status
        assert restored.evidence_refs == hypothesis.evidence_refs
        assert restored.confidence == hypothesis.confidence


class TestVerificationResultRoleContract:
    """Test VerificationResult role contract enforcement."""

    def test_valid_verification_result(self):
        """Test valid VerificationResult creation."""
        result = VerificationResult(
            pattern_id="reentrancy-classic",
            status=VerificationStatus.MATCHED,
            evidence_refs=["edge:call:45"],
            counter_signals=["nonReentrant"],
            unknowns=[]
        )
        assert result.pattern_id == "reentrancy-classic"
        assert result.status == VerificationStatus.MATCHED

    def test_counter_signals_tracked(self):
        """Test that counter signals are tracked."""
        result = VerificationResult(
            pattern_id="test",
            status=VerificationStatus.NOT_MATCHED,
            evidence_refs=["node:fn:test:1"],
            counter_signals=["nonReentrant", "onlyOwner", "paused"],
            unknowns=[]
        )
        assert len(result.counter_signals) == 3

    def test_evidence_refs_validation(self):
        """Test evidence ref format validation."""
        with pytest.raises(ValueError, match="Invalid evidence ref format"):
            VerificationResult(
                pattern_id="test",
                status=VerificationStatus.MATCHED,
                evidence_refs=["bad-ref"],
                counter_signals=[],
                unknowns=[]
            )


class TestContradictionReportRoleContract:
    """Test ContradictionReport role contract enforcement."""

    def test_valid_contradiction_report(self):
        """Test valid ContradictionReport creation."""
        report = ContradictionReport(
            finding_id="FND-001",
            status=ContradictionStatus.CHALLENGED,
            counterarguments=[
                Counterargument(
                    type=CounterargumentType.GUARD_PRESENT,
                    claim="Reentrancy guard on withdraw",
                    evidence_refs=["node:fn:withdraw:123"],
                    strength=CounterargumentStrength.STRONG
                )
            ],
            confidence=0.75
        )
        assert report.finding_id == "FND-001"
        assert len(report.counterarguments) == 1

    def test_finding_id_format_validation_fnd(self):
        """Test FND- prefix is valid for finding IDs."""
        report = ContradictionReport(
            finding_id="FND-test-123",
            status=ContradictionStatus.REFUTED,
            counterarguments=[]
        )
        assert report.finding_id == "FND-test-123"

    def test_finding_id_format_validation_as(self):
        """Test AS- prefix is valid for finding IDs."""
        report = ContradictionReport(
            finding_id="AS-A1B2C3D4",
            status=ContradictionStatus.REFUTED,
            counterarguments=[]
        )
        assert report.finding_id == "AS-A1B2C3D4"

    def test_finding_id_invalid_format(self):
        """Test invalid finding ID format rejected."""
        with pytest.raises(ValueError, match="Invalid finding_id format"):
            ContradictionReport(
                finding_id="INVALID-001",  # Wrong prefix
                status=ContradictionStatus.REFUTED,
                counterarguments=[]
            )

    def test_counterargument_evidence_required(self):
        """Test counterarguments require evidence refs."""
        with pytest.raises(ValueError, match="Invalid evidence ref format"):
            Counterargument(
                type=CounterargumentType.GUARD_PRESENT,
                claim="Test claim",
                evidence_refs=["invalid"],
                strength=CounterargumentStrength.MODERATE
            )

    def test_counterargument_types(self):
        """Test all counterargument types are available."""
        types = [t.value for t in CounterargumentType]
        assert "guard_present" in types
        assert "anti_signal" in types
        assert "safe_ordering" in types
        assert "economic_constraint" in types
        assert "missing_precondition" in types


class TestCompositionProposalRoleContract:
    """Test CompositionProposal role contract enforcement."""

    def test_valid_composition_proposal(self):
        """Test valid CompositionProposal creation."""
        proposal = CompositionProposal(
            composition_id="COMP-abc123",
            status=CompositionStatus.PROPOSED,
            compositions=[
                ComposedPattern(
                    name="flash-loan-amplified-reentrancy",
                    operation="flash-loan + reentrancy",
                    base_patterns=["flash-loan-attack", "reentrancy-classic"],
                    evidence_refs=["node:fn:loan:1", "edge:call:2"]
                )
            ]
        )
        assert proposal.composition_id == "COMP-abc123"
        assert len(proposal.compositions) == 1

    def test_composition_id_format(self):
        """Test composition ID format validation."""
        with pytest.raises(ValueError, match="Invalid composition_id format"):
            CompositionProposal(
                composition_id="BAD-123",  # Wrong prefix
                status=CompositionStatus.PROPOSED,
                compositions=[]
            )

    def test_composed_pattern_confidence_cap(self):
        """Test composed patterns capped at 0.70 confidence."""
        with pytest.raises(ValueError, match="Composition confidence must be <= 0.70"):
            ComposedPattern(
                name="test",
                operation="A + B",
                base_patterns=["A", "B"],
                evidence_refs=["node:fn:test:1"],
                confidence=0.85  # Too high
            )

    def test_composed_pattern_tier_always_b(self):
        """Test composed patterns are always Tier B."""
        pattern = ComposedPattern(
            name="test",
            operation="A + B",
            base_patterns=["A", "B"],
            evidence_refs=["node:fn:test:1"]
        )
        data = pattern.to_dict()
        assert data["tier"] == "B"


class TestSynthesizedFindingRoleContract:
    """Test SynthesizedFinding role contract enforcement."""

    def test_valid_synthesized_finding(self):
        """Test valid SynthesizedFinding creation."""
        finding = SynthesizedFinding(
            synthesis_id="SYN-abc123",
            status=SynthesisStatus.SYNTHESIZED,
            synthesized_findings=[
                SynthesizedCluster(
                    cluster_id="CLU-001",
                    name="State manipulation via reentrancy",
                    severity="critical",
                    constituent_findings=["FND-001", "FND-003"],
                    confidence_bounds=ConfidenceBounds(
                        lower=0.72,
                        upper=0.88,
                        method="min-max with convergence boost"
                    )
                )
            ]
        )
        assert finding.synthesis_id == "SYN-abc123"
        assert len(finding.synthesized_findings) == 1

    def test_synthesis_id_format(self):
        """Test synthesis ID format validation."""
        with pytest.raises(ValueError, match="Invalid synthesis_id format"):
            SynthesizedFinding(
                synthesis_id="BAD-123",
                status=SynthesisStatus.SYNTHESIZED,
                synthesized_findings=[]
            )

    def test_cluster_id_format(self):
        """Test cluster ID format validation."""
        with pytest.raises(ValueError, match="Invalid cluster_id format"):
            SynthesizedCluster(
                cluster_id="BAD-123",
                name="test",
                severity="medium",
                constituent_findings=[],
                confidence_bounds=ConfidenceBounds(lower=0.5, upper=0.7, method="test")
            )

    def test_confidence_bounds_validation(self):
        """Test confidence bounds validation."""
        with pytest.raises(ValueError, match="Lower bound must be 0-1"):
            ConfidenceBounds(lower=-0.1, upper=0.5, method="test")

        with pytest.raises(ValueError, match="Upper bound must be 0-1"):
            ConfidenceBounds(lower=0.5, upper=1.5, method="test")

        with pytest.raises(ValueError, match="Lower bound .* cannot exceed upper"):
            ConfidenceBounds(lower=0.8, upper=0.5, method="test")

    @pytest.mark.xfail(reason="Stale code: SynthesizedFinding role contract changed")
    def test_conflict_types_available(self):
        """Test all conflict types are available."""
        types = [t.value for t in ConflictType]
        assert "contradictory_evidence" in types
        assert "confidence_disagreement" in types
        assert "scope_overlap" in types
        assert "temporal_conflict" in types

    def test_conflict_resolution_strategies(self):
        """Test all conflict resolution strategies are available."""
        strategies = [s.value for s in ConflictResolution]
        assert "human_review_required" in strategies
        assert "use_confidence_bounds" in strategies
        assert "merge_with_union" in strategies
        assert "verify_with_ordering_proof" in strategies


class TestDiversityPolicy:
    """Test diversity policy enforcement for distinct reasoning modes."""

    def test_default_diversity_policy(self):
        """Test default diversity policy creation."""
        policy = DiversityPolicy.default()
        assert policy.policy_id == "default-diversity-v1"
        assert len(policy.paths) == 3
        assert policy.min_distinct_paths == 2

    def test_diversity_requires_three_paths(self):
        """Test diversity policy requires at least 3 paths."""
        with pytest.raises(ValueError, match="requires at least 3 paths"):
            DiversityPolicy(
                policy_id="test",
                paths=[
                    DiversityPath(
                        path_type=DiversityPathType.OPERATION_FIRST,
                        focus="test"
                    )
                ]  # Only 1 path
            )

    def test_diversity_requires_all_path_types(self):
        """Test diversity policy requires all three path types."""
        with pytest.raises(ValueError, match="missing required path types"):
            DiversityPolicy(
                policy_id="test",
                paths=[
                    DiversityPath(path_type=DiversityPathType.OPERATION_FIRST, focus="test"),
                    DiversityPath(path_type=DiversityPathType.OPERATION_FIRST, focus="test2"),
                    DiversityPath(path_type=DiversityPathType.GUARD_FIRST, focus="test3"),
                    # Missing INVARIANT_FIRST
                ]
            )

    def test_diversity_path_types_coverage(self):
        """Test all three reasoning modes are enforced."""
        policy = DiversityPolicy.default()
        path_types = {p.path_type for p in policy.paths}
        assert DiversityPathType.OPERATION_FIRST in path_types
        assert DiversityPathType.GUARD_FIRST in path_types
        assert DiversityPathType.INVARIANT_FIRST in path_types

    def test_min_distinct_paths_range(self):
        """Test min_distinct_paths must be 2-3."""
        with pytest.raises(ValueError, match="min_distinct_paths must be 2-3"):
            DiversityPolicy(
                policy_id="test",
                paths=[
                    DiversityPath(path_type=DiversityPathType.OPERATION_FIRST, focus="test"),
                    DiversityPath(path_type=DiversityPathType.GUARD_FIRST, focus="test2"),
                    DiversityPath(path_type=DiversityPathType.INVARIANT_FIRST, focus="test3"),
                ],
                min_distinct_paths=4  # Too high
            )

    def test_path_assignment_round_robin(self):
        """Test round robin path assignment."""
        policy = DiversityPolicy.default()
        policy.assignment_strategy = AssignmentStrategy.ROUND_ROBIN

        path_0 = policy.assign_path(0)
        path_1 = policy.assign_path(1)
        path_2 = policy.assign_path(2)
        path_3 = policy.assign_path(3)  # Should wrap around

        assert path_3.path_type == path_0.path_type

    def test_validate_assignments_meets_diversity(self):
        """Test assignment validation for diversity requirements."""
        policy = DiversityPolicy.default()

        # Valid: two distinct paths
        valid_assignments = [
            DiversityPath(path_type=DiversityPathType.OPERATION_FIRST, focus="test"),
            DiversityPath(path_type=DiversityPathType.GUARD_FIRST, focus="test2"),
        ]
        assert policy.validate_assignments(valid_assignments)

        # Invalid: only one distinct path type
        invalid_assignments = [
            DiversityPath(path_type=DiversityPathType.OPERATION_FIRST, focus="test"),
            DiversityPath(path_type=DiversityPathType.OPERATION_FIRST, focus="test2"),
        ]
        assert not policy.validate_assignments(invalid_assignments)

    def test_diversity_policy_serialization(self):
        """Test DiversityPolicy serialization roundtrip."""
        policy = DiversityPolicy.default()
        data = policy.to_dict()
        restored = DiversityPolicy.from_dict(data)
        assert restored.policy_id == policy.policy_id
        assert len(restored.paths) == len(policy.paths)
        assert restored.min_distinct_paths == policy.min_distinct_paths


class TestEvidenceIdValidation:
    """Test evidence ID validation across all role contracts."""

    @pytest.mark.parametrize("valid_ref", [
        "node:fn:withdraw:123",
        "node:contract:Vault:1",
        "edge:call:45",
        "edge:read:balance:78",
        "EVD-abc123",
        "EVD-XYZ789def",
        "fn:transfer:1",
    ])
    def test_valid_evidence_refs(self, valid_ref):
        """Test valid evidence ref formats are accepted."""
        hypothesis = ScoutHypothesis(
            pattern_id="test",
            status=ScoutStatus.CANDIDATE,
            evidence_refs=[valid_ref],
            unknowns=[]
        )
        assert valid_ref in hypothesis.evidence_refs

    @pytest.mark.parametrize("invalid_ref", [
        "invalid",  # No prefix
        "bad:format",  # Not a valid prefix
        "123:node:fn",  # Wrong order
        "NODE:fn:test:1",  # Wrong case
        "",  # Empty
        "node:",  # Missing content after prefix
    ])
    def test_invalid_evidence_refs(self, invalid_ref):
        """Test invalid evidence ref formats are rejected."""
        with pytest.raises(ValueError, match="Invalid evidence ref format"):
            ScoutHypothesis(
                pattern_id="test",
                status=ScoutStatus.CANDIDATE,
                evidence_refs=[invalid_ref],
                unknowns=[]
            )
