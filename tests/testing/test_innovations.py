"""Tests for Phase 7.2 Innovation outputs.

Validates the innovation implementations from Phase 7.2 CONTEXT:
- I4: Evidence Debt Ledger (>25% weak evidence blocks promotion)
- I5: Protocol Context TTL + Decay (30-day TTL, decay to unknown)
- I6: Exploit Plausibility Scoring (priority only, never hides findings)

These tests ensure the innovation thresholds are enforced correctly
and the quality tracking system works as specified.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import yaml

from alphaswarm_sol.testing.quality import (
    EvidenceStrength,
    EvidenceDebtEntry,
    PatternEvidenceDebt,
    EvidenceDebtTracker,
    PlausibilityFactors,
    PlausibilityScore,
    PlausibilityScorer,
    ContextTTLEntry,
    ContextTTLManager,
)


# =============================================================================
# I4: Evidence Debt Ledger Tests
# =============================================================================


class TestEvidenceDebtThreshold:
    """Test that >25% weak evidence blocks pattern promotion (I4).

    Per Phase 7.2 CONTEXT:
    - Each finding must link to evidence IDs
    - If >25% of a pattern's findings lack high-confidence evidence IDs -> debt
    - Evidence debt gets logged and blocks promotion to "ready/excellent"
    """

    def test_debt_threshold_constant_is_25_percent(self) -> None:
        """Verify the debt threshold is set to 25% as specified."""
        assert EvidenceDebtTracker.DEBT_THRESHOLD == 0.25

    def test_pattern_under_threshold_not_blocked(self) -> None:
        """Pattern with <25% weak evidence should not be blocked."""
        debt = PatternEvidenceDebt(
            pattern_id="test-pattern",
            total_findings=10,
            strong_evidence_count=6,
            medium_evidence_count=2,
            weak_evidence_count=2,  # 20% weak
            unknown_evidence_count=0,
        )
        assert debt.weak_evidence_ratio == 0.2
        assert not debt.promotion_blocked
        # 20% is between 10% (low) and 25% (moderate threshold)
        assert debt.debt_level == "moderate"

    def test_pattern_at_threshold_not_blocked(self) -> None:
        """Pattern with exactly 25% weak evidence should not be blocked."""
        debt = PatternEvidenceDebt(
            pattern_id="test-pattern",
            total_findings=20,
            strong_evidence_count=10,
            medium_evidence_count=5,
            weak_evidence_count=5,  # 25% weak
            unknown_evidence_count=0,
        )
        assert debt.weak_evidence_ratio == 0.25
        assert not debt.promotion_blocked  # >25% required to block
        assert debt.debt_level == "moderate"

    def test_pattern_over_threshold_blocked(self) -> None:
        """Pattern with >25% weak evidence should be blocked from promotion."""
        debt = PatternEvidenceDebt(
            pattern_id="test-pattern",
            total_findings=10,
            strong_evidence_count=5,
            medium_evidence_count=2,
            weak_evidence_count=2,
            unknown_evidence_count=1,  # 30% weak+unknown
        )
        assert debt.weak_evidence_ratio == 0.3
        assert debt.promotion_blocked
        assert debt.debt_level == "high"

    def test_unknown_evidence_counts_as_weak(self) -> None:
        """Unknown evidence should be counted toward weak ratio."""
        debt = PatternEvidenceDebt(
            pattern_id="test-pattern",
            total_findings=10,
            strong_evidence_count=7,
            medium_evidence_count=0,
            weak_evidence_count=0,
            unknown_evidence_count=3,  # 30% unknown = blocked
        )
        assert debt.weak_evidence_ratio == 0.3
        assert debt.promotion_blocked

    def test_empty_pattern_not_blocked(self) -> None:
        """Pattern with no findings should not be blocked (0% weak)."""
        debt = PatternEvidenceDebt(pattern_id="empty-pattern")
        assert debt.weak_evidence_ratio == 0.0
        assert not debt.promotion_blocked
        assert debt.debt_level == "none"


class TestEvidenceDebtTracker:
    """Test EvidenceDebtTracker functionality."""

    def test_classify_strong_evidence_with_audit_ref(self) -> None:
        """Evidence with audit reference should be classified as strong."""
        tracker = EvidenceDebtTracker()
        strength = tracker.classify_evidence_strength(
            evidence_refs=["https://audit.example.com/report"],
            has_audit_ref=True,
        )
        assert strength == EvidenceStrength.STRONG

    def test_classify_strong_evidence_by_keywords(self) -> None:
        """Evidence with audit/postmortem keywords should be strong."""
        tracker = EvidenceDebtTracker()

        for keyword in ["audit", "postmortem", "exploit", "poc", "cve"]:
            strength = tracker.classify_evidence_strength(
                evidence_refs=[f"https://example.com/{keyword}/finding-123"],
            )
            assert strength == EvidenceStrength.STRONG, f"Keyword '{keyword}' not recognized"

    def test_classify_medium_evidence_with_code_and_graph(self) -> None:
        """Evidence with code location and graph node should be medium."""
        tracker = EvidenceDebtTracker()
        strength = tracker.classify_evidence_strength(
            evidence_refs=[],
            has_code_location=True,
            has_graph_node_id=True,
        )
        assert strength == EvidenceStrength.MEDIUM

    def test_classify_weak_evidence_no_refs(self) -> None:
        """Evidence with nothing should be unknown/weak."""
        tracker = EvidenceDebtTracker()
        strength = tracker.classify_evidence_strength(
            evidence_refs=[],
            has_code_location=False,
            has_graph_node_id=False,
        )
        assert strength == EvidenceStrength.UNKNOWN

    def test_record_finding_updates_pattern_counts(self) -> None:
        """Recording findings should update pattern aggregate counts."""
        tracker = EvidenceDebtTracker()

        # Record strong evidence
        tracker.record_finding_evidence(
            pattern_id="reentrancy-classic",
            finding_id="f-001",
            evidence_refs=["https://audit.com/finding"],
            has_audit_ref=True,
        )

        # Record weak evidence
        tracker.record_finding_evidence(
            pattern_id="reentrancy-classic",
            finding_id="f-002",
            evidence_refs=[],
        )

        debt = tracker.get_pattern_debt("reentrancy-classic")
        assert debt is not None
        assert debt.total_findings == 2
        assert debt.strong_evidence_count == 1
        assert debt.unknown_evidence_count == 1

    def test_get_blocked_patterns(self) -> None:
        """Test retrieving list of blocked patterns."""
        tracker = EvidenceDebtTracker()

        # Create a pattern with >25% weak evidence
        for i in range(4):
            tracker.record_finding_evidence(
                pattern_id="weak-pattern",
                finding_id=f"f-{i}",
                evidence_refs=[],  # All unknown
            )

        # Create a pattern with strong evidence
        for i in range(4):
            tracker.record_finding_evidence(
                pattern_id="strong-pattern",
                finding_id=f"s-{i}",
                evidence_refs=[f"https://audit.com/{i}"],
                has_audit_ref=True,
            )

        blocked = tracker.get_blocked_patterns()
        assert "weak-pattern" in blocked
        assert "strong-pattern" not in blocked

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Test persistence to YAML."""
        storage = tmp_path / "evidence_debt.yaml"
        tracker = EvidenceDebtTracker(storage_path=storage)

        tracker.record_finding_evidence(
            pattern_id="test-pattern",
            finding_id="f-001",
            evidence_refs=["https://audit.com/finding"],
            has_audit_ref=True,
        )

        saved_path = tracker.save()
        assert saved_path == storage
        assert storage.exists()

        # Reload and verify
        tracker2 = EvidenceDebtTracker(storage_path=storage)
        debt = tracker2.get_pattern_debt("test-pattern")
        assert debt is not None
        assert debt.total_findings == 1


# =============================================================================
# I5: Protocol Context TTL + Decay Tests
# =============================================================================


class TestContextTTLDecay:
    """Test that TTL decay works as specified (I5).

    Per Phase 7.2 CONTEXT:
    - Every economic-context field gets a 30-day TTL
    - Expired fields decay to "unknown" (NEVER "safe")
    - This applies in validation/ingestion pipeline
    """

    def test_default_ttl_is_30_days(self) -> None:
        """Verify default TTL is 30 days."""
        assert ContextTTLManager.DEFAULT_TTL_DAYS == 30

    def test_ttl_entry_not_expired_within_window(self) -> None:
        """Entry should not be expired within TTL window."""
        now = datetime.utcnow()
        expires = (now + timedelta(days=15)).isoformat()

        entry = ContextTTLEntry(
            field_path="protocol.tvl",
            value="$1B",
            source_id="docs-001",
            source_date=now.isoformat(),
            last_verified=now.isoformat(),
            expires_at=expires,
            status="active",
        )
        assert not entry.is_expired
        assert entry.status == "active"

    def test_ttl_entry_expired_after_window(self) -> None:
        """Entry should be expired after TTL window passes."""
        past = datetime.utcnow() - timedelta(days=31)
        expired_at = past.isoformat()

        entry = ContextTTLEntry(
            field_path="protocol.tvl",
            value="$1B",
            source_id="docs-001",
            source_date=(past - timedelta(days=30)).isoformat(),
            last_verified=(past - timedelta(days=30)).isoformat(),
            expires_at=expired_at,
            status="active",
        )
        assert entry.is_expired

    def test_expired_decays_to_unknown_never_safe(self) -> None:
        """Expired context must decay to 'unknown', NEVER 'safe'."""
        manager = ContextTTLManager()

        # Register field with very short TTL for testing
        manager.register_context_field(
            field_path="oracle.price_source",
            value="chainlink",
            source_id="docs-001",
            ttl_days=0,  # Immediately expired
        )

        # Force expiration
        entry = manager.entries["oracle.price_source"]
        past = (datetime.utcnow() - timedelta(days=1)).isoformat()
        entry.expires_at = past

        # Run decay
        decayed = manager.check_and_decay_expired()
        assert "oracle.price_source" in decayed

        # Verify decayed to unknown, NOT safe
        updated_entry = manager.entries["oracle.price_source"]
        assert updated_entry.status == "unknown"
        assert updated_entry.status != "safe"
        assert "expired" in updated_entry.decay_reason.lower()

    def test_decay_log_recorded(self) -> None:
        """Decay events should be logged for debugging."""
        manager = ContextTTLManager()

        manager.register_context_field(
            field_path="test.field",
            value="test",
            source_id="docs",
            ttl_days=0,
        )

        entry = manager.entries["test.field"]
        entry.expires_at = (datetime.utcnow() - timedelta(days=1)).isoformat()

        manager.check_and_decay_expired()

        assert len(manager.decay_log) == 1
        log_entry = manager.decay_log[0]
        assert log_entry["field_path"] == "test.field"
        assert log_entry["new_status"] == "unknown"

    def test_refresh_extends_ttl(self) -> None:
        """Refreshing a field should extend its TTL."""
        manager = ContextTTLManager()

        manager.register_context_field(
            field_path="protocol.tvl",
            value="$1B",
            source_id="docs-001",
        )

        original_expires = manager.entries["protocol.tvl"].expires_at

        # Wait a tiny bit and refresh
        manager.refresh_field(
            field_path="protocol.tvl",
            new_value="$1.5B",
            new_source_id="docs-002",
        )

        new_expires = manager.entries["protocol.tvl"].expires_at
        assert new_expires > original_expires

    def test_save_and_load_ttl(self, tmp_path: Path) -> None:
        """Test TTL persistence to YAML."""
        storage = tmp_path / "context_ttl.yaml"
        manager = ContextTTLManager(storage_path=storage)

        manager.register_context_field(
            field_path="oracle.decimals",
            value=18,
            source_id="chainlink-docs",
        )

        manager.save()
        assert storage.exists()

        # Verify YAML content
        data = yaml.safe_load(storage.read_text())
        assert "context_ttl" in data
        assert "oracle.decimals" in data["context_ttl"]["entries"]

        # Reload
        manager2 = ContextTTLManager(storage_path=storage)
        assert "oracle.decimals" in manager2.entries
        assert manager2.entries["oracle.decimals"].value == 18


class TestTimeMachineDriftSimulation:
    """Test time-machine drift simulation for TTL decay logging.

    This simulates advancing `last_verified` dates and verifies
    that TTL decay is properly logged.
    """

    def test_advance_time_triggers_decay(self) -> None:
        """Advancing time past TTL should trigger decay."""
        manager = ContextTTLManager()

        # Register multiple fields
        for i in range(3):
            manager.register_context_field(
                field_path=f"economic.field_{i}",
                value=f"value_{i}",
                source_id=f"source_{i}",
                ttl_days=30,
            )

        # Simulate 31 days passing
        past_expiry = (datetime.utcnow() - timedelta(days=1)).isoformat()
        for entry in manager.entries.values():
            entry.expires_at = past_expiry

        # Run decay check
        decayed = manager.check_and_decay_expired()

        assert len(decayed) == 3
        assert all(manager.entries[fp].status == "unknown" for fp in decayed)

    def test_mixed_expiry_partial_decay(self) -> None:
        """Some fields expired, others not - only expired should decay."""
        manager = ContextTTLManager()

        # Fresh field
        manager.register_context_field(
            field_path="fresh.field",
            value="fresh",
            source_id="fresh-source",
            ttl_days=30,
        )

        # Stale field
        manager.register_context_field(
            field_path="stale.field",
            value="stale",
            source_id="stale-source",
            ttl_days=0,
        )
        manager.entries["stale.field"].expires_at = (
            datetime.utcnow() - timedelta(days=1)
        ).isoformat()

        decayed = manager.check_and_decay_expired()

        assert "stale.field" in decayed
        assert "fresh.field" not in decayed
        assert manager.entries["fresh.field"].status == "active"
        assert manager.entries["stale.field"].status == "unknown"


# =============================================================================
# I6: Plausibility Scoring Tests
# =============================================================================


class TestPlausibilityScoringNeverHidesFindings:
    """Test that plausibility scores are for priority only (I6).

    Per Phase 7.2 CONTEXT:
    - Score factors: liquidity depth, capital requirement, time window, access barrier
    - Score NEVER affects correctness, only ordering and review priority
    """

    def test_score_present_on_all_findings(self) -> None:
        """Every scored finding should have a plausibility score."""
        scorer = PlausibilityScorer()

        for i in range(5):
            score = scorer.compute_score(
                finding_id=f"finding-{i}",
                pattern_id="test-pattern",
            )
            assert score is not None
            assert 0 <= score.score <= 1

    def test_score_does_not_affect_finding_visibility(self) -> None:
        """Low plausibility should NOT hide the finding."""
        scorer = PlausibilityScorer()

        # Compute score with very low plausibility factors
        low_factors = PlausibilityFactors(
            liquidity_depth=0.0,
            capital_requirement=0.0,
            time_window=0.0,
            access_barrier=0.0,
            complexity=0.0,
        )

        score = scorer.compute_score(
            finding_id="low-plausibility",
            pattern_id="test",
            factors=low_factors,
        )

        # Score should be low but finding should still be retrievable
        assert score.score >= 0  # Score exists
        assert scorer.get_score("low-plausibility") is not None
        assert "low-plausibility" in scorer.scores  # Not hidden

    def test_priority_tiers_map_correctly(self) -> None:
        """Priority tiers should map score ranges correctly."""
        scorer = PlausibilityScorer()

        # P0: >= 0.8
        high_factors = PlausibilityFactors(
            liquidity_depth=1.0,
            capital_requirement=1.0,
            time_window=1.0,
            access_barrier=1.0,
            complexity=1.0,
        )
        p0_score = scorer.compute_score("p0", "test", factors=high_factors, severity="critical")
        assert p0_score.priority_tier == "P0"

        # P3: < 0.4
        low_factors = PlausibilityFactors(
            liquidity_depth=0.1,
            capital_requirement=0.1,
            time_window=0.1,
            access_barrier=0.1,
            complexity=0.1,
        )
        p3_score = scorer.compute_score("p3", "test", factors=low_factors, severity="low")
        assert p3_score.priority_tier == "P3"

    def test_all_priority_tiers_reviewed(self) -> None:
        """P3 findings should still be in the review queue."""
        scorer = PlausibilityScorer()

        for i, factors in enumerate([
            PlausibilityFactors(liquidity_depth=0.1),  # Low
            PlausibilityFactors(liquidity_depth=0.5),  # Medium
            PlausibilityFactors(liquidity_depth=0.9),  # High
        ]):
            scorer.compute_score(f"finding-{i}", "test", factors=factors)

        # All should be retrievable in prioritized order
        prioritized = scorer.get_prioritized_findings()
        assert len(prioritized) == 3

    def test_severity_boost_applied(self) -> None:
        """Severity should boost plausibility score."""
        scorer = PlausibilityScorer()

        default_factors = PlausibilityFactors()

        critical = scorer.compute_score("critical", "test", factors=default_factors, severity="critical")
        low = scorer.compute_score("low", "test", factors=default_factors, severity="low")

        assert critical.score > low.score
        assert critical.severity_boost > low.severity_boost


class TestPlausibilityScorerPersistence:
    """Test plausibility scorer save/load."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Test persistence to YAML."""
        storage = tmp_path / "plausibility.yaml"
        scorer = PlausibilityScorer(storage_path=storage)

        scorer.compute_score(
            finding_id="test-finding",
            pattern_id="test-pattern",
            severity="high",
            notes="Test note",
        )

        scorer.save()
        assert storage.exists()

        # Verify YAML content includes the "never hide" note
        data = yaml.safe_load(storage.read_text())
        assert "PRIORITIZATION ONLY" in data["plausibility_scores"]["note"]

        # Reload
        scorer2 = PlausibilityScorer(storage_path=storage)
        score = scorer2.get_score("test-finding")
        assert score is not None
        assert score.pattern_id == "test-pattern"


# =============================================================================
# Ground Truth YAML Schema Validation Tests
# =============================================================================


class TestGroundTruthYAMLSchemaValidation:
    """Test that ground truth YAML stubs validate against scenario schema."""

    def test_minimal_ground_truth_valid(self) -> None:
        """Minimal ground truth entry should be valid."""
        from alphaswarm_sol.testing.scenarios.config_schema import GroundTruth

        gt = GroundTruth(
            pattern="reentrancy-classic",
            severity="critical",
            location="withdraw:42",
        )
        assert gt.pattern == "reentrancy-classic"
        assert gt.confidence_min == 0.5  # Default

    def test_full_ground_truth_valid(self) -> None:
        """Full ground truth entry should be valid."""
        from alphaswarm_sol.testing.scenarios.config_schema import GroundTruth

        gt = GroundTruth(
            pattern="oracle-l2-sequencer-grace-missing",
            severity="high",
            location="getPrice:30",
            description="Missing grace period after sequencer check",
            confidence_min=0.7,
        )
        assert gt.pattern == "oracle-l2-sequencer-grace-missing"
        assert gt.description is not None

    def test_contract_case_with_ground_truth(self) -> None:
        """Contract case with ground truth should validate."""
        from alphaswarm_sol.testing.scenarios.config_schema import ContractCase, GroundTruth

        case = ContractCase(
            path="corpus/oracle/no-grace-period.sol",
            has_vulnerability=True,
            expected_pattern="oracle-l2-sequencer-grace-missing",
            expected_severity="high",
            ground_truth=[
                GroundTruth(
                    pattern="oracle-l2-sequencer-grace-missing",
                    severity="high",
                    location="getPrice:25",
                )
            ],
        )
        assert len(case.ground_truth) == 1

    def test_safe_contract_case_valid(self) -> None:
        """Safe contract case (no vulnerability) should validate."""
        from alphaswarm_sol.testing.scenarios.config_schema import ContractCase

        case = ContractCase(
            path="corpus/oracle/with-grace-period.sol",
            has_vulnerability=False,
            notes="Proper 1-hour grace period after sequencer restart",
        )
        assert not case.has_vulnerability
        assert case.ground_truth == []


# =============================================================================
# Integration: Evidence Debt Affects Promotion
# =============================================================================


class TestEvidenceDebtAffectsPromotion:
    """Integration test: evidence debt should block promotion."""

    def test_high_debt_blocks_pattern_promotion(self, tmp_path: Path) -> None:
        """Pattern with high evidence debt should be blocked."""
        storage = tmp_path / "evidence_debt.yaml"
        tracker = EvidenceDebtTracker(storage_path=storage)

        # Add 4 findings: 3 weak, 1 strong = 75% weak
        for i in range(3):
            tracker.record_finding_evidence(
                pattern_id="weak-pattern",
                finding_id=f"weak-{i}",
                evidence_refs=[],  # No evidence
            )

        tracker.record_finding_evidence(
            pattern_id="weak-pattern",
            finding_id="strong-1",
            evidence_refs=["https://audit.com/report"],
            has_audit_ref=True,
        )

        assert tracker.is_promotion_blocked("weak-pattern")

        summary = tracker.get_summary()
        assert "weak-pattern" in summary["blocked_patterns"]
        assert summary["overall_weak_ratio"] == 0.75
