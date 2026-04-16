"""Tests for 3.1c-02 observation hooks and JSONL writer.

Verifies:
- observation_writer produces valid JSONL
- Each hook produces ObservationRecord-compatible output
- Thread safety of writer
- Hooks handle malformed stdin gracefully
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from alphaswarm_sol.testing.evaluation.models import ObservationRecord
from tests.workflow_harness.lib.observation_writer import (
    get_observations_dir,
    write_observation,
)

HOOKS_DIR = Path(__file__).parents[1] / "workflow_harness" / "hooks"


# ---------------------------------------------------------------------------
# ObservationWriter
# ---------------------------------------------------------------------------


class TestObservationWriter:
    def test_write_creates_jsonl(self, tmp_path: Path):
        path = write_observation(
            session_id="test-001",
            event_type="tool_use",
            hook_name="test_hook",
            data={"tool": "Bash"},
            base_dir=tmp_path,
        )
        assert path.exists()
        assert path.suffix == ".jsonl"

    def test_jsonl_is_valid_observation_record(self, tmp_path: Path):
        write_observation(
            session_id="test-001",
            event_type="tool_use",
            hook_name="test_hook",
            data={"tool": "Bash"},
            base_dir=tmp_path,
        )
        jsonl_path = tmp_path / ".vrs" / "observations" / "test-001.jsonl"
        with open(jsonl_path) as f:
            line = f.readline()
        record = ObservationRecord.model_validate_json(line)
        assert record.event_type == "tool_use"
        assert record.hook_name == "test_hook"
        assert record.data["tool"] == "Bash"

    def test_append_multiple_records(self, tmp_path: Path):
        for i in range(3):
            write_observation(
                session_id="test-001",
                event_type=f"event_{i}",
                hook_name="test_hook",
                base_dir=tmp_path,
            )
        jsonl_path = tmp_path / ".vrs" / "observations" / "test-001.jsonl"
        lines = jsonl_path.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_different_sessions_different_files(self, tmp_path: Path):
        write_observation(
            session_id="sess-a", event_type="x", hook_name="h", base_dir=tmp_path
        )
        write_observation(
            session_id="sess-b", event_type="y", hook_name="h", base_dir=tmp_path
        )
        obs_dir = tmp_path / ".vrs" / "observations"
        files = list(obs_dir.glob("*.jsonl"))
        assert len(files) == 2

    def test_thread_safety(self, tmp_path: Path):
        """Multiple threads writing concurrently should not corrupt output."""
        errors = []

        def writer(n: int):
            try:
                write_observation(
                    session_id="concurrent",
                    event_type=f"event_{n}",
                    hook_name="thread_test",
                    base_dir=tmp_path,
                )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        jsonl_path = tmp_path / ".vrs" / "observations" / "concurrent.jsonl"
        lines = jsonl_path.read_text().strip().split("\n")
        assert len(lines) == 20
        # Each line should be valid JSON
        for line in lines:
            json.loads(line)

    def test_custom_timestamp(self, tmp_path: Path):
        ts = "2026-02-18T12:00:00Z"
        write_observation(
            session_id="ts-test",
            event_type="x",
            hook_name="h",
            timestamp=ts,
            base_dir=tmp_path,
        )
        jsonl_path = tmp_path / ".vrs" / "observations" / "ts-test.jsonl"
        record = json.loads(jsonl_path.read_text().strip())
        assert record["timestamp"] == ts

    def test_observations_dir_created(self, tmp_path: Path):
        obs_dir = get_observations_dir(tmp_path)
        assert obs_dir.exists()
        assert obs_dir == tmp_path / ".vrs" / "observations"


# ---------------------------------------------------------------------------
# Hook scripts — verify they produce valid output
# ---------------------------------------------------------------------------


def _run_hook(hook_name: str, input_data: dict, tmp_cwd: Path) -> None:
    """Run a hook script with given input, using tmp_cwd as working directory."""
    hook_path = HOOKS_DIR / hook_name
    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        cwd=str(tmp_cwd),
        timeout=10,
    )
    # Hooks should exit 0 (or 2 for blocking)
    assert result.returncode in (0, 2), f"Hook {hook_name} failed: {result.stderr}"


def _get_observations(tmp_cwd: Path, session_id: str = "test-session") -> list[dict]:
    """Read all observation records from a session's JSONL file."""
    jsonl_path = tmp_cwd / ".vrs" / "observations" / f"{session_id}.jsonl"
    if not jsonl_path.exists():
        return []
    lines = jsonl_path.read_text().strip().split("\n")
    return [json.loads(line) for line in lines if line.strip()]


class TestObsToolUseHook:
    def test_produces_observation(self, tmp_path: Path):
        _run_hook("obs_tool_use.py", {
            "session_id": "test-session",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        }, tmp_path)
        records = _get_observations(tmp_path)
        assert len(records) == 1
        assert records[0]["event_type"] == "tool_use"
        assert records[0]["data"]["tool_name"] == "Bash"

    def test_malformed_stdin(self, tmp_path: Path):
        """Hook should not crash on malformed input."""
        hook_path = HOOKS_DIR / "obs_tool_use.py"
        result = subprocess.run(
            [sys.executable, str(hook_path)],
            input="not json",
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            timeout=10,
        )
        assert result.returncode == 0


class TestObsToolResultHook:
    def test_produces_observation(self, tmp_path: Path):
        _run_hook("obs_tool_result.py", {
            "session_id": "test-session",
            "tool_name": "Bash",
            "tool_output": "file1.txt\nfile2.txt",
        }, tmp_path)
        records = _get_observations(tmp_path)
        assert len(records) == 1
        assert records[0]["event_type"] == "tool_result"


class TestObsBskgQueryHook:
    def test_captures_alphaswarm_command(self, tmp_path: Path):
        _run_hook("obs_bskg_query.py", {
            "session_id": "test-session",
            "tool_name": "Bash",
            "tool_input": {"command": "uv run alphaswarm query 'functions without access control'"},
            "tool_output": "Found 3 functions...",
        }, tmp_path)
        records = _get_observations(tmp_path)
        assert len(records) == 1
        assert records[0]["event_type"] == "bskg_query"

    def test_ignores_non_alphaswarm(self, tmp_path: Path):
        _run_hook("obs_bskg_query.py", {
            "session_id": "test-session",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
        }, tmp_path)
        records = _get_observations(tmp_path)
        assert len(records) == 0

    def test_ignores_non_bash_tools(self, tmp_path: Path):
        _run_hook("obs_bskg_query.py", {
            "session_id": "test-session",
            "tool_name": "Read",
            "tool_input": {"path": "contracts/Vault.sol"},
        }, tmp_path)
        records = _get_observations(tmp_path)
        assert len(records) == 0


class TestObsMessageHook:
    def test_captures_send_message(self, tmp_path: Path):
        _run_hook("obs_message.py", {
            "session_id": "test-session",
            "tool_name": "SendMessage",
            "tool_input": {
                "type": "message",
                "recipient": "defender",
                "content": "Found reentrancy vulnerability",
                "summary": "Reentrancy finding",
            },
        }, tmp_path)
        records = _get_observations(tmp_path)
        assert len(records) == 1
        assert records[0]["event_type"] == "message"
        assert records[0]["data"]["recipient"] == "defender"

    def test_ignores_non_send_message(self, tmp_path: Path):
        _run_hook("obs_message.py", {
            "session_id": "test-session",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        }, tmp_path)
        records = _get_observations(tmp_path)
        assert len(records) == 0


class TestObsSessionStartHook:
    def test_produces_observation(self, tmp_path: Path):
        _run_hook("obs_session_start.py", {
            "session_id": "test-session",
            "cwd": "/projects/audit",
            "model": "sonnet",
        }, tmp_path)
        records = _get_observations(tmp_path)
        assert len(records) == 1
        assert records[0]["event_type"] == "session_start"

    def test_includes_source_and_agent_type(self, tmp_path: Path):
        """P13-IMP-05: source and agent_type fields are present."""
        _run_hook("obs_session_start.py", {
            "session_id": "test-session",
            "cwd": "/projects/audit",
            "model": "sonnet",
            "source": "headless",
            "agent_type": "attacker",
        }, tmp_path)
        records = _get_observations(tmp_path)
        assert len(records) == 1
        assert records[0]["data"]["source"] == "headless"
        assert records[0]["data"]["agent_type"] == "attacker"

    def test_defaults_source_and_agent_type(self, tmp_path: Path):
        """source and agent_type default when not provided."""
        _run_hook("obs_session_start.py", {
            "session_id": "test-session",
        }, tmp_path)
        records = _get_observations(tmp_path)
        assert len(records) == 1
        assert records[0]["data"]["source"] == "unknown"
        assert records[0]["data"]["agent_type"] == "main"


class TestObsAgentStopHook:
    def test_produces_observation(self, tmp_path: Path):
        _run_hook("obs_agent_stop.py", {
            "session_id": "test-session",
            "agent_id": "attacker-1",
            "agent_transcript_path": "/tmp/transcript.jsonl",
            "stop_hook_active": False,
        }, tmp_path)
        records = _get_observations(tmp_path)
        assert len(records) == 1
        assert records[0]["event_type"] == "agent_stop"
        assert records[0]["data"]["agent_id"] == "attacker-1"


class TestDebriefGateHook:
    def test_exits_cleanly(self, tmp_path: Path):
        """Stub should exit 0 (not block) in stub mode."""
        _run_hook("debrief_gate.py", {
            "session_id": "test-session",
            "teammate_name": "attacker",
            "stop_hook_active": False,
        }, tmp_path)

    def test_exits_on_stop_hook_active(self, tmp_path: Path):
        _run_hook("debrief_gate.py", {
            "session_id": "test-session",
            "stop_hook_active": True,
        }, tmp_path)


class TestDebriefTaskCompleteHook:
    def test_records_completion(self, tmp_path: Path):
        _run_hook("debrief_task_complete.py", {
            "session_id": "test-session",
            "task_id": "task-1",
            "task_subject": "Investigate reentrancy",
            "stop_hook_active": False,
        }, tmp_path)
        records = _get_observations(tmp_path)
        assert len(records) == 1
        assert records[0]["event_type"] == "task_completed"


# ---------------------------------------------------------------------------
# New hooks (3.1c-02): obs_precompact, obs_session_end, delegate_guard
# ---------------------------------------------------------------------------


def _run_hook_with_exit(hook_name: str, input_data: dict, tmp_cwd: Path) -> int:
    """Run a hook script and return exit code."""
    hook_path = HOOKS_DIR / hook_name
    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        cwd=str(tmp_cwd),
        timeout=10,
    )
    return result.returncode


class TestObsPrecompactHook:
    def test_auto_trigger_writes_snapshot(self, tmp_path: Path):
        """Auto trigger writes precompact_snapshot and .compacted marker."""
        # Create a minimal transcript file for the hook to read
        transcript = tmp_path / "test.jsonl"
        transcript.write_text(
            json.dumps({"type": "user", "message": {"content": [
                {"type": "tool_result", "content": "Found F-vault-withdraw and C-vault-owner"}
            ]}}) + "\n"
        )
        _run_hook("obs_precompact.py", {
            "session_id": "test-session",
            "trigger": "auto",
            "transcript_path": str(transcript),
        }, tmp_path)
        records = _get_observations(tmp_path)
        assert len(records) == 1
        assert records[0]["event_type"] == "precompact_snapshot"
        assert "bskg_node_ids" in records[0]["data"]
        # Verify BSKG node extraction
        node_ids = records[0]["data"]["bskg_node_ids"]
        assert "C-vault-owner" in node_ids
        assert "F-vault-withdraw" in node_ids
        # Verify .compacted marker
        marker = tmp_path / ".vrs" / "markers" / "test-session.compacted"
        assert marker.exists()

    def test_manual_trigger_no_output(self, tmp_path: Path):
        """Manual trigger exits 0 with no marker."""
        exit_code = _run_hook_with_exit("obs_precompact.py", {
            "session_id": "test-session",
            "trigger": "manual",
        }, tmp_path)
        assert exit_code == 0
        records = _get_observations(tmp_path)
        assert len(records) == 0
        marker = tmp_path / ".vrs" / "markers" / "test-session.compacted"
        assert not marker.exists()

    def test_stdlib_only_imports(self):
        """obs_precompact.py must not import TranscriptParser or project modules."""
        hook_path = HOOKS_DIR / "obs_precompact.py"
        source = hook_path.read_text()
        assert "transcript_parser" not in source
        assert "from tests." not in source
        assert "import alphaswarm" not in source
        assert "from workflow_harness" not in source


class TestObsSessionEndHook:
    def test_produces_observation(self, tmp_path: Path):
        _run_hook("obs_session_end.py", {
            "session_id": "test-session",
        }, tmp_path)
        records = _get_observations(tmp_path)
        assert len(records) == 1
        assert records[0]["event_type"] == "session_end"

    def test_writes_session_ended_marker(self, tmp_path: Path):
        _run_hook("obs_session_end.py", {
            "session_id": "test-session",
        }, tmp_path)
        marker = tmp_path / ".vrs" / "markers" / "test-session.session_ended"
        assert marker.exists()


class TestDelegateGuardHook:
    def test_blocks_read_of_sol_file(self, tmp_path: Path):
        """delegate_guard blocks Read of .sol files."""
        exit_code = _run_hook_with_exit("delegate_guard.py", {
            "session_id": "test-session",
            "tool_name": "Read",
            "tool_input": {"file_path": "contracts/Vault.sol"},
        }, tmp_path)
        assert exit_code == 2  # Blocked

    def test_allows_read_of_vrs_path(self, tmp_path: Path):
        """delegate_guard permits Read of .vrs/ paths."""
        exit_code = _run_hook_with_exit("delegate_guard.py", {
            "session_id": "test-session",
            "tool_name": "Read",
            "tool_input": {"file_path": ".vrs/observations/session.jsonl"},
        }, tmp_path)
        assert exit_code == 0  # Allowed

    def test_allows_unblocked_tool(self, tmp_path: Path):
        """delegate_guard allows tools not in blocked_tools list."""
        exit_code = _run_hook_with_exit("delegate_guard.py", {
            "session_id": "test-session",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        }, tmp_path)
        assert exit_code == 0  # Allowed

    def test_blocks_sol_pattern_in_input(self, tmp_path: Path):
        """delegate_guard blocks .sol pattern in tool input."""
        exit_code = _run_hook_with_exit("delegate_guard.py", {
            "session_id": "test-session",
            "tool_name": "Grep",
            "tool_input": {"pattern": "function", "path": "contracts/Vault.sol"},
        }, tmp_path)
        assert exit_code == 2  # Blocked by .sol pattern


# ---------------------------------------------------------------------------
# Real session validation (3.1c-02 P0 hard gate)
# ---------------------------------------------------------------------------

REAL_SESSIONS_DIR = Path(__file__).parents[1] / "workflow_harness" / "fixtures" / "real_sessions"


class TestRealSessionTranscriptParser:
    """Validate TranscriptParser.to_observation_summary() on real transcripts."""

    @pytest.mark.parametrize("jsonl_file", sorted(REAL_SESSIONS_DIR.glob("*.jsonl")) if REAL_SESSIONS_DIR.exists() else [])
    def test_non_empty_tool_counts(self, jsonl_file: Path):
        from tests.workflow_harness.lib.transcript_parser import TranscriptParser
        parser = TranscriptParser(jsonl_file)
        summary = parser.to_observation_summary()
        assert len(summary.tool_counts) > 0, f"Empty tool_counts for {jsonl_file.name}"
        assert summary.total_tool_calls > 0

    @pytest.mark.parametrize("jsonl_file", sorted(REAL_SESSIONS_DIR.glob("*.jsonl")) if REAL_SESSIONS_DIR.exists() else [])
    def test_null_safety(self, jsonl_file: Path):
        from tests.workflow_harness.lib.transcript_parser import TranscriptParser
        parser = TranscriptParser(jsonl_file)
        summary = parser.to_observation_summary()
        assert isinstance(summary.tool_counts, dict)
        assert isinstance(summary.tool_sequences, list)
        assert isinstance(summary.bskg_query_events, list)
        assert isinstance(summary.tool_failures, list)
        assert isinstance(summary.agent_lifecycle_events, list)


# ---------------------------------------------------------------------------
# All records validate against ObservationRecord schema
# ---------------------------------------------------------------------------


class TestObservationRecordValidation:
    """Every hook output must parse as ObservationRecord."""

    def test_all_hook_outputs_valid(self, tmp_path: Path):
        """Run all hooks and validate all produced JSONL lines."""
        hooks_and_inputs = [
            ("obs_tool_use.py", {"session_id": "validate", "tool_name": "Bash", "tool_input": {}}),
            ("obs_tool_result.py", {"session_id": "validate", "tool_name": "Bash", "tool_output": "ok"}),
            ("obs_bskg_query.py", {"session_id": "validate", "tool_name": "Bash",
                                    "tool_input": {"command": "alphaswarm query x"}, "tool_output": "y"}),
            ("obs_message.py", {"session_id": "validate", "tool_name": "SendMessage",
                                "tool_input": {"recipient": "a", "content": "b"}}),
            ("obs_session_start.py", {"session_id": "validate"}),
            ("obs_agent_stop.py", {"session_id": "validate", "agent_id": "a"}),
            ("debrief_task_complete.py", {"session_id": "validate", "task_id": "1"}),
        ]
        for hook_name, input_data in hooks_and_inputs:
            _run_hook(hook_name, input_data, tmp_path)

        records = _get_observations(tmp_path, "validate")
        assert len(records) >= 5  # At least 5 hooks produce output

        for record_dict in records:
            # Must parse as ObservationRecord without error
            rec = ObservationRecord.model_validate(record_dict)
            assert rec.session_id == "validate"
