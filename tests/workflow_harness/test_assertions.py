"""Tests for assertions.py — all 7 assertion categories.

Tests both PASS and FAIL cases for each assertion function.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .lib.controller_events import EventStream
from .lib.transcript_parser import TranscriptParser
from .lib import assertions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stream(events: list[dict]) -> EventStream:
    return EventStream(events)


def _write_jsonl(tmp_path: Path, records: list[dict]) -> TranscriptParser:
    p = tmp_path / "transcript.jsonl"
    with open(p, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return TranscriptParser(p)


def _tool_use(name: str, input_: dict, tid: str = "tu_1") -> dict:
    return {
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "id": tid, "name": name, "input": input_}]},
    }


# ---------------------------------------------------------------------------
# Category 1: Agent Lifecycle
# ---------------------------------------------------------------------------


class TestAgentLifecycle:
    def test_assert_agent_spawned_pass(self):
        stream = _stream([{"type": "agent:spawned", "agent_type": "attacker"}])
        assertions.assert_agent_spawned(stream, "attacker")

    def test_assert_agent_spawned_fail(self):
        stream = _stream([{"type": "agent:spawned", "agent_type": "defender"}])
        with pytest.raises(AssertionError, match="attacker"):
            assertions.assert_agent_spawned(stream, "attacker")

    def test_assert_agent_exited_cleanly_pass(self):
        stream = _stream([
            {"type": "agent:spawned", "agent_type": "attacker"},
            {"type": "agent:exited", "agent_type": "attacker"},
        ])
        assertions.assert_agent_exited_cleanly(stream, "attacker")

    def test_assert_agent_exited_cleanly_fail(self):
        stream = _stream([{"type": "agent:spawned", "agent_type": "attacker"}])
        with pytest.raises(AssertionError, match="attacker"):
            assertions.assert_agent_exited_cleanly(stream, "attacker")

    def test_assert_spawn_order_pass(self):
        stream = _stream([
            {"type": "agent:spawned", "agent_type": "attacker"},
            {"type": "agent:spawned", "agent_type": "defender"},
        ])
        assertions.assert_spawn_order(stream, "attacker", "defender")

    def test_assert_spawn_order_fail_reversed(self):
        stream = _stream([
            {"type": "agent:spawned", "agent_type": "defender"},
            {"type": "agent:spawned", "agent_type": "attacker"},
        ])
        with pytest.raises(AssertionError, match="before"):
            assertions.assert_spawn_order(stream, "attacker", "defender")

    def test_assert_spawn_order_fail_missing(self):
        stream = _stream([{"type": "agent:spawned", "agent_type": "attacker"}])
        with pytest.raises(AssertionError, match="never spawned"):
            assertions.assert_spawn_order(stream, "attacker", "defender")

    def test_assert_min_agents_pass(self):
        stream = _stream([
            {"type": "agent:spawned", "agent_type": "a"},
            {"type": "agent:spawned", "agent_type": "b"},
            {"type": "agent:spawned", "agent_type": "c"},
        ])
        assertions.assert_min_agents(stream, 3)
        assertions.assert_min_agents(stream, 1)

    def test_assert_min_agents_fail(self):
        stream = _stream([{"type": "agent:spawned", "agent_type": "a"}])
        with pytest.raises(AssertionError, match="at least 3"):
            assertions.assert_min_agents(stream, 3)


# ---------------------------------------------------------------------------
# Category 2: Tool Sequence
# ---------------------------------------------------------------------------


class TestToolSequence:
    def test_assert_tool_sequence_pass(self, tmp_path: Path):
        parser = _write_jsonl(tmp_path, [
            _tool_use("Read", {}, "tu_1"),
            _tool_use("Grep", {}, "tu_2"),
            _tool_use("Bash", {}, "tu_3"),
        ])
        assertions.assert_tool_sequence(parser, ["Read", "Grep", "Bash"])

    def test_assert_tool_sequence_pass_nonconsecutive(self, tmp_path: Path):
        parser = _write_jsonl(tmp_path, [
            _tool_use("Read", {}, "tu_1"),
            _tool_use("Glob", {}, "tu_2"),
            _tool_use("Bash", {}, "tu_3"),
        ])
        assertions.assert_tool_sequence(parser, ["Read", "Bash"])

    def test_assert_tool_sequence_fail(self, tmp_path: Path):
        parser = _write_jsonl(tmp_path, [
            _tool_use("Bash", {}, "tu_1"),
            _tool_use("Read", {}, "tu_2"),
        ])
        with pytest.raises(AssertionError, match="not found in order"):
            assertions.assert_tool_sequence(parser, ["Read", "Bash", "Grep"])

    def test_assert_tool_used_pass(self, tmp_path: Path):
        parser = _write_jsonl(tmp_path, [_tool_use("Bash", {}, "tu_1")])
        assertions.assert_tool_used(parser, "Bash")

    def test_assert_tool_used_fail(self, tmp_path: Path):
        parser = _write_jsonl(tmp_path, [_tool_use("Read", {}, "tu_1")])
        with pytest.raises(AssertionError, match="Bash"):
            assertions.assert_tool_used(parser, "Bash")

    def test_assert_bash_command_ran_pass(self, tmp_path: Path):
        parser = _write_jsonl(tmp_path, [
            _tool_use("Bash", {"command": "uv run alphaswarm build-kg contracts/"}, "tu_1"),
        ])
        assertions.assert_bash_command_ran(parser, "build-kg")

    def test_assert_bash_command_ran_fail(self, tmp_path: Path):
        parser = _write_jsonl(tmp_path, [
            _tool_use("Bash", {"command": "ls -la"}, "tu_1"),
        ])
        with pytest.raises(AssertionError, match="build-kg"):
            assertions.assert_bash_command_ran(parser, "build-kg")


# ---------------------------------------------------------------------------
# Category 3: Graph-First Compliance
# ---------------------------------------------------------------------------


class TestGraphFirstCompliance:
    def test_assert_graph_first_pass(self, tmp_path: Path):
        """BSKG query before conclusion."""
        parser = _write_jsonl(tmp_path, [
            _tool_use("Bash", {"command": "uv run alphaswarm query 'access'"}, "tu_1"),
            _tool_use("Write", {"file_path": "/report.md", "content": "finding: vulnerability confirmed"}, "tu_2"),
        ])
        assertions.assert_graph_first(parser)

    def test_assert_graph_first_fail_no_query(self, tmp_path: Path):
        parser = _write_jsonl(tmp_path, [
            _tool_use("Write", {"file_path": "/r.md", "content": "conclusion"}, "tu_1"),
        ])
        with pytest.raises(AssertionError, match="No BSKG query"):
            assertions.assert_graph_first(parser)

    def test_assert_graph_first_fail_wrong_order(self, tmp_path: Path):
        """Conclusion before query."""
        parser = _write_jsonl(tmp_path, [
            _tool_use("Write", {"file_path": "/r.md", "content": "finding: vulnerability"}, "tu_1"),
            _tool_use("Bash", {"command": "uv run alphaswarm query 'x'"}, "tu_2"),
        ])
        with pytest.raises(AssertionError, match="must come before"):
            assertions.assert_graph_first(parser)

    def test_assert_graph_first_no_conclusion_still_passes(self, tmp_path: Path):
        """If there's a query but no conclusion yet, that's fine."""
        parser = _write_jsonl(tmp_path, [
            _tool_use("Bash", {"command": "uv run alphaswarm build-kg contracts/"}, "tu_1"),
        ])
        assertions.assert_graph_first(parser)


# ---------------------------------------------------------------------------
# Category 4: Evidence Validity
# ---------------------------------------------------------------------------


class TestEvidenceValidity:
    def test_assert_findings_have_locations_pass(self):
        findings = [
            {"pattern": "reentrancy", "location": "Vault.sol:45"},
            {"pattern": "access-control", "location": "Token.sol:withdraw"},
        ]
        assertions.assert_findings_have_locations(findings)

    def test_assert_findings_have_locations_fail(self):
        findings = [
            {"pattern": "reentrancy", "location": ""},
        ]
        with pytest.raises(AssertionError, match="Finding 0"):
            assertions.assert_findings_have_locations(findings)

    def test_assert_findings_cite_graph_nodes_pass(self):
        findings = [
            {"pattern": "x", "graph_nodes": ["node-1", "node-2"]},
        ]
        assertions.assert_findings_cite_graph_nodes(findings)

    def test_assert_findings_cite_graph_nodes_nested(self):
        findings = [
            {"pattern": "x", "evidence": {"graph_nodes": ["n1"]}},
        ]
        assertions.assert_findings_cite_graph_nodes(findings)

    def test_assert_findings_cite_graph_nodes_fail(self):
        findings = [{"pattern": "x"}]
        with pytest.raises(AssertionError, match="Finding 0"):
            assertions.assert_findings_cite_graph_nodes(findings)


# ---------------------------------------------------------------------------
# Category 5: Task State Machine
# ---------------------------------------------------------------------------


class TestTaskStateMachine:
    def test_assert_task_completed_pass(self):
        stream = _stream([
            {"type": "task:completed", "subject": "Run Slither analysis"},
        ])
        assertions.assert_task_completed(stream, "Slither")

    def test_assert_task_completed_fail(self):
        stream = _stream([
            {"type": "task:completed", "subject": "Run Aderyn analysis"},
        ])
        with pytest.raises(AssertionError, match="Slither"):
            assertions.assert_task_completed(stream, "Slither")

    def test_assert_all_tasks_completed_pass(self):
        stream = _stream([
            {"type": "task:completed", "subject": "Task A"},
        ])
        assertions.assert_all_tasks_completed(stream)

    def test_assert_all_tasks_completed_fail_no_tasks(self):
        stream = _stream([{"type": "message"}])
        with pytest.raises(AssertionError, match="No tasks"):
            assertions.assert_all_tasks_completed(stream)

    def test_assert_all_tasks_completed_fail_with_errors(self):
        stream = _stream([
            {"type": "task:completed", "subject": "A"},
            {"type": "error", "message": "something broke"},
        ])
        with pytest.raises(AssertionError, match="Errors"):
            assertions.assert_all_tasks_completed(stream)


# ---------------------------------------------------------------------------
# Category 6: Performance Bounds
# ---------------------------------------------------------------------------


class TestPerformanceBounds:
    def test_assert_duration_between_pass(self):
        stream = _stream([
            {"type": "start", "timestamp": 100.0},
            {"type": "end", "timestamp": 130.0},
        ])
        assertions.assert_duration_between(stream, 20.0, 60.0)

    def test_assert_duration_between_fail_too_short(self):
        stream = _stream([
            {"type": "start", "timestamp": 100.0},
            {"type": "end", "timestamp": 101.0},
        ])
        with pytest.raises(AssertionError, match="not in"):
            assertions.assert_duration_between(stream, 5.0, 60.0)

    def test_assert_duration_between_fail_too_long(self):
        stream = _stream([
            {"type": "start", "timestamp": 100.0},
            {"type": "end", "timestamp": 300.0},
        ])
        with pytest.raises(AssertionError, match="not in"):
            assertions.assert_duration_between(stream, 5.0, 60.0)

    def test_assert_cost_nonzero_pass(self):
        stream = _stream([{"type": "result", "cost_usd": 0.01}])
        assertions.assert_cost_nonzero(stream)

    def test_assert_cost_nonzero_fail(self):
        stream = _stream([{"type": "result"}])
        with pytest.raises(AssertionError, match="non-zero cost"):
            assertions.assert_cost_nonzero(stream)


# ---------------------------------------------------------------------------
# Category 7: Anti-Fabrication
# ---------------------------------------------------------------------------


class TestAntiFabrication:
    def test_assert_not_fabricated_pass(self, tmp_path: Path):
        stream = _stream([
            {"type": "start", "timestamp": 100.0},
            {"type": "result", "cost_usd": 0.05, "timestamp": 120.0},
        ])
        # Need a parser with tool calls and enough content
        records = [_tool_use("Bash", {"command": "uv run alphaswarm query 'x'"}, "tu_1")]
        # Pad transcript to exceed 500 chars
        records.append({"type": "progress", "message": {"content": "x" * 600}})
        parser = _write_jsonl(tmp_path, records)
        assertions.assert_not_fabricated(stream, parser)

    def test_assert_not_fabricated_fail_too_fast(self, tmp_path: Path):
        stream = _stream([
            {"type": "start", "timestamp": 100.0},
            {"type": "end", "timestamp": 101.0},  # Only 1 second
        ])
        records = [_tool_use("Bash", {"command": "echo"}, "tu_1")]
        records.append({"type": "progress", "message": {"content": "x" * 600}})
        parser = _write_jsonl(tmp_path, records)
        with pytest.raises(AssertionError, match="suspiciously fast"):
            assertions.assert_not_fabricated(stream, parser)

    def test_assert_not_fabricated_fail_no_tools(self, tmp_path: Path):
        stream = _stream([
            {"type": "start", "timestamp": 100.0},
            {"type": "end", "timestamp": 120.0},
        ])
        # No tool calls at all, but enough chars
        records = [{"type": "user", "message": {"content": "x" * 600}}]
        parser = _write_jsonl(tmp_path, records)
        with pytest.raises(AssertionError, match="No tool calls"):
            assertions.assert_not_fabricated(stream, parser)

    def test_assert_not_fabricated_fail_tiny_transcript(self, tmp_path: Path):
        stream = _stream([
            {"type": "start", "timestamp": 100.0},
            {"type": "end", "timestamp": 120.0},
        ])
        records = [_tool_use("Bash", {"command": "x"}, "tu_1")]
        parser = _write_jsonl(tmp_path, records)
        with pytest.raises(AssertionError, match="chars"):
            assertions.assert_not_fabricated(stream, parser)
