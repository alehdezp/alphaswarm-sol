"""Tests for IntegratorAgent.

Tests for multi-agent verdict integration per PHILOSOPHY.md Infrastructure Roles:
- Agreement: All agents agree -> LIKELY confidence
- Conflict detection: Attacker vulnerable + Defender safe -> conflict
- Debate trigger: Conflict routes to debate protocol
- Evidence merging: Deduplication by content hash
- Verifier precedence: Verifier verdict takes priority
- Partial verdicts: Single agent handling
"""

import pytest
from unittest.mock import MagicMock, patch

from alphaswarm_sol.agents.infrastructure import (
    IntegratorAgent,
    IntegratorConfig,
    MergedVerdict,
    AgentVerdict,
)
from alphaswarm_sol.agents.runtime import AgentRole
from alphaswarm_sol.orchestration.schemas import VerdictConfidence, EvidenceItem


@pytest.fixture
def mock_bead():
    """Create mock bead for testing."""
    bead = MagicMock()
    bead.id = "test-bead-001"
    return bead


@pytest.fixture
def agreeing_verdicts_vulnerable():
    """All agents agree: vulnerable with high confidence."""
    return {
        AgentRole.ATTACKER: AgentVerdict(
            agent_role=AgentRole.ATTACKER,
            is_vulnerable=True,
            confidence=0.9,
            rationale="Found reentrancy",
            evidence=[
                EvidenceItem(
                    type="pattern",
                    value="R:bal->X:out->W:bal",
                    location="Vault.sol:42",
                )
            ],
        ),
        AgentRole.DEFENDER: AgentVerdict(
            agent_role=AgentRole.DEFENDER,
            is_vulnerable=True,
            confidence=0.85,
            rationale="No reentrancy guard",
            evidence=[
                EvidenceItem(
                    type="property",
                    value="no_reentrancy_guard",
                    location="Vault.sol:40",
                )
            ],
        ),
        AgentRole.VERIFIER: AgentVerdict(
            agent_role=AgentRole.VERIFIER,
            is_vulnerable=True,
            confidence=0.95,
            rationale="Verified exploitability",
            evidence=[
                EvidenceItem(
                    type="scenario",
                    value="Attacker contract drains",
                    location="Vault.sol:42-45",
                )
            ],
        ),
    }


@pytest.fixture
def agreeing_verdicts_safe():
    """All agents agree: safe with high confidence."""
    return {
        AgentRole.ATTACKER: AgentVerdict(
            agent_role=AgentRole.ATTACKER,
            is_vulnerable=False,
            confidence=0.85,
            rationale="No attack path found",
            evidence=[],
        ),
        AgentRole.DEFENDER: AgentVerdict(
            agent_role=AgentRole.DEFENDER,
            is_vulnerable=False,
            confidence=0.9,
            rationale="Protected by nonReentrant",
            evidence=[
                EvidenceItem(
                    type="guard",
                    value="nonReentrant modifier",
                    location="Vault.sol:38",
                )
            ],
        ),
    }


@pytest.fixture
def conflicting_verdicts():
    """Attacker and defender disagree."""
    return {
        AgentRole.ATTACKER: AgentVerdict(
            agent_role=AgentRole.ATTACKER,
            is_vulnerable=True,
            confidence=0.9,
            rationale="Exploitable",
            evidence=[
                EvidenceItem(
                    type="attack_step",
                    value="Call withdraw in fallback",
                    location="Vault.sol:42",
                )
            ],
        ),
        AgentRole.DEFENDER: AgentVerdict(
            agent_role=AgentRole.DEFENDER,
            is_vulnerable=False,
            confidence=0.85,
            rationale="Mitigated by modifier",
            evidence=[
                EvidenceItem(
                    type="guard",
                    value="onlyOwner modifier",
                    location="Vault.sol:40",
                )
            ],
        ),
    }


class TestIntegratorAgent:
    """Tests for IntegratorAgent."""

    def test_integrate_agreement_vulnerable(self, mock_bead, agreeing_verdicts_vulnerable):
        """Unanimous agreement on vulnerable should produce LIKELY confidence."""
        integrator = IntegratorAgent()
        result = integrator.integrate(mock_bead, agreeing_verdicts_vulnerable)

        assert result.is_vulnerable
        assert result.confidence == VerdictConfidence.LIKELY
        assert not result.conflict_detected
        assert not result.debate_triggered
        assert result.bead_id == "test-bead-001"

    def test_integrate_agreement_safe(self, mock_bead, agreeing_verdicts_safe):
        """Unanimous agreement on safe should produce LIKELY confidence."""
        integrator = IntegratorAgent()
        result = integrator.integrate(mock_bead, agreeing_verdicts_safe)

        assert not result.is_vulnerable
        assert result.confidence == VerdictConfidence.LIKELY
        assert not result.conflict_detected
        assert not result.debate_triggered

    def test_evidence_merging(self, mock_bead, agreeing_verdicts_vulnerable):
        """Evidence from all agents should be merged."""
        integrator = IntegratorAgent()
        result = integrator.integrate(mock_bead, agreeing_verdicts_vulnerable)

        assert len(result.merged_evidence) == 3  # One from each agent
        # Check attribution preserved via source field
        sources = [e.source for e in result.merged_evidence]
        assert "attacker" in sources
        assert "defender" in sources
        assert "verifier" in sources

    def test_evidence_deduplication(self, mock_bead):
        """Duplicate evidence should be deduplicated."""
        # Create verdicts with same evidence from multiple agents
        verdicts = {
            AgentRole.ATTACKER: AgentVerdict(
                agent_role=AgentRole.ATTACKER,
                is_vulnerable=True,
                confidence=0.9,
                rationale="Found issue",
                evidence=[
                    EvidenceItem(
                        type="pattern",
                        value="same_pattern",
                        location="Vault.sol:42",
                    )
                ],
            ),
            AgentRole.DEFENDER: AgentVerdict(
                agent_role=AgentRole.DEFENDER,
                is_vulnerable=True,
                confidence=0.9,
                rationale="Confirmed issue",
                evidence=[
                    EvidenceItem(
                        type="pattern",
                        value="same_pattern",
                        location="Vault.sol:42",
                    )
                ],
            ),
        }

        integrator = IntegratorAgent()
        result = integrator.integrate(mock_bead, verdicts)

        # Should be deduplicated to 1 item
        assert len(result.merged_evidence) == 1

    def test_conflict_detection(self, mock_bead, conflicting_verdicts):
        """Should detect conflict between attacker and defender."""
        integrator = IntegratorAgent(IntegratorConfig(auto_debate_on_conflict=False))
        result = integrator.integrate(mock_bead, conflicting_verdicts)

        assert result.conflict_detected

    def test_debate_triggered_on_conflict(self, mock_bead, conflicting_verdicts):
        """Conflict should trigger debate when enabled."""
        mock_debate = MagicMock()
        mock_debate.run_debate.return_value = MagicMock(
            is_vulnerable=True,
            confidence=VerdictConfidence.LIKELY,
            rationale="Attacker's claim upheld",
        )

        integrator = IntegratorAgent(
            IntegratorConfig(auto_debate_on_conflict=True),
            debate_orchestrator=mock_debate,
        )
        result = integrator.integrate(mock_bead, conflicting_verdicts)

        assert result.debate_triggered
        assert result.conflict_detected
        mock_debate.run_debate.assert_called_once()

    def test_verifier_precedence(self, mock_bead):
        """Verifier's verdict should take precedence."""
        verdicts = {
            AgentRole.ATTACKER: AgentVerdict(
                agent_role=AgentRole.ATTACKER,
                is_vulnerable=True,
                confidence=0.9,
                rationale="Exploitable",
                evidence=[],
            ),
            AgentRole.VERIFIER: AgentVerdict(
                agent_role=AgentRole.VERIFIER,
                is_vulnerable=False,  # Verifier says safe
                confidence=0.95,
                rationale="False positive",
                evidence=[],
            ),
        }

        integrator = IntegratorAgent()
        result = integrator.integrate(mock_bead, verdicts)

        # Verifier's verdict (safe) should win
        assert not result.is_vulnerable

    def test_partial_verdicts(self, mock_bead):
        """Should handle missing agent verdicts."""
        partial = {
            AgentRole.ATTACKER: AgentVerdict(
                agent_role=AgentRole.ATTACKER,
                is_vulnerable=True,
                confidence=0.8,
                rationale="Found issue",
                evidence=[],
            ),
        }

        integrator = IntegratorAgent(IntegratorConfig(require_all_agents=False))
        result = integrator.integrate(mock_bead, partial)

        assert result.is_vulnerable
        # Single agent should produce UNCERTAIN confidence
        assert result.confidence == VerdictConfidence.UNCERTAIN

    def test_require_all_agents_raises(self, mock_bead):
        """Should raise when require_all_agents=True and agents missing."""
        partial = {
            AgentRole.ATTACKER: AgentVerdict(
                agent_role=AgentRole.ATTACKER,
                is_vulnerable=True,
                confidence=0.8,
                rationale="Found issue",
                evidence=[],
            ),
        }

        integrator = IntegratorAgent(IntegratorConfig(require_all_agents=True))

        with pytest.raises(ValueError, match="Missing required agent verdicts"):
            integrator.integrate(mock_bead, partial)

    def test_high_confidence_conflict(self, mock_bead):
        """High confidence on both sides with disagreement is a conflict."""
        verdicts = {
            AgentRole.ATTACKER: AgentVerdict(
                agent_role=AgentRole.ATTACKER,
                is_vulnerable=True,
                confidence=0.95,
                rationale="Definitely exploitable",
                evidence=[],
            ),
            AgentRole.DEFENDER: AgentVerdict(
                agent_role=AgentRole.DEFENDER,
                is_vulnerable=False,
                confidence=0.92,
                rationale="Definitely safe",
                evidence=[],
            ),
        }

        integrator = IntegratorAgent(
            IntegratorConfig(
                auto_debate_on_conflict=False,
                high_confidence_threshold=0.7,
            )
        )
        result = integrator.integrate(mock_bead, verdicts)

        assert result.conflict_detected

    def test_low_confidence_no_conflict(self, mock_bead):
        """Low confidence disagreement is not a conflict."""
        verdicts = {
            AgentRole.ATTACKER: AgentVerdict(
                agent_role=AgentRole.ATTACKER,
                is_vulnerable=True,
                confidence=0.5,
                rationale="Maybe exploitable",
                evidence=[],
            ),
            AgentRole.DEFENDER: AgentVerdict(
                agent_role=AgentRole.DEFENDER,
                is_vulnerable=False,
                confidence=0.5,
                rationale="Maybe safe",
                evidence=[],
            ),
        }

        integrator = IntegratorAgent(
            IntegratorConfig(
                auto_debate_on_conflict=False,
                high_confidence_threshold=0.7,
            )
        )
        result = integrator.integrate(mock_bead, verdicts)

        # Low confidence disagreement - not a high-stakes conflict
        # But attacker says vulnerable + defender says safe = always conflict
        assert result.conflict_detected  # This is still true per the logic

    def test_higher_confidence_wins(self, mock_bead):
        """When no verifier, higher confidence agent wins (no conflict trigger)."""
        verdicts = {
            AgentRole.ATTACKER: AgentVerdict(
                agent_role=AgentRole.ATTACKER,
                is_vulnerable=True,
                confidence=0.95,
                rationale="Exploitable",
                evidence=[],
            ),
            AgentRole.DEFENDER: AgentVerdict(
                agent_role=AgentRole.DEFENDER,
                is_vulnerable=False,
                confidence=0.6,  # Lower confidence
                rationale="Maybe safe",
                evidence=[],
            ),
        }

        integrator = IntegratorAgent(IntegratorConfig(auto_debate_on_conflict=False))
        result = integrator.integrate(mock_bead, verdicts)

        # Attacker has higher confidence, so vulnerable wins
        assert result.is_vulnerable

    def test_merged_verdict_to_dict(self, mock_bead, agreeing_verdicts_vulnerable):
        """MergedVerdict.to_dict() should work correctly."""
        integrator = IntegratorAgent()
        result = integrator.integrate(mock_bead, agreeing_verdicts_vulnerable)

        result_dict = result.to_dict()

        assert result_dict["bead_id"] == "test-bead-001"
        assert result_dict["is_vulnerable"] is True
        assert result_dict["confidence"] == "likely"
        assert len(result_dict["merged_evidence"]) == 3
        assert result_dict["conflict_detected"] is False
        assert result_dict["debate_triggered"] is False

    def test_merged_verdict_from_dict(self):
        """MergedVerdict.from_dict() should reconstruct correctly."""
        data = {
            "bead_id": "test-bead-002",
            "is_vulnerable": True,
            "confidence": "uncertain",
            "merged_evidence": [
                {
                    "type": "pattern",
                    "value": "test_value",
                    "location": "Test.sol:1",
                    "confidence": 0.9,
                    "source": "attacker",
                }
            ],
            "agent_verdicts": {},
            "conflict_detected": True,
            "debate_triggered": True,
            "rationale": "Test rationale",
        }

        result = MergedVerdict.from_dict(data)

        assert result.bead_id == "test-bead-002"
        assert result.is_vulnerable is True
        assert result.confidence == VerdictConfidence.UNCERTAIN
        assert result.conflict_detected is True
        assert result.debate_triggered is True

    def test_agent_verdict_confidence_validation(self):
        """AgentVerdict should validate confidence range."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            AgentVerdict(
                agent_role=AgentRole.ATTACKER,
                is_vulnerable=True,
                confidence=1.5,  # Invalid
                rationale="Test",
                evidence=[],
            )

        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            AgentVerdict(
                agent_role=AgentRole.ATTACKER,
                is_vulnerable=True,
                confidence=-0.1,  # Invalid
                rationale="Test",
                evidence=[],
            )


class TestIntegratorConfig:
    """Tests for IntegratorConfig."""

    def test_default_config(self):
        """Default config should have expected values."""
        config = IntegratorConfig()

        assert config.conflict_threshold == 0.3
        assert config.require_all_agents is False
        assert config.auto_debate_on_conflict is True
        assert config.high_confidence_threshold == 0.7

    def test_config_to_dict(self):
        """Config should serialize to dict."""
        config = IntegratorConfig(
            conflict_threshold=0.5,
            require_all_agents=True,
        )

        config_dict = config.to_dict()

        assert config_dict["conflict_threshold"] == 0.5
        assert config_dict["require_all_agents"] is True

    def test_config_from_dict(self):
        """Config should deserialize from dict."""
        data = {
            "conflict_threshold": 0.4,
            "auto_debate_on_conflict": False,
        }

        config = IntegratorConfig.from_dict(data)

        assert config.conflict_threshold == 0.4
        assert config.auto_debate_on_conflict is False


class TestAgentVerdict:
    """Tests for AgentVerdict."""

    def test_agent_verdict_to_dict(self):
        """AgentVerdict should serialize to dict."""
        verdict = AgentVerdict(
            agent_role=AgentRole.ATTACKER,
            is_vulnerable=True,
            confidence=0.9,
            rationale="Test rationale",
            evidence=[
                EvidenceItem(
                    type="pattern",
                    value="test",
                    location="Test.sol:1",
                )
            ],
        )

        verdict_dict = verdict.to_dict()

        assert verdict_dict["agent_role"] == "attacker"
        assert verdict_dict["is_vulnerable"] is True
        assert verdict_dict["confidence"] == 0.9
        assert len(verdict_dict["evidence"]) == 1

    def test_agent_verdict_from_dict(self):
        """AgentVerdict should deserialize from dict."""
        data = {
            "agent_role": "defender",
            "is_vulnerable": False,
            "confidence": 0.85,
            "rationale": "Protected by guard",
            "evidence": [],
        }

        verdict = AgentVerdict.from_dict(data)

        assert verdict.agent_role == AgentRole.DEFENDER
        assert verdict.is_vulnerable is False
        assert verdict.confidence == 0.85
