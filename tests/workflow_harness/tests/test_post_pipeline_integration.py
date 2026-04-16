"""Integration tests for post-pipeline stages: integrity + debrief + enrichment.

Covers:
- Integrity check auto-REJECT on FAIL verdict (Stage 8.5)
- Rejection artifact (rejection.json) persistence
- DEGRADED escalation at 3+ warnings boundary
- Debrief artifact persistence (Stage 9)
- Score tainting on integrity FAIL
- Stage timing telemetry in health.stage_durations and result.metadata
- session_correlation_id (UUID4) in result.metadata
- Observation enrichment (_enrichment.json)
- Ground truth comparison

Uses tmp_path, RunMode.SIMULATED, and synthetic observation data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml

from alphaswarm_sol.testing.evaluation.models import (
    EvaluationResult,
    RunMode,
    ScoreCard,
)
from tests.workflow_harness.lib.evaluation_runner import (
    EvaluationRunner,
    PIPELINE_STAGES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_CONTRACT = {
    "workflow_id": "test-workflow",
    "category": "skill",
    "grader_type": "standard",
    "rule_refs": [],
    "reasoning_dimensions": [],
    "capability_checks": [],
    "evidence_requirements": [],
    "metadata": {"tier": "Core"},
}


@dataclass
class FakeCollectedOutput:
    scenario_name: str = "test-scenario"
    run_id: str = "run-001"
    tool_sequence: list[str] = field(default_factory=list)
    bskg_queries: list[Any] = field(default_factory=list)
    duration_ms: float = 100.0
    cost_usd: float = 0.01
    failure_notes: str = ""
    response_text: str = ""
    structured_output: Any = None


def _write_contract(contracts_dir: Path, workflow_id: str, contract: dict) -> None:
    """Write a contract YAML to disk."""
    contracts_dir.mkdir(parents=True, exist_ok=True)
    path = contracts_dir / f"{workflow_id}.yaml"
    path.write_text(yaml.dump(contract))


def _make_valid_obs_dir(obs_dir: Path, session_id: str = "test-session") -> Path:
    """Create an obs_dir with JSONL that passes session validity checks."""
    obs_dir.mkdir(parents=True, exist_ok=True)
    jf = obs_dir / "session.jsonl"
    jf.write_text(
        '{"type": "assistant", "timestamp": "2026-03-01T10:00:00Z", '
        f'"session_id": "{session_id}", "subtype": "agent_stop", '
        '"message": {"role": "assistant", "content": [{"type": "text", "text": "done"}]}}\n'
    )
    return obs_dir


def _make_observation_file(
    obs_dir: Path,
    *,
    queries_executed: int = 4,
    nodes: int = 12,
    edges: int = 17,
    contract_id: str = "cal-01",
    session_duration_s: float = 300.0,
) -> Path:
    """Create a cal-*.json observation file with configurable stats."""
    started = "2026-03-01T00:00:00Z"
    # Simple offset for completed_at
    data = {
        "contract": "ReentrancyClassic",
        "contract_id": contract_id,
        "agent": "attacker",
        "agent_type": "vrs-attacker",
        "findings": [
            {"title": "Reentrancy", "severity": "high", "confidence": 0.8}
        ],
        "graph_stats": {"nodes": nodes, "edges": edges},
        "queries_executed": queries_executed,
        "session_metadata": {
            "started_at": started,
            "completed_at": f"2026-03-01T00:05:00Z",
        },
    }
    path = obs_dir / f"{contract_id}.json"
    path.write_text(json.dumps(data, indent=2))
    return path


def _make_runner(
    tmp_path: Path,
    *,
    obs_dir: Path | None = None,
    ground_truth_dir: Path | None = None,
    debrief_dir: Path | None = None,
) -> tuple[EvaluationRunner, Path]:
    """Create an EvaluationRunner with contracts and obs dir."""
    contracts_dir = tmp_path / "contracts"
    _write_contract(contracts_dir, "test-workflow", MINIMAL_CONTRACT)

    if obs_dir is None:
        obs_dir = tmp_path / "obs"
    _make_valid_obs_dir(obs_dir)

    runner = EvaluationRunner(
        contracts_dir=contracts_dir,
        obs_dir=obs_dir,
        debrief_dir=debrief_dir,
        run_mode=RunMode.SIMULATED,
        ground_truth_dir=ground_truth_dir,
    )
    return runner, obs_dir


def _run_pipeline(
    runner: EvaluationRunner,
    *,
    session_id: str = "test-session",
    debrief_agent_name: str | None = None,
    debrief_agent_type: str | None = None,
) -> EvaluationResult:
    """Run the pipeline with standard arguments."""
    return runner.run(
        scenario_name="test-scenario",
        workflow_id="test-workflow",
        collected_output=FakeCollectedOutput(),
        session_id=session_id,
        contract=MINIMAL_CONTRACT,
        debrief_agent_name=debrief_agent_name,
        debrief_agent_type=debrief_agent_type,
    )


# ---------------------------------------------------------------------------
# Integrity tests
# ---------------------------------------------------------------------------


class TestIntegrityCheck:
    def test_integrity_fail_produces_rejection_json(self, tmp_path: Path):
        """FAIL verdict -> rejection.json + baseline_update_status = rejected."""
        runner, obs_dir = _make_runner(tmp_path)
        # Create observation with queries_executed=0 -> critical violation
        _make_observation_file(obs_dir, queries_executed=0)

        result = _run_pipeline(runner)

        assert result.baseline_update_status == "rejected"
        rejection_path = obs_dir / "rejection.json"
        assert rejection_path.exists(), "rejection.json should be written on FAIL"

        report_data = json.loads(rejection_path.read_text())
        assert report_data["verdict"] == "FAIL"
        assert any(
            v["check_name"] == "zero_queries"
            for v in report_data["violations"]
        )

    def test_integrity_pass_no_rejection(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """PASS verdict -> no rejection.json, no tainted flag, no rejected status.

        Uses monkeypatch to return a clean PASS report so the test is not
        affected by the always-firing worktree check in test environments.
        """
        from alphaswarm_sol.testing.evaluation.agent_execution_validator import (
            IntegrityReport,
        )
        import alphaswarm_sol.testing.evaluation.agent_execution_validator as val_mod

        pass_report = IntegrityReport(
            batch_id="test",
            total_files=1,
            files_checked=1,
            violations=[],
            verdict="PASS",
            summary="All checks passed",
        )
        monkeypatch.setattr(val_mod, "validate_batch", lambda *a, **kw: pass_report)

        runner, obs_dir = _make_runner(tmp_path)
        _make_observation_file(obs_dir, queries_executed=4, nodes=12, edges=17)

        result = _run_pipeline(runner)

        rejection_path = obs_dir / "rejection.json"
        assert not rejection_path.exists(), "rejection.json must NOT exist for PASS verdict"

        ic = result.metadata.get("integrity_check", {})
        assert ic.get("verdict") == "PASS", f"Expected PASS verdict in metadata, got {ic}"

        assert "tainted" not in result.metadata, (
            f"PASS verdict must not set tainted flag, metadata={result.metadata}"
        )

        assert result.baseline_update_status != "rejected", (
            f"PASS verdict must not set baseline_update_status=rejected, "
            f"got {result.baseline_update_status}"
        )

    def test_integrity_degraded_escalation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """DEGRADED with 3+ warnings escalates to FAIL.

        Uses monkeypatch to control validate_batch output, avoiding
        environment-dependent worktree check that always fires critical.
        """
        from alphaswarm_sol.testing.evaluation.agent_execution_validator import (
            IntegrityReport,
            IntegrityViolation,
        )
        import alphaswarm_sol.testing.evaluation.agent_execution_validator as val_mod

        # Create a report with 3 warnings and no criticals = DEGRADED
        fake_report = IntegrityReport(
            batch_id="test",
            total_files=1,
            files_checked=1,
            violations=[
                IntegrityViolation(
                    check_name="graph_stats_implausible",
                    severity="warning",
                    file_path="test.json",
                    details="warning 1",
                ),
                IntegrityViolation(
                    check_name="graph_no_edges",
                    severity="warning",
                    file_path="test.json",
                    details="warning 2",
                ),
                IntegrityViolation(
                    check_name="uniform_confidence",
                    severity="warning",
                    file_path="test.json",
                    details="warning 3",
                ),
            ],
            verdict="DEGRADED",
            summary="3 warnings, 0 critical",
        )

        # Patch at the source module — lazy import in evaluation_runner
        # does `from alphaswarm_sol...agent_execution_validator import validate_batch`
        # which reads the attribute from the already-cached module
        monkeypatch.setattr(val_mod, "validate_batch", lambda *a, **kw: fake_report)

        runner, obs_dir = _make_runner(tmp_path)
        _make_observation_file(obs_dir, queries_executed=4, nodes=12, edges=17)

        result = _run_pipeline(runner)

        ic = result.metadata.get("integrity_check", {})
        assert ic.get("escalated") is True, f"Expected escalated=True, got {ic}"
        assert ic.get("escalation_reason", "").startswith("DEGRADED with 3 warnings")
        assert result.baseline_update_status == "rejected"
        assert result.metadata.get("tainted") is True

    def test_integrity_check_with_ground_truth(self, tmp_path: Path):
        """Ground truth comparison: >30% deviation = critical -> FAIL."""
        gt_dir = tmp_path / "ground_truth"
        gt_dir.mkdir(parents=True, exist_ok=True)
        # Ground truth says 12 nodes
        (gt_dir / "cal-01-graph-stats.json").write_text(
            json.dumps({"nodes": 12, "edges": 17})
        )

        runner, obs_dir = _make_runner(tmp_path, ground_truth_dir=gt_dir)
        # Observation reports 50 nodes (>30% deviation from 12)
        _make_observation_file(obs_dir, queries_executed=4, nodes=50, edges=100)

        result = _run_pipeline(runner)

        assert result.baseline_update_status == "rejected"
        rejection_path = obs_dir / "rejection.json"
        assert rejection_path.exists()

        report_data = json.loads(rejection_path.read_text())
        assert report_data["verdict"] == "FAIL"
        assert any(
            v["check_name"] == "graph_stats_mismatch"
            for v in report_data["violations"]
        )

    def test_integrity_error_graceful(self, tmp_path: Path):
        """Integrity check on non-existent obs_dir does not crash."""
        contracts_dir = tmp_path / "contracts"
        _write_contract(contracts_dir, "test-workflow", MINIMAL_CONTRACT)

        # Runner with no obs_dir — integrity check should be skipped
        runner = EvaluationRunner(
            contracts_dir=contracts_dir,
            run_mode=RunMode.SIMULATED,
        )

        result = runner.run(
            scenario_name="test-scenario",
            workflow_id="test-workflow",
            collected_output=FakeCollectedOutput(),
            contract=MINIMAL_CONTRACT,
        )

        # Should complete without crashing
        assert result.status in ("completed", "failed")
        # No integrity_check since there's no obs dir
        # (integrity_check may or may not be in stages depending on impl)

    def test_integrity_rejection_not_overwritten_by_baseline_manager(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Tainted (integrity-rejected) sessions must not have baselines updated.

        Verifies Correction 1: the tainted guard in the baseline manager condition
        prevents update_baseline() from being called for tainted results.
        """
        from alphaswarm_sol.testing.evaluation.agent_execution_validator import (
            IntegrityReport,
            IntegrityViolation,
        )
        import alphaswarm_sol.testing.evaluation.agent_execution_validator as val_mod

        # FAIL report so result gets tainted
        fail_report = IntegrityReport(
            batch_id="test",
            total_files=1,
            files_checked=1,
            violations=[
                IntegrityViolation(
                    check_name="zero_queries",
                    severity="critical",
                    file_path="test.json",
                    details="No CLI queries executed",
                ),
            ],
            verdict="FAIL",
            summary="1 critical violation",
        )
        monkeypatch.setattr(val_mod, "validate_batch", lambda *a, **kw: fail_report)

        # Minimal fake baseline_manager: records whether update_baseline was called
        class FakeBaselineManager:
            def __init__(self):
                self.called = False

            def update_baseline(self, workflow_id: str, result: Any) -> None:
                self.called = True

        fake_bm = FakeBaselineManager()

        contracts_dir = tmp_path / "contracts"
        _write_contract(contracts_dir, "test-workflow", MINIMAL_CONTRACT)
        obs_dir = tmp_path / "obs"
        _make_valid_obs_dir(obs_dir)
        _make_observation_file(obs_dir, queries_executed=4, nodes=12, edges=17)

        runner = EvaluationRunner(
            contracts_dir=contracts_dir,
            obs_dir=obs_dir,
            run_mode=RunMode.SIMULATED,
            baseline_manager=fake_bm,
        )

        result = runner.run(
            scenario_name="test-scenario",
            workflow_id="test-workflow",
            collected_output=FakeCollectedOutput(),
            session_id="test-session",
            contract=MINIMAL_CONTRACT,
        )

        # Integrity FAIL must have set tainted
        assert result.metadata.get("tainted") is True

        # baseline_update_status must remain "rejected" (set by integrity check)
        assert result.baseline_update_status == "rejected", (
            f"Expected 'rejected', got '{result.baseline_update_status}'. "
            "Tainted flag must prevent baseline update."
        )

        # update_baseline must NOT have been called
        assert not fake_bm.called, (
            "update_baseline() must not be called for tainted (integrity-failed) results"
        )


# ---------------------------------------------------------------------------
# Debrief tests
# ---------------------------------------------------------------------------


class TestDebriefPersistence:
    def test_debrief_persisted_on_completed_session(self, tmp_path: Path):
        """Debrief artifact persisted to obs_dir when debrief agent info provided."""
        # NOTE: Do NOT pass debrief_dir here — session validity rejects if
        # debrief_dir is set but empty. Debrief persistence writes to obs_dir.
        runner, obs_dir = _make_runner(tmp_path)
        # Create a valid observation
        _make_observation_file(obs_dir, queries_executed=4, nodes=12, edges=17)

        result = _run_pipeline(
            runner,
            debrief_agent_name="test-agent",
            debrief_agent_type="vrs-attacker",
        )

        assert result.status == "completed", f"Expected completed, got {result.status}"

        # Debrief artifact should exist in obs_dir
        debrief_path = obs_dir / "debrief.json"
        assert debrief_path.exists(), "debrief.json should be written"

        # Stage 9 should be in stages_completed
        assert "run_debrief" in result.pipeline_health.stages_completed

        # Metadata should have debrief info
        assert result.metadata.get("debrief", {}).get("layer_used") is not None

    def test_debrief_skipped_on_invalid_session(self, tmp_path: Path):
        """Debrief skipped when session is invalid (early return)."""
        contracts_dir = tmp_path / "contracts"
        _write_contract(contracts_dir, "test-workflow", MINIMAL_CONTRACT)

        # Empty obs_dir: no JSONL files -> session validity fails
        obs_dir = tmp_path / "obs"
        obs_dir.mkdir(parents=True, exist_ok=True)

        runner = EvaluationRunner(
            contracts_dir=contracts_dir,
            obs_dir=obs_dir,
            run_mode=RunMode.SIMULATED,
        )

        result = runner.run(
            scenario_name="test-scenario",
            workflow_id="test-workflow",
            collected_output=FakeCollectedOutput(),
            session_id="test-session",
            contract=MINIMAL_CONTRACT,
            debrief_agent_name="test-agent",
            debrief_agent_type="vrs-attacker",
        )

        # Session is invalid => early return
        assert result.status == "invalid_session"
        assert "run_debrief" not in result.pipeline_health.stages_completed

    def test_debrief_skipped_without_agent_info(self, tmp_path: Path):
        """No debrief when agent info is absent."""
        runner, obs_dir = _make_runner(tmp_path)
        _make_observation_file(obs_dir, queries_executed=4, nodes=12, edges=17)

        result = _run_pipeline(runner)  # No debrief_agent_name/type

        debrief_path = obs_dir / "debrief.json"
        assert not debrief_path.exists(), "debrief.json should NOT exist without agent info"
        assert "run_debrief" not in result.pipeline_health.stages_completed

    def test_debrief_artifact_format(self, tmp_path: Path):
        """Debrief artifact has the expected JSON structure."""
        runner, obs_dir = _make_runner(tmp_path)
        _make_observation_file(obs_dir, queries_executed=4, nodes=12, edges=17)

        result = _run_pipeline(
            runner,
            debrief_agent_name="test-agent",
            debrief_agent_type="vrs-attacker",
        )

        debrief_path = obs_dir / "debrief.json"
        assert debrief_path.exists(), "debrief.json must exist for format validation"
        artifact = json.loads(debrief_path.read_text())
        assert "agent_name" in artifact
        assert "layer_used" in artifact
        assert "answers" in artifact
        assert "confidence" in artifact
        assert "questions_asked" in artifact


# ---------------------------------------------------------------------------
# Tainting tests
# ---------------------------------------------------------------------------


class TestScoreTainting:
    def test_score_tainting_on_integrity_fail(self, tmp_path: Path):
        """Integrity FAIL sets tainted=True and taint_reason in metadata."""
        runner, obs_dir = _make_runner(tmp_path)
        # Zero queries -> critical -> FAIL
        _make_observation_file(obs_dir, queries_executed=0)

        result = _run_pipeline(runner)

        assert result.metadata.get("tainted") is True
        taint_reason = result.metadata.get("taint_reason", "")
        assert taint_reason.startswith("integrity_check_failed:")


# ---------------------------------------------------------------------------
# Timing and correlation tests
# ---------------------------------------------------------------------------


class TestTimingAndCorrelation:
    def test_stage_timing_telemetry(self, tmp_path: Path):
        """Pipeline timing recorded in metadata and health."""
        runner, obs_dir = _make_runner(tmp_path)
        _make_observation_file(obs_dir, queries_executed=4, nodes=12, edges=17)

        result = _run_pipeline(runner)

        timing = result.metadata.get("pipeline_timing")
        assert timing is not None, "pipeline_timing should be in metadata"
        assert isinstance(timing, dict)

        # Check all values are non-negative floats
        for stage_name, duration in timing.items():
            assert isinstance(duration, float), f"{stage_name} duration should be float"
            assert duration >= 0, f"{stage_name} duration should be non-negative"

        # Check health.stage_durations matches
        assert result.pipeline_health.stage_durations == timing

    def test_session_correlation_id_present(self, tmp_path: Path):
        """session_correlation_id is a UUID4 string in metadata."""
        runner, obs_dir = _make_runner(tmp_path)
        _make_observation_file(obs_dir, queries_executed=4, nodes=12, edges=17)

        result = _run_pipeline(runner)

        cid = result.metadata.get("session_correlation_id")
        assert cid is not None, "session_correlation_id should be in metadata"
        assert isinstance(cid, str)
        assert len(cid) == 36, f"UUID4 should be 36 chars, got {len(cid)}"
        # UUID4 format: 8-4-4-4-12
        parts = cid.split("-")
        assert len(parts) == 5, f"UUID4 should have 5 dash-separated parts, got {len(parts)}"


# ---------------------------------------------------------------------------
# DEGRADED escalation boundary tests
# ---------------------------------------------------------------------------


class TestDegradedEscalation:
    def test_degraded_escalation_threshold(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Boundary: 2 warnings = no escalation, 3 warnings = escalation to FAIL.

        Uses monkeypatch to control validate_batch output for both sides
        of the boundary.
        """
        from alphaswarm_sol.testing.evaluation.agent_execution_validator import (
            IntegrityReport,
            IntegrityViolation,
        )
        import alphaswarm_sol.testing.evaluation.agent_execution_validator as val_mod

        def _make_report(warning_count: int) -> IntegrityReport:
            violations = [
                IntegrityViolation(
                    check_name=f"warning_{i}",
                    severity="warning",
                    file_path="test.json",
                    details=f"warning {i}",
                )
                for i in range(warning_count)
            ]
            return IntegrityReport(
                batch_id="test",
                total_files=1,
                files_checked=1,
                violations=violations,
                verdict="DEGRADED",
                summary=f"{warning_count} warnings, 0 critical",
            )

        # --- Test 2 warnings: should NOT escalate ---
        report_2w = _make_report(2)
        monkeypatch.setattr(val_mod, "validate_batch", lambda *a, **kw: report_2w)

        runner, obs_dir = _make_runner(tmp_path)
        _make_observation_file(obs_dir, queries_executed=4, nodes=12, edges=17)

        result_2w = _run_pipeline(runner)

        ic_2w = result_2w.metadata.get("integrity_check", {})
        assert ic_2w.get("escalated") is not True, "2 warnings should NOT escalate"
        assert result_2w.metadata.get("tainted") is not True, "2 warnings should NOT taint"

        # --- Test 3 warnings: should escalate ---
        report_3w = _make_report(3)
        monkeypatch.setattr(val_mod, "validate_batch", lambda *a, **kw: report_3w)

        # New runner in separate dir to avoid leftover artifacts
        runner_3, obs_dir_3 = _make_runner(tmp_path / "run3")
        _make_observation_file(obs_dir_3, queries_executed=4, nodes=12, edges=17)

        result_3w = _run_pipeline(runner_3)

        ic_3w = result_3w.metadata.get("integrity_check", {})
        assert ic_3w.get("escalated") is True, "3 warnings should escalate"
        assert result_3w.baseline_update_status == "rejected"
        assert result_3w.metadata.get("tainted") is True


# ---------------------------------------------------------------------------
# Enrichment tests
# ---------------------------------------------------------------------------


class TestObservationEnrichment:
    def test_enrichment_json_written(self, tmp_path: Path):
        """_enrichment.json written to obs_dir after pipeline."""
        runner, obs_dir = _make_runner(tmp_path)
        _make_observation_file(obs_dir, queries_executed=4, nodes=12, edges=17)

        result = _run_pipeline(runner)

        enrichment_path = obs_dir / "_enrichment.json"
        assert enrichment_path.exists(), "_enrichment.json should be written"

        enrichment = json.loads(enrichment_path.read_text())
        assert "pipeline_timing" in enrichment
        assert "session_correlation_id" in enrichment
        assert "stages_completed" in enrichment
        assert "total_duration_s" in enrichment
        assert isinstance(enrichment["total_duration_s"], float)
        assert enrichment["total_duration_s"] >= 0

    def test_enrichment_includes_integrity_verdict(self, tmp_path: Path):
        """Enrichment includes integrity_verdict when integrity check ran."""
        runner, obs_dir = _make_runner(tmp_path)
        _make_observation_file(obs_dir, queries_executed=0)  # triggers FAIL

        result = _run_pipeline(runner)

        enrichment_path = obs_dir / "_enrichment.json"
        assert enrichment_path.exists()

        enrichment = json.loads(enrichment_path.read_text())
        assert "integrity_verdict" in enrichment
        assert enrichment.get("tainted") is True
