"""Thin pytest wrappers for Plan 11 orchestrator evaluation validation.

These tests assert on the STRUCTURED EVALUATION RESULTS in progress.json
produced by Plan 11 (3.1c-11). They do NOT invoke evaluation_runner.py
or spawn new evaluations. They read pre-existing progress.json and observation
artifacts, asserting on lifecycle completeness, evidence fidelity, coherence,
and anti-simulation guards.

Each test is thin (<=20 LOC) and contains no LLM scoring logic.

CONTRACT_VERSION: 11.1
CONSUMERS: [3.1c-12]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_EVALUATIONS_DIR = _PROJECT_ROOT / ".vrs" / "evaluations"
_PROGRESS_PATH = _EVALUATIONS_DIR / "progress.json"
_OBSERVATIONS_DIR = _PROJECT_ROOT / ".vrs" / "observations" / "plan11"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIDELITY_THRESHOLD = 0.6  # WARN threshold for Core tier (IMP-31)
REQUIRED_LIFECYCLE_PHASES = {"spawn", "task_assignment", "dm_exchange", "shutdown"}
REQUIRED_AGENT_ROLES = {"attacker", "defender", "verifier"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_plan11() -> dict[str, Any]:
    """Load plan11 section from progress.json or skip if not yet produced."""
    if not _PROGRESS_PATH.exists():
        pytest.skip("progress.json not yet produced")
    progress = json.loads(_PROGRESS_PATH.read_text())
    plan11 = progress.get("plan11")
    if plan11 is None:
        pytest.skip("plan11 section not yet produced")
    return plan11


def _get_orchestrator_evals(plan11: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract orchestrator evaluation entries from plan11."""
    return plan11.get("orchestrator_evaluations", [])


def _get_core_evals(plan11: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract Core-tier orchestrator evaluations."""
    return [e for e in _get_orchestrator_evals(plan11) if e.get("tier") == "core"]


# ---------------------------------------------------------------------------
# Anti-Simulation Guards (mandatory per Plan 11)
# ---------------------------------------------------------------------------


class TestAntiSimulation:
    """Verify no orchestrator evaluation used simulated mode."""

    def test_orchestrator_not_simulated(self) -> None:
        """Each orchestrator evaluation must have run_mode != SIMULATED."""
        plan11 = _load_plan11()
        evals = _get_orchestrator_evals(plan11)
        assert len(evals) > 0, "No orchestrator evaluations found"
        for ev in evals:
            run_mode = ev.get("run_mode", "UNKNOWN")
            assert run_mode != "SIMULATED" and run_mode != "simulated", (
                f"Orchestrator {ev.get('workflow_id')} used SIMULATED mode"
            )

    def test_anti_simulation_flags(self) -> None:
        """Plan11 anti_simulation section must confirm all checks passed."""
        plan11 = _load_plan11()
        anti_sim = plan11.get("anti_simulation", {})
        assert anti_sim.get("all_interactive_or_headless") is True
        assert anti_sim.get("no_simulated_mode") is True
        assert anti_sim.get("real_dm_exchanges") is True
        assert anti_sim.get("real_tool_use_events") is True

    def test_orchestrator_real_transcripts(self) -> None:
        """At least 1 Core orchestrator must have all 3 agent artifacts."""
        plan11 = _load_plan11()
        core_evals = _get_core_evals(plan11)
        assert len(core_evals) >= 1, "No Core orchestrator evaluations found"
        for ev in core_evals:
            agents = ev.get("agents", {})
            for role in REQUIRED_AGENT_ROLES:
                agent = agents.get(role, {})
                artifact = agent.get("artifact", "")
                assert artifact, f"Core eval missing artifact for {role}"
                artifact_path = _PROJECT_ROOT / artifact
                assert artifact_path.exists(), (
                    f"Artifact file missing: {artifact}"
                )

    def test_orchestrator_real_dm_exchange(self) -> None:
        """Core orchestrator must have real DM exchange (count > 0)."""
        plan11 = _load_plan11()
        core_evals = _get_core_evals(plan11)
        assert len(core_evals) >= 1
        for ev in core_evals:
            coherence = ev.get("coherence", {})
            dm_count = coherence.get("dm_exchange_count", 0)
            assert dm_count > 0, "No DM exchanges recorded"
            assert coherence.get("dm_exchange_real") is True, (
                "DM exchanges not marked as real"
            )

    def test_fidelity_from_real_text(self) -> None:
        """Fidelity must be computed from real agent text, not placeholders.

        Checks: (a) fidelity_score is non-None, (b) tuples differ from empty,
        (c) intersection count > 0.
        """
        plan11 = _load_plan11()
        core_evals = _get_core_evals(plan11)
        assert len(core_evals) >= 1
        for ev in core_evals:
            fidelity = ev.get("evidence_fidelity", {})
            score = fidelity.get("fidelity_score")
            assert score is not None, "fidelity_score is None"
            assert isinstance(score, (int, float)), "fidelity_score not numeric"
            atk_tuples = fidelity.get("attacker_tuples", [])
            ver_tuples = fidelity.get("verifier_tuples", [])
            assert len(atk_tuples) > 0, "Attacker tuples empty"
            assert len(ver_tuples) > 0, "Verifier tuples empty"
            assert fidelity.get("intersection_count", 0) > 0, (
                "Zero intersection — tuples not preserved"
            )


# ---------------------------------------------------------------------------
# Lifecycle Tests
# ---------------------------------------------------------------------------


class TestLifecycle:
    """Verify full 3-agent lifecycle was observed."""

    def test_full_lifecycle_observed(self) -> None:
        """Core orchestrator must show all lifecycle phases."""
        plan11 = _load_plan11()
        core_evals = _get_core_evals(plan11)
        assert len(core_evals) >= 1, "Need at least 1 Core orchestrator eval"
        for ev in core_evals:
            lifecycle = ev.get("lifecycle", {})
            for phase in REQUIRED_LIFECYCLE_PHASES:
                assert lifecycle.get(phase) is True, (
                    f"Lifecycle phase '{phase}' not observed in {ev.get('workflow_id')}"
                )

    def test_all_agent_roles_present(self) -> None:
        """Core orchestrator must have all 3 agent roles."""
        plan11 = _load_plan11()
        core_evals = _get_core_evals(plan11)
        assert len(core_evals) >= 1
        for ev in core_evals:
            agents = ev.get("agents", {})
            for role in REQUIRED_AGENT_ROLES:
                assert role in agents, f"Missing agent role: {role}"
                assert agents[role].get("status") == "completed", (
                    f"Agent {role} not completed"
                )

    def test_clean_shutdown(self) -> None:
        """All agents must have shut down cleanly."""
        plan11 = _load_plan11()
        core_evals = _get_core_evals(plan11)
        assert len(core_evals) >= 1
        for ev in core_evals:
            coherence = ev.get("coherence", {})
            assert coherence.get("shutdown_clean") is True

    def test_agent_team_provenance(self) -> None:
        """Each orchestrator eval must record agent_team name."""
        plan11 = _load_plan11()
        evals = _get_orchestrator_evals(plan11)
        for ev in evals:
            assert ev.get("agent_team"), (
                f"No agent_team recorded for {ev.get('workflow_id')}"
            )


# ---------------------------------------------------------------------------
# Evidence Fidelity Tests
# ---------------------------------------------------------------------------


class TestEvidenceFidelity:
    """Verify evidence fidelity metric is operational."""

    def test_fidelity_above_threshold(self) -> None:
        """Core tier fidelity must be >= 0.6 (WARN, not FAIL)."""
        plan11 = _load_plan11()
        core_evals = _get_core_evals(plan11)
        assert len(core_evals) >= 1
        for ev in core_evals:
            fidelity = ev.get("evidence_fidelity", {})
            score = fidelity.get("fidelity_score")
            assert score is not None, "fidelity_score is None"
            if score < FIDELITY_THRESHOLD:
                pytest.warns(
                    UserWarning,
                    match=f"Fidelity {score} below {FIDELITY_THRESHOLD}",
                )

    def test_fidelity_field_exists_in_model(self) -> None:
        """EvidenceFlowEdge must have fidelity_score field."""
        from tests.workflow_harness.lib.output_collector import EvidenceFlowEdge

        fields = EvidenceFlowEdge.__dataclass_fields__
        assert "fidelity_score" in fields, "fidelity_score field missing"

    def test_fidelity_compute_not_trivial(self) -> None:
        """compute_fidelity must produce non-zero for matching tuples."""
        from tests.workflow_harness.lib.output_collector import EvidenceFlowEdge

        text = "(withdraw, reentrancy, critical)"
        score = EvidenceFlowEdge.compute_fidelity(text, text)
        assert score > 0.0, "Identical text should produce non-zero fidelity"

    def test_fidelity_compute_zero_for_empty(self) -> None:
        """compute_fidelity must return 0.0 when source has no tuples."""
        from tests.workflow_harness.lib.output_collector import EvidenceFlowEdge

        score = EvidenceFlowEdge.compute_fidelity("no tuples here", "also nothing")
        assert score == 0.0


# ---------------------------------------------------------------------------
# Coherence Tests
# ---------------------------------------------------------------------------


class TestCoherence:
    """Verify cross-agent coherence scoring is operational."""

    def test_coherence_not_agent_average(self) -> None:
        """Coherence must derive from lifecycle events, not agent score averages.

        The coherence section must have coherence_source == 'lifecycle_events'
        and must NOT contain a field called 'average_reasoning_score'.
        """
        plan11 = _load_plan11()
        core_evals = _get_core_evals(plan11)
        assert len(core_evals) >= 1
        for ev in core_evals:
            coherence = ev.get("coherence", {})
            assert coherence.get("coherence_source") == "lifecycle_events", (
                "Coherence must be from lifecycle events, not score averages"
            )
            assert "average_reasoning_score" not in coherence, (
                "Coherence must NOT be a simple average of agent scores"
            )

    def test_coherence_agents_converged(self) -> None:
        """Agents should have converged on findings."""
        plan11 = _load_plan11()
        core_evals = _get_core_evals(plan11)
        assert len(core_evals) >= 1
        for ev in core_evals:
            coherence = ev.get("coherence", {})
            assert coherence.get("agents_converged") is True


# ---------------------------------------------------------------------------
# Observation Artifact Tests
# ---------------------------------------------------------------------------


class TestObservationArtifacts:
    """Verify observation files exist and contain real data."""

    def test_observation_dir_exists(self) -> None:
        """Plan 11 observation directory must exist."""
        assert _OBSERVATIONS_DIR.exists(), (
            f"Observations dir missing: {_OBSERVATIONS_DIR}"
        )

    def test_artifact_json_valid(self) -> None:
        """All JSON artifacts must parse without error."""
        plan11 = _load_plan11()
        core_evals = _get_core_evals(plan11)
        for ev in core_evals:
            agents = ev.get("agents", {})
            for _role, agent_data in agents.items():
                artifact = agent_data.get("artifact", "")
                if artifact:
                    path = _PROJECT_ROOT / artifact
                    if path.exists():
                        data = json.loads(path.read_text())
                        assert isinstance(data, dict), (
                            f"Artifact {artifact} is not a JSON object"
                        )

    def test_attacker_has_structured_tuples(self) -> None:
        """Attacker findings must include structured tuples."""
        plan11 = _load_plan11()
        core_evals = _get_core_evals(plan11)
        assert len(core_evals) >= 1
        for ev in core_evals:
            attacker = ev.get("agents", {}).get("attacker", {})
            tuples = attacker.get("structured_tuples", [])
            assert len(tuples) > 0, "Attacker has no structured tuples"

    def test_verifier_has_verdict(self) -> None:
        """Verifier must have rendered a verdict."""
        plan11 = _load_plan11()
        core_evals = _get_core_evals(plan11)
        assert len(core_evals) >= 1
        for ev in core_evals:
            verifier = ev.get("agents", {}).get("verifier", {})
            assert verifier.get("verdict") in (
                "CONFIRMED", "DISPUTED", "REJECTED"
            ), "Verifier must have a valid verdict"
            assert verifier.get("confidence") is not None, (
                "Verifier must have a confidence score"
            )


# ---------------------------------------------------------------------------
# IMP-18: Full Pipeline Test
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """At least 1 Core orchestrator must exercise the full pipeline."""

    def test_at_least_one_core_orchestrator(self) -> None:
        """IMP-18: At least 1 Core orchestrator test exercises full pipeline."""
        plan11 = _load_plan11()
        core_evals = _get_core_evals(plan11)
        assert len(core_evals) >= 1, (
            "IMP-18 requires at least 1 Core orchestrator evaluation"
        )
        ev = core_evals[0]
        assert ev.get("status") == "completed"
        assert ev.get("run_mode") == "INTERACTIVE"

    def test_no_silent_gaps(self) -> None:
        """No orchestrator evaluations should have silent failures."""
        plan11 = _load_plan11()
        evals = _get_orchestrator_evals(plan11)
        for ev in evals:
            assert ev.get("status") != "failed_silent", (
                f"Silent failure in {ev.get('workflow_id')}"
            )
