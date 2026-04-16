"""Tests for 3.1c-01 evaluation data structures.

Verifies:
- All models construct with valid data
- JSON serialization round-trips
- Validation rejects invalid data
- No imports from alphaswarm_sol.kg or alphaswarm_sol.vulndocs (DC-2)
- EvaluationPlugin protocol compliance with context kwarg (DC-3)
- EvaluationInput bridge from CollectedOutput
- effective_score() edge cases (normal, all-N/A, mixed)
- EvaluatorConstants.current() with SHA256 hash
- CalibrationConfig/CalibrationResult split verification
- disambiguation_check() and ConstructAmbiguityError
- Self-evaluation guard on EvaluationConfig
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import ValidationError

from alphaswarm_sol.testing.evaluation.models import (
    BaselineKey,
    CalibrationConfig,
    CalibrationResult,
    ConstructAmbiguityError,
    DebriefResponse,
    DetectionSummary,
    DimensionScore,
    EvaluationConfig,
    EvaluationInput,
    EvaluationPlugin,
    EvaluationProgress,
    EvaluationResult,
    EvaluationStoreProtocol,
    EvaluatorConstants,
    EvaluatorDisagreement,
    ExperimentLedgerEntry,
    FailureMode,
    classify_failure,
    FailureNarrative,
    FailureReport,
    FailureRecommendation,
    FailureSignal,
    GraphValueScore,
    GroundTruthComparison,
    GroundTruthEntry,
    ImprovementHint,
    INFRA_TO_SIGNAL,
    MetaEvaluationResult,
    MoveAssessment,
    NormalizedFinding,
    ObservationDataQuality,
    ObservationRecord,
    PipelineHealth,
    PluginScore,
    ReasoningAssessment,
    ReasoningMove,
    RunMode,
    ScoreCard,
    SessionValidityManifest,
    SuiteExitReport,
    WorkflowStatus,
)


# ---------------------------------------------------------------------------
# RunMode
# ---------------------------------------------------------------------------


class TestRunMode:
    def test_values(self):
        assert RunMode.SIMULATED == "simulated"
        assert RunMode.HEADLESS == "headless"
        assert RunMode.INTERACTIVE == "interactive"

    def test_string_comparison(self):
        assert RunMode.SIMULATED == "simulated"
        assert RunMode("headless") == RunMode.HEADLESS


# ---------------------------------------------------------------------------
# ObservationRecord
# ---------------------------------------------------------------------------


class TestObservationRecord:
    def test_minimal_construction(self):
        rec = ObservationRecord(
            timestamp="2026-02-18T12:00:00Z",
            session_id="sess-001",
            event_type="tool_use",
            hook_name="obs_tool_use.py",
        )
        assert rec.event_type == "tool_use"
        assert rec.data == {}

    def test_with_data(self):
        rec = ObservationRecord(
            timestamp="2026-02-18T12:00:00Z",
            session_id="sess-001",
            event_type="bskg_query",
            hook_name="obs_bskg_query.py",
            data={"query": "functions without access control", "results": 5},
        )
        assert rec.data["results"] == 5

    def test_json_roundtrip(self):
        rec = ObservationRecord(
            timestamp="2026-02-18T12:00:00Z",
            session_id="sess-001",
            event_type="tool_use",
            hook_name="obs_tool_use.py",
            data={"tool": "Bash", "args": {"command": "ls"}},
        )
        json_str = rec.model_dump_json()
        restored = ObservationRecord.model_validate_json(json_str)
        assert restored == rec

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            ObservationRecord(
                timestamp="2026-02-18T12:00:00Z",
                session_id="sess-001",
                event_type="tool_use",
                hook_name="obs_tool_use.py",
                unknown_field="bad",
            )


# ---------------------------------------------------------------------------
# PluginScore & GraphValueScore
# ---------------------------------------------------------------------------


class TestPluginScore:
    def test_minimal(self):
        ps = PluginScore(plugin_name="test_plugin", score=75)
        assert ps.score == 75
        assert ps.details == {}
        assert ps.applicable is True

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            PluginScore(plugin_name="test", score=-1)
        with pytest.raises(ValidationError):
            PluginScore(plugin_name="test", score=101)

    def test_applicable_field(self):
        ps = PluginScore(plugin_name="test", score=50, applicable=False)
        assert ps.applicable is False

    def test_graph_value_score(self):
        gvs = GraphValueScore(
            plugin_name="graph_value",
            score=85,
            query_coverage=0.9,
            citation_rate=0.75,
            graph_first_compliant=True,
        )
        assert gvs.query_coverage == 0.9
        assert isinstance(gvs, PluginScore)

    def test_graph_value_score_json_roundtrip(self):
        gvs = GraphValueScore(
            plugin_name="graph_value",
            score=70,
            query_coverage=0.8,
            citation_rate=0.6,
            graph_first_compliant=False,
            details={"queries_issued": 5, "queries_expected": 7},
        )
        json_str = gvs.model_dump_json()
        restored = GraphValueScore.model_validate_json(json_str)
        assert restored.query_coverage == 0.8
        assert restored.details["queries_issued"] == 5


# ---------------------------------------------------------------------------
# DimensionScore & FailureNarrative
# ---------------------------------------------------------------------------


class TestDimensionScore:
    def test_construction(self):
        ds = DimensionScore(
            dimension="graph_utilization",
            score=80,
            weight=1.5,
            evidence=["Issued 5 BSKG queries", "Cited 4 results"],
            explanation="Good graph usage with minor gaps",
        )
        assert ds.dimension == "graph_utilization"
        assert ds.weight == 1.5
        assert ds.applicable is True

    def test_default_weight(self):
        ds = DimensionScore(dimension="test", score=50)
        assert ds.weight == 1.0

    def test_applicable_field(self):
        ds = DimensionScore(dimension="test", score=50, applicable=False)
        assert ds.applicable is False

    def test_behavioral_signature(self):
        ds = DimensionScore(
            dimension="graph_use",
            score=70,
            behavioral_signature="queries graph nodes traversal",
        )
        assert ds.behavioral_signature == "queries graph nodes traversal"


class TestFailureNarrative:
    def test_construction(self):
        fn = FailureNarrative(
            what_happened="Agent used manual code reading without BSKG queries",
            what_should_have_happened="Agent should query BSKG before reading code",
            root_dimensions=["graph_utilization"],
        )
        assert "BSKG" in fn.what_happened


# ---------------------------------------------------------------------------
# Disambiguation Check
# ---------------------------------------------------------------------------


class TestDisambiguationCheck:
    def test_no_overlap_passes(self):
        d1 = DimensionScore(dimension="graph_use", score=50, behavioral_signature="queries graph nodes")
        d2 = DimensionScore(dimension="evidence", score=60, behavioral_signature="cites findings conclusions")
        # Should not raise
        DimensionScore.disambiguation_check([d1, d2])

    def test_high_overlap_raises(self):
        d1 = DimensionScore(dimension="graph_use", score=50, behavioral_signature="queries graph nodes traversal")
        d2 = DimensionScore(dimension="graph_util", score=60, behavioral_signature="queries graph nodes coverage")
        with pytest.raises(ConstructAmbiguityError, match="overlap"):
            DimensionScore.disambiguation_check([d1, d2], overlap_threshold=0.3)

    def test_empty_signatures_ignored(self):
        d1 = DimensionScore(dimension="a", score=50, behavioral_signature="")
        d2 = DimensionScore(dimension="b", score=60, behavioral_signature="queries graph")
        # Should not raise — empty signatures are skipped
        DimensionScore.disambiguation_check([d1, d2])


# ---------------------------------------------------------------------------
# ScoreCard
# ---------------------------------------------------------------------------


class TestScoreCard:
    def _make_score_card(self, score: int = 75, passed: bool = True) -> ScoreCard:
        return ScoreCard(
            workflow_id="skill-vrs-audit",
            dimensions=[
                DimensionScore(dimension="capability", score=80),
                DimensionScore(dimension="reasoning", score=70),
            ],
            plugin_scores=[
                PluginScore(plugin_name="graph_value", score=85),
            ],
            overall_score=score,
            passed=passed,
        )

    def test_construction(self):
        sc = self._make_score_card()
        assert sc.workflow_id == "skill-vrs-audit"
        assert len(sc.dimensions) == 2
        assert len(sc.plugin_scores) == 1

    def test_dimension_lookup(self):
        sc = self._make_score_card()
        assert sc.dimension_by_name("capability") is not None
        assert sc.dimension_by_name("capability").score == 80
        assert sc.dimension_by_name("nonexistent") is None

    def test_failure_narrative_on_fail(self):
        sc = ScoreCard(
            workflow_id="test",
            overall_score=30,
            passed=False,
            failure_narrative=FailureNarrative(
                what_happened="Failed",
                what_should_have_happened="Succeeded",
            ),
        )
        assert sc.failure_narrative is not None
        assert not sc.passed

    def test_json_roundtrip(self):
        sc = self._make_score_card()
        json_str = sc.model_dump_json()
        restored = ScoreCard.model_validate_json(json_str)
        assert restored.overall_score == 75
        assert len(restored.dimensions) == 2

    def test_effective_score_normal(self):
        sc = ScoreCard(
            workflow_id="test",
            overall_score=75,
            passed=True,
            dimensions=[
                DimensionScore(dimension="a", score=80, weight=1.0),
                DimensionScore(dimension="b", score=60, weight=1.0),
            ],
        )
        assert sc.effective_score() == 70

    def test_effective_score_weighted(self):
        sc = ScoreCard(
            workflow_id="test",
            overall_score=75,
            passed=True,
            dimensions=[
                DimensionScore(dimension="a", score=100, weight=3.0),
                DimensionScore(dimension="b", score=0, weight=1.0),
            ],
        )
        # (100*3 + 0*1) / (3+1) = 75
        assert sc.effective_score() == 75

    def test_effective_score_all_na_returns_none(self):
        sc = ScoreCard(
            workflow_id="test",
            overall_score=75,
            passed=True,
            dimensions=[
                DimensionScore(dimension="a", score=80, applicable=False),
                DimensionScore(dimension="b", score=60, applicable=False),
            ],
        )
        assert sc.effective_score() is None

    def test_effective_score_mixed_applicable(self):
        sc = ScoreCard(
            workflow_id="test",
            overall_score=75,
            passed=True,
            dimensions=[
                DimensionScore(dimension="a", score=80, weight=1.0, applicable=True),
                DimensionScore(dimension="b", score=60, weight=1.0, applicable=False),
                DimensionScore(dimension="c", score=90, weight=1.0, applicable=True),
            ],
        )
        # Only a(80) and c(90) are applicable: (80+90)/2 = 85
        assert sc.effective_score() == 85

    def test_effective_score_empty_dimensions(self):
        sc = ScoreCard(
            workflow_id="test",
            overall_score=75,
            passed=True,
            dimensions=[],
        )
        assert sc.effective_score() is None


# ---------------------------------------------------------------------------
# PipelineHealth
# ---------------------------------------------------------------------------


class TestPipelineHealth:
    def test_healthy(self):
        ph = PipelineHealth(parsed_records=50, expected_records=52, errors=2)
        assert ph.health_pct == pytest.approx(48 / 52, rel=1e-3)
        assert ph.is_reliable  # 92% > 60%

    def test_unreliable(self):
        ph = PipelineHealth(parsed_records=10, expected_records=50, errors=25)
        assert not ph.is_reliable

    def test_empty(self):
        ph = PipelineHealth()
        assert ph.health_pct == 1.0  # No records expected, no errors
        assert ph.is_reliable


# ---------------------------------------------------------------------------
# EvaluationResult (with new fields)
# ---------------------------------------------------------------------------


class TestEvaluationResult:
    def test_construction(self):
        sc = ScoreCard(
            workflow_id="skill-vrs-audit",
            overall_score=75,
            passed=True,
        )
        er = EvaluationResult(
            scenario_name="reentrancy-basic",
            workflow_id="skill-vrs-audit",
            run_mode=RunMode.HEADLESS,
            score_card=sc,
        )
        assert er.run_mode == RunMode.HEADLESS
        assert er.result_id  # Auto-generated UUID
        assert er.started_at  # Auto-generated timestamp
        assert er.is_reliable  # Default PipelineHealth is healthy
        # New fields have defaults
        assert er.improvement_hints == []
        assert er.evaluator_disagreements == []
        assert er.detection_summary is None
        assert er.failure_signals == []
        assert er.infrastructure_failure_type is None
        assert er.scoring_cost_usd == 0.0
        assert er.baseline_update_status == "none"
        assert er.data_quality_warning == ""

    def test_json_roundtrip(self):
        sc = ScoreCard(
            workflow_id="test",
            overall_score=60,
            passed=True,
        )
        er = EvaluationResult(
            result_id="test-001",
            scenario_name="test-scenario",
            workflow_id="test",
            run_mode=RunMode.SIMULATED,
            score_card=sc,
            trial_number=2,
            metadata={"model": "sonnet"},
        )
        json_str = er.model_dump_json()
        restored = EvaluationResult.model_validate_json(json_str)
        assert restored.result_id == "test-001"
        assert restored.trial_number == 2
        assert restored.metadata["model"] == "sonnet"
        assert restored.run_mode == RunMode.SIMULATED

    def test_unreliable_result(self):
        sc = ScoreCard(workflow_id="test", overall_score=90, passed=True)
        er = EvaluationResult(
            scenario_name="test",
            workflow_id="test",
            run_mode=RunMode.HEADLESS,
            score_card=sc,
            pipeline_health=PipelineHealth(
                parsed_records=5, expected_records=50, errors=30
            ),
        )
        assert not er.is_reliable

    def test_with_new_fields(self):
        sc = ScoreCard(workflow_id="test", overall_score=60, passed=True)
        er = EvaluationResult(
            scenario_name="test",
            workflow_id="test",
            run_mode=RunMode.HEADLESS,
            score_card=sc,
            improvement_hints=[
                ImprovementHint(dimension="reasoning", hypothesis="Better prompts")
            ],
            detection_summary=DetectionSummary(tp=5, fp=2, fn=1),
            failure_signals=[FailureSignal(signal_type="hook_timeout", detail="slow")],
            scoring_cost_usd=0.05,
            baseline_update_status="updated",
            data_quality_warning="Some records had parse errors",
        )
        assert len(er.improvement_hints) == 1
        assert er.detection_summary.tp == 5
        assert er.scoring_cost_usd == 0.05
        assert er.baseline_update_status == "updated"


# ---------------------------------------------------------------------------
# ReasoningAssessment & 7-Move Decomposition
# ---------------------------------------------------------------------------


class TestReasoningAssessment:
    def test_construction(self):
        ra = ReasoningAssessment(
            session_id="sess-001",
            workflow_id="skill-vrs-audit",
            evaluator_id="A",
            overall_reasoning_score=75,
            moves=[
                MoveAssessment(
                    move=ReasoningMove.HYPOTHESIS_FORMATION,
                    score=80,
                    evidence=["Formed clear hypothesis about reentrancy"],
                ),
                MoveAssessment(
                    move=ReasoningMove.QUERY_FORMULATION,
                    score=70,
                ),
            ],
        )
        assert ra.overall_reasoning_score == 75
        assert len(ra.moves) == 2
        assert ra.moves[0].move == ReasoningMove.HYPOTHESIS_FORMATION

    def test_all_seven_moves(self):
        moves = [
            MoveAssessment(move=m, score=50)
            for m in ReasoningMove
        ]
        assert len(moves) == 7

    def test_json_roundtrip(self):
        ra = ReasoningAssessment(
            session_id="sess-001",
            workflow_id="test",
            overall_reasoning_score=65,
        )
        json_str = ra.model_dump_json()
        restored = ReasoningAssessment.model_validate_json(json_str)
        assert restored.session_id == "sess-001"
        assert restored.overall_reasoning_score == 65


# ---------------------------------------------------------------------------
# EvaluatorDisagreement
# ---------------------------------------------------------------------------


class TestEvaluatorDisagreement:
    def test_construction(self):
        ed = EvaluatorDisagreement(
            dimension="reasoning_depth",
            a_score=80,
            b_score=60,
        )
        assert ed.delta == 20
        assert ed.resolved_by == "unresolved"

    def test_with_pre_exposure(self):
        ed = EvaluatorDisagreement(
            dimension="evidence_quality",
            a_score=85,
            b_score=70,
            b_score_pre_exposure=65,
            debate_completed=True,
            resolved_by="consensus",
        )
        assert ed.b_score_pre_exposure == 65
        assert ed.debate_completed is True

    def test_delta_auto_computed(self):
        ed = EvaluatorDisagreement(
            dimension="test",
            a_score=90,
            b_score=45,
        )
        assert ed.delta == 45


# ---------------------------------------------------------------------------
# ImprovementHint
# ---------------------------------------------------------------------------


class TestImprovementHint:
    def test_construction(self):
        ih = ImprovementHint(
            dimension="graph_utilization",
            calibration_status="calibrated",
            hypothesis="Add explicit BSKG query prompt",
            kill_criterion="Score does not improve after 3 iterations",
            priority=8,
        )
        assert ih.dimension == "graph_utilization"
        assert ih.priority == 8


# ---------------------------------------------------------------------------
# MetaEvaluationResult
# ---------------------------------------------------------------------------


class TestMetaEvaluationResult:
    def test_construction(self):
        ra_a = ReasoningAssessment(
            session_id="s1", workflow_id="w1", overall_reasoning_score=80,
        )
        ra_b = ReasoningAssessment(
            session_id="s1", workflow_id="w1", overall_reasoning_score=65,
        )
        mer = MetaEvaluationResult(
            evaluator_a=ra_a,
            evaluator_b=ra_b,
            merged_score=73,
            disagreements=[
                EvaluatorDisagreement(dimension="reasoning", a_score=80, b_score=65)
            ],
        )
        assert mer.merged_score == 73
        assert len(mer.disagreements) == 1


# ---------------------------------------------------------------------------
# Calibration (split verification)
# ---------------------------------------------------------------------------


class TestCalibrationSplit:
    def test_config_construction(self):
        cc = CalibrationConfig(
            evaluator_model="opus",
            effort_level="thorough",
            debate_enabled=True,
            evaluator_prompt_hash="abc123",
            status="completed",
        )
        assert cc.evaluator_model == "opus"
        assert cc.status == "completed"

    def test_result_construction(self):
        cr = CalibrationResult(
            spearman_rho=0.85,
            spearman_rho_ci=(0.75, 0.92),
            consistency_class="stable",
        )
        assert cr.spearman_rho == 0.85

    def test_config_and_result_are_separate_types(self):
        """CalibrationConfig (inputs) and CalibrationResult (outputs) are distinct."""
        cc = CalibrationConfig(evaluator_model="opus")
        cr = CalibrationResult(spearman_rho=0.5)
        assert type(cc) != type(cr)
        assert not hasattr(cc, "spearman_rho")
        assert not hasattr(cr, "evaluator_model")


# ---------------------------------------------------------------------------
# EvaluatorConstants
# ---------------------------------------------------------------------------


class TestEvaluatorConstants:
    def test_current_factory(self):
        prompt_hash = hashlib.sha256(b"test prompt template").hexdigest()
        ec = EvaluatorConstants.current(prompt_hash)
        assert ec.prompt_template_hash == prompt_hash
        assert ec.scoring_scale_min == 0
        assert ec.scoring_scale_max == 100
        assert ec.disagreement_threshold == 15
        assert ec.evaluator_model == "opus"

    def test_frozen(self):
        ec = EvaluatorConstants.current("hash123")
        with pytest.raises(AttributeError):
            ec.scoring_scale_max = 200  # type: ignore[misc]

    def test_no_reasoning_evaluator_import(self):
        """EvaluatorConstants must not import from reasoning_evaluator (P14-IMP-06)."""
        import inspect
        import alphaswarm_sol.testing.evaluation.models as m
        source = inspect.getsource(m)
        import_lines = [
            line.strip()
            for line in source.splitlines()
            if line.strip().startswith(("import ", "from "))
        ]
        for line in import_lines:
            assert "reasoning_evaluator" not in line, (
                f"models.py imports from reasoning_evaluator: {line}"
            )


# ---------------------------------------------------------------------------
# Infrastructure Models
# ---------------------------------------------------------------------------


class TestFailureSignal:
    def test_construction(self):
        fs = FailureSignal(signal_type="hook_timeout", detail="Hook timed out after 30s")
        assert fs.signal_type == "hook_timeout"
        assert fs.recoverable is True


class TestSessionValidityManifest:
    def test_construction(self):
        svm = SessionValidityManifest(
            session_id="sess-001",
            valid=True,
            reasons=["All hooks executed", "Transcript complete"],
        )
        assert svm.valid is True
        assert len(svm.reasons) == 2


class TestObservationDataQuality:
    def test_construction(self):
        odq = ObservationDataQuality(
            serialize_errors=2,
            cross_session_records_dropped=1,
            stale_files_excluded=0,
            degraded=False,
        )
        assert odq.serialize_errors == 2
        assert not odq.degraded


class TestInfraToSignal:
    def test_mapping_exists(self):
        assert "hook_timeout" in INFRA_TO_SIGNAL
        assert "parser_error" in INFRA_TO_SIGNAL
        assert INFRA_TO_SIGNAL["hook_timeout"] == "observation_gap"


# ---------------------------------------------------------------------------
# Detection + Ground Truth
# ---------------------------------------------------------------------------


class TestDetectionSummary:
    def test_construction(self):
        ds = DetectionSummary(tp=8, fp=2, fn=1)
        assert ds.precision == 0.8
        assert ds.recall == pytest.approx(8 / 9)
        assert ds.f1 > 0

    def test_no_predictions(self):
        ds = DetectionSummary(tp=0, fp=0, fn=3)
        assert ds.precision == 1.0  # No predictions = perfect precision
        assert ds.recall == 0.0


class TestGroundTruthEntry:
    def test_construction(self):
        gte = GroundTruthEntry(
            entry_id="gt-001",
            contract_name="SideEntranceLenderPool",
            vulnerability_type="reentrancy",
            severity="high",
        )
        assert gte.severity == "high"


class TestNormalizedFinding:
    def test_construction(self):
        nf = NormalizedFinding(
            finding_id="f-001",
            tier="A",
            category="reentrancy",
            function_name="withdraw",
        )
        assert nf.tier == "A"


class TestGroundTruthComparison:
    def test_construction(self):
        gtc = GroundTruthComparison(
            ground_truths=[
                GroundTruthEntry(
                    entry_id="gt-001",
                    contract_name="Test",
                    vulnerability_type="reentrancy",
                )
            ],
            findings=[
                NormalizedFinding(finding_id="f-001", tier="A")
            ],
            matched=[("gt-001", "f-001")],
            detection_summary=DetectionSummary(tp=1, fp=0, fn=0),
        )
        assert len(gtc.matched) == 1


# ---------------------------------------------------------------------------
# Progress + Reporting
# ---------------------------------------------------------------------------


class TestEvaluationProgress:
    def test_construction(self):
        ep = EvaluationProgress(
            total_workflows=10,
            completed=5,
            failed=1,
            skipped=0,
        )
        assert ep.remaining == 4
        assert not ep.is_complete

    def test_complete(self):
        ep = EvaluationProgress(
            total_workflows=3,
            completed=2,
            failed=1,
        )
        assert ep.is_complete


class TestWorkflowStatus:
    def test_construction(self):
        ws = WorkflowStatus(
            workflow_id="skill-vrs-audit",
            status="completed",
        )
        assert ws.status == "completed"


class TestFailureReport:
    def test_construction(self):
        fr = FailureReport(
            failure_type="evaluator_crash",
            detail="LLM call timed out",
            recommendation=FailureRecommendation.RETRY,
        )
        assert fr.recommendation == FailureRecommendation.RETRY


class TestSuiteExitReport:
    def test_construction(self):
        ser = SuiteExitReport(
            progress=EvaluationProgress(total_workflows=1, completed=1),
            overall_passed=True,
        )
        assert ser.overall_passed is True
        assert ser.suite_id  # Auto-generated


class TestExperimentLedgerEntry:
    def test_construction(self):
        ele = ExperimentLedgerEntry(
            dimension="graph_utilization",
            hypothesis="Better prompts",
            decision="continue",
            iteration=1,
            score_before=50,
            score_after=65,
        )
        assert ele.decision == "continue"

    def test_roundtrip_json(self):
        """ExperimentLedgerEntry -> model_dump_json -> reload -> equal."""
        ele = ExperimentLedgerEntry(
            dimension="reasoning",
            hypothesis="Add chain-of-thought",
            decision="abandon",
            abandon_reason="Score decreased after 3 iterations",
            kill_criterion="Score < baseline for 3 consecutive runs",
            iteration=3,
            score_before=70,
            score_after=55,
        )
        json_str = ele.model_dump_json()
        restored = ExperimentLedgerEntry.model_validate_json(json_str)
        assert restored.dimension == ele.dimension
        assert restored.hypothesis == ele.hypothesis
        assert restored.decision == ele.decision
        assert restored.abandon_reason == ele.abandon_reason
        assert restored.kill_criterion == ele.kill_criterion
        assert restored.iteration == ele.iteration
        assert restored.score_before == ele.score_before
        assert restored.score_after == ele.score_after
        assert restored.entry_id == ele.entry_id


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------


class TestBaselineKey:
    def test_construction(self):
        bk = BaselineKey(
            workflow_id="skill-vrs-audit",
            run_mode=RunMode.HEADLESS,
            debate_enabled=True,
            effort_level="thorough",
            scoring_denominator_version="v2",
        )
        assert bk.workflow_id == "skill-vrs-audit"
        assert bk.scoring_denominator_version == "v2"


# ---------------------------------------------------------------------------
# EvaluationConfig (self-evaluation guard)
# ---------------------------------------------------------------------------


class TestEvaluationConfig:
    def test_normal_construction(self):
        cfg = EvaluationConfig(
            evaluator_session_id="eval-001",
            evaluated_session_id="target-001",
        )
        assert cfg.self_evaluation_guard is True

    def test_self_evaluation_rejected(self):
        with pytest.raises(ValidationError, match="Self-evaluation rejected"):
            EvaluationConfig(
                evaluator_session_id="same-session",
                evaluated_session_id="same-session",
                self_evaluation_guard=True,
            )

    def test_self_evaluation_guard_disabled(self):
        cfg = EvaluationConfig(
            evaluator_session_id="same-session",
            evaluated_session_id="same-session",
            self_evaluation_guard=False,
        )
        assert cfg.evaluator_session_id == "same-session"

    def test_empty_session_ids_allowed(self):
        """Empty session IDs should not trigger the guard."""
        cfg = EvaluationConfig(
            evaluator_session_id="",
            evaluated_session_id="",
        )
        assert cfg.self_evaluation_guard is True


# ---------------------------------------------------------------------------
# DebriefResponse (updated fields)
# ---------------------------------------------------------------------------


class TestDebriefResponse:
    def test_construction(self):
        dr = DebriefResponse(
            agent_name="attacker-1",
            agent_type="attacker",
            layer_used="send_message",
            questions=["What was your reasoning?", "What did you find?"],
            answers=["I queried BSKG first...", "Found reentrancy..."],
            confidence=0.9,
            duration_ms=1500.0,
        )
        assert dr.layer_used == "send_message"
        assert len(dr.questions) == 2
        assert len(dr.answers) == 2

    def test_compacted_field(self):
        dr = DebriefResponse(
            agent_name="a", agent_type="attacker", layer_used="hook_gate",
            questions=[], answers=[], compacted=True,
        )
        assert dr.compacted is True

    def test_delivery_status(self):
        dr = DebriefResponse(
            agent_name="a", agent_type="defender", layer_used="send_message",
            questions=[], answers=[], delivery_status="delivered",
        )
        assert dr.delivery_status == "delivered"

    def test_delivery_status_default(self):
        dr = DebriefResponse(
            agent_name="a", agent_type="attacker", layer_used="hook_gate",
            questions=[], answers=[],
        )
        assert dr.delivery_status == "not_attempted"


# ---------------------------------------------------------------------------
# EvaluationPlugin Protocol (DC-3 with context kwarg)
# ---------------------------------------------------------------------------


class _MockPlugin:
    """Test plugin implementing EvaluationPlugin protocol with context kwarg."""

    @property
    def name(self) -> str:
        return "mock_plugin"

    def score(
        self,
        collected_output: Any,
        context: dict[str, Any] | None = None,
    ) -> PluginScore:
        return PluginScore(plugin_name=self.name, score=50)

    def explain(self, plugin_score: PluginScore) -> str:
        return f"Score was {plugin_score.score}"


class _BadPlugin:
    """Missing required methods."""

    @property
    def name(self) -> str:
        return "bad"


class _OldPlugin:
    """Plugin without context kwarg (pre-DC-3 signature)."""

    @property
    def name(self) -> str:
        return "old_plugin"

    def score(self, collected_output: Any) -> PluginScore:
        return PluginScore(plugin_name=self.name, score=50)

    def explain(self, plugin_score: PluginScore) -> str:
        return "old"


class TestEvaluationPlugin:
    def test_protocol_compliance(self):
        plugin = _MockPlugin()
        assert isinstance(plugin, EvaluationPlugin)

    def test_protocol_non_compliance(self):
        bad = _BadPlugin()
        assert not isinstance(bad, EvaluationPlugin)

    def test_plugin_produces_score(self):
        plugin = _MockPlugin()
        result = plugin.score(None)
        assert result.plugin_name == "mock_plugin"
        assert result.score == 50

    def test_plugin_with_context(self):
        """DC-3: Plugin accepts context kwarg."""
        plugin = _MockPlugin()
        result = plugin.score(None, context={"run_mode": "headless"})
        assert result.score == 50

    def test_plugin_explains(self):
        plugin = _MockPlugin()
        ps = PluginScore(plugin_name="mock_plugin", score=75)
        explanation = plugin.explain(ps)
        assert "75" in explanation

    def test_old_plugin_fails_with_context(self):
        """PEP 544 trap: old plugin without context kwarg raises TypeError."""
        old = _OldPlugin()
        # Old plugin can be called without context (backwards compatible at call site)
        result = old.score(None)
        assert result.score == 50
        # But calling with context= raises TypeError
        with pytest.raises(TypeError):
            old.score(None, context={})


# ---------------------------------------------------------------------------
# EvaluationStoreProtocol
# ---------------------------------------------------------------------------


class _MockStore:
    """Test store implementing EvaluationStoreProtocol."""

    def __init__(self):
        self._results: dict[str, EvaluationResult] = {}

    def store_result(self, result: EvaluationResult) -> None:
        self._results[result.result_id] = result

    def get_result(self, result_id: str) -> EvaluationResult | None:
        return self._results.get(result_id)

    def list_results(
        self, workflow_id: str | None = None, limit: int = 100
    ) -> list[EvaluationResult]:
        results = list(self._results.values())
        if workflow_id:
            results = [r for r in results if r.workflow_id == workflow_id]
        return results[:limit]

    def get_latest(self, workflow_id: str) -> EvaluationResult | None:
        matching = [
            r for r in self._results.values() if r.workflow_id == workflow_id
        ]
        return matching[-1] if matching else None

    def append_history(self, workflow_id: str, result: EvaluationResult) -> None:
        self.store_result(result)


class TestEvaluationStoreProtocol:
    def test_protocol_compliance(self):
        store = _MockStore()
        assert isinstance(store, EvaluationStoreProtocol)

    def test_store_and_retrieve(self):
        store = _MockStore()
        sc = ScoreCard(workflow_id="test", overall_score=70, passed=True)
        er = EvaluationResult(
            result_id="r-001",
            scenario_name="test",
            workflow_id="test",
            run_mode=RunMode.SIMULATED,
            score_card=sc,
        )
        store.store_result(er)
        assert store.get_result("r-001") is not None
        assert store.get_result("nonexistent") is None

    def test_list_with_filter(self):
        store = _MockStore()
        for i, wf in enumerate(["a", "b", "a"]):
            sc = ScoreCard(workflow_id=wf, overall_score=50, passed=True)
            er = EvaluationResult(
                result_id=f"r-{i}",
                scenario_name="test",
                workflow_id=wf,
                run_mode=RunMode.SIMULATED,
                score_card=sc,
            )
            store.store_result(er)
        assert len(store.list_results(workflow_id="a")) == 2
        assert len(store.list_results()) == 3


# ---------------------------------------------------------------------------
# EvaluationInput Bridge (Issue #3)
# ---------------------------------------------------------------------------


@dataclass
class _FakeBSKGQuery:
    """Mimics the BSKGQuery dataclass from transcript_parser."""

    command: str = "query"
    query_text: str = "test query"
    category: str = "general"


@dataclass
class _FakeTeamObs:
    """Mimics TeamObservation."""

    agents: dict = field(default_factory=lambda: {"a1": {}, "a2": {}})


@dataclass
class _FakeCollectedOutput:
    """Mimics CollectedOutput for bridge testing."""

    scenario_name: str = "reentrancy-basic"
    run_id: str = "run-001"
    tool_sequence: list = field(default_factory=lambda: ["Bash", "Read", "Bash"])
    bskg_queries: list = field(default_factory=list)
    duration_ms: float = 5000.0
    cost_usd: float = 0.0
    failure_notes: str = ""
    response_text: str = "Found vulnerability"
    structured_output: dict | None = None
    team_observation: Any = None


class TestEvaluationInput:
    def test_from_collected_output_basic(self):
        co = _FakeCollectedOutput()
        ei = EvaluationInput.from_collected_output(co)
        assert ei.scenario_name == "reentrancy-basic"
        assert ei.run_id == "run-001"
        assert ei.tool_sequence == ["Bash", "Read", "Bash"]
        assert ei.run_mode == RunMode.SIMULATED

    def test_from_collected_output_with_bskg(self):
        co = _FakeCollectedOutput(
            bskg_queries=[
                _FakeBSKGQuery(command="query", query_text="test"),
                {"command": "build-kg", "query_text": "contracts/"},
            ]
        )
        ei = EvaluationInput.from_collected_output(co)
        assert len(ei.bskg_queries) == 2
        assert ei.bskg_queries[0]["command"] == "query"
        assert ei.bskg_queries[1]["command"] == "build-kg"

    def test_from_collected_output_with_team(self):
        co = _FakeCollectedOutput(team_observation=_FakeTeamObs())
        ei = EvaluationInput.from_collected_output(co)
        assert ei.agent_count == 2

    def test_run_mode_override(self):
        co = _FakeCollectedOutput()
        ei = EvaluationInput.from_collected_output(co, run_mode=RunMode.INTERACTIVE)
        assert ei.run_mode == RunMode.INTERACTIVE

    def test_json_roundtrip(self):
        co = _FakeCollectedOutput(response_text="test response")
        ei = EvaluationInput.from_collected_output(co)
        json_str = ei.model_dump_json()
        restored = EvaluationInput.model_validate_json(json_str)
        assert restored.response_text == "test response"
        assert restored.run_mode == RunMode.SIMULATED


# ---------------------------------------------------------------------------
# DC-2: No alphaswarm_sol.kg or vulndocs imports
# ---------------------------------------------------------------------------


class TestDC2NoForbiddenImports:
    """Verify models.py does NOT import from kg or vulndocs."""

    def _get_import_lines(self, module) -> list[str]:
        import inspect
        source = inspect.getsource(module)
        return [
            line.strip()
            for line in source.splitlines()
            if line.strip().startswith(("import ", "from "))
        ]

    def test_no_kg_import_in_models(self):
        import alphaswarm_sol.testing.evaluation.models as m
        imports = self._get_import_lines(m)
        for line in imports:
            assert "alphaswarm_sol.kg" not in line, f"Forbidden import: {line}"

    def test_no_vulndocs_import_in_models(self):
        import alphaswarm_sol.testing.evaluation.models as m
        imports = self._get_import_lines(m)
        for line in imports:
            assert "alphaswarm_sol.vulndocs" not in line, f"Forbidden import: {line}"

    def test_no_kg_import_in_intelligence(self):
        import alphaswarm_sol.testing.evaluation.intelligence as intel
        imports = self._get_import_lines(intel)
        for line in imports:
            assert "alphaswarm_sol.kg" not in line, f"Forbidden import in intelligence: {line}"

    def test_no_vulndocs_import_in_intelligence(self):
        import alphaswarm_sol.testing.evaluation.intelligence as intel
        imports = self._get_import_lines(intel)
        for line in imports:
            assert "alphaswarm_sol.vulndocs" not in line, f"Forbidden import in intelligence: {line}"

    def test_no_reasoning_evaluator_import(self):
        """P14-IMP-06: models.py must not import reasoning_evaluator."""
        import alphaswarm_sol.testing.evaluation.models as m
        imports = self._get_import_lines(m)
        for line in imports:
            assert "reasoning_evaluator" not in line, f"Forbidden import: {line}"


# ---------------------------------------------------------------------------
# FailureMode enum + classify_failure (R5)
# ---------------------------------------------------------------------------


class TestFailureMode:
    def test_enum_values(self):
        assert FailureMode.POLICY_REFUSAL == "policy_refusal"
        assert FailureMode.TASK_RESIGNATION == "task_resignation"
        assert FailureMode.SCAFFOLD_NONCOMPLIANCE == "scaffold_noncompliance"
        assert FailureMode.FABRICATION == "fabrication"
        assert FailureMode.FALSE_COMPLETION == "false_completion"

    def test_all_five_modes_defined(self):
        assert len(FailureMode) == 5


class TestClassifyFailure:
    def test_no_violations_no_transcript_returns_none(self):
        assert classify_failure([], "") is None

    def test_policy_refusal_from_transcript(self):
        result = classify_failure(
            [], transcript_text="I cannot assist with this security task"
        )
        assert result == FailureMode.POLICY_REFUSAL

    def test_scaffold_noncompliance(self):
        violations = [{"check_id": "python_import_bypass", "severity": "critical"}]
        result = classify_failure(violations)
        assert result == FailureMode.SCAFFOLD_NONCOMPLIANCE

    def test_fabrication(self):
        violations = [{"check_id": "no_cli_tool_calls", "severity": "critical"}]
        result = classify_failure(violations)
        assert result == FailureMode.FABRICATION

    def test_task_resignation_from_transcript(self):
        result = classify_failure(
            [], transcript_text="I cannot complete this analysis, giving up"
        )
        assert result == FailureMode.TASK_RESIGNATION

    def test_false_completion_fallback(self):
        """Unrecognized violations default to false_completion."""
        violations = [{"check_id": "some_other_check", "severity": "warning"}]
        result = classify_failure(violations)
        assert result == FailureMode.FALSE_COMPLETION

    def test_priority_scaffold_over_fabrication(self):
        """Scaffold noncompliance takes priority over fabrication."""
        violations = [
            {"check_id": "python_import_bypass", "severity": "critical"},
            {"check_id": "no_cli_tool_calls", "severity": "critical"},
        ]
        result = classify_failure(violations)
        assert result == FailureMode.SCAFFOLD_NONCOMPLIANCE

    def test_priority_refusal_over_violations(self):
        """Policy refusal from transcript takes priority over violations."""
        violations = [{"check_id": "no_cli_tool_calls", "severity": "critical"}]
        result = classify_failure(
            violations, transcript_text="I cannot assist with this"
        )
        assert result == FailureMode.POLICY_REFUSAL
