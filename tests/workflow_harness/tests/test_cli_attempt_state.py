"""Unit tests for CLIAttemptState extraction, check 13, reasoning timeline, and tool sequence.

Tests use synthetic JSONL transcripts that follow the Claude Code transcript format:
- assistant records with tool_use content blocks
- user records with tool_result content blocks

Each test creates a temporary JSONL file and exercises the extraction/validation
logic with deterministic synthetic data.

14 tests total:
- 9 CLIAttemptState tests (success, failed, not_attempted, transcript_unavailable,
  empty, mixed, check 13 severity x3)
- 3 reasoning timeline tests (hypothesis, query_formulation, conclusion)
- 2 tool sequence tests (build+query classification, empty transcript)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


# --- Synthetic JSONL transcript builders ---


def _write_jsonl(records: list[dict], path: Path) -> None:
    """Write a list of dicts as JSONL to the given path."""
    with open(path, "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def _make_assistant_tool_use(
    tool_name: str,
    tool_input: dict,
    tool_id: str = "tu_1",
    timestamp: str | None = "2026-03-02T10:00:00Z",
) -> dict:
    """Create a synthetic assistant record with a tool_use block."""
    return {
        "type": "assistant",
        "timestamp": timestamp,
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": tool_name,
                    "input": tool_input,
                }
            ]
        },
    }


def _make_tool_result(
    tool_use_id: str,
    content: str,
    is_error: bool = False,
    timestamp: str | None = "2026-03-02T10:00:05Z",
) -> dict:
    """Create a synthetic user record with a tool_result block."""
    return {
        "type": "user",
        "timestamp": timestamp,
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": content,
                    "is_error": is_error,
                }
            ]
        },
    }


def _make_assistant_text(
    text: str,
    timestamp: str | None = "2026-03-02T10:00:10Z",
) -> dict:
    """Create a synthetic assistant record with a text block."""
    return {
        "type": "assistant",
        "timestamp": timestamp,
        "message": {
            "content": [
                {
                    "type": "text",
                    "text": text,
                }
            ]
        },
    }


# --- Fixtures ---


@pytest.fixture
def success_transcript(tmp_path: Path) -> Path:
    """Transcript with a successful alphaswarm query."""
    jsonl_path = tmp_path / "success.jsonl"
    records = [
        _make_assistant_text("I'll analyze this contract for reentrancy vulnerabilities."),
        _make_assistant_tool_use(
            "Bash",
            {"command": "uv run alphaswarm query 'reentrancy' --graph /tmp/g.toon"},
            tool_id="tu_1",
        ),
        _make_tool_result(
            "tu_1",
            "graph_nodes=12 matches=3\nF-vault-withdraw: R:bal -> X:call -> W:bal",
        ),
        _make_assistant_text("The query returned 3 matches. The reentrancy pattern is confirmed."),
    ]
    _write_jsonl(records, jsonl_path)
    return jsonl_path


@pytest.fixture
def failed_transcript(tmp_path: Path) -> Path:
    """Transcript with a failed alphaswarm query (error result)."""
    jsonl_path = tmp_path / "failed.jsonl"
    records = [
        _make_assistant_tool_use(
            "Bash",
            {"command": "uv run alphaswarm query 'access control' --graph /tmp/g.toon"},
            tool_id="tu_1",
        ),
        _make_tool_result(
            "tu_1",
            "Error: graph file not found: /tmp/g.toon",
            is_error=True,
        ),
    ]
    _write_jsonl(records, jsonl_path)
    return jsonl_path


@pytest.fixture
def not_attempted_transcript(tmp_path: Path) -> Path:
    """Transcript with no alphaswarm CLI calls (only Read and echo)."""
    jsonl_path = tmp_path / "not_attempted.jsonl"
    records = [
        _make_assistant_tool_use(
            "Read",
            {"file_path": "/tmp/contract.sol"},
            tool_id="tu_1",
        ),
        _make_tool_result("tu_1", "pragma solidity ^0.8.0;\ncontract Vault { ... }"),
        _make_assistant_tool_use(
            "Bash",
            {"command": "echo hello"},
            tool_id="tu_2",
        ),
        _make_tool_result("tu_2", "hello"),
    ]
    _write_jsonl(records, jsonl_path)
    return jsonl_path


@pytest.fixture
def mixed_transcript(tmp_path: Path) -> Path:
    """Transcript with one failed and one successful alphaswarm query."""
    jsonl_path = tmp_path / "mixed.jsonl"
    records = [
        _make_assistant_tool_use(
            "Bash",
            {"command": "uv run alphaswarm query 'nonexistent' --graph /tmp/g.toon"},
            tool_id="tu_1",
        ),
        _make_tool_result("tu_1", "Error: no matches found", is_error=True),
        _make_assistant_tool_use(
            "Bash",
            {"command": "uv run alphaswarm query 'reentrancy' --graph /tmp/g.toon"},
            tool_id="tu_2",
        ),
        _make_tool_result(
            "tu_2",
            "graph_nodes=12 matches=3\nF-vault-withdraw: reentrancy detected",
        ),
    ]
    _write_jsonl(records, jsonl_path)
    return jsonl_path


@pytest.fixture
def build_and_query_transcript(tmp_path: Path) -> Path:
    """Transcript with build-kg and query commands for tool sequence testing."""
    jsonl_path = tmp_path / "build_query.jsonl"
    records = [
        _make_assistant_text("Let me build the knowledge graph first."),
        _make_assistant_tool_use(
            "Bash",
            {"command": "uv run alphaswarm build-kg /tmp/contracts/Vault.sol"},
            tool_id="tu_1",
            timestamp="2026-03-02T10:00:00Z",
        ),
        _make_tool_result(
            "tu_1",
            "Built graph: 42 nodes, 58 edges",
            timestamp="2026-03-02T10:00:30Z",
        ),
        _make_assistant_text("Graph built. Now querying for vulnerabilities."),
        _make_assistant_tool_use(
            "Bash",
            {"command": "uv run alphaswarm query 'reentrancy' --graph /tmp/g.toon"},
            tool_id="tu_2",
            timestamp="2026-03-02T10:00:35Z",
        ),
        _make_tool_result(
            "tu_2",
            "graph_nodes=42 matches=5\nF-vault-withdraw: R:bal -> X:call -> W:bal",
            timestamp="2026-03-02T10:00:40Z",
        ),
        _make_assistant_text("Based on the query results, I found a reentrancy vulnerability."),
    ]
    _write_jsonl(records, jsonl_path)
    return jsonl_path


# =========================================================================
# CLIAttemptState tests (9)
# =========================================================================


class TestCLIAttemptState:
    """Tests for CLIAttemptState enum and compute_cli_attempt_state."""

    def test_cli_success(self, success_transcript: Path) -> None:
        """Transcript with successful alphaswarm query -> ATTEMPTED_SUCCESS."""
        from alphaswarm_sol.testing.evaluation.cli_attempt_state import (
            CLIAttemptState,
            compute_cli_attempt_state,
        )

        result = compute_cli_attempt_state(success_transcript)
        assert result == CLIAttemptState.ATTEMPTED_SUCCESS

    def test_cli_failed(self, failed_transcript: Path) -> None:
        """Transcript with failed alphaswarm query -> ATTEMPTED_FAILED."""
        from alphaswarm_sol.testing.evaluation.cli_attempt_state import (
            CLIAttemptState,
            compute_cli_attempt_state,
        )

        result = compute_cli_attempt_state(failed_transcript)
        assert result == CLIAttemptState.ATTEMPTED_FAILED

    def test_cli_not_attempted(self, not_attempted_transcript: Path) -> None:
        """Transcript with no alphaswarm commands -> NOT_ATTEMPTED."""
        from alphaswarm_sol.testing.evaluation.cli_attempt_state import (
            CLIAttemptState,
            compute_cli_attempt_state,
        )

        result = compute_cli_attempt_state(not_attempted_transcript)
        assert result == CLIAttemptState.NOT_ATTEMPTED

    def test_transcript_unavailable(self) -> None:
        """None path -> TRANSCRIPT_UNAVAILABLE."""
        from alphaswarm_sol.testing.evaluation.cli_attempt_state import (
            CLIAttemptState,
            compute_cli_attempt_state,
        )

        result = compute_cli_attempt_state(None)
        assert result == CLIAttemptState.TRANSCRIPT_UNAVAILABLE

    def test_empty_transcript(self, tmp_path: Path) -> None:
        """0-byte file -> TRANSCRIPT_UNAVAILABLE."""
        from alphaswarm_sol.testing.evaluation.cli_attempt_state import (
            CLIAttemptState,
            compute_cli_attempt_state,
        )

        empty_file = tmp_path / "empty.jsonl"
        empty_file.touch()
        assert empty_file.stat().st_size == 0

        result = compute_cli_attempt_state(empty_file)
        assert result == CLIAttemptState.TRANSCRIPT_UNAVAILABLE

    def test_mixed_results_is_success(self, mixed_transcript: Path) -> None:
        """Transcript with one failed + one successful query -> ATTEMPTED_SUCCESS."""
        from alphaswarm_sol.testing.evaluation.cli_attempt_state import (
            CLIAttemptState,
            compute_cli_attempt_state,
        )

        result = compute_cli_attempt_state(mixed_transcript)
        assert result == CLIAttemptState.ATTEMPTED_SUCCESS


class TestCheck13:
    """Tests for check 13 (_check_cli_attempt_state) in the validator."""

    def test_check_13_critical_for_not_attempted(
        self, not_attempted_transcript: Path
    ) -> None:
        """NOT_ATTEMPTED transcript -> critical violation from check 13."""
        from alphaswarm_sol.testing.evaluation.agent_execution_validator import (
            _check_cli_attempt_state,
        )

        violations = _check_cli_attempt_state({}, "test.json", not_attempted_transcript)
        assert len(violations) == 1
        assert violations[0].severity == "critical"
        assert violations[0].check_name == "cli_attempt_state"
        assert violations[0].evidence["cli_attempt_state"] == "not_attempted"

    def test_check_13_warning_for_failed(self, failed_transcript: Path) -> None:
        """ATTEMPTED_FAILED transcript -> warning violation from check 13."""
        from alphaswarm_sol.testing.evaluation.agent_execution_validator import (
            _check_cli_attempt_state,
        )

        violations = _check_cli_attempt_state({}, "test.json", failed_transcript)
        assert len(violations) == 1
        assert violations[0].severity == "warning"
        assert violations[0].check_name == "cli_attempt_state"
        assert violations[0].evidence["cli_attempt_state"] == "attempted_failed"

    def test_check_13_no_violation_for_success(
        self, success_transcript: Path
    ) -> None:
        """ATTEMPTED_SUCCESS transcript -> no violations from check 13."""
        from alphaswarm_sol.testing.evaluation.agent_execution_validator import (
            _check_cli_attempt_state,
        )

        violations = _check_cli_attempt_state({}, "test.json", success_transcript)
        assert len(violations) == 0


# =========================================================================
# Reasoning timeline tests (3)
# =========================================================================


class TestReasoningTimeline:
    """Tests for extract_reasoning_timeline heuristic classification."""

    def test_timeline_hypothesis_before_first_query(
        self, build_and_query_transcript: Path
    ) -> None:
        """Text before first tool call -> hypothesis move type."""
        from alphaswarm_sol.testing.evaluation.reasoning_timeline import (
            extract_reasoning_timeline,
        )

        events = extract_reasoning_timeline(build_and_query_transcript)
        assert len(events) > 0
        # First event should be hypothesis (text before first tool call)
        assert events[0].move_type == "hypothesis"
        assert "build the knowledge graph" in events[0].content_snippet

    def test_timeline_query_formulation(
        self, build_and_query_transcript: Path
    ) -> None:
        """alphaswarm query Bash command -> query_formulation event present."""
        from alphaswarm_sol.testing.evaluation.reasoning_timeline import (
            extract_reasoning_timeline,
        )

        events = extract_reasoning_timeline(build_and_query_transcript)
        formulation_events = [e for e in events if e.move_type == "query_formulation"]
        assert len(formulation_events) > 0
        # At least one query formulation should reference alphaswarm
        assert any("alphaswarm" in e.content_snippet for e in formulation_events)

    def test_timeline_conclusion(
        self, build_and_query_transcript: Path
    ) -> None:
        """Last assistant text after all tool calls -> conclusion move type."""
        from alphaswarm_sol.testing.evaluation.reasoning_timeline import (
            extract_reasoning_timeline,
        )

        events = extract_reasoning_timeline(build_and_query_transcript)
        assert len(events) > 0
        # Last event should be conclusion
        last_text_event = None
        for e in reversed(events):
            if e.tool_call_id is None:
                last_text_event = e
                break
        assert last_text_event is not None
        assert last_text_event.move_type == "conclusion"


# =========================================================================
# Tool sequence tests (2)
# =========================================================================


class TestToolSequence:
    """Tests for extract_tool_sequence subtype classification."""

    def test_tool_sequence_build_and_query(
        self, build_and_query_transcript: Path
    ) -> None:
        """build-kg and query commands -> correct subtype classification."""
        from alphaswarm_sol.testing.evaluation.reasoning_timeline import (
            extract_tool_sequence,
        )

        sequence = extract_tool_sequence(build_and_query_transcript)
        assert len(sequence) >= 2

        # Find build-kg and query subtypes
        subtypes = [s["subtype"] for s in sequence]
        assert "build-kg" in subtypes, f"Expected 'build-kg' in subtypes: {subtypes}"
        assert "query" in subtypes, f"Expected 'query' in subtypes: {subtypes}"

        # Verify ordering: build-kg should come before query
        build_idx = next(s["index"] for s in sequence if s["subtype"] == "build-kg")
        query_idx = next(s["index"] for s in sequence if s["subtype"] == "query")
        assert build_idx < query_idx

    def test_tool_sequence_empty_transcript(self) -> None:
        """Missing transcript -> empty tool sequence list."""
        from alphaswarm_sol.testing.evaluation.reasoning_timeline import (
            extract_tool_sequence,
        )

        result = extract_tool_sequence(Path("/nonexistent/path.jsonl"))
        assert result == []
