"""Tests for transcript_parser.py — TranscriptParser and ToolCall."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .lib.transcript_parser import BSKGQuery, TranscriptParser, ToolCall


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl(tmp_path: Path, records: list[dict]) -> Path:
    """Write records as JSONL and return the file path."""
    p = tmp_path / "test_transcript.jsonl"
    with open(p, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return p


def _assistant_tool_use(tool_name: str, tool_input: dict, tool_id: str = "tu_1") -> dict:
    """Create an assistant record with a tool_use block."""
    return {
        "type": "assistant",
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


def _user_tool_result(tool_id: str, result_text: str) -> dict:
    """Create a user record with a tool_result block."""
    return {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result_text,
                }
            ]
        },
    }


# ---------------------------------------------------------------------------
# TranscriptParser basics
# ---------------------------------------------------------------------------


class TestTranscriptParserBasics:
    def test_empty_file(self, tmp_path: Path):
        p = _write_jsonl(tmp_path, [])
        parser = TranscriptParser(p)
        assert parser.get_tool_calls() == []
        assert parser.get_tool_sequence() == []
        assert parser.record_count == 0

    def test_nonexistent_file(self, tmp_path: Path):
        p = tmp_path / "nonexistent.jsonl"
        parser = TranscriptParser(p)
        assert parser.get_tool_calls() == []
        assert parser.record_count == 0

    def test_single_tool_call(self, tmp_path: Path):
        records = [
            _assistant_tool_use("Bash", {"command": "ls"}, "tu_1"),
            _user_tool_result("tu_1", "file1.txt\nfile2.txt"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))

        calls = parser.get_tool_calls()
        assert len(calls) == 1
        assert calls[0].tool_name == "Bash"
        assert calls[0].tool_input == {"command": "ls"}
        assert calls[0].tool_result == "file1.txt\nfile2.txt"
        assert calls[0].index == 0

    def test_multiple_tool_calls(self, tmp_path: Path):
        records = [
            _assistant_tool_use("Read", {"file_path": "/foo"}, "tu_1"),
            _user_tool_result("tu_1", "contents"),
            _assistant_tool_use("Grep", {"pattern": "error"}, "tu_2"),
            _user_tool_result("tu_2", "line 5: error found"),
            _assistant_tool_use("Bash", {"command": "echo done"}, "tu_3"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))

        seq = parser.get_tool_sequence()
        assert seq == ["Read", "Grep", "Bash"]
        assert parser.get_tool_calls()[0].index == 0
        assert parser.get_tool_calls()[2].index == 2

    def test_tool_result_truncation(self, tmp_path: Path):
        long_result = "x" * 1000
        records = [
            _assistant_tool_use("Bash", {"command": "cat big"}, "tu_1"),
            _user_tool_result("tu_1", long_result),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        assert len(parser.get_tool_calls()[0].tool_result) == 500

    def test_tool_result_content_blocks(self, tmp_path: Path):
        """tool_result content may be a list of blocks instead of a string."""
        records = [
            _assistant_tool_use("Read", {"file_path": "/f"}, "tu_1"),
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "tu_1",
                            "content": [
                                {"type": "text", "text": "line 1"},
                                {"type": "text", "text": "line 2"},
                            ],
                        }
                    ]
                },
            },
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        assert parser.get_tool_calls()[0].tool_result == "line 1\nline 2"

    def test_malformed_records_skipped(self, tmp_path: Path):
        """Invalid JSON lines are skipped gracefully."""
        p = tmp_path / "bad.jsonl"
        with open(p, "w") as f:
            f.write("not json\n")
            f.write(json.dumps(_assistant_tool_use("Bash", {"command": "ls"}, "tu_1")) + "\n")
        parser = TranscriptParser(p)
        assert len(parser.get_tool_calls()) == 1


# ---------------------------------------------------------------------------
# Query methods
# ---------------------------------------------------------------------------


class TestTranscriptParserQueries:
    @pytest.fixture
    def parser(self, tmp_path: Path) -> TranscriptParser:
        records = [
            _assistant_tool_use("Bash", {"command": "uv run alphaswarm build-kg contracts/"}, "tu_1"),
            _user_tool_result("tu_1", "Graph built"),
            _assistant_tool_use("Bash", {"command": "uv run alphaswarm query 'reentrancy'"}, "tu_2"),
            _user_tool_result("tu_2", "Found 3 nodes"),
            _assistant_tool_use("Read", {"file_path": "/contracts/Vault.sol"}, "tu_3"),
            _user_tool_result("tu_3", "pragma solidity..."),
            _assistant_tool_use("Write", {"file_path": "/report.md", "content": "## Finding: vulnerability confirmed"}, "tu_4"),
        ]
        return TranscriptParser(_write_jsonl(tmp_path, records))

    def test_get_bash_commands(self, parser: TranscriptParser):
        cmds = parser.get_bash_commands()
        assert len(cmds) == 2
        assert "build-kg" in cmds[0]
        assert "query" in cmds[1]

    def test_has_tool_call(self, parser: TranscriptParser):
        assert parser.has_tool_call("Bash")
        assert parser.has_tool_call("Read")
        assert parser.has_tool_call("Write")
        assert not parser.has_tool_call("Grep")

    def test_has_tool_call_with_input_match(self, parser: TranscriptParser):
        assert parser.has_tool_call("Read", file_path="/contracts/Vault.sol")
        assert not parser.has_tool_call("Read", file_path="/contracts/Token.sol")

    def test_first_tool_call(self, parser: TranscriptParser):
        first_bash = parser.first_tool_call("Bash")
        assert first_bash is not None
        assert "build-kg" in first_bash.tool_input["command"]

        assert parser.first_tool_call("Glob") is None

    def test_tool_calls_matching(self, parser: TranscriptParser):
        bash_calls = parser.tool_calls_matching("Bash")
        assert len(bash_calls) == 2

        query_calls = parser.tool_calls_matching("Bash", command="uv run alphaswarm query 'reentrancy'")
        assert len(query_calls) == 1

    def test_has_bskg_query(self, parser: TranscriptParser):
        assert parser.has_bskg_query()

    def test_bskg_query_index(self, parser: TranscriptParser):
        # build-kg is index 0, query is index 1 — both are BSKG-related
        idx = parser.bskg_query_index()
        assert idx == 0

    def test_first_conclusion_index(self, parser: TranscriptParser):
        idx = parser.first_conclusion_index()
        assert idx == 3  # The Write call with "vulnerability confirmed"

    def test_no_bskg_query(self, tmp_path: Path):
        records = [
            _assistant_tool_use("Read", {"file_path": "/f"}, "tu_1"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        assert not parser.has_bskg_query()
        assert parser.bskg_query_index() is None

    def test_no_conclusion(self, tmp_path: Path):
        records = [
            _assistant_tool_use("Bash", {"command": "uv run alphaswarm query 'x'"}, "tu_1"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        assert parser.first_conclusion_index() is None


class TestTranscriptParserMetrics:
    def test_record_count(self, tmp_path: Path):
        records = [{"type": "user"}, {"type": "assistant"}, {"type": "progress"}]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        assert parser.record_count == 3

    def test_total_chars(self, tmp_path: Path):
        records = [{"type": "user", "message": {"content": "hello"}}]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        assert parser.total_chars > 0


# ---------------------------------------------------------------------------
# Helpers for timestamped records
# ---------------------------------------------------------------------------


def _assistant_tool_use_ts(
    tool_name: str, tool_input: dict, tool_id: str, timestamp: str
) -> dict:
    """Create an assistant record with a tool_use block and a timestamp."""
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


def _user_tool_result_ts(tool_id: str, result_text: str, timestamp: str) -> dict:
    """Create a user record with a tool_result block and a timestamp."""
    return {
        "type": "user",
        "timestamp": timestamp,
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result_text,
                }
            ]
        },
    }


# ---------------------------------------------------------------------------
# BSKGQuery extraction tests
# ---------------------------------------------------------------------------


class TestBSKGQueryExtraction:
    def test_extracts_bskg_queries_from_alphaswarm_commands(self, tmp_path: Path):
        """BSKGQuery extraction correctly identifies alphaswarm commands."""
        records = [
            _assistant_tool_use(
                "Bash",
                {"command": "uv run alphaswarm build-kg contracts/"},
                "tu_1",
            ),
            _user_tool_result("tu_1", "Graph built: 42 nodes, 15 edges"),
            _assistant_tool_use(
                "Bash",
                {"command": "uv run alphaswarm query 'functions without access control'"},
                "tu_2",
            ),
            _user_tool_result("tu_2", "Found 3 matching functions"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))

        queries = parser.get_bskg_queries()
        assert len(queries) == 2
        assert queries[0].query_type == "build-kg"
        assert queries[0].query_text == "contracts/"
        assert queries[0].tool_call_index == 0
        assert queries[1].query_type == "query"
        assert queries[1].query_text == "functions without access control"
        assert queries[1].tool_call_index == 1

    def test_returns_empty_list_when_no_alphaswarm_commands(self, tmp_path: Path):
        records = [
            _assistant_tool_use("Bash", {"command": "ls -la"}, "tu_1"),
            _user_tool_result("tu_1", "file1.txt"),
            _assistant_tool_use("Read", {"file_path": "/foo"}, "tu_2"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        assert parser.get_bskg_queries() == []

    def test_query_type_classification(self, tmp_path: Path):
        """Test classification: build-kg, query, pattern-query, vulndocs."""
        records = [
            _assistant_tool_use(
                "Bash", {"command": "uv run alphaswarm build-kg src/"}, "tu_1"
            ),
            _user_tool_result("tu_1", "built"),
            _assistant_tool_use(
                "Bash",
                {"command": "uv run alphaswarm query 'reentrancy'"},
                "tu_2",
            ),
            _user_tool_result("tu_2", "nodes"),
            _assistant_tool_use(
                "Bash",
                {"command": "uv run alphaswarm query 'pattern:weak-access-control'"},
                "tu_3",
            ),
            _user_tool_result("tu_3", "pattern match"),
            _assistant_tool_use(
                "Bash",
                {"command": "uv run alphaswarm vulndocs validate vulndocs/"},
                "tu_4",
            ),
            _user_tool_result("tu_4", "validated"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))

        queries = parser.get_bskg_queries()
        assert len(queries) == 4
        assert queries[0].query_type == "build-kg"
        assert queries[1].query_type == "query"
        assert queries[2].query_type == "pattern-query"
        assert queries[3].query_type == "vulndocs"

    def test_result_snippet_up_to_2000_chars(self, tmp_path: Path):
        long_result = "x" * 3000
        records = [
            _assistant_tool_use(
                "Bash", {"command": "uv run alphaswarm query 'all'"}, "tu_1"
            ),
            _user_tool_result("tu_1", long_result),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        queries = parser.get_bskg_queries()
        assert len(queries) == 1
        assert len(queries[0].result_snippet) == 2000

    def test_filters_out_non_bskg_bash_calls(self, tmp_path: Path):
        """Non-alphaswarm Bash calls are not treated as BSKG queries."""
        records = [
            _assistant_tool_use("Bash", {"command": "ls -la"}, "tu_1"),
            _user_tool_result("tu_1", "files"),
            _assistant_tool_use("Bash", {"command": "git status"}, "tu_2"),
            _user_tool_result("tu_2", "clean"),
            _assistant_tool_use(
                "Bash", {"command": "uv run alphaswarm query 'x'"}, "tu_3"
            ),
            _user_tool_result("tu_3", "result"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        queries = parser.get_bskg_queries()
        assert len(queries) == 1
        assert queries[0].tool_call_index == 2

    def test_cited_in_conclusion_detection(self, tmp_path: Path):
        """Citation heuristic detects result substrings in later Write calls."""
        # Result is 30 chars long; a 20-char substring should match in Write content
        result_text = "Found vulnerability in transfer function"
        records = [
            _assistant_tool_use(
                "Bash", {"command": "uv run alphaswarm query 'vuln'"}, "tu_1"
            ),
            _user_tool_result("tu_1", result_text),
            _assistant_tool_use(
                "Write",
                {"file_path": "/report.md", "content": f"Analysis: {result_text} confirmed"},
                "tu_2",
            ),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        queries = parser.get_bskg_queries()
        assert len(queries) == 1
        assert queries[0].cited_in_conclusion is True

    def test_cited_in_conclusion_false_when_not_referenced(self, tmp_path: Path):
        records = [
            _assistant_tool_use(
                "Bash", {"command": "uv run alphaswarm query 'reentrancy'"}, "tu_1"
            ),
            _user_tool_result("tu_1", "Some unique BSKG query result text here for testing"),
            _assistant_tool_use(
                "Write",
                {"file_path": "/report.md", "content": "Completely unrelated content"},
                "tu_2",
            ),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        queries = parser.get_bskg_queries()
        assert len(queries) == 1
        assert queries[0].cited_in_conclusion is False


# ---------------------------------------------------------------------------
# Graph citation rate tests
# ---------------------------------------------------------------------------


class TestGraphCitationRate:
    def test_returns_none_when_no_queries(self, tmp_path: Path):
        records = [_assistant_tool_use("Read", {"file_path": "/f"}, "tu_1")]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        rate = parser.graph_citation_rate()
        assert rate is None

    def test_returns_one_when_all_cited(self, tmp_path: Path):
        result_text = "Found 3 vulnerable transfer functions in contract"
        records = [
            _assistant_tool_use(
                "Bash", {"command": "uv run alphaswarm query 'vuln'"}, "tu_1"
            ),
            _user_tool_result("tu_1", result_text),
            _assistant_tool_use(
                "Write",
                {"file_path": "/r.md", "content": f"Report: {result_text}"},
                "tu_2",
            ),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        assert parser.graph_citation_rate() == 1.0

    def test_returns_fraction_when_partially_cited(self, tmp_path: Path):
        cited_result = "Found reentrant call chain in withdraw function"
        uncited_result = "Completely different unique analysis output here"
        records = [
            _assistant_tool_use(
                "Bash", {"command": "uv run alphaswarm query 'a'"}, "tu_1"
            ),
            _user_tool_result("tu_1", cited_result),
            _assistant_tool_use(
                "Bash", {"command": "uv run alphaswarm query 'b'"}, "tu_2"
            ),
            _user_tool_result("tu_2", uncited_result),
            _assistant_tool_use(
                "Write",
                {"file_path": "/r.md", "content": f"Report: {cited_result}"},
                "tu_3",
            ),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        rate = parser.graph_citation_rate()
        assert rate == 0.5


# ---------------------------------------------------------------------------
# Raw message accessor tests
# ---------------------------------------------------------------------------


class TestRawMessageAccessors:
    def test_get_raw_messages_returns_copy(self, tmp_path: Path):
        records = [{"type": "user"}, {"type": "assistant"}]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        raw = parser.get_raw_messages()
        assert len(raw) == 2
        # Verify it's a copy (mutating returned list doesn't affect parser)
        raw.append({"type": "extra"})
        assert parser.record_count == 2

    def test_get_message_at_valid_index(self, tmp_path: Path):
        records = [
            {"type": "user", "data": "first"},
            {"type": "assistant", "data": "second"},
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        msg = parser.get_message_at(0)
        assert msg["data"] == "first"
        msg = parser.get_message_at(1)
        assert msg["data"] == "second"

    def test_get_message_at_out_of_bounds(self, tmp_path: Path):
        records = [{"type": "user"}]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        with pytest.raises(IndexError):
            parser.get_message_at(5)

    def test_get_messages_between_returns_slice(self, tmp_path: Path):
        records = [
            {"type": "user", "idx": 0},
            {"type": "assistant", "idx": 1},
            {"type": "user", "idx": 2},
            {"type": "assistant", "idx": 3},
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        sliced = parser.get_messages_between(1, 3)
        assert len(sliced) == 2
        assert sliced[0]["idx"] == 1
        assert sliced[1]["idx"] == 2

    def test_get_messages_between_empty_when_start_gte_end(self, tmp_path: Path):
        records = [{"type": "user"}, {"type": "assistant"}]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        assert parser.get_messages_between(1, 1) == []
        assert parser.get_messages_between(2, 1) == []

    def test_get_messages_between_raises_on_negative_start(self, tmp_path: Path):
        records = [{"type": "user"}]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        with pytest.raises(IndexError):
            parser.get_messages_between(-1, 1)

    def test_get_messages_between_raises_on_end_exceeding_count(self, tmp_path: Path):
        records = [{"type": "user"}]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        with pytest.raises(IndexError):
            parser.get_messages_between(0, 5)


# ---------------------------------------------------------------------------
# ToolCall timing fields tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# get_text_between_tools tests
# ---------------------------------------------------------------------------


class TestGetTextBetweenTools:
    def _assistant_text(self, text: str) -> dict:
        """Create an assistant record with just text content."""
        return {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": text}]
            },
        }

    def test_extracts_text_between_tool_pair(self, tmp_path: Path):
        records = [
            _assistant_tool_use("Bash", {"command": "uv run alphaswarm build-kg c/"}, "tu_1"),
            _user_tool_result("tu_1", "Graph built"),
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "The graph shows a CEI violation."},
                    ]
                },
            },
            _assistant_tool_use("Write", {"file_path": "/report.md", "content": "done"}, "tu_2"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        texts = parser.get_text_between_tools("Bash", "Write")
        assert len(texts) == 1
        assert "CEI violation" in texts[0]

    def test_returns_empty_when_no_matching_pair(self, tmp_path: Path):
        records = [
            _assistant_tool_use("Read", {"file_path": "/f"}, "tu_1"),
            _user_tool_result("tu_1", "content"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        assert parser.get_text_between_tools("Bash", "Write") == []

    def test_returns_empty_when_no_text_between(self, tmp_path: Path):
        records = [
            _assistant_tool_use("Bash", {"command": "ls"}, "tu_1"),
            _user_tool_result("tu_1", "files"),
            _assistant_tool_use("Write", {"file_path": "/r.md", "content": "x"}, "tu_2"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        # No assistant text records between the two tool calls
        assert parser.get_text_between_tools("Bash", "Write") == []

    def test_multiple_pairs(self, tmp_path: Path):
        records = [
            _assistant_tool_use("Bash", {"command": "cmd1"}, "tu_1"),
            _user_tool_result("tu_1", "r1"),
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "First analysis"}]},
            },
            _assistant_tool_use("Write", {"file_path": "/a", "content": "x"}, "tu_2"),
            _user_tool_result("tu_2", "ok"),
            _assistant_tool_use("Bash", {"command": "cmd2"}, "tu_3"),
            _user_tool_result("tu_3", "r2"),
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Second analysis"}]},
            },
            _assistant_tool_use("Write", {"file_path": "/b", "content": "y"}, "tu_4"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        texts = parser.get_text_between_tools("Bash", "Write")
        assert len(texts) == 2
        assert "First" in texts[0]
        assert "Second" in texts[1]


class TestToolCallTimingFields:
    def test_timestamp_populated_from_record(self, tmp_path: Path):
        records = [
            _assistant_tool_use_ts(
                "Bash", {"command": "ls"}, "tu_1", "2026-01-15T10:30:00Z"
            ),
            _user_tool_result_ts("tu_1", "files", "2026-01-15T10:30:02Z"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        calls = parser.get_tool_calls()
        assert len(calls) == 1
        assert calls[0].timestamp == "2026-01-15T10:30:00Z"

    def test_duration_ms_computed_from_timestamps(self, tmp_path: Path):
        records = [
            _assistant_tool_use_ts(
                "Bash", {"command": "sleep 1"}, "tu_1", "2026-01-15T10:30:00Z"
            ),
            _user_tool_result_ts("tu_1", "done", "2026-01-15T10:30:02Z"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        calls = parser.get_tool_calls()
        assert calls[0].duration_ms == 2000

    def test_timestamp_none_when_not_in_record(self, tmp_path: Path):
        """Existing records without timestamps get None (backward compat)."""
        records = [
            _assistant_tool_use("Bash", {"command": "ls"}, "tu_1"),
            _user_tool_result("tu_1", "files"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        calls = parser.get_tool_calls()
        assert calls[0].timestamp is None
        assert calls[0].duration_ms is None

    def test_content_block_populated(self, tmp_path: Path):
        records = [
            _assistant_tool_use("Bash", {"command": "ls"}, "tu_1"),
        ]
        parser = TranscriptParser(_write_jsonl(tmp_path, records))
        calls = parser.get_tool_calls()
        assert calls[0].content_block["type"] == "tool_use"
        assert calls[0].content_block["id"] == "tu_1"

    def test_toolcall_backward_compatible_construction(self):
        """Existing code constructing ToolCall with positional/keyword args still works."""
        tc = ToolCall(tool_name="Bash", tool_input={"command": "ls"}, tool_result="ok", index=0)
        assert tc.timestamp is None
        assert tc.duration_ms is None
        assert tc.content_block == {}
