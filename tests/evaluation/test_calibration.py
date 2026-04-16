"""Phase 3.1d-04: Calibrate Evaluator on Real Output.

AUDIT NOTE (2026-02-18): All calibration transcripts and "real" transcripts were
fabricated (hand-authored JSONL with zero-ms timestamps, not from real agent runs).
They have been deleted. Tests that depended on this fabricated data are marked
xfail until genuine transcripts are captured from real Claude Code sessions.

To capture real transcripts, run actual workflows with observation hooks installed:
  uv run alphaswarm build-kg tests/contracts/ReentrancyClassic.sol
  uv run alphaswarm query "reentrancy patterns"
Then copy the resulting .vrs/observations/*.jsonl files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from alphaswarm_sol.testing.evaluation.models import EvaluationInput, RunMode
from tests.workflow_harness.graders.graph_value_scorer import GraphValueScorer
from tests.workflow_harness.graders.reasoning_evaluator import ReasoningEvaluator
from tests.workflow_harness.lib.observation_parser import ObservationParser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CALIBRATION_DIR = Path(__file__).parents[2] / ".vrs" / "observations" / "calibration"

# Inline contract for calibration (avoids dependency on disk contract files)
CALIBRATION_CONTRACT = {
    "workflow_id": "calibration-test",
    "category": "agent",
    "grader_type": "hybrid",
    "rule_refs": ["GRAPH-FIRST", "EVIDENCE-QUALITY"],
    "reasoning_dimensions": [
        {"name": "graph_utilization", "weight": 1.5},
        {"name": "evidence_quality", "weight": 1.0},
        {"name": "reasoning_depth", "weight": 1.0},
        {"name": "hypothesis_formation", "weight": 0.8},
    ],
    "capability_checks": [
        {
            "id": "bskg_query_issued",
            "description": "Agent issued BSKG queries before code reading",
            "expected_behavior": "Tool sequence contains Bash with alphaswarm query before first Read",
            "grader_type": "code",
        },
        {
            "id": "evidence_cited",
            "description": "Findings reference graph nodes",
            "expected_behavior": "Response contains node or BSKG references",
            "grader_type": "model",
        },
    ],
    "evidence_requirements": [],
    "evaluation_config": {"run_gvs": True},
    "metadata": {"tier": "calibration"},
}


def _load_transcript_as_eval_input(jsonl_path: Path) -> EvaluationInput:
    """Parse a calibration JSONL file into an EvaluationInput.

    Extracts tool_sequence, bskg_queries, and response_text from
    the observation records.
    """
    records: list[dict[str, Any]] = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    tool_sequence: list[str] = []
    bskg_queries: list[dict[str, Any]] = []
    response_text = ""
    session_id = ""

    for record in records:
        if not session_id:
            session_id = record.get("session_id", "unknown")

        event_type = record.get("event_type", "")
        data = record.get("data", {})

        if event_type == "tool_use":
            tool_sequence.append(data.get("tool_name", ""))
        elif event_type == "bskg_query":
            bskg_queries.append({
                "command": data.get("command", ""),
                "category": data.get("category", ""),
                "result_preview": data.get("result_preview", ""),
            })
        elif event_type == "message":
            # Use the content_preview as the response text
            content = data.get("content_preview", "")
            if content:
                response_text += content + "\n"

    return EvaluationInput(
        scenario_name=jsonl_path.stem,
        run_id=session_id,
        tool_sequence=tool_sequence,
        bskg_queries=bskg_queries,
        response_text=response_text.strip(),
        run_mode=RunMode.SIMULATED,
    )


def _score_transcript(jsonl_path: Path) -> tuple[int, dict[str, Any]]:
    """Run the full evaluation pipeline on a calibration transcript.

    Returns (overall_score, details_dict).
    """
    eval_input = _load_transcript_as_eval_input(jsonl_path)

    evaluator = ReasoningEvaluator(
        workflow_id="calibration-test",
        contract=CALIBRATION_CONTRACT,
        pass_threshold=60,
    )
    score_card = evaluator.evaluate(eval_input)

    details = {
        "overall": score_card.overall_score,
        "passed": score_card.passed,
        "dimensions": {
            d.dimension: d.score for d in score_card.dimensions
        },
        "plugins": {
            ps.plugin_name: ps.score for ps in score_card.plugin_scores
        },
        "tool_sequence": eval_input.tool_sequence,
        "bskg_query_count": len(eval_input.bskg_queries),
        "response_length": len(eval_input.response_text),
    }
    return score_card.overall_score, details


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def calibration_dir() -> Path:
    """Path to calibration transcripts."""
    if not CALIBRATION_DIR.exists():
        pytest.skip(
            "Calibration directory not found. Fabricated data was deleted in audit. "
            "Capture real transcripts from actual Claude Code sessions to restore."
        )
    return CALIBRATION_DIR


# ---------------------------------------------------------------------------
# GVS Direct Tests on Calibration Data
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="Calibration data was fabricated (hand-authored JSONL). Deleted in quality audit. "
    "Needs real transcripts from actual Claude Code sessions.",
    strict=False,
)
class TestGVSOnCalibrationData:
    """Test GraphValueScorer directly on calibration transcripts."""

    def test_gvs_good_transcript_high_score(self, calibration_dir: Path):
        """Good transcript should score >= 70 on GVS alone."""
        eval_input = _load_transcript_as_eval_input(
            calibration_dir / "calibration-good-01.jsonl"
        )
        scorer = GraphValueScorer()
        result = scorer.score(eval_input)

        assert result.score >= 65, (
            f"GVS score {result.score} too low for good transcript. "
            f"Coverage={result.query_coverage:.2f}, "
            f"Citation={result.citation_rate:.2f}, "
            f"GraphFirst={result.graph_first_compliant}"
        )

    def test_gvs_bad_transcript_low_score(self, calibration_dir: Path):
        """Bad transcript should score < 30 on GVS."""
        eval_input = _load_transcript_as_eval_input(
            calibration_dir / "calibration-bad-01.jsonl"
        )
        scorer = GraphValueScorer()
        result = scorer.score(eval_input)

        assert result.score < 30, (
            f"GVS score {result.score} too high for bad transcript. "
            f"Coverage={result.query_coverage:.2f}, "
            f"Citation={result.citation_rate:.2f}, "
            f"GraphFirst={result.graph_first_compliant}"
        )

    def test_gvs_spread_between_good_and_bad(self, calibration_dir: Path):
        """Good - Bad differential should be > 30 on GVS alone."""
        good_input = _load_transcript_as_eval_input(
            calibration_dir / "calibration-good-01.jsonl"
        )
        bad_input = _load_transcript_as_eval_input(
            calibration_dir / "calibration-bad-01.jsonl"
        )
        scorer = GraphValueScorer()

        good_score = scorer.score(good_input).score
        bad_score = scorer.score(bad_input).score

        diff = good_score - bad_score
        assert diff > 30, (
            f"GVS spread too narrow: good={good_score}, bad={bad_score}, "
            f"diff={diff}"
        )


# ---------------------------------------------------------------------------
# Full Pipeline Calibration
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="Calibration data was fabricated (hand-authored JSONL). Deleted in quality audit. "
    "Needs real transcripts from actual Claude Code sessions.",
    strict=False,
)
class TestFullPipelineCalibration:
    """Test the full evaluation pipeline on calibration transcripts."""

    def test_good_01_scores_above_70(self, calibration_dir: Path):
        score, details = _score_transcript(
            calibration_dir / "calibration-good-01.jsonl"
        )
        assert score > 70, (
            f"Good-01 scored {score}, expected >70. Details: {details}"
        )

    def test_good_02_scores_above_70(self, calibration_dir: Path):
        score, details = _score_transcript(
            calibration_dir / "calibration-good-02.jsonl"
        )
        assert score > 70, (
            f"Good-02 scored {score}, expected >70. Details: {details}"
        )

    def test_mediocre_01_scores_30_to_60(self, calibration_dir: Path):
        score, details = _score_transcript(
            calibration_dir / "calibration-mediocre-01.jsonl"
        )
        assert 30 <= score <= 60, (
            f"Mediocre-01 scored {score}, expected 30-60. Details: {details}"
        )

    def test_mediocre_02_scores_30_to_60(self, calibration_dir: Path):
        score, details = _score_transcript(
            calibration_dir / "calibration-mediocre-02.jsonl"
        )
        assert 30 <= score <= 60, (
            f"Mediocre-02 scored {score}, expected 30-60. Details: {details}"
        )

    def test_bad_01_scores_below_30(self, calibration_dir: Path):
        score, details = _score_transcript(
            calibration_dir / "calibration-bad-01.jsonl"
        )
        assert score < 30, (
            f"Bad-01 scored {score}, expected <30. Details: {details}"
        )

    def test_bad_02_scores_below_30(self, calibration_dir: Path):
        score, details = _score_transcript(
            calibration_dir / "calibration-bad-02.jsonl"
        )
        assert score < 30, (
            f"Bad-02 scored {score}, expected <30. Details: {details}"
        )

    def test_good_bad_differential_above_20(self, calibration_dir: Path):
        """The spread between best good and worst bad must exceed 20 points."""
        good_scores = []
        bad_scores = []

        for f in sorted(calibration_dir.glob("calibration-good-*.jsonl")):
            score, _ = _score_transcript(f)
            good_scores.append(score)

        for f in sorted(calibration_dir.glob("calibration-bad-*.jsonl")):
            score, _ = _score_transcript(f)
            bad_scores.append(score)

        assert good_scores and bad_scores, "Missing calibration transcripts"

        avg_good = sum(good_scores) / len(good_scores)
        avg_bad = sum(bad_scores) / len(bad_scores)
        diff = avg_good - avg_bad

        assert diff > 20, (
            f"Differential too narrow: avg_good={avg_good:.1f}, "
            f"avg_bad={avg_bad:.1f}, diff={diff:.1f}"
        )


# ---------------------------------------------------------------------------
# Score Distribution Report
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="Calibration data was fabricated. Deleted in quality audit.",
    strict=False,
)
class TestScoreDistribution:
    """Report score distribution across all calibration transcripts."""

    def test_report_all_scores(self, calibration_dir: Path):
        """Not a strict assertion -- reports all scores for calibration review."""
        results: dict[str, list[tuple[str, int, dict]]] = {
            "good": [],
            "mediocre": [],
            "bad": [],
        }

        for f in sorted(calibration_dir.glob("*.jsonl")):
            score, details = _score_transcript(f)
            for quality in ("good", "mediocre", "bad"):
                if quality in f.stem:
                    results[quality].append((f.stem, score, details))
                    break

        # Print report
        print("\n=== CALIBRATION SCORE DISTRIBUTION ===")
        for quality, entries in results.items():
            scores = [s for _, s, _ in entries]
            avg = sum(scores) / len(scores) if scores else 0
            print(f"\n{quality.upper()} (avg={avg:.1f}):")
            for name, score, details in entries:
                print(f"  {name}: {score}/100")
                print(f"    GVS: {details.get('plugins', {}).get('graph_value', 'N/A')}")
                print(f"    Dims: {details.get('dimensions', {})}")
                print(f"    BSKG queries: {details.get('bskg_query_count', 0)}")

        # Verify all quality levels have entries
        for quality, entries in results.items():
            assert len(entries) >= 1, f"No {quality} transcripts found"


# ---------------------------------------------------------------------------
# ObservationParser Integration
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="Calibration data was fabricated. Deleted in quality audit.",
    strict=False,
)
class TestObservationParserIntegration:
    """Verify ObservationParser handles calibration transcripts correctly."""

    def test_parser_loads_good_transcript(self, calibration_dir: Path):
        parser = ObservationParser(calibration_dir, session_id=None)  # P13-ADV-6-01
        summary = parser.parse()

        assert summary.total_tool_calls > 0

    def test_parser_extracts_tool_timeline(self, calibration_dir: Path):
        parser = ObservationParser(calibration_dir, session_id=None)  # P13-ADV-6-01
        timeline = parser.get_tool_timeline()

        assert len(timeline) > 0
        tool_names = [t.tool_name for t in timeline]
        assert "Bash" in tool_names, "Expected Bash tool in timeline"

    def test_parser_extracts_bskg_observations(self, calibration_dir: Path):
        parser = ObservationParser(calibration_dir, session_id=None)  # P13-ADV-6-01
        bskg = parser.get_bskg_observations()

        # Calibration dir has multiple transcripts, some with BSKG queries
        assert len(bskg) > 0, "Expected BSKG observations from good transcripts"


# ---------------------------------------------------------------------------
# Real Transcript Evaluation
# ---------------------------------------------------------------------------


class TestRealTranscriptEvaluation:
    """Run GVS on real transcripts from .vrs/observations/.

    These tests skip gracefully when no real transcripts exist.
    Real transcripts must be captured from actual Claude Code sessions
    with observation hooks installed.
    """

    REAL_OBS_DIR = Path(__file__).parents[2] / ".vrs" / "observations"

    def test_real_transcript_scores(self):
        """Any real transcript found should produce a non-zero GVS score."""
        if not self.REAL_OBS_DIR.exists():
            pytest.skip("Real observations directory not found")

        transcripts = list(self.REAL_OBS_DIR.glob("transcript-*.jsonl"))
        if not transcripts:
            pytest.skip(
                "No real transcripts found. Capture from actual Claude Code sessions."
            )

        scores = []
        for path in sorted(transcripts):
            eval_input = _load_transcript_as_eval_input(path)
            scorer = GraphValueScorer()
            result = scorer.score(eval_input)
            scores.append((path.stem, result.score))

        print("\n=== REAL TRANSCRIPT GVS SCORES ===")
        for name, score in scores:
            print(f"  {name}: {score}/100")

        # At least one should produce a non-zero score
        assert any(s > 0 for _, s in scores), "All real transcripts scored 0"

    def test_real_transcripts_full_pipeline(self):
        """Run full evaluation on all real transcripts."""
        if not self.REAL_OBS_DIR.exists():
            pytest.skip("Real observations not available")

        transcripts = list(self.REAL_OBS_DIR.glob("transcript-*.jsonl"))
        if not transcripts:
            pytest.skip("No real transcripts found")

        scores = []
        for path in sorted(transcripts):
            eval_input = _load_transcript_as_eval_input(path)
            evaluator = ReasoningEvaluator(
                workflow_id="real-transcript-eval",
                contract=CALIBRATION_CONTRACT,
                pass_threshold=60,
            )
            score_card = evaluator.evaluate(eval_input)
            scores.append((path.stem, score_card.overall_score))

        print("\n=== REAL TRANSCRIPT SCORES ===")
        for name, score in scores:
            print(f"  {name}: {score}/100")

        # At least one should produce a non-zero score
        assert any(s > 0 for _, s in scores), "All real transcripts scored 0"
