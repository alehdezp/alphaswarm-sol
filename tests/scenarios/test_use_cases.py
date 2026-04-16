"""Use Case Scenario tests -- validate and evaluate scenario YAML files.

Each scenario is parametrized via conftest.py and identified by its ID
(e.g., test_use_cases[UC-AUDIT-001]).

In simulated mode (default), tests validate YAML structure and run the
evaluation pipeline with synthetic data. In headless mode, tests would
execute against real Claude Code sessions (not yet implemented).

Usage:
    pytest tests/scenarios/test_use_cases.py -v
    pytest tests/scenarios/test_use_cases.py -k "UC-AUDIT-001"
    pytest tests/scenarios/test_use_cases.py -k "core"
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Validation constants (mirrored from conftest for independence)
# ---------------------------------------------------------------------------

ID_PATTERN = re.compile(r"^UC-[A-Z]+-\d{3}$")

VALID_WORKFLOWS = {
    "vrs-audit", "vrs-investigate", "vrs-verify", "vrs-debate",
    "vrs-attacker", "vrs-defender", "vrs-health-check",
    "graph-build", "tool-run", "failure",
}

VALID_CATEGORIES = {
    "audit", "investigate", "verify", "debate", "agents",
    "tools", "graph", "failure", "cross-workflow",
}

VALID_TIERS = {"core", "important", "mechanical"}
VALID_STATUSES = {"draft", "ready", "validated", "broken"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_structure(scenario: dict[str, Any]) -> list[str]:
    """Validate the structural correctness of a scenario dict.

    Returns a list of error strings. Empty list means valid.
    """
    errors: list[str] = []

    # Check for load errors
    if "_load_error" in scenario:
        return [f"Failed to load YAML: {scenario['_load_error']}"]

    # id
    sid = scenario.get("id", "")
    if not sid:
        errors.append("Missing required field: id")
    elif not ID_PATTERN.match(sid):
        errors.append(f"id '{sid}' does not match UC-[A-Z]+-NNN")

    # name
    if not scenario.get("name"):
        errors.append("Missing required field: name")

    # workflow
    wf = scenario.get("workflow", "")
    if not wf:
        errors.append("Missing required field: workflow")
    elif wf not in VALID_WORKFLOWS:
        errors.append(f"Invalid workflow: {wf}")

    # category
    cat = scenario.get("category", "")
    if not cat:
        errors.append("Missing required field: category")
    elif cat not in VALID_CATEGORIES:
        errors.append(f"Invalid category: {cat}")

    # tier
    tier = scenario.get("tier", "")
    if not tier:
        errors.append("Missing required field: tier")
    elif tier not in VALID_TIERS:
        errors.append(f"Invalid tier: {tier}")

    # status
    status = scenario.get("status", "")
    if not status:
        errors.append("Missing required field: status")
    elif status not in VALID_STATUSES:
        errors.append(f"Invalid status: {status}")

    # input
    inp = scenario.get("input")
    if not inp:
        errors.append("Missing required field: input")
    elif isinstance(inp, dict):
        for field in ("contract", "command", "context"):
            if not inp.get(field):
                errors.append(f"Missing required field: input.{field}")

    # expected_behavior
    eb = scenario.get("expected_behavior")
    if not eb:
        errors.append("Missing required field: expected_behavior")
    elif isinstance(eb, dict):
        if not eb.get("summary"):
            errors.append("Missing: expected_behavior.summary")
        for lf in ("must_happen", "must_not_happen"):
            val = eb.get(lf)
            if not val:
                errors.append(f"Missing or empty: expected_behavior.{lf}")
            elif not isinstance(val, list) or len(val) == 0:
                errors.append(f"expected_behavior.{lf} must be a non-empty list")

    # evaluation
    ev = scenario.get("evaluation")
    if not ev:
        errors.append("Missing required field: evaluation")
    elif isinstance(ev, dict):
        pt = ev.get("pass_threshold")
        if pt is None:
            errors.append("Missing: evaluation.pass_threshold")
        elif not isinstance(pt, int) or not (0 <= pt <= 100):
            errors.append(f"evaluation.pass_threshold must be int 0-100, got {pt}")
        kd = ev.get("key_dimensions")
        if not kd or not isinstance(kd, list) or len(kd) == 0:
            errors.append("evaluation.key_dimensions must be a non-empty list")
        rs = ev.get("regression_signals")
        if not rs or not isinstance(rs, list) or len(rs) == 0:
            errors.append("evaluation.regression_signals must be a non-empty list")

    return errors


def _build_simulated_feedback(scenario: dict[str, Any]) -> dict[str, Any]:
    """Build structured feedback for a scenario in simulated mode.

    In simulated mode, we cannot actually run the workflow. Instead we
    validate the scenario specification quality and produce feedback
    about what would be tested.
    """
    eb = scenario.get("expected_behavior", {})
    ev = scenario.get("evaluation", {})
    links = scenario.get("links", {})

    feedback: dict[str, Any] = {
        "scenario_id": scenario.get("id", "UNKNOWN"),
        "scenario_name": scenario.get("name", "UNKNOWN"),
        "mode": "simulated",
        "structure_valid": True,
        "checks": {},
        "suggestions": [],
    }

    # Check must_happen specificity
    must_happen = eb.get("must_happen", [])
    vague_items = [
        item for item in must_happen
        if len(item.split()) < 4 or item.lower().startswith("should")
    ]
    if vague_items:
        feedback["suggestions"].append(
            f"Some must_happen items may be too vague: {vague_items}"
        )
    feedback["checks"]["must_happen_count"] = len(must_happen)
    feedback["checks"]["must_happen_specific"] = len(must_happen) - len(vague_items)

    # Check must_not_happen coverage
    must_not_happen = eb.get("must_not_happen", [])
    feedback["checks"]["must_not_happen_count"] = len(must_not_happen)

    # Check dimension coverage
    dims = ev.get("key_dimensions", [])
    feedback["checks"]["dimension_count"] = len(dims)

    # Check if graph_utilization dimension is present (mandatory for graph-first)
    has_graph_dim = any(
        "graph" in d.get("name", "").lower()
        for d in dims
    )
    if scenario.get("workflow") not in ("failure",) and not has_graph_dim:
        feedback["suggestions"].append(
            "Missing graph_utilization dimension -- graph-first workflows "
            "should evaluate BSKG query usage"
        )

    # Check regression signal quality
    signals = ev.get("regression_signals", [])
    has_critical = any("CRITICAL" in s for s in signals)
    if not has_critical:
        feedback["suggestions"].append(
            "No CRITICAL regression signal defined -- consider adding one "
            "for the most important invariant"
        )
    feedback["checks"]["regression_signal_count"] = len(signals)
    feedback["checks"]["has_critical_signal"] = has_critical

    # Check links
    feedback["checks"]["has_workflow_doc"] = bool(links.get("workflow_doc"))
    feedback["checks"]["has_evaluation_contract"] = bool(links.get("evaluation_contract"))
    feedback["checks"]["has_test_contract"] = bool(links.get("test_contract"))
    feedback["checks"]["related_scenario_count"] = len(links.get("related_scenarios", []))

    return feedback


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUseCaseScenarios:
    """Parametrized test suite for use case scenarios."""

    def test_scenario_structure(self, scenario: dict[str, Any]) -> None:
        """Validate the YAML structure of the scenario.

        Checks all required fields, valid enum values, and ID format.
        This test runs for every scenario discovered by conftest.
        """
        errors = _validate_structure(scenario)
        if errors:
            error_msg = "\n".join(f"  - {e}" for e in errors)
            pytest.fail(
                f"Scenario {scenario.get('id', 'UNKNOWN')} has structural errors:\n{error_msg}"
            )

    def test_scenario_simulated_evaluation(self, scenario: dict[str, Any]) -> None:
        """Run the scenario through simulated evaluation.

        In simulated mode, validates specification quality and produces
        structured feedback about what would be tested in a real run.
        """
        # Skip if load error
        if "_load_error" in scenario:
            pytest.skip(f"Load error: {scenario['_load_error']}")

        feedback = _build_simulated_feedback(scenario)

        # Assertions on specification quality
        assert feedback["structure_valid"], "Structure validation failed"

        checks = feedback["checks"]

        # must_happen should have enough items
        assert checks["must_happen_count"] >= 3, (
            f"Scenario {scenario['id']} has only {checks['must_happen_count']} "
            f"must_happen items (minimum 3 for meaningful coverage)"
        )

        # must_not_happen should have at least 2 items
        assert checks["must_not_happen_count"] >= 2, (
            f"Scenario {scenario['id']} has only {checks['must_not_happen_count']} "
            f"must_not_happen items (minimum 2)"
        )

        # At least 2 evaluation dimensions
        assert checks["dimension_count"] >= 2, (
            f"Scenario {scenario['id']} has only {checks['dimension_count']} "
            f"evaluation dimensions (minimum 2)"
        )

        # At least 1 regression signal
        assert checks["regression_signal_count"] >= 1, (
            f"Scenario {scenario['id']} has no regression signals"
        )

    def test_scenario_id_matches_filename(self, scenario: dict[str, Any]) -> None:
        """Verify the scenario ID matches the filename convention.

        File UC-AUDIT-001-simple-reentrancy.yaml should have id: UC-AUDIT-001.
        """
        if "_load_error" in scenario:
            pytest.skip(f"Load error: {scenario['_load_error']}")

        filepath = Path(scenario.get("_filepath", ""))
        scenario_id = scenario.get("id", "")

        if not filepath.name or not scenario_id:
            pytest.skip("Missing filepath or id")

        # Extract ID from filename: UC-AUDIT-001 from UC-AUDIT-001-foo.yaml
        filename_stem = filepath.stem
        # Match the ID pattern at the start of the filename
        match = re.match(r"^(UC-[A-Z]+-\d{3})", filename_stem)
        if match:
            filename_id = match.group(1)
            assert scenario_id == filename_id, (
                f"Scenario id '{scenario_id}' does not match filename "
                f"'{filepath.name}' (expected {filename_id})"
            )

    def test_scenario_evaluation_model_construction(
        self, scenario: dict[str, Any], project_root: Path
    ) -> None:
        """Test that the scenario config can construct evaluation models.

        Verifies that EvaluationInput and ScoreCard can be created from
        the scenario's configuration. Does NOT run the actual evaluation
        pipeline — that requires real workflow execution.
        """
        if "_load_error" in scenario:
            pytest.skip(f"Load error: {scenario['_load_error']}")

        # Try to import evaluation infrastructure
        try:
            from alphaswarm_sol.testing.evaluation.models import (
                EvaluationInput,
                RunMode,
                ScoreCard,
            )
        except ImportError as e:
            pytest.skip(f"Evaluation models not available: {e}")

        # Build a minimal EvaluationInput from the scenario
        scenario_id = scenario.get("id", "UNKNOWN")
        workflow = scenario.get("workflow", "unknown")
        ev = scenario.get("evaluation", {})
        pass_threshold = ev.get("pass_threshold", 60)

        eval_input = EvaluationInput(
            scenario_name=scenario_id,
            run_id=f"simulated-{scenario_id}",
            run_mode=RunMode.SIMULATED,
        )

        # Verify the EvaluationInput was constructed correctly
        assert eval_input.scenario_name == scenario_id
        assert eval_input.run_mode == RunMode.SIMULATED

        # Check if we can construct a ScoreCard with the scenario's threshold
        score_card = ScoreCard(
            workflow_id=workflow,
            overall_score=0,
            passed=False,
            pass_threshold=pass_threshold,
        )
        assert score_card.pass_threshold == pass_threshold
        assert not score_card.passed
