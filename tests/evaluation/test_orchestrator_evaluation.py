"""Tests for 3.1c-11 Orchestrator Evaluation.

Integration tests that evaluate orchestrator workflows using the full pipeline.

Orchestrators tested (from Core-tier contracts):
- full-audit (orchestrator-full-audit)
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
# Fixtures
# ---------------------------------------------------------------------------


@dataclass
class SimulatedOrchestratorOutput:
    tool_sequence: list[str] = field(default_factory=list)
    bskg_queries: list[dict[str, Any]] = field(default_factory=list)
    transcript: Any = None
    team_observation: Any = None


def _full_audit_output() -> SimulatedOrchestratorOutput:
    """Simulated full audit orchestration output."""
    return SimulatedOrchestratorOutput(
        tool_sequence=[
            "Bash", "Bash",  # Build KG
            "Read", "Read",  # Read contracts
            "Bash",          # Run attacker
            "Bash",          # Run defender
            "Bash",          # Run verifier
            "Write",         # Write report
        ],
        bskg_queries=[
            {"category": "build-kg", "command": "alphaswarm build-kg contracts/"},
            {"category": "query", "command": "alphaswarm query 'vulnerabilities'"},
            {"category": "analyze", "command": "alphaswarm analyze all"},
        ],
    )


# ---------------------------------------------------------------------------
# Orchestrator: full-audit
# ---------------------------------------------------------------------------


class TestFullAuditEvaluation:
    def test_evaluates_without_error(self):
        ev = ReasoningEvaluator("orchestrator-full-audit")
        co = _full_audit_output()
        result = ev.evaluate(co)
        assert isinstance(result, ScoreCard)

    def test_contract_exists_and_is_orchestrator(self):
        contract = load_contract("orchestrator-full-audit")
        assert contract["category"] == "orchestrator"

    def test_good_orchestration_outscores_minimal(self):
        ev = ReasoningEvaluator("orchestrator-full-audit")
        good = _full_audit_output()
        bad = SimulatedOrchestratorOutput(tool_sequence=["Read"])

        good_result = ev.evaluate(good)
        bad_result = ev.evaluate(bad)
        assert good_result.overall_score > bad_result.overall_score

    def test_orchestrator_contract_has_dimensions(self):
        contract = load_contract("orchestrator-full-audit")
        assert len(contract.get("reasoning_dimensions", [])) > 0

    def test_orchestrator_contract_has_evidence_requirements(self):
        contract = load_contract("orchestrator-full-audit")
        assert len(contract.get("evidence_requirements", [])) > 0


# ---------------------------------------------------------------------------
# Runner integration
# ---------------------------------------------------------------------------


class TestOrchestratorRunnerIntegration:
    def test_runner_with_orchestrator_contract(self):
        runner = EvaluationRunner()
        co = _full_audit_output()
        result = runner.run("audit-orch-test", "orchestrator-full-audit", co)
        assert isinstance(result, EvaluationResult)
        assert result.workflow_id == "orchestrator-full-audit"

    def test_batch_evaluation_across_contracts(self):
        runner = EvaluationRunner()
        scenarios = [
            {
                "scenario_name": "skill-test",
                "workflow_id": "skill-vrs-audit",
                "collected_output": SimulatedOrchestratorOutput(
                    tool_sequence=["Bash", "Read"],
                    bskg_queries=[{"category": "build-kg", "command": "x"}],
                ),
            },
            {
                "scenario_name": "agent-test",
                "workflow_id": "agent-vrs-attacker",
                "collected_output": SimulatedOrchestratorOutput(
                    tool_sequence=["Bash", "Read"],
                    bskg_queries=[{"category": "query", "command": "y"}],
                ),
            },
            {
                "scenario_name": "orch-test",
                "workflow_id": "orchestrator-full-audit",
                "collected_output": _full_audit_output(),
            },
        ]
        results = runner.run_batch(scenarios)
        assert len(results) == 3
        assert all(isinstance(r, EvaluationResult) for r in results)
