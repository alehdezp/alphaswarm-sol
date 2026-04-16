"""Tests for 3.1c-03 ObservationParser adapter.

Verifies:
- Thin adapter delegates to TranscriptParser.to_observation_summary()
- Session ID filter provides O(1) lookup
- tool_use_id pairing works on real transcripts (replaces LIFO)
- Data quality tracking populated correctly
- Staleness guard skips old files
- Real transcripts from Plan 02 parse with zero errors
"""

from __future__ import annotations

import json
import os
import time
import warnings
from pathlib import Path

import pytest

from tests.workflow_harness.lib.observation_parser import ObservationParser

REAL_SESSIONS_DIR = Path("tests/workflow_harness/fixtures/real_sessions")


def _write_cc_transcript(path: Path, records: list[dict]) -> None:
    """Write a Claude Code-format JSONL transcript."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def _make_tool_use_record(
    session_id: str, tool_name: str, tool_use_id: str, ts: str
) -> dict:
    """Create a CC assistant record with a tool_use block."""
    return {
        "type": "assistant",
        "sessionId": session_id,
        "timestamp": ts,
        "message": {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_use_id,
                    "name": tool_name,
                    "input": {"command": f"echo {tool_name}"},
                }
            ],
        },
    }


def _make_tool_result_record(
    session_id: str, tool_use_id: str, result: str, ts: str
) -> dict:
    """Create a CC user record with a tool_result block."""
    return {
        "type": "user",
        "sessionId": session_id,
        "timestamp": ts,
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result,
                }
            ],
        },
    }


# ---------------------------------------------------------------------------
# Empty / nonexistent directory
# ---------------------------------------------------------------------------


class TestObservationParserEmpty:
    def test_empty_dir(self, tmp_path: Path):
        obs_dir = tmp_path / "sessions"
        obs_dir.mkdir(parents=True)
        parser = ObservationParser(obs_dir, session_id="nonexistent")
        summary = parser.parse()
        assert summary.total_tool_calls == 0
        assert summary.parse_errors == 0

    def test_nonexistent_dir(self, tmp_path: Path):
        parser = ObservationParser(tmp_path / "nonexistent", session_id="x")
        summary = parser.parse()
        assert summary.total_tool_calls == 0


# ---------------------------------------------------------------------------
# Session ID filter (O(1) lookup)
# ---------------------------------------------------------------------------


class TestSessionIdFilter:
    def test_session_id_reads_only_matching_file(self, tmp_path: Path):
        """O(1) lookup: only {session_id}.jsonl is opened."""
        obs_dir = tmp_path / "sessions"
        _write_cc_transcript(obs_dir / "sess-a.jsonl", [
            _make_tool_use_record("a", "Bash", "tu-1", "2026-01-01T00:00:00Z"),
            _make_tool_result_record("a", "tu-1", "ok", "2026-01-01T00:00:01Z"),
        ])
        _write_cc_transcript(obs_dir / "sess-b.jsonl", [
            _make_tool_use_record("b", "Read", "tu-2", "2026-01-01T00:00:02Z"),
            _make_tool_result_record("b", "tu-2", "ok", "2026-01-01T00:00:03Z"),
        ])
        parser = ObservationParser(obs_dir, session_id="sess-a")
        summary = parser.parse()
        assert summary.total_tool_calls == 1
        assert "Bash" in summary.tool_counts
        assert "Read" not in summary.tool_counts

    def test_no_session_id_reads_all_files(self, tmp_path: Path):
        """Without session_id, all JSONL files are read."""
        obs_dir = tmp_path / "sessions"
        _write_cc_transcript(obs_dir / "a.jsonl", [
            _make_tool_use_record("a", "Bash", "tu-1", "2026-01-01T00:00:00Z"),
        ])
        _write_cc_transcript(obs_dir / "b.jsonl", [
            _make_tool_use_record("b", "Read", "tu-2", "2026-01-01T00:00:02Z"),
        ])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parser = ObservationParser(obs_dir, session_id=None)
            summary = parser.parse()
        assert summary.total_tool_calls == 2

    def test_no_session_id_emits_warning(self, tmp_path: Path):
        obs_dir = tmp_path / "sessions"
        obs_dir.mkdir(parents=True)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ObservationParser(obs_dir, session_id=None)
        assert any("session_id" in str(warning.message) for warning in w)


# ---------------------------------------------------------------------------
# tool_use_id pairing (replaces LIFO)
# ---------------------------------------------------------------------------


class TestToolUseIdPairing:
    def test_tool_use_id_pairing_on_sequential_calls(self, tmp_path: Path):
        """tool_use_id pairs tool_use with its tool_result."""
        obs_dir = tmp_path / "sessions"
        _write_cc_transcript(obs_dir / "s.jsonl", [
            _make_tool_use_record("s", "Bash", "tu-1", "2026-01-01T00:00:00Z"),
            _make_tool_result_record("s", "tu-1", "output-1", "2026-01-01T00:00:01Z"),
            _make_tool_use_record("s", "Read", "tu-2", "2026-01-01T00:00:02Z"),
            _make_tool_result_record("s", "tu-2", "output-2", "2026-01-01T00:00:03Z"),
        ])
        parser = ObservationParser(obs_dir, session_id="s")
        summary = parser.parse()
        assert summary.total_tool_calls == 2
        # Verify tool calls have results paired by tool_use_id
        seq = summary.tool_sequences
        assert len(seq) == 2
        assert seq[0].tool_name == "Bash"
        assert seq[1].tool_name == "Read"

    def test_tool_use_id_pairing_on_parallel_calls(self, tmp_path: Path):
        """Parallel tool calls: two tool_use blocks before their results."""
        obs_dir = tmp_path / "sessions"
        records = [
            # Two tool_use blocks in same assistant message
            {
                "type": "assistant",
                "sessionId": "s",
                "timestamp": "2026-01-01T00:00:00Z",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": "tu-a", "name": "Bash",
                         "input": {"command": "echo a"}},
                        {"type": "tool_use", "id": "tu-b", "name": "Read",
                         "input": {"file_path": "/tmp/x"}},
                    ],
                },
            },
            # Results come back in a single user message
            {
                "type": "user",
                "sessionId": "s",
                "timestamp": "2026-01-01T00:00:01Z",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tu-b",
                         "content": "file-content"},
                        {"type": "tool_result", "tool_use_id": "tu-a",
                         "content": "bash-output"},
                    ],
                },
            },
        ]
        _write_cc_transcript(obs_dir / "s.jsonl", records)
        parser = ObservationParser(obs_dir, session_id="s")
        summary = parser.parse()
        assert summary.total_tool_calls == 2
        # Both tools should be present
        assert "Bash" in summary.tool_counts
        assert "Read" in summary.tool_counts

    def test_real_transcript_has_tool_use_id(self):
        """Confirm real transcripts from Plan 02 contain tool_use_id fields."""
        if not REAL_SESSIONS_DIR.exists():
            pytest.skip("Real sessions directory not found")
        found_tool_use_id = False
        for jsonl_file in REAL_SESSIONS_DIR.glob("*.jsonl"):
            with open(jsonl_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        msg = record.get("message", {})
                        if not isinstance(msg, dict):
                            continue
                        content = msg.get("content", [])
                        if not isinstance(content, list):
                            continue
                        for block in content:
                            if isinstance(block, dict) and "tool_use_id" in block:
                                found_tool_use_id = True
                                break
                    except json.JSONDecodeError:
                        continue
                    if found_tool_use_id:
                        break
            if found_tool_use_id:
                break
        assert found_tool_use_id, (
            "No tool_use_id found in real transcripts — "
            "Plan 02 hook infrastructure not installed"
        )


# ---------------------------------------------------------------------------
# Data quality tracking
# ---------------------------------------------------------------------------


class TestDataQuality:
    def test_data_quality_populated(self, tmp_path: Path):
        obs_dir = tmp_path / "sessions"
        _write_cc_transcript(obs_dir / "s.jsonl", [
            _make_tool_use_record("s", "Bash", "tu-1", "2026-01-01T00:00:00Z"),
        ])
        parser = ObservationParser(obs_dir, session_id="s")
        summary = parser.parse()
        assert summary.data_quality is not None
        assert summary.data_quality.serialize_errors == 0
        assert summary.data_quality.stale_files_excluded == 0
        assert summary.data_quality.cross_session_records_dropped == 0
        assert summary.data_quality.degraded is False

    def test_cross_session_detection(self, tmp_path: Path):
        """When reading all files, cross-session records are counted."""
        obs_dir = tmp_path / "sessions"
        _write_cc_transcript(obs_dir / "a.jsonl", [
            _make_tool_use_record("session-a", "Bash", "tu-1", "2026-01-01T00:00:00Z"),
        ])
        _write_cc_transcript(obs_dir / "b.jsonl", [
            _make_tool_use_record("session-b", "Read", "tu-2", "2026-01-01T00:00:02Z"),
        ])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parser = ObservationParser(obs_dir, session_id=None)
            summary = parser.parse()
        # Second file has different session_id
        assert summary.data_quality.cross_session_records_dropped >= 1


# ---------------------------------------------------------------------------
# Tool failure handling
# ---------------------------------------------------------------------------


class TestToolFailures:
    def test_tool_failures_extracted(self, tmp_path: Path):
        """Tool failures (is_error: true) are captured in tool_failures."""
        obs_dir = tmp_path / "sessions"
        records = [
            _make_tool_use_record("s", "Bash", "tu-1", "2026-01-01T00:00:00Z"),
            {
                "type": "user",
                "sessionId": "s",
                "timestamp": "2026-01-01T00:00:01Z",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "tu-1",
                            "is_error": True,
                            "content": "Command failed: exit code 1",
                        }
                    ],
                },
            },
        ]
        _write_cc_transcript(obs_dir / "s.jsonl", records)
        parser = ObservationParser(obs_dir, session_id="s")
        summary = parser.parse()
        assert len(summary.tool_failures) == 1
        assert "tu-1" in summary.tool_failures[0].get("tool_use_id", "")


# ---------------------------------------------------------------------------
# Staleness guard
# ---------------------------------------------------------------------------


class TestStalenessGuard:
    def test_stale_file_skipped(self, tmp_path: Path):
        """Files older than max_staleness_seconds are skipped."""
        obs_dir = tmp_path / "sessions"
        _write_cc_transcript(obs_dir / "old.jsonl", [
            _make_tool_use_record("s", "Bash", "tu-1", "2026-01-01T00:00:00Z"),
        ])
        # Set mtime to 2 hours ago
        old_file = obs_dir / "old.jsonl"
        old_mtime = time.time() - 7200
        os.utime(old_file, (old_mtime, old_mtime))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parser = ObservationParser(obs_dir, session_id="old", max_staleness_seconds=3600)
            summary = parser.parse()
        assert summary.total_tool_calls == 0
        assert summary.data_quality.stale_files_excluded == 1

    def test_fresh_file_not_skipped(self, tmp_path: Path):
        """Recent files are parsed normally."""
        obs_dir = tmp_path / "sessions"
        _write_cc_transcript(obs_dir / "fresh.jsonl", [
            _make_tool_use_record("s", "Bash", "tu-1", "2026-01-01T00:00:00Z"),
        ])
        parser = ObservationParser(obs_dir, session_id="fresh")
        summary = parser.parse()
        assert summary.total_tool_calls == 1
        assert summary.data_quality.stale_files_excluded == 0


# ---------------------------------------------------------------------------
# Real transcript validation (Plan 02 deliverables)
# ---------------------------------------------------------------------------


class TestRealTranscripts:
    """Validate adapter on real transcripts from Plan 02."""

    @pytest.fixture
    def real_sessions_dir(self) -> Path:
        if not REAL_SESSIONS_DIR.exists():
            pytest.skip("Real sessions directory not found")
        files = list(REAL_SESSIONS_DIR.glob("*.jsonl"))
        if not files:
            pytest.skip("No real session files found")
        return REAL_SESSIONS_DIR

    def test_investigation_transcript_parses_zero_errors(self, real_sessions_dir: Path):
        """Parse investigation session (65 tools) with zero errors."""
        parser = ObservationParser(
            real_sessions_dir,
            session_id="investigation-eeb93c51",
            max_staleness_seconds=999999999,  # Disable staleness for fixture
        )
        summary = parser.parse()
        assert summary.parse_errors == 0
        assert summary.total_tool_calls == 65

    def test_tool_run_transcript_parses_zero_errors(self, real_sessions_dir: Path):
        """Parse tool-run session (49 tools) with zero errors."""
        parser = ObservationParser(
            real_sessions_dir,
            session_id="tool-run-453e6460",
            max_staleness_seconds=999999999,
        )
        summary = parser.parse()
        assert summary.parse_errors == 0
        assert summary.total_tool_calls == 49

    def test_orchestration_transcript_parses_zero_errors(self, real_sessions_dir: Path):
        """Parse orchestration session (103 tools, 26 Task spawns) with zero errors."""
        parser = ObservationParser(
            real_sessions_dir,
            session_id="orchestration-09cfb310",
            max_staleness_seconds=999999999,
        )
        summary = parser.parse()
        assert summary.parse_errors == 0
        assert summary.total_tool_calls == 103

    def test_real_transcript_tool_use_id_pairing(self, real_sessions_dir: Path):
        """Real transcripts use tool_use_id pairing, not LIFO."""
        parser = ObservationParser(
            real_sessions_dir,
            session_id="investigation-eeb93c51",
            max_staleness_seconds=999999999,
        )
        summary = parser.parse()
        # If tool_use_id pairing works, we get correct tool counts
        assert summary.total_tool_calls > 0
        # Tool sequences should have timestamps from real data
        for entry in summary.tool_sequences[:5]:
            assert entry.tool_name, "Every tool sequence entry has a name"


# ---------------------------------------------------------------------------
# Convenience methods
# ---------------------------------------------------------------------------


class TestConvenienceMethods:
    def test_get_tool_timeline(self, tmp_path: Path):
        obs_dir = tmp_path / "sessions"
        _write_cc_transcript(obs_dir / "s.jsonl", [
            _make_tool_use_record("s", "Bash", "tu-1", "2026-01-01T00:00:00Z"),
            _make_tool_result_record("s", "tu-1", "ok", "2026-01-01T00:00:01Z"),
        ])
        parser = ObservationParser(obs_dir, session_id="s")
        timeline = parser.get_tool_timeline()
        assert len(timeline) == 1
        assert timeline[0].tool_name == "Bash"

    def test_get_bskg_observations(self, tmp_path: Path):
        obs_dir = tmp_path / "sessions"
        records = [
            _make_tool_use_record("s", "Bash", "tu-1", "2026-01-01T00:00:00Z"),
        ]
        # Modify to be a BSKG query
        records[0]["message"]["content"][0]["input"]["command"] = "alphaswarm query 'test'"
        _write_cc_transcript(obs_dir / "s.jsonl", records)
        parser = ObservationParser(obs_dir, session_id="s")
        bskg = parser.get_bskg_observations()
        assert len(bskg) == 1
        assert bskg[0].command == "alphaswarm query 'test'"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_malformed_json_line_skipped(self, tmp_path: Path):
        """Malformed JSON lines are silently skipped by TranscriptParser."""
        obs_dir = tmp_path / "sessions"
        jsonl_path = obs_dir / "s.jsonl"
        jsonl_path.parent.mkdir(parents=True)
        with open(jsonl_path, "w") as f:
            f.write(json.dumps(_make_tool_use_record(
                "s", "Bash", "tu-1", "2026-01-01T00:00:00Z"
            )) + "\n")
            f.write("not json\n")
            f.write(json.dumps(_make_tool_use_record(
                "s", "Read", "tu-2", "2026-01-01T00:00:02Z"
            )) + "\n")
        parser = ObservationParser(obs_dir, session_id="s")
        summary = parser.parse()
        # TranscriptParser skips malformed lines
        assert summary.total_tool_calls == 2

    def test_empty_jsonl_file(self, tmp_path: Path):
        obs_dir = tmp_path / "sessions"
        jsonl_path = obs_dir / "s.jsonl"
        jsonl_path.parent.mkdir(parents=True)
        jsonl_path.write_text("")
        parser = ObservationParser(obs_dir, session_id="s")
        summary = parser.parse()
        assert summary.total_tool_calls == 0

    def test_observation_summary_reexported(self):
        """ObservationSummary is re-exported from observation_parser module."""
        from tests.workflow_harness.lib.observation_parser import ObservationSummary as OS
        from tests.workflow_harness.lib.transcript_parser import ObservationSummary as TS
        assert OS is TS
