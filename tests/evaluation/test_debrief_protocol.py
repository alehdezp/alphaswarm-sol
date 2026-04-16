"""Tests for 3.1c-05 Debrief Protocol.

Verifies:
- 4-layer cascade (send_message -> hook_gate -> transcript -> skip)
- Disk-read path: write artifact, verify runner reads it
- Compaction branching: 3 vs 7 questions
- Dead agent detection: absent artifact -> send_message_no_response
- Fence stripping: ```json wrapper removed correctly
- Confidence fix: gate with no answers = LOW_CONFIDENCE
- delivery_status: phantom vs not_attempted distinction
- DebriefResponseValidator sentinel values
"""

from __future__ import annotations

import json
from pathlib import Path

from alphaswarm_sol.testing.evaluation.models import DebriefResponse
from tests.workflow_harness.lib.debrief_protocol import (
    DEFAULT_DEBRIEF_QUESTIONS,
    FULL_DEBRIEF_QUESTIONS,
    LAYER_NAMES,
    SHORT_DEBRIEF_QUESTIONS,
    DebriefStatus,
    LayerResult,
    attempt_hook_gate_layer,
    attempt_send_message_layer,
    attempt_skip_layer,
    attempt_transcript_layer,
    classify_debrief,
    get_debrief_questions,
    run_debrief,
    validate_debrief_response,
)


# ---------------------------------------------------------------------------
# DebriefResponseValidator
# ---------------------------------------------------------------------------


class TestDebriefResponseValidator:
    def test_valid_json_parses(self):
        raw = json.dumps({"answers": ["a1", "a2"], "confidence": 0.9})
        result = validate_debrief_response(raw)
        assert result["valid"] is True
        assert result["layer_used"] == "send_message"
        assert result["data"]["answers"] == ["a1", "a2"]

    def test_fenced_json_stripped(self):
        raw = '```json\n{"answers": ["fenced"]}\n```'
        result = validate_debrief_response(raw)
        assert result["valid"] is True
        assert result["data"]["answers"] == ["fenced"]

    def test_fenced_json_no_language_tag(self):
        raw = '```\n{"answers": ["nolang"]}\n```'
        result = validate_debrief_response(raw)
        assert result["valid"] is True
        assert result["data"]["answers"] == ["nolang"]

    def test_malformed_json_returns_sentinel(self):
        raw = '```json\n{not valid json}\n```'
        result = validate_debrief_response(raw)
        assert result["valid"] is False
        assert result["layer_used"] == "send_message_malformed"
        assert "JSON parse error" in result["error"]

    def test_empty_response_returns_no_response(self):
        result = validate_debrief_response("")
        assert result["valid"] is False
        assert result["layer_used"] == "send_message_no_response"

    def test_none_response_returns_no_response(self):
        result = validate_debrief_response(None)  # type: ignore[arg-type]
        assert result["valid"] is False
        assert result["layer_used"] == "send_message_no_response"

    def test_whitespace_only_returns_no_response(self):
        result = validate_debrief_response("   \n  ")
        assert result["valid"] is False
        assert result["layer_used"] == "send_message_no_response"


# ---------------------------------------------------------------------------
# Layer 1: SendMessage (disk-read path)
# ---------------------------------------------------------------------------


class TestSendMessageLayer:
    def test_simulated_mode_fails(self):
        result = attempt_send_message_layer("attacker", ["Q1"], simulated=True)
        assert result.success is False
        assert result.layer_name == "send_message"
        assert result.delivery_status == "not_attempted"

    def test_non_simulated_no_session_id_fails(self):
        result = attempt_send_message_layer(
            "attacker", ["Q1"], simulated=False, session_id=""
        )
        assert result.success is False
        assert result.delivery_status == "not_attempted"

    def test_disk_read_path_loads_artifact(self, tmp_path: Path):
        """Write a fixture artifact to disk, verify runner reads it."""
        obs_dir = tmp_path / "observations"
        obs_dir.mkdir()
        session_id = "test-session-123"
        artifact = {
            "answers": ["My hypothesis was reentrancy", "Used BSKG queries"],
            "confidence": 0.9,
        }
        (obs_dir / f"{session_id}_debrief.json").write_text(json.dumps(artifact))

        result = attempt_send_message_layer(
            "attacker",
            ["Q1", "Q2"],
            simulated=False,
            session_id=session_id,
            obs_dir=obs_dir,
        )
        assert result.success is True
        assert result.layer_name == "send_message"
        assert result.answers == ["My hypothesis was reentrancy", "Used BSKG queries"]
        assert result.confidence == 0.9
        assert result.delivery_status == "delivered"

    def test_disk_read_fenced_artifact(self, tmp_path: Path):
        """Artifact wrapped in ```json fences should be parsed correctly."""
        obs_dir = tmp_path / "observations"
        obs_dir.mkdir()
        session_id = "fenced-session"
        raw = '```json\n{"answers": ["fenced answer"]}\n```'
        (obs_dir / f"{session_id}_debrief.json").write_text(raw)

        result = attempt_send_message_layer(
            "attacker",
            ["Q1"],
            simulated=False,
            session_id=session_id,
            obs_dir=obs_dir,
        )
        assert result.success is True
        assert result.answers == ["fenced answer"]

    def test_dead_agent_no_artifact(self, tmp_path: Path):
        """SendMessage returned success but no artifact was written -> phantom."""
        obs_dir = tmp_path / "observations"
        obs_dir.mkdir()
        # No artifact file written

        result = attempt_send_message_layer(
            "attacker",
            ["Q1"],
            simulated=False,
            session_id="dead-agent",
            obs_dir=obs_dir,
        )
        assert result.success is False
        assert result.layer_name == "send_message_no_response"
        assert result.delivery_status == "phantom"

    def test_malformed_artifact(self, tmp_path: Path):
        """Artifact exists but contains invalid JSON -> malformed."""
        obs_dir = tmp_path / "observations"
        obs_dir.mkdir()
        session_id = "malformed-session"
        (obs_dir / f"{session_id}_debrief.json").write_text("not json at all {{{")

        result = attempt_send_message_layer(
            "attacker",
            ["Q1"],
            simulated=False,
            session_id=session_id,
            obs_dir=obs_dir,
        )
        assert result.success is False
        assert result.layer_name == "send_message_malformed"
        assert result.delivery_status == "delivered"  # file existed, just malformed


# ---------------------------------------------------------------------------
# Layer 2: Hook Gate
# ---------------------------------------------------------------------------


class TestHookGateLayer:
    def test_no_obs_dir_fails(self):
        result = attempt_hook_gate_layer("attacker", ["Q1"], obs_dir=None)
        assert result.success is False
        assert result.delivery_status == "not_attempted"

    def test_nonexistent_obs_dir_fails(self, tmp_path: Path):
        result = attempt_hook_gate_layer(
            "attacker", ["Q1"], obs_dir=tmp_path / "nonexistent"
        )
        assert result.success is False

    def test_empty_obs_dir_fails(self, tmp_path: Path):
        obs_dir = tmp_path / "obs"
        obs_dir.mkdir()
        result = attempt_hook_gate_layer("attacker", ["Q1"], obs_dir=obs_dir)
        assert result.success is False

    def test_with_task_completed_observation(self, tmp_path: Path):
        obs_dir = tmp_path / "obs"
        obs_dir.mkdir()
        jsonl = obs_dir / "sess.jsonl"
        record = {
            "timestamp": "T1",
            "session_id": "s",
            "event_type": "task_completed",
            "hook_name": "h",
            "data": {"task_id": "t1", "task_subject": "Investigate vuln"},
        }
        jsonl.write_text(json.dumps(record) + "\n")

        result = attempt_hook_gate_layer("attacker", ["Q1"], obs_dir=obs_dir)
        assert result.success is True
        assert result.layer_name == "hook_gate"
        assert result.confidence == 0.6
        assert result.delivery_status == "delivered"

    def test_with_agent_stop_observation(self, tmp_path: Path):
        obs_dir = tmp_path / "obs"
        obs_dir.mkdir()
        jsonl = obs_dir / "sess.jsonl"
        record = {
            "timestamp": "T1",
            "session_id": "s",
            "event_type": "agent_stop",
            "hook_name": "h",
            "data": {"agent_id": "attacker"},
        }
        jsonl.write_text(json.dumps(record) + "\n")

        result = attempt_hook_gate_layer("attacker", ["Q1"], obs_dir=obs_dir)
        assert result.success is True

    def test_agent_stop_for_different_agent_no_match(self, tmp_path: Path):
        obs_dir = tmp_path / "obs"
        obs_dir.mkdir()
        jsonl = obs_dir / "sess.jsonl"
        record = {
            "timestamp": "T1",
            "session_id": "s",
            "event_type": "agent_stop",
            "hook_name": "h",
            "data": {"agent_id": "defender"},
        }
        jsonl.write_text(json.dumps(record) + "\n")

        result = attempt_hook_gate_layer("attacker", ["Q1"], obs_dir=obs_dir)
        assert result.success is False


# ---------------------------------------------------------------------------
# Layer 3: Transcript Analysis
# ---------------------------------------------------------------------------


class TestTranscriptLayer:
    def test_no_transcript_fails(self):
        result = attempt_transcript_layer("attacker", ["Q1"], transcript_path=None)
        assert result.success is False

    def test_nonexistent_transcript_fails(self, tmp_path: Path):
        result = attempt_transcript_layer(
            "attacker", ["Q1"], transcript_path=tmp_path / "missing.jsonl"
        )
        assert result.success is False

    def test_empty_transcript_fails(self, tmp_path: Path):
        t = tmp_path / "transcript.txt"
        t.write_text("")
        result = attempt_transcript_layer("attacker", ["Q1"], transcript_path=t)
        assert result.success is False
        assert "empty" in result.error.lower()

    def test_transcript_with_hypothesis_content(self, tmp_path: Path):
        t = tmp_path / "transcript.txt"
        t.write_text(
            "My hypothesis was to focus on reentrancy first.\n"
            "I ran alphaswarm query to find entry points.\n"
            "Evidence: found vulnerability in withdraw().\n"
        )

        questions = [
            "What was your primary hypothesis?",
            "What BSKG queries informed your analysis?",
            "What evidence supports your conclusion?",
        ]
        result = attempt_transcript_layer("attacker", questions, transcript_path=t)
        assert result.success is True
        assert result.layer_name == "transcript_analysis"
        assert result.confidence == 0.3
        assert len(result.answers) == 3
        assert "hypothesis" in result.answers[0].lower() or "reentrancy" in result.answers[0].lower()
        assert result.delivery_status == "delivered"

    def test_transcript_raw_response_truncated(self, tmp_path: Path):
        t = tmp_path / "transcript.txt"
        t.write_text("x" * 5000)
        result = attempt_transcript_layer("attacker", ["Q1"], transcript_path=t)
        assert result.success is True
        assert len(result.raw_response) <= 2000


# ---------------------------------------------------------------------------
# Layer 4: Skip
# ---------------------------------------------------------------------------


class TestSkipLayer:
    def test_always_succeeds(self):
        result = attempt_skip_layer("attacker", ["Q1", "Q2"])
        assert result.success is True
        assert result.layer_name == "skip"
        assert result.confidence == 0.0
        assert len(result.answers) == 2
        assert result.delivery_status == "not_attempted"


# ---------------------------------------------------------------------------
# Compaction-Aware Question Selection
# ---------------------------------------------------------------------------


class TestCompactionBranching:
    def test_no_marker_returns_7_questions(self, tmp_path: Path):
        questions, compacted = get_debrief_questions("sess-1", tmp_path)
        assert len(questions) == 7
        assert compacted is False
        assert questions == FULL_DEBRIEF_QUESTIONS

    def test_with_marker_returns_3_questions(self, tmp_path: Path):
        (tmp_path / "sess-2.compacted").touch()
        questions, compacted = get_debrief_questions("sess-2", tmp_path)
        assert len(questions) == 3
        assert compacted is True
        assert questions == SHORT_DEBRIEF_QUESTIONS

    def test_no_obs_dir_returns_full(self):
        questions, compacted = get_debrief_questions("sess-3", None)
        assert len(questions) == 7
        assert compacted is False

    def test_run_debrief_compacted_session(self, tmp_path: Path):
        """run_debrief with compacted session uses 3 questions."""
        obs_dir = tmp_path / "obs"
        obs_dir.mkdir()
        (obs_dir / "compacted-sess.compacted").touch()

        response = run_debrief(
            agent_name="attacker",
            agent_type="vrs-attacker",
            obs_dir=obs_dir,
            session_id="compacted-sess",
            simulated=True,
        )
        assert response.compacted is True
        assert len(response.questions) == 3
        assert response.questions == SHORT_DEBRIEF_QUESTIONS

    def test_run_debrief_non_compacted_session(self, tmp_path: Path):
        """run_debrief without compacted marker uses 7 questions."""
        obs_dir = tmp_path / "obs"
        obs_dir.mkdir()

        response = run_debrief(
            agent_name="attacker",
            agent_type="vrs-attacker",
            obs_dir=obs_dir,
            session_id="normal-sess",
            simulated=True,
        )
        assert response.compacted is False
        assert len(response.questions) == 7


# ---------------------------------------------------------------------------
# Confidence Classification
# ---------------------------------------------------------------------------


class TestConfidenceClassification:
    def test_send_message_high_confidence(self):
        debrief = DebriefResponse(
            agent_name="a",
            agent_type="t",
            layer_used="send_message",
            questions=["Q"],
            answers=["A"],
        )
        assert classify_debrief(debrief) == DebriefStatus.HIGH_CONFIDENCE

    def test_hook_gate_with_answers_medium(self):
        debrief = DebriefResponse(
            agent_name="a",
            agent_type="t",
            layer_used="hook_gate",
            questions=["Q"],
            answers=["Real answer"],
        )
        assert classify_debrief(debrief) == DebriefStatus.MEDIUM_CONFIDENCE

    def test_hook_gate_no_answers_low(self):
        """Gate fired but no real answers -> LOW not MEDIUM."""
        debrief = DebriefResponse(
            agent_name="a",
            agent_type="t",
            layer_used="hook_gate",
            questions=["Q"],
            answers=[],
        )
        assert classify_debrief(debrief) == DebriefStatus.LOW_CONFIDENCE

    def test_hook_gate_placeholder_answers_low(self):
        """Gate fired but only placeholder answers -> LOW."""
        debrief = DebriefResponse(
            agent_name="a",
            agent_type="t",
            layer_used="hook_gate",
            questions=["Q"],
            answers=["[No answer]"],
        )
        assert classify_debrief(debrief) == DebriefStatus.LOW_CONFIDENCE

    def test_transcript_low(self):
        debrief = DebriefResponse(
            agent_name="a",
            agent_type="t",
            layer_used="transcript_analysis",
            questions=["Q"],
            answers=["inferred"],
        )
        assert classify_debrief(debrief) == DebriefStatus.LOW_CONFIDENCE

    def test_malformed_low(self):
        debrief = DebriefResponse(
            agent_name="a",
            agent_type="t",
            layer_used="send_message_malformed",
            questions=["Q"],
            answers=[],
        )
        assert classify_debrief(debrief) == DebriefStatus.LOW_CONFIDENCE

    def test_no_response_low(self):
        debrief = DebriefResponse(
            agent_name="a",
            agent_type="t",
            layer_used="send_message_no_response",
            questions=["Q"],
            answers=[],
        )
        assert classify_debrief(debrief) == DebriefStatus.LOW_CONFIDENCE

    def test_skip_no_data(self):
        debrief = DebriefResponse(
            agent_name="a",
            agent_type="t",
            layer_used="skip",
            questions=["Q"],
            answers=["[No debrief data available]"],
        )
        assert classify_debrief(debrief) == DebriefStatus.NO_DATA


# ---------------------------------------------------------------------------
# delivery_status Tests
# ---------------------------------------------------------------------------


class TestDeliveryStatus:
    def test_phantom_when_artifact_absent(self, tmp_path: Path):
        """Absent artifact after wait -> phantom delivery_status."""
        obs_dir = tmp_path / "obs"
        obs_dir.mkdir()

        result = attempt_send_message_layer(
            "attacker",
            ["Q1"],
            simulated=False,
            session_id="dead",
            obs_dir=obs_dir,
        )
        assert result.delivery_status == "phantom"

    def test_not_attempted_when_simulated(self):
        result = attempt_send_message_layer("attacker", ["Q1"], simulated=True)
        assert result.delivery_status == "not_attempted"

    def test_delivered_when_artifact_parsed(self, tmp_path: Path):
        obs_dir = tmp_path / "obs"
        obs_dir.mkdir()
        (obs_dir / "good_debrief.json").write_text('{"answers": ["ok"]}')
        # Note: artifact name is {session_id}_debrief.json
        (obs_dir / "s1_debrief.json").write_text('{"answers": ["ok"]}')

        result = attempt_send_message_layer(
            "attacker",
            ["Q1"],
            simulated=False,
            session_id="s1",
            obs_dir=obs_dir,
        )
        assert result.delivery_status == "delivered"

    def test_run_debrief_propagates_delivery_status(self):
        """delivery_status flows through to DebriefResponse."""
        response = run_debrief(
            agent_name="x",
            agent_type="t",
            simulated=True,
        )
        assert response.delivery_status == "not_attempted"


# ---------------------------------------------------------------------------
# Cascade Orchestrator
# ---------------------------------------------------------------------------


class TestRunDebrief:
    def test_simulated_falls_through_to_skip(self):
        response = run_debrief(
            agent_name="attacker",
            agent_type="vrs-attacker",
            simulated=True,
        )
        assert isinstance(response, DebriefResponse)
        assert response.agent_name == "attacker"
        assert response.agent_type == "vrs-attacker"
        assert response.layer_used == "skip"
        assert response.confidence == 0.0

    def test_cascade_send_message_wins_in_live(self, tmp_path: Path):
        """When artifact exists, send_message layer wins over hook_gate."""
        obs_dir = tmp_path / "obs"
        obs_dir.mkdir()
        session_id = "cascade-test"

        # Write both: artifact AND hook observation
        artifact = {"answers": ["from send_message"]}
        (obs_dir / f"{session_id}_debrief.json").write_text(json.dumps(artifact))

        jsonl = obs_dir / "sess.jsonl"
        record = {
            "timestamp": "T1",
            "session_id": "s",
            "event_type": "task_completed",
            "hook_name": "h",
            "data": {"task_id": "t1"},
        }
        jsonl.write_text(json.dumps(record) + "\n")

        response = run_debrief(
            agent_name="attacker",
            agent_type="vrs-attacker",
            obs_dir=obs_dir,
            simulated=False,
            session_id=session_id,
        )
        # send_message should win over hook_gate
        assert response.layer_used == "send_message"
        assert response.answers[0] == "from send_message"

    def test_cascade_falls_to_hook_gate(self, tmp_path: Path):
        """When no artifact but hook observations exist, hook_gate wins."""
        obs_dir = tmp_path / "obs"
        obs_dir.mkdir()

        jsonl = obs_dir / "sess.jsonl"
        record = {
            "timestamp": "T1",
            "session_id": "s",
            "event_type": "task_completed",
            "hook_name": "h",
            "data": {"task_id": "t1"},
        }
        jsonl.write_text(json.dumps(record) + "\n")

        response = run_debrief(
            agent_name="attacker",
            agent_type="vrs-attacker",
            obs_dir=obs_dir,
            simulated=True,
        )
        assert response.layer_used == "hook_gate"
        assert response.confidence == 0.6

    def test_cascade_falls_to_transcript(self, tmp_path: Path):
        t = tmp_path / "transcript.txt"
        t.write_text("My approach was strategy-based.\n")

        response = run_debrief(
            agent_name="defender",
            agent_type="vrs-defender",
            transcript_path=t,
            simulated=True,
        )
        assert response.layer_used == "transcript_analysis"
        assert response.confidence == 0.3

    def test_default_questions_used(self):
        response = run_debrief(
            agent_name="x",
            agent_type="t",
            simulated=True,
        )
        assert response.questions == FULL_DEBRIEF_QUESTIONS
        assert len(response.answers) == len(FULL_DEBRIEF_QUESTIONS)

    def test_custom_questions(self):
        qs = ["Custom Q1?", "Custom Q2?"]
        response = run_debrief(
            agent_name="x",
            agent_type="t",
            questions=qs,
            simulated=True,
        )
        assert response.questions == qs
        assert len(response.answers) == 2

    def test_answers_padded_to_match_questions(self, tmp_path: Path):
        """If a layer returns fewer answers than questions, pad with [No answer]."""
        obs_dir = tmp_path / "obs"
        obs_dir.mkdir()
        jsonl = obs_dir / "sess.jsonl"
        record = {
            "timestamp": "T1",
            "session_id": "s",
            "event_type": "task_completed",
            "hook_name": "h",
            "data": {"task_id": "t1"},
        }
        jsonl.write_text(json.dumps(record) + "\n")

        response = run_debrief(
            agent_name="attacker",
            agent_type="vrs-attacker",
            questions=["Q1", "Q2", "Q3"],
            obs_dir=obs_dir,
            simulated=True,
        )
        assert len(response.answers) == 3


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_full_questions_count(self):
        assert len(FULL_DEBRIEF_QUESTIONS) == 7

    def test_short_questions_count(self):
        assert len(SHORT_DEBRIEF_QUESTIONS) == 3

    def test_default_is_full(self):
        assert DEFAULT_DEBRIEF_QUESTIONS == FULL_DEBRIEF_QUESTIONS

    def test_layer_names(self):
        assert LAYER_NAMES == ("send_message", "hook_gate", "transcript_analysis", "skip")

    def test_layer_result_dataclass(self):
        lr = LayerResult(layer_name="test", success=True, confidence=0.5)
        assert lr.layer_name == "test"
        assert lr.success is True
        assert lr.confidence == 0.5
        assert lr.answers == []
        assert lr.delivery_status == "not_attempted"
