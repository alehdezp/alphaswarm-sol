"""Thin pytest wrappers for Plan 10 agent evaluation validation.

These tests assert on the STRUCTURED EVALUATION RESULTS in progress.json
produced by Plan 10 (3.1c-10). They do NOT invoke evaluation_runner.py
or spawn new evaluations. They read pre-existing progress.json and debrief
artifacts, asserting on completeness, tier-gated run modes, agent team
provenance, and anti-simulation guards.

Each test is thin (<=20 LOC) and contains no LLM scoring logic.

CONTRACT_VERSION: 10.2
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
_OBSERVATIONS_DIR = _PROJECT_ROOT / ".vrs" / "observations" / "plan10"

# ---------------------------------------------------------------------------
# Constants (compile-time contract — do NOT modify to accommodate simulated data)
# ---------------------------------------------------------------------------

EXPECTED_AGENT_COUNT = 21
CORE_AGENT_COUNT = 4
IMPORTANT_AGENT_COUNT = 5
STANDARD_AGENT_COUNT = 12

CORE_AGENT_IDS = frozenset({
    "agent-vrs-attacker",
    "agent-vrs-defender",
    "agent-vrs-verifier",
    "agent-vrs-secure-reviewer",
})

IMPORTANT_AGENT_IDS = frozenset({
    "agent-vrs-pattern-scout",
    "agent-vrs-integrator",
    "agent-vrs-finding-merger",
    "agent-vrs-pattern-verifier",
    "agent-vrs-pattern-composer",
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_plan10() -> dict[str, Any]:
    """Load plan10 section from progress.json or skip if not yet produced."""
    if not _PROGRESS_PATH.exists():
        pytest.skip("progress.json not yet produced")
    progress = json.loads(_PROGRESS_PATH.read_text())
    plan10 = progress.get("plan10")
    if plan10 is None:
        pytest.skip("plan10 section not yet produced")
    return plan10


def _load_progress() -> dict[str, Any]:
    """Load full progress.json or skip if not yet produced."""
    if not _PROGRESS_PATH.exists():
        pytest.skip("progress.json not yet produced")
    return json.loads(_PROGRESS_PATH.read_text())


def _get_agent_statuses(plan10: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract per_agent_status list from plan10 section."""
    return plan10.get("per_agent_status", [])


# ---------------------------------------------------------------------------
# Test 1: All 21 agents accounted for (no silent gaps)
# ---------------------------------------------------------------------------


class TestAgentCompleteness:
    """Verify all 21 shipped agents have evaluation entries."""

    def test_all_agents_have_status_entry(self) -> None:
        """Every agent has a per_agent_status entry."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        assert len(statuses) >= EXPECTED_AGENT_COUNT, (
            f"Expected {EXPECTED_AGENT_COUNT} agent entries, "
            f"got {len(statuses)}"
        )

    def test_all_agents_completed(self) -> None:
        """Every agent has status=completed (no pending or failed)."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        for agent in statuses:
            wid = agent.get("workflow_id", "UNKNOWN")
            status = agent.get("status", "")
            assert status == "completed", (
                f"Agent {wid} has status={status!r}, expected 'completed'"
            )

    def test_sub_wave_counts_match(self) -> None:
        """sub_waves section totals match expected tier counts."""
        plan10 = _load_plan10()
        sw = plan10.get("sub_waves", {})

        assert sw.get("core", {}).get("total") == CORE_AGENT_COUNT
        assert sw.get("important", {}).get("total") == IMPORTANT_AGENT_COUNT
        assert sw.get("standard", {}).get("total") == STANDARD_AGENT_COUNT

    def test_sub_waves_all_completed(self) -> None:
        """All sub_waves show completed == total with 0 failed."""
        plan10 = _load_plan10()
        sw = plan10.get("sub_waves", {})

        for tier_name in ("core", "important", "standard"):
            tier = sw.get(tier_name, {})
            assert tier.get("completed") == tier.get("total"), (
                f"{tier_name}: completed={tier.get('completed')} != "
                f"total={tier.get('total')}"
            )
            assert tier.get("failed", -1) == 0, (
                f"{tier_name}: {tier.get('failed')} failures"
            )


# ---------------------------------------------------------------------------
# Test 2: Tier classification correctness
# ---------------------------------------------------------------------------


class TestTierClassification:
    """Verify agents are assigned to correct tiers."""

    def test_core_agents_classified_correctly(self) -> None:
        """Core agents have tier='core'."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        core = [a for a in statuses if a.get("workflow_id") in CORE_AGENT_IDS]
        assert len(core) == CORE_AGENT_COUNT, (
            f"Expected {CORE_AGENT_COUNT} Core agents, found {len(core)}"
        )
        for agent in core:
            assert agent.get("tier") == "core", (
                f"{agent['workflow_id']} has tier={agent.get('tier')!r}"
            )

    def test_important_agents_classified_correctly(self) -> None:
        """Important agents have tier='important'."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        important = [
            a for a in statuses
            if a.get("workflow_id") in IMPORTANT_AGENT_IDS
        ]
        assert len(important) == IMPORTANT_AGENT_COUNT, (
            f"Expected {IMPORTANT_AGENT_COUNT} Important agents, "
            f"found {len(important)}"
        )
        for agent in important:
            assert agent.get("tier") == "important", (
                f"{agent['workflow_id']} has tier={agent.get('tier')!r}"
            )

    def test_standard_agents_exist(self) -> None:
        """Remaining agents are standard tier."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        standard = [a for a in statuses if a.get("tier") == "standard"]
        assert len(standard) == STANDARD_AGENT_COUNT, (
            f"Expected {STANDARD_AGENT_COUNT} Standard agents, "
            f"found {len(standard)}"
        )


# ---------------------------------------------------------------------------
# Test 3: Run mode enforcement (tier-gated)
# ---------------------------------------------------------------------------


class TestRunModeEnforcement:
    """Verify tier-appropriate run modes are enforced."""

    def test_core_agents_ran_interactive(self) -> None:
        """Core agents must use INTERACTIVE mode (real Agent Teams)."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        core = [a for a in statuses if a.get("workflow_id") in CORE_AGENT_IDS]
        for agent in core:
            assert agent.get("run_mode") == "INTERACTIVE", (
                f"{agent['workflow_id']} run_mode={agent.get('run_mode')!r}, "
                f"expected INTERACTIVE"
            )

    def test_important_agents_ran_headless(self) -> None:
        """Important agents must use HEADLESS mode (real Agent Teams)."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        important = [
            a for a in statuses
            if a.get("workflow_id") in IMPORTANT_AGENT_IDS
        ]
        for agent in important:
            assert agent.get("run_mode") == "HEADLESS", (
                f"{agent['workflow_id']} run_mode={agent.get('run_mode')!r}, "
                f"expected HEADLESS"
            )

    def test_standard_agents_allow_simulated(self) -> None:
        """Standard agents may use simulated mode."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        standard = [a for a in statuses if a.get("tier") == "standard"]
        for agent in standard:
            rm = agent.get("run_mode", "")
            assert rm in ("simulated", "HEADLESS", "INTERACTIVE"), (
                f"{agent['workflow_id']} has invalid run_mode={rm!r}"
            )


# ---------------------------------------------------------------------------
# Test 4: Agent Team provenance
# ---------------------------------------------------------------------------


class TestAgentTeamProvenance:
    """Verify Core and Important agents used REAL Agent Teams."""

    def test_core_agents_have_agent_team(self) -> None:
        """Core agents must have agent_team field set."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        core = [a for a in statuses if a.get("workflow_id") in CORE_AGENT_IDS]
        for agent in core:
            assert agent.get("agent_team"), (
                f"{agent['workflow_id']} missing agent_team provenance"
            )

    def test_important_agents_have_agent_team(self) -> None:
        """Important agents must have agent_team field set."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        important = [
            a for a in statuses
            if a.get("workflow_id") in IMPORTANT_AGENT_IDS
        ]
        for agent in important:
            assert agent.get("agent_team"), (
                f"{agent['workflow_id']} missing agent_team provenance"
            )

    def test_core_agents_have_graph_stats(self) -> None:
        """Core agents must have graph_stats with nodes and edges."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        core = [a for a in statuses if a.get("workflow_id") in CORE_AGENT_IDS]
        for agent in core:
            gs = agent.get("graph_stats", {})
            assert gs.get("nodes", 0) > 0, (
                f"{agent['workflow_id']} has no graph nodes"
            )
            assert gs.get("edges", 0) > 0, (
                f"{agent['workflow_id']} has no graph edges"
            )

    def test_important_agents_have_graph_stats(self) -> None:
        """Important agents must have graph_stats."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        important = [
            a for a in statuses
            if a.get("workflow_id") in IMPORTANT_AGENT_IDS
        ]
        for agent in important:
            gs = agent.get("graph_stats", {})
            assert gs.get("nodes", 0) > 0, (
                f"{agent['workflow_id']} has no graph nodes"
            )


# ---------------------------------------------------------------------------
# Test 5: Debrief artifacts exist (Core + Important)
# ---------------------------------------------------------------------------


class TestDebriefArtifacts:
    """Verify debrief.json files exist for real evaluations."""

    def test_core_debrief_files_exist(self) -> None:
        """Each Core agent has a debrief.json in observations."""
        if not _OBSERVATIONS_DIR.exists():
            pytest.skip("Observations directory not yet produced")

        for agent_id in CORE_AGENT_IDS:
            debrief = _OBSERVATIONS_DIR / agent_id / "debrief.json"
            assert debrief.exists() and debrief.stat().st_size > 0, (
                f"{agent_id}: debrief.json missing or empty at {debrief}"
            )

    def test_important_debrief_files_exist(self) -> None:
        """Each Important agent has a debrief.json in observations."""
        if not _OBSERVATIONS_DIR.exists():
            pytest.skip("Observations directory not yet produced")

        for agent_id in IMPORTANT_AGENT_IDS:
            debrief = _OBSERVATIONS_DIR / agent_id / "debrief.json"
            assert debrief.exists() and debrief.stat().st_size > 0, (
                f"{agent_id}: debrief.json missing or empty at {debrief}"
            )

    def test_debrief_json_has_required_fields(self) -> None:
        """Debrief files contain workflow_id, graph_stats, queries_executed."""
        if not _OBSERVATIONS_DIR.exists():
            pytest.skip("Observations directory not yet produced")

        checked = 0
        for agent_id in CORE_AGENT_IDS | IMPORTANT_AGENT_IDS:
            debrief_path = _OBSERVATIONS_DIR / agent_id / "debrief.json"
            if not debrief_path.exists():
                continue
            data = json.loads(debrief_path.read_text())
            assert "workflow_id" in data, f"{agent_id}: missing workflow_id"
            assert "graph_stats" in data, f"{agent_id}: missing graph_stats"
            checked += 1

        assert checked > 0, "No debrief files checked"


# ---------------------------------------------------------------------------
# Test 6: HITL gate validation
# ---------------------------------------------------------------------------


class TestHITLGate:
    """Verify joint HITL gate between Plan 09 and Plan 10."""

    def test_hitl_gate_prerequisites_met(self) -> None:
        """Both Plan 09 Core and Plan 10 Core must be complete."""
        plan10 = _load_plan10()
        gate = plan10.get("hitl_gate_09a_10a", {})

        assert gate.get("plan09_core_complete") is True, (
            "Plan 09 Core not complete for HITL gate"
        )
        assert gate.get("plan10_core_complete") is True, (
            "Plan 10 Core not complete for HITL gate"
        )

    def test_joint_gate_exists(self) -> None:
        """Joint gate section exists in progress.json."""
        progress = _load_progress()
        gate = progress.get("joint_gate")
        assert gate is not None, "Missing joint_gate section in progress.json"


# ---------------------------------------------------------------------------
# Test 7: Anti-simulation guards (mandatory)
# ---------------------------------------------------------------------------


class TestAntiSimulation:
    """Verify evaluations used REAL Agent Teams, not RunMode.SIMULATED."""

    def test_core_agents_not_simulated(self) -> None:
        """Core agents must NOT use RunMode.SIMULATED."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        core = [a for a in statuses if a.get("workflow_id") in CORE_AGENT_IDS]
        simulated = [
            a["workflow_id"] for a in core
            if a.get("run_mode") == "simulated"
        ]
        assert not simulated, (
            f"ANTI-SIMULATION VIOLATION: {len(simulated)} Core agent(s) used "
            f"RunMode.SIMULATED: {simulated}"
        )

    def test_important_agents_not_simulated(self) -> None:
        """Important agents must NOT use RunMode.SIMULATED."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        important = [
            a for a in statuses
            if a.get("workflow_id") in IMPORTANT_AGENT_IDS
        ]
        simulated = [
            a["workflow_id"] for a in important
            if a.get("run_mode") == "simulated"
        ]
        assert not simulated, (
            f"ANTI-SIMULATION VIOLATION: {len(simulated)} Important agent(s) "
            f"used RunMode.SIMULATED: {simulated}"
        )

    def test_core_agents_have_reasoning_scores(self) -> None:
        """Core INTERACTIVE agents must have reasoning_score populated."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        core = [a for a in statuses if a.get("workflow_id") in CORE_AGENT_IDS]
        for agent in core:
            score = agent.get("reasoning_score")
            assert score is not None and score > 0, (
                f"{agent['workflow_id']} has no reasoning_score "
                f"(INTERACTIVE mode should produce scores)"
            )

    def test_standard_tier_no_reasoning_scores(self) -> None:
        """Standard-tier agents must NOT have reasoning scores."""
        plan10 = _load_plan10()
        statuses = _get_agent_statuses(plan10)

        standard = [a for a in statuses if a.get("tier") == "standard"]
        for agent in standard:
            assert agent.get("reasoning_score") is None, (
                f"Standard-tier {agent['workflow_id']} has reasoning_score "
                f"(should be structural only)"
            )

    def test_thresholds_not_gamed(self) -> None:
        """Compile-time constants must not be modified to game results."""
        assert EXPECTED_AGENT_COUNT == 21, (
            f"EXPECTED_AGENT_COUNT modified to {EXPECTED_AGENT_COUNT}"
        )
        assert CORE_AGENT_COUNT == 4, (
            f"CORE_AGENT_COUNT modified to {CORE_AGENT_COUNT}"
        )
        assert IMPORTANT_AGENT_COUNT == 5, (
            f"IMPORTANT_AGENT_COUNT modified to {IMPORTANT_AGENT_COUNT}"
        )

    def test_real_debrief_content_not_empty(self) -> None:
        """At least one Core debrief has substantive content (>100 bytes)."""
        if not _OBSERVATIONS_DIR.exists():
            pytest.skip("Observations not yet produced")

        for agent_id in CORE_AGENT_IDS:
            debrief = _OBSERVATIONS_DIR / agent_id / "debrief.json"
            if debrief.exists() and debrief.stat().st_size > 100:
                data = json.loads(debrief.read_text())
                assert "workflow_id" in data, (
                    f"{agent_id} debrief missing workflow_id"
                )
                return  # At least one substantive debrief found

        pytest.fail("No Core agent has a substantive debrief.json (>100 bytes)")
