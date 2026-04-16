"""Tests for 3.1c-09 Skill Evaluation.

Integration tests that evaluate skill workflows using the full pipeline:
contract → evaluator → score_card. Uses simulated mode with fake output.

Skills tested (from Core-tier contracts):
- vrs-audit
- vrs-verify
- vrs-investigate
- vrs-debate
- vrs-tool-slither
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from alphaswarm_sol.testing.evaluation.contract_loader import load_contract
from alphaswarm_sol.testing.evaluation.models import (
    EvaluationResult,
    RunMode,
    ScoreCard,
)
from tests.workflow_harness.graders.reasoning_evaluator import ReasoningEvaluator
from tests.workflow_harness.lib.evaluation_runner import EvaluationRunner


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@dataclass
class SimulatedSkillOutput:
    """Simulated skill execution output for testing."""

    tool_sequence: list[str] = field(default_factory=list)
    bskg_queries: list[dict[str, Any]] = field(default_factory=list)
    transcript: Any = None
    scenario_name: str = "simulated"
    run_id: str = "sim-001"
    duration_ms: float = 1000.0
    cost_usd: float = 0.05
    failure_notes: str = ""
    response_text: str = ""
    structured_output: Any = None


def _good_investigation_output() -> SimulatedSkillOutput:
    """Output that mimics a good investigation workflow."""
    return SimulatedSkillOutput(
        tool_sequence=["Bash", "Bash", "Read", "Bash", "Read", "Write"],
        bskg_queries=[
            {"category": "build-kg", "command": "alphaswarm build-kg contracts/"},
            {"category": "query", "command": "alphaswarm query 'access control'"},
            {"category": "pattern-query", "command": "alphaswarm query pattern:reentrancy"},
            {"category": "analyze", "command": "alphaswarm analyze x"},
        ],
    )


def _minimal_output() -> SimulatedSkillOutput:
    """Minimal output — no BSKG usage."""
    return SimulatedSkillOutput(
        tool_sequence=["Read", "Read"],
    )


# ---------------------------------------------------------------------------
# Skill: vrs-audit (full investigation with GVS)
# ---------------------------------------------------------------------------


class TestVRSAuditEvaluation:
    def test_good_audit_passes(self):
        ev = ReasoningEvaluator("skill-vrs-audit")
        co = _good_investigation_output()
        result = ev.evaluate(co)
        assert isinstance(result, ScoreCard)
        # A good investigation should score reasonably well
        assert result.overall_score > 30

    def test_minimal_audit_scores_lower(self):
        ev = ReasoningEvaluator("skill-vrs-audit")
        good_co = _good_investigation_output()
        bad_co = _minimal_output()

        good_result = ev.evaluate(good_co)
        bad_result = ev.evaluate(bad_co)
        assert good_result.overall_score > bad_result.overall_score

    def test_audit_contract_has_reasoning_dimensions(self):
        contract = load_contract("skill-vrs-audit")
        assert len(contract.get("reasoning_dimensions", [])) > 0


# ---------------------------------------------------------------------------
# Skill: vrs-verify (multi-agent verification)
# ---------------------------------------------------------------------------


class TestVRSVerifyEvaluation:
    def test_evaluates_without_error(self):
        ev = ReasoningEvaluator("skill-vrs-verify")
        co = SimulatedSkillOutput(
            tool_sequence=["Bash", "Read", "Bash"],
            bskg_queries=[{"category": "query", "command": "alphaswarm query x"}],
        )
        result = ev.evaluate(co)
        assert isinstance(result, ScoreCard)

    def test_verify_contract_exists(self):
        contract = load_contract("skill-vrs-verify")
        assert contract["category"] in ("skill", "orchestrator")


# ---------------------------------------------------------------------------
# Skill: vrs-investigate
# ---------------------------------------------------------------------------


class TestVRSInvestigateEvaluation:
    def test_evaluates_without_error(self):
        ev = ReasoningEvaluator("skill-vrs-investigate")
        co = _good_investigation_output()
        result = ev.evaluate(co)
        assert isinstance(result, ScoreCard)

    def test_investigate_contract_exists(self):
        contract = load_contract("skill-vrs-investigate")
        assert contract["category"] == "skill"


# ---------------------------------------------------------------------------
# Skill: vrs-debate
# ---------------------------------------------------------------------------


class TestVRSDebateEvaluation:
    def test_evaluates_without_error(self):
        ev = ReasoningEvaluator("skill-vrs-debate")
        co = SimulatedSkillOutput(
            tool_sequence=["Bash", "Read", "Bash", "Read"],
            bskg_queries=[{"category": "query", "command": "alphaswarm query x"}],
        )
        result = ev.evaluate(co)
        assert isinstance(result, ScoreCard)


# ---------------------------------------------------------------------------
# Skill: vrs-tool-slither
# ---------------------------------------------------------------------------


class TestVRSToolSlitherEvaluation:
    def test_evaluates_without_error(self):
        ev = ReasoningEvaluator("skill-vrs-tool-slither")
        co = SimulatedSkillOutput(
            tool_sequence=["Bash", "Read"],
        )
        result = ev.evaluate(co)
        assert isinstance(result, ScoreCard)

    def test_tool_contract_category(self):
        contract = load_contract("skill-vrs-tool-slither")
        assert contract["category"] == "skill"


# ---------------------------------------------------------------------------
# Runner integration
# ---------------------------------------------------------------------------


class TestSkillRunnerIntegration:
    def test_runner_with_skill_contract(self):
        runner = EvaluationRunner()
        co = _good_investigation_output()
        result = runner.run("audit-test", "skill-vrs-audit", co)
        assert isinstance(result, EvaluationResult)
        assert result.run_mode == RunMode.SIMULATED
