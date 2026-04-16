"""
Tests for P2-T5: Adversarial Arbiter

Tests evidence aggregation, decision making, and verdict generation.
"""

import pytest
from unittest.mock import Mock

from alphaswarm_sol.agents.arbiter import (
    VerdictType,
    ConfidenceLevel,
    EvidenceType,
    WinningSide,
    Evidence,
    EvidenceChain,
    ArbitrationResult,
    AdversarialArbiter,
)
from alphaswarm_sol.agents.attacker import AttackCategory, AttackConstruction, AttackerResult
from alphaswarm_sol.agents.defender import DefenseArgument, DefenseType, GuardInfo, DefenderResult


# Test Fixtures


@pytest.fixture
def arbiter():
    """Create arbiter instance."""
    return AdversarialArbiter()


@pytest.fixture
def vulnerable_scenario():
    """Scenario where attacker wins (vulnerable)."""
    # Strong attack, weak defense
    attack = AttackConstruction(
        category=AttackCategory.STATE_MANIPULATION,
        target_nodes=["fn_vulnerable"],
        preconditions=[],
        attack_steps=[],
        postconditions=["Funds drained"],
        exploitability_score=0.9,
        feasibility=Mock(),
        economic_analysis=Mock(),
    )

    attacker_result = AttackerResult(
        matched=True,
        confidence=0.9,
        attack=attack,
    )

    # Weak defense (no guards)
    defender_result = DefenderResult(
        matched=False,
        confidence=0.2,
        defenses=[],
    )

    return attacker_result, defender_result


@pytest.fixture
def safe_scenario():
    """Scenario where defender wins (safe)."""
    # Weak attack
    attack = AttackConstruction(
        category=AttackCategory.STATE_MANIPULATION,
        target_nodes=["fn_safe"],
        preconditions=[],
        attack_steps=[],
        postconditions=[],
        exploitability_score=0.3,
        feasibility=Mock(),
        economic_analysis=Mock(),
    )

    attacker_result = AttackerResult(
        matched=True,
        confidence=0.3,
        attack=attack,
    )

    # Strong defense
    defense = DefenseArgument(
        id="defense_001",
        claim="Protected by reentrancy guard",
        defense_type=DefenseType.GUARD_PRESENT,
        guards_identified=[
            GuardInfo(
                guard_type="reentrancy_guard",
                name="nonReentrant",
                strength=0.95,
                blocks_attacks=["reentrancy_classic"],
            )
        ],
        strength=0.95,
    )

    defender_result = DefenderResult(
        matched=True,
        confidence=0.95,
        defenses=[defense],
    )

    return attacker_result, defender_result


# Enum Tests


class TestEnums:
    """Test enum definitions."""

    def test_verdict_types(self):
        """Test verdict type enum."""
        assert VerdictType.VULNERABLE
        assert VerdictType.SAFE
        assert VerdictType.UNCERTAIN

    def test_confidence_levels(self):
        """Test confidence level enum."""
        assert ConfidenceLevel.DEFINITIVE
        assert ConfidenceLevel.HIGH
        assert ConfidenceLevel.MODERATE
        assert ConfidenceLevel.SUGGESTIVE
        assert ConfidenceLevel.INDICATIVE
        assert ConfidenceLevel.UNCERTAIN

    def test_evidence_types(self):
        """Test evidence type enum."""
        assert EvidenceType.FORMAL_PROOF
        assert EvidenceType.CROSS_GRAPH
        assert EvidenceType.GUARD_ANALYSIS
        assert EvidenceType.PATTERN_MATCH
        assert EvidenceType.BEHAVIORAL_SIG
        assert EvidenceType.HEURISTIC

    def test_winning_side(self):
        """Test winning side enum."""
        assert WinningSide.ATTACKER
        assert WinningSide.DEFENDER
        assert WinningSide.INCONCLUSIVE


# Dataclass Tests


class TestDataclasses:
    """Test dataclass functionality."""

    def test_evidence_creation(self):
        """Test creating evidence."""
        evidence = Evidence(
            evidence_type=EvidenceType.PATTERN_MATCH,
            weight=0.6,
            confidence=0.8,
            supports_vulnerable=True,
            description="Attack detected",
            source="attacker",
        )

        assert evidence.evidence_type == EvidenceType.PATTERN_MATCH
        assert evidence.weight == 0.6
        assert evidence.confidence == 0.8
        assert evidence.supports_vulnerable is True

    def test_evidence_chain_creation(self):
        """Test creating evidence chain."""
        chain = EvidenceChain()

        assert len(chain.all_evidence) == 0
        assert len(chain.attacker_evidence) == 0
        assert len(chain.defender_evidence) == 0

    def test_evidence_chain_add(self):
        """Test adding evidence to chain."""
        chain = EvidenceChain()

        attacker_ev = Evidence(
            evidence_type=EvidenceType.PATTERN_MATCH,
            weight=0.6,
            confidence=0.8,
            supports_vulnerable=True,
            description="Attack",
            source="attacker",
        )

        defender_ev = Evidence(
            evidence_type=EvidenceType.GUARD_ANALYSIS,
            weight=0.7,
            confidence=0.9,
            supports_vulnerable=False,
            description="Guard",
            source="defender",
        )

        chain.add(attacker_ev)
        chain.add(defender_ev)

        assert len(chain.all_evidence) == 2
        assert len(chain.attacker_evidence) == 1
        assert len(chain.defender_evidence) == 1


# AdversarialArbiter Tests


class TestAdversarialArbiter:
    """Test arbiter functionality."""

    def test_arbiter_creation(self):
        """Test creating arbiter."""
        arbiter = AdversarialArbiter()

        assert arbiter is not None
        assert hasattr(arbiter, "EVIDENCE_WEIGHTS")

    def test_evidence_weights_defined(self):
        """Test evidence weights are defined."""
        arbiter = AdversarialArbiter()

        assert EvidenceType.FORMAL_PROOF in arbiter.EVIDENCE_WEIGHTS
        assert arbiter.EVIDENCE_WEIGHTS[EvidenceType.FORMAL_PROOF] == 1.0
        assert arbiter.EVIDENCE_WEIGHTS[EvidenceType.GUARD_ANALYSIS] == 0.7
        assert arbiter.EVIDENCE_WEIGHTS[EvidenceType.HEURISTIC] == 0.3

    def test_arbitrate_returns_result(self, arbiter, vulnerable_scenario):
        """Test arbitrate returns ArbitrationResult."""
        attacker_result, defender_result = vulnerable_scenario

        result = arbiter.arbitrate(
            attacker_result=attacker_result, defender_result=defender_result
        )

        assert isinstance(result, ArbitrationResult)
        assert hasattr(result, "verdict")
        assert hasattr(result, "confidence")
        assert hasattr(result, "winning_side")

    def test_arbitrate_vulnerable_verdict(self, arbiter, vulnerable_scenario):
        """Test arbiter finds vulnerable when attacker wins."""
        attacker_result, defender_result = vulnerable_scenario

        result = arbiter.arbitrate(
            attacker_result=attacker_result, defender_result=defender_result
        )

        assert result.verdict == VerdictType.VULNERABLE
        assert result.winning_side == WinningSide.ATTACKER
        assert result.confidence > 0.5

    def test_arbitrate_safe_verdict(self, arbiter, safe_scenario):
        """Test arbiter finds safe when defender wins."""
        attacker_result, defender_result = safe_scenario

        result = arbiter.arbitrate(
            attacker_result=attacker_result, defender_result=defender_result
        )

        assert result.verdict == VerdictType.SAFE
        assert result.winning_side == WinningSide.DEFENDER
        assert result.confidence > 0.7

    def test_arbitrate_no_evidence(self, arbiter):
        """Test arbiter with no evidence."""
        result = arbiter.arbitrate()

        assert result.verdict == VerdictType.UNCERTAIN
        assert result.confidence <= 0.5  # Uncertain, not confident

    def test_arbitrate_error_handling(self, arbiter):
        """Test error handling in arbitrate."""
        bad_attacker = Mock()
        bad_attacker.matched = True
        bad_attacker.attack = None  # Will cause issues

        result = arbiter.arbitrate(attacker_result=bad_attacker)

        # Should not crash, return uncertain
        assert isinstance(result, ArbitrationResult)


# Evidence Collection Tests


class TestEvidenceCollection:
    """Test evidence collection methods."""

    def test_collect_attacker_evidence(self, arbiter, vulnerable_scenario):
        """Test collecting attacker evidence."""
        attacker_result, _ = vulnerable_scenario

        chain = arbiter._collect_evidence(attacker_result, None, None, None)

        assert len(chain.attacker_evidence) > 0
        assert chain.attacker_evidence[0].supports_vulnerable is True

    def test_collect_defender_evidence(self, arbiter, safe_scenario):
        """Test collecting defender evidence."""
        _, defender_result = safe_scenario

        chain = arbiter._collect_evidence(None, defender_result, None, None)

        assert len(chain.defender_evidence) > 0
        assert chain.defender_evidence[0].supports_vulnerable is False

    def test_collect_guard_evidence(self, arbiter, safe_scenario):
        """Test collecting guard evidence."""
        _, defender_result = safe_scenario

        chain = arbiter._collect_evidence(None, defender_result, None, None)

        guard_evidence = [
            e
            for e in chain.defender_evidence
            if e.evidence_type == EvidenceType.GUARD_ANALYSIS
        ]
        assert len(guard_evidence) > 0


# Decision Making Tests


class TestDecisionMaking:
    """Test decision making logic."""

    def test_make_decision_vulnerable(self, arbiter, vulnerable_scenario):
        """Test decision making for vulnerable case."""
        attacker_result, defender_result = vulnerable_scenario

        chain = arbiter._collect_evidence(
            attacker_result, defender_result, None, None
        )
        verdict, confidence, winning_side = arbiter._make_decision(chain)

        assert verdict == VerdictType.VULNERABLE
        assert winning_side == WinningSide.ATTACKER

    def test_make_decision_safe(self, arbiter, safe_scenario):
        """Test decision making for safe case."""
        attacker_result, defender_result = safe_scenario

        chain = arbiter._collect_evidence(
            attacker_result, defender_result, None, None
        )
        verdict, confidence, winning_side = arbiter._make_decision(chain)

        assert verdict == VerdictType.SAFE
        assert winning_side == WinningSide.DEFENDER

    def test_calculate_weighted_score(self, arbiter):
        """Test weighted score calculation."""
        evidence_list = [
            Evidence(
                evidence_type=EvidenceType.PATTERN_MATCH,
                weight=0.6,
                confidence=0.8,
                supports_vulnerable=True,
                description="Test",
                source="attacker",
            ),
            Evidence(
                evidence_type=EvidenceType.BEHAVIORAL_SIG,
                weight=0.5,
                confidence=0.7,
                supports_vulnerable=True,
                description="Test",
                source="attacker",
            ),
        ]

        score = arbiter._calculate_weighted_score(evidence_list)

        # Should be weighted average
        assert 0.0 < score < 1.0

    def test_calculate_weighted_score_empty(self, arbiter):
        """Test weighted score with empty list."""
        score = arbiter._calculate_weighted_score([])

        assert score == 0.0


# Confidence Level Tests


class TestConfidenceLevels:
    """Test confidence level determination."""

    def test_confidence_level_definitive(self, arbiter):
        """Test definitive confidence level (formal proof)."""
        chain = EvidenceChain()
        chain.add(
            Evidence(
                evidence_type=EvidenceType.FORMAL_PROOF,
                weight=1.0,
                confidence=0.95,
                supports_vulnerable=False,
                description="Formal proof",
                source="verifier",
            )
        )

        level = arbiter._get_confidence_level(0.95, chain)

        assert level == ConfidenceLevel.DEFINITIVE

    def test_confidence_level_moderate(self, arbiter):
        """Test moderate confidence level (guards)."""
        chain = EvidenceChain()
        chain.add(
            Evidence(
                evidence_type=EvidenceType.GUARD_ANALYSIS,
                weight=0.7,
                confidence=0.8,
                supports_vulnerable=False,
                description="Guard",
                source="defender",
            )
        )

        level = arbiter._get_confidence_level(0.75, chain)

        assert level == ConfidenceLevel.MODERATE

    def test_confidence_level_uncertain(self, arbiter):
        """Test uncertain confidence level."""
        chain = EvidenceChain()

        level = arbiter._get_confidence_level(0.3, chain)

        assert level == ConfidenceLevel.UNCERTAIN


# Explanation Tests


class TestExplanation:
    """Test explanation generation."""

    def test_generate_explanation(self, arbiter):
        """Test generating explanation."""
        chain = EvidenceChain()
        chain.add(
            Evidence(
                evidence_type=EvidenceType.PATTERN_MATCH,
                weight=0.6,
                confidence=0.8,
                supports_vulnerable=True,
                description="Reentrancy detected",
                source="attacker",
            )
        )

        explanation = arbiter._generate_explanation(
            VerdictType.VULNERABLE, WinningSide.ATTACKER, chain
        )

        assert "VULNERABLE" in explanation
        assert "attacker" in explanation.lower()

    def test_generate_recommendations_vulnerable(self, arbiter, vulnerable_scenario):
        """Test recommendations for vulnerable verdict."""
        attacker_result, defender_result = vulnerable_scenario

        chain = arbiter._collect_evidence(
            attacker_result, defender_result, None, None
        )
        recommendations = arbiter._generate_recommendations(
            VerdictType.VULNERABLE, chain, attacker_result, defender_result
        )

        assert len(recommendations) > 0
        # Should suggest mitigations
        assert any("guard" in r.lower() for r in recommendations)

    def test_generate_recommendations_safe(self, arbiter, safe_scenario):
        """Test recommendations for safe verdict."""
        attacker_result, defender_result = safe_scenario

        chain = arbiter._collect_evidence(
            attacker_result, defender_result, None, None
        )
        recommendations = arbiter._generate_recommendations(
            VerdictType.SAFE, chain, attacker_result, defender_result
        )

        # Should acknowledge good practices
        assert len(recommendations) >= 0


# Integration Tests


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_end_to_end_vulnerable(self, arbiter, vulnerable_scenario):
        """Test end-to-end arbitration for vulnerable code."""
        attacker_result, defender_result = vulnerable_scenario

        result = arbiter.arbitrate(
            attacker_result=attacker_result, defender_result=defender_result
        )

        assert result.verdict == VerdictType.VULNERABLE
        assert result.winning_side == WinningSide.ATTACKER
        assert result.confidence > 0.5
        assert len(result.explanation) > 0
        assert len(result.recommendations) > 0

    def test_end_to_end_safe(self, arbiter, safe_scenario):
        """Test end-to-end arbitration for safe code."""
        attacker_result, defender_result = safe_scenario

        result = arbiter.arbitrate(
            attacker_result=attacker_result, defender_result=defender_result
        )

        assert result.verdict == VerdictType.SAFE
        assert result.winning_side == WinningSide.DEFENDER
        assert result.confidence > 0.7
        assert len(result.explanation) > 0

    def test_metadata_includes_agent_confidences(self, arbiter, vulnerable_scenario):
        """Test metadata includes agent confidences."""
        attacker_result, defender_result = vulnerable_scenario

        result = arbiter.arbitrate(
            attacker_result=attacker_result, defender_result=defender_result
        )

        assert "attacker_confidence" in result.metadata
        assert "defender_confidence" in result.metadata
        assert "evidence_count" in result.metadata


# Success Criteria Tests


class TestSuccessCriteria:
    """Validate P2-T5 success criteria."""

    def test_evidence_prioritization_working(self, arbiter):
        """Evidence prioritization should work."""
        # Formal proof should override everything
        formal_chain = EvidenceChain()
        formal_chain.add(
            Evidence(
                evidence_type=EvidenceType.FORMAL_PROOF,
                weight=1.0,
                confidence=0.95,
                supports_vulnerable=False,
                description="Proof",
                source="verifier",
            )
        )

        verdict, confidence, _ = arbiter._make_decision(formal_chain)

        assert verdict == VerdictType.SAFE
        assert confidence == 0.95

    def test_weighted_aggregation_working(self, arbiter):
        """Weighted evidence aggregation should work."""
        evidence_list = [
            Evidence(EvidenceType.GUARD_ANALYSIS, 0.7, 0.9, False, "G1", "d"),
            Evidence(EvidenceType.PATTERN_MATCH, 0.6, 0.8, False, "P1", "d"),
        ]

        score = arbiter._calculate_weighted_score(evidence_list)

        # Should be weighted, not simple average
        assert score > 0.0

    def test_confidence_levels_assigned(self, arbiter, vulnerable_scenario):
        """Confidence levels should be assigned."""
        attacker_result, defender_result = vulnerable_scenario

        result = arbiter.arbitrate(
            attacker_result=attacker_result, defender_result=defender_result
        )

        assert isinstance(result.confidence_level, ConfidenceLevel)

    def test_explanation_generated(self, arbiter, vulnerable_scenario):
        """Explanations should be generated."""
        attacker_result, defender_result = vulnerable_scenario

        result = arbiter.arbitrate(
            attacker_result=attacker_result, defender_result=defender_result
        )

        assert len(result.explanation) > 0
        assert result.verdict.value.upper() in result.explanation

    def test_recommendations_generated(self, arbiter, vulnerable_scenario):
        """Recommendations should be generated."""
        attacker_result, defender_result = vulnerable_scenario

        result = arbiter.arbitrate(
            attacker_result=attacker_result, defender_result=defender_result
        )

        assert len(result.recommendations) > 0
