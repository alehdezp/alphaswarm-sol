"""Tests for 3.1c-10 Agent Evaluation.

Integration tests that evaluate agent workflows using the full pipeline.

Agents tested (from Core-tier contracts):
- vrs-attacker
- vrs-defender
- vrs-verifier
- vrs-secure-reviewer
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from alphaswarm_sol.testing.evaluation.contract_loader import load_contract
from alphaswarm_sol.testing.evaluation.models import (
    DebriefResponse,
    ScoreCard,
)
from tests.workflow_harness.graders.reasoning_evaluator import ReasoningEvaluator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@dataclass
class SimulatedAgentOutput:
    tool_sequence: list[str] = field(default_factory=list)
    bskg_queries: list[dict[str, Any]] = field(default_factory=list)
    transcript: Any = None


def _attacker_output() -> SimulatedAgentOutput:
    """Simulated attacker agent output."""
    return SimulatedAgentOutput(
        tool_sequence=["Bash", "Bash", "Read", "Bash", "Read"],
        bskg_queries=[
            {"category": "build-kg", "command": "alphaswarm build-kg contracts/"},
            {"category": "query", "command": "alphaswarm query 'no access control'"},
            {"category": "pattern-query", "command": "alphaswarm query pattern:reentrancy"},
        ],
    )


def _defender_output() -> SimulatedAgentOutput:
    """Simulated defender agent output."""
    return SimulatedAgentOutput(
        tool_sequence=["Bash", "Read", "Bash", "Read"],
        bskg_queries=[
            {"category": "query", "command": "alphaswarm query 'guards'"},
            {"category": "query", "command": "alphaswarm query 'access modifiers'"},
        ],
    )


# ---------------------------------------------------------------------------
# Agent: vrs-attacker
# ---------------------------------------------------------------------------


class TestAttackerEvaluation:
    def test_evaluates_without_error(self):
        ev = ReasoningEvaluator("agent-vrs-attacker")
        co = _attacker_output()
        result = ev.evaluate(co)
        assert isinstance(result, ScoreCard)

    def test_attacker_contract_exists(self):
        contract = load_contract("agent-vrs-attacker")
        assert contract["category"] == "agent"

    def test_good_attacker_scores_above_bad(self):
        ev = ReasoningEvaluator("agent-vrs-attacker")
        good = _attacker_output()
        bad = SimulatedAgentOutput(tool_sequence=["Read"])

        good_result = ev.evaluate(good)
        bad_result = ev.evaluate(bad)
        assert good_result.overall_score > bad_result.overall_score

    def test_with_debrief(self):
        ev = ReasoningEvaluator("agent-vrs-attacker")
        co = _attacker_output()
        debrief = DebriefResponse(
            agent_name="attacker",
            agent_type="vrs-attacker",
            layer_used="transcript_analysis",
            questions=["Q1"],
            answers=["A1"],
            confidence=0.3,
        )
        result = ev.evaluate(co, debrief=debrief)
        assert isinstance(result, ScoreCard)


# ---------------------------------------------------------------------------
# Agent: vrs-defender
# ---------------------------------------------------------------------------


class TestDefenderEvaluation:
    def test_evaluates_without_error(self):
        ev = ReasoningEvaluator("agent-vrs-defender")
        co = _defender_output()
        result = ev.evaluate(co)
        assert isinstance(result, ScoreCard)

    def test_defender_contract_exists(self):
        contract = load_contract("agent-vrs-defender")
        assert contract["category"] == "agent"


# ---------------------------------------------------------------------------
# Agent: vrs-verifier
# ---------------------------------------------------------------------------


class TestVerifierEvaluation:
    def test_evaluates_without_error(self):
        ev = ReasoningEvaluator("agent-vrs-verifier")
        co = SimulatedAgentOutput(
            tool_sequence=["Bash", "Read", "Bash"],
            bskg_queries=[
                {"category": "query", "command": "alphaswarm query x"},
            ],
        )
        result = ev.evaluate(co)
        assert isinstance(result, ScoreCard)


# ---------------------------------------------------------------------------
# Agent: vrs-secure-reviewer
# ---------------------------------------------------------------------------


class TestSecureReviewerEvaluation:
    def test_evaluates_without_error(self):
        ev = ReasoningEvaluator("agent-vrs-secure-reviewer")
        co = SimulatedAgentOutput(
            tool_sequence=["Bash", "Read", "Grep", "Read"],
            bskg_queries=[
                {"category": "build-kg", "command": "alphaswarm build-kg contracts/"},
                {"category": "query", "command": "alphaswarm query 'auth'"},
            ],
        )
        result = ev.evaluate(co)
        assert isinstance(result, ScoreCard)

    def test_reviewer_contract_has_dimensions(self):
        contract = load_contract("agent-vrs-secure-reviewer")
        assert len(contract.get("reasoning_dimensions", [])) > 0
