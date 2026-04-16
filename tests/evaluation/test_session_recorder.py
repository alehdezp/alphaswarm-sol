"""Tests for Evaluation Session Recorder and TranscriptSessionExtractor.

Verifies:
- SQLite schema creation and data persistence
- Recording sessions from parsed data
- Querying tool calls, CLI attempts, task actions, violations
- FTS5 full-text search across sessions
- Cross-session pattern aggregation
- Session timeline generation
- TranscriptSessionExtractor: tool extraction, CLI detection, violation detection
- Integration: extractor -> recorder -> query roundtrip
- Basic fallback parse when no extractor is used
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from alphaswarm_sol.testing.evaluation.session_recorder import (
    SessionMetadata,
    SessionRecorder,
)
from alphaswarm_sol.testing.evaluation.transcript_session_extractor import (
    TranscriptSessionExtractor,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_sessions.db"


@pytest.fixture
def recorder(db_path: Path) -> SessionRecorder:
    r = SessionRecorder(db_path=db_path)
    yield r
    r.close()


@pytest.fixture
def sample_metadata() -> SessionMetadata:
    return SessionMetadata(
        teammate_name="attacker-1",
        agent_type="vrs-attacker",
        contract="Vault.sol",
        workflow_id="audit-vault",
        verdict="PASS",
        overall_score=72.5,
    )


@pytest.fixture
def sample_parsed_data() -> dict:
    return {
        "tool_calls": [
            {
                "sequence_num": 0,
                "tool_name": "Read",
                "tool_input": '{"file_path": "contracts/Vault.sol"}',
                "tool_output_excerpt": "pragma solidity ^0.8.0;",
                "timestamp": "2026-03-01T10:00:00Z",
                "blocked": False,
            },
            {
                "sequence_num": 1,
                "tool_name": "Bash",
                "tool_input": '{"command": "uv run alphaswarm build-kg contracts/Vault.sol"}',
                "tool_output_excerpt": "Built graph: 45 nodes, 120 edges",
                "timestamp": "2026-03-01T10:00:05Z",
                "blocked": False,
            },
            {
                "sequence_num": 2,
                "tool_name": "Bash",
                "tool_input": '{"command": "uv run alphaswarm query \\"functions without access control\\""}',
                "tool_output_excerpt": "Found 3 functions: withdraw, transfer, setOwner",
                "timestamp": "2026-03-01T10:00:10Z",
                "blocked": False,
            },
            {
                "sequence_num": 3,
                "tool_name": "TaskCreate",
                "tool_input": '{"subject": "Investigate withdraw reentrancy", "description": "Check withdraw for reentrancy"}',
                "tool_output_excerpt": "",
                "timestamp": "2026-03-01T10:00:15Z",
                "blocked": False,
            },
        ],
        "cli_attempts": [
            {
                "command": "build-kg: uv run alphaswarm build-kg contracts/Vault.sol",
                "full_bash_input": "uv run alphaswarm build-kg contracts/Vault.sol",
                "exit_code": 0,
                "stdout_excerpt": "Built graph: 45 nodes, 120 edges",
                "state": "ATTEMPTED_SUCCESS",
                "timestamp": "2026-03-01T10:00:05Z",
            },
            {
                "command": 'query: uv run alphaswarm query "functions without access control"',
                "full_bash_input": 'uv run alphaswarm query "functions without access control"',
                "exit_code": 0,
                "stdout_excerpt": "Found 3 functions: withdraw, transfer, setOwner",
                "state": "ATTEMPTED_SUCCESS",
                "timestamp": "2026-03-01T10:00:10Z",
            },
        ],
        "task_actions": [
            {
                "action": "create",
                "task_subject": "Investigate withdraw reentrancy",
                "task_description": "Check withdraw for reentrancy",
                "task_status": "pending",
                "timestamp": "2026-03-01T10:00:15Z",
            },
        ],
        "skill_usage": [
            {
                "skill_name": "vrs-audit",
                "was_invoked": True,
                "was_available": True,
                "invocation_result": "success",
            },
        ],
        "violations": [
            {
                "violation_type": "context_read",
                "evidence": "Tool #5 Read: .claude/CLAUDE.md",
                "severity": "critical",
            },
        ],
        "start_time": "2026-03-01T10:00:00Z",
        "end_time": "2026-03-01T10:02:30Z",
        "duration_seconds": 150.0,
    }


# ---------------------------------------------------------------------------
# SessionRecorder: Schema + Recording
# ---------------------------------------------------------------------------


class TestSessionRecorderCreation:
    def test_creates_db_file(self, db_path: Path) -> None:
        recorder = SessionRecorder(db_path=db_path)
        assert db_path.exists()
        recorder.close()

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        deep_path = tmp_path / "a" / "b" / "c" / "sessions.db"
        recorder = SessionRecorder(db_path=deep_path)
        assert deep_path.exists()
        recorder.close()


class TestRecordSession:
    def test_record_returns_session_id(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            session_id = recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            assert session_id
            assert len(session_id) == 36  # UUID format

    def test_session_persisted(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            session_id = recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            session = recorder.get_session(session_id)
            assert session is not None
            assert session["teammate_name"] == "attacker-1"
            assert session["agent_type"] == "vrs-attacker"
            assert session["contract"] == "Vault.sol"
            assert session["workflow_id"] == "audit-vault"
            assert session["verdict"] == "PASS"
            assert session["overall_score"] == 72.5
            assert session["duration_seconds"] == 150.0

    def test_tool_calls_persisted(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            session_id = recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            calls = recorder.query_tool_calls(session_id)
            assert len(calls) == 4
            assert calls[0].tool_name == "Read"
            assert calls[1].tool_name == "Bash"
            assert calls[2].tool_name == "Bash"
            assert calls[3].tool_name == "TaskCreate"

    def test_tool_calls_filtered_by_name(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            session_id = recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            bash_calls = recorder.query_tool_calls(session_id, tool_name="Bash")
            assert len(bash_calls) == 2
            assert all(c.tool_name == "Bash" for c in bash_calls)

    def test_cli_attempts_persisted(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            session_id = recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            attempts = recorder.query_cli_attempts(session_id)
            assert len(attempts) == 2
            assert "build-kg" in attempts[0].command
            assert "query" in attempts[1].command
            assert attempts[0].state == "ATTEMPTED_SUCCESS"
            assert attempts[0].exit_code == 0

    def test_task_actions_persisted(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            session_id = recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            actions = recorder.query_task_actions(session_id)
            assert len(actions) == 1
            assert actions[0].action == "create"
            assert actions[0].task_subject == "Investigate withdraw reentrancy"

    def test_skill_usage_persisted(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            session_id = recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            skills = recorder.query_skill_usage(session_id)
            assert len(skills) == 1
            assert skills[0].skill_name == "vrs-audit"
            assert skills[0].was_invoked is True
            assert skills[0].was_available is True

    def test_violations_persisted(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            session_id = recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            violations = recorder.query_violations(session_id)
            assert len(violations) == 1
            assert violations[0].violation_type == "context_read"
            assert violations[0].severity == "critical"
            assert "CLAUDE.md" in violations[0].evidence


# ---------------------------------------------------------------------------
# FTS5 Search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_tool_calls(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            session_id = recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            results = recorder.search("build-kg")
            assert len(results) > 0
            assert any(r.table_name == "tool_calls" for r in results)

    def test_search_task_actions(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            session_id = recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            results = recorder.search("reentrancy")
            assert len(results) > 0
            assert any(r.table_name == "task_actions" for r in results)

    def test_search_with_session_filter(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            sid1 = recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            sid2 = recorder.record_session(f.name, sample_metadata, sample_parsed_data)

            results = recorder.search("build-kg", session_id=sid1)
            assert all(r.session_id == sid1 for r in results)

    def test_search_no_results(self, recorder: SessionRecorder) -> None:
        results = recorder.search("nonexistent_xyz_query")
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------


class TestTimeline:
    def test_timeline_includes_all_event_types(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            session_id = recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            timeline = recorder.get_session_timeline(session_id)
            event_types = {e.event_type for e in timeline}
            assert "tool_call" in event_types
            assert "cli_attempt" in event_types
            assert "task_action" in event_types
            assert "violation" in event_types

    def test_timeline_sorted_by_timestamp(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            session_id = recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            timeline = recorder.get_session_timeline(session_id)
            timestamps = [e.timestamp for e in timeline if e.timestamp]
            # Timestamps should be in non-decreasing order
            assert timestamps == sorted(timestamps)

    def test_empty_session_timeline(self, recorder: SessionRecorder) -> None:
        timeline = recorder.get_session_timeline("nonexistent-session")
        assert timeline == []


# ---------------------------------------------------------------------------
# Cross-Session Patterns
# ---------------------------------------------------------------------------


class TestCrossSessionPatterns:
    def test_patterns_across_multiple_sessions(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            for _ in range(3):
                recorder.record_session(f.name, sample_metadata, sample_parsed_data)

            report = recorder.get_cross_session_patterns(last_n=10)
            assert report.session_count == 3
            assert report.cli_total == 6  # 2 per session * 3
            assert report.cli_successes == 6
            assert report.cli_success_rate == 1.0
            assert report.total_task_creates == 3
            assert report.empty_task_subjects == 0

    def test_patterns_with_workflow_filter(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            other_meta = SessionMetadata(workflow_id="other-workflow")
            recorder.record_session(f.name, other_meta, sample_parsed_data)

            report = recorder.get_cross_session_patterns(workflow_id="audit-vault", last_n=10)
            assert report.session_count == 1

    def test_patterns_empty(self, recorder: SessionRecorder) -> None:
        report = recorder.get_cross_session_patterns()
        assert report.session_count == 0

    def test_violation_aggregation(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            for _ in range(3):
                recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            report = recorder.get_cross_session_patterns(last_n=10)
            assert len(report.most_common_violations) > 0
            # Each session has 1 context_read violation
            assert ("context_read", 3) in report.most_common_violations


# ---------------------------------------------------------------------------
# List/Get Sessions
# ---------------------------------------------------------------------------


class TestListSessions:
    def test_list_sessions(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            sessions = recorder.list_sessions()
            assert len(sessions) == 2

    def test_get_nonexistent_session(self, recorder: SessionRecorder) -> None:
        assert recorder.get_session("nonexistent") is None


# ---------------------------------------------------------------------------
# TranscriptSessionExtractor
# ---------------------------------------------------------------------------

def _make_jsonl(records: list[dict], path: Path) -> Path:
    """Write records as JSONL."""
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


def _make_assistant_record(tool_calls: list[dict], timestamp: str = "2026-03-01T10:00:00Z") -> dict:
    """Create an assistant record with tool_use blocks."""
    content = []
    for tc in tool_calls:
        content.append({
            "type": "tool_use",
            "id": tc.get("id", f"tool_{id(tc)}"),
            "name": tc["name"],
            "input": tc.get("input", {}),
        })
    return {
        "type": "assistant",
        "timestamp": timestamp,
        "message": {"content": content},
    }


def _make_result_record(tool_id: str, result: str, is_error: bool = False) -> dict:
    """Create a user record with tool_result."""
    return {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result,
                    "is_error": is_error,
                }
            ]
        },
    }


class TestTranscriptSessionExtractor:
    def test_extracts_tool_calls(self, tmp_path: Path) -> None:
        records = [
            _make_assistant_record([
                {"id": "t1", "name": "Read", "input": {"file_path": "Vault.sol"}},
                {"id": "t2", "name": "Bash", "input": {"command": "ls"}},
            ]),
            _make_result_record("t1", "pragma solidity"),
            _make_result_record("t2", "Vault.sol"),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        extractor = TranscriptSessionExtractor(path)
        data = extractor.extract()
        assert len(data["tool_calls"]) == 2
        assert data["tool_calls"][0]["tool_name"] == "Read"
        assert data["tool_calls"][1]["tool_name"] == "Bash"

    def test_extracts_cli_attempts(self, tmp_path: Path) -> None:
        records = [
            _make_assistant_record([
                {"id": "t1", "name": "Bash", "input": {"command": "uv run alphaswarm build-kg contracts/Vault.sol"}},
            ]),
            _make_result_record("t1", "Built graph: 45 nodes, 120 edges"),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        assert len(data["cli_attempts"]) == 1
        assert "build-kg" in data["cli_attempts"][0]["command"]
        assert data["cli_attempts"][0]["state"] == "ATTEMPTED_SUCCESS"

    def test_extracts_failed_cli(self, tmp_path: Path) -> None:
        records = [
            _make_assistant_record([
                {"id": "t1", "name": "Bash", "input": {"command": "uv run alphaswarm query 'bad query'"}},
            ]),
            _make_result_record("t1", "Error: no results", is_error=True),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        assert len(data["cli_attempts"]) == 1
        assert data["cli_attempts"][0]["state"] == "ATTEMPTED_FAILED"
        assert data["cli_attempts"][0]["exit_code"] == 1

    def test_extracts_task_actions(self, tmp_path: Path) -> None:
        records = [
            _make_assistant_record([
                {"id": "t1", "name": "TaskCreate", "input": {
                    "subject": "Check reentrancy",
                    "description": "Look for reentrancy in withdraw",
                }},
            ]),
            _make_result_record("t1", "Task created"),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        assert len(data["task_actions"]) == 1
        assert data["task_actions"][0]["action"] == "create"
        assert data["task_actions"][0]["task_subject"] == "Check reentrancy"

    def test_extracts_skill_usage(self, tmp_path: Path) -> None:
        records = [
            _make_assistant_record([
                {"id": "t1", "name": "Skill", "input": {"skill": "vrs-audit"}},
            ]),
            _make_result_record("t1", "Audit completed"),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        assert len(data["skill_usage"]) == 1
        assert data["skill_usage"][0]["skill_name"] == "vrs-audit"
        assert data["skill_usage"][0]["was_invoked"] is True

    def test_detects_python_import_violation(self, tmp_path: Path) -> None:
        records = [
            _make_assistant_record([
                {"id": "t1", "name": "Bash", "input": {
                    "command": 'python -c "from alphaswarm_sol.kg import KnowledgeGraph"'
                }},
            ]),
            _make_result_record("t1", "OK"),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        assert len(data["violations"]) >= 1
        python_violations = [v for v in data["violations"] if v["violation_type"] == "python_import"]
        assert len(python_violations) == 1
        assert python_violations[0]["severity"] == "critical"

    def test_detects_context_read_violation(self, tmp_path: Path) -> None:
        records = [
            _make_assistant_record([
                {"id": "t1", "name": "Read", "input": {"file_path": "/project/.claude/CLAUDE.md"}},
            ]),
            _make_result_record("t1", "# AlphaSwarm.sol"),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        context_violations = [v for v in data["violations"] if v["violation_type"] == "context_read"]
        assert len(context_violations) == 1
        assert context_violations[0]["severity"] == "critical"

    def test_computes_duration(self, tmp_path: Path) -> None:
        records = [
            _make_assistant_record(
                [{"id": "t1", "name": "Read", "input": {}}],
                timestamp="2026-03-01T10:00:00Z",
            ),
            _make_assistant_record(
                [{"id": "t2", "name": "Read", "input": {}}],
                timestamp="2026-03-01T10:02:30Z",
            ),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        assert data["duration_seconds"] == 150.0

    def test_empty_transcript(self, tmp_path: Path) -> None:
        path = _make_jsonl([], tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        assert data["tool_calls"] == []
        assert data["cli_attempts"] == []
        assert data["duration_seconds"] == 0.0

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.jsonl"
        data = TranscriptSessionExtractor(path).extract()
        assert data["tool_calls"] == []


# ---------------------------------------------------------------------------
# Integration: Extractor -> Recorder -> Query roundtrip
# ---------------------------------------------------------------------------


class TestIntegrationRoundtrip:
    def test_extract_record_query(self, recorder: SessionRecorder, tmp_path: Path) -> None:
        """Full pipeline: JSONL -> extract -> record -> query."""
        records = [
            _make_assistant_record([
                {"id": "t1", "name": "Read", "input": {"file_path": "Vault.sol"}},
            ], timestamp="2026-03-01T10:00:00Z"),
            _make_result_record("t1", "pragma solidity ^0.8.0;"),
            _make_assistant_record([
                {"id": "t2", "name": "Bash", "input": {"command": "uv run alphaswarm build-kg Vault.sol"}},
            ], timestamp="2026-03-01T10:00:05Z"),
            _make_result_record("t2", "Built graph: 30 nodes, 80 edges"),
            _make_assistant_record([
                {"id": "t3", "name": "TaskCreate", "input": {
                    "subject": "Analyze access control",
                    "description": "Check all public functions for access control",
                }},
            ], timestamp="2026-03-01T10:00:10Z"),
            _make_result_record("t3", "Task created"),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")

        # Extract
        extractor = TranscriptSessionExtractor(path)
        parsed = extractor.extract()
        assert len(parsed["tool_calls"]) == 3
        assert len(parsed["cli_attempts"]) == 1

        # Record
        meta = SessionMetadata(
            teammate_name="test-agent",
            agent_type="vrs-attacker",
            contract="Vault.sol",
            workflow_id="test-workflow",
            verdict="PASS",
            overall_score=85.0,
        )
        session_id = recorder.record_session(str(path), meta, parsed_data=parsed)

        # Query
        calls = recorder.query_tool_calls(session_id)
        assert len(calls) == 3
        assert calls[0].tool_name == "Read"
        assert calls[1].tool_name == "Bash"

        cli = recorder.query_cli_attempts(session_id)
        assert len(cli) == 1
        assert "build-kg" in cli[0].command

        tasks = recorder.query_task_actions(session_id)
        assert len(tasks) == 1
        assert tasks[0].task_subject == "Analyze access control"

        # FTS search
        results = recorder.search("build-kg")
        assert len(results) > 0

        # Timeline
        timeline = recorder.get_session_timeline(session_id)
        assert len(timeline) > 0

    def test_basic_fallback_parse(self, recorder: SessionRecorder, tmp_path: Path) -> None:
        """Record without pre-parsed data uses basic fallback parser."""
        records = [
            _make_assistant_record([
                {"id": "t1", "name": "Bash", "input": {"command": "echo hello"}},
            ], timestamp="2026-03-01T10:00:00Z"),
            _make_result_record("t1", "hello"),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")

        meta = SessionMetadata(teammate_name="basic-test")
        session_id = recorder.record_session(str(path), meta)

        calls = recorder.query_tool_calls(session_id)
        assert len(calls) == 1
        assert calls[0].tool_name == "Bash"


# ---------------------------------------------------------------------------
# Non-alphaswarm Bash commands are NOT cli_attempts
# ---------------------------------------------------------------------------


class TestNonCLIBashCommands:
    def test_regular_bash_not_in_cli_attempts(self, tmp_path: Path) -> None:
        records = [
            _make_assistant_record([
                {"id": "t1", "name": "Bash", "input": {"command": "ls -la"}},
                {"id": "t2", "name": "Bash", "input": {"command": "cat README.md"}},
            ]),
            _make_result_record("t1", "total 42"),
            _make_result_record("t2", "# README"),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        assert len(data["tool_calls"]) == 2
        assert len(data["cli_attempts"]) == 0  # No alphaswarm commands


# ---------------------------------------------------------------------------
# TIER 4: Tests for key gaps (FIX-02, FIX-03, FIX-04, FIX-06, FIX-07)
# ---------------------------------------------------------------------------


class TestFabricationInInputsAndText:
    """FIX-02: Fabrication detector should scan tool inputs and assistant text."""

    def test_fabrication_in_tool_input(self, tmp_path: Path) -> None:
        """EVD-[hex] in tool input triggers fabrication violation."""
        records = [
            _make_assistant_record([
                {
                    "id": "t1",
                    "name": "Read",
                    "input": {"file_path": "EVD-abcdef01 reference"},
                },
            ]),
            _make_result_record("t1", "some clean output"),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        fab_violations = [
            v for v in data["violations"] if v["violation_type"] == "fabrication"
        ]
        assert len(fab_violations) >= 1
        assert any("input" in v["evidence"] for v in fab_violations)

    def test_fabrication_in_assistant_text(self, tmp_path: Path) -> None:
        """EVD-[hex] in assistant text blocks triggers fabrication violation."""
        records = [
            {
                "type": "assistant",
                "timestamp": "2026-03-01T10:00:00Z",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "Based on EVD-aabbcc01 and function:00112233aabb, I conclude...",
                        },
                    ]
                },
            },
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        fab_violations = [
            v for v in data["violations"] if v["violation_type"] == "fabrication"
        ]
        # Should detect both EVD- and function: patterns
        assert len(fab_violations) >= 2

    def test_bash_output_exempt_from_fabrication(self, tmp_path: Path) -> None:
        """Bash outputs are not flagged — they come from real CLI."""
        records = [
            _make_assistant_record([
                {
                    "id": "t1",
                    "name": "Bash",
                    "input": {"command": "uv run alphaswarm query x"},
                },
            ]),
            _make_result_record("t1", "function:00112233aabb found in graph"),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        fab_violations = [
            v for v in data["violations"] if v["violation_type"] == "fabrication"
        ]
        # Bash outputs should not trigger fabrication
        output_violations = [v for v in fab_violations if "output" in v["evidence"]]
        assert len(output_violations) == 0

    def test_function_id_in_tool_input(self, tmp_path: Path) -> None:
        """function:[hex] pattern in tool input triggers fabrication."""
        records = [
            _make_assistant_record([
                {
                    "id": "t1",
                    "name": "Read",
                    "input": {"file_path": "function:0011223344aa"},
                },
            ]),
            _make_result_record("t1", "clean output"),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        fab_violations = [
            v for v in data["violations"] if v["violation_type"] == "fabrication"
        ]
        assert len(fab_violations) >= 1


class TestWasAvailableLogic:
    """FIX-04: was_available should be False only when error AND 'not found'."""

    def test_error_with_not_found_marks_unavailable(self, tmp_path: Path) -> None:
        """Skill error with 'not found' → was_available=False."""
        records = [
            _make_assistant_record([
                {"id": "t1", "name": "Skill", "input": {"skill": "vrs-audit"}},
            ]),
            _make_result_record("t1", "Skill not found: vrs-audit", is_error=True),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        assert len(data["skill_usage"]) == 1
        assert data["skill_usage"][0]["was_available"] is False

    def test_error_without_not_found_marks_available(self, tmp_path: Path) -> None:
        """Skill error WITHOUT 'not found' → was_available=True."""
        records = [
            _make_assistant_record([
                {"id": "t1", "name": "Skill", "input": {"skill": "vrs-audit"}},
            ]),
            _make_result_record("t1", "Error: timeout exceeded", is_error=True),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        assert len(data["skill_usage"]) == 1
        assert data["skill_usage"][0]["was_available"] is True

    def test_success_marks_available(self, tmp_path: Path) -> None:
        """Successful skill invocation → was_available=True."""
        records = [
            _make_assistant_record([
                {"id": "t1", "name": "Skill", "input": {"skill": "vrs-audit"}},
            ]),
            _make_result_record("t1", "Audit completed successfully"),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        assert len(data["skill_usage"]) == 1
        assert data["skill_usage"][0]["was_available"] is True


class TestFTSDeleteTrigger:
    """FIX-03: Verify FTS DELETE triggers exist in the schema."""

    def test_delete_triggers_created(self, recorder: SessionRecorder) -> None:
        """FTS DELETE triggers should exist after schema init."""
        triggers = recorder._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        ).fetchall()
        trigger_names = {r[0] for r in triggers}
        assert "tool_calls_fts_delete" in trigger_names
        assert "task_actions_fts_delete" in trigger_names

    def test_fts_search_after_record(
        self, recorder: SessionRecorder, sample_metadata: SessionMetadata, sample_parsed_data: dict
    ) -> None:
        """FTS search works after recording and trigger fires on insert."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            recorder.record_session(f.name, sample_metadata, sample_parsed_data)
            results = recorder.search("build-kg")
            assert len(results) > 0


class TestViolationTimestamps:
    """FIX-07: Violations should carry timestamps for timeline positioning."""

    def test_violation_has_timestamp(self, tmp_path: Path) -> None:
        """Violations produced by extractor include timestamps."""
        records = [
            _make_assistant_record(
                [{"id": "t1", "name": "Read", "input": {"file_path": "/project/.claude/CLAUDE.md"}}],
                timestamp="2026-03-01T10:00:05Z",
            ),
            _make_result_record("t1", "# AlphaSwarm.sol"),
        ]
        path = _make_jsonl(records, tmp_path / "session.jsonl")
        data = TranscriptSessionExtractor(path).extract()
        context_violations = [
            v for v in data["violations"] if v["violation_type"] == "context_read"
        ]
        assert len(context_violations) == 1
        assert context_violations[0]["timestamp"] == "2026-03-01T10:00:05Z"

    def test_violations_sort_in_timeline(
        self, recorder: SessionRecorder,
    ) -> None:
        """Violations with timestamps sort correctly in timeline."""
        import tempfile

        parsed_data = {
            "tool_calls": [
                {
                    "sequence_num": 0,
                    "tool_name": "Read",
                    "tool_input": "{}",
                    "tool_output_excerpt": "",
                    "timestamp": "2026-03-01T10:00:00Z",
                    "blocked": False,
                },
                {
                    "sequence_num": 1,
                    "tool_name": "Bash",
                    "tool_input": "{}",
                    "tool_output_excerpt": "",
                    "timestamp": "2026-03-01T10:00:10Z",
                    "blocked": False,
                },
            ],
            "cli_attempts": [],
            "task_actions": [],
            "skill_usage": [],
            "violations": [
                {
                    "violation_type": "context_read",
                    "evidence": "Tool #0 Read: CLAUDE.md",
                    "severity": "critical",
                    "timestamp": "2026-03-01T10:00:05Z",
                },
            ],
            "start_time": "2026-03-01T10:00:00Z",
            "end_time": "2026-03-01T10:00:10Z",
            "duration_seconds": 10.0,
        }

        meta = SessionMetadata(teammate_name="test", verdict="FAIL")
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            session_id = recorder.record_session(f.name, meta, parsed_data)
            timeline = recorder.get_session_timeline(session_id)

            # Violation at T+5s should sort between T+0s and T+10s
            timestamped = [e for e in timeline if e.timestamp]
            assert len(timestamped) == 3
            assert timestamped[0].timestamp == "2026-03-01T10:00:00Z"
            assert timestamped[1].timestamp == "2026-03-01T10:00:05Z"
            assert timestamped[1].event_type == "violation"
            assert timestamped[2].timestamp == "2026-03-01T10:00:10Z"


class TestContextManager:
    """FIX-06: SessionRecorder supports `with` statement."""

    def test_context_manager(self, db_path: Path) -> None:
        """SessionRecorder works as context manager."""
        with SessionRecorder(db_path=db_path) as r:
            assert db_path.exists()
            # Should be usable inside the block
            sessions = r.list_sessions()
            assert sessions == []
        # After exiting, connection is closed — creating a new one should work
        r2 = SessionRecorder(db_path=db_path)
        assert r2.list_sessions() == []
        r2.close()


class TestToolInputTypeCoercion:
    """FIX-09: Non-string tool_input is JSON-serialized before INSERT."""

    def test_dict_tool_input_coerced(
        self, recorder: SessionRecorder,
    ) -> None:
        """Dict tool_input is JSON-serialized, not stringified."""
        import tempfile

        parsed_data = {
            "tool_calls": [
                {
                    "sequence_num": 0,
                    "tool_name": "Read",
                    "tool_input": {"file_path": "Vault.sol"},  # dict, not string
                    "tool_output_excerpt": "",
                    "timestamp": "2026-03-01T10:00:00Z",
                    "blocked": False,
                },
            ],
            "cli_attempts": [],
            "task_actions": [],
            "skill_usage": [],
            "violations": [],
            "start_time": "2026-03-01T10:00:00Z",
            "end_time": "2026-03-01T10:00:00Z",
            "duration_seconds": 0.0,
        }

        meta = SessionMetadata(teammate_name="test")
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            session_id = recorder.record_session(f.name, meta, parsed_data)
            calls = recorder.query_tool_calls(session_id)
            assert len(calls) == 1
            # Should be valid JSON, not "{'file_path': 'Vault.sol'}"
            parsed = json.loads(calls[0].tool_input)
            assert parsed["file_path"] == "Vault.sol"
