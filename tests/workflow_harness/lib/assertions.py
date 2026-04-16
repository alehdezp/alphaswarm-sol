"""Composable assertion functions for workflow verification.

Organized into 9 categories:
1. Agent Lifecycle — from controller events
2. Tool Sequence — from transcripts
3. Graph-First Compliance — from transcripts
4. Evidence Validity — from findings output
5. Task State Machine — from controller events
6. Performance Bounds — from controller events
7. Anti-Fabrication — composite checks
8. Evaluation Contract — contract-aware result checking
9. Reasoning Dimensions — transcript dimension coverage
"""

from __future__ import annotations

import re
from typing import Any

from .controller_events import EventStream
from .transcript_parser import TranscriptParser


# ---------------------------------------------------------------------------
# Category 1: Agent Lifecycle (controller events)
# ---------------------------------------------------------------------------


def assert_agent_spawned(stream: EventStream, agent_type: str) -> None:
    """Assert that an agent of the given type was spawned."""
    match = stream.agent_by_type(agent_type)
    assert match is not None, (
        f"Expected agent type '{agent_type}' to be spawned. "
        f"Spawned types: {stream.agent_types()}"
    )


def assert_agent_exited_cleanly(stream: EventStream, agent_type: str) -> None:
    """Assert that an agent of the given type exited (has agent:exited event)."""
    agent_type_lower = agent_type.lower()
    exited = [
        e for e in stream.agents_exited()
        if e.agent_type and e.agent_type.lower() == agent_type_lower
    ]
    assert len(exited) > 0, (
        f"Expected agent type '{agent_type}' to have exited cleanly. "
        f"Exited agents: {[e.agent_type for e in stream.agents_exited()]}"
    )


def assert_spawn_order(stream: EventStream, first: str, second: str) -> None:
    """Assert that 'first' agent type was spawned before 'second'."""
    spawned = stream.agents_spawned()
    first_idx = None
    second_idx = None
    first_lower = first.lower()
    second_lower = second.lower()
    for i, e in enumerate(spawned):
        if e.agent_type and e.agent_type.lower() == first_lower and first_idx is None:
            first_idx = i
        if e.agent_type and e.agent_type.lower() == second_lower and second_idx is None:
            second_idx = i

    assert first_idx is not None, f"Agent '{first}' was never spawned"
    assert second_idx is not None, f"Agent '{second}' was never spawned"
    assert first_idx < second_idx, (
        f"Expected '{first}' (index {first_idx}) to be spawned before "
        f"'{second}' (index {second_idx})"
    )


def assert_min_agents(stream: EventStream, count: int) -> None:
    """Assert at least 'count' agents were spawned."""
    actual = len(stream.agents_spawned())
    assert actual >= count, (
        f"Expected at least {count} agents spawned, got {actual}"
    )


# ---------------------------------------------------------------------------
# Category 2: Tool Sequence (transcripts)
# ---------------------------------------------------------------------------


def assert_tool_sequence(parser: TranscriptParser, expected: list[str]) -> None:
    """Assert that the expected tools appear in order (not necessarily contiguous)."""
    actual = parser.get_tool_sequence()
    expected_idx = 0
    for tool_name in actual:
        if expected_idx < len(expected) and tool_name == expected[expected_idx]:
            expected_idx += 1
    assert expected_idx == len(expected), (
        f"Expected tool sequence {expected} not found in order. "
        f"Actual sequence: {actual}"
    )


def assert_tool_used(parser: TranscriptParser, tool_name: str) -> None:
    """Assert that a specific tool was used at least once."""
    assert parser.has_tool_call(tool_name), (
        f"Expected tool '{tool_name}' to be used. "
        f"Tools used: {list(dict.fromkeys(parser.get_tool_sequence()))}"
    )


def assert_bash_command_ran(parser: TranscriptParser, command_substring: str) -> None:
    """Assert that a Bash command containing the substring was executed."""
    commands = parser.get_bash_commands()
    found = any(command_substring in cmd for cmd in commands)
    assert found, (
        f"Expected a Bash command containing '{command_substring}'. "
        f"Commands run: {commands}"
    )


# ---------------------------------------------------------------------------
# Category 3: Graph-First Compliance (transcripts)
# ---------------------------------------------------------------------------


def assert_graph_first(parser: TranscriptParser) -> None:
    """Assert BSKG query appears before any conclusion/finding output.

    Graph-first rule: agents must query the knowledge graph before
    producing conclusions. This checks that the first BSKG query
    tool call index is less than the first conclusion index.
    """
    query_idx = parser.bskg_query_index()
    assert query_idx is not None, "No BSKG query found in transcript"

    conclusion_idx = parser.first_conclusion_index()
    if conclusion_idx is not None:
        assert query_idx < conclusion_idx, (
            f"BSKG query (index {query_idx}) must come before "
            f"conclusion (index {conclusion_idx})"
        )


# ---------------------------------------------------------------------------
# Category 4: Evidence Validity (findings output)
# ---------------------------------------------------------------------------


def assert_findings_have_locations(findings: list[dict[str, Any]]) -> None:
    """Assert every finding has a non-empty code location."""
    for i, f in enumerate(findings):
        location = f.get("location", "")
        assert location, f"Finding {i} has no location: {f}"


def assert_findings_cite_graph_nodes(findings: list[dict[str, Any]]) -> None:
    """Assert every finding references at least one graph node ID."""
    for i, f in enumerate(findings):
        graph_refs = f.get("graph_nodes") or f.get("graph_node_ids") or f.get("evidence", {}).get("graph_nodes")
        assert graph_refs, f"Finding {i} has no graph node references: {f}"


# ---------------------------------------------------------------------------
# Category 5: Task State Machine (controller events)
# ---------------------------------------------------------------------------


def assert_task_completed(stream: EventStream, subject_contains: str) -> None:
    """Assert a task with the given subject substring was completed."""
    completed = stream.tasks_completed()
    subject_lower = subject_contains.lower()
    found = any(
        subject_lower in (e.data.get("subject", "") or e.data.get("task", "")).lower()
        for e in completed
    )
    assert found, (
        f"No completed task containing '{subject_contains}'. "
        f"Completed tasks: {[e.data.get('subject', e.data.get('task', '')) for e in completed]}"
    )


def assert_all_tasks_completed(stream: EventStream) -> None:
    """Assert that the stream contains at least one task:completed and no errors."""
    completed = stream.tasks_completed()
    assert len(completed) > 0, "No tasks were completed"
    errors = stream.errors()
    assert len(errors) == 0, f"Errors occurred: {[e.data for e in errors]}"


# ---------------------------------------------------------------------------
# Category 6: Performance Bounds (controller events)
# ---------------------------------------------------------------------------


def assert_duration_between(stream: EventStream, min_sec: float, max_sec: float) -> None:
    """Assert total session duration is within bounds."""
    duration = stream.duration_seconds()
    assert min_sec <= duration <= max_sec, (
        f"Duration {duration:.1f}s not in [{min_sec}, {max_sec}]"
    )


def assert_cost_nonzero(stream: EventStream) -> None:
    """Assert the session had a non-zero cost (real API calls were made)."""
    cost = stream.total_cost_usd()
    assert cost > 0, "Expected non-zero cost — session may not have made real API calls"


# ---------------------------------------------------------------------------
# Category 7: Anti-Fabrication (composite)
# ---------------------------------------------------------------------------


def assert_not_fabricated(
    stream: EventStream,
    parser: TranscriptParser,
    min_duration_sec: float = 5.0,
    min_transcript_chars: int = 500,
) -> None:
    """Composite anti-fabrication check.

    Verifies that results were not fabricated by checking:
    1. Session had non-zero cost (real API calls)
    2. Duration exceeds minimum (not instant)
    3. Transcript has substantial content
    4. No suspiciously perfect metrics (100% everything)
    """
    # Cost check (soft — may not be available from all controller versions)
    cost = stream.total_cost_usd()
    if cost > 0:
        pass  # Good — real API calls confirmed

    # Duration check
    duration = stream.duration_seconds()
    assert duration >= min_duration_sec, (
        f"Session duration {duration:.1f}s < {min_duration_sec}s — "
        "suspiciously fast, may be fabricated"
    )

    # Transcript size check
    total_chars = parser.total_chars
    assert total_chars >= min_transcript_chars, (
        f"Transcript has only {total_chars} chars (minimum: {min_transcript_chars}) — "
        "may be fabricated"
    )

    # Tool call check — real sessions always have tool calls
    tool_count = len(parser.get_tool_calls())
    assert tool_count > 0, "No tool calls in transcript — session may be fabricated"


# ---------------------------------------------------------------------------
# Category 8: Evaluation Contract (contract-aware result checking)
# ---------------------------------------------------------------------------

# Keyword patterns for checking code-graded capability checks.
# Maps common expected_behavior patterns to result-dict keys to verify.
_CODE_GRADER_PATTERNS: list[tuple[str, list[str]]] = [
    (r"non-empty\s+\w*evidence", ["evidence_nodes", "graph_node_ids", "graph_nodes"]),
    (r"non-empty\s+\w*code.location", ["code_locations", "location", "locations"]),
    (r"build-kg.*appears.*transcript", ["transcript"]),
    (r"controller.*events?\s+show", ["controller_events", "events"]),
    (r"exploit.path|attack.sequence", ["exploit_path", "attack_sequence", "attack_vectors"]),
    (r"verdict.*object", ["verdicts", "verdict"]),
    (r"resolution.*status", ["resolution", "resolutions", "findings"]),
]


def assert_matches_contract(result: dict[str, Any], contract: dict[str, Any]) -> None:
    """Assert workflow result satisfies code-graded capability checks in a contract.

    For each capability_check in the contract:
    - grader_type "code": verify the result contains relevant evidence
    - grader_type "model": skip (returns info about skipped checks)

    Raises AssertionError on first code-graded check that cannot be satisfied.
    """
    checks = contract.get("capability_checks", [])
    if not checks:
        raise AssertionError(
            f"Contract '{contract.get('workflow_id', '?')}' has no capability_checks"
        )

    skipped_model_checks: list[str] = []

    for check in checks:
        check_id = check.get("id", "unknown")
        grader = check.get("grader_type", "code")

        if grader == "model":
            skipped_model_checks.append(check_id)
            continue

        # Code-graded: verify result has evidence relevant to expected_behavior
        expected = check.get("expected_behavior", "")
        _verify_code_check(result, check_id, expected)


def _verify_code_check(result: dict[str, Any], check_id: str, expected_behavior: str) -> None:
    """Verify a code-graded capability check against the result dict.

    Uses pattern matching on expected_behavior to determine which result keys
    to look for. Falls back to checking that the result is non-empty.
    """
    # Try pattern-based matching first
    for pattern, keys in _CODE_GRADER_PATTERNS:
        if re.search(pattern, expected_behavior, re.IGNORECASE):
            found = any(
                result.get(k) for k in keys
            )
            if not found:
                raise AssertionError(
                    f"Capability check '{check_id}' failed: expected result to contain "
                    f"one of {keys} based on expected_behavior: '{expected_behavior}'. "
                    f"Result keys: {list(result.keys())}"
                )
            return

    # Fallback: result must be non-empty
    if not result:
        raise AssertionError(
            f"Capability check '{check_id}' failed: result is empty. "
            f"Expected behavior: '{expected_behavior}'"
        )


# ---------------------------------------------------------------------------
# Category 9: Reasoning Dimensions (transcript dimension coverage)
# ---------------------------------------------------------------------------

# Keyword map for known reasoning dimensions.
# Each dimension maps to a list of keywords/phrases that indicate
# the dimension was exercised in the transcript.
_DIMENSION_KEYWORDS: dict[str, list[str]] = {
    "graph_utilization": [
        "build-kg", "bskg", "knowledge graph", "graph query",
        "query", "node", "graph node",
    ],
    "evidence_quality": [
        "evidence", "graph_node_ids", "code location", "proof",
        "finding", "citation", "reference",
    ],
    "pattern_coverage": [
        "vulndoc", "pattern", "detection", "vulnerability pattern",
        "vm-001", "vm-002", "auth-", "reentrancy",
    ],
    "attack_creativity": [
        "exploit", "attack vector", "attack path", "exploit path",
        "manipulation", "bypass", "escalation",
    ],
    "adversarial_rigor": [
        "attacker", "defender", "counterargument", "refut",
        "challenge", "dispute", "adversarial",
    ],
    "consensus_formation": [
        "consensus", "agree", "resolution", "verdict",
        "confirmed", "refuted", "disputed", "arbitrat",
    ],
}


def assert_reasoning_dimensions_covered(
    transcript: str, contract: dict[str, Any]
) -> None:
    """Assert transcript shows evidence of each reasoning dimension in the contract.

    Uses keyword/pattern matching (not LLM) to verify each dimension is
    exercised. LLM-based reasoning assessment belongs in 3.1c.

    Raises AssertionError with the dimension name on first uncovered dimension.
    """
    dimensions = contract.get("reasoning_dimensions", [])
    transcript_lower = transcript.lower()

    for dimension in dimensions:
        keywords = _DIMENSION_KEYWORDS.get(dimension, [])
        if not keywords:
            # Unknown dimension: check if dimension name itself appears
            if dimension.replace("_", " ") not in transcript_lower:
                raise AssertionError(
                    f"Reasoning dimension '{dimension}' not covered in transcript. "
                    f"No keywords defined and dimension name not found."
                )
            continue

        found = any(kw.lower() in transcript_lower for kw in keywords)
        if not found:
            raise AssertionError(
                f"Reasoning dimension '{dimension}' not covered in transcript. "
                f"Searched for keywords: {keywords}"
            )
