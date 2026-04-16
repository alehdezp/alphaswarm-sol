"""Tests for structured debate protocol.

Tests the iMAD-inspired debate protocol implementation:
- Claim/rebuttal/synthesis phases
- Evidence anchoring requirements
- Human flagging for all debate outcomes
- Disagreement detection and handling
"""

import pytest
from datetime import datetime

from alphaswarm_sol.orchestration.schemas import (
    DebateClaim,
    DebateRecord,
    EvidenceItem,
    EvidencePacket,
    Verdict,
    VerdictConfidence,
)
from alphaswarm_sol.orchestration.debate import (
    DebateConfig,
    DebateOrchestrator,
    DebatePhase,
    DebateRound,
    run_debate,
)


class TestDebatePhases:
    """Test debate phase enum and structure."""

    def test_debate_phases_exist(self):
        """Debate has correct phases."""
        phases = [p.value for p in DebatePhase]
        assert "claim" in phases
        assert "rebuttal" in phases
        assert "synthesis" in phases
        assert "complete" in phases

    def test_debate_phase_order(self):
        """Phases are defined in correct order."""
        phases = list(DebatePhase)
        assert phases[0] == DebatePhase.CLAIM
        assert phases[1] == DebatePhase.REBUTTAL
        assert phases[2] == DebatePhase.SYNTHESIS
        assert phases[3] == DebatePhase.COMPLETE

    def test_debate_round_creation(self):
        """DebateRound can be created with phase."""
        round_obj = DebateRound(phase=DebatePhase.CLAIM)
        assert round_obj.phase == DebatePhase.CLAIM
        assert round_obj.attacker_argument is None
        assert round_obj.defender_argument is None
        assert isinstance(round_obj.timestamp, datetime)

    def test_debate_round_with_arguments(self):
        """DebateRound can hold attacker and defender arguments."""
        attacker_claim = DebateClaim(
            role="attacker",
            claim="Exploit found",
            evidence=[],
            reasoning="Analysis",
        )
        defender_claim = DebateClaim(
            role="defender",
            claim="Protected",
            evidence=[],
            reasoning="Guards present",
        )

        round_obj = DebateRound(
            phase=DebatePhase.CLAIM,
            attacker_argument=attacker_claim,
            defender_argument=defender_claim,
        )

        assert round_obj.attacker_argument.claim == "Exploit found"
        assert round_obj.defender_argument.claim == "Protected"


class TestDebateConfig:
    """Test debate configuration."""

    def test_default_config(self):
        """Default config has expected values."""
        config = DebateConfig()
        assert config.max_rebuttal_rounds == 2
        assert config.require_evidence is True
        assert config.auto_flag_human is True

    def test_custom_config(self):
        """Config can be customized."""
        config = DebateConfig(
            max_rebuttal_rounds=5,
            require_evidence=False,
            auto_flag_human=False,
        )
        assert config.max_rebuttal_rounds == 5
        assert config.require_evidence is False


class TestDebateProtocol:
    """Test structured debate protocol execution."""

    def test_debate_always_human_flagged(self):
        """Debate outcomes are always human-flagged."""
        orchestrator = DebateOrchestrator()
        evidence = EvidencePacket(finding_id="VKG-001")

        verdict = orchestrator.run_debate(
            bead_id="VKG-001",
            evidence=evidence,
            attacker_context={},
            defender_context={},
        )

        assert verdict.human_flag is True

    def test_debate_creates_verdict(self):
        """Debate creates a verdict with correct bead_id."""
        orchestrator = DebateOrchestrator()
        evidence = EvidencePacket(finding_id="VKG-001")

        verdict = orchestrator.run_debate(
            bead_id="VKG-001",
            evidence=evidence,
            attacker_context={},
            defender_context={},
        )

        assert verdict.finding_id == "VKG-001"
        assert isinstance(verdict.confidence, VerdictConfidence)

    def test_debate_with_custom_config(self):
        """Debate respects custom configuration."""
        config = DebateConfig(max_rebuttal_rounds=1)
        orchestrator = DebateOrchestrator(config=config)
        evidence = EvidencePacket(finding_id="VKG-001")

        verdict = orchestrator.run_debate(
            bead_id="VKG-001",
            evidence=evidence,
            attacker_context={},
            defender_context={},
        )

        # Should still produce valid verdict
        assert verdict.human_flag is True

    def test_claim_round_structure(self):
        """Claim round has both attacker and defender claims."""
        orchestrator = DebateOrchestrator()
        evidence = EvidencePacket(finding_id="VKG-001")

        round_obj = orchestrator._run_claim_round(evidence, {}, {})

        assert round_obj.phase == DebatePhase.CLAIM
        # Without agents, we get placeholder claims
        assert round_obj.attacker_argument is not None
        assert round_obj.defender_argument is not None

    def test_rebuttal_round_structure(self):
        """Rebuttal round challenges previous claims."""
        orchestrator = DebateOrchestrator()
        evidence = EvidencePacket(finding_id="VKG-001")

        # First run claim round
        claim_round = orchestrator._run_claim_round(evidence, {}, {})

        # Then run rebuttal
        rebuttal_round = orchestrator._run_rebuttal_round(
            claim_round, evidence, {}, {}
        )

        assert rebuttal_round.phase == DebatePhase.REBUTTAL


class TestEvidenceAnchoring:
    """Test evidence anchoring in debate."""

    def test_evidence_item_has_location(self):
        """Evidence items can have code locations."""
        item = EvidenceItem(
            type="behavioral_signature",
            value="R:bal->X:out->W:bal",
            location="Vault.sol:142",
            confidence=0.9,
            source="pattern_engine",
        )

        assert item.location == "Vault.sol:142"
        assert item.confidence == 0.9

    def test_evidence_item_confidence_range(self):
        """Evidence confidence must be in valid range."""
        # Valid confidence
        item = EvidenceItem(
            type="guard",
            value="nonReentrant",
            location="Vault.sol:50",
            confidence=0.95,
        )
        assert item.confidence == 0.95

        # Invalid confidence raises
        with pytest.raises(ValueError):
            EvidenceItem(
                type="guard",
                value="test",
                location="test",
                confidence=1.5,  # Out of range
            )

    def test_claim_has_evidence(self):
        """Claims can have evidence items."""
        evidence_items = [
            EvidenceItem(
                type="attack_vector",
                value="Reentrancy via withdraw",
                location="Vault.sol:142",
                confidence=0.85,
                source="attacker_agent",
            )
        ]

        claim = DebateClaim(
            role="attacker",
            claim="Reentrancy vulnerability in withdraw",
            evidence=evidence_items,
            reasoning="External call before state update",
        )

        assert len(claim.evidence) == 1
        assert claim.evidence[0].location == "Vault.sol:142"

    def test_evidence_packet_average_confidence(self):
        """Evidence packet calculates average confidence."""
        packet = EvidencePacket(
            finding_id="VKG-001",
            items=[
                EvidenceItem(type="a", value="1", location="l1", confidence=0.8),
                EvidenceItem(type="b", value="2", location="l2", confidence=0.6),
            ],
        )

        assert packet.average_confidence == 0.7

    def test_evidence_packet_locations(self):
        """Evidence packet collects unique locations."""
        packet = EvidencePacket(
            finding_id="VKG-001",
            items=[
                EvidenceItem(type="a", value="1", location="Vault.sol:10"),
                EvidenceItem(type="b", value="2", location="Vault.sol:20"),
                EvidenceItem(type="c", value="3", location="Vault.sol:10"),  # Duplicate
            ],
        )

        locations = packet.locations
        assert len(locations) == 2
        assert "Vault.sol:10" in locations
        assert "Vault.sol:20" in locations


class TestDebateOutcomes:
    """Test debate outcome determination."""

    def test_attacker_wins_when_stronger(self):
        """Attacker wins when evidence is stronger."""
        orchestrator = DebateOrchestrator()

        debate = DebateRecord(
            finding_id="VKG-001",
            attacker_claim=DebateClaim(
                role="attacker",
                claim="Exploit exists",
                evidence=[
                    EvidenceItem(
                        type="attack",
                        value="path",
                        location="l1",
                        confidence=0.9,
                    ),
                ],
                reasoning="Strong attack path",
            ),
            defender_claim=DebateClaim(
                role="defender",
                claim="Protected",
                evidence=[
                    EvidenceItem(
                        type="guard",
                        value="check",
                        location="l2",
                        confidence=0.3,
                    ),
                ],
                reasoning="Weak guard",
            ),
        )

        confidence = orchestrator._assess_debate_outcome(debate)
        assert confidence == VerdictConfidence.LIKELY

    def test_defender_wins_when_stronger(self):
        """Defender wins when evidence is stronger."""
        orchestrator = DebateOrchestrator()

        debate = DebateRecord(
            finding_id="VKG-001",
            attacker_claim=DebateClaim(
                role="attacker",
                claim="Maybe exploit",
                evidence=[
                    EvidenceItem(
                        type="attack",
                        value="weak",
                        location="l1",
                        confidence=0.2,
                    ),
                ],
                reasoning="Weak attack",
            ),
            defender_claim=DebateClaim(
                role="defender",
                claim="Strong guard",
                evidence=[
                    EvidenceItem(
                        type="guard",
                        value="nonReentrant",
                        location="l2",
                        confidence=0.95,
                    ),
                ],
                reasoning="Strong defense",
            ),
        )

        confidence = orchestrator._assess_debate_outcome(debate)
        assert confidence == VerdictConfidence.REJECTED

    def test_uncertain_when_close(self):
        """Uncertain when evidence is close."""
        orchestrator = DebateOrchestrator()

        debate = DebateRecord(
            finding_id="VKG-001",
            attacker_claim=DebateClaim(
                role="attacker",
                claim="Possible",
                evidence=[
                    EvidenceItem(
                        type="attack",
                        value="path",
                        location="l1",
                        confidence=0.5,
                    ),
                ],
                reasoning="Medium attack",
            ),
            defender_claim=DebateClaim(
                role="defender",
                claim="Maybe protected",
                evidence=[
                    EvidenceItem(
                        type="guard",
                        value="check",
                        location="l2",
                        confidence=0.55,
                    ),
                ],
                reasoning="Medium defense",
            ),
        )

        confidence = orchestrator._assess_debate_outcome(debate)
        assert confidence == VerdictConfidence.UNCERTAIN

    def test_uncertain_with_no_evidence(self):
        """Uncertain when neither side has evidence."""
        orchestrator = DebateOrchestrator()

        debate = DebateRecord(
            finding_id="VKG-001",
            attacker_claim=DebateClaim(
                role="attacker",
                claim="Maybe",
                evidence=[],
                reasoning="No evidence",
            ),
            defender_claim=DebateClaim(
                role="defender",
                claim="Maybe safe",
                evidence=[],
                reasoning="No evidence",
            ),
        )

        confidence = orchestrator._assess_debate_outcome(debate)
        assert confidence == VerdictConfidence.UNCERTAIN


class TestDissentTracking:
    """Test dissenting opinion tracking."""

    def test_dissent_recorded_when_defender_strong(self):
        """Dissent recorded when defender had strong evidence."""
        orchestrator = DebateOrchestrator()

        debate = DebateRecord(
            finding_id="VKG-001",
            attacker_claim=DebateClaim(
                role="attacker",
                claim="Attack possible",
                evidence=[
                    EvidenceItem(
                        type="attack",
                        value="path",
                        location="l1",
                        confidence=0.95,
                    ),
                ],
                reasoning="Strong attack",
            ),
            defender_claim=DebateClaim(
                role="defender",
                claim="Guard at L138 should block",
                evidence=[
                    EvidenceItem(
                        type="guard",
                        value="check",
                        location="l2",
                        confidence=0.8,
                    ),
                ],
                reasoning="Strong guard",
            ),
        )

        dissent = orchestrator._check_for_dissent(debate)
        assert dissent is not None
        assert "Guard" in dissent or "defender" in dissent.lower()

    def test_no_dissent_when_defender_weak(self):
        """No dissent when defender had weak evidence."""
        orchestrator = DebateOrchestrator()

        debate = DebateRecord(
            finding_id="VKG-001",
            attacker_claim=DebateClaim(
                role="attacker",
                claim="Attack",
                evidence=[],
                reasoning="Attack",
            ),
            defender_claim=DebateClaim(
                role="defender",
                claim="Weak guard",
                evidence=[
                    EvidenceItem(
                        type="guard",
                        value="weak",
                        location="l1",
                        confidence=0.3,
                    ),
                ],
                reasoning="Weak",
            ),
        )

        dissent = orchestrator._check_for_dissent(debate)
        assert dissent is None

    def test_no_dissent_without_defender(self):
        """No dissent when defender has no claim."""
        orchestrator = DebateOrchestrator()

        debate = DebateRecord(
            finding_id="VKG-001",
            attacker_claim=DebateClaim(
                role="attacker",
                claim="Attack",
                evidence=[],
                reasoning="Attack",
            ),
        )

        dissent = orchestrator._check_for_dissent(debate)
        assert dissent is None


class TestDebateRecord:
    """Test debate record creation and completion."""

    def test_debate_record_from_rounds(self):
        """Debate record is built correctly from rounds."""
        orchestrator = DebateOrchestrator()

        # Create rounds
        claim_round = DebateRound(
            phase=DebatePhase.CLAIM,
            attacker_argument=DebateClaim(
                role="attacker",
                claim="Attack claim",
                evidence=[],
                reasoning="Reason",
            ),
            defender_argument=DebateClaim(
                role="defender",
                claim="Defense claim",
                evidence=[],
                reasoning="Reason",
            ),
        )

        rebuttal_round = DebateRound(
            phase=DebatePhase.REBUTTAL,
            attacker_argument=DebateClaim(
                role="attacker",
                claim="Attacker rebuttal",
                evidence=[],
                reasoning="Rebuttal reason",
            ),
        )

        record = orchestrator._build_debate_record("VKG-001", [claim_round, rebuttal_round])

        assert record.finding_id == "VKG-001"
        assert record.attacker_claim is not None
        assert record.defender_claim is not None
        assert len(record.rebuttals) == 1

    def test_debate_record_completion(self):
        """Debate record can be marked complete."""
        record = DebateRecord(finding_id="VKG-001")

        assert not record.is_complete
        record.complete("Synthesis summary", "Dissenting opinion")

        assert record.is_complete
        assert record.verifier_summary == "Synthesis summary"
        assert record.dissenting_opinion == "Dissenting opinion"


class TestConvenienceFunction:
    """Test run_debate convenience function."""

    def test_run_debate_returns_verdict(self):
        """run_debate returns valid verdict."""
        evidence = EvidencePacket(finding_id="VKG-001")

        verdict = run_debate(
            bead_id="VKG-001",
            evidence=evidence,
            attacker_context={},
            defender_context={},
        )

        assert isinstance(verdict, Verdict)
        assert verdict.finding_id == "VKG-001"
        assert verdict.human_flag is True

    def test_run_debate_with_agents(self):
        """run_debate accepts agent parameters."""
        evidence = EvidencePacket(finding_id="VKG-001")

        verdict = run_debate(
            bead_id="VKG-001",
            evidence=evidence,
            attacker_context={},
            defender_context={},
            attacker_agent=None,
            defender_agent=None,
            verifier_agent=None,
        )

        assert verdict.human_flag is True

    def test_run_debate_with_config(self):
        """run_debate accepts custom config."""
        evidence = EvidencePacket(finding_id="VKG-001")
        config = DebateConfig(max_rebuttal_rounds=0)

        verdict = run_debate(
            bead_id="VKG-001",
            evidence=evidence,
            attacker_context={},
            defender_context={},
            config=config,
        )

        assert verdict.human_flag is True


class TestRationaleSynthesis:
    """Test rationale synthesis from debate."""

    def test_synthesize_rationale_both_claims(self):
        """Rationale includes both attacker and defender claims."""
        orchestrator = DebateOrchestrator()

        debate = DebateRecord(
            finding_id="VKG-001",
            attacker_claim=DebateClaim(
                role="attacker",
                claim="Reentrancy possible",
                evidence=[],
                reasoning="R",
            ),
            defender_claim=DebateClaim(
                role="defender",
                claim="Guard blocks attack",
                evidence=[],
                reasoning="R",
            ),
        )

        rationale = orchestrator._synthesize_rationale(debate)

        assert "Attacker:" in rationale
        assert "Defender:" in rationale
        assert "Reentrancy" in rationale
        assert "Guard" in rationale

    def test_synthesize_rationale_with_rebuttals(self):
        """Rationale mentions rebuttals if present."""
        orchestrator = DebateOrchestrator()

        debate = DebateRecord(
            finding_id="VKG-001",
            attacker_claim=DebateClaim(
                role="attacker",
                claim="Attack",
                evidence=[],
                reasoning="R",
            ),
            defender_claim=DebateClaim(
                role="defender",
                claim="Defense",
                evidence=[],
                reasoning="R",
            ),
            rebuttals=[
                DebateClaim(role="attacker", claim="Rebuttal", evidence=[], reasoning="R"),
            ],
        )

        rationale = orchestrator._synthesize_rationale(debate)
        assert "Rebuttals:" in rationale

    def test_synthesize_rationale_no_debate(self):
        """Rationale handles empty debate."""
        orchestrator = DebateOrchestrator()

        debate = DebateRecord(finding_id="VKG-001")
        rationale = orchestrator._synthesize_rationale(debate)

        assert rationale == "No debate conducted"


class TestPhaseHandlersIntegration:
    """Test handlers integration with debate."""

    def test_handler_config_defaults(self):
        """HandlerConfig has sensible defaults."""
        from alphaswarm_sol.orchestration.handlers import HandlerConfig

        config = HandlerConfig()
        assert config.project_root.exists() or str(config.project_root) == "."
        assert config.use_llm is False
        assert config.verbose is False

    def test_create_default_handlers_exists(self):
        """create_default_handlers function is available."""
        from alphaswarm_sol.orchestration.handlers import create_default_handlers
        from alphaswarm_sol.orchestration.router import RouteAction

        # Just verify it's importable and callable
        assert callable(create_default_handlers)

    def test_run_debate_handler_exists(self):
        """RunDebateHandler is available."""
        from alphaswarm_sol.orchestration.handlers import RunDebateHandler

        assert RunDebateHandler is not None
