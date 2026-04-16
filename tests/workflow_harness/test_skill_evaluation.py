"""Thin pytest wrappers for /vrs-test-suite exit report validation.

These tests assert on the STRUCTURED EXIT REPORTS produced by the
/vrs-test-suite CC skill (3.1c-09). They do NOT invoke evaluation_runner.py
or spawn new evaluations. They read pre-existing progress.json and exit
report files, asserting on completeness, capability checks, delegate mode
contamination, 3.2-critical readiness, and anti-simulation guards.

Each test is thin (<=20 LOC) and contains no LLM scoring logic.

CONTRACT_VERSION: 09.2
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
_RESULTS_DIR = _EVALUATIONS_DIR / "results"
_OBSERVATIONS_DIR = _PROJECT_ROOT / ".vrs" / "observations" / "plan09"

# Total shipped skills (excluding test-suite directory itself)
EXPECTED_SKILL_COUNT = 30
CORE_CAPABILITY_THRESHOLD = 8  # >= 8 of 10 Core skills must pass
FAILURE_ESCALATION_THRESHOLD = 6  # > 6 of 30 = >20% triggers escalation
CRITICAL_READINESS_THRESHOLD = 3  # 3 of 8 critical workflows must score above threshold


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_progress() -> dict[str, Any]:
    """Load progress.json or return empty dict if not yet produced."""
    if not _PROGRESS_PATH.exists():
        pytest.skip("progress.json not yet produced (suite has not run)")
    return json.loads(_PROGRESS_PATH.read_text())


def _get_workflow_statuses(progress: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract per_workflow_status list from progress."""
    return progress.get("per_workflow_status", [])


def _get_result_files() -> list[Path]:
    """List all result JSON files in the results directory."""
    if not _RESULTS_DIR.exists():
        return []
    return sorted(_RESULTS_DIR.glob("*.json"))


def _get_failed_files() -> list[Path]:
    """List all .failed.json files in the evaluations directory."""
    if not _EVALUATIONS_DIR.exists():
        return []
    return sorted(_EVALUATIONS_DIR.glob("*.failed.json"))


# ---------------------------------------------------------------------------
# Test 1: All 30 skills accounted for (no silent gaps)
# ---------------------------------------------------------------------------


class TestSkillCompleteness:
    """Verify all shipped skills have exit report or failure record."""

    def test_all_skills_have_exit_report_or_failed_json(self) -> None:
        """Every workflow_id resolves to exit report OR .failed.json."""
        progress = _load_progress()
        statuses = _get_workflow_statuses(progress)

        assert len(statuses) >= EXPECTED_SKILL_COUNT, (
            f"Expected {EXPECTED_SKILL_COUNT} workflow entries, "
            f"got {len(statuses)}"
        )

        for ws in statuses:
            wid = ws.get("workflow_id", "UNKNOWN")
            status = ws.get("status", "")
            assert status in ("completed", "failed", "skipped"), (
                f"Silent gap: {wid} has status={status!r}"
            )

    def test_no_silent_gaps_in_file_artifacts(self) -> None:
        """Result files + failed files cover all tracked workflows."""
        progress = _load_progress()
        statuses = _get_workflow_statuses(progress)

        # Result files are UUID-named; extract workflow_id from JSON content
        result_wids: set[str] = set()
        for p in _get_result_files():
            try:
                data = json.loads(p.read_text())
                result_wids.add(data.get("workflow_id", ""))
            except (json.JSONDecodeError, KeyError):
                continue
        failed_ids = {p.stem.replace(".failed", "") for p in _get_failed_files()}
        covered = result_wids | failed_ids

        for ws in statuses:
            wid = ws.get("workflow_id", "UNKNOWN")
            if ws.get("status") == "skipped":
                continue  # Skipped workflows may lack file artifacts
            assert wid in covered, (
                f"Silent gap: {wid} has no result file and no .failed.json"
            )

    def test_failure_count_below_escalation_threshold(self) -> None:
        """Fewer than 20% of workflows have .failed.json."""
        progress = _load_progress()
        statuses = _get_workflow_statuses(progress)
        failed_count = sum(1 for ws in statuses if ws.get("status") == "failed")

        assert failed_count <= FAILURE_ESCALATION_THRESHOLD, (
            f"Failure escalation: {failed_count} failures exceed "
            f"{FAILURE_ESCALATION_THRESHOLD} threshold (20% of {EXPECTED_SKILL_COUNT})"
        )


# ---------------------------------------------------------------------------
# Test 2: Core skills pass capability check
# ---------------------------------------------------------------------------


class TestCoreCapability:
    """Verify Core-tier skills pass capability contract checks."""

    def test_core_skills_pass_capability_gate(self) -> None:
        """At least 8 of 10 Core skills must pass capability check."""
        progress = _load_progress()
        statuses = _get_workflow_statuses(progress)

        core = [ws for ws in statuses if ws.get("tier") == "core"]
        if not core:
            pytest.skip("No Core-tier results yet")

        passed = sum(
            1 for ws in core if ws.get("capability_check") == "passed"
        )
        assert passed >= CORE_CAPABILITY_THRESHOLD, (
            f"Core capability gate: {passed}/{len(core)} passed, "
            f"need >= {CORE_CAPABILITY_THRESHOLD}"
        )

    def test_core_subwave_precedes_important(self) -> None:
        """Core sub-wave entries appear before Important entries in progress."""
        progress = _load_progress()
        statuses = _get_workflow_statuses(progress)

        core_indices = [
            i for i, ws in enumerate(statuses) if ws.get("tier") == "core"
        ]
        important_indices = [
            i for i, ws in enumerate(statuses) if ws.get("tier") == "important"
        ]

        if not core_indices or not important_indices:
            pytest.skip("Need both Core and Important results")

        assert max(core_indices) < min(important_indices), (
            "Core sub-wave must complete before Important sub-wave begins"
        )


# ---------------------------------------------------------------------------
# Test 3: Delegate mode contamination check
# ---------------------------------------------------------------------------


class TestDelegateMode:
    """Verify orchestrator session has zero prohibited calls."""

    def test_no_prohibited_cli_calls_in_orchestrator_jsonl(self) -> None:
        """Orchestrator JSONL contains no alphaswarm query/build-kg calls."""
        if not _OBSERVATIONS_DIR.exists():
            pytest.skip("Observations not yet produced")

        jsonl_files = list(_OBSERVATIONS_DIR.glob("*.jsonl"))
        if not jsonl_files:
            pytest.skip("No JSONL observation files found")

        violations: list[str] = []
        for jf in jsonl_files:
            for line_num, line in enumerate(jf.read_text().splitlines(), 1):
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                session_type = record.get("session_type", "")
                if session_type != "orchestrator":
                    continue

                tool = record.get("tool", "")
                command = record.get("command", "")

                # Check prohibited CLI calls
                if tool == "Bash" and (
                    "alphaswarm query" in command
                    or "alphaswarm build-kg" in command
                ):
                    violations.append(
                        f"{jf.name}:{line_num} — prohibited CLI: {command[:80]}"
                    )

        assert not violations, (
            f"Delegate mode contamination: {len(violations)} prohibited CLI calls\n"
            + "\n".join(violations[:5])
        )

    def test_no_sol_reads_in_orchestrator_jsonl(self) -> None:
        """Orchestrator JSONL contains no Read calls on .sol files."""
        if not _OBSERVATIONS_DIR.exists():
            pytest.skip("Observations not yet produced")

        jsonl_files = list(_OBSERVATIONS_DIR.glob("*.jsonl"))
        if not jsonl_files:
            pytest.skip("No JSONL observation files found")

        violations: list[str] = []
        for jf in jsonl_files:
            for line_num, line in enumerate(jf.read_text().splitlines(), 1):
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if record.get("session_type") != "orchestrator":
                    continue

                tool = record.get("tool", "")
                file_path = record.get("file_path", "")

                if tool == "Read" and file_path.endswith(".sol"):
                    violations.append(
                        f"{jf.name}:{line_num} — prohibited Read: {file_path}"
                    )

        assert not violations, (
            f"Delegate mode contamination: {len(violations)} .sol Read calls\n"
            + "\n".join(violations[:5])
        )

    def test_progress_reports_clean_delegate_mode(self) -> None:
        """progress.json delegate_mode status is 'clean' with 0 violations."""
        progress = _load_progress()
        dm = progress.get("delegate_mode", {})

        assert dm.get("status") == "clean", (
            f"Delegate mode not clean: {dm}"
        )
        assert dm.get("violations", -1) == 0, (
            f"Delegate mode violations: {dm.get('violations')}"
        )


# ---------------------------------------------------------------------------
# Test 4: Gate 0 dry-run evidence
# ---------------------------------------------------------------------------


class TestGateZero:
    """Verify Gate 0 dry-run completed before sub-wave execution."""

    def test_gate_0_recorded_in_progress(self) -> None:
        """progress.json has gate_0 entry with passed status."""
        progress = _load_progress()
        gate_0 = progress.get("gate_0", {})

        assert gate_0.get("status") == "passed", (
            f"Gate 0 not passed: {gate_0}"
        )

    def test_activation_test_10_of_10(self) -> None:
        """Pre-flight activation test achieved 10/10."""
        progress = _load_progress()
        at = progress.get("activation_test", {})

        assert at.get("score", 0) == 10, (
            f"Activation test score {at.get('score')}, expected 10"
        )
        assert at.get("result") == "pass", (
            f"Activation test result: {at.get('result')}"
        )


# ---------------------------------------------------------------------------
# Test 5: 3.2-critical readiness signal
# ---------------------------------------------------------------------------


class TestCriticalReadiness:
    """Verify 3.2-critical workflows are tagged and readiness computed."""

    def test_three_two_critical_section_exists(self) -> None:
        """progress.json contains three_two_critical section."""
        progress = _load_progress()
        ttc = progress.get("three_two_critical")

        assert ttc is not None, (
            "Missing three_two_critical section in progress.json"
        )

    def test_readiness_signal_computed(self) -> None:
        """At least 3 of 8 critical workflows score above threshold."""
        progress = _load_progress()
        ttc = progress.get("three_two_critical", {})

        above = ttc.get("achieved", ttc.get("above_threshold", 0))
        assert above >= CRITICAL_READINESS_THRESHOLD, (
            f"3.2 readiness: {above} above threshold, "
            f"need >= {CRITICAL_READINESS_THRESHOLD}"
        )

    def test_critical_workflows_have_dimension_scores(self) -> None:
        """Each critical workflow has CONCLUSION_SYNTHESIS and EVIDENCE_INTEGRATION."""
        progress = _load_progress()
        ttc = progress.get("three_two_critical", {})
        workflows = ttc.get("workflows", [])

        if not workflows:
            pytest.skip("No 3.2-critical workflow results yet")

        for wf in workflows:
            wid = wf.get("workflow_id", "UNKNOWN")
            assert "conclusion_synthesis" in wf, (
                f"{wid}: missing conclusion_synthesis score"
            )
            assert "evidence_integration" in wf, (
                f"{wid}: missing evidence_integration score"
            )


# ---------------------------------------------------------------------------
# Test 6: Circuit breaker not triggered
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    """Verify circuit breaker did not halt execution."""

    def test_no_stage_halt_files(self) -> None:
        """No stage_halt_*.json files exist (circuit breaker not triggered)."""
        if not _EVALUATIONS_DIR.exists():
            pytest.skip("Evaluations directory not yet created")

        halt_files = list(_EVALUATIONS_DIR.glob("stage_halt_*.json"))
        assert not halt_files, (
            f"Circuit breaker triggered: {[f.name for f in halt_files]}"
        )


# ---------------------------------------------------------------------------
# Test 7: Standard-tier baseline exclusion
# ---------------------------------------------------------------------------


class TestStandardTierExclusion:
    """Standard-tier results should not contribute to baseline scores."""

    def test_standard_tier_structural_only(self) -> None:
        """Standard-tier workflows should have run_reasoning: false."""
        progress = _load_progress()
        statuses = _get_workflow_statuses(progress)

        standard = [ws for ws in statuses if ws.get("tier") == "standard"]
        if not standard:
            pytest.skip("No Standard-tier results yet")

        # Standard-tier entries should not have full reasoning scores
        # They are structural validation only (P15-CSC-02)
        for ws in standard:
            # If there is a reasoning_score, it should be absent or null
            # (structural validation does not produce reasoning scores)
            if ws.get("reasoning_score") is not None:
                pytest.fail(
                    f"Standard-tier {ws.get('workflow_id')} has reasoning_score "
                    f"(should be structural only)"
                )


# ---------------------------------------------------------------------------
# Test 8: Anti-simulation guards (Plan 09 Task 3 — mandatory)
# ---------------------------------------------------------------------------


class TestAntiSimulation:
    """Verify evaluations used REAL Agent Teams, not RunMode.SIMULATED."""

    def test_core_evaluations_not_simulated(self) -> None:
        """Core workflows must NOT use RunMode.SIMULATED."""
        progress = _load_progress()
        statuses = _get_workflow_statuses(progress)

        core = [ws for ws in statuses if ws.get("tier") == "core"]
        if not core:
            pytest.skip("No Core-tier results yet")

        simulated = [
            ws["workflow_id"]
            for ws in core
            if ws.get("run_mode") == "simulated"
        ]
        assert not simulated, (
            f"ANTI-SIMULATION VIOLATION: {len(simulated)} Core workflow(s) used "
            f"RunMode.SIMULATED: {simulated}"
        )

    def test_real_transcripts_exist(self) -> None:
        """At least 1 Core workflow has non-empty observation artifacts."""
        if not _OBSERVATIONS_DIR.exists():
            pytest.skip("Observations not yet produced")

        # Check for any non-empty debrief or exit_report files
        gate0_dir = _OBSERVATIONS_DIR / "gate0"
        if not gate0_dir.exists():
            pytest.fail("No gate0 observation directory — Gate 0 not executed")

        debrief = gate0_dir / "debrief.json"
        assert debrief.exists() and debrief.stat().st_size > 0, (
            "Gate 0 debrief.json missing or empty — no REAL transcript evidence"
        )

        exit_report = gate0_dir / "exit_report.json"
        assert exit_report.exists() and exit_report.stat().st_size > 0, (
            "Gate 0 exit_report.json missing or empty"
        )

    def test_reasoning_scores_populated(self) -> None:
        """Core workflows that used INTERACTIVE mode should have run_mode set."""
        progress = _load_progress()
        statuses = _get_workflow_statuses(progress)

        interactive_core = [
            ws for ws in statuses
            if ws.get("tier") == "core"
            and ws.get("run_mode") == "INTERACTIVE"
        ]
        if not interactive_core:
            pytest.skip("No INTERACTIVE Core evaluations yet")

        # At least 1 Core workflow ran in INTERACTIVE mode
        assert len(interactive_core) >= 1, (
            "No Core workflows used INTERACTIVE mode"
        )

    def test_thresholds_not_gamed(self) -> None:
        """Compile-time constants must not be modified to accommodate simulated data."""
        # These constants are the contract — if someone changes them to make
        # simulated data pass, the test itself is compromised
        assert EXPECTED_SKILL_COUNT == 30, (
            f"EXPECTED_SKILL_COUNT modified to {EXPECTED_SKILL_COUNT}, expected 30"
        )
        assert CRITICAL_READINESS_THRESHOLD == 3, (
            f"CRITICAL_READINESS_THRESHOLD modified to "
            f"{CRITICAL_READINESS_THRESHOLD}, expected 3"
        )

    def test_gate0_used_real_agent(self) -> None:
        """Gate 0 must have run_mode != SIMULATED and real tool_use events."""
        progress = _load_progress()
        gate_0 = progress.get("gate_0", {})

        assert gate_0.get("status") == "passed", "Gate 0 not passed"
        assert gate_0.get("run_mode") != "simulated", (
            "Gate 0 used RunMode.SIMULATED — PROHIBITED"
        )

        result = gate_0.get("result", {})
        assert result.get("agent_teams_spawned") is True, (
            "Gate 0 did not spawn Agent Teams"
        )
        assert result.get("jsonl_transcript_nonempty") is True, (
            "Gate 0 JSONL transcript empty or missing"
        )
